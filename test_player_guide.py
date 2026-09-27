"""Tests for the player guide tooling.

Covers the parts of ``scripts/build_player_guide.py`` that need neither pandoc
nor Typst (anchors, cross-chapter links, the source fingerprint and ``--check``)
and the rules of ``scripts/analysis/check_player_guide_style.py``.
"""

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

import build_player_guide as guide  # noqa: E402
import check_player_guide_style as style  # noqa: E402


class GuideDirTestCase(unittest.TestCase):
    """A throwaway guide folder with a template and the given chapters."""

    def make_guide(self, chapters: dict) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "template.typ").write_text("// template\n", encoding="utf-8")
        for name, text in chapters.items():
            (root / name).write_text(text, encoding="utf-8")
        return root


class SlugTests(unittest.TestCase):
    def test_matches_github_anchors(self):
        cases = {
            "The policy rate": "the-policy-rate",
            "Banking & monetary policy": "banking--monetary-policy",
            "Who holds the button?": "who-holds-the-button",
            "Tiers 1–5": "tiers-15",
            "The `Stabilize` preset": "the-stabilize-preset",
            "**Bold** heading": "bold-heading",
            "[Linked](04-banking.md) heading": "linked-heading",
            "CO₂ and warming": "co₂-and-warming",
        }
        for heading, slug in cases.items():
            with self.subTest(heading=heading):
                self.assertEqual(guide.github_slug(heading), slug)

    def test_headings_inside_code_fences_are_ignored(self):
        text = "# Title\n\n```\n# not a heading\n```\n\n## Real\n"
        self.assertEqual([h for _, _, h in guide.iter_headings(text)], ["Title", "Real"])


class CrossLinkTests(unittest.TestCase):
    def test_section_link_becomes_in_document_anchor(self):
        text = "See [the rate](04-banking.md#the-policy-rate)."
        self.assertEqual(guide.rewrite_cross_links(text, {}), "See [the rate](#the-policy-rate).")

    def test_bare_chapter_link_targets_its_first_heading(self):
        text = "See [banking](04-banking.md) and [space](15-space.md)."
        out = guide.rewrite_cross_links(text, {"04-banking.md": "banking-and-monetary-policy"})
        self.assertEqual(out, "See [banking](#banking-and-monetary-policy) and [space](15-space.md).")

    def test_external_and_local_links_untouched(self):
        text = "[a](https://example.com/x.md#y) [b](#local) [c](images/pic.png)"
        self.assertEqual(guide.rewrite_cross_links(text, {}), text)


class FingerprintTests(GuideDirTestCase):
    def test_changes_with_content_and_ignores_line_endings(self):
        root = self.make_guide({"01-a.md": "# A\n\nText.\n"})
        before = guide.source_fingerprint(root)
        (root / "01-a.md").write_bytes(b"# A\r\n\r\nText.\r\n")
        self.assertEqual(guide.source_fingerprint(root), before)
        (root / "01-a.md").write_text("# A\n\nOther text.\n", encoding="utf-8")
        self.assertNotEqual(guide.source_fingerprint(root), before)

    def test_only_numbered_chapters_count(self):
        root = self.make_guide({"01-a.md": "# A\n", "STYLE.md": "# Style\n", "README.md": "# Readme\n"})
        self.assertEqual([p.name for p in guide.chapter_paths(root)], ["01-a.md"])

    def test_check_detects_stale_pdf(self):
        root = self.make_guide({"01-a.md": "# A\n"})
        pdf = root / "guide.pdf"
        pdf.write_bytes(b"%PDF " + (guide.FINGERPRINT_PREFIX + guide.source_fingerprint(root)).encode())
        self.assertEqual(guide.check(pdf, root), 0)
        (root / "01-a.md").write_text("# A changed\n", encoding="utf-8")
        self.assertEqual(guide.check(pdf, root), 1)
        self.assertEqual(guide.check(root / "missing.pdf", root), 1)

    def test_combined_markdown_joins_in_order_and_rewrites_links(self):
        root = self.make_guide({
            "02-b.md": "# Second\n\nBack to [first](01-a.md).\n",
            "01-a.md": "# First\n\nOn to [second](02-b.md#second).\n",
        })
        combined = guide.combined_markdown(root)
        self.assertLess(combined.index("# First"), combined.index("# Second"))
        self.assertIn("[first](#first)", combined)
        self.assertIn("[second](#second)", combined)


