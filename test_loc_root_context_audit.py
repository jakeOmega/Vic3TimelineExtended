"""Unit tests for loc_root_context_audit (#319).

Each fixture is a throwaway mod tree with one journal entry (a status_desc, a
progress_desc, its implicit keys), a scripted button, a scripted progress
bar, a scripted GUI, a customizable localization entry, a journal widget and a
panel whose types stand for a public tab. The tree is clean as written; each
test plants one read and looks for its flag. The crux is which context a key
is reached from, through splices, named keys and GetCustom entries, and which
roots each context flags.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

import gui_test_helpers as h
import loc_root_context_audit as audit_module
from loc_root_context_audit import (
    CHECK, ENTRY, ENTRY_READ_ON_PUBLIC, FRAME, PLAYER_READ_ON_PUBLIC, PUBLIC, RELOAD_NOTE, REPORT_PATH,
    SCRIPT_ROOT_IN_WIDGET, SGUI, WIDGET, WIDGET_ROOT_IN_ENTRY, Reach, audit, main, regenerate, render_report,
)

LOC_FILE = "localization/english/te_fx_l_english.yml"
WIDGET_FILE = "gui/journal_entry_widgets/fx_widget.gui"
PANEL_FILE = "gui/te_fx_panel.gui"

JOURNAL = """\
je_fx = {
\tstatus_desc = {
\t\tfirst_valid = {
\t\t\ttriggered_desc = {
\t\t\t\tdesc = fx_status_active
\t\t\t\ttrigger = { custom_tooltip = { text = fx_status_trigger_tt always = yes } }
\t\t\t}
\t\t\ttriggered_desc = { desc = fx_status_idle }
\t\t}
\t}
\tprogress_desc = fx_progress
\tscripted_button = fx_button
}
"""

BUTTONS = """\
fx_button = {
\tname = "fx_button_name"
\tdesc = "fx_button_desc"
\tpossible = { custom_tooltip = { text = fx_button_possible_tt } }
\teffect = { custom_tooltip = fx_button_effect_tt }
}
"""

BARS = """\
fx_bar = {
\tname = "fx_bar_name"
\tdesc = "fx_bar_desc"
\tmonthly_progress = { add = { value = 1 desc = "fx_bar_term" } }
}
"""

SGUIS = """\
fx_list_sgui = {
\tscope = country
\teffect = {
\t\tevery_scope_state = { custom_tooltip = fx_sgui_line }
\t}
}
"""

CUSTOM = """\
fx_custom = {
\ttype = country
\ttext = { trigger = { always = yes } localization_key = fx_custom_a }
\ttext = { localization_key = fx_custom_b }
}
"""

JE_WIDGET = """\
flowcontainer = {
\tname = "widget_je_fx"
\ttextbox = { text = "fx_widget_label" }
\ttextbox = { tooltip = "fx_widget_tt" }
\ttextbox = { text = "[Country.GetCustom('fx_custom')]" }
\ttextbox = { tooltip = "[GetScriptedGui('fx_list_sgui').ExecuteTooltip( GuiScope.SetRoot( Country.MakeScope ).End )]" }
}
"""

PANEL = """\
types fixture
{
\ttype te_fx_wide = flowcontainer {
\t\tte_fx_section = {}
\t\twidget = {
\t\t\tusing = te_own_country_only
\t\t\ttextbox = { text = "fx_own_label" }
\t\t}
\t}
\ttype te_fx_section = flowcontainer {
\t\ttextbox = { text = "fx_public_label" }
\t}
}
"""

# Every key the tree names, with text that is right where it renders.
CLEAN = {
    "je_fx": "Fixture",
    "je_fx_reason": "Run by [JournalEntry.GetCountry.GetName], as [ROOT.GetCountry.GetName] says",
    "fx_status_active": "[ROOT.GetCountry.GetName] is at it: $fx_shared$",
    "fx_status_idle": "Idle",
    "fx_status_trigger_tt": "A trigger's tooltip",
    "fx_progress": "[JournalEntry.GetGoalProgressPercent|%1v]",
    "fx_button_name": "Go",
    "fx_button_desc": "[ROOT.GetCountry.GetName] goes, with [SCOPE.sCountry('rival').GetName]",
    "fx_button_possible_tt": "Possible",
    "fx_button_effect_tt": "Effect",
    "fx_bar_name": "Bar",
    "fx_bar_desc": "#v [JournalEntry.GetCurrentBarProgress(ScriptedProgressBar.Self)|%]#!",
    "fx_bar_term": "A term",
    "fx_sgui_line": "[THIS.GetState.GetName]: [JournalEntry.GetCountry.GetName]",
    "fx_custom_a": "A",
    "fx_custom_b": "B",
    "fx_widget_label": "[Country.GetName]: $fx_shared$",
    "fx_widget_tt": "[JournalEntry.GetCountry.MakeScope.ScriptValue('x')|0]",
    "fx_shared": "[GetPlayer.GetName] and plain text",
    "fx_public_label": "[Country.GetName]",
    "fx_own_label": "[JournalEntry.GetCountry.GetName] and [GetPlayer.GetName]",
}
FX_PUBLIC = {"fx": {"te_fx_wide"}}


def _write(root: str, rel: str, text: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write(text)


class _Fixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        _write(self.root, "common/journal_entries/te_fx_je.txt", JOURNAL)
        _write(self.root, "common/scripted_buttons/te_fx_buttons.txt", BUTTONS)
        _write(self.root, "common/scripted_progress_bars/te_fx_bars.txt", BARS)
        _write(self.root, "common/scripted_guis/te_fx_sguis.txt", SGUIS)
        _write(self.root, "common/customizable_localization/te_fx_custom_loc.txt", CUSTOM)
        _write(self.root, WIDGET_FILE, JE_WIDGET)
        _write(self.root, PANEL_FILE, PANEL)
        self.text = dict(CLEAN)
        self.tags: dict[str, str] = {}

    def run_audit(self, public=None, world=(), **changed):
        """Write the loc with `changed` keys' text replaced or added, and audit."""
        self.text.update(changed)
        lines = [f' {key}:0 "{value}"' + (f" {self.tags[key]}" if key in self.tags else "")
                 for key, value in self.text.items()]
        _write(self.root, LOC_FILE, "l_english:\n" + "\n".join(lines) + "\n")
        return audit(self.root, public_panels=public or {}, world_loc=set(world))

    def line(self, key):
        return list(self.text).index(key) + 2

    def flags(self, result):
        return [(f.kind, f.key, f.reads) for f in result.flags]


