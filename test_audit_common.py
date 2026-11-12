"""Tests for audit_common: the shared `# REVIEWED` parser agrees with every
audit's own parser it replaces, and the result, report and command line.

Run: python3 -m pytest test_audit_common.py -q
"""
import io
import os
import re
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout

import audit_common
from audit_common import AuditResult, Flag, StaleTag, cli_main, parse_reviewed

ROOT = os.path.dirname(os.path.abspath(__file__))


# The audits' own parsers as they stood on main before #1536 (frozen here, so
# the comparison survives an audit's move onto audit_common). Each entry:
# (pattern, how the tag list is read, the audits that used it).
#   "plain":  no tag; the result is the match.
#   "split":  tags split on spaces and commas (`re.split(r"[\s,]+")`).
#   "comma":  tags split on commas, each stripped.
#   "equal":  one tag, compared whole.
#   "fixed":  the tag is written into the pattern.
# The shared parser takes the union of these forms with the tag as a parameter:
# for any tag, a comment some form took for that tag, and nothing else.
_DATE = r"(?P<date>\d{4}-\d{2}-\d{2})"
LEGACY = {
    "plain_lazy": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*:\s*(?P<rationale>.+?)\s*$", "plain",
        # Migrated in #1536's first stage: the agreement test below covers them.
        ("attitude_key_audit", "kill_character_audit", "any_limit_audit", "event_image_audit",
         "orphaned_event_audit", "sol_fraction_audit", "duplicate_key_audit",
         "script_loc_reference_audit",
         # Not yet migrated.
         "concept_reference_audit", "delayed_event_trigger_audit",
         "effect_trigger_validity_audit", "event_magnitude_audit", "iterator_limit_audit",
         "loc_coverage_audit", "loc_render_audit", "localization_accessor_audit",
         "mod_structure_audit", "modifier_multiplier_var_audit", "modifier_visibility_audit",
         "pm_employment_audit", "prev_scope_audit"),
    ),
    "plain_greedy": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*:\s*(?P<rationale>.+)$", "plain",
        ("prestige_good_roster_audit", "principle_tier_audit", "treaty_leverage_side_audit"),
    ),
    "tagged_split": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$",
        "split",
        ("button_reason_audit", "empty_effect_audit", "event_context_audit", "faith_scene_audit",
         "hidden_modifier_audit", "long_tooltip_audit", "loc_root_context_audit",
         "loc_script_value_audit", "script_argument_audit", "texture_reference_audit"),
    ),
    "tagged_comma": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$",
        "comma",
        ("silent_variable_audit", "variable_guard_audit"),
    ),
    "tagged_word": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*\((?P<checks>\w+)\)\s*:\s*(?P<rationale>.+)$", "equal",
        ("amendment_reachability_audit", "ideology_lawgroup_audit"),
    ),
    "tagged_lower": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*\((?P<checks>[a-z_]+)\)\s*:\s*(?P<rationale>.+)$",
        "equal",
        ("treaty_leverage_side_audit",),
    ),
    # Written for its one tag (`roster_membership`); read here with the tag as
    # a parameter, like the others, so `{tag}` stands for it.
    "tagged_spaced": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*\(\s*{tag}\s*\)\s*:\s*(?P<rationale>.+)$",
        "fixed",
        ("roster_membership_audit",),
    ),
}

# The rules whose audits have moved onto audit_common.
MIGRATED_RULES = ("plain_lazy",)
MIGRATED = LEGACY["plain_lazy"][2][:8]


def legacy_parse(rule: str, comment: str, tag: str = ""):
    pattern, kind, _ = LEGACY[rule]
    if not comment:
        return None
    if kind == "fixed":
        if not tag:
            return None
        pattern = pattern.replace("{tag}", re.escape(tag))
    m = re.search(pattern, comment)
    if not m:
        return None
    if kind == "split":
        if tag not in re.split(r"[\s,]+", m.group("checks").strip()):
            return None
    elif kind == "comma":
        if tag not in {c.strip() for c in m.group("checks").split(",")}:
            return None
    elif kind == "equal" and m.group("checks") != tag:
        return None
    return {"date": m.group("date"), "tag": tag, "rationale": m.group("rationale").strip()}


