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
from core import PLATFORM, get_interface
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
BA_SERVER_CLASS = "CBaseAnimating"
ENTITY_IS_NBCC = lambda entity: entity.classname == NBCC_CLASSNAME

NBCC_VIRTUALS = (
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
        "name": "SetModel",
        "index": 24 if PLATFORM == "windows" else 25,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.STRING,
        ),
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
    {
        "name": "StudioFrameAdvance",
        "index": 194 if PLATFORM == "windows" else 195,
        "convention": Convention.THISCALL,
        "args": (DataType.POINTER,),
        "return": DataType.VOID,
    },
    {
        "name": "SetSequence",
        "index": 195 if PLATFORM == "windows" else 196,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.INT,
        ),
        "return": DataType.POINTER,
    },
    {
        "name": "DispatchAnimEvents",
        "index": 206 if PLATFORM == "windows" else 207,
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
        ),
        "return": DataType.VOID,
    },
    {
        "name": "LookupSequence",
        "signature": ""
        if PLATFORM == "windows"
        else "_ZN14CBaseAnimating14LookupSequenceEPKc",
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.STRING,
        ),
        "return": DataType.INT,
    },
    {
        "name": "ResetSequence",
        "signature": ""
        if PLATFORM == "windows"
        else "_ZN14CBaseAnimating13ResetSequenceEi",
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.INT,
        ),
        "return": DataType.VOID,
    },
    {
        "name": "LookupPoseParameter",
        "signature": ""
        if PLATFORM == "windows"
        else "_ZN14CBaseAnimating19LookupPoseParameterEP10CStudioHdrPKc",
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
            DataType.STRING,
        ),
        "return": DataType.INT,
    },
    {
        "name": "SetPoseParameter",
        "signature": ""
        if PLATFORM == "windows"
        else "_ZN14CBaseAnimating16SetPoseParameterEP10CStudioHdrPKcf",
        "convention": Convention.THISCALL,
        "args": (
            DataType.POINTER,
            DataType.POINTER,
            DataType.STRING,
            DataType.FLOAT,
        ),
        "return": DataType.FLOAT,
    },
)

# Non-networked members relative to a CNetworkVar pointer
NBCC_MEMBERS = (
    {
        "name": "m_speed",
        "relative": "m_lastHealthPercentage",
        "offset": 8,
    },
    {
        "name": "m_startDisabled",
        "relative": "m_lastHealthPercentage",
        "offset": 12,
    },
    {
        "name": "m_isEnabled",
        "relative": "m_lastHealthPercentage",
        "offset": 16,
    },
    {
        "name": "m_damagePoseParameter",
        "relative": "m_lastHealthPercentage",
        "offset": 20,
    },
    {
        "name": "m_currencyValue",
        "relative": "m_lastHealthPercentage",
        "offset": 24,
    },
    {
        "name": "m_bResolvePlayerCollisions",
        "relative": "m_lastHealthPercentage",
        "offset": 28,
    },
    {
        "name": "m_locomotor",
        "relative": "m_lastHealthPercentage",
        "offset": 32,
    },
    {
        "name": "m_pStudioHdr",
        "relative": "m_flFadeScale",
        "offset": 28,
        "server_class": BA_SERVER_CLASS,
    },
)


