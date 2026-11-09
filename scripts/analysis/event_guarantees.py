#!/usr/bin/env python3
"""What an event's trigger guarantees, for whoever writes its text.

    python3 scripts/analysis/event_guarantees.py modern_election_events.11
    python3 scripts/analysis/event_guarantees.py modern_election_events      # the whole chain
    python3 scripts/analysis/event_guarantees.py --tech social_media         # one technology

A text may show only what must be true whenever it is shown
(docs/guides/loc_style_guide.md, "Detail that cannot be wrong"). For an event
that mostly means its `trigger`. This prints, per event:

* the technologies the trigger requires, each with its era;
* every technology that follows from them: their prerequisites, recursively,
  and (owner's rule, 2026-11-09) every technology more than two eras behind
  the latest one required. A tech cannot require one from another category,
  so the prerequisites alone miss the obvious (social media does not require
  the telephone), but technology spread makes anything three eras back as
  good as certain;
* the technologies the trigger requires to be ABSENT;
* the rest of the trigger's top-level lines, as written.

It reads the trigger only. What fires the event (an on_action's own trigger, a
parent event, a button) can guarantee more, and an option's own `trigger` adds
to it for that option's text. A requirement inside an `OR` is listed as
"one of", and guarantees nothing by itself.

Technologies come from the mod's files and the committed vanilla_parsed/
snapshot. Needs no game and no server.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ERAS_BEHIND = 3
"""A tech this many eras behind a required one, or more, is assumed researched."""

_TECH_DEF = re.compile(r"^(?:(?:INJECT|REPLACE|TRY_INJECT|REPLACE_OR_CREATE|INJECT_OR_CREATE):)?([\w\-]+)\s*=\s*\{", re.M)
_ERA = re.compile(r"\bera\s*=\s*era_(\d+)")
_UNLOCKING = re.compile(r"unlocking_technologies\s*=\s*\{([^}]*)\}")
_COMMENT = re.compile(r"#[^\n]*")
_HAS_TECH = re.compile(r"has_technology_researched\s*=\s*([\w\-]+)")


def block_end(text: str, open_brace: int) -> int:
    """Index just past the brace matching the one at `open_brace`."""
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def load_technologies(repo_root=REPO_ROOT) -> dict:
    """{tech: {"era": int | None, "requires": [tech, ...]}} for vanilla and the mod."""
    techs = {}
    snapshot = os.path.join(repo_root, "vanilla_parsed", "common", "technologies.json")
    if os.path.exists(snapshot):
        with open(snapshot, encoding="utf-8") as fh:
            for name, (_, body) in json.load(fh).items():
                era = body.get("era", [None, ""])[1]
                requires = body.get("unlocking_technologies", [None, []])[1]
                names = list(requires) if isinstance(requires, dict) else [
                    r if isinstance(r, str) else r[1] for r in (requires or [])
                ]
                techs[name] = {
                    "era": int(era.split("_")[1]) if era.startswith("era_") else None,
                    "requires": [n for n in names if isinstance(n, str)],
                }
    for path in sorted(glob.glob(os.path.join(repo_root, "common", "technology", "technologies", "*.txt"))):
        with open(path, encoding="utf-8-sig") as fh:
            text = _COMMENT.sub("", fh.read())
        for match in _TECH_DEF.finditer(text):
            body = text[match.end() - 1: block_end(text, match.end() - 1)]
            entry = techs.setdefault(match.group(1), {"era": None, "requires": []})
            era = _ERA.search(body)
            if era:
                entry["era"] = int(era.group(1))
            unlocking = _UNLOCKING.search(body)
            if unlocking:
                for name in unlocking.group(1).split():
                    if name not in entry["requires"]:
                        entry["requires"].append(name)
    return techs


def prerequisites(tech: str, techs: dict) -> set:
    """Every technology `tech` requires, recursively (not `tech` itself)."""
    seen, stack = set(), list(techs.get(tech, {}).get("requires", []))
    while stack:
        name = stack.pop()
        if name not in seen:
            seen.add(name)
            stack.extend(techs.get(name, {}).get("requires", []))
    return seen


def assumed(required: list, techs: dict) -> tuple:
    """(prerequisites of the required techs, the era at or before which every
    tech is assumed, or None)."""
    closure = set()
    for tech in required:
        closure |= prerequisites(tech, techs)
    eras = [techs[t]["era"] for t in required if techs.get(t, {}).get("era")]
    cutoff = max(eras) - ERAS_BEHIND if eras else None
    return closure - set(required), (cutoff if cutoff and cutoff >= 1 else None)


def find_events(selector: str, repo_root=REPO_ROOT) -> list:
    """[(event id, file, body)] for an event id or a whole namespace."""
    namespace = selector.rsplit(".", 1)[0] if re.search(r"\.\d+$", selector) else selector
    pattern = re.compile(r"^(%s\.\d+)\s*=\s*\{" % re.escape(namespace), re.M)
    found = []
    for path in sorted(glob.glob(os.path.join(repo_root, "events", "**", "*.txt"), recursive=True)):
        with open(path, encoding="utf-8-sig") as fh:
            text = _COMMENT.sub("", fh.read())
        for match in pattern.finditer(text):
            if selector != namespace and match.group(1) != selector:
                continue
            body = text[match.end() - 1: block_end(text, match.end() - 1)]
            found.append((match.group(1), os.path.relpath(path, repo_root), body))
    found.sort(key=lambda e: int(e[0].rsplit(".", 1)[1]))
    return found


def top_level_statements(block: str) -> list:
    """The statements directly inside a `{ ... }` block, each as one string."""
    inner = block[block.index("{") + 1: block.rindex("}")]
    statements, depth, start = [], 0, 0
    for i, ch in enumerate(inner):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                statements.append(inner[start:i + 1])
                start = i + 1
        elif ch == "\n" and depth == 0:
            statements.append(inner[start:i])
            start = i + 1
    statements.append(inner[start:])
    return [" ".join(s.split()) for s in statements if s.strip()]


def read_trigger(body: str) -> dict:
    """The event's own `trigger`: required, forbidden and one-of technologies,
    and its other top-level statements."""
    match = re.search(r"^\ttrigger\s*=\s*\{", body, re.M) or re.search(r"\btrigger\s*=\s*\{", body)
    out = {"required": [], "absent": [], "one_of": [], "other": [], "has_trigger": bool(match)}
    if not match:
        return out
    block = body[match.end() - 1: block_end(body, match.end() - 1)]
    for statement in top_level_statements(block):
        head = statement.split("=", 1)[0].strip()
        names = _HAS_TECH.findall(statement)
        if head == "has_technology_researched":
            out["required"] += names
        elif head in ("NOT", "NOR") and names:
            out["absent"] += names
            if _HAS_TECH.sub("", statement).count("=") > 1:
                out["other"].append(statement)
        elif head == "OR" and names:
            out["one_of"].append(names)
            out["other"].append(statement)
        else:
            out["other"].append(statement)
    return out


def describe(event_id, path, body, techs) -> str:
    trigger = read_trigger(body)
    lines = [f"{event_id}  ({path})"]
    if not trigger["has_trigger"]:
        lines.append("  no trigger of its own: everything depends on what fires it")
        return "\n".join(lines)

    def with_era(name):
        era = techs.get(name, {}).get("era")
        return f"{name} (era {era})" if era else f"{name} (unknown technology)"

    if trigger["required"]:
        lines.append("  requires:      " + ", ".join(with_era(t) for t in trigger["required"]))
        closure, cutoff = assumed(trigger["required"], techs)
        if closure:
            lines.append("  so also has:   " + ", ".join(sorted(closure, key=lambda t: (techs.get(t, {}).get("era") or 0, t))))
        if cutoff:
            lines.append(f"  and may assume every technology of era {cutoff} or earlier")
    else:
        lines.append("  requires no technology: assume none, whatever the subject suggests")
    if trigger["absent"]:
        lines.append("  must NOT have: " + ", ".join(with_era(t) for t in trigger["absent"]))
    for group in trigger["one_of"]:
        lines.append("  one of:        " + ", ".join(with_era(t) for t in group) + "  (guarantees none of them)")
    for statement in trigger["other"]:
        shown = statement if len(statement) <= 150 else statement[:147] + "..."
        lines.append("  also:          " + shown)
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("selector", nargs="?", help="An event id (`ns.12`) or a namespace.")
    parser.add_argument("--tech", help="Show one technology's era and prerequisites instead.")
    args = parser.parse_args(argv)

    techs = load_technologies()
    if args.tech:
        if args.tech not in techs:
            print(f"No technology named {args.tech}.", file=sys.stderr)
            return 1
        closure, cutoff = assumed([args.tech], techs)
        print(f"{args.tech}: era {techs[args.tech]['era']}")
        print("  requires, recursively: " + (", ".join(sorted(closure)) or "nothing"))
        if cutoff:
            print(f"  an event gated on it may assume every technology of era {cutoff} or earlier")
        return 0
    if not args.selector:
        parser.error("give an event id, a namespace, or --tech")
    events = find_events(args.selector)
    if not events:
        print(f"No event matches {args.selector}.", file=sys.stderr)
        return 1
    print("\n\n".join(describe(*event, techs) for event in events))
    return 0


if __name__ == "__main__":
    sys.exit(main())
