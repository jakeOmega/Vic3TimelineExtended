"""The banking entry for every country, its cycle dormant until it starts.

docs/superpowers/archive/specs/2026-10-17-banking-always-on-design.md. Every country
under the Banking System rule holds je_banking_cycle from the first weeks of a
game; what starts later is the financial cycle (te_banking_cycle_unlocked:
Stock Exchange and an Urban Center of level 5), latched by finance_cycle_value
(te_banking_cycle_running). Before the start the tools and the Monetary Policy
controls are greyed, the AI sees no tool, and nothing reads or writes the cycle.

These tests hold the entry's gate and pulses, the gate on every tool and on the
monetary controls, every reader of the entry to one of the spec's rows (§ 8),
the panels' gates, and the old-save safety net.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
JE = os.path.join(REPO, "common", "journal_entries", "je_banking.txt")
POLICY_TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "banking_policy_triggers.txt")
CYCLE_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "banking_cycle_effects.txt")
MON_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_monetary_sguis.txt")
DASH_SGUIS = os.path.join(REPO, "common", "scripted_guis", "banking_dashboard_scripted_gui.txt")
BUTTONS = [os.path.join(REPO, "common", "scripted_buttons", n)
           for n in ("timeline_extended_scripted_buttons.txt", "banking_alt_economy_buttons.txt")]
DISPLAY_VALUES = os.path.join(REPO, "common", "script_values", "banking_overview_display_values.txt")
NET = os.path.join(REPO, "common", "on_actions", "te_banking_entry_on_actions.txt")
SELFCHECK_EVENT = os.path.join(REPO, "events", "te_debug_banking_events.txt")
MESSAGES = os.path.join(REPO, "common", "messages", "extra_messages.txt")
PLAYTEST = os.path.join(REPO, "docs", "testing", "banking-playtest.md")
W = os.path.join(REPO, "gui", "journal_entry_widgets")
DASH = os.path.join(W, "banking_dashboard_widget.gui")
HISTORY = os.path.join(W, "banking_history_widget.gui")
LAYOUT = os.path.join(W, "banking_layout_widget.gui")
BUDGET = os.path.join(REPO, "gui", "budget_panel.gui")
LOC_DIR = os.path.join(REPO, "localization", "english")

RUNNING_SGUI = "GetScriptedGui('banking_dash_cycle_running')"
DORMANT_SGUI = "GetScriptedGui('banking_dash_cycle_dormant')"
CYCLE_VARS = ("finance_cycle_value", "finance_cycle_momentum", "bubble_pressure")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block_from(text, start):
    """The brace block that opens at or after `start`, braces included."""
    j = text.index("{", start)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j:k + 1]
    raise AssertionError("unbalanced block")


def _top_block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"no top-level block {name}"
    return _block_from(text, m.end() - 1)


def _key_block(text, key):
    """The first `key = { ... }` in text."""
    m = re.search(rf"\b{re.escape(key)} = \{{", text)
    assert m, f"no {key} block"
    return _block_from(text, m.end() - 1)


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return _block_from(text, m.end() - 1)


def _top_blocks(text):
    """Every top-level `name = { ... }` as (name, body)."""
    out = []
    for m in re.finditer(r"(?m)^([A-Za-z_][\w.]*) = \{", text):
        out.append((m.group(1), _block_from(text, m.end() - 1)))
    return out


def _norm(s):
    return " ".join(s.split())


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
        for line in _read(path).splitlines():
            m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


class EntryTest(unittest.TestCase):
    """The entry is every country's; the cycle starts on the unlock test."""

    @classmethod
    def setUpClass(cls):
        cls.je = _strip_comments(_read(JE))
        cls.triggers = _strip_comments(_read(POLICY_TRIGGERS))
        cls.effects = _strip_comments(_read(CYCLE_EFFECTS))

    def test_the_gate_is_the_rule_and_not_a_rebel(self):
        self.assertEqual(_norm(_key_block(self.je, "is_shown_when_inactive")),
                         "{ te_banking_entry_expected = yes }")
        self.assertEqual(_norm(_top_block(self.triggers, "te_banking_entry_expected")),
                         "{ te_banking_system_on = yes NOT = { is_country_type = decentralized } "
                         "is_revolutionary = no }")
        self.assertEqual(_norm(_key_block(self.je, "possible")), "{ always = yes }")

    def test_the_unlock_test_opens_nothing_but_the_cycle(self):
        # te_banking_entry_unlocked was the entry's gate; renamed, it is only the
        # cycle's start test, and the entry no longer asks it.
        repo_text = "\n".join(_read(p) for p in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True))
        self.assertNotIn("te_banking_entry_unlocked", repo_text)
        unlocked = _norm(_top_block(self.triggers, "te_banking_cycle_unlocked"))
        self.assertIn("has_technology_researched = stock_exchange", unlocked)
        self.assertIn("is_building_type = building_urban_center level >= 5", unlocked)
        self.assertNotIn("te_banking_cycle_unlocked", _key_block(self.je, "is_shown_when_inactive"))

    def test_running_is_the_entry_and_the_latch(self):
        self.assertEqual(_norm(_top_block(self.triggers, "te_banking_cycle_running")),
                         "{ has_journal_entry = je_banking_cycle has_variable = finance_cycle_value }")
        self.assertEqual(_norm(_top_block(self.triggers, "te_banking_controls_open")),
                         "{ te_banking_cycle_running = yes }")
        self.assertEqual(_norm(_top_block(self.triggers, "te_banking_cycle_started_tt")),
                         "{ custom_tooltip = { text = te_banking_cycle_started_tt te_banking_cycle_running = yes } }")

    def test_the_start_seeds_each_variable_only_when_absent(self):
        start = _norm(_top_block(self.effects, "banking_cycle_start"))
        for var, value in zip(CYCLE_VARS, (50, 0, 0)):
            self.assertIn(f"if = {{ limit = {{ NOT = {{ has_variable = {var} }} }} "
                          f"set_variable = {{ name = {var} value = {value} }} }}", start)
        self.assertIn("banking_cycle_update_progress_bars = yes", start)

    def test_immediate_starts_only_an_unlocked_country_without_a_cycle(self):
        immediate = _key_block(self.je, "immediate")
        for var in CYCLE_VARS:
            self.assertNotIn(f"name = {var}", immediate, "immediate seeds through banking_cycle_start only")
        self.assertIn(_norm("if = { limit = { NOT = { has_variable = finance_cycle_value } "
                            "te_banking_cycle_unlocked = yes } banking_cycle_start = yes }"), _norm(immediate))
        self.assertIn(_norm("if = { limit = { te_banking_cycle_running = yes } "
                            "banking_cycle_update_progress_bars = yes }"), _norm(immediate))

    def test_the_monthly_pulse_starts_or_runs(self):
        effect = _key_block(_key_block(self.je, "on_monthly_pulse"), "effect")
        first_if = _key_block(effect, "if")
        self.assertIn("limit = { te_banking_cycle_running = no }", _norm(first_if))
        self.assertIn(_norm("if = { limit = { te_banking_cycle_unlocked = yes } banking_cycle_start = yes "
                            "if = { limit = { is_ai = no } post_notification = banking_cycle_started_notice } }"),
                      _norm(first_if))
        running = _key_block(effect[effect.index(first_if) + len(first_if):], "else")
        for step in ("banking_cycle_advance_variables", "banking_cycle_check_and_execute_crash",
                     "banking_cycle_random_event_effect", "banking_cycle_apply_phase_modifiers",
                     "te_history_record_banking_samples"):
            self.assertIn(f"{step} = yes", running, step)
            self.assertNotIn(f"{step} = yes", first_if, step)

    def test_the_weekly_pulse_waits_for_the_cycle(self):
        effect = _norm(_key_block(_key_block(self.je, "on_weekly_pulse"), "effect"))
        self.assertEqual(effect, "{ if = { limit = { te_banking_cycle_running = yes } "
                                 "banking_cycle_weekly_effects = yes } }")

    def test_no_status_text(self):
        # The dormant entry draws an overview (its Not Started cell), so the
        # line it used to keep would repeat it (style guide rule 1).
        self.assertNotIn("status_desc", self.je)
        self.assertNotIn("banking_cycle_status_not_started", _loc())

    def test_the_start_notice(self):
        self.assertIn("banking_cycle_started_notice = {", _read(MESSAGES))
        loc = _loc()
        for suffix in ("_name", "_desc"):
            self.assertIn("notification_banking_cycle_started_notice" + suffix, loc)
        # Send players to the tab (style guide rule 9).
        self.assertIn("Banking tab of the Budget panel", loc["notification_banking_cycle_started_notice_desc"])


