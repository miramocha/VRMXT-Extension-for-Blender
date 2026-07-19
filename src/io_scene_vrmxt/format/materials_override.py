# SPDX-License-Identifier: MIT
"""VRMXT_materials_override per-material glTF extension parsing and serialization."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field

from ..common.constants import (
    ENGINE_UNITY,
    ENGINE_UNREAL,
    EXTENSION_MATERIALS_OVERRIDE,
    ID_TYPE_MATERIAL_SET,
    ID_TYPE_SHADER_NAME,
    MTOON_SOURCES,
    SPEC_VERSION_1_0,
    TARGET_TYPES,
)
from ..common.json_util import (
    Json,
    as_dict,
    as_int,
    as_list,
    as_number,
    as_str,
    ensure_extensions_used,
    get_material_extension,
)

UNITY_VARIANTS = frozenset({"builtin", "urp", "hdrp"})
UNREAL_VARIANT_KEYS = frozenset(
    {"opaque", "opaqueTwoSided", "translucent", "translucentTwoSided"}
)


@dataclass
class MaterialProvider:
    id: str
    version: str | None = None


@dataclass
class UnityMaterial:
    id_type: str
    id: str
    variant: str | None = None
    provider: MaterialProvider | None = None


@dataclass
class UnrealVariants:
    opaque: str | None = None
    opaque_two_sided: str | None = None
    translucent: str | None = None
    translucent_two_sided: str | None = None

    def has_any(self) -> bool:
        return any(
            (
                self.opaque,
                self.opaque_two_sided,
                self.translucent,
                self.translucent_two_sided,
            )
        )


@dataclass
class UnrealMaterial:
    id_type: str
    variants: UnrealVariants
    provider: MaterialProvider | None = None


@dataclass
class MaterialBinding:
    source: str
    target: str
    target_type: str


@dataclass
class MaterialProperty:
    name: str
    type: str
    value: Json | None = None
    texture: int | None = None


@dataclass
class MaterialOverride:
    engine: str
    material: UnityMaterial | UnrealMaterial
    bindings: list[MaterialBinding] = field(default_factory=list)
    properties: list[MaterialProperty] = field(default_factory=list)


@dataclass
class VrmxtMaterialsOverride:
    spec_version: str = SPEC_VERSION_1_0
    overrides: list[MaterialOverride] = field(default_factory=list)


def _parse_provider(raw: Mapping[str, Json]) -> MaterialProvider | None:
    provider_id = as_str(raw.get("id"))
    if provider_id is None or not provider_id:
        return None
    version = as_str(raw.get("version"))
    return MaterialProvider(id=provider_id, version=version)


def _parse_bindings(raw_bindings: list[Json]) -> list[MaterialBinding] | None:
    bindings: list[MaterialBinding] = []
    for item in raw_bindings:
        binding_dict = as_dict(item)
        if binding_dict is None:
            return None
        source = as_str(binding_dict.get("source"))
        target = as_str(binding_dict.get("target"))
        target_type = as_str(binding_dict.get("targetType"))
        if source is None or target is None or target_type is None:
            return None
        if source not in MTOON_SOURCES:
            return None
        if target_type not in TARGET_TYPES:
            return None
        bindings.append(
            MaterialBinding(source=source, target=target, target_type=target_type)
        )
    return bindings


def _parse_property(raw: Mapping[str, Json]) -> MaterialProperty | None:
    name = as_str(raw.get("name"))
    prop_type = as_str(raw.get("type"))
    if name is None or not name or prop_type is None:
        return None
    if prop_type not in TARGET_TYPES:
        return None

    if prop_type == "texture":
        texture = as_int(raw.get("texture"))
        if texture is None or texture < 0:
            return None
        return MaterialProperty(name=name, type=prop_type, texture=texture)

    if "value" not in raw:
        return None
    value = raw.get("value")

    if prop_type == "shaderFeature":
        if not isinstance(value, bool):
            return None
        return MaterialProperty(name=name, type=prop_type, value=value)

    if prop_type == "vector":
        values_list = as_list(value)
        if values_list is None or not values_list:
            return None
        numbers: list[Json] = []
        for item in values_list:
            number = as_number(item)
            if number is None:
                return None
            numbers.append(number)
        return MaterialProperty(name=name, type=prop_type, value=numbers)

    # scalar
    number = as_number(value)
    if number is None:
        return None
    return MaterialProperty(name=name, type=prop_type, value=number)


def _parse_properties(raw_properties: list[Json]) -> list[MaterialProperty] | None:
    properties: list[MaterialProperty] = []
    for item in raw_properties:
        property_dict = as_dict(item)
        if property_dict is None:
            return None
        parsed = _parse_property(property_dict)
        if parsed is None:
            return None
        properties.append(parsed)
    return properties


def _parse_unity_material(raw: Mapping[str, Json]) -> UnityMaterial | None:
    id_type = as_str(raw.get("idType"))
    if id_type != ID_TYPE_SHADER_NAME:
        return None
    material_id = as_str(raw.get("id"))
    if material_id is None or not material_id:
        return None
    variant = as_str(raw.get("variant"))
    if variant is not None and variant not in UNITY_VARIANTS:
        return None
    provider_raw = as_dict(raw.get("provider"))
    provider = _parse_provider(provider_raw) if provider_raw is not None else None
    if provider_raw is not None and provider is None:
        return None
    return UnityMaterial(
        id_type=id_type,
        id=material_id,
        variant=variant,
        provider=provider,
    )


def _parse_unreal_variants(raw: Mapping[str, Json]) -> UnrealVariants | None:
    variants = UnrealVariants(
        opaque=as_str(raw.get("opaque")),
        opaque_two_sided=as_str(raw.get("opaqueTwoSided")),
        translucent=as_str(raw.get("translucent")),
        translucent_two_sided=as_str(raw.get("translucentTwoSided")),
    )
    for key in raw:
        if key not in UNREAL_VARIANT_KEYS:
            continue
        value = raw.get(key)
        if value is not None and not isinstance(value, str):
            return None
    if not variants.has_any():
        return None
    return variants


def _parse_unreal_material(raw: Mapping[str, Json]) -> UnrealMaterial | None:
    id_type = as_str(raw.get("idType"))
    if id_type != ID_TYPE_MATERIAL_SET:
        return None
    variants_raw = as_dict(raw.get("variants"))
    if variants_raw is None:
        return None
    variants = _parse_unreal_variants(variants_raw)
    if variants is None:
        return None
    provider_raw = as_dict(raw.get("provider"))
    provider = _parse_provider(provider_raw) if provider_raw is not None else None
    if provider_raw is not None and provider is None:
        return None
    return UnrealMaterial(id_type=id_type, variants=variants, provider=provider)


def _parse_override(raw: Mapping[str, Json]) -> MaterialOverride | None:
    engine = as_str(raw.get("engine"))
    if engine is None or not engine:
        return None
    material_raw = as_dict(raw.get("material"))
    if material_raw is None:
        return None

    material: UnityMaterial | UnrealMaterial | None
    if engine == ENGINE_UNITY:
        material = _parse_unity_material(material_raw)
    elif engine == ENGINE_UNREAL:
        material = _parse_unreal_material(material_raw)
    else:
        return None
    if material is None:
        return None

    bindings_raw = raw.get("bindings")
    bindings: list[MaterialBinding] = []
    if bindings_raw is not None:
        bindings_list = as_list(bindings_raw)
        if bindings_list is None:
            return None
        parsed_bindings = _parse_bindings(bindings_list)
        if parsed_bindings is None:
            return None
        bindings = parsed_bindings

    properties_raw = raw.get("properties")
    properties: list[MaterialProperty] = []
    if properties_raw is not None:
        properties_list = as_list(properties_raw)
        if properties_list is None:
            return None
        parsed_properties = _parse_properties(properties_list)
        if parsed_properties is None:
            return None
        properties = parsed_properties

    return MaterialOverride(
        engine=engine,
        material=material,
        bindings=bindings,
        properties=properties,
    )


def parse_materials_override(
    extension_dict: Mapping[str, Json],
) -> VrmxtMaterialsOverride | None:
    spec_version = as_str(extension_dict.get("specVersion"))
    if spec_version != SPEC_VERSION_1_0:
        return None

    overrides_raw = as_list(extension_dict.get("overrides"))
    if overrides_raw is None or not overrides_raw:
        return None

    overrides: list[MaterialOverride] = []
    seen_engines: set[str] = set()
    for item in overrides_raw:
        override_dict = as_dict(item)
        if override_dict is None:
            return None
        override = _parse_override(override_dict)
        if override is None:
            return None
        if override.engine in seen_engines:
            return None
        seen_engines.add(override.engine)
        overrides.append(override)

    if not overrides:
        return None

    return VrmxtMaterialsOverride(spec_version=spec_version, overrides=overrides)


def _serialize_provider(provider: MaterialProvider) -> dict[str, Json]:
    result: dict[str, Json] = {"id": provider.id}
    if provider.version is not None:
        result["version"] = provider.version
    return result


def _serialize_unity_material(material: UnityMaterial) -> dict[str, Json]:
    result: dict[str, Json] = {
        "idType": material.id_type,
        "id": material.id,
    }
    if material.variant is not None:
        result["variant"] = material.variant
    if material.provider is not None:
        result["provider"] = _serialize_provider(material.provider)
    return result


def _serialize_unreal_variants(variants: UnrealVariants) -> dict[str, Json]:
    result: dict[str, Json] = {}
    if variants.opaque is not None:
        result["opaque"] = variants.opaque
    if variants.opaque_two_sided is not None:
        result["opaqueTwoSided"] = variants.opaque_two_sided
    if variants.translucent is not None:
        result["translucent"] = variants.translucent
    if variants.translucent_two_sided is not None:
        result["translucentTwoSided"] = variants.translucent_two_sided
    return result


def _serialize_unreal_material(material: UnrealMaterial) -> dict[str, Json]:
    result: dict[str, Json] = {
        "idType": material.id_type,
        "variants": _serialize_unreal_variants(material.variants),
    }
    if material.provider is not None:
        result["provider"] = _serialize_provider(material.provider)
    return result


def _serialize_material(material: UnityMaterial | UnrealMaterial) -> dict[str, Json]:
    if isinstance(material, UnityMaterial):
        return _serialize_unity_material(material)
    return _serialize_unreal_material(material)


def _serialize_binding(binding: MaterialBinding) -> dict[str, Json]:
    return {
        "source": binding.source,
        "target": binding.target,
        "targetType": binding.target_type,
    }


def _serialize_property(prop: MaterialProperty) -> dict[str, Json]:
    result: dict[str, Json] = {
        "name": prop.name,
        "type": prop.type,
    }
    if prop.type == "texture":
        result["texture"] = prop.texture if prop.texture is not None else 0
    else:
        result["value"] = prop.value
    return result


def _serialize_override(override: MaterialOverride) -> dict[str, Json]:
    result: dict[str, Json] = {
        "engine": override.engine,
        "material": _serialize_material(override.material),
    }
    if override.bindings:
        result["bindings"] = [
            _serialize_binding(binding) for binding in override.bindings
        ]
    if override.properties:
        result["properties"] = [
            _serialize_property(prop) for prop in override.properties
        ]
    return result


def serialize_materials_override(extension: VrmxtMaterialsOverride) -> dict[str, Json]:
    return {
        "specVersion": extension.spec_version,
        "overrides": [
            _serialize_override(override) for override in extension.overrides
        ],
    }


def write_materials_override_to_material_dict(
    material_dict: MutableMapping[str, Json],
    extension: VrmxtMaterialsOverride,
) -> None:
    write_raw_materials_override_to_material_dict(
        material_dict,
        serialize_materials_override(extension),
    )


def write_raw_materials_override_to_material_dict(
    material_dict: MutableMapping[str, Json],
    extension_dict: Mapping[str, Json],
) -> None:
    extensions = material_dict.get("extensions")
    if not isinstance(extensions, dict):
        extensions = {}
        material_dict["extensions"] = extensions
    extensions[EXTENSION_MATERIALS_OVERRIDE] = dict(extension_dict)


def ensure_materials_override_extensions_used(
    json_dict: MutableMapping[str, Json],
) -> None:
    ensure_extensions_used(json_dict, EXTENSION_MATERIALS_OVERRIDE)


def read_materials_override_from_material(
    material_dict: Mapping[str, Json],
) -> VrmxtMaterialsOverride | None:
    extension_dict = get_material_extension(material_dict, EXTENSION_MATERIALS_OVERRIDE)
    if extension_dict is None:
        return None
    return parse_materials_override(extension_dict)


__all__ = [
    "MaterialBinding",
    "MaterialOverride",
    "MaterialProperty",
    "MaterialProvider",
    "UnityMaterial",
    "UnrealMaterial",
    "UnrealVariants",
    "VrmxtMaterialsOverride",
    "ensure_materials_override_extensions_used",
    "parse_materials_override",
    "read_materials_override_from_material",
    "serialize_materials_override",
    "write_materials_override_to_material_dict",
    "write_raw_materials_override_to_material_dict",
]
