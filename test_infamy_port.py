"""The mod's infamy figures read vanilla 1.14+'s infamy values (#387).

Vanilla 1.14 moved war-goal infamy to world-share script values
(`state_infamy_value`, `country_infamy_value`). The mod's reunification goal
took vanilla's annex block in #600; Subjugate and the UN mandate goal's
fallback followed in #387. What this pins, none of which the engine would
report:

- no mod script reads the old population-scaling shape;
- Subjugate charges a fifth of the target's `country_infamy_value`, halved for
  a Sovereign Empire, capped at 25 (owner, 2026-11-12);
- the UN mandate goal charges nothing under a mandate and vanilla
  return_state's `state_infamy_value` without one.

No game install needed.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
SUBJUGATE = os.path.join(REPO, "common", "diplomatic_actions", "te_force_become_subject.txt")
MANDATE = os.path.join(REPO, "common", "war_goal_types", "te_un_mandate_restore_state.txt")


def _flat(path):
    with open(path, encoding="utf-8-sig") as fh:
        text = re.sub(r"#[^\n]*", "", fh.read())
    return re.sub(r"\s+", " ", text)


def _block(flat, start):
    """The balanced `{ ... }` that opens at the first `start` in `flat`."""
    i = flat.index(start)
    j = flat.index("{", i)
    depth = 0
    for k in range(j, len(flat)):
        depth += {"{": 1, "}": -1}.get(flat[k], 0)
        if depth == 0:
            return flat[j : k + 1]
    raise AssertionError(f"{start} is unbalanced")


class InfamyPortTests(unittest.TestCase):
    def test_no_mod_script_reads_the_old_population_shape(self):
        hits = []
        for top in ("common", "events"):
            for root, _dirs, files in os.walk(os.path.join(REPO, top)):
                for name in files:
                    if not name.endswith(".txt"):
                        continue
                    path = os.path.join(root, name)
                    if "WAR_GOAL_INFAMY_POPULATION_SCALING" in _flat(path):
                        hits.append(os.path.relpath(path, REPO))
        self.assertEqual(hits, [])

    def test_subjugate_charges_a_fifth_of_the_annexation_figure(self):
        charge = _block(_flat(SUBJUGATE), "change_infamy = {")
        self.assertIn("scope:target_country = { add = country_infamy_value }", charge)
        self.assertIn("multiply = 0.2", charge)
        self.assertRegex(
            charge,
            r"if = \{ limit = \{ modifier:power_bloc_leader_can_make_subjects_bool = yes \} "
            r"multiply = 0\.5 \}",
        )
        self.assertIn("min = 0 max = 25", charge)
        self.assertNotIn("total_population", charge)

    def test_the_mandate_goal_is_free_only_under_its_mandate(self):
        infamy = _block(_flat(MANDATE), "infamy = {")
        self.assertIn("if = { limit = { NOT = { un_mandate_covers_goal = yes } }", infamy)
        self.assertIn("scope:target_state = { add = state_infamy_value }", infamy)
        self.assertIn("WAR_GOAL_INFAMY_LOW_LIBERTY_DESIRE_SUBJECT_MULT", infamy)
        self.assertIn("WAR_GOAL_INFAMY_REBELLING_SUBJECT_MULT", infamy)
        self.assertNotIn("state_population", infamy)


if __name__ == "__main__":
    unittest.main()
