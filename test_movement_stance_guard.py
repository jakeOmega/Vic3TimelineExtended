"""No movement disapproves of a law no government can leave (#1832).

A political movement's target activism takes, from every law in force,
MOVEMENT_RADICALISM_FROM_ACTIVE_LAW_STANCE (vanilla's -0.05; the mod leaves it
to vanilla since #1824) x the movement's stance on it (-2 to 2) x its
active_law_radicalism_multiplier. A disapproved law that a country holds from
1836, while nothing the movement rates higher can be enacted, is activism no
government can answer: a measurement of two AI observer games (2026-11-15)
found the law term the largest part of the activism behind 34 of 42 civil
wars, a third of it from the mod's own law groups.

The rule: a movement may disapprove of a law a country can hold from 1836 only
if it rates higher a law of the same group that a country can enact by the era
in which the movement can first exist. `movement_stances.standing_grievances`
reads both sides (its section comment says how, and what it does with a
condition it can't place in time); the resolution is an era.

These tests hold the rule for every movement and every ideology it can hold
(`set_core_ideology` switches included), on the mod's data, for every row the
mod makes worse than vanilla's own data gives: vanilla's design stays
vanilla's. A grievance that is meant goes in REVIEWED with a date and a
reason; a law whose gate the guard can't read, but a person has, goes in
OPEN_GATES. Both fail when an entry stops being needed. The stances moved to
neutral are in ideology_modifications.NEUTRAL_ON_LOCKED_DEFAULT, and the last
tests hold how they were moved.

Run: python3 -m pytest test_movement_stance_guard.py -q
"""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import movement_stances as mvs  # noqa: E402
from ideology_lawgroup_audit import carrier_laws  # noqa: E402

# {(ideology, law): "YYYY-MM-DD: why the standing grievance is meant"}.
REVIEWED = {}

# {law: "YYYY-MM-DD: why the conditions the guard can't read don't keep it from
# being an answer"}. Each is an answer in time for some row the mod makes.
OPEN_GATES = {
    "law_national_militia": "2026-11-15: barred only to the leader of a power bloc with the Military Treaty "
                            "Organization identity",
    "law_diplomatic_navy": "2026-11-15: visible to a country with a coastal state, the only kind that holds a "
                           "navy law to object to",
    "law_merchant_navy": "2026-11-15: visible to a country with a coastal state, as Diplomatic Navy",
    "law_jeune_ecole": "2026-11-15: visible to a country with a coastal state, as Diplomatic Navy",
    "law_littoral_defense": "2026-11-15: visible to a country with a coastal state, as Diplomatic Navy",
    # te_tax_vanilla_law_gates.txt: barred under the Legislated Tax Code rule,
    # which moves every country onto the tax code, so then no country holds a
    # vanilla taxation law to object to either.
    "law_consumption_based_taxation": "2026-11-15: barred only under the tax code rule (comment above)",
    "law_land_based_taxation": "2026-11-15: barred only under the tax code rule (comment above)",
    "law_per_capita_based_taxation": "2026-11-15: barred only under the tax code rule (comment above)",
    "law_proportional_taxation": "2026-11-15: barred only under the tax code rule (comment above)",
    "law_graduated_taxation": "2026-11-15: barred only under the tax code rule (comment above)",
}

# Vanilla's own standing grievances, left to vanilla: (movement, ideology, law).
# The modernizer's second-tier ideology disapproves of Child Labor Allowed, and
# Restricted Child Labor opens an era after Academia.
VANILLA_STANDING = {
    ("movement_modernizer", "ideology_modernizer_movement_2", "law_child_labor_allowed"),
}


def _key(row):
    return row["ideology"], row["law"]


def _describe(row):
    answers = ", ".join(f"{a['law']} (era {a['era']}{', unread: ' + '/'.join(a['unread']) if a['unread'] else ''})"
                        for a in row["answers"]) or "none"
    return (f"{row['movement']} as {row['ideology']} (from era {row['first_era']}) rates {row['law']} "
            f"{row['stance']:+d}: {row['verdict']}; rated higher: {answers}")


