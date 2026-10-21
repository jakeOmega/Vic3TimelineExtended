"""Demographics phase 3: the metropolitan share (docs/superpowers/specs/2026-10-08-demographics-design.md §5.2).

The target's eight terms through test_demographics_registry's state interpreter against demographics_metro.py (its
Python twin) on a grid of inputs; the yearly update (seed at the target, the drift, the floor, the census off) and the
modifiers' one refresh site; the census's urban fertility term; static checks on the constants, the modifiers' sizes
and signs, the census type and its carrier, the Overspill's switch to the real share, the panel's wiring and loc, the
nation tab's registry and the docs' self-check row.
"""

import importlib.util
import itertools
import re
import sys
import unittest

import test_demographics_registry as R
from test_demographics_registry import ROOT, _block, _Engine, _parse_script, _raw_blocks, _text

sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_metro as DMT  # noqa: E402
import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402

METRO_VALUES = ROOT / "common" / "script_values" / "te_demog_metro_values.txt"
METRO_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_metro_effects.txt"
METRO_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_metro_modifiers.txt"
METRO_SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_metro_sguis.txt"
METRO_GUI = ROOT / "gui" / "te_demographics_metro.gui"
WIDGETS = ROOT / "gui" / "te_demographics_widgets.gui"
TYPES_FILE = ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt"
INSTITUTIONS = ROOT / "common" / "institutions" / "extra_institutions.txt"
DEMOG_ON_ACTIONS = ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"
WAVE_TRIGGERS = ROOT / "common" / "scripted_triggers" / "te_demog_wave_triggers.txt"
WAVE_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_wave_effects.txt"
ENGINE_MODIFIERS = ROOT / "docs" / "engine" / "modifiers_summary.txt"
VANILLA_MODIFIER_TYPES = ROOT / "vanilla_parsed" / "common" / "modifier_types.json"
MOD_MODIFIER_TYPES = ROOT / "common" / "modifier_type_definitions"
PLAYTEST = ROOT / "docs" / "testing" / "demographics-playtest.md"
LOC_DIR = ROOT / "localization" / "english"

# te_demog_k_mt_* -> its demographics_params.py constant
PINNED = {
    "te_demog_k_mt_drift": P.MT_DRIFT, "te_demog_k_mt_base": P.MT_BASE, "te_demog_k_mt_min": P.MT_MIN,
    "te_demog_k_mt_max": P.MT_MAX, "te_demog_k_mt_min_urban": P.MT_MIN_URBAN,
    "te_demog_k_mt_metropolis": P.MT_LABELS[0], "te_demog_k_mt_leading": P.MT_LABELS[1],
    "te_demog_k_mt_several": P.MT_LABELS[2], "te_demog_k_mt_capital": P.MT_CAPITAL, "te_demog_k_mt_hub": P.MT_HUB,
    "te_demog_k_mt_finance_per_level": P.MT_FINANCE_PER_LEVEL, "te_demog_k_mt_finance_max": P.MT_FINANCE_MAX,
    "te_demog_k_mt_area_free": P.MT_AREA_FREE, "te_demog_k_mt_area_step": P.MT_AREA_STEP,
    "te_demog_k_mt_work": P.MT_WORK, "te_demog_k_mt_urban_peak": P.MT_URBAN_PEAK,
    "te_demog_k_mt_urban_width": P.MT_URBAN_WIDTH, "te_demog_k_mt_urban_size": P.MT_URBAN_SIZE,
    "te_demog_k_mt_infra": P.MT_INFRA, "te_demog_k_mt_crowd": P.MT_CROWD,
    "te_demog_k_mt_crowd_ceiling": P.MT_CROWD_CEILING,
    "te_demog_k_mt_planned_towns_per_level": P.MT_PLANNED_TOWNS_PER_LEVEL,
    "te_demog_k_mt_planned_capital": P.MT_PLANNED_CAPITAL, "te_demog_k_mt_plan_min": P.MT_PLAN_MIN,
    "te_demog_k_mt_effect_from": P.MT_EFFECT_FROM, "te_demog_k_mt_effect_full": P.MT_EFFECT_FULL,
    "te_demog_k_mt_dispersed_from": P.MT_DISPERSED_FROM, "te_demog_k_mt_dispersed_full": P.MT_DISPERSED_FULL,
    "te_demog_k_mt_crowding": P.MT_EFFECTS["state_migration_crowding_density_mult"],
    "te_demog_k_mt_infra_up": P.MT_EFFECTS["state_infrastructure_from_population_mult"],
    "te_demog_k_mt_services": P.MT_EFFECTS["building_urban_center_throughput_add"],
    "te_demog_k_mt_turmoil": P.MT_EFFECTS["state_turmoil_effects_mult"],
    "te_demog_k_mt_infra_down": P.MT_DISPERSED_EFFECTS["state_infrastructure_from_population_mult"],
    "te_demog_k_mt_fertility": P.MT_FERTILITY,
}


