"""Financial Districts and company headquarters hire their owners as a partnership (owner, 2026-11-28).

docs/superpowers/specs/2026-11-28-ownership-concentration-scope.md. Every ownership method that
hires capitalists or aristocrats as owners splits them into a fixed number a building (`unscaled`)
and a smaller part a level (`level_scaled`): 6 x and 0.4 x what the method hired a level before,
so a building breaks even with the old staff at level 10 and keeps 40% of it a level beyond. A
larger district or company then has fewer owners a level, and each holds more. The staff (clerks,
academics, clergy) and the categories' broad owners (shopkeepers, bureaucrats, academics) stay per
level, and so do the government-run and cooperative headquarters, which hold no private fortune.

The headquarters take their own automation tiers, one per company category, each gated to its
category and closed under Command Economy and Cooperative Ownership: the Financial District's tiers
have no such gate and stay in the District's group. A copy keeps its category's owners and
automates the back office, its clerks and academics at the District's tier ratios.

Dynastic Wealth's Scale of Fortunes term counts the property these buildings own per owner:
te_demog_is_fortune_building names the methods it leaves out, and te_demog_building_owned_levels
the top-level building groups it counts. Both lists are held here to the files.

Run: python3 -m pytest test_ownership_partnership.py -q
"""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

PARTNERS, PER_LEVEL = 6, 0.4            # x the old per-level owners: break-even at level 10
OWNERS = ("capitalists", "aristocrats")
FD_GROUP = "pmg_ownership_building_financial_district"
HQ_GROUP = "pmg_ownership_building_company_headquarter"
NOT_PRIVATE_LAWS = {"law_command_economy", "law_cooperative_ownership", "law_post-scarcity"}
FD_TIERS = {"pm_electronic_brokerage": ("transistors", 0.6), "pm_digital_trading": ("computer_networks", 0.4),
            "pm_automated_trading": ("digital_telecommunications", 0.2)}
CATEGORIES = {"": "capitalist_owned", "_aristocrats": "aristocrat_owned", "_shopkeepers": "shopkeeper_owned",
              "_bureaucrats": "bureaucrat_owned", "_academics": "academic_owned"}
DIVINE = {f"principle_divine_economics_{n}" for n in (2, 3, 4, 5)}
# Top-level building groups the owned-levels count leaves out, though private owners hold buildings there.
OWNED_LEVELS_EXCLUDED = {
    "bg_urban_facilities": "the ownership buildings themselves (and Art Academies)",
    "bg_monuments_hidden": "the wonders",
    "bg_sr_colony_sites": "the colony sites' marker buildings",
}


