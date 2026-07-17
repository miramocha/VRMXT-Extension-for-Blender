# Contributing

1. Keep Extended-VRM-Specs normative. Link specs; do not duplicate schema text.
2. Peer-depend on Extended VRM hooks. Do not vendor `io_scene_vrm`.
3. Skip invalid emitters/overrides; never abort stock VRM import/export for bad VRMXT data.
4. Never list optional `VRMXT_*` extensions in `extensionsRequired`.
5. Run unit tests and Ruff before opening a PR.
