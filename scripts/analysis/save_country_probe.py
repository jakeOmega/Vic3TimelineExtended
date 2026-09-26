"""Dump or diff per-country script state in a Victoria 3 save: variables, modifiers, journal entries.

Read-only, and needs nothing but the .v3 file. Built for questions a save answers
at once and a running game answers slowly; the first was "what does the winner of
a civil war inherit?" (docs/guides/scripting_best_practices.md § "What a Civil
War's Winner Inherits").

Usage:
    save_country_probe.py [save.v3] --tag GER
    save_country_probe.py [save.v3] --var '^(nuclear_|nd_)' --modifier '^nuclear_power$' --je je_nuclear_program
    save_country_probe.py --diff before.v3 after.v3 --tag GER
    save_country_probe.py --diff before.v3 after.v3 --var '^nd_'

With no save named, the newest in the save folder is read. A country is shown if
it matches every filter given: --tag (repeatable), --var / --modifier (a regex; it
holds a matching variable / modifier), --je (it owns an entry of that type; any
exact name works, prefix or not).
--var / --modifier / --je also choose what is printed: only the parts they name,
and only the matching names. With --tag alone everything is printed, journal
entries limited to the running ones (every country holds an inactive record for
each entry it could ever take). Each save takes a few seconds.

In --diff mode a tag is compared if any of its objects matches in either save,
and then all of its objects are, so a civil war's two sides stay together. When
one of two objects has taken the tag and the other is gone or flagless — a civil
war that ended, either way — a MERGE section says which of the loser's variables
the survivor received and, where both held one, whose value it kept. Diff
against the first save after the war: a later one also counts what script put
back since (nuclear_power, restored by je_nuclear_program's weekly pulse, then
looks inherited).

BINARY LAYOUT (worked out on 1.14 saves, 2026-09-25; token names are unknown,
only their numbers). A non-ironman .v3 is a 24-byte header plus a zip whose
`gamestate` and `meta` entries are Clausewitz binary (read_gamestate in
check_save_history_order.py).

  tokens    0x0001 '='  0x0003 '{'  0x0004 '}'  0x000c i32  0x0014 u32
            0x000e bool (1 byte)  0x000d f32  0x0167 f64  0x029c i64  0x009c u64
            0x000f / 0x0017 string (u16 length + bytes). Any other 2-byte value
            is a bare token: a key, or an enum-like value.

  country   u32:<id> = { [<flag> = bool]*  0x07dd = "<TAG>"  ... }
            The top byte of an id is a reuse counter; the low 24 bits are the
            slot (0x0100005a is slot 90, reused once). The leading bool flags are
            not decoded, but a civil war shows two of them: 0x538b sat on the
            original during the war and moved to the revolutionary when it won
            (read it as "the object c:TAG resolves to"); 0x4386 sat on the
            revolutionary during the war and cleared on the win (read it as
            "revolutionary"). A normal country's block ends exactly where the
            next country header begins, which is the check that the tokenizer
            covers every value type present; a block that runs past it is
            reported as a WARNING.

  variables (a direct child of the country block)
            0x0555 = { 0x00f0 = { { 0x0384 = "<name>" [other keys]
                                     0x00f0 = { 0x00e1 = <kind> 0x00db = <value> } } ... } }
            Kind 0x02d2 is a script value: i64 fixed point, value * 1e5, and
            exactly 0 is saved with no 0x00db at all. Kind 0x333c is a country
            reference (the value is its id), printed as country#<id>(<TAG>), or
            (gone) when no country block has that id. Other kinds print raw.

  modifiers (a direct child of the country block)
            0x333b = { 0x0d00 = { { 0x000b = u32:<instance>  0x0c1f = "<name>"
                                    0x0cf8 = i32:<start>  [0x0cf9 = i32:<end>] ... } ... } }

  journal entries (their own manager, outside the country blocks)
            u32:<id> = { 0x00e1 = "<type>"  0x2840 = u32:<owner country id>  [0x2ab2 = bool]
                         ...  0x333b = { <modifier list, laid out as a country's> } ... }
            0x2ab2 reads as "active": 1 on running entries, 0 on inactive ones
            (every country holds a record for each entry it could ever take).
            Other databases (combat units, …) share the type/owner keys, so
            records are told apart by name (is_journal_type): the je_ prefix,
            the few prefix-less vanilla entries (pinned against vanilla_parsed
            by the test), or whatever --je names exactly.

  meta      0x3245 = i32 game date in hours: days = v // 24,
            year = days // 365 - 5000, day of year = days % 365.
"""

