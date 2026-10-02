# SPDX-License-Identifier: MIT
"""glTF buffer helpers for replacing morph normals.

The VRM 1 exporter evaluates shape-key normals without modifiers, then strips
morph NORMAL accessors from MToon primitives. These helpers append dense
replacements onto the binary chunk the export hook still owns.
"""

from __future__ import annotations

import array
import struct
import sys
from collections.abc import Mapping, Sequence

Vec3 = tuple[float, float, float]

_FLOAT = 5126
_ARRAY_BUFFER = 34962
_INDEX_FORMATS = {5121: "<B", 5123: "<H", 5125: "<I"}
_INDEX_SIZES = {5121: 1, 5123: 2, 5125: 4}


def yup_to_zup(x: float, y: float, z: float) -> Vec3:
    """Inverse of the glTF exporter's ``zup2yup`` (x, y, z) -> (x, z, -y)."""
    return (x, -z, y)


def zup_to_yup(x: float, y: float, z: float) -> Vec3:
    """glTF exporter ``zup2yup``: Blender (x, y, z) -> glTF (x, z, -y)."""
    return (x, z, -y)


def quantize(value: float, digits: int = 5) -> float:
    return round(value, digits)


def choose_by_morph_delta(
    candidates: Sequence[int],
    gltf_deltas: Sequence[Vec3 | None],
    blender_deltas: Sequence[Mapping[int, Vec3]],
    *,
    epsilon: float = 1e-5,
) -> int:
    """Pick the Blender vertex whose shape-key delta matches the morph target.

    ``gltf_deltas`` and ``blender_deltas`` share target order. A target is
    useful when the candidate vertices do not all move the same way.
    """
    if len(candidates) == 1:
        return candidates[0]

    best_target = -1
    best_spread = epsilon
    for target_index, gltf_delta in enumerate(gltf_deltas):
        if gltf_delta is None or target_index >= len(blender_deltas):
            continue
        points = [
            blender_deltas[target_index].get(vertex)
            for vertex in candidates
            if vertex in blender_deltas[target_index]
        ]
        if len(points) < 2:
            continue
        spread = _spread(points)
        if spread > best_spread:
            best_spread = spread
            best_target = target_index

    if best_target < 0:
        return candidates[0]

    gltf_delta = gltf_deltas[best_target]
    assert gltf_delta is not None
    table = blender_deltas[best_target]
    return min(
        candidates,
        key=lambda vertex: _distance_sq(
            table.get(vertex, (0.0, 0.0, 0.0)),
            gltf_delta,
        ),
    )


def read_vec3_accessor(
    json_dict: Mapping[str, object],
    buffer: bytearray,
    accessor_index: object,
) -> list[Vec3] | None:
    """Read a float VEC3 accessor, expanding sparse data over a zero base."""
    accessors = json_dict.get("accessors")
    if not isinstance(accessor_index, int) or not isinstance(accessors, list):
        return None
    if not 0 <= accessor_index < len(accessors):
        return None
    accessor = accessors[accessor_index]
    if not isinstance(accessor, dict):
        return None
    if accessor.get("componentType") != _FLOAT or accessor.get("type") != "VEC3":
        return None
    count = accessor.get("count")
    if not isinstance(count, int) or count < 0:
        return None

    values = [(0.0, 0.0, 0.0)] * count
    buffer_view = accessor.get("bufferView")
    if buffer_view is not None:
        dense = _read_vec3_view(
            json_dict,
            buffer,
            buffer_view,
            int(accessor.get("byteOffset") or 0),
            count,
        )
        if dense is None:
            return None
        values = dense

    sparse = accessor.get("sparse")
    if isinstance(sparse, dict) and not _apply_sparse_vec3(
        json_dict, buffer, values, sparse
    ):
        return None
    return values


