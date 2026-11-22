"""Vanilla 1.15 opportunities, from the prep doc's § 7.1 shortlist and § 4.11 (#1445-#1452).

Each change swaps a hand-rolled stand-in for a 1.15 engine feature, and the engine notices none of the ways it can come
apart: an unregistered modifier type, a leader weight that never reads it, a losing-war rule the twin trigger lacks, a
contextless entry's value reading a country, a reach check dropped from one site, an institution name with no loc, a
formal name filed as unused. These check the wiring. The in-game checks are in docs/testing/vanilla-1-15-playtest.md,
"1.15 opportunities".

Run: python3 -m unittest test_vanilla_1_15_opportunities -v
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _text(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, opener, start=None):
    """The brace block that starts at the first `opener` (which must end in `{`), opener included, or at `start`."""
    if start is None:
        start = text.index(opener)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError(f"unclosed block {opener!r}")


def _top(text, name):
    """A top-level definition's block, not the first call of it."""
    match = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if match is None:
        raise AssertionError(f"no top-level {name}")
    return _block(text, match.group(0), match.start())


def _all_loc():
    loc = {}
    for path in sorted((ROOT / "localization" / "english").rglob("*_l_english.yml")):
        for m in re.finditer(r'(?m)^ ([^\s:#]+):\d* "(.*)"', path.read_text(encoding="utf-8-sig")):
            loc[m.group(1)] = (path.name, m.group(2))
    return loc


class GdpPerCapitaTest(unittest.TestCase):
    """#1445: vanilla's global_average_gdp_per_capita replaces the mod's unread value."""

    def test_value_and_its_only_reader_are_gone(self):
        for path in (ROOT / "common").rglob("*.txt"):
            self.assertNotRegex(_strip_comments(path.read_text(encoding="utf-8-sig")), r"\bglobal_gdp_per_capita\b",
                                path.relative_to(ROOT).as_posix())
        self.assertNotIn("POP_LOW_GDP_PER_CAPITA_REL", _all_loc())

    def test_its_input_stays(self):
        """Other values read global_gdp_script_value; global_population is an engine event target."""
        values = _strip_comments(_text("common/script_values/extra_script_values.txt"))
        self.assertRegex(values, r"(?m)^global_gdp_script_value = \{")

    def test_country_gdp_per_capita_is_vanilla_s(self):
        """#1460: 1.15 defines country_gdp_per_capita; the mod's identical copy is gone and its readers read vanilla's.

        A bare duplicate script value logs nothing and the copy read last wins, so a mod copy would silently replace
        (or be replaced by) vanilla's in Reform or Revolution and the Five-Year Plan if the two ever diverged.
        """
        for path in (ROOT / "common" / "script_values").rglob("*.txt"):
            self.assertNotRegex(_strip_comments(path.read_text(encoding="utf-8-sig")),
                                r"(?m)^\s*country_gdp_per_capita\s*=\s*\{", path.relative_to(ROOT).as_posix())
        vanilla = json.loads(_text("vanilla_parsed/common/script_values.json"))
        self.assertIn("country_gdp_per_capita", vanilla)


class LeaderChanceTest(unittest.TestCase):
    """#1446: a mod ideology's leader-chance modifier is declared and read by hand (vanilla declares its own)."""

    TYPE = "interest_group_ideology_environmentalists_leader_chance_mult"

    def test_type_is_declared(self):
        types = _strip_comments(_text("common/modifier_type_definitions/mod_entity_modifier_types.txt"))
        self.assertRegex(types, rf"(?m)^{self.TYPE} = \{{")

    def test_both_leader_weights_read_it(self):
        ideology = _top(_strip_comments(_text("common/ideologies/extra_ideologies.txt")), "ideology_environmentalists")
        self.assertIn(f"add = modifier:{self.TYPE}", _block(ideology, "interest_group_leader_weight = {"))
        self.assertIn(f"add = interest_group.modifier:{self.TYPE}",
                      _block(ideology, "non_interest_group_leader_weight = {"))

    def test_the_pull_carries_it_and_has_loc(self):
        modifier = _top(_strip_comments(_text("common/static_modifiers/extra_modifiers.txt")),
                        "environmentalist_leader_pull_modifier")
        self.assertRegex(modifier, rf"{self.TYPE} = 1\b")
        loc = _all_loc()
        for key in (self.TYPE, f"{self.TYPE}_desc", "environmentalist_leader_pull_modifier",
                    "environmentalist_leader_pull_modifier_desc"):
            self.assertIn(key, loc)

    def test_only_the_reckoning_converts_a_sitting_leader(self):
        events = _strip_comments(_text("events/environmentalism_events.txt"))
        self.assertEqual(events.count("set_ideology = ideology:ideology_environmentalists"), 1)
        reckoning = _top(events, "environmentalism_events.4")
        self.assertIn("set_ideology = ideology:ideology_environmentalists", reckoning)
        for event, igs in ((3, ("ig_intelligentsia",)), (4, ("ig_trade_unions",)), (8, ("ig_intelligentsia",)),
                           (15, ("ig_industrialists",))):
            body = _top(events, f"environmentalism_events.{event}")
            for ig in igs:
                with self.subTest(event=event, ig=ig):
                    self.assertRegex(body, rf"ig:{ig} \?= \{{\s*add_modifier = \{{\s*"
                                           r"name = environmentalist_leader_pull_modifier\s*days = long_modifier_time")


