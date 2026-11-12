"""What did a vanilla patch change, and does the mod use it? (`parsed` and `docs` need no vanilla clone)

The runbook's default OLD_REF is a commit in the vanilla mirror (`~/src/vic3`),
which lags the install whenever nobody has committed the last hotfixes into it.
Two artefacts already hold the *previous* version without it:

* the committed `vanilla_parsed/` snapshot (git history: `HEAD` is the version
  the mod was last migrated on), and
* the previous `script_docs` dump (`~/src/vic3-engine-docs/<old>/docs`, or a
  Modding-Digests `docs/` folder).

Subcommands:

  parsed [--old-ref REF | --old-dir DIR] [--new-dir DIR] [--out DIR] [--mod-uses]
      Per entity type, which vanilla entities were removed / added / changed
      between the old and new `vanilla_parsed/` snapshots (run
      `python3 vanilla_parsed.py build` on the new install first). With --out,
      writes `<type>.diff`: a unified diff of each changed entity rendered back
      to Paradox-like text, so "what did vanilla edit in these 57 journal
      entries" is a file to read. Also diffs English loc keys.

  docs OLD_DOCS_DIR NEW_DOCS_DIR [--show-changed] [--mod-uses]
      Section-level diff of effects.log, triggers.log, event_targets.log,
      modifiers.log and on_actions.log. The ~3,300 regional iterators
      (`every_country_in_<region>` and kin) are skipped: their descriptions leak
      unrelated script and reshuffle on every dump.

  targets OLD_REF NEW_REF [--vanilla-repo DIR] [--mod-root DIR] [--diffs replace|all|none]
      The one mode that does need the vanilla mirror: two of its commits (the
      runbook's OLD_REF and NEW_REF). It reads every top-level entry of every
      `common/` folder at both, compares them without comments and
      indentation, and lists the mod's `REPLACE:` / `INJECT:` / `TRY_*` /
      `*_OR_CREATE` and bare same-name definitions of each entry vanilla
      changed, removed or added, with file and line (the runbook's § 5 sweep).
      A key is looked up in its whole folder, so an entry vanilla moved to
      another file unchanged is not a change. The same pass lists the defines
      vanilla removed (with the mod's `define:` / `GetDefine` reads and
      `common/defines/` overrides of each), the changed defines the mod
      overrides, the vanilla events the mod redefines or (removed ones) still
      names, and vanilla's diff of each changed block the mod restates.

`--mod-uses` greps the mod (common/ events/ gui/ localization/english/) for
every REMOVED name and prints the hits; comment-only hits are counted apart.
On `parsed` it also lists the entity fields vanilla dropped from a type (no
entity of the type sets them any more: 1.15's `complete`, `on_complete`, ...)
that the mod's files of that type still set at the top level.
That join is what `/validate/vanilla-surface-diff` is meant to do, without
needing an old ref. Unit test: `test_vanilla_patch_diff.py`.
"""
import argparse
import collections
import difflib
import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import external_mod_overlap as emo  # noqa: E402
from paradox_file_parser import INJECT_DIRECTIVES, REPLACE_DIRECTIVES  # noqa: E402

# Section header per engine-doc log. effects/triggers use `## name`,
# event_targets uses `### name`, modifiers/on_actions use a `name:` line.
_DOC_HEADERS = {
    "effects.log": r"^## (\S+)\s*$",
    "triggers.log": r"^## (\S+)\s*$",
    "event_targets.log": r"^### (\S+)\s*$",
    "modifiers.log": r"^([A-Za-z0-9_]+):\s*$",
    "on_actions.log": r"^([A-Za-z0-9_]+):\s*$",
}

_REGION_ITERATOR = re.compile(r"^(every|any|random|ordered)_\w+_in_(\w+)$")
# A suffix shared by this many iterator headers is a map region, not a scope.
_REGION_SUFFIX_MIN = 8

MOD_ROOTS = ("common", "events", "gui", "localization/english")

_OPERATORS = ("=", ">", "<", ">=", "<=", "!=", "?=", "==")


# ---------------------------------------------------------------- engine docs

def load_sections(path, header):
    """{section name: normalised body} for one engine-doc log ({} if missing)."""
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read().replace("\r", "")
    sections = collections.OrderedDict()
    current = None
    for line in text.split("\n"):
        m = re.match(header, line)
        if m:
            current = m.group(1)
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line.rstrip())
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def region_suffixes(names):
    """Map-region names, read off iterator headers: `every_country_in_<region>` and
    its seven siblings put eight headers on one suffix in effects.log."""
    counts = collections.Counter(m.group(2) for n in names if (m := _REGION_ITERATOR.match(n)))
    return {suffix for suffix, n in counts.items() if n >= _REGION_SUFFIX_MIN}


