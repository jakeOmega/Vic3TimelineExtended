"""AI law cadence: AI countries start law changes more often, with more revolution aversion to match.

- common/ai_strategies/edited_political_strategies.txt: every political agenda's own change_law_chance is vanilla's
  whole block plus one `add = 39` line (2026-11-16), and seven agendas' revolution_aversion is vanilla's whole block
  plus one `add` line (2026-11-15); nothing else in those strategies (the pass-chance floor stays vanilla's).
- common/ai_strategies/edited_default_strategy.txt: ai_strategy_default's change_law_chance is vanilla's 1, times 10
  in the mod's crisis case. Its 2026-11-15 `add = 39` moved into the agendas: an unattended run read no rise with it
  there, and kept beside the agendas' 39 it would make the chance vanilla's + 79 if the default's field adds.
- TE_SELF_CHECK ai_law_cadence (common/on_actions/te_ai_law_cadence_selfcheck_on_actions.txt) and its play-test row.

The arithmetic behind the numbers, and the outcome table under each engine behavior:
docs/systems/mod_systems/ai.md § Law-Change Cadence.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STRATEGIES = ROOT / "common/ai_strategies"
DEFAULT = STRATEGIES / "edited_default_strategy.txt"
POLITICAL = STRATEGIES / "edited_political_strategies.txt"
SELFCHECK = ROOT / "common/on_actions/te_ai_law_cadence_selfcheck_on_actions.txt"
SELFCHECK_VALUES = ROOT / "common/script_values/te_ai_law_cadence_selfcheck_values.txt"
PLAYTEST = ROOT / "docs/testing/ai-economy-playtest.md"
SYSTEM_DOC = ROOT / "docs/systems/mod_systems/ai.md"

# Vanilla 1.15.1 (game/common/ai_strategies/00_default_strategy.txt): `change_law_chance = { value = 1 }`.
VANILLA_DEFAULT_CHANCE = 1
CHANCE_ADD = 39
CRISIS_MULTIPLIER = 10

# Vanilla 1.15.1's political agendas (every `type = political` strategy, all in 03_political_strategies.txt; the mod
# adds none), in the game file's order, with the name ai.md's outcome table gives each.
POLITICAL_AGENDAS = {
    "ai_strategy_conservative_agenda": "Conservative",
    "ai_strategy_reactionary_agenda": "Reactionary",
    "ai_strategy_progressive_agenda": "Progressive",
    "ai_strategy_egalitarian_agenda": "Egalitarian",
    "ai_strategy_nationalist_agenda": "Nationalist",
    "ai_strategy_maintain_mandate_of_heaven": "Mandate of Heaven",
    "ai_strategy_tanzimat_reforms": "Tanzimat",
    "ai_strategy_meiji_restoration": "Meiji Restoration",
    "ai_strategy_great_reforms": "Great Reforms",
    "ai_strategy_consolidation_agenda": "Consolidation",
    "ai_strategy_confrontation_agenda": "Confrontation",
}
# The seven the 41-60% target is for (ai.md): every agenda but the four with a purpose of their own.
COMMON_AGENDAS = (
    "ai_strategy_conservative_agenda", "ai_strategy_reactionary_agenda", "ai_strategy_progressive_agenda",
    "ai_strategy_egalitarian_agenda", "ai_strategy_nationalist_agenda", "ai_strategy_consolidation_agenda",
    "ai_strategy_confrontation_agenda",
)

_INSURRECTION = "if = { limit = { any_interest_group = { is_insurrectionary = yes } } add = %s } "
_SOCIALIST = "if = { limit = { has_revolutionary_socialist_laws = yes } add = 25 } "
_COMMITMENT = "if = { limit = { has_enactment_je_or_law_commitment = yes } add = %s } "

# Vanilla 1.15.1's change_law_chance block per agenda, comments stripped and whitespace-normalized.
# test_restated_blocks_match_the_game_files reads the game where installed (vanilla_parsed/ holds no AI strategies).
VANILLA_CHANCE = {
    "ai_strategy_conservative_agenda": "value = 2.5 " + _INSURRECTION % "7.5" + _SOCIALIST + _COMMITMENT % "25",
    "ai_strategy_reactionary_agenda": "value = 3.5 " + _INSURRECTION % "1.5" + _SOCIALIST + _COMMITMENT % "10",
    "ai_strategy_progressive_agenda": "value = 10 " + _INSURRECTION % "10" + _SOCIALIST + _COMMITMENT % "25",
    "ai_strategy_egalitarian_agenda": "value = 15 " + _INSURRECTION % "5" + _SOCIALIST + _COMMITMENT % "25",
    "ai_strategy_nationalist_agenda": "value = 10 " + _INSURRECTION % "10" + _SOCIALIST + _COMMITMENT % "25",
    "ai_strategy_maintain_mandate_of_heaven": "value = 1 " + _COMMITMENT % "10" + _SOCIALIST,
    "ai_strategy_tanzimat_reforms": "value = 100",
    "ai_strategy_meiji_restoration": "value = 50 " + _SOCIALIST,
    "ai_strategy_great_reforms": "value = 100 " + _SOCIALIST,
    "ai_strategy_consolidation_agenda": "value = 10 " + _INSURRECTION % "5" + _COMMITMENT % "25",
    "ai_strategy_confrontation_agenda": (
        "value = 20 " + _INSURRECTION % "5" + _COMMITMENT % "25"
        + "if = { limit = { has_journal_entry = je_social_revolution } add = 10 }"
    ),
}
VANILLA_CHANCE = {name: block.strip() for name, block in VANILLA_CHANCE.items()}

# Vanilla 1.15.1's revolution_aversion block per agenda the mod raises, and the rise.
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
# The agendas whose aversion stays vanilla's (no INJECT of it): Mandate of Heaven never goes ahead, the Meiji
# Restoration's starts rise 6%, the Tanzimat and the Great Reforms were certain already.
VANILLA_AVERSION_KEPT = {
    "ai_strategy_maintain_mandate_of_heaven": "value = 100",
    "ai_strategy_tanzimat_reforms": "value = 25",
    "ai_strategy_meiji_restoration": "value = 10",
    "ai_strategy_great_reforms": "value = 10",
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


def _top_level_entries(text):
    """(prefix, name, body) of each top-level `[PREFIX:]name = { ... }` of a stripped file."""
    out, depth, i = [], 0, 0
    for m in re.finditer(r"(?m)[{}]|^(?:([A-Z_]+):)?(\w+)\s*=\s*\{", text):
        if m.start() < i:
            continue
        if m.group(0) == "{":
            depth += 1
        elif m.group(0) == "}":
            depth -= 1
        elif depth == 0:
            body = _block(text[m.start():], m.group(2))
            out.append((m.group(1), m.group(2), body))
            i = m.end() + len(body) + 1
    return out


def _norm(text):
    return " ".join(text.replace("{", " { ").replace("}", " } ").split())


def _without_line(body, pattern):
    """The body with the first line matching `pattern` removed."""
    return re.sub(pattern, "", body, count=1)


def _value(block):
    """The number on a normalized block's leading `value =` line: the field in normal times."""
    return float(re.match(r"value = ([\d.]+)", block).group(1))


