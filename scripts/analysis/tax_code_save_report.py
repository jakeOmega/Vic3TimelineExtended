#!/usr/bin/env python3
"""Print a country's legislated tax code from a Victoria 3 save, or diff two saves group by group.

The instrument for the owner's in-game validation of the tax code: what the enacted code, the package slots, the
draft and bill, the obligations and the AI hold in a save, grouped as the schema groups them, and what changed
between two saves. Read-only. Works on both kinds of save.

Usage:
    tax_code_save_report.py [save.v3]                        # which countries hold a tax code
    tax_code_save_report.py [save.v3] --country GBR          # one country's code (TAG, name or id)
    tax_code_save_report.py --diff before.v3 after.v3 [--country GBR] [--full]

With no save named, the newest in the save folder is read. --country takes a tag (any case), a save id (the slot
number or, in a binary save, the full id) or an English country name (vanilla's, then the mod's loc).

The groups are: enacted code, packages, draft and bill, obligations and trust, AI state, drift counters, history,
then caches (the economy snapshot), then anything else. The schema is read at run time from the tables of
docs/systems/tax_code_schema.md, so a new table or row is reported without a code change: a token a table lists is
grouped by the table's heading (a heading this tool does not know becomes a group named after it), every
`te_tax_ai_*` name is AI state by prefix, and a `te_tax_*` name no table lists lands in "other" and is always
printed. The diff's verdict per group is `same`, `changed` (the names, old -> new) or `missing on A` / `missing
on B` (a group one save holds and the other does not; for a country in one save only, every group).

TEXT SAVES. The game writes a plain-text .v3 (`SAV0100...` then `meta_data={`) in debug mode, and the owner's
tax-code saves are likely to be text. A text save is read by a streaming scan, never parsed whole: `mmap.find`
jumps to the top-level `country_manager={`, `laws={` and `amendment_manager={` blocks and each is read line by
line, holding one country's `variables` block at a time. Layout (the engine's own, from 1.14.5 debug saves; the
fixture test_fixtures/tax_code_save/plain_small.v3 copies it):

  country_manager={ database={ <id>={ definition="TAG" ... tax_level=low taxed_goods={ a b }
      variables={ data={ { flag=<name> [tick=N] data={ type=value [identity=<value x 1e5>] } } { ... } }
                  list={ { name="<list>" item={ type=state identity=5 } ... duration={ ... } } } map_data={ ... } } } } }
  laws={ database={ <n>={ law=<type> country=<id> [active=yes] ... } } }
  amendment_manager={ database={ <n>={ type=<amendment type> law=<law record n> sponsor=<ig id> ... } } }

Braces are counted per line (outside quotes), never indentation: the engine writes `} {` between entries,
`}<tabs>key={` on one line and a few lines at column 0. A zero is saved with no `identity` line. The native tax
level (the save omits it when it is medium), the taxed goods and the carrier law's amendments (the amendments on the active `law_te_tax_code` record
of the country, found through the law record id) are read only from a text save; the amendment layout is the
vanilla one, as no save held a tax-code amendment when this was written.

BINARY SAVES go through save_country_probe's decoder (variables and, with read_lists, variable lists). The
native settings are not decoded there.

LIMITS. State variables (`te_tax_relief_state`) are not read in either format. Lists print `state#<id>`, not a
state name. A country with no `te_tax_` variable is not listed (the rule off, or never migrated). The civil-war
MERGE verdicts of save_country_probe --diff are not repeated here. Names resolve only to vanilla's and the mod's
English loc.
"""

import argparse
import dataclasses
import functools
import mmap
import re
import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
for _path in (REPO / "scripts" / "generators", REPO / "scripts" / "analysis", REPO):
    sys.path.insert(0, str(_path))

import check_save_history_order as csho  # noqa: E402
import gen_tax_code as gen  # noqa: E402
import save_country_probe as scp  # noqa: E402

SCHEMA_DOC = REPO / "docs" / "systems" / "tax_code_schema.md"
PREFIX = "te_tax_"
STANDARD_GROUPS = (
    "enacted code", "packages", "draft and bill", "obligations and trust", "AI state", "drift counters", "history",
)
CACHES, OTHER = "caches", "other"
KEYS = tuple(inst.key for inst in gen.INSTRUMENTS)
INSTRUMENT = {inst.key: inst for inst in gen.INSTRUMENTS}
SLOT_NAMES = {number: name for name, number in gen.SLOT_IDS if number}
FIXED = 100000.0
MAX_NAMES = 8

# The group a table feeds, by the heading it sits under. A heading not listed becomes a group named after it
# (and one with "AI" in it is AI state).
HEADING_GROUPS = {
    "Schema": "enacted code",
    "Package slots, history ring and clock": "packages",
    "Obligation slots and trust": "obligations and trust",
    "Records": "draft and bill",
    "The snapshot": CACHES,
}
# Families that sit in a table beside another group's rows, and families the doc describes in prose only. Checked
# first, on the token's own name.
NAME_RULES = tuple((re.compile(pattern), group) for pattern, group in (
    (r"te_tax_ai_", "AI state"),
    (r"te_tax_(drift_|sync_version$|cretry_|cblock_)", "drift counters"),
    (r"te_tax_h(_head$|\d+_)", "history"),
    (r"te_tax_(dr|bl)_on$", "draft and bill"),
    (r"te_tax_(sup|sr|com|off)_", "draft and bill"),
    (r"te_tax_(now|last_month|next_month)$", "enacted code"),
    (r"te_tax_(snap|fisc)_", CACHES),
))
# Tokens holding a month index (te_history_month_index), besides those whose table row opens "the month ...".
MONTH_NAME = re.compile(r"te_tax_.*(_month|_since|_exp|_due|_due0|_deadline|_maint_end|_until)$|te_tax_now$")
MONTH_MEANING = re.compile(r"^(?:the |a )?(?:[\w\-]+ ){0,2}month\b", re.I)
ENUM = re.compile(r"(?<![\w#`])(\d+)\s+([A-Za-z][A-Za-z_' \-]*?)(?=\s*(?:[,;(:.]|$))")


