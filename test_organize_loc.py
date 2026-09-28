"""Tests for organize_loc's unused-key detection."""

import contextlib
import io
import os
import tempfile
import unittest

from organize_loc import (
    categorize_key, find_diplo_action_keys, find_parameterized_keys,
    find_quoted_loc_args, find_treaty_article_keys, find_war_goal_keys,
    organize_all, treaty_article_families,
)


class FindQuotedLocArgsTests(unittest.TestCase):
    def test_select_localization_branches(self):
        value = (
            "\"$hist_date$\\n[SelectLocalization( ScriptContainer.HasVariable('v_share'), "
            "'hist_share_row', 'hist_share_none' )]\""
        )
        self.assertEqual(
            find_quoted_loc_args(value), ["v_share", "hist_share_row", "hist_share_none"]
        )

    def test_nested_brackets(self):
        value = (
            "\"[AddLocalizationIf(THIS.GetCountry.Exists, THIS.GetCountry.GetName)]"
            "[AddLocalizationIf(Not(THIS.GetCountry.Exists), 'rivals_entry_gone')]\""
        )
        self.assertEqual(find_quoted_loc_args(value), ["rivals_entry_gone"])

    def test_prose_quotes_outside_brackets_ignored(self):
        value = "\"'How long, then?' The 'first' power [GetPlayer.GetName] claims it.\""
        self.assertEqual(find_quoted_loc_args(value), [])

    def test_prose_between_expressions_ignored(self):
        value = "\"[Localize('key_one')]'s rival, the 'x' of [Localize('key_two')]\""
        self.assertEqual(find_quoted_loc_args(value), ["key_one", "key_two"])


class CategorizeKeyTests(unittest.TestCase):
    def test_homeland_panel_family_stays_together(self):
        for key in ("TE_HOMELAND_CREATION", "TE_HOMELAND_REMOVAL",
                    "TE_HOMELAND_PAUSED_LOCKED", "TE_HOMELAND_CREATION_THRESHOLD"):
            with self.subTest(key=key):
                self.assertEqual(categorize_key(key, set()), "MISCELLANEOUS")

    def test_resettlement_families_stay_together(self):
        for key in ("resettlement_arrivals", "resettlement_arrivals_desc",
                    "resettlement_special_settlements_politics", "resettlement_special_settlements_politics_desc",
                    "resettlement_declaration_pm_line", "resettlement_possible_open_frontier_tt"):
            with self.subTest(key=key):
                self.assertEqual(categorize_key(key, set()), "MISCELLANEOUS")

    def test_collective_governance_families_stay_together(self):
        # A government type or amendment name and its _desc must land in the
        # same file. Four-token bases would otherwise split: the name to
        # MISCELLANEOUS, the _desc to CONCEPTS.
        for key in (
            "gov_collective_noble_commonwealth",
            "gov_collective_noble_commonwealth_desc",
            "gov_collective_governance",
            "gov_collective_governance_desc",
            "gov_direct_democracy_single_party_state",
            "gov_direct_democracy_single_party_state_desc",
            "amendment_collective_direct_democracy",
            "amendment_collective_direct_democracy_desc",
        ):
            with self.subTest(key=key):
                self.assertEqual(categorize_key(key, set()), "CONCEPTS")


