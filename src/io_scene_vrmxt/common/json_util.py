# SPDX-License-Identifier: MIT
"""glTF JSON typing and safe accessors."""

from __future__ import annotations

import math
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Union

Json = Union[None, bool, int, float, str, list["Json"], dict[str, "Json"]]


def as_dict(value: object) -> dict[str, Json] | None:
    if isinstance(value, dict):
        return value
    return None


def as_list(value: object) -> list[Json] | None:
    if isinstance(value, list):
        return value
    return None


def as_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def as_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def finite_numbers(values: Sequence[object], length: int) -> list[float] | None:
    if len(values) != length:
        return None
    result: list[float] = []
    for item in values:
        number = as_number(item)
        if number is None:
            return None
        result.append(number)
    return result


def ensure_extensions_used(
    json_dict: MutableMapping[str, Json], extension_name: str
) -> None:
    used = json_dict.get("extensionsUsed")
    if not isinstance(used, list):
        used = []
        json_dict["extensionsUsed"] = used
    if extension_name not in used:
        used.append(extension_name)

    required = json_dict.get("extensionsRequired")
    if isinstance(required, list) and extension_name in required:
        required.remove(extension_name)


def get_root_extension(
    json_dict: Mapping[str, Json], extension_name: str
) -> dict[str, Json] | None:
    extensions = as_dict(json_dict.get("extensions"))
    if extensions is None:
        return None
    return as_dict(extensions.get(extension_name))


def get_material_extension(
    material_dict: Mapping[str, Json],
    extension_name: str,
) -> dict[str, Json] | None:
    extensions = as_dict(material_dict.get("extensions"))
    if extensions is None:
        return None
    return as_dict(extensions.get(extension_name))


__all__ = [
    "Json",
    "as_dict",
    "as_int",
    "as_list",
    "as_number",
    "as_str",
    "ensure_extensions_used",
    "finite_numbers",
    "get_material_extension",
    "get_root_extension",
]
