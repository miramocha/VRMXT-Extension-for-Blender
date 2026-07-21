# SPDX-License-Identifier: MIT
"""Operators for the armature VRMXT_sprite_particle emitter collection."""

from __future__ import annotations

import logging
from typing import ClassVar

from .property_group import ATTACHMENT_TYPE_BONE, ATTACHMENT_TYPE_OBJECT

try:
    import bpy
    from bpy.props import EnumProperty
    from bpy.types import Armature, Context, Operator
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _active_armature_object(context: object):
    if bpy is None:
        return None

    obj = getattr(context, "active_object", None)
    if (
        obj is not None
        and getattr(obj, "type", None) == "ARMATURE"
        and hasattr(getattr(obj, "data", None), "vrmxt_vfx_settings")
    ):
        return obj

    try:
        from io_scene_vrm.editor import search as vrm_search
    except ImportError:
        import importlib

        try:
            vrm_search = importlib.import_module(
                "bl_ext.user_default.vrm.editor.search"
            )
        except ImportError:
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


def _active_vfx_settings(context: object):
    armature = _active_armature_object(context)
    if armature is None:
        return None
    armature_data = armature.data
    if not isinstance(armature_data, Armature):
        return None
    return getattr(armature_data, "vrmxt_vfx_settings", None)


def _rebuild_preview_safe(context: object) -> None:
    armature = _active_armature_object(context)
    if armature is None:
        return
    try:
        from .geonodes_preview import rebuild_vfx_preview
    except ImportError:
        return
    try:
        rebuild_vfx_preview(armature, context=context)
    except Exception:  # noqa: BLE001
        logger.exception(
            "VRMXT VFX preview rebuild failed for armature %r",
            getattr(armature, "name", "?"),
        )


def _default_attachment_bone(context: object) -> str:
    """Prefer active bone, else first bone on the armature."""
    obj = getattr(context, "active_object", None)
    if obj is None or getattr(obj, "type", None) != "ARMATURE":
        try:
            from io_scene_vrm.editor import search as vrm_search

            obj = vrm_search.current_armature(context)
        except Exception:  # noqa: BLE001
            try:
                import importlib

                vrm_search = importlib.import_module(
                    "bl_ext.user_default.vrm.editor.search"
                )
                obj = vrm_search.current_armature(context)
            except Exception:  # noqa: BLE001
                return ""
    if obj is None or getattr(obj, "type", None) != "ARMATURE":
        return ""
    armature_data = obj.data
    if not isinstance(armature_data, Armature):
        return ""
    active = getattr(armature_data.bones, "active", None)
    if active is not None:
        return active.name
    if armature_data.bones:
        return armature_data.bones[0].name
    return ""


def _bone_parent_of_object(obj: object) -> str:
    """Return armature bone name when *obj* is bone-parented; else empty."""
    if obj is None:
        return ""
    parent = getattr(obj, "parent", None)
    if parent is None or getattr(parent, "type", None) != "ARMATURE":
        return ""
    if getattr(obj, "parent_type", None) != "BONE":
        return ""
    return getattr(obj, "parent_bone", "") or ""


def _resolve_offset_parent_bone(context: object, emitter: object) -> str:
    """Bone used when creating an offset Empty for *emitter*."""
    attachment_type = getattr(emitter, "attachment_type", ATTACHMENT_TYPE_BONE)
    if attachment_type == ATTACHMENT_TYPE_BONE:
        bone = getattr(emitter, "attachment_bone", "") or ""
        if bone:
            return bone
    elif attachment_type == ATTACHMENT_TYPE_OBJECT:
        attached = getattr(emitter, "attachment_object", None)
        bone = _bone_parent_of_object(attached)
        if bone:
            return bone
    return _default_attachment_bone(context)