def _is_region_iterator(name, suffixes):
    m = _REGION_ITERATOR.match(name)
    return bool(m and m.group(2) in suffixes)


def diff_doc_file(old_path, new_path, header, suffixes=None):
    """(removed, added, changed) name lists for one log; changed carries a diff.

    `suffixes` are the map-region names whose iterators to skip; by default they
    are read off this log's own headers, which only works for effects.log (the
    other logs carry one iterator kind per region), so `diff_docs` passes them in.
    """
    old = load_sections(old_path, header)
    new = load_sections(new_path, header)
    if suffixes is None:
        suffixes = region_suffixes(set(old) | set(new))
    skip = {n for n in set(old) | set(new) if _is_region_iterator(n, suffixes)}
    removed = sorted(k for k in set(old) - set(new) if k not in skip)
    added = sorted(k for k in set(new) - set(old) if k not in skip)
    changed = {}
    for k in old:
        if k in new and k not in skip and old[k] != new[k]:
            changed[k] = [l for l in difflib.unified_diff(
                old[k].split("\n"), new[k].split("\n"), lineterm="", n=0)
                if not l.startswith(("---", "+++", "@@"))]
    return removed, added, changed


def diff_docs(old_dir, new_dir):
    """{log file: (removed, added, changed)} for the five logs."""
    effects = _DOC_HEADERS["effects.log"]
    names = set()
    for d in (old_dir, new_dir):
        names |= set(load_sections(os.path.join(d, "effects.log"), effects))
    suffixes = region_suffixes(names)
    return {name: diff_doc_file(os.path.join(old_dir, name),
                                os.path.join(new_dir, name), header, suffixes)
            for name, header in _DOC_HEADERS.items()}


# ------------------------------------------------------------- parsed vanilla

def _is_pair(x):
    return isinstance(x, list) and len(x) == 2 and isinstance(x[0], str) and x[0] in _OPERATORS


def render_entry(key, val, indent=0):
    """Render one parsed `key -> [op, value]` (or a list of them) as Paradox-like lines."""
    tab = "\t" * indent
    if not isinstance(val, list):  # a localization value, not a parsed block
        return [f"{tab}{key} = {val}"]
    lines = []
    for pair in ([val] if _is_pair(val) else val):
        if not _is_pair(pair):
            lines.append(f"{tab}{key} <?> {json.dumps(pair)[:200]}")
            continue
        op, x = pair
        if isinstance(x, dict):
            lines.append(f"{tab}{key} {op} {{")
            for k, v in x.items():
                lines += render_entry(k, v, indent + 1)
            lines.append(tab + "}")
        elif isinstance(x, list):
            lines.append(f"{tab}{key} {op} [list] {json.dumps(x)[:300]}")
        else:
            lines.append(f"{tab}{key} {op} {x}")
    return lines


def diff_entities(old, new):
    """(removed, added, changed names, {name: unified diff lines}) between two parses."""
    removed = [k for k in old if k not in new]
    added = [k for k in new if k not in old]
    changed = [k for k in old if k in new and old[k] != new[k]]
    diffs = {}
    for k in changed:
        diffs[k] = [l for l in difflib.unified_diff(
            render_entry(k, old[k]), render_entry(k, new[k]), lineterm="", n=2)
            if not l.startswith(("---", "+++"))]
    return removed, added, changed, diffs


def _git_show_json(ref, rel_path):
    r = subprocess.run(["git", "show", f"{ref}:{rel_path}"], capture_output=True,
                       text=True, cwd=REPO_ROOT)
    return json.loads(r.stdout) if r.returncode == 0 else None


def _load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def entity_fields(data):
    """Top-level field names any entity of one parsed type sets."""
    return {k for v in data.values() if isinstance(v, list)
            for pair in ([v] if _is_pair(v) else v)
            if _is_pair(pair) and isinstance(pair[1], dict) for k in pair[1]}


def diff_parsed(new_dir, old_ref=None, old_dir=None, fields_out=None):
    """{snapshot file name: (removed, added, changed, diffs)} for changed snapshot files.

    `new_dir` is a `vanilla_parsed/`-shaped directory; the old side is either
    another such directory (`old_dir`) or the same tree at a git ref. A
    `fields_out` dict gets {snapshot file name: [fields no entity sets now]}.
    """
    out = {}
    files = sorted(glob.glob(os.path.join(new_dir, "common", "*.json"))
                   + [os.path.join(new_dir, "localization_english.json")])
    for path in files:
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, new_dir)
        if old_dir:
            old_path = os.path.join(old_dir, rel)
            old = _load_json(old_path) if os.path.isfile(old_path) else None
        else:
            old = _git_show_json(old_ref or "HEAD", "vanilla_parsed/" + rel.replace(os.sep, "/"))
        if old is None:
            out[rel] = (["<whole type absent in the old snapshot>"], [], [], {})
            continue
        new = _load_json(path)
        res = diff_entities(old, new)
        gone = sorted(entity_fields(old) - entity_fields(new))
        if fields_out is not None and gone:
            fields_out[rel] = gone
        if res[0] or res[1] or res[2]:
            out[rel] = res
    return out


