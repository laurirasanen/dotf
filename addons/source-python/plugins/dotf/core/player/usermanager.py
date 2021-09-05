"""
================================================================
    * core/player/usermanager.py
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
from filters.players import PlayerIter

# dotf
from .user import User


class UserManager:
    __instance = None

    users = []

    def instance():
        """Singleton instance"""
        if UserManager.__instance is None:
            UserManager()
        return UserManager.__instance

    def __init__(self):
        if UserManager.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.users = []

        UserManager.__instance = self

    def add_user(self, user):
        print(f"[dotf] Register user {user.player.steamid}")
        self.users.append(user)

    def remove_user(self, user):
        print(f"[dotf] Unregister user {user.player.steamid}")
        self.users.remove(user)

    def clear(self):
        print("[dotf] Clear users")
        self.users.clear()

    def add_all(self):
        for p in PlayerIter.iterator():
            if not p.is_bot():
                user = User(p)
                UserManager.instance().add_user(user)
                if not p.dead:
                    user.apply_class_settings()

    def user_from_index(self, index):
        for user in self.users:
            if user.player.index == index:
                return user
        return None

    def on_spawn(self, index):
        user = self.user_from_index(index)
        if user != None:
            user.on_spawn()

    def tick(self):
        for user in self.users:
            user.tick()