class ToolGateTest(unittest.TestCase):
    """Before the start every tool is greyed with the reason, and the AI sees none."""

    def test_every_possible_helper_opens_with_the_cycle(self):
        text = _strip_comments(_read(POLICY_TRIGGERS))
        helpers = [(n, b) for n, b in _top_blocks(text) if n.startswith("banking_possible_")]
        self.assertEqual(len(helpers), 40)
        for name, body in helpers:
            with self.subTest(helper=name):
                self.assertTrue(_norm(body).startswith("{ te_banking_cycle_started_tt = yes "), body[:120])

    def test_every_enable_button_is_invisible_to_a_dormant_ai(self):
        # The buttons' ai_chance blocks read var:finance_cycle_value unguarded,
        # so a dormant entry's tool must not be visible to be scored.
        found = 0
        for path in BUTTONS:
            for name, body in _top_blocks(_strip_comments(_read(path))):
                if "possible = { banking_possible_" not in body:
                    continue
                found += 1
                with self.subTest(button=name):
                    visible = _norm(_key_block(body, "visible"))
                    self.assertTrue(visible.startswith("{ is_ai = yes te_banking_cycle_running = yes"), visible)
        self.assertEqual(found, 40)

    def test_the_monetary_controls_are_read_only_before_the_start(self):
        sgui = _top_block(_strip_comments(_read(MON_SGUIS)), "banking_mon_control_sgui")
        is_valid = _norm(_key_block(sgui, "is_valid"))
        self.assertTrue(is_valid.startswith("{ custom_tooltip = { text = te_banking_cycle_started_tt "
                                            "te_banking_controls_open = yes }"), is_valid[:160])

    def test_the_crisis_tools_guard_their_phase_test(self):
        # A dormant entry's greyed buttons evaluate these every frame.
        text = _strip_comments(_read(POLICY_TRIGGERS))
        for name in ("banking_possible_cb_emergency_liquidity_program", "banking_possible_cb_bank_holiday"):
            with self.subTest(helper=name):
                self.assertIn("te_banking_cycle_running = yes banking_cycle_is_recession = yes",
                              _norm(_top_block(text, name)))


