# SPDX-License-Identifier: MIT
"""Stable integration surface for standalone and embedded hosts."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from .format.mtoonxt import MtoonxtStencil
from .hooks.vrm1_hooks import Vrm1ExportUserExtension, Vrm1ImportUserExtension
from .mtoonxt import property_group as mtoonxt_property_group
from .mtoonxt.export_hook import (
    register_external_stencil_export_provider,
    unregister_external_stencil_export_provider,
)
from .mtoonxt.import_hook import (
    register_external_stencil_import_consumer,
    unregister_external_stencil_import_consumer,
)

MtoonxtStencilExportProvider = Callable[[Any, dict[str, int]], Sequence[MtoonxtStencil]]
MtoonxtStencilImportConsumer = Callable[[Any, Sequence[MtoonxtStencil]], None]
_EMBEDDED_STENCIL_PROVIDER: MtoonxtStencilExportProvider | None = None
_EMBEDDED_STENCIL_CONSUMER: MtoonxtStencilImportConsumer | None = None
_EMBEDDED_PROPERTIES_REGISTERED = False


def register_embedded(
    *,
    mtoonxt_stencil_export_provider: MtoonxtStencilExportProvider | None = None,
    mtoonxt_stencil_import_consumer: MtoonxtStencilImportConsumer | None = None,
    register_mtoonxt_properties: bool = True,
) -> None:
    """Register the package as a dependency without standalone UI/operators.

    VRMXT still owns its portable Blender properties and format adapters. A host
    maps its authoring into VRMXT Scene RNA (or supplies `MtoonxtStencil` rows
    through the export provider). The host exposes VRMXT's official VRM
    user-extension classes from its top-level package without duplicating schema
    or JSON code. Shared RNA is registered only when another standalone/embedded
    copy does not own it.
    """

    global _EMBEDDED_PROPERTIES_REGISTERED
    global _EMBEDDED_STENCIL_CONSUMER
    global _EMBEDDED_STENCIL_PROVIDER
    if register_mtoonxt_properties and not _EMBEDDED_PROPERTIES_REGISTERED:
        _EMBEDDED_PROPERTIES_REGISTERED = mtoonxt_property_group.register()
    if _EMBEDDED_STENCIL_PROVIDER is not None:
        unregister_external_stencil_export_provider(_EMBEDDED_STENCIL_PROVIDER)
    _EMBEDDED_STENCIL_PROVIDER = mtoonxt_stencil_export_provider
    if _EMBEDDED_STENCIL_PROVIDER is not None:
        register_external_stencil_export_provider(_EMBEDDED_STENCIL_PROVIDER)
    if _EMBEDDED_STENCIL_CONSUMER is not None:
        unregister_external_stencil_import_consumer(_EMBEDDED_STENCIL_CONSUMER)
    _EMBEDDED_STENCIL_CONSUMER = mtoonxt_stencil_import_consumer
    if _EMBEDDED_STENCIL_CONSUMER is not None:
        register_external_stencil_import_consumer(_EMBEDDED_STENCIL_CONSUMER)


def unregister_embedded() -> None:
    """Reverse only registrations created by :func:`register_embedded`."""

    global _EMBEDDED_PROPERTIES_REGISTERED
    global _EMBEDDED_STENCIL_CONSUMER
    global _EMBEDDED_STENCIL_PROVIDER
    if _EMBEDDED_PROPERTIES_REGISTERED:
        mtoonxt_property_group.unregister()
        _EMBEDDED_PROPERTIES_REGISTERED = False
    if _EMBEDDED_STENCIL_PROVIDER is not None:
        unregister_external_stencil_export_provider(_EMBEDDED_STENCIL_PROVIDER)
        _EMBEDDED_STENCIL_PROVIDER = None
    if _EMBEDDED_STENCIL_CONSUMER is not None:
        unregister_external_stencil_import_consumer(_EMBEDDED_STENCIL_CONSUMER)
        _EMBEDDED_STENCIL_CONSUMER = None


__all__ = [
    "MtoonxtStencilExportProvider",
    "MtoonxtStencilImportConsumer",
    "Vrm1ExportUserExtension",
    "Vrm1ImportUserExtension",
    "register_embedded",
    "unregister_embedded",
]
