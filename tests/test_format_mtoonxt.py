# SPDX-License-Identifier: MIT
"""Tests for VRMXT_materials_mtoonxt format parsing and serialization."""

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
    DEPTH_ALWAYS,
    MtoonxtStencil,
    VrmxtMaterialsMtoonxt,
    coalesce_stencils,
    parse_mtoonxt,
    parse_stencils,
    read_mtoonxt_from_material,
    serialize_mtoonxt,
    serialize_stencil,
    write_stencil,
)
from io_scene_vrmxt.mtoonxt.export_hook import apply_mtoonxt_export
from io_scene_vrmxt.mtoonxt.import_hook import apply_mtoonxt_import

RESOURCES = Path(__file__).resolve().parent / "resources" / "gltf"


class TestFormatMtoonxt(unittest.TestCase):
    def test_retired_material_fixture_is_ignored(self) -> None:
        payload = json.loads(
            (RESOURCES / "mtoonxt_stencil.json").read_text(encoding="utf-8")
        )
        iris = read_mtoonxt_from_material(payload["materials"][0])
        white = read_mtoonxt_from_material(payload["materials"][1])
        self.assertIsNotNone(iris)
        self.assertIsNotNone(white)
        assert iris is not None and white is not None
        self.assertEqual(iris.spec_version, SPEC_VERSION_1_0)
        self.assertEqual(serialize_mtoonxt(iris), {"specVersion": SPEC_VERSION_1_0})

    def test_read_ignores_retired_gltf_key(self) -> None:
        extra = read_mtoonxt_from_material(
            {
                "name": "Face",
                "extensions": {
                    "VRMC_materials_mtoon": {"specVersion": "1.0"},
                    EXTENSION_MATERIALS_MTOONXT: {
                        "specVersion": "1.0",
                        "stencil": {"op": "write"},
                    },
                },
            }
        )
        self.assertIsNotNone(extra)
        assert extra is not None
        self.assertEqual(serialize_mtoonxt(extra), {"specVersion": SPEC_VERSION_1_0})

    def test_retired_inside_overlay_is_ignored(self) -> None:
        parsed = parse_mtoonxt(
            {
                "specVersion": "1.0",
                "stencil": {"op": "insideOverlay", "materials": [0]},
                "outlineStencil": {"op": "same"},
            }
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(serialize_mtoonxt(parsed), {"specVersion": SPEC_VERSION_1_0})

    def test_parse_skips_retired_material_ops(self) -> None:
        extension = {
            "specVersion": "1.0",
            "stencil": {"op": "inside", "materials": [0]},
            "outlineStencil": {"op": "write"},
        }
        parsed = parse_mtoonxt(extension)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertNotIn("stencil", serialize_mtoonxt(parsed))
        self.assertNotIn("outlineStencil", serialize_mtoonxt(parsed))

    def test_parse_wrong_spec_fails(self) -> None:
        self.assertIsNone(parse_mtoonxt({"specVersion": "0.9"}))

    def test_serialize_round_trip(self) -> None:
        extra = VrmxtMaterialsMtoonxt()
        payload = serialize_mtoonxt(extra)
        parsed = parse_mtoonxt(payload)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(serialize_mtoonxt(extra), serialize_mtoonxt(parsed))
        self.assertNotIn("outlineStencil", payload)

    def test_retired_root_name_is_not_an_alias(self) -> None:
        document = {
            "extensions": {
                "VRMXT_materials_mtoonxt": {
                    "specVersion": "1.0",
                    "stencilRelationships": [{"writers": [0], "readers": [1]}],
                }
            }
        }
        self.assertEqual(parse_stencils(document, material_count=2), [])

    def test_root_stencil_round_trip_and_defaults(self) -> None:
        document = {"materials": [{}, {}]}
        stencil = MtoonxtStencil(
            writers=[1],
            readers=[0],
            show_writers_through_occluders=True,
            writers_self_occlude=False,
            writers_write_color=False,
            writers_write_depth=False,
            writer_depth_test=DEPTH_ALWAYS,
        )
        write_stencil(document, [stencil])
        payload = document["extensions"][EXTENSION_MATERIALS_MTOONXT]
        self.assertFalse(payload["stencil"][0]["writersWriteColor"])
        self.assertNotIn("readersWriteDepth", payload["stencil"][0])
        self.assertNotIn("outlineStencil", payload)
        self.assertNotIn("outlineStencil", payload["stencil"][0])
        parsed = parse_stencils(document, material_count=2)
        self.assertEqual(parsed, [stencil])
        self.assertIn(EXTENSION_MATERIALS_MTOONXT, document["extensionsUsed"])

        write_stencil(document, [stencil, stencil])
        payload = document["extensions"][EXTENSION_MATERIALS_MTOONXT]
        self.assertEqual(len(payload["stencil"]), 1)

    def test_equivalent_writer_stencils_coalesce_readers(self) -> None:
        stencils = coalesce_stencils(
            [
                MtoonxtStencil(writers=[0], readers=[1], writers_write_color=False),
                MtoonxtStencil(writers=[0], readers=[2], writers_write_color=False),
            ]
        )
        self.assertEqual(len(stencils), 1)
        self.assertEqual(stencils[0].writers, [0])
        self.assertEqual(stencils[0].readers, [1, 2])
        self.assertFalse(stencils[0].writers_write_color)

    def test_root_stencil_skips_invalid_entries_individually(self) -> None:
        document = {
            "materials": [{}, {}, {}],
            "extensions": {
                EXTENSION_MATERIALS_MTOONXT: {
                    "specVersion": "1.0",
                    "stencil": [
                        {"writers": [0], "readers": [1]},
                        {"writers": [0], "readers": [0]},
                        {
                            "writers": [2],
                            "readers": [1],
                            "writersOnlyInsideReaders": True,
                            "writersOnlyOutsideReaders": True,
                        },
                    ],
                }
            },
        }
        parsed = parse_stencils(document, material_count=3)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].writers, [0])
        self.assertEqual(parsed[0].readers, [1])

    def test_serialize_stencil_omits_outline_key(self) -> None:
        payload = serialize_stencil(MtoonxtStencil(writers=[0], readers=[1]))
        self.assertNotIn("outlineStencil", payload)
        self.assertNotIn("op", payload)


