"""Reform or Revolution: no stance of the two movements it reads on a law nobody can leave.

Vanilla's global entry `je_reform_or_revolution` counts, each month and for
each socialist or labor movement with 5% support, (activism - 0.25) x 10
toward revolution, weighted by the country's share of the involved population.
The engine sets part of a movement's activism from its stance on each active
law: MOVEMENT_RADICALISM_FROM_ACTIVE_LAW_STANCE (vanilla's -0.05; the mod set
-0.1 until 2026-11-15 and sets nothing now) x the stance x the movement's
active_law_radicalism_multiplier (0.75 for both). A disapproved law that every
country holds from 1836 and none can replace while the entry runs is therefore
a fixed push toward revolution in every country: +0.075 activism for a
strongly_disapprove, +0.0375 for a disapprove (stance values -2 and -1
assumed, as for interest-group approval).
Unrestricted Automation (to Humanoid Robotics, era 11) and Unregulated
Donations (to Mass Media or Keynesian Economics, era 6) were two such laws.

These tests hold: the two movements are neutral on both, they still rate above
each one every law the lists they came from rated above it, the mod leaves the
define to vanilla (so another mod can set it), the figures above rest on
vanilla's value and multiplier, and no 1836 law either movement disapproves
lacks a law it rates higher that a country holding it can enact before era 6.
The same rule for every movement, by the era each can first exist in, is
test_movement_stance_guard.py's (#1832).

Run: python3 test_reform_or_revolution_stances.py
"""
import glob
import json
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

from paradox_file_parser import ParadoxFileParser  # noqa: E402

GENERATED = os.path.join(REPO, "common", "ideologies", "modified.txt")
HISTORY = os.path.join(REPO, "common", "history", "extra_history.txt")
DEFINES_DIR = os.path.join(REPO, "common", "defines")
ACTIVE_LAW_STANCE = "MOVEMENT_RADICALISM_FROM_ACTIVE_LAW_STANCE"
# Vanilla 1.15.1's value (game/common/defines/00_defines.txt). The repo keeps no
# copy of vanilla's defines (vanilla_parsed/ holds none), so the literal is
# checked against an installed game when there is one.
VANILLA_ACTIVE_LAW_STANCE = -0.05
VANILLA = os.path.join(REPO, "vanilla_parsed", "common")

