"""Global Warming's Top Emitters list (the owner, 2026-09-30: "show the top
emitters, so the player knows who to target for climate agreements... show
current and cumulative emissions").

The panel lists the five markets emitting most, each named by its leader, with
its annual emissions, its share of the world's and its cumulative total. There
is no datamodel of markets a journal-entry widget can walk, so, as the Space
Race's Rivals rows do (test_space_race_rivals.py), a monthly refresh for players
only stores how many markets emit and the first five leaders' capitals on the
viewer; the figures on each row are read live from the listed leader.

The cumulative total is a new per-leader variable, added in the same yearly step
that adds the market's figure to the world total.
"""
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
                  "gw_disp_emitters_state", "gw_disp_emitters_total", "gw_disp_emitters_shown",
                  "gw_disp_emitters_more", "gw_disp_emitters_own_slot", "gw_disp_emitters_own_rank"]


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
    def test_a_ranked_emitter_leads_its_market_and_emits(self):
        body = " ".join(_body(_read(TRIGGERS), "gw_is_ranked_emitter").split())
        self.assertEqual(body, "gw_is_market_leader = yes has_variable = gw_disp_market_emis "
                               "var:gw_disp_market_emis > 0")

    def test_one_test_for_the_count_the_slots_the_rank_and_the_full_list(self):
        effects = _read(EFFECTS)
        refresh = _body(effects, "gw_top_emitters_refresh")
        self.assertEqual(refresh.count("gw_is_ranked_emitter = yes"), 3)   # count, own leader, rank
        slot = _body(effects, "gw_top_emitter_slot")
        self.assertEqual(slot.count("gw_is_ranked_emitter = yes"), 2)      # count check, ordered_country
        full = _body(_read(SGUIS), "gw_top_emitters_sgui")
        self.assertIn("limit = { gw_is_ranked_emitter = yes }", full)


class CumulativeTest(unittest.TestCase):
    def test_the_total_starts_at_zero_and_adds_the_year_s_figure(self):
        body = _body(_read(EFFECTS), "gw_accumulate_market_emissions_effect")
        self.assertRegex(body, r"hidden_effect = \{\s*if = \{\s*limit = \{ NOT = \{ has_variable = gw_disp_market_emis_cum \} \}\s*"
                               r"set_variable = \{\s*name = gw_disp_market_emis_cum\s*value = 0\s*\}\s*\}\s*"
                               r"change_variable = \{\s*name = gw_disp_market_emis_cum\s*add = var:gw_disp_market_emis\s*\}")

    def test_it_runs_in_the_step_that_adds_to_the_world_total(self):
        """Right after the leader's figure goes into the world total, so the
        cumulative is the sum of exactly the numbers the world received."""
        pulse = _body(_read(ON_ACTIONS), "global_warming_update_on_action")
        self.assertRegex(pulse, r"owner = \{\s*gw_snapshot_market_emissions_effect = yes\s*"
                                r"change_global_variable = \{\s*name = greenhouse_gas_emissions\s*"
                                r"add = var:gw_disp_market_emis\s*\}\s*"
                                r"gw_accumulate_market_emissions_effect = yes\s*\}")
        self.assertEqual(_callers("gw_accumulate_market_emissions_effect = yes"),
                         [os.path.relpath(ON_ACTIONS, REPO)])

    def test_the_rule_is_written_down(self):
        effects = _read(EFFECTS, comments=True)
        comment = effects[:effects.index("gw_accumulate_market_emissions_effect = {")]
        comment = comment[comment.rindex("# The market's CUMULATIVE emissions"):]
        for phrase in ("THE RULE WHEN LEADERSHIP CHANGES", "keeps its total but adds nothing",
                       "starts from its own total", "when markets merge", "revolution"):
            self.assertIn(phrase, comment)
        tt = _loc("gw_te_head_cum_tt")
        for phrase in ("keeps its total but adds nothing", "starts from its own total", "When markets merge"):
            self.assertIn(phrase, tt)


class RefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _read(EFFECTS)
        cls.refresh = _body(cls.effects, "gw_top_emitters_refresh")
        cls.slot = _body(cls.effects, "gw_top_emitter_slot")

    def test_the_refresh_runs_monthly_for_players_only(self):
        pulse = _body(_read(JE), "on_monthly_pulse", prefix=r"\t")
        self.assertRegex(pulse, r"limit = \{ is_player = yes \}\s*gw_top_emitters_refresh = yes")
        self.assertEqual(_callers("gw_top_emitters_refresh = yes"), [os.path.relpath(JE, REPO)])

    def test_the_refresh_writes_nothing_visible(self):
        self.assertTrue(self.refresh.lstrip().startswith("hidden_effect = {"))

    def test_five_slots_each_checked_before_it_is_read(self):
        slots = re.findall(r"gw_top_emitter_slot = \{ N = (\d) POS = (\d) \}", self.refresh)
        self.assertEqual(slots, [(str(n), str(n - 1)) for n in range(1, 6)])
        # an ordered_ position past the end clamps to the last element, so count first
        self.assertRegex(self.slot, r"^\s*if = \{\s*limit = \{\s*any_country = \{\s*gw_is_ranked_emitter = yes\s*"
                                    r"count >= \$N\$\s*\}\s*\}\s*ordered_country = \{")
        ordered = self.slot[self.slot.index("ordered_country = {"):]
        self.assertIn("order_by = gw_disp_own_emis", ordered)
        self.assertIn("position = $POS$", ordered)
        # a capital saved under the slot's own name, so a slot never inherits the previous one's
        self.assertIn("capital ?= { save_scope_as = gw_te_capital_$N$ }", ordered)
        self.assertRegex(self.slot, r"limit = \{ exists = scope:gw_te_capital_\$N\$ \}\s*"
                                    r"set_variable = \{ name = gw_emitter_\$N\$ value = scope:gw_te_capital_\$N\$ \}")

    def test_an_empty_slot_is_cleared(self):
        cleared = re.findall(r"else_if = \{\s*limit = \{ has_variable = gw_emitter_\$N\$ \}\s*"
                             r"remove_variable = gw_emitter_\$N\$\s*\}", self.slot)
        self.assertEqual(len(cleared), 2)   # no capital; fewer emitters than N

    def test_the_rows_shown_are_the_filled_slots_from_the_first(self):
        shown = self.refresh[self.refresh.index("name = gw_emitters_shown value = 0"):]
        for n in range(1, 6):
            self.assertRegex(shown, rf"limit = \{{ has_variable = gw_emitter_{n} \}}\s*"
                                    rf"set_variable = \{{ name = gw_emitters_shown value = {n} \}}")
        # nested, each test inside the one before, so a hole stops the count
        for n in range(1, 5):
            self.assertRegex(shown, rf"value = {n} \}}\s*if = \{{\s*limit = \{{ has_variable = gw_emitter_{n + 1} \}}")

    def test_the_count_and_our_place(self):
        self.assertIn("set_variable = { name = gw_emitters_total value = 0 }", self.refresh)
        self.assertRegex(self.refresh, r"every_country = \{\s*limit = \{ gw_is_ranked_emitter = yes \}\s*"
                                       r"scope:gw_te_viewer = \{\s*change_variable = \{ name = gw_emitters_total add = 1 \}")
        self.assertIn("set_variable = { name = gw_emitters_own_slot value = 0 }", self.refresh)
        self.assertIn("scope:gw_te_viewer = {\n\t\t\t\t\tset_variable = { name = gw_emitters_own_slot value = $N$ }",
                      self.slot)
        self.assertIn("var:gw_disp_market_emis > scope:gw_te_viewer.var:gw_emitters_own_emis", self.refresh)
        self.assertIn("remove_variable = gw_emitters_own_emis", self.refresh)   # scratch, never left behind


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
        self.assertRegex(body, r"value = 0\s*if = \{\s*limit = \{ gw_has_yearly_figures = yes \}\s*value = 1\s*"
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
        members = _body(_read(SGUIS), "gw_te_members_sgui")
        self.assertIn("market_capital ?= { owner ?= ROOT.owner }", members)


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

    def test_the_row_reads_its_slot_only_when_shown(self):
        self.assertTrue(self.row.lstrip().startswith('size = { 480 50 }\n\t\tblock "row_visible" {}'), self.row[:80])
        outer = self.row[:self.row.index("flowcontainer = {")]
        self.assertNotIn('block "row_context"', outer)          # the datacontext is on the inner container
        self.assertIn('block "row_context" {}', self.row[self.row.index("flowcontainer = {"):])

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

    def test_five_rows_gated_on_the_filled_count(self):
        shown = SV.format("gw_disp_emitters_shown")
        self.assertEqual(self.section.count("gw_emitter_row = {"), 5)
        for n in range(1, 6):
            self.assertRegex(self.section, rf'blockoverride "row_visible" \{{\s*visible = "\[GreaterThanOrEqualTo_CFixedPoint\( '
                                           rf"{re.escape(shown)}, '\(CFixedPoint\){n}' \)\]\"\s*\}}\s*"
                                           rf'blockoverride "row_context" \{{\s*datacontext = '
                                           rf"\"\[JournalEntry\.GetCountry\.MakeScope\.Var\('gw_emitter_{n}'\)\.GetState\]\"\s*\}}\s*"
                                           rf'blockoverride "row_ours" \{{\s*visible = "\[EqualTo_CFixedPoint\( '
                                           rf"{re.escape(SV.format('gw_disp_emitters_own_slot'))}, '\(CFixedPoint\){n}' \)\]\"")
        self.assertIn(f"visible = \"[GreaterThanOrEqualTo_CFixedPoint( {shown}, '(CFixedPoint)1' )]\"\n\t\t\t\t}}",
                      self.section)   # the headings

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

    def test_annual_is_the_overview_s_figure(self):
        """For a leader, gw_disp_own_emis reads the same variable the overview's
        Our Market's Emissions reads through market_capital.owner."""
        values = _read(VALUES)
        self.assertIn("add = var:gw_disp_market_emis", _body(values, "gw_disp_own_emis"))
        self.assertIn("add = var:gw_disp_market_emis", _body(values, "gw_market_emis_raw"))
        self.assertIn("value = gw_market_emis_raw", _body(values, "gw_market_emis_display"))
        for name in ("gw_disp_own_emis", "gw_market_emis_display"):
            self.assertIn("multiply = gw_emission_display_scale", _body(values, name))
        self.assertIn("ScriptValue('gw_market_emis_display')|K]/yr", _loc("gw_emis_market_value"))
        self.assertIn("ScriptValue('gw_disp_own_emis')|K]/yr", _loc("gw_te_row_annual"))


if __name__ == "__main__":
    unittest.main()
