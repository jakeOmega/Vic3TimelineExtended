"""The Banking readings in vanilla's top bar (gui/topbar.gui).

The owner asked for the cycle's phase, momentum and bubble pressure in the top
bar itself, as bands: icons after MONEY, each its own hover and click target,
the phase on the bar's top row and the other two beneath it on the second. This
checks that the override is vanilla's file plus two marked changes (the
readings and the bar's declared width), that the declared width covers the
widest bar so the alerts beside it cannot sit on the readings again, that the
two rows line up with vanilla's and add no height, that the readings are gated
like the Budget panel's Banking tab, and that they draw the overview's own
icons and tooltips rather than a copy.
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
    """The readings' blocks: the top row, the bottom row, the three buttons."""

    def __init__(self):
        self.dash = _read(DASH)
        self.body = "{" + _type_body(self.dash, "te_banking_topbar_readings") + "}"
        self.top = _children(self.body, "widget")[0]
        self.gates = _instances(self.body, "te_banking_topbar_gate")
        self.bottom_gate = self.gates[1]
        self.pair = _block_from(self.bottom_gate, self.bottom_gate.index("flowcontainer = {"))
        self.buttons = _instances(self.body, "te_banking_topbar_reading")


class GateTest(unittest.TestCase):
    """Hidden in observer mode, while the Banking tab is closed to the player,
    and until the entry runs: one widget per gate, as budget_panel.gui nests
    them, for each row."""

    def test_three_nested_gates_then_the_row(self):
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

    def test_every_reading_is_behind_a_gate(self):
        r = Readings()
        self.assertEqual(len(r.gates), 2)
        inside = sum(len(_instances(g, "te_banking_topbar_reading")) for g in r.gates)
        self.assertEqual(inside, 3)
        self.assertEqual(len(r.buttons), 3)
        self.assertNotRegex(_own(r.body), r"\bvisible =")    # the top row's 80 stay: see GeometryTest
        self.assertNotRegex(_own(r.top), r"\bvisible =")

    def test_the_gate_is_the_budget_tabs(self):
        tab = _read(BUDGET)
        self.assertIn("GetScriptedGui('te_budget_banking_tab_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope )"
                      ".End )", tab)
        self.assertIn("GetPlayerJournalEntry('je_banking_cycle')", tab)
        self.assertIn("has_journal_entry = je_banking_cycle",
                      _read(os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")))


class GeometryTest(unittest.TestCase):
    """The bar's declared width covers its widest content, so ingame_hud.gui's
    hbox puts the alerts after the readings (#588 put them under the alerts),
    and the two rows line up with vanilla's without making the bar taller.
    Every number is read from the markup."""

    @classmethod
    def setUpClass(cls):
        text = _read(TOPBAR)
        bar = _type_body(text, "topbar")
        cls.named = _block_from(bar, bar.index("widget = {"))
        cls.outer = _block_from(cls.named, cls.named.index("flowcontainer = {"))
        cls.primary = _block_from(cls.named, cls.named.index("flowcontainer = {", cls.named.index("### PRIMARY ICONS")))
        cls.secondary = "{" + _type_body(text, "topbar_secondary_icons") + "}"
        cls.secondary_icon = int(re.search(r"@secondary_icon_size = (\d+)", text).group(1))
        cls.r = Readings()

        cls.spacing = int(re.search(r'block "spacing" \{\s*spacing = (\d+)', cls.primary).group(1))
        supply_at = cls.primary.index('block "supply_ships_info" {')
        supply = _block_from(cls.primary, supply_at)
        buttons = [(m.start(), _block_from(cls.primary, m.end() - 1))
                   for m in re.finditer(r"\bbutton = \{", cls.primary)]
        glow = [(at, b) for at, b in buttons if "using = glow_button" in _own(b)]
        cls.widths = [_size(b)[0] for _, b in glow]
        cls.supply_width = sum(_size(b)[0] for at, b in glow if supply_at < at < supply_at + len(supply) + 30)
        cls.first_icon = _block_from(glow[0][1], glow[0][1].index("icon = {"))

    def start(self, landlocked):
        """Where the readings start: after the capacities, supply ships and
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
        reserved = _size(self.r.top)[0]
        right = _int(self.outer, "margin_right")
        widest = max(self.start(False), self.start(True)) + reserved + right
        self.assertEqual(width, -(-widest // 5) * 5, "the widest case, rounded up to a multiple of 5")

    def test_the_lock_toggle_clears_the_bottom_row(self):
        toggle = _block_from(self.named, self.named.index("button_icon_round_toggle = {"))
        self.assertIn("parentanchor = bottom|right", _own(toggle))
        tw, th = _size(toggle)
        tx, ty = _position(toggle)
        width, height = _size(self.named)
        left = width + tx - tw
        pair_right = _int(self.r.pair, "margin_left") + 2 * _size(self.r.buttons[1])[0] + _int(self.r.pair, "spacing")
        for landlocked in (False, True):
            with self.subTest(landlocked=landlocked):
                self.assertGreaterEqual(left - (self.start(landlocked) + pair_right), 2)

    def test_the_bottom_row_clears_the_secondary_row(self):
        items = [int(w) for w, h in re.findall(r"minimumsize = \{ (\d+) (\d+) \}", self.secondary)]
        background = _block_from(self.secondary, self.secondary.index("background = {"))
        end = _position(self.secondary)[0] + sum(items) + _int(background, "margin_right")
        self.assertEqual(end, 676)
        first = min(self.start(False), self.start(True)) + _int(self.r.pair, "margin_left")
        self.assertGreaterEqual(first - end, 2, "tight: the landlocked bar leaves this gap")

    def test_the_rows_line_up_with_vanillas_and_add_no_height(self):
        py = _position(self.primary)[1]
        top_h = _size(self.r.top)[1]
        phase, momentum, bubble = self.r.buttons
        # top row: vanilla's primary buttons are 40 high, their icons 32, 2 down from centre
        self.assertEqual(top_h, 40)
        self.assertEqual(_size(phase)[1], 40)
        icon = _block_from(phase, phase.index("te_banking_phase_icons = {"))
        self.assertEqual(_size(icon), _size(self.first_icon))
        self.assertEqual(_position(icon), _position(self.first_icon))
        # bottom row: the secondary row's icons, at the locked row's y
        locked_y = int(re.search(r'blockoverride "animation" \{\s*position = \{ 0 (\d+) \}', self.named).group(1))
        item_h = int(re.search(r"minimumsize = \{ \d+ (\d+) \}", self.secondary).group(1))
        vanilla_icon_y = locked_y + (item_h - self.secondary_icon) // 2
        for button, name in ((momentum, "te_banking_momentum_icons"), (bubble, "te_banking_bubble_icons")):
            with self.subTest(icons=name):
                icon = _block_from(button, button.index(f"{name} = {{"))
                self.assertEqual(_size(icon), (self.secondary_icon, self.secondary_icon))
                self.assertEqual(py + top_h + _position(icon)[1], vanilla_icon_y)
        # no taller: the primary row ends where the locked secondary row does
        bottom_h = _size(momentum)[1]
        self.assertLessEqual(py + top_h + bottom_h + _int(self.primary, "margin_bottom"), locked_y + item_h)

    def test_the_phase_is_centred_over_the_pair(self):
        phase_gate = _instances(self.r.top, "te_banking_topbar_gate")[0]
        phase_w = _size(self.r.buttons[0])[0]
        pair_w = 2 * _size(self.r.buttons[1])[0] + _int(self.r.pair, "spacing")
        self.assertEqual(_position(phase_gate)[0] + phase_w / 2, _int(self.r.pair, "margin_left") + pair_w / 2)
        self.assertLessEqual(_position(phase_gate)[0] + phase_w, _size(self.r.top)[0])


class ReuseTest(unittest.TestCase):
    """The readings draw the overview's icon types and name the overview's
    words and tooltips: no texture, band code or threshold of their own."""

    def setUp(self):
        self.r = Readings()
        self.dash = self.r.dash
        self.body = self.r.body
        self.buttons = self.r.buttons

    def test_each_reading_instances_the_overviews_icon_type(self):
        overview = _type_body(self.dash, "te_banking_overview_panel")
        self.assertEqual(len(self.buttons), len(READINGS))
        for button, (reading, icons, _, _), px in zip(self.buttons, READINGS, (32, 26, 26)):
            with self.subTest(reading=reading):
                self.assertIn(f"{icons} = {{", button)
                self.assertEqual(_size(_block_from(button, button.index(f"{icons} = {{"))), (px, px))
                self.assertRegex(overview, rf'blockoverride "icons" \{{\s*{icons} = \{{\}}')

    def test_nothing_is_drawn_or_decided_here(self):
        for body in (self.body, _type_body(self.dash, "te_banking_topbar_gate")):
            for needle in ("texture =", "ScriptValue(", "CFixedPoint", "banking_dash_phase_", "Var("):
                self.assertNotIn(needle, body)

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
