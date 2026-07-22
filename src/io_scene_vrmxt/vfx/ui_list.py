# SPDX-License-Identifier: MIT
"""UIList for armature VRMXT_sprite_particle emitters."""

from __future__ import annotations

try:
    import bpy
    from bpy.types import UILayout, UIList
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]


if bpy is not None:

    class VRMXT_UL_vfx_emitters(UIList):
        bl_idname = "VRMXT_UL_vfx_emitters"

        def draw_item(
            self,
            _context: object,
            layout: UILayout,
            _data: object,
            item: object,
            _icon: int,
            _active_data: object,
            _active_prop_name: str,
            _index: int = 0,
            _flt_flag: int = 0,
        ) -> None:
            if self.layout_type not in {"DEFAULT", "COMPACT"}:
                if self.layout_type == "GRID":
                    layout.alignment = "CENTER"
                    layout.label(text="", icon="PARTICLES")
                return

            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False, icon="PARTICLES")

            attachment_type = getattr(item, "attachment_type", "BONE")
            if attachment_type == "OBJECT":
                attachment_object = getattr(item, "attachment_object", None)
                label = attachment_object.name if attachment_object else ""
            else:
                label = getattr(item, "attachment_bone", "") or ""

            if label:
                row.label(text=label)
            else:
                row.label(text="", icon="ERROR")

    CLASSES = (VRMXT_UL_vfx_emitters,)
else:  # pragma: no cover
    VRMXT_UL_vfx_emitters = None  # type: ignore[misc, assignment]
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


__all__ = ["VRMXT_UL_vfx_emitters", "register", "unregister"]
