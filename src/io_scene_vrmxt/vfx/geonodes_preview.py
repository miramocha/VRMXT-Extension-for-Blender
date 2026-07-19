# SPDX-License-Identifier: MIT
"""Geometry Nodes viewport preview for VRMXT_vfx particle emitters.

Property groups remain the export source of truth. Preview helpers are tagged
with ``PREVIEW_CUSTOM_PROP`` (VRMXT lifecycle) and
``EXCLUDE_FROM_EXPORT_CUSTOM_PROP`` (host ``export_objects`` filter) and must
not be inferred back into VFX data.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from .property_group import ATTACHMENT_TYPE_BONE, ATTACHMENT_TYPE_OBJECT

logger = logging.getLogger(__name__)

NODE_GROUP_NAME = "VRMXT_Particle"
NODE_GROUP_VERSION = 6
PREVIEW_CUSTOM_PROP = "vrmxt_vfx_preview"
# Host contract (Extended VRM ``export_objects``). Soft-import when available.
EXCLUDE_FROM_EXPORT_CUSTOM_PROP = "vrm_exclude_from_export"
try:
    from io_scene_vrm.extension_hooks import (  # type: ignore[attr-defined]
        EXCLUDE_FROM_EXPORT_CUSTOM_PROP as _HOST_EXCLUDE_PROP,
    )

    EXCLUDE_FROM_EXPORT_CUSTOM_PROP = _HOST_EXCLUDE_PROP
except ImportError:
    pass
# Stable per-armature id (UUID). Helpers store this value — not the armature name —
# so rename does not orphan previews.
ARMATURE_PREVIEW_ID_PROP = "vrmxt_vfx_id"
PREVIEW_ARMATURE_PROP = "vrmxt_vfx_preview_armature"
PREVIEW_EMITTER_PROP = "vrmxt_vfx_preview_emitter"
OBJECT_NAME_PREFIX = "VRMXT_vfx_"
MATERIAL_NAME_PREFIX = "VRMXT_vfx_mat_"
MODIFIER_NAME = "VRMXT_Particle"
# Legacy leftover from free-viewport billboard sync (removed; delete on clear).
_LEGACY_VIEWPORT_VIEW_NAME = "VRMXT_vfx_viewport_view"

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")

try:
    import bpy
    from mathutils import Quaternion, Vector
except ImportError:  # pragma: no cover - exercised only outside Blender
    bpy = None  # type: ignore[assignment]
    Quaternion = None  # type: ignore[misc, assignment]
    Vector = None  # type: ignore[misc, assignment]


def is_preview_object(obj: Any) -> bool:
    """Return True when ``obj`` is a VRMXT VFX GeoNodes preview helper."""
    if obj is None:
        return False
    try:
        return bool(obj.get(PREVIEW_CUSTOM_PROP))
    except (AttributeError, TypeError, KeyError):
        return False


def preview_object_name(emitter_name: str, index: int) -> str:
    """Stable unique Empty name: sanitized label plus emitter index."""
    label = (emitter_name or "").strip() or "Emitter"
    safe = _SAFE_NAME_RE.sub("_", label).strip("._") or "Emitter"
    return f"{OBJECT_NAME_PREFIX}{safe}.{index:03d}"


def _safe_token(value: str, fallback: str) -> str:
    safe = _SAFE_NAME_RE.sub("_", (value or "").strip()).strip("._")
    return safe or fallback


def _ensure_armature_preview_id(armature_object: Any) -> str:
    """Return a stable id on the armature used to own preview helpers.

    Prefers a persisted UUID. If the custom property cannot be stored, falls back
    to the armature object name so clear/rebuild can still match tagged helpers.
    """
    existing = None
    try:
        existing = armature_object.get(ARMATURE_PREVIEW_ID_PROP)
    except (AttributeError, TypeError, KeyError):
        existing = None
    if existing:
        return str(existing)

    name_fallback = str(getattr(armature_object, "name", "") or "")
    new_id = str(uuid.uuid4())
    try:
        armature_object[ARMATURE_PREVIEW_ID_PROP] = new_id
        stored = armature_object.get(ARMATURE_PREVIEW_ID_PROP)
        if str(stored or "") == new_id:
            return new_id
    except (AttributeError, TypeError, KeyError):
        pass
    return name_fallback or new_id


def _preview_belongs_to_armature(
    obj: Any, armature_object: Any, armature_id: str
) -> bool:
    owner = ""
    try:
        owner = str(obj.get(PREVIEW_ARMATURE_PROP, "") or "")
    except (AttributeError, TypeError, KeyError):
        owner = ""
    if owner:
        if owner == armature_id:
            return True
        # Legacy helpers tagged with armature name before UUID ownership.
        if owner == getattr(armature_object, "name", ""):
            return True
        return False
    # Untagged parent chain fallback (legacy).
    if obj.parent == armature_object:
        return True
    parent = obj.parent
    if parent is not None and is_preview_object(parent):
        return _preview_belongs_to_armature(parent, armature_object, armature_id)
    return False


def ensure_particle_node_group() -> Any:
    """Create or update the shared ``VRMXT_Particle`` Geometry Node group in place.

    Stale versions are rebuilt inside the same datablock so other armatures' modifiers
    keep a valid node-group reference.
    """
    if bpy is None:
        raise RuntimeError("bpy is unavailable")

    existing = bpy.data.node_groups.get(NODE_GROUP_NAME)
    if existing is not None and existing.bl_idname == "GeometryNodeTree":
        if existing.get("vrmxt_particle_version") == NODE_GROUP_VERSION:
            return existing
        _populate_particle_node_group(existing)
        existing["vrmxt_particle_version"] = NODE_GROUP_VERSION
        return existing

    group = bpy.data.node_groups.new(NODE_GROUP_NAME, "GeometryNodeTree")
    _populate_particle_node_group(group)
    group["vrmxt_particle_version"] = NODE_GROUP_VERSION
    return group


def clear_vfx_preview(armature_object: Any) -> int:
    """Remove preview helpers owned by ``armature_object``. Return count removed."""
    if bpy is None or armature_object is None:
        return 0

    armature_id = ""
    try:
        armature_id = str(armature_object.get(ARMATURE_PREVIEW_ID_PROP, "") or "")
    except (AttributeError, TypeError, KeyError):
        armature_id = ""
    if not armature_id:
        # Still clear legacy name-tagged helpers for this armature.
        armature_id = getattr(armature_object, "name", "")

    candidates: list[Any] = []
    for obj in list(bpy.data.objects):
        if not is_preview_object(obj):
            continue
        if not _preview_belongs_to_armature(obj, armature_object, armature_id):
            continue
        candidates.append(obj)

    # Remove mesh children before empty parents.
    candidates.sort(key=lambda o: 0 if getattr(o, "type", None) == "MESH" else 1)

    removed = 0
    for obj in candidates:
        mesh = obj.data if getattr(obj, "type", None) == "MESH" else None
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh is not None and getattr(mesh, "users", 1) == 0:
            bpy.data.meshes.remove(mesh)
        removed += 1

    _remove_legacy_viewport_view_object()
    return removed


def _remove_legacy_viewport_view_object() -> None:
    """Drop the old free-viewport tracking Empty if it still exists."""
    if bpy is None:
        return
    legacy = bpy.data.objects.get(_LEGACY_VIEWPORT_VIEW_NAME)
    if legacy is None:
        return
    bpy.data.objects.remove(legacy, do_unlink=True)


def rebuild_vfx_preview(armature_object: Any, *, context: Any | None = None) -> int:
    """Clear and recreate GeoNodes preview helpers from armature VFX settings.

    Returns the number of helpers created.
    """
    if bpy is None or armature_object is None:
        return 0
    if getattr(armature_object, "type", None) != "ARMATURE":
        return 0

    armature_data = armature_object.data
    settings = getattr(armature_data, "vrmxt_vfx_settings", None)
    if settings is None:
        clear_vfx_preview(armature_object)
        return 0

    clear_vfx_preview(armature_object)
    emitters = settings.emitters
    if not emitters:
        return 0

    _ensure_armature_preview_id(armature_object)
    node_group = ensure_particle_node_group()
    blend_context = context
    if blend_context is None:
        blend_context = bpy.context

    created = 0
    for index, emitter in enumerate(emitters):
        if getattr(emitter, "emitter_type", "particle") != "particle":
            continue
        helper = _spawn_emitter_preview(
            armature_object=armature_object,
            emitter=emitter,
            index=index,
            node_group=node_group,
            context=blend_context,
        )
        if helper is not None:
            created += 1
    return created


def _populate_particle_node_group(ng: Any) -> Any:
    """Rebuild Geometry Nodes contents on an existing or new node group datablock."""
    assert bpy is not None
    iface = ng.interface
    while iface.items_tree:
        iface.remove(iface.items_tree[0])

    def add_in(name: str, socket_type: str, default: Any = None) -> None:
        sock = iface.new_socket(name=name, in_out="INPUT", socket_type=socket_type)
        if default is not None:
            sock.default_value = default

    add_in("Geometry", "NodeSocketGeometry")
    add_in("Emission Rate", "NodeSocketFloat", 10.0)
    add_in("Max Particles", "NodeSocketInt", 64)
    add_in("Lifetime", "NodeSocketFloat", 1.0)
    add_in("Start Size", "NodeSocketFloat", 0.05)
    add_in("Start Speed", "NodeSocketFloat", 0.1)
    iface.new_socket(name="Material", in_out="INPUT", socket_type="NodeSocketMaterial")
    iface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    def link(from_sock: Any, to_sock: Any) -> None:
        links.new(from_sock, to_sock)

    def math_node(
        operation: str, location: tuple[float, float], label: str = ""
    ) -> Any:
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        node.location = location
        if label:
            node.label = label
        return node

    in_n = nodes.new("NodeGroupInput")
    in_n.location = (-1800, 0)
    out_n = nodes.new("NodeGroupOutput")
    out_n.location = (2000, 0)

    sim_out = nodes.new("GeometryNodeSimulationOutput")
    sim_out.location = (200, 200)
    while len(sim_out.state_items):
        sim_out.state_items.remove(sim_out.state_items[0])
    sim_out.state_items.new("GEOMETRY", "Geometry")
    sim_out.state_items.new("FLOAT", "Accum")

    sim_in = nodes.new("GeometryNodeSimulationInput")
    sim_in.location = (-1000, 200)
    sim_in.pair_with_output(sim_out)

    empty_pts = nodes.new("GeometryNodePoints")
    empty_pts.location = (-1400, 300)
    empty_pts.inputs["Count"].default_value = 0
    link(empty_pts.outputs["Points"], sim_in.inputs["Geometry"])
    if "Accum" in sim_in.inputs:
        sim_in.inputs["Accum"].default_value = 0.0

    age_attr = nodes.new("GeometryNodeInputNamedAttribute")
    age_attr.location = (-800, 0)
    age_attr.data_type = "FLOAT"
    age_attr.inputs["Name"].default_value = "age"

    age_add = math_node("ADD", (-600, 0), "age+=dt")
    link(age_attr.outputs["Attribute"], age_add.inputs[0])
    link(sim_in.outputs["Delta Time"], age_add.inputs[1])

    store_age = nodes.new("GeometryNodeStoreNamedAttribute")
    store_age.location = (-400, 200)
    store_age.data_type = "FLOAT"
    store_age.domain = "POINT"
    store_age.inputs["Name"].default_value = "age"
    link(sim_in.outputs["Geometry"], store_age.inputs["Geometry"])
    link(age_add.outputs[0], store_age.inputs["Value"])

    age_gt = math_node("GREATER_THAN", (-200, 0), "age>life")
    link(age_add.outputs[0], age_gt.inputs[0])
    link(in_n.outputs["Lifetime"], age_gt.inputs[1])

    delete_old = nodes.new("GeometryNodeDeleteGeometry")
    delete_old.location = (0, 200)
    delete_old.domain = "POINT"
    delete_old.mode = "ALL"
    link(store_age.outputs["Geometry"], delete_old.inputs["Geometry"])
    link(age_gt.outputs[0], delete_old.inputs["Selection"])

    speed_dt = math_node("MULTIPLY", (-600, -200), "speed*dt")
    link(in_n.outputs["Start Speed"], speed_dt.inputs[0])
    link(sim_in.outputs["Delta Time"], speed_dt.inputs[1])

    combine = nodes.new("ShaderNodeCombineXYZ")
    combine.location = (-400, -200)
    link(speed_dt.outputs[0], combine.inputs["Y"])

    set_pos = nodes.new("GeometryNodeSetPosition")
    set_pos.location = (200, 100)
    link(delete_old.outputs["Geometry"], set_pos.inputs["Geometry"])
    link(combine.outputs["Vector"], set_pos.inputs["Offset"])

    rate_dt = math_node("MULTIPLY", (-800, -400), "rate*dt")
    link(in_n.outputs["Emission Rate"], rate_dt.inputs[0])
    link(sim_in.outputs["Delta Time"], rate_dt.inputs[1])

    accum_add = math_node("ADD", (-600, -400), "accum+")
    link(sim_in.outputs["Accum"], accum_add.inputs[0])
    link(rate_dt.outputs[0], accum_add.inputs[1])

    accum_floor = math_node("FLOOR", (-400, -450), "floor")
    link(accum_add.outputs[0], accum_floor.inputs[0])

    accum_sub = math_node("SUBTRACT", (-200, -400), "accum-")
    link(accum_add.outputs[0], accum_sub.inputs[0])
    link(accum_floor.outputs[0], accum_sub.inputs[1])

    fti = nodes.new("FunctionNodeFloatToInt")
    fti.location = (-200, -550)
    fti.rounding_mode = "FLOOR"
    link(accum_floor.outputs[0], fti.inputs["Float"])

    new_pts = nodes.new("GeometryNodePoints")
    new_pts.location = (0, -550)
    link(fti.outputs["Integer"], new_pts.inputs["Count"])

    store_new = nodes.new("GeometryNodeStoreNamedAttribute")
    store_new.location = (200, -550)
    store_new.data_type = "FLOAT"
    store_new.domain = "POINT"
    store_new.inputs["Name"].default_value = "age"
    store_new.inputs["Value"].default_value = 0.0
    link(new_pts.outputs["Points"], store_new.inputs["Geometry"])

    join = nodes.new("GeometryNodeJoinGeometry")
    join.location = (400, 50)
    link(set_pos.outputs["Geometry"], join.inputs["Geometry"])
    link(store_new.outputs["Geometry"], join.inputs["Geometry"])

    idx = nodes.new("GeometryNodeInputIndex")
    idx.location = (400, -150)
    idx_ge = nodes.new("FunctionNodeCompare")
    idx_ge.location = (600, -150)
    idx_ge.data_type = "INT"
    idx_ge.operation = "GREATER_EQUAL"
    a_int = next(s for s in idx_ge.inputs if s.identifier == "A_INT")
    b_int = next(s for s in idx_ge.inputs if s.identifier == "B_INT")
    link(idx.outputs["Index"], a_int)
    link(in_n.outputs["Max Particles"], b_int)

    delete_cap = nodes.new("GeometryNodeDeleteGeometry")
    delete_cap.location = (800, 50)
    delete_cap.domain = "POINT"
    link(join.outputs["Geometry"], delete_cap.inputs["Geometry"])
    link(idx_ge.outputs["Result"], delete_cap.inputs["Selection"])

    link(delete_cap.outputs["Geometry"], sim_out.inputs["Geometry"])
    link(accum_sub.outputs[0], sim_out.inputs["Accum"])

    grid = nodes.new("GeometryNodeMeshGrid")
    grid.location = (0, -400)
    grid.inputs["Size X"].default_value = 1.0
    grid.inputs["Size Y"].default_value = 1.0
    grid.inputs["Vertices X"].default_value = 2
    grid.inputs["Vertices Y"].default_value = 2

    # Persist UVs so Image Texture samples the sprite (not a transparent texel).
    store_uv = nodes.new("GeometryNodeStoreNamedAttribute")
    store_uv.location = (200, -400)
    store_uv.data_type = "FLOAT2"
    store_uv.domain = "CORNER"
    store_uv.inputs["Name"].default_value = "UVMap"
    link(grid.outputs["Mesh"], store_uv.inputs["Geometry"])
    link(grid.outputs["UV Map"], store_uv.inputs["Value"])

    # Mesh Grid lies in XY (normal +Z). Rotate to XZ (normal +Y) — fixed
    # orientation in emitter local space (no camera / viewport billboarding).
    grid_rot_e = nodes.new("FunctionNodeEulerToRotation")
    grid_rot_e.location = (200, -550)
    grid_rot_e.inputs["Euler"].default_value = (1.57079632679, 0.0, 0.0)

    grid_xf = nodes.new("GeometryNodeTransform")
    grid_xf.location = (400, -400)
    link(store_uv.outputs["Geometry"], grid_xf.inputs["Geometry"])
    link(grid_rot_e.outputs["Rotation"], grid_xf.inputs["Rotation"])

    combine_s = nodes.new("ShaderNodeCombineXYZ")
    combine_s.location = (800, -400)
    link(in_n.outputs["Start Size"], combine_s.inputs["X"])
    link(in_n.outputs["Start Size"], combine_s.inputs["Y"])
    link(in_n.outputs["Start Size"], combine_s.inputs["Z"])

    iop = nodes.new("GeometryNodeInstanceOnPoints")
    iop.location = (1000, -200)
    link(sim_out.outputs["Geometry"], iop.inputs["Points"])
    link(grid_xf.outputs["Geometry"], iop.inputs["Instance"])
    link(combine_s.outputs["Vector"], iop.inputs["Scale"])

    set_mat = nodes.new("GeometryNodeSetMaterial")
    set_mat.location = (1200, -200)
    link(iop.outputs["Instances"], set_mat.inputs["Geometry"])
    link(in_n.outputs["Material"], set_mat.inputs["Material"])

    realize = nodes.new("GeometryNodeRealizeInstances")
    realize.location = (1400, -200)
    link(set_mat.outputs["Geometry"], realize.inputs["Geometry"])
    link(realize.outputs["Geometry"], out_n.inputs["Geometry"])

    return ng


def _spawn_emitter_preview(
    *,
    armature_object: Any,
    emitter: Any,
    index: int,
    node_group: Any,
    context: Any,
) -> Any | None:
    assert bpy is not None
    assert Quaternion is not None
    assert Vector is not None

    attachment_type = getattr(emitter, "attachment_type", ATTACHMENT_TYPE_BONE)
    parent_bone = ""
    parent_object = armature_object

    if attachment_type == ATTACHMENT_TYPE_BONE:
        bone_name = getattr(emitter, "attachment_bone", "") or ""
        if not bone_name:
            logger.warning(
                "VFX preview skip emitter %r: missing attachment bone",
                getattr(emitter, "name", ""),
            )
            return None
        if bone_name not in armature_object.data.bones:
            logger.warning(
                "VFX preview skip emitter %r: bone %r not found",
                getattr(emitter, "name", ""),
                bone_name,
            )
            return None
        parent_bone = bone_name
    elif attachment_type == ATTACHMENT_TYPE_OBJECT:
        attachment_object = getattr(emitter, "attachment_object", None)
        if attachment_object is None:
            logger.warning(
                "VFX preview skip emitter %r: missing attachment object",
                getattr(emitter, "name", ""),
            )
            return None
        parent_object = attachment_object
    else:
        logger.warning(
            "VFX preview skip emitter %r: unknown attachment_type %r",
            getattr(emitter, "name", ""),
            attachment_type,
        )
        return None

    name = preview_object_name(getattr(emitter, "name", ""), index)
    collection = _target_collection(armature_object, context)
    armature_id = _ensure_armature_preview_id(armature_object)

    # Empty owns attachment transform (Empties cannot host Geometry Nodes).
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = "PLAIN_AXES"
    empty.empty_display_size = 0.05
    empty[PREVIEW_CUSTOM_PROP] = 1
    empty[EXCLUDE_FROM_EXPORT_CUSTOM_PROP] = 1
    empty[PREVIEW_ARMATURE_PROP] = armature_id
    empty[PREVIEW_EMITTER_PROP] = getattr(emitter, "name", "") or name
    empty.hide_render = True
    collection.objects.link(empty)

    empty.parent = parent_object
    if parent_bone:
        empty.parent_type = "BONE"
        empty.parent_bone = parent_bone
    else:
        empty.parent_type = "OBJECT"

    loc = tuple(getattr(emitter, "local_position", (0.0, 0.0, 0.0)))
    rot = tuple(getattr(emitter, "local_rotation", (0.0, 0.0, 0.0, 1.0)))
    empty.location = Vector((float(loc[0]), float(loc[1]), float(loc[2])))
    quat = Quaternion((float(rot[3]), float(rot[0]), float(rot[1]), float(rot[2])))
    # Blender Quaternion is (w, x, y, z); spec stores xyzw.
    if quat.magnitude > 0.0:
        quat.normalize()
        empty.rotation_mode = "QUATERNION"
        empty.rotation_quaternion = quat

    # Child mesh carries the Nodes modifier (base mesh has no faces).
    geo_name = f"{name}_geo"
    mesh = bpy.data.meshes.new(geo_name)
    mesh.from_pydata([(0.0, 0.0, 0.0)], [], [])
    mesh.update()

    geo = bpy.data.objects.new(geo_name, mesh)
    geo[PREVIEW_CUSTOM_PROP] = 1
    geo[EXCLUDE_FROM_EXPORT_CUSTOM_PROP] = 1
    geo[PREVIEW_ARMATURE_PROP] = armature_id
    geo[PREVIEW_EMITTER_PROP] = getattr(emitter, "name", "") or name
    geo.hide_render = True
    geo.hide_select = True
    collection.objects.link(geo)
    geo.parent = empty
    geo.parent_type = "OBJECT"
    geo.location = (0.0, 0.0, 0.0)
    geo.rotation_mode = "QUATERNION"
    geo.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)

    material = _ensure_emitter_material(armature_object, emitter, index)
    modifier = geo.modifiers.new(name=MODIFIER_NAME, type="NODES")
    modifier.node_group = node_group
    _set_modifier_input(modifier, "Emission Rate", float(emitter.emission_rate))
    _set_modifier_input(modifier, "Max Particles", int(emitter.max_particles))
    _set_modifier_input(modifier, "Lifetime", float(emitter.lifetime))
    _set_modifier_input(modifier, "Start Size", float(emitter.start_size))
    _set_modifier_input(modifier, "Start Speed", float(emitter.start_speed))
    _set_modifier_input(modifier, "Material", material)

    return empty


def _target_collection(armature_object: Any, context: Any) -> Any:
    assert bpy is not None
    users = getattr(armature_object, "users_collection", None)
    if users:
        return users[0]
    scene = getattr(context, "scene", None)
    if scene is not None and getattr(scene, "collection", None) is not None:
        return scene.collection
    return bpy.context.scene.collection


def _ensure_emitter_material(armature_object: Any, emitter: Any, index: int) -> Any:
    assert bpy is not None
    arm_safe = _safe_token(getattr(armature_object, "name", ""), "Armature")
    emitter_safe = _safe_token(getattr(emitter, "name", ""), f"Emitter")
    mat_name = f"{MATERIAL_NAME_PREFIX}{arm_safe}_{index:03d}_{emitter_safe}"
    material = bpy.data.materials.get(mat_name)
    if material is None:
        material = bpy.data.materials.new(mat_name)
    material.use_nodes = True
    nt = material.node_tree
    if nt is None:
        return material

    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    color = tuple(getattr(emitter, "start_color", (1.0, 1.0, 1.0, 1.0)))
    tint_rgb = (
        float(color[0]),
        float(color[1]),
        float(color[2]),
        1.0,
    )
    tint_alpha = float(color[3]) if len(color) > 3 else 1.0

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)

    emission = nodes.new("ShaderNodeEmission")
    emission.location = (100, 80)
    emission.inputs["Strength"].default_value = 1.0

    transparent = nodes.new("ShaderNodeBsdfTransparent")
    transparent.location = (100, -80)

    mix_shader = nodes.new("ShaderNodeMixShader")
    mix_shader.location = (300, 0)
    # Fac 0 → Transparent, Fac 1 → Emission
    links.new(transparent.outputs["BSDF"], mix_shader.inputs[1])
    links.new(emission.outputs["Emission"], mix_shader.inputs[2])
    links.new(mix_shader.outputs["Shader"], out.inputs["Surface"])

    texture_image = getattr(emitter, "texture", None)
    if texture_image is not None:
        uv = nodes.new("ShaderNodeUVMap")
        uv.location = (-600, 40)
        uv.uv_map = "UVMap"

        tex = nodes.new("ShaderNodeTexImage")
        tex.location = (-400, 40)
        tex.image = texture_image
        tex.interpolation = "Linear"
        tex.extension = "CLIP"
        links.new(uv.outputs["UV"], tex.inputs["Vector"])

        # Color = texture.rgb × startColor.rgb
        mul_color = nodes.new("ShaderNodeMix")
        mul_color.location = (-150, 100)
        mul_color.data_type = "RGBA"
        mul_color.blend_type = "MULTIPLY"
        factor = next(s for s in mul_color.inputs if s.identifier == "Factor_Float")
        factor.default_value = 1.0
        a_col = next(s for s in mul_color.inputs if s.identifier == "A_Color")
        b_col = next(s for s in mul_color.inputs if s.identifier == "B_Color")
        result_col = next(
            s for s in mul_color.outputs if s.identifier == "Result_Color"
        )
        links.new(tex.outputs["Color"], a_col)
        b_col.default_value = tint_rgb
        links.new(result_col, emission.inputs["Color"])

        # Alpha = texture.a × startColor.a
        mul_alpha = nodes.new("ShaderNodeMath")
        mul_alpha.location = (-150, -80)
        mul_alpha.operation = "MULTIPLY"
        links.new(tex.outputs["Alpha"], mul_alpha.inputs[0])
        mul_alpha.inputs[1].default_value = tint_alpha
        links.new(mul_alpha.outputs["Value"], mix_shader.inputs["Fac"])
    else:
        emission.inputs["Color"].default_value = tint_rgb
        mix_shader.inputs["Fac"].default_value = tint_alpha

    _configure_material_transparency(material)
    if hasattr(material, "use_backface_culling"):
        material.use_backface_culling = False
    return material


def _configure_material_transparency(material: Any) -> None:
    """Enable alpha blending for particle quads (EEVEE / Blender 4.2–5.x)."""
    if hasattr(material, "blend_method"):
        try:
            material.blend_method = "BLEND"
        except TypeError:
            try:
                material.blend_method = "HASHED"
            except TypeError:
                pass
    if hasattr(material, "surface_render_method"):
        try:
            material.surface_render_method = "BLENDED"
        except TypeError:
            pass


def _set_modifier_input(modifier: Any, identifier: str, value: Any) -> None:
    """Set a Geometry Nodes modifier input by socket name (Blender 4.x/5.x)."""
    # Blender 4.2+: modifier[identifier] with socket identifier from interface.
    node_group = getattr(modifier, "node_group", None)
    if node_group is None:
        return

    socket_identifier = None
    iface = getattr(node_group, "interface", None)
    if iface is not None:
        for item in iface.items_tree:
            if getattr(item, "in_out", None) != "INPUT":
                continue
            if getattr(item, "name", None) == identifier:
                socket_identifier = getattr(item, "identifier", None)
                break

    keys_to_try = []
    if socket_identifier:
        keys_to_try.append(socket_identifier)
    keys_to_try.append(identifier)

    for key in keys_to_try:
        try:
            modifier[key] = value
            return
        except (KeyError, TypeError, ValueError):
            continue

    # Fallback: iterate modifier keys
    for key in list(getattr(modifier, "keys", lambda: [])()):
        if identifier.lower().replace(" ", "_") in str(key).lower():
            try:
                modifier[key] = value
                return
            except (KeyError, TypeError, ValueError):
                continue
    logger.debug("Could not set GeoNodes input %r on modifier", identifier)


__all__ = [
    "ARMATURE_PREVIEW_ID_PROP",
    "EXCLUDE_FROM_EXPORT_CUSTOM_PROP",
    "MATERIAL_NAME_PREFIX",
    "MODIFIER_NAME",
    "NODE_GROUP_NAME",
    "OBJECT_NAME_PREFIX",
    "PREVIEW_ARMATURE_PROP",
    "PREVIEW_CUSTOM_PROP",
    "PREVIEW_EMITTER_PROP",
    "clear_vfx_preview",
    "ensure_particle_node_group",
    "is_preview_object",
    "preview_object_name",
    "rebuild_vfx_preview",
]
