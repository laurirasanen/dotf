"""
================================================================
    * core/player/user.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Player extension
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python
from configobj import ConfigObj

# Source.Python
from engines.server import server

# dotf
from ..constants import CFG_PATH
from ..helpers.entity import dump_entity_attributes, dump_entity_properties
from ..log import Logger

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
player_config = ConfigObj(CFG_PATH + "/player_settings.ini")


class User:
    player = None
    class_settings = None

    def __init__(self, player):
        self.player = player
        self.class_settings = player_config["class_settings"][
            f"{self.player.get_property_uchar('m_PlayerClass.m_iClass')}"
        ]

    def on_spawn(self):
        if self.player.is_observer():
            return
        Logger.instance().log_debug(f"player {self.player.steamid} on_spawn")
        self.apply_class_settings()

    def apply_class_settings(self):
        self.class_settings = player_config["class_settings"][
            f"{self.player.get_property_uchar('m_PlayerClass.m_iClass')}"
        ]
        self.player.set_property_int("m_iHealth", self.get_max_health())

    def tick(self):
        if self.player.dead or self.player.is_observer():
            return

        regen_interval = self.class_settings.as_int("regen_interval")
        if regen_interval > 0:
            if server.tick % regen_interval == 0:
                regen = self.class_settings.as_int("regen")
                if self.player.health < self.get_max_health() and regen > 0:
                    self.player.health += regen

        # Don't allow overheal from medics
        if self.player.health > self.get_max_health():
            self.player.health = self.get_max_health()

    def get_max_health(self):
        base_health = self.class_settings.as_int("health")
        bonus_health = 0  # TODO: more health per player level
        return base_health + bonus_health
