# PM → Rivals 2 Character Porting Docs

The goal is to say "export character X into Rivals 2" and have it done, with every step that still needs a
human written down here.

Falcon-first: these docs describe Captain Falcon (`Cap`, mod ID `3729910023`). Anything Falcon-specific is
flagged so it can be moved into per-character config later.

| Doc | What it's for |
|---|---|
| [PIPELINE.md](PIPELINE.md) | The end-to-end process, stage by stage, with inputs/outputs and automation level |
| [PITFALLS.md](PITFALLS.md) | Every known caveat: symptom → cause → fix. **Read before each stage.** |
| [STATUS.md](STATUS.md) | What's automated, manual, or not implemented yet; open questions |
| [RECOVERY.md](RECOVERY.md) | The Oct 2026 publish data-loss incident and how the mod was restored |
| [SOURCES.md](SOURCES.md) | Links to official docs and tools, grouped by topic |

Older reference material in the repo root (kept as-is):

- [`../Guide.md`](../Guide.md) — original manual model/animation guide (superseded by PIPELINE.md)
- [`../convert_hitboxes.md`](../convert_hitboxes.md) — function reference for `convert_hitboxes.py` (kept in sync per CLAUDE.md)
- [`../animation_mapping.md`](../animation_mapping.md) — R2 state → PM animation table
- [`../hitboxes.md`](../hitboxes.md) — original conversion rules + worked example
- [`../r2_attribs_usage.md`](../r2_attribs_usage.md) — attribute sheet round-trip tool
- [`../Sub_Action_Meanings.txt`](../Sub_Action_Meanings.txt) — Brawl/PM subaction glossary

## Conventions used in these docs

- **Verified** = observed working in our own mod. **Unverified** = from docs or assumption; test before relying on it.
- File paths use the real locations on this machine:
  - Exporter repo: `D:\git_repos\PM_Character_Exporter`
  - Character source data: `D:\ROA2_Modding\character_data\Captain_falcon`
  - R2Kit project: `D:\Program Files\Epic Games\R2Kit\Project`
  - Mod folder: `...\Project\Content\ModContent\3729910023`
