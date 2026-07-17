# SPDX-License-Identifier: MIT
"""Blender property groups for VRMXT_vfx authoring data."""

from __future__ import annotations

try:
    import bpy
    from bpy.props import (
        CollectionProperty,
        FloatProperty,
        FloatVectorProperty,
        IntProperty,
        PointerProperty,
        StringProperty,
    )
    from bpy.types import PropertyGroup
except ImportError:  # pragma: no cover - exercised only inside Blender
    bpy = None  # type: ignore[assignment]

    class PropertyGroup:  # type: ignore[no-redef]
        pass


class VrmxtVfxEmitterItem(PropertyGroup):  # type: ignore[misc]
    """Single portable VFX emitter stored on the armature."""

    name: StringProperty(name="Name", default="")  # type: ignore[name-defined]
    node_index: IntProperty(name="Node Index", default=-1)  # type: ignore[name-defined]
    attachment_name: StringProperty(name="Attachment Name", default="")  # type: ignore[name-defined]
    emitter_type: StringProperty(name="Type", default="particle")  # type: ignore[name-defined]
    local_position: FloatVectorProperty(  # type: ignore[name-defined]
        name="Local Position",
        size=3,
        default=(0.0, 0.0, 0.0),
    )
    local_rotation: FloatVectorProperty(  # type: ignore[name-defined]
        name="Local Rotation",
        size=4,
        default=(0.0, 0.0, 0.0, 1.0),
    )
    texture_index: IntProperty(name="Texture Index", default=-1)  # type: ignore[name-defined]
    emission_rate: FloatProperty(name="Emission Rate", default=10.0, min=0.0)  # type: ignore[name-defined]
    max_particles: IntProperty(name="Max Particles", default=64, min=1)  # type: ignore[name-defined]
    lifetime: FloatProperty(name="Lifetime", default=1.0, min=0.0)  # type: ignore[name-defined]
    start_size: FloatProperty(name="Start Size", default=0.05, min=0.0)  # type: ignore[name-defined]
    start_speed: FloatProperty(name="Start Speed", default=0.1, min=0.0)  # type: ignore[name-defined]
    start_color: FloatVectorProperty(  # type: ignore[name-defined]
        name="Start Color",
        size=4,
        subtype="COLOR",
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
    )


class VrmxtVfxSettings(PropertyGroup):  # type: ignore[misc]
    """Armature-level VRMXT_vfx emitter collection."""

    emitters: CollectionProperty(type=VrmxtVfxEmitterItem)  # type: ignore[name-defined]
    active_emitter_index: IntProperty(name="Active Emitter", default=0)  # type: ignore[name-defined]


def register() -> None:
    if bpy is None:
        return
    bpy.utils.register_class(VrmxtVfxEmitterItem)
    bpy.utils.register_class(VrmxtVfxSettings)
    bpy.types.Armature.vrmxt_vfx_settings = PointerProperty(type=VrmxtVfxSettings)  # type: ignore[attr-defined]


def unregister() -> None:
    if bpy is None:
        return
    if hasattr(bpy.types.Armature, "vrmxt_vfx_settings"):
        del bpy.types.Armature.vrmxt_vfx_settings
    bpy.utils.unregister_class(VrmxtVfxSettings)
    bpy.utils.unregister_class(VrmxtVfxEmitterItem)


__all__ = [
    "VrmxtVfxEmitterItem",
    "VrmxtVfxSettings",
    "register",
    "unregister",
]
