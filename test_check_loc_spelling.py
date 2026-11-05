"""Unit tests for scripts/analysis/check_loc_spelling.py, the American spelling sweep (owner, 2026-10-27).

The sweep rewrites text players read, so these pin what it must never touch: a loc key, the parts of a value the
engine reads ($splices$, [data expressions], @icons!, #format codes, \\n escapes, script keys), code and link
targets in the guide, and the allowlisted official names.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "analysis"))

import check_loc_spelling as spell  # noqa: E402

BOM = b"\xef\xbb\xbf"


def value(text: str, keep=frozenset()) -> str:
    return spell.americanize_value(text, keep)[0]


class WordListTest(unittest.TestCase):
    def test_pairs(self):
        for brit, amer in [("programme", "program"), ("programmes", "programs"), ("defence", "defense"),
                           ("licences", "licenses"), ("labourers", "laborers"), ("unfavourable", "unfavorable"),
                           ("centred", "centered"), ("metres", "meters"), ("organisation", "organization"),
                           ("stabilising", "stabilizing"), ("analysed", "analyzed"), ("travelling", "traveling"),
                           ("counsellor", "counselor"), ("jewellery", "jewelry"), ("fulfilment", "fulfillment"),
                           ("judgement", "judgment"), ("ageing", "aging"), ("grey", "gray"), ("storeys", "stories"),
                           ("practised", "practiced"), ("vapourise", "vaporize"), ("manoeuvring", "maneuvering")]:
            with self.subTest(brit=brit):
                self.assertEqual(spell.WORDS[brit], amer)

    def test_words_spelled_the_same_in_american_are_not_listed(self):
        for word in ("rise", "promise", "exercise", "advertise", "compromise", "enterprise", "franchise", "surprise",
                     "otherwise", "precise", "expertise", "premise", "merchandise", "televise", "supervise", "revise",
                     "devise", "advise", "cruise", "programmed", "programming", "enrolled", "fulfilled",
                     "cancellation", "dialogue", "towards", "tonne", "aeroplanes", "analyses", "paralysis",
                     "laborious", "vigorous", "honorary", "glamour", "exchequer", "realm"):
            with self.subTest(word=word):
                self.assertNotIn(word, spell.WORDS)

    def test_every_replacement_is_a_different_word(self):
        for brit, amer in spell.WORDS.items():
            self.assertNotEqual(brit, amer)
            self.assertNotIn(amer, spell.WORDS, f"{brit} -> {amer}, which is itself listed")


class LocValueTest(unittest.TestCase):
    def test_case_is_kept(self):
        self.assertEqual(value("Programme programme PROGRAMME"), "Program program PROGRAM")

    def test_compounds_and_possessives(self):
        self.assertEqual(value("centre-left Labour's self-defence"), "center-left Labor's self-defense")

    def test_engine_parts_are_left_alone(self):
        cases = {
            "$concept_defence$ defence": "$concept_defence$ defense",
            "[GetPlayer.MakeScope.ScriptValue('te_programme_cost')|0] programme": "[GetPlayer.MakeScope.ScriptValue('te_programme_cost')|0] program",
            "@defence! defence": "@defence! defense",
            "#grey Grey#!": "#grey Gray#!",
            "#tooltippable;tooltip:te_defence_tt Defence#!": "#tooltippable;tooltip:te_defence_tt Defense#!",
            "concept_seabed_licence licence": "concept_seabed_licence license",
            "gfx/interface/icons/defence.dds defence": "gfx/interface/icons/defence.dds defense",
        }
        for before, after in cases.items():
            with self.subTest(before=before):
                self.assertEqual(value(before), after)

    def test_escapes_bound_a_word(self):
        self.assertEqual(value(r"First line.\nDefence spending\n\"Colour\""),
                         r"First line.\nDefense spending\n\"Color\"")

    def test_concept_display_text_changes_but_not_its_key(self):
        self.assertEqual(value("[Concept('concept_seabed_licence','Licences')]s"),
                         "[Concept('concept_seabed_licence','Licenses')]s")
        self.assertEqual(value("[Concept('concept_x', '$concept_licence$ Licences')]"),
                         "[Concept('concept_x', '$concept_licence$ Licenses')]")

    def test_allowlisted_names_keep_their_spelling(self):
        self.assertEqual(value("the Kenyatta International Convention Centre, a centre"),
                         "the Kenyatta International Convention Centre, a center")
        self.assertEqual(value("Founds the UN Environment Programme (UNEP), a programme."),
                         "Founds the UN Environment Programme (UNEP), a program.")

    def test_vanilla_text_for_the_key_is_kept(self):
        keep = spell._vanilla_keep("The theatre of European politics")
        self.assertEqual(value("The theatre of European politics, a theatre", keep),
                         "The theatre of European politics, a theatre")


class LocFileTest(unittest.TestCase):
    def sweep(self, text: str, vanilla=None) -> str:
        return spell.sweep_loc_text(text, vanilla or {})[0]

    def test_keys_comments_and_trailing_text_are_left_alone(self):
        text = ('l_english:\n'
                '# defence programme notes\n'
                ' te_defence_programme:0 "Defence Programme" # REVIEWED 2026-10-27: defence\n'
                ' te_colour_desc: "Colour"\r\n')
        self.assertEqual(self.sweep(text),
                         'l_english:\n'
                         '# defence programme notes\n'
                         ' te_defence_programme:0 "Defense Program" # REVIEWED 2026-10-27: defence\n'
                         ' te_colour_desc: "Color"\r\n')

    def test_key_override_of_vanilla(self):
        text = ' SWI_FLAVOR_TEXT:0 "the theatre of European politics and its defence"\n'
        vanilla = {"SWI_FLAVOR_TEXT": "the theatre of European politics"}
        self.assertEqual(self.sweep(text, vanilla),
                         ' SWI_FLAVOR_TEXT:0 "the theatre of European politics and its defense"\n')


class GuideTest(unittest.TestCase):
    def test_code_links_and_urls_are_left_alone(self):
        text = ("# Defence\n\n"
                "Defence `programme_cost` [the programme](04-banking.md#the-programme) https://x.org/programme\n"
                "```\nprogramme\n```\n")
        new, _changes, _allowed = spell.sweep_md_text(text)
        self.assertEqual(new, "# Defense\n\n"
                              "Defense `programme_cost` [the program](04-banking.md#the-programme) "
                              "https://x.org/programme\n```\nprogramme\n```\n")

    def test_links_follow_a_renamed_heading(self):
        texts = {"01-a.md": "# A\n\nSee [colour](#colour-and-honours) and [b](02-b.md#the-defence-programme).\n\n"
                            "## Color and honors\n\nText.\n",
                 "02-b.md": "# B\n\n## The defense program\n\nText.\n"}
        fixed, count = spell.fix_guide_links(texts)
        self.assertEqual(count, 2)
        self.assertIn("(#color-and-honors)", fixed["01-a.md"])
        self.assertIn("(02-b.md#the-defense-program)", fixed["01-a.md"])

    def test_a_link_to_an_existing_anchor_is_kept(self):
        texts = {"01-a.md": "# A\n\n[k](#kenyatta-international-convention-centre)\n\n"
                            "## Kenyatta International Convention Centre\n\nText.\n"}
        self.assertEqual(spell.fix_guide_links(texts), (texts, 0))


class RunTest(unittest.TestCase):
    def test_rewrite_then_check_is_clean_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            loc = Path(tmp) / "loc"
            guide = Path(tmp) / "guide"
            (loc / "replace").mkdir(parents=True)
            guide.mkdir()
            (loc / "a_l_english.yml").write_bytes(BOM + b'l_english:\n te_x:0 "Colour programme"\n')
            (loc / "replace" / "b_l_english.yml").write_bytes(BOM + b'l_english:\n te_y:0 "defence"\n')
            (guide / "01-a.md").write_text("# A\n\n[x](#the-colour)\n\n## The colour\n\nGrey.\n", encoding="utf-8")

            out = io.StringIO()
            self.assertEqual(spell.run(True, loc, guide, {}, out), 1)
            self.assertIn("1 guide link(s) point at a heading's British anchor\n6 British spelling(s) left", out.getvalue())
            self.assertEqual(spell.run(False, loc, guide, {}, io.StringIO()), 0)
            self.assertEqual((loc / "a_l_english.yml").read_bytes(), BOM + b'l_english:\n te_x:0 "Color program"\n')
            self.assertEqual((loc / "replace" / "b_l_english.yml").read_bytes(),
                             BOM + b'l_english:\n te_y:0 "defense"\n')
            self.assertEqual((guide / "01-a.md").read_text(encoding="utf-8"),
                             "# A\n\n[x](#the-color)\n\n## The color\n\nGray.\n")
            out = io.StringIO()
            self.assertEqual(spell.run(True, loc, guide, {}, out), 0)
            self.assertIn("no British spellings left", out.getvalue())


if __name__ == "__main__":
    unittest.main()
