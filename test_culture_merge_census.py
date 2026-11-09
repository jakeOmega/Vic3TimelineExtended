"""Tests for the culture merges' yearly census and per-part gates.

Files under test:
* common/scripted_effects/te_culture_merge_effects.txt (hand-written census helpers)
* common/on_actions/te_culture_merge_on_actions.txt (the yearly pulse behind a lock)
* common/scripted_effects/te_culture_merges_generated_effects.txt and
  common/scripted_triggers/te_culture_merges_generated_triggers.txt
  (generated per merge by scripts/generators/gen_culture_merges.py)

The script can't be run offline, so the tests read its text: the shape of each
block, the order of its clauses, and that every call matches its callee.

Run: python3 -m unittest test_culture_merge_census -v
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import culture_merges_config as cfg  # noqa: E402
import gen_culture_merges as gen  # noqa: E402
import vanilla_parsed  # noqa: E402

EFFECTS = ROOT / "common/scripted_effects/te_culture_merge_effects.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_culture_merge_on_actions.txt"
GEN_EFFECTS = ROOT / "common/scripted_effects/te_culture_merges_generated_effects.txt"
GEN_TRIGGERS = ROOT / "common/scripted_triggers/te_culture_merges_generated_triggers.txt"
SCRIPT_FILES = (EFFECTS, ON_ACTIONS, GEN_EFFECTS, GEN_TRIGGERS)
# The core gap's figures the census keeps for the status row, te_cm_sol_<name>_<merge>.
SOL_SHOWN = ("best", "worst", "hi", "lo", "gap")
BOM = b"\xef\xbb\xbf"


def text_of(path):
    """A script file's text without the BOM and without comments."""
    raw = path.read_text(encoding="utf-8-sig")
    return "\n".join(line.split("#", 1)[0].rstrip() for line in raw.splitlines())


def block(text, name):
    """The body (between the braces) of the top-level `name = { ... }`, or None."""
    m = re.search(r"^" + re.escape(name) + r" = \{\n", text, re.M)
    if not m:
        return None
    depth = 1
    i = m.end()
    start = i
    while depth and i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    return text[start:i - 1]


def squash(text):
    return re.sub(r"\s+", " ", text).strip()


_VANILLA = None
_SNAPSHOT = None


def snapshot_data():
    """The committed vanilla snapshot's entity data, loaded once."""
    global _SNAPSHOT
    if _SNAPSHOT is None:
        _SNAPSHOT = vanilla_parsed.load(str(ROOT / "vanilla_parsed")).data
    return _SNAPSHOT


def vanilla():
    global _VANILLA
    if _VANILLA is None:
        data = snapshot_data()
        cultures = dict(data["Cultures"])
        cultures["__traits__"] = dict(data["Discrimination Traits"])
        _VANILLA = cultures
    return _VANILLA


def merge_index(merge):
    return 1 + [m.key for m in cfg.MERGES].index(merge.key)


def slot_cultures(merge):
    return [c for part in merge.core + merge.optional for c in part.cultures]


def tier_of(merge, culture):
    return cfg.derive_tier(merge, culture, vanilla(), cfg.MERGES)


def _absorb_result(merge, culture):
    return merge.new is None and culture == merge.result


class FilesTest(unittest.TestCase):
    def test_one_bom_and_tabs(self):
        for path in SCRIPT_FILES:
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(BOM), path.name)
            self.assertFalse(raw[3:].startswith(BOM), path.name + " has two BOMs")
            for line in raw.decode("utf-8-sig").splitlines():
                self.assertFalse(line.startswith(" "), path.name + ": " + line)

    def test_generated_files_carry_the_header(self):
        for path in (GEN_EFFECTS, GEN_TRIGGERS):
            self.assertEqual(path.read_text(encoding="utf-8-sig").splitlines()[0], gen.HEADER, path.name)

    def test_generated_files_are_current(self):
        self.assertFalse(gen.regenerate(dry_run=True)["changed"], "run python3 scripts/generators/gen_culture_merges.py")


class LockTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = text_of(ON_ACTIONS)

    def test_the_hook_runs_the_yearly_on_action(self):
        body = squash(block(self.text, "on_yearly_pulse_country"))
        self.assertIn("on_actions = { te_cm_yearly_on_action }", body)

    def test_census_is_locked(self):
        body = block(self.text, "te_cm_yearly_on_action")
        self.assertIsNotNone(body)
        flat = squash(body)
        self.assertRegex(flat, r"set_global_variable = \{ name = te_cm_census_lock value = yes days = 330 \}")
        guard = flat.index("NOT = { has_global_variable = te_cm_census_lock }")
        census = flat.index("te_cmg_census_all = yes")
        lock = flat.index("name = te_cm_census_lock")
        self.assertLess(guard, lock)
        self.assertLess(lock, census)

    def test_census_runs_once_per_calendar_year(self):
        # M1: a lock alone runs the census every 330 days (1.1 a year), so the counters that add one per
        # census would run ahead. The year it last ran is stored and a later year runs it again.
        flat = squash(block(self.text, "te_cm_yearly_on_action"))
        self.assertIn("set_local_variable = { name = te_cm_year value = year }", flat)
        self.assertIn(
            "OR = { NOT = { has_global_variable = te_cm_census_year } global_var:te_cm_census_year < local_var:te_cm_year }",
            flat,
        )
        self.assertIn("set_global_variable = { name = te_cm_census_year value = local_var:te_cm_year }", flat)
        # The year is read and compared before the census runs, and stored by the same branch.
        self.assertLess(flat.index("global_var:te_cm_census_year <"), flat.index("te_cmg_census_all = yes"))
        self.assertLess(flat.index("name = te_cm_census_year"), flat.index("te_cmg_census_all = yes"))
        self.assertNotIn("180 days", self.text)

    def test_the_whole_census_waits_for_the_rule(self):
        # R19: a rule switched off mid-game pauses the system. Nothing is recomputed,
        # and no variable is reset or removed.
        flat = squash(block(self.text, "te_cm_yearly_on_action"))
        gate = flat.index("te_cm_system_enabled = yes")
        self.assertLess(gate, flat.index("has_global_variable = te_cm_census_lock"))
        self.assertLess(gate, flat.index("te_cmg_census_all = yes"))
        self.assertEqual(flat.count("te_cmg_census_all = yes"), 1)
        # The outermost if's limit holds the gate and the lock test, and the census sits inside that if.
        m = re.match(r"effect = \{ if = \{ limit = \{ (.*?) \} set_local_variable", flat)
        self.assertIsNotNone(m)
        self.assertIn("te_cm_system_enabled = yes", m.group(1))
        self.assertIn("NOT = { has_global_variable = te_cm_census_lock }", m.group(1))
        self.assertNotIn("remove_variable", flat)
        self.assertNotIn("remove_global_variable", flat)


class CensusRunsOnlyWhenNeededTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = text_of(GEN_EFFECTS)
        cls.triggers = text_of(GEN_TRIGGERS)

    def test_every_merge_has_a_census_and_a_wanted_trigger(self):
        for merge in cfg.MERGES:
            self.assertIsNotNone(block(self.effects, "te_cmg_census_" + merge.key), merge.key)
            self.assertIsNotNone(block(self.effects, "te_cmg_census_%s_country" % merge.key), merge.key)
            self.assertIsNotNone(block(self.triggers, "te_cmg_%s_census_wanted" % merge.key), merge.key)

    def test_each_merge_is_censused_once_under_its_wanted_trigger(self):
        census_all = squash(block(self.effects, "te_cmg_census_all"))
        for merge in cfg.MERGES:
            call = "te_cmg_census_%s = yes" % merge.key
            self.assertEqual(census_all.count(call), 1, merge.key)
            self.assertIn(
                "if = { limit = { te_cmg_%s_census_wanted = yes } %s }" % (merge.key, call), census_all, merge.key
            )

    def test_census_runs_only_when_needed(self):
        # Every te_cmg_census_<m> call sits under te_cmg_<m>_census_wanted, which is true only for an idle
        # merge with a candidate or a running or complete one with its starter.
        census_all = squash(block(self.effects, "te_cmg_census_all"))
        for merge in cfg.MERGES:
            body = squash(block(self.triggers, "te_cmg_%s_census_wanted" % merge.key))
            key = merge.key
            self.assertIn(
                "if = { limit = { te_cmg_%s_census_wanted = yes } te_cmg_census_%s = yes }" % (key, key), census_all, key
            )
            idle = "NOR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 } " % (key, key)
            self.assertIn(idle + "any_country = { te_cmg_%s_is_candidate = yes }" % key, body, key)
            running = "OR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 } " % (key, key)
            self.assertIn(running + "exists = global_var:te_cm_starter_%s" % key, body, key)
            # A trigger, and no any_* takes a limit; a trigger_if's guards the starter read (the entries' tooltip test).
            self.assertNotIn("limit", body.replace("trigger_if = { limit = ", "trigger_if = { "), key)

    def test_a_running_or_complete_merge_needs_a_slot_culture_still_to_convert(self):
        # Neither switched nor absent from the world; an absorb merge's result never switches.
        for merge in cfg.MERGES:
            body = squash(block(self.triggers, "te_cmg_%s_census_wanted" % merge.key))
            for culture in slot_cultures(merge):
                live = (
                    "NOT = { has_global_variable = te_cm_switched_%s } "
                    "any_country = { culture_percent_country = { target = cu:%s value > 0 } }" % (culture, culture)
                )
                if merge.new is None and culture == merge.result:
                    self.assertNotIn("cu:%s " % culture, body, merge.key)
                else:
                    self.assertIn(live, body, "%s %s" % (merge.key, culture))

    def test_the_idle_branch_walks_candidates_and_the_other_only_the_starter(self):
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_" + merge.key))
            key = merge.key
            self.assertIn(
                "if = { limit = { NOR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 } } "
                "every_country = { limit = { te_cmg_%s_is_candidate = yes } te_cmg_census_%s_country = yes } }"
                % (key, key, key, key),
                body,
                key,
            )
            self.assertIn(
                "else_if = { limit = { exists = global_var:te_cm_starter_%s } "
                "global_var:te_cm_starter_%s = { te_cmg_census_%s_country = yes } }" % (key, key, key),
                body,
                key,
            )

    def test_every_culture_is_measured_once_under_the_merges_that_want_it(self):
        census_all = squash(block(self.effects, "te_cmg_census_all"))
        wanting = {}
        for merge in cfg.MERGES:
            for culture in slot_cultures(merge):
                wanting.setdefault(culture, []).append(merge)
        for culture, merges in wanting.items():
            plain = "te_cm_census_culture = { CULTURE = %s }" % culture
            self.assertEqual(census_all.count(plain), 1, culture)
            conds = ["te_cmg_%s_census_wanted = yes" % m.key for m in merges]
            wanted = conds[0] if len(conds) == 1 else "OR = { %s }" % " ".join(conds)
            # R21: a switched culture is not measured again.
            head = "if = { limit = { NOT = { has_global_variable = te_cm_switched_%s } %s }" % (culture, wanted)
            self.assertIn(head, census_all, culture)
        # Measured before any merge's census reads it.
        self.assertLess(census_all.rindex("te_cm_census_culture"), census_all.index("te_cmg_census_"))

    def test_a_joined_part_is_walked_with_its_merges_result(self):
        # R22: one walk per culture; a culture that joined a merge is walked together with that
        # merge's result, so te_cm_home_r_<c> is there for the hold and for Task 6's dominance.
        census_all = squash(block(self.effects, "te_cmg_census_all"))
        for merge in cfg.MERGES:
            for culture in slot_cultures(merge):
                joined = (
                    "limit = { global_var:te_cm_joined_%s_%s ?= 1 } "
                    "te_cm_census_culture_joined = { CULTURE = %s RESULT = %s }" % (merge.key, culture, culture, merge.result)
                )
                if _absorb_result(merge, culture):
                    self.assertNotIn("global_var:te_cm_joined_%s_%s" % (merge.key, culture), census_all)
                else:
                    self.assertEqual(census_all.count(joined), 1, "%s %s" % (merge.key, culture))
        # Every culture has exactly one plain walk, as the last branch; the joined walks come before it.
        for culture in {c for m in cfg.MERGES for c in slot_cultures(m)}:
            plain = census_all.index("te_cm_census_culture = { CULTURE = %s }" % culture)
            first_joined = census_all.find("te_cm_census_culture_joined = { CULTURE = %s " % culture)
            if first_joined != -1:
                self.assertLess(first_joined, plain, culture)
        self.assertIn(
            "if = { limit = { global_var:te_cm_joined_american_yankee ?= 1 } te_cm_census_culture_joined = { CULTURE = yankee RESULT = cm_american } } "
            "else_if = { limit = { global_var:te_cm_joined_anglophone_yankee ?= 1 } te_cm_census_culture_joined = { CULTURE = yankee RESULT = cm_anglophone } } "
            "else = { te_cm_census_culture = { CULTURE = yankee } }",
            census_all,
        )

    def test_a_switched_part_is_not_censused(self):
        # R21: its pops are the result's now, so held would read 0 and stall the merge for good.
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            for culture in slot_cultures(merge):
                call = "te_cm_census_part = { MERGE = %s CULTURE = %s RESULT = %s TIER = %d }" % (
                    merge.key, culture, merge.result, tier_of(merge, culture)
                )
                self.assertIn(
                    "if = { limit = { NOT = { has_global_variable = te_cm_switched_%s } } %s }" % (culture, call),
                    body, call,
                )


class CensusHelpersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = text_of(EFFECTS)

    def test_census_walks_homeland_states(self):
        body = block(self.text, "te_cm_census_culture")
        self.assertIsNotNone(body)
        self.assertIn("every_scope_homeland_state", body)
        self.assertIn("cu:$CULTURE$ = {", body)
        # The world fallback visits only countries that hold the culture.
        fallback = body[body.index("every_country"):]
        self.assertIn("culture_percent_country = { target = cu:$CULTURE$ value > 0 }", fallback)
        self.assertLess(fallback.index("culture_percent_country"), fallback.index("every_scope_pop"))
        self.assertIn("set_global_variable = { name = te_cm_home_$CULTURE$", body)

    def test_the_sphere_is_measured_against_the_candidate(self):
        body = block(self.text, "te_cm_census_part")
        self.assertIsNotNone(body)
        save = body.index("save_temporary_scope_as = te_cm_starter")
        self.assertLess(save, body.index("te_cm_in_sphere"))
        self.assertEqual(body.count("save_temporary_scope_as"), 1)
        self.assertNotIn("save_scope_as", body.replace("save_temporary_scope_as", ""))

    def test_census_part_counts_homeland_pops_of_the_sphere_only(self):
        body = squash(block(self.text, "te_cm_census_part"))
        self.assertIn("every_scope_homeland_state", body)
        self.assertIn("owner = { te_cm_in_sphere = yes }", body)
        # The same fallback as the culture's total, so the share is over one pop set.
        self.assertIn("culture_percent_country = { target = cu:$CULTURE$ value > 0 }", body)
        self.assertEqual(body.count("te_cm_cp_sum_pops = { CULTURE = $CULTURE$ RESULT = $RESULT$ }"), 2)
        sums = squash(block(self.text, "te_cm_cp_sum_pops"))
        self.assertIn("limit = { culture = cu:$CULTURE$ }", sums)
        self.assertIn("value = standard_of_living multiply = total_size", sums)

    def test_a_joined_part_holds_part_plus_result_on_both_sides(self):
        # R22: the sphere's part + result over the world's part + result in the part's homeland states.
        sums = squash(block(self.text, "te_cm_cp_sum_pops"))
        self.assertIn("if = { limit = { local_var:te_cm_cp_joined = 1 } every_scope_pop = { limit = { culture = cu:$RESULT$ }", sums)
        body = squash(block(self.text, "te_cm_census_part"))
        self.assertIn(
            "if = { limit = { global_var:te_cm_joined_$MERGE$_$CULTURE$ ?= 1 } set_local_variable = { name = te_cm_cp_joined value = 1 } }",
            body,
        )
        self.assertIn("set_local_variable = { name = te_cm_cp_denom value = global_var:te_cm_home_$CULTURE$ }", body)
        self.assertIn(
            "local_var:te_cm_cp_joined = 1 has_global_variable = te_cm_home_r_$CULTURE$ } "
            "change_local_variable = { name = te_cm_cp_denom add = global_var:te_cm_home_r_$CULTURE$ }",
            body,
        )
        self.assertIn("value = local_var:te_cm_cp_pops divide = local_var:te_cm_cp_denom max = 1", body)
        # The acceptance test counts holders by the part's own pops, and the hold by both.
        self.assertIn("change_local_variable = { name = te_cm_cp_pops add = local_var:te_cm_cp_state_res }", sums)
        self.assertIn("change_local_variable = { name = te_cm_cp_part_pops add = local_var:te_cm_cp_state_pops }", sums)
        self.assertNotIn("state_res", squash(block(self.text, "te_cm_cp_note_holder")))

    def test_the_joined_census_stores_the_results_pops_in_the_same_walk(self):
        body = squash(block(self.text, "te_cm_census_culture_joined"))
        self.assertEqual(body.count("every_scope_homeland_state"), 1)
        self.assertIn("limit = { culture = cu:$RESULT$ } change_local_variable = { name = te_cm_cc_res add = total_size }", body)
        self.assertIn("set_global_variable = { name = te_cm_home_$CULTURE$ value = local_var:te_cm_cc_sum }", body)
        self.assertIn("set_global_variable = { name = te_cm_home_r_$CULTURE$ value = local_var:te_cm_cc_res }", body)
        fallback = body[body.index("every_country"):]
        self.assertLess(fallback.index("culture_percent_country"), fallback.index("every_scope_pop"))
        # What the two homes mean is written where the next reader looks.
        raw = EFFECTS.read_text(encoding="utf-8-sig")
        self.assertIn("te_cm_home_r_<c>", raw)
        self.assertIn("part + result", raw)
        self.assertIn("pops that remain", raw)

    def test_acceptance_tests_the_largest_holder_as_well_as_every_meaningful_one(self):
        # M3: with the sphere's holdings split thin no country reaches the meaningful share, and the test
        # would pass vacuously; the cut-off is capped at the largest holding.
        body = squash(block(self.text, "te_cm_census_part"))
        self.assertIn(
            "value = local_var:te_cm_cp_part_pops multiply = te_cm_meaningful_share } } "
            "if = { limit = { local_var:te_cm_cp_min_cnt > local_var:te_cm_cp_max_cnt } "
            "set_local_variable = { name = te_cm_cp_min_cnt value = local_var:te_cm_cp_max_cnt } }",
            body,
        )
        self.assertIn("var:te_cm_tmp_cnt >= local_var:te_cm_cp_min_cnt", body)
        holder = squash(block(self.text, "te_cm_cp_note_holder"))
        self.assertIn("limit = { var:te_cm_tmp_cnt > local_var:te_cm_cp_max_cnt } set_local_variable = { name = te_cm_cp_max_cnt value = var:te_cm_tmp_cnt }", holder)
        self.assertIn("set_local_variable = { name = te_cm_cp_max_cnt value = 0 }", body)

    def test_gates_have_hysteresis_and_use_the_named_values(self):
        body = squash(block(self.text, "te_cm_census_part"))
        for name in (
            "te_cm_hold_open", "te_cm_hold_close", "te_cm_accept_open", "te_cm_accept_close",
            "te_cm_accept_high_open", "te_cm_accept_high_close", "te_cm_meaningful_share",
        ):
            self.assertIn(name, body, name)
        # The open branch pairs the open hold with the open failures, the close branch the close pair.
        self.assertIn(
            "if = { limit = { var:te_cm_ok_$MERGE$_$CULTURE$ = 1 } "
            "if = { limit = { OR = { var:te_cm_held_$MERGE$_$CULTURE$ < te_cm_hold_close local_var:te_cm_cp_fail_close > 0 } } "
            "set_variable = { name = te_cm_ok_$MERGE$_$CULTURE$ value = 0 } } } "
            "else = { if = { limit = { var:te_cm_held_$MERGE$_$CULTURE$ >= te_cm_hold_open local_var:te_cm_cp_fail_open = 0 } "
            "set_variable = { name = te_cm_ok_$MERGE$_$CULTURE$ value = 1 } } }",
            body,
        )
        # Each counter counts the failures of its own threshold, nothing else.
        pairs = {
            "te_cm_cp_fail_open": "te_cm_accept_open",
            "te_cm_cp_fail_close": "te_cm_accept_close",
            "te_cm_cp_fail_high_open": "te_cm_accept_high_open",
            "te_cm_cp_fail_high_close": "te_cm_accept_high_close",
        }
        for counter, threshold in pairs.items():
            self.assertIn(
                "if = { limit = { country_average_culture_pop_acceptance = { culture = cu:$CULTURE$ value < %s } } "
                "change_local_variable = { name = %s add = 1 } }" % (threshold, counter),
                body, counter,
            )
        found = re.findall(r"country_average_culture_pop_acceptance = \{ culture = cu:\$CULTURE\$ value < (\S+) \}", body)
        self.assertEqual(sorted(found), sorted(pairs.values()))
        # Tier 2 (the spec's 1b) swaps in the very high pair, open for open and close for close.
        self.assertIn(
            "if = { limit = { local_var:te_cm_cp_tier = 2 } "
            "set_local_variable = { name = te_cm_cp_fail_open value = local_var:te_cm_cp_fail_high_open } "
            "set_local_variable = { name = te_cm_cp_fail_close value = local_var:te_cm_cp_fail_high_close } }",
            body,
        )

    def test_tier_2_counts_years_and_nothing_else_touches_the_counter(self):
        body = squash(block(self.text, "te_cm_census_part"))
        self.assertIn("set_local_variable = { name = te_cm_cp_tier value = $TIER$ }", body)
        self.assertIn("local_var:te_cm_cp_tier = 2", body)
        years = body[body.index("local_var:te_cm_cp_tier > 1"):]
        self.assertIn("change_variable = { name = te_cm_years_$MERGE$_$CULTURE$ add = 1 }", years)
        # M6: every write to the counter in the whole helper: a first value of 0 only where it is unset,
        # then an add of 1, and never a reset, a subtraction or a removal.
        writes = re.findall(r"(\w+_variable) = \{ name = te_cm_years_\$MERGE\$_\$CULTURE\$ ([^}]*)\}", body)
        self.assertEqual(sorted(writes), [("change_variable", "add = 1 "), ("set_variable", "value = 0 ")])
        init = body.index("set_variable = { name = te_cm_years_$MERGE$_$CULTURE$ value = 0 }")
        self.assertEqual(
            body[init - len("limit = { NOT = { has_variable = te_cm_years_$MERGE$_$CULTURE$ } } "):init].strip(),
            "limit = { NOT = { has_variable = te_cm_years_$MERGE$_$CULTURE$ } }",
        )
        self.assertNotIn("remove_variable = te_cm_years", body)

    def test_the_temporary_holder_variable_is_removed_in_the_same_call(self):
        body = squash(block(self.text, "te_cm_census_part"))
        self.assertIn("every_country = { limit = { has_variable = te_cm_tmp_cnt }", body)
        self.assertIn("remove_variable = te_cm_tmp_cnt", body)
        # It is written only through the helper census_part calls, and read before it is removed.
        self.assertLess(body.index("var:te_cm_tmp_cnt >="), body.index("remove_variable = te_cm_tmp_cnt"))
        self.assertGreater(body.index("remove_variable = te_cm_tmp_cnt"), body.rindex("te_cm_cp_note_holder"))

    def test_division_is_guarded(self):
        body = squash(block(self.text, "te_cm_census_part"))
        self.assertIn("limit = { local_var:te_cm_cp_denom > 0 }", body)
        self.assertIn("limit = { local_var:te_cm_cp_pops >= 1 }", body)

    def test_dispatch_helpers_name_every_argument(self):
        # Every helper that is called with arguments names each one in its body.
        for name, args in (
            ("te_cm_census_culture", ("CULTURE",)),
            ("te_cm_census_culture_joined", ("CULTURE", "RESULT")),
            ("te_cm_census_part", ("MERGE", "CULTURE", "RESULT", "TIER")),
            ("te_cm_cp_sum_pops", ("CULTURE", "RESULT")),
            ("te_cm_sol_track", ("MERGE", "CULTURE")),
            ("te_cm_sol_gate_part", ("MERGE", "CULTURE")),
        ):
            body = block(self.text, name)
            self.assertIsNotNone(body, name)
            for arg in args:
                self.assertIn("$%s$" % arg, body, name + " " + arg)


class SolGateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = text_of(GEN_EFFECTS)
        cls.helpers = text_of(EFFECTS)

    def test_sol_gate_has_hysteresis(self):
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            key = merge.key
            self.assertIn("te_cm_sol_gap_close", body, key)
            self.assertIn("te_cm_sol_gap_open", body, key)
            # Once open, it closes only above the looser value; otherwise it opens only below the stricter,
            # and only while every core slot is met (M2).
            self.assertIn(
                "if = { limit = { var:te_cm_sol_ok_%s = 1 } if = { limit = { local_var:te_cm_sg_gap > te_cm_sol_gap_close } "
                "set_variable = { name = te_cm_sol_ok_%s value = 0 } } }" % (key, key),
                body, key,
            )
            self.assertIn(
                "else = { if = { limit = { local_var:te_cm_sg_gap < te_cm_sol_gap_open local_var:te_cm_sg_all = 1 } "
                "set_variable = { name = te_cm_sol_ok_%s value = 1 } } }" % key,
                body, key,
            )

    def test_the_merge_wide_gap_is_over_core_cultures_that_pass_their_gates(self):
        # R23: the optional parts have gates of their own, so no optional part is in the merge-wide gap.
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            optional = {c for part in merge.optional for c in part.cultures}
            for culture in slot_cultures(merge):
                track = "te_cm_sol_track = { MERGE = %s CULTURE = %s }" % (merge.key, culture)
                if culture in optional:
                    self.assertNotIn(track, body, culture)
                    continue
                self.assertEqual(body.count(track), 1, culture)
                self.assertIn("if = { limit = { te_cmg_%s_%s_measured = yes } %s }" % (merge.key, culture, track), body)
            # A joined part isn't a condition of the merge-wide gap, and (I2) not of the result walk's "needed"
            # limit either: that one asks only whether an optional part has switched, joined or not.
            self.assertEqual(body.count("te_cm_joined"), 0, merge.key)

    def test_the_merge_wide_gate_opens_only_when_every_core_slot_is_met(self):
        # M2: a slot is met when one of its alternatives has a figure, or joined and switched. The gate
        # opens only if all of them are.
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            self.assertIn("if = { limit = { local_var:te_cm_sg_slots = %d } set_local_variable = { name = te_cm_sg_all value = 1 } }" % len(merge.core), body)
            self.assertEqual(body.count("change_local_variable = { name = te_cm_sg_slots add = 1 }"), len(merge.core))
            for part in merge.core:
                met = ["te_cmg_%s_%s_measured = yes" % (merge.key, c) for c in part.cultures]
                met += ["te_cmg_%s_%s_switched_in = yes" % (merge.key, c) for c in part.cultures if not _absorb_result(merge, c)]
                limit = met[0] if len(met) == 1 else "OR = { %s }" % " ".join(met)
                self.assertIn(
                    "if = { limit = { %s } change_local_variable = { name = te_cm_sg_slots add = 1 } }" % limit, body, merge.key
                )

    def test_each_optional_part_has_a_gate_of_its_own(self):
        # R23: the gap over the core cultures plus this part, open below te_cm_sol_gap_open, closed above
        # te_cm_sol_gap_close. Skipped once the part has switched.
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            optional = [c for part in merge.optional for c in part.cultures]
            for culture in optional:
                self.assertIn(
                    "if = { limit = { NOT = { has_global_variable = te_cm_switched_%s } } "
                    "te_cm_sol_gate_part = { MERGE = %s CULTURE = %s } }" % (culture, merge.key, culture),
                    body, culture,
                )
            self.assertEqual(body.count("te_cm_sol_gate_part"), len(optional), merge.key)
            # After the merge-wide gate, which has built the core range they read.
            if optional:
                self.assertGreater(body.index("te_cm_sol_gate_part"), body.index("te_cm_sol_gap_open"))
        gate = squash(block(self.helpers, "te_cm_sol_gate_part"))
        self.assertIn("limit = { local_var:te_cm_sg_all = 1 var:te_cm_ok_$MERGE$_$CULTURE$ = 1 }", gate)
        self.assertIn("set_local_variable = { name = te_cm_sg_lo value = local_var:te_cm_sg_min }", gate)
        self.assertIn("limit = { var:te_cm_sol_$MERGE$_$CULTURE$ < local_var:te_cm_sg_lo }", gate)
        self.assertIn("limit = { var:te_cm_sol_$MERGE$_$CULTURE$ > local_var:te_cm_sg_hi }", gate)
        # One hysteresis for both references: closed above te_cm_sol_gap_close, reopened below te_cm_sol_gap_open.
        self.assertIn(
            "if = { limit = { local_var:te_cm_sg_known = 1 } "
            "if = { limit = { var:te_cm_sol_ok_$MERGE$_$CULTURE$ = 1 } "
            "if = { limit = { local_var:te_cm_sg_gap > te_cm_sol_gap_close } "
            "set_variable = { name = te_cm_sol_ok_$MERGE$_$CULTURE$ value = 0 } } } "
            "else = { if = { limit = { local_var:te_cm_sg_gap < te_cm_sol_gap_open } "
            "set_variable = { name = te_cm_sol_ok_$MERGE$_$CULTURE$ value = 1 } } } }",
            gate,
        )

    def test_with_no_core_figure_left_a_part_is_held_against_the_result(self):
        # R26: once every core part has switched, the optional part is compared with the result culture's
        # pop-weighted SoL, |part - result|; a merge with core figures keeps using their range.
        gate = squash(block(self.helpers, "te_cm_sol_gate_part"))
        core = gate.index("if = { limit = { local_var:te_cm_sg_n > 0 }")
        result = gate.index("else_if = { limit = { local_var:te_cm_sg_ref > 0 }")
        self.assertLess(core, result)
        branch = gate[result:gate.index("if = { limit = { local_var:te_cm_sg_known = 1 }")]
        # The absolute difference, from whichever side is larger.
        self.assertIn(
            "if = { limit = { var:te_cm_sol_$MERGE$_$CULTURE$ >= local_var:te_cm_sg_ref } "
            "set_local_variable = { name = te_cm_sg_gap value = var:te_cm_sol_$MERGE$_$CULTURE$ } "
            "change_local_variable = { name = te_cm_sg_gap subtract = local_var:te_cm_sg_ref } } "
            "else = { set_local_variable = { name = te_cm_sg_gap value = local_var:te_cm_sg_ref } "
            "change_local_variable = { name = te_cm_sg_gap subtract = var:te_cm_sol_$MERGE$_$CULTURE$ } }",
            branch,
        )
        # No reference figure either: the gate is left as it was (known stays 0).
        self.assertEqual(gate.count("set_local_variable = { name = te_cm_sg_known value = 1 }"), 2)
        self.assertIn("set_local_variable = { name = te_cm_sg_known value = 0 }", gate)

    def test_the_result_walk_sits_under_its_needed_limit(self):
        # R26: walk only while it is needed: no measured core figure, every core slot met, and some optional
        # part neither joined nor switched. A merge with no optional part never walks.
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            optional = [c for part in merge.optional for c in part.cultures]
            call = "te_cmg_%s_result_sol = yes" % merge.key
            if not optional:
                self.assertNotIn("result_sol", body, merge.key)
                self.assertIsNone(block(self.effects, "te_cmg_%s_result_sol" % merge.key), merge.key)
                continue
            self.assertEqual(body.count(call), 1, merge.key)
            # I2: while any optional part has not switched, joined or not. A part that has joined keeps
            # following the result, or one dip in the hold would freeze its gate at 0 for good. R38 M1: and only
            # for a part whose own gates are on, the only case te_cm_sol_gate_part reads the figure.
            needed = " ".join(
                "AND = { NOT = { has_global_variable = te_cm_switched_%s } var:te_cm_ok_%s_%s ?= 1 }" % (c, merge.key, c)
                for c in optional
            )
            self.assertIn(
                "set_local_variable = { name = te_cm_sg_ref value = 0 } "
                "if = { limit = { local_var:te_cm_sg_n = 0 local_var:te_cm_sg_all = 1 OR = { %s } } %s }" % (needed, call),
                body, merge.key,
            )
            # Before the optional gates read the reference.
            self.assertLess(body.index(call), body.index("te_cm_sol_gate_part"))

    def test_the_result_reference_is_the_results_sol_in_the_cores_homeland_states_in_the_sphere(self):
        for merge in cfg.MERGES:
            optional = [c for part in merge.optional for c in part.cultures]
            if not optional:
                continue
            body = squash(block(self.effects, "te_cmg_%s_result_sol" % merge.key))
            homelands = " ".join("state_region = { is_homeland = cu:%s }" % c for part in merge.core for c in part.cultures)
            self.assertTrue(body.startswith("save_temporary_scope_as = te_cm_starter"), merge.key)
            self.assertIn(
                "every_country = { limit = { te_cm_in_sphere = yes } every_scope_state = { limit = { OR = { %s } } "
                "every_scope_pop = { limit = { culture = cu:%s } " % (homelands, merge.result),
                body, merge.key,
            )
            self.assertIn("value = standard_of_living multiply = total_size", body)
            self.assertIn("limit = { local_var:te_cm_sg_rpops >= 1 }", body)
            self.assertIn("divide = local_var:te_cm_sg_rpops", body)
        self.assertIn(
            "culture = cu:cm_german", squash(block(self.effects, "te_cmg_german_result_sol"))
        )

    def test_no_slot_qualifying_leaves_the_gate_as_it_was(self):
        body = squash(block(self.effects, "te_cmg_census_german_country"))
        self.assertIn("if = { limit = { local_var:te_cm_sg_n > 0 }", body)

    def test_the_gap_and_its_two_ends_are_kept_for_the_status_row(self):
        # The status row names the best- and worst-off core cultures, their figures and the gap (2026-11-09), so the
        # census keeps what the gate read, and takes it away once no core part has a figure.
        track = squash(block(self.helpers, "te_cm_sol_track"))
        self.assertIn(
            "limit = { var:te_cm_sol_$MERGE$_$CULTURE$ < local_var:te_cm_sg_min } "
            "set_local_variable = { name = te_cm_sg_min value = var:te_cm_sol_$MERGE$_$CULTURE$ } "
            "set_local_variable = { name = te_cm_sg_worst value = cu:$CULTURE$ }", track,
        )
        self.assertIn(
            "limit = { var:te_cm_sol_$MERGE$_$CULTURE$ > local_var:te_cm_sg_max } "
            "set_local_variable = { name = te_cm_sg_max value = var:te_cm_sol_$MERGE$_$CULTURE$ } "
            "set_local_variable = { name = te_cm_sg_best value = cu:$CULTURE$ }", track,
        )
        for merge in cfg.MERGES:
            key = merge.key
            body = squash(block(self.effects, "te_cmg_census_%s_country" % key))
            kept = " ".join(
                "set_variable = { name = te_cm_sol_%s_%s value = local_var:%s }" % (name, key, local)
                for name, local in zip(SOL_SHOWN, ("te_cm_sg_best", "te_cm_sg_worst", "te_cm_sg_max", "te_cm_sg_min", "te_cm_sg_gap"))
            )
            self.assertIn(
                "if = { limit = { local_var:te_cm_sg_n > 0 } set_local_variable = { name = te_cm_sg_gap value = local_var:te_cm_sg_max } "
                "change_local_variable = { name = te_cm_sg_gap subtract = local_var:te_cm_sg_min } %s " % kept,
                body, key,
            )
            self.assertIn("else = { %s }" % " ".join("remove_variable = te_cm_sol_%s_%s" % (n, key) for n in SOL_SHOWN), body, key)

    def test_every_part_is_censused_at_its_own_tier(self):
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            for culture in slot_cultures(merge):
                call = "te_cm_census_part = { MERGE = %s CULTURE = %s RESULT = %s TIER = %d }" % (
                    merge.key, culture, merge.result, tier_of(merge, culture)
                )
                self.assertEqual(body.count(call), 1, call)


class TriggerShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = text_of(GEN_TRIGGERS)

    def trig(self, name):
        body = block(self.triggers, name)
        self.assertIsNotNone(body, name)
        return squash(body)

    def test_german_candidate(self):
        body = self.trig("te_cmg_german_is_candidate")
        self.assertEqual(
            body,
            "te_cm_system_enabled = yes "
            "exists = cu:cm_german "
            "OR = { country_has_primary_culture = cu:north_german country_has_primary_culture = cu:south_german } "
            "te_cm_tier_tech = { TIER = 1 } "
            "NOT = { global_var:te_cm_state_german ?= 2 }",
        )
        # A new result culture must exist: a game begun before it was added has none (2026-11-08). An absorbing merge's
        # result is a vanilla culture, so it isn't asked.
        self.assertNotIn("exists = cu:", self.trig("te_cmg_hungarian_is_candidate"))
        # A result that is a part of another merge also asks that it has not switched into it (R33, R36), through the
        # one generated trigger that says so (M6).
        self.assertIn("NOT = { te_cmg_italian_result_switched = yes }", self.trig("te_cmg_italian_is_candidate"))
        self.assertIn("NOT = { te_cmg_french_result_switched = yes }", self.trig("te_cmg_french_is_candidate"))
        self.assertEqual(self.trig("te_cmg_italian_result_switched"), "has_global_variable = te_cm_switched_cm_italian")
        self.assertNotIn("result_switched", self.trig("te_cmg_hungarian_is_candidate"))
        # R38 M2: a merge whose core part another merge can take asks that it has not switched there.
        self.assertIn("te_cmg_american_core_left = yes", self.trig("te_cmg_american_is_candidate"))
        self.assertEqual(
            self.trig("te_cmg_american_core_left"),
            "OR = { NOT = { has_global_variable = te_cm_switched_yankee } global_var:te_cm_joined_american_yankee ?= 1 } "
            "OR = { NOT = { has_global_variable = te_cm_switched_dixie } global_var:te_cm_joined_american_dixie ?= 1 }",
        )
        self.assertNotIn("core_left", self.trig("te_cmg_german_is_candidate"))

    def test_candidate_needs_the_tech_of_the_highest_core_tier(self):
        for merge in cfg.MERGES:
            tier = gen.start_tier(merge, vanilla(), cfg.MERGES)
            body = self.trig("te_cmg_%s_is_candidate" % merge.key)
            self.assertIn("te_cm_tier_tech = { TIER = %d }" % tier, body, merge.key)
            self.assertTrue(body.startswith("te_cm_system_enabled = yes"), merge.key)
            for part in merge.core:
                for culture in part.cultures:
                    self.assertIn("country_has_primary_culture = cu:%s" % culture, body, culture)
            self.assertNotIn("optional", body)
        self.assertIn("TIER = 2", self.trig("te_cmg_anglophone_is_candidate"))

    def test_a_skipped_dlc_is_not_a_candidate(self):
        body = self.trig("te_cmg_brazilian_is_candidate")
        self.assertIn("NOT = { has_dlc_feature = rp1_content }", body)
        for merge in cfg.MERGES:
            if merge.skip_if_dlc is None:
                self.assertNotIn("has_dlc_feature", self.trig("te_cmg_%s_is_candidate" % merge.key))

    def test_state_and_variables_are_read_with_the_unset_safe_form(self):
        # A comparison against an unset variable logs an error under a tooltip; ?= is false instead.
        text = self.triggers
        for m in re.finditer(r"(global_var|var):(te_cm_(?:state|ok|sol_ok|joined|in)\w*) *([<>=]+) ", text):
            self.assertEqual(m.group(3), "?=", m.group(0))

    def test_core_ok_wants_every_core_slot_met_through_an_alternative(self):
        # R21 + R24: a slot is met by an alternative that passes its gates now (and, at tier 1b or 2, has its
        # years), or by one that joined this merge and has switched.
        for merge in cfg.MERGES:
            body = self.trig("te_cmg_%s_core_ok" % merge.key)
            key = merge.key
            start = max(tier_of(merge, p.cultures[0]) for p in merge.core)
            for part in merge.core:
                routes = []
                for c in part.cultures:
                    route = ["te_cmg_%s_%s_measured = yes" % (key, c)]
                    if tier_of(merge, c) != start:  # R31: a part of another tier than the start takes its own technology
                        route.append("te_cm_tier_tech = { TIER = %d }" % tier_of(merge, c))
                    if tier_of(merge, c) > 1:
                        route.append("te_cmg_%s_%s_years_met = yes" % (key, c))
                    routes.append(route)
                    if not _absorb_result(merge, c):
                        routes.append(["te_cmg_%s_%s_switched_in = yes" % (key, c)])
                if len(routes) == 1:
                    self.assertIn(" ".join(routes[0]), body, key)
                else:
                    text = " ".join(r[0] if len(r) == 1 else "AND = { %s }" % " ".join(r) for r in routes)
                    self.assertIn("OR = { %s }" % text, body, key)
            for part in merge.optional:
                for c in part.cultures:
                    self.assertNotIn("_%s_" % c, body.replace("te_cmg_%s_" % key, ""), "optional parts don't gate the start")

    def test_a_switched_part_still_meets_its_slot(self):
        # R21: once north_german has switched, nothing measures it, so the merge reads it as met for good.
        self.assertIn("te_cmg_german_north_german_switched_in = yes", self.trig("te_cmg_german_core_ok"))
        body = self.trig("te_cmg_german_north_german_switched_in")
        self.assertEqual(body, "global_var:te_cm_joined_german_north_german ?= 1 has_global_variable = te_cm_switched_north_german")
        self.assertEqual(
            self.trig("te_cmg_german_north_german_measured"),
            "var:te_cm_ok_german_north_german ?= 1 te_cmg_german_north_german_available = yes "
            "NOT = { has_global_variable = te_cm_switched_north_german }",
        )
        # An absorb merge's result is never joined or switched, so it has no such route.
        self.assertNotIn("te_cmg_hungarian_hungarian_switched_in", self.triggers)
        self.assertNotIn("switched_in = yes", self.trig("te_cmg_hungarian_core_ok").split("szekely")[0])

    def test_the_start_wants_the_years_of_a_tier_2_and_3_alternative(self):
        # R24: core_ok asks for the counter can_join writes: 1b at te_cm_years_tier2, tier 2 at te_cm_years_tier3.
        pan_slavic = self.trig("te_cmg_pan_slavic_core_ok")
        for c in ("cm_east_slavic", "cm_czechoslovak", "cm_yugoslav"):
            self.assertEqual(tier_of(cfg.merge_by_key("pan_slavic"), c), 3)
            self.assertIn("AND = { te_cmg_pan_slavic_%s_measured = yes te_cmg_pan_slavic_%s_years_met = yes }" % (c, c), pan_slavic)
            self.assertIn("var:te_cm_years_pan_slavic_%s >= te_cm_years_tier3" % c, self.trig("te_cmg_pan_slavic_%s_years_met" % c))
        anglophone = self.trig("te_cmg_anglophone_core_ok")
        self.assertIn("AND = { te_cmg_anglophone_british_measured = yes te_cmg_anglophone_british_years_met = yes }", anglophone)
        self.assertIn("var:te_cm_years_anglophone_british >= te_cm_years_tier2", self.trig("te_cmg_anglophone_british_years_met"))
        self.assertNotIn("years_met", self.trig("te_cmg_german_core_ok"))

    def test_availability(self):
        indexes = {m.key: merge_index(m) for m in cfg.MERGES}
        results = {m.result: m for m in cfg.MERGES}
        for merge in cfg.MERGES:
            for culture in slot_cultures(merge):
                body = self.trig("te_cmg_%s_%s_available" % (merge.key, culture))
                others = [m for m in cfg.MERGES if m is not merge and culture in slot_cultures(m)]
                for other in others:
                    self.assertIn("NOT = { global_var:te_cm_in_%s ?= %d }" % (culture, indexes[other.key]), body)
                self.assertNotIn("?= %d }" % indexes[merge.key], body.replace("te_cm_state", ""))
                # R33: the result of another merge (an absorb result such as french, or a cm_ id) is free only
                # once that merge is finished: complete with every joined part switched, or nothing joined.
                lower = results.get(culture)
                if lower is not None and lower is not merge:
                    joined = " ".join(
                        "global_var:te_cm_joined_%s_%s ?= 1" % (lower.key, c)
                        for c in slot_cultures(lower) if not _absorb_result(lower, c)
                    )
                    self.assertIn(
                        "OR = { AND = { global_var:te_cm_state_%s ?= 2 te_cmg_%s_all_switched = yes } NOR = { %s } }"
                        % (lower.key, lower.key, joined),
                        body, "%s/%s" % (merge.key, culture),
                    )
                else:
                    self.assertNotIn("all_switched", body, "%s/%s" % (merge.key, culture))
                if not others and (lower is None or lower is merge):
                    self.assertEqual(body, "always = yes", culture)
        self.assertIn("NOT = { global_var:te_cm_in_yankee ?= %d }" % indexes["american"],
                      self.trig("te_cmg_anglophone_yankee_available"))
        self.assertIn("global_var:te_cm_state_american ?= 2", self.trig("te_cmg_anglophone_cm_american_available"))
        # An absorb result is the same: Latin takes french, Anglophone takes british, only after those merges.
        self.assertIn("te_cmg_french_all_switched = yes", self.trig("te_cmg_latin_french_available"))
        self.assertIn("te_cmg_british_all_switched = yes", self.trig("te_cmg_anglophone_british_available"))

    def test_can_join_follows_the_part_tier(self):
        for merge in cfg.MERGES:
            optional = {c for part in merge.optional for c in part.cultures}
            for culture in slot_cultures(merge):
                tier = tier_of(merge, culture)
                body = self.trig("te_cmg_%s_%s_can_join" % (merge.key, culture))
                self.assertIn("var:te_cm_ok_%s_%s ?= 1" % (merge.key, culture), body)
                self.assertIn("te_cmg_%s_%s_available = yes" % (merge.key, culture), body)
                self.assertIn("NOT = { global_var:te_cm_joined_%s_%s ?= 1 }" % (merge.key, culture), body)
                # R32/R33: a culture that has switched joins nothing, and nothing joins a merge whose result has
                # (M6: one generated trigger says so). R38: nor one whose result a higher merge has joined.
                self.assertIn("NOT = { has_global_variable = te_cm_switched_%s }" % culture, body)
                self.assertIn("NOT = { te_cmg_%s_result_switched = yes }" % merge.key, body)
                joined_higher = "NOT = { has_global_variable = te_cm_in_%s }" % merge.result
                self.assertEqual(joined_higher in body, gen.result_can_switch(merge, cfg.MERGES), (merge.key, culture))
                self.assertIn("te_cm_tier_tech = { TIER = %d }" % tier, body)
                years = "te_cm_years_%s_%s" % (merge.key, culture)
                if tier == 1:
                    self.assertNotIn("te_cm_years", body)
                    self.assertNotIn("years_met", body)
                else:
                    needed = "te_cm_years_tier2" if tier == 2 else "te_cm_years_tier3"
                    self.assertIn("te_cmg_%s_%s_years_met = yes" % (merge.key, culture), body)
                    self.assertEqual(
                        self.trig("te_cmg_%s_%s_years_met" % (merge.key, culture)),
                        "has_variable = %s trigger_if = { limit = { has_variable = %s } var:%s >= %s }" % (years, years, years, needed),
                    )
                # R23: an optional part also waits for its own standard-of-living gate.
                gate = "var:te_cm_sol_ok_%s_%s ?= 1" % (merge.key, culture)
                if culture in optional:
                    self.assertIn(gate, body, culture)
                else:
                    self.assertNotIn("te_cm_sol_ok", body, culture)

    def test_a_part_joins_on_its_own_tier_even_below_the_merges(self):
        # R17: Afro-American is a tier-1b join to a tier-1 American merge.
        american = cfg.merge_by_key("american")
        self.assertEqual(tier_of(american, "afro_american"), 2)
        body = self.trig("te_cmg_american_afro_american_can_join")
        self.assertIn("te_cm_tier_tech = { TIER = 2 }", body)
        self.assertIn("te_cmg_american_afro_american_years_met = yes", body)
        self.assertIn("te_cm_years_tier2", self.trig("te_cmg_american_afro_american_years_met"))
        self.assertIn("TIER = 1 }", self.trig("te_cmg_american_is_candidate"))

    def test_the_set_of_generated_triggers(self):
        names = set(re.findall(r"^(te_cmg_\w+) = \{", self.triggers, re.M))
        expected = set()
        for merge in cfg.MERGES:
            expected.update(
                "te_cmg_%s_%s" % (merge.key, suffix)
                for suffix in (
                    "is_candidate", "core_ok", "census_wanted", "is_starter", "has_other_starter", "can_start",
                    "starter_gone", "all_switched", "core_switched", "result_switched",
                )
            )
            if any(part.wait_for for part in merge.core):
                expected.add("te_cmg_%s_start_basics" % merge.key)
            if gen.core_left_slots(merge, cfg.MERGES):
                expected.add("te_cmg_%s_core_left" % merge.key)
            for culture in slot_cultures(merge):
                for suffix in ("available", "measured", "can_join"):
                    expected.add("te_cmg_%s_%s_%s" % (merge.key, culture, suffix))
                part = next(p for p in merge.core + merge.optional if culture in p.cultures)
                if part.wait_for and not _absorb_result(merge, culture):
                    expected.add("te_cmg_%s_%s_waiting" % (merge.key, culture))
                if tier_of(merge, culture) > 1:
                    expected.add("te_cmg_%s_%s_years_met" % (merge.key, culture))
                if not _absorb_result(merge, culture):
                    expected.add("te_cmg_%s_%s_switched_in" % (merge.key, culture))
        # Task 6: the two culture-scope triggers over every culture that can switch, one each.
        expected.update(("te_cmg_is_switched_part", "te_cmg_switched_part_kept"))
        self.assertEqual(names, expected)

    def test_no_two_merges_name_the_same_variable(self):
        # te_cm_sol_ok_<m> and te_cm_sol_ok_<m>_<c> share a prefix; a merge key that is another merge's key + _ +
        # a culture would make one variable of two.
        names = {}
        for merge in cfg.MERGES:
            names.setdefault("te_cm_sol_ok_%s" % merge.key, []).append(merge.key)
            for culture in slot_cultures(merge):
                names.setdefault("te_cm_sol_ok_%s_%s" % (merge.key, culture), []).append("%s/%s" % (merge.key, culture))
        self.assertEqual({n: who for n, who in names.items() if len(who) > 1}, {})


