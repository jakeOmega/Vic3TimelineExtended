"""Political parties for GET /parties (#1164): which files define each party,
and the terms of its merged `join_weight` in the order the engine reads them.

An injected `join_weight` replaces the party's whole field (read in game
2026-10-25, docs/guides/scripting_best_practices.md), and ModState merges it
the same way: the field is a script value, so `_is_script_value_field` in
paradox_file_parser.py swaps it in. The merged entity (`/raw/Parties/<key>`)
keeps order only among entries of one key, though: a repeated key folds into
one list, so walking it lists every `if` before every `else_if`, and the size
chain's `from_two_prior_members` lands after the First Past the Post penalty
that follows it. The terms here therefore come from the source text of the
definition whose `join_weight` the merged entity carries (`"terms_order":
"source"`). When that text isn't on disk (a vanilla-only party with vanilla
loaded from `vanilla_parsed/`), or doesn't reproduce the merged field, they
come from the merged entity instead (`"terms_order": "by_key"`).

Which block carries the field follows ModState's INJECT rules. A definition or
`REPLACE:` of the party sets it, or leaves the party without one. Inside an
`INJECT:` of the party, `join_weight` and `REPLACE:join_weight` replace it,
while `INJECT:join_weight` merges into it, after which no single file carries
it. A row names no `join_weight_file` when no file's block reproduces the
merged field.

`join_weight_terms` is flat: one string per desc, in order. A term (one
top-level entry of the field: `value`, `add`, `multiply`, `if`, `else_if`,
...) contributes its desc; a branch whose nested blocks carry several descs
contributes each once, in order. A term with no desc is written as its key and
value, `value = 0`, or `if = {...}` for a block, which no loc key can be.
"""
from __future__ import annotations

import codecs
import logging
import os

from mod_state import iter_script_files
from paradox_file_parser import ParadoxFileParser

logger = logging.getLogger(__name__)

FIELD = "join_weight"
SNAPSHOT_FILE = "vanilla_parsed/common/parties.json"
_REPLACING = (None, "REPLACE", "REPLACE_OR_CREATE")
_PARSER = ParadoxFileParser()


def split_directive(raw_key):
    """(`INJECT`|`REPLACE`|`REPLACE_OR_CREATE`|None, key), as the parser splits it."""
    return _PARSER._split_directive(raw_key)


def entries(block):
    """A parsed block's (key, value) entries in order, from either parse form.

    A raw parse gives a dict when every key is unique and a list of
    single-key dicts, in source order, when one repeats. The normalized form
    ModState keeps is a dict whose repeated keys hold a list of their
    entries, so there the order holds only within one key."""
    if isinstance(block, tuple) and len(block) >= 2:
        block = block[1]
    if isinstance(block, list):
        if all(isinstance(item, dict) and len(item) == 1 for item in block):
            return [next(iter(item.items())) for item in block]
        return []
    if isinstance(block, dict):
        out = []
        for key, value in block.items():
            if isinstance(value, list):
                out.extend((key, item) for item in value)
            else:
                out.append((key, value))
        return out
    return []


def field(block, name):
    """The value of `name` in `block` (the last entry if it repeats), or None."""
    found = None
    for key, value in entries(block):
        if key == name:
            found = value
    return found


def _field_write(block):
    """(directive, value) of the last entry in `block` that names the field,
    with or without a directive (`REPLACE:join_weight`), or None."""
    found = None
    for key, value in entries(block):
        directive, name = split_directive(key)
        if name == FIELD:
            found = (directive, value)
    return found


def _is_block(value):
    inner = value[1] if isinstance(value, tuple) and len(value) >= 2 else value
    return isinstance(inner, (dict, list))


def _descs(value):
    """Every desc a term names outside its `limit`, unquoted, once each, in order."""
    found = []

    def walk(block):
        for key, child in entries(block):
            if key == "limit":
                continue
            if key == "desc":
                text = child[1] if isinstance(child, tuple) else child
                if isinstance(text, str):
                    text = text.strip('"')
                    if text not in found:
                        found.append(text)
            elif _is_block(child):
                walk(child)

    walk(value)
    return found


