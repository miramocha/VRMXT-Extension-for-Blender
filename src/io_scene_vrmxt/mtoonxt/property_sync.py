# SPDX-License-Identifier: MIT
"""Optional synchronization between VRMXT-owned and host-owned Blender RNA."""

from __future__ import annotations

import contextlib
from contextlib import contextmanager

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
)

_BVT_TO_VRMXT_DEPTH = {
    "NEVER": DEPTH_NEVER,
    "LESS": DEPTH_LESS,
    "EQUAL": DEPTH_EQUAL,
    "LEQUAL": DEPTH_LESS_EQUAL,
    "GREATER": DEPTH_GREATER,
    "NOTEQUAL": DEPTH_NOT_EQUAL,
    "GEQUAL": DEPTH_GREATER_EQUAL,
    "ALWAYS": DEPTH_ALWAYS,
}
_VRMXT_TO_BVT_DEPTH = {value: key for key, value in _BVT_TO_VRMXT_DEPTH.items()}
_SYNCING_SCENES: set[int] = set()


def _scene_key(scene: object) -> int:
    as_pointer = getattr(scene, "as_pointer", None)
    if callable(as_pointer):
        try:
            return int(as_pointer())
        except (ReferenceError, RuntimeError, TypeError):
            pass
    return id(scene)


@contextmanager
def _sync_guard(scene: object):
    key = _scene_key(scene)
    if key in _SYNCING_SCENES:
        yield False
        return
    _SYNCING_SCENES.add(key)
    try:
        yield True
    finally:
        _SYNCING_SCENES.discard(key)


def _is_enabled_mtoon_material(material: object) -> bool:
    if material is None:
        return False
    try:
        return bool(material.vrm_addon_extension.mtoon1.enabled)
    except (AttributeError, ReferenceError, TypeError):
        return False


def _object_mtoon_materials(obj: object) -> list[object]:
    result: list[object] = []
    seen: set[int] = set()
    for slot in getattr(obj, "material_slots", ()) or ():
        material = getattr(slot, "material", None)
        if not _is_enabled_mtoon_material(material):
            continue
        key = id(material)
        as_pointer = getattr(material, "as_pointer", None)
        if callable(as_pointer):
            with contextlib.suppress(ReferenceError, RuntimeError, TypeError):
                key = int(as_pointer())
        if key not in seen:
            seen.add(key)
            result.append(material)
    return result


def _bvt_target_materials(item: object, side: str) -> list[object]:
    normalized = "writer" if side == "WRITER" else "reader"
    kind = str(getattr(item, f"{normalized}_target_kind", "MATERIAL") or "MATERIAL")
    if kind != "OBJECT":
        property_name = (
            "writer_material" if normalized == "writer" else "masked_material"
        )
        material = getattr(item, property_name, None)
        return [material] if _is_enabled_mtoon_material(material) else []

    collection = getattr(item, f"{normalized}_object_material_items", ()) or ()
    configured: list[object] = []
    for entry in collection:
        if str(getattr(entry, "mode", "INCLUDE") or "INCLUDE") == "EXCLUDE":
            continue
        material = getattr(entry, "material", None)
        if _is_enabled_mtoon_material(material):
            configured.append(material)
    if collection:
        return configured
    return _object_mtoon_materials(getattr(item, f"{normalized}_object", None))