def _constants():
    return {m.group(1): float(m.group(2)) for m in
            re.finditer(r"^(te_demog_k_mt_\w+) = \{ value = (-?[\d.]+) \}", _text(METRO_VALUES), re.M)}


def _modifier(name):
    return {k: float(v) for k, _, v in _parse_script(_block(_text(METRO_MODIFIERS), name)) if k != "icon"}


class _MetroEngine(_Engine):
    """The state interpreter with the metro values and effects, and the engine reads the target makes:
    has_building (self.buildings), `X ?= { ... }` for the owner and the Settlement Authority (self.owner_census,
    self.planned_towns), every_state for the hub self-check (stubbed: the census's test doesn't need it)."""

    def __init__(self, fixtures, triggers=None, buildings=(), owner_census=True, planned_towns=False):
        super().__init__(fixtures, triggers=triggers, effects={"te_debug_demog_mt_hub_selfcheck": ""})
        self.values.update(_raw_blocks([METRO_VALUES]))
        self.effects.update({k: v for k, v in _raw_blocks([METRO_EFFECTS]).items()
                             if k != "te_debug_demog_mt_hub_selfcheck"})
        self.buildings = set(buildings)
        self.owner_census = owner_census
        self.planned_towns = planned_towns

    def holds(self, items):
        merged, i = [], 0
        while i < len(items):
            key, op, arg = items[i]
            if op == "" and i + 1 < len(items) and items[i + 1][0] == "?" and items[i + 1][1] == "=":
                merged.append((key, "?=", items[i + 1][2]))
                i += 2
                continue
            merged.append(items[i])
            i += 1
        return all(self._test(*item) for item in merged)

    def _test(self, key, op, arg):
        if key == "has_building":
            return arg in self.buildings
        if op == "?=" and key == "owner":
            return self.owner_census
        if op == "?=" and key == "b:building_resettlement_colony":
            return self.planned_towns
        return super()._test(key, op, arg)


_TEMPLATE = []


def _fresh(fixtures, triggers, buildings=(), owner_census=True, planned_towns=False):
    """A new _MetroEngine sharing one template's parsed files (an _Engine reads some twenty files when made)."""
    if not _TEMPLATE:
        _TEMPLATE.append(_MetroEngine({}))
    t = _TEMPLATE[0]
    eng = object.__new__(_MetroEngine)
    eng.__dict__.update(t.__dict__)
    eng.fixtures = {**t.fixtures, **fixtures}
    eng.trigger_fixtures = {**t.trigger_fixtures, **triggers}
    eng.vars, eng.locals, eng.modifiers, eng.removed, eng.decrees = {}, {}, {}, [], set()
    eng.buildings, eng.owner_census, eng.planned_towns = set(buildings), owner_census, planned_towns
    return eng


