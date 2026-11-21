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


# ---------------------------------------------------------------------------
# Task 2: the legs follow the fielded variables (§4.2-§4.4; D7-D10, D13)
# ---------------------------------------------------------------------------
DETERRENCE_EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
TABOO_EFFECTS = ROOT / "common/scripted_effects/nuclear_taboo_effects.txt"
DETERRENCE_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
DETERRENCE_VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
DELIVERY_ON_ACTIONS = ROOT / "common/on_actions/nuclear_delivery_on_actions.txt"
ARTICLES = ROOT / "common/treaty_articles/extra_treaty_articles.txt"
MESSAGES = ROOT / "common/messages/extra_messages.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_deterrence_custom_loc.txt"
LEG_VARS = ("nd_icbms_fielded", "nd_subs_fielded", "nd_prog_focus",
            "nd_proj_warhead_progress", "nd_proj_icbm_progress", "nd_proj_sub_progress")


def every_country_blocks(body):
    """The bodies of each every_country block in an effect body."""
    found = []
    for m in re.finditer(r"every_country\s*=\s*\{", body):
        depth, j = 1, m.end()
        while depth:
            depth += body[j] == "{"
            depth -= body[j] == "}"
            j += 1
        found.append(body[m.end():j - 1])
    return found


class TestMigration(unittest.TestCase):
    """Once, on the first monthly pulse: every country that had a leg from
    its technology keeps it as fielded (plan D8, spec §4.4)."""

    def setUp(self):
        self.effects = strip_comments(read(DETERRENCE_EFFECTS))
        self.body = block(self.effects, "nd_delivery_migrate")

    def test_global_monthly_and_once(self):
        on_actions = strip_comments(read(DELIVERY_ON_ACTIONS))
        self.assertIn("on_monthly_pulse = { on_actions = { nd_delivery_monthly_on_action } }", squash(on_actions))
        hook = squash(block(on_actions, "nd_delivery_monthly_on_action"))
        self.assertIn("limit = { has_game_rule = nuclear_weapons_enabled "
                      "NOT = { has_global_variable = nd_delivery_migrated } } nd_delivery_migrate = yes", hook)
        # The flag first, so a second pulse can never run it again.
        self.assertTrue(squash(self.body).startswith("set_global_variable = nd_delivery_migrated"))

    def test_tech_and_coast_armed_or_not(self):
        icbms, subs = every_country_blocks(self.body)
        self.assertIn("has_technology_researched = ICBMs", icbms)
        self.assertIn("set_variable = { name = nd_icbms_fielded value = year }", squash(icbms))
        self.assertIn("has_technology_researched = advanced_submarine_technology", subs)
        self.assertIn("any_scope_state = { is_coastal = yes }", subs)
        self.assertIn("set_variable = { name = nd_subs_fielded value = year }", squash(subs))
        for loop in (icbms, subs):
            self.assertNotIn("nd_is_armed", loop)
            # Disarmament takes the launchers too (owner call 9).
            self.assertIn("nd_delivery_given_up = no", loop)

    def test_a_granted_leg_drops_its_project(self):
        icbms, subs = (squash(b) for b in every_country_blocks(self.body))
        self.assertIn("if = { limit = { nd_focus_is_icbms = yes } nd_focus_set = { F = 1 } }", icbms)
        self.assertIn("remove_variable = nd_proj_icbm_progress", icbms)
        self.assertIn("if = { limit = { nd_focus_is_submarines = yes } nd_focus_set = { F = 1 } }", subs)
        self.assertIn("remove_variable = nd_proj_sub_progress", subs)

    def test_given_up(self):
        body = squash(block(strip_comments(read(DETERRENCE_TRIGGERS)), "nd_delivery_given_up"))
        for part in ("has_variable = nd_renounced", "has_variable = nd_renounced_locked",
                     "modifier:country_nuclear_disarmament_bool = yes"):
            self.assertIn(part, body)

    def test_headlines_and_log(self):
        body = squash(self.body)
        self.assertIn("limit = { local_var:nd_mig_icbms > 0 } set_global_variable = nd_headline_icbms_fielded", body)
        self.assertIn("limit = { local_var:nd_mig_subs > 0 } set_global_variable = nd_headline_subs_fielded", body)
        self.assertIn("TE_NUCLEAR: type=delivery_migrated;", body)
        self.assertIn("icbms=[GetGlobalVariable('nd_mig_icbms').GetValue|0]", body)
        self.assertIn("subs=[GetGlobalVariable('nd_mig_subs').GetValue|0]", body)


class TestLegRemoval(unittest.TestCase):
    """The Nuclear Disarmament article and a completed dismantling take the
    legs, the projects and a project focus (owner call 9; plan D10)."""

    def setUp(self):
        self.body = squash(block(strip_comments(read(DETERRENCE_EFFECTS)), "nd_delivery_remove_legs"))

    def test_clears_the_legs_slots_and_focus(self):
        for var in ("nd_icbms_fielded", "nd_subs_fielded", "nd_proj_icbm_progress", "nd_proj_sub_progress"):
            self.assertIn(f"if = {{ limit = {{ has_variable = {var} }} remove_variable = {var} }}", self.body)
        # A project in focus: the live figure was the project's, so the
        # warheads' parked progress comes back to the bar.
        self.assertIn("limit = { has_variable = nd_prog_focus } remove_variable = nd_prog_focus "
                      "if = { limit = { has_variable = nd_proj_warhead_progress } "
                      "set_variable = { name = nuclear_weapon_program_progress value = var:nd_proj_warhead_progress } "
                      "remove_variable = nd_proj_warhead_progress } "
                      "else = { set_variable = { name = nuclear_weapon_program_progress value = 0 } }", self.body)
        self.assertIn("nd_authority_bind_check = yes", self.body)

    def test_both_call_sites(self):
        article = squash(strip_comments(block(read(ARTICLES), "nuclear_disarmament")))
        entry = article[article.index("on_entry_into_force"):]
        # Before the progress is zeroed: the zeroing then also clears the
        # warheads' progress the removal loaded back.
        self.assertLess(entry.index("nd_delivery_remove_legs = yes"),
                        entry.index("set_variable = { name = nuclear_weapon_program_progress value = 0 }"))
        dismantle = squash(block(strip_comments(read(TABOO_EFFECTS)), "nd_taboo_dismantle_complete"))
        self.assertLess(dismantle.index("nd_delivery_remove_legs = yes"),
                        dismantle.index("nd_apply_posture_modifiers = yes"))


