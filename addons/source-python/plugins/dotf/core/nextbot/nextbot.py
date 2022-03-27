"""
================================================================
    * core/nextbot/nextbot.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    ...
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python
from configobj import ConfigObj

# Source.Python
from inspect import stack
from pprint import pprint
from engines.trace import engine_trace, Ray, ContentMasks, TraceFilterSimple, GameTrace
from engines.server import engine_server, server
from engines.precache import Model
from core import PLATFORM
from entities import TakeDamageInfo
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
from .locomotion import BaseBossLocomotion
from .interface import NextBotInterface
from ..log import Logger
from ..helpers import get_closest_lane, closest_point_on_line_segment, Team, BotType
from ..constants import CFG_PATH


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
bot_config = ConfigObj(CFG_PATH + "/bot_settings.ini")

NBCC_CLASSNAME = "base_boss"
NBCC_SERVER_CLASS = "CTFBaseBoss"
ENTITY_IS_NBCC = lambda entity: entity.classname == NBCC_CLASSNAME

NBCC_VIRTUALS = (
    {
        "name": "Deconstructor",
        "index": 0,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
    {
        "name": "GetBaseEntity",
        "index": 5 if PLATFORM == "windows" else 6,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.POINTER,
    },
    {
        "name": "Spawn",
        "index": 22 if PLATFORM == "windows" else 23,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
    {
        "name": "OnTakeDamage",
        "index": 63 if PLATFORM == "windows" else 62,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
        ),
        "return": DataType.VOID,
    },
    {
        "name": "Event_Killed",
        "index": 66 if PLATFORM == "windows" else 67,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
        ),
        "return": DataType.VOID,
    },
    {
        "name": "MyNextBotPointer",
        "index": 72 if PLATFORM == "windows" else 73,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.POINTER,
    },
)

# Non-networked members relative to a CNetworkVar pointer
NBCC_MEMBERS = (
    {
        "name": "m_speed",
        "type": "float",
        "relative": "m_lastHealthPercentage",
        "offset": 8,
    },
    {
        "name": "m_startDisabled",
        "type": "int",
        "relative": "m_lastHealthPercentage",
        "offset": 12,
    },
    {
        "name": "m_isEnabled",
        "type": "bool",
        "relative": "m_lastHealthPercentage",
        "offset": 16,
    },
    {
        "name": "m_damagePoseParameter",
        "type": "int",
        "relative": "m_lastHealthPercentage",
        "offset": 20,
    },
    {
        "name": "m_currencyValue",
        "type": "int",
        "relative": "m_lastHealthPercentage",
        "offset": 24,
    },
    {
        "name": "m_bResolvePlayerCollisions",
        "type": "bool",
        "relative": "m_lastHealthPercentage",
        "offset": 28,
    },
    {
        "name": "m_locomotor",
        "type": "pointer",
        "relative": "m_lastHealthPercentage",
        "offset": 32,
    },
)


class NextBotCombatCharacter(Entity):
    @staticmethod
    def create():
        Logger.instance().log_debug("NBCC create")
        entity = Entity.create(NBCC_CLASSNAME)
        return NextBotCombatCharacter(entity.index)

    def __init__(self, index, caching=False):
        Logger.instance().log_debug("NBCC __init__")
        super().__init__(index, caching)
        self.virtuals = []
        self.locomotor = BaseBossLocomotion(
            self.get_member_pointer("m_locomotor").get_pointer()
        )
        self.interface = NextBotInterface(
            self.get_virtual("MyNextBotPointer").__call__(self), self.update
        )

    def get_member_pointer(self, name):
        for member in NBCC_MEMBERS:
            if member["name"] == name:
                for networked in self.server_class.find_server_class(
                    NBCC_SERVER_CLASS
                ).table:
                    if networked.name == member["relative"]:
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
        for virtual in NBCC_VIRTUALS:
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
    def spawn(self, origin: Vector, angles: QAngle, team: Team, bot_type: BotType):
        self.origin = origin
        self.angles = angles
        self.team = team
        self.bot_type = bot_type
        Logger.instance().log_debug("NBCC spawn")

        self.config = (
            bot_config["bot_melee"]
            if self.bot_type == BotType.MELEE
            else bot_config["bot_ranged"]
        )

        self.model = Model(self.config["model"], True, False)
        self.set_property_float("m_flModelScale", self.config.as_float("model_scale"))
        self.set_property_int("m_iTeamNum", self.team)
        self.set_property_int(
            "m_nSkin",
            self.config.as_int("model_skin_blu")
            if self.team == Team.BLU
            else self.config.as_int("model_skin_red"),
        )

        # Spawn!
        self.get_virtual("Spawn").__call__(self)

        # health gets reset in Spawn
        self.max_health = self.config.as_int("health")
        self.health = self.config.as_int("health")

        self.target_pos = origin

        # Test
        for member in NBCC_MEMBERS:
            pointer = self.get_member_pointer(member["name"])
            if member["type"] == "bool":
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
        self.get_virtual("OnTakeDamage").add_pre_hook(self.pre_take_damage)

    def pre_killed(self, stack_data):
        if stack_data[0].address != get_object_pointer(self).address:
            return

        Logger.instance().log_debug(f"NBCC pre_killed")
        self.remove_hooks()

    def pre_take_damage(self, stack_data):
        if stack_data[0].address != get_object_pointer(self).address:
            return

        Logger.instance().log_debug(f"NBCC pre_take_damage")
        pprint(make_object(TakeDamageInfo, stack_data[1]))

    def update(self):
        # Called right before INextBot::Update from interface.py.

        # If no aggro, navigate along lane, or back to the lane if not on it
        start, end = get_closest_lane(self.origin, self.team)
        line = end - start

        closest_point = closest_point_on_line_segment(start, end, self.origin)
        margin = 32.0

        # At least margin away from the lane, just move to closest point
        if closest_point.get_distance(self.origin) > margin:
            self.target_pos = closest_point
        # We are on the lane, move towards end
        else:
            self.target_pos = end + line.normalized() * 10.0

        self.locomotor.set_desired_speed(self.config.as_float("move_speed"))
        self.get_member_pointer("m_speed").set_float(self.config.as_float("move_speed"))
        self.locomotor.approach(self.target_pos, 0.1)
        self.locomotor.face_towards(self.target_pos)

    def remove_hooks(self):
        Logger.instance().log_debug(f"NBCC remove_hooks")
        if self.locomotor is not None:
            self.locomotor.remove_hooks()
            self.locomotor = None
        if self.interface is not None:
            self.interface.remove_hooks()
            self.interface = None
        self.get_virtual("Event_Killed").remove_pre_hook(self.pre_killed)
        self.get_virtual("OnTakeDamage").remove_pre_hook(self.pre_take_damage)
