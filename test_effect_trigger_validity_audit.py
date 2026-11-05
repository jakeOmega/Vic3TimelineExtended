"""Tests for effect_trigger_validity_audit (issue #146)."""

import contextlib
import io
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

    def test_scripted_gui_schema_clean_and_bogus_effect_flagged(self):
        # #305: common/scripted_guis/ is scanned, with the SGUI schema fields
        # (scripted_guis.md) valid and a dangling call in `effect` flagged.
        m = _Mod(
            {
                "common/scripted_guis/g.txt": "my_sgui = {\n"
                "\tscope = country\n\tsaved_scopes = { target }\n"
                "\tis_shown = { always = yes }\n\tis_valid = { always = yes }\n"
                "\tai_is_valid = { always = no }\n"
                "\teffect = { add_modifier = { name = x } }\n}\n"
                "my_bad_sgui = {\n\tscope = country\n"
                "\teffect = {\n\t\tbogus_helper = yes\n\t}\n}\n"
            }
        )
        self.assertEqual(
            _flagged(m.audit()), {("bogus_helper", "unresolved-helper-call")}
        )

    def test_customizable_localization_schema_not_flagged(self):
        # #305: custom-loc fields as vanilla uses them; `fallback = yes` and
        # `log_loc_errors = no` would otherwise read as helper calls.
        m = _Mod(
            {
                "common/customizable_localization/c.txt": "my_loc = {\n"
                "\ttype = country\n\tlog_loc_errors = no\n\trandom_valid = no\n"
                "\ttext = {\n\t\ttrigger = { always = yes }\n"
                "\t\tlocalization_key = my_loc_a\n\t}\n"
                "\ttext = {\n\t\tlocalization_key = my_loc_b\n\t\tfallback = yes\n\t}\n}\n"
                "my_child = {\n\tparent = my_loc\n\tsuffix = x\n}\n"
            }
        )
        self.assertEqual(_flagged(m.audit()), set())

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


