"""The state panel leaves the mod's bookkeeping modifiers out of its modifier rows.

Some state modifiers are the mod's bookkeeping, refreshed by script each month
or step: tourism, pollution, migration crowding, the free port's tariffs, and
the demographics census's corrections to birth and death rates. They carry the
mod's blank icon, modifier_system.dds. Others are shown by a card of their own
in the state panel and keep their icon: a Grand Monument's tourism and local
effect (gm_local_*), which its card lists, and the six modifiers wealth
concentration and the inheritance law give a state, which the Wealth
Concentration tile lists, and the nine standing modifiers the Demographics
census gives it (Inequality, Primate City, Metropolis ...), which the
Demographics subtab's Modifiers section lists. All three kinds are hidden from
the rows.
A GUI can't read a timed modifier's key
(`TimedModifier` has no GetKey), and its icon can't be compared:
`EqualTo_string(TimedModifier.GetIcon, ...)` fails at runtime with "FetchData
failed" on every frame (GetIcon returns an unregistered texture type; 13,690
lines in minutes, 2026-10-10). Its name can: GetName returns a CString, and the
global Localize('<key>') renders the modifier's own name in the same language,
so `EqualTo_string(TimedModifier.GetName, Localize('<key>'))` picks it out in
any language. Each row's item is `visible = no` for every hidden modifier, in a
container that ignores invisible items.

The condensed view's box fades out when the state carries nothing else, which
needs a count the GUI can't make itself: gui_state_hidden_modifier_count
(common/script_values/gui_chart_script_values.txt) names each hidden static
modifier by a has_modifier term.
"""
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui")
STATIC_MODIFIERS = os.path.join(REPO, "common", "static_modifiers")
COUNT_FILE = os.path.join(REPO, "common", "script_values", "gui_chart_script_values.txt")
COUNT = "gui_state_hidden_modifier_count"

# The mod's one invisible modifier icon (4x4, alpha 0): a bookkeeping modifier
# carries it and gets a term in gui_state_hidden_modifier_count.
HIDDEN_ICONS = (
    "gfx/interface/icons/timed_modifier_icons/modifier_system.dds",
)

# State modifiers a card in the state panel already shows, hidden from the rows
# with their own icons kept for the Modifiers tab and the tooltips. The Grand
# Monument card (te_state_gm_card, gui/te_state_panel_widgets.gui) shows the
# Tourism Industry throughput and the dedication's local effect the monument
# gives its state: gm_local_tourism and gm_local_<dedication>
# (common/static_modifiers/gm_modifiers.txt), so a new dedication is hidden too.
SHOWN_ON_A_CARD_PREFIXES = (
    "gm_local_",
)

# State modifiers the state panel's Wealth Concentration tile lists by name
# (te_state_wealth_tile, gui/te_state_panel_widgets.gui): what wealth
# concentration and the inheritance law do in the state. By name, not by an
# `inh_` prefix, which would also catch the country's own inheritance
# modifiers. The tile shows whenever the state carries one, whatever the
# Demographics rule (gui_state_wealth_modifier_count), so hiding them from the
# rows never hides them from the player.
SHOWN_ON_A_CARD_NAMES = (
    "inh_concentrated_property", "inh_dispersed_property", "inh_land_hunger",
    "inh_forced_heirship_rural", "inh_primogeniture_rural", "inh_undivided_farm_rural",
)
WEALTH_COUNT = "gui_state_wealth_modifier_count"

# State modifiers the Demographics subtab's Modifiers section lists by name
# (te_state_demog_modifiers, gui/te_demographics_widgets.gui; owner, 2026-10-21):
# the standing conditions the census's yearly pulses recompute, under Full only.
# The timed ones a choice grants stay in the rows with their time left: the
# Planned Capital decision (te_demog_pc_new_capital) and the event wave's options
# (te_demog_wave_*). The subtab is there whenever the modifiers are (Full runs
# the census), except for the pulse after the rule leaves Full, which takes them
# off: gui_state_demog_modifier_count gates the section's "none" line.
SHOWN_ON_THE_DEMOGRAPHICS_TAB_NAMES = (
    "te_demog_census_fewer_men", "te_demog_census_inequality", "te_demog_census_more_men",
    "te_demog_census_youth_bulge", "te_demog_lx_gap_labor", "te_demog_mt_dispersed",
    "te_demog_mt_metropolis", "te_demog_primate_city", "te_demog_provincial_neglect",
)
DEMOG_COUNT = "gui_state_demog_modifier_count"
DEMOG_SECTION = "te_state_demog_modifiers"

