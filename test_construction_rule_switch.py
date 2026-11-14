"""Direct construction follows free_market_construction_rule, and script owns Base Construction.

Two faults, both read in the running game on 2026-11-13 (docs/testing/direct-construction-playtest.md):

- **Base Construction came and went with the player's last lobby.** The Disabled setting applied it with
  `apply_modifier = all:te_direct_construction_base_modifier`. The engine applies such a line by the rules the
  player last applied in a lobby on their machine, not by the rules of the save being played: a save whose rule
  said Enabled got the Disabled setting's modifier, and a save switched to no culture merges got the merges
  setting's. So a direct game lost its 5 points (10 since #1768) once its player had set up any other game, and a market game
  gained them. Script adds the modifier now (te_direct_construction_ensure_base), and no rule setting of the mod
  may carry an `apply_modifier` line.
- **The conversion ran only when a game started.** A rule can be changed in a running game. A market game
  switched to Disabled kept its Construction Sectors and its market sites, each site with the capacity modifier
  of the market's last week (France's at -100%), so the country had Base Construction and nothing else, whatever
  it built. te_construction_market_follow_rule converts in either direction, every day.

Run: python3 -m unittest test_construction_rule_switch -v
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/te_construction_market_direct_effects.txt"
VALUES = ROOT / "common/script_values/te_construction_market_direct_values.txt"
PULSE_EVENTS = ROOT / "events/te_construction_market_pulse_events.txt"
PULSE_EFFECTS = ROOT / "common/scripted_effects/te_construction_market_pulse_effects.txt"
RULES = ROOT / "common/game_rules"
GROUPS = ROOT / "common/building_groups/te_construction_market_groups.txt"
BUILDINGS = ROOT / "common/buildings/te_construction_market_site.txt"
SITE_BUILDER = ROOT / "common/scripted_effects/te_construction_market_build_effects.txt"
SECTOR_BUILDER = ROOT / "common/scripted_effects/build_effects.txt"
PLAYTEST = ROOT / "docs/testing/direct-construction-playtest.md"
MODIFIERS = ROOT / "common/static_modifiers/te_construction_market_modifiers.txt"
BASE = "te_direct_construction_base_modifier"
SITE = "te_construction_market_site"
SECTOR = "building_construction_sector"
SITE_TIERS = ("wooden", "iron_frame", "steel_frame", "arc_welded", "reinforced_concrete", "advanced",
              "nanomaterial", "self_replicating")
SECTOR_TIERS = ("pm_wooden_buildings", "pm_iron_frame_buildings", "pm_steel_frame_buildings",
                "pm_arc_welded_buildings", "pm_reinforced_concrete_buildings", "pm_advanced_construction",
                "pm_nanomaterial_buildings", "pm_self_replicating_construction")


def code(path: Path) -> str:
    """The file's text without its comments (a `#` inside a quoted string is kept)."""
    out = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        quoted, kept = False, []
        for ch in line:
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                break
            kept.append(ch)
        out.append("".join(kept))
    return "\n".join(out)


def body(text: str, name: str) -> str:
    """The text between the braces of the top-level `name = { ... }`."""
    match = re.search(r"^%s\s*=\s*\{" % re.escape(name), text, re.M)
    if match is None:
        raise AssertionError("%s is not defined" % name)
    depth, start, quoted = 1, match.end(), False
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '"':
            quoted = not quoted
        elif quoted:
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    raise AssertionError("%s's braces do not close" % name)


def calls(text: str, name: str) -> bool:
    return re.search(r"(?<![\w.:])%s\s*=\s*yes\b" % re.escape(name), text) is not None


class NoRuleAppliesAModifierTest(unittest.TestCase):
    def test_no_rule_setting_carries_apply_modifier(self):
        for path in sorted(RULES.glob("*.txt")):
            with self.subTest(file=path.name):
                self.assertNotRegex(
                    code(path), r"(?<![\w.:])apply_modifier\s*=",
                    "a rule setting's apply_modifier follows the rules the player last applied in a lobby, not the "
                    "save's (read live, 2026-11-13): add the modifier from script under has_game_rule instead")


