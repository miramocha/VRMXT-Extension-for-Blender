# SPDX-License-Identifier: MIT
"""Optional Blender add-on for VRMXT_* Extended VRM extensions."""

bl_info = {
    "name": "VRMXT Extensions",
    "author": "Mira Luna",
    "version": (0, 2, 2),
    "blender": (4, 2, 0),
    "location": "File > Import-Export",
    "description": "Optional VRMXT_* authoring for Extended VRM",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

from . import registration  # noqa: E402


def register() -> None:
    registration.register()


def unregister() -> None:
    registration.unregister()
