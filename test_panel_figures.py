"""Figures and counts in the Strategic Reserve, Demographics, Seabed and Grand
Monuments panels (GUI wave, 2026-11-24).

`|K` on a CFixedPoint always abbreviates: the running game printed 0 as
"0.00K" and 80 as "0.08K" (the Reserve's rates, the Causes of Death table).
So a figure that can be small is printed through a switch,
`<fig>` = `[SelectLocalization( LessThan_CFixedPoint( Abs_CFixedPoint( x ),
'(CFixedPoint)1000' ), '<fig>_n', '<fig>_k' )]`: whole below 1,000,
abbreviated from it. `|K` truncates (255,600 printed "255K"), so the cut is
1,000 itself: a figure from 999.5 would otherwise print "0.99K". A figure
that can pass 9,999 is not printed raw ("+255600" in the Seabed's +1 license
column) but through the same switch, or delimited where the player sets it
(`|D0`). And a count reads "1 level", not "1 levels": the count's line has a
`_one` and a `_many` form (the `_many` the old text, so its translations keep
shipping), split off into `<key>_count` when the count sits in one line of a
longer tooltip. A line a script prints (THIS, SCOPE) picks the noun instead
(gm_word_level): a key named in SelectLocalization renders without THIS or
SCOPE, so its forms could not read them. Where the count sits mid-sentence
in a long line, the pick goes in a splice of its own (`$x_word$`), which
changes no number in the line, so its translations keep shipping too.
"""
import os
import re
import unittest

import gui_test_helpers as h

REPO = os.path.dirname(os.path.abspath(__file__))
PANELS = (
    "gui/journal_entry_widgets/strategic_reserve_widget.gui",
    "gui/te_demographics_widgets.gui",
    "gui/te_demographics_layout.gui",
    "gui/te_seabed_widgets.gui",
    "gui/gm_trophy_widgets.gui",
    "gui/gm_archaeology_widgets.gui",
    "gui/journal_entry_widgets/grand_monuments_widget.gui",
)
GM_PANELS = PANELS[4:]

FIG_K = re.compile(r"\[([^\[\]]*)\|([A-Za-z0-9%+=*\-]*K[A-Za-z0-9%+=*\-]*)\]")
SWITCH = re.compile(r"^\[SelectLocalization\( LessThan_CFixedPoint\( Abs_CFixedPoint\( (.+) \), "
                    r"'\(CFixedPoint\)1000' \), '(\w+)', '(\w+)' \)\]$")
NOUNS = {"level": "levels", "is": "are"}
# A noun picked in a splice of its own, for a line that reads SCOPE or THIS (a
# key named in SelectLocalization renders without either; a `$key$` splice
# renders in the line's context): `#v [count|0]#! $word$`, where word picks
# gm_word_level / gm_word_levels by that same count.
SPLICED_PICK = re.compile(r"\[([^\[\]]*)\|0\]#! \$(\w+_word)\$")
COUNTED = re.compile(r"\|[+=\-]*0\](?:#! | )(?:more |missing )?(levels|months|monuments|digs|sites|trophies|mines|"
                     r"licenses)\b")
NOUN_PICK = re.compile(r"\[([^\[\]]*)\|0\]#! (?:more |missing )?\[SelectLocalization\( EqualTo_CFixedPoint\( "
                       r"([^\[\]]*?), '\(CFixedPoint\)1' \), 'gm_word_(\w+)', 'gm_word_(\w+)' \)\]")
# Counts that are never 1: a dig takes 100 / (rate x size factor) months, at
# least 9 (a rate of at most 4, a size factor of at most 3), and Forensic adds
# gm_arch_forensic_bonus (2) levels.
NEVER_ONE = {"gm_arch_launch_antiquarian_tooltip", "gm_arch_launch_systematic_tooltip",
             "gm_arch_launch_forensic_tooltip"}


