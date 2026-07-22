# SPDX-License-Identifier: MIT
"""Tests for materials-override PropertyGroup ↔ format sync helpers."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from io_scene_vrmxt.format.materials_override import MaterialProperty
from io_scene_vrmxt.materials_override.sync import _property_item_to_format
from io_scene_vrmxt.materials_override.vector_ui import is_color_vector_property_name


class TestColorVectorHeuristic(unittest.TestCase):
    def test_color_names(self) -> None:
        self.assertTrue(is_color_vector_property_name("_Color"))
        self.assertTrue(is_color_vector_property_name("_GlitterColor"))
        self.assertTrue(is_color_vector_property_name("_OutlineLitColor"))

    def test_non_color_names(self) -> None:
        self.assertFalse(is_color_vector_property_name("_GlitterParams1"))
        self.assertFalse(is_color_vector_property_name("_MainTexHSVG"))
        self.assertFalse(is_color_vector_property_name("_ColorMask"))  # scalar name
        self.assertFalse(is_color_vector_property_name(""))


class TestMaterialsOverrideSyncVectors(unittest.TestCase):
    def test_vector_preserves_values_above_one(self) -> None:
        """Regression: Blender COLOR+max=1 used to clamp _GlitterParams1 to 1s."""
        item = SimpleNamespace(
            name="_GlitterParams1",
            prop_type="vector",
            vector_size=4,
            value_vector=(256.0, 256.0, 1.07329607, 49.999897),
            value_color=(0.0, 0.0, 0.0, 1.0),
        )
        parsed = _property_item_to_format(item)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.type, "vector")
        self.assertEqual(
            parsed.value,
            [256.0, 256.0, 1.07329607, 49.999897],
        )

    def test_hdr_color_reads_value_color_not_vector(self) -> None:
        item = SimpleNamespace(
            name="_GlitterColor",
            prop_type="vector",
            vector_size=4,
            value_vector=(0.0, 0.0, 0.0, 0.0),
            value_color=(1.13530147, 0.8083822, 0.285311341, 1.0),
        )
        parsed = _property_item_to_format(item)
        self.assertIsInstance(parsed, MaterialProperty)
        assert parsed is not None
        assert isinstance(parsed.value, list)
        self.assertGreater(parsed.value[0], 1.0)
        self.assertAlmostEqual(parsed.value[0], 1.13530147)


if __name__ == "__main__":
    unittest.main()
