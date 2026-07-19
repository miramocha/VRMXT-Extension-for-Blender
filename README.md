# VRMXT Extension for Blender

Optional Blender 4.2+ extension that authors and round-trips Extended VRM
extensions (`VRMXT_*`) on top of
[Extended-VRM-Addon-for-Blender](https://github.com/miramocha/Extended-VRM-Addon-for-Blender).

Specs live in [Extended-VRM-Specs](https://github.com/miramocha/Extended-VRM-Specs).

## Status

| Extension | Import | Export | UI | Notes |
|-----------|--------|--------|----|-------|
| `VRMXT_vfx` | JSON → property groups + GeoNodes preview | property groups → JSON | armature UIList | Preview via shared `VRMXT_Particle` node group; export SoT = property groups. |
| `VRMXT_materials_override` | parse/store (`kind`/`name`) | serialize (`kind`/`name`) | stub | Must switch to `idType`/`id` (UniVRMXT already emits that). No production files on old names — replace, don't dual-read. See [Blender Materials Override](https://github.com/miramocha/Extended-VRM-Specs/blob/main/implementations/blender-materials-override.md). |

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
