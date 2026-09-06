# SPDX-License-Identifier: MIT
"""Operators for VRMXT_materials_mtoonxt stencil authoring."""

from __future__ import annotations

import contextlib
from typing import ClassVar

from .property_group import add_body_target, add_outline_target

try:
    import bpy
    from bpy.props import EnumProperty, IntProperty
    from bpy.types import Context, Operator
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    Context = object  # type: ignore[misc, assignment]
    Operator = object  # type: ignore[misc, assignment]


def _active_material(context: object):
    material = getattr(context, "material", None)
    if material is not None:
        return material
    obj = getattr(context, "active_object", None)
    if obj is None:
        return None
    return getattr(obj, "active_material", None)


def _settings(context: object):
    material = _active_material(context)
    if material is None:
        return None, None
    return material, getattr(material, "vrmxt_mtoonxt_settings", None)


if bpy is not None:

    class VRMXT_OT_mtoonxt_add_body_target(Operator):
        bl_idname = "vrmxt.mtoonxt_add_body_target"
        bl_label = "Add clip target"
        bl_description = (
            "Add a writer material for body clip inside, inside overlay, or outside"
        )
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            _material, settings = _settings(context)
            if settings is None:
                return {"CANCELLED"}
            add_body_target(settings, None)
            return {"FINISHED"}

    class VRMXT_OT_mtoonxt_remove_body_target(Operator):
        bl_idname = "vrmxt.mtoonxt_remove_body_target"
        bl_label = "Remove clip target"
        bl_description = "Remove this writer from the body clip list"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        target_index: IntProperty(name="Target index", default=0, min=0)

        def execute(self, context: Context) -> set[str]:
            _material, settings = _settings(context)
            if settings is None:
                return {"CANCELLED"}
            index = int(self.target_index)
            if index < 0 or index >= len(settings.body_targets):
                return {"CANCELLED"}
            settings.body_targets.remove(index)
            return {"FINISHED"}

    class VRMXT_OT_mtoonxt_add_outline_target(Operator):
        bl_idname = "vrmxt.mtoonxt_add_outline_target"
        bl_label = "Add outline clip target"
        bl_description = (
            "Add a writer material for outline clip inside, inside overlay, or outside"
        )
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            _material, settings = _settings(context)
            if settings is None:
                return {"CANCELLED"}
            add_outline_target(settings, None)
            return {"FINISHED"}

    class VRMXT_OT_mtoonxt_remove_outline_target(Operator):
        bl_idname = "vrmxt.mtoonxt_remove_outline_target"
        bl_label = "Remove outline clip target"
        bl_description = "Remove this writer from the outline clip list"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        target_index: IntProperty(name="Target index", default=0, min=0)

        def execute(self, context: Context) -> set[str]:
            _material, settings = _settings(context)
            if settings is None:
                return {"CANCELLED"}
            index = int(self.target_index)
            if index < 0 or index >= len(settings.outline_targets):
                return {"CANCELLED"}
            settings.outline_targets.remove(index)
            return {"FINISHED"}

    def _relationship_settings(context: Context):
        return getattr(context.scene, "vrmxt_mtoonxt_relationship_settings", None)

    class VRMXT_OT_mtoonxt_add_relationship(Operator):
        bl_idname = "vrmxt.mtoonxt_add_relationship"
        bl_label = "Add stencil relationship"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            settings = _relationship_settings(context)
            if settings is None:
                return {"CANCELLED"}
            settings.relationships.add()
            settings.relationship_index = len(settings.relationships) - 1
            return {"FINISHED"}

    class VRMXT_OT_mtoonxt_remove_relationship(Operator):
        bl_idname = "vrmxt.mtoonxt_remove_relationship"
        bl_label = "Remove stencil relationship"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            settings = _relationship_settings(context)
            if settings is None or not settings.relationships:
                return {"CANCELLED"}
            index = min(settings.relationship_index, len(settings.relationships) - 1)
            settings.relationships.remove(index)
            settings.relationship_index = max(
                0, min(index, len(settings.relationships) - 1)
            )
            return {"FINISHED"}

    class VRMXT_OT_mtoonxt_add_relationship_material(Operator):
        bl_idname = "vrmxt.mtoonxt_add_relationship_material"
        bl_label = "Add relationship material"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        side: EnumProperty(  # type: ignore[valid-type]
            items=(("WRITER", "Writer", ""), ("READER", "Reader", "")),
            default="WRITER",
        )

        def execute(self, context: Context) -> set[str]:
            settings = _relationship_settings(context)
            if settings is None or not settings.relationships:
                return {"CANCELLED"}
            item = settings.relationships[
                min(settings.relationship_index, len(settings.relationships) - 1)
            ]
            (item.writers if self.side == "WRITER" else item.readers).add()
            return {"FINISHED"}

    class VRMXT_OT_mtoonxt_remove_relationship_material(Operator):
        bl_idname = "vrmxt.mtoonxt_remove_relationship_material"
        bl_label = "Remove relationship material"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        side: EnumProperty(  # type: ignore[valid-type]
            items=(("WRITER", "Writer", ""), ("READER", "Reader", "")),
            default="WRITER",
        )
        target_index: IntProperty(default=0, min=0)  # type: ignore[valid-type]

        def execute(self, context: Context) -> set[str]:
            settings = _relationship_settings(context)
            if settings is None or not settings.relationships:
                return {"CANCELLED"}
            item = settings.relationships[
                min(settings.relationship_index, len(settings.relationships) - 1)
            ]
            collection = item.writers if self.side == "WRITER" else item.readers
            if self.target_index >= len(collection):
                return {"CANCELLED"}
            collection.remove(self.target_index)
            return {"FINISHED"}

    CLASSES = (
        VRMXT_OT_mtoonxt_add_body_target,
        VRMXT_OT_mtoonxt_remove_body_target,
        VRMXT_OT_mtoonxt_add_outline_target,
        VRMXT_OT_mtoonxt_remove_outline_target,
        VRMXT_OT_mtoonxt_add_relationship,
        VRMXT_OT_mtoonxt_remove_relationship,
        VRMXT_OT_mtoonxt_add_relationship_material,
        VRMXT_OT_mtoonxt_remove_relationship_material,
    )
else:  # pragma: no cover
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


__all__ = ["register", "unregister"]
