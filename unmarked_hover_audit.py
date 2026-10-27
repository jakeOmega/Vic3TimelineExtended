"""Flag a hover whose text is not underlined (#1213, #1202 finding 6).

Style rule 3 (`docs/guides/gui_style_guide.md`): hoverable text is underlined,
with the `#tooltippable` format, so the player knows a hover is there. The
GUI and localization audit (#1202) found whole panels with no underline at
all: the Nuclear panel's rows, the Space Race value rows and column heads, the
state view's tile rows. In a row type whose tooltip comes from a block, the
fix is a `label_format` block on the label (`nd_row`, `nuclear_program_row`),
which a row without a tooltip overrides empty.

What is checked
---------------
A *hover* is a widget that carries a tooltip:

- a `tooltip = …` property (or a `tooltipwidget = { }`) on a widget, or
- a `blockoverride "X" { tooltip = … }` in an instance of a mod type whose
  definition has `block "X"` in some widget: the tooltip lands on that widget
  (`nd_row = { blockoverride "row_tooltip" { tooltip = "…" } }`), or
- a `tooltip` on an instance of a mod type, which lands on the type's root.

Its *text* is every textbox inside it (`textbox`, `text_single`,
`text_multi`, or a mod type built on one), as the instance assembles it: a
block takes the instance's override, or its own default. A textbox inside a
button, a control with an `onclick`, or a nested hover of its own belongs to
that one, not this hover.

A hover is flagged when it has text and none of it is marked. A textbox is
marked when its `default_format` holds `#tooltippable`, or its text does:
a literal, or the loc of a key it names (with `$key$` splices and the keys a
`Localize` / `SelectLocalization` names), the inline `#tooltippable;tooltip:
… Word#!` form included. One marked textbox is enough: the label, not the
value beside it.

Not flagged, to keep the audit to the mod's own hovers:

- a button or anything with an `onclick` (a control's hover says what it
  does, and vanilla underlines no button), and a hover with no textbox;
- a hover whose tooltip names nothing of the mod's: no loc key only the mod
  defines, no scripted GUI, script value, custom loc, static modifier or
  variable read (for a `tooltipwidget`, nothing in it does). That leaves out
  the vanilla markup the mod's copies of vanilla panels carry, which vanilla
  rarely underlines;
- a hover whose text is all vanilla's (a locked power bloc slot, whose
  tooltip the mod rewrote but whose look is vanilla's);
- a tooltip that repeats its label, the full text of a label that may elide
  (a good's name in a narrow column), since there is nothing more to find;
- `gui/te_debug_*.gui`, the console-only panels.

Where a flag is reported, and where its tag goes
------------------------------------------------
- A tooltip written where the hover is (a plain widget's, a type
  definition's, a `tooltipwidget`) is reported at its own line, once however
  many instances of the type show it. Its tag trails that line.
- A tooltip each instance sets (in a `blockoverride`, or on the instance) is
  reported once, at the type definition that holds the block (or the type of
  the instance), with the instances listed: a `label_format` block in the
  type mends them all. Its tag trails the type's opening `type x = … {` line.

    tooltip = "my_tt" # REVIEWED 2026-10-27 (unmarked_hover): the icon says it

A tag on a line where no flag is reported is stale and fails `--strict`.

Report: docs/engine/unmarked_hover_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import gui_tree
from gui_reference_audit import LEX, defined_names
from long_tooltip_audit import loc_call_keys
from mod_state import split_loc_line

CHECK = "unmarked_hover"
MARK = "#tooltippable"
SKIP_PREFIX = "te_debug_"
TEXT_KINDS = frozenset({"textbox", "text_single", "text_multi"})
LOC_DIR = os.path.join("localization", "english")
VANILLA_LOC = os.path.join("vanilla_parsed", "localization_english.json")
REPORT_PATH = os.path.join("docs", "engine", "unmarked_hover_report.md")
# Compound properties and other blocks that hold no widget.
NOT_WIDGETS = frozenset({
    "", "size", "position", "margin", "minimumsize", "maximumsize", "framesize",
    "spriteborder", "uv_scale", "translate_uv", "color", "state", "modify_texture",
    "background", "animation", "glow", "layer", "on_start", "on_finish",
    "start_sound", "soundparam", "margin_widget", "tooltipwidget", "types",
    "blockoverride", "block", "datamodel_wrap", "resizeparent", "cursorposition",
})

_SPLICE = re.compile(r"\$([\w.\-]+)(?:\|[^$]*)?\$")
_KEY_RE = re.compile(r"[A-Za-z_][\w.\-]*")
_MOD_CALLS = {
    "scripted_guis": re.compile(r"GetScriptedGui\(\s*'([^']+)'"),
    "script_values": re.compile(r"ScriptValue\(\s*'([^']+)'"),
    "customizable_localization": re.compile(r"GetCustom\(\s*'([^']+)'"),
    "static_modifiers": re.compile(r"GetStaticModifier\(\s*'([^']+)'"),
}
_VARIABLE_READ = re.compile(r"\b(?:Var|GetVariable|GetGlobalVariable)\(|\bScriptedGui\.")
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$"
)


@dataclass
class Flag:
    file: str
    line: int
    hover: str  # the widget carrying the tooltip, as the report names it
    tooltip: str
    labels: list[str]  # the unmarked textboxes' text
    # For a type's flag: "file:line" of each instance tooltip it covers.
    instances: list[str] = field(default_factory=list)
    exemption: dict | None = None


@dataclass
class StaleTag:
    file: str
    line: int


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    files_scanned: int = 0
    hovers_checked: int = 0
    vanilla_skipped: int = 0
    repeat_skipped: int = 0

    @property
    def failing(self) -> int:
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


def _parse_tag(comment: str) -> dict | None:
    if "REVIEWED" not in comment:
        return None
    m = _TAGGED_REVIEWED_RE.search(comment)
    if not m or CHECK not in re.split(r"[\s,]+", m.group("checks").strip()):
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


class _Context:
    """What the walk needs from the mod: loc, the mod's own names, types."""

    def __init__(self, root: Path, trees: dict[str, gui_tree.Node]):
        vpath = root / VANILLA_LOC
        if not vpath.is_file():
            raise FileNotFoundError(
                f"{vpath} is missing; rebuild it with `python3 vanilla_parsed.py build` "
                "on a machine with the game (without it every vanilla key would read as the mod's)"
            )
        self.vanilla_loc = {k for k in json.loads(vpath.read_text(encoding="utf-8"))}
        self.loc: dict[str, str] = {}
        loc_dir = root / LOC_DIR
        for p in sorted(loc_dir.rglob("*.yml"), key=lambda p: (p.parent.name == "replace", p.name)):
            for raw in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                parsed = split_loc_line(raw)
                if parsed:
                    self.loc[parsed[0]] = parsed[1]
        self.mod_names = {
            kind: set().union(*(defined_names(p.read_text(encoding="utf-8-sig", errors="replace"))
                                for p in sorted((root / "common" / kind).rglob("*.txt"))))
            for kind in _MOD_CALLS
        }
        self.trees = trees
        self.types = gui_tree.type_index(trees)
        self._marked_keys: dict[str, bool] = {}

    # -- what is the mod's --------------------------------------------------
    def mod_only_key(self, key: str) -> bool:
        return key in self.loc and key not in self.vanilla_loc

    def mod_owned(self, tooltip: str) -> bool:
        if _KEY_RE.fullmatch(tooltip):
            return self.mod_only_key(tooltip)
        if any(self.mod_only_key(k) for k in loc_call_keys(tooltip)):
            return True
        if _VARIABLE_READ.search(tooltip):
            return True
        return any(name in self.mod_names[kind]
                   for kind, rx in _MOD_CALLS.items() for name in rx.findall(tooltip))

    # -- marks ----------------------------------------------------------------
    def key_marked(self, key: str) -> bool:
        if key in self._marked_keys:
            return self._marked_keys[key]
        self._marked_keys[key] = False  # cycle guard
        value = self.loc.get(key, "")
        marked = MARK in value or any(
            self.key_marked(k) for k in _SPLICE.findall(value) + loc_call_keys(value))
        self._marked_keys[key] = marked
        return marked

    def text_marked(self, text: str) -> bool:
        if MARK in text:
            return True
        if _KEY_RE.fullmatch(text):
            return self.key_marked(text)
        return any(self.key_marked(k) for k in _SPLICE.findall(text) + loc_call_keys(text))

    # -- the instantiated tree ------------------------------------------------
    def is_text(self, kind: str) -> bool:
        return any(k in TEXT_KINDS for k in gui_tree.base_chain(kind, self.types))

    def is_button(self, kind: str) -> bool:
        return any("button" in k for k in gui_tree.base_chain(kind, self.types))

    def type_defs(self, kind: str) -> list[gui_tree.Node]:
        """The mod type definitions an instance of `kind` is built from, base first."""
        chain = [k for k in gui_tree.base_chain(kind, self.types) if k in self.types]
        return [self.types[k] for k in reversed(chain)]


