# SPDX-License-Identifier: MIT
"""VRMC_materials_mtoonxt per-material glTF extension parse/serialize."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass

from ..common.constants import (
    EXTENSION_MATERIALS_MTOON,
    EXTENSION_MATERIALS_MTOONXT,
    SPEC_VERSION_1_0,
)
from ..common.json_util import (
    Json,
    as_dict,
    as_int,
    as_list,
    as_str,
    ensure_extensions_used,
    get_material_extension,
)

OP_WRITE = "write"
OP_INSIDE = "inside"
OP_INSIDE_OVERLAY = "insideOverlay"
OP_OUTSIDE = "outside"
OP_SAME = "same"

BODY_OPS = frozenset({OP_WRITE, OP_INSIDE, OP_INSIDE_OVERLAY, OP_OUTSIDE})
OUTLINE_OPS = frozenset({OP_WRITE, OP_INSIDE, OP_INSIDE_OVERLAY, OP_OUTSIDE, OP_SAME})
CLIP_OPS = frozenset({OP_INSIDE, OP_INSIDE_OVERLAY, OP_OUTSIDE})


@dataclass
class MtoonxtStencil:
    op: str
    materials: list[int] | None = None


@dataclass
class VrmcMaterialsMtoonxt:
    spec_version: str = SPEC_VERSION_1_0
    stencil: MtoonxtStencil | None = None
    outline_stencil: MtoonxtStencil | None = None


def uses_materials_list(op: str) -> bool:
    return op in CLIP_OPS


def parse_stencil(
    value: object,
    *,
    allow_same: bool,
    own_index: int | None = None,
    material_count: int | None = None,
) -> MtoonxtStencil | None:
    obj = as_dict(value)
    if obj is None:
        return None
    op = as_str(obj.get("op"))
    if op is None:
        return None
    allowed = OUTLINE_OPS if allow_same else BODY_OPS
    if op not in allowed:
        return None

    materials_raw = obj.get("materials")
    if op in (OP_WRITE, OP_SAME):
        if materials_raw is not None:
            return None
        return MtoonxtStencil(op=op, materials=None)

    items = as_list(materials_raw)
    if items is None or len(items) == 0:
        return None
    indices: list[int] = []
    seen: set[int] = set()
    for item in items:
        index = as_int(item)
        if index is None:
            return None
        if index < 0:
            return None
        if material_count is not None and index >= material_count:
            return None
        if own_index is not None and index == own_index:
            return None
        if index not in seen:
            seen.add(index)
            indices.append(index)
    if not indices:
        return None
    return MtoonxtStencil(op=op, materials=indices)


def parse_mtoonxt(
    extension: Mapping[str, Json],
    *,
    own_index: int | None = None,
    material_count: int | None = None,
) -> VrmcMaterialsMtoonxt | None:
    if as_str(extension.get("specVersion")) != SPEC_VERSION_1_0:
        return None
    stencil = None
    if "stencil" in extension:
        stencil = parse_stencil(
            extension.get("stencil"),
            allow_same=False,
            own_index=own_index,
            material_count=material_count,
        )
    outline = None
    if "outlineStencil" in extension:
        outline = parse_stencil(
            extension.get("outlineStencil"),
            allow_same=True,
            own_index=own_index,
            material_count=material_count,
        )
    return VrmcMaterialsMtoonxt(
        spec_version=SPEC_VERSION_1_0,
        stencil=stencil,
        outline_stencil=outline,
    )


def serialize_stencil(stencil: MtoonxtStencil) -> dict[str, Json]:
    result: dict[str, Json] = {"op": stencil.op}
    if uses_materials_list(stencil.op) and stencil.materials:
        result["materials"] = list(stencil.materials)
    return result


def serialize_mtoonxt(extension: VrmcMaterialsMtoonxt) -> dict[str, Json]:
    result: dict[str, Json] = {"specVersion": extension.spec_version}
    if extension.stencil is not None:
        result["stencil"] = serialize_stencil(extension.stencil)
    if extension.outline_stencil is not None:
        result["outlineStencil"] = serialize_stencil(extension.outline_stencil)
    return result


def write_mtoonxt_to_material_dict(
    material_dict: MutableMapping[str, Json],
    extension: VrmcMaterialsMtoonxt,
) -> None:
    write_raw_mtoonxt_to_material_dict(material_dict, serialize_mtoonxt(extension))


def write_raw_mtoonxt_to_material_dict(
    material_dict: MutableMapping[str, Json],
    extension_dict: Mapping[str, Json],
) -> None:
    extensions = material_dict.get("extensions")
    if not isinstance(extensions, dict):
        extensions = {}
        material_dict["extensions"] = extensions
    extensions[EXTENSION_MATERIALS_MTOONXT] = dict(extension_dict)


def clear_mtoonxt_from_material_dict(material_dict: MutableMapping[str, Json]) -> None:
    extensions = as_dict(material_dict.get("extensions"))
    if extensions is None or EXTENSION_MATERIALS_MTOONXT not in extensions:
        return
    del extensions[EXTENSION_MATERIALS_MTOONXT]
    if not extensions:
        material_dict.pop("extensions", None)


def material_has_sibling_mtoon(material_dict: Mapping[str, Json]) -> bool:
    return get_material_extension(material_dict, EXTENSION_MATERIALS_MTOON) is not None


def read_mtoonxt_from_material(
    material_dict: Mapping[str, Json],
    *,
    own_index: int | None = None,
    material_count: int | None = None,
) -> VrmcMaterialsMtoonxt | None:
    extension_dict = get_material_extension(material_dict, EXTENSION_MATERIALS_MTOONXT)
    if extension_dict is None:
        return None
    return parse_mtoonxt(
        extension_dict, own_index=own_index, material_count=material_count
    )


def listed_writers_have_body_write(
    stencil: MtoonxtStencil | None,
    extras_by_index: Sequence[VrmcMaterialsMtoonxt | None],
) -> bool:
    if stencil is None or not uses_materials_list(stencil.op) or not stencil.materials:
        return True
    count = len(extras_by_index)
    for index in stencil.materials:
        if index < 0 or index >= count:
            return False
        extra = extras_by_index[index]
        if extra is None or extra.stencil is None or extra.stencil.op != OP_WRITE:
            return False
    return True


def drop_unresolvable_stencils(
    extra: VrmcMaterialsMtoonxt,
    extras_by_index: Sequence[VrmcMaterialsMtoonxt | None],
) -> None:
    """Drop clip lists without writers, then dangling outline ``same``."""
    if not listed_writers_have_body_write(extra.stencil, extras_by_index):
        extra.stencil = None
    if extra.outline_stencil is not None and extra.outline_stencil.op == OP_SAME:
        if extra.stencil is None:
            extra.outline_stencil = None
    elif not listed_writers_have_body_write(extra.outline_stencil, extras_by_index):
        extra.outline_stencil = None


def ensure_mtoonxt_extensions_used(json_dict: MutableMapping[str, Json]) -> None:
    ensure_extensions_used(json_dict, EXTENSION_MATERIALS_MTOONXT)


__all__ = [
    "BODY_OPS",
    "CLIP_OPS",
    "OP_INSIDE",
    "OP_INSIDE_OVERLAY",
    "OP_OUTSIDE",
    "OP_SAME",
    "OP_WRITE",
    "OUTLINE_OPS",
    "MtoonxtStencil",
    "VrmcMaterialsMtoonxt",
    "clear_mtoonxt_from_material_dict",
    "drop_unresolvable_stencils",
    "ensure_mtoonxt_extensions_used",
    "listed_writers_have_body_write",
    "material_has_sibling_mtoon",
    "parse_mtoonxt",
    "parse_stencil",
    "read_mtoonxt_from_material",
    "serialize_mtoonxt",
    "serialize_stencil",
    "uses_materials_list",
    "write_mtoonxt_to_material_dict",
    "write_raw_mtoonxt_to_material_dict",
]
