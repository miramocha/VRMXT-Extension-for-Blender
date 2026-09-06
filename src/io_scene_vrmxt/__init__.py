# SPDX-License-Identifier: MIT
"""Optional Blender add-on for VRMXT_* Extended VRM extensions."""

bl_info = {
    "name": "VRMXT Extensions",
    "author": "Mira Luna",
    "version": (0, 3, 0),
    "blender": (4, 2, 0),
    "location": "File > Import-Export",
    "description": "Optional VRMXT_* authoring for Extended VRM",
    "warning": "",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

from . import registration  # noqa: E402
from .hooks.vrm1_hooks import (  # noqa: E402
    Vrm1ExportUserExtension,
    Vrm1ImportUserExtension,
)

__all__ = [
    "Vrm1ExportUserExtension",
    "Vrm1ImportUserExtension",
    "register",
    "unregister",
]


def register() -> None:
    registration.register()


def unregister() -> None:
    registration.unregister()
