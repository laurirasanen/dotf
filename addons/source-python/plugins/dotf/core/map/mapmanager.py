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

    def instance():
        """Singleton instance"""
        if MapManager.__instance is None:
            MapManager()
        return MapManager.__instance

    def __init__(self):
        if MapManager.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.bot_spawn_points = []

        MapManager.__instance = self

    def on_load_map(self):
        self.bot_spawn_points.clear()

        for point in EntityIter("info_target"):
            # for attr in dir(point):
            #     print(f"{attr}: {getattr(point, attr)}")
            if point.target_name.startswith("dotf_bot_spawn_point"):
                parts = point.target_name.split("_")[4:]
                spawn = {
                    "origin": point.origin,
                    "team": int(parts[0]),
                    "index": int(parts[1]),
                    "rotation": point.rotation,
                }
                self.bot_spawn_points.append(spawn)

        print("[dotf] map loaded")
        print(f"[dotf]   bot spawnpoints: {len(self.bot_spawn_points)}")

    def get_spawn_points(self, team, index):
        return filter(
            lambda p: p["team"] == team and p["index"] == index, self.bot_spawn_points
        )
