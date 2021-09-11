"""
================================================================
    * core/nextbot/locomotion.py
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
from platform import platform
from engines.server import engine_server
from engines.precache import Model
from core import PLATFORM
from entities.entity import Entity
from memory import (
    DataType,
    Pointer,
    Convention,
    get_object_pointer,
    get_virtual_function,
    make_object,
    find_binary,
    Function,
)
from entities.hooks import EntityPreHook, EntityPostHook, EntityCondition
from mathlib import Vector, QAngle


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
LOCO_VIRTUALS = (
    {
        "name": "FaceTowards",
        "index": 73 if platform == "windows" else 74,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
        ),
        "return": DataType.VOID,
    },
)


class BaseBossLocomotion(Pointer):
    def __init__(self, pointer) -> None:
        print("LOCO __init__")
        super().__init__(pointer)
        self.virtuals = []

    def get_virtual(self, name):
        # Already created?
        for virtual in self.virtuals:
            if virtual["name"] == name:
                return virtual["func"]

        # Create
        for virtual in LOCO_VIRTUALS:
            if virtual["name"] == name:
                func = self.make_virtual_function(
                    virtual["index"],
                    virtual["convention"],
                    virtual["args"],
                    virtual["return"],
                )
                self.virtuals.append(
                    {
                        "name": name,
                        "func": func,
                    }
                )
                return func

        # Invalid
        return None

    # =============================================================================
    # >> VIRTUALS
    # =============================================================================
    def face_towards(self, target: Vector):
        print(f"LOCO face_towards {target.x} {target.y} {target.z}")
        self.get_virtual("FaceTowards").__call__(self, target)
