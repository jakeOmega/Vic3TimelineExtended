"""Unit tests for gen_un_button_descs: what it states, and what it leaves to
the engine's own modifier lines (the 2026-10-27 audit, UN-10)."""
import unittest

from gen_un_button_descs import _walk_for_effects, render_effects_text


def _found(**kw):
    found = {"added_modifiers": [], "removed_modifiers": [],
             "authority_delta": 0.0, "ledger_entries": []}
    found.update(kw)
    return found


class RenderTests(unittest.TestCase):
    def test_modifiers_are_left_to_the_engine(self):
        # The buttons no longer hide their add_modifier lines in a
        # custom_tooltip, so the engine prints them coloured; prose here would
        # print them twice.
        text = render_effects_text(_found(added_modifiers=["un_peacekeeping_contributor_modifier"],
                                          removed_modifiers=["un_x_modifier"]))
        self.assertEqual(text, "")

    def test_a_ledger_booking_is_stated(self):
        text = render_effects_text(_found(ledger_entries=[("credibility", -1.0)]))
        self.assertIn("#R UN credibility −1#!", text)
        self.assertIn("[concept_un_authority]", text)


class LedgerEntryTests(unittest.TestCase):
    def test_both_forms_of_the_actor_entry_are_read(self):
        # un_buttons.txt's Lift Sanctions books through the _on form, which
        # names the sanctioned country in the UN's log; its button text must
        # still carry the credibility debit.
        found = _found()
        _walk_for_effects({
            "un_ledger_actor_entry": {"PILLAR": "credibility", "POINTS": "-1", "REASON": "7"},
            "custom_tooltip": {
                "un_ledger_actor_entry_on": {
                    "PILLAR": "credibility", "POINTS": "-1", "REASON": "7",
                    "SUBJECT": "scope:un_sanctions_lifted_target"},
            },
        }, found)
        self.assertEqual(found["ledger_entries"], [("credibility", -1.0), ("credibility", -1.0)])

    def test_a_booking_inside_a_hidden_effect_is_read(self):
        found = _found()
        _walk_for_effects({"hidden_effect": {"un_ledger_actor_entry_on": {
            "PILLAR": "credibility", "POINTS": "-1", "REASON": "7", "SUBJECT": "scope:x"}}}, found)
        self.assertEqual(found["ledger_entries"], [("credibility", -1.0)])


if __name__ == "__main__":
    unittest.main()
