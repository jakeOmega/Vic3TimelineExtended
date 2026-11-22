#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inject resource deposit blocks into state region files.

Reads deposits_config.json for subgood-to-state mappings (Manganese, Chromium,
Copper, Bauxite, etc.), computes deposit amounts from scores, and writes
updated state region files to map_data/state_regions/.

The output is a full copy of every vanilla state-region file (vanilla's text
passes through untouched: provinces, hubs, `min_cold_effect` /
`max_cold_effect`, ...) with two kinds of edits, deposits from
deposits_config.json and traits from state_trait_config.json. A `.txt` in
map_data/state_regions/ that vanilla no longer ships is deleted, and a config
key that names no vanilla state is an error (exit 1; on a post-load run,
`hard_fails` in the reload's warnings): after a map change, point the key at
its successor (docs/guides/vanilla_patch_runbook.md § 4).

How a deposit lands depends on its building's group, read the way the engine
reads it (vanilla's and the mod's common/buildings and common/building_groups,
a bare redefinition of a vanilla key losing to the copy whose file sorts
first, REPLACE/INJECT applied on top). The engine reads a `resource = { }`
block only for a building whose group chain sets `discoverable_resource = yes`
(bg_discoverable_mining for the mod's mines, vanilla's oil, rubber and gold
fields), and `capped_resources` for the rest. The config's figure is the
state's whole endowment, so where vanilla already places the building in
that state (since 1.15 that is vanilla's copper mine, capped in 84 states)
the larger of the two figures is kept, never both added:
  - discoverable building: one `resource` block, `discovered_amount` =
    vanilla's cap (available from the start, as vanilla had it) and
    `undiscovered_amount` = the rest of the config's figure. Vanilla writes the
    same pair for its gold fields and rubber. Vanilla's capped entry for the
    building goes, in every state, since a cap means nothing to a
    discoverable building.
  - capped building: vanilla's cap is raised to the config's figure; no
    `resource` block (the engine would not read it).
An existing vanilla `resource` block for the building keeps the larger
`undiscovered_amount`.

Usage:
    python resources.py              # Inject deposits + print score table
    python resources.py --table      # Only print deposit score table (no file writes)
"""

import argparse
import json
import re
import sys
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
# [ \t]*, not \s*: the indent must not reach back across a blank line, which a removal would then delete.
TRAITS_RE = re.compile(r"(?m)^([ \t]*)traits\s*=\s*\{([^}]*)\}")
SUBSISTENCE_RE = re.compile(r'(?m)^(\s*)subsistence_building\s*=\s*"[^"]*"\s*$')
CAPPED_RE = re.compile(r"(?m)^([ \t]*)capped_resources\s*=\s*\{([^}]*)\}[ \t]*\n?")
CAPPED_ENTRY_RE = re.compile(r"(\w+)\s*=\s*(\d+)")

_REPLACE_FORMS = ("REPLACE", "TRY_REPLACE", "REPLACE_OR_CREATE")
_INJECT_FORMS = ("INJECT", "TRY_INJECT", "INJECT_OR_CREATE")


def _field(value, name):
    """`name`'s value in a parsed entity, ParadoxFileParser's ('=', {...}) form, or None."""
    body = value[1] if isinstance(value, tuple) and len(value) == 2 else value
    if not isinstance(body, dict) or name not in body:
        return None
    v = body[name]
    v = v[1] if isinstance(v, tuple) and len(v) == 2 else v
    return v.strip('"') if isinstance(v, str) else None


def effective_fields(vanilla_dir: Path, mod_dir: Path, names: set, fields: tuple) -> dict:
    """{entity: {field: value}} for `names` as the engine loads one database.

    Files load in name order across vanilla and the mod, a mod file replacing
    vanilla's of the same name. The first bare definition of a key stands (a
    later one logs `Duplicated key` and is dropped: vanilla's 1.15 copper mine
    in 03_mines.txt beats the mod's in 03_zz_te_mines.txt), a REPLACE form
    replaces it, and an INJECT form sets the fields it names. Only files that
    mention one of `names` are parsed.
    """
    from paradox_file_parser import ParadoxFileParser

    files = {p.name: p for p in sorted(vanilla_dir.glob("*.txt"))}
    files.update({p.name: p for p in sorted(mod_dir.glob("*.txt"))})
    out = {}
    for fname in sorted(files):
        path = files[fname]
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if not any(n in text for n in names):
            continue
        parser = ParadoxFileParser()
        parser.parse_file(str(path), apply_directives=False)
        for raw_key, value in parser.data.items():
            directive, _, key = raw_key.rpartition(":")
            if key not in names:
                continue
            got = {f: _field(value, f) for f in fields}
            if not directive:
                out.setdefault(key, got)
            elif directive in _REPLACE_FORMS:
                if key in out or directive == "REPLACE_OR_CREATE":
                    out[key] = got
            elif directive in _INJECT_FORMS:
                if key in out or directive == "INJECT_OR_CREATE":
                    out.setdefault(key, {f: None for f in fields})
                    out[key].update({f: v for f, v in got.items() if v is not None})
    return out


def discoverable_buildings(game_root: Path, mod_root: Path, buildings: set) -> dict:
    """{building: True if its group chain sets discoverable_resource = yes, False if not}.

    A building neither vanilla nor the mod defines is left out. The closest
    group that sets the flag decides; a chain that never sets it is capped.
    """
    defs = effective_fields(game_root / "common" / "buildings", mod_root / "common" / "buildings",
                            set(buildings), ("building_group",))
    group_dirs = (game_root / "common" / "building_groups", mod_root / "common" / "building_groups")
    groups = {}
    wanted = {d["building_group"] for d in defs.values() if d.get("building_group")}
    while wanted - set(groups):
        found = effective_fields(*group_dirs, wanted - set(groups), ("parent_group", "discoverable_resource"))
        for g in wanted - set(groups):
            groups[g] = found.get(g, {"parent_group": None, "discoverable_resource": None})
        wanted |= {g["parent_group"] for g in groups.values() if g.get("parent_group")}
    out = {}
    for b, d in defs.items():
        group, seen, flag = d.get("building_group"), set(), None
        while group and group not in seen and flag is None:
            seen.add(group)
            flag = groups.get(group, {}).get("discoverable_resource")
            group = groups.get(group, {}).get("parent_group")
        out[b] = flag == "yes"
    return out


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


def process_traits_block(block_text: str, state_name: str, trait_mapping: dict) -> str:
    """Inject state-trait references into a state's `traits = { ... }` block.

    Driven by state_trait_config.json. Dedupes existing entries; if the state
    has no traits block, inserts one after the subsistence_building line.
    An entry written "-state_trait_x" removes vanilla's trait instead, and a
    state left with none loses the line. Early-returns when the state has no
    mapped traits to avoid diff churn.
    """
    entries = trait_mapping.get(state_name)
    if not entries:
        return block_text
    removed = {t[1:] for t in entries if t.startswith("-")}
    new_traits = [t for t in entries if not t.startswith("-")]
    m = TRAITS_RE.search(block_text)
    if m:
        # Vanilla writes some traits unquoted ("state_trait_parana_river" state_trait_terra_roxa); read both.
        existing = re.findall(r'"?([A-Za-z0-9_]+)"?', m.group(2))
        merged = [t for t in dict.fromkeys(existing + new_traits) if t not in removed]
        if merged == existing:
            return block_text
        if not merged:
            return block_text[: m.start()].rstrip(" \t").removesuffix("\n") + block_text[m.end():]
        rebuilt = m.group(1) + 'traits = { ' + ' '.join(f'"{t}"' for t in merged) + ' }'
        return block_text[: m.start()] + rebuilt + block_text[m.end():]
    if not new_traits:
        return block_text
    sm = SUBSISTENCE_RE.search(block_text)
    if not sm:
        return block_text  # extremely rare; skip rather than misplace
    indent = sm.group(1)
    line = f'\n{indent}traits = {{ ' + ' '.join(f'"{t}"' for t in new_traits) + ' }'
    return block_text[: sm.end()] + line + block_text[sm.end():]


def rewrite_capped(block_text: str, indent: str, changes: dict) -> str:
    """Apply {building: cap, or None to remove it} to a state's capped_resources block.

    The block is rebuilt in vanilla's layout only when a change applies; a
    block left empty goes, and a missing one is added before `naval_exit_id`
    (or the closing brace).
    """
    m = CAPPED_RE.search(block_text)
    entries = [(b, int(n)) for b, n in CAPPED_ENTRY_RE.findall(m.group(2))] if m else []
    names = [b for b, _ in entries]
    for building, cap in changes.items():
        if building in names:
            entries[names.index(building)] = (building, cap)
        elif cap is not None:
            entries.append((building, cap))
            names.append(building)
    entries = [(b, n) for b, n in entries if n is not None]
    ind = m.group(1) if m else indent
    block = "".join(
        [f"{ind}capped_resources = {{\n", *(f"{ind}    {b} = {n}\n" for b, n in entries), f"{ind}}}\n"]
    ) if entries else ""
    if m:
        return block_text[: m.start()] + block + block_text[m.end():]
    at = compute_insert_position(block_text)
    return block_text[:at] + block + block_text[at:]


def discovered_resource_block(indent: str, building_type: str, undiscovered: int, discovered: int) -> str:
    """A resource block in vanilla's field order (type, undiscovered_amount, discovered_amount)."""
    lines = [f"{indent}resource = {{", f'{indent}    type = "{building_type}"']
    if undiscovered:
        lines.append(f"{indent}    undiscovered_amount = {undiscovered}")
    if discovered:
        lines.append(f"{indent}    discovered_amount = {discovered}")
    return "\n" + "\n".join(lines) + f"\n{indent}}}\n"


def process_state_block(
    block_text: str,
    state_name: str,
    mapping: dict,
    trait_mapping: dict | None = None,
    discoverable: dict | None = None,
) -> str:
    """Add/merge resource blocks for this state and return modified block text.

    `discoverable` is discoverable_buildings()'s answer. None treats every
    configured building as discoverable and leaves vanilla's caps alone (the
    behavior before 1.15, when no configured building was a vanilla one).
    """
    # Determine indentation based on other keys; default to 4 spaces
    # Find first non-empty line within block to steal indentation
    indent = "    "
    for line in block_text.splitlines():
        ln = line.strip()
        if ln and not ln.startswith("STATE_") and not ln.startswith("}"):
            indent = line[: len(line) - len(line.lstrip())]
            break

    capped_m = CAPPED_RE.search(block_text)
    vanilla_caps = {b: int(n) for b, n in CAPPED_ENTRY_RE.findall(capped_m.group(2))} if capped_m else {}
    wanted = {}
    for subgood, score in mapping.get(state_name, {}).items():
        building_type = SUBGOOD_TO_BGTYPE.get(subgood)
        if not building_type:
            print(
                f"[WARN] Unknown subgood {subgood!r} for {state_name}; skipping.",
                file=sys.stderr,
            )
            continue
        wanted[building_type] = max(wanted.get(building_type, 0), int(new_amount(score, subgood)))
    if discoverable is not None:
        # A vanilla cap on a building the mod reads as discoverable becomes a discovered deposit.
        for building_type in vanilla_caps:
            if discoverable.get(building_type):
                wanted.setdefault(building_type, 0)

    for building_type, amount in wanted.items():
        is_discoverable = True if discoverable is None else discoverable.get(building_type, True)
        cap = vanilla_caps.get(building_type)
        if not is_discoverable:
            # Capped building: vanilla's cap rises to the config's figure.
            if cap is None or amount > cap:
                block_text = rewrite_capped(block_text, indent, {building_type: amount})
            continue
        existing = extract_existing_resource_types(block_text)
        if cap is not None and discoverable is not None and building_type not in existing:
            # Vanilla's cap stays known from the start; the rest of the config's figure is to discover.
            block_text = rewrite_capped(block_text, indent, {building_type: None})
            at = compute_insert_position(block_text)
            new_block = discovered_resource_block(indent, building_type, max(amount - cap, 0), cap)
            block_text = block_text[:at] + new_block + block_text[at:]
            continue
        if amount:
            block_text, _ = upsert_resource(
                block_text, compute_insert_position(block_text), indent, building_type, amount, existing
            )

    #prefix_re = re.compile(rf"(?m)^(\s*){re.escape(state_name)}(\s*=\s*\{{)")
    #block_text = prefix_re.sub(r"\1REPLACE:" + state_name + r"\2", block_text, count=1)

    if trait_mapping:
        block_text = process_traits_block(block_text, state_name, trait_mapping)

    return block_text


def process_file(
    in_path: Path,
    out_path: Path,
    mapping: dict,
    trait_mapping: dict | None = None,
    verbose: bool = True,
    discoverable: dict | None = None,
):
    # utf-8-sig strips any leading BOM so the utf-8-sig write below emits one BOM.
    text = in_path.read_text(encoding="utf-8-sig")
    pieces = []
    last = 0
    changed_any = False

    for name, start, end in iter_state_blocks(text):
        block = text[start : end + 1]
        updated = process_state_block(block, name, mapping, trait_mapping, discoverable)
        pieces.append(text[last:start])
        pieces.append(updated)
        last = end + 1
        if updated != block:
            changed_any = True

    pieces.append(text[last:])
    out_text = "".join(pieces)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text, encoding="utf-8-sig")  # emit Paradox BOM

    if verbose:
        action = "modified" if changed_any else "copied"
        print(f"[{action}] {in_path} -> {out_path}")


def discover_files(root: Path, recursive: bool):
    if recursive:
        yield from (p for p in root.rglob("*.txt") if p.is_file())
    else:
        yield from (p for p in root.glob("*.txt") if p.is_file())


def load_trait_mapping(path: Path) -> dict:
    """Load state_trait_config.json: { STATE_X: [trait_key, ...] }.

    Strips any keys starting with '_' (used for inline JSON comments).
    Returns {} if the file is missing — keeps resources.py usable in repos
    that haven't adopted the trait-injection feature yet.
    """
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for state, traits in data.items():
        if state.startswith("_"):
            continue
        if not isinstance(traits, list):
            raise ValueError(
                f"state_trait_config: value for {state!r} must be a list of trait keys"
            )
        out[state] = [str(t) for t in traits]
    return out


def state_names(files) -> set:
    """Every state key the given state-region files define."""
    names = set()
    for path in files:
        names.update(name for name, _, _ in iter_state_blocks(path.read_text(encoding="utf-8-sig")))
    return names


def _run(verbose: bool) -> dict:
    mapping = load_mapping(mod_path / "deposits_config.json")
    trait_mapping = load_trait_mapping(mod_path / "state_trait_config.json")
    input = base_game_path / "game" / "map_data" / "state_regions"
    output = mod_path / "map_data" / "state_regions"

    files = list(discover_files(input, recursive=True))
    if not files:
        print(f"[ERROR] No .txt files found in {input}; map_data/state_regions/ left as it was.", file=sys.stderr)
        return {"files": 0, "hard_fails": 1}

    # A key vanilla no longer has (a renamed, merged or split state) would be skipped without a word.
    known = state_names(files)
    unmatched = sorted(
        {f"deposits_config.json: {k}" for k in mapping if k not in known}
        | {f"state_trait_config.json: {k}" for k in trait_mapping if k not in known}
    )
    for entry in unmatched:
        print(f"[ERROR] {entry} names no vanilla state region; point it at its successor.", file=sys.stderr)

    capped = set()
    for path in files:
        capped.update(b for m in CAPPED_RE.finditer(path.read_text(encoding="utf-8-sig"))
                      for b, _ in CAPPED_ENTRY_RE.findall(m.group(2)))
    configured = set(SUBGOOD_TO_BGTYPE.values())
    discoverable = discoverable_buildings(base_game_path / "game", mod_path, configured | capped)
    missing = sorted(configured - set(discoverable))
    for building in missing:
        print(f"[ERROR] {building} (SUBGOOD_TO_BGTYPE) is defined by neither vanilla nor the mod.", file=sys.stderr)
    if verbose:
        for building in sorted(configured & set(discoverable)):
            if not discoverable[building]:
                print(f"[INFO] {building} is a capped building: its deposits raise capped_resources.")
        for building in sorted(capped - configured):
            if discoverable.get(building):
                print(f"[INFO] {building}: vanilla's caps become discovered deposits (its group is discoverable).")

    written = set()
    for in_path in files:
        rel = in_path.relative_to(input)
        out_path = output / rel
        process_file(in_path, out_path, mapping, trait_mapping=trait_mapping, verbose=verbose,
                     discoverable=discoverable)
        written.add(out_path.resolve())

    # Every .txt here is this script's copy of a vanilla file; one vanilla dropped or renamed is stale.
    deleted = []
    for stale in sorted(p for p in discover_files(output, recursive=True) if p.resolve() not in written):
        stale.unlink()
        deleted.append(str(stale.relative_to(mod_path)))
        print(f"[deleted] {stale} (no vanilla file of that name)", file=sys.stderr)

    return {
        "files": len(files),
        "deleted": len(deleted),
        "hard_fails": len(unmatched) + len(missing),
        "unmatched_config_keys": unmatched,
        "undefined_buildings": missing,
        "deleted_files": deleted,
    }


def main() -> int:
    return 1 if _run(verbose=True)["hard_fails"] else 0


mod_path = Path(mod_path)
base_game_path = Path(base_game_path)


def regenerate(mod_state=None):
    """Auto-run entrypoint invoked by mod_state_server post-load.

    The summary's `hard_fails` (a config key naming no vanilla state, or a
    configured building nobody defines) lands in the reload's `warnings`.
    """
    return _run(verbose=False)


def print_score_table():
    """Print deposit amounts for each subgood at each score level."""
    print(f"{'Subgood':<35} " + "  ".join(f"{'S' + str(i):>6}" for i in range(1, 11)))
    print("-" * 35 + "  " + "  ".join("-" * 6 for _ in range(10)))
    for key in SUBGOOD_TO_SPREAD.keys():
        amounts = [str(new_amount(i, key)) for i in range(1, 11)]
        print(f"{key:<35} " + "  ".join(f"{a:>6}" for a in amounts))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject resource deposits into state region files")
    parser.add_argument("--table", action="store_true", help="Only print score table, don't write files")
    args = parser.parse_args()

    print_score_table()
    if not args.table:
        print()
        sys.exit(main())
