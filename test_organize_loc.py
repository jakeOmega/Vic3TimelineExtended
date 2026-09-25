"""Tests for organize_loc's unused-key detection."""

import contextlib
import io
import os
import tempfile
import unittest

from organize_loc import find_diplo_action_keys, find_quoted_loc_args, organize_all


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


if __name__ == "__main__":
    unittest.main()
