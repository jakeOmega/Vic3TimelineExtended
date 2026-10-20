"""The life tables' open last interval and life expectancy's display cap (owner, 2026-10-20).

The life tables sum person-years over the age groups, which end at 145-149; the survivors at 150 now live on at the death
rate past 150 (demographics_model.tail_years, te_demog_lt_tail), in e0 and e65 alone. The panel shows e0 and e65 as they
are up to 10,000 years and "over 10,000" past that; the stored figures stay exact. The Life Expectancy chart's axis runs to
the largest figure its samples hold, 100 to 10,000, and a bar stops at 10,000. demographics-playtest.md has the in-game
checks."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_model as M  # noqa: E402
import demographics_params as P  # noqa: E402
from test_demographics_registry import (  # noqa: E402
    EFFECTS, GENERATED_EFFECTS, GENERATED_VALUES, HISTORY_EFFECTS, LX_EFFECTS, LX_GEN_EFFECTS, _block, _Engine,
    _parse_script, _text)

GUI = ROOT / "gui" / "te_demographics_widgets.gui"
LOC = ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml"
# the figures the panel shows: the state's and the country's (the same names), and a history sample's
SHOWN = ("te_dg_e0", "te_dg_e0f", "te_dg_e0m", "te_dg_e65", "te_dg_prev_e0")
OVER = f"'(CFixedPoint){P.E0_SHOWN_MAX}'"


def _loc():
    return dict(re.findall(r'(?m)^ ([\w.]+):0 "(.*)"$', _text(LOC)))


class TestTailScript(unittest.TestCase):
    """te_demog_lt_finish against demographics_model.life_table's tail, in the engine's fixed point."""

    def finish(self, lf, lm, qf, qm, pyf=4.0e6, pym=3.5e6, l65f=60000.0, l65m=50000.0, py65f=3.0e6, py65m=2.8e6):
        eng = _Engine({}, truncate=True)
        eng.locals.update(te_dg_lf=lf, te_dg_lm=lm, te_dg_pyf=pyf, te_dg_pym=pym, te_dg_l65f=l65f, te_dg_l65m=l65m,
                          te_dg_py65f=py65f, te_dg_py65m=py65m, te_dg_qf=qf, te_dg_qm=qm)
        eng.run(_parse_script("te_demog_lt_finish = { QF = local_var:te_dg_qf QM = local_var:te_dg_qm }"))
        want_f = (pyf + lf * M.tail_years(qf)) / 100000
        want_m = (pym + lm * M.tail_years(qm)) / 100000
        e65 = ((pyf + lf * M.tail_years(qf) - py65f) / l65f + (pym + lm * M.tail_years(qm) - py65m) / l65m) / 2
        return eng, want_f, want_m, e65

    def check(self, eng, want_f, want_m, e65):
        for name, want in (("te_dg_e0f", want_f), ("te_dg_e0m", want_m), ("te_dg_e0", (want_f + want_m) / 2),
                           ("te_dg_e65", e65)):
            self.assertLessEqual(abs(eng.vars[name] - want), 1e-4 + 1e-7 * want, f"{name}: {eng.vars[name]} vs {want}")
        # the table to 150 stays in te_dg_py<f|m> for the old-age pass after
        self.assertEqual((eng.locals["te_dg_pyf"], eng.locals["te_dg_pym"]), (4.0e6, 3.5e6))

    def test_a_table_before_the_late_game_barely_moves(self):
        # a few in ten million at 150, dying at the last group's rate: under a thousandth of a year
        eng, f, m, e65 = self.finish(0.05, 0.0003, 22720.7, 29521.2)
        self.check(eng, f, m, e65)
        self.assertLess(eng.vars["te_dg_e0f"] - 40.0, 1e-3)

    def test_immortal_survivors_live_for_thousands_of_years(self):
        # most of the cohort at 150, its bodies dying at a young adult's rate
        eng, f, m, e65 = self.finish(90000.0, 85000.0, 40.0, 55.0)
        self.check(eng, f, m, e65)
        self.assertGreater(eng.vars["te_dg_e0"], 1000)

    def test_no_deaths_take_the_floor_rate(self):
        # q -> 0: the rate floors at te_demog_k_lt_tail_rate_min (one per 100,000), so the tail is finite and the
        # product (survivors x 100,000) stays inside the fixed point
        eng, f, m, e65 = self.finish(100000.0, 100000.0, 0.0, 0.0)
        self.check(eng, f, m, e65)
        self.assertAlmostEqual(eng.vars["te_dg_e0"], (4.0e6 + 3.5e6) / 200000 + 99999.5, places=3)
        self.assertLess(eng.vars["te_dg_e0"] * 100000, (2 ** 63 - 1) / 1e5)

    def test_the_floor_is_the_params(self):
        self.assertIn(f"te_demog_k_lt_tail_rate_min = {{ value = {P.LT_TAIL_RATE_MIN:g} }}", _text(GENERATED_VALUES))
        self.assertIn(f"te_demog_k_e0_shown_max = {{ value = {P.E0_SHOWN_MAX} }}", _text(GENERATED_VALUES))
        self.assertIn(f"te_demog_k_e0_axis_min = {{ value = {P.E0_AXIS_MIN} }}", _text(GENERATED_VALUES))


class TestTailWiring(unittest.TestCase):
    """Which rate each table's survivors at 150 live on at."""

    def test_the_plain_table_passes_its_last_groups_rates(self):
        body = _block(_text(GENERATED_EFFECTS), "te_demog_life_table")
        self.assertIn("te_demog_lt_finish = { QF = local_var:te_dg_qf QM = local_var:te_dg_qm }", body)
        # after the last group, and before the old-age pass, which reads the table to 150
        self.assertLess(body.rindex("te_demog_lt_group"), body.index("te_demog_lt_finish"))
        self.assertLess(body.index("te_demog_lt_finish"), body.index("te_demog_old_age_pass"))

    def test_the_old_age_threshold_keeps_the_table_to_150(self):
        for path, name in ((GENERATED_EFFECTS, "te_demog_old_age_pass"), (LX_GEN_EFFECTS, "te_demog_lx_old_age_pass")):
            body = _block(_text(path), name)
            self.assertIn("local_var:te_dg_py", body, name)
            self.assertNotIn("te_dg_pyt", body, name)

    def test_the_blend_takes_the_pools_rate(self):
        body = _block(_text(LX_GEN_EFFECTS), "te_demog_lx_tables")
        self.assertIn("te_demog_lt_finish = { QF = local_var:te_dg_lt_tqf QM = local_var:te_dg_lt_tqm }", body)
        last = len(P.GROUPS) - 1
        for s in "fm":
            self.assertIn(f"value = local_var:te_dg_lxp_u{s} multiply = local_var:te_dg_lxu_q{s}{last} add = {{ value = "
                          f"local_var:te_dg_lxp_t{s} multiply = local_var:te_dg_lxp_bq{s} }}", body)
        stores = _block(_text(LX_EFFECTS), "te_demog_lx_fold_deaths")
        for s, part in (("f", "f"), ("m", "m")):
            self.assertIn(f"set_local_variable = {{ name = te_dg_lxp_u{s} value = local_var:te_dg_lx_{part}u }}", stores)
            self.assertIn(f"set_local_variable = {{ name = te_dg_lxp_t{s} value = local_var:te_dg_lx_{part}t }}", stores)
            self.assertIn(f"set_local_variable = {{ name = te_dg_lxp_bq{s} value = local_var:te_dg_lx_uq{s} }}", stores)
        # before the pool's deaths change its people
        self.assertLess(stores.index("te_dg_lxp_uf"), stores.index("name = te_dg_deaths"))

    def test_the_model_takes_the_same_rates(self):
        lx = {"pool": {"f": (3.0, 1.0, 20000.0, 40.0), "m": (0.0, 0.0, 25000.0, 50.0)}}
        self.assertEqual(M.lx_tail_rate(lx, "untreated", "f"), 20000.0)
        self.assertEqual(M.lx_tail_rate(lx, "treated", "f"), 40.0)
        self.assertAlmostEqual(M.lx_tail_rate(lx, "blend", "f"), (3 * 20000.0 + 40.0) / 4)
        self.assertIsNone(M.lx_tail_rate(lx, "blend", "m"))      # no pool: the table's last group's
        self.assertIsNone(M.lx_tail_rate(lx, "treated", "m"))
        self.assertIsNone(M.lx_tail_rate({}, "blend", "f"))

    def test_lt_finish_is_the_one_place_e0_is_written(self):
        """te_dg_e0's writers: the tables' finish, and the country's people-weighted average of its states'."""
        for path in (EFFECTS, GENERATED_EFFECTS, LX_EFFECTS, LX_GEN_EFFECTS):
            text = _text(path)
            for m in re.finditer(r"set_variable = \{ name = te_dg_e0f? ", text):
                start = text.rindex("\n", 0, m.start())
                owner = re.findall(r"(?m)^(\w+) = \{", text[:start])[-1]
                self.assertIn(owner, ("te_demog_lt_finish", "te_demog_country_census"), (path.name, owner))


