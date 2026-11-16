"""The Research Commons power bloc identity (owner rulings, 2026-11-16).

docs/systems/mod_systems/power_blocs.md § Research Commons; design
docs/superpowers/specs/2026-11-16-power-bloc-identities-design.md § 6. Members stop
researching and send the leader 75% of their weekly innovation; the leader's cap rises by
a tenth of the pool; every member is granted what any member knows; leaving is hard and
costs research speed for ten years; the leader's share of the bloc's innovation drives
cohesion. These tests hold the pieces to each other, since the engine checks none of it.

Run: /home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_research_commons.py
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def entry(text, name):
    """The top-level `name = { ... }` entry's body, by brace depth, comments dropped."""
    text = strip_comments(text)
    start = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert start, name
    depth, i = 1, start.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[start.end():i - 1]


def inner(body, head):
    """The `head = { ... }` block inside body, by brace depth."""
    start = body.index(head) + len(head)
    depth, i = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(body[i], 0)
        i += 1
    return body[start:i - 1]


IDENTITIES = read("common/power_bloc_identities/extra_power_bloc_identities.txt")
VALUES = read("common/script_values/te_research_commons_values.txt")
EFFECTS = read("common/scripted_effects/te_research_commons_effects.txt")
TRIGGERS = read("common/scripted_triggers/te_research_commons_triggers.txt")
PRINCIPLES = read("common/power_bloc_principles/te_research_commons_principles.txt")
GROUPS = read("common/power_bloc_principle_groups/extra_power_bloc_principle_groups.txt")
MODIFIERS = read("common/static_modifiers/te_research_commons_modifiers.txt")
JE = read("common/journal_entries/je_research_commons.txt")
ON_ACTIONS = read("common/on_actions/te_research_commons_on_actions.txt")
PLAYTEST = read("docs/testing/power-bloc-identities-playtest.md")


class IdentityTest(unittest.TestCase):
    body = entry(IDENTITIES, "identity_research_commons")

    def test_members_stop_researching(self):
        self.assertIn("country_tech_research_speed_mult = -10", inner(self.body, "non_leader_modifier = {"))
        self.assertNotIn("country_tech_research_speed_mult", inner(self.body, "member_modifier = {"))

    def test_hard_to_leave(self):
        leave = inner(self.body, "can_leave = {")
        self.assertIn("value <= 10", leave)
        self.assertIn("is_power_bloc_leader = yes", leave)

    def test_founding_and_unlock(self):
        self.assertIn("has_law = law_type:law_ministry_of_science", inner(self.body, "possible = {"))
        self.assertIn("has_technology_researched = intergovernmental_organizations", inner(self.body, "visible = {"))

    def test_cohesion_reads_the_leader_share(self):
        cohesion = inner(self.body, "cohesion = {")
        self.assertIn("scope:power_bloc.power_bloc_leader.var:te_rc_leader_share", cohesion)
        self.assertIn("has_variable = te_rc_leader_share", cohesion)
        self.assertIn("POWER_BLOC_COHESION_RESEARCH_SHARE", cohesion)

    def test_the_leader_keeps_its_ministry(self):
        law = entry(read("common/laws/extra_laws.txt"), "law_no_ministry_of_science")
        enact = inner(law, "can_enact = {")
        self.assertIn("is_power_bloc_leader = no", enact)
        self.assertIn("has_identity = identity:identity_research_commons", enact)


class ShareTest(unittest.TestCase):
    def test_owner_shares(self):
        self.assertRegex(VALUES, r"(?m)^te_rc_contribution_share = 0\.75$")
        self.assertRegex(VALUES, r"(?m)^te_rc_pool_cap_share = 0\.1$")

    def test_fixed_point_reads_add_units(self):
        gross = entry(VALUES, "te_rc_member_gross_adds")
        self.assertIn("value = modifier:country_weekly_innovation_add", gross)
        self.assertIn("add = var:te_rc_contributed", gross)
        self.assertNotIn("country_innovation", gross.replace("country_weekly_innovation_add", ""))

    def test_unit_modifiers(self):
        self.assertIn("country_weekly_innovation_add = -1", entry(MODIFIERS, "te_rc_contribution"))
        self.assertIn("country_weekly_innovation_add = 1", entry(MODIFIERS, "te_rc_pool"))
        self.assertIn("country_weekly_innovation_max_add = 1", entry(MODIFIERS, "te_rc_pool_cap"))
        self.assertIn("country_tech_research_speed_mult = -0.5", entry(MODIFIERS, "te_rc_institutes_left_behind"))
        self.assertIn("country_tech_spread_mult = -0.01", entry(MODIFIERS, "te_rc_technology_embargoed"))

    def test_entry_declares_the_three(self):
        body = entry(JE, "je_research_commons")
        for modifier, value in (("te_rc_contribution", "te_rc_contribution_value"),
                                ("te_rc_pool", "te_rc_pool_value"),
                                ("te_rc_pool_cap", "te_rc_pool_cap_value")):
            with self.subTest(modifier=modifier):
                self.assertRegex(body, rf"modifier = {modifier}\s+value = \{{ value = {value} \}}")
        self.assertIn("te_rc_in_commons = no", inner(body, "outcome = {"))
        self.assertIn("te_rc_entry_ended = yes", inner(body, "outcome = {"))

    def test_institutes_left_behind_runs_ten_years(self):
        self.assertIn("value = 120", entry(EFFECTS, "te_rc_start_institutes_left_behind"))
        self.assertIn("divide = 120", entry(VALUES, "te_rc_ilb_fraction"))
        apply = entry(EFFECTS, "te_rc_ilb_apply")
        self.assertLess(apply.index("remove_modifier = te_rc_institutes_left_behind"), apply.index("add_modifier"))


