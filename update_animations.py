import json
import csv
import re
from pathlib import Path

CAP_JSON_PATH = r"D:\ROA2_Modding\character_data\Captain_falcon\UE_Attribs\animations.json"
CLAIREN_JSON_PATH = r"D:\ROA2_Modding\character_data\Captain_falcon\UE_Attribs\clairen_animations_example.json"
CSV_PATH = r"C:\Users\Chris\Downloads\PM_to_roa_animation_Mapping - Sheet1.csv"
MD_OUTPUT_PATH = r"D:\ROA2_Modding\character_data\Captain_falcon\UE_Attribs\animation_mapping.md"

CAP_ANIM_DIR = "/Game/ModContent/3729910023/UnrealAssets/Animation"

SECTIONS = [
    "StateAnimations",
    "AerialGrabbedAnimations",
    "ThrownAnimations",
    "ItemHoldAnimations",
    "AerialItemThrowAnimations",
]


def make_cap_ue_ref(pm_name):
    anim = f"AN_Cap_{pm_name}"
    return f"/Script/Engine.AnimSequence'{CAP_ANIM_DIR}/{anim}.{anim}'"


def parse_inline_animations(inline_str):
    """Parse ((State, "path"),...) into ordered list of (state, raw_value) tuples.
    raw_value is '"quoted_path"' or 'None'.
    """
    pattern = r'\((\w+),\s*((?:"[^"]*")|None)\)'
    return [(m.group(1), m.group(2)) for m in re.finditer(pattern, inline_str)]


def rebuild_inline_animations(entries):
    """Rebuild the inline ((State, value),...) string."""
    parts = ",".join(f"({state}, {value})" for state, value in entries)
    return f"({parts})"


def raw_value_to_path(raw_value):
    """Strip outer double quotes from a raw inline value; returns 'None' for None entries."""
    if raw_value == "None":
        return "None"
    return raw_value[1:-1]


def extract_anim_filename(ue_path):
    """Extract 'AN_Cla_AirDodge' from '/Script/Engine.AnimSequence'/Game/.../AN_Cla_AirDodge.AN_Cla_AirDodge''"""
    last_slash = ue_path.rfind("/")
    if last_slash == -1:
        return ue_path
    after_slash = ue_path[last_slash + 1:].rstrip("'")
    return after_slash.split(".")[0]


def load_clairen_section_map(clairen_data, section_key):
    """Return {state_name: clairen_filename} for states with real (non-None) animations."""
    for key, value in clairen_data["Tagged"]:
        if key == section_key:
            entries = parse_inline_animations(value)
            result = {}
            for state, raw in entries:
                if raw != "None":
                    ue_path = raw_value_to_path(raw)
                    result[state] = extract_anim_filename(ue_path)
            return result
    return {}


def build_cap_map(clairen_section_map, clairen_to_pm):
    """Return {state: (cap_ue_path, clairen_filename, pm_name)} for states that have CSV mappings."""
    result = {}
    for state, clairen_filename in clairen_section_map.items():
        pm_name = clairen_to_pm.get(clairen_filename)
        if pm_name:
            result[state] = (make_cap_ue_ref(pm_name), clairen_filename, pm_name)
    return result


def update_cap_json(cap_data, section_updates):
    """Update Cap's JSON in-place. section_updates: {section_key: cap_map}."""
    tagged = cap_data["Tagged"]
    # Pre-compute the new ordered values for each section by parsing the inline string
    # so we can update the individual indexed entries accurately.
    section_new_values = {}  # section_key -> [new_ue_path_or_None_str, ...]
    for section_key, cap_map in section_updates.items():
        for key, value in tagged:
            if key == section_key:
                entries = parse_inline_animations(value)
                ordered_values = []
                for state, raw in entries:
                    if state in cap_map:
                        ordered_values.append(cap_map[state][0])  # new cap ue_path
                    else:
                        ordered_values.append(raw_value_to_path(raw))  # unchanged
                section_new_values[section_key] = (entries, ordered_values)
                break

    new_tagged = []
    for key, value in tagged:
        updated = False

        # Update section inline strings
        for section_key, cap_map in section_updates.items():
            if key == section_key and section_key in section_new_values:
                entries, ordered_values = section_new_values[section_key]
                new_entries = []
                for i, (state, raw) in enumerate(entries):
                    new_path = ordered_values[i]
                    if new_path == "None":
                        new_entries.append((state, "None"))
                    else:
                        new_entries.append((state, f'"{new_path}"'))
                new_tagged.append([key, rebuild_inline_animations(new_entries)])
                updated = True
                break

        if updated:
            continue

        # Update individual indexed entries like "StateAnimations.StateAnimations[N]"
        for section_key in section_updates:
            pattern = rf'^{re.escape(section_key)}\.{re.escape(section_key)}\[(\d+)\]$'
            m = re.match(pattern, key)
            if m and section_key in section_new_values:
                idx = int(m.group(1))
                _, ordered_values = section_new_values[section_key]
                if idx < len(ordered_values):
                    new_tagged.append([key, ordered_values[idx]])
                else:
                    new_tagged.append([key, value])
                updated = True
                break

        if not updated:
            new_tagged.append([key, value])

    cap_data["Tagged"] = new_tagged


