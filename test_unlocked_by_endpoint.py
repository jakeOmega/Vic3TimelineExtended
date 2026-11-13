"""GET /unlocked-by/<tech> with no server and no game install (#1698).

`/unlocked-by` takes another path than `/tech-unlocks`: it walks ModState's
merged data (`_find_unlocked_by_tech` in `mod_state_server.py`) where
`/tech-unlocks` reads `tech_unlocks_lib`'s index of the files, and only
`test_annotator_endpoints.py`, which needs a live server and so never runs
in CI, called it. Here `ModStateHandler.route` runs it over a small vanilla
and mod written to a temp dir, then over the mod's own files and the
committed vanilla snapshot.

Run:
    .venv/bin/python -m pytest test_unlocked_by_endpoint.py -q
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mod_state_server as mss
import pm_balance_lib
import vanilla_parsed
from mod_state import ModState

TYPES = {"Technologies": "technology/technologies", "PMs": "production_methods",
         "Laws": "laws", "Buildings": "buildings"}

GAME = {
    "technology/technologies": "tech_a = {\n\tera = era_1\n}\n",
    "production_methods": (
        "pm_vanilla = {\n\tunlocking_technologies = { tech_a }\n}\n"
        "pm_replaced = {\n\tunlocking_technologies = { tech_a }\n}\n"
    ),
    "laws": "law_vanilla = {\n\tunlocking_technologies = { tech_a }\n}\n",
    "buildings": "building_vanilla = {\n\tunlocking_technologies = { tech_a }\n}\n",
}

# The mod moves pm_replaced to its own tech, and spells two ids and a tech
# with a hyphen, as `pm_e-commerce` and `law_post-scarcity` do.
MOD = {
    "technology/technologies": (
        "e-commerce = {\n\tera = era_9\n\tunlocking_technologies = { tech_a }\n}\n"
        "tech_lonely = {\n\tera = era_9\n}\n"
    ),
    "production_methods": (
        "pm_e-commerce = {\n"
        "\tunlocking_technologies = { e-commerce }\n"
        "\tbuilding_modifiers = {\n"
        "\t\tworkforce_scaled = {\n"
        "\t\t\t# Total input cost: 100\n"
        "\t\t\t# Total output cost: 300\n"
        "\t\t\t# Profit: 200\n"
        "\t\t\t# Profit margin: 200%\n"
        "\t\t\t# Wage breakeven: 0.05\n"
        "\t\t}\n"
        "\t}\n"
        "}\n"
        "REPLACE:pm_replaced = {\n\tunlocking_technologies = { e-commerce }\n}\n"
    ),
    "laws": "law_post-scarcity = {\n\tunlocking_technologies = { e-commerce }\n}\n",
    "buildings": (
        "building_mod = {\n\tunlocking_technologies = { tech_a e-commerce }\n}\n"
    ),
}


def _state():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for side, files in (("game", GAME), ("mod", MOD)):
        for folder, text in files.items():
            (root / side / "common" / folder).mkdir(parents=True)
            (root / side / "common" / folder / "00_file.txt").write_text(
                text, encoding="utf-8")

    def dirs(side):
        return {et: str(root / side / "common" / folder) for et, folder in TYPES.items()}

    state = ModState(dirs("game"), dirs("mod"))
    state.localization = {"pm_e-commerce": "E-Commerce", "law_vanilla": "A Law"}
    return tmp, root / "mod", state


class SyntheticTests(unittest.TestCase):
    """ModStateHandler.route on /unlocked-by over a temp-dir vanilla and mod."""

    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.mod_root, cls.state = _state()
        cls.addClassCleanup(cls.tmp.cleanup)

    def get(self, *parts, **params):
        handler = object.__new__(mss.ModStateHandler)
        with mock.patch.multiple(mss, ms=self.state, mod_path=str(self.mod_root),
                                 _annotator_compute_cache={}):
            return handler.route(["unlocked-by", *parts],
                                 {k: [v] for k, v in params.items()})

    def test_lists_vanilla_and_mod_entities_by_type(self):
        self.assertEqual(self.get("tech_a"), {
            "Technologies": [{"type": "Technologies", "id": "e-commerce",
                              "name": "e-commerce"}],
            "PMs": [{"type": "PMs", "id": "pm_vanilla", "name": "pm_vanilla"}],
            "Laws": [{"type": "Laws", "id": "law_vanilla", "name": "A Law"}],
            "Buildings": [{"type": "Buildings", "id": "building_vanilla",
                           "name": "building_vanilla"},
                          {"type": "Buildings", "id": "building_mod",
                           "name": "building_mod"}],
        })

    def test_reads_the_merged_data_and_hyphenated_ids(self):
        # The mod's REPLACE moved pm_replaced off tech_a, so tech_a no longer
        # lists it and e-commerce does.
        out = self.get("e-commerce")
        self.assertEqual(sorted(e["id"] for e in out["PMs"]),
                         ["pm_e-commerce", "pm_replaced"])
        self.assertEqual([e["id"] for e in out["Laws"]], ["law_post-scarcity"])
        self.assertEqual([e["id"] for e in out["Buildings"]], ["building_mod"])
        self.assertNotIn("pm_replaced", [e["id"] for e in self.get("tech_a")["PMs"]])

    def test_annotate_balance_flags_the_mod_s_pms(self):
        # route()'s post-processor reads the cost comments under mod_path.
        # pm_replaced is a mod definition without a cost block: NO-COSTS.
        pms = {e["id"]: e for e in self.get("e-commerce", annotate="balance")["PMs"]}
        self.assertEqual(pms["pm_e-commerce"], {
            "type": "PMs", "id": "pm_e-commerce", "name": "E-Commerce",
            "flag": "HIGH-PROFIT", "margin_pct": 200.0, "wage_be": 0.05,
        })
        self.assertEqual(pms["pm_replaced"]["flag"], "NO-COSTS")
        # A vanilla PM the mod does not define gets no flag.
        self.assertNotIn("flag", self.get("tech_a", annotate="balance")["PMs"][0])
        # Without ?annotate= nothing is added.
        self.assertNotIn("flag", self.get("e-commerce")["PMs"][0])

    def test_a_tech_that_unlocks_nothing_is_empty(self):
        self.assertEqual(self.get("tech_lonely"), {})

    def test_unknown_or_missing_tech(self):
        with self.assertRaises(mss.NotFound):
            self.get("tech_nope")
        with self.assertRaises(mss.BadRequest):
            self.get()


class ModDataTests(unittest.TestCase):
    """The mod's own technologies, production methods, laws and buildings
    over the committed vanilla snapshot: the offline twin of
    `test_annotator_endpoints.py`'s two `/unlocked-by` tests."""

    @classmethod
    def setUpClass(cls):
        snap = vanilla_parsed.load(mss.VANILLA_PARSED_DIR)
        base = {et: mss.base_game_paths[et] for et in TYPES}
        mod = {et: mss.mod_paths[et] for et in TYPES}
        cls.state = ModState(base, mod, vanilla_data={et: snap.data[et] for et in TYPES})
        cls.state.localization = dict(snap.localization)
        cls.mod_pms = set(pm_balance_lib.build_pm_balance_map(Path(mss.mod_path)))

    def get(self, *parts, **params):
        handler = object.__new__(mss.ModStateHandler)
        with mock.patch.multiple(mss, ms=self.state, _annotator_compute_cache={}):
            return handler.route(["unlocked-by", *parts],
                                 {k: [v] for k, v in params.items()})

    def test_every_entry_carries_its_type(self):
        out = self.get("modern_tools")
        self.assertIn("PMs", out)
        for etype, entries in out.items():
            for e in entries:
                self.assertEqual(e["type"], etype)

    def test_annotate_balance_flags_every_pm_the_mod_defines(self):
        pms = self.get("modern_tools", annotate="balance")["PMs"]
        mod_defined = [e for e in pms if e["id"] in self.mod_pms]
        self.assertGreater(len(mod_defined), 5)
        for e in mod_defined:
            self.assertIn(e.get("flag"), pm_balance_lib.FLAGS, e)

    def test_hyphenated_pm(self):
        out = self.get("e-commerce")
        self.assertIn("pm_e-commerce", [e["id"] for e in out["PMs"]])


if __name__ == "__main__":
    unittest.main()
