# VRMXT Extension for Blender

Optional Blender 4.2+ extension that authors and round-trips Extended VRM
extensions (`VRMXT_*`) on top of
[Extended-VRM-Addon-for-Blender](https://github.com/miramocha/Extended-VRM-Addon-for-Blender).

Specs live in [Extended-VRM-Specs](https://github.com/miramocha/Extended-VRM-Specs).

## Status

| Extension | Import | Export | UI | Notes |
|-----------|--------|--------|----|-------|
| `VRMXT_vfx` | JSON → property groups | property groups → JSON | armature UIList | Authoring MVP; no viewport particle preview. Texture export uses host `find_or_create_image`. |
| `VRMXT_materials_override` | parse/store | serialize Unity/Unreal profiles | stub | Authoring only; no Blender engine profile |

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
