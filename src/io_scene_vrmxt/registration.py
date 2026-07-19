# SPDX-License-Identifier: MIT
"""Register Blender property groups, UI, and VRM 1.0 extension hooks."""

from __future__ import annotations

from .hooks import vrm1_hooks
from .materials_override import panel as materials_panel
from .materials_override import property_group as materials_property_group
from .vfx import ops as vfx_ops
from .vfx import panel as vfx_panel
from .vfx import property_group as vfx_property_group
from .vfx import ui_list as vfx_ui_list


def register() -> None:
    vfx_property_group.register()
    materials_property_group.register()
    vfx_ui_list.register()
    vfx_ops.register()
    vfx_panel.register()
    materials_panel.register()
    vrm1_hooks.register()


def unregister() -> None:
    vrm1_hooks.unregister()
    materials_panel.unregister()
    vfx_panel.unregister()
    vfx_ops.unregister()
    vfx_ui_list.unregister()
    materials_property_group.unregister()
    vfx_property_group.unregister()


__all__ = ["register", "unregister"]
