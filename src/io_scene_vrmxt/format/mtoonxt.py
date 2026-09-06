# SPDX-License-Identifier: MIT
"""VRMXT_materials_mtoonxt root stencil graph parse/serialize."""

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
    get_root_extension,
)

OP_WRITE = "write"
OP_INSIDE = "inside"
OP_INSIDE_OVERLAY = "insideOverlay"
OP_OUTSIDE = "outside"
OP_SAME = "same"

BODY_OPS = frozenset({OP_WRITE, OP_INSIDE, OP_INSIDE_OVERLAY, OP_OUTSIDE})
OUTLINE_OPS = frozenset({OP_WRITE, OP_INSIDE, OP_INSIDE_OVERLAY, OP_OUTSIDE, OP_SAME})
CLIP_OPS = frozenset({OP_INSIDE, OP_INSIDE_OVERLAY, OP_OUTSIDE})

COMPARISON_INSIDE = "inside"
COMPARISON_OUTSIDE = "outside"
RELATIONSHIP_COMPARISONS = frozenset({COMPARISON_INSIDE, COMPARISON_OUTSIDE})

DEPTH_NEVER = "never"
DEPTH_LESS = "less"
DEPTH_EQUAL = "equal"
DEPTH_LESS_EQUAL = "lessEqual"
DEPTH_GREATER = "greater"
DEPTH_NOT_EQUAL = "notEqual"
DEPTH_GREATER_EQUAL = "greaterEqual"
DEPTH_ALWAYS = "always"
DEPTH_TESTS = frozenset(
    {
        DEPTH_NEVER,
        DEPTH_LESS,
        DEPTH_EQUAL,
        DEPTH_LESS_EQUAL,
        DEPTH_GREATER,
        DEPTH_NOT_EQUAL,
        DEPTH_GREATER_EQUAL,
        DEPTH_ALWAYS,
    }
)


@dataclass
class MtoonxtStencil:
    op: str
    materials: list[int] | None = None


@dataclass
class VrmxtMaterialsMtoonxt:
    spec_version: str = SPEC_VERSION_1_0
    stencil: MtoonxtStencil | None = None
    outline_stencil: MtoonxtStencil | None = None


@dataclass
class MtoonxtStencilRelationship:
    writers: list[int]
    readers: list[int]
    comparison: str = COMPARISON_OUTSIDE
    show_writers_through_occluders: bool = False
    writers_only_inside_readers: bool = False
    writers_only_outside_readers: bool = False
    writers_self_occlude: bool = True
    ignore_occluded_reader_areas: bool = True
    writers_write_color: bool = True
    writers_write_depth: bool = True
    readers_write_depth: bool = True
    writer_depth_test: str = DEPTH_LESS_EQUAL
    reader_depth_test: str = DEPTH_LESS_EQUAL


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
) -> VrmxtMaterialsMtoonxt | None:
    if as_str(extension.get("specVersion")) != SPEC_VERSION_1_0:
        return None
    # Stencil is authored only by the root graph; retired material shorthand is ignored.
    return VrmxtMaterialsMtoonxt(spec_version=SPEC_VERSION_1_0)


def serialize_stencil(stencil: MtoonxtStencil) -> dict[str, Json]:
    result: dict[str, Json] = {"op": stencil.op}
    if uses_materials_list(stencil.op) and stencil.materials:
        result["materials"] = list(stencil.materials)
    return result


def serialize_mtoonxt(extension: VrmxtMaterialsMtoonxt) -> dict[str, Json]:
    return {"specVersion": extension.spec_version}


def _parse_material_indices(
    value: object,
    *,
    material_count: int | None,
) -> list[int] | None:
    items = as_list(value)
    if items is None or not items:
        return None
    indices: list[int] = []
    seen: set[int] = set()
    for item in items:
        index = as_int(item)
        if index is None or index < 0:
            return None
        if material_count is not None and index >= material_count:
            return None
        if index not in seen:
            seen.add(index)
            indices.append(index)
    return indices or None


def _bool_or_default(obj: Mapping[str, Json], key: str, default: bool) -> bool | None:
    value = obj.get(key, default)
    return value if isinstance(value, bool) else None


