# SPDX-License-Identifier: MIT
"""Tests for VRMXT_vfx format parsing and serialization."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from io_scene_vrmxt.common.constants import EXTENSION_VRMXT_VFX, SPEC_VERSION_1_0
from io_scene_vrmxt.format.vfx import (
    DEFAULT_EMISSION_RATE,
    DEFAULT_MAX_PARTICLES,
    ParticleParams,
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
        extension = payload["extensions"][EXTENSION_VRMXT_VFX]
        vfx = parse_vfx(extension, node_count=3)
        self.assertIsNotNone(vfx)
        assert vfx is not None
        self.assertEqual(vfx.spec_version, SPEC_VERSION_1_0)
        self.assertEqual(len(vfx.emitters), 1)
        emitter = vfx.emitters[0]
        self.assertEqual(emitter.name, "HandSpark")
        self.assertEqual(emitter.node, 1)
        self.assertIsNotNone(emitter.particle)
        assert emitter.particle is not None
        self.assertEqual(emitter.particle.emission_rate, 20.0)
        self.assertEqual(emitter.particle.max_particles, 32)

    def test_parse_applies_defaults(self) -> None:
        extension = {
            "specVersion": "1.0",
            "emitters": [
                {
                    "type": "particle",
                    "node": 0,
                    "particle": {},
                }
            ],
        }
        vfx = parse_vfx(extension, node_count=1)
        self.assertIsNotNone(vfx)
        assert vfx is not None
        particle = vfx.emitters[0].particle
        self.assertIsNotNone(particle)
        assert particle is not None
        self.assertEqual(particle.emission_rate, DEFAULT_EMISSION_RATE)
        self.assertEqual(particle.max_particles, DEFAULT_MAX_PARTICLES)

    def test_parse_skips_invalid_emitters(self) -> None:
        extension = {
            "specVersion": "1.0",
            "emitters": [
                {"type": "ribbon", "node": 0},
                {
                    "type": "particle",
                    "node": 99,
                    "particle": {"emissionRate": 1.0},
                },
                {
                    "type": "particle",
                    "node": 0,
                    "particle": {"emissionRate": -1.0},
                },
                {
                    "type": "particle",
                    "node": 0,
                    "particle": {"emissionRate": 5.0},
                },
            ],
        }
        vfx = parse_vfx(extension, node_count=1)
        self.assertIsNotNone(vfx)
        assert vfx is not None
        self.assertEqual(len(vfx.emitters), 1)
        self.assertEqual(vfx.emitters[0].particle.emission_rate, 5.0)

    def test_parse_rejects_wrong_spec_version(self) -> None:
        extension = {"specVersion": "2.0", "emitters": []}
        self.assertIsNone(parse_vfx(extension))

    def test_serialize_round_trip(self) -> None:
        vfx = VrmxtVfx(
            emitters=[
                VrmxtVfxEmitter(
                    type="particle",
                    node=2,
                    name="Spark",
                    particle=ParticleParams(emission_rate=15.0),
                )
            ]
        )
        serialized = serialize_vfx(vfx)
        parsed = parse_vfx(serialized, node_count=3)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.emitters[0].node, 2)
        self.assertEqual(parsed.emitters[0].particle.emission_rate, 15.0)

    def test_write_vfx_to_gltf(self) -> None:
        json_dict: dict[str, object] = {"nodes": [{}, {}]}
        vfx = VrmxtVfx(
            emitters=[
                VrmxtVfxEmitter(
                    type="particle",
                    node=0,
                    particle=ParticleParams(),
                )
            ]
        )
        write_vfx_to_gltf(json_dict, vfx)
        self.assertIn(EXTENSION_VRMXT_VFX, json_dict["extensionsUsed"])  # type: ignore[index]
        required = json_dict.get("extensionsRequired")
        if isinstance(required, list):
            self.assertNotIn(EXTENSION_VRMXT_VFX, required)
        read_back = read_vfx_from_gltf(json_dict, node_count=1)
        self.assertIsNotNone(read_back)
        assert read_back is not None
        self.assertEqual(len(read_back.emitters), 1)


if __name__ == "__main__":
    unittest.main()
