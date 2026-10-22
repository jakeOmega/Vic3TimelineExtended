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
`pops={ database={ <id>={ … } … } }`, `states=`, `country_manager=`, `laws=`, `technology=`, `institutions=`,
each record's own fields one tab in. The fields read:
    pops             type, location (state id), workforce, dependents, num_literate, wealth,
                     previous_quality_of_life (the pop's standard of living last week), workplace (absent for a pop
                     with no job: phase 2 step 4's unemployment, state_unemployment)
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
             "social_class", "workplace"),
    "states": ("country", "incorporation", "devastation", "region"),
    "state_region_manager": ("template", "pollution"),
    "country_manager": ("definition",),
    "laws": ("law", "country", "active"),
    "technology": ("country", "acquired_technologies"),
    "institutions": ("institution", "investment", "country"),
}
# Saves are read line by line from a 16 MB buffer: the archive drive (/mnt/d under WSL) reads at about 17 MB/s,
# and Python's default 8 KB reads took about 90 s a save there against 10-25 s (#894's analysis, 2026-10-11)
READ_BUFFER = 16 * 1024 * 1024
_FIELD = re.compile(r"^\t([a-z_]+)=(.*)$")
_SOCIAL_CLASS = re.compile(r"^\t\tsocial_class=([a-z_]+)$")
# a pop's food security: the value inside its food_security={ } block (phase 2 step 4, predict)
_FOOD_SECURITY = re.compile(r"^\t\tvalue=([-0-9.]+)$")
# a country's or a state's timed modifiers (timed_modifiers={ modifiers={ { modifier=... multiplier=... } } }),
# read as [name, multiplier] pairs inside that block only
_TIMED_MODIFIER = re.compile(r"^\t+modifier=([A-Za-z0-9_]+)$")
_TIMED_MULTIPLIER = re.compile(r"^\t+multiplier=(-?[0-9.]+)$")
# static modifiers that carry state_fertility_means_add, by their value (the census reads them in game;
# the harness, from a save): te_demog_modifiers.txt
STATIC_MEANS_ADD = {"te_demog_family_limitation": M.P.FAMILY_LIMITATION_MEANS}
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
    in_timed = False   # inside the current record's timed_modifiers block
    in_food = False    # inside the current pop's food_security block
    with open(path, encoding="utf-8", errors="replace", buffering=READ_BUFFER) as fh:
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
                    record_id, record, in_timed, in_food = m.group(1), {}, False, False
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
                m = _FOOD_SECURITY.match(line.rstrip("\n")) if in_food else None
                if m:
                    record["food_security"] = m.group(1)
            elif in_timed:
                # only inside the record's own timed_modifiers block: a country's budget trends carry multiplier=
                # lines and its timed_enactment_modifiers modifier= lines at the same depth
                m = _TIMED_MODIFIER.match(line.rstrip("\n"))
                if m:
                    record.setdefault("timed_modifiers", []).append([m.group(1), 1.0])
                else:
                    m = _TIMED_MULTIPLIER.match(line.rstrip("\n"))
                    if m and record.get("timed_modifiers"):
                        record["timed_modifiers"][-1][1] = float(m.group(1))
            if depth == 3 and section in ("country_manager", "states") and line.startswith("\ttimed_modifiers={"):
                in_timed = True
            if depth == 3 and section == "pops" and line.startswith("\tfood_security={"):
                in_food = True
            depth += opened - closed
            if depth <= 3:   # back at the record's own fields (an empty block opens and closes on one line)
                in_timed = in_food = False
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
    agrarian: float = 0.0    # Peasants and Farmers (the walk's te_dg_agr_share; Late Marriage's inheritance driver)
    strata_people: dict = field(default_factory=lambda: defaultdict(float))
    strata_wealth: dict = field(default_factory=lambda: defaultdict(float))
    sol_bins: dict = field(default_factory=lambda: defaultdict(float))
    laws: set = field(default_factory=set)
    techs: set = field(default_factory=set)
    institutions: dict = field(default_factory=dict)   # institution -> investment level
    incorporated_people: float = 0.0                   # people in its incorporated states
    states: int = 0
    means_add: float = 0.0                              # static modifiers' state_fertility_means_add
    crowding: float = 0.0    # a state's migration penalty from crowding (state_inputs); a country's stays 0
    malaria: int = 0         # a state's malaria trait level from its state region (state_inputs; calibration step 3)

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

    @property
    def agrarian_share(self):
        return self.agrarian / self.population if self.population else 0.0