class BaseConstructionTest(unittest.TestCase):
    def setUp(self):
        self.effects = code(EFFECTS)

    def test_the_base_is_added_only_where_it_is_missing(self):
        ensure = body(self.effects, "te_direct_construction_ensure_base")
        self.assertRegex(ensure, r"NOT\s*=\s*\{\s*has_modifier\s*=\s*%s\s*\}" % BASE,
                         "a same-name add_modifier stacks: only a country without the base gets it")
        self.assertRegex(ensure, r"add_modifier\s*=\s*\{\s*name\s*=\s*%s\s*\}" % BASE)
        self.assertRegex(ensure, r"NOT\s*=\s*\{\s*is_country_type\s*=\s*decentralized\s*\}")

    def test_nothing_else_adds_it(self):
        added = re.findall(r"add_modifier\s*=\s*\{[^{}]*\bname\s*=\s*%s\b" % BASE, self.effects)
        self.assertEqual(len(added), 1, "te_direct_construction_ensure_base is the base's one add site")

    def test_the_weekly_pulse_and_the_conversion_ensure_it(self):
        for effect in ("te_direct_construction_on_weekly_pulse", "te_direct_construction_convert_all"):
            with self.subTest(effect=effect):
                self.assertTrue(calls(body(self.effects, effect), "te_direct_construction_ensure_base"))

    def test_country_setup_does_not_add_it(self):
        # Setup runs from history, where a rule read is not final: a lobby that then picks a market setting
        # would leave every country the modifier, and nothing converts a game that never was a direct one.
        setup = body(self.effects, "te_direct_construction_country_setup")
        self.assertFalse(calls(setup, "te_direct_construction_ensure_base"))

    def test_the_base_is_the_base_games_maximum_and_the_self_check_reads_it(self):
        # #1768: vanilla's country_gdp_construction gives 10 at most (the mod empties it), so the direct game's
        # flat base is 10. The self-check counts a holder under the base as under_base, so its threshold must be
        # the modifier's own value: under the old 5 a threshold left at 5 would pass a base that gave half.
        modifier = body(code(MODIFIERS), BASE)
        value = re.search(r"\bcountry_construction_add\s*=\s*([\d.]+)", modifier)
        self.assertIsNotNone(value)
        self.assertEqual(float(value.group(1)), 10.0)
        check = body(self.effects, "te_direct_construction_base_self_check")
        thresholds = re.findall(r"modifier:country_construction_add\s*<\s*([\d.]+)", check)
        self.assertEqual([float(t) for t in thresholds], [float(value.group(1))])

    def test_the_market_takes_it_away(self):
        remove = body(self.effects, "te_direct_construction_remove_base")
        self.assertRegex(remove, r"has_modifier\s*=\s*%s\b" % BASE)
        self.assertRegex(remove, r"remove_modifier\s*=\s*%s\b" % BASE)
        self.assertTrue(calls(body(self.effects, "te_direct_construction_revert_all"),
                              "te_direct_construction_remove_base"))
        # ... and weekly from any holder, in the market's own branch of the pulse.
        pulse = body(code(PULSE_EFFECTS), "te_construction_market_on_weekly_pulse")
        market = pulse[pulse.index("else_if"):]
        self.assertTrue(calls(market, "te_direct_construction_remove_base"))
        self.assertFalse(calls(pulse[:pulse.index("else_if")], "te_direct_construction_remove_base"))