# ------------------------------------------------------------------ the schema doc
def placeholders():
    return {
        "key": "(?:" + "|".join(KEYS) + ")", "s": "[ab]", "n": "[1-8]", "o": "[1-9]", "r": "(?:dr|bl)",
        "ig": "(?:" + "|".join(gen.IGS) + ")", "code": r"\d+",
    }


def template_regex(template):
    """(compiled regex, specificity) for `te_tax_p<s>_<key>`: a placeholder matches its own values, else any word."""
    known, parts, literal, loose = placeholders(), [], 0, 0
    for piece in re.split(r"(<\w+>)", template):
        if piece.startswith("<"):
            name = piece[1:-1]
            parts.append(known.get(name, "[a-z0-9_]+"))
            loose += name not in known
        else:
            parts.append(re.escape(piece))
            literal += len(piece)
    return re.compile("".join(parts)), (literal, -loose)


def parse_enum(cell):
    """{1: "commenced", ...} from a table cell such as "1 commenced, 2 sunset; 3 held_conflict (note)"; 0 is skipped."""
    cell = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)
    return {int(number): name.strip() for number, name in ENUM.findall(cell) if int(number)}


@dataclasses.dataclass
class Pattern:
    template: str
    regex: re.Pattern
    rank: tuple
    group: str
    heading: str
    meaning: str
    is_list: bool

    def sort_key(self):
        return self.rank


class Schema:
    """The tax code's variables as the schema doc's tables list them: which group each belongs to, and the enums."""

    def __init__(self, text):
        self.patterns = []
        self.kind_names, self.obligation_states, self.obligation_kinds, self.package_states = {}, {}, {}, {}
        self.extra_groups = []
        heading, header, in_table = "", "", False
        for line in text.splitlines():
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
            if not line.startswith("|"):
                in_table = False
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not in_table:        # the first row of a table names its columns: only "Variable" tables list tokens
                header, in_table = cells[0].lower(), True
                continue
            if header != "variable" or len(cells) < 2 or "`te_tax_" not in cells[0] or cells[0].startswith("state var"):
                continue
            self._add_row(heading, cells[0], cells[1])
        self.patterns.sort(key=Pattern.sort_key, reverse=True)
        for name, enum in (("te_tax_h<n>_kind", "kind_names"), ("te_tax_o<o>_state", "obligation_states"),
                           ("te_tax_o<o>_kind", "obligation_kinds"), ("te_tax_p<s>_state", "package_states")):
            row = next((p for p in self.patterns if p.template == name), None)
            setattr(self, enum, parse_enum(row.meaning) if row else {})
        for number, key in gen.HISTORY_KIND_KEYS.items():   # the generator's names win; a sunset (2) has none
            self.kind_names[number] = key.removeprefix("te_tax_hist_kind_")

    def _add_row(self, heading, names, meaning):
        group = self._heading_group(heading)
        if group not in STANDARD_GROUPS and group not in (CACHES, OTHER) and group not in self.extra_groups:
            self.extra_groups.append(group)
        templates = []
        for span in re.findall(r"`(_?[\w<>]+)`", names):
            if span.startswith("te_tax_"):
                templates.append(span)
            elif span.startswith("_") and templates:       # "`te_tax_bl_prom_<ig>_kind`, `_arg`": the same stem, a new ending
                templates.append(templates[-1].rsplit("_", 1)[0] + span)
        for template in templates:
            regex, rank = template_regex(template)
            self.patterns.append(Pattern(template, regex, rank, group, heading, meaning, names.startswith("list")))

    @staticmethod
    def _heading_group(heading):
        if heading in HEADING_GROUPS:
            return HEADING_GROUPS[heading]
        return "AI state" if re.search(r"\bAI\b", heading) else heading

    def pattern_for(self, name):
        return next((p for p in self.patterns if p.regex.fullmatch(name)), None)

    def claimed(self, name):
        """Is the name one of the tables' variables (or lists)?"""
        return self.pattern_for(name) is not None

    def group_of(self, name):
        for regex, group in NAME_RULES:
            if regex.match(name):
                return group
        pattern = self.pattern_for(name)
        return pattern.group if pattern else OTHER

    def is_month(self, name):
        if MONTH_NAME.fullmatch(name):
            return True
        pattern = self.pattern_for(name)
        return bool(pattern and MONTH_MEANING.match(pattern.meaning))

    def groups(self):
        """Every group this schema can print, standard ones first."""
        return list(STANDARD_GROUPS) + [CACHES] + self.extra_groups + [OTHER]


@functools.lru_cache(maxsize=4)
def _load(path):
    return Schema(Path(path).read_text(encoding="utf-8-sig"))


def load_schema(path=None):
    return _load(str(path or SCHEMA_DOC))


# ------------------------------------------------------------------ decoding
def fmt_num(value):
    if isinstance(value, float):
        return str(int(value)) if value == int(value) else f"{value:g}"
    return str(value)


def fmt_month(index):
    """A month index (year x 12 + month, January = 0) as year.month: 22033 -> 1836.02. A sentinel prints as a dash."""
    index = int(round(index))
    if index < 0:
        return "—"
    return csho.fmt_month(index) if index >= 12000 else str(index)


def fmt_rate(inst, index):
    """index x step, as a percentage for the percent instruments, else a bare amount."""
    rate = Decimal(int(index)) * inst.step
    if inst.percent:
        return f"{format((rate * 100).normalize(), 'f')}%"
    return format(rate.normalize(), "f")


def fmt_value(schema, name, value):
    if isinstance(value, tuple):
        return " ".join(value) or "(empty)"
    if isinstance(value, float) and schema.is_month(name):
        return fmt_month(value)
    return fmt_num(value)


def number(tokens, name, default=0):
    value = tokens.get(name, default)
    return int(round(value)) if isinstance(value, float) else default