def parse_stencil_relationship(
    value: object,
    *,
    material_count: int | None = None,
) -> MtoonxtStencilRelationship | None:
    obj = as_dict(value)
    if obj is None:
        return None
    writers = _parse_material_indices(obj.get("writers"), material_count=material_count)
    readers = _parse_material_indices(obj.get("readers"), material_count=material_count)
    if writers is None or readers is None or set(writers).intersection(readers):
        return None
    comparison = as_str(obj.get("comparison", COMPARISON_OUTSIDE))
    writer_depth_test = as_str(obj.get("writerDepthTest", DEPTH_LESS_EQUAL))
    reader_depth_test = as_str(obj.get("readerDepthTest", DEPTH_LESS_EQUAL))
    if comparison not in RELATIONSHIP_COMPARISONS:
        return None
    if writer_depth_test not in DEPTH_TESTS or reader_depth_test not in DEPTH_TESTS:
        return None
    values = {
        "show_writers_through_occluders": _bool_or_default(
            obj, "showWritersThroughOccluders", False
        ),
        "writers_only_inside_readers": _bool_or_default(
            obj, "writersOnlyInsideReaders", False
        ),
        "writers_only_outside_readers": _bool_or_default(
            obj, "writersOnlyOutsideReaders", False
        ),
        "writers_self_occlude": _bool_or_default(obj, "writersSelfOcclude", True),
        "ignore_occluded_reader_areas": _bool_or_default(
            obj, "ignoreOccludedReaderAreas", True
        ),
        "writers_write_color": _bool_or_default(obj, "writersWriteColor", True),
        "writers_write_depth": _bool_or_default(obj, "writersWriteDepth", True),
        "readers_write_depth": _bool_or_default(obj, "readersWriteDepth", True),
    }
    if any(value is None for value in values.values()):
        return None
    if values["writers_only_inside_readers"] and values["writers_only_outside_readers"]:
        return None
    return MtoonxtStencilRelationship(
        writers=writers,
        readers=readers,
        comparison=comparison,
        writer_depth_test=writer_depth_test,
        reader_depth_test=reader_depth_test,
        **values,
    )


def parse_stencil_relationships(
    json_dict: Mapping[str, Json],
    *,
    material_count: int | None = None,
) -> list[MtoonxtStencilRelationship]:
    extension = get_root_extension(json_dict, EXTENSION_MATERIALS_MTOONXT)
    if extension is None or as_str(extension.get("specVersion")) != SPEC_VERSION_1_0:
        return []
    values = as_list(extension.get("stencil"))
    if values is None:
        return []
    result: list[MtoonxtStencilRelationship] = []
    for value in values:
        relationship = parse_stencil_relationship(value, material_count=material_count)
        if relationship is not None:
            result.append(relationship)
    return result


def serialize_stencil_relationship(
    relationship: MtoonxtStencilRelationship,
) -> dict[str, Json]:
    result: dict[str, Json] = {
        "writers": list(relationship.writers),
        "readers": list(relationship.readers),
    }
    optional = (
        ("comparison", relationship.comparison, COMPARISON_OUTSIDE),
        (
            "showWritersThroughOccluders",
            relationship.show_writers_through_occluders,
            False,
        ),
        (
            "writersOnlyInsideReaders",
            relationship.writers_only_inside_readers,
            False,
        ),
        (
            "writersOnlyOutsideReaders",
            relationship.writers_only_outside_readers,
            False,
        ),
        ("writersSelfOcclude", relationship.writers_self_occlude, True),
        (
            "ignoreOccludedReaderAreas",
            relationship.ignore_occluded_reader_areas,
            True,
        ),
        ("writersWriteColor", relationship.writers_write_color, True),
        ("writersWriteDepth", relationship.writers_write_depth, True),
        ("readersWriteDepth", relationship.readers_write_depth, True),
        ("writerDepthTest", relationship.writer_depth_test, DEPTH_LESS_EQUAL),
        ("readerDepthTest", relationship.reader_depth_test, DEPTH_LESS_EQUAL),
    )
    for key, value, default in optional:
        if value != default:
            result[key] = value
    return result


def coalesce_stencil_relationships(
    relationships: Sequence[MtoonxtStencilRelationship],
) -> list[MtoonxtStencilRelationship]:
    """Merge identical writer presentations by unioning their reader materials.

    One material pass can stamp one stencil reference. Keeping equivalent rows with
    the same writers but disjoint readers would make a consumer's later row replace
    the earlier stencil state. The schema already supports reader arrays, so emit one
    relationship instead.
    """

    result: list[MtoonxtStencilRelationship] = []
    by_key: dict[tuple[object, ...], MtoonxtStencilRelationship] = {}
    for relationship in relationships:
        key = (
            tuple(sorted(set(relationship.writers))),
            relationship.comparison,
            relationship.show_writers_through_occluders,
            relationship.writers_only_inside_readers,
            relationship.writers_only_outside_readers,
            relationship.writers_self_occlude,
            relationship.ignore_occluded_reader_areas,
            relationship.writers_write_color,
            relationship.writers_write_depth,
            relationship.readers_write_depth,
            relationship.writer_depth_test,
            relationship.reader_depth_test,
        )
        existing = by_key.get(key)
        if existing is None:
            existing = MtoonxtStencilRelationship(
                writers=list(dict.fromkeys(relationship.writers)),
                readers=list(dict.fromkeys(relationship.readers)),
                comparison=relationship.comparison,
                show_writers_through_occluders=(
                    relationship.show_writers_through_occluders
                ),
                writers_only_inside_readers=(relationship.writers_only_inside_readers),
                writers_only_outside_readers=(
                    relationship.writers_only_outside_readers
                ),
                writers_self_occlude=relationship.writers_self_occlude,
                ignore_occluded_reader_areas=(
                    relationship.ignore_occluded_reader_areas
                ),
                writers_write_color=relationship.writers_write_color,
                writers_write_depth=relationship.writers_write_depth,
                readers_write_depth=relationship.readers_write_depth,
                writer_depth_test=relationship.writer_depth_test,
                reader_depth_test=relationship.reader_depth_test,
            )
            by_key[key] = existing
            result.append(existing)
            continue
        for reader in relationship.readers:
            if reader not in existing.readers and reader not in existing.writers:
                existing.readers.append(reader)
    return result


