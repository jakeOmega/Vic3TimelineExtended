"""The entry modifier strip on system tabs (#1383).

A modifier script puts on a journal entry (`je:je_<x> ?= { add_modifier = {
... } }`), or one the entry scales (`scaling_modifiers_while_active`), shows in
the journal window's header strip (vanilla's JournalEntry.GetTimedModifiers /
GetScalingModifiers row). A system tab draws the same strip,
te_je_modifier_strip (gui/te_system_tab_widgets.gui), under the entry's
GetPlayerJournalEntry datacontext: through the frame's tab_entry_modifiers
block, or, for a Space Race milestone, inside its own part.

This is the audit the issue asked for, as a test: every entry that carries
such a modifier and has a tab draws the strip there, and every entry with
such a modifier and no tab is listed in NO_TAB, so the list of entries whose
modifiers only the journal window shows stays written down.
"""
import functools
import glob
import os
import re
import unittest

from gui_test_helpers import _children, _close, _read, _strip_comments, _type_body

REPO = os.path.dirname(os.path.abspath(__file__))
WIDGETS = os.path.join(REPO, "gui", "te_system_tab_widgets.gui")
STRIP = "te_je_modifier_strip = {}"

# Entries script adds modifiers to that have no system tab: only the journal
# window shows their modifiers (2026-11-12). An entry that gets a tab leaves
# this list and draws the strip there.
NO_TAB = {
    "je_world_war": "no tab; the World War entry is the only panel",
    "je_civil_rights": "no tab",
    "je_world_climate": "no tab (the world's climate entry; its scaled global_warming modifier)",
}

# A parameterized `je:je_<prefix>$X$` site: the entries it can name.
PARAM_PREFIXES = ("je_space_race_",)


def _script_files():
    for sub in ("common", "events"):
        yield from glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True)


@functools.lru_cache(maxsize=None)
def entries_with_added_modifiers():
    """{entry or parameterized prefix: [file:line, ...]} for each `je:je_x = {`
    or `je:je_x ?= {` block that holds an add_modifier."""
    found = {}
    pattern = re.compile(r"je:(je_[A-Za-z0-9_$]+)\s*\??=\s*\{")
    for path in _script_files():
        raw = _read(path)
        if "je:je_" not in raw:
            continue
        text = _strip_comments(raw)
        for m in pattern.finditer(text):
            block = text[m.end():_close(text, m.end() - 1)]
            if "add_modifier" not in block:
                continue
            name = m.group(1)
            if "$" in name:
                name = name[:name.index("$")]
            line = text.count("\n", 0, m.start()) + 1
            found.setdefault(name, []).append(f"{os.path.relpath(path, REPO)}:{line}")
    return found


@functools.lru_cache(maxsize=None)
def entries_with_scaling_modifiers():
    found = set()
    for path in glob.glob(os.path.join(REPO, "common", "journal_entries", "*.txt")):
        text = _strip_comments(_read(path))
        for m in re.finditer(r"(?m)^(je_\w+)\s*=\s*\{", text):
            if "scaling_modifiers_while_active" in text[m.end():_close(text, m.end() - 1)]:
                found.add(m.group(1))
    return found


def _enclosing(text, at):
    """The opening-brace indices that enclose position `at`, innermost first."""
    stack = []
    for m in re.finditer(r"[{}]", text[:at]):
        if m.group() == "{":
            stack.append(m.start())
        else:
            stack.pop()
    return stack[::-1]


ENTRY_CONTEXT = re.compile(r"""^"\[GetPlayerJournalEntry\('(je_\w+)'\)\]"$""")


def _own_entry(items):
    """The entry a block's own items set: its datacontext, or the frame's
    tab_entry override."""
    for kind, name, value in items:
        if kind == "property" and name == "datacontext":
            m = ENTRY_CONTEXT.match(value)
            if m:
                return m.group(1)
        if kind == "blockoverride" and name == "tab_entry":
            for k, n, v in _children(value):
                if k == "property" and n == "datacontext" and ENTRY_CONTEXT.match(v):
                    return ENTRY_CONTEXT.match(v).group(1)
    return None


