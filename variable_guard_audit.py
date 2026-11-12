"""Audit for a `has_variable` guard that shares a `NOT`, `NAND` or `NOR` with
the read it is meant to guard.

A trigger that reads `var:X` when X is not set logs `Failed to fetch variable`
and gives an answer nobody chose. The usual guard is `has_variable = X` beside
the read, and inside a negating block that guard protects nothing::

    NOT = {
        has_variable = te_seabed_lease_n_$B$
        var:te_seabed_lease_n_$B$ > 0
    }

On 2026-10-18 this block logged `Failed to fetch variable` on a first lease
(#1052): a multi-child `NOT` reads every child. Whether `NOT` is NAND or NOR,
and whether `NAND` and `NOR` stop at the child that settles them, is untested
(`event te_debug_engine.1` asks). Read as NOR, the block is also wrong when X
is set and the comparison fails, which is engine-silent: a kept 0 turned a
re-lease away. So a guard and its read never share one of these blocks
(`docs/guides/scripting_best_practices.md` § "Write `NOR` or `NAND`, Never a
Multi-Child `NOT`"; issue #1053).

What is flagged
---------------
A `NOT` / `NAND` / `NOR` block with a direct child `has_variable = X`
(`has_global_variable`, `has_local_variable`) and, anywhere else inside the
block, a bare read of the same variable: `var:X` (`global_var:X`,
`local_var:X`) on either side of a comparison, as a value, or as a scope. The
read may sit a level or more down (`NOT = { has_variable = X  AND = { var:X >
0  … } }`): the guard is still the block's own child and still evaluated beside
it.

What is not
-----------
* A read written `var:X ?= …`, which is false when X is unset and logs nothing.
* A read inside a block that guards it itself: a nested block with its own
  `has_variable = X` child (judged on its own if it is a `NOT`/`NAND`/`NOR`;
  an `OR` guards nothing and is not counted), or a `trigger_if` /
  `trigger_else_if` / `if` / `else_if` whose `limit` names the guard.
* A negating block that already sits inside such a `trigger_if` (the read is
  guarded from outside; the inner guard is only redundant), unless a scope
  change lies between the two: that limit tested another object's variable.
* A read of `var:X` behind a scope change (`owner = { var:X > 0 }`): that is
  another object's variable, which the guard never covered. Global and local
  variables have no scope, so those reads count at any depth.
* A guard and a read that are siblings in an `AND` or at the top level of a
  trigger. That is the mod's ordinary idiom (thousands of sites), and the guide
  warns about it only where a tooltip lays the trigger out line by line, which
  no static scan can see.

The fix
-------
Move the guard into a limit and keep the rest of the block inside the
negation: `trigger_if = { limit = { has_variable = X } NOT = { var:X > 0 } }`
(`NAND = { … }` when more than one condition is left), which passes when X is
unset. Where every read is an equality with a number, `var:X ?= N` with no
guard also does, the block's other conditions staying where they are: `?=` is
false when X is unset. Both mean the same under every reading of the engine.
`?=` is offered for a number only: with a `var:` or a `flag:` on the right it
is unverified (`scripting_best_practices.md` § "Triggered Option Names").
Suppress a block that is deliberately left with a trailing
`# REVIEWED YYYY-MM-DD (variable_guard): rationale` on its opening line.

Known gaps (none occurs in the mod as of 2026-11-12)
----------------------------------------------------
* `root.var:X`, `prev.var:X`, `root = { var:X > 0 }`: skipped as another
  object's variable even where `root` is the scope the guard ran in, which a
  text scan cannot know.
* A guard whose name is quoted (`has_variable = "x"`): string bodies are
  blanked before the scan, so the name is not seen.
* A guard or a read that arrives through a scripted trigger call or a `$X$`
  argument: only what the file's text spells out is compared.

A raw-text scan, like `iterator_limit_audit` and for its reasons: the parser
keeps neither line numbers nor comments, and folds repeated keys. It walks
every character of `common/` and `events/` (about 40 MB), so it takes several
seconds (7 to 10 s on a loaded 4-core machine), like `prev_scope_audit`.
"""
from __future__ import annotations

import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field

from iterator_limit_audit import blank_comments_and_strings

CHECK = "variable_guard"

# Directories scanned, relative to the mod root: every scripted surface.
AUDIT_DIRS = ("common", "events")

