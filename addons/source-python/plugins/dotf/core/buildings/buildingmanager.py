"""
================================================================
    * core/buildings/buildingmanager.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Building functionality
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Source.Python
from filters.players import PlayerIter
from mathlib import NULL_VECTOR
from filters.entities import EntityIter

# dotf
from .sentry import Sentry


class BuildingManager:
    __instance = None

    sentries = []

    def instance():
        """Singleton instance"""
        if BuildingManager.__instance is None:
            BuildingManager()
        return BuildingManager.__instance

    def __init__(self):
        if BuildingManager.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.sentries = []

        BuildingManager.__instance = self

    def add_sentry(self, entity):
        sentry = Sentry(entity)
        print(
            f"[dotf] Register sentry {sentry.entity.target_name}, team: {sentry.entity.team_index}"
        )
        self.sentries.append(sentry)
        return sentry

    def remove_sentry(self, sentry):
        print(f"[dotf] Unregister sentry {sentry.entity.target_name}")
        sentry.unregister()
        self.sentries.remove(sentry)

    def add_all(self):
        for entity in EntityIter():
            if entity.classname == "obj_sentrygun":
                if entity.target_name.startswith("dotf_sentrygun"):
                    self.add_sentry(entity)

    def clear(self):
        print("[dotf] Clear buildings")
        for sentry in self.sentries:
            sentry.unregister()
        self.sentries.clear()

    def sentry_from_index(self, index):
        for sentry in self.sentries:
            if sentry.entity.index == index:
                return sentry
        return None

    def tick(self):
        for sentry in self.sentries:
            sentry.tick()

    def on_building_destroy(self, index):
        sentry = self.sentry_from_index(index)
        if sentry != None:
            sentry.on_destroy()
