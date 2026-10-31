"""The Deep-Sea Mine against the Extraplanetary Base at base prices (Global Commons § 1,
docs/superpowers/archive/specs/2026-10-16-global-commons-design.md).

Seabed licences cap the Deep-Sea Mine (building_ocean_mine), so § 1.1 makes each level
worth more than an Extraplanetary Base (building_space_mine) level until era 12's
propulsion arrives. § 1.2 gives the Extraplanetary Base two logistics groups, each with
one late upgrade cutting its Launch Capacity input (Fusion Tugs in era 12, Tethered Launch
in era 13 since the era 13 split); with Space Colonization and both, it out-earns the
Deep-Sea Mine per level.

The Deep-Sea Mine's ships are in a group of their own, its support vessels: Motor Ship
Tenders by default, and Magnetic Drive Tenders once the technology that makes those
ships arrives. Every Deep-Sea figure counts them: a claim that the mine earns more holds
on the dearer tenders, and a claim that it earns less holds on the cheaper.

Everything is read from the files: the buildings' method groups, each method's goods and
staff (the Deep-Sea Mine's a level, the Extraplanetary Base's a flat crew at any level,
owner 2026-10-31), the logistics methods' input multipliers, the technologies' eras and the goods'
base prices (vanilla_parsed plus the mod's goods file, as pm_costs.py prices them). The
two buildings share their other groups (maintenance), which cancel in every comparison.

Methods are compared era with era, as § 1.2's table does. One known gap: Space
Colonization and Advanced Nanofabrication are both era 12 and neither requires the other,
so a country with only the first runs its Deep-Sea Mines on the era-11 method beside a
Mining Colony that earns more per level (though not per point of construction).

The Extraplanetary Base opens in era 10 on Regolith Processing (lunar colonization
design § 6, docs/superpowers/specs/2026-10-29-lunar-colonization-design.md), before
any Deep-Sea Mine: an era with no Deep-Sea method has nothing to compare, and every
ordering from era 11 on is unchanged.

Run `python3 test_deep_sea_rebalance.py --table` to print the per-level figures.
"""
import glob
import itertools
import json
import os
import re
import sys
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))

DEEP_SEA = "building_ocean_mine"
SPACE = "building_space_mine"
# The § 1.2 logistics groups and the technology each one's upgrade waits for.
LOGISTICS = {
    "pmg_launch_to_orbit_building_space_mine": "space_elevator",
    "pmg_transport_in_space_building_space_mine": "compact_fusion_reactors",
}
LOGISTICS_MODIFIER = "goods_input_launch_capacity_mult"
LOGISTICS_CUT = -0.3
LAND_TECH_METAL_MINE = "pm_smart_miners_building_tech_metals_mine"
# The Deep-Sea Mine's support vessels: one free default and one upgrade, each costing one
# kind of ship and nothing else.
VESSELS = "pmg_support_vessels_building_ocean_mine"
SHIP_GOODS = {"clippers", "steamers", "motor_ships", "magnetic_drive_ships"}
# Vanilla game/common/defines/00_ai.txt (1.14.5), unless extra_defines.txt overrides them.
VANILLA_AI_DEFINES = {
    "PRODUCTION_METHOD_BASE_VALUE": 1000.0,
    "PRODUCTION_METHOD_STICKINESS_DOWNGRADE": 0.75,
    "PRODUCTION_METHOD_REDUCE_OUTPUT_PENALTY_FACTOR": 10.0,
}
# The rebalance holds under the Global Commons rule; with it off the mine is uncapped
# and keeps the methods it had before (spec § 2.9), its *_uncapped family.
RULE, RULE_ON, RULE_OFF = "global_commons_rule", "global_commons_enabled", "global_commons_disabled"
UNCAPPED = "_uncapped"


def _unwrap(value):
    while isinstance(value, tuple) and len(value) == 2:
        value = value[1]
    return value


def _parse_dir(*parts):
    parser = ParadoxFileParser()
    for path in sorted(glob.glob(os.path.join(REPO, *parts, "*.txt"))):
        parser.parse_file(path)
    return {key: _unwrap(value) for key, value in parser.data.items()}


def _list(value):
    value = _unwrap(value)
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _block(body, *path):
    for key in path:
        body = _unwrap(body.get(key)) if isinstance(body, dict) else None
    return body if isinstance(body, dict) else {}


