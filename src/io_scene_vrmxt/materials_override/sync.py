# SPDX-License-Identifier: MIT
"""Sync PropertyGroups <-> VRMXT_materials_override extension dict / raw_json."""

from __future__ import annotations

import json
from typing import Any

from ..common.constants import (
    ENGINE_UNITY,
    ENGINE_UNREAL,
    ID_TYPE_SHADER_NAME,
    SPEC_VERSION_1_0,
)
from ..common.json_util import Json, as_dict
from ..format.materials_override import (
    MaterialOverride,
    MaterialProperty,
    UnityMaterial,
    UnrealMaterial,
    VrmxtMaterialsOverride,
    parse_materials_override,
    serialize_materials_override,
)
from .catalog import CUSTOM_SHADER_ENUM, CatalogProperty, find_catalog_by_shader_name
from .vector_ui import is_color_vector_property_name

CUSTOM_PROP_KEY = "vrmxt_materials_override"

# Matches FloatVectorProperty defaults on value_vector / value_color.
_DEFAULT_VEC4 = (1.0, 1.0, 1.0, 1.0)


def _settings_of(material: Any) -> Any | None:
    return getattr(material, "vrmxt_materials_override_settings", None)


def _as_float4(vec: Any) -> tuple[float, float, float, float]:
    try:
        return (float(vec[0]), float(vec[1]), float(vec[2]), float(vec[3]))
    except (TypeError, ValueError, IndexError):
        return _DEFAULT_VEC4


def _is_default_float4(vec: Any) -> bool:
    values = _as_float4(vec)
    return all(abs(values[i] - _DEFAULT_VEC4[i]) < 1e-6 for i in range(4))


def migrate_legacy_color_storage(item: Any) -> None:
    """Copy 0.2.0 *Color values from ``value_vector`` into ``value_color``.

    Pre-``value_color`` blends kept colors in ``value_vector``. The new field
    stays at its (1,1,1,1) default, so export/UI must migrate once or colors
    silently become white. Clears ``value_vector`` after copy so a later edit
    back to white is not overridden by stale legacy data.
    """
    name = (getattr(item, "name", "") or "").strip()
    if getattr(item, "prop_type", "") != "vector":
        return
    if not is_color_vector_property_name(name):
        return
    color = getattr(item, "value_color", _DEFAULT_VEC4)
    vector = getattr(item, "value_vector", _DEFAULT_VEC4)
    if _is_default_float4(color) and not _is_default_float4(vector):
        migrated = _as_float4(vector)
        item.value_color = migrated
        item.value_vector = _DEFAULT_VEC4


def apply_catalog_default(item: Any, catalog_prop: CatalogProperty) -> None:
    """Fill a property-group row from a catalog property definition."""
    item.name = catalog_prop.name
    item.prop_type = catalog_prop.type
    item.vector_size = catalog_prop.vector_size
    default = catalog_prop.default
    if catalog_prop.type == "scalar":
        if isinstance(default, (int, float)):
            item.value_float = float(default)
    elif catalog_prop.type == "vector":
        if isinstance(default, list) and default:
            values = [float(v) for v in default[:4]]
            while len(values) < 4:
                values.append(1.0 if len(values) == 3 else 0.0)
            vec = tuple(values[:4])
            item.vector_size = min(max(len(default), 2), 4)
            if is_color_vector_property_name(catalog_prop.name):
                item.value_color = vec
            else:
                item.value_vector = vec
    elif catalog_prop.type == "shaderFeature":
        item.value_bool = bool(default) if isinstance(default, bool) else bool(default)


def clear_authored_overrides(material: Any) -> None:
    settings = _settings_of(material)
    if settings is None:
        return
    settings.overrides.clear()
    settings.active_override_index = 0
    settings.authored = False


def populate_groups_from_extension(
    material: Any,
    extension: VrmxtMaterialsOverride,
) -> None:
    """Replace PropertyGroups from a parsed extension (bindings stay in raw_json)."""
    settings = _settings_of(material)
    if settings is None:
        return
    settings.overrides.clear()
    for entry in extension.overrides:
        slot = settings.overrides.add()
        slot.engine = entry.engine
        if isinstance(entry.material, UnityMaterial):
            slot.id_type = entry.material.id_type
            slot.material_id = entry.material.id
            slot.variant = entry.material.variant or "builtin"
            catalog = find_catalog_by_shader_name(
                entry.material.id, engine=ENGINE_UNITY
            )
            if catalog is not None:
                slot.catalog_key = catalog.key
                slot.shader_enum = catalog.key
            else:
                slot.catalog_key = ""
                slot.shader_enum = CUSTOM_SHADER_ENUM
        elif isinstance(entry.material, UnrealMaterial):
            slot.id_type = entry.material.id_type
            slot.material_id = ""
            slot.catalog_key = ""
            slot.shader_enum = CUSTOM_SHADER_ENUM
            # Unreal authoring not in first ship; keep raw_json as source for export.
            settings.authored = False
            return

        for prop in entry.properties:
            item = slot.properties.add()
            item.name = prop.name
            item.prop_type = prop.type
            if prop.type == "scalar" and isinstance(prop.value, (int, float)):
                item.value_float = float(prop.value)
            elif prop.type == "vector" and isinstance(prop.value, list):
                values = [float(v) for v in prop.value[:4]]
                while len(values) < 4:
                    values.append(0.0)
                vec = tuple(values[:4])
                item.vector_size = min(max(len(prop.value), 2), 4)
                if is_color_vector_property_name(prop.name):
                    item.value_color = vec
                else:
                    item.value_vector = vec
            elif prop.type == "shaderFeature" and isinstance(prop.value, bool):
                item.value_bool = prop.value
            elif prop.type == "texture":
                item.texture_index = prop.texture if prop.texture is not None else -1

    settings.authored = True
    settings.active_override_index = 0


