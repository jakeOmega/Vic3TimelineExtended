"""Flag live GUI text and tooltips whose loc runs long (#1213, #1202 finding 7).

The owner's rule (2026-10-27): tooltips are short, and the rules of a system
live in its collapsed "How X Works" section, not in a live hover. The GUI and
localization audit (#1202) measured the gap by hand: 303 loc keys referenced
from `.gui` files, outside How sections, ran over 300 rendered characters,
and 132 over 500. The longest were Banking's Monetary Policy row tooltips, at
900 to 3,850 characters each. This audit keeps that measure running.

What is checked
---------------
Every loc key a mod `.gui` file names:

- as a `text = "key"` or `tooltip = "key"` property, and
- as a quoted argument of `Localize('key')`, or a comma-led one of
  `SelectLocalization( …, 'a', 'b' )`, `AddLocalizationIf` or `AddTextIf`, in
  any quoted value (`check_gui_lint.loc_args`, the lint's rule).

A key counts when the mod's English loc defines it (`localization/english/`,
`replace/` included, `te_unused_l_english.yml` skipped) and at least one
reference sits outside a How section. A reference is in a How section when it,
or a block around it, is named for one (a `how` or `help` token: `type
te_demog_sec_how`, `te_un_help_standing`) or is shown only while a How toggle
is open (`visible = "[GetVariableSystem.Exists('un_how_open')]"`; every How
section has one, `gui_tree.opens_how_section`). A key whose own name has a
`how` token (`te_tax_how_passage`) is How text wherever it is used.
`gui/te_debug_*.gui`, the console-only panels, are not read.

Rendered length
---------------
The loc value as the player reads it, measured in characters:

- each `$key$` splice is replaced by that key's text (mod first, then vanilla
  from the committed `vanilla_parsed/` snapshot), recursively; a `$NAME$`
  that names no key, a script parameter, counts as one character;
- each `[...]` data expression counts as one character, whatever it prints:
  the audit can't know how long a name or a modifier list renders, so it
  undercounts rather than guesses;
- a text icon (`@oil!`) counts as one; format codes (`#b `, `#tooltippable;
  tooltip:… `, `#!`) count as none; `\\n` counts as one.

The scan in #1202 used the same rules. A key is flagged over 500 characters
(`THRESHOLD`; `--threshold N` for a wider look). That is above all but 9 of
vanilla's 4,722 tooltip keys (`*_tt`, `*_tooltip`, measured the same way:
vanilla's 99th percentile is 311 and its longest 718), and about the mod's own
97th percentile of GUI-referenced keys. 300 would flag twice as many keys, a
good share of them data breakdowns that read as a table.

Suppression is check-tagged and trails the key's loc line (the definition
that wins: the last file in name order), as `loc_script_value_audit` does:

    my_tt:0 "..." # REVIEWED 2026-10-27 (long_tooltip): a reference card on purpose

Keep the rationale free of `"`. A tag on a line whose key is not flagged is
stale and fails `--strict`.

Report: docs/engine/long_tooltip_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import gui_tree
from mod_state import split_loc_line

CHECK = "long_tooltip"
THRESHOLD = 500
SKIP_FILES = frozenset({"te_unused_l_english.yml"})
SKIP_PREFIX = "te_debug_"  # console-only panels
LOC_DIR = os.path.join("localization", "english")
VANILLA_LOC = os.path.join("vanilla_parsed", "localization_english.json")
REPORT_PATH = os.path.join("docs", "engine", "long_tooltip_report.md")

_KEY_RE = re.compile(r"[A-Za-z_][\w.\-]*")
_LOC_CALL = re.compile(r"\b(Localize|SelectLocalization|AddLocalizationIf|AddTextIf)\(")
_SPLICE = re.compile(r"\$([\w.\-]+)(?:\|[^$]*)?\$")
_ICON = re.compile(r"@[\w.\-]+!")
_FORMAT = re.compile(r"#(?:!|[^\s#!]+ ?)")
_HOW_KEY = re.compile(r"(?:^|_)how(?:_|$)", re.I)
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)
_TOKEN = "\x01"


@dataclass
class LocEntry:
    value: str
    file: str
    line: int
    tag: dict | None


@dataclass
class Flag:
    key: str
    length: int
    loc_file: str
    loc_line: int
    gui_files: list[str]
    kinds: list[str]
    exemption: dict | None = None


@dataclass
class StaleTag:
    file: str
    line: int
    key: str


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    threshold: int = THRESHOLD
    gui_files_scanned: int = 0
    keys_measured: int = 0
    how_only_skipped: int = 0

    @property
    def failing(self) -> int:
        """Flags without a tag, plus tags that suppress nothing."""
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


def parse_tag(trailing: str) -> dict | None:
    if "REVIEWED" not in trailing:
        return None
    m = _TAGGED_REVIEWED_RE.search(trailing)
    if not m or CHECK not in re.split(r"[\s,]+", m.group("checks").strip()):
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def load_mod_loc(root: Path) -> tuple[dict[str, LocEntry], list[tuple[str, int, str]]]:
    """The mod's English loc, last file (name order) winning, and every tagged
    line as (file, line, key), the overridden copies included."""
    entries: dict[str, LocEntry] = {}
    tagged: list[tuple[str, int, str]] = []
    loc_dir = root / LOC_DIR
    files = sorted(p for p in loc_dir.rglob("*.yml") if p.name not in SKIP_FILES)
    if not files:
        raise FileNotFoundError(f"no loc file to scan under {loc_dir}")
    # The engine reads `replace/` after the rest, so its copy wins.
    for path in sorted(files, key=lambda p: (p.parent.name == "replace", p.name)):
        rel = path.relative_to(root).as_posix()
        for lineno, raw in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
            parsed = split_loc_line(raw)
            if parsed is None:
                continue
            key, value, trailing = parsed
            tag = parse_tag(trailing)
            if tag:
                tagged.append((rel, lineno, key))
            entries[key] = LocEntry(value, rel, lineno, tag)
    return entries, tagged


def load_vanilla_loc(root: Path) -> dict[str, str]:
    path = root / VANILLA_LOC
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is missing; rebuild it with `python3 vanilla_parsed.py build` "
            "on a machine with the game (without it a vanilla $key$ splice can't be measured)"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def loc_call_keys(expr: str) -> list[str]:
    """Loc keys passed as quoted arguments: `Localize('k')`, and the comma-led
    quoted arguments of `SelectLocalization` / `AddLocalizationIf` /
    `AddTextIf` (a quoted argument opening a call, `ScriptValue('x')`, is not
    one). The rule `scripts/analysis/check_gui_lint.loc_args` uses."""
    keys: list[str] = []
    for m in _LOC_CALL.finditer(expr):
        depth, end = 1, len(expr)
        for j in range(m.end(), len(expr)):
            if expr[j] == "(":
                depth += 1
            elif expr[j] == ")":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        span = expr[m.end():end]
        lead = r"^\s*" if m.group(1) == "Localize" else r",\s*"
        keys += [k for k in re.findall(lead + r"'([^'(][^']*)'", span) if _KEY_RE.fullmatch(k)]
    return keys


def gui_references(node: gui_tree.Node):
    """(key, property, line) for each loc key a node's own properties name."""
    for prop in node.props:
        if prop.key in ("text", "tooltip") and prop.quoted and _KEY_RE.fullmatch(prop.value):
            yield prop.value, prop.key, prop.line
        elif prop.quoted and "(" in prop.value:
            for key in loc_call_keys(prop.value):
                yield key, "call", prop.line