# ------------------------------------------------- targets: two mirror commits
#
# The comparison takes plain {path: text} trees (`sweep_targets`), so it runs
# on anything; the git access is the few functions at the end of the section.
# Paths are relative to the mirror's `game/` folder and to the mod root, which
# have the same shape: `common/<folder>/...`, `events/...`.

EVENTS = "events"
DEFINES = "defines"
_EVENT_ID = re.compile(r"^[\w\-]+\.[\w\-]+$")
_SCRIPT_TOKEN = re.compile(r"[\w\-.]+")
_DEFINE_READS = (re.compile(r"define:(\w+)\|(\w+)"),
                 re.compile(r"GetDefine\(\s*'(\w+)'\s*,\s*'(\w+)'\s*\)"))
# Folders where a bare same-name block adds to vanilla's instead of competing
# with it (external_mod_overlap.rule_for: on_actions, history).
_MERGING_KINDS = ("on_actions", "additive")
# What the mod's files are read for: script (entries, event ids, `define:`),
# and GUI and loc for `GetDefine`.
MOD_SCAN = (("common", ".txt"), ("events", ".txt"), ("gui", ".gui"),
            ("localization/english", ".yml"))
VANILLA_ROOTS = ("game/common", "game/events")
_STATUS_ORDER = {"removed": 0, "added": 1, "changed": 2}
_MAX_RENAME_HINTS = 3


@dataclass
class Block:
    """One named entry of a script file: a top-level entry, an event, a define
    (`NBlock|KEY`) or a wrapper folder's child (a named color)."""
    key: str
    directive: Optional[str]
    line: int
    lines: list                 # its raw lines, right-stripped
    value: Optional[str]        # a scalar's value (a define's: its value or short block text)
    norm: str = ""              # what is compared

    def __post_init__(self):
        self.norm = normalise(self.lines)


def normalise(lines):
    """The lines without comments, indentation, spacing runs and blank lines:
    two blocks the engine reads alike compare equal."""
    out = []
    for raw in lines:
        code = " ".join(emo.strip_comment(raw).split())
        if code:
            out.append(code)
    return "\n".join(out)


def group_of(rel):
    """The database a script file belongs to: `common/<folder>/...` gives the
    folder as external_mod_overlap names it (`laws`, `technology/technologies`),
    `events/...` gives `events`; None for anything else."""
    if not rel.endswith(".txt"):
        return None
    top, _, rest = rel.partition("/")
    if top == EVENTS:
        return EVENTS
    if top == "common":
        split = emo.split_common_path(rest)
        return split[0] if split else None
    return None


def blocks_in(group, text):
    """The Blocks of one file of `group`. external_mod_overlap.scan_script
    finds the entries; a block's text is its lines, first to closing brace.
    A define or a wrapper's child runs to the line before the next one."""
    lines = text.lstrip("﻿").splitlines()   # as scan_script numbers them
    entries, _warnings = emo.scan_script(text)

    def span(start, end):
        return [raw.rstrip() for raw in lines[start - 1:end]]

    def children(entry):
        last = entry.end_line or len(lines)
        kids = entry.children
        for n, (raw_key, line, value) in enumerate(kids):
            if n + 1 < len(kids):
                end = kids[n + 1][1] - 1
            else:
                end = last
                if end > line and emo.strip_comment(lines[end - 1]).strip() == "}":
                    end -= 1                     # the parent's own closing brace
            directive, key = emo.split_directive(raw_key)
            yield Block(key, directive, line, span(line, max(end, line)), value)

    out = []
    wrapper = emo.WRAPPER_DIRS.get(group)
    for e in entries:
        if group == DEFINES:
            if e.value is None:
                for b in children(e):
                    b.key = f"{e.key}|{b.key}"
                    out.append(b)
        elif wrapper:
            if e.key == wrapper and e.value is None:
                out.extend(children(e))
        elif group != EVENTS or (e.value is None and _EVENT_ID.match(e.key)):
            out.append(Block(e.key, e.directive, e.line,
                             span(e.line, e.end_line or len(lines)), e.value))
    return out


