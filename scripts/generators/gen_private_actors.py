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
  - ``te_pa_gen_seat_pick`` (company scope): the firm's seat (§ 4.5), the incorporated home state with the most
    levels of its building types, saved as ``scope:te_pa_seat_pick`` (§ 16, probe 11: no script link reaches a
    company's headquarters state).
  - helpers ``te_pa_gen_clear_good``, ``te_pa_gen_read_good``, ``te_pa_gen_tech_check``,
    ``te_pa_gen_tech_cache_one``, ``te_pa_gen_law_pick_in_force``, ``_open``, ``_enacting``.
* ``common/scripted_triggers/te_pa_gen_triggers.txt``: ``te_pa_gen_is_<feature>`` (company scope, reads the
  flag ``te_pa_gen_assess`` wrote), ``te_pa_gen_excluded_type`` (a type that is not a firm) and
  ``te_pa_gen_law_open_<law>`` (country scope: the country could move to the law), and
  ``te_pa_gen_enacting_<lawgroup>`` (country scope: it is enacting a law of a covered group).
* ``common/script_values/te_pa_gen_values.txt``: the config's numbers (``te_pa_gen_<name>``); each good's
  signed price reading (``te_pa_gen_price_<good>``, country scope, and ``te_pa_gen_firm_price_<good>``, company
  scope through its owner); the staffing band and campaign share; ``te_pa_gen_stance_<law>`` for every covered
  law; ``te_pa_gen_stance_enacting``, ``te_pa_gen_stance_in_force_worst`` and ``te_pa_gen_stance_best_available``;
  the executive's temperament (§ 5.3), ``te_pa_gen_temper_<axis>`` (company scope, -1 to 1, from the config's trait
  and ideology tables) and the self-check counts ``te_pa_gen_exec_traits_held`` and ``_ideologies_held``; and
  ``te_pa_gen_seat_levels_<company type>`` (state scope), the order the seat is picked by.
* ``common/customizable_localization/te_pa_gen_custom_loc.txt``: a good's or a law's name from its index, read
  from a script container (``NAME_LOCS``).
