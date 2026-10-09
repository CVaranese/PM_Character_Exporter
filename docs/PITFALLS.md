# Pitfalls & caveats

Format: **Symptom → Cause → Fix**, plus status (Verified / Unverified / Open). Add new entries as they're
found; don't delete fixed ones, mark them **Fixed** so the history stays.

---

## Unreal / R2Kit

<a id="p-ue-0"></a>
### P-UE-0 — Publishing can wipe your whole mod  ⚠️ highest priority
- **Symptom:** after publishing, `UnrealAssets/` is empty apart from `SteamPreview.uasset`. All CD_, ATT_,
  meshes and animations are gone.
- **Cause:** publishing moves assets into `PublishedAssets/`, rewrites their internal paths and then cleans up.
  The kit's backup (`Project/Saved/ModPublishBackup`) is supposed to restore them, but ours only held
  `SteamPreview.uasset`, and each publish overwrites it.
- **Fix:** run `Unreal_Scripts/backup_mod.py` before every publish. It commits the mod to our own repo
  (`R2_Captain_Falcon`) outside the R2Kit folder; see PIPELINE stage 8. Don't count on the kit's
  version-control button: if pressed at the wrong time it commits `PublishedAssets/` with rewritten paths
  (that's what saved us, but restoring took extra editor steps; see [RECOVERY.md](RECOVERY.md)).
- **Status:** Verified (happened 2026-10-08). Backup script added 2026-10-09.

<a id="p-ue-12"></a>
### P-UE-12 — Publish crashes after the Oct 8 2026 R2Kit update (shield material assert)  ❗ Open
- **Symptom:** the editor crashes mid-publish and the mod is left in the published layout (see P-UE-0).
- **Log** (`Project/Saved/Logs/Rivals2.log`):
  ```
  Saving Package: /Game/ModContent/<id>/PublishedAssets/References/Game/Characters/Shared/Shield/MAT_Cha_ShieldGlow
  LogMaterial: Error: Compiler->Texture() failed to find texture 'T_Cha_ShieldOffset_M' in referenced list of size '2'
  Assertion failed: TextureReferenceIndex != INDEX_NONE [HLSLMaterialTranslator.cpp:8555]
  ```
- **Cause (diagnosed 2026-10-09):** publishing copies every external (base-game) asset the mod references into
  `PublishedAssets/References/` and points the copies at each other. For the shield chain it gets this wrong:
  1. Chain: `Skin_<Char>_Default.shield_mesh` → `SK_Cha_Shield` → `MI_Cha_ShieldGlow/Stun` (+ `MI_Zet_DefaultShieldElement/Glass`,
     also referenced by `SK_Cha_Shield`) → `MAT_Cha_ShieldGlow/Stun/Glass/Shield_Element` → material function
     `MF_Cha_Shield_VertexOffsetShake` → texture `T_Cha_ShieldOffset_M` (sampled **inside the function**).
  2. Log order: the MF is duplicated (17:44:40.477) **before** the texture (40.485), and the MAT after both (40.702).
  3. The MF copy keeps pointing at the **original** `/Game/.../T_Cha_ShieldOffset_M`. Verified in the Oct 8 copies.
     The MAT copy's cached referenced-texture list points at the **copied** texture.
  4. Re-saving the MAT copy compiles it for the thumbnail. The compiler finds a texture with the right name but the
     wrong object (`failed to find texture 'T_Cha_ShieldOffset_M' in referenced list`), and asserts.
  - Affects **every character mod using the template's default shield mesh**, not just Falcon. It started with
    the kit update installed 2026-10-08 ~20:23–20:34. The Oct 8 wipe (20:56) was very likely the same crash.
- **Recovery:** this time `Saved/ModPublishBackup` was complete (413 files). Restore from it or from the
  `rivals-2-falcon` backup repo, and delete `PublishedAssets/`.
- **Fix:** devs are working on it (2026-10-09). Don't publish until resolved. Possible local workaround (untested): put
  mod-local copies of the whole shield chain (SK, MIs, MATs, MF, textures; ~16 assets) in `UnrealAssets/Shield/`,
  with the copies referencing each other, and point `Skin_Cap_Default.shield_mesh` at the local SK. Publish then
  has nothing external to duplicate in that chain. It's the only reference into the chain from the mod.
- **Status:** Crash verified 2026-10-09 (second occurrence).

<a id="p-ue-1"></a>
### P-UE-1 — Mesh import settings
- **Symptom:** only a skeleton is created / mesh fails to import / capsule shadow errors.
- **Fix:** **Override Full Name = on**. **Import Uniform Scale = 1**: fix the scale in Blender, never in the
  importer. Convert Scene on. Material import = Do Not Create Materials (delete any that get created). Import
  Animations off. Update Skeleton Reference Pose on. Normals = Import Normals.
  Re-import the *template* SK with "re-import with new file", accept "Reset to FBX" and the skeleton change,
  and ignore incompatibility warnings if the mesh imports.
- **Status:** from official docs; partly verified.

<a id="p-ue-2"></a>
### P-UE-2 — Animations must import at 60 fps
- **Symptom:** the game **crashes on load**.
- **Fix:** untick "Use Default Sample Rate" and set Custom Sample Rate = **60** on every animation import.
  Assign the correct skeleton, since Unreal guesses from the current folder.
- **Status:** Verified (in the original Guide) + official docs.

<a id="p-ue-3"></a>
### P-UE-3 — Hurtbox physics asset: capsules only
- **Symptom:** crash during playtest.
- **Cause:** non-capsule shapes (boxes, spheres, convex hulls) in `HB_`.
- **Fix:** select the body, Tools → Primitive Type = Capsule → Re-generate Bodies. You don't need a capsule
  per bone (e.g. hands yes, fingers no).
- **Related:** redefining *every* hurtbox as `Default` in CD_ breaks initialization (overhead UI clipping,
  revive-platform camera, missing %). Use `Vulnerable`, or remove the entries.
- **Status:** official docs.

<a id="p-ue-4"></a>
### P-UE-4 — Two physics asset slots, and shadows
- `HB_` = hurtboxes. `PH_` = shadow caster + offscreen culling. Both must be reconnected to the new
  skeleton after replacing the mesh.
- No slot-1 asset → culling uses bounds, so the character can vanish. No slot-2 asset → no capsule shadows.
- Shadows still missing → remove non-1 joint scales in Blender, apply transforms, re-export.
- **Status:** official docs.

<a id="p-ue-5"></a>
### P-UE-5 — Materials
- Blender materials don't import. Author everything in UE as instances of `MAT_Cha_Standard` (toon
  shading + outline).
