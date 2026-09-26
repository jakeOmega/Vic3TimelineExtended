"""Audit for script that runs and does nothing: empty effect blocks and event
options with no effect.

Two checks, both engine-silent:

`empty_block` — a block whose body can never do anything:

- an `if` / `else_if` (or `trigger_if` / `trigger_else_if`) holding only its
  `limit`, when it **ends its chain** — no `else_if` / `else` follows it;
- an `else` (or `trigger_else`) with an empty body;
- an `every_*` / `random_*` / `ordered_*` iterator holding only iteration
  properties (`limit`, `order_by`, `max`, …);
- `hidden_effect`, `show_as_tooltip`, `while` or `random` with nothing to run.

An empty branch *inside* a chain is not flagged: it claims its case, so the
branches after it do not fire (`else_if = { limit = { var:x < 60 } } # Stable
= no modifier` in `banking_cycle_effects.txt`). Only the last link of a chain
can be removed without changing what the chain does.

`no_effect_option` — an option of a visible mod event that executes nothing
(its content is only option metadata, a `custom_tooltip` line, a
`show_as_tooltip` preview or empty blocks) while another option of the same
event does execute something. A pure notification whose options are all
flavour is not flagged, nor is anything in the console-only `te_debug_*` files.
Deliberate declines ("Say nothing for now") are the common case and carry a
tag; the check exists to catch the option a refactor emptied.

Found 2026-09-26 in `space_race_events.20.a` ("We must not fall behind."). The
space-race rework (418d06ec) split the shared `sr_milestone_progress` variable
into per-milestone ones and deleted the option's `+3` instead of moving it,
leaving `if = { limit = { has_variable = sr_active_milestone } }` with nothing
inside: a player picking it got nothing for six months, and no audit noticed.

Calibration. Run against vanilla, the `empty_block` rule's hits are genuine
dead code (an `if` meant to wrap `add_trait = scarred` in
`tibetan_expedition.txt`; an empty `every_diplomatically_relevant_country`
that leaves a progress bar's `add = 0.3` unconditional), plus one deliberate
case ("#Removes errors about unused variable."). `NON_ITERATOR_KEYS` was
derived by diffing every `every_/random_/ordered_` block key used in vanilla
and the mod against the engine effect list (`docs/engine/effects_summary.txt`).

Raw text, not `paradox_file_parser`: the parser folds repeated keys and drops
order and line numbers, and both checks need source order (what follows an
`if`) and lines to hang a suppression on. Comments and strings are blanked with
`iterator_limit_audit.blank_comments_and_strings`, so line numbers stay exact.
A block whose own text holds a `$PARAM$` or a `[[PARAM]` guard is never empty:
the parameter may expand to anything.

Suppression is check-tagged, so no other audit's `# REVIEWED` regex reads it:

    # REVIEWED 2026-09-26 (empty_block): rationale
    # REVIEWED 2026-09-26 (no_effect_option): rationale

`empty_block` takes the tag on the block's opener line or any line inside it;
`no_effect_option` anywhere inside the option. A tag that suppresses nothing is
stale and fails `--strict` until it is removed. Both check names are listed in
`event_context_audit.FOREIGN_CHECKS`, which reads every tag inside an event.

Report: docs/engine/empty_effect_report.md. Registered in POST_LOAD_AUDITS.
"""
import os
import re
from dataclasses import dataclass, field

from iterator_limit_audit import (
    ITERATOR_PROPERTY_KEYS,
    SCALAR_ITERATOR_PROPERTY_KEYS,
    _line_of,
    _line_starts,
    blank_comments_and_strings,
)

CHECK_BLOCK = "empty_block"
CHECK_OPTION = "no_effect_option"
CHECKS = (CHECK_BLOCK, CHECK_OPTION)

# Directories scanned for empty blocks, relative to the mod root. Every `.txt`
# below them: script values and scripted triggers carry `if` chains too.
AUDIT_DIRS = ("common", "events")
EVENTS_DIR = "events"

_CONDITIONALS = {"if", "else_if", "else", "trigger_if", "trigger_else_if", "trigger_else"}
_ELSE_KEYS = {"else", "trigger_else"}
# What may follow a conditional and keep it part of the same chain.
_CHAIN_NEXT = {
    "if": {"else_if", "else"},
    "else_if": {"else_if", "else"},
    "trigger_if": {"trigger_else_if", "trigger_else"},
    "trigger_else_if": {"trigger_else_if", "trigger_else"},
}
ITERATOR_PREFIXES = ("every_", "random_", "ordered_")
# Keys with an iterator prefix that are not iterators: `random_list` and
# `random_events` hold weights, `random_range` is a value.
NON_ITERATOR_KEYS = {"random_list", "random_events", "random_range"}