if bpy is not None:

    class VRMXT_OT_add_vfx_emitter(Operator):
        bl_idname = "vrmxt.add_vfx_emitter"
        bl_label = "Add VFX Emitter"
        bl_description = "Add a VRMXT_sprite_particle emitter"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            settings = _active_vfx_settings(context)
            if settings is None:
                return {"CANCELLED"}
            item = settings.emitters.add()
            item.name = f"Emitter.{len(settings.emitters):03d}"
            item.attachment_type = ATTACHMENT_TYPE_BONE
            item.attachment_bone = _default_attachment_bone(context)
            settings.active_emitter_index = len(settings.emitters) - 1
            _rebuild_preview_safe(context)
            return {"FINISHED"}

    class VRMXT_OT_remove_vfx_emitter(Operator):
        bl_idname = "vrmxt.remove_vfx_emitter"
        bl_label = "Remove VFX Emitter"
        bl_description = "Remove the active VRMXT_sprite_particle emitter"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            settings = _active_vfx_settings(context)
            if settings is None or not settings.emitters:
                return {"CANCELLED"}
            index = settings.active_emitter_index
            if index < 0 or index >= len(settings.emitters):
                return {"CANCELLED"}
            settings.emitters.remove(index)
            settings.active_emitter_index = min(
                index, max(0, len(settings.emitters) - 1)
            )
            _rebuild_preview_safe(context)
            return {"FINISHED"}

    class VRMXT_OT_move_vfx_emitter(Operator):
        bl_idname = "vrmxt.move_vfx_emitter"
        bl_label = "Move VFX Emitter"
        bl_description = "Reorder the active VRMXT_sprite_particle emitter"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        direction: EnumProperty(  # type: ignore[valid-type]
            name="Direction",
            items=(
                ("UP", "Up", "Move the active emitter up"),
                ("DOWN", "Down", "Move the active emitter down"),
            ),
            options={"HIDDEN"},
        )

        def execute(self, context: Context) -> set[str]:
            settings = _active_vfx_settings(context)
            if settings is None or not settings.emitters:
                return {"CANCELLED"}
            index = settings.active_emitter_index
            if index < 0 or index >= len(settings.emitters):
                return {"CANCELLED"}
            if self.direction == "UP":
                if index <= 0:
                    return {"CANCELLED"}
                settings.emitters.move(index, index - 1)
                settings.active_emitter_index = index - 1
                _rebuild_preview_safe(context)
                return {"FINISHED"}
            if index >= len(settings.emitters) - 1:
                return {"CANCELLED"}
            settings.emitters.move(index, index + 1)
            settings.active_emitter_index = index + 1
            _rebuild_preview_safe(context)
            return {"FINISHED"}

    class VRMXT_OT_create_vfx_offset_empty(Operator):
        bl_idname = "vrmxt.create_vfx_offset_empty"
        bl_label = "Create Offset Empty"
        bl_description = (
            "Create an exportable Empty parented to a bone and attach the "
            "active emitter to it (offsets live on the Empty transform)"
        )
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            if bpy is None:
                return {"CANCELLED"}
            armature = _active_armature_object(context)
            settings = _active_vfx_settings(context)
            if armature is None or settings is None or not settings.emitters:
                return {"CANCELLED"}
            index = settings.active_emitter_index
            if index < 0 or index >= len(settings.emitters):
                return {"CANCELLED"}
            emitter = settings.emitters[index]

            bone_name = _resolve_offset_parent_bone(context, emitter)
            if not bone_name or bone_name not in armature.data.bones:
                self.report({"ERROR"}, "Select a bone or set the emitter bone first")
                return {"CANCELLED"}

            label = (getattr(emitter, "name", "") or "").strip() or "Emitter"
            empty_name = f"{label}_Offset"
            empty = bpy.data.objects.new(empty_name, None)
            empty.empty_display_type = "PLAIN_AXES"
            empty.empty_display_size = 0.05

            users = getattr(armature, "users_collection", None)
            collection = users[0] if users else context.scene.collection
            collection.objects.link(empty)

            empty.parent = armature
            empty.parent_type = "BONE"
            empty.parent_bone = bone_name
            empty.location = (0.0, 0.0, 0.0)
            empty.rotation_mode = "QUATERNION"
            empty.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
            empty.scale = (1.0, 1.0, 1.0)

            emitter.attachment_type = ATTACHMENT_TYPE_OBJECT
            emitter.attachment_bone = ""
            emitter.attachment_object = empty

            _rebuild_preview_safe(context)
            self.report({"INFO"}, f"Attached emitter to offset Empty '{empty.name}'")
            return {"FINISHED"}

    class VRMXT_OT_rebuild_vfx_preview(Operator):
        bl_idname = "vrmxt.rebuild_vfx_preview"
        bl_label = "Rebuild VFX Preview"
        bl_description = (
            "Rebuild Geometry Nodes particle preview helpers from VFX emitters"
        )
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            armature = _active_armature_object(context)
            if armature is None:
                return {"CANCELLED"}
            try:
                from .geonodes_preview import rebuild_vfx_preview
            except ImportError:
                self.report({"ERROR"}, "GeoNodes preview unavailable")
                return {"CANCELLED"}
            count = rebuild_vfx_preview(armature, context=context)
            self.report({"INFO"}, f"Rebuilt {count} VFX preview helper(s)")
            return {"FINISHED"}

    class VRMXT_OT_clear_vfx_preview(Operator):
        bl_idname = "vrmxt.clear_vfx_preview"
        bl_label = "Clear VFX Preview"
        bl_description = "Remove Geometry Nodes particle preview helpers"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            armature = _active_armature_object(context)
            if armature is None:
                return {"CANCELLED"}
            try:
                from .geonodes_preview import clear_vfx_preview
            except ImportError:
                self.report({"ERROR"}, "GeoNodes preview unavailable")
                return {"CANCELLED"}
            count = clear_vfx_preview(armature)
            self.report({"INFO"}, f"Cleared {count} VFX preview helper(s)")
            return {"FINISHED"}

    CLASSES = (
        VRMXT_OT_add_vfx_emitter,
        VRMXT_OT_remove_vfx_emitter,
        VRMXT_OT_move_vfx_emitter,
        VRMXT_OT_create_vfx_offset_empty,
        VRMXT_OT_rebuild_vfx_preview,
        VRMXT_OT_clear_vfx_preview,
    )
else:  # pragma: no cover
    VRMXT_OT_add_vfx_emitter = None  # type: ignore[misc, assignment]
    VRMXT_OT_remove_vfx_emitter = None  # type: ignore[misc, assignment]
    VRMXT_OT_move_vfx_emitter = None  # type: ignore[misc, assignment]
    VRMXT_OT_create_vfx_offset_empty = None  # type: ignore[misc, assignment]
    VRMXT_OT_rebuild_vfx_preview = None  # type: ignore[misc, assignment]
    VRMXT_OT_clear_vfx_preview = None  # type: ignore[misc, assignment]
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
    "VRMXT_OT_add_vfx_emitter",
    "VRMXT_OT_clear_vfx_preview",
    "VRMXT_OT_create_vfx_offset_empty",
    "VRMXT_OT_move_vfx_emitter",
    "VRMXT_OT_rebuild_vfx_preview",
    "VRMXT_OT_remove_vfx_emitter",
    "register",
    "unregister",
]
