# SPDX-License-Identifier: MIT
"""Blender property groups for VRMXT_materials_override authoring."""

from __future__ import annotations

from ..common.constants import ENGINE_UNITY, ENGINE_UNREAL, ID_TYPE_SHADER_NAME
from .catalog import CUSTOM_SHADER_ENUM, catalogs_for_variant, find_catalog_by_key

# Blender EnumProperty items callbacks MUST keep returned strings alive.
# Returning a fresh list each call → GC → garbled / random labels on hover.
_OVERRIDE_SLOT_ITEMS_CACHE: list[tuple[str, str, str]] = []
_SHADER_ENUM_ITEMS_CACHE: list[tuple[str, str, str]] = []

_VARIANT_UI_LABELS = {
    "builtin": "Built-In",
    "urp": "URP",
    "hdrp": "HDRP",
}


def engine_ui_label(engine: str) -> str:
    if engine == ENGINE_UNITY:
        return "Unity"
    if engine == ENGINE_UNREAL:
        return "Unreal"
    return engine or "?"


def variant_ui_label(variant: str) -> str:
    return _VARIANT_UI_LABELS.get(variant, variant or "?")


def override_slot_label(slot: object, index: int = 0) -> str:
    engine = getattr(slot, "engine", "") or "override"
    if engine == ENGINE_UNITY:
        variant = variant_ui_label(getattr(slot, "variant", "") or "")
        catalog_key = getattr(slot, "catalog_key", "") or ""
        catalog = find_catalog_by_key(catalog_key) if catalog_key else None
        if catalog is not None:
            shader = catalog.display_name
        else:
            shader = (getattr(slot, "material_id", "") or "").strip() or "Custom"
        return f"Unity · {variant} · {shader}"
    return f"{engine} · slot {index + 1}"


try:
    import bpy
    from bpy.props import (
        BoolProperty,
        CollectionProperty,
        EnumProperty,
        FloatProperty,
        FloatVectorProperty,
        IntProperty,
        PointerProperty,
        StringProperty,
    )
    from bpy.types import Image, PropertyGroup
except ImportError:  # pragma: no cover - exercised only outside Blender
    bpy = None  # type: ignore[assignment]
    PropertyGroup = object  # type: ignore[misc, assignment]
    VrmxtMaterialsOverridePropertyItem = None  # type: ignore[misc, assignment]
    VrmxtMaterialsOverrideEntry = None  # type: ignore[misc, assignment]
    VrmxtMaterialsOverrideSettings = None  # type: ignore[misc, assignment]