def history_entries(tokens, size=gen.HISTORY_SIZE):
    """The history ring newest first: from te_tax_h_head back round `size` entries, skipping empty ones (kind 0)."""
    head = number(tokens, "te_tax_h_head")
    if not 1 <= head <= size:
        return []
    out = []
    for step in range(size):
        n = (head - 1 - step) % size + 1
        kind = number(tokens, f"te_tax_h{n}_kind")
        if kind:
            out.append({
                "n": n, "kind": kind, "month": number(tokens, f"te_tax_h{n}_month", -1),
                "slot": number(tokens, f"te_tax_h{n}_slot"), "inst": number(tokens, f"te_tax_h{n}_inst"),
                "version": number(tokens, f"te_tax_h{n}_version", -1),
            })
    return out


# ------------------------------------------------------------------ reading saves
@dataclasses.dataclass
class Country:
    cid: int
    tag: str
    vars: dict = dataclasses.field(default_factory=dict)
    lists: dict = dataclasses.field(default_factory=dict)
    native: dict = dataclasses.field(default_factory=dict)

    @property
    def slot(self):
        return self.cid & 0xFFFFFF

    def tokens(self):
        """Every te_tax_ variable and list: {name: float | str | tuple}."""
        out = {k: (f"country#{v[1]}" if isinstance(v, tuple) else v) for k, v in self.vars.items() if k.startswith(PREFIX)}
        out.update({k: tuple(v) for k, v in self.lists.items() if k.startswith(PREFIX)})
        return out


@dataclasses.dataclass
class SaveData:
    path: Path
    kind: str
    date: str
    countries: dict


def brace_delta(line):
    """Opening minus closing braces on one line, quoted text ignored."""
    if b'"' in line:
        line = re.sub(rb'"[^"]*"', b"", line)
    return line.count(b"{") - line.count(b"}")


TEXT_TOKEN = re.compile(r'"[^"]*"|[{}=]|[^\s{}="]+')
ENTRY_LINE = re.compile(rb"^\s*(\d+)=\{\s*$")


def parse_text(text):
    """[(key | None, value)] for Clausewitz text: a value is a string or a nested list; `{ { } { } }` nests."""
    tokens, at = TEXT_TOKEN.findall(text), [0]

    def block():
        items = []
        while at[0] < len(tokens):
            token = tokens[at[0]]
            at[0] += 1
            if token == "}":
                return items
            if token == "{":
                items.append((None, block()))
            elif at[0] < len(tokens) and tokens[at[0]] == "=":
                value = tokens[at[0] + 1]
                at[0] += 2
                items.append((token, block() if value == "{" else value))
            else:
                items.append((None, token))
        return items

    return block()


def child(items, key):
    return next((v for k, v in items if k == key), None)


def read_text_variables(items):
    """({name: value}, {list name: [items]}) from the children of a country's `variables` block."""
    variables, lists = {}, {}
    for key, value in items:
        if key == "data" and isinstance(value, list):
            for _, entry in value:
                name, data = child(entry, "flag"), child(entry, "data")
                if not name or not isinstance(data, list):
                    continue
                kind, identity = child(data, "type"), child(data, "identity")
                if kind == "value":
                    variables[name] = round(int(identity or 0) / FIXED, 3)
                elif kind == "ctry" and identity:
                    variables[name] = ("country", int(identity))
                else:
                    variables[name] = f"{kind}:{identity}" if identity else "flag"
        elif key == "list" and isinstance(value, list):
            for _, entry in value:
                name = (child(entry, "name") or "").strip('"')
                found = []
                for item_key, item in entry:
                    if item_key == "item" and isinstance(item, list):
                        kind = child(item, "type") or "?"
                        found.append(f"{'country' if kind == 'ctry' else kind}#{child(item, 'identity') or '?'}")
                if name:
                    lists[name] = found
    return variables, lists


def block_lines(handle, offset):
    """(depth before, depth after, line) for each line of the top-level block opening at `offset`."""
    handle.seek(offset)
    depth = 0
    for raw in handle:
        after = depth + brace_delta(raw)
        yield depth, after, raw.rstrip(b"\r\n")
        depth = after
        if depth <= 0:
            return


def section_offset(mapped, name):
    at = mapped.find(b"\n" + name + b"={")
    return None if at == -1 else at + 1


def read_text_meta(handle):
    """game_date from the top of a text save: the `meta_data={` block."""
    date = "?"
    handle.seek(0)
    handle.readline()
    for depth, _, line in block_lines(handle, handle.tell()):
        match = re.match(rb"\s*game_date=(\S+)", line)
        if depth == 1 and match:
            date = match.group(1).decode()
    return date


def read_text_save(path, want, require_tax):
    countries = {}
    with open(path, "rb") as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
        date = read_text_meta(handle)
        offset = section_offset(mapped, b"country_manager")
        if offset is not None:
            _read_countries(handle, offset, want, require_tax, countries)
        if countries:
            carrier = _carrier_records(handle, section_offset(mapped, b"laws"), countries)
            _read_amendments(handle, section_offset(mapped, b"amendment_manager"), carrier, countries)
    return SaveData(Path(path), "text", date, countries)


def _read_countries(handle, offset, want, require_tax, countries):
    """country_manager={ database={ <id>={ ... } } }: the entry opens at depth 2, its keys sit at depth 3."""
    entry = None

    def finish():
        if entry is None or entry["tag"] is None or not (want is None or want(entry["cid"], entry["tag"])):
            return
        text = b"\n".join(entry["lines"]).decode("utf-8", "replace")
        if require_tax and PREFIX not in text:
            return
        parsed = parse_text(text)
        variables, lists = read_text_variables(child(parsed, "variables") or [])
        countries[entry["cid"]] = Country(entry["cid"], entry["tag"], variables, lists, entry["native"])

    for depth, after, line in block_lines(handle, offset):
        match = ENTRY_LINE.match(line) if depth == 2 else None
        if match:
            finish()
            # a text save writes `tax_level=` only when the level is not medium (12 countries of the owner's
            # temp.v3 carry one; none says medium)
            entry = {"cid": int(match.group(1)), "tag": None, "lines": [], "native": {"tax_level": "medium"}, "in_vars": False}
            continue
        if entry is None:
            continue
        text = line.strip()
        if entry["in_vars"]:
            entry["lines"].append(line)
            entry["in_vars"] = after > 3
        elif depth == 3:
            if text.startswith(b"definition="):
                entry["tag"] = text.split(b"=", 1)[1].strip(b'"').decode()
            elif text.startswith(b"tax_level="):
                entry["native"]["tax_level"] = text.split(b"=", 1)[1].decode()
            elif text.startswith(b"taxed_goods={"):
                entry["native"]["taxed_goods"] = text[len(b"taxed_goods={"):].strip(b" }").decode().split()
            elif text.startswith(b"variables={"):
                entry["lines"].append(line)
                entry["in_vars"] = after > 3
    finish()


