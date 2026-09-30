"""The Banking phase in vanilla's top bar (gui/topbar.gui).

The owner asked for Banking readings in the top bar itself, as bands, and then
for the phase alone: one icon after MONEY, level with vanilla's primary icons,
with its word and the overview's tooltip on hover and the Banking tab on a
click. This checks that the override is vanilla's file plus two marked changes
(the phase and the bar's declared width), that the declared width covers the
widest bar so the alerts beside it cannot sit on the phase again (#588's
three icons were under them), that the phase lines up with vanilla's icons and
adds no height, that it is gated like the Budget panel's Banking tab, and that
it draws the overview's own icon and tooltip rather than a copy.
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

PHASE_WORD = "[JournalEntry.GetCountry.GetCustom('banking_dash_phase_word')]"
CRASH_RISK = ("[AddLocalizationIf( GetScriptedGui('banking_dash_bubble_risk_high').IsShown( GuiScope.SetRoot( "
              "JournalEntry.GetCountry.MakeScope ).End ), 'banking_dash_ov_crash_risk_tt' )]")
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
    """A block's own lines: the text outside its nested blocks. A one-line
    value in braces (`size = { 26 26 }`) stays."""
    out, i, inner = [], 0, block[1:-1]
    while i < len(inner):
        if inner[i] == "{":
            nested = _block_from(inner, i)
            if "\n" not in nested:
                out.append(nested)
            i += len(nested)
            continue
        out.append(inner[i])
        i += 1
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

    def test_two_changes_the_width_and_the_readings(self):
        def code(lines):
            return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
        hunks = self.hunks()
        self.assertEqual(len(hunks), 2)
        (tag, old, new), (tag2, old2, new2) = hunks
        self.assertEqual(tag, "replace")
        self.assertEqual(code(old), ["size = { 705 80 }"])
        self.assertRegex(" ".join(code(new)), r"^size = \{ \d+ 80 \}$")
        self.assertEqual(tag2, "insert")
        self.assertEqual(old2, [])
        self.assertEqual(code(new2), ["te_banking_topbar_readings = {}"])

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


# ingame_hud.gui (vanilla, not in the repo) instances the bar twice: with
# supply ships, and landlocked with blockoverride "supply_ships_info" {} and
# blockoverride "spacing" { spacing = 37 }.
LANDLOCKED_SPACING = 37


def _size(block):
    return tuple(int(n) for n in re.search(r"size = \{ (-?\d+) (-?\d+) \}", _own(block)).groups())


def _position(block):
    m = re.search(r"position = \{ (-?\d+) (-?\d+) \}", _own(block))
    return tuple(int(n) for n in m.groups()) if m else (0, 0)


def _int(block, prop):
    return int(re.search(rf"\b{prop} = (-?\d+)", _own(block)).group(1))


def _instances(block, name):
    return [_block_from(block, m.end() - 1) for m in re.finditer(rf"\b{name} = \{{", block)]


class Readings:
    """The top bar's Banking type: the reserved widget and the phase button."""

    def __init__(self):
        self.dash = _read(DASH)
        self.body = "{" + _type_body(self.dash, "te_banking_topbar_readings") + "}"
        self.gates = _instances(self.body, "te_banking_topbar_gate")
        self.buttons = _instances(self.body, "te_banking_topbar_reading")
        self.phase = self.buttons[0]
        self.icon = _block_from(self.phase, self.phase.index("te_banking_phase_icons = {"))
        # the button's size: the instance's, or else its type's
        button_type = "{" + _type_body(self.dash, "te_banking_topbar_reading") + "}"
        own = re.search(r"size = \{", _own(self.phase))
        self.phase_size = _size(self.phase if own else button_type)


