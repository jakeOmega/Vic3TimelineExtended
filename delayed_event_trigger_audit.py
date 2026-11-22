"""Audit the events the mod queues with a delay whose `trigger` may be false
on the day they are queued (#1596).

`trigger_event = { id = X days = N }` (or `months` / `years`) seems to drop
`X` for good, with no log line, if `X`'s `trigger` is false on the day it is
queued, even when it would hold on the day `X` is due
(`docs/guides/scripting_best_practices.md` § "A Delayed `trigger_event`
Re-Checks Its Trigger When It Fires"). Court Overhaul never fired because of
it. The rule is the likely reading of a QA session, not yet a closed fact:
the self-checks `delayed_trigger_queue_check` (judiciary) and
`delayed_trigger_queue_probe` / `delayed_trigger_fire_probe`
(`te_judiciary_events.11`-`.15`, started by `te_jud_dt_probe_start`) settle it
in ordinary play, and whether the trigger is read again on the day the event
is due (`docs/testing/judiciary-playtest.md`).

What is listed
--------------
Every event the mod queues with a delay that has a non-empty top-level
`trigger`. The call sites come from `event_context_audit`'s scan, as
`script_call_graph` reads it, so an id passed to a helper as `$EVENT$` is read
at the caller that names it, and the `te_debug_*` harnesses are read too.
Each target falls in one class:

- `likely_false`: something at a call site says the trigger cannot yet hold.
  `modifier_same_block`: the trigger reads `has_modifier = X` (or its `NOT`)
  and the calling entity adds (removes) `X` before the call, which that
  block cannot see yet. `law_lag`: the trigger reads `modifier:` sums,
  directly or through a mod scripted trigger or script value, and the call
  is made where a law has just changed (a law's file, an on_action run from
  `on_law_activated`, or after an `activate_law` in the same entity): the
  new law is not in `modifier:` reads that day.
- `set_before`: at every call, each condition of the trigger is either
  tested by a `limit` the call sits inside (an `if` or an iterator on the
  way to it, or the calling event's own `trigger` for a call in its
  `immediate`), or is a `has_variable = X` the entity sets before the call
  (a variable is visible at once). Both must be about the scope the event is
  sent to: a block that changes scope on the way to the call starts over,
  a write inside another scope's block does not count, and neither does a
  write that only an earlier `if` makes. A condition that merely appears in
  some earlier block's `limit` proves nothing and is not counted (until
  2026-11-13 it was, and so was a write on another scope). True when queued;
  not flagged.
- `reviewed`: the trigger line carries
  `# REVIEWED YYYY-MM-DD (delayed_trigger): why`. A rationale that starts
  with "cancels" marks a trigger that also stops an event whose premise went
  away during the delay (a dead country, a closed vote): that works only if
  the engine reads the trigger again on the day the event is due, which the
  self-check `delayed_trigger_fire_probe` settles, and the report lists those
  apart.
- `review`: the rest.

`likely_false` and `review` are the flags: `--strict` fails on them, and on a
tag on an event that is no longer a delayed target with a trigger.

The fix for a trigger that waits for something to become true is no
top-level `trigger` and the conditions in `immediate` as
`if = { limit = { ... } }`; for a visible event, a hidden relay with no
trigger that opens it on the day (`te_judiciary_events.7`, `.8`,
`decolonization_events.81`). A review says why the trigger already holds
when queued.

Blind spots: a scope change between an `add_modifier` and the call is not
followed, and a site inside a helper is classed by what its caller runs
before the call, not by what the helper runs first.

Runs on every full `POST /reload` (its unreviewed count joins the reload's
warnings) and in CI with `--strict`; writes
`docs/engine/delayed_event_trigger_report.md`. `python3
delayed_event_trigger_audit.py` prints the report; `--write` writes it.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from audit_common import AuditResult as _AuditResult
from audit_common import cli_main, parse_reviewed, write_text

TAG = "delayed_trigger"
REPORT = os.path.join("docs", "engine", "delayed_event_trigger_report.md")

_TOKEN_RE = re.compile(r'"[^"\n]*"|[{}]|\?=|[<>!=]=?|[^\s{}<>!=?"]+')
_OPS = {"=", "?=", "<", ">", "<=", ">=", "!="}


# --- a small tree of a Paradox file -----------------------------------------

@dataclass
class Node:
    key: str
    op: str
    value: str | None  # None for a block
    children: list[Node]
    line: int
    pos: int  # token index of the key
    comment: str | None = None  # the comment on the key's line

    def canon(self) -> str:
        if self.value is not None:
            return f"{self.key} {self.op} {self.value}"
        return f"{self.key} {self.op} {{ " + " ".join(c.canon() for c in self.children) + " }"

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def child(self, key: str) -> Node | None:
        return next((c for c in self.children if c.key == key), None)


def _tokens(text: str):
    toks, comments = [], {}
    for line_num, raw in enumerate(text.splitlines(), 1):
        idx = raw.find("#")
        content = raw if idx < 0 else raw[:idx]
        if idx >= 0:
            comments[line_num] = raw[idx:]
        for tok in _TOKEN_RE.findall(content):
            toks.append((tok, line_num))
    return toks, comments


def parse(text: str) -> list[Node]:
    toks, comments = _tokens(text)
    pos = 0

    def block() -> list[Node]:
        nonlocal pos
        out: list[Node] = []
        while pos < len(toks):
            tok, line = toks[pos]
            if tok == "}":
                pos += 1
                return out
            if tok == "{":  # an anonymous block: keep its children flat
                pos += 1
                out.extend(block())
                continue
            if pos + 1 < len(toks) and toks[pos + 1][0] in _OPS:
                key, op, start = tok, toks[pos + 1][0], pos
                pos += 2
                if pos < len(toks) and toks[pos][0] == "{":
                    pos += 1
                    out.append(Node(key, op, None, block(), line, start, comments.get(line)))
                elif pos < len(toks):
                    out.append(Node(key, op, toks[pos][0], [], line, start, comments.get(line)))
                    pos += 1
                continue
            out.append(Node(tok, "", tok, [], line, pos, comments.get(line)))  # a bare list item
            pos += 1
        return out

    return block()


def _read(path: str) -> str:
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def _txt_files(mod_path: str, sub: str):
    root_dir = os.path.join(mod_path, sub)
    for root, _dirs, files in os.walk(root_dir):
        for fname in sorted(files):
            if fname.endswith(".txt"):
                abs_p = os.path.join(root, fname)
                yield abs_p, os.path.relpath(abs_p, mod_path).replace(os.sep, "/")


# --- the audit ---------------------------------------------------------------

@dataclass
class Call:
    file: str
    line: int
    entity: str  # the top-level entity holding the call
    delay: str
    reason: str = ""  # why this call makes the target likely false; "" if none
    set_before: bool = False


@dataclass
class Target:
    event: str
    file: str
    line: int  # of the trigger
    hidden: bool
    conditions: list[str]
    calls: list[Call] = field(default_factory=list)
    exemption: dict | None = None
    cls: str = "review"

    @property
    def cancels(self) -> bool:
        """A review saying the trigger also cancels the event."""
        return bool(self.exemption) and self.exemption["rationale"].lower().startswith("cancels")


@dataclass
class Stale:
    """A tag on an event that is no longer a delayed target with a trigger."""
    event: str
    file: str
    line: int


@dataclass
class AuditResult(_AuditResult):
    # The flags field holds every delayed target with a non-empty trigger, in
    # all classes; `unreviewed` picks the ones that fail.
    flags: list[Target] = field(default_factory=list)
    delayed_targets: int = 0  # every delayed target, with a trigger or not
    calls: int = 0
    unresolved: list[str] = field(default_factory=list)  # ids naming no mod event

    @property
    def targets(self) -> list[Target]:
        """This audit's own name for `flags`."""
        return self.flags

    @property
    def unreviewed(self) -> list[Target]:
        return [t for t in self.flags if t.cls in ("likely_false", "review")]

    @property
    def exemptions(self) -> list[Target]:
        return [t for t in self.flags if t.cls == "reviewed"]


