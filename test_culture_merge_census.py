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


def vanilla():
    global _VANILLA
    if _VANILLA is None:
        data = vanilla_parsed.load(str(ROOT / "vanilla_parsed")).data
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
            self.assertNotIn("limit", body, key)  # a trigger, and no any_* takes a limit

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
            # following the result, or one dip in the hold would freeze its gate at 0 for good.
            needed = " ".join("NOT = { has_global_variable = te_cm_switched_%s }" % c for c in optional)
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
            "OR = { country_has_primary_culture = cu:north_german country_has_primary_culture = cu:south_german } "
            "te_cm_tier_tech = { TIER = 1 } "
            "NOT = { global_var:te_cm_state_german ?= 2 } "
            "NOT = { has_global_variable = te_cm_switched_cm_german }",
        )

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
                # R32/R33: a culture that has switched joins nothing, and nothing joins a merge whose result has.
                self.assertIn("NOT = { has_global_variable = te_cm_switched_%s }" % culture, body)
                self.assertIn("NOT = { has_global_variable = te_cm_switched_%s }" % merge.result, body)
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
                    "starter_gone", "all_switched", "core_switched",
                )
            )
            if any(part.wait_for for part in merge.core):
                expected.add("te_cmg_%s_start_basics" % merge.key)
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
        # The three helpers that start, join and release a merge (Task 5) and the four that convert, measure
        # dominance, switch and keep the primary cultures (Task 6) sit in the same file but are not the census:
        # the release and the switch are the places a global variable is removed, and test_culture_merge_entries
        # and test_culture_merge_switch pin what each of them writes.
        helpers = (
            "te_cm_start_merge", "te_cm_join_part", "te_cm_release_starter",
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
        # The one removal is the temporary holder variable, which never outlives its census call.
        removed = set(re.findall(r"remove_variable = (\w+)", census_only(EFFECTS) + census_only(GEN_EFFECTS)))
        self.assertEqual(removed, {"te_cm_tmp_cnt"})
        written = set(re.findall(r"set_global_variable = \{ name = ([\w$]+)", census_only(EFFECTS) + census_only(ON_ACTIONS)))
        self.assertEqual(written, {"te_cm_census_lock", "te_cm_census_year"} | {"te_cm_home_$CULTURE$", "te_cm_home_r_$CULTURE$"})


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
