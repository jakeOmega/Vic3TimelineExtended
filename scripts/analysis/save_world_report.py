#!/usr/bin/env python3
"""World-level counts from a Victoria 3 save: treaty articles, technology, buildings, and PM churn between saves.

Read-only. Built for the owner's AI-only "observer" games, where the question is
what the AI is doing across the whole world (which treaty articles every pair
signs, how far research has got, how many ports sit retooling, how often PMs flip
back and forth), so the next observer run is re-measured in one command instead
of a throwaway script per question.

Usage:
    save_world_report.py treaties [save.v3] [--article joint_military_exercises] [--top 10]
    save_world_report.py techs [save.v3] [--tech nuclear_energy] [--top 15]
    save_world_report.py buildings [save.v3] [--type building_port] [--top 25]
    save_world_report.py churn old.v3 newer.v3 [...] [--type building_port] [--top 15]
    any of them with --json for machine output, --server URL for the mod state server

With no save named (treaties / techs / buildings), the newest in the save folder
is read. A binary save takes 2-5 s (its gamestate is ~300 MB unzipped). A
plain-text save (debug mode writes these) is memory-mapped and only the sections
asked for are streamed: 3-4 s for a 383 MB one once the OS has it cached.

WHAT EACH REPORT COUNTS
  treaties   Every treaty article record, by type, with the treaties holding it,
             the treaties holding nothing else, and how many of its articles sit
             in a treaty that also holds an alliance or defensive pact, or
             between two countries that hold one in any treaty. Mod types are
             marked `*` (defined in the mod's common/treaty_articles and absent
             from vanilla's snapshot). Then the commonest treaty compositions.
             --article X adds who holds it: a country counts each X article of a
             treaty it is a party to (first or second country), with the
             source/target split for a directed article.
  techs      Per country (each technology record; a tag can have two objects, so
             one shared tag prints as TAG#<slot>): techs acquired, per era. Era
             complete = every researchable tech of the era acquired; a tech with
             `can_research = no` (vanilla's sericulture) is left out of that, as
             no country can research it. Highest era touched = the latest era
             with any tech acquired. --tech X lists its holders and who is
             researching it.
  buildings  Buildings and retooling share by type. Retooling = the timed
             modifier pm_retooling in the building's modifier list (all 3,039 on
             the 2015.6.1 observer save had an end date after the save date and a
             1,820-day span; a stale one is counted apart as "ended"). --type X
             adds its PM usage, by PM group.
  churn      Buildings matched by id between consecutive saves (sorted by game
             date). A change = a building whose PM set differs between two
             consecutive saves (the saved PM order is not stable, so order is
             ignored). A reversal = a change that re-adds a PM an earlier change
             on the same building, within the series, removed. A switch = one
             removed PM paired with the added PM of the same PM group (a lone
             swap pairs without group data; unmatched leftovers print joined by
             +). Buildings present in only one of two saves are not changes.

REFERENCE DATA (not in the save)
  Technology eras: the mod state server's GET /technologies when it answers
  (--server, default http://localhost:8950; --offline skips it), else vanilla's
  snapshot (vanilla_parsed/common/technologies.json) with the mod's
  common/technology/technologies/*.txt over it. `can_research` always comes
  from those files (the server's summary does not carry it).
  PM groups of a building type: the server's GET /production-methods?building=<type>,
  else the snapshot's buildings.json + pm_groups.json with the mod's
  common/buildings and common/production_method_groups over them (INJECT:
  lists are added to the vanilla ones).
  Mod treaty articles: top-level names in the mod's common/treaty_articles
  that vanilla's snapshot does not define.
  Checked 2026-10-05: the server and the files agreed on the era of all 351
  techs and on the PM groups of all 545 building types (before INJECT: and
  REPLACE: were told apart, six types the mod REPLACEs kept vanilla's groups).

BINARY LAYOUT (worked out on 1.14.5 saves, 2026-10-05; token numbers, with the
key the engine writes for the same field in a plain-text save, matched by key
order and value shape; the BINARY LAYOUT of save_country_probe.py has the token
types, the country blocks and laws.)

  date      The gamestate's first 0x3245 = i32 (hours, as meta's) sits ~30 bytes
            in: autosaves have no `meta` entry, so the date is read from there.

  treaty articles  (text: treaty_article_manager={ database={ ... } })
            u32:<id> = { 0x2f11 = "<article type>"      article
                         0x57d6 = u32:<treaty id>       treaty
                         0x60c9 = u32:<country>         source_country
                         0x321f = u32:<country>         target_country
                         [0x60d4 = { u32:<country> = 0 }]  current_contraventions
                         [0x081b = { { ... } }]           inputs (goods, amounts) }
            Found by `\x14\x00 <id> \x01\x00 \x03\x00 \x11\x2f \x01\x00 (\x0f|\x17)\x00`.
            A mutual article saves 0xffffffff in both country fields. Source vs
            target: verified on the 2015.6.1 observer save, where the country
            in 0x60d4 equalled 0x60c9 on all 172 records that carry it and never
            0x321f, as current_contraventions holds source_country in a text
            save; the text key order agrees. Coverage check: the count of
            `0x2f11 = "<string>"` must equal the records decoded (667 of 667).

  treaties  (text: treaty_manager={ database={ ... } })
            u32:<id> = { 0x001b = { <name block> }     name
                         0x32cf = u32:<country>         first_country
                         0x32d0 = u32:<country>         second_country
                         [0x60cb = <date hours>]        entered_into_force_on
                         [0x6488 = <date hours>]        binding_started_on
                         0x60ca = <days> }              binding_period
            Found by `\x14\x00 <id> \x01\x00 \x03\x00 \x1b\x00 \x01\x00 \x03\x00`
            (2,584 hits on the observer save, other databases open the same way)
            keeping the records with a 0x32cf: exactly the 272 ids the articles
            name. An id the pass misses is searched for by its own bytes, and
            one still missing is a WARNING.

  technology  (text: technology={ database={ ... } }; one record per country)
            u32:<id> = { 0x2840 = u32:<country>         country
                         0x53b1 = "<tech>"               research_technology
                         0x5b2a = { "<tech>" ... }       research_queue
                         0x5bac = { { 0x31a9 = "<tech>"   progressed_technologies: technology
                                      0x2a4f = <progress> progress
                                      0x5443 = bool } ... }  is_researched
                         0x5bad = { "<tech>" ... }       acquired_technologies
                         0x5546 = { "<tech>" ... } }     currently_spreading_technologies
            Found by `\x14\x00 <id> \x01\x00 \x03\x00 \x40\x28 \x01\x00 \x14\x00`
            keeping records with a 0x5bad. The progress is written with the f64
            token (0x0167) but holds an i64 fixed point x 1e5: the 8 bytes are
            reinterpreted (a text save writes the plain decimal). Coverage
            check: the count of `0x5bad = {` must equal the records (175 of 175).

  buildings  (text: building_manager={ database={ ... } })
            u32:<id> = { 0x27f8 = "<building type>"     building
                         0x3a52 = <level>                levels
                         ... 0x01b7 = <state id>         state
                         ... 0x5925 = { "<pm>" ... }     production_methods (not in PM-group order)
                         ... 0x333b = { 0x0d00 = { { 0x000b = n  0x0c1f = "<modifier>"
                                                    0x0cf8 = <start hours>  0x0cf9 = <end hours> } ... } } }
                                                         timed_modifiers = { modifiers = { { id modifier
                                                         start_date end_date } } }
            Found by `(\x0c|\x14)\x00 <id> \x01\x00 \x03\x00 \xf8\x27 \x01\x00 (\x0f|\x17)\x00`,
            keeping records with a 0x5925. Ids are unique across the two key
            bytes (13,965 of 13,965 on the observer save, all 0x14), so a
            building is matched across saves by id alone, in either format.
            No coverage check: other records also carry `0x27f8 = "<type>"`
            (21,226 strings against 13,965 buildings).

TEXT LAYOUT. A text save writes the same records under the names above, each
`<id>={` entry at brace depth 2 of `<section>={ database={ ... } }`, plus
country_manager={ database={ <id>={ definition="TAG" ... } } } for tags and
meta_data={ game_date=Y.M.D } for the date. Braces are counted per line, quotes
skipped; indentation is not trusted (nested records also start at column 0).
"""

