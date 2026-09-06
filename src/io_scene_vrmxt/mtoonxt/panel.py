# SPDX-License-Identifier: MIT
"""Material PROPERTIES panel for VRMXT_materials_mtoonxt stencil authoring."""

from __future__ import annotations

import contextlib
from typing import ClassVar

from ..materials_override.panel import VRMXT_MATERIAL_PANEL_ID

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


def _draw_relationship_materials(layout: UILayout, item: object, side: str) -> None:
    collection = item.writers if side == "WRITER" else item.readers
    box = layout.box()
    box.label(text="Writers" if side == "WRITER" else "Readers")
    for index, target in enumerate(collection):
        row = box.row(align=True)
        row.prop(target, "material", text="")
        op = row.operator(
            "vrmxt.mtoonxt_remove_relationship_material", text="", icon="X"
        )
        op.side = side
        op.target_index = index
    op = box.operator("vrmxt.mtoonxt_add_relationship_material", icon="ADD")
    op.side = side


def draw_relationship_layout(layout: UILayout, settings: object) -> None:
    row = layout.row(align=True)
    row.operator("vrmxt.mtoonxt_add_relationship", text="", icon="ADD")
    row.operator("vrmxt.mtoonxt_remove_relationship", text="", icon="REMOVE")
    if not settings.relationships:
        layout.label(text="No stencil relationships")
        return
    row.prop(settings, "relationship_index", text="Relationship")
    index = min(settings.relationship_index, len(settings.relationships) - 1)
    item = settings.relationships[index]
    _draw_relationship_materials(layout, item, "WRITER")
    _draw_relationship_materials(layout, item, "READER")
    layout.prop(item, "comparison")
    layout.prop(item, "show_writers_through_occluders")
    layout.prop(item, "writers_only_inside_readers")
    layout.prop(item, "writers_only_outside_readers")
    layout.prop(item, "writers_self_occlude")
    layout.prop(item, "ignore_occluded_reader_areas")
    layout.prop(item, "writers_write_color")
    layout.prop(item, "writers_write_depth")
    layout.prop(item, "readers_write_depth")
    layout.prop(item, "writer_depth_test")
    layout.prop(item, "reader_depth_test")


if bpy is not None:

    class VRMXT_PT_mtoonxt_stencil(Panel):
        bl_idname = "VRMXT_PT_mtoonxt_stencil"
        bl_label = "MToonXT stencil"
        bl_space_type = "PROPERTIES"
        bl_region_type = "WINDOW"
        bl_context = "material"
        bl_options: ClassVar[set[str]] = {"DEFAULT_CLOSED"}
        bl_parent_id = VRMXT_MATERIAL_PANEL_ID

        @classmethod
        def poll(cls, context: Context) -> bool:
            return _active_material(context) is not None

        def draw_header(self, _context: Context) -> None:
            self.layout.label(icon="MOD_MASK")

        def draw(self, context: Context) -> None:
            material = _active_material(context)
            if material is None:
                return
            draw_relationship_layout(
                self.layout, context.scene.vrmxt_mtoonxt_relationship_settings
            )

    class VRMXT_PT_mtoonxt_stencil_relationships(Panel):
        bl_idname = "VRMXT_PT_mtoonxt_stencil_relationships"
        bl_label = "MToonXT stencil"
        bl_space_type = "PROPERTIES"
        bl_region_type = "WINDOW"
        bl_context = "scene"
        bl_options: ClassVar[set[str]] = {"DEFAULT_CLOSED"}

        def draw(self, context: Context) -> None:
            settings = getattr(
                context.scene, "vrmxt_mtoonxt_relationship_settings", None
            )
            if settings is None:
                self.layout.label(text="MToonXT relationship settings unavailable")
                return
            draw_relationship_layout(self.layout, settings)

    CLASSES = (
        VRMXT_PT_mtoonxt_stencil,
        VRMXT_PT_mtoonxt_stencil_relationships,
    )
else:  # pragma: no cover
    VRMXT_PT_mtoonxt_stencil = None  # type: ignore[misc, assignment]
    VRMXT_PT_mtoonxt_stencil_relationships = None  # type: ignore[misc, assignment]
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
    "VRMXT_PT_mtoonxt_stencil_relationships",
    "draw_relationship_layout",
    "register",
    "unregister",
]