class LosingWarTest(unittest.TestCase):
    """#1447: losing a war counts blockades and enemy pressure, in both triggers alike."""

    def setUp(self):
        self.nuke = _top(_strip_comments(_text("common/scripted_triggers/nuke_triggers.txt")), "is_losing_war_against")
        self.nd = _strip_comments(_text("common/scripted_triggers/nuclear_deterrence_triggers.txt"))

    def test_both_triggers_read_the_same_four_tests(self):
        twin = _top(self.nd, "nd_is_losing_war_to")
        for body, who in ((self.nuke, "ROOT"), (twin, "scope:nd_lw_self")):
            with self.subTest(who=who):
                self.assertIn("enemy_occupation >= 0.25", body)
                self.assertIn("num_significant_battles >= 5", body)
                self.assertIn("size_weighted_won_battles_fraction = { target = PREV value < 0.35 }", body)
                self.assertIn(f"blockaded_gdp_share = {{ target = {who} value >= 0.25 }}", body)
                self.assertIn(f"enemy_pressure = {{ target = {who} value >= 0.5 }}", body)
        self.assertNotIn("ROOT", twin)

    def test_a_stalled_goal_threatens_the_core_only_while_losing(self):
        core = _top(self.nd, "nd_core_threatened_by")
        self.assertRegex(core, r"OR = \{\s*NOT = \{\s*any_scope_war = \{\s*is_war_participant = \$ENEMY\$\s*"
                               r"has_stalled_state_wargoal_against = scope:nd_ct_self\s*\}\s*\}\s*"
                               r"nd_is_losing_war_to = \{ ENEMY = \$ENEMY\$ \}\s*\}")


