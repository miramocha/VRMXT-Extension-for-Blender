# SPDX-License-Identifier: MIT
"""Tests for VRMXT_materials_override format parsing and serialization."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from io_scene_vrmxt.common.constants import (
    ENGINE_UNITY,
    ENGINE_UNREAL,
    EXTENSION_MATERIALS_OVERRIDE,
    ID_TYPE_MATERIAL_SET,
    ID_TYPE_SHADER_NAME,
    SPEC_VERSION_1_0,
)
from io_scene_vrmxt.format.materials_override import (
    MaterialBinding,
    MaterialOverride,
    MaterialProperty,
    UnityMaterial,
    UnrealMaterial,
    VrmxtMaterialsOverride,
    parse_materials_override,
    read_materials_override_from_material,
    serialize_materials_override,
    write_materials_override_to_material_dict,
    write_raw_materials_override_to_material_dict,
)
from io_scene_vrmxt.materials_override.export_hook import (
    apply_materials_override_export,
)
from io_scene_vrmxt.materials_override.import_hook import (
    CUSTOM_PROP_KEY,
    apply_materials_override_import,
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
        self.assertEqual(entry.material.id_type, ID_TYPE_SHADER_NAME)
        self.assertEqual(entry.material.id, "Example/SkinToon")
        self.assertEqual(entry.material.variant, "urp")
        self.assertIsNotNone(entry.material.provider)
        assert entry.material.provider is not None
        self.assertEqual(entry.material.provider.id, "com.miramocha.univrmxt")
        self.assertEqual(len(entry.bindings), 1)
        self.assertEqual(entry.bindings[0].target_type, "vector")
        self.assertEqual(len(entry.properties), 2)
        self.assertEqual(entry.properties[0].name, "_OutlineWidth")
        self.assertEqual(entry.properties[0].type, "scalar")
        self.assertEqual(entry.properties[0].value, 0.05)
        self.assertEqual(entry.properties[1].type, "shaderFeature")
        self.assertEqual(entry.properties[1].value, True)

    def test_parse_unreal_material_set(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNREAL,
                    "material": {
                        "idType": ID_TYPE_MATERIAL_SET,
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
        self.assertEqual(entry.material.id_type, ID_TYPE_MATERIAL_SET)
        self.assertEqual(entry.material.variants.opaque, "/Game/M_Opaque.M_Opaque")

    def test_rejects_duplicate_engines(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNITY,
                    "material": {
                        "idType": ID_TYPE_SHADER_NAME,
                        "id": "A",
                    },
                },
                {
                    "engine": ENGINE_UNITY,
                    "material": {
                        "idType": ID_TYPE_SHADER_NAME,
                        "id": "B",
                    },
                },
            ],
        }
        self.assertIsNone(parse_materials_override(extension))

    def test_rejects_empty_overrides(self) -> None:
        extension = {"specVersion": "1.0", "overrides": []}
        self.assertIsNone(parse_materials_override(extension))

    def test_rejects_legacy_kind_name(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNITY,
                    "material": {"kind": "shader", "name": "Example/SkinToon"},
                }
            ],
        }
        self.assertIsNone(parse_materials_override(extension))

    def test_rejects_wrong_unity_id_type(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNITY,
                    "material": {
                        "idType": ID_TYPE_MATERIAL_SET,
                        "id": "Bad",
                    },
                }
            ],
        }
        self.assertIsNone(parse_materials_override(extension))

    def test_rejects_unity_missing_id(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNITY,
                    "material": {"idType": ID_TYPE_SHADER_NAME},
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
                    "material": {
                        "idType": ID_TYPE_MATERIAL_SET,
                        "variants": {},
                    },
                }
            ],
        }
        self.assertIsNone(parse_materials_override(extension))

    def test_serialize_and_write_material_dict(self) -> None:
        override = VrmxtMaterialsOverride(
            overrides=[
                MaterialOverride(
                    engine=ENGINE_UNITY,
                    material=UnityMaterial(
                        id_type=ID_TYPE_SHADER_NAME,
                        id="Example/Toon",
                    ),
                    bindings=[
                        MaterialBinding(
                            source="shadingToonyFactor",
                            target="_ShadingToonyFactor",
                            target_type="scalar",
                        )
                    ],
                    properties=[
                        MaterialProperty(
                            name="_Color",
                            type="vector",
                            value=[1.0, 1.0, 0.0, 1.0],
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


class TestMaterialsOverrideHooks(unittest.TestCase):
    def test_import_stores_verbatim_even_when_unparsed(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNITY,
                    "material": {"kind": "shader", "name": "Legacy"},
                }
            ],
        }
        self.assertIsNone(parse_materials_override(extension))

        blender_material: dict[str, object] = {}
        context = SimpleNamespace(
            json_dict={
                "materials": [
                    {
                        "name": "Face",
                        "extensions": {EXTENSION_MATERIALS_OVERRIDE: extension},
                    }
                ]
            },
            material_index_to_material={0: blender_material},
        )
        apply_materials_override_import(context)
        self.assertIn(CUSTOM_PROP_KEY, blender_material)
        stored = json.loads(str(blender_material[CUSTOM_PROP_KEY]))
        self.assertEqual(stored, extension)

    def test_export_writes_stored_dict_without_parse(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": ENGINE_UNITY,
                    "material": {"kind": "shader", "name": "Legacy"},
                    "extraFutureField": True,
                }
            ],
        }
        stored = json.dumps(extension)

        class _Mat:
            name = "Face"

            def __contains__(self, key: object) -> bool:
                return key == CUSTOM_PROP_KEY

            def __getitem__(self, key: str) -> str:
                return stored

        material_dict: dict[str, object] = {"name": "Face"}
        context = SimpleNamespace(
            json_dict={"materials": [material_dict]},
            material_name_to_index={"Face": 0},
        )

        import io_scene_vrmxt.materials_override.export_hook as export_hook

        original_iter = export_hook._iter_scene_materials
        export_hook._iter_scene_materials = lambda _ctx: [_Mat()]  # type: ignore[assignment]
        try:
            apply_materials_override_export(context)
        finally:
            export_hook._iter_scene_materials = original_iter  # type: ignore[assignment]

        extensions = material_dict.get("extensions")
        assert isinstance(extensions, dict)
        self.assertEqual(extensions[EXTENSION_MATERIALS_OVERRIDE], extension)
        used = context.json_dict.get("extensionsUsed")
        assert isinstance(used, list)
        self.assertIn(EXTENSION_MATERIALS_OVERRIDE, used)

    def test_write_raw_preserves_unknown_fields(self) -> None:
        extension = {
            "specVersion": "1.0",
            "overrides": [],
            "futureRoot": 1,
        }
        material_dict: dict[str, object] = {"name": "Face"}
        write_raw_materials_override_to_material_dict(material_dict, extension)
        extensions = material_dict["extensions"]
        assert isinstance(extensions, dict)
        self.assertEqual(extensions[EXTENSION_MATERIALS_OVERRIDE], extension)


if __name__ == "__main__":
    unittest.main()
