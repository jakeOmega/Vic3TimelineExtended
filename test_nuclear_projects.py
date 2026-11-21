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


if __name__ == "__main__":
    unittest.main()
