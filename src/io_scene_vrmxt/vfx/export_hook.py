# SPDX-License-Identifier: MIT
"""Serialize armature VFX property groups into root VRMXT_vfx."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from io_scene_vrmxt.format.vfx import (
    EMITTER_TYPE_PARTICLE,
    ParticleParams,
    VrmxtVfx,
    VrmxtVfxEmitter,
    write_vfx_to_gltf,
)

logger = logging.getLogger(__name__)


def _resolve_node_index(
    attachment_name: str,
    bone_name_to_node_index: Mapping[str, int],
    object_name_to_node_index: Mapping[str, int],
) -> int | None:
    if attachment_name in bone_name_to_node_index:
        return bone_name_to_node_index[attachment_name]
    if attachment_name in object_name_to_node_index:
        return object_name_to_node_index[attachment_name]
    return None


def apply_vfx_export(context: Any) -> None:
    armature = context.armature
    if armature is None or not hasattr(armature.data, "vrmxt_vfx_settings"):
        return

    emitters: list[VrmxtVfxEmitter] = []
    for item in armature.data.vrmxt_vfx_settings.emitters:
        if item.emitter_type != EMITTER_TYPE_PARTICLE:
            continue
        if not item.attachment_name:
            continue
        node_index = _resolve_node_index(
            item.attachment_name,
            context.bone_name_to_node_index,
            context.object_name_to_node_index,
        )
        if node_index is None:
            continue
        emitters.append(
            VrmxtVfxEmitter(
                type=item.emitter_type,
                node=node_index,
                name=item.name or None,
                local_position=tuple(item.local_position),
                local_rotation=tuple(item.local_rotation),
                particle=ParticleParams(
                    texture=item.texture_index if item.texture_index >= 0 else None,
                    emission_rate=item.emission_rate,
                    max_particles=item.max_particles,
                    lifetime=item.lifetime,
                    start_size=item.start_size,
                    start_speed=item.start_speed,
                    start_color=tuple(item.start_color),
                ),
            )
        )

    if not emitters:
        return

    write_vfx_to_gltf(context.json_dict, VrmxtVfx(emitters=emitters))


def on_vrm1_export(context: Any) -> None:
    try:
        apply_vfx_export(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM export
        logger.exception("VRMXT VFX export hook failed")


__all__ = ["apply_vfx_export", "on_vrm1_export"]
