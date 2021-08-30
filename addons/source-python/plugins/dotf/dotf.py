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

# dotf
from .core.hooks import *
from .core.commands.commands import register_commands
from .core.player.usermanager import UserManager
from .core.bot.botmanager import BotManager

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================


# =============================================================================
# >> LISTENERS
# =============================================================================
def load():
    """Called when Source.Python loads the plugin."""
    print(f"[dotf] Loaded!")
    queue_command_string(f"exec source-python/dotf/dotf")
    register_commands()
    UserManager.instance().add_all()
    BotManager.instance().add_bot(0)
    BotManager.instance().add_bot(1)


def unload():
    """Called when Source.Python unloads the plugin."""
    BotManager.instance().clear()  # kick bots
    print(f"[dotf] Unloaded!")
