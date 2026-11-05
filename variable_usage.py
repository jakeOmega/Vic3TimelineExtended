"""Every site in the mod that reads, writes or iterates a variable or variable
list (#973), for `GET /variable-usage/<name>` and the CLI below.

`/references/<key>` names the entities that mention a key. This index says how
each site uses it: `set_variable`, `has_variable`, a `var:` read, an
`every_in_list = { variable = ... }` walker and the `limit` it filters by, a
`GetList('...')` in a `.gui` file. The covert Counterintelligence Support work
needed exactly that ("does every `iw_ops` walker exclude friendly ops?") and
swept 47 walkers by hand.

Raw text, not `paradox_file_parser`, so every site keeps its file and line.
Comments are blanked first (`script_helper_index.blank_comments`). Scanned, mod
only:

  * `common/` and `events/` (`.txt`): every variable and variable-list effect
    and trigger, scope (`set_variable`), global (`set_global_variable`) and
    local (`set_local_variable`) alike, in its value form
    (`has_variable = x`) or block form (`set_variable = { name = x ... }`);
    the `*_in_list` / `*_in_global_list` / `*_in_local_list` iterators with
    `variable = x` (`list = x` walks a temporary list, not a variable, and is
    left out); and `var:x` / `global_var:x` / `local_var:x` reads.
  * `gui/` (`.gui`) and `localization/english/` (`.yml`), plus any quoted
    string in script: data-function reads such as `MakeScope.Var('x')`,
    `GetList('x')`, `HasVariable('x')` and `GetGlobalVariable('x')`.

Each variable lives in one of three stores, reported per site as `store`
(`scope`, `global`, `local`), so `var:x` and `global_var:x` are not mixed up;
`kind` is `var` or `list`, and `access` is `write`, `read` or `iterate`.

A name built from a parameter (`te_$KIND$_count`) is indexed as written. A
query matches it as a pattern (each `$X$` stands for any run of name
characters) and the site carries `pattern`. A name that is nothing but a
parameter (`name = $NAME$`) would match every query, so it is not matched;
`/script-args/<helper>` lists what its callers pass.

`scope_hint` is the innermost enclosing block that changes scope (an
iterator, `scope:x`, `owner`, any engine link), or the explicit chain in front
of a `var:` read (`scope:actor` for `scope:actor.var:x`); `null` when the site
sits in its entity's root scope. A list iterator shows the list it walks, as
`every_in_list(iw_ops)`. It is lexical, not scope inference.

`unfiltered` answers "does every walker of this list filter by trigger T?":
the iteration sites whose `limit` (for an `any_*` trigger, its whole body) names
neither T nor a mod scripted trigger that names T, directly or through other
scripted triggers. Each such site says whether T is named elsewhere in its
body (`named_in_body`, e.g. an `if = { limit = { T = yes } }` inside the
loop). Naming is textual: `NOT = { T = yes }` counts as naming T.

    python3 variable_usage.py iw_ops [--kind list] [--unfiltered-by covert_op_is_hostile]
    python3 variable_usage.py --names [--prefix iw_]
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from bisect import bisect_right
from dataclasses import dataclass, field

from prev_scope_audit import _is_scope_change, load_links
from paradox_file_parser import directive_prefixes
from script_helper_index import blank_comments, line_of, line_starts

SCRIPT_DIRS = ("common", "events")
GUI_DIR = "gui"
LOC_DIR = os.path.join("localization", "english")

# key -> (access, kind, store). `name = x` names the variable in a block form.
_OPS: dict[str, tuple[str, str, str]] = {}
for _store, _infix, _list_infix in (("scope", "", ""), ("global", "global_", "global_"),
                                    ("local", "local_", "local_")):
    for _verb in ("set", "change", "clamp", "round", "remove"):
        _OPS[f"{_verb}_{_infix}variable"] = ("write", "var", _store)
    _OPS[f"has_{_infix}variable"] = ("read", "var", _store)
    _OPS[f"add_to_{_list_infix}variable_list"] = ("write", "list", _store)
    _OPS[f"remove_list_{_infix}variable"] = ("write", "list", _store)
    _OPS[f"clear_{_list_infix}variable_list"] = ("write", "list", _store)
    _OPS[f"has_{_list_infix}variable_list"] = ("read", "list", _store)
    _OPS[f"is_target_in_{_list_infix}variable_list"] = ("read", "list", _store)
    _OPS[f"{_list_infix}variable_list_size"] = ("read", "list", _store)

# Iterators over a variable list; `variable = x` names it.
_ITERATORS: dict[str, str] = {}
for _store, _suffix in (("scope", "in_list"), ("global", "in_global_list"),
                        ("local", "in_local_list")):
    for _prefix in ("every", "random", "any", "ordered"):
        _ITERATORS[f"{_prefix}_{_suffix}"] = _store

_VAR_READ_STORE = {"var": "scope", "global_var": "global", "local_var": "local"}

# One pass over comment- and string-blanked script: a close, an unattributed
# open, or `key [op [value | {]]`.
_TOKEN_RE = re.compile(
    r"(?P<close>\})|(?P<anon>\{)"
    r"|(?P<key>[A-Za-z_@$][A-Za-z0-9_.:|@$\-]*)"
    r"(?:\s*(?P<op>\?=|[!<>=]=|[=<>])\s*"
    r"(?:(?P<open>\{)|(?P<value>[A-Za-z0-9_.:@$\-]+))?)?"
)
_QUOTED_RE = re.compile(r'"([^"\n]*)"')
# One `.`-separated link of a token that reads a variable: `var:x` in
# `scope:actor.var:x`, both reads in `var:a.var:b`, `global_var:x`.
_VAR_LINK_RE = re.compile(r"(?P<pfx>global_var|local_var|var):(?P<name>[A-Za-z0-9_$]+)")
# Data functions in GUI and loc text: `Var('x')`, `GetList('x')`,
# `HasVariable('x')`, `GetGlobalVariable('x')`, ...
_DATA_FN_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<fn>(?:Get|Has)?(?:Global|Local)?(?:Var|Variable|VariableList|List))"
    r"\(\s*'(?P<name>[A-Za-z0-9_$]+)'\s*\)"
)
_LOC_KEY_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+):\d*\s")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PARAM_RE = re.compile(r"\$[A-Za-z0-9_]+\$")
# The six merge directives (paradox_file_parser.directive_prefixes).
_MERGE_PREFIX_RE = re.compile(r"^(?:" + "|".join(map(re.escape, directive_prefixes)) + ")")
# A file with none of these has no site; skip tokenizing it.
_SCRIPT_HINT_RE = re.compile(r"variable|in_list|in_global_list|in_local_list|var:|'\)")

_LIMIT_TEXT_MAX = 600

_ENTITY_TYPES = {
    "scripted_guis": "Scripted GUIs",
}


@dataclass
class Site:
    file: str
    line: int
    entity: str | None
    entity_type: str
    op: str
    access: str  # write | read | iterate
    kind: str  # var | list
    store: str  # scope | global | local
    name: str  # as written; may hold $PARAM$ placeholders
    scope_hint: str | None = None
    limit: str | None = None  # iterate only: the limit (any_*: the body)
    body_idents: frozenset = field(default_factory=frozenset, repr=False)

    def to_dict(self) -> dict:
        out = {
            "file": self.file, "line": self.line, "entity": self.entity,
            "entity_type": self.entity_type, "op": self.op, "access": self.access,
            "kind": self.kind, "store": self.store, "scope_hint": self.scope_hint,
        }
        if self.access == "iterate":
            limit = self.limit
            if limit is not None and len(limit) > _LIMIT_TEXT_MAX:
                limit = limit[:_LIMIT_TEXT_MAX] + " …"
            out["limit"] = limit
        return out


@dataclass
class Index:
    sites: dict[str, list[Site]] = field(default_factory=dict)  # name as written
    # Mod scripted trigger -> identifiers its body names, for the transitive
    # `unfiltered_by` check.
    trigger_idents: dict[str, frozenset] = field(default_factory=dict)
    files_scanned: int = 0

    def add(self, site: Site) -> None:
        self.sites.setdefault(site.name, []).append(site)


def _entity_type(rel: str) -> str:
    parts = rel.replace("\\", "/").split("/")
    if parts[0] == "events":
        return "Events"
    if parts[0] == "gui":
        return "GUI"
    if parts[0] == "localization":
        return "Localization"
    if parts[0] == "common" and len(parts) > 2:
        sub = parts[1]
        return _ENTITY_TYPES.get(sub, sub.replace("_", " ").title())
    return parts[0]


def _flatten(text: str) -> str:
    return " ".join(text.split())


def _data_fn_sites(text: str, rel: str, prefix: str, starts: list[int],
                   entity_at=None) -> list[Site]:
    out = []
    etype = _entity_type(rel)
    for m in _DATA_FN_RE.finditer(text):
        fn = m.group("fn")
        store = "global" if "Global" in fn else "local" if "Local" in fn else "scope"
        line = line_of(starts, m.start())
        out.append(Site(
            file=rel, line=line, entity=entity_at(line) if entity_at else None,
            entity_type=etype, op=f"{prefix}_{fn}", access="read",
            kind="list" if fn.endswith("List") else "var", store=store,
            name=m.group("name"),
        ))
    return out


def scan_script(text: str, rel: str, links: set[str],
                trigger_idents: dict[str, frozenset] | None = None) -> list[Site]:
    """Every variable site in one `.txt` script file. With `trigger_idents`,
    a scripted-trigger file's depth-0 bodies are also recorded there."""
    no_comments, clean = blank_comments(text)
    starts = line_starts(clean)
    sites: list[Site] = []
    etype = _entity_type(rel)
    # Frame: key, line, open (offset of `{`), and for an op/iterator block the
    # name it names, plus an iterator's limit span.
    stack: list[dict] = []
    entity: str | None = None
    entity_lines: list[tuple[int, str]] = []  # (first line, entity) for quoted reads

    def scope_hint() -> str | None:
        for fr in reversed(stack[1:]):
            key = fr["key"]
            if key is None:
                continue
            if key in _ITERATORS:
                return f"{key}({fr['name']})" if fr.get("name") else key
            if _is_scope_change(key, links):
                return key
        return None

    for m in _TOKEN_RE.finditer(clean):
        if m.group("close"):
            if not stack:
                continue
            fr = stack.pop()
            parent = stack[-1] if stack else None
            if parent is not None and fr["key"] == "limit" and parent.get("iterator"):
                parent["limit_span"] = (fr["open"] + 1, m.start())
            if fr.get("op") and fr.get("name"):
                sites.append(_block_site(fr, rel, etype, no_comments, m.start()))
            if not stack and trigger_idents is not None and fr["key"]:
                trigger_idents[fr["key"]] = frozenset(
                    _IDENT_RE.findall(no_comments[fr["open"] + 1:m.start()]))
            continue
        if m.group("anon"):
            stack.append({"key": None, "line": line_of(starts, m.start()),
                          "open": m.start()})
            continue

        key = m.group("key")
        line = line_of(starts, m.start("key"))
        parent = stack[-1] if stack else None
        value = m.group("value")
        if m.group("op") and not value and not m.group("open"):
            q = _QUOTED_RE.match(no_comments, m.end())
            if q:
                value = q.group(1).strip() or None

        value_at = m.start("value") if m.group("value") else m.end()
        for tok, at in ((key, m.start("key")), (value, value_at)):
            if not tok or ":" not in tok:
                continue
            links_ = tok.split(".")
            for i, link in enumerate(links_):
                r = _VAR_LINK_RE.match(link)
                if not r:
                    continue
                sites.append(Site(
                    rel, line_of(starts, at), entity, etype, r.group("pfx") + "_read",
                    "read", "var", _VAR_READ_STORE[r.group("pfx")], r.group("name"),
                    ".".join(links_[:i]) if i else scope_hint()))

        if parent is None:
            if m.group("open"):
                entity = _MERGE_PREFIX_RE.sub("", key)
                entity_lines.append((line, entity))
                stack.append({"key": entity, "line": line, "open": m.start("open")})
            continue

        # A block op's or iterator's naming child.
        if value and parent.get("op") and parent.get("name") is None:
            if (key == "name" and not parent.get("iterator")) or (
                    key == "variable" and parent.get("iterator")):
                parent["name"] = value

        if key in _OPS and m.group("op"):
            access, kind, store = _OPS[key]
            if m.group("open"):
                stack.append({"key": key, "line": line, "open": m.start("open"),
                              "op": (access, kind, store), "name": None,
                              "entity": entity, "scope_hint": scope_hint()})
                continue
            if value:
                sites.append(Site(rel, line, entity, etype, key, access, kind, store,
                                  value, scope_hint()))
            continue
        if key in _ITERATORS and m.group("open"):
            stack.append({"key": key, "line": line, "open": m.start("open"),
                          "op": ("iterate", "list", _ITERATORS[key]), "name": None,
                          "iterator": True, "entity": entity,
                          "scope_hint": scope_hint()})
            continue
        if m.group("open"):
            stack.append({"key": key, "line": line, "open": m.start("open")})

    # Data functions inside quoted strings (custom tooltips, scripted GUI
    # texts) belong to the entity whose opener precedes them.
    entity_firsts = [first for first, _name in entity_lines]

    def entity_at(line: int) -> str | None:
        i = bisect_right(entity_firsts, line)
        return entity_lines[i - 1][1] if i else None

    sites.extend(_data_fn_sites(no_comments, rel, "loc", starts, entity_at))
    return sites