import io
import re
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_save_history_order import find_saves, read_gamestate  # noqa: E402

FIXED = 100000.0
KEY_DEF, KEY_VARS, KEY_DATA, KEY_NAME, KEY_VAL, KEY_KIND = 0x07DD, 0x0555, 0x00F0, 0x0384, 0x00DB, 0x00E1
KEY_MODS, KEY_MODLIST, KEY_MODNAME = 0x333B, 0x0D00, 0x0C1F
KIND_VALUE, KIND_COUNTRY = 0x02D2, 0x333C
FLAG_TAG_HOLDER, FLAG_REVOLUTIONARY = 0x538B, 0x4386
FLAG_GUESSES = {FLAG_TAG_HOLDER: "tag holder?", FLAG_REVOLUTIONARY: "revolutionary?"}
# Every mod journal entry and all but these vanilla ones (1.14) start with je_.
VANILLA_JE_WITHOUT_PREFIX = {"central_america_falls_apart", "ragamuffin_war", "ragamuffin_war_minors", "slave_owner_paranoia"}

DEF_RE = re.compile(rb"\xdd\x07\x01\x00(?:\x0f|\x17)\x00(..)", re.S)
HDR_RE = re.compile(rb"\x14\x00(....)\x01\x00\x03\x00", re.S)
JE_TYPE_RE = re.compile(rb"\xe1\x00\x01\x00(?:\x0f|\x17)\x00(..)", re.S)
JE_OWNER = b"\x40\x28\x01\x00\x14\x00"
JE_ACTIVE = b"\xb2\x2a\x01\x00\x0e\x00"
MONTHS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


# ---------------------------------------------------------------- decoding
def tokens(b, i, end):
    """Yield (offset, kind, value) for every token in b[i:end]."""
    while i < end - 1:
        t = struct.unpack_from("<H", b, i)[0]
        o = i
        i += 2
        if t == 0x0003:
            yield o, "{", None
        elif t == 0x0004:
            yield o, "}", None
        elif t == 0x0001:
            yield o, "=", None
        elif t in (0x000F, 0x0017):
            n = struct.unpack_from("<H", b, i)[0]
            yield o, "str", b[i + 2 : i + 2 + n].decode("latin1")
            i += 2 + n
        elif t == 0x000C:
            yield o, "int", struct.unpack_from("<i", b, i)[0]
            i += 4
        elif t == 0x0014:
            yield o, "int", struct.unpack_from("<I", b, i)[0]
            i += 4
        elif t == 0x029C:
            yield o, "int", struct.unpack_from("<q", b, i)[0]
            i += 8
        elif t == 0x009C:
            yield o, "int", struct.unpack_from("<Q", b, i)[0]
            i += 8
        elif t == 0x000E:
            yield o, "bool", b[i]
            i += 1
        elif t == 0x000D:
            yield o, "float", struct.unpack_from("<f", b, i)[0]
            i += 4
        elif t == 0x0167:
            yield o, "float", struct.unpack_from("<d", b, i)[0]
            i += 8
        else:
            yield o, "tok", t


def parse_block(b, start):
    """Parse `<key> = { ... }` at `start`; return (items, end_offset).

    items is a list of (key, value): key is None for a bare value, and a value
    is a scalar (kind, v) or a nested items list.
    """
    stream = tokens(b, start, len(b))
    next(stream), next(stream)  # the key and '='
    if next(stream)[1] != "{":
        raise ValueError(f"no block at 0x{start:x}")

    def parse_list():
        items, pending = [], None
        while True:
            o, k, v = next(stream)
            if k == "}":
                if pending is not None:
                    items.append((None, pending))
                return items, o + 2
            if k == "=":
                key, pending = pending, None
                _, k2, v2 = next(stream)
                items.append((key, parse_list()[0] if k2 == "{" else (k2, v2)))
                continue
            if pending is not None:
                items.append((None, pending))
                pending = None
            if k == "{":
                items.append((None, parse_list()[0]))
            else:
                pending = (k, v)

    return parse_list()


