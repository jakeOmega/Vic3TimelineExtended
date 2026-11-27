"""Journal entry map modes, fifth pass (docs/systems/mod_systems/journal_map_modes.md).

The engine says nothing about a map's script: a named color it doesn't know, a tooltip key with no loc or a selector
number no branch reads all fail silently on the map. So this holds the pieces together offline:

- every color a map names is one of the mod's (common/named_colors/te_journal_map_colors.txt), and each is used;
- every Map Room pick (a scripted GUI) sets a selector that map_color and map_tooltip both branch on, has a
  button, and has its loc; the Map Room stays contextless, in no journal, with no scripted buttons (they lock);
- every map that needs a stored figure has a "no data" branch, and a year's figures wait for a state's first step;
- the leading-cause map's colors are the Causes of Death pie's;
- every map_tooltip key has loc;
- each pick reopens the Map Room's page a beat after its click, so a paused map repaints (check 4), from a
  widget outside the page (te_jmap_repainter), since a widget on it dies with the close (fifth session);
- the map buttons are mounted, Banking's shows while its entry is inactive (check 7), and every GUI reach into an
  entry names one that exists;
- every journal page has the see-through eye (gui/journal_entry.gui): a pick's reopen keeps it, closing clears it;
- the systems' maps (selectors 18-25): each system entry's map and the Map Room's branch for it ask the same triggers
  in the same order (the parity test), each pick waits for its system's rule, each system tab's button picks its map
  and opens the Map Room, and the "your" maps follow the viewer the picks note;
- the Timeline Extended window's Map Room button opens the page before it closes the window;
- the Map Room's options (Area and Outliers, 2026-11-14): a state outside the area is greyed by one stored mark the
  paint reads first, the mark is put on by an effect (never asked for in a paint), every state region belongs to
  exactly one continent, each option button runs its scripted GUI and then the picks' own repaint, and no system's
  own entry reads the mark or the Map Room's ranges;
- Nuclear Reach (selector 90): the viewer's reach by the cheapest leg, its bombers' from the deterrent's own builder
  into the map's list, rebuilt whenever the viewer is noted while it is the pick, and nothing private read.
"""
import os
import re
import subprocess
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
HOST = "common/journal_entries/te_journal_maps.txt"
EFFECTS = "common/scripted_effects/te_journal_map_effects.txt"
SGUIS = "common/scripted_guis/te_journal_map_sguis.txt"
# The picks' scripted GUIs and their rows on the page, generated from one table (gen_journal_map_picks.py, #1974)
PICK_SGUIS = "common/scripted_guis/te_journal_map_picks_generated.txt"
PICKS_GUI = "gui/journal_entry_widgets/te_map_room_picks_generated.gui"
ROOM_WIDGET = "gui/journal_entry_widgets/te_map_room_widget.gui"
BANKING = "common/journal_entries/je_banking.txt"
# The systems' maps: (selector, entry file, entry key, Map Room pick, tab button, tab file, rule gate). The Seabed and
# the Power Grids have no entry, so the Map Room alone draws them.
SYSTEM_MAPS = (
    (18, "common/journal_entries/je_global_warming.txt", "je_global_warming", "emissions", "gw",
     "gui/journal_entry_widgets/global_warming_widget.gui", "has_game_rule = global_warming_enabled"),
    (19, "common/journal_entries/je_nuclear_program.txt", "je_nuclear_program", "nuclear", "nuclear",
     "gui/journal_entry_widgets/nuclear_layout_widget.gui", "has_game_rule = nuclear_weapons_enabled"),
    (20, "common/journal_entries/je_covert_warfare.txt", "je_covert_warfare", "networks", "covert",
     "gui/journal_entry_widgets/covert_operations_widget.gui", "te_covert_warfare_on = yes"),
    (21, "common/journal_entries/je_united_nations.txt", "je_united_nations", "united_nations", "un",
     "gui/journal_entry_widgets/un_layout_widget.gui", "te_united_nations_on = yes"),
    (22, "common/journal_entries/je_cultural_hegemony.txt", "je_cultural_hegemony", "political_models", "ch",
     "gui/journal_entry_widgets/cultural_hegemony_widget.gui", "te_cultural_hegemony_on = yes"),
    (23, None, None, "ocean_basins", "seabed", "gui/te_seabed_widgets.gui", "te_global_commons_enabled = yes"),
    (24, "common/journal_entries/je_grand_monuments.txt", "je_grand_monuments", "grandeur", "gm",
     "gui/journal_entry_widgets/grand_monuments_widget.gui", "gm_system_enabled = yes"),
    (25, "common/journal_entries/je_colonial_empire.txt", "je_colonial_empire", "colonies", "ce",
     "gui/journal_entry_widgets/colonial_empire_widget.gui", "has_game_rule = decolonization_enabled"),
    # Power Grids have no entry and no game rule, as their tab has none.
    (31, None, None, "power_grids", "grid", "gui/te_grid_widgets.gui", "is_player = yes"),
)
SYSTEM_ENTRIES = tuple((rel, key) for _sel, rel, key, *_ in SYSTEM_MAPS if rel)
MAP_ENTRIES = (HOST, BANKING) + tuple(rel for rel, _key in SYSTEM_ENTRIES)
TRIGGERS = "common/scripted_triggers/te_journal_map_triggers.txt"
ON_ACTIONS = "common/on_actions/te_journal_map_on_actions.txt"
SYSTEMS_WINDOW = "gui/te_systems_window.gui"
COLORS = "common/named_colors/te_journal_map_colors.txt"
# The class maps' family, generated (gen_journal_map_classes.py, #1975)
CLASS_COLORS = "common/named_colors/te_journal_map_classes_generated.txt"
CLASS_VALUES = "common/script_values/te_journal_map_classes_generated.txt"
CLASS_EFFECTS = "common/scripted_effects/te_journal_map_classes_generated.txt"
VALUES = "common/script_values/te_journal_map_values.txt"
SCALES = "common/script_values/te_journal_map_scales_generated.txt"
WIDGETS = "gui/te_map_widgets.gui"
REPAINTER = "te_jmap_repainter"
REGISTRATION = "gui/scripted_widgets/te_systems_window.txt"
DEMOG_LAYOUT = "gui/te_demographics_layout.gui"
BANKING_LAYOUT = "gui/journal_entry_widgets/banking_layout_widget.gui"
JE_PANEL = "gui/journal_entry.gui"
MAP_MODE = "gfx/map/map_modes/te_map_modes.txt"
LOC_DIR = "localization/english"
PLAYTEST = "docs/testing/journal-map-modes-playtest.md"
BOM = b"\xef\xbb\xbf"


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def code(rel):
    """The file with comments removed (a `#` inside a quoted string is kept)."""
    out = []
    for line in read(rel).splitlines():
        kept, quoted = [], False
        for ch in line:
            if ch == '"':
                quoted = not quoted
            if ch == "#" and not quoted:
                break
            kept.append(ch)
        out.append("".join(kept))
    return "\n".join(out)


def sguis():
    """Every Map Room scripted GUI: the generated picks and the hand-written options."""
    return code(PICK_SGUIS) + "\n" + code(SGUIS)


def block(text, key):
    """The body of the first `key = { ... }` in text (or `type key = base { ... }`), braces balanced."""
    m = re.search(r"\b" + re.escape(key) + r"\s*=\s*(?:\w+\s*)?\{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def override(text, name):
    """The body of `blockoverride "name" { ... }` in text."""
    m = re.search(r'\bblockoverride\s+"' + re.escape(name) + r'"\s*\{', text)
    if not m:
        return None
    start, end = enclosing_span(text, m.end())
    return text[start:end]


def enclosing(text, pos):
    """The body of the innermost `{ ... }` around pos."""
    start, end = enclosing_span(text, pos)
    return text[start:end]


def enclosing_span(text, pos):
    """(start, end) of the body of the innermost `{ ... }` around pos."""
    depth, i = 0, pos
    while i > 0:
        i -= 1
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                break
            depth -= 1
    j, depth = i + 1, 1
    while depth:
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        j += 1
    return i + 1, j - 1


def top_level_widget(text, name):
    """The body of the top-level widget named `name` (a scripted widget's root)."""
    m = re.search(r'^\tname\s*=\s*"' + re.escape(name) + r'"', text, re.M)
    if not m:
        raise AssertionError(f"no top-level widget {name}")
    start, end = enclosing_span(text, m.start())
    assert re.search(r"^widget\s*=\s*\{\s*$", text[:start], re.M), name
    return text[start:end]


def entry(rel, name):
    return block(code(rel), name)


def loc_keys():
    keys = set()
    for name in os.listdir(os.path.join(REPO, LOC_DIR)):
        if name.endswith(".yml"):
            for line in read(os.path.join(LOC_DIR, name)).splitlines():
                m = re.match(r"\s+([A-Za-z0-9_.\-]+):\d*\s", line)
                if m:
                    keys.add(m.group(1))
    return keys


def named_colors():
    return set(re.findall(r"^\s*([a-z0-9_]+)\s*=\s*(?:hsv360|hsv|rgb)\s*\{", code(COLORS) + code(CLASS_COLORS), re.M))


def tracked(rel):
    """Whether git tracks rel. CI checks out without gfx/ (sparse), so a file can be absent on disk yet committed."""
    return subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=REPO,
                          capture_output=True).returncode == 0


class FilesTest(unittest.TestCase):
    def test_each_new_file_has_one_bom(self):
        for rel in (HOST, COLORS, VALUES, SCALES, WIDGETS, ROOM_WIDGET, EFFECTS, SGUIS, PICK_SGUIS, PICKS_GUI, TRIGGERS,
                    ON_ACTIONS, CLASS_COLORS, CLASS_VALUES, CLASS_EFFECTS):
            with open(os.path.join(REPO, rel), "rb") as f:
                head = f.read(6)
            self.assertTrue(head.startswith(BOM) and not head[3:].startswith(BOM), rel)


class ColorsTest(unittest.TestCase):
    def test_every_map_color_is_defined(self):
        known = named_colors()
        for rel, name in ((HOST, "je_te_map_room"), (BANKING, "je_banking_cycle")) + SYSTEM_ENTRIES:
            body = entry(rel, name)
            for key in ("map_color", "map_color_second"):
                part = block(body, key)
                if part is None:
                    continue
                used = set(re.findall(r'\b(?:value|min_color|max_color)\s*=\s*"([a-z0-9_]+)"', part))
                self.assertTrue(used, f"{name}.{key} names no color")
                self.assertEqual(used - known, set(), f"{name}.{key}: colors not in {COLORS}")

    def test_every_defined_color_is_used(self):
        defined = set(re.findall(r"^\s*([a-z0-9_]+)\s*=\s*hsv360", code(COLORS) + code(CLASS_COLORS), re.M))
        used = set()
        for rel in MAP_ENTRIES:
            used |= set(re.findall(r'"(te_jmap_[a-z0-9_]+)"', code(rel)))
        self.assertEqual(defined - used, set(), "named colors no map uses")


class CauseColorsTest(unittest.TestCase):
    PIE = "scripts/image_pipeline/gen_ch_model_pie_textures.py"

    def test_leading_cause_colors_are_the_pies(self):
        # the leading-cause map draws in the Causes of Death pie's colors, so the pie's legend reads the map too
        import colorsys
        pie = dict(re.findall(r'"icons/demographics_icons/pie_(\w+)\.dds",\s*"(#[0-9a-f]{6})"', read(self.PIE)))
        names = {"inf": "infection", "chr": "chronic", "ext": "external", "work": "work", "mat": "maternal",
                 "kill": "killed", "war": "war"}
        text = code(COLORS)
        for short, long in names.items():
            h = pie[long]
            hsv = colorsys.rgb_to_hsv(*(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)))
            m = re.search(r"\bte_jmap_cause_" + short + r"\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}", text)
            self.assertIsNotNone(m, short)
            want = (round(hsv[0] * 360), round(hsv[1] * 100), round(hsv[2] * 100))
            self.assertEqual(tuple(int(x) for x in m.groups()), want, f"te_jmap_cause_{short} vs the pie's {h}")

    def test_each_cause_fades_by_its_share(self):
        # each cause's branch fades from a pale end of its own hue to the pie's color by the leading share, so a
        # state where a cause barely leads reads apart from one where it takes nearly every death
        text, host = code(COLORS), code(HOST)
        for short in ("inf", "chr", "ext", "work", "mat", "kill", "war"):
            full = re.search(r"\bte_jmap_cause_" + short + r"\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", text)
            pale = re.search(r"\bte_jmap_cause_" + short + r"_pale\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", text)
            self.assertIsNotNone(pale, short)
            self.assertEqual(pale.group(1), full.group(1), f"te_jmap_cause_{short}_pale keeps the cause's hue")
            self.assertLess(int(pale.group(2)), int(full.group(2)), f"te_jmap_cause_{short}_pale is paler")
            self.assertRegex(host, r'lerp = \{\s*min_color = "te_jmap_cause_' + short + r'_pale"\s*max_color = '
                             r'"te_jmap_cause_' + short + r'"\s*factor = te_jmap_cause_factor\s*\}', short)
        self.assertNotRegex(block(entry(HOST, "je_te_map_room"), "map_color"), r'value = "te_jmap_cause_',
                            "a cause drawn flat, not by its share")

    CAUSES = (("inf", 1), ("chr", 2), ("ext", 3), ("work", 4), ("mat", 5), ("kill", 7), ("war", 8))

    def test_the_runner_up_stripes_at_half_the_leader(self):
        # the runner-up cause (te_dg_dc_second) stripes the Leading Cause map in its pie color, and its hover line
        # names it, once it took at least half the leader's deaths (owner, 2026-11-06)
        room = entry(HOST, "je_te_map_room")
        stripes, hover = block(room, "map_color_second"), block(room, "map_tooltip")
        self.assertIsNotNone(stripes, "the Map Room draws no stripes")
        for short, n in self.CAUSES:
            gate = (r"te_jmap_selector = 11\b[^{}]*var:te_dg_dc_second = " + str(n) +
                    r"\s+te_jmap_cause_second_ratio >= 0\.5\s*\}\s*")
            self.assertRegex(stripes, gate + r'value = "te_jmap_cause_' + short + r'"', short)
            self.assertRegex(hover, gate + r"custom_tooltip_no_bullet = te_jmap_tt_cause_second_" + short + r"\b",
                             short)
        cause_stripes = [body for limit, body in branches_of(stripes) if re.search(r"te_jmap_selector = 11\b", limit)]
        self.assertEqual(len(cause_stripes), len(self.CAUSES), "a stripe that isn't a cause's")
        # the only other stripes: Power Grids' hubs, Company Headquarters' regional headquarters and Nuclear Reach's
        # submarines over the bombers (Trade Capacity striped its Trade Centers only while it painted the owner's trade)
        others = [limit for limit, _body in branches_of(stripes) if not re.search(r"te_jmap_selector = 11\b", limit)]
        self.assertEqual(others, [ColorTest.GREY_STRIPES,     # Greyscale's, first (the Color option)
                                  "te_jmap_selector = 31 te_jmap_in_area = yes te_jmap_grid_hub = yes",
                                  "te_jmap_selector = 34 te_jmap_in_area = yes has_variable = te_jmap_rhq_n "
                                  "te_jmap_color < 2",
                                  "te_jmap_selector = 90 te_jmap_in_area = yes te_jmap_reach_bombers = yes "
                                  "te_jmap_reach_subs = yes"])

    def test_the_census_stores_the_runner_up(self):
        # te_dg_dc_second is the largest slice but the leader's, in te_dg_dc_lead's codes, for every slice
        effects = code("common/scripted_effects/te_demog_effects.txt")
        total = re.search(r"^te_demog_cause_deaths_total = \{(.*?)^\}", effects, re.S | re.M).group(1)
        lead = re.findall(r"te_demog_cause_deaths_lead = \{ SLICE = (\w+) CODE = (\d+) \}", total)
        second = re.findall(r"te_demog_cause_deaths_second = \{ SLICE = (\w+) CODE = (\d+) \}", total)
        self.assertEqual(second, lead)
        self.assertEqual([(s, int(n)) for s, n in second], list(self.CAUSES))
        self.assertLess(total.index("te_demog_cause_deaths_lead"), total.index("te_demog_cause_deaths_second"),
                        "the runner-up is picked after the leader")
        helper = re.search(r"^te_demog_cause_deaths_second = \{(.*?)^\}", effects, re.S | re.M).group(1)
        self.assertIn("NOT = { var:te_dg_dc_lead = $CODE$ }", helper)
        zero = re.search(r"^te_demog_cause_deaths_zero = \{(.*?)^\}", effects, re.S | re.M).group(1)
        self.assertIn("set_variable = { name = te_dg_dc_second value = 0 }", zero)


class MapRoomTest(unittest.TestCase):
    def setUp(self):
        self.room = entry(HOST, "je_te_map_room")
        self.sguis = sguis()

    def picks(self):
        """{scripted GUI: selector} for every Map Room pick."""
        out = {}
        for name in re.findall(r"^(te_jmap_pick_\w+_sgui)\s*=\s*\{", self.sguis, re.M):
            m = re.search(r"te_jmap_set_selector\s*=\s*\{\s*SEL\s*=\s*(\d+)\s*\}", block(self.sguis, name))
            self.assertIsNotNone(m, f"{name} sets no selector")
            out[name] = int(m.group(1))
        return out

    def test_every_pick_has_a_map_and_a_tooltip(self):
        picks = self.picks()
        # 2 was literacy, retired in the fifth pass (vanilla's literacy map mode shows it) and back in the first tier
        # 48-73 the class maps (#1975); 2 literacy again and 74-82 the first tier's (#1976); 83-87 the second tier's
        # (#1977); 88-89 the class maps' Spacers, the mod's own pop type (space forces personnel, 2026-11-24); 90
        # Nuclear Reach (2026-11-26); 91 Grid Flows (2026-11-27)
        self.assertEqual(sorted(picks.values()), list(range(1, 92)), "one pick per selector")
        # the "no data" branch names the figure maps in an OR; a pick needs a branch of its own
        color = re.sub(r"\bOR\s*=\s*\{[^{}]*\}", "", block(self.room, "map_color"))
        tooltip = re.sub(r"\bOR\s*=\s*\{[^{}]*\}", "", block(self.room, "map_tooltip"))
        for name, sel in picks.items():
            branch = re.compile(r"te_jmap_selector\s*=\s*" + str(sel) + r"\b")
            self.assertRegex(color, branch, f"{name}: map_color has no branch for selector {sel}")
            self.assertRegex(tooltip, branch, f"{name}: map_tooltip has no branch for selector {sel}")

    def branches(self, key, sel):
        """The bodies of key's branches (if / else_if) that name selector sel outside an OR."""
        part = block(self.room, key)
        out = []
        for m in re.finditer(r"\b(?:if|else_if)\s*=\s*\{", part):
            body = enclosing(part, m.end())
            limit = re.sub(r"\bOR\s*=\s*\{[^{}]*\}", "", block(body, "limit") or "")
            if re.search(r"te_jmap_selector\s*=\s*" + str(sel) + r"\b", limit):
                out.append(body)
        return out

    def no_data(self, key):
        """The selectors key's OR-only branches list: the maps that show grey for a state with no figure. map_color has
        one; map_tooltip one for the census and walk figures and one for the tourism and climate refreshes' figures,
        whose wait is a month, not a census year."""
        part = block(self.room, key)
        ors = re.findall(r"\bOR\s*=\s*\{([^{}]*te_jmap_selector[^{}]*)\}", part)
        self.assertTrue(ors, f"{key}: no 'no data' branch")
        found = [int(n) for body in ors for n in re.findall(r"te_jmap_selector\s*=\s*(\d+)", body)]
        self.assertEqual(len(found), len(set(found)), f"{key}: a selector in two 'no data' branches")
        return set(found)

    def test_every_figure_map_has_a_no_data_branch(self):
        # a map whose branches all need a stored figure (has_variable) leaves a state with none unpainted (dark grey)
        # and with the "Pick a map" tooltip, unless the OR lists it
        gated = set()
        for sel in self.picks().values():
            bodies = self.branches("map_color", sel)
            self.assertTrue(bodies, sel)
            if all("has_variable" in b for b in bodies):
                gated.add(sel)
        self.assertIn(3, gated)
        self.assertTrue({26, 27, 28} <= gated, "tourism and the two climate maps read stored figures")
        self.assertTrue({33, 35} <= gated, "Armed Forces (the walk's) and War Dead (the census's) read stored figures")
        self.assertTrue(set(range(36, 41)) <= gated, "Ownership, Population Growth and the census's three")
        self.assertFalse({32, 34} & gated, "City Rank and Company Headquarters paint every state")
        self.assertEqual(self.no_data("map_color"), gated, "map_color's 'no data' OR")
        self.assertEqual(self.no_data("map_tooltip"), gated, "map_tooltip's 'no data' OR")

    def test_a_years_figures_wait_for_a_step(self):
        # a seed writes births, deaths and migration as 0, and no causes of death (te_demog_state_stepped_sgui): those
        # maps show grey until the state's first full year
        for sel in (7, 8, 9, 11, 13, 35):
            for key in ("map_color", "map_tooltip"):
                for body in self.branches(key, sel):
                    self.assertRegex(body, r"var:te_dg_stepped\s*>\s*0", f"{key}, selector {sel}")

    def test_the_stored_figures_are_written(self):
        # tourism's Base Appeal and Local Climate's penalties are state_region chains too dear to evaluate per state as
        # the map paints, so each refresh stores the figure the map reads (and the map's guard names it)
        writes = {
            "te_tourism_base_appeal": ("common/scripted_effects/extra_effects.txt", "te_update_tourism_modifier",
                                       "tourism_bonus_from_base_appeal"),
            "te_climate_base_penalty": ("common/scripted_effects/local_climate_effects.txt",
                                        "te_update_local_climate_modifier", "te_climate_penalty_raw"),
            "te_climate_penalty_applied": ("common/scripted_effects/local_climate_effects.txt",
                                           "te_update_local_climate_modifier", "te_climate_penalty"),
        }
        for var, (rel, effect, value) in writes.items():
            body = block(code(rel), effect)
            self.assertRegex(body, r"set_variable\s*=\s*\{\s*name\s*=\s*" + var + r"\s+value\s*=\s*" + value + r"\s*\}",
                             f"{effect} doesn't store {var}")
            self.assertIn(f"has_variable = {var}", self.room, f"no map reads {var}")

    def test_the_current_pick_is_invalid_so_its_button_draws_pressed(self):
        for name, sel in self.picks().items():
            valid = block(block(self.sguis, name), "is_valid")
            self.assertRegex(valid, r"NOT\s*=\s*\{\s*te_jmap_selector\s*=\s*" + str(sel) + r"\s*\}", name)

    def test_every_pick_has_a_button(self):
        row = block(code(PICKS_GUI), "te_jmap_pick_row")
        self.assertIsNotNone(row)
        seen = []
        for m in re.finditer(r"\bte_jmap_pick_button\s*=\s*\{", row):
            button = enclosing(row, m.end())
            sguis = set(re.findall(r"GetScriptedGui\('(\w+)'\)", button))
            self.assertEqual(len(sguis), 1, f"one scripted GUI per button: {sguis}")
            name = sguis.pop()
            for call in ("IsShown", "IsValid", "Execute"):
                self.assertIn(f"GetScriptedGui('{name}').{call}(", button, f"{name}: no {call} on its button")
            key = name[:-len("_sgui")]
            self.assertIn(f'text = "{key}"', button, f"{name}: its button shows another pick's name")
            # its own description; for a map fitted to a range, only under the map's own curve, which is the
            # one that description describes (ScaleTooltipTest)
            plain = f'tooltip = "{key}_desc"'
            scaled = ("tooltip = \"[SelectLocalization( EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue("
                      f"'te_jmap_scale'), '(CFixedPoint)0' ), '{key}_desc', '{key}_scaled' )]\"")
            self.assertTrue((plain in button) != (scaled in button), f"{name}: its button shows another pick's tooltip")
            clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', button)
            self.assertEqual(len(clicks), 2, f"{name}: pick, then the repaint")
            self.assertIn(".Execute(", clicks[0], f"{name}: the pick runs first")
            # PdxGuiTriggerAllAnimations, not PdxGuiWidget.TriggerAnimation: the repaint's states sit on a widget
            # outside the page, which outlives the close (fifth session)
            self.assertEqual(clicks[1], "[PdxGuiTriggerAllAnimations('te_jmap_repaint')]", name)
            seen.append(name)
        self.assertEqual(sorted(seen), sorted(self.picks()), "one button per pick")

    def test_a_pick_reopens_the_page_to_repaint(self):
        # check 4 (2026-11-05): paused, reopening the page repainted the map. Fifth session: a state on the pick button
        # itself closed the page and never reopened it (ClosePanel then the DontToggle open, one on_finish after the
        # other). So the states sit on a scripted widget outside the page, which outlives the close, and the close and
        # the open are two states, so the open runs frames after the close has landed.
        host = top_level_widget(code(WIDGETS), REPAINTER)
        self.assertIn('datacontext = "[GetPlayerJournalEntry(\'je_te_map_room\')]"', host,
                      "the host names the entry itself: the pick button's datacontext goes with the page")
        states = {}
        for m in re.finditer(r"\bstate\s*=\s*\{", host):
            body = enclosing(host, m.end())
            states[re.search(r"name\s*=\s*(\w+)", body).group(1)] = body
        self.assertEqual(sorted(states), ["te_jmap_repaint", "te_jmap_repaint_open"])
        close, reopen = states["te_jmap_repaint"], states["te_jmap_repaint_open"]
        self.assertRegex(close, r"\bnext\s*=\s*te_jmap_repaint_open\b")
        for body in (close, reopen):
            self.assertRegex(body, r"duration\s*=\s*0?\.\d*[1-9]", "each state waits a beat")
        self.assertEqual(re.findall(r'on_finish\s*=\s*"([^"]*)"', close), ["[InformationPanelBar.ClosePanel]"])
        finish = re.findall(r'on_finish\s*=\s*"([^"]*)"', reopen)
        # the plain open, proven in game from a widget outside the page (the Demographics and Banking buttons); the
        # page is closed by now, so its toggle opens it. DontToggle has never been seen to work.
        self.assertEqual(finish[-1], "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]")
        self.assertIn("te_jmap_reopen_log_sgui", finish[0], "the reopen logs before it opens")
        # the pick button keeps no repaint state of its own: TriggerAllAnimations would fire it too
        self.assertNotRegex(block(code(WIDGETS), "te_jmap_pick_button"), r"\bstate\s*=")

    def test_the_repainter_is_registered(self):
        self.assertIn(f"{WIDGETS} = {REPAINTER}", code(REGISTRATION))

    def test_the_room_is_contextless_and_in_no_journal(self):
        # check 7 (2026-11-05): a contextless entry nobody is involved in is active from the start, in no journal, and
        # a button opens its page at the first click
        self.assertRegex(self.room, r"\bcontext\s*=\s*none\b")
        self.assertRegex(block(self.room, "should_be_involved"), r"always\s*=\s*no")
        self.assertRegex(block(self.room, "should_show_when_not_involved"), r"always\s*=\s*no")
        self.assertNotRegex(self.room, r"\bpossible\s*=", "possible defaults to yes: the room is active from the start")
        self.assertNotRegex(self.room, r"\boutcome\s*=", "the Map Room never concludes")

    def test_the_room_has_no_scripted_buttons(self):
        # check 14 (2026-11-05): the engine locks a contextless entry's scripted buttons for a country not involved
        self.assertNotRegex(self.room, r"\bscripted_button\s*=")

    def test_the_widget_is_mounted_and_defined(self):
        mount = block(self.room, "widget")
        self.assertIsNotNone(mount)
        self.assertIn(f'gui = "{ROOM_WIDGET}"', mount)
        name = re.search(r'name\s*=\s*"(\w+)"', mount).group(1)
        self.assertRegex(code(ROOM_WIDGET), r'name\s*=\s*"' + name + '"')
        self.assertIn("te_jmap_pick_row = {}", code(ROOM_WIDGET))

    def test_no_ai_use(self):
        for name in re.findall(r"^(te_jmap_\w+_sgui)\s*=\s*\{", self.sguis, re.M):
            self.assertRegex(block(self.sguis, name), r"ai_is_valid\s*=\s*\{\s*always\s*=\s*no\s*\}", name)


