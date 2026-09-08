# SPDX-License-Identifier: MIT
"""Blender property groups for VRMXT_materials_mtoonxt stencil authoring."""

from __future__ import annotations

import contextlib

from ..format.mtoonxt import (
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
    MtoonxtStencil,
)

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
    VrmxtMtoonxtStencil = None  # type: ignore[misc, assignment]
    VrmxtMtoonxtStencilMaterial = None  # type: ignore[misc, assignment]
    VrmxtMtoonxtSceneSettings = None  # type: ignore[misc, assignment]
else:
    _COMPARISON_ITEMS = (
        (COMPARISON_OUTSIDE, "Outside", "Reader uses outside comparison"),
        (COMPARISON_INSIDE, "Inside", "Reader uses inside comparison"),
    )
    _DEPTH_ITEMS = (
        (DEPTH_NEVER, "Never", "Never pass depth"),
        (DEPTH_LESS, "Less", "Pass when nearer"),
        (DEPTH_EQUAL, "Equal", "Pass at equal depth"),
        (DEPTH_LESS_EQUAL, "Less equal", "Pass when nearer or equal"),
        (DEPTH_GREATER, "Greater", "Pass when farther"),
        (DEPTH_NOT_EQUAL, "Not equal", "Pass at different depth"),
        (DEPTH_GREATER_EQUAL, "Greater equal", "Pass when farther or equal"),
        (DEPTH_ALWAYS, "Always", "Always pass depth"),
    )

    class VrmxtMtoonxtStencilMaterial(PropertyGroup):
        material: PointerProperty(name="Material", type=Material)  # type: ignore[valid-type]

    class VrmxtMtoonxtStencil(PropertyGroup):
        writers: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtStencilMaterial
        )
        readers: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtStencilMaterial
        )
        comparison: EnumProperty(  # type: ignore[valid-type]
            name="Stencil test", items=_COMPARISON_ITEMS, default=COMPARISON_OUTSIDE
        )
        show_writers_through_occluders: BoolProperty(  # type: ignore[valid-type]
            name="Show writers through occluders", default=False
        )
        writers_only_inside_readers: BoolProperty(  # type: ignore[valid-type]
            name="Writers only inside readers", default=False
        )
        writers_only_outside_readers: BoolProperty(  # type: ignore[valid-type]
            name="Writers only outside readers", default=False
        )
        writers_self_occlude: BoolProperty(  # type: ignore[valid-type]
            name="Writers occlude themselves", default=True
        )
        ignore_occluded_reader_areas: BoolProperty(  # type: ignore[valid-type]
            name="Ignore occluded reader areas", default=True
        )
        writers_write_color: BoolProperty(  # type: ignore[valid-type]
            name="Writers write color", default=True
        )
        writers_write_depth: BoolProperty(  # type: ignore[valid-type]
            name="Writers write depth", default=True
        )
        readers_write_depth: BoolProperty(  # type: ignore[valid-type]
            name="Readers write depth", default=True
        )
        writer_depth_test: EnumProperty(  # type: ignore[valid-type]
            name="Writer depth test", items=_DEPTH_ITEMS, default=DEPTH_LESS_EQUAL
        )
        reader_depth_test: EnumProperty(  # type: ignore[valid-type]
            name="Reader depth test", items=_DEPTH_ITEMS, default=DEPTH_LESS_EQUAL
        )

    class VrmxtMtoonxtSceneSettings(PropertyGroup):
        stencils: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMtoonxtStencil
        )
        stencil_index: IntProperty(default=0, min=0)  # type: ignore[valid-type]


_OWNS_RNA_REGISTRATION = False


def _material_key(material: object) -> int:
    as_pointer = getattr(material, "as_pointer", None)
    if callable(as_pointer):
        with contextlib.suppress(ReferenceError, RuntimeError, TypeError):
            return int(as_pointer())
    return id(material)


def iter_target_materials(collection: object) -> list[object]:
    result: list[object] = []
    if collection is None:
        return result
    for item in collection:
        material = getattr(item, "material", item)
        if material is not None:
            result.append(material)
    return result


