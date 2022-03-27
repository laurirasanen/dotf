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
from core import PLATFORM
from entities import entity
from listeners import (
    OnTick,
    OnClientActive,
    OnClientDisconnect,
    OnLevelInit,
    OnLevelEnd,
    OnServerActivate,
    OnEntitySpawned,
    OnNetworkedEntitySpawned,
)
from entities import TakeDamageInfo
from entities.hooks import EntityPreHook, EntityPostHook, EntityCondition
from entities.entity import Entity
from entities.helpers import baseentity_from_index
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
    Pointer,
    Convention,
    get_object_pointer,
    get_virtual_function,
    make_object,
    find_binary,
)
from memory.hooks import PreHook
from messages.hooks import HookUserMessage
from filters.recipients import RecipientFilter
from weapons.entity import Weapon

# dotf
from .game.gamemanager import GameManager
from .bot.botmanager import BotManager
from .player.usermanager import UserManager
from .map.mapmanager import MapManager
from .buildings.buildingmanager import BuildingManager
from .player.user import User
from .commands.clientcommands import CommandHandler
from .commands.clientcommands import CommandHandler
from .constants import CFG_PATH
from .chat.messages import message_class_banned
from .log import Logger

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
player_config = ConfigObj(CFG_PATH + "/player_settings.ini")

server_binary = find_binary("tf/bin/server")

if PLATFORM == "windows":
    # Look for Building_Sentrygun strings in CObjectSentrygun::SentryRotate,
    # same function has call to CObjectSentrygun::FindTarget and early return.
    # TODO: move to sentry.py
    sentrygun_find_target_sig = b"\x55\x8B\xEC\x81\xEC\xC8\x00\x00\x00\x56\x57\x8B\xF9"
    emit_sound_offset = 4
    get_max_health_offset = 117
else:
    sentrygun_find_target_sig = "_ZN16CObjectSentrygun10FindTargetEv"
    emit_sound_offset = 5
    get_max_health_offset = 118

# bool CObjectSentrygun::FindTarget()
sentrygun_find_target = server_binary[sentrygun_find_target_sig].make_function(
    Convention.THISCALL, (DataType.POINTER,), DataType.BOOL
)

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
@OnServerActivate
def on_server_activate(edicts, edict_count, max_clients):
    """Called when a new map is loaded."""
    GameManager.instance().reset()
    GameManager.instance().load()


@Event("round_end")
def on_round_end(message, reason, winner):
    GameManager.instance().reset()


@Event("round_start")
def on_round_start(fraglimit, objective, timelimit):
    GameManager.instance().reset()
    GameManager.instance().load()


@OnLevelInit
def on_level_init(level):
    """Called when a new map is loaded."""
    pass


@OnLevelEnd
def on_level_end():
    """Called when a map is unloaded."""
    GameManager.instance().reset()


@OnTick
def on_tick():
    """Called every engine tick."""
    GameManager.instance().tick()
    BotManager.instance().tick()
    UserManager.instance().tick()
    BuildingManager.instance().tick()


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


# @OnEntitySpawned
# def on_entity_spawned(entity):
#     Logger.instance().log_debug(f"entity_spawned: {entity.classname}")


# @OnNetworkedEntitySpawned
# def on_networked_entity_spawned(entity):
#     Logger.instance().log_debug(f"networked_entity_spawned: {entity.classname}")


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
    # TODO: engineer tower heal?
    # blocked by m_bDisposableBuilding
    pass


@PreEvent("object_destroyed")
def pre_object_destroyed(event):
    if event["was_building"]:
        BuildingManager.instance().on_building_destroy(event["index"])


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


@EntityPreHook(lambda ent: ent.classname == "base_boss", "on_take_damage")
def pre_take_damage_bot(args):
    pre_take_damage(args)


@EntityPreHook(lambda ent: ent.classname == "obj_sentrygun", "on_take_damage")
def pre_take_damage_sentry(args):
    pre_take_damage(args)


