# Sources

Where to look when we have questions. Note when a source was last checked; the workshop docs are a beta site
and change.

## Rivals 2 Workshop (official) — last checked 2026-10-09

Index: <https://rivals2.com/workshop/>

The kit runs on the **5.8 workshop update**. The import page says its settings screenshots are outdated for 5.8.

### Getting started
- [Installing the modkit](https://rivals2.com/workshop/knowledge-base/getting-started/installing-the-modkit/)
- [Modding tool window](https://rivals2.com/workshop/knowledge-base/getting-started/modding-tool-window/)
- [Playtesting](https://rivals2.com/workshop/knowledge-base/getting-started/playtesting/)
- [Publish to Steam Workshop](https://rivals2.com/workshop/knowledge-base/getting-started/publish-to-steam-workshop/) — publish pipeline, interrupted-publish recovery (see [RECOVERY.md](RECOVERY.md))

### Character creation (in roughly pipeline order)
- [Character creation overview](https://rivals2.com/workshop/knowledge-base/character-creation/character-creation-overview/)
- [Rig your character](https://rivals2.com/workshop/knowledge-base/character-creation/rig-your-character/)
- [Animation overview](https://rivals2.com/workshop/knowledge-base/character-creation/animation-overview/)
- [Create your character mod](https://rivals2.com/workshop/knowledge-base/character-creation/create-your-character-mod/) — template asset list (CD_, HB_, PH_, skins, palettes)
- [Exporting character mesh to Unreal](https://rivals2.com/workshop/knowledge-base/character-creation/exporting-character-mesh-to-unreal/)
- [Import into Unreal](https://rivals2.com/workshop/knowledge-base/character-creation/import-into-unreal/) — mesh/anim import settings, 60 fps sample rate, animation assignment
- [Import textures](https://rivals2.com/workshop/knowledge-base/character-creation/import-textures/)
- [Materials overview](https://rivals2.com/workshop/knowledge-base/character-creation/materials-overview/)
- [Setting up hurtboxes](https://rivals2.com/workshop/knowledge-base/character-creation/setting-up-hurtboxes/) — HB_/PH_ physics assets, capsules only
- [Color palettes](https://rivals2.com/workshop/knowledge-base/character-creation/color-palettes-setup/) · [Dynamic colors](https://rivals2.com/workshop/knowledge-base/character-creation/setting-up-dynamic-colors/)
- [Character select portraits](https://rivals2.com/workshop/knowledge-base/character-creation/generate-csp-character-select-portraits/)
- [Sockets](https://rivals2.com/workshop/knowledge-base/character-creation/sockets/)
- [Setting up an attack](https://rivals2.com/workshop/knowledge-base/character-creation/setting-up-an-attack/) — ATT_ assets, windows, hitbox windows, on-hit properties
- [Setting up a throw](https://rivals2.com/workshop/knowledge-base/character-creation/setting-up-a-throw/)
- [Creating articles](https://rivals2.com/workshop/knowledge-base/character-creation/creating-articles/)
- [Victory sequence](https://rivals2.com/workshop/knowledge-base/character-creation/victory-sequence/) · [Stock icons](https://rivals2.com/workshop/knowledge-base/character-creation/stock-icon-visuals/) · [Shield visuals](https://rivals2.com/workshop/knowledge-base/character-creation/shield-visuals/)
- [Zapped skeleton](https://rivals2.com/workshop/knowledge-base/character-creation/zapped-skeleton/) · [Animating material parameters](https://rivals2.com/workshop/knowledge-base/character-creation/animating-material-parameters/) · [Controlling visibility](https://rivals2.com/workshop/knowledge-base/character-creation/controlling-visibility/)
- [Status effects](https://rivals2.com/workshop/knowledge-base/character-creation/status-effect-overview/)

### Miscellaneous
- [File name conventions](https://rivals2.com/workshop/knowledge-base/miscellaneous/file-name-conventions/) — `SK_`, `AN_`, `MI_`, `T_*_BC` etc.
- [How to make a Rivals 2 attack](https://rivals2.com/workshop/knowledge-base/miscellaneous/how-to-make-a-rivals-2-attack/)
- [Animation states](https://rivals2.com/workshop/knowledge-base/miscellaneous/animation-states/)
- [Lua scripting API](https://rivals2.com/workshop/knowledge-base/miscellaneous/lua-scripting-api-documentation/) — for `Scripts/Captain.Lua`
- [Known issues & troubleshooting](https://rivals2.com/workshop/knowledge-base/miscellaneous/known-issues-and-troubleshooting/)
- [Blender reference files](https://rivals2.com/workshop/knowledge-base/miscellaneous/blender-reference-files/)
- [Export content from workshop](https://rivals2.com/workshop/knowledge-base/miscellaneous/export-content-from-workshop/) — exporting base-game FBX/textures for reference
- [Audio modding](https://rivals2.com/workshop/knowledge-base/miscellaneous/audio-modding-3/) · [FMOD setup](https://rivals2.com/workshop/knowledge-base/miscellaneous/setting-up-fmod/) · [Universal SFX/VFX](https://rivals2.com/workshop/knowledge-base/miscellaneous/universal-sfx-sound-and-vfx-particles/)

## Blender

- Built-in Collada (`.dae`) import/export was **removed in Blender 5.0**; 4.5 is the last version that has it.
  ([Convert 3D writeup](https://convert3d.org/posts/blender-collada))
- Blender MCP add-ons (lets Claude drive Blender directly):
  - `ahujasid/blender-mcp` — the popular one ([directory listing](https://enterprisedna.co/directories/mcp/ahujasid-blender-mcp)). Check the GitHub README for current install steps; it was reportedly being renamed in Sept 2026.
  - `harveyxiacn/blender-mcp` fork — needs Blender 4.0+.
- Blender Python API: <https://docs.blender.org/api/current/>

## Unreal Engine

- Unreal Python API (editor scripting): <https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/>
- "Blueprint Operations" (Fab) exports Blueprint *graphs* to JSON. Not a good fit, because our data is in data
  assets (CD_, ATT_), not graphs. ([Fab listing](https://www.fab.com/listings/a66d7801-6955-4815-a33c-6d86bb27cc94))

## Brawl / Project M

- BrawlCrate (model/animation extraction; our `Loaders/Animations/export_to_anim.py` is a BrawlCrate plugin): <https://github.com/soopercool101/BrawlCrate>
- **Rukai Data** is where the move scripts come from. The PM input files are copied from each subaction page's
  *Scripts → Main* section (`AsyncWait`, `CreateHitBox(HitBoxArguments {…})`, `AllowInterrupts` …).
  - Example: <https://rukaidata.com/P+/Captain%20Falcon/subactions/AttackHi4.html>
  - URL pattern: `https://rukaidata.com/<Game>/<Character>/subactions/<SubactionName>.html`, where Game is
    `P+`, `PM3.6`, `PM3.02`, `Brawl` or `LXP2.1`.
  - Each page also shows IASA, active frames, the hitbox table, and a frame-by-frame viewer with ECB, which is
    useful for checking our converted output.
  - The site is generated by **brawllib_rs** (<https://github.com/rukai/brawllib_rs>), which parses the
    `.pac` files directly. That's a possible route to automating stage 1 without copy/paste (unverified).
