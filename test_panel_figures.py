"""Figures and counts in the Strategic Reserve, Demographics, Seabed and Grand
Monuments panels (GUI wave, 2026-11-24).

`|K` on a CFixedPoint always abbreviates: the running game printed 0 as
"0.00K" and 80 as "0.08K" (the Reserve's rates, the Causes of Death table).
So a figure that can be small is printed through a switch,
`<fig>` = `[SelectLocalization( LessThan_CFixedPoint( Abs_CFixedPoint( x ),
'(CFixedPoint)999.5' ), '<fig>_n', '<fig>_k' )]`: whole below 1,000,
abbreviated from it. A figure that can pass 9,999 is not printed raw
("+255600" in the Seabed's +1 license column) but through the same switch,
or delimited where the player sets it (`|D0`). And a count reads "1 level",
not "1 levels": its noun is picked by the count (gm_word_*), or the line has a
`_one` and a `_many` form.
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
                    r"'\(CFixedPoint\)999\.5' \), '(\w+)', '(\w+)' \)\]$")
NOUNS = {"level": "levels", "month": "months", "monument": "monuments", "dig": "digs", "site": "sites"}
COUNTED = re.compile(r"\|[+=\-]*0\]#! (?:more |missing )?(levels|months|monuments|digs|sites|trophies)\b")
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
            self.assertIn(f"+$te_seabed_need_navy_fig_{b}$", loc[f"te_seabed_next_tt_{b}"])
            for key in (f"te_seabed_weight_far_{b}", f"te_seabed_weight_home_{b}"):
                self.assertIn("$te_seabed_npp_fig$", loc[key])
                self.assertNotIn("te_seabed_npp_counted_disp')|0]", loc[key])
        self.assertIn("$te_seabed_fee_fig$", loc["te_seabed_ov_licences_fig_fee"])
        self.assertNotIn("fee_k_disp", loc["te_seabed_ov_licences_fig_fee"])

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
        for p in GM_PANELS:
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
                    self.assertRegex(self.loc[parent], r"EqualTo_CFixedPoint\(.*'\(CFixedPoint\)1' \), "
                                                       rf"'{parent}_one', '{key}'")

    def test_each_noun_is_picked_by_its_own_count(self):
        seen = 0
        for key in sorted(self.keys):
            for m in NOUN_PICK.finditer(self.loc[key]):
                seen += 1
                with self.subTest(key=key):
                    count, tested, one, many = m.groups()
                    self.assertEqual(count, tested)
                    self.assertEqual(NOUNS.get(one), many)
        self.assertGreaterEqual(seen, 40)

    def test_the_trophy_row(self):
        """Item 4: "1 levels carried off" was the coordinator's."""
        self.assertRegex(self.loc["gm_tr_row_value"], NOUN_PICK)
        for key in ("gm_je_tr_summary", "gm_je_abroad_summary"):
            self.assertIn(f"'{key}_one', '{key}_many'", self.loc[key])
        self.assertIn("trophy counts", self.loc["gm_je_tr_summary_one"])
        self.assertIn("stands abroad", self.loc["gm_je_abroad_summary_one"])


if __name__ == "__main__":
    unittest.main()
