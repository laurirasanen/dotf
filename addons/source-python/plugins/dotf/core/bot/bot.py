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
from mathlib import Vector, NULL_VECTOR, QAngle, NULL_QANGLE
from players.bots import bot_manager, BotCmd
from players.entity import Player
from players.constants import PlayerButtons

# dotf
from ..helpers import PlayerClass, BotType

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

    def __init__(self, bot_type=BotType.MELEE):
        """Create a new bot"""

        self.bot = None
        self.controller = None
        self.bot_type = bot_type
        self.team = 2
        self.move_speed = 200

    def spawn(self):
        if self.bot != None or self.controller != None:
            return

        bot_edict = bot_manager.create_bot("Botty McBotface")
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

    def kick(self, reason=""):
        if self.bot != None:
            self.bot.kick(reason)
            self.bot = None
            self.controller = None

    def tick(self):
        if self.bot == None or self.controller == None:
            return

        bcmd = self.get_cmd()
        self.controller.run_player_move(bcmd)

        # Refill ammo
        if self.bot_type == BotType.RANGED:
            if self.bot.active_weapon != None:
                ammoType = self.bot.active_weapon.get_property_int("m_iPrimaryAmmoType")
                self.bot.set_property_int(f"localdata.m_iAmmo.00{ammoType}", 25)

    def get_cmd(self):
        """Get BotCmd for move, aim direction, buttons, etc."""

        # TODO: big brain method for getting these for current state, etc.
        move_action = 1
        shoot_action = 1
        view_angles = QAngle(0, server.tick % 360, 0)

        bcmd = BotCmd()
        bcmd.reset()

        bcmd.forward_move = self.move_speed * move_action

        if shoot_action == 1:
            bcmd.buttons |= PlayerButtons.ATTACK

        bcmd.view_angles = view_angles

        if self.bot_type == BotType.MELEE:
            for index in self.bot.weapon_indexes(classname=melee_weapon):
                bcmd.weaponselect = index
        else:
            for index in self.bot.weapon_indexes(classname=ranged_weapon):
                bcmd.weaponselect = index

        return bcmd

    def get_origin(self):
        if self.bot != None:
            return self.bot.origin
        return NULL_VECTOR
