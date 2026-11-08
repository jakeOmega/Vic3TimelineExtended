"""Every field of every mod static modifier names a registered modifier type.

The engine creates no modifier type on its own, not even the ones keyed by a culture: vanilla registers
``state_<culture>_standard_of_living_add`` and its two siblings for each of its cultures in
``common/modifier_type_definitions/``. A static modifier field naming an unregistered type logs
``Unknown modifier type`` at load and is dropped, so the modifier loads without it. #1518 generated the culture merges'
expected static modifiers without their types, and the next launch logged 126 such lines (2026-11-08). The server's
``/validate/engine-coverage`` would have flagged them, but it runs only on a reload, which a worktree build never does.

A known type is one vanilla registers (the committed ``vanilla_parsed/`` snapshot) or the mod does. ``icon`` is the only
other field a static modifier has, in vanilla and in the mod.

Run: python3 test_static_modifier_types.py
"""

import json
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
NOT_A_TYPE = {"icon"}


def _unwrap(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(path))
    return parser.data


def known_types():
    names = set(json.loads((ROOT / "vanilla_parsed/common/modifier_types.json").read_text(encoding="utf-8")))
    for path in sorted((ROOT / "common/modifier_type_definitions").glob("*.txt")):
        names |= set(_parse(path))
    return names


def unknown_fields():
    """[(file, static modifier, field)] for each field that names no registered type."""
    known = known_types()
    out = []
    for path in sorted((ROOT / "common/static_modifiers").glob("*.txt")):
        for name, body in _parse(path).items():
            body = _unwrap(body)
            if not isinstance(body, dict):
                continue
            for field in body:
                if field not in NOT_A_TYPE and field not in known:
                    out.append((path.name, name, field))
    return out


class StaticModifierTypesTest(unittest.TestCase):
    def test_every_field_names_a_registered_type(self):
        bad = unknown_fields()
        self.assertEqual(bad, [], "register these in common/modifier_type_definitions/ (or fix the name): %s" % bad[:10])

    def test_the_snapshot_holds_vanilla_culture_types(self):
        # The check rests on the snapshot listing the per-culture types; if a rebuild dropped them, every merged
        # culture's would look as known as vanilla's do, or vanilla's own static modifiers would fail here.
        known = known_types()
        for name in ("state_scottish_standard_of_living_add", "country_scottish_cultural_acceptance_add",
                     "country_fervor_target_scottish_add"):
            self.assertIn(name, known)


if __name__ == "__main__":
    unittest.main()