class FollowRuleTest(unittest.TestCase):
    def setUp(self):
        self.effects = code(EFFECTS)
        self.follow = body(self.effects, "te_construction_market_follow_rule")

    def test_the_daily_pulse_follows_the_rule_before_the_weekly_bodies(self):
        pulse = body(code(PULSE_EVENTS), "te_construction_market_pulse_events.1")
        follow = re.search(r"te_construction_market_follow_rule\s*=\s*yes", pulse)
        fan_out = re.search(r"id\s*=\s*te_construction_market_pulse_events\.3", pulse)
        self.assertIsNotNone(follow, "the daily pulse calls te_construction_market_follow_rule")
        self.assertIsNotNone(fan_out)
        self.assertLess(follow.start(), fan_out.start(),
                        "the buildings follow the rule before the countries' weekly bodies read them")
        # Not inside the weekly test: a rule changed on Monday is followed on Tuesday.
        weekly = re.search(r"if\s*=\s*\{\s*limit\s*=\s*\{\s*te_construction_market_pulse_count_modulo_7\s*=\s*0",
                           pulse)
        self.assertIsNotNone(weekly)
        self.assertLess(follow.start(), weekly.start())

    def test_it_converts_in_both_directions(self):
        self.assertTrue(calls(self.follow, "te_direct_construction_convert_all"))
        self.assertTrue(calls(self.follow, "te_direct_construction_revert_all"))
        self.assertRegex(self.follow, r"te_free_market_construction_off\s*=\s*yes")
        self.assertRegex(self.follow, r"NOT\s*=\s*\{\s*has_global_variable\s*=\s*te_direct_construction_converted\s*\}")

    def test_the_marker_says_which_model_the_buildings_are_in(self):
        convert = body(self.effects, "te_direct_construction_convert_all")
        revert = body(self.effects, "te_direct_construction_revert_all")
        self.assertRegex(convert, r"set_global_variable\s*=\s*\{\s*name\s*=\s*te_direct_construction_converted")
        self.assertRegex(revert, r"remove_global_variable\s*=\s*te_direct_construction_converted")
        # The sector's build permission reads the same marker.
        sector = body(code(BUILDINGS), "REPLACE:%s" % SECTOR)
        self.assertEqual(len(re.findall(r"has_global_variable\s*=\s*te_direct_construction_converted", sector)), 2)

    def test_the_game_start_conversion_is_the_same_one(self):
        start = body(self.effects, "te_direct_construction_convert_sectors")
        self.assertTrue(calls(start, "te_direct_construction_convert_all"))
        self.assertRegex(start, r"NOT\s*=\s*\{\s*has_global_variable\s*=\s*te_direct_construction_converted\s*\}")

    def test_a_converted_game_sweeps_up_sectors_weekly(self):
        self.assertRegex(self.follow, r"te_construction_market_pulse_count_modulo_7\s*=\s*0")
        self.assertTrue(calls(self.follow, "te_direct_construction_convert_state"))

    def test_each_switch_logs_its_self_check(self):
        self.assertEqual(len(re.findall(r"te_direct_construction_switch_self_check\s*=\s*yes", self.follow)), 2)

    def test_each_switch_counts_what_it_should_make(self):
        # Review, 2026-11-13: the verdicts read only what was left over, so a switch whose create_building was
        # refused everywhere (no site, or one sector for 381 sites) still read OK.
        for effect in ("te_direct_construction_convert_all", "te_direct_construction_revert_all"):
            with self.subTest(effect=effect):
                raised = re.search(r"set_global_variable\s*=\s*\{\s*name\s*=\s*te_dc_switch_expected\s+value\s*=\s*0"
                                   r"\s*\}\s*set_global_variable\s*=\s*\{\s*name\s*=\s*te_dc_switch_capped\s+"
                                   r"value\s*=\s*0\s*\}\s*%s\s*=\s*yes\s*"
                                   r"te_direct_construction_switch_cost_scaling\s*=\s*yes\s*"
                                   r"te_direct_construction_switch_self_check\s*=\s*yes" % effect, self.follow)
                self.assertIsNotNone(raised, "the counters are up from before %s to the self-check" % effect)
        count = body(self.effects, "te_direct_construction_count_made")
        self.assertRegex(count, r"has_global_variable\s*=\s*te_dc_switch_expected")
        for effect in ("te_direct_construction_convert_state", "te_direct_construction_revert_state_site"):
            with self.subTest(effect=effect):
                self.assertTrue(calls(body(self.effects, effect), "te_direct_construction_count_made"))
        check = body(self.effects, "te_direct_construction_switch_self_check")
        self.assertRegex(check, r"global_var:te_dc_check_sites\s*>=\s*te_dc_check_expected")
        self.assertRegex(check, r"global_var:te_dc_check_sectors\s*>=\s*te_dc_check_expected")
        self.assertRegex(check, r"remove_global_variable\s*=\s*te_dc_switch_expected")

    def test_a_switch_applies_the_new_models_cost_scaling_at_once(self):
        # The market's price and goods per point multiply by the live construction_cost_scaling_mult whether or
        # not the modifier is in force, so a switch that only cleared the modifiers left a rich country's Fixed
        # Budget buying fewer points than it paid for until its yearly pulse (a second session's review of #1763).
        switch = body(self.effects, "te_direct_construction_switch_cost_scaling")
        # Through a hidden country event, never called from the fan-out: the switch runs in one country's
        # pulse event, and add_modifier's multiplier resolves against ROOT, so a direct call would give every
        # country that one country's scaling until its own yearly pulse.
        # Not to decentralized countries, as the weekly and game-start passes leave them out.
        self.assertRegex(switch, r"every_country\s*=\s*\{\s*limit\s*=\s*\{\s*NOT\s*=\s*\{\s*is_country_type\s*=\s*"
                                 r"decentralized\s*\}\s*\}\s*trigger_event\s*=\s*\{\s*id\s*=\s*"
                                 r"te_construction_market_recalc_events\.4\s*\}\s*\}")
        self.assertFalse(calls(switch, "te_cc_apply_scaling"))
        events = code(ROOT / "events/te_construction_market_recalc_events.txt")
        event = body(events, "te_construction_market_recalc_events.4")
        self.assertRegex(event, r"type\s*=\s*country_event")
        self.assertRegex(event, r"immediate\s*=\s*\{\s*te_cc_apply_scaling\s*=\s*yes\s*\}")
        self.assertNotRegex(event, r"\btrigger\s*=")
        cost = code(ROOT / "common/scripted_effects/te_construction_cost_effects.txt")
        apply = body(cost, "te_cc_apply_scaling")
        for modifier in ("construction_cost_scaling", "construction_cost_scaling_direct"):
            self.assertRegex(apply, r"add_modifier\s*=\s*\{\s*name\s*=\s*%s\s" % modifier)
        # The yearly pulse sets the modifier through the same effect, after its reading of the slack.
        pulse = body(code(ROOT / "common/on_actions/extra_on_actions.txt"), "construction_cost_scaling_on_action")
        self.assertRegex(pulse, r"te_cc_yearly_update\s*=\s*yes\s*te_cc_apply_scaling\s*=\s*yes")
        # Not from the conversion itself, which also runs at game start, before any country's first reading.
        for effect in ("te_direct_construction_convert_all", "te_direct_construction_revert_all"):
            self.assertFalse(calls(body(self.effects, effect), "te_cc_apply_scaling"))
        # What the reader multiplies by is the live value.
        target = code(ROOT / "common/script_values/te_construction_market_target_values.txt")
        self.assertRegex(body(target, "te_construction_market_goods_per_point"),
                         r"add\s*=\s*construction_cost_scaling_mult")

    def test_the_stray_sector_walk_is_every_fourth_week(self):
        # It reads every building in the world, and nothing can queue a sector once the conversion has closed it.
        weekly = self.follow[self.follow.index("te_construction_market_pulse_count_modulo_7"):]
        walk = weekly.index("every_country")
        self.assertRegex(weekly[:walk], r"te_construction_market_pulse_count_modulo_28\s*=\s*0")
        pulse_values = code(ROOT / "common/script_values/te_construction_market_pulse_values.txt")
        self.assertRegex(body(pulse_values, "te_construction_market_pulse_count_modulo_28"), r"modulo\s*=\s*28")
        # The base's self-check stays weekly: it is not inside the walk's test.
        month = re.search(r"if\s*=\s*\{\s*limit\s*=\s*\{\s*te_construction_market_pulse_count_modulo_28", weekly)
        depth, i = 0, month.end()
        while True:                     # to the end of the `if` that opened at month.start()
            if weekly[i] == "{":
                depth += 1
            elif weekly[i] == "}":
                if depth == 0:
                    break
                depth -= 1
            i += 1
        self.assertNotIn("te_direct_construction_base_self_check", weekly[month.start():i])
        self.assertIn("te_direct_construction_base_self_check", weekly[i:])

    def test_the_weekly_pass_only_cancels_a_sector_under_construction(self):
        # A state's staffed site is not rebuilt (and its workers let go) to cancel a sector that never stood.
        weekly = self.follow[self.follow.index("te_construction_market_pulse_count_modulo_7"):]
        self.assertRegex(weekly, r"if\s*=\s*\{\s*limit\s*=\s*\{\s*has_building\s*=\s*%s\s*\}\s*"
                                 r"te_direct_construction_convert_state\s*=\s*yes\s*\}\s*"
                                 r"else\s*=\s*\{\s*remove_building\s*=\s*%s\s*\}" % (SECTOR, SECTOR))


