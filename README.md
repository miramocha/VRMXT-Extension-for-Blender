# VRMXT Extension for Blender

Optional Blender 4.2+ extension that authors and round-trips Extended VRM
extensions (`VRMXT_*`) on top of stock
[VRM Add-on for Blender](https://github.com/saturday06/VRM-Addon-for-Blender)
**4.6.0** or later (VRM 1.0 `Vrm1ImportUserExtension` /
`Vrm1ExportUserExtension` hooks).

Specs live in [Extended-VRM-Specs](https://github.com/miramocha/Extended-VRM-Specs).

Material PROPERTIES: parent panel **VRMXT Material** holds materials override and
MToonXT stencil.

## Status

| Extension | Import | Export | UI | Notes |
|-----------|--------|--------|----|-------|
| `VRMXT_sprite_particle` | JSON → property groups + GeoNodes preview | property groups → JSON | armature UIList | Flat emitters; offsets via helper Empty; preview via shared `VRMXT_Particle` node group (excluded from export). |
| `VRMXT_materials_override` | JSON → material store | material store → JSON | VRMXT Material | Unity slots, catalog shaders, textures. Schema: `idType`/`id` (+ optional `properties[]`). |
| `VRMXT_materials_mtoonxt` | JSON → root stencil graph | Scene settings → JSON | VRMXT Material + Scene | One portable stencil graph controls cross-material presentation, depth tests, and depth publication. No EEVEE clip. Runtime stencil is supplied by a consumer such as UniVRMXT. |

## Requirements

- Blender **4.2** inclusive through **&lt;5.3**
- [VRM Add-on for Blender](https://github.com/saturday06/VRM-Addon-for-Blender/releases/tag/v4.6.0) **4.6.0+** (VRM 1.0 third-party hooks)

**Beyond VTuber Tools / Beyond VRM Extension Suite is not required.** VRMXT's
own Material and Scene panels let you configure stencil operations,
relationships, visibility, and depth settings. The standard VRM importer and
exporter round-trip these settings without a preview add-on installed.

### Optional Blender preview

For an optional visual preview, [Beyond VRM Extension Suite (BVES) on
Gumroad](https://beyonddev.gumroad.com/l/vrm) has a **v1.0.0 release coming soon**
with native-in-Blender stencil preview and MToon render queue offset preview.
These are upcoming preview features, not requirements for VRMXT authoring,
import, or export. VRMXT does not install, purchase, or enable BVES for you.

## Install

1. Install and enable VRM format 4.6.0 or later.
2. Build the standalone extension from the shared source package:

   ```bash
   blender --command extension build --source-dir src/io_scene_vrmxt
   ```

3. Install the generated `vrmxt-0.3.0.zip` through Blender's Extensions UI.
   Its extension ID is `vrmxt`.
4. Enable **VRMXT Extensions**. Stock VRM discovers `Vrm1ImportUserExtension` /
   `Vrm1ExportUserExtension` on this add-on's root module.

## Embedded dependency mode

The same source tree can be vendored under another Blender extension. In that
mode, import the vendored package by its nested package name and call
`integration.register_embedded(...)`. VRMXT still owns and registers its
portable Scene/Material properties; embedded registration omits only standalone
panels. The host exposes `Vrm1ImportUserExtension` and
`Vrm1ExportUserExtension` from its top-level package so the official VRM add-on
discovers them. Existing shared RNA from an enabled standalone copy is reused
rather than duplicated.

The Blender manifest lives beside the Python package so the source directory is
directly buildable as a standalone extension. Embedded hosts ignore that data
file and load the same package through `integration`, so standalone and embedded
installations cannot drift into separate implementations.

Use the official **File > Export > VRM (.vrm)** command.
`Vrm1ExportUserExtension.pre_save_hook()` receives the final material and node
maps and adds authored metadata before the official exporter writes the file.
`Vrm1ImportUserExtension.post_import_hook()` restores that metadata after the
official importer finishes. VRMXT does not register an export operator, invoke
another exporter, or patch a completed GLB.

## Development

See the [stencil matrix checkpoint](docs/stencil-matrix.md) for official-hook
ownership, 13 showcased modes and the linked recorded Blender/Unity comparisons.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
ruff check src tests
ruff format --check src tests
```

## License

MIT. See [LICENSE](LICENSE).
