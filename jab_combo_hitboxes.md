# Jab Combo Hitbox Reference

Generated from `temp_start.txt`. Use this as a reference when manually copying sections into R2.

---

## Attack11 (22 frames)

| Window | Length | Anim Start | IASA |
|--------|--------|------------|------|
| Startup | 2 | 0 | — |
| Active | 3 | 2 | — |
| Recovery | 17 | 5 | 10 |

### HitboxAttributes

| Name | Bone | Offset X | Offset Y | Offset Z | Radius | OnHitProp |
|------|------|----------|----------|----------|--------|-----------|
| TopN1 Early | TopN | 0.000000 | -115.192800 | 113.166260 | 37.544320 | TopN Early |
| TopN2 Early | TopN | 0.000000 | -129.378580 | 56.529800 | 37.544320 | TopN Early |
| TopN3 Early | TopN | 0.000000 | -115.192800 | 20.158740 | 24.958440 | TopN Early |

### OnHitProperties

| Name | Damage | BaseKnockback | KnockbackScaling | Angle |
|------|--------|---------------|------------------|-------|
| TopN Early | 2 | 3.669104 | 0.000000 | 80 |

---

## Attack12 (21 frames)

| Window | Length | Anim Start | IASA |
|--------|--------|------------|------|
| Startup | 4 | 0 | — |
| Active | 3 | 4 | — |
| Recovery | 14 | 7 | 11 |

### HitboxAttributes

| Name | Bone | Offset X | Offset Y | Offset Z | Radius | OnHitProp |
|------|------|----------|----------|----------|--------|-----------|
| TopN1 Early | TopN | 0.000000 | -119.245880 | 161.696560 | 37.544320 | TopN Early |
| TopN2 Early | TopN | 0.000000 | -119.245880 | 101.007020 | 37.544320 | TopN Early |
| TopN3 Early | TopN | 0.000000 | -119.245880 | 40.424140 | 29.118180 | TopN Early |

### OnHitProperties

| Name | Damage | BaseKnockback | KnockbackScaling | Angle |
|------|--------|---------------|------------------|-------|
| TopN Early | 3 | 3.562444 | 0.000000 | 80 |

---

## Attack13 (29 frames)

Two active phases with no gap between them (Active 1 transitions directly to Active 2).
`RLegJ Late` uses `InitialInterpolationMode=Auto` because it follows `RLegJ Early` on the same bone.

| Window | Length | Anim Start | IASA |
|--------|--------|------------|------|
| Startup | 5 | 0 | — |
| Active 1 (Early) | 2 | 5 | — |
| Active 2 (Late) | 5 | 7 | — |
| Recovery | 17 | 12 | 10 |

### HitboxAttributes

| Name | Bone | Interp | Offset X | Offset Y | Offset Z | Radius | OnHitProp |
|------|------|--------|----------|----------|----------|--------|-----------|
| RLegJ Early | RLegJ | None | 0.000000 | -44.477220 | 0.000000 | 54.183280 | RLegJ Early |
| HipN Early | HipN | None | 44.477220 | -0.000000 | 0.000000 | 37.544320 | RLegJ Early |
| RLegJ Late | RLegJ | Auto | 0.000000 | -44.477220 | 0.000000 | 41.704060 | RLegJ Late |
| HipN Late | HipN | None | 44.477220 | -0.000000 | 0.000000 | 33.384580 | RLegJ Late |

> Both Early hitboxes share `RLegJ Early` properties (same damage/KB on both bones).

### OnHitProperties

| Name | Damage | BaseKnockback | KnockbackScaling | Angle |
|------|--------|---------------|------------------|-------|
| RLegJ Early | 8 | 4.053080 | 0.622183 | 55 |
| RLegJ Late | 6 | 1.919880 | 0.497747 | 50 |

---

## Attack100Start (7 frames)

No hitboxes.

---

## Attack100 (34 frames — rapid jab cycle)

One complete cycle of the rapid jab. In PM this loops via `Goto`; the 34-frame script encodes the full cycle. All 5 phases are geometrically identical — only the hitbox names differ.

The 5th phase is labeled **Phase4** (the label list exhausts Early/Late/Late2/Late3 at index 3, then falls back to `Phase{i}`).

| Window | Length | Anim Start |
|--------|--------|------------|
| Startup | 2 | 0 |
| Active 1 (Early) | 2 | 2 |
| Between 1 | 4 | 4 |
| Active 2 (Late) | 2 | 8 |
| Between 2 | 5 | 10 |
| Active 3 (Late2) | 2 | 15 |
| Between 3 | 4 | 17 |
| Active 4 (Late3) | 2 | 21 |
| Between 4 | 4 | 23 |
| Active 5 (Phase4) | 2 | 27 |
| Recovery | 5 | 29 |

### HitboxAttributes

All 15 hitboxes (3 per phase × 5 phases). All positions and sizes are identical across phases.

| Name | Bone | Offset X | Offset Y | Offset Z | Radius | OnHitProp |
|------|------|----------|----------|----------|--------|-----------|
| RShoulderJ Early | RShoulderJ | 0.000000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ1 Early | RArmJ | -10.666000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ2 Early | RArmJ | -63.996000 | -0.000000 | 0.000000 | 24.958440 | RArmJ Early |
| RShoulderJ Late | RShoulderJ | 0.000000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ1 Late | RArmJ | -10.666000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ2 Late | RArmJ | -63.996000 | -0.000000 | 0.000000 | 24.958440 | RArmJ Early |
| RShoulderJ Late2 | RShoulderJ | 0.000000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ1 Late2 | RArmJ | -10.666000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ2 Late2 | RArmJ | -63.996000 | -0.000000 | 0.000000 | 24.958440 | RArmJ Early |
| RShoulderJ Late3 | RShoulderJ | 0.000000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ1 Late3 | RArmJ | -10.666000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ2 Late3 | RArmJ | -63.996000 | -0.000000 | 0.000000 | 24.958440 | RArmJ Early |
| RShoulderJ Phase4 | RShoulderJ | 0.000000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ1 Phase4 | RArmJ | -10.666000 | -0.000000 | 0.000000 | 24.958440 | RShoulderJ Early |
| RArmJ2 Phase4 | RArmJ | -63.996000 | -0.000000 | 0.000000 | 24.958440 | RArmJ Early |

### OnHitProperties

All 5 phases share the same 2 on-hit properties (stats are identical across the full cycle).

| Name | Damage | BaseKnockback | KnockbackScaling | Angle |
|------|--------|---------------|------------------|-------|
| RShoulderJ Early | 2 | 0.959940 | 0.124437 | 45 |
| RArmJ Early | 1 | 0.383976 | 0.037331 | 90 |

> Angle 45 = Sakurai (PM trajectory 361 → R2 45°). `RArmJ2` hitboxes always use `RArmJ Early`; all others use `RShoulderJ Early`.

---

## AttackEnd (15 frames)

No hitboxes. AllowInterrupts at frame 9.
