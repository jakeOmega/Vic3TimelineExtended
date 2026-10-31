"""Taking a colony module down (owner, 2026-10-31).

On a colony's page each module has a minus button (sr_colony_dismantle_sgui)
that takes one level down over sr_mod_dismantle_months, one level at a time a
world, so a colony can't be stripped bare the moment a rival moves on it: the
world leaving its holder, or its occupation, ends the order, and a blockade
holds it. These tests pin that wiring in the generator's output and the
hand-written parts; docs/testing/solar-colonies-playtest.md § Taking a module
down holds the in-game checks.
"""
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


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
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


EFFECTS = _read(str(gss.EFFECTS_OUT))
TRIGGERS = _read(str(gss.TRIGGERS_OUT))
VALUES = _read(str(gss.VALUES_OUT))
DISPLAY = _read(str(gss.DISPLAY_OUT))
ROWS = _read(str(gss.GUI_OUT))
SGUIS = _read("common/scripted_guis/sr_colony_sguis.txt")
MODULE_EFFECTS = _read("common/scripted_effects/sr_colony_module_effects.txt")
MODULE_VALUES = _read("common/script_values/sr_colony_module_values.txt")
WIDGET = _read("gui/journal_entry_widgets/space_race_widget.gui")


class DismantleRecordTests(unittest.TestCase):
    def test_it_takes_time(self):
        """A level takes a year to come down: long enough that a rival's move
        on a colony finds its modules standing."""
        m = re.search(r"(?m)^sr_mod_dismantle_months = \{ value = (\d+) \}", MODULE_VALUES)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(int(m.group(1)), 6)
        start = _squash(_block(MODULE_EFFECTS, "sr_md_start"))
        self.assertIn("set_variable = { name = sr_md_type_$KEY$ value = $CODE$ }", start)
        self.assertIn("set_variable = { name = sr_md_left_$KEY$ value = sr_mod_dismantle_months }", start)

    def test_the_month_counts_it_down(self):
        """sr_mod_month runs every world's step; a blockade holds the count,
        losing the world or its occupation ends the order."""
        self.assertIn("sr_md_month = yes", _block(MODULE_EFFECTS, "sr_mod_month"))
        monthly = _squash(_block(EFFECTS, "sr_md_month"))
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"sr_md_month_{k} = yes", monthly)
                step = _squash(_block(EFFECTS, f"sr_md_month_{k}"))
                self.assertIn(f"NOT = {{ global_var:sr_site_holder_{k} ?= this }} "
                              f"has_global_variable = sr_site_occupier_{k} }} }} sr_md_clear_{k} = yes", step)
                self.assertIn(f"limit = {{ NOT = {{ has_global_variable = sr_site_blockaded_{k} }} }}", step)
                self.assertIn(f"change_variable = {{ name = sr_md_left_{k} subtract = 1 }}", step)
                self.assertIn(f"sr_md_finish_{k} = yes", step)

    def test_leaving_the_holder_ends_it(self):
        """The unmirror (the world leaving the country, or occupied) clears the
        order, so a captured colony keeps the level that was coming down."""
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"sr_md_clear_{site.key} = yes", _block(EFFECTS, f"sr_site_unmirror_{site.key}"))

    def test_a_level_comes_down_to_its_floor_and_syncs(self):
        for site in gss.SITES:
            k = site.key
            finish = _squash(_block(EFFECTS, f"sr_md_finish_{k}"))
            for t in ("a", "b", *gss.generic_types(site)):
                with self.subTest(site=k, type=t):
                    floor = f"sr_md_floor_{t}_{k}" if t in ("a", "b") else "0"
                    self.assertIn(f"var:sr_md_type_{k} = {gss.MODULE_CODES[t]} "
                                  f"{gss.level_value(t, site)} > {floor}", finish)
            self.assertIn(f"sr_md_clear_{k} = yes sr_site_sync_{k} = yes", finish)

    def test_the_founding_specialization_keeps_its_first_level(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                for slot, option in (("a", 1), ("b", 2)):
                    floor = _squash(_block(VALUES, f"sr_md_floor_{slot}_{k}"))
                    self.assertIn(f"global_var:sr_site_spec_{k} = {option} }} value = 1", floor)

    def test_a_habitat_coming_down_holds_the_room(self):
        """While a Habitat comes down, growth and settlers fill the room it
        will leave, so no one is lost when it goes."""
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                held = _squash(_block(VALUES, f"sr_site_room_held_{k}"))
                self.assertIn(f"var:sr_md_type_{k} = {gss.MODULE_CODES['hab']}", held)
                self.assertIn(f"value = sr_md_room_less_hab_{k}", held)
                self.assertIn(f"value = sr_site_room_held_{k}", _block(VALUES, f"sr_site_free_room_{k}"))
                self.assertIn(f"max = sr_site_room_held_{k}", _block(EFFECTS, f"sr_site_monthly_{k}"))


class DismantleButtonTests(unittest.TestCase):
    def test_the_scripted_gui(self):
        sgui = _squash(_block(SGUIS, "sr_colony_dismantle_sgui"))
        self.assertIn("saved_scopes = { site op }", sgui)
        self.assertIn("ai_is_valid = { always = no }", sgui)
        for trigger in ("sr_cf_scope_site_held", "sr_md_scope_not_occupied", "sr_md_scope_idle",
                        "sr_md_scope_above_floor", "sr_md_scope_room_kept"):
            self.assertIn(f"{trigger} = yes", sgui)
            self.assertIn(f"{trigger} = {{", TRIGGERS)
        self.assertIn("sr_md_scope_is_this = yes", sgui)
        self.assertIn("sr_md_start_from_scope = yes", sgui)
        self.assertIn("sr_md_cancel_from_scope = yes", sgui)

    def test_each_world_and_type_has_a_start(self):
        start = _squash(_block(EFFECTS, "sr_md_start_from_scope"))
        for site in gss.SITES:
            for t in ("a", "b", *gss.generic_types(site)):
                with self.subTest(site=site.key, type=t):
                    self.assertIn(f"sr_md_start = {{ KEY = {site.key} CODE = {gss.MODULE_CODES[t]} }}", start)

    def test_the_page_row_has_the_button_and_the_line(self):
        typ = _squash(_type_body(WIDGET, "te_sr_page_mod_row"))
        self.assertIn('button_icon_minus_action = { size = { 22 22 } parentanchor = center block "row_dismantle" {} }',
                      typ)
        self.assertIn('block "row_dismantling" {}', typ)
        self.assertIn('text = "je_space_race_widget_mod_coming_down"', typ)
        self.assertIn('block "row_dismantling_months" {}', typ)
        for t in gss.MODULE_TYPES:
            with self.subTest(type=t):
                self.assertIn(f'blockoverride "row_dismantle" {{ block "mod_{t}_dismantle_button" {{}} }}',
                              _squash(WIDGET))

    def test_every_colony_row_fills_them(self):
        for site in gss.SITES:
            k = site.key
            for t in ("a", "b", *gss.generic_types(site)):
                with self.subTest(site=k, type=t):
                    self.assertIn(f"sr_disp_md_{t}_{k} = {{", DISPLAY)
                    self.assertIn(f'blockoverride "mod_{t}_dismantling"', ROWS)
                    self.assertIn(f"sr_disp_md_left_{k}", ROWS)
            if k in gss.NO_SPACEPORT:
                self.assertIn('blockoverride "mod_port_dismantle_button" {\n\t\t\t\tvisible = no', ROWS)
        self.assertEqual(ROWS.count("GetScriptedGui('sr_colony_dismantle_sgui').Execute("),
                         sum(len(("a", "b", *gss.generic_types(s))) for s in gss.SITES))


if __name__ == "__main__":
    unittest.main()
