"""Flag greyed buttons that don't say why (#1213, #1202 finding 5).

Style rule 6 (`docs/guides/gui_style_guide.md`): a button that can't be
pressed is greyed, and its tooltip lists the failing condition, with
`IsValidTooltip` concatenated with the effect preview (gotcha #16). A
requirement reads as a requirement, never as a raw trigger name. Two checks:

`missing_reason`
    A `.gui` widget whose `enabled` is a scripted GUI's `IsValid(…)` (named,
    `GetScriptedGui('x').IsValid`, or through a datacontext,
    `ScriptedGui.IsValid`) while no tooltip of that button prints
    `IsValidTooltip(…)`. The button greys and nothing says why: the Space
    colony and fleet buttons render only `ExecuteTooltip` (SPC-1). The
    tooltip is looked for on the widget, and where the `enabled` sits in a
    `blockoverride`, on its instance, the instance's other overrides and the
    type's definition. A tooltip that branches on the same `IsValid(…)` to a
    reason of its own (`SelectLocalization( ….IsValid(…), 'ok', 'why_not' )`)
    counts as a reason. Not flagged: a scripted GUI with no `is_valid`, or one
    holding only `always = yes`, which never greys the button.

`raw_condition`
    A condition `IsValidTooltip` (or a scripted button's tooltip) prints as
    raw script: in the `is_valid` of a scripted GUI whose `IsValidTooltip` the
    mod's GUI or loc renders, or the `possible` of a scripted button, a test
    outside any `custom_tooltip` that is

    - a variable test: `has_variable`, `has_global_variable`, a `…_list`
      test, `exists = var:x`, or a comparison whose left side reads `var:`,
      `global_var:` or `local_var:` (`var:te_peg_confidence <= 40`);
    - a comparison of a mod script value (`ww_ideological_tension >= 30`);
    - a mod scripted trigger (`banking_external_available = yes`) whose body,
      read through further mod scripted triggers, holds one of the above
      outside a `custom_tooltip`, since a tooltip prints a scripted trigger's
      contents. The flag names the test it reaches.

    Blocks that print nothing are not read: `custom_tooltip` (and its
    `_no_bullet`, `custom_description` and `custom_label` forms),
    `hidden_trigger`, and a `trigger_if`'s `limit`. A scripted GUI's
    `IsValidTooltip` counts as rendered when a `.gui` or loc file names it
    (`GetScriptedGui('x').IsValidTooltip`), or when a `.gui` file that uses
    `ScriptedGui.IsValidTooltip` gives x as a `datacontext`. A scripted
    button whose `visible` holds `is_ai = yes` at its top level is the AI's
    alone (the UN's and the Nuclear program's buttons, since their panels'
    scripted GUIs took over): no player sees its tooltip, so its `possible`
    is not read (counted as `ai_only_skipped`).

`gui/te_debug_*.gui` and `te_debug_*` script files are skipped, as
console-only panels.

Suppression is check-tagged. For `missing_reason`, on the `enabled =` line;
for `raw_condition`, on the block's opening `is_valid = {` / `possible = {`
line (one flag a block, listing its tests):

    enabled = "[…IsValid(…)]" # REVIEWED 2026-10-27 (missing_reason): rationale
    is_valid = { # REVIEWED 2026-10-27 (raw_condition): rationale

A tag on a line with no flag of its check is stale and fails `--strict`.

Report: docs/engine/button_reason_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import gui_tree
from gui_reference_audit import LEX, defined_names, masks
from long_tooltip_audit import loc_call_keys
from mod_state import split_loc_line

CHECKS = ("missing_reason", "raw_condition")
SKIP_PREFIX = "te_debug_"
LOC_DIR = os.path.join("localization", "english")
REPORT_PATH = os.path.join("docs", "engine", "button_reason_report.md")

_IS_VALID = re.compile(r"(?:GetScriptedGui\(\s*'(\w+)'\s*\)|\bScriptedGui)\s*\.\s*IsValid\(")
_DATACONTEXT_SGUI = re.compile(r"^\[\s*GetScriptedGui\(\s*'(\w+)'\s*\)\s*\]$")
_RENDERED_NAMED = re.compile(r"GetScriptedGui\(\s*'(\w+)'\s*\)\s*\.\s*IsValidTooltip\(")
_SPLICE = re.compile(r"\$([\w.\-]+)(?:\|[^$]*)?\$")
_SCRIPT_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[{}]|[!?<>=]=|[<>=]|[^\s{}=<>!?"]+')
_OPS = frozenset({"=", "<", ">", "<=", ">=", "!=", "?=", "=="})
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)

COVER = frozenset({
    "custom_tooltip", "custom_tooltip_no_bullet", "custom_description",
    "custom_description_no_bullet", "custom_label", "custom_label_no_bullet",
    "hidden_trigger",
})
VARIABLE_TESTS = frozenset({
    "has_variable", "has_global_variable", "has_local_variable",
    "has_variable_list", "has_global_variable_list", "has_local_variable_list",
    "has_variable_map", "has_global_variable_map", "has_local_variable_map",
    "is_target_in_variable_list", "is_target_in_global_variable_list",
    "is_target_in_local_variable_list", "variable_list_size",
    "global_variable_list_size", "local_variable_list_size",
})
_VAR_READ = re.compile(r"(?:^|[.:])(?:global_|local_)?var:")


@dataclass
class Stmt:
    key: str
    op: str
    value: str | None
    children: list[Stmt] | None
    line: int


@dataclass
class Flag:
    check: str
    file: str
    line: int
    owner: str  # the scripted GUI / button, or the widget
    detail: str
    exemption: dict | None = None


@dataclass
class StaleTag:
    check: str
    file: str
    line: int


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    buttons_checked: int = 0
    blocks_checked: int = 0
    ai_only_skipped: int = 0

    @property
    def failing(self) -> int:
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


def _tags_in(text: str) -> dict[int, dict[str, dict]]:
    """line -> {check: tag} for every check-tagged REVIEWED comment."""
    out: dict[int, dict[str, dict]] = {}
    if "REVIEWED" not in text:
        return out
    for tok in LEX.finditer(text):
        if not tok[0].startswith("#") or "REVIEWED" not in tok[0]:
            continue
        m = _TAGGED_REVIEWED_RE.search(tok[0])
        if not m:
            continue
        checks = set(re.split(r"[\s,]+", m.group("checks").strip())) & set(CHECKS)
        if checks:
            line = text.count("\n", 0, tok.start()) + 1
            tag = {"date": m.group("date"), "rationale": m.group("rationale").strip()}
            out.setdefault(line, {}).update({c: tag for c in checks})
    return out


def parse_script(text: str) -> list[Stmt]:
    """A script file's statements as a tree, each with its line."""
    code = masks(text)[0]
    tokens = [(m[0], m.start()) for m in _SCRIPT_TOKEN.finditer(code)]
    lines: list[int] = []
    line, pos = 1, 0
    for _, offset in tokens:
        line += code.count("\n", pos, offset)
        pos = offset
        lines.append(line)
    root: list[Stmt] = []
    stack = [root]
    i, n = 0, len(tokens)
    while i < n:
        t = tokens[i][0]
        if t == "}":
            if len(stack) > 1:
                stack.pop()
            i += 1
        elif t == "{":
            node = Stmt("", "", None, [], lines[i])
            stack[-1].append(node)
            stack.append(node.children)
            i += 1
        elif i + 1 < n and tokens[i + 1][0] in _OPS:
            op = tokens[i + 1][0]
            value = tokens[i + 2][0] if i + 2 < n else ""
            if value == "{":
                node = Stmt(t, op, None, [], lines[i])
                stack[-1].append(node)
                stack.append(node.children)
            else:
                stack[-1].append(Stmt(t, op, value.strip('"'), None, lines[i]))
            i += 3
        else:
            stack[-1].append(Stmt(t, "", None, None, lines[i]))
            i += 1
    return root


