"""Tests for the combat-unit cost helpers added to pm_costs.py."""

import os
import tempfile
import textwrap
import unittest

from pm_costs import (
    compute_combat_unit_breakdown,
    emit_combat_unit_market_cost_svs,
    update_combat_unit_loc,
)


GOODS = {"tanks": 120, "artillery": 70, "oil": 40, "iron": 30}


class ComputeCombatUnitBreakdownTest(unittest.TestCase):
    def test_skips_inject_entries(self):
        body = textwrap.dedent(
            """\
            INJECT:combat_unit_type_line_infantry = {
                upkeep_modifier = {
                    goods_input_iron_add = 99
                }
            }

            combat_unit_type_armored_infantry = {
                upkeep_modifier = {
                    goods_input_tanks_add = 4
                    goods_input_artillery_add = 10
                    goods_input_oil_add = 4
                }
            }
            """
        )
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(body)
            path = f.name
        try:
            out = compute_combat_unit_breakdown(path, GOODS)
        finally:
            os.unlink(path)
        self.assertEqual(set(out.keys()), {"armored_infantry"})
        rows = out["armored_infantry"]
        self.assertIn(("tanks", 4, 120), rows)
        self.assertIn(("artillery", 10, 70), rows)
        self.assertIn(("oil", 4, 40), rows)

    def test_only_first_upkeep_block_per_unit(self):
        body = textwrap.dedent(
            """\
            combat_unit_type_solo = {
                battle_modifier = {
                    goods_input_iron_add = 99
                }
                upkeep_modifier = {
                    goods_input_tanks_add = 2
                }
            }
            """
        )
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(body)
            path = f.name
        try:
            out = compute_combat_unit_breakdown(path, GOODS)
        finally:
            os.unlink(path)
        # The non-upkeep block also matches goods_input_iron_add lexically;
        # confirm we captured the upkeep block specifically and not the
        # battle_modifier block.
        rows = out["solo"]
        self.assertIn(("tanks", 2, 120), rows)
        self.assertNotIn(("iron", 99, 30), rows)


class UpdateCombatUnitLocTest(unittest.TestCase):
    def _write_loc(self, body):
        path = tempfile.NamedTemporaryFile(
            "wb", suffix=".yml", delete=False
        ).name
        with open(path, "wb") as f:
            f.write("﻿".encode("utf-8"))
            f.write(body.encode("utf-8"))
        return path

    def test_round_trip_appends_market_line_and_corrects_base(self):
        loc_body = (
            "l_english:\n"
            ' combat_unit_type_armored_infantry:0 "Armored Infantry"\n'
            ' combat_unit_type_armored_infantry_desc:0 "Some flavor.\\n\\nCost at base prices: #N @money!999 #!"\n'
        )
        path = self._write_loc(loc_body)
        try:
            breakdown = {
                "armored_infantry": [
                    ("tanks", 4, 120),
                    ("artillery", 10, 70),
                    ("oil", 4, 40),
                ]
            }
            warnings = update_combat_unit_loc(path, breakdown)
            with open(path, "rb") as f:
                raw = f.read()
        finally:
            os.unlink(path)
        # BOM survives.
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        text = raw.decode("utf-8-sig")
        self.assertEqual(warnings, [])
        # Base-price integer corrected to 4*120 + 10*70 + 4*40 = 1340.
        self.assertIn("Cost at base prices: #N @money!1340 #!", text)
        # Market-price line appended with the right SV reference.
        self.assertIn(
            "Cost at current market prices: #N @money!"
            "[GetPlayer.MakeScope.ScriptValue("
            "'value_combat_unit_market_cost_armored_infantry')|0] #!",
            text,
        )
        # Old number is gone.
        self.assertNotIn("@money!999", text)

    def test_warns_on_missing_desc(self):
        loc_body = (
            "l_english:\n"
            ' combat_unit_type_armored_infantry:0 "Armored Infantry"\n'
        )
        path = self._write_loc(loc_body)
        try:
            warnings = update_combat_unit_loc(
                path, {"armored_infantry": [("tanks", 1, 120)]}
            )
        finally:
            os.unlink(path)
        self.assertEqual(len(warnings), 1)
        self.assertIn("no _desc key", warnings[0])

    def test_warns_on_missing_cost_suffix(self):
        loc_body = (
            "l_english:\n"
            ' combat_unit_type_armored_infantry_desc:0 "Some flavor without a cost line."\n'
        )
        path = self._write_loc(loc_body)
        try:
            warnings = update_combat_unit_loc(
                path, {"armored_infantry": [("tanks", 1, 120)]}
            )
        finally:
            os.unlink(path)
        self.assertEqual(len(warnings), 1)
        self.assertIn("Cost at base prices", warnings[0])

    def test_idempotent_second_run(self):
        loc_body = (
            "l_english:\n"
            ' combat_unit_type_armored_infantry_desc:0 "Some flavor.\\n\\nCost at base prices: #N @money!500 #!"\n'
        )
        path = self._write_loc(loc_body)
        breakdown = {"armored_infantry": [("tanks", 4, 120)]}
        try:
            update_combat_unit_loc(path, breakdown)
            with open(path, "rb") as f:
                first = f.read()
            update_combat_unit_loc(path, breakdown)
            with open(path, "rb") as f:
                second = f.read()
        finally:
            os.unlink(path)
        self.assertEqual(first, second)


class EmitMarketCostSvsTest(unittest.TestCase):
    def test_sv_shape(self):
        breakdown = {
            "armored_infantry": [
                ("tanks", 4, 120),
                ("oil", 4, 40),
            ]
        }
        with tempfile.NamedTemporaryFile(
            "r", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            path = f.name
        try:
            emit_combat_unit_market_cost_svs(path, breakdown)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        finally:
            os.unlink(path)
        self.assertIn("AUTO-GENERATED", content)
        self.assertIn("value_combat_unit_market_cost_armored_infantry = {", content)
        self.assertIn(
            "value = this.market.mg:tanks.market_goods_pricier", content
        )
        self.assertIn("value = this.market.mg:oil.market_goods_pricier", content)
        # 4 * 120 = 480 and 4 * 40 = 160.
        self.assertIn("multiply = 480", content)
        self.assertIn("multiply = 160", content)
        self.assertIn("add = 1", content)

    def test_skips_units_with_no_inputs(self):
        breakdown = {"empty_unit": []}
        with tempfile.NamedTemporaryFile(
            "r", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            path = f.name
        try:
            emit_combat_unit_market_cost_svs(path, breakdown)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        finally:
            os.unlink(path)
        self.assertNotIn("value_combat_unit_market_cost_empty_unit", content)


if __name__ == "__main__":
    unittest.main()