RURAL_TYPES = {"peasants", "farmers", "slaves"}
AGRARIAN_TYPES = {"peasants", "farmers"}   # the walk's te_dg_agr_share


def is_incorporated(state_record):
    """A state counts as incorporated once its incorporation reaches 1 (institution modifiers apply there)."""
    return _num(state_record.get("incorporation")) >= 1


def _add_pop(c, rec, size, incorporated):
    """One pop's people, SoL, literacy, wealth and class into a country's or a state's sums."""
    sol = _num(rec.get("previous_quality_of_life"))
    wealth = _num(rec.get("wealth"))
    c.population += size
    if incorporated:
        c.incorporated_people += size
    c.sol_x_size += sol * size
    c.wealth_tfr_x_size += M.wealth_tfr(sol) * size
    c.literate += _num(rec.get("num_literate"))
    c.workforce += _num(rec.get("workforce"))
    c.wealth_x_size += wealth * size
    if rec.get("type") in RURAL_TYPES:
        c.rural += size
    if rec.get("type") in AGRARIAN_TYPES:
        c.agrarian += size
    s = STRATA_OF_CLASS.get(rec.get("social_class"), "lower")
    c.strata_people[s] += size
    c.strata_wealth[s] += wealth * size
    c.sol_bins[min(int(sol // 5) * 5, 40)] += size


_MALARIA = []


def _malaria_levels():
    """{state region: malaria level} from the map files (demographics_regions.malaria_levels), read once."""
    if not _MALARIA:
        import demographics_regions as R
        _MALARIA.append(R.malaria_levels())
    return _MALARIA[0]


def state_inputs(sections):
    """{tag: [(state id, CountryInputs of that state's own pops, incorporated)]}. The census works state
    by state, so a curve that bends (the poverty term at SoL 9) needs each state's own SoL and literacy;
    laws, techs and institutions are the owner's (country_inputs). A state's malaria level is its state region's
    trait (calibration step 3); the owner's techs carry the control that switches it off."""
    countries = country_inputs(sections)
    tags = {cid: rec.get("definition", "").strip('"') for cid, rec in sections["country_manager"].items()}
    owner_of_state = {sid: rec.get("country") for sid, rec in sections["states"].items()}
    incorporated = {sid for sid, rec in sections["states"].items() if is_incorporated(rec)}
    malaria = _malaria_levels()
    per = {}
    for rec in sections["pops"].values():
        size = _num(rec.get("workforce")) + _num(rec.get("dependents"))
        sid = rec.get("location")
        tag = tags.get(owner_of_state.get(sid))
        if size <= 0 or not tag:
            continue
        if (tag, sid) not in per:
            per[(tag, sid)] = CountryInputs(tag, states=1)
        _add_pop(per[(tag, sid)], rec, size, sid in incorporated)
    out = {}
    for (tag, sid), st in per.items():
        c = countries[tag]
        st.laws, st.techs, st.institutions, st.means_add = c.laws, c.techs, c.institutions, c.means_add
        st.crowding = sum(M.P.MIGRATION_CROWDING_PULL_PER_MULT * mult
                          for name, mult in sections["states"].get(sid, {}).get("timed_modifiers", ())
                          if name == "migration_crowding")
        st.malaria = malaria.get(sections["states"].get(sid, {}).get("region", "").strip('"'), 0)
        out.setdefault(tag, []).append((sid, st, sid in incorporated))
    return out


def state_unemployment(sections):
    """{state id: (workforce, workforce with no workplace)} from the pops: the share of the workforce with no work, as
    phase 2 step 4's youth bulge takes it. In game the census stores te_state_unemployment_share (te_dg_unemp, 2026-10-17):
    the engine's state_unemployment_rate, the idle workforce over all the people, over the workforce's share of the
    people. That equals this count where the engine's figure is per person, as the self-checks unemployment_rate_read
    and unemployment_share_read test. A save holds neither figure, so this is the stand-in, the walk's own count
    (te_dg_unemp_walk)."""
    out = {}
    for rec in sections["pops"].values():
        wf = _num(rec.get("workforce"))
        if wf <= 0:
            continue
        sid = rec.get("location")
        total, idle = out.get(sid, (0.0, 0.0))
        out[sid] = (total + wf, idle + (wf if not rec.get("workplace") else 0.0))
    return out


def state_pollution(sections):
    """{state id: its state region's pollution, 0 to POLLUTION_MAX} for the states whose region the save names
    (predict's Pollution Impact line, owner 2026-10-11). Pollution is region-wide: split states share it."""
    by_region = {rec.get("template"): _num(rec.get("pollution")) for rec in sections.get("state_region_manager", {}).values()}
    out = {}
    for sid, rec in sections.get("states", {}).items():
        region = rec.get("region", "").strip('"')
        if region in by_region:
            out[sid] = by_region[region]
    return out


def state_regions(sections):
    """{state id: its state region's key} for the states whose record names one (`region="STATE_X"`)."""
    out = {}
    for sid, rec in sections.get("states", {}).items():
        region = rec.get("region", "").strip('"')
        if region:
            out[sid] = region
    return out


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
        _add_pop(c, rec, size, rec.get("location") in incorporated)
    for cid, rec in sections["country_manager"].items():
        c = get(cid)
        if c:
            c.means_add = sum(STATIC_MEANS_ADD.get(name, 0.0) * mult for name, mult in rec.get("timed_modifiers", []))
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


def country_budgets(path):
    """{tag: {"gdp", "income", "expenses"}} for every country with a GDP record (phase 2 step 2's pension fit):
    the latest sample of the country's GDP channel (yearly, as the `gdp` script value), and its weekly income and
    expenses, each the sum of the budget's weekly_income / weekly_expenses vectors (every category). Read from
    country_manager's records: `\tdefinition=`, `\t\tweekly_income={ … }`, and inside `\tgdp={` the channel's
    `\t\t\t\tindex=` and `\t\t\t\tvalues={ … }` (a ring, oldest first, `index` samples written)."""
    check_plain_text(path)
    out, cur, in_gdp, section, depth = {}, None, False, False, 0
    with open(path, encoding="utf-8", errors="replace", buffering=READ_BUFFER) as fh:
        for line in fh:
            if not section:
                if line == "country_manager={\n":
                    section, depth = True, 1
                continue
            if depth == 2:
                m = _RECORD.match(line)
                if m:
                    cur, in_gdp = out.setdefault(m.group(1), {}), False
            if cur is not None:
                if line.startswith("\tdefinition="):
                    cur["tag"] = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("\t\tweekly_income={"):
                    cur["income"] = sum(_num(x) for x in line.split("{", 1)[1].split("}")[0].split())
                elif line.startswith("\t\tweekly_expenses={"):
                    cur["expenses"] = sum(_num(x) for x in line.split("{", 1)[1].split("}")[0].split())
                elif line.startswith("\tgdp={"):
                    in_gdp = True
                elif in_gdp and line.startswith("\t\t\t\tindex="):
                    cur["gdp_index"] = int(_num(line.split("=", 1)[1]))
                elif in_gdp and line.startswith("\t\t\t\tvalues={"):
                    vals = [_num(x) for x in line.split("{", 1)[1].split("}")[0].split()]
                    i = min(cur.get("gdp_index", len(vals)), len(vals))
                    cur["gdp"] = vals[i - 1] if i > 0 else 0.0
                    in_gdp = False
            depth += line.count("{") - line.count("}")
            if depth == 0:
                break
    return {v["tag"]: {"gdp": v["gdp"], "income": v.get("income", 0.0), "expenses": v.get("expenses", 0.0)}
            for v in out.values() if v.get("tag") and v.get("gdp", 0.0) > 0}


def read_variables(path, country_vars, state_vars, raw=()):
    """(countries, states) from a plain-text save's script variables and active laws.

    countries: {id: {"tag": str, "laws": set, "vars": {name: value}}} for the variables named in
    country_vars; states: {id: {"owner": country id, "vars": {...}}} for state_vars. A variable named
    in raw keeps its identity as written, a string: a scope reference such as te_dg_primate_state
    (`type=state`, `identity=<state id>`), which isn't fixed point. A record's nested blocks can
    restart at column 0 (`0={` inside a country), so records are told by brace depth, not by
    indentation. Raises NotPlainText as read_sections does.
    """
    check_plain_text(path)
    countries, states = {}, {}
    law_owner = {}
    section, rec, flag, law = None, None, None, {}
    depth = 0
    with open(path, encoding="utf-8", errors="replace", buffering=READ_BUFFER) as fh:
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
                    value = text[9:] if flag in raw else fixed_point(text[9:])
                    (countries if section == "country_manager" else states)[rec]["vars"][flag] = value
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
