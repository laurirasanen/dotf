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
from filters.entities import EntityIter

# dotf
from .sentry import Sentry
from ..log import Logger

SENTRY_CLASSNAME = "obj_sentrygun"
# helps separate from player sentries
SENTRY_TARGETNAME = "dotf_sentrygun"


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

    def spawn_sentry(self, origin, angles, team, lane, tier):
        sentry = Sentry.create()
        sentry.spawn(origin, angles, team, lane, tier)
        print(
            f"[dotf] Spawn sentry - team: {team}, lane: {lane}, tier: {tier}, origin: {origin}, angles: {angles}"
        )
        self.sentries.append(sentry)

    def remove_sentry(self, sentry):
        Logger.instance().log_debug(f"Unregister sentry {sentry.entity.target_name}")
        self.sentries.remove(sentry)

    def destroy_all(self):
        for entity in EntityIter():
            if entity.classname == SENTRY_CLASSNAME:
                # if entity.target_name.startswith(SENTRY_TARGETNAME):
                entity.take_damage(999999)
                entity.call_input("Kill")

    def clear(self):
        Logger.instance().log_debug("Clear buildings")
        self.sentries.clear()
        self.destroy_all()

    def sentry_from_index(self, index):
        for sentry in self.sentries:
            if sentry.index == index:
                return sentry
        return None

    def tick(self):
        for sentry in self.sentries:
            sentry.tick()
        pass

    def on_building_destroy(self, index):
        sentry = self.sentry_from_index(index)
        if sentry != None:
            sentry.on_destroy()
            self.remove_sentry(sentry)
