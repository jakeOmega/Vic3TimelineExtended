#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from path_constants import base_game_path, mod_path

SUBGOOD_TO_BGTYPE = {
    "Manganese": "building_manganese_mine",
    "Chromium": "building_chromium_mine",
    "Specialty Alloys": "building_specialty_alloy_metal_mine",
    "Copper": "building_copper_mine",
    "Bauxite": "building_bauxite_mine",
    "Precious & Minor Base Metals": "building_precious_minor_base_metal_mine",
    "Nickel & Cobalt": "building_nickel_cobalt_mine",
    "Lithium": "building_lithium_mine",
    "Rare Earth Elements": "building_rare_earth_metals_mine",
    "Platinum Group Metals": "building_platinum_group_metals_mine",
    "Graphite": "building_graphite_mine",
    "Phosphate": "building_phosphate_mine",
    "Potash": "building_potash_mine",
    "Industrial Minerals & Salts": "building_industrial_mineral_salt_mine",
}

SUBGOOD_TO_SPREAD = {
    "Nickel & Cobalt": 25,
    "Lithium": 50,
    "Rare Earth Elements": 50,
    "Platinum Group Metals": 50,
    "Graphite": 5,
    "Phosphate": 25,
    "Potash": 50,
    "Industrial Minerals & Salts": 5,
    "Manganese": 10,
    "Chromium": 25,
    "Specialty Alloys": 50,
    "Copper": 10,
    "Bauxite": 10,
    "Precious & Minor Base Metals": 10,
}

SUBGOOD_TO_MAX = {
    "Nickel & Cobalt": 200,
    "Lithium": 200,
    "Rare Earth Elements": 200,
    "Platinum Group Metals": 200,
    "Graphite": 200,
    "Phosphate": 200,
    "Potash": 200,
    "Industrial Minerals & Salts": 200,
    "Manganese": 200,
    "Chromium": 200,
    "Specialty Alloys": 200,
    "Copper": 800,
    "Bauxite": 200,
    "Precious & Minor Base Metals": 200,
}

STATE_START_RE = re.compile(r"(?m)^\s*(STATE_[A-Z0-9_]+)\s*=\s*\{")
NAVAL_EXIT_RE = re.compile(r"(?m)^\s*naval_exit_id\s*=\s*\d+\s*$")
RESOURCE_BLOCK_RE = re.compile(
    r"(?ms)^\s*resource\s*=\s*\{\s*([^{}]*?\{[^{}]*\}[^{}]*?)*[^{}]*?\}", re.MULTILINE
)
TYPE_LINE_RE = re.compile(r'(?m)^\s*type\s*=\s*"([^"]+)"\s*$')
UNDISC_LINE_RE = re.compile(r"(?m)^\s*undiscovered_amount\s*=\s*(\d+)\s*$")


