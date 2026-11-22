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

from test_nuclear_delivery import constant, figure
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
        outer = squash(block(self.effects, "nd_focus_set"))
        self.assertEqual(outer, "nd_focus_set_core = { F = $F$ } nd_taboo_refresh_held = yes "
                                "set_local_variable = { name = nd_focus_hold_refreshed value = 1 }")
        body = block(self.effects, "nd_focus_set_core")
        self.assertNotIn("nd_taboo_refresh_held", body)
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
                                    "has_global_variable = nd_delivery_migrated",
                                    "var:nuclear_weapons_program_first_nuke_done ?= 1",
                                    "has_technology_researched = ICBMs",
                                    "NOT = { has_variable = nd_icbms_fielded }"],
        "nd_proj_subs_available": ["nuclear_program_has_programme = yes",
                                   "has_global_variable = nd_delivery_migrated",
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
        self.assertIn("AND = { nd_focus_is_icbms = yes NOT = { nd_proj_icbms_lasting = yes } }", body)
        self.assertIn("AND = { nd_focus_is_submarines = yes NOT = { nd_proj_subs_lasting = yes } }", body)
        self.assertIn("nd_focus_set = { F = 1 }", body)

    def test_the_weekly_check_reads_only_the_lasting_requirements(self):
        """Lost standing holds a project in focus, it doesn't move it (spec
        §4.1, §4.4; the 2a review): the weekly check's triggers are the
        available ones less the programme and the migration lines."""
        for leg in ("icbms", "subs"):
            with self.subTest(leg=leg):
                lasting = squash(block(self.triggers, f"nd_proj_{leg}_lasting"))
                required = self.REQUIRED[f"nd_proj_{leg}_available"]
                self.assertEqual(lasting, " ".join(required[2:]))
                self.assertNotIn("nuclear_program_has_programme", lasting)


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
        self.assertIn("set_variable = { name = nd_icbms_fielded value = 0 }", squash(icbms))
        self.assertIn("has_technology_researched = advanced_submarine_technology", subs)
        self.assertIn("any_scope_state = { is_coastal = yes }", subs)
        self.assertIn("set_variable = { name = nd_subs_fielded value = 0 }", squash(subs))
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
                         "add = nd_upkeep_units_submarines_fielded }", body)
        self.assertEqual(squash(block(self.values, "nd_upkeep_units_submarines_fielded")),
                         "value = nd_upkeep_size_factor multiply = 6")
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
        # Held whatever the focus: at the ceiling it is why every row stands
        # still (the 2a review).
        self.assertEqual(warheads[0][0], "nd_taboo_has_ceiling = yes nd_stockpile >= nd_taboo_effective_ceiling_value")
        self.assertEqual([k for _, k in warheads], ["nd_focus_row_1_held", "nd_focus_row_1_months", "nd_focus_row_1_stalled"])
        icbms = custom_targets("nd_focus_row_2")
        self.assertEqual([k for _, k in icbms], ["nd_focus_row_2_fielded_before", "nd_focus_row_2_fielded",
                                                  "nd_focus_row_2_unavailable", "nd_focus_row_2_months",
                                                  "nd_focus_row_2_stalled"])
        self.assertEqual(icbms[0][0], "var:nd_icbms_fielded ?= 0")
        self.assertEqual(icbms[1][0], "has_variable = nd_icbms_fielded")
        self.assertEqual(icbms[2][0], "nd_proj_icbms_available = no")
        subs = custom_targets("nd_focus_row_3")
        self.assertEqual([k for _, k in subs], ["nd_focus_row_3_lapsed", "nd_focus_row_3_fielded_before",
                                                 "nd_focus_row_3_fielded", "nd_focus_row_3_unavailable",
                                                 "nd_focus_row_3_months", "nd_focus_row_3_stalled"])
        # A leg with no coast left has lapsed (spec §4.3), before "at sea".
        self.assertEqual(subs[0][0], "has_variable = nd_subs_fielded nd_fields_missile_submarines = no")
        self.assertEqual(subs[1][0], "var:nd_subs_fielded ?= 0")
        self.assertEqual(subs[2][0], "has_variable = nd_subs_fielded")
        self.assertEqual(subs[3][0], "nd_proj_subs_available = no")
        for key in ("nd_focus_row_2_fielded_before", "nd_focus_row_3_fielded_before"):
            self.assertNotIn("GetValue", self.loc[key], "a migrated leg holds 0, not a year")
        for f in (1, 2, 3):
            self.assertEqual(self.loc[f"nd_w_focus_row_{f}"], f"[Country.GetCustom('nd_focus_row_{f}')]")
            self.assertIn(f"ScriptValue('nd_display_proj_share_{f}')|%0", self.loc[f"nd_focus_row_{f}_months"])
            # Tenths, as the time row: under a month never reads 0 (the 2a review).
            self.assertIn(f"ScriptValue('nd_display_proj_months_{f}')|1", self.loc[f"nd_focus_row_{f}_months"])

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
        # 4's timing: TestReviewFixes2a.test_status_4_follows_the_hold_in_force.
        self.assertIn("set_variable = { name = nuclear_program_last_status value = 4 }", body)
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
                # .35's flavor splits as its text does (the 2a review).
                flavors = ("f_own", "f_world") if event == 35 else ("f",)
                for part in ("t", "d_own", "d_own_held", "d_world", "a", "b") + flavors:
                    self.assertIn(f"nuclear_weapon_events.{event}.{part}", self.loc)
                self.assertEqual(flat.count("option = {"), 2)
                self.assertEqual(flat.count("default_option = yes"), 2)
                # Nothing writes the taboo's ledger. The fielder's text reads
                # the ceiling's triggers, which write nothing.
                effects = flat.replace(squash(block(body, "desc")), "")
                self.assertNotRegex(effects, r"nd_taboo_\w+ = yes|change_global_variable")


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

    def test_only_after_the_first_device_and_with_a_programme(self):
        # Lost standing leaves a project in focus waiting, not re-chosen (the
        # 2a review; spec §4.4).
        self.assertTrue(self.body.startswith(
            "if = { limit = { var:nuclear_weapons_program_first_nuke_done ?= 1 "
            "nuclear_program_has_programme = yes } save_scope_as = nd_rf_self"))

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
        # crisis with a country out of reach, and never while a ceiling would
        # hold them: arms control binds warheads only, so the walk goes on to
        # delivery (the 2a review; spec §2).
        self.assertIn("else_if = { limit = { has_variable = nuclear_weapon_stockpile "
                      "var:nuclear_weapon_stockpile < nd_ai_focus_warheads_first "
                      "NOT = { AND = { nd_taboo_has_ceiling = yes "
                      "nd_stockpile >= nd_taboo_effective_ceiling_value } } } "
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

    def test_the_focus_set_through_nd_focus_set_core(self):
        self.assertNotIn("nd_prog_focus", self.body)
        pick = squash(block(self.effects, "nd_ai_focus_pick"))
        # The core, without the hold's refresh: the review runs inside the
        # monthly pulse whose taboo half refreshes the hold once (the 2a
        # review: a second refresh in one block adds the hold twice).
        self.assertIn("nd_focus_set_core = { F = $F$ }", pick)
        self.assertNotIn("nd_focus_set = {", pick)
        self.assertNotIn("nd_taboo_refresh_held", pick)
        self.assertNotIn("nd_taboo_refresh_held", self.body)
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
        self.assertGreater(pick.index("debug_log"), pick.index("nd_focus_set_core = { F = $F$ }"))

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


class TestReviewFixes2a(unittest.TestCase):
    """What phase 2a's review changed (2026-11-21): calendar months on the
    panel, the cap from its script value, the status's timing, the fielding
    texts, the Help topic and the funding hover."""

    def setUp(self):
        self.values = strip_comments(read(EXTRA_VALUES))
        self.effects = strip_comments(read(WEAPON_EFFECTS))
        self.loc = loc_values()

    def test_the_month_factor_is_the_weekly_step_s(self):
        """The weekly step adds a quarter of the nominal monthly rate, and a
        year has 52 pulses: a calendar month gains 52 / (4 x 12) of it."""
        step = squash(block(self.effects, "nuclear_program_weekly_progress"))
        weekly = re.search(r"change_variable = \{ name = nuclear_weapon_program_progress add = \{ "
                           r"value = nuclear_weapon_program_monthly_progress divide = (\d+) ", step)
        self.assertIsNotNone(weekly)
        factor = squash(block(self.values, "nuclear_program_pulse_month_factor"))
        m = re.fullmatch(r"value = 52 divide = (\d+)", factor)
        self.assertIsNotNone(m, factor)
        self.assertEqual(int(m.group(1)), int(weekly.group(1)) * 12)

    def test_every_month_the_panel_prints_is_a_calendar_month(self):
        for name in ("nuclear_program_display_monthly_progress", "nd_display_proj_monthly_1",
                     "nd_display_proj_monthly_project"):
            with self.subTest(value=name):
                self.assertIn("multiply = nuclear_program_pulse_month_factor", squash(block(self.values, name)))
        floor = squash(block(self.values, "nuclear_program_display_weekly_progress_floor"))
        self.assertIn("divide = nuclear_program_pulse_month_factor divide = 4", floor)
        months = squash(block(self.values, "nuclear_program_display_months_to_next"))
        self.assertIn("divide = nuclear_program_display_weekly_progress_floor divide = 4 "
                      "divide = nuclear_program_pulse_month_factor", months)

    def test_the_upkeep_cap_from_its_script_value(self):
        values = strip_comments(read(DETERRENCE_VALUES))
        weekly = squash(block(values, "nd_upkeep_weekly"))
        divisor = re.search(r"value = gdp divide = (\d+) multiply = nd_upkeep_units", weekly).group(1)
        cap = squash(block(values, "nd_display_upkeep_cap_gdp_pct"))
        self.assertEqual(cap, f"value = nd_upkeep_units_cap multiply = 52 multiply = 100 divide = {divisor}")
        tt = self.loc["nd_w_upkeep_tt"]
        self.assertIn("ScriptValue('nd_display_upkeep_cap_gdp_pct')|1]%", tt)
        self.assertNotIn("two and a half", tt)

    def test_status_4_follows_the_hold_in_force(self):
        """The hold in force (the modifier, on a Warheads focus), except in a
        block that just refreshed it (nd_focus_set marks the block)."""
        refresh = squash(block(self.effects, "nuclear_program_refresh_state_effect"))
        self.assertIn("else_if = { limit = { OR = { "
                      "AND = { has_local_variable = nd_focus_hold_refreshed nd_taboo_programme_should_be_held = yes } "
                      "AND = { NOT = { has_local_variable = nd_focus_hold_refreshed } nd_focus_is_warheads = yes "
                      "has_modifier = nd_taboo_programme_held } } } "
                      "set_variable = { name = nuclear_program_last_status value = 4 } }", refresh)
        self.assertLess(refresh.index("value = 5"), refresh.index("value = 4"))
        choose = squash(block(self.effects, "nd_focus_choose"))
        self.assertLess(choose.index("nd_focus_set = { F = $F$ }"),
                        choose.index("nuclear_program_refresh_state_effect = yes"))

    def test_the_fielding_texts_promise_only_what_holds(self):
        """Readiness is tracked, so nothing says the missiles are on alert; the
        focus returns to warheads, which a ceiling may hold."""
        keys = [k for k in self.loc if k.startswith(("nuclear_weapon_events.35.", "nuclear_weapon_events.36.",
                                                      "notification_headlines_nd_icbms_fielded",
                                                      "notification_headlines_nd_subs_fielded"))]
        self.assertTrue(keys)
        for key in keys:
            with self.subTest(key=key):
                self.assertNotIn("on alert", self.loc[key].lower())
                self.assertNotIn("goes back to building warheads", self.loc[key])
        events = strip_comments(read(WEAPON_EVENTS))
        for n in ("35", "36"):
            with self.subTest(event=n):
                desc = squash(block(block(events, f"nuclear_weapon_events.{n}"), "desc"))
                self.assertLess(desc.index(f"nuclear_weapon_events.{n}.d_own_held"),
                                desc.index(f"nuclear_weapon_events.{n}.d_own "))
                self.assertIn("THIS = scope:nd_leg_fielder nd_taboo_has_ceiling = yes "
                              "nd_stockpile >= nd_taboo_effective_ceiling_value", desc)
                self.assertIn("at its ceiling", self.loc[f"nuclear_weapon_events.{n}.d_own_held"])
        flavor = squash(block(block(events, "nuclear_weapon_events.35"), "flavor"))
        self.assertIn("trigger = { THIS = scope:nd_leg_fielder } desc = nuclear_weapon_events.35.f_own", flavor)
        self.assertIn("desc = nuclear_weapon_events.35.f_world", flavor)

    def test_the_help_topic_and_the_funding_hover(self):
        how = self.loc["je_nuclear_how_programme"]
        self.assertNotIn("for good", how)
        self.assertNotIn("ten times", how)
        self.assertIn("ScriptValue('nuclear_weapon_program_additional_nuke_progress_multiplier')", how)
        self.assertIn("Nuclear Disarmament", how)
        funding = self.loc["je_nuclear_program_widget_funding_tt"]
        self.assertNotIn("warhead progress a month", funding)
        self.assertIn("GetCustom('nd_prog_focus_object')", funding)
        self.assertIn("ScriptValue('nuclear_weapon_program_additional_nuke_progress_multiplier')", funding)

    def test_the_project_buttons_say_one_thing(self):
        """Op 3's hover lists eight requirement lines; the rows' own hovers say
        a project's progress is kept and no ceiling holds it."""
        for op in (2, 3):
            with self.subTest(op=op):
                self.assertEqual(self.loc[f"nd_tt_focus_set_{op}"].count(". "), 0)

    def test_the_pictures_are_registered(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts" / "image_pipeline"))
        from event_image_prompts import IMAGES
        self.assertIn("nuclear_weapon_events.35", IMAGES["missile_parade"]["events"])
        self.assertIn("nuclear_weapon_events.36", IMAGES["missile_submarine_departure"]["events"])



STATIC_MODIFIERS = ROOT / "common/static_modifiers/nuclear_deterrence_modifiers.txt"
DISPLAY_TYPES = ROOT / "common/modifier_type_definitions/nuclear_deterrence_display_types.txt"
TERMS = {
    "icbms": ("nd_exposure_factor_icbms_held",
              ("country_nd_reach_every_state_bool", "country_nd_unlocks_launch_on_warning_bool",
               "country_nd_unlocks_automatic_retaliation_bool")),
    "submarines": ("nd_exposure_factor_submarines_held", ("country_nd_reach_every_coast_bool",)),
}


def static_modifier_lines(name, loc):
    """A static modifier's GetDesc, as the hover prints it: one line a field,
    its type's name and, unless it is a boolean, a figure (six characters)."""
    body = squash(block(strip_comments(read(STATIC_MODIFIERS)), name))
    fields = [f for f in re.findall(r"\b(\w+) = ", body) if f != "icon"]
    names = (re.sub(r"\[(concept_\w+)\]", lambda m: loc.get(m.group(1), m.group(1)), loc.get(f, f)) for f in fields)
    return "\n".join(name + ("" if f.endswith("_bool") else " +99.9%") for name, f in zip(names, fields))


def composed(key, loc, depth=0):
    """A hover as the player reads it: each GetCustom at its longest branch,
    each static modifier's GetDesc as its lines, each $key$ spliced, each other
    data call as five characters, formatting codes stripped."""
    text = loc.get(key, "")
    text = re.sub(r"\$([\w.\-]+)\$", lambda m: composed(m.group(1), loc, depth + 1) if m.group(1) in loc
                  else "X", text)

    def call(m):
        inner = m.group(1)
        mod = re.search(r"GetStaticModifier\('(\w+)'\)\.GetDesc", inner)
        if mod:
            return static_modifier_lines(mod.group(1), loc)
        if re.fullmatch(r"concept_\w+", inner):
            return loc.get(inner, inner)
        custom = re.search(r"GetCustom\('(\w+)'\)", inner)
        if custom and depth < 4:
            keys = [k for _, k in custom_targets_any(custom.group(1))]
            return max((composed(k, loc, depth + 1) for k in keys), key=len, default="")
        return "99.9K"
    text = re.sub(r"\[([^\[\]]*)\]", call, text)
    text = re.sub(r"#[A-Za-z_]+(;\S*)? ?", "", text).replace("#!", "")
    return re.sub(r"@\w+!", "X", text).replace("\\n", "\n")


def custom_targets_any(name):
    """custom_targets over every customizable-localization file."""
    for path in (ROOT / "common/customizable_localization").glob("*.txt"):
        text = strip_comments(read(path))
        if re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*\{", text):
            body = squash(block(text, name))
            return re.findall(r"text = \{ trigger = \{ (.*?) \} localization_key = (\w+) \}", body)
    return []


class TestFocusTermsMatchScript(unittest.TestCase):
    """What each project grants, as never-added display modifiers whose figures
    are the script's (phase 2 plan D16), and the reach counts the hovers read,
    stored weekly and at fielding (D17)."""

    def setUp(self):
        self.modifiers = strip_comments(read(STATIC_MODIFIERS))
        self.values = strip_comments(read(DETERRENCE_VALUES))
        self.extra = strip_comments(read(EXTRA_VALUES))
        self.types = strip_comments(read(DISPLAY_TYPES))

    def test_the_factors_are_named(self):
        self.assertEqual(constant(self.values, "nd_exposure_factor_icbms_held"), 0.70)
        self.assertEqual(constant(self.values, "nd_exposure_factor_submarines_held"), 0.50)
        self.assertIn("limit = { nd_fields_icbms = yes } value = nd_exposure_factor_icbms_held",
                      squash(block(self.values, "nd_exposure_factor_icbms")))
        self.assertIn("limit = { nd_fields_missile_submarines = yes } value = nd_exposure_factor_submarines_held",
                      squash(block(self.values, "nd_exposure_factor_submarines")))

    def test_each_terms_modifier_carries_its_factor_and_rules(self):
        for leg, (held, booleans) in TERMS.items():
            with self.subTest(leg=leg):
                body = squash(block(self.modifiers, f"nd_focus_terms_{leg}"))
                self.assertAlmostEqual(figure(body, "country_nd_exposure_mult"),
                                       constant(self.values, held) - 1, places=6)
                for field in booleans:
                    self.assertIn(f"{field} = yes", body)

    def test_the_types_are_display_only(self):
        for field in ("country_nd_exposure_mult", "country_nd_reach_every_state_bool",
                      "country_nd_reach_every_coast_bool", "country_nd_unlocks_launch_on_warning_bool",
                      "country_nd_unlocks_automatic_retaliation_bool"):
            with self.subTest(field=field):
                self.assertIn("script_only = yes", squash(block(self.types, field)))
        self.assertIn("percent = yes", squash(block(self.types, "country_nd_exposure_mult")))
        # Less exposure is better: a negative figure shows green.
        self.assertIn("color = bad", squash(block(self.types, "country_nd_exposure_mult")))

    def test_nothing_adds_them_and_the_header_lists_them(self):
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").rglob("*.txt")):
            text = strip_comments(path.read_text(encoding="utf-8-sig", errors="replace"))
            self.assertNotRegex(text, r"(add|remove)_modifier\s*=\s*\{?\s*(name\s*=\s*)?nd_focus_terms_", path)
        header = read(STATIC_MODIFIERS)[:4000]
        self.assertIn("nd_focus_terms_", header)

    def test_the_target_with_each_leg(self):
        for leg, held in (("icbms", "nd_exposure_factor_icbms_held"),
                          ("submarines", "nd_exposure_factor_submarines_held")):
            with self.subTest(leg=leg):
                parts = ["nd_exposure_factor_bombers", "nd_exposure_factor_radar", "nd_exposure_factor_icbms",
                         "nd_exposure_factor_submarines", "nd_exposure_factor_missile_defense"]
                parts[parts.index(f"nd_exposure_factor_{leg}")] = held
                expected = (f"value = {parts[0]} " + " ".join(f"multiply = {p}" for p in parts[1:])
                            + " multiply = -1 add = 1 multiply = 100")
                self.assertEqual(squash(block(self.values, f"nd_survivability_target_with_{leg}")), expected)

    def test_the_forgone_warheads(self):
        rate = squash(block(self.extra, "nd_display_warheads_monthly"))
        self.assertEqual(rate, "value = nd_display_proj_monthly_1 divide = nuclear_weapon_program_goal_value "
                               "max = nd_display_warheads_monthly_cap")
        cap = squash(block(self.extra, "nd_display_warheads_monthly_cap"))
        self.assertEqual(cap, "value = nuclear_weapon_program_max_per_week multiply = 52 divide = 12")
        for n in (2, 3):
            with self.subTest(n=n):
                body = squash(block(self.extra, f"nd_proj_forgone_warheads_{n}"))
                self.assertTrue(body.startswith(f"value = nd_display_proj_months_{n} "
                                                "multiply = nd_display_warheads_monthly"), body)
                self.assertIn("max = nd_display_ceiling_room", body)
        room = squash(block(self.extra, "nd_display_ceiling_room"))
        self.assertIn("limit = { nd_taboo_has_ceiling = yes } value = nd_taboo_effective_ceiling_value "
                      "subtract = nd_stockpile", room)

    def test_the_submarine_upkeep_at_fielding(self):
        self.assertIn("add = nd_upkeep_units_submarines_fielded",
                      squash(block(self.values, "nd_upkeep_units_submarines")))
        self.assertEqual(squash(block(self.values, "nd_upkeep_units_submarines_fielded")),
                         "value = nd_upkeep_size_factor multiply = 6")
        self.assertEqual(squash(block(self.values, "nd_display_upkeep_submarines_with_weekly")),
                         "value = gdp divide = 100000 multiply = nd_upkeep_units_submarines_fielded min = 0")

    def test_the_reach_counts_are_stored_weekly_and_at_fielding(self):
        effects = strip_comments(read(DETERRENCE_EFFECTS))
        refresh = squash(block(effects, "nd_reach_refresh"))
        for name in ("nd_reach_count_now", "nd_reach_count_with_subs", "nd_reach_count_every"):
            self.assertIn(f"set_variable = {{ name = {name} value = 0 }}", refresh)
        self.assertIn("nd_reaches_country = { TARGET = scope:nd_reach_cnt }", refresh)
        self.assertIn("scope:nd_reach_cnt = { any_scope_state = { is_coastal = yes } }", refresh)
        # Our own panel only, from the first device on (D17).
        self.assertIn("is_ai = no var:nuclear_weapons_program_first_nuke_done ?= 1", refresh)
        self.assertIn("nd_reach_refresh = yes", squash(block(effects, "nd_weekly_update")))
        self.assertIn("nd_reach_refresh = yes", squash(block(strip_comments(read(WEAPON_EFFECTS)), "nd_field_leg")))
        for name in ("nd_reach_count_now", "nd_reach_count_with_subs", "nd_reach_count_every"):
            self.assertIn(f"limit = {{ has_variable = {name} }} value = var:{name}",
                          squash(block(self.values, f"nd_display_{name.replace('nd_', '', 1)}")))


class TestFocusHovers(unittest.TestCase):
    """Each project row's hover prints what fielding grants, in figures (spec
    §5.3's Programme focus row; plan D16)."""

    def setUp(self):
        self.loc = loc_values()

    def test_each_row_prints_its_terms(self):
        two, three = self.loc["nd_w_focus_2_tt"], self.loc["nd_w_focus_3_tt"]
        self.assertIn("[GetStaticModifier('nd_focus_terms_icbms').GetDesc]", two)
        self.assertIn("[GetStaticModifier('nd_icbm_force').GetDesc]", two)
        self.assertIn("[Country.GetCustom('nd_focus_grants_2')]", two)
        self.assertIn("[GetStaticModifier('nd_focus_terms_submarines').GetDesc]", three)
        self.assertIn("[Country.GetCustom('nd_focus_grants_3')]", three)

    def test_the_figures_before_and_after(self):
        grants = dict((key, trig) for trig, key in custom_targets("nd_focus_grants_2"))
        self.assertEqual(list(grants)[-1], "nd_w_focus_grants_2")
        self.assertEqual(grants["nd_w_focus_grants_fielded"], "nd_fields_icbms = yes")
        text = self.loc["nd_w_focus_grants_2"]
        for value in ("nd_display_survivability_target", "nd_survivability_target_with_icbms",
                      "nd_display_reach_count_now", "nd_display_reach_count_every", "nd_proj_forgone_warheads_2"):
            self.assertIn(f"ScriptValue('{value}')", text)
        subs = [key for _, key in custom_targets("nd_focus_grants_3")]
        self.assertEqual(subs[-1], "nd_w_focus_grants_3")
        text = self.loc["nd_w_focus_grants_3"]
        for value in ("nd_display_survivability_target", "nd_survivability_target_with_submarines",
                      "nd_display_reach_count_now", "nd_display_reach_count_with_subs", "nd_proj_forgone_warheads_3"):
            self.assertIn(f"ScriptValue('{value}')", text)
        # The submarines' upkeep in money, as the Upkeep row's hover gives it (D16).
        self.assertIn("ScriptValue('nd_display_upkeep_submarines_with_weekly')|D]", text)

    def test_every_new_key_has_loc(self):
        for key in ("nd_focus_terms_icbms", "nd_focus_terms_submarines", "nd_focus_terms_icbms_desc",
                    "nd_focus_terms_submarines_desc", "country_nd_exposure_mult", "country_nd_exposure_mult_desc",
                    "country_nd_reach_every_state_bool", "country_nd_reach_every_coast_bool",
                    "country_nd_unlocks_launch_on_warning_bool", "country_nd_unlocks_automatic_retaliation_bool",
                    "nd_w_focus_grants_fielded"):
            self.assertIn(key, self.loc)

    def test_each_hover_fits(self):
        for key in ("nd_w_focus_1_tt", "nd_w_focus_2_tt", "nd_w_focus_3_tt"):
            with self.subTest(key=key):
                self.assertLess(len(composed(key, self.loc)), 500, composed(key, self.loc))


class TestReviewFixes2b(unittest.TestCase):
    """Phase 2b's review: the reach counts a human's country hasn't had yet,
    a country with no coast, disarmament's rebuild, and the reach texts."""

    REACH = ("nd_reach_count_now", "nd_reach_count_with_subs", "nd_reach_count_every")

    def setUp(self):
        self.loc = loc_values()

    def test_uncounted_reach_has_its_own_form(self):
        # A country a player has just taken, or a save from before 2b, has no
        # counts yet: the hover leaves the reach line out and says when it comes.
        for n, after in ((2, "nd_survivability_target_with_icbms"), (3, "nd_survivability_target_with_submarines")):
            with self.subTest(row=n):
                pairs = custom_targets(f"nd_focus_grants_{n}")
                keys = [key for _, key in pairs]
                self.assertEqual(keys[-2:], [f"nd_w_focus_grants_{n}_uncounted", f"nd_w_focus_grants_{n}"])
                self.assertEqual(pairs[-2][0], "NOT = { has_variable = nd_reach_count_now }")
                text = self.loc[f"nd_w_focus_grants_{n}_uncounted"]
                self.assertNotIn("reach_count", text)
                self.assertIn(f"ScriptValue('{after}')", text)
                self.assertIn(f"ScriptValue('nd_proj_forgone_warheads_{n}')", text)
                self.assertIn("next weekly update", text)

    def test_no_coast_prints_no_figures(self):
        pairs = custom_targets("nd_focus_grants_3")
        keys = [key for _, key in pairs]
        # After the fielded branches, before the figures.
        self.assertLess(keys.index("nd_w_focus_grants_fielded"), keys.index("nd_w_focus_grants_no_coast"))
        self.assertLess(keys.index("nd_w_focus_grants_no_coast"), keys.index("nd_w_focus_grants_3_uncounted"))
        self.assertEqual(dict((k, t) for t, k in pairs)["nd_w_focus_grants_no_coast"],
                         "NOT = { any_scope_state = { is_coastal = yes } }")
        self.assertNotIn("ScriptValue", self.loc["nd_w_focus_grants_no_coast"])

    def test_an_ai_country_keeps_no_counts(self):
        refresh = squash(block(strip_comments(read(DETERRENCE_EFFECTS)), "nd_reach_refresh"))
        tail = refresh[refresh.index("is_ai = no var:nuclear_weapons_program_first_nuke_done ?= 1"):]
        others = tail[tail.index("else = {"):]
        for name in self.REACH:
            self.assertIn(f"if = {{ limit = {{ has_variable = {name} }} remove_variable = {name} }}", others)

    def test_disarmament_rebuilds_reach_after_the_zeroing(self):
        article = squash(strip_comments(block(read(ARTICLES), "nuclear_disarmament")))
        entry = article[article.index("on_entry_into_force"):]
        zeroed = entry.index("set_variable = { name = nuclear_weapon_stockpile value = 0 }")
        self.assertLess(entry.index("nd_delivery_remove_legs = yes"), zeroed)
        self.assertGreater(entry.index("nd_reach_refresh = yes"), zeroed)
        # nd_is_armed reads the variable, so the rebuild sees the zero at once.
        self.assertIn("var:nuclear_weapon_stockpile >= 1",
                      squash(block(strip_comments(read(DETERRENCE_TRIGGERS)), "nd_is_armed")))

    def test_the_bomber_texts_name_a_subjects_and_a_hosts_neighbors(self):
        for key in ("je_nuclear_ov_delivery_tt_theirs", "nuclear_program_power_leg_bombers_tt"):
            with self.subTest(key=key):
                self.assertIn("neighbors of a subject or a host of", self.loc[key])

    def test_the_exposure_line_describes_the_cut(self):
        desc = self.loc["country_nd_exposure_mult_desc"]
        self.assertIn("cuts the share", desc)
        self.assertNotIn("stays", desc)


if __name__ == "__main__":
    unittest.main()
