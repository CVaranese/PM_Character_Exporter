#!/usr/bin/env python3
"""
Convert Project M hitbox script data to Rivals 2 JSON format.

Usage:
    python convert_hitboxes.py input.txt --move-name AttackAirB
    python convert_hitboxes.py input.txt --move-name AttackAirB --total-frames 36 --landing-lag-frames 7
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_calc import calc_rivals2_kb

UNIT_SCALE = 10.666
TRAJECTORY_SAKURAI = 361
SAKURAI_R2_ANGLE = 45
DEFAULT_LANDING_LAG_FRAMES = 7
GRAB_HOLD_FRAMES = 60
GRAB_HOLD_ANIM_FRAMES = 120
GRAB_RELEASE_FRAMES = 32
GRAB_RELEASE_VELOCITY_X = -12.5


# ── Fixed R2 default struct strings ────────────────────────────────────────────

MOVEMENT_PROPS = (
    "(Gravity=-1.000000,MaxFallSpeed=-1.000000,FrictionGround=-1.000000,"
    "FrictionAir=-1.000000,CanDrift=Default,AirAcceleration=-1.000000,"
    "AirSpeedHorizontalMax=-1.000000,CanFallThroughPlatforms=False,"
    "DiminishingReturnsPercentLostPerUse=0.000000,MinimumDiminishingReturnsValue=0.000000)"
)
ADVANCED_WINDOW_PROPS = (
    "(WindowArmor=-1,AerialAutocancelFrame=-1,CanWallJumpOnFrame=-1,"
    "BReverseOnFrame=-1,ToggleECBActiveOnFrame=,ToggleRootedOnFrame=,"
    "TurnAroundOnFrame=,ToggleFarFromECBOnFrame=,ToggleCanFastfallOnFrame=,"
    "ToggleVisibleOnFrame=,CooldownData=(CooldownStartFrame=0,CooldownDuration=0),"
    "bDisableHitpauseYOffset=False,PreserveRotation=False)"
)
LEDGE_PROPS = (
    "(CanGrabLedgeOnFrame=-1,LedgeGrabBoxOffset=(X=0.000000,Y=0.000000),"
    "LedgeGrabBoxDimensions=(X=0.000000,Y=0.000000),ReleaseLedgeOnFrame=-1,"
    "StayOnLedge=False)"
)
GRAB_ADV_WINDOW_PROPS = ADVANCED_WINDOW_PROPS.replace("WindowArmor=-1,", "WindowArmor=0,")
ADV_ON_HIT_PROPS = (
    "(SpecialEffect=None,HitpauseMultiplier=1.000000,ExtraHitpauseForOpponent=0,"
    "HitpauseMovementType=None,HitpauseMovementOffsetFromHost=(X=0.000000,Y=0.000000),"
    "HitpauseMovementStrength=0.500000,SDIMultiplier=1.000000,ASDIMultiplier=-1.000000,"
    "bCanReverse=True,bReverseBasedOnHorizontalSpeed=False,bForceFlinch=False,"
    "GroundTechable=True,bIgnoresWeight=False,bAutoFloorhuggable=False,"
    "ProjectileInteraction=Default,bForceKnockbackInKnockdown=False,bPreserveFacing=False,"
    "KnockbackAngleMode=SpecifiedAngle,HitstunMultiplier=1.000000,"
    "HitfallHitstunMultiplier=1.000000,ParryReaction=Stun,GrabPartnerInteraction=None,"
    "ExtraShieldStun=0,ShieldDamageMultiplier=1.000000,ShieldPushbackMultiplier=1.000000,"
    "ShieldHitpauseMultiplier=1.000000,FullChargeKnockbackMultiplier=1.300000,"
    "FullChargeDamageMultiplier=1.600000,FinalBaseKnockback=0.000000,ForceTumble=False,"
    "IgnoreKnockbackArmor=False,IgnoreSuperArmor=False,IgnoreInvincibility=False,"
    "PreventChaingrabsOnHit=False,bIsWindbox=False,HitstunAnimationStateOverride=None)"
)


# ── Helpers ─────────────────────────────────────────────────────────────────────

def ff(v):
    return f"{v:.6f}"


def load_bones(csv_path):
    bones = {}
    bone_parents = {}
    with open(csv_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("index"):
                continue
            parts = line.split(",")
            idx = int(parts[0].strip())
            name = parts[1].strip()
            parent = parts[2].strip()
            bones[idx] = name
            bone_parents[name] = "" if parent == "Bones" else parent
    return bones, bone_parents


def parse_hitbox_args(s):
    """Parse a CreateHitBox argument string into a dict of hitbox properties."""
    def get(pattern, conv=str):
        m = re.search(pattern, s)
        return conv(m.group(1)) if m else None

    return {
        "bone_index": get(r"bone_index:\s*(\d+)", int),
        "hitbox_id":  get(r"hitbox_id:\s*(\d+)", int),
        "damage":     get(r"damage:\s*Constant\((\d+(?:\.\d+)?)\)", float),
        "trajectory": get(r"trajectory:\s*(\d+)", int),
        "wdsk":       get(r"wdsk:\s*(\d+)", int) or 0,
        "kbg":        get(r"kbg:\s*(\d+)", int),
        "bkb":        get(r"bkb:\s*(\d+)", int),
        "size":       get(r"size:\s*(\d+(?:\.\d+)?)", float),
        "x_offset":   get(r"x_offset:\s*(-?\d+(?:\.\d+)?)", float),
        "y_offset":   get(r"y_offset:\s*(-?\d+(?:\.\d+)?)", float),
        "z_offset":   get(r"z_offset:\s*(-?\d+(?:\.\d+)?)", float),
        "ground":     get(r"ground:\s*(true|false)", lambda v: v == "true"),
        "aerial":     get(r"aerial:\s*(true|false)", lambda v: v == "true"),
        "is_grab_box": False,
    }


def parse_grabbox_args(s):
    """Parse a CreateGrabBox argument string; damage/KB fields are zeroed (grabs carry no PM knockback data)."""
    def get(pattern, conv=str):
        m = re.search(pattern, s)
        return conv(m.group(1)) if m else None

    return {
        "bone_index": get(r"bone_index:\s*(\d+)", int),
        "hitbox_id":  get(r"hitbox_id:\s*(\d+)", int),
        "size":       get(r"size:\s*(\d+(?:\.\d+)?)", float),
        "x_offset":   get(r"x_offset:\s*(-?\d+(?:\.\d+)?)", float),
        "y_offset":   get(r"y_offset:\s*(-?\d+(?:\.\d+)?)", float),
        "z_offset":   get(r"z_offset:\s*(-?\d+(?:\.\d+)?)", float),
        "ground":     True,
        "aerial":     True,
        "damage":     0.0,
        "trajectory": 0,
        "wdsk":       0,
        "kbg":        0,
        "bkb":        0,
        "is_grab_box": True,
    }


def is_grab(text):
    return "CreateGrabBox" in text


# ── PM script parsing ────────────────────────────────────────────────────────────

def split_angled_blocks(text):
    """Split a concatenated 3-variant input file into (forward, down, up) text blocks."""
    pm_prefixes = ("AsyncWait", "SyncWait", "CreateHitBox", "DeleteAllHitBoxes",
                   "AllowInterrupts", "BoolVariable", "CreateGrabBox", "DeleteAllGrabBoxes",
                   "Subroutine", "--")
    blocks = []
    current = []
    seen_pm = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            current.append(line)
            continue
        is_pm = any(stripped.startswith(p) for p in pm_prefixes)
        if is_pm:
            seen_pm = True
            current.append(line)
        else:
            if seen_pm:
                blocks.append("\n".join(current))
                current = []
                seen_pm = False
            current.append(line)

    if current:
        blocks.append("\n".join(current))

    return blocks


def split_charged_blocks(text):
    """Split a concatenated multi-animation input file into blocks by move name headers.
    A move name header is a line matching ^[A-Z][A-Za-z0-9]+$ that is not a bare PM keyword.
    Lines before the first move name header (description/preamble) are discarded.
    This handles unknown commands (ExternalGraphicEffect, loop, etc.) without needing to whitelist them.
    """
    _PM_BARE = {"DeleteAllHitBoxes", "DeleteAllGrabBoxes", "AllowInterrupts"}

    def _is_move_name(line):
        s = line.strip()
        return bool(re.match(r'^[A-Z][A-Za-z0-9]+$', s)) and s not in _PM_BARE

    blocks = []
    current = None  # None = still in preamble

    for line in text.splitlines():
        if _is_move_name(line):
            if current is not None:
                blocks.append("\n".join(current))
            current = [line]
        else:
            if current is not None:
                current.append(line)

    if current is not None:
        blocks.append("\n".join(current))

    return blocks


def extract_move_name(text):
    """Return the move name if the first non-blank line is not a PM command, else None."""
    pm_prefixes = ("AsyncWait", "SyncWait", "CreateHitBox", "DeleteAllHitBoxes",
                   "AllowInterrupts", "BoolVariable", "CreateGrabBox", "DeleteAllGrabBoxes",
                   "Subroutine", "--")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(line.startswith(p) for p in pm_prefixes):
            return None
        return line
    return None


def extract_file_params(text):
    """Return (total_frames, landing_lag) from line 2.
    Accepts 'N, M' (both values) or just 'N' (total_frames only; landing_lag returns None).
    """
    pm_prefixes = ("AsyncWait", "SyncWait", "CreateHitBox", "DeleteAllHitBoxes",
                   "AllowInterrupts", "BoolVariable", "CreateGrabBox", "DeleteAllGrabBoxes",
                   "Subroutine", "--")
    found_header = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if not found_header:
            if any(line.startswith(p) for p in pm_prefixes):
                return None, None
            found_header = True
            continue
        m = re.match(r"^(\d+)\s*,\s*(\d+)$", line)
        if m:
            return int(m.group(1)), int(m.group(2))
        m = re.match(r"^(\d+)$", line)
        if m:
            return int(m.group(1)), None
        return None, None
    return None, None


def parse_pm(text, bones, bone_parents):
    frame = 0
    startup_frame = None
    active_end = None
    allow_interrupts = None
    snapshots = []
    delete_frames = []

    pm_prefixes = ("AsyncWait", "SyncWait", "CreateHitBox", "DeleteAllHitBoxes",
                   "AllowInterrupts", "BoolVariable", "CreateGrabBox", "DeleteAllGrabBoxes",
                   "Subroutine", "--")
    header_lines_skipped = 0

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("--"):
            continue
        # Skip the move-name header line and the optional params line (N, M)
        if header_lines_skipped < 2 and not any(line.startswith(p) for p in pm_prefixes):
            header_lines_skipped += 1
            continue

        m = re.match(r"AsyncWait\((\d+(?:\.\d+)?)\)", line)
        if m:
            frame = int(float(m.group(1)))
            continue

        m = re.match(r"SyncWait\((\d+(?:\.\d+)?)\)", line)
        if m:
            frame += int(float(m.group(1)))
            continue

        m = re.match(r"CreateHitBox\(HitBoxArguments \{(.+)\}\)", line)
        if m:
            args = parse_hitbox_args(m.group(1))
            args["bone_name"] = bones.get(args["bone_index"], f"Bone{args['bone_index']}")
            args["parent_bone_name"] = bone_parents.get(args["bone_name"], "")
            if startup_frame is None:
                startup_frame = frame
            snapshots.append({"frame": frame, "args": args})
            continue

        if line == "DeleteAllHitBoxes":
            active_end = frame
            delete_frames.append(frame)
            continue

        m = re.match(r"CreateGrabBox\(GrabBoxArguments \{(.+)\}\)", line)
        if m:
            args = parse_grabbox_args(m.group(1))
            args["bone_name"] = bones.get(args["bone_index"], f"Bone{args['bone_index']}")
            args["parent_bone_name"] = bone_parents.get(args["bone_name"], "")
            if startup_frame is None:
                startup_frame = frame
            snapshots.append({"frame": frame, "args": args})
            continue

        if line == "DeleteAllGrabBoxes":
            active_end = frame
            delete_frames.append(frame)
            continue

        if line == "AllowInterrupts" or ("BoolVariableSetTrue" in line and "EnableActionTransition" in line):
            allow_interrupts = frame

    return {
        "startup_frames": startup_frame or 0,
        "active_end": active_end or 0,
        "allow_interrupts": allow_interrupts,
        "snapshots": snapshots,
        "delete_frames": delete_frames,
    }


# ── Phase and hitbox grouping ────────────────────────────────────────────────────

def build_phases(data):
    """Group hitbox snapshots by frame into phases (Early/Late/etc) and compute each phase's duration."""
    startup = data["startup_frames"]
    snapshots = data["snapshots"]
    delete_frames = sorted(data["delete_frames"])

    phase_frames = sorted(set(s["frame"] for s in snapshots))
    labels = ["Early", "Late", "Late2", "Late3"]

    phases = []
    for i, pf in enumerate(phase_frames):
        label = labels[i] if i < len(labels) else f"Phase{i}"
        start_rel = pf - startup
        # End of this phase = the first DeleteAllHitBoxes after pf, unless the next
        # phase starts before that delete (meaning they share an active block).
        my_delete = next((df for df in delete_frames if df > pf), None)
        next_pf = phase_frames[i + 1] if i + 1 < len(phase_frames) else None
        if next_pf is not None and (my_delete is None or next_pf <= my_delete):
            end_rel = next_pf - startup
        elif my_delete is not None:
            end_rel = my_delete - startup
        else:
            end_rel = start_rel
        duration = end_rel - start_rel

        phase_snaps = [s for s in snapshots if s["frame"] == pf]
        bone_counts = {}
        for s in phase_snaps:
            bone_counts[s["args"]["bone_name"]] = bone_counts.get(s["args"]["bone_name"], 0) + 1

        bone_idx = {}
        hitboxes = []
        for snap_i, s in enumerate(phase_snaps):
            bn = s["args"]["bone_name"]
            if s["args"].get("is_grab_box"):
                hb_name = f"Grab {snap_i + 1}"
            else:
                bone_idx[bn] = bone_idx.get(bn, 0) + 1
                suffix = str(bone_idx[bn]) if bone_counts[bn] > 1 else ""
                hb_name = f"{bn}{suffix} {label}"
            hitboxes.append({
                "name": hb_name,
                "bone_name": bn,
                "label": label,
                "start_rel": start_rel,
                "duration": duration,
                "args": s["args"],
            })

        phases.append({
            "label": label,
            "start_rel": start_rel,
            "duration": duration,
            "hitboxes": hitboxes,
        })

    return phases