- Outline gaps → faceted shading or custom normals; fix in Blender.
- Mesh not showing in game → assign it on the character mesh component in `RivalsCharacterRenderer`
  (`Skins/Default/BP_Cap_Default`).
- **Status:** official docs.

<a id="p-ue-6"></a>
### P-UE-6 — Mod name ≥ 3 characters
- Shorter names generate empty numbered folders and block progress. Delete the folder and retry.

<a id="p-ue-7"></a>
### P-UE-7 — Asset reference paths change on publish
- The paste files and `update_animations.py` reference `/Game/ModContent/<id>/UnrealAssets/Animation/...`.
  Published assets reference `/Game/ModContent/<id>/PublishedAssets/...`, and base-game assets become copies
  under `PublishedAssets/References/Game/...`.
- **Rule:** always author against `UnrealAssets` paths. Never paste data copied from a published asset
  without rewriting its paths.
- **Status:** Verified (seen in the restored `CD_Captain.uasset`).

<a id="p-ue-8"></a>
### P-UE-8 — Animation length vs window length
- If an attack window's animation length doesn't match its frame length, playback **scales to fit**. That's
  silent, so a wrong `AnimationLengthFrames` speeds up or slows down the animation instead of erroring.

<a id="p-ue-9"></a>
### P-UE-9 — CD_ / ATT_ are Blueprints: their data is on the class default object
- **Symptom:** exporting an `ATT_` or `CD_` asset (Asset Actions → Export / T3D) gives an empty event
  graph and none of the attack data.
