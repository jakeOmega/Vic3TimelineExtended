"""The Budget panel's read-only monetary readout (#805).

A country can hold a central bank dial (a national bank is enough) or tie its
money to another's without the banking journal entry, and such a country can
meet a peg crisis. The Banking tab opens for it, read-only, with
te_banking_mon_readout in place of the entry's panels. These tests hold the
gate, the readout's independence from the entry it is drawn without, its copies
of the dashboard's state words, and the peg events' tooltips that now name what
it shows.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.join(REPO, "gui", "journal_entry_widgets", "banking_dashboard_widget.gui")
BUDGET = os.path.join(REPO, "gui", "budget_panel.gui")
TAB_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")
CUSTOM_LOC = os.path.join(REPO, "common", "customizable_localization", "banking_dash_custom_loc.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")
EVENTS = os.path.join(REPO, "events", "te_peg_events.txt")

READOUT_SGUI = "te_budget_banking_readout_sgui"
ENTRY_SGUI = "te_budget_banking_tab_sgui"
PLAYER_ROOT = "GuiScope.SetRoot( GetPlayer.MakeScope ).End"


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _block_from(text, start):
    """The brace block that opens at or after `start`, braces included."""
    j = text.index("{", start)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j:k + 1]
    raise AssertionError("unbalanced block")


def _top_block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"no top-level block {name}"
    return _block_from(text, m.end() - 1)


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return _block_from(text, m.end() - 1)[1:-1]


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _norm(s):
    return " ".join(s.split())


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
        for line in _read(path).splitlines():
            m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def _custom_locs():
    out = {}
    for path in glob.glob(os.path.join(REPO, "common", "customizable_localization", "*.txt")):
        text = _strip_comments(_read(path))
        for m in re.finditer(r"(?m)^(\w+) = \{", text):
            out[m.group(1)] = _block_from(text, m.end() - 1)
    return out


def _branches(block):
    """(trigger, key) per text block of a customizable localization, in order;
    the trigger is "" for a branch without one."""
    return [(_norm(t), k) for t, k in re.findall(
        r"text = \{\s*(?:trigger = \{(.*?)\}\s*)?localization_key = (\w+)\s*\}", block, re.S)]


def _tab_content():
    text = _read(BUDGET)
    start = text.index('name = "te_budget_banking_tab"')
    return text[start:text.index("### END MOD ###", start)]


def _tab_button():
    text = _read(BUDGET)
    start = text.index("### MOD: Banking tab (te_banking) ###")
    return text[start:text.index("### END MOD ###", start)]


def _shown(sgui):
    return f"GetScriptedGui('{sgui}').IsShown( {PLAYER_ROOT} )"


class GateTest(unittest.TestCase):
    def test_the_readout_gate(self):
        block = _top_block(_strip_comments(_read(TAB_SGUIS)), READOUT_SGUI)
        shown = _norm(_block_from(block, block.index("is_shown")))
        for line in ("te_mon_full_system = yes", "NOT = { has_journal_entry = je_banking_cycle }",
                     "te_mon_has_stance = yes"):
            self.assertIn(line, shown)
        self.assertIn("is_valid = { always = no }", _norm(block))
        self.assertIn("ai_is_valid = { always = no }", _norm(block))
        # ...and the entry's own gate is exactly an active entry, so the two
        # are never true together.
        entry = _norm(_top_block(_strip_comments(_read(TAB_SGUIS)), ENTRY_SGUI))
        self.assertIn("has_journal_entry = je_banking_cycle", entry)

    def test_the_tab_button_opens_for_either(self):
        button = _tab_button()
        enabled = re.search(r'enabled = "(.*)"', button).group(1)
        self.assertEqual(enabled, f"[Or( {_shown(ENTRY_SGUI)}, {_shown(READOUT_SGUI)} )]")
        tooltip = re.search(r'tooltip = "(.*)"', button).group(1)
        self.assertIn(f"SelectLocalization( {_shown(READOUT_SGUI)}, 'te_budget_tab_banking_readout_tt', "
                      "'te_budget_tab_banking_locked_tt' )", tooltip)
        loc = _loc()
        for key in ("te_budget_tab_banking_readout_tt", "te_budget_tab_banking_locked_tt"):
            self.assertIn(key, loc)

    def test_the_content_shows_one_header_and_the_readout_behind_its_gate(self):
        tab = _tab_content()
        self.assertIn("ignoreinvisible = yes", tab[:tab.index("default_header")])
        headers = re.findall(r'default_header = \{\s*visible = "(.*)"\s*blockoverride "text" \{\s*text = "(\w+)"',
                             tab)
        self.assertEqual(headers, [(f"[Not( {_shown(READOUT_SGUI)} )]", "je_banking_cycle"),
                                   (f"[{_shown(READOUT_SGUI)}]", "banking_dash_cat_monetary")])
        at = tab.index("te_banking_mon_readout = {}")
        gate = tab.rindex("flowcontainer = {", 0, at)
        block = _block_from(tab, gate)
        self.assertRegex(block, rf'^\{{\s*visible = "\[{re.escape(_shown(READOUT_SGUI))}\]"')
        # the readout comes before the entry's panels, which keep their gate
        self.assertLess(at, tab.index("GetPlayerJournalEntry('je_banking_cycle')"))
        self.assertNotIn("GetPlayerJournalEntry", block)

    def test_the_note_names_what_opens_the_rest(self):
        tab = _tab_content()
        note = _block_from(tab, tab.rindex("textbox = {", 0, tab.index('text = "banking_dash_ro_note"')))
        tooltip = re.search(r'tooltip = "(.*)"', note).group(1)
        self.assertIn("GetScriptedGui('te_budget_banking_tab_unlock_sgui').IsValidTooltip(", tooltip)
        self.assertLess(tooltip.index("'te_system_tab_met_tt'"), tooltip.index(".IsValidTooltip("))
        self.assertIn("Localize( 'banking_dash_ro_note_tt' )", tooltip)


class ReadsThePlayerTest(unittest.TestCase):
    """Drawn where there is no entry, so nothing in it may read JournalEntry,
    however many keys or custom localizations away."""

    @classmethod
    def setUpClass(cls):
        cls.body = _type_body(_read(DASH), "te_banking_mon_readout")
        cls.loc = _loc()
        cls.custom = _custom_locs()

    def _reached(self, keys):
        seen, stack = set(), list(keys)
        while stack:
            key = stack.pop()
            if key in seen or key not in self.loc:
                continue
            seen.add(key)
            text = self.loc[key]
            stack += re.findall(r"\$(\w+)\$", text)
            for name in re.findall(r"GetCustom\('(\w+)'\)", text):
                self.assertIn(name, self.custom, f"{key}: no customizable localization {name}")
                stack += [k for _, k in _branches(self.custom[name])]
        return seen

    def test_the_type_reads_no_journal_entry(self):
        self.assertNotIn("JournalEntry", self.body)
        for expr in re.findall(r'"(\[[^"]*\])"', self.body):
            if "GetScriptedGui" in expr or "ScriptValue" in expr:
                self.assertIn("GetPlayer.MakeScope", expr)

    def test_every_key_exists_and_reads_no_journal_entry(self):
        tab = _tab_content()
        readout = _block_from(tab, tab.rindex("flowcontainer = {", 0, tab.index("te_banking_mon_readout = {}")))
        keys = re.findall(r'(?:text|tooltip) = "(\w+)"', self.body + readout)
        keys += ["te_budget_tab_banking_readout_tt", "banking_dash_ro_note_tt"]
        for key in keys:
            self.assertIn(key, self.loc, key)
        reached = self._reached(keys)
        self.assertGreaterEqual(len(reached), 30)
        for key in sorted(reached):
            self.assertNotIn("JournalEntry", self.loc[key], key)

    def test_every_scripted_gui_exists(self):
        sguis = {}
        for path in glob.glob(os.path.join(REPO, "common", "scripted_guis", "*.txt")):
            text = _strip_comments(_read(path))
            for m in re.finditer(r"(?m)^(\w+) = \{", text):
                sguis[m.group(1)] = _block_from(text, m.end() - 1)
        names = set(re.findall(r"GetScriptedGui\('(\w+)'\)", self.body))
        self.assertEqual(names, {"banking_mon_display_ready", "banking_mon_world_rate_ready",
                                 "banking_mon_has_dial", "banking_mon_is_anchored",
                                 "banking_mon_shows_gold", "banking_mon_shows_anchor_peg"})
        for name in names:
            self.assertIn(name, sguis, name)
            self.assertIn("scope = country", sguis[name], name)
        self.assertIn("te_mon_is_anchored = yes", sguis["banking_mon_is_anchored"])

    def test_the_rows(self):
        """Rate and world rate, mandate (a dial), anchor (anchored), exchange
        rate, and Peg Confidence with its meter, for gold or a treaty peg."""
        rows = re.findall(r'tooltip = "(banking_dash_\w+)"', self.body)
        self.assertEqual(rows, ["banking_dash_ro_rate_tt", "banking_dash_mon_worldrate_tt",
                                "banking_dash_ro_mandate_tt", "banking_dash_ro_anchor_tt",
                                "banking_dash_ro_fx_tt", "banking_dash_ro_pegconf_tt",
                                "banking_dash_ro_pegconf_tt", "banking_dash_ro_anchorpeg_tt",
                                "banking_dash_ro_anchorpeg_tt"])
        # no control: nothing to click
        for control in ("onclick", "ScriptedGui.Execute", "button", "banking_mon_control_sgui"):
            self.assertNotIn(control, self.body, control)


class CopiesTest(unittest.TestCase):
    """The readout's own copies of three dashboard state words: the same
    branches in the same order, keys reading GetPlayer."""

    @classmethod
    def setUpClass(cls):
        cls.custom = _custom_locs()
        cls.loc = _loc()

    def test_fx_state_follows_the_dashboard(self):
        ours, theirs = (_branches(self.custom[n]) for n in ("te_mon_ro_fx_state", "te_mon_fx_state"))
        self.assertEqual([t for t, _ in ours], [t for t, _ in theirs])
        for (_, mine), (_, dash) in zip(ours, theirs):
            self.assertEqual(self.loc[mine], self.loc[dash].replace("JournalEntry.GetCountry", "GetPlayer"), mine)

    def test_anchor_state_follows_the_dashboard_without_the_rate(self):
        ours = _branches(self.custom["te_mon_ro_anchor_state"])
        theirs = [b for b in _branches(self.custom["te_mon_anchor_state"]) if "te_mon_is_anchored" in b[0]]
        self.assertEqual([t for t, _ in ours[:-1]], [t for t, _ in theirs])
        self.assertEqual(ours[-1], ("", "banking_dash_mon_anchor_state_none"))
        for (_, mine), (_, dash) in zip(ours, theirs):
            want = self.loc[dash].split(" — rate")[0].replace("JournalEntry.GetCountry", "GetPlayer")
            self.assertEqual(self.loc[mine], want, mine)

    def test_rate_source(self):
        branches = _branches(self.custom["te_mon_ro_rate_source"])
        self.assertEqual([t for t, _ in branches],
                         ["te_mon_is_anchored = yes", "te_mon_mandate_binds = yes", ""])


class PegEventTooltipTest(unittest.TestCase):
    """The no-entry tooltips of te_peg.1/.2/.3 name what the readout shows,
    and not what only the dashboard has."""

    def test_no_je_tooltips(self):
        loc = _loc()
        events = _read(EVENTS)
        variants = re.findall(r"custom_tooltip = (te_peg\.\d\.\w)\.no_je_tt", events)
        self.assertEqual(len(variants), 8)
        for base in variants:
            with self.subTest(option=base):
                tt, no_je = loc[f"{base}.tt"], loc[f"{base}.no_je_tt"]
                if "Peg Confidence" in tt:
                    self.assertIn("Peg Confidence", no_je)
                if "Exchange Rate Index" in tt:
                    self.assertIn("Exchange Rate Index", no_je)
                self.assertNotRegex(no_je, r"(?i)\bdial\b|rate target|\$banking_dash_mon_mandate_")


if __name__ == "__main__":
    unittest.main()