def _entries(handle, offset):
    """(record fields) for each `<n>={ key=value ... }` of a `section={ database={ ... } }` block, depth-3 keys only."""
    record = None
    for depth, _, line in block_lines(handle, offset):
        match = ENTRY_LINE.match(line) if depth == 2 else None
        if match:
            if record is not None:
                yield record
            record = {"n": int(match.group(1))}
        elif record is not None and depth == 3 and b"=" in line:
            key, _, value = line.strip().partition(b"=")
            record[key.decode()] = value.strip(b'"').decode()
    if record is not None:
        yield record


def _carrier_records(handle, offset, countries):
    """{law record id: country id} for each active carrier-law record of a country read."""
    carrier = {}
    for record in _entries(handle, offset) if offset is not None else ():
        if record.get("law") == gen.CARRIER_LAW and record.get("active") == "yes" and record.get("country", "").isdigit():
            if int(record["country"]) in countries:
                carrier[record["n"]] = int(record["country"])
    return carrier


def _read_amendments(handle, offset, carrier, countries):
    for country in countries.values():
        country.native["amendments"] = {}
    for record in _entries(handle, offset) if offset is not None and carrier else ():
        match = re.fullmatch(r"amendment_te_tax_([a-z]+)_(\d+)", record.get("type", ""))
        if match and record.get("law", "").isdigit() and int(record["law"]) in carrier:
            countries[carrier[int(record["law"])]].native["amendments"][match.group(1)] = int(match.group(2))


def read_binary_save(path, want, require_tax):
    save = scp.Save(path, scp.Filters(var=r"^te_tax_"))     # trims each record to the tax code's variables and lists
    countries = {}
    for cid, (start, end, tag, _) in save.extent.items():
        if (want and not want(cid, tag)) or (require_tax and save.blob.find(b"te_tax_", start, end) == -1):
            continue
        rec = save.record(cid)
        countries[cid] = Country(cid, tag, rec["vars"], rec["lists"])
    return SaveData(Path(path), "binary", scp.save_date(path), countries)


def read_save(path, want=None, require_tax=True):
    """SaveData for a text or binary save: the countries (all, or those `want(cid, tag)` accepts) holding te_tax_ state."""
    with open(path, "rb") as handle:
        head = handle.read(256)
    if b"meta_data={" in head:
        return read_text_save(path, want, require_tax)
    return read_binary_save(path, want, require_tax)


# ------------------------------------------------------------------ choosing a country
@functools.lru_cache(maxsize=1)
def country_names():
    """{tag: English name}: vanilla's loc snapshot, then the mod's own country names on top."""
    import json
    names = {}
    snapshot = REPO / "vanilla_parsed" / "localization_english.json"
    if snapshot.is_file():
        names.update({k: v for k, v in json.loads(snapshot.read_text(encoding="utf-8")).items() if re.fullmatch(r"[A-Z][A-Z0-9]{2}", k)})
    line = re.compile(r'^\s*([A-Z][A-Z0-9]{2}):\d*\s+"(.*)"')
    for path in sorted((REPO / "localization" / "english").glob("*.yml")):
        for text in path.read_text(encoding="utf-8-sig").splitlines():
            match = line.match(text)
            if match:
                names[match.group(1)] = match.group(2)
    return names


def selector(spec):
    """A predicate (cid, tag) -> bool for --country: a tag, a save id, or an English name; None for everything."""
    if not spec:
        return None
    spec = spec.strip()
    if spec.isdigit():
        return lambda cid, tag: int(spec) in (cid, cid & 0xFFFFFF)
    folded = spec.casefold()
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{2}", spec):
        return lambda cid, tag: tag.casefold() == folded
    return lambda cid, tag: country_names().get(tag, "").casefold() == folded


# ------------------------------------------------------------------ report
def group_tokens(schema, tokens):
    """{group: {name: value}} for every group (the ones with no token map to {})."""
    grouped = {group: {} for group in schema.groups()}
    for name, value in tokens.items():
        grouped.setdefault(schema.group_of(name), {})[name] = value
    return grouped


def instrument_rows(tokens, rest):
    lines = []
    for key in KEYS:
        name = f"te_tax_en_{key}"
        if name not in tokens:
            continue
        inst, index = INSTRUMENT[key], number(tokens, name)
        exp, succ = number(tokens, f"{name}_exp", -1), number(tokens, f"{name}_succ", -1)
        line = (f"  {inst.label:<22} index {index:<3} rate {fmt_rate(inst, index):<7} "
                f"since {fmt_month(number(tokens, f'{name}_since', -1))}  sunset {fmt_month(exp)}")
        if exp >= 0 and succ >= 0:
            line += f" then index {succ} ({fmt_rate(inst, succ)})"
        versions = [f"{label} {number(tokens, f'te_tax_{label}_{key}')}" for label in ("pver", "xver") if f"te_tax_{label}_{key}" in tokens]
        lines.append(line + (f"  [{', '.join(versions)}]" if versions else ""))
        for suffix in ("", "_since", "_exp", "_succ"):
            rest.pop(name + suffix, None)
        for label in ("pver", "xver"):
            rest.pop(f"te_tax_{label}_{key}", None)
    return lines


