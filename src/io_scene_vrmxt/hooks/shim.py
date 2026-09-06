# SPDX-License-Identifier: MIT
"""Build apply_* hook contexts from stock VRM 4.6.0 user-extension arguments."""

from __future__ import annotations

from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any

try:
    import bpy
except ImportError:  # pragma: no cover - exercised only outside Blender
    bpy = None  # type: ignore[assignment]


def invert_name_to_index(index_to_id: Mapping[int, Any] | None) -> dict[str, int]:
    """Map Blender ID ``.name`` → glTF index. Last write wins on collisions."""
    result: dict[str, int] = {}
    if not index_to_id:
        return result
    for index, item in index_to_id.items():
        name = getattr(item, "name", None)
        if isinstance(name, str) and name:
            result[name] = index
    return result


def names_from_index_map(index_to_id: Mapping[int, Any] | None) -> dict[int, str]:
    result: dict[int, str] = {}
    if not index_to_id:
        return result
    for index, item in index_to_id.items():
        name = getattr(item, "name", None)
        if isinstance(name, str) and name:
            result[index] = name
    return result


def image_name_to_index_from_images(
    image_index_to_image: Mapping[int, Any] | None,
) -> dict[str, int]:
    return invert_name_to_index(image_index_to_image)


def blender_context() -> Any:
    if bpy is None:
        return None
    return bpy.context


def scene_for_armature(armature: Any, context: Any) -> Any:
    context_scene = getattr(context, "scene", None)
    if context_scene is not None:
        scene_objects = getattr(context_scene, "objects", ())
        armature_name = getattr(armature, "name", None)
        try:
            if armature in scene_objects or (
                isinstance(armature_name, str) and armature_name in scene_objects
            ):
                return context_scene
        except (ReferenceError, TypeError):
            pass
    for scene in tuple(getattr(armature, "users_scene", ()) or ()):
        if scene is not None:
            return scene
    return context_scene


def make_import_context(
    json_chunk: Mapping[str, Any],
    armature: Any,
    node_index_to_object: Mapping[int, Any],
    node_index_to_bone: Mapping[int, Any],
    image_index_to_image: Mapping[int, Any],
    material_index_to_material: Mapping[int, Any],
    mesh_index_to_mesh: Mapping[int, Any] | None = None,
) -> SimpleNamespace:
    context = blender_context()
    return SimpleNamespace(
        context=context,
        scene=scene_for_armature(armature, context),
        armature=armature,
        json_dict=json_chunk,
        node_index_to_object=dict(node_index_to_object or {}),
        node_index_to_object_name=names_from_index_map(node_index_to_object),
        node_index_to_bone=dict(node_index_to_bone or {}),
        node_index_to_bone_name=names_from_index_map(node_index_to_bone),
        image_index_to_image=dict(image_index_to_image or {}),
        material_index_to_material=dict(material_index_to_material or {}),
        mesh_index_to_mesh=dict(mesh_index_to_mesh or {}),
    )


def make_export_context(
    json_chunk: dict[str, Any],
    bin_chunk: Any,
    armature: Any,
    node_index_to_object: Mapping[int, Any],
    node_index_to_bone: Mapping[int, Any],
    image_index_to_image: Mapping[int, Any],
    material_index_to_material: Mapping[int, Any],
    mesh_index_to_mesh: Mapping[int, Any] | None = None,
) -> SimpleNamespace:
    context = blender_context()
    buffer0 = bin_chunk if isinstance(bin_chunk, bytearray) else None
    return SimpleNamespace(
        context=context,
        scene=scene_for_armature(armature, context),
        armature=armature,
        json_dict=json_chunk,
        buffer0=buffer0,
        bin_chunk=bin_chunk,
        node_index_to_object=dict(node_index_to_object or {}),
        bone_name_to_node_index=invert_name_to_index(node_index_to_bone),
        object_name_to_node_index=invert_name_to_index(node_index_to_object),
        node_index_to_bone=dict(node_index_to_bone or {}),
        image_index_to_image=dict(image_index_to_image or {}),
        image_name_to_index=image_name_to_index_from_images(image_index_to_image),
        material_index_to_material=dict(material_index_to_material or {}),
        material_name_to_index=invert_name_to_index(material_index_to_material),
        mesh_index_to_mesh=dict(mesh_index_to_mesh or {}),
        mesh_name_to_index=invert_name_to_index(mesh_index_to_mesh),
    )


__all__ = [
    "blender_context",
    "image_name_to_index_from_images",
    "invert_name_to_index",
    "make_export_context",
    "make_import_context",
    "names_from_index_map",
    "scene_for_armature",
]