@EntityPreHook(
    # FIXME
    # lambda ent: ent.classname in ["obj_sentrygun", "player", "base_boss"],
    lambda ent: ent.classname == "player",
    "on_take_damage",
)
def pre_take_damage(args):
    victim = make_object(Entity, args[0])
    info = make_object(TakeDamageInfo, args[1])

    # Default damage multiplier if we don't know what to do
    default_mult = 0.2

    # Get attacker
    if info.attacker == 0:
        # World
        info.base_damage *= default_mult
        info.damage *= default_mult
        return
    elif info.inflictor > 0:
        try:
            # Owner
            owner_handle = Entity(info.inflictor).owner_handle

            # Level 3 sentry rockets need to get owner twice
            # rocket -> sentry -> player
            try:
                second_owner_handle = Entity.from_inthandle(owner_handle).owner_handle
                owner_handle = second_owner_handle
            except (ValueError, OverflowError):
                pass

            attacker = Entity.from_inthandle(owner_handle)
            info.attacker = attacker.index
        except (ValueError, OverflowError):
            pass

    # Handle attacker
    attacker_bot = BotManager.instance().bot_from_index(info.attacker)
    attacker_player = UserManager.instance().user_from_index(info.attacker)
    attacker_sentry = BuildingManager.instance().sentry_from_index(info.attacker)

    if attacker_bot != None:
        info.base_damage = attacker_bot.config.as_float("damage")
        info.damage = attacker_bot.config.as_float("damage")
    elif attacker_player != None:
        info.base_damage *= attacker_player.class_settings.as_float("damage_deal_mult")
        info.damage *= attacker_player.class_settings.as_float("damage_deal_mult")
    elif attacker_sentry != None:
        info.base_damage = attacker_sentry.get_damage()
        info.damage = attacker_sentry.get_damage()

    # Handle victim
    victim_player = UserManager.instance().user_from_index(victim.index)

    if victim_player != None:
        info.base_damage *= victim_player.class_settings.as_float("damage_take_mult")
        info.damage *= victim_player.class_settings.as_float("damage_take_mult")

    # print(
    #     f"ab: {attacker_bot}, ap: {attacker_player}, as: {attacker_sentry}, vp: {victim_player}"
    # )


@EntityPreHook(
    EntityCondition.is_player,
    lambda ent: get_object_pointer(ent).make_virtual_function(
        get_max_health_offset,
        Convention.THISCALL,
        (DataType.POINTER,),
        DataType.INT,
    ),
)
def pre_get_max_health_player(args):
    player = make_object(Player, args[0])

    human_player = UserManager.instance().user_from_index(player.index)
    if human_player != None:
        return human_player.get_max_health()

    bot_player = BotManager.instance().bot_from_index(player.index)
    if bot_player != None:
        return bot_player.get_max_health()


@PreHook(sentrygun_find_target)
def pre_sentrygun_find_target(args):
    # FIXME
    # entity = make_object(Entity, int(args[0]))

    # sentry = BuildingManager.instance().sentry_from_index(entity.index)
    # if sentry != None:
    #     sentry.set_range()
    for sentry in BuildingManager.instance().sentries:
        sentry.set_range()


# =============================================================================
# >> HOOKS
# =============================================================================
@Event("player_spawn")
def on_player_spawn(event):
    """Called when a player spawns."""
    cancel_wait = ConVar(name="mp_waitingforplayers_cancel")
    cancel_wait.set_bool(True)

    player = Player.from_userid(event["userid"])
    # BotManager.instance().on_spawn(player.index)
    UserManager.instance().on_spawn(player.index)


# @Event("player_death")
# def on_player_death(event):
#     """Called when a player dies."""
#     player = Player.from_userid(event["userid"])
#     BotManager.instance().on_death(player.index)


@Event("entity_killed")
def on_entity_killed(event):
    Logger.instance().log_debug("on_entity_killed")
    entity = baseentity_from_index(event["entindex_killed"])
    Logger.instance().log_debug(f"  classname: {entity.classname}")


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
