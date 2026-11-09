"""Unit tests for scripts/i18n/translate_loc.py, the machine-translation harness.

The markup check is what keeps a model's output from breaking the game's loc,
so most of these pin what it accepts (the grammar the official German uses)
and what it rejects.
"""
from __future__ import annotations

import contextlib
import io
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
    def test_unescaped_reference_in_a_quoted_argument(self):
        # 1.15: a $key$ inside a loc function's quoted argument needs |q.
        en = "[Concept('concept_state', '$concept_states|q$')] grow"
        errors = _errors(en, "[Concept('concept_state', '$concept_states$')] wachsen")
        self.assertTrue(any("quote-escaping" in e for e in errors), errors)
        self.assertEqual(_errors(en, "[Concept('concept_state', '$concept_states|q$')] wachsen"), [])

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

    def test_alt_name_only_in_a_language_that_declines(self):
        en = "Protect [TARGET_COUNTRY.GetName]"
        errors = t.check_translation(en, "Protege a [TARGET_COUNTRY.GetAltName('DAT')]", "spanish")[0]
        self.assertTrue(any("GetAltName" in e for e in errors), errors)
        self.assertEqual(t.check_translation(en, "Protege a [TARGET_COUNTRY.GetName]", "spanish")[0], [])

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

    def test_american_spelling_is_minor(self):
        """The 2026-10-27 sweep to American spelling keeps every translation, short labels included."""
        self.assertTrue(t.is_minor_change("Seabed Licences", "Seabed Licenses"))
        self.assertTrue(t.is_minor_change("[Concept('concept_x','Defence')] programme", "[Concept('concept_x','Defense')] program"))
        self.assertFalse(t.is_minor_change("Seabed Licences", "Seabed Permits"))

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

    def test_percent_space_closed_as_vanilla_german_writes(self):
        self.assertEqual(t.localize_numbers("up to 5% more", "bis zu 5 % mehr", "german"), "bis zu 5% mehr")

    def test_spanish_thousands_take_a_no_break_space(self):
        en = "Costs 2.5 times as much, up to 1,000 units, or 12,000 at 5%."
        es = "Cuesta 2.5 veces más, hasta 1,000 unidades, o 12 000 al 5 %."
        self.assertEqual(t.localize_numbers(en, es, "spanish"),
                         "Cuesta 2,5 veces más, hasta 1\u00a0000 unidades, o 12\u00a0000 al 5%.")

    def test_english_formats_kept_for_other_languages(self):
        self.assertEqual(t.localize_numbers("2.5", "2.5", "japanese"), "2.5")


class QuoteFormatTests(unittest.TestCase):
    def test_escaped_straight_quotes_become_german(self):
        self.assertEqual(t.localize_quotes('\\"Ja.\\"\\n\\n\\"Nein.\\"', "german"), "„Ja.“\\n\\n„Nein.“")

    def test_inner_pair_nests_as_single_marks(self):
        self.assertEqual(t.localize_quotes('\\"Mit „ja“ beginnen.\\"', "german"), "„Mit ‚ja‘ beginnen.“")

    def test_wrong_closing_mark(self):
        self.assertEqual(t.localize_quotes("Die Aktion „Krisenlösung” nutzen", "german"), "Die Aktion „Krisenlösung“ nutzen")

    def test_unpaired_quotes_left_alone(self):
        odd = '\\"Eins.\\" Zwei.\\"'
        self.assertEqual(t.localize_quotes(odd, "german"), odd)
        self.assertEqual(t.localize_quotes("„Ja“", "french"), "„Ja“")

    def test_spanish_angle_quotes_outside_curly_inside(self):
        self.assertEqual(t.localize_quotes('\\"Empezar con “sí”.\\"', "spanish"), "«Empezar con “sí”.»")
        self.assertEqual(t.localize_quotes("La acción “Resolver la crisis”", "spanish"), "La acción «Resolver la crisis»")

    def test_spanish_apostrophe_is_not_a_quote(self):
        self.assertEqual(t.localize_quotes('O’Higgins dijo \\"no\\"', "spanish"), "O’Higgins dijo «no»")


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


