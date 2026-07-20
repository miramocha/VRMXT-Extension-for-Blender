# SPDX-License-Identifier: MIT
"""Operators for VRMXT_materials_override authoring."""

from __future__ import annotations

from typing import ClassVar

from ..common.constants import ENGINE_UNITY, ID_TYPE_SHADER_NAME
from .catalog import (
    CUSTOM_SHADER_ENUM,
    find_catalog_by_key,
    find_catalog_by_shader_name,
)
from .sync import (
    CUSTOM_PROP_KEY,
    apply_catalog_default,
    existing_property_names,
    sync_raw_json_from_groups,
)

_ADD_PROPERTY_ENUM_ITEMS_CACHE: list[tuple[str, str, str]] = []

try:
    import bpy
    from bpy.props import EnumProperty, IntProperty, StringProperty
    from bpy.types import Context, Operator
except ImportError:  # pragma: no cover
    bpy = None  # type: ignore[assignment]
    Context = object  # type: ignore[misc, assignment]
    Operator = object  # type: ignore[misc, assignment]


def _active_material(context: object):
    material = getattr(context, "material", None)
    if material is not None:
        return material
    obj = getattr(context, "active_object", None)
    if obj is None:
        return None
    return getattr(obj, "active_material", None)


def _settings(context: object):
    material = _active_material(context)
    if material is None:
        return None, None
    return material, getattr(material, "vrmxt_materials_override_settings", None)


def _set_active_override(settings: object, index: int) -> None:
    count = len(settings.overrides)
    if count <= 0:
        settings.active_override_index = 0
        settings.override_slot = "0"
        return
    index = max(0, min(int(index), count - 1))
    settings.active_override_index = index
    settings.override_slot = str(index)


def _active_slot(settings: object):
    if settings is None or len(settings.overrides) == 0:
        return None
    index = max(
        0, min(int(settings.active_override_index), len(settings.overrides) - 1)
    )
    _set_active_override(settings, index)
    return settings.overrides[index]


def _sync(material: object) -> None:
    sync_raw_json_from_groups(material)


def _catalog_for_slot(slot: object):
    key = getattr(slot, "catalog_key", "") or ""
    if key:
        return find_catalog_by_key(key)
    material_id = getattr(slot, "material_id", "") or ""
    if material_id:
        return find_catalog_by_shader_name(material_id, engine=ENGINE_UNITY)
    return None