def _assert_tracked_texture(case, texture):
    case.assertTrue(texture.startswith("gfx/interface/icons/production_method_icons/"))
    # CI checks out without gfx/, so accept a texture git tracks.
    if not os.path.exists(os.path.join(REPO, texture)):
        import subprocess
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", texture],
                                 cwd=REPO, capture_output=True)
        case.assertEqual(tracked.returncode, 0, texture)


class _Data:
    """The parsed entities, loaded once for the module."""

    def __init__(self):
        import pm_costs  # prices exactly as the cost comments in extra_pms.txt are made

        self.prices = pm_costs.load_goods()
        self.pms = _parse_dir("common", "production_methods")
        self.groups = _parse_dir("common", "production_method_groups")
        self.buildings = _parse_dir("common", "buildings")
        self.techs = _parse_dir("common", "technology", "technologies")
        self.values = _parse_dir("common", "script_values")
        self.modifier_types = _parse_dir("common", "modifier_type_definitions")
        self.rules = _parse_dir("common", "game_rules")
        with open(os.path.join(REPO, "common", "defines", "extra_defines.txt"), encoding="utf-8-sig") as f:
            self.defines = re.sub(r"#[^\n]*", "", f.read())
        self._vanilla_techs = None

    def era(self, tech):
        body = self.techs.get(tech)
        if body is None:
            if self._vanilla_techs is None:
                with open(os.path.join(REPO, "vanilla_parsed", "common", "technologies.json"),
                          encoding="utf-8") as f:
                    self._vanilla_techs = json.load(f)
            body = self._vanilla_techs.get(tech)
            body = body[1] if isinstance(body, list) else body
        era = _unwrap(body.get("era")) if isinstance(body, dict) else None
        if not isinstance(era, str) or not era.startswith("era_"):
            raise AssertionError(f"technology {tech} has no era")
        return int(era[len("era_"):])

    def building_groups(self, building):
        return [str(g) for g in _list(self.buildings[building].get("production_method_groups"))]

    def group_methods(self, group, setting=RULE_ON):
        """The group's methods a game under `setting` of the Global Commons rule can use."""
        off = self.rule_disabled(setting)
        return [str(m) for m in _list(self.groups[group].get("production_methods"))
                if str(m) not in off]

    def rule_disabled(self, setting):
        """The methods a setting of the Global Commons rule switches off (disable_pm_ flags)."""
        body = _block(self.rules[RULE], setting)
        flags = [str(_unwrap(f)) for f in _list(body.get("flag"))]
        return {f[len("disable_"):] for f in flags if f.startswith("disable_pm_")}

    def base_group(self, building):
        return self.building_groups(building)[0]

    def method_era(self, pm, building):
        """The era a method becomes available: its latest unlocking technology's, or the
        building's own when it has none."""
        techs = _list(self.pms[pm].get("unlocking_technologies")) or \
            _list(self.buildings[building].get("unlocking_technologies"))
        return max(self.era(str(t)) for t in techs)

    def goods(self, pm, direction):
        """{good: amount per level} from the method's workforce_scaled block."""
        block = _block(self.pms[pm], "building_modifiers", "workforce_scaled")
        prefix, suffix = f"goods_{direction}_", "_add"
        return {key[len(prefix):-len(suffix)]: float(_unwrap(v)) for key, v in block.items()
                if key.startswith(prefix) and key.endswith(suffix)}

    def employment(self, pm, bucket="level_scaled"):
        """The method's staff in one building_modifiers block: level_scaled is a level's,
        unscaled a flat crew's at any level."""
        block = _block(self.pms[pm], "building_modifiers", bucket)
        return sum(float(_unwrap(v)) for key, v in block.items()
                   if key.startswith("building_employment_") and key.endswith("_add"))

    def crew(self, pm):
        return self.employment(pm, "unscaled")

    def input_mults(self, pm):
        """{good: mult} for every goods_input_<good>_mult the method carries in unscaled."""
        block = _block(self.pms[pm], "building_modifiers", "unscaled")
        prefix, suffix = "goods_input_", "_mult"
        return {key[len(prefix):-len(suffix)]: float(_unwrap(v)) for key, v in block.items()
                if key.startswith(prefix) and key.endswith(suffix)}

    def value(self, pm, direction, mults=None):
        mults = mults or {}
        return sum(qty * self.prices[good] * (1 + mults.get(good, 0.0))
                   for good, qty in self.goods(pm, direction).items())

    def profit(self, pm, secondary=()):
        """Per-level profit at base prices of `pm` with the `secondary` methods of the
        building's other groups: their goods add to its own, and their input multipliers
        are summed (the engine adds same-type modifiers) and apply to all of them."""
        mults = {}
        for other in secondary:
            for good, mult in self.input_mults(other).items():
                mults[good] = mults.get(good, 0.0) + mult
        methods = (pm, *secondary)
        return sum(self.value(m, "output") - self.value(m, "input", mults) for m in methods)

    def tenders(self, pm):
        """The support-vessel methods a Deep-Sea Mine on `pm` can run in that method's era."""
        era = self.method_era(pm, DEEP_SEA)
        return [t for t in self.group_methods(VESSELS) if self.method_era(t, DEEP_SEA) <= era]

    def deep_profits(self, pm):
        """{tender: per-level profit} of Deep-Sea method `pm` on each tender of its era."""
        return {t: self.profit(pm, [t]) for t in self.tenders(pm)}

    def ai_define(self, key):
        m = re.search(r"\b" + key + r"\s*=\s*([\d.]+)", self.defines)
        return float(m[1]) if m else VANILLA_AI_DEFINES[key]

    def logistics_upgrades(self):
        """{group: its upgrade method}: the group's one method with an unlocking technology."""
        upgrades = {}
        for group in LOGISTICS:
            gated = [pm for pm in self.group_methods(group)
                     if _list(self.pms[pm].get("unlocking_technologies"))]
            upgrades[group] = gated[0] if len(gated) == 1 else None
        return upgrades

    def construction(self, building):
        name = str(_unwrap(self.buildings[building].get("required_construction")))
        return name, float(_unwrap(self.values[name]))


