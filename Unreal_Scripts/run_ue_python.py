#!/usr/bin/env python3
"""
Run one of this folder's editor Python scripts headless in R2Kit.

One fixed entry point so Claude Code can be given a single, narrow permission rule for it
(see .claude/settings.local.json). Refuses to run while R2Kit is open, and only runs scripts
that live in Unreal_Scripts/.

Usage:
    python -I Unreal_Scripts/run_ue_python.py <script.py> [KEY=VALUE ...]
    python -I Unreal_Scripts/run_ue_python.py set_ledge_grab.py R2_WINDOWS="Active,Special Fall" R2_APPLY=1

Prints the script's report/summary lines and the Python errors from the editor log.
"""

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R2KIT = Path(r"D:\Program Files\Epic Games\R2Kit")
UE_CMD = R2KIT / "Engine" / "Binaries" / "Win64" / "UnrealEditor-Cmd.exe"
UPROJECT = R2KIT / "Project" / "Rivals2.uproject"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    script = (HERE / sys.argv[1]).resolve()
    if script.parent != HERE or script.suffix != ".py" or not script.exists() or script == Path(__file__).resolve():
        sys.exit(f"not a script in {HERE}: {sys.argv[1]}")

    env = dict(os.environ)
    for arg in sys.argv[2:]:
        key, sep, value = arg.partition("=")
        if not sep or not key.startswith("R2_"):
            sys.exit(f"settings must look like R2_NAME=value, got: {arg}")
        env[key] = value

    tasks = subprocess.run(["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe", "/NH"],
                           capture_output=True, text=True).stdout
    if "UnrealEditor.exe" in tasks:
        sys.exit("R2Kit is open: close it first (two editors on one project can corrupt assets)")

    r = subprocess.run([str(UE_CMD), str(UPROJECT), "-run=pythonscript", f"-script={script}",
                        "-unattended", "-nosplash", "-nullrhi"], env=env, capture_output=True, text=True,
                       errors="replace")
    ok = False
    for line in r.stdout.splitlines():
        if "LogPython: Error" in line or "LogPythonScriptCommandlet" in line:
            print(line.split("]", 2)[-1].strip())
        if "Python script executed successfully" in line:
            ok = True
    # The commandlet's exit code is unreliable (unrelated engine errors make it 1), so report
    # success from the log line instead. See docs/PITFALLS.md P-UE-10.
    print("RESULT:", "success" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
