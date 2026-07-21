# SPDX-License-Identifier: MIT
"""Unit tests for VFX attachment and texture resolution helpers."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from io_scene_vrmxt.common.constants import EXTENSION_VRMXT_SPRITE_PARTICLE
from io_scene_vrmxt.vfx.export_hook import resolve_node_index
from io_scene_vrmxt.vfx.gltf_texture import find_texture_index_for_image
from io_scene_vrmxt.vfx.import_hook import resolve_attachment, resolve_texture_image
from io_scene_vrmxt.vfx.property_group import (
    ATTACHMENT_TYPE_BONE,
    ATTACHMENT_TYPE_OBJECT,
)


class TestVfxAttachmentResolution(unittest.TestCase):
    def test_resolve_attachment_prefers_bone(self) -> None:
        result = resolve_attachment(
            2,
            {2: "Hand_L"},
            {2: "ShouldNotWin"},
        )
        self.assertEqual(result, (ATTACHMENT_TYPE_BONE, "Hand_L"))

    def test_resolve_attachment_falls_back_to_object(self) -> None:
        result = resolve_attachment(3, {}, {3: "SparkEmpty"})
        self.assertEqual(result, (ATTACHMENT_TYPE_OBJECT, "SparkEmpty"))

    def test_resolve_attachment_unresolved(self) -> None:
        self.assertIsNone(resolve_attachment(9, {}, {}))

    def test_resolve_node_index_bone_and_object(self) -> None:
        self.assertEqual(
            resolve_node_index(
                ATTACHMENT_TYPE_BONE,
                "Hand_L",
                None,
                {"Hand_L": 2},
                {},
            ),
            2,
        )
        self.assertEqual(
            resolve_node_index(
                ATTACHMENT_TYPE_OBJECT,
                "",
                "SparkEmpty",
                {},
                {"SparkEmpty": 4},
            ),
            4,
        )
        self.assertIsNone(resolve_node_index(ATTACHMENT_TYPE_BONE, "", None, {}, {}))


class TestVfxTextureResolution(unittest.TestCase):
    def test_resolve_texture_image_via_source(self) -> None:
        image = object()
        result = resolve_texture_image(
            0,
            {"textures": [{"source": 7}]},
            {7: image},
        )
        self.assertIs(result, image)

    def test_resolve_texture_image_missing(self) -> None:
        self.assertIsNone(resolve_texture_image(None, {}, {}))
        self.assertIsNone(resolve_texture_image(0, {"textures": [{"source": 7}]}, {}))

    def test_resolve_texture_index_finds_existing_entry(self) -> None:
        self.assertEqual(
            find_texture_index_for_image(7, [{"source": 3}, {"source": 7}]),
            1,
        )

    def test_resolve_texture_index_missing_skips(self) -> None:
        self.assertIsNone(find_texture_index_for_image(9, [{"source": 1}]))

    def test_ensure_vfx_texture_index_appends_texture(self) -> None:
        from io_scene_vrmxt.vfx import gltf_texture

        image = SimpleNamespace(name="Spark.png")
        json_dict: dict = {"textures": [], "samplers": [], "images": []}
        buffer0 = bytearray()
        image_name_to_index: dict[str, int] = {}

        def fake_find_or_create(
            json_dict, buffer0, image_name_to_index, image, _settings
        ):
            image_name_to_index[image.name] = 3
            return 3

        with mock.patch.object(
            gltf_texture,
            "_load_image_helpers",
            return_value=(fake_find_or_create, lambda: {}),
        ):
            texture_index = gltf_texture.ensure_vfx_texture_index(
                image=image,
                json_dict=json_dict,
                buffer0=buffer0,
                image_name_to_index=image_name_to_index,
            )

        self.assertEqual(texture_index, 0)
        self.assertEqual(json_dict["textures"][0]["source"], 3)


class TestVfxImportExportAdapters(unittest.TestCase):
    def test_apply_vfx_import_sets_bone_attachment(self) -> None:
        from io_scene_vrmxt.vfx.import_hook import apply_vfx_import

        emitters = mock.Mock()
        item = SimpleNamespace(
            name="",
            attachment_type="",
            attachment_bone="",
            attachment_object=None,
            texture=None,
            size=None,
            color=None,
            emission_rate=0.0,
            max_particles=0,
            lifetime=0.0,
            start_speed=0.0,
        )
        emitters.add.return_value = item
        settings = SimpleNamespace(emitters=emitters)
        armature_data = SimpleNamespace(vrmxt_vfx_settings=settings)
        armature = SimpleNamespace(data=armature_data)

        context = SimpleNamespace(
            json_dict={
                "nodes": [{}, {}, {}],
                "extensions": {
                    EXTENSION_VRMXT_SPRITE_PARTICLE: {
                        "specVersion": "1.0",
                        "emitters": [
                            {
                                "name": "HandSpark",
                                "node": 2,
                                "emissionRate": 20.0,
                                "maxParticles": 32,
                                "size": [0.04, 0.04],
                                "color": [1.0, 0.85, 0.4, 1.0],
                            }
                        ],
                    }
                },
            },
            armature=armature,
            node_index_to_bone_name={2: "Hand_L"},
            node_index_to_object_name={},
            image_index_to_image={},
            context=SimpleNamespace(blend_data=SimpleNamespace(objects={})),
        )

        apply_vfx_import(context)

        emitters.clear.assert_called_once()
        emitters.add.assert_called_once()
        self.assertEqual(item.name, "HandSpark")
        self.assertEqual(item.attachment_type, ATTACHMENT_TYPE_BONE)
        self.assertEqual(item.attachment_bone, "Hand_L")
        self.assertEqual(item.emission_rate, 20.0)
        self.assertEqual(item.max_particles, 32)
        self.assertEqual(item.size, (0.04, 0.04))
        self.assertEqual(item.color, (1.0, 0.85, 0.4, 1.0))

    def test_apply_vfx_export_writes_bone_emitter(self) -> None:
        from io_scene_vrmxt.vfx.export_hook import apply_vfx_export

        item = SimpleNamespace(
            attachment_type=ATTACHMENT_TYPE_BONE,
            attachment_bone="Hand_L",
            attachment_object=None,
            name="HandSpark",
            texture=None,
            emission_rate=20.0,
            max_particles=32,
            lifetime=0.8,
            size=(0.04, 0.04),
            start_speed=0.2,
            color=(1.0, 0.85, 0.4, 1.0),
        )
        settings = SimpleNamespace(emitters=[item])
        armature = SimpleNamespace(data=SimpleNamespace(vrmxt_vfx_settings=settings))
        json_dict: dict = {"extensions": {}}
        context = SimpleNamespace(
            armature=armature,
            json_dict=json_dict,
            buffer0=bytearray(),
            bone_name_to_node_index={"Hand_L": 2},
            object_name_to_node_index={},
            image_name_to_index={},
        )

        apply_vfx_export(context)

        extension = json_dict["extensions"][EXTENSION_VRMXT_SPRITE_PARTICLE]
        self.assertEqual(extension["specVersion"], "1.0")
        self.assertEqual(len(extension["emitters"]), 1)
        emitter = extension["emitters"][0]
        self.assertEqual(emitter["node"], 2)
        self.assertEqual(emitter["name"], "HandSpark")
        self.assertEqual(emitter["size"], [0.04, 0.04])
        self.assertEqual(emitter["color"], [1.0, 0.85, 0.4, 1.0])
        self.assertNotIn("type", emitter)
        self.assertNotIn("particle", emitter)
        self.assertNotIn("localPosition", emitter)
        self.assertNotIn("localRotation", emitter)
        self.assertNotIn("billboard", emitter)


if __name__ == "__main__":
    unittest.main()
