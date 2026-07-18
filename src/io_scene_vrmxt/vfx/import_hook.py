# SPDX-License-Identifier: MIT
"""Apply parsed VRMXT_vfx data to Blender armature property groups."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from ..common.constants import EXTENSION_VRMXT_VFX
from ..common.json_util import get_root_extension
from ..format.vfx import parse_vfx
from .property_group import (
    ATTACHMENT_TYPE_BONE,
    ATTACHMENT_TYPE_OBJECT,
)

logger = logging.getLogger(__name__)

CUSTOM_PROP_KEY = "vrmxt_vfx_json"


def resolve_attachment(
    node_index: int,
    node_index_to_bone_name: Mapping[int, str],
    node_index_to_object_name: Mapping[int, str],
) -> tuple[str, str] | None:
    """Return ``(attachment_type, name)`` or ``None`` when unresolved."""
    bone_name = node_index_to_bone_name.get(node_index)
    if bone_name:
        return ATTACHMENT_TYPE_BONE, bone_name
    object_name = node_index_to_object_name.get(node_index)
    if object_name:
        return ATTACHMENT_TYPE_OBJECT, object_name
    return None


def resolve_texture_image(
    texture_index: int | None,
    json_dict: Mapping[str, Any],
    image_index_to_image: Mapping[int, Any],
) -> Any | None:
    """Map ``particle.texture`` (textures[] index) to a Blender Image."""
    if texture_index is None or texture_index < 0:
        return None
    textures = json_dict.get("textures")
    if not isinstance(textures, list) or texture_index >= len(textures):
        return None
    texture_dict = textures[texture_index]
    if not isinstance(texture_dict, dict):
        return None
    source = texture_dict.get("source")
    if not isinstance(source, int):
        return None
    return image_index_to_image.get(source)


def apply_vfx_import(context: Any) -> None:
    json_dict = context.json_dict
    extension_dict = get_root_extension(json_dict, EXTENSION_VRMXT_VFX)
    if extension_dict is None:
        return

    nodes = json_dict.get("nodes")
    node_count = len(nodes) if isinstance(nodes, list) else None
    vfx = parse_vfx(extension_dict, node_count=node_count)
    if vfx is None:
        return

    armature = context.armature
    if armature is None or not hasattr(armature.data, "vrmxt_vfx_settings"):
        return

    settings = armature.data.vrmxt_vfx_settings
    settings.emitters.clear()

    blend_data = getattr(getattr(context, "context", None), "blend_data", None)
    image_index_to_image = getattr(context, "image_index_to_image", {}) or {}

    for emitter in vfx.emitters:
        attachment = resolve_attachment(
            emitter.node,
            context.node_index_to_bone_name,
            context.node_index_to_object_name,
        )
        if attachment is None:
            continue

        attachment_type, attachment_name = attachment
        item = settings.emitters.add()
        item.name = emitter.name or ""
        item.attachment_type = attachment_type
        item.emitter_type = emitter.type
        item.local_position = emitter.local_position
        item.local_rotation = emitter.local_rotation

        if attachment_type == ATTACHMENT_TYPE_BONE:
            item.attachment_bone = attachment_name
            item.attachment_object = None
        else:
            item.attachment_bone = ""
            if blend_data is not None:
                item.attachment_object = blend_data.objects.get(attachment_name)
            else:
                item.attachment_object = None

        if emitter.particle is not None:
            item.texture = resolve_texture_image(
                emitter.particle.texture,
                json_dict,
                image_index_to_image,
            )
            item.emission_rate = emitter.particle.emission_rate
            item.max_particles = emitter.particle.max_particles
            item.lifetime = emitter.particle.lifetime
            item.start_size = emitter.particle.start_size
            item.start_speed = emitter.particle.start_speed
            item.start_color = emitter.particle.start_color

    _rebuild_preview_after_import(armature, context)


def _rebuild_preview_after_import(armature: Any, context: Any) -> None:
    """Spawn GeoNodes helpers after property groups are filled."""
    try:
        from .geonodes_preview import rebuild_vfx_preview
    except ImportError:
        return

    blend_context = getattr(context, "context", None)
    try:
        rebuild_vfx_preview(armature, context=blend_context)
    except Exception:  # noqa: BLE001 - preview must not abort VFX import
        logger.exception("VRMXT VFX GeoNodes preview rebuild failed")


def on_vrm1_import(context: Any) -> None:
    try:
        apply_vfx_import(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM import
        logger.exception("VRMXT VFX import hook failed")


__all__ = [
    "CUSTOM_PROP_KEY",
    "apply_vfx_import",
    "on_vrm1_import",
    "resolve_attachment",
    "resolve_texture_image",
]