def read_vec2_accessor(
    json_dict: Mapping[str, object],
    buffer: bytearray,
    accessor_index: object,
) -> list[tuple[float, float]] | None:
    """Read a tightly packed or strided float VEC2 accessor."""
    accessors = json_dict.get("accessors")
    views = json_dict.get("bufferViews")
    if not isinstance(accessor_index, int) or not isinstance(accessors, list):
        return None
    if not isinstance(views, list) or not 0 <= accessor_index < len(accessors):
        return None
    accessor = accessors[accessor_index]
    if not isinstance(accessor, dict):
        return None
    if accessor.get("componentType") != _FLOAT or accessor.get("type") != "VEC2":
        return None
    count = accessor.get("count")
    buffer_view = accessor.get("bufferView")
    if not isinstance(count, int) or not isinstance(buffer_view, int):
        return None
    if not 0 <= buffer_view < len(views) or not isinstance(views[buffer_view], dict):
        return None
    view = views[buffer_view]
    start = int(view.get("byteOffset") or 0) + int(accessor.get("byteOffset") or 0)
    stride = view.get("byteStride")
    step = int(stride) if isinstance(stride, int) and stride >= 8 else 8
    end = start + (count - 1) * step + 8 if count else start
    if start < 0 or end > len(buffer):
        return None
    values: list[tuple[float, float]] = []
    for index in range(count):
        u, v = struct.unpack_from("<2f", buffer, start + index * step)
        values.append((u, v))
    return values


def append_vec3_accessor(
    json_dict: dict[str, object],
    buffer: bytearray,
    vectors: Sequence[Vec3],
) -> int:
    """Append a 4-byte-aligned dense float VEC3 accessor. Returns its index."""
    _pad4(buffer)
    byte_offset = len(buffer)
    floats = array.array("f")
    mins = [float("inf"), float("inf"), float("inf")]
    maxs = [float("-inf"), float("-inf"), float("-inf")]
    for vector in vectors:
        for axis, component in enumerate(vector):
            number = float(component)
            floats.append(number)
            mins[axis] = min(mins[axis], number)
            maxs[axis] = max(maxs[axis], number)
    if sys.byteorder != "little":
        floats.byteswap()
    blob = floats.tobytes()
    buffer.extend(blob)

    views = _ensure_list(json_dict, "bufferViews")
    accessors = _ensure_list(json_dict, "accessors")
    views.append(
        {
            "buffer": 0,
            "byteOffset": byte_offset,
            "byteLength": len(blob),
            "target": _ARRAY_BUFFER,
        }
    )
    accessors.append(
        {
            "bufferView": len(views) - 1,
            "byteOffset": 0,
            "componentType": _FLOAT,
            "count": len(vectors),
            "type": "VEC3",
            "min": mins,
            "max": maxs,
        }
    )
    buffers = json_dict.get("buffers")
    if isinstance(buffers, list) and buffers and isinstance(buffers[0], dict):
        buffers[0]["byteLength"] = len(buffer)
    return len(accessors) - 1


def rewrite_primitive_normals(
    json_dict: dict[str, object],
    buffer: bytearray,
    primitive: dict[str, object],
    assignments: Sequence[int | None],
    affected: set[int],
    basis_gltf: Mapping[int, Vec3],
    morph_gltf: Sequence[Mapping[int, Vec3]],
) -> int:
    """Replace one primitive's base and morph normals.

    ``assignments`` maps each glTF vertex to a Blender vertex, or None.
    Only Blender vertices in ``affected`` are overwritten. Other vertices keep
    the normal already stored on the primitive. Morph deltas for skipped or
    unaffected vertices are zero, which drops a stale shape-key normal the
    MToon strip may have left behind.
    """
    attributes = primitive.get("attributes")
    if not isinstance(attributes, dict):
        return 0
    count = len(assignments)
    if count == 0:
        return 0

    existing = read_vec3_accessor(json_dict, buffer, attributes.get("NORMAL"))
    if existing is None or len(existing) != count:
        existing = [(0.0, 0.0, 1.0)] * count

    rewritten = 0
    base: list[Vec3] = []
    for gltf_index, blender_index in enumerate(assignments):
        if blender_index is not None and blender_index in affected:
            normal = basis_gltf.get(blender_index)
            if normal is not None:
                base.append(normal)
                rewritten += 1
                continue
        base.append(existing[gltf_index])
    if rewritten == 0:
        return 0

    attributes["NORMAL"] = append_vec3_accessor(json_dict, buffer, base)

    targets = primitive.get("targets")
    if not isinstance(targets, list):
        return rewritten
    for target_index, target in enumerate(targets):
        if not isinstance(target, dict) or target_index >= len(morph_gltf):
            continue
        absolute = morph_gltf[target_index]
        deltas: list[Vec3] = []
        for _gltf_index, blender_index in enumerate(assignments):
            if (
                blender_index is not None
                and blender_index in affected
                and blender_index in absolute
                and blender_index in basis_gltf
            ):
                key_normal = absolute[blender_index]
                basis_normal = basis_gltf[blender_index]
                deltas.append(
                    (
                        key_normal[0] - basis_normal[0],
                        key_normal[1] - basis_normal[1],
                        key_normal[2] - basis_normal[2],
                    )
                )
            else:
                deltas.append((0.0, 0.0, 0.0))
        target["NORMAL"] = append_vec3_accessor(json_dict, buffer, deltas)
    return rewritten


