# -*- coding: utf-8 -*-
"""SoL Expectations: the adaptive shift's ceiling sits at the mod's top wealth level.

sol_expectations_shift_clamped_value (extra_script_values.txt) caps the shift.
At 50 the cap stopped expectations following SoL above about 55-60, which an
era 12-13 country passes, and the gap then stayed positive for good (#2147).
The ceiling is now the mod's top wealth level, NPops NUM_WEALTH_LEVELS
(extra_defines.txt), so a change to either should be a decision about both.
The system doc quotes the figure twice by hand; this pins those too.

Run: python3 -m unittest test_sol_expectations_ceiling -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

SCRIPT_VALUES = os.path.join(REPO, "common", "script_values", "extra_script_values.txt")
DEFINES = os.path.join(REPO, "common", "defines", "extra_defines.txt")
SYSTEM_DOC = os.path.join(REPO, "docs", "systems", "mod_systems", "sol_expectations.md")


def _script(path):
    """Script text with comments stripped."""
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name, top_level=True):
    anchor = r"^" if top_level else r"(?<![\w.:])"
    m = re.search(anchor + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _ceiling_block():
    return _block(_script(SCRIPT_VALUES), "sol_expectations_shift_clamped_value")


def _ceiling():
    m = re.search(r"^\s*value\s*=\s*(\d+)\s*$", _block(_ceiling_block(), "max", top_level=False), re.M)
    if m is None:
        raise AssertionError("sol_expectations_shift_clamped_value's max has no literal base value")
    return int(m.group(1))


def _num_wealth_levels():
    m = re.search(r"^\s*NUM_WEALTH_LEVELS\s*=\s*(\d+)", _block(_script(DEFINES), "NPops"), re.M)
    if m is None:
        raise AssertionError("NUM_WEALTH_LEVELS not found in extra_defines.txt's NPops")
    return int(m.group(1))


class ShiftCeiling(unittest.TestCase):

    def test_ceiling_is_the_top_wealth_level(self):
        self.assertEqual(
            _ceiling(), _num_wealth_levels(),
            "the shift's ceiling should be NUM_WEALTH_LEVELS, so expectations can follow SoL "
            "across the wealth range (#2147)")

    def test_modifiers_still_lower_the_ceiling(self):
        self.assertIn("modifier:country_sol_expectations_shift_max_add",
                      _block(_ceiling_block(), "max", top_level=False))

    def test_system_doc_quotes_the_ceiling(self):
        with open(SYSTEM_DOC, encoding="utf-8") as f:
            doc = f.read()
        ceiling = _ceiling()
        self.assertIn(f"The ceiling is {ceiling} plus `country_sol_expectations_shift_max_add`", doc)
        self.assertIn(f"lower the ceiling (default {ceiling}) of the shift", doc)


if __name__ == "__main__":
    unittest.main()
