# SPDX-License-Identifier: MIT
"""Blender property groups for VRMC_materials_mtoonxt stencil authoring."""

from __future__ import annotations

import contextlib

from ..format.mtoonxt import (
    OP_INSIDE,
    OP_OUTSIDE,
    OP_SAME,
    OP_WRITE,
    VrmcMaterialsMtoonxt,
)

BODY_OP_OFF = "OFF"
OUTLINE_OP_OFF = "OFF"

try:
    import bpy
    from bpy.props import (
        CollectionProperty,
        EnumProperty,
        PointerProperty,
    )
    from bpy.types import Material, PropertyGroup
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    PropertyGroup = object  # type: ignore[misc, assignment]
    VrmxtMtoonxtTarget = None  # type: ignore[misc, assignment]
    VrmxtMtoonxtSettings = None  # type: ignore[misc, assignment]
else:
    _BODY_OP_ITEMS = (
        (BODY_OP_OFF, "Off", "No body stencil"),
        (OP_WRITE, "Write", "Stamp coverage"),
        (OP_INSIDE, "Clip inside", "Draw only where listed writers covered"),
        (OP_OUTSIDE, "Clip outside", "Skip pixels listed writers covered"),
    )
    _OUTLINE_OP_ITEMS = (
        (OUTLINE_OP_OFF, "Off", "No outline stencil"),
        (OP_SAME, "Same as body", "Copy compiled body stencil"),
        (OP_WRITE, "Write", "Stamp coverage in the outline pass"),
        (OP_INSIDE, "Clip inside", "Outline only where listed writers covered"),
        (OP_OUTSIDE, "Clip outside", "Outline skips listed writer coverage"),
    )

    class VrmxtMtoonxtTarget(PropertyGroup):
        material: PointerProperty(  # type: ignore[valid-type]
            name="Material",
            type=Material,
        )

    class VrmxtMtoonxtSettings(PropertyGroup):
        body_op: EnumProperty(  # type: ignore[valid-type]
            name="Stencil",
            items=_BODY_OP_ITEMS,
            default=BODY_OP_OFF,
        )
        outline_op: EnumProperty(  # type: ignore[valid-type]
            name="Outline stencil",
            items=_OUTLINE_OP_ITEMS,
            default=OUTLINE_OP_OFF,
        )
        body_targets: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtTarget,
        )
        outline_targets: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtTarget,
        )


def body_op_needs_targets(op: str) -> bool:
    return op in (OP_INSIDE, OP_OUTSIDE)


def outline_op_needs_targets(op: str) -> bool:
    return op in (OP_INSIDE, OP_OUTSIDE)


def add_body_target(settings: object, material: object) -> None:
    collection = getattr(settings, "body_targets", None)
    if collection is None:
        return
    if hasattr(collection, "add"):
        item = collection.add()
        if hasattr(item, "material"):
            item.material = material
        return
    collection.append(material)


def add_outline_target(settings: object, material: object) -> None:
    collection = getattr(settings, "outline_targets", None)
    if collection is None:
        return
    if hasattr(collection, "add"):
        item = collection.add()
        if hasattr(item, "material"):
            item.material = material
        return
    collection.append(material)


def clear_body_targets(settings: object) -> None:
    collection = getattr(settings, "body_targets", None)
    if collection is None:
        return
    if hasattr(collection, "clear"):
        collection.clear()
        return
    if hasattr(collection, "remove"):
        while len(collection):
            collection.remove(len(collection) - 1)


def clear_outline_targets(settings: object) -> None:
    collection = getattr(settings, "outline_targets", None)
    if collection is None:
        return
    if hasattr(collection, "clear"):
        collection.clear()
        return
    if hasattr(collection, "remove"):
        while len(collection):
            collection.remove(len(collection) - 1)


def iter_target_materials(collection: object) -> list[object]:
    result: list[object] = []
    if collection is None:
        return result
    for item in collection:
        material = getattr(item, "material", item)
        if material is not None:
            result.append(material)
    return result


def _add_body(settings: object, material: object) -> None:
    adder = getattr(settings, "add_body_target", None)
    if callable(adder):
        adder(material)
        return
    add_body_target(settings, material)


def _add_outline(settings: object, material: object) -> None:
    adder = getattr(settings, "add_outline_target", None)
    if callable(adder):
        adder(material)
        return
    add_outline_target(settings, material)


def apply_parsed_to_settings(
    settings: object,
    extra: VrmcMaterialsMtoonxt,
    index_to_material: dict[int, object],
) -> None:
    settings.body_op = BODY_OP_OFF
    settings.outline_op = OUTLINE_OP_OFF
    clearer = getattr(settings, "clear_body_targets", None)
    if callable(clearer):
        clearer()
    else:
        clear_body_targets(settings)
    clearer = getattr(settings, "clear_outline_targets", None)
    if callable(clearer):
        clearer()
    else:
        clear_outline_targets(settings)
    if extra.stencil is not None:
        settings.body_op = extra.stencil.op
        if extra.stencil.materials:
            for index in extra.stencil.materials:
                material = index_to_material.get(index)
                if material is not None:
                    _add_body(settings, material)
    if extra.outline_stencil is not None:
        settings.outline_op = extra.outline_stencil.op
        if extra.outline_stencil.materials:
            for index in extra.outline_stencil.materials:
                material = index_to_material.get(index)
                if material is not None:
                    _add_outline(settings, material)


def register() -> None:
    if bpy is None:
        return
    bpy.utils.register_class(VrmxtMtoonxtTarget)
    bpy.utils.register_class(VrmxtMtoonxtSettings)
    bpy.types.Material.vrmxt_mtoonxt_settings = PointerProperty(  # type: ignore[attr-defined]
        type=VrmxtMtoonxtSettings
    )


def unregister() -> None:
    if bpy is None:
        return
    if hasattr(bpy.types.Material, "vrmxt_mtoonxt_settings"):
        del bpy.types.Material.vrmxt_mtoonxt_settings
    for cls in (VrmxtMtoonxtSettings, VrmxtMtoonxtTarget):
        with contextlib.suppress(RuntimeError):
            bpy.utils.unregister_class(cls)


__all__ = [
    "BODY_OP_OFF",
    "OUTLINE_OP_OFF",
    "VrmxtMtoonxtSettings",
    "VrmxtMtoonxtTarget",
    "add_body_target",
    "add_outline_target",
    "apply_parsed_to_settings",
    "body_op_needs_targets",
    "clear_body_targets",
    "clear_outline_targets",
    "iter_target_materials",
    "outline_op_needs_targets",
    "register",
    "unregister",
]