def _stencil_material_indices(
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


def stencils_from_scene(
    material_name_to_index: dict[str, int], scene: object | None = None
) -> list[MtoonxtStencil]:
    if scene is None and bpy is not None:
        scene = getattr(getattr(bpy, "context", None), "scene", None)
    settings = getattr(scene, "vrmxt_mtoonxt_stencil_settings", None)
    result: list[MtoonxtStencil] = []
    for item in getattr(settings, "stencils", ()) or ():
        writers = _stencil_material_indices(item.writers, material_name_to_index)
        readers = _stencil_material_indices(item.readers, material_name_to_index)
        if not writers or not readers or set(writers).intersection(readers):
            continue
        result.append(
            MtoonxtStencil(
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


def validate_stencils_in_scene(scene: object | None = None) -> list[str]:
    """Validate authored VRMXT stencil properties before serialization."""

    if scene is None and bpy is not None:
        scene = getattr(getattr(bpy, "context", None), "scene", None)
    settings = getattr(scene, "vrmxt_mtoonxt_stencil_settings", None)
    errors: list[str] = []
    for index, item in enumerate(getattr(settings, "stencils", ()) or ()):
        writers = iter_target_materials(getattr(item, "writers", None))
        readers = iter_target_materials(getattr(item, "readers", None))
        label = f"VRMXT stencil {index + 1}"
        if not writers:
            errors.append(f"{label} has no writer material.")
        if not readers:
            errors.append(f"{label} has no reader material.")
        writer_keys = {_material_key(material) for material in writers}
        if any(_material_key(material) in writer_keys for material in readers):
            errors.append(f"{label} uses the same material as writer and reader.")
        if bool(getattr(item, "writers_only_inside_readers", False)) and bool(
            getattr(item, "writers_only_outside_readers", False)
        ):
            errors.append(f"{label} cannot be both inside-only and outside-only.")
    return list(dict.fromkeys(errors))


def apply_parsed_stencils_to_scene(
    stencils: object,
    index_to_material: dict[int, object],
    context: object | None = None,
) -> None:
    blender_context = getattr(context, "context", None)
    scene = getattr(context, "scene", None) or getattr(blender_context, "scene", None)
    if scene is None and bpy is not None:
        scene = getattr(getattr(bpy, "context", None), "scene", None)
    settings = getattr(scene, "vrmxt_mtoonxt_stencil_settings", None)
    collection = getattr(settings, "stencils", None)
    if collection is None or not hasattr(collection, "add"):
        return
    if hasattr(collection, "clear"):
        collection.clear()
    settings.stencil_index = 0
    for stencil in stencils or ():
        item = collection.add()
        for index in stencil.writers:
            material = index_to_material.get(index)
            if material is not None:
                item.writers.add().material = material
        for index in stencil.readers:
            material = index_to_material.get(index)
            if material is not None:
                item.readers.add().material = material
        item.comparison = stencil.comparison
        item.show_writers_through_occluders = stencil.show_writers_through_occluders
        item.writers_only_inside_readers = stencil.writers_only_inside_readers
        item.writers_only_outside_readers = stencil.writers_only_outside_readers
        item.writers_self_occlude = stencil.writers_self_occlude
        item.ignore_occluded_reader_areas = stencil.ignore_occluded_reader_areas
        item.writers_write_color = stencil.writers_write_color
        item.writers_write_depth = stencil.writers_write_depth
        item.readers_write_depth = stencil.readers_write_depth
        item.writer_depth_test = stencil.writer_depth_test
        item.reader_depth_test = stencil.reader_depth_test
    if collection:
        settings.stencil_index = 0


def register() -> bool:
    global _OWNS_RNA_REGISTRATION
    if bpy is None:
        return False
    if hasattr(bpy.types.Scene, "vrmxt_mtoonxt_stencil_settings"):
        # Another standalone or embedded copy already owns the shared RNA.
        # Reuse it so both deployment modes can coexist without class clashes.
        return False
    classes = (
        VrmxtMtoonxtStencilMaterial,
        VrmxtMtoonxtStencil,
        VrmxtMtoonxtSceneSettings,
    )
    registered = []
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
            registered.append(cls)
        bpy.types.Scene.vrmxt_mtoonxt_stencil_settings = PointerProperty(  # type: ignore[attr-defined]
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
    if hasattr(bpy.types.Scene, "vrmxt_mtoonxt_stencil_settings"):
        del bpy.types.Scene.vrmxt_mtoonxt_stencil_settings
    for cls in (
        VrmxtMtoonxtSceneSettings,
        VrmxtMtoonxtStencil,
        VrmxtMtoonxtStencilMaterial,
    ):
        with contextlib.suppress(RuntimeError):
            bpy.utils.unregister_class(cls)
    _OWNS_RNA_REGISTRATION = False


__all__ = [
    "VrmxtMtoonxtSceneSettings",
    "VrmxtMtoonxtStencil",
    "VrmxtMtoonxtStencilMaterial",
    "apply_parsed_stencils_to_scene",
    "iter_target_materials",
    "register",
    "stencils_from_scene",
    "unregister",
    "validate_stencils_in_scene",
]
