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
    OP_INSIDE,
    OP_INSIDE_OVERLAY,
    OP_SAME,
    OP_WRITE,
    MtoonxtStencil,
    MtoonxtStencilRelationship,
    VrmxtMaterialsMtoonxt,
    coalesce_stencil_relationships,
    drop_unresolvable_stencils,
    listed_writers_have_body_write,
    parse_mtoonxt,
    parse_stencil_relationships,
    read_mtoonxt_from_material,
    serialize_mtoonxt,
    write_stencil_relationships,
)
from io_scene_vrmxt.mtoonxt.export_hook import (
    apply_mtoonxt_export,
    extra_from_blender_material,
    register_external_export_provider,
    unregister_external_export_provider,
)
from io_scene_vrmxt.mtoonxt.import_hook import apply_mtoonxt_import

RESOURCES = Path(__file__).resolve().parent / "resources" / "gltf"


class TestFormatMtoonxt(unittest.TestCase):
    def test_retired_material_fixture_is_ignored(self) -> None:
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
        self.assertIsNone(iris.stencil)
        self.assertIsNone(iris.outline_stencil)
        self.assertIsNone(white.stencil)

    def test_read_ignores_retired_gltf_key(self) -> None:
        extra = read_mtoonxt_from_material(
            {
                "name": "Face",
                "extensions": {
                    "VRMC_materials_mtoon": {"specVersion": "1.0"},
                    "VRMC_materials_mtoonxt": {
                        "specVersion": "1.0",
                        "stencil": {"op": "write"},
                    },
                },
            },
            own_index=0,
            material_count=1,
        )
        self.assertIsNone(extra)

    def test_retired_inside_overlay_is_ignored(self) -> None:
        parsed = parse_mtoonxt(
            {
                "specVersion": "1.0",
                "stencil": {"op": "insideOverlay", "materials": [0]},
                "outlineStencil": {"op": "same"},
            },
            own_index=1,
            material_count=2,
        )
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertIsNone(parsed.stencil)
        self.assertIsNone(parsed.outline_stencil)

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
        self.assertIsNone(parsed.outline_stencil)

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
        extra = VrmxtMaterialsMtoonxt(
            stencil=MtoonxtStencil(op=OP_INSIDE, materials=[3]),
            outline_stencil=MtoonxtStencil(op=OP_SAME),
        )
        payload = serialize_mtoonxt(extra)
        parsed = parse_mtoonxt(payload, own_index=1, material_count=4)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(serialize_mtoonxt(extra), serialize_mtoonxt(parsed))

    def test_serializer_omits_retired_material_ops(self) -> None:
        extra = VrmxtMaterialsMtoonxt(
            stencil=MtoonxtStencil(op=OP_INSIDE_OVERLAY, materials=[0]),
            outline_stencil=MtoonxtStencil(op=OP_SAME),
        )
        payload = serialize_mtoonxt(extra)
        self.assertNotIn("stencil", payload)
        self.assertNotIn("outlineStencil", payload)
        parsed = parse_mtoonxt(payload, own_index=1, material_count=2)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(serialize_mtoonxt(extra), serialize_mtoonxt(parsed))

    def test_listed_writers_require_body_write(self) -> None:
        extras: list[VrmxtMaterialsMtoonxt | None] = [None, None]
        extras[0] = VrmxtMaterialsMtoonxt(
            stencil=MtoonxtStencil(op=OP_INSIDE, materials=[1])
        )
        extras[1] = VrmxtMaterialsMtoonxt(stencil=MtoonxtStencil(op=OP_WRITE))
        assert extras[0] is not None
        self.assertTrue(listed_writers_have_body_write(extras[0].stencil, extras))
        extras[1] = VrmxtMaterialsMtoonxt()
        self.assertFalse(listed_writers_have_body_write(extras[0].stencil, extras))

    def test_drop_outline_same_without_body(self) -> None:
        extra = VrmxtMaterialsMtoonxt(
            stencil=None,
            outline_stencil=MtoonxtStencil(op=OP_SAME),
        )
        drop_unresolvable_stencils(extra, [extra])
        self.assertIsNone(extra.stencil)
        self.assertIsNone(extra.outline_stencil)

    def test_drop_outline_same_after_invalid_body_clip(self) -> None:
        extras: list[VrmxtMaterialsMtoonxt | None] = [None, None]
        extras[0] = VrmxtMaterialsMtoonxt(
            stencil=MtoonxtStencil(op=OP_INSIDE, materials=[1]),
            outline_stencil=MtoonxtStencil(op=OP_SAME),
        )
        extras[1] = VrmxtMaterialsMtoonxt()
        assert extras[0] is not None
        drop_unresolvable_stencils(extras[0], extras)
        self.assertIsNone(extras[0].stencil)
        self.assertIsNone(extras[0].outline_stencil)

    def test_keep_outline_same_with_body_write(self) -> None:
        extra = VrmxtMaterialsMtoonxt(
            stencil=MtoonxtStencil(op=OP_WRITE),
            outline_stencil=MtoonxtStencil(op=OP_SAME),
        )
        drop_unresolvable_stencils(extra, [extra])
        assert extra.stencil is not None
        assert extra.outline_stencil is not None
        self.assertEqual(extra.stencil.op, OP_WRITE)
        self.assertEqual(extra.outline_stencil.op, OP_SAME)

    def test_retired_root_name_is_not_an_alias(self) -> None:
        document = {
            "extensions": {
                "VRMXT_materials_mtoonxt": {
                    "specVersion": "1.0",
                    "stencilRelationships": [{"writers": [0], "readers": [1]}],
                }
            }
        }
        self.assertEqual(parse_stencil_relationships(document, material_count=2), [])

    def test_root_relationship_round_trip_and_defaults(self) -> None:
        document = {"materials": [{}, {}]}
        relationship = MtoonxtStencilRelationship(
            writers=[1],
            readers=[0],
            show_writers_through_occluders=True,
            writers_self_occlude=False,
            writers_write_color=False,
            writers_write_depth=False,
            writer_depth_test=DEPTH_ALWAYS,
        )
        write_stencil_relationships(document, [relationship])
        payload = document["extensions"][EXTENSION_MATERIALS_MTOONXT]
        self.assertFalse(payload["stencil"][0]["writersWriteColor"])
        self.assertNotIn("readersWriteDepth", payload["stencil"][0])
        parsed = parse_stencil_relationships(document, material_count=2)
        self.assertEqual(parsed, [relationship])
        self.assertIn(EXTENSION_MATERIALS_MTOONXT, document["extensionsUsed"])

        write_stencil_relationships(document, [relationship, relationship])
        payload = document["extensions"][EXTENSION_MATERIALS_MTOONXT]
        self.assertEqual(len(payload["stencil"]), 1)

    def test_equivalent_writer_relationships_coalesce_readers(self) -> None:
        relationships = coalesce_stencil_relationships(
            [
                MtoonxtStencilRelationship(
                    writers=[0], readers=[1], writers_write_color=False
                ),
                MtoonxtStencilRelationship(
                    writers=[0], readers=[2], writers_write_color=False
                ),
            ]
        )
        self.assertEqual(len(relationships), 1)
        self.assertEqual(relationships[0].writers, [0])
        self.assertEqual(relationships[0].readers, [1, 2])
        self.assertFalse(relationships[0].writers_write_color)

    def test_root_relationship_skips_invalid_entries_individually(self) -> None:
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
        parsed = parse_stencil_relationships(document, material_count=3)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].writers, [0])
        self.assertEqual(parsed[0].readers, [1])