class StateIsVariablesTest(unittest.TestCase):
    def test_counters_are_variables(self):
        # Revolution inheritance: a modifier or a variable list would be lost to a civil war's winner.
        paths = sorted((ROOT / "common").rglob("*culture_merge*")) + list(SCRIPT_FILES)
        seen = 0
        for path in set(paths):
            if path.suffix != ".txt":
                continue
            seen += 1
            text = text_of(path)
            for banned in ("add_modifier", "add_to_variable_list", "add_to_global_variable_list"):
                self.assertNotIn(banned, text, "%s uses %s" % (path.name, banned))
        self.assertGreaterEqual(seen, len(SCRIPT_FILES))

    def test_the_census_resets_nothing_on_a_rule_change(self):
        # R19: counters and gates keep their last values while the rule is off, so the census never takes a
        # global variable away: the lock is set, never removed, and it is the only global it writes besides
        # the home counts and the year.
        # The four helpers that start, join, unjoin and release a merge (Task 5, R38) and the four that convert,
        # measure dominance, switch and keep the primary cultures (Task 6) sit in the same file but are not the
        # census: the release, the unjoin and the switch are the places a global variable is removed, and
        # test_culture_merge_entries and test_culture_merge_switch pin what each of them writes.
        helpers = (
            "te_cm_start_merge", "te_cm_join_part", "te_cm_unjoin_part", "te_cm_release_starter",
            "te_cm_convert_part", "te_cm_census_dominance", "te_cm_switch_part", "te_cm_monthly_switched_culture",
        )

        def census_only(path):
            text = text_of(path)
            for name in helpers:
                body = block(text, name)
                if body is not None:
                    text = text.replace("%s = {\n%s}" % (name, body), "")
            return text

        for path in (EFFECTS, ON_ACTIONS, GEN_EFFECTS, GEN_TRIGGERS):
            text = census_only(path)
            self.assertNotIn("has_game_rule", text, path.name)
            self.assertNotIn("remove_global_variable", text, path.name)
            self.assertNotIn("clear_global_variable_list", text, path.name)
        # The removals are the temporary holder variable, which never outlives its census call, and the
        # standard-of-living figures the status row prints, taken away when no core part has one: they are for display
        # only (the gate is te_cm_sol_ok_<m>, never removed), and with the rule off no census runs to touch them.
        removed = set(re.findall(r"remove_variable = (\w+)", census_only(EFFECTS) + census_only(GEN_EFFECTS)))
        shown = {"te_cm_sol_%s_%s" % (name, merge.key) for name in SOL_SHOWN for merge in cfg.MERGES}
        self.assertEqual(removed, {"te_cm_tmp_cnt"} | shown)
        written = set(re.findall(r"set_global_variable = \{ name = ([\w$]+)", census_only(EFFECTS) + census_only(ON_ACTIONS)))
        self.assertEqual(written, {"te_cm_census_lock", "te_cm_census_year"} | {"te_cm_home_$CULTURE$", "te_cm_home_r_$CULTURE$"})


