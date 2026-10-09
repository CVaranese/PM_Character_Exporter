#!/usr/bin/env python3
"""
Back up an R2Kit mod into its own git repo before publishing. Publishing has wiped the mod before:
see docs/PITFALLS.md P-UE-0 and docs/RECOVERY.md.

What it does:
  1. Safety checks: refuses if the mod looks wiped (no UnrealAssets, a PublishedAssets folder left by a
     publish, or far fewer assets than the last backup). Use --force to override.
  2. Mirrors ModId.json, Scripts/ and UnrealAssets/ into <backup repo>/mod/.
  3. If R2Kit is closed, dumps every data asset to JSON in <backup repo>/data/ (readable, diffable values).
     If R2Kit is open, the dump is skipped and the binary mirror is still committed.
  4. Commits, and pushes if the repo has a remote.

Usage (defaults are Captain Falcon's):
    python backup_mod.py
    python backup_mod.py -m "before publish: new up-b"
    python backup_mod.py --mod-id 3729910023 --backup-repo D:/git_repos/R2_Captain_Falcon
"""

import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

R2KIT = Path(r"D:\Program Files\Epic Games\R2Kit")
UE_CMD = R2KIT / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"
UPROJECT = R2KIT / "Project" / "Rivals2.uproject"
DUMP_SCRIPT = Path(__file__).resolve().parent / "dump_mod_assets.py"

MIN_RATIO = 0.5  # refuse if UnrealAssets has fewer than this fraction of the last backup's assets


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def git(repo, *args):
    r = run(["git", "-C", str(repo), *args])
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{r.stderr}")
    return r.stdout.strip()


def count_uassets(folder):
    return sum(1 for _ in folder.rglob("*.uasset")) if folder.exists() else 0


def editor_running():
    r = run(["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe", "/NH"])
    return "UnrealEditor.exe" in r.stdout


def mirror(src, dst):
    """robocopy /MIR: dst becomes an exact copy of src (removed files are removed; git keeps history)."""
    r = run(["robocopy", str(src), str(dst), "/MIR", "/NFL", "/NDL", "/NJH", "/NJS", "/NP", "/R:2", "/W:1"])
    if r.returncode >= 8:  # robocopy: 0-7 = success variants
        sys.exit(f"robocopy {src} -> {dst} failed ({r.returncode}):\n{r.stdout}{r.stderr}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mod-id", default="3729910023")
    ap.add_argument("--backup-repo", default=r"D:\git_repos\R2_Captain_Falcon")
    ap.add_argument("-m", "--message", default="", help="extra text for the commit message")
    ap.add_argument("--force", action="store_true", help="skip the 'mod looks wiped' safety checks")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    mod = R2KIT / "Project" / "Content" / "ModContent" / args.mod_id
    repo = Path(args.backup_repo)
    if not (repo / ".git").exists():
        sys.exit(f"{repo} is not a git repo; create it first (see docs/PIPELINE.md stage 8)")

    # 1. Safety checks
    current = count_uassets(mod / "UnrealAssets")
    previous = count_uassets(repo / "mod" / "UnrealAssets")
    problems = []
    if not mod.exists():
        problems.append(f"mod folder not found: {mod}")
    if current == 0:
        problems.append("UnrealAssets is empty or missing")
    if (mod / "PublishedAssets").exists() or (mod / "PublishAssets").exists():
        problems.append("a PublishedAssets/PublishAssets folder exists: a publish may be in progress or failed")
    if previous and current < previous * MIN_RATIO:
        problems.append(f"UnrealAssets has {current} assets vs {previous} in the last backup")
    if problems and not args.force:
        sys.exit("REFUSING TO BACK UP: the mod may have been wiped. Recover it first (docs/RECOVERY.md).\n  - "
                 + "\n  - ".join(problems) + "\nRe-run with --force only if this state is intended.")
    for p in problems:
        print(f"WARNING (forced): {p}")

    # 2. Mirror files
    dest = repo / "mod"
    dest.mkdir(exist_ok=True)
    for name in ("UnrealAssets", "Scripts"):
        if (mod / name).exists():
            mirror(mod / name, dest / name)
    (dest / "ModId.json").write_bytes((mod / "ModId.json").read_bytes())
    print(f"mirrored {current} assets from {mod}")

    # 3. Text dump (needs R2Kit closed)
    dump_note = "data dump skipped (R2Kit was open)"
    if editor_running():
        print("R2Kit is open: skipping the JSON data dump (binary backup still committed)")
    else:
        env = dict(os.environ, R2_MOD_ROOT=f"/Game/ModContent/{args.mod_id}", R2_DUMP_DIR=str(repo / "data"))
        summary = repo / "data" / "_dump_summary.txt"
        started = datetime.datetime.now().timestamp()
        run([str(UE_CMD), str(UPROJECT), "-run=pythonscript", f"-script={DUMP_SCRIPT}",
             "-unattended", "-nosplash", "-nullrhi"], env=env)
        # Don't trust the exit code: unrelated engine errors (e.g. a gamepad driver) make it 1 even when
        # the script succeeded. The summary file is written last, so a fresh one means the dump finished.
        if summary.exists() and summary.stat().st_mtime >= started:
            dump_note = summary.read_text().strip().replace("\n", "; ")
            print(f"data dump: {dump_note}")
        else:
            dump_note = "data dump FAILED (see Saved/Logs in R2Kit)"
            print(f"WARNING: {dump_note}")

    # 4. Commit + push
    git(repo, "add", "-A")
    if not git(repo, "status", "--porcelain"):
        print("no changes since the last backup")
        return
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"Backup {stamp}" + (f": {args.message}" if args.message else "")
    git(repo, "commit", "-q", "-m", title, "-m", f"{current} assets; {dump_note}")
    print(f"committed: {git(repo, 'log', '-1', '--format=%h %s')}")

    if args.no_push:
        return
    if not git(repo, "remote"):
        print("no git remote set: backup is local only (add one with: git remote add origin <url>)")
        return
    r = run(["git", "-C", str(repo), "push", "-q", "-u", "origin", "HEAD"])
    print("pushed" if r.returncode == 0 else f"WARNING: push failed:\n{r.stderr}")


if __name__ == "__main__":
    main()