def populate_groups_from_raw_json(material: Any, raw_json: str) -> bool:
    """Parse ``raw_json`` into groups. Returns False if unparsed (keep raw only)."""
    if not raw_json:
        clear_authored_overrides(material)
        return False
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        clear_authored_overrides(material)
        return False
    extension_dict = as_dict(payload)
    if extension_dict is None:
        clear_authored_overrides(material)
        return False
    extension = parse_materials_override(extension_dict)
    if extension is None:
        clear_authored_overrides(material)
        return False
    # Reject Unreal-only or mixed for authored groups in MVP.
    if any(entry.engine == ENGINE_UNREAL for entry in extension.overrides):
        clear_authored_overrides(material)
        return False
    populate_groups_from_extension(material, extension)
    return True


def _property_item_to_format(item: Any) -> MaterialProperty | None:
    name = (getattr(item, "name", "") or "").strip()
    prop_type = getattr(item, "prop_type", "") or ""
    if not name or not prop_type:
        return None
    if prop_type == "texture":
        image = getattr(item, "image", None)
        texture_index = int(getattr(item, "texture_index", -1))
        # Image resolution happens at export; store index placeholder for sync.
        if image is not None:
            # Keep prior index if any; export hook remaps.
            return MaterialProperty(
                name=name,
                type=prop_type,
                texture=texture_index if texture_index >= 0 else 0,
            )
        if texture_index < 0:
            return None
        return MaterialProperty(name=name, type=prop_type, texture=texture_index)
    if prop_type == "scalar":
        return MaterialProperty(
            name=name, type=prop_type, value=float(getattr(item, "value_float", 0.0))
        )
    if prop_type == "vector":
        size = int(getattr(item, "vector_size", 4))
        size = min(max(size, 2), 4)
        migrate_legacy_color_storage(item)
        if is_color_vector_property_name(name):
            vec = _as_float4(getattr(item, "value_color", _DEFAULT_VEC4))
        else:
            vec = _as_float4(getattr(item, "value_vector", _DEFAULT_VEC4))
        return MaterialProperty(
            name=name,
            type=prop_type,
            value=[float(vec[i]) for i in range(size)],
        )
    if prop_type == "shaderFeature":
        return MaterialProperty(
            name=name, type=prop_type, value=bool(getattr(item, "value_bool", False))
        )
    return None


def groups_to_extension(material: Any) -> VrmxtMaterialsOverride | None:
    settings = _settings_of(material)
    if settings is None or not settings.authored:
        return None
    if len(settings.overrides) == 0:
        return None

    overrides: list[MaterialOverride] = []
    for slot in settings.overrides:
        engine = slot.engine
        if engine != ENGINE_UNITY:
            continue
        material_id = (slot.material_id or "").strip()
        if not material_id:
            continue
        properties: list[MaterialProperty] = []
        for item in slot.properties:
            parsed = _property_item_to_format(item)
            if parsed is not None:
                properties.append(parsed)
        overrides.append(
            MaterialOverride(
                engine=ENGINE_UNITY,
                material=UnityMaterial(
                    id_type=slot.id_type or ID_TYPE_SHADER_NAME,
                    id=material_id,
                    variant=slot.variant or None,
                ),
                properties=properties,
            )
        )
    if not overrides:
        return None
    return VrmxtMaterialsOverride(spec_version=SPEC_VERSION_1_0, overrides=overrides)


def sync_raw_json_from_groups(material: Any) -> str | None:
    """Write authored groups to ``raw_json`` + custom prop. Return JSON or None."""
    settings = _settings_of(material)
    if settings is None or not settings.authored:
        return None
    extension = groups_to_extension(material)
    if extension is None:
        settings.raw_json = ""
        if CUSTOM_PROP_KEY in material:
            del material[CUSTOM_PROP_KEY]
        return ""
    payload = serialize_materials_override(extension)
    serialized = json.dumps(payload)
    settings.raw_json = serialized
    material[CUSTOM_PROP_KEY] = serialized
    return serialized


def read_extension_dict_for_export(material: Any) -> dict[str, Json] | None:
    """Preferred export payload: authored groups, else stored raw_json."""
    settings = _settings_of(material)
    if settings is not None and settings.authored:
        extension = groups_to_extension(material)
        if extension is not None:
            return serialize_materials_override(extension)
        return None

    raw_json = ""
    if settings is not None:
        raw_json = settings.raw_json or ""
    if not raw_json and CUSTOM_PROP_KEY in material:
        raw_json = str(material[CUSTOM_PROP_KEY])
    if not raw_json:
        return None
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    return as_dict(parsed)


def existing_property_names(slot: Any) -> set[str]:
    return {str(item.name) for item in slot.properties if getattr(item, "name", None)}


__all__ = [
    "CUSTOM_PROP_KEY",
    "apply_catalog_default",
    "clear_authored_overrides",
    "existing_property_names",
    "groups_to_extension",
    "migrate_legacy_color_storage",
    "populate_groups_from_extension",
    "populate_groups_from_raw_json",
    "read_extension_dict_for_export",
    "sync_raw_json_from_groups",
]