def _block_site(fr: dict, rel: str, etype: str, no_comments: str, close: int) -> Site:
    access, kind, store = fr["op"]
    limit = None
    idents: frozenset = frozenset()
    if access == "iterate":
        body = no_comments[fr["open"] + 1:close]
        idents = frozenset(_IDENT_RE.findall(body))
        span = fr.get("limit_span")
        if fr["key"].startswith("any_"):
            # An any_* trigger takes no limit; its body is the condition.
            limit = _flatten(re.sub(r"\bvariable\s*=\s*\S+", "", body)) or None
        elif span:
            limit = _flatten(no_comments[span[0]:span[1]]) or None
    return Site(rel, fr["line"], fr["entity"], etype, fr["key"], access, kind, store,
                fr["name"], fr["scope_hint"], limit, idents)


def build_index(mod_path: str) -> Index:
    index = Index()
    links = load_links(mod_path)
    for top in SCRIPT_DIRS:
        root = os.path.join(mod_path, top)
        for dirpath, _dirs, files in os.walk(root):
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                path = os.path.join(dirpath, fname)
                rel = os.path.relpath(path, mod_path).replace(os.sep, "/")
                text = _read(path)
                if text is None:
                    continue
                is_trigger_file = rel.startswith("common/scripted_triggers/")
                if not is_trigger_file and not _SCRIPT_HINT_RE.search(text):
                    continue
                index.files_scanned += 1
                for site in scan_script(text, rel, links,
                                        index.trigger_idents if is_trigger_file else None):
                    index.add(site)
    for top, ext, prefix in ((GUI_DIR, ".gui", "gui"), (LOC_DIR, ".yml", "loc")):
        root = os.path.join(mod_path, top)
        for dirpath, _dirs, files in os.walk(root):
            for fname in sorted(files):
                if not fname.endswith(ext):
                    continue
                path = os.path.join(dirpath, fname)
                rel = os.path.relpath(path, mod_path).replace(os.sep, "/")
                text = _read(path)
                if text is None or "('" not in text:
                    continue
                index.files_scanned += 1
                for site in scan_markup(text, rel, prefix):
                    index.add(site)
    return index


