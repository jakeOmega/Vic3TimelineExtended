"""Unit tests for treaty_leverage_side_audit.

`country_treaty_leverage_generation_add` generates leverage *against* the
country whose modifier block carries it. Vanilla's own articles all put it on
the side that does **not** pay `maintenance_paid_by` — the beneficiary pays the
upkeep, the party being leaned on carries the leverage. The audit flags any
directed article where the two land on the same side.

The crux is discrimination: flag only when the article is directed, has a
`maintenance_paid_by` to compare against, and the leverage line sits in the
paying side's own modifier block. Mutual articles, articles with no leverage
line, and articles with no maintenance side must stay silent.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from treaty_leverage_side_audit import audit, render_report, scan_text


def _scan(text: str):
    return scan_text(text, "test.txt")


ARTICLE_TEMPLATE = (
    "{name} = {{\n"
    "\tkind = directed\n"
    "\tmaintenance_paid_by = {maint}\n"
    "\n"
    "\t{side} = {{\n"
    "\t\tcountry_treaty_leverage_generation_add = 200\n"
    "\t}}\n"
    "}}\n"
)


def _article(name="an_article", maint="source_country", side="target_modifier"):
    return ARTICLE_TEMPLATE.format(name=name, maint=maint, side=side)


class DetectionTests(unittest.TestCase):
    def test_flags_leverage_on_the_maintenance_paying_side(self):
        flags = _scan(_article(maint="source_country", side="source_modifier"))
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].article, "an_article")
        self.assertEqual(flags[0].side, "source_modifier")
        self.assertEqual(flags[0].maintenance_paid_by, "source_country")
        self.assertEqual(flags[0].line, 6)
        self.assertEqual(flags[0].article_line, 1)

    def test_reproduces_currency_peg_inversion(self):
        # The historical case: the anchor pays the upkeep AND carried the
        # leverage line, so the pegger accumulated influence over its anchor.
        flags = _scan(
            "currency_peg = {\n"
            "\tkind = directed\n"
            "\tmaintenance_paid_by = target_country\n"
            "\n"
            "\ttarget_modifier = {\n"
            "\t\tcountry_prestige_mult = 0.02\n"
            "\t\tcountry_treaty_leverage_generation_add = 200\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].article, "currency_peg")
        self.assertEqual(flags[0].side, "target_modifier")
        self.assertEqual(flags[0].maintenance_paid_by, "target_country")
        self.assertEqual(flags[0].line, 7)

    def test_no_flag_when_leverage_opposes_maintenance(self):
        self.assertEqual(_scan(_article(maint="source_country", side="target_modifier")), [])
        self.assertEqual(_scan(_article(maint="target_country", side="source_modifier")), [])

    def test_no_flag_for_mutual_modifier(self):
        # A mutual block has no side to be wrong about.
        flags = _scan(
            "intelligence_sharing_pact = {\n"
            "\tkind = mutual\n"
            "\tmutual_modifier = {\n"
            "\t\tcountry_treaty_leverage_generation_add = 300\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_when_article_has_no_maintenance_paid_by(self):
        # Nothing to compare against — the heuristic does not apply.
        flags = _scan(
            "an_article = {\n"
            "\tkind = directed\n"
            "\ttarget_modifier = {\n"
            "\t\tcountry_treaty_leverage_generation_add = 200\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_no_flag_for_article_without_a_leverage_line(self):
        flags = _scan(
            "an_article = {\n"
            "\tkind = directed\n"
            "\tmaintenance_paid_by = source_country\n"
            "\tsource_modifier = {\n"
            "\t\tcountry_prestige_mult = 0.02\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_leverage_outside_a_modifier_block_is_not_attributed_to_a_side(self):
        # A bare occurrence (e.g. inside an effect or a comment-free stray) has
        # no side, so it cannot be judged.
        flags = _scan(
            "an_article = {\n"
            "\tkind = directed\n"
            "\tmaintenance_paid_by = source_country\n"
            "\ton_entry_into_force = {\n"
            "\t\tcountry_treaty_leverage_generation_add = 200\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(flags, [])

    def test_flags_each_offending_article_in_a_multi_article_file(self):
        text = (
            _article(name="good_one", maint="source_country", side="target_modifier")
            + _article(name="bad_one", maint="source_country", side="source_modifier")
            + _article(name="other_bad", maint="target_country", side="target_modifier")
        )
        flags = _scan(text)
        self.assertEqual([f.article for f in flags], ["bad_one", "other_bad"])

    def test_nested_block_inside_a_modifier_side_does_not_leak_to_the_next_article(self):
        text = (
            "first = {\n"
            "\tkind = directed\n"
            "\tmaintenance_paid_by = target_country\n"
            "\tsource_modifier = {\n"
            "\t\tcountry_treaty_leverage_generation_add = 200\n"
            "\t}\n"
            "\tai = {\n"
            "\t\tinherent_accept_score = {\n"
            "\t\t\tvalue = 0\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        ) + _article(name="second", maint="source_country", side="source_modifier")
        flags = _scan(text)
        self.assertEqual([f.article for f in flags], ["second"])

    def test_ignores_a_commented_out_leverage_line(self):
        flags = _scan(
            "an_article = {\n"
            "\tkind = directed\n"
            "\tmaintenance_paid_by = source_country\n"
            "\tsource_modifier = {\n"
            "\t\t# country_treaty_leverage_generation_add = 200\n"
            "\t\tcountry_prestige_mult = 0.02\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(flags, [])


class ExemptionTests(unittest.TestCase):
    def test_reviewed_on_the_leverage_line_suppresses(self):
        flags = _scan(
            "request_influence = {\n"
            "\tkind = directed\n"
            "\tmaintenance_paid_by = source_country\n"
            "\tsource_modifier = {\n"
            "\t\tcountry_treaty_leverage_generation_add = 5000"
            "  # REVIEWED 2026-09-21: petitioner pays and is the one leveraged\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)
        self.assertEqual(flags[0].exemption["date"], "2026-09-21")
        self.assertIn("petitioner", flags[0].exemption["rationale"])

    def test_reviewed_on_the_article_opener_suppresses(self):
        flags = _scan(
            "request_influence = {  # REVIEWED 2026-09-21: petitioner pays and is leveraged\n"
            "\tkind = directed\n"
            "\tmaintenance_paid_by = source_country\n"
            "\tsource_modifier = {\n"
            "\t\tcountry_treaty_leverage_generation_add = 5000\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)

    def test_unreviewed_flag_has_no_exemption(self):
        flags = _scan(_article(maint="source_country", side="source_modifier"))
        self.assertEqual(len(flags), 1)
        self.assertIsNone(flags[0].exemption)


class IntegrationTests(unittest.TestCase):
    def test_walks_treaty_articles_dir_and_renders_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "common", "treaty_articles")
            os.makedirs(d)
            with open(os.path.join(d, "01_a.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write(_article(name="bad_one", maint="target_country", side="target_modifier"))
            with open(os.path.join(d, "02_b.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write(_article(name="good_one", maint="target_country", side="source_modifier"))

            result = audit(mod_path=tmp)

        self.assertEqual(result.files_audited, 2)
        self.assertEqual(len(result.flags), 1)
        self.assertEqual(result.flags[0].article, "bad_one")

        report = render_report(result)
        self.assertIn("bad_one", report)
        self.assertIn("common/treaty_articles/01_a.txt", report)
        self.assertIn("## Unreviewed Flags", report)

    def test_report_reports_none_when_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "common", "treaty_articles")
            os.makedirs(d)
            with open(os.path.join(d, "01_a.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write(_article(name="good_one", maint="source_country", side="target_modifier"))
            result = audit(mod_path=tmp)

        self.assertEqual(result.flags, [])
        report = render_report(result)
        self.assertIn("_None._", report)

    def test_missing_treaty_articles_dir_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = audit(mod_path=tmp)
        self.assertEqual(result.files_audited, 0)
        self.assertEqual(result.flags, [])


class RealModTests(unittest.TestCase):
    """The mod's own `common/treaty_articles/` must stay clean."""

    def test_mod_tree_has_no_unreviewed_flags(self):
        repo = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isdir(os.path.join(repo, "common", "treaty_articles")):
            self.skipTest("no treaty_articles/ in this checkout")
        result = audit(mod_path=repo)
        unreviewed = [f for f in result.flags if not f.exemption]
        self.assertEqual(
            unreviewed,
            [],
            "leverage line sits on the maintenance-paying side in: "
            + ", ".join(f"{f.article} ({f.file}:{f.line})" for f in unreviewed),
        )


if __name__ == "__main__":
    unittest.main()
