"""Flag `ScriptValue('x')` in loc or script text that names no script value (#1120, #1181).

A loc value can print a script value with the `ScriptValue('name')` data
function (`[GetPlayer.MakeScope.ScriptValue('gm_policy_factor_local')|1]`),
and so can a quoted string in script, mostly the `TE_SELF_CHECK OK|BROKEN`
`debug_log` lines. When no script value has that name, because it was
deleted, renamed or misspelled, the text renders `0` (or `×0`) and the only
sign is a line in debug.log; a self-check can then report the wrong verdict.
Nothing else offline catches it: the Grand Monuments policy pass deleted
`gm_policy_factor_local` and left three state-card tooltips reading it, past
every registry test and `--strict` audit.

What is checked
---------------
Every `ScriptValue('name')` in

- a value in `localization/english/**/*.yml`, `replace/` included.
  `te_unused_l_english.yml` is skipped: it is `organize_loc` output holding
  keys nothing references, so a dead read there is harmless, and a tag on a
  key that drifts into it is not judged either.
- a quoted string in `common/**/*.txt` or `events/**/*.txt`. Text in a `#`
  comment is not read, and a `#` inside a string doesn't start one (the
  lexer `gui_reference_audit` uses for its masks).

The escaped double-quoted form, `ScriptValue(\\"name\\")`, is checked too.

A name resolves when it is a top-level key of a mod file under
`common/script_values/` (subfolders included) or of vanilla's, read from the
committed `vanilla_parsed/` snapshot (`common/script_values.json`). What
counts as a definition is `gui_reference_audit.defined_names`, shared with
that audit's `.gui` check (#1180): a scalar `foo = 1` counts, and so does an
`INJECT_OR_CREATE:` / `REPLACE_OR_CREATE:` name. A scripted constant
(`@foo = 3`) does not, and neither does an `INJECT:`, `REPLACE:`,
`TRY_INJECT:` or `TRY_REPLACE:` name: it edits a definition that has to exist
elsewhere, in the mod or vanilla, and that definition is what resolves the
read. No game install is needed. A missing snapshot raises rather than
flagging every vanilla name, and so does a scan that finds no loc file or no
script file at all, so a wrong path can't pass as clean.

Skipped as dynamic, and counted in the summary (`dynamic_skipped`,
`script_dynamic_skipped`): an argument that is not a quoted literal
identifier. That covers `ScriptValue(Concatenate(...))`, a name built from
`$PARAM$`, a dotted or hyphenated name, and an unescaped `ScriptValue("x")`,
whose first `"` ends the loc value or script string as the audit reads it
(`check_localization_files.py` rejects that loc line anyway).

`.gui` files are not scanned here: `gui_reference_audit` resolves
`ScriptValue('x')` in `gui/**/*.gui` against the same definitions and the
same snapshot, and fails CI with `--strict`.

Suppression is check-tagged. In loc it trails the loc line (the engine
ignores anything after the closing quote):

    my_key:0 "[ScriptValue('x')]" # REVIEWED 2026-10-26 (loc_script_value): rationale

Keep the rationale free of `"`: the engine reads a loc value out to the
line's last quote, so a quote in the comment would pull the comment into the
text. In script it trails the line the string closes on, which for a
one-line string is the read's own line:

    debug_log = "[ScriptValue('x')]" # REVIEWED 2026-10-26 (loc_script_value): rationale

A tag on a line with no flag is stale and fails `--strict`.

Report: docs/engine/loc_script_value_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from gui_reference_audit import IDENT, LEX, defined_names, masks
from mod_state import split_loc_line

CHECK = "loc_script_value"
SKIP_FILES = frozenset({"te_unused_l_english.yml"})
LOC_DIR = os.path.join("localization", "english")
SCRIPT_DIRS = ("common", "events")
SCRIPT_VALUE_DIR = os.path.join("common", "script_values")
VANILLA_SNAPSHOT = os.path.join("vanilla_parsed", "common", "script_values.json")
REPORT_PATH = os.path.join("docs", "engine", "loc_script_value_report.md")

# `ScriptValue(` and, when present, a quoted argument: `'x'` or the escaped
# `\"x\"` a loc value or script string has to use (a bare `"` never gets here,
# since it ends the value or string). A call whose argument isn't quoted
# (`Concatenate(...)`, a bare scope) leaves `arg` unset and is skipped.
_CALL_RE = re.compile(
    r"\bScriptValue\(\s*(?:(?P<q>\\?[\"'])(?P<arg>[^\"'\\]*)(?P=q)\s*\))?"
)
_NAME_RE = re.compile(r"[A-Za-z_]\w*")
# Depth-0 keys of a script file, directive prefix kept (`INJECT:foo`): the
# entry a script flag sits in, named in the report.
_ENTRY_RE = re.compile(rf"[{{}}]|(?<![@\w:])((?:\w+:)?{IDENT})\s*=")
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)


@dataclass
class Flag:
    file: str
    line: int
    key: str
    name: str
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
    loc_files_scanned: int = 0
    refs_checked: int = 0
    dynamic_skipped: int = 0
    # The same counts for quoted strings in common/ and events/ (#1181).
    script_files_scanned: int = 0
    script_refs_checked: int = 0
    script_dynamic_skipped: int = 0
    script_values_indexed: int = 0

    @property
    def failing(self) -> int:
        """Flags without a tag, plus tags that suppress nothing."""
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


def mod_script_value_names(mod_path: str | Path) -> set[str]:
    """Top-level keys of every `.txt` under the mod's `common/script_values/`."""
    names: set[str] = set()
    folder = Path(mod_path) / SCRIPT_VALUE_DIR
    for path in sorted(folder.rglob("*.txt")):
        names |= defined_names(path.read_text(encoding="utf-8-sig", errors="replace"))
    return names


