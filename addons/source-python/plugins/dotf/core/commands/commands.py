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
# Source.Python
from engines.trace import engine_trace, Ray, ContentMasks, TraceFilterSimple, GameTrace
from mathlib import Vector
from filters.players import PlayerIter

# dotf
from .clientcommands import CommandHandler, Argument
from ..chat.messages import message_help, message_start
from ..game.gamemanager import GameManager
from ..nextbot.nextbot import NextBotCombatCharacter


# =============================================================================
# >> COMMAND CALLBACK HANDLERS
# =============================================================================
def _help_handler(user, command):
    """Called when player uses /r command."""

    message_help.send(user.player.index)


def _start_handler(user, command):
    """Start game"""
    GameManager.instance().start_game()
    message_start.send(user.player.index)


def _test_handler(user, command):
    trace = GameTrace()
    engine_trace.trace_ray(
        Ray(
            user.player.get_eye_location(),
            user.player.get_eye_location() + user.player.view_vector * 10000.0,
        ),
        ContentMasks.PLAYER_SOLID,
        TraceFilterSimple(PlayerIter()),
        trace,
    )
    if trace.did_hit() and trace.entity.index == 0:
        bot = NextBotCombatCharacter.create()
        bot.spawn(trace.end_position, user.player.angles)


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

    CommandHandler.instance().add_command(
        name="start",
        alias=["s"],
        callback=_start_handler,
        description="Start game",
        usage="/start",
    )

    CommandHandler.instance().add_command(
        name="test",
        callback=_test_handler,
    )
