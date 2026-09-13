"""Audit for a permanent `add_modifier { multiplier = var:X }` whose backing
variable is removed later in the same top-level block.

The engine stores the `multiplier` **expression** with the modifier and
re-evaluates it on later ticks (decay, tooltip, recalculation), not just at
`add_modifier` time. If the variable it reads has since been removed, every
later evaluation reads `'none'` and the engine logs
`Value of wrong type ... Got value of type 'none'` (`jomini_scriptvalue.cpp`)
while the modifier silently behaves as if unscaled::

    add_modifier = { name = shield  multiplier = var:_best_boost }
    ...
    remove_variable = _best_boost          # <- the multiplier now reads 'none'

Real cases: `population_transfer_effect` (`extra_effects.txt`, first instance)
and `update_intel_sharing_defense` (`treaty_article_effects.txt`, fixed in #240
by pointing the multiplier at the persistent `intel_shield_mult` copy).
Documented in `scripting_best_practices.md`, "Variables backing
`add_modifier { multiplier = … }` must persist beyond the call site".

Scope of the rule
-----------------
* Only **permanent** modifiers are flagged — an `add_modifier` carrying
  `days` / `months` / `years` is allowed to outlive its variable here, because
  the issue's rule targets the never-expiring shape (a timed modifier still
  re-evaluates, so those are worth a look, but they are not flagged to keep the
  audit's signal clean).
* Multiplier forms matched: `var:X`, `owner.var:X`, `root.var:X`,
  `scope:S.var:X` (any scope-path prefix) and `local_var:X`. A `var:` name is
  paired with `remove_variable`, a `local_var:` name with
  `remove_local_variable`; the match is on the bare variable name.
* Only a removal that appears **after** the `add_modifier` and inside the same
  top-level block (one scripted effect / on_action / event / journal entry /
  scripted button) counts. Setting the variable again later is fine — only
  removal breaks re-evaluation.
* One exemption inside that block: a removal sitting in a mutually exclusive
  branch (`if` vs `else` / `else_if`, two `option`s of an event, two children of
  a `random_list` / `switch`) **that first calls `remove_modifier` on the same
  modifier**. That is the correct clean-up shape — the modifier a previous call
  applied is gone before its variable is. A branch that removes the variable
  *without* dropping the modifier is still flagged, because the modifier applied
  on an earlier call outlives the branch choice.
* Block-form `multiplier = { … }` arithmetic is out of scope (see the separate
  best-practices bullet advising against it).

Why a raw-text scan instead of `paradox_file_parser`
----------------------------------------------------
The rule is about *source order within one block*, and the parser cannot answer
that: it folds repeated keys (several `add_modifier` / `remove_variable`
statements in one effect are exactly that shape) into one list stored at the
first occurrence, and the tokenizer drops line numbers and comments, so there
would be nothing to report or to hang a `# REVIEWED YYYY-MM-DD:` suppression
comment on. This audit blanks comments and string bodies in place (offsets and
therefore line numbers preserved), then brace-walks the raw text.

Suppress a deliberate case with a trailing `# REVIEWED YYYY-MM-DD: rationale`
comment on either the `multiplier = …` line or the `remove_variable` line.
"""
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

# Directories scanned, relative to the mod root (issue #250).
AUDIT_DIRS = (
    os.path.join("common", "scripted_effects"),
    os.path.join("common", "on_actions"),
    os.path.join("common", "journal_entries"),
    os.path.join("common", "scripted_buttons"),
    "events",
)

# A modifier with one of these keys expires on its own.
DURATION_KEYS = ("days", "months", "years")

_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)
_OPENER_RE = re.compile(r"(?P<name>[A-Za-z_][\w.:|@$\-]*)\s*(?:\?=|=)\s*\{")
_ADD_MODIFIER_RE = re.compile(r"\badd_modifier\s*=\s*\{")
_MULTIPLIER_RE = re.compile(r"\bmultiplier\s*=\s*(?P<value>[^\s{}]+)")
_MODIFIER_NAME_RE = re.compile(r"\bname\s*=\s*(?P<name>[^\s{}]+)")
_DURATION_RE = re.compile(r"\b(?:" + "|".join(DURATION_KEYS) + r")\s*=")
# `var:X`, `owner.var:X`, `scope:s.var:X`, `local_var:X`, …
_VAR_REF_RE = re.compile(r"(?:^|[.:])(?P<kind>local_var|var):(?P<name>[A-Za-z_$][\w$]*)$")
_REMOVE_RE = re.compile(
    r"\bremove_(?P<kind>local_variable|variable)\s*=\s*(?P<name>[A-Za-z_$][\w$]*)"
)


