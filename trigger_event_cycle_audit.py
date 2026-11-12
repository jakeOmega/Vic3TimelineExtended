"""Audit cycles through an undelayed `trigger_event` (#1012).

`trigger_event = { id = X }` with no `days` / `weeks` / `months` / `years`
runs `X` at once, nested on the engine's stack inside the effect that fires
it. If `X` leads back to that effect (event → scripted effect → the event
again) and nothing written before the `trigger_event` stops the next pass, the
engine recurses until the stack overflows: a crash with no log line. Two
crashes on 2026-10-17 were `gm_com_fulfil` firing `monument_events.26` before
it closed the opportunity, 198 rounds deep
(`scripting_best_practices.md` § "A `trigger_event` With No Delay Runs the
Event Inside the Effect That Fires It").

What is flagged
---------------
Every undelayed `trigger_event` that lies on a cycle of the mod's script call
graph (`script_call_graph`): the firing entity and the fired event are in one
strongly connected component of the graph whose edges are scripted-effect
calls and undelayed `trigger_event`s. The report gives the shortest cycle
through each.

* **Delayed** (`days`, `weeks`, `months` or `years` other than a literal 0):
  not an edge. The event is queued and runs on a fresh stack. A range reads
  as its first value (`days = { 0 1 }` is no delay); a `$DAYS$` reads as its
  caller's value, and is no delay when some caller passes 0.
* **`random` / `random_list`**: an edge. A branch can be taken on every pass,
  and its weight is not read here.
* **An event option**: an edge. A player's click runs on a fresh stack, but
  the AI answers "as soon as the event fires" (`event_creation_guide.md`), and
  whether that is inside the `trigger_event` is not measured. A review may
  rest on the event reaching only a player, and says how that is known.
* **An on-action's `events` list, a pulse**: nothing fires an on-action from
  script, so none is on a cycle. An effect that makes the engine run other
  script at once (`activate_law` → `on_law_activated`, `add_journal_entry` →
  the entry's `immediate`) is an edge this graph does not hold.
* **`$EVENT$`**: an id passed as a parameter is an edge from the caller that
  names the event, at the caller's line.
* The `te_debug_*` console harnesses are read too: a loop there crashes the
  game all the same.
* **`REPLACE:x` / `INJECT:x`** (any of the six merge directives): the
  definition is `x`'s, so its calls and events are `x`'s edges.
* **`$EFFECT$ = yes`** in a helper: a call to each effect a caller names
  (`EFFECT = nd_log_incident_launch_warning`); a caller whose value is no
  effect (a scope, for `$WHO$ = { … }`) adds nothing.

A cycle of scripted effects alone, with no event in it, is not flagged.

Blind spots
-----------
* Edges the engine runs from an effect, which the graph does not hold:
  `create_building` → `on_building_built` → `monument_events.1` →
  `monument_events.20` (the one nearest the Grand Monuments' cycles; whether
  the hook runs inside the effect is not established), `activate_law` →
  `on_law_activated`, `add_journal_entry` → the entry's `immediate`.
* A delay written as a script value's name (`days = my_value`) reads as a
  delay whatever the value; a `$DAYS$` that no caller fills in with a literal
  does too. The mod has neither (every delay is an integer literal).
* A `$EFFECT$ = yes` whose effect a caller names only through a scripted
  value or a scope (no literal name anywhere up the chain): no edge.

Suppression
-----------
Every flag needs a fix or a review. A fix breaks the cycle: write what the
cycle re-reads before the `trigger_event` (fire it last), or delay it. A
review names the write that already does, trailing on the flagged line:

    trigger_event = { id = ns.2 } # REVIEWED 2026-11-12 (trigger_event_cycle): gm_com_close on the line above removes gm_com_open, which gm_com_check_progress reads

The flagged line is the `trigger_event` line (its opening line when it spans
several), or, for an id passed as `$EVENT$`, the opening line of the call that
names it. A tag on a line with no flag is stale and fails `--strict`. The
check name is in `event_context_audit.FOREIGN_CHECKS`, which reads every tag
inside an event.

Not done (the issue's order-aware refinement)
---------------------------------------------
The audit does not read what is written before or after the `trigger_event`.
A second pass could, within the firing block, collect the variables the
cycle's triggers and limits read (`has_variable`, `var:X`) and flag an edge
only when none of them is set or removed before the `trigger_event`, or one is
written only after it; that would have pointed at `gm_com_close` and would let
most reviews go. It needs the cycle's guards resolved through scripted
triggers and scopes, which this version leaves to the reviewer.

`python3 trigger_event_cycle_audit.py --through <event or effect>` lists the
flagged cycles a name lies on.

Report: docs/engine/trigger_event_cycle_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import script_call_graph as scg

CHECK = "trigger_event_cycle"
AUDIT_DIRS = ("common", "events")

_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)


@dataclass
class Flag:
    file: str
    line: int
    source: str  # the event or scripted effect that fires it
    event: str  # the event fired with no delay
    cycle: list[str]  # source, event, ..., back to source
    component: int  # which strongly connected component
    component_size: int
    in_option: bool = False
    random: bool = False
    through: str | None = None  # the helper whose `$EVENT$` the source's call fills in
    exemption: dict | None = None


@dataclass
class StaleTag:
    file: str
    line: int


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    events: int = 0
    effects: int = 0
    undelayed_edges: int = 0
    components: int = 0  # components holding at least one flag

    @property
    def failing(self) -> int:
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


def read_tags(mod_path: str) -> dict[tuple[str, int], dict]:
    """{(file, line): {date, rationale}} for every `(trigger_event_cycle)` tag
    in the mod's script."""
    tags: dict[tuple[str, int], dict] = {}
    for sub in AUDIT_DIRS:
        base = os.path.join(mod_path, sub)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs.sort()
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, encoding="utf-8-sig", errors="replace") as fh:
                        text = fh.read()
                except OSError:
                    continue
                if CHECK not in text:
                    continue
                rel = os.path.relpath(path, mod_path).replace("\\", "/")
                for lineno, raw in enumerate(text.splitlines(), 1):
                    if "REVIEWED" not in raw:
                        continue
                    m = _TAGGED_REVIEWED_RE.search(raw)
                    if m and CHECK in re.split(r"[\s,]+", m.group("checks").strip()):
                        tags[(rel, lineno)] = {"date": m.group("date"),
                                               "rationale": m.group("rationale").strip()}
    return tags