class ConversionTest(unittest.TestCase):
    def setUp(self):
        self.effects = code(EFFECTS)
        self.values = code(VALUES)
        self.state = body(self.effects, "te_direct_construction_convert_state")
        self.back = body(self.effects, "te_direct_construction_revert_state_site")

    def test_the_site_is_made_new_so_no_market_modifier_survives(self):
        # The capacity modifier sits on the site building; a site raised in place would keep it.
        removed = self.state.index("remove_building = %s" % SITE)
        built = self.state.index("te_construction_market_build_specified_level")
        self.assertLess(removed, built)
        self.assertRegex(self.state, r"SPEC_TYPE\s*=\s*%s\b" % SITE)

    def test_a_sector_under_construction_is_cancelled_too(self):
        # has_building is false for a building whose first level is still being built.
        self.assertRegex(self.state, r"any_scope_building\s*=\s*\{\s*is_building_type\s*=\s*%s\s*\}\s*\}\s*"
                                     r"remove_building\s*=\s*%s" % (SECTOR, SECTOR))
        # ... and a site under construction, so the new site is never made over a building that is there.
        self.assertRegex(self.state, r"any_scope_building\s*=\s*\{\s*is_building_type\s*=\s*%s\s*\}\s*\}\s*"
                                     r"remove_building\s*=\s*%s" % (SITE, SITE))
        self.assertRegex(self.back, r"any_scope_building\s*=\s*\{\s*is_building_type\s*=\s*%s\s*\}\s*\}\s*"
                                    r"remove_building\s*=\s*%s" % (SECTOR, SECTOR))
        # The walk finds them the same way: has_building would miss a state whose only sector is at level 0.
        convert = body(self.effects, "te_direct_construction_convert_all")
        self.assertRegex(convert, r"any_scope_building\s*=\s*\{\s*OR\s*=\s*\{\s*is_building_type\s*=\s*%s\s+"
                                  r"is_building_type\s*=\s*%s\s*\}\s*\}" % (SITE, SECTOR))

    def test_a_market_sites_own_level_is_not_capacity(self):
        level = body(self.values, "te_direct_construction_convert_uncapped_level")
        self.assertRegex(level, r"has_global_variable\s*=\s*te_dc_from_market\s*\}\s*subtract\s*=\s*1")
        self.assertRegex(body(self.values, "te_direct_construction_convert_target_level"),
                         r"value\s*=\s*te_direct_construction_convert_uncapped_level")
        convert = body(self.effects, "te_direct_construction_convert_all")
        raised = convert.index("name = te_dc_from_market")
        lowered = convert.index("remove_global_variable = te_dc_from_market")
        walked = convert.index("te_direct_construction_convert_state = yes")
        self.assertLess(raised, walked)
        self.assertLess(walked, lowered)

    def test_every_tier_is_carried_both_ways(self):
        for tier, (site_pm, sector_pm) in enumerate(zip(SITE_TIERS, SECTOR_TIERS), start=1):
            with self.subTest(tier=tier):
                self.assertRegex(self.state, r"te_direct_construction_activate_site_tier\s*=\s*\{\s*TIER\s*=\s*%d\s+"
                                             r"PM\s*=\s*pm_te_direct_construction_%s\s*\}" % (tier, site_pm))
                self.assertRegex(self.back, r"te_direct_construction_activate_sector_tier\s*=\s*\{\s*TIER\s*=\s*%d\s+"
                                            r"PM\s*=\s*%s\s*\}" % (tier, sector_pm))
                if tier > 1:        # tier 1 is the default the others are read over
                    self.assertRegex(self.state, r"BUILDING\s*=\s*%s\s+TIER\s*=\s*%d\s+PM\s*=\s*%s\s*\}"
                                     % (SECTOR, tier, sector_pm))
                    self.assertRegex(self.back, r"BUILDING\s*=\s*%s\s+TIER\s*=\s*%d\s+"
                                                r"PM\s*=\s*pm_te_direct_construction_%s\s*\}" % (SITE, tier, site_pm))

    def test_the_level_caps_are_what_the_builders_can_make(self):
        site_cases = [int(n) for n in re.findall(r"^\t\t(\d+)\s*=\s*\{", code(SITE_BUILDER), re.M)]
        sector_cases = [int(n) for n in re.findall(r"^\t\t(\d+)\s*=\s*\{", code(SECTOR_BUILDER), re.M)]
        site_cap = int(re.search(r"max\s*=\s*(\d+)",
                                 body(self.values, "te_direct_construction_convert_target_level")).group(1))
        sector_cap = int(re.search(r"max\s*=\s*(\d+)",
                                   body(self.values, "te_direct_construction_revert_target_level")).group(1))
        self.assertEqual(site_cap, max(site_cases))
        self.assertEqual(sector_cap, max(sector_cases))

    def test_a_state_cut_to_the_builders_cap_is_counted(self):
        # The self-check counts buildings, so a capped state read OK with nothing to say what the switch cost.
        for effect, uncapped, capped in (
                ("te_direct_construction_convert_state", "te_direct_construction_convert_uncapped_level",
                 "te_direct_construction_convert_target_level"),
                ("te_direct_construction_revert_state_site", "te_direct_construction_revert_uncapped_level",
                 "te_direct_construction_revert_target_level")):
            with self.subTest(effect=effect):
                text = body(self.effects, effect)
                counted = re.search(r"%s\s*>\s*%s\s*\}\s*te_direct_construction_count_capped\s*=\s*yes"
                                    % (uncapped, capped), text)
                self.assertIsNotNone(counted)
                # Read while the buildings still stand: both values read their levels.
                self.assertLess(counted.start(), text.index("remove_building"))
        check = body(self.effects, "te_direct_construction_switch_self_check")
        self.assertEqual(check.count("capped=[THIS.ScriptValue('te_dc_check_capped')|0]"), 4)
        self.assertRegex(check, r"remove_global_variable\s*=\s*te_dc_switch_capped")

    def test_a_site_kept_for_want_of_urbanization_is_a_level_one_market_site(self):
        # The market sizes each site for a share of the week's purchase, and a site gives that times its level.
        revert = body(self.effects, "te_direct_construction_revert_all")
        kept = re.search(r"b:%s\.level\s*>\s*1\s*\}\s*remove_building\s*=\s*%s\s*"
                         r"te_construction_market_place_site\s*=\s*yes" % (SITE, SITE), revert)
        self.assertIsNotNone(kept)
        # After the walk that turns every other site into a sector: only a kept one is left to find.
        self.assertGreater(kept.start(), revert.index("te_direct_construction_revert_state_site = yes"))

    def test_the_way_back_makes_a_government_owned_sector(self):
        self.assertRegex(self.back, r"extended_timeline_build_specified_building_level\s*=\s*\{\s*"
                                    r"SPEC_TYPE\s*=\s*%s\s+SPEC_LEVEL\s*=\s*var:te_dc_convert_level\s+"
                                    r"SPEC_OWNER\s*=\s*owner\s*\}" % SECTOR)
        # ... and only where the owner can have one: create_building checks the sector's technology.
        revert = body(self.effects, "te_direct_construction_revert_all")
        self.assertRegex(revert, r"has_technology_researched\s*=\s*urbanization")

    def test_the_cost_scaling_of_the_other_model_goes_with_it(self):
        clear = body(self.effects, "te_direct_construction_clear_cost_scaling")
        for line in ("remove_modifier = construction_cost_scaling", "remove_modifier = construction_cost_scaling_direct",
                     "remove_variable = prior_construction_scaling"):
            with self.subTest(line=line):
                self.assertRegex(clear, r"%s\b" % re.escape(line))
        for effect in ("te_direct_construction_convert_all", "te_direct_construction_revert_all"):
            with self.subTest(effect=effect):
                self.assertTrue(calls(body(self.effects, effect), "te_direct_construction_clear_cost_scaling"))

    def test_the_ai_site_guard_holds_from_the_conversion(self):
        self.assertRegex(self.state, r"name\s*=\s*te_dc_site_level\s+value\s*=\s*var:te_dc_convert_level")
        self.assertRegex(self.state, r"name\s*=\s*te_dc_site_tier\s+value\s*=\s*var:te_dc_target_tier")
        # The market has no use for the record, and a stale one would restore levels at the next switch.
        self.assertRegex(self.back, r"remove_variable\s*=\s*te_dc_site_level")

    def test_both_switches_forget_every_states_record(self):
        # Review, 2026-11-13: only the states a switch walked lost their record. One left on a state with no site
        # (its AI owner removed it that week, or the owner had no Urbanization) outlived the market period, and at
        # the next switch to direct construction the guard built a site of the old level from nothing.
        forget = body(self.effects, "te_direct_construction_forget_site_record")
        for name in ("te_dc_site_level", "te_dc_site_tier"):
            self.assertRegex(forget, r"remove_variable\s*=\s*%s\b" % name)
        every_state = r"every_scope_state\s*=\s*\{\s*te_direct_construction_forget_site_record\s*=\s*yes\s*\}"
        convert = body(self.effects, "te_direct_construction_convert_all")
        revert = body(self.effects, "te_direct_construction_revert_all")
        self.assertRegex(convert, every_state)
        self.assertRegex(revert, every_state)
        # Before the conversion writes the new records, and after the way back has read the old ones.
        self.assertLess(re.search(every_state, convert).start(),
                        convert.index("te_direct_construction_convert_state = yes"))
        self.assertGreater(re.search(every_state, revert).start(),
                           revert.index("te_direct_construction_revert_state_site = yes"))