def repo_lines() -> list[str]:
    """Every line in the repository that says REVIEWED: the comments, and the
    code, tests and docs that read or describe them."""
    out = subprocess.run(["git", "grep", "-h", "-I", "REVIEWED"], cwd=ROOT,
                         capture_output=True, text=True, check=False).stdout
    return out.splitlines()


EDGES = [
    "",
    "# REVIEWED",
    "# REVIEWED 2026-01-01",
    "# REVIEWED 2026-01-01:",
    "# REVIEWED 2026-01-01:   ",
    "# REVIEWED 2026-01-01: why",
    "#REVIEWED 2026-01-01:why",
    "# REVIEWED 2026-01-01 : why   ",
    "# REVIEWED 2026-1-01: why",
    "# REVIEWED: why",
    "# reviewed 2026-01-01: why",
    "\tx = 1 # REVIEWED 2026-01-01: why # and more",
    "x = 1 # REVIEWED 2026-01-01 (any_tag): tagged # REVIEWED 2026-02-02: plain after",
    "x = 1 # REVIEWED 2026-01-01: plain # REVIEWED 2026-02-02 (faith_scene): tagged after",
    "# REVIEWED 2026-01-01 (faith_scene): why",
    "# REVIEWED 2026-01-01(faith_scene):why",
    "# REVIEWED 2026-01-01 ( faith_scene ): why",
    "# REVIEWED 2026-01-01 (faith_scene, long_tooltip): why",
    "# REVIEWED 2026-01-01 (long_tooltip faith_scene): why",
    "# REVIEWED 2026-01-01 (faith_scene,): why",
    "# REVIEWED 2026-01-01 (Faith_Scene): why",
    "# REVIEWED 2026-01-01 (): why",
    "# REVIEWED 2026-01-01 (faith-scene): why",
    "# REVIEWED 2026-01-01 (roster_membership): why",
    "# REVIEWED 2026-01-01 ( roster_membership ): why",
    "# REVIEWED 2026-01-01 (\troster_membership): why",
    "# REVIEWED 2026-01-01 (\tfaith_scene): why",
    "# REVIEWED 2026-01-01 (involvement): why",
    "# REVIEWED 2026-01-01 (involvement):",
    "# REVIEWED 2026-01-01 (variable_guard other): why",
    "# REVIEWED 2026-01-01 (other, variable_guard): why",
    "key: \"text\" # REVIEWED 2026-01-01 (long_tooltip): why\n",
]

def tags_in(lines) -> set[str]:
    found = set()
    for line in lines:
        for m in re.finditer(r"REVIEWED\s+\d{4}-\d{2}-\d{2}\s*\(([^)]*)\)", line):
            # Real tags only: docs also write placeholders such as `(<check>)`.
            found.update(t for t in re.split(r"[\s,]+", m.group(1).strip()) if re.fullmatch(r"\w+", t))
    return found


