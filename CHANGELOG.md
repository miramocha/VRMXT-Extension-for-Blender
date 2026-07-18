# Changelog

## Unreleased

- VFX Geometry Nodes viewport preview after import (shared `VRMXT_Particle` group;
  Empty attachment helper + child mesh for the modifier)
- Preview ownership uses stable armature UUID (rename-safe); unique Empty/material
  names per emitter index; node-group updates rebuild in place
- Preview rebuild failures are logged (no longer swallowed silently)
- Rebuild / Clear VFX Preview operators on the VFX panel
- Preview helpers tagged `vrmxt_vfx_preview` (export SoT stays property groups)
- VFX armature UI (UIList, add/remove/reorder) with bone or object attachment
- VFX import/export resolves Image ↔ glTF textures via host helpers
- New emitters default to active/first bone; UIList warns when attachment missing
- Export logs skipped emitters (unresolved attachment)

## 0.1.0

- Initial scaffold: format models, VRM1 hook registration, VFX and materials-override foundations.