class LensTest(unittest.TestCase):
    """The production lens lists a building whose group names a lens and whose can_build_government holds: with
    `lens = development` the Development tab offered the Construction Site in a direct game and not in a market
    game (screenshots, 2026-11-13)."""

    def test_the_sites_group_is_in_the_development_lens(self):
        group = body(code(GROUPS), "te_construction_market_bg")
        self.assertRegex(group, r"(?<![\w.:])lens\s*=\s*development\b")

    def test_a_market_game_still_lets_nobody_build_one(self):
        site = body(code(BUILDINGS), SITE)
        permission = body(site, "\tcan_build_government")
        self.assertRegex(permission, r"te_free_market_construction_off\s*=\s*yes")
        self.assertRegex(permission, r"has_global_variable\s*=\s*te_cm_placing_site")
        self.assertEqual(len(re.findall(r"=\s*yes|has_global_variable", permission)), 2,
                         "nothing else opens the site to construction in a market game")
        self.assertRegex(body(site, "\tcan_build_private"), r"always\s*=\s*no")


class SelfCheckTest(unittest.TestCase):
    CHECKS = ("direct_base_construction", "construction_rule_switch")

    def test_each_check_has_both_verdicts(self):
        text = EFFECTS.read_text(encoding="utf-8-sig")
        for name in self.CHECKS:
            for verdict in ("OK", "BROKEN"):
                with self.subTest(check=name, verdict=verdict):
                    self.assertIn('debug_log = "TE_SELF_CHECK %s %s ' % (verdict, name), text)

    def test_the_playtest_list_names_them_with_their_fallbacks(self):
        text = PLAYTEST.read_text(encoding="utf-8")
        for name in self.CHECKS:
            with self.subTest(check=name):
                self.assertIn("`TE_SELF_CHECK … %s`" % name, text)


if __name__ == "__main__":
    unittest.main()