def index_tree(files, cache=None, groups=None):
    """{group: {key: [(path, Block), ...]}} for a {path: text} tree, each
    key's list in path and line order. `cache` (a dict) lets two trees share
    the scan of a file they both hold; `groups` limits the scan."""
    cache = {} if cache is None else cache
    out = {}
    for path in sorted(files):
        group = group_of(path)
        if group is None or (groups is not None and group not in groups):
            continue
        text = files[path]
        if (group, text) not in cache:
            cache[(group, text)] = blocks_in(group, text)
        for block in cache[(group, text)]:
            out.setdefault(group, {}).setdefault(block.key, []).append((path, block))
    return out


def _body(group, key, blocks):
    """A key's definitions without its name, to spot the same body under a
    new name (a define's: within its `N*` block)."""
    where = key.split("|")[0] if group == DEFINES else ""
    return where, tuple(sorted(b.norm.partition(" ")[2] for _p, b in blocks))


def vanilla_delta(old_index, new_index):
    """{group: {key: {'status', 'old', 'new', 'renamed_to'}}} for every key
    whose definitions differ between two index_tree results. `status` is
    changed, added or removed; `renamed_to` lists the added keys of the group
    that carry a removed key's body (at most three)."""
    delta = {}
    for group in sorted(set(old_index) | set(new_index)):
        old, new = old_index.get(group, {}), new_index.get(group, {})
        rows = {}
        for key in sorted(set(old) | set(new)):
            o, n = old.get(key, []), new.get(key, [])
            if sorted(b.norm for _p, b in o) == sorted(b.norm for _p, b in n):
                continue
            status = "added" if not o else "removed" if not n else "changed"
            rows[key] = {"status": status, "old": o, "new": n, "renamed_to": []}
        added = collections.defaultdict(list)
        for key, row in rows.items():
            if row["status"] == "added":
                added[_body(group, key, row["new"])].append(key)
        for key, row in rows.items():
            if row["status"] == "removed":
                row["renamed_to"] = added.get(_body(group, key, row["old"]), [])[:_MAX_RENAME_HINTS]
        if rows:
            delta[group] = rows
    return delta


def consequence(status, directive, bare_rule=emo.UNKNOWN):
    """What a vanilla change of `status` does to a mod definition with
    `directive` (None: a bare same-name definition), in a few words; '' when
    the directive says it all. The directive semantics are
    external_mod_overlap.LOAD_ORDER_MODEL's `directives` and `bare_duplicate`."""
    try_form = directive in emo.TRY_FORMS
    or_create = directive in emo.OR_CREATE_DIRECTIVES
    bare = {emo.FIRST_WINS: "the first file read wins",
            emo.LAST_WINS: "the last file read wins"}.get(bare_rule, "")
    if status == "removed":
        if directive is None:
            return "the mod's is now the only definition"
        if try_form:
            return "no target now: the block is skipped, with no log line"
        if or_create:
            return "no target now: the mod's block creates the entry by itself"
        return "no target now: the engine logs an error"
    if status == "added":
        if directive is None:
            return "now a duplicate key" + (f": {bare}" if bare else "")
        if try_form:
            return "has a target now and applies"
        if or_create:
            return "lands on vanilla's entry now instead of creating one"
        return "vanilla defines its target now"
    return bare if directive is None else ""


def _vanilla_files(row):
    """The base names of the vanilla files a delta row's key is (was) in."""
    side = row["new"] or row["old"]
    return sorted({os.path.basename(p) for p, _b in side})


def _block_diff(row):
    """Unified diff of a changed key's raw lines, old to new."""
    old = [line for _p, b in row["old"] for line in b.lines]
    new = [line for _p, b in row["new"] for line in b.lines]
    return [l for l in difflib.unified_diff(old, new, lineterm="", n=3)
            if not l.startswith(("---", "+++"))]


def define_reads(mod_files, wanted):
    """{'NBlock|KEY': ['file:line', ...]} for the mod's reads of the `wanted`
    defines: `define:NBlock|KEY` in script, `GetDefine('NBlock', 'KEY')` in
    GUI and loc. Commented-out script and GUI lines don't count."""
    hits = collections.defaultdict(list)
    for path in sorted(mod_files):
        text = mod_files[path]
        if "efine" not in text:
            continue
        for lineno, raw in enumerate(text.splitlines(), 1):
            if "efine" not in raw:
                continue
            code = raw if path.endswith(".yml") else emo.strip_comment(raw)
            for pattern in _DEFINE_READS:
                for m in pattern.finditer(code):
                    name = f"{m.group(1)}|{m.group(2)}"
                    if name in wanted:
                        hits[name].append(f"{path}:{lineno}")
    return hits


