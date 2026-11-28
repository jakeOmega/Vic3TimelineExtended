"""Generate the Private Actors sectors: every company type's buildings, goods, staffing, technologies and law stances.

Every company is a firm (docs/superpowers/specs/2026-11-28-actors-firms-design.md § 5.1). Script can't read a
company's building types, goods or methods, and has no technology iterator and no link from a key to a law's
stance, so this writes what each firm type knows about itself, from the merged vanilla + mod data and the
hand-set table in ``private_actors_config.py`` (§ 8.1's law table, the sector features, the numbers):

* ``common/scripted_effects/te_pa_gen_effects.txt``
  - ``te_pa_gen_assess`` (company scope): one ``if``/``else_if`` chain on ``is_company_type``, a branch a type,
    writing the firm's sector readings into company variables ``te_pa_g_*`` (the list is in the file's
    preamble). Every reading is reset to 0 first, so a type with no branch reads as nothing known.
  - ``te_pa_gen_tech_cache`` (any scope): one ``any_country`` per technology in the union of the sectors' lists,
    setting ``te_pa_gen_tech_held_<index>`` (a global variable, 1) where some country holds it and removing it
    where none does. ``te_pa_gen_assess`` reads it for the technology gap; run it once a year.
  - ``te_pa_gen_law_pick`` (company scope): the stances on the covered laws in force, open and being enacted,
    with each one's index, into ``te_pa_g_law_*`` (for the reason line).
  - ``te_pa_gen_law_selfcheck`` (country scope): the tally behind a self-check of the open-law reading.
  - helpers ``te_pa_gen_clear_good``, ``te_pa_gen_read_good``, ``te_pa_gen_tech_check``,
    ``te_pa_gen_tech_cache_one``, ``te_pa_gen_law_pick_in_force``, ``_open``, ``_enacting``.
* ``common/scripted_triggers/te_pa_gen_triggers.txt``: ``te_pa_gen_is_<feature>`` (company scope, reads the
  flag ``te_pa_gen_assess`` wrote), ``te_pa_gen_excluded_type`` (a type that is not a firm) and
  ``te_pa_gen_law_open_<law>`` (country scope: the country could move to the law).
* ``common/script_values/te_pa_gen_values.txt``: the config's numbers (``te_pa_gen_<name>``); each good's
  signed price reading (``te_pa_gen_price_<good>``, country scope, and ``te_pa_gen_firm_price_<good>``, company
  scope through its owner); the staffing band and campaign share; ``te_pa_gen_stance_<law>`` for every covered
  law; ``te_pa_gen_stance_enacting``, ``te_pa_gen_stance_in_force_worst`` and ``te_pa_gen_stance_best_available``.
* ``common/customizable_localization/te_pa_gen_custom_loc.txt``: a good's or a law's name from its index, read
  from a script container (``NAME_LOCS``).

How the sector is read (the config says why for each hand-set part):

* A type's building types are its ``building_types`` (company_building types only; ``extension_building_types``
  are left out, as an extension needs an industry charter, one at a time, so it is not the firm's sector).
* A building's **base methods** are, in each of its method groups, the method with ``is_default = yes`` or else
  the first (vanilla and the mod list the ungated method first; ``is_default`` marks the few exceptions).
* **Inputs**: amount x the good's base price, ``workforce_scaled`` and ``level_scaled`` inputs of the base
  methods, summed over the type's building types. The two largest are the firm's inputs, leaving out local
  goods (their price is per state, so a market reading means nothing) and goods the type itself makes.
* **Main output**: each building type's outputs as shares of that building's output value, summed over the
  building types, so the good most of its buildings make wins; raw value breaks a tie. A local main output is
  named but not read (``te_pa_g_out_local``).
* **Jobs**: the ``level_scaled`` employment of a level's base methods, averaged over the building types.
* **Technologies**: every technology that unlocks any method of any of its building types.

Run ``python3 scripts/generators/gen_private_actors.py [--dry-run | --check]``. No game install or running
server is needed. Full server reloads call ``regenerate`` (``server/post_load.py``, before ``organize_loc``).
Its outputs feed none of its inputs, so the live ModState is safe to read.
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import private_actors_config as cfg  # noqa: E402

KINDS = (
    "Company Types", "Buildings", "PM Groups", "PMs", "Goods", "Technologies", "Laws", "Law Groups",
    "Building Groups", "Pop Needs",
)
COVERED_GROUPS = tuple(cfg.LAW_TABLE)

EFFECTS_OUT = Path("common/scripted_effects/te_pa_gen_effects.txt")
TRIGGERS_OUT = Path("common/scripted_triggers/te_pa_gen_triggers.txt")
VALUES_OUT = Path("common/script_values/te_pa_gen_values.txt")
CUSTOM_LOC_OUT = Path("common/customizable_localization/te_pa_gen_custom_loc.txt")

HEADER = (
    "# AUTO-GENERATED by scripts/generators/gen_private_actors.py - do not edit manually.\n"
    "# Private Actors, the firms' sectors: docs/superpowers/specs/2026-11-28-actors-firms-design.md\n"
    "# (§ 5.1, § 8.1, § 10.1). Hand-set inputs: scripts/generators/private_actors_config.py.\n"
)

GOOD_SLOTS = ("in1", "in2", "out")
GOOD_UNKNOWN_KEY = "te_pa_good_unknown"
LAW_UNKNOWN_KEY = "te_pa_law_unknown"
STANCE_MIN, STANCE_MAX = -2, 2

_INPUT_RE = re.compile(r"goods_input_(\w+)_add")
_OUTPUT_RE = re.compile(r"goods_output_(\w+)_add")
_EMPLOY_RE = re.compile(r"building_employment_\w+_add")
_SUBSIDY_RE = re.compile(r"country_building_(\w+)_require_subsidies_bool")
_COLLECTIVIZE_RE = re.compile(r"building_group_(\w+)_allowed_collectivization_add")


# ---------------------------------------------------------------------------
# Parsed-data helpers
# ---------------------------------------------------------------------------

def _unwrap(value):
    """Strip the parser's (operator, value) wrappers."""
    while isinstance(value, (tuple, list)) and len(value) == 2 and isinstance(value[0], str) \
            and value[0] in ("=", "?=", "<", ">", "<=", ">="):
        value = value[1]
    return value


