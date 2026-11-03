"""Unit tests for scripts/analysis/te_rebind_country.py, the tool each system's
binding PR runs first (plan 2026-11-02-charts-help-national-info, Task F0.5).

A fixture of two types and three keys holds the plan's contract: the mechanical
read is rewritten; an entry-only read is reported and left; a key the entry's
status_desc also renders is reported as shared and left. Then the classes --write
must leave alone (a read under another country's datacontext, a generated file, a
chart bar's tooltip), and the tool agreeing with BindingTest on the public tabs.
"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "analysis"))

import te_rebind_country as tool  # noqa: E402

BOM = "﻿"

WIDE = """\
types te_fix_types {
	type te_fix_wide = flowcontainer {
		visible = "[JournalEntry.IsActive]"
		textbox = {
			text = "[JournalEntry.GetCountry.GetName]"
		}
		textbox = {
			text = "te_fix_mech"
		}
		textbox = {
			tooltip = "te_fix_entry"
		}
		te_fix_row = {}
		widget = {
			using = te_own_country_only
			textbox = {
				text = "[GetPlayer.GetName]"
			}
		}
	}

	type te_fix_row = widget {
		textbox = {
			raw_text = "[GetPlayer.MakeScope.ScriptValue('x')]"
		}
		textbox = {
			text = "te_fix_shared"
		}
		button = {
			onclick = "[GetScriptedGui('x').Execute( GuiScope.SetRoot( GetPlayer.MakeScope ).End )]"
		}
	}
}
"""

LOC = """\
l_english:
 te_fix_mech: "[JournalEntry.GetCountry.GetName] and [GetPlayer.GetName]"
 te_fix_entry: "[JournalEntry.GetGoalProgress]"
 te_fix_shared: "[JournalEntry.GetCountry.GetName]'s plan"
