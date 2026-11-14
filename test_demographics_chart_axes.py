"""The Demographics history charts' axes span the values they show (owner, 2026-11-14).

Five of the eight charts draw figures with no fixed top: Births and Deaths, Net Migration, Life Expectancy, Children
per Woman and Median Age. Each one's axis is the largest figure its samples hold, rounded up to a round number and
never under the axis the chart had while it was fixed (te_demog_history_axes, at each census). The bars and the axis
label read one script value, te_demog_hist_<axis>_axis_shown, which falls back to the floor on a save whose census
hasn't set the variable. Life expectancy's axis is the older one (test_demographics_life_tail.py holds its 10,000 cap).
The other three charts (the causes' shares, the Gini, Wealth Concentration) have fixed tops and keep their axes."""

import re
import unittest
from pathlib import Path

from gui_test_helpers import _type_body, history_charts
from test_demographics_registry import (
    DISPLAY_VALUES, HISTORY_EFFECTS, _block, _Engine, _raw_blocks, _text)

ROOT = Path(__file__).resolve().parent
GUI = ROOT / "gui" / "te_demographics_widgets.gui"
GENERATED = ROOT / "gui" / "te_history_charts_generated.gui"
CIVIL_WAR = ROOT / "common" / "scripted_effects" / "te_history_civil_war_effects.txt"

# axis -> (the chart's id in gen_te_history_charts.CHARTS, the samples' variables it spans, its floor: the axis the
# chart had while it was fixed)
AXES = {
    "bd": ("demog_births_deaths", ("te_dg_h_cbr", "te_dg_h_cdr"), 60),
    "mig": ("demog_migration", ("te_dg_h_mig",), 20),
    "e0": ("demog_e0", ("te_dg_h_e0",), 100),
    "tfr": ("demog_tfr", ("te_dg_h_tfr",), 8),
    "median": ("demog_median", ("te_dg_h_median",), 60),
}
# the charts whose figures cannot pass their axis: shares of a whole, an index from 0 to 1, a percentage
FIXED = {"demog_causes": "1", "demog_gini": "1", "demog_wc": "100"}


def _shown(axis):
    return f"Country.MakeScope.ScriptValue('te_demog_hist_{axis}_axis_shown')"


class _AxesEngine(_Engine):
    """_Engine with the country's history list: every_in_list runs its body in each sample's variables."""

    def __init__(self, samples, **kw):
        super().__init__({}, effects=_raw_blocks([HISTORY_EFFECTS]), **kw)
        self.samples = samples

    def run(self, items):
        batch = []
        for item in items:
            if item[0] != "every_in_list":
                batch.append(item)
                continue
            super().run(batch)
            batch = []
            body = [i for i in item[2] if i[0] != "variable"]
            assert ("variable", "=", "te_dg_hist") in item[2], item[2]
            country = self.vars
            for sample in self.samples:
                self.vars = sample
                try:
                    self.run(body)
                finally:
                    self.vars = country
        super().run(batch)


def _axes(samples, truncate=True):
    eng = _AxesEngine(samples, truncate=truncate)
    eng.call("te_demog_history_axes")
    return {axis: eng.vars[f"te_dg_h_{axis}_max"] for axis in AXES}


