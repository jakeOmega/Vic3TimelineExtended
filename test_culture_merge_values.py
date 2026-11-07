"""Tests for the culture-merge rule, thresholds, conversion rate and speed modifier.

Files under test: common/script_values/te_culture_merge_values.txt (every named
number, and the pop-scope rate te_cm_pop_rate), common/scripted_triggers/
te_culture_merge_triggers.txt, the game rule in common/game_rules/
extra_game_rules.txt, the modifier type country_culture_merge_speed_mult and its
four sources (Public Schools, the Ministry of Culture, Radio, Film, Mass
Propaganda).

The pace test mirrors te_cm_pop_rate in Python. The script value can't be run
offline, so the mirror reads every coefficient from the values file and a
structural test pins the script value's text to the factors the mirror applies.

Run: python3 -m unittest test_culture_merge_values -v
"""

import json
import math
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
VALUES = ROOT / "common/script_values/te_culture_merge_values.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_culture_merge_triggers.txt"
RULES = ROOT / "common/game_rules/extra_game_rules.txt"
TYPES = ROOT / "common/modifier_type_definitions/te_culture_merge_modifier_types.txt"
LAW_INJECT = ROOT / "common/laws/te_culture_merge_law_injections.txt"
TECH_INJECT = ROOT / "common/technology/technologies/te_culture_merge_tech_injections.txt"
INSTITUTIONS = ROOT / "common/institutions/extra_institutions.txt"
VANILLA_SCRIPT_VALUES = ROOT / "vanilla_parsed/common/script_values.json"
VANILLA_TECHS = ROOT / "vanilla_parsed/common/technologies.json"
LOC_DIR = ROOT / "localization/english"

SPEED = "country_culture_merge_speed_mult"
RATE_BLOCK = "te_cm_pop_rate"


def unwrap(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def parse(path, apply_directives=True):
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=apply_directives)
    return {key: unwrap(value) for key, value in parser.data.items()}


_VANILLA_VALUES = None


def vanilla_value(name):
    """A vanilla named script value from the committed snapshot (acceptance_status_4 = 60)."""
    global _VANILLA_VALUES
    if _VANILLA_VALUES is None:
        _VANILLA_VALUES = json.loads(VANILLA_SCRIPT_VALUES.read_text(encoding="utf-8"))
    return float(unwrap(_VANILLA_VALUES[name]))


def values():
    """Every top-level te_cm_ number as a float. A value that is `{ value = <name> }`
    or a bare name (te_cm_accept_open = acceptance_status_4) resolves through
    vanilla's script values, so the hysteresis comparisons are between numbers."""
    parsed = parse(VALUES)
    out = {}
    for key, raw in parsed.items():
        if key == RATE_BLOCK:
            continue
        if isinstance(raw, dict):
            raw = unwrap(raw["value"])
        try:
            out[key] = float(raw)
        except ValueError:
            out[key] = vanilla_value(raw)
    return out


def rate_text():
    """The raw text of the te_cm_pop_rate block (it needs a brace-matched slice)."""
    text = VALUES.read_text(encoding="utf-8-sig")
    start = text.index(RATE_BLOCK + " = {")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("te_cm_pop_rate never closes")


# ---------------------------------------------------------------------------
# The mirror of te_cm_pop_rate and its sources.
# ---------------------------------------------------------------------------

def pop_rate(v, *, literacy, urbanization, speed, discriminated=False, in_homeland=True, is_starter=True):
    """This year's conversion fraction of one pop, as te_cm_pop_rate computes it.

    literacy: the pop's literacy_rate, 0-1.
    urbanization: vanilla's state_urbanization_rate (common/script_values/
        building_values.txt: total_urbanization / state_population * 1000,
        clamped to 0-1), a share. 0.1 is a state 10% urban, 0.4 one 40% urban.
    speed: the owner's modifier:country_culture_merge_speed_mult (0.8 = +80%).
    """
    rate = v["te_cm_base_rate"]
    rate *= v["te_cm_literacy_base"] + literacy
    rate *= 1 + v["te_cm_urban_weight"] * urbanization
    rate *= 1 + speed
    if discriminated:
        rate *= v["te_cm_discriminated_factor"]
    if not in_homeland:
        rate *= v["te_cm_diaspora_factor"]
    if not is_starter:
        rate *= v["te_cm_sphere_rate_factor"]
    return max(0.0, min(0.5, rate))


def years_to_switch(v, fraction):
    """Years until the part's remaining share, (1 - f) ** n, falls to 1 - te_cm_switch_share."""
    return math.log(1 - v["te_cm_switch_share"]) / math.log(1 - fraction)