def branches_of(part):
    """[(limit, body)] for the top-level if / else_if / else of a map_color or map_tooltip block, whitespace collapsed;
    an else's limit is ""."""
    out = []
    for m in re.finditer(r"\b(if|else_if|else)\s*=\s*\{", part):
        start, end = enclosing_span(part, m.end())
        if part[:m.start()].count("{") - part[:m.start()].count("}") != 0:
            continue    # nested
        body = part[start:end]
        limit = block(body, "limit") if m.group(1) != "else" else ""
        rest = body
        if limit is not None and m.group(1) != "else":
            lm = re.search(r"\blimit\s*=\s*\{", body)
            ls, le = enclosing_span(body, lm.end())
            rest = body[:lm.start()] + body[le + 1:]
        out.append((" ".join((limit or "").split()), " ".join(rest.split())))
    return out


class SystemMapsTest(unittest.TestCase):
    """The systems' maps: each on its own entry and in the Map Room (selectors 18-25)."""

    def setUp(self):
        self.room = entry(HOST, "je_te_map_room")
        self.sguis = sguis()
        self.widgets = code(WIDGETS)

    def room_branches(self, key, sel):
        """The Map Room's branches for selector sel, the selector taken out of each limit."""
        out = []
        for limit, body in branches_of(block(self.room, key)):
            if re.search(r"(^| )te_jmap_selector = " + str(sel) + r"( |$)", limit) and "OR = {" not in limit:
                out.append((" ".join(re.sub(r"\bte_jmap_selector = " + str(sel) + r"\b", "", limit).split()), body))
        return out

    def test_each_entry_draws_the_map_room_s_map(self):
        # one map, two hosts: the entry's ladder and the Map Room's branches for its selector, in the same order, from
        # the same triggers and colors (te_journal_map_triggers.txt). A drift paints the two pages differently, silently.
        for sel, rel, key, *_ in SYSTEM_MAPS:
            for part in ("map_color", "map_tooltip"):
                with self.subTest(selector=sel, block=part):
                    room = self.room_branches(part, sel)
                    self.assertTrue(room, "no Map Room branch")
                    self.assertEqual(room[-1][0], "", "the map's last branch takes every state left")
                    if rel is None:
                        continue
                    mine = branches_of(block(entry(rel, key), part))
                    # Emissions' and Grandeur's lerp reads the Map Room's own factor here (te_jmap_<map>_room_factor,
                    # whose range follows the Map Room's options) and the entry's there; the rest is one text
                    room = [(limit, re.sub(r"\b(te_jmap_\w+)_room_factor\b", r"\1_factor", body))
                            for limit, body in room]
                    self.assertEqual(mine, room)

    def test_the_systems_maps_read_only_shared_triggers(self):
        # every limit of a system map is the shared triggers (yes, or a parameter block), so the entry and the Map Room
        # can't each grow their own reading
        names = set(re.findall(r"^(te_jmap_\w+)\s*=\s*\{", code(TRIGGERS), re.M))
        for sel, *_ in SYSTEM_MAPS:
            for part in ("map_color", "map_tooltip"):
                for limit, _body in self.room_branches(part, sel):
                    for call in re.findall(r"(\w+) = (?:yes|\{)", limit):
                        self.assertIn(call, names, f"selector {sel}, {part}: {call} is not a shared map trigger")

    def test_each_pick_waits_for_its_system(self):
        for sel, _rel, _key, pick, *_rest, gate in SYSTEM_MAPS:
            body = block(self.sguis, f"te_jmap_pick_{pick}_sgui")
            self.assertIsNotNone(body, pick)
            self.assertIn(gate, block(body, "is_shown"), pick)
            self.assertRegex(body, r"te_jmap_set_selector\s*=\s*\{\s*SEL\s*=\s*" + str(sel) + r"\s*\}")

    def test_each_system_tab_has_a_one_click_map_button(self):
        # the Map Room, not the system's own entry: several entries are held by only some countries, or not yet, and a
        # button on an entry nobody holds has nothing to open
        for _sel, _rel, _key, pick, button, tab, _gate in SYSTEM_MAPS:
            with self.subTest(button=button):
                name = f"te_jmap_{button}_map_button"
                self.assertIn(f"{name} = {{}}", code(tab), f"{name} isn't mounted in {tab}")
                body = block(self.widgets, name)
                self.assertIn("GetPlayerJournalEntry('je_te_map_room')", body)
                clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', body)
                self.assertEqual(len(clicks), 4, "unfade, note the viewer, pick, then open")
                self.assertEqual(clicks[0], "[GetVariableSystem.Clear('te_je_see_through')]")
                # the viewer first: a pick already made is invalid, and its effect (which notes it too) doesn't run
                self.assertIn("te_jmap_note_viewer_sgui", clicks[1])
                self.assertIn(f"te_jmap_pick_{pick}_sgui", clicks[2])
                self.assertEqual(clicks[3], "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]")

    def test_the_your_maps_follow_the_viewer(self):
        # a paint can't reach the player (is_player drew nothing, 2026-11-05): every pick and map button notes the
        # player's country as the viewer, and each month a player's pulse does too
        effects = code(EFFECTS)
        self.assertIn("te_jmap_note_viewer = yes", block(effects, "te_jmap_set_selector"))
        self.assertRegex(block(effects, "te_jmap_note_viewer"),
                         r"set_global_variable\s*=\s*\{\s*name\s*=\s*te_jmap_viewer\s*value\s*=\s*root\s*\}")
        self.assertIn("te_jmap_monthly_viewer", block(code(ON_ACTIONS), "on_monthly_pulse_country"))
        self.assertRegex(block(code(ON_ACTIONS), "te_jmap_monthly_viewer"), r"is_player\s*=\s*yes")
        self.assertIn("te_jmap_note_viewer_sgui", block(self.widgets, "te_jmap_window_button"))

    def test_the_monthly_pulse_keeps_another_players_view(self):
        # In multiplayer every player's pulse noted itself, so the shared view went to whoever's pulse ran last each
        # month (#1809). A player's pulse notes it only when there is no viewer, the viewer is no longer a player (it
        # left, or its player changed country), or it is the viewer already (the Nuclear Reach store's monthly rebuild).
        monthly = " ".join(block(code(ON_ACTIONS), "te_jmap_monthly_viewer").split())
        self.assertIn("if = { limit = { is_player = yes OR = { "
                      "NOT = { global_var:te_jmap_viewer ?= { is_player = yes } } "
                      "global_var:te_jmap_viewer ?= this } } te_jmap_note_viewer = yes }", monthly)
        self.assertEqual(monthly.count("te_jmap_note_viewer"), 1)

    def test_the_nuclear_map_shows_the_world_s_view_of_others(self):
        # nuclear.md's privacy rule: another country's true count never shows. The owner is read only through
        # nd_believed_armed and the public estimate; nd_is_armed is the viewer's own
        # nd_is_armed is read on nobody, the viewer included: in multiplayer another player sees the viewer's map
        trig = code(TRIGGERS)
        secret = ("nuclear_weapon_stockpile", "nd_is_armed", "nd_display_public_estimate", "nd_believed_stockpile",
                  "nd_stockpile")
        names = [n for n in re.findall(r"^(te_jmap_\w+)\s*=\s*\{", trig, re.M) if n.startswith(("te_jmap_nuke_",
                                                                                                "te_jmap_owner_"))]
        self.assertIn("te_jmap_nuke_guaranteed", names)
        for name in names:
            for word in secret:
                self.assertNotRegex(block(trig, name), r"\b" + word + r"\b", f"{name} reads {word}")
        for key, text in loc_values().items():
            if key.startswith("te_jmap_tt_nuke_"):
                for word in secret:
                    self.assertNotRegex(text, r"\b" + word + r"\b", key)
                if "ScriptValue(" in text:
                    self.assertIn("ScriptValue('nd_shown_public_estimate')", text, key)

    def test_the_political_models_are_the_pie_s_colors(self):
        import colorsys
        pie = dict(re.findall(r'\("(\w+)", "(#[0-9a-f]{6})"\)', read(CauseColorsTest.PIE)))
        text = code(COLORS)
        models = re.findall(r"te_jmap_ch_model = \{ MODEL = (\d+) \}\s*\}\s*value = \"te_jmap_ch_(\w+)\"",
                            code(HOST))
        self.assertEqual([int(n) for n, _ in models], list(range(1, 16)), "one branch per model code")
        for _n, model in models:
            h = pie[model]
            hsv = colorsys.rgb_to_hsv(*(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)))
            m = re.search(r"\bte_jmap_ch_" + model + r"\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}", text)
            self.assertIsNotNone(m, model)
            want = (round(hsv[0] * 360), round(hsv[1] * 100), round(hsv[2] * 100))
            self.assertEqual(tuple(int(x) for x in m.groups()), want, f"te_jmap_ch_{model} vs the pie's {h}")

    def test_the_model_codes_are_the_census_s(self):
        # ch_set_political_model's codes, in order (cultural_hegemony_effects.txt's code table)
        table = read("common/scripted_effects/cultural_hegemony_effects.txt")
        for n, model in re.findall(r"te_jmap_ch_model = \{ MODEL = (\d+) \}\s*\}\s*value = \"te_jmap_ch_(\w+)\"",
                                   code(HOST)):
            self.assertRegex(table, r"\b" + n + r"\s*=?\s*" + model + r"\b", f"code {n} is not {model}")


class ScriptChangesTest(unittest.TestCase):
    """The maps' figures the systems keep for them, since a paint can't walk pops."""

    def test_emissions_are_kept_per_state_in_the_one_yearly_walk(self):
        body = block(code("common/scripted_effects/global_warming_effects.txt"), "gw_snapshot_country_emissions_effect")
        state = body.index("name = gw_state_emis")
        country = body.index("name = gw_disp_country_emis")
        self.assertLess(state, country, "each state's figure first, then the country's as their sum")
        self.assertIn("value = gw_country_emis_from_states", body)
        self.assertNotIn("country_greenhouse_gas_emissions_script_value", body, "a second walk of the pops")

    def test_colonies_are_marked_in_the_pass_that_counts_them(self):
        body = block(code("common/scripted_effects/colonial_empire_display_effects.txt"),
                     "colonial_empire_refresh_display")
        mark = body.index("name = te_jmap_ce_colony")
        self.assertLess(mark, body.index("name = colonial_empire_colony_count"))
        self.assertIn("value = te_jmap_ce_colony_count", body)
        self.assertEqual(body.count("is_overseas_colonial_state"), 1, "one colony test per state")

    def test_the_basins_are_set_from_the_first_month_and_each_january(self):
        # each January too: a coastal state made after the first month (a colony) would otherwise wait for a claimant
        effects = code("common/scripted_effects/te_global_commons_seabed_effects.txt")
        at = effects.index("set_global_variable = te_seabed_basins_set")
        limit = enclosing(effects, effects.rindex("limit = {", 0, at) + len("limit = {"))
        self.assertNotIn("abyssal_plain_mining", limit)
        self.assertIn("NOT = { has_global_variable = te_seabed_basins_set }", limit)
        self.assertRegex(limit, r"\bmonth = 0\b")
        self.assertIn("te_seabed_ensure_state_basin = yes", enclosing(effects, at))

    def test_the_emissions_map_reads_nothing_beside_its_guard(self):
        # a multi-child NOT reads every child (scripting_best_practices.md), so a figure an OR guards is read anyway
        trig = code(TRIGGERS)
        for name in ("te_jmap_gw_no_data", "te_jmap_gw_removal"):
            self.assertNotRegex(block(trig, name), r"\b(?:var|global_var):", name)


class PowerGridMapTest(unittest.TestCase):
    """The Power Grids map (31): each grid's color is chosen by the monthly balancing, kept on its members."""

    GRID_EFFECTS = "common/scripted_effects/power_grid_effects.txt"
    GRID_TRIGGERS = "common/scripted_triggers/power_grid_triggers.txt"

    def test_each_grid_is_colored_after_its_record(self):
        balance = block(code(self.GRID_EFFECTS), "te_grid_balance_region_effect")
        self.assertLess(balance.index("te_grid_record_effect = yes"), balance.index("te_grid_map_color_effect = yes"))

    def test_the_color_is_one_of_the_twelve_and_avoids_neighbours(self):
        body = block(code(self.GRID_EFFECTS), "te_grid_map_color_effect")
        self.assertIn("te_grid_map_color_taken = yes", body)
        self.assertIn("local_var:te_grid_color <= 12", body)
        self.assertIn("set_variable = { name = te_grid_map_color value = local_var:te_grid_color }", body)
        taken = block(code(self.GRID_TRIGGERS), "te_grid_map_color_taken")
        self.assertIn("any_neighbouring_state", taken)
        self.assertIn("var:te_grid_map_color = local_var:te_grid_color", taken)
        self.assertIn("NOT = { is_target_in_global_variable_list = { name = te_grid_region target = this } }", taken)

    def test_a_station_off_its_grid_drops_its_color(self):
        effects = code(self.GRID_EFFECTS)
        for name in ("te_grid_idle_station_effect", "te_grid_clear_state_effect"):
            self.assertIn("remove_variable = te_grid_map_color", block(effects, name), name)

    def test_every_grid_color_is_painted(self):
        room = entry(HOST, "je_te_map_room")
        colors = block(room, "map_color")
        for n in range(1, 13):
            self.assertRegex(colors, r"te_jmap_grid_color = \{ COLOR = " + str(n) + r" \}\s*\}\s*value = \"te_jmap_grid_"
                             + str(n) + '"')


class _RoomBranches:
    """The Map Room's map_color and map_tooltip branches, and those of one selector."""

    def setUp(self):
        self.room = entry(HOST, "je_te_map_room")
        self.colors = branches_of(block(self.room, "map_color"))
        self.hover = branches_of(block(self.room, "map_tooltip"))

    def of(self, part, sel):
        return [(limit, body) for limit, body in part if re.search(r"(^| )te_jmap_selector = " + str(sel) + r"( |$)",
                                                                   limit) and "OR = {" not in limit]


class NinthPassMapsTest(_RoomBranches, unittest.TestCase):
    """City Rank, Armed Forces, Company Headquarters and War Dead (selectors 32-35; owner's ask, 2026-11-08)."""

    def test_city_rank_is_tourism_s(self):
        # the first 20 by the Cities bonus tourism gives them, the rest by rank, a state the ranking misses pale
        colors = self.of(self.colors, 32)
        self.assertEqual([limit for limit, _ in colors],
                         ["te_jmap_selector = 32 tourism_bonus_from_urban_centers > 0",
                          "te_jmap_selector = 32 city_size_rank > 0", "te_jmap_selector = 32"])
        self.assertIn("factor = te_jmap_city_top_factor", colors[0][1])
        self.assertIn("factor = te_jmap_city_rest_factor", colors[1][1])
        self.assertEqual(colors[2][1], 'value = "te_jmap_none"')
        self.assertEqual([limit for limit, _ in self.of(self.hover, 32)], [limit for limit, _ in colors])
        tourism = code("common/script_values/tourism.txt")
        self.assertIn("value = var:state_city_size_rank", block(tourism, "city_size_rank"))
        self.assertIn("subtract = city_size_rank", block(tourism, "tourism_bonus_from_urban_centers"))

    def test_the_ranking_keeps_no_stale_rank(self):
        # the ranking reaches 501 states; a state that falls past them loses its rank instead of keeping its last
        body = block(code("common/on_actions/extra_on_actions.txt"), "city_rank_on_action")
        clear = body.index("remove_variable = state_city_size_rank")
        self.assertLess(clear, body.index("ordered_state"))
        self.assertIn("has_variable = state_city_size_rank", enclosing(body, clear))

    def test_armed_forces_reads_the_walk_s_soldiers(self):
        colors = self.of(self.colors, 33)
        self.assertEqual([limit for limit, _ in colors],
                         ["te_jmap_selector = 33 has_variable = te_dg_soldiers var:te_dg_soldiers > 0",
                          "te_jmap_selector = 33 has_variable = te_dg_soldiers"])
        self.assertEqual(colors[1][1], 'value = "te_jmap_none"', "a state with no soldiers is pale, not 'no data'")
        walk = code("common/scripted_effects/te_demog_effects.txt")
        self.assertIn("set_variable = { name = te_dg_soldiers value = local_var:te_dg_w_sold }", walk)
        # whatever the Demographics rule, as the walk runs
        self.assertEqual(block(block(sguis(), "te_jmap_pick_armed_forces_sgui"), "is_shown").split(),
                         ["is_player", "=", "yes"])

    def test_company_hqs_grey_without_one(self):
        # owner, 2026-11-08: a state without a headquarters is grey; one with any, by their profit summed
        colors = self.of(self.colors, 34)
        self.assertEqual([limit for limit, _ in colors],
                         ["te_jmap_selector = 34 has_variable = te_jmap_hq_n te_jmap_hq_profit > 0",
                          "te_jmap_selector = 34 has_variable = te_jmap_hq_n",
                          "te_jmap_selector = 34"])
        self.assertIn("factor = te_jmap_hq_factor", colors[0][1])
        self.assertEqual(colors[1][1], 'value = "te_jmap_hq_loss"')
        self.assertEqual(colors[2][1], 'value = "te_jmap_no_data"')
        # the hover's own ladder; the regional headquarters' line under it is a ladder of its own
        hover = [limit for limit, _ in self.of(self.hover, 34) if "te_jmap_rhq_n" not in limit]
        self.assertEqual(hover, [limit for limit, _ in colors])

    def test_the_hq_profit_sums_the_headquarters_only_where_one_stands(self):
        # A headquarters is found by its building group: the engine's per-company building types match no
        # has_building on the template type (2026-11-08, the first build painted every state grey).
        values = code(VALUES)
        for name, group, add in (("te_jmap_hq_walk_profit", "bg_company_headquarter", "add = weekly_profit"),
                                 ("te_jmap_hq_walk_count", "bg_company_headquarter", "add = 1"),
                                 ("te_jmap_rhq_walk_count", "bg_company_regional_headquarter", "add = 1")):
            walk = block(block(values, name), "every_scope_building")
            self.assertIn("is_building_group = %s" % group, walk, name)
            self.assertIn(add, walk, name)
        # The map, its hover and its range read the store's state variables, 0 where unset.
        for name, var in (("te_jmap_hq_profit", "te_jmap_hq_wp"), ("te_jmap_hq_count", "te_jmap_hq_n"),
                          ("te_jmap_rhq_count", "te_jmap_rhq_n")):
            body = " ".join(block(values, name).split())
            self.assertIn("if = { limit = { has_variable = %s } value = var:%s }" % (var, var), body, name)
            self.assertNotIn("every_scope_building", body, name)

    def test_the_hq_figures_are_stored_monthly_and_at_the_pick(self):
        store = " ".join(block(code(EFFECTS), "te_jmap_store_hqs").split())
        for var, walk in (("te_jmap_hq_n", "te_jmap_hq_walk_count"), ("te_jmap_hq_wp", "te_jmap_hq_walk_profit"),
                          ("te_jmap_rhq_n", "te_jmap_rhq_walk_count")):
            self.assertIn("set_variable = { name = %s value = %s }" % (var, walk), store)
            self.assertIn("remove_variable = %s" % var, store)
        self.assertTrue(store.startswith("every_state = {"), store[:40])
        monthly = " ".join(block(code(ON_ACTIONS), "te_jmap_monthly_ranges").split())
        # stored before the ranges read them, and before the two self-checks
        self.assertLess(monthly.index("te_jmap_store_hqs = yes"), monthly.index("te_jmap_refresh_range = yes"))
        self.assertLess(monthly.index("te_jmap_store_hqs = yes"), monthly.index("te_jmap_hq_found_selfcheck = yes"))
        pick = " ".join(block(code(EFFECTS), "te_jmap_set_selector").split())
        self.assertIn("if = { limit = { global_var:te_jmap_sel ?= 34 } te_jmap_store_hqs = yes }", pick)
        self.assertLess(pick.index("te_jmap_store_hqs = yes"), pick.index("te_jmap_refresh_range = yes"))

    def test_the_hq_store_is_self_checked(self):
        # TE_SELF_CHECK hq_found: once a game, armed on companies existing (not on what the store finds), so a store
        # that finds nothing speaks instead of staying silent as the first build's check did.
        body = block(code(EFFECTS), "te_jmap_hq_found_selfcheck")
        limit = " ".join(block(body, "limit").split())
        self.assertIn("NOT = { has_global_variable = te_jmap_hq_found_selfcheck_done }", limit)
        self.assertIn("any_company = { always = yes }", limit)
        self.assertNotIn("te_jmap_hq_n", limit)
        self.assertIn("TE_SELF_CHECK OK hq_found", body)
        self.assertIn("TE_SELF_CHECK BROKEN hq_found", body)

    def test_the_hq_profit_read_is_self_checked(self):
        # TE_SELF_CHECK hq_profit: once a game, only with three headquarters or more to read, from the monthly pulse
        body = block(code(EFFECTS), "te_jmap_hq_selfcheck")
        limit = block(body, "limit")
        self.assertIn("NOT = { has_global_variable = te_jmap_hq_selfcheck_done }", " ".join(limit.split()))
        self.assertRegex(limit, r"count\s*>=\s*3")
        self.assertIn("TE_SELF_CHECK OK hq_profit", body)
        self.assertIn("TE_SELF_CHECK BROKEN hq_profit", body)
        self.assertIn("te_jmap_hq_selfcheck = yes", block(code(ON_ACTIONS), "te_jmap_monthly_ranges"))
        self.assertIn("hq_profit", read(PLAYTEST))

    def test_war_dead_is_the_census_s(self):
        colors = self.of(self.colors, 35)
        self.assertEqual(len(colors), 2)
        self.assertIn("var:te_dg_dc_war > 0", colors[0][0])
        self.assertIn("factor = te_jmap_war_dead_factor", colors[0][1])
        self.assertEqual(colors[1][1], 'value = "te_jmap_none"', "a state that lost none is pale")
        self.assertIn("te_demog_cohorts_run = yes", block(block(sguis(), "te_jmap_pick_war_dead_sgui"), "is_shown"))

    def test_armed_forces_and_war_dead_share_a_row(self):
        # the census shares a country's war dead out to its states by their soldiers: the two read together
        row = block(code(PICKS_GUI), "te_jmap_pick_row")
        at = row.index('text = "te_jmap_pick_armed_forces"')
        self.assertIn('text = "te_jmap_pick_war_dead"', enclosing(row, enclosing_span(row, at)[0] - 1))


