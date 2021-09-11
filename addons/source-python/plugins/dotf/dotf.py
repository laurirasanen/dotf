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

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================


# =============================================================================
# >> LISTENERS
# =============================================================================
def load():
    """Called when Source.Python loads the plugin."""
    print(f"[dotf] Loaded!")
    # main server cfg
    queue_command_string(f"exec source-python/dotf/dotf")
    # protected cvars, TODO move to .ini
    cvar.find_var("tf_dropped_weapon_lifetime").set_int(0)
    cvar.find_var("nb_update_frequency").set_float(0.0152)

    register_commands()
    UserManager.instance().add_all()
    MapManager.instance().on_load_map()
    BuildingManager.instance().add_all()


def unload():
    """Called when Source.Python unloads the plugin."""
    BotManager.instance().clear()  # kick bots
    print(f"[dotf] Unloaded!")
