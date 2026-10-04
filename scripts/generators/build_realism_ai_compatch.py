#!/usr/bin/env python3
"""Build the Timeline Extended + Realism AI compatibility patch mod.

Realism Ai Historical Flavor Mod (Workshop 2893069455, mod id
`realism_ai_historical_flavor_mod`) and this mod overlap in five places that
neither can fix from its own files. The analysis is in
docs/guides/mod_compatibility.md; this script writes a small third mod, loaded
after both, that merges the two sides:

- map_data/state_regions/*.txt: both mods ship whole copies of 15 vanilla
  files (RA rescales arable land and capped resources nearly everywhere; we
  add mineral deposits and state traits), and the later-loaded copy wins
  outright. State regions take no INJECT/REPLACE (1.12 inject_types digest),
  so the patch ships RA's files with our deposits and traits applied by
  resources.py's own code, the same as it applies them to vanilla.
- gui/topbar.gui: RA redesigns the top bar; ours widens it and adds the
  Banking phase after MONEY. The patch ships RA's file with our two changes.
- common/ideologies: RA REPLACE_OR_CREATEs 16 vanilla ideologies (mostly to
  give stances on the laws it adds to vanilla law groups), and we REPLACE or
  INJECT the same 16. Whichever file applies last drops the other side's
  stances. The patch REPLACEs each with RA's body plus our
  ideology_modifications.py edits, applied by apply_ideologies.py's own code.
- common/laws: RA TRY_INJECTs modifiers into two laws we REPLACE, so ours wipes
  them. The patch REPLACEs both with our body and RA's modifiers summed in,
  which is what an INJECT does (docs/guides/scripting_best_practices.md).
  A REPLACE rather than a re-INJECT keeps the result independent of the order
  directives apply in, which is assumed, not documented (#557).
- common/country_ranks: RA adds a `super_power` rank above Great Power, which
  none of our per-rank INJECTs reach. The patch gives it our Great Power
  injections, with the monetary interest cancel set to RA's own discount.

Every patch file in common/ sorts last (`zzz_te_realism_ai_*`) and the patch
must load last in the playset, so it wins under either load-order model.

Each part checks its own output and the run stops with an error when an
anchor is missing or a merge didn't take. Afterwards the script rescans both
mods for overlaps the patch doesn't handle (a new same-path file, a key both
define, a GUI type, an event id, a loc key) and prints them; `--strict` makes
those fatal. Rerun after an RA update, and after changing anything the patch
merges: ideology_modifications.py, common/laws/modified.txt,
deposits_config.json, state_trait_config.json, gui/topbar.gui, or our country
rank injections.

The output contains RA's own files (merged). Publishing it needs the RA
author's permission.

Usage:
    python3 scripts/generators/build_realism_ai_compatch.py            # build into build/compat/realism_ai/
    python3 scripts/generators/build_realism_ai_compatch.py --deploy   # build, then copy into the game's mod folder
    python3 scripts/generators/build_realism_ai_compatch.py --check    # exit 1 if the deployed patch is stale
    python3 scripts/generators/build_realism_ai_compatch.py --ra-path <dir>   # RA somewhere other than the Workshop folder
"""

import argparse
import difflib
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import path_constants  # noqa: E402
from paradox_file_parser import ParadoxFileParser  # noqa: E402

RA_WORKSHOP_ID = "2893069455"
RA_MOD_ID = "realism_ai_historical_flavor_mod"
RA_NAME = "Realism Ai Historical Flavor Mod"
PATCH_NAME = "Timeline Extended + Realism AI Compatibility Patch"
PATCH_ID = "vic3timelineextended_realism_ai_compat"
DEPLOY_DIR_NAME = "Vic3TimelineExtended_RealismAI_Compat"
OUT_DIR = REPO / "build" / "compat" / "realism_ai"
FILE_PREFIX = "zzz_te_realism_ai_"

DEPLOYED_DIRS = ("common", "events", "gui", "localization", "map_data", "gfx")
INJECT_FAMILY = {"INJECT", "TRY_INJECT", "INJECT_OR_CREATE"}
REPLACE_FAMILY = {"REPLACE", "TRY_REPLACE", "REPLACE_OR_CREATE"}
DIRECTIVE_RE = re.compile(r"^(INJECT|REPLACE|TRY_INJECT|TRY_REPLACE|REPLACE_OR_CREATE|INJECT_OR_CREATE):(.+)$")
ENTRY_RE = re.compile(r"([A-Za-z0-9_][\w:.\-]*)\s*=\s*\{")
NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


class BuildError(RuntimeError):
    """A part of the patch could not be built or failed its own check."""


# --------------------------------------------------------------------------
# Text helpers
# --------------------------------------------------------------------------


def read_text(path):
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read().replace("\r\n", "\n")


