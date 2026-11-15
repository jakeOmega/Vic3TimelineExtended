"""Unit tests for modifier_name_audit (2026-11-15).

Each fixture is a throwaway mod tree: a vanilla loc snapshot, a modifier type
definition file, a static modifier file and English loc. The crux: a name is
measured as rendered, a figure is judged on modifier types only, a sentence
break is told from an abbreviation, and the tagged suppression, stale tags
included. The last class runs the audit on the mod itself.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modifier_name_audit import CHECK, MAX_NAME, REPORT_PATH, audit, main, name_checks, regenerate

ROOT = Path(__file__).resolve().parent


def _write(root: str, rel: str, text: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write(text)


class _Fixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        os.makedirs(os.path.join(self.root, "vanilla_parsed"))
        with open(os.path.join(self.root, "vanilla_parsed", "localization_english.json"), "w", encoding="utf-8") as fh:
            json.dump({"concept_trade_advantage": "Trade Advantage", "VANILLA_LONG": "y" * MAX_NAME}, fh)
        self.types("country_placeholder_add")

    def types(self, *names: str, prefix: str = "") -> None:
        body = "".join(f"{prefix}{n} = {{\n\tcolor = good\n\tscript_only = yes\n}}\n\n" for n in names)
        _write(self.root, "common/modifier_type_definitions/te_test_types.txt", body)

    def statics(self, *names: str) -> None:
        body = "".join(f"{n} = {{\n\tcountry_prestige_add = 1\n}}\n\n" for n in names)
        _write(self.root, "common/static_modifiers/te_test_modifiers.txt", body)

    def loc(self, *lines: str, name: str = "te_test_l_english.yml") -> None:
        _write(self.root, f"localization/english/{name}",
               "l_english:\n" + "".join(f" {line}\n" for line in lines))

    def flags(self, result=None):
        result = result or audit(self.root)
        return {f.key: f.checks for f in result.flags}


class NameChecksTests(unittest.TestCase):
    def test_a_label_passes(self):
        self.assertEqual(name_checks("Common Currency Trade Advantage", figures=True), [])

    def test_long(self):
        self.assertEqual(name_checks("x" * (MAX_NAME + 1), figures=True), ["long"])
        self.assertEqual(name_checks("x" * MAX_NAME, figures=True), [])

    def test_sentence_breaks(self):
        for text in ("Members adopt. Leaders issue", "One thing; another", "Add Ideology to X and Y.",
                     "Why not? Because"):
            with self.subTest(text=text):
                self.assertIn("sentence", name_checks(text, figures=True))

    def test_abbreviations_and_colons_are_not_sentences(self):
        for text in ("St. Louis Exchange Rights", "U.S. Navy Basing", "Census: Men at Work",
                     "Subjugation Strength (Trade)"):
            with self.subTest(text=text):
                self.assertEqual(name_checks(text, figures=True), [])

    def test_figures(self):
        for text in ("Adopters get +5% Trade", "−0.5 points of premium", "Relief 25%", "-1 Slot"):
            with self.subTest(text=text):
                self.assertIn("figure", name_checks(text, figures=True))

    def test_a_number_that_is_a_name_is_not_a_figure(self):
        for text in ("Boys per 100 Girls at Birth", "Fab 18 Max Level", "Year-2000 Compliance"):
            with self.subTest(text=text):
                self.assertEqual(name_checks(text, figures=True), [])

    def test_figures_can_be_left_out(self):
        self.assertEqual(name_checks("Agricultural Tax Relief 25%", figures=False), [])


class FlagTests(_Fixture):
    def test_the_monetary_union_paragraph(self):
        self.types("power_bloc_shared_currency_bool")
        self.loc('power_bloc_shared_currency_bool:0 "Members may adopt the leader’s currency: adopters get '
                 '#G +5%#! export and import advantage and #G +2%#! more pool contribution, none under excess"')
        self.assertEqual(self.flags(), {"power_bloc_shared_currency_bool": ["long", "figure"]})

    def test_rendered_not_raw(self):
        # Format codes count none and a concept one character: 80 raw characters, short rendered.
        self.types("country_te_trade_mult")
        self.loc('country_te_trade_mult:0 "#b Common Currency#! [concept_trade_advantage] [GetPlayer.GetName] '
                 '#tooltippable Edge#!"')
        self.assertEqual(self.flags(), {})

    def test_a_splice_is_expanded(self):
        self.types("country_te_spliced_add")
        self.loc('country_te_spliced_add:0 "$VANILLA_LONG$ Bonus"')
        self.assertEqual(self.flags(), {"country_te_spliced_add": ["long"]})

    def test_replace_and_inject_definitions_count(self):
        self.types("country_te_replaced_add", prefix="REPLACE:")
        self.loc('country_te_replaced_add:0 "Replaced; Badly"')
        self.assertEqual(self.flags(), {"country_te_replaced_add": ["sentence"]})

    def test_a_static_modifier_is_judged_for_length_and_sentences_not_figures(self):
        self.statics("te_tax_relief_1", "te_static_prose")
        self.loc('te_tax_relief_1:0 "Agricultural Tax Relief 25%"',
                 'te_static_prose:0 "We have done a thing. It was good"')
        self.assertEqual(self.flags(), {"te_static_prose": ["sentence"]})

    def test_a_name_without_mod_loc_is_skipped(self):
        self.types("country_te_unnamed_add")
        self.loc('other_key:0 "This is a sentence. Not a name"')
        self.assertEqual(self.flags(), {})

    def test_a_nested_key_is_not_a_definition(self):
        _write(self.root, "common/static_modifiers/te_test_modifiers.txt",
               "te_outer = {\n\tte_inner = { x = 1 }\n}\n")
        self.loc('te_inner:0 "Inner thing. Prose"', 'te_outer:0 "Outer"')
        self.assertEqual(self.flags(), {})

    def test_the_last_file_wins(self):
        self.types("country_te_twice_add")
        self.loc('country_te_twice_add:0 "Short"', name="te_a_l_english.yml")
        self.loc('country_te_twice_add:0 "Long one. Prose"', name="te_b_l_english.yml")
        self.assertEqual(self.flags(), {"country_te_twice_add": ["sentence"]})


class SuppressionTests(_Fixture):
    def test_a_tag_on_the_winning_line_suppresses(self):
        self.types("country_te_tagged_add")
        self.loc(f'country_te_tagged_add:0 "One. Two" # REVIEWED 2026-11-15 ({CHECK}): a quoted motto')
        result = audit(self.root)
        self.assertEqual(len(result.flags), 1)
        self.assertEqual(result.unreviewed, [])
        self.assertFalse(result.failed)

    def test_a_tag_on_a_clean_name_is_stale(self):
        self.types("country_te_clean_add")
        self.loc(f'country_te_clean_add:0 "Clean" # REVIEWED 2026-11-15 ({CHECK}): no longer needed')
        result = audit(self.root)
        self.assertEqual(len(result.stale), 1)
        self.assertTrue(result.failed)

    def test_another_audits_tag_does_not_suppress(self):
        self.types("country_te_other_add")
        self.loc('country_te_other_add:0 "One. Two" # REVIEWED 2026-11-15 (long_tooltip): wrong audit')
        self.assertEqual(len(audit(self.root).unreviewed), 1)


class CommandLineTests(_Fixture):
    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--mod-path", self.root, *args])
        return code, out.getvalue()

    def test_strict_fails_on_an_unreviewed_flag(self):
        self.types("country_te_bad_add")
        self.loc('country_te_bad_add:0 "Gets +5% more"')
        code, out = self.run_main("--strict")
        self.assertEqual(code, 1)
        self.assertIn("country_te_bad_add", out)
        self.assertEqual(self.run_main()[0], 0)

    def test_strict_passes_clean(self):
        self.loc('country_placeholder_add:0 "Placeholder"')
        self.assertEqual(self.run_main("--strict")[0], 0)

    def test_regenerate_writes_the_report(self):
        self.types("country_te_bad_add")
        self.loc('country_te_bad_add:0 "Gets +5% more"')
        with mock.patch("path_constants.mod_path", self.root):
            out = regenerate()
        self.assertEqual(out["unreviewed"], 1)
        report = Path(self.root, REPORT_PATH).read_text(encoding="utf-8")
        self.assertIn("country_te_bad_add", report)
        self.assertIn(f"# REVIEWED YYYY-MM-DD ({CHECK}): why", report)


class TheModTests(unittest.TestCase):
    def test_the_mod_has_no_unreviewed_flag(self):
        result = audit(ROOT)
        self.assertGreater(result.names_measured, 2000)
        self.assertEqual([f.message for f in result.failing if hasattr(f, "message")], [])
        self.assertEqual(result.stale, [])


if __name__ == "__main__":
    unittest.main()