def build_on_hit_props(phases):
    """Deduplicate hitbox KB params into named OnHitProperties; hitboxes sharing identical stats share one prop."""
    on_hit = []
    hitbox_to_prop = {}
    seen = {}  # (damage, bkb, kbg, wdsk, trajectory) -> prop_name

    for phase in phases:
        for hb in phase["hitboxes"]:
            a = hb["args"]
            key = (a["damage"], a["bkb"], a["kbg"], a["wdsk"], a["trajectory"])
            if key not in seen:
                damage = int(a["damage"])
                bkb_r2, scaling_r2 = calc_rivals2_kb(damage, a["wdsk"], a["bkb"], a["kbg"])
                angle = SAKURAI_R2_ANGLE if a["trajectory"] == TRAJECTORY_SAKURAI else a["trajectory"]

                # Name by bone (no number suffix) + phase label; use full name if collision
                prop_name = f"{hb['bone_name']} {hb['label']}"
                if any(p["name"] == prop_name for p in on_hit):
                    prop_name = hb["name"]

                on_hit.append({
                    "name": prop_name,
                    "damage": damage,
                    "bkb": round(bkb_r2, 6),
                    "scaling": round(scaling_r2, 6),
                    "angle": angle,
                })
                seen[key] = prop_name
            hitbox_to_prop[hb["name"]] = seen[key]

    return on_hit, hitbox_to_prop


# ── Groundedness helper ──────────────────────────────────────────────────────────

# ── Output generators ────────────────────────────────────────────────────────────

def build_anim_path(move_name, char_code, mod_id):
    if not char_code or not mod_id:
        return ""
    anim_name = f"AN_{char_code}_{move_name}"
    return f"/Script/Engine.AnimSequence'/Game/ModContent/{mod_id}/UnrealAssets/Animation/{anim_name}.{anim_name}'"


def gen_animations(move_name, char_code, mod_id):
    is_aerial = "air" in move_name.lower()
    anim_path = build_anim_path(move_name, char_code, mod_id)
    tagged = [
        ["AttackName", ""],
        ["GroundedAnimation", "" if is_aerial else anim_path],
        ["AerialAnimation", anim_path if is_aerial else "None"],
    ]
    return {"Tagged": tagged}


def gen_attack_properties(move_name, startup_frames, landing_lag_frames, char_code, mod_id):
    is_aerial = "air" in move_name.lower()
    groundedness = "AirOnly" if is_aerial else "GroundOnly"
    landing_anim_name = move_name.replace("Attack", "Landing") if is_aerial else ""
    landing_anim_path = build_anim_path(landing_anim_name, char_code, mod_id) if landing_anim_name else "None"
    tagged = [
        ["Groundedness", groundedness],
        ["LandingLagFrames", str(landing_lag_frames) if is_aerial else "0"],
        ["LandingLagAnimation", landing_anim_path if is_aerial else "None"],
    ]
    tagged += [
        ["RootedType", "None" if is_aerial else "Rooted"],
        ["BReverseType", "None"],
        ["EndInCrouchWhenGrounded", "True" if "lw3" in move_name.lower() else "False"],
    ]
    return {"Tagged": tagged}


def _cancel_full(ctype, cancel_frame, post_key):
    return (
        f'(WindowCancelType={ctype},bIgnoreRightStick=False,WindowCancelFrame={cancel_frame},'
        f'WindowCancelLengthFrames=9999,PostCancelWindowStringTableKey="{post_key}",'
        f'WindowCancelPrerequisite=None,NegatePrerequisite=False,CancellableWhenParried=True,'
        f'bPreseveWindowTimer=False,CancelIntoAttack=None,bConsumeCancelInput=True)'
    )


def _hbw_short(hb_windows):
    parts = []
    for hbw in hb_windows:
        p = [f'HitboxName="{hbw["name"]}"']
        if hbw["start"] != 0:
            p.append(f'StartFrame={hbw["start"]}')
        if hbw["length"] != 0:
            p.append(f'LengthInFrames={hbw["length"]}')
        parts.append(f'({",".join(p)})')
    return f'({",".join(parts)})'


def _hbw_full(hb_windows):
    parts = [
        f'(HitboxName="{hbw["name"]}",StartFrame={hbw["start"]},LengthInFrames={hbw["length"]})'
        for hbw in hb_windows
    ]
    return f'({",".join(parts)})'


def _window_short(name, length, anim_start, anim_length, next_name, iasa, hb_windows, window_cancels=None):
    p = [f'StringTableKey="{name}"', f'WindowLengthFrames={length}']
    if iasa != -1:
        p.append(f'IasaFrame={iasa}')
    if anim_start != 0:
        p.append(f'AnimationStartFrame={anim_start}')
    p.append(f'AnimationLengthFrames={anim_length}')
    if next_name:
        p.append(f'NextWindowStringTableKey="{next_name}"')
    if window_cancels:
        c_parts = [
            f'(WindowCancelType={c["type"]},WindowCancelFrame={c["frame"]},PostCancelWindowStringTableKey="{c["post_key"]}")'
            for c in window_cancels
        ]
        p.append(f'WindowCancels=({",".join(c_parts)})')
    if hb_windows:
        p.append(f'HitboxWindows={_hbw_short(hb_windows)}')
    return f'({",".join(p)})'


def _window_full(name, length, anim_start, anim_length, next_name, iasa, hb_windows, window_cancels=None):
    hbw_str = _hbw_full(hb_windows) if hb_windows else ""
    if window_cancels:
        cancels_str = f'({",".join(_cancel_full(c["type"], c["frame"], c["post_key"]) for c in window_cancels)})'
    else:
        cancels_str = ""
    return (
        f'(StringTableKey="{name}",WindowLengthFrames={length},'
        f'IasaFrame={iasa},AnimationStartFrame={anim_start},'
        f'AnimationLengthFrames={anim_length},'
        f'NextWindowStringTableKey="{next_name if next_name else ""}",'
        f'WindowCancels={cancels_str},VelocityData=,'
        f'MovementProperties={MOVEMENT_PROPS},'
        f'HitboxWindows={hbw_str},'
        f'bRefreshHasHit=True,HurtboxStateChanges=,'
        f'AdvancedProperties={ADVANCED_WINDOW_PROPS},'
        f'LedgeProperties={LEDGE_PROPS})'
    )


