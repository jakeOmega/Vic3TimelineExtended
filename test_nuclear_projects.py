"""Delivery projects (2026-11-20 delivery spec §4.1; phase 2 plan Task 1, D2-D6).

After its first device a programme's funding builds whatever its focus names:
Warheads, ICBMs or Missile Submarines. nd_prog_focus holds 2 or 3 for a
project and is unset for Warheads, so every save and every activation starts
valid without a write. The native bar reads nuclear_weapon_program_progress,
the progress of the focus in force; the others wait in their own slots
(nd_proj_warhead_progress, nd_proj_icbm_progress, nd_proj_sub_progress). One
effect parks and loads (nd_focus_set); the entry's immediate parks before it
zeroes, and the weekly pulse loads back, raising only. A project runs at the
first device's rate toward 100, and at 100 its leg is fielded and the focus
returns to Warheads. An arsenal ceiling, ours, a treaty's or the UN ban's,
holds only a Warheads focus, and so does the AI's stockpile cap."""

import re
import unittest

from test_nuclear_delivery import constant
from test_nuclear_deterrence import ROOT, block, read, squash, strip_comments

NUKE_TRIGGERS = ROOT / "common/scripted_triggers/nuke_triggers.txt"
TABOO_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_taboo_triggers.txt"
EXTRA_VALUES = ROOT / "common/script_values/extra_script_values.txt"
WEAPON_EFFECTS = ROOT / "common/scripted_effects/nuclear_weapon_effects.txt"
JOURNAL = ROOT / "common/journal_entries/je_nuclear_program.txt"
SGUIS = ROOT / "common/scripted_guis/nuclear_program_sguis.txt"
GUI = ROOT / "gui/journal_entry_widgets/nuclear_program_widget.gui"
SYSTEMS_DOC = ROOT / "docs/systems/journal_entry_systems.md"
LOC = ROOT / "localization/english"

SLOTS = {1: "nd_proj_warhead_progress", 2: "nd_proj_icbm_progress", 3: "nd_proj_sub_progress"}
LIVE = "nuclear_weapon_program_progress"


