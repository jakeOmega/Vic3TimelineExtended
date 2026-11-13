"""Parse-time audit: fractional `*_standard_of_living_add` modifiers (issue #338).

Pop standard of living is a whole-number level, so a `*_standard_of_living_add`
below 1 does nothing on its own: it renders in the tooltip and changes no
outcome unless it happens to sum with other live sources across a whole point.
The fractional part of a value such as 1.5 is inert the same way. Every vanilla
grant of these keys but two is a whole number. The engine says nothing about
it. Lesson: `docs/guides/scripting_best_practices.md` § "Standard of Living Is
an INTEGER".

Rule: flag a literal `<key>_standard_of_living_add = <non-integer>` in `common/`
or `events/`, except where the value is scaled before it applies:

- inside a `workforce_scaled`, `level_scaled` or `throughput_scaled` block
  (multiplied by workforce or levels, so the total is not the literal);
- in a static modifier that the mod applies with `add_modifier = { name = X
  multiplier = ... }` (directly, or through a scripted effect whose
  `add_modifier` takes `name = $P$` with a multiplier and a call passing
  `P = X`), or names in a journal entry's `scaling_modifiers_while_active`;
- in an institution-scaled block (a law's or principle's
  `institution_modifier`, or an institution's own `modifier`), which applies
  once per level of investment. Such a line is flagged only when it stays below
  a whole point even at the highest level, `MAX_INSTITUTION_INVESTMENT` from
  the mod's defines (vanilla's 5 if the mod sets none).

Suppress an intended value with `# REVIEWED YYYY-MM-DD: rationale` trailing on
the flagged line, e.g. "designed to stack with X to reach 1".

Report: docs/engine/sol_fraction_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from audit_common import AuditResult as _AuditResult
from audit_common import cli_main, parse_reviewed, write_text

_SOL_RE = re.compile(
    r"^[ \t]*(?P<key>[a-z_][a-z0-9_]*standard_of_living_add)[ \t]*=[ \t]*"
    r"(?P<value>-?\d+(?:\.\d+)?)\b(?P<rest>.*)$"
)
_OPENER_RE = re.compile(r"(?P<key>[A-Za-z0-9_:.$\-]+)[ \t]*=[ \t]*\{")
_TOP_RE = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_:.\-]*)[ \t]*=[ \t]*\{")
_DEFINE_RE = re.compile(r"^[ \t]*MAX_INSTITUTION_INVESTMENT[ \t]*=[ \t]*(\d+)", re.M)

_SCALING_WRAPPERS = frozenset({"workforce_scaled", "level_scaled", "throughput_scaled"})
VANILLA_MAX_INSTITUTION_INVESTMENT = 5

# Definitions, not uses (script values are scalars; the type files register).
_SKIP_COMMON_SUBDIRS = frozenset({"modifier_type_definitions", "script_values"})


@dataclass
class SolFlag:
    file: str
    line: int
    entity: str
    key: str
    value: str
    institution_scaled: bool = False
    exemption: dict | None = None


@dataclass
class AuditResult(_AuditResult):
    flags: list[SolFlag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


# This audit's old name for the shared parser.
parse_reviewed_comment = parse_reviewed


def _strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _iter_files(mod_path: str):
    for top in ("common", "events"):
        base = os.path.join(mod_path, top)
        if not os.path.isdir(base):
            continue
        for dirpath, dirs, files in os.walk(base):
            rel_dir = os.path.relpath(dirpath, base)
            if top == "common" and rel_dir.split(os.sep)[0] in _SKIP_COMMON_SUBDIRS:
                dirs[:] = []
                continue
            dirs.sort()
            for f in sorted(files):
                if f.endswith(".txt"):
                    p = os.path.join(dirpath, f)
                    yield p, os.path.relpath(p, mod_path).replace(os.sep, "/")


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _blocks(text: str, opener: str):
    """Yield the body of every `<opener> = { ... }` in comment-stripped text."""
    for m in re.finditer(r"\b" + re.escape(opener) + r"[ \t]*=[ \t]*\{", text):
        depth, i = 0, m.end() - 1
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield text[m.end():i]


def _top_level_bodies(text: str):
    """Yield (name, body) for every top-level `name = { ... }`."""
    depth, start, name = 0, 0, None
    i = 0
    for line in text.splitlines(keepends=True):
        if depth == 0:
            m = _TOP_RE.match(line)
            if m:
                name, start = m.group("name"), i
        depth += line.count("{") - line.count("}")
        i += len(line)
        if depth <= 0 and name is not None:
            yield name, text[start:i]
            name, depth = None, 0


_NAME_RE = re.compile(r"\bname[ \t]*=[ \t]*(?P<name>\$?[A-Za-z0-9_]+\$?)")
_MULT_RE = re.compile(r"\bmultiplier[ \t]*=")


def scaled_modifier_names(texts: dict[str, str]) -> set[str]:
    """Static modifier names the mod applies scaled: `add_modifier` with a
    `multiplier`, through a helper's `$P$`, or in `scaling_modifiers_while_active`.
    `texts` maps relative path to comment-stripped file text."""
    names: set[str] = set()
    helper_params: dict[str, set[str]] = {}
    for rel, text in texts.items():
        for body in _blocks(text, "add_modifier"):
            if not _MULT_RE.search(body):
                continue
            nm = _NAME_RE.search(body)
            if not nm:
                continue
            n = nm.group("name")
            if n.startswith("$"):
                continue
            names.add(n)
        for body in _blocks(text, "scaling_modifiers_while_active"):
            m = re.search(r"\bmodifier[ \t]*=[ \t]*([A-Za-z0-9_]+)", body)
            if m:
                names.add(m.group(1))
        if rel.startswith("common/scripted_effects/"):
            for eff, body in _top_level_bodies(text):
                for amb in _blocks(body, "add_modifier"):
                    nm = _NAME_RE.search(amb)
                    if nm and nm.group("name").startswith("$") and _MULT_RE.search(amb):
                        helper_params.setdefault(eff, set()).add(nm.group("name").strip("$"))
    for eff, params in helper_params.items():
        for text in texts.values():
            for body in _blocks(text, eff):
                for p in params:
                    m = re.search(r"\b" + re.escape(p) + r"[ \t]*=[ \t]*([A-Za-z0-9_]+)", body)
                    if m:
                        names.add(m.group(1))
    return names


def max_institution_investment(mod_path: str) -> int:
    base = os.path.join(mod_path, "common", "defines")
    best = None
    if os.path.isdir(base):
        for f in sorted(os.listdir(base)):
            if f.endswith(".txt"):
                m = _DEFINE_RE.search(_strip_comments(_read(os.path.join(base, f))))
                if m:
                    best = int(m.group(1))
    return best if best is not None else VANILLA_MAX_INSTITUTION_INVESTMENT


def _scan(rel: str, text: str, scaled: set[str], max_inst: int) -> tuple[list[SolFlag], int]:
    flags: list[SolFlag] = []
    seen = 0
    stack: list[str] = []  # opener keys of the blocks the current line is inside
    is_institution_file = rel.startswith("common/institutions/")
    for lineno, line in enumerate(text.splitlines(), start=1):
        code = line.split("#", 1)[0]
        m = _SOL_RE.match(code)
        if m and stack:
            seen += 1
            value = m.group("value")
            fval = float(value)
            entity = stack[0]
            if fval != int(fval):
                inst = "institution_modifier" in stack or (
                    is_institution_file and len(stack) >= 2 and stack[1] == "modifier"
                )
                skip = (
                    any(k in _SCALING_WRAPPERS for k in stack)
                    or entity.split(":")[-1] in scaled
                    or (inst and abs(fval) * max_inst >= 1)
                )
                if not skip:
                    comment = line[line.find("#"):] if "#" in line else ""
                    flags.append(SolFlag(
                        file=rel, line=lineno, entity=entity, key=m.group("key"),
                        value=value, institution_scaled=inst,
                        exemption=parse_reviewed_comment(comment),
                    ))
        # Track block nesting: each `{` pushes its opener key (or "" when bare).
        pos = 0
        for ch_m in re.finditer(r"[{}]", code):
            if ch_m.group() == "{":
                om = None
                for om in _OPENER_RE.finditer(code[pos:ch_m.end()]):
                    pass
                stack.append(om.group("key") if om else "")
            elif stack:
                stack.pop()
            pos = ch_m.end()
    return flags, seen


def audit(mod_path: str) -> AuditResult:
    files = list(_iter_files(mod_path))
    raw = {rel: _read(p) for p, rel in files}
    stripped = {rel: _strip_comments(t) for rel, t in raw.items()}
    scaled = scaled_modifier_names(stripped)
    max_inst = max_institution_investment(mod_path)
    flags: list[SolFlag] = []
    seen = 0
    for rel, text in raw.items():
        f, n = _scan(rel, text, scaled, max_inst)
        flags.extend(f)
        seen += n
    return AuditResult(flags=flags, coverage={
        "files_audited": len(raw), "sol_lines": seen,
        "scaled_modifiers": len(scaled), "max_institution_investment": max_inst,
    })


def render_report(result: AuditResult) -> str:
    unrev = result.unreviewed
    exemp = result.exemptions
    out = [
        "# Fractional standard of living audit report",
        "",
        "Auto-generated by `sol_fraction_audit.py` on every `POST /reload` of the",
        "mod state server. Do not hand-edit.",
        "",
        "Flagged: a `*_standard_of_living_add` literal that is not a whole number and",
        "is not scaled before it applies. Standard of living is an integer, so the",
        "fraction does nothing on its own. Round it to a whole point where a whole",
        "point is the right size, or express the intent with another lever (an",
        "expectations offset, sized conservatively; radicals and loyalists; approval).",
        "",
        "Not flagged: lines in `workforce_scaled` / `level_scaled` / `throughput_scaled`,",
        "static modifiers applied with a `multiplier` or a journal entry's",
        "`scaling_modifiers_while_active`, and institution-scaled lines that reach a",
        "whole point at the top investment level.",
        "",
        "Suppress an intended value with `# REVIEWED YYYY-MM-DD: rationale` on its line.",
        "",
        "## Unreviewed flags",
        "",
    ]
    if not unrev:
        out += ["_None._", ""]
    else:
        for f in unrev:
            note = " (per institution level, below 1 at the top level)" if f.institution_scaled else ""
            out.append(f"- `{f.file}:{f.line}` `{f.entity}`: `{f.key} = {f.value}`{note}")
        out.append("")
    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}` `{f.entity}`: `{f.key} = {f.value}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")
    out += [
        "## Coverage", "",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        "",
    ]
    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS entry point. File-based; `mod_state` is unused."""
    from path_constants import mod_path

    result = audit(mod_path)
    out_path = os.path.join(mod_path, "docs", "engine", "sol_fraction_report.md")
    write_text(out_path, render_report(result))
    return {
        "unreviewed": len(result.unreviewed),
        "exempted": len(result.exemptions),
        **result.coverage,
        "path": out_path,
    }


def main(argv=None) -> int:
    """Print the report; `--strict` (CI) exits 1 if any flag lacks a
    `# REVIEWED ...` exemption."""
    from path_constants import mod_path as _mp

    return cli_main(lambda args: audit(_mp), lambda result, args: render_report(result),
                    argv=argv, description=__doc__.splitlines()[0])


if __name__ == "__main__":
    raise SystemExit(main())
