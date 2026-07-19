# SPDX-License-Identifier: MIT
"""Readonly Material PROPERTIES panel for VRMXT_materials_override."""

from __future__ import annotations

import json
from typing import ClassVar

from ..common.json_util import as_dict
from ..format.materials_override import (
    UnityMaterial,
    UnrealMaterial,
    VrmxtMaterialsOverride,
    parse_materials_override,
)
from .import_hook import CUSTOM_PROP_KEY

try:
    import bpy
    from bpy.types import Context, Panel, UILayout
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    Context = object  # type: ignore[misc, assignment]
    Panel = object  # type: ignore[misc, assignment]
    UILayout = object  # type: ignore[misc, assignment]


# Peer-depend on Extended VRM material panel when that add-on is enabled.
VRM_MATERIAL_PANEL_ID = "VRM_PT_vrm_material_property"


def _read_raw_json(material: object) -> str:
    if hasattr(material, "vrmxt_materials_override_settings"):
        settings = material.vrmxt_materials_override_settings
        raw = getattr(settings, "raw_json", "") or ""
        if raw:
            return str(raw)
    if CUSTOM_PROP_KEY in material:
        return str(material[CUSTOM_PROP_KEY])
    return ""


def _active_material(context: Context) -> object | None:
    material = getattr(context, "material", None)
    if material is not None:
        return material
    obj = getattr(context, "active_object", None)
    if obj is None:
        return None
    return getattr(obj, "active_material", None)


def _format_property_value(prop: object) -> str:
    prop_type = getattr(prop, "type", "")
    if prop_type == "texture":
        return f"texture[{getattr(prop, 'texture', None)}]"
    value = getattr(prop, "value", None)
    return str(value)


def _draw_unity_material(layout: UILayout, material: UnityMaterial) -> None:
    layout.label(text=f"idType: {material.id_type}")
    layout.label(text=f"id: {material.id}")
    if material.variant is not None:
        layout.label(text=f"variant: {material.variant}")
    if material.provider is not None:
        provider_text = material.provider.id
        if material.provider.version:
            provider_text = f"{provider_text}@{material.provider.version}"
        layout.label(text=f"provider: {provider_text}")


def _draw_unreal_material(layout: UILayout, material: UnrealMaterial) -> None:
    layout.label(text=f"idType: {material.id_type}")
    variants = material.variants
    if variants.opaque is not None:
        layout.label(text=f"opaque: {variants.opaque}")
    if variants.opaque_two_sided is not None:
        layout.label(text=f"opaqueTwoSided: {variants.opaque_two_sided}")
    if variants.translucent is not None:
        layout.label(text=f"translucent: {variants.translucent}")
    if variants.translucent_two_sided is not None:
        layout.label(text=f"translucentTwoSided: {variants.translucent_two_sided}")
    if material.provider is not None:
        provider_text = material.provider.id
        if material.provider.version:
            provider_text = f"{provider_text}@{material.provider.version}"
        layout.label(text=f"provider: {provider_text}")


def _draw_parsed_override(layout: UILayout, extension: VrmxtMaterialsOverride) -> None:
    layout.label(text=f"specVersion: {extension.spec_version}")
    for entry in extension.overrides:
        box = layout.box()
        box.label(text=f"engine: {entry.engine}")
        if isinstance(entry.material, UnityMaterial):
            _draw_unity_material(box, entry.material)
        elif isinstance(entry.material, UnrealMaterial):
            _draw_unreal_material(box, entry.material)

        if entry.bindings:
            bind_box = box.box()
            bind_box.label(text="Bindings")
            for binding in entry.bindings:
                bind_box.label(
                    text=(
                        f"{binding.source} → {binding.target} ({binding.target_type})"
                    )
                )

        if entry.properties:
            prop_box = box.box()
            prop_box.label(text="Properties")
            for prop in entry.properties:
                prop_box.label(
                    text=(f"{prop.name}: {_format_property_value(prop)} ({prop.type})")
                )


def draw_materials_override_layout(layout: UILayout, material: object) -> None:
    raw_json = _read_raw_json(material)
    if not raw_json:
        layout.label(text="No VRMXT materials override")
        return

    try:
        parsed_json = json.loads(raw_json)
    except json.JSONDecodeError:
        layout.label(text="Stored (invalid JSON)")
        return

    extension_dict = as_dict(parsed_json)
    if extension_dict is None:
        layout.label(text="Stored (unparsed)")
        return

    extension = parse_materials_override(extension_dict)
    if extension is None:
        layout.label(text="Stored (unparsed)")
        layout.label(text="Export still round-trips this JSON.")
        preview = raw_json if len(raw_json) <= 80 else raw_json[:77] + "..."
        layout.label(text=preview)
        return

    _draw_parsed_override(layout, extension)


if bpy is not None:

    class VRMXT_PT_materials_override(Panel):
        bl_idname = "VRMXT_PT_materials_override"
        bl_label = "Materials Override"
        bl_space_type = "PROPERTIES"
        bl_region_type = "WINDOW"
        bl_context = "material"
        bl_options: ClassVar[set[str]] = {"DEFAULT_CLOSED"}
        bl_parent_id = VRM_MATERIAL_PANEL_ID

        @classmethod
        def poll(cls, context: Context) -> bool:
            # Always show for the active material so the panel is discoverable
            # even before an override is imported (draw shows empty state).
            return _active_material(context) is not None

        def draw_header(self, _context: Context) -> None:
            self.layout.label(icon="MATERIAL")

        def draw(self, context: Context) -> None:
            material = _active_material(context)
            if material is None:
                return
            draw_materials_override_layout(self.layout, material)

    CLASSES = (VRMXT_PT_materials_override,)
else:  # pragma: no cover
    VRMXT_PT_materials_override = None  # type: ignore[misc, assignment]
    CLASSES = ()


def register() -> None:
    if bpy is None:
        return
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister() -> None:
    if bpy is None:
        return
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


__all__ = [
    "VRM_MATERIAL_PANEL_ID",
    "VRMXT_PT_materials_override",
    "draw_materials_override_layout",
    "register",
    "unregister",
]
