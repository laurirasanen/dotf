"""
================================================================
    * core/hooks.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Module for hooking in-game events.
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python
import os
from threading import Thread
import re
from configobj import ConfigObj

# Source.Python
from listeners import (
    OnTick,
    OnClientActive,
    OnClientDisconnect,
    OnLevelInit,
    OnLevelEnd,
)
from entities import TakeDamageInfo
from entities.hooks import EntityPreHook, EntityPostHook, EntityCondition
from entities.entity import Entity
from events import Event
from events.hooks import PreEvent, EventAction
from mathlib import NULL_VECTOR
from players.helpers import playerinfo_from_index, userid_from_index
from players.entity import Player
from steam import SteamID
from cvars import ConVar
from effects.base import TempEntity
from engines.server import server, engine_server
from engines.sound import engine_sound
from memory import (
    DataType,
    Convention,
    get_object_pointer,
    get_virtual_function,
    make_object,
)
from memory.hooks import PreHook
from messages.hooks import HookUserMessage
from filters.recipients import RecipientFilter
from weapons.entity import Weapon

# dotf
from .bot.botmanager import BotManager
from .player.usermanager import UserManager
from .map.mapmanager import MapManager
from .player.user import User
from .commands.clientcommands import CommandHandler
from .commands.clientcommands import CommandHandler
from .constants import CFG_PATH
from .chat.messages import message_class_banned

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
player_config = ConfigObj(CFG_PATH + "/player_settings.ini")

emit_sound_offset = 4 if os.name == "nt" else 5

""" CEngineSoundServer::EmitSound(
        IRecipientFilter&,
        int,
        int,
        char const*,
        float,
        soundlevel_t,
        int,
        int,
        int,
        Vector const*,
        Vector const*,
        CUtlVector<Vector, CUtlMemory<Vector, int> >*,
        bool,
        float,
        int
    )"""

EMIT_SOUND_FUNC = get_object_pointer(engine_sound).make_virtual_function(
    emit_sound_offset,
    Convention.THISCALL,
    (
        DataType.POINTER,  # this pointer
        DataType.POINTER,
        DataType.INT,
        DataType.INT,
        DataType.STRING,
        DataType.FLOAT,
        DataType.USHORT,
        DataType.INT,
        DataType.INT,
        DataType.INT,
        DataType.POINTER,
        DataType.POINTER,
        DataType.POINTER,
        DataType.BOOL,
        DataType.FLOAT,
        DataType.INT,
    ),
    DataType.VOID,
)

blocked_sounds = []

blocked_temp_entities = []

engine_sound.precache_sound("vo/null.wav")

# =============================================================================
# >> LISTENERS
# =============================================================================
@OnLevelInit
def on_level_init(level):
    """Called when a new map is loaded."""
    UserManager.instance().add_all()
    MapManager.instance().on_load_map()


@OnLevelEnd
def on_level_end():
    """Called when a map is unloaded."""
    UserManager.instance().clear()
    BotManager.instance().clear()


@OnTick
def on_tick():
    """Called every engine tick."""
    BotManager.instance().tick()
    UserManager.instance().tick()


@OnClientActive
def on_client_active(index):
    """Called when a client has fully joined the game."""
    info = playerinfo_from_index(index)
    player = Player.from_userid(info.userid)
    if not player.is_bot():
        UserManager.instance().add_user(User(player))


@OnClientDisconnect
def on_client_disconnect(index):
    """Called when a client leaves the game."""
    user = UserManager.instance().user_from_index(index)
    if user != None:
        UserManager.instance().remove_user(user)


# =============================================================================
# >> PRE-HOOKS
# =============================================================================
@PreEvent("player_death")
def pre_player_death(event):
    """Called before a player dies."""
    pass


@PreEvent("player_team")
def pre_player_team(event):
    """Called before a player joins a team."""
    # Don't broadcast to other players.
    return EventAction.STOP_BROADCAST


@PreEvent("building_healed")
def pre_building_healed(event):
    # TODO: engineer tower heal
    pass


@PreEvent("player_healed")
def on_player_healed(event):
    patient = Player.from_userid(event["patient"])
    healer_idx = event["healer"]
    healer = None

    # Default heal multiplier if we don't know what to do
    default_mult = 0.2

    if healer_idx == 0:
        # World or server
        event["amount"] = int(event["amount"] * default_mult)
        return EventAction.CONTINUE
    else:
        # Some other entity
        try:
            healer = Player.from_userid(healer_idx)
        except ValueError:
            # Not a player, try to get player from owner
            try:
                owner_handle = Entity(healer_idx).owner_handle
                healer = Player.from_inthandle(owner_handle)
            except (ValueError, OverflowError):
                # Not a player or invalid handle
                event["amount"] = int(event["amount"] * default_mult)
                return EventAction.CONTINUE

    heal_multiplier = 1.0

    if healer != None:
        # Handle player healer
        player_healer = UserManager.instance().user_from_index(healer.index)
        if player_healer != None:
            heal_multiplier *= player_healer.class_settings.as_float("heal_deal_mult")

        # Handle bot healer
        bot_healer = BotManager.instance().bot_from_index(healer.index)
        if bot_healer != None:
            heal_multiplier *= 1.0

    # Handle player patient
    player_patient = UserManager.instance().user_from_index(patient.index)
    if player_patient != None:
        heal_multiplier *= player_patient.class_settings.as_float("heal_take_mult")

    # Handle bot patient
    bot_patient = BotManager.instance().bot_from_index(patient.index)
    if bot_patient != None:
        heal_multiplier *= 1.0

    if heal_multiplier != 1.0:
        event["amount"] = int(event["amount"] * heal_multiplier)

    return EventAction.CONTINUE


@PreEvent("player_changeclass")
def pre_player_changeclass(event):
    player = Player.from_userid(event["userid"])
    human_player = UserManager.instance().user_from_index(player.index)
    if human_player != None:
        for ban in player_config["class_settings"].as_list("banned_classes"):
            if f"{event['class']}" == ban:
                player.set_property_uchar("m_PlayerClass.m_iClass", 1)
                player.set_property_uchar("m_Shared.m_iDesiredPlayerClass", 1)
                message_class_banned.send(player.index)
                return EventAction.BLOCK


@EntityPreHook(EntityCondition.is_player, "on_take_damage_alive")
def pre_take_damage_alive_player(args):
    info = make_object(TakeDamageInfo, args[1])
    victim = make_object(Player, args[0])
    attacker = None

    # Default damage multiplier if we don't know what to do
    default_mult = 0.2

    if info.attacker == 0:
        # World
        info.base_damage *= default_mult
        info.damage *= default_mult
        return
    else:
        # Some other entity
        try:
            attacker = Player.from_userid(userid_from_index(info.attacker))
        except ValueError:
            # Not a player, try to get player from owner
            try:
                owner_handle = Entity(info.inflictor).owner_handle
                attacker = Player.from_inthandle(owner_handle)
            except (ValueError, OverflowError):
                # Not a player or invalid handle
                info.base_damage *= default_mult
                info.damage *= default_mult
                return

    # Handle bot attacker
    attacker_bot = BotManager.instance().bot_from_index(attacker.index)
    if attacker_bot != None:
        info.base_damage = attacker_bot.config.as_float("damage")
        info.damage = attacker_bot.config.as_float("damage")

    # Handle player attacker
    attacker_player = UserManager.instance().user_from_index(attacker.index)
    if attacker_player != None:
        info.base_damage *= attacker_player.class_settings.as_float("damage_deal_mult")
        info.damage *= attacker_player.class_settings.as_float("damage_deal_mult")

    # Handle bot victim
    victim_bot = BotManager.instance().bot_from_index(victim.index)
    if victim_bot != None:
        # don't throw bots around
        # FIXME
        info.force = NULL_VECTOR

    # Handle player victim
    victim_player = UserManager.instance().user_from_index(victim.index)
    if victim_player != None:
        info.base_damage *= victim_player.class_settings.as_float("damage_take_mult")
        info.damage *= victim_player.class_settings.as_float("damage_take_mult")


@EntityPreHook(EntityCondition.is_player, "get_max_health")
def pre_get_max_health_player(args):
    player = make_object(Player, args[0])

    human_player = UserManager.instance().user_from_index(player.index)
    if human_player != None:
        return human_player.get_max_health()

    bot_player = BotManager.instance().bot_from_index(player.index)
    if bot_player != None:
        return bot_player.get_max_health()


# =============================================================================
# >> HOOKS
# =============================================================================
@Event("player_spawn")
def on_player_spawn(event):
    """Called when a player spawns."""
    cancel_wait = ConVar(name="mp_waitingforplayers_cancel")
    cancel_wait.set_bool(True)

    player = Player.from_userid(event["userid"])
    BotManager.instance().on_spawn(player.index)
    UserManager.instance().on_spawn(player.index)


@Event("player_death")
def on_player_death(event):
    """Called when a player dies."""
    player = Player.from_userid(event["userid"])
    BotManager.instance().on_death(player.index)


# =============================================================================
# >> VIRTUAL FUNCTIONS
# =============================================================================
@PreHook(EMIT_SOUND_FUNC)
def pre_emit_sound(args):
    """Called before a sound is emitted."""

    sound_file = args[4]

    for sound in blocked_sounds:
        regex = re.compile(sound)
        if re.match(regex, sound_file):
            return 0


@PreHook(get_virtual_function(engine_server, "PlaybackTempEntity"))
def pre_playback_temp_entity(args):
    """Called before a temp entity is created."""

    te = TempEntity(args[3])

    if te.name in blocked_temp_entities:
        return 0


# =============================================================================
# >> USER MESSAGE HOOKS
# =============================================================================
@HookUserMessage("SayText2")
def saytext2_hook(recipient, data):
    """Hook SayText2 for commands and hidechat.
    This is called once for every recipient."""

    # Server
    if data["index"] == 0:
        return

    # TODO:
    # get index from RecipientList?
    receiving_player = list(recipient)[0]
    sending_player = data["index"]

    # Handle commands
    if (
        receiving_player == sending_player
        and len(data["param2"]) > 1
        and data["param2"][0] in CommandHandler.instance().prefix
    ):
        recipient.update([])
        command_response = CommandHandler.instance().check_command(
            data["param2"][1:], UserManager.instance().user_from_index(sending_player)
        )
        if command_response:
            data["message"] = command_response
            data["index"] = 0
            recipient.update([sending_player])