def _closure(path, loc):
    text = h._read(os.path.join(REPO, path))
    keys = h.gui_keys(text, loc) | h.scripted_keys(text, loc, markup=True)
    return text, h.loc_closure(keys, loc)


class FigureSwitchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = h.load_loc()
        cls.panels = {p: _closure(p, cls.loc) for p in PANELS}

    def test_no_abbreviated_figure_in_the_markup(self):
        for path, (text, _) in self.panels.items():
            self.assertEqual(FIG_K.findall(text), [], path)

    def test_every_abbreviated_figure_is_switched(self):
        """Each `|K` figure a panel prints is a `<fig>_k` branch of its switch."""
        for path, (_, keys) in self.panels.items():
            for key in sorted(keys):
                for m in FIG_K.finditer(self.loc[key]):
                    with self.subTest(panel=path, key=key):
                        expr, fmt = m.groups()
                        self.assertEqual(self.loc[key], m.group(0), "a switch branch prints the figure alone")
                        self.assertTrue(key.endswith("_k"), key)
                        fig = key[:-2]
                        sw = SWITCH.match(self.loc.get(fig, ""))
                        self.assertIsNotNone(sw, f"{fig} is not the switch")
                        self.assertEqual(sw.groups(), (expr, f"{fig}_n", f"{fig}_k"))
                        small = self.loc[f"{fig}_n"]
                        n = re.fullmatch(r"\[(.*)\|([A-Za-z0-9%+=*\-]+)\]", small)
                        self.assertIsNotNone(n, small)
                        self.assertEqual(n.group(1), expr)
                        self.assertNotIn("K", n.group(2))
                        # the sign flags stay the same on both sides
                        self.assertEqual(set(n.group(2)) & set("+=-"), set(fmt) & set("+=-"), small)

    def test_the_named_figures(self):
        """The figures the coordinator saw (2026-11-24), and their siblings."""
        loc = self.loc
        for g in ("grain", "ammunition", "oil", "small_arms", "artillery", "aeroplanes", "tanks", "fertilizer",
                  "copper"):
            self.assertRegex(loc[f"st_res_row_{g}_rate_short"], SWITCH)
            self.assertEqual(loc[f"st_res_row_{g}_flow"], f"$st_res_row_{g}_rate_short$/wk")
            for key in (f"st_res_row_{g}_amount", f"st_res_row_{g}_stock_tt"):
                self.assertIn(f"$st_res_row_{g}_stored_fig$ / $st_res_row_{g}_capacity_fig$", loc[key])
        for kind in ("spend", "income"):
            self.assertIn(f"$je_strategic_reserve_ov_{kind}_fig$", loc[f"je_strategic_reserve_ov_{kind}_value"])
        for pre in ("te_demog_cd", "te_demog_st"):
            for c in ("inf", "chr", "ext", "work", "mat", "kill", "war"):
                self.assertRegex(loc[f"{pre}_dc_{c}_fig"], SWITCH)
                self.assertIn(f"${pre}_dc_{c}_fig$", loc[f"{pre}_dc_{c}_deaths"])
        for b in ("pacific", "atlantic", "indian", "arctic", "southern"):
            self.assertEqual(loc[f"te_seabed_next_{b}"], f"+$te_seabed_need_navy_fig_{b}$")
            for form in ("one", "many"):
                self.assertIn(f"+$te_seabed_need_navy_fig_{b}$", loc[f"te_seabed_next_tt_{b}_{form}"])
            for key in (f"te_seabed_weight_far_{b}", f"te_seabed_weight_home_{b}"):
                self.assertIn("$te_seabed_npp_fig$", loc[key])
                self.assertNotIn("te_seabed_npp_counted_disp')|0]", loc[key])
        self.assertIn("$te_seabed_fee_fig$", loc["te_seabed_ov_licences_fig_fee"])
        self.assertNotIn("fee_k_disp", loc["te_seabed_ov_licences_fig_fee"])

    def test_the_state_panels_grid_tile(self):
        """Flow, the market flow and the pass-through on the state panel's Power Grid tile (2026-11-24 follow-up):
        three bindings of the tile, nothing else of it."""
        # The tile stands among the mod's tiles (te_state_tiles, gui/te_state_panel_widgets.gui).
        states = h._read(os.path.join(REPO, "gui/te_state_panel_widgets.gui"))
        for name, sv in (("moved", "te_grid_electricity_moved_disp"), ("market", "te_grid_market_flow_disp"),
                         ("pass", "te_grid_import_disp")):
            self.assertNotIn(f"ScriptValue('{sv}')|K]", states)
            self.assertEqual(states.count(f'text = "te_grid_tile_{name}_value"'), 1, name)
            self.assertEqual(self.loc[f"te_grid_tile_{name}_value"], f"#v $te_grid_tile_{name}_fig$#!")
            x = f"State.MakeScope.ScriptValue('{sv}')"
            sw = SWITCH.match(self.loc[f"te_grid_tile_{name}_fig"])
            self.assertEqual(sw.groups(), (x, f"te_grid_tile_{name}_fig_n", f"te_grid_tile_{name}_fig_k"))
            self.assertEqual(self.loc[f"te_grid_tile_{name}_fig_n"], f"[{x}|0]")
            self.assertEqual(self.loc[f"te_grid_tile_{name}_fig_k"], f"[{x}|K]")

    def test_the_settings_the_player_sets_stay_exact(self):
        """The adjustment step (to 10,000) and the weekly budget (past 100,000) are the player's: exact, with
        their thousands delimited."""
        sr = h._read(os.path.join(REPO, PANELS[0]))
        for v in ("max_flow", "budget"):
            self.assertEqual(len(re.findall(rf"Var\('st_res_\w+_{v}'\)\.GetValue\|D0\]", sr)), 9, v)
            self.assertNotRegex(sr, rf"Var\('st_res_\w+_{v}'\)\.GetValue\|0\]")
        self.assertIn("ScriptValue('st_res_adjust_step_value')|D0]", self.loc["je_strategic_reserve_inv_step"])


class SingularTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = h.load_loc()
        cls.keys = set()
        for p in PANELS:
            cls.keys |= _closure(p, cls.loc)[1]

    def test_the_noun_words(self):
        for one, many in NOUNS.items():
            self.assertEqual(self.loc[f"gm_word_{one}"], one)
            self.assertEqual(self.loc[f"gm_word_{many}"], many)

    def test_a_count_of_one_takes_the_singular(self):
        """No `N levels` (months, monuments, ...) a count of 1 would print, outside a line's `_many` form."""
        for key in sorted(self.keys):
            for m in COUNTED.finditer(self.loc[key]):
                with self.subTest(key=key, noun=m.group(1)):
                    if key in NEVER_ONE:
                        continue
                    self.assertRegex(key, r"_(many|n)$")
                    parent = key.rsplit("_", 1)[0]
                    self.assertIn(f"{parent}_one", self.loc)
                    # picked against its `_one` by a count: the line's own switch, or a nested one
                    # (te_demog_st_census_next picks te_demog_st_next_now / _one / _n)
                    pick = f"'{parent}_one', '{key}' )"
                    self.assertTrue(any(pick in v for v in self.loc.values()), pick)

    def test_each_noun_is_picked_by_its_own_count(self):
        seen = 0
        for key in sorted(k for k in self.loc if k.startswith("gm_")):
            for m in NOUN_PICK.finditer(self.loc[key]):
                seen += 1
                with self.subTest(key=key):
                    count, tested, one, many = m.groups()
                    self.assertEqual(count, tested)
                    self.assertEqual(NOUNS.get(one), many)
        self.assertGreaterEqual(seen, 4)

    def test_a_spliced_pick_reads_its_own_count(self):
        """The state panel's Grand Monument card and the commission's accept option (2026-11-24 follow-up)."""
        seen = 0
        for key in ("gm_state_grandeur_tt_one", "gm_state_grandeur_tt_many", "gm_com_accept_build_line"):
            text = self.loc[key]
            self.assertNotRegex(text, r"\|0\]#! levels\b", key)
            for m in SPLICED_PICK.finditer(text):
                seen += 1
                count, word = m.groups()
                with self.subTest(key=key, word=word):
                    pk = re.fullmatch(r"\[SelectLocalization\( EqualTo_CFixedPoint\( (.*), '\(CFixedPoint\)1' \), "
                                      r"'gm_word_(\w+)', 'gm_word_(\w+)' \)\]", self.loc[word])
                    self.assertIsNotNone(pk, self.loc[word])
                    self.assertEqual(pk.group(1), count)
                    self.assertEqual(NOUNS.get(pk.group(2)), pk.group(3))
        self.assertEqual(seen, 3)
        # "The 1 level ... is queued": the verb follows the same count
        line = self.loc["gm_com_accept_build_line"]
        self.assertIn("takes at today's rate $gm_com_accept_build_are_word$ queued", line)
        self.assertIn("'gm_word_is', 'gm_word_are'", self.loc["gm_com_accept_build_are_word"])
        self.assertIn("SCOPE.GetRootScope.ScriptValue('gm_disp_com_target_levels')",
                      self.loc["gm_com_accept_build_are_word"])
        for word in ("is", "are"):
            self.assertEqual(self.loc[f"gm_word_{word}"], word)

    def test_the_umbrella(self):
        """The Nuclear Weapons tab's Forces table, Under our umbrella (2026-11-24 follow-up)."""
        loc = self.loc
        self.assertIn("'(CFixedPoint)1' ), 'nd_w_umbrella_value_one', 'nd_w_umbrella_value_many'",
                      loc["nd_w_umbrella_value"])
        self.assertEqual(loc["nd_w_umbrella_value_one"], "#v 1#! subject")
        self.assertTrue(loc["nd_w_umbrella_value_many"].endswith("#! subjects"))

    def test_the_named_lines(self):
        """Item 4: "1 levels carried off" was the coordinator's; Finished, the summaries and Carry It Off with it."""
        loc = self.loc
        for key in ("gm_tr_row_value", "gm_row_frozen", "gm_site_row_detail", "gm_je_tr_summary",
                    "gm_je_abroad_summary"):
            self.assertIn(f"'{key}_one', '{key}_many'", loc[key])
            self.assertIn("#v 1#!", loc[f"{key}_one"])
        self.assertTrue(loc["gm_tr_row_value_one"].startswith("#v 1#! level carried off"))
        self.assertTrue(loc["gm_row_frozen_one"].startswith("Finished: #v 1#! level ·"))
        self.assertIn("trophy counts", loc["gm_je_tr_summary_one"])
        self.assertIn("stands abroad", loc["gm_je_abroad_summary_one"])
        for key in ("gm_tr_take_occupation_tt", "gm_tr_take_own_tt"):
            self.assertRegex(loc[key], NOUN_PICK)
        self.assertEqual(loc["gm_je_arch_summary"], "$gm_je_arch_summary_digs$, $gm_je_arch_summary_sites$")
        # the Seabed's counts and the Longevity Gap's points, which print a fraction whole
        for key in ("te_seabed_ov_room_word", "te_seabed_ov_longhaul_word", "te_seabed_next_tt_indian",
                    "te_seabed_ov_claims_lent_ours", "te_seabed_ov_claims_lent_theirs"):
            self.assertIn(f"'(CFixedPoint)1' ), '{key}_one', '{key}_many'", loc[key])
        for key in ("te_demog_ov_lx_gap_value", "te_demog_st_lx_gap_value"):
            self.assertIn("'(CFixedPoint)0.5' ), LessThan_CFixedPoint(", loc[key])
            self.assertTrue(loc[f"{key}_one"].endswith("#v 1#! point"))


if __name__ == "__main__":
    unittest.main()
