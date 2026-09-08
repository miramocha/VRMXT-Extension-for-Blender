# SPDX-License-Identifier: MIT
"""Serialize Blender MToonXT stencil authoring into the root glTF extension."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Any

from ..common.constants import EXTENSION_MATERIALS_MTOONXT
from ..common.json_util import as_dict, as_list
from ..format.mtoonxt import (
    MtoonxtStencil,
    clear_mtoonxt_from_material_dict,
    material_has_sibling_mtoon,
    write_stencil,
)

logger = logging.getLogger(__name__)

MtoonxtStencilExportProvider = Callable[[Any, dict[str, int]], Sequence[MtoonxtStencil]]
_EXTERNAL_STENCIL_EXPORT_PROVIDERS: list[MtoonxtStencilExportProvider] = []


def register_external_stencil_export_provider(
    provider: MtoonxtStencilExportProvider,
) -> None:
    """Register an optional host stencil-graph provider.

    Scene RNA is the portable graph. A host should map into Scene `stencils` and
    return an empty sequence (BVT fill-then-`[]`). Providers that return rows are
    used only when Scene RNA is empty. Do not fill Scene and also return rows.
    """

    if provider not in _EXTERNAL_STENCIL_EXPORT_PROVIDERS:
        _EXTERNAL_STENCIL_EXPORT_PROVIDERS.append(provider)


def unregister_external_stencil_export_provider(
    provider: MtoonxtStencilExportProvider,
) -> None:
    try:
        _EXTERNAL_STENCIL_EXPORT_PROVIDERS.remove(provider)
    except ValueError:
        return


def apply_mtoonxt_export(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

    name_to_index: dict[str, int] = dict(
        getattr(context, "material_name_to_index", {}) or {}
    )
    stencils: list[MtoonxtStencil] = []
    try:
        from .property_group import stencils_from_scene, validate_stencils_in_scene

        blender_context = getattr(context, "context", None)
        scene = getattr(context, "scene", None) or getattr(
            blender_context, "scene", None
        )
        for message in validate_stencils_in_scene(scene):
            logger.warning("%s", message)
        stencils.extend(stencils_from_scene(name_to_index, scene=scene))
    except Exception:  # noqa: BLE001 - standalone RNA is optional in embedded mode
        logger.debug("VRMXT standalone stencil export unavailable", exc_info=True)
    if not stencils:
        for provider in tuple(_EXTERNAL_STENCIL_EXPORT_PROVIDERS):
            try:
                stencils.extend(provider(context, name_to_index))
            except Exception:  # noqa: BLE001 - one host must not abort export
                logger.exception("VRMXT external stencil provider failed")
    elif _EXTERNAL_STENCIL_EXPORT_PROVIDERS:
        logger.debug(
            "VRMXT skipping %s stencil provider(s); Scene RNA already has stencils",
            len(_EXTERNAL_STENCIL_EXPORT_PROVIDERS),
        )

    mtoon_material_indices = {
        material_index
        for material_index, material_entry in enumerate(materials_raw)
        if (material_dict := as_dict(material_entry)) is not None
        and material_has_sibling_mtoon(material_dict)
    }
    stencils = [
        stencil
        for stencil in stencils
        if set(stencil.writers).issubset(mtoon_material_indices)
        and set(stencil.readers).issubset(mtoon_material_indices)
    ]

    # Only the root stencil graph is portable. Never emit retired material ops.
    for material_entry in materials_raw:
        material_dict = as_dict(material_entry)
        if material_dict is None:
            continue
        extensions = as_dict(material_dict.get("extensions"))
        extra = (
            as_dict(extensions.get(EXTENSION_MATERIALS_MTOONXT)) if extensions else None
        )
        if extra is not None:
            extra.pop("stencil", None)
            extra.pop("outlineStencil", None)
            if set(extra) <= {"specVersion"}:
                clear_mtoonxt_from_material_dict(material_dict)

    write_stencil(json_dict, stencils)


def on_vrm1_export(context: Any) -> None:
    try:
        apply_mtoonxt_export(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM export
        logger.exception("VRMXT MToonXT export hook failed")


__all__ = [
    "MtoonxtStencilExportProvider",
    "apply_mtoonxt_export",
    "on_vrm1_export",
    "register_external_stencil_export_provider",
    "unregister_external_stencil_export_provider",
]
