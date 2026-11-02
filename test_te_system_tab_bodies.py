"""The shared system-tab frame and the tab bodies built on it
(gui/te_system_tab_widgets.gui; spec
docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 9.1).

One shape for every journal-entry tab, in the window and in the vanilla
panels that host a system's tab: the header, the tab's gate on a parent of the
GetPlayerJournalEntry datacontext (gotcha #29), a fixed 520 column, the
content, and Open Journal Entry. Each body type derives from the frame and
fills its blocks, so two hosts of one tab can't drift apart.
"""
import os
import re
import unittest

from test_te_systems_window import _close, _read, _strip_comments, _type_body

REPO = os.path.dirname(os.path.abspath(__file__))
WIDGETS = os.path.join(REPO, "gui", "te_system_tab_widgets.gui")

OPEN_JOURNAL = "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]"


def _children(body):
    """The top-level items of a block's body, in order: (kind, name, text).
    kind is "block" for `block "x" {…}`, "widget" for `name = {…}`, and
    "property" for a one-line `key = value`."""
    items = []
    i = 0
    while i < len(body):
        m = re.compile(r'\s*(?:block "(\w+)" \{|(\w+) = \{|(\w+) = ([^\n{]+))').match(body, i)
        if not m or m.end() == i:
            rest = body[i:].strip()
            assert not rest, f"unparsed: {rest[:60]}"
            break
        if m.group(1) or m.group(2):
            end = _close(body, m.end() - 1)
            inner = body[m.end():end]
            if m.group(2) and "\n" not in inner:    # a one-line value: size = { 480 32 }
                items.append(("property", m.group(2), "{" + inner + "}"))
            else:
                items.append(("block" if m.group(1) else "widget", m.group(1) or m.group(2), inner))
            i = end + 1
        else:
            items.append(("property", m.group(3), m.group(4).strip()))
            i = m.end()
    return items


class FrameTest(unittest.TestCase):
    """te_system_tab_frame: the shape every frame-based tab body shares."""

    @classmethod
    def setUpClass(cls):
        cls.body = _strip_comments(_type_body(_read(WIDGETS), "te_system_tab_frame"))

    def test_the_frame_shape(self):
        self.assertRegex(_read(WIDGETS), r"type te_system_tab_frame = flowcontainer \{")
        top = _children(self.body)
        # the header, then what goes before the gate (Banking's readout), then the gate
        blocks = [name for kind, name, _ in top if kind == "block"]
        self.assertEqual(blocks, ["tab_header", "tab_before_gate"])
        widgets = [(name, text) for kind, name, text in top if kind == "widget"]
        self.assertEqual([name for name, _ in widgets], ["flowcontainer"])
        names = [name for _, name, _ in top]
        self.assertLess(names.index("tab_before_gate"), names.index("flowcontainer"))
        self.assertNotIn("visible", names)   # the root's visible is the instance's
        # the gate: on the parent's own properties, never with the datacontext
        gate = _children(widgets[0][1])
        own = [(kind, name) for kind, name, _ in gate if kind != "widget"]
        self.assertIn(("block", "tab_gate"), own)
        self.assertNotIn("datacontext", [name for _, name in own])
        inner = [text for kind, name, text in gate if kind == "widget"]
        self.assertEqual(len(inner), 1)
        # the entry's column: its datacontext block, a fixed 520, the content,
        # then the link
        column = _children(inner[0])
        self.assertEqual([name for kind, name, _ in column if kind == "block"],
                         ["tab_entry", "tab_content", "tab_open_journal"])
        self.assertIn(("property", "minimumsize", "{ 520 -1 }"), column)
        self.assertNotIn("visible", [name for kind, name, _ in column if kind == "property"])
        link = [text for kind, name, text in column if kind == "block" and name == "tab_open_journal"][0]
        self.assertEqual([name for kind, name, _ in _children(link)], ["button"])

    def test_the_link(self):
        """Open Journal Entry: shown while the entry runs, at the width every
        host uses, with its font and tooltip left to the body."""
        m = re.search(r'block "tab_open_journal" \{', self.body)
        self.assertTrue(m)
        link = self.body[m.end():_close(self.body, m.end() - 1)]
        button = _children(link)[0][2]
        for line in ('visible = "[JournalEntry.IsActive]"', "using = default_button", "size = { 480 32 }",
                     'text = "te_system_tab_open_journal"', f'onclick = "{OPEN_JOURNAL}"',
                     'block "tab_open_journal_font" {}', 'block "tab_open_journal_tooltip" {}'):
            self.assertIn(line, button)
        # the font block after default_button, so a body's font wins
        self.assertLess(button.index("using = default_button"), button.index('block "tab_open_journal_font"'))


if __name__ == "__main__":
    unittest.main()
