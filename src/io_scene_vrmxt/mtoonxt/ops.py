# SPDX-License-Identifier: MIT
"""Operators for VRMXT_materials_mtoonxt stencil authoring."""

from __future__ import annotations

import contextlib
from typing import ClassVar

try:
    import bpy
    from bpy.props import EnumProperty, IntProperty
    from bpy.types import Context, Operator
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    Context = object  # type: ignore[misc, assignment]
    Operator = object  # type: ignore[misc, assignment]


if bpy is not None:

    def _stencil_settings(context: Context):
        return getattr(context.scene, "vrmxt_mtoonxt_stencil_settings", None)

    class VRMXT_OT_mtoonxt_add_stencil(Operator):
        bl_idname = "vrmxt.mtoonxt_add_stencil"
        bl_label = "Add stencil"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            settings = _stencil_settings(context)
            if settings is None:
                return {"CANCELLED"}
            settings.stencils.add()
            settings.stencil_index = len(settings.stencils) - 1
            return {"FINISHED"}

    class VRMXT_OT_mtoonxt_remove_stencil(Operator):
        bl_idname = "vrmxt.mtoonxt_remove_stencil"
        bl_label = "Remove stencil"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            settings = _stencil_settings(context)
            if settings is None or not settings.stencils:
                return {"CANCELLED"}
            index = min(settings.stencil_index, len(settings.stencils) - 1)
            settings.stencils.remove(index)
            settings.stencil_index = max(0, min(index, len(settings.stencils) - 1))
            return {"FINISHED"}

    class VRMXT_OT_mtoonxt_add_stencil_material(Operator):
        bl_idname = "vrmxt.mtoonxt_add_stencil_material"
        bl_label = "Add material"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        side: EnumProperty(  # type: ignore[valid-type]
            items=(("WRITER", "Writer", ""), ("READER", "Reader", "")),
            default="WRITER",
        )

        def execute(self, context: Context) -> set[str]:
            settings = _stencil_settings(context)
            if settings is None or not settings.stencils:
                return {"CANCELLED"}
            item = settings.stencils[
                min(settings.stencil_index, len(settings.stencils) - 1)
            ]
            (item.writers if self.side == "WRITER" else item.readers).add()
            return {"FINISHED"}

    class VRMXT_OT_mtoonxt_remove_stencil_material(Operator):
        bl_idname = "vrmxt.mtoonxt_remove_stencil_material"
        bl_label = "Remove material"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        side: EnumProperty(  # type: ignore[valid-type]
            items=(("WRITER", "Writer", ""), ("READER", "Reader", "")),
            default="WRITER",
        )
        target_index: IntProperty(default=0, min=0)  # type: ignore[valid-type]

        def execute(self, context: Context) -> set[str]:
            settings = _stencil_settings(context)
            if settings is None or not settings.stencils:
                return {"CANCELLED"}
            item = settings.stencils[
                min(settings.stencil_index, len(settings.stencils) - 1)
            ]
            collection = item.writers if self.side == "WRITER" else item.readers
            if self.target_index >= len(collection):
                return {"CANCELLED"}
            collection.remove(self.target_index)
            return {"FINISHED"}

    CLASSES = (
        VRMXT_OT_mtoonxt_add_stencil,
        VRMXT_OT_mtoonxt_remove_stencil,
        VRMXT_OT_mtoonxt_add_stencil_material,
        VRMXT_OT_mtoonxt_remove_stencil_material,
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
