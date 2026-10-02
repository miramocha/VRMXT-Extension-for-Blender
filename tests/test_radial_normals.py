# SPDX-License-Identifier: MIT
"""Buffer rewrite tests for VRM 1 radial morph normals."""

from __future__ import annotations

import struct
import unittest

from io_scene_vrmxt.radial_normals.gltf_normals import (
    append_vec3_accessor,
    choose_by_morph_delta,
    read_vec3_accessor,
    rewrite_primitive_normals,
    yup_to_zup,
    zup_to_yup,
)


def _empty_gltf(buffer: bytearray) -> dict:
    return {
        "buffers": [{"byteLength": len(buffer)}],
        "bufferViews": [],
        "accessors": [],
    }


class TestAxisSwap(unittest.TestCase):
    def test_yup_round_trip(self) -> None:
        original = (0.2, -0.4, 0.8)
        self.assertEqual(yup_to_zup(*zup_to_yup(*original)), original)


class TestMorphDisambiguation(unittest.TestCase):
    def test_picks_vertex_whose_delta_matches(self) -> None:
        gltf_deltas = [None, (0.0, 1.0, 0.0)]
        blender_deltas = [
            {0: (0.0, 0.0, 0.0), 1: (0.0, 0.0, 0.0)},
            {0: (1.0, 0.0, 0.0), 1: (0.0, 1.0, 0.0)},
        ]
        self.assertEqual(
            choose_by_morph_delta([0, 1], gltf_deltas, blender_deltas),
            1,
        )


class TestRewriteNormals(unittest.TestCase):
    def test_appends_basis_and_zero_delta_for_unmoved_vertex(self) -> None:
        buffer = bytearray(b"\xff")
        gltf = _empty_gltf(buffer)
        base_index = append_vec3_accessor(
            gltf, buffer, [(0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
        )
        position_index = append_vec3_accessor(
            gltf, buffer, [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
        )
        primitive = {
            "attributes": {"POSITION": position_index, "NORMAL": base_index},
            "targets": [{"POSITION": position_index}],
        }
        rewritten = rewrite_primitive_normals(
            gltf,
            buffer,
            primitive,
            [0, 1],
            {0},
            {0: (1.0, 0.0, 0.0)},
            [{0: (1.0, 0.0, 0.5)}],
        )
        self.assertEqual(rewritten, 1)
        self.assertEqual(gltf["buffers"][0]["byteLength"], len(buffer))
        self.assertEqual(len(buffer) % 4, 0)

        base = read_vec3_accessor(gltf, buffer, primitive["attributes"]["NORMAL"])
        morph = read_vec3_accessor(gltf, buffer, primitive["targets"][0]["NORMAL"])
        assert base is not None and morph is not None
        self.assertEqual(base[0], (1.0, 0.0, 0.0))
        self.assertEqual(base[1], (0.0, 0.0, 1.0))
        self.assertEqual(morph[0], (0.0, 0.0, 0.5))
        self.assertEqual(morph[1], (0.0, 0.0, 0.0))

    def test_sparse_base_normal_is_kept_for_other_vertices(self) -> None:
        buffer = bytearray()
        gltf = _empty_gltf(buffer)
        values = append_vec3_accessor(gltf, buffer, [(0.0, 0.0, 1.0)])
        indices = _append_bytes(gltf, buffer, struct.pack("<I", 1))
        gltf["accessors"].append(
            {
                "componentType": 5126,
                "count": 2,
                "type": "VEC3",
                "sparse": {
                    "count": 1,
                    "indices": {"bufferView": indices, "componentType": 5125},
                    "values": {"bufferView": values},
                },
            }
        )
        sparse_index = len(gltf["accessors"]) - 1
        primitive = {
            "attributes": {"NORMAL": sparse_index},
            "targets": [{}],
        }
        rewrite_primitive_normals(
            gltf,
            buffer,
            primitive,
            [0, None],
            {0},
            {0: (0.0, 1.0, 0.0)},
            [{}],
        )
        base = read_vec3_accessor(gltf, buffer, primitive["attributes"]["NORMAL"])
        morph = read_vec3_accessor(gltf, buffer, primitive["targets"][0]["NORMAL"])
        assert base is not None and morph is not None
        self.assertEqual(base[0], (0.0, 1.0, 0.0))
        self.assertEqual(base[1], (0.0, 0.0, 1.0))
        self.assertEqual(morph, [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)])

    def test_skips_targets_without_a_sampled_shape_key(self) -> None:
        buffer = bytearray()
        gltf = _empty_gltf(buffer)
        normal_index = append_vec3_accessor(gltf, buffer, [(0.0, 0.0, 1.0)])
        primitive = {
            "attributes": {"NORMAL": normal_index},
            "targets": [{"POSITION": normal_index}],
        }
        rewrite_primitive_normals(
            gltf,
            buffer,
            primitive,
            [7],
            {7},
            {7: (1.0, 0.0, 0.0)},
            [],
        )
        self.assertNotIn("NORMAL", primitive["targets"][0])


def _append_bytes(gltf: dict, buffer: bytearray, blob: bytes) -> int:
    while len(buffer) % 4:
        buffer.append(0)
    offset = len(buffer)
    buffer.extend(blob)
    gltf["bufferViews"].append(
        {"buffer": 0, "byteOffset": offset, "byteLength": len(blob)}
    )
    return len(gltf["bufferViews"]) - 1


if __name__ == "__main__":
    unittest.main()