def band(value):
    return "none" if value <= 0 else f"{25 * value}%"


def enacted_lines(schema, country, tokens, rest):
    lines = []
    header = [f"{label} {fmt_num(tokens[name])}" for label, name in (
        ("schema", "te_tax_schema"), ("migrated", "te_tax_migrated"), ("code version", "te_tax_code_version"),
        ("migration discrepancy", "te_tax_migration_discrepancy")) if name in tokens]
    if header:
        lines.append("  " + "   ".join(header))
    clock = [f"{label} {fmt_month(tokens[name])}" for label, name in (
        ("now", "te_tax_now"), ("last run", "te_tax_last_month"), ("next due", "te_tax_next_month")) if name in tokens]
    if clock:
        lines.append("  clock   " + "   ".join(clock))
    for name in ("te_tax_schema", "te_tax_migrated", "te_tax_code_version", "te_tax_migration_discrepancy",
                 "te_tax_now", "te_tax_last_month", "te_tax_next_month"):
        rest.pop(name, None)
    lines += instrument_rows(tokens, rest)
    goods = sorted(n[len("te_tax_en_g_"):] for n, v in tokens.items() if n.startswith("te_tax_en_g_") and v == 1.0)
    for name in [n for n in rest if n.startswith("te_tax_en_g_")]:
        rest.pop(name)
    if any(n.startswith("te_tax_en_g_") for n in tokens):
        lines.append(f"  taxed goods (enacted)  {', '.join(goods) or 'none'}")
    for label, name in (("agricultural relief", "te_tax_en_agrel"), ("regional relief", "te_tax_en_regrel")):
        if name in tokens:
            states = tokens.get("te_tax_en_relief_states") if name.endswith("regrel") else None
            lines.append(f"  {label:<22} {band(number(tokens, name))}" + (f"  states: {', '.join(states)}" if states else ""))
            rest.pop(name, None)
    rest.pop("te_tax_en_relief_states", None)
    if "te_tax_customs_held" in tokens:
        lines.append(f"  customs held           {'yes' if number(tokens, 'te_tax_customs_held') else 'no'}")
        rest.pop("te_tax_customs_held")
    levels = dict(getattr(gen, "CUSTOMS_LEVELS", ()))
    customs = [f"{d} {n[len(f'te_tax_en_{d}_'):]} {levels.get(number(tokens, n), number(tokens, n))}"
               for n in sorted(tokens) for d in ("imp", "exp") if n.startswith(f"te_tax_en_{d}_") and number(tokens, n)]
    for name in [n for n in rest if re.match(r"te_tax_en_(imp|exp)_", n)]:
        rest.pop(name)
    if customs:
        lines.append(f"  customs levels (not 0)  {', '.join(customs)}")
    lines += native_lines(country, tokens)
    return lines


def native_lines(country, tokens):
    if not country.native:
        return ["  native settings        not read from a binary save (a plain-text save has them)"]
    lines = []
    if "tax_level" in country.native:
        lines.append(f"  native tax level       {country.native['tax_level']}")
    if "taxed_goods" in country.native:
        enacted = {n[len('te_tax_en_g_'):] for n, v in tokens.items() if n.startswith("te_tax_en_g_") and v == 1.0}
        native = set(country.native["taxed_goods"])
        line = f"  native taxed goods     {', '.join(country.native['taxed_goods']) or 'none'}"
        if enacted != native:
            line += f"   (differs from the code: native only {sorted(native - enacted)}, code only {sorted(enacted - native)})"
        lines.append(line)
    amendments = country.native.get("amendments")
    if amendments is not None:
        shown = ", ".join(f"{INSTRUMENT[k].label} {i}" for k, i in sorted(amendments.items(), key=lambda kv: KEYS.index(kv[0])) if k in INSTRUMENT)
        lines.append(f"  carrier amendments     {shown or 'none'}")
        off = [INSTRUMENT[k].label for k in KEYS if f"te_tax_en_{k}" in tokens and number(tokens, f"te_tax_en_{k}") != amendments.get(k, 0)]
        if off and "te_tax_en_wage" in tokens:
            lines.append(f"  carrier amendments differ from the enacted index for: {', '.join(off)}")
    return lines


def provision_lines(schema, tokens, rest, prefix, indent="    ", sun_months=False):
    """The provisions a package slot / draft / bill holds (not -1), as printable lines."""
    lines = []
    for key in KEYS:
        name = f"{prefix}_{key}"
        index = number(tokens, name, -1)
        for suffix in ("", "_exp", "_succ", "_sun", "_pver"):
            rest.pop(name + suffix, None)
        if index < 0:
            continue
        line = f"{indent}{key} {index} (rate {fmt_rate(INSTRUMENT[key], index)})"
        if sun_months:
            sun = number(tokens, f"{name}_sun")
            line += f"  sunset after {sun} months" if sun else ""
        else:
            exp, succ = number(tokens, f"{name}_exp", -1), number(tokens, f"{name}_succ", -1)
            line += f"  sunset {fmt_month(exp)}" if exp >= 0 else ""
            line += f" (then {succ})" if exp >= 0 and succ >= 0 else ""
        lines.append(line)
    goods = {n[len(f"{prefix}_g_"):]: number(tokens, n) for n in tokens if n.startswith(f"{prefix}_g_")}
    for n in [n for n in rest if n.startswith(f"{prefix}_g_")]:
        rest.pop(n)
    if any(v >= 0 for v in goods.values()):
        tax = sorted(g for g, v in goods.items() if v == 1)
        stop = sorted(g for g, v in goods.items() if v == 0)
        lines.append(f"{indent}goods: " + "; ".join(x for x in (f"tax {', '.join(tax)}" if tax else "", f"stop taxing {', '.join(stop)}" if stop else "") if x))
    for label, suffix in (("agricultural relief", "agrel"), ("regional relief", "regrel")):
        value = number(tokens, f"{prefix}_{suffix}", -1)
        rest.pop(f"{prefix}_{suffix}", None)
        if value >= 0:
            states = tokens.get(f"{prefix}_relief_states")
            lines.append(f"{indent}{label} {band(value)}" + (f" (states: {', '.join(states)})" if suffix == "regrel" and states else ""))
    rest.pop(f"{prefix}_relief_states", None)
    levels = dict(getattr(gen, "CUSTOMS_LEVELS", ()))
    for direction in ("imp", "exp"):
        for n in sorted(x for x in tokens if x.startswith(f"{prefix}_{direction}_")):
            rest.pop(n, None)
            if number(tokens, n, -99) != -99:
                lines.append(f"{indent}customs {direction} {n[len(f'{prefix}_{direction}_'):]} {levels.get(number(tokens, n), number(tokens, n))}")
    return lines