def load_mapping(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Normalize keys/values to str->dict[str,int]
        out = {}
        for state, subgoods in data.items():
            if not isinstance(subgoods, dict):
                continue
            out[state] = {}
            for sg, score in subgoods.items():
                if sg in SUBGOOD_TO_BGTYPE:
                    try:
                        out[state][sg] = int(score)
                    except Exception:
                        raise ValueError(
                            f"Score for {state}/{sg} must be int; got {score!r}"
                        )
                else:
                    print(
                        f"[WARN] Unknown subgood name {sg!r} for state {state}; skipping.",
                        file=sys.stderr,
                    )
        return out
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse JSON mapping: {e}", file=sys.stderr)
        sys.exit(1)


def find_matching_brace(text: str, open_idx: int) -> int:
    """Given index of '{', return index of matching '}' (inclusive)."""
    depth = 0
    for i in range(open_idx, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("Unbalanced braces while parsing state block.")


def iter_state_blocks(text: str):
    """Yield (state_name, start_idx, end_idx_inclusive) for each state block."""
    pos = 0
    while True:
        m = STATE_START_RE.search(text, pos)
        if not m:
            break
        name = m.group(1)
        brace_open = text.find("{", m.end() - 1)
        if brace_open == -1:
            raise ValueError(f"Missing '{{' after state {name}")
        brace_close = find_matching_brace(text, brace_open)
        yield name, m.start(), brace_close
        pos = brace_close + 1


def extract_existing_resource_types(block_text: str) -> dict:
    """Return {building_type: (block_start_idx, block_end_idx)} for resource blocks within block_text."""
    existing = {}
    for m in RESOURCE_BLOCK_RE.finditer(block_text):
        block = m.group(0)
        # Find type within this block
        tm = TYPE_LINE_RE.search(block)
        if tm:
            building_type = tm.group(1).strip()
            existing[building_type] = (m.start(), m.end())
    return existing


def upsert_resource(
    block_text: str,
    insert_at: int,
    indent: str,
    building_type: str,
    amount: int,
    existing: dict,
):
    """If a resource block with building_type exists, update its undiscovered_amount=max(existing,new).
    Otherwise, insert a new resource block at insert_at (character index in block_text)."""
    if building_type in existing:
        start, end = existing[building_type]
        sub = block_text[start:end]
        # Update undiscovered_amount line
        um = UNDISC_LINE_RE.search(sub)
        if um:
            old = int(um.group(1))
            new_val = max(old, amount)
            sub_updated = sub[: um.start(1)] + str(new_val) + sub[um.end(1) :]
        else:
            # No undiscovered_amount: append one before closing brace
            close_brace = sub.rfind("}")
            add = f"{indent}    undiscovered_amount = {amount}\n{indent}"
            sub_updated = sub[:close_brace] + add + sub[close_brace:]
        return block_text[:start] + sub_updated + block_text[end:], True
    else:
        new_block = (
            f"\n{indent}resource = {{\n"
            f'{indent}    type = "{building_type}"\n'
            f"{indent}    undiscovered_amount = {amount}\n"
            f"{indent}}}\n"
        )
        return block_text[:insert_at] + new_block + block_text[insert_at:], True


def compute_insert_position(block_text: str) -> int:
    """Return char index inside block_text where new resources should be inserted.
    Prefer right before 'naval_exit_id = …' line, else before final '}'."""
    m = NAVAL_EXIT_RE.search(block_text)
    if m:
        return m.start()
    # otherwise, before final closing brace
    return block_text.rfind("}")


def new_amount(score: int, subgood: str) -> int:
    max_val = SUBGOOD_TO_MAX.get(subgood, 200)
    spread = SUBGOOD_TO_SPREAD.get(subgood, 25)
    new_val = max_val * spread ** ((score - 10) / 9)
    if new_val < 10:
        return int(new_val / 2) * 2
    return int(new_val / 5) * 5


def process_state_block(block_text: str, state_name: str, mapping: dict) -> str:
    """Add/merge resource blocks for this state and return modified block text."""
    # Determine indentation based on other keys; default to 4 spaces
    # Find first non-empty line within block to steal indentation
    indent = "    "
    for line in block_text.splitlines():
        ln = line.strip()
        if ln and not ln.startswith("STATE_") and not ln.startswith("}"):
            indent = line[: len(line) - len(line.lstrip())]
            break

    existing = extract_existing_resource_types(block_text)
    insert_at = compute_insert_position(block_text)

    changed = False
    for subgood, score in mapping.get(state_name, {}).items():
        building_type = SUBGOOD_TO_BGTYPE.get(subgood)
        if not building_type:
            print(
                f"[WARN] Unknown subgood {subgood!r} for {state_name}; skipping.",
                file=sys.stderr,
            )
            continue
        amount = int(new_amount(score, subgood))
        block_text, did = upsert_resource(
            block_text, insert_at, indent, building_type, amount, existing
        )
        if did:
            # If we inserted a new block before insert_at, future insert_at moves forward
            # Recompute existing and insertion point to remain safe for subsequent inserts
            existing = extract_existing_resource_types(block_text)
            insert_at = compute_insert_position(block_text)
            changed = True

    return block_text if changed else block_text


def process_file(in_path: Path, out_path: Path, mapping: dict):
    text = in_path.read_text(encoding="utf-8")
    pieces = []
    last = 0
    changed_any = False

    for name, start, end in iter_state_blocks(text):
        block = text[start : end + 1]
        updated = process_state_block(block, name, mapping)
        pieces.append(text[last:start])
        pieces.append(updated)
        last = end + 1
        if updated != block:
            changed_any = True

    pieces.append(text[last:])
    out_text = "".join(pieces)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text, encoding="utf-8")

    action = "modified" if changed_any else "copied"
    print(f"[{action}] {in_path} -> {out_path}")


def discover_files(root: Path, recursive: bool):
    if recursive:
        yield from (p for p in root.rglob("*.txt") if p.is_file())
    else:
        yield from (p for p in root.glob("*.txt") if p.is_file())


def main():
    deposits_by_type = defaultdict(list)
    amount_by_type = defaultdict(int)
    mapping = load_mapping(mod_path / "deposits_config.json")
    for key, val in mapping.items():
        for subgood, amount in val.items():
            processed_amount = new_amount(amount, subgood)
            deposits_by_type[subgood].append((key, processed_amount))
            amount_by_type[subgood] += processed_amount

    input = base_game_path / "game" / "map_data" / "state_regions"
    output = mod_path / "map_data" / "state_regions"
    recursive = True

    files = list(discover_files(input, recursive))
    if not files:
        print(f"[INFO] No .txt files found in {input}", file=sys.stderr)

    for in_path in files:
        rel = in_path.relative_to(input)
        out_path = output / rel
        process_file(in_path, out_path, mapping)


mod_path = Path(mod_path)
base_game_path = Path(base_game_path)

for key in SUBGOOD_TO_SPREAD.keys():
    print(f"Deposits for {key}:")
    for i in range(1, 11):
        score = i
        amount = new_amount(score, key)
        print(f"\t{key} score {score}: {amount}")

if __name__ == "__main__":
    main()