def _window_tagged_entries(idx, name, length, anim_start, anim_length, next_name, iasa, hb_windows, window_cancels=None):
    pre = f'Windows.Windows[{idx}]'
    full = _window_full(name, length, anim_start, anim_length, next_name, iasa, hb_windows, window_cancels)
    entries = [
        [pre, full],
        [f'{pre}.StringTableKey', name],
        [f'{pre}.WindowLengthFrames', str(length)],
        [f'{pre}.IasaFrame', str(iasa)],
        [f'{pre}.AnimationStartFrame', str(anim_start)],
        [f'{pre}.AnimationLengthFrames', str(anim_length)],
        [f'{pre}.NextWindowStringTableKey', next_name if next_name else ""],
    ]
    if window_cancels:
        full_cancels = [_cancel_full(c["type"], c["frame"], c["post_key"]) for c in window_cancels]
        cancels_str = f'({",".join(full_cancels)})'
        entries.append([f'{pre}.WindowCancels', cancels_str])
        for j, (c, fc) in enumerate(zip(window_cancels, full_cancels)):
            cpre = f'{pre}.WindowCancels.WindowCancels[{j}]'
            entries += [
                [cpre, fc],
                [f'{cpre}.WindowCancelType', c["type"]],
                [f'{cpre}.bIgnoreRightStick', 'False'],
                [f'{cpre}.WindowCancelFrame', str(c["frame"])],
                [f'{cpre}.WindowCancelLengthFrames', '9999'],
                [f'{cpre}.PostCancelWindowStringTableKey', c["post_key"]],
                [f'{cpre}.WindowCancelPrerequisite', 'None'],
                [f'{cpre}.NegatePrerequisite', 'False'],
                [f'{cpre}.CancellableWhenParried', 'True'],
                [f'{cpre}.bPreseveWindowTimer', 'False'],
                [f'{cpre}.CancelIntoAttack', 'None'],
                [f'{cpre}.bConsumeCancelInput', 'True'],
            ]
    else:
        entries.append([f'{pre}.WindowCancels', ""])
    entries += [
        [f'{pre}.VelocityData', ""],
        [f'{pre}.MovementProperties', MOVEMENT_PROPS],
        [f'{pre}.MovementProperties.Gravity', '-1.000000'],
        [f'{pre}.MovementProperties.MaxFallSpeed', '-1.000000'],
        [f'{pre}.MovementProperties.FrictionGround', '-1.000000'],
        [f'{pre}.MovementProperties.FrictionAir', '-1.000000'],
        [f'{pre}.MovementProperties.CanDrift', 'Default'],
        [f'{pre}.MovementProperties.AirAcceleration', '-1.000000'],
        [f'{pre}.MovementProperties.AirSpeedHorizontalMax', '-1.000000'],
        [f'{pre}.MovementProperties.CanFallThroughPlatforms', 'False'],
        [f'{pre}.MovementProperties.DiminishingReturnsPercentLostPerUse', '0.000000'],
        [f'{pre}.MovementProperties.MinimumDiminishingReturnsValue', '0.000000'],
    ]

    if hb_windows:
        entries.append([f'{pre}.HitboxWindows', _hbw_full(hb_windows)])
        for j, hbw in enumerate(hb_windows):
            hpre = f'{pre}.HitboxWindows.HitboxWindows[{j}]'
            entries.append([hpre,
                f'(HitboxName="{hbw["name"]}",StartFrame={hbw["start"]},LengthInFrames={hbw["length"]})'])
            entries.append([f'{hpre}.HitboxName', hbw["name"]])
            entries.append([f'{hpre}.StartFrame', str(hbw["start"])])
            entries.append([f'{hpre}.LengthInFrames', str(hbw["length"])])
    else:
        entries.append([f'{pre}.HitboxWindows', ""])

    entries += [
        [f'{pre}.bRefreshHasHit', 'True'],
        [f'{pre}.HurtboxStateChanges', ""],
        [f'{pre}.AdvancedProperties', ADVANCED_WINDOW_PROPS],
        [f'{pre}.AdvancedProperties.WindowArmor', '-1'],
        [f'{pre}.AdvancedProperties.AerialAutocancelFrame', '-1'],
        [f'{pre}.AdvancedProperties.CanWallJumpOnFrame', '-1'],
        [f'{pre}.AdvancedProperties.BReverseOnFrame', '-1'],
        [f'{pre}.AdvancedProperties.ToggleECBActiveOnFrame', ''],
        [f'{pre}.AdvancedProperties.ToggleRootedOnFrame', ''],
        [f'{pre}.AdvancedProperties.TurnAroundOnFrame', ''],
        [f'{pre}.AdvancedProperties.ToggleFarFromECBOnFrame', ''],
        [f'{pre}.AdvancedProperties.ToggleCanFastfallOnFrame', ''],
        [f'{pre}.AdvancedProperties.ToggleVisibleOnFrame', ''],
        [f'{pre}.AdvancedProperties.CooldownData', '(CooldownStartFrame=0,CooldownDuration=0)'],
        [f'{pre}.AdvancedProperties.CooldownData.CooldownStartFrame', '0'],
        [f'{pre}.AdvancedProperties.CooldownData.CooldownDuration', '0'],
        [f'{pre}.AdvancedProperties.bDisableHitpauseYOffset', 'False'],
        [f'{pre}.AdvancedProperties.PreserveRotation', 'False'],
        [f'{pre}.LedgeProperties', LEDGE_PROPS],
        [f'{pre}.LedgeProperties.CanGrabLedgeOnFrame', '-1'],
        [f'{pre}.LedgeProperties.LedgeGrabBoxOffset', '(X=0.000000,Y=0.000000)'],
        [f'{pre}.LedgeProperties.LedgeGrabBoxOffset.X', '0.000000'],
        [f'{pre}.LedgeProperties.LedgeGrabBoxOffset.Y', '0.000000'],
        [f'{pre}.LedgeProperties.LedgeGrabBoxDimensions', '(X=0.000000,Y=0.000000)'],
        [f'{pre}.LedgeProperties.LedgeGrabBoxDimensions.X', '0.000000'],
        [f'{pre}.LedgeProperties.LedgeGrabBoxDimensions.Y', '0.000000'],
        [f'{pre}.LedgeProperties.ReleaseLedgeOnFrame', '-1'],
        [f'{pre}.LedgeProperties.StayOnLedge', 'False'],
    ]
    return entries


def _build_win_defs(data, phases, total_frames):
    """Return ordered window definitions as (name, length, anim_start, anim_length, next_name, iasa, hb_windows) tuples."""
    startup = data["startup_frames"]

    if len(phases) == 1:
        phase = phases[0]
        recovery_start = startup + phase["duration"]
        recovery_length = total_frames - recovery_start if total_frames > 0 else -1
        iasa_frame = -1
        if data["allow_interrupts"] is not None:
            iasa_frame = data["allow_interrupts"] - recovery_start
        hb_windows = [{"name": hb["name"], "start": hb["start_rel"], "length": 0}
                      for hb in phase["hitboxes"]]
        return [
            ("Startup", startup, 0, startup, "Active", -1, []),
            ("Active", phase["duration"], startup, phase["duration"], "Recovery", -1, hb_windows),
            ("Recovery", recovery_length, recovery_start, recovery_length, "", iasa_frame, []),
        ]

    # Multi-phase: insert "Between N" only when there is an actual gap between Active windows.
    # Active N duration = max(phase.duration, 1) to avoid zero-length windows.
    active_durs = [max(p["duration"], 1) for p in phases]
    between_durs = [
        phases[i + 1]["start_rel"] - (phases[i]["start_rel"] + phases[i]["duration"])
        for i in range(len(phases) - 1)
    ]

    recovery_start = startup + sum(active_durs) + sum(b for b in between_durs if b > 0)
    recovery_length = total_frames - recovery_start if total_frames > 0 else -1
    iasa_frame = -1
    if data["allow_interrupts"] is not None:
        iasa_frame = data["allow_interrupts"] - recovery_start

    win_defs = [("Startup", startup, 0, startup, "Active 1", -1, [])]
    anim_cursor = startup
    between_counter = 0

    for i, phase in enumerate(phases):
        active_name = f"Active {i + 1}"
        duration = active_durs[i]
        hb_windows = [{"name": hb["name"], "start": 0, "length": duration}
                      for hb in phase["hitboxes"]]

        if i + 1 < len(phases):
            has_gap = between_durs[i] > 0
            next_win = f"Between {between_counter + 1}" if has_gap else f"Active {i + 2}"
        else:
            next_win = "Recovery"

        win_defs.append((active_name, duration, anim_cursor, duration, next_win, -1, hb_windows))
        anim_cursor += duration

        if i + 1 < len(phases) and between_durs[i] > 0:
            between_counter += 1
            bh_dur = between_durs[i]
            win_defs.append((f"Between {between_counter}", bh_dur, anim_cursor, bh_dur, f"Active {i + 2}", -1, []))
            anim_cursor += bh_dur

    win_defs.append(("Recovery", recovery_length, recovery_start, recovery_length, "", iasa_frame, []))
    return win_defs


def _rename_phases_for_variant(phases, suffix):
    for phase in phases:
        for hb in phase["hitboxes"]:
            hb["name"] = f"{hb['name']} {suffix}"


def _build_angled_win_defs(data_fwd, data_dn, data_up, phases_fwd, phases_dn, phases_up, total_frames):
    startup = data_fwd["startup_frames"]

    fwd_start = 0
    dn_start = total_frames
    up_start = 2 * total_frames

    def _hbw(phases):
        if not phases:
            return []
        return [{"name": hb["name"], "start": hb["start_rel"], "length": 0}
                for hb in phases[0]["hitboxes"]]

    def _active_dur(phases):
        return max(phases[0]["duration"], 1) if phases else 1

    def _iasa(data, recovery_start_local):
        if data["allow_interrupts"] is not None:
            return data["allow_interrupts"] - recovery_start_local
        return -1

    adu = _active_dur(phases_fwd)
    add = _active_dur(phases_dn)
    adu2 = _active_dur(phases_up)

    rec_start_fwd = startup + adu
    rec_start_dn = startup + add
    rec_start_up = startup + adu2

    rec_len = lambda rs: (total_frames - rs) if total_frames > 0 else -1

    wc_startup = [
        {"type": "UpDown",   "frame": startup, "post_key": "Active Up"},
        {"type": "DownDown", "frame": startup, "post_key": "Active Down"},
    ]

    # Each tuple: (name, length, anim_start, anim_length, next_name, iasa, hb_windows, window_cancels)
    return [
        ("Startup",       startup,         fwd_start,                         startup,  "Active",        -1,                    [],            wc_startup),
        ("Active",        adu,             fwd_start + startup,               adu,      "Recovery",      -1,                    _hbw(phases_fwd), None),
        ("Recovery",      rec_len(rec_start_fwd), fwd_start + rec_start_fwd, rec_len(rec_start_fwd), "", _iasa(data_fwd, rec_start_fwd), [], None),
        ("Active Down",   add,             dn_start + startup,                add,      "Recovery Down", -1,                    _hbw(phases_dn),  None),
        ("Recovery Down", rec_len(rec_start_dn),  dn_start + rec_start_dn,   rec_len(rec_start_dn),  "", _iasa(data_dn, rec_start_dn),  [], None),
        ("Active Up",     adu2,            up_start + startup,                adu2,     "Recovery Up",   -1,                    _hbw(phases_up),  None),
        ("Recovery Up",   rec_len(rec_start_up),  up_start + rec_start_up,   rec_len(rec_start_up),  "", _iasa(data_up, rec_start_up),  [], None),
    ]


def gen_angled_windows(data_fwd, data_dn, data_up, phases_fwd, phases_dn, phases_up, total_frames):
    win_defs = _build_angled_win_defs(data_fwd, data_dn, data_up, phases_fwd, phases_dn, phases_up, total_frames)

    short_parts = [
        _window_short(name, length, anim_start, anim_length, next_name, iasa, hbw, wc)
        for name, length, anim_start, anim_length, next_name, iasa, hbw, wc in win_defs
    ]
    tagged = [["Windows", f'({",".join(short_parts)})']]

    for idx, (name, length, anim_start, anim_length, next_name, iasa, hbw, wc) in enumerate(win_defs):
        tagged.extend(_window_tagged_entries(idx, name, length, anim_start, anim_length, next_name, iasa, hbw, wc))

    return {"Tagged": tagged}


def _adapt_smash_win_defs(win_defs_7, suffix, offset):
    """Rename and shift win_defs from _build_win_defs for use in charged pipelines.
    - Skips the 'Startup' entry (caller builds Post-Charge separately from it).
    - Appends 'suffix' to Active/Between/Recovery names and their next_name references.
    - Adds 'offset' to every anim_start.
    - Returns 8-tuples with window_cancels=None.
    """
    def _rename(name):
        if not name:
            return ""
        if name == "Active":
            return f"Active{suffix}"
        if name == "Recovery":
            return f"Recovery{suffix}"
        if name.startswith("Active "):
            return f"Active{suffix} {name[7:]}"
        if name.startswith("Between "):
            return f"Between{suffix} {name[8:]}"
        return name

    result = []
    for name, length, anim_start, anim_length, next_name, iasa, hb_windows in win_defs_7:
        if name == "Startup":
            continue
        result.append((_rename(name), length, anim_start + offset, anim_length,
                       _rename(next_name), iasa, hb_windows, None))
    return result


def _build_charged_win_defs(data_smash, phases, start_frames, hold_frames, smash_frames,
                             post_charge_cancels=None):
    """Return window definitions for a charged smash attack.
    Delegates the smash portion to _build_win_defs so multi-phase (Early/Late) moves
    produce the correct Active N / Between N / Recovery windows.
    Each tuple: (name, length, anim_start, anim_length, next_name, iasa, hb_windows, window_cancels)
    """
    smash_offset = start_frames + hold_frames
    smash_win_defs = _build_win_defs(data_smash, phases, smash_frames)

    startup_win = next(w for w in smash_win_defs if w[0] == "Startup")
    post_charge_len, _, _, post_charge_next = startup_win[1], startup_win[2], startup_win[3], startup_win[4]

    adapted = _adapt_smash_win_defs(smash_win_defs, "", smash_offset)
    # first_active_name is the first window of adapted (= post_charge_next with no suffix)
    first_active_name = adapted[0][0] if adapted else post_charge_next

    wc_charge = [{"type": "StrongReleased", "frame": 0, "post_key": "Post-Charge"}]

    return [
        ("Pre-Charge",  start_frames,    0,            start_frames,    "Charge",          -1, [], None),
        ("Charge",      hold_frames,     start_frames, hold_frames,     "Post-Charge",      -1, [], wc_charge),
        ("Post-Charge", post_charge_len, smash_offset, post_charge_len, first_active_name,  -1, [], post_charge_cancels),
    ] + adapted


