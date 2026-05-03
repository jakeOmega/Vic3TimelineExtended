# -*- coding: utf-8 -*-
"""Auto-generate localization for power-bloc principle unlock booleans.

Reads:
    common/modifier_type_definitions/tech_gate_modifier_types.txt
        - the authoritative set of country_*_pb_principles_bool modifiers
    common/power_bloc_principles/extra_power_bloc_principles.txt
        - each principle's `possible = { modifier:<bool> = yes }` clause

Writes:
    localization/english/te_power_bloc_unlocks_l_english.yml
        - one *_desc key per defined unlock bool, naming the tier(s) and
          group(s) it actually unlocks. Always overwrites — the file is
          owned by this generator (and by organize_loc as the final
          re-categorizer; see organize_loc.py POWER_BLOC_UNLOCKS rule).

Runs as a post-load generator from mod_state_server.py before organize_loc.
The unused `mod_state` parameter on regenerate() is kept for parity with
sibling generators; this one parses the source files directly so it also
works as a standalone CLI.

Usage:
    .venv/bin/python gen_pb_principle_unlock_descs.py             # write
    .venv/bin/python gen_pb_principle_unlock_descs.py --dry-run   # preview
"""

import argparse
import logging
import os
import re

from paradox_file_parser import ParadoxFileParser
from path_constants import mod_path

logger = logging.getLogger(__name__)

PRINCIPLES_FILE = os.path.join(
    mod_path, "common", "power_bloc_principles", "extra_power_bloc_principles.txt"
)
TECH_GATE_FILE = os.path.join(
    mod_path, "common", "modifier_type_definitions", "tech_gate_modifier_types.txt"
)
LOC_DIR = os.path.join(mod_path, "localization", "english")
OUTPUT_FILE = os.path.join(LOC_DIR, "te_power_bloc_unlocks_l_english.yml")

ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}

# `principle_construction_4` → group_stem='construction', tier='4'
# `principle_sacred_civics_4_mod` → group_stem='sacred_civics', tier='4'
PRINCIPLE_ID_RE = re.compile(r"^principle_(.+?)_([1-5])(?:_mod)?$")
UNLOCK_BOOL_RE = re.compile(r"^country_[a-z0-9_]+_pb_principles_bool$")

PRINCIPLE_CONCEPT = (
    "[Concept('concept_power_bloc_principle', '$concept_power_bloc_principles$')]"
)
POWER_BLOC_CONCEPT = "[Concept('concept_power_bloc', '$concept_power_blocs$')]"
GROUP_SINGULAR = "[concept_power_bloc_principle_group]"
GROUP_PLURAL = (
    "[Concept('concept_power_bloc_principle_group', "
    "'$concept_power_bloc_principle_groups$')]"
)


def _value_of(node):
    """Unwrap (operator, value) tuples from ParadoxFileParser output."""
    if isinstance(node, tuple) and len(node) >= 2:
        return node[1]
    return node


def _walk_modifier_unlocks(possible_block):
    """Yield every `country_*_pb_principles_bool` referenced by a `possible` block.

    Recurses into OR/AND/NOT/trigger_if/trigger_else/etc. Subscopes — current
    mod data has no nesting, but we'd rather be future-proof.
    """
    if not isinstance(possible_block, dict):
        return
    for key, raw_val in possible_block.items():
        val = _value_of(raw_val)
        if key.startswith("modifier:"):
            mod_name = key[len("modifier:"):]
            if UNLOCK_BOOL_RE.match(mod_name) and val == "yes":
                yield mod_name
        elif isinstance(val, dict):
            yield from _walk_modifier_unlocks(val)
        elif isinstance(val, list):
            for item in val:
                inner = _value_of(item)
                if isinstance(inner, dict):
                    yield from _walk_modifier_unlocks(inner)


