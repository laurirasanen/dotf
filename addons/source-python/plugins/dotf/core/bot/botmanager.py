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


class BotManager:
    __instance = None

    bots = []

    def instance():
        """Singleton instance"""
        if BotManager.__instance is None:
            BotManager()
        return BotManager.__instance

    def __init__(self):
        if BotManager.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.bots = []

        BotManager.__instance = self

    def add_bot(self, team, bot_type):
        bot = Bot(team, bot_type)
        print(f"[dotf] Register bot {bot.bot.name}, team: {team}, type: {bot_type}")
        self.bots.append(bot)
        return bot

    def remove_bot(self, bot):
        print(f"[dotf] Unregister bot {bot.bot.name}")
        bot.bot.kick()
        self.bots.remove(bot)

    def clear(self):
        print("[dotf] Clear bots")
        for bot in self.bots:
            bot.bot.kick()
        self.bots.clear()

    def bot_from_index(self, index):
        for bot in self.bots:
            if bot.bot.index == index:
                return bot
        return None

    def tick(self):
        for bot in self.bots:
            bot.tick()

    def on_spawn(self, index):
        bot = self.bot_from_index(index)
        if bot != None:
            bot.on_spawn()