def sync_bvt_scene_to_vrmxt(scene: object) -> bool:
    """Mirror BVT relationship rows into VRMXT-owned Scene properties."""

    bvt = getattr(scene, "bvt_mtoon_compositor_settings", None)
    vrmxt = getattr(scene, "vrmxt_mtoonxt_relationship_settings", None)
    if bvt is None or vrmxt is None:
        return False
    with _sync_guard(scene) as active:
        if not active:
            return False
        vrmxt.relationships.clear()
        source_items = tuple(getattr(bvt, "stencil_relationship_items", ()) or ())
        for source in source_items:
            writers = _bvt_target_materials(source, "WRITER")
            readers = _bvt_target_materials(source, "READER")
            if not writers or not readers:
                continue
            writer_keys = {id(material) for material in writers}
            if any(id(material) in writer_keys for material in readers):
                continue
            target = vrmxt.relationships.add()
            for material in writers:
                target.writers.add().material = material
            for material in readers:
                target.readers.add().material = material
            target.comparison = (
                COMPARISON_INSIDE
                if str(getattr(source, "comparison", "OUTSIDE")) == "INSIDE"
                else COMPARISON_OUTSIDE
            )
            target.show_writers_through_occluders = bool(
                getattr(source, "show_writers_through_occluders", False)
            )
            target.writers_only_inside_readers = bool(
                getattr(source, "writers_inside_readers_only", False)
            )
            target.writers_only_outside_readers = bool(
                getattr(source, "writers_outside_readers_only", False)
            )
            target.writers_self_occlude = bool(
                getattr(source, "writers_self_occlude", True)
            )
            target.ignore_occluded_reader_areas = bool(
                getattr(source, "ignore_occluded_reader_areas", True)
            )
            target.writers_write_color = bool(
                getattr(source, "writers_write_color", True)
            )
            target.writers_write_depth = bool(
                getattr(source, "writers_write_depth", True)
            )
            target.readers_write_depth = bool(
                getattr(source, "readers_write_depth", True)
            )
            target.writer_depth_test = _BVT_TO_VRMXT_DEPTH.get(
                str(getattr(source, "writer_ztest", "LEQUAL")), DEPTH_LESS_EQUAL
            )
            target.reader_depth_test = _BVT_TO_VRMXT_DEPTH.get(
                str(getattr(source, "reader_ztest", "LEQUAL")), DEPTH_LESS_EQUAL
            )
        vrmxt.relationship_index = max(
            0,
            min(
                int(getattr(bvt, "stencil_relationship_index", 0)),
                len(vrmxt.relationships) - 1,
            ),
        )
        return True


def sync_vrmxt_scene_to_bvt(scene: object) -> bool:
    """Mirror imported VRMXT relationships into BVT when BVT is present."""

    bvt = getattr(scene, "bvt_mtoon_compositor_settings", None)
    vrmxt = getattr(scene, "vrmxt_mtoonxt_relationship_settings", None)
    if bvt is None or vrmxt is None:
        return False
    with _sync_guard(scene) as active:
        if not active:
            return False
        bvt.stencil_relationship_items.clear()
        for source in tuple(getattr(vrmxt, "relationships", ()) or ()):
            writers = [entry.material for entry in source.writers if entry.material]
            readers = [entry.material for entry in source.readers if entry.material]
            for writer in writers:
                for reader in readers:
                    if writer == reader:
                        continue
                    target = bvt.stencil_relationship_items.add()
                    target.writer_target_kind = "MATERIAL"
                    target.writer_material = writer
                    target.reader_target_kind = "MATERIAL"
                    target.masked_material = reader
                    target.comparison = (
                        "INSIDE"
                        if str(source.comparison) == COMPARISON_INSIDE
                        else "OUTSIDE"
                    )
                    target.show_writers_through_occluders = bool(
                        source.show_writers_through_occluders
                    )
                    target.writers_inside_readers_only = bool(
                        source.writers_only_inside_readers
                    )
                    target.writers_outside_readers_only = bool(
                        source.writers_only_outside_readers
                    )
                    target.writers_self_occlude = bool(source.writers_self_occlude)
                    target.ignore_occluded_reader_areas = bool(
                        source.ignore_occluded_reader_areas
                    )
                    target.writers_write_color = bool(source.writers_write_color)
                    target.writers_write_depth = bool(source.writers_write_depth)
                    target.readers_write_depth = bool(source.readers_write_depth)
                    target.writer_ztest = _VRMXT_TO_BVT_DEPTH.get(
                        str(source.writer_depth_test), "LEQUAL"
                    )
                    target.reader_ztest = _VRMXT_TO_BVT_DEPTH.get(
                        str(source.reader_depth_test), "LEQUAL"
                    )
        bvt.stencil_relationship_index = max(
            0,
            min(
                int(getattr(vrmxt, "relationship_index", 0)),
                len(bvt.stencil_relationship_items) - 1,
            ),
        )
        return True


def initialize_bvt_scene_sync(scene: object) -> bool:
    """Reconcile persisted authoring without erasing standalone VRMXT data."""

    bvt = getattr(scene, "bvt_mtoon_compositor_settings", None)
    vrmxt = getattr(scene, "vrmxt_mtoonxt_relationship_settings", None)
    if bvt is None or vrmxt is None:
        return False
    bvt_items = getattr(bvt, "stencil_relationship_items", ()) or ()
    vrmxt_items = getattr(vrmxt, "relationships", ()) or ()
    if not bvt_items and vrmxt_items:
        return sync_vrmxt_scene_to_bvt(scene)
    return sync_bvt_scene_to_vrmxt(scene)


__all__ = [
    "initialize_bvt_scene_sync",
    "sync_bvt_scene_to_vrmxt",
    "sync_vrmxt_scene_to_bvt",
]