class WorldClimateTest(unittest.TestCase):
    """#1448: one contextless entry declares Climate Warming for every country."""

    def setUp(self):
        self.world = _top(_strip_comments(_text("common/journal_entries/je_world_climate.txt")), "je_world_climate")

    def test_the_world_entry_declares_it(self):
        self.assertRegex(self.world, r"(?m)^\tcontext = none$")
        self.assertRegex(self.world, r"should_be_involved = \{\s*always = yes\s*\}")
        self.assertRegex(self.world, r"scaling_modifiers_while_active = \{\s*modifier = global_warming\s*"
                                     r"value = \{\s*value = temperature_anomaly_display\s*min = 0\s*\}\s*\}")
        self.assertRegex(self.world, r"possible = \{\s*temperature_anomaly_display >= 0\.1\s*\}")
        self.assertRegex(self.world, r"is_shown_when_inactive = \{\s*has_game_rule = global_warming_enabled\s*\}")
        # A contextless entry ignores disable_evaluation, and 1.15 logs so at load (2026-11-06).
        self.assertNotIn("disable_evaluation", self.world)
        self.assertIn("can_revolution_inherit = no", self.world)

    def test_the_country_entry_no_longer_does(self):
        country = _strip_comments(_text("common/journal_entries/je_global_warming.txt"))
        self.assertNotRegex(country, r"modifier = global_warming\b")

    def test_its_value_reads_no_country(self):
        """The value's root is no country on a contextless entry: the anomaly reads globals only."""
        values = _strip_comments(_text("common/script_values/extra_script_values.txt"))
        felt = _top(values, "temperature_anomaly_display")
        for name in ("gw_unmasked_temperature", "gw_aerosol_mask"):
            self.assertIn(name, felt)
        unmasked = _top(values, "gw_unmasked_temperature")
        mask = _top(_strip_comments(_text("common/script_values/global_warming_aerosol_values.txt")),
                    "gw_aerosol_mask")
        for body in (felt, unmasked, mask):
            self.assertNotRegex(body, r"\b(?:owner|capital|ROOT|root|gdp|has_variable|var:)\b")

    def test_readers_and_the_fallback(self):
        triggers = _strip_comments(_text("common/scripted_triggers/global_warming_triggers.txt"))
        self.assertRegex(_top(triggers, "gw_warming_felt"), r"is_involved_in_journal_entry = je_world_climate")
        self.assertRegex(self.world, r"on_monthly_pulse = \{\s*effect = \{\s*"
                                     r"gw_world_climate_involve_missing_effect = yes\s*\}\s*\}")
        effects = _strip_comments(_text("common/scripted_effects/global_warming_effects.txt"))
        involve = _top(effects, "gw_world_climate_involve_missing_effect")
        self.assertIn("NOT = { is_involved_in_journal_entry = je_world_climate }", involve)
        self.assertIn("add_involved_country = scope:gw_wc_missing", involve)

    def test_the_self_check_runs_from_the_global_pulse(self):
        pulse = _block(_strip_comments(_text("common/on_actions/extra_on_actions.txt")),
                       "global_warming_events_on_action = {")
        rule = _block(pulse, "if = {")
        self.assertIn("has_game_rule = global_warming_enabled", rule)
        self.assertIn("gw_world_climate_selfcheck_effect = yes", rule)
        effects = _text("common/scripted_effects/global_warming_effects.txt")
        check = _top(effects, "gw_world_climate_selfcheck_effect")
        self.assertIn("TE_SELF_CHECK OK gw_world_climate", check)
        self.assertIn("TE_SELF_CHECK BROKEN gw_world_climate", check)
        self.assertIn("modifier:state_harvest_condition_wildfire_duration_mult", check)
        # The field it reads is Climate Warming's alone, at 0.5 a degree, which the expected value restates.
        warming = _top(_strip_comments(_text("common/static_modifiers/extra_modifiers.txt")), "global_warming")
        self.assertIn("state_harvest_condition_wildfire_duration_mult = 0.5", warming)
        others = 0
        for path in (ROOT / "common").rglob("*.txt"):
            others += _strip_comments(path.read_text(encoding="utf-8-sig")).count(
                "state_harvest_condition_wildfire_duration_mult =")
        self.assertEqual(others, 1)
        values = _strip_comments(_text("common/script_values/global_warming_values.txt"))
        self.assertRegex(_top(values, "gw_wc_selfcheck_expected"),
                         r"value = temperature_anomaly_display\s*multiply = 0\.5")

    def test_loc(self):
        loc = _all_loc()
        for key in ("je_world_climate", "je_world_climate_reason"):
            self.assertIn(key, loc)


