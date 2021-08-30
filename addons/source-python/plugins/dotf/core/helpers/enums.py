"""Helpful enums"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python
from enum import IntEnum


class PlayerClass(IntEnum):
    NONE = 0
    SCOUT = 1
    SOLDIER = 3
    PYRO = 7
    DEMOMAN = 4
    HEAVY = 6
    ENGINEER = 9
    MEDIC = 5
    SNIPER = 2
    SPY = 8


class BotType(IntEnum):
    MELEE = 0
    RANGED = 1
