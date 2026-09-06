# SPDX-License-Identifier: MIT
"""Stock VRM 4.6.0 user-extension entry points for VRMXT import/export."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from ..materials_override.export_hook import (
    on_vrm1_export as on_materials_export,
)
from ..materials_override.import_hook import (
    on_vrm1_import as on_materials_import,
)
from ..mtoonxt.export_hook import on_vrm1_export as on_mtoonxt_export
from ..mtoonxt.import_hook import on_vrm1_import as on_mtoonxt_import
from ..mtoonxt.property_sync import sync_bvt_scene_to_vrmxt
from ..vfx.export_hook import on_vrm1_export as on_vfx_export
from ..vfx.import_hook import on_vrm1_import as on_vfx_import
from .shim import make_export_context, make_import_context

logger = logging.getLogger(__name__)


def _on_vrm1_import(context: Any) -> None:
    on_vfx_import(context)
    on_materials_import(context)
    on_mtoonxt_import(context)


def _on_vrm1_export(context: Any) -> None:
    on_vfx_export(context)
    on_materials_export(context)
    on_mtoonxt_export(context)


class Vrm1ImportUserExtension:
    """Discovered by stock VRM on the add-on root module."""

    def post_import_hook(
        self,
        json_chunk: Mapping[str, Any],
        _bin_chunk: bytes,
        armature: Any,
        node_index_to_object: Mapping[int, Any],
        node_index_to_bone: Mapping[int, Any],
        image_index_to_image: Mapping[int, Any],
        material_index_to_material: Mapping[int, Any],
        mesh_index_to_mesh: Mapping[int, Any],
    ) -> None:
        _on_vrm1_import(
            make_import_context(
                json_chunk,
                armature,
                node_index_to_object,
                node_index_to_bone,
                image_index_to_image,
                material_index_to_material,
                mesh_index_to_mesh,
            )
        )


class Vrm1ExportUserExtension:
    """Discovered by stock VRM on the add-on root module."""

    def pre_save_hook(
        self,
        json_chunk: dict[str, Any],
        bin_chunk: bytearray,
        armature: Any,
        node_index_to_object: Mapping[int, Any],
        node_index_to_bone: Mapping[int, Any],
        image_index_to_image: Mapping[int, Any],
        material_index_to_material: Mapping[int, Any],
        mesh_index_to_mesh: Mapping[int, Any],
    ) -> None:
        context = make_export_context(
            json_chunk,
            bin_chunk,
            armature,
            node_index_to_object,
            node_index_to_bone,
            image_index_to_image,
            material_index_to_material,
            mesh_index_to_mesh,
        )
        context.mtoonxt_relationship_graph_authoritative = False
        if context.scene is not None:
            context.mtoonxt_relationship_graph_authoritative = bool(
                sync_bvt_scene_to_vrmxt(context.scene)
            )
        _on_vrm1_export(context)


__all__ = [
    "Vrm1ExportUserExtension",
    "Vrm1ImportUserExtension",
]
