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
    body_op: str = "OFF",
    body_targets: list[object] | None = None,
    outline_op: str = "OFF",
    outline_targets: list[object] | None = None,
    mtoon_enabled: bool = True,
) -> SimpleNamespace:
    mtoon1 = SimpleNamespace(enabled=mtoon_enabled, alpha_mode=alpha_mode)
    return SimpleNamespace(
        name=name,
        vrm_addon_extension=SimpleNamespace(mtoon1=mtoon1),
        vrmxt_mtoonxt_settings=SimpleNamespace(
            body_op=body_op,
            outline_op=outline_op,
            body_targets=body_targets or [],
            outline_targets=outline_targets or [],
        ),
    )


class TestMtoonxtDrawOrder(unittest.TestCase):
    def test_rank(self) -> None:
        self.assertTrue(writer_draws_after_reader("BLEND", "MASK"))
        self.assertTrue(writer_draws_after_reader("MASK", "OPAQUE"))
        self.assertFalse(writer_draws_after_reader("MASK", "MASK"))
        self.assertFalse(writer_draws_after_reader("MASK", "BLEND"))
        self.assertFalse(writer_draws_after_reader("OPAQUE", "MASK"))

    def test_hair_outside_transparent_brow(self) -> None:
        brow = _material("Brow_Face-NoRim", alpha_mode="BLEND", body_op="write")
        hair = _material(
            "Hair-Highlight",
            alpha_mode="MASK",
            body_op="outside",
            body_targets=[brow],
        )
        mats = [brow, hair]
        hair_warn = collect_stencil_draw_warnings(hair, mats)
        brow_warn = collect_stencil_draw_warnings(brow, mats)
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
        white = _material("White", alpha_mode="MASK", body_op="write")
        iris = _material(
            "Iris",
            alpha_mode="MASK",
            body_op="inside",
            body_targets=[white],
        )
        self.assertEqual(collect_stencil_draw_warnings(iris, [white, iris]), [])
        self.assertEqual(collect_stencil_draw_warnings(white, [white, iris]), [])

    def test_skips_disabled_mtoon(self) -> None:
        brow = _material(
            "Brow", alpha_mode="BLEND", body_op="write", mtoon_enabled=False
        )
        hair = _material(
            "Hair",
            alpha_mode="MASK",
            body_op="outside",
            body_targets=[brow],
        )
        self.assertEqual(collect_stencil_draw_warnings(hair, [brow, hair]), [])