@dataclass
class _View:
    """A widget as one instance assembles it."""
    node: gui_tree.Node
    props: list[gui_tree.Prop]
    children: list[tuple[gui_tree.Node, dict]]
    # Where each tooltip-bearing prop came from, for the report.
    tooltip_source: gui_tree.Prop | None
    has_tooltipwidget: gui_tree.Node | None


def _block_contents(node: gui_tree.Node, overrides: dict, depth: int = 0):
    """(props, children) of a node's own content, blocks resolved against
    the overrides in force (an override replaces the block's default)."""
    props = list(node.props)
    children: list[tuple[gui_tree.Node, dict]] = []
    for c in node.children:
        if c.kind == "block":
            src = overrides.get(c.name, c)
            if depth < 8:
                p, ch = _block_contents(src, overrides, depth + 1)
                props += p
                children += ch
        elif c.kind == "blockoverride":
            continue
        else:
            children.append((c, overrides))
    return props, children


def view(ctx: _Context, node: gui_tree.Node, overrides: dict) -> _View:
    props, children = _block_contents(node, overrides)
    # A type definition builds on its base's; an instance on its type's.
    defs = ctx.type_defs(node.base if node.kind == "type" else node.kind)
    if defs:
        inner = dict(overrides)
        inner.update({c.name: c for c in node.children if c.kind == "blockoverride"})
        tprops: list[gui_tree.Prop] = []
        tchildren: list[tuple[gui_tree.Node, dict]] = []
        for d in defs:
            p, ch = _block_contents(d, inner)
            tprops += p
            tchildren += ch
        props = tprops + props
        children = tchildren + children
    tooltip = None
    for p in props:
        if p.key == "tooltip" and p.value.strip():
            tooltip = p
    widget = next((c for c, _ in children if c.kind == "tooltipwidget"), None)
    return _View(node, props, children, tooltip, widget)