- **Cause:** they're Blueprint classes. Values live on the generated class's default object (CDO).
- **Fix (Python):** `cls = EditorAssetLibrary.load_blueprint_class(pkg)`, `cdo = unreal.get_default_object(cls)`,
  then `cdo.get_editor_property(...)`. Struct values have `.export_text()`, which produces the same text as
  details-panel Copy. Property names can be listed by parsing the class's Python docstring
  ("Editor Properties" section). See `Unreal_Scripts/dump_mod_assets.py`.
- **Status:** Verified 2026-10-09.

<a id="p-ue-10"></a>
### P-UE-10 — Running editor Python headless
- `UnrealEditor-Cmd.exe <Project>\Rivals2.uproject -run=pythonscript -script="<file.py>" -unattended -nosplash -nullrhi -stdout`
  works with R2Kit. A full run takes about 25 s. **The R2Kit editor must be closed**, since two editors on
  one project can corrupt assets.
- Pass settings through environment variables (the scripts read `R2_*`).
- **Preferred:** run through `python -I Unreal_Scripts/run_ue_python.py <script.py> [R2_KEY=value ...]`. It
  refuses while R2Kit is open, only runs scripts from `Unreal_Scripts/`, and reports success from the log.
  It's also the one command allowed in `.claude/settings.local.json`, so Claude Code can run it without a
  permission prompt.
- Harmless noise in the log: the ZenShared DDC timeout (192.168.1.8, which is the developers' internal
  cache), `MPC_StoryMode` not found, and Python name-clash warnings for `CharacterMoveData`/`RivalsCpuData`.
- **Don't trust the exit code.** The commandlet returns 1 if *anything* logged an error, e.g.
  `FSDLInputDevice::OnGamepadAttached - duplicate InstanceID` when a controller is plugged in, even though
  "Python script executed successfully". Check the script's own output file instead.
- **Status:** Verified 2026-10-09.

<a id="p-ue-11"></a>
### P-UE-11 — Moving/consolidating assets from Python (UE 5.8)
- `AssetTools.rename_assets([...AssetRenameData])` moves assets, rewrites references and **saves on its
  own**, leaving the old files deleted. `EditorAssetLibrary.consolidate_assets(target, [copies])` turns
  the copies into redirectors to `target`.
- `AssetTools.fixup_referencers` **does not exist** in R2Kit's Python. Instead, check
  `AssetRegistry.get_referencers` on each redirector, re-save any referencers, then delete the redirectors
  (`Unreal_Scripts/cleanup_redirectors.py`).
- The editor may refuse to delete a redirector the engine loads at startup. Delete it on disk with the
  editor closed, after checking that nothing references it.
- **Status:** Verified 2026-10-09.

---

## Scale & coordinates

<a id="p-scale-1"></a>
### P-SCALE-1 — Two different scale numbers  ❓ Open
- Hitbox/movement data: R2 = PM × **10.666** (`UNIT_SCALE`, `fit_transn.SCALE`), rounded to 3 decimals.
- Model in Blender: unit scale 0.01 and object scale **10.33** (Guide.md).
- These differ by about 3%. Either 10.33 was a typo, or the model was deliberately made slightly smaller
  than the hitbox scale. **TODO: measure the restored mesh against a hitbox to confirm**, then pick one
  constant for both.

---

## Blender

<a id="p-blend-1"></a>
### P-BLEND-1 — Collada import is gone in Blender 5.0
- Built-in `.dae` import was removed in 5.0; 4.5 is the last version with it. Stay on ≤ 4.5, or switch the
  model path to another format BrawlCrate can export.
- We're on 3.6 because of the DAE + BrawlBox animation import plugins. A 4.x trial is planned; see
  [STATUS](STATUS.md).

<a id="p-model-1"></a>
### P-MODEL-1 — Rename `ThrowN` → `Grab_M`
- R2 expects a `Grab_M` bone (grab/throw attachment). Brawl calls it `ThrowN`. Skipping this breaks grabs.
  *(Exact R2 failure mode not recorded.)*

<a id="p-model-2"></a>
### P-MODEL-2 — Joint transforms Unreal doesn't like
- Disable segment scale compensation. Keep joints that have children at uniform scale. Don't export Control
  Rig data. Apply transforms to **deltas** (Ctrl+A) after rotating/scaling.