def script_mentions(mod_files, wanted):
    """{name: ['file:line', ...]} for whole-token uses of the `wanted` names
    (event ids) in the mod's script, comments apart."""
    hits = collections.defaultdict(list)
    for path in sorted(mod_files):
        if group_of(path) is None:
            continue
        text = mod_files[path]
        if not wanted.intersection(_SCRIPT_TOKEN.findall(text)):
            continue
        for lineno, raw in enumerate(text.splitlines(), 1):
            for tok in _SCRIPT_TOKEN.findall(emo.strip_comment(raw)):
                if tok in wanted:
                    hits[tok].append(f"{path}:{lineno}")
    return hits


def sweep_targets(old_files, new_files, mod_files):
    """What changed in vanilla between two trees and what the mod does with it.

    `old_files` and `new_files` are {path below `game/`: text} for vanilla's
    script at the two versions (whole folders: a key is looked up across its
    folder's files), `mod_files` {path below the mod root: text}. Returns
    {'counts', 'targets', 'merged', 'defines_removed', 'defines_changed',
    'events', 'diffs'}: `counts` is {group: {status: n}}, the rest sorted lists.
    """
    cache = {}
    delta = vanilla_delta(index_tree(old_files, cache), index_tree(new_files, cache))
    mod = index_tree(mod_files, groups=set(delta))
    report = {"counts": {}, "targets": [], "merged": [], "defines_removed": [],
              "defines_changed": [], "events": [], "diffs": []}

    for group, rows in delta.items():
        report["counts"][group] = dict(collections.Counter(r["status"] for r in rows.values()))
        if group in (DEFINES, EVENTS):
            continue
        rule = emo.rule_for(group)
        merging = rule.kind in _MERGING_KINDS
        for key, row in rows.items():
            mine = mod.get(group, {}).get(key, [])
            common = {"group": group, "key": key, "status": row["status"],
                      "vanilla_files": _vanilla_files(row)}
            hooks = []
            for path, b in mine:
                if merging and b.directive is None:
                    hooks.append(f"{path}:{b.line}")
                    continue
                report["targets"].append({
                    **common, "directive": b.directive, "file": path, "line": b.line,
                    "note": consequence(row["status"], b.directive, rule.bare_duplicate),
                    "renamed_to": row["renamed_to"]})
            if hooks:
                report["merged"].append({**common, "sites": hooks})
            if mine and row["status"] == "changed":
                # Restated: a REPLACE family directive, or a bare copy that competes.
                restated = any(b.directive in REPLACE_DIRECTIVES
                               or (b.directive is None and not merging) for _p, b in mine)
                report["diffs"].append({**common, "restated": restated,
                                        "lines": _block_diff(row)})

    def rank(d):
        return 0 if d in REPLACE_DIRECTIVES else 2 if d in INJECT_DIRECTIVES else 1
    report["targets"].sort(key=lambda r: (_STATUS_ORDER[r["status"]], rank(r["directive"]),
                                          r["group"], r["key"], r["file"], r["line"]))

    defines = delta.get(DEFINES, {})
    removed = {k for k, row in defines.items() if row["status"] == "removed"}
    reads = define_reads(mod_files, removed) if removed else {}
    for name, row in defines.items():
        overrides = [{"file": p, "line": b.line, "value": b.value}
                     for p, b in mod.get(DEFINES, {}).get(name, [])]
        old = row["old"][-1][1].value if row["old"] else None
        new = row["new"][-1][1].value if row["new"] else None
        if row["status"] == "removed":
            report["defines_removed"].append({
                "define": name, "status": "removed", "old": old,
                "vanilla_files": _vanilla_files(row),
                "renamed_to": row["renamed_to"], "overrides": overrides,
                "reads": reads.get(name, [])})
        elif row["status"] == "changed" and overrides:
            report["defines_changed"].append({
                "define": name, "old": old, "new": new, "overrides": overrides})

    events = delta.get(EVENTS, {})
    gone = {k for k, row in events.items() if row["status"] == "removed"}
    mentions = script_mentions(mod_files, gone) if gone else {}
    for event_id, row in events.items():
        defs = [f"{p}:{b.line}" for p, b in mod.get(EVENTS, {}).get(event_id, [])]
        names = [site for site in mentions.get(event_id, []) if site not in defs]
        if defs or names:
            report["events"].append({
                "id": event_id, "status": row["status"], "vanilla_files": _vanilla_files(row),
                "redefined": defs, "named": names})
    return report


def _where(row):
    word = {"changed": "changed in", "added": "added in", "removed": "removed from"}[row["status"]]
    return f"{word} {', '.join(row['vanilla_files'])}"


def _sites(sites, limit=3):
    more = f" (+{len(sites) - limit} more)" if len(sites) > limit else ""
    return ", ".join(sites[:limit]) + more


