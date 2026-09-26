"""Unit tests for empty_effect_audit.

The crux is discrimination. `empty_block`: an empty conditional is dead only
at the end of its chain (inside one it claims its case), and a parameterised
body is never empty. `no_effect_option`: an option that does nothing is only
interesting beside one that does something.
"""
from __future__ import annotations

import os
import tempfile
import unittest

import event_context_audit
import iterator_limit_audit
from empty_effect_audit import audit, render_report, scan_text


def _blocks(text: str):
    return scan_text(text, "test.txt")[0]


def _options(text: str):
    return scan_text(text, "events/test.txt", options=True)[1]


class EmptyBlockTests(unittest.TestCase):
    def test_flags_chain_end_if(self):
        flags = _blocks(
            "se = {\n"
            "\tif = {\n"
            "\t\tlimit = { has_variable = x }\n"
            "\t}\n"
            "\tdo_b = yes\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.key, f.reason) for f in flags], [(2, "if", "chain-end")])

    def test_mid_chain_empty_branch_is_load_bearing(self):
        # banking_cycle_effects.txt: "Stable = no modifier" claims 40-60 so
        # the expansion branch below it does not fire.
        flags = _blocks(
            "se = {\n"
            "\tif = { limit = { var:v < 40 } add_modifier = { name = a } }\n"
            "\telse_if = { limit = { var:v < 60 } } # Stable = no modifier\n"
            "\telse_if = { limit = { var:v < 75 } add_modifier = { name = b } }\n"
            "\telse = { add_modifier = { name = c } }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_empty_if_before_else_is_an_inverted_guard(self):
        flags = _blocks(
            "se = {\n"
            "\tif = { limit = { NOT = { exists = scope:h } } }\n"
            "\telse = { do_x = yes }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_flags_last_else_if_and_empty_else(self):
        flags = _blocks(
            "se = {\n"
            "\tif = { limit = { a = yes } do_a = yes }\n"
            "\telse_if = { limit = { b = yes } }\n"
            "}\n"
            "se2 = {\n"
            "\tif = { limit = { a = yes } do_a = yes }\n"
            "\telse = { }\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.key, f.reason) for f in flags],
                         [(3, "else_if", "chain-end"), (7, "else", "else")])

    def test_trigger_if_chain(self):
        flags = _blocks(
            "t = {\n"
            "\ttrigger_if = { limit = { a = yes } }\n"
            "\ttrigger_else = { b = yes }\n"
            "}\n"
            "t2 = {\n"
            "\ttrigger_if = { limit = { a = yes } b = yes }\n"
            "\ttrigger_else_if = { limit = { c = yes } }\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.key) for f in flags], [(7, "trigger_else_if")])

    def test_flags_iterator_with_only_properties(self):
        # vanilla production_tech_events.txt: the save_scope_as meant for the
        # building sits outside the iterator, which does nothing.
        flags = _blocks(
            "e = {\n"
            "\trandom_scope_building = {\n"
            "\t\tlimit = { is_building_type = building_coal_mine }\n"
            "\t}\n"
            "\tordered_scope_state = { order_by = gdp max = 3 limit = { a = yes } }\n"
            "\tsave_scope_as = x\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.key, f.reason) for f in flags],
                         [(2, "random_scope_building", "wrapper"),
                          (5, "ordered_scope_state", "wrapper")])

    def test_iterator_with_content_is_not_flagged(self):
        flags = _blocks(
            "e = {\n"
            "\tevery_scope_state = { limit = { a = yes } save_scope_as = s }\n"
            "\tevery_in_list = { variable = l add_to_temporary_list = t }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_weight_lists_and_values_are_not_iterators(self):
        flags = _blocks(
            "oa = {\n"
            "\trandom_events = { 100 = 0 50 = my.1 }\n"
            "\trandom_list = { 50 = { } 50 = { do_x = yes } }\n"
            "\tage = { random_range = { min = 20 max = 30 } }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_script_value_min_max_are_content_in_an_if(self):
        # un_authority_values.txt: `max` inside an `if` is an operation,
        # not an iterator property.
        flags = _blocks(
            "sv = {\n"
            "\tvalue = 1\n"
            "\tif = { limit = { a = yes } max = 5 }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_parameterised_body_is_never_empty(self):
        flags = _blocks(
            "se = {\n"
            "\tif = { limit = { a = yes } $EFFECT$ }\n"
            "\tif = { limit = { a = yes } [[OPT] ] }\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_parameter_only_inside_limit_still_empty(self):
        flags = _blocks(
            "se = {\n"
            "\tif = { limit = { has_variable = sr_active_$MILESTONE$ } }\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)

    def test_wrappers_with_nothing_to_run(self):
        flags = _blocks(
            "se = {\n"
            "\thidden_effect = { }\n"
            "\twhile = { count = 3 }\n"
            "\trandom = { chance = 50 }\n"
            "\thidden_effect = { do_x = yes }\n"
            "}\n"
        )
        self.assertEqual([f.key for f in flags], ["hidden_effect", "while", "random"])

    def test_nested_dead_blocks_report_the_outer_one(self):
        flags = _blocks(
            "se = {\n"
            "\tevery_country = {\n"
            "\t\tlimit = { a = yes }\n"
            "\t\tif = { limit = { b = yes } }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual([(f.line, f.key) for f in flags], [(2, "every_country")])

    def test_comments_and_strings_do_not_count_as_content(self):
        flags = _blocks(
            "se = {\n"
            "\tif = {\n"
            "\t\tlimit = { a = yes }\n"
            "\t\t# do_x = yes\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)


# The original space_race_events.20, before the 2026-09-26 fix.
SPACE_RACE_20 = (
    "space_race_events.20 = {\n"
    "\ttype = country_event\n"
    "\ttitle = space_race_events.20.t\n"
    "\toption = {\n"
    "\t\tname = space_race_events.20.a\n"
    "\t\tdefault_option = yes\n"
    "\t\tai_chance = { base = 5 }\n"
    "\t\t# We must accelerate our own program\n"
    "\t\tif = {\n"
    "\t\t\tlimit = { has_variable = sr_active_milestone }\n"
    "\t\t}\n"
    "\t}\n"
    "\toption = {\n"
    "\t\tname = space_race_events.20.b\n"
    "\t\tai_chance = { base = 3 }\n"
    "\t\tif = {\n"
    "\t\t\tlimit = { exists = scope:sr_achiever }\n"
    "\t\t\tchange_relations = { country = scope:sr_achiever value = 10 }\n"
    "\t\t}\n"
    "\t}\n"
    "\tafter = {\n"
    "\t\thidden_effect = { scope:flavor_speaker = { kill_character = { hidden = yes } } }\n"
    "\t}\n"
    "}\n"
)


class NoEffectOptionTests(unittest.TestCase):
    def test_reproduces_space_race_20(self):
        blocks, opts, _stale, events, n_opts = scan_text(
            SPACE_RACE_20, "events/space_race_events.txt", options=True)
        self.assertEqual([(f.event_id, f.option, f.line) for f in opts],
                         [("space_race_events.20", "space_race_events.20.a", 4)])
        self.assertEqual([(f.line, f.key) for f in blocks], [(9, "if")])
        # A nested `hidden = yes` (kill_character's) does not hide the event.
        self.assertEqual((events, n_opts), (1, 2))

    def test_fixed_option_is_not_flagged(self):
        text = SPACE_RACE_20.replace(
            "\t\tif = {\n\t\t\tlimit = { has_variable = sr_active_milestone }\n\t\t}\n",
            "\t\tif = {\n\t\t\tlimit = { sr_has_running_milestone = yes }\n"
            "\t\t\tcustom_tooltip = SR_PROGRESS_ADD_3_TT\n"
            "\t\t\tset_variable = { name = sr_progress_boost value = 3 }\n"
            "\t\t\tsr_boost_active_milestones = yes\n\t\t}\n"
            "\t\telse = { add_loyalists = { value = very_small_radicals pop_type = academics } }\n",
        )
        blocks, opts, *_ = scan_text(text, "events/space_race_events.txt", options=True)
        self.assertEqual((blocks, opts), ([], []))

    def test_all_flavour_notification_is_not_flagged(self):
        opts = _options(
            "ev.1 = {\n"
            "\toption = { name = ev.1.a trigger = { a = yes } default_option = yes }\n"
            "\toption = { name = ev.1.b trigger = { a = no } }\n"
            "}\n"
        )
        self.assertEqual(opts, [])

    def test_tooltip_only_option_is_a_no_op(self):
        opts = _options(
            "ev.1 = {\n"
            "\toption = { name = ev.1.a custom_tooltip = ev.1.a.tt }\n"
            "\toption = { name = ev.1.b show_as_tooltip = { add_treasury = 5 } }\n"
            "\toption = { name = ev.1.c add_treasury = 5 }\n"
            "\toption = { name = ev.1.d custom_tooltip = { text = ev.1.d.tt add_treasury = 5 } }\n"
            "\toption = { name = ev.1.e custom_tooltip = { text = ev.1.e.tt } }\n"
            "}\n"
        )
        self.assertEqual([f.option for f in opts], ["ev.1.a", "ev.1.b", "ev.1.e"])

    def test_scripted_effect_call_and_empty_scope_switch(self):
        opts = _options(
            "ev.1 = {\n"
            "\toption = { name = ev.1.a my_effect = yes }\n"
            "\toption = { name = ev.1.b scope:x = { } }\n"
            "}\n"
        )
        self.assertEqual([f.option for f in opts], ["ev.1.b"])

    def test_hidden_event_is_skipped(self):
        opts = _options(
            "ev.1 = {\n"
            "\thidden = yes\n"
            "\toption = { name = ev.1.a }\n"
            "\toption = { name = ev.1.b add_treasury = 5 }\n"
            "}\n"
        )
        self.assertEqual(opts, [])

    def test_options_check_off_outside_events(self):
        _b, opts, *_ = scan_text(
            "ev.1 = {\n\toption = { name = a }\n\toption = { name = b x = yes }\n}\n",
            "common/x.txt",
        )
        self.assertEqual(opts, [])


class SuppressionTests(unittest.TestCase):
    def test_tagged_option_is_exempt(self):
        opts = _options(
            "ev.1 = {\n"
            "\toption = {\n"
            "\t\tname = ev.1.a\n"
            "\t\t# REVIEWED 2026-09-26 (no_effect_option): the decline\n"
            "\t}\n"
            "\toption = { name = ev.1.b add_treasury = 5 }\n"
            "}\n"
        )
        self.assertEqual(len(opts), 1)
        self.assertEqual(opts[0].exemption["rationale"], "the decline")

    def test_block_tag_on_opener_or_inside(self):
        flags = _blocks(
            "se = {\n"
            "\tif = { # REVIEWED 2026-09-26 (empty_block): opener\n"
            "\t\tlimit = { a = yes }\n"
            "\t}\n"
            "\tdo_x = yes\n"
            "\tif = {\n"
            "\t\tlimit = { a = yes }\n"
            "\t\t# REVIEWED 2026-09-26 (empty_block): silences an unused variable\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual([f.exemption["rationale"] for f in flags],
                         ["opener", "silences an unused variable"])

    def test_untagged_or_wrong_check_does_not_exempt(self):
        flags = _blocks(
            "se = {\n"
            "\tif = { # REVIEWED 2026-09-26: untagged\n"
            "\t\tlimit = { a = yes }\n"
            "\t}\n"
            "\tdo_x = yes\n"
            "\tif = { # REVIEWED 2026-09-26 (no_effect_option): wrong check\n"
            "\t\tlimit = { a = yes }\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual([f.exemption for f in flags], [None, None])

    def test_stale_tag_is_reported(self):
        _b, _o, stale, *_ = scan_text(
            "ev.1 = {\n"
            "\toption = {\n"
            "\t\tname = ev.1.a\n"
            "\t\t# REVIEWED 2026-09-26 (no_effect_option): once a decline\n"
            "\t\tadd_treasury = 5\n"
            "\t}\n"
            "}\n",
            "events/test.txt", options=True,
        )
        self.assertEqual([(s.line, s.check) for s in stale], [(4, "no_effect_option")])

    def test_tagged_form_is_invisible_to_untagged_audits(self):
        # An `every_x = {` opener carries both this audit's and
        # iterator_limit_audit's comments; neither may read the other's.
        c = "# REVIEWED 2026-09-26 (empty_block): why"
        self.assertIsNone(iterator_limit_audit._REVIEWED_RE.search(c))

    def test_event_context_audit_treats_our_tags_as_foreign(self):
        self.assertIn("empty_block", event_context_audit.FOREIGN_CHECKS)
        self.assertIn("no_effect_option", event_context_audit.FOREIGN_CHECKS)


class AuditTests(unittest.TestCase):
    def _tree(self, files: dict[str, str]) -> str:
        root = tempfile.mkdtemp()
        for rel, text in files.items():
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8-sig") as fh:
                fh.write(text)
        return root

    def test_audit_walks_common_and_events_and_skips_debug_options(self):
        root = self._tree({
            "events/space_race_events.txt": SPACE_RACE_20,
            "events/te_debug_x_events.txt": SPACE_RACE_20.replace("space_race_events", "te_debug_x"),
            "common/script_values/sv.txt": "sv = { value = 1 if = { limit = { a = yes } } }\n",
            "gui/x.gui": "if = { limit = { a = yes } }\n",
        })
        result = audit(mod_path=root)
        self.assertEqual(result.files_audited, 3)
        self.assertEqual([f.option for f in result.option_flags], ["space_race_events.20.a"])
        self.assertEqual(sorted(f.file for f in result.block_flags), [
            os.path.join("common", "script_values", "sv.txt"),
            os.path.join("events", "space_race_events.txt"),
            os.path.join("events", "te_debug_x_events.txt"),
        ])
        self.assertEqual(result.failing, 4)
        report = render_report(result)
        self.assertIn("space_race_events.20.a", report)
        self.assertIn("## Coverage", report)

    def test_clean_tree_passes(self):
        root = self._tree({"events/e.txt": "ev.1 = {\n\toption = { name = a x = yes }\n}\n"})
        self.assertEqual(audit(mod_path=root).failing, 0)


if __name__ == "__main__":
    unittest.main()
