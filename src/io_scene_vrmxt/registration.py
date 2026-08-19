# SPDX-License-Identifier: MIT
"""Register Blender property groups, UI, and VRM 1.0 extension hooks."""

from __future__ import annotations

from .hooks import vrm1_hooks
from .materials_override import ops as materials_ops
from .materials_override import panel as materials_panel
from .materials_override import property_group as materials_property_group
from .mtoonxt import ops as mtoonxt_ops
from .mtoonxt import panel as mtoonxt_panel
from .mtoonxt import property_group as mtoonxt_property_group
from .vfx import ops as vfx_ops
from .vfx import panel as vfx_panel
from .vfx import property_group as vfx_property_group
from .vfx import ui_list as vfx_ui_list


def register() -> None:
    vfx_property_group.register()
    materials_property_group.register()
    mtoonxt_property_group.register()
    vfx_ui_list.register()
    vfx_ops.register()
    materials_ops.register()
    mtoonxt_ops.register()
    vfx_panel.register()
    materials_panel.register()
    mtoonxt_panel.register()
    vrm1_hooks.register()


def unregister() -> None:
    vrm1_hooks.unregister()
    mtoonxt_panel.unregister()
    materials_panel.unregister()
    vfx_panel.unregister()
    mtoonxt_ops.unregister()
    materials_ops.unregister()
    vfx_ops.unregister()
    vfx_ui_list.unregister()
    mtoonxt_property_group.unregister()
    materials_property_group.unregister()
    vfx_property_group.unregister()


__all__ = ["register", "unregister"]