class GrantTest(unittest.TestCase):
    def test_grant_is_guarded(self):
        grant = entry(EFFECTS, "te_rc_grant")
        self.assertLess(grant.index("set_variable = te_rc_granting"), grant.index("add_technology_researched = $TECH$"))
        self.assertLess(grant.index("add_technology_researched = $TECH$"), grant.index("remove_variable = te_rc_granting"))

    def test_discovery_hooks_skip_a_grant(self):
        for rel, name in (("common/on_actions/headlines.txt", "extra_headlines_tech"),
                          ("common/on_actions/cultural_hegemony_on_actions.txt", "cultural_hegemony_tech_first_on_action"),
                          ("common/on_actions/extra_on_actions.txt", "agricultural_diffusion_on_action")):
            with self.subTest(hook=name):
                body = entry(read(rel), name)
                self.assertIn("NOT = { has_variable = te_rc_granting }", inner(body, "trigger = {"))

    def test_own_hook_does_not_recurse(self):
        hook = entry(ON_ACTIONS, "te_rc_on_acquired")
        self.assertLess(hook.index("has_variable = te_rc_granting"), hook.index("te_rc_share_acquired = yes"))
        self.assertIn("te_rc_monthly_country", entry(ON_ACTIONS, "on_monthly_pulse_country"))
        self.assertIn("te_rc_on_acquired", entry(ON_ACTIONS, "on_acquired_technology"))


class TechnologyControlsTest(unittest.TestCase):
    TIERS = {1: (5, None), 2: (10, None), 3: (15, 50), 4: (20, 75), 5: (25, 100)}

    def test_tiers_restate(self):
        for tier, (defense, strength) in self.TIERS.items():
            body = entry(PRINCIPLES, f"principle_technology_controls_{tier}")
            bloc = inner(body, "power_bloc_modifier = {")
            member = inner(body, "member_modifier = {")
            with self.subTest(tier=tier):
                self.assertIn("power_bloc_technology_controls_bool = yes", bloc)
                self.assertIn(f"country_covert_defense_economic_add = {defense}", member)
                self.assertIn(f"country_covert_defense_military_add = {defense}", member)
                self.assertIn(f"te_pb_principle_slot_free = {{ GROUP = principle_group_technology_controls }}",
                              inner(body, "possible = {"))
                if strength is None:
                    self.assertNotIn("embargo", bloc)
                else:
                    self.assertIn("power_bloc_can_use_technology_embargo_bool = yes", bloc)
                    self.assertIn(f"power_bloc_technology_embargo_strength_add = {strength}", bloc)

    def test_tooltip_strength_matches_the_script(self):
        points = entry(VALUES, "te_rc_embargo_points")
        self.assertRegex(points, r"principle_technology_controls_5 \}\s*\}\s*multiply = 100")
        self.assertRegex(points, r"principle_technology_controls_4 \}\s*\}\s*multiply = 75")
        self.assertRegex(points, r"else = \{\s*multiply = 50")
        self.assertIn("max = 50", points)

    def test_groups(self):
        for name in ("principle_group_technology_controls", "principle_group_education"):
            with self.subTest(group=name):
                self.assertIn("primary_for_identity = identity_research_commons", entry(GROUPS, name))
        self.assertIn("primary_for_identity = identity_research_commons",
                      entry(GROUPS, "INJECT:principle_group_advanced_research"))
        self.assertIn("unlocking_identity = identity_research_commons",
                      entry(GROUPS, "principle_group_technology_controls"))

    def test_science_aid_is_closed(self):
        articles = read("common/treaty_articles/extra_treaty_articles.txt")
        for name in ("science_aid", "science_aid_2"):
            with self.subTest(article=name):
                self.assertIn("te_rc_tech_controls_bars_aid = { TARGET = scope:other_country }",
                              inner(entry(articles, name), "possible = {"))
        self.assertIn("modifier:power_bloc_technology_controls_bool = yes", entry(TRIGGERS, "te_rc_tech_controls_bars_aid"))


class SelfCheckTest(unittest.TestCase):
    def test_each_self_check_is_on_the_play_test_list(self):
        names = set(re.findall(r"TE_SELF_CHECK (?:OK|BROKEN) (\w+)", EFFECTS))
        self.assertEqual(names, {"rc_contribution_lands", "rc_grant_lands", "rc_grant_hook", "rc_entry_add"})
        for name in names:
            with self.subTest(check=name):
                self.assertIn(f"`TE_SELF_CHECK … {name}`", PLAYTEST)


if __name__ == "__main__":
    unittest.main()
