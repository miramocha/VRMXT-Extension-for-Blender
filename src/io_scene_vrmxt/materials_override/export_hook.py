# SPDX-License-Identifier: MIT
"""Serialize Blender material override JSON into glTF material extensions."""

from __future__ import annotations

import json
import logging
from typing import Any

from ..common.json_util import Json, as_dict, as_list
from ..format.materials_override import (
    ensure_materials_override_extensions_used,
    parse_materials_override,
    write_materials_override_to_material_dict,
)
from .import_hook import CUSTOM_PROP_KEY

logger = logging.getLogger(__name__)


def _read_material_override_json(material: Any) -> dict[str, Json] | None:
    raw_json = ""
    if hasattr(material, "vrmxt_materials_override_settings"):
        raw_json = material.vrmxt_materials_override_settings.raw_json or ""
    if not raw_json and CUSTOM_PROP_KEY in material:
        raw_json = str(material[CUSTOM_PROP_KEY])
    if not raw_json:
        return None
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    return as_dict(parsed)


def apply_materials_override_export(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

    wrote_any = False
    for material_name, material_index in context.material_name_to_index.items():
        override_dict = _read_material_override_json_from_name(context, material_name)
        if override_dict is None:
            continue
        override = parse_materials_override(override_dict)
        if override is None:
            continue
        if material_index < 0 or material_index >= len(materials_raw):
            continue
        material_dict = as_dict(materials_raw[material_index])
        if material_dict is None:
            continue
        write_materials_override_to_material_dict(material_dict, override)
        wrote_any = True

    if wrote_any:
        ensure_materials_override_extensions_used(json_dict)


def _read_material_override_json_from_name(
    context: Any,
    material_name: str,
) -> dict[str, Json] | None:
    for material in _iter_scene_materials(context):
        if getattr(material, "name", None) != material_name:
            continue
        return _read_material_override_json(material)
    return None


def _iter_scene_materials(context: Any):
    try:
        import bpy
    except ImportError:
        return []
    yield from bpy.data.materials


def on_vrm1_export(context: Any) -> None:
    try:
        apply_materials_override_export(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM export
        logger.exception("VRMXT materials override export hook failed")


__all__ = ["apply_materials_override_export", "on_vrm1_export"]
