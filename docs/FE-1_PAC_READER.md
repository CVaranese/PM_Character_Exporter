# FE-1 design notes: reading Brawl/P+ `.pac` files directly

Status: **planned, not started** (written 2026-10-09). Summary and unknowns: [STATUS.md → FE-1](STATUS.md#future-enhancements).

## Goal

Replace hand-copying from Rukai Data with one command:

```bash
pac_dump --brawl <brawl dump> --mod <P+ sd folder> --fighter "Captain Falcon" --out character_data/Captain.json
```

Then every downstream step reads `Captain.json` instead of text pasted into `temp_attack.txt`.

## Architecture

```
FitCaptain*.pac (+ Brawl dump) ──► pac_dump (Rust, brawllib_rs) ──► Captain.json ──► Python pipeline
                                                                                   ├─ convert_hitboxes.py (per move)
                                                                                   ├─ attribute mapping (CD_)
                                                                                   ├─ hurtbox → HB_ capsules
                                                                                   └─ fit_transn.py (TransN movement)
```

- **Rust side kept thin:** load the fighter with brawllib_rs, serialize to JSON, nothing else. All porting logic
  stays in Python, where the rest of the pipeline lives.
- New folder `pac_dump/` in this repo (a Cargo project). The built `.exe` is gitignored. Pin the brawllib_rs
  version in `Cargo.toml` so output doesn't drift.

## Phase 0: spike (answer the unknowns, ~1 session)

1. Install Rust (`rustup`), clone brawllib_rs, build its example.
2. Try loading in this order, stopping at the first that works:
   a. `p+falcon/` files alone (`FitCaptain.pac`, `FitCaptain00.pac`, `FitCaptainMotionEtc.pac`)
   b. a minimal fake "brawl dump" folder containing just the fighter folder
   c. a full extracted Brawl disc + P+ SD folder (needs your own disc)
3. List what `HighLevelFighter` exposes (scripts, attributes, hit/hurt/grab/ledge-grab boxes, ECB, bones,
   per-frame data). Record findings in this file.
4. **Go/no-go:** if (c) is the only option and it's impractical, fall back to BrawlLib (C#) or a Python
   parser (see STATUS FE-1 approach list).

## Phase 1: `pac_dump` JSON (sketch, adjust to what brawllib_rs actually exposes)

```jsonc
{
  "source": { "game": "P+", "fighter": "Captain Falcon", "brawllib_rs": "<version>", "files": ["FitCaptain.pac", "..."] },
  "attributes": { "gravity": 0.13, "weight": 99, "jump_squat_frames": 4 /* ... all ~70 */ },
  "bones": [ { "index": 0, "name": "TopN", "parent": null } /* replaces bones.csv */ ],
  "misc": { "ledge_grab_boxes": [ /* sizes; the P-MOVE-11 question */ ], "ecb": { /* ... */ } },
  "subactions": {
    "SpecialHi": {
      "index": "0x5d",
      "animation": "SpecialHi",
      "frame_count": 53,
      "iasa": null,
      "scripts": { "main": [ /* commands, same shape as Rukai's text, plus parsed args */ ],
                   "gfx": [], "sfx": [], "other": [] },
      "frames": [ { "hit_boxes": [], "hurt_boxes": [], "grab_boxes": [], "ledge_grab_box": null,
                    "ecb": {}, "trans_n": [0,0,0] } ]
    }
  }
}
```

Notes:
- Keep **raw script commands** (for the existing parser) *and* **per-frame resolved data** (for checks and
  the TransN fitting). The per-frame data removes our AsyncWait/SyncWait guesswork (P-MOVE-3).
- `trans_n` per frame replaces `transn_keyframes.csv` (P-ANIM-2, stage 6).

## Phase 2: wire into the pipeline

| Consumer | Change |
|---|---|
| `convert_hitboxes.py` | New input mode `--from-json Captain.json --subaction AttackAirB` alongside the text input. Keep text mode working until JSON output is verified. |
| Converter: ledge grab | Parse `LedgeGrabEnable(...)` → set `CanGrabLedgeOnFrame` on the window containing that frame and on following windows (fixes P-MOVE-11 at the source). |
| Converter: auto-cancel / IASA | Read `EnableLandingLag` / `AllowInterrupts` directly instead of inferring them from waits. |
| `bones.csv` | Generated from JSON `bones`. |
| Attributes | New `attribs_map.py`: PM attribute → R2 CD_ property + formula table; validated against `character_dumps/.../CD_Captain.json`. |
| Hurtboxes | New editor script: JSON hurtboxes → capsules in `HB_<Char>` (scale × 10.666, bone mapping). |
| `fit_transn.py` | Read per-frame `trans_n` from JSON; batch over every subaction whose TransN moves. |
| Move manifest | Lists subactions → R2 attack slot + flags (angled/charged/grab). Replaces the name heuristics (P-MOVE-7). |

## Phase 3: verification

- **Golden tests:** for 4–5 moves (AttackAirB, AttackHi4, SpecialHi, Catch, Attack11), the converter output
  from JSON must equal the output from today's Rukai-copied text. Commit the expected files under
  `tests/golden/`.
- Spot-check `attributes` against Rukai's attributes page.
- Re-run the full Falcon conversion and diff against `character_dumps/Captain` to see what changes (should be
  only intended fixes, e.g. ledge grab).

## Risks

- **Input requirements** (full Brawl dump) — Phase 0 decides.
- **P+ specifics:** P+ changes moves through its own files and code. brawllib_rs handles P+ for Rukai Data,
  so it should work, but check that the P+ values (not vanilla Brawl) come through.
- **brawllib_rs API changes:** pin the version.
- **Legal/practical:** don't commit `.pac` files or the Brawl dump to any repo, especially the **public**
  `rivals-2-falcon` backup repo. Only our derived JSON goes into git.

## Open questions for later

- Should `pac_dump` also export animations (replacing the BrawlCrate plugin + Blender import), or keep that
  path? brawllib_rs reads animations for its renderer, so possibly, but that's a separate decision.
- One JSON per fighter, or one per subaction? (One per fighter is simpler; size is probably fine.)