def vanilla_script_value_names(mod_path: str | Path) -> set[str]:
    """Vanilla's script value names from the committed `vanilla_parsed/` snapshot."""
    path = Path(mod_path) / VANILLA_SNAPSHOT
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is missing; rebuild it with `python3 vanilla_parsed.py build` "
            "on a machine with the game (without it every vanilla name would be flagged)"
        )
    return set(json.loads(path.read_text(encoding="utf-8")))


def _parse_tag(trailing: str) -> dict | None:
    if "REVIEWED" not in trailing:
        return None
    m = _TAGGED_REVIEWED_RE.search(trailing)
    if not m or CHECK not in re.split(r"[\s,]+", m.group("checks").strip()):
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _loc_files(mod_path: Path):
    loc_dir = mod_path / LOC_DIR
    if not loc_dir.is_dir():
        return
    for path in sorted(loc_dir.rglob("*.yml")):
        if path.name not in SKIP_FILES:
            yield path


def audit(mod_path: str | Path | None = None) -> AuditResult:
    """Scan the mod's English loc against the mod's and vanilla's script values."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    root = Path(mod_path)
    script_values = mod_script_value_names(root) | vanilla_script_value_names(root)
    result = AuditResult(script_values_indexed=len(script_values))

    for path in _loc_files(root):
        rel = path.relative_to(root).as_posix()
        result.loc_files_scanned += 1
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for lineno, raw in enumerate(text.splitlines(), 1):
            parsed = split_loc_line(raw)
            if parsed is None:
                continue
            key, value, trailing = parsed
            tag = _parse_tag(trailing)
            missing: list[str] = []
            for m in _CALL_RE.finditer(value):
                name = m.group("arg")
                if name is None or not _NAME_RE.fullmatch(name):
                    result.dynamic_skipped += 1
                    continue
                result.refs_checked += 1
                if name not in script_values and name not in missing:
                    missing.append(name)
            for name in missing:
                result.flags.append(Flag(rel, lineno, key, name, exemption=tag))
            if tag and not missing:
                result.stale_tags.append(StaleTag(rel, lineno, key))
    if not result.loc_files_scanned:
        # A wrong mod path or an emptied loc folder would otherwise pass as clean.
        raise FileNotFoundError(
            f"no loc file to scan under {root / LOC_DIR} (te_unused_l_english.yml is skipped)"
        )

    for path in _script_files(root):
        result.script_files_scanned += 1
        _audit_script_file(root, path, script_values, result)
    if not result.script_files_scanned:
        raise FileNotFoundError(
            f"no .txt file to scan under {root / 'common'} or {root / 'events'}"
        )
    return result


def _script_files(mod_path: Path):
    for folder in SCRIPT_DIRS:
        yield from sorted((mod_path / folder).rglob("*.txt"))


def _entry_at(syntax: str, offset: int) -> str:
    """The last depth-0 key before `offset`: the event, effect or script value
    whose block holds a read, or the key a top-level string is assigned to."""
    depth, name = 0, ""
    for tok in _ENTRY_RE.finditer(syntax, 0, offset):
        if tok[0] == "{":
            depth += 1
        elif tok[0] == "}":
            depth -= 1
        elif depth == 0:
            name = tok[1]
    return name or "(top level)"


def _audit_script_file(root: Path, path: Path, script_values: set[str], result: AuditResult) -> None:
    """Check the `ScriptValue('x')` reads in one script file's quoted strings.

    `LEX` reads strings and `#` comments in source order, so a `#` inside a
    string stays text and a quote inside a comment stays comment. A read's
    tag sits on the line its string closes on (one-line strings: its own).
    """
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if "ScriptValue" not in text and CHECK not in text:
        return
    rel = path.relative_to(root).as_posix()
    pos, lineno = 0, 1

    def line_of(offset: int) -> int:
        nonlocal pos, lineno  # LEX matches arrive in order: count forward
        lineno += text.count("\n", pos, offset)
        pos = offset
        return lineno

    tags: dict[int, tuple[dict, int]] = {}
    # Closing line -> {missing name: offset of its first read on that line}.
    missing: dict[int, dict[str, int]] = {}
    for tok in LEX.finditer(text):
        lexeme = tok[0]
        if lexeme.startswith("#"):
            tag = _parse_tag(lexeme)
            if tag:
                tags[line_of(tok.start())] = (tag, tok.start())
            continue
        if "ScriptValue" not in lexeme:
            continue
        found: list[tuple[str, int]] = []
        for m in _CALL_RE.finditer(lexeme):
            name = m.group("arg")
            if name is None or not _NAME_RE.fullmatch(name):
                result.script_dynamic_skipped += 1
                continue
            result.script_refs_checked += 1
            if name not in script_values:
                found.append((name, tok.start() + m.start()))
        if found:
            on_line = missing.setdefault(line_of(tok.end() - 1), {})
            for name, offset in found:
                on_line.setdefault(name, offset)
    if not missing and not tags:
        return

    syntax = masks(text)[1]
    for close_line, names in missing.items():
        tag = tags.get(close_line, (None, 0))[0]
        for name, offset in names.items():
            line = text.count("\n", 0, offset) + 1
            result.flags.append(Flag(rel, line, _entry_at(syntax, offset), name, exemption=tag))
    for tag_line, (_, offset) in tags.items():
        if tag_line not in missing:
            result.stale_tags.append(StaleTag(rel, tag_line, _entry_at(syntax, offset)))


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Loc script value audit report",
        "",
        "Auto-generated by `loc_script_value_audit.py` on every `POST /reload` of",
        "the mod state server. Do not hand-edit.",
        "",
        "Flagged: a `ScriptValue('name')` in a `localization/english/` value, or in",
        "a quoted string in `common/**/*.txt` or `events/**/*.txt` (comments",
        "aside), whose name is not a script value, in the mod's",
        "`common/script_values/` or in vanilla's (from the `vanilla_parsed/`",
        "snapshot). An `INJECT:` or `REPLACE:` name is not a definition. The text",
        "renders `0` and only debug.log says why. `te_unused_l_english.yml` is not",
        "scanned, and `.gui` files are `gui_reference_audit`'s. A loc flag names",
        "its loc key; a script flag names the top-level entry it sits in.",
        "",
        "Fix: point the read at the script value's current name, or restore the",
        "script value.",
        "",
        "Suppress a deliberate case trailing on the loc line (no `\"` in the",
        "rationale), or in script trailing on the line the string closes on:",
        "`# REVIEWED YYYY-MM-DD (loc_script_value): why`",
        "",
        "## Unreviewed flags",
        "",
    ]
    if not unrev:
        out += ["_None._", ""]
    else:
        by_file: dict[str, list[Flag]] = {}
        for f in unrev:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out += [f"### `{fname}` ({len(by_file[fname])})", ""]
            out += [f"- line {f.line}: `{f.key}` reads `{f.name}`" for f in by_file[fname]]
            out.append("")

    if result.stale_tags:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` `{t.key}` ({CHECK})" for t in result.stale_tags]
        out.append("")

    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        # No line number on a reviewed entry: the loc key names it, and an
        # edit above it would otherwise churn the report.
        out += [
            f"- `{f.file}` — `{f.key}` reads `{f.name}` — "
            f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            for f in exemp
        ]
        out.append("")

    # Flag counts only: the file and reference counts stay on the result (and
    # in the regenerate() summary) but move with unrelated loc.
    out += [
        "## Coverage",
        "",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        f"- stale tags: {len(result.stale_tags)}",
        "",
    ]
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report. Reads the
    loc, script and script value files itself, so `mod_state` is unused."""
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
        "loc_files_scanned": result.loc_files_scanned,
        "refs_checked": result.refs_checked,
        "dynamic_skipped": result.dynamic_skipped,
        "script_files_scanned": result.script_files_scanned,
        "script_refs_checked": result.script_refs_checked,
        "script_dynamic_skipped": result.script_dynamic_skipped,
        "script_values_indexed": result.script_values_indexed,
        "path": out_path,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on any untagged flag or stale tag (CI mode)")
    parser.add_argument("--mod-path", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.mod_path)
    print(render_report(result))
    return int(args.strict and result.failing > 0)


if __name__ == "__main__":
    raise SystemExit(main())
