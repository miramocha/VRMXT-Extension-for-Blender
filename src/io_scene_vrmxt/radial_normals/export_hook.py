# SPDX-License-Identifier: MIT
"""Sample Normal Edit modifiers into VRM 1 morph NORMAL accessors."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .gltf_normals import (
    Vec3,
    choose_by_morph_delta,
    quantize,
    read_vec2_accessor,
    read_vec3_accessor,
    rewrite_primitive_normals,
    yup_to_zup,
    zup_to_yup,
)

logger = logging.getLogger(__name__)

_POSITION_DIGITS = 5
_UV_DIGITS = 5
_MOVE_EPSILON = 1e-8
_MATCH_EPSILON_SQ = 1e-6


def on_vrm1_export(context: Any) -> dict[str, int]:
    """Rewrite morph normals for objects that still have a Normal Edit modifier."""
    stats = {"meshes": 0, "vertices": 0, "unmatched": 0}
    json_dict = getattr(context, "json_dict", None)
    buffer = getattr(context, "buffer0", None)
    if not isinstance(json_dict, dict) or not isinstance(buffer, bytearray):
        return stats
    nodes = json_dict.get("nodes")
    meshes = json_dict.get("meshes")
    if not isinstance(nodes, list) or not isinstance(meshes, list):
        return stats

    node_index_to_object = getattr(context, "node_index_to_object", {}) or {}
    material_index_to_material = (
        getattr(context, "material_index_to_material", {}) or {}
    )
    armature = getattr(context, "armature", None)
    rewritten_mesh_indices: set[int] = set()

    for node_index, obj in node_index_to_object.items():
        if not isinstance(node_index, int) or not _has_enabled_normal_edit(obj):
            continue
        if not 0 <= node_index < len(nodes) or not isinstance(nodes[node_index], dict):
            continue
        mesh_index = nodes[node_index].get("mesh")
        if not isinstance(mesh_index, int) or not 0 <= mesh_index < len(meshes):
            continue
        if mesh_index in rewritten_mesh_indices:
            logger.warning(
                "VRMXT radial normals: skip shared glTF mesh %s on %s",
                mesh_index,
                getattr(obj, "name", "?"),
            )
            continue
        mesh_dict = meshes[mesh_index]
        if not isinstance(mesh_dict, dict):
            continue
        try:
            rewritten, unmatched = _rewrite_object(
                obj,
                mesh_dict,
                json_dict,
                buffer,
                material_index_to_material,
                armature,
            )
        except Exception:
            logger.exception(
                "VRMXT radial normals: failed on %s",
                getattr(obj, "name", "?"),
            )
            continue
        if rewritten:
            rewritten_mesh_indices.add(mesh_index)
            stats["meshes"] += 1
            stats["vertices"] += rewritten
            stats["unmatched"] += unmatched

    if stats["meshes"]:
        logger.info(
            "VRMXT radial normals: rewrote %s glTF vertices on %s mesh(es)"
            " (%s unmatched)",
            stats["vertices"],
            stats["meshes"],
            stats["unmatched"],
        )
    return stats


def _has_enabled_normal_edit(obj: Any) -> bool:
    return bool(_enabled_normal_edits(obj))


def _enabled_normal_edits(obj: Any) -> list[Any]:
    modifiers = getattr(obj, "modifiers", None)
    if modifiers is None:
        return []
    return [
        modifier
        for modifier in modifiers
        if getattr(modifier, "type", None) == "NORMAL_EDIT"
        and getattr(modifier, "show_viewport", True)
    ]


def _rewrite_object(
    obj: Any,
    mesh_dict: dict[str, Any],
    json_dict: dict[str, Any],
    buffer: bytearray,
    material_index_to_material: Mapping[int, Any],
    armature: Any,
) -> tuple[int, int]:
    mesh = getattr(obj, "data", None)
    if mesh is None or not hasattr(mesh, "loops"):
        return 0, 0
    modifiers = _enabled_normal_edits(obj)
    affected = _affected_vertices(obj, modifiers)
    if not affected:
        return 0, 0

    primitives = mesh_dict.get("primitives")
    if not isinstance(primitives, list):
        return 0, 0
    target_names = _target_names(mesh_dict)
    basis_object, moving_keys = _basis_and_moving_keys(mesh, target_names, affected)
    normal_matrix = _skinned_normal_matrix(obj, armature)

    rewritten = 0
    unmatched = 0
    with _sampling_pose(obj):
        basis_local = _evaluated_normals(obj, affected)
        morph_local: list[dict[int, Any]] = []
        for key_name, moves in moving_keys:
            if not moves:
                morph_local.append({})
                continue
            _set_only_shape_key(mesh, key_name)
            morph_local.append(_evaluated_normals(obj, affected))
            _set_only_shape_key(mesh, None)

        basis_gltf = {
            vertex: _object_normal_to_gltf(normal, normal_matrix)
            for vertex, normal in basis_local.items()
        }
        morph_gltf = [
            {
                vertex: _object_normal_to_gltf(normal, normal_matrix)
                for vertex, normal in absolute.items()
            }
            for absolute in morph_local
        ]
        blender_deltas = _object_space_key_deltas(mesh, target_names, affected)

        for primitive in primitives:
            if not isinstance(primitive, dict):
                continue
            slot = _material_slot(obj, primitive, material_index_to_material)
            assignments, missed = _assign_primitive(
                obj,
                mesh,
                primitive,
                json_dict,
                buffer,
                slot,
                affected,
                basis_object,
                blender_deltas,
            )
            unmatched += missed
            rewritten += rewrite_primitive_normals(
                json_dict,
                buffer,
                primitive,
                assignments,
                affected,
                basis_gltf,
                morph_gltf,
            )
    return rewritten, unmatched


def _target_names(mesh_dict: Mapping[str, Any]) -> list[str]:
    extras = mesh_dict.get("extras")
    if not isinstance(extras, dict):
        return []
    names = extras.get("targetNames")
    if not isinstance(names, list):
        return []
    return [name for name in names if isinstance(name, str)]


def _basis_and_moving_keys(
    mesh: Any,
    target_names: Sequence[str],
    affected: set[int],
) -> tuple[Any, list[tuple[str, bool]]]:
    shape_keys = getattr(mesh, "shape_keys", None)
    key_blocks = getattr(shape_keys, "key_blocks", None) if shape_keys else None
    basis = key_blocks[0] if key_blocks else None
    moving: list[tuple[str, bool]] = []
    for name in target_names:
        key = key_blocks.get(name) if key_blocks else None
        moves = bool(
            basis is not None and key is not None and _key_moves(basis, key, affected)
        )
        moving.append((name, moves))
    return basis, moving


def _key_moves(basis: Any, key: Any, affected: set[int]) -> bool:
    for vertex in affected:
        delta = key.data[vertex].co - basis.data[vertex].co
        if delta.length_squared > _MOVE_EPSILON:
            return True
    return False


def _object_space_key_deltas(
    mesh: Any,
    target_names: Sequence[str],
    affected: set[int],
) -> list[dict[int, Vec3]]:
    shape_keys = getattr(mesh, "shape_keys", None)
    key_blocks = getattr(shape_keys, "key_blocks", None) if shape_keys else None
    basis = key_blocks[0] if key_blocks else None
    tables: list[dict[int, Vec3]] = []
    for name in target_names:
        table: dict[int, Vec3] = {}
        key = None
        if key_blocks is not None and basis is not None:
            key = key_blocks.get(name)
        if key is not None and basis is not None:
            for vertex in affected:
                delta = key.data[vertex].co - basis.data[vertex].co
                table[vertex] = (float(delta.x), float(delta.y), float(delta.z))
        tables.append(table)
    return tables


def _affected_vertices(obj: Any, modifiers: Sequence[Any]) -> set[int]:
    mesh = obj.data
    count = len(mesh.vertices)
    affected: set[int] = set()
    for modifier in modifiers:
        group_name = getattr(modifier, "vertex_group", "") or ""
        invert = bool(getattr(modifier, "invert_vertex_group", False))
        if not group_name:
            affected.update(range(count))
            continue
        group = obj.vertex_groups.get(group_name)
        if group is None:
            affected.update(range(count))
            continue
        for vertex in mesh.vertices:
            try:
                weight = group.weight(vertex.index)
            except RuntimeError:
                weight = 0.0
            in_group = weight > 1e-8
            if in_group != invert:
                affected.add(vertex.index)
    return affected


def _skinned_normal_matrix(obj: Any, fallback_armature: Any) -> Any:
    from mathutils import Matrix

    armature = fallback_armature
    for modifier in getattr(obj, "modifiers", []):
        if getattr(modifier, "type", None) == "ARMATURE" and getattr(
            modifier, "object", None
        ):
            armature = modifier.object
            break
    if armature is None or not hasattr(armature, "matrix_world"):
        return Matrix.Identity(3)
    apply = (armature.matrix_world.inverted() @ obj.matrix_world).to_3x3()
    apply = apply.inverted().transposed()
    return armature.matrix_world.to_3x3() @ apply


def _object_normal_to_gltf(normal: Any, normal_matrix: Any) -> Vec3:
    transformed = (normal_matrix @ normal).normalized()
    return zup_to_yup(float(transformed.x), float(transformed.y), float(transformed.z))


def _assign_primitive(
    obj: Any,
    mesh: Any,
    primitive: Mapping[str, Any],
    json_dict: Mapping[str, object],
    buffer: bytearray,
    slot: int | None,
    affected: set[int],
    basis: Any,
    blender_deltas: Sequence[Mapping[int, Vec3]],
) -> tuple[list[int | None], int]:
    attributes = primitive.get("attributes")
    if not isinstance(attributes, dict):
        return [], 0
    positions = read_vec3_accessor(json_dict, buffer, attributes.get("POSITION"))
    if not positions:
        return [], 0
    texcoord_accessors = [
        attributes[name]
        for name in sorted(attributes)
        if isinstance(name, str) and name.startswith("TEXCOORD_")
    ]
    texcoords = [
        read_vec2_accessor(json_dict, buffer, accessor)
        for accessor in texcoord_accessors
    ]
    layer_count = len(texcoords)
    morph_positions = _morph_position_deltas(
        primitive, json_dict, buffer, len(positions)
    )
    world = obj.matrix_world
    world_inv = world.inverted()
    world_3x3_inv = world.to_3x3().inverted()

    records = _loop_records(mesh, basis, slot, affected)
    buckets: dict[tuple[float, ...], list[int]] = defaultdict(list)
    position_buckets: dict[tuple[float, ...], list[int]] = defaultdict(list)
    for vertex, position, uvs in records:
        position_buckets[_bucket_key(position, [])].append(vertex)
        buckets[_bucket_key(position, uvs[:layer_count])].append(vertex)

    assignments: list[int | None] = []
    unmatched = 0
    for index, gltf_position in enumerate(positions):
        object_position = world_inv @ _vec(yup_to_zup(*gltf_position))
        object_uvs = []
        for layer in texcoords:
            if layer is None or index >= len(layer):
                object_uvs.append(None)
                continue
            u, v = layer[index][0], layer[index][1]
            object_uvs.append((u, 1.0 - v))
        candidates = buckets.get(_bucket_key(object_position, object_uvs), [])
        if not candidates:
            candidates = _nearest(records, object_position, object_uvs, layer_count)
        if not candidates:
            near = position_buckets.get(_bucket_key(object_position, []), [])
            if near:
                unmatched += 1
            assignments.append(None)
            continue
        unique = list(dict.fromkeys(candidates))
        if len(unique) == 1:
            assignments.append(unique[0])
            continue
        gltf_deltas = []
        for target_deltas in morph_positions:
            if target_deltas is None or index >= len(target_deltas):
                gltf_deltas.append(None)
                continue
            delta = world_3x3_inv @ _vec(yup_to_zup(*target_deltas[index]))
            gltf_deltas.append((float(delta.x), float(delta.y), float(delta.z)))
        assignments.append(choose_by_morph_delta(unique, gltf_deltas, blender_deltas))
    return assignments, unmatched


def _morph_position_deltas(
    primitive: Mapping[str, Any],
    json_dict: Mapping[str, object],
    buffer: bytearray,
    count: int,
) -> list[list[Vec3] | None]:
    targets = primitive.get("targets")
    if not isinstance(targets, list):
        return []
    deltas: list[list[Vec3] | None] = []
    for target in targets:
        if not isinstance(target, dict):
            deltas.append(None)
            continue
        values = read_vec3_accessor(json_dict, buffer, target.get("POSITION"))
        if values is None or len(values) != count:
            deltas.append(None)
        else:
            deltas.append(values)
    return deltas


def _loop_records(
    mesh: Any,
    basis: Any,
    slot: int | None,
    affected: set[int],
) -> list[tuple[int, Any, list[tuple[float, float] | None]]]:
    uv_layers = list(getattr(mesh, "uv_layers", []) or [])
    records = []
    for polygon in mesh.polygons:
        if slot is not None and polygon.material_index != slot:
            continue
        for loop_index in polygon.loop_indices:
            vertex = mesh.loops[loop_index].vertex_index
            if vertex not in affected:
                continue
            if basis is not None:
                position = basis.data[vertex].co
            else:
                position = mesh.vertices[vertex].co
            uvs: list[tuple[float, float] | None] = []
            for layer in uv_layers:
                uv = layer.data[loop_index].uv
                uvs.append((float(uv.x), float(uv.y)))
            records.append((vertex, position, uvs))
    return records


def _bucket_key(
    position: Any, uvs: Sequence[tuple[float, float] | None]
) -> tuple[float, ...]:
    key = [
        quantize(float(position.x), _POSITION_DIGITS),
        quantize(float(position.y), _POSITION_DIGITS),
        quantize(float(position.z), _POSITION_DIGITS),
    ]
    for uv in uvs:
        if uv is None:
            continue
        key.append(quantize(uv[0], _UV_DIGITS))
        key.append(quantize(uv[1], _UV_DIGITS))
    return tuple(key)


def _nearest(
    records: Sequence[tuple[int, Any, list[tuple[float, float] | None]]],
    position: Any,
    uvs: Sequence[tuple[float, float] | None],
    layer_count: int,
) -> list[int]:
    best: list[int] = []
    best_distance = _MATCH_EPSILON_SQ
    for vertex, record_position, record_uvs in records:
        delta = record_position - position
        distance = float(delta.length_squared)
        if distance > best_distance:
            continue
        if not _uvs_close(record_uvs[:layer_count], uvs):
            continue
        if distance < best_distance:
            best_distance = distance
            best = [vertex]
        else:
            best.append(vertex)
    return best


def _uvs_close(
    record_uvs: Sequence[tuple[float, float] | None],
    gltf_uvs: Sequence[tuple[float, float] | None],
) -> bool:
    for record_uv, gltf_uv in zip(record_uvs, gltf_uvs):
        if record_uv is None or gltf_uv is None:
            continue
        if (
            abs(record_uv[0] - gltf_uv[0]) > 1e-3
            or abs(record_uv[1] - gltf_uv[1]) > 1e-3
        ):
            return False
    return True


def _material_slot(
    obj: Any,
    primitive: Mapping[str, Any],
    material_index_to_material: Mapping[int, Any],
) -> int | None:
    material_index = primitive.get("material")
    if not isinstance(material_index, int):
        return None
    material = material_index_to_material.get(material_index)
    material_name = getattr(material, "name", None)
    if not isinstance(material_name, str):
        return None
    for slot_index, slot in enumerate(getattr(obj, "material_slots", []) or []):
        slot_material = getattr(slot, "material", None)
        if getattr(slot_material, "name", None) == material_name:
            return slot_index
    return None


def _evaluated_normals(obj: Any, affected: set[int]) -> dict[int, Any]:
    import bpy
    from mathutils import Vector

    depsgraph = bpy.context.evaluated_depsgraph_get()
    depsgraph.update()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        totals = {vertex: Vector((0.0, 0.0, 0.0)) for vertex in affected}
        counts = dict.fromkeys(affected, 0)
        for loop_index, loop in enumerate(mesh.loops):
            vertex = loop.vertex_index
            if vertex not in totals:
                continue
            normal = mesh.corner_normals[loop_index].vector
            totals[vertex] += Vector(
                (float(normal.x), float(normal.y), float(normal.z))
            )
            counts[vertex] += 1
        result = {}
        for vertex, total in totals.items():
            if counts[vertex]:
                result[vertex] = (total / counts[vertex]).normalized()
            else:
                result[vertex] = Vector((0.0, 0.0, 1.0))
        return result
    finally:
        evaluated.to_mesh_clear()


def _set_only_shape_key(mesh: Any, name: str | None) -> None:
    shape_keys = getattr(mesh, "shape_keys", None)
    if shape_keys is None:
        return
    for key in shape_keys.key_blocks:
        key.value = 1.0 if name is not None and key.name == name else 0.0


class _sampling_pose:
    def __init__(self, obj: Any) -> None:
        self._obj = obj
        self._keys: list[tuple[Any, float]] = []
        self._armatures: list[tuple[Any, bool]] = []

    def __enter__(self) -> _sampling_pose:
        mesh = self._obj.data
        shape_keys = getattr(mesh, "shape_keys", None)
        if shape_keys is not None:
            self._keys = [(key, float(key.value)) for key in shape_keys.key_blocks]
            for key, _value in self._keys:
                key.value = 0.0
        for modifier in self._obj.modifiers:
            if getattr(modifier, "type", None) == "ARMATURE":
                self._armatures.append((modifier, bool(modifier.show_viewport)))
                modifier.show_viewport = False
        return self

    def __exit__(self, *_exc: object) -> None:
        for key, value in self._keys:
            key.value = value
        for modifier, show in self._armatures:
            modifier.show_viewport = show


def _vec(value: Vec3) -> Any:
    from mathutils import Vector

    return Vector(value)
