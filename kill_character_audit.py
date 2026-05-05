"""Detects unguarded `kill_character` calls in events/*.txt.

Background: event-flavor characters created without `place_character_in_void = 6`
get garbage-collected by the engine ~20 days into an open event. A subsequent
`kill_character = scope:X` (typically in an `after` block) then fires on an
invalidated scope. The mod's documented defense is two-fold:

1. Create the character with `on_created = { place_character_in_void = 6 }`,
   which keeps the engine from pruning it while the event is open.
2. Wrap every `kill_character` in `if = { limit = { exists = scope:X } ... }`
   so the kill is silently skipped if the scope is invalid for any reason.

This audit flags any `kill_character` lacking BOTH guards. As of 2026-05-04
all 35 occurrences in this mod's events/ are double-guarded — the audit
exists to catch regressions in future events.

Suppress an intentional flag with a same-line comment in the format:

    kill_character = scope:flavor_speaker  # REVIEWED 2026-05-04: rationale

CLI:
    python kill_character_audit.py            # write the report
    python kill_character_audit.py --check    # exit non-zero on issues
"""
from __future__ import annotations

import argparse
import bisect
import os
import re
import sys
from dataclasses import dataclass


@dataclass
class AuditFlag:
    file: str
    line: int
    event_id: str | None
    target_scope: str | None
    has_void6: bool
    has_exists_guard: bool
    reason: str
    exemption: dict | None = None


_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)
_EVENT_HEADER_RE = re.compile(
    r"^(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([A-Za-z_]\w*\.\w+)\s*=\s*\{"
)
_KILL_CHARACTER_RE = re.compile(r"(?<!\w)kill_character\b")
_KILL_TARGET_INLINE_RE = re.compile(r"kill_character\s*=\s*scope:([A-Za-z_]\w*)")
_SCOPE_HEADER_RE = re.compile(r"^scope:([A-Za-z_]\w*)\s*=\s*$")


def parse_reviewed_comment(line: str) -> dict | None:
    m = _REVIEWED_RE.search(line)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def find_event_id_at_line(lines: list[str], line_no: int) -> str | None:
    if not (1 <= line_no <= len(lines)):
        return None
    for i in range(line_no - 1, -1, -1):
        m = _EVENT_HEADER_RE.match(lines[i].lstrip())
        if m:
            return m.group(1)
    return None


def _strip_paradox(text: str) -> str:
    """Replace `#...\\n` comments and `"..."` strings with same-length space runs.

    Preserves byte offsets so brace positions in the cleaned text map back to
    the original. Newlines are kept intact.
    """
    out = list(text)
    in_comment = False
    in_string = False
    for i, c in enumerate(text):
        if in_comment:
            if c == "\n":
                in_comment = False
            else:
                out[i] = " "
        elif in_string:
            if c == '"':
                in_string = False
                out[i] = " "
            else:
                out[i] = " "
        else:
            if c == "#":
                in_comment = True
                out[i] = " "
            elif c == '"':
                in_string = True
                out[i] = " "
    return "".join(out)


def _build_brace_pairs(clean_text: str) -> dict[int, int]:
    """Map each `{` position to its matching `}` position and vice versa."""
    pairs: dict[int, int] = {}
    stack: list[int] = []
    for i, c in enumerate(clean_text):
        if c == "{":
            stack.append(i)
        elif c == "}":
            if stack:
                open_pos = stack.pop()
                pairs[open_pos] = i
                pairs[i] = open_pos
    return pairs


def _enclosing_open_positions(clean_text: str, pos: int) -> list[int]:
    """Return open-brace positions enclosing `pos`, innermost first."""
    stack: list[int] = []
    for i in range(pos):
        c = clean_text[i]
        if c == "{":
            stack.append(i)
        elif c == "}":
            if stack:
                stack.pop()
    return list(reversed(stack))


def _block_header_text(clean_text: str, open_pos: int) -> str:
    """Return the trimmed text from the previous `{`/`}`/`;` (or start of file)
    up to (but not including) the open brace. This is the head of the block,
    e.g. `if =`, `scope:flavor_speaker =`, `limit =`, `after =`.
    """
    # Walk backward to a delimiter that ends a sibling statement.
    end = open_pos
    start = end
    for i in range(end - 1, -1, -1):
        if clean_text[i] in "{};":
            start = i + 1
            break
    else:
        start = 0
    return clean_text[start:end].strip()


def _block_body(clean_text: str, open_pos: int, close_pos: int) -> str:
    return clean_text[open_pos + 1 : close_pos]


_LIMIT_EXISTS_RE = re.compile(
    r"limit\s*=\s*\{[^{}]*?exists\s*=\s*scope:([A-Za-z_]\w*)[^{}]*?\}",
    re.DOTALL,
)


