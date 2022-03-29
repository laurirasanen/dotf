"""
================================================================
    * core/nextbot/interface.py
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
INB_VIRTUALS = (
    {
        "name": "Update",
        "index": 43 if platform == "windows" else 44,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
)


class NextBotInterface(Pointer):
    def __init__(self, pointer, update_cb) -> None:
        # Logger.instance().log_debug("iNB __init__")
        super().__init__(pointer)
        self.virtuals = []
        self.update_cb = update_cb
        self.get_virtual("Update").add_pre_hook(self.pre_update)

    def get_virtual(self, name):
        # Already created?
        for virtual in self.virtuals:
            if virtual["name"] == name:
                return virtual["func"]

        # Create
        for virtual in INB_VIRTUALS:
            if virtual["name"] == name:
                # Logger.instance().log_debug(f"iNB create virtual {name}")
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
        self.update_cb()
