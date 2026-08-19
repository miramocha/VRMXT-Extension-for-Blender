# SPDX-License-Identifier: MIT
"""Apply VRMC_materials_mtoonxt stencil data to Blender materials."""

from __future__ import annotations

import logging
from typing import Any

from ..common.json_util import as_dict, as_list
from ..format.mtoonxt import read_mtoonxt_from_material
from .property_group import apply_parsed_to_settings

logger = logging.getLogger(__name__)


def apply_mtoonxt_import(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

    index_to_material = getattr(context, "material_index_to_material", {}) or {}
    material_count = len(materials_raw)

    for material_index, material_entry in enumerate(materials_raw):
        material_dict = as_dict(material_entry)
        if material_dict is None:
            continue
        extra = read_mtoonxt_from_material(
            material_dict,
            own_index=material_index,
            material_count=material_count,
        )
        if extra is None:
            continue
        blender_material = index_to_material.get(material_index)
        if blender_material is None:
            continue
        settings = getattr(blender_material, "vrmxt_mtoonxt_settings", None)
        if settings is None:
            continue
        apply_parsed_to_settings(settings, extra, dict(index_to_material))


def on_vrm1_import(context: Any) -> None:
    try:
        apply_mtoonxt_import(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM import
        logger.exception("VRMXT MToonXT import hook failed")


__all__ = ["apply_mtoonxt_import", "on_vrm1_import"]
