"""Flag a loc key whose country root is wrong for a context that renders it (#319).

The same loc key can be drawn from places with different data roots. Script
builds a journal entry's `status_desc` in the entry's scope, where the country
is `ROOT.GetCountry`; a `.gui` widget evaluates its text in the widget's data
context, where the country is `Country` (the one its mount supplies) or
`JournalEntry.GetCountry`. A key written for one and reached from the other
renders blank, or shows the wrong country's figure, and no log line names the
key. A key's own text doesn't say where it renders: it gets there through a
`$KEY$` splice, a key named in `SelectLocalization` or `AddLocalizationIf`, or
as a `customizable_localization` entry's `localization_key` behind a
`GetCustom('entry')` call. #317 and #318 shipped ten such keys between them,
three of them with their own text unchanged, pulled into a widget by a new
parent.

The contexts, and what is flagged in each
-----------------------------------------
entry text      The keys a journal entry's `status_desc` block names (`desc =`
                at any depth), and a scripted button's `name` and `desc`.
                Flagged (`widget_root_in_entry_text`): a `JournalEntry.` or
                `Country.` read. Vanilla's own keys there read `ROOT`, `SCOPE`
                and `GetPlayer` and nothing else (the 82 of its 187
                `status_desc` keys and the 111 of its 524 button keys that
                read a root, in the 1.15 snapshot), so those are the proven
                roots; read the country as `ROOT.GetCountry`.
widget          The keys any `gui/**/*.gui` file names: a `text`, `tooltip` or
                `raw_text`, a quoted key inside an expression, a `GetCustom`
                entry's keys. Flagged (`script_root_in_widget`): a `ROOT.`,
                `SCOPE.` or `THIS.` read. A widget has no script scope; read
                `Country` (`gui_modding_guide.md` gotcha #45).
public panel    The keys another country's panel renders of a public tab
                (National Info; `Tab.public` in `gen_te_systems_window.py`),
                by `gui_test_helpers.panel_loc_keys`, which leaves out what
                sits under `te_own_country_only`. Flagged: a `JournalEntry`
                read (`entry_read_on_public_panel`: another country has no
                entry in reach, gotcha #35) and a read of the player
                (`player_read_on_public_panel`) unless the key is in
                `WORLD_LOC` in `test_te_system_tab_bodies.py`. These are that
                file's `BindingTest` rules for loc, restated here so a reload
                reports them too. Fix by `te_rebind_country.py <tab>`.

Every read is looked for inside the value's `[...]` expressions only, so
"the richest Country." in prose is not one.

Rendered, counted and not judged
--------------------------------
entry frame     A journal entry's implicit keys (`<je>`, `<je>_reason`,
                `<je>_goal`, `<je>_status`), its `progress_desc`, and a
                scripted progress bar's `name`, `desc` and `second_desc`. The
                journal panel draws these with the entry in context: vanilla
                reads `JournalEntry` in 22 `_status`, 20 `_goal` and 19
                `_reason` keys (`je_princely_states_status` reads
                `JournalEntry.GetCountry`), in the default progress text
                (`JOURNAL_ENTRY_PROGRESSBAR_FROM_ZERO`) and in every progress
                bar's `[JournalEntry.GetCurrentBarProgress(
                ScriptedProgressBar.Self)]`; it reads `ROOT` and `SCOPE` there
                too, and `Country` in eight. No root can be called wrong.
scripted GUI    The keys a scripted GUI's own `custom_tooltip` lines name
tooltip         (`common/scripted_guis/`), which a widget renders through
                `ExecuteTooltip`. Script builds the text, so `ROOT`, `SCOPE`
                and `THIS` (inside a scope change) are right there, and the
                widget's data context seems to reach it too (the UN's
                `je_un_ov_motions_wait_tt` reads `JournalEntry.GetCountry`).
                Exempt. A finding on a key that is also one of these says so:
                split the key. The helper here reads only the scripted GUI's
                own lines, not the scripted effects it calls; #1361 is to add
                a shared walker.

Not looked at: an event's text, a `custom_tooltip` in other script, and
whether a widget's context holds the object a widget root names (a
`JournalEntry` read on a panel with no entry, `Country` in a vanilla-copied
panel or a datamodel item's tooltip; `te_rebind_country.py` classes those for
a tab).

Reach
-----
`gui_test_helpers.loc_closure` decides what a key reaches: a `$KEY$` splice,
any quoted name in the value that is a loc key (so the keys named in
`SelectLocalization`, `AddLocalizationIf` and `Localize`), and the keys of a
`GetCustom` entry. `gui_keys` reads a `.gui` file the same way. Both err
wide: a quoted script value or scripted GUI name that happens to be a loc key
counts. A finding gives the path from the line that names the first key down
to the flagged one, so a key whose text never changed shows which parent
exposed it.

Suppression
-----------
A reviewed case takes a tag trailing its loc line (the engine ignores
anything after the closing quote; keep the reason free of `"`):

    my_key:0 "[ROOT.GetCountry.GetName]" # REVIEWED 2026-11-12 (loc_root_context): rationale

It covers that key's `widget_root_in_entry_text` and `script_root_in_widget`
flags. A public-panel flag takes none: a world read goes in `WORLD_LOC`, and
`BindingTest` fails on anything else. A tag on a key with no flag is stale
and fails `--strict`.

No game install is needed. A scan that finds no loc file or no `.gui` file
raises, so a wrong path can't pass as clean.

Report: docs/engine/loc_root_context_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import re
from dataclasses import dataclass, field

import gui_test_helpers as h
from mod_state import split_loc_line
from script_loc_reference_audit import iter_references

CHECK = "loc_root_context"
REPORT_PATH = os.path.join("docs", "engine", "loc_root_context_report.md")
LOC_DIR = os.path.join("localization", "english")

ENTRY, FRAME, WIDGET, PUBLIC, SGUI = "entry text", "entry frame", "widget", "public panel", "scripted GUI tooltip"

WIDGET_ROOT_IN_ENTRY = "widget_root_in_entry_text"
SCRIPT_ROOT_IN_WIDGET = "script_root_in_widget"
ENTRY_READ_ON_PUBLIC = "entry_read_on_public_panel"
PLAYER_READ_ON_PUBLIC = "player_read_on_public_panel"
TAGGABLE = frozenset({WIDGET_ROOT_IN_ENTRY, SCRIPT_ROOT_IN_WIDGET})

WHY = {
    WIDGET_ROOT_IN_ENTRY: "a widget's root, in text script builds (a `status_desc`, a scripted button): read "
                          "`ROOT.GetCountry` there, or split the key",
    SCRIPT_ROOT_IN_WIDGET: "a script root, in text a widget renders: read `Country` there, or split the key",
    ENTRY_READ_ON_PUBLIC: "a journal entry read on a public tab: another country's panel has no entry in reach",
    PLAYER_READ_ON_PUBLIC: "a read of the player on a public tab: another country's panel would show the "
                           "player's figure (a world read goes in `WORLD_LOC`)",
}

# A read is the root and the first call on it, inside a `[...]` expression.
_EXPR = re.compile(r"\[([^\]]*)\]")
_SCRIPT_ROOT = re.compile(r"(?<![\w.'])(?:ROOT|SCOPE|THIS)\.\w+")
_WIDGET_ROOT = re.compile(r"(?<![\w.'])(?:JournalEntry|Country)\.\w+")

# A top-level entry of a script file, a merge directive (`INJECT:`) cut from its name.
_TOP = re.compile(r"(?m)^(?:\w+:)?([\w.\-]+)\s*=\s*\{")
_FIELD = re.compile(r'[{}]|(?<![\w.])(\w+)\s*=\s*(?:"([\w.\-]+)"|([\w.\-]+)(?![\w.\-"]))')
_DESC_FIELD = re.compile(r'(?<![\w.])(status_desc|progress_desc)\s*=\s*(\{|"?[\w.\-]+"?)')
_JOURNAL_SUFFIXES = ("", "_reason", "_goal", "_status")
_TOOLTIP_FIELDS = frozenset({"custom_tooltip", "custom_tooltip_no_bullet", "text"})
_TAG = re.compile(r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$")


@dataclass
class Flag:
    kind: str
    key: str
    file: str
    line: int
    reads: tuple[str, ...]
    path: tuple[str, ...] = ()
    """Entry text and widget: where the first key is named, then each key down to this one."""
    tabs: tuple[str, ...] = ()
    """Public panel: the tabs whose panel renders the key."""
    also_sgui: bool = False
    exemption: dict | None = None


@dataclass
class StaleTag:
    file: str
    line: int
    key: str


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    stale_tags: list[StaleTag] = field(default_factory=list)
    reach: dict[str, int] = field(default_factory=dict)
    """Context -> the loc keys it renders."""
    public_tabs: int = 0

    @property
    def failing(self) -> int:
        """Flags without a tag, plus tags that suppress nothing."""
        return sum(1 for f in self.flags if not f.exemption) + len(self.stale_tags)


def _end(code: str, brace: int) -> int:
    """The brace that closes the one at `brace`; the end of the text for a
    block left open (mod_structure_audit's to flag)."""
    try:
        return h._close(code, brace)
    except AssertionError:
        return len(code) - 1


def _code(text: str) -> str:
    """gui_test_helpers._strip_comments, run only on the lines that hold a `#`
    (it walks every character, and most lines have no comment)."""
    return "\n".join(h._strip_comments(line) if "#" in line else line for line in text.split("\n"))


def _script_files(root: str, sub: str):
    for path in sorted(glob.glob(os.path.join(root, "common", sub, "**", "*.txt"), recursive=True)):
        yield os.path.relpath(path, root).replace(os.sep, "/"), _code(h._read(path))


def _line(code: str, pos: int) -> int:
    return code.count("\n", 0, pos) + 1


def _own_fields(code: str, brace: int, end: int, names):
    """(field, value, offset) for each `field = value` a block holds directly."""
    depth = 0
    for m in _FIELD.finditer(code, brace, end + 1):
        if m.group() == "{":
            depth += 1
        elif m.group() == "}":
            depth -= 1
        elif depth == 1 and m.group(1) in names:
            yield m.group(1), m.group(2) or m.group(3), m.start()


def journal_seeds(root: str, loc) -> tuple[dict[str, str], dict[str, str]]:
    """(entry text, entry frame): each key a journal entry file names for
    either, with where. Entry text is a `status_desc`'s keys; the frame is the
    entry's implicit keys and its `progress_desc`."""
    entry: dict[str, str] = {}
    frame: dict[str, str] = {}

    def add(out, key, where):
        if key in loc:
            out.setdefault(key, where)

    for rel, code in _script_files(root, "journal_entries"):
        for top in _TOP.finditer(code):
            for suffix in _JOURNAL_SUFFIXES:
                add(frame, top.group(1) + suffix, f"{rel}:{_line(code, top.start())} {top.group(1)}'s own text")
        for m in _DESC_FIELD.finditer(code):
            out = entry if m.group(1) == "status_desc" else frame
            at = _line(code, m.start())
            if m.group(2) != "{":
                add(out, m.group(2).strip('"'), f"{rel}:{at} {m.group(1)}")
                continue
            brace = m.end() - 1
            for n, fld, key, _ in iter_references(code[brace:_end(code, brace) + 1]):
                if fld == "desc":
                    add(out, key, f"{rel}:{at + n - 1} {m.group(1)}")
    return entry, frame


def block_seeds(root: str, sub: str, fields, loc) -> dict[str, str]:
    """Each key a top-level block under common/<sub>/ names in one of `fields`
    (a scripted button's or a scripted progress bar's own text), with where."""
    out: dict[str, str] = {}
    for rel, code in _script_files(root, sub):
        for top in _TOP.finditer(code):
            brace = top.end() - 1
            for fld, key, pos in _own_fields(code, brace, _end(code, brace), fields):
                if key in loc:
                    out.setdefault(key, f"{rel}:{_line(code, pos)} {top.group(1)}'s {fld}")
    return out


def _scripted_gui_tooltip_seeds(root: str, loc) -> dict[str, str]:
    """Each key a scripted GUI's own `custom_tooltip` lines name. Private and
    shallow on purpose: it doesn't follow the scripted effects a GUI calls.
    #1361 is to add the shared "scripted GUI -> tooltip keys" walker; move
    onto it then."""
    out: dict[str, str] = {}
    for rel, code in _script_files(root, "scripted_guis"):
        for n, fld, key, _ in iter_references(code):
            if fld in _TOOLTIP_FIELDS and key in loc:
                out.setdefault(key, f"{rel}:{n} {fld}")
    return out


def widget_seeds(root: str, loc, custom) -> tuple[dict[str, str], int]:
    """Each key a .gui file names (gui_test_helpers.gui_keys), with the file,
    and how many files were read."""
    out: dict[str, str] = {}
    paths = sorted(glob.glob(os.path.join(root, "gui", "**", "*.gui"), recursive=True))
    for path in paths:
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        for key in h.gui_keys(_code(h._read(path)), loc, custom=custom):
            out.setdefault(key, rel)
    return out, len(paths)


class Reach:
    """What a set of keys reaches, by gui_test_helpers.loc_closure's edges,
    with each key's parent, so a finding can give its path. One step is the
    shared walker run over a table in which only the key in hand has its
    text: its `$KEY$` splices, quoted names and GetCustom keys come out, and
    go no further."""

    def __init__(self, loc, custom):
        self.loc, self.custom = loc, custom
        self._blank = dict.fromkeys(loc, "")

    def step(self, key: str) -> set[str]:
        self._blank[key] = self.loc[key]
        try:
            return h.loc_closure({key}, self._blank, custom=self.custom) - {key}
        finally:
            self._blank[key] = ""

    def closure(self, seeds) -> dict[str, str | None]:
        """key -> the key that reaches it first (None for a seed), breadth first."""
        parent: dict[str, str | None] = {}
        todo = collections.deque()
        for key in sorted(seeds):
            if key in self.loc:
                parent[key] = None
                todo.append(key)
        while todo:
            key = todo.popleft()
            for child in sorted(self.step(key)):
                if child not in parent:
                    parent[child] = key
                    todo.append(child)
        return parent


def _path(key: str, parent, seeds) -> tuple[str, ...]:
    chain = [key]
    while parent.get(chain[-1]) is not None:
        chain.append(parent[chain[-1]])
    return (seeds[chain[-1]],) + tuple(reversed(chain))


def _reads(value: str, pattern) -> tuple[str, ...]:
    out: list[str] = []
    for expr in _EXPR.findall(value):
        for read in pattern.findall(expr):
            if read not in out:
                out.append(read)
    return tuple(out)


def _gui_line(root: str, rel: str, key: str) -> str:
    """file:line of the first line of a .gui file that spells the key."""
    token = re.compile(rf"(?<![\w.\-]){re.escape(key)}(?![\w.\-])")
    for n, line in enumerate(h._read(os.path.join(root, rel)).split("\n"), 1):
        if token.search(line):
            return f"{rel}:{n}"
    return rel  # reached through a GetCustom entry: the file names the entry, not the key


def _tags(root: str) -> dict[str, tuple[str, int, dict]]:
    """key -> (file, line, tag) for each loc line tagged for this check."""
    out = {}
    for path in sorted(glob.glob(os.path.join(root, LOC_DIR, "**", "*.yml"), recursive=True)):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        for n, raw in enumerate(h._read(path).splitlines(), 1):
            if "REVIEWED" not in raw:
                continue
            got = split_loc_line(raw)
            m = got and _TAG.search(got[2])
            if m and CHECK in re.split(r"[\s,]+", m.group("checks").strip()):
                out[got[0]] = (rel, n, {"date": m.group("date"), "rationale": m.group("rationale").strip()})
    return out


def _is_repo(root: str) -> bool:
    return os.path.realpath(root) == os.path.realpath(h.REPO)


def repo_public_panels() -> dict[str, set[str]]:
    """Each public tab and the types National Info's mount for another country
    draws for it, from the window's registry."""
    from scripts.generators import gen_te_systems_window as gen
    return {t.key: set(gen.ni_types(t)) for t in gen.TABS if t.public}


def repo_world_loc() -> set[str]:
    """The loc keys that are world reads: BindingTest's own list."""
    from test_te_system_tab_bodies import WORLD_LOC
    return set(WORLD_LOC)


def _fresh():
    """gui_test_helpers keeps what it read; a reload must read the files again."""
    for cached in (h._loc_index, h._custom_loc, h._mod_types, h._mod_templates):
        cached.cache_clear()


def audit(mod_path: str | None = None, public_panels=None, world_loc=None) -> AuditResult:
    """Run the audit over a mod tree. `public_panels` ({tab: type names}) and
    `world_loc` (keys) default to the repo's own when the tree is the repo,
    and to none for any other tree."""
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    root = str(mod_path)
    if public_panels is None:
        public_panels = repo_public_panels() if _is_repo(root) else {}
    if world_loc is None:
        world_loc = repo_world_loc() if _is_repo(root) else set()
    _fresh()

    index = h.loc_index(os.path.join(root, LOC_DIR), root)
    if not index:
        raise FileNotFoundError(f"no loc key under {os.path.join(root, LOC_DIR)}")
    loc = {k: v for k, (v, _, _) in index.items()}
    custom = h.custom_loc(root)
    reach = Reach(loc, custom)

    status, frame = journal_seeds(root, loc)
    entry_seeds = {**block_seeds(root, "scripted_buttons", ("name", "desc"), loc), **status}
    frame_seeds = {**block_seeds(root, "scripted_progress_bars", ("name", "desc", "second_desc"), loc), **frame}
    gui_seeds, gui_files = widget_seeds(root, loc, custom)
    if not gui_files:
        raise FileNotFoundError(f"no .gui file under {os.path.join(root, 'gui')}")
    sgui_seeds = _scripted_gui_tooltip_seeds(root, loc)

    entry = reach.closure(entry_seeds)
    widget = reach.closure(gui_seeds)
    sgui = reach.closure(sgui_seeds)
    result = AuditResult(reach={ENTRY: len(entry), FRAME: len(reach.closure(frame_seeds)), WIDGET: len(widget),
                                SGUI: len(sgui)}, public_tabs=len(public_panels))
    tags = _tags(root)

    def flag(kind, key, reads, **more):
        _, path, line = index[key]
        tag = tags.get(key) if kind in TAGGABLE else None
        result.flags.append(Flag(kind, key, path, line, reads, also_sgui=key in sgui,
                                 exemption=tag[2] if tag else None, **more))

    for key in sorted(entry):
        reads = _reads(loc[key], _WIDGET_ROOT)
        if reads:
            flag(WIDGET_ROOT_IN_ENTRY, key, reads, path=_path(key, entry, entry_seeds))
    for key in sorted(widget):
        reads = _reads(loc[key], _SCRIPT_ROOT)
        if reads:
            path = _path(key, widget, gui_seeds)
            flag(SCRIPT_ROOT_IN_WIDGET, key, reads, path=(_gui_line(root, path[0], path[1]),) + path[1:])

    public: set[str] = set()
    found: dict[tuple[str, str], tuple[list[str], list[str]]] = {}
    if public_panels:
        types, templates = h.mod_types(root), h.mod_templates(root)
        for tab in sorted(public_panels):
            keys = h.panel_loc_keys(set(public_panels[tab]), types, loc, templates, custom)
            public |= keys
            for f in h.loc_reads(keys, index):
                entry_read = h.is_entry_read(f.what)
                if not entry_read and f.where in world_loc:
                    continue
                reads, tabs = found.setdefault((ENTRY_READ_ON_PUBLIC if entry_read else PLAYER_READ_ON_PUBLIC,
                                                f.where), ([], []))
                if f.what not in reads:
                    reads.append(f.what)
                if tab not in tabs:
                    tabs.append(tab)
    for (kind, key), (reads, tabs) in sorted(found.items()):
        flag(kind, key, tuple(reads), tabs=tuple(tabs))
    result.reach[PUBLIC] = len(public)

    flagged = {f.key for f in result.flags if f.kind in TAGGABLE}
    result.stale_tags = [StaleTag(rel, n, key) for key, (rel, n, _) in sorted(tags.items()) if key not in flagged]
    result.flags.sort(key=lambda f: (f.file, f.line, f.kind))
    return result


def _describe(f: Flag) -> str:
    reads = ", ".join(f"`{r}`" for r in f.reads)
    if f.tabs:
        where = "rendered by " + ", ".join(f.tabs) + (f": `python3 scripts/analysis/te_rebind_country.py {f.tabs[0]}`")
    else:
        where = "reached by " + " → ".join(f.path[:1] + tuple(f"`{k}`" for k in f.path[1:]))
    note = ("; also a scripted GUI's tooltip key, where a script root is right, so split it"
            if f.also_sgui and f.kind == SCRIPT_ROOT_IN_WIDGET else "")
    return f"`{f.key}` reads {reads} ({f.kind}); {where}{note}"


def render_report(result: AuditResult, reach: bool = False) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]
    out = [
        "# Loc root context audit report",
        "",
        "Auto-generated by `loc_root_context_audit.py` on every `POST /reload` of",
        "the mod state server. Do not hand-edit.",
        "",
        "Flagged: a loc key whose country root is wrong for a context that renders",
        "it, through `$KEY$` splices, keys named in `SelectLocalization` and",
        "`AddLocalizationIf`, and `GetCustom` entries.",
        "",
    ]
    out += [f"- `{kind}`: {why}." for kind, why in WHY.items()]
    out += [
        "",
        "A journal entry's own text (`<je>_reason`, `_goal`, `_status`, its",
        "`progress_desc`, a scripted progress bar) and a scripted GUI's tooltip keys",
        "are not judged: the module's docstring says why.",
        "",
        "Suppress a reviewed entry-text or widget case trailing on the key's loc line",
        "(no `\"` in the rationale): `# REVIEWED YYYY-MM-DD (loc_root_context): why`.",
        "A public-panel flag takes none.",
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
            out += [f"- line {f.line}: {_describe(f)}" for f in by_file[fname]]
            out.append("")

    if result.stale_tags:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` `{t.key}` ({CHECK})" for t in result.stale_tags]
        out.append("")

    out += ["## Reviewed exemptions", ""]
    if not exemp:
        out += ["_None._", ""]
    else:
        # No line number or path on a reviewed entry: an edit above it would churn the report.
        out += [f"- `{f.file}` — `{f.key}` reads {', '.join(f'`{r}`' for r in f.reads)} ({f.kind}) — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}" for f in exemp]
        out.append("")

    # Flag counts only: how many keys each context reaches moves with unrelated
    # loc, so it stays on the result, in regenerate()'s summary and in the CLI's output.
    out += [
        "## Coverage",
        "",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unrev)}",
        f"- exempted: {len(exemp)}",
        f"- stale tags: {len(result.stale_tags)}",
        "",
    ]
    if reach:
        out += ["## Reach (this run)", ""]
        out += [f"- {context}: {n} keys" + (f" ({result.public_tabs} public tabs)" if context == PUBLIC else "")
                + ("" if context in (ENTRY, WIDGET, PUBLIC) else ", not judged")
                for context, n in result.reach.items()]
        out.append("")
    return "\n".join(out) + "\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report. Reads the
    loc, script and GUI files itself, so `mod_state` is unused."""
    from path_constants import mod_path
    result = audit(mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result))
    return {
        # Flags without a tag, plus tags that suppress nothing.
        "unreviewed": result.failing,
        "total_flags": len(result.flags),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "stale_tags": len(result.stale_tags),
        "entry_text_keys": result.reach[ENTRY],
        "entry_frame_keys": result.reach[FRAME],
        "widget_keys": result.reach[WIDGET],
        "public_panel_keys": result.reach[PUBLIC],
        "scripted_gui_tooltip_keys": result.reach[SGUI],
        "public_tabs": result.public_tabs,
        "path": out_path,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 on any untagged flag or stale tag (CI mode)")
    parser.add_argument("--mod-path")
    args = parser.parse_args(argv)
    result = audit(args.mod_path)
    print(render_report(result, reach=True))
    return int(args.strict and result.failing > 0)


if __name__ == "__main__":
    raise SystemExit(main())