def _names(value) -> list[str]:
    out: list[str] = []

    def walk(x):
        x = _unwrap(x)
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, (list, tuple)):
            for y in x:
                walk(y)

    walk(value)
    return out


def _number(value) -> float:
    value = _unwrap(value)
    if isinstance(value, (list, tuple)):
        return sum(_number(v) for v in value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _body(table: dict, key: str) -> dict:
    body = _unwrap(table.get(key))
    return body if isinstance(body, dict) else {}


def _keys_deep(value, key: str) -> list:
    """Every value of `key` anywhere inside a parsed block."""
    found: list = []

    def walk(x):
        x = _unwrap(x)
        if isinstance(x, dict):
            for k, v in x.items():
                if k == key:
                    found.extend(_names(v))
                walk(v)
        elif isinstance(x, (list, tuple)):
            for y in x:
                walk(y)

    walk(value)
    return found


def _has_key_deep(value, key: str) -> bool:
    value = _unwrap(value)
    if isinstance(value, dict):
        return any(k == key or _has_key_deep(v, key) for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_has_key_deep(v, key) for v in value)
    return False


def _fmt(number: float) -> str:
    if float(number).is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# The data
# ---------------------------------------------------------------------------

def load_state(root: Path = ROOT):
    """The entity types the generator reads: vanilla from the committed snapshot, the mod's from disk."""
    from mod_state import VANILLA_COMMON_DIRS, ModState
    from vanilla_parsed import load

    snapshot = load(str(root / "vanilla_parsed"))
    state = ModState(
        {kind: "/nonexistent" for kind in KINDS},
        {kind: str(root / "common" / VANILLA_COMMON_DIRS[kind]) for kind in KINDS},
        vanilla_data=snapshot.data,
    )
    if state.parse_failures:
        raise ValueError(f"Cannot generate the Private Actors sectors from an incomplete parse: {state.parse_failures}")
    return state


@dataclass(frozen=True)
class Data:
    company_types: dict
    buildings: dict
    pm_groups: dict
    pms: dict
    goods: dict
    technologies: dict
    laws: dict
    building_groups: dict
    pop_needs: dict

    @classmethod
    def from_state(cls, mod_state) -> "Data":
        def get(kind):
            return mod_state.get_data(kind) or {}
        return cls(get("Company Types"), get("Buildings"), get("PM Groups"), get("PMs"), get("Goods"),
                   get("Technologies"), get("Laws"), get("Building Groups"), get("Pop Needs"))

    def cost(self, good: str) -> float:
        return _number(_body(self.goods, good).get("cost"))

    def is_local(self, good: str) -> bool:
        return _unwrap(_body(self.goods, good).get("local")) == "yes"

    def category(self, good: str) -> str | None:
        return _unwrap(_body(self.goods, good).get("category"))

    def group_chain(self, building: str) -> list[str]:
        out: list[str] = []
        group = _unwrap(_body(self.buildings, building).get("building_group"))
        while isinstance(group, str) and group not in out:
            out.append(group)
            group = _unwrap(_body(self.building_groups, group).get("parent_group"))
        return out

    def is_flagship(self, building: str) -> bool:
        return cfg.COMPANY_FLAGSHIP_GROUP in self.group_chain(building)

    def method_groups(self, building: str) -> list[str]:
        return [g for g in _names(_body(self.buildings, building).get("production_method_groups")) if g in self.pm_groups]

    def methods(self, group: str) -> list[str]:
        return [p for p in _names(_body(self.pm_groups, group).get("production_methods")) if p in self.pms]

    def base_method(self, group: str) -> str | None:
        methods = self.methods(group)
        for pm in methods:
            if _unwrap(_body(self.pms, pm).get("is_default")) == "yes":
                return pm
        return methods[0] if methods else None

    def need_goods(self) -> set[str]:
        goods: set[str] = set()
        for name in self.pop_needs:
            for entry in _keys_deep(self.pop_needs[name], "goods"):
                goods.add(entry)
        return goods

    def law_group(self, law: str) -> str | None:
        return _unwrap(_body(self.laws, law).get("group"))

    def laws_of(self, group: str) -> list[str]:
        return [law for law in self.laws if self.law_group(law) == group]

    def law_modifier_keys(self, law: str) -> list[str]:
        body = _body(self.laws, law)
        keys: list[str] = []
        for block in ("modifier", "institution_modifier"):
            mods = _unwrap(body.get(block))
            if isinstance(mods, dict):
                keys += list(mods)
        return keys

    def law_techs(self, law: str) -> list[str]:
        return _names(_body(self.laws, law).get("unlocking_technologies"))

    def law_has_can_enact(self, law: str) -> bool:
        return "can_enact" in _body(self.laws, law)


@dataclass(frozen=True)
class Building:
    inputs: dict      # good -> amount a level, base methods
    outputs: dict
    jobs: float
    techs: frozenset
    marked: frozenset  # method markers some method carries


def read_building(data: Data, name: str) -> Building:
    inputs: dict = {}
    outputs: dict = {}
    jobs = 0.0
    techs: set = set()
    marked: set = set()
    for group in data.method_groups(name):
        base = data.base_method(group)
        for pm in data.methods(group):
            body = _body(data.pms, pm)
            techs.update(_names(body.get("unlocking_technologies")))
            for feature in cfg.FEATURES.values():
                if feature.method_marker and _has_key_deep(body.get("building_modifiers"), feature.method_marker):
                    marked.add(feature.method_marker)
            if pm != base:
                continue
            mods = _unwrap(body.get("building_modifiers"))
            if not isinstance(mods, dict):
                continue
            for block in ("workforce_scaled", "level_scaled"):
                entries = _unwrap(mods.get(block))
                if not isinstance(entries, dict):
                    continue
                for key, value in entries.items():
                    if m := _INPUT_RE.fullmatch(key):
                        inputs[m.group(1)] = inputs.get(m.group(1), 0.0) + _number(value)
                    elif m := _OUTPUT_RE.fullmatch(key):
                        outputs[m.group(1)] = outputs.get(m.group(1), 0.0) + _number(value)
                    elif block == "level_scaled" and _EMPLOY_RE.fullmatch(key):
                        jobs += _number(value)
    return Building(inputs, outputs, jobs, frozenset(techs), frozenset(marked))


@dataclass(frozen=True)
class Sector:
    company: str
    buildings: tuple[str, ...]
    inputs: tuple[str, ...]      # up to two, largest first
    output: str | None
    output_local: bool
    jobs: int
    techs: tuple[str, ...]
    features: tuple[str, ...]    # the features that hold, in FEATURES order


def law_sets(data: Data) -> dict:
    """What the law-derived features read: removed building types, subsidized ones, collectivizable groups."""
    removes = {f.law_removes: set(_keys_deep(_body(data.laws, f.law_removes).get("on_activate"), "remove_building"))
               for f in cfg.FEATURES.values() if f.law_removes}
    subsidizes = {}
    for f in cfg.FEATURES.values():
        if f.law_subsidizes:
            subsidizes[f.law_subsidizes] = {
                f"building_{m.group(1)}" for k in data.law_modifier_keys(f.law_subsidizes)
                if (m := _SUBSIDY_RE.fullmatch(k))
            }
    collectivizes = {}
    for f in cfg.FEATURES.values():
        for law in f.law_collectivizes:
            collectivizes[law] = {m.group(1) for k in data.law_modifier_keys(law) if (m := _COLLECTIVIZE_RE.fullmatch(k))}
    return {"removes": removes, "subsidizes": subsidizes, "collectivizes": collectivizes}


def _feature_holds(feature, data: Data, company: str, buildings: list[str], read: dict, output: str | None,
                   sets: dict, need_goods: set[str]) -> bool:
    if company in feature.companies:
        return True
    if feature.buildings and any(b in feature.buildings for b in buildings):
        return True
    plain = [b for b in buildings if not data.is_flagship(b)]
    if feature.groups and any(set(feature.groups) & set(data.group_chain(b)) for b in plain):
        return True
    if feature.method_marker and any(feature.method_marker in read[b].marked for b in buildings):
        return True
    if feature.output_categories and output and output in need_goods \
            and data.category(output) in feature.output_categories:
        return True
    if feature.law_removes and set(buildings) & sets["removes"][feature.law_removes]:
        return True
    if feature.law_subsidizes and set(buildings) & sets["subsidizes"][feature.law_subsidizes]:
        return True
    if feature.law_collectivizes:
        groups = set().union(*(sets["collectivizes"][law] for law in feature.law_collectivizes))
        if any(groups & set(data.group_chain(b)) for b in plain):
            return True
    return False


def build_sectors(data: Data) -> list[Sector]:
    """Every company type's sector, by name; excluded types and types with no known building are left out."""
    sets = law_sets(data)
    need_goods = data.need_goods()
    researchable = {t for t in data.technologies if _unwrap(_body(data.technologies, t).get("can_research")) != "no"}
    cache: dict[str, Building] = {}
    sectors = []
    for company in sorted(data.company_types):
        if company in cfg.EXCLUDED_COMPANY_TYPES:
            continue
        buildings = []
        for b in _names(_body(data.company_types, company).get("building_types")):
            if b.startswith("building_") and b in data.buildings and b not in buildings:
                buildings.append(b)
        if not buildings:
            continue
        for b in buildings:
            if b not in cache:
                cache[b] = read_building(data, b)
        read = {b: cache[b] for b in buildings}

        made = set().union(*(read[b].outputs for b in buildings))
        input_value: dict = {}
        for b in buildings:
            for good, amount in read[b].inputs.items():
                if good in data.goods and not data.is_local(good) and good not in made \
                        and good not in cfg.INPUTS_LEFT_OUT:
                    input_value[good] = input_value.get(good, 0.0) + amount * data.cost(good)
        inputs = tuple(g for g, v in sorted(input_value.items(), key=lambda kv: (-kv[1], kv[0])) if v > 0)[:2]

        share: dict = {}
        raw: dict = {}
        for b in buildings:
            values = {g: a * data.cost(g) for g, a in read[b].outputs.items() if g in data.goods}
            total = sum(values.values())
            for good, value in values.items():
                if value > 0 and total > 0:
                    share[good] = share.get(good, 0.0) + value / total
                    raw[good] = raw.get(good, 0.0) + value
        output = min(share, key=lambda g: (-round(share[g], 9), -raw[g], g)) if share else None

        jobs = round(sum(read[b].jobs for b in buildings) / len(buildings))
        techs = tuple(sorted({t for b in buildings for t in read[b].techs if t in researchable}))
        features = tuple(name for name, f in cfg.FEATURES.items()
                         if _feature_holds(f, data, company, buildings, read, output, sets, need_goods))
        sectors.append(Sector(company, tuple(buildings), inputs, output,
                              bool(output and data.is_local(output)), jobs, techs, features))
    return sectors


@dataclass(frozen=True)
class Law:
    key: str
    group: str
    index: int
    row: object  # cfg.Row
    techs: tuple[str, ...]
    can_enact: bool


def law_catalog(data: Data) -> list[Law]:
    """The covered laws that exist, in the table's order, numbered from 1."""
    laws = []
    for group, rows in cfg.LAW_TABLE.items():
        for key, row in rows.items():
            if key in data.laws:
                laws.append(Law(key, group, len(laws) + 1, row, tuple(data.law_techs(key)), data.law_has_can_enact(key)))
    return laws


@dataclass(frozen=True)
class Plan:
    sectors: list
    goods: list          # every good, by key; index = position + 1
    techs: list          # the union of the sectors' technologies, by key; index = position + 1
    laws: list

    def good_index(self, good: str) -> int:
        return self.goods.index(good) + 1

    def tech_index(self, tech: str) -> int:
        return self.techs.index(tech) + 1

    def read_goods(self) -> list[str]:
        """The goods some sector reads a price of: its inputs and its main output when not local."""
        used = set()
        for s in self.sectors:
            used.update(s.inputs)
            if s.output and not s.output_local:
                used.add(s.output)
        return sorted(used)


def build_plan(mod_state) -> Plan:
    data = Data.from_state(mod_state)
    sectors = build_sectors(data)
    techs = sorted({t for s in sectors for t in s.techs})
    return Plan(sectors, sorted(data.goods), techs, law_catalog(data))


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _block(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def _comment(text: str) -> list[str]:
    """A prose comment, wrapped to the file's width."""
    return textwrap.wrap(" ".join(text.split()), width=110, initial_indent="# ", subsequent_indent="# ")


EFFECTS_PREAMBLE = """\
#
# te_pa_gen_assess (company scope) writes, on the company:
#   te_pa_g_known          1 when this file knows the type (0: excluded, or a type added after generation)
#   te_pa_g_sector_levels  the home country's levels of the type's building types
#   te_pa_g_jobs           staff a level of its buildings employs by the base methods
#   te_pa_g_<slot>_good    the good's index (goods by key, from 1; 0 none), slots in1, in2 (its two largest
#                          inputs by value) and out (its main output). te_pa_row_reason_good and its kin name it
#   te_pa_g_<slot>_pricier the home market's price of it over base, less 1, signed (0.4 = 40% above base)
#   te_pa_g_<slot>_imported, _exported  1 while the home market imports (exports) any of it
#   te_pa_g_out_local      1 when the main output is a local good, whose price and trade are not read
#   te_pa_g_f_<feature>    the sector features (private_actors_config.FEATURES), 0 or 1
#   te_pa_g_tech_count     how many technologies unlock a method of its building types
#   te_pa_g_tech_gap       how many of them the home country lacks and can research, each counted
#                          te_pa_gen_tech_held_bonus more while some country holds it (te_pa_gen_tech_cache)
# A static fact is rewritten each call, so a config change never leaves one stale.
"""


def render_assess(plan: Plan) -> str:
    lines = ["te_pa_gen_assess = {"]
    lines += [
        "\tset_variable = { name = te_pa_g_known value = 0 }",
        "\tset_variable = { name = te_pa_g_sector_levels value = 0 }",
        "\tset_variable = { name = te_pa_g_jobs value = 0 }",
        "\tset_variable = { name = te_pa_g_out_local value = 0 }",
        "\tset_variable = { name = te_pa_g_tech_count value = 0 }",
        "\tset_variable = { name = te_pa_g_tech_gap value = 0 }",
    ]
    lines += [f"\tte_pa_gen_clear_good = {{ SLOT = {slot} }}" for slot in GOOD_SLOTS]
    lines += [f"\tset_variable = {{ name = te_pa_g_f_{name} value = 0 }}" for name in cfg.FEATURES]
    for position, s in enumerate(plan.sectors):
        keyword = "if" if position == 0 else "else_if"
        summary = ", ".join(b.removeprefix("building_") for b in s.buildings)
        lines += [
            f"\t{keyword} = {{",
            f"\t\tlimit = {{ is_company_type = company_type:{s.company} }}",
            f"\t\t# {summary} | in {', '.join(s.inputs) or '-'} | out {s.output or '-'}"
            f" | {', '.join(s.features) or 'no features'}",
            "\t\tset_variable = { name = te_pa_g_known value = 1 }",
            "\t\tset_variable = {",
            "\t\t\tname = te_pa_g_sector_levels",
            "\t\t\tvalue = {",
            "\t\t\t\tvalue = 0",
            "\t\t\t\towner = {",
            *(f"\t\t\t\t\tadd = \"country_has_building_type_levels(bt:{b})\"" for b in s.buildings),
            "\t\t\t\t}",
            "\t\t\t}",
            "\t\t}",
            f"\t\tset_variable = {{ name = te_pa_g_jobs value = {s.jobs} }}",
        ]
        for slot, good in zip(("in1", "in2"), s.inputs):
            lines.append(f"\t\tte_pa_gen_read_good = {{ SLOT = {slot} GOOD = {good} IDX = {plan.good_index(good)} }}")
        if s.output and s.output_local:
            lines += [
                f"\t\tset_variable = {{ name = te_pa_g_out_good value = {plan.good_index(s.output)} }}",
                "\t\tset_variable = { name = te_pa_g_out_local value = 1 }",
            ]
        elif s.output:
            lines.append(f"\t\tte_pa_gen_read_good = {{ SLOT = out GOOD = {s.output} IDX = {plan.good_index(s.output)} }}")
        lines += [f"\t\tset_variable = {{ name = te_pa_g_f_{name} value = 1 }}" for name in s.features]
        if s.techs:
            lines.append(f"\t\tset_variable = {{ name = te_pa_g_tech_count value = {len(s.techs)} }}")
            lines += [f"\t\tte_pa_gen_tech_check = {{ TECH = {t} N = {plan.tech_index(t)} }}" for t in s.techs]
        lines.append("\t}")
    lines.append("}")
    return _block(lines)


GOOD_HELPERS = """\
# Scope: a company. Resets one good slot of te_pa_gen_assess's readings.
te_pa_gen_clear_good = {
	set_variable = { name = te_pa_g_$SLOT$_good value = 0 }
	set_variable = { name = te_pa_g_$SLOT$_pricier value = 0 }
	set_variable = { name = te_pa_g_$SLOT$_imported value = 0 }
	set_variable = { name = te_pa_g_$SLOT$_exported value = 0 }
}

# Scope: a company. Reads one good of its sector in its owner's market: the index, the signed price over
# base (te_pa_gen_firm_price_<good>) and whether the market imports and exports it.
te_pa_gen_read_good = {
	set_variable = { name = te_pa_g_$SLOT$_good value = $IDX$ }
	set_variable = { name = te_pa_g_$SLOT$_pricier value = te_pa_gen_firm_price_$GOOD$ }
	if = {
		limit = { owner = { market = { mg:$GOOD$ = { market_goods_imports > 0 } } } }
		set_variable = { name = te_pa_g_$SLOT$_imported value = 1 }
	}
	else = {
		set_variable = { name = te_pa_g_$SLOT$_imported value = 0 }
	}
	if = {
		limit = { owner = { market = { mg:$GOOD$ = { market_goods_exports > 0 } } } }
		set_variable = { name = te_pa_g_$SLOT$_exported value = 1 }
	}
	else = {
		set_variable = { name = te_pa_g_$SLOT$_exported value = 0 }
	}
}
"""

TECH_HELPERS = """\
# Scope: a company. One technology of its sector: counted in te_pa_g_tech_gap when the home country lacks it
# and can research it, te_pa_gen_tech_held_bonus more while te_pa_gen_tech_cache found some country holding it.
te_pa_gen_tech_check = {
	if = {
		limit = {
			owner = {
				NOT = { has_technology_researched = $TECH$ }
				can_research = $TECH$
			}
		}
		change_variable = { name = te_pa_g_tech_gap add = 1 }
		if = {
			limit = { has_global_variable = te_pa_gen_tech_held_$N$ }
			change_variable = { name = te_pa_g_tech_gap add = te_pa_gen_tech_held_bonus }
		}
	}
}

# Any scope. Whether some country holds one technology, into the global te_pa_gen_tech_held_<N>.
te_pa_gen_tech_cache_one = {
	if = {
		limit = { any_country = { has_technology_researched = $TECH$ } }
		set_global_variable = { name = te_pa_gen_tech_held_$N$ value = 1 }
	}
	else_if = {
		limit = { has_global_variable = te_pa_gen_tech_held_$N$ }
		remove_global_variable = te_pa_gen_tech_held_$N$
	}
}
"""


def render_tech_cache(plan: Plan) -> str:
    lines = [
        "# Any scope; run once a year. For every technology on some sector's list, whether some country holds",
        "# it: te_pa_gen_tech_held_<index> (technologies by key, from 1), which te_pa_gen_assess reads.",
        "te_pa_gen_tech_cache = {",
        *(f"\tte_pa_gen_tech_cache_one = {{ TECH = {t} N = {plan.tech_index(t)} }}" for t in plan.techs),
        "}",
    ]
    return _block(lines)


LAW_PICK_PREAMBLE = """\
# Scope: a company. Its stances on the covered laws (te_pa_gen_stance_<law>), with the index of the law each
# comes from (the table's order, from 1; 0 none), for the reason line and te_pa_row_reason_law:
#   te_pa_g_law_worst, _worst_law        the law in force that burdens the sector most (stance <= 0)
#   te_pa_g_law_best, _best_law          the law it could move to that favors it most (stance >= 0;
#                                        te_pa_gen_law_open_<law>)
#   te_pa_g_law_enacting, _enacting_law  the law the home country is enacting, when covered
# The stances read the firm's own record too (te_pa_share, te_pa_posture, te_pa_lab, te_pa_campaign_total),
# so run it after the turn has written those.
"""

LAW_HELPERS = """\
# Scope: a company. One covered law in force: kept when it burdens the sector more than the worst so far.
te_pa_gen_law_pick_in_force = {
	if = {
		limit = {
			owner = { has_law = law_type:$LAW$ }
			te_pa_gen_stance_$LAW$ < var:te_pa_g_law_worst
		}
		set_variable = { name = te_pa_g_law_worst value = te_pa_gen_stance_$LAW$ }
		set_variable = { name = te_pa_g_law_worst_law value = $N$ }
	}
}

# Scope: a company. One covered law the home country could move to: kept when it favors the sector more than
# the best so far.
te_pa_gen_law_pick_open = {
	if = {
		limit = {
			te_pa_gen_stance_$LAW$ > var:te_pa_g_law_best
			owner = { te_pa_gen_law_open_$LAW$ = yes }
		}
		set_variable = { name = te_pa_g_law_best value = te_pa_gen_stance_$LAW$ }
		set_variable = { name = te_pa_g_law_best_law value = $N$ }
	}
}

# Scope: a company. One covered law, when the home country is enacting it.
te_pa_gen_law_pick_enacting = {
	if = {
		limit = { owner = { is_enacting_law = law_type:$LAW$ } }
		set_variable = { name = te_pa_g_law_enacting value = te_pa_gen_stance_$LAW$ }
		set_variable = { name = te_pa_g_law_enacting_law value = $N$ }
	}
}
"""


def _signed(law: Law) -> bool:
    return bool(law.row.terms)


def render_law_pick(plan: Plan) -> str:
    signed = [law for law in plan.laws if _signed(law)]
    lines = ["te_pa_gen_law_pick = {"]
    for name in ("worst", "worst_law", "best", "best_law", "enacting", "enacting_law"):
        lines.append(f"\tset_variable = {{ name = te_pa_g_law_{name} value = 0 }}")
    lines += [f"\tte_pa_gen_law_pick_in_force = {{ LAW = {law.key} N = {law.index} }}" for law in signed]
    lines += [f"\tte_pa_gen_law_pick_open = {{ LAW = {law.key} N = {law.index} }}" for law in signed]
    lines += ["\tif = {", "\t\tlimit = { owner = { enacting_any_law = yes } }"]
    lines += [f"\t\tte_pa_gen_law_pick_enacting = {{ LAW = {law.key} N = {law.index} }}" for law in signed]
    lines += ["\t}", "}"]
    return _block(lines)


def render_law_selfcheck(plan: Plan) -> str:
    """The open-law reading's tally: of the covered laws not in force with one unlocking technology and no
    can_enact, how many read open by law_is_available alone, and how many of those lack the technology."""
    checked = [law for law in plan.laws if len(law.techs) == 1 and not law.can_enact]
    lines = [
        "# Scope: a country. The tally behind a self-check of the open-law reading (te_pa_gen_law_open_<law>):",
        "# te_pa_sc_law_open counts the covered laws not in force, with one unlocking technology and no",
        "# can_enact, that law_is_available reads as open; te_pa_sc_law_open_untech those of them whose",
        "# technology the country lacks. OK: open >= 1 and untech = 0 (law_is_available reads the law's",
        "# technology, so it reads the rest of its unlocking too). BROKEN: untech > 0, and the open-law reading",
        "# rests on the technology lines te_pa_gen_law_open_<law> adds beside it. Task 2 logs it once a game.",
        "te_pa_gen_law_selfcheck = {",
        "\tset_variable = { name = te_pa_sc_law_open value = 0 }",
        "\tset_variable = { name = te_pa_sc_law_open_untech value = 0 }",
    ]
    for law in checked:
        lines += [
            "\tif = {",
            "\t\tlimit = {",
            f"\t\t\tNOT = {{ has_law = law_type:{law.key} }}",
            f"\t\t\tany_law = {{ type = law_type:{law.key} law_is_available = yes }}",
            "\t\t}",
            "\t\tchange_variable = { name = te_pa_sc_law_open add = 1 }",
            "\t\tif = {",
            f"\t\t\tlimit = {{ NOT = {{ has_technology_researched = {law.techs[0]} }} }}",
            "\t\t\tchange_variable = { name = te_pa_sc_law_open_untech add = 1 }",
            "\t\t}",
            "\t}",
        ]
    lines.append("}")
    return _block(lines)


def render_effects(plan: Plan) -> str:
    return "\n".join([
        HEADER + EFFECTS_PREAMBLE,
        render_assess(plan),
        GOOD_HELPERS,
        TECH_HELPERS,
        render_tech_cache(plan),
        LAW_PICK_PREAMBLE + render_law_pick(plan),
        LAW_HELPERS,
        render_law_selfcheck(plan),
    ])


def render_triggers(plan: Plan) -> str:
    parts = [HEADER]
    parts.append("# Scope: a company. Its sector has the feature (the flag te_pa_gen_assess wrote).\n")
    for name, feature in cfg.FEATURES.items():
        parts.append(_block(_comment(f"{name}: {feature.why}") + [f"te_pa_gen_is_{name} = {{ var:te_pa_g_f_{name} ?= 1 }}"]))
    parts.append("# Scope: a company. A type that is not a firm (private_actors_config.EXCLUDED_COMPANY_TYPES).\n"
                 "te_pa_gen_excluded_type = {\n\tOR = {\n"
                 + "".join(f"\t\tis_company_type = company_type:{c}\n" for c in sorted(cfg.EXCLUDED_COMPANY_TYPES))
                 + "\t}\n}\n")
    parts.append(
        "# Scope: a country. It could move to the law: not in force, available on the country's law object\n"
        "# (law_is_available), its one unlocking technology held where it has one, and its can_enact met where it\n"
        "# has one (private_actors_config.CAN_ENACT_MIRROR). te_pa_gen_law_selfcheck checks the first reading.\n"
    )
    for law in plan.laws:
        lines = [
            f"te_pa_gen_law_open_{law.key} = {{",
            f"\tNOT = {{ has_law = law_type:{law.key} }}",
            f"\tany_law = {{ type = law_type:{law.key} law_is_available = yes }}",
        ]
        if len(law.techs) == 1:
            lines.append(f"\thas_technology_researched = {law.techs[0]}")
        if law.key in cfg.CAN_ENACT_MIRROR:
            lines.append(f"\t{cfg.CAN_ENACT_MIRROR[law.key]}")
        lines.append("}")
        parts.append(_block(lines))
    return "\n".join(parts)


def render_term(term) -> list[str]:
    weight = _fmt(term.weight)
    if term.kind == "feature":
        return [f"\tif = {{ limit = {{ var:te_pa_g_f_{term.arg} ?= 1 }} add = {weight} }}"]
    if term.kind == "all":
        return [f"\tadd = {weight}"]
    if term.kind == "when":
        conditions = " ".join(cfg.CONDITIONS[c] for c in term.arg)
        return [f"\tif = {{ limit = {{ {conditions} }} add = {weight} }}"]
    if term.kind == "labor":
        return [f"\tadd = {{ value = te_pa_gen_labor_band multiply = {weight} }}"]
    if term.kind == "campaign":
        return [f"\tadd = {{ value = te_pa_gen_campaign_share multiply = {weight} }}"]
    raise ValueError(f"unknown term kind {term.kind!r}")


def render_stance(law: Law) -> str:
    lines = _comment(f"{law.index}. {law.key} ({law.group}): {law.row.why}")
    lines += [f"te_pa_gen_stance_{law.key} = {{", "\tvalue = 0"]
    for term in law.row.terms:
        lines += render_term(term)
    if law.row.terms:
        lines += [f"\tmin = {STANCE_MIN}", f"\tmax = {STANCE_MAX}"]
    lines.append("}")
    return _block(lines)


VALUES_PREAMBLE = """\
# The numbers (private_actors_config.NUMBERS).
"""


def render_values(plan: Plan) -> str:
    parts = [HEADER, VALUES_PREAMBLE]
    parts.append("".join(f"te_pa_gen_{name} = {_fmt(value)}\n" for name, value in cfg.NUMBERS.items()))
    parts.append(
        "# Each good a sector reads: the home market's price over base, less 1, signed, built from both clamped\n"
        "# halves (scripting_best_practices.md § \"Is it signed below base price?\"). te_pa_gen_price_<good> is\n"
        "# country scope; te_pa_gen_firm_price_<good> the same from a company, through its owner.\n"
    )
    for good in plan.read_goods():
        parts.append(_block([
            f"te_pa_gen_price_up_{good} = {{ value = 0 market = {{ mg:{good} = {{ add = market_goods_pricier }} }} min = 0 }}",
            f"te_pa_gen_price_down_{good} = {{ value = 0 market = {{ mg:{good} = {{ add = market_goods_cheaper }} }} min = 0 }}",
            f"te_pa_gen_price_{good} = {{ value = te_pa_gen_price_up_{good} subtract = te_pa_gen_price_down_{good} }}",
            f"te_pa_gen_firm_price_{good} = {{ value = 0 owner = {{ add = te_pa_gen_price_{good} }} }}",
        ]))
    parts.append(_block([
        "# Scope: a company. Its staffing band for the labor laws: 2 at te_pa_gen_jobs_band_2 a level or more,",
        "# 1 at te_pa_gen_jobs_band_1 or more, else 0 (te_pa_g_jobs, te_pa_gen_assess).",
        "te_pa_gen_labor_band = {",
        "\tvalue = 0",
        "\tif = { limit = { has_variable = te_pa_g_jobs var:te_pa_g_jobs >= te_pa_gen_jobs_band_2 } value = 2 }",
        "\telse_if = { limit = { has_variable = te_pa_g_jobs var:te_pa_g_jobs >= te_pa_gen_jobs_band_1 } value = 1 }",
        "}",
        "",
        "# Scope: a company. Its campaign spending (te_pa_campaign_total, Task 5) over te_pa_gen_campaign_full,",
        "# 0 to 1, for the Electoral Finance laws; 0 while nothing is recorded.",
        "te_pa_gen_campaign_share = {",
        "\tvalue = 0",
        "\tif = { limit = { has_variable = te_pa_campaign_total } add = var:te_pa_campaign_total }",
        "\tdivide = te_pa_gen_campaign_full",
        "\tmin = 0",
        "\tmax = 1",
        "}",
    ]))
    parts.append(
        "# Scope: a company. Its stance on each covered law, -2 (burdens it) to +2 (favors it): § 8.1's table\n"
        "# (private_actors_config.LAW_TABLE), summed over its sector and clamped. A law with no terms reads 0.\n"
    )
    parts += [render_stance(law) for law in plan.laws]

    signed = [law for law in plan.laws if _signed(law)]
    enacting = ["# Scope: a company. Its stance on the law the home country is enacting; 0 when none, or not covered.",
                "te_pa_gen_stance_enacting = {", "\tvalue = 0", "\tif = {",
                "\t\tlimit = { owner = { enacting_any_law = yes } }"]
    for position, law in enumerate(signed):
        keyword = "if" if position == 0 else "else_if"
        enacting.append(f"\t\t{keyword} = {{ limit = {{ owner = {{ is_enacting_law = law_type:{law.key} }} }}"
                        f" value = te_pa_gen_stance_{law.key} }}")
    enacting += ["\t}", "}"]
    parts.append(_block(enacting))

    worst = ["# Scope: a company. The most negative of its stances on the covered laws in force; 0 when none burdens it.",
             "te_pa_gen_stance_in_force_worst = {", "\tvalue = 0"]
    for group in COVERED_GROUPS:
        members = [law for law in signed if law.group == group]
        for position, law in enumerate(members):
            keyword = "if" if position == 0 else "else_if"
            worst.append(f"\t{keyword} = {{ limit = {{ owner = {{ has_law = law_type:{law.key} }} }}"
                         f" max = te_pa_gen_stance_{law.key} }}")
    worst.append("}")
    parts.append(_block(worst))

    best = ["# Scope: a company. The most positive of its stances on the covered laws the home country could move to",
            "# (te_pa_gen_law_open_<law>); 0 when none favors it.",
            "te_pa_gen_stance_best_available = {", "\tvalue = 0"]
    for law in signed:
        best.append(f"\tif = {{ limit = {{ te_pa_gen_stance_{law.key} > 0 owner = {{ te_pa_gen_law_open_{law.key} = yes }} }}"
                    f" min = te_pa_gen_stance_{law.key} }}")
    best.append("}")
    parts.append(_block(best))
    return "\n".join(parts)


def render_custom_loc(plan: Plan) -> str:
    names = {"good": plan.goods, "law": [law.key for law in plan.laws]}
    unknown = {"good": GOOD_UNKNOWN_KEY, "law": LAW_UNKNOWN_KEY}
    parts = [
        HEADER,
        "# A good's or a law's name from the index a firm's readings carry, read from a script container that\n"
        "# holds a copy (private_actors_config.NAME_LOCS): [ScriptContainer.GetCustom('<key>')]. Goods are\n"
        "# numbered by key from 1, laws in the law table's order from 1; a name key is the good's or law's own.\n",
    ]
    for entry in cfg.NAME_LOCS:
        lines = [f"# {entry.kind} from var:{entry.variable}", f"{entry.key} = {{", "\ttype = container", "\trandom_valid = no"]
        for index, key in enumerate(names[entry.kind], start=1):
            lines += [
                "\ttext = {",
                f"\t\ttrigger = {{ var:{entry.variable} ?= {index} }}",
                f"\t\tlocalization_key = {key}",
                "\t}",
            ]
        lines += ["\ttext = {", f"\t\tlocalization_key = {unknown[entry.kind]}", "\t}", "}"]
        parts.append(_block(lines))
    return "\n".join(parts)


def plan_outputs(mod_state) -> dict[Path, str]:
    plan = build_plan(mod_state)
    return {
        EFFECTS_OUT: render_effects(plan),
        TRIGGERS_OUT: render_triggers(plan),
        VALUES_OUT: render_values(plan),
        CUSTOM_LOC_OUT: render_custom_loc(plan),
    }


def regenerate(mod_state=None, *, root: Path = ROOT, dry_run: bool = False) -> dict:
    """Post-load entry point (server/post_load.py's POST_LOAD_REGENERATORS) and CLI body.

    Writes a file only when its content changed, with one UTF-8 BOM.
    """
    if mod_state is None:
        mod_state = load_state(root)
    changed = []
    for relative, text in plan_outputs(mod_state).items():
        target = root / relative
        expected = text.encode("utf-8-sig")
        if not target.exists() or target.read_bytes() != expected:
            changed.append(str(relative))
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(expected)
    return {"changed": bool(changed), "changed_files": changed}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    mode.add_argument("--check", action="store_true", help="exit 1 if any output is stale")
    args = parser.parse_args(argv)
    result = regenerate(dry_run=args.dry_run or args.check)
    verb = "stale" if args.check else "would write" if args.dry_run else "wrote"
    for path in result["changed_files"]:
        print(f"{verb}: {path}")
    if not result["changed"]:
        print("private actors sectors: current")
    return int(args.check and result["changed"])


if __name__ == "__main__":
    raise SystemExit(main())
