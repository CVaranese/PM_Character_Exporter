"""
Dump every data asset / Blueprint in a mod folder to JSON so their values (CD_, ATT_, HB_, ...)
live in git as readable, diffable text.

For Blueprints (CD_, ATT_, ...) the values live on the generated class's default object, so that
is what gets dumped. Struct values use Unreal's own text format (the same format as right-click >
Copy in the details panel), so they can be pasted back.

Run inside R2Kit (Tools > Execute Python Script) or headless:
    UnrealEditor-Cmd.exe <Rivals2.uproject> -run=pythonscript -script="<this file>"

Config via environment variables (defaults are Falcon's):
    R2_MOD_ROOT   content path to dump      (default /Game/ModContent/3729910023)
    R2_DUMP_DIR   output folder on disk     (default <repo>/character_dumps/Captain)
"""

import json
import os
import re
from pathlib import Path

import unreal

MOD_ROOT = os.environ.get("R2_MOD_ROOT", "/Game/ModContent/3729910023")
DUMP_DIR = Path(os.environ.get(
    "R2_DUMP_DIR", Path(__file__).resolve().parent.parent / "character_dumps" / "Captain"))

# Binary-heavy or engine-owned classes that aren't worth dumping as text.
SKIP_CLASSES = {
    "AnimSequence", "SkeletalMesh", "StaticMesh", "Skeleton", "Texture2D",
    "Material", "MaterialFunction", "CurveFloat", "CurveLinearColor", "CurveLinearColorAtlas",
    "LevelSequence", "SoundWave", "UserDefinedEnum", "World",
}

eal = unreal.EditorAssetLibrary
PROP_RE = re.compile(r"^\s*-\s*``(\w+)``\s*\(([^)]*)\)", re.MULTILINE)


def editor_property_names(obj):
    """Unreal's generated Python docstrings list every editor property; parse them out."""
    names = []
    for klass in type(obj).__mro__:
        doc = klass.__doc__ or ""
        if "Editor Properties" not in doc:
            continue
        section = doc.split("Editor Properties", 1)[1]
        names += [m.group(1) for m in PROP_RE.finditer(section)]
    return list(dict.fromkeys(names))


def to_text(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, unreal.Name) or isinstance(value, unreal.Text):
        return str(value)
    if isinstance(value, unreal.EnumBase):
        return value.name
    if isinstance(value, unreal.StructBase):
        return value.export_text()
    if isinstance(value, unreal.Object):
        return value.get_path_name()
    if isinstance(value, (unreal.Array, list, tuple, unreal.Set)):
        return [to_text(v) for v in value]
    if isinstance(value, unreal.Map):
        return {str(to_text(k)): to_text(v) for k, v in value.items()}
    return str(value)


def dump_object(obj):
    props, errors = {}, {}
    for name in editor_property_names(obj):
        try:
            props[name] = to_text(obj.get_editor_property(name))
        except Exception as e:  # some properties aren't readable from Python
            errors[name] = str(e)
    return props, errors


def main():
    # Clear previous dump files (not folders, which may be held open by other processes).
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    for old in list(DUMP_DIR.rglob("*.json")) + list(DUMP_DIR.rglob("*.t3d")):
        old.unlink()

    assets = eal.list_assets(MOD_ROOT, recursive=True, include_folder=False)
    ok, skipped, failed = 0, 0, []
    for asset_path in assets:
        package = asset_path.split(".")[0]
        if "/References/" in package:
            skipped += 1
            continue
        obj = eal.load_asset(asset_path)
        if obj is None:
            failed.append((asset_path, "load failed"))
            continue
        cls_name = obj.get_class().get_name()
        if cls_name in SKIP_CLASSES:
            skipped += 1
            continue

        target, kind = obj, cls_name
        if isinstance(obj, unreal.Blueprint):
            gen = eal.load_blueprint_class(package)
            if gen is None:
                failed.append((asset_path, "no generated class"))
                continue
            target = unreal.get_default_object(gen)
            kind = f"Blueprint CDO ({target.get_class().get_name()})"

        props, errors = dump_object(target)
        rel = package[len(MOD_ROOT):].lstrip("/")
        out = DUMP_DIR / (rel + ".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(
            {"asset": package, "kind": kind, "properties": props, "unreadable": errors},
            indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        ok += 1

    summary = [f"mod root: {MOD_ROOT}", f"dumped: {ok}", f"skipped: {skipped}", f"failed: {len(failed)}"]
    summary += [f"  {p}: {why}" for p, why in failed]
    (DUMP_DIR / "_dump_summary.txt").write_text("\n".join(summary) + "\n")
    for line in summary:
        unreal.log(line)


main()