# Every `has_journal_entry = je_banking_cycle` outside the entry, by the top-level
# block that holds it. They mean the entry object (its modifiers) or the panel,
# never "has a banking cycle" (spec § 8): that is te_banking_cycle_running.
ENTRY_OBJECT_READERS = {
    ("common/scripted_triggers/banking_policy_triggers.txt", "te_banking_cycle_running"),
    ("common/scripted_guis/te_monetary_sguis.txt", "banking_mon_control_sgui"),
    ("common/scripted_guis/te_system_tab_sguis.txt", "te_budget_banking_tab_sgui"),
    ("common/scripted_guis/te_system_tab_sguis.txt", "te_budget_banking_readout_sgui"),
    ("common/scripted_effects/te_monetary_effects.txt", "te_monetary_settle_modifier_home"),
    ("common/scripted_effects/te_monetary_effects.txt", "te_mon_mod_strip"),
    ("common/scripted_triggers/te_monetary_triggers.txt", "te_mon_mod_has"),
    ("common/scripted_effects/te_monetary_fx_effects.txt", "te_monetary_init_fx_variables"),
    ("common/scripted_effects/te_monetary_arrangement_effects.txt", "te_monetary_init_arrangement_variables"),
    ("common/on_actions/extra_on_actions.txt", "te_banking_law_change_cleanup"),
    ("common/on_actions/extra_on_actions.txt", "te_banking_economy_law_cleanup"),
    ("common/on_actions/te_banking_entry_on_actions.txt", "te_banking_entry_net"),
    ("common/script_values/te_banking_entry_values.txt", "te_banking_entry_missing_count"),
    # the self-check names the countries te_banking_entry_missing_count counts
    ("events/te_debug_banking_events.txt", "te_debug_banking.1"),
}

# Readers that mean "the cycle runs" and must ask te_banking_cycle_running.
CYCLE_READERS = {
    "common/scripted_effects/banking_cycle_effects.txt": (
        "banking_change_bubble_pressure", "banking_change_momentum", "banking_change_cycle_value",
        "banking_cycle_spread_contagion", "banking_crisis_wave_check_great_depression",
        "banking_cycle_post_event_refresh"),
    "common/scripted_effects/legacy_event_integration_effects.txt": ("banking_enactment_run_shock",),
    "common/scripted_effects/te_history_banking_effects.txt": (
        "te_history_record_banking_samples", "te_history_record_banking_marker"),
    "common/scripted_triggers/legacy_event_integration_triggers.txt": (
        "banking_is_bailout_recipient", "banking_can_offer_bailout"),
    "common/scripted_triggers/banking_debt_triggers.txt": ("banking_restructuring_shown",),
    "common/scripted_triggers/un_economy_triggers.txt": ("un_dev_fund_pays_into_pool",),
    "common/scripted_triggers/un_docket_triggers.txt": ("un_docket_loan_candidate",),
    "common/scripted_triggers/amendment_petition_triggers.txt": ("te_ap_economy_faltering",),
    "common/scripted_triggers/banking_policy_triggers.txt": ("banking_external_available",),
    "events/banking_cycle_events.txt": ("banking_cycle_events.68",),
    "events/society_technology_events.txt": ("society_technology_events.30",),
    "events/modern_election_events.txt": ("modern_election_events.15",),
    "events/extra_law_events.txt": ("extra_law_events.62",),
    "events/un_events.txt": ("un_events.35",),
}