def collect_defined_unlock_bools():
    """Return the mod-defined country_*_pb_principles_bool modifiers
    (those with `boolean = yes` in tech_gate_modifier_types.txt)."""
    parser = ParadoxFileParser()
    parser.parse_file(TECH_GATE_FILE, apply_directives=False)
    out = set()
    for key, raw_val in parser.data.items():
        if not UNLOCK_BOOL_RE.match(key):
            continue
        body = _value_of(raw_val)
        if not isinstance(body, dict):
            continue
        if _value_of(body.get("boolean")) == "yes":
            out.add(key)
    return out


def collect_principle_unlocks():
    """Return list of (bool_name, group, tier, principle_id) in file order."""
    parser = ParadoxFileParser()
    parser.parse_file(PRINCIPLES_FILE, apply_directives=False)
    rows = []
    for principle_id, raw_entry in parser.data.items():
        entry = _value_of(raw_entry)
        if not isinstance(entry, dict):
            continue
        possible = _value_of(entry.get("possible"))
        if not isinstance(possible, dict):
            continue
        m = PRINCIPLE_ID_RE.match(principle_id)
        if not m:
            logger.debug("principle id without tier suffix: %s", principle_id)
            continue
        group_stem, tier_str = m.group(1), m.group(2)
        group = f"principle_group_{group_stem}"
        tier = int(tier_str)
        for bool_name in _walk_modifier_unlocks(possible):
            rows.append((bool_name, group, tier, principle_id))
    return rows


def _join_english(items):
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _tier_phrase(tiers):
    tiers = sorted(set(tiers))
    if len(tiers) == 1:
        return f"tier {ROMAN[tiers[0]]}"
    return "tiers " + _join_english([ROMAN[t] for t in tiers])


def _group_ref(group):
    return f"[GetPowerBlocPrincipleGroup('{group}').GetName]"


def render_description(unlocks):
    """Render the desc text for one bool given its (group, tier, _) tuples.

    Three layouts to match the existing canonical phrasing:
        - one group:                       "tier X in the GROUP <singular>"
        - many groups, same tier set:      "tier X in the GROUPS <plural>"
        - many groups, mixed tier sets:    "tier(s) X in GROUP, tier(s) Y in GROUP, ... <plural>"
    """
    by_group = {}
    for group, tier, _pid in unlocks:
        by_group.setdefault(group, [])
        if tier not in by_group[group]:
            by_group[group].append(tier)

    if len(by_group) == 1:
        group, tiers = next(iter(by_group.items()))
        return (
            f"Unlocks {_tier_phrase(tiers)} {PRINCIPLE_CONCEPT} in the "
            f"{_group_ref(group)} {GROUP_SINGULAR} for {POWER_BLOC_CONCEPT}."
        )

    distinct_tier_sets = {tuple(sorted(set(t))) for t in by_group.values()}
    if len(distinct_tier_sets) == 1:
        tiers = list(next(iter(distinct_tier_sets)))
        groups_text = _join_english([_group_ref(g) for g in by_group.keys()])
        return (
            f"Unlocks {_tier_phrase(tiers)} {PRINCIPLE_CONCEPT} in the "
            f"{groups_text} {GROUP_PLURAL} for {POWER_BLOC_CONCEPT}."
        )

    parts = [
        f"{_tier_phrase(tiers)} in the {_group_ref(group)}"
        for group, tiers in by_group.items()
    ]
    return (
        f"Unlocks {PRINCIPLE_CONCEPT} at {_join_english(parts)} {GROUP_PLURAL} "
        f"for {POWER_BLOC_CONCEPT}."
    )


def build_descriptions():
    defined_bools = collect_defined_unlock_bools()
    rows = collect_principle_unlocks()

    grouped = {}
    for bool_name, group, tier, pid in rows:
        grouped.setdefault(bool_name, []).append((group, tier, pid))

    descriptions = {}
    orphans = sorted(defined_bools - set(grouped))
    referenced_undefined = sorted(set(grouped) - defined_bools)

    for bool_name in sorted(defined_bools & set(grouped)):
        descriptions[f"{bool_name}_desc"] = render_description(grouped[bool_name])

    return descriptions, orphans, referenced_undefined


