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
# the comparison survives the audits' move onto audit_common, which every
# audit has now made). Each entry: (pattern, how the tag list is read, the
# audits that used it).
#   "plain":  no tag; the result is the match.
#   "split":  tags split on spaces and commas (`re.split(r"[\s,]+")`).
#   "comma":  tags split on commas, each stripped.
#   "equal":  one tag, compared whole.
#   "fixed":  the tag is written into the pattern.
#   "presence": the tag is written into the pattern, which captures no
#             rationale: the audit only asked whether the comment is there.
# The shared parser's plain form is exactly the old plain forms. Its tagged form
# agrees with every old form on every line in the repository, but not on every
# shape: `TAGGED_DIVERGENCES` pins the shapes where it differs.
_DATE = r"(?P<date>\d{4}-\d{2}-\d{2})"
LEGACY = {
    "plain_lazy": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*:\s*(?P<rationale>.+?)\s*$", "plain",
        ("attitude_key_audit", "kill_character_audit", "any_limit_audit", "event_image_audit",
         "orphaned_event_audit", "sol_fraction_audit", "duplicate_key_audit",
         "script_loc_reference_audit", "concept_reference_audit", "delayed_event_trigger_audit",
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
    # The same with a lazy rationale (`modifier_field_loc`).
    "tagged_spaced_lazy": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*\(\s*{tag}\s*\)\s*:\s*(?P<rationale>.+?)\s*$",
        "fixed",
        ("modifier_field_audit",),
    ),
    # `treaty_scope`: `\(treaty_scope\)\s*:\s*\S`, a yes/no. The rationale group
    # here is what follows the colon, which is what the shared parser reads.
    "tagged_presence": (
        r"#\s*REVIEWED\s+" + _DATE + r"\s*\({tag}\)\s*:\s*(?P<rationale>\S.*?)\s*$",
        "presence",
        ("treaty_evaluation_scope_audit",),
    ),
}

# The plain rules: the shared parser reads every comment exactly as they did.
MIGRATED_RULES = ("plain_lazy", "plain_greedy")


def _registry_audits() -> tuple[str, ...]:
    import audit_registry
    return tuple(a.name for a in audit_registry.AUDITS)


# Every audit is on audit_common (#1536).
MIGRATED = _registry_audits()


def legacy_parse(rule: str, comment: str, tag: str = ""):
    pattern, kind, _ = LEGACY[rule]
    if not comment:
        return None
    if kind in ("fixed", "presence"):
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

