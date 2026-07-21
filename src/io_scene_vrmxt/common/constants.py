# SPDX-License-Identifier: MIT
"""Shared VRMXT extension identifiers and validation vocabularies."""

EXTENSION_VRMXT_SPRITE_PARTICLE = "VRMXT_sprite_particle"
EXTENSION_MATERIALS_OVERRIDE = "VRMXT_materials_override"
SPEC_VERSION_1_0 = "1.0"

ENGINE_UNITY = "unity"
ENGINE_UNREAL = "unreal"

ID_TYPE_SHADER_NAME = "shaderName"
ID_TYPE_MATERIAL_SET = "materialSet"

TARGET_TYPES = frozenset({"scalar", "vector", "texture", "shaderFeature"})

MTOON_SOURCES = frozenset(
    {
        "shadeColorFactor",
        "shadeMultiplyTexture",
        "shadingShiftFactor",
        "shadingShiftTexture",
        "shadingShiftTexture.scale",
        "shadingToonyFactor",
        "giEqualizationFactor",
    }
)

__all__ = [
    "ENGINE_UNITY",
    "ENGINE_UNREAL",
    "EXTENSION_MATERIALS_OVERRIDE",
    "EXTENSION_VRMXT_SPRITE_PARTICLE",
    "ID_TYPE_MATERIAL_SET",
    "ID_TYPE_SHADER_NAME",
    "MTOON_SOURCES",
    "SPEC_VERSION_1_0",
    "TARGET_TYPES",
]