def _outcomes(name):
    """The agenda's change_law_chance and revolution_aversion in normal times, by what the engine does with the
    INJECT: replaces vanilla's field with it (or merges in only the keys vanilla's lacks, which gives the same),
    sums the two fields, or ignores it. Without the default strategy's 1, which adds to each if vanilla's comment holds.
    """
    v = _value(VANILLA_CHANCE[name])
    chance = {"replaced": v + CHANCE_ADD, "summed": 2 * v + CHANCE_ADD, "ignored": v}
    if name in VANILLA_AVERSION:
        a, rise = _value(VANILLA_AVERSION[name]), AVERSION_ADD[name]
        aversion = {"replaced": a + rise, "summed": 2 * a + rise, "ignored": a}
    else:
        a = _value(VANILLA_AVERSION_KEPT[name])
        aversion = {"replaced": a, "summed": a, "ignored": a}
    return chance, aversion


class TestDefaultChangeLawChance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(DEFAULT.read_text(encoding="utf-8-sig"))
        cls.strategy = _block(cls.text, "ai_strategy_default")
        cls.field = _block(cls.strategy, "change_law_chance")

    def test_the_field_appears_once(self):
        self.assertEqual(_top_level_keys(self.strategy).count("change_law_chance"), 1)

    def test_vanilla_value_and_no_rise(self):
        # The rise is in the agendas' own fields; one here too would count twice if the default's field adds.
        self.assertEqual(_top_level_keys(self.field), ["value", "if"], "value = 1 (vanilla's), then the crisis branch")
        self.assertRegex(self.field, r"^\s*value\s*=\s*%d\s" % VANILLA_DEFAULT_CHANCE)
        self.assertNotRegex(self.field, r"\badd\s*=")

    def test_the_crisis_multiplier_still_applies(self):
        branch = _block(self.field, "if")
        self.assertIsNotNone(branch)
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

    def test_injects_every_political_agenda_once(self):
        self.assertEqual(sorted(self.injected), sorted(POLITICAL_AGENDAS))
        self.assertNotRegex(self.text, r"(?m)^(?:REPLACE|TRY_REPLACE|REPLACE_OR_CREATE):", "INJECT only")

    def test_only_the_rate_and_the_aversion(self):
        # The pass-chance floor stays vanilla's (ai.md § Law-Change Cadence).
        for name in self.injected:
            with self.subTest(strategy=name):
                expected = (["revolution_aversion"] if name in VANILLA_AVERSION else []) + ["change_law_chance"]
                self.assertEqual(_top_level_keys(_block(self.text, name)), expected)

    def test_each_chance_restates_vanilla_and_adds_39_once(self):
        for name, vanilla in VANILLA_CHANCE.items():
            with self.subTest(strategy=name):
                field = _block(_block(self.text, name), "change_law_chance")
                self.assertEqual(len(re.findall(r"(?m)^\s*add\s*=\s*%d\s*$" % CHANCE_ADD, field)), 1)
                own = _without_line(field, r"(?m)^\s*add\s*=\s*%d\s*$" % CHANCE_ADD)
                self.assertEqual(_norm(own), vanilla)
                self.assertEqual(_top_level_keys(field)[:2], ["value", "add"])
                # `add` is the one top-level key vanilla's field lacks, so a merge of the new keys only gives the
                # same total as a replace.
                self.assertNotIn("add", _top_level_keys(own))

    def test_each_aversion_restates_vanilla_and_adds_once(self):
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
            with self.subTest(strategy=name):
                self.assertGreater(add, 0)
                self.assertLessEqual(_value(VANILLA_AVERSION[name]) + add, 100)

    def test_sorts_before_the_other_ai_mods_file(self):
        # Two INJECTs of one field apply in file order and the later one wins; with that mod on, its values stand.
        self.assertLess(POLITICAL.name, "kai_political_strategies.txt")

    def test_restated_blocks_match_the_game_files(self):
        path = _game_file("03_political_strategies.txt")
        if path is None:
            self.skipTest("no Victoria 3 install")
        game = _strip_comments(path.read_text(encoding="utf-8-sig"))
        political = [name for _, name, body in _top_level_entries(game) if re.search(r"\btype\s*=\s*political\b", body)]
        self.assertEqual(political, list(POLITICAL_AGENDAS), "vanilla's political agendas changed: add each new one")
        for name in POLITICAL_AGENDAS:
            with self.subTest(strategy=name):
                strategy = _block(game, name)
                self.assertEqual(_norm(_block(strategy, "change_law_chance")), VANILLA_CHANCE[name])
                aversion = _norm(_block(strategy, "revolution_aversion"))
                self.assertEqual(aversion, VANILLA_AVERSION.get(name) or VANILLA_AVERSION_KEPT[name])


