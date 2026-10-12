"""Demographics phase 3: the event wave (docs/superpowers/specs/2026-10-08-demographics-design.md §9).

Static checks on the ten events (art, loc, AI weights, no trigger of their own, the harm menus' shape), the dispatcher's
wiring, the thresholds pinned to scripts/analysis/demographics_wave.py, the share past the old-age threshold run through
test_demographics_registry's _Engine against its Python twin, the self-check's measure lines, and the fit's bands on the
model (demographics_wave.report without saves).
"""

import contextlib
import io
import json
import random
import re
import sys
import unittest

from test_demographics_registry import ROOT, _Engine, _parse_script, _raw_blocks, _text

sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
import demographics_params as P  # noqa: E402
import demographics_wave as DW  # noqa: E402

EVENTS = ROOT / "events" / "te_demog_wave_events.txt"
CONSOLE = ROOT / "events" / "te_debug_demog_events.txt"
VALUES = ROOT / "common" / "script_values" / "te_demog_wave_values.txt"
TRIGGERS = ROOT / "common" / "scripted_triggers" / "te_demog_wave_triggers.txt"
EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_wave_effects.txt"
MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_wave_modifiers.txt"
MEASURE_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_measure_modifiers.txt"
ON_ACTIONS = ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"
TYPES_FILE = ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt"
LOC_EVENTS = ROOT / "localization" / "english" / "te_events_l_english.yml"
LOC_MISC = ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml"
ENGINE_MODIFIERS = ROOT / "docs" / "engine" / "modifiers_summary.txt"

# The thresholds: te_demog_wave_values.txt's constant -> demographics_wave's.
THRESHOLDS = {
    "te_demog_wave_k_dividend_ref": DW.DIVIDEND_REF, "te_demog_wave_k_dividend_bar": DW.DIVIDEND_BAR,
    "te_demog_wave_k_greying_pensioners": DW.GREYING_PENSIONERS, "te_demog_wave_k_greying_old": DW.GREYING_OLD,
    "te_demog_wave_k_youth_share": DW.YOUTH_SHARE, "te_demog_wave_k_youth_unemployment": DW.YOUTH_UNEMPLOYMENT,
    "te_demog_wave_k_girls_srb": DW.GIRLS_SRB, "te_demog_wave_k_branches": DW.BRANCHES,
    "te_demog_wave_k_villages_farm": DW.VILLAGES_FARM, "te_demog_wave_k_villages_median": DW.VILLAGES_MEDIAN,
    "te_demog_wave_k_villages_shrink": DW.VILLAGES_SHRINK, "te_demog_wave_k_crowding": DW.CROWDING,
    "te_demog_wave_k_lost_share": DW.LOST_SHARE, "te_demog_wave_k_war_men": DW.WAR_MEN,
    "te_demog_wave_k_boom_years": DW.BOOM_YEARS, "te_demog_wave_k_boom_dead": DW.BOOM_DEAD,
}
# The dispatcher's yearly events, in its order, and the war tracker's two.
YEARLY = [("immortal", 10), ("greying", 4), ("youth", 5), ("girls", 6), ("branches", 7), ("villages", 8),
          ("overspill", 9), ("dividend", 1)]
MONTHLY = [("lost", 3), ("boom", 2)]
HARM_MENUS = (3, 8)
# The options that put a census type on a timed country modifier, with the self-check's code and the line it expects.
CENSUS_LINE_OPTIONS = {("6", "a"): ("te_demog_wave_srb_ban", 1, "state_sex_ratio_at_birth_add"),
                       ("6", "b"): ("te_demog_wave_srb_daughters", 1, "state_sex_ratio_at_birth_add"),
                       ("10", "a"): ("te_demog_wave_immortal_licences", 2, "state_desired_fertility_mult"),
                       ("10", "c"): ("te_demog_wave_immortal_heirs", 2, "state_desired_fertility_mult")}


def _events(path=EVENTS):
    """{number: parsed body} of the wave's events."""
    blocks = _raw_blocks([path])
    return {k.split(".")[1]: _parse_script(v) for k, v in blocks.items() if k.startswith("te_demog_wave.")}


