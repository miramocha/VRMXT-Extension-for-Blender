# SPDX-License-Identifier: MIT
"""Serialize Blender MToonXT stencil authoring into the root glTF extension."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Any, Optional

from ..common.json_util import as_dict, as_list
from ..format.mtoonxt import (
    CLIP_OPS,
    OP_SAME,
    OP_WRITE,
    MtoonxtStencil,
    MtoonxtStencilRelationship,
    VrmxtMaterialsMtoonxt,
    clear_mtoonxt_from_material_dict,
    ensure_mtoonxt_extensions_used,
    material_has_sibling_mtoon,
    write_stencil_relationships,
)
from .property_group import (
    BODY_OP_OFF,
    OUTLINE_OP_OFF,
    iter_target_materials,
)

logger = logging.getLogger(__name__)

MtoonxtExportProvider = Callable[
    [Any, dict[str, int], int], Optional[VrmxtMaterialsMtoonxt]
]
MtoonxtRelationshipExportProvider = Callable[
    [Any, dict[str, int]], Sequence[MtoonxtStencilRelationship]
]
_EXTERNAL_EXPORT_PROVIDERS: list[MtoonxtExportProvider] = []
_EXTERNAL_RELATIONSHIP_EXPORT_PROVIDERS: list[MtoonxtRelationshipExportProvider] = []


def register_external_export_provider(provider: MtoonxtExportProvider) -> None:
    """Register an optional host authoring provider.

    A host such as Beyond VTuber Tools can embed this package without
    duplicating VRMXT property groups. Providers are additive and run after the
    standalone add-on's own material settings, so a host can fill or override
    the body and outline stencil fields it owns.
    """

    if provider not in _EXTERNAL_EXPORT_PROVIDERS:
        _EXTERNAL_EXPORT_PROVIDERS.append(provider)


def unregister_external_export_provider(provider: MtoonxtExportProvider) -> None:
    try:
        _EXTERNAL_EXPORT_PROVIDERS.remove(provider)
    except ValueError:
        return


def register_external_relationship_export_provider(
    provider: MtoonxtRelationshipExportProvider,
) -> None:
    if provider not in _EXTERNAL_RELATIONSHIP_EXPORT_PROVIDERS:
        _EXTERNAL_RELATIONSHIP_EXPORT_PROVIDERS.append(provider)


def unregister_external_relationship_export_provider(
    provider: MtoonxtRelationshipExportProvider,
) -> None:
    try:
        _EXTERNAL_RELATIONSHIP_EXPORT_PROVIDERS.remove(provider)
    except ValueError:
        return


def _merge_extra(
    base: VrmxtMaterialsMtoonxt | None,
    override: VrmxtMaterialsMtoonxt | None,
) -> VrmxtMaterialsMtoonxt | None:
    if override is None:
        return base
    if base is None:
        return override
    if override.stencil is not None:
        base.stencil = override.stencil
    if override.outline_stencil is not None:
        base.outline_stencil = override.outline_stencil
    return base


def _find_material_by_name(material_name: str) -> Any | None:
    try:
        import bpy
    except ImportError:
        return None
    for material in bpy.data.materials:
        if getattr(material, "name", None) == material_name:
            return material
    return None


def _resolve_clip_indices(
    targets: object,
    material_name_to_index: dict[str, int],
    own_index: int,
) -> list[int]:
    indices: list[int] = []
    seen: set[int] = set()
    for material in iter_target_materials(targets):
        name = getattr(material, "name", None)
        if not isinstance(name, str):
            continue
        index = material_name_to_index.get(name)
        if index is None or index == own_index or index in seen:
            continue
        seen.add(index)
        indices.append(index)
    return indices


def _stencil_from_settings(
    op: str,
    targets: object,
    material_name_to_index: dict[str, int],
    own_index: int,
    *,
    allow_same: bool,
) -> MtoonxtStencil | None:
    if op in ("", BODY_OP_OFF, OUTLINE_OP_OFF):
        return None
    if op == OP_SAME:
        if not allow_same:
            return None
        return MtoonxtStencil(op=OP_SAME)
    if op == OP_WRITE:
        return MtoonxtStencil(op=OP_WRITE)
    if op in CLIP_OPS:
        indices = _resolve_clip_indices(targets, material_name_to_index, own_index)
        if not indices:
            return None
        return MtoonxtStencil(op=op, materials=indices)
    return None


def extra_from_blender_material(
    material: Any,
    material_name_to_index: dict[str, int],
    own_index: int,
    *,
    include_material_settings: bool = True,
) -> VrmxtMaterialsMtoonxt | None:
    extra = None
    settings = (
        getattr(material, "vrmxt_mtoonxt_settings", None)
        if include_material_settings
        else None
    )
    if settings is not None:
        body = _stencil_from_settings(
            str(getattr(settings, "body_op", BODY_OP_OFF) or BODY_OP_OFF),
            getattr(settings, "body_targets", None),
            material_name_to_index,
            own_index,
            allow_same=False,
        )
        outline = _stencil_from_settings(
            str(getattr(settings, "outline_op", OUTLINE_OP_OFF) or OUTLINE_OP_OFF),
            getattr(settings, "outline_targets", None),
            material_name_to_index,
            own_index,
            allow_same=body is not None,
        )
        if body is not None or outline is not None:
            extra = VrmxtMaterialsMtoonxt(
                stencil=body,
                outline_stencil=outline,
            )

    for provider in tuple(_EXTERNAL_EXPORT_PROVIDERS):
        try:
            extra = _merge_extra(
                extra,
                provider(material, material_name_to_index, own_index),
            )
        except Exception:  # noqa: BLE001 - one host must not abort export
            logger.exception("VRMXT external MToonXT export provider failed")
    return extra


def apply_mtoonxt_export(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

    name_to_index: dict[str, int] = dict(
        getattr(context, "material_name_to_index", {}) or {}
    )
    relationships: list[MtoonxtStencilRelationship] = []
    try:
        from .property_group import relationships_from_scene

        blender_context = getattr(context, "context", None)
        scene = getattr(context, "scene", None) or getattr(
            blender_context, "scene", None
        )
        relationships.extend(relationships_from_scene(name_to_index, scene=scene))
    except Exception:  # noqa: BLE001 - standalone RNA is optional in embedded mode
        logger.debug("VRMXT standalone relationship export unavailable", exc_info=True)
    for provider in tuple(_EXTERNAL_RELATIONSHIP_EXPORT_PROVIDERS):
        try:
            relationships.extend(provider(context, name_to_index))
        except Exception:  # noqa: BLE001 - one host must not abort export
            logger.exception("VRMXT external stencil relationship provider failed")

    mtoon_material_indices = {
        material_index
        for material_index, material_entry in enumerate(materials_raw)
        if (material_dict := as_dict(material_entry)) is not None
        and material_has_sibling_mtoon(material_dict)
    }
    relationships = [
        relationship
        for relationship in relationships
        if set(relationship.writers).issubset(mtoon_material_indices)
        and set(relationship.readers).issubset(mtoon_material_indices)
    ]

    # Only the root stencil graph is portable. Never emit retired material ops.
    for material_entry in materials_raw:
        material_dict = as_dict(material_entry)
        if material_dict is None:
            continue
        extensions = as_dict(material_dict.get("extensions"))
        extra = (
            as_dict(extensions.get("VRMXT_materials_mtoonxt")) if extensions else None
        )
        if extra is not None:
            extra.pop("stencil", None)
            extra.pop("outlineStencil", None)
            if set(extra) <= {"specVersion"}:
                clear_mtoonxt_from_material_dict(material_dict)

    write_stencil_relationships(json_dict, relationships)

    if relationships:
        ensure_mtoonxt_extensions_used(json_dict)


def on_vrm1_export(context: Any) -> None:
    try:
        apply_mtoonxt_export(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM export
        logger.exception("VRMXT MToonXT export hook failed")


__all__ = [
    "MtoonxtExportProvider",
    "MtoonxtRelationshipExportProvider",
    "apply_mtoonxt_export",
    "extra_from_blender_material",
    "on_vrm1_export",
    "register_external_export_provider",
    "register_external_relationship_export_provider",
    "unregister_external_export_provider",
    "unregister_external_relationship_export_provider",
]
