# SPDX-License-Identifier: MIT
"""Apply VRMXT_materials_override data to Blender materials."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from ..common.constants import EXTENSION_MATERIALS_OVERRIDE
from ..common.json_util import Json, as_dict, as_list
from ..vfx.import_hook import resolve_texture_image
from .sync import CUSTOM_PROP_KEY, populate_groups_from_raw_json

logger = logging.getLogger(__name__)


def _set_material_override_json(material: Any, payload: dict[str, Json]) -> None:
    serialized = json.dumps(payload)
    if hasattr(material, "vrmxt_materials_override_settings"):
        material.vrmxt_materials_override_settings.raw_json = serialized
        populate_groups_from_raw_json(material, serialized)
    material[CUSTOM_PROP_KEY] = serialized


def bind_override_texture_images(
    material: Any,
    json_dict: Mapping[str, Any],
    image_index_to_image: Mapping[int, Any],
) -> int:
    """Resolve ``texture_index`` → Blender ``Image`` on authored texture rows.

    Without this, re-export keeps stale ``textures[]`` indices from the import
    GLB while Blender rebuilds a shorter ``textures[]`` (override-only images
    like ``VrmxtTestTexture`` never get packed).
    """
    settings = getattr(material, "vrmxt_materials_override_settings", None)
    if settings is None or not getattr(settings, "authored", False):
        return 0

    bound = 0
    for slot in settings.overrides:
        for item in slot.properties:
            if getattr(item, "prop_type", "") != "texture":
                continue
            if getattr(item, "image", None) is not None:
                continue
            texture_index = int(getattr(item, "texture_index", -1))
            image = resolve_texture_image(
                texture_index,
                json_dict,
                image_index_to_image,
            )
            if image is None:
                continue
            item.image = image
            bound += 1
    return bound


def apply_materials_override_import(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

    image_index_to_image = getattr(context, "image_index_to_image", {}) or {}

    for material_index, material_entry in enumerate(materials_raw):
        material_dict = as_dict(material_entry)
        if material_dict is None:
            continue
        extensions = as_dict(material_dict.get("extensions"))
        if extensions is None:
            continue
        extension_dict = as_dict(extensions.get(EXTENSION_MATERIALS_OVERRIDE))
        if extension_dict is None:
            continue

        blender_material = context.material_index_to_material.get(material_index)
        if blender_material is None:
            continue

        # Store the original extension JSON verbatim so round-trip does not
        # depend on typed parse succeeding; also fill PropertyGroups when parseable.
        _set_material_override_json(blender_material, extension_dict)
        bind_override_texture_images(
            blender_material,
            json_dict,
            image_index_to_image,
        )


def on_vrm1_import(context: Any) -> None:
    try:
        apply_materials_override_import(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM import
        logger.exception("VRMXT materials override import hook failed")


__all__ = [
    "CUSTOM_PROP_KEY",
    "apply_materials_override_import",
    "bind_override_texture_images",
    "on_vrm1_import",
]
