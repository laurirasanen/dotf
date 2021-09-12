"""Maps plugin name as a subdirectory to paths.
i.e. 	   /resource/source-python/translations/dotf/chat_strings.ini
instead of /resource/source-python/translations/chat_strings.ini"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Source.Python
from paths import (
    TRANSLATION_PATH as _TRANSLATION_PATH,
    CFG_PATH as _CFG_PATH,
    LOG_PATH as _LOG_PATH,
)

# dotf
from .info import info

# =============================================================================
# >> GLOBAL VARIABLES
# =============================================================================
TRANSLATION_PATH = _TRANSLATION_PATH / info.name
CFG_PATH = _CFG_PATH / info.name
LOG_PATH = _LOG_PATH / info.name

__all__ = ("TRANSLATION_PATH", "CFG_PATH", "LOG_PATH")