---

## Animations

<a id="p-anim-1"></a>
### P-ANIM-1 — Scene framerate before import
- Set Blender to 60 fps **before** importing BrawlBox animations, or keyframes land on the wrong frames.

<a id="p-anim-2"></a>
### P-ANIM-2 — TransN bone (root movement)
- PM animations move the character through the `TransN` bone. In R2, movement comes from physics/window
  velocity, so TransN is disabled on export (`animations_no_trans`). Any movement it carried (dash attack,
  specials, ledge options, rolls, getups…) must be rebuilt as `VelocityData` / `MovementProperties`;
  see PIPELINE stage 6.
- `transn_keyframes.csv` lists the animations that have TransN keys. That's the to-do list for movement.

<a id="p-anim-3"></a>
### P-ANIM-3 — Merged animations: seams and offsets
- R2 expects one animation per attack. Jab 1/2/3 and angled/charged variants are concatenated in Blender
  (`merge_actions.py`), and windows pick the right section via `AnimationStartFrame`.
- **Fixed 2026-05-23:** the merge used `frame_range[1] - frame_range[0]` (N−1 frames), causing a 1-frame
  overlap per seam. It now advances by `frames + 1`. Angled offsets are `total_frames × variant_index`.
  Merge script and converter must agree on this.

<a id="p-anim-4"></a>
### P-ANIM-4 — Turnaround animations need flipping  ❓ Open
- Animations that turn the character around end facing the wrong way in R2. They need to be mirrored or
  flipped: `Turn`, `TurnRun`, `TurnRunBrake`, `CatchTurn`, `SpecialNTurn`, `SpecialAirNTurn`
  (separate FBXs exist in `p+falcon/`). Not solved.

<a id="p-anim-5"></a>
### P-ANIM-5 — Landing lag animations are 2× too long
- Melee/PM landing lag assumes L-cancelling halves it. R2 has no L-cancel, so landing-lag animations need to
  be sped up 2× (or LandingLagFrames halved). **Open:** not implemented.

<a id="p-anim-6"></a>
### P-ANIM-6 — Missing animations
- Some R2 states have no PM equivalent and are left as the dummy idle: `CubedSpinHorizontal/Vertical`,
  `ItemThrowForwardHard`, `LedgeSlip`, `ParryFall`, `ShieldBreak`, several thrown states, item fall/run.
  The full list is in [`animation_mapping.md`](../animation_mapping.md). Hitstun animations are also listed
  as missing in the README.

---

## Moves / attacks

<a id="p-move-1"></a>
### P-MOVE-1 — Knockback conversion is an approximation
- `kb_calc.py`: compute PM KB at 0% and 100% damage, × 0.03 × 10.666, ÷ `GLOBAL_KB_MULTIPLIER = 3`, then
  solve for R2 BKB and scaling. Weight is ignored, and WDSK is treated as constant. The constants (0.03,
  0.12, 3) were tuned by feel; **re-check against the restored ATT_ values** in case we tweaked them by hand.

<a id="p-move-2"></a>
### P-MOVE-2 — Sakurai angle
- PM trajectory 361 → R2 angle **45**. R2 has no "Sakurai angle" behaviour, so 45 is a stand-in.

<a id="p-move-3"></a>
### P-MOVE-3 — AsyncWait vs SyncWait
- `AsyncWait(n)` = wait until absolute frame n. `SyncWait(n)` = wait n frames from now. The parser keeps a
  frame counter from both. The trailing AsyncWaits after `DeleteAllHitBoxes` (e.g. `EnableLandingLag` false,
  `AllowInterrupts`) set the auto-cancel and IASA frames, not hitbox timing.

<a id="p-move-4"></a>
### P-MOVE-4 — `EnableLandingLag` = aerial auto-cancel window
- Toggling `EnableLandingLag` in PM is what defines the auto-cancel window in R2.

<a id="p-move-5"></a>
### P-MOVE-5 — "Between" windows only when there's a gap
- **Fixed 2026-05-23:** `_build_win_defs` used `max(gap, 1)` and created spurious Between windows when
  gap = 0. Between windows are now only inserted when gap > 0.

