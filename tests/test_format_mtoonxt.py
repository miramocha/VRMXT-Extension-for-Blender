# SPDX-License-Identifier: MIT
"""Tests for VRMC_materials_mtoonxt format parsing and serialization."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from io_scene_vrmxt.common.constants import (
    EXTENSION_MATERIALS_MTOON,
    EXTENSION_MATERIALS_MTOONXT,
    SPEC_VERSION_1_0,
)
from io_scene_vrmxt.format.mtoonxt import (
    OP_INSIDE,
    OP_SAME,
    OP_WRITE,
    MtoonxtStencil,
    VrmcMaterialsMtoonxt,
    listed_writers_have_body_write,
    parse_mtoonxt,
    read_mtoonxt_from_material,
    serialize_mtoonxt,
)
from io_scene_vrmxt.mtoonxt.export_hook import apply_mtoonxt_export
from io_scene_vrmxt.mtoonxt.import_hook import apply_mtoonxt_import

RESOURCES = Path(__file__).resolve().parent / "resources" / "gltf"


class TestFormatMtoonxt(unittest.TestCase):
    def test_parse_fixture(self) -> None:
        payload = json.loads(
            (RESOURCES / "mtoonxt_stencil.json").read_text(encoding="utf-8")
        )
        iris = read_mtoonxt_from_material(
            payload["materials"][0], own_index=0, material_count=2
        )
        white = read_mtoonxt_from_material(
            payload["materials"][1], own_index=1, material_count=2
        )
        self.assertIsNotNone(iris)
        self.assertIsNotNone(white)
        assert iris is not None and white is not None
        self.assertEqual(iris.spec_version, SPEC_VERSION_1_0)
        assert iris.stencil is not None
        self.assertEqual(iris.stencil.op, OP_INSIDE)
        self.assertEqual(iris.stencil.materials, [1])
        assert iris.outline_stencil is not None
        self.assertEqual(iris.outline_stencil.op, OP_SAME)
        assert white.stencil is not None
        self.assertEqual(white.stencil.op, OP_WRITE)

    def test_parse_skips_invalid_stencil_objects(self) -> None:
        extension = {
            "specVersion": "1.0",
            "stencil": {"op": "inside", "materials": [0]},
            "outlineStencil": {"op": "write"},
        }
        parsed = parse_mtoonxt(extension, own_index=0, material_count=2)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertIsNone(parsed.stencil)
        assert parsed.outline_stencil is not None
        self.assertEqual(parsed.outline_stencil.op, OP_WRITE)

    def test_parse_write_with_materials_skipped(self) -> None:
        parsed = parse_mtoonxt(
            {
                "specVersion": "1.0",
                "stencil": {"op": "write", "materials": [1]},
            },
            own_index=0,
            material_count=2,
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertIsNone(parsed.stencil)

    def test_parse_same_on_body_skipped(self) -> None:
        parsed = parse_mtoonxt(
            {"specVersion": "1.0", "stencil": {"op": "same"}},
            own_index=0,
            material_count=1,
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertIsNone(parsed.stencil)

    def test_parse_wrong_spec_fails(self) -> None:
        self.assertIsNone(parse_mtoonxt({"specVersion": "0.9"}))

    def test_serialize_round_trip(self) -> None:
        extra = VrmcMaterialsMtoonxt(
            stencil=MtoonxtStencil(op=OP_INSIDE, materials=[3]),
            outline_stencil=MtoonxtStencil(op=OP_SAME),
        )
        payload = serialize_mtoonxt(extra)
        parsed = parse_mtoonxt(payload, own_index=1, material_count=4)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(serialize_mtoonxt(extra), serialize_mtoonxt(parsed))

    def test_listed_writers_require_body_write(self) -> None:
        extras: list[VrmcMaterialsMtoonxt | None] = [None, None]
        extras[0] = VrmcMaterialsMtoonxt(
            stencil=MtoonxtStencil(op=OP_INSIDE, materials=[1])
        )
        extras[1] = VrmcMaterialsMtoonxt(stencil=MtoonxtStencil(op=OP_WRITE))
        assert extras[0] is not None
        self.assertTrue(listed_writers_have_body_write(extras[0].stencil, extras))
        extras[1] = VrmcMaterialsMtoonxt()
        self.assertFalse(listed_writers_have_body_write(extras[0].stencil, extras))


class TestMtoonxtHooks(unittest.TestCase):
    def test_import_maps_writer_pointers(self) -> None:
        iris = SimpleNamespace(vrmxt_mtoonxt_settings=_FakeSettings())
        white = SimpleNamespace(vrmxt_mtoonxt_settings=_FakeSettings())
        context = SimpleNamespace(
            json_dict={
                "materials": [
                    {
                        "name": "Iris",
                        "extensions": {
                            EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"},
                            EXTENSION_MATERIALS_MTOONXT: {
                                "specVersion": "1.0",
                                "stencil": {"op": "inside", "materials": [1]},
                            },
                        },
                    },
                    {
                        "name": "White",
                        "extensions": {
                            EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"},
                            EXTENSION_MATERIALS_MTOONXT: {
                                "specVersion": "1.0",
                                "stencil": {"op": "write"},
                            },
                        },
                    },
                ]
            },
            material_index_to_material={0: iris, 1: white},
        )
        apply_mtoonxt_import(context)
        self.assertEqual(iris.vrmxt_mtoonxt_settings.body_op, OP_INSIDE)
        self.assertEqual(list(iris.vrmxt_mtoonxt_settings.body_targets), [white])
        self.assertEqual(white.vrmxt_mtoonxt_settings.body_op, OP_WRITE)

    def test_export_writes_indices_and_skips_missing_mtoon(self) -> None:
        white_settings = _FakeSettings()
        white_settings.body_op = OP_WRITE
        iris_settings = _FakeSettings()
        iris_settings.body_op = OP_INSIDE
        iris_settings.body_targets = [_Mat("White", white_settings)]
        iris = _Mat("Iris", iris_settings)
        white = _Mat("White", white_settings)
        no_mtoon = {
            "name": "Iris",
            "extensions": {EXTENSION_MATERIALS_MTOONXT: {"specVersion": "1.0"}},
        }
        with_mtoon = {
            "name": "White",
            "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
        }
        json_dict = {"materials": [no_mtoon, with_mtoon]}
        context = SimpleNamespace(
            json_dict=json_dict,
            material_name_to_index={"Iris": 0, "White": 1},
        )
        import io_scene_vrmxt.mtoonxt.export_hook as export_hook

        original = export_hook._find_material_by_name
        mapping = {"Iris": iris, "White": white}

        def _find(name: str) -> object | None:
            return mapping.get(name)

        export_hook._find_material_by_name = _find  # type: ignore[assignment]
        try:
            apply_mtoonxt_export(context)
        finally:
            export_hook._find_material_by_name = original  # type: ignore[assignment]

        self.assertNotIn(
            EXTENSION_MATERIALS_MTOONXT,
            no_mtoon.get("extensions", {}),
        )
        white_ext = with_mtoon["extensions"][EXTENSION_MATERIALS_MTOONXT]
        self.assertEqual(white_ext["stencil"]["op"], OP_WRITE)
        used = json_dict.get("extensionsUsed")
        assert isinstance(used, list)
        self.assertIn(EXTENSION_MATERIALS_MTOONXT, used)

    def test_export_skips_clip_when_writer_is_not_body_write(self) -> None:
        white_settings = _FakeSettings()
        iris_settings = _FakeSettings()
        iris_settings.body_op = OP_INSIDE
        iris_settings.body_targets = [_Mat("White", white_settings)]
        iris = _Mat("Iris", iris_settings)
        white = _Mat("White", white_settings)
        iris_dict = {
            "name": "Iris",
            "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
        }
        white_dict = {
            "name": "White",
            "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
        }
        json_dict = {"materials": [iris_dict, white_dict]}
        context = SimpleNamespace(
            json_dict=json_dict,
            material_name_to_index={"Iris": 0, "White": 1},
        )
        import io_scene_vrmxt.mtoonxt.export_hook as export_hook

        original = export_hook._find_material_by_name
        mapping = {"Iris": iris, "White": white}

        def _find(name: str) -> object | None:
            return mapping.get(name)

        export_hook._find_material_by_name = _find  # type: ignore[assignment]
        try:
            apply_mtoonxt_export(context)
        finally:
            export_hook._find_material_by_name = original  # type: ignore[assignment]

        self.assertNotIn(
            EXTENSION_MATERIALS_MTOONXT,
            iris_dict.get("extensions", {}),
        )
        self.assertNotIn(
            EXTENSION_MATERIALS_MTOONXT,
            white_dict.get("extensions", {}),
        )


class _FakeTarget:
    def __init__(self, material: object) -> None:
        self.material = material


class _FakeSettings:
    def __init__(self) -> None:
        self.body_op = "OFF"
        self.outline_op = "OFF"
        self.body_targets: list[object] = []
        self.outline_targets: list[object] = []
        self.authored = False

    def add_body_target(self, material: object) -> None:
        self.body_targets.append(material)

    def add_outline_target(self, material: object) -> None:
        self.outline_targets.append(material)

    def clear_body_targets(self) -> None:
        self.body_targets.clear()

    def clear_outline_targets(self) -> None:
        self.outline_targets.clear()


class _Mat:
    def __init__(self, name: str, settings: _FakeSettings) -> None:
        self.name = name
        self.vrmxt_mtoonxt_settings = settings


if __name__ == "__main__":
    unittest.main()
