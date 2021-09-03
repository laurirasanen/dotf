"""
================================================================
    * core/game/gamestate.py
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
from mathlib import Vector


def closest_point_on_line(start: Vector, end: Vector, point: Vector) -> Vector:
    """Get the closest position on line (start, end) to point"""
    norm = (end - start).normalized()
    to_point = point - start
    frac = to_point.dot(norm)
    return start + frac * norm