# Scope-link catalog, generated from the engine's event_targets.log.
EVENT_TARGETS = os.path.join("docs", "engine", "event_targets_summary.txt")

NEGATING_KEYS = {"NOT", "NAND", "NOR"}

# guard trigger -> the prefix its variable is read with.
GUARD_KEYS = {
    "has_variable": "var",
    "has_global_variable": "global_var",
    "has_local_variable": "local_var",
}

_ANY_GUARD_RE = re.compile(r"\bhas_(?:global_|local_)?variable\b")

# Blocks whose `limit` gates the rest of the block.
CONDITIONAL_KEYS = {"trigger_if", "trigger_else_if", "if", "else_if"}

ITERATOR_PREFIXES = ("every_", "random_", "ordered_", "any_")
NON_ITERATOR_KEYS = {"random_list"}

_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)

_WORD = r"""[^\s={}<>!?#"]+"""
# One pass over the cleaned text: a closing brace, `key <op> {`, `key <op>
# value`, an unattributed `{`, or a bare token (a list item).
_TOKEN_RE = re.compile(
    r"(?P<close>\})"
    rf"|(?P<key>{_WORD})\s*(?P<op>\?=|[!<>=]=|[=<>])\s*"
    rf"(?:(?P<open>\{{)|(?P<value>{_WORD}|\"[^\"\n]*\"))"
    r"|(?P<anon>\{)"
    rf"|(?P<bare>{_WORD})"
)

# A variable read at the head of a token (`this.` is the current scope).
# `scope:x.var:y` and `owner.var:y` read another object's variable, so only
# global and local reads count deeper in a chain.
_HEAD_READ_RE = re.compile(r"^(?:this\.)?(var|global_var|local_var):([A-Za-z0-9_$\-]+)", re.I)
# The right side `?=` is known to take: a plain number.
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
_CHAIN_READ_RE = re.compile(r"[.(|](global_var|local_var):([A-Za-z0-9_$\-]+)")


@dataclass
class Node:
    """A `key <op> {` block, with its statements in source order."""
    key: str | None
    op: str | None
    line: int
    parent: "Node | None" = None
    # ("scalar", key, op, value, line) | ("block", Node) | ("bare", token, line)
    children: list[tuple] = field(default_factory=list)


@dataclass
class Read:
    line: int
    text: str  # the statement as written, for the report
    equality: bool  # `var:X = <number>`: the `?=` rewrite fits


@dataclass
class Flag:
    file: str
    line: int  # opening line of the NOT / NAND / NOR
    block: str  # "NOT", "NAND" or "NOR"
    guard: str  # e.g. "has_variable = x"
    guard_line: int
    variable: str  # e.g. "var:x"
    reads: list[Read] = field(default_factory=list)
    exemption: dict | None = None

    @property
    def suggestion(self) -> str:
        wrapped = (
            "move the guard into a limit and keep the rest of the block inside the negation: "
            f"`trigger_if = {{ limit = {{ {self.guard} }} NAND = {{ <the block's other conditions> }} }}` "
            "(`NOT` if one condition is left; passes when unset)"
        )
        if self.block == "NOR":
            return ("as `NOR` this is false whenever the variable is set, so the read can only "
                    "matter when it is unset: decide what was meant. For \"not (set and …)\", "
                    + wrapped)
        if all(r.equality for r in self.reads):
            return (f"read it as `{self.variable} ?= <number>` and drop the guard, leaving the "
                    f"block's other conditions where they are (false when unset), or {wrapped}")
        return wrapped


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    files_audited: int = 0


def load_scope_links(mod_path: str) -> set[str]:
    """Names of the engine's scope links that move to another object (every
    link but the ones that yield a value); empty if the catalog is absent, and
    the audit then knows iterators and named scopes only."""
    path = os.path.join(mod_path, EVENT_TARGETS)
    links: set[str] = set()
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#") or "|" not in line:
                    continue
                parts = line.split("|")
                if len(parts) < 3:
                    continue
                name, output = parts[1].strip(), parts[2].strip()
                if name and output != "value":
                    links.add(name)
    except OSError:
        pass
    return links


