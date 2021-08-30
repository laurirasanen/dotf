"""
================================================================
    * setup.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    Setup script for installing python requirements.
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# Python
import sys
import platform
from pip._internal import main as pipmain

if __name__ == "__main__":
    # make sure we're running same python version as Source.Python
    assert sys.version_info.major == 3
    assert platform.architecture()[0] == "32bit"

    # install requirements to /addons/source-python/packages/site-packages/
    with open("requirements.txt") as requirements:
        pipmain(
            [
                "install",
                "-t",
                "../../packages/site-packages/",
                *requirements.readlines(),
            ]
        )
