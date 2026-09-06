# SPDX-License-Identifier: MIT
"""Blender property groups for VRMXT_materials_mtoonxt stencil authoring."""

from __future__ import annotations

import contextlib

from ..format.mtoonxt import (
    CLIP_OPS,
    COMPARISON_INSIDE,
    COMPARISON_OUTSIDE,
    DEPTH_ALWAYS,
    DEPTH_EQUAL,
    DEPTH_GREATER,
    DEPTH_GREATER_EQUAL,
    DEPTH_LESS,
    DEPTH_LESS_EQUAL,
    DEPTH_NEVER,
    DEPTH_NOT_EQUAL,
    OP_INSIDE,
    OP_INSIDE_OVERLAY,
    OP_OUTSIDE,
    OP_SAME,
    OP_WRITE,
    MtoonxtStencilRelationship,
    VrmxtMaterialsMtoonxt,
)

BODY_OP_OFF = "OFF"
OUTLINE_OP_OFF = "OFF"

try:
    import bpy
    from bpy.props import (
        BoolProperty,
        CollectionProperty,
        EnumProperty,
        IntProperty,
        PointerProperty,
    )
    from bpy.types import Material, PropertyGroup
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    PropertyGroup = object  # type: ignore[misc, assignment]
    VrmxtMtoonxtTarget = None  # type: ignore[misc, assignment]
    VrmxtMtoonxtRelationship = None  # type: ignore[misc, assignment]
    VrmxtMtoonxtRelationshipMaterial = None  # type: ignore[misc, assignment]
    VrmxtMtoonxtSceneSettings = None  # type: ignore[misc, assignment]
    VrmxtMtoonxtSettings = None  # type: ignore[misc, assignment]
else:
    _BODY_OP_ITEMS = (
        (BODY_OP_OFF, "Off", "No body stencil"),
        (OP_WRITE, "Write", "Stamp coverage"),
        (OP_INSIDE, "Clip inside", "Draw only where listed writers covered"),
        (OP_OUTSIDE, "Clip outside", "Skip pixels listed writers covered"),
        (
            OP_INSIDE_OVERLAY,
            "Clip inside overlay",
            "Draw only where listed writers covered, even if closer depth exists",
        ),
    )
    _COMPARISON_ITEMS = (
        (COMPARISON_OUTSIDE, "Outside", "Reader uses outside comparison"),
        (COMPARISON_INSIDE, "Inside", "Reader uses inside comparison"),
    )
    _DEPTH_ITEMS = (
        (DEPTH_NEVER, "Never", "Never pass depth"),
        (DEPTH_LESS, "Less", "Pass when nearer"),
        (DEPTH_EQUAL, "Equal", "Pass at equal depth"),
        (DEPTH_LESS_EQUAL, "Less Equal", "Pass when nearer or equal"),
        (DEPTH_GREATER, "Greater", "Pass when farther"),
        (DEPTH_NOT_EQUAL, "Not Equal", "Pass at different depth"),
        (DEPTH_GREATER_EQUAL, "Greater Equal", "Pass when farther or equal"),
        (DEPTH_ALWAYS, "Always", "Always pass depth"),
    )

    def _outline_op_items(self, _context: object) -> list[tuple[str, str, str, int]]:
        items: list[tuple[str, str, str, int]] = [
            (OUTLINE_OP_OFF, "Off", "No outline stencil", 0),
        ]
        if getattr(self, "body_op", BODY_OP_OFF) != BODY_OP_OFF:
            items.append((OP_SAME, "Same as body", "Copy compiled body stencil", 1))
        items.extend(
            (
                (OP_WRITE, "Write", "Stamp coverage in the outline pass", 2),
                (
                    OP_INSIDE,
                    "Clip inside",
                    "Outline only where listed writers covered",
                    3,
                ),
                (
                    OP_OUTSIDE,
                    "Clip outside",
                    "Outline skips listed writer coverage",
                    4,
                ),
                (
                    OP_INSIDE_OVERLAY,
                    "Clip inside overlay",
                    (
                        "Outline only where listed writers covered,"
                        " even if closer depth exists"
                    ),
                    5,
                ),
            )
        )
        return items

    def _on_body_op_update(self, _context: object) -> None:
        if self.body_op == BODY_OP_OFF and self.outline_op == OP_SAME:
            self.outline_op = OUTLINE_OP_OFF

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
            update=_on_body_op_update,
        )
        outline_op: EnumProperty(  # type: ignore[valid-type]
            name="Outline stencil",
            items=_outline_op_items,
            default=0,
        )
        body_targets: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtTarget,
        )
        outline_targets: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtTarget,
        )

    class VrmxtMtoonxtRelationshipMaterial(PropertyGroup):
        material: PointerProperty(name="Material", type=Material)  # type: ignore[valid-type]

    class VrmxtMtoonxtRelationship(PropertyGroup):
        writers: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtRelationshipMaterial
        )
        readers: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtRelationshipMaterial
        )
        comparison: EnumProperty(  # type: ignore[valid-type]
            name="Stencil Test", items=_COMPARISON_ITEMS, default=COMPARISON_OUTSIDE
        )
        show_writers_through_occluders: BoolProperty(  # type: ignore[valid-type]
            name="Show Writers Through Occluders", default=False
        )
        writers_only_inside_readers: BoolProperty(  # type: ignore[valid-type]
            name="Writers Only Inside Readers", default=False
        )
        writers_only_outside_readers: BoolProperty(  # type: ignore[valid-type]
            name="Writers Only Outside Readers", default=False
        )
        writers_self_occlude: BoolProperty(  # type: ignore[valid-type]
            name="Writers Occlude Themselves", default=True
        )
        ignore_occluded_reader_areas: BoolProperty(  # type: ignore[valid-type]
            name="Ignore Occluded Reader Areas", default=True
        )
        writers_write_color: BoolProperty(  # type: ignore[valid-type]
            name="Writers Write Color", default=True
        )
        writers_write_depth: BoolProperty(  # type: ignore[valid-type]
            name="Writers Write Depth", default=True
        )
        readers_write_depth: BoolProperty(  # type: ignore[valid-type]
            name="Readers Write Depth", default=True
        )
        writer_depth_test: EnumProperty(  # type: ignore[valid-type]
            name="Writer Depth Test", items=_DEPTH_ITEMS, default=DEPTH_LESS_EQUAL
        )
        reader_depth_test: EnumProperty(  # type: ignore[valid-type]
            name="Reader Depth Test", items=_DEPTH_ITEMS, default=DEPTH_LESS_EQUAL
        )

    class VrmxtMtoonxtSceneSettings(PropertyGroup):
        relationships: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtRelationship
        )
        relationship_index: IntProperty(default=0, min=0)  # type: ignore[valid-type]