def _body(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _list(value):
    value = _body(value)
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def _blocks(modifiers, key):
    value = _body(modifiers.get(key)) if isinstance(modifiers, dict) else None
    if value is None:
        return []
    return [_body(v) for v in value] if isinstance(value, list) else [value]


class _Data:
    def __init__(self):
        import vanilla_parsed
        from mod_state import VANILLA_COMMON_DIRS, ModState

        types = ("Buildings", "Building Groups", "PM Groups", "PMs")
        snapshot = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed"))
        vanilla = {k: v for k, v in snapshot.data.items() if k in types}
        state = ModState({k: "" for k in types},
                         {k: os.path.join(REPO, "common", *VANILLA_COMMON_DIRS[k].split("/")) for k in types},
                         vanilla_data=vanilla)
        data = {k: {n: _body(v) for n, v in state.get_data(k).items()} for k in types}
        self.buildings, self.bgs = data["Buildings"], data["Building Groups"]
        self.groups, self.pms = data["PM Groups"], data["PMs"]

    def methods(self, group):
        return _list(self.groups[group].get("production_methods"))

    def hires(self, name, bucket):
        """{profession: positions} of one method's `bucket` block."""
        out = {}
        for block in _blocks(_body(self.pms[name].get("building_modifiers")) or {}, bucket):
            for key, value in block.items():
                m = re.fullmatch(r"building_employment_(\w+)_add", key)
                if m:
                    out[m.group(1)] = out.get(m.group(1), 0.0) + float(_body(value))
        return out

    def unscaled(self, name):
        blocks = _blocks(_body(self.pms[name].get("building_modifiers")) or {}, "unscaled")
        return {k: float(_body(v)) for b in blocks for k, v in b.items()}

    def laws(self, name, key):
        return set(_list(self.pms[name].get(key)))

    def not_private(self, name):
        return bool(self.laws(name, "unlocking_laws") & NOT_PRIVATE_LAWS)

    def private_methods(self):
        out = set()
        for group in (FD_GROUP, HQ_GROUP):
            out |= {m for m in self.methods(group) if not self.not_private(m)}
        return out


_DATA = None


def _data():
    global _DATA
    if _DATA is None:
        _DATA = _Data()
    return _DATA


def _text(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def _block(text, name):
    m = re.search(rf"^{re.escape(name)} = \{{", text, re.M)
    assert m, name
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class PartnershipTest(unittest.TestCase):
    def test_every_private_owner_is_a_partnership(self):
        data = _data()
        methods = data.private_methods()
        self.assertGreaterEqual(len(methods), 33)
        for name in sorted(methods):
            level, flat = data.hires(name, "level_scaled"), data.hires(name, "unscaled")
            with self.subTest(method=name):
                self.assertTrue(set(flat) <= set(OWNERS), f"only owners are hired once a building: {flat}")
                for pop in OWNERS:
                    if pop in level or pop in flat:
                        self.assertGreater(level.get(pop, 0), 0, pop)
                        self.assertAlmostEqual(flat.get(pop, 0), level[pop] * PARTNERS / PER_LEVEL, msg=pop)

    def test_the_capitalists_are_owners_everywhere_they_hold_shares(self):
        data = _data()
        for name in sorted(data.private_methods()):
            shares = data.unscaled(name)
            for pop in OWNERS:
                if shares.get(f"building_{pop}_shares_add"):
                    with self.subTest(method=name, pop=pop):
                        self.assertIn(pop, data.hires(name, "unscaled"))

    def test_the_district_keeps_its_old_figures_at_level_ten(self):
        data = _data()
        before = {"pm_financial_district_privately_owned": 50, "pm_financial_district_publicly_traded": 50,
                  "pm_financial_district_principle_divine_economics_2": 50, "pm_electronic_brokerage": 30,
                  "pm_digital_trading": 20, "pm_automated_trading": 10,
                  "pm_company_headquarter_privately_owned": 25}
        for name, old in before.items():
            with self.subTest(method=name):
                level, flat = data.hires(name, "level_scaled"), data.hires(name, "unscaled")
                self.assertEqual(flat["capitalists"] + 10 * level["capitalists"], 10 * old)

    def test_the_state_and_cooperative_headquarters_hire_by_the_level(self):
        data = _data()
        for name in data.methods(HQ_GROUP):
            if data.not_private(name):
                with self.subTest(method=name):
                    self.assertEqual(data.hires(name, "unscaled"), {})

    def test_the_manor_houses_are_unchanged(self):
        data = _data()
        for group in ("pmg_ownership_building_manor_house", "pmg_additional_ownership_building_manor_house"):
            for name in data.methods(group):
                with self.subTest(method=name):
                    self.assertEqual(data.hires(name, "unscaled"), {})


class HeadquartersTierTest(unittest.TestCase):
    def test_the_districts_tiers_left_the_headquarters(self):
        data = _data()
        hq = set(data.methods(HQ_GROUP))
        for tier in FD_TIERS:
            self.assertNotIn(tier, hq)
            self.assertIn(tier, data.methods(FD_GROUP))

    def test_one_copy_per_tier_and_category_gated_to_it(self):
        data = _data()
        hq = set(data.methods(HQ_GROUP))
        for tier, (tech, _ratio) in FD_TIERS.items():
            for suffix, category in CATEGORIES.items():
                name = f"pm_company_headquarter_{tier[3:]}{suffix}"
                with self.subTest(method=name):
                    self.assertIn(name, hq)
                    pm = data.pms[name]
                    self.assertEqual(_list(pm.get("unlocking_company_categories")), [category])
                    self.assertEqual(_list(pm.get("unlocking_technologies")), [tech])
                    self.assertTrue({"law_command_economy", "law_cooperative_ownership"}
                                    <= data.laws(name, "disallowing_laws"))
                    self.assertEqual(_body(pm.get("is_hidden_when_unavailable")), "yes")

    def test_a_copy_keeps_its_categorys_owners_and_automates_the_back_office(self):
        data = _data()
        base = {"": "pm_company_headquarter_privately_owned",
                "_aristocrats": "pm_company_headquarter_privately_owned_aristocrats",
                "_shopkeepers": "pm_company_headquarter_privately_owned_shopkeepers",
                "_bureaucrats": "pm_company_headquarter_privately_owned_bureaucrats",
                "_academics": "pm_company_headquarter_privately_owned_academics"}
        broad = {"_shopkeepers": "shopkeepers", "_bureaucrats": "bureaucrats", "_academics": "academics"}
        for tier, (_tech, ratio) in FD_TIERS.items():
            for suffix, base_name in base.items():
                name = f"pm_company_headquarter_{tier[3:]}{suffix}"
                with self.subTest(method=name):
                    self.assertEqual(data.hires(name, "unscaled"), data.hires(base_name, "unscaled"))
                    self.assertEqual(data.unscaled(name), data.unscaled(base_name), "shares and dividends")
                    level, base_level = data.hires(name, "level_scaled"), data.hires(base_name, "level_scaled")
                    kept = set(OWNERS) | ({broad[suffix]} if suffix in broad else set())
                    for pop, n in base_level.items():
                        expected = n if pop in kept else n * ratio
                        self.assertAlmostEqual(level.get(pop, 0), expected, msg=pop)

    def test_the_divine_economics_copies_agree(self):
        data = _data()
        copies = [m for m in data.methods(HQ_GROUP) if "principle_divine_economics_2" in m]
        self.assertEqual(len(copies), 6)
        for name in copies:
            with self.subTest(method=name):
                self.assertEqual(data.laws(name, "unlocking_principles"), DIVINE)
                self.assertEqual(len(_list(data.pms[name].get("unlocking_company_categories"))), 1)


class FortuneMeasureTest(unittest.TestCase):
    def test_the_excluded_methods_are_the_unprivate_ones(self):
        data = _data()
        expected = {m for g in (FD_GROUP, HQ_GROUP) for m in data.methods(g) if data.not_private(m)}
        body = _block(_text("common/scripted_triggers/te_demog_triggers.txt"), "te_demog_is_fortune_building")
        listed = set(re.findall(r"has_active_production_method = (\w+)", body))
        self.assertEqual(listed, expected)

    def test_the_owned_levels_count_every_top_level_group_private_owners_hold(self):
        data = _data()
        parent = {n: _body(g.get("parent_group")) if isinstance(g, dict) else None for n, g in data.bgs.items()}

        def chain(group):
            seen = []
            while group and group not in seen:
                seen.append(group)
                group = parent.get(group)
            return seen

        def funded(group):
            return any(isinstance(data.bgs.get(g), dict) and _body(data.bgs[g].get("is_government_funded")) == "yes"
                       for g in chain(group))

        roots = set()
        for building in data.buildings.values():
            group = _body(building.get("building_group")) if isinstance(building, dict) else None
            if group and not funded(group):
                roots.add(chain(group)[-1])
        body = _block(_text("common/script_values/te_demog_values.txt"), "te_demog_building_owned_levels")
        counted = set(re.findall(r'"num_building_assets_of_group\((\w+)\)"', body))
        self.assertEqual(counted, roots - set(OWNED_LEVELS_EXCLUDED))
        self.assertTrue(set(OWNED_LEVELS_EXCLUDED) <= roots, "an exclusion names a group that no longer exists")


if __name__ == "__main__":
    unittest.main()