def modifier_lines(path, entity):
    """The `modifier = { ... }` block of an INJECT:<entity> in a file, as a dict."""
    body = parse(path, apply_directives=False)["INJECT:" + entity]
    return {k: float(unwrap(x)) for k, x in unwrap(body["modifier"]).items()}


def ministry_per_level():
    """The Ministry of Culture's speed per institution level (the engine multiplies by the level)."""
    ministry = unwrap(parse(INSTITUTIONS)["institution_ministry_of_culture"]["modifier"])
    return float(unwrap(ministry[SPEED]))


def speed_from_files(*, public_schools, ministry_level, techs):
    """The speed modifier a country has, summed from the files that grant it."""
    total = 0.0
    if public_schools:
        total += modifier_lines(LAW_INJECT, "law_public_schools")[SPEED]
    total += ministry_level * ministry_per_level()
    for tech in techs:
        total += modifier_lines(TECH_INJECT, tech)[SPEED]
    return total


def loc_keys():
    keys = {}
    for path in sorted(LOC_DIR.glob("*.yml")):
        for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', path.read_text(encoding="utf-8-sig"), re.M):
            keys[m.group(1)] = m.group(2)
    return keys


class TestThresholds(unittest.TestCase):
    def test_values_match_the_spec(self):
        v = values()
        self.assertEqual(v["te_cm_hold_open"], 0.60)
        self.assertEqual(v["te_cm_switch_share"], 0.667)
        self.assertEqual(v["te_cm_sphere_rate_factor"], 0.5)
        self.assertEqual(v["te_cm_wait_cap_years"], 20)

    def test_plan_numbers(self):
        v = values()
        self.assertEqual(v["te_cm_hold_close"], 0.50)
        self.assertEqual(v["te_cm_accept_open"], 60)
        self.assertEqual(v["te_cm_accept_close"], 55)
        self.assertEqual(v["te_cm_accept_high_open"], 80)
        self.assertEqual(v["te_cm_accept_high_close"], 75)
        self.assertEqual(v["te_cm_sol_gap_close"], 4)
        self.assertEqual(v["te_cm_sol_gap_open"], 3)
        self.assertEqual(v["te_cm_meaningful_share"], 0.10)
        self.assertEqual(v["te_cm_years_tier2"], 30)
        self.assertEqual(v["te_cm_years_tier3"], 50)

    def test_hysteresis_closes_looser_than_it_opens(self):
        v = values()
        self.assertLess(v["te_cm_hold_close"], v["te_cm_hold_open"])
        self.assertLess(v["te_cm_accept_close"], v["te_cm_accept_open"])
        self.assertLess(v["te_cm_accept_high_close"], v["te_cm_accept_high_open"])
        # The SoL gap opens below 3 and closes above 4: here "looser" is larger.
        self.assertLess(v["te_cm_sol_gap_open"], v["te_cm_sol_gap_close"])

    def test_acceptance_names_resolve_to_vanilla_statuses(self):
        raw = parse(VALUES)
        self.assertEqual(unwrap(unwrap(raw["te_cm_accept_open"])["value"]), "acceptance_status_4")
        self.assertEqual(unwrap(unwrap(raw["te_cm_accept_high_open"])["value"]), "acceptance_status_5")


class TestRule(unittest.TestCase):
    def test_rule_polarity(self):
        rules = parse(RULES)
        rule = rules["culture_merges_rule"]
        self.assertEqual(unwrap(rule["default"]), "culture_merges_enabled")
        self.assertIn("culture_merges_enabled", rule)
        self.assertIn("culture_merges_disabled", rule)
        self.assertEqual(unwrap(unwrap(rule["culture_merges_enabled"])["flag"]), "culture_merges_enabled")
        self.assertEqual(unwrap(unwrap(rule["culture_merges_disabled"])["flag"]), "culture_merges_disabled")
        trigger = parse(TRIGGERS)["te_cm_system_enabled"]
        self.assertEqual(trigger, {"NOT": ("=", {"has_game_rule": ("=", "culture_merges_disabled")})})

    def test_rule_loc(self):
        loc = loc_keys()
        for key in (
            "rule_culture_merges_rule",
            "setting_culture_merges_enabled", "setting_culture_merges_enabled_desc",
            "setting_culture_merges_disabled", "setting_culture_merges_disabled_desc",
        ):
            self.assertIn(key, loc)


