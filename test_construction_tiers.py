"""The Construction Sector's tiers and their Construction Site twins
(docs/systems/mod_systems/construction.md, "Construction as a Market Good" and
"Free Market Construction off").

Each tier of `pmg_base_building_construction_sector` has a twin in
`pmg_base_te_construction_market_site`, in the same order, that turns the same goods and
staff into the tier's construction as points (te_construction_market_pms.txt's header:
"When a sector tier changes, change its twin too"). A new tier lands in six places: the
sector's group, the twin and the site's group, the market settings that disable the twin,
the automation and principle methods that name tiers, and the direct-construction tier
helpers. Self-Replicating Construction (Von Neumann Machines, era 13 spec § 7.10) was the
first added after these tests; each test names the place a later one misses.
"""
import glob
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))

SECTOR_GROUP = "pmg_base_building_construction_sector"
SITE_GROUP = "pmg_base_te_construction_market_site"
MARKET_PM = "pm_te_construction_market_base"
TIER_LISTS = ("pmg_construction_automation", "pmg_construction_principle")
RULE = "free_market_construction_rule"
DIRECT_SETTING = "free_market_construction_disabled"
DIRECT_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_construction_market_direct_effects.txt")
OUTPUT = "goods_output_construction_add"


def _unwrap(value):
    while isinstance(value, tuple) and len(value) == 2:
        value = value[1]
    return value


def _list(value):
    value = _unwrap(value)
    if value is None:
        return []
    return [str(_unwrap(v)) for v in value] if isinstance(value, list) else [str(value)]


def _block(body, *path):
    for key in path:
        body = _unwrap(body.get(key)) if isinstance(body, dict) else None
    return body if isinstance(body, dict) else {}


def _numbers(block):
    return {key: float(_unwrap(v)) for key, v in block.items()}


def _parse(*parts):
    parser = ParadoxFileParser()
    for path in sorted(glob.glob(os.path.join(REPO, *parts, "*.txt"))):
        parser.parse_file(path)
    return {key: _unwrap(value) for key, value in parser.data.items()}


