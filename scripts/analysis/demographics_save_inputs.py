#!/usr/bin/env python3
"""Read what the demographics harness needs from a plain-text Victoria 3 save.

Usage:
    demographics_save_inputs.py summary SAVE [--tag GBR ...]
    demographics_save_inputs.py slice SAVE --tag GBR [--tag POR] [--max-pops 300] -o OUT

A plain-text save is what the game writes in debug mode (it starts `SAV0…` and then
`meta_data={`). Binary saves aren't read here (read_sections raises NotPlainText, and the
commands print the message and exit 1); `save_country_probe.py` covers those for
variables and laws but not pops. Spec: docs/superpowers/specs/2026-10-08-demographics-design.md
§11.1 (the harness is driven by SoL, literacy, technology and law read from saves).

Layout, as written by 1.14.5 (checked on an 1836 save, 2026-10-08): top-level sections
`pops={ database={ <id>={ … } … } }`, `states=`, `country_manager=`, `laws=`, `technology=`,
each record's own fields one tab in. The fields read:
    pops             type, location (state id), workforce, dependents, num_literate, wealth,
                     previous_quality_of_life (the pop's standard of living last week)
    states           country (owner id), incorporation (1 once incorporated; a fraction while
                     incorporating; absent in an unincorporated state)
    country_manager  definition (the tag, quoted)
    laws             law, country, active (yes on the law in force)
    technology       country, acquired_technologies={ … }
    institutions     institution, investment (its level), country
A pop with no workforce or dependents field is empty (size 0).
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import demographics_model as M

SECTIONS = {
    "pops": ("type", "location", "workforce", "dependents", "num_literate", "wealth", "previous_quality_of_life",
             "social_class"),
    "states": ("country", "incorporation"),
    "country_manager": ("definition",),
    "laws": ("law", "country", "active"),
    "technology": ("country", "acquired_technologies"),
    "institutions": ("institution", "investment", "country"),
}
_FIELD = re.compile(r"^\t([a-z_]+)=(.*)$")
_SOCIAL_CLASS = re.compile(r"^\t\tsocial_class=([a-z_]+)$")
# social class -> strata, from game/common/social_classes/*.txt (1.14.5). Not in the
# vanilla_parsed/ snapshot; an unknown class counts as lower.
STRATA_OF_CLASS = {
    "upper_class": "upper", "middle_class": "middle", "lower_class": "lower",
    "brahmins": "upper", "kshatriyas": "middle", "vaishyas": "middle", "shudras": "lower", "dalit": "lower",
    "strata_samurai_high": "upper", "strata_samurai_low": "middle", "strata_religious": "middle",
    "strata_commoners_peasants": "lower", "strata_commoners_townspeople": "lower", "strata_outcastes": "lower",
}
_RECORD = re.compile(r"^(\d+)=\{\s*$")


class NotPlainText(ValueError):
    """The file is not a plain-text save (a binary or zipped one, or not a save at all)."""


def check_plain_text(path):
    """Raise NotPlainText unless the save's second line is `meta_data={`.

    A plain-text save is `SAV0…` on line 1 and `meta_data={` on line 2. A binary or zipped
    save has binary bytes there, and scanning it for sections finds none, so without this
    check it reads as an empty save and the commands print plausible zeros.
    """
    with open(path, "rb") as fh:
        fh.readline(256)
        second = fh.readline(64).rstrip(b"\r\n")
    if second != b"meta_data={":
        raise NotPlainText(f"{path} is not a plain-text save (its second line is not `meta_data={{`); "
                           "save in debug mode for plain text, or unzip/convert it first")


def read_sections(path, wanted=tuple(SECTIONS)):
    """{section: {record_id: {field: raw string}}} for the wanted sections.

    Raises NotPlainText (a ValueError) naming the file when it isn't a plain-text save.
    """
    check_plain_text(path)
    out = {name: {} for name in wanted}
    section = None
    depth = 0
    record_id = None
    record = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if section is None:
                if depth == 0 and line.endswith("={\n") and not line.startswith("\t"):
                    name = line[:-3]
                    if name in out:
                        section, depth = name, 1
                        continue
                depth += line.count("{") - line.count("}")
                continue
            opened, closed = line.count("{"), line.count("}")
            if record is None:
                m = _RECORD.match(line)
                if m and depth == 2:
                    record_id, record = m.group(1), {}
                    depth += 1
                    continue
                depth += opened - closed
                if depth == 0:
                    section = None
                continue
            if depth == 3:
                m = _FIELD.match(line.rstrip("\n"))
                if m and m.group(1) in SECTIONS[section]:
                    record[m.group(1)] = m.group(2).strip()
            elif depth == 4 and section == "pops":
                m = _SOCIAL_CLASS.match(line.rstrip("\n"))
                if m:
                    record["social_class"] = m.group(1)
            depth += opened - closed
            if depth == 2:
                out[section][record_id] = record
                record = None
    return out


def _num(raw, default=0.0):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


@dataclass
class CountryInputs:
    tag: str
    population: float = 0.0
    sol_x_size: float = 0.0
    wealth_tfr_x_size: float = 0.0       # sum of the wealth curve at each pop's SoL x its size
    literate: float = 0.0
    workforce: float = 0.0
    wealth_x_size: float = 0.0
    rural: float = 0.0
    strata_people: dict = field(default_factory=lambda: defaultdict(float))
    strata_wealth: dict = field(default_factory=lambda: defaultdict(float))
    sol_bins: dict = field(default_factory=lambda: defaultdict(float))
    laws: set = field(default_factory=set)
    techs: set = field(default_factory=set)
    institutions: dict = field(default_factory=dict)   # institution -> investment level
    incorporated_people: float = 0.0                   # people in its incorporated states
    states: int = 0

    @property
    def sol(self):
        return self.sol_x_size / self.population if self.population else 0.0

    @property
    def wealth_tfr(self):
        """The pop-weighted wealth term (Inputs.wealth_tfr), not the curve at the mean SoL; None for no people."""
        return self.wealth_tfr_x_size / self.population if self.population else None

    @property
    def literacy(self):
        return self.literate / self.workforce if self.workforce else 0.0

    @property
    def incorporated_share(self):
        return self.incorporated_people / self.population if self.population else 0.0

    @property
    def urban_share(self):
        return 1 - self.rural / self.population if self.population else 0.0


RURAL_TYPES = {"peasants", "farmers", "slaves"}


def is_incorporated(state_record):
    """A state counts as incorporated once its incorporation reaches 1 (institution modifiers apply there)."""
    return _num(state_record.get("incorporation")) >= 1


def country_inputs(sections):
    """{tag: CountryInputs} from read_sections()'s output."""
    tags = {cid: rec.get("definition", "").strip('"') for cid, rec in sections["country_manager"].items()}
    owner_of_state = {sid: rec.get("country") for sid, rec in sections["states"].items()}
    incorporated = {sid for sid, rec in sections["states"].items() if is_incorporated(rec)}
    out = {}

    def get(cid):
        tag = tags.get(cid)
        if not tag:
            return None
        if tag not in out:
            out[tag] = CountryInputs(tag)
        return out[tag]

    for sid, cid in owner_of_state.items():
        c = get(cid)
        if c:
            c.states += 1
    for rec in sections["pops"].values():
        size = _num(rec.get("workforce")) + _num(rec.get("dependents"))
        if size <= 0:
            continue
        c = get(owner_of_state.get(rec.get("location")))
        if not c:
            continue
        sol = _num(rec.get("previous_quality_of_life"))
        wealth = _num(rec.get("wealth"))
        c.population += size
        if rec.get("location") in incorporated:
            c.incorporated_people += size
        c.sol_x_size += sol * size
        c.wealth_tfr_x_size += M.wealth_tfr(sol) * size
        c.literate += _num(rec.get("num_literate"))
        c.workforce += _num(rec.get("workforce"))
        c.wealth_x_size += wealth * size
        if rec.get("type") in RURAL_TYPES:
            c.rural += size
        s = STRATA_OF_CLASS.get(rec.get("social_class"), "lower")
        c.strata_people[s] += size
        c.strata_wealth[s] += wealth * size
        c.sol_bins[min(int(sol // 5) * 5, 40)] += size
    for rec in sections["laws"].values():
        if rec.get("active") == "yes":
            c = get(rec.get("country"))
            if c:
                c.laws.add(rec.get("law"))
    for rec in sections["technology"].values():
        c = get(rec.get("country"))
        if c:
            c.techs.update(rec.get("acquired_technologies", "").strip("{} ").split())
    for rec in sections.get("institutions", {}).values():
        c = get(rec.get("country"))
        if c and rec.get("institution"):
            c.institutions[rec["institution"]] = int(_num(rec.get("investment")))
    return out


# ---- script variables (Wealth Concentration as the game holds it) -----------------------

_SECTION = re.compile(r"^([a-z_]+)=\{$")


def fixed_point(raw):
    """A script value's saved `identity`: i64 x 1e5 written unsigned, so a negative wraps past 2^63."""
    v = int(raw)
    if v >= 2 ** 63:
        v -= 2 ** 64
    return v / 1e5


def read_variables(path, country_vars, state_vars):
    """(countries, states) from a plain-text save's script variables and active laws.

    countries: {id: {"tag": str, "laws": set, "vars": {name: value}}} for the variables named in
    country_vars; states: {id: {"owner": country id, "vars": {...}}} for state_vars. A record's
    nested blocks can restart at column 0 (`0={` inside a country), so records are told by brace
    depth, not by indentation. Raises NotPlainText as read_sections does.
    """
    check_plain_text(path)
    countries, states = {}, {}
    law_owner = {}
    section, rec, flag, law = None, None, None, {}
    depth = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            before = depth
            depth += line.count("{") - line.count("}")
            if before == 0:
                m = _SECTION.match(line.rstrip("\n"))
                section = m.group(1) if m else None
                continue
            if section not in ("country_manager", "states", "laws"):
                continue
            if before == 2:
                m = _RECORD.match(line)
                if m:
                    rec, flag, law = m.group(1), None, {}
                    if section == "country_manager":
                        countries[rec] = {"tag": "", "laws": set(), "vars": {}}
                    elif section == "states":
                        states[rec] = {"owner": None, "vars": {}}
                continue
            text = line.strip()
            if section == "laws":
                if before == 3 and "=" in text:
                    key, _, value = text.partition("=")
                    law[key] = value
                    if law.get("active") == "yes" and "law" in law and "country" in law:
                        law_owner.setdefault(law["country"], set()).add(law["law"])
                continue
            if before == 3 and section == "country_manager" and text.startswith("definition="):
                countries[rec]["tag"] = text[11:].strip('"')
            elif before == 3 and section == "states" and text.startswith("country="):
                states[rec]["owner"] = text[8:]
            elif text.startswith("flag="):
                flag = text[5:]
            elif text.startswith("identity=") and flag:
                wanted = country_vars if section == "country_manager" else state_vars
                if flag in wanted:
                    (countries if section == "country_manager" else states)[rec]["vars"][flag] = fixed_point(text[9:])
                flag = None
    for cid, laws in law_owner.items():
        if cid in countries:
            countries[cid]["laws"] = laws
    return countries, states


def write_slice(sections, tags, max_pops, out_path):
    """A small save holding only the read fields of the named countries' first pops."""
    ids = {cid for cid, rec in sections["country_manager"].items() if rec.get("definition", "").strip('"') in tags}
    states = {sid for sid, rec in sections["states"].items() if rec.get("country") in ids}
    keep = {
        "country_manager": {cid: rec for cid, rec in sections["country_manager"].items() if cid in ids},
        "states": {sid: rec for sid, rec in sections["states"].items() if sid in states},
        "laws": {i: r for i, r in sections["laws"].items() if r.get("country") in ids and r.get("active") == "yes"},
        "technology": {i: r for i, r in sections["technology"].items() if r.get("country") in ids},
        "institutions": {i: r for i, r in sections.get("institutions", {}).items() if r.get("country") in ids},
        "pops": {},
    }
    candidates = [(pid, rec) for pid, rec in sections["pops"].items()
                  if rec.get("location") in states and rec.get("workforce")]
    stride = max(1, len(candidates) // max_pops)
    keep["pops"] = dict(candidates[::stride][:max_pops])
    lines = ["SAV0100demographics-test-slice", "meta_data={", '\tversion="1.14.5"', "}"]
    for name in ("pops", "country_manager", "states", "laws", "technology", "institutions"):
        lines += [f"{name}={{", "\tdatabase={"]
        for rid, rec in keep[name].items():
            lines.append(f"{rid}={{")
            lines += [f"\t{k}={v}" for k, v in rec.items()]
            lines.append("}")
        lines += ["\t}", "}"]
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {k: len(v) for k, v in keep.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summary")
    s.add_argument("save")
    s.add_argument("--tag", action="append", default=[])
    sl = sub.add_parser("slice")
    sl.add_argument("save")
    sl.add_argument("--tag", action="append", required=True)
    sl.add_argument("--max-pops", type=int, default=300)
    sl.add_argument("-o", "--out", required=True)
    args = ap.parse_args(argv)
    try:
        sections = read_sections(args.save)
    except NotPlainText as e:
        print(e, file=sys.stderr)
        return 1
    if args.cmd == "slice":
        print(write_slice(sections, set(args.tag), args.max_pops, args.out))
        return 0
    inputs = country_inputs(sections)
    for tag in (args.tag or sorted(inputs, key=lambda t: -inputs[t].population)[:15]):
        c = inputs.get(tag)
        if c:
            print(f"{tag} pop={c.population:,.0f} states={c.states} sol={c.sol:.1f} literacy={c.literacy:.2f} "
                  f"urban={c.urban_share:.2f} laws={len(c.laws)} techs={len(c.techs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
