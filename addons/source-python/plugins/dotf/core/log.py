"""
================================================================
    * core/log.py
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
from datetime import datetime

# Source.Python
from loggers import LogManager
from cvars import ConVar

# =============================================================================
# >> CVARS
# =============================================================================
# Critical   = 0
# Exception  = 1
# Warning    = 2
# Info       = 3
# Debug      = 4
# Message    = 5
dotf_logging_level = ConVar("dotf_logging_level", "5", "dotf logging level")
# Console    = 1
# Main log   = 2
# SP log     = 4
# Script log = 8
dotf_logging_areas = ConVar("dotf_logging_areas", "15", "dotf logging areas")


class Logger:
    __instance = None

    def instance():
        """Singleton instance"""
        if Logger.__instance is None:
            Logger()
        return Logger.__instance

    def __init__(self):
        if Logger.__instance is not None:
            raise Exception("This class is a singleton, use .instance() access method.")

        self.set_log_file(datetime.now().strftime("dotf-%Y%m%d_%H%M%S"))

        Logger.__instance = self

    def set_log_file(self, file):
        self.manager = LogManager(
            "dotf",
            dotf_logging_level,
            dotf_logging_areas,
            file,
            "%(asctime)s %(levelname)s\t%(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

    def log_message(self, msg, *args, **kwargs):
        self.manager.log_message(f"[dotf] {msg}", *args, **kwargs)

    def log_debug(self, msg, *args, **kwargs):
        self.manager.log_debug(f"[dotf] {msg}", *args, **kwargs)

    def log_info(self, msg, *args, **kwargs):
        self.manager.log_info(f"[dotf] {msg}", *args, **kwargs)

    def log_warning(self, msg, *args, **kwargs):
        self.manager.log_warning(f"[dotf] {msg}", *args, **kwargs)

    def log_exception(self, msg, *args, **kwargs):
        self.manager.log_exception(f"[dotf] {msg}", *args, **kwargs)

    def log_critical(self, msg, *args, **kwargs):
        self.manager.log_critical(f"[dotf] {msg}", *args, **kwargs)