class BootstrapCatalogTests(unittest.TestCase):
    """`bootstrap_catalog` must keep vanilla's callable helper names valid."""

    def test_vanilla_helper_defined_but_never_used_at_depth_is_in_the_catalog(self):
        # 1.14.5: `has_treaty_alliance_with` is defined in vanilla's
        # 00_diplomacy_triggers.txt and no vanilla script calls it at depth > 0,
        # so the LHS harvest alone drops it and mod calls flagged unresolved.
        game = tempfile.mkdtemp()
        mod = tempfile.mkdtemp()
        for rel, text in {
            "game/common/scripted_triggers/00_diplomacy_triggers.txt":
                "has_treaty_alliance_with = {\n\tis_at_war = no\n}\n",
            "game/common/script_values/x.txt": "some_vanilla_value = 5\n",
        }.items():
            p = os.path.join(game, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8-sig") as f:
                f.write(text)
        eva.bootstrap_catalog(game, mod)
        catalog = eva.load_catalog(mod)
        self.assertIn("has_treaty_alliance_with", catalog)
        self.assertIn("some_vanilla_value", catalog)


# --- #1142: effects in trigger context and the reverse ----------------------

# A union catalog for the context fixtures below, and the two context sets.
CTX_VALID = VALID | {
    "is_at_war", "save_scope_as", "save_temporary_scope_as", "has_modifier",
    "any_enemy_in_war", "is_subject_of", "has_variable", "set_variable",
    "custom_tooltip", "text", "every_country", "any_country", "random_country",
    "ai_chance", "base", "modifier", "option", "immediate", "trigger",
    "type", "else", "add_radicals", "strata", "gdp", "is_shown",
    "create_power_bloc", "cede_state_trigger", "should_be_pinned_by_default",
    "accept_effect", "will_propose_with_states", "will_select_as_first_state",
    "non_fulfillment", "conditions", "weekly", "owner", "ai_will_do", "exists",
    "ruler", "on_monthly_pulse", "random_list",
}
CTX_KEYS = {
    "effect_only": {"save_scope_as", "set_variable", "every_country",
                    "random_country", "add_modifier", "if", "else",
                    "trigger_event", "add_radicals"},
    "trigger_only": {"is_at_war", "has_modifier", "any_enemy_in_war",
                     "is_subject_of", "has_variable", "any_country"},
}

# decol_fighting_colonial_war as #1130 shipped it (colonial_empire_triggers.txt
# before 7d2df7ea8): `save_scope_as` is an effect, so the trigger parser
# dropped the line and every scope:decol_cw_metropole read failed.
BROKEN_DECOL_TRIGGER = """decol_fighting_colonial_war = {
\tis_at_war = yes
\tsave_scope_as = decol_cw_metropole
\tOR = {
\t\thas_modifier = colonial_crackdown_modifier
\t\tany_enemy_in_war = {
\t\t\tOR = {
\t\t\t\tAND = {
\t\t\t\t\tis_subject_of = scope:decol_cw_metropole
\t\t\t\t\tis_qualifying_colonial_subject = yes
\t\t\t\t}
\t\t\t\tvar:decol_iw_metropole ?= scope:decol_cw_metropole
\t\t\t}
\t\t}
\t}
}
"""
_QUALIFYING = "is_qualifying_colonial_subject = {\n\tis_at_war = yes\n}\n"


def _ctx_audit(files: dict[str, str]):
    return eva.audit(_Mod(files).root, valid_keys=CTX_VALID, context_keys=CTX_KEYS)


class EffectInTriggerTests(unittest.TestCase):
    def test_save_scope_as_in_scripted_trigger_flags(self):
        # The regression fixture: one flag, on the save_scope_as line.
        result = _ctx_audit({
            "common/scripted_triggers/colonial_empire_triggers.txt":
                _QUALIFYING + BROKEN_DECOL_TRIGGER,
        })
        flags = [f for f in result.flags if not f.exemption]
        self.assertEqual(
            [(f.keyword, f.kind, f.line) for f in flags],
            [("save_scope_as", "effect-in-trigger", 6)],
        )

    def test_save_temporary_scope_as_passes(self):
        fixed = BROKEN_DECOL_TRIGGER.replace(
            "save_scope_as =", "save_temporary_scope_as ="
        )
        result = _ctx_audit({
            "common/scripted_triggers/colonial_empire_triggers.txt":
                _QUALIFYING + fixed,
        })
        self.assertEqual(_flagged(result), set())

    def test_committed_catalog_rejects_save_scope_as_in_a_trigger(self):
        # Against the real committed catalogs: a re-bootstrap that lost
        # save_scope_as from [effect_only] would reopen #1142.
        here = os.path.dirname(os.path.abspath(__file__))
        mod = _Mod({
            "common/scripted_triggers/colonial_empire_triggers.txt":
                _QUALIFYING + BROKEN_DECOL_TRIGGER,
        })
        result = eva.audit(
            mod.root,
            valid_keys=eva.load_catalog(here),
            context_keys=eva.load_context_catalog(here),
        )
        self.assertEqual(
            {(f.keyword, f.kind) for f in result.flags},
            {("save_scope_as", "effect-in-trigger")},
        )

    def test_effect_in_event_limit_flags(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tif = {\n\t\t\tlimit = {\n"
            "\t\t\t\tset_variable = x\n\t\t\t}\n\t\t\tset_variable = y\n"
            "\t\t}\n\t}\n}\n"
        )})
        self.assertEqual(
            [(f.keyword, f.kind, f.line) for f in result.flags],
            [("set_variable", "effect-in-trigger", 5)],
        )

    def test_effect_in_event_immediate_passes(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tsave_scope_as = x\n"
            "\t\tevery_country = { set_variable = y }\n\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), set())

    def test_inline_limit_and_negation_on_one_line(self):
        # Context follows the braces within a line: the effect after the
        # limit closes is fine, the one inside NOT in the limit is not.
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n"
            "\t\tif = { limit = { NOT = { save_scope_as = x } } set_variable = y }\n"
            "\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), {("save_scope_as", "effect-in-trigger")})

    def test_trigger_iterator_body_and_effect_iterator(self):
        # Inside any_* the context stays trigger, so a random_* there flags.
        result = _ctx_audit({"common/scripted_triggers/t.txt": (
            "te_t = {\n\tany_country = {\n\t\trandom_country = { is_at_war = yes }\n"
            "\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), {("random_country", "effect-in-trigger")})

    def test_event_trigger_and_option_gate_are_trigger_context(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\ttype = country_event\n\ttrigger = { set_variable = a }\n"
            "\toption = {\n\t\tname = my.1.a\n\t\ttrigger = { has_variable = b }\n"
            "\t\tis_shown = { add_modifier = { name = c } }\n\t}\n}\n"
        )})
        self.assertEqual(
            _flagged(result),
            {("set_variable", "effect-in-trigger"),
             ("add_modifier", "effect-in-trigger")},
        )

    def test_custom_tooltip_takes_its_parents_context(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\ttrigger = {\n\t\tcustom_tooltip = { text = t has_variable = a }\n"
            "\t}\n\timmediate = {\n\t\tcustom_tooltip = { text = t set_variable = b }\n"
            "\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), set())

    def test_script_value_compared_in_a_trigger_is_neutral(self):
        # `x > { … }` is a script value: its `if` is math, not an effect.
        result = _ctx_audit({"common/scripted_triggers/t.txt": (
            "te_t = {\n\tgdp > {\n\t\tvalue = 5\n"
            "\t\tif = { limit = { is_at_war = yes } add = 1 }\n\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), set())

    def test_ai_weight_modifier_is_neutral(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\toption = {\n\t\tname = my.1.a\n"
            "\t\tai_chance = { base = 1 modifier = { trigger = { is_at_war = yes } add = 2 } }\n"
            "\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), set())

    def test_mod_scripted_effect_called_from_a_trigger_flags(self):
        result = _ctx_audit({
            "common/scripted_effects/s.txt": "te_do = {\n\tset_variable = x\n}\n",
            "common/scripted_triggers/t.txt": "te_check = {\n\tte_do = yes\n}\n",
        })
        self.assertEqual(_flagged(result), {("te_do", "effect-in-trigger")})

    def test_name_in_both_mod_databases_is_not_checked(self):
        result = _ctx_audit({
            "common/scripted_effects/s.txt": "te_both = {\n\tset_variable = x\n}\n",
            "common/scripted_triggers/t.txt": "te_both = {\n\tis_at_war = yes\n}\n"
            "te_check = {\n\tte_both = yes\n}\n",
        })
        self.assertEqual(_flagged(result), set())

    def test_journal_entry_complete_is_trigger_context(self):
        result = _ctx_audit({"common/journal_entries/j.txt": (
            "je_x = {\n\tcomplete = { set_variable = x }\n"
            "\ton_complete = { set_variable = y }\n}\n"
        )})
        self.assertEqual(
            [(f.keyword, f.line) for f in result.flags], [("set_variable", 2)]
        )

    def test_multiline_string_keys_are_not_read(self):
        # vanilla neighbor_events.txt: a trigger passed as a two-line string.
        # Its keys are text, not script, and its braces don't count.
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tte_helper = {\n"
            "\t\t\tCRITERIA = \"NOT = { has_variable = x }\n"
            "\t\t\tgdp > 5\"\n\t\t}\n\t\tif = { limit = { set_variable = y } }\n"
            "\t}\n}\n"
        ), "common/scripted_effects/s.txt": "te_helper = {\n\tsave_scope_as = z\n}\n"})
        self.assertEqual(
            [(f.keyword, f.kind, f.line) for f in result.flags],
            [("set_variable", "effect-in-trigger", 7)],
        )

    def test_hash_inside_a_string_is_not_a_comment(self):
        # `"#b …#!"` loc formatting: a `#` in a string must not cut the line,
        # or its closing quote reads as an open string that blanks the file.
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n"
            "\t\tcustom_tooltip = { text = \"#b Warning#!\" }  # REVIEWED 2026-10-26: x\n"
            "\t\tif = { limit = { set_variable = y } }\n\t}\n}\n"
        )})
        self.assertEqual(
            [(f.keyword, f.kind, f.line) for f in result.flags],
            [("set_variable", "effect-in-trigger", 4)],
        )

    def test_bare_trigger_in_an_option_weight_is_neutral(self):
        # A weight modifier inside an option holds bare triggers, not effects.
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\toption = {\n\t\tname = my.1.a\n"
            "\t\tai_chance = { base = 1 modifier = { is_at_war = yes add = 2 } }\n"
            "\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), set())

    def test_random_list_weight_modifier_is_neutral(self):
        # `modifier` alone: a random_list weight inside effect context.
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\trandom_list = {\n"
            "\t\t\t10 = { modifier = { is_at_war = yes add = 5 } set_variable = x }\n"
            "\t\t}\n\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), set())

    def test_trigger_suffix_block_in_an_effect_is_trigger_context(self):
        # decolonization.txt passes `cede_state_trigger = { … }` to an effect.
        result = _ctx_audit({"common/scripted_effects/s.txt": (
            "te_fx = {\n\tcreate_power_bloc = {\n"
            "\t\tcede_state_trigger = { has_variable = y }\n\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), set())

    def test_should_on_and_effect_suffix_blocks(self):
        result = _ctx_audit({
            "common/journal_entries/j.txt": "je_x = {\n"
            "\tshould_be_pinned_by_default = { set_variable = a }\n"
            "\ton_monthly_pulse = { has_variable = b }\n}\n",
            "common/diplomatic_actions/d.txt": "da_x = {\n"
            "\taccept_effect = { has_variable = c }\n}\n",
        })
        self.assertEqual(
            sorted((f.keyword, f.kind, os.path.basename(f.file), f.line)
                   for f in result.flags),
            [("has_variable", "trigger-in-effect", "d.txt", 2),
             ("has_variable", "trigger-in-effect", "j.txt", 3),
             ("set_variable", "effect-in-trigger", "j.txt", 2)],
        )

    def test_diplomatic_action_and_treaty_trigger_blocks(self):
        result = _ctx_audit({
            "common/diplomatic_actions/d.txt": "da_x = {\n"
            "\twill_propose_with_states = { set_variable = a }\n"
            "\twill_select_as_first_state = { set_variable = b }\n}\n",
            "common/treaty_articles/t.txt": "ta_x = {\n\tnon_fulfillment = {\n"
            "\t\tconditions = {\n\t\t\tweekly = { set_variable = c }\n"
            "\t\t}\n\t}\n}\n",
        })
        self.assertEqual(
            sorted((os.path.basename(f.file), f.line) for f in result.flags),
            [("d.txt", 2), ("d.txt", 3), ("t.txt", 4)],
        )

    def test_ai_will_do_holds_triggers(self):
        # Vanilla laws and character interactions: `ai_will_do = { exists =
        # ruler }`, bare triggers rather than a weight.
        result = _ctx_audit({"common/laws/l.txt": (
            "law_x = {\n\tai_will_do = { exists = ruler }\n}\n"
            "law_y = {\n\tai_will_do = { save_scope_as = z }\n}\n"
        )})
        self.assertEqual(
            [(f.keyword, f.kind, f.line) for f in result.flags],
            [("save_scope_as", "effect-in-trigger", 5)],
        )

    def test_block_opened_on_the_next_line(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tif = {\n\t\t\tlimit =\n"
            "\t\t\t{ set_variable = x }\n\t\t}\n\t}\n}\n"
        )})
        self.assertEqual(
            [(f.keyword, f.line) for f in result.flags], [("set_variable", 5)]
        )

    def test_guarded_scope_change_inherits(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\towner ?= { has_variable = a }\n"
            "\t\tif = { limit = { owner ?= { set_variable = b } } }\n\t}\n}\n"
        )})
        self.assertEqual(
            _flagged(result),
            {("has_variable", "trigger-in-effect"),
             ("set_variable", "effect-in-trigger")},
        )

    def test_reviewed_after_a_string_suppresses(self):
        # The comment starts after the string's closing quote, `#` inside it
        # included.
        result = _ctx_audit({"common/scripted_triggers/t.txt": (
            "te_t = {\n\tcustom_tooltip = { text = \"a#b\" save_scope_as = y }"
            "  # REVIEWED 2026-10-26: test\n}\n"
        )})
        self.assertEqual(_flagged(result), set())
        self.assertEqual(
            [(f.keyword, f.kind) for f in result.flags],
            [("save_scope_as", "effect-in-trigger")],
        )

    def test_commented_out_effect_after_a_string_in_a_limit(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tif = {\n"
            "\t\t\tlimit = { custom_tooltip = { text = \"t\" } } # save_scope_as = y\n"
            "\t\t}\n\t}\n}\n"
        )})
        self.assertEqual(result.flags, [])

    def test_run_on_string_continuation_is_text(self):
        # The continuation line's key and brace belong to the string.
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tte_helper = {\n"
            "\t\t\tCRITERIA = \"NOT = {\n"
            "\t\t\thas_variable = x }\"\n\t\t}\n"
            "\t\tif = { limit = { set_variable = y } }\n\t}\n}\n"
        ), "common/scripted_effects/s.txt": "te_helper = {\n\tsave_scope_as = z\n}\n"})
        self.assertEqual(
            [(f.keyword, f.kind, f.line) for f in result.flags],
            [("set_variable", "effect-in-trigger", 7)],
        )

    def test_reviewed_suppresses(self):
        result = _ctx_audit({"common/scripted_triggers/t.txt": (
            "te_t = {\n\tsave_scope_as = x  # REVIEWED 2026-10-26: test\n}\n"
        )})
        self.assertEqual(_flagged(result), set())
        self.assertEqual(
            [(f.keyword, f.kind) for f in result.flags],
            [("save_scope_as", "effect-in-trigger")],
        )


class TriggerInEffectTests(unittest.TestCase):
    def test_trigger_in_scripted_effect_body_flags(self):
        result = _ctx_audit({"common/scripted_effects/s.txt": (
            "te_fx = {\n\thas_variable = x\n\tif = { limit = { has_variable = x } }\n}\n"
        )})
        self.assertEqual(
            [(f.keyword, f.kind, f.line) for f in result.flags],
            [("has_variable", "trigger-in-effect", 2)],
        )

    def test_trigger_iterator_in_immediate_flags(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tany_country = { is_at_war = yes }\n\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), {("any_country", "trigger-in-effect")})

    def test_mod_scripted_trigger_called_from_an_effect_flags(self):
        result = _ctx_audit({
            "common/scripted_triggers/t.txt": "te_check = {\n\tis_at_war = yes\n}\n",
            "events/e.txt": "my.1 = {\n\toption = {\n\t\tname = my.1.a\n"
            "\t\tte_check = yes\n\t}\n}\n",
        })
        self.assertEqual(_flagged(result), {("te_check", "trigger-in-effect")})

    def test_effect_argument_not_in_trigger_only_passes(self):
        # `strata` is a trigger vanilla also passes to add_radicals, so the
        # bootstrap leaves it out of trigger_only; it must not flag.
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tadd_radicals = { value = 1 strata = lower }\n"
            "\t}\n}\n"
        )})
        self.assertEqual(_flagged(result), set())