def package_lines(schema, tokens, rest):
    lines = []
    for slot in gen.SLOTS:
        prefix = f"te_tax_p{slot}"
        mine = {n: v for n, v in tokens.items() if n.startswith(prefix) and re.match(rf"te_tax_p{slot}_", n)}
        if not mine:
            continue
        if number(tokens, f"{prefix}_on"):
            state = number(tokens, f"{prefix}_state")
            lines.append(f"  slot {slot}   {schema.package_states.get(state, f'state {state}'):<13} due {fmt_month(number(tokens, f'{prefix}_due', -1))}"
                         f"   seq {number(tokens, f'{prefix}_seq')}   approved for {fmt_month(number(tokens, f'{prefix}_due0', -1))}")
            for name in (f"{prefix}_on", f"{prefix}_state", f"{prefix}_due", f"{prefix}_seq", f"{prefix}_due0"):
                rest.pop(name, None)
            lines += provision_lines(schema, tokens, rest, prefix)
        else:
            payload = sorted(n for n in mine if n not in (f"{prefix}_on", f"{prefix}_state", f"{prefix}_due", f"{prefix}_seq")
                             and fmt_num(mine[n]) not in ("-1", "-99", "0"))
            note = f"   unread payload (inherited or stale): {', '.join(payload)}" if payload else ""
            lines.append(f"  slot {slot}   free{note}")
            for name in mine:
                rest.pop(name, None)
    return lines


def reason_text(tokens, ig):
    reasons = [f"{r} {number(tokens, f'te_tax_sr_{ig}_{r}'):+d}" for r in getattr(gen, "SUPPORT_REASONS", ()) if f"te_tax_sr_{ig}_{r}" in tokens]
    return ", ".join(reasons)


def offer_text(schema, tokens, ig):
    kind = number(tokens, f"te_tax_off_{ig}_kind")
    if not kind:
        return ""
    names = {1: "cut a tax", 2: "agricultural relief", 3: "untax a staple"}
    label = names.get(kind) or (f"promise ({schema.obligation_kinds.get(kind - gen.OFFER_PROMISE, kind)})" if kind > gen.OFFER_PROMISE else f"kind {kind}")
    return f"offer: {label} arg {number(tokens, f'te_tax_off_{ig}_arg')}, for revision {number(tokens, f'te_tax_off_{ig}_rev')}"


def bill_lines(schema, tokens, rest):
    lines = []
    for record, label in (("dr", "draft"), ("bl", "bill")):
        prefix = f"te_tax_{record}"
        mine = [n for n in tokens if n.startswith(prefix + "_")]
        if f"{prefix}_on" not in tokens and not mine:
            continue
        opened = number(tokens, f"{prefix}_on")
        rest.pop(f"{prefix}_on", None)
        if not opened:
            payload = [n for n in mine if not n.startswith(f"{prefix}_prom_") and not n.startswith(f"{prefix}_got_") and fmt_num(tokens[n]) not in ("-1", "-99", "0")]
            lines.append(f"  {label:<7} closed" + (f"   unread payload (inherited or stale): {len(payload)} tokens" if payload else ""))
            for n in mine:
                rest.pop(n, None)
            continue
        text = f"  {label:<7} open"
        if record == "bl":
            text += (f"   revision {number(tokens, 'te_tax_bl_rev')}   {'minor' if number(tokens, 'te_tax_bl_minor') else 'major'}"
                     f"   last revised day {number(tokens, 'te_tax_bl_day')}")
        lines.append(text + f"   due {fmt_month(number(tokens, f'{prefix}_due', -1))}")
        for suffix in ("due", "rev", "minor", "day"):
            rest.pop(f"{prefix}_{suffix}", None)
        lines += provision_lines(schema, tokens, rest, prefix, sun_months=True)
        if record == "bl":
            for ig in gen.IGS:
                if number(tokens, f"te_tax_bl_prom_{ig}_kind", -1) >= 0:
                    kind = number(tokens, f"te_tax_bl_prom_{ig}_kind")
                    lines.append(f"    promise to {ig}: {schema.obligation_kinds.get(kind, kind)}, arg {number(tokens, f'te_tax_bl_prom_{ig}_arg', -1)}, target {number(tokens, f'te_tax_bl_prom_{ig}_target', -1)}")
                for n in [n for n in tokens if n.startswith(f"te_tax_bl_prom_{ig}_") or n.startswith(f"te_tax_bl_got_{ig}_")]:
                    if n.startswith("te_tax_bl_got_") and number(tokens, n) == 1:
                        lines.append(f"    {ig} gained clause {n.rsplit('_', 1)[1]}")
                    rest.pop(n, None)
    groups = [ig for ig in gen.IGS if any(n.startswith((f"te_tax_sup_{ig}", f"te_tax_com_{ig}", f"te_tax_sr_{ig}_", f"te_tax_off_{ig}_")) for n in tokens)]
    if groups:
        lines.append("  interest groups")
    for ig in groups:
        commit = {1: "committed", 0: "persuadable", -1: "red line"}.get(number(tokens, f"te_tax_com_{ig}", 9), "")
        parts = [f"score {number(tokens, f'te_tax_sup_{ig}')}" if f"te_tax_sup_{ig}" in tokens else "", f"{commit} (revision {number(tokens, f'te_tax_com_{ig}_rev')})" if commit else "",
                 reason_text(tokens, ig), offer_text(schema, tokens, ig)]
        lines.append(f"    {ig:<18} " + "   ".join(p for p in parts if p))
        for n in [n for n in tokens if re.match(rf"te_tax_(sup_{ig}$|com_{ig}(_rev)?$|sr_{ig}_|off_{ig}_)", n)]:
            rest.pop(n, None)
    return lines