class QuoteRepairTests(unittest.TestCase):
    def test_plain_closing_quote_after_german_opening(self):
        line = ' k:0 "„Man hört es." \\n\\n— Kommandant"\n'
        self.assertEqual(t.repair_bare_quotes(line), '„Man hört es.“ \\n\\n— Kommandant')

    def test_both_marks_plain(self):
        self.assertEqual(t.repair_bare_quotes(' k:0 "Er sagte "Hallo" laut"'), "Er sagte „Hallo“ laut")

    def test_spanish_marks(self):
        self.assertEqual(t.repair_bare_quotes(' k:0 "Dijo "Hola" en voz alta"', "spanish"), "Dijo «Hola» en voz alta")
        self.assertEqual(t.repair_bare_quotes(' k:0 "«Se oye." \\n— Comandante"', "spanish"), "«Se oye.» \\n— Comandante")


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
    def test_referenced_keys_read_through_format_flags(self):
        keys = t.referenced_keys("[Concept('concept_ship_group', '$ship_group_cruisers|q$')] $iron$")
        self.assertTrue({"ship_group_cruisers", "iron", "concept_ship_group"} <= keys, keys)

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


class ChunkFileTests(unittest.TestCase):
    def test_stale_line_carries_its_previous_translation(self):
        chunk = [t.Entry("te_x_l_english.yml", "a", "Dues"), t.Entry("te_x_l_english.yml", "b", "New")]
        previous = {"a": {"en": "Our Dues", "de": "Unsere Beiträge"}}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "c-001.txt")
            t.write_chunk(path, "c-001", chunk, [], [], "german", previous, "de")
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        i = lines.index(' a:0 "Dues"')
        self.assertEqual(lines[i - 2:i], ["# PREVIOUS ENGLISH: Our Dues", "# PREVIOUS TRANSLATION: Unsere Beiträge"])
        j = lines.index(' b:0 "New"')
        self.assertFalse(lines[j - 1].startswith("# PREVIOUS"))  # a new key has none

    def test_dev_only_files_are_not_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("te_x_l_english.yml", *t.DEV_ONLY_FILES):
                with open(os.path.join(tmp, name), "w", encoding="utf-8-sig") as fh:
                    fh.write(f'l_english:\n {name[:4]}key:0 "Text"\n')
            self.assertEqual([e.file for e in t.load_english(tmp)], ["te_x_l_english.yml"])


