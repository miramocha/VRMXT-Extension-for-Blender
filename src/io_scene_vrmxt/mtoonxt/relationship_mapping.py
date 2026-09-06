# SPDX-License-Identifier: MIT
"""Map portable stencil relationships to legacy per-material shorthand."""

from __future__ import annotations

from collections.abc import Sequence

from ..format.mtoonxt import (
    COMPARISON_INSIDE,
    DEPTH_LESS_EQUAL,
    OP_INSIDE,
    OP_INSIDE_OVERLAY,
    OP_OUTSIDE,
    OP_SAME,
    OP_WRITE,
    MtoonxtStencil,
    MtoonxtStencilRelationship,
    VrmxtMaterialsMtoonxt,
)


def _merge_assignment(
    assignments: dict[int, tuple[str, list[int]]],
    material_index: int,
    op: str,
    targets: Sequence[int],
    errors: list[str],
) -> None:
    target_list = list(dict.fromkeys(int(index) for index in targets))
    existing = assignments.get(int(material_index))
    if existing is None:
        assignments[int(material_index)] = (op, target_list)
        return
    existing_op, existing_targets = existing
    if existing_op != op:
        errors.append(
            "Material index "
            f"{material_index} has conflicting portable VRMXT stencil roles: "
            f"{existing_op} and {op}."
        )
        return
    for target in target_list:
        if target not in existing_targets:
            existing_targets.append(target)


def relationship_uses_advanced_presentation(
    relationship: MtoonxtStencilRelationship,
) -> bool:
    return (
        not relationship.writers_self_occlude
        or not relationship.ignore_occluded_reader_areas
        or not relationship.writers_write_color
        or not relationship.writers_write_depth
        or not relationship.readers_write_depth
        or relationship.writer_depth_test != DEPTH_LESS_EQUAL
        or relationship.reader_depth_test != DEPTH_LESS_EQUAL
    )


def relationship_shorthand_extras(
    relationships: Sequence[MtoonxtStencilRelationship],
    *,
    material_count: int,
) -> tuple[list[VrmxtMaterialsMtoonxt | None], list[str]]:
    """Return pixel-equivalent legacy material extras for root relationships.

    The root relationship graph remains authoritative. Relationships whose
    presentation cannot be represented by the legacy per-material stencil
    object deliberately produce no shorthand rather than an approximation.
    """

    assignments: dict[int, tuple[str, list[int]]] = {}
    errors: list[str] = []
    for relationship in relationships:
        writers = [
            int(index)
            for index in relationship.writers
            if 0 <= int(index) < material_count
        ]
        readers = [
            int(index)
            for index in relationship.readers
            if 0 <= int(index) < material_count
        ]
        if not writers or not readers or set(writers).intersection(readers):
            continue
        inside_only = relationship.writers_only_inside_readers
        outside_only = relationship.writers_only_outside_readers
        through = relationship.show_writers_through_occluders
        if inside_only and outside_only:
            errors.append(
                "A VRMXT stencil relationship cannot be both inside-only "
                "and outside-only."
            )
            continue
        if relationship_uses_advanced_presentation(relationship) or (
            through and not inside_only
        ):
            continue
        if inside_only:
            subject_op = OP_INSIDE_OVERLAY if through else OP_INSIDE
            for reader in readers:
                _merge_assignment(assignments, reader, OP_WRITE, (), errors)
            for writer in writers:
                _merge_assignment(assignments, writer, subject_op, readers, errors)
        elif outside_only:
            for reader in readers:
                _merge_assignment(assignments, reader, OP_WRITE, (), errors)
            for writer in writers:
                _merge_assignment(assignments, writer, OP_OUTSIDE, readers, errors)
        else:
            subject_op = (
                OP_INSIDE
                if relationship.comparison == COMPARISON_INSIDE
                else OP_OUTSIDE
            )
            for writer in writers:
                _merge_assignment(assignments, writer, OP_WRITE, (), errors)
            for reader in readers:
                _merge_assignment(assignments, reader, subject_op, writers, errors)

    extras: list[VrmxtMaterialsMtoonxt | None] = [None] * material_count
    for material_index, (op, targets) in assignments.items():
        stencil = MtoonxtStencil(
            op=op,
            materials=targets
            if op in {OP_INSIDE, OP_INSIDE_OVERLAY, OP_OUTSIDE}
            else None,
        )
        outline = MtoonxtStencil(
            op=OP_SAME if stencil.materials else OP_WRITE,
        )
        extras[material_index] = VrmxtMaterialsMtoonxt(
            stencil=stencil,
            outline_stencil=outline,
        )
    return extras, list(dict.fromkeys(errors))


__all__ = [
    "relationship_shorthand_extras",
    "relationship_uses_advanced_presentation",
]