class StyleRuleTests(GuideDirTestCase):
    def rules(self, body: str, name: str = "01-a.md") -> set:
        root = self.make_guide({name: "# Chapter\n\n" + body})
        return {f.rule for f in style.lint_guide(guide.chapter_paths(root))}

    def test_clean_prose_passes(self):
        text = (
            "The reserve drains into the market when war cuts supply. Build it while\n"
            "prices are low.\n\n## Reserve capacity\n\nEach level of the hub adds capacity.\n"
        )
        self.assertEqual(self.rules(text), set())

    def test_language_tells(self):
        cases = {
            "This pivotal system matters.": "ai-vocab",
            "The hub serves as a stockpile.": "ai-phrase",
            "Additionally, it drains.": "stock-opener",
            "It is not just a stockpile, it's a weapon.": "negative-parallel",
            "One — two — three.": "em-dash",
            "**a** and **b** and **c** here.": "bold-density",
            "- **Rate**: the policy rate.": "inline-header-list",
            "A “quoted” word.": "curly-quote",
            "Nice \U0001F680 rocket.": "emoji",
        }
        for text, rule in cases.items():
            with self.subTest(rule=rule):
                self.assertIn(rule, self.rules(text + "\n"))

    def test_internals_are_flagged(self):
        self.assertIn("script-key", self.rules("Open je_banking_cycle now.\n"))
        self.assertIn("mod-path", self.rules("See common/laws/x.txt for details.\n"))
        self.assertIn("raw-html", self.rules("Line one<br>line two.\n"))
        # Code spans and link targets are not prose.
        self.assertEqual(self.rules("Type `je_banking_cycle` in [the wiki](https://x.org/a_b).\n"), set())

    def test_structure_rules(self):
        self.assertIn("heading-skip", self.rules("Intro.\n\n#### Too deep\n\nText.\n"))
        self.assertIn("empty-heading", self.rules("Intro.\n\n## Parent\n\n### Child\n\nText.\n"))
        self.assertIn("title-case-heading", self.rules("Intro.\n\n## How The Policy Rate Works\n\nText.\n"))
        self.assertIn("thematic-break", self.rules("Intro.\n\n---\n\nMore.\n"))
        self.assertIn("chapter-heading", self.rules("Intro.\n\n# Second chapter\n\nText.\n"))
        self.assertIn("leading-comment", self.rules("<!-- note -->Text that vanishes.\n"))
        # A comment alone on its line, as screenshot placeholders are, is fine.
        self.assertEqual(self.rules("Text.\n\n<!-- screenshot: the panel -->\n\nMore text.\n"), set())

    def test_suppression_comment_at_end_of_line(self):
        self.assertEqual(self.rules("Press the key in the corner. <!-- style: allow ai-vocab -->\n"), set())
        self.assertIn("ai-vocab", self.rules("Press the key in the corner. <!-- style: allow em-dash -->\n"))

    def test_cross_file_rules(self):
        root = self.make_guide({
            "01-a.md": "# First\n\nSee [b](02-b.md#shared), [gone](02-b.md#nope), [x](#missing).\n\n## Shared\n\nText.\n",
            "02-b.md": "# Second\n\nText.\n\n## Shared\n\nText.\n",
        })
        findings = style.lint_guide(guide.chapter_paths(root))
        rules = [f.rule for f in findings]
        self.assertEqual(rules.count("duplicate-anchor"), 1)
        messages = " ".join(f.message for f in findings if f.rule == "broken-link")
        self.assertIn("#nope", messages)
        self.assertIn("#missing", messages)
        self.assertNotIn("#shared", messages)


if __name__ == "__main__":
    unittest.main()