class SecondRoundMapsTest(_RoomBranches, unittest.TestCase):
    """Ownership, Population Growth, Family Planning, Health Care, Fighting-Age Men (36-40) and Company HQs' regional
    headquarters stripes (owner's ask, 2026-11-08, second round)."""

    def test_ownership_paints_the_leading_holder_faded_by_its_share(self):
        colors = self.of(self.colors, 36)
        holders = (("priv", 1), ("self", 2), ("ctry", 3))
        self.assertEqual([limit for limit, _ in colors],
                         [f"te_jmap_selector = 36 has_variable = te_dg_lv_priv te_jmap_own_lead = {n}" for _, n in holders]
                         + ["te_jmap_selector = 36 has_variable = te_dg_lv_priv"])
        palette = code(COLORS)
        for (short, _n), (_limit, body) in zip(holders, colors):
            self.assertEqual(body, f'lerp = {{ min_color = "te_jmap_own_{short}_pale" max_color = "te_jmap_own_{short}" '
                                   f'factor = te_jmap_own_factor }}')
            full = re.search(r"\bte_jmap_own_" + short + r"\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)", palette)
            pale = re.search(r"\bte_jmap_own_" + short + r"_pale\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)", palette)
            self.assertEqual(pale.group(1), full.group(1), f"{short}'s pale end keeps its hue")
            self.assertLess(int(pale.group(2)), int(full.group(2)), f"{short}'s pale end is paler")
        self.assertEqual(colors[-1][1], 'value = "te_jmap_none"', "a state with no capital is pale, not 'no data'")

    def test_ownership_reads_the_walk_s_levels(self):
        values = code(VALUES)
        lead = block(values, "te_jmap_own_lead")
        for var in ("te_dg_lv_priv", "te_dg_lv_self", "te_dg_lv_ctry"):
            self.assertIn(f"has_variable = {var}", block(lead, "limit"))
        self.assertIn("te_demog_wc_capital_levels >= 1", lead, "Dynastic Wealth's own test for capital to own")
        for name in ("te_jmap_own_lead_share", "te_jmap_own_priv_share", "te_jmap_own_self_share",
                     "te_jmap_own_ctry_share"):
            self.assertIn("divide = { value = te_demog_wc_capital_levels min = 1 }", block(values, name), name)
        walk = code("common/scripted_effects/te_demog_effects.txt")
        for var in ("priv", "self", "ctry"):
            self.assertIn(f"set_variable = {{ name = te_dg_lv_{var} value = local_var:te_dg_w_{var} }}", walk)

    def test_the_walk_s_maps_wait_for_no_rule(self):
        every = sguis()
        for name in ("te_jmap_pick_ownership_sgui", "te_jmap_pick_population_growth_sgui"):
            self.assertEqual(block(block(every, name), "is_shown").split(), ["is_player", "=", "yes"], name)
        for name in ("te_jmap_pick_family_planning_sgui", "te_jmap_pick_health_care_sgui",
                     "te_jmap_pick_fighting_age_men_sgui"):
            self.assertIn("te_demog_cohorts_run = yes", block(block(every, name), "is_shown"), name)

    def test_population_growth_is_walk_to_walk(self):
        body = block(code(VALUES), "te_jmap_pop_growth")
        self.assertIn("has_variable = te_dg_walk_pop_prev", body)
        self.assertLess(body.index("divide = var:te_dg_walk_pop_prev"), body.index("multiply = 1000"),
                        "the ratio first: tens of millions times 1,000 needn't fit the fixed point")
        self.assertIn("set_variable = { name = te_dg_walk_pop_prev value = var:te_dg_walk_pop }",
                      code("common/scripted_effects/te_demog_effects.txt"))

    def test_the_census_s_three_read_their_figures(self):
        for sel, factor, guard in ((38, "te_jmap_means_factor", "has_variable = te_dg_means"),
                                   (39, "te_jmap_health_factor", "has_variable = te_dg_acc"),
                                   (40, "te_jmap_fam_factor", "has_variable = te_dg_fam has_variable = te_dg_people")):
            colors = self.of(self.colors, sel)
            self.assertEqual([limit for limit, _ in colors], [f"te_jmap_selector = {sel} {guard}"], sel)
            self.assertIn(f"factor = {factor}", colors[0][1], sel)
            hovers = [limit for limit, _ in self.of(self.hover, sel)]
            self.assertTrue(all(limit.startswith(f"te_jmap_selector = {sel} {guard}") for limit in hovers), sel)

    def test_regional_headquarters_stripe_and_are_named(self):
        stripes = branches_of(block(self.room, "map_color_second"))
        # (not under Greyscale, where a stripe says one thing: PickTooltipTest)
        self.assertIn(("te_jmap_selector = 34 te_jmap_in_area = yes has_variable = te_jmap_rhq_n te_jmap_color < 2",
                       'value = "te_jmap_hq_regional"'), stripes)
        self.assertIn("custom_tooltip_no_bullet = te_jmap_tt_hq_regional", block(self.room, "map_tooltip"))
        body = block(code(VALUES), "te_jmap_rhq_walk_count")
        self.assertIn("is_building_group = bg_company_regional_headquarter", body)

    def test_the_new_rows(self):
        row = block(code(PICKS_GUI), "te_jmap_pick_row")

        def row_of(key):
            at = row.index(f'text = "te_jmap_pick_{key}"')
            inner = enclosing_span(row, at)[0] - 1
            return re.findall(r'text = "te_jmap_pick_(\w+)"', enclosing(row, inner))

        # Ownership and Investment beside their kind since the first tier joined Economy (#1976)
        self.assertEqual(row_of("ownership"), ["gini", "dynastic_wealth", "ownership"])
        self.assertEqual(row_of("investment"), ["company_hqs", "investment", "trade_capacity"])
        self.assertEqual(row_of("armed_forces"), ["armed_forces", "fighting_age_men", "war_dead"])
        self.assertEqual(row_of("population_growth"), ["population_growth", "net_migration", "crowding"])
        self.assertEqual(row_of("health_care"), ["health_care"])