# Keys that give a block no content of its own, per kind of block.
_NON_CONTENT = {
    "hidden_effect": frozenset(),
    "show_as_tooltip": frozenset(),
    "while": frozenset({"limit", "count"}),
    "random": frozenset({"chance", "modifier"}),
}

# An event option's own settings: they configure the button, not the outcome.
OPTION_META_KEYS = {
    "name", "default_option", "highlighted_option", "fallback", "trigger",
    "ai_chance", "show_as_unavailable",
}
# Shown, never executed.
_DISPLAY_ONLY_KEYS = {"custom_tooltip", "custom_description", "show_as_tooltip"}

_EVENT_ID_RE = re.compile(r"^[A-Za-z_][\w]*\.\d+$")
_CONSOLE_FILE_RE = re.compile(r"^te_debug_")
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)
# A closing brace, a `key <op> {` opener, a `key <op> value` statement (the
# value consumed, so it is never re-read as a key), or an unattributed `{`
# (`50 = {` inside a random_list).
_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    r"|(?P<key>[A-Za-z_$][A-Za-z0-9_.:|@$\-]*)\s*(?:\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[^\s{}]+))?"
    r"|(?P<anon>\{)"
)


@dataclass
class Node:
    key: str | None  # None for an unattributed `{`
    line: int
    end_line: int = 0
    is_block: bool = False
    value: str | None = None
    children: list["Node"] = field(default_factory=list)
    param: bool = False  # own text holds `$PARAM$` / `[[PARAM]`
    dead: bool = False  # set by _mark_dead


@dataclass
class BlockFlag:
    file: str
    line: int
    key: str
    reason: str  # "chain-end" | "else" | "wrapper"
    exemption: dict | None = None


@dataclass
class OptionFlag:
    file: str
    line: int
    event_id: str
    option: str
    exemption: dict | None = None


@dataclass
class StaleTag:
    file: str
    line: int
    check: str