class OrganizeAllUnusedTests(unittest.TestCase):
    def test_quoted_argument_keeps_key_out_of_unused(self):
        loc = (
            "l_english:\n"
            " widget_root:0 \"[SelectLocalization( X.HasVariable('v'), 'widget_row', 'widget_row_none' )]\"\n"
            " widget_row:0 \"row\"\n"
            " widget_row_none:0 \"none\"\n"
            " widget_prose:0 \"never referenced\"\n"
            " widget_dead:0 \"'widget_prose' is only quoted in prose here\"\n"
        )
        with tempfile.TemporaryDirectory() as td:
            loc_dir = os.path.join(td, "localization", "english")
            os.makedirs(loc_dir)
            with open(os.path.join(loc_dir, "x_l_english.yml"), "w", encoding="utf-8-sig") as fh:
                fh.write(loc)
            os.makedirs(os.path.join(td, "common", "scripted_guis"))
            with open(os.path.join(td, "common", "scripted_guis", "w.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write("widget_sgui = { tooltip = widget_root }\n")
            with contextlib.redirect_stdout(io.StringIO()):
                organize_all(td)
            unused_path = os.path.join(loc_dir, "te_unused_l_english.yml")
            with open(unused_path, encoding="utf-8-sig") as fh:
                unused = fh.read()
        self.assertNotIn(" widget_row:", unused)
        self.assertNotIn(" widget_row_none:", unused)
        self.assertNotIn(" widget_root:", unused)
        self.assertIn(" widget_prose:", unused)
        self.assertIn(" widget_dead:", unused)

    def test_embedded_tooltip_keeps_key_out_of_unused(self):
        loc = (
            "l_english:\n"
            " widget_root:0 \"needs #tooltippable #tooltip:[State.GetTooltipTag],widget_tt #v 60%#!#!#!\"\n"
            " widget_tt:0 \"breakdown [SelectLocalization( X.HasVariable('v'), 'widget_note', '' )]\"\n"
            " widget_note:0 \"note\"\n"
            " widget_bare:0 \"#tooltip:widget_bare_tt text#!\"\n"
            " widget_bare_tt:0 \"bare\"\n"
            " widget_dead:0 \"never referenced\"\n"
        )
        with tempfile.TemporaryDirectory() as td:
            loc_dir = os.path.join(td, "localization", "english")
            os.makedirs(loc_dir)
            with open(os.path.join(loc_dir, "x_l_english.yml"), "w", encoding="utf-8-sig") as fh:
                fh.write(loc)
            os.makedirs(os.path.join(td, "gui"))
            with open(os.path.join(td, "gui", "w.gui"), "w", encoding="utf-8-sig") as fh:
                fh.write('textbox = { text = "widget_root" }\ntextbox = { text = "widget_bare" }\n')
            with contextlib.redirect_stdout(io.StringIO()):
                organize_all(td)
            with open(os.path.join(loc_dir, "te_unused_l_english.yml"), encoding="utf-8-sig") as fh:
                unused = fh.read()
        for key in ("widget_root", "widget_tt", "widget_note", "widget_bare_tt"):
            self.assertNotIn(f" {key}:", unused)
        self.assertIn(" widget_dead:", unused)

    def test_dotted_splice_keeps_key_out_of_unused(self):
        # `\w+` excludes `.` and `-`, so a splice of a key containing either,
        # such as `$ev.1.common_tt$` or `$tech_e-x_name|V$`, used to die at
        # the first `.`/`-` and never count as a reference.
        loc = (
            "l_english:\n"
            " ev.1.a.tt:0 \"option text\\n\\n$ev.1.common_tt$\"\n"
            " ev.1.common_tt:0 \"shared\"\n"
            " widget_root:0 \"$tech_e-x_name|V$\"\n"
            " tech_e-x_name:0 \"hyphenated\"\n"
            " ev.1.dead:0 \"never referenced\"\n"
        )
        with tempfile.TemporaryDirectory() as td:
            loc_dir = os.path.join(td, "localization", "english")
            os.makedirs(loc_dir)
            with open(os.path.join(loc_dir, "x_l_english.yml"), "w", encoding="utf-8-sig") as fh:
                fh.write(loc)
            os.makedirs(os.path.join(td, "events"))
            with open(os.path.join(td, "events", "e.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write("ev.1 = { option = { custom_tooltip = ev.1.a.tt } }\n")
            os.makedirs(os.path.join(td, "gui"))
            with open(os.path.join(td, "gui", "w.gui"), "w", encoding="utf-8-sig") as fh:
                fh.write('textbox = { text = "widget_root" }\n')
            with contextlib.redirect_stdout(io.StringIO()):
                organize_all(td)
            with open(os.path.join(loc_dir, "te_unused_l_english.yml"), encoding="utf-8-sig") as fh:
                unused = fh.read()
        for key in ("ev.1.a.tt", "ev.1.common_tt", "widget_root", "tech_e-x_name"):
            self.assertNotIn(f" {key}:", unused)
        self.assertIn(" ev.1.dead:", unused)

    def test_replace_override_value_keeps_key_out_of_unused(self):
        # replace/ holds overrides of vanilla keys and is never organised, but
        # an override's value can name mod keys: the era building names make
        # building_art_academy a SelectLocalization over two mod keys.
        replace = (
            "l_english:\n"
            " building_x:0 \"[SelectLocalization(GetPlayer.IsValid, 'building_x_name_player', 'building_x_name_early')]\"\n"
            " building_y:0 \"$building_y_name$ Works\"\n"
        )
        loc = (
            "l_english:\n"
            " building_x_name_player:0 \"[GetPlayer.GetCustom('x_name')]\"\n"
            " building_x_name_early:0 \"Early\"\n"
            " building_y_name:0 \"Old\"\n"
            " building_x_dead:0 \"never referenced\"\n"
        )
        with tempfile.TemporaryDirectory() as td:
            loc_dir = os.path.join(td, "localization", "english")
            os.makedirs(os.path.join(loc_dir, "replace"))
            replace_path = os.path.join(loc_dir, "replace", "o_l_english.yml")
            with open(replace_path, "w", encoding="utf-8-sig") as fh:
                fh.write(replace)
            with open(os.path.join(loc_dir, "x_l_english.yml"), "w", encoding="utf-8-sig") as fh:
                fh.write(loc)
            with contextlib.redirect_stdout(io.StringIO()):
                organize_all(td)
            with open(os.path.join(loc_dir, "te_unused_l_english.yml"), encoding="utf-8-sig") as fh:
                unused = fh.read()
            with open(replace_path, encoding="utf-8-sig") as fh:
                replace_after = fh.read()
        for key in ("building_x_name_player", "building_x_name_early", "building_y_name"):
            self.assertNotIn(f" {key}:", unused)
        self.assertIn(" building_x_dead:", unused)
        self.assertEqual(replace_after, replace)


class CategorizeInstitutionKeysTests(unittest.TestCase):
    def test_breakdown_labels_file_with_their_institution(self):
        # 5+ tokens, so without the rule these fall through to MISCELLANEOUS.
        for key in (
            "INSTITUTION_FUNDING_LEVEL_ministry_of_foreign_affairs",
            "NO_INSTITUTION_ministry_of_foreign_affairs",
            "institution_ministry_of_foreign_affairs_desc",
        ):
            self.assertEqual(categorize_key(key, set()), "INSTITUTIONS", key)


class FindDiploActionKeysTests(unittest.TestCase):
    def test_third_party_and_directed_autokeys_are_used(self):
        # The engine renders these off the action name with no script
        # reference; missing them exiled live keys to te_unused.
        with tempfile.TemporaryDirectory() as td:
            da_dir = os.path.join(td, "common", "diplomatic_actions")
            os.makedirs(da_dir)
            with open(os.path.join(da_dir, "a.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write("my_action = {\n\tshould_notify_third_parties = yes\n}\n")
            keys = find_diplo_action_keys(td)
        for suffix in (
            "", "_action_notification_name",
            "_action_notification_third_party_name",
            "_action_notification_third_party_desc",
            "_action_notification_third_party_break_desc",
            "_proposal_third_party_accepted_desc",
            "_effect_desc_first", "_effect_desc_third", "_effect_desc_global",
        ):
            self.assertIn(f"my_action{suffix}", keys)


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write(text)


class FindParameterizedKeysTests(unittest.TestCase):
    def _project(self, td):
        _write(td, "common/scripted_effects/e.txt", (
            "my_step = {\n"
            "\tcustom_tooltip = {\n"
            "\t\ttext = my_tt_$VAR$_$OP$\n"
            "\t\tchange_variable = { name = $VAR$ $OP$ = 1 }\n"
            "\t}\n"
            "\t# text = my_tt_$VAR$_commented\n"
            "}\n"
            "# Passes its own parameter on to my_step.\n"
            "my_wrapper = { my_step = { VAR = $V$ OP = add } }\n"
            "other = { add_modifier = { name = other_$VAR$ } }\n"
        ))
        # The call sites live in a file with no `$` of its own.
        _write(td, "common/scripted_guis/g.txt", (
            "g = {\n"
            "\teffect = { my_step = { VAR = alpha OP = subtract } }\n"
            "\teffect = { my_wrapper = { V = beta } }\n"
            "\teffect = { other = { VAR = gamma } }\n"
            "}\n"
        ))

    def test_expands_templates_with_their_callers_values(self):
        keys = {
            "my_tt_alpha_subtract", "my_tt_beta_add", "other_gamma",
            # alpha is only ever passed to my_step, never to other.
            "other_alpha",
            "my_tt_alpha_commented", "unrelated",
        }
        with tempfile.TemporaryDirectory() as td:
            self._project(td)
            found = find_parameterized_keys(td, keys)
        self.assertIn("my_tt_alpha_subtract", found)
        self.assertIn("my_tt_beta_add", found)  # through the wrapper's $V$
        self.assertIn("other_gamma", found)
        self.assertNotIn("other_alpha", found)
        self.assertNotIn("my_tt_alpha_commented", found)
        self.assertNotIn("unrelated", found)

    def test_parameter_cycle_terminates(self):
        # cyc_a passes $X$ to cyc_b and cyc_b passes it straight back. The
        # `seen` guard in values_for is all that stops this recursing forever,
        # which on the server would hang every POST /reload.
        with tempfile.TemporaryDirectory() as td:
            _write(td, "common/scripted_effects/c.txt", (
                "cyc_a = {\n"
                "\tcustom_tooltip = { text = cyc_tt_$X$ }\n"
                "\tcyc_b = { X = $X$ }\n"
                "}\n"
                "cyc_b = {\n"
                "\tcustom_tooltip = { text = cyc_b_tt_$X$ }\n"
                "\tcyc_a = { X = $X$ }\n"
                "}\n"
            ))
            _write(td, "events/e.txt", "e.1 = { immediate = { cyc_a = { X = one } } }\n")
            found = find_parameterized_keys(
                td, {"cyc_tt_one", "cyc_tt_two", "cyc_b_tt_one", "cyc_b_tt_two"}
            )
        # cyc_b only hears `one` through cyc_a, across the cut cycle: a result
        # computed with the cycle cut short must not be remembered as final.
        self.assertEqual(found, {"cyc_tt_one", "cyc_b_tt_one"})

    def test_organize_all_keeps_parameterized_keys_out_of_unused(self):
        loc = (
            "l_english:\n"
            " my_tt_alpha_subtract:0 \"down\"\n"
            " other_alpha:0 \"never reached\"\n"
        )
        with tempfile.TemporaryDirectory() as td:
            self._project(td)
            _write(td, "localization/english/x_l_english.yml", loc)
            with contextlib.redirect_stdout(io.StringIO()):
                organize_all(td)
            with open(os.path.join(td, "localization", "english", "te_unused_l_english.yml"),
                      encoding="utf-8-sig") as fh:
                unused = fh.read()
        self.assertNotIn(" my_tt_alpha_subtract:", unused)
        self.assertIn(" other_alpha:", unused)


class FindTreatyArticleKeysTests(unittest.TestCase):
    """#357: a treaty article's engine-built keys are used, and file together."""

    _ARTICLE = (
        "lender_of_last_resort = {\n\tkind = directed\n"
        "\tcan_ratify = {\n\t\talways = yes\n\t}\n"
        "\tarticle_ai_usage = { offer request }\n}\n"
    )

    def test_engine_built_suite_is_used(self):
        with tempfile.TemporaryDirectory() as td:
            _write(td, "common/treaty_articles/a.txt", self._ARTICLE)
            keys = find_treaty_article_keys(td)
        for suffix in ("", "_desc", "_effects_desc", "_article_short_desc"):
            self.assertIn(f"lender_of_last_resort{suffix}", keys)
        # Only top-level names start a family, not nested blocks.
        self.assertNotIn("can_ratify_desc", keys)
        self.assertNotIn("article_ai_usage_desc", keys)

    def test_family_files_with_its_desc(self):
        # The bare names used to fall to MISCELLANEOUS (four tokens; a digit)
        # while their _desc keys went to CONCEPTS. Articles whose _desc files
        # elsewhere (the pact rule) keep their whole family there.
        with tempfile.TemporaryDirectory() as td:
            _write(td, "common/treaty_articles/a.txt", (
                self._ARTICLE + "science_aid_2 = {\n\tkind = directed\n}\n"
                "intelligence_sharing_pact = {\n\tkind = mutual\n}\n"
            ))
            article_of = treaty_article_families(td)
        for article, cat in (("lender_of_last_resort", "CONCEPTS"),
                             ("science_aid_2", "CONCEPTS"),
                             ("intelligence_sharing_pact", "DIPLOMACY")):
            for suffix in ("", "_desc", "_effects_desc", "_article_short_desc"):
                with self.subTest(key=article + suffix):
                    self.assertEqual(
                        categorize_key(article + suffix, set(), article_of), cat
                    )


class FindWarGoalKeysTests(unittest.TestCase):
    def test_engine_implicit_suite(self):
        with tempfile.TemporaryDirectory() as td:
            _write(td, "common/war_goal_types/w.txt", "te_my_goal = {\n\tkind = annex_country\n}\n")
            keys = find_war_goal_keys(td)
        for suffix in ("", "_desc", "_sway_desc", "_type_name", "_type_desc"):
            self.assertIn(f"war_goal_te_my_goal{suffix}", keys)

    def test_families_file_together(self):
        for key in ("war_goal_te_reunify_country", "war_goal_te_reunify_country_desc",
                    "war_goal_te_reunify_country_type_name",
                    "nd_tt_nd_hardening_add", "nd_tt_nd_hardening_subtract"):
            with self.subTest(key=key):
                self.assertEqual(categorize_key(key, set()), "MISCELLANEOUS")


if __name__ == "__main__":
    unittest.main()
