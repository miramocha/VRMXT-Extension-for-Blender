# SPDX-License-Identifier: MIT
"""Blender property groups for VRMXT_vfx authoring data."""

from __future__ import annotations

ATTACHMENT_TYPE_BONE = "BONE"
ATTACHMENT_TYPE_OBJECT = "OBJECT"

_ATTACHMENT_TYPE_ITEMS = (
    (ATTACHMENT_TYPE_BONE, "Bone", "Attach to an armature pose bone"),
    (ATTACHMENT_TYPE_OBJECT, "Object", "Attach to a scene object"),
)

try:
    import bpy
    from bpy.props import (
        CollectionProperty,
        EnumProperty,
        FloatProperty,
        FloatVectorProperty,
        IntProperty,
        PointerProperty,
        StringProperty,
    )
    from bpy.types import Image, Object, PropertyGroup
except ImportError:  # pragma: no cover - exercised only outside Blender
    bpy = None  # type: ignore[assignment]
    PropertyGroup = object  # type: ignore[misc, assignment]
    VrmxtVfxEmitterItem = None  # type: ignore[misc, assignment]
    VrmxtVfxSettings = None  # type: ignore[misc, assignment]
else:

    class VrmxtVfxEmitterItem(PropertyGroup):  # type: ignore[misc]
        """Single portable VFX emitter stored on the armature."""

        name: StringProperty(  # type: ignore[valid-type]
            name="Name",
            default="",
        )
        attachment_type: EnumProperty(  # type: ignore[valid-type]
            name="Attachment",
            items=_ATTACHMENT_TYPE_ITEMS,
            default=ATTACHMENT_TYPE_BONE,
        )
        attachment_bone: StringProperty(  # type: ignore[valid-type]
            name="Bone",
            default="",
            description="Armature bone name used as the emitter attachment node",
        )
        attachment_object: PointerProperty(  # type: ignore[valid-type]
            name="Object",
            type=Object,
            description="Scene object used as the emitter attachment node",
        )
        emitter_type: StringProperty(  # type: ignore[valid-type]
            name="Type",
            default="particle",
        )
        local_position: FloatVectorProperty(  # type: ignore[valid-type]
            name="Local Position",
            size=3,
            default=(0.0, 0.0, 0.0),
            description="Offset in node local space (glTF meters, XYZ)",
        )
        local_rotation: FloatVectorProperty(  # type: ignore[valid-type]
            name="Local Rotation",
            size=4,
            default=(0.0, 0.0, 0.0, 1.0),
            description="Orientation in node local space as quaternion XYZW",
        )
        texture: PointerProperty(  # type: ignore[valid-type]
            name="Texture",
            type=Image,
            description=(
                "Particle billboard image (mapped through glTF textures on export)"
            ),
        )
        emission_rate: FloatProperty(  # type: ignore[valid-type]
            name="Emission Rate",
            default=10.0,
            min=0.0,
        )
        max_particles: IntProperty(  # type: ignore[valid-type]
            name="Max Particles",
            default=64,
            min=1,
        )
        lifetime: FloatProperty(  # type: ignore[valid-type]
            name="Lifetime",
            default=1.0,
            min=0.0,
        )
        start_size: FloatProperty(  # type: ignore[valid-type]
            name="Start Size",
            default=0.05,
            min=0.0,
        )
        start_speed: FloatProperty(  # type: ignore[valid-type]
            name="Start Speed",
            default=0.1,
            min=0.0,
        )
        start_color: FloatVectorProperty(  # type: ignore[valid-type]
            name="Start Color",
            size=4,
            subtype="COLOR",
            min=0.0,
            max=1.0,
            default=(1.0, 1.0, 1.0, 1.0),
        )

    class VrmxtVfxSettings(PropertyGroup):  # type: ignore[misc]
        """Armature-level VRMXT_vfx emitter collection."""

        emitters: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtVfxEmitterItem
        )
        active_emitter_index: IntProperty(  # type: ignore[valid-type]
            name="Active Emitter",
            default=0,
        )


def register() -> None:
    if bpy is None or VrmxtVfxEmitterItem is None or VrmxtVfxSettings is None:
        return
    bpy.utils.register_class(VrmxtVfxEmitterItem)
    bpy.utils.register_class(VrmxtVfxSettings)
    bpy.types.Armature.vrmxt_vfx_settings = PointerProperty(type=VrmxtVfxSettings)  # type: ignore[attr-defined]


def unregister() -> None:
    if bpy is None or VrmxtVfxEmitterItem is None or VrmxtVfxSettings is None:
        return
    if hasattr(bpy.types.Armature, "vrmxt_vfx_settings"):
        del bpy.types.Armature.vrmxt_vfx_settings
    bpy.utils.unregister_class(VrmxtVfxSettings)
    bpy.utils.unregister_class(VrmxtVfxEmitterItem)


__all__ = [
    "ATTACHMENT_TYPE_BONE",
    "ATTACHMENT_TYPE_OBJECT",
    "VrmxtVfxEmitterItem",
    "VrmxtVfxSettings",
    "register",
    "unregister",
]