def gen_charged_windows(data_smash, phases, start_frames, hold_frames, smash_frames):
    win_defs = _build_charged_win_defs(data_smash, phases, start_frames, hold_frames, smash_frames)

    short_parts = [
        _window_short(name, length, anim_start, anim_length, next_name, iasa, hbw, wc)
        for name, length, anim_start, anim_length, next_name, iasa, hbw, wc in win_defs
    ]
    tagged = [["Windows", f'({",".join(short_parts)})']]

    for idx, (name, length, anim_start, anim_length, next_name, iasa, hbw, wc) in enumerate(win_defs):
        tagged.extend(_window_tagged_entries(idx, name, length, anim_start, anim_length, next_name, iasa, hbw, wc))

    return {"Tagged": tagged}


def _build_charged_angled_win_defs(data_fwd, data_dn, data_up, phases_fwd, phases_dn, phases_up,
                                    start_frames, hold_frames, smash_fwd_frames, smash_dn_frames, smash_up_frames):
    """Return window definitions for a charged+angled smash attack.
    Delegates each smash variant to _build_win_defs so multi-phase moves are handled correctly.
    Post-Charge is shared (forward animation); DownDown/UpDown cancels skip directly to the
    first active window of each angled variant.
    Each tuple: (name, length, anim_start, anim_length, next_name, iasa, hb_windows, window_cancels)
    """
    smash_fwd_offset = start_frames + hold_frames
    smash_dn_offset  = smash_fwd_offset + smash_fwd_frames
    smash_up_offset  = smash_dn_offset  + smash_dn_frames

    fwd_win_defs = _build_win_defs(data_fwd, phases_fwd, smash_fwd_frames)
    dn_win_defs  = _build_win_defs(data_dn,  phases_dn,  smash_dn_frames)
    up_win_defs  = _build_win_defs(data_up,  phases_up,  smash_up_frames)

    startup_win    = next(w for w in fwd_win_defs if w[0] == "Startup")
    post_charge_len = startup_win[1]

    adapted_fwd = _adapt_smash_win_defs(fwd_win_defs, "",      smash_fwd_offset)
    adapted_dn  = _adapt_smash_win_defs(dn_win_defs,  " Down", smash_dn_offset)
    adapted_up  = _adapt_smash_win_defs(up_win_defs,  " Up",   smash_up_offset)

    first_active_fwd = adapted_fwd[0][0] if adapted_fwd else "Active"
    first_active_dn  = adapted_dn[0][0]  if adapted_dn  else "Active Down"
    first_active_up  = adapted_up[0][0]  if adapted_up  else "Active Up"

    wc_charge = [{"type": "StrongReleased", "frame": 0,              "post_key": "Post-Charge"}]
    wc_post   = [{"type": "DownDown",       "frame": post_charge_len, "post_key": first_active_dn},
                 {"type": "UpDown",         "frame": post_charge_len, "post_key": first_active_up}]

    return [
        ("Pre-Charge",  start_frames,    0,                start_frames,     "Charge",          -1, [], None),
        ("Charge",      hold_frames,     start_frames,     hold_frames,      "Post-Charge",      -1, [], wc_charge),
        ("Post-Charge", post_charge_len, smash_fwd_offset, post_charge_len,  first_active_fwd,   -1, [], wc_post),
    ] + adapted_fwd + adapted_dn + adapted_up


def gen_charged_angled_windows(data_fwd, data_dn, data_up, phases_fwd, phases_dn, phases_up,
                                start_frames, hold_frames, smash_fwd_frames, smash_dn_frames, smash_up_frames):
    win_defs = _build_charged_angled_win_defs(
        data_fwd, data_dn, data_up, phases_fwd, phases_dn, phases_up,
        start_frames, hold_frames, smash_fwd_frames, smash_dn_frames, smash_up_frames)

    short_parts = [
        _window_short(name, length, anim_start, anim_length, next_name, iasa, hbw, wc)
        for name, length, anim_start, anim_length, next_name, iasa, hbw, wc in win_defs
    ]
    tagged = [["Windows", f'({",".join(short_parts)})']]

    for idx, (name, length, anim_start, anim_length, next_name, iasa, hbw, wc) in enumerate(win_defs):
        tagged.extend(_window_tagged_entries(idx, name, length, anim_start, anim_length, next_name, iasa, hbw, wc))

    return {"Tagged": tagged}


def gen_windows(data, phases, total_frames):
    win_defs = _build_win_defs(data, phases, total_frames)

    short_parts = [
        _window_short(name, length, anim_start, anim_length, next_name, iasa, hbw)
        for name, length, anim_start, anim_length, next_name, iasa, hbw in win_defs
    ]
    tagged = [["Windows", f'({",".join(short_parts)})']]

    for idx, (name, length, anim_start, anim_length, next_name, iasa, hbw) in enumerate(win_defs):
        tagged.extend(_window_tagged_entries(idx, name, length, anim_start, anim_length, next_name, iasa, hbw))

    return {"Tagged": tagged}


def gen_start_windows(move_name, total_frames):
    """Single window for start animations: STK = move name, no hitbox windows."""
    length = total_frames if total_frames > 0 else -1
    win_defs = [(move_name, length, 0, length, "", -1, [])]

    short_parts = [
        _window_short(name, l, anim_start, anim_length, next_name, iasa, hbw)
        for name, l, anim_start, anim_length, next_name, iasa, hbw in win_defs
    ]
    tagged = [["Windows", f'({",".join(short_parts)})']]

    for idx, (name, l, anim_start, anim_length, next_name, iasa, hbw) in enumerate(win_defs):
        tagged.extend(_window_tagged_entries(idx, name, l, anim_start, anim_length, next_name, iasa, hbw))

    return {"Tagged": tagged}


def gen_end_windows(move_name, total_frames, iasa):
    """Single window for end animations: STK = move name, IasaFrame from AllowInterrupts."""
    length = total_frames if total_frames > 0 else -1
    iasa_frame = iasa if iasa is not None else -1
    win_defs = [(move_name, length, 0, length, "", iasa_frame, [])]

    short_parts = [
        _window_short(name, l, anim_start, anim_length, next_name, i, hbw)
        for name, l, anim_start, anim_length, next_name, i, hbw in win_defs
    ]
    tagged = [["Windows", f'({",".join(short_parts)})']]

    for idx, (name, l, anim_start, anim_length, next_name, i, hbw) in enumerate(win_defs):
        tagged.extend(_window_tagged_entries(idx, name, l, anim_start, anim_length, next_name, i, hbw))

    return {"Tagged": tagged}


def _hitbox_full_struct(hb, prop_name, interp_mode="None"):
    a = hb["args"]
    x = a["x_offset"] * UNIT_SCALE
    y = -a["y_offset"] * UNIT_SCALE
    z = a["z_offset"] * UNIT_SCALE
    radius = a["size"] * UNIT_SCALE
    offset_str = f'(X={ff(x)},Y={ff(y)},Z={ff(z)})'
    groundedness = "GroundOrAir" if (a["ground"] and a["aerial"]) else ("GroundOnly" if a["ground"] else "AirOnly")
    return (
        f'(Name="{hb["name"]}",BoneName="{hb["bone_name"]}",OffsetBoneName="",'
        f'Offset={offset_str},bClampToGameplayPlane=False,'
        f'InitialInterpolationMode={interp_mode},InitialInterpolationBoneName="",'
        f'InitialInterpolationOffsetBoneName="",'
        f'InitialInterpolationOffset=(X=0.000000,Y=0.000000,Z=0.000000),'
        f'UseCurrentFrameForInterpolation=False,'
        f'Radius={ff(radius)},CanRehitAfterXFrames=0,HitResponse=Hit,'
        f'CanHitgrabKnockedDownOpponents=False,CanGrabArticles=False,'
        f'OnHitPropertiesName="{prop_name}",Groundedness={groundedness},'
        f'bNeverHitTeammates=False)'
    )


def _hitbox_tagged_entries(idx, hb, prop_name, interp_mode="None"):
    a = hb["args"]
    x = a["x_offset"] * UNIT_SCALE
    y = -a["y_offset"] * UNIT_SCALE
    z = a["z_offset"] * UNIT_SCALE
    radius = a["size"] * UNIT_SCALE
    groundedness = "GroundOrAir" if (a["ground"] and a["aerial"]) else ("GroundOnly" if a["ground"] else "AirOnly")
    pre = f'HitboxAttributes.HitboxAttributes[{idx}]'
    zero_offset = '(X=0.000000,Y=0.000000,Z=0.000000)'
    return [
        [pre, _hitbox_full_struct(hb, prop_name, interp_mode)],
        [f'{pre}.Name', hb["name"]],
        [f'{pre}.BoneName', hb["bone_name"]],
        [f'{pre}.OffsetBoneName', 'None'],
        [f'{pre}.Offset', f'(X={ff(x)},Y={ff(y)},Z={ff(z)})'],
        [f'{pre}.Offset.X', ff(x)],
        [f'{pre}.Offset.Y', ff(y)],
        [f'{pre}.Offset.Z', ff(z)],
        [f'{pre}.bClampToGameplayPlane', 'False'],
        [f'{pre}.InitialInterpolationMode', interp_mode],
        [f'{pre}.InitialInterpolationBoneName', 'None'],
        [f'{pre}.InitialInterpolationOffsetBoneName', 'None'],
        [f'{pre}.InitialInterpolationOffset', zero_offset],
        [f'{pre}.InitialInterpolationOffset.X', '0.000000'],
        [f'{pre}.InitialInterpolationOffset.Y', '0.000000'],
        [f'{pre}.InitialInterpolationOffset.Z', '0.000000'],
        [f'{pre}.UseCurrentFrameForInterpolation', 'False'],
        [f'{pre}.Radius', ff(radius)],
        [f'{pre}.CanRehitAfterXFrames', '0'],
        [f'{pre}.HitResponse', 'Hit'],
        [f'{pre}.CanHitgrabKnockedDownOpponents', 'False'],
        [f'{pre}.CanGrabArticles', 'False'],
        [f'{pre}.OnHitPropertiesName', prop_name],
        [f'{pre}.Groundedness', groundedness],
        [f'{pre}.bNeverHitTeammates', 'False'],
    ]


def _on_hit_full_struct(prop):
    return (
        f'(Name="{prop["name"]}",Damage={prop["damage"]},'
        f'BaseKnockback={ff(prop["bkb"])},KnockbackScaling={ff(prop["scaling"])},'
        f'KnockbackAngle={prop["angle"]},HitEffectName="",HitSoundName="",'
        f'AdvancedOnHitProperties={ADV_ON_HIT_PROPS})'
    )