class GateTest(unittest.TestCase):
    """Hidden in observer mode, while the Banking tab is closed to the player,
    and until the entry runs: one widget per gate, as budget_panel.gui nests
    them."""

    def test_three_nested_gates_then_the_phase(self):
        gate = "{" + _type_body(_read(DASH), "te_banking_topbar_gate") + "}"
        self.assertIn('visible = "[Not( GetMetaPlayer.IsObserver )]"', _own(gate))
        tab, = _children(gate)
        self.assertIn("GetScriptedGui('te_budget_banking_tab_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope )"
                      ".End )", _own(tab))
        self.assertNotRegex(_own(tab), r"\bdatacontext =")
        entry, = _children(tab)
        self.assertIn('datacontext = "[GetPlayerJournalEntry(\'je_banking_cycle\')]"', _own(entry))
        self.assertNotRegex(_own(entry), r"\bvisible =")
        running, = _children(entry)
        self.assertIn('visible = "[JournalEntry.IsActive]"', _own(running))
        self.assertIn('block "readings" {}', running)

    def test_the_phase_is_behind_the_gate_and_the_widget_is_not(self):
        r = Readings()
        self.assertEqual(len(r.gates), 1)
        self.assertEqual(len(r.buttons), 1)
        self.assertEqual(len(_instances(r.gates[0], "te_banking_topbar_reading")), 1)
        self.assertNotRegex(_own(r.body), r"\bvisible =")    # its 40 stay: see GeometryTest

    def test_the_gate_is_the_budget_tabs(self):
        tab = _read(BUDGET)
        self.assertIn("GetScriptedGui('te_budget_banking_tab_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope )"
                      ".End )", tab)
        self.assertIn("GetPlayerJournalEntry('je_banking_cycle')", tab)
        self.assertIn("has_journal_entry = je_banking_cycle",
                      _read(os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")))


class GeometryTest(unittest.TestCase):
    """The bar's declared width covers its widest content, so ingame_hud.gui's
    hbox puts the alerts after the phase (#588 put its icons under them), and
    the phase lines up with vanilla's icons without making the bar taller.
    Every number is read from the markup."""

    @classmethod
    def setUpClass(cls):
        text = _read(TOPBAR)
        bar = _type_body(text, "topbar")
        cls.named = _block_from(bar, bar.index("widget = {"))
        cls.outer = _block_from(cls.named, cls.named.index("flowcontainer = {"))
        cls.primary = _block_from(cls.named, cls.named.index("flowcontainer = {", cls.named.index("### PRIMARY ICONS")))
        cls.r = Readings()

        cls.spacing = int(re.search(r'block "spacing" \{\s*spacing = (\d+)', cls.primary).group(1))
        supply_at = cls.primary.index('block "supply_ships_info" {')
        supply = _block_from(cls.primary, supply_at)
        buttons = [(m.start(), _block_from(cls.primary, m.end() - 1))
                   for m in re.finditer(r"\bbutton = \{", cls.primary)]
        cls.glow = [(at, b) for at, b in buttons if "using = glow_button" in _own(b)]
        cls.widths = [_size(b)[0] for _, b in cls.glow]
        cls.supply_width = sum(_size(b)[0] for at, b in cls.glow if supply_at < at < supply_at + len(supply) + 30)
        cls.first_icon = _block_from(cls.glow[0][1], cls.glow[0][1].index("icon = {"))

    def start(self, landlocked):
        """Where the phase starts: after the capacities, supply ships and
        MONEY, with a gap before each child of the row and inside the
        capacities' own row."""
        x = _position(self.primary)[0]
        if landlocked:
            return x + sum(self.widths) - self.supply_width + 4 * LANDLOCKED_SPACING
        return x + sum(self.widths) + 5 * self.spacing

    def test_the_widest_case_is_as_briefed(self):
        self.assertEqual(len(self.widths), 5)
        self.assertEqual(self.start(False), 130 + 5 * 100 + 5 * 12)
        self.assertEqual(self.start(True), 130 + 4 * 100 + 4 * 37)

    def test_the_declared_width_covers_the_widest_bar(self):
        width, height = _size(self.named)
        self.assertEqual(height, 80)
        reserved = _size(self.r.body)[0]
        right = _int(self.outer, "margin_right")
        widest = max(self.start(False), self.start(True)) + reserved + right
        self.assertEqual(width, -(-widest // 5) * 5, "the widest case, rounded up to a multiple of 5")

    def test_the_lock_toggle_is_below_the_phase(self):
        """The toggle is anchored to the declared size's bottom-right corner,
        so it moves with the width: onto the bottom row, under the phase."""
        toggle = _block_from(self.named, self.named.index("button_icon_round_toggle = {"))
        self.assertIn("parentanchor = bottom|right", _own(toggle))
        tw, th = _size(toggle)
        tx, ty = _position(toggle)
        width, height = _size(self.named)
        top = height + ty - th
        phase_bottom = _position(self.primary)[1] + self.r.phase_size[1]
        self.assertGreaterEqual(top - phase_bottom, 2)

    def test_the_phase_lines_up_with_vanillas_icons_and_adds_no_height(self):
        self.assertEqual(_size(self.r.body), (self.r.phase_size[0], 40))
        self.assertEqual(self.r.phase_size[1], _size(self.glow[0][1])[1])       # 40, a primary button's height
        self.assertEqual(_size(self.r.icon), _size(self.first_icon))            # 32
        self.assertEqual(_position(self.r.icon), _position(self.first_icon))    # 2 below centre


class ReuseTest(unittest.TestCase):
    """The phase draws the overview's icon type and names the overview's word
    and tooltip: no texture, band code or threshold of its own."""

    def setUp(self):
        self.r = Readings()
        self.dash = self.r.dash

    def test_the_phase_instances_the_overviews_icon_type(self):
        overview = _type_body(self.dash, "te_banking_overview_panel")
        self.assertRegex(overview, r'blockoverride "icons" \{\s*te_banking_phase_icons = \{\}')

    def test_only_the_phase(self):
        body = self.r.body + _type_body(self.dash, "te_banking_topbar_gate")
        for gone in ("te_banking_momentum_icons", "te_banking_bubble_icons", "te_banking_crash_risk_badge"):
            self.assertNotIn(gone, body)
        loc = _loc()
        for gone in ("banking_dash_top_momentum_tt", "banking_dash_top_bubble_tt"):
            self.assertNotIn(gone, loc)

    def test_nothing_is_drawn_or_decided_here(self):
        for body in (self.r.body, _type_body(self.dash, "te_banking_topbar_gate")):
            for needle in ("texture =", "ScriptValue(", "CFixedPoint", "banking_dash_phase_", "Var("):
                self.assertNotIn(needle, body)

    def test_a_click_opens_the_banking_tab(self):
        reading = _type_body(self.dash, "te_banking_topbar_reading")
        self.assertIn('onclick = "[InformationPanelBar.OpenPanelTab(\'budget\', \'te_banking\')]"', reading)
        self.assertIn("using = glow_button", reading)
        self.assertIn("using = tooltip_below", reading)
        self.assertIn("InformationPanel.SelectTab('te_banking')", _read(BUDGET))

    def test_the_tooltip_is_the_word_the_crash_risk_then_the_overviews_tooltip(self):
        loc = _loc()
        key = re.search(r'tooltip = "(\w+)"', _own(self.r.phase)).group(1)
        self.assertEqual(key, "banking_dash_top_phase_tt")
        header = re.match(r"(#header [^#]+#!)\\n\$(\w+)\$$", loc["banking_dash_phase_tt"])
        self.assertIsNotNone(header, "banking_dash_phase_tt is its header and its body")
        self.assertEqual(header.group(2), "banking_dash_phase_tt_body")
        self.assertIn(header.group(2), loc)
        self.assertEqual(loc[key],
                         f"{header.group(1)}\\n{PHASE_WORD} {CRASH_RISK}\\n$TOOLTIP_DELIMITER$\\n${header.group(2)}$")

    def test_the_crash_risk_line_is_the_overviews_badge(self):
        badge = _type_body(self.dash, "te_banking_crash_risk_badge")
        self.assertIn("GetScriptedGui('banking_dash_bubble_risk_high').IsShown( GuiScope.SetRoot( "
                      "JournalEntry.GetCountry.MakeScope ).End )", badge)
        self.assertIn('tooltip = "banking_dash_ov_crash_risk_tt"', badge)


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
