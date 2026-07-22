# Changelog

## Unreleased

## 0.2.2

- Version bump for Blender extension refresh.

## 0.2.1

- Materials override: stop clamping vector props to 0–1 (was `COLOR` + `max=1`).
  Import/export now keeps lilToon values like `_GlitterParams1` `[256, 256, …]`.
- Materials override UI: `*Color` / `_Color` rows use an HDR color swatch
  (`soft_max=10`, no hard max); other vectors stay expanded float4.
- Materials override textures: bind Blender `Image` on import; on export pack via
  `ensure_vfx_texture_index` and never keep stale `textures[]` indices (fixes
  missing override-only images like `VrmxtTestTexture` after Blender re-export).

## 0.2.0

- Materials override authoring UI (Add Override, Engine / Variant / catalog shader,
  Add Common Props / Add / Remove properties)
- Vendored lilToon catalog JSON (opaque / cutout / transparent)
- Unity multi-slot parse: `(engine, variant)` selection key
- Export prefers authored PropertyGroups; remaps texture Images when helpers available

## 0.1.0

- Initial scaffold: format models, VRM1 hook registration, VFX and materials-override foundations.
- Materials override: `idType`/`id` (+ optional `properties[]`); import/export store
  extension JSON on the Blender material. Readonly Material PROPERTIES panel.
- VFX Geometry Nodes viewport preview after import (shared `VRMXT_Particle` group;
  Empty attachment helper + child mesh for the modifier)
- Preview ownership uses stable armature UUID (rename-safe); unique Empty/material
  names per emitter index; node-group updates rebuild in place
- Preview rebuild failures are logged (no longer swallowed silently)
- Rebuild / Clear VFX Preview operators on the VFX panel
- Preview helpers tagged `vrmxt_vfx_preview` plus host `vrm_exclude_from_export`
  (export SoT stays property groups)
- VFX armature UI (UIList, add/remove/reorder) with bone or object attachment
- VFX import/export resolves Image ↔ glTF textures via host helpers
- New emitters default to active/first bone; UIList warns when attachment missing
- Export logs skipped emitters (unresolved attachment)
