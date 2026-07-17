# SPDX-License-Identifier: MIT
"""Tests for VRM 1.0 hook registration against a mocked extension_hooks module."""

from __future__ import annotations

import sys
import types
import unittest
from unittest import mock

from io_scene_vrmxt.hooks import vrm1_hooks
from io_scene_vrmxt.vfx.export_hook import on_vrm1_export as on_vfx_export_hook
from io_scene_vrmxt.vfx.import_hook import on_vrm1_import as on_vfx_import_hook


class _FakeExtensionHooksModule(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("io_scene_vrm.extension_hooks")
        self.import_hooks: list[object] = []
        self.export_hooks: list[object] = []

    def register_vrm1_import_extension_hook(self, hook: object) -> None:
        if hook not in self.import_hooks:
            self.import_hooks.append(hook)

    def unregister_vrm1_import_extension_hook(self, hook: object) -> None:
        try:
            self.import_hooks.remove(hook)
        except ValueError:
            return

    def register_vrm1_export_extension_hook(self, hook: object) -> None:
        if hook not in self.export_hooks:
            self.export_hooks.append(hook)

    def unregister_vrm1_export_extension_hook(self, hook: object) -> None:
        try:
            self.export_hooks.remove(hook)
        except ValueError:
            return


class TestHooksRegistration(unittest.TestCase):
    def setUp(self) -> None:
        self._original_module = sys.modules.get("io_scene_vrm.extension_hooks")
        vrm1_hooks._EXTENSION_HOOKS_MODULE = None
        vrm1_hooks._HOOKS_AVAILABLE = False

    def tearDown(self) -> None:
        if self._original_module is None:
            sys.modules.pop("io_scene_vrm.extension_hooks", None)
        else:
            sys.modules["io_scene_vrm.extension_hooks"] = self._original_module
        vrm1_hooks._EXTENSION_HOOKS_MODULE = None
        vrm1_hooks._HOOKS_AVAILABLE = False

    def test_register_and_unregister_with_mock_module(self) -> None:
        fake_module = _FakeExtensionHooksModule()
        sys.modules["io_scene_vrm.extension_hooks"] = fake_module

        vrm1_hooks.register()
        self.assertTrue(vrm1_hooks.hooks_available())
        self.assertEqual(len(fake_module.import_hooks), 1)
        self.assertEqual(len(fake_module.export_hooks), 1)

        vrm1_hooks.unregister()
        self.assertEqual(fake_module.import_hooks, [])
        self.assertEqual(fake_module.export_hooks, [])

    def test_import_hook_swallows_exceptions(self) -> None:
        context = mock.Mock()
        context.json_dict = {
            "extensions": {"VRMXT_vfx": {"specVersion": "1.0", "emitters": []}}
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

    def test_combined_import_hook_calls_both_adapters(self) -> None:
        context = mock.Mock()
        with (
            mock.patch("io_scene_vrmxt.hooks.vrm1_hooks.on_vfx_import") as vfx_import,
            mock.patch(
                "io_scene_vrmxt.hooks.vrm1_hooks.on_materials_import"
            ) as materials_import,
        ):
            vrm1_hooks._on_vrm1_import(context)
            vfx_import.assert_called_once_with(context)
            materials_import.assert_called_once_with(context)


if __name__ == "__main__":
    unittest.main()
