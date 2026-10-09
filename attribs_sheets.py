#!/usr/bin/env python3
"""
Convert between r2_attribs format and Google Sheets TSV.

Usage:
    python attribs_sheets.py to-sheets <input.txt> [output.tsv]
    python attribs_sheets.py from-sheets <input.tsv> [output.txt]

If the output file is omitted, the result is printed to stdout so you can
pipe it or copy it directly.

Sub-keys (e.g. ECBDimensions.X, EcbBones.EcbBones[0]) are stripped when
going to sheets and automatically rebuilt from the compound parent value
when coming back.
"""

import json
import re
import sys


# ---------------------------------------------------------------------------
# Parsing the r2_attribs format
# ---------------------------------------------------------------------------

def parse_attribs(text):
    """Return [(section_name, tagged_pairs)] from r2_attribs text."""
    sections = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        # Lines that are not JSON tokens are section names.
        if line.startswith('"') or line in ('{', '}', '[', ']'):
            i += 1
            continue
        section_name = line
        # Advance to the opening '{'.
        j = i + 1
        while j < len(lines) and lines[j].strip() != '{':
            j += 1
        if j >= len(lines):
            i += 1
            continue
        # Collect lines until the matching '}'.
        depth = 0
        json_lines = []
        while j < len(lines):
            json_lines.append(lines[j])
            depth += lines[j].count('{') - lines[j].count('}')
            j += 1
            if depth == 0:
                break
        data = json.loads('\n'.join(json_lines))
        sections.append((section_name, data['Tagged']))
        i = j
    return sections


# ---------------------------------------------------------------------------
# Sub-key handling
# ---------------------------------------------------------------------------

def _expand_sub_keys(key, value):
    """Return the sub-key pairs that should follow a compound parent value."""
    # Vector: (X=1.0,Y=2.0)
    m = re.fullmatch(r'\(X=(.*?),Y=(.*?)\)', value)
    if m:
        return [[f'{key}.X', m.group(1)], [f'{key}.Y', m.group(2)]]
    # Array: ("a","b","c")  — sub-key format is Key.Key[index]
    m = re.fullmatch(r'\((.*)\)', value)
    if m:
        items = re.findall(r'"([^"]*)"', m.group(1))
        if items:
            return [[f'{key}.{key}[{i}]', item] for i, item in enumerate(items)]
    return []


# ---------------------------------------------------------------------------
# to-sheets
# ---------------------------------------------------------------------------

def to_tsv(sections):
    """Convert sections to TSV, omitting sub-keys (keys that contain '.')."""
    rows = [['Section', 'Key', 'Value']]
    for section_name, tagged in sections:
        first_in_section = True
        for key, value in tagged:
            if '.' in key:
                continue
            section_col = section_name if first_in_section else ''
            rows.append([section_col, key, value])
            first_in_section = False
    return '\n'.join('\t'.join(row) for row in rows)


# ---------------------------------------------------------------------------
# from-sheets
# ---------------------------------------------------------------------------

def from_tsv(text):
    """Parse TSV from Google Sheets and reconstruct sub-keys."""
    lines = text.splitlines()
    sections = []
    current_section = None
    current_tagged = []

    for line in lines[1:]:  # skip header row
        if not line.strip():
            continue
        parts = line.split('\t')
        while len(parts) < 3:
            parts.append('')
        section, key, value = parts[0], parts[1], parts[2]

        if section:
            if current_section is not None:
                sections.append((current_section, current_tagged))
            current_section = section
            current_tagged = []

        if key:
            current_tagged.append([key, value])
            for sub in _expand_sub_keys(key, value):
                current_tagged.append(sub)

    if current_section is not None:
        sections.append((current_section, current_tagged))

    return sections


# ---------------------------------------------------------------------------
# Serialising back to r2_attribs format
# ---------------------------------------------------------------------------

def to_attribs(sections):
    """Serialise sections back to r2_attribs format."""
    parts = []
    for section_name, tagged in sections:
        json_str = json.dumps({'Tagged': tagged}, indent='\t')
        parts.append(f'{section_name}\n{json_str}')
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    input_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if mode == 'to-sheets':
        sections = parse_attribs(content)
        result = to_tsv(sections)
    elif mode == 'from-sheets':
        sections = from_tsv(content)
        result = to_attribs(sections)
    else:
        print(f"Unknown mode: {mode!r}")
        print(__doc__)
        sys.exit(1)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Written to {output_file}")
    else:
        sys.stdout.write(result)


if __name__ == '__main__':
    main()
