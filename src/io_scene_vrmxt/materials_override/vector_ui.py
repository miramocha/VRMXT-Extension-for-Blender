# SPDX-License-Identifier: MIT
"""Heuristics for materials-override vector UI (color swatch vs float4)."""

from __future__ import annotations


def is_color_vector_property_name(name: str) -> bool:
    """Unity / lilToon color params end with ``Color`` (plus exact ``_Color``).

    Param packs (``_GlitterParams1``, HSVG, scroll, etc.) must stay plain float4
    so Blender does not treat them as 0–1 colors.
    """
    trimmed = (name or "").strip()
    if not trimmed:
        return False
    return trimmed == "_Color" or trimmed.endswith("Color")


__all__ = ["is_color_vector_property_name"]