def _defined_names(mod_path: str, sub: str) -> dict[str, Node]:
    out: dict[str, Node] = {}
    for abs_p, _rel in _txt_files(mod_path, sub):
        for node in parse(_read(abs_p)):
            if node.value is None:
                out[node.key] = node
    return out


def _reads_modifier(node: Node, helpers: dict[str, Node], depth: int = 0, seen=None) -> bool:
    """Whether the block reads a `modifier:` sum, directly or through a mod
    scripted trigger or script value it names (a few levels down)."""
    seen = set() if seen is None else seen
    for n in node.walk():
        if n.key.startswith("modifier:") or (n.value or "").startswith("modifier:"):
            return True
        for name in (n.key, n.value):
            if name in helpers and name not in seen and depth < 4:
                seen.add(name)
                if _reads_modifier(helpers[name], helpers, depth + 1, seen):
                    return True
    return False


def _law_hook_on_actions(mod_path: str) -> set[str]:
    names = {"on_law_activated"}
    for abs_p, _rel in _txt_files(mod_path, os.path.join("common", "on_actions")):
        for node in parse(_read(abs_p)):
            if node.key == "on_law_activated" and node.value is None:
                lst = node.child("on_actions")
                if lst is not None:
                    names.update(c.key for c in lst.children)
    return names


