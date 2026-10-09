# Publish crash workaround: shield (Oct 2026 R2Kit update)

Shareable steps for other character creators. Background and diagnosis: [PITFALLS.md P-UE-12](PITFALLS.md#p-ue-12).
Tested on Captain Falcon 2026-10-09 (publish succeeded). The UI path for setting the skeleton's preview mesh
wasn't tested by hand (we did that step with Python), so tell us if your menus look different.

---

**Publish crashing after the Oct 8 update? It's the default shield. Here's how to get around it until the official fix.**

The crash is `Assertion failed: TextureReferenceIndex != INDEX_NONE` while saving `MAT_Cha_ShieldGlow`. Publishing
copies the shared shield materials wrong. The fix is to give your character its own copy of the shield so
nothing in your mod points at `Characters/Shared/Shield` anymore. **Your shield will look wrong** (it uses one of
your own materials) until the devs fix it.

**Before you start**
- Close R2Kit and back up your mod's `UnrealAssets` folder somewhere outside the R2Kit folder.
- If a publish already crashed: close the editor, copy everything from `Project\Saved\ModPublishBackup` into your
  mod's `UnrealAssets` folder, and delete the `PublishedAssets` folder in your mod.

**Make your own shield**
- In your mod's `UnrealAssets`, make a new folder called `Shield`.
- Go to `Content/Characters/Shared/Shield`. Drag `SK_Cha_Shield` into your `Shield` folder and pick **Copy Here**.
- Go to `Content/Characters/Shared/Shield/Animation`. Drag `SK_VFX_Shield_skeleton` into your `Shield` folder and pick **Copy Here**.
- Open your shield mesh copy:
  - Set all 4 material slots (Glass, Stun, Element, Glow) to a material instance from your own mod, e.g. your body material.
  - Set **Physics Asset** to **None**.
  - Save.
- Right-click your shield mesh copy → **Assign Skeleton** → pick **your** skeleton copy (not `SK_VFX_Shield_skeleton`).
- Open your skeleton copy and set its **Preview Mesh** (Preview Scene Settings) to your shield mesh copy. Save.
  This matters: the original skeleton and physics asset point back at the shared shield, and publish follows those links.
- Open your skin data (`Skins/Default/Data/Skin_<yours>_Default`) and set **Shield Mesh** to your shield mesh copy.
- **Save All.**

**Check before publishing**
- Right-click your shield mesh copy and your skeleton copy → **Reference Viewer**. Nothing from
  `Characters/Shared/Shield` should show up.
- Playtest, back up again, then publish.

**Undo it once the devs fix the crash**
- Back up first.
- Open your skin data and set **Shield Mesh** back to `SK_Cha_Shield` (`Characters/Shared/Shield`).
- Delete your `Shield` folder. If it warns about references, something still points at it; fix that first.
- Save All, playtest, publish.
