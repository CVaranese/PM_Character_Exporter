# Recovery: Oct 2026 publish data loss

## What happened (2026-10-08)

- The Captain Falcon mod (`ModContent/3729910023`) had been published to Steam several times.
- After a publish, `UnrealAssets/` contained only `SteamPreview.uasset`. Every other asset was gone.
- The kit's documented recovery source, `Project/Saved/ModPublishBackup`, also only had
  `SteamPreview.uasset`. Each publish overwrites it.
- Recuva wasn't needed.

## What saved it

The R2Kit version-control button had created a git repo inside the mod folder. One commit,
`4383851 "Manual Push."` (2026-10-08 20:56), contains **562 files under `PublishedAssets/`**:
- `CD_Captain`, all 33 `ATT_Cap_*`, `HB_Captain`
- `SK_Cap_Default` + skeleton, all `AN_Cap_*`
- materials, palettes, skin, SFX/VFX data
- base-game references under `PublishedAssets/References/Game/...`

`git fsck --full` passed with no errors.

Backups on C: (session scratchpad, **temporary**, so copy them somewhere permanent):
- `mod_restore_3729910023/`: extracted files
- `mod_3729910023_git_backup/`: copy of the `.git` folder

## Why the commit has the wrong layout

The same button on another mod (`3607712286`, Armando) commits `UnrealAssets/`, and its assets reference
`/Game/ModContent/3607712286/UnrealAssets/...`. **Ours was committed while the mod was in its published
state**, so it holds `PublishedAssets/` with rewritten paths plus `References/` copies of base-game assets.
Moving the files on disk isn't enough: the paths inside each `.uasset` would still point at
`PublishedAssets`. The move has to happen inside Unreal so references get rewritten.

## Restore steps

1. ✅ Close the editor. Run `git checkout -- PublishedAssets` in the mod folder → 559 files restored
   (2026-10-09).
2. ✅ Assets load and hold our data (verified headless, 2026-10-09).
3. ✅ Dumped all 60 data assets to [`character_dumps/Captain/`](../character_dumps/Captain) with
   `Unreal_Scripts/dump_mod_assets.py` and committed them. Includes all 100 CD_ attributes and every
   ATT_ window/hitbox/on-hit property, plus the up-special momentum values (e.g. Active: velocity
   (4.1753, 27.0939), gravity 0.8302; Recovery Down: gravity 2.1541, max fall 18.8194).
4. ✅ Ran `Unreal_Scripts/restore_published_layout.py` with `R2_APPLY=1` (2026-10-09). It consolidated the
   146 `References/` copies into the real `/Game/...` originals and moved 412 assets into `UnrealAssets/`.
5. ✅ Ran `Unreal_Scripts/cleanup_redirectors.py` to delete the redirectors left in `PublishedAssets/`
   (none were referenced).
6. ✅ Re-dumped: all 60 data assets are identical to the pre-restore dump after path normalization, and no
   property holds a `PublishedAssets` path. (Seven assets, `Char_Cap`, `Skin_Cap_Default`, the 4 palette `CS_`
   and `SK_Cap_Default`, still contain stale path *text* outside their properties. The asset registry shows
   no dependency on it, so it's harmless.)
7. ☐ Delete the leftover `PublishedAssets` folder by hand with R2Kit closed. One unreferenced redirector
   (`References/Game/VFX/Textures/Noise/T_Veronoi_02_G`) couldn't be deleted by the editor, probably because
   the engine loads it at startup. The publish docs say to delete this folder before publishing anyway.
8. ☐ Playtest.
9. ☐ Set up a backup of `UnrealAssets/` we control before the next publish ([P-UE-0](PITFALLS.md#p-ue-0)).

## Lessons

- Back up `UnrealAssets` outside the kit before every publish.
- Keep a **text** copy of all data-asset values in git (step 3), so binary-asset loss is never total.