def format_targets(report, diffs="replace"):
    """The report as text lines. `diffs`: `replace` prints vanilla's diff of
    each changed entry the mod restates (a REPLACE family directive or a bare
    copy), `all` of every changed entry the mod defines, `none` of none."""
    out = []
    folders = {g: c for g, c in report["counts"].items() if g != EVENTS}
    totals = collections.Counter()
    for counts in folders.values():
        totals.update(counts)
    out.append(f"top-level entries of vanilla's common/ (a define counts as one): "
               f"{totals['changed']} changed, {totals['added']} added, "
               f"{totals['removed']} removed in {len(folders)} folder(s)")
    if folders:
        out.append("  " + ", ".join(f"{g} {sum(c.values())}" for g, c in sorted(folders.items())))
    events = report["counts"].get(EVENTS, {})
    out.append(f"vanilla events: {events.get('changed', 0)} changed, {events.get('added', 0)} "
               f"added, {events.get('removed', 0)} removed")

    out.append(f"\n== the mod's definitions of those entries: {len(report['targets'])}")
    for r in report["targets"]:
        notes = [_where(r)]
        if r["renamed_to"]:
            notes.append("same body now under " + ", ".join(r["renamed_to"]))
        if r["note"]:
            notes.append(r["note"])
        out.append(f"{r['directive'] or 'bare':<17}  {r['group']}/{r['key']}  "
                   f"{r['file']}:{r['line']}  ({'; '.join(notes)})")

    out.append("\n== on_actions and history blocks the mod also adds to "
               f"(the blocks merge): {len(report['merged'])}")
    for r in report["merged"]:
        out.append(f"{r['group']}/{r['key']}  ({_where(r)})  {len(r['sites'])} mod block(s): "
                   f"{_sites(r['sites'])}")

    out.append(f"\n== defines vanilla removed: {len(report['defines_removed'])}")
    for d in report["defines_removed"]:
        hint = (f"; same value now under {', '.join(n.split('|')[1] for n in d['renamed_to'])}"
                if d["renamed_to"] else "")
        used = "" if d["overrides"] or d["reads"] else "  the mod neither sets nor reads it"
        out.append(f"{d['define']} = {d['old']}  ({_where(d)}{hint}){used}")
        for o in d["overrides"]:
            out.append(f"    set   {o['file']}:{o['line']}  = {o['value']}")
        for site in d["reads"]:
            out.append(f"    read  {site}")

    out.append(f"\n== changed defines the mod sets: {len(report['defines_changed'])}")
    for d in report["defines_changed"]:
        for o in d["overrides"]:
            out.append(f"{d['define']}  {d['old']} -> {d['new']}  "
                       f"{o['file']}:{o['line']}  = {o['value']}")

    out.append("\n== vanilla events the mod redefines, or names though vanilla removed them: "
               f"{len(report['events'])}")
    for e in report["events"]:
        for site in e["redefined"]:
            out.append(f"redefined  {e['id']}  {site}  ({_where(e)})")
        for site in e["named"]:
            out.append(f"named      {e['id']}  {site}  ({_where(e)})")

    shown = [d for d in report["diffs"] if diffs == "all" or (diffs == "replace" and d["restated"])]
    if diffs != "none":
        what = "the mod restates (REPLACE or a bare copy), to port" if diffs == "replace" \
            else "the mod defines"
        out.append(f"\n== vanilla's diff of each changed entry {what}: {len(shown)}")
        for d in shown:
            out.append(f"@@@@@@ {d['group']}/{d['key']}  ({_where(d)})")
            out.extend(d["lines"])
    return out


def read_mod_tree(mod_root):
    """{path below the mod root: text} for the files MOD_SCAN names."""
    out = {}
    for top, ext in MOD_SCAN:
        for rel in emo.list_files(mod_root, top):
            if rel.endswith(ext):
                out[rel] = emo.read_text(os.path.join(mod_root, *rel.split("/")))
    return out


class GitError(RuntimeError):
    """A git command on the vanilla mirror failed."""


def _git(repo, *args, stdin=None):
    try:
        r = subprocess.run(["git", "-C", repo, *args], input=stdin, capture_output=True)
    except OSError as exc:
        raise GitError(f"could not run git: {exc}") from exc
    if r.returncode != 0:
        detail = r.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(f"`git {args[0]}` failed in {repo}" + (f": {detail}" if detail else ""))
    return r.stdout


def resolve_commit(repo, ref):
    """The commit SHA `ref` names in `repo` (GitError when it names none)."""
    if ref.startswith("-"):
        raise GitError(f"not a ref: {ref!r}")
    try:
        return _git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}").decode().strip()
    except GitError as exc:
        if os.path.isdir(repo):
            raise GitError(f"no commit {ref!r} in {repo}") from exc
        raise