if bpy is not None:

    class VRMXT_OT_materials_override_add(Operator):
        bl_idname = "vrmxt.materials_override_add"
        bl_label = "Add Override"
        bl_description = "Add a Unity materials override slot"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            material, settings = _settings(context)
            if material is None or settings is None:
                return {"CANCELLED"}

            engine = getattr(settings, "add_engine", ENGINE_UNITY) or ENGINE_UNITY
            variant = getattr(settings, "add_variant", "builtin") or "builtin"
            if engine != ENGINE_UNITY:
                self.report({"ERROR"}, "Only Unity authoring is available")
                return {"CANCELLED"}

            for existing in settings.overrides:
                if existing.engine == engine and (existing.variant or "") == variant:
                    self.report(
                        {"ERROR"},
                        f"Override already exists for {engine} / {variant}",
                    )
                    return {"CANCELLED"}

            slot = settings.overrides.add()
            slot.engine = engine
            slot.variant = variant
            slot.id_type = ID_TYPE_SHADER_NAME
            slot.shader_enum = CUSTOM_SHADER_ENUM
            slot.catalog_key = ""
            slot.material_id = ""
            _set_active_override(settings, len(settings.overrides) - 1)
            settings.authored = True
            _sync(material)
            return {"FINISHED"}

    class VRMXT_OT_materials_override_remove(Operator):
        bl_idname = "vrmxt.materials_override_remove"
        bl_label = "Remove Override"
        bl_description = "Remove the active materials override slot"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            material, settings = _settings(context)
            if material is None or settings is None or len(settings.overrides) == 0:
                return {"CANCELLED"}
            index = int(settings.active_override_index)
            if index < 0 or index >= len(settings.overrides):
                return {"CANCELLED"}
            settings.overrides.remove(index)
            _set_active_override(settings, max(0, index - 1))
            if len(settings.overrides) == 0:
                settings.authored = False
                settings.raw_json = ""
                if CUSTOM_PROP_KEY in material:
                    del material[CUSTOM_PROP_KEY]
            else:
                settings.authored = True
                _sync(material)
            return {"FINISHED"}

    class VRMXT_OT_materials_override_add_common_props(Operator):
        bl_idname = "vrmxt.materials_override_add_common_props"
        bl_label = "Add Common Props"
        bl_description = "Append catalog properties marked common:true"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        def execute(self, context: Context) -> set[str]:
            material, settings = _settings(context)
            slot = _active_slot(settings)
            if material is None or settings is None or slot is None:
                return {"CANCELLED"}
            catalog = _catalog_for_slot(slot)
            if catalog is None:
                self.report({"WARNING"}, "No catalog for this shader")
                return {"CANCELLED"}
            existing = existing_property_names(slot)
            added = 0
            for catalog_prop in catalog.common_properties():
                if catalog_prop.name in existing:
                    continue
                item = slot.properties.add()
                apply_catalog_default(item, catalog_prop)
                existing.add(catalog_prop.name)
                added += 1
            settings.authored = True
            _sync(material)
            self.report({"INFO"}, f"Added {added} common properties")
            return {"FINISHED"}

    def _add_property_enum_items(self, context):  # type: ignore[no-untyped-def]
        _ADD_PROPERTY_ENUM_ITEMS_CACHE.clear()
        _ADD_PROPERTY_ENUM_ITEMS_CACHE.append(
            ("CUSTOM", "Custom…", "Free-text property name and type")
        )
        _material, settings = _settings(context)
        slot = _active_slot(settings)
        if slot is None:
            return _ADD_PROPERTY_ENUM_ITEMS_CACHE
        catalog = _catalog_for_slot(slot)
        if catalog is None:
            return _ADD_PROPERTY_ENUM_ITEMS_CACHE
        existing = existing_property_names(slot)
        for prop in catalog.properties:
            if prop.name in existing:
                continue
            _ADD_PROPERTY_ENUM_ITEMS_CACHE.append(
                (prop.name, prop.display_name or prop.name, prop.type)
            )
        return _ADD_PROPERTY_ENUM_ITEMS_CACHE

    class VRMXT_OT_materials_override_add_property(Operator):
        bl_idname = "vrmxt.materials_override_add_property"
        bl_label = "Add Property"
        bl_description = "Add a catalog or custom property to the active override"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        property_choice: EnumProperty(  # type: ignore[valid-type]
            name="Property",
            items=_add_property_enum_items,
        )
        custom_name: StringProperty(  # type: ignore[valid-type]
            name="Name",
            default="",
        )
        custom_type: EnumProperty(  # type: ignore[valid-type]
            name="Type",
            items=(
                ("scalar", "Scalar", ""),
                ("vector", "Vector", ""),
                ("texture", "Texture", ""),
                ("shaderFeature", "Shader Feature", ""),
            ),
            default="scalar",
        )

        def invoke(self, context: Context, _event) -> set[str]:
            return context.window_manager.invoke_props_dialog(self, width=360)

        def draw(self, _context: Context) -> None:
            layout = self.layout
            layout.prop(self, "property_choice")
            if self.property_choice == "CUSTOM":
                layout.prop(self, "custom_name")
                layout.prop(self, "custom_type")

        def execute(self, context: Context) -> set[str]:
            material, settings = _settings(context)
            slot = _active_slot(settings)
            if material is None or settings is None or slot is None:
                return {"CANCELLED"}
            existing = existing_property_names(slot)
            choice = self.property_choice
            if choice == "CUSTOM":
                name = (self.custom_name or "").strip()
                if not name:
                    self.report({"ERROR"}, "Property name required")
                    return {"CANCELLED"}
                if name in existing:
                    self.report({"ERROR"}, f"Property {name!r} already exists")
                    return {"CANCELLED"}
                item = slot.properties.add()
                item.name = name
                item.prop_type = self.custom_type
            else:
                if choice in existing:
                    self.report({"ERROR"}, f"Property {choice!r} already exists")
                    return {"CANCELLED"}
                catalog = _catalog_for_slot(slot)
                catalog_prop = (
                    catalog.property_by_name(choice) if catalog is not None else None
                )
                item = slot.properties.add()
                if catalog_prop is not None:
                    apply_catalog_default(item, catalog_prop)
                else:
                    item.name = choice
                    item.prop_type = "scalar"
            settings.authored = True
            _sync(material)
            return {"FINISHED"}

    class VRMXT_OT_materials_override_remove_property(Operator):
        bl_idname = "vrmxt.materials_override_remove_property"
        bl_label = "Remove Property"
        bl_description = "Remove this property row from the override"
        bl_options: ClassVar[set[str]] = {"REGISTER", "UNDO"}

        property_index: IntProperty(  # type: ignore[valid-type]
            name="Property Index",
            default=0,
            min=0,
        )

        def execute(self, context: Context) -> set[str]:
            material, settings = _settings(context)
            slot = _active_slot(settings)
            if material is None or settings is None or slot is None:
                return {"CANCELLED"}
            index = int(self.property_index)
            if index < 0 or index >= len(slot.properties):
                return {"CANCELLED"}
            slot.properties.remove(index)
            settings.authored = True
            _sync(material)
            return {"FINISHED"}

    CLASSES = (
        VRMXT_OT_materials_override_add,
        VRMXT_OT_materials_override_remove,
        VRMXT_OT_materials_override_add_common_props,
        VRMXT_OT_materials_override_add_property,
        VRMXT_OT_materials_override_remove_property,
    )
else:  # pragma: no cover
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
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass


__all__ = [
    "register",
    "unregister",
]