def _depth0(path: Path) -> list[Stmt]:
    return [s for s in parse_script(path.read_text(encoding="utf-8-sig", errors="replace"))
            if s.children is not None]


class _Script:
    """The mod's scripted triggers and script value names."""

    def __init__(self, root: Path):
        self.triggers: dict[str, list[Stmt]] = {}
        for path in sorted((root / "common" / "scripted_triggers").rglob("*.txt")):
            for st in _depth0(path):
                self.triggers[st.key.split(":")[-1]] = st.children
        self.script_values: set[str] = set()
        for path in sorted((root / "common" / "script_values").rglob("*.txt")):
            self.script_values |= defined_names(path.read_text(encoding="utf-8-sig", errors="replace"))
        self._memo: dict[str, list[str]] = {}

    def raw_tests(self, stmts: list[Stmt], stack: tuple = ()) -> list[tuple[Stmt, str]]:
        """(statement, what prints raw) for each raw test among `stmts`, a
        scripted trigger call standing for the raw test it reaches."""
        out: list[tuple[Stmt, str]] = []
        for st in stmts:
            if st.key in COVER or st.key == "limit":
                continue
            if st.children is not None:
                if st.key in self.triggers:
                    reached = self.trigger_raw(st.key, stack)
                    if reached:
                        out.append((st, f"`{st.key}` reaches `{reached[0]}`"))
                    continue
                out += self.raw_tests(st.children, stack)
                continue
            raw = self.leaf_raw(st)
            if raw:
                out.append((st, f"`{raw}`"))
            elif st.key in self.triggers and st.value in ("yes", "no"):
                reached = self.trigger_raw(st.key, stack)
                if reached:
                    out.append((st, f"`{st.key} = {st.value}` reaches `{reached[0]}`"))
        return out

    def leaf_raw(self, st: Stmt) -> str | None:
        text = f"{st.key} {st.op} {st.value}" if st.op else st.key
        if st.key in VARIABLE_TESTS:
            return text
        if st.op and _VAR_READ.search(st.key):
            return text
        if st.key == "exists" and st.value and _VAR_READ.search(st.value):
            return text
        if st.op and st.op != "=" and st.key in self.script_values:
            return text
        if st.op == "=" and st.key in self.script_values and st.value and re.fullmatch(r"-?[\d.]+", st.value):
            return text
        return None

    def trigger_raw(self, name: str, stack: tuple) -> list[str]:
        """The raw tests a scripted trigger's body prints, as text."""
        if name in self._memo:
            return self._memo[name]
        if name in stack:
            return []
        self._memo[name] = []
        found = [why.strip("`") for _, why in self.raw_tests(self.triggers[name], stack + (name,))]
        # A nested trigger's description already names its own raw test.
        found = [f.split("` reaches `")[-1] for f in found]
        self._memo[name] = found
        return found


