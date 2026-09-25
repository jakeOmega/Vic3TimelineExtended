"""Unit tests for gen_un_button_descs' modifier phrase rendering."""
import unittest

from gen_un_button_descs import _render_modifier_phrase, _walk_for_effects


class RenderModifierPhraseTests(unittest.TestCase):
    def test_name_is_a_plain_substitution(self):
        # `Concept()` takes a game concept key and no modifier is one; the old
        # `[Concept('<name>','$<name>$')]` also broke on names that are links.
        phrase = _render_modifier_phrase(
            "un_peacekeeping_contributor_modifier",
            {"un_peacekeeping_contributor_modifier": [("country_prestige_mult", 0.05)]},
        )
        self.assertEqual(
            phrase, "$un_peacekeeping_contributor_modifier$ (+5% $country_prestige_mult$)")
        self.assertNotIn("Concept(", phrase)

    def test_modifier_without_effects(self):
        self.assertEqual(_render_modifier_phrase("un_x_modifier", {}), "$un_x_modifier$")


class LedgerEntryTests(unittest.TestCase):
    def _found(self):
        return {"added_modifiers": [], "removed_modifiers": [],
                "authority_delta": 0.0, "ledger_entries": []}

    def test_both_forms_of_the_actor_entry_are_read(self):
        # un_buttons.txt's Lift Sanctions books through the _on form, which
        # names the sanctioned country in the UN's log; its button text must
        # still carry the credibility debit.
        found = self._found()
        _walk_for_effects({
            "un_ledger_actor_entry": {"PILLAR": "credibility", "POINTS": "-1", "REASON": "7"},
            "custom_tooltip": {
                "un_ledger_actor_entry_on": {
                    "PILLAR": "credibility", "POINTS": "-1", "REASON": "7",
                    "SUBJECT": "scope:un_sanctions_lifted_target"},
            },
        }, found)
        self.assertEqual(found["ledger_entries"], [("credibility", -1.0), ("credibility", -1.0)])


if __name__ == "__main__":
    unittest.main()