def get(items, key):
    for k, v in items:
        if k == ("tok", key):
            return v
    return None


def country_headers(b):
    """[(offset, id, tag, flags)] for every country block, in file order."""
    out = []
    for m in DEF_RE.finditer(b):
        n = struct.unpack("<H", m.group(1))[0]
        tag = b[m.end() : m.end() + n]
        if n > 6 or not re.fullmatch(rb"[A-Z0-9_]{3,6}", tag):
            continue
        window = b[max(0, m.start() - 48) : m.start()]
        heads = list(HDR_RE.finditer(window))
        if not heads:
            continue
        between = window[heads[-1].end() :]
        if len(between) % 7 or not all(
            between[i + 2 : i + 6] == b"\x01\x00\x0e\x00" for i in range(0, len(between), 7)
        ):
            continue
        flags = {struct.unpack("<H", between[i : i + 2])[0]: between[i + 6] for i in range(0, len(between), 7)}
        cid = struct.unpack("<I", heads[-1].group(1))[0]
        out.append((m.start() - len(window) + heads[-1].start(), cid, tag.decode(), flags))
    out.sort()
    return out


def read_variables(items):
    """{name: value}: floats for script values, ("country", id) for country refs, else raw text."""
    out = {}
    block = get(items, KEY_VARS)
    data = get(block, KEY_DATA) if isinstance(block, list) else None
    for _, entry in data or []:
        if not isinstance(entry, list):
            continue
        name = get(entry, KEY_NAME)
        if not name or name[0] != "str":
            continue
        wrap = get(entry, KEY_DATA)
        kind = get(wrap, KEY_KIND) if isinstance(wrap, list) else None
        val = get(wrap, KEY_VAL) if isinstance(wrap, list) else None
        if kind == ("tok", KIND_VALUE):
            out[name[1]] = round(val[1] / FIXED, 3) if val and val[0] == "int" else 0.0
        elif kind == ("tok", KIND_COUNTRY) and val and val[0] == "int":
            out[name[1]] = ("country", val[1])
        elif val is None:
            out[name[1]] = "flag"
        else:
            kind_text = f"0x{kind[1]:04x}" if kind and kind[0] == "tok" else str(kind)
            out[name[1]] = f"{kind_text}:{val[1] if not isinstance(val, list) else '{...}'}"
    return out


def read_modifiers(items):
    block = get(items, KEY_MODS)
    entries = get(block, KEY_MODLIST) if isinstance(block, list) else None
    names = []
    for _, entry in entries or []:
        if isinstance(entry, list):
            name = get(entry, KEY_MODNAME)
            if name and name[0] == "str":
                names.append(name[1])
    return sorted(names)


def is_journal_type(name, wanted=None):
    """Other databases (combat units, …) share the type/owner keys; tell entries apart by name."""
    return name == wanted or name.startswith("je_") or name in VANILLA_JE_WITHOUT_PREFIX


def journal_entries(b, wanted=None):
    """{owner id: [(type, active or None, record offset), ...]} for every journal-entry record."""
    out = {}
    for m in JE_TYPE_RE.finditer(b):
        n = struct.unpack("<H", m.group(1))[0]
        at = m.end() + n
        if b[at : at + 6] != JE_OWNER:
            continue
        name = b[m.end() : at].decode("latin1")
        if not is_journal_type(name, wanted):
            continue
        owner = struct.unpack_from("<I", b, at + 6)[0]
        active = b[at + 16] if b[at + 10 : at + 16] == JE_ACTIVE else None
        # The record opens `u32:<id> = {` ten bytes before its type key.
        out.setdefault(owner, []).append((name, active, m.start() - 10))
    return out


def save_date(save_path):
    raw = Path(save_path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw[raw.find(b"PK\x03\x04") :])) as archive:
        meta = archive.read("meta") if "meta" in archive.namelist() else b""
    at = meta.find(b"\x45\x32\x01\x00\x0c\x00")
    if at == -1:
        return "?"
    days = struct.unpack_from("<i", meta, at + 6)[0] // 24
    year, day = days // 365 - 5000, days % 365
    month = 0
    while day >= MONTHS[month]:
        day -= MONTHS[month]
        month += 1
    return f"{year}.{month + 1}.{day + 1}"


