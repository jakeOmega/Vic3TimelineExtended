"""The Help pages (spec docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md
§§ 5.2, 7.5; plan docs/superpowers/plans/2026-11-02-charts-help-national-info.md, PRs H1
and H2).

Each system's "How X Works" section moved into a help body type,
te_<key>_help_body, which only its popup, te_<key>_help_popup, instances. The
popup derives from te_ui_help_popup (gui/te_widget_library.gui) and sits in the
te_popups root (gui/te_popups.gui), shown on te_popup = help_<key>. The section,
te_<system>_sec_how, keeps its name and its place in every composer, shrunk to
its header: a link that opens the page. Each tab's header carries a "?", a
te_help_button with the same onclick.

A help body reads only GetPlayer, never JournalEntry, so a page opens from any
host, whether or not the player holds the entry. That holds for the loc it
shows too, in English and in the translation memories deploy ships.

To move another section, add its row to PAGES.
"""
import collections
import glob
import json
import os
import re
import unittest

from gui_test_helpers import _children, _close, _read, _strip_comments, _type_body

REPO = os.path.dirname(os.path.abspath(__file__))
GUI_DIR = os.path.join(REPO, "gui")
LIBRARY = os.path.join(GUI_DIR, "te_widget_library.gui")
TAB_WIDGETS = os.path.join(GUI_DIR, "te_system_tab_widgets.gui")
POPUPS = os.path.join(GUI_DIR, "te_popups.gui")
LOC_DIR = os.path.join(REPO, "localization", "english")
# The translation memories: deploy ships their German and Spanish lines into the
# same popups (scripts/generators/gen_non_english_loc.py, i18n/README.md).
I18N_DIR = os.path.join(REPO, "i18n")

# Vanilla's gold question mark, shipped unused: a placeholder (style guide rule 10).
HELP_ICON = "gfx/interface/buttons/button_icons/unused/help.dds"

# One row a page.
#   key       the page: te_popup = help_<key>, te_<key>_help_body, te_<key>_help_popup
#   sections  the te_*_sec_how types that link to it (each keeps its place in the composers)
#   title     the section's header key: the link's text and the popup's title
#   flags     the collapse flags the move retired
#   tabs      the tab body types (te_system_tab_frame) whose headers carry the "?"
Page = collections.namedtuple("Page", "key sections title flags tabs")

PAGES = [
    Page("banking", ("te_banking_sec_how",), "banking_dash_how_header",
         ("banking_dash_how_open",), ("te_banking_tab_body",)),
    Page("grand_monuments", ("te_gm_sec_how",), "gm_je_how_header",
         ("gm_how_open",), ("te_gm_tab_body",)),
    Page("colonial_empire", ("te_ce_sec_how",), "je_colonial_empire_how_header",
         ("colonial_empire_how_open",), ("te_ce_tab_body",)),
]

def _open(key):
    return f"[GetVariableSystem.Set('te_popup', 'help_{key}')]"


def _gui_paths():
    return sorted(glob.glob(os.path.join(GUI_DIR, "**", "*.gui"), recursive=True))


def _all_types():
    """Every mod GUI type: name -> (base, body), comments cut."""
    types = {}
    for path in _gui_paths():
        text = _strip_comments(_read(path))
        for m in re.finditer(r"^\s*type (\w+) = (\w+) \{", text, re.M):
            types[m.group(1)] = (m.group(2), text[m.end():_close(text, m.end() - 1)])
    return types


def _closure(types, start):
    """The types a type reaches: itself, its bases and every type it
    instances, all the way down (mod types only)."""
    reached, todo = set(), [start]
    while todo:
        name = todo.pop()
        if name in reached or name not in types:
            continue
        reached.add(name)
        base, body = types[name]
        todo.append(base)
        todo += re.findall(r"\b(\w+) = \{", body)
    return reached


def _loc():
    """The mod's English loc, key -> value (the last file in name order wins, as in game)."""
    keys = {}
    for path in sorted(glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True)):
        if path.endswith("te_unused_l_english.yml"):
            continue
        for line in _read(path).splitlines():
            m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def _translations():
    """Every translation memory's text, key -> [(file, field, text)]: each
    record's English and its translation (a stale record ships its old
    translation, binding and all)."""
    out = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(I18N_DIR, "*", "tm", "**", "*.json"), recursive=True)):
        with open(path, encoding="utf-8") as f:
            records = json.load(f)
        rel = os.path.relpath(path, REPO)
        for key, record in records.items():
            for field, value in record.items():
                if isinstance(value, str) and field != "base":
                    out[key].append((rel, field, value))
    return out


# What a loc text reaches: a splice ($key$), a key quoted as a loc function's
# argument (Localize('key'), SelectLocalization( …, 'a', 'b' ), AddLocalizationIf,
# AddTextIf) and an inline tooltip (#tooltippable;tooltip:key).
_LOC_REFS = re.compile(r"\$(\w+)\$|'(\w+)'|tooltip:(\w+)")