def scan_markup(text: str, rel: str, prefix: str) -> list[Site]:
    """Data-function reads in one `.gui` (`prefix="gui"`) or loc `.yml`
    (`prefix="loc"`) file. A loc site's entity is the key on its line."""
    if prefix == "loc":
        # Loc values are quoted and `#` inside them is markup, not a comment.
        no_comments = "\n".join("" if ln.lstrip().startswith("#") else ln
                                for ln in text.split("\n"))
    else:
        no_comments, _clean = blank_comments(text)
    starts = line_starts(no_comments)
    lines = no_comments.split("\n") if prefix == "loc" else None

    def loc_key(line: int) -> str | None:
        m = _LOC_KEY_RE.match(lines[line - 1]) if lines else None
        return m.group(1) if m else None

    return _data_fn_sites(no_comments, rel, prefix, starts,
                          loc_key if prefix == "loc" else None)


def _read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _template_regex(name: str) -> re.Pattern | None:
    """A regex for a `$PARAM$` name, or None for a name that is only
    parameters (it would match anything)."""
    parts = _PARAM_RE.split(name)
    if not "".join(parts):
        return None
    return re.compile("[A-Za-z0-9_]+".join(re.escape(p) for p in parts) + r"\Z")


def lookup(index: Index, name: str, patterns: bool = True) -> list[tuple[Site, str | None]]:
    """(site, pattern) for every site naming `name`: exact first, then the
    `$PARAM$` names it fits (`pattern` is that name as written)."""
    out = [(s, None) for s in index.sites.get(name, [])]
    if patterns:
        for written, sites in index.sites.items():
            if "$" not in written:
                continue
            rx = _template_regex(written)
            if rx is not None and rx.match(name):
                out.extend((s, written) for s in sites)
    return out