class TestMtoonxtHooks(unittest.TestCase):
    def test_import_ignores_retired_material_writer_pointers(self) -> None:
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
            material_index_to_material={},
            scene=None,
        )
        apply_mtoonxt_import(context)
        self.assertEqual(parse_stencils(context.json_dict, material_count=2), [])

    def test_import_ignores_retired_material_inside_overlay(self) -> None:
        context = SimpleNamespace(
            json_dict={
                "materials": [
                    {
                        "name": "Swimsuit",
                        "extensions": {
                            EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"},
                            EXTENSION_MATERIALS_MTOONXT: {
                                "specVersion": "1.0",
                                "stencil": {"op": "write"},
                            },
                        },
                    },
                    {
                        "name": "Skeleton",
                        "extensions": {
                            EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"},
                            EXTENSION_MATERIALS_MTOONXT: {
                                "specVersion": "1.0",
                                "stencil": {"op": "insideOverlay", "materials": [0]},
                                "outlineStencil": {"op": "same"},
                            },
                        },
                    },
                ]
            },
            material_index_to_material={},
            scene=None,
        )
        apply_mtoonxt_import(context)
        self.assertEqual(parse_stencils(context.json_dict, material_count=2), [])

    def test_external_root_stencil_export_and_import(self) -> None:
        import io_scene_vrmxt.mtoonxt.export_hook as export_hook
        import io_scene_vrmxt.mtoonxt.import_hook as import_hook

        stencil = MtoonxtStencil(
            writers=[1], readers=[0], show_writers_through_occluders=True
        )
        document = {
            "materials": [
                {
                    "name": "Reader",
                    "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
                },
                {
                    "name": "Writer",
                    "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
                },
            ]
        }
        export_context = SimpleNamespace(
            json_dict=document,
            material_name_to_index={"Reader": 0, "Writer": 1},
        )

        def provider(_context, _indices):
            return [stencil]

        received: list[MtoonxtStencil] = []

        def consumer(_context, values):
            received.extend(values)

        export_hook.register_external_stencil_export_provider(provider)
        import_hook.register_external_stencil_import_consumer(consumer)
        try:
            export_hook.apply_mtoonxt_export(export_context)
            import_hook.apply_mtoonxt_import(
                SimpleNamespace(
                    json_dict=document,
                    material_index_to_material={},
                    scene=None,
                )
            )
        finally:
            export_hook.unregister_external_stencil_export_provider(provider)
            import_hook.unregister_external_stencil_import_consumer(consumer)
        self.assertEqual(received, [stencil])
        root = document["extensions"][EXTENSION_MATERIALS_MTOONXT]
        self.assertNotIn("outlineStencil", root)
        self.assertNotIn("outlineStencil", root["stencil"][0])

    def test_export_pops_leftover_material_stencil_ops(self) -> None:
        leftover = {
            "name": "Iris",
            "extensions": {
                EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"},
                EXTENSION_MATERIALS_MTOONXT: {
                    "specVersion": "1.0",
                    "stencil": {"op": "inside", "materials": [1]},
                    "outlineStencil": {"op": "same"},
                },
            },
        }
        with_mtoon = {
            "name": "White",
            "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
        }
        json_dict = {"materials": [leftover, with_mtoon]}
        apply_mtoonxt_export(
            SimpleNamespace(
                json_dict=json_dict,
                material_name_to_index={"Iris": 0, "White": 1},
            )
        )
        self.assertNotIn(
            EXTENSION_MATERIALS_MTOONXT,
            leftover.get("extensions", {}),
        )
        self.assertNotIn(EXTENSION_MATERIALS_MTOONXT, with_mtoon["extensions"])

    def test_export_does_not_emit_outline_stencil(self) -> None:
        document = {
            "materials": [
                {
                    "name": "Reader",
                    "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
                },
                {
                    "name": "Writer",
                    "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
                },
            ]
        }
        import io_scene_vrmxt.mtoonxt.export_hook as export_hook

        def provider(_context, _indices):
            return [MtoonxtStencil(writers=[1], readers=[0])]

        export_hook.register_external_stencil_export_provider(provider)
        try:
            apply_mtoonxt_export(
                SimpleNamespace(
                    json_dict=document,
                    material_name_to_index={"Reader": 0, "Writer": 1},
                )
            )
        finally:
            export_hook.unregister_external_stencil_export_provider(provider)

        dumped = json.dumps(document)
        self.assertNotIn("outlineStencil", dumped)
        self.assertIn('"stencil"', dumped)


if __name__ == "__main__":
    unittest.main()