_DATA = None


def setUpModule():
    global _DATA
    _DATA = _Data()


class DeepSeaMineAgainstExtraplanetaryBase(unittest.TestCase):
    """§ 1.1: better on every axis but scale until the era-12 logistics upgrades."""

    def setUp(self):
        self.d = _DATA
        self.deep = self.d.group_methods(self.d.base_group(DEEP_SEA))
        self.space = self.d.group_methods(self.d.base_group(SPACE))

    def test_the_buildings_share_their_other_groups(self):
        """Only the base, logistics and support-vessel groups differ, so the rest cancels."""
        deep = [g for g in self.d.building_groups(DEEP_SEA)[1:] if g != VESSELS]
        space = [g for g in self.d.building_groups(SPACE)[1:] if g not in LOGISTICS]
        self.assertEqual(deep, space)

    def test_out_earns_every_method_of_its_era_without_upgrades(self):
        for deep, space in itertools.product(self.deep, self.space):
            if self.d.method_era(space, SPACE) > self.d.method_era(deep, DEEP_SEA):
                continue  # compared era with era (module docstring)
            with self.subTest(deep_sea=deep, extraplanetary=space):
                self.assertGreaterEqual(min(self.d.deep_profits(deep).values()),
                                        self.d.profit(space))

    def test_the_best_colony_grade_keeps_the_era_11_ordering(self):
        """Colony modules design § 9: a base level in the best colony's room (16 Psyche)
        works at its grade's extra throughput, which scales its goods both ways and so
        its profit; the era-11 Deep-Sea Mine still out-earns it per level."""
        sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
        import gen_solar_sites
        best = 1 + max(s.ebase_grade for s in gen_solar_sites.SITES) / 100
        base = [pm for pm in self.deep if self.d.method_era(pm, DEEP_SEA) == 11]
        for space in (pm for pm in self.space if self.d.method_era(pm, SPACE) == 11):
            with self.subTest(extraplanetary=space, throughput=best):
                self.assertGreater(min(self.d.deep_profits(base[0]).values()), best * self.d.profit(space))

    def test_era_11_outputs_each_at_least_the_asteroid_mine(self):
        era_11 = [pm for pm in self.space if self.d.method_era(pm, SPACE) == 11]
        self.assertTrue(era_11)
        base = [pm for pm in self.deep if self.d.method_era(pm, DEEP_SEA) == 11]
        self.assertEqual(len(base), 1)
        deep_out = self.d.goods(base[0], "output")
        for pm in era_11:
            for good, qty in self.d.goods(pm, "output").items():
                with self.subTest(extraplanetary=pm, good=good):
                    self.assertGreaterEqual(deep_out.get(good, 0.0), qty)
            with self.subTest(extraplanetary=pm, axis="input cost"):
                dearest = max(self.d.value(t, "input") for t in self.d.tenders(base[0]))
                self.assertLess(self.d.value(base[0], "input") + dearest,
                                self.d.value(pm, "input"))
            with self.subTest(extraplanetary=pm, axis="workforce"):
                # The base's flat crew is one Deep-Sea Mine level's staff (owner, 2026-10-31).
                self.assertEqual(self.d.employment(base[0]), self.d.crew(pm))

    def test_era_12_methods_double_the_base_output(self):
        base = [pm for pm in self.deep if self.d.method_era(pm, DEEP_SEA) == 11]
        self.assertEqual(len(base), 1)
        base_out = self.d.goods(base[0], "output")
        for pm in self.deep:
            if pm == base[0]:
                continue
            with self.subTest(method=pm):
                self.assertEqual(self.d.goods(pm, "output"),
                                 {good: 2 * qty for good, qty in base_out.items()})

    def test_construction_a_quarter_of_the_extraplanetary_base(self):
        name, deep = self.d.construction(DEEP_SEA)
        self.assertEqual(name, "construction_cost_mega_high")
        _, space = self.d.construction(SPACE)
        self.assertLessEqual(4 * deep, space)

    def test_base_method_margin_below_the_late_land_mines(self):
        base = [pm for pm in self.deep if self.d.method_era(pm, DEEP_SEA) == 11][0]

        def margin(pm, secondary=()):
            cost = sum(self.d.value(m, "input") for m in (pm, *secondary))
            return self.d.profit(pm, secondary) / cost

        for tender in self.d.tenders(base):
            with self.subTest(tender=tender):
                self.assertLess(margin(base, [tender]), margin(LAND_TECH_METAL_MINE))


