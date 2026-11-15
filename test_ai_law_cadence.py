"""AI law cadence (2026-11-15): AI countries start law changes more often, with more revolution aversion to match.

- common/ai_strategies/edited_default_strategy.txt: ai_strategy_default's change_law_chance is vanilla's 1 plus 39,
  times 10 in the mod's crisis case. By vanilla's comment (unread in game) the default's field adds to every
  political strategy's own.
- common/ai_strategies/edited_political_strategies.txt: seven political agendas' revolution_aversion, each vanilla's
  whole block plus one `add` line; nothing else in those strategies (the pass-chance floor stays vanilla's).
- TE_SELF_CHECK ai_law_cadence (common/on_actions/te_ai_law_cadence_selfcheck_on_actions.txt) and its play-test row.

The arithmetic behind the numbers: docs/systems/mod_systems/ai.md § Law-Change Cadence.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT = ROOT / "common/ai_strategies/edited_default_strategy.txt"
POLITICAL = ROOT / "common/ai_strategies/edited_political_strategies.txt"
SELFCHECK = ROOT / "common/on_actions/te_ai_law_cadence_selfcheck_on_actions.txt"
SELFCHECK_VALUES = ROOT / "common/script_values/te_ai_law_cadence_selfcheck_values.txt"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"
SYSTEM_DOC = ROOT / "docs/systems/mod_systems/ai.md"

# Vanilla 1.15.1 (game/common/ai_strategies/00_default_strategy.txt): `change_law_chance = { value = 1 }`.
VANILLA_DEFAULT_CHANCE = 1
CHANCE_ADD = 39
CRISIS_MULTIPLIER = 10

# Vanilla 1.15.1's revolution_aversion block per agenda (game/common/ai_strategies/03_political_strategies.txt),
# whitespace-normalized, and the mod's rise. test_restated_blocks_match_the_game_files reads the game where installed.
VANILLA_AVERSION = {
    "ai_strategy_conservative_agenda": (
        "value = 75 "
        "if = { limit = { has_journal_entry = je_tp_pool_suppress_revolts } add = 50 } "
        "if = { limit = { divided_monarchists_ai_monarchist = yes } add = 50 } "
        "if = { limit = { divided_monarchists_ai_republican = yes } subtract = 50 } "
        "min = 10"
    ),
    "ai_strategy_reactionary_agenda": (
        "value = 50 if = { limit = { has_journal_entry = je_tp_pool_suppress_revolts } add = 50 }"
    ),
    "ai_strategy_progressive_agenda": "value = 50",
    "ai_strategy_egalitarian_agenda": "value = 25",
    "ai_strategy_nationalist_agenda": "value = 35",
    "ai_strategy_consolidation_agenda": "value = 75",
    "ai_strategy_confrontation_agenda": "value = 25",
}
AVERSION_ADD = {
    "ai_strategy_conservative_agenda": 10,
    "ai_strategy_reactionary_agenda": 20,
    "ai_strategy_progressive_agenda": 10,
    "ai_strategy_egalitarian_agenda": 10,
    "ai_strategy_nationalist_agenda": 10,
    "ai_strategy_consolidation_agenda": 5,
    "ai_strategy_confrontation_agenda": 5,
}


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    """The body of the first `name = { ... }` (a top-level entry may carry a directive prefix)."""
    m = re.search(r"(?:^|\s)(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def _top_level_keys(body):
    """The keys at depth 0 of a block body, in order."""
    keys, depth = [], 0
    for tok in re.findall(r"[{}]|[^\s{}=]+(?=\s*=)", body):
        if tok == "{":
            depth += 1
        elif tok == "}":
            depth -= 1
        elif depth == 0:
            keys.append(tok)
    return keys


def _norm(text):
    return " ".join(text.replace("{", " { ").replace("}", " } ").split())


def _without_line(body, pattern):
    """The body with the first line matching `pattern` removed."""
    return re.sub(pattern, "", body, count=1)


class TestDefaultChangeLawChance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(DEFAULT.read_text(encoding="utf-8-sig"))
        cls.strategy = _block(cls.text, "ai_strategy_default")
        cls.field = _block(cls.strategy, "change_law_chance")

    def test_the_field_appears_once(self):
        self.assertEqual(_top_level_keys(self.strategy).count("change_law_chance"), 1)

    def test_restates_vanilla_then_adds(self):
        keys = _top_level_keys(self.field)
        self.assertEqual(keys[:2], ["value", "add"], "value = 1 (vanilla's), then the add, then the crisis branch")
        self.assertRegex(self.field, r"^\s*value\s*=\s*%d\s" % VANILLA_DEFAULT_CHANCE)
        self.assertRegex(self.field, r"\badd\s*=\s*%d\b" % CHANCE_ADD)
        self.assertEqual(VANILLA_DEFAULT_CHANCE + CHANCE_ADD, 40)

    def test_the_crisis_multiplier_still_applies(self):
        branch = _block(self.field, "if")
        self.assertIsNotNone(branch)
        self.assertEqual(_top_level_keys(self.field), ["value", "add", "if"])
        movement = _block(branch, "any_political_movement")
        self.assertRegex(movement, r"political_movement_support\s*>\s*0\.2\b")
        self.assertRegex(movement, r"political_movement_radicalism\s*>\s*0\.75\b")
        self.assertEqual(_top_level_keys(branch), ["limit", "multiply"])
        self.assertRegex(branch, r"\bmultiply\s*=\s*%d\b" % CRISIS_MULTIPLIER)

    def test_matches_the_game_files(self):
        path = _game_file("00_default_strategy.txt")
        if path is None:
            self.skipTest("no Victoria 3 install")
        vanilla = _block(_strip_comments(path.read_text(encoding="utf-8-sig")), "ai_strategy_default")
        self.assertEqual(_norm(_block(vanilla, "change_law_chance")), "value = %d" % VANILLA_DEFAULT_CHANCE)


class TestPoliticalStrategies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(POLITICAL.read_text(encoding="utf-8-sig"))
        cls.injected = re.findall(r"(?m)^INJECT:(ai_strategy_\w+)\s*=\s*\{", cls.text)

    def test_injects_the_seven_agendas_once_each(self):
        self.assertEqual(sorted(self.injected), sorted(VANILLA_AVERSION))
        self.assertNotRegex(self.text, r"(?m)^(?:REPLACE|TRY_REPLACE|REPLACE_OR_CREATE):", "INJECT only")

    def test_only_revolution_aversion(self):
        # The pass-chance floor and the agendas' own rates stay vanilla's (ai.md § Law-Change Cadence).
        for name in self.injected:
            with self.subTest(strategy=name):
                self.assertEqual(_top_level_keys(_block(self.text, name)), ["revolution_aversion"])

    def test_each_restates_vanilla_and_adds_once(self):
        for name, vanilla in VANILLA_AVERSION.items():
            with self.subTest(strategy=name):
                field = _block(_block(self.text, name), "revolution_aversion")
                adds = re.findall(r"(?m)^\s*add\s*=\s*(\d+)\s*$", field)
                self.assertIn(str(AVERSION_ADD[name]), adds)
                own = _without_line(field, r"(?m)^\s*add\s*=\s*%d\s*$" % AVERSION_ADD[name])
                self.assertEqual(_norm(own), vanilla)
                self.assertEqual(_top_level_keys(field)[:2], ["value", "add"])

    def test_aversion_stays_within_the_engine_range(self):
        for name, add in AVERSION_ADD.items():
            base = int(re.match(r"value = (\d+)", VANILLA_AVERSION[name]).group(1))
            with self.subTest(strategy=name):
                self.assertGreater(add, 0)
                self.assertLessEqual(base + add, 100)

    def test_sorts_before_the_other_ai_mods_file(self):
        # Two INJECTs of one field apply in file order and the later one wins; with that mod on, its aversion stands.
        self.assertLess(POLITICAL.name, "kai_political_strategies.txt")

    def test_restated_blocks_match_the_game_files(self):
        path = _game_file("03_political_strategies.txt")
        if path is None:
            self.skipTest("no Victoria 3 install")
        game = _strip_comments(path.read_text(encoding="utf-8-sig"))
        for name, vanilla in VANILLA_AVERSION.items():
            with self.subTest(strategy=name):
                self.assertEqual(_norm(_block(_block(game, name), "revolution_aversion")), vanilla)


class TestSelfCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = _strip_comments(SELFCHECK.read_text(encoding="utf-8-sig"))
        cls.verdict = _block(cls.body, "te_ai_law_cadence_selfcheck")
        cls.trigger = _block(cls.verdict, "trigger")
        cls.effect = _block(cls.verdict, "effect")
        cls.values = _strip_comments(SELFCHECK_VALUES.read_text(encoding="utf-8-sig"))

    def branches(self):
        """(limit, log line) of the if / else_if / else under random_country, in order."""
        chain = _block(self.effect, "random_country")
        out = []
        for m in re.finditer(r"(?m)^\t{3}(if|else_if|else) = \{", chain):
            body = _block(chain[m.start():], m.group(1))
            line = re.search(r'debug_log = "(TE_SELF_CHECK \w+ ai_law_cadence[^"]*)"', body).group(1)
            out.append((m.group(1), _norm(_block(body, "limit") or ""), line))
        return out

    def test_once_a_game_from_a_sub_action(self):
        self.assertRegex(self.body, r"on_monthly_pulse\s*=\s*\{\s*on_actions\s*=\s*\{\s*"
                                    r"te_ai_law_cadence_selfcheck_settle\s+te_ai_law_cadence_selfcheck\s*\}")
        self.assertNotRegex(self.body, r"on_monthly_pulse\s*=\s*\{[^}]*\beffect\b", "a sub-action, never an effect")
        # the latch: in the verdict's own trigger, and the first thing its effect sets
        self.assertIn("NOT = { has_global_variable = te_alc_checked }", self.trigger)
        self.assertTrue(self.effect.strip().startswith("set_global_variable = te_alc_checked"))

    def test_a_save_from_the_build_before_settles_first(self):
        # A save begun before this build would otherwise read the old world's share at its first pulse past 1890.
        settle = _block(self.body, "te_ai_law_cadence_selfcheck_settle")
        self.assertIn("change_global_variable = { name = te_alc_months add = 1 }", settle)
        self.assertRegex(settle, r"global_var:te_alc_months\s*<\s*36\b")
        self.assertRegex(self.trigger, r"has_global_variable = te_alc_months\s+global_var:te_alc_months\s*>=\s*36\b")
        # late enough that most AI countries have a law to start (conservatives read 0.09-0.10 in 1849 and 1867)
        self.assertRegex(self.trigger, r"game_date\s*>=\s*1890\.1\.1")

    def test_counts_ai_countries_not_decentralized_and_conservatives_among_them(self):
        loop = _block(self.effect, "every_country")
        self.assertEqual(_norm(_block(loop, "limit")), "is_ai = yes NOT = { is_country_type = decentralized }")
        for name in ("te_alc_chk_countries", "te_alc_chk_enacting", "te_alc_chk_cons", "te_alc_chk_cons_enacting"):
            with self.subTest(counter=name):
                self.assertIn("set_global_variable = { name = %s value = 0 }" % name, self.effect)
                self.assertIn("change_global_variable = { name = %s add = 1 }" % name, loop)
        self.assertIn("if = { limit = { enacting_any_law = yes } change_global_variable = { name = te_alc_chk_enacting "
                      "add = 1 } }", _norm(loop))
        cons = _norm(loop[loop.index("has_strategy = ai_strategy_conservative_agenda"):])
        self.assertTrue(cons.startswith("has_strategy = ai_strategy_conservative_agenda } change_global_variable = { "
                                        "name = te_alc_chk_cons add = 1 } if = { limit = { enacting_any_law = yes } "
                                        "change_global_variable = { name = te_alc_chk_cons_enacting add = 1 }"))

    def test_shares_are_enacting_over_counted(self):
        cons = _norm(_block(self.values, "te_alc_chk_cons_share"))
        self.assertEqual(cons, "value = 0 if = { limit = { global_var:te_alc_chk_cons > 0 } "
                               "value = global_var:te_alc_chk_cons_enacting divide = global_var:te_alc_chk_cons }")
        rest = _norm(_block(self.values, "te_alc_chk_rest_share"))
        self.assertEqual(rest, "value = 0 if = { limit = { global_var:te_alc_chk_countries > global_var:te_alc_chk_cons } "
                               "value = global_var:te_alc_chk_enacting subtract = global_var:te_alc_chk_cons_enacting "
                               "divide = te_alc_chk_rest_g }")
        self.assertEqual(_norm(_block(self.values, "te_alc_chk_rest_g")),
                         "value = global_var:te_alc_chk_countries subtract = global_var:te_alc_chk_cons")

    def test_ok_needs_conservatives_well_above_the_build_before(self):
        # The build before: conservatives at most 0.26 from 1890, the rest at most 0.43 (ai.md § Law-Change Cadence).
        kinds = [(kind, limit, line.split()[1]) for kind, limit, line in self.branches()]
        self.assertEqual(kinds, [
            ("if", "te_alc_chk_cons_g >= 40 te_alc_chk_cons_share >= 0.40", "OK"),
            ("else_if", "te_alc_chk_cons_g >= 40 te_alc_chk_cons_share < 0.30 te_alc_chk_rest_share < 0.55", "BROKEN"),
            ("else", "", "NO_VERDICT"),
        ])

    def test_broken_names_its_three_causes_and_no_line_sends_to_the_replace_alone(self):
        lines = {line.split()[1]: line for _, _, line in self.branches()}
        broken = lines["BROKEN"]
        for cause in ("the INJECT is ignored", "does not add to an agenda's own", "no law to start",
                      "not grounds for the REPLACE alone"):
            self.assertIn(cause, broken)
        for verdict, line in lines.items():
            with self.subTest(verdict=verdict):
                self.assertIn("cons=[SCOPE.ScriptValue('te_alc_chk_cons_enacting_g')|0]/", line)
                self.assertIn("rest=[SCOPE.ScriptValue('te_alc_chk_rest_enacting_g')|0]/", line)
                # log_triage.py shows a line's first 400 characters: the figures and, for BROKEN, the causes fit
                shown = re.sub(r"\[[^\]]*\]", "0000", line)[:400]
                self.assertIn("date=0000 (", shown)
                if verdict == "BROKEN":
                    self.assertIn("not grounds for the REPLACE alone", shown)

    def test_a_plain_marker_comes_before_the_templated_verdict(self):
        start = re.search(r'debug_log = "(TE_SELF_CHECK START ai_law_cadence[^"]*)"', self.effect)
        self.assertIsNotNone(start)
        self.assertNotIn("[", start.group(1))
        self.assertLess(start.start(), self.effect.index("random_country"))
        self.assertGreater(start.start(), self.effect.index("every_country"))

    def test_every_value_the_lines_read_is_defined(self):
        used = set(re.findall(r"te_alc_chk_\w+_g\b|te_alc_chk_\w+_share\b", self.effect))
        self.assertTrue(used)
        for name in sorted(used):
            with self.subTest(value=name):
                self.assertRegex(self.values, r"(?m)^%s\s*=" % name)

    def test_the_play_test_list_and_the_doc_carry_it(self):
        playtest = PLAYTEST.read_text(encoding="utf-8")
        self.assertIn("ai_law_cadence", playtest)
        self.assertIn("Fallback", playtest)
        self.assertIn("## Law-Change Cadence", SYSTEM_DOC.read_text(encoding="utf-8"))


def _game_file(name):
    try:
        from path_constants import base_game_path
    except Exception:
        return None
    path = Path(base_game_path) / "game/common/ai_strategies" / name
    return path if path.is_file() else None


if __name__ == "__main__":
    unittest.main()