def obligation_lines(schema, tokens, rest):
    lines = []
    institutions = {n: key.removeprefix("institution_") for n, key in gen.OBL_INSTITUTIONS}
    wage = dict(gen.OBL_WAGE_LEVELS)
    for o in gen.OBLIGATION_SLOTS:
        prefix = f"te_tax_o{o}"
        mine = [n for n in tokens if re.fullmatch(rf"{prefix}_\w+", n)]
        if not mine:
            continue
        state = number(tokens, f"{prefix}_state")
        if not number(tokens, f"{prefix}_on"):
            outcome = schema.obligation_states.get(state) if state else None
            lines.append(f"  o{o}   free" + (f"   last outcome {outcome}" if outcome else ""))
        else:
            kind, arg = number(tokens, f"{prefix}_kind"), number(tokens, f"{prefix}_arg")
            base, target = number(tokens, f"{prefix}_baseline"), number(tokens, f"{prefix}_target")
            igs = {i + 1: ig for i, ig in enumerate(gen.IGS)}
            detail = {1: f"{institutions.get(arg, arg)} level {base} to {target}",
                      3: f"military wage {wage.get(base, base)} to {wage.get(target, target)}"}.get(
                          kind, f"condition held when proposed: {'yes' if base else 'no'}")
            text = (f"  o{o}   {schema.obligation_states.get(state, f'state {state}'):<11} {schema.obligation_kinds.get(kind, f'kind {kind}')}"
                    f"   {detail}   to {igs.get(number(tokens, f'{prefix}_ig'), '?')}")
            slot = number(tokens, f"{prefix}_slot")
            for label, name in (("deadline", "deadline"), ("maintenance ends", "maint_end")):
                if number(tokens, f"{prefix}_{name}", -1) >= 0:
                    text += f"   {label} {fmt_month(number(tokens, f'{prefix}_{name}'))}"
            text += f"   slot {SLOT_NAMES.get(slot, '-')}   revision {number(tokens, f'{prefix}_rev')}"
            if number(tokens, f"{prefix}_maint_only"):
                text += "   maintains existing provision"
            lines.append(text)
            if number(tokens, f"{prefix}_streak") or number(tokens, f"{prefix}_fails"):
                lines.append(f"       streak {number(tokens, f'{prefix}_streak')}   failing checks {number(tokens, f'{prefix}_fails')}")
        for name in mine:
            rest.pop(name, None)
    for ig in gen.IGS:
        if f"te_tax_trust_{ig}" in tokens:
            month = number(tokens, f"te_tax_trust_{ig}_month", -1)
            lines.append(f"  trust  {ig:<18} {number(tokens, f'te_tax_trust_{ig}'):+d}   last changed {fmt_month(month)}")
            rest.pop(f"te_tax_trust_{ig}", None)
            rest.pop(f"te_tax_trust_{ig}_month", None)
    return lines


def drift_lines(schema, tokens, rest):
    lines = []
    if "te_tax_sync_version" in tokens and "te_tax_code_version" in tokens:
        synced = number(tokens, "te_tax_sync_version") == number(tokens, "te_tax_code_version")
        lines.append(f"  drift counted          {'yes' if synced else 'no'}   (sync version {number(tokens, 'te_tax_sync_version')}, code version {number(tokens, 'te_tax_code_version')})")
    return lines


def history_lines(schema, tokens, rest):
    entries = history_entries(tokens)
    lines = []
    for entry in entries:
        kind = schema.kind_names.get(entry["kind"], f"kind {entry['kind']}")
        extra = ""
        if entry["kind"] == 2 and 1 <= entry["inst"] <= len(KEYS):
            extra = f" ({KEYS[entry['inst'] - 1]})"
        elif entry["kind"] == 15:
            extra = f" ({entry['inst']} levels)"
        elif entry["kind"] == 18 and entry["inst"] == 1:
            extra = " (bill withdrawn)"
        slot = f"slot {SLOT_NAMES[entry['slot']]}" if entry["slot"] in SLOT_NAMES else ""
        lines.append(f"  {fmt_month(entry['month'])}  {kind + extra:<28} {slot:<7} version {entry['version']}")
    for n in [n for n in rest if re.match(r"te_tax_h(_head|\d+_(month|kind|slot|inst|version))$", n)]:
        rest.pop(n)
    return lines or ["  (empty)"]


def generic_lines(schema, tokens, label=None):
    lines = [f"  {name} = {fmt_value(schema, name, value)}" for name, value in sorted(tokens.items())]
    return ([f"  {label}:"] + ["  " + line for line in lines]) if label and lines else lines


RENDERERS = {
    "enacted code": enacted_lines, "packages": lambda s, c, t, r: package_lines(s, t, r),
    "draft and bill": lambda s, c, t, r: bill_lines(s, t, r), "obligations and trust": lambda s, c, t, r: obligation_lines(s, t, r),
    "drift counters": lambda s, c, t, r: drift_lines(s, t, r), "history": lambda s, c, t, r: history_lines(s, t, r),
}


def render_group(schema, country, group, all_tokens, group_toks):
    rest = dict(group_toks)
    renderer = RENDERERS.get(group)
    lines = renderer(schema, country, all_tokens, rest) if renderer else []
    lines += generic_lines(schema, rest, "other tokens" if lines else None)
    return lines or ["  (no tokens)"]


