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

# dotf
from ..log import Logger

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
LOCO_VIRTUALS = (
    {
        "name": "Update",
        "index": 43 if platform == "windows" else 44,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
    {
        "name": "Approach",
        "index": 46 if platform == "windows" else 47,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
            DataType.FLOAT,
        ),
        "return": DataType.VOID,
    },
    {
        "name": "DriveTo",
        "index": 47 if platform == "windows" else 48,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
        ),
        "return": DataType.VOID,
    },
    {
        "name": "Run",
        "index": 55 if platform == "windows" else 56,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
    {
        "name": "SetDesiredSpeed",
        "index": 59 if platform == "windows" else 60,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.FLOAT,
        ),
        "return": DataType.VOID,
    },
    {
        "name": "GetGroundSpeed",
        "index": 66 if platform == "windows" else 67,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.FLOAT,
    },
    {
        "name": "GetGroundMotionVector",
        "index": 67 if platform == "windows" else 68,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.POINTER,
    },
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
    {
        "name": "GetFeet",
        "index": 78 if platform == "windows" else 79,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.POINTER,
    },
    {
        "name": "IsPotentiallyTraversable",
        "index": 91 if platform == "windows" else 92,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
            DataType.POINTER,
            DataType.INT,
            DataType.POINTER,
        ),
        "return": DataType.BOOL,
    },
    {
        "name": "StuckMonitor",
        "index": 101 if platform == "windows" else 102,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
)


class BaseBossLocomotion(Pointer):
    def __init__(self, pointer) -> None:
        # Logger.instance().log_debug("LOCO __init__")
        super().__init__(pointer)
        self.virtuals = []
        self.get_virtual("Update").add_pre_hook(self.pre_update)

    def get_virtual(self, name):
        # Already created?
        for virtual in self.virtuals:
            if virtual["name"] == name:
                return virtual["func"]

        # Create
        for virtual in LOCO_VIRTUALS:
            if virtual["name"] == name:
                # Logger.instance().log_debug(f"LOCO create virtual {name}")
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

    def remove_hooks(self):
        self.get_virtual("Update").remove_pre_hook(self.pre_update)

    # =============================================================================
    # >> VIRTUALS
    # =============================================================================
    def pre_update(self, stack_data):
        if stack_data[0].address != self.address:
            return
        # Logger.instance().log_debug(f"LOCO pre_update")
        foo = 1  # pass cancels function call

    def approach(self, target: Vector, weight: float):
        # Logger.instance().log_debug(f"LOCO approach {target.x} {target.y} {target.z}, weight: {weight}")
        self.get_virtual("Approach").__call__(self, target, weight)

    def drive_to(self, target: Vector):
        # Logger.instance().log_debug(f"LOCO drive_to {target.x} {target.y} {target.z}")
        self.get_virtual("DriveTo").__call__(self, target)

    def run(self):
        self.get_virtual("Run").__call__(self)

    def set_desired_speed(self, value: float):
        # Logger.instance().log_debug(f"LOCO set_desired_speed {value}")
        self.get_virtual("SetDesiredSpeed").__call__(self, value)

    def face_towards(self, target: Vector):
        # Logger.instance().log_debug(f"LOCO face_towards {target.x} {target.y} {target.z}")
        self.get_virtual("FaceTowards").__call__(self, target)

    def get_feet(self) -> Vector:
        pointer = self.get_virtual("GetFeet").__call__(self)
        return make_object(Vector, pointer)

    def is_potentially_traversable(
        self,
        start: Vector,
        end: Vector,
        when: int = 0,
        fraction_ptr: Pointer = 0,
    ) -> bool:
        return self.get_virtual("IsPotentiallyTraversable").__call__(
            self, start, end, when, fraction_ptr
        )

    def stuck_monitor(self):
        self.get_virtual("StuckMonitor").__call__(self)

    def get_ground_speed(self) -> float:
        return self.get_virtual("GetGroundSpeed").__call__(self)

    def get_ground_motion_vector(self) -> Vector:
        data = self.get_virtual("GetGroundMotionVector").__call__(self)
        return make_object(Vector, data)
