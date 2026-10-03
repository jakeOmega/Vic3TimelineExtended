"""Unit tests for prestige_good_roster_audit.

A company makes its prestige goods in place of their base good, in its own
buildings, so a prestige good whose base good no `building_types` building
produces never appears. The audit flags those (`not_produced`) and the ones
only an extension building makes (`extension_only`), for every company the
mod touches.

Each test builds a throwaway mod tree (companies, buildings, PM groups, PMs,
goods, prestige goods) and a vanilla data set parsed from text, then runs the
real `load_state` merge.
"""
from __future__ import annotations

import os
import tempfile
import textwrap
import unittest

from paradox_file_parser import ParadoxFileParser
from prestige_good_roster_audit import audit, load_state, render_report

# Three buildings, one good each, through one PM group each.
_BUILDINGS = """
building_steel_mill = { production_method_groups = { pmg_steel } }
building_tool_shop = { production_method_groups = { pmg_tools } }
building_lab = { production_method_groups = { pmg_lab } }
"""
_PM_GROUPS = """
pmg_steel = { production_methods = { pm_steel } }
pmg_tools = { production_methods = { pm_tools_a pm_tools_b } }
pmg_lab = { production_methods = { pm_lab } }
"""
_PMS = """
pm_steel = { building_modifiers = { workforce_scaled = { goods_output_steel_add = 10 } } }
pm_tools_a = { building_modifiers = { workforce_scaled = { goods_input_steel_add = 5 } } }
pm_tools_b = { building_modifiers = { level_scaled = { goods_output_tools_add = 10 } } }
pm_lab = { building_modifiers = { workforce_scaled = { goods_output_research_add = 1 } } }
"""
_GOODS = "steel = { cost = 50 }\ntools = { cost = 40 }\nresearch = { cost = 1 }\nwine = { cost = 30 }\n"
_PRESTIGE = "prestige_good_fine_tools = {\n    base_good = tools\n}\n"