def _on_hit_tagged_entries(idx, prop):
    pre = f'HitboxOnHitProperties.HitboxOnHitProperties[{idx}]'
    return [
        [pre, _on_hit_full_struct(prop)],
        [f'{pre}.Name', prop["name"]],
        [f'{pre}.Damage', str(prop["damage"])],
        [f'{pre}.BaseKnockback', ff(prop["bkb"])],
        [f'{pre}.KnockbackScaling', ff(prop["scaling"])],
        [f'{pre}.KnockbackAngle', str(prop["angle"])],
        [f'{pre}.HitEffectName', 'None'],
        [f'{pre}.HitSoundName', 'None'],
        [f'{pre}.AdvancedOnHitProperties', ADV_ON_HIT_PROPS],
        [f'{pre}.AdvancedOnHitProperties.SpecialEffect', 'None'],
        [f'{pre}.AdvancedOnHitProperties.HitpauseMultiplier', '1.000000'],
        [f'{pre}.AdvancedOnHitProperties.ExtraHitpauseForOpponent', '0'],
        [f'{pre}.AdvancedOnHitProperties.HitpauseMovementType', 'None'],
        [f'{pre}.AdvancedOnHitProperties.HitpauseMovementOffsetFromHost', '(X=0.000000,Y=0.000000)'],
        [f'{pre}.AdvancedOnHitProperties.HitpauseMovementOffsetFromHost.X', '0.000000'],
        [f'{pre}.AdvancedOnHitProperties.HitpauseMovementOffsetFromHost.Y', '0.000000'],
        [f'{pre}.AdvancedOnHitProperties.HitpauseMovementStrength', '0.500000'],
        [f'{pre}.AdvancedOnHitProperties.SDIMultiplier', '1.000000'],
        [f'{pre}.AdvancedOnHitProperties.ASDIMultiplier', '-1.000000'],
        [f'{pre}.AdvancedOnHitProperties.bCanReverse', 'True'],
        [f'{pre}.AdvancedOnHitProperties.bReverseBasedOnHorizontalSpeed', 'False'],
        [f'{pre}.AdvancedOnHitProperties.bForceFlinch', 'False'],
        [f'{pre}.AdvancedOnHitProperties.GroundTechable', 'True'],
        [f'{pre}.AdvancedOnHitProperties.bIgnoresWeight', 'False'],
        [f'{pre}.AdvancedOnHitProperties.bAutoFloorhuggable', 'False'],
        [f'{pre}.AdvancedOnHitProperties.ProjectileInteraction', 'Default'],
        [f'{pre}.AdvancedOnHitProperties.bForceKnockbackInKnockdown', 'False'],
        [f'{pre}.AdvancedOnHitProperties.bPreserveFacing', 'False'],
        [f'{pre}.AdvancedOnHitProperties.KnockbackAngleMode', 'SpecifiedAngle'],
        [f'{pre}.AdvancedOnHitProperties.HitstunMultiplier', '1.000000'],
        [f'{pre}.AdvancedOnHitProperties.HitfallHitstunMultiplier', '1.000000'],
        [f'{pre}.AdvancedOnHitProperties.ParryReaction', 'Stun'],
        [f'{pre}.AdvancedOnHitProperties.GrabPartnerInteraction', 'None'],
        [f'{pre}.AdvancedOnHitProperties.ExtraShieldStun', '0'],
        [f'{pre}.AdvancedOnHitProperties.ShieldDamageMultiplier', '1.000000'],
        [f'{pre}.AdvancedOnHitProperties.ShieldPushbackMultiplier', '1.000000'],
        [f'{pre}.AdvancedOnHitProperties.ShieldHitpauseMultiplier', '1.000000'],
        [f'{pre}.AdvancedOnHitProperties.FullChargeKnockbackMultiplier', '1.300000'],
        [f'{pre}.AdvancedOnHitProperties.FullChargeDamageMultiplier', '1.600000'],
        [f'{pre}.AdvancedOnHitProperties.FinalBaseKnockback', '0.000000'],
        [f'{pre}.AdvancedOnHitProperties.ForceTumble', 'False'],
        [f'{pre}.AdvancedOnHitProperties.IgnoreKnockbackArmor', 'False'],
        [f'{pre}.AdvancedOnHitProperties.IgnoreSuperArmor', 'False'],
        [f'{pre}.AdvancedOnHitProperties.IgnoreInvincibility', 'False'],
        [f'{pre}.AdvancedOnHitProperties.PreventChaingrabsOnHit', 'False'],
        [f'{pre}.AdvancedOnHitProperties.bIsWindbox', 'False'],
        [f'{pre}.AdvancedOnHitProperties.HitstunAnimationStateOverride', 'None'],
    ]


def gen_hitboxes(phases, on_hit_props, hitbox_to_prop):
    all_hitboxes = [hb for phase in phases for hb in phase["hitboxes"]]

    # Determine interpolation mode: Auto if hitbox directly follows a same-bone hitbox from the prior phase
    interp_modes = {}
    for pi, phase in enumerate(phases):
        prev_by_bone = {hb["bone_name"]: hb for hb in phases[pi - 1]["hitboxes"]} if pi > 0 else {}
        for hb in phase["hitboxes"]:
            prev = prev_by_bone.get(hb["bone_name"])
            if prev and hb["start_rel"] == prev["start_rel"] + prev["duration"]:
                interp_modes[hb["name"]] = "Auto"
            else:
                interp_modes[hb["name"]] = "None"

    # Build HitboxAttributes shorthand
    hba_parts = []
    for hb in all_hitboxes:
        a = hb["args"]
        x = a["x_offset"] * UNIT_SCALE
        y = -a["y_offset"] * UNIT_SCALE
        z = a["z_offset"] * UNIT_SCALE
        radius = a["size"] * UNIT_SCALE
        prop_name = hitbox_to_prop[hb["name"]]
        hba_parts.append(
            f'(Name="{hb["name"]}",BoneName="{hb["bone_name"]}",'
            f'Offset=(X={ff(x)},Y={ff(y)},Z={ff(z)}),'
            f'Radius={ff(radius)},OnHitPropertiesName="{prop_name}")'
        )

    # Build HitboxOnHitProperties shorthand
    hohp_parts = []
    for prop in on_hit_props:
        hohp_parts.append(
            f'(Name="{prop["name"]}",Damage={prop["damage"]},'
            f'BaseKnockback={ff(prop["bkb"])},KnockbackScaling={ff(prop["scaling"])},'
            f'KnockbackAngle={prop["angle"]})'
        )

    tagged = [["HitboxAttributes", f'({",".join(hba_parts)})']]

    for idx, hb in enumerate(all_hitboxes):
        tagged.extend(_hitbox_tagged_entries(idx, hb, hitbox_to_prop[hb["name"]], interp_modes[hb["name"]]))

    tagged.append(["HitboxOnHitProperties", f'({",".join(hohp_parts)})'])

    for idx, prop in enumerate(on_hit_props):
        tagged.extend(_on_hit_tagged_entries(idx, prop))

    return {"Tagged": tagged}


# ── Grab generators ──────────────────────────────────────────────────────────────

