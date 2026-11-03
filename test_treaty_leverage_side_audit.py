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

from treaty_leverage_side_audit import (
    audit,
    render_report,
    scan_involvement_text,
    scan_text,
    strict_failures,
)


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

    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line number and Coverage no file or
        judged-article count, so the report changes only when the findings do."""
        from treaty_leverage_side_audit import AuditResult, Flag
        result = AuditResult(
            flags=[Flag("common/treaty_articles/a.txt", 20, "request_influence", 3,
                        "source_modifier", "source_country",
                        exemption={"date": "2026-09-21", "rationale": "petitioner pays"}),
                   Flag("common/treaty_articles/b.txt", 45, "grant_loan", 30,
                        "target_modifier", "target_country")],
            files_audited=17, articles_checked=14, articles_undetermined=0,
        )
        report = render_report(result)
        self.assertIn(
            "- `common/treaty_articles/a.txt` — `request_influence`: leverage in "
            "`source_modifier` with `maintenance_paid_by = source_country` — "
            "**2026-09-21**: petitioner pays", report)
        self.assertNotIn("a.txt:20", report)
        self.assertIn("- line 45: `grant_loan` (opened at line 30)", report)  # unreviewed keeps its lines
        for gone in ("files audited", "directed articles judged", "17", "14"):
            self.assertNotIn(gone, report)
        self.assertIn("- articles with a leverage line but no `maintenance_paid_by`: 0",
                      report)

    def test_missing_treaty_articles_dir_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = audit(mod_path=tmp)
        self.assertEqual(result.files_audited, 0)
        self.assertEqual(result.flags, [])


def _inv(text: str):
    return scan_involvement_text(text, "test.txt")


def _inv_article(
    name="an_article",
    kind="directed",
    maint="source_country",
    lev_side=None,
    max_inv="1000",
    applies="target_country",
    opener_comment="",
    max_comment="",
):
    """A treaty article with the involvement fields; None leaves a field out."""
    lines = [f"{name} = {{{opener_comment}", f"\tkind = {kind}"]
    if maint:
        lines.append(f"\tmaintenance_paid_by = {maint}")
    if max_inv is not None:
        lines.append(f"\tmax_target_involvement = {max_inv}{max_comment}")
    if applies is not None:
        lines.append(f"\ttarget_involvement_applies_to = {applies}")
    if lev_side:
        lines += [
            f"\t{lev_side} = {{",
            "\t\tcountry_treaty_leverage_generation_add = 200",
            "\t}",
        ]
    lines.append("}")
    return "\n".join(lines) + "\n"


def _kinds(flags):
    return [f.kind for f in flags]


TAG = "  # REVIEWED 2026-11-03 (involvement): a one-off transfer"


class InvolvementDetectionTests(unittest.TestCase):
    """Every mod treaty article declares the Involvement it builds, on the
    side vanilla would put it, or carries a reviewed reason it builds none."""

    def test_clean_directed_article(self):
        # Pays from the source, so the target is the local side.
        self.assertEqual(_inv(_inv_article()), [])

    def test_clean_mutual_article(self):
        self.assertEqual(
            _inv(_inv_article(kind="mutual", maint=None, applies="mutual")), []
        )

    def test_missing_involvement(self):
        flags = _inv(_inv_article(max_inv=None, applies=None))
        self.assertEqual(_kinds(flags), ["missing_involvement"])
        self.assertEqual(flags[0].article, "an_article")
        self.assertEqual(flags[0].line, 1)
        self.assertIsNone(flags[0].exemption)

    def test_side_without_a_maximum_is_missing_involvement(self):
        flags = _inv(_inv_article(max_inv=None))
        self.assertEqual(_kinds(flags), ["missing_involvement"])

    def test_missing_side(self):
        # The engine defaults a missing side to source_country, silently.
        flags = _inv(_inv_article(applies=None))
        self.assertEqual(_kinds(flags), ["missing_side"])
        self.assertEqual(flags[0].line, 4)

    def test_mutual_article_needs_mutual_side(self):
        flags = _inv(_inv_article(kind="mutual", maint=None, applies="source_country"))
        self.assertEqual(_kinds(flags), ["kind_mismatch"])

    def test_directed_article_cannot_use_mutual(self):
        flags = _inv(_inv_article(applies="mutual"))
        self.assertEqual(_kinds(flags), ["kind_mismatch"])

    def test_wrong_side_against_the_leverage_line(self):
        # Leverage generated against the target: the target is the local side.
        flags = _inv(
            _inv_article(maint="source_country", lev_side="target_modifier",
                         applies="source_country")
        )
        self.assertEqual(_kinds(flags), ["wrong_side"])
        self.assertIn("target_modifier", flags[0].detail)

    def test_leverage_side_wins_over_the_maintenance_proxy(self):
        # request_influence: the petitioner pays and is leveraged, so it is
        # also the local side the bloc leader gains Involvement in.
        flags = _inv(
            _inv_article(maint="source_country", lev_side="source_modifier",
                         applies="source_country")
        )
        self.assertEqual(flags, [])

    def test_wrong_side_against_maintenance(self):
        # Foreign investment rights: the investor (target) pays, so the
        # local side is the source. Naming the payer is backwards.
        flags = _inv(_inv_article(maint="target_country", applies="target_country"))
        self.assertEqual(_kinds(flags), ["wrong_side"])
        self.assertIn("maintenance_paid_by", flags[0].detail)

    def test_no_side_judgement_without_leverage_or_maintenance(self):
        flags = _inv(_inv_article(maint=None, applies="source_country"))
        self.assertEqual(flags, [])

    def test_bad_values(self):
        for value in ("0", "-5", "6000", "lots"):
            with self.subTest(value=value):
                self.assertEqual(_kinds(_inv(_inv_article(max_inv=value))), ["bad_value"])

    def test_the_treaty_cap_itself_is_allowed(self):
        self.assertEqual(_inv(_inv_article(max_inv="5000")), [])

    def test_unknown_side_value(self):
        self.assertEqual(_kinds(_inv(_inv_article(applies="both"))), ["bad_value"])

    def test_commented_out_field_counts_as_missing(self):
        text = (
            "an_article = {\n"
            "\tkind = directed\n"
            "\t# max_target_involvement = 1000\n"
            "\t# target_involvement_applies_to = target_country\n"
            "}\n"
        )
        self.assertEqual(_kinds(_inv(text)), ["missing_involvement"])

    def test_fields_in_a_nested_block_do_not_count(self):
        text = (
            "an_article = {\n"
            "\tkind = directed\n"
            "\tai = {\n"
            "\t\tmax_target_involvement = 1000\n"
            "\t\ttarget_involvement_applies_to = target_country\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(_kinds(_inv(text)), ["missing_involvement"])

    def test_inject_into_an_existing_article_is_skipped(self):
        # The article it extends keeps its own fields.
        text = "INJECT:alliance = {\n\tflags = { friendly }\n}\n"
        self.assertEqual(_inv(text), [])

    def test_state_does_not_leak_between_articles(self):
        text = _inv_article(name="first") + _inv_article(
            name="second", max_inv=None, applies=None
        )
        flags = _inv(text)
        self.assertEqual([(f.article, f.kind) for f in flags],
                         [("second", "missing_involvement")])


class InvolvementExemptionTests(unittest.TestCase):
    def test_tagged_comment_on_the_opener_suppresses(self):
        flags = _inv(_inv_article(max_inv=None, applies=None, opener_comment=TAG))
        self.assertEqual(_kinds(flags), ["missing_involvement"])
        self.assertEqual(flags[0].exemption["date"], "2026-11-03")
        self.assertIn("one-off", flags[0].exemption["rationale"])

    def test_tagged_comment_on_the_maximum_line_suppresses(self):
        flags = _inv(_inv_article(maint="target_country", applies="target_country",
                                  max_comment=TAG))
        self.assertEqual(_kinds(flags), ["wrong_side"])
        self.assertIsNotNone(flags[0].exemption)

    def test_untagged_reviewed_does_not_suppress(self):
        flags = _inv(_inv_article(
            max_inv=None, applies=None,
            opener_comment="  # REVIEWED 2026-11-03: a one-off transfer"))
        self.assertIsNone(flags[0].exemption)

    def test_another_checks_tag_does_not_suppress(self):
        flags = _inv(_inv_article(
            max_inv=None, applies=None,
            opener_comment="  # REVIEWED 2026-11-03 (amendment_reachability): x"))
        self.assertIsNone(flags[0].exemption)

    def test_stale_tag_is_flagged_and_cannot_be_exempted(self):
        flags = _inv(_inv_article(opener_comment=TAG))
        self.assertEqual(_kinds(flags), ["stale_review"])
        self.assertEqual(flags[0].line, 1)
        self.assertIsNone(flags[0].exemption)

    def test_involvement_tag_does_not_blind_the_leverage_check(self):
        text = (
            "an_article = {" + TAG + "\n"
            "\tkind = directed\n"
            "\tmaintenance_paid_by = source_country\n"
            "\tsource_modifier = {\n"
            "\t\tcountry_treaty_leverage_generation_add = 200\n"
            "\t}\n"
            "}\n"
        )
        flags = _scan(text)
        self.assertEqual(len(flags), 1)
        self.assertIsNone(flags[0].exemption)


class InvolvementIntegrationTests(unittest.TestCase):
    def _audit(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            d = os.path.join(tmp, "common", "treaty_articles")
            os.makedirs(d)
            with open(os.path.join(d, "01_a.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write(text)
            return audit(mod_path=tmp)

    def test_audit_collects_involvement_flags_and_counts(self):
        result = self._audit(
            _inv_article(name="good_one")
            + _inv_article(name="silent_one", max_inv=None, applies=None)
            + _inv_article(name="transfer_one", max_inv=None, applies=None,
                           opener_comment=TAG)
        )
        self.assertEqual(
            [(f.article, f.kind) for f in result.involvement_flags],
            [("silent_one", "missing_involvement"),
             ("transfer_one", "missing_involvement")],
        )
        self.assertEqual(result.articles_with_involvement, 1)
        self.assertEqual(result.articles_reviewed_without_involvement, 1)
        report = render_report(result)
        self.assertIn("## Involvement", report)
        self.assertIn("`silent_one`", report)
        self.assertIn("**2026-11-03**: a one-off transfer", report)
        self.assertEqual(strict_failures(result), 1)

    def test_strict_counts_both_checks(self):
        result = self._audit(
            _inv_article(name="silent_one", max_inv=None, applies=None)
            + _article(name="bad_lev", maint="source_country", side="source_modifier")
        )
        # bad_lev fails twice: leverage on the payer, and no involvement.
        self.assertEqual(strict_failures(result), 3)

    def test_clean_tree_passes_strict(self):
        result = self._audit(_inv_article(name="good_one"))
        self.assertEqual(strict_failures(result), 0)


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

    def test_mod_tree_declares_involvement_or_says_why_not(self):
        repo = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isdir(os.path.join(repo, "common", "treaty_articles")):
            self.skipTest("no treaty_articles/ in this checkout")
        result = audit(mod_path=repo)
        unreviewed = [f for f in result.involvement_flags if not f.exemption]
        self.assertEqual(
            unreviewed,
            [],
            "treaty articles with an Involvement problem: "
            + ", ".join(f"{f.article} {f.kind} ({f.file}:{f.line})" for f in unreviewed),
        )


if __name__ == "__main__":
    unittest.main()