def _last(props: list[gui_tree.Prop], key: str) -> str | None:
    found = None
    for p in props:
        if p.key == key:
            found = p.value
    return found


class _Walker:
    def __init__(self, ctx: _Context):
        self.ctx = ctx
        self.flags: dict[tuple[str, int], Flag] = {}
        self.hovers = 0
        self.vanilla = 0
        self.repeats = 0
        self.prop_file: dict[int, str] = {}
        self.owner: dict[int, gui_tree.Node] = {}

    def file_of(self, prop: gui_tree.Prop) -> str:
        return self.prop_file.get(id(prop), "?")

    def control(self, v: _View) -> bool:
        return self.ctx.is_button(v.node.kind) or _last(v.props, "onclick") is not None

    def labels(self, v: _View, depth: int = 0) -> list[tuple[_View, bool]]:
        """(textbox view, marked) for each textbox of the hover `v`."""
        out: list[tuple[_View, bool]] = []
        if self.ctx.is_text(v.node.kind):
            text = _last(v.props, "text") or _last(v.props, "raw_text") or ""
            if text.strip():
                fmt = _last(v.props, "default_format") or ""
                out.append((v, MARK in fmt or self.ctx.text_marked(text)))
        if depth > 30:
            return out
        for child, ov in v.children:
            if child.kind in NOT_WIDGETS:
                continue
            cv = view(self.ctx, child, ov)
            if self.control(cv) or cv.tooltip_source or cv.has_tooltipwidget:
                continue
            out += self.labels(cv, depth + 1)
        return out

    def walk(self, node: gui_tree.Node, overrides: dict, depth: int = 0) -> None:
        if node.kind in NOT_WIDGETS or depth > 40:
            return
        v = view(self.ctx, node, overrides)
        self.judge(v)
        for child, ov in v.children:
            self.walk(child, ov, depth + 1)

    def home_type(self, v: _View, source: gui_tree.Prop | None) -> gui_tree.Node | None:
        """The type definition to fix when each instance sets its own tooltip:
        the one holding the block an instance's `blockoverride` fills, or the
        type of an instance that carries the tooltip itself. None when the
        tooltip is written where the hover is (a definition or a plain widget)."""
        if source is None:
            return None
        owner = self.owner.get(id(source))
        if owner is None:
            return None
        if owner.kind == "blockoverride":
            # The most derived type of the overriding instance whose
            # definition holds the block, else the type around the hover.
            instance = owner.parent
            for d in reversed(self.ctx.type_defs(instance.kind) if instance else []):
                if any(n.kind == "block" and n.name == owner.name for n in d.walk()):
                    return d
            node = v.node
            if node.kind == "type":
                return node
            return next((a for a in node.ancestors() if a.kind == "type"), None)
        if owner is v.node and v.node.kind in self.ctx.types:
            return self.ctx.types[v.node.kind]
        return None

    def judge(self, v: _View) -> None:
        source = v.tooltip_source
        if source is None and v.has_tooltipwidget is None:
            return
        if self.control(v):
            return
        if source is not None:
            set_at = (self.file_of(source), source.line)
            tooltip = source.value
        else:
            w = v.has_tooltipwidget
            set_at = (self.prop_file.get(id(w), "?"), w.line)
            tooltip = "tooltipwidget"
        if set_at[0].startswith("gui/" + SKIP_PREFIX):
            return
        if source is not None:
            owned = self.ctx.mod_owned(tooltip)
        else:
            owned = any(self.ctx.mod_owned(p.value) for n in v.has_tooltipwidget.walk() for p in n.props)
        if not owned:
            self.vanilla += 1
            return
        labels = self.labels(v)
        if not labels:
            return
        if not any(self.ctx.mod_owned(_last(lv.props, "text") or _last(lv.props, "raw_text") or "")
                   for lv, _ in labels):
            # Vanilla's own text under a hover the mod rewrote (a locked
            # power bloc slot): vanilla's look, not one of the mod's panels.
            self.vanilla += 1
            return
        self.hovers += 1
        if any(marked for _, marked in labels):
            return
        texts = {_last(lv.props, "text") or _last(lv.props, "raw_text") for lv, _ in labels}
        if source is not None and tooltip in texts:
            # The hover repeats the label, the full name of a label that may
            # elide (a good's name in a narrow column): nothing to find.
            self.repeats += 1
            return
        home = self.home_type(v, source)
        if home is not None:
            loc = (self.prop_file.get(id(home), "?"), home.line)
            hover = f"type {home.name}"
            instance = f"{set_at[0]}:{set_at[1]}"
        else:
            loc, hover, instance = set_at, v.node.label, ""
        flag = self.flags.get(loc)
        if flag is None:
            flag = Flag(loc[0], loc[1], hover, tooltip, [])
            self.flags[loc] = flag
        for lv, _ in labels:
            t = _last(lv.props, "text") or _last(lv.props, "raw_text") or ""
            if t not in flag.labels and len(flag.labels) < 4:
                flag.labels.append(t)
        if instance and instance not in flag.instances:
            flag.instances.append(instance)