class TestAxesScript(unittest.TestCase):
    """te_demog_history_axes, run over a list of samples in the engine's fixed point."""

    def test_no_sample_passes_a_floor(self):
        # 1836's figures, and a country with no figures at all: every axis is the one the chart had
        early = [{"te_dg_h_cbr": 38.2, "te_dg_h_cdr": 31.0, "te_dg_h_mig": -1.4, "te_dg_h_e0": 36.9,
                  "te_dg_h_tfr": 5.31, "te_dg_h_median": 21.7}]
        for samples in (early, [{}], []):
            self.assertEqual(_axes(samples), {axis: float(floor) for axis, (_, _, floor) in AXES.items()})

    def test_an_axis_reaches_its_largest_sample(self):
        # the owner's case: life expectancy of 120 takes the axis to 120 at least
        samples = [{"te_dg_h_e0": 78.0, "te_dg_h_median": 41.0}, {"te_dg_h_e0": 120.0, "te_dg_h_median": 61.3},
                   {"te_dg_h_e0": 123.4, "te_dg_h_median": 58.0}]
        got = _axes(samples)
        self.assertEqual(got["e0"], 130.0)
        self.assertEqual(got["median"], 70.0)
        self.assertEqual((got["bd"], got["mig"], got["tfr"]), (60.0, 20.0, 8.0))   # no figure of theirs: the floors

    def test_every_sample_fits_and_the_axis_is_close(self):
        """Whatever the largest figure, the axis holds it, is a round number, and stands at most a quarter over it."""
        for top in (8.01, 9.0, 19.99, 20.0, 20.01, 33.3, 50.0, 50.01, 60.0, 61.0, 100.0, 100.01, 149.9, 200.0,
                    200.01, 499.0, 500.01, 1708.9, 2000.0, 2000.01, 4999.0, 5000.01, 9000.01, 123456.7):
            got = _axes([{"te_dg_h_tfr": top}, {"te_dg_h_tfr": 1.2}])["tfr"]
            self.assertGreaterEqual(got, top, top)
            self.assertLessEqual(got, top * 1.25, top)
            self.assertEqual(got, float(int(got)), top)
            step = next(s for limit, s in ((20, 1), (50, 5), (200, 10), (500, 50), (2000, 100), (5000, 500),
                                           (float("inf"), 1000)) if top <= limit)
            self.assertEqual(got % step, 0, top)

    def test_births_and_deaths_share_the_larger(self):
        # a war year's deaths lift the axis the births are drawn on too
        self.assertEqual(_axes([{"te_dg_h_cbr": 30.0, "te_dg_h_cdr": 20.0}, {"te_dg_h_cbr": 12.0, "te_dg_h_cdr": 84.5}])["bd"], 90.0)
        self.assertEqual(_axes([{"te_dg_h_cbr": 71.0, "te_dg_h_cdr": 20.0}])["bd"], 80.0)

    def test_net_migration_is_sized_either_way(self):
        self.assertEqual(_axes([{"te_dg_h_mig": 4.0}, {"te_dg_h_mig": -33.3}])["mig"], 35.0)
        self.assertEqual(_axes([{"te_dg_h_mig": 41.0}, {"te_dg_h_mig": -33.3}])["mig"], 45.0)

    def test_life_expectancy_stops_where_its_bars_do(self):
        self.assertEqual(_axes([{"te_dg_h_e0": 99000.0}])["e0"], 10000.0)
        self.assertEqual(_axes([{"te_dg_h_e0": 9000.01}])["e0"], 10000.0)
        self.assertEqual(_axes([{"te_dg_h_e0": 1708.9}])["e0"], 1800.0)

    def test_an_axis_falls_when_its_year_leaves_the_store(self):
        spike = [{"te_dg_h_cdr": 310.0}] + [{"te_dg_h_cdr": 14.0}] * 5
        self.assertEqual(_axes(spike)["bd"], 350.0)
        self.assertEqual(_axes(spike[1:])["bd"], 60.0)

    def test_a_sample_without_the_figure_is_skipped(self):
        # a seed's sample holds no rates: read as absent, never as a zero (and never as a missing variable)
        self.assertEqual(_axes([{"te_dg_h_e0": 40.0}, {"te_dg_h_e0": 41.0, "te_dg_h_cbr": 66.0, "te_dg_h_cdr": 30.0}])["bd"], 70.0)