def trigger_wrappers(index: Index, trigger: str) -> list[str]:
    """Mod scripted triggers that name `trigger`, directly or through other
    scripted triggers."""
    found = {trigger}
    changed = True
    while changed:
        changed = False
        for name, idents in index.trigger_idents.items():
            if name not in found and idents & found:
                found.add(name)
                changed = True
    found.discard(trigger)
    return sorted(found)


def usage(index: Index, name: str, kind: str | None = None, store: str | None = None,
          unfiltered_by: str | None = None, patterns: bool = True) -> dict | None:
    """The `/variable-usage/<name>` payload, or None when nothing names it."""
    matched = lookup(index, name, patterns)
    if not matched:
        return None
    if kind:
        matched = [(s, p) for s, p in matched if s.kind == kind]
    if store:
        matched = [(s, p) for s, p in matched if s.store == store]
    matched.sort(key=lambda sp: (sp[0].file, sp[0].line))

    iterations = [s for s, _p in matched if s.access == "iterate"]
    summary = {
        "writes": sum(1 for s, _p in matched if s.access == "write"),
        "reads": sum(1 for s, _p in matched if s.access == "read"),
        "iterations": len(iterations),
        "iterations_without_limit": sum(1 for s in iterations if not s.limit),
        "pattern_sites": sum(1 for _s, p in matched if p),
    }
    out: dict = {"name": name, "kind": kind, "store": store}

    def row(site: Site, pattern: str | None) -> dict:
        d = site.to_dict()
        if pattern:
            d["pattern"] = pattern
        return d

    if unfiltered_by:
        wrappers = trigger_wrappers(index, unfiltered_by)
        names = {unfiltered_by, *wrappers}
        rows = []
        for site, pattern in matched:
            if site.access != "iterate":
                continue
            limit_idents = set(_IDENT_RE.findall(site.limit or ""))
            if limit_idents & names:
                continue
            d = row(site, pattern)
            d["named_in_body"] = bool(site.body_idents & names)
            rows.append(d)
        summary["unfiltered"] = len(rows)
        out["unfiltered_by"] = {"trigger": unfiltered_by, "wrappers": wrappers}
        out["sites"] = rows
    else:
        out["sites"] = [row(s, p) for s, p in matched]
    out["summary"] = summary
    return out


