"""What the systems leave behind when their game rule is switched off mid-game (2026-11-08).

A rule can be changed from the screen that changes country, and `disable_evaluation` touches only inactive records, so
every rule-pruned journal entry ends on its rule (test_journal_entry_shape.py, RuleEndTreeTest). Ending the entry takes
the modifiers on it; these tests pin the teardowns of what the systems put elsewhere, where a later edit could quietly
undo them:

- the Tax Code's way out restates, without the rule, the tests that map an enacted code to its vanilla law;
- the UN's rule-off end is a dissolution's quiet half, with no record, cooldown, event or vacuum;
- the Space Race's rule-off stop clears a milestone's running variables without marking a programme lost;
- World War's rule-off helper clears every variable the completion outcome clears, and the latches;
- Grand Monuments' rule-off pass keeps the upkeep exemption on the building;
- the monetary layer, when the banking rule goes from Full to Simplified (the entry stays), strips its managed modifiers,
  forgets the skipped steps' state so step 0 seeds it neutral again, and switches off the full-system tools (#1507);
  its treaty articles end on the rule (owner, 2026-11-12), and the teardown clears the backstop roles they leave.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from je_multiplier_scope_audit import Node, parse_text

ROOT = Path(__file__).resolve().parent


def top(rel: str) -> dict[str, Node]:
    path = ROOT / rel
    return {n.key: n for n in parse_text(path.read_text(encoding="utf-8-sig"), rel)[0] if n.children}


def walk(nodes: list[Node]):
    for node in nodes:
        yield node
        yield from walk(node.children)


def keys(node: Node) -> set[str]:
    return {n.key for n in walk(node.children)}


def pairs(nodes: list[Node]) -> list[tuple[str, str | None]]:
    return [(n.key, n.value) for n in nodes]


class TaxCodeWayOutTest(unittest.TestCase):
    """te_tax_leave_code_for_rule picks the vanilla law te_tax_code_equivalent_* name, in the same order."""

    @classmethod
    def setUpClass(cls):
        cls.triggers = top("common/scripted_triggers/te_tax_triggers.txt")
        effect = top("common/scripted_effects/te_tax_migration_effects.txt")["te_tax_leave_code_for_rule"]
        carrier = next(c for c in effect.children if c.key == "if")
        cls.branches = [c for c in carrier.children if c.key in ("if", "else_if", "else")]

    def restated(self, trigger: str) -> list[tuple[str, str | None]]:
        """The trigger's tests without the rule and the carrier, which the way out has already established."""
        dropped = {("te_tax_code_full", "yes"), ("has_law", "law_type:law_te_tax_code")}
        return [t for t in pairs(self.triggers[trigger].children) if t not in dropped]

    def branch(self, index: int) -> tuple[list[tuple[str, str | None]], str]:
        node = self.branches[index]
        limit = next((c for c in node.children if c.key == "limit"), None)
        law = next(c.value for c in node.children if c.key == "activate_law")
        return (pairs(limit.children) if limit else []), law

    def test_the_branches_follow_the_equivalence(self):
        expected = [
            ("te_tax_code_counts_as_graduated", "law_type:law_graduated_taxation"),
            ("te_tax_code_counts_as_proportional", "law_type:law_proportional_taxation"),
            ("te_tax_code_counts_as_per_capita", "law_type:law_per_capita_based_taxation"),
        ]
        self.assertEqual([b.key for b in self.branches], ["if", "else_if", "else_if", "else_if", "else"])
        for index, (trigger, law) in enumerate(expected):
            with self.subTest(trigger=trigger):
                self.assertEqual(self.branch(index), (self.restated(trigger), law))
        land = [t for t in self.restated("te_tax_code_equivalent_land_based") if not t[0].startswith("NOT")]
        self.assertEqual(self.branch(3), (land, "law_type:law_land_based_taxation"))
        self.assertEqual(self.branch(4), ([], "law_type:law_consumption_based_taxation"))

    def test_the_net_runs_only_where_a_code_was(self):
        net = top("common/on_actions/te_tax_on_actions.txt")["te_tax_rule_off_net"]
        limit = next(n for n in walk(net.children) if n.key == "limit")
        self.assertIn(("NOT", None), pairs(limit.children))
        marker = next(c for c in limit.children if c.key == "OR")
        self.assertIn("has_law", keys(marker))
        # An on_actions list is bare names, which the parser skips: read the hook's text.
        text = (ROOT / "common/on_actions/te_tax_on_actions.txt").read_text(encoding="utf-8-sig")
        hook = text[text.index("on_monthly_pulse_country = {"):]
        self.assertIn("te_tax_rule_off_net", hook[:hook.index("}")])


class UnitedNationsQuietEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = top("common/scripted_effects/un_ladder_effects.txt")

    def test_a_dissolution_runs_the_quiet_half(self):
        dissolve = self.effects["un_dissolve"]
        self.assertEqual(dissolve.children[-1].key, "un_dissolve_quiet")
        quiet = keys(self.effects["un_dissolve_quiet"])
        self.assertIn("un_dissolve_strip_country", quiet)
        self.assertIn("un_hq_enforce_single_building", quiet)

    def test_the_rule_off_end_records_no_dissolution(self):
        """No record, cooldown, world-moment event or vacuum: the UN ends as if it had never been founded."""
        for name in ("un_dissolve_quiet", "un_stop_for_rule"):
            body = self.effects[name]
            with self.subTest(effect=name):
                self.assertNotIn("trigger_event", keys(body))
                self.assertNotIn("add_modifier", keys(body))
                written = {n.value for n in walk(body.children) if n.key == "name"}
                self.assertFalse(written & {"un_dissolution_count", "un_refounding_cooldown",
                                            "un_dissolved_year", "un_refounding_open_year"})

    def test_the_global_pulse_stops_with_the_rule(self):
        pulse = top("common/on_actions/un_on_actions.txt")["un_global_authority_on_action"]
        effect = next(c for c in pulse.children if c.key == "effect")
        first = effect.children[0]
        self.assertEqual(first.key, "if")
        self.assertIn("un_stop_for_rule", keys(first))
        for block in effect.children[1:]:
            limit = next(c for c in block.children if c.key == "limit")
            with self.subTest(line=block.line):
                self.assertIn(("has_game_rule", "united_nations_enabled"), pairs(limit.children))


class SpaceRaceStopTest(unittest.TestCase):
    def test_a_rule_off_stop_is_not_a_programme_loss(self):
        effects = top("common/scripted_effects/space_race_effects.txt")
        stop = effects["sr_stop_for_rule_base"]
        written = {n.value for n in walk(stop.children) if n.key in ("set_variable", "remove_variable")}
        self.assertFalse(any(v and v.startswith("sr_closed_by_loss") for v in written))
        self.assertNotIn("sr_report_program_loss", keys(stop))
        self.assertNotIn("set_variable", keys(stop))
        removed = {n.value for n in walk(stop.children) if n.key == "remove_variable"}
        cleanup = {n.value for n in walk(effects["sr_cleanup_milestone_variables_effect"].children)
                   if n.key == "remove_variable"}
        self.assertLessEqual(cleanup, removed, "the stop clears what a loss's cleanup clears")


class WorldWarStopTest(unittest.TestCase):
    def test_the_stop_clears_what_completion_clears(self):
        effects = top("common/scripted_effects/te_event_agency_ww_effects.txt")
        stop = {n.value for n in walk(effects["ww_stop_for_rule"].children) if n.key == "remove_variable"}
        self.assertIn("ww_clear_outcome_latches", keys(effects["ww_stop_for_rule"]))
        entry = top("common/journal_entries/world_war_je.txt")["je_world_war"]
        completion = next(o for o in entry.children if o.key == "outcome")
        effect = next(c for c in completion.children if c.key == "effect")
        cleared = {c.value for c in effect.children if c.key == "remove_variable"}
        self.assertEqual(cleared - stop, set())


class GrandMonumentsRuleOffTest(unittest.TestCase):
    def test_the_rule_off_pass_keeps_the_upkeep_exemption(self):
        effects = top("common/scripted_effects/gm_effects.txt")
        local = {n.value for n in effects["gm_remove_local_effect_modifiers"].children if n.key == "remove_modifier"}
        self.assertIn("gm_local_tourism", local)
        self.assertNotIn("gm_upkeep", local)
        self.assertNotIn("gm_upkeep", {n.value for n in walk(effects["gm_remove_local_effect_modifiers"].children)})
        full = effects["gm_remove_local_modifiers"]
        self.assertIn(("gm_remove_local_effect_modifiers", "yes"), pairs(full.children))
        self.assertIn("gm_upkeep", {n.value for n in walk(full.children)})
        pass_ = top("common/on_actions/monument_events_on_actions.txt")["gm_state_rule_off_on_action"]
        self.assertIn(("gm_system_enabled", "no"), pairs(next(c for c in pass_.children if c.key == "trigger").children))


