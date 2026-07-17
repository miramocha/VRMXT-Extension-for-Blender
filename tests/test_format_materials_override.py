# SPDX-License-Identifier: MIT
"""Tests for VRMXT_materials_override format parsing and serialization."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from io_scene_vrmxt.common.constants import (
    ENGINE_UNITY,
    ENGINE_UNREAL,
    EXTENSION_MATERIALS_OVERRIDE,
    SPEC_VERSION_1_0,
)
from io_scene_vrmxt.format.materials_override import (
    MaterialBinding,
    MaterialOverride,
    UnityMaterial,
    UnrealMaterial,
    VrmxtMaterialsOverride,
    parse_materials_override,
    read_materials_override_from_material,
    serialize_materials_override,
    write_materials_override_to_material_dict,
)

RESOURCES = Path(__file__).resolve().parent / "resources" / "gltf"


class TestFormatMaterialsOverride(unittest.TestCase):
    def test_parse_unity_fixture(self) -> None:
        payload = json.loads(
            (RESOURCES / "materials_override_unity.json").read_text(encoding="utf-8")
        )
        material = payload["materials"][0]
        override = read_materials_override_from_material(material)
        self.assertIsNotNone(override)
        assert override is not None
        self.assertEqual(override.spec_version, SPEC_VERSION_1_0)
        self.assertEqual(len(override.overrides), 1)
        entry = override.overrides[0]
        self.assertEqual(entry.engine, ENGINE_UNITY)
        self.assertIsInstance(entry.material, UnityMaterial)
        assert isinstance(entry.material, UnityMaterial)
        self.assertEqual(entry.material.kind, "shader")
        self.assertEqual(entry.material.name, "Example/SkinToon")
        self.assertEqual(entry.material.variant, "urp")
        self.assertEqual(len(entry.bindings), 1)
        self.assertEqual(entry.bindings[0].target_type, "vector")

    def test_parse_unreal_material_set(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNREAL,
                    "material": {
                        "kind": "materialSet",
                        "variants": {"opaque": "/Game/M_Opaque.M_Opaque"},
                    },
                }
            ],
        }
        override = parse_materials_override(extension)
        self.assertIsNotNone(override)
        assert override is not None
        entry = override.overrides[0]
        self.assertIsInstance(entry.material, UnrealMaterial)
        assert isinstance(entry.material, UnrealMaterial)
        self.assertEqual(entry.material.variants.opaque, "/Game/M_Opaque.M_Opaque")

    def test_rejects_duplicate_engines(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNITY,
                    "material": {"kind": "shader", "name": "A"},
                },
                {
                    "engine": ENGINE_UNITY,
                    "material": {"kind": "shader", "name": "B"},
                },
            ],
        }
        self.assertIsNone(parse_materials_override(extension))

    def test_rejects_empty_overrides(self) -> None:
        extension = {"specVersion": "1.0", "overrides": []}
        self.assertIsNone(parse_materials_override(extension))

    def test_rejects_invalid_unity_kind(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNITY,
                    "material": {"kind": "materialSet", "name": "Bad"},
                }
            ],
        }
        self.assertIsNone(parse_materials_override(extension))

    def test_rejects_unreal_without_variants(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNREAL,
                    "material": {"kind": "materialSet", "variants": {}},
                }
            ],
        }
        self.assertIsNone(parse_materials_override(extension))

    def test_serialize_and_write_material_dict(self) -> None:
        override = VrmxtMaterialsOverride(
            overrides=[
                MaterialOverride(
                    engine=ENGINE_UNITY,
                    material=UnityMaterial(kind="shader", name="Example/Toon"),
                    bindings=[
                        MaterialBinding(
                            source="shadingToonyFactor",
                            target="_ShadingToonyFactor",
                            target_type="scalar",
                        )
                    ],
                )
            ]
        )
        material_dict: dict[str, object] = {"name": "Face"}
        write_materials_override_to_material_dict(material_dict, override)
        extensions = material_dict["extensions"]
        assert isinstance(extensions, dict)
        payload = extensions[EXTENSION_MATERIALS_OVERRIDE]
        assert isinstance(payload, dict)
        parsed = parse_materials_override(payload)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(
            serialize_materials_override(override),
            serialize_materials_override(parsed),
        )


if __name__ == "__main__":
    unittest.main()