class CleanTests(_Fixture):
    def test_the_fixture_is_clean(self):
        r = self.run_audit(public=FX_PUBLIC)
        self.assertEqual(self.flags(r), [])
        self.assertEqual(r.failing, 0)

    def test_what_each_context_reaches(self):
        r = self.run_audit(public=FX_PUBLIC)
        # status_desc's two keys and the splice, the button's name and desc: not the
        # tooltips in its blocks, nor a tooltip in a status_desc's trigger
        self.assertEqual(r.reach[ENTRY], 5)
        # je_fx, je_fx_reason, the progress_desc, the bar's name and desc: not its term's label
        self.assertEqual(r.reach[FRAME], 5)
        # the widget's label, its splice and its tooltip, the custom entry's two keys, the panel's two
        self.assertEqual(r.reach[WIDGET], 7)
        self.assertEqual(r.reach[SGUI], 1)
        # the guarded label is the player's own
        self.assertEqual(r.reach[PUBLIC], 1)
        self.assertEqual(r.public_tabs, 1)

    def test_a_key_right_in_both_contexts_passes(self):
        """fx_shared is spliced into a status_desc key and into a widget key.
        With no root, or the player, it is right in both."""
        self.run_audit()
        reach = Reach(h.load_loc(os.path.join(self.root, "localization", "english")), {})
        self.assertIn("fx_shared", reach.closure({"fx_status_active"}))
        self.assertIn("fx_shared", reach.closure({"fx_widget_label"}))
        self.assertEqual(self.flags(self.run_audit(fx_shared="Plain text")), [])
        self.assertEqual(self.flags(self.run_audit(fx_shared="[GetPlayer.MakeScope.ScriptValue('x')|0]")), [])


