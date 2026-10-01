"""The exchange rate's confidence term is one-sided for a floating currency (design doc §0.12, "The currency").

`te_mon_fx_term_inflation` is the price gap against the world in exchange-rate
points, both ways. The target reads it through `te_mon_fx_term_confidence`,
which drops the below-the-world half when the index follows its own target (a
float that is not anchored): inflating costs a currency trust, deflating does not
buy it any, because what a deflating currency pays its holders is the carry term.
Metal and anchored currencies keep the whole gap, since for them the target is
only the shadow their overvaluation is judged on. The commodity-specie term keeps
reading the whole gap too.
"""
import re
import unittest
from pathlib import Path

from test_banking_external_tools import Script, definitions

ROOT = Path(__file__).resolve().parent
FX_VALUES = 'common/script_values/te_monetary_fx_script_values.txt'
VALUES = 'common/script_values/te_monetary_script_values.txt'


def confidence(inflation, *, floats=True, anchored=False, world=2.0):
    """Both terms on the real script, with the regime triggers and the inflation read stubbed."""
    s = Script(te_mon_fx_inflation_read=inflation, te_mon_fx_floats=floats, te_mon_is_anchored=anchored)
    s.vars['te_mon_world_inflation_now'] = world
    return s.number('te_mon_fx_term_inflation'), s.number('te_mon_fx_term_confidence')


class ConfidenceTerm(unittest.TestCase):
    def test_a_floating_currency_gains_nothing_from_deflating(self):
        for inflation in (-9.1, -2, 1.5):
            gap, conf = confidence(inflation)
            self.assertGreater(gap, 0, inflation)
            self.assertEqual(conf, 0, inflation)

    def test_inflating_still_costs_a_floating_currency_the_same(self):
        for inflation, want in ((3, -2), (6, -8), (30, -20)):
            gap, conf = confidence(inflation)
            self.assertEqual((gap, conf), (want, want), inflation)

    def test_metal_and_anchored_currencies_keep_the_whole_gap(self):
        for kw in (dict(floats=False), dict(anchored=True)):
            for inflation in (-9.1, 0, 6):
                gap, conf = confidence(inflation, **kw)
                self.assertEqual(conf, gap, (kw, inflation))
        self.assertEqual(confidence(-9.1, floats=False)[1], 20)  # the clamp: ten points at 2 a point

    def test_the_target_reads_the_confidence_term_and_the_specie_term_the_whole_gap(self):
        values = definitions(FX_VALUES)
        target = [val for key, _, val in values['te_mon_fx_target_value'] if key == 'add']
        self.assertIn('te_mon_fx_term_confidence', target)
        self.assertNotIn('te_mon_fx_term_inflation', target)
        # The specie discipline answers a price gap under a fixed parity both ways.
        specie = definitions(VALUES)['te_mon_commodity_specie_gap']
        self.assertIn(('value', '=', 'te_mon_fx_term_inflation'), specie)

    def test_the_gate_is_the_index_following_its_own_target(self):
        """The same two conditions step 5b uses to let the index follow the shadow."""
        body = repr(definitions(FX_VALUES)['te_mon_fx_term_confidence'])
        self.assertIn("('te_mon_fx_floats', '=', 'yes')", body)
        self.assertIn("('te_mon_is_anchored', '=', 'no')", body)
        effects = (ROOT / 'common/scripted_effects/te_monetary_fx_effects.txt').read_text(encoding='utf-8-sig')
        self.assertIn('limit = { te_mon_is_anchored = yes }', effects)
        self.assertRegex(effects, r"limit = \{ te_mon_fx_floats = yes \}\n\t+set_variable = \{ name = te_fx_index value = var:te_fx_shadow \}")

    def test_the_tooltip_prints_the_term_the_target_uses(self):
        loc = (ROOT / 'localization/english/te_miscellaneous_l_english.yml').read_text(encoding='utf-8-sig')
        tip = re.search(r'^ banking_dash_mon_fx_tt:0 "(.*)"$', loc, re.M).group(1)
        self.assertIn("ScriptValue('te_mon_fx_term_confidence')", tip)
        self.assertNotIn("ScriptValue('te_mon_fx_term_inflation')", tip)
        self.assertIn('not won by deflating', tip)


if __name__ == '__main__':
    unittest.main()