def _modifier_name(node: Node) -> str | None:
    if node.value is not None:
        return node.value
    name = node.child("name")
    return name.value if name is not None else None


_EXCLUSIVE_PARENTS = {"random_list", "switch", "first_valid"}
_NOT_RUN = {"limit", "trigger", "ai_chance", "weight", "possible", "potential", "is_shown",
            "is_valid", "visible", "cancel", "is_triggered_only", "title", "desc", "flavor"}
_DIRECTIVE_RE = re.compile(r"^[A-Z_]+:")


def _path(node: Node, target: Node) -> list[Node] | None:
    if node is target:
        return [node]
    for c in node.children:
        sub = _path(c, target)
        if sub is not None:
            return [node] + sub
    return None


def _run_before(entity: Node, call: Node) -> list[Node]:
    """The nodes that can run before `call` on the way to it: at each level
    of the path, the earlier siblings and what they hold. Not another
    option of the same event, an `if` before the `else` the call is in, or
    another branch of a `random_list`; nor a block that is only read
    (`limit`, `trigger`, `ai_chance`, ...)."""
    path = _path(entity, call) or [entity, call]
    out: list[Node] = []
    for parent, child in zip(path, path[1:]):
        if parent.key in _EXCLUSIVE_PARENTS:
            continue
        for sib in parent.children:
            if sib is child:
                break
            if sib.key in _NOT_RUN:
                continue
            if sib.key == "option" and parent is entity:
                continue
            if child.key in ("else", "else_if") and sib.key in ("if", "else_if"):
                continue
            out.extend(m for m in sib.walk())
    return out


# Blocks that run their children in the scope they are in. Any other block on
# the way to a call is taken to change scope (`scope:x = { }`, `owner = { }`,
# an iterator, ...), which is the careful reading: what was tested or set
# outside it was about another object.
_SAME_SCOPE = {"immediate", "option", "after", "effect", "if", "else_if", "else", "hidden_effect", "random",
               "random_list", "switch", "while", "custom_tooltip", "show_as_tooltip"}
_UNCONDITIONAL = {"hidden_effect", "custom_tooltip", "show_as_tooltip"}


def _same_scope(node: Node, parent: Node | None) -> bool:
    if node.key in _SAME_SCOPE:
        return True
    # a random_list's weights and a switch's cases
    return parent is not None and parent.key in ("random_list", "switch")


def _variable_name(node: Node) -> str | None:
    if node.value is not None:
        return node.value
    name = node.child("name")
    return name.value if name is not None else None


def _unconditional_writes(node: Node) -> set[str]:
    """The variables `node` sets on its own scope whenever it runs: itself, or
    what an unconditional wrapper holds."""
    if node.key == "set_variable":
        name = _variable_name(node)
        return {name} if name else set()
    if node.value is None and node.key in _UNCONDITIONAL:
        out: set[str] = set()
        for c in node.children:
            out |= _unconditional_writes(c)
        return out
    return set()