class TestMtoonxtHooks(unittest.TestCase):
    def test_external_provider_overrides_standalone_body(self) -> None:
        settings = _FakeSettings()
        settings.body_op = OP_WRITE
        material = _Mat("Face", settings)

        def provider(_material, _name_to_index, _own_index):
            return VrmxtMaterialsMtoonxt(
                stencil=MtoonxtStencil(op=OP_INSIDE, materials=[1])
            )

        register_external_export_provider(provider)
        try:
            extra = extra_from_blender_material(
                material,
                {"Face": 0, "Mask": 1},
                0,
            )
        finally:
            unregister_external_export_provider(provider)
        self.assertIsNotNone(extra)
        assert extra is not None and extra.stencil is not None
        self.assertEqual(extra.stencil.op, OP_INSIDE)
        self.assertEqual(extra.stencil.materials, [1])

    def test_import_ignores_retired_material_writer_pointers(self) -> None:
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
        self.assertEqual(iris.vrmxt_mtoonxt_settings.body_op, "OFF")
        self.assertEqual(list(iris.vrmxt_mtoonxt_settings.body_targets), [])
        self.assertEqual(white.vrmxt_mtoonxt_settings.body_op, "OFF")

    def test_import_ignores_retired_material_inside_overlay(self) -> None:
        bone = SimpleNamespace(vrmxt_mtoonxt_settings=_FakeSettings())
        suit = SimpleNamespace(vrmxt_mtoonxt_settings=_FakeSettings())
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
            material_index_to_material={0: suit, 1: bone},
        )
        apply_mtoonxt_import(context)
        self.assertEqual(bone.vrmxt_mtoonxt_settings.body_op, "OFF")
        self.assertEqual(list(bone.vrmxt_mtoonxt_settings.body_targets), [])
        self.assertEqual(bone.vrmxt_mtoonxt_settings.outline_op, "OFF")

    def test_external_root_relationship_export_and_import(self) -> None:
        import io_scene_vrmxt.mtoonxt.export_hook as export_hook
        import io_scene_vrmxt.mtoonxt.import_hook as import_hook

        relationship = MtoonxtStencilRelationship(
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
            return [relationship]

        received: list[MtoonxtStencilRelationship] = []

        def consumer(_context, values):
            received.extend(values)

        export_hook.register_external_relationship_export_provider(provider)
        import_hook.register_external_relationship_import_consumer(consumer)
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
            export_hook.unregister_external_relationship_export_provider(provider)
            import_hook.unregister_external_relationship_import_consumer(consumer)
        self.assertEqual(received, [relationship])

    def test_authoritative_relationship_graph_ignores_material_settings(self) -> None:
        import io_scene_vrmxt.mtoonxt.export_hook as export_hook

        writer_settings = _FakeSettings()
        writer_settings.body_op = OP_WRITE
        reader_settings = _FakeSettings()
        reader_settings.body_op = OP_INSIDE
        writer = _Mat("Writer", writer_settings)
        reader = _Mat("Reader", reader_settings)
        reader_settings.body_targets = [writer]

        stale_writer_settings = _FakeSettings()
        stale_writer_settings.body_op = OP_WRITE
        stale_reader_settings = _FakeSettings()
        stale_reader_settings.body_op = OP_INSIDE
        stale_writer = _Mat("Stale Writer", stale_writer_settings)
        stale_reader = _Mat("Stale Reader", stale_reader_settings)
        stale_reader_settings.body_targets = [stale_writer]

        materials = [
            {
                "name": material.name,
                "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
            }
            for material in (writer, reader, stale_writer, stale_reader)
        ]
        relationship = MtoonxtStencilRelationship(writers=[0], readers=[1])
        context = SimpleNamespace(
            json_dict={"materials": materials},
            material_name_to_index={
                material.name: index
                for index, material in enumerate(
                    (writer, reader, stale_writer, stale_reader)
                )
            },
            material_index_to_material={
                index: material
                for index, material in enumerate(
                    (writer, reader, stale_writer, stale_reader)
                )
            },
            mtoonxt_relationship_graph_authoritative=True,
        )

        def provider(_context, _indices):
            return [relationship]

        export_hook.register_external_relationship_export_provider(provider)
        try:
            export_hook.apply_mtoonxt_export(context)
        finally:
            export_hook.unregister_external_relationship_export_provider(provider)

        self.assertEqual(
            parse_stencil_relationships(context.json_dict, material_count=4),
            [relationship],
        )
        for material in materials:
            self.assertNotIn(EXTENSION_MATERIALS_MTOONXT, material["extensions"])

    def test_export_ignores_legacy_material_authoring(self) -> None:
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
        self.assertNotIn(EXTENSION_MATERIALS_MTOONXT, with_mtoon["extensions"])

    def test_export_does_not_emit_legacy_inside_overlay(self) -> None:
        suit_settings = _FakeSettings()
        suit_settings.body_op = OP_WRITE
        bone_settings = _FakeSettings()
        bone_settings.body_op = OP_INSIDE_OVERLAY
        bone_settings.outline_op = OP_SAME
        bone_settings.body_targets = [_Mat("Swimsuit", suit_settings)]
        bone = _Mat("Skeleton", bone_settings)
        suit = _Mat("Swimsuit", suit_settings)
        bone_dict = {
            "name": "Skeleton",
            "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
        }
        suit_dict = {
            "name": "Swimsuit",
            "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
        }
        json_dict = {"materials": [suit_dict, bone_dict]}
        context = SimpleNamespace(
            json_dict=json_dict,
            material_name_to_index={"Swimsuit": 0, "Skeleton": 1},
        )
        import io_scene_vrmxt.mtoonxt.export_hook as export_hook

        original = export_hook._find_material_by_name
        mapping = {"Skeleton": bone, "Swimsuit": suit}

        def _find(name: str) -> object | None:
            return mapping.get(name)

        export_hook._find_material_by_name = _find  # type: ignore[assignment]
        try:
            apply_mtoonxt_export(context)
        finally:
            export_hook._find_material_by_name = original  # type: ignore[assignment]

        self.assertNotIn(EXTENSION_MATERIALS_MTOONXT, bone_dict["extensions"])

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

    def test_export_skips_outline_same_when_body_is_off(self) -> None:
        settings = _FakeSettings()
        settings.outline_op = OP_SAME
        material = _Mat("Skin", settings)
        material_dict = {
            "name": "Skin",
            "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
        }
        json_dict = {"materials": [material_dict]}
        context = SimpleNamespace(
            json_dict=json_dict,
            material_name_to_index={"Skin": 0},
        )
        import io_scene_vrmxt.mtoonxt.export_hook as export_hook

        original = export_hook._find_material_by_name

        def _find(name: str) -> object | None:
            return material if name == "Skin" else None

        export_hook._find_material_by_name = _find  # type: ignore[assignment]
        try:
            apply_mtoonxt_export(context)
        finally:
            export_hook._find_material_by_name = original  # type: ignore[assignment]

        self.assertNotIn(
            EXTENSION_MATERIALS_MTOONXT,
            material_dict.get("extensions", {}),
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