def terms(join_weight):
    """[{"key", "descs"} | {"key", "descs": [], "value"}] for each top-level
    term of a join_weight, in the block's entry order. `value` is set for a
    one-line term (`value = 0`)."""
    out = []
    for key, value in entries(join_weight):
        if _is_block(value):
            out.append({"key": key, "descs": _descs(value)})
        else:
            literal = value[1] if isinstance(value, tuple) else value
            out.append({"key": key, "descs": [], "value": literal})
    return out


def flat_terms(term_list):
    """`terms()` as the flat string list /parties returns (see the module doc)."""
    out = []
    for term in term_list:
        if term["descs"]:
            out.extend(term["descs"])
        elif "value" in term:
            out.append(f"{term['key']} = {term['value']}")
        else:
            out.append(f"{term['key']} = {{...}}")
    return out


def raw_entries(text):
    """A file's top-level (raw key, value) entries in source order, un-normalized."""
    parser = ParadoxFileParser()
    parsed = parser.parse_object(parser.tokenize("{" + text + "}"))[0]
    return entries(parsed)


def directory_sites(directory, root, origin):
    """One site per script file under `directory` (load order), as
    {"source": origin, "file": path relative to `root`, "entries", "ordered": True}.
    A file that doesn't parse is skipped (ModState reports it in parse_failures)."""
    sites = []
    if not directory or not os.path.isdir(directory):
        return sites
    for path in iter_script_files(directory):
        try:
            with codecs.open(path, "r", "utf-8-sig") as file:
                found = raw_entries(file.read())
        except Exception as exc:  # noqa: BLE001 - one bad file mustn't sink the catalog
            logger.warning("party scan skipped %s: %s", path, exc)
            continue
        sites.append({
            "source": origin,
            "file": os.path.relpath(path, root).replace(os.sep, "/"),
            "entries": found,
            "ordered": True,
        })
    return sites


def snapshot_site(vanilla):
    """The vanilla side when it was loaded from vanilla_parsed/: its entries
    are the snapshot's normalized entities, which keep no cross-key order."""
    return {"source": "vanilla", "file": SNAPSHOT_FILE,
            "entries": list(vanilla.items()), "ordered": False}


def _site_ref(site, directive):
    ref = {"source": site["source"], "file": site["file"]}
    if directive:
        ref["directive"] = directive
    return ref


def party_rows(merged, vanilla, sites):
    """One row per party in `merged` (ModState's merged Parties data), sorted
    by key. `vanilla` is the vanilla side alone; `sites` are the files that
    define parties, vanilla first, each in load order (directory_sites,
    snapshot_site).

    Row: {"key", "source": "vanilla"|"mod"|"both", "files": [{"source",
    "file", "directive"?}], "join_weight_file": the site whose join_weight
    the merged party carries, or None when no site's block reproduces the
    merged field, "terms_order": "source"|"by_key", "join_weight_terms": [...],
    "terms": the per-term detail}."""
    rows = []
    for key in sorted(merged):
        files = []
        carrier = None  # (site ref, raw join_weight, ordered)
        for site in sites:
            for raw_key, value in site["entries"]:
                directive, name = split_directive(raw_key)
                if name != key:
                    continue
                ref = _site_ref(site, directive)
                if ref not in files:
                    files.append(ref)
                write = _field_write(value)
                if directive in _REPLACING:
                    # A definition or REPLACE sets the whole party.
                    carrier = None if write is None else (ref, write[1], site["ordered"])
                elif write is None:
                    pass  # an INJECT that leaves the field alone
                elif write[0] == "INJECT":
                    carrier = None  # merged into the field: no one block carries it
                else:
                    carrier = (ref, write[1], site["ordered"])
        touched = any(ref["source"] == "mod" for ref in files)
        if key not in vanilla:
            source = "mod"
        else:
            source = "both" if touched else "vanilla"
        merged_field = field(merged[key], FIELD)
        matches = carrier is not None and _PARSER._normalize_fully(carrier[1]) == merged_field
        if matches and carrier[2]:
            order, term_list = "source", terms(carrier[1])
        else:
            order, term_list = "by_key", terms(merged_field) if merged_field is not None else []
        rows.append({
            "key": key,
            "source": source,
            "files": files,
            "join_weight_file": carrier[0] if matches else None,
            "terms_order": order,
            "join_weight_terms": flat_terms(term_list),
            "terms": term_list,
        })
    return rows
