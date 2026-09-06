# SPDX-License-Identifier: MIT
"""Portable relationship mapping remains a VRMXT-owned concern."""

from __future__ import annotations

import unittest

from io_scene_vrmxt.format.mtoonxt import (
    DEPTH_ALWAYS,
    MtoonxtStencilRelationship,
)
from io_scene_vrmxt.mtoonxt.relationship_mapping import (
    relationship_shorthand_extras,
)


class RelationshipMappingTest(unittest.TestCase):
    def test_default_outside_shorthand(self) -> None:
        extras, errors = relationship_shorthand_extras(
            [MtoonxtStencilRelationship(writers=[0], readers=[1])],
            material_count=2,
        )
        self.assertFalse(errors)
        self.assertEqual(extras[0].stencil.op, "write")
        self.assertEqual(extras[1].stencil.op, "outside")
        self.assertEqual(extras[1].stencil.materials, [0])

    def test_inside_overlay_shorthand(self) -> None:
        extras, errors = relationship_shorthand_extras(
            [
                MtoonxtStencilRelationship(
                    writers=[0],
                    readers=[1],
                    writers_only_inside_readers=True,
                    show_writers_through_occluders=True,
                )
            ],
            material_count=2,
        )
        self.assertFalse(errors)
        self.assertEqual(extras[0].stencil.op, "insideOverlay")
        self.assertEqual(extras[0].stencil.materials, [1])
        self.assertEqual(extras[1].stencil.op, "write")

    def test_advanced_relation_has_no_lossy_shorthand(self) -> None:
        extras, errors = relationship_shorthand_extras(
            [
                MtoonxtStencilRelationship(
                    writers=[0],
                    readers=[1],
                    writer_depth_test=DEPTH_ALWAYS,
                )
            ],
            material_count=2,
        )
        self.assertFalse(errors)
        self.assertEqual(extras, [None, None])

    def test_colorless_writer_has_no_lossy_shorthand(self) -> None:
        extras, errors = relationship_shorthand_extras(
            [
                MtoonxtStencilRelationship(
                    writers=[0],
                    readers=[1],
                    writers_write_color=False,
                )
            ],
            material_count=2,
        )
        self.assertFalse(errors)
        self.assertEqual(extras, [None, None])

    def test_conflicting_material_roles_report_error(self) -> None:
        extras, errors = relationship_shorthand_extras(
            [
                MtoonxtStencilRelationship(writers=[0], readers=[1]),
                MtoonxtStencilRelationship(writers=[1], readers=[2]),
            ],
            material_count=3,
        )
        self.assertTrue(errors)
        self.assertEqual(len(extras), 3)


if __name__ == "__main__":
    unittest.main()