# ---------------------------------------------------------------------------------------------------------------
# The gate, run. A small interpreter for te_cm_census_part's acceptance count and its hysteresis gate, so a test can
# ask what the gate does over a run of years. It keeps the comparison operators, which the other test files' parsed
# trees drop, and reads the thresholds from the values file, with vanilla's acceptance_status_<n> from the committed
# snapshot (no game install needed).
# ---------------------------------------------------------------------------------------------------------------

HAND_VALUES = ROOT / "common/script_values/te_culture_merge_values.txt"
_OP_TOKEN = re.compile(
    r"(?P<close>\})|(?P<key>[\w.:|@$-]+)\s*(?P<op>\?=|[!<>=]=|[=<>])\s*(?:(?P<open>\{)|(?P<value>[^\s{}]+))"
)


class OpNode:
    def __init__(self, key, op, value):
        self.key, self.op, self.value, self.children = key, op, value, []


def parse_ops(text):
    root = []
    stack = [root]
    for m in _OP_TOKEN.finditer(text):
        if m.group("close"):
            if len(stack) > 1:
                stack.pop()
            continue
        node = OpNode(m.group("key"), m.group("op"), m.group("value"))
        stack[-1].append(node)
        if m.group("open"):
            stack.append(node.children)
    return root


def _op_child(node, key):
    return next((c for c in node.children if c.key == key), None)


class GateSim:
    """Countries with variables and an average acceptance of the part, the locals, `this`; named values resolved."""

    def __init__(self, cvars, acceptance, locals_, this="CAND", values=None):
        self.cvars = {c: dict(v) for c, v in cvars.items()}
        self.acceptance = dict(acceptance)
        self.locals = dict(locals_)
        self.this = this
        self.values = gate_values() if values is None else values

    def num(self, token):
        if token.startswith("local_var:"):
            return self.locals[token.split(":", 1)[1]]
        if token.startswith("var:"):
            return self.cvars[self.this][token.split(":", 1)[1]]
        if token in self.values:
            return self.values[token]
        return float(token)

    def value_of(self, node):
        if node.value is not None:
            return self.num(node.value)
        total = 0.0
        for c in node.children:
            v = self.value_of(c)
            total = {"value": lambda: v, "multiply": lambda: total * v, "divide": lambda: total / v,
                     "add": lambda: total + v, "max": lambda: min(total, v), "min": lambda: max(total, v)}[c.key]()
        return total

    @staticmethod
    def compare(a, op, b):
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "=": a == b, "?=": a == b, "==": a == b}[op]

    def holds(self, nodes):
        return all(self.holds_one(n) for n in nodes)

    def holds_one(self, n):
        if n.key == "AND":
            return self.holds(n.children)
        if n.key == "OR":
            return any(self.holds_one(c) for c in n.children)
        if n.key == "NOT":
            return not self.holds(n.children)
        if n.key == "has_variable":
            return n.value in self.cvars.get(self.this, {})
        if n.key == "country_average_culture_pop_acceptance":
            value = _op_child(n, "value")
            return self.compare(self.acceptance[self.this], value.op, self.num(value.value))
        if n.key.startswith(("var:", "local_var:")):
            name = n.key.split(":", 1)[1]
            scope = self.locals if n.key.startswith("local_var:") else self.cvars.get(self.this, {})
            if name not in scope:
                if n.op == "?=":
                    return False
                raise KeyError("read of the unset %s" % n.key)
            return self.compare(scope[name], n.op, self.num(n.value))
        raise KeyError("the gate interpreter does not know %s" % n.key)

    def run(self, nodes):
        last = None
        for n in nodes:
            k = n.key
            if k == "limit":
                continue
            if k == "if":
                last = self.holds(_op_child(n, "limit").children)
                if last:
                    self.run(n.children)
            elif k == "else":
                if not last:
                    self.run(n.children)
            elif k in ("set_local_variable", "change_local_variable", "set_variable", "change_variable"):
                store = self.locals if "local" in k else self.cvars.setdefault(self.this, {})
                name = _op_child(n, "name").value
                if k.startswith("set_"):
                    store[name] = self.value_of(_op_child(n, "value"))
                elif _op_child(n, "add") is not None:
                    store[name] += self.value_of(_op_child(n, "add"))
                else:
                    store[name] -= self.value_of(_op_child(n, "subtract"))
            elif k == "remove_variable":
                self.cvars.get(self.this, {}).pop(n.value, None)
            elif k == "every_country":
                saved = self.this
                for country in sorted(self.cvars):
                    self.this = country
                    if self.holds(_op_child(n, "limit").children):
                        self.run(n.children)
                self.this = saved
            else:
                raise KeyError("the gate interpreter does not know %s" % k)


_GATE_VALUES = None


def gate_values():
    """The values file's named numbers (te_cm_accept_open = { value = acceptance_status_5 } resolved), and vanilla's
    acceptance statuses from the snapshot."""
    global _GATE_VALUES
    if _GATE_VALUES is None:
        snapshot = snapshot_data()["Script Values"]
        values = {k: float(cfg.unwrap(v)) for k, v in snapshot.items() if re.fullmatch(r"acceptance_status_\d", k)}
        sim = GateSim({}, {}, {}, values=values)
        for node in parse_ops(text_of(HAND_VALUES)):
            try:
                values[node.key] = sim.value_of(node)
            except (KeyError, ValueError):
                pass  # the per-pop rate and the Russification share read game state, not numbers
        _GATE_VALUES = values
    return _GATE_VALUES