def _engine(pl, full=True, census=True, share=None, urban=50000.0):
    """A state with `pl`'s inputs (demographics_metro.Place) as the interpreter's fixtures."""
    usage = 100.0
    fixtures = {
        "te_region_area_km2": float(max(pl.area, 1.0)),
        "infrastructure": usage * (1 + pl.infra_surplus),
        "infrastructure_usage": usage,
        "modifier:state_metro_share_add": float(P.MT_MINISTRY_PER_LEVEL * pl.ministry_levels),
        "b:building_financial_district.level": float(pl.finance_levels),
        "b:building_resettlement_colony.level": float(pl.planned_towns_levels),
        "owner.var:te_dg_urban_share": float(pl.national),
    }
    eng = _fresh(fixtures, {"is_capital": pl.capital, "is_world_market_hub": pl.hub, "te_demog_effects_run": full,
                            "te_demog_cohorts_run": census},
                 buildings={"building_financial_district"} if pl.finance_levels else set(),
                 planned_towns=pl.planned_towns_levels > 0)
    eng.vars.update(te_dg_urban=urban, te_dg_urban_share=float(pl.urban_share))
    if pl.crowding > 0:
        eng.vars["migration_crowding_mult_applied"] = float(pl.crowding)
    if pl.planned_capital:
        eng.modifiers["te_demog_pc_new_capital"] = 1.0
    if share is not None:
        eng.vars["te_dg_mt"] = float(share)
    return eng


# Each input's values on the grid: the area takes every rung of its ladder (Texas, 536,486 km2, is the 4x-8x one), and
# the ministry's 20 levels with Planned Towns and a Planned Capital pass the planning term's floor.
GRID = {"urban_share": (0.05, 0.4, 0.95), "national": (0.08, 0.5, 0.92), "capital": (False, True),
        "hub": (False, True), "finance_levels": (0, 4, 14), "area": (5000, 150000, 320000, 536486, 900000),
        "infra_surplus": (-0.2, 0.4, 1.5), "crowding": (0.0, 2.0, 6.0), "ministry_levels": (0, 7, 20),
        "planned_towns_levels": (0, 3), "planned_capital": (False, True)}


def _grid():
    """A seventh of the product (7 is prime to every axis' length, so it still takes every value of each input)."""
    for i, combo in enumerate(itertools.product(*GRID.values())):
        if i % 7:
            continue
        yield DMT.Place(**dict(zip(GRID, combo)))


class TestConstants(unittest.TestCase):
    def test_each_constant_is_pinned_to_the_params(self):
        k = _constants()
        self.assertEqual(set(k), set(PINNED))
        for name, want in PINNED.items():
            self.assertAlmostEqual(k[name], want, places=9, msg=name)

    def test_the_constants_parse_as_engine_literals(self):
        for name, v in _constants().items():
            self.assertLessEqual(len(repr(v).split(".")[-1]), 5, name)

    def test_the_area_ladder_is_three_doublings(self):
        """The script's ladder hard-codes three doublings (te_demog_mt_area_2/_4/_8)."""
        self.assertEqual(P.MT_AREA_DOUBLINGS, 3)
        text = _text(METRO_VALUES)
        for n in (2, 4, 8):
            self.assertIn(f"te_demog_mt_area_{n} = {{\n\tvalue = te_demog_k_mt_area_free\n\tmultiply = {n}\n}}", text)

    def test_the_anchors_read_their_labels(self):
        """The owner's anchors (2026-10-19): New York, Buenos Aires and Paris high; Texas and Germany's states lower."""
        for name, pl, want in DMT.ANCHORS:
            self.assertEqual(DMT.label(DMT.target(pl)), want, name)