def _spread(points: Sequence[Vec3 | None]) -> float:
    present = [point for point in points if point is not None]
    if len(present) < 2:
        return 0.0
    first = present[0]
    return max(_distance_sq(first, point) for point in present[1:])


def _distance_sq(left: Vec3, right: Vec3) -> float:
    return (
        (left[0] - right[0]) ** 2
        + (left[1] - right[1]) ** 2
        + (left[2] - right[2]) ** 2
    )


def _pad4(buffer: bytearray) -> None:
    remainder = len(buffer) % 4
    if remainder:
        buffer.extend(b"\x00" * (4 - remainder))


def _ensure_list(json_dict: dict[str, object], key: str) -> list[object]:
    value = json_dict.get(key)
    if not isinstance(value, list):
        value = []
        json_dict[key] = value
    return value


def _read_vec3_view(
    json_dict: Mapping[str, object],
    buffer: bytearray,
    buffer_view_index: object,
    byte_offset: int,
    count: int,
) -> list[Vec3] | None:
    views = json_dict.get("bufferViews")
    if not isinstance(buffer_view_index, int) or not isinstance(views, list):
        return None
    if not 0 <= buffer_view_index < len(views):
        return None
    view = views[buffer_view_index]
    if not isinstance(view, dict):
        return None
    start = int(view.get("byteOffset") or 0) + byte_offset
    stride = view.get("byteStride")
    step = int(stride) if isinstance(stride, int) and stride >= 12 else 12
    end = start + (count - 1) * step + 12 if count else start
    if start < 0 or end > len(buffer):
        return None
    values: list[Vec3] = []
    for index in range(count):
        offset = start + index * step
        x, y, z = struct.unpack_from("<3f", buffer, offset)
        values.append((x, y, z))
    return values


def _apply_sparse_vec3(
    json_dict: Mapping[str, object],
    buffer: bytearray,
    values: list[Vec3],
    sparse: Mapping[str, object],
) -> bool:
    sparse_count = sparse.get("count")
    indices = sparse.get("indices")
    sparse_values = sparse.get("values")
    if (
        not isinstance(sparse_count, int)
        or not isinstance(indices, dict)
        or not isinstance(sparse_values, dict)
    ):
        return False
    component_type = indices.get("componentType")
    if not isinstance(component_type, int) or component_type not in _INDEX_FORMATS:
        return False
    index_bytes = _read_view_slice(
        json_dict,
        buffer,
        indices.get("bufferView"),
        int(indices.get("byteOffset") or 0),
        sparse_count * _INDEX_SIZES[component_type],
    )
    value_bytes = _read_view_slice(
        json_dict,
        buffer,
        sparse_values.get("bufferView"),
        int(sparse_values.get("byteOffset") or 0),
        sparse_count * 12,
    )
    if index_bytes is None or value_bytes is None:
        return False
    index_fmt = _INDEX_FORMATS[component_type]
    index_size = _INDEX_SIZES[component_type]
    for sparse_index in range(sparse_count):
        vertex = struct.unpack_from(index_fmt, index_bytes, sparse_index * index_size)[
            0
        ]
        if not 0 <= vertex < len(values):
            return False
        x, y, z = struct.unpack_from("<3f", value_bytes, sparse_index * 12)
        values[vertex] = (x, y, z)
    return True


def _read_view_slice(
    json_dict: Mapping[str, object],
    buffer: bytearray,
    buffer_view_index: object,
    byte_offset: int,
    byte_length: int,
) -> bytes | None:
    views = json_dict.get("bufferViews")
    if not isinstance(buffer_view_index, int) or not isinstance(views, list):
        return None
    if not 0 <= buffer_view_index < len(views):
        return None
    view = views[buffer_view_index]
    if not isinstance(view, dict):
        return None
    start = int(view.get("byteOffset") or 0) + byte_offset
    end = start + byte_length
    if start < 0 or end > len(buffer):
        return None
    return bytes(buffer[start:end])