class MonetaryRuleSwitchTest(unittest.TestCase):
    """te_monetary_settle_rule_switch: Full to Simplified mid-game (te_monetary_rule_switch_effects.txt)."""

    @classmethod
    def setUpClass(cls):
        cls.effects = top("common/scripted_effects/te_monetary_effects.txt")
        cls.effects.update(top("common/scripted_effects/te_monetary_fx_effects.txt"))
        cls.effects.update(top("common/scripted_effects/te_monetary_arrangement_effects.txt"))
        cls.effects.update(top("common/scripted_effects/te_monetary_union_effects.txt"))
        cls.switch = top("common/scripted_effects/te_monetary_rule_switch_effects.txt")
        cls.leave = cls.switch["te_monetary_leave_full_system"]

    def test_the_switch_runs_before_step_0_and_0b(self):
        order = [n.key for n in self.effects["te_monetary_monthly_update"].children]
        self.assertEqual(order[0], "te_monetary_settle_rule_switch")
        self.assertLess(order.index("te_monetary_settle_rule_switch"), order.index("te_monetary_init_variables"))
        self.assertLess(order.index("te_monetary_settle_rule_switch"), order.index("te_monetary_settle_modifier_home"))

    def test_only_a_country_that_ran_full_leaves_it(self):
        settle = self.switch["te_monetary_settle_rule_switch"]
        full = next(c for c in settle.children if c.key == "if")
        self.assertIn(("te_mon_full_system", "yes"), pairs(next(c for c in full.children if c.key == "limit").children))
        self.assertIn(("set_variable", "te_mon_ran_full"), [(n.key, n.value) for n in walk(full.children)])
        left = next(c for c in settle.children if c.key == "else_if")
        self.assertIn(("has_variable", "te_mon_ran_full"),
                      pairs(next(c for c in left.children if c.key == "limit").children))
        self.assertIn(("remove_variable", "te_mon_ran_full"), pairs(left.children))
        self.assertIn(("te_monetary_leave_full_system", "yes"), pairs(left.children))

    def seeded(self) -> set[str]:
        """Every variable step 0 sets only when it is missing, through the init effects it calls."""
        found: set[str] = set()
        seen: set[str] = set()

        def visit(name: str) -> None:
            if name in seen or name not in self.effects:
                return
            seen.add(name)
            for node in walk(self.effects[name].children):
                if node.key == "if":
                    limit = next((c for c in node.children if c.key == "limit"), None)
                    if limit is None:
                        continue
                    for nott in (c for c in limit.children if c.key == "NOT"):
                        found.update(c.value for c in nott.children if c.key == "has_variable")
                if node.value == "yes":
                    visit(node.key)

        visit("te_monetary_init_variables")
        return found

    def test_step_0_seeds_every_variable_the_switch_forgets(self):
        forgotten = [next(c.value for c in n.children if c.key == "VAR")
                     for n in walk(self.leave.children) if n.key == "te_mon_forget_variable"]
        self.assertGreaterEqual(len(forgotten), 20)
        for name in ("te_inflation", "te_inflation_expected", "te_fx_index", "te_monetisation_level",
                     "te_mon_stance_band", "te_mon_anchor_kind", "te_peg_suspended_months"):
            self.assertIn(name, forgotten)
        missing = set(forgotten) - self.seeded()
        self.assertEqual(missing, set(), "step 0 would not seed these again, so they would stay unset")

    def test_the_managed_modifiers_go_through_a_change_of_home(self):
        home = next(n for n in self.leave.children if n.key == "if")
        self.assertIn("te_mon_mod_home", {c.value for c in walk(home.children) if c.key == "name"})
        self.assertIn("-1", {c.value for c in walk(home.children) if c.key == "value"})
        # Step 9 re-adds the rate paid on the same pulse, because it is missing.
        step9 = self.effects["te_monetary_apply_interest_modifiers"]
        self.assertIn("te_mon_mod_has", keys(step9))

    def test_every_full_system_tool_is_switched_off(self):
        buttons = top("common/scripted_buttons/timeline_extended_scripted_buttons.txt")
        tools = set()
        for name, node in buttons.items():
            visible = next((c for c in node.children if c.key == "visible"), None)
            if visible is not None and ("banking_external_available", "yes") in pairs(visible.children):
                tools.add(name.removeprefix("cb_"))
        self.assertEqual(len(tools), 5)
        called = {n.key for n in walk(self.leave.children)}
        for tool in sorted(tools):
            with self.subTest(tool=tool):
                self.assertIn(f"banking_effect_cb_disable_{tool}", called)

    def requirement_triggers(self, rel: str, article: str) -> list[Node]:
        node = top(rel)[article]
        return [t for r in node.children if r.key == "requirement_to_maintain"
                for t in r.children if t.key == "trigger"]

    def test_the_backstop_articles_end_on_the_rule(self):
        # Owner, 2026-11-12: a signed swap line, guarantee or receivership ends when the rule leaves Full,
        # through a failed requirement (no breaker), not by a withdrawal the teardown would charge to a party.
        for rel, article in (("common/treaty_articles/111_swap_line.txt", "swap_line"),
                             ("common/treaty_articles/112_lender_of_last_resort.txt", "lender_of_last_resort"),
                             ("common/treaty_articles/114_debt_receivership.txt", "debt_receivership")):
            with self.subTest(article=article):
                found = [t for t in self.requirement_triggers(rel, article)
                         if ("te_mon_full_system", "yes") in pairs(walk(t.children))]
                self.assertEqual(len(found), 1, "one requirement on te_mon_full_system")

    def test_the_pegs_end_on_the_rule_through_the_anchors_dial(self):
        triggers = top("common/scripted_triggers/te_monetary_triggers.txt")
        triggers.update(top("common/scripted_triggers/te_monetary_arrangement_triggers.txt"))
        self.assertIn(("te_mon_has_dial", "yes"), pairs(triggers["te_mon_can_be_anchor"].children))
        self.assertIn(("te_mon_full_system", "yes"), pairs(triggers["te_mon_has_dial"].children))
        for rel, article in (("common/treaty_articles/110_currency_peg.txt", "currency_peg"),
                             ("common/treaty_articles/113_imposed_currency_peg.txt", "imposed_currency_peg")):
            with self.subTest(article=article):
                reads = [n for t in self.requirement_triggers(rel, article) for n in walk(t.children)]
                self.assertIn(("te_mon_can_be_anchor", "yes"), pairs(reads))

    def test_the_teardown_settles_the_line_then_clears_the_roles(self):
        self.assertIn(("te_mon_leave_backstop_treaties", "yes"), pairs(self.leave.children))
        step4 = self.switch["te_mon_leave_backstop_treaties"]
        order = [n for n in step4.children if n.key == "if"]
        settle = next(i for i, n in enumerate(order) if "te_mon_effect_swap_settle" in keys(n))
        cleared = {}
        for i, n in enumerate(order):
            for sv in (c for c in walk(n.children) if c.key == "set_variable" and c.children):
                fields = dict(pairs(sv.children))
                if fields.get("value") == "0":
                    cleared[fields["name"]] = i
        for role in ("te_mon_swap_recipient", "te_mon_lolr_ward", "te_mon_receivership",
                     "te_mon_receivership_clear_months"):
            with self.subTest(role=role):
                self.assertIn(role, cleared)
                self.assertGreater(cleared[role], settle, "settle while the role still names the lender")
        self.assertIn(("te_mon_clear_backstop_rows", "yes"), pairs(step4.children))

    def test_a_save_switched_before_step_4_still_runs_it(self):
        # No te_mon_ran_full mark (switched between #1667 and the requirement), but a role still held off Full.
        settle = self.switch["te_monetary_settle_rule_switch"]
        last = [c for c in settle.children if c.key == "else_if"][-1]
        limit = next(c for c in last.children if c.key == "limit")
        roles = {n.key for n in walk(limit.children)}
        for role in ("te_mon_is_swap_recipient", "te_mon_is_lolr_ward", "te_mon_is_under_receivership"):
            with self.subTest(role=role):
                self.assertIn(role, roles)
        self.assertEqual(pairs(c for c in last.children if c.key != "limit"),
                         [("te_mon_leave_backstop_treaties", "yes")])
        # Idempotent: step 4 clears every role that opens the branch.
        step4 = self.switch["te_mon_leave_backstop_treaties"]
        cleared = {dict(pairs(sv.children)).get("name") for sv in walk(step4.children)
                   if sv.key == "set_variable" and sv.children}
        self.assertLessEqual({"te_mon_swap_recipient", "te_mon_lolr_ward", "te_mon_receivership"}, cleared)

    def test_the_self_check_reads_a_month_later_once_a_game(self):
        settle = self.switch["te_monetary_settle_rule_switch"]
        branches = [c for c in settle.children if c.key == "else_if"]
        self.assertEqual(len(branches), 3)
        later = branches[1]
        self.assertIn(("has_variable", "te_mon_switch_treaty_check"),
                      pairs(next(c for c in later.children if c.key == "limit").children))
        self.assertIn(("te_mon_selfcheck_switch_treaties", "yes"), pairs(later.children))
        self.assertIn("te_mon_switch_treaty_check",
                      {n.value for n in walk(self.switch["te_mon_leave_backstop_treaties"].children)})
        check = self.switch["te_mon_selfcheck_switch_treaties"]
        self.assertEqual(sum(1 for n in walk(check.children) if n.key == "debug_log"), 2)
        self.assertIn("te_mon_switch_treaties_selfcheck_logged", {n.value for n in walk(check.children)})
        # This parser keeps no quoted string whole, so the two lines are read from the text.
        text = (ROOT / "common/scripted_effects/te_monetary_rule_switch_effects.txt").read_text(encoding="utf-8-sig")
        for verdict in ("OK", "BROKEN"):
            self.assertIn(f'debug_log = "TE_SELF_CHECK {verdict} mon_rule_switch_treaties', text)


if __name__ == "__main__":
    unittest.main()