class TestTarget(unittest.TestCase):
    """te_demog_mt_target and each term (the script) against demographics_metro (its twin)."""

    def test_the_script_matches_the_model_on_a_grid(self):
        n = 0
        for pl in _grid():
            eng = _engine(pl)
            want = DMT.terms(pl)
            for term in DMT.TERMS:
                self.assertAlmostEqual(eng.number(f"te_demog_mt_t_{term}"), want[term], places=6, msg=(term, pl))
            self.assertAlmostEqual(eng.number("te_demog_mt_target"), DMT.target(pl), places=6, msg=pl)
            n += 1
        self.assertGreater(n, 4000)

    def test_the_grid_takes_every_value_and_every_branch(self):
        cases = list(_grid())
        for name, values in GRID.items():
            self.assertEqual({getattr(pl, name) for pl in cases}, set(values), name)
        free = P.MT_AREA_FREE
        for lo, hi in ((0, free), (free, 2 * free), (2 * free, 4 * free), (4 * free, 8 * free), (8 * free, 1e9)):
            self.assertTrue(any(lo < pl.area <= hi for pl in cases), (lo, hi))
        raw = [P.MT_MINISTRY_PER_LEVEL * pl.ministry_levels + P.MT_PLANNED_TOWNS_PER_LEVEL * pl.planned_towns_levels
               + (P.MT_PLANNED_CAPITAL if pl.planned_capital else 0) for pl in cases]
        self.assertLess(min(raw), P.MT_PLAN_MIN, "the planning floor")
        self.assertTrue(any(DMT.terms(pl)["planning"] == P.MT_PLAN_MIN and P.MT_MIN < DMT.target(pl) < P.MT_MAX
                            for pl in cases), "the floor binds where the target isn't clamped")

    def test_the_area_term_is_continuous_and_capped(self):
        for a in (100000, 200000, 400000, 800000):
            self.assertAlmostEqual(DMT.area_term(a - 1e-6), DMT.area_term(a + 1e-6), places=4)
        self.assertEqual(DMT.area_term(5_000_000), -P.MT_AREA_STEP * P.MT_AREA_DOUBLINGS)
        self.assertEqual(DMT.area_term(P.MT_AREA_FREE), 0.0)

    def test_the_urban_term_is_an_inverted_u(self):
        peak = DMT.urban_term(P.MT_URBAN_PEAK)
        self.assertEqual(peak, P.MT_URBAN_SIZE)
        self.assertAlmostEqual(DMT.urban_term(0.1), 0.0)
        self.assertAlmostEqual(DMT.urban_term(0.9), 0.0)
        self.assertLess(DMT.urban_term(1.0), 0)

    def test_the_target_is_clamped(self):
        top = DMT.Place(1.0, 0.5, capital=True, hub=True, finance_levels=20)
        bottom = DMT.Place(0.0, 0.0, area=2e6, infra_surplus=2, crowding=9, ministry_levels=30)
        self.assertEqual(DMT.target(top), P.MT_MAX)
        self.assertEqual(DMT.target(bottom), P.MT_MIN)
        self.assertEqual(_engine(top).number("te_demog_mt_target"), P.MT_MAX)
        self.assertEqual(_engine(bottom).number("te_demog_mt_target"), P.MT_MIN)

    def test_the_owner_without_a_census_reads_the_states_own_share(self):
        pl = DMT.Place(0.3, 0.7)
        eng = _engine(pl)
        eng.owner_census = False
        self.assertAlmostEqual(eng.number("te_demog_mt_national"), 0.3)


