"""
Turn a mod stuck in its published layout back into a normal, editable layout.

    ModContent/<id>/PublishedAssets/...                     -> ModContent/<id>/UnrealAssets/...
    ModContent/<id>/PublishedAssets/References/Game/<path>  -> references repointed to /Game/<path>, copies deleted

See docs/RECOVERY.md. Moves happen through the asset tools so references inside every
.uasset are rewritten. Never move these files on disk.

DRY RUN BY DEFAULT: set R2_APPLY=1 to change anything.

Run inside R2Kit (Tools > Execute Python Script) or headless:
    UnrealEditor-Cmd.exe <Rivals2.uproject> -run=pythonscript -script="<this file>"

Env vars:
    R2_MOD_ROOT   default /Game/ModContent/3729910023
    R2_APPLY      "1" to apply
    R2_REPORT     report file path (default <repo>/Unreal_Scripts/restore_report.txt)
"""

import os
from pathlib import Path

import unreal

MOD_ROOT = os.environ.get("R2_MOD_ROOT", "/Game/ModContent/3729910023")
APPLY = os.environ.get("R2_APPLY") == "1"
REPORT = Path(os.environ.get("R2_REPORT", Path(__file__).resolve().parent / "restore_report.txt"))

SRC = MOD_ROOT + "/PublishedAssets"
DST = MOD_ROOT + "/UnrealAssets"
REF = SRC + "/References/Game"

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lines = []


def log(msg):
    lines.append(msg)
    unreal.log(msg)


def package_of(asset_path):
    return asset_path.split(".")[0]


def split_package(package):
    folder, name = package.rsplit("/", 1)
    return folder, name


def main():
    log(f"mode: {'APPLY' if APPLY else 'DRY RUN'}   mod: {MOD_ROOT}")
    if not eal.does_directory_exist(SRC):
        log(f"nothing to do: {SRC} does not exist")
        return

    assets = [package_of(a) for a in eal.list_assets(SRC, recursive=True, include_folder=False)]
    refs = [p for p in assets if p.startswith(REF + "/")]
    moves = [p for p in assets if not p.startswith(SRC + "/References/")]
    log(f"assets under PublishedAssets: {len(assets)}  (references: {len(refs)}, to move: {len(moves)})")

    # Load everything in the mod first so consolidation/rename can see every referencer.
    for p in assets:
        eal.load_asset(p)

    # 1. Repoint bundled base-game copies to the real base-game assets.
    consolidate = []
    for copy_pkg in refs:
        orig_pkg = "/Game/" + copy_pkg[len(REF) + 1:]
        if not eal.does_asset_exist(orig_pkg):
            log(f"  [REF MISSING ORIGINAL] {copy_pkg} -> {orig_pkg} (left in place)")
            continue
        copy_obj, orig_obj = eal.load_asset(copy_pkg), eal.load_asset(orig_pkg)
        if copy_obj.get_class() != orig_obj.get_class():
            log(f"  [REF CLASS MISMATCH] {copy_pkg} ({copy_obj.get_class().get_name()}) vs "
                f"{orig_pkg} ({orig_obj.get_class().get_name()}) (left in place)")
            continue
        consolidate.append((copy_obj, orig_obj))
    log(f"references to repoint to /Game originals: {len(consolidate)} / {len(refs)}")

    # 2. Move everything else into UnrealAssets, keeping relative folders.
    renames, conflicts = [], []
    for src_pkg in moves:
        folder, name = split_package(src_pkg)
        new_folder = DST + folder[len(SRC):]
        if eal.does_asset_exist(f"{new_folder}/{name}"):
            conflicts.append((src_pkg, f"{new_folder}/{name}"))
            continue
        renames.append(unreal.AssetRenameData(eal.load_asset(src_pkg), new_folder, name))
    log(f"assets to move into UnrealAssets: {len(renames)}")
    for src_pkg, dst_pkg in conflicts:
        log(f"  [CONFLICT] {dst_pkg} already exists; {src_pkg} will be merged into it")

    if not APPLY:
        log("dry run complete: nothing changed")
        return

    for copy_obj, orig_obj in consolidate:
        if not eal.consolidate_assets(orig_obj, [copy_obj]):
            log(f"  [FAILED consolidate] {copy_obj.get_path_name()}")
    for src_pkg, dst_pkg in conflicts:
        eal.consolidate_assets(eal.load_asset(dst_pkg), [eal.load_asset(src_pkg)])

    if not tools.rename_assets(renames):
        log("  [FAILED] rename_assets returned False; check the output log")

    # 3. Fix up any redirectors left behind, then save only the mod's own assets.
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    redirectors = [
        d.get_asset() for d in registry.get_assets_by_path(SRC, recursive=True)
        if d.asset_class_path.asset_name == "ObjectRedirector"
    ]
    if redirectors:
        tools.fixup_referencers(redirectors)
    eal.save_directory(DST, only_if_is_dirty=False, recursive=True)

    remaining = eal.list_assets(SRC, recursive=True, include_folder=False)
    log(f"remaining under PublishedAssets: {len(remaining)}")
    for a in remaining:
        log(f"  {a}")
    if not remaining:
        eal.delete_directory(SRC)
        log("deleted empty PublishedAssets")


try:
    main()
finally:
    REPORT.write_text("\n".join(lines) + "\n")
