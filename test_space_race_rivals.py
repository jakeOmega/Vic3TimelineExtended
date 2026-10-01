"""Rivals' estimated progress: "a bar with some fuzz" (owner's play-test, 2026-09-29).

The Rivals section shows up to five rivals as estimate rows. Each rival carries
one random offset per milestone (sr_fuzz_<m>, -1 to +1), drawn again a year
after it was drawn. The viewer sees progress + offset x band, inside a band of
+-25% of the goal that the viewer's covert network in the rival narrows to
+-10% / +-5% (intelligence tier 1 / 2), so the true figure is always inside the
band. A monthly refresh, for players only, fills the viewer's slots (how many
rivals, and the first five's capitals); the numbers are read live, with the
rival passed in to the script values as scope:sr_rival.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "space_race_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "space_race_triggers.txt")
VALUES = os.path.join(REPO, "common", "script_values", "space_race_values.txt")
DISPLAY = os.path.join(REPO, "common", "script_values", "space_race_display_values.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "space_race_on_actions.txt")
COVERT_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "covert_warfare_effects.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
              "interstellar_probe", "solar_colonization")  # sr_rivals_sgui op order
FUZZ_STEPS = [-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1]
ROW_VALUE = ("[FixedPointToFloat( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope )"
             ".AddScope( 'sr_rival', State.GetCountry.MakeScope ).ScriptValue('{}') )]")


def _read(path, comments=False):
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    return text if comments else re.sub(r"#[^\n]*", "", text)


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


def _root(text, name):
    """A journal root with the body of the milestone's own type it wraps
    (te_sr_<m>_status), as the journal renders it."""
    m = re.search(rf'name = "{name}"', text)
    assert m, name
    start = text.rfind("flowcontainer = {", 0, m.start())
    root = _body(text[start:], "flowcontainer")
    for wrapped in re.findall(r"^\t(te_sr_\w+_(?:overview|status)) = \{\}$", root, re.M):
        root += "\n" + _body(text, wrapped, prefix=r"\ttype ")
    return root


def _loc(key):
    for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
        m = re.search(rf'^ {re.escape(key)}:\d* "(.*)"\s*$', _read(path, comments=True), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


class RivalTestTest(unittest.TestCase):
    def test_one_rival_test_for_list_rows_and_refresh(self):
        body = _body(_read(TRIGGERS), "sr_is_rival").split()
        self.assertEqual(" ".join(body), "NOT = { THIS = ROOT } has_variable = sr_active_$MILESTONE$ "
                                         "sr_ai_should_participate = yes")
        effects = _read(EFFECTS)
        for name in ("sr_rivals_participants_base", "sr_rivals_estimate_refresh_base", "sr_rival_slot"):
            self.assertIn("sr_is_rival = { MILESTONE = $MILESTONE$ }", _body(effects, name), name)
        self.assertNotIn("has_variable = sr_active_$MILESTONE$\n\t\t\t\tsr_ai_should_participate",
                         _body(effects, "sr_rivals_participants_base"))


class RefreshTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _read(EFFECTS)

    def test_the_refresh_runs_for_players_only(self):
        pulse = _body(_read(ON_ACTIONS), "space_race_on_action")
        self.assertRegex(pulse, r"limit = \{ is_player = yes \}\s*sr_rivals_estimate_refresh = yes")
        callers = [p for p in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True)
                   + glob.glob(os.path.join(REPO, "events", "*.txt"))
                   if "sr_rivals_estimate_refresh = yes" in _read(p)]
        self.assertEqual([os.path.relpath(p, REPO) for p in callers],
                         [os.path.relpath(ON_ACTIONS, REPO)])

    def test_every_milestone_is_refreshed(self):
        body = _body(self.effects, "sr_rivals_estimate_refresh")
        self.assertEqual(re.findall(r"MILESTONE = (\w+)", body), list(MILESTONES))

    def test_the_offset_is_drawn_when_missing_or_a_year_old(self):
        body = _body(self.effects, "sr_rivals_estimate_refresh_base")
        self.assertRegex(body, r"limit = \{ NOT = \{ has_variable = sr_fuzz_until_\$MILESTONE\$ \} \}\s*"
                               r"sr_roll_rival_fuzz = \{ MILESTONE = \$MILESTONE\$ \}")
        self.assertRegex(body, r"else_if = \{\s*limit = \{ var:sr_fuzz_until_\$MILESTONE\$ <= te_history_month_index \}\s*"
                               r"sr_roll_rival_fuzz = \{ MILESTONE = \$MILESTONE\$ \}")

    def test_the_draw(self):
        roll = _body(self.effects, "sr_roll_rival_fuzz")
        branches = re.findall(r"(\d+) = \{ set_variable = \{ name = sr_fuzz_\$MILESTONE\$ value = (-?[\d.]+) \} \}", roll)
        self.assertEqual([w for w, _ in branches], ["1"] * 9)  # literal, even weights
        self.assertEqual([float(v) for _, v in branches], FUZZ_STEPS)
        self.assertIn("set_variable = { name = sr_fuzz_until_$MILESTONE$ value = te_history_month_index }", roll)
        self.assertIn("change_variable = { name = sr_fuzz_until_$MILESTONE$ add = 12 }", roll)

    def test_five_slots_each_checked_before_it_is_read(self):
        body = _body(self.effects, "sr_rivals_estimate_refresh_base")
        slots = re.findall(r"sr_rival_slot = \{ MILESTONE = \$MILESTONE\$ N = (\d) POS = (\d) \}", body)
        self.assertEqual(slots, [(str(n), str(n - 1)) for n in range(1, 6)])
        slot = _body(self.effects, "sr_rival_slot")
        # an ordered_ position past the end clamps to the last element, so count first
        self.assertRegex(slot, r"any_country = \{\s*sr_is_rival = \{ MILESTONE = \$MILESTONE\$ \}\s*count >= \$N\$")
        self.assertIn("order_by = sr_rival_est_open_$MILESTONE$", slot)
        self.assertIn("position = $POS$", slot)
        self.assertIn("set_variable = { name = sr_rival_$MILESTONE$_$N$ value = scope:sr_rival_capital }", slot)

    def test_cleanup(self):
        clear = _body(self.effects, "sr_clear_rival_slots")
        for var in ["sr_rival_total_$MILESTONE$"] + [f"sr_rival_$MILESTONE$_{n}" for n in range(1, 6)]:
            self.assertIn(f"limit = {{ has_variable = {var} }} remove_variable = {var}", clear)
        cleanup = _body(self.effects, "sr_cleanup_milestone_if_inactive_base")
        for var in ("sr_fuzz_$MILESTONE$", "sr_fuzz_until_$MILESTONE$"):
            self.assertRegex(cleanup, rf"has_variable = {re.escape(var)}\s*\}}\s*remove_variable = {re.escape(var)}")
        self.assertIn("sr_clear_rival_slots = { MILESTONE = $MILESTONE$ }", cleanup)
        self.assertIn("sr_clear_rival_slots = { MILESTONE = $MILESTONE$ }",
                      _body(self.effects, "sr_rivals_estimate_refresh_base").split("else = {")[-1])


class BandTest(unittest.TestCase):
    def test_the_band_narrows_with_the_viewer_s_network(self):
        values = _read(VALUES)
        for name, value in (("sr_rival_band_open", "0.25"), ("sr_rival_band_tier_1", "0.1"),
                            ("sr_rival_band_tier_2", "0.05")):
            self.assertEqual(_body(values, name).split(), ["value", "=", value])
        band = _body(_read(DISPLAY), "sr_disp_rival_band")
        self.assertRegex(band, r"value = sr_rival_band_open\s*if = \{\s*limit = \{ root = \{ sr_has_intel_tier = "
                               r"\{ TARGET = scope:sr_rival TIER = 2 \} \} \}\s*value = sr_rival_band_tier_2")
        self.assertRegex(band, r"else_if = \{\s*limit = \{ root = \{ sr_has_intel_tier = "
                               r"\{ TARGET = scope:sr_rival TIER = 1 \} \} \}\s*value = sr_rival_band_tier_1")

    def test_the_network_test_reads_the_covert_system_s_own_names(self):
        tier = _body(_read(TRIGGERS), "sr_has_intel_tier")
        for token in ("has_variable_list = iw_nets", "variable = iw_nets", "var:iw_target ?= $TARGET$",
                      "has_variable = iw_net_intel_tier", "var:iw_net_intel_tier >= $TIER$"):
            self.assertIn(token, tier)
        covert = _read(COVERT_EFFECTS)
        for name in ("iw_nets", "iw_target", "iw_net_intel_tier"):
            self.assertIn(name, covert, f"the covert system no longer writes {name}")

    def test_the_truth_is_always_inside_the_band(self):
        """est = progress + offset x band, the band drawn around est: |truth - est| <= band."""
        for band in (0.25, 0.1, 0.05):
            for fuzz in FUZZ_STEPS:
                for truth in (0, 0.02, 0.3, 0.5, 0.97, 1):
                    est = min(1, max(0, truth + fuzz * band))
                    lo, hi = max(0, est - band), min(1, est + band)
                    # within the engine's fixed-point step (0.001), invisible on a 380 px bar
                    self.assertTrue(lo - 1e-3 <= truth <= hi + 1e-3, (band, fuzz, truth))


class EstimateValueTest(unittest.TestCase):
    def test_each_milestone_s_estimate(self):
        display = _read(DISPLAY)
        values = _read(VALUES)
        for m in MILESTONES:
            with self.subTest(milestone=m):
                est = _body(display, f"sr_disp_rival_est_{m}")
                self.assertRegex(est, rf"scope:sr_rival = \{{\s*add = sr_progress_{m}_value\s*\}}\s*divide = sr_{m}_goal")
                self.assertRegex(est, rf"limit = \{{ has_variable = sr_fuzz_{m} \}}\s*add = \{{\s*value = var:sr_fuzz_{m}\s*"
                                      r"multiply = sr_disp_rival_band")
                self.assertEqual(_body(display, f"sr_disp_rival_lo_{m}").split(),
                                 ["value", "=", f"sr_disp_rival_est_{m}", "subtract", "=", "sr_disp_rival_band",
                                  "min", "=", "0", "max", "=", "1"])
                self.assertEqual(_body(display, f"sr_disp_rival_hi_{m}").split(),
                                 ["value", "=", f"sr_disp_rival_est_{m}", "add", "=", "sr_disp_rival_band",
                                  "min", "=", "0", "max", "=", "1"])
                self.assertIn(f"has_variable = sr_rival_total_{m} }} value = var:sr_rival_total_{m}",
                              _body(display, f"sr_disp_rival_total_{m}"))
                open_est = _body(values, f"sr_rival_est_open_{m}")
                self.assertRegex(open_est, rf"limit = \{{ has_variable = sr_fuzz_{m} \}}\s*add = \{{\s*"
                                           rf"value = var:sr_fuzz_{m}\s*multiply = sr_rival_band_open")


class RowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)

    def test_the_row_is_fixed_width_and_reads_its_slot_only_when_shown(self):
        row = _body(self.gui, "te_sr_rival_row", prefix=r"\ttype ")
        self.assertTrue(row.lstrip().startswith("size = { 480 42 }\n\t\tblock \"row_visible\" {}"), row[:80])
        inner = row[row.index("flowcontainer = {"):]
        self.assertIn('block "row_context" {}', inner)          # the datacontext is on the inner container
        self.assertNotIn('block "row_context"', row[:row.index("flowcontainer = {")])
        # round 3: the name has the whole line (a country's name runs to 48
        # characters); the bar and the band in words share the line beneath,
        # 380 + 8 + 92 = 480
        self.assertIn("direction = vertical", inner[:inner.index("textbox")])
        self.assertIn("minimumsize = { 480 -1 }\n\t\t\t\tmaximumsize = { 480 -1 }", inner)
        self.assertIn("minimumsize = { 92 -1 }\n\t\t\t\t\tmaximumsize = { 92 -1 }", inner)
        self.assertIn("size = { 380 14 }", inner)
        self.assertIn("white_progressbar_horizontal", inner)
        self.assertRegex(inner, r'default_progressbar_horizontal = \{\s*size = \{ 100% 100% \}\s*'
                                r'blockoverride "background" \{\}\s*blockoverride "frame" \{\}')
        self.assertIn('block "row_est" {}', inner)
        self.assertIn("progressbar_marker.dds", inner)

    def test_the_section_has_five_rows(self):
        section = _body(self.gui, "te_sr_sec_rivals", prefix=r"\ttype ")
        self.assertEqual(re.findall(r'block "rival_(\d)" \{\}', section), ["1", "2", "3", "4", "5"])
        self.assertEqual(section.count("te_sr_rival_row = {"), 5)
        self.assertIn('text = "sr_rivals_none"', section)

    def test_each_root_feeds_its_own_milestone(self):
        for op, m in enumerate(MILESTONES):
            with self.subTest(milestone=m):
                root = _root(self.gui, f"widget_je_space_race_{m}")
                total = f"JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_rival_total_{m}')"
                self.assertIn(f"[EqualTo_CFixedPoint( {total}, '(CFixedPoint)0' )]", root)
                for n in range(1, 6):
                    self.assertRegex(root, rf'blockoverride "sr_rival_{n}" \{{\s*visible = "\[GreaterThanOrEqualTo_CFixedPoint\( '
                                           rf"{re.escape(total)}, '\(CFixedPoint\){n}' \)\]\"")
                    self.assertRegex(root, rf'blockoverride "sr_rival_{n}_context" \{{\s*datacontext = '
                                           rf"\"\[JournalEntry\.GetCountry\.MakeScope\.Var\('sr_rival_{m}_{n}'\)\.GetState\]\"")
                for part in ("lo", "hi", "est"):
                    self.assertIn(f'value = "{ROW_VALUE.format(f"sr_disp_rival_{part}_{m}")}"', root)
                self.assertIn(f'tooltip = "je_space_race_widget_rival_tt_{m}"', root)
                self.assertIn(f'text = "je_space_race_widget_rival_range_{m}"', root)
                self.assertRegex(root, rf"GreaterThanOrEqualTo_CFixedPoint\( {re.escape(total)}, '\(CFixedPoint\)6' \)")
                self.assertIn(f"MakeScopeValue( '(CFixedPoint){op}' )", root)


class TooltipTest(unittest.TestCase):
    def test_the_tooltip_says_it_is_an_estimate_and_what_narrows_it(self):
        for m in MILESTONES:
            with self.subTest(milestone=m):
                tt = _loc(f"je_space_race_widget_rival_tt_{m}")
                self.assertIn("estimate", tt.lower())
                self.assertIn("intelligence network", tt)
                for part in ("lo", "hi", "est"):
                    self.assertIn(f"ScriptValue('sr_disp_rival_{part}_{m}')", tt)
                self.assertIn("ScriptValue('sr_disp_rival_band')", tt)
                self.assertIn("State.GetCountry.GetName", tt)
        how = _loc("je_space_race_widget_how_rivals")
        self.assertIn("estimate", how)
        self.assertIn("intelligence network", how)


if __name__ == "__main__":
    unittest.main()
