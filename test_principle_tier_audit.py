"""Unit tests for principle_tier_audit.

Power bloc principle tiers do not stack: the higher tier's blocks replace the
lower tier's, so a tier that leaves out a lower tier's modifier takes it away
on upgrade. The audit judges every consecutive tier pair the mod touches, on
merged vanilla + mod data, and stays silent on pairs where both tiers are
untouched vanilla.

Each test builds a throwaway mod tree (principles + principle groups) and a
vanilla data set parsed from text, then runs the real `load_state` merge.
"""
from __future__ import annotations

import os
import tempfile
import textwrap
import unittest

from paradox_file_parser import ParadoxFileParser
from principle_tier_audit import audit, load_state, render_report, scan_text


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


def _principle(name: str, body: str) -> str:
    return f"{name} = {{\n{textwrap.indent(textwrap.dedent(body).strip(), '    ')}\n}}\n"


def _group(name: str, *levels: str) -> str:
    return f"{name} = {{\n    levels = {{\n        {' '.join(levels)}\n    }}\n}}\n"


class _Tree:
    """A temp mod tree with optional vanilla data."""

    def __init__(self, mod_principles="", mod_groups="", vanilla_principles="", vanilla_groups=""):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        for sub, text in (
            ("power_bloc_principles", mod_principles),
            ("power_bloc_principle_groups", mod_groups),
        ):
            os.makedirs(os.path.join(self.root, "common", sub))
            if text:
                with open(os.path.join(self.root, "common", sub, "test.txt"), "w", encoding="utf-8") as fh:
                    fh.write(textwrap.dedent(text))
        self.vanilla = {
            "Principles": _parse(vanilla_principles) if vanilla_principles else {},
            "Principle Groups": _parse(vanilla_groups) if vanilla_groups else {},
        }

    def run(self):
        state = load_state(self.root, vanilla_data=self.vanilla)
        return audit(state, mod_path=self.root)

    def cleanup(self):
        self._tmp.cleanup()


