"""GET /goods/<good>/producers and /consumers (#1757): which buildings make or
use a good, method by method, at what figure. A fixture ModState for the
shape, and the real data for Electricity against test_power_grid_tab's own
walk."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mod_state_server as mss
from mod_state import ModState

REPO = os.path.dirname(os.path.abspath(__file__))
GOODS = "coal = { cost = 30 }\nelectricity = { cost = 30 }\niron = { cost = 40 }\n"
BUILDINGS = """
building_power_plant = {
	building_group = bg_power
	production_method_groups = { pmg_base_building_power_plant pmg_capture }
}
building_iron_mine = {
	building_group = bg_mining
	production_method_groups = { pmg_mine }
}
building_grid_transfer_station = {
	building_group = bg_power
	production_method_groups = { pmg_transfer }
}
"""
GROUPS = """
pmg_base_building_power_plant = { production_methods = { pm_coal_fired_plant pm_oil_fired_plant } }
pmg_capture = { production_methods = { pm_no_capture } }
pmg_mine = { production_methods = { pm_basic_mine } }
pmg_transfer = { production_methods = { pm_transfer } }
"""
PMS = """
pm_coal_fired_plant = {
	building_modifiers = {
		workforce_scaled = {
			goods_input_coal_add = 30
			goods_output_electricity_add = 50
		}
	}
}
pm_oil_fired_plant = {
	building_modifiers = {
		workforce_scaled = { goods_output_electricity_add = 60 }
	}
}
pm_no_capture = { }
pm_basic_mine = {
	building_modifiers = {
		workforce_scaled = { goods_input_electricity_add = 5 goods_output_iron_add = 20 }
		level_scaled = { building_employment_laborers_add = 1000 }
	}
}
pm_transfer = {
	building_modifiers = { unscaled = { goods_output_electricity_add = 1 goods_input_electricity_add = 1 } }
}
"""
MOD_GROUPS = "REPLACE:pmg_capture = { production_methods = { pm_no_capture pm_te_capture } }\n"
MOD_PMS = """
pm_te_capture = {
	building_modifiers = { workforce_scaled = { goods_output_electricity_add = -4 } }
}
REPLACE:pm_oil_fired_plant = {
	building_modifiers = { workforce_scaled = { goods_output_electricity_add = 65 } }
}
"""


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class GoodsFlowEndpointTests(unittest.TestCase):
    TYPES = {"Goods": "goods", "Buildings": "buildings", "PM Groups": "production_method_groups",
             "PMs": "production_methods"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        base, mod = root / "base/game/common", root / "mod/common"
        for rel, text in (("goods/00.txt", GOODS), ("buildings/00.txt", BUILDINGS),
                          ("production_method_groups/00.txt", GROUPS), ("production_methods/00.txt", PMS)):
            _write(base / rel, text)
        _write(mod / "production_method_groups/te.txt", MOD_GROUPS)
        _write(mod / "production_methods/te.txt", MOD_PMS)
        state = ModState({et: str(base / rel) for et, rel in self.TYPES.items()},
                         {et: str(mod / rel) for et, rel in self.TYPES.items()})
        state.localization = {"building_power_plant": "Power Plant", "electricity": "Electricity"}
        patcher = mock.patch.object(mss, "ms", state)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.handler = object.__new__(mss.ModStateHandler)

    def request(self, path):
        self.handler.path = path
        self.handler._local_request_ok = mock.Mock(return_value=True)
        self.handler._respond_json = mock.Mock()
        self.handler.do_GET()
        args = self.handler._respond_json.call_args.args
        json.dumps(args[0])
        return (args[1] if len(args) > 1 else 200), args[0]

    def test_producers_per_method(self):
        status, body = self.request("/goods/electricity/producers")
        self.assertEqual(status, 200)
        self.assertEqual((body["modifier"], body["building_count"], body["method_count"]),
                         ("goods_output_electricity_add", 2, 4))
        plant = body["buildings"]["building_power_plant"]
        self.assertEqual((plant["name"], plant["building_group"], plant["source"]),
                         ("Power Plant", "bg_power", "vanilla"))
        self.assertEqual([(m["pm"], m["group"], m["block"], m["per_level"], m["source"]) for m in plant["methods"]], [
            ("pm_coal_fired_plant", "pmg_base_building_power_plant", "workforce_scaled", 50.0, "vanilla"),
            ("pm_oil_fired_plant", "pmg_base_building_power_plant", "workforce_scaled", 65.0, "modified"),
            ("pm_te_capture", "pmg_capture", "workforce_scaled", -4.0, "mod"),
        ])
        self.assertNotIn("inputs", plant["methods"][0])
        self.assertEqual(body["buildings"]["building_grid_transfer_station"]["methods"][0]["block"], "unscaled")

    def test_exclude_and_inputs(self):
        _status, body = self.request(
            "/goods/electricity/producers?exclude=building_grid_transfer_station&inputs=yes&outputs=yes")
        self.assertEqual(sorted(body["buildings"]), ["building_power_plant"])
        self.assertEqual(body["excluded"], ["building_grid_transfer_station"])
        coal = body["buildings"]["building_power_plant"]["methods"][0]
        self.assertEqual(coal["inputs"], [{"good": "coal", "block": "workforce_scaled", "per_level": 30.0}])
        # The good itself is not repeated among the other lines.
        self.assertEqual(coal["outputs"], [])

    def test_consumers(self):
        _status, body = self.request("/goods/electricity/consumers?outputs=yes")
        self.assertEqual(body["modifier"], "goods_input_electricity_add")
        mine = body["buildings"]["building_iron_mine"]["methods"]
        self.assertEqual([(m["pm"], m["per_level"], m["outputs"]) for m in mine], [
            ("pm_basic_mine", 5.0, [{"good": "iron", "block": "workforce_scaled", "per_level": 20.0}])])
        self.assertEqual(sorted(body["buildings"]), ["building_grid_transfer_station", "building_iron_mine"])
        _status, body = self.request("/goods/iron/consumers")
        self.assertEqual((body["building_count"], body["buildings"]), (0, {}))

    def test_catalog_entry_and_unknown_paths(self):
        status, rows = self.request("/goods")
        self.assertEqual((status, [r["id"] for r in rows]), (200, ["coal", "electricity", "iron"]))
        status, body = self.request("/goods/coal")
        self.assertEqual((status, body["id"], body["source"]), (200, "coal", "vanilla"))
        self.assertEqual(body["raw"], ["=", {"cost": ["=", "30"]}])
        # An unknown sub-path used to answer with the whole catalog at 200.
        for path in ("/goods/coal/whatever", "/goods/electricity/producers/extra", "/goods/electrcity",
                     "/goods/electrcity/producers"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.assertIn("electricity", self.request("/goods/electrcity")[1]["did_you_mean"])


class ElectricityAgainstThePowerGridWalkTests(unittest.TestCase):
    """The real data: every method that makes Electricity, at its figure, as
    test_power_grid_tab's _plant_methods() finds it (the Generation panel's
    table is held to that walk)."""

    def test_same_plants_and_figures(self):
        from mod_state import VANILLA_COMMON_DIRS
        from test_power_grid_tab import _plant_methods
        from vanilla_parsed import load

        kinds = ("Goods", "Buildings", "PMs", "PM Groups")
        state = ModState({kind: "/nonexistent" for kind in kinds},
                         {kind: os.path.join(REPO, "common", VANILLA_COMMON_DIRS[kind]) for kind in kinds},
                         vanilla_data=load(os.path.join(REPO, "vanilla_parsed")).data)
        with mock.patch.object(mss, "ms", state):
            handler = object.__new__(mss.ModStateHandler)
            body, status = handler.get_result("/goods/electricity/producers?exclude=building_grid_transfer_station")
        self.assertEqual(status, 200)
        got = {b: {m["pm"]: (m["block"], m["per_level"]) for m in rec["methods"]}
               for b, rec in body["buildings"].items()}
        plants, _inputs = _plant_methods()
        self.assertTrue(plants)
        self.assertEqual(got, plants)
        # The mod REPLACEs vanilla's power plant methods (extra_pms.txt) and adds its own.
        sources = {m["source"] for rec in body["buildings"].values() for m in rec["methods"]}
        self.assertEqual(sources, {"modified", "mod"})
        self.assertEqual(body["buildings"]["building_power_plant"]["methods"][1]["pm"], "pm_coal-fired_plant")


if __name__ == "__main__":
    unittest.main()
