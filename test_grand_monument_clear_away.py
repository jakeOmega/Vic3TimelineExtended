"""Clear It Away (owner, 2026-10-31).

Once six Grand Monuments stand in one of a player's states (a construction
site among them, the most construction allows), the least grand of them,
contested ones aside, may be cleared away to make room for a grander one.
These tests pin the wiring: the reads that pick the least grand, the buttons
and where they show, the order-then-hidden-event shape every monument button
uses, and that nothing else follows (no ledger). In-game checks:
docs/testing/grand-monuments-multiple-playtest.md § Clear It Away.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    return "\n".join(line.split("#", 1)[0] if not line.lstrip().startswith("###") else "" for line in text.split("\n"))


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
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


VALUES = _read("common/script_values/gm_monument_values.txt")
TRIGGERS = _read("common/scripted_triggers/gm_monument_triggers.txt")
EFFECTS = _read("common/scripted_effects/gm_monument_effects.txt")
SGUIS = _read("common/scripted_guis/gm_monument_sguis.txt")
EVENTS = _read("events/monument_events.txt")
TROPHY_GUI = _read("gui/gm_trophy_widgets.gui")
STATE_GUI = _read("gui/te_state_panel_widgets.gui")
JE_GUI = _read("gui/journal_entry_widgets/grand_monuments_widget.gui")


class LeastGrandTests(unittest.TestCase):
    def test_six_is_the_gate_construction_has(self):
        """The button shows at the cap a new construction site stops at."""
        site_gate = _squash(_block(_read("common/scripted_triggers/gm_monument_triggers.txt"),
                                   "gm_state_can_build_site"))
        self.assertIn("gm_state_monument_count < 6", site_gate)
        self.assertIn("gm_state_monument_count >= 6", _squash(_block(VALUES, "gm_state_disp_clearable")))
        self.assertIn("var:gm_tr_origin ?= { gm_state_monument_count >= 6 }",
                      _squash(_block(VALUES, "gm_mon_disp_clearable")))

    def test_the_least_is_read_over_the_eligible(self):
        least = _squash(_block(VALUES, "gm_state_least_grandeur"))
        self.assertIn("ordered_in_list = { variable = gm_monuments_here limit = { gm_mon_clear_eligible = yes } "
                      "order_by = gm_mon_grandeur_neg position = 0 check_range_bounds = no add = gm_mon_grandeur }",
                      least)
        self.assertIn("limit = { gm_state_primary_clear_eligible = yes } max = gm_state_primary_grandeur", least)
        self.assertIn("multiply = -1", _squash(_block(VALUES, "gm_mon_grandeur_neg")))
        self.assertIn("var:gm_tr_origin = { subtract = gm_state_least_grandeur }",
                      _squash(_block(VALUES, "gm_mon_least_gap")))

    def test_contested_monuments_keep_their_own_choices(self):
        self.assertIn("NOT = { has_variable = gm_tr_contested }", _block(TRIGGERS, "gm_mon_clear_eligible"))
        self.assertIn("NOT = { gm_state_is_contested = yes }", _block(TRIGGERS, "gm_state_primary_clear_eligible"))
        self.assertIn("gm_state_primary_grandeur <= gm_state_least_grandeur",
                      _block(TRIGGERS, "gm_state_primary_is_least"))
        self.assertIn("gm_mon_least_gap <= 0", _block(TRIGGERS, "gm_mon_is_least"))


class ButtonTests(unittest.TestCase):
    def test_the_scripted_guis_order_only(self):
        for name, scope, order in (("gm_clear_sgui", "gm_state", "gm_state_order_clear"),
                                   ("gm_mon_clear_sgui", "gm_mon", "gm_mon_order_clear")):
            with self.subTest(sgui=name):
                sgui = _squash(_block(SGUIS, name))
                self.assertIn(f"saved_scopes = {{ {scope} }}", sgui)
                self.assertIn("ai_is_valid = { always = no }", sgui)
                self.assertIn(f"{order} = yes", sgui)
                self.assertIn("gm_state_clear_quiet = yes", sgui)
                self.assertIn("NOT = { has_variable = gm_clear_by }", sgui)
                body = _squash(_block(EFFECTS, order))
                self.assertIn("trigger_event = { id = monument_events.33 }", body)
                self.assertNotIn("destroy_container", body)
                self.assertNotIn("gm_clear_state", body)

    def test_the_hidden_event_runs_it(self):
        event = _squash(_block(EVENTS, "monument_events.33"))
        self.assertIn("type = state_event hidden = yes", event)
        self.assertIn("gm_state_run_clear = yes", event)
        run = _squash(_block(EFFECTS, "gm_state_run_clear"))
        for check in ("var:gm_clear_by ?= { this = scope:gm_clear_owner }", "gm_state_monument_count >= 6",
                      "gm_state_clear_quiet = yes", "gm_state_primary_is_least = yes", "gm_state_has_secondary = yes",
                      "gm_mon_is_least = yes", "gm_state_clear_away_primary = yes", "gm_mon_clear_away_one = yes"):
            self.assertIn(check, run)
        for var in ("gm_clear_primary", "gm_clear_target", "gm_clear_by"):
            self.assertIn(f"gm_remove_state_var = {{ VAR = {var} }}", run)

    def test_nothing_else_follows(self):
        """No ledger: losing the monument is the price (Pull Down, a contested
        monument's, is the political act)."""
        for name in ("gm_state_clear_away_primary", "gm_mon_clear_away_one", "gm_state_run_clear"):
            with self.subTest(effect=name):
                body = _block(EFFECTS, name)
                self.assertNotIn("ledger", body)
                self.assertNotIn("gm_state_record_teardown", body)
        primary = _squash(_block(EFFECTS, "gm_state_clear_away_primary"))
        self.assertIn("gm_clear_state = { KEEP_LANDMARK = no } gm_state_promote_secondary = yes", primary)
        self.assertNotIn("remove_building", primary)
        one = _squash(_block(EFFECTS, "gm_mon_clear_away_one"))
        for step in ("remove_list_variable = { name = gm_monuments_here target = scope:gm_mon_down }",
                     "remove_list_variable = { name = gm_monuments_held target = scope:gm_mon_down }",
                     "remove_list_global_variable = { name = gm_monuments target = scope:gm_mon_down }",
                     "destroy_container = yes"):
            self.assertIn(step, one)

    def test_where_the_buttons_show(self):
        clear = _squash(_type_body(TROPHY_GUI, "gm_clear_button"))
        self.assertIn("datacontext = \"[GetScriptedGui('gm_clear_sgui')]\"", clear)
        self.assertIn("ObjectsEqual( State.GetOwner, GetPlayer.Self )", clear)
        self.assertIn("ScriptValue('gm_state_disp_clearable')", clear)
        self.assertNotIn("IsShown", clear)
        mon = _squash(_type_body(TROPHY_GUI, "gm_mon_clear_button"))
        self.assertIn("datacontext = \"[GetScriptedGui('gm_mon_clear_sgui')]\"", mon)
        self.assertIn("ScriptValue('gm_mon_disp_clearable')", mon)
        self.assertNotIn("IsShown", mon)
        self.assertIn("gm_mon_clear_button = {}", _squash(_type_body(TROPHY_GUI, "gm_mon_row_site")))
        self.assertIn("gm_clear_button = {}", _squash(_strip_comments(_type_body(STATE_GUI, "te_state_gm_card"))))
        self.assertIn("gm_clear_button = {}", _squash(_strip_comments(_type_body(JE_GUI, "gm_monument_row"))))

    def test_the_self_check_runs_monthly(self):
        self.assertIn("gm_clear_self_check = yes", _block(EFFECTS, "gm_monument_monthly"))
        check = _block(EFFECTS, "gm_clear_self_check")
        self.assertIn("TE_SELF_CHECK OK monument_least_grandeur", check)
        self.assertIn("TE_SELF_CHECK BROKEN monument_least_grandeur", check)
        self.assertIn("set_global_variable = gm_clear_checked", check)
        self.assertIn("monument_least_grandeur", _read("docs/testing/grand-monuments-multiple-playtest.md"))


if __name__ == "__main__":
    unittest.main()