class RegolithProcessing(unittest.TestCase):
    """Lunar colonization design § 6: the base opens in era 10 on a weak method of its
    own, and the Asteroid Mine waits for Asteroid Mining."""

    REGOLITH, ASTEROID = "pm_regolith_processing", "pm_space_mine"

    def setUp(self):
        self.d = _DATA
        self.space = self.d.group_methods(self.d.base_group(SPACE))

    def test_the_default_and_its_era(self):
        self.assertEqual(self.space[0], self.REGOLITH)  # first in the group: the default
        self.assertEqual(_list(self.d.pms[self.REGOLITH].get("unlocking_technologies")), [])
        self.assertEqual([str(t) for t in _list(self.d.buildings[SPACE].get("unlocking_technologies"))],
                         ["in_situ_resource_utilization"])
        self.assertEqual(self.d.method_era(self.REGOLITH, SPACE), 10)
        self.assertEqual([str(t) for t in _list(self.d.pms[self.ASTEROID].get("unlocking_technologies"))],
                         ["asteroid_mining"])
        self.assertEqual(self.d.method_era(self.ASTEROID, SPACE), 11)
        self.assertLess(self.d.method_era(self.REGOLITH, SPACE),
                        min(self.d.method_era(pm, DEEP_SEA) for pm in self.d.group_methods(self.d.base_group(DEEP_SEA))))

    def test_half_the_asteroid_mine_s_inputs_and_a_thin_profit(self):
        regolith, asteroid = self.d.goods(self.REGOLITH, "input"), self.d.goods(self.ASTEROID, "input")
        self.assertEqual(regolith, {good: qty / 2 for good, qty in asteroid.items()})
        profit = self.d.profit(self.REGOLITH)
        self.assertGreater(profit, 0)
        self.assertLess(4 * profit, self.d.profit(self.ASTEROID))  # under a quarter of its return a level
        self.assertEqual(self.d.crew(self.REGOLITH), 800)
        self.assertAlmostEqual(profit / self.d.crew(self.REGOLITH), 2.0)  # the wage one level can pay


