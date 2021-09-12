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
from filters.players import PlayerIter
from mathlib import NULL_VECTOR

# dotf
from .bot import Bot
from ..log import Logger


class BotManager:
    __instance = None

    bots = []
    max_bots = 22

    def instance():
        """Singleton instance"""
        if BotManager.__instance is None:
            BotManager()
        return BotManager.__instance

    def __init__(self):
        if BotManager.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.bots = []
        self.max_bots = 22

        BotManager.__instance = self

    def add_bot(self):
        if len(self.bots) >= self.max_bots:
            Logger.instance().log_debug("ERR: out of bots!")
            return None

        bot = Bot()
        Logger.instance().log_debug(f"Register bot {bot.bot.name}")
        self.bots.append(bot)
        return bot

    def add_or_get_bot(self):
        # Try to find an unreserved bot
        for bot in self.bots:
            if bot.reserved == False:
                return bot
        return self.add_bot()

    def remove_bot(self, bot):
        Logger.instance().log_debug(f"Unregister bot {bot.bot.name}")
        bot.bot.kick()
        self.bots.remove(bot)

    def clear(self):
        Logger.instance().log_debug("Clear bots")
        for bot in self.bots:
            bot.bot.kick()
        self.bots.clear()

    def bot_from_index(self, index):
        for bot in self.bots:
            if bot.bot.index == index:
                return bot
        return None

    def tick(self):
        # Calling PlayerIter multiple times for each bot
        # murders the server...
        players = []
        for player in PlayerIter():
            players.append(player)

        for bot in self.bots:
            bot.tick(players)

    def on_spawn(self, index):
        bot = self.bot_from_index(index)
        if bot != None:
            bot.on_spawn()

    def on_death(self, index):
        bot = self.bot_from_index(index)
        if bot != None:
            bot.on_death()
