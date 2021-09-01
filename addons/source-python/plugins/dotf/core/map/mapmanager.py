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

        MapManager.__instance = self

    def on_load_map(self):
        self.bot_spawn_points.clear()

        for point in EntityIter("info_target"):
            if point.target_name.startswith("dotf_bot_spawn_point"):
                parts = point.target_name.split("_")[4:]
                spawn = {
                    "origin": point.origin,
                    "team": int(parts[0]),
                    "index": int(parts[1]),
                    "rotation": point.rotation,
                }
                self.bot_spawn_points.append(spawn)
            elif point.target_name.startswith("dotf_bot_lane_node"):
                parts = point.target_name.split("_")[4:]
                node = {
                    "origin": point.origin,
                    "index": int(parts[0]),
                }
                self.lane_nodes.append(node)

        print("[dotf] map loaded")
        print(f"[dotf]   bot spawnpoints: {len(self.bot_spawn_points)}")
        print(f"[dotf]   lane nodes: {len(self.lane_nodes)}")

    def get_spawn_points(self, team, index):
        return filter(
            lambda p: p["team"] == team and p["index"] == index, self.bot_spawn_points
        )

    def get_lane_nodes(self, index):
        return filter(lambda node: node["index"] == index, self.lane_nodes)
