"""The Extraplanetary Base's ground types, its shared basket and the month's rules
(docs/superpowers/specs/2026-11-05-extraplanetary-base-ground-types-design.md).

``scripts/generators/ebase_ground.py`` is the reference the generated script must
match: each site's type, each type's mix (§ 6), the basket of the four mining
methods (§ 7), and the month (§ 8.2 to § 8.5) as a Python model.
"""
import os
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import ebase_ground as eg  # noqa: E402
import gen_solar_sites as gss  # noqa: E402

# § 6.2's table, the figures the loc states: each type's mix, rounded to the whole
# percent, in the goods' order (iron, tech_metals, gold, copper, lead, sulfur, glass).
ROUNDED_MIX = {
    "mixed": (0, 0, 0, 0, 0, 0, 0),
    "metallic": (12, 2, 30, 12, -7, -72, -91),
    "rocky": (26, -3, -51, -17, -17, 7, 36),
    "carbonaceous": (-17, -7, -33, -7, -7, 107, 117),
    "sulfurous": (-16, -11, -37, 5, 5, 320, 26),
    "hydrocarbon": (-25, -15, -50, -20, -20, 80, 249),
    "icy": (0, -5, -40, -10, -10, 61, 81),
}


class GroundTypes(unittest.TestCase):
    """§ 6: a site is its type and its grade, and every type's mix averages to zero
    over the basket, so the grade alone carries how much a site yields."""

    def test_every_place_has_a_type(self):
        self.assertEqual(set(eg.GROUND), {"near_earth"} | {s.key for s in gss.SITES})
        for place, type_ in eg.GROUND.items():
            with self.subTest(place=place):
                self.assertIn(type_, eg.TYPES)

    def test_places_are_near_earth_then_the_sites_in_index_order(self):
        self.assertEqual(eg.PLACES[0], "near_earth")
        self.assertEqual(eg.PLACES[1:], tuple(s.key for s in sorted(gss.SITES, key=lambda s: s.index)))

    def test_each_mix_averages_to_zero(self):
        shares = eg.shares(eg.BASKET)
        for t in eg.TYPES:
            with self.subTest(type=t):
                self.assertLess(abs(sum(shares[g] * eg.mix(t)[g] for g in eg.GOODS)), 1e-12)

    def test_every_derived_grade_is_the_site_s(self):
        shares = eg.shares(eg.BASKET)
        for p in eg.PLACES:
            with self.subTest(place=p):
                derived = sum(shares[g] * eg.score(p, g) for g in eg.GOODS)
                self.assertAlmostEqual(derived, eg.grade(p), delta=1e-12)

    def test_grades_are_the_sites_ebase_grades(self):
        self.assertEqual(eg.grade("near_earth"), 0)
        for s in gss.SITES:
            with self.subTest(site=s.key):
                self.assertAlmostEqual(eg.grade(s.key), s.ebase_grade / 100, delta=1e-12)

    def test_rounded_mixes_match_the_spec(self):
        self.assertEqual(set(ROUNDED_MIX), set(eg.TYPES))
        for t, figures in ROUNDED_MIX.items():
            for g, figure in zip(eg.GOODS, figures):
                with self.subTest(type=t, good=g):
                    self.assertEqual(round(100 * eg.mix(t)[g]), figure)

    def test_base_prices_match_the_goods_files(self):
        import pm_costs  # prices exactly as test_deep_sea_rebalance._Data reads them

        prices = pm_costs.load_goods()
        self.assertEqual(eg.BASE_PRICE, {g: prices[g] for g in eg.GOODS})
        for g in eg.GOODS:
            with self.subTest(good=g):
                self.assertEqual(eg.good_base_price(g), prices[g])

    def test_mixed_is_the_basket(self):
        self.assertEqual(eg.mix("mixed"), {g: 0.0 for g in eg.GOODS})


