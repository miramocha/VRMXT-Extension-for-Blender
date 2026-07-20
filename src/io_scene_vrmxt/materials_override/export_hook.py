# SPDX-License-Identifier: MIT
"""Serialize Blender material override JSON into glTF material extensions."""

from __future__ import annotations

import logging
from typing import Any

from ..common.json_util import Json, as_dict, as_list
from ..format.materials_override import (
    ensure_materials_override_extensions_used,
    write_raw_materials_override_to_material_dict,
)
from ..vfx.gltf_texture import ensure_vfx_texture_index
from .sync import read_extension_dict_for_export

logger = logging.getLogger(__name__)


def _remap_texture_properties_for_export(
    material: Any,
    override_dict: dict[str, Json],
    context: Any,
) -> dict[str, Json]:
    """Resolve authored Image pointers into glTF textures[] indices when possible."""
    settings = getattr(material, "vrmxt_materials_override_settings", None)
    if settings is None or not getattr(settings, "authored", False):
        return override_dict

    json_dict = context.json_dict
    buffer0 = getattr(context, "buffer0", None)
    image_name_to_index = getattr(context, "image_name_to_index", None)
    if buffer0 is None or image_name_to_index is None:
        return override_dict

    overrides_raw = as_list(override_dict.get("overrides"))
    if overrides_raw is None:
        return override_dict

    # Walk authored slots in parallel with serialized overrides (Unity-only authored).
    authored_slots = list(settings.overrides)
    new_overrides: list[Json] = []
    authored_index = 0
    for entry in overrides_raw:
        entry_dict = as_dict(entry)
        if entry_dict is None:
            new_overrides.append(entry)
            continue
        if authored_index >= len(authored_slots):
            new_overrides.append(entry_dict)
            continue
        slot = authored_slots[authored_index]
        authored_index += 1
        props_raw = as_list(entry_dict.get("properties"))
        if props_raw is None:
            new_overrides.append(entry_dict)
            continue
        slot_props = list(slot.properties)
        new_props: list[Json] = []
        prop_index = 0
        for prop_entry in props_raw:
            prop_dict = as_dict(prop_entry)
            if prop_dict is None:
                continue
            if prop_dict.get("type") != "texture":
                new_props.append(prop_dict)
                prop_index += 1
                continue
            image = None
            if prop_index < len(slot_props):
                image = getattr(slot_props[prop_index], "image", None)
            prop_index += 1
            if image is not None:
                texture_index = ensure_vfx_texture_index(
                    image=image,
                    json_dict=json_dict,
                    buffer0=buffer0,
                    image_name_to_index=image_name_to_index,
                )
                if texture_index is None:
                    # Soft-fail: drop unresolvable authored texture (rule 24).
                    continue
                prop_dict = dict(prop_dict)
                prop_dict["texture"] = texture_index
                prop_dict.pop("value", None)
                new_props.append(prop_dict)
            else:
                # Keep imported texture index when present.
                if "texture" in prop_dict:
                    new_props.append(prop_dict)
        entry_dict = dict(entry_dict)
        if new_props:
            entry_dict["properties"] = new_props
        elif "properties" in entry_dict:
            del entry_dict["properties"]
        new_overrides.append(entry_dict)

    result = dict(override_dict)
    result["overrides"] = new_overrides
    return result


def apply_materials_override_export(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

    wrote_any = False
    for material_name, material_index in context.material_name_to_index.items():
        material = _find_material_by_name(material_name)
        if material is None:
            continue
        override_dict = read_extension_dict_for_export(material)
        if override_dict is None:
            continue
        if material_index < 0 or material_index >= len(materials_raw):
            continue
        material_dict = as_dict(materials_raw[material_index])
        if material_dict is None:
            continue
        override_dict = _remap_texture_properties_for_export(
            material, override_dict, context
        )
        write_raw_materials_override_to_material_dict(material_dict, override_dict)
        wrote_any = True

    if wrote_any:
        ensure_materials_override_extensions_used(json_dict)


def _find_material_by_name(material_name: str) -> Any | None:
    try:
        import bpy
    except ImportError:
        return None
    for material in bpy.data.materials:
        if getattr(material, "name", None) == material_name:
            return material
    return None


def on_vrm1_export(context: Any) -> None:
    try:
        apply_materials_override_export(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM export
        logger.exception("VRMXT materials override export hook failed")


__all__ = ["apply_materials_override_export", "on_vrm1_export"]
