"""Tests for pm_costs.py: the combat-unit cost helpers, and running it from
parsed vanilla goods (the snapshot or a ModState) instead of the game files."""

import os
import shutil
import tempfile
import textwrap
import types
import unittest
from unittest import mock

import pm_costs
import vanilla_parsed
from paradox_file_parser import ParadoxFileParser
from pm_costs import (
    calculate_costs,
    calculate_employment,
    compute_combat_unit_breakdown,
    emit_combat_unit_market_cost_svs,
    goods_from_parsed,
    load_goods,
    parse_goods,
    process_and_update_military_costs,
    process_and_update_production_methods_grouped,
    update_combat_unit_loc,
)

REPO = os.path.dirname(os.path.abspath(__file__))


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
        # Market-price line appended with the right SV reference, using the
        # tagged game-concept label pm_costs._build_market_cost_line emits.
        self.assertIn(
            "Cost at current [Concept('concept_market_price', 'market prices')]: "
            "#N @money!"
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


def _read_text(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return fh.read()


def _goods_mod_state(goods_data):
    parser = ParadoxFileParser()
    parser.data = goods_data
    return types.SimpleNamespace(base_parsers={"Goods": parser})


class GoodsFromParsedTest(unittest.TestCase):
    def test_reads_cost_through_operator_tuples(self):
        data = {
            "iron": ("=", {"texture": ("=", '"x.dds"'), "cost": ("=", "30")}),
            "tanks": ("=", {"cost": ("=", "120"), "category": ("=", "military")}),
        }
        self.assertEqual(goods_from_parsed(data), {"iron": 30, "tanks": 120})

    def test_skips_a_good_without_a_numeric_cost(self):
        data = {
            "nameless": ("=", {"texture": ("=", '"x.dds"')}),
            "odd": ("=", {"cost": ("=", "cheap")}),
            "not_a_block": ("=", "yes"),
            "iron": ("=", {"cost": ("=", "30")}),
        }
        self.assertEqual(goods_from_parsed(data), {"iron": 30})

    def test_matches_parse_goods_on_a_goods_file(self):
        text = (
            'iron = {\n\ttexture = "x.dds"\n\tcost = 30\n\tcategory = industrial\n}\n'
            'tanks = {\n\ttexture = "y.dds"\n\tcost = 120\n}\n'
        )
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(text)
            path = f.name
        try:
            parser = ParadoxFileParser()
            parser.parse_file(path)
            self.assertEqual(goods_from_parsed(parser.data), parse_goods([path]))
            self.assertEqual(parse_goods([path]), {"iron": 30, "tanks": 120})
        finally:
            os.unlink(path)


class LoadGoodsTest(unittest.TestCase):
    """Vanilla prices come from parsed data when there's no game install."""

    @classmethod
    def setUpClass(cls):
        cls.snapshot = vanilla_parsed.load()

    def test_snapshot_prices_without_game_files(self):
        with mock.patch.object(pm_costs, "_vanilla_game_dir", return_value=None):
            goods = load_goods()
        for good in ("iron", "ammunition"):
            # ("=", {... "cost": ("=", "<n>") ...}) in the parsed snapshot.
            self.assertEqual(goods[good], int(self.snapshot.data["Goods"][good][1]["cost"][1]))
        # The mod's own goods file is layered on top.
        mod_goods = parse_goods([
            os.path.join(REPO, "common", "goods", "timeline_extended_extra_goods.txt")
        ])
        self.assertTrue(mod_goods)
        for good, cost in mod_goods.items():
            self.assertEqual(goods[good], cost)
        self.assertGreater(len(goods), len(mod_goods))

    def test_mod_state_vanilla_wins_over_the_snapshot(self):
        mod_state = _goods_mod_state({"iron": ("=", {"cost": ("=", "999")})})
        with mock.patch.object(pm_costs, "_vanilla_game_dir", return_value=None):
            goods = load_goods(mod_state)
        self.assertEqual(goods["iron"], 999)
        self.assertNotIn("ammunition", goods)

    def test_game_files_preferred_standalone(self):
        with tempfile.TemporaryDirectory() as game:
            os.makedirs(os.path.join(game, "common", "goods"))
            with open(os.path.join(game, "common", "goods", "00_goods.txt"), "w", encoding="utf-8") as f:
                f.write('iron = {\n\ttexture = "x.dds"\n\tcost = 31\n}\n')
            with mock.patch.object(pm_costs, "_vanilla_game_dir", return_value=game):
                self.assertEqual(load_goods()["iron"], 31)
                # ...but a server's ModState is still the authority.
                mod_state = _goods_mod_state({"iron": ("=", {"cost": ("=", "40")})})
                self.assertEqual(load_goods(mod_state)["iron"], 40)


class SnapshotReproducesCommittedFilesTest(unittest.TestCase):
    """Annotating the mod's files with snapshot prices leaves them as committed:
    this is what lets pm_costs run in a session with no game install (#624).
    A failure means a price, a PM or a combat unit changed without a regenerate."""

    @classmethod
    def setUpClass(cls):
        with mock.patch.object(pm_costs, "_vanilla_game_dir", return_value=None):
            cls.goods = load_goods()

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def _copy(self, rel):
        src = os.path.join(REPO, *rel.split("/"))
        dst = os.path.join(self.tmp, os.path.basename(src))
        shutil.copyfile(src, dst)
        return src, dst

    def test_mod_production_methods(self):
        for rel in ("common/production_methods/extra_pms.txt", "common/production_methods/unique_pms.txt"):
            src, dst = self._copy(rel)
            process_and_update_production_methods_grouped(
                dst, self.goods, calculate_costs, calculate_employment
            )
            self.assertEqual(_read_text(dst), _read_text(src), rel)

    def test_mod_military_files(self):
        for rel in (
            "common/combat_unit_types/extra_combat_units.txt",
            "common/mobilization_options/extra_mobilization_options.txt",
        ):
            src, dst = self._copy(rel)
            process_and_update_military_costs(dst, self.goods)
            self.assertEqual(_read_text(dst), _read_text(src), rel)

    def test_combat_unit_market_cost_script_values(self):
        units = os.path.join(REPO, "common", "combat_unit_types", "extra_combat_units.txt")
        out = os.path.join(self.tmp, "auto_combat_unit_market_costs.txt")
        emit_combat_unit_market_cost_svs(out, compute_combat_unit_breakdown(units, self.goods))
        committed = os.path.join(REPO, "common", "script_values", "auto_combat_unit_market_costs.txt")
        self.assertEqual(_read_text(out), _read_text(committed))

    def test_combat_unit_loc(self):
        units = os.path.join(REPO, "common", "combat_unit_types", "extra_combat_units.txt")
        src, dst = self._copy("localization/english/te_combat_units_l_english.yml")
        warnings = update_combat_unit_loc(dst, compute_combat_unit_breakdown(units, self.goods))
        self.assertEqual(warnings, [])
        self.assertEqual(_read_text(dst), _read_text(src))


class VanillaDocsGateTest(unittest.TestCase):
    """The two docs/engine/commented_vanilla_* files are cut from raw vanilla
    text, so only a run with usable game files writes them."""

    def _run(self, game_dir, **kwargs):
        with mock.patch.object(pm_costs, "_vanilla_game_dir", return_value=game_dir), \
                mock.patch.object(pm_costs, "load_goods", return_value=GOODS), \
                mock.patch.object(pm_costs, "process_and_update_production_methods_grouped") as pms, \
                mock.patch.object(pm_costs, "process_and_update_military_costs") as military, \
                mock.patch.object(pm_costs, "compute_combat_unit_breakdown", return_value={}), \
                mock.patch.object(pm_costs, "emit_combat_unit_market_cost_svs") as svs, \
                mock.patch.object(pm_costs, "update_combat_unit_loc", return_value=[]) as loc:
            pm_costs._run(dry_run=False, verbose=False, **kwargs)
        return pms, military, svs, loc

    def _game_dir(self):
        game = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, game)
        pms = os.path.join(game, "common", "production_methods")
        units = os.path.join(game, "common", "combat_unit_types")
        os.makedirs(pms)
        os.makedirs(units)
        open(os.path.join(pms, "01_industry.txt"), "w").close()
        for name in ("00_land_combat_unit_types.txt", "01_navy_combat_unit_types.txt"):
            open(os.path.join(units, name), "w").close()
        return game

    @staticmethod
    def _write_paths(mock_fn):
        """The write_path each call got: None for an in-place annotation."""
        out = []
        for c in mock_fn.call_args_list:
            if "write_path" in c.kwargs:
                out.append(c.kwargs["write_path"])
            else:
                # process_and_update_production_methods_grouped(path, goods, costs, employment, write_path)
                out.append(c.args[4] if len(c.args) > 4 else None)
        return out

    def test_no_game_files_annotates_the_mod_only(self):
        pms, military, svs, loc = self._run(None)
        self.assertEqual(len(pms.call_args_list), 2)  # extra_pms, unique_pms
        self.assertEqual(self._write_paths(pms), [None, None])
        self.assertEqual(len(military.call_args_list), 2)  # extra units, mobilization
        self.assertEqual(self._write_paths(military), [None, None])
        svs.assert_called_once()
        loc.assert_called_once()

    def test_game_files_also_write_the_commented_vanilla_docs(self):
        pms, military, _svs, _loc = self._run(self._game_dir())
        paths = [os.path.basename(p) for p in self._write_paths(pms) if p]
        self.assertEqual(paths, ["commented_vanilla_pms.txt"])
        paths = [os.path.basename(p) for p in self._write_paths(military) if p]
        self.assertEqual(paths, ["commented_vanilla_military_units.txt"])

    def test_vanilla_files_false_ignores_game_files_on_disk(self):
        # The server's verdict (files older than the snapshot) beats what is on disk.
        pms, military, svs, _loc = self._run(self._game_dir(), vanilla_files=False)
        self.assertEqual(self._write_paths(pms), [None, None])
        self.assertEqual(self._write_paths(military), [None, None])
        svs.assert_called_once()

    def test_regenerate_passes_the_server_arguments_through(self):
        with mock.patch.object(pm_costs, "_run") as run:
            pm_costs.regenerate("ms", vanilla_files=False)
        run.assert_called_once_with(dry_run=False, verbose=False, mod_state="ms", vanilla_files=False)


if __name__ == "__main__":
    unittest.main()