class AgreementTests(unittest.TestCase):
    """The shared parser reads every REVIEWED line in the repository exactly
    as each audit's own parser read it."""

    @classmethod
    def setUpClass(cls):
        cls.repo = repo_lines()
        cls.lines = cls.repo + EDGES
        cls.tags = sorted(tags_in(cls.lines) | {"roster_membership", "involvement"})
        assert len(cls.lines) > 500, "git grep found no corpus"

    def _check(self, rule: str, tags: list[str], exact: bool, lines=None):
        """Where the rule's parser took a comment, the shared one reads it the
        same. Where it did not, the shared one takes it only if another form
        took it for that tag (the union), and with `exact`, not at all."""
        diffs = []
        for line in self.lines if lines is None else lines:
            for tag in tags:
                old = legacy_parse(rule, line, tag)
                new = parse_reviewed(line, (tag,))
                if old == new:
                    continue
                if (not exact and old is None
                        and any(legacy_parse(r, line, tag) == new for r in LEGACY)):
                    continue
                diffs.append((tag, line, old, new))
        self.assertEqual(diffs, [], f"{rule}: {len(diffs)} disagreements, first {diffs[:3]}")

    def test_migrated_audits_read_every_comment_exactly_as_before(self):
        for rule in MIGRATED_RULES:
            self.assertEqual(LEGACY[rule][1], "plain")
            self._check(rule, [""], exact=True)

    def test_plain_audits_not_yet_migrated_agree_exactly_too(self):
        self._check("plain_greedy", [""], exact=True)

    def test_tagged_forms_agree_or_widen_only_to_the_union(self):
        for rule in ("tagged_split", "tagged_comma", "tagged_word", "tagged_lower", "tagged_spaced"):
            with self.subTest(rule=rule):
                self._check(rule, self.tags, exact=False)

    def test_the_most_used_tagged_form_agrees_exactly_on_the_repo(self):
        """Ten audits' form. The shared parser widens it only by a tab inside
        the parentheses (`roster_membership_audit`'s form), which no comment in
        the repository has."""
        self._check("tagged_split", self.tags, exact=True, lines=self.repo)

    def test_nothing_outside_the_union(self):
        """Every comment the shared parser takes, for any tag, some audit's
        own parser took."""
        extra = []
        for line in self.lines:
            for tag in [""] + self.tags:
                new = parse_reviewed(line, (tag,) if tag else ())
                if new is not None and not any(legacy_parse(r, line, tag) == new for r in LEGACY):
                    extra.append((tag, line, new))
        self.assertEqual(extra, [])

    def test_migrated_audits_lost_their_own_parser(self):
        for name in MIGRATED:
            with open(os.path.join(ROOT, f"{name}.py"), encoding="utf-8") as fh:
                source = fh.read()
            self.assertNotIn("re.compile(\n    r\"#\\s*REVIEWED", source, name)
            self.assertNotIn("_REVIEWED_RE", source, name)
            self.assertIn("audit_common", source, name)

    def test_the_corpus_has_both_forms(self):
        self.assertTrue(any(parse_reviewed(line) for line in self.lines))
        self.assertTrue(any(parse_reviewed(line, ("faith_scene",)) for line in self.lines))


class ParseReviewedTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(parse_reviewed("x = 1  # REVIEWED 2026-05-01: kept on purpose  "),
                         {"date": "2026-05-01", "tag": "", "rationale": "kept on purpose"})

    def test_plain_audit_ignores_a_tagged_comment(self):
        self.assertIsNone(parse_reviewed("# REVIEWED 2026-05-01 (faith_scene): why"))

    def test_tagged_audit_ignores_a_plain_comment_and_other_tags(self):
        self.assertIsNone(parse_reviewed("# REVIEWED 2026-05-01: why", ("faith_scene",)))
        self.assertIsNone(parse_reviewed("# REVIEWED 2026-05-01 (long_tooltip): why", ("faith_scene",)))

    def test_a_tag_list(self):
        got = parse_reviewed("# REVIEWED 2026-05-01 (long_tooltip, faith_scene): why",
                             ("faith_scene", "long_tooltip"))
        self.assertEqual(got["tag"], "long_tooltip")
        self.assertEqual(parse_reviewed("# REVIEWED 2026-05-01 (a b): why", ("b",))["tag"], "b")

    def test_both_forms(self):
        both = ("", "involvement")
        self.assertEqual(parse_reviewed("# REVIEWED 2026-05-01: why", both)["tag"], "")
        self.assertEqual(parse_reviewed("# REVIEWED 2026-05-01 (involvement): why", both)["tag"],
                         "involvement")
        self.assertIsNone(parse_reviewed("# REVIEWED 2026-05-01 (other): why", both))

    def test_nothing(self):
        for comment in (None, "", "# just a comment", "# REVIEWED: no date",
                        "# REVIEWED 2026-05-01:", "# REVIEWED 2026-05-01 no colon"):
            self.assertIsNone(parse_reviewed(comment), comment)


