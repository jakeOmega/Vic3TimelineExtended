"""Tests for effect_trigger_validity_audit (issue #146)."""

import os
import tempfile
import unittest

import effect_trigger_validity_audit as eva

# A minimal "known-good" catalog for the synthetic mods below.
VALID = {"add_modifier", "name", "multiplier", "if", "limit", "value",
         "trigger_event", "id", "add", "subtract", "is_war_participant"}


class _Mod:
    """Build a temp mod tree of {relpath: content} and clean it up."""

    def __init__(self, files: dict[str, str]):
        self.root = tempfile.mkdtemp()
        for rel, content in files.items():
            p = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8-sig") as f:
                f.write(content)

    def audit(self):
        return eva.audit(self.root, valid_keys=VALID)


def _flagged(result):
    return {(f.keyword, f.kind) for f in result.flags if not f.exemption}


class DetectionTests(unittest.TestCase):
    def test_unknown_effect_flagged(self):
        m = _Mod({"events/e.txt": "my.1 = {\n\tadd_authority = -200\n}\n"})
        self.assertIn(("add_authority", "unknown-name"), _flagged(m.audit()))

    def test_valid_effect_not_flagged(self):
        m = _Mod(
            {"events/e.txt": "my.1 = {\n\tadd_modifier = { name = x multiplier = 1 }\n}\n"}
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_unquoted_call_syntax_flagged(self):
        m = _Mod({"events/e.txt": "my.1 = {\n\tvalue = negate(foo)\n}\n"})
        flags = _flagged(m.audit())
        self.assertIn(("negate(...)", "call-syntax"), flags)

    def test_quoted_scripted_value_call_not_flagged(self):
        # The legit Vic3 form lives inside quotes — must not flag as call-syntax.
        m = _Mod(
            {
                "common/scripted_triggers/t.txt": 'tg = {\n'
                '\tvalue = "cultural_acceptance_delta(PREV)"\n}\n'
            }
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_param_interpolated_identifier_not_flagged(self):
        # `heir_education_$TRAIT$_ig_reaction = yes` must not match the tail.
        m = _Mod(
            {"common/scripted_effects/s.txt": "se = {\n\their_education_$TRAIT$_ig_reaction = yes\n}\n"}
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_uppercase_param_not_flagged(self):
        m = _Mod({"common/scripted_effects/s.txt": "se = {\n\tte_foo = { GOOD = wood }\n}\n"})
        self.assertEqual(_flagged(m.audit()), set())

    def test_curated_valid_key_not_flagged(self):
        m = _Mod({"events/e.txt": 'my.1 = {\n\tevent_image = { texture = "x.dds" }\n}\n'})
        self.assertNotIn("texture", {f.keyword for f in m.audit().flags})


class NameHarvestTests(unittest.TestCase):
    def test_mod_scripted_effect_name_not_flagged(self):
        m = _Mod(
            {
                "common/scripted_effects/s.txt": "te_helper = {\n\tadd_modifier = { name = x }\n}\n",
                "events/e.txt": "my.1 = {\n\tte_helper = yes\n}\n",
            }
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_script_value_compared_as_trigger_not_flagged(self):
        m = _Mod(
            {
                "common/script_values/v.txt": "te_counter = {\n\tvalue = 3\n}\n",
                "events/e.txt": "my.1 = {\n\tif = { limit = { te_counter = 0 } }\n}\n",
            }
        )
        self.assertEqual(_flagged(m.audit()), set())


class SuppressionTests(unittest.TestCase):
    def test_reviewed_partitions_flag(self):
        m = _Mod(
            {"events/e.txt": "my.1 = {\n\tbogus_effect = 1  # REVIEWED 2026-05-24: intentional\n}\n"}
        )
        result = m.audit()
        self.assertEqual(_flagged(result), set())  # not unreviewed
        self.assertTrue(any(f.exemption for f in result.flags))


if __name__ == "__main__":
    unittest.main()