def _block(stmts: list[Stmt], key: str) -> Stmt | None:
    for st in stmts:
        if st.key == key and st.children is not None:
            return st
    return None


def _never_greys(sgui: Stmt) -> bool:
    """A scripted GUI with no `is_valid`, or one that holds only `always =
    yes`, is always valid: its button never greys."""
    valid = _block(sgui.children, "is_valid")
    if valid is None:
        return True
    tests = [st for st in valid.children if st.key]
    return all(st.key == "always" and st.value == "yes" for st in tests)


def _ai_only(button: Stmt) -> bool:
    """A scripted button only the AI sees: `is_ai = yes` at the top level of
    its `visible` (an AND), so no player ever reads its `possible`."""
    visible = _block(button.children, "visible")
    return visible is not None and any(
        st.key == "is_ai" and st.op == "=" and st.value == "yes" for st in visible.children)


def _rendered_sguis(root: Path, trees: dict[str, gui_tree.Node]) -> set[str]:
    names: set[str] = set()
    for rel, tree in trees.items():
        text = (root / rel).read_text(encoding="utf-8-sig", errors="replace")
        names |= set(_RENDERED_NAMED.findall(text))
        if "ScriptedGui.IsValidTooltip" in text.replace(" ", ""):
            for node in tree.walk():
                dc = node.prop("datacontext")
                if dc and (m := _DATACONTEXT_SGUI.match(dc.value.strip())):
                    names.add(m.group(1))
    for path in sorted((root / LOC_DIR).rglob("*.yml")):
        names |= set(_RENDERED_NAMED.findall(path.read_text(encoding="utf-8-sig", errors="replace")))
    return names