class TestAxesWiring(unittest.TestCase):
    def setUp(self):
        self.effects = _text(HISTORY_EFFECTS)

    def test_the_census_and_a_revolutions_winner_set_them(self):
        record = _block(self.effects, "te_demog_history_record")
        self.assertGreater(record.index("te_demog_history_axes = yes"), record.index("te_demog_history_markers = yes"))
        # the winner takes the loser's older samples, so its axes are read again over the joined list
        self.assertRegex(_text(CIVIL_WAR), r"limit = \{ has_variable_list = te_dg_hist \}\s+te_demog_history_axes = yes")
        for text in (self.effects, _text(CIVIL_WAR)):
            self.assertNotIn("te_demog_history_e0_axis", text)

    def test_every_axis_is_taken_and_set(self):
        axes = _block(self.effects, "te_demog_history_axes")
        for axis, (_, variables, _) in AXES.items():
            for var in variables:
                self.assertEqual(axes.count(f"te_demog_history_axis_take = {{ AXIS = {axis} VAR = {var} }}"), 1, var)
            self.assertEqual(axes.count(f"te_demog_history_axis_set = {{ AXIS = {axis} }}"), 1, axis)
        self.assertEqual(axes.count("te_demog_history_axis_take"), sum(len(v) for _, v, _ in AXES.values()))

    def test_the_shown_value_falls_back_to_the_floor(self):
        eng = _Engine({})
        for axis, (_, _, floor) in AXES.items():
            value = eng._tree(eng.values, f"te_demog_hist_{axis}_axis_shown")
            eng.vars.pop(f"te_dg_h_{axis}_max", None)
            self.assertEqual(eng.value(value), floor, axis)      # a save from before: no variable until its census
            eng.vars[f"te_dg_h_{axis}_max"] = 250.0
            self.assertEqual(eng.value(value), 250.0, axis)

    def test_the_floors_are_the_fixed_axes(self):
        values = _text(DISPLAY_VALUES)
        for axis, (_, _, floor) in AXES.items():
            if axis != "e0":                                     # life expectancy's is generated (te_demog_k_e0_axis_min)
                self.assertIn(f"te_demog_hist_{axis}_axis_min = {{ value = {floor} }}", values)


class TestChartsReadTheAxis(unittest.TestCase):
    """Each chart at both sizes: its bars' range and its label read the axis, and no number of the old axis is left."""

    def charts(self, chart):
        """The chart's two wrappers: the panel's and the full-screen viewer's."""
        text = _text(GENERATED)
        return [_type_body(text, f"te_hist_{chart}"), _type_body(text, f"te_hist_{chart}_large")]

    def test_the_panel_draws_the_generated_charts(self):
        self.assertEqual(len(history_charts(_text(GUI))), 8)

    def test_bars_and_label(self):
        for axis, (chart_id, variables, floor) in AXES.items():
            shown = _shown(axis)
            for chart in self.charts(chart_id):
                # every progressbar's top is the axis: no literal max but a lower half's 0
                self.assertEqual(set(re.findall(r"\bmax = (\S+)", chart)) - {"0"}, {'"[FixedPointToFloat('}, axis)
                self.assertGreaterEqual(chart.count(f'max = "[FixedPointToFloat( {shown} )]"'), 2, axis)
                self.assertIn(f"[{shown}|0]\"", chart, axis)
                for label in re.findall(r'raw_text = "([^"]*)"', chart):
                    self.assertTrue(label == "0" or shown in label, f"{axis}: a fixed label {label!r}")
                # the bars' floor and cap are parts of the axis, so they keep their thickness as it grows: a bar's
                # value holds no number in the axis's units but 0 and life expectancy's 10,000
                values = re.findall(r'\bvalue = "([^"]*)"', chart)
                self.assertGreaterEqual(len(values), 2, axis)
                for value in values:
                    for literal in re.findall(r"'\(CFixedPoint\)([\d.]+)'", value):
                        if literal not in ("0", "10000"):
                            self.assertIn(f"Multiply_CFixedPoint( {shown}, '(CFixedPoint){literal}' )", value, axis)
                            self.assertLess(float(literal), 0.1, axis)
                # the variable is never read in the GUI: an old save holds none until its next census
                self.assertNotIn(f"te_dg_h_{axis}_max", chart)
                for var in variables:
                    self.assertIn(f"GetVariableValue('{var}')", chart)

    def test_net_migration_reaches_as_far_down_as_up(self):
        shown = _shown("mig")
        for chart in self.charts(AXES["mig"][0]):
            self.assertEqual(chart.count(f'min = "[Negate_float( FixedPointToFloat( {shown} ) )]"\n'), 2)
            self.assertEqual(chart.count(f'max = "[FixedPointToFloat( {shown} )]"\n'), 2)
            self.assertIn(f'raw_text = "+[{shown}|0]"', chart)
            self.assertIn(f'raw_text = "-[{shown}|0]"', chart)

    def test_the_bounded_charts_keep_their_axes(self):
        for chart_id, top in FIXED.items():
            for chart in self.charts(chart_id):
                self.assertEqual(set(re.findall(r"\bmax = (\S+)", chart)), {top}, chart_id)
                self.assertNotIn("_axis_shown", chart)


if __name__ == "__main__":
    unittest.main()