def _is_scope_change(key: str | None, links: set[str]) -> bool:
    if not key or key in NON_ITERATOR_KEYS:
        return False
    if key.startswith(ITERATOR_PREFIXES):
        return True
    low = key.lower()
    if low == "this":
        return False
    if low in ("root", "prev"):
        return True
    if ":" in key or "." in key:
        return True
    return low in links


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _TAGGED_REVIEWED_RE.search(comment)
    if not m:
        return None
    checks = {c.strip() for c in m.group("checks").split(",")}
    if CHECK not in checks:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _reads_in(token: str | None, scoped: bool) -> list[tuple[str, str]]:
    """(prefix, name) of each variable `token` reads. `scoped` is False behind
    a scope change, where a `var:` read is another object's."""
    if not token:
        return []
    found: list[tuple[str, str]] = []
    m = _HEAD_READ_RE.match(token)
    if m and (scoped or m.group(1).lower() != "var"):
        found.append((m.group(1).lower(), m.group(2)))
    found.extend((c.group(1), c.group(2))
                 for c in _CHAIN_READ_RE.finditer(token, m.end() if m else 0))
    return found


def parse_tree(clean: str) -> Node:
    """The file as a tree of blocks; `clean` has comments and strings blanked."""
    starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]

    def line_of(pos: int) -> int:
        return bisect_right(starts, pos)

    root = Node(None, None, 0)
    cur = root
    for m in _TOKEN_RE.finditer(clean):
        kind = m.lastgroup  # the alternative's last named group that matched
        if kind == "close":
            if cur.parent is not None:
                cur = cur.parent
        elif kind == "anon":
            node = Node(None, None, line_of(m.start()), parent=cur)
            cur.children.append(("block", node))
            cur = node
        elif kind == "bare":
            cur.children.append(("bare", m.group("bare"), line_of(m.start())))
        elif kind == "open":
            node = Node(m.group("key"), m.group("op"), line_of(m.start()), parent=cur)
            cur.children.append(("block", node))
            cur = node
        else:
            cur.children.append(
                ("scalar", m.group("key"), m.group("op"), m.group("value"), line_of(m.start())))
    return root


def _direct_guards(node: Node) -> dict[tuple[str, str], int]:
    """{(prefix, name): line} for the block's own `has_variable = X` children."""
    guards: dict[tuple[str, str], int] = {}
    for child in node.children:
        if child[0] != "scalar":
            continue
        _, key, op, value, line = child
        prefix = GUARD_KEYS.get(key)
        if prefix and op == "=" and value:
            guards.setdefault((prefix, value), line)
    return guards


def _limit_guards(node: Node) -> set[tuple[str, str]]:
    """Variables a `trigger_if`-like block's `limit` guards for its body."""
    guards: set[tuple[str, str]] = set()
    if node.key not in CONDITIONAL_KEYS:
        return guards
    for child in node.children:
        if child[0] == "block" and child[1].key == "limit":
            guards.update(_direct_guards(child[1]))
    return guards


def _collect_reads(node: Node, var: tuple[str, str], links: set[str],
                   scoped: bool, out: list[Read]) -> None:
    for child in node.children:
        kind = child[0]
        if kind == "bare":
            if var in _reads_in(child[1], scoped):
                out.append(Read(child[2], child[1], False))
        elif kind == "scalar":
            _, key, op, value, line = child
            text = f"{key} {op} {value}"
            if op != "?=" and var in _reads_in(key, scoped):
                out.append(Read(
                    line, text, op == "=" and bool(_NUMBER_RE.fullmatch(value or ""))))
            if var in _reads_in(value, scoped):
                out.append(Read(line, text, False))
        else:
            sub = child[1]
            if sub.op != "?=" and var in _reads_in(sub.key, scoped):
                out.append(Read(sub.line, f"{sub.key} {sub.op} {{ … }}", False))
            regards = var in _direct_guards(sub) and (sub.key or "").upper() != "OR"
            if regards or var in _limit_guards(sub):
                continue  # guarded again further in; judged there
            _collect_reads(
                sub, var, links,
                scoped and not _is_scope_change(sub.key, links), out,
            )


def _guarded_from_outside(node: Node, var: tuple[str, str], links: set[str]) -> bool:
    """True when an enclosing `trigger_if`-like block's limit guards `var` and
    `node` sits in that block's body, not in the limit itself. For a `var:`,
    the search stops at a scope change: a limit above it tested another
    object's variable."""
    below = node
    cur = node.parent
    while cur is not None:
        if below.key != "limit" and var in _limit_guards(cur):
            return True
        if var[0] == "var" and _is_scope_change(cur.key, links):
            return False
        below, cur = cur, cur.parent
    return False


