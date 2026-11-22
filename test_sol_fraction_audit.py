"""Tests for sol_fraction_audit (issue #338)."""

import os
import tempfile
import unittest

import sol_fraction_audit as sfa


def _mod(files: dict[str, str]) -> str:
    """Build a temp mod tree from {relative path: contents}; return its root."""
    td = tempfile.mkdtemp()
    for rel, content in files.items():
        p = os.path.join(td, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8-sig") as f:
            f.write(content)
    return td


def _flagged(mod: str) -> list[tuple[str, str]]:
    return [(f.entity, f.value) for f in sfa.audit(mod).flags if not f.exemption]


SM = "common/static_modifiers/m.txt"


class SolFractionAuditTests(unittest.TestCase):
    def test_fraction_in_a_flat_static_modifier_is_flagged(self):
        mod = _mod({
            SM: "flat_mod = {\n\tstate_standard_of_living_add = 0.5\n}\n",
            "events/e.txt": "e.1 = {\n\timmediate = { add_modifier = { name = flat_mod days = 30 } }\n}\n",
        })
        self.assertEqual(_flagged(mod), [("flat_mod", "0.5")])

    def test_whole_numbers_are_clean(self):
        mod = _mod({SM: "m = {\n\tstate_lower_strata_standard_of_living_add = -2\n"
                        "\tstate_standard_of_living_add = 1.0\n}\n"})
        self.assertEqual(_flagged(mod), [])

    def test_fractional_part_of_a_larger_value_is_flagged(self):
        mod = _mod({SM: "m = {\n\tstate_standard_of_living_add = -1.5\n}\n"})
        self.assertEqual(_flagged(mod), [("m", "-1.5")])

    def test_modifier_applied_with_a_multiplier_is_skipped(self):
        mod = _mod({
            SM: "scaled = {\n\tstate_standard_of_living_add = 0.25\n}\n",
            "events/e.txt": "e.1 = {\n\timmediate = {\n\t\tadd_modifier = {\n"
                            "\t\t\tname = scaled\n\t\t\tmultiplier = var:x\n\t\t}\n\t}\n}\n",
        })
        self.assertEqual(_flagged(mod), [])

    def test_modifier_applied_through_a_helper_with_a_multiplier_is_skipped(self):
        mod = _mod({
            SM: "scaled = {\n\tstate_standard_of_living_add = 0.25\n}\n",
            "common/scripted_effects/h.txt": "apply_it = {\n\tadd_modifier = { name = $MOD$ multiplier = 3 }\n}\n",
            "events/e.txt": "e.1 = {\n\timmediate = { apply_it = { MOD = scaled } }\n}\n",
        })
        self.assertEqual(_flagged(mod), [])

    def test_journal_entry_scaling_modifier_is_skipped(self):
        mod = _mod({
            SM: "je_scaled = {\n\tstate_standard_of_living_add = 0.2\n}\n",
            "common/journal_entries/j.txt": "je_x = {\n\tscaling_modifiers_while_active = {\n"
                                            "\t\tmodifier = je_scaled\n\t\tvalue = 3\n\t}\n}\n",
        })
        self.assertEqual(_flagged(mod), [])

    def test_workforce_scaled_block_is_skipped(self):
        mod = _mod({"common/production_methods/p.txt":
                    "pm_x = {\n\tstate_modifiers = {\n\t\tworkforce_scaled = {\n"
                    "\t\t\tstate_standard_of_living_add = 0.5\n\t\t}\n\t}\n}\n"})
        self.assertEqual(_flagged(mod), [])

    def test_institution_scaled_line_flagged_only_below_one_at_the_top_level(self):
        law = ("law_x = {\n\tinstitution_modifier = {\n"
               "\t\tstate_upper_strata_standard_of_living_add = 0.25\n"
               "\t\tstate_middle_strata_standard_of_living_add = 0.1\n\t}\n"
               "\tmodifier = {\n\t\tstate_standard_of_living_add = 0.25\n\t}\n}\n")
        # Vanilla's 5 levels: 0.25 reaches 1.25, 0.1 only 0.5.
        flags = sfa.audit(_mod({"common/laws/l.txt": law})).flags
        self.assertEqual(
            sorted((f.key, f.value, f.institution_scaled) for f in flags),
            [("state_middle_strata_standard_of_living_add", "0.1", True),
             ("state_standard_of_living_add", "0.25", False)])
        # At 9 levels 0.1 still reaches only 0.9; 0.125 would reach 1.125.
        mod = _mod({"common/laws/l.txt": law.replace("0.1\n", "0.125\n"),
                    "common/defines/d.txt": "NPolitics = {\n\tMAX_INSTITUTION_INVESTMENT = 9\n}\n"})
        self.assertEqual(_flagged(mod), [("law_x", "0.25")])

    def test_institutions_own_modifier_is_per_level(self):
        mod = _mod({"common/institutions/i.txt":
                    "institution_x = {\n\tmodifier = {\n\t\tstate_standard_of_living_add = 0.5\n\t}\n}\n"})
        self.assertEqual(_flagged(mod), [])

    def test_reviewed_comment_suppresses(self):
        mod = _mod({SM: "m = {\n\tstate_standard_of_living_add = 0.5 "
                        "# REVIEWED 2026-11-12: stacks with n to reach 1\n}\n"})
        flags = sfa.audit(mod).flags
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].exemption["date"], "2026-11-12")
        self.assertIn("2026-11-12", sfa.render_report(sfa.audit(mod)))

    def test_comments_and_script_values_are_ignored(self):
        mod = _mod({
            SM: "m = {\n\t# state_standard_of_living_add = 0.5\n}\n",
            "common/script_values/v.txt": "x = {\n\tstate_standard_of_living_add = 0.5\n}\n",
        })
        self.assertEqual(_flagged(mod), [])


if __name__ == "__main__":
    unittest.main()
