# SPDX-License-Identifier: MIT
"""Authoring warnings when MToon alphaMode puts a stencil writer after its reader."""

from __future__ import annotations

from collections.abc import Sequence

from .property_group import iter_target_materials

# Unity MToon mapped queues: Opaque 2000, Cutout 2450, Transparent 3000.
# UniVRMXT only nudges write/inside/insideOverlay by a couple of slots inside
# that mapping.
_ALPHA_RANK = {
    "OPAQUE": 0,
    "MASK": 1,
    "BLEND": 2,
}

_ALPHA_LABEL = {
    "OPAQUE": "Opaque",
    "MASK": "Cutout",
    "BLEND": "Transparent",
}


def vrm_alpha_mode(material: object) -> str | None:
    extension = getattr(material, "vrm_addon_extension", None)
    mtoon1 = getattr(extension, "mtoon1", None)
    if mtoon1 is None or not getattr(mtoon1, "enabled", False):
        return None
    mode = getattr(mtoon1, "alpha_mode", None)
    if mode in _ALPHA_RANK:
        return str(mode)
    return None


def writer_draws_after_reader(writer_mode: str, reader_mode: str) -> bool:
    writer_rank = _ALPHA_RANK.get(writer_mode)
    reader_rank = _ALPHA_RANK.get(reader_mode)
    if writer_rank is None or reader_rank is None:
        return False
    return writer_rank > reader_rank


def collect_stencil_draw_warnings(
    material: object,
    stencils: Sequence[object],
) -> list[tuple[str, str]]:
    warnings: list[tuple[str, str]] = []
    seen: set[tuple[int, int]] = set()

    def add_pair(writer: object, reader: object, *, writer_is_self: bool) -> None:
        writer_mode = vrm_alpha_mode(writer)
        reader_mode = vrm_alpha_mode(reader)
        if writer_mode is None or reader_mode is None:
            return
        if not writer_draws_after_reader(writer_mode, reader_mode):
            return
        key = (id(writer), id(reader))
        if key in seen:
            return
        seen.add(key)
        writer_label = _ALPHA_LABEL[writer_mode]
        reader_label = _ALPHA_LABEL[reader_mode]
        writer_name = str(getattr(writer, "name", "") or "Write material")
        reader_name = str(getattr(reader, "name", "") or "Clip material")
        if writer_is_self:
            warnings.append(
                (
                    f"{reader_name} is {reader_label} and clips this Write material",
                    (
                        f"This material is {writer_label}."
                        " Write may draw too late for clip"
                    ),
                )
            )
            return
        warnings.append(
            (
                f"{writer_name} is {writer_label} and set to Write",
                f"This material is {reader_label}. Write may draw too late for clip",
            )
        )

    for stencil in stencils:
        writers = iter_target_materials(getattr(stencil, "writers", None))
        readers = iter_target_materials(getattr(stencil, "readers", None))
        if material in writers:
            for reader in readers:
                add_pair(material, reader, writer_is_self=True)
        if material in readers:
            for writer in writers:
                add_pair(writer, material, writer_is_self=False)

    return warnings


__all__ = [
    "collect_stencil_draw_warnings",
    "vrm_alpha_mode",
    "writer_draws_after_reader",
]