import argparse
import bisect
import json
import mmap
import re
import struct
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_save_history_order import find_saves, read_gamestate  # noqa: E402
from save_country_probe import (  # noqa: E402
    DIRECTIVE_RE,
    MONTHS,
    SCRIPT_TOKEN_RE,
    country_headers,
    fmt_hours,
    parse_block,
    top_level_fields,
)

REPO = Path(__file__).resolve().parents[2]
DEFAULT_SERVER = "http://localhost:8950"
NO_COUNTRY = 0xFFFFFFFF
MILITARY_PACTS = ("alliance", "defensive_pact")
RETOOLING = "pm_retooling"

# Binary token -> the key a text save writes for the same field (BINARY LAYOUT).
ARTICLE_KEYS = {0x2F11: "article", 0x57D6: "treaty", 0x60C9: "source_country", 0x321F: "target_country",
                0x60D4: "current_contraventions", 0x081B: "inputs"}
TREATY_KEYS = {0x001B: "name", 0x32CF: "first_country", 0x32D0: "second_country", 0x60CB: "entered_into_force_on",
               0x6488: "binding_started_on", 0x60CA: "binding_period"}
TECH_KEYS = {0x2840: "country", 0x53B1: "research_technology", 0x5B2A: "research_queue",
             0x5BAC: "progressed_technologies", 0x31A9: "technology", 0x2A4F: "progress", 0x5443: "is_researched",
             0x5BAD: "acquired_technologies", 0x5546: "currently_spreading_technologies"}
BUILDING_KEYS = {0x27F8: "building", 0x3A52: "levels", 0x01B7: "state", 0x5925: "production_methods",
                 0x333B: "timed_modifiers", 0x0D00: "modifiers", 0x000B: "id", 0x0C1F: "modifier",
                 0x0CF8: "start_date", 0x0CF9: "end_date"}

ARTICLE_RE = re.compile(rb"\x14\x00(....)\x01\x00\x03\x00\x11\x2f\x01\x00(?:\x0f|\x17)\x00", re.S)
ARTICLE_ANCHOR_RE = re.compile(rb"\x11\x2f\x01\x00(?:\x0f|\x17)\x00")
TREATY_RE = re.compile(rb"\x14\x00(....)\x01\x00\x03\x00\x1b\x00\x01\x00\x03\x00", re.S)
TECH_RE = re.compile(rb"\x14\x00(....)\x01\x00\x03\x00\x40\x28\x01\x00\x14\x00", re.S)
TECH_ANCHOR_RE = re.compile(rb"\xad\x5b\x01\x00\x03\x00")
BUILDING_RE = re.compile(rb"(?:\x0c|\x14)\x00(....)\x01\x00\x03\x00\xf8\x27\x01\x00(?:\x0f|\x17)\x00", re.S)
DATE_KEY = b"\x45\x32\x01\x00\x0c\x00"
PARSE_ERRORS = (ValueError, StopIteration, struct.error, IndexError)

TEXT_TOKEN_RE = re.compile(rb'"[^"]*"|[{}=]|[^\s{}="]+')
DIRECTIVE_LINE_RE = re.compile(r"(?m)^\s*([A-Z_]+):([^\s={}#]+)\s*=")
TEXT_ENTRY_RE = re.compile(rb"^\s*(\d+)=\{")
TEXT_DATE_RE = re.compile(rb"\n\s*game_date=([\d.]+)")


# ---------------------------------------------------------------- values
def normalize(items, names):
    """Binary parse_block items as text-save items: [(name or None, value)], value a str/int/float/bool or a list.

    A token key in `names` takes its text-save name; any other key reads `0x....`.
    """
    out = []
    for key, value in items:
        if key is not None:
            key = names.get(key[1], f"0x{key[1]:04x}") if key[0] == "tok" else scalar(key)
        out.append((key, normalize(value, names) if isinstance(value, list) else scalar(value)))
    return out


def scalar(value):
    kind, v = value
    if kind == "tok":
        return f"0x{v:04x}"
    if kind == "bool":
        return bool(v)
    return v


def field(items, key, default=None):
    for k, v in items:
        if k == key:
            return v
    return default


