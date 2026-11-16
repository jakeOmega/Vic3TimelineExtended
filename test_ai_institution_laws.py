"""The AI doesn't found an institution its bureaucracy can't carry (#1822).

26 of the mod's laws carry an institution. Each level of an institution costs bureaucracy for as long as it exists, a
country short of bureaucracy loses tax revenue, and none of those laws' AI weights looked at bureaucracy: the
National Bank's standing +600 applied to a country already in shortage. Every such law now reads one shared trigger,
te_ai_law_brings_unstaffed_institution, and takes te_ai_unstaffed_institution_law_weight while it holds.

- every law the mod defines with `institution = X` carries the check for X in its ai_enact_weight_modifier;
- a vanilla law the mod INJECTs an institution into is listed in INJECTED with why it carries none;
- the trigger is vanilla's "bureaucracy in order" pair plus the new institution's own level-1 cost, and is false for
  a country that already has the institution;
- the mod sets none of the AI's three institution-spending defines, whose arithmetic at 7 and 24 institutions is
  the table in docs/systems/mod_systems/ai.md § AI Coverage of the Mod's Content.
"""
import re
import unittest
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
LAW_FILES = sorted((ROOT / "common/laws").glob("*.txt"))
TRIGGERS = ROOT / "common/scripted_triggers/te_ai_coverage_triggers.txt"
VALUES = ROOT / "common/script_values/te_ai_coverage_values.txt"
DEFINES = sorted((ROOT / "common/defines").glob("*.txt"))
SYSTEM_DOC = ROOT / "docs/systems/mod_systems/ai.md"

CHECK = "te_ai_law_brings_unstaffed_institution"
WEIGHT = "te_ai_unstaffed_institution_law_weight"

# Vanilla laws that get an institution line by INJECT, and why they carry no check.
INJECTED = {
    "law_public_health_insurance": "vanilla's own law and institution (the INJECT restates the line beside the mod's "
                                   "institution_modifier); vanilla's weight stands",
    "law_migration_controls": "the mod's Migration Controls institution costs a tenth of a normal one "
                              "(country_institution_cost_institution_migration_controls_mult = -0.9), and the check "
                              "would mean restating a vanilla law's weight by INJECT",
}

# Vanilla 1.15.1, game/common/defines/00_ai.txt (NAI). The mod leaves all three alone.
VANILLA_SPENDING = {
    "MAX_INSTITUTION_SPENDING_BASE": 0.015,
    "MAX_INSTITUTION_SPENDING_PER_INSTITUTION": 0.005,
    "INSTITUTION_SPENDING_DECREASE_SPENDING_RATIO": 2.0,
}
VANILLA_INSTITUTIONS = 7
MOD_INSTITUTIONS = 24


def entries(node):
    for part in node if isinstance(node, list) else [node]:
        if isinstance(part, dict):
            for key, (op, value) in part.items():
                yield key, op, value


def parse(path):
    parser = ParadoxFileParser()
    return parser.parse_object(parser.tokenize("{" + path.read_text(encoding="utf-8-sig") + "}"))[0]


def field(block, key):
    return next((value for k, _, value in entries(block) if k == key), None)


def plain(node):
    if isinstance(node, (dict, list)):
        return [[key, plain(value)] for key, _, value in entries(node)]
    return node


def institution_laws():
    """(law key as written, file, institution, block) for every law entry in the mod with an institution line."""
    for path in LAW_FILES:
        for name, _, block in entries(parse(path)):
            institution = field(block, "institution")
            if institution:
                yield name, path.name, institution, block


def ceiling(institutions, per_institution=VANILLA_SPENDING["MAX_INSTITUTION_SPENDING_PER_INSTITUTION"]):
    return VANILLA_SPENDING["MAX_INSTITUTION_SPENDING_BASE"] + per_institution * institutions