def _loc(path):
    out = {}
    for line in _text(path).split("\n"):
        m = re.match(r'^ ([\w.]+):0 "(.*)"\s*(#.*)?$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _walk(items):
    """Every (key, value) in a parsed block, depth first."""
    for key, _op, value in items:
        yield key, value
        if isinstance(value, list):
            yield from _walk(value)


def _option_letter(name):
    return name.split(".")[2].replace("_opt", "")


def _modifiers():
    return {k: _parse_script(v) for k, v in _raw_blocks([MODIFIERS]).items()}


def _census_types():
    return set(re.findall(r"^(\w+) = \{", re.sub(r"#[^\n]*", "", _text(TYPES_FILE)), re.M))


class TestThresholds(unittest.TestCase):
    def test_each_threshold_is_pinned_to_the_harness(self):
        values = _raw_blocks([VALUES])
        for name, want in THRESHOLDS.items():
            with self.subTest(name=name):
                got = float(re.search(r"value = (\S+)", values[name]).group(1))
                self.assertAlmostEqual(got, want, places=6)

    def test_the_dividends_bar_is_its_reference_raised_by_a_tenth(self):
        self.assertAlmostEqual(DW.DIVIDEND_BAR, round(DW.DIVIDEND_REF * DW.DIVIDEND_RISE, 3), places=6)

    def test_the_youth_unemployment_is_half_the_youth_bulges_full(self):
        self.assertAlmostEqual(DW.YOUTH_UNEMPLOYMENT, P.YOUTH_UNEMPLOYMENT_FULL / 2, places=6)


class TestOldPastShare(unittest.TestCase):
    """te_demog_wave_old_past_share (the script) against demographics_wave.old_past_share (its twin)."""

    def engine(self, women, men, old_age):
        eng = _Engine({})
        eng.values.update(_raw_blocks([VALUES]))
        for b in range(P.BANDS):
            eng.vars[f"te_dg_cbf{b}"], eng.vars[f"te_dg_cbm{b}"] = women[b], men[b]
        eng.vars["te_dg_old_age"] = old_age
        return eng

    def test_the_script_matches_its_twin(self):
        rng = random.Random(9)
        for _ in range(40):
            women = [rng.uniform(1e3, 1e6) for _ in range(P.BANDS)]
            men = [rng.uniform(1e3, 1e6) for _ in range(P.BANDS)]
            old_age = rng.uniform(40, 90)
            eng = self.engine(women, men, old_age)
            got = eng.value(eng._tree(eng.values, "te_demog_wave_old_past_share"))
            self.assertAlmostEqual(got, DW.old_past_share(women, men, old_age), places=9)

    def test_a_threshold_on_a_band_edge_counts_whole_bands(self):
        women = [100.0] * P.BANDS
        men = [100.0] * P.BANDS
        # old age from 65: bands 13 (65-69) to 17 (85+), five of eighteen
        self.assertAlmostEqual(DW.old_past_share(women, men, 65.0), 5 / 18, places=9)
        # from 67.5: half of 65-69 and the four above
        self.assertAlmostEqual(DW.old_past_share(women, men, 67.5), 4.5 / 18, places=9)

    def test_the_greying_reads_pensioners_under_old_age_pension(self):
        women, men = [100.0] * P.BANDS, [100.0] * P.BANDS
        eng = self.engine(women, men, 65.0)
        eng.vars["te_dg_pensioners"] = 0.31
        eng.trigger_fixtures["te_demog_has_pension_law"] = True
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_wave_greying_share")), 0.31)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_wave_greying_bar")), DW.GREYING_PENSIONERS)
        eng.trigger_fixtures["te_demog_has_pension_law"] = False
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_wave_greying_share")), 5 / 18)
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_wave_greying_bar")), DW.GREYING_OLD)


