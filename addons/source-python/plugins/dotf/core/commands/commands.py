"""
================================================================
    * core/commands/commands.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Registering commands
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# dotf
from .clientcommands import CommandHandler, Argument
from ..chat.messages import message_help


# =============================================================================
# >> COMMAND CALLBACK HANDLERS
# =============================================================================
def _help_handler(user, command):
    """Called when player uses /r command."""

    message_help.send(user.player.index)


# =============================================================================
# >> REGISTER COMMANDS
# =============================================================================
def register_commands():
    """Register commands"""

    CommandHandler.instance().add_command(
        name="help",
        callback=_help_handler,
        args=[Argument(str, False, None)],
        description="Shows a general help text or one for a specific command",
        usage="/help <command>",
    )
