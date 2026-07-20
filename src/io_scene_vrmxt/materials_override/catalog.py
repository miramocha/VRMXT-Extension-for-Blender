# SPDX-License-Identifier: MIT
"""Load vendored VRMXT materials-override shader catalogs."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..common.json_util import as_dict, as_list, as_str

logger = logging.getLogger(__name__)

CATALOGS_DIR = Path(__file__).resolve().parent / "catalogs"
CUSTOM_SHADER_ENUM = "CUSTOM"


@dataclass(frozen=True)
class CatalogProperty:
    name: str
    type: str
    display_name: str
    common: bool = False
    vector_size: int = 4
    default: Any = None
    keyword: str | None = None


@dataclass(frozen=True)
class ShaderCatalog:
    key: str
    catalog_version: str
    engine: str
    display_name: str
    shader_name: str
    id_type: str
    default_variant: str | None
    supported_variants: tuple[str, ...]
    properties: tuple[CatalogProperty, ...] = field(default_factory=tuple)

    def property_by_name(self, name: str) -> CatalogProperty | None:
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None

    def common_properties(self) -> tuple[CatalogProperty, ...]:
        return tuple(prop for prop in self.properties if prop.common)


def _parse_property(raw: dict[str, Any]) -> CatalogProperty | None:
    name = as_str(raw.get("name"))
    prop_type = as_str(raw.get("type"))
    if name is None or not name or prop_type is None:
        return None
    display_name = as_str(raw.get("displayName")) or name
    vector_size = 4
    raw_size = raw.get("vectorSize")
    if isinstance(raw_size, int) and raw_size in (2, 3, 4):
        vector_size = raw_size
    keyword = as_str(raw.get("keyword"))
    return CatalogProperty(
        name=name,
        type=prop_type,
        display_name=display_name,
        common=bool(raw.get("common", False)),
        vector_size=vector_size,
        default=raw.get("default"),
        keyword=keyword,
    )


def _parse_catalog(path: Path, payload: dict[str, Any]) -> ShaderCatalog | None:
    catalog_version = as_str(payload.get("catalogVersion"))
    engine = as_str(payload.get("engine"))
    display_name = as_str(payload.get("displayName"))
    shader_name = as_str(payload.get("shaderName"))
    id_type = as_str(payload.get("idType"))
    if (
        catalog_version is None
        or engine is None
        or display_name is None
        or shader_name is None
        or id_type is None
    ):
        return None

    supported_raw = as_list(payload.get("supportedVariants"))
    if supported_raw is None:
        supported = ("builtin", "urp", "hdrp")
    else:
        supported_list = [as_str(item) for item in supported_raw]
        supported = tuple(item for item in supported_list if item)

    default_variant = as_str(payload.get("defaultVariant"))
    properties_raw = as_list(payload.get("properties")) or []
    properties: list[CatalogProperty] = []
    for item in properties_raw:
        prop_dict = as_dict(item)
        if prop_dict is None:
            continue
        parsed = _parse_property(prop_dict)
        if parsed is not None:
            properties.append(parsed)

    return ShaderCatalog(
        key=path.stem,
        catalog_version=catalog_version,
        engine=engine,
        display_name=display_name,
        shader_name=shader_name,
        id_type=id_type,
        default_variant=default_variant,
        supported_variants=supported,
        properties=tuple(properties),
    )


@lru_cache(maxsize=1)
def load_shader_catalogs() -> tuple[ShaderCatalog, ...]:
    """Load all ``*.json`` catalogs beside this module. Bad files are skipped."""
    if not CATALOGS_DIR.is_dir():
        return ()

    catalogs: list[ShaderCatalog] = []
    for path in sorted(CATALOGS_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to load materials override catalog %s", path.name)
            continue
        catalog_dict = as_dict(payload)
        if catalog_dict is None:
            logger.warning("Materials override catalog %s is not an object", path.name)
            continue
        parsed = _parse_catalog(path, catalog_dict)
        if parsed is None:
            logger.warning("Materials override catalog %s missing required fields", path.name)
            continue
        catalogs.append(parsed)
    return tuple(catalogs)


def clear_catalog_cache() -> None:
    load_shader_catalogs.cache_clear()


def find_catalog_by_key(key: str) -> ShaderCatalog | None:
    for catalog in load_shader_catalogs():
        if catalog.key == key:
            return catalog
    return None


def find_catalog_by_shader_name(
    shader_name: str,
    *,
    engine: str = "unity",
) -> ShaderCatalog | None:
    for catalog in load_shader_catalogs():
        if catalog.engine == engine and catalog.shader_name == shader_name:
            return catalog
    return None


def catalogs_for_variant(
    variant: str,
    *,
    engine: str = "unity",
) -> tuple[ShaderCatalog, ...]:
    return tuple(
        catalog
        for catalog in load_shader_catalogs()
        if catalog.engine == engine and variant in catalog.supported_variants
    )


__all__ = [
    "CUSTOM_SHADER_ENUM",
    "CatalogProperty",
    "ShaderCatalog",
    "catalogs_for_variant",
    "clear_catalog_cache",
    "find_catalog_by_key",
    "find_catalog_by_shader_name",
    "load_shader_catalogs",
]