class EntryTextTests(_Fixture):
    def test_a_widget_root_in_a_status_desc_is_flagged(self):
        r = self.run_audit(fx_status_idle="[Country.GetName] idles")
        self.assertEqual(self.flags(r), [(WIDGET_ROOT_IN_ENTRY, "fx_status_idle", ("Country.GetName",))])
        f = r.flags[0]
        self.assertEqual((f.file, f.line), (LOC_FILE, self.line("fx_status_idle")))
        self.assertEqual(f.path, ("common/journal_entries/te_fx_je.txt:8 status_desc", "fx_status_idle"))

    def test_the_journal_entry_root_in_a_status_desc_is_flagged(self):
        r = self.run_audit(fx_status_active="[JournalEntry.GetCountry.GetCustom('fx_custom')] [JournalEntry.IsActive]")
        self.assertEqual(self.flags(r), [(WIDGET_ROOT_IN_ENTRY, "fx_status_active",
                                          ("JournalEntry.GetCountry", "JournalEntry.IsActive"))])
        self.assertEqual(r.flags[0].path[0], "common/journal_entries/te_fx_je.txt:5 status_desc")

    def test_a_one_line_status_desc_is_read(self):
        _write(self.root, "common/journal_entries/te_fx_je.txt", "je_fx = {\n\tstatus_desc = fx_status_idle\n}\n")
        r = self.run_audit(fx_status_idle="[Country.GetName] idles")
        self.assertEqual([f.path for f in r.flags],
                         [("common/journal_entries/te_fx_je.txt:2 status_desc", "fx_status_idle")])

    def test_a_scripted_buttons_name_and_desc_are_entry_text(self):
        r = self.run_audit(fx_button_name="[Country.GetName]", fx_button_desc="[JournalEntry.GetCountry.GetName]")
        self.assertEqual(self.flags(r), [(WIDGET_ROOT_IN_ENTRY, "fx_button_name", ("Country.GetName",)),
                                         (WIDGET_ROOT_IN_ENTRY, "fx_button_desc", ("JournalEntry.GetCountry",))])
        self.assertEqual(r.flags[0].path, ("common/scripted_buttons/te_fx_buttons.txt:2 fx_button's name",
                                           "fx_button_name"))

    def test_a_key_reached_only_through_a_splice_is_followed(self):
        """fx_shared's own text is all that changes; a status_desc key splices it."""
        r = self.run_audit(fx_shared="[Country.GetName]")
        self.assertEqual(self.flags(r), [(WIDGET_ROOT_IN_ENTRY, "fx_shared", ("Country.GetName",))])
        self.assertEqual(r.flags[0].path, ("common/journal_entries/te_fx_je.txt:5 status_desc", "fx_status_active",
                                           "fx_shared"))

    def test_a_splice_two_levels_down_is_followed(self):
        r = self.run_audit(fx_shared="$fx_deep|v$", fx_deep="[Country.GetName]")
        self.assertEqual([f.path[1:] for f in r.flags], [("fx_status_active", "fx_shared", "fx_deep")])

    def test_script_roots_are_right_in_entry_text(self):
        r = self.run_audit(fx_status_idle="[ROOT.GetCountry.GetName] [SCOPE.sCountry('x').GetName] [THIS.GetName]")
        self.assertEqual(self.flags(r), [])

    def test_other_script_text_is_not_entry_text(self):
        """A button's tooltips, a tooltip in a status_desc's trigger and a
        progress bar term's label are not what the rule covers."""
        r = self.run_audit(fx_button_possible_tt="[Country.GetName]", fx_button_effect_tt="[Country.GetName]",
                           fx_status_trigger_tt="[Country.GetName]", fx_bar_term="[Country.GetName]")
        self.assertEqual(self.flags(r), [])


