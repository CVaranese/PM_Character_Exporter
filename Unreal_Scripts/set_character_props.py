"""
Set top-level properties on a character data Blueprint (CD_<Name>) class default object.

DRY RUN BY DEFAULT: R2_APPLY=1 to change anything. Run with Unreal_Scripts/run_ue_python.py.

Env vars:
    R2_CD      CD asset path (default /Game/ModContent/3729910023/UnrealAssets/CD_Captain)
    R2_SET     semicolon-separated name=value pairs (Python property names), e.g.
               "hurtboxes_physics_asset=/Game/ModContent/3729910023/UnrealAssets/HB_Captain;head_bone_name=HeadN"
               Values starting with /Game/ are loaded as assets; "None" clears; anything else is used as given
               (converted to the property's current type for names/numbers/bools).
    R2_APPLY   "1" to apply
"""

import os
from pathlib import Path

import unreal

CD = os.environ.get("R2_CD", "/Game/ModContent/3729910023/UnrealAssets/CD_Captain")
PAIRS = [p.split("=", 1) for p in os.environ.get("R2_SET", "").split(";") if "=" in p]
APPLY = os.environ.get("R2_APPLY") == "1"
REPORT = Path(__file__).resolve().parent / "set_character_props_report.txt"

eal = unreal.EditorAssetLibrary
lines = []


def log(msg):
    lines.append(msg)
    unreal.log(msg)


def show(v):
    return v.get_path_name() if isinstance(v, unreal.Object) else str(v)


def convert(raw, current):
    raw = raw.strip()
    if raw == "None":
        return None
    if raw.startswith("/Game/"):
        obj = eal.load_asset(raw)
        if obj is None:
            raise ValueError(f"asset not found: {raw}")
        return obj
    if isinstance(current, unreal.Name):
        return unreal.Name(raw)
    if isinstance(current, bool):
        return raw.lower() in ("1", "true", "yes")
    if isinstance(current, int):
        return int(raw)
    if isinstance(current, float):
        return float(raw)
    return raw


def main():
    log(f"mode: {'APPLY' if APPLY else 'DRY RUN'}   CD: {CD}")
    if not PAIRS:
        log("ERROR: R2_SET is empty")
        return
    cdo = unreal.get_default_object(eal.load_blueprint_class(CD))
    changes = []
    for name, raw in PAIRS:
        name = name.strip()
        current = cdo.get_editor_property(name)
        new = convert(raw, current)
        log(f"  {name}: {show(current)} -> {show(new)}")
        changes.append((name, new))
    if not APPLY:
        log("dry run complete: nothing changed")
        return
    for name, new in changes:
        cdo.set_editor_property(name, new)
    log("saved" if eal.save_asset(CD, only_if_is_dirty=False) else "ERROR: save failed")


try:
    main()
finally:
    REPORT.write_text("\n".join(lines) + "\n")