class _Data:
    _cache = None

    @classmethod
    def get(cls):
        if cls._cache is None:
            ms, vanilla = mvs.load_state(REPO)
            merged = {et: ms.get_data(et) or {} for et in mvs.ENTITY_TYPES}
            carriers = frozenset(carrier_laws(REPO))
            seeded = frozenset(mvs.history_seeded_laws(REPO))

            def run(data, carriers_, seeded_, gates):
                return mvs.standing_grievances(
                    data.get("Political Movements") or {}, data.get("Ideologies") or {}, data.get("Laws") or {},
                    data.get("Technologies") or {}, carriers_, seeded_, gates)

            cls._cache = {
                "merged": run(merged, carriers, seeded, frozenset(OPEN_GATES)),
                "merged_unreviewed": run(merged, carriers, seeded, frozenset()),
                "vanilla": run(vanilla, frozenset(), frozenset(), frozenset(OPEN_GATES)),
                "vanilla_unreviewed": run(vanilla, frozenset(), frozenset(), frozenset()),
                "seeded": seeded,
                "laws": merged["Laws"],
            }
        return cls._cache


class MovementStanceGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = _Data.get()

    def test_every_technology_is_placed_in_an_era(self):
        """A technology the era table lacks is a gate the guard can't place."""
        self.assertEqual(self.data["merged"]["unknown_technologies"], [])
        self.assertEqual(self.data["vanilla"]["unknown_technologies"], [])

    def test_the_history_baseline_is_read(self):
        for law in ("law_unrestricted_automation", "law_punishment_focused_criminal_justice",
                    "law_traditional_heredity", "law_unregulated_banking", "law_unregulated_donations"):
            self.assertIn(law, self.data["seeded"])

    def test_no_movement_disapproves_a_law_no_government_can_leave(self):
        new = [r for r in mvs.new_grievances(self.data["merged"], self.data["vanilla"]) if _key(r) not in REVIEWED]
        self.assertEqual([_describe(r) for r in new], [])

    def test_reviewed_grievances_are_still_there(self):
        live = {_key(r) for r in mvs.new_grievances(self.data["merged"], self.data["vanilla"])}
        self.assertEqual(sorted(set(REVIEWED) - live), [], "stale REVIEWED entries")
        for key, why in REVIEWED.items():
            self.assertRegex(why, r"^\d{4}-\d{2}-\d{2}: \S", key)

    def test_open_gates_are_unread_and_answer_something(self):
        """Each entry is a law with a condition the guard can't read, and an
        answer in time to some row the mod makes that is unread without it."""
        used = set()
        for row in mvs.new_grievances(self.data["merged_unreviewed"], self.data["vanilla_unreviewed"]):
            if row["verdict"] == "unread":
                used |= {a["law"] for a in row["answers"] if a["era"] <= row["first_era"]}
        self.assertEqual(sorted(set(OPEN_GATES) - used), [], "OPEN_GATES entries that answer nothing")
        for law, why in OPEN_GATES.items():
            self.assertRegex(why, r"^\d{4}-\d{2}-\d{2}: \S", law)

    def test_vanilla_own_standing_grievances(self):
        """Left to vanilla, and listed so a vanilla patch that changes them shows."""
        own = {(r["movement"], r["ideology"], r["law"]) for r in self.data["vanilla"]["rows"]
               if r["verdict"] == "standing"}
        self.assertEqual(own, VANILLA_STANDING)

    def test_every_movement_is_read(self):
        """Every movement the mod and vanilla define, and every ideology it can
        switch to, has rows (a movement with no disapproved holdable law has
        none, so this counts ideologies with any stance at all)."""
        rows = self.data["merged"]["rows"]
        movements = {r["movement"] for r in rows}
        for name in ("movement_environmental", "movement_civil_rights", "movement_anti_war", "movement_liberal",
                     "movement_cultural_minority", "movement_socialist"):
            self.assertIn(name, movements)
        ideologies = {r["ideology"] for r in rows}
        for ideology in ("ideology_revolutionary_socialist_movement", "ideology_pluralist_movement_4",
                         "ideology_liberal_republican_movement"):
            self.assertIn(ideology, ideologies)


