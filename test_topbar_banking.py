"""The Banking readings in vanilla's top bar (gui/topbar.gui).

The owner asked for the cycle's phase, momentum and bubble pressure in the top
bar itself, as bands: three icons after MONEY, each its own hover and click
target. This checks that the override is vanilla's file plus that one marked
change, that the readings are gated like the Budget panel's Banking tab, and
that they draw the overview's own icons and tooltips rather than a copy.
"""
import difflib
import os
import re
import unittest

from test_banking_layout import (BUDGET, CUSTOM_LOC, DASH, LOC, SGUIS, _block_from, _loc, _read, _sgui,
                                 _type_body)

REPO = os.path.dirname(os.path.abspath(__file__))
TOPBAR = os.path.join(REPO, "gui", "topbar.gui")
# Vanilla's topbar.gui as the override started from (the branch's first
# commit, which a squash merge does not keep). Update it with each vanilla
# patch merged into gui/topbar.gui (gui_modding_guide.md, "GUI 3-way merge").
VANILLA = os.path.join(REPO, "test_fixtures", "vanilla_gui", "topbar.gui")
MARK = "### TIMELINE EXTENDED"

READINGS = [  # (reading, icon type, overview tooltip, the word the tooltip names)
    ("phase", "te_banking_phase_icons", "banking_dash_phase_tt",
     "[JournalEntry.GetCountry.GetCustom('banking_dash_phase_word')]"),
    ("momentum", "te_banking_momentum_icons", "banking_dash_momentum_tt", "$banking_dash_momentum_value$"),
    ("bubble", "te_banking_bubble_icons", "banking_dash_bubble_tt", "$banking_dash_bubble_value$"),
]
PHASES = ["panic", "downturn", "stagnation", "stable", "expansion", "boom", "frenzy"]


def _lines(path):
    return _read(path).splitlines()