def _keys_reached(text, loc, translations=None):
    """The loc keys a GUI text names (a quoted key, a quoted argument), and
    every key those reach (_LOC_REFS), in English or in a translation,
    recursively."""
    found = {k for k in re.findall(r"""["'](\w+)["']""", text) if k in loc}
    todo = list(found)
    while todo:
        key = todo.pop()
        texts = [loc[key]] + [value for _, _, value in (translations or {}).get(key, ())]
        for value in texts:
            for groups in _LOC_REFS.findall(value):
                k = next(g for g in groups if g)
                if k in loc and k not in found:
                    found.add(k)
                    todo.append(k)
    return found


# A popup sits in te_popups, a root with no datacontext: the only objects a
# page can read are the global ones. Every data chain in a page's markup and
# loc must start at one of these (a chain's head: a name followed by a dot,
# not itself after a dot). Functions (Localize(…), GetScriptedGui(…),
# Concept(…)) take no context. Country, JournalEntry, State, ScriptContainer
# and the host panels are what a page must not read.
GLOBAL_HEADS = {"GetPlayer", "GetMetaPlayer", "GetVariableSystem", "GuiScope", "PdxGuiWidget"}


def _chain_heads(text):
    """The heads of the data chains in a text's [ … ] expressions, quoted
    arguments left out."""
    heads = set()
    for expr in re.findall(r"\[([^\[\]]*)\]", text):
        expr = re.sub(r"'[^']*'", "''", expr)
        heads.update(re.findall(r"(?<![\w.])([A-Za-z_]\w*)\.", expr))
    return heads


def _override(body, name):
    m = re.search(rf'blockoverride "{name}" \{{', body)
    return None if m is None else body[m.end():_close(body, m.end() - 1)]


class ShellTest(unittest.TestCase):
    """The two shared types (plan Task H1.1)."""

    def test_the_shells(self):
        library = _strip_comments(_read(LIBRARY))
        self.assertRegex(library, r"(?m)^\ttype te_ui_help_popup = te_ui_popup \{")
        popup = _children(_type_body(library, "te_ui_help_popup"))
        self.assertEqual([(kind, name) for kind, name, _ in popup], [("blockoverride", "popup_size")])
        self.assertEqual(popup[0][2].strip(), "size = { 640 820 }")

        widgets = _strip_comments(_read(TAB_WIDGETS))
        self.assertRegex(widgets, r"(?m)^\ttype te_help_button = button_icon_round \{")
        button = _children(_type_body(widgets, "te_help_button"))
        props = {name: value for kind, name, value in button if kind == "property"}
        self.assertEqual(props, {"parentanchor": "right|vcenter", "position": "{ -10 0 }",
                                 "tooltip": '"te_help_button_tt"'})
        overrides = {name: inner.strip() for kind, name, inner in button if kind == "blockoverride"}
        self.assertEqual(overrides, {"size": "size = { 29 29 }", "icon": f'texture = "{HELP_ICON}"'})
        # an instance adds its own onclick, and nothing gates the type
        self.assertNotIn("onclick", _type_body(widgets, "te_help_button"))
        self.assertNotIn("visible", _type_body(widgets, "te_help_button"))

    def test_the_loc(self):
        self.assertIn("te_help_button_tt", _loc())


