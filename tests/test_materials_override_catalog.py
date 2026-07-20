# SPDX-License-Identifier: MIT
"""Tests for vendored materials-override shader catalogs."""

from __future__ import annotations

import unittest

from io_scene_vrmxt.materials_override.catalog import (
    catalogs_for_variant,
    clear_catalog_cache,
    find_catalog_by_shader_name,
    load_shader_catalogs,
)


class TestMaterialsOverrideCatalogs(unittest.TestCase):
    def setUp(self) -> None:
        clear_catalog_cache()

    def tearDown(self) -> None:
        clear_catalog_cache()

    def test_loads_liltoon_family(self) -> None:
        catalogs = load_shader_catalogs()
        keys = {catalog.key for catalog in catalogs}
        self.assertIn("unity-liltoon", keys)
        self.assertIn("unity-liltoon-cutout", keys)
        self.assertIn("unity-liltoon-transparent", keys)
        self.assertIn("unity-vrmxt-test-override-builtin", keys)
        self.assertIn("unity-vrmxt-test-override-urp", keys)

    def test_liltoon_opaque_identity(self) -> None:
        catalog = find_catalog_by_shader_name("lilToon")
        self.assertIsNotNone(catalog)
        assert catalog is not None
        self.assertEqual(catalog.display_name, "lilToon")
        self.assertEqual(catalog.shader_name, "lilToon")
        self.assertEqual(catalog.supported_variants, ("builtin", "urp"))
        self.assertGreaterEqual(len(catalog.common_properties()), 1)
        self.assertGreater(len(catalog.properties), len(catalog.common_properties()))

    def test_vrmxt_test_override_identity(self) -> None:
        builtin = find_catalog_by_shader_name("VRMXT/Samples/TestOverrideBuiltin")
        urp = find_catalog_by_shader_name("VRMXT/Samples/TestOverrideURP")
        self.assertIsNotNone(builtin)
        self.assertIsNotNone(urp)
        assert builtin is not None and urp is not None
        self.assertEqual(builtin.supported_variants, ("builtin",))
        self.assertEqual(urp.supported_variants, ("urp",))
        self.assertEqual(len(builtin.properties), 11)
        self.assertEqual(len(builtin.common_properties()), 11)
        rim = builtin.property_by_name("_USE_RIM_LIGHT")
        self.assertIsNotNone(rim)
        assert rim is not None
        self.assertEqual(rim.type, "shaderFeature")
        self.assertEqual(rim.keyword, "_USE_RIM_LIGHT")

    def test_variant_filter_excludes_hdrp(self) -> None:
        builtin = catalogs_for_variant("builtin")
        urp = catalogs_for_variant("urp")
        hdrp = catalogs_for_variant("hdrp")
        self.assertGreaterEqual(len(builtin), 4)
        self.assertGreaterEqual(len(urp), 4)
        self.assertEqual(len(hdrp), 0)
        builtin_names = {c.shader_name for c in builtin}
        urp_names = {c.shader_name for c in urp}
        self.assertIn("VRMXT/Samples/TestOverrideBuiltin", builtin_names)
        self.assertNotIn("VRMXT/Samples/TestOverrideURP", builtin_names)
        self.assertIn("VRMXT/Samples/TestOverrideURP", urp_names)
        self.assertNotIn("VRMXT/Samples/TestOverrideBuiltin", urp_names)

    def test_common_cutoff_present(self) -> None:
        catalog = find_catalog_by_shader_name("lilToon")
        assert catalog is not None
        cutoff = catalog.property_by_name("_Cutoff")
        self.assertIsNotNone(cutoff)
        assert cutoff is not None
        self.assertTrue(cutoff.common)
        self.assertEqual(cutoff.type, "scalar")


if __name__ == "__main__":
    unittest.main()
