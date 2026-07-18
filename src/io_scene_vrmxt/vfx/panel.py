# SPDX-License-Identifier: MIT
"""Armature / VRM sidebar panels for VRMXT_vfx emitters."""

from __future__ import annotations

from typing import ClassVar

from .ops import (
    VRMXT_OT_add_vfx_emitter,
    VRMXT_OT_move_vfx_emitter,
    VRMXT_OT_remove_vfx_emitter,
)
from .property_group import (
    ATTACHMENT_TYPE_BONE,
    ATTACHMENT_TYPE_OBJECT,
)
from .ui_list import VRMXT_UL_vfx_emitters

try:
    import bpy
    from bpy.types import Armature, Context, Panel, UILayout
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    Armature = type("Armature", (), {})  # type: ignore[misc, assignment]
    Context = object  # type: ignore[misc, assignment]
    Panel = object  # type: ignore[misc, assignment]
    UILayout = object  # type: ignore[misc, assignment]

# Peer-depend on Extended VRM armature panel when that add-on is enabled.
VRM_ARMATURE_PANEL_ID = "VRM_PT_vrm_armature_object_property"


def _find_armature_object(context: Context) -> object | None:
    obj = getattr(context, "active_object", None)
    if (
        obj is not None
        and getattr(obj, "type", None) == "ARMATURE"
        and hasattr(getattr(obj, "data", None), "vrmxt_vfx_settings")
    ):
        return obj

    # Prefer the same armature the host VRM N-panel uses when available.
    vrm_search = None
    try:
        from io_scene_vrm.editor import search as vrm_search
    except ImportError:
        import importlib
        import sys

        candidates = [
            name
            for name in sys.modules
            if name.startswith("bl_ext.") and name.endswith(".vrm.editor.search")
        ]
        candidates.append("bl_ext.user_default.vrm.editor.search")
        for module_name in candidates:
            try:
                vrm_search = importlib.import_module(module_name)
                break
            except ImportError:
                continue
        if vrm_search is None:
            return None

    if vrm_search is None:
        return None

    try:
        armature = vrm_search.current_armature(context)
    except Exception:  # noqa: BLE001
        return None
    if (
        armature is not None
        and getattr(armature, "type", None) == "ARMATURE"
        and hasattr(getattr(armature, "data", None), "vrmxt_vfx_settings")
    ):
        return armature
    return None


def _draw_emitter_list(layout: UILayout, settings: object) -> None:
    if (
        VRMXT_UL_vfx_emitters is None
        or VRMXT_OT_add_vfx_emitter is None
        or VRMXT_OT_remove_vfx_emitter is None
        or VRMXT_OT_move_vfx_emitter is None
    ):
        return

    row = layout.row()
    row.template_list(
        VRMXT_UL_vfx_emitters.bl_idname,
        "",
        settings,
        "emitters",
        settings,
        "active_emitter_index",
        rows=3,
    )

    col = row.column(align=True)
    col.operator(VRMXT_OT_add_vfx_emitter.bl_idname, icon="ADD", text="")
    col.operator(VRMXT_OT_remove_vfx_emitter.bl_idname, icon="REMOVE", text="")
    col.separator()
    up = col.operator(VRMXT_OT_move_vfx_emitter.bl_idname, icon="TRIA_UP", text="")
    up.direction = "UP"
    down = col.operator(VRMXT_OT_move_vfx_emitter.bl_idname, icon="TRIA_DOWN", text="")
    down.direction = "DOWN"


def _draw_emitter_details(
    layout: UILayout,
    armature_object: object,
    emitter: object,
) -> None:
    layout.use_property_split = True
    layout.use_property_decorate = False

    layout.prop(emitter, "name")
    layout.prop(emitter, "attachment_type", expand=True)

    attachment_type = getattr(emitter, "attachment_type", ATTACHMENT_TYPE_BONE)
    if attachment_type == ATTACHMENT_TYPE_BONE:
        armature_data = getattr(armature_object, "data", None)
        if armature_data is not None:
            layout.prop_search(
                emitter,
                "attachment_bone",
                armature_data,
                "bones",
                text="Bone",
            )
        else:
            layout.prop(emitter, "attachment_bone")
    elif attachment_type == ATTACHMENT_TYPE_OBJECT:
        layout.prop(emitter, "attachment_object")

    layout.prop(emitter, "local_position")
    layout.prop(emitter, "local_rotation")

    box = layout.box()
    box.label(text="Particle")
    box.prop(emitter, "texture")
    box.prop(emitter, "emission_rate")
    box.prop(emitter, "max_particles")
    box.prop(emitter, "lifetime")
    box.prop(emitter, "start_size")
    box.prop(emitter, "start_speed")
    box.prop(emitter, "start_color")


def draw_vfx_layout(layout: UILayout, armature_object: object) -> None:
    armature_data = getattr(armature_object, "data", None)
    if not isinstance(armature_data, Armature):
        return
    settings = getattr(armature_data, "vrmxt_vfx_settings", None)
    if settings is None:
        return

    _draw_emitter_list(layout, settings)

    emitters = settings.emitters
    index = settings.active_emitter_index
    if not emitters or index < 0 or index >= len(emitters):
        layout.label(text="No emitters")
        return

    _draw_emitter_details(layout, armature_object, emitters[index])


if bpy is not None:

    class VRMXT_PT_vfx_armature_object_property(Panel):
        bl_idname = "VRMXT_PT_vfx_armature_object_property"
        bl_label = "VFX"
        bl_space_type = "PROPERTIES"
        bl_region_type = "WINDOW"
        bl_context = "object"
        bl_options: ClassVar[set[str]] = {"DEFAULT_CLOSED"}
        bl_parent_id = VRM_ARMATURE_PANEL_ID

        @classmethod
        def poll(cls, context: Context) -> bool:
            return _find_armature_object(context) is not None

        def draw_header(self, _context: Context) -> None:
            self.layout.label(icon="PARTICLES")

        def draw(self, context: Context) -> None:
            armature = _find_armature_object(context)
            if armature is None:
                return
            draw_vfx_layout(self.layout, armature)

    class VRMXT_PT_vfx_ui(Panel):
        bl_idname = "VRMXT_PT_vfx_ui"
        bl_label = "VFX"
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "VRM"
        bl_options: ClassVar[set[str]] = {"DEFAULT_CLOSED"}

        @classmethod
        def poll(cls, context: Context) -> bool:
            return _find_armature_object(context) is not None

        def draw_header(self, _context: Context) -> None:
            self.layout.label(icon="PARTICLES")

        def draw(self, context: Context) -> None:
            armature = _find_armature_object(context)
            if armature is None:
                return
            draw_vfx_layout(self.layout, armature)

    CLASSES = (
        VRMXT_PT_vfx_armature_object_property,
        VRMXT_PT_vfx_ui,
    )
else:  # pragma: no cover
    VRMXT_PT_vfx_armature_object_property = None  # type: ignore[misc, assignment]
    VRMXT_PT_vfx_ui = None  # type: ignore[misc, assignment]
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
        bpy.utils.unregister_class(cls)


__all__ = [
    "VRM_ARMATURE_PANEL_ID",
    "VRMXT_PT_vfx_armature_object_property",
    "VRMXT_PT_vfx_ui",
    "draw_vfx_layout",
    "register",
    "unregister",
]
