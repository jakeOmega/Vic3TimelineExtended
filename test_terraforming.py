"""Terraforming (era 13 spec § 7.11): the technology and its colony module.

The era 13 society technology Terraforming (after Space Colonization and
Geoengineering) carries a script-only marker, country_sr_terraforming_bool,
that the colony module's queue reads (scripting_best_practices.md § Technology
markers). The module, code 16, is generic: it takes a slot and needs crews,
but only the worlds in gen_solar_sites.TERRAFORMABLE take it. Each staffed
level does a month's work a month into the world's own record
(sr_site_terra_done_<key>, global, kept through a cession, a release and a
level coming down); TERRA_LEVEL_MONTHS of work add the world's base room once
more, up to TERRA_MAX_LEVELS shares, and a finished world's levels stand down.
These tests pin that wiring in the generator's output and the hand-written
parts; docs/testing/era-13-playtest.md § Phase 3: Terraforming holds the
in-game checks.
"""
import glob
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
import gen_solar_sites as gss  # noqa: E402


def _read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[m.end():i - 1]


def _def(text, name):
    """A definition at the start of a line, not a call of it."""
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if not m:
        raise AssertionError(f"no definition {name}")
    depth, i = 1, m.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[m.end():i - 1]


def _type_body(text, name):
    m = re.search(rf"(?m)^\ttype {re.escape(name)} = \w+ \{{", text)
    if not m:
        raise AssertionError(f"no type {name}")
    depth, i = 1, m.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[m.end():i - 1]


def _squash(text):
    return re.sub(r"\s+", " ", text).strip()


def _loc():
    out = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "*.yml")):
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                m = re.match(r'^ ([\w.\-]+):\d* "(.*)"\s*$', line)
                if m:
                    out[m.group(1)] = m.group(2)
    return out


EFFECTS = _strip(_read(str(gss.EFFECTS_OUT)))
TRIGGERS = _strip(_read(str(gss.TRIGGERS_OUT)))
VALUES = _strip(_read(str(gss.VALUES_OUT)))
DISPLAY = _strip(_read(str(gss.DISPLAY_OUT)))
ROWS = _read(str(gss.GUI_OUT))
WIDGET = _read("gui/journal_entry_widgets/space_race_widget.gui")
SGUIS = _strip(_read("common/scripted_guis/sr_colony_sguis.txt"))
LOC = _loc()
TERRA = [s for s in gss.SITES if gss.terraformable(s)]
OTHERS = [s for s in gss.SITES if not gss.terraformable(s)]
CODE = gss.MODULE_CODES["terra"]


class TechnologyTest(unittest.TestCase):
    def test_the_technology(self):
        tech = _block(_strip(_read("common/technology/technologies/era_13.txt")), "terraforming")
        self.assertIn("era = era_13", tech)
        self.assertIn("category = society", tech)
        self.assertEqual(re.findall(r"^\t\t(\w+)$", _block(tech, "unlocking_technologies"), re.M),
                         ["space_colonization", "geoengineering"])
        self.assertEqual(_squash(_block(tech, "modifier")), f"{gss.TERRA_MARKER} = yes")
        self.assertIn("ai_weight = { value = 1 }", _squash(tech))
        # Both prerequisites are society technologies (same-category rule).
        era_12 = _strip(_read("common/technology/technologies/era_12.txt"))
        for prereq in ("space_colonization", "geoengineering"):
            with self.subTest(prereq=prereq):
                self.assertIn("category = society", _block(era_12, prereq))
        self.assertRegex(_read("common/technology/technologies/era_13.txt"),
                         r'terraforming = \{[^}]*texture = "([^"]+)" # Placeholder Icon')
        self.assertEqual(LOC["terraforming"], "Terraforming")
        self.assertIn("Unlocks the Terraforming colony module", LOC["terraforming_desc"])
        prompts = _read("scripts/image_pipeline/icon_prompts.py")
        self.assertRegex(prompts, r'"terraforming": \{"subject": "[^"]+", "seed": None\}')

    def test_the_marker(self):
        """A script-only boolean the technology's tooltip names, read by the
        module's queue and the panel, never the technology itself."""
        types = _strip(_read("common/modifier_type_definitions/space_race_modifier_types.txt"))
        body = _squash(_block(types, gss.TERRA_MARKER))
        self.assertIn("boolean = yes", body)
        self.assertIn("script_only = yes", body)
        self.assertTrue(LOC[gss.TERRA_MARKER])
        self.assertTrue(LOC[f"{gss.TERRA_MARKER}_desc"])
        for site in TERRA:
            with self.subTest(site=site.key):
                self.assertIn(f"modifier:{gss.TERRA_MARKER} = yes",
                              _block(TRIGGERS, f"sr_mod_can_queue_terra_{site.key}"))
        self.assertNotIn("has_technology_researched = terraforming", EFFECTS + TRIGGERS + VALUES + SGUIS)