class ConstructionTiers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pms = _parse("common", "production_methods")
        cls.groups = _parse("common", "production_method_groups")
        cls.rules = _parse("common", "game_rules")
        cls.tiers = _list(cls.groups[SECTOR_GROUP].get("production_methods"))
        site = _list(cls.groups[SITE_GROUP].get("production_methods"))
        cls.twins = [pm for pm in site if pm != MARKET_PM]
        with open(DIRECT_EFFECTS, encoding="utf-8-sig") as f:
            cls.direct_effects = re.sub(r"#[^\n]*", "", f.read())

    def output(self, tier):
        return float(_unwrap(_block(self.pms[tier], "building_modifiers", "workforce_scaled")[OUTPUT]))

    def test_the_site_lists_the_market_method_then_one_twin_per_tier(self):
        site = _list(self.groups[SITE_GROUP].get("production_methods"))
        self.assertEqual(site[0], MARKET_PM)
        self.assertEqual(len(self.twins), len(self.tiers))
        for twin in self.twins:
            with self.subTest(twin=twin):
                self.assertTrue(twin.startswith("pm_te_direct_construction_"))
                self.assertEqual(str(_unwrap(self.pms[twin].get("is_hidden_when_unavailable"))), "yes")

    def test_each_twin_copies_its_tier(self):
        for tier, twin in zip(self.tiers, self.twins):
            with self.subTest(tier=tier, twin=twin):
                a, b = self.pms[tier], self.pms[twin]
                self.assertEqual(_list(a.get("unlocking_technologies")), _list(b.get("unlocking_technologies")))
                self.assertEqual(_list(a.get("required_input_goods")), _list(b.get("required_input_goods")))
                self.assertEqual(_numbers(_block(a, "state_modifiers", "unscaled")),
                                 _numbers(_block(b, "state_modifiers", "unscaled")))
                goods = _numbers(_block(a, "building_modifiers", "workforce_scaled"))
                points = goods.pop(OUTPUT)
                self.assertEqual(goods, _numbers(_block(b, "building_modifiers", "workforce_scaled")))
                self.assertEqual({"country_construction_add": points},
                                 _numbers(_block(b, "country_modifiers", "workforce_scaled")))
                for bucket in ("level_scaled", "unscaled"):
                    self.assertEqual(_numbers(_block(a, "building_modifiers", bucket)),
                                     _numbers(_block(b, "building_modifiers", bucket)), bucket)

    def test_the_ladder_rises(self):
        outputs = [self.output(tier) for tier in self.tiers]
        self.assertEqual(outputs, sorted(set(outputs)), dict(zip(self.tiers, outputs)))

    def test_every_market_setting_disables_every_twin(self):
        rule = self.rules[RULE]
        settings = [key for key, body in rule.items() if isinstance(_unwrap(body), dict)]
        self.assertIn(DIRECT_SETTING, settings)
        for setting in settings:
            flags = set(_list(_block(rule, setting).get("flag")))
            with self.subTest(setting=setting):
                if setting == DIRECT_SETTING:
                    self.assertIn("disable_" + MARKET_PM, flags)
                    self.assertFalse({"disable_" + twin for twin in self.twins} & flags)
                else:
                    self.assertEqual({"disable_" + twin for twin in self.twins} - flags, set())

    def test_tier_lists_name_a_tier_with_its_twin_and_every_later_tier(self):
        """A method that names a tier in unlocking_production_methods names its twin, and
        every later tier: staff falls up the ladder, so a cut that fits one tier fits the
        next (pm_employment_audit checks the fit itself). A method split by tier, so a
        flat crew's cut is exact on the later tiers (3D Printed Buildings, #1684), stops
        where its copy starts: both hide when unavailable and the copy runs to the top."""
        checked = 0
        for group in TIER_LISTS:
            methods = _list(self.groups[group].get("production_methods"))
            named_by = {}
            for pm in methods:
                names = set(_list(self.pms[pm].get("unlocking_production_methods")))
                named_by[pm] = [i for i, tier in enumerate(self.tiers) if tier in names]
            for pm in methods:
                names = set(_list(self.pms[pm].get("unlocking_production_methods")))
                if not names:
                    continue
                checked += 1
                with self.subTest(group=group, method=pm):
                    named = named_by[pm]
                    self.assertTrue(named)
                    self.assertEqual(named, list(range(named[0], named[-1] + 1)))
                    if named[-1] != len(self.tiers) - 1:
                        copies = [other for other in methods
                                  if named_by[other] and named_by[other][0] == named[-1] + 1]
                        self.assertEqual(len(copies), 1, "no copy takes the later tiers")
                        self.assertEqual(named_by[copies[0]][-1], len(self.tiers) - 1)
                        for name in (pm, copies[0]):
                            self.assertEqual(_unwrap(self.pms[name].get("is_hidden_when_unavailable")), "yes", name)
                    self.assertEqual({self.twins[i] for i in named},
                                     {twin for twin in self.twins if twin in names})
                    self.assertNotIn(MARKET_PM, names)
        self.assertGreaterEqual(checked, 5)

    def test_the_direct_tier_helpers_know_every_tier(self):
        """te_dc_target_tier numbers the twins from 1 in the site group's order. The conversion to
        direct construction reads the sector's tier, or the site's where a site is the capacity
        (te_direct_construction_convert_state), and sets the new site's; the conversion back reads the
        site's and sets the sector's (te_direct_construction_revert_state_site); the site guard records
        and restores the site's."""
        text = self.direct_effects

        def count(pattern):
            return len(re.findall(pattern, text))

        for i, (tier, twin) in enumerate(zip(self.tiers, self.twins), start=1):
            with self.subTest(tier=i):
                self.assertEqual(count(rf"te_direct_construction_activate_site_tier = \{{ TIER = {i} PM = {twin} \}}"), 2)
                self.assertEqual(count(rf"te_direct_construction_activate_sector_tier = \{{ TIER = {i} PM = {tier} \}}"), 1)
                if i > 1:  # tier 1 is the starting value, not read
                    self.assertEqual(count(rf"BUILDING = building_construction_sector TIER = {i} PM = {tier} \}}"), 1)
                    self.assertEqual(count(rf"BUILDING = te_construction_market_site TIER = {i} PM = {twin} \}}"), 3)
        # Two site activations and one sector activation a tier; one sector read and three site reads a tier above 1.
        self.assertEqual(count(r"TIER = \d+ PM ="), 7 * len(self.tiers) - 4)