class WidgetTests(_Fixture):
    def test_a_script_root_in_a_widget_key_is_flagged(self):
        r = self.run_audit(fx_widget_tt="[ROOT.GetCountry.GetName] [SCOPE.sCountry('x').GetName] [THIS.GetName]")
        self.assertEqual(self.flags(r), [(SCRIPT_ROOT_IN_WIDGET, "fx_widget_tt",
                                          ("ROOT.GetCountry", "SCOPE.sCountry", "THIS.GetName"))])
        self.assertEqual(r.flags[0].path, (f"{WIDGET_FILE}:4", "fx_widget_tt"))

    def test_a_status_key_spliced_into_a_widget_is_flagged_where_it_reads_root(self):
        """#318's shape: the shared key is right for the status_desc that
        splices it, and a widget key now splices it too."""
        r = self.run_audit(fx_shared="[ROOT.GetCountry.GetName]")
        self.assertEqual(self.flags(r), [(SCRIPT_ROOT_IN_WIDGET, "fx_shared", ("ROOT.GetCountry",))])
        self.assertEqual(r.flags[0].path, (f"{WIDGET_FILE}:3", "fx_widget_label", "fx_shared"))

    def test_a_named_key_is_followed(self):
        r = self.run_audit(fx_widget_tt="[SelectLocalization( Country.IsAtWar, 'fx_pick_a', 'fx_pick_b' )]"
                                        "[AddLocalizationIf( Country.IsAtWar, 'fx_pick_c' )]",
                           fx_pick_a="At war", fx_pick_b="[ROOT.GetCountry.GetName] at peace",
                           fx_pick_c="[THIS.GetName]")
        self.assertEqual(self.flags(r), [(SCRIPT_ROOT_IN_WIDGET, "fx_pick_b", ("ROOT.GetCountry",)),
                                         (SCRIPT_ROOT_IN_WIDGET, "fx_pick_c", ("THIS.GetName",))])
        self.assertEqual(r.flags[0].path[1:], ("fx_widget_tt", "fx_pick_b"))

    def test_a_custom_localization_entrys_keys_are_followed(self):
        """#317's shape: a GetCustom entry's keys render in the caller's context."""
        r = self.run_audit(fx_custom_b="[ROOT.GetCountry.GetName]")
        self.assertEqual(self.flags(r), [(SCRIPT_ROOT_IN_WIDGET, "fx_custom_b", ("ROOT.GetCountry",))])
        # the .gui names the entry, not the key, so the path starts at the file
        self.assertEqual(r.flags[0].path, (WIDGET_FILE, "fx_custom_b"))
        r = self.run_audit(fx_custom_b="B", fx_custom_a="[Country.GetName]",
                           fx_status_idle="[ROOT.GetCountry.GetCustom('fx_custom')]")
        self.assertEqual(self.flags(r), [(WIDGET_ROOT_IN_ENTRY, "fx_custom_a", ("Country.GetName",))])
        self.assertEqual(r.flags[0].path[1:], ("fx_status_idle", "fx_custom_a"))

    def test_widget_roots_are_right_in_a_widget(self):
        r = self.run_audit(fx_widget_tt="[Country.GetName] [JournalEntry.GetCountry.GetName] [GetPlayer.GetName]")
        self.assertEqual(self.flags(r), [])

    def test_a_read_is_a_root_inside_an_expression(self):
        r = self.run_audit(fx_status_idle="The richest Country. [ROOT.GetCountry.GetName] "
                                          "[SCOPE.sCountry('x').GetCountry.GetName] [Concept('c', 'Country.x')]",
                           fx_widget_tt="DO THIS. [Country.MakeScope.Var('ROOT.x').GetValue] [TopScope.GetName]")
        self.assertEqual(self.flags(r), [])

    def test_a_comment_in_a_gui_file_names_no_key(self):
        _write(self.root, WIDGET_FILE, JE_WIDGET + '# textbox = { text = "fx_status_idle" }\n')
        self.assertEqual(self.flags(self.run_audit(fx_status_idle="[ROOT.GetCountry.GetName]")), [])
        _write(self.root, WIDGET_FILE, JE_WIDGET + 'textbox = { text = "fx_status_idle" }\n')
        r = self.run_audit()
        self.assertEqual(self.flags(r), [(SCRIPT_ROOT_IN_WIDGET, "fx_status_idle", ("ROOT.GetCountry",))])
        self.assertEqual(r.flags[0].path, (f"{WIDGET_FILE}:8", "fx_status_idle"))