class ModHelperOverlapTests(unittest.TestCase):
    def test_catalog_name_the_mod_defines_on_the_other_side_passes(self):
        # A mod scripted trigger named like a vanilla scripted effect (and the
        # reverse) is valid where the mod's own definition is read.
        keys = {"effect_only": {"v_shared_fx"}, "trigger_only": {"v_shared_tg"}}
        mod = _Mod({
            "common/scripted_triggers/t.txt": "v_shared_fx = {\n\tis_at_war = yes\n}\n"
            "te_check = {\n\tv_shared_fx = yes\n}\n",
            "common/scripted_effects/s.txt": "v_shared_tg = {\n\tset_variable = x\n}\n"
            "te_do = {\n\tv_shared_tg = yes\n}\n",
        })
        result = eva.audit(mod.root, valid_keys=CTX_VALID, context_keys=keys)
        self.assertEqual(_flagged(result), set())


class UnterminatedStringTests(unittest.TestCase):
    def test_file_ending_inside_a_string_flags_its_opening_line(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tcustom_tooltip = { text = \"t }\n"
            "\t\tif = { limit = { set_variable = y } }\n\t}\n}\n"
        )})
        self.assertEqual(
            [(f.keyword, f.kind, f.line) for f in result.flags],
            [("string to end of file", "unterminated-string", 3)],
        )

    def test_stray_quote_mid_file_flags_where_it_opens(self):
        # Two stray quotes: the file ends outside a string, but the first
        # "string" runs from line 3 to the next quote, on line 7.
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tcustom_tooltip = { text = \"t }\n"
            "\t\tsave_scope_as = a\n\t\tsave_scope_as = b\n"
            "\t\tsave_scope_as = c\n\t\tcustom_tooltip = { text = t\" }\n"
            "\t}\n}\n"
        )})
        self.assertEqual(
            [(f.keyword, f.kind, f.line) for f in result.flags],
            [("string over 5 lines", "unterminated-string", 3)],
        )

    def test_two_line_string_passes(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tte_helper = {\n"
            "\t\t\tCRITERIA = \"NOT = { has_variable = x }\n"
            "\t\t\tgdp > 5\"\n\t\t}\n\t}\n}\n"
        ), "common/scripted_effects/s.txt": "te_helper = {\n\tsave_scope_as = z\n}\n"})
        self.assertEqual(result.flags, [])

    def test_long_string_reviewed_on_its_closing_line(self):
        result = _ctx_audit({"events/e.txt": (
            "my.1 = {\n\timmediate = {\n\t\tte_helper = {\n"
            "\t\t\tCRITERIA = \"a\n\t\t\tb\n\t\t\tc\n"
            "\t\t\td\"  # REVIEWED 2026-10-26: a four-line criteria string\n"
            "\t\t}\n\t}\n}\n"
        ), "common/scripted_effects/s.txt": "te_helper = {\n\tsave_scope_as = z\n}\n"})
        self.assertEqual(_flagged(result), set())
        self.assertEqual(
            [(f.kind, f.line) for f in result.flags], [("unterminated-string", 4)]
        )


