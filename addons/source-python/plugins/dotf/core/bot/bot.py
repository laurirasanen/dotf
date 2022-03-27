"""
================================================================
    * core/bot/bot.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Bot functionality
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python
from configobj import ConfigObj

# Source.Python
from engines.trace import engine_trace, Ray, ContentMasks, TraceFilterSimple, GameTrace
from engines.server import server
from entities.helpers import index_from_edict
from mathlib import Vector, NULL_VECTOR, QAngle, NULL_QANGLE
from players.bots import bot_manager, BotCmd
from players.entity import Player
from players.constants import PlayerButtons
from entities.constants import CollisionGroup

# dotf
from ..helpers import (
    PlayerClass,
    BotType,
    Team,
    closest_point_on_line,
    get_closest_lane,
)
from ..constants import CFG_PATH

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
bot_config = ConfigObj(CFG_PATH + "/bot_settings.ini")

# =============================================================================
# >> CLASSES
# =============================================================================
class Bot:
    """A controllable bot class"""

    # TODO: look at tf_robot_destruction_robot / CTFRobotDestruction_Robot,
    # or just CBaseCombatCharacter without Player.
    # Default player class bot seems very laggy when full server and limited to maxplayers!

    reserved = False
    spawned = False
    aggro_target = None
    config = None

    def __init__(self):
        """Create a new bot"""

        self.cached_origin = None
        self.reserved = False
        self.spawned = False
        self.aggro_target = None
        self.bot = None
        self.controller = None

        self.bot_edict = bot_manager.create_bot("Bot")
        if self.bot_edict == None:
            raise ValueError("Failed to create a bot")

        self.controller = bot_manager.get_bot_controller(self.bot_edict)
        if self.controller == None:
            raise ValueError("Failed to get bot controller")

        self.bot = Player(index_from_edict(self.bot_edict))

    def spawn(
        self,
        team=Team.BLU,
        bot_type=BotType.MELEE,
        origin=NULL_VECTOR,
        rotation=NULL_QANGLE,
    ):
        self.reserved = True
        self.bot_type = bot_type
        self.team = team
        self.aggro_target = None
        self.spawn_origin = origin
        self.spawn_rotation = rotation

        # Settings we can apply before spawn
        # TODO: move props to .ini ?
        self.bot.team = self.team
        self.bot.name = f"{'Blu' if team == Team.BLU else 'Red'} {'melee' if bot_type == BotType.MELEE else 'ranged'} bot"

        self.config = (
            bot_config["bot_melee"]
            if self.bot_type == BotType.MELEE
            else bot_config["bot_ranged"]
        )
        self.move_speed = self.config.as_float("move_speed")

        self.bot.set_property_uchar(
            "m_PlayerClass.m_iClass", self.config.as_int("class")
        )
        self.bot.set_property_uchar(
            "m_Shared.m_iDesiredPlayerClass", self.config.as_int("class")
        )

        self.bot.spawn(force=True)

    def on_spawn(self):
        # These will need to be applied after spawning
        self.bot.set_noblock(True)

        self.bot.call_input("SetCustomModel", self.config["model"])

        # TODO: move props to .ini ?
        self.bot.set_property_bool("m_PlayerClass.m_bUseClassAnimations", True)
        self.bot.set_property_float(
            "m_flModelScale", float(self.config.as_float("model_scale"))
        )
        self.bot.set_property_int("m_iHealth", self.config.as_int("health"))

        self.ammo_type = None
        for weapon in self.bot.weapons():
            if weapon.weapon_name != self.config["weapon"]:
                weapon.remove()
            else:
                self.ammo_type = weapon.get_property_int("m_iPrimaryAmmoType")

        self.bot.teleport(self.spawn_origin, self.spawn_rotation)
        self.spawned = True

    def on_death(self):
        self.reserved = False
        self.spawned = False
        self.aggro_target = None
        # Prevent automatic respawn
        self.bot.set_property_uchar("m_Shared.m_iDesiredPlayerClass", 0)

    def kick(self, reason=""):
        if self.bot != None:
            self.bot.kick(reason)
            self.bot = None
            self.controller = None

    def get_max_health(self):
        return self.config.as_int("health")

    def tick(self, player_list):
        self.cached_origin = None

        if self.bot == None or self.controller == None:
            return

        if self.reserved and not self.spawned:
            self.tick_dead()
            return

        bcmd = self.get_cmd(player_list)
        self.controller.run_player_move(bcmd)

        # Refill ammo
        if self.config.as_int("ammo") > 0 and self.ammo_type != None:
            self.bot.set_property_int(
                f"localdata.m_iAmmo.00{self.ammo_type}", self.config.as_int("ammo")
            )

        # Don't allow overheal from medics
        if self.bot.health > self.get_max_health():
            self.bot.health = self.get_max_health()

    def tick_dead(self):
        # Need to run cmds to respawn
        bcmd = BotCmd()
        bcmd.reset()
        self.controller.run_player_move(bcmd)

    def get_cmd(self, player_list):
        """Get BotCmd for move, aim direction, buttons, etc."""

        forward_move, side_move, attack_action, view_angles = self.get_action(
            player_list
        )

        bcmd = BotCmd()
        bcmd.reset()

        bcmd.forward_move = self.move_speed * forward_move
        bcmd.side_move = self.move_speed * side_move

        if attack_action == 1:
            bcmd.buttons |= PlayerButtons.ATTACK

        bcmd.view_angles = view_angles

        for index in self.bot.weapon_indexes(classname=self.config["weapon"]):
            bcmd.weaponselect = index

        return bcmd

    def get_origin(self) -> Vector:
        if self.bot != None:
            if self.cached_origin != None:
                return self.cached_origin
            return self.bot.origin
        return NULL_VECTOR

    def get_eye_pos(self) -> Vector:
        if self.bot != None:
            return self.get_origin() + self.bot.view_offset
        return NULL_VECTOR

    def get_action(self, player_list):
        # 1 = move forward
        forward_move = 0
        # 1 = move right
        side_move = 0
        # 1 = shoot
        attack_action = 0
        # direction to look
        view_angles = NULL_QANGLE

        if self.bot.dead:
            return forward_move, side_move, attack_action, view_angles

        move_target = self.get_origin()

        # TODO:
        # - figure out de-aggro from players
        # - visibility check, dont aggro through walls
        #   - check if any friendly has vision
        # - prio players over buildings

        """
        # Check if existing target is still valid
        if self.aggro_target != None:
            if self.aggro_target.dead:
                self.aggro_target = None
            elif (
                self.aggro_target.origin.get_distance(self.get_origin())
                > self.config.as_float("aggro_range")
            ):
                self.aggro_target = None

        if self.aggro_target == None:
            # No prev target or invalid,
            # check for enemies in our range
            closest_dist = float("inf")
            for p in player_list:
                if p.dead == False and p.team != self.bot.team:
                    dist = p.origin.get_distance(self.get_origin())
                    if dist < closest_dist:
                        closest_dist = dist
                        if dist <= self.config.as_float("aggro_range"):
                            self.aggro_target = p
                            Logger.instance().log_debug(f"{self.bot.name} aggro to {p.name}")
        """
        self.aggro_target = None
        closest_dist = float("inf")
        closest_friendly = None
        closest_friendly_dist = float("inf")
        for p in player_list:
            if p.dead:
                continue

            dist = p.origin.get_distance(self.get_origin())
            if p.team != self.bot.team:
                if dist < closest_dist:
                    closest_dist = dist
                    if dist <= self.config.as_float("aggro_range"):
                        # Close enough to aggro, check visibility
                        trace = GameTrace()
                        engine_trace.trace_ray(
                            Ray(
                                self.get_eye_pos(),
                                p.origin
                                + Vector(
                                    0,
                                    0,
                                    p.get_property_vector("m_Collision.m_vecMaxs").z,
                                ),
                            ),
                            ContentMasks.PLAYER_SOLID,
                            TraceFilterSimple(player_list),
                            trace,
                        )
                        if trace.did_hit() and trace.entity.index == 0:
                            # hit world
                            pass
                        else:
                            self.aggro_target = p

            else:
                if p != self.bot:
                    if dist < 24.0 and dist < closest_friendly_dist:
                        closest_friendly_dist = dist
                        closest_friendly = p

        # Move away from friendlies
        # (Melee attacks get absorbed)
        if closest_friendly != None:
            left = Vector()
            view_angles.get_angle_vectors(None, None, left)
            to_closest = closest_friendly.origin - self.get_origin()
            if left.dot(to_closest) < 0:
                # closest friendly is on our right, move left
                side_move = -0.5
            else:
                # closest friendly is on our left, move right
                side_move = 0.5

        # If have aggro, move towards aggro target if not in range, otherwise attack
        if self.aggro_target != None:
            dist = self.aggro_target.origin.get_distance(self.get_origin())
            if dist < self.config.as_float("attack_range"):
                attack_action = 1
                forward_move = 0
                # TODO: this stops working if target is too close,
                # something wrong with get_distance?
                if dist < self.config.as_float("attack_range_min"):
                    forward_move = -1
            else:
                attack_action = 0
                forward_move = 1

            # Face aggro
            target_center = self.aggro_target.origin
            target_center.z += (
                self.aggro_target.get_property_vector("m_Collision.m_vecMaxs").z * 0.5
            )
            direction = target_center - self.get_eye_pos()
            direction.get_vector_angles(Vector(0, 0, 1), view_angles)

            return forward_move, side_move, attack_action, view_angles

        # If no aggro, navigate along lane, or back to the lane if not on it
        start, end = get_closest_lane(self.get_origin(), self.team)
        line = end - start

        # Are we on the line?
        closest_point = closest_point_on_line(start, end, self.get_origin())
        margin = 32.0
        if closest_point.get_distance(self.get_origin()) > margin:
            move_target = closest_point
        else:
            # Overshoot end a bit to avoid weirdness if we're very close to it
            move_target = end + line.normalized() * 10.0

        to_move_target = move_target - self.get_origin()
        move_margin = 1.0
        if to_move_target.length > move_margin:
            # Let's move
            to_move_target.get_vector_angles(Vector(0, 0, 1), view_angles)
            forward_move = 1

        return forward_move, side_move, attack_action, view_angles
