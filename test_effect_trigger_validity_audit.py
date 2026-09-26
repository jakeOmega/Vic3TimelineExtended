"""Tests for effect_trigger_validity_audit (issue #146)."""

import os
import tempfile
import unittest

import effect_trigger_validity_audit as eva

# A minimal "known-good" catalog for the synthetic mods below.
VALID = {"add_modifier", "name", "multiplier", "if", "limit", "value",
         "trigger_event", "id", "add", "subtract", "is_war_participant",
         # Present in the real bootstrapped catalog (vanilla uses them in
         # on_actions / scripted helpers); needed by the SCAN_ROOTS cases.
         "always", "effect"}


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

    def test_vanilla_pact_keys_not_flagged(self):
        # Vanilla pact vocabulary (common/diplomatic_actions/diplomatic_action.md,
        # 34_subjects_exempt_from_service.txt) is valid in call form (#456).
        m = _Mod({"common/diplomatic_actions/d.txt":
                  "my_action = {\n\tpact = {\n\t\tforced_duration = 12\n"
                  "\t\tactor_can_break = { always = yes }\n"
                  "\t\ttarget_can_break = { always = no }\n\t}\n}\n"})
        flagged = {k for k, _ in _flagged(m.audit())}
        self.assertFalse(flagged & {"actor_can_break", "target_can_break", "forced_duration"}, flagged)

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
                "common/scripted_effects/s.txt": "te_foo = {\n\tvalue = 1\n}\n"
                "se = {\n\tte_foo = { GOOD = wood }\n}\n"
            }
        )
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


class ScanRootTests(unittest.TestCase):
    """#288 / #295 — the audit reaches beyond the original four directories."""

    def test_dangling_helper_call_in_scripted_buttons_flagged(self):
        # #288: `covert_op_refresh_all_targets` was deleted but two call sites
        # in common/scripted_buttons/ survived; POST /reload came back clean.
        m = _Mod(
            {
                "common/scripted_buttons/b.txt": "cw_button = {\n"
                "\tvisible = { always = yes }\n"
                "\teffect = {\n\t\tcovert_op_refresh_all_targets = yes\n\t}\n}\n"
            }
        )
        self.assertIn(
            ("covert_op_refresh_all_targets", "unresolved-helper-call"),
            _flagged(m.audit()),
        )

    def test_removed_trigger_in_diplomatic_actions_flagged(self):
        # #295: 1.14 removed has_war_exhaustion; nuke.txt's will_propose kept it.
        m = _Mod(
            {
                "common/diplomatic_actions/nuke.txt": "alliance_nuke = {\n"
                "\trequires_approval = yes\n"
                "\twill_propose = {\n\t\thas_war_exhaustion = { value > 0.5 }\n\t}\n}\n"
            }
        )
        self.assertIn(
            ("has_war_exhaustion", "unresolved-helper-call"), _flagged(m.audit())
        )

    def test_entity_schema_fields_not_flagged(self):
        m = _Mod(
            {
                "common/journal_entries/je.txt": "je_x = {\n"
                "\tgroup = je_group_x\n"
                "\tis_shown_in_lobby = { is_war_participant = yes }\n"
                "\tpossible = { is_war_participant = yes }\n"
                "\tstatus_desc = je_x_status\n}\n",
                "common/scripted_buttons/b.txt": "b_x = {\n"
                "\tvisible = { always = yes }\n\tpossible = { always = yes }\n}\n",
            }
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_static_modifier_block_body_skipped(self):
        # Modifier names belong to modifier_visibility_audit, not to this one.
        m = _Mod(
            {
                "common/laws/l.txt": "law_x = {\n\tgroup = lawgroup_x\n"
                "\tmodifier = {\n\t\tcountry_authority_add = 150\n\t}\n}\n"
            }
        )
        self.assertEqual(_flagged(m.audit()), set())

    def test_add_modifier_body_still_checked(self):
        # add_modifier is an *effect*, not a static-modifier container — its body
        # must keep being validated even inside a skip_blocks root.
        m = _Mod(
            {
                "common/laws/l.txt": "law_x = {\n\ton_enact = {\n"
                "\t\tadd_modifier = { name = x bogus_effect = 1 }\n\t}\n}\n"
            }
        )
        self.assertIn(("bogus_effect", "unknown-name"), _flagged(m.audit()))

    def test_entity_name_not_globally_valid(self):
        # A journal entry id is a definition, not a callable keyword: calling it
        # from an event must still flag (this is what the depth-0 rule buys).
        m = _Mod(
            {
                "common/journal_entries/je.txt": "je_x = {\n\tgroup = je_group_x\n}\n",
                "events/e.txt": "my.1 = {\n\tje_x = yes\n}\n",
            }
        )
        self.assertIn(("je_x", "unresolved-helper-call"), _flagged(m.audit()))

    def test_scalar_script_value_name_harvested(self):
        # Bare `name = <number>` script values are definitions too, and are
        # callable by name from anywhere.
        m = _Mod(
            {
                "common/script_values/v.txt": "te_cap = 7\n",
                "events/e.txt": "my.1 = {\n\tif = { limit = { te_cap = 7 } }\n}\n",
            }
        )
        self.assertEqual(_flagged(m.audit()), set())


class UnresolvedHelperCallTests(unittest.TestCase):
    def test_returns_call_sites_with_missing_callee(self):
        m = _Mod(
            {
                "common/scripted_buttons/b.txt": "b_x = {\n\teffect = {\n"
                "\t\tgone_helper = yes\n\t}\n}\n"
            }
        )
        rows = eva.unresolved_helper_calls(m.root, m.audit())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "gone_helper")
        self.assertEqual(
            rows[0]["file"], os.path.join("common", "scripted_buttons", "b.txt")
        )
        self.assertEqual(rows[0]["line"], 3)
        self.assertEqual(rows[0]["kind"], "effect_call")

    def test_non_call_form_is_not_a_helper_call(self):
        m = _Mod({"events/e.txt": "my.1 = {\n\tadd_authority = -200\n}\n"})
        self.assertEqual(eva.unresolved_helper_calls(m.root, m.audit()), [])


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
