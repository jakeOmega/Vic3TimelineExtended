"""Unit tests for gen_un_button_descs' modifier phrase rendering."""
import unittest

from gen_un_button_descs import _render_modifier_phrase


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


if __name__ == "__main__":
    unittest.main()