def generate_md(section_clairen_maps, section_cap_maps):
    lines = [
        "# Animation Mapping: Clairen → Captain Falcon",
        "",
        "Mapping between ROA2 state name, Clairen source animation, PM animation name, and the resulting Cap animation.",
        "",
    ]

    section_labels = {
        "StateAnimations": "State Animations",
        "AerialGrabbedAnimations": "Aerial Grabbed Animations",
        "ThrownAnimations": "Thrown Animations",
        "ItemHoldAnimations": "Item Hold Animations",
        "AerialItemThrowAnimations": "Aerial Item Throw Animations",
    }

    for section_key in SECTIONS:
        clairen_map = section_clairen_maps.get(section_key, {})
        cap_map = section_cap_maps.get(section_key, {})

        if not clairen_map:
            continue

        lines.append(f"## {section_labels.get(section_key, section_key)}")
        lines.append("")
        lines.append("| State Name | Clairen File | PM Name | Cap File |")
        lines.append("|---|---|---|---|")

        for state in sorted(clairen_map.keys()):
            clairen_file = clairen_map[state]
            if state in cap_map:
                _, _, pm_name = cap_map[state]
                cap_file = f"AN_Cap_{pm_name}"
            else:
                pm_name = "*(no CSV mapping)*"
                cap_file = "*(left as dummy)*"
            lines.append(f"| {state} | {clairen_file} | {pm_name} | {cap_file} |")

        lines.append("")

    return "\n".join(lines)


def main():
    print("Loading files...")
    with open(CAP_JSON_PATH, "r", encoding="utf-8") as f:
        cap_data = json.load(f)
    with open(CLAIREN_JSON_PATH, "r", encoding="utf-8") as f:
        clairen_data = json.load(f)

    # Build Clairen filename -> PM name lookup (first match wins)
    clairen_to_pm = {}
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            r2_name = row["R2 Name"].strip()
            pm_raw = row["PM Raw"].strip()
            if r2_name and pm_raw and r2_name not in clairen_to_pm:
                clairen_to_pm[r2_name] = pm_raw

    print(f"  Loaded {len(clairen_to_pm)} CSV mappings")

    # Build per-section maps
    section_clairen_maps = {}
    section_cap_maps = {}
    for section_key in SECTIONS:
        clairen_map = load_clairen_section_map(clairen_data, section_key)
        cap_map = build_cap_map(clairen_map, clairen_to_pm)
        section_clairen_maps[section_key] = clairen_map
        section_cap_maps[section_key] = cap_map

        no_csv = [s for s in clairen_map if s not in cap_map]
        print(f"\n{section_key}: {len(clairen_map)} Clairen animations found")
        print(f"  {len(cap_map)} will be mapped to Cap animations")
        if no_csv:
            print(f"  {len(no_csv)} have no CSV mapping and will be left as dummy: {no_csv}")

    # Apply updates
    print("\nUpdating Cap animations.json...")
    update_cap_json(cap_data, section_cap_maps)

    with open(CAP_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cap_data, f, indent="\t", ensure_ascii=False)
    print(f"  Written: {CAP_JSON_PATH}")

    # Generate MD mapping table
    print("\nGenerating mapping table...")
    md_content = generate_md(section_clairen_maps, section_cap_maps)
    with open(MD_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"  Written: {MD_OUTPUT_PATH}")

    print("\nDone.")


if __name__ == "__main__":
    main()
