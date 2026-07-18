# SPDX-License-Identifier: MIT
"""Append VFX particle images into the host VRM export glTF document."""

from __future__ import annotations

import importlib
import logging
from collections.abc import MutableMapping, Sequence
from typing import Any

logger = logging.getLogger(__name__)

_IMAGE_HELPERS: tuple[Any, Any] | None | bool = False


def _load_image_helpers() -> tuple[Any, Any] | None:
    """Return ``(find_or_create_image, create_export_settings)`` or ``None``."""
    global _IMAGE_HELPERS
    if _IMAGE_HELPERS is False:
        candidates = (
            (
                "io_scene_vrm.exporter.vrm1_exporter",
                "Vrm1Exporter",
                "io_scene_vrm.external.io_scene_gltf2_support",
            ),
            (
                "bl_ext.user_default.vrm.exporter.vrm1_exporter",
                "Vrm1Exporter",
                "bl_ext.user_default.vrm.external.io_scene_gltf2_support",
            ),
        )
        for exporter_module, exporter_attr, support_module in candidates:
            try:
                exporter = getattr(
                    importlib.import_module(exporter_module), exporter_attr
                )
                support = importlib.import_module(support_module)
                _IMAGE_HELPERS = (
                    exporter.find_or_create_image,
                    support.create_export_settings,
                )
                break
            except Exception:  # noqa: BLE001
                continue
        else:
            _IMAGE_HELPERS = None
            logger.warning(
                "VRM image export helpers unavailable; VFX textures will be omitted"
            )
    if _IMAGE_HELPERS is False or _IMAGE_HELPERS is None:
        return None
    return _IMAGE_HELPERS


def find_texture_index_for_image(
    image_index: int,
    textures: Sequence[Any] | None,
) -> int | None:
    if not isinstance(textures, Sequence):
        return None
    for texture_index, texture_dict in enumerate(textures):
        if isinstance(texture_dict, dict) and texture_dict.get("source") == image_index:
            return texture_index
    return None


def ensure_vfx_texture_index(
    *,
    image: Any,
    json_dict: MutableMapping[str, Any],
    buffer0: bytearray,
    image_name_to_index: MutableMapping[str, int],
) -> int | None:
    """Ensure ``images[]`` / ``textures[]`` entries exist; return textures[] index."""
    if image is None:
        return None

    if image.name in image_name_to_index:
        textures_existing = json_dict.get("textures")
        texture_index = find_texture_index_for_image(
            image_name_to_index[image.name],
            textures_existing if isinstance(textures_existing, list) else None,
        )
        if texture_index is not None:
            return texture_index

    helpers = _load_image_helpers()
    if helpers is None:
        return None
    find_or_create_image, create_export_settings = helpers

    try:
        image_index = find_or_create_image(
            json_dict,
            buffer0,
            image_name_to_index,
            image,
            create_export_settings(),
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Failed to append VFX image %r to glTF",
            getattr(image, "name", image),
        )
        return None

    textures = json_dict.get("textures")
    if not isinstance(textures, list):
        textures = []
        json_dict["textures"] = textures

    texture_index = find_texture_index_for_image(image_index, textures)
    if texture_index is not None:
        return texture_index

    samplers = json_dict.get("samplers")
    if not isinstance(samplers, list):
        samplers = []
        json_dict["samplers"] = samplers
    if not samplers:
        # Default sampler (REPEAT / LINEAR) matching typical VRM material export.
        samplers.append(
            {
                "magFilter": 9729,
                "minFilter": 9729,
                "wrapS": 10497,
                "wrapT": 10497,
            }
        )

    texture_index = len(textures)
    textures.append({"sampler": 0, "source": image_index})
    return texture_index


__all__ = [
    "ensure_vfx_texture_index",
    "find_texture_index_for_image",
]
