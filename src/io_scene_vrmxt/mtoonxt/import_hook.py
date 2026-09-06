# SPDX-License-Identifier: MIT
"""Apply VRMXT_materials_mtoonxt stencil data to Blender Scene properties."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from typing import Any

from ..common.json_util import as_list
from ..format.mtoonxt import (
    MtoonxtStencil,
    parse_stencils,
)
from .property_group import (
    apply_parsed_stencils_to_scene,
)

logger = logging.getLogger(__name__)

MtoonxtStencilImportConsumer = Callable[[Any, Sequence[MtoonxtStencil]], None]
_EXTERNAL_STENCIL_IMPORT_CONSUMERS: list[MtoonxtStencilImportConsumer] = []


def register_external_stencil_import_consumer(
    consumer: MtoonxtStencilImportConsumer,
) -> None:
    if consumer not in _EXTERNAL_STENCIL_IMPORT_CONSUMERS:
        _EXTERNAL_STENCIL_IMPORT_CONSUMERS.append(consumer)


def unregister_external_stencil_import_consumer(
    consumer: MtoonxtStencilImportConsumer,
) -> None:
    try:
        _EXTERNAL_STENCIL_IMPORT_CONSUMERS.remove(consumer)
    except ValueError:
        return


def apply_mtoonxt_import(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

    index_to_material = getattr(context, "material_index_to_material", {}) or {}
    material_count = len(materials_raw)

    stencils = parse_stencils(json_dict, material_count=material_count)
    if stencils:
        apply_parsed_stencils_to_scene(stencils, dict(index_to_material), context)
        for consumer in tuple(_EXTERNAL_STENCIL_IMPORT_CONSUMERS):
            try:
                consumer(context, stencils)
            except Exception:  # noqa: BLE001 - one host must not abort import
                logger.exception("VRMXT external stencil consumer failed")


def on_vrm1_import(context: Any) -> None:
    try:
        apply_mtoonxt_import(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM import
        logger.exception("VRMXT MToonXT import hook failed")


__all__ = [
    "MtoonxtStencilImportConsumer",
    "apply_mtoonxt_import",
    "on_vrm1_import",
    "register_external_stencil_import_consumer",
    "unregister_external_stencil_import_consumer",
]
