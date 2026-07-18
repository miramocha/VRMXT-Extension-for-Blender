# SPDX-License-Identifier: MIT
"""VRMXT_vfx root glTF extension parsing and serialization."""

from __future__ import annotations

import math
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field

from ..common.constants import EXTENSION_VRMXT_VFX, SPEC_VERSION_1_0
from ..common.json_util import (
    Json,
    as_dict,
    as_int,
    as_list,
    as_number,
    as_str,
    ensure_extensions_used,
    finite_numbers,
    get_root_extension,
)
from ..common.validation import is_finite_non_negative, is_positive_int

DEFAULT_LOCAL_POSITION = (0.0, 0.0, 0.0)
DEFAULT_LOCAL_ROTATION = (0.0, 0.0, 0.0, 1.0)
DEFAULT_EMISSION_RATE = 10.0
DEFAULT_MAX_PARTICLES = 64
DEFAULT_LIFETIME = 1.0
DEFAULT_START_SIZE = 0.05
DEFAULT_START_SPEED = 0.1
DEFAULT_START_COLOR = (1.0, 1.0, 1.0, 1.0)

EMITTER_TYPE_PARTICLE = "particle"


@dataclass
class ParticleParams:
    texture: int | None = None
    emission_rate: float = DEFAULT_EMISSION_RATE
    max_particles: int = DEFAULT_MAX_PARTICLES
    lifetime: float = DEFAULT_LIFETIME
    start_size: float = DEFAULT_START_SIZE
    start_speed: float = DEFAULT_START_SPEED
    start_color: tuple[float, float, float, float] = DEFAULT_START_COLOR


@dataclass
class VrmxtVfxEmitter:
    type: str
    node: int
    name: str | None = None
    local_position: tuple[float, float, float] = DEFAULT_LOCAL_POSITION
    local_rotation: tuple[float, float, float, float] = DEFAULT_LOCAL_ROTATION
    particle: ParticleParams | None = None


@dataclass
class VrmxtVfx:
    spec_version: str = SPEC_VERSION_1_0
    emitters: list[VrmxtVfxEmitter] = field(default_factory=list)


def _quaternion_is_valid(rotation: tuple[float, float, float, float]) -> bool:
    length_squared = sum(component * component for component in rotation)
    return length_squared > 0.0 and all(
        math.isfinite(component) for component in rotation
    )


def _parse_particle_params(raw: Mapping[str, Json]) -> ParticleParams | None:
    texture = as_int(raw.get("texture"))
    if raw.get("texture") is not None and texture is None:
        return None

    emission_rate = as_number(raw.get("emissionRate"))
    if raw.get("emissionRate") is not None:
        if emission_rate is None or not is_finite_non_negative(emission_rate):
            return None
    else:
        emission_rate = DEFAULT_EMISSION_RATE

    max_particles = as_int(raw.get("maxParticles"))
    if raw.get("maxParticles") is not None:
        if max_particles is None or not is_positive_int(max_particles):
            return None
    else:
        max_particles = DEFAULT_MAX_PARTICLES

    lifetime = as_number(raw.get("lifetime"))
    if raw.get("lifetime") is not None:
        if lifetime is None or not is_finite_non_negative(lifetime):
            return None
    else:
        lifetime = DEFAULT_LIFETIME

    start_size = as_number(raw.get("startSize"))
    if raw.get("startSize") is not None:
        if start_size is None or not is_finite_non_negative(start_size):
            return None
    else:
        start_size = DEFAULT_START_SIZE

    start_speed = as_number(raw.get("startSpeed"))
    if raw.get("startSpeed") is not None:
        if start_speed is None or not is_finite_non_negative(start_speed):
            return None
    else:
        start_speed = DEFAULT_START_SPEED

    start_color_raw = raw.get("startColor")
    if start_color_raw is None:
        start_color = DEFAULT_START_COLOR
    else:
        parsed_color = finite_numbers(as_list(start_color_raw) or [], 4)
        if parsed_color is None:
            return None
        start_color = (
            parsed_color[0],
            parsed_color[1],
            parsed_color[2],
            parsed_color[3],
        )

    return ParticleParams(
        texture=texture,
        emission_rate=emission_rate,
        max_particles=max_particles,
        lifetime=lifetime,
        start_size=start_size,
        start_speed=start_speed,
        start_color=start_color,
    )