def _has_exists_guard_for(clean_text: str, brace_pairs: dict[int, int],
                          kill_pos: int, target: str) -> bool:
    """True if some enclosing `if`/`else_if` block carries `limit = { exists = scope:target }`."""
    for open_pos in _enclosing_open_positions(clean_text, kill_pos):
        header = _block_header_text(clean_text, open_pos)
        # Strip trailing `=` so headers like "if =" become "if".
        head_kw = header.split("=")[0].strip()
        if head_kw not in {"if", "else_if"}:
            continue
        close_pos = brace_pairs.get(open_pos)
        if close_pos is None:
            continue
        body = _block_body(clean_text, open_pos, close_pos)
        for m in _LIMIT_EXISTS_RE.finditer(body):
            if m.group(1) == target:
                return True
    return False


def _resolve_target_scope(text: str, clean_text: str, kill_line: str,
                          kill_pos: int) -> str | None:
    """Determine which scope the `kill_character` operates on.

    Two cases:
    1. Inline form: `kill_character = scope:NAME` on the same line.
    2. Scope-change form: `scope:NAME = { ... kill_character = { ... } ... }`
       — the innermost enclosing `scope:NAME = {` block.
    """
    inline = _KILL_TARGET_INLINE_RE.search(kill_line)
    if inline:
        return inline.group(1)
    for open_pos in _enclosing_open_positions(clean_text, kill_pos):
        header = _block_header_text(clean_text, open_pos)
        # Strip trailing `=` for headers like `scope:flavor_speaker =`.
        head = header.rstrip("=").strip()
        m = _SCOPE_HEADER_RE.match(head + " ") or re.match(r"^scope:([A-Za-z_]\w*)$", head)
        if m:
            return m.group(1)
    return None


_CREATE_CHARACTER_BLOCK_RE = re.compile(
    r"create_character\s*=\s*\{",
)
_SAVE_SCOPE_AS_RE = re.compile(r"(?<!\w)save_scope_as\s*=\s*([A-Za-z_]\w*)")
_VOID6_RE = re.compile(r"(?<!\w)place_character_in_void\s*=\s*6\b")


def _voided_scopes(clean_text: str, brace_pairs: dict[int, int]) -> set[str]:
    """Return the set of `save_scope_as` names whose `create_character`
    blocks set `place_character_in_void = 6`."""
    voided: set[str] = set()
    for m in _CREATE_CHARACTER_BLOCK_RE.finditer(clean_text):
        # The brace dict keys are positions of `{`; the create_character block's
        # opening brace is whatever `{` lies at m.end()-1.
        open_pos = m.end() - 1
        close_pos = brace_pairs.get(open_pos)
        if close_pos is None:
            continue
        body = _block_body(clean_text, open_pos, close_pos)
        sn = _SAVE_SCOPE_AS_RE.search(body)
        if not sn:
            continue
        if _VOID6_RE.search(body):
            voided.add(sn.group(1))
    return voided


def audit_file(file_path: str, rel_path: str) -> list[AuditFlag]:
    with open(file_path, encoding="utf-8-sig") as f:
        text = f.read()
    clean = _strip_paradox(text)
    brace_pairs = _build_brace_pairs(clean)
    voided = _voided_scopes(clean, brace_pairs)

    lines = text.splitlines()
    line_starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(i + 1)

    flags: list[AuditFlag] = []
    for m in _KILL_CHARACTER_RE.finditer(clean):
        kill_pos = m.start()
        line_no = bisect.bisect_right(line_starts, kill_pos)
        if not (1 <= line_no <= len(lines)):
            continue
        kill_line = lines[line_no - 1]
        prev_line = lines[line_no - 2] if line_no >= 2 else ""
        exemption = parse_reviewed_comment(kill_line) or parse_reviewed_comment(prev_line)

        target = _resolve_target_scope(text, clean, kill_line, kill_pos)
        has_void6 = bool(target and target in voided)
        has_guard = bool(target and _has_exists_guard_for(clean, brace_pairs, kill_pos, target))

        # Doubly-guarded calls are silent; everything else gets a flag (even
        # single-guard "defense-in-depth gaps") so future regressions surface.
        if has_void6 and has_guard:
            continue
        flags.append(AuditFlag(
            file=rel_path,
            line=line_no,
            event_id=find_event_id_at_line(lines, line_no),
            target_scope=target,
            has_void6=has_void6,
            has_exists_guard=has_guard,
            reason=_describe_reason(target, has_void6, has_guard),
            exemption=exemption,
        ))
    return flags


def _describe_reason(target: str | None, has_void6: bool, has_guard: bool) -> str:
    if target is None:
        return "could not resolve target scope"
    parts = []
    if not has_void6:
        parts.append(f"no `create_character` for `scope:{target}` with `place_character_in_void = 6`")
    if not has_guard:
        parts.append(f"no enclosing `if = {{ limit = {{ exists = scope:{target} }} ... }}`")
    return "; ".join(parts) or "passes both guards"


