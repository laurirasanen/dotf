"""
================================================================
    * core/buildings/sentry.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Sentrygun functionality
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python
from configobj import ConfigObj
from inspect import stack
from pprint import pprint
from engines.trace import engine_trace, Ray, ContentMasks, TraceFilterSimple, GameTrace
from engines.server import engine_server, server
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
from mathlib import NULL_VECTOR, Vector, QAngle
from filters.players import PlayerIter

# dotf
from ..log import Logger
from ..helpers import get_closest_lane, closest_point_on_line_segment, Team
from ..constants.paths import CFG_PATH

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
building_config = ConfigObj(CFG_PATH + "/building_settings.ini")

SENTRY_CLASSNAME = "obj_sentrygun"
SENTRY_TARGET_NAME = "dotf_sentrygun"
SENTRY_SERVER_CLASS = "CObjectSentrygun"

SENTRY_VIRTUALS = (
    {
        "name": "Spawn",
        "index": 22 if PLATFORM == "windows" else 23,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
    {
        "name": "Think",
        "index": 47 if PLATFORM == "windows" else 48,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
    {
        "name": "Event_Killed",
        "index": 67 if PLATFORM == "windows" else 66,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
        ),
        "return": DataType.VOID,
    },
    {
        "name": "ChangeTeam",
        "index": 92 if PLATFORM == "windows" else 91,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.INT,
        ),
        "return": DataType.VOID,
    },
    {
        "name": "Activate",
        "index": 33 if PLATFORM == "windows" else 34,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
    {
        "name": "InitializeMapPlacedObject",
        "index": 374 if PLATFORM == "windows" else 376,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
)

SENTRY_MEMBERS = (
    {
        "name": "m_flSentryRange",
        "type": "float",
        "relative": "m_bPlayerControlled",
        "offset": 4,
        "reverse": True,
    },
    {
        "name": "m_nDefaultUpgradeLevel",
        "type": "int",
        "relative": "m_iHighestUpgradeLevel",
        "offset": 4,
    },
)


class Sentry(Entity):
    @staticmethod
    def create():
        Logger.instance().log_debug("Sentry create")
        entity = Entity.create(SENTRY_CLASSNAME)
        entity.target_name = SENTRY_TARGET_NAME
        return Sentry(entity.index)

    def __init__(self, index, caching=True):
        Logger.instance().log_debug("Sentry __init__")
        super().__init__(index, caching)
        self.virtuals = []

    def get_member_pointer(self, name):
        for member in SENTRY_MEMBERS:
            if member["name"] == name:
                for networked in self.server_class.find_server_class(
                    SENTRY_SERVER_CLASS
                ).table:
                    if networked.name == member["relative"]:
                        if member["reverse"] != None:
                            return Pointer(
                                self.pointer + networked.offset - member["offset"]
                            )
                        return Pointer(
                            self.pointer + networked.offset + member["offset"]
                        )

        return None

    def get_virtual(self, name):
        # Already created?
        for virtual in self.virtuals:
            if virtual["name"] == name:
                return virtual["func"]

        # Create
        for virtual in SENTRY_VIRTUALS:
            if virtual["name"] == name:
                Logger.instance().log_debug(f"NBCC create virtual {name}")
                func = get_object_pointer(self).make_virtual_function(
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
    def spawn(self, origin: Vector, angles: QAngle, team: Team, lane: int, tier: int):
        Logger.instance().log_debug("Sentry spawn")

        trace = GameTrace()
        engine_trace.trace_ray(
            Ray(
                origin,
                origin + Vector(0, 0, -1000.0),
            ),
            ContentMasks.SOLID_BRUSH_ONLY,
            TraceFilterSimple(PlayerIter()),
            trace,
        )
        if trace.did_hit() and trace.entity.index == 0:
            origin = trace.end_position

        self.origin = origin
        self.angles = angles
        self.lane = lane
        self.tier = tier
        self.team = team
        self.config = building_config["sentry"][f"{self.tier}"]

        # Spawn!
        self.get_virtual("Spawn").__call__(self)

        self.set_property_int("m_iTeamNum", self.team)

        self.get_virtual("Activate").__call__(self)

        # health gets reset in Spawn
        self.set_property_int("m_iMaxHealth", self.config.as_int("health"))
        self.call_input(
            "SetHealth", self.config.as_int("health")
        )  # Buildings do weird stuff with health

        # set level and prevent upgrades
        self.set_property_int("m_iUpgradeLevel", self.tier)
        self.set_property_int("m_iHighestUpgradeLevel", self.tier)

        # this prevents repairing
        self.set_property_bool("m_bDisposableBuilding", True)

        # Test
        for member in SENTRY_MEMBERS:
            pointer = self.get_member_pointer(member["name"])
            if pointer is None:
                Logger.instance().log_debug(f"  {member['name']}: NOT FOUND")
            elif member["type"] == "bool":
                Logger.instance().log_debug(f"  {member['name']}: {pointer.get_bool()}")
            elif member["type"] == "int":
                Logger.instance().log_debug(f"  {member['name']}: {pointer.get_int()}")
            elif member["type"] == "float":
                Logger.instance().log_debug(
                    f"  {member['name']}: {pointer.get_float()}"
                )
            elif member["type"] == "pointer":
                Logger.instance().log_debug(
                    f"  {member['name']}: {pointer.get_pointer()}"
                )

        # Setup hooks
        self.get_virtual("Event_Killed").add_pre_hook(self.pre_killed)

    def pre_killed(self, stack_data):
        if stack_data[0].address != get_object_pointer(self).address:
            return

        # For some reason this gets called when
        # the sentry takes damage for the first time.
        if self.get_property_int("m_iHealth") > 0:
            return

        self.remove_hooks()

    def set_range(self):
        self.get_member_pointer("m_flSentryRange").set_float(
            self.config.as_float("range")
        )

    def remove_hooks(self):
        Logger.instance().log_debug(f"Sentry remove_hooks")
        self.get_virtual("Event_Killed").remove_pre_hook(self.pre_killed)

    def get_damage(self):
        return self.config.as_float("damage")

    def tick(self):
        # Refill ammo
        if self.tier == 0:
            self.set_property_int("m_iAmmoShells", 150)
        elif self.tier == 1:
            self.set_property_int("m_iAmmoShells", 200)
        elif self.tier == 2:
            self.set_property_int("m_iAmmoShells", 200)
            self.set_property_int("m_iAmmoRockets", 20)