class TestUpdate(unittest.TestCase):
    """te_demog_mt_state_update: the stock's seed, drift and removal (the census on, any setting)."""
    PL = DMT.Place(0.6, 0.4, capital=True, area=40000, infra_surplus=0.2)

    def test_a_state_without_a_share_seeds_at_its_target(self):
        eng = _engine(self.PL, full=False)
        eng.call("te_demog_mt_state_update")
        self.assertAlmostEqual(eng.vars["te_dg_mt"], DMT.target(self.PL), places=6)

    def test_the_share_moves_a_twentieth_of_the_way(self):
        eng = _engine(self.PL, share=30.0)
        eng.call("te_demog_mt_state_update")
        self.assertAlmostEqual(eng.vars["te_dg_mt"], DMT.step(30.0, DMT.target(self.PL)), places=6)
        self.assertAlmostEqual(eng.vars["te_dg_mt"], 30.0 + 0.05 * (DMT.target(self.PL) - 30.0), places=6)

    def test_too_few_urban_people_or_the_census_off_keep_no_share(self):
        for kw in ({"urban": P.MT_MIN_URBAN - 1.0}, {"census": False}):
            eng = _engine(self.PL, share=50.0, **kw)
            eng.call("te_demog_mt_state_update")
            self.assertNotIn("te_dg_mt", eng.vars, kw)
            eng = _engine(self.PL, **kw)
            eng.call("te_demog_mt_state_update")
            self.assertNotIn("te_dg_mt", eng.vars, kw)

    def test_it_runs_first_on_the_state_pulse_and_the_refresh_last(self):
        hook = _block(_text(DEMOG_ON_ACTIONS), "te_demog_state_yearly_on_action")
        self.assertLess(hook.index("te_demog_mt_state_update = yes"), hook.index("te_demog_state_yearly = yes"))
        self.assertLess(hook.index("te_demog_pc_state_check = yes"), hook.index("te_demog_mt_state_refresh = yes"))
        for name in ("te_demog_mt_metropolis", "te_demog_mt_dispersed"):
            sites = [p for p in (ROOT / "common").rglob("*.txt") if f"name = {name}" in _text(p)]
            self.assertEqual(sites, [METRO_EFFECTS], name)

    def test_the_census_gate_is_the_only_rule_read(self):
        update = _block(_text(METRO_EFFECTS), "te_demog_mt_state_update")
        self.assertIn("te_demog_cohorts_run = yes", update)
        self.assertNotIn("te_demog_effects_run", update)


class TestRefresh(unittest.TestCase):
    """te_demog_mt_state_refresh: the two modifiers' one refresh site, under Full only."""

    def refresh(self, share, full=True, held=()):
        eng = _engine(DMT.Place(0.5, 0.5), full=full, share=share)
        for name in held:
            eng.modifiers[name] = 0.3
        eng.call("te_demog_mt_state_refresh")
        return eng

    def test_a_metropolis_takes_the_concentrated_side(self):
        for share in (45.0, 50.0, 60.0, 80.0):
            eng = self.refresh(share)
            self.assertEqual(eng.modifiers, {"te_demog_mt_metropolis": DMT.concentrated(share)}, share)
            self.assertEqual(eng.vars["te_dg_mt_mult"], DMT.concentrated(share))

    def test_market_towns_take_the_dispersed_side(self):
        for share in (15.0, 10.0, 5.0):
            eng = self.refresh(share)
            self.assertEqual(eng.modifiers, {"te_demog_mt_dispersed": DMT.dispersed(share)}, share)

    def test_several_cities_and_leading_citys_floor_are_the_baseline(self):
        for share in (20.0, 30.0, 40.0):
            self.assertEqual(self.refresh(share).modifiers, {}, share)

    def test_nothing_outside_full_and_the_old_modifier_comes_off(self):
        eng = self.refresh(80.0, full=False, held=("te_demog_mt_metropolis", "te_demog_mt_dispersed"))
        self.assertEqual(eng.modifiers, {})
        eng = self.refresh(10.0, held=("te_demog_mt_metropolis",))
        self.assertEqual(set(eng.modifiers), {"te_demog_mt_dispersed"})

    def test_the_multiplier_variable_is_never_removed(self):
        self.assertNotIn("remove_variable = te_dg_mt_mult", _text(METRO_EFFECTS))

    def test_the_strengths_match_the_model(self):
        for share in range(0, 101, 5):
            eng = _engine(DMT.Place(0.5, 0.5), share=float(share))
            self.assertAlmostEqual(eng.number("te_demog_mt_e_pos"), DMT.concentrated(share), places=6)
            self.assertAlmostEqual(eng.number("te_demog_mt_e_neg"), DMT.dispersed(share), places=6)
            self.assertEqual(eng.number("te_demog_mt_label"), DMT.label(share), share)
            self.assertFalse(DMT.concentrated(share) and DMT.dispersed(share), share)