def as_int(value):
    if isinstance(value, bool) or value is None or isinstance(value, list):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_country(value):
    """A country id, or None for no country (0xffffffff, as a mutual article saves both of its)."""
    cid = as_int(value)
    return None if cid in (None, NO_COUNTRY) else cid


def words(value):
    """The bare values of a `{ a b c }` list."""
    return [v for k, v in value if k is None and not isinstance(v, list)] if isinstance(value, list) else []


def date_hours(value):
    """Hours since year -5000 (as fmt_hours reads them) from a binary i32 or a text `Y.M.D[.H]`."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if not isinstance(value, str):
        return None
    try:
        parts = [int(p) for p in value.split(".")]
    except ValueError:
        return None
    year, month, day = (parts + [1, 1])[:3]
    hour = parts[3] if len(parts) > 3 else 0
    return (((year + 5000) * 365 + sum(MONTHS[: month - 1]) + day - 1) * 24) + hour


def fixed_point(value):
    """A technology's progress.

    Binary saves write it with the f64 token but hold an i64 fixed point x 1e5:
    the float the tokenizer made of those 8 bytes is packed back bit for bit
    (CPython copies an IEEE double verbatim both ways; a non-negative i64 of
    this size reads as a denormal, never a NaN) and read as the integer it is.
    A text save writes the decimal itself.
    """
    if isinstance(value, float):
        return struct.unpack("<q", struct.pack("<d", value))[0] / 1e5
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- records
def decode_article(aid, items):
    return {
        "id": aid,
        "type": field(items, "article"),
        "treaty": as_int(field(items, "treaty")),
        "source": as_country(field(items, "source_country")),
        "target": as_country(field(items, "target_country")),
    }


def decode_treaty(tid, items):
    return {
        "id": tid,
        "first": as_country(field(items, "first_country")),
        "second": as_country(field(items, "second_country")),
        "in_force": date_hours(field(items, "entered_into_force_on")),
        "binding_days": as_int(field(items, "binding_period")),
    }


def decode_tech(items):
    progress = {}
    for _, rec in field(items, "progressed_technologies") or []:
        if isinstance(rec, list) and field(rec, "technology"):
            progress[field(rec, "technology")] = fixed_point(field(rec, "progress"))
    return {
        "country": as_country(field(items, "country")),
        "researching": field(items, "research_technology"),
        "acquired": words(field(items, "acquired_technologies")),
        "progress": progress,
    }


def decode_building(bid, items):
    retool = None
    modifiers = field(field(items, "timed_modifiers") or [], "modifiers")
    for _, mod in modifiers if isinstance(modifiers, list) else []:
        if isinstance(mod, list) and field(mod, "modifier") == RETOOLING:
            retool = (date_hours(field(mod, "start_date")), date_hours(field(mod, "end_date")))
    return {
        "id": bid,
        "type": field(items, "building"),
        "level": as_int(field(items, "levels")),
        "state": as_int(field(items, "state")),
        "pms": words(field(items, "production_methods")),
        "retool": retool,
    }


# ---------------------------------------------------------------- binary
def gamestate_hours(blob):
    """The game date (hours) from the gamestate itself: its first 0x3245 = i32, ~30 bytes in."""
    at = blob.find(DATE_KEY, 0, 4096)
    return struct.unpack_from("<i", blob, at + 6)[0] if at != -1 else None


def binary_records(blob, regex, names, errors):
    """(id, normalized items, offset) for each block whose header `regex` matches; parse failures counted in errors."""
    for m in regex.finditer(blob):
        try:
            items = parse_block(blob, m.start())[0]
        except PARSE_ERRORS:
            errors[regex.pattern] += 1
            continue
        yield struct.unpack("<I", m.group(1))[0], normalize(items, names), m.start()


def binary_articles(blob, warnings):
    errors, out, starts = Counter(), [], set()
    for aid, items, at in binary_records(blob, ARTICLE_RE, ARTICLE_KEYS, errors):
        out.append(decode_article(aid, items))
        starts.add(at)
    # Coverage: a 0x2f11 that opens a block keyed by an id is an article record the header regex must have found.
    # One that opens any other block is a reference (a war goal enforcing an article: one on the observer save).
    missed = 0
    for m in ARTICLE_ANCHOR_RE.finditer(blob):
        at = m.start() - 10
        if blob[m.start() - 4 : m.start()] == b"\x01\x00\x03\x00" and blob[at : at + 2] in (b"\x0c\x00", b"\x14\x00"):
            missed += at not in starts
    if missed or errors:
        warnings.append(f"{missed + sum(errors.values())} article records missed or unparsed; {len(out)} decoded")
    return [a for a in out if a["type"]]


def binary_treaties(blob, wanted, warnings):
    """{id: treaty} for every treaty an article names."""
    errors, out = Counter(), {}
    for tid, items, _ in binary_records(blob, TREATY_RE, TREATY_KEYS, errors):
        if field(items, "first_country") is not None:
            out[tid] = decode_treaty(tid, items)
    for tid in sorted(set(wanted) - set(out)):
        needle = b"\x14\x00" + struct.pack("<I", tid) + b"\x01\x00\x03\x00"
        at = blob.find(needle)
        while at != -1 and tid not in out:
            try:
                items = normalize(parse_block(blob, at)[0], TREATY_KEYS)
                if field(items, "first_country") is not None and field(items, "name") is not None:
                    out[tid] = decode_treaty(tid, items)
            except PARSE_ERRORS:
                pass
            at = blob.find(needle, at + 1)
    missing = set(wanted) - set(out)
    if missing:
        warnings.append(f"{len(missing)} treaties named by articles not found: {sorted(missing)[:10]}")
    return out


def binary_techs(blob, warnings):
    """Technology records. 60k other blocks (on the observer save) also open with `0x2840 = u32`, so only the
    header nearest before each acquired-technology list (0x5bad) is parsed."""
    heads = [m.start() for m in TECH_RE.finditer(blob)]
    anchors = [m.start() for m in TECH_ANCHOR_RE.finditer(blob)]
    out, seen = [], set()
    for anchor in anchors:
        pos = bisect.bisect_left(heads, anchor) - 1
        if pos < 0 or heads[pos] in seen:
            continue
        seen.add(heads[pos])
        try:
            items = normalize(parse_block(blob, heads[pos])[0], TECH_KEYS)
        except PARSE_ERRORS:
            continue
        if field(items, "acquired_technologies") is not None:
            out.append(decode_tech(items))
    if len(anchors) != len(out):
        warnings.append(f"{len(anchors)} acquired-technology lists (0x5bad) in the gamestate but {len(out)} records decoded")
    return out


def binary_buildings(blob, warnings):
    errors, out = Counter(), {}
    for bid, items, _ in binary_records(blob, BUILDING_RE, BUILDING_KEYS, errors):
        if field(items, "production_methods") is not None:
            out[bid] = decode_building(bid, items)
    if errors:
        warnings.append(f"{sum(errors.values())} building-like records failed to parse")
    return out


# ---------------------------------------------------------------- text
def brace_delta(line):
    """Opening minus closing braces on one line, quoted text ignored."""
    if b'"' in line:
        line = re.sub(rb'"[^"]*"', b"", line)
    return line.count(b"{") - line.count(b"}")


def parse_text(data):
    """[(key or None, value)] for Clausewitz text: a value is a string (quotes stripped) or a nested list."""
    toks, at = TEXT_TOKEN_RE.findall(data), 0

    def block():
        nonlocal at
        items = []
        while at < len(toks):
            tok = toks[at]
            at += 1
            if tok == b"}":
                return items
            if tok == b"{":
                items.append((None, block()))
            elif at < len(toks) and toks[at] == b"=" and at + 1 < len(toks):
                value = toks[at + 1]
                at += 2
                items.append((tok.decode("latin1"), block() if value == b"{" else value.strip(b'"').decode("latin1")))
            else:
                items.append((None, tok.strip(b'"').decode("latin1")))
        return items

    return block()


def text_entries(mapped, section, keep=None):
    """(id, items) for each `<id>={ ... }` of a text save's `section={ database={ ... } }`.

    keep: the entry keys worth parsing (bytes); None parses every key. The
    rest of an entry is skipped line by line, which is what keeps the 450k-line
    country_manager cheap.
    """
    # Positions are kept here, not in the mmap (whose find and readline start at its shared current position),
    # so two of these can run at once.
    at = mapped.find(b"\n" + section + b"={", 0)
    if at == -1:
        return
    pos, size = at + 1, len(mapped)
    depth, in_db, entry, lines, capture = 0, False, None, [], False
    while pos < size:
        nl = mapped.find(b"\n", pos)
        end = size if nl == -1 else nl + 1
        line, pos = mapped[pos:end], end
        before = depth
        depth += brace_delta(line)
        if before == 1:
            in_db = line.strip().startswith(b"database=")
        elif before == 2 and in_db:
            m = TEXT_ENTRY_RE.match(line)
            if m and depth == 2:  # a one-line entry
                yield int(m.group(1)), parse_text(line[line.index(b"{") + 1 : line.rindex(b"}")])
            elif m:
                entry, lines, capture = int(m.group(1)), [line[line.index(b"{") + 1 :]], False
        elif before >= 3 and entry is not None:
            if before == 3:
                key = line.strip().split(b"=", 1)[0]
                capture = keep is None or key in keep
            if capture:
                lines.append(line)
            if depth <= 2:
                yield entry, parse_text(b"".join(lines))
                entry, lines = None, []
        if depth <= 0:
            return


class TextSave:
    """A plain-text save, memory-mapped; each section is streamed when asked for."""

    def __init__(self, path):
        self.handle = open(path, "rb")
        self.mapped = mmap.mmap(self.handle.fileno(), 0, access=mmap.ACCESS_READ)

    def close(self):
        self.mapped.close()
        self.handle.close()

    def hours(self):
        m = TEXT_DATE_RE.search(self.mapped[:65536])
        return date_hours(m.group(1).decode()) if m else None

    def tags(self):
        return {cid: field(items, "definition") for cid, items in text_entries(self.mapped, b"country_manager", {b"definition"})
                if field(items, "definition")}

    def articles(self, warnings):
        return [a for a in (decode_article(aid, items) for aid, items in text_entries(self.mapped, b"treaty_article_manager"))
                if a["type"]]

    def treaties(self, wanted, warnings):
        keep = {b"first_country", b"second_country", b"entered_into_force_on", b"binding_period"}
        out = {tid: decode_treaty(tid, items) for tid, items in text_entries(self.mapped, b"treaty_manager", keep)
               if tid in wanted}
        missing = set(wanted) - set(out)
        if missing:
            warnings.append(f"{len(missing)} treaties named by articles not found: {sorted(missing)[:10]}")
        return out

    def techs(self, warnings):
        return [decode_tech(items) for _, items in text_entries(self.mapped, b"technology")
                if field(items, "acquired_technologies") is not None]

    def buildings(self, warnings):
        keep = {b"building", b"levels", b"state", b"production_methods", b"timed_modifiers"}
        return {bid: decode_building(bid, items) for bid, items in text_entries(self.mapped, b"building_manager", keep)
                if field(items, "building") and field(items, "production_methods") is not None}


class BinarySave:
    def __init__(self, path):
        self.blob = read_gamestate(path)

    def close(self):
        self.blob = None

    def hours(self):
        return gamestate_hours(self.blob)

    def tags(self):
        return {cid: tag for _, cid, tag, _ in country_headers(self.blob)}

    def articles(self, warnings):
        return binary_articles(self.blob, warnings)

    def treaties(self, wanted, warnings):
        return binary_treaties(self.blob, wanted, warnings)

    def techs(self, warnings):
        return binary_techs(self.blob, warnings)

    def buildings(self, warnings):
        return binary_buildings(self.blob, warnings)


def is_text_save(path):
    with open(path, "rb") as handle:
        return b"meta_data={" in handle.read(256)


class World:
    """One save: its date, its countries, and each section decoded on first use."""

    def __init__(self, path):
        self.path = Path(path)
        self.format = "text" if is_text_save(path) else "binary"
        self.source = TextSave(path) if self.format == "text" else BinarySave(path)
        self.hours = self.source.hours()
        self.date = fmt_hours(self.hours) if self.hours is not None else "?"
        self.warnings = []
        self._labels = None

    def close(self):
        self.source.close()

    def label(self, cid):
        """The country's tag; TAG#<slot> where two objects share it; #<id> for an id with no country block."""
        if self._labels is None:
            tags = self.source.tags()
            shared = Counter(tags.values())
            self._labels = {c: tag if shared[tag] == 1 else f"{tag}#{c & 0xFFFFFF}" for c, tag in tags.items()}
        return self._labels.get(cid, f"#{cid}")

    def header(self):
        return {"save": str(self.path), "date": self.date, "format": self.format}