def write_text(path, text, bom=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="\n") as fh:
        fh.write(text)


def mask(text):
    """Blank out comments and quoted strings (same length) so brace matching
    and key scans only see script structure."""
    out = list(text)
    i, n = 0, len(text)
    in_str = in_comment = False
    while i < n:
        c = text[i]
        if in_comment:
            if c == "\n":
                in_comment = False
            else:
                out[i] = " "
        elif in_str:
            if c == "\\" and i + 1 < n:
                out[i] = out[i + 1] = " "
                i += 1
            elif c == '"':
                in_str = False
                out[i] = " "
            elif c != "\n":
                out[i] = " "
        elif c == "#":
            in_comment = True
            out[i] = " "
        elif c == '"':
            in_str = True
            out[i] = " "
        i += 1
    return "".join(out)


def match_brace(masked, open_idx):
    depth = 0
    for i in range(open_idx, len(masked)):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise BuildError(f"unbalanced braces from offset {open_idx}")


def blocks_at_depth(text, masked=None, start=0, end=None, depth_target=0):
    """Yield (key, key_start, open_idx, close_idx) for every `key = {` at
    `depth_target` between start and end."""
    masked = mask(text) if masked is None else masked
    end = len(masked) if end is None else end
    depth = 0
    i = start
    while i < end:
        c = masked[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == depth_target and (i == 0 or not (masked[i - 1].isalnum() or masked[i - 1] in "_:.-")):
            m = ENTRY_RE.match(masked, i)
            if m and m.end() <= end:
                open_idx = m.end() - 1
                close_idx = match_brace(masked, open_idx)
                yield m.group(1), i, open_idx, close_idx
                i = close_idx + 1
                continue
        i += 1


def split_directive(key):
    m = DIRECTIVE_RE.match(key)
    return (m.group(1), m.group(2)) if m else ("", key)


def collect_entries(root, sub):
    """{name: [(directive, file_name, body_text)]} over root/sub/**/*.txt in
    file-name order."""
    out = defaultdict(list)
    base = Path(root) / sub
    if not base.is_dir():
        return out
    for path in sorted(base.rglob("*.txt"), key=lambda p: p.name):
        text = read_text(path)
        for key, _s, o, c in blocks_at_depth(text):
            directive, name = split_directive(key)
            out[name].append((directive, path.name, text[o : c + 1]))
    return out


def parse_text(text):
    """Parse script text with the repo's parser (no directive merging)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(text)
        name = fh.name
    try:
        parser = ParadoxFileParser()
        parser.parse_file(name, apply_directives=False)
        return parser.data
    finally:
        os.unlink(name)


def values(v):
    """A parsed field as a list of values (a repeated key parses to a list)."""
    if isinstance(v, tuple):
        return [v[1]]
    if isinstance(v, list) and v and all(isinstance(x, tuple) for x in v):
        return [x[1] for x in v]
    return [v]


def unquote(s):
    return s.strip('"') if isinstance(s, str) else s


def fmt_number(x):
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# --------------------------------------------------------------------------
# Part 1: state regions
# --------------------------------------------------------------------------


def _deposits_and_traits(state_text):
    """{state: ({(building_type, ...)}, [traits])} from a state_regions file."""
    out = {}
    for state, body in parse_text(state_text).items():
        body = values(body)[0]
        if not isinstance(body, dict):
            continue
        resources = set()
        for res in values(body.get("resource", [])):
            if isinstance(res, dict) and "type" in res:
                resources.add(unquote(values(res["type"])[0]))
        traits = [unquote(t) for t in values(body["traits"])[0]] if "traits" in body else []
        out[state] = (resources, traits, body)
    return out


def build_state_regions(ra, out, log):
    import resources

    mapping = resources.load_mapping(REPO / "deposits_config.json")
    trait_mapping = resources.load_trait_mapping(REPO / "state_trait_config.json")
    our_types = set(resources.SUBGOOD_TO_BGTYPE.values())
    src = ra / "map_data" / "state_regions"
    files = sorted(src.glob("*.txt"))
    if not files:
        raise BuildError(f"no state_regions files in {src}")
    for path in files:
        dst = out / "map_data" / "state_regions" / path.name
        resources.process_file(path, dst, mapping, trait_mapping=trait_mapping, verbose=False)

        ours_path = REPO / "map_data" / "state_regions" / path.name
        if not ours_path.exists():
            raise BuildError(f"RA overrides {path.name}, which this mod doesn't ship; review it by hand")
        merged = _deposits_and_traits(read_text(dst))
        ours = _deposits_and_traits(read_text(ours_path))
        theirs = _deposits_and_traits(read_text(path))
        if set(merged) != set(theirs):
            raise BuildError(f"{path.name}: merged file has different states from RA's")
        for state, (res, traits, body) in merged.items():
            want = ours.get(state, (set(), [], {}))
            missing = (want[0] & our_types) - res
            if missing:
                raise BuildError(f"{path.name} {state}: deposits not applied: {sorted(missing)}")
            lost = set(trait_mapping.get(state, [])) - set(traits)
            if lost:
                raise BuildError(f"{path.name} {state}: traits not applied: {sorted(lost)}")
            ra_body = theirs[state][2]
            for field in set(ra_body) | set(body):
                if field in ("resource", "traits"):
                    continue
                if json.dumps(ra_body.get(field), sort_keys=True) != json.dumps(body.get(field), sort_keys=True):
                    raise BuildError(f"{path.name} {state}: RA's `{field}` changed in the merge")
            lost_ra = theirs[state][0] - res
            if lost_ra or not set(theirs[state][1]) <= set(traits):
                raise BuildError(f"{path.name} {state}: RA's resources or traits were dropped")
    log.append(f"state_regions: {len(files)} files, RA's map with our deposits and traits")


# --------------------------------------------------------------------------
# Part 2: top bar
# --------------------------------------------------------------------------

BANKING_WIDGET = "te_banking_topbar_readings = {}"


def _significant_lines(text):
    return [ln.strip() for ln in mask(text).splitlines() if ln.strip()]


def _check_our_topbar_changes(ours):
    """Fail if gui/topbar.gui changed vanilla's file in more than the two
    ways this part knows how to carry over."""
    vanilla_path = Path(path_constants.base_game_path) / "game" / "gui" / "topbar.gui"
    if not vanilla_path.exists():
        return "vanilla topbar.gui not found; skipped the check that ours changes only the width and the Banking widget"
    added, removed = [], []
    for ln in difflib.ndiff(_significant_lines(read_text(vanilla_path)), _significant_lines(ours)):
        if ln.startswith("+ "):
            added.append(ln[2:])
        elif ln.startswith("- "):
            removed.append(ln[2:])
    width_added = [a for a in added if re.fullmatch(r"size = \{ \d+ 80 \}", a)]
    other_added = [a for a in added if a not in width_added and a != BANKING_WIDGET]
    other_removed = [r for r in removed if r != "size = { 705 80 }"]
    if other_added or other_removed or BANKING_WIDGET not in added:
        raise BuildError(
            "gui/topbar.gui now differs from vanilla in ways build_topbar doesn't carry over: "
            f"added {other_added[:5]}, removed {other_removed[:5]}; extend build_topbar"
        )
    return None


def build_topbar(ra, out, log):
    ours = read_text(REPO / "gui" / "topbar.gui")
    theirs = read_text(ra / "gui" / "topbar.gui")
    note = _check_our_topbar_changes(ours)
    if note:
        log.append(f"topbar: {note}")

    def topbar_type(text):
        m = re.search(r"(?m)^\s*type topbar = widget \{", text)
        if not m:
            raise BuildError("`type topbar = widget {` not found")
        masked = mask(text)
        return m.start(), match_brace(masked, text.index("{", m.start())), masked

    o_start, o_end, _ = topbar_type(ours)
    ow = re.search(r"size = \{ (\d+) (\d+) \}", ours[o_start:o_end])
    our_width = int(ow.group(1))

    t_start, t_end, t_masked = topbar_type(theirs)
    tw = re.search(r"size = \{ (\d+) (\d+) \}", theirs[t_start:t_end])
    if not tw or tw.group(1) != "705":
        raise BuildError(f"RA's topbar width is no longer vanilla's 705 ({tw.group(0) if tw else 'none'}); recheck the widening")
    a, b = t_start + tw.start(), t_start + tw.end()
    indent = theirs[theirs.rindex("\n", 0, a) + 1 : a]
    patched = (
        theirs[:a]
        + "### TIMELINE EXTENDED (compatibility patch): vanilla's 705 widened for the Banking phase, as in\n"
        + f"{indent}### Timeline Extended's own topbar.gui. RA's height is kept.\n"
        + f"{indent}size = {{ {our_width} {tw.group(2)} }}"
        + theirs[b:]
    )

    masked = mask(patched)
    money = [m.start() for m in re.finditer(r"### MONEY", patched)]
    if len(money) != 1:
        raise BuildError(f"expected one `### MONEY` in RA's topbar, found {len(money)}")
    cm = re.compile(r"container = \{").search(masked, money[0])
    if not cm:
        raise BuildError("no MONEY container after `### MONEY` in RA's topbar")
    close = match_brace(masked, cm.end() - 1)
    line_start = patched.rindex("\n", 0, cm.start()) + 1
    indent = patched[line_start : cm.start()]
    eol = patched.index("\n", close)
    patched = (
        patched[:eol]
        + "\n\n"
        + f"{indent}### TIMELINE EXTENDED (compatibility patch): the Banking phase after MONEY, as in\n"
        + f"{indent}### Timeline Extended's own topbar.gui (type in gui/journal_entry_widgets/banking_dashboard_widget.gui).\n"
        + f"{indent}{BANKING_WIDGET}\n"
        + patched[eol:]
    )
    if patched.count(BANKING_WIDGET) != 1:
        raise BuildError("the Banking widget isn't in the patched topbar exactly once")
    if patched.count("{") != patched.count("}"):
        raise BuildError("patched topbar has unbalanced braces")
    write_text(out / "gui" / "topbar.gui", patched)
    log.append(f"topbar: RA's top bar, widened to {our_width} with the Banking phase after MONEY")


# --------------------------------------------------------------------------
# Part 3: ideologies
# --------------------------------------------------------------------------


def build_ideologies(ra, out, log):
    import apply_ideologies
    from ideology_modifications import modifications

    ours = collect_entries(REPO, "common/ideologies")
    touched = {n for n, rows in ours.items() if any(d for d, _f, _b in rows)}
    theirs = collect_entries(ra, "common/ideologies")
    bodies, unhandled = {}, []
    for name in sorted(touched & set(theirs)):
        for directive, fname, body in theirs[name]:
            if directive in REPLACE_FAMILY:
                bodies[name] = (fname, body + "\n")  # the last REPLACE in file order is the one that sticks
            else:
                unhandled.append(f"{name} ({directive or 'plain'} in {fname})")
    if unhandled:
        raise BuildError(f"RA touches ideologies we change in ways build_ideologies doesn't merge: {unhandled}")
    if not bodies:
        log.append("ideologies: nothing to merge")
        return set()
    missing = sorted(n for n in bodies if n not in modifications)
    if missing:
        raise BuildError(f"ideologies in modified.txt with no ideology_modifications entry: {missing}")

    merged, unmatched = apply_ideologies.modify_entries(
        {n: b for n, (_f, b) in bodies.items()}, {n: modifications[n] for n in bodies}
    )
    if unmatched:
        raise BuildError(f"apply_ideologies matched nothing for {unmatched}")
    merged = apply_ideologies.update_law_reqs(merged)

    parts = [
        "# AUTO-GENERATED by scripts/generators/build_realism_ai_compatch.py - do not edit manually.\n"
        "# Each entry is Realism AI's REPLACE_OR_CREATE body for the ideology with Timeline\n"
        "# Extended's ideology_modifications.py edits applied, so neither mod's stances are lost.\n"
    ]
    for name in sorted(merged):
        _kw, body, _reasons = merged[name]
        parts.append(f"# Realism AI: {bodies[name][0]}\nREPLACE:{name} = {body}")
    text = "\n".join(parts)
    path = out / "common" / "ideologies" / f"{FILE_PREFIX}ideologies.txt"
    write_text(path, text)

    parsed = parse_text(text)
    for name, (_fname, ra_body) in bodies.items():
        got = values(parsed[f"REPLACE:{name}"])[0]
        ra_parsed = values(parse_text(f"x = {ra_body}")["x"])[0]
        for group, stances in modifications[name].items():
            block = values(got.get(group, ("=", {})))[0]
            for law, stance in stances:
                if stance not in [str(v) for v in values(block.get(law, ("=", None)))]:
                    raise BuildError(f"{name}: our {group} {law} = {stance} didn't land")
        for group, block in ra_parsed.items():
            if not group.startswith("lawgroup_"):
                continue
            if group not in got:
                raise BuildError(f"{name}: RA's {group} block was lost")
            ours_here = {law for law, _s in modifications[name].get(group, [])}
            got_block = values(got[group])[0]
            for law, stance in values(block)[0].items():
                if law in ours_here:
                    continue
                if law not in got_block:
                    raise BuildError(f"{name}: RA's {group} {law} was lost")
                if [str(v) for v in values(got_block[law])] != [str(v) for v in values(stance)]:
                    raise BuildError(f"{name}: RA's {group} {law} stance changed in the merge")
    log.append(f"ideologies: {len(merged)} merged ({', '.join(sorted(merged))})")
    return set(merged)


# --------------------------------------------------------------------------
# Part 4: laws
# --------------------------------------------------------------------------

FLAT_LINE_RE = re.compile(r"^\s*([A-Za-z_][\w]*)\s*=\s*([^\s{}#]+)\s*(?:#.*)?$")


def _flat_modifier_lines(block_text, where):
    """[(key, value)] from a modifier block holding only flat `key = value`."""
    inner = block_text[block_text.index("{") + 1 : block_text.rindex("}")]
    rows = []
    for ln in inner.splitlines():
        if not mask(ln).strip():
            continue
        m = FLAT_LINE_RE.match(ln)
        if not m:
            raise BuildError(f"{where}: unsupported line in modifier block: {ln.strip()!r}")
        rows.append((m.group(1), m.group(2)))
    return rows


def _merge_into_modifier(body, additions, where):
    """Sum `additions` into the single depth-1 `modifier = {}` of an entity
    body, as an INJECT would; append keys the block lacks."""
    masked = mask(body)
    blocks = [b for b in blocks_at_depth(body, masked, depth_target=1) if b[0] == "modifier"]
    if len(blocks) != 1:
        raise BuildError(f"{where}: expected one modifier block, found {len(blocks)}")
    _k, _s, o, c = blocks[0]
    block = body[o : c + 1]
    existing = dict(_flat_modifier_lines(block, where))
    for key, value in additions:
        if key in existing:
            if not (NUMBER_RE.match(existing[key]) and NUMBER_RE.match(value)):
                raise BuildError(f"{where}: can't sum non-numeric {key} ({existing[key]} + {value})")
            total = fmt_number(float(existing[key]) + float(value))
            new_block, n = re.subn(
                rf"(?m)^(\s*{re.escape(key)}\s*=\s*){re.escape(existing[key])}\b",
                lambda m: m.group(1) + total + f" # Realism AI adds {value}",
                block,
                count=1,
            )
            if n != 1:
                raise BuildError(f"{where}: couldn't rewrite {key}")
            block = new_block
        else:
            close = block.rindex("}")
            line_start = block.rindex("\n", 0, close) + 1
            indent = block[line_start:close] + "\t"
            block = block[:line_start] + f"{indent}{key} = {value} # Realism AI\n" + block[line_start:]
    return body[:o] + block + body[c + 1 :]


def build_laws(ra, out, log):
    ours = collect_entries(REPO, "common/laws")
    theirs = collect_entries(ra, "common/laws")
    out_parts, handled, unhandled = [], set(), []
    for name in sorted(set(ours) & set(theirs)):
        our_rows, ra_rows = ours[name], theirs[name]
        our_dirs = {d for d, _f, _b in our_rows}
        ra_dirs = {d for d, _f, _b in ra_rows}
        if our_dirs <= INJECT_FAMILY and ra_dirs <= INJECT_FAMILY:
            continue  # INJECTs sum; both sides survive
        if not (our_dirs & REPLACE_FAMILY and ra_dirs <= INJECT_FAMILY):
            unhandled.append(f"{name} (ours {sorted(our_dirs)}, RA {sorted(ra_dirs)})")
            continue
        replace_idx = max(i for i, (d, _f, _b) in enumerate(our_rows) if d in REPLACE_FAMILY)
        if any(d in INJECT_FAMILY for d, _f, _b in our_rows[replace_idx + 1 :]):
            unhandled.append(f"{name} (we INJECT after our own REPLACE)")
            continue
        _d, our_file, body = our_rows[replace_idx]
        additions = []
        for _rd, ra_file, ra_body in ra_rows:
            for key, _s, o, c in blocks_at_depth(ra_body, depth_target=1):
                if key != "modifier":
                    raise BuildError(f"{name}: RA's inject in {ra_file} has a `{key}` block; only modifier blocks are merged")
                additions += _flat_modifier_lines(ra_body[o : c + 1], f"RA {ra_file} {name}")
            stripped = re.sub(r"modifier\s*=\s*\{[^{}]*\}", "", mask(ra_body)).strip("{} \n\t")
            if stripped:
                raise BuildError(f"{name}: RA's inject in {ra_file} carries more than modifier blocks")
        merged = _merge_into_modifier(body, additions, f"{our_file} {name}")
        out_parts.append(
            f"# Timeline Extended's {our_file} body with Realism AI's injected modifiers "
            f"({', '.join(f for _d, f, _b in ra_rows)}) summed in.\nREPLACE:{name} = {merged}\n"
        )
        handled.add(name)

        got = values(parse_text(f"REPLACE:{name} = {merged}")[f"REPLACE:{name}"])[0]
        base = values(parse_text(f"x = {body}")["x"])[0]
        got_mod, base_mod = values(got["modifier"])[0], values(base["modifier"])[0]
        for key, value in additions:
            expect = float(values(base_mod[key])[0]) + float(value) if key in base_mod else float(value)
            if abs(float(values(got_mod[key])[0]) - expect) > 1e-9:
                raise BuildError(f"{name}: {key} came out {values(got_mod[key])[0]}, expected {expect}")
    if unhandled:
        raise BuildError(f"laws both mods change in ways build_laws doesn't merge: {unhandled}")
    if out_parts:
        header = "# AUTO-GENERATED by scripts/generators/build_realism_ai_compatch.py - do not edit manually.\n\n"
        write_text(out / "common" / "laws" / f"{FILE_PREFIX}laws.txt", header + "\n".join(out_parts))
    log.append(f"laws: {len(handled)} merged ({', '.join(sorted(handled)) or 'none'})")
    return handled


# --------------------------------------------------------------------------
# Part 5: country ranks
# --------------------------------------------------------------------------


def _rank_modifiers(rows, where):
    total = {}
    for _d, fname, body in rows:
        for key, _s, o, c in blocks_at_depth(body, depth_target=1):
            if key == "modifier":
                for k, v in _flat_modifier_lines(body[o : c + 1], f"{where} {fname}"):
                    total[k] = total.get(k, 0.0) + float(v)
    return total


def build_ranks(ra, out, log):
    vanilla_dir = Path(path_constants.base_game_path) / "game" / "common" / "country_ranks"
    vanilla = collect_entries(vanilla_dir.parent.parent, "common/country_ranks") if vanilla_dir.is_dir() else {}
    if not vanilla:
        raise BuildError("vanilla country_ranks not found; the rank part needs the game files")
    ours = collect_entries(REPO, "common/country_ranks")
    theirs = collect_entries(ra, "common/country_ranks")

    def rank_value(rows):
        for _d, _f, body in rows:
            m = re.search(r"(?m)^\s*rank_value\s*=\s*(\d+)", body)
            if m:
                return int(m.group(1))
        return None

    gp_value = rank_value(vanilla["great_power"])
    ours_gp = _rank_modifiers([r for r in ours["great_power"] if r[0] in INJECT_FAMILY], "our great_power")
    vanilla_gp = _rank_modifiers(vanilla["great_power"], "vanilla great_power")
    cancel = ours_gp.get("country_loan_interest_rate_mult", 0.0)
    if abs(cancel + vanilla_gp.get("country_loan_interest_rate_mult", 0.0)) > 1e-9:
        raise BuildError("our great_power interest cancel no longer mirrors vanilla's discount; recheck te_monetary_rank_injections.txt")

    parts = []
    for name, rows in sorted(theirs.items()):
        if name in vanilla:
            continue
        value = rank_value(rows)
        if value is None or value <= gp_value:
            raise BuildError(f"RA adds rank {name} (rank_value {value}) at or below Great Power; decide its injections by hand")
        if name in ours:
            raise BuildError(f"this mod already touches RA's rank {name}")
        own = _rank_modifiers(rows, f"RA {name}")
        mods = dict(ours_gp)
        mods["country_loan_interest_rate_mult"] = -own.get("country_loan_interest_rate_mult", 0.0)
        lines = "\n".join(f"\t\t{k} = {fmt_number(v)}" for k, v in sorted(mods.items()) if fmt_number(v) != "0")
        parts.append(
            f"# Realism AI's {name} ranks above Great Power: it gets Timeline Extended's Great Power\n"
            f"# injections (extra_country_ranks.txt, te_monetary_rank_injections.txt), with the\n"
            f"# interest cancel matched to {name}'s own discount.\n"
            f"INJECT:{name} = {{\n\tmodifier = {{\n{lines}\n\t}}\n}}\n"
        )
    if parts:
        header = "# AUTO-GENERATED by scripts/generators/build_realism_ai_compatch.py - do not edit manually.\n\n"
        write_text(out / "common" / "country_ranks" / f"{FILE_PREFIX}country_ranks.txt", header + "\n".join(parts))
    log.append(f"country_ranks: {len(parts)} rank(s) given our Great Power injections")


# --------------------------------------------------------------------------
# Metadata, README
# --------------------------------------------------------------------------


def build_metadata(ra, out, log):
    te_meta = json.loads(read_text(REPO / ".metadata" / "metadata.json"))
    ra_meta = json.loads(read_text(ra / ".metadata" / "metadata.json"))
    if ra_meta.get("id") != RA_MOD_ID:
        raise BuildError(f"RA's metadata id is {ra_meta.get('id')!r}, expected {RA_MOD_ID!r}")
    ra_major = str(ra_meta.get("version", "")).split(".")[0] or "*"
    meta = {
        "name": PATCH_NAME,
        "id": PATCH_ID,
        "version": f"{te_meta['version']}+ra{ra_meta.get('version', '')}",
        "supported_game_version": te_meta["supported_game_version"],
        "short_description": (
            "Compatibility patch for Vic3TimelineExtended and Realism Ai Historical Flavor Mod. "
            "Load it after both."
        ),
        "tags": ["Fixes"],
        "relationships": [
            {
                "rel_type": "dependency",
                "id": RA_MOD_ID,
                "display_name": RA_NAME,
                "resource_type": "mod",
                "version": f"{ra_major}.*",
            }
        ],
        "game_custom_data": {"multiplayer_synchronized": True},
    }
    write_text(out / ".metadata" / "metadata.json", json.dumps(meta, indent=2, ensure_ascii=False) + "\n", bom=False)
    readme = f"""# {PATCH_NAME}

Built by `scripts/generators/build_realism_ai_compatch.py` in the Vic3TimelineExtended
repository from Timeline Extended {te_meta['version']} and {RA_NAME} {ra_meta.get('version', '')}.
Do not edit these files; rebuild them.

## Load order

1. {RA_NAME}
2. Vic3TimelineExtended
3. This patch (last)

## What it merges

{chr(10).join('- ' + line for line in log)}

Details and the in-game checklist: `docs/guides/mod_compatibility.md` in the repository.
"""
    write_text(out / "README.md", readme, bom=False)


# --------------------------------------------------------------------------
# Rescan for overlaps the patch doesn't handle
# --------------------------------------------------------------------------


def _files(root):
    out = set()
    for d in DEPLOYED_DIRS:
        base = Path(root) / d
        if base.is_dir():
            out |= {p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file()}
    if Path(root) == REPO:
        # A sparse worktree has no gfx/ on disk; the index still lists it.
        listed = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "--", *DEPLOYED_DIRS], capture_output=True, text=True
        )
        if listed.returncode == 0:
            out |= set(listed.stdout.splitlines())
    return out


def _loc_keys(root):
    keys = defaultdict(set)
    base = Path(root) / "localization" / "english"
    for p in base.rglob("*.yml") if base.is_dir() else []:
        for ln in read_text(p).splitlines():
            m = re.match(r"^\s+([\w.\-]+):\d*\s*\"", ln)
            if m:
                keys[m.group(1)].add(p.name)
    return keys


def _gui_types(root):
    types = defaultdict(set)
    base = Path(root) / "gui"
    for p in base.rglob("*.gui") if base.is_dir() else []:
        for m in re.finditer(r"(?m)^\s*(?:type|template)\s+([\w]+)", mask(read_text(p))):
            types[m.group(1)].add(p.relative_to(root).as_posix())
    return types


def _events(root):
    ids = defaultdict(set)
    base = Path(root) / "events"
    for p in base.rglob("*.txt") if base.is_dir() else []:
        text = mask(read_text(p))
        for m in re.finditer(r"(?m)^\s*namespace\s*=\s*(\w+)", text):
            ids["namespace " + m.group(1)].add(p.name)
        for m in re.finditer(r"(?m)^([\w]+\.\d+)\s*=\s*\{", text):
            ids[m.group(1)].add(p.name)
    return ids


def _defines(root):
    out = {}
    base = Path(root) / "common" / "defines"
    for p in sorted(base.glob("*.txt")) if base.is_dir() else []:
        text = read_text(p)
        masked = mask(text)
        for ns, _s, o, c in blocks_at_depth(text, masked):
            for m in re.finditer(r"(?m)^\s*([A-Z_0-9]+)\s*=", masked[o + 1 : c]):
                out[f"{ns}.{m.group(1)}"] = p.name
    return out


def scan_unhandled(ra, handled_paths, handled_keys):
    findings = []
    for p in sorted((_files(REPO) & _files(ra)) - handled_paths):
        findings.append(f"same-path file (the later-loaded mod's copy wins whole): {p}")

    common_dirs = sorted(
        {d.name for d in (REPO / "common").iterdir() if d.is_dir()}
        & {d.name for d in (ra / "common").iterdir() if d.is_dir()}
    )
    for sub in common_dirs:
        if sub in ("on_actions", "defines", "history", "named_colors"):
            continue  # merged by the engine; defines are compared key by key below
        ours, theirs = collect_entries(REPO, f"common/{sub}"), collect_entries(ra, f"common/{sub}")
        for name in sorted(set(ours) & set(theirs)):
            if (sub, name) in handled_keys:
                continue
            our_dirs = {d for d, _f, _b in ours[name]}
            ra_dirs = {d for d, _f, _b in theirs[name]}
            if our_dirs <= INJECT_FAMILY and ra_dirs <= INJECT_FAMILY:
                continue
            findings.append(
                f"common/{sub} key both mods define: {name} "
                f"(ours {sorted(d or 'plain' for d in our_dirs)} in {sorted({f for _d, f, _b in ours[name]})}, "
                f"RA {sorted(d or 'plain' for d in ra_dirs)} in {sorted({f for _d, f, _b in theirs[name]})})"
            )
    our_defs, ra_defs = _defines(REPO), _defines(ra)
    for k in sorted(set(our_defs) & set(ra_defs)):
        findings.append(f"define both mods set: {k} ({our_defs[k]} / {ra_defs[k]})")

    our_types, ra_types = _gui_types(REPO), _gui_types(ra)
    for k in sorted(set(our_types) & set(ra_types)):
        if our_types[k] | ra_types[k] <= handled_paths:
            continue
        findings.append(f"GUI type/template both mods define: {k} ({sorted(our_types[k])} / {sorted(ra_types[k])})")

    our_ev, ra_ev = _events(REPO), _events(ra)
    for k in sorted(set(our_ev) & set(ra_ev)):
        findings.append(f"event {k} in both mods")

    our_loc, ra_loc = _loc_keys(REPO), _loc_keys(ra)
    for k in sorted(set(our_loc) & set(ra_loc)):
        # The game takes the key from the file that sorts last by name.
        winner = max(our_loc[k] | ra_loc[k])
        side = "ours" if winner in our_loc[k] else "RA's"
        if side == "ours":
            continue
        findings.append(f"loc key both mods define, RA's text shows: {k} ({sorted(our_loc[k])} / {sorted(ra_loc[k])})")
    return findings


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def default_ra_path():
    return Path(path_constants.base_game_path).parent.parent / "workshop" / "content" / "529340" / RA_WORKSHOP_ID


def deploy_target():
    return Path(path_constants.mod_deploy_target).parent / DEPLOY_DIR_NAME


def build(ra, out):
    if out.exists():
        meta = out / ".metadata" / "metadata.json"
        is_patch = meta.exists() and json.loads(read_text(meta)).get("id") == PATCH_ID
        if any(out.iterdir()) and not is_patch:
            raise BuildError(f"{out} exists and isn't a previous build of this patch; not deleting it")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    log = []
    build_state_regions(ra, out, log)
    build_topbar(ra, out, log)
    ideologies = build_ideologies(ra, out, log)
    laws = build_laws(ra, out, log)
    build_ranks(ra, out, log)
    build_metadata(ra, out, log)
    handled_paths = {p.relative_to(out).as_posix() for p in (out / "map_data").rglob("*.txt")} | {"gui/topbar.gui"}
    handled_keys = {("ideologies", n) for n in ideologies} | {("laws", n) for n in laws}
    return log, scan_unhandled(ra, handled_paths, handled_keys)


def tree_diff(a, b):
    cmp = filecmp.dircmp(a, b)
    diffs = []

    def walk(c, rel):
        diffs.extend(f"only in build: {rel}{x}" for x in c.left_only)
        diffs.extend(f"only in deployed copy: {rel}{x}" for x in c.right_only)
        diffs.extend(f"differs: {rel}{x}" for x in c.diff_files)
        for name, sub in c.subdirs.items():
            walk(sub, f"{rel}{name}/")

    walk(cmp, "")
    return diffs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ra-path", type=Path, default=None, help="Realism AI mod folder (default: the Steam Workshop copy)")
    ap.add_argument("--out", type=Path, default=OUT_DIR, help=f"output folder (default: {OUT_DIR.relative_to(REPO)})")
    ap.add_argument("--deploy", action="store_true", help=f"copy the build to <mod folder>/{DEPLOY_DIR_NAME}")
    ap.add_argument("--check", action="store_true", help="build to a temp folder and exit 1 if the deployed patch differs")
    ap.add_argument("--strict", action="store_true", help="exit 2 when the rescan finds overlaps the patch doesn't handle")
    args = ap.parse_args()

    ra = args.ra_path or default_ra_path()
    if not (ra / ".metadata" / "metadata.json").exists():
        sys.exit(f"Realism AI not found at {ra}; pass --ra-path")

    try:
        if args.check:
            with tempfile.TemporaryDirectory() as tmp:
                log, findings = build(ra, Path(tmp) / "patch")
                target = deploy_target()
                if not target.exists():
                    sys.exit(f"no deployed patch at {target}")
                diffs = tree_diff(Path(tmp) / "patch", target)
                for d in diffs:
                    print(d)
                for f in findings:
                    print(f"unhandled overlap: {f}")
                print("deployed patch is current" if not diffs else f"deployed patch is stale ({len(diffs)} differences)")
                sys.exit(1 if diffs else 0)
        log, findings = build(ra, args.out)
    except BuildError as e:
        sys.exit(f"build failed: {e}")

    print(f"Built {PATCH_NAME} in {args.out}")
    for line in log:
        print(f"  {line}")
    if findings:
        print(f"\n{len(findings)} overlap(s) the patch doesn't handle:")
        for f in findings:
            print(f"  {f}")
    else:
        print("\nRescan: no overlaps outside the patch.")

    if args.deploy:
        target = deploy_target()
        if target.exists():
            meta = target / ".metadata" / "metadata.json"
            if not meta.exists() or json.loads(read_text(meta)).get("id") != PATCH_ID:
                sys.exit(f"{target} exists and isn't this patch; not overwriting")
            shutil.rmtree(target)
        shutil.copytree(args.out, target)
        print(f"\nDeployed to {target}")
    if findings and args.strict:
        sys.exit(2)


if __name__ == "__main__":
    main()