def percent(share):
    """A share as the doc prints it: one decimal, halves up (2.55% is 2.6%, whatever the float holds)."""
    return str((Decimal(repr(round(share, 6))) * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) + "%"


class InstitutionLawTests(unittest.TestCase):
    def test_every_institution_law_carries_the_staffing_check(self):
        missing, checked = [], 0
        for name, file, institution, block in institution_laws():
            if name.startswith("INJECT:"):
                continue
            checked += 1
            weight = field(block, "ai_enact_weight_modifier")
            wanted = ["if", [["limit", [[CHECK, [["INSTITUTION", institution]]]]], ["add", WEIGHT]]]
            if weight is None or wanted not in plain(weight):
                missing.append(f"{file}: {name} ({institution})")
        self.assertGreaterEqual(checked, 26)
        self.assertEqual(missing, [], "a law that founds an institution must weigh whether the bureaucracy can "
                                      "carry it: add the te_ai_law_brings_unstaffed_institution branch")

    def test_injected_institutions_are_the_ones_listed(self):
        injected = {name.split(":", 1)[1] for name, _, _, _ in institution_laws() if name.startswith("INJECT:")}
        self.assertEqual(injected, set(INJECTED))

    def test_no_weight_has_two_value_lines_or_two_checks(self):
        for name, file, institution, block in institution_laws():
            if name.startswith("INJECT:"):
                continue
            keys = plain(field(block, "ai_enact_weight_modifier"))
            with self.subTest(law=name):
                self.assertEqual(sum(1 for k, _ in keys if k == "value"), 1)
                self.assertEqual(sum(1 for k, v in keys if k == "if" and v[0][1][0][0] == CHECK), 1)

    def test_the_trigger(self):
        triggers = parse(TRIGGERS)
        self.assertEqual(plain(field(triggers, "te_ai_can_staff_new_institution")),
                         [["approaching_bureaucracy_shortage", "no"],
                          ["bureaucracy", "te_ai_new_institution_bureaucracy"]])
        text = re.sub(r"#[^\n]*", "", TRIGGERS.read_text(encoding="utf-8-sig"))
        self.assertRegex(text, r"bureaucracy\s*>=\s*te_ai_new_institution_bureaucracy")
        self.assertEqual(plain(field(triggers, CHECK)),
                         [["NOT", [["has_institution", "$INSTITUTION$"]]],
                          ["te_ai_can_staff_new_institution", "no"]])

    def test_the_sizes(self):
        values = parse(VALUES)
        self.assertEqual(plain(field(values, "te_ai_new_institution_bureaucracy")),
                         [["value", "total_population"], ["divide", "100000"], ["min", "10"]])
        # Vanilla's readme: +1000 is "very significant". Strong enough to outweigh a standing +600.
        self.assertLessEqual(float(field(values, WEIGHT)), -1000)


class SpendingDefineTests(unittest.TestCase):
    def test_the_mod_leaves_the_institution_spending_defines_alone(self):
        for path in DEFINES:
            text = re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))
            for key in VANILLA_SPENDING:
                with self.subTest(file=path.name, define=key):
                    self.assertNotRegex(text, r"\b" + key + r"\b",
                                        "the mod now sets this define: redo the table in ai.md and this test")

    def test_the_docs_table_matches_the_arithmetic(self):
        doc = SYSTEM_DOC.read_text(encoding="utf-8")
        self.assertAlmostEqual(ceiling(VANILLA_INSTITUTIONS), 0.050)
        self.assertAlmostEqual(ceiling(MOD_INSTITUTIONS), 0.135)
        rows = {
            0.005: ("5.0%", "7.5%", "10.0%", "13.5%"),
            0.003: ("3.6%", "5.1%", "6.6%", "8.7%"),
            0.002: ("2.9%", "3.9%", "4.9%", "6.3%"),
            0.0015: ("2.6%", "3.3%", "4.1%", "5.1%"),
        }
        for per, shown in rows.items():
            computed = tuple(percent(ceiling(n, per)) for n in (7, 12, 17, 24))
            with self.subTest(per_institution=per):
                self.assertEqual(computed, shown)
                self.assertTrue("| " + " | ".join(shown) + " |" in doc, f"ai.md's table lacks the row for {per}")

    def test_matches_the_game_files(self):
        try:
            from path_constants import base_game_path
            path = Path(base_game_path) / "game/common/defines/00_ai.txt"
        except Exception:
            path = None
        if path is None or not path.is_file():
            self.skipTest("no Victoria 3 install")
        text = path.read_text(encoding="utf-8-sig")
        for key, value in VANILLA_SPENDING.items():
            with self.subTest(define=key):
                m = re.search(r"(?m)^\s*" + key + r"\s*=\s*([\d.]+)", text)
                self.assertIsNotNone(m)
                self.assertEqual(float(m.group(1)), value)


if __name__ == "__main__":
    unittest.main()