def _brackets_to_tokens(value: str) -> str:
    out: list[str] = []
    depth = 0
    for ch in value:
        if ch == "[":
            if depth == 0:
                out.append(_TOKEN)
            depth += 1
        elif ch == "]" and depth:
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def rendered_text(value: str, lookup, _depth: int = 0) -> str:
    """The value as the audit measures it: splices expanded, each `[...]` and
    icon one `\\x01` character, format codes gone, `\\n` one character."""
    def splice(m: re.Match) -> str:
        key = m.group(1)
        inner = lookup(key)
        if inner is None or _depth >= 8:
            return _TOKEN
        return rendered_text(inner, lookup, _depth + 1)

    text = _SPLICE.sub(splice, value)
    if _depth:
        return text  # the outermost call does the rest, once
    text = _brackets_to_tokens(text)
    text = text.replace("\\n", "\n").replace('\\"', '"')
    text = _ICON.sub(_TOKEN, text)
    return _FORMAT.sub("", text)


def rendered_length(value: str, lookup) -> int:
    return len(rendered_text(value, lookup))


def audit(mod_path: str | Path | None = None, threshold: int = THRESHOLD) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    root = Path(mod_path)
    mod_loc, tagged = load_mod_loc(root)
    vanilla = load_vanilla_loc(root)

    def lookup(key: str):
        if key in mod_loc:
            return mod_loc[key].value
        value = vanilla.get(key)
        return value if isinstance(value, str) else None

    result = AuditResult(threshold=threshold)
    live: dict[str, dict[str, set[str]]] = {}  # key -> gui file -> kinds
    in_how: set[str] = set()  # keys with a reference inside a How section
    for path in gui_tree.gui_files(root):
        rel = path.relative_to(root).as_posix()
        if path.name.startswith(SKIP_PREFIX):
            continue
        result.gui_files_scanned += 1
        tree = gui_tree.parse_file(path)
        for node in tree.walk():
            refs = [r for r in gui_references(node) if r[0] in mod_loc]
            if not refs:
                continue
            how = gui_tree.in_how_section(node)
            for key, kind, _line in refs:
                if how:
                    in_how.add(key)
                else:
                    live.setdefault(key, {}).setdefault(rel, set()).add(kind)
    if not result.gui_files_scanned:
        raise FileNotFoundError(f"no .gui file to scan under {root / 'gui'}")

    how_named = {key for key in live if _HOW_KEY.search(key)}
    result.how_only_skipped = len((in_how - set(live)) | how_named)
    flagged: set[str] = set()
    for key in sorted(set(live) - how_named):
        result.keys_measured += 1
        entry = mod_loc[key]
        length = rendered_length(entry.value, lookup)
        if length <= threshold:
            continue
        flagged.add(key)
        files = live[key]
        kinds = sorted({k for ks in files.values() for k in ks})
        result.flags.append(Flag(key, length, entry.file, entry.line, sorted(files), kinds,
                                 exemption=entry.tag))
    for rel, lineno, key in tagged:
        winning = mod_loc.get(key)
        if key not in flagged or (winning.file, winning.line) != (rel, lineno):
            result.stale_tags.append(StaleTag(rel, lineno, key))
    result.flags.sort(key=lambda f: (-f.length, f.key))
    return result


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Long tooltip audit report",
        "",
        "Auto-generated by `long_tooltip_audit.py` on every `POST /reload` of the",
        "mod state server. Do not hand-edit.",
        "",
        "Flagged: a loc key a mod `.gui` file names (`text`, `tooltip`, `Localize`,",
        "`SelectLocalization`, ...) outside a How-it-works section, whose rendered",
        f"text runs over {result.threshold} characters. Splices are expanded; each `[...]` and",
        "icon counts as one character and format codes as none. Live tooltips are",
        "short; the rules belong in the system's How section, or in a concept the",
        "tooltip links (`docs/guides/gui_style_guide.md`, rule 3).",
        "",
        "Suppress a deliberate case trailing on the key's loc line (no `\"` in the",
        "rationale): `# REVIEWED YYYY-MM-DD (long_tooltip): why`",
        "",
        "## Unreviewed flags",
        "",
    ]
    if not unrev:
        out += ["_None._", ""]
    else:
        out += ["| Length | Key | Used in | Loc line |", "|---:|---|---|---|"]
        for f in unrev:
            used = ", ".join(f"`{g}`" for g in f.gui_files)
            out.append(f"| {f.length} | `{f.key}` | {used} | `{f.loc_file}:{f.loc_line}` |")
        out.append("")

    if result.stale_tags:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` `{t.key}` ({CHECK})" for t in result.stale_tags]
        out.append("")

    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        out += [
            f"- `{f.key}` ({f.length}) — `{f.loc_file}` — "
            f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            for f in exemp
        ]
        out.append("")
    out += [
        "## Coverage",
        "",
        f"- threshold: {result.threshold} characters",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        f"- stale tags: {len(result.stale_tags)}",
        "",
    ]
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report. Reads the
    GUI and loc files itself, so `mod_state` is unused."""
    from path_constants import mod_path
    result = audit(mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        # Flags without a tag, plus tags that suppress nothing.
        "unreviewed": result.failing,
        "total_flags": len(result.flags),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "stale_tags": len(result.stale_tags),
        "gui_files_scanned": result.gui_files_scanned,
        "keys_measured": result.keys_measured,
        "how_only_skipped": result.how_only_skipped,
        "path": out_path,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on any untagged flag or stale tag (CI mode)")
    parser.add_argument("--threshold", type=int, default=THRESHOLD,
                        help=f"rendered characters a key may run to (default {THRESHOLD})")
    parser.add_argument("--mod-path", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.mod_path, args.threshold)
    print(render_report(result))
    return int(args.strict and result.failing > 0)


if __name__ == "__main__":
    raise SystemExit(main())