def _children(block, kind="flowcontainer"):
    """The direct children of `kind` in a brace block, as blocks."""
    out, depth, i = [], 0, 1
    while i < len(block) - 1:
        c = block[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0 and block.startswith(f"{kind} = {{", i) and not (block[i - 1].isalnum() or block[i - 1] == "_"):
            child = _block_from(block, i)
            out.append(child)
            i += len(f"{kind} = ") + len(child)
            continue
        i += 1
    return out


def _own(block):
    """A block's own lines: the text outside its nested braces."""
    out, depth = [], 0
    for c in block[1:-1]:
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0:
            out.append(c)
    return "".join(out)


class OverrideTest(unittest.TestCase):
    """gui/topbar.gui is vanilla's file, changed only inside marked blocks."""

    def hunks(self):
        vanilla, mod = _lines(VANILLA), _lines(TOPBAR)
        ops = difflib.SequenceMatcher(None, vanilla, mod, autojunk=False).get_opcodes()
        return [(tag, vanilla[i1:i2], mod[j1:j2]) for tag, i1, i2, j1, j2 in ops if tag != "equal"]

    def test_both_carry_the_bom(self):
        for path in (TOPBAR, VANILLA):
            with open(path, "rb") as f:
                self.assertEqual(f.read(3), b"\xef\xbb\xbf", path)

    def test_every_change_is_marked(self):
        hunks = self.hunks()
        self.assertTrue(hunks, "the override changes nothing")
        for tag, old, new in hunks:
            with self.subTest(hunk=new[:1]):
                self.assertTrue(any(line.strip().startswith(MARK) for line in new),
                                f"unmarked {tag}: {old!r} -> {new!r}")

    def test_the_one_change_adds_the_readings_and_removes_nothing(self):
        hunks = self.hunks()
        self.assertEqual(len(hunks), 1)
        tag, old, new = hunks[0]
        self.assertEqual(tag, "insert")
        self.assertEqual(old, [])
        self.assertEqual([line.strip() for line in new if line.strip() and not line.strip().startswith("#")],
                         ["te_banking_topbar_readings = {}"])

    def test_the_readings_sit_after_money_in_the_primary_row(self):
        bar = _type_body(_read(TOPBAR), "topbar")
        named = _block_from(bar, bar.index("widget = {"))
        self.assertIn('name = "topbar"', _own(named))
        self.assertIn("using = hud_visibility", _own(named))   # hidden with the bar
        primary = _block_from(named, named.index("flowcontainer = {", named.index("### PRIMARY ICONS")))
        money = primary.index("container = {", primary.index("### MONEY"))
        money_end = money + len("container = ") + len(_block_from(primary, money))
        at = primary.index("te_banking_topbar_readings = {}")
        between = [line.strip() for line in primary[money_end:at].splitlines()]
        self.assertTrue(all(not line or line.startswith("#") for line in between),
                        "the readings follow the MONEY container directly")


class GateTest(unittest.TestCase):
    """Hidden in observer mode, while the Banking tab is closed to the player,
    and until the entry runs: one widget per gate, as budget_panel.gui nests
    them."""

    def setUp(self):
        self.body = "{" + _type_body(_read(DASH), "te_banking_topbar_readings") + "}"

    def test_three_nested_gates_then_the_readings(self):
        observer = _own(self.body)
        self.assertIn('visible = "[Not( GetMetaPlayer.IsObserver )]"', observer)
        tab, = _children(self.body)
        self.assertIn("GetScriptedGui('te_budget_banking_tab_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope )"
                      ".End )", _own(tab))
        self.assertNotRegex(_own(tab), r"\bdatacontext =")
        entry, = _children(tab)
        self.assertIn('datacontext = "[GetPlayerJournalEntry(\'je_banking_cycle\')]"', _own(entry))
        self.assertNotRegex(_own(entry), r"\bvisible =")
        running, = _children(entry)
        self.assertIn('visible = "[JournalEntry.IsActive]"', _own(running))
        self.assertEqual(len(re.findall(r"\bte_banking_topbar_reading = \{", running)), 3)

    def test_the_gate_is_the_budget_tabs(self):
        tab = _read(BUDGET)
        self.assertIn("GetScriptedGui('te_budget_banking_tab_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope )"
                      ".End )", tab)
        self.assertIn("GetPlayerJournalEntry('je_banking_cycle')", tab)
        self.assertIn("has_journal_entry = je_banking_cycle",
                      _read(os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")))


class ReuseTest(unittest.TestCase):
    """The readings draw the overview's icon types and name the overview's
    words and tooltips: no texture, band code or threshold of their own."""

    def setUp(self):
        self.dash = _read(DASH)
        self.body = _type_body(self.dash, "te_banking_topbar_readings")
        self.buttons = [_block_from(self.body, m.end() - 1)
                        for m in re.finditer(r"\bte_banking_topbar_reading = \{", self.body)]

    def test_each_reading_instances_the_overviews_icon_type(self):
        overview = _type_body(self.dash, "te_banking_overview_panel")
        self.assertEqual(len(self.buttons), len(READINGS))
        for button, (reading, icons, _, _) in zip(self.buttons, READINGS):
            with self.subTest(reading=reading):
                self.assertIn(f"{icons} = {{", button)
                self.assertRegex(_block_from(button, button.index(f"{icons} = {{")), r"size = \{ 28 28 \}")
                self.assertRegex(overview, rf'blockoverride "icons" \{{\s*{icons} = \{{\}}')

    def test_nothing_is_drawn_or_decided_here(self):
        for needle in ("texture =", "ScriptValue(", "CFixedPoint", "banking_dash_phase_", "Var("):
            self.assertNotIn(needle, self.body)

    def test_the_bubble_carries_the_overviews_crash_risk_badge(self):
        self.assertIn("te_banking_crash_risk_badge = {", self.buttons[2])
        overview = _type_body(self.dash, "te_banking_overview_panel")
        self.assertRegex(overview, r'blockoverride "badge" \{\s*te_banking_crash_risk_badge = \{')

    def test_a_click_opens_the_banking_tab(self):
        reading = _type_body(self.dash, "te_banking_topbar_reading")
        self.assertIn('onclick = "[InformationPanelBar.OpenPanelTab(\'budget\', \'te_banking\')]"', reading)
        self.assertIn("using = glow_button", reading)
        self.assertIn("using = tooltip_below", reading)
        self.assertIn("InformationPanel.SelectTab('te_banking')", _read(BUDGET))

    def test_narrower_than_one_vanilla_button(self):
        reading = _type_body(self.dash, "te_banking_topbar_reading")
        width = int(re.search(r"size = \{ (\d+) 40 \}", reading).group(1))
        running = _children(_children(_children("{" + self.body + "}")[0])[0])[0]
        spacing = int(re.search(r"spacing = (\d+)", _own(running)).group(1))
        self.assertLessEqual(3 * width + 2 * spacing, 100)

    def test_each_tooltip_is_the_word_then_the_overviews_tooltip(self):
        loc = _loc()
        for button, (reading, _, overview_tt, word) in zip(self.buttons, READINGS):
            with self.subTest(reading=reading):
                key = re.search(r'tooltip = "(\w+)"', _own(button)).group(1)
                self.assertEqual(key, f"banking_dash_top_{reading}_tt")
                header = re.match(r"(#header [^#]+#!)\\n\$(\w+)\$$", loc[overview_tt])
                self.assertIsNotNone(header, f"{overview_tt} is its header and its body")
                self.assertEqual(header.group(2), f"{overview_tt}_body")
                self.assertIn(header.group(2), loc)
                self.assertEqual(loc[key], f"{header.group(1)}\\n{word}\\n$TOOLTIP_DELIMITER$\\n${header.group(2)}$")

    def test_the_momentum_and_bubble_words_are_the_overviews(self):
        overview = _type_body(self.dash, "te_banking_overview_panel")
        for key in ("banking_dash_momentum_value", "banking_dash_bubble_value"):
            self.assertIn(f'text = "{key}"', overview)


class PhaseWordTest(unittest.TestCase):
    """The phase word the top bar's tooltip prints asks each phase's question
    through the overview's scripted GUI's own trigger, and names its word."""

    def test_the_word_follows_the_phase_scripted_guis(self):
        custom = _read(CUSTOM_LOC)
        block = _block_from(custom, re.search(r"(?m)^banking_dash_phase_word = \{", custom).end() - 1)
        branches = re.findall(r"text = \{\s*trigger = \{(.*?)\}\s*localization_key = (\w+)\s*\}", block, re.S)
        unknown, branches = branches[0], branches[1:]
        self.assertEqual(" ".join(unknown[0].split()), "NOT = { has_variable = finance_cycle_value }")
        self.assertEqual(unknown[1], "banking_dash_band_unknown")
        self.assertEqual([k for _, k in branches], [f"banking_dash_phase_{p}_value" for p in PHASES])
        for (trigger, _), phase in zip(branches, PHASES):
            with self.subTest(phase=phase):
                self.assertEqual(" ".join(trigger.split()), f"banking_cycle_is_{phase} = yes")
                self.assertIn(f"banking_cycle_is_{phase} = yes", _sgui(f"banking_dash_phase_{phase}"))

    def test_every_word_exists(self):
        loc = _loc()
        for phase in PHASES:
            self.assertIn(f"banking_dash_phase_{phase}_value", loc)
        self.assertIn("banking_dash_band_unknown", loc)
        self.assertTrue(os.path.exists(LOC) and os.path.exists(SGUIS))


if __name__ == "__main__":
    unittest.main()
