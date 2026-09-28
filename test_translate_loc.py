"""Unit tests for scripts/i18n/translate_loc.py, the machine-translation harness.

The markup check is what keeps a model's output from breaking the game's loc,
so most of these pin what it accepts (the grammar the official German uses)
and what it rejects.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "scripts", "i18n"))

import translate_loc as t  # noqa: E402


def _errors(en: str, de: str) -> list[str]:
    return t.check_translation(en, de)[0]


class MarkupCheckAcceptsTests(unittest.TestCase):
    def test_plain_translation(self):
        self.assertEqual(_errors("Raises the price", "Erhöht den Preis"), [])

    def test_concept_link_inflected_with_concept_call(self):
        en = "in [concept_power_bloc_member] with lower [concept_rank]"
        de = "bei [Concept('concept_power_bloc_member','Blockmitgliedern')] mit niedrigerem [concept_rank]"
        self.assertEqual(_errors(en, de), [])

    def test_concept_call_display_text_is_free(self):
        en = "[Concept('concept_pop', '$concept_pops$')] support it"
        de = "[Concept('concept_pop', 'Bevölkerungsgruppen')] unterstützen es"
        self.assertEqual(_errors(en, de), [])

    def test_country_name_declined_with_alt_name_and_case_flag(self):
        en = "[INITIATOR_COUNTRY.GetName] has rights in [TARGET_COUNTRY.GetName]"
        de = "[INITIATOR_COUNTRY.GetAltName('NOM')|U] hat Rechte [TARGET_COUNTRY.GetAltName('IN')]"
        self.assertEqual(_errors(en, de), [])

    def test_lowercase_flag_on_a_concept(self):
        self.assertEqual(_errors("has [concept_war] now", "hat jetzt [concept_war|l]"), [])

    def test_markup_may_move_within_the_sentence(self):
        en = "#b Warning:#! lose @money!$VALUE|+=0$ per week\\n"
        de = "Verlust von @money!$VALUE|+=0$ pro Woche #b Warnung:#!\\n"
        self.assertEqual(_errors(en, de), [])

    def test_genitive_suffix_after_a_reference(self):
        self.assertEqual(_errors("the laws of the $concept_country$", "die Gesetze des $concept_country$es"), [])


class MarkupCheckRejectsTests(unittest.TestCase):
    def test_dropped_concept_link(self):
        errors = _errors("Raises [concept_legitimacy]", "Erhöht die Legitimität")
        self.assertTrue(any("concept links" in e for e in errors), errors)

    def test_translated_script_call(self):
        errors = _errors("[GetPlayer.GetName] wins", "[GetSpieler.GetName] gewinnt")
        self.assertTrue(any("[...] calls" in e for e in errors), errors)

    def test_alt_name_does_not_excuse_a_different_scope(self):
        errors = _errors("[TARGET_COUNTRY.GetName]", "[ROOT.GetAltName('NOM')]")
        self.assertTrue(any("[...] calls" in e for e in errors), errors)

    def test_numeric_format_flag_must_stay(self):
        errors = _errors("[X.GetValue|+=]", "[X.GetValue]")
        self.assertTrue(any("[...] calls" in e for e in errors), errors)

    def test_lost_reference_icon_code_and_line_break(self):
        errors = _errors("#b $VAL$#! @money!\\nMore", "fett Geld mehr")
        names = " ".join(errors)
        for part in ("$...$", "@icons!", "#format codes", "#! closers", "\\n line breaks"):
            self.assertIn(part, names)

    def test_empty_translation(self):
        self.assertEqual(_errors("Something", "  "), ["empty translation"])


class WarningTests(unittest.TestCase):
    def test_untranslated_prose_warns(self):
        en = "This is a long English sentence"
        self.assertIn("identical to English", t.check_translation(en, en)[1])

    def test_extreme_length_ratio_warns(self):
        warnings = t.check_translation("Raises the price of grain", "Ja")[1]
        self.assertTrue(any("length ratio" in w for w in warnings), warnings)


class StalePolicyTests(unittest.TestCase):
    def test_small_wording_change_is_minor(self):
        self.assertTrue(t.is_minor_change(
            "Raises the price of grain by 10% for two years.",
            "Raises the price of grain by 10% for the next two years."))

    def test_changed_number_is_major(self):
        self.assertFalse(t.is_minor_change("Raises the price by 10%.", "Raises the price by 15%."))

    def test_renamed_short_name_is_major(self):
        self.assertFalse(t.is_minor_change("African Union", "Pan-African Union"))

    def test_short_label_case_or_punctuation_is_minor(self):
        self.assertTrue(t.is_minor_change("Raise taxes.", "Raise Taxes"))

    def test_rewrite_is_major(self):
        self.assertFalse(t.is_minor_change("Raises the price of grain.", "Lowers wages in every state."))

    def test_classify(self):
        entries = [t.Entry("a_l_english.yml", k, en) for k, en in [
            ("same", "Hello there"), ("tweak", "Hello there, friend!"), ("new", "Brand new"),
            ("rewritten", "Something else"), ("markup_only", "$X$"),
        ]]
        tm = {
            "same": {"en": "Hello there", "de": "Hallo"},
            "tweak": {"en": "Hello there, friend.", "de": "Hallo, Freund."},
            "rewritten": {"en": "Old text entirely", "de": "Alt"},
        }
        state = t.classify(entries, tm)
        self.assertEqual([e.key for e in state["translated"]], ["same"])
        self.assertEqual([e.key for e in state["stale_minor"]], ["tweak"])
        self.assertEqual([e.key for e in state["stale_major"]], ["rewritten"])
        self.assertEqual([e.key for e in state["missing"]], ["new"])
        self.assertEqual([e.key for e in state["skip"]], ["markup_only"])


class NumberFormatTests(unittest.TestCase):
    def test_decimal_and_thousands_swapped_in_prose(self):
        en = "Costs 2.5 times as much, up to 1,000 units."
        self.assertEqual(t.localize_numbers(en, "Kostet 2.5-mal so viel, bis zu 1,000 Einheiten.", "german"),
                         "Kostet 2,5-mal so viel, bis zu 1.000 Einheiten.")

    def test_markup_and_already_converted_numbers_untouched(self):
        en = "Rate #v 0.5#! of [X.GetValue|1.0] and 1,000"
        de = "Rate #v 0.5#! von [X.GetValue|1.0] und 1.000"
        self.assertEqual(t.localize_numbers(en, de, "german"), "Rate #v 0,5#! von [X.GetValue|1.0] und 1.000")

    def test_numbers_not_in_the_english_untouched(self):
        self.assertEqual(t.localize_numbers("Plain text", "Version 2.0", "german"), "Version 2.0")

    def test_english_formats_kept_for_other_languages(self):
        self.assertEqual(t.localize_numbers("2.5", "2.5", "japanese"), "2.5")


class TermCheckTests(unittest.TestCase):
    def test_inflected_rendering_passes_other_rendering_flagged(self):
        tm = {
            "a": {"en": "Boosts Tradecraft", "de": "Stärkt das Spionagehandwerks"},
            "b": {"en": "Seasoned Tradecraft", "de": "Erfahrene Tradecraft"},
            "c": {"en": "Unrelated", "de": "Anders"},
            "AFU_DAT": {"en": "Tradecraft", "de": "x", "base": "AFU"},
        }
        self.assertEqual(t.term_mismatches(tm, {"Tradecraft": "Spionagehandwerk"}, "de"),
                         [("b", "Tradecraft", "Spionagehandwerk")])


class ChunkingTests(unittest.TestCase):
    def test_event_group_is_not_split(self):
        entries = [t.Entry("e_l_english.yml", f"ev.1.{s}", "word " * 10) for s in ("t", "d", "f", "a")]
        entries.append(t.Entry("e_l_english.yml", "ev.2.t", "word " * 10))
        chunks = t.split_chunks(entries, budget=15)
        self.assertEqual([len(c) for c in chunks], [4, 1])

    def test_key_cap_ends_a_chunk_of_short_labels(self):
        entries = [t.Entry("a_l_english.yml", f"pm_{i}", "Label") for i in range(10)]
        self.assertEqual([len(c) for c in t.split_chunks(entries, budget=1000, max_keys=4)], [4, 4, 2])

    def test_new_file_starts_a_chunk_once_over_budget(self):
        entries = [t.Entry("a_l_english.yml", "x", "w " * 20), t.Entry("b_l_english.yml", "x_desc", "w " * 5)]
        self.assertEqual(len(t.split_chunks(entries, budget=10)), 2)


class GlossarySelectionTests(unittest.TestCase):
    def test_names_are_selected_descriptions_are_not(self):
        self.assertTrue(t.is_glossary_entry(t.Entry("te_laws_l_english.yml", "law_x", "Ancestral Citizenship")))
        self.assertFalse(t.is_glossary_entry(t.Entry("te_laws_l_english.yml", "law_x_desc", "Citizenship is…")))
        self.assertTrue(t.is_glossary_entry(t.Entry(os.path.join("replace", "o_l_english.yml"), "coal", "Energy")))
        self.assertFalse(t.is_glossary_entry(t.Entry("te_events_l_english.yml", "ev.1.t", "The Shadow War")))

    def test_country_names(self):
        f = "te_formable_countries_l_english.yml"
        self.assertTrue(t.is_country_name(t.Entry(f, "AFU", "African Union")))
        self.assertTrue(t.is_country_name(t.Entry(f, "dyn_c_african_empire", "African Empire")))
        self.assertFalse(t.is_country_name(t.Entry(f, "AFU_ADJ", "African")))
        self.assertFalse(t.is_country_name(t.Entry(f, "dyn_c_african_empire_adj", "African")))


class RoundTripTests(unittest.TestCase):
    """prepare-free: a manifest and agent output on disk, then merge and save."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.dirs = (os.path.join(root, "i18n", "german"), os.path.join(root, "build", "i18n", "german"))
        self.entries = [
            t.Entry("te_formable_countries_l_english.yml", "AFU", "African Union"),
            t.Entry("te_laws_l_english.yml", "law_x", "Raises [concept_legitimacy]"),
            t.Entry("te_laws_l_english.yml", "law_y", "Plain"),
        ]
        os.makedirs(os.path.join(self.dirs[1], "out"))
        with open(os.path.join(self.dirs[1], "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump({"names-001": {"keys": {e.key: e.en for e in self.entries},
                                     "country_names": ["AFU"], "words": 5}}, fh)
        forms = "\n".join(f' AFU_{f}:0 "die Afrikanische Union"' for f in t.COUNTRY_FORMS)
        with open(os.path.join(self.dirs[1], "out", "names-001.01.txt"), "w", encoding="utf-8") as fh:
            fh.write(' AFU:0 "Afrikanische Union"\n law_x:0 "Erhöht die Legitimität"\n'
                     ' law_y:0 "Er sagte "Hallo""\n' + forms + "\n")
        self.patches = [
            mock.patch.object(t, "language_dirs", lambda language: self.dirs),
            mock.patch.object(t, "load_english", lambda english_dir=None: self.entries),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_merge_accepts_good_lines_and_rejects_bad_ones(self):
        args = mock.Mock(language="german", field="de", chunks=[])
        self.assertEqual(t.cmd_merge(args), 1)
        tm = t.load_tm("german")
        self.assertEqual(tm["AFU"]["de"], "Afrikanische Union")
        self.assertEqual(tm["AFU_DAT"], {"en": "African Union", "de": "die Afrikanische Union", "base": "AFU"})
        self.assertNotIn("law_x", tm)  # dropped its concept link
        self.assertNotIn("law_y", tm)  # bare quote inside the value
        with open(os.path.join(self.dirs[1], "merge_report.json"), encoding="utf-8") as fh:
            rejected = json.load(fh)["names-001"]["rejected"]
        self.assertTrue(any("concept links" in e for e in rejected["law_x"]))
        self.assertTrue(any('bare "' in e for e in rejected["law_y"]))
        # The country forms live in the base key's file.
        self.assertTrue(os.path.isfile(os.path.join(self.dirs[0], "tm", "te_formable_countries.json")))


if __name__ == "__main__":
    unittest.main()