def class_table():
    """journal_map_classes.py, the class maps' one table (#1975)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "journal_map_classes", os.path.join(REPO, "scripts", "generators", "journal_map_classes.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ClassMapsTest(_RoomBranches, unittest.TestCase):
    """Every pop type by its people and by its share of the people, with a Count/Share switch (owner, 2026-11-23,
    #1975; four shares since 2026-11-11). The family is generated (gen_journal_map_classes.py); this holds what it
    writes to the paint and the walk, test_journal_map_classes.py the generator."""

    def setUp(self):
        super().setUp()
        self.cls = class_table()

    def test_every_pop_type_has_two_maps(self):
        import json
        with open(os.path.join(REPO, "vanilla_parsed", "common", "pop_types.json"), encoding="utf-8") as f:
            vanilla = set(json.load(f))
        import re
        mod_types = set()
        mod = os.path.join(REPO, "common", "pop_types")
        for name in sorted(os.listdir(mod)) if os.path.isdir(mod) else []:
            with open(os.path.join(mod, name), encoding="utf-8-sig") as f:
                mod_types |= set(re.findall(r"^(\w+) = \{", f.read(), re.M))
        # the mod's own: Spacers (space forces personnel, 2026-11-24)
        self.assertEqual(mod_types, {"spacers"})
        self.assertEqual({c["pop"] for c in self.cls.CLASSES}, vanilla | mod_types, "every pop type, the mod's too, has a row")
        self.assertEqual(len(vanilla), 15)
        # the tenth pass's four shares keep their selectors, so a save holding one shows it
        shares = {c["pop"]: c["share_sel"] for c in self.cls.CLASSES}
        self.assertEqual([shares[p] for p in ("capitalists", "aristocrats", "clergymen", "academics")], [41, 42, 43, 44])

    def test_a_count_paints_people_a_doubling_at_a_time_and_a_share_the_share(self):
        for c in self.cls.CLASSES:
            pop, var = c["pop"], f"te_dg_cls_{c['pop']}"
            lerp = ('lerp = {{ min_color = "te_jmap_class_{0}_low" max_color = "te_jmap_class_{0}_high" '
                    'factor = te_jmap_{1}_factor }}')
            with self.subTest(pop=pop):
                count = f"te_jmap_selector = {c['count_sel']} has_variable = {var} var:{var} > 0"
                held = f"te_jmap_selector = {c['count_sel']} has_variable = {var}"
                self.assertEqual(self.of(self.colors, c["count_sel"]),
                                 [(count, lerp.format(pop, f"class_{pop}")), (held, 'value = "te_jmap_none"')])
                self.assertEqual(self.of(self.hover, c["count_sel"]),
                                 [(count, f"custom_tooltip_no_bullet = te_jmap_tt_class_{pop}"),
                                  (held, f"custom_tooltip_no_bullet = te_jmap_tt_class_{pop}_none")])
                share = (f"te_jmap_selector = {c['share_sel']} has_variable = {var} has_variable = te_dg_walk_pop "
                         "var:te_dg_walk_pop > 0")
                self.assertEqual(self.of(self.colors, c["share_sel"]), [(share, lerp.format(pop, f"class_{pop}_share"))])
                self.assertEqual(self.of(self.hover, c["share_sel"]),
                                 [(share, f"custom_tooltip_no_bullet = te_jmap_tt_class_{pop}")])
                value = " ".join(block(code(CLASS_VALUES), f"te_jmap_share_{pop}").split())
                self.assertIn(f"value = var:{var} divide = {{ value = var:te_dg_walk_pop min = 1 }}", value)
                # the hover's two figures: the people, then their share
                hover = loc_values()[f"te_jmap_tt_class_{pop}"]
                self.assertLess(hover.index(f"Var('{var}')"), hover.index(f"ScriptValue('te_jmap_share_{pop}')"))

    def test_the_class_branches_come_last(self):
        # every other map's branches before the 45 of the classes', so no other map pays for them
        order = [int(m) for limit, _ in self.colors for m in re.findall(r"^te_jmap_selector = (\d+)", limit)]
        first = min(i for i, sel in enumerate(order) if sel in self.cls.selectors())
        self.assertEqual(set(order[first:]), set(self.cls.selectors()))

    def test_the_switch_shows_one_of_a_class_s_two_buttons(self):
        row = block(code(PICKS_GUI), "te_jmap_pick_row")
        texts = re.findall(r'text = "te_jmap_pick_class_(\w+)"', row)
        for c in self.cls.CLASSES:
            pop = c["pop"]
            with self.subTest(pop=pop):
                # side by side in one row, the count first
                self.assertEqual(texts[texts.index(f"{pop}_count") + 1], f"{pop}_share")
                for kind, mode, sel in (("count", 0, c["count_sel"]), ("share", 1, c["share_sel"])):
                    body = block(sguis(), f"te_jmap_pick_class_{pop}_{kind}_sgui")
                    self.assertEqual(block(body, "is_shown").split(),
                                     ["is_player", "=", "yes", "te_jmap_class_mode", "=", str(mode)])
                    self.assertIn(f"te_jmap_set_selector = {{ SEL = {sel} }}", body)
                values = loc_values()
                self.assertEqual(values[f"te_jmap_pick_class_{pop}_count"], c["name"])
                self.assertEqual(values[f"te_jmap_pick_class_{pop}_share"], c["name"])
        # the Classes header says which kind the buttons pick, at its right
        header = enclosing(row, row.index('text = "te_jmap_cat_classes"'))
        header = enclosing(row, row.index(header) - 2)
        self.assertIn('text = "te_jmap_classes_now"', override(header, "right_text"))
        self.assertEqual(loc_values()["te_jmap_classes_now"],
                         "[SelectLocalization( EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_jmap_class_mode'), "
                         "'(CFixedPoint)0' ), 'te_jmap_classes_by_count', 'te_jmap_classes_by_share' )]")

    def test_the_switch_moves_a_class_map_to_its_other(self):
        effects = code(EFFECTS)
        mode = " ".join(block(effects, "te_jmap_set_class_mode").split())
        self.assertTrue(mode.startswith("set_global_variable = { name = te_jmap_opt_class value = $MODE$ } "
                                        "te_jmap_class_flip = yes"), mode)
        self.assertIn("value = global_var:te_jmap_opt_class", block(code(VALUES), "te_jmap_class_mode"))
        flip = branches_of(block(code(CLASS_EFFECTS), "te_jmap_class_flip"))
        expected = []
        for c in self.cls.CLASSES:
            expected += [(f"te_jmap_selector = {c['count_sel']} te_jmap_class_mode = 1",
                          f"te_jmap_set_selector = {{ SEL = {c['share_sel']} }}"),
                         (f"te_jmap_selector = {c['share_sel']} te_jmap_class_mode = 0",
                          f"te_jmap_set_selector = {{ SEL = {c['count_sel']} }}")]
        self.assertEqual(flip, expected)
        # greyed off a class map
        picked = block(code(CLASS_VALUES), "te_jmap_pick_class")
        self.assertEqual(sorted(int(n) for n in re.findall(r"te_jmap_selector = (\d+)", picked)), self.cls.selectors())
        for kind in ("count", "share"):
            self.assertEqual(block(block(sguis(), f"te_jmap_classes_{kind}_sgui"), "is_valid").split(),
                             ["te_jmap_pick_class", "=", "1"])

    def test_the_walk_counts_every_class_in_calls_of_its_own(self):
        walk = block(code("common/scripted_effects/te_demog_effects.txt"), "te_demog_walks")
        pops = walk.index("every_scope_pop = {")
        self.assertLess(walk.index("te_jmap_walk_init = yes"), pops)
        self.assertGreater(walk.index("te_jmap_walk_pop = yes"), pops)
        self.assertGreater(walk.index("te_jmap_walk_store = yes"), walk.index("te_demog_work_walk_store = yes"))
        effects, generated = code(EFFECTS), code(CLASS_EFFECTS)
        for part in ("init", "pop", "store"):
            self.assertIn(f"te_jmap_class_walk_{part} = yes", block(effects, f"te_jmap_walk_{part}"))
        pop = " ".join(block(generated, "te_jmap_class_walk_pop").split())
        store = " ".join(block(generated, "te_jmap_class_walk_store").split())
        self.assertEqual(sorted(re.findall(r"is_pop_type = (\w+)", pop)), sorted(c["pop"] for c in self.cls.CLASSES))
        for c in self.cls.CLASSES:
            p = c["pop"]
            self.assertIn(f"limit = {{ is_pop_type = {p} }} change_local_variable = {{ name = te_jmap_w_{p} "
                          "add = total_size }", pop)
            self.assertIn(f"set_variable = {{ name = te_dg_cls_{p} value = local_var:te_jmap_w_{p} }}", store)
        # no census gate: the counts are the walk's, as Armed Forces' soldiers; the tenth pass's names are gone
        self.assertNotIn("te_demog_cohorts_run", generated)
        for var in ("te_dg_capitalists", "te_dg_aristocrats", "te_dg_clergy", "te_dg_academics"):
            self.assertNotIn(var, generated)
            self.assertNotIn(var, code(HOST))


class ClassesAndTradeMapsTest(_RoomBranches, unittest.TestCase):
    """Trade Capacity and Investment (selectors 45-46; owner's asks, 2026-11-11). The classes beside them that day are
    ClassMapsTest's."""

    def test_trade_capacity_is_the_state_s_own(self):
        # owner, 2026-11-11: the state's own Trade Capacity, its Trade Center's, not its owner's trade (which painted
        # every state of a country alike)
        colors = self.of(self.colors, 45)
        self.assertEqual([limit for limit, _ in colors],
                         ["te_jmap_selector = 45 te_jmap_trade_capacity > 0", "te_jmap_selector = 45"])
        self.assertIn("factor = te_jmap_trade_factor", colors[0][1])
        self.assertEqual(colors[1][1], 'value = "te_jmap_none"', "a state with no Trade Capacity is pale")
        # the map's two lines, then the Trade Center's level
        self.assertEqual([limit for limit, _ in self.of(self.hover, 45)],
                         [limit for limit, _ in colors] +
                         ["te_jmap_selector = 45 te_jmap_in_area = yes has_building = building_trade_center"])
        values = code(VALUES)
        capacity = " ".join(block(values, "te_jmap_trade_capacity").split())
        self.assertTrue(capacity.startswith("value = modifier:state_trade_capacity_add"), capacity)
        self.assertIn("multiply = { value = 1 add = modifier:state_trade_capacity_mult min = 0 }", capacity)
        # a state's figure: nothing of its owner's in it
        self.assertNotIn("owner", capacity)
        self.assertNotIn("total_trade_value", capacity)
        # no stripes now that the color is the Trade Center's
        stripes = block(self.room, "map_color_second")
        self.assertNotIn("te_jmap_selector = 45", " ".join(stripes.split()))
        self.assertNotIn("te_jmap_trade_center", code("common/named_colors/te_journal_map_colors.txt"))
        # the hover keeps the owner's trade, for scale, and the Trade Center's level
        loc = loc_values()
        for key in ("te_jmap_tt_trade", "te_jmap_tt_trade_none"):
            self.assertIn("ScriptValue('te_jmap_trade_value')", loc[key], key)
        self.assertIn("ScriptValue('te_jmap_trade_capacity')", loc["te_jmap_tt_trade"])
        self.assertIn("limit = { exists = owner } owner = { add = total_trade_value }",
                      " ".join(block(values, "te_jmap_trade_value").split()))
        self.assertIn("value = b:building_trade_center.level", block(values, "te_jmap_trade_center_levels"))

    def test_investment_paints_what_the_owners_pay_in(self):
        colors = self.of(self.colors, 46)
        self.assertEqual([limit for limit, _ in colors],
                         ["te_jmap_selector = 46 has_variable = te_jmap_inv_cap te_jmap_invest_value > 0",
                          "te_jmap_selector = 46"])
        self.assertIn("factor = te_jmap_invest_factor", colors[0][1])
        self.assertEqual(colors[1][1], 'value = "te_jmap_none"', "a state that pays nothing is pale")
        self.assertEqual([limit for limit, _ in self.of(self.hover, 46)], [limit for limit, _ in colors])
        values = code(VALUES)
        # the owners' buildings by group, in profit only: a loss pays nothing in
        for name, groups in (("te_jmap_invest_walk_cap_profit", ("bg_financial_districts", "bg_company_headquarter")),
                             ("te_jmap_invest_walk_ari_profit", ("bg_manor_houses",))):
            walk = block(block(values, name), "every_scope_building")
            for group in groups:
                self.assertIn(f"is_building_group = {group}", walk, name)
            self.assertIn("weekly_profit > 0", walk, name)
            self.assertIn("add = weekly_profit", walk, name)
        # a regional headquarters pays its company's home
        self.assertNotIn("bg_company_regional_headquarter", block(values, "te_jmap_invest_walk_cap_profit"))
        # times the share each class reinvests, with efficiency
        for short, pop_type in (("cap", "capitalists"), ("ari", "aristocrats")):
            rate = " ".join(block(values, f"te_jmap_invest_rate_{short}").split())
            self.assertTrue(rate.startswith(f"value = modifier:state_{pop_type}_investment_pool_contribution_add "
                                            "min = 0 max = 1"), rate)
            self.assertIn(f"add = modifier:state_{pop_type}_investment_pool_efficiency_mult", rate)
            self.assertEqual(" ".join(block(values, f"te_jmap_invest_walk_{short}").split()),
                             f"value = te_jmap_invest_walk_{short}_profit multiply = te_jmap_invest_rate_{short}")
            # the paint and the hover read the store's variable, and walk nothing
            stored = " ".join(block(values, f"te_jmap_invest_{short}").split())
            self.assertIn("if = { limit = { has_variable = te_jmap_inv_%s } value = var:te_jmap_inv_%s }"
                          % (short, short), stored)
            self.assertNotIn("every_scope_building", stored)
        self.assertEqual(" ".join(block(values, "te_jmap_invest_value").split()),
                         "value = te_jmap_invest_cap add = te_jmap_invest_ari")

    def test_the_investment_figures_are_stored_at_the_pick_and_monthly_while_picked(self):
        effects = code(EFFECTS)
        store = " ".join(block(effects, "te_jmap_store_invest").split())
        self.assertTrue(store.startswith("every_state = {"), store[:40])
        for short in ("cap", "ari"):
            self.assertIn("set_variable = { name = te_jmap_inv_%s value = te_jmap_invest_walk_%s }" % (short, short),
                          store)
            self.assertIn("remove_variable = te_jmap_inv_%s" % short, store)
        pick = " ".join(block(effects, "te_jmap_set_selector").split())
        self.assertIn("if = { limit = { global_var:te_jmap_sel ?= 46 } te_jmap_store_invest = yes }", pick)
        self.assertLess(pick.index("te_jmap_store_invest = yes"), pick.index("te_jmap_refresh_range = yes"))
        # the world's buildings aren't walked for a map nobody is looking at
        monthly = " ".join(block(effects, "te_jmap_monthly_invest").split())
        self.assertTrue(monthly.startswith("if = { limit = { has_global_variable = te_jmap_sel "
                                           "global_var:te_jmap_sel = 46 }"), monthly[:90])
        self.assertLess(monthly.index("te_jmap_store_invest = yes"), monthly.index("te_jmap_invest_selfcheck = yes"))
        pulse = " ".join(block(code(ON_ACTIONS), "te_jmap_monthly_ranges").split())
        self.assertLess(pulse.index("te_jmap_monthly_invest = yes"), pulse.index("te_jmap_refresh_range = yes"))

    def test_the_reinvested_share_is_self_checked(self):
        # TE_SELF_CHECK invest_rate: once a game, armed on owners' buildings in profit, not on the figure it tests
        body = block(code(EFFECTS), "te_jmap_invest_selfcheck")
        limit = " ".join(block(body, "limit").split())
        self.assertIn("NOT = { has_global_variable = te_jmap_invest_selfcheck_done }", limit)
        self.assertIn("count >= 3", limit)
        self.assertIn("te_jmap_invest_walk_cap_profit > 0", limit)
        self.assertNotIn("te_jmap_invest_value", limit)
        self.assertNotIn("te_jmap_inv_cap", limit)
        self.assertIn("TE_SELF_CHECK OK invest_rate", body)
        self.assertIn("TE_SELF_CHECK BROKEN invest_rate", body)
        playtest = read("docs/testing/journal-map-modes-playtest.md")
        self.assertIn("invest_rate", playtest)

class PopulationDensityMapTest(_RoomBranches, unittest.TestCase):
    """Population Density (2026-11-16): people per km² of land, from the engine's people and the region area table."""

    def test_the_paint_and_the_hover(self):
        colors = self.of(self.colors, 47)
        self.assertEqual([limit for limit, _ in colors],
                         ["te_jmap_selector = 47 te_jmap_density > 0", "te_jmap_selector = 47"])
        self.assertIn("factor = te_jmap_density_factor", colors[0][1])
        self.assertEqual(colors[1][1], 'value = "te_jmap_none"', "a state with no people is pale")
        # whole people per km² from 10, hundredths below, where whole numbers would read 0
        hover = self.of(self.hover, 47)
        self.assertEqual([(limit, body) for limit, body in hover],
                         [("te_jmap_selector = 47 te_jmap_density >= 10", "custom_tooltip_no_bullet = te_jmap_tt_density"),
                          ("te_jmap_selector = 47 te_jmap_density > 0",
                           "custom_tooltip_no_bullet = te_jmap_tt_density_sparse"),
                          ("te_jmap_selector = 47", "custom_tooltip_no_bullet = te_jmap_tt_density_none")])
        loc = loc_values()
        for key, fmt in (("te_jmap_tt_density", "0"), ("te_jmap_tt_density_sparse", "2")):
            self.assertIn(f"ScriptValue('te_jmap_density')|{fmt}]", loc[key], key)
            self.assertIn("ScriptValue('te_jmap_density_area')", loc[key], key)

    def test_the_figure_is_the_state_s_people_over_its_share_of_the_region_s_land(self):
        values = code(VALUES)
        area = " ".join(block(values, "te_jmap_density_area").split())
        # the region's area from the table, read only once it is written
        self.assertIn("limit = { state_region = { has_variable = te_region_area } } value = te_region_area_km2", area)
        # shared out by province, so a split region's parts don't each claim the whole
        self.assertIn("divide = { value = state_region.num_provinces min = 1 } multiply = num_provinces", area)
        density = " ".join(block(values, "te_jmap_density").split())
        # the bareword head reads state_population (scripting_best_practices.md: a nested read can resolve to none)
        self.assertTrue(density.startswith("value = state_population divide = { value = te_jmap_density_area min = 1 }"),
                        density)
        self.assertIn("if = { limit = { te_jmap_density_area < 1 } value = 0 }", density)
        # cheap reads only: the paint walks nothing
        for body in (area, density):
            self.assertNotRegex(body, r"\b(?:every|any|ordered|random)_", body)
        # the table it reads is written at the game's start
        self.assertIn("te_region_area_on_action", block(code("common/on_actions/te_region_area_on_actions.txt"),
                                                        "on_game_started"))

    def test_it_sits_with_the_cities(self):
        row = block(code(PICKS_GUI), "te_jmap_pick_row")
        at = row.index('text = "te_jmap_pick_population_density"')
        inner = enclosing_span(row, at)[0] - 1
        # beside the people themselves since the first tier (#1976), City Rank on the group's last row
        self.assertEqual(re.findall(r'text = "te_jmap_pick_(\w+)"', enclosing(row, inner)),
                         ["population", "population_density", "urban_share"])
        population = CategoriesTest.CATEGORIES.index("population")
        bodies = [enclosing(row, m.end()) for m in re.finditer(r"\bte_jmap_category\s*=\s*\{", row)]
        self.assertIn('text = "te_jmap_pick_population_density"', bodies[population])


class FirstTierMapsTest(_RoomBranches, unittest.TestCase):
    """Living standards, the economy and politics (owner, 2026-11-23, #1976): ten maps of figures the mod reads
    elsewhere, each fitted to the world, so Map Options' area and the rest apply to them."""

    # selector -> (the factor its lerp reads, what that figure is, in te_journal_map_values.txt or the engine's)
    LIVE = {
        77: ("sol_expected", "te_jmap_sol_expected", "value = average_sol subtract = average_expected_sol"),
        80: ("gdp", "te_jmap_gdp_value", "value = gdp"),
        81: ("infra", "te_jmap_infra_balance", "value = infrastructure subtract = infrastructure_usage"),
        82: ("loyal", "te_jmap_loyal_net", "value = loyalist_fraction subtract = radical_fraction"),
    }

    def test_each_live_figure_is_the_engine_s(self):
        values = code(VALUES)
        for sel, (name, value, body) in self.LIVE.items():
            with self.subTest(map=name):
                self.assertEqual(" ".join(block(values, value).split()), body)
                self.assertTrue(any(f"te_jmap_{name}_factor" in b for _limit, b in self.of(self.colors, sel)))
        # Literacy and Population read the engine's own figures bare, every state
        scales = code(SCALES)
        self.assertIn("value = literacy_rate", block(scales, "te_jmap_literacy_input"))
        self.assertIn("value = state_population", block(scales, "te_jmap_people_input"))

    def test_wealth_is_the_walk_s_people_weighted_mean(self):
        effects = code(EFFECTS)
        self.assertIn("change_local_variable = { name = te_jmap_w_wealth add = te_jmap_pop_wealth }",
                      " ".join(block(effects, "te_jmap_walk_pop").split()))
        self.assertEqual(" ".join(block(code(VALUES), "te_jmap_pop_wealth").split()), "value = wealth multiply = total_size")
        store = " ".join(block(effects, "te_jmap_walk_store").split())
        self.assertIn("name = te_dg_wealth value = { value = local_var:te_jmap_w_wealth divide = { value = var:te_dg_walk_pop "
                      "min = 1 } }", store)
        # and SoL vs Wealth is the walk's two, guarded
        self.assertIn("value = var:te_dg_sol subtract = var:te_dg_wealth",
                      " ".join(block(code(VALUES), "te_jmap_sol_wealth").split()))

    def test_unemployment_is_stored_at_the_pick_and_monthly_while_picked(self):
        # a GUI reads state_unemployment_rate as none (scripting_best_practices.md), so neither the paint nor the
        # hover reads it: the store does, from an effect, as every other reader of the figure takes it
        effects = code(EFFECTS)
        store = " ".join(block(effects, "te_jmap_store_unemp").split())
        self.assertIn("set_variable = { name = te_jmap_unemp value = te_state_unemployment_share }", store)
        self.assertIn("global_var:te_jmap_sel ?= 78 } te_jmap_store_unemp = yes",
                      " ".join(block(effects, "te_jmap_set_selector").split()))
        self.assertIn("global_var:te_jmap_sel = 78 } te_jmap_store_unemp = yes",
                      " ".join(block(effects, "te_jmap_monthly_unemp").split()))
        monthly = block(code(ON_ACTIONS), "te_jmap_monthly_ranges")
        self.assertLess(monthly.index("te_jmap_monthly_unemp = yes"), monthly.index("te_jmap_refresh_range = yes"))
        for part in (block(self.room, "map_color"), block(self.room, "map_tooltip"), code(SCALES)):
            self.assertNotIn("state_unemployment_rate", part)
            self.assertNotIn("te_state_unemployment_share", part)
        self.assertNotIn("state_unemployment_rate", loc_values()["te_jmap_tt_unemp"])

    def test_the_hovers_read_the_engine_s_own_figures_where_it_has_them(self):
        values = loc_values()
        for key, call in (("te_jmap_tt_sol_expected", "GetExpectedStandardOfLivingAll"),
                          ("te_jmap_tt_literacy", "GetLiteracy"), ("te_jmap_tt_people", "GetPopulationSize"),
                          ("te_jmap_tt_infra", "GetInfrastructureBalance"), ("te_jmap_tt_loyal", "GetNumRadicals"),
                          ("te_jmap_tt_unemp", "GetNumUnemployedWorkingAdults")):
            self.assertIn(f"THIS.GetState.{call}", values[key], key)

    def test_a_state_with_nobody_is_pale_on_the_two_counts(self):
        for sel, name, figure in ((79, "people", "state_population > 0"), (80, "gdp", "te_jmap_gdp_value > 0")):
            colors = self.of(self.colors, sel)
            self.assertEqual([limit for limit, _ in colors], [f"te_jmap_selector = {sel} {figure}",
                                                              f"te_jmap_selector = {sel}"])
            self.assertEqual(colors[1][1], 'value = "te_jmap_none"')


class SecondTierMapsTest(_RoomBranches, unittest.TestCase):
    """Market Access, Pollution, Vacant Jobs, Below Expected SoL and Discrimination (owner, 2026-11-23, #1977): four
    engine figures the mod reads as a value for the first time, each with a once-a-game self-check, and a count of the
    yearly walk."""

    # selector -> (the factor its lerp reads, the script value of the engine's figure, that value's body)
    LIVE = {
        83: ("access", "te_jmap_market_access", "value = market_access"),
        84: ("pollution", "te_jmap_pollution", "value = state_region.pollution_amount"),
        85: ("jobs", "te_jmap_vacant_jobs", "value = available_jobs"),
        86: ("below_sol", "te_jmap_below_expected", "value = population_below_expected_sol"),
    }
    # the script value -> (the check's name in debug.log, its effect, a fact it arms on, read another way)
    CHECKS = {
        "te_jmap_market_access": ("market_access", "te_jmap_access_selfcheck", "te_jmap_infra_balance < 0"),
        "te_jmap_pollution": ("pollution_amount", "te_jmap_pollution_selfcheck", "state_region = { pollution_amount > 0 }"),
        "te_jmap_vacant_jobs": ("available_jobs", "te_jmap_jobs_selfcheck", "occupancy < 0.9"),
        "te_jmap_below_expected": ("below_expected_sol", "te_jmap_below_sol_selfcheck", "te_jmap_sol_expected < -1"),
    }

    def test_each_figure_is_the_engine_s_read_through_one_value(self):
        # the paint, the range, the hover and the self-check read one name
        values, scales = code(VALUES), code(SCALES)
        for sel, (name, value, body) in self.LIVE.items():
            with self.subTest(map=name):
                self.assertEqual(" ".join(block(values, value).split()), body)
                self.assertTrue(any(f"te_jmap_{name}_factor" in b for _limit, b in self.of(self.colors, sel)))
                self.assertEqual(" ".join(block(scales, f"te_jmap_{name}_input").split()), f"value = {value}")
                self.assertIn(value, self.CHECKS)

    def test_each_engine_figure_is_self_checked_once_a_game_whatever_the_pick(self):
        monthly = block(code(ON_ACTIONS), "te_jmap_monthly_ranges")
        effects, doc = code(EFFECTS), read(PLAYTEST)
        for value, (name, effect, arm) in self.CHECKS.items():
            body = block(effects, effect)
            with self.subTest(check=name):
                self.assertIn(f"{effect} = yes", monthly)
                self.assertIn(f'"TE_SELF_CHECK OK {name} ', body)
                self.assertIn(f'"TE_SELF_CHECK BROKEN {name} ', body)
                self.assertIn(f"set_global_variable = {effect}_done", body, "once a game")
                self.assertIn(value, body, "it checks the map's own read")
                self.assertNotIn("te_jmap_sel", body, "a game answers it before anyone picks the map")
                # it arms on three states holding a fact read another way, so a read of none everywhere can't pass
                limit = " ".join(block(body, "limit").split())
                self.assertRegex(limit, r"any_state = \{ count >= 3 ")
                self.assertIn(arm, limit)
                self.assertNotRegex(limit.replace(f"{effect}_done", ""), r"\b" + value + r"\b")
                # and the play-test list's Self-checks table names it, with its fallback
                self.assertIn(f"TE_SELF_CHECK OK {name}", doc)
                self.assertIn(f"TE_SELF_CHECK BROKEN {name}", doc)
        # the two with a trigger form vanilla or the mod already reads hold the value to it in every state
        flat = " ".join(block(effects, "te_jmap_pollution_selfcheck").split())
        for at in (0, 10):
            self.assertIn(f"AND = {{ state_region = {{ pollution_amount > {at} }} NOT = {{ te_jmap_pollution > {at} }} }}", flat)
        self.assertIn("AND = { available_jobs > 0 NOT = { te_jmap_vacant_jobs > 0 } }",
                      " ".join(block(effects, "te_jmap_jobs_selfcheck").split()))
        self.assertIn("## Self-checks", doc)

    def test_discrimination_is_the_walk_s_count_below_full_acceptance(self):
        effects = code(EFFECTS)
        flat = lambda name: " ".join(block(effects, name).split())
        self.assertIn("set_local_variable = { name = te_jmap_w_unacc value = 0 }", flat("te_jmap_walk_init"))
        self.assertIn("if = { limit = { pop_acceptance < acceptance_status_5 } change_local_variable = { name = "
                      "te_jmap_w_unacc add = total_size } }", flat("te_jmap_walk_pop"))
        self.assertIn("set_variable = { name = te_dg_unacc value = local_var:te_jmap_w_unacc }", flat("te_jmap_walk_store"))
        self.assertIn("value = var:te_dg_unacc divide = { value = var:te_dg_walk_pop min = 1 }",
                      " ".join(block(code(VALUES), "te_jmap_unacc_share").split()))
        self.assertTrue(any("te_jmap_unacc_factor" in b for _limit, b in self.of(self.colors, 87)))
        # the walk runs whatever the Demographics rule, so the pick has no gate
        self.assertEqual(block(block(sguis(), "te_jmap_pick_discrimination_sgui"), "is_shown").split(),
                         ["is_player", "=", "yes"])

    def test_a_clean_region_and_a_state_with_no_jobs_open_are_pale(self):
        for sel, figure in ((84, "te_jmap_pollution > 0"), (85, "te_jmap_vacant_jobs > 0")):
            colors = self.of(self.colors, sel)
            self.assertEqual([limit for limit, _ in colors], [f"te_jmap_selector = {sel} {figure}",
                                                              f"te_jmap_selector = {sel}"])
            self.assertEqual(colors[1][1], 'value = "te_jmap_none"')

    def test_the_hovers_read_the_engine_s_own_figures_where_it_has_them(self):
        # so a hover that read a script value as none would still show the engine's figure
        values = loc_values()
        for key, call in (("te_jmap_tt_access", "GetMarketAccess"),
                          ("te_jmap_tt_pollution", "GetStateRegion.GetPollutionImpact"),
                          ("te_jmap_tt_jobs", "GetNumUnemployedWorkingAdults"),
                          ("te_jmap_tt_below_sol", "GetPopulationRatioBelowExpectedStandardOfLiving")):
            self.assertIn(f"THIS.GetState.{call}", values[key], key)


class CategoriesTest(unittest.TestCase):
    """The Map Room's picks in collapsible groups by theme (owner's ask, 2026-11-11; by theme, not by game system,
    2026-11-23, #1974)."""

    CATEGORIES = ("population", "families", "living", "classes", "economy", "politics", "military", "land")
    # the group whose every map is the census's: its header hides while it doesn't run (Living Conditions did too,
    # until the first tier's living-standard maps joined it, #1976)
    GATED = ("families",)

    def setUp(self):
        self.row = block(code(PICKS_GUI), "te_jmap_pick_row")

    def headers(self):
        return [enclosing(self.row, m.end()) for m in re.finditer(r"\bte_jmap_category_header\s*=\s*\{", self.row)]

    def bodies(self):
        return [enclosing(self.row, m.end()) for m in re.finditer(r"\bte_jmap_category\s*=\s*\{", self.row)]

    def test_each_category_has_a_header_and_rows(self):
        headers, bodies = self.headers(), self.bodies()
        self.assertEqual([re.search(r'text = "te_jmap_cat_(\w+)"', h).group(1) for h in headers],
                         list(self.CATEGORIES))
        self.assertEqual(len(bodies), len(self.CATEGORIES))
        keys = loc_keys()
        for cat, header, body in zip(self.CATEGORIES, headers, bodies):
            flag = f"te_jmap_cat_{cat}_open"
            with self.subTest(category=cat):
                self.assertIn(f"te_jmap_cat_{cat}", keys)
                # _open: it starts collapsed (gui_style_guide.md, Sections)
                self.assertIn(f"onclick = \"[GetVariableSystem.Toggle('{flag}')]\"", header)
                self.assertIn(f"visible = \"[Not(GetVariableSystem.Exists('{flag}'))]\"",
                              override(header, "onclick_showmore"))
                self.assertIn(f"visible = \"[GetVariableSystem.Exists('{flag}')]\"", override(header, "onclick_showless"))
                # the rows' own visible, before any row's: open, and (for a gated group) shown
                self.assertIn(f"GetVariableSystem.Exists('{flag}')", re.search(r'visible = "([^"]*)"', body).group(1))
                self.assertIn("te_jmap_pick_button = {", body)

    def test_a_group_of_census_maps_hides_with_the_census(self):
        # with the census off, Families and Ages has nothing to open: header and rows go
        shown = "GetScriptedGui('te_jmap_cat_{0}_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"
        for cat, header, body in zip(self.CATEGORIES, self.headers(), self.bodies()):
            own = re.findall(r'visible = "[^"]*"', re.sub(r'blockoverride\s+"\w+"\s*\{[^{}]*\}', "", header))
            with self.subTest(category=cat):
                if cat in self.GATED:
                    self.assertEqual(own, [f'visible = "[{shown.format(cat)}]"'])
                    self.assertIn(f"visible = \"[And( GetVariableSystem.Exists('te_jmap_cat_{cat}_open'), "
                                  f"{shown.format(cat)} )]\"", body)
                    gate = block(block(sguis(), f"te_jmap_cat_{cat}_sgui"), "is_shown").split()
                    self.assertEqual(gate, ["is_player", "=", "yes", "te_demog_cohorts_run", "=", "yes"])
                else:
                    self.assertEqual(own, [], "a group with a map every player sees is always shown")
                    self.assertIsNone(block(sguis(), f"te_jmap_cat_{cat}_sgui"))
                for name in re.findall(r"GetScriptedGui\('(te_jmap_pick_\w+_sgui)'\)", body):
                    pick = block(block(sguis(), name), "is_shown")
                    self.assertEqual("te_demog_cohorts_run = yes" in pick, cat in self.GATED or name in {
                        "te_jmap_pick_net_migration_sgui", "te_jmap_pick_fighting_age_men_sgui",
                        "te_jmap_pick_war_dead_sgui", "te_jmap_pick_life_expectancy_sgui",
                        "te_jmap_pick_infant_mortality_sgui", "te_jmap_pick_leading_cause_sgui",
                        "te_jmap_pick_health_care_sgui"}, name)

    def test_every_pick_sits_in_one_category(self):
        seen = []
        for body in self.bodies():
            seen += re.findall(r'text = "te_jmap_pick_(\w+)"', body)
        everything = re.findall(r'text = "te_jmap_pick_(\w+)"', self.row)
        self.assertEqual(sorted(seen), sorted(everything), "a pick outside every category")
        self.assertEqual(len(seen), len(set(seen)), "a pick in two categories")

    def test_the_maps_sit_by_theme(self):
        # by theme, not by the system a map comes from: no Systems or Census group, and each system's map beside the
        # maps of its kind (owner, 2026-11-23)
        where = {}
        for cat, body in zip(self.CATEGORIES, self.bodies()):
            for key in re.findall(r'text = "te_jmap_pick_(\w+)"', body):
                where[key] = cat
        expected = {
            "population": ("population", "population_density", "urban_share", "city_rank", "population_growth",
                           "net_migration", "crowding"),
            "families": ("birth_rate", "death_rate", "natural_change", "fertility", "family_planning", "median_age",
                         "old_share", "sex_balance"),
            "living": ("standard_of_living", "wealth", "sol_vs_wealth", "sol_vs_expected", "below_expected_sol",
                       "literacy", "life_expectancy", "infant_mortality", "leading_cause", "health_care"),
            "classes": tuple(f"class_{c['pop']}_{kind}" for c in class_table().CLASSES for kind in ("count", "share")),
            "economy": ("gdp", "gdp_per_capita", "unemployment", "vacant_jobs", "gini", "dynastic_wealth", "ownership",
                        "company_hqs", "investment", "trade_capacity", "infrastructure", "market_access",
                        "power_grids", "grid_flows"),
            "politics": ("turmoil", "radicals_loyalists", "discrimination", "political_models", "united_nations",
                         "colonies"),
            "military": ("armed_forces", "fighting_age_men", "war_dead", "devastation", "nuclear", "nuclear_reach",
                         "networks"),
            "land": ("base_comfort", "current_comfort", "tourism_appeal", "pollution", "emissions", "ocean_basins",
                     "grandeur"),
        }
        self.assertEqual(where, {key: cat for cat, keys in expected.items() for key in keys})
        values = loc_values()
        names = {"population": "Population", "families": "Families and Ages", "living": "Living Conditions",
                 "classes": "Classes", "economy": "Economy", "politics": "Politics",
                 "military": "Military and Security", "land": "Land and Environment"}
        self.assertEqual({cat: values[f"te_jmap_cat_{cat}"] for cat in self.CATEGORIES}, names)
        for gone in ("society", "migration", "systems", "census"):
            self.assertNotIn(f"te_jmap_cat_{gone}", values, "a retired group's name")


def option_buttons():
    """[(scripted GUI, button body)] for every option button on the Map Room's page."""
    section = block(code(WIDGETS), "te_jmap_options")
    out = []
    for m in re.finditer(r"\bte_jmap_option_button\s*=\s*\{", section):
        body = enclosing(section, m.end())
        names = set(re.findall(r"GetScriptedGui\('(\w+)'\)", body))
        assert len(names) == 1, f"one scripted GUI per option button: {names}"
        out.append((names.pop(), body))
    return out


class OptionsTest(unittest.TestCase):
    """The Map Room's options (owner, 2026-11-14): Area, Outliers, since the thirteenth pass Scale, and since the
    fourteenth Color (ColorTest, below, has its paint)."""

    # scripted GUI -> (the effect it runs, its argument, the script value its button draws pressed from)
    OPTIONS = {
        "te_jmap_area_world_sgui": ("te_jmap_set_area", "AREA", 0, "te_jmap_area"),
        "te_jmap_area_continent_sgui": ("te_jmap_set_area", "AREA", 1, "te_jmap_area"),
        "te_jmap_area_market_sgui": ("te_jmap_set_area", "AREA", 2, "te_jmap_area"),
        "te_jmap_area_bloc_sgui": ("te_jmap_set_area", "AREA", 3, "te_jmap_area"),
        "te_jmap_area_country_sgui": ("te_jmap_set_area", "AREA", 4, "te_jmap_area"),
        "te_jmap_continent_europe_sgui": ("te_jmap_set_continent", "CONT", 1, "te_jmap_continent"),
        "te_jmap_continent_asia_sgui": ("te_jmap_set_continent", "CONT", 2, "te_jmap_continent"),
        "te_jmap_continent_africa_sgui": ("te_jmap_set_continent", "CONT", 3, "te_jmap_continent"),
        "te_jmap_continent_north_america_sgui": ("te_jmap_set_continent", "CONT", 4, "te_jmap_continent"),
        "te_jmap_continent_south_america_sgui": ("te_jmap_set_continent", "CONT", 5, "te_jmap_continent"),
        "te_jmap_continent_oceania_sgui": ("te_jmap_set_continent", "CONT", 6, "te_jmap_continent"),
        "te_jmap_trim_default_sgui": ("te_jmap_set_trim", "TRIM", 0, "te_jmap_trim"),
        "te_jmap_trim_none_sgui": ("te_jmap_set_trim", "TRIM", 1, "te_jmap_trim"),
        "te_jmap_trim_percent_sgui": ("te_jmap_set_trim", "TRIM", 2, "te_jmap_trim"),
        "te_jmap_scale_own_sgui": ("te_jmap_set_scale", "SCALE", 0, "te_jmap_scale"),
        "te_jmap_scale_linear_sgui": ("te_jmap_set_scale", "SCALE", 1, "te_jmap_scale"),
        "te_jmap_scale_log_sgui": ("te_jmap_set_scale", "SCALE", 2, "te_jmap_scale"),
        "te_jmap_scale_ranked_sgui": ("te_jmap_set_scale", "SCALE", 3, "te_jmap_scale"),
        "te_jmap_color_own_sgui": ("te_jmap_set_color", "COLOR", 0, "te_jmap_color"),
        "te_jmap_color_safe_sgui": ("te_jmap_set_color", "COLOR", 1, "te_jmap_color"),
        "te_jmap_color_grey_sgui": ("te_jmap_set_color", "COLOR", 2, "te_jmap_color"),
        "te_jmap_classes_count_sgui": ("te_jmap_set_class_mode", "MODE", 0, "te_jmap_class_mode"),
        "te_jmap_classes_share_sgui": ("te_jmap_set_class_mode", "MODE", 1, "te_jmap_class_mode"),
    }
    # Outliers is greyed on a map with no range and under the Ranked scale, which reads none: one reason each
    TRIM_VALID = "te_jmap_pick_fitted = 1 NOT = { te_jmap_scale = 3 }"
    TRIM_REASONS = ("SelectLocalization( EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_jmap_pick_fitted'), "
                    "'(CFixedPoint)1' ), 'te_jmap_trim_ranked_tt', 'te_jmap_trim_no_range_tt' )")
    # the options that can be greyed: (is_valid, what the tooltip shows in place of the option's own text)
    GREYED = {
        "te_jmap_area_bloc_sgui": ("is_in_power_bloc = yes", "'te_jmap_area_bloc_none_tt'"),
        "te_jmap_trim_default_sgui": (TRIM_VALID, TRIM_REASONS),
        "te_jmap_trim_none_sgui": (TRIM_VALID, TRIM_REASONS),
        "te_jmap_trim_percent_sgui": (TRIM_VALID, TRIM_REASONS),
        # the map's own curve is always there, to go back to
        "te_jmap_scale_linear_sgui": ("te_jmap_pick_fitted = 1", "'te_jmap_scale_no_range_tt'"),
        "te_jmap_scale_log_sgui": ("te_jmap_pick_fitted = 1", "'te_jmap_scale_no_range_tt'"),
        "te_jmap_scale_ranked_sgui": ("te_jmap_pick_fitted = 1", "'te_jmap_scale_no_range_tt'"),
        # and so are the map's own colors
        "te_jmap_color_safe_sgui": ("te_jmap_pick_fitted = 1", "'te_jmap_color_no_range_tt'"),
        "te_jmap_color_grey_sgui": ("te_jmap_pick_fitted = 1", "'te_jmap_color_no_range_tt'"),
        # the Count/Share switch acts on a class map alone (#1975)
        "te_jmap_classes_count_sgui": ("te_jmap_pick_class = 1", "'te_jmap_classes_no_class_tt'"),
        "te_jmap_classes_share_sgui": ("te_jmap_pick_class = 1", "'te_jmap_classes_no_class_tt'"),
    }

    def setUp(self):
        self.room = entry(HOST, "je_te_map_room")
        self.sguis = sguis()
        self.effects = code(EFFECTS)
        self.triggers = code(TRIGGERS)

    # ---- the paint ----
    def test_a_state_outside_the_area_is_greyed_first_whatever_the_map(self):
        # one stored mark, read before any selector: the cheapest test a paint can make, and under the world (no
        # state marked, as in a save from before the options) it is the only cost
        colors = branches_of(block(self.room, "map_color"))
        hover = branches_of(block(self.room, "map_tooltip"))
        self.assertEqual(colors[0], ("has_variable = te_jmap_out", 'value = "te_jmap_outside"'))
        self.assertEqual(hover[0], ("has_variable = te_jmap_out", "custom_tooltip_no_bullet = te_jmap_tt_outside"))
        for part in (colors, hover):
            self.assertEqual([i for i, (limit, _) in enumerate(part) if "te_jmap_out" in limit], [0])
        self.assertIn("te_jmap_outside", named_colors())
        # apart from "no data" grey, from the pale "nothing here" and from Power Grids' offline grey, each of which
        # can lie inside the area beside it
        colors_text = code(COLORS)
        hsv = {name: tuple(int(x) for x in re.search(
            r"\b" + name + r"\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", colors_text).groups())
            for name in ("te_jmap_outside", "te_jmap_no_data", "te_jmap_none", "te_jmap_grid_offline")}
        for other in ("te_jmap_no_data", "te_jmap_none", "te_jmap_grid_offline"):
            self.assertGreaterEqual(hsv[other][2] - hsv["te_jmap_outside"][2], 12, f"as dark as {other}")

    def test_no_stripes_and_no_second_line_outside_the_area(self):
        stripes = branches_of(block(self.room, "map_color_second"))
        self.assertEqual(len(stripes), 11)  # Greyscale's, the grids' hubs, the regional HQs, the seven causes and
        # Nuclear Reach's submarines over the bombers
        self.assertEqual(stripes[0][0], ColorTest.GREY_STRIPES)
        for limit, _body in stripes:
            self.assertIn(" te_jmap_in_area = yes ", limit)
        for limit, _body in stripes[1:]:
            self.assertRegex(limit, r"^te_jmap_selector = \d+ te_jmap_in_area = yes ", limit)
        # the hover's second chain starts at the second top-level `if`
        hover = block(self.room, "map_tooltip")
        second = hover[hover.index("custom_tooltip_no_bullet = te_jmap_tt_no_pick"):]
        lines = branches_of(second[second.index("if = {"):])
        self.assertEqual(len(lines), 12)  # 34, 45, the seven causes and Nuclear Reach's three
        for limit, _body in lines:
            self.assertRegex(limit, r"^te_jmap_selector = \d+ te_jmap_in_area = yes ", limit)
        self.assertEqual(" ".join(block(self.triggers, "te_jmap_in_area").split()),
                         "NOT = { has_variable = te_jmap_out }")

    def test_the_paint_asks_only_for_the_mark(self):
        # what the area is (a continent's regions, a market, a power bloc) is asked by the marking effect, once per
        # state per click or month; a paint, which may run per state per frame, never reaches for it
        for key in ("map_color", "map_color_second", "map_tooltip"):
            part = block(self.room, key)
            for word in ("te_jmap_state_in_area", "te_jmap_in_continent", "te_jmap_state_in_continent",
                         "is_in_same_power_bloc", "is_in_geographic_region", "region =", "market", "te_jmap_area",
                         "te_jmap_trim", "te_jmap_continent"):
                self.assertNotIn(word, part, f"{key} asks about the area: {word}")
        # nor do the factors: the area and the trim reach a paint only through the range's two stored globals
        scales = code(SCALES)
        factors = scales[:scales.index("te_jmap_states = {")]
        for word in ("te_jmap_out", "te_jmap_in_area", "te_jmap_area", "te_jmap_trim", "te_jmap_states"):
            self.assertNotIn(word, factors, word)

    def test_the_options_are_the_map_room_s_alone(self):
        # a player who limits the Map Room to Europe must not find Global Warming's own page greyed outside Europe,
        # nor its colors squeezed into Europe's range (test_journal_map_scales.py holds the ranges apart)
        for rel, key in SYSTEM_ENTRIES + ((BANKING, "je_banking_cycle"),):
            body = entry(rel, key)
            for word in ("te_jmap_out", "te_jmap_in_area", "te_jmap_outside", "_room_factor", "te_jmap_area"):
                self.assertNotIn(word, body, f"{key} reads the Map Room's options: {word}")

    # ---- the marks ----
    def test_the_mark_is_put_on_by_one_effect_at_a_click_a_pick_and_each_month(self):
        writers = [name for name in re.findall(r"^(\w+)\s*=\s*\{", self.effects, re.M)
                   if re.search(r"(set|remove)_variable\s*=\s*(\{\s*name\s*=\s*)?te_jmap_out\b", block(self.effects, name))]
        self.assertEqual(writers, ["te_jmap_mark_area"])
        mark = block(self.effects, "te_jmap_mark_area")
        # under the world nothing is walked unless some state may still carry a mark
        world = " ".join(mark[mark.index("te_jmap_area = 0"):mark.index("else = {")].split())
        self.assertIn("limit = { has_global_variable = te_jmap_marks } every_state = { limit = { has_variable = "
                      "te_jmap_out } remove_variable = te_jmap_out } remove_global_variable = te_jmap_marks", world)
        other = " ".join(mark[mark.index("else = {"):].split())
        self.assertIn("set_global_variable = te_jmap_marks", other)
        self.assertIn("limit = { te_jmap_state_in_area = yes }", other)
        self.assertIn("else = { set_variable = te_jmap_out }", other)
        for caller in ("te_jmap_set_selector", "te_jmap_apply_options"):
            self.assertIn("te_jmap_mark_area = yes", block(self.effects, caller), caller)
        monthly = block(code(ON_ACTIONS), "te_jmap_monthly_ranges")
        self.assertLess(monthly.index("te_jmap_mark_area = yes"), monthly.index("te_jmap_refresh_range = yes"))

    def test_an_area_that_lost_its_anchor_goes_back_to_the_world(self):
        # the viewer left its power bloc, or holds no state: every state would be outside, a map that looks broken
        mark = " ".join(block(self.effects, "te_jmap_mark_area").split())
        self.assertRegex(mark, r"^if = \{ limit = \{ te_jmap_area_holds = no \} debug_log = \"TE_JMAP area reset[^\"]*\" "
                         r"set_global_variable = \{ name = te_jmap_opt_area value = 0 \} \}")
        holds = " ".join(block(self.triggers, "te_jmap_area_holds").split())
        for area, test in ((1, "te_jmap_continent > 0"), (2, "global_var:te_jmap_viewer ?= { exists = market }"),
                           (3, "global_var:te_jmap_viewer ?= { is_in_power_bloc = yes }"),
                           (4, "global_var:te_jmap_viewer ?= { exists = capital }")):
            self.assertIn(f"limit = {{ te_jmap_area = {area} }} {test}", holds)
        self.assertTrue(holds.endswith("trigger_else = { always = yes }"))

    def test_each_area_is_tested_against_the_viewer(self):
        area = " ".join(block(self.triggers, "te_jmap_state_in_area").split())
        self.assertIn("limit = { te_jmap_area = 1 } te_jmap_state_in_continent = yes", area)
        self.assertIn("limit = { te_jmap_area = 2 } global_var:te_jmap_viewer ?= { market ?= { save_temporary_scope_as"
                      " = te_jmap_viewer_market } } market ?= { this = scope:te_jmap_viewer_market }", area)
        self.assertIn("limit = { te_jmap_area = 3 } global_var:te_jmap_viewer ?= { save_temporary_scope_as = "
                      "te_jmap_viewer_scope } owner ?= { OR = { this = scope:te_jmap_viewer_scope "
                      "is_in_same_power_bloc = scope:te_jmap_viewer_scope } }", area)
        self.assertIn("limit = { te_jmap_area = 4 } te_jmap_owner_is_viewer = yes", area)
        self.assertTrue(area.endswith("trigger_else = { always = yes }"), "the world takes every state")
        # the viewer is the player who clicks: every option notes it before it marks
        apply = block(self.effects, "te_jmap_apply_options")
        self.assertLess(apply.index("te_jmap_note_viewer = yes"), apply.index("te_jmap_mark_area = yes"))

    # ---- the options' values, scripted GUIs and buttons ----
    def test_the_options_default_to_what_the_map_room_showed(self):
        values = code(VALUES)
        for value, var in (("te_jmap_area", "te_jmap_opt_area"), ("te_jmap_continent", "te_jmap_opt_cont"),
                           ("te_jmap_trim", "te_jmap_opt_trim"), ("te_jmap_scale", "te_jmap_opt_scale"),
                           ("te_jmap_color", "te_jmap_opt_color")):
            self.assertEqual(" ".join(block(values, value).split()),
                             f"value = 0 if = {{ limit = {{ has_global_variable = {var} }} value = global_var:{var} }}")
        # globals, as the pick: they survive a save, and nothing else writes them
        for effect, arg, var in (("te_jmap_set_area", "AREA", "te_jmap_opt_area"),
                                 ("te_jmap_set_continent", "CONT", "te_jmap_opt_cont"),
                                 ("te_jmap_set_trim", "TRIM", "te_jmap_opt_trim"),
                                 ("te_jmap_set_scale", "SCALE", "te_jmap_opt_scale"),
                                 ("te_jmap_set_color", "COLOR", "te_jmap_opt_color")):
            self.assertRegex(block(self.effects, effect),
                             r"^\s*set_global_variable = \{ name = " + var + r" value = \$" + arg + r"\$ \}")

    def test_each_option_runs_its_effect_as_the_player(self):
        found = set(re.findall(r"^(te_jmap_(?:area|continent|trim|scale|color|classes)_\w+_sgui)\s*=\s*\{", self.sguis,
                               re.M))
        self.assertEqual(found, set(self.OPTIONS))
        for name, (effect, arg, number, _value) in self.OPTIONS.items():
            body = block(self.sguis, name)
            with self.subTest(option=name):
                self.assertRegex(body, r"scope\s*=\s*country")
                self.assertEqual(" ".join(block(body, "is_shown").split()), "is_player = yes")
                self.assertEqual(" ".join(block(body, "effect").split()), f"{effect} = {{ {arg} = {number} }}")
                valid = block(body, "is_valid")
                if name in self.GREYED:
                    self.assertEqual(" ".join(valid.split()), self.GREYED[name][0])
                else:
                    self.assertIsNone(valid, "nothing greys this option")

    def test_each_option_has_a_button_that_repaints_as_a_pick_does(self):
        buttons = option_buttons()
        self.assertEqual(sorted(name for name, _ in buttons), sorted(self.OPTIONS))
        for name, body in buttons:
            _effect, _arg, number, value = self.OPTIONS[name]
            key = name[:-len("_sgui")]
            scope = "GuiScope.SetRoot( GetPlayer.MakeScope ).End"
            with self.subTest(option=name):
                self.assertIn(f'text = "{key}"', body)
                clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', body)
                # the picks' own repaint, exactly: the option's effect, then the repainter's close and reopen
                self.assertEqual(clicks, [f"[GetScriptedGui('{name}').Execute( {scope} )]",
                                          "[PdxGuiTriggerAllAnimations('te_jmap_repaint')]"])
                self.assertIn(f"visible = \"[GetScriptedGui('{name}').IsShown( {scope} )]\"", body)
                # pressed while it is the option in force, read from the option itself
                self.assertIn(f"down = \"[EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('{value}'), "
                              f"'(CFixedPoint){number}' )]\"", body)
                if name in self.GREYED:
                    reason = self.GREYED[name][1]
                    self.assertIn(f"enabled = \"[GetScriptedGui('{name}').IsValid( {scope} )]\"", body)
                    self.assertIn(f"tooltip = \"[SelectLocalization( GetScriptedGui('{name}').IsValid( {scope} ), "
                                  f"'{key}_tt', {reason} )]\"", body)
                else:
                    self.assertNotIn("enabled =", body)
                    self.assertIn(f'tooltip = "{key}_tt"', body)
        # no repaint state on the button: TriggerAllAnimations would fire it too, and it dies with the page
        self.assertNotRegex(block(code(WIDGETS), "te_jmap_option_button"), r"\bstate\s*=")

    def test_the_repainter_is_the_picks_own(self):
        # one close-and-reopen for picks and options: no second repaint state anywhere
        widgets = code(WIDGETS)
        self.assertEqual(sorted(set(re.findall(r"PdxGuiTriggerAllAnimations\('(\w+)'\)", widgets))), ["te_jmap_repaint"])
        self.assertEqual(sorted(re.findall(r"^\s*name\s*=\s*(te_jmap_repaint\w*)", widgets, re.M)),
                         ["te_jmap_repaint", "te_jmap_repaint_open"])

    def test_the_section_is_below_the_picks_and_says_what_is_set(self):
        page = code(ROOM_WIDGET)
        self.assertLess(page.index("te_jmap_pick_row = {}"), page.index("te_jmap_options = {}"))
        section = block(code(WIDGETS), "te_jmap_options")
        header = enclosing(section, re.search(r"\bte_jmap_category_header\s*=\s*\{", section).end())
        flag = "te_jmap_options_open"    # _open: it starts collapsed (gui_style_guide.md, Sections)
        self.assertIn(f"onclick = \"[GetVariableSystem.Toggle('{flag}')]\"", header)
        self.assertIn(f"visible = \"[Not(GetVariableSystem.Exists('{flag}'))]\"", override(header, "onclick_showmore"))
        self.assertIn(f"visible = \"[GetVariableSystem.Exists('{flag}')]\"", override(header, "onclick_showless"))
        # the options in force show on the header while the section is closed
        self.assertIn('text = "te_jmap_options_now"', override(header, "right_text"))
        body = enclosing(section, re.search(r"\bte_jmap_category\s*=\s*\{", section).end())
        self.assertIn(f"visible = \"[GetVariableSystem.Exists('{flag}')]\"", body)
        # the continents show only while the area is one
        rows = body[body.index('text = "te_jmap_area_country"'):body.index('text = "te_jmap_options_outliers"')]
        self.assertIn("visible = \"[EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_jmap_area'), "
                      "'(CFixedPoint)1' )]\"", rows)
        self.assertEqual(rows.count("te_jmap_option_button = {"), 6)
        # and at the top of the page while any option is off its default
        notice = page[page.index('text = "te_jmap_room_pick_heading"'):page.index("te_jmap_pick_row = {}")]
        self.assertIn('text = "te_jmap_options_in_use"', notice)
        self.assertIn("visible = \"[EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_jmap_options_set'), "
                      "'(CFixedPoint)1' )]\"", notice)
        self.assertEqual(" ".join(block(code(VALUES), "te_jmap_options_set").split()),
                         "value = 0 if = { limit = { OR = { te_jmap_area > 0 te_jmap_trim > 0 te_jmap_scale > 0 "
                         "te_jmap_color > 0 } } value = 1 }")
        # what the two lines say is ColorTest's (test_the_header_and_the_line_name_only_what_is_off_its_default)

    def test_the_scale_row_and_what_the_page_says_of_a_ranked_map(self):
        section = block(code(WIDGETS), "te_jmap_options")
        body = enclosing(section, re.search(r"\bte_jmap_category\s*=\s*\{", section).end())
        # Area, Outliers, Scale, then the line on what the map was measured over
        order = [body.index(f'text = "{key}"') for key in ("te_jmap_options_area", "te_jmap_options_outliers",
                                                           "te_jmap_options_scale", "te_jmap_options_color",
                                                           "te_jmap_options_measured")]
        self.assertEqual(order, sorted(order))
        row = body[body.index('text = "te_jmap_options_scale"'):body.index('text = "te_jmap_options_color"')]
        self.assertEqual(re.findall(r'text = "te_jmap_scale_(\w+)"', row), ["own", "linear", "log", "ranked"])
        widths = [int(w) for w in re.findall(r"size = \{ (\d+) 30 \}", row)]
        self.assertEqual(len(widths), 4)
        self.assertLessEqual(sum(widths) + 3 * 4, 470)
        # a fitted map says what it was measured over; a Ranked one says how old its places can be instead, since
        # they are taken at the measure and a paint only reads them
        fitted = "EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_jmap_pick_fitted'), '(CFixedPoint)1' )"
        ranked = "EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('te_jmap_scale'), '(CFixedPoint)3' )"
        lines = {re.search(r'text = "(\w+)"', box).group(1): re.search(r'visible = "([^"]*)"', box).group(1)
                 for box in (enclosing(body, m.end()) for m in re.finditer(r"\btextbox\s*=\s*\{", body))}
        self.assertEqual(lines["te_jmap_options_measured"], f"[And( {fitted}, Not{ranked} )]")
        self.assertEqual(lines["te_jmap_options_measured_ranked"], f"[And( {fitted}, {ranked} )]")
        self.assertIn("te_jmap_options_no_range", lines)
        values = loc_values()
        self.assertIn("a month old at most", values["te_jmap_options_measured_ranked"])
        self.assertIn("te_jmap_shown_states", values["te_jmap_options_measured_ranked"])
        self.assertNotIn("left out", values["te_jmap_options_measured_ranked"], "Ranked leaves no state out")
        self.assertIn("te_jmap_shown_cut", values["te_jmap_options_measured"])

    def test_the_area_row_fits_the_page(self):
        # five buttons of their labels' widths in one row, inside the header's 470
        section = block(code(WIDGETS), "te_jmap_options")
        row = section[section.index('text = "te_jmap_area_world"') - 200:section.index('text = "te_jmap_area_country"')]
        widths = [int(w) for w in re.findall(r"size = \{ (\d+) 30 \}", row)]
        self.assertEqual(len(widths), 5)
        self.assertLessEqual(sum(widths) + 4 * 4, 470)

    # ---- the words ----
    def test_the_options_have_their_words(self):
        keys = loc_keys()
        wanted = {"te_jmap_tt_outside", "te_jmap_measured_area", "te_jmap_measured_trim"}
        for name in self.OPTIONS:
            key = name[:-len("_sgui")]
            wanted |= {key, key + "_tt"}
        for _valid, reason in self.GREYED.values():
            wanted |= set(re.findall(r"'(te_jmap_\w+_tt)'", reason))
        custom = code("common/customizable_localization/te_journal_map_custom_loc.txt")
        named = set(re.findall(r"localization_key\s*=\s*(\w+)", custom))
        texts = ["te_jmap_area_name", "te_jmap_area_text", "te_jmap_color_name", "te_jmap_color_short",
                 "te_jmap_color_text", "te_jmap_color_text_gw", "te_jmap_color_text_hq", "te_jmap_color_text_mid",
                 "te_jmap_color_text_none", "te_jmap_now",
                 "te_jmap_now_area", "te_jmap_now_color", "te_jmap_now_scale", "te_jmap_now_trim",
                 "te_jmap_scale_name", "te_jmap_scale_short", "te_jmap_scale_text", "te_jmap_scale_text_doubling",
                 "te_jmap_scale_text_mid", "te_jmap_scaled_range_lead", "te_jmap_set_color", "te_jmap_set_scale",
                 "te_jmap_trim_name", "te_jmap_trim_text"]
        self.assertEqual(sorted(re.findall(r"^(\w+)\s*=\s*\{", custom, re.M)), texts)
        self.assertEqual((wanted | named) - keys, set(), "loc keys missing")
        # every custom text is read somewhere, as [GetPlayer.GetCustom('<key>')]
        loc = "\n".join(loc_values().values())
        for text in texts:
            self.assertIn(f"[GetPlayer.GetCustom('{text}')]", loc, text)
            body = block(custom, text)
            self.assertRegex(" ".join(body.split()), r"text = \{ localization_key = \w+ \} *$",
                             f"{text} ends on a default with no trigger")

    def test_names_come_from_scopes_and_vanilla_s_keys(self):
        # a market's, a power bloc's and a country's names are read from the viewer, never typed; the continents'
        # and the three kinds of area carry vanilla's own names
        values = loc_values()
        self.assertEqual(values["te_jmap_area_text_market"],
                         "the [GetGlobalVariable('te_jmap_viewer').GetCountry.GetMarket.GetNameNoFormatting]")
        self.assertEqual(values["te_jmap_area_text_bloc"],
                         "[GetGlobalVariable('te_jmap_viewer').GetCountry.GetPowerBloc.GetNameNoFormatting]")
        self.assertEqual(values["te_jmap_area_text_country"],
                         "[GetGlobalVariable('te_jmap_viewer').GetCountry.GetNameNoFlag]")
        self.assertEqual((values["te_jmap_area_market"], values["te_jmap_area_bloc"], values["te_jmap_area_country"]),
                         ("$concept_market$", "$concept_power_bloc$", "$concept_country$"))
        # the bloc's name is asked for only while the viewer is in one
        custom = " ".join(block(code("common/customizable_localization/te_journal_map_custom_loc.txt"),
                                "te_jmap_area_text").split())
        self.assertIn("trigger = { te_jmap_area = 3 global_var:te_jmap_viewer ?= { is_in_power_bloc = yes } } "
                      "localization_key = te_jmap_area_text_bloc", custom)

    # ---- what only the game can show ----
    def test_the_unverified_reads_are_self_checked(self):
        monthly = block(code(ON_ACTIONS), "te_jmap_monthly_ranges")
        doc = read(PLAYTEST)
        for name, effect in (("area_mark", "te_jmap_area_selfcheck"), ("range_count", "te_jmap_range_selfcheck"),
                             ("rank_walk", "te_jmap_rank_selfcheck")):
            body = block(self.effects, effect)
            with self.subTest(check=name):
                self.assertIn(f"{effect} = yes", monthly)
                self.assertIn(f'"TE_SELF_CHECK OK {name} ', body)
                self.assertIn(f'"TE_SELF_CHECK BROKEN {name} ', body)
                self.assertIn(f"set_global_variable = {effect}_done", body, "once a game")
                self.assertIn(f"TE_SELF_CHECK OK {name}", doc)
                self.assertIn(f"TE_SELF_CHECK BROKEN {name}", doc)
        # each arms on enough states that an all-one-side answer means something
        self.assertRegex(block(self.effects, "te_jmap_area_selfcheck"), r"any_state = \{\s*count >= 20")
        self.assertRegex(block(self.effects, "te_jmap_range_selfcheck"), r"any_state = \{\s*count >= 20\s*gdp_per_capita > 0")
        # the rank's walk is checked on a fixed map whatever the Scale option, so a game answers it before anyone
        # picks Ranked: every state visited, none out of order, by the very walk a rank takes
        rank = block(self.effects, "te_jmap_rank_selfcheck")
        self.assertRegex(rank, r"any_state = \{\s*count >= 20\s*gdp_per_capita > 0")
        self.assertNotIn("te_jmap_scale", rank)
        self.assertRegex(" ".join(rank.split()), r"ordered_state = \{ limit = \{ gdp_per_capita > 0 \} order_by = "
                         r"te_jmap_gdppc_input_neg min = 0 max = 5000 check_range_bounds = no ")
        self.assertIn("global_var:te_jmap_sc_rank_seen = global_var:te_jmap_sc_rank_states", rank)
        self.assertNotIn("te_jmap_rank ", rank.replace("te_jmap_rank_selfcheck", ""), "the check stores no place")
        # not from a click: a tooltip that walked an option's effect would read the counts unset
        for caller in ("te_jmap_apply_options", "te_jmap_set_area", "te_jmap_set_scale", "te_jmap_set_selector",
                       "te_jmap_mark_area"):
            self.assertNotIn("selfcheck", block(self.effects, caller), caller)


class ColorTest(_RoomBranches, unittest.TestCase):
    """The Map Room's Color option (owner, 2026-11-14, the fourteenth pass): the map's own colors, colorblind-safe
    ramps or greyscale. A lerp's colors are literal names, so the option can't reach into a map's own branch: eleven
    shared branches open the paint instead, each taken only while the option is off its default, and color whatever
    fitted map is picked from one ramp. Nothing here has been seen in the game (play-test check 31)."""

    GREY_STRIPES = "te_jmap_color = 2 te_jmap_pick_fitted = 1 te_jmap_in_area = yes te_jmap_pick_ramp = 0"
    # The published stops, and the named colors that carry them (the colors file's comment has the sources):
    # ColorBrewer 2.0's five-class YlOrBr and PuOr, its nine-class Greys (classes 2 and 6), and the first color of
    # Tableau's Color Blind 10.
    SEQ = (("te_jmap_cb_seq_0", "#FFFFD4"), ("te_jmap_cb_seq_1", "#FED98E"), ("te_jmap_cb_seq_2", "#FE9929"),
           ("te_jmap_cb_seq_3", "#D95F0E"), ("te_jmap_cb_seq_4", "#993404"))
    DIV_LOW = (("te_jmap_cb_div_0", "#E66101"), ("te_jmap_cb_div_1", "#FDB863"), ("te_jmap_cb_div_mid_low", "#F7F7F7"))
    DIV_HIGH = (("te_jmap_cb_div_mid_high", "#F7F7F7"), ("te_jmap_cb_div_3", "#B2ABD2"), ("te_jmap_cb_div_4", "#5E3C99"))
    GREY = (("te_jmap_grey_low", "#F0F0F0"), ("te_jmap_grey_high", "#737373"))
    BELOW = ("te_jmap_cb_below", "#006BA4")
    # What a color looks like with no working L, M or S cones: Machado, Oliveira and Fernandes (2009), "A
    # Physiologically-based Model for Simulation of Color Vision Deficiency", doi 10.1109/TVCG.2009.113, the
    # paper's matrices at severity 1.0, applied to linear RGB (as the colorspacious package, 1.1.2, carries them).
    VISION = {
        "normal": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        "protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
        "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
        "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
    }

    def setUp(self):
        super().setUp()
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gen_journal_map_scales", os.path.join(REPO, "scripts", "generators", "gen_journal_map_scales.py"))
        self.gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gen)
        self.rows = sorted((s for s in self.gen.SCALES if self.gen.fitted(s) and self.gen.in_room(s)),
                           key=lambda s: s["sel"])
        self.generated = code(SCALES)
        self.named = {name: tuple(float(x) for x in hsv.split()) for name, hsv in
                      re.findall(r"^\s*([a-z0-9_]+)\s*=\s*hsv360\s*\{\s*([\d. ]+?)\s*\}", code(COLORS), re.M)}

    # ---- color arithmetic (sRGB, D65) ----
    @staticmethod
    def hex_rgb(text):
        return tuple(int(text[i:i + 2], 16) / 255 for i in (1, 3, 5))

    def rgb(self, name):
        import colorsys
        h, s, v = self.named[name]
        return colorsys.hsv_to_rgb(h / 360, s / 100, v / 100)

    @classmethod
    def lab(cls, rgb, vision="normal"):
        """CIELAB of an sRGB color as `vision` sees it."""
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        lin = [min(max(sum(m * c for m, c in zip(row, lin)), 0), 1) for row in cls.VISION[vision]]
        xyz = (0.4124564 * lin[0] + 0.3575761 * lin[1] + 0.1804375 * lin[2],
               0.2126729 * lin[0] + 0.7151522 * lin[1] + 0.0721750 * lin[2],
               0.0193339 * lin[0] + 0.1191920 * lin[1] + 0.9503041 * lin[2])
        f = [t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
             for t in (xyz[0] / 0.95047, xyz[1], xyz[2] / 1.08883)]
        return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])

    @staticmethod
    def apart(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

    @staticmethod
    def mixes(a, b, steps=8):
        """The colors between two stops as a lerp would mix them, in RGB and in HSV: nothing records which the
        engine's does, so a ramp has to hold under both."""
        import colorsys
        ha, hb = colorsys.rgb_to_hsv(*a), colorsys.rgb_to_hsv(*b)
        turn = hb[0] - ha[0]
        turn = turn - 1 if turn > 0.5 else turn + 1 if turn < -0.5 else turn
        out = {"rgb": [], "hsv": []}
        for i in range(steps + 1):
            t = i / steps
            out["rgb"].append(tuple(x + (y - x) * t for x, y in zip(a, b)))
            out["hsv"].append(colorsys.hsv_to_rgb((ha[0] + turn * t) % 1, ha[1] + (hb[1] - ha[1]) * t,
                                                  ha[2] + (hb[2] - ha[2]) * t))
        return out

    def run_of(self, stops, mix):
        """Every color a run of lerps through `stops` can show, under one way of mixing."""
        out = []
        for (a, _), (b, _) in zip(stops, stops[1:]):
            out += self.mixes(self.rgb(a), self.rgb(b))[mix]
        return out

    # ---- the option ----
    def test_only_the_paint_reads_the_option(self):
        effects = code(EFFECTS)
        body = " ".join(block(effects, "te_jmap_set_color").split())
        # a color changes nothing a range or a rank is measured over: no marking, no measure, only the global
        self.assertEqual(body, "set_global_variable = { name = te_jmap_opt_color value = $COLOR$ } debug_log = "
                         "\"TE_JMAP color $COLOR$ date=[TimeKeeper.GetCurrentDate.GetString]\"")
        room = self.room
        for key in ("map_tooltip",):
            self.assertNotIn("te_jmap_color", block(room, key), "the hover is the map's own under every color")
        # no factor branches on it, and no system's own entry reads it: an entry's page keeps its own colors
        factors = self.generated[:self.generated.index("te_jmap_pick_ramp = {")]
        self.assertNotIn("te_jmap_color", factors)
        for rel, name in SYSTEM_ENTRIES + ((BANKING, "je_banking_cycle"),):
            self.assertNotIn("te_jmap_color", entry(rel, name), name)
            self.assertNotIn("te_jmap_pick_", entry(rel, name), name)

    def test_the_shared_branches_open_the_paint(self):
        limits = [limit for limit, _ in self.colors]
        self.assertEqual(limits[0], "has_variable = te_jmap_out", "outside the area first, whatever the colors")
        shared = self.colors[1:12]
        seq, div_low, div_high = [n for n, _ in self.SEQ], [n for n, _ in self.DIV_LOW], [n for n, _ in self.DIV_HIGH]
        pairs = list(zip(seq, seq[1:])) + list(zip(div_low, div_low[1:])) + list(zip(div_high, div_high[1:]))
        want = []
        for ramp, base in ((1, 0), (2, 4)):
            for n in range(4):
                under = f" te_jmap_pick_factor < {0.25 * (n + 1):g}" if n < 3 else ""
                lo, hi = pairs[base + n]
                want.append((f"te_jmap_color = 1 te_jmap_pick_ramp = {ramp}{under}",
                             f'lerp = {{ min_color = "{lo}" max_color = "{hi}" factor = te_jmap_pick_q{n + 1} }}'))
        want.append(("te_jmap_color = 1 te_jmap_pick_below = yes", 'value = "te_jmap_cb_below"'))
        want.append(("te_jmap_color = 2 te_jmap_pick_ramp > 0",
                     'lerp = { min_color = "te_jmap_grey_low" max_color = "te_jmap_grey_high" factor = te_jmap_pick_factor }'))
        want.append(("te_jmap_color = 2 te_jmap_pick_fitted = 1", 'value = "te_jmap_no_data"'))
        self.assertEqual(shared, want)
        # each asks for the option first, so a default paint pays one comparison a branch; no other branch asks
        for limit in limits[1:12]:
            self.assertRegex(limit, r"^te_jmap_color = [12] ")
        for limit, body in self.colors[12:]:
            self.assertNotIn("te_jmap_color", limit + body)
            self.assertNotIn("te_jmap_pick_", limit + body)
        self.assertEqual(self.gen.RAMP_LERPS, 4)
        self.assertEqual((self.gen.COLOR_OWN, self.gen.COLOR_SAFE, self.gen.COLOR_GREY), (0, 1, 2))

    def test_greyscale_stripes_what_its_ramp_leaves(self):
        # a grey for "no data" would be a grey on the ramp, so under Greyscale a fitted map's other states (no
        # figure, none, off the scale) are one flat grey with stripes; outside the area stays slate, unstriped
        stripes = branches_of(block(self.room, "map_color_second"))
        self.assertEqual(stripes[0], (self.GREY_STRIPES, 'value = "te_jmap_grey_stripe"'))
        self.assertEqual(self.colors[11][0], "te_jmap_color = 2 te_jmap_pick_fitted = 1")
        self.assertLess(self.apart(self.lab(self.rgb("te_jmap_grey_stripe")), self.lab(self.rgb("te_jmap_no_data"))) * -1, -40,
                        "the stripes stand out of the grey under them")

    # ---- what the shared branches ask ----
    @staticmethod
    def lines(limit):
        return re.findall(r"\S+ (?:=|>=|<=|>|<) \S+", limit)

    def own_condition(self, scale):
        """The limit under which the map's own lerp paints a state, read from the paint in ladder order: the lerp
        branch's lines (less the pick, and less a three-color map's split) and the opposite of every branch of the
        same pick before it."""
        before, found = [], None
        for limit, body in self.of(self.colors[12:], scale["sel"]):
            lines = [ln for ln in self.lines(limit) if ln != f"te_jmap_selector = {scale['sel']}"]
            if body.startswith("lerp"):
                found = [ln for ln in lines if not re.fullmatch(r"te_jmap_\w+_factor < 0\.5", ln)]
                break
            self.assertEqual(len(lines), 1, f"{scale['name']}: an earlier branch of one line can be turned round")
            self.assertTrue(lines[0].endswith(" = yes"), lines[0])
            before.append(lines[0][:-len("yes")] + "no")
        self.assertIsNotNone(found, scale["name"])
        return before + found

    def test_a_ramp_takes_the_states_the_map_s_own_lerp_would(self):
        for scale in self.rows:
            with self.subTest(map=scale["name"]):
                self.assertEqual(sorted(self.own_condition(scale)), sorted(self.gen.painted(scale)))
        # where a row's lerp isn't limited by what its range is measured over, the row says so
        differ = sorted(s["name"] for s in self.rows if "paint" in s)
        # and the first tier's live maps, which paint every state and leave one with no people out of the range (#1976),
        # and two of the second tier's (#1977)
        self.assertEqual(differ, ["access", "below_sol", "comfort", "gdppc", "gw_room", "infra", "literacy", "loyal",
                                  "sol_expected"])
        # te_jmap_pick_ramp repeats each: the pick and its has_variable guards, then the rest inside them
        ramp = " ".join(block(self.generated, "te_jmap_pick_ramp").split())
        for scale in self.rows:
            guards = [ln for ln in self.gen.painted(scale) if ln.startswith("has_variable = ")]
            rest = [ln for ln in self.gen.painted(scale) if not ln.startswith("has_variable = ")]
            kind = 2 if scale["world"]["kind"] == "mid" else 1
            limit = " ".join([f"te_jmap_selector = {scale['sel']}"] + guards)
            inner = f"if = {{ limit = {{ {' '.join(rest)} }} value = {kind} }}" if rest else f"value = {kind}"
            with self.subTest(map=scale["name"]):
                self.assertIn(f"if = {{ limit = {{ {limit} }} {inner} }}", ramp)
        self.assertEqual(ramp.count("te_jmap_selector = "), len(self.rows))
        self.assertEqual(sorted(s["name"] for s in self.rows if self.gen.pick_ramp(s) == self.gen.RAMP_DIV),
                         ["comfort", "comfort_base", "growth", "infra", "loyal", "mig", "natural", "sex", "sol_expected",
                          "sol_wealth", "tfr", "wc"])

    def test_the_ramp_reads_the_factor_the_map_s_own_lerp_reads(self):
        pick = " ".join(block(self.generated, "te_jmap_pick_factor").split())
        for scale in self.rows:
            own = {re.sub(r"_(lower|upper)$", "", f) for _limit, body in self.of(self.colors[12:], scale["sel"])
                   for f in re.findall(r"factor = (\w+)", body)}
            with self.subTest(map=scale["name"]):
                self.assertEqual(own, {f"te_jmap_{scale['name']}_factor"})
                self.assertIn(f"if = {{ limit = {{ te_jmap_selector = {scale['sel']} }} value = "
                              f"te_jmap_{scale['name']}_factor }}", pick)
        self.assertEqual(pick.count("te_jmap_selector = "), len(self.rows))

    def test_a_factor_is_read_a_quarter_at_a_time(self):
        for n in range(1, 5):
            start = (n - 1) / 4
            want = "value = te_jmap_pick_factor " + (f"subtract = {start:g} " if start else "") + "multiply = 4 min = 0 max = 1"
            self.assertEqual(" ".join(block(self.generated, f"te_jmap_pick_q{n}").split()), want)
        # the paint's ladder and the quarters, against the generator's reference, the midpoint included
        for i in range(0, 1001):
            f = i / 1000
            branch = next((n + 1 for n in range(3) if f < 0.25 * (n + 1)), 4)
            along = min(max((f - (branch - 1) / 4) * 4, 0), 1)
            self.assertEqual((branch, round(along, 9)), tuple(round(x, 9) for x in self.gen.ramp_lerp(f)), f)
        # a map with a meaningful midpoint: just under it the last of the lower side's color, at it the upper side's
        # first, and the two are the same near white
        self.assertEqual(self.gen.ramp_lerp(0.5), (3, 0))
        self.assertLess(self.apart(self.lab(self.rgb("te_jmap_cb_div_mid_low")), self.lab(self.rgb("te_jmap_cb_div_mid_high"))), 3)

    def test_a_state_painted_below_its_scale_is_one_color_off_the_ramp(self):
        # every flat color a fitted map's own branches paint is "none", "no data", or below the scale; the last
        # are what te_jmap_pick_below gathers, each in its map's own ladder order
        below = {}
        for scale in self.rows:
            before = []
            for limit, body in self.of(self.colors[12:], scale["sel"]):
                lines = [ln for ln in self.lines(limit) if ln != f"te_jmap_selector = {scale['sel']}"]
                color = re.fullmatch(r'value = "(\w+)"', body)
                if color and color.group(1) not in ("te_jmap_none", "te_jmap_no_data"):
                    below[scale["sel"]] = (color.group(1), before + lines)
                before += [f"NOT = {{ {ln} }}" if not ln.endswith(" = yes") else ln[:-3] + "no" for ln in lines
                           if not ln.startswith("has_variable = ") and not re.fullmatch(r"te_jmap_\w+_factor < 0\.5", ln)]
        self.assertEqual({sel: color for sel, (color, _) in below.items()}, {18: "te_jmap_gw_removal", 34: "te_jmap_hq_loss"})
        trigger = " ".join(block(code(TRIGGERS), "te_jmap_pick_below").split())
        self.assertEqual(trigger, "OR = { AND = { te_jmap_selector = 34 has_variable = te_jmap_hq_n NOT = { te_jmap_hq_profit > 0 } } "
                         "AND = { te_jmap_selector = 18 te_jmap_gw_no_data = no te_jmap_gw_removal = yes } }")
        self.assertEqual(below[34][1], ["NOT = { te_jmap_hq_profit > 0 }", "has_variable = te_jmap_hq_n"])
        self.assertEqual(below[18][1], ["te_jmap_gw_no_data = no", "te_jmap_gw_removal = yes"])

    # ---- the ramps ----
    def test_the_stops_are_the_published_ones(self):
        for name, published in self.SEQ + self.DIV_LOW + self.DIV_HIGH + self.GREY + (self.BELOW,):
            with self.subTest(color=name):
                for mine, theirs in zip(self.rgb(name), self.hex_rgb(published)):
                    self.assertLessEqual(abs(mine - theirs), 3 / 255, "a whole hsv360 within a step or two of the hex")
        # the diverging ramp's middle is written once a side, with that side's hue, so a mix in HSV doesn't sweep
        for stops in (self.DIV_LOW, self.DIV_HIGH):
            self.assertEqual(self.named[stops[1][0]][0], self.named[stops[0 if stops is self.DIV_HIGH else 2][0]][0])
        self.assertEqual(len({self.named[name][0] for name, _ in self.GREY}), 1)
        text = read(COLORS)
        for source in ("ColorBrewer 2.0", "YlOrBr", "PuOr", "Greys", "Tableau's Color Blind 10", "colorbrewer2.org"):
            self.assertIn(source, text)

    def test_the_ramps_hold_under_each_color_vision_and_in_grey(self):
        special = {name: self.rgb(name) for name in ("te_jmap_outside", "te_jmap_no_data", "te_jmap_none")}
        for mix in ("rgb", "hsv"):
            runs = {"seq": self.run_of(self.SEQ, mix), "low": self.run_of(self.DIV_LOW, mix),
                    "high": self.run_of(self.DIV_HIGH, mix), "grey": self.run_of(self.GREY, mix)}
            for vision in self.VISION:
                labs = {key: [self.lab(c, vision) for c in run] for key, run in runs.items()}
                near = lambda run, name: min(self.apart(p, self.lab(special[name], vision)) for p in labs[run])
                with self.subTest(mix=mix, vision=vision):
                    # lightness never turns: low to high darkens, and each side of a midpoint darkens away from it
                    for key, down in (("seq", True), ("low", False), ("high", True), ("grey", True)):
                        steps = [b[0] - a[0] for a, b in zip(labs[key], labs[key][1:])]
                        self.assertTrue(all(s < 0.5 for s in steps) if down else all(s > -0.5 for s in steps), key)
                    # a stop is told from the next (9 mixes a lerp: every 8th point is a stop)
                    for key in ("seq", "low", "high"):
                        self.assertGreaterEqual(min(self.apart(a, b) for a, b in zip(labs[key][::9], labs[key][9::9])), 15)
                    # nothing on a ramp is taken for slate, for "no data" or for "none"
                    self.assertGreaterEqual(near("seq", "te_jmap_outside"), 40)
                    self.assertGreaterEqual(near("seq", "te_jmap_no_data"), 40)
                    self.assertGreaterEqual(near("seq", "te_jmap_none"), 12)
                    for side in ("low", "high"):     # a midpoint map has no "none"
                        self.assertGreaterEqual(near(side, "te_jmap_outside"), 18)
                        self.assertGreaterEqual(near(side, "te_jmap_no_data"), 10)
                    # the two sides of a midpoint are told apart, the same distance out (from each end to three
                    # quarters of the way in: at the midpoint itself they are one color)
                    arms = min(self.apart(a, b) for a, b in zip(labs["low"][:-4], labs["high"][::-1][:-4]))
                    self.assertGreaterEqual(arms, 19)
                    # a loss and a removal: the maps' own red and green sit too near the ramp for some eyes, the
                    # one color they take instead far from it and from every other flat color
                    below = self.lab(self.rgb("te_jmap_cb_below"), vision)
                    self.assertGreaterEqual(min(self.apart(p, below) for p in labs["seq"]), 50)
                    for name in special:
                        self.assertGreaterEqual(self.apart(below, self.lab(special[name], vision)), 25, name)
            # (the own red at a loss is within 5 of the ramp for an eye with no S cones, within 13 with no M)
            loss = self.rgb("te_jmap_hq_loss")
            self.assertLess(min(self.apart(self.lab(c, "tritan"), self.lab(loss, "tritan")) for c in runs["seq"]), 6)
        # Greyscale stops well short of slate, in lightness alone
        dark = self.lab(self.rgb("te_jmap_grey_high"))[0]
        self.assertGreaterEqual(dark - self.lab(self.rgb("te_jmap_outside"))[0], 25)
        self.assertEqual(self.named["te_jmap_grey_high"][1], 0)

    # ---- the rows and the two lines ----
    def test_the_color_row(self):
        section = block(code(WIDGETS), "te_jmap_options")
        body = enclosing(section, re.search(r"\bte_jmap_category\s*=\s*\{", section).end())
        row = body[body.index('text = "te_jmap_options_color"'):body.index('text = "te_jmap_options_classes"')]
        self.assertEqual(re.findall(r'text = "te_jmap_color_(\w+)"', row), ["own", "safe", "grey"])
        self.assertEqual(row.count("te_jmap_option_button = {"), 3)
        self.assertNotIn("size = {", row, "the option button's own 150")
        self.assertLessEqual(3 * 150 + 2 * 4, 470)
        values = loc_values()
        # the default has one name, whichever row it is on
        self.assertEqual(values["te_jmap_color_own"], "$te_jmap_scale_own$")
        self.assertEqual(values["te_jmap_scale_own"], "Map Default")
        self.assertEqual((values["te_jmap_color_safe"], values["te_jmap_color_grey"]), ("Colorblind-Safe", "Grayscale"))
        # nothing of the look can be checked here: the play-test list says what to look at, and what to do instead
        check = next(line for line in read(PLAYTEST).splitlines() if line.startswith("| 31 | Map Options: Color"))
        for words in ("Colorblind-Safe", "Grayscale", "GDP per Capita", "Fertility", "Company HQs", "All defaults",
                      "Odd hues between two stops", "Stripes missing under Grayscale", "Grayscale should mark the midpoint"):
            self.assertIn(words, check)

    def custom_text(self, name, options, depth=0):
        """A custom localization's text under `options`, its own splices and custom localizations resolved."""
        self.assertLess(depth, 6)
        custom = code("common/customizable_localization/te_journal_map_custom_loc.txt")
        values = loc_values()
        for text in re.finditer(r"text\s*=\s*\{", block(custom, name)):
            entry_body = enclosing(block(custom, name), text.end())
            trigger = block(entry_body, "trigger")
            if trigger is None or self.holds(" ".join(trigger.split()), options):
                key = re.search(r"localization_key\s*=\s*(\w+)", entry_body).group(1)
                return self.resolve(values[key], options, depth)
        self.fail(f"{name}: no text")

    def resolve(self, text, options, depth):
        values = loc_values()
        text = re.sub(r"\$(te_jmap_\w+)\$", lambda m: self.resolve(values[m.group(1)], options, depth + 1), text)
        return re.sub(r"\[GetPlayer\.GetCustom\('(\w+)'\)\]", lambda m: self.custom_text(m.group(1), options, depth + 1), text)

    def holds(self, trigger, options):
        m = re.fullmatch(r"OR = \{ (.*) \}", trigger)
        parts = re.findall(r"(te_jmap_\w+) (=|>) (\d+)", m.group(1) if m else trigger)
        self.assertTrue(parts, trigger)
        results = [(options[name] == int(n)) if op == "=" else (options[name] > int(n)) for name, op, n in parts]
        return any(results) if m else all(results)

    def test_the_header_and_the_line_name_only_what_is_off_its_default(self):
        values = loc_values()
        self.assertEqual(values["te_jmap_options_now"], "[GetPlayer.GetCustom('te_jmap_now')]")
        short = {"te_jmap_area": "Market", "te_jmap_trim": "Keep All", "te_jmap_scale": "Log", "te_jmap_color": "Colorblind"}
        full = dict(short, te_jmap_scale="Logarithmic", te_jmap_color="Colorblind-Safe")
        names = dict(values)
        for area, trim, scale, color in __import__("itertools").product((0, 2), (0, 1), (0, 2), (0, 1)):
            options = {"te_jmap_area": area, "te_jmap_trim": trim, "te_jmap_scale": scale, "te_jmap_color": color,
                       "te_jmap_continent": 0}
            options["te_jmap_options_set"] = int(any((area, trim, scale, color)))
            on = [key for key in ("te_jmap_area", "te_jmap_trim", "te_jmap_scale", "te_jmap_color") if options[key]]
            header = self.resolve(values["te_jmap_options_now"], options, 0).replace("$concept_market$", "Market")
            line = self.resolve(values["te_jmap_options_in_use"], options, 0).replace("$concept_market$", "Market")
            with self.subTest(set=on):
                self.assertEqual(header, ", ".join(short[key] for key in on) if on else "All defaults")
                # the line shows only while something is set, and names the same options in full
                self.assertEqual(line, "Map options in use: #b " + ", ".join(full[key] for key in on) + "#!")
        del names
        # at its longest the header's summary is 43 characters, "North America, Keep All, Ranked, Colorblind": about
        # 302 px in the page's font (EBGaramond 17) where the 470-wide header leaves about 296 beside its title at
        # full size and about 338 with the title at its smallest (measured against the game's fonts, 2026-11-14)
        longest = max(len(", ".join((a, t, c, k))) for a in ("North America", "South America", "Power Bloc")
                      for t in ("Keep All", "Trim 5%") for c in ("Linear", "Log", "Ranked") for k in ("Colorblind", "Gray"))
        self.assertLessEqual(longest, 43)
        self.assertEqual((values["te_jmap_scale_short_log"], values["te_jmap_color_short_safe"],
                          values["te_jmap_color_short_grey"], values["te_jmap_now_none"]),
                         ("Log", "Colorblind", "Gray", "All defaults"))
        self.assertNotIn("te_jmap_scale_short_own", values)
        self.assertNotIn("te_jmap_trim_short_default", values)


class PickTooltipTest(_RoomBranches, unittest.TestCase):
    """No tooltip describes a curve or a color that isn't the one in force (owner, 2026-11-14). A fitted pick's
    tooltip is four lines: what the map shows, with no word of a curve, a color or a range; the range now; the
    scale, in the map's own curve's words under Map Default and the scale in force's otherwise; and the colors, the
    map's own under Map Default and the palette in force's otherwise. The own curve's words are the generator's,
    from the knots the curve is written from."""

    # words for a curve's shape, and for a color: none belongs in what a map shows
    CURVE = ("half the color", "two-thirds", "most of the color", "halfway", "first fifth", "first third",
             "for each doubling", "of that span", "of the color", "straight")
    COLORS = ("red", "green", "blue", "yellow", "orange", "purple", "violet", "brown", "cream", "rust", "teal", "plum",
              "rose", "magenta", "amber", "oxblood", "gray", "grey", "pale", "gold", "navy", "khaki", "olive", "straw",
              "sand", "bronze", "lilac", "aqua", "aubergine", "brick", "white", "dark", "light", "striped", "stripes")

    def setUp(self):
        super().setUp()
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "gen_journal_map_scales", os.path.join(REPO, "scripts", "generators", "gen_journal_map_scales.py"))
        self.gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gen)
        self.values = loc_values()
        self.sguis = sguis()
        self.row = block(code(PICKS_GUI), "te_jmap_pick_row")

    def picks(self):
        """{pick key: its scale} for every map fitted to a range."""
        out = {}
        for scale in self.gen.SCALES:
            if self.gen.fitted(scale) and self.gen.in_room(scale):
                m = re.search(r"^(te_jmap_pick_\w+)_sgui\s*=\s*\{(?:(?!^\}).)*?SEL = " + str(scale["sel"]) + r"\b",
                              self.sguis, re.M | re.S)
                out[m.group(1)] = scale
        return out

    @staticmethod
    def select(option, own, other):
        return (f"[SelectLocalization( EqualTo_CFixedPoint( GetPlayer.MakeScope.ScriptValue('{option}'), "
                f"'(CFixedPoint)0' ), '{own}', '{other}' )]")

    def variant(self, scale):
        """Which of the palette-in-force texts a map takes, by what its paint can show besides its ramp."""
        if scale["world"]["kind"] == "mid":
            return "_mid"
        flat = {c for _limit, body in self.of(self.colors, scale["sel"]) for c in re.findall(r'^value = "(\w+)"$', body)}
        if "te_jmap_hq_loss" in flat:
            return "_hq"
        if "te_jmap_gw_removal" in flat:
            return "_gw"
        return "_none" if "te_jmap_none" in flat else ""

    def test_every_pick_has_one_tooltip(self):
        picks = self.picks()
        # 36 until the class maps (#1975), whose 30 took the four shares' place, the first tier's ten (#1976) and the
        # second tier's five (#1977), and Spacers' two (2026-11-24)
        self.assertEqual(len(picks), 36 - 4 + 30 + 10 + 5 + 2)
        for key in sorted(set(re.findall(r'text = "(te_jmap_pick_\w+)"', self.row))):
            self.assertIn(f'tooltip = "{key}_desc"', self.row, key)
        self.assertNotIn("SelectLocalization", self.row, "a pick's tooltip chooses its own parts")
        self.assertEqual([k for k in self.values if re.fullmatch(r"te_jmap_pick_\w+_scaled", k)], [])

    def test_a_fitted_pick_s_tooltip_is_true_under_every_scale_and_color(self):
        kinds = {"frac": "te_jmap_scale_in_force", "doubling": "te_jmap_scale_in_force_doubling",
                 "mid": "te_jmap_scale_in_force_mid"}
        for key, scale in self.picks().items():
            lines, n = self.values[f"{key}_desc"].split("\\n"), scale["name"]
            with self.subTest(pick=key):
                self.assertEqual(len(lines), 4)
                what, rng, curve, colors = lines
                # what it shows: nothing a scale or a palette could make untrue
                for words in self.CURVE:
                    self.assertNotIn(words, what)
                for word in self.COLORS:
                    self.assertNotRegex(what, r"(?i)\b" + word + r"\b")
                self.assertNotIn("ScriptValue", what, "the range has its own line")
                self.assertTrue(what.startswith("Color each state "), what)
                # the range now: the two figures, what leads them (Ranked reads no range) and what is left out
                self.assertTrue(rng.startswith("$te_jmap_scaled_lead$ $te_jmap_measured_area$: "), rng)
                self.assertTrue(rng.endswith("$te_jmap_measured_trim$"), rng)
                for end in ("lo", "hi"):
                    self.assertIn(f"ScriptValue('te_jmap_{n}_{end}')", rng)
                # the scale: the map's own curve under Map Default, the scale in force otherwise
                self.assertEqual(curve, self.select("te_jmap_scale", self.gen.curve_key(scale), kinds[scale["world"]["kind"]]))
                # the colors: the map's own under Map Default, the palette in force otherwise
                self.assertEqual(colors, self.select("te_jmap_color", f"{key}_colors",
                                                     "te_jmap_color_in_force" + self.variant(scale)))
                own = self.values[f"{key}_colors"]
                self.assertTrue(own.startswith("$te_jmap_color_text_own$ "), own)
                if scale["world"]["kind"] == "mid":
                    self.assertNotIn("low end", own, "a midpoint map's colors are told by the midpoint")
                else:
                    self.assertRegex(own, r"From [a-z -]+ at the low end (through [a-z]+ halfway )?to [a-z -]+ at the high\.")
                    self.assertEqual("halfway" in own, scale["three"], "a three-color map names its middle color")
                for mark, word in (("_none", " is pale."), ("_hq", "A loss is red"), ("_gw", "is green")):
                    self.assertEqual(word in own, self.variant(scale) == mark, f"{word!r} in {own!r}")
        self.assertEqual(self.values["te_jmap_color_text_own"], "$te_jmap_color$: #b $te_jmap_color_own$#!.")
        self.assertEqual(self.values["te_jmap_scale_text_own"], "$te_jmap_scale$: #b $te_jmap_scale_own$#!.")

    def test_the_own_curve_s_words_are_the_generator_s(self):
        rows = list(self.picks().values())
        keys = {self.gen.curve_key(s): self.gen.curve_words(s) for s in rows}
        self.assertEqual(sorted(k for k in self.values if k.startswith("te_jmap_curve_")), sorted(keys))
        for key, words in keys.items():
            self.assertEqual(self.values[key], "$te_jmap_scale_text_own$ " + words, key)
        # and the knots mean what the words say: the color a curve has reached at its knee, on its default range
        for scale in rows:
            w = scale["world"]
            lo, hi = w["default"]
            with self.subTest(map=scale["name"]):
                if w["kind"] == "frac" and len(w["knots"]) == 3:
                    x, y = w["knots"][1]
                    self.assertAlmostEqual(self.gen.world_factor(scale, lo, hi, lo + x * (hi - lo)), y, places=6)
                    self.assertIn(f"first {self.gen._share(x, True)} of the range", self.gen.curve_words(scale))
                elif w["kind"] == "mid":
                    for side, end, sign in (("lower", lo, -1), ("upper", hi, 1)):
                        if len(w[side]) == 3:
                            x, y = w[side][1]
                            at = w["mid"] + x * (end - w["mid"])
                            self.assertAlmostEqual(self.gen.world_factor(scale, lo, hi, at), 0.5 + sign * y / 2, places=6)
        self.assertEqual(self.gen._share(0.2, True), "fifth")
        self.assertEqual((self.gen._share(0.5), self.gen._share(2 / 3), self.gen._share(0.3684)), ("half", "two-thirds", "37%"))

    def test_each_kind_of_map_has_its_palette_s_words(self):
        custom = code("common/customizable_localization/te_journal_map_custom_loc.txt")
        for variant in ("", "_none", "_hq", "_gw", "_mid"):
            body = " ".join(block(custom, f"te_jmap_color_text{variant}").split())
            self.assertIn(f"trigger = {{ te_jmap_color = 1 }} localization_key = te_jmap_color_text{variant}_safe", body)
            self.assertTrue(body.endswith(f"text = {{ localization_key = te_jmap_color_text{variant}_grey }}"), body)
            self.assertEqual(self.values[f"te_jmap_color_in_force{variant}"],
                             f"[GetPlayer.GetCustom('te_jmap_color_text{variant}')]")
            safe, grey = self.values[f"te_jmap_color_text{variant}_safe"], self.values[f"te_jmap_color_text{variant}_grey"]
            self.assertTrue(safe.startswith("$te_jmap_color$: #b $te_jmap_color_safe$#!. "), safe)
            self.assertTrue(grey.startswith("$te_jmap_color$: #b $te_jmap_color_grey$#!. "), grey)
            # the ramps as the colors file has them, and what Greyscale stripes
            if variant == "_mid":
                self.assertIn("Orange below the midpoint, near white at it, purple above", safe)
                self.assertIn("The midpoint sits at the middle gray", grey)
            else:
                self.assertIn("Pale yellow at the low end to brown at the high.", safe)
            self.assertIn("Light gray at the low end to dark gray at the high.", grey)
            self.assertIn("striped", grey)
            self.assertNotIn("striped", safe)
            self.assertEqual("is blue" in safe, variant in ("_hq", "_gw"), "a loss and a net removal are blue")
            self.assertEqual("with none" in safe + grey, variant == "_none")
        # under Greyscale a stripe says one thing, so the regional headquarters' gold stripes stand down
        stripes = dict(branches_of(block(self.room, "map_color_second")))
        self.assertEqual([limit for limit in stripes if "te_jmap_hq_regional" in stripes[limit]],
                         ["te_jmap_selector = 34 te_jmap_in_area = yes has_variable = te_jmap_rhq_n te_jmap_color < 2"])
        self.assertIn("regional headquarters are not marked", self.values["te_jmap_color_text_hq_grey"])
        # and the hover's line names them without the stripes, which aren't always there
        self.assertTrue(self.values["te_jmap_tt_hq_regional"].startswith("Regional headquarters here: "))

    def test_each_kind_of_map_has_its_scale_s_words(self):
        custom = code("common/customizable_localization/te_journal_map_custom_loc.txt")
        for text, keys in (("te_jmap_scale_text", ("linear", "log", "ranked")),
                           ("te_jmap_scale_text_doubling", ("linear", "log_doubling", "ranked")),
                           ("te_jmap_scale_text_mid", ("linear_mid", "log_mid", "ranked_mid"))):
            body = " ".join(block(custom, text).split())
            for number, key in enumerate(keys, 1):
                self.assertIn(f"trigger = {{ te_jmap_scale = {number} }} localization_key = te_jmap_scale_text_{key}",
                              body, text)
        # each says which scale, by the button's own name
        for key, button in (("linear", "linear"), ("log", "log"), ("ranked", "ranked"), ("log_doubling", "log"),
                            ("linear_mid", "linear"), ("log_mid", "log"), ("ranked_mid", "ranked")):
            self.assertTrue(self.values[f"te_jmap_scale_text_{key}"].startswith(
                f"$te_jmap_scale$: #b $te_jmap_scale_{button}$#!"), key)
        # the midpoint maps' logarithm is said in what it does, not by a name
        self.assertIn("each doubling of the distance from it", self.values["te_jmap_scale_text_log_mid"])
        self.assertIn("Close to the midpoint the colors run straight", self.values["te_jmap_scale_text_log_mid"])
        for text in self.values:
            if text.startswith("te_jmap_"):
                self.assertNotIn("symlog", self.values[text].lower(), text)
        # a Ranked map's tooltip says how old it can be, and that the range isn't read
        for key in ("te_jmap_scale_text_ranked", "te_jmap_scale_text_ranked_mid"):
            self.assertIn("a month old at most", self.values[key])
        lead = " ".join(block(custom, "te_jmap_scaled_range_lead").split())
        self.assertIn("trigger = { te_jmap_scale = 3 } localization_key = te_jmap_scaled_lead_ranked", lead)
        self.assertIn("Not read by this scale", self.values["te_jmap_scaled_lead_ranked"])