class GateReadingTest(unittest.TestCase):
    """How the guard reads gates, on small hand-made data."""

    ERAS = {"tech_a": 2, "tech_b": 4, "tech_c": 6}

    def test_a_movement_needs_every_technology_of_a_block_and_one_of_an_or(self):
        body = {"creation_trigger": {"has_technology_researched": "tech_a",
                                     "OR": {"has_technology_researched": ["tech_b", "tech_c"]}}}
        self.assertEqual(mvs.movement_first_era(body, self.ERAS), (4, set()))

    def test_a_movement_ignores_negations_and_other_conditions(self):
        body = {"creation_trigger": {"NOT": {"has_technology_researched": "tech_c"}, "is_subject": "no",
                                     "has_law": "law_type:law_late"}}
        self.assertEqual(mvs.movement_first_era(body, self.ERAS), (1, set()))

    def test_an_unknown_technology_is_reported(self):
        self.assertEqual(mvs.movement_first_era({"creation_trigger": {"has_technology_researched": "tech_x"}},
                                                self.ERAS)[1], {"tech_x"})

    def test_a_law_opens_at_its_earliest_technology_and_unlocking_law(self):
        laws = {
            "law_late": {"group": "lawgroup_g", "unlocking_technologies": ["tech_b", "tech_c"]},
            "law_needs": {"group": "lawgroup_g", "unlocking_laws": ["law_late"]},
            "law_never": {"group": "lawgroup_g", "can_enact": {"always": "no"}},
            "law_tagged": {"group": "lawgroup_g", "is_visible": {"c:RUS": "this"}},
            "law_excepted": {"group": "lawgroup_g", "can_enact": {"trigger_if": {"limit": {"c:BIC": "ROOT"}, "x": "y"}}},
        }
        gates, unknown = mvs.law_gates(laws, self.ERAS)
        self.assertEqual(unknown, set())
        self.assertEqual(gates["law_late"]["era"], 4)
        self.assertEqual(gates["law_needs"]["era"], 4)
        self.assertIsNone(gates["law_never"]["era"])
        self.assertEqual((gates["law_tagged"]["era"], gates["law_tagged"]["unread"]), (1, ["c:RUS"]))
        self.assertEqual(gates["law_excepted"]["unread"], [])

    def _rows(self, stances, laws, first="tech_a", carriers=frozenset(), open_gates=frozenset()):
        movements = {"movement_m": {"ideology": "ideology_m",
                                    "creation_trigger": {"has_technology_researched": first}}}
        ideologies = {"ideology_m": {"lawgroup_g": stances}}
        return mvs.standing_grievances(movements, ideologies, laws, {k: {"era": f"era_{v}"} for k, v in
                                                                     self.ERAS.items()},
                                       carriers, frozenset(), open_gates)["rows"]

    GATES = {
        "law_later": {"unlocking_technologies": ["tech_b"]},
        "law_now": {"unlocking_technologies": ["tech_a"]},
        "law_tagged": {"is_visible": {"c:RUS": "this"}},
    }

    def _verdicts(self, other, stance="approve", **kwargs):
        """The default disapproved, one other law of the group rated `stance`.
        (A law the block leaves out would be neutral, so an answer: each case
        has only the two.)"""
        laws = {"law_default": {"group": "lawgroup_g"}, other: {"group": "lawgroup_g", **self.GATES[other]}}
        return [r["verdict"] for r in self._rows({"law_default": "disapprove", other: stance}, laws, **kwargs)]

    def test_verdicts(self):
        self.assertEqual(self._verdicts("law_later"), ["standing"])
        self.assertEqual(self._verdicts("law_now", "neutral"), ["answered"])
        self.assertEqual(self._verdicts("law_now", "disapprove"), ["standing"])
        self.assertEqual(self._verdicts("law_tagged"), ["unread"])
        self.assertEqual(self._verdicts("law_tagged", open_gates=frozenset({"law_tagged"})), ["answered"])
        self.assertEqual(self._verdicts("law_now", carriers=frozenset({"law_now"})), ["standing"])
        # a movement of the later era meets the later law in time
        self.assertEqual(self._verdicts("law_later", first="tech_b"), ["answered"])

    def test_a_law_the_block_leaves_out_is_a_neutral_answer(self):
        laws = {"law_default": {"group": "lawgroup_g"}, "law_now": {"group": "lawgroup_g", **self.GATES["law_now"]}}
        self.assertEqual([r["verdict"] for r in self._rows({"law_default": "disapprove"}, laws)], ["answered"])

    def test_an_answer_barred_by_what_the_law_in_force_needs_does_not_count(self):
        laws = {"law_vote": {"group": "lawgroup_v"},
                "law_default": {"group": "lawgroup_g", "unlocking_laws": ["law_vote"]},
                "law_other": {"group": "lawgroup_g", "disallowing_laws": ["law_vote"]}}
        rows = self._rows({"law_default": "disapprove", "law_other": "approve"}, laws)
        self.assertEqual([r["verdict"] for r in rows], ["standing"])