def audit(mod_path: str | Path | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    root = Path(mod_path)
    trees: dict[str, gui_tree.Node] = {}
    for path in gui_tree.gui_files(root):
        trees[path.relative_to(root).as_posix()] = gui_tree.parse_file(path)
    if not trees:
        raise FileNotFoundError(f"no .gui file to scan under {root / 'gui'}")
    ctx = _Context(root, trees)
    walker = _Walker(ctx)
    for rel, tree in trees.items():
        for node in tree.walk():
            walker.prop_file[id(node)] = rel
            for p in node.props:
                walker.prop_file[id(p)] = rel
                walker.owner[id(p)] = node
    result = AuditResult(files_scanned=len(trees))
    for rel, tree in sorted(trees.items()):
        if rel.startswith("gui/" + SKIP_PREFIX):
            continue
        for top in tree.children:
            if top.kind == "types":
                for t in top.children:
                    if t.kind == "type":
                        walker.walk(t, {})
            else:
                walker.walk(top, {})
    # A hover marked in one instance and not in another is still flagged:
    # some instance shows it unmarked.
    tags = _tags(root, trees)
    flagged = set(walker.flags)
    for loc, flag in sorted(walker.flags.items()):
        flag.exemption = tags.get(loc)
        result.flags.append(flag)
    for loc in sorted(tags):
        if loc not in flagged:
            result.stale_tags.append(StaleTag(*loc))
    result.hovers_checked = walker.hovers
    result.vanilla_skipped = walker.vanilla
    result.repeat_skipped = walker.repeats
    return result


def _tags(root: Path, trees: dict[str, gui_tree.Node]) -> dict[tuple[str, int], dict]:
    out: dict[tuple[str, int], dict] = {}
    for rel in trees:
        text = (root / rel).read_text(encoding="utf-8-sig", errors="replace")
        if CHECK not in text:
            continue
        for tok in LEX.finditer(text):
            if tok[0].startswith("#"):
                tag = _parse_tag(tok[0])
                if tag:
                    out[(rel, text.count("\n", 0, tok.start()) + 1)] = tag
    return out


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Unmarked hover audit report",
        "",
        "Auto-generated by `unmarked_hover_audit.py` on every `POST /reload` of the",
        "mod state server. Do not hand-edit.",
        "",
        "Flagged: a widget of the mod's that carries a tooltip (its own `tooltip`, a",
        "`tooltipwidget`, or a `blockoverride` that fills a tooltip block) and whose",
        "text has no `#tooltippable` underline, neither in a textbox's",
        "`default_format` nor in its loc. Style rule 3: hoverable text is",
        "underlined. In a row type, put the label's `default_format` in a",
        "`label_format` block that a row without a tooltip overrides empty",
        "(`nd_row`). Buttons and `onclick` controls are not judged.",
        "",
        "A tooltip each instance sets is reported once, at the type that holds",
        "the unmarked text, with the instances listed.",
        "",
        "Suppress a deliberate case trailing on the flag's line (the tooltip's,",
        "or a type's opening `type x = … {` line):",
        "`# REVIEWED YYYY-MM-DD (unmarked_hover): why`",
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
            out += [f"### `{fname}` ({len(by_file[fname])})", ""]
            for f in by_file[fname]:
                labels = ", ".join(f"`{t[:60]}`" for t in f.labels)
                where = ""
                if f.instances:
                    shown = ", ".join(f"`{i}`" for i in f.instances[:3])
                    more = f" and {len(f.instances) - 3} more" if len(f.instances) > 3 else ""
                    where = f"; {len(f.instances)} instance tooltip(s): {shown}{more}"
                out.append(f"- line {f.line}: {f.hover}, text {labels}{where}")
            out.append("")
    if result.stale_tags:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` ({CHECK})" for t in result.stale_tags]
        out.append("")
    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        for f in exemp:
            out.append(f"- `{f.file}` — {f.hover} — "
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
    GUI, loc and script files itself, so `mod_state` is unused."""
    from path_constants import mod_path
    result = audit(mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        "unreviewed": result.failing,
        "total_flags": len(result.flags),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "stale_tags": len(result.stale_tags),
        "files_scanned": result.files_scanned,
        "hovers_checked": result.hovers_checked,
        "vanilla_skipped": result.vanilla_skipped,
        "repeat_skipped": result.repeat_skipped,
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