class TestTriggers(unittest.TestCase):
    def test_tier_tech_dispatches_to_the_three_techs(self):
        triggers = parse(TRIGGERS)
        self.assertEqual(triggers["te_cm_tier_tech"], {"te_cm_tier_tech_$TIER$": ("=", "yes")})
        for tier, tech in ((1, "pan-nationalism"), (2, "mass_media"), (3, "television")):
            self.assertEqual(
                triggers["te_cm_tier_tech_%d" % tier],
                {"has_technology_researched": ("=", tech)},
            )

    def test_tier_techs_exist(self):
        vanilla_techs = json.loads(VANILLA_TECHS.read_text(encoding="utf-8"))
        mod_text = (ROOT / "common/technology/technologies/era_6.txt").read_text(encoding="utf-8-sig")
        self.assertIn("pan-nationalism", vanilla_techs)
        for tech in ("radio", "film", "mass_propaganda"):
            self.assertIn(tech, vanilla_techs)
        for tech in ("mass_media", "television"):
            self.assertRegex(mod_text, r"(?m)^%s = \{" % tech)

    def test_in_sphere_has_its_three_clauses(self):
        text = TRIGGERS.read_text(encoding="utf-8-sig")
        start = text.index("te_cm_in_sphere = {")
        block = text[start:]
        self.assertIn("this = scope:te_cm_starter", block)
        self.assertIn("is_subject_of = scope:te_cm_starter", block)
        self.assertIn("scope:te_cm_starter = { is_power_bloc_leader = yes }", block)
        self.assertIn("is_in_same_power_bloc = scope:te_cm_starter", block)


class TestSpeedModifier(unittest.TestCase):
    def test_type_is_registered(self):
        body = parse(TYPES)[SPEED]
        self.assertEqual(unwrap(body["color"]), "good")
        self.assertEqual(unwrap(body["percent"]), "yes")
        self.assertEqual(unwrap(body["decimals"]), "0")

    def test_sources(self):
        self.assertEqual(modifier_lines(LAW_INJECT, "law_public_schools"), {SPEED: 0.10})
        self.assertEqual(modifier_lines(TECH_INJECT, "radio"), {SPEED: 0.10})
        self.assertEqual(modifier_lines(TECH_INJECT, "film"), {SPEED: 0.05})
        self.assertEqual(modifier_lines(TECH_INJECT, "mass_propaganda"), {SPEED: 0.10})
        self.assertEqual(ministry_per_level(), 0.05)

    def test_every_speed_value_shows_as_a_whole_percent(self):
        # decimals = 0 with percent = yes: a source that is not a multiple of 0.01 would round away.
        sources = [ministry_per_level(), modifier_lines(LAW_INJECT, "law_public_schools")[SPEED]]
        sources += [modifier_lines(TECH_INJECT, tech)[SPEED] for tech in ("radio", "film", "mass_propaganda")]
        for value in sources:
            self.assertAlmostEqual(value * 100, round(value * 100), places=9)

    def test_loc(self):
        loc = loc_keys()
        self.assertIn(SPEED, loc)
        self.assertIn(SPEED + "_desc", loc)


