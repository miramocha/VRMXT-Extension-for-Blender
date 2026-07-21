# SPDX-License-Identifier: MIT
"""Tests for VRMXT_sprite_particle format parsing and serialization."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from io_scene_vrmxt.common.constants import (
    EXTENSION_VRMXT_SPRITE_PARTICLE,
    SPEC_VERSION_1_0,
)
from io_scene_vrmxt.format.vfx import (
    DEFAULT_EMISSION_RATE,
    DEFAULT_MAX_PARTICLES,
    DEFAULT_SIZE,
    VrmxtVfx,
    VrmxtVfxEmitter,
    parse_vfx,
    read_vfx_from_gltf,
    serialize_vfx,
    write_vfx_to_gltf,
)

RESOURCES = Path(__file__).resolve().parent / "resources" / "gltf"


class TestFormatVfx(unittest.TestCase):
    def test_parse_minimal_fixture(self) -> None:
        payload = json.loads(
            (RESOURCES / "vfx_minimal.json").read_text(encoding="utf-8")
        )
        extension = payload["extensions"][EXTENSION_VRMXT_SPRITE_PARTICLE]
        vfx = parse_vfx(extension, node_count=3)
        self.assertIsNotNone(vfx)
        assert vfx is not None
        self.assertEqual(vfx.spec_version, SPEC_VERSION_1_0)
        self.assertEqual(len(vfx.emitters), 1)
        emitter = vfx.emitters[0]
        self.assertEqual(emitter.name, "HandSpark")
        self.assertEqual(emitter.node, 1)
        self.assertEqual(emitter.emission_rate, 20.0)
        self.assertEqual(emitter.max_particles, 32)
        self.assertEqual(emitter.size, (0.04, 0.04))
        self.assertEqual(emitter.color, (1.0, 0.85, 0.4, 1.0))
        self.assertNotIn("type", extension["emitters"][0])
        self.assertNotIn("particle", extension["emitters"][0])
        self.assertNotIn("localPosition", extension["emitters"][0])

    def test_parse_applies_defaults(self) -> None:
        extension = {
            "specVersion": "1.0",
            "emitters": [
                {
                    "node": 0,
                }
            ],
        }
        vfx = parse_vfx(extension, node_count=1)
        self.assertIsNotNone(vfx)
        assert vfx is not None
        emitter = vfx.emitters[0]
        self.assertEqual(emitter.emission_rate, DEFAULT_EMISSION_RATE)
        self.assertEqual(emitter.max_particles, DEFAULT_MAX_PARTICLES)
        self.assertEqual(emitter.size, DEFAULT_SIZE)

    def test_parse_skips_invalid_emitters(self) -> None:
        extension = {
            "specVersion": "1.0",
            "emitters": [
                {"node": 99, "emissionRate": 1.0},
                {"node": 0, "emissionRate": -1.0},
                {"node": 0, "size": [0.0, 0.05]},
                {"node": 0, "color": [1.0, 1.0, 1.0, 2.0]},
                {"node": 0, "texture": 9},
                {"node": 0, "emissionRate": 5.0},
            ],
        }
        vfx = parse_vfx(extension, node_count=1, texture_count=1)
        self.assertIsNotNone(vfx)
        assert vfx is not None
        self.assertEqual(len(vfx.emitters), 1)
        self.assertEqual(vfx.emitters[0].emission_rate, 5.0)

    def test_parse_rejects_wrong_spec_version(self) -> None:
        extension = {"specVersion": "2.0", "emitters": []}
        self.assertIsNone(parse_vfx(extension))

    def test_read_ignores_legacy_roots(self) -> None:
        for legacy_name in ("VRMXT_vfx", "VRMXT_particle"):
            with self.subTest(root=legacy_name):
                json_dict = {
                    "nodes": [{}],
                    "extensionsUsed": [legacy_name],
                    "extensions": {
                        legacy_name: {
                            "specVersion": "1.0",
                            "emitters": [{"node": 0, "emissionRate": 5.0}],
                        }
                    },
                }
                self.assertIsNone(read_vfx_from_gltf(json_dict, node_count=1))

    def test_serialize_round_trip(self) -> None:
        vfx = VrmxtVfx(
            emitters=[
                VrmxtVfxEmitter(
                    node=2,
                    name="Spark",
                    emission_rate=15.0,
                    size=(0.03, 0.06),
                )
            ]
        )
        serialized = serialize_vfx(vfx)
        self.assertNotIn("type", serialized["emitters"][0])
        self.assertNotIn("particle", serialized["emitters"][0])
        self.assertNotIn("localPosition", serialized["emitters"][0])
        self.assertEqual(serialized["emitters"][0]["size"], [0.03, 0.06])
        parsed = parse_vfx(serialized, node_count=3)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.emitters[0].node, 2)
        self.assertEqual(parsed.emitters[0].emission_rate, 15.0)
        self.assertEqual(parsed.emitters[0].size, (0.03, 0.06))

    def test_write_vfx_to_gltf(self) -> None:
        json_dict: dict[str, object] = {"nodes": [{}, {}]}
        vfx = VrmxtVfx(
            emitters=[
                VrmxtVfxEmitter(
                    node=0,
                )
            ]
        )
        write_vfx_to_gltf(json_dict, vfx)
        self.assertIn(EXTENSION_VRMXT_SPRITE_PARTICLE, json_dict["extensionsUsed"])  # type: ignore[index]
        required = json_dict.get("extensionsRequired")
        if isinstance(required, list):
            self.assertNotIn(EXTENSION_VRMXT_SPRITE_PARTICLE, required)
        self.assertIn(EXTENSION_VRMXT_SPRITE_PARTICLE, json_dict["extensions"])  # type: ignore[index]
        read_back = read_vfx_from_gltf(json_dict, node_count=1)
        self.assertIsNotNone(read_back)
        assert read_back is not None
        self.assertEqual(len(read_back.emitters), 1)


if __name__ == "__main__":
    unittest.main()