# ---------------------------------------------------------------- selection
class Filters:
    def __init__(self, tags=(), var=None, modifier=None, je=None):
        self.tags = set(tags)
        self.var = re.compile(var) if var else None
        self.modifier = re.compile(modifier) if modifier else None
        self.je = je

    @staticmethod
    def _bytes_probe(pattern):
        """A bytes regex that matches the raw block whenever `pattern` can match a name in it, or None.

        Names sit in the block as plain length-prefixed strings, so the pattern
        works on the bytes once its outer ^ / $ anchors are dropped (which only
        widens it). A pattern with any other anchor gets no probe.
        """
        core = pattern[1:] if pattern.startswith("^") else pattern
        core = core[:-1] if core.endswith("$") and not core.endswith("\\$") else core
        if "^" in core.replace("[^", "") or "$" in core.replace("\\$", ""):
            return None
        try:
            return re.compile(core.encode("latin1"))
        except (re.error, UnicodeEncodeError):
            return None

    def prefilter(self, segment, tag):
        """Cheap test before decoding a block; False only when the country cannot match."""
        if self.tags and tag not in self.tags:
            return False
        for regex in (self.var, self.modifier):
            probe_re = self._bytes_probe(regex.pattern) if regex else None
            if probe_re and not probe_re.search(segment):
                return False
        return True

    def matches(self, rec):
        """Called on a trimmed record: does it hold something every content filter asked for?"""
        if self.var and not rec["vars"]:
            return False
        if self.modifier and not rec["modifiers"]:
            return False
        if self.je and not rec["journal"]:
            return False
        return True

    def trim(self, rec):
        if self.var:
            rec["vars"] = {k: v for k, v in rec["vars"].items() if self.var.search(k)}
        if self.modifier:
            rec["modifiers"] = [m for m in rec["modifiers"] if self.modifier.search(m)]
        if self.je:
            rec["journal"] = [(t, a) for t, a in rec["journal"] if t == self.je]
        else:
            # Every country carries a record for each entry it could ever take;
            # without --je only the running ones are worth printing.
            rec["journal"] = [(t, a) for t, a in rec["journal"] if a]
        return rec

    def shows(self, part):
        """Print every part of a record, unless a content filter names the parts wanted."""
        if not (self.var or self.modifier or self.je):
            return True
        return {"vars": self.var, "modifiers": self.modifier, "journal": self.je}[part] is not None


class Save:
    """One save's gamestate, its country index and its journal-entry records."""

    def __init__(self, path, filters):
        self.path = Path(path)
        self.filters = filters
        self.blob = read_gamestate(path)
        heads = country_headers(self.blob)
        self.extent = {}
        for pos, (start, cid, tag, flags) in enumerate(heads):
            nxt = heads[pos + 1][0] if pos + 1 < len(heads) else len(self.blob)
            self.extent[cid] = (start, nxt, tag, flags)
        self.tags = {cid: e[2] for cid, e in self.extent.items()}
        self.journal = journal_entries(self.blob, filters.je)

    def record(self, cid):
        start, nxt, tag, flags = self.extent[cid]
        items, end = parse_block(self.blob, start)
        rec = {
            "id": cid,
            "tag": tag,
            "flags": flags,
            "vars": read_variables(items),
            "modifiers": read_modifiers(items),
            "journal": sorted((t, a) for t, a, _ in self.journal.get(cid, [])),
            "warning": f"block ends at 0x{end:x}, past the next header at 0x{nxt:x}" if end > nxt else None,
        }
        self.filters.trim(rec)
        # An entry record carries its own modifier block, laid out like a
        # country's. Decoded only for the entries that will be shown.
        shown = set(rec["journal"])
        rec["journal_modifiers"] = {}
        for t, a, at in self.journal.get(cid, []):
            if (t, a) in shown:
                rec["journal_modifiers"].setdefault(t, []).extend(read_modifiers(parse_block(self.blob, at)[0]))
        return rec

    def select(self):
        """{id: record} for every country block that matches the filters."""
        out = {}
        for cid, (start, nxt, tag, _) in self.extent.items():
            if self.filters.je and not any(e[0] == self.filters.je for e in self.journal.get(cid, ())):
                continue
            if not self.filters.prefilter(self.blob[start:nxt], tag):
                continue
            rec = self.record(cid)
            if self.filters.matches(rec):
                out[cid] = rec
        return out


