"""
================================================================
    * dotf.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Main module for dotf
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Source.Python
from engines.server import queue_command_string
from cvars import cvar

# dotf
from .core.hooks import *
from .core.commands.commands import register_commands
from .core.player.usermanager import UserManager
from .core.bot.botmanager import BotManager
from .core.map.mapmanager import MapManager
from .core.buildings.buildingmanager import BuildingManager
from .core.game import GameManager
from .core.log import Logger

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================


# =============================================================================
# >> LISTENERS
# =============================================================================
def load():
    """Called when Source.Python loads the plugin."""
    Logger.instance().log_info("PLUGIN LOAD")
    # main server cfg
    queue_command_string(f"exec source-python/dotf/dotf")
    # protected cvars, TODO move to .ini
    cvar.find_var("tf_dropped_weapon_lifetime").set_float(0)
    cvar.find_var("nb_update_frequency").set_float(0.5)
    cvar.find_var("nb_update_framelimit").set_float(15)
    cvar.find_var("tf_base_boss_max_turn_rate").set_float(200)

    register_commands()
    GameManager.instance().load()


def unload():
    """Called when Source.Python unloads the plugin."""
    Logger.instance().log_info("PLUGIN UNLOAD")
    GameManager.instance().reset()