def gen_grab_windows(data, phases, total_frames):
    """Generate 03_Windows.txt for grabs: 5 fixed windows — Startup, Active, Recovery, Hold, Release."""
    startup = data["startup_frames"]
    phase = phases[0] if phases else {"duration": 0, "hitboxes": []}
    active_dur = max(phase["duration"], 1)
    recovery_start = startup + active_dur
    recovery_length = max(total_frames - recovery_start, 1) if total_frames > 0 else -1
    iasa_frame = -1
    if data["allow_interrupts"] is not None:
        iasa_frame = data["allow_interrupts"] - recovery_start

    hold_anim_start = startup + active_dur + max(recovery_length, 0)
    release_anim_start = hold_anim_start + GRAB_HOLD_ANIM_FRAMES

    hb_windows = [{"name": hb["name"], "start": 0, "length": active_dur} for hb in phase["hitboxes"]]

    def cancel_full_str(ctype, post):
        return (
            f'(WindowCancelType={ctype},bIgnoreRightStick=False,WindowCancelFrame=-1,'
            f'WindowCancelLengthFrames=9999,PostCancelWindowStringTableKey="{post}",'
            f'WindowCancelPrerequisite=None,NegatePrerequisite=False,CancellableWhenParried=True,'
            f'bPreseveWindowTimer=False,CancelIntoAttack=None,bConsumeCancelInput=True)'
        )

    def cancel_wrap_str(ctype, post):
        return f'({cancel_full_str(ctype, post)})'

    def cancel_short_str(ctype, post):
        return f'((WindowCancelType={ctype},WindowCancelFrame=-1,PostCancelWindowStringTableKey="{post}"))'

    def hurtbox_full_str(state):
        return f'(WindowFrame=0,HurtboxName="None",HurtboxState={state},HurtboxActive=True)'

    def hurtbox_wrap_str(state):
        return f'({hurtbox_full_str(state)})'

    def hurtbox_short_str(state):
        return f'((HurtboxName="None",HurtboxState={state}))'

    hbw_short = _hbw_short(hb_windows) if hb_windows else ""
    hbw_full = _hbw_full(hb_windows) if hb_windows else ""
    adv_short = '(WindowArmor=0)'

    # Top-level Windows short summary string
    startup_s = (
        f'(StringTableKey="Startup",WindowLengthFrames={startup},'
        f'AnimationLengthFrames={startup},NextWindowStringTableKey="Active",'
        f'AdvancedProperties={adv_short})'
    )
    active_s_parts = [
        f'StringTableKey="Active"', f'WindowLengthFrames={active_dur}',
        f'AnimationStartFrame={startup}', f'AnimationLengthFrames={active_dur}',
        f'NextWindowStringTableKey="Recovery"',
        f'WindowCancels={cancel_short_str("OnGrab", "Hold")}',
    ]
    if hbw_short:
        active_s_parts.append(f'HitboxWindows={hbw_short}')
    active_s_parts.append(f'AdvancedProperties={adv_short}')
    active_s = f'({",".join(active_s_parts)})'

    rec_s_parts = [f'StringTableKey="Recovery"', f'WindowLengthFrames={recovery_length}']
    if iasa_frame != -1:
        rec_s_parts.append(f'IasaFrame={iasa_frame}')
    rec_s_parts += [
        f'AnimationStartFrame={recovery_start}', f'AnimationLengthFrames={recovery_length}',
        f'AdvancedProperties={adv_short}',
    ]
    recovery_s = f'({",".join(rec_s_parts)})'

    hold_s = (
        f'(StringTableKey="Hold",WindowLengthFrames={GRAB_HOLD_FRAMES},'
        f'AnimationStartFrame={hold_anim_start},AnimationLengthFrames={GRAB_HOLD_ANIM_FRAMES},'
        f'NextWindowStringTableKey="Release",'
        f'WindowCancels={cancel_short_str("OnThrow", "Release")},'
        f'HurtboxStateChanges={hurtbox_short_str("Ungrabbable")},AdvancedProperties={adv_short})'
    )
    vel_x = ff(GRAB_RELEASE_VELOCITY_X)
    vel_short = f'((Velocity=(X={vel_x},Y=0.000000),HorizontalVelocityType=SetVelocity))'
    vel_full = (
        f'(Velocity=(X={vel_x},Y=0.000000),HorizontalVelocityType=SetVelocity,'
        f'VerticalVelocityType=None,ApplyVelocityOnWindowFrame=0,'
        f'ApplyVelocityUntilFrame=9999,VelocityModifiers=)'
    )
    release_s = (
        f'(StringTableKey="Release",WindowLengthFrames={GRAB_RELEASE_FRAMES},'
        f'AnimationStartFrame={release_anim_start},AnimationLengthFrames={GRAB_RELEASE_FRAMES},'
        f'VelocityData={vel_short},'
        f'HurtboxStateChanges={hurtbox_short_str("Default")},AdvancedProperties={adv_short})'
    )

    tagged = [["Windows", f'({",".join([startup_s, active_s, recovery_s, hold_s, release_s])})']]

    def _mvmt(pre):
        return [
            [f'{pre}.MovementProperties', MOVEMENT_PROPS],
            [f'{pre}.MovementProperties.Gravity', '-1.000000'],
            [f'{pre}.MovementProperties.MaxFallSpeed', '-1.000000'],
            [f'{pre}.MovementProperties.FrictionGround', '-1.000000'],
            [f'{pre}.MovementProperties.FrictionAir', '-1.000000'],
            [f'{pre}.MovementProperties.CanDrift', 'Default'],
            [f'{pre}.MovementProperties.AirAcceleration', '-1.000000'],
            [f'{pre}.MovementProperties.AirSpeedHorizontalMax', '-1.000000'],
            [f'{pre}.MovementProperties.CanFallThroughPlatforms', 'False'],
            [f'{pre}.MovementProperties.DiminishingReturnsPercentLostPerUse', '0.000000'],
            [f'{pre}.MovementProperties.MinimumDiminishingReturnsValue', '0.000000'],
        ]

    def _adv(pre):
        return [
            [f'{pre}.AdvancedProperties', GRAB_ADV_WINDOW_PROPS],
            [f'{pre}.AdvancedProperties.WindowArmor', '0'],
            [f'{pre}.AdvancedProperties.AerialAutocancelFrame', '-1'],
            [f'{pre}.AdvancedProperties.CanWallJumpOnFrame', '-1'],
            [f'{pre}.AdvancedProperties.BReverseOnFrame', '-1'],
            [f'{pre}.AdvancedProperties.ToggleECBActiveOnFrame', ''],
            [f'{pre}.AdvancedProperties.ToggleRootedOnFrame', ''],
            [f'{pre}.AdvancedProperties.TurnAroundOnFrame', ''],
            [f'{pre}.AdvancedProperties.ToggleFarFromECBOnFrame', ''],
            [f'{pre}.AdvancedProperties.ToggleCanFastfallOnFrame', ''],
            [f'{pre}.AdvancedProperties.ToggleVisibleOnFrame', ''],
            [f'{pre}.AdvancedProperties.CooldownData', '(CooldownStartFrame=0,CooldownDuration=0)'],
            [f'{pre}.AdvancedProperties.CooldownData.CooldownStartFrame', '0'],
            [f'{pre}.AdvancedProperties.CooldownData.CooldownDuration', '0'],
            [f'{pre}.AdvancedProperties.bDisableHitpauseYOffset', 'False'],
            [f'{pre}.AdvancedProperties.PreserveRotation', 'False'],
        ]

    def _ledge(pre):
        return [
            [f'{pre}.LedgeProperties', LEDGE_PROPS],
            [f'{pre}.LedgeProperties.CanGrabLedgeOnFrame', '-1'],
            [f'{pre}.LedgeProperties.LedgeGrabBoxOffset', '(X=0.000000,Y=0.000000)'],
            [f'{pre}.LedgeProperties.LedgeGrabBoxOffset.X', '0.000000'],
            [f'{pre}.LedgeProperties.LedgeGrabBoxOffset.Y', '0.000000'],
            [f'{pre}.LedgeProperties.LedgeGrabBoxDimensions', '(X=0.000000,Y=0.000000)'],
            [f'{pre}.LedgeProperties.LedgeGrabBoxDimensions.X', '0.000000'],
            [f'{pre}.LedgeProperties.LedgeGrabBoxDimensions.Y', '0.000000'],
            [f'{pre}.LedgeProperties.ReleaseLedgeOnFrame', '-1'],
            [f'{pre}.LedgeProperties.StayOnLedge', 'False'],
        ]

    def _cancel_entries(pre, ctype, post):
        cf = cancel_full_str(ctype, post)
        return [
            [f'{pre}.WindowCancels', f'({cf})'],
            [f'{pre}.WindowCancels.WindowCancels[0]', cf],
            [f'{pre}.WindowCancels.WindowCancels[0].WindowCancelType', ctype],
            [f'{pre}.WindowCancels.WindowCancels[0].bIgnoreRightStick', 'False'],
            [f'{pre}.WindowCancels.WindowCancels[0].WindowCancelFrame', '-1'],
            [f'{pre}.WindowCancels.WindowCancels[0].WindowCancelLengthFrames', '9999'],
            [f'{pre}.WindowCancels.WindowCancels[0].PostCancelWindowStringTableKey', post],
            [f'{pre}.WindowCancels.WindowCancels[0].WindowCancelPrerequisite', 'None'],
            [f'{pre}.WindowCancels.WindowCancels[0].NegatePrerequisite', 'False'],
            [f'{pre}.WindowCancels.WindowCancels[0].CancellableWhenParried', 'True'],
            [f'{pre}.WindowCancels.WindowCancels[0].bPreseveWindowTimer', 'False'],
            [f'{pre}.WindowCancels.WindowCancels[0].CancelIntoAttack', 'None'],
            [f'{pre}.WindowCancels.WindowCancels[0].bConsumeCancelInput', 'True'],
        ]

    def _hurtbox_entries(pre, state):
        hf = hurtbox_full_str(state)
        return [
            [f'{pre}.HurtboxStateChanges', hurtbox_short_str(state)],
            [f'{pre}.HurtboxStateChanges.HurtboxStateChanges[0]', hf],
            [f'{pre}.HurtboxStateChanges.HurtboxStateChanges[0].WindowFrame', '0'],
            [f'{pre}.HurtboxStateChanges.HurtboxStateChanges[0].HurtboxName', 'None'],
            [f'{pre}.HurtboxStateChanges.HurtboxStateChanges[0].HurtboxState', state],
            [f'{pre}.HurtboxStateChanges.HurtboxStateChanges[0].HurtboxActive', 'True'],
        ]

    def _base(pre, name, length, anim_start, anim_length, next_name, iasa):
        return [
            [f'{pre}.StringTableKey', name],
            [f'{pre}.WindowLengthFrames', str(length)],
            [f'{pre}.IasaFrame', str(iasa)],
            [f'{pre}.AnimationStartFrame', str(anim_start)],
            [f'{pre}.AnimationLengthFrames', str(anim_length)],
            [f'{pre}.NextWindowStringTableKey', next_name],
        ]

    # Window 0: Startup
    pre0 = 'Windows.Windows[0]'
    full0 = (
        f'(StringTableKey="Startup",WindowLengthFrames={startup},'
        f'IasaFrame=-1,AnimationStartFrame=0,AnimationLengthFrames={startup},'
        f'NextWindowStringTableKey="Active",'
        f'WindowCancels=,VelocityData=,MovementProperties={MOVEMENT_PROPS},'
        f'HitboxWindows=,bRefreshHasHit=True,HurtboxStateChanges=,'
        f'AdvancedProperties={GRAB_ADV_WINDOW_PROPS},LedgeProperties={LEDGE_PROPS})'
    )
    tagged += [[pre0, full0]] + _base(pre0, 'Startup', startup, 0, startup, 'Active', -1)
    tagged += [[f'{pre0}.WindowCancels', ''], [f'{pre0}.VelocityData', '']]
    tagged += _mvmt(pre0) + [[f'{pre0}.HitboxWindows', ''], [f'{pre0}.bRefreshHasHit', 'True'], [f'{pre0}.HurtboxStateChanges', '']]
    tagged += _adv(pre0) + _ledge(pre0)

    # Window 1: Active
    pre1 = 'Windows.Windows[1]'
    full1 = (
        f'(StringTableKey="Active",WindowLengthFrames={active_dur},'
        f'IasaFrame=-1,AnimationStartFrame={startup},AnimationLengthFrames={active_dur},'
        f'NextWindowStringTableKey="Recovery",'
        f'WindowCancels={cancel_wrap_str("OnGrab", "Hold")},'
        f'VelocityData=,MovementProperties={MOVEMENT_PROPS},'
        f'HitboxWindows={hbw_full},bRefreshHasHit=True,HurtboxStateChanges=,'
        f'AdvancedProperties={GRAB_ADV_WINDOW_PROPS},LedgeProperties={LEDGE_PROPS})'
    )
    tagged += [[pre1, full1]] + _base(pre1, 'Active', active_dur, startup, active_dur, 'Recovery', -1)
    tagged += _cancel_entries(pre1, 'OnGrab', 'Hold')
    tagged.append([f'{pre1}.VelocityData', ''])
    tagged += _mvmt(pre1)
    if hb_windows:
        tagged.append([f'{pre1}.HitboxWindows', hbw_full])
        for j, hbw in enumerate(hb_windows):
            hpre = f'{pre1}.HitboxWindows.HitboxWindows[{j}]'
            tagged += [
                [hpre, f'(HitboxName="{hbw["name"]}",StartFrame={hbw["start"]},LengthInFrames={hbw["length"]})'],
                [f'{hpre}.HitboxName', hbw["name"]],
                [f'{hpre}.StartFrame', str(hbw["start"])],
                [f'{hpre}.LengthInFrames', str(hbw["length"])],
            ]
    else:
        tagged.append([f'{pre1}.HitboxWindows', ''])
    tagged += [[f'{pre1}.bRefreshHasHit', 'True'], [f'{pre1}.HurtboxStateChanges', '']]
    tagged += _adv(pre1) + _ledge(pre1)

    # Window 2: Recovery
    pre2 = 'Windows.Windows[2]'
    full2 = (
        f'(StringTableKey="Recovery",WindowLengthFrames={recovery_length},'
        f'IasaFrame={iasa_frame},AnimationStartFrame={recovery_start},'
        f'AnimationLengthFrames={recovery_length},'
        f'NextWindowStringTableKey="",'
        f'WindowCancels=,VelocityData=,MovementProperties={MOVEMENT_PROPS},'
        f'HitboxWindows=,bRefreshHasHit=True,HurtboxStateChanges=,'
        f'AdvancedProperties={GRAB_ADV_WINDOW_PROPS},LedgeProperties={LEDGE_PROPS})'
    )
    tagged += [[pre2, full2]] + _base(pre2, 'Recovery', recovery_length, recovery_start, recovery_length, '', iasa_frame)
    tagged += [[f'{pre2}.WindowCancels', ''], [f'{pre2}.VelocityData', '']]
    tagged += _mvmt(pre2) + [[f'{pre2}.HitboxWindows', ''], [f'{pre2}.bRefreshHasHit', 'True'], [f'{pre2}.HurtboxStateChanges', '']]
    tagged += _adv(pre2) + _ledge(pre2)

    # Window 3: Hold
    pre3 = 'Windows.Windows[3]'
    full3 = (
        f'(StringTableKey="Hold",WindowLengthFrames={GRAB_HOLD_FRAMES},'
        f'IasaFrame=-1,AnimationStartFrame={hold_anim_start},AnimationLengthFrames={GRAB_HOLD_ANIM_FRAMES},'
        f'NextWindowStringTableKey="Release",'
        f'WindowCancels={cancel_wrap_str("OnThrow", "Release")},'
        f'VelocityData=,MovementProperties={MOVEMENT_PROPS},'
        f'HitboxWindows=,bRefreshHasHit=True,'
        f'HurtboxStateChanges={hurtbox_wrap_str("Ungrabbable")},'
        f'AdvancedProperties={GRAB_ADV_WINDOW_PROPS},LedgeProperties={LEDGE_PROPS})'
    )
    tagged += [[pre3, full3]] + _base(pre3, 'Hold', GRAB_HOLD_FRAMES, hold_anim_start, GRAB_HOLD_ANIM_FRAMES, 'Release', -1)
    tagged += _cancel_entries(pre3, 'OnThrow', 'Release')
    tagged += [[f'{pre3}.VelocityData', '']]
    tagged += _mvmt(pre3) + [[f'{pre3}.HitboxWindows', ''], [f'{pre3}.bRefreshHasHit', 'True']]
    tagged += _hurtbox_entries(pre3, 'Ungrabbable')
    tagged += _adv(pre3) + _ledge(pre3)

    # Window 4: Release
    pre4 = 'Windows.Windows[4]'
    full4 = (
        f'(StringTableKey="Release",WindowLengthFrames={GRAB_RELEASE_FRAMES},'
        f'IasaFrame=-1,AnimationStartFrame={release_anim_start},AnimationLengthFrames={GRAB_RELEASE_FRAMES},'
        f'NextWindowStringTableKey="",'
        f'WindowCancels=,VelocityData={vel_short},MovementProperties={MOVEMENT_PROPS},'
        f'HitboxWindows=,bRefreshHasHit=True,'
        f'HurtboxStateChanges={hurtbox_wrap_str("Default")},'
        f'AdvancedProperties={GRAB_ADV_WINDOW_PROPS},LedgeProperties={LEDGE_PROPS})'
    )
    tagged += [[pre4, full4]] + _base(pre4, 'Release', GRAB_RELEASE_FRAMES, release_anim_start, GRAB_RELEASE_FRAMES, '', -1)
    tagged += [[f'{pre4}.WindowCancels', '']]
    tagged += [
        [f'{pre4}.VelocityData', vel_short],
        [f'{pre4}.VelocityData.VelocityData[0]', vel_full],
        [f'{pre4}.VelocityData.VelocityData[0].Velocity', f'(X={vel_x},Y=0.000000)'],
        [f'{pre4}.VelocityData.VelocityData[0].Velocity.X', vel_x],
        [f'{pre4}.VelocityData.VelocityData[0].Velocity.Y', '0.000000'],
        [f'{pre4}.VelocityData.VelocityData[0].HorizontalVelocityType', 'SetVelocity'],
        [f'{pre4}.VelocityData.VelocityData[0].VerticalVelocityType', 'None'],
        [f'{pre4}.VelocityData.VelocityData[0].ApplyVelocityOnWindowFrame', '0'],
        [f'{pre4}.VelocityData.VelocityData[0].ApplyVelocityUntilFrame', '9999'],
        [f'{pre4}.VelocityData.VelocityData[0].VelocityModifiers', ''],
    ]
    tagged += _mvmt(pre4) + [[f'{pre4}.HitboxWindows', ''], [f'{pre4}.bRefreshHasHit', 'True']]
    tagged += _hurtbox_entries(pre4, 'Default')
    tagged += _adv(pre4) + _ledge(pre4)

    return {"Tagged": tagged}