# ---------------------------------------------------------------- reference data
def top_level_names(text):
    """The name of each top-level `name = { ... }` block of a script file, INJECT:/REPLACE: stripped."""
    toks = [t for t in SCRIPT_TOKEN_RE.findall(text) if not t.startswith("#")]
    names, depth = [], 0
    for i, t in enumerate(toks):
        if t == "{":
            if depth == 0 and i >= 2 and toks[i - 1] == "=":
                names.append(DIRECTIVE_RE.sub("", toks[i - 2]))
            depth += 1
        elif t == "}":
            depth = max(depth - 1, 0)
    return names


class Reference:
    """What the save does not hold: technology eras, PM groups, which treaty articles are the mod's."""

    def __init__(self, server=DEFAULT_SERVER, offline=False, repo=REPO):
        self.server = None if offline else server.rstrip("/")
        self.repo = Path(repo)
        self.snapshot = self.repo / "vanilla_parsed" / "common"
        self._server_up = None
        self._groups = {}
        self._offline_groups = None

    # -- server
    def get(self, path):
        """JSON from the mod state server, or None (down, or any error; the first failure stops further calls)."""
        if not self.server or self._server_up is False:
            return None
        try:
            with urllib.request.urlopen(self.server + path, timeout=5 if self._server_up else 2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._server_up = True
            return data
        except urllib.error.HTTPError:  # it answered: up, but no such entity
            self._server_up = True
            return None
        except (urllib.error.URLError, OSError, ValueError):
            if self._server_up is None:
                self._server_up = False
            return None

    # -- files
    def snapshot_field(self, name, key):
        """{entity: value} from a vanilla_parsed JSON: {"x": ["=", {key: ["=", value]}]}."""
        path = self.snapshot / f"{name}.json"
        if not path.is_file():
            return {}
        out = {}
        for entity, entry in json.loads(path.read_text(encoding="utf-8")).items():
            body = entry[1] if isinstance(entry, list) and len(entry) == 2 else None
            value = body.get(key) if isinstance(body, dict) else None
            if isinstance(value, list) and len(value) == 2:
                out[entity] = value[1]
        return out

    def layered(self, snapshot_name, folder, key, merge_lists=False):
        """{entity: value}: vanilla's snapshot, then the mod's common/<folder>/*.txt over it.

        A mod block replaces the value, except that with merge_lists an INJECT:
        block's list is added to the one before it (REPLACE: and a plain
        definition still replace it).
        """
        out = self.snapshot_field(snapshot_name, key)
        for path in sorted((self.repo / "common" / folder).glob("*.txt")):
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            injected = {name for directive, name in DIRECTIVE_LINE_RE.findall(text) if "INJECT" in directive}
            for entity, value in top_level_fields(text, key).items():
                if merge_lists and entity in injected and isinstance(value, list) and isinstance(out.get(entity), list):
                    out[entity] = out[entity] + [v for v in value if v not in out[entity]]
                else:
                    out[entity] = value
        return out

    # -- technology
    def tech_eras(self):
        """({tech: "era_N"}, source)."""
        data = self.get("/technologies")
        if isinstance(data, dict) and data:
            eras = {t["id"]: era for era, block in data.items() if isinstance(block, dict)
                    for t in block.get("technologies", []) if isinstance(t, dict) and "id" in t}
            if eras:
                return eras, f"mod state server {self.server}"
        eras = {t: e for t, e in self.layered("technologies", "technology/technologies", "era").items() if isinstance(e, str)}
        return eras, "vanilla_parsed + the mod's technology files"

    def unresearchable(self):
        return {t for t, v in self.layered("technologies", "technology/technologies", "can_research").items() if v == "no"}

    # -- production methods
    def pm_groups(self, building_type):
        """({pm: group} for one building type, source); ({}, None) when neither source knows the type."""
        if building_type in self._groups:
            return self._groups[building_type]
        result = ({}, None)
        data = self.get(f"/production-methods?building={building_type}")
        if isinstance(data, dict) and data.get("pm_groups"):
            result = ({pm["id"]: g["id"] for g in data["pm_groups"] for pm in g.get("pms", []) if "id" in pm},
                      "server")
        else:
            offline = self.offline_pm_groups().get(building_type)
            if offline:
                result = (offline, "files")
        self._groups[building_type] = result
        return result

    def offline_pm_groups(self):
        """{building type: {pm: group}} from vanilla's snapshot and the mod's files."""
        if self._offline_groups is None:
            groups = self.layered("pm_groups", "production_method_groups", "production_methods", merge_lists=True)
            buildings = self.layered("buildings", "buildings", "production_method_groups", merge_lists=True)
            self._offline_groups = {
                b: {pm: g for g in gs if isinstance(groups.get(g), list) for pm in groups[g]}
                for b, gs in buildings.items() if isinstance(gs, list)
            }
        return self._offline_groups

    # -- treaty articles
    def mod_articles(self):
        vanilla_path = self.snapshot / "treaty_articles.json"
        vanilla = set(json.loads(vanilla_path.read_text(encoding="utf-8"))) if vanilla_path.is_file() else set()
        names = set()
        for path in (self.repo / "common" / "treaty_articles").glob("*.txt"):
            names.update(top_level_names(path.read_text(encoding="utf-8-sig", errors="replace")))
        return names - vanilla


# ---------------------------------------------------------------- reports
def treaties_report(world, ref, articles_wanted=(), top=10):
    articles = world.source.articles(world.warnings)
    treaties = world.source.treaties({a["treaty"] for a in articles}, world.warnings)
    mod = ref.mod_articles()
    by_treaty = defaultdict(list)
    for a in articles:
        by_treaty[a["treaty"]].append(a["type"])
    pair_of = {tid: frozenset((t["first"], t["second"])) for tid, t in treaties.items()}
    pact_pairs = {pair_of[tid] for tid, types in by_treaty.items() if tid in pair_of and set(types) & set(MILITARY_PACTS)}
    rows = []
    for typ, n in Counter(a["type"] for a in articles).most_common():
        sel = [a for a in articles if a["type"] == typ]
        holding = {a["treaty"] for a in sel}
        rows.append({
            "type": typ,
            "mod": typ in mod,
            "articles": n,
            "treaties": len(holding),
            "only": sum(1 for tid in holding if set(by_treaty[tid]) == {typ}),
            "directed": sum(1 for a in sel if a["source"] is not None),
            "pact_same_treaty": sum(1 for a in sel if set(by_treaty[a["treaty"]]) & set(MILITARY_PACTS)),
            "pact_between_pair": sum(1 for a in sel if pair_of.get(a["treaty"]) in pact_pairs),
        })
    compositions = Counter(tuple(sorted(types)) for types in by_treaty.values())
    out = {
        **world.header(),
        "articles": len(articles),
        "treaties": len(by_treaty),
        "countries": len({c for t in treaties.values() for c in (t["first"], t["second"]) if c is not None}),
        "types": rows,
        "compositions": [{"articles": list(k), "treaties": n} for k, n in compositions.most_common(top)],
        "holders": {},
    }
    for typ in articles_wanted:
        holders = defaultdict(Counter)
        for a in articles:
            t = treaties.get(a["treaty"])
            if a["type"] != typ or not t:
                continue
            for cid in {t["first"], t["second"]} - {None}:
                holders[cid]["articles"] += 1
                holders[cid]["as_source"] += a["source"] == cid
                holders[cid]["as_target"] += a["target"] == cid
        out["holders"][typ] = [
            {"country": world.label(cid), "id": cid, **counts}
            for cid, counts in sorted(holders.items(), key=lambda kv: (-kv[1]["articles"], world.label(kv[0])))
        ]
    out["warnings"] = world.warnings
    return out


def era_number(era):
    try:
        return int(str(era).rsplit("_", 1)[-1])
    except ValueError:
        return 0


def techs_report(world, ref, tech=None, top=15):
    records = world.source.techs(world.warnings)
    eras, source = ref.tech_eras()
    blocked = ref.unresearchable()
    era_techs = defaultdict(set)
    for t, e in eras.items():
        era_techs[e].add(t)
    era_order = sorted(era_techs, key=era_number)
    rows, highest, unknown = [], Counter(), set()
    for rec in records:
        acquired = set(rec["acquired"])
        unknown |= {t for t in acquired if t not in eras}
        by_era = {e: len(acquired & era_techs[e]) for e in era_order}
        touched = [e for e in era_order if by_era[e]]
        highest[touched[-1] if touched else "none"] += 1
        rows.append({
            "country": world.label(rec["country"]) if rec["country"] is not None else "?",
            "id": rec["country"],
            "acquired": len(acquired),
            "by_era": by_era,
            "researching": rec["researching"],
            "progress": rec["progress"].get(rec["researching"]),
        })
    rows.sort(key=lambda r: (-r["acquired"], r["country"]))
    era_rows = []
    for e in era_order:
        researchable = era_techs[e] - blocked
        era_rows.append({
            "era": e,
            "techs": len(era_techs[e]),
            "researchable": len(researchable),
            "complete": sum(1 for rec in records if researchable and researchable <= set(rec["acquired"])),
            "touched": sum(1 for rec in records if era_techs[e] & set(rec["acquired"])),
        })
    out = {
        **world.header(),
        "countries": len(records),
        "era_source": source,
        "unresearchable": sorted(blocked),
        "eras": era_rows,
        "highest_era": {e: highest[e] for e in sorted(highest, key=era_number)},
        "top": rows[:top],
        "unknown_techs": sorted(unknown),
    }
    if tech:
        holders = sorted(world.label(r["country"]) for r in records if tech in r["acquired"])
        researching = sorted(
            ({"country": world.label(r["country"]), "progress": r["progress"].get(tech)}
             for r in records if r["researching"] == tech),
            key=lambda x: -(x["progress"] or 0),
        )
        out["tech"] = {"name": tech, "era": eras.get(tech), "known": tech in eras, "holders": holders,
                       "researching": researching}
    out["warnings"] = world.warnings
    return out


def buildings_report(world, ref, building_type=None, top=25):
    buildings = world.source.buildings(world.warnings)
    now = world.hours
    by_type = defaultdict(lambda: {"buildings": 0, "levels": 0, "retooling": 0, "retool_ended": 0})
    spans = Counter()
    for b in buildings.values():
        row = by_type[b["type"]]
        row["buildings"] += 1
        row["levels"] += b["level"] or 0
        if b["retool"]:
            start, end = b["retool"]
            if end is not None and now is not None and end <= now:
                row["retool_ended"] += 1
            else:
                row["retooling"] += 1
            if start is not None and end is not None:
                spans[(end - start) // 24] += 1
    rows = sorted(({"type": t, **r} for t, r in by_type.items()), key=lambda r: (-r["buildings"], r["type"]))
    out = {
        **world.header(),
        "buildings": len(buildings),
        "retooling": sum(r["retooling"] for r in rows),
        "retool_ended": sum(r["retool_ended"] for r in rows),
        "retool_span_days": {str(d): n for d, n in spans.most_common()},
        "types": rows[:top] if top else rows,
        "type_count": len(rows),
    }
    if building_type:
        sel = [b for b in buildings.values() if b["type"] == building_type]
        groups, source = ref.pm_groups(building_type)
        usage = defaultdict(lambda: {"buildings": 0, "retooling": 0})
        for b in sel:
            for pm in b["pms"]:
                usage[pm]["buildings"] += 1
                usage[pm]["retooling"] += bool(b["retool"])
        by_group = defaultdict(list)
        for pm, u in usage.items():
            by_group[groups.get(pm)].append({"pm": pm, **u})
        out["type"] = {
            "type": building_type,
            "buildings": len(sel),
            "retooling": sum(1 for b in sel if b["retool"]),
            "group_source": source,
            "groups": [{"group": g, "pms": sorted(pms, key=lambda p: (-p["buildings"], p["pm"]))}
                       for g, pms in sorted(by_group.items(), key=lambda kv: (kv[0] is None, kv[0] or ""))],
        }
    out["warnings"] = world.warnings
    return out


def pair_switches(removed, added, groups):
    """[(from, to, group)] for one building's change: removed and added PMs of the same group pair up.

    A lone removed/added pair needs no group data; anything left unpaired is
    joined with + (or - for none).
    """
    removed, added = sorted(removed), sorted(added)
    pairs, left = [], []
    for pm in removed:
        group = groups.get(pm)
        match = next((a for a in added if group is not None and groups.get(a) == group), None)
        if match:
            pairs.append((pm, match, group))
            added.remove(match)
        else:
            left.append(pm)
    if len(left) == 1 and len(added) == 1:
        pairs.append((left[0], added[0], groups.get(left[0]) or groups.get(added[0])))
    elif left or added:
        pairs.append(("+".join(left) or "-", "+".join(added) or "-", None))
    return pairs


def churn(snapshots):
    """Changes between consecutive snapshots ({id: (type, pms)}, oldest first).

    Returns (changes, steps): changes is [(step, id, type, removed, added, reversal)];
    steps is [(matched, changed)] per consecutive pair.
    """
    changes, steps, removed_before = [], [], defaultdict(set)
    for step in range(len(snapshots) - 1):
        a, z = snapshots[step], snapshots[step + 1]
        matched = set(a) & set(z)
        changed = 0
        for bid in sorted(matched):
            before, after = set(a[bid][1]), set(z[bid][1])
            if before == after:
                continue
            changed += 1
            removed, added = before - after, after - before
            reversal = bool(added & removed_before[bid])
            removed_before[bid] |= removed
            changes.append((step, bid, z[bid][0], removed, added, reversal))
        steps.append((len(matched), changed))
    return changes, steps


def churn_report(paths, ref, building_type=None, top=15):
    loaded = []
    for path in paths:
        world = World(path)
        buildings = world.source.buildings(world.warnings)
        loaded.append((world.hours if world.hours is not None else -1, len(loaded), world.header(), world.warnings,
                       {bid: (b["type"], b["pms"]) for bid, b in buildings.items()}))
        world.close()
    loaded.sort(key=lambda x: (x[0], x[1]))
    snapshots = [x[4] for x in loaded]
    changes, steps = churn(snapshots)
    per_type = defaultdict(lambda: {"changes": 0, "reversals": 0, "buildings": set()})
    for _, bid, typ, _, _, reversal in changes:
        row = per_type[typ]
        row["changes"] += 1
        row["reversals"] += reversal
        row["buildings"].add(bid)
    rows = sorted(({"type": t, "changes": r["changes"], "reversals": r["reversals"], "buildings": len(r["buildings"])}
                   for t, r in per_type.items()), key=lambda r: (-r["changes"], r["type"]))
    switches, sources = Counter(), set()
    for _, _, typ, removed, added, _ in changes:
        if building_type and typ != building_type:
            continue
        if not building_type and typ not in {r["type"] for r in rows[:top]}:
            continue
        groups, source = ref.pm_groups(typ)
        sources.add(source)
        for frm, to, group in pair_switches(removed, added, groups):
            switches[(typ, frm, to, group)] += 1
    out = {
        "saves": [{**x[2], "buildings": len(x[4])} for x in loaded],
        "steps": [{"from": loaded[i][2]["date"], "to": loaded[i + 1][2]["date"], "matched": m, "changed": c}
                  for i, (m, c) in enumerate(steps)],
        "changes": len(changes),
        "reversals": sum(1 for c in changes if c[5]),
        "types": rows if building_type is None else [r for r in rows if r["type"] == building_type],
        "switch_scope": building_type or f"the top {top} types",
        "group_source": sorted(s for s in sources if s) or None,
        "switches": [{"type": t, "from": f, "to": to, "group": g, "count": n}
                     for (t, f, to, g), n in switches.most_common(top)],
        "warnings": [f"{x[2]['save']}: {w}" for x in loaded for w in x[3]],
    }
    return out


# ---------------------------------------------------------------- text output
def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "-"


def head_line(r):
    return f"{r['save']}  [{r['date']}, {r['format']}]"


def print_warnings(r):
    for w in r.get("warnings", []):
        print(f"  WARNING: {w}")


def render_treaties(r, top):
    print(f"{head_line(r)}  {r['articles']} treaty articles in {r['treaties']} treaties, {r['countries']} countries party")
    print_warnings(r)
    print("\n  articles by type (* = the mod's):  articles / treaties holding it / holding nothing else /"
          " directed / in a treaty with an alliance or defensive pact / between a pair with one anywhere")
    for t in r["types"]:
        print(f"  {t['articles']:6d} {t['type'] + (' *' if t['mod'] else ''):42s} {t['treaties']:5d} {t['only']:5d}"
              f" {t['directed']:5d} {t['pact_same_treaty']:5d} {t['pact_between_pair']:5d}")
    print(f"\n  treaty compositions, top {top}:")
    for c in r["compositions"]:
        parts = Counter(c["articles"])
        print(f"  {c['treaties']:6d}  " + " + ".join(f"{a}{f' x{n}' if n > 1 else ''}" for a, n in sorted(parts.items())))
    for typ, holders in r["holders"].items():
        if not holders:
            print(f"\n  {typ}: no such article in this save")
            continue
        directed = any(h["as_source"] or h["as_target"] for h in holders)
        print(f"\n  {typ}: {len(holders)} countries hold one" + (" (as source/as target)" if directed else " (mutual)"))
        cells = [f"{h['country']} {h['articles']}" + (f" ({h['as_source']}/{h['as_target']})" if directed else "")
                 for h in holders]
        for i in range(0, len(cells), 8):
            print("    " + ", ".join(cells[i : i + 8]))


def render_techs(r, top):
    print(f"{head_line(r)}  {r['countries']} countries with a technology record; eras from {r['era_source']}")
    print_warnings(r)
    if r["unknown_techs"]:
        print(f"  techs with no known era ({len(r['unknown_techs'])}): {', '.join(r['unknown_techs'][:20])}")
    print("\n  era: techs (researchable) / countries with every researchable one / countries with any")
    for e in r["eras"]:
        print(f"  {e['era']:7s} {e['techs']:3d} ({e['researchable']:3d})  complete {e['complete']:4d}/{r['countries']}"
              f"  touched {e['touched']:4d}/{r['countries']}")
    if r["unresearchable"]:
        print(f"  left out of 'complete' (can_research = no): {', '.join(r['unresearchable'])}")
    print("\n  highest era touched: " + ", ".join(f"{e} {n}" for e, n in r["highest_era"].items()))
    shown = [e["era"] for e in r["eras"] if e["touched"]]
    print(f"\n  top {top} by techs acquired (per era: {' '.join(str(era_number(e)) for e in shown)}):")
    for row in r["top"]:
        per_era = " ".join(f"{row['by_era'][e]:2d}" for e in shown)
        research = f"  researching {row['researching']}" if row["researching"] else ""
        if row["researching"] and row["progress"] is not None:
            research += f" ({row['progress']:.0f})"
        print(f"  {row['country']:10s} {row['acquired']:4d}  [{per_era}]{research}")
    if "tech" in r:
        t = r["tech"]
        known = t["era"] or "no such technology in the era data"
        print(f"\n  {t['name']} ({known}): {len(t['holders'])} holders")
        for i in range(0, len(t["holders"]), 16):
            print("    " + " ".join(t["holders"][i : i + 16]))
        if t["researching"]:
            print("  researching it now: " + ", ".join(
                f"{x['country']} ({x['progress']:.0f})" if x["progress"] is not None else x["country"]
                for x in t["researching"]))


def render_buildings(r, top):
    print(f"{head_line(r)}  {r['buildings']} buildings, {r['retooling']} retooling ({pct(r['retooling'], r['buildings'])})"
          + (f", {r['retool_ended']} with an ended pm_retooling still listed" if r["retool_ended"] else ""))
    print_warnings(r)
    if r["retool_span_days"]:
        print("  retooling spans (end - start, days): "
              + ", ".join(f"{d} x{n}" for d, n in list(r["retool_span_days"].items())[:6]))
    print(f"\n  top {len(r['types'])} of {r['type_count']} types by count:  buildings / levels / retooling (share)")
    for t in r["types"]:
        print(f"  {t['type']:48s} {t['buildings']:6d} {t['levels']:7d} {t['retooling']:6d} ({pct(t['retooling'], t['buildings'])})")
    if "type" in r:
        t = r["type"]
        source = {"server": "the mod state server", "files": "vanilla_parsed + mod files", None: "no source knew it"}[t["group_source"]]
        print(f"\n  {t['type']}: {t['buildings']} buildings, {t['retooling']} retooling; PM groups from {source}")
        for g in t["groups"]:
            print(f"    {g['group'] or '(group unknown)'}:")
            for pm in g["pms"]:
                print(f"      {pm['buildings']:6d}  {pm['pm']}" + (f"  ({pm['retooling']} retooling)" if pm["retooling"] else ""))


def render_churn(r, top):
    print("churn: " + " -> ".join(f"{s['date']} ({Path(s['save']).name}, {s['buildings']} buildings)" for s in r["saves"]))
    print_warnings(r)
    for s in r["steps"]:
        print(f"  {s['from']} -> {s['to']}: {s['matched']} buildings in both, {s['changed']} changed PMs")
    print(f"  {r['changes']} changes, {r['reversals']} reversals (a change that re-adds a PM an earlier change on the"
          " same building removed)")
    print(f"\n  by type, top {top}:  changes / reversals / buildings changed")
    for t in r["types"][:top]:
        print(f"  {t['type']:48s} {t['changes']:6d} {t['reversals']:6d} {t['buildings']:6d}")
    source = ", ".join(r["group_source"]) if r["group_source"] else "none (lone swaps paired, the rest joined)"
    print(f"\n  top {top} switches in {r['switch_scope']} (PM groups from: {source}):")
    for s in r["switches"]:
        print(f"  {s['count']:6d}  {s['type']}: {s['from']} -> {s['to']}" + (f"  [{s['group']}]" if s["group"] else ""))


# ---------------------------------------------------------------- main
def newest_save():
    saves = find_saves()
    return saves[0] if saves else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print the report as JSON")
    common.add_argument("--top", type=int, help="rows per list")
    common.add_argument("--server", default=DEFAULT_SERVER, help=f"mod state server (default {DEFAULT_SERVER})")
    common.add_argument("--offline", action="store_true", help="never ask the mod state server")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("treaties", parents=[common], help="treaty articles and treaties")
    p.add_argument("save", nargs="?", type=Path)
    p.add_argument("--article", action="append", default=[], help="list who holds this article type (repeatable)")
    p = sub.add_parser("techs", parents=[common], help="technology per country and era")
    p.add_argument("save", nargs="?", type=Path)
    p.add_argument("--tech", help="list the holders of this technology")
    p = sub.add_parser("buildings", parents=[common], help="buildings and retooling by type")
    p.add_argument("save", nargs="?", type=Path)
    p.add_argument("--type", dest="building_type", help="PM usage of this building type")
    p = sub.add_parser("churn", parents=[common], help="PM changes between saves")
    p.add_argument("saves", nargs="+", type=Path)
    p.add_argument("--type", dest="building_type", help="switches of this building type only")
    args = parser.parse_args(argv)
    ref = Reference(args.server, args.offline)
    defaults = {"treaties": 10, "techs": 15, "buildings": 25, "churn": 15}
    top = args.top or defaults[args.command]

    if args.command == "churn":
        if len(args.saves) < 2:
            parser.error("churn takes two or more saves")
        report = churn_report(args.saves, ref, args.building_type, top)
        render = render_churn
    else:
        save = args.save or newest_save()
        if save is None:
            print("no save found")
            return 1
        world = World(save)
        try:
            if args.command == "treaties":
                report, render = treaties_report(world, ref, args.article, top), render_treaties
            elif args.command == "techs":
                report, render = techs_report(world, ref, args.tech, top), render_techs
            else:
                report, render = buildings_report(world, ref, args.building_type, top), render_buildings
        finally:
            world.close()
    if args.json:
        print(json.dumps(report, indent=1))
    else:
        render(report, top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