def _parse(text: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(textwrap.dedent(text))
        path = fh.name
    try:
        parser = ParadoxFileParser()
        parser.parse_file(path)
        return parser.data
    finally:
        os.unlink(path)


def _company(name: str, roster=(), extensions=(), prestige=(), opener_comment="") -> str:
    lines = [f"{name} = {{{(' ' + opener_comment) if opener_comment else ''}"]
    lines.append(f"    building_types = {{ {' '.join(roster)} }}")
    if extensions:
        lines.append(f"    extension_building_types = {{ {' '.join(extensions)} }}")
    if prestige:
        lines.append("    possible_prestige_goods = {")
        lines += [f"        {p}" for p in prestige]
        lines.append("    }")
    lines.append("}")
    return "\n".join(lines) + "\n"


class _Tree:
    """A temp mod tree holding `companies`, over shared buildings/PMs/goods."""

    def __init__(self, companies="", vanilla_companies=""):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        for sub, text in (
            ("company_types", companies),
            ("buildings", _BUILDINGS),
            ("production_method_groups", _PM_GROUPS),
            ("production_methods", _PMS),
            ("goods", _GOODS),
            ("prestige_goods", _PRESTIGE),
        ):
            os.makedirs(os.path.join(self.root, "common", sub))
            if text:
                with open(os.path.join(self.root, "common", sub, "test.txt"), "w", encoding="utf-8") as fh:
                    fh.write(textwrap.dedent(text))
        self.vanilla = {
            "Company Types": _parse(vanilla_companies) if vanilla_companies else {},
        }

    def run(self):
        state = load_state(self.root, vanilla_data=self.vanilla)
        return audit(state, mod_path=self.root)

    def cleanup(self):
        self._tmp.cleanup()


class PrestigeGoodRosterAuditTest(unittest.TestCase):
    def _run(self, **kw):
        tree = _Tree(**kw)
        self.addCleanup(tree.cleanup)
        return tree.run()

    def _kinds(self, result, unreviewed_only=True):
        return sorted(
            (f.kind, f.company, f.prestige_good)
            for f in result.flags
            if not (unreviewed_only and f.exemption)
        )

    def test_roster_building_making_the_base_good_is_clean(self):
        result = self._run(companies=_company(
            "company_a", roster=["building_steel_mill"], prestige=["prestige_good_generic_steel"]))
        self.assertEqual(self._kinds(result), [])
        self.assertEqual(result.prestige_goods_checked, 1)

    def test_output_in_any_pm_of_the_group_counts(self):
        # pm_tools_a makes nothing; pm_tools_b in the same group makes tools.
        result = self._run(companies=_company(
            "company_a", roster=["building_tool_shop"], prestige=["prestige_good_fine_tools"]))
        self.assertEqual(self._kinds(result), [])

    def test_extension_only_base_good_is_flagged(self):
        result = self._run(companies=_company(
            "company_a", roster=["building_lab"], extensions=["building_tool_shop"],
            prestige=["prestige_good_fine_tools"]))
        self.assertEqual(self._kinds(result), [("extension_only", "company_a", "prestige_good_fine_tools")])
        self.assertIn("building_tool_shop", result.flags[0].detail)

    def test_base_good_made_nowhere_is_flagged(self):
        result = self._run(companies=_company(
            "company_a", roster=["building_lab"], prestige=["prestige_good_generic_steel"]))
        self.assertEqual(self._kinds(result), [("not_produced", "company_a", "prestige_good_generic_steel")])

    def test_flag_points_at_the_prestige_good_line(self):
        result = self._run(companies=_company(
            "company_a", roster=["building_lab"], prestige=["prestige_good_generic_steel"]))
        flag = result.flags[0]
        self.assertEqual(flag.file, "common/company_types/test.txt")
        self.assertEqual(flag.line, 4)

    def test_mod_base_good_overrides_the_generic_name(self):
        # prestige_good_fine_tools is mod-defined with base_good = tools.
        result = self._run(companies=_company(
            "company_a", roster=["building_steel_mill"], prestige=["prestige_good_fine_tools"]))
        self.assertEqual(self._kinds(result), [("not_produced", "company_a", "prestige_good_fine_tools")])
        self.assertEqual(result.flags[0].base_good, "tools")

    def test_unknown_base_good_is_counted_not_flagged(self):
        # A vanilla named prestige good, and a generic one naming no known good.
        result = self._run(companies=_company(
            "company_a", roster=["building_lab"],
            prestige=["prestige_good_bohemian_crystal", "prestige_good_generic_glass"]))
        self.assertEqual(self._kinds(result), [])
        self.assertEqual(sorted(result.unresolved),
                         ["prestige_good_bohemian_crystal", "prestige_good_generic_glass"])
        self.assertIn("Unknown base goods", render_report(result))

    def test_vanilla_only_company_is_not_judged(self):
        result = self._run(vanilla_companies=_company(
            "company_v", roster=["building_lab"], prestige=["prestige_good_generic_steel"]))
        self.assertEqual(self._kinds(result, unreviewed_only=False), [])
        self.assertEqual(result.companies_vanilla_only, 1)

    def test_inject_into_vanilla_company_is_judged_on_merged_data(self):
        result = self._run(
            vanilla_companies=_company("company_v", roster=["building_steel_mill"]),
            companies=(
                "INJECT:company_v = {\n"
                "    possible_prestige_goods = {\n"
                "        prestige_good_fine_tools\n"
                "    }\n}\n"
            ),
        )
        self.assertEqual(self._kinds(result), [("not_produced", "company_v", "prestige_good_fine_tools")])
        self.assertEqual(result.flags[0].line, 3)

    def test_reviewed_on_the_prestige_good_line_suppresses(self):
        result = self._run(companies=(
            "company_a = {\n"
            "    building_types = { building_lab }\n"
            "    extension_building_types = { building_tool_shop }\n"
            "    possible_prestige_goods = {\n"
            "        prestige_good_fine_tools # REVIEWED 2026-10-03: charter is the point\n"
            "        prestige_good_generic_steel\n"
            "    }\n}\n"
        ))
        self.assertEqual(self._kinds(result), [("not_produced", "company_a", "prestige_good_generic_steel")])
        exempt = [f for f in result.flags if f.exemption]
        self.assertEqual(len(exempt), 1)
        self.assertEqual(exempt[0].exemption["date"], "2026-10-03")
        self.assertIn("Reviewed Exemptions", render_report(result))

    def test_reviewed_on_the_company_opener_covers_every_flag(self):
        result = self._run(companies=_company(
            "company_a", roster=["building_lab"],
            prestige=["prestige_good_generic_steel", "prestige_good_fine_tools"],
            opener_comment="# REVIEWED 2026-10-03: placeholder company"))
        self.assertEqual(self._kinds(result), [])
        self.assertEqual(len(result.flags), 2)

    def test_unrelated_comment_does_not_suppress(self):
        result = self._run(companies=(
            "company_a = {\n"
            "    building_types = { building_lab }\n"
            "    possible_prestige_goods = {\n"
            "        prestige_good_generic_steel # the good steel\n"
            "    }\n}\n"
        ))
        self.assertEqual(self._kinds(result), [("not_produced", "company_a", "prestige_good_generic_steel")])

    def test_commented_out_prestige_good_is_ignored(self):
        result = self._run(companies=(
            "company_a = {\n"
            "    building_types = { building_lab }\n"
            "    possible_prestige_goods = {\n"
            "        # prestige_good_generic_steel\n"
            "    }\n}\n"
        ))
        self.assertEqual(self._kinds(result, unreviewed_only=False), [])


if __name__ == "__main__":
    unittest.main()
