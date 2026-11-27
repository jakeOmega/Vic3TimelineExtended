"""Flag a bare name in a script value position that nothing defines (#2021).

A value position takes a number, a script value, or an engine value or link:
`value = X`, `add = X`, `max = X`, `count = X`, `add_modifier`'s
`multiplier = X` and `days = X`, and the right side of `<`, `>`, `<=`, `>=`,
`!=` and `==`. A bare name there that is none of these, because it was
renamed, deleted or never written, compiles to nothing without a word in any
log: the cap is gone, the self-check reads 0. `loc_script_value_audit` catches
the same mistake in a loc `ScriptValue('x')`, and `gui_reference_audit` in a
`.gui` file; this is the script half. Space forces personnel (PR #2020) used
`sr_pers_state_spacers` and `sr_pers_state_spacer_steps` in four places,
defined neither, and passed every audit; the system's own test
(`test_space_forces_personnel.py`) was the stopgap.

What is checked
---------------
Every value written as a bare identifier (letters, digits and `_` only) after
one of `VALUE_KEYS` with `=`, or after any key with one of `COMPARISONS`, in
`common/**/*.txt` and `events/**/*.txt`, the generated files included.
Comments and strings are blanked first. Not judged, and counted in the
report's summary as `chained_skipped`: a prefixed or chained value
(`scope:x`, `var:x`, `define:X|Y`, `owner.x`, `c:USA`), a name built from a
`$PARAM$` and a `@constant`. `=` is not read as a comparison: it is also an
assignment, and the keys above are the positions it can tell apart.

A name resolves when it is

- a script value: a top-level key of a mod file under `common/script_values/`
  or of vanilla's, from the committed `vanilla_parsed/` snapshot (what counts
  as a definition is `gui_reference_audit.defined_names`, as for
  `loc_script_value_audit`);
- a mod scripted trigger or effect (the issue's proposal; neither is a value,
  so this only errs towards silence);
- an engine trigger or event target, from `docs/engine/triggers_summary.txt`
  and `docs/engine/event_targets_summary.txt` (`total_size`, `gdp`, `root`;
  a scope keyword in any case, `ROOT`, `PREV`);
- one of `ENGINE_WORDS`: `yes`, `no`, `count = all`, and the engine's levels
  for stances (`law_stance = { law = x value < neutral }`), IG approval
  (`ig_approval < happy`) and wage levels (`military_wage_level <= low`).

A missing snapshot or engine list raises rather than flagging every vanilla
name.

Suppress a deliberate case trailing on the flagged line:

    max = my_value # REVIEWED 2026-11-27 (script_value_reference): why

A tag on a line with no flag is stale and fails `--strict`.

Report: docs/engine/script_value_reference_report.md. Registered in
POST_LOAD_AUDITS.
"""
from __future__ import annotations

import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field
from pathlib import Path

from audit_common import AuditResult as _AuditResult
from audit_common import StaleTag, cli_main, parse_reviewed, render_report, summary, write_text
from blanked_text import blank_comments_and_strings
from gui_reference_audit import defined_names
from loc_script_value_audit import mod_script_value_names, vanilla_script_value_names

CHECK = "script_value_reference"
AUDIT_DIRS = ("common", "events")
DEFINING_DIRS = (os.path.join("common", "scripted_triggers"), os.path.join("common", "scripted_effects"))
ENGINE_LISTS = (os.path.join("docs", "engine", "triggers_summary.txt"),
                os.path.join("docs", "engine", "event_targets_summary.txt"))
REPORT_PATH = os.path.join("docs", "engine", "script_value_reference_report.md")

# Keys whose `=` value is a script value position. `factor` is not one
# (`change_appeasement`'s names an appeasement factor), nor `name` or
# `modifier`.
VALUE_KEYS = frozenset({
    "value", "add", "subtract", "multiply", "divide", "min", "max", "count",
    "multiplier", "days", "weeks", "months", "years",
})
COMPARISONS = frozenset({"<", ">", "<=", ">=", "!=", "=="})

ENGINE_WORDS = frozenset({
    "yes", "no",
    "all",  # `count = all` in an any_* trigger
    # Law and amendment stances (law_stance, law_enactment_stance, amendment_stance):
    # vanilla's amendments.json compares `value < neutral`.
    "strongly_disapprove", "disapprove", "neutral", "approve", "strongly_approve",
    # IG approval levels: triggers.log gives `ig_approval < happy`.
    "angry", "unhappy", "happy", "loyal",
    # Wage levels (military_wage_level, government_wage_level).
    "very_low", "low", "medium", "high", "very_high",
})

# A key, its operator, and the value when it is a name or a block. The value
# group takes the characters a prefixed or chained value can hold, so the
# whole token is seen and a `scope:x` is not read as `scope`.
_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z0-9_@][A-Za-z0-9_.:|@$\-]*)\s*(?P<op>\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[A-Za-z_$][A-Za-z0-9_.:|@$\-]*))?"
    r"|(?P<anon>\{)"
)
_BARE_RE = re.compile(r"[A-Za-z_]\w*")


