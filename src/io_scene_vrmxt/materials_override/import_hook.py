# SPDX-License-Identifier: MIT
"""Apply parsed VRMXT_materials_override data to Blender materials."""

from __future__ import annotations

import json
import logging
from typing import Any

from io_scene_vrmxt.common.constants import EXTENSION_MATERIALS_OVERRIDE
from io_scene_vrmxt.common.json_util import Json, as_dict, as_list
from io_scene_vrmxt.format.materials_override import (
    parse_materials_override,
    serialize_materials_override,
)

logger = logging.getLogger(__name__)

CUSTOM_PROP_KEY = "vrmxt_materials_override"


def _set_material_override_json(material: Any, payload: dict[str, Json]) -> None:
    serialized = json.dumps(payload)
    if hasattr(material, "vrmxt_materials_override_settings"):
        material.vrmxt_materials_override_settings.raw_json = serialized
    material[CUSTOM_PROP_KEY] = serialized


def apply_materials_override_import(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

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

        override = parse_materials_override(extension_dict)
        if override is None:
            continue

        blender_material = context.material_index_to_material.get(material_index)
        if blender_material is None:
            continue

        _set_material_override_json(
            blender_material,
            serialize_materials_override(override),
        )


def on_vrm1_import(context: Any) -> None:
    try:
        apply_materials_override_import(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM import
        logger.exception("VRMXT materials override import hook failed")


__all__ = [
    "CUSTOM_PROP_KEY",
    "apply_materials_override_import",
    "on_vrm1_import",
]
