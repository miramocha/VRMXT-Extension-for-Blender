# SPDX-License-Identifier: MIT
"""Material PROPERTIES panel for VRMXT_materials_override authoring."""

from __future__ import annotations

import contextlib
from typing import ClassVar

from .catalog import CUSTOM_SHADER_ENUM, find_catalog_by_key
from .property_group import engine_ui_label, variant_ui_label
from .sync import CUSTOM_PROP_KEY
from .vector_ui import is_color_vector_property_name

try:
    import bpy
    from bpy.types import Context, Panel, UILayout
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    Context = object  # type: ignore[misc, assignment]
    Panel = object  # type: ignore[misc, assignment]
    UILayout = object  # type: ignore[misc, assignment]


VRM_MATERIAL_PANEL_ID = "VRM_PT_vrm_material_property"


def _active_material(context: Context):
    material = getattr(context, "material", None)
    if material is not None:
        return material
    obj = getattr(context, "active_object", None)
    if obj is None:
        return None
    return getattr(obj, "active_material", None)


def _draw_property_row(layout: UILayout, item: object, property_index: int) -> None:
    row = layout.row(align=True)
    row.label(text=str(getattr(item, "name", "")))
    prop_type = getattr(item, "prop_type", "scalar")
    if prop_type == "scalar":
        row.prop(item, "value_float", text="")
    elif prop_type == "vector":
        if is_color_vector_property_name(str(getattr(item, "name", ""))):
            # HDR swatch (value_color: COLOR, soft_max=10, no hard max=1).
            row.prop(item, "value_color", text="")
        else:
            # Param packs — expanded unclamped float4.
            row.prop(item, "value_vector", text="", expand=True)
    elif prop_type == "texture":
        row.prop(item, "image", text="")
    elif prop_type == "shaderFeature":
        row.prop(item, "value_bool", text="")
    else:
        row.label(text=str(prop_type))
    op = row.operator(
        "vrmxt.materials_override_remove_property",
        text="",
        icon="X",
    )
    op.property_index = property_index


def _draw_slot(layout: UILayout, slot: object) -> None:
    box = layout.box()
    # Engine / variant locked after Add — display only.
    box.label(text=f"Engine: {engine_ui_label(getattr(slot, 'engine', ''))}")
    if getattr(slot, "engine", "") == "unity":
        box.label(text=f"Variant: {variant_ui_label(getattr(slot, 'variant', ''))}")
        box.prop(slot, "shader_enum")
        if getattr(slot, "shader_enum", "") == CUSTOM_SHADER_ENUM:
            box.prop(slot, "material_id")
        else:
            catalog = find_catalog_by_key(getattr(slot, "catalog_key", "") or "")
            if catalog is not None:
                box.label(text=f"id: {catalog.shader_name}")
            elif getattr(slot, "material_id", ""):
                box.label(text=f"id: {slot.material_id}")
    else:
        box.label(text="Unreal authoring not available yet")

    props_box = box.box()
    props_box.label(text="Properties")
    row = props_box.row(align=True)
    catalog = find_catalog_by_key(getattr(slot, "catalog_key", "") or "")
    common_enabled = catalog is not None and any(p.common for p in catalog.properties)
    sub = row.row(align=True)
    sub.enabled = common_enabled
    sub.operator(
        "vrmxt.materials_override_add_common_props",
        text="Add Common Props",
        icon="ADD",
    )
    row.operator(
        "vrmxt.materials_override_add_property",
        text="Add",
        icon="ADD",
    )

    if len(slot.properties) == 0:
        props_box.label(text="No properties")
    else:
        for index, item in enumerate(slot.properties):
            _draw_property_row(props_box.row(align=True), item, index)


def draw_materials_override_layout(layout: UILayout, material: object) -> None:
    settings = getattr(material, "vrmxt_materials_override_settings", None)
    if settings is None:
        layout.label(text="Materials override settings unavailable")
        return

    # Staging: pick Engine + Variant, then Add.
    staging = layout.row(align=True)
    staging.prop(settings, "add_engine", text="")
    staging.prop(settings, "add_variant", text="")
    staging.operator("vrmxt.materials_override_add", text="Add Override", icon="ADD")

    if len(settings.overrides) == 0:
        raw = settings.raw_json or ""
        if not raw and CUSTOM_PROP_KEY in material:
            raw = str(material[CUSTOM_PROP_KEY])
        if raw and not settings.authored:
            layout.label(text="Stored override (uneditable / Unreal or unparsed)")
            preview = raw if len(raw) <= 80 else raw[:77] + "..."
            layout.label(text=preview)
        else:
            layout.label(text="No override slots — pick Engine / Variant, then Add")
        return

    slot_row = layout.row(align=True)
    slot_row.prop(settings, "override_slot", text="Override")
    slot_row.operator("vrmxt.materials_override_remove", text="", icon="REMOVE")
    index = int(getattr(settings, "active_override_index", 0) or 0)
    index = max(0, min(index, len(settings.overrides) - 1))
    slot = settings.overrides[index]
    _draw_slot(layout, slot)


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
        with contextlib.suppress(RuntimeError):
            bpy.utils.unregister_class(cls)


__all__ = [
    "VRM_MATERIAL_PANEL_ID",
    "VRMXT_PT_materials_override",
    "draw_materials_override_layout",
    "register",
    "unregister",
]