class NotJudgedTests(_Fixture):
    def test_the_entrys_own_text_and_a_progress_bar_take_either_root(self):
        r = self.run_audit(je_fx_reason="[JournalEntry.GetCountry.GetName] [Country.GetName] [ROOT.GetCountry.GetName]",
                           je_fx_goal="[JournalEntry.GetTotalGoalValue|D] [Country.GetName]",
                           je_fx_status="[JournalEntry.GetCountry.GetNameNoFormatting]",
                           fx_progress="[JournalEntry.GetCountry.GetCustom('fx_custom')]",
                           fx_bar_name="[JournalEntry.GetCountry.GetName] [SCOPE.sCountry('x').GetName]")
        self.assertEqual(self.flags(r), [])
        self.assertEqual(r.reach[FRAME], 9)  # two more implicit keys, and the custom entry's two

    def test_a_scripted_guis_tooltip_takes_either_root(self):
        r = self.run_audit(fx_sgui_line="[THIS.GetName] [ROOT.GetName] [SCOPE.sState('x').GetName] "
                                        "[JournalEntry.GetCountry.GetName] [Country.GetName]")
        self.assertEqual(self.flags(r), [])

    def test_a_widget_key_that_is_also_a_scripted_guis_tooltip_is_flagged_and_says_so(self):
        _write(self.root, WIDGET_FILE, JE_WIDGET + 'textbox = { text = "fx_sgui_line" }\n')
        r = self.run_audit()
        self.assertEqual(self.flags(r), [(SCRIPT_ROOT_IN_WIDGET, "fx_sgui_line", ("THIS.GetState",))])
        self.assertTrue(r.flags[0].also_sgui)
        self.assertIn("also a scripted GUI's tooltip key", render_report(r))


class PublicPanelTests(_Fixture):
    def test_the_journal_entry_root_on_a_public_tab_is_flagged(self):
        r = self.run_audit(public=FX_PUBLIC, fx_public_label="[JournalEntry.GetCountry.GetName]")
        self.assertEqual(self.flags(r), [(ENTRY_READ_ON_PUBLIC, "fx_public_label", ("JournalEntry.GetCountry",))])
        self.assertEqual(r.flags[0].tabs, ("fx",))
        self.assertEqual(r.flags[0].path, (f"{PANEL_FILE}:11", "fx_public_label"))
        self.assertIn(f"rendered by fx, reached by {PANEL_FILE}:11 → `fx_public_label`: "
                      f"`python3 scripts/analysis/te_rebind_country.py fx`", render_report(r))

    def test_the_same_key_passes_on_a_panel_that_is_not_public(self):
        self.assertEqual(self.flags(self.run_audit(fx_public_label="[JournalEntry.GetCountry.GetName]")), [])

    def test_a_player_read_is_flagged_unless_it_is_a_world_read(self):
        r = self.run_audit(public=FX_PUBLIC, fx_public_label="[GetPlayer.GetName] [GetPlayerJournalEntry('x').IsActive]")
        self.assertEqual(self.flags(r), [(ENTRY_READ_ON_PUBLIC, "fx_public_label", ("GetPlayerJournalEntry",)),
                                         (PLAYER_READ_ON_PUBLIC, "fx_public_label", ("GetPlayer",))])
        r = self.run_audit(public=FX_PUBLIC, world={"fx_public_label"})
        self.assertEqual(self.flags(r), [(ENTRY_READ_ON_PUBLIC, "fx_public_label", ("GetPlayerJournalEntry",))],
                         "an entry read is never a world read")

    def test_a_key_under_the_guard_is_the_players_own(self):
        """fx_own_label reads the entry and the player under te_own_country_only."""
        self.assertEqual(self.flags(self.run_audit(public=FX_PUBLIC)), [])

    def test_a_splice_on_a_public_tab_is_followed_and_each_tab_named(self):
        r = self.run_audit(public={"fx": {"te_fx_wide"}, "also": {"te_fx_section"}},
                           fx_public_label="$fx_deep$", fx_deep="[JournalEntry.IsActive]")
        self.assertEqual(self.flags(r), [(ENTRY_READ_ON_PUBLIC, "fx_deep", ("JournalEntry.IsActive",))])
        self.assertEqual(r.flags[0].tabs, ("also", "fx"))
        self.assertEqual(r.flags[0].path, (f"{PANEL_FILE}:11", "fx_public_label", "fx_deep"))

    def test_the_players_own_branch_is_not_on_the_path(self):
        """SelectLocalization( Country.IsLocalPlayer, mine, theirs ): another
        country's panel never renders the first key, so it is neither flagged
        nor a step on the way to one."""
        r = self.run_audit(public=FX_PUBLIC,
                           fx_public_label="[SelectLocalization( Country.IsLocalPlayer, 'fx_mine', 'fx_theirs' )]",
                           fx_mine="[GetPlayer.GetName] is ours", fx_theirs="[GetPlayer.GetName] is theirs")
        self.assertEqual(self.flags(r), [(PLAYER_READ_ON_PUBLIC, "fx_theirs", ("GetPlayer",))])
        self.assertEqual(r.flags[0].path, (f"{PANEL_FILE}:11", "fx_public_label", "fx_theirs"))

    def test_a_key_a_custom_entry_brings_starts_at_the_type(self):
        _write(self.root, PANEL_FILE, PANEL.replace('text = "fx_public_label"', "text = \"[Country.GetCustom('fx_custom')]\""))
        r = self.run_audit(public=FX_PUBLIC, fx_custom_b="[JournalEntry.IsActive]")
        self.assertEqual([(f.kind, f.path) for f in r.flags],
                         [(ENTRY_READ_ON_PUBLIC, (f"{PANEL_FILE} (te_fx_section)", "fx_custom_b"))])


