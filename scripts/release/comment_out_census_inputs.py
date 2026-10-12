#!/usr/bin/env python3
"""Release-only: take the census's inputs out of a build that ships with the census off.

The census reads script-only modifier types (common/modifier_type_definitions/
demographics_modifier_types.txt) from techs, laws, institutions and a static modifier.
The engine never applies them, but their lines still render on those tooltips. A release
that ships without the census runs this on its release branch, never on main:

    git switch -c release/<version> origin/main
    python3 scripts/release/comment_out_census_inputs.py
    git add common/    # stage by path; it edits only common/
    git commit -m "Release <version>: the census's inputs commented out"

It comments out, keeping each line's text after a `# RELEASE: ` prefix:
1. every line that sets one of the types (`<type> = <value>`; the census's own
   `modifier:<type>` reads are left alone);
2. every top-level entry those leave with nothing in it (the INJECTs that carried only
   census lines);
3. every `add_modifier = { name = X }` of a static modifier left with no effect line, with or without a
   `multiplier = Y` (te_demog_family_limitation: France's history, and phase 3's census line under Full,
   te_demog_fl_effects.txt);
3b. every decree whose `modifier` block is left with no effect line is commented out
   whole (Medical Outreach: the census is its only reader);
4. the rule: both gates (te_demog_triggers.txt) read `always = no` and the rule's block
   goes, since the census can't run correctly without its inputs (owner, 2026-10-10:
   the release offers no way to turn it on).

A second run changes nothing. --check lists what it would change and writes nothing. It refuses
to write on the main branch.
test_release_census_inputs.py runs it on a copy of the tree.
"""
import re
import subprocess
import sys
from pathlib import Path

TYPES_FILE = Path("common/modifier_type_definitions/demographics_modifier_types.txt")
TRIGGERS = Path("common/scripted_triggers/te_demog_triggers.txt")
RULES = Path("common/game_rules/extra_game_rules.txt")
GATES = ("te_demog_cohorts_run", "te_demog_effects_run", "te_debug_demog_selfchecks_run")
RULE = "demographics_rule"
TAG = "# RELEASE: "
# common/ directories that only read the types
READERS = {"modifier_type_definitions", "script_values", "scripted_effects", "scripted_triggers"}


def _read(path):
    raw = path.read_bytes()
    return raw.startswith(b"\xef\xbb\xbf"), raw.decode("utf-8-sig").split("\n")


def _code(line):
    """The line without its comment (the carrier lines hold no quoted '#')."""
    return line.split("#", 1)[0]


def _entries(lines):
    """(start, end) line indexes of each top-level `name = { ... }`, by brace depth."""
    out, depth, start = [], 0, None
    for i, line in enumerate(lines):
        code = _code(line)
        if depth == 0 and "{" in code:
            start = i
        depth += code.count("{") - code.count("}")
        if depth == 0 and start is not None:
            out.append((start, i))
            start = None
    return out


def _empty(lines):
    """True when the code holds only braces and the names that open blocks."""
    body = re.sub(r"[\w:.@-]+\s*=\s*\{", "{", " ".join(_code(line) for line in lines))
    return not re.sub(r"[{}\s]", "", body)


def _modifier_emptied(lines):
    """True when an entry's `modifier = { ... }` block holds no live line: a decree whose only effects were census
    types (its texture and cost would ship as an empty decree otherwise)."""
    depth, inside = 0, False
    for line in lines:
        code = _code(line)
        if not inside and re.match(r"\s*modifier\s*=\s*\{", code):
            inside = True
        if inside:
            depth += code.count("{") - code.count("}")
            if re.sub(r"[\w:.@-]+\s*=\s*\{|[{}\s]", "", code):
                return False
            if depth == 0:
                return True
    return False


def _tag(lines, i):
    if lines[i].strip() and not lines[i].startswith(TAG):
        lines[i] = TAG + lines[i]


def run(root, check=False):
    """Comment the census's inputs out under root; returns {path: (old, new)} of what changed."""
    root = Path(root)
    _, type_lines = _read(root / TYPES_FILE)
    types = [m.group(1) for m in map(re.compile(r"^(\w+) = \{").match, type_lines) if m]
    assert types, TYPES_FILE
    carrier = re.compile(rf"^\s*({'|'.join(types)})\s*=\s*\S")
    files = {}  # path -> (bom, old lines, new lines)

    def edit(path):
        if path not in files:
            bom, lines = _read(path)
            files[path] = (bom, lines, list(lines))
        return files[path][2]

    emptied = set()
    for path in sorted((root / "common").rglob("*.txt")):
        if READERS & set(path.relative_to(root / "common").parts):
            continue
        _, lines = _read(path)
        hits = {i for i, line in enumerate(lines) if carrier.match(_code(line))}
        if not hits:
            continue
        new = edit(path)
        for i in hits:
            _tag(new, i)
        for start, end in _entries(new):
            if not hits & set(range(start, end + 1)):
                continue
            if _empty(new[start:end + 1]):
                for i in range(start, end + 1):
                    _tag(new, i)
            elif path.parent.name == "decrees" and _modifier_emptied(new[start:end + 1]):
                for i in range(start, end + 1):
                    _tag(new, i)
            elif path.parent.name == "static_modifiers":
                effects = [_code(line) for line in new[start + 1:end]]
                if not [e for e in effects if e.strip() and not re.match(r"\s*icon\s*=", e)]:
                    emptied.add(re.match(r"\s*([\w.-]+)\s*=", new[start]).group(1))

    if emptied:
        applied = re.compile(rf"add_modifier\s*=\s*\{{\s*name\s*=\s*({'|'.join(map(re.escape, sorted(emptied)))})"
                             rf"(?:\s+multiplier\s*=\s*\S+)?\s*\}}")
        for path in sorted([*(root / "common").rglob("*.txt"), *(root / "events").rglob("*.txt")]):
            _, lines = _read(path)
            hits = [i for i, line in enumerate(lines) if applied.search(_code(line))]
            if hits:
                new = edit(path)
                for i in hits:
                    _tag(new, i)

    new = edit(root / TRIGGERS)
    for start, end in reversed(_entries(new)):
        name = re.match(r"\s*(\w+)\s*=", new[start])
        if not name or name.group(1) not in GATES:
            continue
        body = [_code(line).strip() for line in new[start + 1:end] if _code(line).strip()]
        if body == ["always = no"]:
            continue
        for i in range(start + 1, end):
            _tag(new, i)
        new.insert(end, "\talways = no")

    new = edit(root / RULES)
    for start, end in _entries(new):
        if re.match(rf"{RULE}\s*=", new[start]):
            for i in range(start, end + 1):
                _tag(new, i)

    changed = {}
    for path, (bom, old, new) in files.items():
        if old == new:
            continue
        changed[path] = (old, new)
        if not check:
            path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + "\n".join(new).encode("utf-8"))
    return changed


def main(argv):
    check = "--check" in argv
    root = Path.cwd()
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root,
                            capture_output=True, text=True).stdout.strip()
    if branch == "main" and not check:
        sys.exit("On main: this is for a release branch only (git switch -c release/<version> origin/main).")
    changed = run(root, check)
    total = 0
    for path, (old, new) in changed.items():
        lines = [line for line in new if line.startswith(TAG) or line == "\talways = no"]
        lines = [line for line in lines if line not in old]
        total += len(lines)
        print(f"{path.relative_to(root)}: {len(lines)} line(s)")
        for line in lines:
            print(f"    {line.strip()[:120]}")
    print(f"{total} line(s) in {len(changed)} file(s)" + (" (check only, nothing written)" if check else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