def find_flags(cg: scg.CallGraph) -> tuple[list[Flag], int]:
    """(flags, undelayed `trigger_event` edges seen)."""
    comp = cg.components(scg.runs_at_once)
    members: dict[int, set] = {}
    for node, c in comp.items():
        members.setdefault(c, set()).add(node)
    flags: list[Flag] = []
    undelayed = 0
    for e in cg.edges:
        if e.kind != "event" or e.via != "trigger_event" or e.delayed:
            continue
        undelayed += 1
        c = comp.get(e.src)
        if c is None or comp.get(e.dst) != c:
            continue
        # An event that fires itself is its own cycle; else the way back.
        back = [] if e.src == e.dst else (
            cg.shortest_path(e.dst, e.src, scg.runs_at_once, members[c]) or [])
        cycle = [e.src.name, e.dst.name] + [b.dst.name for b in back]
        flags.append(Flag(e.file, e.line, e.src.name, e.dst.name, cycle, c, len(members[c]),
                          e.in_option, e.random, e.through[0] if e.through else None))
    flags.sort(key=lambda f: (f.file, f.line, f.event, f.source))
    return flags, undelayed


def audit(mod_state=None, mod_path: str | None = None) -> AuditResult:
    """`mod_state` is unused (pure file scan) but kept for the
    POST_LOAD_GENERATORS `regenerate(mod_state)` contract."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    cg = scg.build(mod_path)
    result = AuditResult(
        events=sum(1 for n in cg.nodes if n.kind == scg.EVENT),
        effects=sum(1 for n in cg.nodes if n.kind == scg.EFFECT),
    )
    result.flags, result.undelayed_edges = find_flags(cg)
    result.components = len({f.component for f in result.flags})

    tags = read_tags(mod_path)
    used: set[tuple[str, int]] = set()
    for f in result.flags:
        f.exemption = tags.get((f.file, f.line))
        if f.exemption:
            used.add((f.file, f.line))
    result.stale_tags = [StaleTag(file, line) for (file, line) in sorted(tags) if (file, line) not in used]
    return result


def cycles_through(result: AuditResult, name: str) -> list[Flag]:
    """The flags whose cycle passes through the event or scripted effect `name`."""
    return [f for f in result.flags if name in f.cycle]


def flag_dict(f: Flag) -> dict:
    return {
        "file": f.file, "line": f.line, "from": f.source, "event": f.event, "path": f.cycle,
        "in_option": f.in_option, "random": f.random, "through": f.through,
        "component": f.component, "component_size": f.component_size, "reviewed": f.exemption,
    }


def describe(f: Flag) -> str:
    notes = []
    if f.through:
        notes.append(f"the id is `{f.through}`'s parameter")
    if f.in_option:
        notes.append("in an option")
    if f.random:
        notes.append("behind a random roll")
    head = f"`{f.source}` fires `{f.event}` with no delay"
    if notes:
        head += " (" + ", ".join(notes) + ")"
    if len(f.cycle) == 2 and f.source == f.event:
        return head + ", which is itself"
    return head + ", and it leads back: " + " → ".join(f"`{n}`" for n in f.cycle)


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Trigger-event cycle audit report",
        "",
        "Auto-generated by `trigger_event_cycle_audit.py` on every `POST /reload` of",
        "the mod state server. Do not hand-edit.",
        "",
        "Flagged: a `trigger_event` with no delay that lies on a cycle of scripted",
        "effect calls and undelayed `trigger_event`s. Such an event runs at once,",
        "inside the effect that fires it, so a cycle nothing stops recurses until",
        "the stack overflows: a crash with no log line (#1012). An event option",
        "and a `random` branch count as edges; a delayed `trigger_event` does not.",
        "",
        "Fix: write what the cycle re-reads before the `trigger_event` (fire it",
        "last), or give it `days = 1`. Where a write already stops the next pass,",
        "name it on the flagged line (the `trigger_event` line; for an id passed",
        "as `$EVENT$`, the line of the call that names it):",
        "`# REVIEWED YYYY-MM-DD (trigger_event_cycle): <the write that breaks the cycle>`",
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
            out += [f"### `{fname}`", ""]
            out += [f"- line {f.line}: {describe(f)}" for f in by_file[fname]]
            out.append("")

    if result.stale_tags:
        out += ["## Stale tags", "", "Tags on a line with no flag; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` ({CHECK})" for t in result.stale_tags]
        out.append("")

    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        # No line number on a reviewed entry: an edit above it would otherwise
        # churn the report.
        out += [
            f"- `{f.file}` — {describe(f)} — **{f.exemption['date']}**: {f.exemption['rationale']}"
            for f in exemp
        ]
        out.append("")

    # Flag counts only: the event, effect and edge counts stay on the result
    # (and in the regenerate() summary) but move with unrelated mod content.
    out += [
        "## Coverage",
        "",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        f"- stale tags: {len(result.stale_tags)}",
        f"- cycles' components: {result.components}",
        "",
    ]
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report."""
    from path_constants import mod_path
    result = audit(mod_state, mod_path=mod_path)
    out_path = os.path.join(mod_path, "docs", "engine", "trigger_event_cycle_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        # Flags without a tag, plus tags on a line with no flag.
        "unreviewed": result.failing,
        "total_flags": len(result.flags),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "stale_tags": len(result.stale_tags),
        "components": result.components,
        "undelayed_edges": result.undelayed_edges,
        "events": result.events,
        "effects": result.effects,
        "path": out_path,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    res = audit(mod_path=mod_path)
    if "--through" in sys.argv:
        i = sys.argv.index("--through")
        if i + 1 >= len(sys.argv):
            raise SystemExit("--through needs an event id or a scripted effect's name")
        hits = cycles_through(res, sys.argv[i + 1])
        for f in hits:
            mark = "reviewed" if f.exemption else "UNREVIEWED"
            print(f"{f.file}:{f.line} [{mark}] " + " -> ".join(f.cycle))
        if not hits:
            print(f"no flagged cycle passes through {sys.argv[i + 1]}")
    else:
        print(render_report(res))
    # --strict: CI mode. Exit 1 if any flag lacks its check-tagged
    # `# REVIEWED` comment, or any such tag sits on a line with no flag.
    if "--strict" in sys.argv:
        raise SystemExit(1 if res.failing else 0)