class TestFertility(unittest.TestCase):
    """The census's urban term raised by the share, under Full only (te_demog_mt_fertility_scale)."""

    def scale(self, share, full):
        eng = _engine(DMT.Place(0.5, 0.5), full=full, share=share)
        return eng.number("te_demog_mt_fertility_scale")

    def test_exactly_one_outside_full_or_without_a_share(self):
        self.assertEqual(self.scale(90.0, full=False), 1.0)
        self.assertEqual(self.scale(None, full=True), 1.0)
        self.assertEqual(self.scale(30.0, full=True), 1.0)

    def test_a_tenth_at_full_strength(self):
        self.assertAlmostEqual(self.scale(60.0, full=True), 1 + P.MT_FERTILITY)
        self.assertAlmostEqual(self.scale(50.0, full=True), DMT.fertility_scale(50.0))

    def test_the_urban_term_reads_it_and_the_model_twins_it(self):
        self.assertIn("multiply = te_demog_mt_fertility_scale", _block(_text(R.VALUES), "te_demog_tfr_urban"))
        inp = M.Inputs(urban_share=0.8)
        base = M.urban_term(inp)
        inp.metro_scale = DMT.fertility_scale(70.0)
        self.assertAlmostEqual(1 - M.urban_term(inp), (1 - base) * (1 + P.MT_FERTILITY))
        # at most a tenth of the urban term, so desired fertility in a wholly urban metropolis falls by at most 2 points
        self.assertLessEqual((1 - M.urban_term(M.Inputs(urban_share=1.0, metro_scale=DMT.fertility_scale(100))))
                             - (1 - M.urban_term(M.Inputs(urban_share=1.0))), 0.02 + 1e-9)


class TestModifiers(unittest.TestCase):
    def test_the_fields_are_the_values(self):
        k = _constants()
        self.assertEqual(_modifier("te_demog_mt_metropolis"), {
            "state_migration_crowding_density_mult": k["te_demog_k_mt_crowding"],
            "state_infrastructure_from_population_mult": k["te_demog_k_mt_infra_up"],
            "building_urban_center_throughput_add": k["te_demog_k_mt_services"],
            "state_turmoil_effects_mult": k["te_demog_k_mt_turmoil"]})
        self.assertEqual(_modifier("te_demog_mt_dispersed"), {
            "state_infrastructure_from_population_mult": k["te_demog_k_mt_infra_down"]})
        self.assertEqual(_modifier("te_demog_mt_metropolis"), P.MT_EFFECTS)
        self.assertEqual(_modifier("te_demog_mt_dispersed"), P.MT_DISPERSED_EFFECTS)

    def test_every_effect_is_within_a_tenth(self):
        """Owner, 2026-10-19: each effect at most 10% at the Metropolis label (the extreme)."""
        for size in (*P.MT_EFFECTS.values(), *P.MT_DISPERSED_EFFECTS.values(), P.MT_FERTILITY):
            self.assertLessEqual(abs(size), 0.10)

    def test_the_metropolis_crowds_sooner(self):
        """state_population_density divides by 1 + state_migration_crowding_density_mult (a positive value is
        capacity), so the spec's denser metropolis is a negative value."""
        self.assertIn("add = modifier:state_migration_crowding_density_mult",
                      _block(_text(ROOT / "common" / "script_values" / "extra_script_values.txt"),
                             "state_population_density"))
        self.assertLess(P.MT_EFFECTS["state_migration_crowding_density_mult"], 0)

    def test_every_field_is_an_engine_modifier(self):
        """modifiers.log lists a throughput type for every building, but a static modifier can use only a type that
        vanilla's or the mod's modifier_type_definitions registers: building_financial_district_throughput_add was in
        the log and the game dropped it as unknown (#1096)."""
        import json
        known = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        registered = set(json.load(open(VANILLA_MODIFIER_TYPES, encoding="utf-8")))
        for path in MOD_MODIFIER_TYPES.glob("*.txt"):
            registered |= set(re.findall(r"^(?:INJECT:|REPLACE:)?(\w+)\s*=\s*\{", _text(path), re.M))
        for name in ("te_demog_mt_metropolis", "te_demog_mt_dispersed"):
            for field in _modifier(name):
                self.assertIn(field, known, f"{name}: {field}")
                self.assertIn(field, registered, f"{name}: {field} is not a registered modifier type")

    def test_every_field_has_a_name(self):
        """The engine shows a raw key for a field with no loc line and logs nothing (review I1, 2026-10-20): each field
        of both modifiers is named in vanilla's loc snapshot or the mod's."""
        import json
        names = dict(json.load(open(ROOT / "vanilla_parsed" / "localization_english.json", encoding="utf-8")))
        for path in LOC_DIR.glob("*.yml"):
            for line in _text(path).splitlines():
                m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
                if m:
                    names[m.group(1)] = m.group(2)
        for name in ("te_demog_mt_metropolis", "te_demog_mt_dispersed"):
            for field in _modifier(name):
                self.assertIn(field, names, f"{name}: {field}")
                self.assertIn(f"{field}_desc", names, f"{name}: {field}_desc")

    def test_the_nation_tab_places_them_on_states(self):
        spec = importlib.util.spec_from_file_location("gen_nation_tab",
                                                      ROOT / "scripts" / "generators" / "gen_nation_tab.py")
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        self.assertEqual(gen.NOT_ON_COUNTRY.get("te_demog_mt_*"), "states")