class TestTheModsOtherStrategies(unittest.TestCase):
    """Nothing else in the mod sets the rate, adds a political agenda without it, or REPLACEs an agenda."""

    @classmethod
    def setUpClass(cls):
        cls.files = {p: _strip_comments(p.read_text(encoding="utf-8-sig")) for p in sorted(STRATEGIES.glob("*.txt"))}

    def test_no_other_file_sets_change_law_chance(self):
        # So a country's chance is the default's field and its agenda's, each as this test pins it.
        for path, text in self.files.items():
            if path in (DEFAULT, POLITICAL):
                continue
            with self.subTest(file=path.name):
                self.assertNotIn("change_law_chance", text)

    def test_no_replace_of_a_political_agenda(self):
        # A REPLACE applies after every INJECT, so it would drop the agenda's raised rate and aversion.
        for path, text in self.files.items():
            for prefix, name, _ in _top_level_entries(text):
                with self.subTest(file=path.name, entry=name):
                    if name in POLITICAL_AGENDAS:
                        self.assertEqual(prefix, "INJECT")

    def test_a_political_agenda_of_the_mods_own_carries_the_rise(self):
        for path, text in self.files.items():
            for prefix, name, body in _top_level_entries(text):
                if prefix is None and re.search(r"\btype\s*=\s*political\b", body):
                    with self.subTest(file=path.name, strategy=name):
                        self.assertRegex(_block(body, "change_law_chance") or "", r"\badd\s*=\s*%d\b" % CHANCE_ADD)