def ls_tree(repo, commit, roots=VANILLA_ROOTS):
    """{path below `game/`: blob SHA} for the .txt files under `roots` at `commit`."""
    tree = {}
    for record in _git(repo, "ls-tree", "-r", "-z", commit, "--", *roots).split(b"\0"):
        meta, _, path = record.partition(b"\t")
        if not path.endswith(b".txt") or meta.split()[1] != b"blob":
            continue
        tree[path.decode("utf-8", errors="replace").partition("/")[2]] = meta.split()[2].decode()
    return tree


def read_blobs(repo, shas):
    """{blob SHA: text} from one `git cat-file --batch` (BOM dropped)."""
    shas = list(shas)
    out = _git(repo, "cat-file", "--batch", stdin=("\n".join(shas) + "\n").encode()) if shas else b""
    texts, pos = {}, 0
    for sha in shas:
        eol = out.index(b"\n", pos)
        header = out[pos:eol].split()
        if len(header) != 3 or header[1] != b"blob":
            raise GitError(f"`git cat-file` could not read {sha} in {repo}")
        size = int(header[2])
        texts[sha] = out[eol + 1:eol + 1 + size].decode("utf-8-sig", errors="replace")
        pos = eol + 1 + size + 1
    return texts


def read_vanilla_pair(repo, old_ref, new_ref):
    """(old files, new files, number of files that differ): vanilla's script at
    two commits of the mirror as {path below `game/`: text}, for every file of
    each folder in which some file differs (the folders `sweep_targets` needs)."""
    old_tree = ls_tree(repo, resolve_commit(repo, old_ref))
    new_tree = ls_tree(repo, resolve_commit(repo, new_ref))
    differing = [p for p in set(old_tree) | set(new_tree) if old_tree.get(p) != new_tree.get(p)]
    groups = {group_of(p) for p in differing} - {None}
    old_tree = {p: sha for p, sha in old_tree.items() if group_of(p) in groups}
    new_tree = {p: sha for p, sha in new_tree.items() if group_of(p) in groups}
    texts = read_blobs(repo, sorted(set(old_tree.values()) | set(new_tree.values())))
    return ({p: texts[sha] for p, sha in old_tree.items()},
            {p: texts[sha] for p, sha in new_tree.items()}, len(differing))


# -------------------------------------------------------------------- mod uses

def mod_uses(names, repo=REPO_ROOT):
    """{name: {'code': [file:line, ...], 'comment': n}} for names the mod mentions."""
    hits = {}
    for name in sorted(set(names)):
        r = subprocess.run(["git", "grep", "-n", "-w", "-F", name, "--", *MOD_ROOTS],
                           capture_output=True, text=True, cwd=repo)
        code, comment = [], 0
        for line in r.stdout.splitlines():
            path, lineno, text = line.split(":", 2)
            if text.lstrip().startswith("#"):
                comment += 1
            else:
                code.append(f"{path}:{lineno}")
        if code or comment:
            hits[name] = {"code": code, "comment": comment}
    return hits


def mod_field_uses(fields_by_file, new_dir, repo=REPO_ROOT):
    """{(mod dir, field): [file:line, ...]} for removed fields that the mod's
    files of the same type set at entity level (one tab in)."""
    types = _load_json(os.path.join(new_dir, "manifest.json"))["entity_types"].values()
    dirs = {t["file"]: t["dir"].split("/", 1)[1] for t in types}
    hits = {}
    for rel, fields in fields_by_file.items():
        mod_dir = dirs.get(rel.replace(os.sep, "/"))
        for field in fields if mod_dir else ():
            r = subprocess.run(["git", "grep", "-n", "-E", "^\t" + re.escape(field) + r"\s*=",
                                "--", mod_dir], capture_output=True, text=True, cwd=repo)
            code = [":".join(line.split(":", 2)[:2]) for line in r.stdout.splitlines()]
            if code:
                hits[(mod_dir, field)] = code
    return hits


def print_mod_uses(names):
    hits = mod_uses(names)
    print(f"\n== removed names the mod mentions: {len(hits)} of {len(set(names))}")
    for name, h in hits.items():
        more = f" (+{len(h['code']) - 3} more)" if len(h["code"]) > 3 else ""
        print(f"  {name}: {len(h['code'])} code hit(s), {h['comment']} comment-only"
              f"{'  ' + ', '.join(h['code'][:3]) + more if h['code'] else ''}")


# ------------------------------------------------------------------------- CLI