class TableTest(unittest.TestCase):
    def test_the_worlds_that_take_it(self):
        """Mars, Venus and Titan (the spec's), and Jupiter's two largest moons."""
        keys = {s.key for s in gss.SITES}
        self.assertLessEqual(gss.TERRAFORMABLE, keys)
        self.assertEqual({s.key for s in gss.SITES if s.kind == "mars"} | {"venus", "titan", "ganymede", "callisto"},
                         gss.TERRAFORMABLE)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertEqual("terra" in gss.module_types(site), gss.terraformable(site))
                self.assertEqual("terra" in gss.generic_types(site), gss.terraformable(site))
                self.assertEqual("terra" in gss.crewed_types(site), gss.terraformable(site))

    def test_its_code_comes_after_every_saved_one(self):
        """Saves keep codes 1 to 15 in their queues and shipments."""
        self.assertEqual(CODE, 16)
        self.assertEqual(max(gss.MODULE_CODES.values()), CODE)
        self.assertEqual(gss.FACILITY["terra"].name, "Terraforming")
        self.assertFalse(gss.FACILITY["terra"].ships)
        self.assertFalse(gss.FACILITY["terra"].modifier)
        self.assertEqual(gss.MODULE_LINES[-1], ("terra",))

    def test_no_other_world_has_any_of_it(self):
        everything = EFFECTS + TRIGGERS + VALUES + DISPLAY + ROWS
        for site in OTHERS:
            with self.subTest(site=site.key):
                self.assertNotRegex(everything, rf"\w*terra\w*_{site.key}\b")

    def test_the_numbers(self):
        """A share is the base room once more; a staffed level is 4% a year;
        three at once finish a world in 25 years."""
        self.assertEqual(gss.TERRA_ROOM_SHARE, 1)
        self.assertEqual(gss.TERRA_LEVEL_MONTHS, 300)
        self.assertEqual(gss.TERRA_MAX_LEVELS, 3)
        self.assertEqual(gss.TERRA_FULL_MONTHS, gss.TERRA_MAX_LEVELS * gss.TERRA_LEVEL_MONTHS)
        self.assertEqual(gss.TERRA_FULL_MONTHS / gss.TERRA_MAX_LEVELS / 12, 25)
        for name, value in (("sr_terra_level_months", gss.TERRA_LEVEL_MONTHS),
                            ("sr_terra_max_levels", gss.TERRA_MAX_LEVELS),
                            ("sr_terra_full_months", gss.TERRA_FULL_MONTHS),
                            ("sr_mod_ai_terra_fill", gss.TERRA_AI_FILL)):
            with self.subTest(value=name):
                self.assertIn(f"{name} = {{ value = {value} }}", VALUES)

    def test_the_loc_states_the_numbers(self):
        per_year = round(100 * 12 * gss.TERRA_ROOM_SHARE / gss.TERRA_LEVEL_MONTHS)
        whole = f"+{gss.TERRA_MAX_LEVELS * gss.TERRA_ROOM_SHARE * 100}%"
        for key in ("je_space_race_widget_mod_terra_tt", "je_space_race_widget_terra_progress_tt",
                    "sr_mod_queue_terra_tt"):
            with self.subTest(key=key):
                self.assertIn(f"#v {per_year}%#!", LOC[key])
                self.assertIn(f"#v {whole}#!", LOC[key])
        self.assertIn(f"#v {gss.TERRA_MAX_LEVELS}#! levels", LOC["je_space_race_widget_mod_terra_tt"])
        self.assertIn("#v 25#! years", LOC["je_space_race_widget_mod_terra_tt"])
        self.assertIn("fewer than three", LOC["sr_mod_req_terra_room_tt"])
        self.assertEqual(LOC["sr_mq_module_terra"], "Terraforming")
        self.assertEqual(LOC["je_space_race_widget_mod_name_terra"], "Terraforming")