@dataclass
class AuditResult:
    block_flags: list[BlockFlag] = field(default_factory=list)
    option_flags: list[OptionFlag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    files_audited: int = 0
    events_scanned: int = 0
    options_scanned: int = 0

    @property
    def failing(self) -> int:
        return (
            sum(1 for f in self.block_flags if not f.exemption)
            + sum(1 for f in self.option_flags if not f.exemption)
            + len(self.stale_tags)
        )


def parse_tree(text: str) -> tuple[list[Node], dict[int, str]]:
    """Top-level nodes of one file, plus its comments by line."""
    clean, comments = blank_comments_and_strings(text)
    starts = _line_starts(clean)
    root = Node(key=None, line=0, is_block=True)
    stack: list[tuple[Node, int, list[tuple[int, int]]]] = [(root, 0, [])]

    for m in _TOKEN_RE.finditer(clean):
        node, body_start, spans = stack[-1]
        if m.group("close"):
            if len(stack) == 1:
                continue
            stack.pop()
            node.end_line = _line_of(m.start(), starts)
            own = list(clean[body_start:m.start()])
            for a, b in spans:
                own[a - body_start:b - body_start] = " " * (b - a)
            own_text = "".join(own)
            node.param = "$" in own_text or "[[" in own_text
            stack[-1][2].append((body_start - 1, m.end()))
            continue
        if m.group("anon"):
            child = Node(key=None, line=_line_of(m.start(), starts), is_block=True)
            node.children.append(child)
            stack.append((child, m.end(), []))
            continue
        child = Node(key=m.group("key"), line=_line_of(m.start("key"), starts))
        node.children.append(child)
        if m.group("open"):
            child.is_block = True
            stack.append((child, m.end(), []))
        else:
            child.value = m.group("value")
            if m.group("value"):
                # The statement's text is not the enclosing block's own text
                # when it comes to `$PARAM$`: a parameterised value is content
                # anyway, and scanning it again would only repeat that.
                spans.append((m.start(), m.end()))
    return root.children, comments


def _is_iterator(key: str | None) -> bool:
    return bool(key and key not in NON_ITERATOR_KEYS and key.startswith(ITERATOR_PREFIXES))


def _non_content_keys(key: str | None) -> frozenset | None:
    """Keys that give a block of this kind no content, or None when the block
    is not one this audit judges (a scope switch, an effect's argument block)."""
    if key in _CONDITIONALS:
        return frozenset({"limit"})
    if key in _NON_CONTENT:
        return _NON_CONTENT[key]
    if _is_iterator(key):
        return frozenset(ITERATOR_PROPERTY_KEYS)
    return None


def _has_content(node: Node, non_content: frozenset) -> bool:
    if node.param:
        return True
    for c in node.children:
        if c.dead:
            continue
        if c.key in non_content:
            continue
        if c.key in SCALAR_ITERATOR_PROPERTY_KEYS and not c.is_block and _is_iterator(node.key):
            continue
        return True
    return False


def _mark_dead(nodes: list[Node], rel: str, out: list[tuple[Node, str]]) -> None:
    """Depth first: mark every judged block that can do nothing, and record
    the ones to report. A mid-chain empty conditional is inert but not
    reported; it is load-bearing for the branches after it. A dead block
    whose only content was dead children is reported alone: one flag, one
    fix."""
    for i, n in enumerate(nodes):
        if not n.is_block:
            continue
        _mark_dead(n.children, rel, out)
        nc = _non_content_keys(n.key)
        if nc is None or _has_content(n, nc):
            continue
        if n.key in _ELSE_KEYS:
            reason = "else"
        elif n.key in _CHAIN_NEXT:
            nxt = nodes[i + 1].key if i + 1 < len(nodes) else None
            if nxt in _CHAIN_NEXT[n.key]:
                continue
            reason = "chain-end"
        else:
            reason = "wrapper"
        n.dead = True
        inner = {id(c) for c in n.children if c.dead}
        out[:] = [(d, r) for d, r in out if id(d) not in inner]
        out.append((n, reason))


def executes(node: Node) -> bool:
    """Does this statement change anything when it runs?"""
    if node.dead:
        return False
    if not node.is_block:
        return node.key not in _DISPLAY_ONLY_KEYS
    if node.param:
        return True
    if node.key == "show_as_tooltip":
        return False
    if node.key in ("custom_tooltip", "custom_description"):
        return any(executes(c) for c in node.children if c.key not in ("text", "subject", "object"))
    nc = _non_content_keys(node.key)
    if nc is not None:
        return any(executes(c) for c in node.children if c.key not in nc)
    if not node.children:
        # An empty scope switch (`scope:x = { }`) or an argument-less block.
        return False
    return any(executes(c) for c in node.children)


def option_executes(option: Node) -> bool:
    if option.param:
        return True
    return any(executes(c) for c in option.children if c.key not in OPTION_META_KEYS)


def _tag_lines(comments: dict[int, str]) -> dict[int, list[tuple[str, dict]]]:
    """line -> [(check, {"date", "rationale"})] for this audit's checks."""
    out: dict[int, list[tuple[str, dict]]] = {}
    for line, comment in comments.items():
        m = _TAGGED_REVIEWED_RE.search(comment)
        if not m:
            continue
        for chk in re.split(r"[\s,]+", m.group("checks").strip()):
            if chk in CHECKS:
                out.setdefault(line, []).append(
                    (chk, {"date": m.group("date"), "rationale": m.group("rationale").strip()})
                )
    return out


def _find_tag(tags, check: str, first: int, last: int, used: set) -> dict | None:
    for line in range(first, last + 1):
        for chk, info in tags.get(line, ()):
            if chk == check:
                used.add((line, chk))
                return info
    return None


def scan_text(text: str, rel_path: str, *, options: bool = False):
    """Scan one file. Returns (block_flags, option_flags, stale_tags, events,
    options_scanned). `options` enables the event-option check."""
    nodes, comments = parse_tree(text)
    tags = _tag_lines(comments)
    used: set[tuple[int, str]] = set()

    dead: list[tuple[Node, str]] = []
    _mark_dead(nodes, rel_path, dead)
    block_flags = [
        BlockFlag(
            rel_path, n.line, n.key or "{", reason,
            _find_tag(tags, CHECK_BLOCK, n.line, max(n.end_line, n.line), used),
        )
        for n, reason in dead
    ]

    option_flags: list[OptionFlag] = []
    events = options_scanned = 0
    if options:
        for ev in nodes:
            if not (ev.is_block and ev.key and _EVENT_ID_RE.match(ev.key)):
                continue
            if any(c.key == "hidden" and c.value == "yes" for c in ev.children):
                continue
            events += 1
            opts = [c for c in ev.children if c.key == "option" and c.is_block]
            options_scanned += len(opts)
            doing = [option_executes(o) for o in opts]
            if not any(doing):
                continue
            for o, does in zip(opts, doing):
                if does:
                    continue
                name = next((c.value for c in o.children if c.key == "name" and c.value), "?")
                option_flags.append(OptionFlag(
                    rel_path, o.line, ev.key, name,
                    _find_tag(tags, CHECK_OPTION, o.line, o.end_line, used),
                ))

    stale = [
        StaleTag(rel_path, line, chk)
        for line, entries in sorted(tags.items())
        for chk, _info in entries
        if (line, chk) not in used
    ]
    return block_flags, option_flags, stale, events, options_scanned


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    result = AuditResult()
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
                try:
                    with open(abs_p, encoding="utf-8-sig", errors="replace") as fh:
                        text = fh.read()
                except OSError:
                    continue
                in_events = rel_p.split(os.sep)[0] == EVENTS_DIR
                blocks, opts, stale, events, n_opts = scan_text(
                    text, rel_p,
                    options=in_events and not _CONSOLE_FILE_RE.match(fname),
                )
                result.files_audited += 1
                result.block_flags.extend(blocks)
                result.option_flags.extend(opts)
                result.stale_tags.extend(stale)
                result.events_scanned += events
                result.options_scanned += n_opts

    result.block_flags.sort(key=lambda f: (f.file, f.line))
    result.option_flags.sort(key=lambda f: (f.file, f.line))
    result.stale_tags.sort(key=lambda s: (s.file, s.line))
    return result


_REASON_TEXT = {
    "chain-end": "holds only its `limit` and ends its chain",
    "else": "has an empty body",
    "wrapper": "has nothing to run",
}


def render_report(result: AuditResult) -> str:
    unrev_b = [f for f in result.block_flags if not f.exemption]
    unrev_o = [f for f in result.option_flags if not f.exemption]
    exemp_b = [f for f in result.block_flags if f.exemption]
    exemp_o = [f for f in result.option_flags if f.exemption]

    out = [
        "# Empty effect audit report",
        "",
        "Auto-generated by `empty_effect_audit.py` on every `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Two engine-silent ways for script to run and do nothing:",
        "",
        "- `empty_block` — an `if` / `else_if` holding only its `limit` at the",
        "  end of its chain, an empty `else`, or an iterator / `hidden_effect` /",
        "  `while` / `random` with nothing to run. An empty branch *inside* a",
        "  chain is load-bearing (it claims its case) and is not flagged.",
        "- `no_effect_option` — an event option that executes nothing while",
        "  another option of the same event does something.",
        "",
        "Fix the block or option, or suppress a deliberate case with a",
        "check-tagged comment — for a block on its opener line or inside it, for",
        "an option anywhere inside it:",
        "`# REVIEWED YYYY-MM-DD (empty_block): why` /",
        "`# REVIEWED YYYY-MM-DD (no_effect_option): why`.",
        "",
        "## Unreviewed empty blocks",
        "",
    ]
    if not unrev_b:
        out += ["_None._", ""]
    else:
        for f in unrev_b:
            out.append(f"- `{f.file}:{f.line}` — `{f.key}` {_REASON_TEXT[f.reason]}")
        out.append("")

    out += ["## Unreviewed no-effect options", ""]
    if not unrev_o:
        out += ["_None._", ""]
    else:
        for f in unrev_o:
            out.append(f"- `{f.file}:{f.line}` — `{f.event_id}` option `{f.option}`")
        out.append("")

    if result.stale_tags:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        for s in result.stale_tags:
            out.append(f"- `{s.file}:{s.line}` ({s.check})")
        out.append("")

    out += ["## Reviewed exemptions", ""]
    if not exemp_b and not exemp_o:
        out += ["_None._", ""]
    else:
        # No line number on a reviewed entry: an edit above it would otherwise
        # churn the report. An option is named by its id; a block by its key
        # and why it is empty, and by its rationale.
        for f in exemp_b:
            out.append(
                f"- `{f.file}` — `{f.key}` {_REASON_TEXT[f.reason]} (empty_block) — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        for f in exemp_o:
            out.append(
                f"- `{f.file}` — `{f.event_id}` option `{f.option}` "
                f"(no_effect_option) — **{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out += [
        # Flag counts only: the file / event / option counts stay on the
        # result but move with every new event.
        "## Coverage",
        "",
        f"- empty blocks: {len(result.block_flags)} ({len(unrev_b)} unreviewed)",
        f"- no-effect options: {len(result.option_flags)} ({len(unrev_o)} unreviewed)",
        f"- stale tags: {len(result.stale_tags)}",
        "",
    ]
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    out_path = os.path.join(mod_path, "docs", "engine", "empty_effect_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        # Flags without a tag, plus tags that suppress nothing.
        "unreviewed": result.failing,
        "empty_blocks": len(result.block_flags),
        "no_effect_options": len(result.option_flags),
        "stale_tags": len(result.stale_tags),
        "exempted": sum(1 for f in result.block_flags + result.option_flags if f.exemption),
        "path": out_path,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    res = audit(mod_path=mod_path)
    print(render_report(res))
    # --strict: CI mode. Exit 1 if any flag lacks its check-tagged
    # `# REVIEWED` comment, or any such tag suppresses nothing.
    if "--strict" in sys.argv:
        raise SystemExit(1 if res.failing else 0)