class StrictExitTests(unittest.TestCase):
    def _mod(self, event_body: str) -> str:
        mod = _Mod({
            "events/e.txt": "my.1 = {\n" + event_body + "}\n",
            "docs/engine/effect_trigger_valid_keys.txt":
                "\n".join(sorted(CTX_VALID)) + "\n",
            "docs/engine/effect_trigger_context_keys.txt":
                "[effect_only]\nset_variable\n[trigger_only]\nhas_variable\n",
        })
        return mod.root

    def test_strict_fails_on_an_unreviewed_flag(self):
        root = self._mod("\ttrigger = { set_variable = x }\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(eva.main(["--strict"], mod_path=root), 1)
            self.assertEqual(eva.main([], mod_path=root), 0)

    def test_strict_passes_a_clean_tree(self):
        root = self._mod("\timmediate = { set_variable = x }\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(eva.main(["--strict"], mod_path=root), 0)


class ContextCatalogTests(unittest.TestCase):
    def test_bootstrap_and_load(self):
        game = tempfile.mkdtemp()
        docs = tempfile.mkdtemp()
        mod = tempfile.mkdtemp()
        with open(os.path.join(docs, "effects.log"), "w", encoding="utf-8") as f:
            f.write("# Effect Documentation\n## save_scope_as\nx\n## set_variable\n"
                    "## custom_tooltip\n## add_radicals\n")
        with open(os.path.join(docs, "triggers.log"), "w", encoding="utf-8") as f:
            f.write("# Trigger Documentation\n## has_variable\n## custom_tooltip\n"
                    "## strata\n")
        for rel, text in {
            # `strata` as an effect argument: vanilla uses it in effect context.
            "game/events/e.txt": "v.1 = {\n\timmediate = {\n"
                "\t\tadd_radicals = { value = 1 strata = lower }\n\t}\n}\n",
            "game/common/scripted_effects/x.txt": "v_fx = {\n\tset_variable = a\n}\n",
            "game/common/scripted_triggers/y.txt": "v_tg = {\n\thas_variable = a\n}\n",
        }.items():
            p = os.path.join(game, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8-sig") as f:
                f.write(text)
        info = eva.bootstrap_context_catalog(game, mod, docs)
        cat = eva.load_context_catalog(mod)
        self.assertEqual(cat["effect_only"],
                         {"save_scope_as", "set_variable", "add_radicals", "v_fx"})
        self.assertEqual(cat["trigger_only"], {"has_variable", "v_tg"})
        self.assertEqual(info["dropped_as_used_by_vanilla"]["trigger_only"], ["strata"])

    def test_missing_catalog_loads_empty(self):
        cat = eva.load_context_catalog(tempfile.mkdtemp())
        self.assertEqual(cat, {"effect_only": set(), "trigger_only": set()})


class SuppressionTests(unittest.TestCase):
    def test_reviewed_partitions_flag(self):
        m = _Mod(
            {"events/e.txt": "my.1 = {\n\tbogus_effect = 1  # REVIEWED 2026-05-24: intentional\n}\n"}
        )
        result = m.audit()
        self.assertEqual(_flagged(result), set())  # not unreviewed
        self.assertTrue(any(f.exemption for f in result.flags))


class RenderReportTests(unittest.TestCase):
    def test_report_carries_no_volatile_numbers(self):
        """A reviewed entry prints no line number and the summary no scan
        counts (the frozen catalog size stays), so the report changes only when
        the findings do."""
        result = eva.AuditResult(
            flags=[
                eva.Flag("/mod/events/e.txt", 5, "bogus_effect", "unknown-name", "bogus_effect = 1"),
                eva.Flag("/mod/common/diplomatic_actions/a.txt", 128, "decline_effect",
                         "unresolved-helper-call", "decline_effect = { }",
                         exemption={"date": "2026-09-18", "rationale": "action field"}),
            ],
            coverage={"files_scanned": 262, "roots_scanned": 16, "keys_checked": 109392,
                      "catalog_size": 7145, "effect_only_catalog_size": 3657,
                      "trigger_only_catalog_size": 2595, "mod_defined_names": 2650,
                      "flags": 2},
        )
        report = eva.render_report(result, "/mod")
        self.assertIn(
            "- `decline_effect` (unresolved-helper-call) — common/diplomatic_actions/a.txt "
            "(REVIEWED 2026-09-18: action field)", report)
        self.assertNotIn("a.txt:128", report)
        self.assertIn("— events/e.txt:5 —", report)  # unreviewed keeps its line
        self.assertIn("- Catalog size: **7145**\n", report)
        self.assertIn(
            "- Context catalog: **3657** effect-only, **2595** trigger-only names\n",
            report,
        )
        for gone in ("Roots scanned", "files scanned", "keys checked", "mod-defined names",
                     "109392", "2650"):
            self.assertNotIn(gone, report)


if __name__ == "__main__":
    unittest.main()
