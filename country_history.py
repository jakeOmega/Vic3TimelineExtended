"""What each country starts with: `common/history/countries` (#1628).

Vanilla ships one file per tag, each an effect script: `COUNTRIES = { c:TAG
?= { activate_law = … add_technology_researched = … } }`. ModState's
top-level merge is last-wins by key, so it would keep one `COUNTRIES` block of
the 450 and say nothing about the rest; this module reads the files on their
own instead, as state_history does for the start map.

A record holds the literal effects of a tag's block, the ones a question
usually needs sorted into fields and the rest kept as written. A field is
stored only when it has something in it; `describe` fills in the rest:

    {"laws": ["law_monarchy", …],                  # activate_law, in order
     "technologies": ["labor_movement", …],         # add_technology_researched
     "tech_tier_effects": ["effect_starting_technology_tier_1_tech"],
     "scripted_effects": ["effect_starting_politics_traditional"],
     "tax_level": "medium",
     "taxed_goods": ["liquor", …],
     "institutions": {"institution_schools": "3"},
     "ruling_interest_groups": ["ig_intelligentsia", …],
     "journal_entries": ["je_victoria"],
     "conditional": [{"kind": "if", "limit": "has_dlc_feature = rp1_content",
                      "effects": ["add_journal_entry = { type = je_aberdeen_act }"]}],
     "other": ["set_next_election_date = 1836.2.1", …]}

`tech_tier_effects` and `scripted_effects` are the `<name> = yes` calls whose
name starts with `effect_` or ends in `_effect` (vanilla's naming; the
starting-technology tiers are split out because they decide most of a tag's
technology). They are named, not expanded: what a tier grants is in vanilla's
`common/scripted_effects`, which `/scripted-effects/<name>?source=vanilla`
reads. Effects inside an `if` stay literal under `conditional`, since whether
they run depends on the limit (most are DLC checks). `other` and the
conditional parts are re-rendered from the parse on one line, comments
dropped.

`parse_dir` keeps the file each record came from (`{file name: {tag:
record}}`), because the engine replaces a vanilla history file with a mod
file of the same name and runs every other one: `merge(vanilla, mod)` applies
that, and gives each tag its records in file order.

`vanilla_parsed.py` snapshots `parse_dir`'s result for vanilla
(`vanilla_parsed/history/countries.json`), so `GET /country-history/<TAG>`
works with no game install. The mod's `common/history/*.txt` GLOBAL files run
after all of this (`extra_history.txt` activates the mod's default laws on
every country) and are not folded in.

CLI (the game files when the machine has them, else the snapshot):

    python3 country_history.py GBR
    python3 country_history.py --summary
"""
from __future__ import annotations

import argparse
import codecs
import json
import os
import sys
from typing import Iterable, Optional

from mod_state import iter_script_files
from state_history import _entries, _raw_parse, _strip_scope, _unquote

# Relative to a game root (`<install>/game`) or to the mod root.
REL_DIR = "common/history/countries"

LIST_FIELDS = ("laws", "technologies", "tech_tier_effects", "scripted_effects", "taxed_goods",
               "ruling_interest_groups", "journal_entries", "conditional", "other")
CONDITIONAL_KEYS = ("if", "else_if", "else")
TECH_TIER_PREFIX = "effect_starting_technology_"


def render(key, op, value) -> str:
    """One effect back to script text on one line: `key op value`, a block as
    `{ … }`. Comments are gone (the parse drops them)."""
    return f"{_unquote(key) if isinstance(key, str) else key} {op} {render_value(value)}"


def render_value(value) -> str:
    if isinstance(value, tuple) and len(value) == 2:
        return render_value(value[1])
    if isinstance(value, dict):
        inner = " ".join(render(k, v[0], v[1]) if isinstance(v, tuple) else f"{k} = {render_value(v)}"
                         for k, v in value.items())
        return "{ " + inner + " }" if inner else "{ }"
    if isinstance(value, list):
        # A block with a repeated key parses as a list of single-key dicts.
        if value and all(isinstance(i, dict) and len(i) == 1 for i in value):
            return "{ " + " ".join(render_value(i)[2:-2] for i in value) + " }"
        inner = " ".join(render_value(i) for i in value)
        return "{ " + inner + " }" if inner else "{ }"
    return str(value)