class RoomTest(unittest.TestCase):
    def test_room_adds_the_share_done(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                for name in (f"sr_site_room_{k}", f"sr_md_room_less_hab_{k}"):
                    body = _squash(_block(VALUES, name))
                    if gss.terraformable(site):
                        self.assertIn(f"add = 1 add = sr_site_terra_share_{k} multiply = sr_site_base_room_{k}", body)
                    else:
                        self.assertIn(f"add = 1 multiply = sr_site_base_room_{k}", body)
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                self.assertEqual(_squash(_block(VALUES, f"sr_site_terra_share_{k}")),
                                 f"value = sr_site_terra_done_value_{k} divide = sr_terra_level_months")
                done = _squash(_block(VALUES, f"sr_site_terra_done_value_{k}"))
                self.assertIn(f"has_global_variable = sr_site_terra_done_{k} }} value = global_var:sr_site_terra_done_{k}",
                              done)

    def test_the_pace_is_the_staffed_levels_and_nothing_occupied(self):
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                rate = _squash(_block(VALUES, f"sr_site_terra_rate_{k}"))
                self.assertIn(f"value = sr_site_terra_staffed_{k}", rate)
                self.assertIn(f"has_global_variable = sr_site_occupier_{k} }} value = 0", rate)
                self.assertIn(f"sr_site_terra_staffed_{k} = {{ value = sr_site_terra_value_{k} "
                              f"multiply = sr_site_staffing_{k} }}", VALUES)
                self.assertIn(f"add = sr_site_terra_value_{k}", _squash(_block(VALUES, f"sr_site_levels_{k}")))

    def test_the_work_is_the_world_s(self):
        """A release clears the levels, not the work done; nothing else removes it."""
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                release = _block(EFFECTS, f"sr_site_release_{k}")
                self.assertIn(f"remove_global_variable = sr_site_terra_{k} ", release + " ")
                self.assertNotIn(f"sr_site_terra_done_{k}", release)
        self.assertEqual(len(re.findall(r"remove_global_variable = sr_site_terra_done_", EFFECTS)), 0)


class MonthTest(unittest.TestCase):
    def test_the_month_runs_before_the_projection(self):
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                month = _block(EFFECTS, f"sr_site_monthly_{k}")
                step = month.index(f"sr_site_terra_step_{k} = {{ MONTHS = 1 }}")
                self.assertLess(step, month.index(f"sr_site_sync_{k} = yes"))
                guard = _squash(month[:step][month[:step].rindex("limit"):])
                self.assertIn("sr_colonies_contested_enabled = yes", guard)
                self.assertIn(f"sr_site_terra_value_{k} > 0", guard)

    def test_the_step_adds_the_pace_and_stands_down_when_finished(self):
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                step = _squash(_def(EFFECTS, f"sr_site_terra_step_{k}"))
                self.assertIn(f"limit = {{ sr_site_terra_rate_{k} > 0 }}", step)
                self.assertIn(f"name = sr_site_terra_done_{k} value = {{ value = sr_site_terra_rate_{k} "
                              f"multiply = $MONTHS$ add = sr_site_terra_done_value_{k} max = sr_terra_full_months }}", step)
                self.assertLess(step.index("set_global_variable"), step.index("remove_global_variable"))
                self.assertIn(f"NOT = {{ sr_site_terra_open_{k} = yes }} }} remove_global_variable = sr_site_terra_{k} ",
                              step)
                self.assertIn(f"sr_site_terra_open_{k} = {{ sr_site_terra_done_value_{k} < sr_terra_full_months }}",
                              TRIGGERS)

    def test_a_simulated_world(self):
        """The step's arithmetic, month by month: three staffed levels finish in
        25 years and stand down; one level alone has done a third by then."""
        def run(levels, staffing, months):
            done = 0.0
            for _ in range(months):
                if levels:
                    done = min(done + levels * staffing, gss.TERRA_FULL_MONTHS)
                    if done >= gss.TERRA_FULL_MONTHS:
                        levels = 0
            return done / gss.TERRA_LEVEL_MONTHS * gss.TERRA_ROOM_SHARE, levels
        self.assertEqual(run(3, 1, 300), (3, 0))
        self.assertEqual(run(3, 1, 299)[1], 3)
        self.assertAlmostEqual(run(1, 1, 300)[0], 1)
        self.assertAlmostEqual(run(2, 0.5, 120)[0], 0.4)


class QueueTest(unittest.TestCase):
    def test_the_queue_gate(self):
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                can = _squash(_block(TRIGGERS, f"sr_mod_can_queue_terra_{k}"))
                for cond in (f"global_var:sr_site_holder_{k} ?= this", "sr_mq_has_room = yes",
                             f"sr_mod_slots_used_{k} < sr_site_slots_max_{k}", f"modifier:{gss.TERRA_MARKER} = yes",
                             f"sr_mod_terra_used_{k} < sr_terra_max_levels", f"sr_site_terra_open_{k} = yes"):
                    self.assertIn(cond, can)
                used = _squash(_block(VALUES, f"sr_mod_terra_used_{k}"))
                self.assertIn(f"value = sr_site_terra_value_{k}", used)
                self.assertIn(f"add = var:sr_mq_terra_{k}", used)
                self.assertIn(f"add = global_var:sr_site_ship_terra_{k}", used)

    def test_the_scripted_gui(self):
        sgui = _squash(_block(SGUIS, "sr_colony_module_sgui"))
        terra = sgui[sgui.index(f"limit = {{ scope:op = {CODE} }} custom_tooltip = {{ text = sr_mod_req_terra_tech_tt"):]
        for line in (f"text = sr_mod_req_terra_tech_tt modifier:{gss.TERRA_MARKER} = yes",
                     "text = sr_mod_req_terra_room_tt sr_mod_scope_terra_room = yes",
                     "text = sr_mod_req_terra_open_tt sr_mod_scope_terra_open = yes"):
            self.assertIn(line, terra)
        self.assertIn(f"limit = {{ scope:op = {CODE} }} custom_tooltip = {{ text = sr_mod_queue_terra_tt "
                      "sr_mod_queue_from_scope = yes }", sgui)
        for name in ("sr_mod_scope_terra_room", "sr_mod_scope_terra_open"):
            body = _block(TRIGGERS, name)
            with self.subTest(trigger=name):
                self.assertEqual(re.findall(r"scope:site = (\d+)", body), [str(s.index) for s in TERRA])

    def test_a_landing_and_the_queue_s_head(self):
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                install = _squash(_block(EFFECTS, f"sr_mod_install_{k}"))
                self.assertIn(f"local_var:sr_ms_type_now = {CODE} sr_site_generic_built_{k} < sr_site_slots_max_{k} "
                              f"sr_site_terra_value_{k} < sr_terra_max_levels sr_site_terra_open_{k} = yes", install)
                self.assertIn(f"local_var:sr_mq_head_site = {site.index}", _block(EFFECTS, "sr_mod_fab_head"))
                self.assertIn(f"local_var:sr_mq_head_type = {CODE} sr_site_terra_open_{k} = yes }} sr_mod_fab_build",
                              _squash(_block(EFFECTS, "sr_mod_fab_head")))

    def test_the_ai_terraforms_a_filling_world_within_its_slots(self):
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                plan = _squash(_block(EFFECTS, f"sr_mod_ai_plan_{k}"))
                terra = plan[plan.index(f"sr_mod_can_queue_terra_{k} = yes"):]
                terra = terra[:terra.index("}", terra.index("sr_mod_queue = {"))]
                for cond in (f"sr_mod_slots_used_{k} < sr_site_slots_{k}", f"sr_site_fill_{k} >= sr_mod_ai_terra_fill",
                             f"sr_site_crews_{k} >= sr_site_levels_{k}"):
                    self.assertIn(cond, terra)
                order = [plan.index(f"sr_mod_can_queue_{t}_{k}") for t in ("mine", "terra", "bunker")]
                self.assertEqual(order, sorted(order))


class PanelTest(unittest.TestCase):
    def test_the_widget_hides_it_by_default(self):
        row = _type_body(WIDGET, "te_sr_colony_row")
        self.assertEqual(_squash(row).count('block "terra_visible" { visible = no }'), 3)
        for block in ("mod_terra_level", "mod_terra_pending", "mod_terra_button", "mod_terra_dismantle_button",
                      "terra_pct", "terra_years", "terra_idle_visible", "terra_under_way_visible",
                      "terra_finished_visible"):
            with self.subTest(block=block):
                self.assertIn(f'block "{block}" {{}}', row)
        self.assertIn('text = "je_space_race_widget_mod_name_terra"', row)
        self.assertIn('text = "je_space_race_widget_page_terraformed"', row)

    def test_each_world_that_takes_it_shows_it(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                shown = f"ScriptValue('sr_disp_terra_shown_{k}')"
                self.assertEqual(shown in ROWS, gss.terraformable(site))
                op = (f"AddScope( 'site', MakeScopeValue( '(CFixedPoint){site.index}' ) )"
                      f".AddScope( 'op', MakeScopeValue( '(CFixedPoint){CODE}' ) )")
                self.assertEqual(op in ROWS, gss.terraformable(site))
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                shown = _squash(_block(DISPLAY, f"sr_disp_terra_shown_{k}"))
                for cond in (f"modifier:{gss.TERRA_MARKER} = yes", f"sr_site_terra_value_{k} > 0",
                             f"sr_site_terra_done_value_{k} > 0", f"sr_disp_mod_pending_terra_{k} > 0"):
                    self.assertIn(cond, shown)
                state = _squash(_block(DISPLAY, f"sr_disp_terra_state_{k}"))
                self.assertIn(f"NOT = {{ sr_site_terra_open_{k} = yes }} }} value = 2", state)
                self.assertIn(f"sr_site_terra_rate_{k} > 0 }} value = 1", state)
                years = _squash(_block(DISPLAY, f"sr_disp_terra_years_{k}"))
                self.assertIn(f"value = sr_terra_full_months subtract = sr_site_terra_done_value_{k} "
                              f"divide = sr_site_terra_rate_{k} divide = 12 ceiling = yes max = 999", years)

    def test_the_icon_is_kept_art(self):
        """The page's row and tile show the Mars colony's icon, art the panel
        already has (space_race_gui_icons.md, Kept)."""
        row = _type_body(WIDGET, "te_sr_colony_row")
        page = row[row.index('block "terra_visible" {', row.index("te_sr_page_tile")):]
        self.assertIn('texture = "gfx/interface/icons/space_race_icons/colony_mars.dds"', page)
        self.assertIn("Terraforming", _read("docs/systems/space_race_gui_icons.md"))


class ConsoleTest(unittest.TestCase):
    def test_ten_years_from_the_console(self):
        event = _squash(_block(_strip(_read("events/te_debug_space_race_events.txt")), "te_debug_space_race.4"))
        self.assertIn("name = te_debug_space_race.4.i trigger = { sr_colonies_contested_enabled = yes } "
                      "sr_terra_debug_advance = yes sr_emig_refresh_modifiers = yes", event)
        self.assertTrue(LOC["te_debug_space_race.4.i"])
        advance = _squash(_block(EFFECTS, "sr_terra_debug_advance"))
        for site in TERRA:
            with self.subTest(site=site.key):
                self.assertIn(f"global_var:sr_site_holder_{site.key} ?= this }} "
                              f"sr_site_terra_step_{site.key} = {{ MONTHS = 120 }} sr_site_sync_{site.key} = yes", advance)


if __name__ == "__main__":
    unittest.main()