class ExtraplanetaryBaseFlatCrew(unittest.TestCase):
    """Owner, 2026-10-31: a base needs its colonies' room to pay, so it hires a flat crew
    at any level, in `unscaled`, and no staff a level. Like every flat crew
    (test_ai_managed_flat_staff.py), the job is very attractive so the crew fills."""

    MIN_ATTRACTIVENESS = 5  # +500%, as pm_grid_transfer_base and the pm_ai_managed_* crews

    def setUp(self):
        self.d = _DATA

    def test_every_base_method_hires_a_flat_crew_only(self):
        for pm in self.d.group_methods(self.d.base_group(SPACE), None):
            with self.subTest(method=pm):
                self.assertGreater(self.d.crew(pm), 0)
                for bucket in ("level_scaled", "workforce_scaled"):
                    self.assertEqual(self.d.employment(pm, bucket), 0, bucket)

    def test_the_other_groups_hire_no_one(self):
        for group in self.d.building_groups(SPACE)[1:]:
            for pm in self.d.group_methods(group, None):
                for bucket in ("level_scaled", "workforce_scaled", "unscaled"):
                    with self.subTest(group=group, method=pm, bucket=bucket):
                        self.assertEqual(self.d.employment(pm, bucket), 0)

    def test_every_crew_is_a_very_attractive_job(self):
        for pm in self.d.group_methods(self.d.base_group(SPACE), None):
            unscaled = _block(self.d.pms[pm], "building_modifiers", "unscaled")
            with self.subTest(method=pm):
                value = _unwrap(unscaled.get("building_job_attractiveness_mult"))
                self.assertIsNotNone(value, "no building_job_attractiveness_mult in unscaled")
                self.assertGreaterEqual(float(value), self.MIN_ATTRACTIVENESS)


class RuleOffKeepsTheOldMine(unittest.TestCase):
    """§ 2.9: with the Global Commons rule off the mine is uncapped, so it keeps the
    pre-rebalance methods; the rule's two settings switch the families."""

    def setUp(self):
        self.d = _DATA
        self.group = self.d.base_group(DEEP_SEA)
        self.on = self.d.group_methods(self.group, RULE_ON)
        self.off = self.d.group_methods(self.group, RULE_OFF)

    def test_each_setting_shows_one_family(self):
        self.assertTrue(self.on)
        self.assertEqual(self.off, [pm + UNCAPPED for pm in self.on])
        self.assertEqual(sorted(self.on + self.off), sorted(self.d.group_methods(self.group, None)))

    def test_the_twins_differ_only_in_output_and_staff(self):
        for capped, old in zip(self.on, self.off):
            with self.subTest(method=capped):
                for key in ("texture", "unlocking_technologies", "required_input_goods"):
                    self.assertEqual(self.d.pms[capped].get(key), self.d.pms[old].get(key), key)
                self.assertEqual(self.d.goods(capped, "input"), self.d.goods(old, "input"))
                self.assertGreater(self.d.profit(capped), self.d.profit(old))

    def test_every_method_hides_when_unavailable(self):
        for pm in self.on + self.off:
            with self.subTest(method=pm):
                self.assertEqual(str(_unwrap(self.d.pms[pm].get("is_hidden_when_unavailable"))), "yes")