class TestCensusType(unittest.TestCase):
    def test_the_type_is_registered_script_only_and_named(self):
        body = _block(_text(TYPES_FILE), P.MT_TYPE)
        for line in ("script_only = yes", "percent = no", "decimals = 0", "color = neutral"):
            self.assertIn(line, body)
        loc = _text(LOC_DIR / "te_modifiers_l_english.yml")
        self.assertRegex(loc, rf"(?m)^ {P.MT_TYPE}:0 \"")
        self.assertRegex(loc, rf"(?m)^ {P.MT_TYPE}_desc:0 \"")
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        self.assertNotIn(P.MT_TYPE, engine)

    def test_the_ministry_carries_it_a_level(self):
        body = _block(_text(INSTITUTIONS), "institution_ministry_of_urban_planning")
        self.assertIn(f"{P.MT_TYPE} = {P.MT_MINISTRY_PER_LEVEL}", body)
        self.assertIn(f"value = modifier:{P.MT_TYPE}", _block(_text(METRO_VALUES), "te_demog_mt_plan_ministry"))


class TestOverspill(unittest.TestCase):
    """§9: the Overspill fires on a Metropolis-pattern state with crowding active, the stand-in gone."""

    def test_the_trigger_reads_the_share(self):
        text = _text(WAVE_TRIGGERS)
        cond = _block(text, "te_demog_wave_cond_overspill")
        self.assertIn("te_demog_wave_overspill_state = yes", cond)
        state = _block(text, "te_demog_wave_overspill_state")
        self.assertIn("var:te_dg_mt >= te_demog_k_mt_metropolis", state)
        self.assertIn("te_demog_wave_crowded_city = yes", state)
        self.assertNotIn("te_dg_urban_label", cond + state)

    def test_the_stand_in_is_gone_and_the_event_sits_on_the_metropolis(self):
        effects = _text(WAVE_EFFECTS)
        self.assertNotIn("te_dg_wv_city_crowded", effects + _text(WAVE_TRIGGERS))
        pick = _block(effects, "te_demog_wave_pick_city")
        self.assertLess(pick.index("te_demog_wave_overspill_state = yes"), pick.index("capital = {"))

    def test_the_wave_models_twin_reads_the_share(self):
        import demographics_wave as DW
        self.assertIn("te_dg_mt", DW.STATE_VARS)
        src = (ROOT / "scripts" / "analysis" / "demographics_wave.py").read_text(encoding="utf-8")
        self.assertIn('sv.get("te_dg_mt", 0.0) >= P.MT_LABELS[0]', src)


class TestPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = {}
        for path in LOC_DIR.glob("*.yml"):
            for line in _text(path).splitlines():
                m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
                if m:
                    cls.loc[m.group(1)] = m.group(2)

    def test_the_rows_are_gated_and_wired(self):
        from test_demographics_layout import _type_body
        widgets = _text(WIDGETS)
        pyramid = _type_body(widgets, "te_state_demog_pyramid")
        self.assertIn("GetScriptedGui('te_demog_state_mt_sgui')", pyramid)
        self.assertIn("GetScriptedGui('te_demog_state_mt_none_sgui')", pyramid)
        self.assertIn("te_demog_mt_tooltip = {}", pyramid)
        self.assertLess(pyramid.index('text = "te_demog_st_urban"'), pyramid.index('text = "te_demog_mt_st"'))
        self.assertIn('text = "te_demog_mt_pl_value"', _type_body(widgets, "te_demog_sec_places"))
        sguis = _raw_blocks([METRO_SGUIS])
        self.assertIn("has_variable = te_dg_mt", sguis["te_demog_state_mt_sgui"])
        self.assertIn("te_demog_mt_too_few > 0", sguis["te_demog_state_mt_none_sgui"])

    def test_the_tooltip_draws_every_term_as_a_bar(self):
        gui = _text(METRO_GUI)
        self.assertIn("type te_demog_mt_tooltip = TooltipWidgetType {", gui)
        self.assertIn('blockoverride "tooltip_content_after"', gui)
        for term in DMT.TERMS:
            self.assertEqual(gui.count(f"ScriptValue('te_demog_mt_t_{term}')"), 3, term)
            self.assertIn(f'text = "te_demog_mt_bar_{term}"', gui)
            self.assertIn(f'tooltip = "te_demog_mt_bar_{term}_tt"', gui)

    def test_every_key_the_panel_names_exists(self):
        texts = _text(METRO_GUI) + _text(WIDGETS)
        keys = set(re.findall(r'(?:text|tooltip) = "(te_demog_mt_\w+)"', texts))
        self.assertGreater(len(keys), 20)
        for key in keys | {"te_demog_mt_st_tt_plain", "te_demog_mt_label_0", "te_demog_mt_label_1",
                           "te_demog_mt_label_2", "te_demog_mt_label_3", "te_demog_mt_eff_metro",
                           "te_demog_mt_eff_dispersed", "te_demog_mt_eff_none", "te_demog_mt_eff_display"}:
            self.assertIn(key, self.loc, key)

    def test_every_script_value_the_loc_reads_exists(self):
        values = set(_raw_blocks([METRO_VALUES]))
        for key, text in self.loc.items():
            if key.startswith("te_demog_mt_"):
                for name in re.findall(r"ScriptValue\('(te_demog_mt_\w+)'\)", text):
                    self.assertIn(name, values, f"{key}: {name}")

    def test_the_labels(self):
        self.assertEqual([self.loc[f"te_demog_mt_label_{i}"] for i in range(4)], list(DMT.LABELS))


class TestSelfCheck(unittest.TestCase):
    def test_the_hub_check_runs_once_and_is_listed(self):
        body = _block(_text(METRO_EFFECTS), "te_debug_demog_mt_hub_selfcheck")
        self.assertIn("te_debug_demog_selfchecks_run = yes", body)
        self.assertIn("NOT = { has_global_variable = te_demog_mt_hub_selfcheck_done }", body)
        self.assertIn("TE_SELF_CHECK OK metro_world_market_hub", body)
        self.assertIn("TE_SELF_CHECK BROKEN metro_world_market_hub", body)
        self.assertIn("metro_world_market_hub", _text(PLAYTEST))
        # review M1 (2026-10-20): OK needs hubs, every hub with a Port and some Port states that aren't hubs
        for cond in ("var:te_dg_mt_chk_hubs > 0", "var:te_dg_mt_chk_hub_noport = 0", "var:te_dg_mt_chk_port_nohub > 0"):
            self.assertIn(cond, body)
        self.assertIn("b:building_port ?= { level > 0 }", body)
        self.assertNotIn("te_debug_demog_mt_hub_most", body + _text(METRO_VALUES))


if __name__ == "__main__":
    unittest.main()
