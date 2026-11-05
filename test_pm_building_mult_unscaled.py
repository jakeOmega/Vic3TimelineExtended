"""A production method's percentage on its own building sits in `unscaled`.

`workforce_scaled` and `level_scaled` multiply every value by the building's
(staffed) level, which is right for a flat add and wrong for a `_mult`: the
shipyard focus methods' -20% civilian output was -200% on a level-10 yard,
taking its output below zero. Vanilla has 83 building-scope `_mult` modifiers
in its methods, every one `unscaled` (scripting_best_practices.md § "A
Building's Own `_mult` in a PM Belongs in `unscaled`").
"""

from pathlib import Path
import unittest

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
SCALED = ("workforce_scaled", "level_scaled")
CIVILIAN_HULLS = ("clippers", "steamers", "motor_ships", "magnetic_drive_ships")


def pairs(body):
    """(key, value) for each entry of a block; one that repeats a key parses as a list."""
    for item in body if isinstance(body, list) else [body]:
        if isinstance(item, dict):
            for key, value in item.items():
                yield key, value[1] if isinstance(value, tuple) else value


def methods():
    for path in sorted((ROOT / "common/production_methods").glob("*.txt")):
        parser = ParadoxFileParser()
        parser.parse_file(str(path), apply_directives=False)
        for name, value in parser.data.items():
            yield path.name, name, value[1] if isinstance(value, tuple) else value


def building_blocks(method):
    """{scaling: {key: value}} for the method's building_modifiers."""
    blocks = {}
    for key, body in pairs(method):
        if key == "building_modifiers":
            for scaling, inner in pairs(body):
                blocks.setdefault(scaling, {}).update(pairs(inner))
    return blocks


class BuildingMultUnscaledTest(unittest.TestCase):
    def test_no_building_mult_is_scaled(self):
        found = [
            f"{file}: {name} {scaling} {key}"
            for file, name, method in methods()
            for scaling, block in building_blocks(method).items()
            if scaling in SCALED
            for key in block
            if key.endswith("_mult")
        ]
        self.assertEqual(found, [], "move these to building_modifiers = { unscaled = { ... } }")

    def test_shipyard_focus_percentages(self):
        """The focus methods change civilian hull output by a flat percentage."""
        want = {
            "pm_focus_civilian_production": "0.25",
            "pm_focus_naval_production": "-0.20",
            "pm_focus_wartime_mobilization": "-0.40",
        }
        found = {name: method for _, name, method in methods() if name in want}
        self.assertEqual(sorted(found), sorted(want))
        for name, value in want.items():
            unscaled = building_blocks(found[name]).get("unscaled", {})
            with self.subTest(method=name):
                self.assertEqual(
                    {hull: unscaled.get(f"goods_output_{hull}_mult") for hull in CIVILIAN_HULLS},
                    dict.fromkeys(CIVILIAN_HULLS, value),
                )


if __name__ == "__main__":
    unittest.main()
