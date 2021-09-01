"""
================================================================
    * core/chat/messages.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Module for formatting and holding chat messages.
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Source.Python
from messages.base import SayText2
from messages.colors.saytext2 import (
    BLUE,
    BRIGHT_GREEN,
    DARK_BLUE,
    DULL_RED,
    GRAY,
    GREEN,
    LIGHT_BLUE,
    ORANGE,
    PALE_GREEN,
    PALE_RED,
    PINK,
    RED,
    WHITE,
    YELLOW,
)
from events import Event
from translations.strings import LangStrings

# dotf
from ..constants.paths import TRANSLATION_PATH

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
chat_strings = LangStrings(TRANSLATION_PATH / "chat_strings")

message_prefix = SayText2(chat_strings["prefix default"])

message_help = SayText2(chat_strings["help"])

message_start = SayText2(chat_strings["start"])

color_formats = {
    "blue": BLUE,
    "brightgreen": BRIGHT_GREEN,
    "darkblue": DARK_BLUE,
    "dullred": DULL_RED,
    "gray": GRAY,
    "grey": GRAY,
    "green": GREEN,
    "lightblue": LIGHT_BLUE,
    "orange": ORANGE,
    "lightgreen": PALE_GREEN,
    "lightred": PALE_RED,
    "pink": PINK,
    "red": RED,
    "white": WHITE,
    "yellow": YELLOW,
}

# =============================================================================
# >> ALL DECLARATION
# =============================================================================
__all__ = (
    message_help,
    message_start,
)


class SafeDict(dict):
    """Class for safe formatting of strings using dicts."""

    def __missing__(self, key):
        """Ignore missing keys."""
        return "{" + key + "}"


# Format prefix and colors in all messages.
for saytext in __all__:
    for key in saytext.message.keys():
        # Add prefix
        if "{prefix}" in saytext.message[key]:
            if key in message_prefix.message:
                saytext.message[key] = saytext.message[key].replace(
                    "{prefix}", message_prefix.message[key]
                )

        # Format colors
        saytext.message[key] = saytext.message[key].format_map(SafeDict(color_formats))