def _parse_emitter(
    raw: Mapping[str, Json], node_count: int | None
) -> VrmxtVfxEmitter | None:
    emitter_type = as_str(raw.get("type"))
    if emitter_type != EMITTER_TYPE_PARTICLE:
        return None

    node = as_int(raw.get("node"))
    if node is None or node < 0:
        return None
    if node_count is not None and node >= node_count:
        return None

    local_position_raw = raw.get("localPosition")
    if local_position_raw is None:
        local_position = DEFAULT_LOCAL_POSITION
    else:
        parsed_position = finite_numbers(as_list(local_position_raw) or [], 3)
        if parsed_position is None:
            return None
        local_position = (parsed_position[0], parsed_position[1], parsed_position[2])

    local_rotation_raw = raw.get("localRotation")
    if local_rotation_raw is None:
        local_rotation = DEFAULT_LOCAL_ROTATION
    else:
        parsed_rotation = finite_numbers(as_list(local_rotation_raw) or [], 4)
        if parsed_rotation is None:
            return None
        local_rotation = (
            parsed_rotation[0],
            parsed_rotation[1],
            parsed_rotation[2],
            parsed_rotation[3],
        )
        if not _quaternion_is_valid(local_rotation):
            return None

    particle_raw = as_dict(raw.get("particle"))
    if particle_raw is None:
        return None
    particle = _parse_particle_params(particle_raw)
    if particle is None:
        return None

    name = as_str(raw.get("name"))

    return VrmxtVfxEmitter(
        type=emitter_type,
        node=node,
        name=name,
        local_position=local_position,
        local_rotation=local_rotation,
        particle=particle,
    )


def parse_vfx(
    extension_dict: Mapping[str, Json],
    *,
    node_count: int | None = None,
) -> VrmxtVfx | None:
    spec_version = as_str(extension_dict.get("specVersion"))
    if spec_version != SPEC_VERSION_1_0:
        return None

    emitters_raw = as_list(extension_dict.get("emitters"))
    if emitters_raw is None:
        return None

    emitters: list[VrmxtVfxEmitter] = []
    for item in emitters_raw:
        emitter_dict = as_dict(item)
        if emitter_dict is None:
            continue
        emitter = _parse_emitter(emitter_dict, node_count)
        if emitter is not None:
            emitters.append(emitter)

    return VrmxtVfx(spec_version=spec_version, emitters=emitters)


def _serialize_particle_params(particle: ParticleParams) -> dict[str, Json]:
    result: dict[str, Json] = {
        "emissionRate": particle.emission_rate,
        "maxParticles": particle.max_particles,
        "lifetime": particle.lifetime,
        "startSize": particle.start_size,
        "startSpeed": particle.start_speed,
        "startColor": list(particle.start_color),
    }
    if particle.texture is not None:
        result["texture"] = particle.texture
    return result


def _serialize_emitter(emitter: VrmxtVfxEmitter) -> dict[str, Json]:
    result: dict[str, Json] = {
        "type": emitter.type,
        "node": emitter.node,
    }
    if emitter.name is not None:
        result["name"] = emitter.name
    if emitter.local_position != DEFAULT_LOCAL_POSITION:
        result["localPosition"] = list(emitter.local_position)
    if emitter.local_rotation != DEFAULT_LOCAL_ROTATION:
        result["localRotation"] = list(emitter.local_rotation)
    if emitter.particle is not None:
        result["particle"] = _serialize_particle_params(emitter.particle)
    return result


def serialize_vfx(vfx: VrmxtVfx) -> dict[str, Json]:
    return {
        "specVersion": vfx.spec_version,
        "emitters": [_serialize_emitter(emitter) for emitter in vfx.emitters],
    }


def write_vfx_to_gltf(json_dict: MutableMapping[str, Json], vfx: VrmxtVfx) -> None:
    extensions = json_dict.get("extensions")
    if not isinstance(extensions, dict):
        extensions = {}
        json_dict["extensions"] = extensions
    extensions[EXTENSION_VRMXT_VFX] = serialize_vfx(vfx)
    ensure_extensions_used(json_dict, EXTENSION_VRMXT_VFX)


def read_vfx_from_gltf(
    json_dict: Mapping[str, Json], *, node_count: int | None = None
) -> VrmxtVfx | None:
    extension_dict = get_root_extension(json_dict, EXTENSION_VRMXT_VFX)
    if extension_dict is None:
        return None
    return parse_vfx(extension_dict, node_count=node_count)


__all__ = [
    "DEFAULT_EMISSION_RATE",
    "DEFAULT_LOCAL_POSITION",
    "DEFAULT_LOCAL_ROTATION",
    "DEFAULT_MAX_PARTICLES",
    "EMITTER_TYPE_PARTICLE",
    "ParticleParams",
    "VrmxtVfx",
    "VrmxtVfxEmitter",
    "parse_vfx",
    "read_vfx_from_gltf",
    "serialize_vfx",
    "write_vfx_to_gltf",
]