class TestAuthorityBind(unittest.TestCase):
    """Launch on Warning and Automatic Retaliation need fielded ICBMs: without
    them the authority falls back to Central, and its clock isn't restarted
    (plan D10, the No-First-Strike binding's pattern)."""

    def setUp(self):
        self.effects = strip_comments(read(DETERRENCE_EFFECTS))
        self.body = squash(block(self.effects, "nd_authority_bind_check"))

    def test_the_bind(self):
        self.assertIn("AND = { nd_authority_launch_on_warning = yes NOT = { nd_can_adopt_launch_on_warning = yes } }",
                      self.body)
        self.assertIn("AND = { nd_authority_automatic = yes NOT = { nd_can_adopt_automatic_retaliation = yes } }",
                      self.body)
        self.assertIn("nd_set_authority_1 = yes", self.body)

    def test_months_put_back(self):
        save = self.body.index("set_variable = { name = nd_authority_months_before_bind value = var:nd_authority_months }")
        tenure = self.body.index("set_variable = { name = nd_authority_months_before_bind value = nd_authority_tenure_months }")
        setter = self.body.index("nd_set_authority_1 = yes")
        restore = self.body.index("set_variable = { name = nd_authority_months value = var:nd_authority_months_before_bind }")
        self.assertLess(max(save, tenure), setter)
        self.assertLess(setter, restore)
        self.assertIn("remove_variable = nd_authority_months_before_bind", self.body)

    def test_a_human_is_told(self):
        self.assertIn("limit = { is_ai = no } post_notification = nd_authority_bound_by_delivery", self.body)
        self.assertIn("nd_authority_bound_by_delivery = {", read(MESSAGES))
        keys = loc_keys()
        for suffix in ("name", "desc", "tooltip"):
            self.assertIn(f"notification_nd_authority_bound_by_delivery_{suffix}", keys)

    def test_weekly_backstop(self):
        self.assertIn("nd_authority_bind_check = yes", squash(block(self.effects, "nd_weekly_update")))

    def test_one_writer(self):
        callers = re.findall(r"\bnd_authority_bind_check\s*=\s*yes", self.effects)
        self.assertEqual(len(callers), 2)  # nd_weekly_update and nd_delivery_remove_legs


class TestCustodyAndRevolutions(unittest.TestCase):
    """Warheads taken into custody arrive without their delivery (owner call
    3), and a revolution's winner continues the nation with its variables
    (plan D13): nothing in custody or a civil war writes a leg, the focus or
    a project's progress."""

    FILES = ("common/on_actions/nuclear_custody_on_actions.txt",
             "common/on_actions/te_civil_war_on_actions.txt",
             "common/scripted_effects/nuclear_custody_effects.txt",
             "common/scripted_effects/te_civil_war_effects.txt",
             "events/nuclear_custody_events.txt")

    def test_no_writes(self):
        writes = re.compile(r"\b(set_variable|change_variable|remove_variable|clamp_variable)\s*=\s*"
                            r"(\{\s*name\s*=\s*)?(" + "|".join(LEG_VARS) + r")\b")
        for rel in self.FILES:
            code = strip_comments(read(ROOT / rel))
            self.assertIsNone(writes.search(code), rel)


class TestSubmarineUpkeep(unittest.TestCase):
    """The submarine leg is the dearest to keep: 6 × the size factor a week
    (spec §4.3, owner call 11; plan D9)."""

    def setUp(self):
        self.values = strip_comments(read(DETERRENCE_VALUES))

    def test_the_part(self):
        body = squash(block(self.values, "nd_upkeep_units_submarines"))
        self.assertEqual("value = 0 if = { limit = { nd_fields_missile_submarines = yes } "
                         "add = { value = nd_upkeep_size_factor multiply = 6 } }", body)
        self.assertIn("add = nd_upkeep_units_submarines", squash(block(self.values, "nd_upkeep_units_fixed")))

    def test_the_cap(self):
        self.assertEqual(constant(self.values, "nd_upkeep_units_cap"), 46)
        names = ["nd_upkeep_units", "nd_upkeep_weekly_at_ceiling_lowered", "nd_upkeep_weekly_at_ceiling_raised"]
        names += [f"nd_upkeep_weekly_at_readiness_{r}" for r in range(4)]
        for name in names:
            body = squash(block(self.values, name))
            self.assertIn("max = nd_upkeep_units_cap", body, name)
            self.assertNotIn("max = 40", body, name)

    def test_the_unit_table(self):
        header = read(DETERRENCE_VALUES)
        self.assertRegex(header, r"#\s+missile submarines\s+6 × size factor")
        self.assertRegex(header, r"#\s+cap\s+46 units")

    def test_a_ceiling_counts_its_own_size(self):
        # The submarines' part scales with the arsenal, so a ceiling's preview
        # takes the part at its own size, not the stockpile's.
        for name, size in (("nd_upkeep_weekly_at_ceiling_lowered", "nd_ceiling_lowered_capped"),
                           ("nd_upkeep_weekly_at_ceiling_raised", "nd_ceiling_raised_capped")):
            body = squash(block(self.values, name))
            self.assertIn("subtract = nd_upkeep_units_submarines", body, name)
            self.assertIn(f"limit = {{ nd_fields_missile_submarines = yes }} add = {{ value = {size} "
                          "divide = 50 multiply = 0.6 add = 0.4 multiply = 6 }", body, name)

    def test_the_upkeep_hover_names_it(self):
        loc = "\n".join(read(p) for p in LOC.glob("*.yml"))
        hover = re.search(r"(?m)^ nd_w_upkeep_tt:0 \"(.*)\"", loc).group(1)
        self.assertIn("GetCustom('nd_upkeep_subs_line')", hover)
        line = squash(block(strip_comments(read(CUSTOM_LOC)), "nd_upkeep_subs_line"))
        self.assertIn("trigger = { nd_fields_missile_submarines = yes } localization_key = nd_w_upkeep_subs_line", line)


