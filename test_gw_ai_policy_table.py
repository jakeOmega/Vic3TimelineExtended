"""The AI's climate-policy table: adopt and repeal read the same threshold.

Every AI used to hold seven of the eight mitigation policies by 1.26 C, because
each adopt button weighed temperature alone and every repeal weight was zero
above ~0.5 C (common/script_values/global_warming_ai_values.txt, header). The
fix gives each policy one threshold on a per-country climate will: adopt at or
above it, repeal only a band below it. That only works while each button pair
reads the SAME threshold, and nothing in the engine notices when a pair drifts
apart -- a repeal gate above its adopt gate flips a policy every roll, and an
adopt with no repeal is the old ratchet again. Each policy's will is a shared
core plus the same five signals under per-policy weights; the weights are a
table in the values file's header, checked here against the code so the table
a reader edits is the one the game runs. Everything is derived from the
journal entry's `scripted_button = gw_*` lines.
"""

import json
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
JE = ROOT / "common/journal_entries/je_global_warming.txt"
BUTTONS = ROOT / "common/scripted_buttons/global_warming_buttons.txt"
VALUES = ROOT / "common/script_values/global_warming_ai_values.txt"
TRIGGERS = ROOT / "common/scripted_triggers/global_warming_triggers.txt"
MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"

# The five signals every policy's will weighs, in the header table's column
# order. Industrialists is the one that flips on its own (at elections) and is
# yes/no, so its weight must stay inside the repeal band in every row.
SIGNALS = ("laissez_faire", "industrialists", "movement", "wealth", "fossil")
ELECTION_SIGNALS = ("industrialists",)


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(path), apply_directives=False)
    return parser.data


def _body(entry):
    """The block of a parsed `key = { ... }` entry ((op, value) pair)."""
    return entry[1]


def _items(node):
    """A repeated key parses to a list of (op, value) pairs, a single one to
    one pair; always return the list."""
    return node if isinstance(node[0], (list, tuple)) else [node]


def _top_level_block(body, header):
    block = body[body.index("\n" + header + " = {") + 1:]
    return block[: block.index("\n}") + 2]


def _ai_chance(button):
    block = _top_level_block(_text(BUTTONS), button)
    start = block.index("\tai_chance = {")
    return block[start: block.index("\n\t}", start) + 3]


def _policies():
    """Policy keys, from the adopt half of every button the entry registers."""
    names = re.findall(r"(?m)^\s*scripted_button = (gw_\w+)_button", _text(JE))
    return [n[len("gw_"):] for n in names if not n.startswith("gw_remove_")]


def _header_table():
    """{policy: {signal: weight}} from the values file's header table."""
    rows = {}
    for line in _text(VALUES).splitlines():
        if not line.startswith("#"):
            if rows:
                break
            continue
        m = re.match(r"#\s+([a-z_]+)" + r"\s+(-?\d+)" * len(SIGNALS) + r"\s*$", line)
        if m:
            rows[m.group(1)] = dict(zip(SIGNALS, map(int, m.groups()[1:])))
    return rows


def _code_weights(values, policy):
    """(shared core, {signal: weight}, signals in order of appearance) for
    one policy's will as the game computes it."""
    will = _body(values[f"gw_ai_will_{policy}"])
    weights, order = {}, []
    for term in _items(will["add"]):
        block = _body(term)
        signal = block["value"][1].removeprefix("gw_ai_sig_")
        order.append(signal)
        weights[signal] = int(block["multiply"][1])
    return will["value"][1], weights, order


def _authority_cost(policy):
    """The policy modifier's country_authority_cost_add, found through the
    shared `gw_policy_<p>_active` trigger (the button's key and the modifier's
    name differ for reforestation)."""
    trigger = _top_level_block(_text(TRIGGERS), f"gw_policy_{policy}_active")
    modifier = re.search(r"has_modifier = (\w+)", trigger).group(1)
    block = _top_level_block(_text(MODIFIERS), modifier)
    m = re.search(r"country_authority_cost_add = (-?\d+)", block)
    return int(m.group(1)) if m else 0


