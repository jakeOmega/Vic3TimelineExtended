"""Report of the events the mod queues with a delay whose `trigger` may be
false on the day they are queued (#1596).

`trigger_event = { id = X days = N }` (or `months` / `years`) re-checks `X`'s
`trigger` when it fires, and the event also seems to be dropped for good,
with no log line, if that trigger is false when it is queued
(`docs/guides/scripting_best_practices.md` § "A Delayed `trigger_event`
Re-Checks Its Trigger When It Fires"). Court Overhaul never fired because of
it. The rule is measured only in part: the self-check
`delayed_trigger_queue_check` (`docs/testing/judiciary-playtest.md`) settles
it in game. Until then this is a report, not a gate: it fails nothing, and
nothing here says to rewrite an event. It gives the play-test its list.

Every delayed target with a top-level `trigger` falls in one class:

- `likely_false`: something at a call site says the trigger cannot yet hold.
  `modifier_same_block`: the trigger reads `has_modifier = X` (or its `NOT`)
  and the calling entity adds (removes) `X` before the call, which that
  block cannot see yet. `law_lag`: the trigger reads `modifier:` sums,
  directly or through a mod scripted trigger or script value, and the call
  is made where a law has just changed (a law's file, an on_action run from
  `on_law_activated`, or after an `activate_law` in the same entity): the
  new law is not in `modifier:` reads that day.
- `set_before`: every condition of the trigger is either restated in the
  calling entity before the call, or a `has_variable = X` the entity sets
  before it (a variable is visible at once). Plausibly true when queued.
- `reviewed`: the trigger line carries `# REVIEWED YYYY-MM-DD: why`.
- `review`: the rest. Most are surely true when queued (a trigger that
  restates what the caller already knows, from a scripted effect whose
  callers this audit does not follow); one that waits for something to
  become true never fires.

The fix for one that is false when queued (under the rule) is no top-level
`trigger` and the conditions in `immediate` as `if = { limit = { ... } }`;
for a visible event, a hidden relay with no trigger that opens it on the day
(`te_judiciary_events.7`, `.8`).

Runs on every full `POST /reload` and writes
`docs/engine/delayed_event_trigger_report.md`; returns no `unreviewed`
count, so it adds nothing to the reload's warnings. `python3
delayed_event_trigger_audit.py` prints the report; `--write` writes it.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field

REPORT = os.path.join("docs", "engine", "delayed_event_trigger_report.md")
DELAY_KEYS = {"days", "months", "years"}

_TOKEN_RE = re.compile(r'"[^"\n]*"|[{}]|\?=|[<>!=]=?|[^\s{}<>!=?"]+')
_REVIEWED_RE = re.compile(r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<why>.+?)\s*$")
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


@dataclass
class AuditResult:
    targets: list[Target] = field(default_factory=list)
    delayed_targets: int = 0  # every delayed target, with a trigger or not
    calls: int = 0
    unresolved: list[str] = field(default_factory=list)  # ids naming no mod event


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

    result = AuditResult()
    by_event: dict[str, list[Call]] = {}
    sites: list[tuple[str, Node, Node, str]] = []  # (file, entity, call node, target)
    for sub in ("common", "events"):
        for abs_p, rel in _txt_files(mod_path, sub):
            for entity in parse(_read(abs_p)):
                for n in entity.walk():
                    if n.key != "trigger_event" or n.value is not None:
                        continue
                    delay = next((c for c in n.children if c.key in DELAY_KEYS), None)
                    target = n.child("id")
                    if delay is None or target is None:
                        continue
                    result.calls += 1
                    sites.append((rel, entity, n, target.value or ""))
                    by_event.setdefault(target.value or "", [])

    for rel, entity, n, target in sites:
        delay = next(c for c in n.children if c.key in DELAY_KEYS)
        call = Call(rel, n.line, entity.key, f"{delay.key} = {delay.value or '{ … }'}")
        by_event[target].append(call)
        if target not in events:
            continue
        trigger = events[target][1].child("trigger")
        if trigger is None:
            continue
        before = _run_before(entity, n)
        added = {_modifier_name(m) for m in before if m.key == "add_modifier"}
        removed = {_modifier_name(m) for m in before if m.key == "remove_modifier"}
        set_vars = {m.value if m.value is not None else (m.child("name").value if m.child("name") else None)
                    for m in before if m.key == "set_variable"}
        canon_before = {m.canon() for m in before}
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
            or entity.key in law_hooks
            or any(m.key == "activate_law" for m in before)
        )
        if law_context and _reads_modifier(trigger, helpers):
            reasons.append("law_lag: the trigger reads `modifier:` sums where a law has just changed")
        call.reason = "; ".join(reasons)
        call.set_before = all(
            c.canon() in canon_before or (c.key == "has_variable" and c.value in set_vars)
            for c in trigger.children
        )

    for target, calls in sorted(by_event.items()):
        if target not in events:
            result.unresolved.append(target)
            continue
        result.delayed_targets += 1
        rel, node = events[target]
        trigger = node.child("trigger")
        if trigger is None:
            continue
        hidden = node.child("hidden")
        t = Target(
            event=target, file=rel, line=trigger.line,
            hidden=hidden is not None and hidden.value == "yes",
            conditions=[c.canon() for c in trigger.children],
            calls=calls,
        )
        m = _REVIEWED_RE.search(trigger.comment or "")
        if m:
            t.exemption = {"date": m.group("date"), "why": m.group("why")}
            t.cls = "reviewed"
        elif any(c.reason for c in calls):
            t.cls = "likely_false"
        elif all(c.set_before for c in calls):
            t.cls = "set_before"
        result.targets.append(t)
    return result


# --- the report --------------------------------------------------------------

_HEADINGS = (
    ("likely_false", "Likely false when queued"),
    ("review", "Not classified: read the trigger against each call"),
    ("set_before", "Restated or set by the caller before the call"),
    ("reviewed", "Reviewed"),
)


def _short(cond: str, limit: int = 90) -> str:
    return cond if len(cond) <= limit else cond[: limit - 1] + "…"


def render_report(result: AuditResult) -> str:
    counts = {cls: sum(1 for t in result.targets if t.cls == cls) for cls, _ in _HEADINGS}
    out = [
        "# Delayed events with a trigger",
        "",
        "Auto-generated by `delayed_event_trigger_audit.py` on every full `POST /reload` of the mod state",
        "server. Do not hand-edit.",
        "",
        "A delayed `trigger_event` seems to drop its event, with no log line, when the event's `trigger` is",
        "false on the day it is queued, even if it holds on the day the event is due (#1596; measured in part,",
        "settled by the self-check `delayed_trigger_queue_check`, `docs/testing/judiciary-playtest.md`). This",
        "lists every event the mod queues with `days`, `months` or `years` that has a top-level `trigger`, by",
        "how likely that trigger is to be false when queued. It fails nothing. Under the rule, the fix for one",
        "that waits for something to become true is no `trigger` and the conditions in `immediate` as",
        "`if = { limit = { ... } }`; for a visible event, a hidden relay with no trigger that opens it on the",
        "day (`te_judiciary_events.7`, `.8`). Mark one checked with `# REVIEWED YYYY-MM-DD: why` on its",
        "`trigger = {` line.",
        "",
        "## Summary",
        "",
        f"- delayed calls: {result.calls}",
        f"- events they queue: {result.delayed_targets}",
        f"- with a top-level trigger: {len(result.targets)}",
    ]
    for cls, heading in _HEADINGS:
        out.append(f"- {heading.lower()}: {counts[cls]}")
    out.append("")
    for cls, heading in _HEADINGS:
        out += [f"## {heading}", ""]
        rows = [t for t in result.targets if t.cls == cls]
        if not rows:
            out += ["_None._", ""]
            continue
        for t in sorted(rows, key=lambda t: (t.file, t.event)):
            kind = "hidden" if t.hidden else "visible"
            out.append(f"### `{t.event}` ({kind}, `{t.file}`)")
            out.append("")
            if t.exemption:
                out.append(f"**{t.exemption['date']}**: {t.exemption['why']}")
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
    if result.unresolved:
        out += ["## Ids naming no mod event", "",
                "A parameter (`$EVENT$`) or a vanilla event; not read.", ""]
        out += [f"- `{u}`" for u in result.unresolved]
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: write the report. Deliberately no `unreviewed`
    key: the list is not enforced until the rule is confirmed in game."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    out_path = os.path.join(mod_path, REPORT)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        "delayed_calls": result.calls,
        "with_trigger": len(result.targets),
        "likely_false": sum(1 for t in result.targets if t.cls == "likely_false"),
    }


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    report = render_report(result)
    if "--write" in argv:
        with open(os.path.join(mod_path, REPORT), "w", encoding="utf-8") as fh:
            fh.write(report)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