def _body_text(value) -> str:
    """A block's content without its braces."""
    text = render_value(value)
    return text[2:-2] if text.startswith("{ ") and text.endswith(" }") else text


def _add(record: dict, field: str, item) -> None:
    record.setdefault(field, []).append(item)


def _add_effects(record: dict, body) -> None:
    for key, pair in _pairs(body):
        op, value = pair
        if key == "activate_law":
            _add(record, "laws", _strip_scope(value, "law_type:"))
        elif key == "add_technology_researched":
            _add(record, "technologies", _unquote(value))
        elif key == "set_tax_level" and isinstance(value, str):
            record["tax_level"] = _unquote(value)
        elif key == "add_taxed_goods":
            _add(record, "taxed_goods", _strip_scope(value, "g:"))
        elif key == "set_institution_investment_level" and isinstance(value, (dict, list)):
            fields = dict(_entries(value))
            if "institution" in fields and "level" in fields:
                record.setdefault("institutions", {})[_unquote(fields["institution"])] = _unquote(fields["level"])
            else:
                _add(record, "other", render(key, op, value))
        elif key == "add_journal_entry" and isinstance(value, (dict, list)) and "type" in dict(_entries(value)):
            _add(record, "journal_entries", _unquote(dict(_entries(value))["type"]))
        elif key == "set_ruling_interest_groups" and isinstance(value, list) \
                and all(isinstance(v, str) for v in value):
            record["ruling_interest_groups"] = [_unquote(v) for v in value]
        elif key.startswith("ig:") and isinstance(value, (dict, list)):
            rest = [(k, p) for k, p in _pairs(value) if not (k == "add_ruling_interest_group" and p[1] == "yes")]
            if len(rest) < len(_pairs(value)):
                _add(record, "ruling_interest_groups", key[3:])
            if rest:
                _add(record, "other", render(key, op, value))
        elif value == "yes" and (key.startswith("effect_") or key.endswith("_effect")):
            _add(record, "tech_tier_effects" if key.startswith(TECH_TIER_PREFIX) else "scripted_effects", key)
        elif key in CONDITIONAL_KEYS and isinstance(value, (dict, list)):
            limit = [p[1] for k, p in _pairs(value) if k == "limit"]
            _add(record, "conditional", {
                "kind": key,
                "limit": _body_text(limit[0]) if limit else None,
                "effects": [render(k, p[0], p[1]) for k, p in _pairs(value) if k != "limit"],
            })
        else:
            _add(record, "other", render(key, op, value))


def _pairs(block) -> list[tuple[str, tuple]]:
    """(key, (op, value)) for each entry of a raw parsed block, in source
    order, keeping the operator (`ig:x ?= { }`)."""
    items = [block] if isinstance(block, dict) else block if isinstance(block, list) else []
    out = []
    for item in items:
        if isinstance(item, dict):
            for key, pair in item.items():
                if not (isinstance(pair, tuple) and len(pair) == 2):
                    pair = ("=", pair)
                out.append((_unquote(key), pair))
    return out


def parse_text(text: str) -> dict[str, dict]:
    """{tag: record} for one history file's text. Every `COUNTRIES` block in
    the file counts, and a tag named twice keeps both blocks' effects."""
    countries: dict[str, dict] = {}
    for key, block in _entries(_raw_parse(text)):
        if key != "COUNTRIES":
            continue
        for tag_key, body in _entries(block):
            tag = _strip_scope(tag_key, "c:")
            if not tag:
                continue
            _add_effects(countries.setdefault(tag, {}), body)
    return countries


def _read(path: str) -> str:
    with codecs.open(path, "r", "utf-8-sig") as f:
        return f.read()


