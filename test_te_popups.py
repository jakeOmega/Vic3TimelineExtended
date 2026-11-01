"""The mod's centred popups (Space Race UI pass design § 3,
docs/superpowers/specs/2026-10-31-space-race-ui-pass-design.md).

One scripted widget root, te_popups (gui/te_popups.gui), on the popups layer,
instances one popup type per picker. Each popup derives from the widget
library's shell, te_ui_popup (gui/te_widget_library.gui), which dims the screen,
closes on a click outside and on Escape, and holds the picker's list in a
scrollarea. Which popup is open is the client-side te_popup key.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(REPO, "gui", "te_widget_library.gui")
POPUPS = os.path.join(REPO, "gui", "te_popups.gui")
REGISTRATION = os.path.join(REPO, "gui", "scripted_widgets", "te_systems_window.txt")
SR_WIDGET = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
# The per-slot popup bodies and the fleet rows (gen_space_fleets.py).
SR_FLEET_ROWS = os.path.join(REPO, "gui", "journal_entry_widgets", "sr_fleets_generated_rows.gui")
SLOTS = 9  # gen_space_fleets.SLOTS
SR_GATE = ("GetScriptedGui('te_window_space_race_solar_colonization_sgui').IsShown( "
           "GuiScope.SetRoot( GetPlayer.MakeScope ).End )")
SR_CONTEXT = "datacontext = \"[GetPlayerJournalEntry('je_space_race_solar_colonization')]\""
CLEAR = "onclick = \"[GetVariableSystem.Clear('te_popup')]\""
ROOT_VISIBLE = ("[And( And( GetMetaPlayer.GetPlayedOrObservedCountry.IsValid, Not( GetMetaPlayer.IsObserver ) ), "
                "GetVariableSystem.Exists('te_popup') )]")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    out = []
    for line in text.split("\n"):
        quoted = False
        for i, ch in enumerate(line):
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return text[m.end():_close(text, m.end() - 1)]


def _top_level(text, name):
    """A top-level widget (a registered root) by its name."""
    for m in re.finditer(r"^(\w+) = \{$", text, re.M):
        brace = text.index("{", m.start())
        block = text[m.start():_close(text, brace) + 1]
        if re.search(rf'^\tname = "{name}"$', block, re.M):
            return block
    raise AssertionError(f"no top-level widget {name}")


def _child(text, opener):
    """The first block opened by `opener` (e.g. 'scrollarea = {'), braces included."""
    i = text.index(opener)
    return text[i:_close(text, i + len(opener) - 1) + 1]


class PopupTypeTest(unittest.TestCase):
    """te_ui_popup, the shell every picker derives from (design § 3)."""

    @classmethod
    def setUpClass(cls):
        cls.shell = _type_body(_strip_comments(_read(LIBRARY)), "te_ui_popup")

    def test_the_shell_dims_and_closes_on_a_click_outside(self):
        self.assertIn("using = Background_Full_Dim", self.shell)
        # The full-size button behind the body comes first, so the body draws over it.
        behind = re.search(r"button_normal = \{\s*size = \{ 100% 100% \}\s*" + re.escape(CLEAR), self.shell)
        self.assertIsNotNone(behind, "no full-size close button behind the body")
        body = re.search(r"\twidget = \{\s*parentanchor = center", self.shell)
        self.assertIsNotNone(body, "no centred body")
        self.assertLess(behind.start(), body.start())
        self.assertIn("alwaystransparent = no", self.shell[body.start():])

    def test_the_header_close_button_closes(self):
        # Escape comes with it: vanilla's close button carries
        # shortcut = "close_window" (frontend/shared/buttons.gui,
        # buttons_window_control's close_button), and the override sets only
        # the click.
        header = _child(self.shell, "header_pattern = {")
        close = _child(header, 'blockoverride "button_close" {')
        self.assertIn(CLEAR, close)
        self.assertNotIn("shortcut", close)

    def test_the_shell_keeps_the_mouse_from_the_screen_behind(self):
        self.assertRegex(self.shell, r"(?m)^\t\tfilter_mouse = left\|right\|wheel$")

    def test_the_blocks(self):
        for name in ("popup_visible", "popup_title", "popup_size", "popup_list", "popup_footer"):
            with self.subTest(block=name):
                self.assertEqual(self.shell.count(f'block "{name}"'), 1)
        self.assertIn('block "popup_list"', _child(self.shell, "scrollarea = {"))
        self.assertNotIn('block "popup_footer"', _child(self.shell, "scrollarea = {"))


class PopupRootTest(unittest.TestCase):
    def test_the_root_is_gated_and_on_the_popup_layer(self):
        root = _top_level(_strip_comments(_read(POPUPS)), "te_popups")
        self.assertRegex(root, r"(?m)^\tlayer = popups$")
        self.assertEqual(re.findall(r'(?m)^\tvisible = "(.*)"$', root), [ROOT_VISIBLE])

    def test_it_is_registered(self):
        self.assertIn("gui/te_popups.gui = te_popups", _strip_comments(_read(REGISTRATION)))

    def test_the_files_carry_one_bom(self):
        for path in (LIBRARY, POPUPS):
            with open(path, "rb") as f:
                head = f.read(6)
            with self.subTest(path=path):
                self.assertTrue(head.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(head[3:].startswith(b"\xef\xbb\xbf"))


def _popup_types(text):
    """Every Space Race popup: a type deriving from the shell."""
    return {m.group(1): _type_body(text, m.group(1))
            for m in re.finditer(r"type (te_sr_\w+_popup) = te_ui_popup \{", text)}


class PopupHostTest(unittest.TestCase):
    """The Space Race's popups (UI pass design §§ 3, 5)."""

    @classmethod
    def setUpClass(cls):
        cls.widget = _strip_comments(_read(SR_WIDGET))
        cls.popups = _popup_types(cls.widget)
        cls.root = _top_level(_strip_comments(_read(POPUPS)), "te_popups")

    def test_the_target_popup(self):
        body = self.popups["te_sr_target_popup"]
        self.assertRegex(body, r'blockoverride "popup_visible" \{\s*visible = '
                               r'"\[GetVariableSystem\.HasValue\(\'te_popup\', \'sr_target\'\)\]"\s*\}')
        self.assertIn("te_sr_target_popup_body = {}", body)
        self.assertIn('text = "je_space_race_widget_tp_title"', body)
        # An entry that closes under an open popup leaves a line, not an empty frame.
        self.assertIn(f'visible = "[Not( {SR_GATE} )]"', body)
        self.assertIn("je_space_race_widget_tp_gone", body)

    def test_the_transfer_popup(self):
        """A fleet's Transfer (UI pass design § 6): one popup type for the nine
        slots, up on any of their values; the bodies are generated, one a slot."""
        body = self.popups["te_sr_xfer_popup"]
        shown = _child(body, 'blockoverride "popup_visible" {')
        self.assertEqual(sorted(int(n) for n in re.findall(r"HasValue\('te_popup', 'sr_xfer_(\d)'\)", shown)),
                         list(range(1, 10)))
        self.assertIn("te_sr_xfer_popup_body = {}", body)
        self.assertIn('text = "je_space_race_widget_xf_title"', body)
        self.assertIn(f'visible = "[Not( {SR_GATE} )]"', body)

    def test_the_fleet_popups(self):
        """UI pass design §§ 4, 7: the destination and target popups, each one
        popup for nine slots, open on any slot's value; the body shows the open
        slot's (sr_fleets_generated_rows.gui)."""
        rows = _strip_comments(_read(SR_FLEET_ROWS))
        for popup, key, title in (("te_sr_dest_popup", "sr_dest", "dp_title"),
                                  ("te_sr_ftarget_popup", "sr_ftarget", "ft_title")):
            body = self.popups[popup]
            with self.subTest(popup=popup):
                visible = re.search(r'blockoverride "popup_visible" \{\s*visible = "(.*)"\s*\}', body).group(1)
                self.assertEqual(sorted(re.findall(rf"GetVariableSystem\.HasValue\('te_popup', '{key}_(\d)'\)", visible)),
                                 [str(n) for n in range(1, SLOTS + 1)])
                self.assertNotIn("And(", visible)
                self.assertIn(f"{popup}_body = {{}}", body)
                self.assertIn(f'text = "je_space_race_widget_{title}"', body)
                self.assertIn(f'visible = "[Not( {SR_GATE} )]"', body)
                slots = re.findall(rf"visible = \"\[GetVariableSystem\.HasValue\('te_popup', '{key}_(\d)'\)\]\"",
                                   _type_body(rows, f"{popup}_body"))
                self.assertEqual(slots, [str(n) for n in range(1, SLOTS + 1)])

    def test_the_pick_button_opens_the_popup(self):
        """A fleet row's destination button opens its slot's popup in place of
        stepping; it greys, with its reason, on sr_fleet_pick_sgui's is_valid."""
        rows = _strip_comments(_read(SR_FLEET_ROWS))
        fleet_rows = _type_body(rows, "te_sr_fleet_rows")
        found = []
        for m in re.finditer(r'blockoverride "fl_pick_button" \{', fleet_rows):
            found.append(fleet_rows[m.end():_close(fleet_rows, m.end() - 1)])
        self.assertEqual(len(found), SLOTS)
        for n, override in enumerate(found, 1):
            with self.subTest(slot=n):
                self.assertEqual(re.findall(r'onclick = "(.*)"', override),
                                 [f"[GetVariableSystem.Set('te_popup', 'sr_dest_{n}')]"])
                self.assertIn(f"enabled = \"[GetScriptedGui('sr_fleet_pick_sgui').IsValid( GuiScope.SetRoot( "
                              f"JournalEntry.GetCountry.MakeScope ).AddScope( 'op', MakeScopeValue( '(CFixedPoint){n}' ) ).End )]\"",
                              override)
                self.assertIn(f'tooltip = "je_space_race_widget_fl_{n}_leg_tt"', override)
                self.assertNotIn("Execute", override)

    def test_every_popup_is_in_the_root(self):
        self.assertTrue(self.popups)
        for name in self.popups:
            with self.subTest(popup=name):
                self.assertEqual(self.root.count(f"{name} = {{}}"), 1)

    def test_bodies_read_the_entry_through_get_player_journal_entry(self):
        """The scope-free gate on a parent, the datacontext on a child (gotchas
        #22 and #29), so the rows' JournalEntry.GetCountry reads resolve."""
        for name, body in self.popups.items():
            with self.subTest(popup=name):
                gate = body.index(f'visible = "[{SR_GATE}]"')
                context = body.index(SR_CONTEXT, gate)
                content = re.search(r"te_sr_\w+_popup_body = \{\}", body[context:])
                self.assertIsNotNone(content)
                # The datacontext's block holds the body.
                start = body.rindex("{", 0, context)
                self.assertGreater(_close(body, start), context + content.end())
                # The gate's block holds the datacontext's.
                gate_start = body.rindex("{", 0, gate)
                self.assertGreater(_close(body, gate_start), _close(body, start))


if __name__ == "__main__":
    unittest.main()
