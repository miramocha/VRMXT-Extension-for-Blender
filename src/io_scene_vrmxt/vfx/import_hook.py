# SPDX-License-Identifier: MIT
"""Apply parsed VRMXT_vfx data to Blender armature property groups."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from io_scene_vrmxt.common.constants import EXTENSION_VRMXT_VFX
from io_scene_vrmxt.common.json_util import get_root_extension
from io_scene_vrmxt.format.vfx import parse_vfx

logger = logging.getLogger(__name__)

CUSTOM_PROP_KEY = "vrmxt_vfx_json"


def _resolve_attachment_name(
    node_index: int,
    node_index_to_bone_name: Mapping[int, str],
    node_index_to_object_name: Mapping[int, str],
) -> str | None:
    if node_index in node_index_to_bone_name:
        return node_index_to_bone_name[node_index]
    if node_index in node_index_to_object_name:
        return node_index_to_object_name[node_index]
    return None


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

    for emitter in vfx.emitters:
        attachment_name = _resolve_attachment_name(
            emitter.node,
            context.node_index_to_bone_name,
            context.node_index_to_object_name,
        )
        if attachment_name is None:
            continue

        item = settings.emitters.add()
        item.name = emitter.name or ""
        item.node_index = emitter.node
        item.attachment_name = attachment_name
        item.emitter_type = emitter.type
        item.local_position = emitter.local_position
        item.local_rotation = emitter.local_rotation
        if emitter.particle is not None:
            item.texture_index = (
                emitter.particle.texture if emitter.particle.texture is not None else -1
            )
            item.emission_rate = emitter.particle.emission_rate
            item.max_particles = emitter.particle.max_particles
            item.lifetime = emitter.particle.lifetime
            item.start_size = emitter.particle.start_size
            item.start_speed = emitter.particle.start_speed
            item.start_color = emitter.particle.start_color


def on_vrm1_import(context: Any) -> None:
    try:
        apply_vfx_import(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM import
        logger.exception("VRMXT VFX import hook failed")


__all__ = ["CUSTOM_PROP_KEY", "apply_vfx_import", "on_vrm1_import"]
