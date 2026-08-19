# SPDX-License-Identifier: MIT
"""Material PROPERTIES panel for VRMC_materials_mtoonxt stencil authoring."""

from __future__ import annotations

import contextlib
from typing import ClassVar

from ..materials_override.panel import VRM_MATERIAL_PANEL_ID
from .property_group import body_op_needs_targets, outline_op_needs_targets

try:
    import bpy
    from bpy.types import Context, Panel, UILayout
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    Context = object  # type: ignore[misc, assignment]
    Panel = object  # type: ignore[misc, assignment]
    UILayout = object  # type: ignore[misc, assignment]


def _active_material(context: Context):
    material = getattr(context, "material", None)
    if material is not None:
        return material
    obj = getattr(context, "active_object", None)
    if obj is None:
        return None
    return getattr(obj, "active_material", None)


def _draw_target_rows(
    layout: UILayout,
    collection: object,
    remove_id: str,
) -> None:
    for index, item in enumerate(collection):
        row = layout.row(align=True)
        row.prop(item, "material", text="")
        op = row.operator(remove_id, text="", icon="X")
        op.target_index = index


def draw_mtoonxt_layout(layout: UILayout, material: object) -> None:
    settings = getattr(material, "vrmxt_mtoonxt_settings", None)
    if settings is None:
        layout.label(text="MToonXT settings unavailable")
        return

    layout.prop(settings, "body_op")
    if body_op_needs_targets(str(getattr(settings, "body_op", "") or "")):
        box = layout.box()
        box.label(text="Clip against writers")
        _draw_target_rows(
            box, settings.body_targets, "vrmxt.mtoonxt_remove_body_target"
        )
        box.operator("vrmxt.mtoonxt_add_body_target", icon="ADD")

    layout.prop(settings, "outline_op")
    if outline_op_needs_targets(str(getattr(settings, "outline_op", "") or "")):
        box = layout.box()
        box.label(text="Outline clip against writers")
        _draw_target_rows(
            box, settings.outline_targets, "vrmxt.mtoonxt_remove_outline_target"
        )
        box.operator("vrmxt.mtoonxt_add_outline_target", icon="ADD")

    help_box = layout.box()
    help_box.label(text="Runtime stencil is Unity / Warudo.")
    help_box.label(text="This panel authors the glTF extras.")


if bpy is not None:

    class VRMXT_PT_mtoonxt_stencil(Panel):
        bl_idname = "VRMXT_PT_mtoonxt_stencil"
        bl_label = "MToonXT stencil"
        bl_space_type = "PROPERTIES"
        bl_region_type = "WINDOW"
        bl_context = "material"
        bl_options: ClassVar[set[str]] = {"DEFAULT_CLOSED"}
        bl_parent_id = VRM_MATERIAL_PANEL_ID

        @classmethod
        def poll(cls, context: Context) -> bool:
            return _active_material(context) is not None

        def draw_header(self, _context: Context) -> None:
            self.layout.label(icon="MOD_MASK")

        def draw(self, context: Context) -> None:
            material = _active_material(context)
            if material is None:
                return
            draw_mtoonxt_layout(self.layout, material)

    CLASSES = (VRMXT_PT_mtoonxt_stencil,)
else:  # pragma: no cover
    VRMXT_PT_mtoonxt_stencil = None  # type: ignore[misc, assignment]
    CLASSES = ()


def register() -> None:
    if bpy is None:
        return
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    if bpy is None:
        return
    for cls in reversed(CLASSES):
        with contextlib.suppress(RuntimeError):
            bpy.utils.unregister_class(cls)


__all__ = [
    "VRMXT_PT_mtoonxt_stencil",
    "draw_mtoonxt_layout",
    "register",
    "unregister",
]