MOVEMENTS = {
    "ideology_labor_movement": "movement_labor",
    "ideology_socialist_movement": "movement_socialist",
}
STANCE = {"strongly_disapprove": -2, "disapprove": -1, "neutral": 0, "approve": 1, "strongly_approve": 2}
LAST_ERA_OF_THE_ENTRY = 5  # it ended by 1856-1890 in the three 1.15 games read (era 3-4); era 5 is generous
AUTOMATION = "lawgroup_automation_policy"
UNRESTRICTED = "law_unrestricted_automation"
DONATIONS = "law_unregulated_donations"


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _block(text, name):
    """The body of the first `name = {` (or `REPLACE:name = {`, `INJECT:name = {`) that opens a line."""
    m = re.search(rf"(?m)^[ \t]*(?:[A-Z_]+:)?{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        return None
    i = j = m.end()
    depth = 1
    while depth:
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        j += 1
    return text[i:j - 1]


def generated_stances(ideology):
    """{lawgroup: {law: stance value}} for one ideology as modified.txt writes it."""
    body = _block(_read(GENERATED), ideology)
    assert body is not None, ideology
    return {group: {law: STANCE[s] for law, s in re.findall(r"(law_[\w\-]+)\s*=\s*(\w+)", inner)}
            for group, inner in re.findall(r"(lawgroup_\w+)\s*=\s*\{([^{}]*)\}", body)}


def _as_list(value):
    if value is None:
        return []
    value = value[1] if isinstance(value, (list, tuple)) and value and value[0] == "=" else value
    if isinstance(value, str):
        return [value]
    return list(value) if isinstance(value, (list, tuple)) else []


def _field(entry, key):
    entry = entry[1] if isinstance(entry, (list, tuple)) and entry and entry[0] == "=" else entry
    return entry.get(key) if isinstance(entry, dict) else None


def laws():
    """{law: (group, unlocking technologies, unlocking laws, disallowing laws)}, vanilla then the mod's own."""
    out = {}
    with open(os.path.join(VANILLA, "laws.json")) as f:
        for name, entry in json.load(f).items():
            group = _field(entry, "group")
            if group:
                out[name] = (_as_list(group)[0], _as_list(_field(entry, "unlocking_technologies")),
                             _as_list(_field(entry, "unlocking_laws")), _as_list(_field(entry, "disallowing_laws")))
    for path in sorted(glob.glob(os.path.join(REPO, "common", "laws", "*.txt"))):
        parser = ParadoxFileParser()
        parser.parse_file(path, apply_directives=False)
        for name, entry in parser.data.items():
            if ":" in name:
                continue  # INJECT:/REPLACE: of a vanilla law keeps vanilla's group and gates here
            group = _field(entry, "group")
            if group:
                out[name] = (_as_list(group)[0], _as_list(_field(entry, "unlocking_technologies")),
                             _as_list(_field(entry, "unlocking_laws")), _as_list(_field(entry, "disallowing_laws")))
    return out


def tech_eras():
    """{technology: era number}: vanilla's, then the mod's own files."""
    out = {}
    with open(os.path.join(VANILLA, "technologies.json")) as f:
        for name, entry in json.load(f).items():
            era = _field(entry, "era")
            if era:
                out[name] = int(_as_list(era)[0].split("_")[1])
    for path in sorted(glob.glob(os.path.join(REPO, "common", "technology", "technologies", "*.txt"))):
        parser = ParadoxFileParser()
        parser.parse_file(path, apply_directives=False)
        for name, entry in parser.data.items():
            era = _field(entry, "era")
            if era:
                out[name.split(":")[-1]] = int(_as_list(era)[0].split("_")[1])
    return out


def laws_of_1836():
    """Every law the history's first `every_country` block activates, conditional lines included."""
    first = _block(_block(_read(HISTORY), "GLOBAL"), "every_country")
    return sorted(set(re.findall(r"activate_law\s*=\s*law_type:(law_\w+)", first)))


class NeutralOnLockedDefaultsTest(unittest.TestCase):
    def test_both_movements_are_neutral_on_unrestricted_automation(self):
        for ideology in MOVEMENTS:
            self.assertEqual(generated_stances(ideology)[AUTOMATION][UNRESTRICTED], 0, ideology)

    def test_the_socialist_movement_is_neutral_on_unregulated_donations(self):
        self.assertEqual(generated_stances("ideology_socialist_movement")["lawgroup_electoral_finance"][DONATIONS], 0)

    def test_the_movements_still_back_what_their_lists_backed(self):
        """Every automation law the shared list rated above Unrestricted
        Automation the movement still rates above it, so it backs the same
        laws once Humanoid Robotics arrives."""
        import ideology_modifications as im

        for ideology, shared in (("ideology_labor_movement", "labor"), ("ideology_socialist_movement", "socialist")):
            # Since #1832 the lift is ideology_modifications.NEUTRAL_ON_LOCKED_DEFAULT's,
            # applied to the shared list (test_movement_stance_guard.py holds it for
            # every movement).
            self.assertEqual(im.AUTOMATION_STANCES[ideology], shared)
            self.assertIn(UNRESTRICTED, im.NEUTRAL_ON_LOCKED_DEFAULT[ideology])
            before = {law: STANCE[s] for law, s in im.AUTOMATION_LISTS[shared]}
            after = {law: STANCE[s] for law, s in im.modifications[ideology][AUTOMATION]}
            for law in before:
                if before[law] > before[UNRESTRICTED]:
                    self.assertGreater(after[law], after[UNRESTRICTED], (ideology, law))
        finance = generated_stances("ideology_socialist_movement")["lawgroup_electoral_finance"]
        for law in ("law_donation_limits", "law_publicly_funded_elections"):
            self.assertGreater(finance[law], finance[DONATIONS], law)

    def test_the_interest_groups_keep_their_lists(self):
        """Only the two movements moved: the Trade Unions' proletarian and the
        communists keep their stances on Unrestricted Automation."""
        self.assertEqual(generated_stances("ideology_proletarian")[AUTOMATION][UNRESTRICTED], -1)
        self.assertEqual(generated_stances("ideology_communist")[AUTOMATION][UNRESTRICTED], -2)

    def test_the_mod_leaves_the_define_to_vanilla(self):
        """No mod defines file sets it, so vanilla's value holds and another mod
        that sets it alone wins (the owner, 2026-11-15). Comments don't count."""
        for path in sorted(glob.glob(os.path.join(DEFINES_DIR, "*.txt"))):
            code = re.sub(r"#[^\n]*", "", _read(path))
            with self.subTest(path=os.path.relpath(path, REPO)):
                self.assertNotRegex(code, rf"\b{ACTIVE_LAW_STANCE}\s*=")

    def test_vanilla_value_matches_the_installed_game_when_present(self):
        try:
            import path_constants
            base = path_constants.base_game_path
        except Exception:  # no paths on this machine
            self.skipTest("no game paths")
        path = os.path.join(base, "game", "common", "defines", "00_defines.txt")
        if not os.path.exists(path):
            self.skipTest("no installed Victoria 3")
        m = re.search(rf"(?m)^\s*{ACTIVE_LAW_STANCE}\s*=\s*(-?[\d.]+)", _read(path))
        self.assertIsNotNone(m)
        self.assertEqual(float(m.group(1)), VANILLA_ACTIVE_LAW_STANCE)

    def test_the_figures_rest_on_these_values(self):
        """+0.075 = 2 x 0.05 x 0.75 and +0.0375 = 1 x 0.05 x 0.75: vanilla's define
        (above) and the movements' multiplier."""
        with open(os.path.join(VANILLA, "political_movements.json")) as f:
            movements = json.load(f)
        for movement in MOVEMENTS.values():
            self.assertEqual(float(_as_list(_field(movements[movement], "active_law_radicalism_multiplier"))[0]), 0.75)

    def test_no_disapproved_1836_law_without_an_answer_before_era_6(self):
        """For each law every 1836 country can start with: if either movement
        disapproves it, its group holds a law the movement rates higher that
        needs no technology or one of era 5 or earlier, and that the
        condition putting the 1836 law in force does not bar (No Campaign
        Finance Laws is disallowed by the voting laws Unregulated Donations
        needs)."""
        all_laws, eras = laws(), tech_eras()
        starting = laws_of_1836()
        self.assertIn(UNRESTRICTED, starting)
        self.assertIn(DONATIONS, starting)
        problems = []
        for ideology in MOVEMENTS:
            stances = generated_stances(ideology)
            for law in starting:
                group, _, needs_laws, _ = all_laws[law]
                own = stances.get(group, {}).get(law, 0)
                if own >= 0:
                    continue
                answers = []
                for other, (other_group, techs, _, barred_by) in all_laws.items():
                    if other_group != group or other == law or stances.get(group, {}).get(other, 0) <= own:
                        continue
                    if needs_laws and set(needs_laws) <= set(barred_by):
                        continue
                    if not techs or min(eras.get(t, 99) for t in techs) <= LAST_ERA_OF_THE_ENTRY:
                        answers.append(other)
                if not answers:
                    problems.append(f"{ideology} disapproves {law} ({group}), and nothing it rates higher opens by era {LAST_ERA_OF_THE_ENTRY}")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
