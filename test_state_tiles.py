"""The state view's Overview: the mod's tiles in one anatomy, in two columns after vanilla's (gui/state-tiles).

- One anatomy (te_state_tile): vanilla's 260-wide tile with its icon in a 60 inset box at the top left and a 170
  text column, the caption then the rows. Every reading is a te_state_tile_row (label 92 + 4 + value 74); a name
  as the value takes te_state_tile_word_row (52 + 4 + 114, wrapping), a culture's name as the label
  te_state_tile_culture_row (115 + 4 + 51); a line across the column is a te_state_tile_line. No instance sets
  widths of its own, so every tile's labels start at one x and its values end at one x.
- Two columns (te_state_tiles), each a vertical flow fixed at 260, mounted once, after vanilla's grid and decrees;
  the full-width cards (Grand Monument, construction site, trophies, then tourism) after them. Each tile is
  mounted once, in the column the design gives it, the always-shown tile first.
- A width budget read off the game's own OpenSans at 14 (fontsize_medium): every English label fits its cell and
  every value its cell, each with 5% to spare. The glyph widths below were measured from the game's font files and
  matched the panel's screenshot (2026-11-24, 1.5 px a unit) to 2 units, so 5% is room, not guesswork.
- GDP per Capita, the mod's tile at the head of vanilla's grid, keeps vanilla's anatomy and reads as a caption
  and two rows.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATES = ROOT / "gui" / "states_panel.gui"
WIDGETS = ROOT / "gui" / "te_state_panel_widgets.gui"
LOC_DIR = ROOT / "localization" / "english"
VANILLA = ROOT / "vanilla_parsed"

# Advance widths at 14 of clausewitz/fonts/Open_Sans/OpenSans-{Regular,Bold}.ttf (PIL ImageFont.getlength),
# the tooltip face that fontsize_medium uses. A label is regular, a value #v (white;bold;shadow) bold.
REGULAR_14 = {
    ' ': 3.64, '!': 3.73, '"': 5.61, '#': 9.05, '$': 8.0, '%': 11.53, '&': 10.22, "'": 3.09, '(': 4.14, ')': 4.14,
    '*': 7.72, '+': 8.0, ',': 3.44, '-': 4.5, '.': 3.72, '/': 5.14, '0': 8.0, '1': 8.0, '2': 8.0, '3': 8.0, '4': 8.0,
    '5': 8.0, '6': 8.0, '7': 8.0, '8': 8.0, '9': 8.0, ':': 3.72, ';': 3.72, '<': 8.0, '=': 8.0, '>': 8.0, '?': 6.02,
    '@': 12.58, 'A': 8.86, 'B': 9.08, 'C': 8.83, 'D': 10.2, 'E': 7.78, 'F': 7.22, 'G': 10.19, 'H': 10.33, 'I': 3.91,
    'J': 3.91, 'K': 8.5, 'L': 7.28, 'M': 12.66, 'N': 10.72, 'O': 10.91, 'P': 8.42, 'Q': 10.91, 'R': 8.73, 'S': 7.5,
    'T': 7.61, 'U': 10.19, 'V': 8.27, 'W': 12.83, 'X': 8.33, 'Y': 7.89, 'Z': 7.98, '[': 4.48, '\\': 5.14, ']': 4.48,
    '^': 7.56, '_': 5.81, '`': 8.27, 'a': 7.78, 'b': 8.58, 'c': 6.67, 'd': 8.58, 'e': 7.86, 'f': 4.77, 'g': 7.58,
    'h': 8.59, 'i': 3.55, 'j': 3.55, 'k': 7.34, 'l': 3.55, 'm': 13.02, 'n': 8.59, 'o': 8.45, 'p': 8.58, 'q': 8.58,
    'r': 5.72, 's': 6.67, 't': 4.94, 'u': 8.59, 'v': 7.02, 'w': 10.89, 'x': 7.33, 'y': 7.06, 'z': 6.55, '{': 5.31,
    '|': 7.72, '}': 5.31, '~': 8.0, '°': 6.0, '×': 8.0, '→': 8.41, '−': 8.0, '–': 7.0, '—': 14.0, '’': 2.38,
    'é': 7.86, 'è': 7.86, 'ê': 7.86, 'á': 7.78, 'à': 7.78, 'â': 7.78, 'í': 3.55, 'ó': 8.45, 'ô': 8.45, 'ú': 8.59,
    'ñ': 8.59, 'ç': 6.67, 'ä': 7.78, 'ö': 8.45, 'ü': 8.59, 'ß': 8.7, 'Ä': 8.86, 'Ö': 10.91, 'Ü': 10.19, 'É': 7.78,
    '£': 8.0,
}
BOLD_14 = {
    ' ': 3.64, '!': 4.0, '"': 6.61, '#': 9.05, '$': 7.98, '%': 12.61, '&': 10.5, "'": 3.72, '(': 4.75, ')': 4.75,
    '*': 7.62, '+': 7.98, ',': 4.06, '-': 4.5, '.': 4.0, '/': 5.78, '0': 7.98, '1': 7.98, '2': 7.98, '3': 7.98,
    '4': 7.98, '5': 7.98, '6': 7.98, '7': 7.98, '8': 7.98, '9': 7.98, ':': 4.0, ';': 4.06, '<': 7.98, '=': 7.98,
    '>': 7.98, '?': 6.67, '@': 12.56, 'A': 9.66, 'B': 9.41, 'C': 8.92, 'D': 10.36, 'E': 7.84, 'F': 7.69, 'G': 10.14,
    'H': 10.72, 'I': 4.64, 'J': 4.64, 'K': 9.3, 'L': 7.91, 'M': 13.2, 'N': 11.38, 'O': 11.14, 'P': 8.8, 'Q': 11.14,
    'R': 9.25, 'S': 7.72, 'T': 8.11, 'U': 10.58, 'V': 9.09, 'W': 13.53, 'X': 9.34, 'Y': 8.73, 'Z': 8.11, '[': 4.64,
    '\\': 5.78, ']': 4.64, '^': 7.45, '_': 5.75, '`': 8.5, 'a': 8.45, 'b': 8.86, 'c': 7.2, 'd': 8.86, 'e': 8.27,
    'f': 5.42, 'g': 7.91, 'h': 9.2, 'i': 4.27, 'j': 4.27, 'k': 8.69, 'l': 4.27, 'm': 13.75, 'n': 9.2, 'o': 8.67,
    'p': 8.86, 'q': 8.86, 'r': 6.36, 's': 6.95, 't': 6.08, 'u': 9.2, 'v': 7.97, 'w': 11.98, 'x': 8.09, 'y': 7.97,
    'z': 6.83, '{': 5.52, '|': 7.72, '}': 5.52, '~': 7.98, '°': 6.0, '×': 7.98, '→': 8.41, '−': 7.98, '–': 7.0,
    '—': 14.0, '’': 3.03, 'é': 8.27, 'è': 8.27, 'ê': 8.27, 'á': 8.45, 'à': 8.45, 'â': 8.45, 'í': 4.27, 'ó': 8.67,
    'ô': 8.67, 'ú': 9.2, 'ñ': 9.2, 'ç': 7.2, 'ä': 8.45, 'ö': 8.67, 'ü': 9.2, 'ß': 9.95, 'Ä': 9.66, 'Ö': 11.14,
    'Ü': 10.58, 'É': 7.84, '£': 7.98,
}
MARGIN = 1.05
MONEY_ICON = 18  # an @money! text icon at 14, with its gap
WIDEST = 14.0    # a glyph the tables lack counts as an em dash, the widest they hold

# The widest a figure prints, by its format: four digits for a count (Illinois's arable land is 1525), a share up
# to a thousand percent (crowding's ratio), a quantity in thousands (a grid's weekly flow), a sum per head in
# thousands (GDP per capita, £1.16K in Illinois in 2032). A score out of 100 prints three digits.
FIGURE = {"0": "1234", "1": "123.4", "2": "12.34", "%0": "1000%", "K": "999.9K", "Kv": "99.99M", "2*": "12.34K"}
CAPPED = {"te_dg_wc": "100", "te_demog_wc_target": "100", "te_homeland_project_progress_pct": "100.0",
          "un_state_mission_progress": "100"}

# The design (PR body, gui/state-tiles): each column opens with its always-shown tile, then the conditional ones.
LEFT = ["TE_STATE_ARABLE_TT", "TE_STATE_WEALTH_TT", "TE_STATE_SEABED_TT", "TE_STATE_SEABED_BASIN_TT",
        "TE_STATE_SOLAR_TT", "TE_STATE_ANTIMATTER_TT", "TE_STATE_UN_MISSION_TT"]
RIGHT = ["TE_STATE_CLIMATE_TT", "TE_STATE_CROWDING_TT", "TE_STATE_GRID_TT", "TE_STATE_HOMELAND_TT"]

ROW_TYPES = {  # type: (label, value), each cell's width
    "te_state_tile_row": (92, 74),
    "te_state_tile_word_row": (52, 114),
    "te_state_tile_culture_row": (115, 51),
    "te_state_vanilla_tile_row": (84, 72),
}
TILE_BODIES = ("te_state_climate_tile", "te_state_wealth_tile", "te_state_homeland_tracks", "te_state_homeland_project")


def strip_comments(text):
    return re.sub(r"(?m)^\s*#.*$|(?<=\s)#(?![!a-zA-Z]).*$", "", text)


def block_at(text, open_brace):
    """The text from `open_brace` (an index of "{") to its closing brace, inclusive."""
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace:i + 1]
    raise AssertionError("unbalanced braces")


def gui_type(text, name):
    m = re.search(rf"(?m)^\ttype {re.escape(name)} = \w+ \{{", text)
    assert m, f"no type {name}"
    return block_at(text, m.end() - 1)


def instances(text, name):
    return [block_at(text, m.end() - 1) for m in re.finditer(rf"\b{re.escape(name)} = \{{", text)]


def own(block):
    """A block's own lines: its text with every nested block removed."""
    out, depth = [], 0
    for ch in block[1:-1]:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def loc():
    keys = dict(json.loads((VANILLA / "localization_english.json").read_text(encoding="utf-8")))
    for path in sorted(LOC_DIR.glob("*.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


LOC = loc()
WIDGETS_TEXT = strip_comments(WIDGETS.read_text(encoding="utf-8-sig"))
STATES_TEXT = strip_comments(STATES.read_text(encoding="utf-8-sig"))
TILES = gui_type(WIDGETS_TEXT, "te_state_tiles")


def shown(text, depth=0):
    """Every English text `text` can print, formatting stripped: a $key$ spliced, a concept by its name, a choice
    of keys (AddLocalizationIf, SelectLocalization) as each of its keys, a figure as the widest of its format."""
    assert depth < 8, text
    out = [text]
    # $key$ splices (a |q or other flag after the key is the key's own text)
    while any("$" in t for t in out):
        nxt = []
        for t in out:
            m = re.search(r"\$([\w.\-]+)(?:\|\w+)?\$", t)
            if not m:
                nxt.append(t)
                continue
            for sub in shown(LOC.get(m.group(1), m.group(1)), depth + 1):
                nxt.append(t[:m.start()] + sub + t[m.end():])
        out = nxt
    result = []
    for t in out:
        # A run of AddLocalizationIf brackets prints one of its keys (each gate excludes the others).
        t = re.sub(r"(?:\[AddLocalizationIf\([^\[\]]*\)\])+",
                   lambda m: "[OneOf(" + " ".join(f"'{k}'" for k in re.findall(r"'([\w.\-]+)'", m.group(0))
                                                  if k in LOC) + ")]", t)
        variants = [t]
        while any("[" in v for v in variants):
            nxt = []
            for v in variants:
                m = re.search(r"\[([^\[\]]*)\]", v)
                if not m:
                    nxt.append(v)
                    continue
                inner = m.group(1)
                if re.fullmatch(r"concept_\w+", inner):
                    subs = shown(LOC[inner], depth + 1)
                elif inner.startswith("Concept("):
                    subs = [re.search(r",\s*'([^']*)'\s*\)$", inner).group(1)]
                    subs = [s for x in subs for s in shown(x, depth + 1)]
                elif inner.startswith("OneOf(") or "SelectLocalization" in inner:
                    keys = [k for k in re.findall(r"'([\w.\-]+)'", inner) if k in LOC]
                    subs = [s for k in keys for s in shown(LOC[k], depth + 1)]
                else:
                    fmt = re.search(r"\|([%+=\w*]+)$", inner)
                    capped = [figure for name, figure in CAPPED.items() if f"'{name}'" in inner]
                    if fmt and capped:
                        subs = capped
                    elif fmt:
                        subs = [FIGURE.get(fmt.group(1).replace("+=", ""), "12345")]
                    else:
                        subs = ["New York"]  # a name read from the game (the hub's state); the word row wraps it
                nxt.extend(v[:m.start()] + s + v[m.end():] for s in subs)
            variants = nxt
        result.extend(variants)
    return [re.sub(r"#[A-Za-z_]+(?:;\S*)? ?|#!", "", r) for r in result]


def width(text, glyphs):
    icons = len(re.findall(r"@\w+!", text))
    text = re.sub(r"@\w+!", "", text)
    return sum(glyphs.get(c, WIDEST) for c in text) + icons * MONEY_ICON


def cell_text(row, block):
    m = re.search(rf'blockoverride "{block}" \{{\s*(raw_text|text) = "((?:[^"\\]|\\.)*)"', row)
    if not m:
        return None
    return m.group(2) if m.group(1) == "raw_text" else LOC.get(m.group(2), m.group(2))


def rows_in(text):
    """(type, body) of every row instance in `text`."""
    found = []
    for kind in ROW_TYPES:
        found.extend((kind, body) for body in instances(text, kind))
    return found


class AnatomyTest(unittest.TestCase):
    def test_the_tile_is_vanillas_width_with_an_inset_icon_box_at_the_top(self):
        tile = gui_type(WIDGETS_TEXT, "te_state_tile")
        flat = " ".join(tile.split())
        self.assertIn("margin = { 10 10 } minimumsize = { 260 -1 }", flat)
        self.assertIn("widget = { size = { 60 60 } background = { using = dark_area alpha = 0.3 }", flat)
        self.assertIn("icon = { size = { 52 52 } parentanchor = center block \"texture\" {} }", flat)
        # The box keeps the default anchor (top): level with the caption in a tall tile.
        box = block_at(tile, tile.index("widget = {") + len("widget = "))
        self.assertNotIn("parentanchor", own(box))
        self.assertIn('minimumsize = { 170 -1 } maximumsize = { 170 -1 } align = nobaseline block "name" {}', flat)
        self.assertEqual(10 + 60 + 10 + 170 + 10, 260)

    def test_every_row_type_fills_its_column(self):
        for kind, (label, value) in ROW_TYPES.items():
            with self.subTest(row=kind):
                body = " ".join(gui_type(WIDGETS_TEXT, kind).split())
                if kind == "te_state_tile_word_row":
                    self.assertIn(f"size = {{ {label} 20 }}", body)
                    self.assertIn(f"max_width = {label}", body)
                    self.assertIn(f"minimumsize = {{ {value} -1 }} maximumsize = {{ {value} -1 }} "
                                  "align = right|nobaseline", body)
                else:
                    self.assertIn(f'blockoverride "label_size" {{ size = {{ {label} 20 }} }}', body)
                    self.assertIn(f'blockoverride "label_max_width" {{ max_width = {label} }}', body)
                    self.assertIn(f'blockoverride "value_size" {{ size = {{ {value} 20 }} }}', body)
                    self.assertIn(f'blockoverride "value_max_width" {{ max_width = {value} }}', body)
                column = 160 if kind == "te_state_vanilla_tile_row" else 170
                self.assertEqual(label + 4 + value, column)  # te_state_stat_row's spacing is 4
        self.assertIn("minimumsize = { 170 -1 } maximumsize = { 170 -1 }",
                      " ".join(gui_type(WIDGETS_TEXT, "te_state_tile_line").split()))
        self.assertIn('blockoverride "bar_size" { size = { 170 4 } }',
                      " ".join(gui_type(WIDGETS_TEXT, "te_state_tile_bar").split()))

    def test_no_tile_sets_widths_of_its_own(self):
        bodies = [TILES] + [gui_type(WIDGETS_TEXT, name) for name in TILE_BODIES]
        for body in bodies:
            for block in ("label_size", "label_max_width", "value_size", "value_max_width", "bar_size",
                          "bar_indent"):
                self.assertNotIn(f'blockoverride "{block}"', body)
            self.assertNotIn("te_state_stat_row = {", body)
            self.assertNotIn("te_state_stat_bar = {", body)
            self.assertNotIn("fontsize_small", body)
            self.assertNotIn("te_state_climate_row", body)
        self.assertNotIn("type te_state_climate_row", WIDGETS_TEXT)

    def test_each_tile_is_a_te_state_tile_with_its_rows_in_the_rows_block(self):
        tiles = instances(TILES, "te_state_tile")
        self.assertEqual(len(tiles), len(LEFT) + len(RIGHT))
        for tile in tiles:
            tooltip = re.search(r'tooltip = "(\w+)"', own(tile)).group(1)
            with self.subTest(tile=tooltip):
                self.assertIn('blockoverride "texture"', tile)
                self.assertIn('blockoverride "name"', tile)
                self.assertNotIn('blockoverride "extra_widget"', tile)
                if tooltip == "TE_STATE_SEABED_BASIN_TT":
                    self.assertIn('blockoverride "rows_box" {}', tile)
                else:
                    rows = block_at(tile, tile.index('blockoverride "rows" {') + len('blockoverride "rows" '))
                    # rows sit straight in the block: the tile's own flow spaces them
                    self.assertNotIn("flowcontainer", own(rows))


class LayoutTest(unittest.TestCase):
    def columns(self):
        body = TILES[1:-1]
        cols = [block_at(body, m.end() - 1) for m in re.finditer(r"(?m)^\t\tflowcontainer = \{", body)]
        self.assertEqual(len(cols), 2)
        return cols

    def test_two_fixed_columns(self):
        self.assertNotIn("wrap_count", TILES)
        for col in self.columns():
            flat = " ".join(col[:col.index("te_state_tile = {")].split())
            self.assertIn("direction = vertical", flat)
            self.assertIn("ignoreinvisible = yes", flat)
            self.assertIn("minimumsize = { 260 -1 }", flat)

    def test_each_tile_in_its_column_in_order_the_always_shown_one_first(self):
        for col, expected in zip(self.columns(), (LEFT, RIGHT)):
            tiles = instances(col, "te_state_tile")
            names = [re.search(r'tooltip = "(\w+)"', own(t)).group(1) for t in tiles]
            self.assertEqual(names, expected)
            self.assertNotIn("visible", own(tiles[0]))
            for tile in tiles[1:]:
                self.assertIn("visible = ", own(tile))

    def test_every_tile_is_mounted_once(self):
        for key in LEFT + RIGHT:
            with self.subTest(tile=key):
                self.assertEqual(WIDGETS_TEXT.count(f'tooltip = "{key}"'), 1)
                self.assertNotIn(key, STATES_TEXT)
        self.assertEqual(WIDGETS_TEXT.count("te_state_tile = {"), len(LEFT) + len(RIGHT))
        self.assertNotIn("te_state_tile = {", STATES_TEXT)
        for name in ("te_state_tiles", "te_state_tourism_card", "te_state_gm_card", "te_state_gm_site_card",
                     "te_state_gm_trophy_card"):
            self.assertEqual(STATES_TEXT.count(f"{name} = {{}}"), 1, name)

    def test_the_mods_part_follows_vanillas_whole_overview(self):
        overview = gui_type(STATES_TEXT, "state_panel_overview_content")
        grid = overview.index("wrap_count = 2")
        decrees = overview.index('name = "tutorial_highlight_state_decrees"')
        order = [overview.index(f"{name} = {{}}") for name in (
            "te_state_tiles", "te_state_gm_card", "te_state_gm_site_card", "te_state_gm_trophy_card",
            "te_state_tourism_card")]
        self.assertLess(grid, decrees)
        self.assertLess(decrees, order[0])
        self.assertEqual(order, sorted(order))
        # Vanilla's grid holds no mod tile but GDP per Capita, at its head.
        opener = overview.rindex("flowcontainer = {", 0, grid)
        grid_block = block_at(overview, overview.index("{", opener))
        self.assertEqual(re.findall(r'"(TE_STATE_\w+_STATUS)"', grid_block), ["TE_STATE_GDP_PC_STATUS"])
        self.assertLess(grid_block.index("TE_STATE_GDP_PC_STATUS"), grid_block.index("TOOLTIP_CAPITAL_STATE"))


class GdpPerCapitaTest(unittest.TestCase):
    def test_a_caption_and_two_rows(self):
        at = STATES_TEXT.index('text = "TE_STATE_GDP_PC_STATUS"')
        tile = STATES_TEXT[STATES_TEXT.rindex("state_panel_status_item_small = {", 0, at):]
        tile = block_at(tile, tile.index("{"))
        self.assertIn('tooltip = "CURRENT_GDP_STATE"', tile)
        rows = instances(tile, "te_state_vanilla_tile_row")
        self.assertEqual([cell_text(r, "row_label") for r in rows], ["Local", "National"])
        self.assertIn("ScriptValue('gdp_per_capita')|2*]", rows[0])
        self.assertIn("State.GetCountry.GetGDPPerCapita|2*]", rows[1])
        self.assertEqual(LOC["TE_STATE_GDP_PC_STATUS"], "$GDP_SHORT$ per Capita")
        self.assertNotIn("GDPPERCAPITA", LOC)
        self.assertNotIn("GDPPERCAPITA", STATES_TEXT)


class WidthBudgetTest(unittest.TestCase):
    """English labels (regular) and values (bold) fit their cells with 5% to spare."""

    def all_rows(self):
        bodies = [TILES] + [gui_type(WIDGETS_TEXT, name) for name in TILE_BODIES]
        gdp = STATES_TEXT[STATES_TEXT.index('text = "TE_STATE_GDP_PC_STATUS"'):]
        bodies.append(gdp[:gdp.index("TOOLTIP_CAPITAL_STATE")])
        return [row for body in bodies for row in rows_in(body)]

    def test_rows_found(self):
        self.assertGreaterEqual(len(self.all_rows()), 40)

    def test_every_label_and_value_fits(self):
        for kind, row in self.all_rows():
            label_cell, value_cell = ROW_TYPES[kind]
            for block, cell, glyphs in (("row_label", label_cell, REGULAR_14), ("row_value", value_cell, BOLD_14)):
                text = cell_text(row, block)
                if text is None or "ExecuteTooltip" in text:
                    continue  # a culture's name: test_every_culture_fits_the_culture_row
                if kind == "te_state_tile_word_row" and block == "row_value":
                    continue  # a name that wraps: test_names_wrap
                for variant in shown(text):
                    need = width(variant, glyphs) * MARGIN
                    with self.subTest(row=kind, text=variant):
                        self.assertLessEqual(need, cell, f"{variant!r} needs {need:.0f} of {cell}")

    def test_every_culture_fits_the_culture_row(self):
        cultures = json.loads((VANILLA / "common" / "cultures.json").read_text(encoding="utf-8"))
        names = [LOC[c] for c in cultures if c in LOC and "$" not in LOC[c]]
        self.assertGreater(len(names), 200)
        label, value = ROW_TYPES["te_state_tile_culture_row"]
        for name in names:
            with self.subTest(culture=name):
                self.assertLessEqual(width(name, REGULAR_14), label)
        self.assertLessEqual(width("100.0%", BOLD_14), value)

    def test_names_wrap(self):
        # A name as the value wraps in its fixed width, ending at the column's right edge.
        body = " ".join(gui_type(WIDGETS_TEXT, "te_state_tile_word_row").split())
        self.assertIn("multiline = yes minimumsize = { 114 -1 } maximumsize = { 114 -1 } align = right|nobaseline",
                      body)
        users = [r for _, r in rows_in(TILES) if _ == "te_state_tile_word_row"]
        self.assertEqual(sorted(cell_text(r, "row_label") for r in users), ["Basin", "Hub"])
        for basin in ("te_seabed_basin_pacific", "te_seabed_basin_atlantic", "te_seabed_basin_indian",
                      "te_seabed_basin_arctic", "te_seabed_basin_southern"):
            self.assertLessEqual(width(LOC[basin], BOLD_14) * MARGIN, ROW_TYPES["te_state_tile_word_row"][1])

    def test_the_un_missions_kind_is_a_line_of_its_own(self):
        at = TILES.index('tooltip = "TE_STATE_UN_MISSION_TT"')
        tile = TILES[at:]
        self.assertIn('te_state_tile_line = { text = "TE_STATE_UN_ROW_KIND_VALUE" }', " ".join(tile.split()))
        self.assertNotIn("TE_STATE_UN_ROW_TYPE\"", WIDGETS_TEXT)


if __name__ == "__main__":
    unittest.main()