class MilitaryReachTest(unittest.TestCase):
    """#1450: six checks read has_military_reach where army size or "both coastal" stood in."""

    SITES = (
        ("common/scripted_triggers/decolonization_war_triggers.txt", "decol_iw_can_intervene", "te_reach_realistic"),
        ("common/scripted_triggers/nuclear_exchange_triggers.txt", "nd_conventionally_outmatched_by",
         "te_reach_ship_match"),
        ("common/scripted_triggers/nuclear_exchange_triggers.txt", "nd_conventionally_outmatches",
         "te_reach_ship_match"),
        ("common/scripted_triggers/irredentism_triggers.txt", "irr_target_reachable", "te_reach_union_link"),
        ("common/script_values/un_mission_values.txt", "un_mission_ai_join_score", "te_reach_realistic"),
        ("common/scripted_triggers/misc_triggers.txt", "te_target_militarily_weaker", "te_reach_ship_match"),
    )

    def test_each_site_reads_it(self):
        for path, name, threshold in self.SITES:
            with self.subTest(site=name):
                body = _top(_strip_comments(_text(path)), name)
                reach = _block(body, "has_military_reach = {")
                self.assertIn(threshold, reach)
                self.assertRegex(reach, r"target = \S+")

    def test_the_fight_option_reads_it(self):
        events = _strip_comments(_text("events/decolonization_events.txt"))
        fight = _block(events[events.index("name = decolonization_events.70.c"):], "ai_chance = {")
        self.assertRegex(fight, r"has_military_reach = \{\s*target = scope:decol_iw_territory\s*"
                                r"min_reach = te_reach_realistic\s*\}")

    def test_both_coastal_is_gone(self):
        body = _top(_strip_comments(_text("common/scripted_triggers/irredentism_triggers.txt")), "irr_target_reachable")
        self.assertNotIn("is_coastal", body)
        self.assertIn("is_adjacent_to_country = ROOT", body)

    def test_thresholds(self):
        values = _strip_comments(_text("common/script_values/te_military_reach_values.txt"))
        self.assertRegex(values, r"(?m)^te_reach_realistic = 0\.4$")
        self.assertRegex(values, r"(?m)^te_reach_union_link = 0\.2$")
        self.assertRegex(values, r"(?m)^te_reach_ship_match = 1$")

    def test_bomber_range_is_kept(self):
        """Strike range, not army reach (the issue's one exception)."""
        effects = _strip_comments(_text("common/scripted_effects/nuclear_deterrence_effects.txt"))
        self.assertNotIn("has_military_reach", effects)


class InstitutionNamesTest(unittest.TestCase):
    """#1451: five ministries take era and government names, each with loc."""

    INSTITUTIONS = ("institution_ministry_of_war", "institution_national_bank", "institution_ministry_of_labor",
                    "institution_ministry_of_intelligence_and_security", "institution_ministry_of_propaganda")

    def test_each_has_a_dynamic_name_with_loc(self):
        text = _strip_comments(_text("common/institutions/extra_institutions.txt"))
        loc = _all_loc()
        for name in self.INSTITUTIONS:
            with self.subTest(institution=name):
                body = _top(text, name)
                dynamic = _block(body, "dynamic_name = {")
                self.assertIn("first_valid = {", dynamic)
                keys = re.findall(r"desc = (\w+)", dynamic)
                self.assertGreaterEqual(len(keys), 3)
                for key in keys:
                    self.assertTrue(key.startswith(name + "_"), key)
                    self.assertIn(key, loc)
                    self.assertNotEqual(loc[key][0], "te_unused_l_english.yml", key)

    def test_the_laws_it_reads_exist(self):
        text = _strip_comments(_text("common/institutions/extra_institutions.txt"))
        laws = set(re.findall(r"law_type:(\w+)", text))
        mod_laws = set()
        for path in (ROOT / "common" / "laws").glob("*.txt"):
            mod_laws |= set(re.findall(r"(?m)^(law_\w+) = \{", path.read_text(encoding="utf-8-sig")))
        vanilla = (ROOT / "vanilla_parsed" / "common" / "laws.json").read_text(encoding="utf-8")
        for law in sorted(laws):
            with self.subTest(law=law):
                self.assertTrue(law in mod_laws or f'"{law}"' in vanilla, law)


class FormalNamesTest(unittest.TestCase):
    """#1452: every mod formable tag has a formal name, filed with its name and adjective."""

    def test_every_tag_has_a_def_key(self):
        defs = _text("common/country_definitions/te_formable_countries.txt")
        tags = re.findall(r"(?m)^([A-Z][A-Z0-9]{2}) = \{", defs)
        self.assertEqual(len(tags), 10)
        loc = _all_loc()
        for tag in tags:
            with self.subTest(tag=tag):
                self.assertIn(f"{tag}_DEF", loc)
                self.assertEqual(loc[f"{tag}_DEF"][0], "te_formable_countries_l_english.yml")

    def test_organize_loc_keeps_def_keys(self):
        import tempfile
        from organize_loc import find_country_keys
        with tempfile.TemporaryDirectory() as td:
            defs = Path(td, "common", "country_definitions")
            defs.mkdir(parents=True)
            (defs / "x.txt").write_text("ABC = {\n}\n", encoding="utf-8-sig")
            self.assertIn("ABC_DEF", find_country_keys(td))


if __name__ == "__main__":
    unittest.main()
