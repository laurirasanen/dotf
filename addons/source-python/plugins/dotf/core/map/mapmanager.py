"""
================================================================
    * core/map/mapmanager.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    ...
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Source.Python
from filters.entities import EntityIter
from mathlib import Vector, QAngle

# dotf
from ..log import Logger


class MapManager:
    __instance = None

    def instance():
        """Singleton instance"""
        if MapManager.__instance is None:
            MapManager()
        return MapManager.__instance

    def __init__(self):
        if MapManager.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.sentry_spawn_points = []
        self.bot_spawn_points = []
        self.lane_nodes = []
        self.lane_count = 0

        MapManager.__instance = self

    def on_load_map(self):
        self.sentry_spawn_points.clear()
        self.bot_spawn_points.clear()
        self.lane_nodes.clear()
        self.lane_count = 0

        # TEST
        # self.sentry_spawn_points.append({
        #     "origin": Vector(-160, -270, -125),
        #     "team": 3,
        #     "lane": 0,
        #     "tier": 0,
        #     "rotation": QAngle(0, 0, 0)
        # })
        # self.sentry_spawn_points.append({
        #     "origin": Vector(520, -270, -125),
        #     "team": 2,
        #     "lane": 0,
        #     "tier": 0,
        #     "rotation": QAngle(0, 180, 0)
        # })

        for point in EntityIter("info_target"):
            if point.target_name.startswith("dotf_sentry_spawn_point"):
                parts = point.target_name.split("_")[4:]
                spawn = {
                    "origin": point.origin,
                    "team": int(parts[0]),
                    "lane": int(parts[1]),
                    "tier": int(parts[2]),
                    "rotation": point.rotation,
                }
                self.sentry_spawn_points.append(spawn)
            elif point.target_name.startswith("dotf_bot_spawn_point"):
                parts = point.target_name.split("_")[4:]
                spawn = {
                    "origin": point.origin,
                    "team": int(parts[0]),
                    "lane": int(parts[1]),
                    "bot_type": int(parts[2]),
                    "rotation": point.rotation,
                }
                self.bot_spawn_points.append(spawn)
            elif point.target_name.startswith("dotf_bot_lane_node"):
                parts = point.target_name.split("_")[4:]
                node = {
                    "origin": point.origin,
                    "lane": int(parts[0]),
                    "index": int(parts[1]),
                }
                self.lane_nodes.append(node)
                # Lane indices start from 0
                if node["lane"] >= self.lane_count:
                    self.lane_count = node["lane"] + 1

        self.lane_nodes.sort(key=lambda node: node["index"])

        Logger.instance().log_debug("map loaded")
        Logger.instance().log_debug(
            f"  sentry spawnpoints: {len(self.sentry_spawn_points)}"
        )
        Logger.instance().log_debug(f"  bot spawnpoints: {len(self.bot_spawn_points)}")
        Logger.instance().log_debug(f"  lane count: {self.lane_count}")
        Logger.instance().log_debug(f"  lane nodes: {len(self.lane_nodes)}")

    def get_bot_spawn_points(self, team, lane):
        return [
            point
            for point in self.bot_spawn_points
            if point["team"] == team and point["lane"] == lane
        ]

    def get_sentry_spawn_points(self, team, lane):
        return [
            point
            for point in self.sentry_spawn_points
            if point["team"] == team and point["lane"] == lane
        ]

    def get_lane_nodes(self, lane):
        return [node for node in self.lane_nodes if node["lane"] == lane]
