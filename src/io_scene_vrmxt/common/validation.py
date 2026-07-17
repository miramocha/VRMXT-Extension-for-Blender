# SPDX-License-Identifier: MIT
"""Numeric validation helpers for VRMXT format parsing."""

from __future__ import annotations

import math
from typing import Union

Number = Union[int, float]


def is_finite_non_negative(value: object) -> bool:
    """Return True when *value* is a finite number greater than or equal to zero."""
    if not isinstance(value, (int, float)):
        return False
    if not math.isfinite(value):
        return False
    return value >= 0


def is_positive_int(value: object) -> bool:
    """Return True when *value* is an integer greater than or equal to one."""
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    return value >= 1


__all__ = ["is_finite_non_negative", "is_positive_int"]
