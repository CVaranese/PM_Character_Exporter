# Claude Instructions

Make sure to do analysis on the change beforehand before implementing anything. In order to minimize assumptions, ask questions before analysis so that I can give you the right answer if it is available.

## Updating documentation

Whenever `convert_hitboxes.py` is modified, update `convert_hitboxes.md` to reflect the change:
- New or removed functions: add or remove the corresponding entry under the correct section heading
- Changed behavior, parameters, or return values: update that function's description
- Changed constants: update the Constants table
- The inline docstring in the Python file and the markdown entry should stay in sync

## Porting docs (`docs/`)

`docs/` holds the end-to-end porting process. Start at `docs/README.md`.
- Whenever a new caveat, gotcha, or workaround is found (in any stage: BrawlCrate, Blender, scripts, Unreal/R2Kit, publishing), add it to `docs/PITFALLS.md` with a stable ID and Symptom → Cause → Fix → Status. Mark entries **Fixed** rather than deleting them.
- When a stage's process or automation level changes, update `docs/PIPELINE.md` and `docs/STATUS.md`.
- When a new external reference is used to answer a question, add it to `docs/SOURCES.md`.
- Never publish the mod or write into the R2Kit mod folder without confirming with the user first; publishing has wiped the mod before (see `docs/RECOVERY.md`).
