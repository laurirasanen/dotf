"""
================================================================
    * core/game/gamemanager.py
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

# dotf
from .gamestate import GameState
from ..bot.botmanager import BotManager
from ..map.mapmanager import MapManager
from ..helpers import Team


class GameManager:
    __instance = None

    state = None

    def instance():
        """Singleton instance"""
        if GameManager.__instance is None:
            GameManager()
        return GameManager.__instance

    def __init__(self):
        if GameManager.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.state = GameState()

        GameManager.__instance = self

    def start_game(self):
        if self.state.started:
            return

        for lane_index in range(MapManager.instance().lane_count):
            blu_bot_spawns = MapManager.instance().get_spawn_points(
                Team.BLU, lane_index
            )
            for point in blu_bot_spawns:
                BotManager.instance().add_bot(Team.BLU, point["bot_type"]).spawn(
                    point["origin"], point["rotation"]
                )

            red_bot_spawns = MapManager.instance().get_spawn_points(
                Team.RED, lane_index
            )
            for point in red_bot_spawns:
                BotManager.instance().add_bot(Team.RED, point["bot_type"]).spawn(
                    point["origin"], point["rotation"]
                )

        self.state.started = True

    def tick(self):
        self.state.tick += 1