class TestE0DisplayCap(unittest.TestCase):
    """Every number the panel shows for life expectancy goes through a switch at E0_SHOWN_MAX: the figure up to it, the
    "over" text past it (owner, 2026-10-20). debug_log lines and the stored figures stay exact."""

    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()
        cls.gui = _text(GUI)

    def number_keys(self):
        """{loc key: the read it formats}: every key whose text formats one of the shown figures."""
        out = {}
        for key, text in self.loc.items():
            for m in re.finditer(r"(\w+(?:\.\w+)*\.Var\('(te_dg_\w+)'\)\.GetValue|ScriptContainer\.GetVariableValue\("
                                 r"'(te_dg_h_e0)'\))\|", text):
                if (m.group(2) or m.group(3)) in SHOWN + ("te_dg_h_e0",):
                    out[key] = m.group(1)
        return out

    def guarded(self, key, read, corpus, depth=0):
        """Every use of `key` sits behind the cap's switch on `read`, or inside a key every use of which does."""
        self.assertLess(depth, 4, key)
        uses = [(k, t) for k, t in corpus.items() if f"'{key}'" in t]
        self.assertTrue(uses, f"{key} is never used")
        for k, t in uses:
            for m in re.finditer(re.escape(f"'{key}'"), t):
                head = t[:m.start()]
                switch = head[head.rindex("SelectLocalization("):]
                if f"GreaterThan_CFixedPoint( {read}, {OVER} )" not in switch:
                    self.assertNotEqual(k, "<gui>", f"{key} in the GUI with no cap")
                    self.guarded(k, read, corpus, depth + 1)

    def test_every_shown_figure_is_switched(self):
        keys = self.number_keys()
        self.assertTrue(keys)
        corpus = {**self.loc, "<gui>": self.gui}
        for key, read in keys.items():
            # every use of a key that prints the figure is behind the switch on that read
            self.guarded(key, read, corpus)
        # no figure formatted straight in the GUI
        for name in SHOWN:
            self.assertNotRegex(self.gui, rf"Var\('{name}'\)\.GetValue\|", name)
        self.assertNotIn("GetVariableValue('te_dg_h_e0')|", self.gui)

    def test_the_over_texts_say_the_cap(self):
        for key in ("te_demog_e0_over", "te_demog_ov_e0_over", "te_demog_hist_e0_over"):
            self.assertIn(f"over {P.E0_SHOWN_MAX:,}", self.loc[key], key)
        self.assertEqual(self.loc["te_demog_states_e0_over"], f"{P.E0_SHOWN_MAX // 1000}K+")   # the list's 56 pixels
        self.assertNotIn("te_demog_ov_e0_100", self.loc)
        self.assertNotIn("stops at 150", self.loc["te_demog_lx_e0_100_note"])

    def test_the_readings_switch_on_the_figure(self):
        for scope, value in (("GetPlayer.MakeScope", "te_demog_ov_e0_value"), ("State.MakeScope", "te_demog_st_e0_value")):
            self.assertIn(f"[SelectLocalization( GreaterThan_CFixedPoint( {scope}.Var('te_dg_e0').GetValue, {OVER} ), "
                          f"'te_demog_ov_e0_over', '{value}' )]", self.gui, scope)

    def test_debug_lines_stay_exact(self):
        text = _text(ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt")
        self.assertIn("e0=[THIS.Var('te_dg_e0').GetValue|2]", text)


class TestE0ChartAxis(unittest.TestCase):
    """The Life Expectancy chart: its axis te_dg_h_e0_max (100 to 10,000, the largest sample), a bar stopping at 10,000."""

    def test_the_bars_read_the_axis_and_stop_at_the_cap(self):
        gui = _text(GUI)
        start = gui.index('text = "te_demog_hist_e0_title"')
        chart = gui[start:gui.index('blockoverride "plot_size"', start)]
        axis = "Max_CFixedPoint( '(CFixedPoint)100', GetPlayer.MakeScope.Var('te_dg_h_e0_max').GetValue )"
        self.assertEqual(chart.count(f'max = "[FixedPointToFloat( {axis} )]"'), 2)
        self.assertEqual(chart.count(f"Min_CFixedPoint( ScriptContainer.GetVariableValue('te_dg_h_e0'), {OVER} )"), 2)
        self.assertNotIn("max = 100", chart)

    def test_the_store_sets_the_axis_after_the_samples(self):
        text = _text(HISTORY_EFFECTS)
        record = _block(text, "te_demog_history_record")
        self.assertGreater(record.index("te_demog_history_e0_axis = yes"), record.index("te_demog_history_markers = yes"))
        axis = _block(text, "te_demog_history_e0_axis")
        self.assertIn("set_local_variable = { name = te_dg_h_ax value = te_demog_k_e0_axis_min }", axis)
        self.assertIn("variable = te_dg_hist", axis)
        self.assertIn("max = te_demog_k_e0_shown_max", axis)


if __name__ == "__main__":
    unittest.main()