class TestPace(unittest.TestCase):
    """The owner's pace targets (spec section 5): a developed, literate, urbanizing
    country reaches its switch in about 20 years, a slow one in about 40."""

    def developed(self, **kw):
        speed = speed_from_files(public_schools=True, ministry_level=3, techs=("radio", "film"))
        args = dict(literacy=0.8, urbanization=0.4, speed=speed)
        args.update(kw)
        return pop_rate(values(), **args)

    def slow(self, **kw):
        args = dict(literacy=0.3, urbanization=0.1, speed=0.0)
        args.update(kw)
        return pop_rate(values(), **args)

    def test_developed_speed_sums_to_0_4(self):
        # Public Schools 0.10 + Ministry level 3 (3 x 0.05) + Radio 0.10 + Film 0.05; no Mass Propaganda.
        speed = speed_from_files(public_schools=True, ministry_level=3, techs=("radio", "film"))
        self.assertAlmostEqual(speed, 0.40, places=9)

    def test_pace_targets(self):
        v = values()
        developed = years_to_switch(v, self.developed())
        slow = years_to_switch(v, self.slow())
        self.assertTrue(17 <= developed <= 23, developed)
        self.assertTrue(35 <= slow <= 45, slow)

    def test_pop_circumstances_matter_as_much_as_policy(self):
        """Owner: literacy and urbanization are levers beside public education and the Ministry.
        Between the slow and the developed profile the spread is about half the pop's
        circumstances and half policy. Each factor alone must multiply the rate by at
        least the minimum below, so a retune can't flatten them without failing here."""
        v = values()
        speed = speed_from_files(public_schools=True, ministry_level=3, techs=("radio", "film"))
        base = dict(literacy=0.3, urbanization=0.1, speed=0.0)
        literacy = pop_rate(v, **dict(base, literacy=0.8)) / pop_rate(v, **base)
        urbanization = pop_rate(v, **dict(base, urbanization=0.4)) / pop_rate(v, **base)
        policy = pop_rate(v, **dict(base, speed=speed)) / pop_rate(v, **base)
        self.assertGreaterEqual(literacy, 1.25, literacy)
        self.assertGreaterEqual(urbanization, 1.15, urbanization)
        self.assertAlmostEqual(policy, 1.40, places=9)
        circumstances = math.log(literacy) + math.log(urbanization)
        share = circumstances / (circumstances + math.log(policy))
        self.assertTrue(0.4 <= share <= 0.6, share)

    def test_bloc_member_takes_about_twice_as_long(self):
        v = values()
        developed = years_to_switch(v, self.developed())
        member = years_to_switch(v, self.developed(is_starter=False))
        self.assertTrue(1.8 <= member / developed <= 2.2, member / developed)

    def test_rates_are_conversion_fractions(self):
        for f in (self.developed(), self.slow()):
            self.assertTrue(0 < f < 0.5, f)

    def test_each_factor_applies(self):
        v = values()
        base = dict(literacy=0.5, urbanization=0.2, speed=0.4)
        plain = pop_rate(v, **base)
        self.assertAlmostEqual(pop_rate(v, discriminated=True, **base), plain * 0.1, places=12)
        self.assertAlmostEqual(pop_rate(v, in_homeland=False, **base), plain * 2, places=12)
        self.assertAlmostEqual(pop_rate(v, is_starter=False, **base), plain * 0.5, places=12)
        self.assertGreater(pop_rate(v, **dict(base, literacy=0.9)), pop_rate(v, **dict(base, literacy=0.1)))
        self.assertGreater(pop_rate(v, **dict(base, urbanization=0.9)), pop_rate(v, **dict(base, urbanization=0.0)))
        self.assertGreater(pop_rate(v, **dict(base, speed=1.0)), pop_rate(v, **dict(base, speed=0.0)))

    def test_rate_is_clamped(self):
        v = values()
        self.assertEqual(pop_rate(v, literacy=1, urbanization=1, speed=500), 0.5)
        self.assertEqual(pop_rate(v, literacy=0, urbanization=0, speed=-5), 0.0)

    def test_the_script_value_applies_the_mirrors_factors(self):
        """Drift guard: the script value names each input the mirror reads."""
        text = rate_text()
        for needle in (
            "te_cm_base_rate",
            "te_cm_literacy_base",
            "literacy_rate",
            "te_cm_urban_weight",
            "state.state_urbanization_rate",
            "owner.modifier:" + SPEED,
            "pop_acceptance < acceptance_status_4",
            "te_cm_discriminated_factor",
            "is_homeland = scope:te_cm_part",
            "te_cm_diaspora_factor",
            "owner = scope:te_cm_starter",
            "te_cm_sphere_rate_factor",
            "min = 0",
            "max = 0.5",
        ):
            self.assertIn(needle, text)
        # Each flat factor is a named value, not a literal in the rate.
        self.assertNotRegex(text, r"multiply = (0\.1|2|0\.5)\s")

    def test_factor_values(self):
        v = values()
        self.assertEqual(v["te_cm_discriminated_factor"], 0.1)
        self.assertEqual(v["te_cm_diaspora_factor"], 2)


class TestFiles(unittest.TestCase):
    def test_each_new_script_file_has_one_bom_and_tabs(self):
        for path in (VALUES, TRIGGERS, TYPES, LAW_INJECT, TECH_INJECT):
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), path.name)
            self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"), path.name)
            for line in raw.decode("utf-8-sig").splitlines():
                self.assertFalse(line.startswith(" "), path.name + ": " + line)

    def test_literals_take_at_most_five_decimals(self):
        # Script-value literals take at most five decimals (test_engine_literal_forms).
        for m in re.finditer(r"=\s*(-?\d+\.\d+)", VALUES.read_text(encoding="utf-8-sig")):
            self.assertLessEqual(len(m.group(1).split(".")[1]), 5, m.group(0))


if __name__ == "__main__":
    unittest.main()
