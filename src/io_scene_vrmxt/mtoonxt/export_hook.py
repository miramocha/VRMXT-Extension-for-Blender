# SPDX-License-Identifier: MIT
"""Serialize Blender MToonXT stencil authoring into glTF material extensions."""

from __future__ import annotations

import logging
from typing import Any

from ..common.json_util import as_dict, as_list
from ..format.mtoonxt import (
    CLIP_OPS,
    OP_SAME,
    OP_WRITE,
    MtoonxtStencil,
    VrmcMaterialsMtoonxt,
    clear_mtoonxt_from_material_dict,
    ensure_mtoonxt_extensions_used,
    listed_writers_have_body_write,
    material_has_sibling_mtoon,
    write_mtoonxt_to_material_dict,
)
from .property_group import (
    BODY_OP_OFF,
    OUTLINE_OP_OFF,
    iter_target_materials,
)

logger = logging.getLogger(__name__)


def _find_material_by_name(material_name: str) -> Any | None:
    try:
        import bpy
    except ImportError:
        return None
    for material in bpy.data.materials:
        if getattr(material, "name", None) == material_name:
            return material
    return None


def _resolve_clip_indices(
    targets: object,
    material_name_to_index: dict[str, int],
    own_index: int,
) -> list[int]:
    indices: list[int] = []
    seen: set[int] = set()
    for material in iter_target_materials(targets):
        name = getattr(material, "name", None)
        if not isinstance(name, str):
            continue
        index = material_name_to_index.get(name)
        if index is None or index == own_index or index in seen:
            continue
        seen.add(index)
        indices.append(index)
    return indices


def _stencil_from_settings(
    op: str,
    targets: object,
    material_name_to_index: dict[str, int],
    own_index: int,
    *,
    allow_same: bool,
) -> MtoonxtStencil | None:
    if op in ("", BODY_OP_OFF, OUTLINE_OP_OFF):
        return None
    if op == OP_SAME:
        if not allow_same:
            return None
        return MtoonxtStencil(op=OP_SAME)
    if op == OP_WRITE:
        return MtoonxtStencil(op=OP_WRITE)
    if op in CLIP_OPS:
        indices = _resolve_clip_indices(targets, material_name_to_index, own_index)
        if not indices:
            return None
        return MtoonxtStencil(op=op, materials=indices)
    return None


def extra_from_blender_material(
    material: Any,
    material_name_to_index: dict[str, int],
    own_index: int,
) -> VrmcMaterialsMtoonxt | None:
    settings = getattr(material, "vrmxt_mtoonxt_settings", None)
    if settings is None:
        return None
    body = _stencil_from_settings(
        str(getattr(settings, "body_op", BODY_OP_OFF) or BODY_OP_OFF),
        getattr(settings, "body_targets", None),
        material_name_to_index,
        own_index,
        allow_same=False,
    )
    outline = _stencil_from_settings(
        str(getattr(settings, "outline_op", OUTLINE_OP_OFF) or OUTLINE_OP_OFF),
        getattr(settings, "outline_targets", None),
        material_name_to_index,
        own_index,
        allow_same=True,
    )
    if body is None and outline is None:
        return None
    return VrmcMaterialsMtoonxt(stencil=body, outline_stencil=outline)


def apply_mtoonxt_export(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

    name_to_index: dict[str, int] = dict(
        getattr(context, "material_name_to_index", {}) or {}
    )
    count = len(materials_raw)
    extras: list[VrmcMaterialsMtoonxt | None] = [None] * count

    for material_name, material_index in name_to_index.items():
        if material_index < 0 or material_index >= count:
            continue
        blender_material = _find_material_by_name(material_name)
        if blender_material is None:
            continue
        extras[material_index] = extra_from_blender_material(
            blender_material, name_to_index, material_index
        )

    wrote_any = False
    for material_index, material_entry in enumerate(materials_raw):
        material_dict = as_dict(material_entry)
        if material_dict is None:
            continue
        extra = extras[material_index]
        if extra is not None:
            if not listed_writers_have_body_write(extra.stencil, extras):
                extra.stencil = None
            if not listed_writers_have_body_write(extra.outline_stencil, extras):
                extra.outline_stencil = None
            if extra.stencil is None and extra.outline_stencil is None:
                extra = None
        if extra is None or not material_has_sibling_mtoon(material_dict):
            clear_mtoonxt_from_material_dict(material_dict)
            continue
        write_mtoonxt_to_material_dict(material_dict, extra)
        wrote_any = True

    if wrote_any:
        ensure_mtoonxt_extensions_used(json_dict)


def on_vrm1_export(context: Any) -> None:
    try:
        apply_mtoonxt_export(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM export
        logger.exception("VRMXT MToonXT export hook failed")


__all__ = ["apply_mtoonxt_export", "on_vrm1_export"]