class GlossaryMatchTests(unittest.TestCase):
    def test_multiword_terms_match_in_any_case_lone_words_as_written(self):
        chunk = [t.Entry("te_x_l_english.yml", "a", "Escalates the diplomatic play over green fields.")]
        lines = t.chunk_glossary(chunk, {}, None, set(), "de",
                                 terms={"Diplomatic Play": "Diplomatiespiel", "Green": "Grüne"})
        self.assertIn("#   Diplomatic Play => Diplomatiespiel", lines)
        self.assertFalse(any("Grüne" in line for line in lines))


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
        forms = "\n".join(f' AFU_{f}:0 "die Afrikanische Union"' for f in t.COUNTRY_FORMS["german"])
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
        self.assertEqual(t.cmd_merge(args), 1)  # law_x is still rejected
        tm = t.load_tm("german")
        self.assertEqual(tm["AFU"]["de"], "Afrikanische Union")
        self.assertEqual(tm["AFU_DAT"], {"en": "African Union", "de": "die Afrikanische Union", "base": "AFU"})
        self.assertNotIn("law_x", tm)  # dropped its concept link
        self.assertEqual(tm["law_y"]["de"], "Er sagte „Hallo“")  # bare quotes repaired
        with open(os.path.join(self.dirs[1], "merge_report.json"), encoding="utf-8") as fh:
            rejected = json.load(fh)["names-001"]["rejected"]
        self.assertTrue(any("concept links" in e for e in rejected["law_x"]))
        # The country forms live in the base key's file.
        self.assertTrue(os.path.isfile(os.path.join(self.dirs[0], "tm", "te_formable_countries.json")))

    def test_refresh_keeps_country_forms_and_previous_translations(self):
        with open(os.path.join(self.dirs[1], "manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        manifest["names-001"]["previous"] = {"law_y": {"en": "Old plain", "de": "Alt"}}
        with open(os.path.join(self.dirs[1], "manifest.json"), "w", encoding="utf-8") as fh:
            json.dump(manifest, fh)
        with mock.patch.object(t, "VanillaTerms", lambda language: None):
            t.cmd_refresh(mock.Mock(language="german", field="de", chunks=["names-001"]))
        with open(os.path.join(self.dirs[1], "chunks", "names-001.txt"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("=== COUNTRY NAME FORMS ===", text)
        self.assertIn("# PREVIOUS TRANSLATION: Alt", text)


class RespellTests(unittest.TestCase):
    """respell keeps a translation whose English changed only to American
    spelling, and leaves any other change stale."""

    def test_spelling_only_change_is_re_pointed(self):
        entries = [
            t.Entry("te_laws_l_english.yml", "law_a", "A license for the center"),
            t.Entry("te_laws_l_english.yml", "law_b", "Ten policies are national"),
            t.Entry("te_formable_countries_l_english.yml", "AFU", "African Labor Union"),
        ]
        tm = {
            "law_a": {"en": "A licence for the centre", "de": "Eine Lizenz für das Zentrum"},
            "law_b": {"en": "Nine policies are national", "de": "Neun Maßnahmen sind national"},
            "AFU": {"en": "African Labour Union", "de": "Afrikanische Arbeiterunion"},
            "AFU_DAT": {"en": "African Labour Union", "de": "der Afrikanischen Arbeiterunion", "base": "AFU"},
        }
        with tempfile.TemporaryDirectory() as root:
            dirs = (os.path.join(root, "i18n", "german"), os.path.join(root, "build", "i18n", "german"))
            with mock.patch.object(t, "language_dirs", lambda language: dirs), \
                    mock.patch.object(t, "load_english", lambda english_dir=None: entries):
                t.save_tm(tm, entries, "german")
                self.assertEqual(t.respelled_keys(t.load_tm("german"), entries), ["AFU", "AFU_DAT", "law_a"])
                self.assertEqual(t.main(["respell"]), 0)
                after = t.load_tm("german")
        self.assertEqual(after["law_a"], {"en": "A license for the center", "de": "Eine Lizenz für das Zentrum"})
        self.assertEqual(after["AFU_DAT"]["en"], "African Labor Union")
        self.assertEqual(after["law_b"]["en"], "Nine policies are national")  # a real change stays stale


CM_FILE = "te_culture_merges_generated_l_english.yml"


def _merge_lines(merges: dict[str, tuple[str, str]], switched: str = "have all switched to") -> list:
    """Two culture-merge templates, as gen_culture_merges.py writes them, per merge."""
    out = []
    for merge, (core_1, core_2) in merges.items():
        out.append(t.Entry(CM_FILE, f"te_cmg_start_{merge}_button", f"Begin the $cm_{merge}$ Merge"))
        out.append(t.Entry(CM_FILE, f"te_cmg_{merge}_done_core_tt", f"${core_1}$ and ${core_2}$ pops {switched} $cm_{merge}$."))
    return out


class TemplateTests(unittest.TestCase):
    """prepare --templates groups a generated file's lines by template; expand
    writes each example's siblings by swapping in their tokens."""

    def test_expanding_an_examples_english_reproduces_each_sibling(self):
        hold = ("${b}$ pops are out of reach: our sphere holds only "
                "[ROOT.GetCountry.MakeScope.Var('te_cm_held_{m}_{b}').GetValue|%0] of them in their homeland, "
                "and [ROOT.GetCountry.MakeScope.ScriptValue('te_cm_hold_open')|%0] is needed.")
        merges = {"american": ("yankee", "dixie"), "iberian": ("spanish", "portuguese"), "nordic": ("norwegian", "swedish")}
        entries = _merge_lines(merges) + [
            t.Entry(CM_FILE, f"je_te_cm_{m}_status_hold_{b}", hold.format(m=m, b=b)) for m, (_, b) in merges.items()]
        groups = t.template_groups(entries)
        self.assertEqual([[e.key for e in g] for g in groups], [
            ["te_cmg_start_american_button", "te_cmg_start_iberian_button", "te_cmg_start_nordic_button"],
            ["te_cmg_american_done_core_tt", "te_cmg_iberian_done_core_tt", "te_cmg_nordic_done_core_tt"],
            ["je_te_cm_american_status_hold_dixie", "je_te_cm_iberian_status_hold_portuguese",
             "je_te_cm_nordic_status_hold_swedish"],
        ])
        for example, *siblings in groups:
            for sibling in siblings:
                self.assertEqual(t.expand_template(example.en, example.en, sibling.en), (sibling.en, None))
        # The translation takes the same swaps, wherever it moved the tokens.
        example, sibling = groups[1][0], groups[1][2]
        de = "Alle Pops der Kulturen $yankee$ und $dixie$ sind zu $cm_american$ übergegangen."
        self.assertEqual(t.expand_template(example.en, de, sibling.en),
                         ("Alle Pops der Kulturen $norwegian$ und $swedish$ sind zu $cm_nordic$ übergegangen.", None))

    def test_a_line_the_swap_cannot_reproduce_starts_its_own_group(self):
        # $dixie$ varies, but the call holding another $dixie$ doesn't, and
        # the swap would change both.
        entries = [t.Entry(CM_FILE, "a", "$dixie$ joins [Concept('concept_culture', '$dixie$ kin')]"),
                   t.Entry(CM_FILE, "b", "$yankee$ joins [Concept('concept_culture', '$dixie$ kin')]")]
        self.assertIsNotNone(t.token_mapping(entries[0].en, entries[1].en))
        self.assertNotEqual(t.expand_template(entries[0].en, entries[0].en, entries[1].en)[0], entries[1].en)
        self.assertEqual(len(t.template_groups(entries)), 2)

    def test_inconsistent_token_mapping_starts_its_own_group(self):
        entries = [t.Entry(CM_FILE, k, en) for k, en in [
            ("a", "$x$ and $x$ join"), ("b", "$y$ and $y$ join"),  # x -> y, consistently
            ("c", "$y$ and $z$ join"),  # x -> y and x -> z: a's swap can't make it
            ("d", "$w$ and $v$ join"),  # c's template: y -> w, z -> v
        ]]
        self.assertIsNone(t.token_mapping(entries[0].en, entries[2].en))
        self.assertEqual([[e.key for e in g] for g in t.template_groups(entries)], [["a", "b"], ["c", "d"]])

    def test_a_surviving_example_token_blocks_a_sibling(self):
        # A concept call's display text is free, so the translation may change
        # it, and merge's markup check would pass the unswapped copy.
        example = "Merges [Concept('concept_culture', '$dixie|q$')] pops"
        sibling = "Merges [Concept('concept_culture', '$yankee|q$')] pops"
        de = "Verschmilzt Pops der [Concept('concept_culture', 'Kultur $dixie|q$')]"
        self.assertEqual(t.check_translation(sibling, de)[0], [])
        value, problem = t.expand_template(example, de, sibling)
        self.assertIsNone(value)
        self.assertIn("dixie", problem)
        # A case flag on a varying call: its literal form isn't there to swap.
        example = "[ROOT.Var('te_cm_sol_best_american').GetCulture.GetName] pops are the best off"
        sibling = "[ROOT.Var('te_cm_sol_best_iberian').GetCulture.GetName] pops are the best off"
        de = "Am besten gestellt sind die [ROOT.Var('te_cm_sol_best_american').GetCulture.GetName|l]en Pops"
        value, problem = t.expand_template(example, de, sibling)
        self.assertIsNone(value)
        self.assertIn("te_cm_sol_best_american", problem)
        # A seed whose translation can't expand onto a line doesn't take it.
        entries = [t.Entry(CM_FILE, "a", example), t.Entry(CM_FILE, "b", sibling)]
        self.assertEqual(len(t.template_groups(entries, {"a": de})), 2)


class TemplateRunTests(unittest.TestCase):
    """prepare --templates, merge, expand and merge again, on a mock English."""

    MERGES = {"american": ("yankee", "dixie"), "iberian": ("spanish", "portuguese"), "nordic": ("norwegian", "swedish")}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.dirs = (os.path.join(root, "i18n", "german"), os.path.join(root, "build", "i18n", "german"))
        self.entries = _merge_lines(self.MERGES) + [
            t.Entry("te_culture_merges_l_english.yml", "te_cm_panel_hint", "Merges run for decades.")]
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

    def manifest(self) -> dict:
        with open(os.path.join(self.dirs[1], "manifest.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def agent_writes(self, cid: str, values: dict[str, str]) -> None:
        os.makedirs(os.path.join(self.dirs[1], "out"), exist_ok=True)
        with open(os.path.join(self.dirs[1], "out", cid + ".01.txt"), "w", encoding="utf-8") as fh:
            fh.write("".join(f' {k}:0 "{v}"\n' for k, v in values.items()))

    def test_examples_merge_then_copies_expand_and_a_changed_template_is_redone(self):
        t.main(["prepare", "--templates", "te_culture_merges_generated", "--no-vanilla"])
        manifest = self.manifest()
        self.assertEqual(list(manifest["c-001"]["keys"]), [
            "te_cmg_start_american_button", "te_cmg_american_done_core_tt", "te_cm_panel_hint"])
        self.assertEqual(manifest["x-001"]["examples"], {
            "te_cmg_start_iberian_button": "te_cmg_start_american_button",
            "te_cmg_start_nordic_button": "te_cmg_start_american_button",
            "te_cmg_iberian_done_core_tt": "te_cmg_american_done_core_tt",
            "te_cmg_nordic_done_core_tt": "te_cmg_american_done_core_tt",
        })
        with open(os.path.join(self.dirs[1], "chunks", "c-001.txt"), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        i = lines.index(' te_cmg_american_done_core_tt:0 "$yankee$ and $dixie$ pops have all switched to $cm_american$."')
        self.assertTrue(lines[i - 1].startswith("# TEMPLATE: the script copies this translation to 2 more lines, "
                                                "replacing $yankee$, $dixie$, $cm_american$ with each line's own."),
                        lines[i - 1])
        self.assertIn("2 of them are templates a script copies to other lines", self._prompt("c-001"))

        self.assertEqual(t.main(["expand"]), 1)  # nothing has merged: every copy waits
        self.assertFalse(os.path.exists(os.path.join(self.dirs[1], "out", "x-001.01.txt")))
        self.agent_writes("c-001", {
            "te_cmg_start_american_button": "Verschmelzung $cm_american$ beginnen",
            "te_cmg_american_done_core_tt": "Alle Pops der Kulturen $yankee$ und $dixie$ sind zu $cm_american$ übergegangen.",
            "te_cm_panel_hint": "Verschmelzungen dauern Jahrzehnte.",
        })
        self.assertEqual(t.main(["merge", "c-001"]), 0)
        self.assertEqual(t.main(["expand"]), 0)
        self.assertEqual(t.main(["merge", "x-001"]), 0)
        tm = t.load_tm("german")
        self.assertEqual(tm["te_cmg_start_nordic_button"], {"en": "Begin the $cm_nordic$ Merge",
                                                            "de": "Verschmelzung $cm_nordic$ beginnen"})
        self.assertEqual(tm["te_cmg_iberian_done_core_tt"]["de"],
                         "Alle Pops der Kulturen $spanish$ und $portuguese$ sind zu $cm_iberian$ übergegangen.")

        # The generator rewrites one template: all its copies go stale together.
        self.entries[:] = _merge_lines(self.MERGES, "have all become") + self.entries[-1:]
        t.main(["prepare", "--templates", "te_culture_merges_generated", "--no-vanilla"])
        manifest = self.manifest()
        self.assertEqual(list(manifest["c-002"]["keys"]), ["te_cmg_american_done_core_tt"])
        self.assertIn("te_cmg_american_done_core_tt", manifest["c-002"]["previous"])
        self.assertEqual(sorted(manifest["x-002"]["examples"]), ["te_cmg_iberian_done_core_tt", "te_cmg_nordic_done_core_tt"])
        # Until the new example merges, its old translation is not copied.
        self.assertEqual(t.main(["expand", "x-002"]), 1)
        self.assertFalse(os.path.exists(os.path.join(self.dirs[1], "out", "x-002.01.txt")))
        self.agent_writes("c-002", {"te_cmg_american_done_core_tt":
                                    "Alle Pops der Kulturen $yankee$ und $dixie$ sind nun $cm_american$."})
        t.main(["merge", "c-002"])
        self.assertEqual(t.main(["expand", "x-002"]), 0)
        self.assertEqual(t.main(["merge", "x-002"]), 0)
        tm = t.load_tm("german")
        self.assertEqual(tm["te_cmg_nordic_done_core_tt"], {
            "en": "$norwegian$ and $swedish$ pops have all become $cm_nordic$.",
            "de": "Alle Pops der Kulturen $norwegian$ und $swedish$ sind nun $cm_nordic$."})
        self.assertEqual(t.classify(self.entries, tm)["translated"], self.entries)

    def test_a_new_copy_expands_from_the_memory_without_an_agent(self):
        sol = "[ROOT.Var('te_cm_sol_best_{m}').GetCulture.GetName] pops are the best off"
        known = {"american": ("yankee", "dixie")}
        self.entries[:] = _merge_lines(known) + [t.Entry(CM_FILE, "te_cm_american_sol", sol.format(m="american"))]
        tm = {
            "te_cmg_start_american_button": {"en": "Begin the $cm_american$ Merge", "de": "Verschmelzung $cm_american$ beginnen"},
            "te_cmg_american_done_core_tt": {"en": self.entries[1].en, "de": "Alle Pops von $yankee$ und $dixie$ sind $cm_american$."},
            # A case flag on the varying call: this translation can't be copied.
            "te_cm_american_sol": {"en": self.entries[2].en,
                                   "de": "Die [ROOT.Var('te_cm_sol_best_american').GetCulture.GetName|l]en Pops stehen am besten da"},
        }
        t.save_tm(tm, self.entries, "german")
        # The generator adds a merge.
        self.entries[:] = self.entries + _merge_lines({"nordic": ("norwegian", "swedish")}) + [
            t.Entry(CM_FILE, "te_cm_nordic_sol", sol.format(m="nordic"))]
        t.main(["prepare", "--templates", "te_culture_merges_generated", "--no-vanilla"])
        manifest = self.manifest()
        self.assertEqual(list(manifest["c-001"]["keys"]), ["te_cm_nordic_sol"])  # an agent writes it
        self.assertNotIn("templates", manifest["c-001"])
        self.assertEqual(manifest["x-001"]["examples"], {
            "te_cmg_start_nordic_button": "te_cmg_start_american_button",
            "te_cmg_nordic_done_core_tt": "te_cmg_american_done_core_tt",
        })
        self.assertEqual(t.main(["expand"]), 0)  # no agent needed for these
        self.assertEqual(t.main(["merge", "x-001"]), 0)
        self.assertEqual(t.load_tm("german")["te_cmg_nordic_done_core_tt"]["de"],
                         "Alle Pops von $norwegian$ und $swedish$ sind $cm_nordic$.")

    def _prompt(self, cid: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            t.main(["prompt", cid])
        return out.getvalue()


class SpanishNamesTests(unittest.TestCase):
    """A language vanilla doesn't decline gets no country-forms section, and
    its merge expects none."""

    def test_names_chunk_and_merge_without_country_forms(self):
        entries = [
            t.Entry("te_formable_countries_l_english.yml", "AFU", "African Union"),
            t.Entry("te_laws_l_english.yml", "law_x", "Free Port"),
        ]
        with tempfile.TemporaryDirectory() as root:
            dirs = (os.path.join(root, "i18n", "spanish"), os.path.join(root, "build", "i18n", "spanish"))
            with mock.patch.object(t, "language_dirs", lambda language: dirs), \
                    mock.patch.object(t, "load_english", lambda english_dir=None: entries):
                t.main(["--language", "spanish", "prepare", "--set", "names", "--no-vanilla"])
                with open(os.path.join(dirs[1], "chunks", "names-001.txt"), encoding="utf-8") as fh:
                    self.assertNotIn("COUNTRY NAME FORMS", fh.read())
                os.makedirs(os.path.join(dirs[1], "out"))
                with open(os.path.join(dirs[1], "out", "names-001.01.txt"), "w", encoding="utf-8") as fh:
                    fh.write(' AFU:0 "Unión Africana"\n law_x:0 "Puerto franco"\n')
                self.assertEqual(t.main(["--language", "spanish", "merge"]), 0)
                self.assertEqual(t.load_tm("spanish")["AFU"], {"en": "African Union", "es": "Unión Africana"})


if __name__ == "__main__":
    unittest.main()
