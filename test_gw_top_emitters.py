"""Country emissions rank separately even inside one market. Annual snapshots
and cumulative totals receive exactly the contributions added to the world.
The GUI draws the five largest from a list of their capitals, the bridges to
country scopes (GW-11: a datamodel, the Demographics States table's shape)."""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "global_warming_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_global_warming.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "global_warming_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "global_warming_triggers.txt")
VALUES = os.path.join(REPO, "common", "script_values", "global_warming_values.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "global_warming_sguis.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "extra_on_actions.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

SV = "JournalEntry.GetCountry.MakeScope.ScriptValue('{}')"
# The script values the list reads. The first four are read in a listed
# leader's scope, the rest in the viewer's.
DISPLAY_VALUES = ["gw_disp_own_emis", "gw_disp_own_share_pct", "gw_disp_own_cum", "gw_disp_is_treaty_bound",
                  "gw_disp_emitters_state", "gw_disp_emitters_total",
                  "gw_disp_emitters_more", "gw_disp_emitters_own_rank"]
LIST = "JournalEntry.GetCountry.MakeScope.GetList('gw_te_top')"


def _read(path, comments=False):
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    # a comment runs from a # outside a string to the end of the line
    return text if comments else re.sub(r'("[^"\n]*")|#[^\n]*', lambda m: m.group(1) or "", text)


def _body(text, name, prefix=""):
    m = re.search(rf"(?m)^{prefix}{re.escape(name)}\s*=\s*\w*\s*\{{", text)
    assert m, f"{name} not found"
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError("unclosed block")


def _loc(key):
    for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
        m = re.search(rf'^ {re.escape(key)}:\d* "(.*)"\s*$', _read(path, comments=True), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


def _callers(token):
    paths = (glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True)
             + glob.glob(os.path.join(REPO, "events", "**", "*.txt"), recursive=True))
    return sorted(os.path.relpath(p, REPO) for p in paths if token in _read(p))


class EmitterTestTest(unittest.TestCase):
    def test_a_ranked_emitter_emits_regardless_of_market_leadership(self):
        body = " ".join(_body(_read(TRIGGERS), "gw_is_ranked_emitter").split())
        self.assertEqual(body, "has_variable = gw_disp_country_emis "
                               "var:gw_disp_country_emis > 0")

    def test_one_test_for_the_count_the_list_the_rank_and_the_full_list(self):
        effects = _read(EFFECTS)
        refresh = _body(effects, "gw_top_emitters_refresh")
        # count, the list, the fifth, own country, rank
        self.assertEqual(refresh.count("gw_is_ranked_emitter = yes"), 5)
        full = _body(_read(SGUIS), "gw_top_emitters_sgui")
        self.assertIn("gw_is_ranked_emitter = yes", full)


class CumulativeTest(unittest.TestCase):
    def test_the_total_starts_at_zero_and_adds_the_year_s_figure(self):
        body = _body(_read(EFFECTS), "gw_accumulate_country_emissions_effect")
        self.assertRegex(body, r"hidden_effect = \{\s*if = \{\s*limit = \{ NOT = \{ has_variable = gw_disp_country_emis_cum \} \}\s*"
                               r"set_variable = \{\s*name = gw_disp_country_emis_cum\s*value = 0\s*\}\s*\}\s*"
                               r"change_variable = \{\s*name = gw_disp_country_emis_cum\s*add = var:gw_disp_country_emis\s*\}")

    def test_it_runs_in_the_step_that_adds_to_the_world_total(self):
        """Right after the leader's figure goes into the world total, so the
        cumulative is the sum of exactly the numbers the world received."""
        pulse = _body(_read(ON_ACTIONS), "global_warming_update_on_action")
        self.assertRegex(pulse, r"owner = \{\s*gw_snapshot_country_emissions_effect = yes\s*"
                                r"change_global_variable = \{\s*name = greenhouse_gas_emissions\s*"
                                r"add = var:gw_disp_country_emis\s*\}\s*"
                                r"gw_accumulate_country_emissions_effect = yes\s*\}")
        self.assertEqual(_callers("gw_accumulate_country_emissions_effect = yes"),
                         [os.path.relpath(ON_ACTIONS, REPO)])

    def test_country_totals_do_not_import_old_market_totals(self):
        effects = _read(EFFECTS)
        snapshot = _body(effects, "gw_snapshot_country_emissions_effect")
        self.assertIn("value = country_greenhouse_gas_emissions_script_value", snapshot)
        cumulative = _body(effects, "gw_accumulate_country_emissions_effect")
        self.assertNotIn("gw_disp_market_emis", snapshot + cumulative)
        self.assertNotIn("gw_is_market_leader", snapshot + cumulative)
        tt = _loc("gw_te_head_cum_tt")
        # The save-migration note left the player tooltip (GW-14, 2026-10-27).
        for phrase in ("Negative years", "Market joins", "Updated each January", "revolution's winner keeps"):
            self.assertIn(phrase, tt)
        self.assertNotIn("Existing saves", tt)


class RefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _read(EFFECTS)
        cls.refresh = _body(cls.effects, "gw_top_emitters_refresh")

    def test_the_refresh_runs_monthly_for_players_only(self):
        pulse = _body(_read(JE), "on_monthly_pulse", prefix=r"\t")
        self.assertRegex(pulse, r"limit = \{ is_player = yes \}\s*gw_top_emitters_refresh = yes")
        self.assertEqual(_callers("gw_top_emitters_refresh = yes"), [os.path.relpath(JE, REPO)])

    def test_the_refresh_writes_nothing_visible(self):
        self.assertTrue(self.refresh.lstrip().startswith("hidden_effect = {"))

    def test_the_list_is_rebuilt_largest_first(self):
        """GW-11: the five largest emitters' capitals, appended in rank order to a
        list cleared first, so the stored order is the rank."""
        self.assertNotIn("gw_top_emitter_slot", self.effects)
        self.assertRegex(self.refresh, r"if = \{\s*limit = \{ has_variable_list = gw_te_top \}\s*"
                                       r"clear_variable_list = gw_te_top\s*\}\s*ordered_country = \{")
        ordered = self.refresh[self.refresh.index("clear_variable_list = gw_te_top"):]
        ordered = ordered[ordered.index("ordered_country = {"):]
        ordered = ordered[:ordered.index("capital ?= {") + 400]
        self.assertRegex(ordered, r"limit = \{ gw_is_ranked_emitter = yes \}\s*order_by = gw_disp_own_emis\s*"
                                  r"max = 5\s*check_range_bounds = no\s*capital \?= \{\s*"
                                  r"save_temporary_scope_as = gw_te_capital\s*scope:gw_te_viewer = \{\s*"
                                  r"add_to_variable_list = \{ name = gw_te_top target = scope:gw_te_capital \}")

    def test_the_fifth_is_read_only_past_five(self):
        """An ordered_ position past the end clamps to the last element, so
        position 4 is read only when a sixth emitter exists."""
        self.assertRegex(self.refresh, r"limit = \{ var:gw_emitters_total > 5 \}\s*ordered_country = \{\s*"
                                       r"limit = \{ gw_is_ranked_emitter = yes \}\s*order_by = gw_disp_own_emis\s*"
                                       r"position = 4\s*save_temporary_scope_as = gw_te_fifth")
        self.assertRegex(self.refresh, r"else_if = \{\s*limit = \{ has_variable = gw_emitters_fifth_emis \}\s*"
                                       r"remove_variable = gw_emitters_fifth_emis")

    def test_the_old_slots_are_dropped(self):
        self.assertIn("gw_top_emitters_drop_slots = yes", self.refresh)
        drop = _body(self.effects, "gw_top_emitters_drop_slots")
        for var in [f"gw_emitter_{n}" for n in range(1, 6)] + ["gw_emitters_shown", "gw_emitters_own_slot"]:
            self.assertRegex(drop, rf"limit = \{{ has_variable = {var} \}}\s*remove_variable = {var}", var)

    def test_the_count_and_our_place(self):
        self.assertIn("set_variable = { name = gw_emitters_total value = 0 }", self.refresh)
        self.assertRegex(self.refresh, r"every_country = \{\s*limit = \{ gw_is_ranked_emitter = yes \}\s*"
                                       r"scope:gw_te_viewer = \{\s*change_variable = \{ name = gw_emitters_total add = 1 \}")
        self.assertIn("var:gw_disp_country_emis > scope:gw_te_viewer.var:gw_emitters_own_emis", self.refresh)
        self.assertIn("remove_variable = gw_emitters_own_emis", self.refresh)   # scratch, never left behind

    def test_the_self_check(self):
        """TE_SELF_CHECK gw_top_emitters_list: once a game, with an emitter in the world."""
        self.assertIn("gw_top_emitters_selfcheck = yes", self.refresh)
        check = _body(_read(EFFECTS, comments=True), "gw_top_emitters_selfcheck")
        self.assertRegex(check, r"NOT = \{ has_global_variable = te_selfcheck_gw_top_emitters_done \}\s*"
                                r"has_variable_list = gw_te_top\s*var:gw_emitters_total > 0")
        self.assertIn("set_global_variable = { name = te_selfcheck_gw_top_emitters_done value = 1 }", check)
        self.assertIn('debug_log = "TE_SELF_CHECK OK gw_top_emitters_list', check)
        self.assertIn('debug_log = "TE_SELF_CHECK BROKEN gw_top_emitters_list', check)
        for var in ("gw_sc_rows", "gw_sc_rises", "gw_sc_expected"):
            self.assertIn(f"remove_variable = {var}", check)


class GuardTest(unittest.TestCase):
    def test_every_read_is_guarded(self):
        values = _read(VALUES)
        for name in DISPLAY_VALUES:
            with self.subTest(value=name):
                body = _body(values, name)
                for var in re.findall(r"(?<![\w.])var:(\w+)", body):
                    self.assertIn(f"has_variable = {var}", body)
                for var in re.findall(r"global_var:(\w+)", body):
                    self.assertIn(f"has_global_variable = {var}", body)

    def test_the_share_never_divides_by_zero(self):
        body = _body(_read(VALUES), "gw_disp_own_share_pct")
        self.assertLess(body.index("global_var:gw_g_global_emis > 0"), body.index("divide"))
        self.assertRegex(body, r"min = 0\s*max = 100\s*$")

    def test_the_state_code(self):
        body = _body(_read(VALUES), "gw_disp_emitters_state")
        self.assertRegex(body, r"value = 0\s*if = \{\s*limit = \{ gw_has_country_yearly_figures = yes \}\s*value = 1\s*"
                               r"if = \{\s*limit = \{ has_variable = gw_emitters_total \}\s*value = 2")


class TooltipBuilderTest(unittest.TestCase):
    def test_the_builders_have_a_state_root(self):
        """Gotcha #27: a country's lines gather under its first appearance, so no
        listed country may also be the root."""
        sguis = _read(SGUIS)
        for name in ("gw_te_members_sgui", "gw_top_emitters_sgui"):
            with self.subTest(sgui=name):
                body = _body(sguis, name)
                self.assertIn("scope = state", body)
                self.assertIn("is_valid = { always = no }", body)
        gui = _read(GUI)
        self.assertIn("GetScriptedGui('gw_top_emitters_sgui').ExecuteTooltip( GuiScope.SetRoot( "
                      "JournalEntry.GetCountry.GetCapital.MakeScope ).End )", gui)
        self.assertIn("GetScriptedGui('gw_te_members_sgui').ExecuteTooltip( GuiScope.SetRoot( State.MakeScope ).End )",
                      _loc("gw_te_row_tt"))

    def test_the_full_list_is_in_the_rows_order(self):
        full = _body(_read(SGUIS), "gw_top_emitters_sgui")
        self.assertIn("order_by = gw_disp_own_emis", full)
        self.assertIn("check_range_bounds = no", full)
        # GW-11: the hover starts below the five rows and stops at 25.
        self.assertIn("var:gw_disp_country_emis < ROOT.owner.var:gw_emitters_fifth_emis", full)
        self.assertIn("max = 25", full)
        self.assertIn("custom_tooltip_no_bullet = gw_te_all_intro_capped", full)
        members = _body(_read(SGUIS), "gw_te_members_sgui")
        self.assertIn("market_capital = ROOT.owner.market_capital", members)


class RowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.row = _body(cls.gui, "gw_emitter_row", prefix=r"\ttype ")
        cls.header = _body(cls.gui, "gw_emitter_header", prefix=r"\ttype ")
        cls.section = _body(cls.gui, "te_gw_sec_emitters", prefix=r"\ttype ")

    def test_the_section_follows_mitigation_policies(self):
        composer = _body(self.gui, "te_gw_status_sections", prefix=r"\ttype ")
        # Fossil Transition (#660) comes after the two.
        self.assertEqual(re.findall(r"^\t\t(te_gw_sec_\w+) = \{", composer, re.M)[:2],
                         ["te_gw_sec_policies", "te_gw_sec_emitters"])

    def test_the_rows_are_a_datamodel_over_the_list(self):
        """GW-11: one row type, drawn once per item of the viewer's gw_te_top list,
        its datacontext the item's state; no slot variables, no row blocks."""
        self.assertTrue(self.row.lstrip().startswith("size = { 480 50 }\n\n\t\tflowcontainer = {"), self.row[:80])
        self.assertNotIn('block "', self.row)
        self.assertRegex(self.section, rf'datamodel = "\[{re.escape(LIST)}\]"\s*item = \{{\s*gw_emitter_row = \{{\s*'
                                       r'datacontext = "\[Scope\.GetState\]"\s*\}\s*\}')
        self.assertEqual(self.section.count("gw_emitter_row = {"), 1)
        self.assertNotIn("Var('gw_emitter_", self.gui)
        self.assertIn(f'visible = "[Not( IsDataModelEmpty( {LIST} ) )]"', self.section)   # the headings
        # "Our country" is the local player's own row.
        self.assertRegex(self.row, r'visible = "\[State\.GetCountry\.IsLocalPlayer\]"\s*text = "gw_te_ours"')

    def test_the_name_has_the_whole_line(self):
        self.assertRegex(self.row, r'minimumsize = \{ 480 -1 \}\s*maximumsize = \{ 480 -1 \}\s*autoresize = yes\s*'
                                   r'elide = right\s*align = left\|nobaseline\s*using = fontsize_medium\s*'
                                   r'default_format = "#tooltippable"\s*text = "gw_te_row_name"')

    def test_cells_fill_the_column_under_their_headings(self):
        row_line = self.row[self.row.index('text = "gw_te_row_name"') + 1:]
        widths = [int(w) for w in re.findall(r"^\t{4}widget = \{\s*size = \{ (\d+) \d+ \}", row_line, re.M)]
        self.assertEqual(widths, [44, 120, 80, 120, 116])
        self.assertEqual(sum(widths), 480)
        heads = [int(w) for w in re.findall(r"^\t{2}widget = \{\s*size = \{ (\d+) \d+ \}", self.header, re.M)]
        self.assertEqual(heads, widths)
        self.assertIn('tiny_flag = {\n\t\t\t\t\t\tparentanchor = left|vcenter\n\t\t\t\t\t\tdatacontext = "[State.GetCountry]"',
                      row_line)
        cells = re.findall(r'text = "(gw_te_row_\w+)"', row_line)
        self.assertEqual(cells, ["gw_te_row_annual", "gw_te_row_share", "gw_te_row_cum"])
        self.assertEqual(re.findall(r'text = "(gw_te_head_\w+)"', self.header),
                         ["gw_te_head_annual", "gw_te_head_share", "gw_te_head_cum"])

    def test_the_treaty_mark(self):
        self.assertRegex(self.row, r"visible = \"\[EqualTo_CFixedPoint\( State\.GetCountry\.MakeScope\.ScriptValue\("
                                   r"'gw_disp_is_treaty_bound'\), '\(CFixedPoint\)1' \)\]\"\s*texture = \"gfx/interface/icons/"
                                   r"diplomatic_treaties_articles_icons/enforce_emissions_reduction\.dds\"\s*"
                                   r'tooltip = "gw_te_treaty_tt"')
        body = _body(_read(VALUES), "gw_disp_is_treaty_bound")
        self.assertIn("gw_bound_by_emissions_treaty = yes", body)

    def test_more_our_place_and_the_waiting_lines(self):
        state = SV.format("gw_disp_emitters_state")
        for code, key in ((0, "gw_emis_pending"), (1, "gw_te_list_pending")):
            self.assertRegex(self.section, rf"visible = \"\[EqualTo_CFixedPoint\( {re.escape(state)}, "
                                           rf"'\(CFixedPoint\){code}' \)\]\"\s*align = hcenter\|nobaseline\s*"
                                           rf'text = "{key}"')
        self.assertRegex(self.section, rf"minimumsize = \{{ 480 -1 \}}\s*spacing = 4\s*visible = \"\[EqualTo_CFixedPoint\( "
                                       rf"{re.escape(state)}, '\(CFixedPoint\)2' \)\]\"")
        self.assertRegex(self.section, rf"GreaterThanOrEqualTo_CFixedPoint\( {re.escape(SV.format('gw_disp_emitters_total'))}, "
                                       r"'\(CFixedPoint\)6' \)\]\"\s*align = hcenter\|nobaseline\s*text = \"gw_te_more\"")
        rank = re.escape(SV.format("gw_disp_emitters_own_rank"))
        self.assertRegex(self.section, rf"GreaterThanOrEqualTo_CFixedPoint\( {rank}, '\(CFixedPoint\)6' \)\]\"\s*"
                                       r'align = hcenter\|nobaseline\s*text = "gw_te_own_rank"')
        self.assertRegex(self.section, rf"EqualTo_CFixedPoint\( {rank}, '\(CFixedPoint\)0' \)\]\"\s*"
                                       r'align = hcenter\|nobaseline\s*text = "gw_te_own_none"')

    def test_the_section_is_open_by_default(self):
        self.assertIn("GetVariableSystem.Toggle('gw_emitters_closed')", self.section)
        self.assertIn("visible = \"[Not(GetVariableSystem.Exists('gw_emitters_closed'))]\"\n\n\t\t\tgw_text",
                      self.section)


class LocTest(unittest.TestCase):
    def test_the_row_figures_are_the_leader_s(self):
        for key, value in (("gw_te_row_annual", "gw_disp_own_emis"), ("gw_te_row_share", "gw_disp_own_share_pct"),
                           ("gw_te_row_cum", "gw_disp_own_cum")):
            self.assertIn(f"State.GetCountry.MakeScope.ScriptValue('{value}')", _loc(key), key)
        self.assertEqual(_loc("gw_te_row_name"), "[State.GetCountry.GetNameNoFormatting]")

    def test_country_rows_and_market_overview_have_separate_snapshots(self):
        values = _read(VALUES)
        self.assertIn("add = var:gw_disp_country_emis", _body(values, "gw_disp_own_emis"))
        self.assertIn("add = var:gw_disp_market_emis", _body(values, "gw_market_emis_raw"))
        for name in ("gw_disp_own_emis", "gw_market_emis_display"):
            self.assertIn("multiply = gw_emission_display_scale", _body(values, name))


if __name__ == "__main__":
    unittest.main()