class NextBotCombatCharacter(Entity):
    @staticmethod
    def create():
        # Logger.instance().log_debug("NBCC create")
        entity = Entity.create(NBCC_CLASSNAME)
        return NextBotCombatCharacter(entity.index)

    def __init__(self, index, caching=False):
        # Logger.instance().log_debug("NBCC __init__")
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
                sc = NBCC_SERVER_CLASS
                if "server_class" in member:
                    sc = member["server_class"]
                for networked in self.server_class.find_server_class(sc).table:
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
                if "index" in virtual:
                    # Logger.instance().log_debug(f"NBCC create virtual function {name}")
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
                elif "signature" in virtual:
                    # Logger.instance().log_debug(
                    #     f"NBCC create non-virtual function {name}"
                    # )
                    binary = find_binary("server_srv", False)
                    address = binary.find_address(virtual["signature"])
                    func = address.make_function(
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
        Logger.instance().log_debug(f"NBCC function {name} not found")
        return None

    # =============================================================================
    # >> VIRTUALS
    # =============================================================================
    def spawn(self, origin: Vector, angles: QAngle, team: Team, bot_type: BotType):
        self.origin = origin
        # this messes up animations somehow
        # self.angles = angles
        self.team = team
        self.bot_type = bot_type
        self.target_pos = origin
        # Logger.instance().log_debug("NBCC spawn")

        self.config = (
            bot_config["bot_melee"]
            if self.bot_type == BotType.MELEE
            else bot_config["bot_ranged"]
        )

        self.model = Model(self.config["model"], True, False)
        self.set_property_float("m_flModelScale", self.config.as_float("model_scale"))
        self.set_property_bool("m_bClientSideAnimation", True)
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

        self.set_animation(self.config["model_anim_move"])

        # Setup hooks
        self.get_virtual("Event_Killed").add_pre_hook(self.pre_killed)
        # self.get_virtual("OnTakeDamage").add_pre_hook(self.pre_take_damage)

    def set_animation(self, anim):
        seq = self.get_virtual("LookupSequence").__call__(self, anim)
        self.get_virtual("ResetSequence").__call__(self, seq)

    def get_studio_model_ptr(self):
        studio_model = self.get_member_pointer("m_pStudioHdr")
        if studio_model is None:
            Logger.instance().log_debug(f"No studio model")
            return

        return studio_model.get_pointer()

    def set_pose_param(self, param, value):
        model_ptr = self.get_studio_model_ptr()
        if model_ptr is None:
            return None

        return self.get_virtual("SetPoseParameter").__call__(
            self, model_ptr, param, value
        )

    def pre_killed(self, stack_data):
        if stack_data[0].address != get_object_pointer(self).address:
            return

        # Logger.instance().log_debug(f"NBCC pre_killed")
        self.remove_hooks()

    # def pre_take_damage(self, stack_data):
    #     if stack_data[0].address != get_object_pointer(self).address:
    #         return

    #     Logger.instance().log_debug(f"NBCC pre_take_damage")
    #     pprint(make_object(TakeDamageInfo, stack_data[1]))

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
        self.locomotor.stuck_monitor()
        self.locomotor.approach(self.target_pos, 0.1)
        self.locomotor.face_towards(self.target_pos)

        # anim params
        expected_speed = float(self.config.as_float("move_speed"))
        if expected_speed != 0:
            movement = self.locomotor.get_ground_motion_vector()
            forward = Vector()
            right = Vector()
            self.angles.get_angle_vectors(forward, right)
            ground_speed = self.locomotor.get_ground_speed()
            frac = ground_speed / expected_speed
            # FIXME: why are animation params so fucked?
            # multiplying dot here with anything other than
            # a const val just breaks animations...
            # f_val = min(1.0, movement.dot(forward) * frac)
            # r_val = min(1.0, movement.dot(right) * frac)
            self.set_pose_param("move_x", movement.dot(forward))
            self.set_pose_param("move_y", movement.dot(right))
            if self.bot_type == BotType.RANGED:
                self.set_pose_param("move_scale", 1.0)
                # self.set_pose_param("move_scale", min(1.0, frac))
            self.set_property_float("m_flPlaybackRate", frac)
            # self.set_property_float("m_flPlaybackRate", max(1.0, frac))

        self.get_virtual("StudioFrameAdvance").__call__(self)
        self.get_virtual("DispatchAnimEvents").__call__(self, self)

    def remove_hooks(self):
        # Logger.instance().log_debug(f"NBCC remove_hooks")
        if self.locomotor is not None:
            self.locomotor.remove_hooks()
            self.locomotor = None
        if self.interface is not None:
            self.interface.remove_hooks()
            self.interface = None
        self.get_virtual("Event_Killed").remove_pre_hook(self.pre_killed)
        # self.get_virtual("OnTakeDamage").remove_pre_hook(self.pre_take_damage)