class TestEvents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _events()
        cls.loc = _loc(LOC_EVENTS)
        cls.misc = _loc(LOC_MISC)
        cls.mods = _modifiers()

    def test_ten_events(self):
        self.assertEqual(sorted(self.events, key=int), [str(n) for n in range(1, 11)])

    def test_each_has_art_and_no_trigger_of_its_own(self):
        for n, body in self.events.items():
            with self.subTest(event=n):
                keys = [k for k, _, _ in body]
                self.assertIn("event_image", keys)
                # a trigger would be evaluated on trigger_event and block the console's test firing
                self.assertNotIn("trigger", keys)
                self.assertNotIn("hidden", keys)

    def test_titles_descriptions_flavor_and_options_have_loc(self):
        for n, body in self.events.items():
            with self.subTest(event=n):
                for key in ("title", "flavor"):
                    self.assertIn(dict((k, v) for k, _, v in body)[key], self.loc)
                descs = [v for k, v in _walk(body) if k == "desc" and isinstance(v, str)]
                self.assertTrue(descs)
                for d in descs:
                    self.assertIn(d, self.loc)
                for k, _, opt in body:
                    if k == "option":
                        self.assertIn(dict((a, b) for a, _, b in opt)["name"], self.loc)

    def test_each_option_has_an_ai_weight_and_one_default(self):
        for n, body in self.events.items():
            options = [opt for k, _, opt in body if k == "option"]
            with self.subTest(event=n):
                self.assertGreaterEqual(len(options), 2)
                for opt in options:
                    self.assertIn("ai_chance", [k for k, _, _ in opt])
                defaults = [opt for opt in options if ("default_option", "=", "yes") in opt]
                # the Greying has one default with Old Age Pension and one without, behind exclusive triggers
                self.assertEqual(len(defaults), 2 if n == "4" else 1)

    def test_every_modifier_is_granted_in_an_option_and_exists(self):
        granted = set()
        for body in self.events.values():
            for k, _, opt in body:
                if k != "option":
                    continue
                for key, value in _walk(opt):
                    if key == "add_modifier" and isinstance(value, list):
                        granted.add(dict((a, b) for a, _, b in value)["name"])
        ours = {g for g in granted if g.startswith("te_demog_wave_")}
        self.assertEqual(ours, set(self.mods), "a wave modifier no option grants, or one granted but not defined")

    def test_every_modifier_field_is_an_engine_or_mod_type_and_has_loc(self):
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).split("\n") if line.count("|") >= 2}
        mod_types = set()
        for path in (ROOT / "common" / "modifier_type_definitions").glob("*.txt"):
            mod_types |= set(re.findall(r"^(\w+) = \{", re.sub(r"#[^\n]*", "", _text(path)), re.M))
        for name, fields in self.mods.items():
            with self.subTest(modifier=name):
                self.assertIn(name, self.misc)
                self.assertIn(name + "_desc", self.misc)
                for key, _, _ in fields:
                    if key == "icon":
                        continue
                    self.assertTrue(key in engine or key in mod_types, key)

    def test_a_census_line_never_stands_alone(self):
        # a release comments the census's types out (comment_out_census_inputs.py rule 1): each such modifier keeps a line
        census = _census_types()
        for name, fields in self.mods.items():
            lines = [k for k, _, _ in fields if k != "icon"]
            if any(k in census for k in lines):
                with self.subTest(modifier=name):
                    self.assertTrue([k for k in lines if k not in census])

    def test_the_harm_menus_have_no_upside(self):
        # the catastrophe events' shape: every option delivers harms, none a positive field
        vanilla = json.loads((ROOT / "vanilla_parsed" / "common" / "modifier_types.json").read_text())

        def color(field):
            if re.match(r"interest_group_ig_\w+_approval_add$", field):
                return "good"
            entry = vanilla.get(field)
            return entry[1].get("color", ["=", "neutral"])[1] if entry else "neutral"

        for n in HARM_MENUS:
            for k, _, opt in self.events[str(n)]:
                if k != "option":
                    continue
                for key, value in _walk(opt):
                    if key != "add_modifier" or not isinstance(value, list):
                        continue
                    name = dict((a, b) for a, _, b in value)["name"]
                    for field, _, v in self.mods[name]:
                        if field == "icon":
                            continue
                        c = color(field)
                        sign = float(v)
                        with self.subTest(event=n, modifier=name, field=field):
                            self.assertFalse((c == "good" and sign > 0) or (c == "bad" and sign < 0))

    def test_each_harm_menu_option_spares_a_different_harm(self):
        harms = {"3": {"te_demog_wave_lost_mourning", "te_demog_wave_lost_workbenches", "te_demog_wave_lost_widows"},
                 "8": {"te_demog_wave_villages_fields", "te_demog_wave_villages_services", "te_demog_wave_villages_alone"}}
        for n, menu in harms.items():
            spared = []
            for k, _, opt in self.events[n]:
                if k != "option":
                    continue
                got = {dict((a, b) for a, _, b in v)["name"] for key, v in _walk(opt)
                       if key == "add_modifier" and isinstance(v, list)} & menu
                self.assertEqual(len(got), 2, (n, got))
                spared.append(menu - got)
            with self.subTest(event=n):
                self.assertEqual(len({frozenset(s) for s in spared}), 3)

    def test_the_census_line_options_arm_the_self_check_with_their_line(self):
        for (n, letter), (mod, code, field) in CENSUS_LINE_OPTIONS.items():
            opt = next(o for k, _, o in self.events[n] if k == "option"
                       and _option_letter(dict((a, b) for a, _, b in o)["name"]) == letter)
            calls = [v for k, v in _walk(opt) if k == "te_debug_demog_wave_selfcheck_start"]
            self.assertEqual(len(calls), 1, (n, letter))
            args = dict((a, b) for a, _, b in calls[0])
            line = float(dict((a, b) for a, _, b in self.mods[mod])[field])
            with self.subTest(event=n, option=letter):
                self.assertEqual(int(args["CODE"]), code)
                self.assertAlmostEqual(float(args["EXPECTED"]), line)

    def test_the_self_checks_measure_lines_are_the_measures(self):
        block = _raw_blocks([VALUES])["te_demog_wave_chk_measure_lines_srb"]
        measures = {k: _parse_script(v) for k, v in _raw_blocks([MEASURE_MODIFIERS]).items()}
        for mod in ("te_demog_ms_birth_limit", "te_demog_ms_birth_limit_one"):
            want = float(dict((a, b) for a, _, b in measures[mod])["state_sex_ratio_at_birth_add"])
            with self.subTest(modifier=mod):
                m = re.search(rf"has_modifier = {mod} \}}\s*add = (\S+)", block)
                self.assertIsNotNone(m, mod)
                self.assertAlmostEqual(float(m.group(1)), want)


