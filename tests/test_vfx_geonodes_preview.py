# SPDX-License-Identifier: MIT
"""Unit tests for VRMXT_vfx Geometry Nodes preview helpers."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from io_scene_vrmxt.vfx.export_hook import resolve_node_index
from io_scene_vrmxt.vfx.geonodes_preview import (
    ARMATURE_PREVIEW_ID_PROP,
    OBJECT_NAME_PREFIX,
    PREVIEW_ARMATURE_PROP,
    PREVIEW_CUSTOM_PROP,
    _ensure_armature_preview_id,
    _preview_belongs_to_armature,
    clear_vfx_preview,
    is_preview_object,
    preview_object_name,
    rebuild_vfx_preview,
)
from io_scene_vrmxt.vfx.property_group import ATTACHMENT_TYPE_OBJECT


class TestVfxPreviewNaming(unittest.TestCase):
    def test_preview_object_name_sanitizes(self) -> None:
        self.assertEqual(
            preview_object_name("Hand Spark!", 0),
            "VRMXT_vfx_Hand_Spark.000",
        )
        self.assertEqual(
            preview_object_name("", 2),
            f"{OBJECT_NAME_PREFIX}Emitter.002",
        )
        # Same label, different indices → distinct object names.
        self.assertNotEqual(
            preview_object_name("Spark", 0),
            preview_object_name("Spark", 1),
        )

    def test_is_preview_object_reads_custom_prop(self) -> None:
        tagged = SimpleNamespace(
            get=lambda key, default=None: (
                1 if key == PREVIEW_CUSTOM_PROP else default
            )
        )
        plain = SimpleNamespace(get=lambda key, default=None: default)
        self.assertTrue(is_preview_object(tagged))
        self.assertFalse(is_preview_object(plain))
        self.assertFalse(is_preview_object(None))


class TestVfxPreviewOwnership(unittest.TestCase):
    def test_preview_belongs_to_armature_matches_uuid_and_legacy_name(self) -> None:
        armature = SimpleNamespace(
            name="Arm.001",
            get=lambda key, default=None: (
                "uuid-arm" if key == ARMATURE_PREVIEW_ID_PROP else default
            ),
        )

        def make_helper(owner: str):
            return SimpleNamespace(
                parent=None,
                get=lambda key, default=None: (
                    owner if key == PREVIEW_ARMATURE_PROP else default
                ),
            )

        self.assertTrue(
            _preview_belongs_to_armature(make_helper("uuid-arm"), armature, "uuid-arm")
        )
        self.assertTrue(
            _preview_belongs_to_armature(make_helper("Arm.001"), armature, "uuid-arm")
        )
        self.assertFalse(
            _preview_belongs_to_armature(make_helper("other"), armature, "uuid-arm")
        )

    def test_ensure_armature_preview_id_falls_back_to_name_when_store_fails(
        self,
    ) -> None:
        class _Arm:
            name = "Arm.001"

            def get(self, key, default=None):
                return default

            def __setitem__(self, key, value):
                raise TypeError("read-only")

        arm = _Arm()
        preview_id = _ensure_armature_preview_id(arm)
        self.assertEqual(preview_id, "Arm.001")
        helper = SimpleNamespace(
            parent=None,
            get=lambda key, default=None: (
                preview_id if key == PREVIEW_ARMATURE_PROP else default
            ),
        )
        self.assertTrue(_preview_belongs_to_armature(helper, arm, preview_id))


class TestVfxPreviewExportIsolation(unittest.TestCase):
    def test_resolve_node_index_rejects_preview_object(self) -> None:
        preview = SimpleNamespace(
            get=lambda key, default=None: (
                1 if key == PREVIEW_CUSTOM_PROP else default
            )
        )
        self.assertIsNone(
            resolve_node_index(
                ATTACHMENT_TYPE_OBJECT,
                "",
                "HandMesh",
                {},
                {"HandMesh": 9},
                attachment_object=preview,
            )
        )

    def test_resolve_node_index_allows_vrmxt_prefixed_scene_object(self) -> None:
        # Name prefix alone must not block a real attachment object.
        self.assertEqual(
            resolve_node_index(
                ATTACHMENT_TYPE_OBJECT,
                "",
                "VRMXT_vfx_Prop",
                {},
                {"VRMXT_vfx_Prop": 9},
            ),
            9,
        )

    def test_resolve_node_index_allows_normal_object(self) -> None:
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


class TestVfxPreviewLifecycleWithoutBpy(unittest.TestCase):
    def test_rebuild_and_clear_noop_without_bpy(self) -> None:
        armature = SimpleNamespace(type="ARMATURE", name="Arm", data=SimpleNamespace())
        self.assertEqual(rebuild_vfx_preview(armature), 0)
        self.assertEqual(clear_vfx_preview(armature), 0)

    def test_apply_vfx_import_calls_preview_rebuild(self) -> None:
        from io_scene_vrmxt.vfx import import_hook

        emitters = mock.Mock()
        item = SimpleNamespace(
            name="",
            attachment_type="",
            attachment_bone="",
            attachment_object=None,
            emitter_type="",
            local_position=None,
            local_rotation=None,
            texture=None,
            emission_rate=0.0,
            max_particles=0,
            lifetime=0.0,
            start_size=0.0,
            start_speed=0.0,
            start_color=None,
        )
        emitters.add.return_value = item
        settings = SimpleNamespace(emitters=emitters)
        armature = SimpleNamespace(
            type="ARMATURE",
            name="Arm",
            data=SimpleNamespace(vrmxt_vfx_settings=settings),
        )
        context = SimpleNamespace(
            json_dict={
                "nodes": [{}, {}, {}],
                "extensions": {
                    "VRMXT_vfx": {
                        "specVersion": "1.0",
                        "emitters": [
                            {
                                "name": "HandSpark",
                                "type": "particle",
                                "node": 2,
                                "particle": {"emissionRate": 20.0},
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

        with mock.patch.object(
            import_hook,
            "_rebuild_preview_after_import",
        ) as rebuild:
            import_hook.apply_vfx_import(context)
            rebuild.assert_called_once_with(armature, context)


if __name__ == "__main__":
    unittest.main()
