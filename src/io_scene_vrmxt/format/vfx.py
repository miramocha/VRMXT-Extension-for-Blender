# SPDX-License-Identifier: MIT
"""VRMXT_sprite_particle root glTF extension parsing and serialization."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field

from ..common.constants import EXTENSION_VRMXT_SPRITE_PARTICLE, SPEC_VERSION_1_0
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
from ..common.validation import (
    is_finite_non_negative,
    is_finite_positive,
    is_positive_int,
)

DEFAULT_SIZE = (0.05, 0.05)
DEFAULT_COLOR = (1.0, 1.0, 1.0, 1.0)
DEFAULT_EMISSION_RATE = 10.0
DEFAULT_MAX_PARTICLES = 64
DEFAULT_LIFETIME = 1.0
DEFAULT_START_SPEED = 0.1


@dataclass
class VrmxtVfxEmitter:
    """Flat sprite-particle emitter (root ``VRMXT_sprite_particle`` entry)."""

    node: int
    name: str | None = None
    texture: int | None = None
    size: tuple[float, float] = DEFAULT_SIZE
    color: tuple[float, float, float, float] = DEFAULT_COLOR
    emission_rate: float = DEFAULT_EMISSION_RATE
    max_particles: int = DEFAULT_MAX_PARTICLES
    lifetime: float = DEFAULT_LIFETIME
    start_speed: float = DEFAULT_START_SPEED


@dataclass
class VrmxtVfx:
    spec_version: str = SPEC_VERSION_1_0
    emitters: list[VrmxtVfxEmitter] = field(default_factory=list)


def _parse_size(raw: object) -> tuple[float, float] | None:
    parsed = finite_numbers(as_list(raw) or [], 2)
    if parsed is None:
        return None
    if not all(is_finite_positive(component) for component in parsed):
        return None
    return (parsed[0], parsed[1])


def _parse_color(raw: object) -> tuple[float, float, float, float] | None:
    parsed = finite_numbers(as_list(raw) or [], 4)
    if parsed is None:
        return None
    if parsed[0] < 0.0 or parsed[1] < 0.0 or parsed[2] < 0.0:
        return None
    if parsed[3] < 0.0 or parsed[3] > 1.0:
        return None
    return (parsed[0], parsed[1], parsed[2], parsed[3])


def _parse_emitter(
    raw: Mapping[str, Json],
    node_count: int | None,
    texture_count: int | None,
) -> VrmxtVfxEmitter | None:
    node = as_int(raw.get("node"))
    if node is None or node < 0:
        return None
    if node_count is not None and node >= node_count:
        return None

    texture = as_int(raw.get("texture"))
    if raw.get("texture") is not None:
        if texture is None or texture < 0:
            return None
        if texture_count is not None and texture >= texture_count:
            return None

    size_raw = raw.get("size")
    if size_raw is None:
        size = DEFAULT_SIZE
    else:
        parsed_size = _parse_size(size_raw)
        if parsed_size is None:
            return None
        size = parsed_size

    color_raw = raw.get("color")
    if color_raw is None:
        color = DEFAULT_COLOR
    else:
        parsed_color = _parse_color(color_raw)
        if parsed_color is None:
            return None
        color = parsed_color

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

    start_speed = as_number(raw.get("startSpeed"))
    if raw.get("startSpeed") is not None:
        if start_speed is None or not is_finite_non_negative(start_speed):
            return None
    else:
        start_speed = DEFAULT_START_SPEED

    name = as_str(raw.get("name"))

    return VrmxtVfxEmitter(
        node=node,
        name=name,
        texture=texture,
        size=size,
        color=color,
        emission_rate=emission_rate,
        max_particles=max_particles,
        lifetime=lifetime,
        start_speed=start_speed,
    )


def parse_vfx(
    extension_dict: Mapping[str, Json],
    *,
    node_count: int | None = None,
    texture_count: int | None = None,
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
        emitter = _parse_emitter(emitter_dict, node_count, texture_count)
        if emitter is not None:
            emitters.append(emitter)

    return VrmxtVfx(spec_version=spec_version, emitters=emitters)


def _serialize_emitter(emitter: VrmxtVfxEmitter) -> dict[str, Json]:
    result: dict[str, Json] = {
        "node": emitter.node,
        "size": list(emitter.size),
        "color": list(emitter.color),
        "emissionRate": emitter.emission_rate,
        "maxParticles": emitter.max_particles,
        "lifetime": emitter.lifetime,
        "startSpeed": emitter.start_speed,
    }
    if emitter.name is not None:
        result["name"] = emitter.name
    if emitter.texture is not None:
        result["texture"] = emitter.texture
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
    extensions[EXTENSION_VRMXT_SPRITE_PARTICLE] = serialize_vfx(vfx)
    ensure_extensions_used(json_dict, EXTENSION_VRMXT_SPRITE_PARTICLE)


def read_vfx_from_gltf(
    json_dict: Mapping[str, Json],
    *,
    node_count: int | None = None,
    texture_count: int | None = None,
) -> VrmxtVfx | None:
    extension_dict = get_root_extension(json_dict, EXTENSION_VRMXT_SPRITE_PARTICLE)
    if extension_dict is None:
        return None
    if texture_count is None:
        textures = json_dict.get("textures")
        if isinstance(textures, list):
            texture_count = len(textures)
    return parse_vfx(extension_dict, node_count=node_count, texture_count=texture_count)


__all__ = [
    "DEFAULT_COLOR",
    "DEFAULT_EMISSION_RATE",
    "DEFAULT_LIFETIME",
    "DEFAULT_MAX_PARTICLES",
    "DEFAULT_SIZE",
    "DEFAULT_START_SPEED",
    "VrmxtVfx",
    "VrmxtVfxEmitter",
    "parse_vfx",
    "read_vfx_from_gltf",
    "serialize_vfx",
    "write_vfx_to_gltf",
]
