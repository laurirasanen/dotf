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

# dotf


class MapManager:
    __instance = None

    bot_spawn_points = []
    lane_nodes = []
    lane_count = 0

    def instance():
        """Singleton instance"""
        if MapManager.__instance is None:
            MapManager()
        return MapManager.__instance

    def __init__(self):
        if MapManager.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.bot_spawn_points = []
        self.lane_nodes = []
        self.lane_count = 0

        MapManager.__instance = self

    def on_load_map(self):
        self.bot_spawn_points.clear()
        self.lane_nodes.clear()
        self.lane_count = 0

        for point in EntityIter("info_target"):
            if point.target_name.startswith("dotf_bot_spawn_point"):
                parts = point.target_name.split("_")[4:]
                spawn = {
                    "origin": point.origin,
                    "team": int(parts[0]),
                    "lane": int(parts[1]),
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

        print("[dotf] map loaded")
        print(f"[dotf]   bot spawnpoints: {len(self.bot_spawn_points)}")
        print(f"[dotf]   lane count: {self.lane_count}")
        print(f"[dotf]   lane nodes: {len(self.lane_nodes)}")

    def get_spawn_points(self, team, lane):
        return [
            point
            for point in self.bot_spawn_points
            if point["team"] == team and point["lane"] == lane
        ]

    def get_lane_nodes(self, lane):
        return [node for node in self.lane_nodes if node["lane"] == lane]