# ---------------------------------------------------------------------------
# Task 3: the Focus rows, the notices and the headline (§4.1, §5.4; D11, D12)
# ---------------------------------------------------------------------------
PROGRAM_CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_program_custom_loc.txt"
OVERVIEW_GUI = ROOT / "gui/journal_entry_widgets/nuclear_overview_widget.gui"
LAYOUT_GUI = ROOT / "gui/journal_entry_widgets/nuclear_layout_widget.gui"
WEAPON_EVENTS = ROOT / "events/nuclear_weapon_events.txt"
FOCUS_NAMES = {1: "warheads", 2: "icbms", 3: "submarines"}
LEGS = {"icbms": 35, "subs": 36}


def loc_values():
    values = {}
    for path in LOC.glob("*.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r'\s+([A-Za-z0-9_.\-]+):\d*\s+"(.*)"', line)
            if m:
                values[m.group(1)] = m.group(2)
    return values


def custom_targets(name):
    """The (trigger, key) pairs of a customizable-localization block, in order."""
    body = squash(block(strip_comments(read(PROGRAM_CUSTOM_LOC)), name))
    return re.findall(r"text = \{ trigger = \{ (.*?) \} localization_key = (\w+) \}", body)


class TestFocusRows(unittest.TestCase):
    """Three choice rows in The Programme, from the first device on, the focus
    in force tinted, each printing its progress and its months to finish at
    current funding (plan D11)."""

    def setUp(self):
        gui = strip_comments(read(GUI))
        self.section = gui[gui.index("type te_nuclear_sec_programme"):gui.index("type te_nuclear_sec_taboo")]
        self.values = strip_comments(read(EXTRA_VALUES))
        self.loc = loc_values()

    def test_three_rows_behind_the_first_device(self):
        gate = "GetScriptedGui('nuclear_program_first_device_sgui').IsShown"
        self.assertIn(gate, self.section)
        rows = self.section[self.section.index(gate):]
        self.assertEqual(rows.count("nd_choice_row = {"), 3)
        for op in (1, 2, 3):
            with self.subTest(op=op):
                self.assertIn(f"ScriptValue('nd_display_prog_focus'), '(CFixedPoint){op}'", rows)
                self.assertIn(f"MakeScopeValue( '(CFixedPoint){op}' )", rows)
                self.assertIn(f'text = "nd_w_focus_row_{op}"', rows)
                self.assertIn(f'tooltip = "nd_w_focus_{op}_tt"', rows)
        self.assertEqual(rows.count("GetScriptedGui('nuclear_program_focus_sgui')"), 3)
        sgui = squash(block(strip_comments(read(SGUIS)), "nuclear_program_first_device_sgui"))
        self.assertIn("is_shown = { var:nuclear_weapons_program_first_nuke_done ?= 1 }", sgui)
        self.assertIn("ai_is_valid = { always = no }", sgui)

    def test_the_focus_in_force_as_a_code(self):
        body = squash(block(self.values, "nd_display_prog_focus"))
        self.assertTrue(body.startswith("value = 1 if = { limit = { has_variable = nd_prog_focus } value = var:nd_prog_focus }"))

    def test_progress_reads_the_live_figure_and_the_slot(self):
        for f, slot in SLOTS.items():
            with self.subTest(focus=f):
                body = squash(block(self.values, f"nd_display_proj_progress_{f}"))
                self.assertIn(f"limit = {{ nd_focus_is_{FOCUS_NAMES[f]} = yes has_variable = {LIVE} }} add = var:{LIVE}", body)
                self.assertIn(f"limit = {{ has_variable = {slot} }} add = var:{slot}", body)
                self.assertIn("max = nuclear_weapon_program_goal_value", body)
                share = squash(block(self.values, f"nd_display_proj_share_{f}"))
                self.assertEqual(share, f"value = nd_display_proj_progress_{f} divide = nuclear_weapon_program_goal_value")

    def test_months_at_each_focus_rate(self):
        warheads = squash(block(self.values, "nd_display_proj_monthly_1"))
        self.assertIn("multiply = nuclear_weapon_program_additional_nuke_progress_multiplier", warheads)
        self.assertIn("add = modifier:country_nuclear_program_progress_mult", warheads)
        project = squash(block(self.values, "nd_display_proj_monthly_project"))
        self.assertNotIn("additional_nuke_progress_multiplier", project)
        self.assertIn("add = modifier:country_nuclear_program_progress_mult", project)
        for f, rate in ((1, "nd_display_proj_monthly_1"), (2, "nd_display_proj_monthly_project"),
                        (3, "nd_display_proj_monthly_project")):
            with self.subTest(focus=f):
                body = squash(block(self.values, f"nd_display_proj_months_{f}"))
                self.assertIn("nuclear_program_display_progressing = yes", body)
                self.assertIn(f"{rate} > 0", body)
                self.assertIn(f"subtract = nd_display_proj_progress_{f} divide = {rate}", body)
        progressing = squash(block(strip_comments(read(NUKE_TRIGGERS)), "nuclear_program_display_progressing"))
        for clause in ("var:nuclear_weapons_program_funding >= 1",
                       "NOT = { modifier:country_nuclear_program_pause_bool = yes }",
                       "NOT = { modifier:country_nuclear_disarmament_bool = yes }"):
            self.assertIn(clause, progressing)

    def test_each_row_says_what_holds_it(self):
        warheads = custom_targets("nd_focus_row_1")
        self.assertIn("nd_focus_is_warheads = no nd_taboo_has_ceiling = yes", warheads[0][0])
        self.assertEqual([k for _, k in warheads], ["nd_focus_row_1_held", "nd_focus_row_1_months", "nd_focus_row_1_stalled"])
        for f, leg, var in ((2, "icbms", "nd_icbms_fielded"), (3, "subs", "nd_subs_fielded")):
            with self.subTest(focus=f):
                targets = custom_targets(f"nd_focus_row_{f}")
                self.assertEqual([k for _, k in targets], [f"nd_focus_row_{f}_{s}" for s in
                                                          ("fielded", "unavailable", "months", "stalled")])
                self.assertEqual(targets[0][0], f"has_variable = {var}")
                self.assertEqual(targets[1][0], f"nd_proj_{leg}_available = no")
        for f in (1, 2, 3):
            self.assertEqual(self.loc[f"nd_w_focus_row_{f}"], f"[Country.GetCustom('nd_focus_row_{f}')]")
            self.assertIn(f"ScriptValue('nd_display_proj_share_{f}')|%0", self.loc[f"nd_focus_row_{f}_months"])
            self.assertIn(f"ScriptValue('nd_display_proj_months_{f}')|0", self.loc[f"nd_focus_row_{f}_months"])

    def test_the_rows_fit(self):
        from test_nuclear_layout import MARGIN, ROW, _renderings
        for f in (1, 2, 3):
            for text in _renderings(f"nd_w_focus_row_{f}"):
                self.assertLessEqual(len(text) * ROW * MARGIN, 358, text)

    def test_the_header_names_the_rows(self):
        self.assertNotIn("its rows come with", read(GUI))
        self.assertIn("the Focus rows", read(GUI))


class TestProgrammeFollowsFocus(unittest.TestCase):
    """The rate and time rows, the bar's label and the status codes follow the
    focus, and a click shows the new state at once (plan D11)."""

    def setUp(self):
        self.loc = loc_values()
        self.effects = strip_comments(read(WEAPON_EFFECTS))

    def test_labels_follow_the_focus(self):
        for key, custom in (("je_nuclear_program_widget_rate_label", "nd_prog_rate_label"),
                            ("je_nuclear_program_widget_next_label", "nd_prog_next_label")):
            self.assertEqual(self.loc[key], f"[Country.GetCustom('{custom}')]")
            triggers = [t for t, _ in custom_targets(custom)]
            self.assertEqual(triggers, ["nd_focus_is_icbms = yes", "nd_focus_is_submarines = yes", "always = yes"])
        for key in ("je_nuclear_program_widget_rate_tt", "je_nuclear_program_widget_next_tt"):
            self.assertIn("GetCustom('nd_prog_focus_object')", self.loc[key])
        self.assertNotIn("a warhead takes", self.loc["je_nuclear_program_widget_next_tt"])

    def test_the_bar_says_what_it_builds(self):
        journal = squash(strip_comments(read(JOURNAL)))
        self.assertIn("progress_desc = je_nuclear_program_progress", journal)
        self.assertIn("ROOT.GetCountry.GetCustom('nd_prog_focus_object')", self.loc["je_nuclear_program_progress"])
        # Accessor-free, so the entry's desc root and the widget's both read it.
        for _, key in custom_targets("nd_prog_focus_object"):
            self.assertNotIn("[", self.loc[key])

    def test_the_rate_note_names_the_projects_rate(self):
        keys = [k for _, k in custom_targets("nuclear_program_rate_note")]
        self.assertLess(keys.index("nuclear_program_rate_note_project"), keys.index("nuclear_program_rate_note_series"))
        self.assertIn("additional_nuke_progress_multiplier", self.loc["nuclear_program_rate_note_project"])

    def test_status_codes(self):
        body = squash(block(self.effects, "nuclear_program_refresh_state_effect"))
        self.assertIn("limit = { nd_taboo_programme_should_be_held = yes } set_variable = { name = nuclear_program_last_status value = 4 }", body)
        self.assertNotIn("has_modifier = nd_taboo_programme_held", body)
        self.assertNotIn("modifier:country_nuclear_program_pause_bool", body)
        self.assertIn("limit = { nuclear_program_is_frozen = yes } set_variable = { name = nuclear_program_last_status value = 3 }", body)
        self.assertIn("limit = { nd_focus_is_icbms = yes } set_variable = { name = nuclear_program_last_status value = 9 }", body)
        self.assertIn("limit = { nd_focus_is_submarines = yes } set_variable = { name = nuclear_program_last_status value = 10 }", body)
        self.assertLess(body.index("value = 0 }"), body.index("value = 9 }"))
        frozen = squash(block(strip_comments(read(NUKE_TRIGGERS)), "nuclear_program_is_frozen"))
        for source in ("has_modifier = nd_crisis_programme_freeze", "has_modifier = nuclear_program_debug_pause",
                       "has_type = nuclear_program_pause"):
            self.assertIn(source, frozen)

    def test_a_click_refreshes_the_status(self):
        body = squash(block(self.effects, "nd_focus_choose"))
        self.assertIn("nd_focus_set = { F = $F$ } nuclear_program_refresh_state_effect = yes", body)

    def test_the_overview_and_the_status_line_know_the_projects(self):
        overview = read(OVERVIEW_GUI)
        for code in (9, 10):
            with self.subTest(code=code):
                self.assertIn(f"ScriptValue('nuclear_program_display_state'), '(CFixedPoint){code}' )]\"\n"
                              "\t\t\t\t\t\t\t\t\ttexture = \"gfx/interface/icons/nuclear_icons/programme_developing.dds\"",
                              overview)
                self.assertIn(f"text = \"je_nuclear_ov_prog_{code}\"", overview)
                self.assertTrue(self.loc[f"je_nuclear_ov_prog_{code}"])
        status = custom_targets("nuclear_program_status_line")
        for code, key in ((9, "nuclear_program_status_project_icbms"), (10, "nuclear_program_status_project_subs")):
            self.assertIn((f"has_variable = nuclear_program_last_status var:nuclear_program_last_status = {code}", key), status)
        short = custom_targets("nuclear_program_next_short")
        self.assertEqual([k for _, k in short], ["nuclear_program_next_short_estimate", "nuclear_program_next_short_project",
                                                  "nuke_line_empty", "nuclear_program_next_warhead_stalled"])
        self.assertIn("nuclear_program_display_state >= 9", short[1][0])
        self.assertIn("nuclear_program_display_state <= 8", short[2][0])


class TestNotices(unittest.TestCase):
    """A leg fielded is public: the fielder hears at once, its rivals either
    way, the countries believed armed and its neighbors a week later; the
    world's first fielder of each leg also makes a headline (plan D12)."""

    def setUp(self):
        self.effects = strip_comments(read(WEAPON_EFFECTS))
        self.events = strip_comments(read(WEAPON_EVENTS))
        self.loc = loc_values()

    def test_field_leg_sends_them_last(self):
        body = squash(block(self.effects, "nd_field_leg"))
        self.assertTrue(body.endswith("nd_leg_notices_$LEG$ = yes"), body[-200:])

    def test_recipients(self):
        for leg, event in LEGS.items():
            with self.subTest(leg=leg):
                body = block(self.effects, f"nd_leg_notices_{leg}")
                flat = squash(body)
                self.assertTrue(flat.startswith("save_scope_as = nd_leg_fielder"))
                self.assertIn(f"trigger_event = {{ id = nuclear_weapon_events.{event} }}", flat)
                (world,) = every_country_blocks(body.split("post_notification")[-1]) or [None]
                world = squash(world)
                for clause in ("NOT = { THIS = scope:nd_leg_fielder }", "NOT = { is_country_type = decentralized }",
                               "any_rival_country = { THIS = scope:nd_leg_fielder }",
                               "any_rivaling_country = { THIS = scope:nd_leg_fielder }",
                               "nd_believed_armed = yes",
                               "any_neighbouring_state = { owner = scope:nd_leg_fielder }"):
                    self.assertIn(clause, world)
                self.assertIn(f"trigger_event = {{ id = nuclear_weapon_events.{event} days = 7 }}", world)

    def test_the_headline_once_per_leg(self):
        messages = strip_comments(read(MESSAGES))
        migration = strip_comments(read(DETERRENCE_EFFECTS))
        for leg in LEGS:
            with self.subTest(leg=leg):
                flat = squash(block(self.effects, f"nd_leg_notices_{leg}"))
                self.assertIn(f"limit = {{ NOT = {{ has_global_variable = nd_headline_{leg}_fielded }} }} "
                              f"set_global_variable = nd_headline_{leg}_fielded "
                              f"every_country = {{ limit = {{ is_ai = no }} post_notification = headlines_nd_{leg}_fielded }}",
                              flat)
                self.assertIn(f"set_global_variable = nd_headline_{leg}_fielded", migration)
                self.assertIn("group = \"headlines_tech_group\"", block(messages, f"headlines_nd_{leg}_fielded"))
                for part in ("name", "desc", "tooltip"):
                    self.assertIn(f"notification_headlines_nd_{leg}_fielded_{part}", self.loc)
                self.assertIn("SCOPE.sCountry('nd_leg_fielder')", self.loc[f"notification_headlines_nd_{leg}_fielded_desc"])

    def test_the_events(self):
        for leg, event in LEGS.items():
            with self.subTest(leg=leg):
                body = block(self.events, f"nuclear_weapon_events.{event}")
                flat = squash(body)
                self.assertRegex(flat, r'event_image = \{ texture = "gfx/event_pictures/\w+\.dds" \}')
                self.assertIn("trigger = { THIS = scope:nd_leg_fielder }", flat)
                for part in ("t", "d_own", "d_world", "f", "a", "b"):
                    self.assertIn(f"nuclear_weapon_events.{event}.{part}", self.loc)
                self.assertEqual(flat.count("option = {"), 2)
                self.assertEqual(flat.count("default_option = yes"), 2)
                self.assertNotRegex(flat, r"nd_taboo_\w+ = yes|change_global_variable")


class TestCeilingSaysWarheadsOnly(unittest.TestCase):
    """An arsenal ceiling holds warheads, not a delivery project (phase 1's
    Task 6 deferred the line here; spec §5.3)."""

    def test_the_ceiling_hover(self):
        loc = loc_values()
        hover = loc["nd_taboo_w_ceiling_tt"]
        self.assertNotIn("the program builds nothing", hover)
        self.assertIn("no warheads", hover)
        self.assertIn("delivery project", hover)
        self.assertIn("Warhead production is held", loc["nuclear_program_status_held"])
        self.assertIn("delivery project", loc["je_nuclear_how_programme"])
        self.assertIn("focus", loc["je_nuclear_how_programme"])


# ---------------------------------------------------------------------------
# Task 4: the AI's focus (§4.5, owner call 12; D14, D15)
# ---------------------------------------------------------------------------
BUTTONS = ROOT / "common/scripted_buttons/nuclear_program_buttons.txt"
# The log's reason words, in the order §4.5 tries them (the tie rule's two
# outcomes sit where steps 3 and 4 meet).
AI_FOCUS_REASONS = ("range_first", "range_urgent", "warheads_short", "tie_range",
                    "tie_submarines", "range_half", "submarines_survival", "range_some", "warheads")


class TestRangeScore(unittest.TestCase):
    """How much the bombers miss: the weighted share of the countries the AI
    must be able to strike that nd_reaches_country does not reach, 0 when there
    are none (spec §4.5, owner call 12; plan D14)."""

    def setUp(self):
        self.values = strip_comments(read(DETERRENCE_VALUES))
        self.triggers = strip_comments(read(DETERRENCE_TRIGGERS))
        self.effect = strip_comments(block(strip_comments(read(DETERRENCE_EFFECTS)), "nd_ai_choose_focus"))

    def test_the_weights(self):
        self.assertEqual(constant(self.values, "nd_ai_range_weight_must"), 3)
        self.assertEqual(constant(self.values, "nd_ai_range_weight_should"), 2)

    def test_who_must_be_reached(self):
        must = squash(block(self.triggers, "nd_ai_range_must_reach"))
        self.assertIn("NOT = { THIS = $AI$ }", must)
        for part in ("$AI$ = { any_rival_country = { THIS = scope:nd_rw_cand } }",
                     "$AI$ = { any_rivaling_country = { THIS = scope:nd_rw_cand } }",
                     "has_war_with = $AI$",
                     "$AI$ = { nd_in_crisis = yes var:nd_crisis_opponent ?= scope:nd_rw_cand }"):
            self.assertIn(part, must)
        # A rival, an enemy or the crisis opponent counts armed or not.
        self.assertNotIn("nd_believed_armed", must)
        should = squash(block(self.triggers, "nd_ai_range_should_reach"))
        self.assertIn("NOT = { THIS = $AI$ }", should)
        self.assertIn("nd_believed_armed = yes", should)
        self.assertIn("has_attitude = { who = $AI$ attitude = antagonistic }", should)

    def test_reach_is_nd_reaches_country(self):
        out = squash(block(self.triggers, "nd_ai_range_out_of_reach"))
        self.assertIn("save_temporary_scope_as = nd_ro_cand", out)
        self.assertIn("$AI$ = { NOT = { nd_reaches_country = { TARGET = scope:nd_ro_cand } } }", out)

    def test_the_highest_weight_per_country(self):
        body = squash(self.effect)
        walk = squash(every_country_blocks(self.effect)[0])
        self.assertTrue(walk.startswith("limit = { OR = { nd_ai_range_must_reach = { AI = scope:nd_rf_self } "
                                        "nd_ai_range_should_reach = { AI = scope:nd_rf_self } } }"))
        self.assertIn("if = { limit = { nd_ai_range_must_reach = { AI = scope:nd_rf_self } } "
                      "set_local_variable = { name = nd_rf_weight value = nd_ai_range_weight_must } } "
                      "else = { set_local_variable = { name = nd_rf_weight value = nd_ai_range_weight_should } }", walk)
        self.assertIn("change_local_variable = { name = nd_rf_total add = local_var:nd_rf_weight }", walk)
        self.assertIn("limit = { nd_ai_range_out_of_reach = { AI = scope:nd_rf_self } } "
                      "change_local_variable = { name = nd_rf_missed add = local_var:nd_rf_weight }", walk)
        # Every sum starts at 0 before the walk.
        for name in ("nd_rf_total", "nd_rf_missed", "nd_rf_inland", "nd_rf_coastal", "nd_rf_urgent"):
            self.assertLess(body.index(f"set_local_variable = {{ name = {name} value = 0 }}"),
                            body.index("every_country"))

    def test_zero_with_none(self):
        body = squash(self.effect)
        self.assertIn("set_variable = { name = nd_ai_range_score value = 0 } "
                      "if = { limit = { local_var:nd_rf_total > 0 } "
                      "set_variable = { name = nd_ai_range_score value = local_var:nd_rf_missed } "
                      "change_variable = { name = nd_ai_range_score divide = local_var:nd_rf_total } }", body)


class TestFocusOrder(unittest.TestCase):
    """§4.5's six steps, its tie rule and the India-Pakistan rule: a score of
    0 never builds range (plan D14)."""

    def setUp(self):
        self.effects = strip_comments(read(DETERRENCE_EFFECTS))
        self.effect = block(self.effects, "nd_ai_choose_focus")
        self.body = squash(self.effect)
        self.order = self.body[self.body.index("set_local_variable = { name = nd_rf_want_subs value = 0 }"):]

    def test_called_from_the_review(self):
        review = squash(block(self.effects, "nd_ai_review_posture"))
        self.assertIn("nd_ai_choose_focus = yes", review)
        # After the review's rival refresh, which the submarine test reads.
        self.assertLess(review.index("nd_refresh_main_rival = yes"), review.index("nd_ai_choose_focus = yes"))

    def test_only_after_the_first_device(self):
        self.assertTrue(self.body.startswith(
            "if = { limit = { var:nuclear_weapons_program_first_nuke_done ?= 1 } save_scope_as = nd_rf_self"))

    def test_six_steps_in_order(self):
        positions = [self.order.index(f"REASON = {reason} ") for reason in AI_FOCUS_REASONS]
        self.assertEqual(positions, sorted(positions))

    def test_each_step_s_test(self):
        o = self.order
        has_range = "local_var:nd_rf_range > 0"
        # 1. Range first when the bombers reach nobody who matters.
        self.assertIn(f"if = {{ limit = {{ {has_range} var:nd_ai_range_score >= 1 }} "
                      "nd_ai_focus_pick_range = { REASON = range_first } }", o)
        # 2. Warheads below half the desired stockpile, unless at war or in a
        # crisis with a country out of reach.
        self.assertIn("else_if = { limit = { has_variable = nuclear_weapon_stockpile "
                      "var:nuclear_weapon_stockpile < nd_ai_focus_warheads_first } "
                      f"if = {{ limit = {{ {has_range} local_var:nd_rf_urgent > 0 }} "
                      "nd_ai_focus_pick_range = { REASON = range_urgent } } "
                      "else = { nd_ai_focus_pick = { F = 1 REASON = warheads_short } } }", o)
        # 3 and 4 together: the tie rule.
        self.assertIn(f"else_if = {{ limit = {{ {has_range} var:nd_ai_range_score >= nd_ai_range_score_for_range "
                      "local_var:nd_rf_want_subs = 1 } "
                      "if = { limit = { local_var:nd_rf_urgent > 0 } nd_ai_focus_pick_range = { REASON = tie_range } } "
                      "else = { nd_ai_focus_pick = { F = 3 REASON = tie_submarines } } }", o)
        # 3. Range at half the score or more.
        self.assertIn(f"else_if = {{ limit = {{ {has_range} var:nd_ai_range_score >= nd_ai_range_score_for_range }} "
                      "nd_ai_focus_pick_range = { REASON = range_half } }", o)
        # 4. Submarines for survival.
        self.assertIn("else_if = { limit = { local_var:nd_rf_want_subs = 1 } "
                      "nd_ai_focus_pick = { F = 3 REASON = submarines_survival } }", o)
        # 5. Range when the score is above 0.
        self.assertIn(f"else_if = {{ limit = {{ {has_range} var:nd_ai_range_score > 0 }} "
                      "nd_ai_focus_pick_range = { REASON = range_some } }", o)
        # 6. Otherwise warheads.
        self.assertIn("else = { nd_ai_focus_pick = { F = 1 REASON = warheads } }", o)

    def test_the_constants(self):
        values = strip_comments(read(DETERRENCE_VALUES))
        self.assertEqual(constant(values, "nd_ai_range_score_for_range"), 0.5)
        self.assertEqual(constant(values, "nd_ai_focus_warheads_share"), 0.5)
        first = squash(block(values, "nd_ai_focus_warheads_first"))
        self.assertEqual(first, "value = nuclear_ai_desired_stockpile multiply = nd_ai_focus_warheads_share")

    def test_never_range_at_zero(self):
        # Every range pick but the urgent one tests the score above 0 (1, 0.5
        # or > 0); an urgent country is out of reach, so its score is above 0.
        picks = re.findall(r"nd_ai_focus_pick_range = \{", self.order)
        self.assertEqual(len(picks), 5)
        walk = squash(every_country_blocks(self.effect)[0])
        missed = walk[walk.index("limit = { nd_ai_range_out_of_reach"):]
        self.assertIn("if = { limit = { nd_ai_range_urgent = { AI = scope:nd_rf_self } } "
                      "change_local_variable = { name = nd_rf_urgent add = 1 } }", missed)

    def test_submarines_as_range_only_with_every_coast(self):
        body = self.body
        self.assertIn("set_local_variable = { name = nd_rf_range value = 0 } "
                      "if = { limit = { nd_proj_subs_available = yes local_var:nd_rf_coastal > 0 "
                      "OR = { local_var:nd_rf_inland = 0 NOT = { nd_proj_icbms_available = yes } } } "
                      "set_local_variable = { name = nd_rf_range value = 3 } } "
                      "else_if = { limit = { nd_proj_icbms_available = yes } "
                      "set_local_variable = { name = nd_rf_range value = 2 } }", body)
        walk = squash(every_country_blocks(self.effect)[0])
        self.assertIn("if = { limit = { any_scope_state = { is_coastal = yes } } "
                      "change_local_variable = { name = nd_rf_coastal add = 1 } } "
                      "else = { change_local_variable = { name = nd_rf_inland add = 1 } }", walk)

    def test_submarines_for_survival(self):
        self.assertIn("if = { limit = { nd_proj_subs_available = yes OR = { "
                      "nd_ai_vulnerable_to_main_rival = yes "
                      "AND = { has_variable = nd_main_rival_accuracy_mult var:nd_main_rival_accuracy_mult > 1 } } } "
                      "set_local_variable = { name = nd_rf_want_subs value = 1 } }", self.body)

    def test_the_urgent_test(self):
        urgent = squash(block(strip_comments(read(DETERRENCE_TRIGGERS)), "nd_ai_range_urgent"))
        self.assertIn("save_temporary_scope_as = nd_ru_cand", urgent)
        self.assertIn("has_war_with = $AI$", urgent)
        self.assertIn("$AI$ = { nd_in_crisis = yes var:nd_crisis_opponent ?= scope:nd_ru_cand }", urgent)

    def test_the_focus_set_through_nd_focus_set(self):
        self.assertNotIn("nd_prog_focus", self.body)
        pick = squash(block(self.effects, "nd_ai_focus_pick"))
        self.assertIn("nd_focus_set = { F = $F$ }", pick)
        # Only a change: an unchanged focus parks and reloads nothing.
        self.assertIn("AND = { local_var:nd_rf_pick = 1 NOT = { nd_focus_is_warheads = yes } } "
                      "AND = { local_var:nd_rf_pick = 2 NOT = { nd_focus_is_icbms = yes } } "
                      "AND = { local_var:nd_rf_pick = 3 NOT = { nd_focus_is_submarines = yes } }", pick)
        pick_range = squash(block(self.effects, "nd_ai_focus_pick_range"))
        self.assertIn("if = { limit = { local_var:nd_rf_range = 3 } nd_ai_focus_pick = { F = 3 REASON = $REASON$ } } "
                      "else = { nd_ai_focus_pick = { F = 2 REASON = $REASON$ } }", pick_range)


class TestFundingAiChance(unittest.TestCase):
    """A project in focus is a reason to fund, never a reason to stop at the
    desired stockpile (spec §4.5's last paragraph; plan D15)."""

    def setUp(self):
        buttons = strip_comments(read(BUTTONS))
        self.up = squash(block(block(buttons, "increase_funding_nuclear_program"), "ai_chance"))
        self.down = squash(block(block(buttons, "decrease_funding_nuclear_program"), "ai_chance"))

    def test_plus_35_with_a_project(self):
        self.assertIn("if = { limit = { nd_focus_is_project = yes } add = 35 }", self.up)
        trigger = squash(block(strip_comments(read(NUKE_TRIGGERS)), "nd_focus_is_project"))
        self.assertEqual(trigger, "has_variable = nd_prog_focus")

    def test_the_stockpile_terms_skipped_then(self):
        self.assertIn("limit = { var:nuclear_weapon_stockpile >= nuclear_ai_desired_stockpile "
                      "nd_focus_is_warheads = yes } add = -45", self.up)
        self.assertIn("limit = { var:nuclear_weapon_stockpile >= nuclear_ai_desired_stockpile "
                      "nd_focus_is_warheads = yes } add = 35", self.down)
        self.assertIn("limit = { var:nuclear_weapon_stockpile > nuclear_ai_desired_stockpile "
                      "nd_focus_is_warheads = yes } add = 15", self.down)

    def test_the_cap_is_focus_aware(self):
        self.assertIn("limit = { nuclear_program_ai_at_stockpile_cap = yes } multiply = 0", self.up)
        cap = squash(block(strip_comments(read(NUKE_TRIGGERS)), "nuclear_program_ai_at_stockpile_cap"))
        self.assertIn("nd_focus_is_warheads = yes", cap)


class TestAiFocusLog(unittest.TestCase):
    """Each review logs its score and the focus it chose, for observer
    balancing (spec §4.5; plan D14)."""

    def test_the_line(self):
        pick = squash(block(strip_comments(read(DETERRENCE_EFFECTS)), "nd_ai_focus_pick"))
        line = re.search(r'debug_log = "(TE_NUCLEAR: type=ai_focus;[^"]*)"', pick)
        self.assertIsNotNone(line)
        for field in ("date=[TimeKeeper.GetCurrentDate.GetString]",
                      "country=[THIS.GetCountry.GetNameNoFormatting]",
                      "score=[THIS.Var('nd_ai_range_score').GetValue|2]",
                      "focus=$F$", "reason=$REASON$",
                      "stockpile=[THIS.Var('nuclear_weapon_stockpile').GetValue|0]",
                      "desired=[THIS.ScriptValue('nuclear_ai_desired_stockpile')|0]"):
            self.assertIn(field, line.group(1))
        # Logged on every review, the focus changed or not.
        self.assertGreater(pick.index("debug_log"), pick.index("nd_focus_set = { F = $F$ }"))

    def test_the_observer_report_counts_it(self):
        from scripts.analysis.nuclear_observer_report import read_records, summarize
        lines = ["[x] TE_NUCLEAR: type=ai_focus; country=A; score=1.00; focus=2; reason=range_first",
                 "[x] TE_NUCLEAR: type=ai_focus; country=B; score=0.00; focus=1; reason=warheads",
                 "[x] TE_NUCLEAR: type=ai_focus; country=C; score=0.40; focus=3; reason=submarines_survival",
                 "[x] TE_NUCLEAR: type=ai_focus; country=D; score=0.00; focus=1; reason=warheads",
                 "[x] TE_NUCLEAR: type=leg_fielded; country=A; leg=icbms"]
        summary = summarize(read_records(lines))
        self.assertEqual(summary["ai_focus_choices"], {"icbms": 1, "submarines": 1, "warheads": 2})
        self.assertEqual(summary["ai_focus_reasons"],
                         {"range_first": 1, "submarines_survival": 1, "warheads": 2})
        self.assertEqual(summary["legs_fielded"], {"icbms": 1})

    def test_every_reason_is_a_known_word(self):
        body = squash(block(strip_comments(read(DETERRENCE_EFFECTS)), "nd_ai_choose_focus"))
        found = set(re.findall(r"REASON = (\w+)", body))
        self.assertEqual(found, set(AI_FOCUS_REASONS))


if __name__ == "__main__":
    unittest.main()