class GateScenarioTest(unittest.TestCase):
    """te_cm_census_part's gate over a run of years: it opens at the open values, holds inside the band, closes only
    past the close values, and reopens only at the open values again (the one hysteresis convention)."""

    @classmethod
    def setUpClass(cls):
        body = block(text_of(EFFECTS), "te_cm_census_part").replace("$MERGE$", "german").replace("$CULTURE$", "north_german")
        nodes = parse_ops(body)
        start = next(i for i, n in enumerate(nodes) if n.key == "set_local_variable"
                     and _op_child(n, "name").value == "te_cm_cp_fail_open")
        cls.gate = nodes[start:]

    def year(self, sim, held, acceptance, holders=None, tier=1, joined=0):
        """One census of the part on CAND: CAND holds every pop unless `holders` ({country: count}) says otherwise."""
        holders = holders or {"CAND": 1000}
        for country in sim.cvars:
            sim.cvars[country].pop("te_cm_tmp_cnt", None)
        for country, count in holders.items():
            sim.cvars.setdefault(country, {})["te_cm_tmp_cnt"] = float(count)
        sim.acceptance.update(acceptance if isinstance(acceptance, dict) else {"CAND": acceptance})
        sim.cvars["CAND"]["te_cm_held_german_north_german"] = held
        sim.locals.update({"te_cm_cp_part_pops": float(sum(holders.values())), "te_cm_cp_max_cnt": float(max(holders.values())),
                           "te_cm_cp_joined": float(joined), "te_cm_cp_tier": float(tier)})
        sim.this = "CAND"
        sim.run(self.gate)
        return int(sim.cvars["CAND"]["te_cm_ok_german_north_german"])

    def walk(self, steps, tier=1, joined=0):
        sim = GateSim({"CAND": {"te_cm_ok_german_north_german": 0}}, {}, {})
        return [self.year(sim, held, acc, tier=tier, joined=joined) for held, acc, _ in steps], [want for _, _, want in steps]

    def test_the_values_are_the_ones_the_rows_and_the_guide_state(self):
        values = gate_values()
        self.assertEqual((values["acceptance_status_4"], values["acceptance_status_5"]), (60, 80))
        self.assertEqual((values["te_cm_hold_open"], values["te_cm_hold_close"]), (0.60, 0.50))
        # R39: accepted is Full Acceptance (80), so a part at Provisional Acceptance (60 to 79) is not.
        self.assertEqual((values["te_cm_accept_open"], values["te_cm_accept_close"]), (80, 75))
        self.assertEqual((values["te_cm_accept_high_open"], values["te_cm_accept_high_close"]), (90, 85))

    def test_a_tier_1_part_opens_closes_and_reopens_at_its_values(self):
        got, want = self.walk([
            (0.59, 90, 0),  # held short of the open value
            (0.60, 70, 0),  # Provisional Acceptance: not accepted
            (0.60, 79, 0),  # accepted short of Full Acceptance
            (0.60, 80, 1),  # both at the open values: opens
            (0.51, 76, 1),  # inside both bands: stays open
            (0.49, 90, 0),  # held below the close value: closes
            (0.55, 90, 0),  # back above the close value but short of the open one: stays closed
            (0.60, 90, 1),  # reopens only at the open value
            (0.70, 74, 0),  # acceptance below its close value: closes
            (0.70, 79, 0),  # stays closed below the open value
            (0.70, 80, 1),  # reopens
        ])
        self.assertEqual(got, want)

    def test_a_tier_1b_part_uses_the_very_high_pair(self):
        got, want = self.walk([
            (0.60, 89, 0),
            (0.60, 90, 1),
            (0.60, 86, 1),
            (0.60, 84, 0),
            (0.60, 89, 0),
            (0.60, 90, 1),
        ], tier=2)
        self.assertEqual(got, want)

    def test_a_joined_part_is_held_to_the_hold_alone(self):
        # R29: once joined, acceptance pauses conversion per country instead.
        got, want = self.walk([(0.60, 10, 1), (0.51, 10, 1), (0.49, 10, 0), (0.60, 10, 1)], joined=1)
        self.assertEqual(got, want)

    def test_acceptance_counts_where_many_live_and_in_the_largest_holder(self):
        sim = GateSim({"CAND": {"te_cm_ok_german_north_german": 0}, "MEM": {}}, {}, {})
        # A member holding a twentieth of the sphere's pops doesn't count; the starter holding most does.
        self.assertEqual(self.year(sim, 0.9, {"CAND": 90, "MEM": 0}, holders={"CAND": 950, "MEM": 50}), 1)
        # Holding a fifth, it does, and it fails the close value: the gate closes.
        self.assertEqual(self.year(sim, 0.9, {"CAND": 90, "MEM": 0}, holders={"CAND": 800, "MEM": 200}), 0)
        # A part split thin, no country holding a tenth: the largest holders are tested all the same, so the gate
        # can't pass with nobody tested.
        thin = {"C%02d" % i: 10 for i in range(20)}
        thin["CAND"] = 5
        for refuser, expected in ((None, 1), ("C00", 0)):
            sim = GateSim({c: {} for c in thin}, {c: 90 for c in thin}, {})
            sim.cvars["CAND"]["te_cm_ok_german_north_german"] = 0
            if refuser:
                sim.acceptance[refuser] = 0
            self.assertEqual(self.year(sim, 0.9, {}, holders=thin), expected, refuser)

    def test_the_years_together_count_while_the_gate_is_open(self):
        sim = GateSim({"CAND": {"te_cm_ok_german_north_german": 0}}, {}, {})
        for held, acc in ((0.60, 90), (0.60, 90), (0.49, 90), (0.60, 90)):
            self.year(sim, held, acc, tier=2)
        self.assertEqual(sim.cvars["CAND"]["te_cm_years_german_north_german"], 3)


class SolFiguresScenarioTest(unittest.TestCase):
    """The census's standard-of-living section for East Slavic (three core cultures, no alternatives), run: it keeps the
    best- and worst-off cultures and the gap the gate read, and drops them once no core culture has a figure."""

    class Sim(GateSim):
        def num(self, token):
            return token if token.startswith("cu:") else super().num(token)

    @classmethod
    def setUpClass(cls):
        body = block(text_of(GEN_EFFECTS), "te_cmg_census_east_slavic_country")
        body = body[body.index("set_local_variable = { name = te_cm_sg_min"):body.index("te_cmg_east_slavic_settle")]
        track = block(text_of(EFFECTS), "te_cm_sol_track")
        cls.cultures = [part.cultures[0] for part in cfg.merge_by_key("east_slavic").core]
        for culture in cls.cultures:
            body = body.replace("te_cm_sol_track = { MERGE = east_slavic CULTURE = %s }" % culture,
                                track.replace("$MERGE$", "east_slavic").replace("$CULTURE$", culture))
            body = body.replace("te_cmg_east_slavic_%s_measured = yes" % culture, "local_var:measured_%s = 1" % culture)
            body = body.replace("te_cmg_east_slavic_%s_switched_in = yes" % culture, "local_var:switched_%s = 1" % culture)
        cls.nodes = parse_ops(body)

    def census(self, sim, sol):
        """One census: `sol` maps each measured core culture to its standard of living; the rest are unmeasured."""
        for culture in self.cultures:
            sim.locals["measured_%s" % culture] = 1 if culture in sol else 0
            sim.locals["switched_%s" % culture] = 0
            if culture in sol:
                sim.cvars["CAND"]["te_cm_sol_east_slavic_%s" % culture] = sol[culture]
        sim.run(self.nodes)
        return {n: sim.cvars["CAND"].get("te_cm_sol_%s_east_slavic" % n) for n in SOL_SHOWN}

    def test_the_figures_follow_the_gate(self):
        self.assertEqual(self.cultures, ["russian", "ukrainian", "byelorussian"])
        sim = self.Sim({"CAND": {}}, {}, {})
        got = self.census(sim, {"russian": 14.0, "ukrainian": 9.5, "byelorussian": 11.0})
        self.assertEqual(got, {"best": "cu:russian", "worst": "cu:ukrainian", "hi": 14.0, "lo": 9.5, "gap": 4.5})
        self.assertEqual(sim.cvars["CAND"]["te_cm_sol_ok_east_slavic"], 0)
        # Ukrainian catches up: a new worst-off culture, and the gap under the open value opens the gate.
        got = self.census(sim, {"russian": 14.0, "ukrainian": 12.5, "byelorussian": 11.5})
        self.assertEqual(got, {"best": "cu:russian", "worst": "cu:byelorussian", "hi": 14.0, "lo": 11.5, "gap": 2.5})
        self.assertEqual(sim.cvars["CAND"]["te_cm_sol_ok_east_slavic"], 1)
        # One culture measured: it is both ends, a gap of 0.
        got = self.census(sim, {"ukrainian": 12.0})
        self.assertEqual(got, {"best": "cu:ukrainian", "worst": "cu:ukrainian", "hi": 12.0, "lo": 12.0, "gap": 0.0})
        # None measured: no figures to show, and the gate stays as it was.
        got = self.census(sim, {})
        self.assertEqual(got, dict.fromkeys(SOL_SHOWN))
        self.assertEqual(sim.cvars["CAND"]["te_cm_sol_ok_east_slavic"], 1)


class CallsMatchTheirHelpersTest(unittest.TestCase):
    def test_every_generated_call_matches_its_helper(self):
        import script_argument_audit

        result = script_argument_audit.audit(mod_path=str(ROOT), vanilla_game=None)
        mine = {str(p.relative_to(ROOT)) for p in SCRIPT_FILES}
        flagged = [(f.file, f.line, f.callee) for f in result.flags if f.file in mine]
        self.assertEqual(flagged, [])
        called = {name for name, calls in result.call_sites.items() if any(c.file in mine for c in calls)}
        for helper in ("te_cm_census_culture", "te_cm_census_part", "te_cm_sol_track", "te_cm_tier_tech"):
            self.assertIn(helper, called, helper)


if __name__ == "__main__":
    unittest.main()