def _sgui_defs(root: Path) -> dict[str, tuple[str, Stmt]]:
    out: dict[str, tuple[str, Stmt]] = {}
    for path in sorted((root / "common" / "scripted_guis").rglob("*.txt")):
        if path.name.startswith(SKIP_PREFIX):
            continue
        rel = path.relative_to(root).as_posix()
        for st in _depth0(path):
            out[st.key.split(":")[-1]] = (rel, st)
    return out


def _load_loc(root: Path) -> dict[str, str]:
    loc: dict[str, str] = {}
    for p in sorted((root / LOC_DIR).rglob("*.yml"), key=lambda p: (p.parent.name == "replace", p.name)):
        for raw in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            parsed = split_loc_line(raw)
            if parsed:
                loc[parsed[0]] = parsed[1]
    return loc


def _gives_reason(tooltip: str, loc: dict[str, str]) -> bool:
    """A tooltip that prints `IsValidTooltip`, or branches on `IsValid` to a
    reason of its own; read through the loc keys it names."""
    seen: set[str] = set()
    todo = [tooltip]
    while todo:
        text = todo.pop()
        if "IsValidTooltip(" in text or re.search(r"\.\s*IsValid\(", text):
            return True
        keys = loc_call_keys(text) + _SPLICE.findall(text)
        if re.fullmatch(r"[A-Za-z_][\w.\-]*", text):
            keys.append(text)
        for k in keys:
            if k not in seen and k in loc:
                seen.add(k)
                todo.append(loc[k])
    return False


def _tooltip_props(node: gui_tree.Node) -> list[str]:
    return [p.value for n in node.walk() for p in n.props if p.key == "tooltip"]


def _instance_tooltips(instance: gui_tree.Node) -> list[str]:
    """The tooltips an instance sets: its own, and its overrides'."""
    found = [p.value for p in instance.props if p.key == "tooltip"]
    for c in instance.children:
        if c.kind == "blockoverride":
            found += _tooltip_props(c)
    return found


def _instance_sgui(instance: gui_tree.Node) -> str | None:
    for c in instance.children:
        if c.kind == "blockoverride":
            for n in c.walk():
                dc = n.prop("datacontext")
                if dc and (m := _DATACONTEXT_SGUI.match(dc.value.strip())):
                    return m.group(1)
    return None


def _contexts(node: gui_tree.Node, types: dict[str, gui_tree.Node],
              instances: dict[str, list[tuple[str, gui_tree.Node]]]):
    """(where, tooltips, scripted GUI or None) for each way the button whose
    `enabled` is in `node` is put together. A widget that sets its own
    tooltip is one context. An `enabled` in a `blockoverride` takes its
    instance's other tooltips and its type's. An `enabled` in a type's
    definition is judged once per instance of the type, each with the
    tooltips and the datacontext that instance overrides in."""
    own = [p.value for p in node.props if p.key == "tooltip"]
    if own:
        return [("", own, None)]
    if node.kind == "blockoverride" and node.parent is not None:
        instance = node.parent
        found = _instance_tooltips(instance)
        for kind in gui_tree.base_chain(instance.kind, types):
            if kind in types:
                found += _tooltip_props(types[kind])
        return [("", found, None)]
    typedef = node if node.kind == "type" else next((a for a in node.ancestors() if a.kind == "type"), None)
    if typedef is None:
        return [("", [], None)]
    base = _tooltip_props(typedef)
    users = instances.get(typedef.name, [])
    if not users:
        return [("", base, None)]
    return [(f"{rel}:{inst.line}", base + _instance_tooltips(inst), _instance_sgui(inst))
            for rel, inst in users]