<a id="p-move-6"></a>
### P-MOVE-6 — Hitbox naming & interpolation
- Hitboxes are named `<Bone><n> <Early|Late|Late2…>`. On-hit properties are deduplicated by
  (damage, bkb, kbg, wdsk, angle).
- When a hitbox follows a same-bone hitbox from the previous phase, it gets `InitialInterpolationMode=Auto`.
- `CreateHitBox` on an existing `hitbox_id` **updates** it rather than adding a new one.

<a id="p-move-7"></a>
### P-MOVE-7 — Heuristics based on the move name
- `"air"` in the name → aerial (AirOnly, landing lag, `Landing*` anim). `"lw3"` → end in crouch.
  `"start"`/`"end"` → single-window start/end pipeline. Moves whose names break these rules get wrong
  output. **Target:** replace with an explicit per-move manifest.

<a id="p-move-8"></a>
### P-MOVE-8 — Jab / multi-hit and angled moves
- One animation file per attack. Phases are selected with window cancels (`UpDown`/`DownDown` for angles,
  `StrongReleased` for charge). Charged+angled assumes the same Post-Charge pose for all angles.
- Jab sub-actions (multi-jab `Attack100`) are listed as an open issue in the README.

<a id="p-move-9"></a>
### P-MOVE-9 — Grab/throw output needs manual fix-ups
- Rename `Grab 1`/`Grab 2` → `Grab Front`/`Grab Back`.
- `OffsetBoneName` can't be derived from PM data; set it by hand.
- `05_ThrowData.txt` is a zero template; knockback is entered by hand.
- `GRAB_RELEASE_VELOCITY_X = -12.5` is Falcon-specific.

<a id="p-move-10"></a>
### P-MOVE-10 — Smash attack START frames
- PM strongs have separate `Start` animations (`AttackS4Start` …). The charged pipeline concatenates
  Start + Hold + attack. The README's "skip for now?" note predates that pipeline. Check against restored
  `ATT_Cap_Fstrong/Ustrong/Dstrong`.

<a id="p-move-11"></a>
### P-MOVE-11 — Can't grab ledge during/after an attack (e.g. up-b)
- **Symptom:** Falcon can't grab ledge after up-b.
- **Cause:** R2 only allows ledge grabs during an attack on windows with
  `LedgeProperties.CanGrabLedgeOnFrame >= 0`. The converter's fixed `LEDGE_PROPS` string writes **-1 (never)**
  on every window of every attack.
- **PM source:** the Rukai Data script has `LedgeGrabEnable(...)` commands, e.g. Falcon `SpecialHi`:
  `Disable` at 0, `EnableInFrontAndBehind` at frame 12 (same frame as the dive grab box), `EnableInFront` at 54.
  Map the frame to the R2 window that contains it, and set `CanGrabLedgeOnFrame` relative to that window's
  start (0 if it lines up with the start), plus every following window of the move.
- **Fix:** `Unreal_Scripts/set_ledge_grab.py` (env `R2_ATTACK`, `R2_WINDOWS`, `R2_FRAME`, `R2_APPLY`).
  For Falcon up-b: Active, Recovery Up, Recovery Down, Special Fall at 0. Window grab-box dimensions are left at
  (0, 0). *Assumed* to mean "use CD_ default box" (200×110 @ (-50, 125)). **Verify in playtest.**
- **Target:** the converter should parse `LedgeGrabEnable` and set `CanGrabLedgeOnFrame` on the right windows.
- **Status:** Cause verified 2026-10-09; fix pending playtest.

---

## Attributes

<a id="p-attr-1"></a>
### P-ATTR-1 — The attribute mapping was never written down
- CD_ attributes were set by hand from the workshop guide, and the values weren't recorded. The README also
  says "some attributes are incorrect". **Action:** dump the restored `CD_Captain` to text with editor
  Python, commit it, and build a PM → R2 mapping table from it.

---

## Process

<a id="p-proc-1"></a>
### P-PROC-1 — Keep the exporter repo committed
- As of 2026-10-09 almost all of this repo (move folders, most scripts) had **never been committed**.
  Commit after each working session, and push to a remote.