class NeutralOnLockedDefaultTest(unittest.TestCase):
    """How the flagged stances were moved (ideology_modifications.NEUTRAL_ON_LOCKED_DEFAULT)."""

    @classmethod
    def setUpClass(cls):
        import ideology_modifications as im

        cls.im = im
        cls.rank = im._STANCE_RANK

    def test_the_lift_keeps_every_preference_over_the_default(self):
        """Neutral on the default; every law strictly above it before is
        strictly above it after; no two other laws change order."""
        for (ideology, law), before in self.im.LOCKED_DEFAULT_SOURCES.items():
            group = self.im.LOCKED_DEFAULT_GROUPS[law]
            after = dict(self.im.modifications[ideology][group])
            before = dict(before)
            with self.subTest(ideology=ideology, law=law):
                self.assertLess(self.rank[before[law]], 0)
                self.assertEqual(after[law], "neutral")
                self.assertEqual(list(after), list(before))
                for other in before:
                    if other != law and self.rank[before[other]] > self.rank[before[law]]:
                        self.assertGreater(self.rank[after[other]], 0, other)
                for a in before:
                    for b in before:
                        if law not in (a, b) and self.rank[before[a]] > self.rank[before[b]]:
                            self.assertGreaterEqual(self.rank[after[a]], self.rank[after[b]], (a, b))

    def test_only_movement_ideologies_move(self):
        """The interest groups' ideologies keep the shared lists: the Trade
        Unions' proletarian still disapproves of Unrestricted Automation."""
        for ideology in self.im.NEUTRAL_ON_LOCKED_DEFAULT:
            self.assertTrue(ideology.endswith("_movement") or re.search(r"_movement_\d$", ideology), ideology)
        self.assertEqual(dict(self.im.modifications["ideology_proletarian"]["lawgroup_automation_policy"])
                         ["law_unrestricted_automation"], "disapprove")
        self.assertEqual(dict(self.im.progressive_criminal_justice)["law_punishment_focused_criminal_justice"],
                         "disapprove")

    def test_the_lift_rebuilds_1824s_lists(self):
        """#1824 wrote the labor and socialist movements' automation lists by
        hand; the lift gives the same."""
        group = "lawgroup_automation_policy"
        self.assertEqual(self.im.modifications["ideology_labor_movement"][group],
                         self.im.automation_constructor("0", "+", "++", "+"))
        self.assertEqual(self.im.modifications["ideology_socialist_movement"][group],
                         self.im.automation_constructor("0", "+", "+", "++"))

    def test_the_generated_file_has_the_lifted_stances(self):
        with open(os.path.join(REPO, "common", "ideologies", "modified.txt"), encoding="utf-8-sig") as f:
            text = f.read()
        for ideology, laws in self.im.NEUTRAL_ON_LOCKED_DEFAULT.items():
            m = re.search(rf"(?m)^(?:REPLACE:|INJECT:)?{ideology} = \{{", text)
            self.assertIsNotNone(m, ideology)
            body = text[m.end():text.find("\n}", m.end())]
            for law in laws:
                self.assertRegex(body, rf"\b{law} = neutral\b", (ideology, law))


class EnvironmentalMinistryTest(unittest.TestCase):
    """The environmental movement counts a missing Ministry of the Environment
    once: through its radicalism factors' funding lines, not also through its
    stance on the law in force (#1832; the owner's call, in the PR)."""

    def test_the_stance_is_neutral_and_the_ministry_still_rated_above_it(self):
        with open(os.path.join(REPO, "common", "ideologies", "extra_ideologies.txt"), encoding="utf-8-sig") as f:
            text = f.read()
        body = text[text.index("ideology_environmentalists = {"):]
        block = body[body.index("lawgroup_ministry_of_the_environment = {"):]
        block = block[:block.index("}")]
        self.assertRegex(block, r"law_no_ministry_of_the_environment = neutral")
        self.assertRegex(block, r"law_ministry_of_the_environment = strongly_approve")

    def test_the_funding_lines_stay(self):
        with open(os.path.join(REPO, "common", "political_movements", "new_ideological_movements.txt"),
                  encoding="utf-8-sig") as f:
            text = f.read()
        body = text[text.index("movement_environmental = {"):text.index("movement_civil_rights = {")]
        code = re.sub(r"#[^\n]*", "", body)
        self.assertIn('desc = "NO_INSTITUTION_ministry_of_the_environment"', code)
        self.assertIn('desc = "INSTITUTION_FUNDING_LEVEL_ministry_of_the_environment"', code)


if __name__ == "__main__":
    unittest.main()