_LOC_LINE_RE = re.compile(r"^\s*([\w\.\-]+)\s*:(.*)$")


def _read_existing_loc_lines():
    """Return {key: 'after-colon-content'} for the existing output file, or {}."""
    if not os.path.exists(OUTPUT_FILE):
        return {}
    out = {}
    with open(OUTPUT_FILE, "r", encoding="utf-8-sig") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped == "l_english:":
                continue
            m = _LOC_LINE_RE.match(line)
            if m:
                out[m.group(1)] = m.group(2).rstrip("\r\n")
    return out


def _format_yml(descriptions, preserved):
    """Render the output yaml. *descriptions* is {key: english_text} for the
    auto-generated _desc keys; *preserved* is {key: 'after-colon-content'}
    for non-desc keys we want to keep verbatim. organize_loc.py owns final
    section headers and formatting; this generator just lays down the keys."""
    lines = ["﻿l_english:"]
    all_keys = set(preserved) | set(descriptions)
    for key in sorted(all_keys):
        if key in descriptions:
            text = descriptions[key].replace('"', '\\"')
            lines.append(f' {key}:0 "{text}"')
        else:
            lines.append(f" {key}:{preserved[key]}")
    return "\n".join(lines) + "\n"


def _existing_keys_match(descriptions, preserved):
    """Return True iff the on-disk file already has identical content
    (ignoring whitespace/header differences imposed by organize_loc)."""
    on_disk = _read_existing_loc_lines()
    expected = {f' {k}:0 "{descriptions[k].replace(chr(34), chr(92)+chr(34))}"'.split(":", 1)[1]: None
                for k in descriptions}
    for k, text in descriptions.items():
        rendered = f'0 "{text.replace(chr(34), chr(92)+chr(34))}"'
        if on_disk.get(k) != rendered:
            return False
    for k, val in preserved.items():
        if on_disk.get(k) != val:
            return False
    # Disallow extra desc keys we don't intend to write
    for k in on_disk:
        if k.endswith("_pb_principles_bool_desc") and k not in descriptions:
            return False
    return True


def write_output(descriptions, dry_run=False):
    existing_lines = _read_existing_loc_lines()
    preserved = {
        key: val for key, val in existing_lines.items()
        if not key.endswith("_pb_principles_bool_desc")
    }

    if _existing_keys_match(descriptions, preserved):
        return False

    if dry_run:
        return True

    new_content = _format_yml(descriptions, preserved)
    with open(OUTPUT_FILE, "wb") as f:
        f.write(new_content.encode("utf-8"))
    return True


def regenerate(mod_state=None, dry_run=False):
    """Post-load entry point. mod_state arg unused (we parse source files directly)."""
    descriptions, orphans, referenced_undefined = build_descriptions()

    for bool_name in orphans:
        logger.warning(
            "[gen_pb_principle_unlock_descs] unlock bool defined but no principle"
            " requires it: %s", bool_name,
        )
    for bool_name in referenced_undefined:
        logger.warning(
            "[gen_pb_principle_unlock_descs] principle requires unlock bool that"
            " is not defined as a modifier type: %s", bool_name,
        )

    wrote = write_output(descriptions, dry_run=dry_run)
    rel_path = os.path.relpath(OUTPUT_FILE, mod_path)
    if wrote:
        verb = "would write" if dry_run else "wrote"
        logger.info(
            "[gen_pb_principle_unlock_descs] %s %d keys to %s",
            verb, len(descriptions), rel_path,
        )
    else:
        logger.info(
            "[gen_pb_principle_unlock_descs] no changes (%d keys, %s)",
            len(descriptions), rel_path,
        )
    return descriptions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="preview the planned output without writing")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    descs = regenerate(dry_run=args.dry_run)
    if args.dry_run:
        print(f"\n--- dry-run preview ({len(descs)} entries) ---")
        for key in sorted(descs):
            print(f' {key}:0 "{descs[key]}"')


if __name__ == "__main__":
    main()
