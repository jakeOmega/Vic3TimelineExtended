"""Tests for event_context_audit (M_NEW2 #2/#3 and the PR #418 system-bypass class)."""

import os
import tempfile
import unittest

import event_context_audit as eca

LOC_HEADER = "﻿l_english:\n"


def _event(eid: str, body: str = "", hidden: bool = False) -> str:
    head = "\thidden = yes\n" if hidden else (
        f"\ttitle = {eid}.t\n\tdesc = {eid}.d\n\tflavor = {eid}.f\n")
    return f"{eid} = {{\n\ttype = country_event\n{head}{body}\n}}\n"


class EventContextAuditTests(unittest.TestCase):
    def _mod(self, files: dict[str, str], loc: dict[str, str] | None = None) -> str:
        td = tempfile.mkdtemp()
        for rel, content in files.items():
            p = os.path.join(td, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8-sig") as f:
                f.write(content)
        if loc:
            p = os.path.join(td, "localization", "english", "t_l_english.yml")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(LOC_HEADER)
                for k, v in loc.items():
                    f.write(f' {k}:0 "{v}"\n')
        return td

    def _flags(self, mod: str, check: str | None = None, unreviewed_only: bool = True):
        out = set()
        for f in eca.audit(mod).flags:
            if check and f.check != check:
                continue
            if unreviewed_only and f.exemption:
                continue
            out.add((f.check, f.event_id))
        return out

    # -- system_ungated ---------------------------------------------------

    PULSE = (
        "on_yearly_pulse_country = {\n\ton_actions = { my_pulse }\n}\n"
        "my_pulse = {\n\teffect = {\n\t\trandom_list = {\n\t\t\t90 = { }\n"
        "\t\t\t10 = { trigger_event = { id = flav.1 } }\n\t\t}\n\t}\n}\n"
    )
    SPY_LOC = {"flav.1.t": "The Spy", "flav.1.d": "A foreign spy was caught in the capital."}

    def test_system_vocab_without_gate_is_flagged(self):
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/p.txt": self.PULSE}, self.SPY_LOC)
        self.assertEqual(self._flags(mod, "system_ungated"), {("system_ungated", "flav.1")})

    def test_event_trigger_reading_game_rule_is_gated(self):
        body = "\ttrigger = { has_game_rule = covert_warfare_disabled }\n"
        mod = self._mod({"events/flav.txt": _event("flav.1", body),
                         "common/on_actions/p.txt": self.PULSE}, self.SPY_LOC)
        self.assertEqual(self._flags(mod, "system_ungated"), set())

    def test_dispatch_under_gated_limit_is_gated(self):
        pulse = (
            "my_pulse = {\n\teffect = {\n\t\tif = {\n"
            "\t\t\tlimit = { has_game_rule = covert_warfare_disabled }\n"
            "\t\t\ttrigger_event = { id = flav.1 }\n\t\t}\n\t}\n}\n"
        )
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/p.txt": pulse}, self.SPY_LOC)
        self.assertEqual(self._flags(mod, "system_ungated"), set())

    def test_else_branch_inherits_the_if_chain_guard(self):
        pulse = (
            "my_pulse = {\n\teffect = {\n"
            "\t\tif = {\n\t\t\tlimit = { has_game_rule = covert_warfare_enabled }\n"
            "\t\t\tcovert_do_the_real_thing = yes\n\t\t}\n"
            "\t\telse = {\n\t\t\ttrigger_event = { id = flav.1 }\n\t\t}\n\t}\n}\n"
        )
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/p.txt": pulse}, self.SPY_LOC)
        self.assertEqual(self._flags(mod, "system_ungated"), set())

    def test_one_ungated_site_among_gated_ones_still_flags(self):
        pulse = (
            "my_pulse = {\n\teffect = {\n\t\tif = {\n"
            "\t\t\tlimit = { has_game_rule = covert_warfare_disabled }\n"
            "\t\t\ttrigger_event = { id = flav.1 }\n\t\t}\n"
            "\t\ttrigger_event = { id = flav.1 }\n\t}\n}\n"
        )
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/p.txt": pulse}, self.SPY_LOC)
        self.assertEqual(self._flags(mod, "system_ungated"), {("system_ungated", "flav.1")})

    def test_event_in_system_owned_file_is_gated(self):
        mod = self._mod({"events/covert_warfare_events.txt": _event("flav.1"),
                         "common/on_actions/p.txt": self.PULSE}, self.SPY_LOC)
        self.assertEqual(self._flags(mod, "system_ungated"), set())

    def test_gate_propagates_through_precursor_event(self):
        pre = _event("flav.2", "\ttrigger = { has_journal_entry = je_covert_warfare }\n"
                               "\toption = { trigger_event = { id = flav.1 days = 3 } }\n")
        loc = dict(self.SPY_LOC, **{"flav.2.t": "x", "flav.2.d": "y"})
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre}, loc)
        self.assertEqual(self._flags(mod, "system_ungated"), set())

    def test_gate_propagates_through_scripted_effect(self):
        eff = "my_helper = {\n\ttrigger_event = { id = flav.1 }\n}\n"
        pulse = (
            "my_pulse = {\n\teffect = {\n\t\tif = {\n"
            "\t\t\tlimit = { has_game_rule = covert_warfare_disabled }\n"
            "\t\t\tmy_helper = yes\n\t\t}\n\t}\n}\n"
        )
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/scripted_effects/h.txt": eff,
                         "common/on_actions/p.txt": pulse}, self.SPY_LOC)
        self.assertEqual(self._flags(mod, "system_ungated"), set())

    def test_merged_engine_hook_is_not_owned_by_first_defining_file(self):
        # on_monthly_pulse_country is declared in many files and merged; the
        # alphabetically-first one belonging to a system must not make every
        # chain hanging off the hook "owned" by that system.
        sys_hook = "on_monthly_pulse_country = {\n\ton_actions = { cultural_hegemony_tick }\n}\n"
        pulse = ("on_monthly_pulse_country = {\n\ton_actions = { my_pulse }\n}\n"
                 "my_pulse = {\n\teffect = { trigger_event = { id = flav.1 } }\n}\n")
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/cultural_hegemony_on_actions.txt": sys_hook,
                         "common/on_actions/zz_misc.txt": pulse},
                        {"flav.1.t": "Soft Power", "flav.1.d": "Our cultural hegemony grows."})
        self.assertEqual(self._flags(mod, "system_ungated"), {("system_ungated", "flav.1")})

    def test_flavor_text_mentions_do_not_count(self):
        loc = {"flav.1.t": "Quiet", "flav.1.d": "Nothing happens.",
               "flav.1.f": "\\\"Like the espionage of old,\\\" he said."}
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/p.txt": self.PULSE}, loc)
        self.assertEqual(self._flags(mod, "system_ungated"), set())

    # -- unchosen_self_action ------------------------------------------

    CAMPAIGN_LOC = {"flav.1.t": "Turns", "flav.1.d": "They answered our information campaign."}

    def test_self_action_fired_into_other_scope_is_flagged(self):
        pre = _event("flav.2", "\timmediate = { random_rival_country = { save_scope_as = rival } }\n"
                               "\toption = { scope:rival = { trigger_event = { id = flav.1 } } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"),
                         {("unchosen_self_action", "flav.1")})

    def test_self_action_from_own_option_is_clean(self):
        pre = _event("flav.2", "\toption = { trigger_event = { id = flav.1 days = 3 } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"), set())

    def test_self_action_from_decision_is_clean(self):
        dec = "my_decision = {\n\twhen_taken = { trigger_event = { id = flav.1 } }\n}\n"
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/decisions/d.txt": dec}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"), set())

    def test_self_action_from_law_hook_is_clean(self):
        oa = ("on_law_enactment_pass = {\n\ton_actions = { my_law_oa }\n}\n"
              "my_law_oa = {\n\teffect = { trigger_event = { id = flav.1 } }\n}\n")
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/o.txt": oa}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"), set())

    def test_self_action_from_pulse_is_flagged(self):
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/p.txt": self.PULSE}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"),
                         {("unchosen_self_action", "flav.1")})

    def test_random_list_weights_are_not_scope_switches(self):
        pre = _event("flav.2", "\toption = { random_list = { 50 = { trigger_event = { id = flav.1 } } "
                               "50 = { } } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"), set())

    def test_parameterised_helper_dispatch_is_resolved(self):
        eff = "send_it = {\n\t$WHO$ = {\n\t\ttrigger_event = { id = $EVENT$ popup = yes }\n\t}\n}\n"
        pre = _event("flav.2", "\timmediate = { random_rival_country = { save_scope_as = rival } }\n"
                               "\toption = { send_it = { WHO = scope:rival EVENT = flav.1 } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre,
                         "common/scripted_effects/h.txt": eff}, self.CAMPAIGN_LOC)
        g = eca.build_graph(mod)
        sites = g.sites_by_event.get("flav.1", [])
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0].switches, ["scope:rival"])
        self.assertNotIn("$EVENT$", g.sites_by_event)
        self.assertEqual(self._flags(mod, "unchosen_self_action"),
                         {("unchosen_self_action", "flav.1")})

    # -- imputed_foreign_action ------------------------------------------

    def _imputing(self, desc: str, option: str) -> str:
        loc = {"flav.2.t": "x", "flav.2.d": desc, "flav.1.t": "t", "flav.1.d": "d"}
        body = ("\timmediate = {\n\t\trandom_country = {\n"
                "\t\t\tlimit = { has_diplomatic_pact = { who = ROOT type = rivalry } }\n"
                "\t\t\tsave_scope_as = rival\n\t\t}\n\t}\n" + option)
        return self._mod({"events/flav.txt": _event("flav.2", body) + _event("flav.1")}, loc)

    def test_imputed_action_with_consequence_is_flagged(self):
        mod = self._imputing("[SCOPE.sCountry('rival').GetName] has launched a campaign.",
                             "\toption = { scope:rival = { trigger_event = { id = flav.1 } } }\n")
        self.assertEqual(self._flags(mod, "imputed_foreign_action"),
                         {("imputed_foreign_action", "flav.2")})

    def test_relations_consequence_counts(self):
        mod = self._imputing("[SCOPE.sCountry('rival').GetName] has launched a campaign.",
                             "\toption = { change_relations = { country = scope:rival value = -20 } }\n")
        self.assertEqual(self._flags(mod, "imputed_foreign_action"),
                         {("imputed_foreign_action", "flav.2")})

    def test_imputed_action_without_consequence_is_clean(self):
        mod = self._imputing("[SCOPE.sCountry('rival').GetName] has launched a campaign.",
                             "\toption = { add_modifier = { name = x } }\n")
        self.assertEqual(self._flags(mod, "imputed_foreign_action"), set())

    def test_consequence_without_attribution_is_clean(self):
        mod = self._imputing("We could pressure [SCOPE.sCountry('rival').GetName].",
                             "\toption = { scope:rival = { trigger_event = { id = flav.1 } } }\n")
        self.assertEqual(self._flags(mod, "imputed_foreign_action"), set())

    # -- suppression / scope --------------------------------------------

    def test_tagged_reviewed_comment_suppresses_only_its_check(self):
        body = "\t# REVIEWED 2026-09-25 (system_ungated): fallback flavour, deliberately rule-agnostic\n"
        loc = {"flav.1.t": "Spy", "flav.1.d": "A foreign spy spoiled our information campaign."}
        mod = self._mod({"events/flav.txt": _event("flav.1", body),
                         "common/on_actions/p.txt": self.PULSE}, loc)
        self.assertEqual(self._flags(mod), {("unchosen_self_action", "flav.1")})
        reviewed = {(f.check, f.event_id) for f in eca.audit(mod).flags if f.exemption}
        self.assertEqual(reviewed, {("system_ungated", "flav.1")})

    def test_all_tag_suppresses_every_check(self):
        body = "\t# REVIEWED 2026-09-25 (all): console harness\n"
        loc = {"flav.1.t": "Spy", "flav.1.d": "A foreign spy spoiled our information campaign."}
        mod = self._mod({"events/flav.txt": _event("flav.1", body),
                         "common/on_actions/p.txt": self.PULSE}, loc)
        self.assertEqual(self._flags(mod), set())

    def test_untagged_opening_line_reviewed_does_not_suppress(self):
        # The opening-line form belongs to orphaned_event / loc_coverage /
        # event_image; it must not silently hide this audit's flags too.
        src = _event("flav.1").replace("flav.1 = {", "flav.1 = { # REVIEWED 2026-09-25: orphan ok", 1)
        mod = self._mod({"events/flav.txt": src, "common/on_actions/p.txt": self.PULSE},
                        self.SPY_LOC)
        self.assertEqual(self._flags(mod, "system_ungated"), {("system_ungated", "flav.1")})

    def test_tagged_comment_is_invisible_to_the_line_audits_regex(self):
        import event_image_audit as eia
        self.assertIsNone(eia.parse_reviewed_comment(
            "# REVIEWED 2026-09-25 (system_ungated): rationale"))

    def test_hidden_events_are_skipped(self):
        # The hidden event carries flaggable text; only the hidden skip saves it.
        src = ("flav.1 = {\n\ttype = country_event\n\thidden = yes\n"
               "\ttitle = flav.1.t\n\tdesc = flav.1.d\n}\n")
        mod = self._mod({"events/flav.txt": src, "common/on_actions/p.txt": self.PULSE},
                        self.SPY_LOC)
        self.assertEqual(self._flags(mod), set())
        shown = self._mod({"events/flav.txt": src.replace("\thidden = yes\n", ""),
                           "common/on_actions/p.txt": self.PULSE}, self.SPY_LOC)
        self.assertEqual(self._flags(shown, "system_ungated"), {("system_ungated", "flav.1")})

    def test_console_events_are_skipped(self):
        loc = {"te_debug_x.1.t": "Spy", "te_debug_x.1.d": "A foreign spy was caught."}
        mod = self._mod({"events/te_debug_x_events.txt": _event("te_debug_x.1"),
                         "common/on_actions/p.txt": self.PULSE.replace("flav.1", "te_debug_x.1")}, loc)
        self.assertEqual(self._flags(mod), set())

    def test_report_renders_every_check(self):
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/p.txt": self.PULSE}, self.SPY_LOC)
        report = eca.render_report(eca.audit(mod))
        for c in eca.CHECKS:
            self.assertIn(f"## `{c}`", report)
        self.assertIn("flav.1", report)

    # -- review follow-ups ------------------------------------------------

    def test_fixed_event_into_parameterised_scope_is_a_switch(self):
        # `notify_it = { $WHO$ = { trigger_event = { id = flav.1 } } }` called with
        # WHO = scope:rival: the .106 pattern hidden behind a helper.
        eff = "notify_it = {\n\t$WHO$ = {\n\t\ttrigger_event = { id = flav.1 }\n\t}\n}\n"
        pre = _event("flav.2", "\toption = { notify_it = { WHO = scope:rival } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre,
                         "common/scripted_effects/h.txt": eff}, self.CAMPAIGN_LOC)
        sites = eca.build_graph(mod).sites_by_event["flav.1"]
        self.assertEqual([s.switches for s in sites], [["scope:rival"]])
        self.assertEqual(self._flags(mod, "unchosen_self_action"),
                         {("unchosen_self_action", "flav.1")})

    def test_unsubstituted_parameter_scope_counts_as_a_switch(self):
        # The caller passes no WHO, so `$WHO$ = { … }` stays an unknown scope;
        # from an own option it would otherwise read as chosen.
        eff = "notify_it = {\n\t$WHO$ = {\n\t\ttrigger_event = { id = flav.1 }\n\t}\n}\n"
        pre = _event("flav.2", "\toption = { notify_it = yes }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre,
                         "common/scripted_effects/h.txt": eff}, self.CAMPAIGN_LOC)
        sites = eca.build_graph(mod).sites_by_event["flav.1"]
        self.assertEqual([s.switches for s in sites], [["$WHO$"]])
        self.assertEqual(self._flags(mod, "unchosen_self_action"),
                         {("unchosen_self_action", "flav.1")})

    def test_self_forwarding_helper_terminates(self):
        eff = "loop_send = {\n\ttrigger_event = { id = $EVENT$ }\n\tloop_send = { EVENT = $EVENT$ }\n}\n"
        pre = _event("flav.2", "\toption = { loop_send = { EVENT = flav.1 } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre,
                         "common/scripted_effects/h.txt": eff}, self.CAMPAIGN_LOC)
        g = eca.build_graph(mod)  # must return
        self.assertEqual([(s.entity, s.in_option) for s in g.sites_by_event["flav.1"]],
                         [("flav.2", True)])
        self.assertFalse(any("$" in k for k in g.sites_by_event))

    def test_renamed_forwarding_resolves(self):
        inner = "a_send = {\n\t$WHO$ = { trigger_event = { id = $EVENT$ } }\n}\n"
        outer = "b_fwd = {\n\ta_send = { WHO = $TARGET$ EVENT = $EV$ }\n}\n"
        pre = _event("flav.2", "\toption = { b_fwd = { TARGET = scope:rival EV = flav.1 } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre,
                         "common/scripted_effects/h.txt": inner + outer}, self.CAMPAIGN_LOC)
        sites = eca.build_graph(mod).sites_by_event.get("flav.1", [])
        self.assertEqual([(s.entity, s.switches) for s in sites], [("flav.2", ["scope:rival"])])

    def test_on_action_cycle_does_not_crash(self):
        oa = ("on_yearly_pulse_country = {\n\ton_actions = { oa_a }\n}\n"
              "oa_a = {\n\ton_actions = { oa_b }\n\teffect = { trigger_event = { id = flav.1 } }\n}\n"
              "oa_b = {\n\ton_actions = { oa_a }\n}\n")
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/o.txt": oa}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"),
                         {("unchosen_self_action", "flav.1")})

    def test_console_files_are_not_dispatch_sources(self):
        dbg = _event("te_debug_x.1", "\toption = { scope:rival = { trigger_event = { id = flav.1 } } }\n")
        dec = "my_decision = {\n\twhen_taken = { trigger_event = { id = flav.1 } }\n}\n"
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "events/te_debug_x_events.txt": dbg,
                         "common/decisions/d.txt": dec}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"), set())

    def test_forwarded_event_parameter_resolves_through_helpers(self):
        inner = "send_it = {\n\ttrigger_event = { id = $EVENT$ }\n}\n"
        outer = "offer_it = {\n\tsend_it = { EVENT = $EVENT$ }\n}\n"
        pre = _event("flav.2", "\toption = { offer_it = { EVENT = flav.1 } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre,
                         "common/scripted_effects/h.txt": inner + outer}, self.CAMPAIGN_LOC)
        g = eca.build_graph(mod)
        self.assertEqual([(s.entity, s.in_option) for s in g.sites_by_event["flav.1"]],
                         [("flav.2", True)])
        self.assertFalse(any("$" in k for k in g.sites_by_event))

    def test_dispatch_cycle_does_not_flag_gated_events(self):
        # A gated pulse fires A; A's option fires B; B's option fires A.
        pulse = ("my_pulse = {\n\teffect = {\n\t\tif = {\n"
                 "\t\t\tlimit = { has_game_rule = covert_warfare_disabled }\n"
                 "\t\t\ttrigger_event = { id = flav.1 }\n\t\t}\n\t}\n}\n")
        a = _event("flav.1", "\toption = { trigger_event = { id = flav.2 } }\n")
        b = _event("flav.2", "\toption = { trigger_event = { id = flav.1 } }\n")
        loc = dict(self.SPY_LOC, **{"flav.2.t": "Spies", "flav.2.d": "Another spy was caught."})
        for order in ((a, b), (b, a)):
            mod = self._mod({"events/flav.txt": order[0] + order[1],
                             "common/on_actions/p.txt": pulse}, loc)
            self.assertEqual(self._flags(mod, "system_ungated"), set())

    def test_else_if_inherits_the_if_chain_guard(self):
        pulse = (
            "my_pulse = {\n\teffect = {\n"
            "\t\tif = {\n\t\t\tlimit = { has_game_rule = covert_warfare_enabled }\n"
            "\t\t\tcovert_do_the_real_thing = yes\n\t\t}\n"
            "\t\telse_if = {\n\t\t\tlimit = { always = yes }\n"
            "\t\t\ttrigger_event = { id = flav.1 }\n\t\t}\n\t}\n}\n"
        )
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/on_actions/p.txt": pulse}, self.SPY_LOC)
        self.assertEqual(self._flags(mod, "system_ungated"), set())

    def test_optional_assignment_scope_is_a_switch(self):
        pre = _event("flav.2", "\toption = { scope:rival ?= { trigger_event = { id = flav.1 } } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.1") + pre}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"),
                         {("unchosen_self_action", "flav.1")})

    def test_journal_entry_tick_is_unchosen(self):
        je = "je_x = {\n\ton_monthly_pulse = { effect = { trigger_event = { id = flav.1 } } }\n}\n"
        mod = self._mod({"events/flav.txt": _event("flav.1"),
                         "common/journal_entries/je_x.txt": je}, self.CAMPAIGN_LOC)
        self.assertEqual(self._flags(mod, "unchosen_self_action"),
                         {("unchosen_self_action", "flav.1")})

    def test_pre_attribution_names_the_picked_country_as_source(self):
        mod = self._imputing("The evidence points to [SCOPE.sCountry('rival').GetName].",
                             "\toption = { scope:rival = { trigger_event = { id = flav.1 } } }\n")
        self.assertEqual(self._flags(mod, "imputed_foreign_action"),
                         {("imputed_foreign_action", "flav.2")})
        mod = self._imputing("We received a proposal of union from [SCOPE.sCountry('rival').GetName].",
                             "\toption = { change_relations = { country = scope:rival value = -10 } }\n")
        self.assertEqual(self._flags(mod, "imputed_foreign_action"),
                         {("imputed_foreign_action", "flav.2")})

    def test_every_iterator_is_not_a_country_picker(self):
        loc = {"flav.2.t": "x", "flav.2.d": "[SCOPE.sCountry('rival').GetName] has launched a campaign.",
               "flav.1.t": "t", "flav.1.d": "d"}
        body = ("\timmediate = {\n\t\tevery_country = {\n\t\t\tsave_scope_as = rival\n\t\t}\n\t}\n"
                "\toption = { scope:rival = { trigger_event = { id = flav.1 } } }\n")
        mod = self._mod({"events/flav.txt": _event("flav.2", body) + _event("flav.1")}, loc)
        self.assertEqual(self._flags(mod, "imputed_foreign_action"), set())

    def test_stale_and_unknown_tags_are_reported(self):
        body = ("\t# REVIEWED 2026-09-25 (system_ungated): no longer needed\n"
                "\t# REVIEWED 2026-09-25 (sytem_ungated): typo\n")
        loc = {"flav.1.t": "Quiet", "flav.1.d": "Nothing happens."}
        mod = self._mod({"events/flav.txt": _event("flav.1", body)}, loc)
        res = eca.audit(mod)
        self.assertEqual([(t.event_id, t.check) for t in res.stale_tags], [("flav.1", "system_ungated")])
        self.assertEqual([(t.event_id, t.check) for t in res.unknown_tags], [("flav.1", "sytem_ungated")])
        self.assertEqual(res.failing, 2)

    def test_another_audits_check_tag_is_ignored(self):
        # silent_variable_audit uses the same tagged shape inside an option;
        # it is neither honoured here nor reported as a misspelled check.
        body = "\toption = {\n\t\t# REVIEWED 2026-09-25 (silent_variable): shown elsewhere\n\t}\n"
        loc = {"flav.1.t": "Quiet", "flav.1.d": "Nothing happens."}
        res = eca.audit(self._mod({"events/flav.txt": _event("flav.1", body)}, loc))
        self.assertEqual(res.unknown_tags, [])
        self.assertEqual(res.failing, 0)

    def test_all_tag_on_a_clean_event_is_stale(self):
        body = "\t# REVIEWED 2026-09-25 (all): nothing to hide\n"
        loc = {"flav.1.t": "Quiet", "flav.1.d": "Nothing happens."}
        res = eca.audit(self._mod({"events/flav.txt": _event("flav.1", body)}, loc))
        self.assertEqual([(t.event_id, t.check) for t in res.stale_tags], [("flav.1", "all")])
        self.assertEqual(res.failing, 1)


if __name__ == "__main__":
    unittest.main()