def _holds_at(entity: Node, call: Node) -> tuple[set[str], set[str]]:
    """`(conditions, variables)` that hold for the scope `call` sends its
    event to, on the day it is queued: the conditions (as `canon()`) of every
    `limit` the call sits inside, and the calling event's own `trigger` for a
    call in its `immediate`; and the variables set on that scope before the
    call. A block that changes scope on the way starts both over; an
    iterator's own `limit` is about the new scope, so it is kept."""
    path = _path(entity, call) or [entity, call]
    conditions: set[str] = set()
    variables: set[str] = set()
    if len(path) > 1 and path[1].key == "immediate":
        trigger = entity.child("trigger")
        if trigger is not None:
            conditions |= {c.canon() for c in trigger.children}
    for i, (parent, child) in enumerate(zip(path, path[1:])):
        if i and not _same_scope(parent, path[i - 1]):
            conditions, variables = set(), set()
        if i and parent.key not in _EXCLUSIVE_PARENTS:
            limit = parent.child("limit")
            if limit is not None and limit is not child:
                conditions |= {c.canon() for c in limit.children}
        if parent.key in _EXCLUSIVE_PARENTS:
            continue
        for sib in parent.children:
            if sib is child:
                break
            if sib.key == "option" and parent is entity:
                continue
            variables |= _unconditional_writes(sib)
    return conditions, variables


class _Files:
    """Each file parsed once; the entity and the node a call site names."""

    def __init__(self, mod_path: str):
        self.mod_path = mod_path
        self._trees: dict[str, list[Node]] = {}

    def entity_and_node(self, rel: str, entity: str, line: int) -> tuple[Node, Node] | None:
        if rel not in self._trees:
            try:
                self._trees[rel] = parse(_read(os.path.join(self.mod_path, rel)))
            except OSError:
                self._trees[rel] = []
        for top in self._trees[rel]:
            if top.value is not None or _DIRECTIVE_RE.sub("", top.key) != entity:
                continue
            at_line = [n for n in top.walk() if n.line == line and n is not top]
            if at_line:
                return top, next((n for n in at_line if n.key == "trigger_event"), at_line[0])
        return None


