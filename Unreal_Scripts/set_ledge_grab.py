"""
Enable (or disable) ledge grabbing on specific windows of an attack.

R2 only lets a character grab ledge during an attack on windows whose
LedgeProperties.CanGrabLedgeOnFrame >= 0 (-1 = never). See docs/PITFALLS.md P-MOVE-11.

Attack data assets are Blueprints, so this edits the generated class's default object and saves
the Blueprint.

DRY RUN BY DEFAULT: set R2_APPLY=1 to change anything. R2Kit must be closed when run headless:
    UnrealEditor-Cmd.exe <Rivals2.uproject> -run=pythonscript -script="<this file>"

Env vars:
    R2_ATTACK    attack asset path   (default /Game/ModContent/3729910023/UnrealAssets/Attacks/ATT_Cap_Uspecial)
    R2_WINDOWS   comma-separated window names (StringTableKey)   (default "Recovery Down,Special Fall")
    R2_FRAME     CanGrabLedgeOnFrame value, relative to window start; -1 disables   (default 0)
    R2_APPLY     "1" to apply
"""

import os
from pathlib import Path

import unreal

ATTACK = os.environ.get("R2_ATTACK", "/Game/ModContent/3729910023/UnrealAssets/Attacks/ATT_Cap_Uspecial")
WINDOWS = [w.strip() for w in os.environ.get("R2_WINDOWS", "Recovery Down,Special Fall").split(",") if w.strip()]
FRAME = int(os.environ.get("R2_FRAME", "0"))
APPLY = os.environ.get("R2_APPLY") == "1"
REPORT = Path(__file__).resolve().parent / "set_ledge_grab_report.txt"

eal = unreal.EditorAssetLibrary
lines = []


def log(msg):
    lines.append(msg)
    unreal.log(msg)


def main():
    log(f"mode: {'APPLY' if APPLY else 'DRY RUN'}   attack: {ATTACK}   windows: {WINDOWS}   frame: {FRAME}")
    gen = eal.load_blueprint_class(ATTACK)
    if gen is None:
        log("ERROR: attack Blueprint not found")
        return
    cdo = unreal.get_default_object(gen)
    windows = list(cdo.get_editor_property("windows"))

    found = set()
    for i, w in enumerate(windows):
        name = str(w.get_editor_property("string_table_key"))
        ledge = w.get_editor_property("ledge_properties")
        old = ledge.get_editor_property("can_grab_ledge_on_frame")
        if name in WINDOWS:
            found.add(name)
            ledge.set_editor_property("can_grab_ledge_on_frame", FRAME)
            w.set_editor_property("ledge_properties", ledge)
            windows[i] = w
            log(f"  [{i}] {name}: CanGrabLedgeOnFrame {old} -> {FRAME}")
        else:
            log(f"  [{i}] {name}: CanGrabLedgeOnFrame {old} (unchanged)")

    missing = [w for w in WINDOWS if w not in found]
    if missing:
        log(f"ERROR: windows not found: {missing}; nothing changed")
        return
    if not APPLY:
        log("dry run complete: nothing changed")
        return

    cdo.set_editor_property("windows", windows)
    if eal.save_asset(ATTACK, only_if_is_dirty=False):
        log("saved")
    else:
        log("ERROR: save failed")


try:
    main()
finally:
    REPORT.write_text("\n".join(lines) + "\n")