class TestWiring(unittest.TestCase):
    def test_the_yearly_dispatcher_names_each_event_whole(self):
        block = _raw_blocks([EFFECTS])["te_demog_wave_yearly"]
        got = re.findall(r"te_demog_wave_try(?:_once)? = \{ EV = (\w+) EVENT = te_demog_wave\.(\d+) \}", block)
        self.assertEqual([(ev, int(n)) for ev, n in got], YEARLY)

    def test_the_war_tracker_fires_its_two(self):
        block = _raw_blocks([EFFECTS])["te_demog_wave_war_monthly"]
        for ev, n in MONTHLY:
            with self.subTest(event=ev):
                self.assertIn(f"te_demog_wave_cond_{ev} = yes", block)
                self.assertIn(f"trigger_event = {{ id = te_demog_wave.{n} }}", block)

    def test_each_event_has_its_condition(self):
        triggers = _raw_blocks([TRIGGERS])
        for ev, _n in YEARLY + MONTHLY:
            with self.subTest(event=ev):
                self.assertIn(f"te_demog_wave_cond_{ev}", triggers)

    def test_the_wave_runs_under_full_only(self):
        self.assertIn("te_demog_effects_run = yes", _raw_blocks([TRIGGERS])["te_demog_wave_runs"])
        effects = _raw_blocks([EFFECTS])
        for name in ("te_demog_wave_yearly", "te_demog_wave_war_monthly", "te_demog_wave_technology"):
            with self.subTest(effect=name):
                self.assertIn("te_demog_wave_runs = yes", effects[name])

    def test_the_hooks(self):
        blocks = _raw_blocks([ON_ACTIONS])
        yearly = blocks["te_demog_country_yearly_on_action"]
        self.assertLess(yearly.index("te_demog_country_yearly = yes"), yearly.index("te_demog_wave_yearly = yes"))
        self.assertIn("te_demog_wave_war_monthly = yes", blocks["te_demog_country_monthly_on_action"])
        self.assertIn("te_demog_wave_technology_on_action", blocks["on_acquired_technology"])
        self.assertIn("te_demog_wave_technology = yes", blocks["te_demog_wave_technology_on_action"])

    def test_the_console_fires_each_event(self):
        chooser = _raw_blocks([CONSOLE])["te_debug_demog.80"]
        fired = sorted(int(n) for n in re.findall(r"trigger_event = \{ id = te_demog_wave\.(\d+) \}", chooser))
        self.assertEqual(fired, list(range(1, 11)))
        self.assertIn("trigger_event = { id = te_debug_demog.80 }", _raw_blocks([CONSOLE])["te_debug_demog.1"])


class TestFit(unittest.TestCase):
    def test_the_bands_on_the_model(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = DW.report()
        self.assertEqual(rc, 0, out.getvalue())


if __name__ == "__main__":
    unittest.main()