def _sgui_for(node: gui_tree.Node, value: str) -> str | None:
    m = _IS_VALID.search(value)
    if m and m.group(1):
        return m.group(1)
    for n in (node, *node.ancestors()):
        dc = n.prop("datacontext")
        if dc and (dm := _DATACONTEXT_SGUI.match(dc.value.strip())):
            return dm.group(1)
    return None


def audit(mod_path: str | Path | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    root = Path(mod_path)
    trees = {p.relative_to(root).as_posix(): gui_tree.parse_file(p) for p in gui_tree.gui_files(root)}
    if not trees:
        raise FileNotFoundError(f"no .gui file to scan under {root / 'gui'}")
    types = gui_tree.type_index(trees)
    loc = _load_loc(root)
    sguis = _sgui_defs(root)
    if not sguis:
        raise FileNotFoundError(f"no scripted GUI under {root / 'common' / 'scripted_guis'}")
    result = AuditResult()
    flagged: set[tuple[str, str, int]] = set()
    tags: dict[str, dict[int, dict[str, dict]]] = {}

    # missing_reason: the .gui side.
    instances: dict[str, list[tuple[str, gui_tree.Node]]] = {}
    for rel, tree in sorted(trees.items()):
        for node in tree.walk():
            if node.kind in types:
                instances.setdefault(node.kind, []).append((rel, node))
    for rel, tree in sorted(trees.items()):
        if rel.startswith("gui/" + SKIP_PREFIX):
            continue
        tags[rel] = _tags_in((root / rel).read_text(encoding="utf-8-sig", errors="replace"))
        for node in tree.walk():
            enabled = node.prop("enabled")
            if enabled is None or not _IS_VALID.search(enabled.value):
                continue
            name = _sgui_for(node, enabled.value)
            missing: list[str] = []
            names: list[str] = []
            for where, tooltips, inst_sgui in _contexts(node, types, instances):
                sgui = name or inst_sgui
                if sgui in sguis and _never_greys(sguis[sgui][1]):
                    continue
                result.buttons_checked += 1
                if any(_gives_reason(t, loc) for t in tooltips):
                    continue
                missing.append(where)
                if sgui and sgui not in names:
                    names.append(sgui)
            if not missing:
                continue
            detail = "greyed with no `IsValidTooltip` in its tooltip"
            sites = [w for w in missing if w]
            if sites:
                shown = ", ".join(f"`{w}`" for w in sites[:3])
                more = f" and {len(sites) - 3} more" if len(sites) > 3 else ""
                detail += f", in {len(sites)} instance(s): {shown}{more}"
            tag = tags[rel].get(enabled.line, {}).get("missing_reason")
            flagged.add(("missing_reason", rel, enabled.line))
            result.flags.append(Flag("missing_reason", rel, enabled.line,
                                     ", ".join(names) or "ScriptedGui", detail, tag))

    # raw_condition: the script side.
    script = _Script(root)
    rendered = _rendered_sguis(root, trees)
    blocks: list[tuple[str, str, Stmt]] = []
    for name, (rel, st) in sorted(sguis.items()):
        valid = _block(st.children, "is_valid")
        if valid is not None and name in rendered:
            blocks.append((rel, name, valid))
    for path in sorted((root / "common" / "scripted_buttons").rglob("*.txt")):
        if path.name.startswith(SKIP_PREFIX):
            continue
        rel = path.relative_to(root).as_posix()
        for st in _depth0(path):
            possible = _block(st.children, "possible")
            if possible is None:
                continue
            if _ai_only(st):
                result.ai_only_skipped += 1
                continue
            blocks.append((rel, st.key.split(":")[-1], possible))
    for rel, owner, block in blocks:
        if rel not in tags:
            tags[rel] = _tags_in((root / rel).read_text(encoding="utf-8-sig", errors="replace"))
        result.blocks_checked += 1
        tests: list[str] = []
        seen_lines: set[int] = set()
        for st, why in script.raw_tests(block.children):
            if st.line not in seen_lines:
                seen_lines.add(st.line)
                tests.append(f"line {st.line}: {why}")
        if not tests:
            continue
        tag = tags[rel].get(block.line, {}).get("raw_condition")
        flagged.add(("raw_condition", rel, block.line))
        where = "is_valid" if block.key == "is_valid" else "possible"
        result.flags.append(Flag("raw_condition", rel, block.line, f"{owner} {where}",
                                 "; ".join(tests), tag))

    for rel, by_line in sorted(tags.items()):
        for line, checks in sorted(by_line.items()):
            for check in sorted(checks):
                if (check, rel, line) not in flagged:
                    result.stale_tags.append(StaleTag(check, rel, line))
    result.flags.sort(key=lambda f: (f.check, f.file, f.line))
    return result


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Button reason audit report",
        "",
        "Auto-generated by `button_reason_audit.py` on every `POST /reload` of the",
        "mod state server. Do not hand-edit.",
        "",
        "Style rule 6: a greyed button's tooltip lists the failing condition, worded",
        "as a requirement. `missing_reason`: a `.gui` widget enabled by a scripted",
        "GUI's `IsValid` whose tooltip prints no `IsValidTooltip`. `raw_condition`:",
        "a test in a rendered scripted GUI's `is_valid` or a scripted button's",
        "`possible`, outside any `custom_tooltip`, that prints as raw script (a",
        "variable or script value test, or a scripted trigger that reaches one).",
        "Wrap it in `custom_tooltip = { text = <requirement> … }`, or in",
        "`hidden_trigger` where `is_shown` already holds it. A scripted button",
        "only the AI sees (`visible` holds `is_ai = yes`) is not read.",
        "",
        "Suppress a deliberate case on the flagged line:",
        "`# REVIEWED YYYY-MM-DD (missing_reason): why` on the `enabled` line, or",
        "`# REVIEWED YYYY-MM-DD (raw_condition): why` on the block's opening",
        "`is_valid = {` / `possible = {` line.",
        "",
    ]
    for check in CHECKS:
        rows = [f for f in unrev if f.check == check]
        out += [f"## Unreviewed `{check}` ({len(rows)})", ""]
        if not rows:
            out += ["_None._", ""]
            continue
        by_file: dict[str, list[Flag]] = {}
        for f in rows:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out += [f"### `{fname}` ({len(by_file[fname])})", ""]
            # Repeats (a generated row per site) share one bullet.
            groups: dict[tuple[str, str], list[int]] = {}
            for f in by_file[fname]:
                groups.setdefault((f.owner, f.detail), []).append(f.line)
            for (owner, detail), lines in groups.items():
                where = f"line {lines[0]}" if len(lines) == 1 else \
                    f"lines {', '.join(map(str, lines))}"
                out.append(f"- {where}: `{owner}` — {detail}")
            out.append("")
    if result.stale_tags:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` ({t.check})" for t in result.stale_tags]
        out.append("")
    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        for f in exemp:
            out.append(f"- `{f.file}` — {f.check} `{f.owner}` — "
                       f"**{f.exemption['date']}**: {f.exemption['rationale']}")
        out.append("")
    out += [
        "## Coverage",
        "",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        f"- stale tags: {len(result.stale_tags)}",
        "",
    ]
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report. Reads the
    GUI, script and loc files itself, so `mod_state` is unused."""
    from path_constants import mod_path
    result = audit(mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        "unreviewed": result.failing,
        "total_flags": len(result.flags),
        "missing_reason": sum(1 for f in result.flags if f.check == "missing_reason"),
        "raw_condition": sum(1 for f in result.flags if f.check == "raw_condition"),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "stale_tags": len(result.stale_tags),
        "buttons_checked": result.buttons_checked,
        "blocks_checked": result.blocks_checked,
        "ai_only_skipped": result.ai_only_skipped,
        "path": out_path,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on any untagged flag or stale tag (CI mode)")
    parser.add_argument("--mod-path", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.mod_path)
    print(render_report(result))
    return int(args.strict and result.failing > 0)


if __name__ == "__main__":
    raise SystemExit(main())