def _sites(mod_path: str):
    """`(event id, file, line, entity, delay)` for every delayed
    `trigger_event`; an id passed as `$EVENT$` is read at the caller that
    names it, as `script_call_graph` does."""
    import event_context_audit as eca
    import script_call_graph as scg

    g = eca.build_graph(mod_path, include_console=True, strip_directives=True)
    seen = set()
    for raw_id, sites in sorted(g.sites_by_event.items()):
        eid = raw_id.strip('"')
        for s in sites:
            if s.via != "trigger_event" or not s.delayed or scg._a_caller_fills_zero(g, s):
                continue
            if s.origin and not s.param_event:
                file, line, entity = s.origin  # a literal id inside `$WHO$ = { … }`
            else:
                file, line, entity = s.file, s.line, s.entity
            if (eid, file, line) in seen:
                continue
            seen.add((eid, file, line))
            delay = next((d for d in s.delays if d), "?")
            through = f", through `{s.origin[2]}`" if s.origin and s.param_event else ""
            yield eid, file, line, entity, f"delay {delay}{through}"


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    events: dict[str, tuple[str, Node]] = {}
    for abs_p, rel in _txt_files(mod_path, "events"):
        for node in parse(_read(abs_p)):
            if node.value is None and node.child("type") is not None:
                events[node.key] = (rel, node)

    helpers = _defined_names(mod_path, os.path.join("common", "scripted_triggers"))
    helpers.update(_defined_names(mod_path, os.path.join("common", "script_values")))
    law_hooks = _law_hook_on_actions(mod_path)
    files = _Files(mod_path)

    result = AuditResult()
    by_event: dict[str, list[Call]] = {}
    for target, rel, line, entity_name, delay in _sites(mod_path):
        result.calls += 1
        call = Call(rel, line, entity_name, delay)
        by_event.setdefault(target, []).append(call)
        trigger = events[target][1].child("trigger") if target in events else None
        if trigger is None or not trigger.children:
            continue
        found = files.entity_and_node(rel, entity_name, line)
        if found is None:
            continue
        entity, node = found
        before = _run_before(entity, node)
        added = {_modifier_name(m) for m in before if m.key == "add_modifier"}
        removed = {_modifier_name(m) for m in before if m.key == "remove_modifier"}
        held, set_vars = _holds_at(entity, node)
        reasons = []
        for cond in trigger.children:
            if cond.key == "has_modifier" and cond.value in added:
                reasons.append(f"modifier_same_block: `{cond.value}` is added before the call")
            elif cond.key == "NOT":
                inner = cond.child("has_modifier")
                if inner is not None and inner.value in removed:
                    reasons.append(f"modifier_same_block: `{inner.value}` is removed before the call")
        law_context = (
            rel.startswith("common/laws/")
            or entity_name in law_hooks
            or any(m.key == "activate_law" for m in before)
        )
        if law_context and _reads_modifier(trigger, helpers):
            reasons.append("law_lag: the trigger reads `modifier:` sums where a law has just changed")
        call.reason = "; ".join(reasons)
        call.set_before = all(
            c.canon() in held or (c.key == "has_variable" and c.value in set_vars)
            for c in trigger.children
        )

    for target, calls in sorted(by_event.items()):
        if target not in events:
            result.unresolved.append(target)
            continue
        result.delayed_targets += 1
        rel, node = events[target]
        trigger = node.child("trigger")
        if trigger is None or not trigger.children:
            continue  # no trigger, or an empty one: always true
        hidden = node.child("hidden")
        t = Target(
            event=target, file=rel, line=trigger.line,
            hidden=hidden is not None and hidden.value == "yes",
            conditions=[c.canon() for c in trigger.children],
            calls=calls,
        )
        t.exemption = parse_reviewed(trigger.comment, (TAG,))
        if t.exemption:
            t.cls = "reviewed"
        elif any(c.reason for c in calls):
            t.cls = "likely_false"
        elif all(c.set_before for c in calls):
            t.cls = "set_before"
        result.flags.append(t)

    listed = {t.event for t in result.flags}
    for eid, (rel, node) in sorted(events.items()):
        trigger = node.child("trigger")
        if trigger is not None and eid not in listed and parse_reviewed(trigger.comment, (TAG,)):
            result.stale.append(Stale(eid, rel, trigger.line))
    return result


# --- the report --------------------------------------------------------------

_HEADINGS = (
    ("likely_false", "Likely false when queued"),
    ("review", "Not reviewed: read the trigger against each call"),
    ("set_before", "Restated or set by the caller before the call"),
    ("reviewed", "Reviewed: true when queued"),
    ("cancels", "Reviewed: true when queued, and also cancels the event"),
)


def _cls(t: Target) -> str:
    return "cancels" if t.cancels else t.cls


def _short(cond: str, limit: int = 90) -> str:
    return cond if len(cond) <= limit else cond[: limit - 1] + "…"