# Shapes where the shared tagged form differs from an audit's own, pinned so a
# change to either is deliberate. None occurs in the repository
# (`test_the_most_used_tagged_form_agrees_exactly_on_the_repo` and
# `test_tagged_forms_agree_on_the_corpus_or_widen_to_another_form` prove it).
# Settled when the tagged audits moved onto audit_common (#1536): each reading
# below is the wider one. (rule, comment, old parser takes it, shared one takes
# it), for the tag `t_ag`.
_A = "# REVIEWED 2026-01-01"
_B = "# REVIEWED 2026-01-02 (t_ag): y"
TAGGED_DIVERGENCES = [
    # Two tagged comments on a line, the first naming only another audit's tag:
    # the first comment that names `t_ag` decides in the shared parser, as the
    # fixed form's did. The split, comma, one-word and lowercase forms read
    # only the first tagged comment their pattern matched, so it hid the second.
    ("tagged_split", f"{_A} (other): x {_B}", False, True),
    ("tagged_comma", f"{_A} (other): x {_B}", False, True),
    ("tagged_word", f"{_A} (other): x {_B}", False, True),
    ("tagged_lower", f"{_A} (other): x {_B}", False, True),
    ("tagged_split", f"{_A} (a, b): x {_B}", False, True),
    ("tagged_comma", f"{_A} (a, b): x {_B}", False, True),
    # A list naming the tag, which only the split and comma forms took.
    ("tagged_word", f"{_A} (t_ag,): x", False, True),
    ("tagged_word", f"{_A} (t_ag, other): x", False, True),
    ("tagged_lower", f"{_A} (t_ag,): x", False, True),
    ("tagged_lower", f"{_A} (t_ag, other): x", False, True),
    ("tagged_spaced", f"{_A} (t_ag,): x", False, True),
    ("tagged_spaced", f"{_A} (t_ag, other): x", False, True),
    # treaty_scope's form took the one name, written tight, and anything after
    # the colon: the shared one takes spaces, a tab or a list in the
    # parentheses, and a colon with only a carriage return after it (as the
    # plain form always has).
    ("tagged_presence", f"{_A} ( t_ag ): x", False, True),
    ("tagged_presence", f"{_A} (\tt_ag): x", False, True),
    ("tagged_presence", f"{_A} (t_ag, other): x", False, True),
    ("tagged_presence", f"{_A} (t_ag):\r", False, True),
    # modifier_field_loc's form took one name: the shared one takes a list.
    ("tagged_spaced_lazy", f"{_A} (t_ag, other): x", False, True),
    # Tabs inside the parentheses, which only the fixed form took.
    ("tagged_split", f"{_A} (\tt_ag\t): x", False, True),
    ("tagged_comma", f"{_A} (\tt_ag\t): x", False, True),
    ("tagged_word", f"{_A} (\tt_ag\t): x", False, True),
    ("tagged_lower", f"{_A} (\tt_ag\t): x", False, True),
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
        took it for that tag, and with `exact`, not at all. Over the corpus
        (the repository and `EDGES`); `TAGGED_DIVERGENCES` holds the shapes
        outside it where the tagged forms differ."""
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

    def test_tagged_forms_agree_on_the_corpus_or_widen_to_another_form(self):
        for rule in ("tagged_split", "tagged_comma", "tagged_word", "tagged_lower", "tagged_spaced",
                     "tagged_spaced_lazy", "tagged_presence"):
            with self.subTest(rule=rule):
                self._check(rule, self.tags, exact=False)

    def test_the_most_used_tagged_form_agrees_exactly_on_the_repo(self):
        """Ten audits' form. The shared parser widens it only by a tab inside
        the parentheses (`roster_membership_audit`'s form), which no comment in
        the repository has."""
        self._check("tagged_split", self.tags, exact=True, lines=self.repo)

    def test_nothing_on_the_corpus_that_no_form_took(self):
        """Every corpus comment the shared parser takes, for any tag, some
        audit's own parser took."""
        extra = []
        for line in self.lines:
            for tag in [""] + self.tags:
                new = parse_reviewed(line, (tag,) if tag else ())
                if new is not None and not any(legacy_parse(r, line, tag) == new for r in LEGACY):
                    extra.append((tag, line, new))
        self.assertEqual(extra, [])

    def test_migrated_audits_lost_their_own_parser(self):
        self.assertEqual(len(MIGRATED), 52)
        for name in MIGRATED:
            with open(os.path.join(ROOT, f"{name}.py"), encoding="utf-8") as fh:
                source = fh.read()
            with self.subTest(audit=name):
                self.assertNotIn("#\\s*REVIEWED", source)
                self.assertNotIn("_REVIEWED_RE", source)
                self.assertIn("audit_common", source)

    def test_every_legacy_rule_names_audits_in_the_registry(self):
        """One plain rule and one tagged rule at most per audit (treaty_leverage_side
        takes both forms), each an audit the registry lists."""
        for plain in (True, False):
            named = [a for _, kind, audits in LEGACY.values() if (kind == "plain") == plain for a in audits]
            self.assertEqual(len(named), len(set(named)), "an audit in two rules of one form")
            self.assertLessEqual(set(named), set(MIGRATED))

    def test_tagged_divergences_are_as_pinned(self):
        for rule, comment, old, new in TAGGED_DIVERGENCES:
            with self.subTest(rule=rule, comment=comment):
                self.assertEqual(legacy_parse(rule, comment, "t_ag") is not None, old)
                self.assertEqual(parse_reviewed(comment, ("t_ag",)) is not None, new)
        # The plain form has none: a plain audit still skips a tagged comment
        # and reads a later plain one.
        self.assertEqual(parse_reviewed(f"{_A} (t_ag): x # REVIEWED 2026-01-02: y")["rationale"], "y")

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
