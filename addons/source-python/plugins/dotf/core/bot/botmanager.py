"""
================================================================
    * core/bot/botmanager.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Bot functionality
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Source.Python
from engines.server import queue_command_string
from filters.players import PlayerIter
from mathlib import NULL_VECTOR

# dotf
from .bot import Bot
from ..nextbot import NextBotCombatCharacter
from ..log import Logger


class BotManager:
    __instance = None

    def instance():
        """Singleton instance"""
        if BotManager.__instance is None:
            BotManager()
        return BotManager.__instance

    def __init__(self):
        if BotManager.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.bots = []
        self.max_bots = 60

        BotManager.__instance = self

    def add_bot(self):
        if len(self.bots) >= self.max_bots:
            Logger.instance().log_debug("ERR: out of bots!")
            return None

        bot = NextBotCombatCharacter.create()
        # Logger.instance().log_debug(f"Register bot {bot.name}")
        self.bots.append(bot)
        return bot

    def remove_bot(self, bot, kill=False):
        # Logger.instance().log_debug(f"Unregister bot {bot.name}")
        self.bots.remove(bot)

    def remove_bot_index(self, index):
        for bot in self.bots:
            if bot.index == index:
                self.bots.remove(bot)

    def clear(self):
        Logger.instance().log_debug("Clear bots")
        for bot in self.bots:
            bot.remove_hooks()
        self.bots.clear()
        queue_command_string("nb_delete_all")

    def bot_from_index(self, index):
        for bot in self.bots:
            if bot.index == index:
                return bot
        return None

    def tick(self):
        pass
