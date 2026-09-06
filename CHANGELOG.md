# Changelog

## Unreleased

- Document all 13 stencil matrix scenarios and the 24 configured/control
  export/import audits; link published review media without claiming full
  visual conformance or changing the portable schema.
- When Beyond VTuber Tools supplies its authoritative stencil relationship
  graph, export only that graph and its exact compatibility shorthand instead
  of leaking unrelated persisted per-material stencil authoring into the VRM.

## 0.2.6

- Import/export uses stock VRM Add-on for Blender **4.6.0**
  `Vrm1ImportUserExtension` / `Vrm1ExportUserExtension` (no fork
  `extension_hooks` register).
- Import reads frozen stock JSON (`MappingProxyType` / tuple), not only
  `dict` / `list`.
- VFX preview helpers unlink from collections during stock VRM export gather
  (`vrmxt_vfx_preview` only; drop `vrm_exclude_from_export`).
- Image pack helpers scan `bl_ext.*.vrm` exporter modules, not only
  `user_default`.

## 0.2.5

- **Breaking:** MToonXT glTF key `VRMC_materials_mtoonxt` → `VRMXT_materials_mtoonxt`.
  Import/export use the new name only. Python type `VrmcMaterialsMtoonxt` →
  `VrmxtMaterialsMtoonxt`.

## 0.2.4

- MToonXT stencil panel: warn when a writer is Transparent (or Cutout vs Opaque)
  and a clip reader draws earlier — Unity queue cannot stamp in time.
- Material PROPERTIES: **VRMXT Material** parent panel. Materials override and
  MToonXT stencil live there, not under VRM Material.
- MToonXT stencil note: runtime is Unity (no Warudo callout).
- MToonXT stencil: drop outline `same` when body stencil is missing; hide
  Same as body while body is Off.
- MToonXT stencil authoring (`VRMXT_materials_mtoonxt`): body/outline ops, writer
  material pointers, import/export on VRM1 hooks. No EEVEE viewport clip.

## 0.2.2

- Version bump for Blender extension refresh.

## 0.2.1

- Materials override: stop clamping vector props to 0–1 (was `COLOR` + `max=1`).
  Import/export now keeps lilToon values like `_GlitterParams1` `[256, 256, …]`.
- Materials override UI: `*Color` / `_Color` rows use an HDR color swatch
  (`soft_max=10`, no hard max); other vectors stay expanded float4.
- Materials override: migrate 0.2.0 `*Color` values from `value_vector` into
  `value_color` on draw/export so old blends do not re-export as white.
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
