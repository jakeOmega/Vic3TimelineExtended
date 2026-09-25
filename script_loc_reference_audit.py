"""Detects loc keys named in script that no localization file defines.

Background: script names loc keys directly in a handful of fields — the
`desc = "KEY"` that labels a line of a script-value breakdown (a political
movement's radicalism factors, a party's attraction, a treaty's AI acceptance,
a power bloc's cohesion), `custom_tooltip = KEY`, an event's `title`/`flavor`,
a journal entry's `custom_completion_header`, and so on. The engine resolves
the key at render time and, when it is missing, prints the raw key in the
tooltip. Nothing is logged. The mod's movements shipped
`desc = "INSTITUTION_FUNDING_LEVEL_ministry_of_foreign_affairs"` copied from
vanilla's pattern without the loc line vanilla has for its own institutions,
and the radicalism breakdown showed the raw key (fixed 2026-09-25).

`loc_coverage_audit` asks the opposite question (does each mod entity have
its conventional keys?) and so never sees a key that only script names.

Fields checked (`LOC_REFERENCE_FIELDS`): each one resolves to a loc key at
every one of its uses in vanilla `common/` and `events/`, except for a single
vanilla bug (`desc = POP_SERVICEMEN`). `text` counts only inside
`custom_tooltip = { }`. Inside `custom_description = { }` it names a
`trigger_localization` entry, not a loc key. The trigger-localization fields
(`first`, `third`, `global`, `none`, `*_not`, `*_neg`) are left out: vanilla
itself leaves about 270 of them unlocalized, so a miss there is no evidence of
a visible raw key. `name` is left out because it names variables, flags and
entities as often as loc.

Skipped values: `yes`/`no`, anything containing `$` (a key built from a
script parameter), quoted text with spaces, and block values (`desc = { ... }`,
whose `triggered_desc` children are checked individually).

Suppress an intentional unresolved reference with a trailing comment on the
same line: `desc = "SOME_KEY" # REVIEWED YYYY-MM-DD: rationale`.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Callable

LOC_REFERENCE_FIELDS = frozenset({
    "desc",
    "title",
    "flavor",
    "custom_tooltip",
    "custom_tooltip_no_bullet",
    "text",
    "button_text",
    "custom_text",
    "header",
    "header_info",
    "custom_completion_header",
    "custom_on_completion_header",
    "custom_failure_header",
    "custom_on_failure_header",
    "qualifications_growth_desc",
})

# `text` is a loc key only inside these blocks.
_TEXT_PARENTS = frozenset({"custom_tooltip"})

SCAN_DIRS = ("common", "events")

_KEY_RE = re.compile(r"[A-Za-z_][\w.\-]*")
_TOKEN_RE = re.compile(r'"[^"\n]*"?|[{}=]|[^\s{}="#]+')
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)


@dataclass
class Flag:
    file: str
    line: int
    field: str
    key: str
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0
    references_checked: int = 0


def _split_comment(line: str) -> tuple[str, str | None]:
    """Split at the first `#` outside a quoted string."""
    in_quote = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quote = not in_quote
        elif ch == "#" and not in_quote:
            return line[:i], line[i:]
    return line, None


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def iter_references(text: str):
    """Yield `(line, field, key, comment)` for every loc-key reference in a
    Paradox script file's text. `comment` is the trailing comment of the
    reference's line, for REVIEWED suppression."""
    tokens: list[tuple[str, int]] = []
    comments: dict[int, str] = {}
    for line_num, raw in enumerate(text.splitlines(), 1):
        code, comment = _split_comment(raw)
        if comment:
            comments[line_num] = comment
        tokens.extend((t, line_num) for t in _TOKEN_RE.findall(code))

    # Block-name stack; None for an anonymous `{`.
    stack: list[str | None] = []
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i][0]
        if tok == "{":
            stack.append(None)
            i += 1
            continue
        if tok == "}":
            if stack:
                stack.pop()
            i += 1
            continue
        if i + 2 < n and tokens[i + 1][0] == "=":
            value, line_num = tokens[i + 2]
            if value == "{":
                stack.append(tok)
                i += 3
                continue
            if tok in LOC_REFERENCE_FIELDS and (
                tok != "text" or (stack and stack[-1] in _TEXT_PARENTS)
            ):
                key = value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value
                if key not in ("yes", "no") and _KEY_RE.fullmatch(key):
                    yield line_num, tok, key, comments.get(line_num)
            i += 3
            continue
        i += 1


