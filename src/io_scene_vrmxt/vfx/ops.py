# SPDX-License-Identifier: MIT
"""Operators for the armature VRMXT_vfx emitter collection."""

from __future__ import annotations

from typing import ClassVar

try:
    import bpy
    from bpy.props import EnumProperty
    from bpy.types import Armature, Context, Operator
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]


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
        pass


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


if bpy is not None:

    class VRMXT_OT_add_vfx_emitter(Operator):
        bl_idname = "vrmxt.add_vfx_emitter"
        bl_label = "Add VFX Emitter"
        bl_description = "Add a VRMXT_vfx particle emitter"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            settings = _active_vfx_settings(context)
            if settings is None:
                return {"CANCELLED"}
            item = settings.emitters.add()
            item.name = f"Emitter.{len(settings.emitters):03d}"
            item.attachment_type = "BONE"
            item.attachment_bone = _default_attachment_bone(context)
            settings.active_emitter_index = len(settings.emitters) - 1
            _rebuild_preview_safe(context)
            return {"FINISHED"}

    class VRMXT_OT_remove_vfx_emitter(Operator):
        bl_idname = "vrmxt.remove_vfx_emitter"
        bl_label = "Remove VFX Emitter"
        bl_description = "Remove the active VRMXT_vfx emitter"
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
        bl_description = "Reorder the active VRMXT_vfx emitter"
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
        VRMXT_OT_rebuild_vfx_preview,
        VRMXT_OT_clear_vfx_preview,
    )
else:  # pragma: no cover
    VRMXT_OT_add_vfx_emitter = None  # type: ignore[misc, assignment]
    VRMXT_OT_remove_vfx_emitter = None  # type: ignore[misc, assignment]
    VRMXT_OT_move_vfx_emitter = None  # type: ignore[misc, assignment]
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
    "VRMXT_OT_move_vfx_emitter",
    "VRMXT_OT_rebuild_vfx_preview",
    "VRMXT_OT_remove_vfx_emitter",
    "register",
    "unregister",
]
