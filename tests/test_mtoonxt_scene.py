# SPDX-License-Identifier: MIT
"""Scene RNA, register_embedded, and stencil import/export policy tests."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from io_scene_vrmxt.common.constants import (
    EXTENSION_MATERIALS_MTOON,
    EXTENSION_MATERIALS_MTOONXT,
)
from io_scene_vrmxt.format.mtoonxt import MtoonxtStencil, write_stencil
from io_scene_vrmxt.integration import register_embedded, unregister_embedded
from io_scene_vrmxt.mtoonxt.export_hook import apply_mtoonxt_export
from io_scene_vrmxt.mtoonxt.import_hook import apply_mtoonxt_import
from io_scene_vrmxt.mtoonxt.property_group import (
    apply_parsed_stencils_to_scene,
    stencils_from_scene,
    validate_stencils_in_scene,
)


class _Collection:
    def __init__(self) -> None:
        self._items: list[object] = []

    def add(self):
        item = SimpleNamespace(material=None)
        self._items.append(item)
        return item

    def clear(self) -> None:
        self._items.clear()

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)


class _StencilCollection:
    def __init__(self) -> None:
        self._items: list[object] = []

    def add(self):
        item = _stencil_item()
        self._items.append(item)
        return item

    def clear(self) -> None:
        self._items.clear()

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)


def _scene_settings() -> SimpleNamespace:
    return SimpleNamespace(stencils=_StencilCollection(), stencil_index=0)


def _stencil_item(**kwargs) -> SimpleNamespace:
    defaults = dict(
        writers=_Collection(),
        readers=_Collection(),
        comparison="outside",
        show_writers_through_occluders=False,
        writers_only_inside_readers=False,
        writers_only_outside_readers=False,
        writers_self_occlude=True,
        ignore_occluded_reader_areas=True,
        writers_write_color=True,
        writers_write_depth=True,
        readers_write_depth=True,
        writer_depth_test="lessEqual",
        reader_depth_test="lessEqual",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestMtoonxtScene(unittest.TestCase):
    def test_register_embedded_swaps_provider(self) -> None:
        seen: list[int] = []

        def provider(_context, _indices):
            seen.append(1)
            return []

        register_embedded(
            mtoonxt_stencil_export_provider=provider,
            register_mtoonxt_properties=False,
        )
        try:
            apply_mtoonxt_export(
                SimpleNamespace(json_dict={"materials": []}, material_name_to_index={})
            )
            self.assertEqual(seen, [1])
        finally:
            unregister_embedded()

        apply_mtoonxt_export(
            SimpleNamespace(json_dict={"materials": []}, material_name_to_index={})
        )
        self.assertEqual(seen, [1])

    def test_stencils_from_scene_round_trip_indices(self) -> None:
        hair = SimpleNamespace(name="Hair")
        face = SimpleNamespace(name="Face")
        writers = _Collection()
        writers.add().material = hair
        readers = _Collection()
        readers.add().material = face
        item = _stencil_item(writers=writers, readers=readers)
        settings = SimpleNamespace(stencils=[item], stencil_index=0)
        scene = SimpleNamespace(vrmxt_mtoonxt_stencil_settings=settings)
        rows = stencils_from_scene({"Hair": 1, "Face": 0}, scene=scene)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].writers, [1])
        self.assertEqual(rows[0].readers, [0])

    def test_import_replaces_scene_graph(self) -> None:
        settings = _scene_settings()
        leftover = _stencil_item()
        leftover.writers.add()
        settings.stencils._items.append(leftover)  # noqa: SLF001
        scene = SimpleNamespace(vrmxt_mtoonxt_stencil_settings=settings)
        hair = SimpleNamespace(name="Hair")
        face = SimpleNamespace(name="Face")
        apply_parsed_stencils_to_scene(
            [MtoonxtStencil(writers=[1], readers=[0])],
            {0: face, 1: hair},
            SimpleNamespace(scene=scene),
        )
        self.assertEqual(len(settings.stencils), 1)
        apply_parsed_stencils_to_scene([], {}, SimpleNamespace(scene=scene))
        self.assertEqual(len(settings.stencils), 0)

    def test_validate_overlap_uses_pointer(self) -> None:
        material = SimpleNamespace(as_pointer=lambda: 42)
        writers = _Collection()
        writers.add().material = material
        readers = _Collection()
        readers.add().material = material
        scene = SimpleNamespace(
            vrmxt_mtoonxt_stencil_settings=SimpleNamespace(
                stencils=[_stencil_item(writers=writers, readers=readers)]
            )
        )
        errors = validate_stencils_in_scene(scene)
        self.assertTrue(any("writer and reader" in message for message in errors))

    def test_write_stencil_pops_retired_relationships_key(self) -> None:
        document = {
            "extensions": {
                EXTENSION_MATERIALS_MTOONXT: {
                    "specVersion": "1.0",
                    "stencilRelationships": [{"writers": [0], "readers": [1]}],
                }
            }
        }
        write_stencil(document, [MtoonxtStencil(writers=[0], readers=[1])])
        payload = document["extensions"][EXTENSION_MATERIALS_MTOONXT]
        self.assertNotIn("stencilRelationships", payload)
        self.assertIn("stencil", payload)

    def test_export_skips_provider_when_scene_has_rows(self) -> None:
        hair = SimpleNamespace(name="Hair")
        face = SimpleNamespace(name="Face")
        writers = _Collection()
        writers.add().material = hair
        readers = _Collection()
        readers.add().material = face
        scene = SimpleNamespace(
            vrmxt_mtoonxt_stencil_settings=SimpleNamespace(
                stencils=[_stencil_item(writers=writers, readers=readers)],
                stencil_index=0,
            )
        )
        called = []

        def provider(_context, _indices):
            called.append(1)
            return [MtoonxtStencil(writers=[0], readers=[1])]

        from io_scene_vrmxt.mtoonxt import export_hook

        document = {
            "materials": [
                {
                    "name": "Face",
                    "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
                },
                {
                    "name": "Hair",
                    "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
                },
            ]
        }
        export_hook.register_external_stencil_export_provider(provider)
        try:
            apply_mtoonxt_export(
                SimpleNamespace(
                    json_dict=document,
                    material_name_to_index={"Face": 0, "Hair": 1},
                    scene=scene,
                )
            )
        finally:
            export_hook.unregister_external_stencil_export_provider(provider)
        self.assertEqual(called, [])
        self.assertEqual(
            len(document["extensions"][EXTENSION_MATERIALS_MTOONXT]["stencil"]), 1
        )

    def test_export_drops_non_sibling_mtoon_row(self) -> None:
        from io_scene_vrmxt.mtoonxt import export_hook

        def provider(_context, _indices):
            return [MtoonxtStencil(writers=[1], readers=[0])]

        document = {
            "materials": [
                {"name": "Reader"},
                {
                    "name": "Writer",
                    "extensions": {EXTENSION_MATERIALS_MTOON: {"specVersion": "1.0"}},
                },
            ]
        }
        export_hook.register_external_stencil_export_provider(provider)
        try:
            apply_mtoonxt_export(
                SimpleNamespace(
                    json_dict=document,
                    material_name_to_index={"Reader": 0, "Writer": 1},
                )
            )
        finally:
            export_hook.unregister_external_stencil_export_provider(provider)
        self.assertNotIn("extensions", document)

    def test_import_empty_graph_notifies_consumer(self) -> None:
        from io_scene_vrmxt.mtoonxt import import_hook

        received: list[object] = []

        def consumer(_context, values):
            received.append(list(values))

        import_hook.register_external_stencil_import_consumer(consumer)
        try:
            apply_mtoonxt_import(
                SimpleNamespace(
                    json_dict={"materials": [{}, {}]},
                    material_index_to_material={},
                    scene=None,
                )
            )
        finally:
            import_hook.unregister_external_stencil_import_consumer(consumer)
        self.assertEqual(received, [[]])


if __name__ == "__main__":
    unittest.main()