@dataclass
class Flag:
    file: str
    add_line: int  # line of the `multiplier = var:X`
    remove_line: int  # line of the later `remove_variable = X`
    variable: str
    multiplier: str  # the multiplier token as written
    modifier_name: str  # `name =` inside the add_modifier block ("?" if absent)
    block: str  # top-level block the pair lives in
    block_line: int
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


def blank_comments_and_strings(text: str) -> tuple[str, dict[int, str]]:
    """Return (clean_text, comments_by_line).

    `clean_text` is the same length as `text` — comment bodies and quoted
    string bodies become spaces — so offsets still map to real line numbers.
    """
    out = list(text)
    comments: dict[int, str] = {}
    line = 1
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            in_string = False
            i += 1
            continue
        if in_string:
            if ch == '"':
                in_string = False
            else:
                out[i] = " "
            i += 1
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue
        if ch == "#":
            end = text.find("\n", i)
            if end < 0:
                end = n
            comments[line] = text[i:end]
            for j in range(i, end):
                out[j] = " "
            i = end
            continue
        i += 1
    return "".join(out), comments


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _line_of(pos: int, starts: list[int]) -> int:
    return bisect_right(starts, pos)


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


@dataclass(frozen=True)
class _Block:
    """One braced block in the cleaned text."""
    start: int  # index of `{`
    end: int  # index just past the matching `}`
    name: str  # key that opened it ("?" when the key is not a plain word)
    line: int
    depth: int  # 0 == top-level entity


def _blocks(clean: str, starts: list[int]) -> list[_Block]:
    """Every braced block in the file, ordered by position."""
    openers = {}
    for m in _OPENER_RE.finditer(clean):
        openers[m.end() - 1] = (m.group("name"), _line_of(m.start("name"), starts))

    blocks: list[_Block] = []
    stack: list[tuple[int, str, int, int]] = []
    for m in re.finditer(r"[{}]", clean):
        if m.group() == "{":
            name, line = openers.get(m.start(), ("?", _line_of(m.start(), starts)))
            stack.append((m.start(), name, line, len(stack)))
        elif stack:
            b_start, name, line, depth = stack.pop()
            blocks.append(_Block(b_start, m.end(), name, line, depth))
    blocks.sort(key=lambda b: b.start)
    return blocks


def _ancestors(pos: int, blocks: list[_Block]) -> list[_Block]:
    """Blocks enclosing `pos`, outermost first."""
    return [b for b in blocks if b.start <= pos < b.end]


def _exclusive_branch(add_pos: int, rem_pos: int, blocks: list[_Block]) -> _Block | None:
    """The block holding `rem_pos` when the two positions sit in mutually
    exclusive branches of one alternation; else None.

    Alternations recognised: `if` vs `else` / `else_if`, two `option` blocks of
    one event, and any two children of a `random_list` / `switch`.
    """
    parent_name = None
    for ba, br in zip(_ancestors(add_pos, blocks), _ancestors(rem_pos, blocks)):
        if ba == br:
            parent_name = ba.name
            continue
        names = {ba.name, br.name}
        if names & {"else", "else_if"} or names == {"option"}:
            return br
        if parent_name in ("random_list", "switch"):
            return br
        return None
    return None


def _branch_drops_modifier(
    clean: str, branch_start: int, rem_pos: int, modifier_name: str
) -> bool:
    """True if `remove_modifier = <modifier_name>` appears in this branch before
    the variable removal — i.e. no live modifier is left reading the variable."""
    if modifier_name == "?":
        return False
    pattern = re.compile(
        r"\bremove_modifier\s*=\s*" + re.escape(modifier_name) + r"\b"
    )
    return pattern.search(clean, branch_start, rem_pos) is not None


@dataclass(frozen=True)
class _Add:
    """A permanent `add_modifier` whose multiplier reads a variable."""
    pos: int  # offset of the `multiplier = …` match
    line: int
    kind: str  # "var" or "local_var"
    variable: str
    multiplier: str  # the token as written, e.g. `owner.var:x`
    modifier_name: str