class AreaTest(unittest.TestCase):
    """The continents: every state region in exactly one."""

    CONTINENTS = ("europe", "asia", "africa", "north_america", "south_america", "oceania")

    def setUp(self):
        self.triggers = code(TRIGGERS)

    def regions(self, continent):
        return re.findall(r"region = sr:(\w+)", block(self.triggers, f"te_jmap_in_continent_{continent}"))

    @staticmethod
    def strategic_regions():
        """{strategic region: [state regions]}: vanilla's snapshot with the mod's REPLACE: blocks over it."""
        import json
        with open(os.path.join(REPO, "vanilla_parsed", "common", "strategic_regions.json"), encoding="utf-8") as f:
            out = {name: body[1]["states"][1] for name, body in json.load(f).items()}
        folder = os.path.join(REPO, "common", "strategic_regions")
        for name in sorted(os.listdir(folder)):
            text = code(os.path.join("common", "strategic_regions", name))
            for m in re.finditer(r"^(?:REPLACE:|INJECT:)?(region_\w+)\s*=\s*\{", text, re.M):
                states = re.search(r"\bstates\s*=\s*\{([^{}]*)\}", enclosing(text, m.end()))
                out[m.group(1)] = states.group(1).split()
        return out

    @staticmethod
    def land_state_regions():
        """Every state region on land: the mod's map_data/state_regions, the seas' file left out."""
        folder = os.path.join(REPO, "map_data", "state_regions")
        out = set()
        for name in sorted(os.listdir(folder)):
            if name.endswith(".txt") and "seas" not in name:
                out |= set(re.findall(r"^(STATE_\w+)\s*=\s*\{", code(os.path.join("map_data", "state_regions", name)),
                                      re.M))
        return out

    def test_every_state_region_is_in_exactly_one_continent(self):
        home = {}
        for sr, states in self.strategic_regions().items():
            for state in states:
                self.assertNotIn(state, home, f"{state} in two strategic regions")
                home[state] = sr
        of = {}
        for continent in self.CONTINENTS:
            for sr in self.regions(continent):
                self.assertNotIn(sr, of, f"{sr} in two continents")
                of[sr] = continent
        land = self.land_state_regions()
        self.assertGreater(len(land), 600)
        for state in sorted(land):
            self.assertIn(state, home, f"{state} is in no strategic region")
            self.assertIn(home[state], of, f"{state} ({home[state]}) is in no continent")
        # and nothing but land: no sea region, no region that doesn't exist
        for sr, continent in of.items():
            self.assertIn(sr, self.strategic_regions(), f"{continent}: no such strategic region")
            self.assertTrue(set(self.strategic_regions()[sr]) <= land, f"{sr} holds a sea")
        counts = {c: sum(len(self.strategic_regions()[sr]) for sr in self.regions(c)) for c in self.CONTINENTS}
        self.assertEqual(sum(counts.values()), len(land))
        self.assertTrue(all(counts.values()), counts)

    def test_the_border_cases_fall_where_the_doc_says(self):
        home = {state: sr for sr, states in self.strategic_regions().items() for state in states}
        of = {sr: c for c in self.CONTINENTS for sr in self.regions(c)}
        where = {state: of[home[state]] for state in (
            "STATE_PALESTINE", "STATE_ARMENIA", "STATE_TOBOLSK", "STATE_WESTERN_NEW_GUINEA", "STATE_MOSCOW",
            "STATE_ICELAND", "STATE_GREENLAND", "STATE_SINAI", "STATE_MEXICO", "STATE_HAITI", "STATE_PANAMA",
            "STATE_HAWAIIAN_ISLANDS", "STATE_ALASKA")}
        self.assertEqual(where, {
            "STATE_PALESTINE": "asia", "STATE_ARMENIA": "asia", "STATE_TOBOLSK": "asia",
            "STATE_WESTERN_NEW_GUINEA": "asia", "STATE_MOSCOW": "europe", "STATE_ICELAND": "europe",
            "STATE_GREENLAND": "europe", "STATE_SINAI": "africa", "STATE_MEXICO": "north_america",
            "STATE_HAITI": "north_america", "STATE_PANAMA": "north_america", "STATE_HAWAIIAN_ISLANDS": "oceania",
            "STATE_ALASKA": "north_america"})

    def test_the_continents_numbers_agree_everywhere(self):
        # te_jmap_continent's 1-6 mean one continent in the marking trigger, the default (the capital's), the buttons
        # and the words
        pick = " ".join(block(self.triggers, "te_jmap_state_in_continent").split())
        default = " ".join(block(code(EFFECTS), "te_jmap_default_continent").split())
        custom = code("common/customizable_localization/te_journal_map_custom_loc.txt")
        for number, continent in enumerate(self.CONTINENTS, 1):
            with self.subTest(continent=continent):
                self.assertIn(f"limit = {{ te_jmap_continent = {number} }} te_jmap_in_continent_{continent} = yes", pick)
                self.assertEqual(OptionsTest.OPTIONS[f"te_jmap_continent_{continent}_sgui"][2], number)
                if number == 1:
                    self.assertTrue(default.startswith("set_global_variable = { name = te_jmap_opt_cont value = 1 }"),
                                    "Europe where the capital is in none of the others")
                else:
                    self.assertIn(f"limit = {{ capital ?= {{ te_jmap_in_continent_{continent} = yes }} }} "
                                  f"set_global_variable = {{ name = te_jmap_opt_cont value = {number} }}", default)
                for text in ("te_jmap_area_name", "te_jmap_area_text"):
                    self.assertIn(f"trigger = {{ te_jmap_area = 1 te_jmap_continent = {number} }} localization_key = "
                                  f"te_jmap_continent_{continent}", " ".join(block(custom, text).split()))
        self.assertTrue(pick.endswith("trigger_else = { always = no }"))

    def test_each_continent_s_tooltip_lists_its_regions(self):
        # the tooltip says exactly what the trigger tests, each region by vanilla's own name
        values = loc_values()
        for continent in self.CONTINENTS:
            listed = re.findall(r"\$(region_\w+)\$", values[f"te_jmap_continent_{continent}_tt"].split("\\n", 1)[1])
            self.assertEqual(listed, self.regions(continent), continent)


