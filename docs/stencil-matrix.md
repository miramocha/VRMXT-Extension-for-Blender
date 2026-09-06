# Stencil matrix checkpoint — 2026-09-06

[Watch the Blender / Unity matrix](https://tdw46.github.io/BVT-Stencil-Matrix/).
The [canonical 13-scenario profile](https://github.com/tdw46/Extended-VRM-Specs/blob/codex/mtoonxt-stencil-parity/examples/stencil-parity-matrix.md)
defines exact controls, defaults, distinct visual purposes and recorded limitations.
Keep that document authoritative; do not maintain a competing JSON schema here.

## Export ownership

The enabled add-on exposes official `Vrm1ImportUserExtension` and
`Vrm1ExportUserExtension` classes. Embedded BVT delegates to the same VRMXT package
and mirrors its authoritative relationships into VRMXT properties. Use the stock
VRM 1.0 export command: `pre_save_hook` resolves final material indices and writes
the root `VRMXT_materials_mtoonxt.stencil` graph. No custom exporter
or post-export patch is required. Import handles frozen JSON mappings/sequences.

Equivalent writer/presentation rows coalesce their readers. Export emits only the root
`stencil` graph, never per-material operations or a second effect. Unrelated stale
per-material stencil settings are ignored. Non-equivalent multi-writer cases must not
be silently collapsed.

## Matrix coverage

| Rows | Authoring inputs exercised |
| --- | --- |
| M01 | Independent writer color off and writer depth off; invisible mask control omitted when stencil is disabled. |
| M02–M04 | Reader-qualified show-through, inside-only writer clipping and their combination. |
| M05–M06 | Reader exclusion versus all-scene-silhouette/background-only exclusion. |
| M07 | Source alpha with independent self-occlusion/depth toggles; approved magical aura. |
| M08 | Complete occluded-reader coverage versus M02's visible-reader coverage. |
| M09–M10 | Writer and reader depth publication independently, with late transparent HUD witnesses. |
| A01 | Inside/Outside comparison of a detailed character recolor. |
| A02–A03 | Explicit writer/reader `always` depth comparisons on view-locked projections. |

All 24 configured/control exports in the extended batch matched their actual Unity
imports, including defaulted flags, material targets, writer color and depth tests.
M02 retains four distinct writer graphs; M01 combines two equivalent UI pairs.
M04 is a separate approved capture set. New recordings are review evidence, not
blanket conformance. The Unity profile's culling/topology/URP limitations still apply.

Alpha mode, base alpha, textures and double-sidedness remain standard material
inputs, not extra relationship flags. Turning off depth writes does not itself
make a surface transparent. Native EEVEE does not provide this preview; BVT's
True MToon preview is an optional consumer, not an exporter dependency.

The recorded animation uses companion timelines, not VRM animation timing.
Public review media excludes raw client model/texture assets.