def _variable_scaled_modifiers(clean: str, block: _Block, starts: list[int],
                               by_start: dict[int, _Block]) -> list[_Add]:
    """Permanent `add_modifier` blocks inside `block` scaled by a variable."""
    adds: list[_Add] = []
    for m in _ADD_MODIFIER_RE.finditer(clean, block.start, block.end):
        body = by_start.get(clean.index("{", m.start()))
        if body is None:
            continue
        if _DURATION_RE.search(clean, body.start, body.end):
            continue  # timed modifier — out of scope
        mult = _MULTIPLIER_RE.search(clean, body.start, body.end)
        if not mult:
            continue
        ref = _VAR_REF_RE.search(mult.group("value"))
        if not ref:
            continue
        name_m = _MODIFIER_NAME_RE.search(clean, body.start, body.end)
        adds.append(_Add(
            pos=mult.start(),
            line=_line_of(mult.start(), starts),
            kind=ref.group("kind"),
            variable=ref.group("name"),
            multiplier=mult.group("value"),
            modifier_name=name_m.group("name") if name_m else "?",
        ))
    return adds


def scan_text(text: str, rel_path: str) -> list[Flag]:
    """Scan one file's raw text for permanent multiplier-variable removals."""
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    blocks = _blocks(clean, starts)
    by_start = {b.start: b for b in blocks}
    flags: list[Flag] = []

    for top in [b for b in blocks if b.depth == 0]:
        adds = _variable_scaled_modifiers(clean, top, starts, by_start)
        if not adds:
            continue

        for rm in _REMOVE_RE.finditer(clean, top.start, top.end):
            kind = "local_var" if rm.group("kind") == "local_variable" else "var"
            rm_line = _line_of(rm.start(), starts)
            for add in adds:
                if add.kind != kind or add.variable != rm.group("name"):
                    continue
                if rm.start() <= add.pos:
                    continue  # removed before the modifier was applied — fine
                branch = _exclusive_branch(add.pos, rm.start(), blocks)
                if branch is not None and _branch_drops_modifier(
                    clean, branch.start, rm.start(), add.modifier_name
                ):
                    # Different branch of the same alternation AND that branch
                    # takes the modifier down first, so nothing live is left
                    # reading the variable (the `update_intel_sharing_defense`
                    # "no pact any more — clean up" shape).
                    continue
                flags.append(Flag(
                    file=rel_path,
                    add_line=add.line,
                    remove_line=rm_line,
                    variable=add.variable,
                    multiplier=add.multiplier,
                    modifier_name=add.modifier_name,
                    block=top.name,
                    block_line=top.line,
                    exemption=(_parse_reviewed(comments.get(add.line))
                               or _parse_reviewed(comments.get(rm_line))),
                ))

    return flags


def scan_file(filepath: str, rel_path: str) -> list[Flag]:
    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    return scan_text(text, rel_path)


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    flags: list[Flag] = []
    files_audited = 0
    for sub in AUDIT_DIRS:
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, files in os.walk(root_dir):
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                rel_p = os.path.relpath(abs_p, mod_path)
                files_audited += 1
                flags.extend(scan_file(abs_p, rel_p))

    return AuditResult(flags=flags, files_audited=files_audited)


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# `add_modifier` multiplier-variable persistence audit report",
        "",
        "Auto-generated by `modifier_multiplier_var_audit.py` on every",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a permanent `add_modifier = { … multiplier = var:X }` (no",
        "`days` / `months` / `years`) followed, later in the same top-level",
        "block, by `remove_variable = X`. The engine re-evaluates the stored",
        "multiplier expression on later ticks, so a removed variable makes every",
        "re-evaluation read `'none'` (`jomini_scriptvalue.cpp` spam, modifier",
        "scaling silently lost).",
        "",
        "Fix: leave the variable set — it can be overwritten by the next",
        "`set_variable` — or copy it to a persistent name and point the",
        "multiplier at the copy.",
        "",
        "Suppress a deliberate case with a trailing comment on the",
        "`multiplier = …` line or the `remove_variable` line:",
        "`remove_variable = X # REVIEWED YYYY-MM-DD: why`",
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
            out.append(f"### `{fname}`")
            out.append("")
            for f in by_file[fname]:
                out.append(
                    f"- `{f.block}` (line {f.block_line}): `{f.modifier_name}` "
                    f"applied at line {f.add_line} with `multiplier = "
                    f"{f.multiplier}`, but `{f.variable}` is removed at line "
                    f"{f.remove_line}"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.add_line}` — `{f.multiplier}` removed at line "
                f"{f.remove_line} — **{f.exemption['date']}**: "
                f"{f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- files audited: {result.files_audited}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(
        mod_path, "docs", "engine", "modifier_multiplier_var_report.md"
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "files_audited": result.files_audited,
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    print(render_report(result))
    # --strict: CI mode. Exit 1 if any flag lacks a `# REVIEWED ...` exemption.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in result.flags) else 0)
