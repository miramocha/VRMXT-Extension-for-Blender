# SPDX-License-Identifier: MIT
"""Blender property group for per-material VRMXT_materials_override JSON."""

from __future__ import annotations

try:
    import bpy
    from bpy.props import PointerProperty, StringProperty
    from bpy.types import PropertyGroup
except ImportError:  # pragma: no cover - exercised only inside Blender
    bpy = None  # type: ignore[assignment]

    class PropertyGroup:  # type: ignore[no-redef]
        pass


class VrmxtMaterialsOverrideSettings(PropertyGroup):  # type: ignore[misc]
    """Stores serialized materials override JSON on a Blender material."""

    raw_json: StringProperty(name="Materials Override JSON", default="")  # type: ignore[name-defined]


def register() -> None:
    if bpy is None:
        return
    bpy.utils.register_class(VrmxtMaterialsOverrideSettings)
    bpy.types.Material.vrmxt_materials_override_settings = PointerProperty(  # type: ignore[attr-defined]
        type=VrmxtMaterialsOverrideSettings
    )


def unregister() -> None:
    if bpy is None:
        return
    if hasattr(bpy.types.Material, "vrmxt_materials_override_settings"):
        del bpy.types.Material.vrmxt_materials_override_settings
    bpy.utils.unregister_class(VrmxtMaterialsOverrideSettings)


__all__ = [
    "VrmxtMaterialsOverrideSettings",
    "register",
    "unregister",
]