def write_stencil_relationships(
    json_dict: MutableMapping[str, Json],
    relationships: Sequence[MtoonxtStencilRelationship],
) -> None:
    root_extensions = json_dict.get("extensions")
    if not isinstance(root_extensions, dict):
        root_extensions = {}
        json_dict["extensions"] = root_extensions
    previous = as_dict(root_extensions.get(EXTENSION_MATERIALS_MTOONXT))
    if previous is not None:
        previous.pop("stencilRelationships", None)
    if not relationships:
        current = as_dict(root_extensions.get(EXTENSION_MATERIALS_MTOONXT))
        if current is not None:
            current.pop("stencil", None)
            if set(current) <= {"specVersion"}:
                root_extensions.pop(EXTENSION_MATERIALS_MTOONXT, None)
        if not root_extensions:
            json_dict.pop("extensions", None)
        return
    current = as_dict(root_extensions.get(EXTENSION_MATERIALS_MTOONXT))
    if current is None:
        current = {}
        root_extensions[EXTENSION_MATERIALS_MTOONXT] = current
    current["specVersion"] = SPEC_VERSION_1_0
    serialized_relationships: list[dict[str, Json]] = []
    for relationship in coalesce_stencil_relationships(relationships):
        serialized = serialize_stencil_relationship(relationship)
        if serialized not in serialized_relationships:
            serialized_relationships.append(serialized)
    current["stencil"] = serialized_relationships
    ensure_mtoonxt_extensions_used(json_dict)


def write_mtoonxt_to_material_dict(
    material_dict: MutableMapping[str, Json],
    extension: VrmxtMaterialsMtoonxt,
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
) -> VrmxtMaterialsMtoonxt | None:
    extension_dict = get_material_extension(material_dict, EXTENSION_MATERIALS_MTOONXT)
    if extension_dict is None:
        return None
    return parse_mtoonxt(
        extension_dict, own_index=own_index, material_count=material_count
    )


def listed_writers_have_body_write(
    stencil: MtoonxtStencil | None,
    extras_by_index: Sequence[VrmxtMaterialsMtoonxt | None],
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
    extra: VrmxtMaterialsMtoonxt,
    extras_by_index: Sequence[VrmxtMaterialsMtoonxt | None],
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
    "COMPARISON_INSIDE",
    "COMPARISON_OUTSIDE",
    "CLIP_OPS",
    "DEPTH_ALWAYS",
    "DEPTH_EQUAL",
    "DEPTH_GREATER",
    "DEPTH_GREATER_EQUAL",
    "DEPTH_LESS",
    "DEPTH_LESS_EQUAL",
    "DEPTH_NEVER",
    "DEPTH_NOT_EQUAL",
    "DEPTH_TESTS",
    "OP_INSIDE",
    "OP_INSIDE_OVERLAY",
    "OP_OUTSIDE",
    "OP_SAME",
    "OP_WRITE",
    "OUTLINE_OPS",
    "MtoonxtStencil",
    "MtoonxtStencilRelationship",
    "VrmxtMaterialsMtoonxt",
    "clear_mtoonxt_from_material_dict",
    "drop_unresolvable_stencils",
    "ensure_mtoonxt_extensions_used",
    "listed_writers_have_body_write",
    "material_has_sibling_mtoon",
    "parse_mtoonxt",
    "parse_stencil",
    "parse_stencil_relationship",
    "parse_stencil_relationships",
    "read_mtoonxt_from_material",
    "serialize_mtoonxt",
    "serialize_stencil",
    "serialize_stencil_relationship",
    "uses_materials_list",
    "write_mtoonxt_to_material_dict",
    "write_raw_mtoonxt_to_material_dict",
    "write_stencil_relationships",
]