def strips_by_entry():
    """{entry: [file, ...]} for each te_je_modifier_strip instance, by the
    nearest entry datacontext around it."""
    out, orphans = {}, []
    for path in sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)):
        raw = _read(path)
        if STRIP not in raw:
            continue
        text = _strip_comments(raw)
        for m in re.finditer(re.escape(STRIP), text):
            entry = None
            for brace in _enclosing(text, m.start()):
                body = text[brace + 1:_close(text, brace)]
                try:
                    entry = _own_entry(_children(body))
                except AssertionError:    # a block _children can't read (not a GUI block)
                    entry = None
                if entry:
                    break
            rel = os.path.relpath(path, REPO)
            if entry:
                out.setdefault(entry, []).append(rel)
            else:
                orphans.append(rel)
    return out, orphans


def tab_entries():
    """Every entry a system tab reads: each GetPlayerJournalEntry a tab body's
    tab_entry override or a Space Race milestone's own part sets."""
    found = set()
    for path in glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True):
        raw = _read(path)
        if 'blockoverride "tab_entry"' not in raw:
            continue
        text = _strip_comments(raw)
        for m in re.finditer(r'blockoverride "tab_entry" \{\s*datacontext = "\[GetPlayerJournalEntry\(\'(je_\w+)\'\)\]"',
                             text):
            found.add(m.group(1))
    generated = _strip_comments(_read(os.path.join(REPO, "gui", "te_systems_window_generated.gui")))
    found |= set(re.findall(r"te_system_tab_frame = \{(?:(?!te_system_tab_frame = \{).)*?"
                            r"GetPlayerJournalEntry\('(je_space_race_\w+)'\)", generated, re.S))
    return found


class StripTypeTest(unittest.TestCase):
    def test_the_strip_is_vanillas_row_under_the_guard(self):
        body = _strip_comments(_type_body(_read(WIDGETS), "te_je_modifier_strip"))
        top = _children(body)
        self.assertIn(("property", "using", "te_own_country_only"), top)
        self.assertNotIn("visible", [n for k, n, _ in top if k == "property"])   # gotcha #17
        for model, item in (("GetScalingModifiers", "ScalingModifier"), ("GetTimedModifiers", "TimedModifier")):
            with self.subTest(model=model):
                self.assertIn(f'datamodel = "[JournalEntry.{model}]"', body)
                self.assertIn(f'tooltip = "[{item}.GetTooltip]"', body)
                self.assertIn(f'texture = "[{item}.GetIcon]"', body)


class StripCoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.strips, cls.orphans = strips_by_entry()
        cls.tabs = tab_entries()

    def test_every_strip_sits_under_an_entry(self):
        self.assertEqual(self.orphans, [], "a te_je_modifier_strip with no GetPlayerJournalEntry around it")

    def test_every_tab_draws_its_entrys_strip(self):
        self.assertGreaterEqual(len(self.tabs), 15)
        for entry in sorted(self.tabs):
            with self.subTest(entry=entry):
                self.assertIn(entry, self.strips, f"{entry}'s tab draws no te_je_modifier_strip")

    def test_every_entry_with_modifiers_is_shown_or_listed(self):
        carried = entries_with_added_modifiers()
        self.assertIn("je_cultural_hegemony", carried)    # the scan finds the known case (#1382)
        names = set(carried) | entries_with_scaling_modifiers()
        for name in sorted(names):
            with self.subTest(entry=name):
                if name in PARAM_PREFIXES:
                    shown = [e for e in self.strips if e.startswith(name)]
                    self.assertTrue(shown, f"no tab draws the strip for any {name}* entry")
                    continue
                self.assertTrue(name in self.strips or name in NO_TAB,
                                f"{name} carries modifiers ({carried.get(name, ['scaling'])[:3]}) that no tab "
                                "shows: give its tab te_je_modifier_strip, or list it in NO_TAB")

    def test_no_tab_is_live(self):
        carried = set(entries_with_added_modifiers()) | entries_with_scaling_modifiers()
        for name in NO_TAB:
            with self.subTest(entry=name):
                self.assertIn(name, carried, "it no longer carries modifiers: drop it from NO_TAB")
                self.assertNotIn(name, self.tabs, "it has a tab now: draw the strip there and drop it from NO_TAB")


if __name__ == "__main__":
    unittest.main()
