# SPDX-License-Identifier: MIT
"""Tests for JSON views shared with third-party import hooks."""

from __future__ import annotations

import unittest
from types import MappingProxyType

from io_scene_vrmxt.common.json_util import as_dict, as_list


class TestJsonUtil(unittest.TestCase):
    def test_accepts_read_only_official_vrm_import_views(self) -> None:
        mapping = MappingProxyType({"name": "Material"})
        sequence = (mapping,)

        self.assertEqual(as_dict(mapping), {"name": "Material"})
        self.assertEqual(as_list(sequence), [mapping])

    def test_preserves_mutable_export_containers(self) -> None:
        mapping = {"name": "Material"}
        sequence = [mapping]

        self.assertIs(as_dict(mapping), mapping)
        self.assertIs(as_list(sequence), sequence)


if __name__ == "__main__":
    unittest.main()