# ---------------------------------------------------------------- output
def fmt_value(v, tags):
    """A country reference names its tag in the same save, or says it is gone."""
    if isinstance(v, tuple) and v[0] == "country":
        return f"country#{v[1]}({tags.get(v[1], 'gone')})"
    return str(v)


def fmt_flags(flags):
    if not flags:
        return "none"
    return " ".join(
        f"0x{k:04x}={v}" + (f" ({FLAG_GUESSES[k]})" if k in FLAG_GUESSES else "") for k, v in sorted(flags.items())
    )


def fmt_journal(entries):
    return ", ".join(f"{t}({'active' if a else 'inactive' if a == 0 else '?'})" for t, a in entries) or "-"


def describe(rec, tags, filters, indent="  "):
    lines = [f"{indent}{rec['tag']} id={rec['id']} (slot {rec['id'] & 0xFFFFFF})  flags: {fmt_flags(rec['flags'])}"]
    if rec["warning"]:
        lines.append(f"{indent}  WARNING: {rec['warning']}")
    if filters.shows("journal"):
        label = "journal" if filters.je else "journal (active)"
        lines.append(f"{indent}  {label}: {fmt_journal(rec['journal'])}")
        for t, mods in sorted(rec["journal_modifiers"].items()):
            if mods:
                lines.append(f"{indent}    {t} modifiers ({len(mods)}): {', '.join(sorted(mods))}")
    if filters.shows("modifiers"):
        lines.append(f"{indent}  modifiers ({len(rec['modifiers'])}): {', '.join(rec['modifiers']) or '-'}")
    if filters.shows("vars"):
        lines.append(f"{indent}  variables ({len(rec['vars'])}):")
        lines += [f"{indent}    {k} = {fmt_value(v, tags)}" for k, v in sorted(rec["vars"].items())]
    return "\n".join(lines)


def report(save_path, filters):
    save = Save(save_path, filters)
    recs = save.select()
    print(f"{save_path}  [{save_date(save_path)}]  {len(save.tags)} country blocks, {len(recs)} shown")
    for rec in sorted(recs.values(), key=lambda r: (r["tag"], r["id"])):
        print(describe(rec, save.tags, filters))


def merge_section(loser, survivor_before, survivor_after, tags):
    """What a civil war's survivor did with the loser's variables and modifiers (within the filters)."""
    lv, sb, sa = loser["vars"], survivor_before["vars"], survivor_after["vars"]
    both = [k for k in lv if k in sb and lv[k] != sb[k]]
    inherited = sorted(k for k in lv if k not in sb and k in sa)
    kept = sorted(k for k in both if sa.get(k) == sb[k])
    took = sorted(k for k in both if sa.get(k) == lv[k])
    moved = sorted(k for k in both if sa.get(k) not in (sb[k], lv[k]))
    dropped = sorted(k for k in lv if k not in sa)
    mods = sorted(set(loser["modifiers"]) - set(survivor_before["modifiers"]))
    arrived = [m for m in mods if m in survivor_after["modifiers"]]
    je_lines = []
    for t, loser_mods in sorted(loser["journal_modifiers"].items()):
        if loser_mods:
            kept_mods = set(survivor_after["journal_modifiers"].get(t, [])) & set(loser_mods)
            je_lines.append(f"       {t}: {len(loser_mods)} on the loser, {len(kept_mods)} of them on the survivor now")
    lines = [
        f"   MERGE: loser id {loser['id']} -> survivor id {survivor_after['id']}",
        f"     inherited (the loser's only, now on the survivor): {len(inherited)}",
        f"     both held, differing: survivor kept its own {len(kept)}, took the loser's {len(took)},"
        f" neither (moved since) {len(moved)}",
        f"     the loser's variables not on the survivor: {len(dropped)} {dropped[:10]}",
        f"     the loser's own modifiers: {len(mods)}, also on the survivor now: {len(arrived)} {arrived}",
    ]
    if je_lines:
        lines.append("     the loser's journal-entry modifiers (shown entries only):")
        lines += je_lines
    lines += [f"       took the loser's: {k} = {fmt_value(lv[k], tags)}" for k in took]
    return "\n".join(lines)


