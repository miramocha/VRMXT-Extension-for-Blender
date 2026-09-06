# SPDX-License-Identifier: MIT
"""MToonXT stencil draw-order authoring warnings."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from io_scene_vrmxt.mtoonxt.draw_order import (
    collect_stencil_draw_warnings,
    writer_draws_after_reader,
)


def _material(
    name: str,
    *,
    alpha_mode: str,
    mtoon_enabled: bool = True,
) -> SimpleNamespace:
    mtoon1 = SimpleNamespace(enabled=mtoon_enabled, alpha_mode=alpha_mode)
    return SimpleNamespace(
        name=name,
        vrm_addon_extension=SimpleNamespace(mtoon1=mtoon1),
    )


def _stencils(*pairs: tuple[object, object]) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(writers=[writer], readers=[reader]) for writer, reader in pairs
    ]


class TestMtoonxtDrawOrder(unittest.TestCase):
    def test_rank(self) -> None:
        self.assertTrue(writer_draws_after_reader("BLEND", "MASK"))
        self.assertTrue(writer_draws_after_reader("MASK", "OPAQUE"))
        self.assertFalse(writer_draws_after_reader("MASK", "MASK"))
        self.assertFalse(writer_draws_after_reader("MASK", "BLEND"))
        self.assertFalse(writer_draws_after_reader("OPAQUE", "MASK"))

    def test_hair_outside_transparent_brow(self) -> None:
        brow = _material("Brow_Face-NoRim", alpha_mode="BLEND")
        hair = _material("Hair-Highlight", alpha_mode="MASK")
        stencils = _stencils((brow, hair))
        hair_warn = collect_stencil_draw_warnings(hair, stencils)
        brow_warn = collect_stencil_draw_warnings(brow, stencils)
        self.assertEqual(
            hair_warn,
            [
                (
                    "Brow_Face-NoRim is Transparent and set to Write",
                    "This material is Cutout. Write may draw too late for clip",
                )
            ],
        )
        self.assertEqual(
            brow_warn,
            [
                (
                    "Hair-Highlight is Cutout and clips this Write material",
                    "This material is Transparent. Write may draw too late for clip",
                )
            ],
        )

    def test_same_cutout_silent(self) -> None:
        white = _material("White", alpha_mode="MASK")
        iris = _material("Iris", alpha_mode="MASK")
        stencils = _stencils((white, iris))
        self.assertEqual(collect_stencil_draw_warnings(iris, stencils), [])
        self.assertEqual(collect_stencil_draw_warnings(white, stencils), [])

    def test_same_cutout_inside_overlay_silent(self) -> None:
        suit = _material("Swimsuit", alpha_mode="MASK")
        bone = _material("Skeleton", alpha_mode="MASK")
        stencils = _stencils((suit, bone))
        self.assertEqual(collect_stencil_draw_warnings(bone, stencils), [])
        self.assertEqual(collect_stencil_draw_warnings(suit, stencils), [])

    def test_skips_disabled_mtoon(self) -> None:
        brow = _material("Brow", alpha_mode="BLEND", mtoon_enabled=False)
        hair = _material("Hair", alpha_mode="MASK")
        stencils = _stencils((brow, hair))
        self.assertEqual(collect_stencil_draw_warnings(hair, stencils), [])