_OWNS_RNA_REGISTRATION = False


def body_op_needs_targets(op: str) -> bool:
    return op in CLIP_OPS


def outline_op_needs_targets(op: str) -> bool:
    return op in CLIP_OPS


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
    extra: VrmxtMaterialsMtoonxt,
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


def _relationship_material_indices(
    collection: object, material_name_to_index: dict[str, int]
) -> list[int]:
    indices: list[int] = []
    seen: set[int] = set()
    for item in collection or ():
        material = getattr(item, "material", item)
        name = getattr(material, "name", None)
        index = material_name_to_index.get(name) if isinstance(name, str) else None
        if index is not None and index not in seen:
            seen.add(index)
            indices.append(index)
    return indices


def relationships_from_scene(
    material_name_to_index: dict[str, int], scene: object | None = None
) -> list[MtoonxtStencilRelationship]:
    if scene is None and bpy is not None:
        scene = getattr(getattr(bpy, "context", None), "scene", None)
    settings = getattr(scene, "vrmxt_mtoonxt_relationship_settings", None)
    result: list[MtoonxtStencilRelationship] = []
    for item in getattr(settings, "relationships", ()) or ():
        writers = _relationship_material_indices(item.writers, material_name_to_index)
        readers = _relationship_material_indices(item.readers, material_name_to_index)
        if not writers or not readers or set(writers).intersection(readers):
            continue
        result.append(
            MtoonxtStencilRelationship(
                writers=writers,
                readers=readers,
                comparison=str(item.comparison),
                show_writers_through_occluders=bool(
                    item.show_writers_through_occluders
                ),
                writers_only_inside_readers=bool(item.writers_only_inside_readers),
                writers_only_outside_readers=bool(item.writers_only_outside_readers),
                writers_self_occlude=bool(item.writers_self_occlude),
                ignore_occluded_reader_areas=bool(item.ignore_occluded_reader_areas),
                writers_write_color=bool(item.writers_write_color),
                writers_write_depth=bool(item.writers_write_depth),
                readers_write_depth=bool(item.readers_write_depth),
                writer_depth_test=str(item.writer_depth_test),
                reader_depth_test=str(item.reader_depth_test),
            )
        )
    return result


def validate_relationships_in_scene(scene: object | None = None) -> list[str]:
    """Validate authored VRMXT relationship properties before serialization."""

    if scene is None and bpy is not None:
        scene = getattr(getattr(bpy, "context", None), "scene", None)
    settings = getattr(scene, "vrmxt_mtoonxt_relationship_settings", None)
    errors: list[str] = []
    for index, item in enumerate(getattr(settings, "relationships", ()) or ()):
        writers = iter_target_materials(getattr(item, "writers", None))
        readers = iter_target_materials(getattr(item, "readers", None))
        label = f"VRMXT stencil relationship {index + 1}"
        if not writers:
            errors.append(f"{label} has no writer material.")
        if not readers:
            errors.append(f"{label} has no reader material.")
        writer_keys = {id(material) for material in writers}
        if any(id(material) in writer_keys for material in readers):
            errors.append(f"{label} uses the same material as writer and reader.")
        if bool(getattr(item, "writers_only_inside_readers", False)) and bool(
            getattr(item, "writers_only_outside_readers", False)
        ):
            errors.append(f"{label} cannot be both inside-only and outside-only.")
    return list(dict.fromkeys(errors))


