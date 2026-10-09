# -*- coding: utf-8 -*-
"""Strategic Reserve: the Stockpile policy, the all-goods buttons and the AI review.

A playtest found that ammunition is worth buying at about base price, because a
war makes it dear, but no policy ever bought there: the purchase threshold could
not rise above base price and the ramp throttled purchases near it. Stockpile
(policy 4) buys at or below its threshold at full flow and sells only at war or
far above base. Nothing in the engine checks any of this; these tests pin it.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
# The goods the AI stockpiles and Military: Stockpile covers: a design choice, not derived.
MILITARY = ["ammunition", "oil", "small_arms", "artillery", "aeroplanes", "tanks"]


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


GOODS = re.findall(r"(?m)^st_res_(\w+)_unlocked_trigger = \{", _read("common", "scripted_triggers", "st_res_triggers.txt"))


def _block(text, name):
    m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _value(text, name):
    return float(re.search(rf"(?m)^{name} = \{{ value = (-?[\d.]+) \}}", text).group(1))


EFFECTS = _read("common", "scripted_effects", "st_res_effects.txt")
VALUES = _read("common", "script_values", "st_res_script_values.txt")
CUSTOM = _read("common", "customizable_localization", "st_res_custom_loc.txt")
EVALUATE = _block(EFFECTS, "st_res_policy_evaluate_good_effect")


class StockpileEvaluationTests(unittest.TestCase):
    def test_buys_at_or_below_the_threshold(self):
        self.assertRegex(EVALUATE, r"var:st_res_\$GOOD\$_policy = 4\s*local_var:st_res_policy_price <= local_var:st_res_policy_buy_at")

    def test_the_ramp_does_not_throttle_purchases(self):
        self.assertRegex(EVALUATE, r"limit = \{ var:st_res_\$GOOD\$_policy = 4 \}\s*set_local_variable = \{ name = st_res_policy_buy_frac value = 1 \}")

    def test_purchases_keep_the_hysteresis_band_whatever_the_ramp(self):
        self.assertRegex(EVALUATE, r"var:st_res_\$GOOD\$_engaged = 1\s*OR = \{\s*var:st_res_\$GOOD\$_ramp <= 0\s*var:st_res_\$GOOD\$_policy = 4\s*\}")

    def test_sells_at_war_or_far_above_base(self):
        self.assertRegex(EVALUATE, r"var:st_res_\$GOOD\$_policy = 4\s*is_at_war = no\s*local_var:st_res_policy_sell_at < st_res_policy_stockpile_peace_release\s*\}\s*"
                                   r"set_local_variable = \{ name = st_res_policy_sell_at value = st_res_policy_stockpile_peace_release \}")
        self.assertRegex(EVALUATE, r"OR = \{\s*var:st_res_\$GOOD\$_policy = 2\s*var:st_res_\$GOOD\$_policy = 3\s*var:st_res_\$GOOD\$_policy = 4\s*\}\s*"
                                   r"local_var:st_res_policy_price > local_var:st_res_policy_sell_at")

    def test_holding_is_said_and_read(self):
        self.assertIn("set_local_variable = { name = st_res_policy_next_status value = 10 }", EVALUATE)
        for g in GOODS:
            reason = _block(CUSTOM, f"st_res_{g}_policy_reason_text")
            self.assertIn(f"var:st_res_{g}_policy_status = 10", reason, g)
            name = _block(CUSTOM, f"st_res_{g}_policy_text")
            self.assertRegex(name, rf"var:st_res_{g}_policy = 4\s*\}}\s*localization_key = st_res_policy_stockpile", g)


class PresetTests(unittest.TestCase):
    PRESETS = {"conservative": 1, "standard": 2, "aggressive": 3, "stockpile": 4}

    def _setting(self, body, name):
        return float(re.search(rf"name = st_res_\$GOOD\$_{name} value = (-?\d+)", body).group(1))

    def test_every_preset_is_a_legal_setting(self):
        gap = _value(VALUES, "st_res_policy_buy_band") + _value(VALUES, "st_res_policy_sell_band")
        for preset, code in self.PRESETS.items():
            body = _block(EFFECTS, f"st_res_apply_preset_{preset}_base")
            self.assertEqual(self._setting(body, "preset"), code, preset)
            buy, sell = self._setting(body, "buy_thr"), self._setting(body, "sell_thr")
            self.assertGreaterEqual(sell - buy, gap, preset)
            self.assertGreaterEqual(buy, _value(VALUES, "st_res_policy_thr_floor"), preset)
            self.assertLessEqual(buy, _value(VALUES, "st_res_policy_buy_thr_ceiling"), preset)
            self.assertLessEqual(sell, _value(VALUES, "st_res_policy_thr_ceiling"), preset)
            self.assertIn(f"PRESET = {code}", body, preset)
            self.assertIn(f"st_res_preset_{preset}_flow_pct", body, preset)

    def test_the_stockpile_preset_buys_above_base(self):
        body = _block(EFFECTS, "st_res_apply_preset_stockpile_base")
        self.assertGreater(self._setting(body, "buy_thr"), 0)

    def test_the_weekly_refresh_follows_every_preset(self):
        refresh = _block(EFFECTS, "st_res_refresh_preset_magnitudes_effect")
        for preset in self.PRESETS:
            self.assertIn(f"st_res_preset_{preset}_flow_pct", refresh, preset)
            self.assertIn(f"st_res_preset_{preset}_budget_pct", refresh, preset)

    def test_choosing_stockpile_loads_its_preset(self):
        sguis = _read("common", "scripted_guis", "st_res_scripted_gui.txt")
        for g in GOODS:
            body = _block(sguis, f"st_res_policy_{g}_sgui")
            self.assertRegex(body, rf"limit = \{{ scope:op = 4 \}}\s*st_res_set_good_policy_base = \{{ GOOD = {g} POLICY = 4 PRESET = stockpile \}}", g)


class AllGoodsTests(unittest.TestCase):
    def _goods(self, effect, base):
        return re.findall(rf"{base} = \{{ GOOD = (\w+)", _block(EFFECTS, effect))

    def test_each_button_covers_its_goods(self):
        self.assertEqual(self._goods("st_res_all_goods_stabilize_effect", "st_res_bulk_policy_good_base"), GOODS)
        self.assertEqual(self._goods("st_res_military_goods_stockpile_effect", "st_res_bulk_policy_good_base"), MILITARY)
        self.assertEqual(self._goods("st_res_all_goods_manual_effect", "st_res_bulk_manual_good_base"), GOODS)

    def test_they_touch_unlocked_goods_and_refresh_once(self):
        for base in ("st_res_bulk_policy_good_base", "st_res_bulk_manual_good_base"):
            self.assertIn("st_res_$GOOD$_unlocked_trigger = yes", _block(EFFECTS, base), base)
        for effect in ("st_res_all_goods_stabilize_effect", "st_res_military_goods_stockpile_effect",
                       "st_res_all_goods_manual_effect"):
            body = _block(EFFECTS, effect)
            self.assertEqual(body.count("st_res_refresh_hub_flow_effect = yes"), 1, effect)
            self.assertLess(body.index("st_res_refresh_hub_cache_effect = yes"), body.index("_good_base"), effect)


class AiReviewTests(unittest.TestCase):
    def test_runs_weekly_and_not_on_activation(self):
        weekly = _block(EFFECTS, "st_res_weekly_update_effect")
        self.assertLess(weekly.index("st_res_ai_seed_policies_effect = yes"), weekly.index("st_res_ai_review_policies_effect = yes"))
        self.assertNotIn("st_res_ai_review_policies_effect", _block(EFFECTS, "st_res_je_immediate_effect"))
        self.assertNotIn("st_res_ai_review_policies_effect", _block(EFFECTS, "st_res_ai_seed_policies_effect"))

    def test_stockpiles_the_military_goods_and_puts_them_back(self):
        review = _block(EFFECTS, "st_res_ai_review_policies_effect")
        self.assertRegex(review, r"is_ai = yes")
        self.assertEqual(re.findall(r"GOOD = (\w+)\s+POLICY = 4 PRESET = stockpile", review), MILITARY)
        self.assertEqual(re.findall(r"GOOD = (\w+)\s+POLICY = 3 PRESET = conservative", review), MILITARY)
        self.assertIn("set_variable = { name = st_res_ai_stance value = 1 }", review)
        self.assertIn("set_variable = { name = st_res_ai_stance value = 2 }", review)

    def test_affordability_has_a_gap_between_starting_and_stopping(self):
        trig = _block(_read("common", "scripted_triggers", "st_res_triggers.txt"), "st_res_ai_wants_stockpile")
        self.assertIn("taking_loans = no", trig)
        self.assertIn("in_default = no", trig)
        self.assertRegex(trig, r"OR = \{\s*var:st_res_ai_stance \?= 1\s*scaled_gold_reserves >= st_res_ai_stockpile_min_reserves\s*\}")

    def test_a_reset_reserve_is_reviewed_afresh(self):
        self.assertIn("remove_variable = st_res_ai_stance", _block(EFFECTS, "st_res_reset_vars_effect"))


if __name__ == "__main__":
    unittest.main()
