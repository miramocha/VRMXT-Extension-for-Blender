# SPDX-License-Identifier: MIT
"""Tests for stock VRM 4.6.0 user-extension dispatch and map invert."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from io_scene_vrmxt.hooks import vrm1_hooks
from io_scene_vrmxt.hooks.shim import invert_name_to_index, make_export_context
from io_scene_vrmxt.hooks.vrm1_hooks import (
    Vrm1ExportUserExtension,
    Vrm1ImportUserExtension,
)
from io_scene_vrmxt.vfx.export_hook import on_vrm1_export as on_vfx_export_hook
from io_scene_vrmxt.vfx.import_hook import on_vrm1_import as on_vfx_import_hook


class TestMapInvert(unittest.TestCase):
    def test_invert_name_to_index(self) -> None:
        bone_l = SimpleNamespace(name="Hand_L")
        bone_r = SimpleNamespace(name="Hand_R")
        self.assertEqual(
            invert_name_to_index({2: bone_l, 5: bone_r}),
            {"Hand_L": 2, "Hand_R": 5},
        )

    def test_export_context_builds_mutable_image_map(self) -> None:
        image = SimpleNamespace(name="Spark")
        ctx = make_export_context(
            json_chunk={"materials": []},
            bin_chunk=bytearray(b"\x00"),
            armature=SimpleNamespace(),
            node_index_to_object={},
            node_index_to_bone={0: SimpleNamespace(name="hips")},
            image_index_to_image={3: image},
            material_index_to_material={1: SimpleNamespace(name="Face")},
        )
        self.assertEqual(ctx.bone_name_to_node_index, {"hips": 0})
        self.assertEqual(ctx.material_name_to_index, {"Face": 1})
        self.assertEqual(ctx.image_name_to_index, {"Spark": 3})
        ctx.image_name_to_index["Spark2"] = 4
        self.assertEqual(ctx.buffer0, bytearray(b"\x00"))


class TestUserExtensionDispatch(unittest.TestCase):
    def test_import_hook_swallows_exceptions(self) -> None:
        context = mock.Mock()
        context.json_dict = {
            "extensions": {
                "VRMXT_sprite_particle": {
                    "specVersion": "1.0",
                    "emitters": [],
                }
            }
        }
        context.armature = mock.Mock()
        context.armature.data = mock.Mock(spec=[])
        context.node_index_to_bone_name = {}
        context.node_index_to_object_name = {}

        with mock.patch(
            "io_scene_vrmxt.vfx.import_hook.apply_vfx_import",
            side_effect=RuntimeError("boom"),
        ):
            on_vfx_import_hook(context)

    def test_export_hook_swallows_exceptions(self) -> None:
        context = mock.Mock()
        context.armature = mock.Mock()
        context.armature.data = mock.Mock(spec=[])

        with mock.patch(
            "io_scene_vrmxt.vfx.export_hook.apply_vfx_export",
            side_effect=RuntimeError("boom"),
        ):
            on_vfx_export_hook(context)

    def test_combined_import_hook_calls_all_adapters(self) -> None:
        context = mock.Mock()
        with (
            mock.patch("io_scene_vrmxt.hooks.vrm1_hooks.on_vfx_import") as vfx_import,
            mock.patch(
                "io_scene_vrmxt.hooks.vrm1_hooks.on_materials_import"
            ) as materials_import,
            mock.patch(
                "io_scene_vrmxt.hooks.vrm1_hooks.on_mtoonxt_import"
            ) as mtoonxt_import,
        ):
            vrm1_hooks._on_vrm1_import(context)
            vfx_import.assert_called_once_with(context)
            materials_import.assert_called_once_with(context)
            mtoonxt_import.assert_called_once_with(context)

    def test_post_import_hook_builds_shim_and_dispatches(self) -> None:
        armature = SimpleNamespace(name="Armature")
        bone = SimpleNamespace(name="hips")
        obj = SimpleNamespace(name="Mesh")
        image = SimpleNamespace(name="Tex")
        material = SimpleNamespace(name="Skin")
        json_chunk = {"extensions": {}}
        with mock.patch("io_scene_vrmxt.hooks.vrm1_hooks._on_vrm1_import") as dispatch:
            Vrm1ImportUserExtension().post_import_hook(
                json_chunk,
                b"",
                armature,
                {1: obj},
                {0: bone},
                {2: image},
                {3: material},
                {},
            )
            dispatch.assert_called_once()
            ctx = dispatch.call_args[0][0]
            self.assertEqual(ctx.armature, armature)
            self.assertEqual(ctx.json_dict, json_chunk)
            self.assertEqual(ctx.node_index_to_bone_name, {0: "hips"})
            self.assertEqual(ctx.node_index_to_object_name, {1: "Mesh"})
            self.assertEqual(ctx.material_index_to_material[3], material)

    def test_pre_save_hook_builds_export_shim(self) -> None:
        json_chunk: dict = {"materials": []}
        buffer0 = bytearray(b"ab")
        scene = SimpleNamespace(name="Scene")
        armature = SimpleNamespace(name="Armature", users_scene=(scene,))
        material = SimpleNamespace(name="Mat")
        mesh = SimpleNamespace(name="Mesh")
        with (
            mock.patch("io_scene_vrmxt.hooks.vrm1_hooks._on_vrm1_export") as dispatch,
            mock.patch(
                "io_scene_vrmxt.hooks.vrm1_hooks.sync_bvt_scene_to_vrmxt",
                return_value=True,
            ) as sync_bvt,
        ):
            Vrm1ExportUserExtension().pre_save_hook(
                json_chunk,
                buffer0,
                armature,
                {4: SimpleNamespace(name="Empty")},
                {1: SimpleNamespace(name="spine")},
                {0: SimpleNamespace(name="A")},
                {2: material},
                {3: mesh},
            )
            ctx = dispatch.call_args[0][0]
            sync_bvt.assert_called_once_with(scene)
            self.assertIs(ctx.json_dict, json_chunk)
            self.assertIs(ctx.buffer0, buffer0)
            self.assertIs(ctx.scene, scene)
            self.assertTrue(ctx.mtoonxt_relationship_graph_authoritative)
            self.assertEqual(ctx.object_name_to_node_index, {"Empty": 4})
            self.assertEqual(ctx.bone_name_to_node_index, {"spine": 1})
            self.assertIs(ctx.material_index_to_material[2], material)
            self.assertEqual(ctx.mesh_name_to_index, {"Mesh": 3})


if __name__ == "__main__":
    unittest.main()