DATAMODEL = 'datamodel = "[State.GetTimedModifiers]"'


def _strip_comments(text):
    """The text with `# ...` comments blanked, keeping a quoted `#` and every
    offset unchanged."""
    out = []
    in_string = in_comment = False
    for ch in text:
        if in_comment:
            if ch == "\n":
                in_comment = False
                out.append(ch)
            else:
                out.append(" ")
            continue
        if ch == '"':
            in_string = not in_string
        elif ch == "#" and not in_string:
            in_comment = True
            out.append(" ")
            continue
        elif ch == "\n":
            in_string = False
        out.append(ch)
    return "".join(out)


def _block_around(text, pos):
    """(opener, start, end) of the innermost `name = { ... }` holding `pos`."""
    depth = 0
    i = pos
    while i >= 0:
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                break
            depth -= 1
        i -= 1
    start = i
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    line_start = text.rfind("\n", 0, start) + 1
    opener = re.match(r"\s*(\w+)", text[line_start:start]).group(1)
    return opener, start, end


def _own_lines(block):
    """The block's own properties: its text with every nested `{ ... }` removed."""
    out, depth = [], 0
    for ch in block[1:-1]:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _sites():
    """One dict per container in gui/**/*.gui whose datamodel is a state's
    timed modifiers."""
    found = []
    for root, _, files in os.walk(GUI):
        for fn in sorted(files):
            if not fn.endswith(".gui"):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding="utf-8-sig") as f:
                text = _strip_comments(f.read())
            for m in re.finditer(re.escape(DATAMODEL), text):
                opener, start, end = _block_around(text, m.start())
                block = text[start:end]
                item = re.search(r"\bitem\s*=\s*\{", block)
                found.append({
                    "where": f"{os.path.relpath(path, REPO)}:{text.count(chr(10), 0, m.start()) + 1}",
                    "container": opener,
                    "own": _own_lines(block),
                    "item": block[item.start():] if item else "",
                })
    return found


def _entries(node):
    for part in node if isinstance(node, list) else [node]:
        for key, (op, value) in part.items():
            yield key, op, value


def _parse(path):
    parser = ParadoxFileParser()
    with open(path, encoding="utf-8-sig") as f:
        return parser.parse_object(parser.tokenize("{" + f.read() + "}"))[0]


def _static_modifiers():
    """{name: [icon, ...]} for every static modifier the mod defines."""
    found = {}
    for fn in sorted(os.listdir(STATIC_MODIFIERS)):
        if not fn.endswith(".txt"):
            continue
        for key, _, block in _entries(_parse(os.path.join(STATIC_MODIFIERS, fn))):
            if not isinstance(block, (dict, list)):
                continue
            icons = [value for k, _, value in _entries(block) if k == "icon"]
            found[key.split(":", 1)[-1]] = icons
    return found


def _hidden_modifiers():
    """The static modifiers both rows leave out: the blank-icon ones and the
    ones a card already shows."""
    return {name for name, icons in _static_modifiers().items()
            if any(icon in HIDDEN_ICONS for icon in icons)
            or name.startswith(SHOWN_ON_A_CARD_PREFIXES) or name in SHOWN_ON_A_CARD_NAMES
            or name in SHOWN_ON_THE_DEMOGRAPHICS_TAB_NAMES}


def _count_terms(count=COUNT):
    """{modifier: add} for each `if = { limit = { has_modifier = X } add = N }`."""
    tree = dict((k, v) for k, _, v in _entries(_parse(COUNT_FILE)))
    terms = {}
    for key, _, value in _entries(tree[count]):
        if key != "if":
            continue
        fields = dict((k, v) for k, _, v in _entries(value))
        limit = dict((k, v) for k, _, v in _entries(fields["limit"]))
        terms[limit["has_modifier"]] = fields.get("add")
    return terms


