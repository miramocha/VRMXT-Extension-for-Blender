# SPDX-License-Identifier: MIT
"""Blender property groups for VRMXT_sprite_particle authoring data."""

from __future__ import annotations

ATTACHMENT_TYPE_BONE = "BONE"
ATTACHMENT_TYPE_OBJECT = "OBJECT"

_ATTACHMENT_TYPE_ITEMS = (
    (ATTACHMENT_TYPE_BONE, "Bone", "Attach to an armature pose bone"),
    (ATTACHMENT_TYPE_OBJECT, "Object", "Attach to a scene object / offset Empty"),
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
        """Single portable sprite-particle emitter stored on the armature."""

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
            description=(
                "Scene object (often an offset Empty under a bone) used as the "
                "emitter attachment node"
            ),
        )
        texture: PointerProperty(  # type: ignore[valid-type]
            name="Texture",
            type=Image,
            description=("Sprite image (mapped through glTF textures on export)"),
        )
        size: FloatVectorProperty(  # type: ignore[valid-type]
            name="Size",
            size=2,
            default=(0.05, 0.05),
            min=0.0001,
            description="Sprite width and height in meters",
        )
        color: FloatVectorProperty(  # type: ignore[valid-type]
            name="Color",
            size=4,
            subtype="COLOR",
            min=0.0,
            soft_max=1.0,
            default=(1.0, 1.0, 1.0, 1.0),
            description=(
                "Linear RGBA multiplier; RGB may exceed 1 (HDR). "
                "Alpha must stay in [0, 1] on export"
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
        start_speed: FloatProperty(  # type: ignore[valid-type]
            name="Start Speed",
            default=0.1,
            min=0.0,
            description="Initial speed along node local +Y, meters per second",
        )

    class VrmxtVfxSettings(PropertyGroup):  # type: ignore[misc]
        """Armature-level VRMXT_sprite_particle emitter collection."""

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