class ResultTests(unittest.TestCase):
    def test_result_splits_flags(self):
        ex = {"date": "2026-05-01", "tag": "", "rationale": "why"}
        result = AuditResult(flags=[Flag("a.txt", 1, "bad"), Flag("b.txt", 2, "fine", ex)])
        self.assertEqual([f.file for f in result.unreviewed], ["a.txt"])
        self.assertEqual([f.file for f in result.exemptions], ["b.txt"])
        self.assertTrue(result.failed)

    def test_a_stale_tag_fails(self):
        result = AuditResult(stale=[StaleTag("a.txt", 3, "x")])
        self.assertEqual(result.failing, result.stale)
        self.assertTrue(result.failed)
        self.assertFalse(AuditResult().failed)

    def test_a_subclass_keeps_its_fields_in_place(self):
        from dataclasses import dataclass

        @dataclass
        class Mine(AuditResult):
            files: int = 0

        self.assertEqual(Mine([], 4).files, 4)

    def test_summary(self):
        result = AuditResult(flags=[Flag("a.txt", 1, "bad")], stale=[StaleTag("b.txt", 2)])
        self.assertEqual(audit_common.summary(result, files=3),
                         {"total_flags": 1, "unreviewed": 1, "exempted": 0, "stale_tags": 1,
                          "files": 3})


class ReportTests(unittest.TestCase):
    def test_report_takes_the_registry_hint(self):
        ex = {"date": "2026-05-01", "tag": "", "rationale": "deliberate"}
        result = AuditResult(flags=[Flag("events/a.txt", 7, "`limit` inside `any_x`"),
                                    Flag("events/b.txt", 9, "`limit` inside `any_y`", ex)])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "docs", "engine", "x_report.md")
            text = audit_common.write_report(result, path, "Example audit report",
                                             audit="any_limit_audit")
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), text)
        self.assertIn("# REVIEWED YYYY-MM-DD: why", text)
        self.assertIn("- `events/a.txt:7`: `limit` inside `any_x`", text)
        self.assertIn("- `events/b.txt`: `limit` inside `any_y` — **2026-05-01**: deliberate", text)
        self.assertNotIn("b.txt:9", text)
        self.assertNotIn("## Stale tags", text)

    def test_report_lists_stale_tags(self):
        text = audit_common.render_report(AuditResult(stale=[StaleTag("a.yml", 4, "long_tooltip")]),
                                          "T", "Suppress with a tag.")
        self.assertIn("## Stale tags", text)
        self.assertIn("- `a.yml:4` (long_tooltip)", text)
        self.assertIn("Suppress with a tag.", text)


class CliTests(unittest.TestCase):
    def run_cli(self, argv, result, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli_main(lambda args: result, lambda r, args: f"report strict={args.strict}",
                            argv=argv, **kw)
        return code, buf.getvalue()

    def test_strict_fails_only_on_a_failing_result(self):
        bad = AuditResult(flags=[Flag("a", 1, "m")])
        self.assertEqual(self.run_cli([], bad), (0, "report strict=False\n"))
        self.assertEqual(self.run_cli(["--strict"], bad), (1, "report strict=True\n"))
        self.assertEqual(self.run_cli(["--strict"], AuditResult())[0], 0)

    def test_aliases_and_always_strict(self):
        bad = AuditResult(flags=[Flag("a", 1, "m")])
        self.assertEqual(self.run_cli(["--check"], bad, aliases=("--check",))[0], 1)
        self.assertEqual(self.run_cli(["--strict"], bad, aliases=("--check",))[0], 1)
        self.assertEqual(self.run_cli([], bad, always_strict=True)[0], 1)
        with self.assertRaises(SystemExit):
            self.run_cli(["--check"], bad)

    def test_render_none_prints_nothing(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli_main(lambda args: AuditResult(), lambda r, a: None, argv=[])
        self.assertEqual((code, buf.getvalue()), (0, ""))


if __name__ == "__main__":
    unittest.main()
