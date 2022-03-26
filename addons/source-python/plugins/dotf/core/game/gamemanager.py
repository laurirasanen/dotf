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
# Python
from configobj import ConfigObj

# Source.Python

# dotf
from .gamestate import GameState
from ..bot.botmanager import BotManager
from ..map.mapmanager import MapManager
from ..helpers import Team
from ..constants.paths import CFG_PATH

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
game_settings = ConfigObj(CFG_PATH + "/game_settings.ini")


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

        self.spawn_bot_wave()

        self.state.started = True

    def spawn_bot_wave(self):
        for lane_index in range(MapManager.instance().lane_count):
            blu_bot_spawns = MapManager.instance().get_spawn_points(
                Team.BLU, lane_index
            )
            for point in blu_bot_spawns:
                bot = BotManager.instance().add_bot()
                if bot != None:
                    bot.spawn(
                        point["origin"],
                        point["rotation"],
                        Team.BLU
                        # , point["bot_type"]
                    )

            red_bot_spawns = MapManager.instance().get_spawn_points(
                Team.RED, lane_index
            )
            for point in red_bot_spawns:
                bot = BotManager.instance().add_bot()
                if bot != None:
                    bot.spawn(
                        point["origin"],
                        point["rotation"],
                        Team.RED
                        # , point["bot_type"]
                    )

    def tick(self):
        if self.state.started:
            self._tick_game()
            pass
        else:
            self._tick_wait()

    def _tick_game(self):
        self.state.tick += 1

        if (self.state.tick % game_settings["time"].as_int("bot_wave_interval")) == 0:
            self.spawn_bot_wave()

    def _tick_wait(self):
        pass
