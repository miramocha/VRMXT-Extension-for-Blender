# VRMXT Extension for Blender

Optional Blender 4.2+ extension that authors and round-trips Extended VRM
extensions (`VRMXT_*`, plus `VRMC_materials_mtoonxt` extras) on top of
[Extended-VRM-Addon-for-Blender](https://github.com/miramocha/Extended-VRM-Addon-for-Blender).

Specs live in [Extended-VRM-Specs](https://github.com/miramocha/Extended-VRM-Specs).

Material PROPERTIES: parent panel **VRMXT Material** holds materials override and
MToonXT stencil.

## Status

| Extension | Import | Export | UI | Notes |
|-----------|--------|--------|----|-------|
| `VRMXT_sprite_particle` | JSON → property groups + GeoNodes preview | property groups → JSON | armature UIList | Flat emitters; offsets via helper Empty; preview via shared `VRMXT_Particle` node group (excluded from export). |
| `VRMXT_materials_override` | JSON → material store | material store → JSON | VRMXT Material | Unity slots, catalog shaders, textures. Schema: `idType`/`id` (+ optional `properties[]`). |
| `VRMC_materials_mtoonxt` | JSON → material stencil ops | material settings → JSON | VRMXT Material | Body/outline `write` / `inside` / `insideOverlay` / `outside` / outline `same`. No EEVEE clip. Warns when a writer is Transparent (or Cutout vs Opaque) and a clip reader would draw earlier. Runtime stencil is Unity. |

## Requirements

- Blender **4.2** inclusive through **&lt;5.3**
- [Extended-VRM-Addon-for-Blender](https://github.com/miramocha/Extended-VRM-Addon-for-Blender) with `io_scene_vrm.extension_hooks` (VRM 1.0 hooks)

## Install

1. Install and enable Extended VRM for Blender.
2. Install this extension (`id = vrmxt`, module `io_scene_vrmxt`).
3. Enable **VRMXT Extensions**.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
ruff check src tests
ruff format --check src tests
```

## License

MIT. See [LICENSE](LICENSE).