# Readers that mean "may use the monetary controls": te_banking_controls_open.
CONTROL_READERS = {
    "common/scripted_effects/te_monetary_effects.txt": ("te_monetary_update_target",),
    "common/scripted_triggers/te_monetary_triggers.txt": ("te_mon_mandate_runs_bank",),
}


class ReaderTest(unittest.TestCase):
    """Widening an entry's gate breaks every has_journal_entry used as "has
    system X" (scripting_best_practices.md); each reader is in one row."""

    def test_every_entry_reader_is_an_entry_object_reader(self):
        seen = set()
        for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True) + \
                glob.glob(os.path.join(REPO, "events", "*.txt")):
            rel = os.path.relpath(path, REPO).replace(os.sep, "/")
            if rel == "common/journal_entries/je_banking.txt":
                continue
            text = _strip_comments(_read(path))
            if "has_journal_entry = je_banking_cycle" not in text:
                continue
            for name, body in _top_blocks(text):
                if "has_journal_entry = je_banking_cycle" in body:
                    seen.add((rel, name))
                    with self.subTest(reader=f"{rel}: {name}"):
                        self.assertIn((rel, name), ENTRY_OBJECT_READERS,
                                      "has a banking cycle is te_banking_cycle_running; "
                                      "add the block to ENTRY_OBJECT_READERS only if it reads the entry itself")
        self.assertEqual(seen, ENTRY_OBJECT_READERS, "a listed reader no longer reads the entry")

    def _check(self, table, trigger):
        for rel, names in table.items():
            text = _strip_comments(_read(os.path.join(REPO, rel)))
            for name in names:
                with self.subTest(reader=f"{rel}: {name}"):
                    self.assertIn(f"{trigger} = ", _top_block(text, name))

    def test_cycle_readers_ask_the_running_trigger(self):
        self._check(CYCLE_READERS, "te_banking_cycle_running")

    def test_control_readers_ask_the_controls_trigger(self):
        self._check(CONTROL_READERS, "te_banking_controls_open")

    def test_the_peg_tooltips_follow_the_controls(self):
        text = _strip_comments(_read(os.path.join(REPO, "events", "te_peg_events.txt")))
        self.assertEqual(text.count("limit = { te_banking_controls_open = yes }"), 8)


