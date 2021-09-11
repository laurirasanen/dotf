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


# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
NBCC_CLASSNAME = "base_boss"
NBCC_SERVER_CLASS = "CTFBaseBoss"
ENTITY_IS_NBCC = lambda entity: entity.classname == NBCC_CLASSNAME

HEAVY_ROBOT_MODEL = "models/bots/heavy/bot_heavy.mdl"

NBCC_VIRTUALS = (
    {
        "name": "Spawn",
        "index": 22 if PLATFORM == "windows" else 23,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
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
        print("NBCC create")
        entity = Entity.create(NBCC_CLASSNAME)
        entity.model = Model(HEAVY_ROBOT_MODEL, True, False)
        return NextBotCombatCharacter(entity.index, True)

    def __init__(self, index, caching=True):
        print("NBCC __init__")
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
        print("NBCC spawn")
        self.origin = origin
        self.angles = angles
        self.set_property_float("m_flModelScale", 0.6)

        # Spawn!
        self.get_virtual("Spawn").__call__(self)

        # health gets reset in Spawn
        self.max_health = 1000
        self.health = 1000

        # Test
        for member in NBCC_MEMBERS:
            pointer = self.get_member_pointer(member["name"])
            if member["type"] == "bool":
                print(f"{member['name']}: {pointer.get_bool()}")
            elif member["type"] == "int":
                print(f"{member['name']}: {pointer.get_int()}")
            elif member["type"] == "float":
                print(f"{member['name']}: {pointer.get_float()}")
            elif member["type"] == "pointer":
                print(f"{member['name']}: {pointer.get_pointer()}")

        target = NULL_VECTOR
        for player in PlayerIter():
            target = player.origin
            break
        self.locomotor.face_towards(target)
