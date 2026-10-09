"""
Workaround for the publish crash in docs/PITFALLS.md P-UE-12.

Publishing crashes while copying the base-game shield materials (MF_Cha_Shield_VertexOffsetShake /
T_Cha_ShieldOffset_M). The mod only reaches them through the skin's shield_mesh (SK_Cha_Shield). This script:
  1. duplicates SK_Cha_Shield into the mod (UnrealAssets/Shield/SK_<Code>_Shield),
  2. replaces every material slot on the copy with a material the mod already uses (default: MI_<Code>_Body),
     so the shield chain is no longer referenced. The shield will look like the body material,
  3. duplicates the shield skeleton too, points the copy's preview mesh at our mesh copy, and switches the mesh
     copy to it. The original skeleton (and PH_Cha_Shield) keep a preview-mesh link back to SK_Cha_Shield,
     which made the publish pull the whole chain back in (second crash, 2026-10-09),
  4. removes the physics asset from the mesh copy (PH_Cha_Shield's preview link can't be edited from Python),
  5. points the skin's shield_mesh at the copy.
Verify afterwards on disk that nothing in the mod references /Game/Characters/Shared/Shield/ at all.

Undo: set the skin's shield_mesh back to /Game/Characters/Shared/Shield/SK_Cha_Shield and delete UnrealAssets/Shield.

DRY RUN BY DEFAULT: R2_APPLY=1 to change anything. Run with Unreal_Scripts/run_ue_python.py.

Env vars (defaults are Falcon's):
    R2_MOD_ROOT    /Game/ModContent/3729910023/UnrealAssets
    R2_CHAR_CODE   Cap
    R2_SKIN        <mod root>/Skins/Default/Data/Skin_Cap_Default
    R2_MATERIAL    <mod root>/Skins/Default/MI_Cap_Body
    R2_APPLY       "1" to apply
"""

import os
from pathlib import Path

import unreal

MOD = os.environ.get("R2_MOD_ROOT", "/Game/ModContent/3729910023/UnrealAssets")
CODE = os.environ.get("R2_CHAR_CODE", "Cap")
SKIN = os.environ.get("R2_SKIN", f"{MOD}/Skins/Default/Data/Skin_{CODE}_Default")
MATERIAL = os.environ.get("R2_MATERIAL", f"{MOD}/Skins/Default/MI_{CODE}_Body")
APPLY = os.environ.get("R2_APPLY") == "1"

SRC_MESH = "/Game/Characters/Shared/Shield/SK_Cha_Shield"
DST_MESH = f"{MOD}/Shield/SK_{CODE}_Shield"
SRC_SKEL = "/Game/Characters/Shared/Shield/Animation/SK_VFX_Shield_skeleton"
DST_SKEL = f"{MOD}/Shield/SK_{CODE}_Shield_Skeleton"
REPORT = Path(__file__).resolve().parent / "local_shield_fix_report.txt"
BAD = ("/Shield/MI_", "/Shield/MAT_", "MF_Cha_Shield", "T_Cha_ShieldOffset", "MI_Zet_DefaultShield")

eal = unreal.EditorAssetLibrary
registry = unreal.AssetRegistryHelpers.get_asset_registry()
lines = []


def log(msg):
    lines.append(msg)
    unreal.log(msg)


def deps(package):
    opts = unreal.AssetRegistryDependencyOptions(
        include_soft_package_references=True, include_hard_package_references=True,
        include_searchable_names=False, include_soft_management_references=False,
        include_hard_management_references=False)
    return sorted(str(d) for d in (registry.get_dependencies(package, opts) or []))


def main():
    log(f"mode: {'APPLY' if APPLY else 'DRY RUN'}")
    material = eal.load_asset(MATERIAL)
    skin_cls = eal.load_blueprint_class(SKIN)
    if material is None or skin_cls is None:
        log(f"ERROR: missing material ({MATERIAL}) or skin ({SKIN})")
        return
    skin = unreal.get_default_object(skin_cls)
    current = skin.get_editor_property("shield_mesh")
    log(f"skin shield_mesh now: {current.get_path_name() if current else None}")
    log(f"source mesh deps: {deps(SRC_MESH)}")

    src = eal.load_asset(SRC_MESH)
    slots = list(src.get_editor_property("materials"))
    for i, s in enumerate(slots):
        mi = s.get_editor_property("material_interface")
        log(f"  slot {i} '{s.get_editor_property('material_slot_name')}': {mi.get_path_name() if mi else None}")
    if not APPLY:
        log(f"dry run: would duplicate to {DST_MESH}, set {len(slots)} slots to {MATERIAL}, repoint skin")
        return

    if eal.does_asset_exist(DST_MESH):
        log(f"{DST_MESH} already exists; reusing it")
        mesh = eal.load_asset(DST_MESH)
    else:
        mesh = eal.duplicate_asset(SRC_MESH, DST_MESH)
        if mesh is None:
            log("ERROR: duplicate failed")
            return
    new_slots = []
    for s in mesh.get_editor_property("materials"):
        s.set_editor_property("material_interface", material)
        new_slots.append(s)
    mesh.set_editor_property("materials", new_slots)

    skel = eal.load_asset(DST_SKEL) if eal.does_asset_exist(DST_SKEL) else eal.duplicate_asset(SRC_SKEL, DST_SKEL)
    if skel is None:
        log("ERROR: skeleton duplicate failed")
        return
    skel.set_skeleton_preview_mesh(mesh)
    skel.set_skeleton_additional_preview_meshes(None)
    # SkeletalMesh.skeleton is read-only from Python, so the swap is a manual step in R2Kit:
    # right-click the mesh copy > Assign Skeleton > pick the skeleton copy, then save.
    mesh.set_editor_property("physics_asset", None)
    current_skel = mesh.get_editor_property("skeleton").get_path_name()
    log(f"mesh physics_asset -> {mesh.get_editor_property('physics_asset')}; skeleton is {current_skel}")
    if not current_skel.startswith(DST_SKEL):
        log(f"MANUAL STEP: in R2Kit right-click {DST_MESH} > Assign Skeleton > {DST_SKEL}, then Save")

    for path in (DST_SKEL, DST_MESH):
        if not eal.save_asset(path, only_if_is_dirty=False):
            log(f"ERROR: saving {path} failed")
            return

    skin.set_editor_property("shield_mesh", mesh)
    if not eal.save_asset(SKIN, only_if_is_dirty=False):
        log("ERROR: saving skin failed")
        return
    log(f"skin shield_mesh -> {mesh.get_path_name()}")

    copy_deps = deps(DST_MESH)
    log(f"copy deps: {copy_deps}")
    leftovers = [d for d in copy_deps if any(b in d for b in BAD)]
    log("OK: no shield materials referenced" if not leftovers else f"WARNING: still references {leftovers}")


try:
    main()
finally:
    REPORT.write_text("\n".join(lines) + "\n")
