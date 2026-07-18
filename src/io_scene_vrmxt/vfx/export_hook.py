# SPDX-License-Identifier: MIT
"""Serialize armature VFX property groups into root VRMXT_vfx.

Export reads property groups only. Geometry Nodes preview helpers tagged with
``vrmxt_vfx_preview`` are never a source of truth (host export also skips them).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from ..format.vfx import (
    EMITTER_TYPE_PARTICLE,
    ParticleParams,
    VrmxtVfx,
    VrmxtVfxEmitter,
    write_vfx_to_gltf,
)
from .gltf_texture import ensure_vfx_texture_index
from .property_group import (
    ATTACHMENT_TYPE_BONE,
    ATTACHMENT_TYPE_OBJECT,
)

logger = logging.getLogger(__name__)


def resolve_node_index(
    attachment_type: str,
    attachment_bone: str,
    attachment_object_name: str | None,
    bone_name_to_node_index: Mapping[str, int],
    object_name_to_node_index: Mapping[str, int],
) -> int | None:
    if attachment_type == ATTACHMENT_TYPE_BONE:
        if not attachment_bone:
            return None
        return bone_name_to_node_index.get(attachment_bone)
    if attachment_type == ATTACHMENT_TYPE_OBJECT:
        if not attachment_object_name:
            return None
        # Preview helpers must never resolve as attachment nodes.
        if attachment_object_name.startswith("VRMXT_vfx_"):
            return None
        return object_name_to_node_index.get(attachment_object_name)
    return None


def apply_vfx_export(context: Any) -> None:
    armature = context.armature
    if armature is None or not hasattr(armature.data, "vrmxt_vfx_settings"):
        return

    image_name_to_index = getattr(context, "image_name_to_index", {})
    buffer0 = getattr(context, "buffer0", None)
    if not isinstance(buffer0, bytearray):
        logger.warning(
            "VRMXT VFX export: host buffer0 missing; textures will be omitted"
        )
        buffer0 = None

    emitters: list[VrmxtVfxEmitter] = []
    skipped = 0

    for item in armature.data.vrmxt_vfx_settings.emitters:
        if item.emitter_type != EMITTER_TYPE_PARTICLE:
            skipped += 1
            logger.warning(
                "Skipping VFX emitter %r: unsupported type %r",
                item.name,
                item.emitter_type,
            )
            continue

        attachment_object = getattr(item, "attachment_object", None)
        attachment_object_name = (
            attachment_object.name if attachment_object is not None else None
        )
        node_index = resolve_node_index(
            item.attachment_type,
            item.attachment_bone,
            attachment_object_name,
            context.bone_name_to_node_index,
            context.object_name_to_node_index,
        )
        if node_index is None:
            skipped += 1
            logger.warning(
                "Skipping VFX emitter %r: unresolved attachment "
                "(type=%s bone=%r object=%r)",
                item.name,
                item.attachment_type,
                item.attachment_bone,
                attachment_object_name,
            )
            continue

        texture_image = getattr(item, "texture", None)
        texture_index = None
        if texture_image is not None:
            if buffer0 is None:
                logger.warning(
                    "VFX emitter %r: texture %r omitted (no export buffer)",
                    item.name,
                    texture_image.name,
                )
            else:
                texture_index = ensure_vfx_texture_index(
                    image=texture_image,
                    json_dict=context.json_dict,
                    buffer0=buffer0,
                    image_name_to_index=image_name_to_index,
                )
                if texture_index is None:
                    logger.warning(
                        "VFX emitter %r: texture %r was not written to glTF",
                        item.name,
                        texture_image.name,
                    )

        emitters.append(
            VrmxtVfxEmitter(
                type=item.emitter_type,
                node=node_index,
                name=item.name or None,
                local_position=tuple(item.local_position),
                local_rotation=tuple(item.local_rotation),
                particle=ParticleParams(
                    texture=texture_index,
                    emission_rate=item.emission_rate,
                    max_particles=item.max_particles,
                    lifetime=item.lifetime,
                    start_size=item.start_size,
                    start_speed=item.start_speed,
                    start_color=tuple(item.start_color),
                ),
            )
        )

    if skipped:
        logger.warning(
            "VRMXT VFX export skipped %d emitter(s); %d written",
            skipped,
            len(emitters),
        )

    if not emitters:
        return

    write_vfx_to_gltf(context.json_dict, VrmxtVfx(emitters=emitters))


def on_vrm1_export(context: Any) -> None:
    try:
        apply_vfx_export(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM export
        logger.exception("VRMXT VFX export hook failed")


__all__ = [
    "apply_vfx_export",
    "on_vrm1_export",
    "resolve_node_index",
]