class Basket(unittest.TestCase):
    """§ 7: the four mining methods share one basket, the same seven goods in the same
    shares of output value at base prices, so a site's mix means the same under each
    and cancels at base prices for every one."""

    MINING = ("pm_regolith_processing", "pm_space_mine", "pm_space_colony_mining", "pm_self_replicating_miners")

    def setUp(self):
        self.methods = eg.base_methods()
        self.mining = eg.mining_methods()

    def test_mining_methods_are_those_within_the_seven_goods(self):
        self.assertEqual(list(self.mining), [pm for pm, m in self.methods.items()
                                             if set(m.outputs) <= set(eg.GOODS)])

    def test_method_goods_are_the_seven_and_the_mining_inputs(self):
        goods = eg.method_goods()
        self.assertEqual(goods[:len(eg.GOODS)], eg.GOODS)
        inputs = {g for m in self.mining.values() for g in m.inputs}
        self.assertEqual(set(goods), set(eg.GOODS) | inputs)
        for g in goods:
            with self.subTest(good=g):
                self.assertGreater(eg.good_base_price(g), 0)

    @staticmethod
    def _value(goods):
        return sum(qty * eg.good_base_price(g) for g, qty in goods.items())

    def test_reads_every_method_of_the_base_group(self):
        for pm in self.MINING:
            with self.subTest(pm=pm):
                self.assertIn(pm, self.mining)
        for pm, m in self.methods.items():
            with self.subTest(pm=pm):
                self.assertTrue(m.outputs)
                self.assertIn("launch_capacity", m.inputs)

    def test_asteroid_mine_is_the_basket(self):
        self.assertEqual(self.methods["pm_space_mine"].outputs, eg.BASKET)

    def test_mining_methods_share_the_basket(self):
        basket = eg.shares(eg.BASKET)
        for pm, m in self.mining.items():
            shares = eg.shares(m.outputs)
            self.assertEqual(set(shares), set(eg.GOODS), pm)
            for g in eg.GOODS:
                with self.subTest(pm=pm, good=g):
                    self.assertAlmostEqual(shares[g], basket[g], delta=0.0001)

    def test_every_type_earns_base_profit_at_base_prices(self):
        for pm, m in self.mining.items():
            base = self._value(m.outputs) - self._value(m.inputs)
            for t in eg.TYPES:
                with self.subTest(pm=pm, type=t):
                    typed = sum(qty * eg.good_base_price(g) * (1 + eg.mix(t)[g])
                                for g, qty in m.outputs.items()) - self._value(m.inputs)
                    self.assertLessEqual(abs(typed - base), 0.001 * abs(base))

    def test_regolith_output_value_is_unchanged(self):
        self.assertAlmostEqual(self._value(self.methods["pm_regolith_processing"].outputs), 16600, delta=0.005)

    def test_regolith_every_type_within_fifty_pence(self):
        """§ 7: with two decimals every type earns £1,600 a level at grade 0 and base
        prices to within £0.50."""
        m = self.methods["pm_regolith_processing"]
        for t in eg.TYPES:
            with self.subTest(type=t):
                typed = sum(qty * eg.good_base_price(g) * (1 + eg.mix(t)[g])
                            for g, qty in m.outputs.items()) - self._value(m.inputs)
                self.assertAlmostEqual(typed, 1600, delta=0.5)


def _parse_dir(*parts):
    from paradox_file_parser import ParadoxFileParser

    parser = ParadoxFileParser()
    folder = os.path.join(REPO, *parts)
    for name in sorted(os.listdir(folder)):
        if name.endswith(".txt"):
            parser.parse_file(os.path.join(folder, name))
    return {key: eg._unwrap(value) for key, value in parser.data.items()}


def _english_loc():
    import re

    line = re.compile(r'^\s+([\w.]+):\d*\s*"(.*)"\s*(#.*)?$')
    folder = os.path.join(REPO, "localization", "english")
    loc = {}
    for name in sorted(os.listdir(folder)):
        if name.endswith(".yml"):
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                for text in f:
                    m = line.match(text)
                    if m:
                        loc[m.group(1)] = m.group(2)
    return loc


