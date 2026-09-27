"""The nuclear taboo: the tables and single-writer rules that must agree.

The taboo (docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md) is one
world score moved by a monthly step and by writers scattered across the
nuclear files. Nothing in the engine checks that the parts the step snapshots
are the parts the target sums, that only the writers touch the score, or that
every path that gives an arsenal up books the renunciation once. Each test
pins one of those rules.

Run: python3 -m unittest test_nuclear_taboo -v
"""

import re
import sys
import unittest
from pathlib import Path

from test_nuclear_deterrence import block, read, strip_comments

ROOT = Path(__file__).resolve().parent
TABOO_VALUES = ROOT / "common/script_values/nuclear_taboo_values.txt"
TABOO_EFFECTS = ROOT / "common/scripted_effects/nuclear_taboo_effects.txt"
TABOO_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_taboo_triggers.txt"
TABOO_ON_ACTIONS = ROOT / "common/on_actions/nuclear_taboo_on_actions.txt"
WEAPON_EFFECTS = ROOT / "common/scripted_effects/nuclear_weapon_effects.txt"
JE = ROOT / "common/journal_entries/je_nuclear_program.txt"

# The target's parts, in the order nd_taboo_target_sum adds them.
PARTS = ["base", "tradition", "postures", "restraint", "ledger"]
NEW_FILES = [TABOO_VALUES, TABOO_EFFECTS, TABOO_TRIGGERS, TABOO_ON_ACTIONS]


def script_files():
    for folder in ("common", "events"):
        yield from (ROOT / folder).rglob("*.txt")


class TestScoreCore(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(TABOO_VALUES))
        self.effects = strip_comments(read(TABOO_EFFECTS))
        self.on_actions = strip_comments(read(TABOO_ON_ACTIONS))

    def test_new_files_start_with_a_bom(self):
        for path in NEW_FILES:
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), path.name)

    def test_snapshot_writes_every_part(self):
        body = block(self.effects, "nd_taboo_snapshot")
        for part in PARTS:
            self.assertIn(f"name = nd_tb_{part} value", body, part)
        self.assertIn("name = nd_taboo_target value = nd_taboo_target_sum", body)

    def test_target_sums_exactly_the_parts(self):
        body = block(self.values, "nd_taboo_target_sum")
        self.assertEqual(re.findall(r"(?:value|add) = global_var:nd_tb_(\w+)", body), PARTS)
        self.assertIn("min = 0", body)
        self.assertIn("max = 100", body)

    def test_drift_alone_tops_out_at_55(self):
        base = float(re.search(r"(?m)^nd_taboo_base = ([\d.]+)", self.values).group(1))
        cap = float(re.search(r"(?m)^nd_taboo_tradition_cap = ([\d.]+)", self.values).group(1))
        self.assertEqual(base + cap, 55)

    def test_only_the_writers_touch_the_score(self):
        writes = re.compile(r"name = (?:nd_taboo|nd_taboo_ledger|nd_taboo_quiet_years|nd_tb_\w+)\b"
                            r"(?= (?:value|add|subtract|multiply))")
        for path in script_files():
            if path == TABOO_EFFECTS:
                continue
            text = strip_comments(read(path))
            self.assertNotRegex(text, writes, path.relative_to(ROOT).as_posix())

    def test_every_writer_waits_for_the_birth(self):
        for name in ("nd_taboo_ledger_add", "nd_taboo_ledger_add_weighted", "nd_taboo_shock"):
            body = block(self.effects, name)
            self.assertIn("has_global_variable = nd_taboo", body, name)

    def test_world_step_runs_from_the_global_pulse_under_the_rule(self):
        pulse = block(self.on_actions, "on_monthly_pulse")
        self.assertIn("nd_taboo_monthly_on_action", pulse)
        body = block(self.on_actions, "nd_taboo_monthly_on_action")
        self.assertIn("has_game_rule = nuclear_weapons_enabled", body)
        self.assertIn("nd_taboo_monthly_update = yes", body)
        self.assertNotIn("un_founded", self.on_actions)

    def test_world_step_applies_no_rooted_modifier(self):
        body = block(self.effects, "nd_taboo_monthly_update")
        self.assertNotIn("add_modifier", body)
        self.assertNotIn("root.var", body)

    def test_birth_is_called_at_the_first_warhead(self):
        text = strip_comments(read(WEAPON_EFFECTS))
        i = text.index("set_global_variable = { name = world_first_nuclear_weapon value = yes }")
        self.assertIn("nd_taboo_birth = yes", text[i:i + 200])

    def test_existing_world_is_seeded_from_the_first_device(self):
        body = block(self.effects, "nd_taboo_seed_existing_world")
        self.assertIn("has_global_variable = world_first_nuclear_weapon", body)
        self.assertIn("world_first_nuclear_weapon_used", body)
        self.assertIn("var:nuclear_program_first_device_year", body)
        self.assertIn("name = nd_taboo value = global_var:nd_taboo_target", body)
        update = block(self.effects, "nd_taboo_monthly_update")
        self.assertLess(update.index("nd_taboo_seed_existing_world = yes"), update.index("nd_taboo_snapshot = yes"))

    def test_leaderboard_runs_once_for_the_world(self):
        self.assertNotIn("update_nuclear_powers_ranking", strip_comments(read(JE)))
        self.assertIn("update_nuclear_powers_ranking = yes", block(self.effects, "nd_taboo_monthly_update"))

    def test_new_loc_family_is_filed_whole(self):
        sys.path.insert(0, str(ROOT))
        import organize_loc
        for key in ("nd_taboo_possession_cost", "nd_taboo_possession_cost_desc",
                    "nd_taboo_resume_programme_desc", "nd_taboo_tt_opt_cut", "nd_taboo_bd_ledger"):
            self.assertEqual(organize_loc.categorize_key(key, set()), "MISCELLANEOUS", key)


if __name__ == "__main__":
    unittest.main()