def loc_keys():
    keys = set()
    for path in LOC.glob("*.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"\s+([A-Za-z0-9_.\-]+):\d*\s", line)
            if m:
                keys.add(m.group(1))
    return keys


def tooltips(body):
    """The bodies of each top-level custom_tooltip block in a trigger body,
    and what is left outside them."""
    found, rest, i = [], [], 0
    for m in re.finditer(r"custom_tooltip\s*=\s*\{", body):
        if m.start() < i:
            continue
        depth, j = 1, m.end()
        while depth:
            depth += body[j] == "{"
            depth -= body[j] == "}"
            j += 1
        rest.append(body[i:m.start()])
        found.append(body[m.end():j - 1])
        i = j
    rest.append(body[i:])
    return found, "".join(rest)


class TestFocus(unittest.TestCase):

    def setUp(self):
        self.triggers = strip_comments(read(NUKE_TRIGGERS))

    def test_three_triggers_and_unset_for_warheads(self):
        self.assertEqual(squash(block(self.triggers, "nd_focus_is_warheads")),
                         "NOT = { has_variable = nd_prog_focus }")
        self.assertEqual(squash(block(self.triggers, "nd_focus_is_icbms")), "var:nd_prog_focus ?= 2")
        self.assertEqual(squash(block(self.triggers, "nd_focus_is_submarines")), "var:nd_prog_focus ?= 3")

    def test_no_activation_writes_the_focus(self):
        immediate = block(strip_comments(read(JOURNAL)), "immediate")
        self.assertNotIn("nd_prog_focus", immediate)
        park = block(strip_comments(read(WEAPON_EFFECTS)), "nd_focus_park_live")
        self.assertNotIn("name = nd_prog_focus", park)
        self.assertNotIn("remove_variable = nd_prog_focus", park)


class TestParking(unittest.TestCase):

    def setUp(self):
        self.effects = strip_comments(read(WEAPON_EFFECTS))
        self.journal = read(JOURNAL)

    def test_focus_set_parks_then_loads_then_refreshes_the_hold_once(self):
        body = block(self.effects, "nd_focus_set")
        park = body.index("nd_focus_park_live = yes")
        for f, slot in SLOTS.items():
            with self.subTest(focus=f):
                load = squash(body)
                self.assertIn(f"has_variable = {slot}", load)
                self.assertIn(f"set_variable = {{ name = {LIVE} value = var:{slot} }}", load)
                self.assertIn(f"remove_variable = {slot}", load)
                self.assertLess(park, body.index(f"var:{slot}"))
        self.assertIn("set_variable = { name = nd_prog_focus value = 2 }", squash(body))
        self.assertIn("set_variable = { name = nd_prog_focus value = 3 }", squash(body))
        self.assertIn("remove_variable = nd_prog_focus", body)
        self.assertEqual(body.count("nd_taboo_refresh_held = yes"), 1)
        self.assertGreater(body.index("nd_taboo_refresh_held = yes"), body.index("remove_variable = nd_prog_focus"))
        # The new focus's slot is gone, so nothing is ever loaded twice.
        self.assertIn(f"set_variable = {{ name = {LIVE} value = 0 }}", squash(body))

    def test_park_covers_all_three_foci_over_zero_only(self):
        body = squash(block(self.effects, "nd_focus_park_live"))
        self.assertIn(f"has_variable = {LIVE} var:{LIVE} > 0", body)
        for trigger, slot in (("nd_focus_is_icbms", SLOTS[2]), ("nd_focus_is_submarines", SLOTS[3])):
            self.assertIn(f"{trigger} = yes }} nd_focus_park_into = {{ SLOT = {slot} }}", body)
        self.assertIn(f"nd_focus_park_into = {{ SLOT = {SLOTS[1]} }}", body)

    def test_a_park_keeps_the_larger_figure(self):
        body = squash(block(self.effects, "nd_focus_park_into"))
        self.assertIn(f"var:$SLOT$ < var:{LIVE}", body)
        self.assertIn(f"set_variable = {{ name = $SLOT$ value = var:{LIVE} }}", body)

    def test_immediate_parks_before_it_zeroes(self):
        immediate = block(self.journal, "immediate")
        park = immediate.index("nd_focus_park_live = yes")
        zero = immediate.index(f"name = {LIVE}")
        self.assertLess(park, zero)
        line = immediate[park:immediate.index("\n", park)]
        self.assertRegex(line, r"# REVIEWED \d{4}-\d{2}-\d{2}")

    def test_restore_runs_after_the_custody_carry_and_raises_only(self):
        pulse = strip_comments(block(self.journal, "on_weekly_pulse"))
        self.assertLess(pulse.index("nd_custody_restore_progress = yes"), pulse.index("nd_focus_restore = yes"))
        self.assertLess(pulse.index("nd_focus_restore = yes"), pulse.index("nuclear_program_weekly_progress = yes"))
        body = squash(block(self.effects, "nd_focus_restore"))
        for trigger, slot in (("nd_focus_is_icbms", SLOTS[2]), ("nd_focus_is_submarines", SLOTS[3]),
                              ("nd_focus_is_warheads", SLOTS[1])):
            self.assertIn(f"{trigger} = yes has_variable = {slot} }} nd_focus_restore_slot = {{ SLOT = {slot} }}", body)
        slot = squash(block(self.effects, "nd_focus_restore_slot"))
        self.assertIn(f"var:{LIVE} < var:$SLOT$", slot)
        self.assertIn("remove_variable = $SLOT$", slot)
        self.assertNotIn("subtract", slot)


class TestProjectRate(unittest.TestCase):

    def test_ten_times_only_on_warheads(self):
        body = squash(block(strip_comments(read(EXTRA_VALUES)), "nuclear_weapon_program_monthly_progress"))
        self.assertIn("value = var:nuclear_weapons_program_funding", body)
        self.assertRegex(body, r"limit = \{ (nd_focus_is_warheads = yes var:nuclear_weapons_program_first_nuke_done > 0"
                               r"|var:nuclear_weapons_program_first_nuke_done > 0 nd_focus_is_warheads = yes) \}"
                               r" multiply = nuclear_weapon_program_additional_nuke_progress_multiplier")

    def test_twenty_months_at_five_steps(self):
        values = read(EXTRA_VALUES)
        goal = constant(values, "nuclear_weapon_program_goal_value")
        self.assertEqual(goal / 5, 20)
        mult = constant(read(ROOT / "common/script_values/extra_script_values.txt"),
                        "nuclear_weapon_program_additional_nuke_progress_multiplier")
        # Ten warheads' worth of effort: a warhead every two months at the same funding.
        self.assertEqual(goal / (5 * mult), 2)


class TestCompletion(unittest.TestCase):

    def setUp(self):
        self.effects = strip_comments(read(WEAPON_EFFECTS))
        self.weekly = block(self.effects, "nuclear_program_weekly_progress")

    def test_warheads_are_built_only_on_a_warheads_focus(self):
        loop = block(self.weekly, "while")
        self.assertIn("nd_focus_is_warheads = yes", block(loop, "limit"))

    def test_a_project_at_its_goal_fields_its_leg(self):
        body = squash(self.weekly)
        for trigger, leg in (("nd_focus_is_icbms", "icbms"), ("nd_focus_is_submarines", "subs")):
            self.assertIn(f"{trigger} = yes var:{LIVE} >= nuclear_weapon_program_goal_value }} "
                          f"nd_field_leg = {{ LEG = {leg} }}", body)

    def test_field_leg(self):
        body = block(self.effects, "nd_field_leg")
        flat = squash(body)
        self.assertIn("set_variable = { name = nd_$LEG$_fielded value = year }", flat)
        # The project's progress is spent, overflow included, before the
        # focus returns to Warheads with that slot loaded.
        zero = flat.index(f"set_variable = {{ name = {LIVE} value = 0 }}")
        self.assertLess(zero, flat.index("nd_focus_set = { F = 1 }"))
        for refresh in ("nd_reach_refresh = yes", "nd_apply_posture_modifiers = yes", "nd_refresh_main_rival = yes"):
            self.assertEqual(body.count(refresh), 1, refresh)
        # nd_focus_set refreshes the hold: once, and not here again.
        self.assertNotIn("nd_taboo_refresh_held", body)
        self.assertIn("type=leg_fielded", body)


class TestHolds(unittest.TestCase):

    def test_ceilings_hold_only_a_warheads_focus(self):
        held = squash(block(strip_comments(read(TABOO_TRIGGERS)), "nd_taboo_programme_should_be_held"))
        self.assertIn("OR = { nd_taboo_is_dismantling = yes AND = { nd_focus_is_warheads = yes", held)
        self.assertEqual(held.count("nd_focus_is_warheads"), 1)
        cap = squash(block(strip_comments(read(NUKE_TRIGGERS)), "nuclear_program_ai_at_stockpile_cap"))
        self.assertIn("nd_focus_is_warheads = yes", cap)

    def test_freezes_disarmament_and_standing_still_hold_a_project(self):
        weekly = block(strip_comments(read(WEAPON_EFFECTS)), "nuclear_program_weekly_progress")
        pause = weekly[:weekly.index("change_variable")]
        self.assertIn("modifier:country_nuclear_program_pause_bool = yes", pause)
        self.assertNotIn("nd_focus", pause)
        pulse = strip_comments(block(read(JOURNAL), "on_weekly_pulse"))
        disarm = pulse[pulse.index("modifier:country_nuclear_disarmament_bool"):pulse.index("Self-heal") if "Self-heal" in pulse else None]
        self.assertNotIn("nd_focus", disarm)
        self.assertNotIn("nd_focus", block(strip_comments(read(NUKE_TRIGGERS)), "nuclear_program_has_programme"))


class TestAvailability(unittest.TestCase):

    REQUIRED = {
        "nd_proj_icbms_available": ["nuclear_program_has_programme = yes",
                                    "var:nuclear_weapons_program_first_nuke_done ?= 1",
                                    "has_technology_researched = ICBMs",
                                    "NOT = { has_variable = nd_icbms_fielded }"],
        "nd_proj_subs_available": ["nuclear_program_has_programme = yes",
                                   "var:nuclear_weapons_program_first_nuke_done ?= 1",
                                   "has_technology_researched = advanced_submarine_technology",
                                   "has_technology_researched = guided_missiles",
                                   "any_scope_state = { is_coastal = yes }",
                                   "NOT = { has_variable = nd_subs_fielded }"],
    }

    def setUp(self):
        self.triggers = strip_comments(read(NUKE_TRIGGERS))
        self.keys = loc_keys()

    def test_each_requirement_is_its_own_line(self):
        for name, required in self.REQUIRED.items():
            with self.subTest(trigger=name):
                found, rest = tooltips(block(self.triggers, name))
                self.assertEqual(rest.strip(), "", "every test sits in a custom_tooltip")
                self.assertEqual(len(found), len(required))
                for body, test in zip(found, required):
                    flat = squash(body)
                    key = re.match(r"text = (\w+) ", flat).group(1)
                    self.assertIn(key, self.keys)
                    self.assertEqual(flat[len(f"text = {key} "):], test)

    def test_an_unavailable_focus_returns_to_warheads_weekly(self):
        pulse = strip_comments(block(read(JOURNAL), "on_weekly_pulse"))
        self.assertLess(pulse.index("nd_focus_restore = yes"), pulse.index("nd_focus_check_available = yes"))
        self.assertLess(pulse.index("nd_focus_check_available = yes"), pulse.index("nuclear_program_weekly_progress = yes"))
        body = squash(block(strip_comments(read(WEAPON_EFFECTS)), "nd_focus_check_available"))
        self.assertIn("AND = { nd_focus_is_icbms = yes NOT = { nd_proj_icbms_available = yes } }", body)
        self.assertIn("AND = { nd_focus_is_submarines = yes NOT = { nd_proj_subs_available = yes } }", body)
        self.assertIn("nd_focus_set = { F = 1 }", body)


class TestFocusHandler(unittest.TestCase):

    def setUp(self):
        self.sguis = strip_comments(read(SGUIS))
        self.handler = block(self.sguis, "nuclear_program_focus_sgui")
        self.effects = strip_comments(read(WEAPON_EFFECTS))

    def test_shape(self):
        flat = squash(self.handler)
        self.assertIn("saved_scopes = { op }", flat)
        self.assertIn("ai_is_valid = { always = no }", flat)
        self.assertIn("is_shown = { has_journal_entry = je_nuclear_program }", flat)

    def test_each_op_reads_its_availability(self):
        valid = squash(block(self.handler, "is_valid"))
        for op, trigger in ((2, "nd_proj_icbms_available"), (3, "nd_proj_subs_available")):
            branch = valid[valid.index(f"scope:op = {op} }}"):]
            self.assertIn(f"{trigger} = yes", branch[:branch.index("trigger_else")])
        effect = squash(block(self.handler, "effect"))
        for op in (1, 2, 3):
            self.assertIn(f"scope:op = {op} }} nd_focus_choose = {{ F = {op} }}", effect)

    def test_the_click_runs_behind_a_marker(self):
        body = squash(block(self.effects, "nd_focus_choose"))
        self.assertTrue(body.startswith("custom_tooltip = nd_tt_focus_set_$F$ set_variable = nd_focus_click"))
        self.assertIn("if = { limit = { has_variable = nd_focus_click } remove_variable = nd_focus_click "
                      "nd_focus_set = { F = $F$ }", body)
        for f in (1, 2, 3):
            self.assertIn(f"nd_tt_focus_set_{f}", loc_keys())

    def test_op_table_in_three_places(self):
        sgui_header = read(SGUIS)
        gui_header = read(GUI)
        doc = SYSTEMS_DOC.read_text(encoding="utf-8")
        for op, meaning in ((1, "Warheads"), (2, "ICBMs"), (3, "Missile Submarines")):
            with self.subTest(op=op):
                self.assertRegex(sgui_header, rf"#\s+{op}\s+focus {meaning}\b")
                self.assertRegex(gui_header, rf"###.*op {op}\s+focus {meaning}\b")
                self.assertRegex(doc, rf"\|\s*(`nuclear_program_focus_sgui`)?\s*\|\s*{op}\s*\|\s*focus {meaning}\s*\|")


if __name__ == "__main__":
    unittest.main()