class PrincipleTierAuditTest(unittest.TestCase):
    def _run(self, **kw):
        tree = _Tree(**kw)
        self.addCleanup(tree.cleanup)
        return tree.run()

    def _kinds(self, result, unreviewed_only=True):
        return sorted(
            (f.kind, f.principle, f.key)
            for f in result.flags
            if not (unreviewed_only and f.exemption)
        )

    # -- the pair checks ---------------------------------------------------

    def test_dropped_modifier_is_flagged_at_the_higher_tier(self):
        result = self._run(
            mod_groups=_group("principle_group_x", "px_1", "px_2"),
            mod_principles=(
                _principle("px_1", "member_modifier = { state_education_access_add = 0.05 country_tech_spread_mult = 0.05 }")
                + _principle("px_2", "member_modifier = { country_tech_spread_mult = 0.1 }")
            ),
        )
        self.assertEqual(self._kinds(result), [("dropped", "px_2", "state_education_access_add")])
        flag = result.flags[0]
        self.assertEqual(flag.lower, "px_1")
        self.assertEqual(flag.file, "common/power_bloc_principles/test.txt")
        self.assertEqual(flag.line, 4)  # px_2's opening line

    def test_restated_ladder_is_clean(self):
        result = self._run(
            mod_groups=_group("principle_group_x", "px_1", "px_2", "px_3"),
            mod_principles=(
                _principle("px_1", "member_modifier = { a_mult = 0.05 }")
                + _principle("px_2", "member_modifier = { a_mult = 0.05 b_add = 1 }\nleader_modifier = { c_bool = yes }")
                + _principle("px_3", "member_modifier = { a_mult = 0.1 b_add = 2 }\nleader_modifier = { c_bool = yes }")
            ),
        )
        self.assertEqual(result.flags, [])
        self.assertEqual(result.pairs_checked, 2)
        self.assertIn("_None._", render_report(result))

    def test_vanilla_only_pair_is_not_judged(self):
        result = self._run(
            vanilla_groups=_group("principle_group_v", "pv_1", "pv_2"),
            vanilla_principles=(
                _principle("pv_1", "power_bloc_modifier = { power_bloc_trade_advantage_add = 100 }")
                + _principle("pv_2", "power_bloc_modifier = { power_bloc_customs_union_bool = yes }")
            ),
        )
        self.assertEqual(result.flags, [])
        self.assertEqual(result.pairs_vanilla_only, 1)
        self.assertEqual(result.pairs_checked, 0)

    def test_slot_limit_inject_does_not_make_a_vanilla_pair_judged(self):
        tree = _Tree(
            vanilla_groups=_group("principle_group_v", "pv_1", "pv_2"),
            vanilla_principles=(
                _principle("pv_1", "power_bloc_modifier = { power_bloc_trade_advantage_add = 100 }")
                + _principle("pv_2", "power_bloc_modifier = { power_bloc_customs_union_bool = yes }")
            ),
        )
        self.addCleanup(tree.cleanup)
        gates = os.path.join(tree.root, "common", "power_bloc_principles", "te_principle_slot_gates_generated.txt")
        with open(gates, "w", encoding="utf-8") as fh:
            fh.write("INJECT:pv_2 = {\n    possible = { te_pb_principle_slot_free = { GROUP = principle_group_v } }\n}\n")
        result = tree.run()
        self.assertEqual(result.flags, [])
        self.assertEqual(result.pairs_vanilla_only, 1)

    def test_vanilla_tier_to_mod_tier_is_judged(self):
        result = self._run(
            vanilla_groups=_group("principle_group_v", "pv_1", "pv_2"),
            vanilla_principles=(
                _principle("pv_1", "member_modifier = { a_add = 1 }")
                + _principle("pv_2", "member_modifier = { a_add = 1 building_port_throughput_add = 0.1 }")
            ),
            mod_groups="INJECT:principle_group_v = {\n    levels = { pv_3 }\n}\n",
            mod_principles=_principle("pv_3", "member_modifier = { a_add = 2 }"),
        )
        self.assertEqual(self._kinds(result), [("dropped", "pv_3", "building_port_throughput_add")])

    def test_inject_into_vanilla_tier_is_judged_and_located_at_the_inject(self):
        result = self._run(
            vanilla_groups=_group("principle_group_v", "pv_1", "pv_2"),
            vanilla_principles=(
                _principle("pv_1", "member_modifier = { a_add = 1 }")
                + _principle("pv_2", "member_modifier = { a_add = 1 }")
            ),
            mod_principles="INJECT:pv_1 = {\n    member_modifier = {\n        b_add = 50\n    }\n}\n",
        )
        self.assertEqual(self._kinds(result), [("dropped", "pv_2", "b_add")])
        self.assertEqual(result.flags[0].line, 3)  # the injected line; pv_2 has no mod site

    def test_moved_to_another_block(self):
        result = self._run(
            mod_groups=_group("principle_group_x", "px_1", "px_2"),
            mod_principles=(
                _principle("px_1", "member_modifier = { state_assimilation_mult = 0.05 }")
                + _principle(
                    "px_2",
                    "institution = institution_schools\ninstitution_modifier = { state_assimilation_mult = 0.05 }",
                )
            ),
        )
        self.assertEqual(self._kinds(result), [("moved", "px_2", "state_assimilation_mult")])
        self.assertEqual(result.flags[0].block, "institution_modifier")

    def test_weaker_is_sign_aware(self):
        result = self._run(
            mod_groups=_group("principle_group_x", "px_1", "px_2"),
            mod_principles=(
                _principle("px_1", "member_modifier = { cost_mult = -0.25 gain_mult = -0.1 up_add = 0.2 }")
                + _principle("px_2", "member_modifier = { cost_mult = -0.1 gain_mult = -0.25 up_add = 0.1 }")
            ),
        )
        self.assertEqual(
            self._kinds(result),
            [("weaker", "px_2", "cost_mult"), ("weaker", "px_2", "up_add")],
        )

    def test_changed_non_numeric_value(self):
        result = self._run(
            mod_groups=_group("principle_group_x", "px_1", "px_2"),
            mod_principles=(
                _principle("px_1", "leader_modifier = { c_bool = yes }")
                + _principle("px_2", "leader_modifier = { c_bool = no }")
            ),
        )
        self.assertEqual(self._kinds(result), [("changed", "px_2", "c_bool")])

    def test_institution_changed_strands_the_institution_modifier(self):
        result = self._run(
            mod_groups=_group("principle_group_x", "px_1", "px_2"),
            mod_principles=(
                _principle("px_1", "institution = institution_schools\ninstitution_modifier = { a_mult = 0.1 }")
                + _principle("px_2", "institution = institution_health_system\ninstitution_modifier = { a_mult = 0.1 }")
            ),
        )
        self.assertEqual(self._kinds(result), [("institution_changed", "px_2", "institution")])

    # -- the per-principle checks ------------------------------------------

    def test_wrong_block_both_directions(self):
        result = self._run(
            mod_principles=_principle(
                "px_4",
                "power_bloc_modifier = { state_trade_advantage_same_religion_add = 50 }\n"
                "member_modifier = { power_bloc_cohesion_add = 5 }",
            ),
        )
        self.assertEqual(
            self._kinds(result),
            [
                ("wrong_block", "px_4", "power_bloc_cohesion_add"),
                ("wrong_block", "px_4", "state_trade_advantage_same_religion_add"),
            ],
        )

    def test_duplicate_block_in_one_definition(self):
        sources = scan_text(
            "px_4 = {\n    leader_modifier = { a_add = 1 }\n    member_modifier = { b_add = 1 }\n"
            "    leader_modifier = { c_bool = yes }\n}\n",
            "test.txt",
        )
        self.assertEqual(
            [(blk, a[1], b[1]) for blk, a, b in sources["px_4"].duplicate_blocks],
            [("leader_modifier", 2, 4)],
        )

    def test_inject_alongside_a_block_is_not_a_duplicate(self):
        sources = scan_text(
            "px_2 = {\n    member_modifier = { a_add = 1 }\n}\n"
            "INJECT:px_2 = {\n    member_modifier = { b_add = 1 }\n}\n",
            "test.txt",
        )
        self.assertEqual(sources["px_2"].duplicate_blocks, [])
        self.assertEqual(len(sources["px_2"].openers), 2)

    # -- suppression ---------------------------------------------------------

    def test_reviewed_on_the_higher_tier_opener_suppresses(self):
        result = self._run(
            mod_groups=_group("principle_group_x", "px_1", "px_2"),
            mod_principles=(
                _principle("px_1", "member_modifier = { a_add = 1 b_add = 1 }")
                + "px_2 = { # REVIEWED 2026-10-02: tier II trades a and b for c\n"
                "    member_modifier = { c_add = 1 }\n}\n"
            ),
        )
        self.assertEqual(self._kinds(result), [])
        self.assertEqual(len(result.flags), 2)
        self.assertEqual(result.flags[0].exemption["date"], "2026-10-02")
        self.assertIn("Reviewed Exemptions", render_report(result))

    def test_reviewed_on_the_lower_tier_key_line_suppresses_a_drop(self):
        result = self._run(
            mod_groups=_group("principle_group_x", "px_1", "px_2"),
            mod_principles=(
                "px_1 = {\n    member_modifier = {\n"
                "        a_add = 1 # REVIEWED 2026-10-02: tier I only\n"
                "        b_add = 1\n    }\n}\n"
                + _principle("px_2", "member_modifier = { c_add = 1 }")
            ),
        )
        self.assertEqual(self._kinds(result), [("dropped", "px_2", "b_add")])

    def test_unrelated_comment_does_not_suppress(self):
        result = self._run(
            mod_groups=_group("principle_group_x", "px_1", "px_2"),
            mod_principles=(
                _principle("px_1", "member_modifier = { a_add = 1 }")
                + "px_2 = { # Modifiers from previous level(s)\n    member_modifier = { c_add = 1 }\n}\n"
            ),
        )
        self.assertEqual(self._kinds(result), [("dropped", "px_2", "a_add")])


if __name__ == "__main__":
    unittest.main()