class WindowButtonTest(unittest.TestCase):
    def test_the_map_room_button_sits_by_the_width_toggle(self):
        text = code(SYSTEMS_WINDOW)
        toggle = enclosing(text, re.search(r"type te_systems_window_toggle = hbox \{", text).end())
        self.assertIn("te_jmap_window_button = {}", toggle)

    def test_it_opens_the_page_then_closes_the_window(self):
        # the close comes last: a button whose own window hides mid-click may lose the lines after it
        body = block(code(WIDGETS), "te_jmap_window_button")
        self.assertIn("GetPlayerJournalEntry('je_te_map_room')", body)
        clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', body)
        self.assertEqual(clicks[0], "[GetVariableSystem.Clear('te_je_see_through')]")
        self.assertIn("te_jmap_note_viewer_sgui", clicks[1])
        self.assertEqual(clicks[2], "[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]")
        self.assertEqual(clicks[3], "[GetVariableSystem.Clear('com_open_window')]")


def loc_values():
    out = {}
    for name in os.listdir(os.path.join(REPO, LOC_DIR)):
        if name.endswith(".yml"):
            for line in read(os.path.join(LOC_DIR, name)).splitlines():
                m = re.match(r'\s+([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    out[m.group(1)] = m.group(2)
    return out


class LocTest(unittest.TestCase):
    def test_tooltips_buttons_and_names_have_loc(self):
        keys = loc_keys()
        wanted = set()
        for rel in MAP_ENTRIES:
            wanted |= set(re.findall(r"custom_tooltip_no_bullet\s*=\s*(\w+)", code(rel)))
        for rel in (WIDGETS, PICKS_GUI, ROOM_WIDGET, JE_PANEL):
            wanted |= set(re.findall(r'(?:text|tooltip)\s*=\s*"(te_j(?:map|e)_\w+)"', code(rel)))
        self.assertIn("te_je_see_through_tt", wanted)
        wanted |= {"je_te_map_room", "je_te_map_room_reason"}
        self.assertEqual(wanted - keys, set(), "loc keys missing")

    def test_retired_test_pieces_left_no_loc(self):
        keys = loc_keys()
        gone = {k for k in keys if k.startswith(("te_jmap_strip_", "te_jmap_tt_probe_", "je_te_map_potential_probe"))}
        gone |= keys & {"te_jmap_pick_scope_probe", "te_jmap_pick_scope_probe_desc", "te_jmap_tt_potential_probe",
                        "mm_te_journal_entry_map"}
        self.assertEqual(gone, set())

    def test_literacy_is_back_on_its_old_selector(self):
        # retired in the fifth pass as the twin of vanilla's lens, back in the first tier (#1976) for the Map Room's
        # options: on 2, so a save that still held the old pick shows it
        self.assertIn("te_jmap_set_selector = { SEL = 2 }", " ".join(block(sguis(), "te_jmap_pick_literacy_sgui").split()))
        self.assertIn("te_jmap_literacy_low", code(COLORS))


class GuiTest(unittest.TestCase):
    def test_buttons_are_mounted(self):
        self.assertIn("te_jmap_demog_map_button = {}", code(DEMOG_LAYOUT))
        self.assertIn("te_jmap_banking_map_button = {}", code(BANKING_LAYOUT))
        self.assertIn("te_jmap_window_button = {}", code(SYSTEMS_WINDOW))

    def test_banking_button_has_no_activity_gate(self):
        # the entry is active from the engine's first check (possible = yes), and an inactive page would open and
        # paint too (check 7, 2026-11-05), so the button needs no IsActive gate
        self.assertNotIn("IsActive", block(code(WIDGETS), "te_jmap_banking_map_button"))
        self.assertRegex(block(code(BANKING), "je_banking_cycle"), r"\bpossible\s*=\s*\{\s*always\s*=\s*yes\s*\}")

    def test_map_buttons_open_pages_whole(self):
        names = ["te_jmap_demog_map_button", "te_jmap_banking_map_button", "te_jmap_window_button"]
        names += [f"te_jmap_{button}_map_button" for *_head, button, _tab, _gate in SYSTEM_MAPS]
        for name in names:
            clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', block(code(WIDGETS), name))
            self.assertEqual(clicks[0], "[GetVariableSystem.Clear('te_je_see_through')]", name)

    def test_every_entry_the_gui_opens_exists(self):
        entries = set(re.findall(r"^([a-z_0-9]+)\s*=\s*\{", code(HOST), re.M)) | {"je_banking_cycle"}
        for name in re.findall(r"GetPlayerJournalEntry\('(\w+)'\)", code(WIDGETS)):
            self.assertIn(name, entries)

    def test_every_open_names_its_entry_by_datacontext(self):
        # GetPlayerJournalEntry fails at load inside a callback, bare (first launch) and ended with .AccessSelf
        # ("requires non const promote", third session): the button carries the entry as its datacontext
        text = code(WIDGETS)
        self.assertNotRegex(text, r'onclick\s*=\s*"[^"]*GetPlayerJournalEntry')
        for m in re.finditer(r"OpenJournalEntryPanel(?:DontToggle)?\(([^)]*)\)", text):
            self.assertEqual(m.group(1), "JournalEntry.AccessSelf")
            start, end = enclosing_span(text, m.start())
            if re.search(r"\bstate\s*=\s*\{\s*$", text[:start]):
                # an animation state's callback: the entry sits on the widget the state belongs to
                start, end = enclosing_span(text, start - 1)
            self.assertIn('datacontext = "[GetPlayerJournalEntry(', text[start:end],
                          "an open with no entry datacontext on its own widget")

    def test_demographics_button_is_one_click(self):
        button = block(code(WIDGETS), "te_jmap_demog_map_button")
        clicks = re.findall(r'onclick\s*=\s*"([^"]*)"', button)
        self.assertEqual(len(clicks), 3, "unfade, pick, then open")
        self.assertIn("te_jmap_pick_life_expectancy_sgui", clicks[1])
        self.assertIn("OpenJournalEntryPanel", clicks[2])
        self.assertIn("GetPlayerJournalEntry('je_te_map_room')", button)


class SeeThroughTest(unittest.TestCase):
    """The eye on every journal page fades it so its map shows (owner's ask, 2026-11-05)."""

    def setUp(self):
        self.panel = block(code(JE_PANEL), "journal_entry_panel")

    def test_the_page_fades_on_the_flag(self):
        alpha = re.findall(r'^\t\talpha\s*=\s*"([^"]*)"', self.panel, re.M)
        self.assertEqual(len(alpha), 1, "one alpha on the panel's root")
        self.assertIn("GetVariableSystem.Exists('te_je_see_through')", alpha[0])

    def test_the_eye_toggles_the_flag(self):
        props = override(self.panel, "top_left_button_properties")
        self.assertIsNotNone(props)
        self.assertIn("[GetVariableSystem.Toggle('te_je_see_through')]", props)
        self.assertIn("JournalEntryPanel.HasJournalEntry", override(self.panel, "top_left_button_visibility"))

    def test_closing_clears_it_but_a_reopen_keeps_it(self):
        # a Map Room pick reopens the page (te_jmap_repaint), which fires _show: clearing there would unfade the page
        # at every pick
        self.assertNotIn("te_je_see_through", override(self.panel, "animation_state_block"))
        close = re.findall(r'onclick\s*=\s*"([^"]*)"', override(self.panel, "header_close_button"))
        self.assertEqual(close, ["[InformationPanelBar.ClosePanel]", "[GetVariableSystem.Clear('te_je_see_through')]"])
        back = override(self.panel, "header_back_button")
        self.assertEqual(re.findall(r'onclick\s*=\s*"([^"]*)"', back),
                         ["[InformationPanelBar.OpenPreviousPanel]", "[GetVariableSystem.Clear('te_je_see_through')]"])
        self.assertRegex(back, r'input_action\s*=\s*"back"', "vanilla's back shortcut kept")


class MapModeTest(unittest.TestCase):
    def test_listed_copy_is_gone(self):
        # check 5 (2026-11-05): with no page open it painted nothing, and with one open it showed that page's map
        self.assertFalse(os.path.exists(os.path.join(REPO, MAP_MODE)) or tracked(MAP_MODE), MAP_MODE)


class DocsTest(unittest.TestCase):
    def test_playtest_names_every_test_piece(self):
        doc = read(PLAYTEST)
        for piece in ("TE_JMAP", "te_jmap_repaint", "te_je_see_through"):
            self.assertIn(piece, doc)


class NuclearReachMapTest(_RoomBranches, unittest.TestCase):
    """Nuclear Reach (selector 90, 2026-11-26, the owner's ask: "what states are reachable by bomber, by sub, and by
    ICBM"): the viewer's reach by the cheapest leg that reaches a state, the bombers' from the deterrent's own builder
    into a list of the map's, and nothing private read."""

    SEL = 90
    SECRET = ("nuclear_weapon_stockpile", "nd_is_armed", "nd_display_public_estimate", "nd_believed_stockpile",
              "nd_stockpile")

    def setUp(self):
        super().setUp()
        self.effects = code(EFFECTS)
        self.triggers = code(TRIGGERS)

    def test_the_paint_runs_from_your_own_states_to_the_icbms(self):
        colors = [(limit, body) for limit, body in self.of(self.colors, self.SEL)]
        self.assertEqual([(" ".join(limit.split()[3:]), body) for limit, body in colors], [
            ("te_jmap_owner_is_viewer = yes", 'value = "te_jmap_reach_you"'),
            ("te_jmap_reach_bombers = yes", 'value = "te_jmap_reach_bombers"'),
            ("te_jmap_reach_subs = yes", 'value = "te_jmap_reach_subs"'),
            ("te_jmap_reach_icbms = yes", 'value = "te_jmap_reach_icbms"'),
            ("", 'value = "te_jmap_none"'),
        ])
        hover = [(" ".join(limit.split()[3:]), body) for limit, body in self.of(self.hover, self.SEL)]
        self.assertEqual(hover[:5], [
            ("te_jmap_owner_is_viewer = yes", "custom_tooltip_no_bullet = te_jmap_tt_reach_you"),
            ("te_jmap_reach_bombers = yes", "custom_tooltip_no_bullet = te_jmap_tt_reach_bombers"),
            ("te_jmap_reach_subs = yes", "custom_tooltip_no_bullet = te_jmap_tt_reach_subs"),
            ("te_jmap_reach_icbms = yes", "custom_tooltip_no_bullet = te_jmap_tt_reach_icbms"),
            ("", "custom_tooltip_no_bullet = te_jmap_tt_reach_none"),
        ])
        # the second line: the submarines over the bombers (the stripes), or what would reach a state out of reach
        self.assertEqual(hover[5:], [
            ("te_jmap_in_area = yes te_jmap_reach_bombers = yes te_jmap_reach_subs = yes",
             "custom_tooltip_no_bullet = te_jmap_tt_reach_also_subs"),
            ("te_jmap_in_area = yes te_jmap_reach_out = yes te_jmap_reach_subs_would = yes",
             "custom_tooltip_no_bullet = te_jmap_tt_reach_would_subs"),
            ("te_jmap_in_area = yes te_jmap_reach_out = yes",
             "custom_tooltip_no_bullet = te_jmap_tt_reach_would_icbms"),
        ])
        out = " ".join(block(self.triggers, "te_jmap_reach_out").split())
        for leg in ("te_jmap_owner_is_viewer", "te_jmap_reach_bombers", "te_jmap_reach_subs", "te_jmap_reach_icbms"):
            self.assertIn(f"NOT = {{ {leg} = yes }}", out)

    def test_the_bombers_reach_is_the_list_or_adjacency_now(self):
        # the list a month old at most, the viewer's own strategic adjacency live, as nd_state_in_reach_of reads it
        body = " ".join(block(self.triggers, "te_jmap_reach_bombers").split())
        self.assertIn("NOT = { this = scope:te_jmap_reach_owner }", body)
        self.assertIn("has_strategic_adjacency = scope:te_jmap_reach_owner", body)
        self.assertIn("is_target_in_variable_list = { name = te_jmap_rch target = scope:te_jmap_reach_owner }", body)
        self.assertIn("is_coastal = yes", block(self.triggers, "te_jmap_reach_subs"))
        self.assertIn("has_variable = te_jmap_rch_subs", block(self.triggers, "te_jmap_reach_subs"))
        self.assertIn("has_variable = te_jmap_rch_icbms", block(self.triggers, "te_jmap_reach_icbms"))

    def test_the_paint_reads_stored_legs_and_nothing_private(self):
        # a paint runs per state as the game runs: the legs are flags the store set, not the delivery triggers (the
        # submarines' walks the viewer's states for a coast); and nuclear.md's privacy rule, as for Nuclear Weapons
        names = [n for n in re.findall(r"^(te_jmap_reach_\w+)\s*=\s*\{", self.triggers, re.M)]
        self.assertEqual(sorted(names), ["te_jmap_reach_bombers", "te_jmap_reach_icbms", "te_jmap_reach_out",
                                         "te_jmap_reach_subs", "te_jmap_reach_subs_would"])
        for name in names:
            body = block(self.triggers, name)
            for word in self.SECRET + ("nd_fields_icbms", "nd_fields_missile_submarines", "any_scope_state"):
                self.assertNotRegex(body, r"\b" + word + r"\b", f"{name} reads {word}")
        for key, text in loc_values().items():
            if key.startswith("te_jmap_tt_reach_") or key.startswith("te_jmap_pick_nuclear_reach"):
                self.assertNotIn("ScriptValue(", text, key)
                self.assertNotIn("Var(", text, key)

    def test_the_store_is_the_deterrent_s_builder_on_a_list_of_the_map_s(self):
        store = " ".join(block(self.effects, "te_jmap_store_reach").split())
        self.assertTrue(store.startswith("nd_reach_reset = { LIST = te_jmap_rch } nd_reach_build = { LIST = te_jmap_rch }"),
                        store)
        # the legs from the delivery triggers, never the technologies, and the viewer's own coast
        for flag, test in (("te_jmap_rch_subs", "nd_fields_missile_submarines = yes"),
                           ("te_jmap_rch_icbms", "nd_fields_icbms = yes"),
                           ("te_jmap_rch_coast", "any_scope_state = { is_coastal = yes }")):
            self.assertIn(f"if = {{ limit = {{ {test} }} set_variable = {flag} }} else_if = {{ limit = {{ "
                          f"has_variable = {flag} }} remove_variable = {flag} }}", store)
        self.assertNotIn("has_technology_researched", store)
        self.assertNotIn("nd_is_armed", store, "the bombers' reach shows before the first warhead too")

    def test_the_reach_follows_the_viewer_while_it_is_the_pick(self):
        # built on whoever becomes the viewer: every pick and option, the window's button and a player's month all
        # note the viewer, so the store sits there, after the viewer is set, and only while the map is up
        note = " ".join(block(self.effects, "te_jmap_note_viewer").split())
        self.assertLess(note.index("set_global_variable = { name = te_jmap_viewer value = root }"),
                        note.index("te_jmap_store_reach"))
        self.assertIn("if = { limit = { global_var:te_jmap_sel ?= 90 } root = { te_jmap_store_reach = yes } }", note)
        self.assertEqual(self.effects.count("te_jmap_store_reach = yes"), 1, "one call site")
        # a pick notes the viewer after it sets the selector, so the first pick of the map builds the reach
        pick = " ".join(block(self.effects, "te_jmap_set_selector").split())
        self.assertLess(pick.index("set_global_variable = { name = te_jmap_sel"), pick.index("te_jmap_note_viewer"))

    def test_the_pick_waits_for_the_rule_and_sits_beside_nuclear_weapons(self):
        body = block(sguis(), "te_jmap_pick_nuclear_reach_sgui")
        self.assertIn("has_game_rule = nuclear_weapons_enabled", block(body, "is_shown"))
        row = code(PICKS_GUI)
        self.assertLess(row.index('text = "te_jmap_pick_nuclear"'), row.index('text = "te_jmap_pick_nuclear_reach"'))

    def test_the_three_legs_stay_apart(self):
        # Okabe and Ito's three, chosen to stay apart for color-blind readers, apart from the "your" blue too
        text = code(COLORS)
        hsv = {n: tuple(int(x) for x in re.search(r"\b" + n + r"\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)",
                                                  text).groups())
               for n in ("te_jmap_reach_you", "te_jmap_reach_bombers", "te_jmap_reach_subs", "te_jmap_reach_icbms")}
        self.assertEqual(hsv["te_jmap_reach_bombers"], (41, 100, 90))
        self.assertEqual(hsv["te_jmap_reach_subs"], (164, 100, 62))
        self.assertEqual(hsv["te_jmap_reach_icbms"], (327, 41, 80))
        self.assertEqual(hsv["te_jmap_reach_you"], tuple(int(x) for x in re.search(
            r"\bte_jmap_nuke_you\s*=\s*hsv360\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", text).groups()))



class GridFlowsMapTest(_RoomBranches, unittest.TestCase):
    """Grid Flows (selector 91, 2026-11-27, the owner's ask for an import/export map beside vanilla's price map): each
    station's state by what its station does this month, read as the Power Grids tab's Stations table reads it."""

    SEL = 91
    MODES = ((1, "te_jmap_grid_send", "te_jmap_tt_grid_send"), (2, "te_jmap_grid_receive", "te_jmap_tt_grid_receive"),
             (3, "te_jmap_grid_idle", "te_jmap_tt_grid_idle"), (4, "te_jmap_grid_offline", "te_jmap_tt_grid_flow_off"))

    def test_the_paint_and_the_hover_follow_the_mode(self):
        expected = [(f"grid_mode = {{ MODE = {n} }}", color) for n, color, _ in self.MODES]
        colors = [(" ".join(limit.split()[3:]).replace("te_jmap_", ""), body) for limit, body in
                  self.of(self.colors, self.SEL)]
        self.assertEqual(colors, [(m, f'value = "{c}"') for m, c in expected] + [("", 'value = "te_jmap_none"')])
        hover = [(" ".join(limit.split()[3:]).replace("te_jmap_", ""), body) for limit, body in
                 self.of(self.hover, self.SEL)]
        # a sender's and a receiver's flow abbreviated from 1,000, a plain figure under it: a branch each, since a key
        # a SelectLocalization names loses THIS (test_loc_add_localization_if_scope.py)
        big = "te_grid_electricity_moved_disp > 999"
        want = []
        for n, _, tt in self.MODES:
            if n in (1, 2):
                want.append((f"grid_mode = {{ MODE = {n} }} {big}", f"custom_tooltip_no_bullet = {tt}_k"))
            want.append((f"grid_mode = {{ MODE = {n} }}", f"custom_tooltip_no_bullet = {tt}"))
        self.assertEqual(hover, want + [("", "custom_tooltip_no_bullet = te_jmap_tt_grid_none")])
        loc = loc_values()
        for tt in ("te_jmap_tt_grid_send", "te_jmap_tt_grid_receive"):
            self.assertIn("ScriptValue('te_grid_electricity_moved_disp')|0]", loc[tt])
            self.assertEqual(loc[f"{tt}_k"], loc[tt].replace("|0]", "|K]"))

    def test_the_mode_is_the_tab_s_on_a_station(self):
        body = " ".join(block(code(TRIGGERS), "te_jmap_grid_mode").split())
        # the station first: te_grid_mode_disp reads 4, offline, where there is none
        self.assertEqual(body, "has_building = building_grid_transfer_station te_grid_mode_disp = $MODE$")
        values = code("common/script_values/power_grid_values.txt")
        self.assertEqual(sorted({int(v) for v in re.findall(r"\bvalue = (\d+)", block(values, "te_grid_mode_disp"))}),
                         [n for n, _, _ in self.MODES])

    def test_the_hovers_read_the_state_through_this(self):
        # a map hover has no State datacontext: each reads THIS.GetState, and the idle reason through its own chain
        loc = loc_values()
        keys = [tt for _, _, tt in self.MODES] + ["te_jmap_tt_grid_send_k", "te_jmap_tt_grid_receive_k",
                                                  "te_jmap_tt_grid_staff", "te_jmap_tt_grid_why"]
        for key in keys:
            self.assertNotRegex(loc[key], r"(?<![.\w])State\.", key)
        why = loc["te_jmap_tt_grid_why"]
        for n in range(1, 11):
            self.assertIn(f"'(CFixedPoint){n}'), 'te_grid_why_short_{n}'", why)
        # a hub is named only where the station moves power, so it is on a grid
        for key in ("te_jmap_tt_grid_idle", "te_jmap_tt_grid_flow_off"):
            self.assertNotIn("te_grid_hub", loc[key], key)

    def test_the_pick_sits_beside_power_grids_and_the_colors_stay_apart(self):
        row = code(PICKS_GUI)
        self.assertLess(row.index('text = "te_jmap_pick_power_grids"'), row.index('text = "te_jmap_pick_grid_flows"'))
        self.assertEqual(block(block(sguis(), "te_jmap_pick_grid_flows_sgui"), "is_shown").split(),
                         ["is_player", "=", "yes"])
        text = code(COLORS)
        hue = {n: int(re.search(r"\b" + n + r"\s*=\s*hsv360\s*\{\s*(\d+)", text).group(1))
               for n in ("te_jmap_grid_send", "te_jmap_grid_receive")}
        # blue against orange: far apart on the wheel, a pair colorblind viewers tell apart
        self.assertGreaterEqual(abs(hue["te_jmap_grid_send"] - hue["te_jmap_grid_receive"]), 150)


if __name__ == "__main__":
    unittest.main()