class PanelTest(unittest.TestCase):
    """The panels read the cycle only once it runs, and say why the rest waits."""

    @classmethod
    def setUpClass(cls):
        cls.dash = _read(DASH)
        cls.history = _read(HISTORY)
        cls.layout = _read(LAYOUT)

    def test_the_two_state_sguis(self):
        text = _strip_comments(_read(DASH_SGUIS))
        self.assertIn("is_shown = { te_banking_cycle_running = yes }",
                      _norm(_top_block(text, "banking_dash_cycle_running")))
        self.assertIn("is_shown = { te_banking_cycle_running = no }",
                      _norm(_top_block(text, "banking_dash_cycle_dormant")))
        self.assertIn("te_banking_controls_open = no", _top_block(text, "banking_dash_monetary_dormant_note"))

    def test_cycle_sections_wait_for_the_cycle(self):
        for text, name in ((self.dash, "te_banking_sec_active"), (self.history, "te_banking_history_panel"),
                           (self.dash, "te_banking_topbar_gate")):
            with self.subTest(type=name):
                self.assertIn(RUNNING_SGUI, _type_body(text, name))
        overview = _type_body(self.dash, "te_banking_overview_panel")
        # The bars, row 1 (phase, momentum) and row 2 (bubble, budget).
        self.assertEqual(overview.count(RUNNING_SGUI), 3)
        self.assertEqual(overview.count(DORMANT_SGUI), 1)
        bars = overview.index("te_je_scripted_bars = {}")
        self.assertLess(overview.rindex(RUNNING_SGUI, 0, bars), bars)

    def test_is_active_gates_only_the_containers(self):
        # JournalEntry.IsActive is true for a dormant entry, so it may gate only
        # the containers (the panel opened on an entry not yet activated), never
        # what reads the cycle.
        allowed = {"te_banking_status_sections", "te_banking_reference_sections", "te_banking_overview_panel",
                   "te_banking_topbar_gate"}
        for path in (DASH, HISTORY, LAYOUT):
            text = _strip_comments(_read(path))
            for m in re.finditer(r"type (\w+) = \w+ \{", text):
                body = _block_from(text, m.end() - 1)
                if "JournalEntry.IsActive" in body:
                    with self.subTest(type=m.group(1)):
                        self.assertIn(m.group(1), allowed)

    def test_the_dormant_notes(self):
        self.assertIn('text = "banking_dash_dormant_tools_note"', _type_body(self.dash, "te_banking_sec_interventions"))
        self.assertIn('text = "banking_dash_dormant_monetary_note"', _type_body(self.dash, "te_banking_sec_monetary"))
        self.assertIn('text = "banking_dash_how_start"', _type_body(self.layout, "te_banking_sec_how"))
        loc = _loc()
        for key in ("te_banking_cycle_started_tt", "banking_dash_not_started_value",
                    "banking_dash_not_started_conditions", "banking_dash_not_started_tt",
                    "banking_dash_not_started_met_tt", "banking_dash_dormant_tools_note",
                    "banking_dash_dormant_monetary_note", "banking_dash_how_start"):
            with self.subTest(key=key):
                self.assertIn(key, loc)

    def test_the_tab_tooltip_lists_no_conditions(self):
        # The tab opens with the entry, not with the cycle's start test.
        m = re.search(r'blockoverride "fourth_button_tooltip" \{\s*tooltip = "([^"]*)"', _read(BUDGET))
        self.assertTrue(m)
        self.assertNotIn("IsValidTooltip", m.group(1))

    def test_the_condition_count_restates_the_start_test(self):
        value = _norm(_top_block(_strip_comments(_read(DISPLAY_VALUES)), "banking_disp_unlock_met"))
        unlocked = _norm(_top_block(_strip_comments(_read(POLICY_TRIGGERS)), "te_banking_cycle_unlocked"))
        for test in ("has_technology_researched = stock_exchange",
                     "any_scope_state = { any_scope_building = { is_building_type = building_urban_center "
                     "level >= 5 } }"):
            with self.subTest(test=test):
                self.assertIn(test, value)
                self.assertIn(test, unlocked)


class SafetyNetTest(unittest.TestCase):
    """Old saves and released countries get the entry; once a game, a line says
    whether the engine had given it to everyone."""

    def test_the_net_adds_the_entry_where_it_should_be(self):
        text = _strip_comments(_read(NET))
        # The self-check arms on the yearly pulse; the net runs monthly since the
        # owner's EU game read BROKEN missing=3 (2026-10-17).
        self.assertIn(_norm("on_yearly_pulse_country = { on_actions = { te_banking_entry_selfcheck } }"), _norm(text))
        self.assertIn(_norm("on_monthly_pulse_country = { on_actions = { te_banking_entry_net } }"), _norm(text))
        net = _norm(_top_block(text, "te_banking_entry_net"))
        self.assertIn("limit = { te_banking_entry_expected = yes NOT = { has_journal_entry = je_banking_cycle } } "
                      "add_journal_entry = { type = je_banking_cycle }", net)
        self.assertIn("change_global_variable = { name = te_banking_entry_net_added add = 1 }", net)

    def test_the_selfcheck_logs_once_a_game(self):
        arm = _norm(_top_block(_strip_comments(_read(NET)), "te_banking_entry_selfcheck"))
        self.assertIn("NOT = { has_global_variable = te_banking_entry_selfcheck_armed }", arm)
        self.assertIn("trigger_event = { id = te_debug_banking.1 days = 30 }", arm)
        event = _read(SELFCHECK_EVENT)
        for verdict in ("TE_SELF_CHECK OK banking_entry_everywhere", "TE_SELF_CHECK BROKEN banking_entry_everywhere"):
            self.assertIn(verdict, event)
        # OK only when nothing was missing and the net added nothing: the net
        # would otherwise hide an engine that left records out.
        self.assertIn("te_banking_entry_missing_count < 1 te_banking_entry_net_added_g < 1", _norm(event))
        self.assertIn("banking_entry_everywhere", _read(PLAYTEST))
        # BROKEN names the countries still missing, one line each.
        self.assertIn("TE_SELF_CHECK INFO banking_entry_everywhere missing: [THIS.GetCountry.GetNameNoFormatting]", event)


if __name__ == "__main__":
    unittest.main()
