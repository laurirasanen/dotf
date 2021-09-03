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
# Source.Python
from engines.server import server
from entities.helpers import index_from_edict
from filters.players import PlayerIter
from mathlib import Vector, NULL_VECTOR, QAngle, NULL_QANGLE
from players.bots import bot_manager, BotCmd
from players.entity import Player
from players.constants import PlayerButtons

# dotf
from ..helpers import PlayerClass, BotType, Team, closest_point_on_line
from ..map.mapmanager import MapManager

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
melee_class = PlayerClass.HEAVY
ranged_class = PlayerClass.SNIPER

melee_model = "models/bots/heavy/bot_heavy.mdl"
ranged_model = "models/bots/sniper/bot_sniper.mdl"

melee_weapon = "tf_weapon_fists"
ranged_weapon = "tf_weapon_sniperrifle"

# =============================================================================
# >> CLASSES
# =============================================================================
class Bot:
    """A controllable bot class"""

    spawned = False
    aggro_target = None

    def __init__(self, team=Team.BLU, bot_type=BotType.MELEE):
        """Create a new bot"""

        self.spawned = False
        self.aggro_target = None
        self.bot = None
        self.controller = None
        self.bot_type = bot_type
        self.team = team
        self.move_speed = 200

        bot_edict = bot_manager.create_bot(
            f"{'Blu' if team == Team.BLU else 'Red'} {'melee' if bot_type == BotType.MELEE else 'ranged'} bot"
        )
        if bot_edict == None:
            raise ValueError("Failed to create a bot")

        self.controller = bot_manager.get_bot_controller(bot_edict)
        if self.controller == None:
            raise ValueError("Failed to get bot controller")

        # Settings we can apply before spawn
        self.bot = Player(index_from_edict(bot_edict))
        self.bot.team = self.team
        if self.bot_type == BotType.MELEE:
            self.bot.set_property_uchar("m_PlayerClass.m_iClass", melee_class)
            self.bot.set_property_uchar("m_Shared.m_iDesiredPlayerClass", melee_class)
        else:
            self.bot.set_property_uchar("m_PlayerClass.m_iClass", ranged_class)
            self.bot.set_property_uchar("m_Shared.m_iDesiredPlayerClass", ranged_class)

    def spawn(self, origin=NULL_VECTOR, rotation=NULL_QANGLE):
        self.spawn_origin = origin
        self.spawn_rotation = rotation
        self.bot.spawn(force=True)

    def on_spawn(self):
        # These will need to be applied after spawning
        self.bot.set_noblock(True)

        if self.bot_type == BotType.MELEE:
            self.bot.call_input("SetCustomModel", melee_model)
            for weapon in self.bot.weapons():
                if weapon.weapon_name != melee_weapon:
                    weapon.remove()
        else:
            self.bot.call_input("SetCustomModel", ranged_model)
            for weapon in self.bot.weapons():
                if weapon.weapon_name != ranged_weapon:
                    weapon.remove()

        self.bot.set_property_bool("m_PlayerClass.m_bUseClassAnimations", True)
        self.bot.set_property_float("m_flModelScale", 0.6)

        self.bot.teleport(self.spawn_origin, self.spawn_rotation)
        self.spawned = True

    def on_death(self):
        self.spawned = False
        self.aggro_target = None

    def kick(self, reason=""):
        if self.bot != None:
            self.bot.kick(reason)
            self.bot = None
            self.controller = None

    def tick(self):
        if self.bot == None or self.controller == None:
            return

        if self.spawned == False or self.bot.dead:
            self.tick_dead()
            return

        bcmd = self.get_cmd()
        self.controller.run_player_move(bcmd)

        # Refill ammo
        if self.bot_type == BotType.RANGED:
            if self.bot.active_weapon != None:
                ammoType = self.bot.active_weapon.get_property_int("m_iPrimaryAmmoType")
                self.bot.set_property_int(f"localdata.m_iAmmo.00{ammoType}", 25)

    def tick_dead(self):
        bcmd = BotCmd()
        bcmd.reset()
        self.controller.run_player_move(bcmd)

    def get_cmd(self):
        """Get BotCmd for move, aim direction, buttons, etc."""

        move_action, attack_action, view_angles = self.get_action()

        bcmd = BotCmd()
        bcmd.reset()

        bcmd.forward_move = self.move_speed * move_action

        if attack_action == 1:
            bcmd.buttons |= PlayerButtons.ATTACK

        bcmd.view_angles = view_angles

        if self.bot_type == BotType.MELEE:
            for index in self.bot.weapon_indexes(classname=melee_weapon):
                bcmd.weaponselect = index
        else:
            for index in self.bot.weapon_indexes(classname=ranged_weapon):
                bcmd.weaponselect = index

        return bcmd

    def get_origin(self) -> Vector:
        if self.bot != None:
            return self.bot.origin
        return NULL_VECTOR

    def get_range(self) -> float:
        if self.bot_type == BotType.MELEE:
            return 48.0
        else:
            return self.get_aggro_range() - 24.0

    def get_aggro_range(self) -> float:
        return 256.0

    def get_eye_pos(self) -> Vector:
        if self.bot != None:
            return self.bot.origin + self.bot.view_offset
        return NULL_VECTOR

    def get_action(self):
        # 1 = move forward
        move_action = 0
        # 1 = shoot
        attack_action = 0
        # direction to look
        view_angles = NULL_QANGLE

        if self.bot.dead:
            return move_action, attack_action, view_angles

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
                > self.get_aggro_range()
            ):
                self.aggro_target = None

        if self.aggro_target == None:
            # No prev target or invalid,
            # check for enemies in our range
            closest_dist = float("inf")
            for p in PlayerIter():
                if p.dead == False and p.team != self.bot.team:
                    dist = p.origin.get_distance(self.get_origin())
                    if dist < closest_dist:
                        closest_dist = dist
                        if dist <= self.get_aggro_range():
                            self.aggro_target = p
                            print(f"{self.bot.name} aggro to {p.name}")
        """
        self.aggro_target = None
        closest_dist = float("inf")
        for p in PlayerIter():
            if p.dead == False and p.team != self.bot.team:
                dist = p.origin.get_distance(self.get_origin())
                if dist < closest_dist:
                    closest_dist = dist
                    if dist <= self.get_aggro_range():
                        self.aggro_target = p

        # If have aggro, move towards aggro target if not in range, otherwise attack
        if self.aggro_target != None:
            dist = self.aggro_target.origin.get_distance(self.get_origin())
            if dist < self.get_range():
                attack_action = 1
                move_action = 0
            else:
                attack_action = 0
                move_action = 1

            # Face aggro
            target_center = self.aggro_target.origin
            target_center.z += (
                self.aggro_target.get_property_vector("m_Collision.m_vecMaxs").z * 0.5
            )
            direction = target_center - self.get_eye_pos()
            direction.get_vector_angles(Vector(0, 0, 1), view_angles)

            return move_action, attack_action, view_angles

        # If no aggro, navigate along lane, or back to the lane if not on it
        lane_count = MapManager.instance().lane_count
        closest_nodes = []
        closest_node = None
        closest_dist = float("inf")
        for x in range(lane_count):
            nodes = MapManager.instance().get_lane_nodes(x)
            for node in nodes:
                dist = self.get_origin().get_distance(node["origin"])
                if dist < closest_dist:
                    closest_dist = dist
                    closest_nodes = nodes
                    closest_node = node

        second_node = None
        direction = 1 if self.team == Team.BLU else -1
        next_node = None
        prev_node = None

        # Get next node
        if (
            len(nodes) > closest_node["index"] + direction
            and closest_node["index"] + direction >= 0
        ):
            next_node = closest_nodes[closest_node["index"] + direction]

        # Get prev node
        if (
            len(nodes) > closest_node["index"] - direction
            and closest_node["index"] - direction >= 0
        ):
            prev_node = closest_nodes[closest_node["index"] - direction]

        # Figure out which to use
        if next_node == None:
            second_node = prev_node
        elif prev_node == None:
            second_node = next_node
        else:
            # Both nodes valid, figure out which side we are on
            dir_next = next_node["origin"] - closest_node["origin"]
            dir_to_closest = closest_node["origin"] - self.get_origin()
            # Are we between closest and next?
            if dir_next.dot(dir_to_closest) < 0:
                second_node = next_node
            else:
                second_node = prev_node

        # This is the line we want to be on
        start = None
        end = None
        if (closest_node["index"] < second_node["index"] and direction < 0) or (
            closest_node["index"] > second_node["index"] and direction > 0
        ):
            end = closest_node["origin"]
            start = second_node["origin"]
        else:
            end = second_node["origin"]
            start = closest_node["origin"]

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
            move_action = 1

        return move_action, attack_action, view_angles
