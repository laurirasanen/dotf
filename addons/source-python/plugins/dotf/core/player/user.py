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

# dotf
from ..constants import CFG_PATH

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
        print(
            f"settings {self.player.name} (class {self.player.get_property_uchar('m_PlayerClass.m_iClass')})"
        )
        self.class_settings.walk(
            lambda section, key: print(f"  {key}: {self.class_settings[key]}")
        )

    def tick(self):
        if self.player.dead:
            return

        pass
