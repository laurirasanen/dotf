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
# Source.Python
from engines.trace import engine_trace, Ray, ContentMasks, TraceFilterSimple, GameTrace
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
from mathlib import NULL_VECTOR, Vector, QAngle
from filters.players import PlayerIter

# dotf
from .locomotion import BaseBossLocomotion
from ..log import Logger


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
NBCC_CLASSNAME = "base_boss"
NBCC_SERVER_CLASS = "CTFBaseBoss"
ENTITY_IS_NBCC = lambda entity: entity.classname == NBCC_CLASSNAME

HEAVY_ROBOT_MODEL = "models/bots/heavy/bot_heavy.mdl"

NBCC_VIRTUALS = (
    {
        "name": "Deconstructor",
        "index": 0,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
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
        "index": 66 if PLATFORM == "windows" else 67,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
        ),
        "return": DataType.VOID,
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
        entity.model = Model(HEAVY_ROBOT_MODEL, True, False)
        return NextBotCombatCharacter(entity.index, True)

    def __init__(self, index, caching=True):
        Logger.instance().log_debug("NBCC __init__")
        super().__init__(index, caching)
        self.virtuals = []
        self.locomotor = BaseBossLocomotion(
            self.get_member_pointer("m_locomotor").get_pointer()
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
    def spawn(self, origin: Vector, angles: QAngle):
        Logger.instance().log_debug("NBCC spawn")
        self.origin = origin
        self.angles = angles
        self.set_property_float("m_flModelScale", 0.6)
        self.set_property_int("m_iTeamNum", 2)

        # Spawn!
        self.get_virtual("Spawn").__call__(self)

        # health gets reset in Spawn
        self.max_health = 1000
        self.health = 1000

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
        self.get_virtual("Think").add_pre_hook(self.pre_think)
        self.get_virtual("Event_Killed").add_pre_hook(self.pre_killed)
        self.get_virtual("Deconstructor").add_pre_hook(self.pre_deconstructor)

        # test
        self.target_pos = Vector(0, 0, 0)

    def pre_think(self, stack_data):
        for player in PlayerIter():
            trace = GameTrace()
            engine_trace.trace_ray(
                Ray(
                    player.get_eye_location(),
                    player.get_eye_location() + player.view_vector * 10000.0,
                ),
                ContentMasks.PLAYER_SOLID_BRUSH_ONLY,
                TraceFilterSimple(PlayerIter()),
                trace,
            )
            if trace.did_hit() and trace.entity.index == 0:
                self.target_pos = trace.end_position
            break

        # self.locomotor.set_desired_speed(100.0)
        self.locomotor.run()
        self.locomotor.approach(self.target_pos, 0.1)
        self.locomotor.face_towards(self.target_pos)
        vel = self.get_property_vector("m_vecAbsVelocity")
        if vel.is_zero() == False:
            Logger.instance().log_debug(f"NBCC vel: {vel.x}, {vel.y}, {vel.z}")

    def pre_killed(self, stack_data):
        Logger.instance().log_debug(f"NBCC pre_killed")
        self.locomotor.remove_hooks()
        self.locomotor = None
        self.remove_hooks()

    def pre_deconstructor(self, stack_data):
        # Trying to remove hooks here will crash.
        # Just make sure we don't try to call any
        # garbage pointers in Think after this point.
        self.locomotor = None

    def remove_hooks(self):
        Logger.instance().log_debug(f"NBCC remove_hooks")
        self.get_virtual("Think").remove_pre_hook(self.pre_think)
        self.get_virtual("Event_Killed").remove_pre_hook(self.pre_killed)
        # self.get_virtual("Deconstructor").remove_pre_hook(self.pre_deconstructor)
