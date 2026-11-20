"""A nuclear city strike razes the state's urban buildings (nuclear_raze_effects.txt): a share
destroyed, every level still standing rebuilt government-owned. The generated dispatcher,
production method lists and level ladders (gen_nuclear_raze.py) are current, take only the
buildings the design names, and the strike paths, salvo sums and event text are wired to them."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
sys.path.insert(0, str(ROOT))

import gen_nuclear_raze as gen  # noqa: E402
from paradox_file_parser import ParadoxFileParser  # noqa: E402

EFFECTS = ROOT / "common/scripted_effects/nuclear_raze_effects.txt"
GENERATED = ROOT / gen.OUTPUT
VALUES = ROOT / "common/script_values/nuclear_raze_values.txt"
EXTRA_EFFECTS = ROOT / "common/scripted_effects/extra_effects.txt"
LOOSE = ROOT / "common/scripted_effects/nuclear_loose_effects.txt"
DETERRENCE = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
EVENTS_LOC = ROOT / "localization/english/te_events_l_english.yml"


def read(path):
	return path.read_text(encoding="utf-8-sig")


def canon(value):
	"""Tuples and lists alike, so a parse and the merged data compare."""
	return json.loads(json.dumps(value))


def block(text, name):
	"""The body of the top-level `name = { ... }` in a script file."""
	match = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
	if match is None:
		raise AssertionError(f"{name} not found")
	depth, index = 1, match.end()
	while depth:
		depth += {"{": 1, "}": -1}.get(text[index], 0)
		index += 1
	return text[match.end():index - 1]


def loc_value(key):
	match = re.search(rf'(?m)^ {re.escape(key)}:0 "(.*)"', read(EVENTS_LOC))
	if match is None:
		raise AssertionError(f"{key} not in {EVENTS_LOC.name}")
	return match[1]


class GeneratedRazeTest(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.state = gen.load_state(ROOT)
		cls.targets = gen.select_targets(cls.state)
		cls.names = [target.name for target in cls.targets]
		cls.groups = cls.state.get_data("Building Groups")
		cls.buildings = cls.state.get_data("Buildings")

	def test_the_committed_file_is_current(self):
		self.assertEqual(gen.regenerate(self.state, root=ROOT, dry_run=True), [],
			"run .venv/bin/python scripts/generators/gen_nuclear_raze.py")

	def chain(self, name):
		return gen.group_chain(self.groups, gen.unwrap(gen.unwrap(self.buildings[name]).get("building_group")))

	def test_only_urban_buildings_are_razed(self):
		# The owner's call (2026-11-19): rural buildings are spared, and nothing whose
		# removal another system or the engine would undo or punish is taken.
		spared_groups = {
			"bg_agriculture", "bg_plantations", "bg_ranching", "bg_extraction", "bg_military",
			"bg_monuments", "bg_grand_monuments", "bg_owner_buildings", "bg_service", "bg_canals",
			"bg_company_buildings", "bg_construction", "bg_trade", "bg_public_infrastructure",
		}
		for name in self.names:
			with self.subTest(building=name):
				self.assertFalse(spared_groups & set(self.chain(name)), self.chain(name))
		for name in ("building_financial_district", "building_manor_house", "building_urban_center",
				"building_construction_sector", "building_trade_center", "building_military_base",
				"building_barrack", "building_naval_fortification", "building_wheat_farm",
				"building_coal_mine", "building_strategic_reserve_hub", "building_grid_transfer_station"):
			with self.subTest(spared=name):
				self.assertNotIn(name, self.names)

	def test_the_city_is_razed(self):
		for name in ("building_steel_mill", "building_textile_mill", "building_power_plant",
				"building_port", "building_railway", "building_government_administration",
				"building_university", "building_art_academy"):
			with self.subTest(building=name):
				self.assertIn(name, self.names)

	def test_ownership_follows_the_building(self):
		# A privately ownable building comes back government-owned; a government
		# building (no ownership type) comes back as it was, with a plain level.
		dispatcher = block(read(GENERATED), "nd_raze_all_buildings")
		for target in self.targets:
			with self.subTest(building=target.name):
				build = "nd_raze_build_owned" if target.owned else "nd_raze_build_plain"
				self.assertIn(f"BUILDING = {target.name} PMS = nd_raze_pms_{target.name} BUILD = {build} ", dispatcher)
		self.assertFalse(next(t for t in self.targets if t.name == "building_university").owned)
		self.assertTrue(next(t for t in self.targets if t.name == "building_steel_mill").owned)

	def test_ownership_methods_are_not_put_back(self):
		academy = next(t for t in self.targets if t.name == "building_art_academy")
		groups = gen.as_list(gen.unwrap(self.buildings["building_art_academy"]).get("production_method_groups"))
		self.assertIn("pmg_ownership_building_art_academy", groups)
		pm_groups = self.state.get_data("PM Groups")
		ownership_pms = gen.as_list(gen.unwrap(pm_groups["pmg_ownership_building_art_academy"]).get("production_methods"))
		self.assertTrue(ownership_pms)
		self.assertFalse(set(ownership_pms) & set(academy.pms))
		self.assertTrue(academy.pms)

	def test_every_guard_copies_back_as_parsed(self):
		# The dispatcher's limit is the building's own potential and possible written
		# back out: parsed again, it reads as the building's block did.
		guards = [(target.name, key, value) for target in self.targets for key, value in target.guards]
		self.assertTrue(guards)
		with tempfile.TemporaryDirectory() as tmp:
			for name, key, value in guards:
				with self.subTest(building=name, guard=key):
					path = Path(tmp) / "guard.txt"
					path.write_text("\n".join(gen.serialize_value(key, "=", value, 0)) + "\n", encoding="utf-8")
					parser = ParadoxFileParser()
					parser.parse_file(str(path), apply_directives=False)
					self.assertEqual(canon(parser.data[key]), canon(("=", value)))

	def test_the_technology_guard_is_each_buildings_own(self):
		dispatcher = block(read(GENERATED), "nd_raze_all_buildings")
		for target in self.targets:
			with self.subTest(building=target.name):
				self.assertRegex(dispatcher, rf"has_building = {target.name}\n\t\t\towner = \{{ has_technology_researched = {re.escape(target.techs[0])} \}}")


class LadderTest(unittest.TestCase):
	def test_the_ladder(self):
		rungs = gen.ladder()
		self.assertEqual(rungs[:gen.EXACT], list(range(1, gen.EXACT + 1)))
		self.assertGreaterEqual(rungs[-1], gen.TOP)
		for low, high in zip(rungs, rungs[1:]):
			self.assertGreater(high, low)
			if low >= gen.EXACT:
				self.assertLessEqual(high, max(low + 1, round(low * gen.STEP)))

	def test_each_rung_is_built_below_the_next(self):
		# A rebuild snaps down: the rung chosen is the largest at or below the levels
		# left, so a building never comes back as large as it was.
		rungs = gen.ladder()
		text = read(GENERATED)
		for name, create in (("nd_raze_build_owned", "levels = {rung} }} }} }}"), ("nd_raze_build_plain", "level = {rung} }}")):
			body = block(text, name)
			with self.subTest(ladder=name):
				branches = re.findall(r"limit = \{ var:nd_raze_left < (\d+) \}\n\t\tcreate_building = \{ building = \$BUILDING\$ (.*)\n\t\tset_variable = \{ name = nd_raze_built value = (\d+) \}", body)
				self.assertEqual(len(branches), len(rungs) - 1)
				for (bound, created, built), rung, next_rung in zip(branches, rungs, rungs[1:]):
					self.assertEqual(int(bound), next_rung)
					self.assertEqual(int(built), rung)
					self.assertTrue(created.endswith(create.format(rung=rung)), created)
				self.assertIn(f"value = {rungs[-1]} }}\n\t}}\n\tchange_variable = {{ name = nd_raze_nat add = var:nd_raze_built }}", body)


class WiringTest(unittest.TestCase):
	def test_every_city_strike_razes(self):
		strike = block(read(EXTRA_EFFECTS), "nuclear_industrial_strike")
		self.assertIn("nuclear_strike_raze_city = yes", strike)
		self.assertLess(strike.index("kill_population_percent_in_state"), strike.index("nuclear_strike_raze_city"))
		# The counterforce and tactical strikes hit military sites, not the city.
		for name in ("nd_counterforce_strike_damage", "nuclear_tactical_strike"):
			self.assertNotIn("nuclear_strike_raze_city", block(read(EXTRA_EFFECTS), name))

	def test_the_razing_runs_only_on_the_real_strike(self):
		entry = block(read(EFFECTS), "nuclear_strike_raze_city")
		self.assertRegex(entry, r"set_variable = nd_raze_click\s+if = \{\s+limit = \{ has_variable = nd_raze_click \}\s+remove_variable = nd_raze_click\s+nd_raze_city_run = yes")

	def test_a_loose_warhead_razes_less(self):
		loose = read(LOOSE)
		self.assertRegex(loose, r"nd_raze_roll_terror_factor = yes\s+nuclear_industrial_strike = yes")
		factors = re.findall(r"set_variable = \{ name = nd_raze_factor value = ([\d.]+) \}", block(read(EFFECTS), "nd_raze_roll_terror_factor"))
		self.assertEqual([float(f) for f in factors], [round(0.1 * n, 1) for n in range(1, 11)])
		self.assertIn("multiply = var:nd_raze_factor", block(read(VALUES), "nd_raze_share_destroyed"))
		run = block(read(EFFECTS), "nd_raze_city_run")
		self.assertTrue(run.rstrip().endswith("remove_variable = nd_raze_factor\n\t}"), "the factor goes with every strike, a same-day one too")

	def test_the_share_destroyed(self):
		# Half the metropolitan share, the share held between 10% and 80% first, so 5% to 40%,
		# only under Full; a quarter otherwise (owner, 2026-11-20).
		base = block(read(VALUES), "nd_raze_share_base")
		self.assertRegex(base, r"^\s+value = 0\.5\n")
		self.assertRegex(base, r"te_demog_effects_run = yes\s+has_variable = te_dg_mt\s+\}\s+value = var:te_dg_mt\s+divide = 100\s+min = 0\.1\s+max = 0\.8\s+\}\s+multiply = 0\.5\s*$")

	def test_a_salvo_sums_what_it_razed(self):
		deterrence = read(DETERRENCE)
		order = block(deterrence, "nd_order_salvo")
		self.assertIn("set_variable = { name = nd_raze_tally_lost value = 0 }", order)
		self.assertIn("set_variable = { name = nd_raze_tally_nat value = 0 }", order)
		self.assertLess(order.index("nd_raze_tally_lost"), order.index("nd_salvo_warhead = yes"))
		aftermath = block(deterrence, "nd_salvo_aftermath")
		self.assertIn("set_variable = { name = nd_salvo_seen_razed value = var:nd_raze_tally_lost days = 30 }", aftermath)
		self.assertIn("set_variable = { name = nd_salvo_seen_razed_nat value = var:nd_raze_tally_nat days = 30 }", aftermath)
		self.assertLess(aftermath.index("nd_salvo_seen_razed"), aftermath.index("nuclear_weapon_events.1 popup"))
		clear = block(deterrence, "nd_salvo_clear")
		self.assertIn("remove_variable = nd_raze_tally_lost", clear)
		self.assertIn("remove_variable = nd_raze_tally_nat", clear)

	def test_the_events_report_it(self):
		single_victim = "[SCOPE.sState('target_state').GetCustom('nd_raze_line_victim')]"
		single_attacker = "[SCOPE.sState('target_state').GetCustom('nd_raze_line_attacker')]"
		salvo_victim = "[ROOT.GetCountry.GetCustom('nd_raze_salvo_line_victim')]"
		salvo_attacker = "[SCOPE.sCountry('target_country').GetCustom('nd_raze_salvo_line_attacker')]"
		expected = {
			"nuclear_weapon_events.1.d": single_victim,
			"nuclear_weapon_events.11.d": single_victim,
			"nuclear_loose.2.d": "[SCOPE.sState('nd_loose_state').GetCustom('nd_raze_line_victim')]",
			"nuclear_weapon_events.1.d_cut_off": salvo_victim,
			"nuclear_weapon_events.1.d_salvo_cities": salvo_victim,
			"nuclear_weapon_events.1.d_salvo_leadership": salvo_victim,
			"nuclear_weapon_events.2.d": single_attacker,
			"nuclear_weapon_events.2.d_commander": single_attacker,
			"nuclear_weapon_events.2.d_system": single_attacker,
			"nuclear_weapon_events.2.d_warning": single_attacker,
			"nuclear_weapon_events.12.d": single_attacker,
			"nuclear_weapon_events.2.d_salvo": salvo_attacker,
			"nuclear_weapon_events.2.d_salvo_cut_off": salvo_attacker,
			"nuclear_weapon_events.2.d_salvo_leadership": salvo_attacker,
		}
		for key, call in expected.items():
			with self.subTest(key=key):
				self.assertTrue(loc_value(key).endswith(call))
		# A Forces salvo hits the nuclear forces' bases, not the cities: it razes nothing.
		for key in ("nuclear_weapon_events.1.d_salvo_forces", "nuclear_weapon_events.2.d_salvo_forces"):
			self.assertNotIn("nd_raze", loc_value(key))


if __name__ == "__main__":
	unittest.main()
