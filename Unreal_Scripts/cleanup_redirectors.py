"""
Finish a layout restore: re-save assets that still mention an old folder, then delete
redirectors under that folder once nothing references them.

(UE 5.8's Python AssetTools has no fixup_referencers, so this does the equivalent.)

DRY RUN BY DEFAULT: set R2_APPLY=1 to change anything.

Env vars:
    R2_MOD_ROOT   default /Game/ModContent/3729910023
    R2_OLD_DIR    folder being emptied (default <mod root>/PublishedAssets)
    R2_APPLY      "1" to apply
"""

import os
from pathlib import Path

import unreal

MOD_ROOT = os.environ.get("R2_MOD_ROOT", "/Game/ModContent/3729910023")
OLD_DIR = os.environ.get("R2_OLD_DIR", MOD_ROOT + "/PublishedAssets")
APPLY = os.environ.get("R2_APPLY") == "1"
REPORT = Path(__file__).resolve().parent / "restore_report.txt"

eal = unreal.EditorAssetLibrary
registry = unreal.AssetRegistryHelpers.get_asset_registry()
lines = []


def log(msg):
    lines.append(msg)
    unreal.log(msg)


def referencers(package):
    opts = unreal.AssetRegistryDependencyOptions(
        include_soft_package_references=True, include_hard_package_references=True,
        include_searchable_names=False, include_soft_management_references=False,
        include_hard_management_references=False)
    return [str(r) for r in (registry.get_referencers(package, opts) or [])]


def main():
    log(f"cleanup mode: {'APPLY' if APPLY else 'DRY RUN'}   old dir: {OLD_DIR}")
    if not eal.does_directory_exist(OLD_DIR):
        log("nothing to do")
        return

    old = [d for d in registry.get_assets_by_path(OLD_DIR, recursive=True)]
    redirectors = [str(d.package_name) for d in old if d.asset_class_path.asset_name == "ObjectRedirector"]
    others = [str(d.package_name) for d in old if d.asset_class_path.asset_name != "ObjectRedirector"]
    log(f"under old dir: {len(redirectors)} redirectors, {len(others)} other assets")
    for p in others:
        log(f"  [NOT A REDIRECTOR, will not delete] {p}")

    # Anything outside the old dir that still references something inside it gets re-saved,
    # which rewrites its stored paths through the (loaded) redirectors.
    to_resave = sorted({r for p in redirectors for r in referencers(p) if not r.startswith(OLD_DIR)})
    log(f"referencers to re-save: {len(to_resave)}")
    for r in to_resave:
        log(f"  {r}")

    if not APPLY:
        log("dry run complete: nothing changed")
        return

    for r in to_resave:
        eal.load_asset(r)
        if not eal.save_asset(r, only_if_is_dirty=False):
            log(f"  [FAILED save] {r}")

    still = {p: [r for r in referencers(p) if not r.startswith(OLD_DIR)] for p in redirectors}
    blocked = {p: rs for p, rs in still.items() if rs}
    for p, rs in blocked.items():
        log(f"  [STILL REFERENCED, kept] {p} <- {rs}")
    if blocked or others:
        log("old dir not deleted")
        return
    eal.delete_directory(OLD_DIR)
    log(f"deleted {OLD_DIR}")


try:
    main()
finally:
    REPORT.write_text("\n".join(lines) + "\n")
