# SPDX-License-Identifier: MIT
"""Register VRM 1.0 import/export hooks with the Extended VRM add-on."""

from __future__ import annotations

import importlib
import logging
from types import ModuleType
from typing import Any

from ..materials_override.export_hook import (
    on_vrm1_export as on_materials_export,
)
from ..materials_override.import_hook import (
    on_vrm1_import as on_materials_import,
)
from ..vfx.export_hook import on_vrm1_export as on_vfx_export
from ..vfx.import_hook import on_vrm1_import as on_vfx_import

logger = logging.getLogger(__name__)

_EXTENSION_HOOKS_MODULE: ModuleType | None = None
_HOOKS_AVAILABLE = False

_IMPORT_MODULE_CANDIDATES = ("io_scene_vrm.extension_hooks",)


def _iter_extension_hook_module_names() -> list[str]:
    names = list(_IMPORT_MODULE_CANDIDATES)
    try:
        import sys

        for module_name in sys.modules:
            if module_name.startswith("bl_ext.") and module_name.endswith(
                ".vrm.extension_hooks"
            ):
                names.append(module_name)
    except Exception:  # noqa: BLE001
        logger.debug(
            "Unable to scan sys.modules for bl_ext VRM hook modules", exc_info=True
        )
    return names


def _load_extension_hooks_module() -> ModuleType | None:
    for module_name in _iter_extension_hook_module_names():
        try:
            return importlib.import_module(module_name)
        except ImportError:
            continue
    return None


def _get_extension_hooks_module() -> ModuleType | None:
    global _EXTENSION_HOOKS_MODULE, _HOOKS_AVAILABLE
    if _EXTENSION_HOOKS_MODULE is not None:
        return _EXTENSION_HOOKS_MODULE
    module = _load_extension_hooks_module()
    if module is None:
        _HOOKS_AVAILABLE = False
        return None
    required = (
        "register_vrm1_import_extension_hook",
        "unregister_vrm1_import_extension_hook",
        "register_vrm1_export_extension_hook",
        "unregister_vrm1_export_extension_hook",
    )
    if not all(hasattr(module, name) for name in required):
        _HOOKS_AVAILABLE = False
        return None
    _EXTENSION_HOOKS_MODULE = module
    _HOOKS_AVAILABLE = True
    return module


def hooks_available() -> bool:
    return _get_extension_hooks_module() is not None


def _on_vrm1_import(context: Any) -> None:
    on_vfx_import(context)
    on_materials_import(context)


def _on_vrm1_export(context: Any) -> None:
    on_vfx_export(context)
    on_materials_export(context)


def register() -> None:
    module = _get_extension_hooks_module()
    if module is None:
        logger.info(
            "Extended VRM extension hooks are unavailable; VRMXT hooks not registered"
        )
        return
    module.register_vrm1_import_extension_hook(_on_vrm1_import)
    module.register_vrm1_export_extension_hook(_on_vrm1_export)


def unregister() -> None:
    module = _get_extension_hooks_module()
    if module is None:
        return
    module.unregister_vrm1_import_extension_hook(_on_vrm1_import)
    module.unregister_vrm1_export_extension_hook(_on_vrm1_export)


__all__ = [
    "hooks_available",
    "register",
    "unregister",
]