def scan_file(
    abs_path: str, rel_path: str, has_loc: Callable[[str], bool]
) -> tuple[list[Flag], int]:
    """Return (flags, references checked) for one file."""
    try:
        with open(abs_path, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return [], 0
    flags: list[Flag] = []
    checked = 0
    for line_num, fld, key, comment in iter_references(text):
        checked += 1
        if has_loc(key):
            continue
        flags.append(Flag(
            file=rel_path, line=line_num, field=fld, key=key,
            exemption=_parse_reviewed(comment),
        ))
    return flags, checked


def audit(has_loc: Callable[[str], bool], mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    result = AuditResult()
    for sub in SCAN_DIRS:
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            dirs.sort()
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                flags, checked = scan_file(abs_p, os.path.relpath(abs_p, mod_path), has_loc)
                result.flags.extend(flags)
                result.references_checked += checked
                result.files_audited += 1
    return result


def offline_localization(mod_path: str) -> set[str]:
    """Vanilla keys from the committed `vanilla_parsed/` snapshot plus the
    mod's own english loc — what the CLI and CI check against, with no game
    install needed."""
    import vanilla_parsed
    from mod_state import iter_loc_files, parse_loc_line

    keys = set(vanilla_parsed.load().localization)
    english = os.path.join(mod_path, "localization", "english")
    for loc_dir in (english, os.path.join(english, "replace")):
        if not os.path.isdir(loc_dir):
            continue
        for path in iter_loc_files(loc_dir):
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                for line in fh:
                    parsed = parse_loc_line(line)
                    if parsed is not None:
                        keys.add(parsed[0])
    return keys


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Script loc reference audit report",
        "",
        "Auto-generated by `script_loc_reference_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a loc key named in script (`desc = \"KEY\"` on a breakdown",
        "line, `custom_tooltip = KEY`, an event `title`, …) that no vanilla or",
        "mod localization file defines. The engine prints the raw key in the",
        "tooltip and logs nothing.",
        "",
        "Fix: add the key to a `localization/english/*_l_english.yml` file, or",
        "point the field at an existing key.",
        "",
        "Suppress an intentional case with a trailing comment on the same line:",
        "`desc = \"SOME_KEY\" # REVIEWED YYYY-MM-DD: rationale`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_file: dict[str, list[Flag]] = {}
        for f in unrev:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out.append(f"### `{fname}` ({len(by_file[fname])})")
            out.append("")
            for f in by_file[fname]:
                out.append(f"- line {f.line}: `{f.field} = {f.key}`")
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — `{f.field} = {f.key}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- files audited: {result.files_audited}")
    out.append(f"- references checked: {result.references_checked}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")
    return "\n".join(out) + "\n"


def regenerate(mod_state) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state.has_localization, mod_path=mod_path)
    out_path = os.path.join(mod_path, "docs", "engine", "script_loc_reference_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    unrev = sum(1 for f in result.flags if not f.exemption)
    return {
        "files_audited": result.files_audited,
        "references_checked": result.references_checked,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": len(result.flags) - unrev,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    keys = offline_localization(mod_path)
    result = audit(keys.__contains__, mod_path=mod_path)
    print(render_report(result))
    # --strict: CI mode. Exit 1 if any flag lacks a `# REVIEWED ...` exemption.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in result.flags) else 0)