class HiddenStateModifierTest(unittest.TestCase):
    def setUp(self):
        # A card's own list picks its modifiers out (`visible = "[Or(...)]"`);
        # the rows leave the hidden ones out (`visible = "[Not(...)]"`).
        sites = _sites()
        self.cards = [s for s in sites if not re.search(r'visible\s*=\s*"\[Not\(', s["item"])]
        self.sites = [s for s in sites if s not in self.cards]

    def test_both_state_panel_rows_are_found(self):
        # The full view's row over the state's picture and the condensed view's box.
        where = [site["where"].split(":")[0] for site in self.sites]
        self.assertGreaterEqual(where.count("gui/states_panel.gui"), 2, self.sites)

    def test_card_modifiers_are_found(self):
        # A renamed prefix would quietly stop hiding the card's modifiers.
        hidden = _hidden_modifiers()
        for prefix in SHOWN_ON_A_CARD_PREFIXES:
            with self.subTest(prefix=prefix):
                self.assertTrue([name for name in hidden if name.startswith(prefix)])
        self.assertIn("gm_local_tourism", hidden)
        statics = _static_modifiers()
        for name in SHOWN_ON_A_CARD_NAMES + SHOWN_ON_THE_DEMOGRAPHICS_TAB_NAMES:
            self.assertIn(name, statics)
            self.assertIn(name, hidden)

    def test_the_demographics_tab_keeps_the_choice_granted_timed_modifiers_out(self):
        # A modifier a decision or an event option grants has an end date: the rows
        # keep it so its time left shows. The Modifiers section lists only the
        # standing conditions the census recomputes.
        statics = _static_modifiers()
        for name in ("te_demog_pc_new_capital", "te_demog_wave_baby_boom", "te_demog_wave_dividend_schools"):
            self.assertIn(name, statics)
            self.assertNotIn(name, _hidden_modifiers(), name)

    def test_card_lists_pick_out_only_card_modifiers(self):
        # te_state_wealth_tile lists the six by name and te_state_demog_modifiers
        # the nine, each taking no space for the rest
        expected = {
            "gui/te_state_panel_widgets.gui": set(SHOWN_ON_A_CARD_NAMES),
            "gui/te_demographics_widgets.gui": set(SHOWN_ON_THE_DEMOGRAPHICS_TAB_NAMES),
        }
        self.assertEqual(sorted(s["where"].split(":")[0] for s in self.cards), sorted(expected),
                         [s["where"] for s in self.cards])
        for site in self.cards:
            with self.subTest(site=site["where"]):
                visible = re.findall(r'visible\s*=\s*"([^"]*)"', site["item"])
                self.assertEqual(len(visible), 1)
                self.assertTrue(visible[0].startswith("[Or("))
                named = set(re.findall(r"EqualTo_string\(TimedModifier\.GetName, Localize\('(\w+)'\)\)", visible[0]))
                self.assertEqual(named, expected[site["where"].split(":")[0]])
                self.assertEqual(visible[0].count("("), visible[0].count(")"), "the Or chain's parentheses balance")
                self.assertEqual(site["container"], "flowcontainer")
                self.assertRegex(site["own"], r"\bignoreinvisible\s*=\s*yes\b")

    def test_the_demographics_section_counts_exactly_the_nine(self):
        # Its "none" line reads gui_state_demog_modifier_count, which names the nine
        # and no others, one each.
        terms = _count_terms(DEMOG_COUNT)
        self.assertEqual(set(terms), set(SHOWN_ON_THE_DEMOGRAPHICS_TAB_NAMES))
        self.assertEqual(set(terms.values()), {"1"})
        with open(os.path.join(GUI, "te_demographics_widgets.gui"), encoding="utf-8-sig") as f:
            widgets = _strip_comments(f.read())
        m = re.search(rf"type {DEMOG_SECTION} = \w+ \{{", widgets)
        self.assertTrue(m, f"no type {DEMOG_SECTION}")
        _, start, end = _block_around(widgets, m.end() - 1)
        body = widgets[start:end]
        self.assertIn(f"EqualTo_CFixedPoint(State.MakeScope.ScriptValue('{DEMOG_COUNT}'), '(CFixedPoint)0')", body)

    def test_the_wealth_tile_shows_whenever_a_card_modifier_is_there(self):
        # Hidden from the rows, so the tile must show whenever the state has one,
        # whatever the Demographics rule: its gate counts exactly the six.
        terms = _count_terms(WEALTH_COUNT)
        self.assertEqual(set(terms), set(SHOWN_ON_A_CARD_NAMES))
        self.assertEqual(set(terms.values()), {"1"})
        with open(os.path.join(GUI, "states_panel.gui"), encoding="utf-8-sig") as f:
            panel = _strip_comments(f.read())
        tile = panel.index("te_state_wealth_tile = {}")
        opener, start, end = _block_around(panel, panel.rfind('blockoverride "extra_widget"', 0, tile) - 1)
        self.assertEqual(opener, "state_panel_status_item_small")
        own = _own_lines(panel[start:end])
        gates = re.findall(r'visible\s*=\s*"([^"]*)"', own)
        self.assertEqual(gates, [f"[GreaterThan_CFixedPoint(State.MakeScope.ScriptValue('{WEALTH_COUNT}'), '(CFixedPoint)0')]"])

    def test_every_row_hides_every_hidden_modifier_by_name(self):
        hidden = _hidden_modifiers()
        self.assertTrue(hidden)
        for site in self.sites:
            with self.subTest(site=site["where"]):
                visible = re.findall(r'visible\s*=\s*"([^"]*)"', site["item"])
                self.assertEqual(len(visible), 1, "one visible per item (gotcha #17)")
                named = set(re.findall(r"EqualTo_string\(TimedModifier\.GetName, Localize\('(\w+)'\)\)", visible[0]))
                missing = sorted(hidden - named)
                self.assertFalse(missing, f"the row's name filter leaves these hidden modifiers showing: {missing}")
                extra = sorted(named - hidden)
                self.assertFalse(extra, f"the row's name filter hides modifiers with neither the blank icon nor a card prefix: {extra}")
                self.assertTrue(visible[0].startswith("[Not("))

    def test_hidden_items_take_no_space(self):
        # flowcontainer, hbox and vbox lay out invisible children unless told not to; an
        # overlappingitembox hides an item on visible alone (vanilla's mobilization options)
        for site in self.sites:
            with self.subTest(site=site["where"]):
                if site["container"] in ("flowcontainer", "hbox", "vbox"):
                    self.assertRegex(site["own"], r"\bignoreinvisible\s*=\s*yes\b")
                else:
                    self.assertEqual(site["container"], "overlappingitembox")

    def test_no_gui_compares_a_modifiers_icon_as_a_string(self):
        # GetIcon is not a string: EqualTo_string on it fails every frame (#872's filter, removed)
        for root, _, files in os.walk(GUI):
            for fn in sorted(files):
                if fn.endswith(".gui"):
                    path = os.path.join(root, fn)
                    with open(path, encoding="utf-8-sig") as f:
                        text = _strip_comments(f.read())
                    lines = [text.count("\n", 0, m.start()) + 1
                             for m in re.finditer(r"EqualTo_string\(\s*TimedModifier\.GetIcon", text)]
                    self.assertFalse(lines, f"{os.path.relpath(path, REPO)} compares TimedModifier.GetIcon at lines {lines}")

    def test_no_row_treats_hidden_modifiers_as_content(self):
        # An emptiness test on the raw list counts the hidden modifiers too,
        # and tourism and pollution sit on every state.
        for site in self.sites:
            with self.subTest(site=site["where"]):
                self.assertNotIn("IsDataModelEmpty(State.GetTimedModifiers)", site["own"])
                if "alpha" in site["own"]:
                    self.assertIn(f"ScriptValue('{COUNT}')", site["own"])

    def test_count_names_every_hidden_modifier(self):
        terms = _count_terms()
        hidden = _hidden_modifiers()
        self.assertTrue(hidden)
        missing = sorted(hidden - set(terms))
        self.assertFalse(missing, f"hidden static modifiers with no has_modifier term in {COUNT} ({os.path.relpath(COUNT_FILE, REPO)}): {missing}")
        extra = sorted(set(terms) - hidden)
        self.assertFalse(extra, f"{COUNT} counts modifiers the state panel shows (icon not in HIDDEN_ICONS, name not in SHOWN_ON_A_CARD_PREFIXES): {extra}")
        self.assertEqual(set(terms.values()), {"1"})


if __name__ == "__main__":
    unittest.main()