def describe_country(schema, save, country):
    """The report for one country, as a list of lines."""
    kind = "plain-text" if save.kind == "text" else "binary"
    tokens = country.tokens()
    lines = [f"Tax code: {country.tag} (id {country.slot})  [{kind} save, game date {save.date}]  {save.path.name}"]
    grouped = group_tokens(schema, tokens)
    for group in schema.groups():
        if group not in STANDARD_GROUPS and not grouped.get(group):
            continue
        lines.append(f"== {group} ==")
        lines += render_group(schema, country, group, tokens, grouped.get(group, {}))
    return lines


def summary_lines(save, countries):
    lines = [f"{save.path.name}  [{save.kind} save, game date {save.date}]: {len(countries)} countries hold tax-code state", ""]
    lines.append(f"  {'tag':<6}{'id':<7}{'schema':<8}{'code version':<14}tokens")
    for country in sorted(countries, key=lambda c: (c.tag, c.cid)):
        t = country.tokens()
        lines.append(f"  {country.tag:<6}{country.slot:<7}{number(t, 'te_tax_schema', '-'):<8}{number(t, 'te_tax_code_version', '-'):<14}{len(t)}")
    lines += ["", "Pass --country <TAG|name|id> for one country's code."]
    return lines


# ------------------------------------------------------------------ diff
def verdict(a, b):
    """(`same` | `changed` | `missing on A` | `missing on B`, [names changed]) for one group's tokens on both sides."""
    if a == b:
        return "same", []
    if not a:
        return "missing on A", []
    if not b:
        return "missing on B", []
    return "changed", sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))


def pair_countries(a, b):
    """[(country on A | None, country on B | None)]: by id, then the one left of a tag on each side."""
    pairs = [(a[cid], b[cid]) for cid in sorted(set(a) & set(b))]
    left_a, left_b = [a[c] for c in sorted(set(a) - set(b))], [b[c] for c in sorted(set(b) - set(a))]
    for country in list(left_a):
        twin = [c for c in left_b if c.tag == country.tag]
        if len(twin) == 1 and sum(c.tag == country.tag for c in left_a) == 1:
            pairs.append((country, twin[0]))
            left_a.remove(country)
            left_b.remove(twin[0])
    return sorted(pairs + [(c, None) for c in left_a] + [(None, c) for c in left_b], key=lambda p: ((p[0] or p[1]).tag, (p[0] or p[1]).cid))


def diff_lines(schema, pair, full):
    ca, cb = pair
    ta, tb = (ca.tokens() if ca else {}), (cb.tokens() if cb else {})
    first = ca or cb
    heading = f"{first.tag} (id {ca.slot if ca else cb.slot}" + (f" -> id {cb.slot}" if ca and cb and ca.slot != cb.slot else "") + ")"
    if not ca or not cb:
        heading += f"  only in {'B' if cb else 'A'}"
    ga, gb = group_tokens(schema, ta), group_tokens(schema, tb)
    lines, changed = [heading], 0
    for group in schema.groups():
        a, b = ga.get(group, {}), gb.get(group, {})
        if group not in STANDARD_GROUPS and not (a or b):
            continue
        what, names = verdict(a, b)
        changed += what != "same"
        text = f"  {group:<22} {what}"
        if names:
            shown = [f"{n} {fmt_value(schema, n, a[n]) if n in a else '-'} -> {fmt_value(schema, n, b[n]) if n in b else '-'}" for n in names]
            if full:
                text += "\n" + "\n".join(f"      {s}" for s in shown)
            else:
                text += "   " + "; ".join(shown[:MAX_NAMES]) + (f"; (+{len(shown) - MAX_NAMES} more, --full)" if len(shown) > MAX_NAMES else "")
        lines.append(text)
    return lines, changed


# ------------------------------------------------------------------ command line
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("save", nargs="?", type=Path, help="a .v3 save, text or binary (default: the newest)")
    parser.add_argument("--country", help="TAG, English name or save id")
    parser.add_argument("--diff", nargs=2, type=Path, metavar=("BEFORE", "AFTER"), help="compare two saves group by group")
    parser.add_argument("--full", action="store_true", help="list every changed name in a --diff, not the first %d" % MAX_NAMES)
    parser.add_argument("--schema", type=Path, help="the schema doc to read (default docs/systems/tax_code_schema.md)")
    args = parser.parse_args(argv)
    if args.diff and args.save:
        parser.error("--diff takes its two saves itself: --diff BEFORE AFTER")
    schema = load_schema(args.schema)
    want = selector(args.country)
    try:
        if args.diff:
            return run_diff(schema, args.diff, want, args.full, bool(args.country))
        save = args.save
        if save is None:
            save = next(iter(csho.find_saves()), None)
        if save is None:
            print("no save found")
            return 1
        return run_report(schema, read_save(save, want, require_tax=not args.country), args.country)
    except (ValueError, OSError) as exc:       # an unreadable or empty save file
        print(exc)
        return 1


def run_report(schema, save, spec):
    countries = list(save.countries.values())
    if spec and not countries:
        print(f"{save.path.name}: no country matches '{spec}' (a tag, an English name or a save id)")
        return 1
    if not countries:
        print(f"{save.path.name}: no country holds tax-code state (the game rule is off, or no code has been migrated)")
        return 0
    if not spec:
        print("\n".join(summary_lines(save, countries)))
        return 0
    blocks = []
    for country in countries:
        if country.tokens():
            blocks.append("\n".join(describe_country(schema, save, country)))
        else:
            blocks.append(f"{country.tag} (id {country.slot}) holds no tax-code variables (the game rule is off, or no code has been migrated)")
    print("\n\n".join(blocks))
    return 0


def run_diff(schema, paths, want, full, named):
    before, after = (read_save(p, want, require_tax=not named) for p in paths)
    print(f"Tax code diff: A {before.path.name} [{before.date}]  ->  B {after.path.name} [{after.date}]")
    changed = 0
    for pair in pair_countries(before.countries, after.countries):
        lines, count = diff_lines(schema, pair, full)
        changed += count
        print("\n".join(lines))
    if not before.countries and not after.countries:
        print("no country holds tax-code state in either save")
    elif not changed:
        print("no tax-code change")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
