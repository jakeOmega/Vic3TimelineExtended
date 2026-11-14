"""War Wounded counts every medical mobilization option (Workshop report, 2026-11-14).

Vanilla's je_war_nursing names First Aid and Field Hospitals by hand. The mod adds
Medevac Helicopters to the same exclusive medic-support group, better than Field
Hospitals, so an army entirely on Medevac started the entry (its formations read
as having no medics) and could never complete it (only Field Hospitals counted).
The mod's copy of the entry (common/journal_entries/te_vanilla_war_nursing.txt)
reads three triggers instead (common/scripted_triggers/te_war_nursing_triggers.txt).

These tests derive the two sets from the option files, vanilla's snapshot with the
mod's files over it: the options of group medic_support, and the ones whose
unit_recovery_rate_add is at least Field Hospitals'. They fail when a trigger
leaves an option out, so a medical option added later can't reopen the bug. The
copy itself is pinned to vanilla by test_vanilla_je_replacements.py.
"""

import itertools
import re
import unittest
from decimal import Decimal
from pathlib import Path

import vanilla_parsed
from paradox_file_parser import ParadoxFileParser
from test_tax_code_rule import load, plain

ROOT = Path(__file__).resolve().parent
OPTIONS_DIR = ROOT / "common/mobilization_options"
TRIGGERS = ROOT / "common/scripted_triggers/te_war_nursing_triggers.txt"
ENTRY = ROOT / "common/journal_entries/te_vanilla_war_nursing.txt"
LOC = ROOT / "localization/english/te_journal_entries_l_english.yml"

GROUP = "medic_support"
FIELD_HOSPITALS = "mobilization_option_field_hospitals"
HAS_MEDICS = "te_formation_has_medic_support"
FIELD_OR_BETTER = "te_formation_has_field_hospitals_or_better"
SHARE = "te_army_has_field_hospitals_or_better_share"
SHARE_TT = "je_war_nursing_combined_medic_share_tt"
THRESHOLD = Decimal("0.20")
STEP = Decimal("0.01")

REPLACING = {"", "REPLACE", "REPLACE_OR_CREATE", "TRY_REPLACE"}
INJECTING = {"INJECT", "INJECT_OR_CREATE", "TRY_INJECT"}


def as_list(value):
    return value if isinstance(value, list) else [value]


def option_name(target):
    prefix = "mobilization_option:"
    if not target.startswith(prefix):
        raise AssertionError(f"not a mobilization option target: {target}")
    return target[len(prefix):]


def recovery(body):
    value = (body.get("unit_modifier") or {}).get("unit_recovery_rate_add", "0")
    return Decimal(value)


def effective_options():
    """{option: {"group", "recovery", "possible"}} as the game sees them: vanilla's,
    replaced by a mod REPLACE or bare definition, an INJECT adding its recovery."""
    options = {}
    for name, body in plain(vanilla_parsed.load().data["Mobilization Options"]).items():
        options[name] = {"group": body.get("group"), "recovery": recovery(body),
                         "possible": body.get("possible", {})}
    injected = []
    for path in sorted(OPTIONS_DIR.glob("*.txt")):
        for key, body in load(path).items():
            directive, _, name = key.rpartition(":")
            if directive in REPLACING:
                options[name] = {"group": body.get("group"), "recovery": recovery(body),
                                 "possible": body.get("possible", {})}
            elif directive in INJECTING:
                injected.append((name, body))
            else:
                raise AssertionError(f"{path.name}: unknown directive on {key}")
    for name, body in injected:
        option = options.setdefault(name, {"group": None, "recovery": Decimal(0), "possible": {}})
        option["recovery"] += recovery(body)
        if "group" in body:
            option["group"] = body["group"]
    return options


def named_options(block):
    """The options a block's `has_mobilization_option` lines name."""
    return {option_name(t) for t in as_list(block.get("has_mobilization_option", []))}


def excluded_options(possible):
    """The options a `possible` block rules out: those named under a NOT or a NOR."""
    found = set()

    def walk(node, negated):
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            for item in as_list(value):
                if key == "has_mobilization_option" and isinstance(item, str):
                    if negated:
                        found.add(option_name(item))
                else:
                    walk(item, negated or key in ("NOT", "NOR"))

    walk(possible, False)
    return found


def fraction(entry):
    """(option, threshold) of one raw `army_mobilization_option_fraction` line."""
    _, body = entry
    _, target = body["target"]
    op, value = body["value"]
    if op != ">=":
        raise AssertionError(f"army_mobilization_option_fraction compares with {op}, not >=")
    return option_name(target), Decimal(value)


def compositions(options, total, step):
    """Every way to split `total` (in whole `step`s) over two or more of `options`,
    each part at least one step, as frozensets of (option, threshold)."""
    units = int(total / step)
    rungs = set()
    for size in range(2, len(options) + 1):
        for chosen in itertools.combinations(sorted(options), size):
            for cuts in itertools.combinations(range(1, units), size - 1):
                parts = [b - a for a, b in zip((0, *cuts), (*cuts, units))]
                rungs.add(frozenset((o, p * step) for o, p in zip(chosen, parts)))
    return rungs


class MedicalOptionSetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.options = effective_options()
        cls.medics = {n for n, o in cls.options.items() if o["group"] == GROUP}
        floor = cls.options[FIELD_HOSPITALS]["recovery"]
        cls.field_or_better = {n for n in cls.medics if cls.options[n]["recovery"] >= floor}
        cls.triggers = load(TRIGGERS)
        parser = ParadoxFileParser()
        parser.parse_file(str(TRIGGERS), apply_directives=False)
        cls.raw_triggers = parser.data

    def test_the_sets_are_what_this_test_was_written_against(self):
        # A guard on the derivation itself: if this fails, the option files moved,
        # and the tests below say which trigger to bring in line.
        self.assertIn("mobilization_option_medevac_helicopters", self.field_or_better)
        self.assertIn(FIELD_HOSPITALS, self.field_or_better)
        self.assertIn("mobilization_option_first_aid", self.medics - self.field_or_better)

    def test_has_medics_names_every_medic_support_option(self):
        named = named_options(self.triggers[HAS_MEDICS]["OR"])
        self.assertEqual(named, self.medics,
                         f"{HAS_MEDICS} must name every option of group {GROUP}")

    def test_field_hospitals_or_better_names_every_option_at_least_as_good(self):
        named = named_options(self.triggers[FIELD_OR_BETTER]["OR"])
        self.assertEqual(named, self.field_or_better,
                         f"{FIELD_OR_BETTER} must name every {GROUP} option whose "
                         "unit_recovery_rate_add is at least Field Hospitals'")

    def test_medic_options_exclude_each_other(self):
        # The share adds the options' fractions, which is exact only while a formation
        # carries one of them; vanilla's group has no other exclusivity rule.
        for name in sorted(self.medics):
            with self.subTest(option=name):
                missing = (self.medics - {name}) - excluded_options(self.options[name]["possible"])
                self.assertFalse(missing, f"{name}'s possible doesn't rule out {sorted(missing)}")

    def test_each_qualifying_option_alone_reaches_the_share(self):
        share = self.raw_triggers[SHARE][1]["OR"][1]
        singles = {fraction(e) for e in as_list(share["army_mobilization_option_fraction"])}
        self.assertEqual(singles, {(o, THRESHOLD) for o in self.field_or_better})

    def test_the_mixed_rungs_add_up_to_the_share(self):
        share = self.raw_triggers[SHARE][1]["OR"][1]
        tooltip = share["custom_tooltip"][1]
        self.assertEqual(tooltip["text"][1], SHARE_TT)
        rungs = []
        for _, rung in as_list(tooltip["OR"][1]["AND"]):
            self.assertEqual(set(rung), {"army_mobilization_option_fraction"})
            parts = [fraction(e) for e in as_list(rung["army_mobilization_option_fraction"])]
            names = [o for o, _ in parts]
            self.assertEqual(len(names), len(set(names)), f"an option twice in one rung: {parts}")
            self.assertLessEqual(set(names), self.field_or_better, f"rung {parts}")
            for _, threshold in parts:
                self.assertGreater(threshold, 0)
                self.assertEqual(threshold % STEP, 0, f"rung {parts} is off the {STEP} grid")
            # Below the share would complete the entry early: the dangerous direction.
            self.assertEqual(sum(t for _, t in parts), THRESHOLD, f"rung {parts}")
            rungs.append(frozenset(parts))
        self.assertEqual(len(rungs), len(set(rungs)), "a rung is written twice")
        self.assertEqual(set(rungs), compositions(self.field_or_better, THRESHOLD, STEP))

    def test_the_combined_line_names_the_options_and_the_share(self):
        text = LOC.read_text(encoding="utf-8-sig")
        line = re.search(rf"^ {SHARE_TT}:0 \"(.*)\"$", text, re.M)
        self.assertIsNotNone(line, f"{SHARE_TT} missing from {LOC.name}")
        spliced = set(re.findall(r"\$(mobilization_option_\w+)\$", line.group(1)))
        self.assertEqual(spliced, self.field_or_better)
        self.assertIn(f"{int(THRESHOLD * 100)}%", line.group(1))


class EntryReadsTheTriggersTest(unittest.TestCase):
    def test_the_entry_names_no_option_itself(self):
        text = re.sub(r"#[^\n]*", "", ENTRY.read_text(encoding="utf-8-sig"))
        self.assertNotIn("mobilization_option:", text)
        for trigger in (HAS_MEDICS, FIELD_OR_BETTER, SHARE):
            self.assertIn(trigger, text)

    def test_nursing_events_4_names_the_scopes_the_outcome_saves(self):
        # The base game's events aren't in vanilla_parsed/, so this needs a game install.
        try:
            from path_constants import base_game_path
            events = Path(base_game_path) / "game/events/tech_events/nursing_events.txt"
        except Exception:
            events = None
        if events is None or not events.is_file():
            self.skipTest("no Victoria 3 install")
        text = events.read_text(encoding="utf-8-sig")
        body = text[text.index("nursing_events.4 = {"):]
        self.assertIn("placement = scope:ongoing_war_state", body)
        for scope in ("complete_nursing_war", "ongoing_war_state"):
            self.assertIn(f"save_scope_as = {scope}", body)
            self.assertIn(f"save_scope_as = {scope}", ENTRY.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