* The trust and the foundation (plan Task 4; spec §§ 5.5, 6.1): one modifier a firm type each, since a modifier
  names its holding's firm and carries the throughput lines of the firm's own building types.
  - ``common/static_modifiers/te_pa_gen_modifiers.txt``: ``te_pa_cartel_<type>`` (open or exposed, "<company>
    Cartel") and ``te_pa_cartel_secret_<type>`` (secret, one shared name that names no firm), each cutting every
    building type of the type by ``cartel_cut`` at strength 100, and ``te_pa_found_<type>`` (a state modifier,
    "<company> Foundation"), for every type with a sector.
  - ``common/modifier_type_definitions/te_pa_gen_modifier_types.txt``: ``building_<b>_throughput_add`` for each
    sector building that neither vanilla (``vanilla_parsed/common/modifier_types.json``) nor another of the mod's
    definition files registers (an unregistered one is dropped at load; ``modifier_field_audit``).
  - ``localization/english/te_pa_generated_l_english.yml``: the names of the three modifiers a type and of the
    registered types, filed through ``organize_loc`` (category PA_GENERATED: the modifiers by prefix, the types by
    the definition file) so that a run of ``organize_loc.py`` leaves it as it is.
  - effects ``te_pa_gen_cartel_apply`` / ``_remove`` (company scope), ``te_pa_gen_cartel_remove_all`` (country),
    ``te_pa_gen_found_apply`` / ``_remove_all`` (state, from the state pulse), ``te_pa_gen_found_pick`` and
    ``te_pa_gen_expand`` (company); the trigger ``te_pa_gen_can_expand``; the values ``te_pa_gen_cartel_tp_country``
    and ``_seat`` (the ``cartel_rents`` self-check's reads) and ``te_pa_gen_enacting_law_index``.
  - Task 4b: the effect ``te_pa_gen_charter_grant`` (a monopoly charter's ``add_company_monopoly`` on the type's
    main building type, ``Sector.expand``'s first) and the trigger ``te_pa_gen_charter_held`` (the
    ``charter_monopoly`` self-check's read).

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
    "Building Groups", "Pop Needs", "Character Traits", "Ideologies",
)
COVERED_GROUPS = tuple(cfg.LAW_TABLE)

EFFECTS_OUT = Path("common/scripted_effects/te_pa_gen_effects.txt")
TRIGGERS_OUT = Path("common/scripted_triggers/te_pa_gen_triggers.txt")
VALUES_OUT = Path("common/script_values/te_pa_gen_values.txt")
CUSTOM_LOC_OUT = Path("common/customizable_localization/te_pa_gen_custom_loc.txt")
STATIC_MODIFIERS_OUT = Path("common/static_modifiers/te_pa_gen_modifiers.txt")
MODIFIER_TYPES_OUT = Path("common/modifier_type_definitions/te_pa_gen_modifier_types.txt")
LOC_OUT = Path("localization/english/te_pa_generated_l_english.yml")
LOC_CATEGORY = "PA_GENERATED"
VANILLA_MODIFIER_TYPES = Path("vanilla_parsed/common/modifier_types.json")
MODIFIER_TYPES_DIR = Path("common/modifier_type_definitions")
# The trust's and the foundation's modifiers, a firm type each (organize_loc files their names by these prefixes),
# and the country variable that holds each cartel modifier's multiplier.
CARTEL_PREFIX = "te_pa_cartel_"
CARTEL_SECRET_PREFIX = "te_pa_cartel_secret_"
FOUNDATION_PREFIX = "te_pa_found_"
CARTEL_MULT_PREFIX = "te_pa_cm_"
CARTEL_ICON = "gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds"
FOUNDATION_ICON = "gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds"

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
    character_traits: dict = None
    ideologies: dict = None

    @classmethod
    def from_state(cls, mod_state) -> "Data":
        def get(kind):
            return mod_state.get_data(kind) or {}
        return cls(get("Company Types"), get("Buildings"), get("PM Groups"), get("PMs"), get("Goods"),
                   get("Technologies"), get("Laws"), get("Building Groups"), get("Pop Needs"),
                   get("Character Traits"), get("Ideologies"))

    def personality_traits(self) -> list[str]:
        """Every trait of type personality, by key (§ 5.3 reads only these)."""
        return sorted(t for t in (self.character_traits or {})
                      if _unwrap(_body(self.character_traits, t).get("type")) == "personality")

    def character_ideologies(self) -> list[str]:
        """Every ideology a character can hold (character_ideology = yes), by key."""
        return sorted(i for i in (self.ideologies or {})
                      if _unwrap(_body(self.ideologies, i).get("character_ideology")) == "yes")

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
    # Its building types in the order expansion tries them (te_pa_gen_expand): those that make the main output,
    # most of it first, then the type's other buildings, flagships last. The first is its main building type.
    expand: tuple[str, ...] = ()


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
        plain = [b for b in buildings if not data.is_flagship(b)]
        main = sorted((b for b in plain if output and read[b].outputs.get(output, 0) > 0),
                      key=lambda b: -read[b].outputs[output])
        expand = tuple(main + [b for b in plain if b not in main] + [b for b in buildings if b not in plain])
        sectors.append(Sector(company, tuple(buildings), inputs, output,
                              bool(output and data.is_local(output)), jobs, techs, features, expand))
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
    traits: tuple = ()       # the personality traits that exist, by key
    ideologies: tuple = ()   # the character ideologies that exist, by key
    # The modifier types vanilla or another of the mod's definition files registers (registered_types)
    registered: frozenset = frozenset()
    # A loc key's English text, the mod's over vanilla's (entity_loc), for the generated names; None: unread
    loc: object = None

    def good_index(self, good: str) -> int:
        return self.goods.index(good) + 1

    def tech_index(self, tech: str) -> int:
        return self.techs.index(tech) + 1

    def type_index(self, company: str) -> int:
        """A firm type's number, its sector's place in the plan from 1 (te_pa_g_type, te_pa_st_found_type)."""
        return next(n for n, s in enumerate(self.sectors, 1) if s.company == company)

    def missing_throughput_types(self) -> list[str]:
        """``building_<b>_throughput_add`` for each sector building no other definition registers."""
        names = {f"{b}_throughput_add" for s in self.sectors for b in s.buildings}
        return sorted(names - self.registered)

    def read_goods(self) -> list[str]:
        """The goods some sector reads a price of: its inputs and its main output when not local."""
        used = set()
        for s in self.sectors:
            used.update(s.inputs)
            if s.output and not s.output_local:
                used.add(s.output)
        return sorted(used)


_TOP_LEVEL_RE = re.compile(r"^(?:[A-Z_]+:)?(\w+)\s*=\s*\{", re.MULTILINE)


def registered_types(root: Path = ROOT) -> frozenset:
    """The modifier types registered by vanilla (the committed snapshot) or by any of the mod's definition files
    but this generator's own, so a type another file takes over drops out of the generated file."""
    import json

    names = set(json.loads((root / VANILLA_MODIFIER_TYPES).read_text(encoding="utf-8")))
    folder = root / MODIFIER_TYPES_DIR
    if folder.is_dir():
        for path in sorted(folder.glob("*.txt")):
            if path.name == MODIFIER_TYPES_OUT.name:
                continue
            names.update(_TOP_LEVEL_RE.findall(path.read_text(encoding="utf-8-sig")))
    return frozenset(names)


_LOC_LINE_RE = re.compile(r'^\s*([\w.\-]+):\d*\s*"(.*)"')
VANILLA_LOC = Path("vanilla_parsed/localization_english.json")


def entity_loc(root: Path = ROOT):
    """A lookup of a key's English text, the mod's (``replace/`` last) over vanilla's snapshot, leaving out this
    generator's own loc file: the names the generated names splice in (a building's, a company's)."""
    import json

    vanilla = {}
    if (root / VANILLA_LOC).is_file():
        vanilla = json.loads((root / VANILLA_LOC).read_text(encoding="utf-8"))
    mod: dict[str, str] = {}
    loc_dir = root / "localization" / "english"
    if loc_dir.is_dir():
        files = sorted((p for p in loc_dir.rglob("*.yml") if p.name != LOC_OUT.name),
                       key=lambda p: (p.parent.name == "replace", p.name))
        for path in files:
            for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
                if m := _LOC_LINE_RE.match(line):
                    mod[m.group(1)] = m.group(2)

    def lookup(key: str):
        if key in mod:
            return mod[key]
        value = vanilla.get(key)
        return value if isinstance(value, str) else None

    return lookup


def build_plan(mod_state, root: Path = ROOT) -> Plan:
    data = Data.from_state(mod_state)
    sectors = build_sectors(data)
    for s in sectors:
        if not s.company.startswith("company_"):
            raise ValueError(f"{s.company}: organize_loc files the trust's modifier names by te_pa_*_company_")
    techs = sorted({t for s in sectors for t in s.techs})
    return Plan(sectors, sorted(data.goods), techs, law_catalog(data),
                tuple(data.personality_traits()), tuple(data.character_ideologies()), registered_types(root),
                entity_loc(root))


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
#   te_pa_g_type           the type's number in this file, from 1 (the order of the branches below; 0 unknown):
#                          a state holds it for its foundation's modifier (te_pa_st_found_type)
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
        "\tset_variable = { name = te_pa_g_type value = 0 }",
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
            f"\t\tset_variable = {{ name = te_pa_g_type value = {position + 1} }}",
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


SEAT_PREAMBLE = """\
# Scope: a company, from the turn when the firm has no seat or its seat has left the country (te_pa_core_effects.txt).
# The firm's seat (§ 4.5): the incorporated home state with the most levels of its type's building types, saved as
# scope:te_pa_seat_pick (unset when no incorporated home state holds one; the turn falls back on the capital).
# Script has no link from a company to its headquarters' state (§ 16, probe 11: the 1.15 event targets give a
# company only executive, owner, type, prosperity and weekly_prosperity_change; its regional headquarters are
# iterable, its main one is not), so the seat is the spec's fallback. te_pa_gen_seat_levels_<type> is the order.
"""


def render_seat_pick(plan: Plan, name: str = "te_pa_gen_seat_pick", save_as: str = "te_pa_seat_pick",
                     extra: tuple = ()) -> str:
    lines = [f"{name} = {{"]
    for position, s in enumerate(plan.sectors):
        keyword = "if" if position == 0 else "else_if"
        lines += [
            f"\t{keyword} = {{",
            f"\t\tlimit = {{ is_company_type = company_type:{s.company} }}",
            "\t\towner = {",
            "\t\t\tordered_scope_state = {",
            "\t\t\t\tlimit = {",
            "\t\t\t\t\tis_incorporated = yes",
            *(f"\t\t\t\t\t{line}" for line in extra),
            "\t\t\t\t\tOR = {",
            *(f"\t\t\t\t\t\thas_building = {b}" for b in s.buildings),
            "\t\t\t\t\t}",
            "\t\t\t\t}",
            f"\t\t\t\torder_by = te_pa_gen_seat_levels_{s.company}",
            "\t\t\t\tposition = 0",
            "\t\t\t\tcheck_range_bounds = no",
            f"\t\t\t\tsave_scope_as = {save_as}",
            "\t\t\t}",
            "\t\t}",
            "\t}",
        ]
    lines.append("}")
    return _block(lines)


def render_seat_values(plan: Plan) -> str:
    parts = ["# Scope: a state. Its levels of a company type's building types: the order te_pa_gen_seat_pick picks "
             "a seat by.\n"]
    for s in plan.sectors:
        lines = [f"te_pa_gen_seat_levels_{s.company} = {{", "\tvalue = 0"]
        lines += [f"\tif = {{ limit = {{ has_building = {b} }} add = b:{b}.level }}" for b in s.buildings]
        lines.append("}")
        parts.append(_block(lines))
    return "\n".join(parts)


def temperament_weights(plan: Plan) -> dict[str, list[tuple[str, str, float]]]:
    """Each axis's (kind, key, weight) lines, for the traits and ideologies that exist, in key order."""
    out: dict[str, list[tuple[str, str, float]]] = {axis: [] for axis in cfg.TEMPERAMENT_AXES}
    for trait in plan.traits:
        for axis, weight in sorted(cfg.TRAIT_TEMPERAMENT.get(trait, {}).items()):
            out[axis].append(("trait", trait, weight))
    for ideology in plan.ideologies:
        for axis, weight in sorted(cfg.IDEOLOGY_TEMPERAMENT.get(ideology, {}).items()):
            out[axis].append(("ideology", ideology, weight))
    return out


def _temper_test(kind: str, key: str) -> str:
    return f"has_trait = {key}" if kind == "trait" else f"has_ideology = ideology:{key}"


def render_temperament(plan: Plan) -> str:
    parts = [
        "# Scope: a company. Its executive's temperament on each axis (§ 5.3; private_actors_config.TRAIT_TEMPERAMENT\n"
        "# and IDEOLOGY_TEMPERAMENT): the weights of the personality traits and the ideology it holds, summed and\n"
        "# clamped to -1..1; 0 with no executive (§ 16, probe 7's fallback).\n"
    ]
    for axis, lines_of in temperament_weights(plan).items():
        lines = _comment(f"{axis}: {cfg.TEMPERAMENT_AXES[axis]}")
        lines += [f"te_pa_gen_temper_{axis} = {{", "\tvalue = 0", "\texecutive ?= {"]
        lines += [f"\t\tif = {{ limit = {{ {_temper_test(kind, key)} }} add = {_fmt(weight)} }}"
                  for kind, key, weight in lines_of]
        lines += ["\t}", "\tmin = -1", "\tmax = 1", "}"]
        parts.append(_block(lines))
    parts.append(_block([
        "# Scope: a company. How many personality traits, and how many character ideologies, its executive holds,",
        "# for the firm_executive self-check (probe 7: are an executive's traits and ideology readable from the",
        "# company?). 0 with no executive.",
        "te_pa_gen_exec_traits_held = {",
        "\tvalue = 0",
        "\texecutive ?= {",
        *(f"\t\tif = {{ limit = {{ has_trait = {t} }} add = 1 }}" for t in plan.traits),
        "\t}",
        "}",
        "",
        "te_pa_gen_exec_ideologies_held = {",
        "\tvalue = 0",
        "\texecutive ?= {",
        *(f"\t\tif = {{ limit = {{ has_ideology = ideology:{i} }} add = 1 }}" for i in plan.ideologies),
        "\t}",
        "}",
    ]))
    return "\n".join(parts)


def render_enacting_groups(plan: Plan) -> str:
    parts = ["# Scope: a country. It is enacting a law of a covered group (any of the group's laws in the law table).\n"]
    for group in COVERED_GROUPS:
        members = [law for law in plan.laws if law.group == group]
        if not members:
            continue
        lines = [f"te_pa_gen_enacting_{group} = {{", "\tOR = {"]
        lines += [f"\t\tis_enacting_law = law_type:{law.key}" for law in members]
        lines += ["\t}", "}"]
        parts.append(_block(lines))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# The trust and the foundation (plan Task 4; te_pa_trust_effects.txt is their caller)
# ---------------------------------------------------------------------------

TRUST_PREAMBLE = """\
# The trust and the foundation (spec §§ 5.5, 6.1; te_pa_trust_effects.txt calls these). A firm type's modifiers
# (te_pa_gen_modifiers.txt): te_pa_cartel_<type> names its firm, for an open or exposed cartel;
# te_pa_cartel_secret_<type> names none, for a secret one (§ 4.6: its effect is seen, its author is not);
# te_pa_found_<type> is its foundation's, on a state.
#
# Scope: a company holding a cartel, from the quarter, with its owner as ROOT (an add_modifier's multiplier
# resolves against ROOT). Replaces the firm's cartel modifier: the known or the secret one by te_pa_cartel_known,
# at te_pa_cartel_mult (strength over 100), which a country variable a type holds (te_pa_cm_<type>), since a
# multiplier is read again after it is applied and two firms' cartels can't share one.
"""


def render_cartel_effects(plan: Plan) -> str:
    apply = ["te_pa_gen_cartel_apply = {", "\tsave_scope_as = te_pa_gen_cartel_firm"]
    remove = [
        "# Scope: a company. Takes its cartel modifiers off its owner (the cartel has ended, or the firm is cleared).",
        "te_pa_gen_cartel_remove = {",
    ]
    remove_all = [
        "# Scope: a country. Takes every firm's cartel modifiers off it: the teardown (the rule switched off), which",
        "# also reaches a modifier whose firm has gone.",
        "te_pa_gen_cartel_remove_all = {",
    ]
    for position, s in enumerate(plan.sectors):
        keyword = "if" if position == 0 else "else_if"
        known, secret, var = (f"{CARTEL_PREFIX}{s.company}", f"{CARTEL_SECRET_PREFIX}{s.company}",
                              f"{CARTEL_MULT_PREFIX}{s.company}")
        apply += [
            f"\t{keyword} = {{",
            f"\t\tlimit = {{ is_company_type = company_type:{s.company} }}",
            "\t\towner = {",
            f"\t\t\tremove_modifier = {known}",
            f"\t\t\tremove_modifier = {secret}",
            f"\t\t\tset_variable = {{ name = {var} value = scope:te_pa_gen_cartel_firm.var:te_pa_cartel_mult }}",
            "\t\t}",
            "\t\tif = {",
            "\t\t\tlimit = { var:te_pa_cartel_known ?= 1 }",
            f"\t\t\towner = {{ add_modifier = {{ name = {known} multiplier = var:{var} }} }}",
            "\t\t}",
            "\t\telse = {",
            f"\t\t\towner = {{ add_modifier = {{ name = {secret} multiplier = var:{var} }} }}",
            "\t\t}",
            "\t}",
        ]
        remove += [
            f"\t{keyword} = {{",
            f"\t\tlimit = {{ is_company_type = company_type:{s.company} }}",
            "\t\towner = {",
            f"\t\t\tremove_modifier = {known}",
            f"\t\t\tremove_modifier = {secret}",
            "\t\t}",
            "\t}",
        ]
        remove_all += [f"\tremove_modifier = {known}", f"\tremove_modifier = {secret}"]
    return "\n".join(_block(part + ["}"]) for part in (apply, remove, remove_all))


FOUND_PREAMBLE = """\
# Scope: a state, from the state pulse (te_pa_state_monthly: ROOT is the state, which an add_modifier's
# multiplier resolves against). Replaces the state's foundation modifier, the one of the type numbered
# te_pa_st_found_type (te_pa_g_type), at te_pa_st_found_mult, while te_pa_st_found_str is above 0; takes it off
# otherwise.
"""


def render_found_effects(plan: Plan) -> str:
    apply = ["te_pa_gen_found_apply = {"]
    remove_all = [
        "# Scope: a state. Takes every type's foundation modifier off it: the teardown, and a state whose foundation's",
        "# type number has changed (a sector added to this file renumbers the types after it).",
        "te_pa_gen_found_remove_all = {",
    ]
    for position, s in enumerate(plan.sectors):
        keyword = "if" if position == 0 else "else_if"
        name = f"{FOUNDATION_PREFIX}{s.company}"
        apply += [
            f"\t{keyword} = {{",
            f"\t\tlimit = {{ var:te_pa_st_found_type ?= {position + 1} }}",
            f"\t\tremove_modifier = {name}",
            "\t\tif = {",
            "\t\t\tlimit = {",
            "\t\t\t\thas_variable = te_pa_st_found_str",
            "\t\t\t\tvar:te_pa_st_found_str > 0",
            "\t\t\t}",
            f"\t\t\tadd_modifier = {{ name = {name} multiplier = var:te_pa_st_found_mult }}",
            "\t\t}",
            "\t}",
        ]
        remove_all.append(f"\tremove_modifier = {name}")
    return _block(apply + ["}"]) + "\n" + _block(remove_all + ["}"])


EXPAND_PREAMBLE = """\
# Scope: a company (te_pa_do_expand, Dominance's verb below the cartel's share, § 6.1 stage 1: the firm builds in
# its sector). Queues one private level of its main building type at its seat, or of the next of its types the
# seat can take a level of (Sector.expand's order). start_privately_funded_building_construction takes a literal
# building and queues private construction for the state's owner, which its investment pool pays for as for the
# engine's own (scripting_best_practices.md), so it spends no funds (§ 4.3). te_pa_gen_can_expand says whether
# there is one.
"""


def render_expand(plan: Plan) -> str:
    lines = ["te_pa_gen_expand = {"]
    for position, s in enumerate(plan.sectors):
        keyword = "if" if position == 0 else "else_if"
        lines += [f"\t{keyword} = {{", f"\t\tlimit = {{ is_company_type = company_type:{s.company} }}",
                  "\t\tvar:te_pa_seat ?= {"]
        for n, b in enumerate(s.expand):
            inner = "if" if n == 0 else "else_if"
            lines += [
                f"\t\t\t{inner} = {{",
                f"\t\t\t\tlimit = {{ any_scope_building = {{ is_building_type = {b} can_queue_building_levels = 1 }} }}",
                f"\t\t\t\tstart_privately_funded_building_construction = {b}",
                "\t\t\t}",
            ]
        lines += ["\t\t}", "\t}"]
    lines.append("}")
    return _block(lines)


CHARTER_PREAMBLE = """\
# Scope: a company granted a monopoly charter (te_pa_charter_grant, § 6.5: on its petition, or unasked from the
# firm's detail). The engine's own monopoly on its main building type (Sector.expand's first), through
# add_company_monopoly, whose target is a building type (bt:). te_pa_gen_charter_held reads it back for the
# charter_monopoly self-check (te_pa_debug_effects.txt).
"""


def render_charter(plan: Plan) -> str:
    lines = ["te_pa_gen_charter_grant = {"]
    for position, s in enumerate(plan.sectors):
        keyword = "if" if position == 0 else "else_if"
        lines += [f"\t{keyword} = {{", f"\t\tlimit = {{ is_company_type = company_type:{s.company} }}",
                  f"\t\tadd_company_monopoly = bt:{s.expand[0]}", "\t}"]
    lines.append("}")
    return _block(lines)


def render_charter_trigger(plan: Plan) -> str:
    lines = [
        "# Scope: a company. It holds the engine's monopoly on its main building type (te_pa_gen_charter_grant's).",
        "te_pa_gen_charter_held = {",
        "\tOR = {",
    ]
    for s in plan.sectors:
        lines += ["\t\tAND = {", f"\t\t\tis_company_type = company_type:{s.company}",
                  f"\t\t\tcompany_has_building_type_monopoly = bt:{s.expand[0]}", "\t\t}"]
    lines += ["\t}", "}"]
    return _block(lines)


def render_found_pick(plan: Plan) -> str:
    return (
        "# Scope: a company endowing a foundation (te_pa_do_endow, § 4.5): the incorporated home state with the most\n"
        "# levels of its building types that holds no other firm's foundation, as the seat is picked, saved as\n"
        "# scope:te_pa_found_pick (unset when there is none).\n"
        + render_seat_pick(plan, "te_pa_gen_found_pick", "te_pa_found_pick",
                           ("NOT = { has_variable = te_pa_st_found_str }",))
    )


def render_trust_triggers(plan: Plan) -> str:
    lines = [
        "# Scope: a company. Its seat can take a private level of one of its building types (te_pa_gen_expand's).",
        "te_pa_gen_can_expand = {",
        "\tOR = {",
    ]
    for s in plan.sectors:
        lines += [
            "\t\tAND = {",
            f"\t\t\tis_company_type = company_type:{s.company}",
            "\t\t\tvar:te_pa_seat ?= {",
            "\t\t\t\tany_scope_building = {",
            "\t\t\t\t\tOR = {",
            *(f"\t\t\t\t\t\tis_building_type = {b}" for b in s.expand),
            "\t\t\t\t\t}",
            "\t\t\t\t\tcan_queue_building_levels = 1",
            "\t\t\t\t}",
            "\t\t\t}",
            "\t\t}",
        ]
    lines += ["\t}", "}"]
    return _block(lines)


def render_trust_values(plan: Plan) -> str:
    country = [
        "# Scope: a company. The cartel_rents self-check's reads (te_pa_debug_effects.txt, probe 2): its owner's sum of",
        "# its main building type's throughput modifier, and that of a building of the type at its seat (0 with none).",
        "te_pa_gen_cartel_tp_country = {",
        "\tvalue = 0",
    ]
    seat = ["te_pa_gen_cartel_tp_seat = {", "\tvalue = 0"]
    seat_has = ["# Scope: a company. 1 while its seat holds a building of its main building type (the read above has one).",
                "te_pa_gen_cartel_seat_has = {", "\tvalue = 0"]
    for position, s in enumerate(plan.sectors):
        keyword = "if" if position == 0 else "else_if"
        b = s.expand[0]
        country.append(f"\t{keyword} = {{ limit = {{ is_company_type = company_type:{s.company} }}"
                       f" owner = {{ add = modifier:{b}_throughput_add }} }}")
        seat_has.append(f"\t{keyword} = {{ limit = {{ is_company_type = company_type:{s.company}"
                        f" var:te_pa_seat ?= {{ has_building = {b} }} }} value = 1 }}")
        seat += [
            f"\t{keyword} = {{",
            "\t\tlimit = {",
            f"\t\t\tis_company_type = company_type:{s.company}",
            "\t\t\thas_variable = te_pa_seat",
            f"\t\t\tvar:te_pa_seat = {{ has_building = {b} }}",
            "\t\t}",
            f"\t\tvar:te_pa_seat = {{ b:{b} = {{ add = modifier:{b}_throughput_add }} }}",
            "\t}",
        ]
    index = [
        "# Scope: a country. The law table's number of the covered law it is enacting (te_pa_g_law_*_law's numbering,",
        "# signed or not), 0 when none: the stall's ledger line names it (te_pa_l_law, te_pa_ledger_law).",
        "te_pa_gen_enacting_law_index = {",
        "\tvalue = 0",
        "\tif = {",
        "\t\tlimit = { enacting_any_law = yes }",
    ]
    for position, law in enumerate(plan.laws):
        keyword = "if" if position == 0 else "else_if"
        index.append(f"\t\t{keyword} = {{ limit = {{ is_enacting_law = law_type:{law.key} }} value = {law.index} }}")
    index += ["\t}", "}"]
    return "\n".join(_block(part) for part in (country + ["}"], seat + ["}"], seat_has + ["}"], index))


STATIC_MODIFIERS_PREAMBLE = """\
# The trust's and the foundation's modifiers, a firm type each (spec §§ 5.5, 6.1, 4.6), at strength 100; applied
# with the strength over 100 as their multiplier (te_pa_gen_cartel_apply from the quarter, te_pa_gen_found_apply
# from the state pulse). A cartel cuts the throughput of each of the type's building types in the country (the
# market price rises from the supply it takes away, § 6.7) and adds to Wealth Concentration's economic laws term;
# te_pa_cartel_secret_<type> is the same for a secret cartel under a name that names no firm. A foundation gives
# its state education access and lower mortality. The numbers: private_actors_config.NUMBERS.
"""


def _modifier_value(number: float) -> str:
    return _fmt(number)


def render_static_modifiers(plan: Plan) -> str:
    cut = _modifier_value(-cfg.NUMBERS["cartel_cut"])
    parts = [HEADER, STATIC_MODIFIERS_PREAMBLE]
    for s in plan.sectors:
        body = [f"\t{b}_throughput_add = {cut}" for b in s.buildings]
        body.append(f"\tcountry_wealth_concentration_economy_add = {_modifier_value(cfg.NUMBERS['cartel_wealth'])}")
        for name in (f"{CARTEL_PREFIX}{s.company}", f"{CARTEL_SECRET_PREFIX}{s.company}"):
            parts.append(_block([f"{name} = {{", f"\ticon = {CARTEL_ICON}", *body, "}"]))
        parts.append(_block([
            f"{FOUNDATION_PREFIX}{s.company} = {{",
            f"\ticon = {FOUNDATION_ICON}",
            f"\tstate_education_access_add = {_modifier_value(cfg.NUMBERS['found_education'])}",
            f"\tstate_mortality_mult = {_modifier_value(-cfg.NUMBERS['found_mortality'])}",
            "}",
        ]))
    return "\n".join(parts)


MODIFIER_TYPES_PREAMBLE = """\
# The throughput type of each sector building that no other definition registers (vanilla registers it for under
# half of its own buildings; an unregistered name is dropped at load, modifier_field_audit), so that a firm's
# cartel modifier (te_pa_gen_modifiers.txt) reaches every building type of its sector. A type another file
# registers drops out of this one at the next run.
"""


def render_modifier_types(plan: Plan) -> str:
    parts = [HEADER, MODIFIER_TYPES_PREAMBLE]
    for name in plan.missing_throughput_types():
        parts.append(_block([f"{name} = {{", "\tcolor = good", "\tpercent = yes", "\tdecimals = 1", "}"]))
    return "\n".join(parts)


# The date the generated names' review tags carry (modifier_name_audit's suppression, below).
REVIEW_DATE = "2026-11-28"


def _splice(plan: Plan, key: str) -> str:
    """``$key$``, or the key's own text with a straight apostrophe turned typographic where it has one: the engine
    pastes a modifier's name into a quoted tooltip argument, which a straight one breaks (loc_render_audit)."""
    text = plan.loc(key) if plan.loc else None
    if text and "'" in text:
        return text.replace("'", "\u2019")
    return f"${key}$"


def _name(plan: Plan, text: str, figures: bool) -> str:
    """A generated modifier name's loc value. A firm's or a building's own name can read to modifier_name_audit as a
    sentence (an abbreviation, "Ltd.", before the word that follows) or run long; such a line carries the audit's
    review tag, from the audit's own test, so a name that stops reading so drops it at the next run."""
    tag = ""
    if plan.loc:
        import long_tooltip_audit
        import modifier_name_audit

        checks = modifier_name_audit.name_checks(long_tooltip_audit.rendered_text(text, plan.loc), figures=figures)
        if checks:
            why = {"sentence": "an abbreviation in the entity's own name reads as a sentence break",
                   "long": "the entity's own name is long", "figure": "a figure in the entity's own name"}
            tag = (f" # REVIEWED {REVIEW_DATE} (modifier_name): generated from the company's or building's name; "
                   + ", ".join(why[c] for c in checks))
    return f'0 "{text}"{tag}'


def loc_entries(plan: Plan) -> dict[str, str]:
    """Loc key -> value (with its version digit), for the trust's modifiers and the registered types."""
    entries: dict[str, str] = {}
    for s in plan.sectors:
        firm = _splice(plan, s.company)
        entries[f"{CARTEL_PREFIX}{s.company}"] = _name(plan, f"{firm} $te_pa_holding_cartel$", False)
        entries[f"{CARTEL_PREFIX}{s.company}_desc"] = '0 "$te_pa_cartel_desc$"'
        entries[f"{CARTEL_SECRET_PREFIX}{s.company}"] = _name(plan, "$te_pa_cartel_secret$", False)
        entries[f"{CARTEL_SECRET_PREFIX}{s.company}_desc"] = '0 "$te_pa_cartel_secret_desc$"'
        entries[f"{FOUNDATION_PREFIX}{s.company}"] = _name(plan, f"{firm} $te_pa_holding_found$", False)
        entries[f"{FOUNDATION_PREFIX}{s.company}_desc"] = '0 "$te_pa_found_desc$"'
    for name in plan.missing_throughput_types():
        building = _splice(plan, name.removesuffix("_throughput_add"))
        entries[name] = _name(plan, f"{building} [concept_throughput]", True)
        entries[f"{name}_desc"] = f'0 "A bonus or penalty to both input and output of {building} buildings"'
    return entries


def render_loc(plan: Plan) -> str:
    from organize_loc import _render_loc_file, section_label

    return _render_loc_file([(section_label(LOC_CATEGORY), loc_entries(plan))]).decode("utf-8-sig")


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
        SEAT_PREAMBLE + render_seat_pick(plan),
        TRUST_PREAMBLE + render_cartel_effects(plan),
        FOUND_PREAMBLE + render_found_effects(plan),
        render_found_pick(plan),
        EXPAND_PREAMBLE + render_expand(plan),
        CHARTER_PREAMBLE + render_charter(plan),
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
    parts.append(render_enacting_groups(plan))
    parts.append(render_trust_triggers(plan))
    parts.append(render_charter_trigger(plan))
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
    parts.append(render_temperament(plan))
    parts.append(render_seat_values(plan))
    parts.append(render_trust_values(plan))
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


def plan_outputs(mod_state, root: Path = ROOT) -> dict[Path, str]:
    plan = build_plan(mod_state, root)
    return {
        EFFECTS_OUT: render_effects(plan),
        TRIGGERS_OUT: render_triggers(plan),
        VALUES_OUT: render_values(plan),
        CUSTOM_LOC_OUT: render_custom_loc(plan),
        STATIC_MODIFIERS_OUT: render_static_modifiers(plan),
        MODIFIER_TYPES_OUT: render_modifier_types(plan),
        LOC_OUT: render_loc(plan),
    }


def regenerate(mod_state=None, *, root: Path = ROOT, dry_run: bool = False) -> dict:
    """Post-load entry point (server/post_load.py's POST_LOAD_REGENERATORS) and CLI body.

    Writes a file only when its content changed, with one UTF-8 BOM.
    """
    if mod_state is None:
        mod_state = load_state(root)
    changed = []
    for relative, text in plan_outputs(mod_state, root).items():
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