@dataclass
class Flag:
    file: str
    line: int
    key: str
    op: str
    name: str
    exemption: dict | None = None

    @property
    def message(self) -> str:
        return f"`{self.key} {self.op} {self.name}`: `{self.name}` is no script value, trigger or event target"


@dataclass
class AuditResult(_AuditResult):
    flags: list[Flag] = field(default_factory=list)
    files_scanned: int = 0
    refs_checked: int = 0
    chained_skipped: int = 0
    names_indexed: int = 0


def engine_names(mod_path: str | Path) -> set[str]:
    """The trigger and event target names of the engine docs (the second column of each list)."""
    names: set[str] = set()
    for rel in ENGINE_LISTS:
        path = Path(mod_path) / rel
        if not path.is_file():
            raise FileNotFoundError(f"{path} is missing; without it every engine trigger used as a value "
                                    "would be flagged")
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.split("|")
            if not line.startswith("#") and len(parts) > 2 and parts[1]:
                names.add(parts[1])
    return names


def known_names(mod_path: str | Path) -> tuple[set[str], set[str]]:
    """(the script values, triggers and effects defined in script; the engine's names, lower case)."""
    root = Path(mod_path)
    defined = mod_script_value_names(root) | vanilla_script_value_names(root)
    for rel in DEFINING_DIRS:
        for path in sorted((root / rel).rglob("*.txt")):
            defined |= defined_names(path.read_text(encoding="utf-8-sig", errors="replace"))
    engine = {n.lower() for n in engine_names(root)} | ENGINE_WORDS
    return defined, engine


def scan_text(text: str, rel_path: str, defined: set[str], engine: set[str],
              result: AuditResult | None = None) -> tuple[list[Flag], list[StaleTag]]:
    """The flags of one file, and the tags in it that suppress nothing."""
    clean, comments = blank_comments_and_strings(text)
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]
    flags: list[Flag] = []
    for m in _TOKEN_RE.finditer(clean):
        value = m.group("value")
        if not value:
            continue
        key, op = m.group("key"), m.group("op")
        if not (op in COMPARISONS or (op == "=" and key in VALUE_KEYS)):
            continue
        if not _BARE_RE.fullmatch(value):
            if result is not None:
                result.chained_skipped += 1
            continue
        if result is not None:
            result.refs_checked += 1
        if value in defined or value.lower() in engine:
            continue
        line = bisect_right(starts, m.start("value"))
        flags.append(Flag(rel_path, line, key, op, value, parse_reviewed(comments.get(line), (CHECK,))))
    flagged = {f.line for f in flags}
    stale = [StaleTag(rel_path, line, CHECK) for line, comment in sorted(comments.items())
             if line not in flagged and parse_reviewed(comment, (CHECK,))]
    return flags, stale


def audit(mod_path: str | Path | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    root = Path(mod_path)
    defined, engine = known_names(root)
    result = AuditResult(names_indexed=len(defined) + len(engine))
    for sub in AUDIT_DIRS:
        for path in sorted((root / sub).rglob("*.txt")):
            rel = path.relative_to(root).as_posix()
            flags, stale = scan_text(path.read_text(encoding="utf-8-sig", errors="replace"), rel,
                                     defined, engine, result)
            result.flags += flags
            result.stale += stale
            result.files_scanned += 1
    if not result.files_scanned:
        raise FileNotFoundError(f"no script file under {root}/common or {root}/events")
    return result


INTRO = """Flagged: a bare name in a script value position (`value =`, `add =`, `subtract =`,
`multiply =`, `divide =`, `min =`, `max =`, `count =`, `multiplier =`, `days =` and the other
durations, or the right side of `<`, `>`, `<=`, `>=`, `!=`, `==`) that is no script value (the
mod's or vanilla's), scripted trigger or effect, engine trigger or event target, or engine level
word (`neutral`, `happy`, `low`). It compiles to nothing, with no log line. Prefixed and chained
values (`scope:x`, `var:x`, `owner.x`) and `$PARAM$` names are not judged.

Fix: define the script value, or point the read at its current name."""


def render(result: AuditResult) -> str:
    # Flag counts only: the values checked stay in the regenerate() summary, since they move with unrelated
    # script.
    return render_report(result, "Script value reference audit report", audit="script_value_reference_audit",
                         intro=INTRO)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report. A pure file
    scan, so `mod_state` is unused."""
    from path_constants import mod_path
    result = audit(mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    write_text(out_path, render(result))
    out = summary(result, files_scanned=result.files_scanned, refs_checked=result.refs_checked,
                  chained_skipped=result.chained_skipped, names_indexed=result.names_indexed, path=out_path)
    # A stale tag fails --strict, so a reload warns of it too.
    out["unreviewed"] = len(result.failing)
    return out


def main(argv=None) -> int:
    def add_arguments(parser):
        parser.add_argument("--mod-path", type=Path)

    return cli_main(lambda args: audit(args.mod_path), lambda result, args: render(result),
                    argv=argv, description=__doc__.splitlines()[0], add_arguments=add_arguments)


if __name__ == "__main__":
    raise SystemExit(main())