class ExtraplanetaryBaseLogistics(unittest.TestCase):
    """§ 1.2: two groups, one cut each, and the order flips only with both."""

    def setUp(self):
        self.d = _DATA

    def test_groups_sit_on_the_extraplanetary_base(self):
        groups = self.d.building_groups(SPACE)
        for group in LOGISTICS:
            with self.subTest(group=group):
                self.assertIn(group, groups)
                self.assertNotIn(group, self.d.building_groups(DEEP_SEA))

    def test_each_group_is_a_free_default_and_one_gated_cut(self):
        upgrades = self.d.logistics_upgrades()
        for group, tech in LOGISTICS.items():
            with self.subTest(group=group):
                methods = self.d.group_methods(group)
                self.assertEqual(len(methods), 2)
                upgrade = upgrades[group]
                self.assertIsNotNone(upgrade)
                default = next(pm for pm in methods if pm != upgrade)
                default_body = self.d.pms[default]
                self.assertEqual(str(_unwrap(default_body.get("is_default"))), "yes")
                self.assertEqual(sorted(default_body), ["is_default", "texture"])

                body = self.d.pms[upgrade]
                self.assertEqual([str(t) for t in _list(body.get("unlocking_technologies"))], [tech])
                self.assertEqual(sorted(body), ["building_modifiers", "texture", "unlocking_technologies"])
                modifiers = _block(body, "building_modifiers")
                self.assertEqual(list(modifiers), ["unscaled"])  # a building's own mult: unscaled
                self.assertEqual({k: float(_unwrap(v)) for k, v in _block(modifiers, "unscaled").items()},
                                 {LOGISTICS_MODIFIER: LOGISTICS_CUT})

    def test_upgrade_textures_are_tracked_mod_icons(self):
        for group in LOGISTICS:
            for pm in self.d.group_methods(group):
                texture = str(_unwrap(self.d.pms[pm].get("texture"))).strip('"')
                with self.subTest(method=pm):
                    _assert_tracked_texture(self, texture)

    def test_modifier_is_registered_as_a_percentage(self):
        definition = self.d.modifier_types.get(LOGISTICS_MODIFIER)
        self.assertIsInstance(definition, dict, f"{LOGISTICS_MODIFIER} is not registered")
        self.assertEqual(str(_unwrap(definition.get("percent"))), "yes")

    def test_both_upgrades_flip_the_order_only_with_space_colonization(self):
        upgrades = list(self.d.logistics_upgrades().values())
        deep = self.d.group_methods(self.d.base_group(DEEP_SEA))
        space = self.d.group_methods(self.d.base_group(SPACE))
        best_deep = max(max(self.d.deep_profits(pm).values()) for pm in deep)
        for pm in space:
            era = self.d.method_era(pm, SPACE)
            if era < min(self.d.method_era(d, DEEP_SEA) for d in deep):
                continue  # Regolith Processing (era 10): no Deep-Sea Mine yet
            with self.subTest(extraplanetary=pm, era=era):
                if era >= 12:
                    # Space Colonization's methods: ahead of every Deep-Sea method with both.
                    self.assertGreater(self.d.profit(pm, upgrades), best_deep)
                else:
                    # The Asteroid Mine stays behind the Deep-Sea Mine of its era even with both.
                    same_era = [d for d in deep if self.d.method_era(d, DEEP_SEA) <= era]
                    self.assertLess(self.d.profit(pm, upgrades),
                                    max(min(self.d.deep_profits(d).values()) for d in same_era))

    def test_each_upgrade_only_cuts_launch_capacity(self):
        space = self.d.group_methods(self.d.base_group(SPACE))
        for upgrade in self.d.logistics_upgrades().values():
            for pm in space:
                launch = self.d.goods(pm, "input").get("launch_capacity", 0.0)
                with self.subTest(upgrade=upgrade, method=pm):
                    self.assertGreater(launch, 0.0)
                    saving = self.d.profit(pm, [upgrade]) - self.d.profit(pm)
                    self.assertAlmostEqual(saving, -LOGISTICS_CUT * launch * self.d.prices["launch_capacity"])