def render_report(result: AuditResult) -> str:
    counts = {cls: sum(1 for t in result.targets if _cls(t) == cls) for cls, _ in _HEADINGS}
    out = [
        "# Delayed events with a trigger",
        "",
        "Auto-generated by `delayed_event_trigger_audit.py` on every full `POST /reload` of the mod state",
        "server. Do not hand-edit.",
        "",
        "A delayed `trigger_event` seems to drop its event, with no log line, when the event's `trigger` is",
        "false on the day it is queued, even if it holds on the day the event is due (#1596; the likely",
        "reading of a QA session, settled by the self-checks `delayed_trigger_queue_check` and",
        "`delayed_trigger_queue_probe`, `docs/testing/judiciary-playtest.md`). This lists every event the mod",
        "queues with `days`, `months` or `years` that has a non-empty top-level `trigger`, by whether that",
        "trigger holds when it is queued. The fix for one that waits for something to become true is no",
        "`trigger` and the conditions in `immediate` as `if = { limit = { ... } }`; for a visible event, a",
        "hidden relay with no trigger that opens it on the day (`te_judiciary_events.7`, `.8`,",
        "`decolonization_events.81`). One checked is marked `# REVIEWED YYYY-MM-DD (delayed_trigger): why`",
        "on its `trigger = {` line; a rationale starting \"cancels\" marks a trigger that also stops an event",
        "whose premise went away during the delay, which works only if the engine reads the trigger again",
        "when the event is due (self-check `delayed_trigger_fire_probe`).",
        "",
        "## Summary",
        "",
        f"- delayed calls: {result.calls}",
        f"- events they queue: {result.delayed_targets}",
        f"- with a non-empty top-level trigger: {len(result.targets)}",
    ]
    for cls, heading in _HEADINGS:
        out.append(f"- {heading.lower()}: {counts[cls]}")
    out.append(f"- stale tags: {len(result.stale)}")
    out.append("")
    for cls, heading in _HEADINGS:
        out += [f"## {heading}", ""]
        rows = [t for t in result.targets if _cls(t) == cls]
        if not rows:
            out += ["_None._", ""]
            continue
        for t in sorted(rows, key=lambda t: (t.file, t.event)):
            kind = "hidden" if t.hidden else "visible"
            out.append(f"### `{t.event}` ({kind}, `{t.file}`)")
            out.append("")
            if t.exemption:
                out.append(f"**{t.exemption['date']}**: {t.exemption['rationale']}")
                out.append("")
            out.append("Trigger: " + "; ".join(f"`{_short(c)}`" for c in t.conditions))
            out.append("")
            calls: dict[tuple[str, str, str, str], int] = {}
            for c in t.calls:
                k = (c.file, c.entity, c.delay, c.reason)
                calls[k] = calls.get(k, 0) + 1
            for (file, entity, delay, reason), n in sorted(calls.items()):
                times = f" ({n} calls)" if n > 1 else ""
                why = f": {reason}" if reason else ""
                out.append(f"- `{entity}` in `{file}`, {delay}{times}{why}")
            out.append("")
    if result.stale:
        out += ["## Stale tags", ""]
        out += [f"- `{s.event}` (`{s.file}:{s.line}`): no longer queued with a delay, or its trigger is empty"
                for s in result.stale]
        out.append("")
    if result.unresolved:
        out += ["## Ids naming no mod event", "", "A vanilla event, or an id no caller fills in; not read.", ""]
        out += [f"- `{u}`" for u in result.unresolved]
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: write the report, and count what is unreviewed."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    write_text(os.path.join(mod_path, REPORT), render_report(result))
    return {
        "delayed_calls": result.calls,
        "with_trigger": len(result.targets),
        "likely_false": sum(1 for t in result.targets if t.cls == "likely_false"),
        "unreviewed": len(result.unreviewed) + len(result.stale),
    }


def main(argv: list[str] | None = None) -> int:
    """Print the report, or with `--write` write it. `--strict` exits 1 on an
    unreviewed target or a stale tag."""
    from path_constants import mod_path

    def add_arguments(parser) -> None:
        parser.add_argument("--write", action="store_true",
                            help=f"Write {REPORT} instead of printing it.")

    def render(result: AuditResult, args) -> str | None:
        report = render_report(result)
        if args.write:
            write_text(os.path.join(mod_path, REPORT), report)
            return None
        if args.strict:
            lines = [f"{t.file}:{t.line}: {t.event} ({t.cls})" for t in result.unreviewed]
            lines += [f"{s.file}:{s.line}: {s.event} (stale delayed_trigger tag)" for s in result.stale]
            return "\n".join(lines) if lines else f"{len(result.targets)} delayed targets with a trigger, all reviewed."
        return report

    return cli_main(lambda args: audit(mod_path=mod_path), render, argv=argv,
                    description=__doc__.splitlines()[0], add_arguments=add_arguments)


if __name__ == "__main__":
    raise SystemExit(main())
