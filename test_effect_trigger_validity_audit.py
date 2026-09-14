"""Tests for effect_trigger_validity_audit (issue #146)."""

import os
import tempfile
import unittest

import effect_trigger_validity_audit as eva

# A minimal "known-good" catalog for the synthetic mods below.
VALID = {"add_modifier", "name", "multiplier", "if", "limit", "value",
         "trigger_event", "id", "add", "subtract", "is_war_participant",
         "effect", "group", "progressiveness", "country_prestige_mult"}


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
        m = _Mod(
            {
                "common/scripted_effects/s.txt": "te_foo = {\n\tadd_modifier = { name = $GOOD$ }\n}\n"
                "se = {\n\tte_foo = { GOOD = wood }\n}\n"
            }
        )
        flags = _flagged(m.audit())
        self.assertEqual(flags, set())
        self.assertNotIn("GOOD", {kw for kw, _ in flags})

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


class ScanRootScopingTests(unittest.TestCase):
    """Entity dirs are scanned only inside their trigger/effect blocks (#295)."""

    def test_dead_trigger_in_diplomatic_action_flagged(self):
        # The #295 motivating bug: 1.14 removed `has_war_exhaustion`, but the
        # copy in `diplomatic_actions/nuke.txt`'s `will_propose` was invisible
        # to the audit because the directory wasn't scanned at all.
        m = _Mod(
            {
                "common/diplomatic_actions/nuke.txt": "nuke_action = {\n"
                "\tai = {\n\t\twill_propose = {\n"
                "\t\t\thas_war_exhaustion = yes\n\t\t}\n\t}\n}\n"
            }
        )
        self.assertIn(("has_war_exhaustion", "unknown-name"), _flagged(m.audit()))

    def test_entity_schema_and_modifier_blocks_not_scanned(self):
        # A law's own schema (`progressiveness`, `group`) and its modifier block
        # are different namespaces — flagging them would drown the report.
        m = _Mod(
            {
                "common/laws/l.txt": "law_x = {\n\tgroup = lawgroup_y\n"
                "\tprogressiveness = 5\n"
                "\tmodifier = {\n\t\tcountry_prestige_mult = 0.1\n\t}\n}\n"
            }
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_effect_inside_entity_entry_block_scanned(self):
        m = _Mod(
            {
                "common/laws/l.txt": "law_x = {\n\ton_enact = {\n"
                "\t\tbogus_effect = yes\n\t}\n}\n"
            }
        )
        self.assertIn(("bogus_effect", "unknown-name"), _flagged(m.audit()))

    def test_single_line_entry_block_scanned_without_flagging_opener(self):
        m = _Mod(
            {"common/decisions/d.txt": "dec = {\n\tpossible = { bogus_trigger = yes }\n}\n"}
        )
        flags = _flagged(m.audit())
        self.assertIn(("bogus_trigger", "unknown-name"), flags)
        self.assertNotIn(("possible", "unknown-name"), flags)

    def test_block_after_entry_block_closes_is_not_scanned(self):
        # `modifier` follows a scanned `on_enact`; the depth tracking must have
        # left the entry block again by then.
        m = _Mod(
            {
                "common/laws/l.txt": "law_x = {\n\ton_enact = {\n\t\tadd_modifier = { name = x }\n\t}\n"
                "\tmodifier = {\n\t\tcountry_prestige_mult = 0.1\n\t}\n}\n"
            }
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_root_extra_valid_key_not_flagged(self):
        # `header` is schema of a JE's scanned `event_outcome_*_effect_desc`.
        m = _Mod(
            {
                "common/journal_entries/je.txt": "je_x = {\n"
                "\tevent_outcome_completed_effect_desc = {\n\t\theader = je_x_header\n"
                "\t\teffect = { add_modifier = { name = x } }\n\t}\n}\n"
            }
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_root_extra_valid_key_is_root_scoped(self):
        # ... and stays invalid in a root that didn't declare it.
        m = _Mod({"events/e.txt": "my.1 = {\n\theader = x\n}\n"})
        self.assertIn(("header", "unknown-name"), _flagged(m.audit()))

    def test_script_values_body_scanned(self):
        m = _Mod({"common/script_values/v.txt": "sv_x = {\n\tvalue = 1\n\tbogus_op = 2\n}\n"})
        self.assertIn(("bogus_op", "unknown-name"), _flagged(m.audit()))


class NameHarvestDepthTests(unittest.TestCase):
    def test_constant_script_value_name_harvested(self):
        # `name = 25` (no braces) defines a script value just as `name = { }` does.
        m = _Mod(
            {
                "common/script_values/v.txt": "te_cap = 25\n",
                "events/e.txt": "my.1 = {\n\tif = { limit = { te_cap = 0 } }\n}\n",
            }
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_nested_key_not_harvested_as_mod_name(self):
        # A nested block opener must not whitelist itself: harvesting at any
        # indentation used to mask unknown effects that happen to open a block.
        m = _Mod({"common/scripted_effects/s.txt": "se = {\n\tbogus_effect = {\n\t\tid = 1\n\t}\n}\n"})
        self.assertIn(("bogus_effect", "unknown-name"), _flagged(m.audit()))


class EventTargetTests(unittest.TestCase):
    def test_event_target_scope_not_flagged(self):
        # Scope transitions live in docs/engine/event_targets_summary.txt, not
        # in the frozen catalog (vanilla's effect corpus doesn't use them all).
        files = {
            "docs/engine/event_targets_summary.txt": "# header\nmarket|trade_center|state|Scope to the trade center state\n",
            "common/script_values/v.txt": "sv_x = {\n\tvalue = 0\n\ttrade_center = {\n\t\tadd = 1\n\t}\n}\n",
        }
        m = _Mod(files)
        self.assertEqual(_flagged(m.audit()), set())

    def test_event_target_absent_when_summary_missing(self):
        m = _Mod({"common/script_values/v.txt": "sv_x = {\n\ttrade_center = {\n\t\tadd = 1\n\t}\n}\n"})
        self.assertIn(("trade_center", "unknown-name"), _flagged(m.audit()))


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