class TestOutcomes(unittest.TestCase):
    """The chance a country rolls under each thing the engine may do with an INJECTed script-value field."""

    def test_common_agendas_land_in_the_target_band_on_a_replace(self):
        # ai.md: about 41-60% at each 50-day law update, whether or not the default's 1 adds.
        for name in COMMON_AGENDAS:
            chance, _ = _outcomes(name)
            for default in (0, VANILLA_DEFAULT_CHANCE):
                with self.subTest(strategy=name, default_adds=bool(default)):
                    self.assertGreaterEqual(chance["replaced"] + default, 41)
                    self.assertLessEqual(chance["replaced"] + default, 60)

    def test_a_sum_overshoots_by_vanillas_own_value_at_most_80(self):
        for name in COMMON_AGENDAS:
            chance, _ = _outcomes(name)
            with self.subTest(strategy=name):
                self.assertEqual(chance["summed"] - chance["replaced"], chance["ignored"])
                self.assertLessEqual(chance["summed"] + VANILLA_DEFAULT_CHANCE, 80)

    def test_the_special_agendas(self):
        self.assertEqual(_outcomes("ai_strategy_maintain_mandate_of_heaven")[0]["replaced"], 40)
        self.assertEqual(_outcomes("ai_strategy_meiji_restoration")[0]["replaced"], 89)
        for name in ("ai_strategy_tanzimat_reforms", "ai_strategy_great_reforms"):
            with self.subTest(strategy=name):
                self.assertGreaterEqual(_outcomes(name)[0]["ignored"], 100, "certain already")

    def test_the_system_doc_carries_the_outcome_table(self):
        doc = SYSTEM_DOC.read_text(encoding="utf-8")

        def cell(x, chance):
            return "certain" if chance and x >= 100 else "%g" % x

        for name, label in POLITICAL_AGENDAS.items():
            chance, aversion = _outcomes(name)
            row = "| %s | %s |" % (label, " | ".join(
                [cell(chance[k], True) for k in ("replaced", "summed", "ignored")]
                + [cell(aversion[k], False) for k in ("replaced", "summed", "ignored")]))
            with self.subTest(strategy=name):
                self.assertIn(row, doc)


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
        self.assertIn("NOT = { has_global_variable = te_alc2_checked }", self.trigger)
        self.assertTrue(self.effect.strip().startswith("set_global_variable = te_alc2_checked"))

    def test_a_save_that_logged_the_first_verdict_checks_again(self):
        # The first build's latch and count were te_alc_checked / te_alc_months: a save that set them (the
        # 2026-11-16 run) must settle and check afresh on this build, not stay silent or read at once.
        self.assertNotRegex(self.body, r"\bte_alc_(checked|months)\b")

    def test_a_save_from_the_build_before_settles_first(self):
        # A save begun before this build would otherwise read the old world's share at its first pulse past 1890.
        settle = _block(self.body, "te_ai_law_cadence_selfcheck_settle")
        self.assertIn("NOT = { has_global_variable = te_alc2_checked }", settle)
        self.assertIn("change_global_variable = { name = te_alc2_months add = 1 }", settle)
        self.assertRegex(settle, r"global_var:te_alc2_months\s*<\s*36\b")
        self.assertRegex(self.trigger, r"has_global_variable = te_alc2_months\s+global_var:te_alc2_months\s*>=\s*36\b")
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

    def test_lines_name_the_agendas_field_and_broken_its_two_causes(self):
        lines = {line.split()[1]: line for _, _, line in self.branches()}
        self.assertIn("the political agendas' raised change_law_chance is in force", lines["OK"])
        broken = lines["BROKEN"]
        for cause in ("each agenda's own change_law_chance", "the agendas' INJECT is ignored", "no law to start",
                      "not grounds for the REPLACE alone"):
            self.assertIn(cause, broken)
        # The rise is in the agenda's own field now, so the default not adding is no cause any more.
        self.assertNotIn("does not add", broken)
        for verdict, line in lines.items():
            with self.subTest(verdict=verdict):
                self.assertNotIn("default strategy", line)
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
        # the first verdict, read 2026-11-16 on the build with the rise in the default strategy's field
        self.assertIn("TE_SELF_CHECK BROKEN ai_law_cadence cons=23/121=0.19 rest=21/98=0.21", playtest)
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