def source_files(dir_path: str) -> list[str]:
    """The files `parse_dir` reads, in the order it reads them."""
    return list(iter_script_files(dir_path)) if os.path.isdir(dir_path) else []


def parse_dir(dir_path: str) -> dict[str, dict]:
    """{file name: {tag: record}} for every history file under `dir_path`, in
    sorted name order. A missing directory is an empty table. A file that
    does not parse raises: a partial table would read as a real one."""
    by_file: dict[str, dict] = {}
    for path in source_files(dir_path):
        rel = os.path.relpath(path, dir_path).replace(os.sep, "/")
        by_file[rel] = parse_text(_read(path))
    return by_file


def merge(*layers: Optional[dict]) -> dict[str, list[dict]]:
    """{tag: [record, …]} from `parse_dir` tables, vanilla first. A later
    layer's file replaces an earlier layer's file of the same name (the
    engine's rule for a mod file at a vanilla path); each surviving file then
    gives its tags one record, carrying `file`, in name order."""
    files: dict[str, dict] = {}
    for layer in layers:
        files.update(layer or {})
    out: dict[str, list[dict]] = {}
    for name in sorted(files):
        for tag, rec in files[name].items():
            out.setdefault(tag, []).append({"file": name, **rec})
    return out


def describe(record: dict) -> dict:
    """A record with every field present: empty lists, `tax_level` None and
    `institutions` {} where the file sets nothing."""
    out = {"file": record.get("file")}
    for field in LIST_FIELDS:
        out[field] = list(record.get(field, []))
    out["tax_level"] = record.get("tax_level")
    out["institutions"] = dict(record.get("institutions", {}))
    return out


def summary(countries: dict[str, list[dict]]) -> dict:
    records = [r for recs in countries.values() for r in recs]
    return {
        "countries": len(countries),
        "with_laws": sum(1 for recs in countries.values() if any(r.get("laws") for r in recs)),
        "with_technologies": sum(1 for recs in countries.values()
                                 if any(r.get("technologies") for r in recs)),
        "conditional_blocks": sum(len(r.get("conditional", [])) for r in records),
    }


def load(game_root: Optional[str] = None, mod_root: Optional[str] = None,
         snapshot_dir: Optional[str] = None) -> tuple[dict[str, list[dict]], str]:
    """(countries, source): every tag's records and where vanilla came from
    (`game_files` or `vanilla_parsed`), with the mod's own country history
    files, if it ever ships any, layered on top."""
    import vanilla_parsed

    vanilla_dir = os.path.join(game_root, "game", *REL_DIR.split("/")) if game_root else None
    if vanilla_dir and os.path.isdir(vanilla_dir):
        vanilla, source = parse_dir(vanilla_dir), "game_files"
    else:
        snap = vanilla_parsed.load_country_history(snapshot_dir or vanilla_parsed.DEFAULT_DIR)
        if snap is None:
            raise FileNotFoundError(
                "no vanilla country history: no game files, and vanilla_parsed/ has none "
                "(rebuild with `python3 vanilla_parsed.py build` on a machine with the game)"
            )
        vanilla, source = snap, "vanilla_parsed"
    mod = parse_dir(os.path.join(mod_root, *REL_DIR.split("/"))) if mod_root else {}
    return merge(vanilla, mod), source


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="What a country starts with (vanilla history/countries).")
    ap.add_argument("tag", nargs="?", help="a country tag, e.g. GBR")
    ap.add_argument("--summary", action="store_true", help="print counts")
    args = ap.parse_args(argv)

    import path_constants
    try:
        game_root = path_constants.base_game_path
    except RuntimeError:
        game_root = None
    countries, source = load(game_root, path_constants.mod_path)
    if args.tag:
        if args.tag not in countries:
            print(f"{args.tag}: no country history", file=sys.stderr)
            return 1
        out = {"country": args.tag, "history": [describe(r) for r in countries[args.tag]]}
    else:
        out = summary(countries)
    out["vanilla_source"] = source
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