def _cmd_docs(args):
    results = diff_docs(args.old, args.new)
    removed_names = []
    for name, (removed, added, changed) in results.items():
        print(f"##### {name}: removed {len(removed)}, added {len(added)}, changed {len(changed)}")
        if removed:
            print("  REMOVED:", ", ".join(removed))
        if added:
            print("  ADDED:  ", ", ".join(added))
        for k, lines in changed.items():
            print(f"  CHANGED: {k}")
            if args.show_changed:
                for line in lines[:20]:
                    print("      " + line[:200])
        removed_names += removed
    if args.mod_uses:
        print_mod_uses(removed_names)
    return 0


def _cmd_parsed(args):
    new_dir = os.path.join(REPO_ROOT, args.new_dir)
    removed_fields = {}
    results = diff_parsed(new_dir, old_ref=args.old_ref, old_dir=args.old_dir,
                          fields_out=removed_fields)
    removed_names = []
    if args.out:
        os.makedirs(args.out, exist_ok=True)
    for rel, (removed, added, changed, diffs) in sorted(results.items()):
        print(f"{rel:42s} removed={len(removed):4d} added={len(added):4d} changed={len(changed):4d}")
        removed_names += [r for r in removed if not r.startswith("<")]
        if not args.out:
            continue
        stem = os.path.splitext(os.path.basename(rel))[0]
        with open(os.path.join(args.out, stem + ".diff"), "w", encoding="utf-8") as fh:
            fh.write(f"REMOVED: {removed}\nADDED: {added}\nCHANGED: {changed}\n\n")
            for k in changed:
                fh.write(f"@@@@@@ {k}\n" + "\n".join(diffs[k]) + "\n")
    if args.mod_uses:
        print_mod_uses(removed_names)
        hits = mod_field_uses(removed_fields, new_dir)
        print(f"\n== removed fields the mod still sets: {len(hits)}")
        for (mod_dir, field), code in sorted(hits.items()):
            more = f" (+{len(code) - 3} more)" if len(code) > 3 else ""
            print(f"  {mod_dir}: {field}: {len(code)} hit(s)  {', '.join(code[:3])}{more}")
    return 0


def _cmd_targets(args):
    repo = args.vanilla_repo
    if not repo:
        import path_constants
        repo = path_constants.vanilla_source_repo_path
    if not os.path.isdir(repo):
        print(f"no vanilla mirror at {repo} (path_constants.vanilla_source_repo_path; "
              "name another with --vanilla-repo)", file=sys.stderr)
        return 2
    try:
        old_files, new_files, differing = read_vanilla_pair(repo, args.old_ref, args.new_ref)
    except GitError as exc:
        print(exc, file=sys.stderr)
        return 2
    report = sweep_targets(old_files, new_files, read_mod_tree(args.mod_root))
    print(f"vanilla {args.old_ref} -> {args.new_ref} ({repo}): {differing} script file(s) differ")
    print("\n".join(format_targets(report, args.diffs)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parsed", help="diff two vanilla_parsed/ snapshots")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--old-ref", default="HEAD", help="git ref holding the old vanilla_parsed/ (default HEAD)")
    src.add_argument("--old-dir", help="a directory shaped like vanilla_parsed/ instead of a git ref")
    p.add_argument("--new-dir", default="vanilla_parsed", help="new snapshot, relative to the repo root")
    p.add_argument("--out", help="write a <type>.diff per changed type into this directory")
    p.add_argument("--mod-uses", action="store_true", help="grep the mod for removed entity names and fields")
    p.set_defaults(func=_cmd_parsed)
    d = sub.add_parser("docs", help="diff two script_docs dumps")
    d.add_argument("old", help="old docs dir (holds effects.log, triggers.log, ...)")
    d.add_argument("new", help="new docs dir")
    d.add_argument("--show-changed", action="store_true", help="print the changed lines of each changed section")
    d.add_argument("--mod-uses", action="store_true", help="grep the mod for removed names")
    d.set_defaults(func=_cmd_docs)
    t = sub.add_parser("targets", help="what two commits of the vanilla mirror changed under the "
                                       "mod's REPLACE/INJECT targets, defines and events")
    t.add_argument("old_ref", help="the mirror commit of the version the mod was last migrated on")
    t.add_argument("new_ref", help="the mirror commit of the new version")
    t.add_argument("--vanilla-repo", help="the vanilla mirror clone "
                                          "(default: path_constants.vanilla_source_repo_path)")
    t.add_argument("--mod-root", default=REPO_ROOT, help="the mod to check (default: this repository)")
    t.add_argument("--diffs", choices=("replace", "all", "none"), default="replace",
                   help="which changed entries to print vanilla's diff of: those the mod restates "
                        "(default), every one the mod defines, or none")
    t.set_defaults(func=_cmd_targets)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