def scan_text(text: str, rel_path: str, links: set[str] | None = None) -> list[Flag]:
    """Scan one file's raw text; one flag per negating block and variable."""
    links = links or set()
    # No guard, no flag: most files stop here, before the character walk.
    if not _ANY_GUARD_RE.search(text):
        return []
    clean, comments = blank_comments_and_strings(text)
    root = parse_tree(clean)
    flags: list[Flag] = []

    def visit(node: Node) -> None:
        if node.key is not None and node.key.upper() in NEGATING_KEYS:
            for var, guard_line in _direct_guards(node).items():
                reads: list[Read] = []
                _collect_reads(node, var, links, True, reads)
                if not reads or _guarded_from_outside(node, var, links):
                    continue
                guard_key = next(k for k, p in GUARD_KEYS.items() if p == var[0])
                flags.append(Flag(
                    file=rel_path,
                    line=node.line,
                    block=node.key.upper(),
                    guard=f"{guard_key} = {var[1]}",
                    guard_line=guard_line,
                    variable=f"{var[0]}:{var[1]}",
                    reads=reads,
                    exemption=_parse_reviewed(comments.get(node.line)),
                ))
        for child in node.children:
            if child[0] == "block":
                visit(child[1])

    visit(root)
    flags.sort(key=lambda f: (f.line, f.variable))
    return flags


def scan_file(filepath: str, rel_path: str, links: set[str] | None = None) -> list[Flag]:
    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    return scan_text(text, rel_path, links)


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_AUDITS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    links = load_scope_links(mod_path)
    flags: list[Flag] = []
    files_audited = 0
    for sub in AUDIT_DIRS:
        root_dir = os.path.join(mod_path, sub)
        if not os.path.isdir(root_dir):
            continue
        for root, dirs, files in os.walk(root_dir):
            dirs.sort()
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                rel_p = os.path.relpath(abs_p, mod_path).replace(os.sep, "/")
                files_audited += 1
                flags.extend(scan_file(abs_p, rel_p, links))

    return AuditResult(flags=flags, files_audited=files_audited)


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Variable guard audit report",
        "",
        "Auto-generated by `variable_guard_audit.py` on every `POST /reload`",
        "of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a `NOT`, `NAND` or `NOR` block that holds a `has_variable = X`",
        "guard (or the global or local form) as a direct child and a bare read",
        "of the same variable elsewhere inside it. A multi-child `NOT` reads",
        "every child, so the guard protects nothing: an unset X logs `Failed to",
        "fetch variable`. Whether `NAND` and `NOR` stop early is untested, and",
        "read as NOR a multi-child `NOT` also gives the wrong answer when X is",
        "set (`docs/guides/scripting_best_practices.md` § \"Write `NOR` or",
        "`NAND`, Never a Multi-Child `NOT`\").",
        "",
        "Fix: move the guard into a limit and keep the rest of the block inside",
        "the negation, `trigger_if = { limit = { has_variable = X }",
        "NOT = { var:X > 0 } }`, which passes when X is unset. Where every read",
        "is an equality with a number, `var:X ?= N` with no guard also does",
        "(false when X is unset; unverified with a `var:` or a `flag:` on the",
        "right). Both mean the same under every reading of the engine.",
        "",
        "Suppress a block that is deliberately left with a trailing comment on",
        "its opening line:",
        f"`NAND = {{ # REVIEWED YYYY-MM-DD ({CHECK}): why`",
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
                reads = ", ".join(
                    f"`{r.text}` (line {r.line})" for r in f.reads
                )
                out.append(
                    f"- line {f.line}: `{f.block}` holds `{f.guard}` beside "
                    f"{reads}. Fix: {f.suggestion}"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        # No line number on a reviewed entry: an edit above it would
        # otherwise churn the report.
        for f in exemp:
            out.append(
                f"- `{f.file}` — `{f.block}` with `{f.guard}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    # Flag counts only: `files_audited` stays on the result (and in the
    # regenerate() summary) but moves with every new file.
    out.append("## Coverage")
    out.append("")
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
    out_path = os.path.join(mod_path, "docs", "engine", "variable_guard_report.md")
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
