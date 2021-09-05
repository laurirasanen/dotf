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
        self.apply_class_settings()

    def apply_class_settings(self):
        self.class_settings = player_config["class_settings"][
            f"{self.player.get_property_uchar('m_PlayerClass.m_iClass')}"
        ]
        self.player.set_property_int(
            "m_iMaxHealth", self.class_settings.as_int("health")
        )
        self.player.set_property_int("m_iHealth", self.class_settings.as_int("health"))
        # TODO: m_iMaxHealth doesn't actually set max health in tf2.
        # use https://github.com/FlaminSarge/tf2attributes ?
        # TF2Attrib_SetByName(player, "max health additive bonus", health)

    def tick(self):
        if self.player.dead:
            return

        regen_interval = self.class_settings.as_int("regen_interval")
        if regen_interval > 0:
            if server.tick % regen_interval == 0:
                regen = self.class_settings.as_int("regen")
                if self.player.health < self.player.max_health and regen > 0:
                    self.player.health += regen
