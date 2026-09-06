# SPDX-License-Identifier: MIT
"""Stable integration surface for standalone and embedded hosts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Optional

from .format.mtoonxt import MtoonxtStencilRelationship, VrmxtMaterialsMtoonxt
from .hooks.vrm1_hooks import Vrm1ExportUserExtension, Vrm1ImportUserExtension
from .mtoonxt import property_group as mtoonxt_property_group
from .mtoonxt.export_hook import (
    register_external_export_provider,
    register_external_relationship_export_provider,
    unregister_external_export_provider,
    unregister_external_relationship_export_provider,
)
from .mtoonxt.import_hook import (
    register_external_relationship_import_consumer,
    unregister_external_relationship_import_consumer,
)
from .mtoonxt.property_sync import (
    initialize_bvt_scene_sync,
    sync_bvt_scene_to_vrmxt,
)

MtoonxtExportProvider = Callable[
    [Any, dict[str, int], int], Optional[VrmxtMaterialsMtoonxt]
]
MtoonxtRelationshipExportProvider = Callable[
    [Any, dict[str, int]], Sequence[MtoonxtStencilRelationship]
]
MtoonxtRelationshipImportConsumer = Callable[
    [Any, Sequence[MtoonxtStencilRelationship]], None
]
_EMBEDDED_PROVIDER: MtoonxtExportProvider | None = None
_EMBEDDED_RELATIONSHIP_PROVIDER: MtoonxtRelationshipExportProvider | None = None
_EMBEDDED_RELATIONSHIP_CONSUMER: MtoonxtRelationshipImportConsumer | None = None
_EMBEDDED_PROPERTIES_REGISTERED = False


def register_embedded(
    *,
    mtoonxt_export_provider: MtoonxtExportProvider | None = None,
    mtoonxt_relationship_export_provider: MtoonxtRelationshipExportProvider
    | None = None,
    mtoonxt_relationship_import_consumer: MtoonxtRelationshipImportConsumer
    | None = None,
    register_mtoonxt_properties: bool = True,
) -> None:
    """Register the package as a dependency without standalone UI/operators.

    VRMXT still owns its portable Blender properties and format adapters. A host
    exposes VRMXT's official VRM user-extension classes from its top-level
    package without duplicating schema or JSON code. Shared RNA is registered
    only when another standalone/embedded copy does not own it.
    """

    global _EMBEDDED_PROPERTIES_REGISTERED
    global _EMBEDDED_PROVIDER
    global _EMBEDDED_RELATIONSHIP_CONSUMER
    global _EMBEDDED_RELATIONSHIP_PROVIDER
    if register_mtoonxt_properties and not _EMBEDDED_PROPERTIES_REGISTERED:
        _EMBEDDED_PROPERTIES_REGISTERED = mtoonxt_property_group.register()
    if _EMBEDDED_PROVIDER is not None:
        unregister_external_export_provider(_EMBEDDED_PROVIDER)
    _EMBEDDED_PROVIDER = mtoonxt_export_provider
    if _EMBEDDED_PROVIDER is not None:
        register_external_export_provider(_EMBEDDED_PROVIDER)
    if _EMBEDDED_RELATIONSHIP_PROVIDER is not None:
        unregister_external_relationship_export_provider(
            _EMBEDDED_RELATIONSHIP_PROVIDER
        )
    _EMBEDDED_RELATIONSHIP_PROVIDER = mtoonxt_relationship_export_provider
    if _EMBEDDED_RELATIONSHIP_PROVIDER is not None:
        register_external_relationship_export_provider(_EMBEDDED_RELATIONSHIP_PROVIDER)
    if _EMBEDDED_RELATIONSHIP_CONSUMER is not None:
        unregister_external_relationship_import_consumer(
            _EMBEDDED_RELATIONSHIP_CONSUMER
        )
    _EMBEDDED_RELATIONSHIP_CONSUMER = mtoonxt_relationship_import_consumer
    if _EMBEDDED_RELATIONSHIP_CONSUMER is not None:
        register_external_relationship_import_consumer(_EMBEDDED_RELATIONSHIP_CONSUMER)


def unregister_embedded() -> None:
    """Reverse only registrations created by :func:`register_embedded`."""

    global _EMBEDDED_PROPERTIES_REGISTERED
    global _EMBEDDED_PROVIDER
    global _EMBEDDED_RELATIONSHIP_CONSUMER
    global _EMBEDDED_RELATIONSHIP_PROVIDER
    if _EMBEDDED_PROPERTIES_REGISTERED:
        mtoonxt_property_group.unregister()
        _EMBEDDED_PROPERTIES_REGISTERED = False
    if _EMBEDDED_PROVIDER is not None:
        unregister_external_export_provider(_EMBEDDED_PROVIDER)
        _EMBEDDED_PROVIDER = None
    if _EMBEDDED_RELATIONSHIP_PROVIDER is not None:
        unregister_external_relationship_export_provider(
            _EMBEDDED_RELATIONSHIP_PROVIDER
        )
        _EMBEDDED_RELATIONSHIP_PROVIDER = None
    if _EMBEDDED_RELATIONSHIP_CONSUMER is not None:
        unregister_external_relationship_import_consumer(
            _EMBEDDED_RELATIONSHIP_CONSUMER
        )
        _EMBEDDED_RELATIONSHIP_CONSUMER = None


__all__ = [
    "MtoonxtExportProvider",
    "MtoonxtRelationshipExportProvider",
    "MtoonxtRelationshipImportConsumer",
    "Vrm1ExportUserExtension",
    "Vrm1ImportUserExtension",
    "initialize_bvt_scene_sync",
    "register_embedded",
    "sync_bvt_scene_to_vrmxt",
    "unregister_embedded",
]