class Modifiers(unittest.TestCase):
    """§ 5.3 and § 9.5: fourteen unit modifiers, a bonus and a penalty for each good of
    the basket, which the refresh adds to every Extraplanetary Base building scaled by
    the base's mix."""

    def test_fourteen_unit_modifiers(self):
        statics = _parse_dir("common", "static_modifiers")
        for g in eg.GOODS:
            for kind, value in (("bonus", 0.01), ("penalty", -0.01)):
                name = f"sr_ebase_mix_{g}_{kind}"
                with self.subTest(modifier=name):
                    block = statics[name]
                    lines = {k: float(eg._unwrap(v)) for k, v in block.items() if k != "icon"}
                    self.assertEqual(lines, {f"goods_output_{g}_mult": value})
                    self.assertTrue(str(eg._unwrap(block["icon"])).startswith(
                        "gfx/interface/icons/timed_modifier_icons/modifier_gear_"))

    def test_every_good_has_its_output_mult_display_entry(self):
        types = _parse_dir("common", "modifier_type_definitions")
        loc = _english_loc()
        glass = types["goods_output_glass_mult"]
        for g in eg.GOODS:
            with self.subTest(good=g):
                entry = types[f"goods_output_{g}_mult"]
                for field in ("color", "percent"):
                    self.assertEqual(eg._unwrap(entry[field]), eg._unwrap(glass[field]))
                self.assertIn(f"${g}$", loc[f"goods_output_{g}_mult"])
        self.assertEqual(eg._unwrap(types["goods_output_lead_mult"]["color"]), "good")
        self.assertEqual(eg._unwrap(types["goods_output_lead_mult"]["percent"]), "yes")

    def test_names_and_descriptions(self):
        loc = _english_loc()
        for g in eg.GOODS:
            for kind in ("bonus", "penalty"):
                name = f"sr_ebase_mix_{g}_{kind}"
                with self.subTest(modifier=name):
                    self.assertEqual(loc.get(name), "Extraplanetary Base Ground")
                    desc = loc.get(f"{name}_desc", "")
                    self.assertIn(f"${g}$", desc)
                    # On top of Extraplanetary Base Room, which carries the grade (§ 9.5).
                    self.assertIn("on top of $sr_ebase_room_bonus$, which carries the sites' grade", desc)
        self.assertEqual(loc["sr_ebase_room_bonus"], "Extraplanetary Base Room")



ASTEROID = {"pm_space_mine": 1.0}
TWO_SITES = {"psyche": 300, "ceres": 200}
BOTH = {"psyche": True, "ceres": True}
# § 9.1's sketch: Glass and Plastics 50% dear, so Ceres (Carbonaceous +15%) earns
# £11,835 a level and 16 Psyche (Metallic +30%) £9,594; the yardstick is £7,250.
SKETCH = {"psyche": 9594, "ceres": 11835}
YARD = 7250


def _state(at, **kw):
    return eg.BaseState(at=dict(at), placed=True, **kw)


def _moved(state):
    return sum(n for _, _, n in state.moves)