class DeepSeaMineSupportVessels(unittest.TestCase):
    """The Deep-Sea Mine's ships: Motor Ship Tenders, then Magnetic Drive Tenders once the
    technology that makes those ships arrives, for every extraction method."""

    def setUp(self):
        self.d = _DATA
        self.methods = self.d.group_methods(VESSELS)
        self.default, self.upgrade = sorted(
            self.methods, key=lambda pm: bool(_list(self.d.pms[pm].get("unlocking_technologies"))))

    def ships(self, pm):
        return {good for good in self.d.goods(pm, "input") if good in SHIP_GOODS}

    def test_group_sits_on_the_deep_sea_mine_after_its_base_group(self):
        self.assertEqual(self.d.building_groups(DEEP_SEA)[1], VESSELS)
        self.assertNotIn(VESSELS, self.d.building_groups(SPACE))

    def test_extraction_methods_carry_no_ships(self):
        for pm in self.d.group_methods(self.d.base_group(DEEP_SEA), None):
            with self.subTest(method=pm):
                self.assertEqual(self.ships(pm), set())

    def test_a_free_default_and_one_gated_upgrade_each_on_one_ship(self):
        self.assertEqual(len(self.methods), 2)
        self.assertEqual(str(_unwrap(self.d.pms[self.default].get("is_default"))), "yes")
        self.assertEqual(_list(self.d.pms[self.default].get("unlocking_technologies")), [])
        self.assertEqual(len(_list(self.d.pms[self.upgrade].get("unlocking_technologies"))), 1)
        for pm in self.methods:
            with self.subTest(method=pm):
                # Only ships: no output, staff or other modifier, so the profit comparisons
                # above count all the group adds.
                self.assertEqual(list(_block(self.d.pms[pm], "building_modifiers")), ["workforce_scaled"])
                self.assertEqual(set(self.d.goods(pm, "input")), self.ships(pm))
                self.assertEqual(len(self.ships(pm)), 1)
                self.assertEqual(self.d.goods(pm, "output"), {})
        self.assertEqual(self.ships(self.default), {"motor_ships"})
        self.assertEqual(self.ships(self.upgrade), {"magnetic_drive_ships"})

    def test_upgrade_waits_for_the_technology_that_makes_its_ships(self):
        (good,) = self.ships(self.upgrade)
        supply = {str(t) for pm, body in self.d.pms.items() if isinstance(body, dict)
                  and self.d.goods(pm, "output").get(good, 0.0) > 0
                  for t in _list(body.get("unlocking_technologies"))}
        self.assertTrue(supply, f"no method makes {good}")
        (tech,) = _list(self.d.pms[self.upgrade].get("unlocking_technologies"))
        self.assertIn(str(tech), supply)

    def test_upgrade_costs_less_at_base_prices(self):
        self.assertLess(self.d.value(self.upgrade, "input"), self.d.value(self.default, "input"))

    def test_textures_are_tracked_mod_icons(self):
        for pm in self.methods:
            with self.subTest(method=pm):
                _assert_tracked_texture(self, str(_unwrap(self.d.pms[pm].get("texture"))).strip('"'))

    def test_ai_moves_up_to_the_upgrade_and_not_back(self):
        """Cost-only methods flip with prices under most_profitable (pmg_emissions_control's
        record), so the group takes most_productive and ai_value ranks the upgrade. What
        ai_value does is undocumented, so the ranking must hold whether it replaces (or
        multiplies) the method's score or adds to the base score, as
        test_emissions_control_ai_value.py requires of the emissions tiers."""
        self.assertEqual(str(_unwrap(self.d.groups[VESSELS].get("ai_selection"))), "most_productive")
        low, high = (float(_unwrap(self.d.pms[pm].get("ai_value"))) for pm in (self.default, self.upgrade))
        self.assertGreater(low, 0)
        stickiness = self.d.ai_define("PRODUCTION_METHOD_STICKINESS_DOWNGRADE")
        base = self.d.ai_define("PRODUCTION_METHOD_BASE_VALUE")
        for reading, (lo, hi) in {"replaces or multiplies": (low, high),
                                  "adds to the base": (base + low, base + high)}.items():
            with self.subTest(reading=reading):
                self.assertGreater(hi * stickiness, lo)
        # An input shortage must still be able to move a mine back to Motor Ship Tenders.
        self.assertLess(high / low, self.d.ai_define("PRODUCTION_METHOD_REDUCE_OUTPUT_PENALTY_FACTOR"))


def print_table():
    """Per-level figures; a Deep-Sea row is one method on one tender (method + tender)."""
    d = _Data()
    upgrades = list(d.logistics_upgrades().values())
    print(f"{'method':42} {'era':>3} {'staff':>6} {'input':>9} {'output':>9} "
          f"{'profit':>9} {'margin':>7} {'one cut':>9} {'both':>9}")
    for building in (DEEP_SEA, SPACE):
        for pm in d.group_methods(d.base_group(building)):
            for tender in d.tenders(pm) if building == DEEP_SEA else [None]:
                secondary = [tender] if tender else []
                inp = sum(d.value(m, "input") for m in (pm, *secondary))
                out, profit = d.value(pm, "output"), d.profit(pm, secondary)
                label = f"{pm} + {tender.split('_')[1]}" if tender else pm
                staff = d.employment(pm) if building == DEEP_SEA else d.crew(pm)  # a level / flat
                row = (f"{label:42} {d.method_era(pm, building):>3} {staff:>6.0f} "
                       f"{inp:>9,.0f} {out:>9,.0f} {profit:>9,.0f} {profit / inp:>7.0%}")
                if building == SPACE:
                    row += f" {d.profit(pm, upgrades[1:]):>9,.0f} {d.profit(pm, upgrades):>9,.0f}"
                print(row)


if __name__ == "__main__":
    if sys.argv[1:] == ["--table"]:
        print_table()
    else:
        unittest.main()