def audit(events_dir: str) -> list[AuditFlag]:
    if not os.path.isdir(events_dir):
        return []
    flags: list[AuditFlag] = []
    for fname in sorted(os.listdir(events_dir)):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(events_dir, fname)
        rel = os.path.join("events", fname)
        flags.extend(audit_file(fpath, rel))
    return flags


def render_report(flags: list[AuditFlag], files_audited: int) -> str:
    fails = [f for f in flags if not f.exemption and not (f.has_void6 and f.has_exists_guard)
             and not (f.has_void6 or f.has_exists_guard)]
    partial = [f for f in flags if not f.exemption and (f.has_void6 ^ f.has_exists_guard)]
    exempted = [f for f in flags if f.exemption]

    out = [
        "# Kill-character guard audit",
        "",
        "Auto-generated by `scripts/analysis/kill_character_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Each `kill_character` in `events/` should satisfy BOTH:",
        "1. The targeted character is created with `on_created = { place_character_in_void = 6 }`.",
        "2. The kill is wrapped in `if = { limit = { exists = scope:X } ... }`.",
        "",
        "Suppress an intentional flag with a same-line comment:",
        "`kill_character = scope:X  # REVIEWED YYYY-MM-DD: rationale`",
        "",
        f"Files audited: **{files_audited}**.  ",
        f"Total `kill_character` occurrences flagged: **{len(flags)}**.  ",
        f"Hard fails (neither guard): **{len(fails)}**.  ",
        f"Defense-in-depth gaps (only one guard): **{len(partial)}**.  ",
        f"Reviewed exemptions: **{len(exempted)}**.",
        "",
        "## Hard fails",
        "",
    ]
    if not fails:
        out.append("_None._")
        out.append("")
    else:
        for f in fails:
            out.append(
                f"- `{f.file}:{f.line}` — event `{f.event_id or '?'}` — "
                f"target `scope:{f.target_scope or '?'}` — {f.reason}"
            )
        out.append("")

    out.append("## Defense-in-depth gaps")
    out.append("")
    if not partial:
        out.append("_None._")
        out.append("")
    else:
        for f in partial:
            out.append(
                f"- `{f.file}:{f.line}` — event `{f.event_id or '?'}` — "
                f"target `scope:{f.target_scope or '?'}` — {f.reason}"
            )
        out.append("")

    out.append("## Reviewed exemptions")
    out.append("")
    if not exempted:
        out.append("_None._")
        out.append("")
    else:
        for f in exempted:
            assert f.exemption is not None
            out.append(
                f"- `{f.file}:{f.line}` — event `{f.event_id or '?'}` — "
                f"target `scope:{f.target_scope or '?'}` — {f.exemption['date']}: "
                f"{f.exemption['rationale']}"
            )
        out.append("")

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Post-load hook (matches POST_LOAD_GENERATORS protocol in mod_state_server).
# ---------------------------------------------------------------------------


def regenerate(mod_state) -> dict:  # noqa: ARG001 — protocol arg unused
    from path_constants import mod_path
    events_dir = os.path.join(mod_path, "events")
    flags = audit(events_dir)
    files_audited = sum(
        1 for fname in os.listdir(events_dir)
        if fname.endswith(".txt") and os.path.isfile(os.path.join(events_dir, fname))
    ) if os.path.isdir(events_dir) else 0
    report = render_report(flags, files_audited)
    out_path = os.path.join(mod_path, "docs", "kill_character_audit.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    fails = sum(1 for f in flags if not f.exemption
                and not (f.has_void6 and f.has_exists_guard)
                and not (f.has_void6 or f.has_exists_guard))
    return {
        "files_audited": files_audited,
        "total_flags": len(flags),
        "hard_fails": fails,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Exit non-zero on hard fails (no report written).")
    parser.add_argument("--events-dir",
                        help="Override events/ directory (defaults to repo events/).")
    args = parser.parse_args()

    if args.events_dir:
        events_dir = args.events_dir
        repo_root = os.path.dirname(os.path.abspath(events_dir))
    else:
        repo_root = os.path.dirname(os.path.abspath(__file__))
        events_dir = os.path.join(repo_root, "events")

    flags = audit(events_dir)
    files_audited = sum(
        1 for fname in os.listdir(events_dir)
        if fname.endswith(".txt") and os.path.isfile(os.path.join(events_dir, fname))
    ) if os.path.isdir(events_dir) else 0

    if args.check:
        fails = [f for f in flags if not f.exemption
                 and not (f.has_void6 and f.has_exists_guard)
                 and not (f.has_void6 or f.has_exists_guard)]
        if fails:
            for f in fails:
                print(f"FAIL {f.file}:{f.line} event={f.event_id or '?'} "
                      f"scope:{f.target_scope or '?'} — {f.reason}", file=sys.stderr)
            return 1
        return 0

    report = render_report(flags, files_audited)
    out_path = os.path.join(repo_root, "docs", "kill_character_audit.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Wrote {out_path} — {len(flags)} flags across {files_audited} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