def civil_war_outcome(ra, rz):
    """(survivor id, loser id) when a tag had two objects before and the war between them has ended.

    Ended means one of the two now holds the tag (FLAG_TAG_HOLDER) and the other
    is gone or has lost every flag — its dead record lingers for a couple of
    weeks. Covers either side winning.
    """
    if len(ra) != 2:
        return None
    for survivor in ra:
        loser = next(cid for cid in ra if cid != survivor)
        holds = survivor in rz and FLAG_TAG_HOLDER in rz[survivor]["flags"]
        dead = loser not in rz or not rz[loser]["flags"]
        if holds and dead:
            return survivor, loser
    return None


def diff(before, after, filters):
    """Per tag: objects gone and new, and what changed on each that survived."""
    a, z = Save(before, filters), Save(after, filters)
    # A tag is in if any of its objects matches in either save; then all of its
    # objects are compared, so a civil war's two sides stay together even when
    # only one of them holds what the filters ask for.
    wanted = {r["tag"] for r in a.select().values()} | {r["tag"] for r in z.select().values()}
    print(f"BEFORE {before}  [{save_date(before)}]\nAFTER  {after}  [{save_date(after)}]\n")
    for tag in sorted(wanted):
        ra = {cid: a.record(cid) for cid, t in a.tags.items() if t == tag}
        rz = {cid: z.record(cid) for cid, t in z.tags.items() if t == tag}
        lines = []
        for cid in sorted(set(ra) - set(rz)):
            lines.append(f"   gone: id {cid} (no longer in the save)")
        for cid in sorted(set(rz) - set(ra)):
            lines.append("   new:\n" + describe(rz[cid], z.tags, filters, "     "))
        for cid in sorted(set(ra) & set(rz)):
            p, q = ra[cid], rz[cid]
            ch = [
                f"{k}: {fmt_value(p['vars'].get(k, '-'), a.tags)} -> {fmt_value(q['vars'].get(k, '-'), z.tags)}"
                for k in sorted(set(p["vars"]) | set(q["vars"]))
                if p["vars"].get(k) != q["vars"].get(k)
            ]
            ch += [f"+modifier {m}" for m in q["modifiers"] if m not in p["modifiers"]]
            ch += [f"-modifier {m}" for m in p["modifiers"] if m not in q["modifiers"]]
            if p["journal"] != q["journal"]:
                ch.append(f"journal: {fmt_journal(p['journal'])} -> {fmt_journal(q['journal'])}")
            for t in sorted(set(p["journal_modifiers"]) | set(q["journal_modifiers"])):
                before_mods = set(p["journal_modifiers"].get(t, []))
                after_mods = set(q["journal_modifiers"].get(t, []))
                ch += [f"+{t} modifier {m}" for m in sorted(after_mods - before_mods)]
                ch += [f"-{t} modifier {m}" for m in sorted(before_mods - after_mods)]
            if p["flags"] != q["flags"]:
                ch.append(f"flags: {fmt_flags(p['flags'])} -> {fmt_flags(q['flags'])}")
            if ch:
                lines.append(f"   id {cid} changed:\n" + "\n".join(f"     {c}" for c in ch))
        ended = civil_war_outcome(ra, rz)
        if ended:
            survivor, loser = ended
            lines.append(merge_section(ra[loser], ra[survivor], rz[survivor], a.tags))
        if lines:
            print(f"== {tag}: ids {sorted(ra)} -> {sorted(rz)}")
            print("\n".join(lines) + "\n")


def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("saves", nargs="*", type=Path)
    parser.add_argument("--diff", action="store_true", help="compare two saves: before after")
    parser.add_argument("--tag", action="append", default=[], help="country tag (repeatable)")
    parser.add_argument("--var", help="regex over variable names")
    parser.add_argument("--modifier", help="regex over modifier names")
    parser.add_argument("--je", help="journal-entry type")
    args = parser.parse_args(argv)
    filters = Filters(args.tag, args.var, args.modifier, args.je)
    if args.diff:
        if len(args.saves) != 2:
            parser.error("--diff takes exactly two saves: before after")
        diff(*args.saves, filters)
        return 0
    saves = args.saves or find_saves()[:1]
    if not saves:
        print("no save found")
        return 1
    for save in saves:
        report(save, filters)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