class GwAiPolicyTableTest(unittest.TestCase):
    def setUp(self):
        self.values = _parse(VALUES)

    def test_eight_policies_each_with_a_repeal_button(self):
        policies = _policies()
        self.assertEqual(len(policies), 8, policies)
        registered = set(re.findall(r"(?m)^\s*scripted_button = (gw_\w+)", _text(JE)))
        for p in policies:
            self.assertIn(f"gw_remove_{p}_button", registered)

    def test_adopt_reads_only_its_own_margin(self):
        for p in _policies():
            with self.subTest(policy=p):
                chance = _ai_chance(f"gw_{p}_button")
                margins = set(re.findall(r"gw_ai_\w+_margin_\w+", chance))
                self.assertEqual(margins, {f"gw_ai_adopt_margin_{p}"})
                self.assertIn(f"gw_ai_adopt_margin_{p} >= 0", chance)
                # Temperature belongs in the will, not beside it: a bare
                # temperature term here is the old ratchet.
                self.assertNotIn("temperature_anomaly_display", chance)

    def test_repeal_reads_only_its_own_margin(self):
        for p in _policies():
            with self.subTest(policy=p):
                chance = _ai_chance(f"gw_remove_{p}_button")
                margins = set(re.findall(r"gw_ai_\w+_margin_\w+", chance))
                self.assertEqual(margins, {f"gw_ai_repeal_margin_{p}"})
                self.assertIn(f"gw_ai_repeal_margin_{p} > 0", chance)
                self.assertNotIn("temperature_anomaly_display", chance)

    def test_repeal_margin_is_derived_from_the_adopt_margin(self):
        for p in _policies():
            with self.subTest(policy=p):
                adopt = _body(self.values[f"gw_ai_adopt_margin_{p}"])
                self.assertEqual(adopt["value"][1], f"gw_ai_will_{p}")
                int(adopt["subtract"][1])  # the threshold, written once, here
                repeal = _body(self.values[f"gw_ai_repeal_margin_{p}"])
                self.assertEqual(repeal["value"][1], "0")
                subtracted = [s[1] for s in _items(repeal["subtract"])]
                self.assertEqual(
                    subtracted, [f"gw_ai_adopt_margin_{p}", "gw_ai_repeal_band"]
                )

    def test_each_will_is_the_shared_core_plus_every_signal(self):
        for p in _policies():
            with self.subTest(policy=p):
                core, _, order = _code_weights(self.values, p)
                self.assertEqual(core, "gw_ai_will_shared")
                # Every signal exactly once, zeros included: a dropped term
                # would otherwise be indistinguishable from a zero weight.
                self.assertEqual(sorted(order), sorted(SIGNALS))
                for signal in SIGNALS:
                    self.assertIn(f"gw_ai_sig_{signal}", self.values)

    def test_header_table_matches_the_code(self):
        table = _header_table()
        self.assertEqual(sorted(table), sorted(_policies()))
        for p in _policies():
            with self.subTest(policy=p):
                _, weights, _ = _code_weights(self.values, p)
                self.assertEqual(weights, table[p])

    def test_band_is_wider_than_any_election_driven_term(self):
        band = int(self.values["gw_ai_repeal_band"][1])
        shared = _body(self.values["gw_ai_will_shared"])
        ig_terms = [
            abs(int(_body(branch)["add"][1]))
            for branch in _items(shared["if"])
            if "is_in_government" in json.dumps(_body(branch)["limit"])
        ]
        self.assertTrue(ig_terms, "no interest-group term in the shared core")
        for p in _policies():
            _, weights, _ = _code_weights(self.values, p)
            ig_terms += [abs(weights[s]) for s in ELECTION_SIGNALS]
        self.assertGreater(band, max(ig_terms))

    def test_adopt_checks_the_authority_the_policy_costs(self):
        for p in _policies():
            with self.subTest(policy=p):
                cost = _authority_cost(p)
                adopt = _ai_chance(f"gw_{p}_button")
                repeal = _ai_chance(f"gw_remove_{p}_button")
                if cost:
                    self.assertIn(f"authority >= {cost}", adopt)
                    self.assertIn("authority < 0", repeal)
                else:
                    self.assertNotIn("authority", adopt)
                    self.assertNotIn("authority < 0", repeal)


if __name__ == "__main__":
    unittest.main()