class TagTests(_Fixture):
    def test_a_tag_exempts_the_keys_flag(self):
        self.tags["fx_status_idle"] = f"# REVIEWED 2026-11-12 ({CHECK}): the entry is drawn by a widget only"
        r = self.run_audit(fx_status_idle="[Country.GetName] idles")
        self.assertEqual(self.flags(r), [(WIDGET_ROOT_IN_ENTRY, "fx_status_idle", ("Country.GetName",))])
        self.assertEqual(r.flags[0].exemption, {"date": "2026-11-12",
                                                "rationale": "the entry is drawn by a widget only"})
        self.assertEqual((r.failing, r.stale_tags), (0, []))
        report = render_report(r)
        self.assertIn("**2026-11-12**: the entry is drawn by a widget only", report)
        self.assertIn("- unreviewed: 0", report)

    def test_a_tag_for_another_check_or_untagged_does_not(self):
        for tag in ("# REVIEWED 2026-11-12 (loc_script_value): other", "# REVIEWED 2026-11-12: plain"):
            self.tags["fx_status_idle"] = tag
            r = self.run_audit(fx_status_idle="[Country.GetName] idles")
            self.assertEqual((r.failing, r.flags[0].exemption), (1, None), tag)

    def test_a_tag_on_a_clean_key_is_stale(self):
        self.tags["fx_status_idle"] = f"# REVIEWED 2026-11-12 ({CHECK}, loc_script_value): nothing here"
        r = self.run_audit()
        self.assertEqual([(t.file, t.line, t.key) for t in r.stale_tags],
                         [(LOC_FILE, self.line("fx_status_idle"), "fx_status_idle")])
        self.assertEqual(r.failing, 1)
        self.assertIn(f"`{LOC_FILE}:{self.line('fx_status_idle')}` `fx_status_idle`", render_report(r))

    def test_a_tag_does_not_cover_a_public_panel_flag(self):
        self.tags["fx_public_label"] = f"# REVIEWED 2026-11-12 ({CHECK}): no"
        r = self.run_audit(public=FX_PUBLIC, fx_public_label="[JournalEntry.GetCountry.GetName]")
        self.assertIsNone(r.flags[0].exemption)
        self.assertEqual(r.failing, 2, "the flag, and the tag that suppresses nothing")