else:
    # Staging / authoring: Unity only for first ship (Unreal UI later).
    _ADD_ENGINE_ITEMS = ((ENGINE_UNITY, "Unity", "Unity engine override"),)
    _ENGINE_ITEMS = (
        (ENGINE_UNITY, "Unity", "Unity engine override"),
        (ENGINE_UNREAL, "Unreal", "Unreal engine override (authoring limited)"),
    )
    _VARIANT_ITEMS = (
        ("builtin", "Built-In", "Built-in Render Pipeline"),
        ("urp", "URP", "Universal Render Pipeline"),
        ("hdrp", "HDRP", "High Definition Render Pipeline"),
    )
    _PROP_TYPE_ITEMS = (
        ("scalar", "Scalar", "Float / int scalar"),
        ("vector", "Vector", "Color or vector"),
        ("texture", "Texture", "Texture reference"),
        ("shaderFeature", "Shader Feature", "Boolean keyword toggle"),
    )

    def _override_slot_items(self, _context):  # type: ignore[no-untyped-def]
        _OVERRIDE_SLOT_ITEMS_CACHE.clear()
        overrides = getattr(self, "overrides", None)
        if overrides is None or len(overrides) == 0:
            _OVERRIDE_SLOT_ITEMS_CACHE.append(
                ("0", "(none)", "No override slots")
            )
        else:
            for i, slot in enumerate(overrides):
                _OVERRIDE_SLOT_ITEMS_CACHE.append(
                    (str(i), override_slot_label(slot, i), "")
                )
        return _OVERRIDE_SLOT_ITEMS_CACHE

    def _on_override_slot_update(self, _context) -> None:  # type: ignore[no-untyped-def]
        try:
            self.active_override_index = int(self.override_slot)
        except (TypeError, ValueError):
            self.active_override_index = 0

    def _shader_enum_items(self, _context):  # type: ignore[no-untyped-def]
        _SHADER_ENUM_ITEMS_CACHE.clear()
        _SHADER_ENUM_ITEMS_CACHE.append(
            (CUSTOM_SHADER_ENUM, "Custom…", "Free-text Unity shader name")
        )
        engine = getattr(self, "engine", ENGINE_UNITY)
        variant = getattr(self, "variant", "builtin") or "builtin"
        if engine == ENGINE_UNITY:
            for catalog in catalogs_for_variant(variant, engine=engine):
                _SHADER_ENUM_ITEMS_CACHE.append(
                    (catalog.key, catalog.display_name, catalog.shader_name)
                )
        return _SHADER_ENUM_ITEMS_CACHE

    def _on_shader_enum_update(self, _context) -> None:  # type: ignore[no-untyped-def]
        choice = getattr(self, "shader_enum", CUSTOM_SHADER_ENUM)
        if choice == CUSTOM_SHADER_ENUM:
            self.catalog_key = ""
            return
        catalog = find_catalog_by_key(choice)
        if catalog is None:
            self.catalog_key = ""
            return
        self.catalog_key = catalog.key
        self.id_type = catalog.id_type
        self.material_id = catalog.shader_name

    class VrmxtMaterialsOverridePropertyItem(PropertyGroup):  # type: ignore[misc]
        """One ``properties[]`` row on an override slot."""

        name: StringProperty(  # type: ignore[valid-type]
            name="Name",
            default="",
        )
        prop_type: EnumProperty(  # type: ignore[valid-type]
            name="Type",
            items=_PROP_TYPE_ITEMS,
            default="scalar",
        )
        value_float: FloatProperty(  # type: ignore[valid-type]
            name="Value",
            default=0.0,
        )
        value_vector: FloatVectorProperty(  # type: ignore[valid-type]
            name="Value",
            size=4,
            subtype="COLOR",
            min=0.0,
            max=1.0,
            default=(1.0, 1.0, 1.0, 1.0),
        )
        vector_size: IntProperty(  # type: ignore[valid-type]
            name="Vector Size",
            default=4,
            min=2,
            max=4,
        )
        value_bool: BoolProperty(  # type: ignore[valid-type]
            name="Value",
            default=False,
        )
        image: PointerProperty(  # type: ignore[valid-type]
            name="Image",
            type=Image,
        )
        texture_index: IntProperty(  # type: ignore[valid-type]
            name="Texture Index",
            description="glTF textures[] index from import (used when Image is empty)",
            default=-1,
            min=-1,
        )

    class VrmxtMaterialsOverrideEntry(PropertyGroup):  # type: ignore[misc]
        """One ``overrides[]`` slot. Engine/variant set at Add time; not edited later."""

        engine: EnumProperty(  # type: ignore[valid-type]
            name="Engine",
            items=_ENGINE_ITEMS,
            default=ENGINE_UNITY,
        )
        variant: EnumProperty(  # type: ignore[valid-type]
            name="Variant",
            items=_VARIANT_ITEMS,
            default="builtin",
        )
        id_type: StringProperty(  # type: ignore[valid-type]
            name="Id Type",
            default=ID_TYPE_SHADER_NAME,
        )
        material_id: StringProperty(  # type: ignore[valid-type]
            name="Shader Name",
            default="",
            description="Exact Unity Shader.Find name (material.id)",
        )
        catalog_key: StringProperty(  # type: ignore[valid-type]
            name="Catalog Key",
            default="",
            description="Vendored catalog stem; empty means Custom",
        )
        shader_enum: EnumProperty(  # type: ignore[valid-type]
            name="Material / Shader",
            items=_shader_enum_items,
            update=_on_shader_enum_update,
        )
        properties: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMaterialsOverridePropertyItem
        )

    class VrmxtMaterialsOverrideSettings(PropertyGroup):  # type: ignore[misc]
        """Per-material VRMXT_materials_override authoring state."""

        raw_json: StringProperty(  # type: ignore[valid-type]
            name="Materials Override JSON",
            default="",
        )
        authored: BoolProperty(  # type: ignore[valid-type]
            name="Authored",
            default=False,
            description="When true, PropertyGroups are the source of truth for export",
        )
        # Staging controls for Add Override (not stored in glTF).
        add_engine: EnumProperty(  # type: ignore[valid-type]
            name="Engine",
            description="Engine for the next Add Override",
            items=_ADD_ENGINE_ITEMS,
            default=ENGINE_UNITY,
        )
        add_variant: EnumProperty(  # type: ignore[valid-type]
            name="Variant",
            description="Render-pipeline variant for the next Add Override",
            items=_VARIANT_ITEMS,
            default="builtin",
        )
        overrides: CollectionProperty(  # type: ignore[valid-type]
            type=VrmxtMaterialsOverrideEntry
        )
        active_override_index: IntProperty(  # type: ignore[valid-type]
            name="Override Index",
            default=0,
        )
        override_slot: EnumProperty(  # type: ignore[valid-type]
            name="Override",
            description="Which override slot to edit",
            items=_override_slot_items,
            update=_on_override_slot_update,
        )


def register() -> None:
    if bpy is None:
        return
    bpy.utils.register_class(VrmxtMaterialsOverridePropertyItem)
    bpy.utils.register_class(VrmxtMaterialsOverrideEntry)
    bpy.utils.register_class(VrmxtMaterialsOverrideSettings)
    bpy.types.Material.vrmxt_materials_override_settings = PointerProperty(  # type: ignore[attr-defined]
        type=VrmxtMaterialsOverrideSettings
    )


def unregister() -> None:
    if bpy is None:
        return
    if hasattr(bpy.types.Material, "vrmxt_materials_override_settings"):
        del bpy.types.Material.vrmxt_materials_override_settings
    for cls in (
        VrmxtMaterialsOverrideSettings,
        VrmxtMaterialsOverrideEntry,
        VrmxtMaterialsOverridePropertyItem,
    ):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass


__all__ = [
    "VrmxtMaterialsOverrideEntry",
    "VrmxtMaterialsOverridePropertyItem",
    "VrmxtMaterialsOverrideSettings",
    "engine_ui_label",
    "override_slot_label",
    "register",
    "unregister",
    "variant_ui_label",
]