class Month(unittest.TestCase):
    """§ 8.2 to § 8.5: the month's steps, the checkbox, the pace, displacement and
    return. The model is the reference the generated script follows."""

    def test_the_sketch_s_figures_come_from_the_formula(self):
        prices = {"glass": 0.5}
        self.assertEqual(round(eg.profit_a_level("ceres", ASTEROID, prices)), SKETCH["ceres"])
        self.assertEqual(round(eg.profit_a_level("psyche", ASTEROID, prices)), SKETCH["psyche"])
        self.assertEqual(round(eg.profit_a_level("near_earth", ASTEROID, prices)), 8650)
        self.assertAlmostEqual(eg.yardstick(ASTEROID), YARD, delta=1e-6)

    def test_section_6_4_s_table(self):
        """§ 6.4: the best of six sites under one price move at a time, and its profit."""
        six = ("psyche", "vesta", "ceres", "io", "titan", "ganymede")
        rows = (({}, "psyche", 9425), ({"iron": 0.5}, "psyche", 16686), ({"tech_metals": 0.5}, "psyche", 18743),
                ({"tech_metals": -0.3}, "ceres", 3841), ({"gold": 0.5}, "psyche", 13661),
                ({"sulfur": 0.75}, "io", 10630), ({"glass": 0.5}, "ceres", 11835), ({"glass": -0.5}, "psyche", 9256))
        for prices, best, figure in rows:
            with self.subTest(prices=prices):
                profit = {p: eg.profit_a_level(p, ASTEROID, prices) for p in six}
                self.assertEqual(max(six, key=profit.get), best)
                self.assertEqual(round(profit[best]), figure)

    def test_the_logistics_cuts_are_read_from_the_building(self):
        """F1 of the Tasks 5 and 6 review: the base building's other method groups' input
        cuts, read from the files (era 12's two Launch Capacity cuts, -30% each)."""
        cuts = eg.input_cuts()
        self.assertEqual(cuts, {"pm_tethered_launch_building_space_mine": {"launch_capacity": -0.3},
                                "pm_fusion_tugs_building_space_mine": {"launch_capacity": -0.3}})
        self.assertEqual(eg.cut_goods(), ("launch_capacity",))
        self.assertAlmostEqual(eg.input_factor(cuts)["launch_capacity"], 0.4)
        self.assertEqual(eg.input_factor(()), {"launch_capacity": 1.0})
        # Each method's factor is its levels' average; a method outside the seven isn't counted.
        both = tuple(cuts)
        got = eg.method_cuts([("pm_space_mine", 30, both), ("pm_space_mine", 10, ()),
                              ("pm_space_colony_vacation", 5, both)])
        self.assertEqual(set(got), {"pm_space_mine"})
        self.assertAlmostEqual(got["pm_space_mine"]["launch_capacity"], (30 * 0.4 + 10) / 40)

    def test_the_cuts_lower_the_input_bill(self):
        """The cut multiplies the input's term: with both cuts an Asteroid Mine level's
        Launch Capacity bill is 40%, and the yardstick £21,650 (the coordinator's decision:
        it counts the cuts), so a move must gain about £1,083 a level."""
        both = eg.method_cuts([("pm_space_mine", 1, tuple(eg.input_cuts()))])
        self.assertAlmostEqual(eg.yardstick(ASTEROID, both), 21650, delta=1e-6)
        self.assertAlmostEqual(eg.MARGIN * eg.yardstick(ASTEROID, both), 1082.5, delta=1e-6)
        lc = -eg.base_methods()["pm_space_mine"].inputs["launch_capacity"] * eg.good_base_price("launch_capacity")
        for t in eg.TYPES:
            for rel in ({}, {"launch_capacity": 0.5, "glass": -0.2}):
                with self.subTest(type=t, rel=rel):
                    self.assertAlmostEqual(eg.margin(t, ASTEROID, rel, both),
                                           eg.margin(t, ASTEROID, rel) - 0.6 * lc * (1 + rel.get("launch_capacity", 0)),
                                           delta=1e-6)

    def test_the_cuts_change_the_best_site(self):
        """The review's scenario: Asteroid Mines with both cuts and Chemical and Industrial
        Minerals 75% dear. Uncut, Io looks best; with the cuts counted, 16 Psyche is."""
        six = ("psyche", "vesta", "ceres", "io", "titan", "ganymede")
        both = eg.method_cuts([("pm_space_mine", 1, tuple(eg.input_cuts()))])
        for cuts, best in ((None, "io"), (both, "psyche")):
            with self.subTest(cuts=bool(cuts)):
                profit = {p: eg.profit_a_level(p, ASTEROID, {"sulfur": 0.75}, cuts) for p in six}
                self.assertEqual(max(six, key=profit.get), best)

    def test_every_type_s_margin_at_base_prices_is_the_yardstick(self):
        shares = {pm: 1 / len(eg.mining_methods()) for pm in eg.mining_methods()}
        for t in eg.TYPES:
            with self.subTest(type=t):
                self.assertAlmostEqual(eg.margin(t, shares, {}), eg.yardstick(shares), delta=0.5)

    def test_pace_is_a_quarter_of_the_base_a_year(self):
        self.assertEqual([eg.pace(n) for n in (0, 1, 48, 49, 150, 1000)], [1, 1, 1, 2, 4, 21])

    def test_first_month_places_everything_at_once(self):
        s = eg.month(eg.BaseState(), room=TWO_SITES, serves=BOTH, built=150,
                     profit=eg.profits(ASTEROID, {}), yard=YARD)
        self.assertEqual(s.at, {"psyche": 150})
        self.assertTrue(s.placed)
        self.assertEqual(s.moves, ())

    def test_checkbox_moves_at_the_pace(self):
        s = eg.month(_state({"psyche": 150}), room=TWO_SITES, serves=BOTH, built=150, profit=SKETCH, yard=YARD)
        self.assertEqual(s.at, {"psyche": 146, "ceres": 4})
        self.assertEqual(s.moves, (("psyche", "ceres", 4),))

    def test_checkbox_stops_inside_the_margin(self):
        edge = eg.MARGIN * YARD  # £362.50: a gap of at least this moves
        for gap, moves in ((edge - 0.5, 0), (edge, 4)):
            with self.subTest(gap=gap):
                profit = {"psyche": 9594, "ceres": 9594 + gap}
                s = eg.month(_state({"psyche": 150}), room=TWO_SITES, serves=BOTH, built=150,
                             profit=profit, yard=YARD)
                self.assertEqual(_moved(s), moves)

    def test_never_to_a_losing_site(self):
        """Every site loses money: nothing moves, and the 10 new levels go by grade
        (16 Psyche, +30%), not to the site that loses least (Ceres)."""
        profit = {"psyche": -500, "ceres": -100}
        s = eg.month(_state({"ceres": 150}), room=TWO_SITES, serves=BOTH, built=160, profit=profit, yard=YARD)
        self.assertEqual(s.moves, ())
        self.assertEqual(s.at, {"ceres": 150, "psyche": 10})

    def test_new_levels_go_to_the_best_site_that_makes_money(self):
        s = eg.month(_state({"psyche": 150}), room=TWO_SITES, serves=BOTH, built=160, profit=SKETCH, yard=YARD)
        self.assertEqual(s.at, {"psyche": 146, "ceres": 14})

    def test_by_hand_moves_toward_targets_at_the_pace(self):
        s = _state({"psyche": 150}, manual=True, target={"psyche": 50, "ceres": 100})
        s = eg.month(s, room=TWO_SITES, serves=BOTH, built=150, profit=SKETCH, yard=YARD)
        self.assertEqual(s.at, {"psyche": 146, "ceres": 4})
        self.assertEqual(s.target, {"psyche": 50, "ceres": 100})

    def test_by_hand_ignores_profit(self):
        s = _state({"ceres": 150}, manual=True, target={"psyche": 150})
        s = eg.month(s, room=TWO_SITES, serves=BOTH, built=150, profit=SKETCH, yard=YARD)
        self.assertEqual(s.at, {"ceres": 146, "psyche": 4})

    def test_level_with_no_target_stays(self):
        s = _state({"psyche": 150}, manual=True, target={"psyche": 100})
        s = eg.month(s, room=TWO_SITES, serves=BOTH, built=150, profit=SKETCH, yard=YARD)
        self.assertEqual(s.at, {"psyche": 150})
        self.assertEqual(s.moves, ())

    def test_by_hand_new_levels_fill_targets_then_go_by_grade(self):
        s = _state({"psyche": 100}, manual=True, target={"psyche": 100, "ceres": 30})
        s = eg.month(s, room=TWO_SITES, serves=BOTH, built=150, profit=SKETCH, yard=YARD)
        self.assertEqual(s.at, {"psyche": 120, "ceres": 30})

    def test_blockade_and_return_are_at_once(self):
        held = {"psyche": True, "ceres": True}
        blockaded = {"psyche": False, "ceres": True}
        for manual in (False, True):
            with self.subTest(manual=manual):
                target = {"psyche": 150} if manual else {}
                s = _state({"psyche": 150}, manual=manual, target=target)
                profit = eg.profits(ASTEROID, {})
                s = eg.month(s, room=TWO_SITES, serves=blockaded, held=held, built=150, profit=profit, yard=YARD)
                self.assertEqual((s.at, s.away, s.over, s.moves), ({"ceres": 150}, {"psyche": 150}, 0, ()))
                self.assertEqual(s.target, target)
                s = eg.month(s, room=TWO_SITES, serves=BOTH, built=150, profit=profit, yard=YARD)
                self.assertEqual((s.at, s.away, s.over, s.moves), ({"psyche": 150}, {}, 0, ()))
                self.assertEqual(s.target, target)

    def test_return_takes_from_past_the_room_first(self):
        room = {"psyche": 300, "ceres": 100}
        held = {"psyche": True, "ceres": True}
        s = _state({"psyche": 150})
        profit = eg.profits(ASTEROID, {})
        s = eg.month(s, room=room, serves={"ceres": True}, held=held, built=150, profit=profit, yard=YARD)
        self.assertEqual((s.at, s.away, s.over), ({"ceres": 100}, {"psyche": 150}, 50))
        s = eg.month(s, room=room, serves=held, built=150, profit=profit, yard=YARD)
        self.assertEqual((s.at, s.away, s.over), ({"psyche": 150}, {}, 0))

    def test_a_site_lost_for_good_loses_its_record(self):
        s = _state({"psyche": 100, "ceres": 50}, manual=True, target={"psyche": 100, "ceres": 50},
                   away={"psyche": 5})
        s = eg.month(s, room=TWO_SITES, serves={"ceres": True}, built=150, profit=SKETCH, yard=YARD)
        self.assertEqual((s.at, s.target, s.away, s.over), ({"ceres": 150}, {"ceres": 50}, {}, 0))

    def test_room_that_shrinks_while_serving_owes_nothing_back(self):
        """A Mining Complex level unstaffed: the excess leaves at once but not into
        `away`."""
        s = eg.month(_state({"psyche": 300}), room={"psyche": 250, "ceres": 200}, serves=BOTH, built=300,
                     profit=eg.profits(ASTEROID, {}), yard=YARD)
        self.assertEqual((s.at, s.away, s.moves), ({"psyche": 250, "ceres": 50}, {}, ()))

    def test_overflow_moves_into_new_room_at_once(self):
        profit = eg.profits(ASTEROID, {})
        s = eg.month(eg.BaseState(), room={"psyche": 250}, serves={"psyche": True}, built=400,
                     profit=profit, yard=YARD)
        self.assertEqual((s.at, s.over), ({"psyche": 250}, 150))
        s = eg.month(s, room=TWO_SITES | {"psyche": 250}, serves=BOTH, built=400, profit=profit, yard=YARD)
        self.assertEqual((s.at, s.over, s.moves), ({"psyche": 250, "ceres": 150}, 0, ()))

    def test_more_levels_than_room(self):
        s = _state({"psyche": 300, "ceres": 200}, over=100)
        s = eg.month(s, room=TWO_SITES, serves=BOTH, built=600, profit=SKETCH, yard=YARD)
        self.assertEqual((s.at, s.over, s.moves), ({"psyche": 300, "ceres": 200}, 100, ()))
        t, d = eg.mix_now(s)
        self.assertAlmostEqual(t, (300 * 0.30 + 200 * 0.15 + 100 * -0.75) / 600, delta=1e-12)
        weight = 300 * 1.3 + 200 * 1.15 + 100 * 0.25
        for g in eg.GOODS:
            with self.subTest(good=g):
                made = (300 * 1.3 * (1 + eg.mix("metallic")[g]) + 200 * 1.15 * (1 + eg.mix("carbonaceous")[g])
                        + 100 * 0.25)
                self.assertAlmostEqual(d[g], made / weight - 1, delta=1e-12)

    def test_toggling_gains_nothing(self):
        """Switching the checkbox off and on, and clicking, between months moves no
        level, so no month moves more than the pace."""
        sequences = ((), (False, True), (False, True, False, True), (False,), (True,))
        for seq in sequences:
            with self.subTest(toggles=seq):
                s = _state({"psyche": 150})
                for _ in range(3):
                    before = dict(s.at)
                    for on in seq:
                        s = eg.set_checkbox(s, on)
                        self.assertEqual(s.at, before)
                    s = eg.assign(s, "ceres", 25, room=TWO_SITES, built=150, queued=0) if not seq else s
                    self.assertEqual(s.at, before)
                    s = eg.month(s, room=TWO_SITES, serves=BOTH, built=150, profit=SKETCH, yard=YARD)
                    self.assertLessEqual(_moved(s), eg.pace(150))

    def test_lost_levels_come_off_overflow_first(self):
        s = _state({"psyche": 250}, over=150)
        s = eg.month(s, room={"psyche": 250}, serves={"psyche": True}, built=350,
                     profit=eg.profits(ASTEROID, {}), yard=YARD)
        self.assertEqual((s.at, s.over), ({"psyche": 250}, 100))

    def test_lost_levels_then_come_from_the_worst_site(self):
        s = _state({"psyche": 100, "ceres": 50})
        s = eg.month(s, room=TWO_SITES, serves=BOTH, built=130, profit=SKETCH, yard=YARD)
        self.assertEqual(s.at["psyche"] + s.at["ceres"], 130)
        # 20 lost at 16 Psyche, which earns least, then the month's pace moved to Ceres
        self.assertEqual(s.at["psyche"], 100 - 20 - eg.pace(130))

    def test_forecast_is_where_the_checkbox_stops(self):
        s = _state({"psyche": 130, "ceres": 20})
        f = eg.forecast(s, room=TWO_SITES, profit=SKETCH, yard=YARD)
        self.assertEqual(f.at, {"ceres": 150})
        self.assertEqual(s.at, {"psyche": 130, "ceres": 20})
        f = eg.forecast(s, room=TWO_SITES, profit={"psyche": 9594, "ceres": 9594 + 300}, yard=YARD)
        self.assertEqual((f.at, f.moves), ({"psyche": 130, "ceres": 20}, ()))

    def test_forecast_by_hand_is_at_our_assignments(self):
        s = _state({"psyche": 150}, manual=True, target={"psyche": 50, "ceres": 100})
        f = eg.forecast(s, room=TWO_SITES, profit=SKETCH, yard=YARD)
        self.assertEqual(f.at, {"psyche": 50, "ceres": 100})

    def test_one_type_base_carries_the_type_mix(self):
        s = _state({"vesta": 100, "valles_marineris": 50, "daedalus": 30, "mercury": 7})
        _, d = eg.mix_now(s)
        for g in eg.GOODS:
            with self.subTest(good=g):
                self.assertAlmostEqual(d[g], eg.mix("rocky")[g], delta=1e-12)

    def test_no_levels_no_mix(self):
        self.assertEqual(eg.mix_now(eg.BaseState()), (0.0, {g: 0.0 for g in eg.GOODS}))

    def test_switching_off_keeps_where_the_levels_are(self):
        s = eg.set_checkbox(_state({"psyche": 100, "ceres": 20}, away={"io": 30}), on=False)
        self.assertTrue(s.manual)
        self.assertEqual(s.target, {"psyche": 100, "ceres": 20, "io": 30})
        s = eg.set_checkbox(s, on=True)
        self.assertEqual((s.manual, s.target), (False, {}))

    def test_the_buttons(self):
        room = TWO_SITES
        s = _state({"psyche": 150})
        s = eg.assign(s, "ceres", 5, room=room, built=150, queued=10)  # switches the checkbox off first
        self.assertEqual((s.manual, s.target), (True, {"psyche": 150, "ceres": 5}))
        s = eg.assign(s, "ceres", 25, room=room, built=150, queued=10)  # stops at the unassigned levels
        self.assertEqual(s.target["ceres"], 10)
        s = eg.assign(s, "ceres", 25, room=room, built=150, queued=10)  # none left
        self.assertEqual(s.target["ceres"], 10)
        s = eg.assign(s, "psyche", -25, room=room, built=150, queued=10)
        s = eg.assign(s, "ceres", 25, room={"ceres": 20}, built=150, queued=10)  # stops at the room
        self.assertEqual(s.target, {"psyche": 125, "ceres": 20})
        s = eg.assign(s, "ceres", -25, room=room, built=150, queued=10)  # stops at 0
        self.assertEqual(s.target, {"psyche": 125})
        self.assertEqual(s.at, {"psyche": 150})

    def test_next_place(self):
        s = _state({"psyche": 290})
        profit = eg.profits(ASTEROID, {})
        self.assertEqual(eg.next_place(s, room=TWO_SITES, serves=BOTH, queued=5, profit=profit), "psyche")
        self.assertEqual(eg.next_place(s, room=TWO_SITES, serves=BOTH, queued=10, profit=profit), "ceres")
        self.assertIsNone(eg.next_place(s, room=TWO_SITES, serves=BOTH, queued=210, profit=profit))

    def test_a_glut_stops_inside_the_margin_with_no_back_and_forth(self):
        """§ 10 stage 3: 150 levels at 16 Psyche when Glass and Plastics go 50% dear.
        As levels move to Ceres the base's own Glass and Plastics bring the price
        down, and the moves stop inside the margin, all one way. The price closes a
        share of its gap to where the base's supply puts it each month: 100%, 50% or
        25%. (Closing 10% a month, it overshoots and comes back once: the margin holds
        only while the price responds faster than the pace, as a market price does.)"""
        room, serves = TWO_SITES, BOTH
        yard = eg.yardstick(ASTEROID)

        def glass(s):
            return sum(n * 70 * (1 + eg.score(p, "glass")) for p, n in s.at.items())

        for lag in (1.0, 0.5, 0.25):
            with self.subTest(lag=lag):
                s = _state({"psyche": 150})
                start, premium, pairs, last = glass(s), 0.5, set(), None
                for m in range(120):
                    premium += lag * (0.5 - 0.6 * (glass(s) - start) / 26000 - premium)
                    profit = eg.profits(ASTEROID, {"glass": premium})
                    s = eg.month(s, room=room, serves=serves, built=150, profit=profit, yard=yard)
                    pairs |= {(a, b) for a, b, _ in s.moves}
                    last = m if s.moves else last
                self.assertEqual(pairs, {("psyche", "ceres")})
                self.assertLess(last, 60)
                self.assertGreater(s.at["psyche"], 0)
                self.assertLess(abs(profit["ceres"] - profit["psyche"]), eg.MARGIN * yard)

    def test_invariants_over_random_months(self):
        """Over random rooms, blockades, losses, gains, prices and toggles: the levels
        are all on record, no place holds more than its room, no month moves more than
        the pace, and the passes stay within the bound the script's loop is given."""
        import random

        rng = random.Random(1397)
        places = eg.PLACES
        for _ in range(60):
            s = eg.BaseState()
            room = {p: rng.choice((0, 0, 50, 100, 200)) for p in places}
            for _ in range(24):
                built = max(0, s.levels + rng.randint(-40, 60))
                held = {p: rng.random() < 0.9 for p in places}
                serves = {p: held[p] and rng.random() < 0.9 for p in places}
                if rng.random() < 0.2:
                    room = {p: max(0, r + rng.choice((-50, 0, 50))) for p, r in room.items()}
                prices = {g: rng.uniform(-0.6, 0.8) for g in eg.method_goods()}
                profit = eg.profits(ASTEROID, prices)
                if rng.random() < 0.15:
                    s = eg.set_checkbox(s, on=s.manual)
                if s.manual and rng.random() < 0.3:
                    s = eg.assign(s, rng.choice(places), rng.choice((-25, -5, 5, 25)), room=room,
                                  built=built, queued=rng.randint(0, 20))
                s = eg.month(s, room=room, serves=serves, held=held, built=built, profit=profit, yard=YARD)
                self.assertEqual(s.levels, built)
                for p, n in s.at.items():
                    self.assertLessEqual(n, room[p] if serves[p] else 0, p)
                    self.assertGreater(n, 0)
                self.assertGreaterEqual(s.over, 0)
                self.assertLessEqual(_moved(s), eg.pace(built))
                self.assertLessEqual(len(s.moves), len(places) + 1)
                self.assertTrue(all(n > 0 for _, _, n in s.moves))
                f = eg.forecast(s, room=room, serves=serves, profit=profit, yard=YARD)
                self.assertLessEqual(len(f.moves), len(places))
                self.assertEqual(f.levels, built)

if __name__ == "__main__":
    unittest.main()
