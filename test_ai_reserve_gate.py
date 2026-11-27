"""The AI's reserve gate on a new construction (#1877 trap 1) and its self-check.

- common/defines/extra_defines.txt sets NAI CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS to 0.02 (vanilla 0.1).
  test_construction_market_ai_purchase.py (Constants) pins the value and that the purchase floor keeps vanilla's tenth.
  Here: the line's comment, and that vanilla's other reserve gate of the same 0.1 is left alone, since the
  self-check's BROKEN names lowering it as the fallback.
- TE_SELF_CHECK ai_reserve_gate (common/on_actions/te_ai_reserve_gate_selfcheck_on_actions.txt, with its trigger and
  values files): does an AI government with reserves under vanilla's 0.1 queue a university.

The evidence and the table behind 0.02: docs/systems/mod_systems/ai.md § AI Government Construction.
"""

import re
import unittest
from pathlib import Path

from vanilla_parsed import vanilla_define

ROOT = Path(__file__).resolve().parent
DEFINES = ROOT / "common/defines/extra_defines.txt"
DEFINES_DIR = ROOT / "common/defines"
SELFCHECK = ROOT / "common/on_actions/te_ai_reserve_gate_selfcheck_on_actions.txt"
SELFCHECK_VALUES = ROOT / "common/script_values/te_ai_reserve_gate_selfcheck_values.txt"
SELFCHECK_TRIGGERS = ROOT / "common/scripted_triggers/te_ai_reserve_gate_selfcheck_triggers.txt"
ADMIN_TRIGGERS = ROOT / "common/scripted_triggers/te_construction_market_triggers.txt"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"
SYSTEM_DOC = ROOT / "docs/systems/mod_systems/ai.md"

GATE = "CONSTRUCTION_RESERVES_NEW_CONSTRUCTIONS"
VANILLA_GATE = 0.1
# Vanilla 1.15.1 (common/defines/00_ai.txt): "If we don't have at least this fraction of gold reserves, don't increase
# spending on a 'should-have'". Left at vanilla's; the self-check's BROKEN fallback is to lower it too.
SHOULD_HAVE_GATE = "MONEY_SPENDING_MIN_GOLD_RESERVE_FRACTION_TO_ADD_SHOULD_HAVE"
VANILLA_SHOULD_HAVE_GATE = 0.1


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def _norm(text):
    return " ".join(text.split())


def _mod_gate():
    m = re.search(rf"(?m)^\t{GATE}\s*=\s*([0-9.]+)", _strip_comments(DEFINES.read_text(encoding="utf-8-sig")))
    return float(m.group(1))


class TheDefine(unittest.TestCase):
    def test_the_comment_gives_vanillas_value_the_reason_and_the_evidence(self):
        text = DEFINES.read_text(encoding="utf-8-sig")
        line = re.search(rf"(?m)^\t{GATE}\s*=", text)
        above = text[:line.start()].splitlines()
        block = []
        while above and above[-1].strip().startswith("#"):
            block.insert(0, above.pop().strip())
        comment = "\n".join(block)
        for part in ("vanilla 0.1", "#1877", "THE RATE and\n# THE PASS", "ai.md § AI Government Construction",
                     SHOULD_HAVE_GATE, "TE_SELF_CHECK", "ai_reserve_gate", "holds no reserves"):
            with self.subTest(part=part):
                self.assertIn(part, comment)

    def test_vanillas_should_have_gate_is_left_alone(self):
        # Lowering it is the self-check's BROKEN fallback: a mod line that sets it changes what OK and BROKEN mean.
        for path in sorted(DEFINES_DIR.glob("*.txt")):
            with self.subTest(file=path.name):
                text = _strip_comments(path.read_text(encoding="utf-8-sig"))
                self.assertNotRegex(text, rf"\b{SHOULD_HAVE_GATE}\s*=")

    def test_matches_vanilla(self):
        # vanilla_parsed/defines.json (#1879), so it runs in CI too.
        for name, value in ((GATE, VANILLA_GATE), (SHOULD_HAVE_GATE, VANILLA_SHOULD_HAVE_GATE)):
            with self.subTest(define=name):
                self.assertEqual(float(vanilla_define("NAI", name)), value)


class TheSelfCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SELFCHECK.read_text(encoding="utf-8-sig")
        cls.body = _strip_comments(cls.raw)
        cls.watch = _block(cls.body, "te_ai_reserve_gate_selfcheck_watch")
        cls.verdict = _block(cls.body, "te_ai_reserve_gate_selfcheck")
        cls.trigger = _block(cls.verdict, "trigger")
        cls.effect = _block(cls.verdict, "effect")
        cls.values = _strip_comments(SELFCHECK_VALUES.read_text(encoding="utf-8-sig"))
        cls.triggers = _strip_comments(SELFCHECK_TRIGGERS.read_text(encoding="utf-8-sig"))

    def branches(self):
        """(kind, limit, verdict word) of the if / else_if / else under random_country, in order."""
        chain = _block(self.effect, "random_country")
        out = []
        for m in re.finditer(r"(?m)^\t{3}(if|else_if|else) = \{", chain):
            body = _block(chain[m.start():], m.group(1))
            line = re.search(r'debug_log = "TE_SELF_CHECK (\w+) ai_reserve_gate[^"]*"', body)
            out.append((m.group(1), _norm(_block(body, "limit") or ""), line.group(1)))
        return out

    def test_files_start_with_one_bom_and_indent_with_tabs(self):
        for path in (SELFCHECK, SELFCHECK_VALUES, SELFCHECK_TRIGGERS):
            with self.subTest(file=path.name):
                raw = path.read_bytes()
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
                self.assertNotRegex(raw.decode("utf-8-sig"), r"(?m)^ +\S")

    def test_sub_actions_of_the_two_monthly_pulses(self):
        self.assertRegex(self.body, r"on_monthly_pulse_country\s*=\s*\{\s*on_actions\s*=\s*\{\s*"
                                    r"te_ai_reserve_gate_selfcheck_watch\s*\}\s*\}")
        self.assertRegex(self.body, r"on_monthly_pulse\s*=\s*\{\s*on_actions\s*=\s*\{\s*"
                                    r"te_ai_reserve_gate_selfcheck\s*\}\s*\}")

    def test_once_a_game(self):
        # the latch: in both triggers, and the first thing the verdict sets
        self.assertIn("NOT = { has_global_variable = te_rgc_checked }", _block(self.watch, "trigger"))
        self.assertIn("NOT = { has_global_variable = te_rgc_checked }", self.trigger)
        self.assertTrue(self.effect.strip().startswith("set_global_variable = te_rgc_checked"))

    def test_the_band_sits_between_the_mods_gate_and_vanillas(self):
        low, cap = 0.03, 0.08
        self.assertGreater(low, _mod_gate(), "room for a building's cost above the mod's gate")
        self.assertLess(cap, VANILLA_GATE, "room for a month's saving below vanilla's gate")
        effect = _norm(_block(self.watch, "effect"))
        self.assertIn("if = { limit = { scaled_gold_reserves >= 0.03 scaled_gold_reserves < 0.08 "
                      "te_rgc_may_queue_a_university = yes }", effect)
        self.assertTrue(effect.endswith("set_variable = te_rgc_watch }"))

    def test_a_low_band_watch_counts_only_if_still_under_the_cap_at_its_read(self):
        read = _norm(_block(self.watch, "effect"))
        # Not counted when the AI construction pass queued for the country in the last 45 days, or still follows a
        # level it queued: its level, not the engine's.
        self.assertIn("if = { limit = { has_variable = te_rgc_watch } remove_variable = te_rgc_watch if = { limit = { "
                      "scaled_gold_reserves < 0.08 NOT = { has_variable = te_ai_build_pass_recent } NOT = { "
                      "has_variable = te_ai_build_pass_pending_kind } } change_global_variable = { name = "
                      "te_rgc_watched add = 1 } if = { "
                      "limit = { construction_queue_num_queued_government_levels > 0 } change_global_variable = { name "
                      "= te_rgc_any add = 1 } if = { limit = { te_rgc_university_queued = yes } "
                      "change_global_variable = { name = te_rgc_uni add = 1 } } } } }", read)
        # the counters exist before the first one is changed
        for name in ("te_rgc_watched", "te_rgc_any", "te_rgc_uni"):
            with self.subTest(counter=name):
                self.assertIn("set_global_variable = { name = %s value = 0 }" % name, read)

    def test_the_control_is_counted_once_at_the_verdict_before_its_line(self):
        effect = _norm(self.effect)
        control = ("set_global_variable = { name = te_rgc_ctrl_queues value = 0 } set_global_variable = { name = "
                   "te_rgc_ctrl_uni value = 0 } every_country = { limit = { is_ai = yes "
                   "construction_queue_num_queued_government_levels > 0 NOT = { has_variable = "
                   "te_ai_build_pass_pending_kind } } change_global_variable = { name = "
                   "te_rgc_ctrl_queues add = 1 } if = { limit = { te_rgc_university_queued = yes } "
                   "change_global_variable = { name = te_rgc_ctrl_uni add = 1 } } }")
        self.assertIn(control, effect)
        self.assertLess(effect.index(control), effect.index("TE_SELF_CHECK START"))
        self.assertNotIn("te_rgc_ctrl", _block(self.watch, "effect"), "the watch walks no control")

    def test_a_watch_drops_what_no_gate_would_let_queue_a_university(self):
        may = _norm(_block(self.triggers, "te_rgc_may_queue_a_university"))
        for part in ("is_ai = yes", "NOT = { is_country_type = decentralized }", "is_at_war = no", "bureaucracy >= 0",
                     "has_technology_researched = academia",
                     "NOT = { construction_queue_num_queued_government_levels > 0 }", "te_rgc_innovation_share < 0.9",
                     "OR = { te_rgc_surplus >= 15000 te_rgc_surplus_share >= 0.17 }"):
            with self.subTest(part=part):
                self.assertIn(part, may)
        self.assertEqual(_norm(_block(self.values, "te_rgc_innovation_cap")),
                         "value = modifier:country_weekly_innovation_max_add")

    def test_the_university_read_is_the_administrations(self):
        uni = _norm(_block(self.triggers, "te_rgc_university_queued"))
        admin = _norm(_block(_strip_comments(ADMIN_TRIGGERS.read_text(encoding="utf-8-sig")),
                             "te_construction_market_ai_building_administration"))
        self.assertEqual(uni, admin.replace("bureaucracy < 0 ", "").replace("building_government_administration",
                                                                             "building_university"))

    def test_the_verdicts(self):
        self.assertEqual(_norm(self.trigger), _norm(
            "NOT = { has_global_variable = te_rgc_checked } has_global_variable = te_rgc_watched OR = { "
            "global_var:te_rgc_uni >= 3 global_var:te_rgc_watched >= 120 }"))
        self.assertEqual(self.branches(), [
            ("if", "te_rgc_uni_g >= 3", "OK"),
            ("else_if", "te_rgc_uni_g < 1 te_rgc_ctrl_uni_g >= 3", "BROKEN"),
            ("else", "", "NO_VERDICT"),
        ])

    def test_broken_names_the_fallback_and_every_line_fits_log_triage(self):
        lines = {verdict: line for line, verdict in re.findall(r'debug_log = "(TE_SELF_CHECK (\w+) ai_reserve_gate[^"]*)"',
                                                               self.effect)}
        self.assertEqual(sorted(lines), ["BROKEN", "NO_VERDICT", "OK", "START"])
        self.assertIn(SHOULD_HAVE_GATE, lines["BROKEN"])
        self.assertIn(GATE, lines["OK"])
        for verdict, line in lines.items():
            if verdict == "START":
                self.assertNotIn("[", line)
                continue
            with self.subTest(verdict=verdict):
                # log_triage.py shows a line's first 400 characters
                shown = re.sub(r"\[[^\]]*\]", "0000", line)[:400]
                self.assertIn("date=0000 (", shown)
                if verdict == "BROKEN":
                    self.assertIn(SHOULD_HAVE_GATE, shown)

    def test_a_plain_marker_comes_before_the_templated_verdict(self):
        start = self.effect.index("TE_SELF_CHECK START ai_reserve_gate")
        self.assertLess(start, self.effect.index("random_country"))
        self.assertGreater(start, self.effect.index("every_country"))

    def test_every_value_and_trigger_it_reads_is_defined(self):
        used = set(re.findall(r"\bte_rgc_\w+", self.body + self.triggers + self.values))
        variables = {"te_rgc_checked", "te_rgc_watch", "te_rgc_watched", "te_rgc_any", "te_rgc_uni",
                     "te_rgc_ctrl_queues", "te_rgc_ctrl_uni"}
        defined = set(re.findall(r"(?m)^(te_rgc_\w+)\s*=", self.values + self.triggers))
        self.assertEqual(used - variables, defined)
        for name in re.findall(r"ScriptValue\('(\w+)'\)", self.effect):
            with self.subTest(value=name):
                self.assertIn(name, defined)

    def test_the_play_test_list_and_the_doc_carry_it(self):
        playtest = PLAYTEST.read_text(encoding="utf-8")
        self.assertIn("## The AI's reserve gate", playtest)
        self.assertIn("TE_SELF_CHECK … ai_reserve_gate", playtest)
        self.assertIn(SHOULD_HAVE_GATE, playtest)
        doc = SYSTEM_DOC.read_text(encoding="utf-8")
        self.assertIn(f"`{GATE}` 0.02", doc)
        self.assertIn("ai_reserve_gate", doc)


if __name__ == "__main__":
    unittest.main()
