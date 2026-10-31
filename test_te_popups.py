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

    def test_the_header_closes_on_escape(self):
        # Vanilla's close button carries shortcut = "close_window"
        # (frontend/shared/buttons.gui, buttons_window_control's close_button).
        header = _child(self.shell, "header_pattern = {")
        close = _child(header, 'blockoverride "button_close" {')
        self.assertIn(CLEAR, close)

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


if __name__ == "__main__":
    unittest.main()