def gen_grab_hitboxes(phases):
    """Generate 04_Hitboxes.txt for grabs: HitResponse=Grab, bClampToGameplayPlane=True, no OnHitProperties."""
    all_hitboxes = [hb for phase in phases for hb in phase["hitboxes"]]
    hba_parts = []
    for hb in all_hitboxes:
        a = hb["args"]
        x = a["x_offset"] * UNIT_SCALE
        y = -a["y_offset"] * UNIT_SCALE
        z = a["z_offset"] * UNIT_SCALE
        radius = a["size"] * UNIT_SCALE
        offset_part = f'Offset=(X={ff(x)},Y={ff(y)},Z={ff(z)}),' if (x or y or z) else ''
        hba_parts.append(
            f'(Name="{hb["name"]}",BoneName="{hb["bone_name"]}",'
            f'{offset_part}'
            f'bClampToGameplayPlane=True,Radius={ff(radius)},HitResponse=Grab)'
        )

    tagged = [["HitboxAttributes", f'({",".join(hba_parts)})']]
    zero_offset = '(X=0.000000,Y=0.000000,Z=0.000000)'

    for idx, hb in enumerate(all_hitboxes):
        a = hb["args"]
        x = a["x_offset"] * UNIT_SCALE
        y = -a["y_offset"] * UNIT_SCALE
        z = a["z_offset"] * UNIT_SCALE
        radius = a["size"] * UNIT_SCALE
        pre = f'HitboxAttributes.HitboxAttributes[{idx}]'
        full = (
            f'(Name="{hb["name"]}",BoneName="{hb["bone_name"]}",OffsetBoneName="",'
            f'Offset=(X={ff(x)},Y={ff(y)},Z={ff(z)}),bClampToGameplayPlane=True,'
            f'InitialInterpolationMode=None,InitialInterpolationBoneName="",'
            f'InitialInterpolationOffsetBoneName="",'
            f'InitialInterpolationOffset={zero_offset},'
            f'UseCurrentFrameForInterpolation=False,'
            f'Radius={ff(radius)},CanRehitAfterXFrames=0,HitResponse=Grab,'
            f'CanHitgrabKnockedDownOpponents=False,CanGrabArticles=False,'
            f'OnHitPropertiesName="",Groundedness=GroundOrAir,bNeverHitTeammates=False)'
        )
        tagged += [
            [pre, full],
            [f'{pre}.Name', hb["name"]],
            [f'{pre}.BoneName', hb["bone_name"]],
            [f'{pre}.OffsetBoneName', 'None'],
            [f'{pre}.Offset', f'(X={ff(x)},Y={ff(y)},Z={ff(z)})'],
            [f'{pre}.Offset.X', ff(x)],
            [f'{pre}.Offset.Y', ff(y)],
            [f'{pre}.Offset.Z', ff(z)],
            [f'{pre}.bClampToGameplayPlane', 'True'],
            [f'{pre}.InitialInterpolationMode', 'None'],
            [f'{pre}.InitialInterpolationBoneName', 'None'],
            [f'{pre}.InitialInterpolationOffsetBoneName', 'None'],
            [f'{pre}.InitialInterpolationOffset', zero_offset],
            [f'{pre}.InitialInterpolationOffset.X', '0.000000'],
            [f'{pre}.InitialInterpolationOffset.Y', '0.000000'],
            [f'{pre}.InitialInterpolationOffset.Z', '0.000000'],
            [f'{pre}.UseCurrentFrameForInterpolation', 'False'],
            [f'{pre}.Radius', ff(radius)],
            [f'{pre}.CanRehitAfterXFrames', '0'],
            [f'{pre}.HitResponse', 'Grab'],
            [f'{pre}.CanHitgrabKnockedDownOpponents', 'False'],
            [f'{pre}.CanGrabArticles', 'False'],
            [f'{pre}.OnHitPropertiesName', 'None'],
            [f'{pre}.Groundedness', 'GroundOrAir'],
            [f'{pre}.bNeverHitTeammates', 'False'],
        ]

    tagged.append(["HitboxOnHitProperties", ""])
    return {"Tagged": tagged}


def gen_throw_data():
    """Generate 05_ThrowData.txt — zero-value template; fill in actual throw knockback manually after export."""
    release_kb = (
        f'(Damage=0,BaseKnockback=0.000000,KnockbackScaling=0.000000,'
        f'KnockbackAngle=0,HitstunMultiplier=1.000000,bTechable=True,'
        f'ForceTumble=False,HitstunAnimationStateOverride=None)'
    )
    release_full = (
        f'(ReleaseOffset=(X=0.000000,Y=0.000000),'
        f'ReleaseWindowStringTableKey="Release",'
        f'ThrowKnockbackData={release_kb},'
        f'ArticleThrowVelocity=(X=0.000000,Y=0.000000))'
    )
    throw_full = f'(ThrowReleaseData=({release_full}),ThrownAnimationData=)'
    tagged = [
        ["ThrowData", throw_full],
        ["ThrowData.ThrowReleaseData", f'({release_full})'],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0]", release_full],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ReleaseOffset", "(X=0.000000,Y=0.000000)"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ReleaseOffset.X", "0.000000"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ReleaseOffset.Y", "0.000000"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ReleaseWindowStringTableKey", "Release"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ThrowKnockbackData", release_kb],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ThrowKnockbackData.Damage", "0"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ThrowKnockbackData.BaseKnockback", "0.000000"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ThrowKnockbackData.KnockbackScaling", "0.000000"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ThrowKnockbackData.KnockbackAngle", "0"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ThrowKnockbackData.HitstunMultiplier", "1.000000"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ThrowKnockbackData.bTechable", "True"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ThrowKnockbackData.ForceTumble", "False"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ThrowKnockbackData.HitstunAnimationStateOverride", "None"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ArticleThrowVelocity", "(X=0.000000,Y=0.000000)"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ArticleThrowVelocity.X", "0.000000"],
        ["ThrowData.ThrowReleaseData.ThrowReleaseData[0].ArticleThrowVelocity.Y", "0.000000"],
        ["ThrowData.ThrownAnimationData", ""],
    ]
    return {"Tagged": tagged}


# ── Summary helpers ───────────────────────────────────────────────────────────────

def windows_summary(phases):
    indent = "\n\t- "
    if len(phases) == 1:
        num_windows = 3
        label = "Windows[1] (Active):"
        lines = [f"{label:<22} {len(phases[0]['hitboxes'])} hitbox windows"]
    else:
        between_durs = [
            phases[i + 1]["start_rel"] - (phases[i]["start_rel"] + phases[i]["duration"])
            for i in range(len(phases) - 1)
        ]
        num_between = sum(1 for b in between_durs if b > 0)
        num_windows = 1 + len(phases) + num_between + 1
        win_idx = 1
        lines = []
        for i, p in enumerate(phases):
            label = f"Windows[{win_idx}] (Active {i + 1}):"
            lines.append(f"{label:<22} {len(p['hitboxes'])} hitbox windows")
            win_idx += 1
            if i + 1 < len(phases) and between_durs[i] > 0:
                win_idx += 1
    return f"{num_windows} windows{indent}{indent.join(lines)}"


def hitboxes_summary(phases, on_hit_props):
    num_hb = sum(len(p["hitboxes"]) for p in phases)
    indent = "\n\t- "
    return (
        f"{num_hb} hitbox attributes"
        f"{indent}{'HitboxAttributes:':<22} {num_hb} hitboxes"
        f"{indent}{'OnHitProperties:':<22} {len(on_hit_props)} on-hit properties"
    )


def angled_windows_summary(phases_fwd, phases_dn, phases_up):
    indent = "\n\t- "
    lines = [
        f"{'Windows[0] (Startup):':<22} 2 window cancels",
        f"{'Windows[1] (Active):':<22} {len(phases_fwd[0]['hitboxes']) if phases_fwd else 0} hitbox windows",
        f"{'Windows[3] (Active Down):':<22} {len(phases_dn[0]['hitboxes']) if phases_dn else 0} hitbox windows",
        f"{'Windows[5] (Active Up):':<22} {len(phases_up[0]['hitboxes']) if phases_up else 0} hitbox windows",
    ]
    return f"7 windows (angled){indent}{indent.join(lines)}"


def charged_windows_summary(phases):
    between_durs = [phases[i + 1]["start_rel"] - (phases[i]["start_rel"] + phases[i]["duration"])
                    for i in range(len(phases) - 1)]
    num_between = sum(1 for b in between_durs if b > 0)
    total = 3 + len(phases) + num_between + 1  # Pre-Charge+Charge+Post-Charge + actives + betweens + Recovery
    multi = len(phases) > 1
    indent = "\n\t- "
    lines = [f"{'Windows[1] (Charge):':<24} 1 window cancel (StrongReleased)"]
    win_idx = 3
    for i, p in enumerate(phases):
        name = f"Active {i + 1}" if multi else "Active"
        lines.append(f"{'Windows['+str(win_idx)+'] ('+name+'):':<24} {len(p['hitboxes'])} hitbox windows")
        win_idx += 1
        if i + 1 < len(phases) and between_durs[i] > 0:
            win_idx += 1
    return f"{total} windows (charged){indent}{indent.join(lines)}"


