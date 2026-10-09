# Pipeline: Brawl/PM character → Rivals 2 mod

Each stage lists **inputs → outputs**, the current way it's done, and the automation target. Pitfalls are
linked by ID (e.g. [P-ANIM-1](PITFALLS.md#p-anim-1)). Read them before running the stage.

```
 PM files (.pac/.brres)        PM move scripts (text)
        │                              │
  [1] BrawlCrate extract         [4] convert_hitboxes.py ──► per-move paste files (01–05)
        │                              │
  [2] Blender: model prep        [5] attributes (r2_attribs)
  [3] Blender: animations        [6] movement fitting (fit_transn)
        │ FBX                          │ text / values
        └──────────────► [7] Unreal (R2Kit) ◄──────┘
                                │
                         [8] playtest → BACKUP → publish
```

Automation levels: **Manual** · **Script** (run by hand) · **Auto** (part of a one-shot run).

---

## 0. Per-character setup

| Value | Falcon | Where it's used today |
|---|---|---|
| Character code (3 letters) | `Cap` | `AN_Cap_*` names, `--char-code`, batch_export `anim_prefix` |
| Mod ID | `3729910023` | asset paths in `--mod-id`, `update_animations.py` |
| Bone table | `bones.csv` | `convert_hitboxes.py` (PM uses bone *indices*) |
| Grab release velocity X | `-12.5` | `GRAB_RELEASE_VELOCITY_X` constant ([P-MOVE-9](PITFALLS.md#p-move-9)) |
| Source data folder | `D:\ROA2_Modding\character_data\Captain_falcon` | hardcoded in several scripts |

**Target:** one `characters/<name>.json` config file read by every script, with no hardcoded paths.

---

## 1. Extract from Brawl/PM (BrawlCrate)

**Inputs:** `FitCaptain.pac`, `FitCaptain00.pac`/`.mdl0`, `FitCaptainMotionEtc.pac`, `Model Data [0].brres`
**Outputs:** `FitCaptain00.dae` (+ `.mdl0`), textures (`cap_body.png`, …), `animations/*` (BrawlBox anim), `bones.csv`

1. Open the model in BrawlCrate. Export as **MDL0** and **DAE**.
2. Export animations with the BrawlCrate plugin `Loaders/Animations/export_to_anim.py` ("Export to ROA Anim").
   It writes an `animations/` folder. The TransN bone is disabled in this export ([P-ANIM-2](PITFALLS.md#p-anim-2)).
3. Export the bone index → name/parent table to `bones.csv`.
4. Copy each move's PM script (the `AsyncWait` / `CreateHitBox(HitBoxArguments {…})` text) into an input file
   for stage 4.

**Automation: Manual + Script.** BrawlCrate plugins run inside the BrawlCrate GUI.
Move scripts are copied by hand from Rukai Data. Planned replacement: read the `.pac` files directly
([STATUS FE-1](STATUS.md#future-enhancements)).
**Target:** check whether BrawlCrate can run plugins headless. Otherwise this stays a single manual "export
everything" click per character.

---

## 2. Blender: model prep (Blender 3.6 today; 4.x trial planned, see [STATUS](STATUS.md))

**Inputs:** `FitCaptain00.dae` · **Outputs:** sized model `.blend` + mesh FBX

1. Import the DAE (Collada importer; [P-BLEND-1](PITFALLS.md#p-blend-1)).
2. Set unit scale to **0.01**, rotate **90° on Y**, scale **10.33** on all axes ([P-SCALE-1](PITFALLS.md#p-scale-1)).
3. `Ctrl+A` → apply all transforms **to deltas**.
4. Rename bone `ThrowN` → **`Grab_M`** ([P-MODEL-1](PITFALLS.md#p-model-1)).
5. Clean up for Unreal ([P-MODEL-2](PITFALLS.md#p-model-2)): no non-uniform scale on joints that have
   children, segment scale compensation off, smooth shading, no custom normals.
6. Export FBX.

Existing outputs: `Output/Captain_Sized_No_Trans.blend`, `Captain_Trans_to_deltas.fbx`, etc.

**Automation: Manual.** **Target: Auto** (headless `blender --background --python`). Every step above can be
done with `bpy`.

---

## 3. Blender: animations

**Inputs:** sized model `.blend`, `animations/` from stage 1 · **Outputs:** one `AN_Cap_<PMName>.fbx` per animation

1. Set the scene framerate to **60 fps** *before* importing.
2. *(Optional, clean re-import)* clear existing actions: `helper_functions.clean_actions()`.
3. Import animations with the **Import BrawlBox Animation** plugin.
4. Push all actions to the NLA stack: `helper_functions.push_all_actions()`.
5. Merge multi-part moves into one action with `merge_actions.py`, following R2 conventions
   ([P-ANIM-3](PITFALLS.md#p-anim-3)):
   - jab 1–2–3 → `Attack1F`
   - angled tilts/strongs → fwd + down + up concatenated (`AttackS3F`, `AttackS4F`)
   - charged strongs → Start + Hold + attack (`AttackHi4F`, `AttackLw4F`, `AttackS4F`)
6. Fix animations that turn the character around ([P-ANIM-4](PITFALLS.md#p-anim-4)): `Turn`, `TurnRun`,
   `TurnRunBrake`, `CatchTurn`, `SpecialNTurn`, `SpecialAirNTurn`.
7. Batch export: `batch_export.py` (prefix `AN_Cap_`, output `p+falcon/exported_animations/`).

**Automation: Script** (run inside the Blender GUI). **Target: Auto**, headless.

---

## 4. Move data → R2 attack paste files

**Inputs:** per-move PM script text, `bones.csv` · **Outputs:** `./<Move>/01_Animations.txt` … `05_ThrowData.txt`

```bash
python convert_hitboxes.py temp_attack.txt --move-name AttackAirB --char-code Cap --mod-id 3729910023
python convert_hitboxes.py temp_attack.txt --move-name AttackS3F --angled
python convert_hitboxes.py temp_start.txt  --move-name AttackS4F --charged [--angled]
```

The converter picks a pipeline in this order: angled+charged → angled → charged → start/end → grab → regular.
See [`convert_hitboxes.md`](../convert_hitboxes.md) for details.

What it converts:
- distances × **10.666** ([P-SCALE-1](PITFALLS.md#p-scale-1))
- bone index → name
- knockback via `kb_calc.py` ([P-MOVE-1](PITFALLS.md#p-move-1))
- angle 361 → 45 ([P-MOVE-2](PITFALLS.md#p-move-2))
- AsyncWait/SyncWait → windows ([P-MOVE-3](PITFALLS.md#p-move-3))
- `EnableLandingLag` → auto-cancel ([P-MOVE-4](PITFALLS.md#p-move-4))

**Automation: Script**, run once per move with hand-made input files.
**Target: Auto.** Batch every move from a manifest (move name → flags, frames, landing lag, R2 attack slot),
and write directly into ATT_ assets in stage 7 instead of producing paste files.

---

## 5. Character attributes

**Inputs:** PM attributes · **Outputs:** CD_ attribute values

- `r2_attribs.txt` is a copy/paste dump of the CD_ attributes (`General` → `Weight`, `ECBDimensions`,
  `EcbBones`, …).
- `attribs_sheets.py` converts it to and from TSV so it can be edited in Google Sheets
  ([`r2_attribs_usage.md`](../r2_attribs_usage.md)).
- The PM → R2 attribute mapping was done **by hand and is not written down** ([P-ATTR-1](PITFALLS.md#p-attr-1)).
  Recover the values from the restored `CD_Captain` (see [RECOVERY.md](RECOVERY.md)).

**Automation: Manual.** **Target:** a documented mapping table (PM attribute → R2 attribute → formula),
then Auto.

---

## 6. Movement fitting (specials, root motion)

**Inputs:** `transn_keyframes.csv` (TransN bone keyframes per animation) · **Outputs:** velocities/gravity for window `VelocityData` / `MovementProperties`

PM moves the character with the TransN bone, which we strip from the animations ([P-ANIM-2](PITFALLS.md#p-anim-2)).
That movement has to be rebuilt as R2 physics:
- `graph_transn.py` plots position, velocity and acceleration for one animation.
- `fit_transn.py` fits ascent/descent parabolas and terminal velocity (used for **up special**,
  `SpecialAirHi`), in animation units and UE units (× 10.666).

**Automation: Script**, one animation at a time. **Target:** a fit for every animation whose TransN moves,
written into window VelocityData.

---

## 7. Unreal (R2Kit 5.8)

Mod folder: `Content/ModContent/3729910023/UnrealAssets` · Lua: `Scripts/Captain.Lua`

1. **Create the mod** in the Modding UI (name ≥ 3 characters, [P-UE-6](PITFALLS.md#p-ue-6)). This generates
   the template assets: `CD_`, `HB_`, `PH_`, skins, palettes, `ATT_*`.
2. **Mesh:** re-import the template Skeletal Mesh with our FBX ([P-UE-1](PITFALLS.md#p-ue-1) for settings).
3. **Physics assets:** open `HB_Captain` and `PH_` and reconnect them to the new skeleton. Build capsules only
   ([P-UE-3](PITFALLS.md#p-ue-3)). Assign both slots on the mesh ([P-UE-4](PITFALLS.md#p-ue-4)).
4. **Textures/materials:** import textures. Make material instances of `MAT_Cha_Standard` (`MI_Cap_Body`,
   `_Equipment`, `_Eye`, `_Face`, `_Helmet`, `_Scarf`) ([P-UE-5](PITFALLS.md#p-ue-5)).
5. **Animations:** import every `AN_Cap_*.fbx` with **Custom Sample Rate = 60** ([P-UE-2](PITFALLS.md#p-ue-2)).
6. **State animations:** set `AnimationsDirectory` + `AnimationsPrefix` on CD_. Paste the state mapping
   generated by `update_animations.py` from [`animation_mapping.md`](../animation_mapping.md).
7. **Attacks:** for each `ATT_Cap_*`, paste the stage 4 files (Animations, AttackProperties, Windows,
   Hitboxes, ThrowData). Then apply the manual fix-ups listed in [P-MOVE-*](PITFALLS.md#moves--attacks).
8. **Attributes:** paste the stage 5 values into CD_.
9. **Lua** (`Captain.Lua`): only the template is present. The metatable name must match
   `LuaMetatableName` on CD_.

**Automation: Manual.** Python editor scripting is **enabled** in R2Kit (verified 2026-10-09).
**Target:** one editor Python script that imports FBXs (60 fps), creates/updates assets and writes CD_/ATT_
properties from the stage 4–6 data. First check: can Python set these struct properties? See [STATUS](STATUS.md).

---

## 8. Playtest → back up → publish

1. Playtest from the Modding UI.
2. **Back up before every publish** ([P-UE-0](PITFALLS.md#p-ue-0)):
   ```bash
   python Unreal_Scripts/backup_mod.py -m "before publish"
   ```
   - Mirrors `UnrealAssets/`, `Scripts/` and `ModId.json` into the mod's own backup repo
     (`D:\git_repos\R2_Captain_Falcon`, folder `mod/`), commits, and pushes to
     <https://github.com/CVaranese/rivals-2-falcon> (**public**).
   - With R2Kit **closed** it also dumps every data asset to JSON in `data/`. With R2Kit open the dump is
     skipped and only the binary files are committed, so close R2Kit for a full backup.
   - Refuses to run if the mod looks wiped (empty `UnrealAssets`, a leftover `PublishedAssets`, or fewer
     than half the assets of the last backup), so a broken state never becomes the "latest" backup.
     `--force` overrides.
   - For a new character, create its backup repo first (`git init`, copy the README/.gitattributes
     from `R2_Captain_Falcon`), then pass `--mod-id` and `--backup-repo`.
3. Publish with the Publish button only. Never cook separately, and never close the editor or terminal window
   mid-publish.
4. After publishing, check that `UnrealAssets/` still has everything (or just run the backup again; its
   safety check catches a wipe). If it was wiped, restore from the backup repo (see its README).