"""

JE = """\
je_fix = {
	status_desc = {
		first_valid = {
			triggered_desc = {
				desc = te_fix_shared
				trigger = { always = yes }
			}
		}
	}
}
"""


def _put(root, path, text, bom=True):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="") as fh:
        fh.write((BOM if bom else "") + text)


def _get(root, path):
    with open(os.path.join(root, path), encoding="utf-8", newline="") as fh:
        return fh.read()


GUI = "gui/journal_entry_widgets/te_fix_widget.gui"
YML = "localization/english/te_fix_l_english.yml"


class FixtureTest(unittest.TestCase):
    """The plan's fixture: two types, three keys."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _put(self.root, GUI, WIDE)
        _put(self.root, YML, LOC)
        _put(self.root, "common/journal_entries/je_fix.txt", JE)
        self.s = tool.survey("te_fix_wide", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def reads(self):
        return sorted((r.finding.where, r.finding.line, r.cls, r.finding.what) for r in self.s.markup)

    def test_markup_reads_by_class(self):
        self.assertEqual(self.reads(), [
            ("te_fix_row", 24, "mechanical", "GetPlayer"),
            ("te_fix_row", 30, "mechanical", "GetPlayer"),
            ("te_fix_wide", 3, "entry-only", "JournalEntry.IsActive"),
            ("te_fix_wide", 5, "mechanical", "JournalEntry.GetCountry"),
        ])

    def test_the_guarded_read_is_not_listed(self):
        self.assertNotIn(17, [r.finding.line for r in self.s.markup])

    def test_loc_reads_by_class(self):
        got = {k: sorted(r.cls for r in kr.reads) for k, kr in self.s.loc.items()}
        self.assertEqual(got, {"te_fix_mech": ["mechanical", "mechanical"],
                               "te_fix_entry": ["entry-only"],
                               "te_fix_shared": ["shared"]})

    def test_a_shared_key_names_the_entry(self):
        (cls, source), = self.s.loc["te_fix_shared"].notes
        self.assertEqual(cls, "shared")
        self.assertIn("journal entry text", source)
        self.assertIn("common/journal_entries/je_fix.txt:5", source)

    def test_the_control_is_listed(self):
        self.assertEqual([(f.where, f.line) for f in self.s.controls], [("te_fix_row", 30)])

    def test_write_rewrites_the_mechanical_reads_only(self):
        done = tool.write(self.s)
        self.assertEqual(done, {GUI: 3, YML: 2})
        gui = _get(self.root, GUI)
        self.assertIn('text = "[Country.GetName]"', gui)
        self.assertIn('raw_text = "[Country.MakeScope.ScriptValue(\'x\')]"', gui)
        self.assertIn("GuiScope.SetRoot( Country.MakeScope )", gui)
        self.assertIn('visible = "[JournalEntry.IsActive]"', gui, "the entry-only read is left")
        self.assertIn('text = "[GetPlayer.GetName]"', gui, "the guarded read is left")
        loc = _get(self.root, YML)
        self.assertIn('te_fix_mech: "[Country.GetName] and [Country.GetName]"', loc)
        self.assertIn('te_fix_entry: "[JournalEntry.GetGoalProgress]"', loc)
        self.assertIn('te_fix_shared: "[JournalEntry.GetCountry.GetName]\'s plan"', loc)
        for path in (GUI, YML):
            text = _get(self.root, path)
            self.assertTrue(text.startswith(BOM) and not text.startswith(BOM * 2), path)

    def test_after_write_only_the_rest_is_left(self):
        tool.write(self.s)
        s = tool.survey("te_fix_wide", self.root)
        self.assertEqual(sorted(r.cls for r in s.markup), ["entry-only"])
        self.assertEqual(sorted(s.loc), ["te_fix_entry", "te_fix_shared"])

    def test_the_cli(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(tool.main(["te_fix_wide", "--root", self.root]), 0)
        text = out.getvalue()
        self.assertIn("Markup, by type", text)
        self.assertIn(f"{GUI}", text)
        self.assertIn("entry-only    :3  JournalEntry.IsActive", text)
        self.assertIn("te_fix_shared  localization/english/te_fix_l_english.yml:4  shared", text)
        self.assertIn("Controls to guard", text)


SHADOW = """\
types te_fix_types {
	type te_fix_wide = flowcontainer {
		flowcontainer = {
			datacontext = "[Country.GetPowerBloc]"
			visible = "[GetPlayer.IsInPowerBloc]"
			datamodel = "[PowerBloc.GetMembers]"
			item = {
				textbox = {
					text = "[GetPlayer.GetName]"
				}
			}
		}
		flowcontainer = {
			datamodel = "[Country.MakeScope.GetList('rivals')]"
			item = {
				widget = {
					datacontext = "[Scope.GetCountry]"
					text = "te_fix_row_name"
					textbox = {
						text = "[GetPlayer.GetName]"
					}
				}
			}
		}
		te_fix_chart = {
			blockoverride "bar_tooltip" {
				tooltip = "te_fix_bar_tt"
			}
		}
		te_fix_generated_row = {}
	}

	type te_fix_chart = widget {
		datamodel = "[Country.MakeScope.GetList('te_hist')]"
		item = {
			widget = {
				block "bar_tooltip" {}
			}
		}
	}
}
"""

GENERATED = """\
# AUTO-GENERATED by scripts/generators/gen_fix.py; do not edit manually.
types te_fix_generated {
	type te_fix_generated_row = widget {
		textbox = {
			text = "[GetPlayer.GetName]"
		}
	}
}
"""

SHADOW_LOC = """\
l_english:
 te_fix_row_name: "[GetPlayer.GetName] and [Country.GetName]"
 te_fix_bar_tt: "[GetPlayer.MakeScope.ScriptValue('y')]"
"""


class LeftAloneTest(unittest.TestCase):
    """What --write must not rewrite: another country's Country, a generated
    file, a chart bar's tooltip."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _put(self.root, GUI, SHADOW)
        _put(self.root, "gui/journal_entry_widgets/te_fix_generated_rows.gui", GENERATED)
        _put(self.root, YML, SHADOW_LOC)
        self.s = tool.survey("te_fix_wide", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_classes(self):
        got = sorted((r.finding.where, r.finding.line, r.cls) for r in self.s.markup)
        self.assertEqual(got, [
            ("te_fix_generated_row", 5, "mechanical"),
            ("te_fix_wide", 5, "mechanical"),  # the members datamodel's own widget: the parent's Country
            ("te_fix_wide", 9, "shadowed"),  # a member
            ("te_fix_wide", 20, "shadowed"),  # a rival's row
        ])
        why = {r.finding.line: r.why for r in self.s.markup if r.cls == "shadowed"}
        self.assertIn(f'{GUI}:6 datamodel = "[PowerBloc.GetMembers]"', why[9])
        self.assertIn(f'{GUI}:17 datacontext = "[Scope.GetCountry]"', why[20])

    def test_loc_classes(self):
        got = {k: [cls for cls, _ in kr.notes] for k, kr in self.s.loc.items()}
        self.assertEqual(got, {"te_fix_row_name": ["shadowed"], "te_fix_bar_tt": ["item tooltip"]})

    def test_the_generator_is_named(self):
        self.assertEqual(self.s.generated["gui/journal_entry_widgets/te_fix_generated_rows.gui"],
                         "scripts/generators/gen_fix.py")

    def test_write_leaves_them(self):
        before_gen = _get(self.root, "gui/journal_entry_widgets/te_fix_generated_rows.gui")
        before_loc = _get(self.root, YML)
        self.assertEqual(tool.write(self.s), {GUI: 1})
        gui = _get(self.root, GUI)
        self.assertIn('visible = "[Country.IsInPowerBloc]"', gui)
        self.assertIn('text = "[GetPlayer.GetName]"', gui, "the shadowed read is left")
        self.assertEqual(_get(self.root, "gui/journal_entry_widgets/te_fix_generated_rows.gui"), before_gen)
        self.assertEqual(_get(self.root, YML), before_loc)


FRAME = """\
types te_fix_types {
	type te_fix_wide = flowcontainer {
		te_fix_frame = {
			blockoverride "body" {
				textbox = {
					text = "[GetPlayer.GetName]"
				}
			}
		}
	}

	type te_fix_frame = flowcontainer {
		block "tab_country" {
			datacontext = "[GetPlayer]"
		}
		block "body" {}
	}
}
"""


class BlockDefaultTest(unittest.TestCase):
    """A read in a shared type's block default (the frame's tab_country) is
    changed by a blockoverride where this panel draws the type, never in place."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _put(self.root, GUI, FRAME)
        self.s = tool.survey("te_fix_wide", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_block_is_named(self):
        got = sorted((r.finding.where, r.finding.line, r.cls, r.block) for r in self.s.markup)
        self.assertEqual(got, [("te_fix_frame", 14, "bare", "tab_country"),
                               ("te_fix_wide", 6, "mechanical", "")])

    def test_the_listing_says_override_it(self):
        text = tool.render(self.s)
        self.assertIn('give this panel a blockoverride "tab_country" where it draws te_fix_frame', text)
        self.assertIn(f"(drawn at {GUI}:3)", text)


ITEMS = """\
types te_fix_types {
	type te_fix_wide = flowcontainer {
		flowcontainer = {
			datamodel = "[Country.MakeScope.GetList('rows')]"
			item = {
				widget = {
					datacontext = "[Scope.GetScriptContainer]"
					text = "[GetPlayer.GetName]"
					tooltip = "[GetScriptedGui('x').ExecuteTooltip( GuiScope.SetRoot( GetPlayer.MakeScope ).End )]"
					button = {
						tooltip = "[Concatenate( GetScriptedGui('x').IsValidTooltip( GuiScope.SetRoot( GetPlayer.MakeScope ).End ), '' )]"
					}
				}
			}
		}
		textbox = {
			tooltip = "[GetPlayer.GetName]"
		}
	}
}
"""

CUSTOM = """\
te_fix_custom = {
	type = country
	text = {
		trigger = { always = yes }
		localization_key = te_fix_picked
	}
}
"""

CUSTOM_LOC = """\
l_english:
 te_fix_mech: "[Country.GetCustom('te_fix_custom')]"
 te_fix_picked: "[JournalEntry.GetCountry.GetName]"
"""


class ItemTooltipTest(unittest.TestCase):
    """A tooltip inside a datamodel's item reads GetPlayer for a reason (gotcha
    #24: it may have only the item's context), so --write leaves it in markup
    as in loc. A text on the item, and a tooltip outside any item, are
    mechanical."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _put(self.root, GUI, ITEMS)
        self.s = tool.survey("te_fix_wide", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_classes(self):
        got = sorted((r.finding.line, r.cls) for r in self.s.markup)
        self.assertEqual(got, [(8, "mechanical"), (9, "item tooltip"), (11, "item tooltip"), (17, "mechanical")])
        self.assertIn(f"{GUI}:4 datamodel", [r.why for r in self.s.markup if r.cls == "item tooltip"][0])

    def test_write_leaves_them(self):
        self.assertEqual(tool.write(self.s), {GUI: 2})
        gui = _get(self.root, GUI)
        self.assertEqual(gui.count("SetRoot( GetPlayer.MakeScope )"), 2, "both item tooltips are left")
        self.assertIn('text = "[Country.GetName]"', gui)
        self.assertIn('tooltip = "[Country.GetName]"', gui)


class CustomLocTest(unittest.TestCase):
    """A key that GetCustom renders is the caller's text: reached, rewritten
    with it, and not shared with script."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        _put(self.root, GUI, WIDE)
        _put(self.root, YML, CUSTOM_LOC)
        _put(self.root, "common/customizable_localization/te_fix_custom.txt", CUSTOM)
        self.s = tool.survey("te_fix_wide", self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_custom_key_is_reached_and_mechanical(self):
        kr = self.s.loc["te_fix_picked"]
        self.assertEqual(kr.notes, [], "a customizable localization entry is not script")
        self.assertEqual([r.cls for r in kr.reads], ["mechanical"])

    def test_write_rewrites_it(self):
        tool.write(self.s)
        self.assertIn('te_fix_picked: "[Country.GetName]"', _get(self.root, YML))


class OtherTabsTest(unittest.TestCase):
    """A key another tab's panel renders too says so, and where a world key
    then goes (WORLD_LOC's Shared heading)."""

    def test_the_note(self):
        with tempfile.TemporaryDirectory() as root:
            _put(root, GUI, WIDE)
            _put(root, YML, LOC)
            s = tool.survey("te_fix_wide", root, others={"banking": {"te_fix_mech"}, "seabed": set()})
        self.assertEqual(s.loc["te_fix_mech"].also, ["banking"])
        self.assertEqual(s.loc["te_fix_entry"].also, [])
        self.assertIn("also rendered by banking: if it goes in WORLD_LOC, it goes once, under its Shared heading",
                      tool.render(s))

    def test_the_repo_names_a_key_two_tabs_render(self):
        # The tabs' rendered keys, which `also` is drawn from: a key with no read
        # left (Banking's binding, PR F2, took te_hist_since's) still counts, so
        # this holds however many systems are bound; test_the_note holds `also`.
        for key in ("banking", "colonial_empire"):
            self.assertIn("te_hist_since", tool._tab_keys(key), key)

    def test_isactive_becomes_the_entrys_gate_not_the_readouts(self):
        """Banking and the Colonial Empire open on a readout without the entry
        (their open gate is an Or); a composer's IsActive is the entry's gate."""
        for key, entry in [("banking", "te_budget_banking_tab_sgui"),
                           ("colonial_empire", "te_window_colonial_empire_tab_sgui")]:
            with self.subTest(key):
                s = tool.survey_tab(key)
                self.assertEqual(s.gate, f"GetScriptedGui('{entry}').IsShown( GuiScope.SetRoot( Country.MakeScope ).End )")
                self.assertNotIn("readout", s.gate)
                # The advice prints while an IsActive read is left to bind.
                if any(r.finding.what == "JournalEntry.IsActive" for r in s.markup):
                    self.assertIn(f"the entry's gate on Country: [{s.gate}]", tool.render(s))
        from scripts.generators import gen_te_systems_window as gen
        nation = next(t for t in gen.TABS if t.key == "nation")
        self.assertIsNone(tool.entry_gate(nation))  # always open, no gate


class OtherCountryTest(unittest.TestCase):
    def test_contexts(self):
        for expr, other in [
            ("Scope.GetCountry", True),
            ("Country.MakeScope.Var('x').GetCountry", True),
            ("PowerBloc.GetMembers", True),
            ("JournalEntry.GetCountry.GetPowerBloc.GetLeader", True),
            ("GetPlayer", True),
            ("JournalEntry.GetCountry", False),
            ("Country.Self", False),
            ("JournalEntry.GetCountry.GetPowerBloc", False),
            ("Scope.GetScriptContainer", False),
            ("GetPlayerJournalEntry('je_space_race')", False),
            ("GetScriptedGui('x')", False),
        ]:
            self.assertEqual(tool._other_country(expr), other, expr)


class RepoTest(unittest.TestCase):
    """On the repo: a public tab has nothing left to bind, as BindingTest says."""

    def test_public_tabs_have_nothing_to_bind(self):
        from scripts.generators import gen_te_systems_window as gen
        for tab in (t for t in gen.TABS if t.public):
            s = tool.survey_tab(tab.key)  # with WORLD_LOC, as BindingTest reads it
            self.assertEqual([str(r.finding) for r in s.markup], [], tab.key)
            self.assertEqual(sorted(s.loc), [], tab.key)
            self.assertEqual(s.controls, [], tab.key)

    def test_survey_tab_takes_world_loc(self):
        """survey_tab reads WORLD_LOC, as BindingTest does: a key listed there is
        a world read, not one to bind."""
        import gui_test_helpers as h
        import test_te_system_tab_bodies as bodies
        keys = h.panel_loc_keys({"te_demog_browser_sections"}, h.mod_types(), h.load_loc())
        key = min(keys)
        saved = dict(bodies.WORLD_LOC)
        try:
            bodies.WORLD_LOC[key] = "a fixture"
            self.assertIn(key, tool.survey_tab("demographics").world_loc)
        finally:
            bodies.WORLD_LOC.clear()
            bodies.WORLD_LOC.update(saved)

    def test_survey_tab_names_an_unknown_tab(self):
        with self.assertRaises(KeyError):
            tool.survey_tab("no_such_tab")


if __name__ == "__main__":
    unittest.main()