class PageTest(unittest.TestCase):
    """Each page: its popup, its body, the link and the "?" (plan Task H1.2)."""

    @classmethod
    def setUpClass(cls):
        cls.types = _all_types()
        cls.gui = "\n".join(_strip_comments(_read(p)) for p in _gui_paths())
        cls.loc = _loc()
        cls.translations = _translations()

    def test_each_page_has_its_popup(self):
        for page in PAGES:
            with self.subTest(page=page.key):
                base, body = self.types[f"te_{page.key}_help_popup"]
                self.assertEqual(base, "te_ui_help_popup")
                items = _children(body)
                self.assertEqual(sorted(name for _, name, _ in items), ["popup_list", "popup_title", "popup_visible"])
                self.assertEqual(_override(body, "popup_visible").strip(),
                                 f"visible = \"[GetVariableSystem.HasValue('te_popup', 'help_{page.key}')]\"")
                self.assertEqual(_override(body, "popup_title").strip(), f'text = "{page.title}"')
                self.assertEqual(_override(body, "popup_list").strip(), f"te_{page.key}_help_body = {{}}")

    def test_every_page_is_in_the_root(self):
        root = _strip_comments(_read(POPUPS))
        for page in PAGES:
            with self.subTest(page=page.key):
                self.assertEqual(len(re.findall(rf"^\tte_{page.key}_help_popup = \{{\}}$", root, re.M)), 1)

    def test_the_body_is_only_in_its_popup(self):
        for page in PAGES:
            with self.subTest(page=page.key):
                base, body = self.types[f"te_{page.key}_help_body"]
                self.assertEqual(base, "flowcontainer")
                own = {name: value for kind, name, value in _children(body) if kind == "property"}
                self.assertEqual({k: own.get(k) for k in ("direction", "ignoreinvisible", "spacing")},
                                 {"direction": "vertical", "ignoreinvisible": "yes", "spacing": "4"})
                self.assertNotIn("visible", own)
                self.assertEqual(len(re.findall(rf"\bte_{page.key}_help_body = \{{", self.gui)), 1)

    def test_every_page_opens(self):
        """Something opens each page (its link at least), and nothing opens a
        page that isn't there."""
        opened = set(re.findall(r"GetVariableSystem\.Set\('te_popup', 'help_(\w+)'\)", self.gui))
        self.assertEqual(opened, {page.key for page in PAGES})

    def test_the_link_replaces_the_section(self):
        """The section keeps its name and its place, shrunk to its header,
        which opens the page instead of expanding."""
        for page in PAGES:
            for section in page.sections:
                with self.subTest(section=section):
                    _, body = self.types[section]
                    widgets = [(name, inner) for kind, name, inner in _children(body) if kind != "property"]
                    self.assertEqual(len(widgets), 1, f"{section} holds more than its header")
                    header = _children(widgets[0][1])
                    props = {name: value for kind, name, value in header if kind == "property"}
                    self.assertEqual(props.get("tooltip"), '"te_help_link_tt"')
                    self.assertIn("te_help_link_tt", self.loc)
                    overrides = {name: inner.strip() for kind, name, inner in header if kind == "blockoverride"}
                    self.assertIn(f'text = "{page.title}"', overrides["left_text"])
                    self.assertEqual(overrides["onclick"], f'onclick = "{_open(page.key)}"')
                    # no arrow: its container hidden, not the onclick_show* blocks, one of which
                    # is also the expand_button widget whose visibility picks the click sound
                    # (vanilla section_header_button), so a click plays "increment"
                    self.assertEqual(overrides["arrow_visible"], "visible = no")
                    self.assertNotIn("onclick_showmore", overrides)
                    self.assertNotIn("onclick_showless", overrides)
                    self.assertNotIn("GetVariableSystem.Exists", body)
                    self.assertNotIn("GetVariableSystem.Toggle", body)

    def test_no_flag_is_left(self):
        raw = "\n".join(_read(p) for p in _gui_paths())
        for page in PAGES:
            for flag in page.flags:
                with self.subTest(flag=flag):
                    self.assertNotIn(f"'{flag}'", raw)
                    self.assertNotIn(flag, raw)

    def test_the_body_reads_the_player(self):
        """No JournalEntry read in what the popup reaches, nor in the loc it
        names, and no read of any context the popups root lacks (Country,
        State, a host panel): a page opens from any host, the entry held or
        not."""
        for page in PAGES:
            with self.subTest(page=page.key):
                reached = _closure(self.types, f"te_{page.key}_help_popup")
                self.assertIn(f"te_{page.key}_help_body", reached)
                self.assertIn("te_ui_popup", reached)
                text = "\n".join(self.types[name][1] for name in sorted(reached))
                self.assertNotRegex(text, r"\bJournalEntry\b|GetPlayerJournalEntry")
                self.assertLessEqual(_chain_heads(text), GLOBAL_HEADS, "the markup reads a context a popup lacks")
                keys = _keys_reached(text, self.loc, self.translations)
                self.assertIn(page.title, keys)
                for key in sorted(keys):
                    # in English, and in German and Spanish, which ship into the same popup
                    for where, value in [("English", self.loc[key])] + [
                            (f"{rel} ({field})", value) for rel, field, value in self.translations.get(key, ())]:
                        self.assertNotIn("JournalEntry", value, f"{key}, {where}")
                        self.assertLessEqual(_chain_heads(value), GLOBAL_HEADS,
                                             f"{key}, {where}: reads a context a popup lacks")

    def test_each_header_has_its_button(self):
        """Every default_header in a tab body's tab_header holds one "?" that
        opens the page, as its last child."""
        for page in PAGES:
            for tab in page.tabs:
                with self.subTest(tab=tab):
                    base, body = self.types[tab]
                    self.assertEqual(base, "te_system_tab_frame")
                    headers = [inner for kind, name, inner in _children(_override(body, "tab_header"))
                               if kind == "widget" and name == "default_header"]
                    self.assertTrue(headers)
                    for header in headers:
                        items = _children(header)
                        self.assertEqual(items[-1][:2], ("widget", "te_help_button"))
                        self.assertEqual([name for _, name, _ in items].count("te_help_button"), 1)
                        self.assertEqual(items[-1][2].strip(), f'onclick = "{_open(page.key)}"')


if __name__ == "__main__":
    unittest.main()
