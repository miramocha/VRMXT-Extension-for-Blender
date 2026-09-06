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

COMPARISON_INSIDE = "inside"
COMPARISON_OUTSIDE = "outside"
STENCIL_COMPARISONS = frozenset({COMPARISON_INSIDE, COMPARISON_OUTSIDE})

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


@dataclass
class VrmxtMaterialsMtoonxt:
    spec_version: str = SPEC_VERSION_1_0


def parse_mtoonxt(extension: Mapping[str, Json]) -> VrmxtMaterialsMtoonxt | None:
    if as_str(extension.get("specVersion")) != SPEC_VERSION_1_0:
        return None
    # Stencil is authored only by the root graph; retired material shorthand is ignored.
    return VrmxtMaterialsMtoonxt(spec_version=SPEC_VERSION_1_0)


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


def parse_stencil(
    value: object,
    *,
    material_count: int | None = None,
) -> MtoonxtStencil | None:
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
    if comparison not in STENCIL_COMPARISONS:
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
    return MtoonxtStencil(
        writers=writers,
        readers=readers,
        comparison=comparison,
        writer_depth_test=writer_depth_test,
        reader_depth_test=reader_depth_test,
        **values,
    )


def parse_stencils(
    json_dict: Mapping[str, Json],
    *,
    material_count: int | None = None,
) -> list[MtoonxtStencil]:
    extension = get_root_extension(json_dict, EXTENSION_MATERIALS_MTOONXT)
    if extension is None or as_str(extension.get("specVersion")) != SPEC_VERSION_1_0:
        return []
    values = as_list(extension.get("stencil"))
    if values is None:
        return []
    result: list[MtoonxtStencil] = []
    for value in values:
        stencil = parse_stencil(value, material_count=material_count)
        if stencil is not None:
            result.append(stencil)
    return result


def serialize_stencil(stencil: MtoonxtStencil) -> dict[str, Json]:
    result: dict[str, Json] = {
        "writers": list(stencil.writers),
        "readers": list(stencil.readers),
    }
    optional = (
        ("comparison", stencil.comparison, COMPARISON_OUTSIDE),
        (
            "showWritersThroughOccluders",
            stencil.show_writers_through_occluders,
            False,
        ),
        (
            "writersOnlyInsideReaders",
            stencil.writers_only_inside_readers,
            False,
        ),
        (
            "writersOnlyOutsideReaders",
            stencil.writers_only_outside_readers,
            False,
        ),
        ("writersSelfOcclude", stencil.writers_self_occlude, True),
        (
            "ignoreOccludedReaderAreas",
            stencil.ignore_occluded_reader_areas,
            True,
        ),
        ("writersWriteColor", stencil.writers_write_color, True),
        ("writersWriteDepth", stencil.writers_write_depth, True),
        ("readersWriteDepth", stencil.readers_write_depth, True),
        ("writerDepthTest", stencil.writer_depth_test, DEPTH_LESS_EQUAL),
        ("readerDepthTest", stencil.reader_depth_test, DEPTH_LESS_EQUAL),
    )
    for key, value, default in optional:
        if value != default:
            result[key] = value
    return result


def coalesce_stencils(stencils: Sequence[MtoonxtStencil]) -> list[MtoonxtStencil]:
    """Merge identical writer presentations by unioning their reader materials.

    One material pass can stamp one stencil reference. Keeping equivalent rows with
    the same writers but disjoint readers would make a consumer's later row replace
    the earlier stencil state. The schema already supports reader arrays, so emit one
    stencil instead.
    """

    result: list[MtoonxtStencil] = []
    by_key: dict[tuple[object, ...], MtoonxtStencil] = {}
    for stencil in stencils:
        key = (
            tuple(sorted(set(stencil.writers))),
            stencil.comparison,
            stencil.show_writers_through_occluders,
            stencil.writers_only_inside_readers,
            stencil.writers_only_outside_readers,
            stencil.writers_self_occlude,
            stencil.ignore_occluded_reader_areas,
            stencil.writers_write_color,
            stencil.writers_write_depth,
            stencil.readers_write_depth,
            stencil.writer_depth_test,
            stencil.reader_depth_test,
        )
        existing = by_key.get(key)
        if existing is None:
            existing = MtoonxtStencil(
                writers=list(dict.fromkeys(stencil.writers)),
                readers=list(dict.fromkeys(stencil.readers)),
                comparison=stencil.comparison,
                show_writers_through_occluders=(stencil.show_writers_through_occluders),
                writers_only_inside_readers=(stencil.writers_only_inside_readers),
                writers_only_outside_readers=(stencil.writers_only_outside_readers),
                writers_self_occlude=stencil.writers_self_occlude,
                ignore_occluded_reader_areas=(stencil.ignore_occluded_reader_areas),
                writers_write_color=stencil.writers_write_color,
                writers_write_depth=stencil.writers_write_depth,
                readers_write_depth=stencil.readers_write_depth,
                writer_depth_test=stencil.writer_depth_test,
                reader_depth_test=stencil.reader_depth_test,
            )
            by_key[key] = existing
            result.append(existing)
            continue
        for reader in stencil.readers:
            if reader not in existing.readers and reader not in existing.writers:
                existing.readers.append(reader)
    return result


def write_stencil(
    json_dict: MutableMapping[str, Json],
    stencils: Sequence[MtoonxtStencil],
) -> None:
    root_extensions = json_dict.get("extensions")
    if not isinstance(root_extensions, dict):
        root_extensions = {}
        json_dict["extensions"] = root_extensions
    previous = as_dict(root_extensions.get(EXTENSION_MATERIALS_MTOONXT))
    if previous is not None:
        previous.pop("stencilRelationships", None)
    if not stencils:
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
    serialized_stencils: list[dict[str, Json]] = []
    for stencil in coalesce_stencils(stencils):
        serialized = serialize_stencil(stencil)
        if serialized not in serialized_stencils:
            serialized_stencils.append(serialized)
    current["stencil"] = serialized_stencils
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
) -> VrmxtMaterialsMtoonxt | None:
    extension_dict = get_material_extension(material_dict, EXTENSION_MATERIALS_MTOONXT)
    if extension_dict is None:
        return None
    return parse_mtoonxt(extension_dict)


def ensure_mtoonxt_extensions_used(json_dict: MutableMapping[str, Json]) -> None:
    ensure_extensions_used(json_dict, EXTENSION_MATERIALS_MTOONXT)


__all__ = [
    "COMPARISON_INSIDE",
    "COMPARISON_OUTSIDE",
    "DEPTH_ALWAYS",
    "DEPTH_EQUAL",
    "DEPTH_GREATER",
    "DEPTH_GREATER_EQUAL",
    "DEPTH_LESS",
    "DEPTH_LESS_EQUAL",
    "DEPTH_NEVER",
    "DEPTH_NOT_EQUAL",
    "DEPTH_TESTS",
    "STENCIL_COMPARISONS",
    "MtoonxtStencil",
    "VrmxtMaterialsMtoonxt",
    "clear_mtoonxt_from_material_dict",
    "coalesce_stencils",
    "ensure_mtoonxt_extensions_used",
    "material_has_sibling_mtoon",
    "parse_mtoonxt",
    "parse_stencil",
    "parse_stencils",
    "read_mtoonxt_from_material",
    "serialize_mtoonxt",
    "serialize_stencil",
    "write_mtoonxt_to_material_dict",
    "write_raw_mtoonxt_to_material_dict",
    "write_stencil",
]
