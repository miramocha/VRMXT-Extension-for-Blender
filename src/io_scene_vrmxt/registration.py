# SPDX-License-Identifier: MIT
"""Register Blender property groups and VRM 1.0 extension hooks."""

from __future__ import annotations

from io_scene_vrmxt.hooks import vrm1_hooks
from io_scene_vrmxt.materials_override import property_group as materials_property_group
from io_scene_vrmxt.vfx import property_group as vfx_property_group


def register() -> None:
    vfx_property_group.register()
    materials_property_group.register()
    vrm1_hooks.register()


def unregister() -> None:
    vrm1_hooks.unregister()
    materials_property_group.unregister()
    vfx_property_group.unregister()


__all__ = ["register", "unregister"]