def names(index: Index, prefix: str | None = None, kind: str | None = None) -> dict:
    """The bare `/variable-usage` payload: every name with its counts. A
    `prefix` may hold `*` / `?` wildcards."""
    rows = []
    for name, sites in sorted(index.sites.items()):
        if prefix and not (name.startswith(prefix) or fnmatch.fnmatchcase(name, prefix)):
            continue
        if kind:
            sites = [s for s in sites if s.kind == kind]
            if not sites:
                continue
        rows.append({
            "name": name,
            "kinds": sorted({s.kind for s in sites}),
            "stores": sorted({s.store for s in sites}),
            "writes": sum(1 for s in sites if s.access == "write"),
            "reads": sum(1 for s in sites if s.access == "read"),
            "iterations": sum(1 for s in sites if s.access == "iterate"),
        })
    return {"files_scanned": index.files_scanned, "count": len(rows), "names": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("name", nargs="?")
    ap.add_argument("--kind", choices=("var", "list"))
    ap.add_argument("--store", choices=("scope", "global", "local"))
    ap.add_argument("--unfiltered-by", metavar="TRIGGER")
    ap.add_argument("--no-patterns", action="store_true")
    ap.add_argument("--names", action="store_true", help="list every name with its counts")
    ap.add_argument("--prefix")
    args = ap.parse_args(argv)
    from path_constants import mod_path
    index = build_index(mod_path)
    if args.names or not args.name:
        print(json.dumps(names(index, args.prefix, args.kind), indent=1))
        return 0
    out = usage(index, args.name, args.kind, args.store, args.unfiltered_by,
                not args.no_patterns)
    if out is None:
        print(f"no site names {args.name!r}", file=sys.stderr)
        return 1
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
