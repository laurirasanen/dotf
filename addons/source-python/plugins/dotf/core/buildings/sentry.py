"""
================================================================
    * core/buildings/sentry.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Sentrygun functionality
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python
from configobj import ConfigObj

# Source.Python
from memory import Pointer

# dotf
from ..constants.paths import CFG_PATH

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
building_config = ConfigObj(CFG_PATH + "/building_settings.ini")


class Sentry:

    entity = None
    lane = 0
    tier = 0
    sentry_range = 0
    config = None

    def __init__(self, entity):
        self.entity = entity
        # dotf_sentrygun_<lane>_<tier>
        self.lane = int(entity.target_name.split("_")[2])
        self.tier = int(entity.target_name.split("_")[3])
        self.config = building_config["sentry"][f"{self.tier}"]
        self.register()

    def tick(self):
        pass

    def on_destroy(self):
        self.unregister()

    def register(self):
        # Get pointer to m_flSentryRange
        player_controlled = None

        for member in self.entity.server_class.find_server_class(
            "CObjectSentrygun"
        ).table:
            if member.name == "m_bPlayerControlled":
                player_controlled = member

        self.sentry_range = Pointer(
            self.entity.pointer + player_controlled.offset - 4,
        )

        # Health
        self.entity.call_input(
            "SetHealth", self.config.as_int("health")
        )  # m_flHealth and m_iHealth for buildings
        self.entity.set_property_int("m_iMaxHealth", self.config.as_int("health"))

    def set_range(self):
        self.sentry_range.set_float(self.config.as_float("range"))

    def get_damage(self):
        return self.config.as_float("damage")

    def unregister(self):
        pass
