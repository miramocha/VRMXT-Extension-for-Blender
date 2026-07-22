# SPDX-License-Identifier: MIT
"""Tests for materials-override texture import bind + export remap."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from io_scene_vrmxt.materials_override.export_hook import (
    _remap_texture_properties_for_export,
)
from io_scene_vrmxt.materials_override.import_hook import bind_override_texture_images


class TestBindOverrideTextureImages(unittest.TestCase):
    def test_binds_image_from_texture_index(self) -> None:
        image = object()
        item = SimpleNamespace(
            prop_type="texture",
            texture_index=0,
            image=None,
        )
        slot = SimpleNamespace(properties=[item])
        settings = SimpleNamespace(authored=True, overrides=[slot])
        material = SimpleNamespace(vrmxt_materials_override_settings=settings)

        bound = bind_override_texture_images(
            material,
            {"textures": [{"source": 3}]},
            {3: image},
        )
        self.assertEqual(bound, 1)
        self.assertIs(item.image, image)

    def test_skips_when_image_already_set(self) -> None:
        existing = object()
        item = SimpleNamespace(
            prop_type="texture",
            texture_index=0,
            image=existing,
        )
        slot = SimpleNamespace(properties=[item])
        settings = SimpleNamespace(authored=True, overrides=[slot])
        material = SimpleNamespace(vrmxt_materials_override_settings=settings)

        bound = bind_override_texture_images(
            material,
            {"textures": [{"source": 3}]},
            {3: object()},
        )
        self.assertEqual(bound, 0)
        self.assertIs(item.image, existing)


class TestRemapTexturePropertiesForExport(unittest.TestCase):
    def test_packs_image_and_rewrites_index(self) -> None:
        image = SimpleNamespace(name="VrmxtTestTexture")
        item = SimpleNamespace(image=image, prop_type="texture", name="_MainTex")
        slot = SimpleNamespace(properties=[item])
        settings = SimpleNamespace(authored=True, overrides=[slot])
        material = SimpleNamespace(
            name="Hair",
            vrmxt_materials_override_settings=settings,
        )
        override_dict = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": "unity",
                    "material": {"idType": "shaderName", "id": "lilToon"},
                    "properties": [
                        {"name": "_MainTex", "type": "texture", "texture": 24},
                        {"name": "_UseGlitter", "type": "scalar", "value": 1.0},
                    ],
                }
            ],
        }
        json_dict: dict = {"textures": [], "images": [], "samplers": []}
        context = SimpleNamespace(
            json_dict=json_dict,
            buffer0=bytearray(),
            image_name_to_index={},
        )

        with mock.patch(
            "io_scene_vrmxt.materials_override.export_hook.ensure_vfx_texture_index",
            return_value=0,
        ) as ensure:
            result = _remap_texture_properties_for_export(
                material, override_dict, context
            )

        ensure.assert_called_once()
        props = result["overrides"][0]["properties"]  # type: ignore[index]
        self.assertEqual(
            props,
            [
                {"name": "_MainTex", "type": "texture", "texture": 0},
                {"name": "_UseGlitter", "type": "scalar", "value": 1.0},
            ],
        )

    def test_drops_stale_texture_without_image(self) -> None:
        item = SimpleNamespace(image=None, prop_type="texture", name="_MainTex")
        slot = SimpleNamespace(properties=[item])
        settings = SimpleNamespace(authored=True, overrides=[slot])
        material = SimpleNamespace(
            name="Hair",
            vrmxt_materials_override_settings=settings,
        )
        override_dict = {
            "specVersion": "1.0",
            "overrides": [
                {
                    "engine": "unity",
                    "material": {"idType": "shaderName", "id": "lilToon"},
                    "properties": [
                        {"name": "_MainTex", "type": "texture", "texture": 24},
                        {"name": "_Color", "type": "vector", "value": [1, 0, 0, 1]},
                    ],
                }
            ],
        }
        context = SimpleNamespace(
            json_dict={"textures": []},
            buffer0=bytearray(),
            image_name_to_index={},
        )

        result = _remap_texture_properties_for_export(material, override_dict, context)
        props = result["overrides"][0]["properties"]  # type: ignore[index]
        self.assertEqual(
            props,
            [{"name": "_Color", "type": "vector", "value": [1, 0, 0, 1]}],
        )


if __name__ == "__main__":
    unittest.main()