class RunTests(_Fixture):
    def test_each_run_reads_the_files_again(self):
        """gui_test_helpers caches what it reads; a server reload must not."""
        self.assertEqual(self.flags(self.run_audit()), [])
        self.assertEqual(len(self.run_audit(fx_status_idle="[Country.GetName]").flags), 1)
        _write(self.root, WIDGET_FILE, JE_WIDGET + 'textbox = { text = "fx_status_active" }\n')
        self.assertEqual(len(self.run_audit().flags), 2)

    def test_no_loc_or_no_gui_raises(self):
        with self.assertRaises(FileNotFoundError):
            audit(self.root, public_panels={}, world_loc=set())
        self.run_audit()
        os.remove(os.path.join(self.root, WIDGET_FILE))
        os.remove(os.path.join(self.root, PANEL_FILE))
        with self.assertRaises(FileNotFoundError):
            self.run_audit()

    def test_an_unclosed_block_does_not_stop_the_run(self):
        _write(self.root, "common/scripted_buttons/te_fx_buttons.txt", BUTTONS.rstrip("}\n"))
        r = self.run_audit(fx_button_desc="[Country.GetName]")
        self.assertEqual(self.flags(r), [(WIDGET_ROOT_IN_ENTRY, "fx_button_desc", ("Country.GetName",))])

    def test_another_tree_takes_no_public_panel_from_the_repo(self):
        self.run_audit()
        r = audit(self.root)
        self.assertEqual((r.public_tabs, r.reach[PUBLIC]), (0, 0))

    def test_report_lists_a_flag_with_its_path(self):
        report = render_report(self.run_audit(fx_shared="[ROOT.GetCountry.GetName]"), reach=True)
        self.assertIn(f"### `{LOC_FILE}` (1)", report)
        self.assertIn(f"- line {self.line('fx_shared')}: `fx_shared` reads `ROOT.GetCountry` (script_root_in_widget); "
                      f"reached by {WIDGET_FILE}:3 → `fx_widget_label` → `fx_shared`", report)
        self.assertIn("- widget: 7 keys", report)
        self.assertIn("- entry frame: 5 keys, not judged", report)
        self.assertNotIn("Reach", render_report(self.run_audit()), "the committed report keeps to flag counts")

    def test_regenerate_writes_the_report(self):
        self.tags["fx_status_idle"] = f"# REVIEWED 2026-11-12 ({CHECK}): stale"
        self.run_audit(fx_shared="[ROOT.GetCountry.GetName]")
        with mock.patch("path_constants.mod_path", self.root):
            summary = regenerate(None)
        self.assertEqual((summary["unreviewed"], summary["total_flags"], summary["stale_tags"]), (2, 1, 1))
        self.assertEqual((summary["entry_text_keys"], summary["widget_keys"]), (5, 7))
        self.assertNotIn("public_panel_keys", summary)
        with open(os.path.join(self.root, REPORT_PATH), encoding="utf-8") as fh:
            report = fh.read()
        self.assertIn("`fx_shared` reads `ROOT.GetCountry`", report)
        self.assertIn(f"Not looked at in this run: {RELOAD_NOTE}.", report)

    def as_the_repo(self):
        """The fixture tree stands for the repo: its public tab and no world read."""
        context = mock.patch.object(audit_module, "repo_public_context", return_value=(FX_PUBLIC, set(), ""))
        for patch in (mock.patch.object(audit_module, "_is_repo", return_value=True), context):
            patch.start()
            self.addCleanup(patch.stop)

    def test_a_reload_leaves_the_public_panel_out_and_the_cli_does_not(self):
        """regenerate() pays for neither the tabs' types nor their walk
        (BindingTest holds the rule in CI's test step); the CLI, which CI
        runs with --strict, still flags the key."""
        self.as_the_repo()
        self.run_audit(fx_public_label="[JournalEntry.GetCountry.GetName]")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--strict", "--mod-path", self.root]), 1)
        self.assertIn("`fx_public_label` reads `JournalEntry.GetCountry` (entry_read_on_public_panel)", out.getvalue())
        self.assertIn("- public panel: 1 keys (1 public tabs)", out.getvalue())
        self.assertNotIn("Not looked at", out.getvalue())

        audit_module.repo_public_context.reset_mock()
        unused = [mock.patch.object(h, name, side_effect=AssertionError(f"a reload called {name}"))
                  for name in ("mod_types", "mod_templates", "panel_loc_keys", "panel_view")]
        with mock.patch("path_constants.mod_path", self.root), contextlib.ExitStack() as stack:
            for patch in unused:
                stack.enter_context(patch)
            summary = regenerate(None)
        audit_module.repo_public_context.assert_not_called()
        self.assertEqual((summary["unreviewed"], summary["total_flags"]), (0, 0))
        with open(os.path.join(self.root, REPORT_PATH), encoding="utf-8") as fh:
            self.assertIn("## Public panel", fh.read())

    def test_the_context_is_left_out_aloud_when_its_lists_cannot_be_imported(self):
        with mock.patch.dict(sys.modules, {"test_te_system_tab_bodies": None}):
            panels, world, note = audit_module.repo_public_context()
        self.assertEqual((panels, world), ({}, set()))
        self.assertIn("could not be imported", note)
        self.run_audit(fx_public_label="[JournalEntry.GetCountry.GetName]")
        out = io.StringIO()
        with mock.patch.object(audit_module, "_is_repo", return_value=True), \
                mock.patch.dict(sys.modules, {"test_te_system_tab_bodies": None}), contextlib.redirect_stdout(out):
            self.assertEqual(main(["--strict", "--mod-path", self.root]), 0)
        self.assertIn("Not looked at in this run: the tab registry or `WORLD_LOC` could not be imported", out.getvalue())
        self.assertIn("- public panel: not looked at", out.getvalue())

    def test_strict_exits_1_on_a_flag_only(self):
        self.run_audit()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["--strict", "--mod-path", self.root]), 0)
            self.run_audit(fx_shared="[ROOT.GetCountry.GetName]")
            self.assertEqual(main(["--mod-path", self.root]), 0)
            self.assertEqual(main(["--strict", "--mod-path", self.root]), 1)
        self.assertIn("## Reach (this run)", out.getvalue())


class RepoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from path_constants import mod_path
        cls.root = str(mod_path)
        cls.result = audit(cls.root)

    def test_the_mod_has_no_failing_flag(self):
        self.assertEqual([f for f in self.result.flags if not f.exemption], [])
        self.assertEqual(self.result.stale_tags, [])

    def test_each_context_is_reached(self):
        """Guard the guard: a seed walk that found nothing would pass as clean."""
        reach = self.result.reach
        self.assertGreater(reach[ENTRY], 1000)
        self.assertGreater(reach[FRAME], 100)
        self.assertGreater(reach[WIDGET], 6000)
        self.assertGreater(reach[SGUI], 400)
        self.assertGreater(reach[PUBLIC], 3000)
        self.assertGreaterEqual(self.result.public_tabs, 11)
        self.assertEqual(self.result.public_note, "", "the repo's own run looks at the public tabs")

    def test_the_public_tabs_are_the_binding_tests(self):
        import test_te_system_tab_bodies as binding
        panels, world, note = audit_module.repo_public_context()
        self.assertEqual(set(panels), {t.key for t in binding.PUBLIC})
        self.assertEqual(world, set(binding.WORLD_LOC))
        self.assertEqual(note, "")

    def test_a_public_flags_path_walks_the_binding_tests_keys(self):
        """public_seeds, closed without the player's own branches, is
        panel_loc_keys's set for every public tab, so a flag there has a path."""
        loc, custom = h.load_loc(), h.custom_loc()
        types, templates = h.mod_types(), h.mod_templates()
        reach = Reach(loc, custom, own=False)
        for tab, names in audit_module.repo_public_context()[0].items():
            with self.subTest(tab=tab):
                seeds = audit_module.public_seeds(names, types, templates, loc, custom)
                self.assertEqual(set(reach.closure(seeds)), h.panel_loc_keys(names, types, loc, templates, custom))

    def test_the_reach_is_the_shared_walkers(self):
        """One step at a time, with parents, gives gui_test_helpers.loc_closure's set."""
        loc, custom = h.load_loc(), h.custom_loc()
        gui, files = audit_module.widget_seeds(self.root, loc, custom)
        self.assertGreater(files, 50)
        status, _ = audit_module.journal_seeds(self.root, loc)
        reach = Reach(loc, custom)
        for seeds in (gui, status):
            self.assertEqual(set(reach.closure(seeds)), h.loc_closure(set(seeds), loc, custom=custom))

    def test_every_status_desc_gives_its_keys(self):
        """Each status_desc in the mod's journal entries names at least one loc key the walk finds."""
        import glob
        import re
        loc = h.load_loc()
        status, _ = audit_module.journal_seeds(self.root, loc)
        files = {where.split(":")[0] for where in status.values()}
        with_status = {os.path.relpath(p, self.root) for p in glob.glob(os.path.join(self.root, "common",
                                                                                     "journal_entries", "*.txt"))
                       if re.search(r"(?m)^\s*status_desc\s*=", h._strip_comments(h._read(p)))}
        self.assertEqual(files, with_status)

    def test_post_load_roster_and_ci(self):
        from scripts.analysis.check_post_load_rosters import extract_rosters
        self.assertIn("loc_root_context_audit", extract_rosters(
            os.path.join(self.root, "mod_state_server.py"))["POST_LOAD_AUDITS"])
        import audit_registry  # CI runs the registry's audits (scripts/run_audits.py)
        entry = audit_registry.get("loc_root_context_audit")
        self.assertEqual(entry.command, "python3 loc_root_context_audit.py --strict")
        self.assertEqual(entry.tags, (CHECK,))


if __name__ == "__main__":
    unittest.main()