def apply_parsed_relationships_to_scene(
    relationships: object,
    index_to_material: dict[int, object],
    context: object | None = None,
) -> None:
    blender_context = getattr(context, "context", None)
    scene = getattr(context, "scene", None) or getattr(blender_context, "scene", None)
    if scene is None and bpy is not None:
        scene = getattr(getattr(bpy, "context", None), "scene", None)
    settings = getattr(scene, "vrmxt_mtoonxt_relationship_settings", None)
    collection = getattr(settings, "relationships", None)
    if collection is None or not hasattr(collection, "add"):
        return
    first_imported_index = len(collection)
    for relationship in relationships or ():
        item = collection.add()
        for index in relationship.writers:
            material = index_to_material.get(index)
            if material is not None:
                item.writers.add().material = material
        for index in relationship.readers:
            material = index_to_material.get(index)
            if material is not None:
                item.readers.add().material = material
        item.comparison = relationship.comparison
        item.show_writers_through_occluders = (
            relationship.show_writers_through_occluders
        )
        item.writers_only_inside_readers = relationship.writers_only_inside_readers
        item.writers_only_outside_readers = relationship.writers_only_outside_readers
        item.writers_self_occlude = relationship.writers_self_occlude
        item.ignore_occluded_reader_areas = relationship.ignore_occluded_reader_areas
        item.writers_write_color = relationship.writers_write_color
        item.writers_write_depth = relationship.writers_write_depth
        item.readers_write_depth = relationship.readers_write_depth
        item.writer_depth_test = relationship.writer_depth_test
        item.reader_depth_test = relationship.reader_depth_test
    if len(collection) > first_imported_index:
        settings.relationship_index = first_imported_index


def register() -> bool:
    global _OWNS_RNA_REGISTRATION
    if bpy is None:
        return False
    if hasattr(bpy.types.Scene, "vrmxt_mtoonxt_relationship_settings"):
        # Another standalone or embedded copy already owns the shared RNA.
        # Reuse it so both deployment modes can coexist without class clashes.
        return False
    classes = (
        VrmxtMtoonxtTarget,
        VrmxtMtoonxtSettings,
        VrmxtMtoonxtRelationshipMaterial,
        VrmxtMtoonxtRelationship,
        VrmxtMtoonxtSceneSettings,
    )
    registered = []
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
            registered.append(cls)
        bpy.types.Material.vrmxt_mtoonxt_settings = PointerProperty(  # type: ignore[attr-defined]
            type=VrmxtMtoonxtSettings
        )
        bpy.types.Scene.vrmxt_mtoonxt_relationship_settings = PointerProperty(  # type: ignore[attr-defined]
            type=VrmxtMtoonxtSceneSettings
        )
    except Exception:
        for cls in reversed(registered):
            with contextlib.suppress(RuntimeError):
                bpy.utils.unregister_class(cls)
        raise
    _OWNS_RNA_REGISTRATION = True
    return True


def unregister() -> None:
    global _OWNS_RNA_REGISTRATION
    if bpy is None:
        return
    if not _OWNS_RNA_REGISTRATION:
        return
    if hasattr(bpy.types.Material, "vrmxt_mtoonxt_settings"):
        del bpy.types.Material.vrmxt_mtoonxt_settings
    if hasattr(bpy.types.Scene, "vrmxt_mtoonxt_relationship_settings"):
        del bpy.types.Scene.vrmxt_mtoonxt_relationship_settings
    for cls in (
        VrmxtMtoonxtSceneSettings,
        VrmxtMtoonxtRelationship,
        VrmxtMtoonxtRelationshipMaterial,
        VrmxtMtoonxtSettings,
        VrmxtMtoonxtTarget,
    ):
        with contextlib.suppress(RuntimeError):
            bpy.utils.unregister_class(cls)
    _OWNS_RNA_REGISTRATION = False


__all__ = [
    "BODY_OP_OFF",
    "OUTLINE_OP_OFF",
    "VrmxtMtoonxtSettings",
    "VrmxtMtoonxtTarget",
    "VrmxtMtoonxtRelationship",
    "VrmxtMtoonxtRelationshipMaterial",
    "VrmxtMtoonxtSceneSettings",
    "add_body_target",
    "add_outline_target",
    "apply_parsed_to_settings",
    "apply_parsed_relationships_to_scene",
    "body_op_needs_targets",
    "clear_body_targets",
    "clear_outline_targets",
    "iter_target_materials",
    "outline_op_needs_targets",
    "relationships_from_scene",
    "validate_relationships_in_scene",
    "register",
    "unregister",
]