def _value(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _names(value):
    value = _value(value)
    if value is None:
        return []
    if isinstance(value, dict):
        return list(value)
    if isinstance(value, (list, tuple)):
        return [str(_value(v)) for v in value]
    return [str(value)]


class TierInputsExistByTheirEra(unittest.TestCase):
    """No Construction Sector tier, automation method or Construction Site twin takes a
    good that only a later era can make. Advanced Construction (prefabricated_construction,
    era 7) took 20 Software until 2026-11-03, and nothing makes Software before the Software
    Industry (computer_networks, era 8).

    A good's era is the earliest era a regular building makes it in: the latest era among
    the technologies its method and its building need. Company buildings, buildings with a
    `potential` (wonders built from their own construction site, such as the Mind Upload
    Nexus) and law-gated methods don't count. A same-era producer passes, since a tier can't
    know which of its era's other technologies come first."""

    GROUPS = (
        (SECTOR_GROUP, "building_construction_sector"),
        ("pmg_construction_automation", "building_construction_sector"),
        (SITE_GROUP, "te_construction_market_site"),
    )
    COMPANY_GROUP = "bg_company_buildings"

    @classmethod
    def setUpClass(cls):
        import vanilla_parsed
        from mod_state import ModState

        types = {"Buildings": "buildings", "PM Groups": "production_method_groups",
                 "PMs": "production_methods", "Technologies": "technology/technologies"}
        snapshot = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed"))
        vanilla = {k: v for k, v in snapshot.data.items() if k in types}
        state = ModState({k: "" for k in types}, {k: os.path.join(REPO, "common", d) for k, d in types.items()},
                         vanilla_data=vanilla)
        cls.buildings, cls.groups, cls.pms, cls.techs = (
            {name: _value(body) for name, body in state.get_data(k).items()} for k in types)
        buildings_of = {}
        for building, body in cls.buildings.items():
            for group in _names(body.get("production_method_groups")):
                for pm in _names(cls.groups.get(group, {}).get("production_methods")):
                    buildings_of.setdefault(pm, set()).add(building)
        cls.first_era = {}
        for pm, body in cls.pms.items():
            if not isinstance(body, dict) or body.get("unlocking_laws"):
                continue
            for building in buildings_of.get(pm, ()):
                b = cls.buildings[building]
                if _value(b.get("building_group")) == cls.COMPANY_GROUP or "potential" in b:
                    continue
                era = cls.gate_era(pm, building)
                for good in cls.goods(pm, "output"):
                    cls.first_era[good] = min(era, cls.first_era.get(good, era))

    @classmethod
    def era_of(cls, tech):
        return int(str(_value(cls.techs[tech].get("era"))).rsplit("_", 1)[1])

    @classmethod
    def gate_era(cls, pm, building):
        techs = _names(cls.pms[pm].get("unlocking_technologies"))
        techs += _names(cls.buildings[building].get("unlocking_technologies"))
        return max((cls.era_of(t) for t in techs), default=1)

    @classmethod
    def goods(cls, pm, kind):
        pattern = re.compile(rf"goods_{kind}_(\w+)_add")
        found = set()
        for block in (_value(cls.pms[pm].get("building_modifiers")) or {}).values():
            for key in _value(block) or {}:
                match = pattern.fullmatch(key)
                if match:
                    found.add(match.group(1))
        return found

    def test_no_tier_takes_a_good_only_a_later_era_makes(self):
        checked = 0
        for group, building in self.GROUPS:
            for pm in _names(self.groups[group].get("production_methods")):
                era = self.gate_era(pm, building)
                for good in sorted(self.goods(pm, "input")):
                    checked += 1
                    with self.subTest(method=pm, good=good):
                        self.assertIn(good, self.first_era, f"no regular building makes {good}")
                        self.assertLessEqual(self.first_era[good], era,
                                             f"{pm} unlocks in era {era}, but {good} is first made in era "
                                             f"{self.first_era[good]}")
        self.assertGreater(checked, 50)

    def test_software_first_comes_with_the_software_industry(self):
        """Guards the producer index: company headquarters and the Mind Upload Nexus make
        Software with no technology, so counting them would pass every tier."""
        self.assertEqual(self.first_era["digital_assets"], self.era_of("computer_networks"))


if __name__ == "__main__":
    unittest.main()