def charged_angled_windows_summary(phases_fwd, phases_dn, phases_up):
    indent = "\n\t- "
    lines = [
        f"{'Windows[1] (Charge):':<28} 1 window cancel (StrongReleased)",
        f"{'Windows[2] (Post-Charge):':<28} 2 window cancels (DownDown, UpDown)",
        f"{'Windows[3] (Active):':<28} {len(phases_fwd[0]['hitboxes']) if phases_fwd else 0} hitbox windows",
        f"{'Windows[5] (Active Down):':<28} {len(phases_dn[0]['hitboxes']) if phases_dn else 0} hitbox windows",
        f"{'Windows[7] (Active Up):':<28} {len(phases_up[0]['hitboxes']) if phases_up else 0} hitbox windows",
    ]
    return f"9 windows (charged+angled){indent}{indent.join(lines)}"


def grab_windows_summary(phases):
    num_hb = len(phases[0]["hitboxes"]) if phases else 0

    def _fmt(counts):
        labels = []
        if counts.get("cancels"):  labels.append(f'{counts["cancels"]} window cancels')
        if counts.get("velocity"): labels.append(f'{counts["velocity"]} velocity data')
        if counts.get("hitboxes"): labels.append(f'{counts["hitboxes"]} hitbox windows')
        if counts.get("hurtbox"):  labels.append(f'{counts["hurtbox"]} hurtbox state changes')
        return ", ".join(labels)

    indent = "\n\t- "
    return (
        f"5 windows"
        f"{indent}{'Windows[1] (Active):':<22} {_fmt({'cancels': 1, 'hitboxes': num_hb})}"
        f"{indent}{'Windows[3] (Hold):':<22} {_fmt({'cancels': 1, 'hurtbox': 1})}"
        f"{indent}{'Windows[4] (Release):':<22} {_fmt({'velocity': 1, 'hurtbox': 1})}"
    )


def grab_hitboxes_summary(phases):
    num_hb = sum(len(p["hitboxes"]) for p in phases)
    indent = "\n\t- "
    return (
        f"{num_hb} hitbox attributes"
        f"{indent}{'HitboxAttributes:':<22} {num_hb} grab hitboxes"
        f"{indent}{'OnHitProperties:':<22} 0 on-hit properties"
    )


# ── Main ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Convert PM hitbox data to Rivals 2 JSON")
    parser.add_argument("input", help="Path to PM script text file")
    parser.add_argument("--move-name", default="", help="Move name (e.g. AttackAirB)")
    parser.add_argument("--total-frames", type=int, default=-1,
                        help="Total animation frame count (for Recovery window length). Default: -1 (placeholder)")
    parser.add_argument("--landing-lag-frames", type=int, default=DEFAULT_LANDING_LAG_FRAMES,
                        help=f"Landing lag frame count. Default: {DEFAULT_LANDING_LAG_FRAMES}")
    parser.add_argument("--char-code", default="",
                        help="Character code used in animation names (e.g. Cap)")
    parser.add_argument("--mod-id", default="",
                        help="Mod content ID used in animation paths (e.g. 3729910023)")
    parser.add_argument("--angled", action="store_true",
                        help="Input file contains three variants (forward, down, up) concatenated in order")
    parser.add_argument("--charged", action="store_true",
                        help="Input file contains pre-charge, charge, and smash animations concatenated in order")
    args = parser.parse_args()

    bones_path = Path(__file__).parent / "bones.csv"
    bones, bone_parents = load_bones(bones_path)

    input_path = Path(args.input).resolve()
    text = input_path.read_text(encoding="utf-8")

    move_name = args.move_name or extract_move_name(text) or ""
    file_total_frames, file_landing_lag = extract_file_params(text)
    total_frames = file_total_frames if file_total_frames is not None else args.total_frames
    landing_lag_frames = file_landing_lag if file_landing_lag is not None else args.landing_lag_frames

    data = parse_pm(text, bones, bone_parents)
    grab = is_grab(text)
    is_start = "start" in move_name.lower()
    is_end = "end" in move_name.lower()
    is_angled = args.angled
    is_charged = args.charged

    if is_angled and not is_charged:
        blocks = split_angled_blocks(text)
        if len(blocks) != 3:
            print(f"Error: --angled requires exactly 3 move blocks in the input file, found {len(blocks)}.", file=sys.stderr)
            sys.exit(1)
        text, text_dn, text_up = blocks
        data = parse_pm(text, bones, bone_parents)
        data_dn = parse_pm(text_dn, bones, bone_parents)
        data_up = parse_pm(text_up, bones, bone_parents)

    if not is_start and not is_end and not is_angled and not is_charged and data["startup_frames"] == 0:
        msg = "no CreateGrabBox commands found." if grab else "no CreateHitBox commands found."
        print(f"Warning: {msg}", file=sys.stderr)

    if is_angled and is_charged:
        blocks = split_charged_blocks(text)
        if len(blocks) != 5:
            print(f"Error: --charged --angled requires exactly 5 move blocks in the input file, found {len(blocks)}.", file=sys.stderr)
            sys.exit(1)
        text_start, text_hold, text_smash_fwd, text_smash_dn, text_smash_up = blocks

        start_frames, _ = extract_file_params(text_start)
        hold_frames, _ = extract_file_params(text_hold)
        smash_fwd_frames, _ = extract_file_params(text_smash_fwd)
        smash_dn_frames, _ = extract_file_params(text_smash_dn)
        smash_up_frames, _ = extract_file_params(text_smash_up)
        start_frames    = start_frames    or 0
        hold_frames     = hold_frames     or 0
        smash_fwd_frames = smash_fwd_frames or total_frames
        smash_dn_frames  = smash_dn_frames  or smash_fwd_frames
        smash_up_frames  = smash_up_frames  or smash_fwd_frames

        data_fwd = parse_pm(text_smash_fwd, bones, bone_parents)
        data_dn  = parse_pm(text_smash_dn,  bones, bone_parents)
        data_up  = parse_pm(text_smash_up,  bones, bone_parents)

        phases_fwd = build_phases(data_fwd)
        phases_dn  = build_phases(data_dn)
        phases_up  = build_phases(data_up)

        _rename_phases_for_variant(phases_fwd, "Fwd")
        _rename_phases_for_variant(phases_dn,  "Dn")
        _rename_phases_for_variant(phases_up,  "Up")

        all_phases = phases_fwd + phases_dn + phases_up
        on_hit_props, hitbox_to_prop = build_on_hit_props(all_phases)
        sections = [
            ("Animations",       None,                                                         gen_animations(move_name, args.char_code, args.mod_id)),
            ("AttackProperties", None,                                                         gen_attack_properties(move_name, data_fwd["startup_frames"], landing_lag_frames, args.char_code, args.mod_id)),
            ("Windows",          charged_angled_windows_summary(phases_fwd, phases_dn, phases_up), gen_charged_angled_windows(data_fwd, data_dn, data_up, phases_fwd, phases_dn, phases_up, start_frames, hold_frames, smash_fwd_frames, smash_dn_frames, smash_up_frames)),
            ("Hitboxes",         hitboxes_summary(all_phases, on_hit_props),                   gen_hitboxes(all_phases, on_hit_props, hitbox_to_prop)),
        ]
    elif is_angled:

        phases_fwd = build_phases(data)
        phases_dn = build_phases(data_dn)
        phases_up = build_phases(data_up)

        _rename_phases_for_variant(phases_fwd, "Fwd")
        _rename_phases_for_variant(phases_dn, "Dn")
        _rename_phases_for_variant(phases_up, "Up")

        all_phases = phases_fwd + phases_dn + phases_up
        on_hit_props, hitbox_to_prop = build_on_hit_props(all_phases)
        sections = [
            ("Animations",       None,                                         gen_animations(move_name, args.char_code, args.mod_id)),
            ("AttackProperties", None,                                         gen_attack_properties(move_name, data["startup_frames"], landing_lag_frames, args.char_code, args.mod_id)),
            ("Windows",          angled_windows_summary(phases_fwd, phases_dn, phases_up), gen_angled_windows(data, data_dn, data_up, phases_fwd, phases_dn, phases_up, total_frames)),
            ("Hitboxes",         hitboxes_summary(all_phases, on_hit_props),   gen_hitboxes(all_phases, on_hit_props, hitbox_to_prop)),
        ]
    elif is_charged:
        blocks = split_charged_blocks(text)
        if len(blocks) != 3:
            print(f"Error: --charged requires exactly 3 move blocks in the input file, found {len(blocks)}.", file=sys.stderr)
            sys.exit(1)
        text_start, text_hold, text_smash = blocks

        start_frames, _ = extract_file_params(text_start)
        hold_frames, _ = extract_file_params(text_hold)
        smash_frames, _ = extract_file_params(text_smash)
        start_frames = start_frames or 0
        hold_frames = hold_frames or 0
        smash_frames = smash_frames or total_frames

        data_smash = parse_pm(text_smash, bones, bone_parents)
        phases = build_phases(data_smash)
        on_hit_props, hitbox_to_prop = build_on_hit_props(phases)

        sections = [
            ("Animations",       None,                                   gen_animations(move_name, args.char_code, args.mod_id)),
            ("AttackProperties", None,                                   gen_attack_properties(move_name, data_smash["startup_frames"], landing_lag_frames, args.char_code, args.mod_id)),
            ("Windows",          charged_windows_summary(phases),        gen_charged_windows(data_smash, phases, start_frames, hold_frames, smash_frames)),
            ("Hitboxes",         hitboxes_summary(phases, on_hit_props), gen_hitboxes(phases, on_hit_props, hitbox_to_prop)),
        ]
    elif is_start:
        sections = [
            ("Animations",       None,       gen_animations(move_name, args.char_code, args.mod_id)),
            ("AttackProperties", None,       gen_attack_properties(move_name, 0, landing_lag_frames, args.char_code, args.mod_id)),
            ("Windows",          "1 window", gen_start_windows(move_name, total_frames)),
        ]
    elif is_end:
        sections = [
            ("Animations",       None,       gen_animations(move_name, args.char_code, args.mod_id)),
            ("AttackProperties", None,       gen_attack_properties(move_name, 0, landing_lag_frames, args.char_code, args.mod_id)),
            ("Windows",          "1 window", gen_end_windows(move_name, total_frames, data["allow_interrupts"])),
        ]
    else:
        phases = build_phases(data)
        if grab:
            sections = [
                ("Animations",       None, gen_animations(move_name, args.char_code, args.mod_id)),
                ("AttackProperties", None, gen_attack_properties(move_name, data["startup_frames"], landing_lag_frames, args.char_code, args.mod_id)),
                ("Windows",          grab_windows_summary(phases),  gen_grab_windows(data, phases, total_frames)),
                ("Hitboxes",         grab_hitboxes_summary(phases), gen_grab_hitboxes(phases)),
                ("ThrowData",        None,                          gen_throw_data()),
            ]
        else:
            on_hit_props, hitbox_to_prop = build_on_hit_props(phases)
            sections = [
                ("Animations",       None,                                   gen_animations(move_name, args.char_code, args.mod_id)),
                ("AttackProperties", None,                                   gen_attack_properties(move_name, data["startup_frames"], landing_lag_frames, args.char_code, args.mod_id)),
                ("Windows",          windows_summary(phases),                gen_windows(data, phases, total_frames)),
                ("Hitboxes",         hitboxes_summary(phases, on_hit_props), gen_hitboxes(phases, on_hit_props, hitbox_to_prop)),
            ]

    out_dir = input_path.parent / move_name
    out_dir.mkdir(exist_ok=True)

    for i, (filename, summary, section_data) in enumerate(sections, start=1):
        if summary:
            print(f"{filename}: {summary}")
        (out_dir / f"{i:02d}_{filename}.txt").write_text(
            json.dumps(section_data, indent="\t"), encoding="utf-8"
        )

    print(f"Written to {out_dir}\\")


if __name__ == "__main__":
    main()
