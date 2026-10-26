"""Flag `ScriptValue('x')` in localization that names no script value (#1120).

A loc value can print a script value with the `ScriptValue('name')` data
function (`[GetPlayer.MakeScope.ScriptValue('gm_policy_factor_local')|1]`).
When no script value has that name, because it was deleted, renamed or
misspelled, the text renders `0` (or `×0`) and the only sign is a line in
debug.log. Nothing else offline catches it: the Grand Monuments policy pass
deleted `gm_policy_factor_local` and left three state-card tooltips reading
it, past every registry test and `--strict` audit.

What is checked
---------------
Every `ScriptValue('name')` in `localization/english/**/*.yml`, `replace/`
included. `te_unused_l_english.yml` is skipped: it is `organize_loc` output
holding keys nothing references, so a dead read there is harmless, and a
tag on a key that drifts into it is not judged either. The escaped
double-quoted form, `ScriptValue(\\"name\\")`, is checked too.

A name resolves when it is a top-level key of a mod file under
`common/script_values/` (subfolders included) or of vanilla's, read from the
committed `vanilla_parsed/` snapshot (`common/script_values.json`). A scalar
`foo = 1` counts, and so does an `INJECT_OR_CREATE:` / `REPLACE_OR_CREATE:`
name. A scripted constant (`@foo = 3`) does not, and neither does an
`INJECT:`, `REPLACE:`, `TRY_INJECT:` or `TRY_REPLACE:` name: it edits a
definition that has to exist elsewhere, in the mod or vanilla, and that
definition is what resolves the read. The rule is
`gui_reference_audit.defined_names`, shared with that audit's `.gui` check
(#1180). No game install is needed. A missing snapshot raises
rather than flagging every vanilla name, and so does a scan that finds no loc
file at all, so a wrong path can't pass as clean.

Skipped as dynamic, and counted in the summary (`dynamic_skipped`): an
argument that is not a quoted literal identifier. That covers
`ScriptValue(Concatenate(...))`, a name built from `$PARAM$`, a dotted or
hyphenated name, and an unescaped `ScriptValue("x")`, whose first `"` ends the
loc value as the audit reads it (`check_localization_files.py` rejects that
line anyway).

`.gui` files are not scanned here: `gui_reference_audit` resolves
`ScriptValue('x')` in `gui/**/*.gui` against the mod's script values and the
same snapshot, and fails CI with `--strict`.

Suppression is check-tagged, trailing on the loc line (the engine ignores
anything after the closing quote):

    my_key:0 "[ScriptValue('x')]" # REVIEWED 2026-10-26 (loc_script_value): rationale

Keep the rationale free of `"`: the engine reads a loc value out to the
line's last quote, so a quote in the comment would pull the comment into the
text. A tag on a line with no flag is stale and fails `--strict`.

Report: docs/engine/loc_script_value_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from gui_reference_audit import defined_names
from mod_state import split_loc_line

CHECK = "loc_script_value"
SKIP_FILES = frozenset({"te_unused_l_english.yml"})
LOC_DIR = os.path.join("localization", "english")
SCRIPT_VALUE_DIR = os.path.join("common", "script_values")
VANILLA_SNAPSHOT = os.path.join("vanilla_parsed", "common", "script_values.json")
REPORT_PATH = os.path.join("docs", "engine", "loc_script_value_report.md")

# `ScriptValue(` and, when present, a quoted argument: `'x'` or the escaped
# `\"x\"` a loc value has to use (a bare `"` never gets here, since
# split_loc_line ends the value at it). A call whose argument isn't quoted
# (`Concatenate(...)`, a bare scope) leaves `arg` unset and is skipped.
_CALL_RE = re.compile(
    r"\bScriptValue\(\s*(?:(?P<q>\\?[\"'])(?P<arg>[^\"'\\]*)(?P=q)\s*\))?"
)
_NAME_RE = re.compile(r"[A-Za-z_]\w*")
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
    return result


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Loc script value audit report",
        "",
        "Auto-generated by `loc_script_value_audit.py` on every `POST /reload` of",
        "the mod state server. Do not hand-edit.",
        "",
        "Flagged: a `ScriptValue('name')` in a `localization/english/` value whose",
        "name is not a script value, in the mod's `common/script_values/` or in",
        "vanilla's (from the `vanilla_parsed/` snapshot). The text renders `0` and",
        "only debug.log says why. `te_unused_l_english.yml` is not scanned, and",
        "`.gui` files are `gui_reference_audit`'s.",
        "",
        "Fix: point the read at the script value's current name, or restore the",
        "script value.",
        "",
        "Suppress a deliberate case trailing on the loc line (no `\"` in the",
        "rationale):",
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
    loc and script value files itself, so `mod_state` is unused."""
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
