"""The Demographics panels' section order, collapse defaults, type sizes and widths.

Issue #1029 rebuilt the Population panel's Demographics tab and the state panel's
Demographics subtab on the Banking panel's model (test_banking_layout.py):
one layout file sets the sections' order for every host (the Census Data
window's Demographics tab takes the tab's, in three columns), an overview of icon
cells on top, Causes of Death with a pie at both levels, History's charts with
marker pips, States rows that open the state, and every collapse flag named for
its default. This file holds those to the markup, and every fixed cell's
longest text to its width.
"""
import json
import os
import re
import unittest
from decimal import ROUND_HALF_UP, Decimal

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui")
WIDGETS = os.path.join(GUI, "te_demographics_widgets.gui")
LAYOUT = os.path.join(GUI, "te_demographics_layout.gui")
POPS = os.path.join(GUI, "pops_overview.gui")
BROWSER = os.path.join(GUI, "pop_browser_panel.gui")
STATES = os.path.join(GUI, "states_panel.gui")
CHART = os.path.join(GUI, "journal_entry_widgets", "te_history_chart.gui")
LOC_DIR = os.path.join(REPO, "localization", "english")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_demog_sguis.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_demog_effects.txt")
HISTORY = os.path.join(REPO, "common", "scripted_effects", "te_demog_history_effects.txt")
DISPLAY = os.path.join(REPO, "common", "script_values", "te_demog_display_values.txt")
PIE_GEN = os.path.join(REPO, "scripts", "image_pipeline", "gen_ch_model_pie_textures.py")
ICONS_DOC = os.path.join(REPO, "docs", "systems", "demographics_gui_icons.md")

# The issue's order: the people's health, the levers, the record, the per-state detail; How it works at the foot.
COUNTRY = ["te_demog_overview", "te_demog_sec_causes", "te_demog_sec_pyramid", "te_demog_sec_work",
           "te_demog_sec_longevity", "te_demog_sec_family", "te_demog_sec_history", "te_demog_sec_wealth",
           "te_demog_sec_places", "te_demog_sec_states"]
# The state's, the same order less the sections a state has no figures for, and its own Modifiers after Wealth (the
# nine standing census modifiers its modifier rows leave out; the country has none).
STATE = ["te_state_demog_overview", "te_state_demog_causes", "te_state_demog_pyramid", "te_state_demog_work",
         "te_state_demog_longevity", "te_state_demog_wealth", "te_state_demog_modifiers"]
STATE_ONLY = ["te_state_demog_modifiers"]
HOW = {"te_demog_tab_sections": "te_demog_sec_how", "te_state_demog_content": "te_state_demog_how"}
# The Census Data window's composer: the tab's sections for the window's country, in three columns.
BROWSER_COMPOSER = "te_demog_browser_sections"

# The history chart's slices, from the foot (te_dg_dc_lead's codes 1-8): the loc and variable name, the texture. The
# pie's are the same less the deaths added on top (code 6), which count under their causes since 2026-10-22 (owner); the
# chart keeps their layer, so a save's older years keep their colours.
SLICES = [("inf", "infection"), ("chr", "chronic"), ("ext", "external"), ("work", "work"), ("mat", "maternal"),
          ("ontop", "on_top"), ("kill", "killed"), ("war", "war")]
PIE_SLICES = [s for s in SLICES if s[0] != "ontop"]
PIE_CODES = [1, 2, 3, 4, 5, 7]     # the cumulative sums the pie's layers read (te_demog_dc_cum_<n>), the last disc whole
PIE_DIR = "gfx/interface/icons/demographics_icons/"


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


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return _block_from(text, m.end() - 1)[1:-1]


def _types(text):
    return re.findall(r"(?m)^\s*type (\w+) = \w+ \{", text)


def _instances(text, name):
    """Each `name = { ... }` block in `text`, braces included."""
    return [_block_from(text, m.end() - 1) for m in re.finditer(rf"(?<![\w.]){name} = \{{", text)]


def _override(block, name):
    """The body of blockoverride `name` in `block`, or None."""
    m = re.search(rf'blockoverride "{name}" \{{', block)
    return _block_from(block, m.end() - 1)[1:-1] if m else None


def _children(body):
    """The names of a block's direct `x = {}` children, in order."""
    out, depth = [], 0
    for line in body.splitlines():
        stripped = line.strip()
        if depth == 0:
            m = re.match(r"(\w+) = \{", stripped)
            if m:
                out.append(m.group(1))
        depth += line.count("{") - line.count("}")
    return out


def _loc():
    """The mod's English loc over vanilla's (vanilla_parsed/), for vanilla concepts' names."""
    with open(os.path.join(REPO, "vanilla_parsed", "localization_english.json"), encoding="utf-8") as f:
        keys = dict(json.load(f))
    for name in sorted(os.listdir(LOC_DIR)):
        if name.endswith(".yml"):
            for line in _read(os.path.join(LOC_DIR, name)).splitlines():
                m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
                if m:
                    keys[m.group(1)] = m.group(2)
    return keys


def _sgui_names():
    return set(re.findall(r"(?m)^(\w+) = \{", _read(SGUIS)))


class OrderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = _read(LAYOUT)
        cls.widgets = _read(WIDGETS)

    def sections(self, composer):
        body = _type_body(self.layout, composer)
        inner = [b for b in _instances(body, "flowcontainer") if "visible" in b]
        self.assertEqual(len(inner), 1, f"{composer}: one gated list of sections")
        return _children(inner[0][1:-1]), _children(body)

    def test_the_country_order(self):
        listed, outer = self.sections("te_demog_tab_sections")
        self.assertEqual(listed, COUNTRY)
        self.assertEqual(outer[-1], HOW["te_demog_tab_sections"], "How Demographics Works at the foot")

    def test_the_state_order_is_the_countrys_less_what_a_state_lacks(self):
        listed, outer = self.sections("te_state_demog_content")
        self.assertEqual(listed, STATE)
        self.assertEqual(outer[-1], HOW["te_state_demog_content"])
        as_country = [s.replace("te_state_demog_", "te_demog_sec_").replace("sec_overview", "overview")
                      for s in STATE if s not in STATE_ONLY]
        self.assertEqual(as_country, [s for s in COUNTRY if s in as_country], "the state keeps the country's order")

    def test_the_census_window_takes_the_tabs_order_in_three_columns(self):
        body = _type_body(self.layout, BROWSER_COMPOSER)
        inner = [b for b in _instances(body, "flowcontainer") if "visible" in b and "direction = horizontal" in b]
        self.assertEqual(len(inner), 1, "one gated row of columns")
        self.assertEqual(_children(inner[0][1:-1]), ["flowcontainer"] * 3)
        columns = [b for b in _instances(inner[0][1:-1], "flowcontainer")]
        self.assertEqual(len(columns), 3)
        for column in columns:
            with self.subTest(column=_children(column[1:-1])):
                self.assertIn("minimumsize = { 520 -1 }", column)
                self.assertIn("maximumsize = { 520 -1 }", column)
        listed = [c for column in columns for c in _children(column[1:-1]) if c not in ("minimumsize", "maximumsize")]
        self.assertEqual(listed, COUNTRY + [HOW["te_demog_tab_sections"]], "read down each column, then across")

    def test_the_layout_file_holds_only_the_three_composers(self):
        self.assertEqual(sorted(_types(self.layout)),
                         sorted(["te_demog_tab_sections", "te_state_demog_content", BROWSER_COMPOSER]))
        for composer in list(HOW) + [BROWSER_COMPOSER]:
            self.assertNotIn(f"type {composer} =", self.widgets)

    def test_every_section_is_a_type_and_each_is_placed_once(self):
        defined = set(_types(self.widgets))
        placed = COUNTRY + STATE + list(HOW.values())
        hosts = {"te_demog_tab_sections": COUNTRY + [HOW["te_demog_tab_sections"]],
                 BROWSER_COMPOSER: COUNTRY + [HOW["te_demog_tab_sections"]],
                 "te_state_demog_content": STATE + [HOW["te_state_demog_content"]]}
        for composer, sections in hosts.items():
            body = _type_body(self.layout, composer)
            for section in sections:
                with self.subTest(composer=composer, section=section):
                    self.assertIn(section, defined)
                    self.assertEqual(len(re.findall(rf"\b{section} = \{{\}}", body)), 1)
        for section in placed:
            with self.subTest(section=section):
                expected = 1 if section.startswith("te_state_demog_") else 2
                self.assertEqual(len(re.findall(rf"\b{section} = \{{\}}", self.layout)), expected)
        sections = {t for t in defined if t.startswith("te_demog_sec_") or t == "te_demog_overview"}
        sections |= {t for t in defined if t.startswith("te_state_demog_") and not t.endswith("_row")}
        self.assertEqual(sections, set(placed), "a section type the layout doesn't place")

    def test_no_type_is_defined_in_both_files(self):
        self.assertFalse(set(_types(self.layout)) & set(_types(self.widgets)))

    def test_each_host_instances_its_composer_once(self):
        self.assertEqual(_read(POPS).count("te_demog_tab_sections = {}"), 1)
        self.assertEqual(_read(BROWSER).count(f"{BROWSER_COMPOSER} = {{}}"), 1)
        self.assertEqual(_read(STATES).count("te_state_demog_content = {}"), 1)


def _toggles(body):
    return re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", body)


def _norm(text):
    return re.sub(r"\s+", "", text)


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.widgets = _read(WIDGETS)
        cls.flat = _norm(cls.widgets)

    def test_every_flag_says_its_default(self):
        flags = _toggles(self.widgets) + _toggles(_read(LAYOUT))
        self.assertGreaterEqual(len(flags), 15)
        for flag in flags:
            with self.subTest(flag=flag):
                self.assertRegex(flag, r"_(open|closed)$")
                self.assertTrue(flag.startswith("te_demog_"), "the panel's own namespace")

    def test_closed_flags_start_open_and_open_flags_start_collapsed(self):
        for flag in set(_toggles(self.widgets)):
            shown_when_unset = f"Not(GetVariableSystem.Exists('{flag}'))"
            with self.subTest(flag=flag):
                if flag.endswith("_closed"):
                    self.assertTrue(shown_when_unset in self.flat, "a _closed section shows while the flag is unset")
                else:
                    shown_when_set = self.flat.count(f"GetVariableSystem.Exists('{flag}')")
                    self.assertGreater(shown_when_set, self.flat.count(shown_when_unset), "an _open one while set")
                    self.assertLessEqual(self.flat.count(shown_when_unset), 1,
                                         "an _open flag's unset side is drawn once (its header's arrow)")

    def test_sections_open_and_how_it_works_collapsed(self):
        """Rule 1: the live sections start open; How Demographics Works starts collapsed (rule 7)."""
        for section in COUNTRY[1:] + STATE[1:] + list(HOW.values()):
            body = _type_body(self.widgets, section)
            header = _instances(body, "te_demog_section_header")
            with self.subTest(section=section):
                self.assertEqual(len(header), 1, "one header")
                flag, = _toggles(header[0])
                self.assertTrue(flag.endswith("_open" if section in HOW.values() else "_closed"), flag)

    def test_the_hosts_keep_their_own_flags(self):
        country = set()
        for section in COUNTRY + [HOW["te_demog_tab_sections"]]:
            country |= set(_toggles(_type_body(self.widgets, section)))
        state = set()
        for section in STATE + [HOW["te_state_demog_content"]]:
            state |= set(_toggles(_type_body(self.widgets, section)))
        self.assertFalse(country & state, "collapsing a section on one host leaves the other alone")
        for flag in state:
            with self.subTest(flag=flag):
                self.assertTrue(flag.startswith("te_demog_st_"))
        for flag in country:
            with self.subTest(flag=flag):
                self.assertFalse(flag.startswith("te_demog_st_"))

    def test_the_overview_has_no_header(self):
        for overview in ("te_demog_overview", "te_state_demog_overview"):
            self.assertNotIn("te_demog_section_header", _type_body(self.widgets, overview))


def _textboxes(text):
    """Every textbox block in `text`, with the type it sits in."""
    starts = [(m.start(), m.group(1)) for m in re.finditer(r"(?m)^\s*type (\w+) = \w+ \{", text)]
    out = []
    for m in re.finditer(r"\btextbox = \{", text):
        owner = None
        for start, name in starts:
            if start < m.start():
                owner = name
        out.append((owner, _block_from(text, m.end() - 1)))
    return out


def _own(block):
    """A block's own lines, its nested blocks removed."""
    inner = block[1:-1]
    while re.search(r"\{[^{}]*\}", inner):
        inner = re.sub(r"\{[^{}]*\}", "", inner)
    return inner


class FontTest(unittest.TestCase):
    """Rule 3, as Banking's owner pass set it (2026-10-17): rows 17, headings 20, the overview's cells 16 in the tooltip
    face; the charts' legends and axis labels keep vanilla's medium."""

    @classmethod
    def setUpClass(cls):
        cls.widgets = _read(WIDGETS)

    def test_the_templates(self):
        sizes = {m.group(1): int(m.group(2)) for m in re.finditer(
            r"template te_demog_fontsize_(\w+) \{\s*fontsize = (\d+)", self.widgets)}
        self.assertEqual(sizes, {"row": 17, "heading": 20, "overview": 16})
        self.assertIn("using = tooltip_font", _block_from(self.widgets, self.widgets.index(
            "template te_demog_fontsize_overview")))
        self.assertEqual(len(re.findall(r"\bfontsize = \d+", self.widgets)), 3, "sizes only in the templates")

    def test_every_textbox_takes_a_template(self):
        medium_ok = {"te_demog_sec_history", "te_demog_hist_pip_legend"}
        found = _textboxes(self.widgets) + _textboxes(_read(LAYOUT))
        self.assertGreater(len(found), 60)
        for owner, block in found:
            fonts = [u for u in re.findall(r"using = (\w+)", _own(block)) if "font" in u]
            with self.subTest(type=owner, text=re.search(r'text = "([^"]{0,60})', block)):
                self.assertEqual(len(fonts), 1, "one font")
                if fonts[0] == "fontsize_medium":
                    self.assertIn(owner, medium_ok, "vanilla's medium only in History's legends and labels")
                else:
                    self.assertRegex(fonts[0], r"^te_demog_fontsize_(row|heading|overview)$")

    def test_the_overview_cells_use_the_overview_face(self):
        cell = _type_body(self.widgets, "te_demog_ov_cell")
        for block in ("caption", "word", "third_line"):
            box = next(b for _, b in _textboxes(cell) if f'block "{block}"' in b)
            self.assertIn("using = te_demog_fontsize_overview", box)

    def test_the_charts_titles_are_headings(self):
        history = _type_body(self.widgets, "te_demog_sec_history")
        charts = _instances(history, "te_history_chart")
        for chart in charts:
            self.assertIn("using = te_demog_fontsize_heading", _override(chart, "chart_title_font"))
            self.assertIn("using = fontsize_medium", _override(chart, "chart_legend_font"))

    def test_only_a_states_name_shrinks(self):
        for owner, block in _textboxes(self.widgets):
            if "fontsize_min" in block:
                with self.subTest(type=owner):
                    self.assertIn("State.GetNameNoFormatting", block)


# ---------------------------------------------------------------------------
# Widths. Banking's budget (test_banking_layout's WidthBudgetTest): GUI units a character, from the owner's screenshots,
# scaled to each template's size (the serif face at 10 a character in 20, the tooltip face at 8.6 in 16), plus 10%.
# ---------------------------------------------------------------------------
UNITS = {"row": 10.0 / 20 * 17, "heading": 10.0 / 20 * 20, "overview": 8.6 / 16 * 16}
MARGIN = 1.1
# The widest a figure prints, by its format; a few named data by their own range.
FORMAT_WIDEST = {"0": "100", "+0": "+100", "1": "99.9", "+1": "+99.9", "2": "9.99", "%0": "100%", "%1": "99.9%",
                 "K": "999.9K"}
# Net migration is signed; the census years are four digits; the share of infants who die never rounds to 100%, and
# the share aged 65 and over only in a state with nobody younger.
DATA_WIDEST = {"te_dg_net_migration": "-999.9K", "te_dg_census_year": "2000", "te_dg_year": "2000",
               "te_demog_imr_share": "99%", "te_dg_old_share": "99%"}
# Life expectancy is shown as it is up to 10,000 years, "over 10,000" past it (2026-10-20): its figures print up to
# 9,999.9. The states list's narrow column shows it whole from 1,000 (te_demog_states_e0_cell's switch), so its two
# branches print at most these.
DATA_WIDEST.update(dict.fromkeys(("te_dg_e0", "te_dg_e0f", "te_dg_e0m", "te_dg_e65", "te_dg_prev_e0"), "9,999.9"))
KEY_WIDEST = {"te_demog_states_e0_small": "999.9", "te_demog_states_e0_whole": "9,999"}


class WidthTest(unittest.TestCase):
    """Nothing a player reads in a fixed cell may elide: each cell's longest text fits its width in its font."""

    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()
        cls.widgets = _read(WIDGETS)

    # -- text ---------------------------------------------------------------
    def shown(self, key, depth=0):
        """The widest text a loc key can show: splices, concepts and SelectLocalization resolved, formatting stripped,
        each figure at its widest."""
        self.assertLess(depth, 8, key)
        if key in KEY_WIDEST:
            return KEY_WIDEST[key]
        value = self.loc.get(key)
        self.assertIsNotNone(value, f"no loc for {key}")
        value = re.sub(r"\$(\w+)\$", lambda m: self.shown(m.group(1), depth + 1), value)
        value = self.expressions(value, depth)
        value = re.sub(r"#[A-Za-z_]+(?:;\S*)? ", "", value).replace("#!", "")
        value = re.sub(r"@\w+!", "", value)
        return max(value.split("\\n"), key=len)

    def expressions(self, value, depth):
        def one(m):
            expr = m.group(1)
            concept = re.fullmatch(r"Concept\('\w+',\s*'([^']*)'\)", expr)
            if concept:
                return concept.group(1)
            if re.fullmatch(r"concept_\w+", expr):
                return self.shown(expr, depth + 1)
            if "SelectLocalization" in expr:
                options = [k for k in re.findall(r"'(\w+)'", expr) if k in self.loc]
                self.assertTrue(options, expr)
                return max((self.shown(k, depth + 1) for k in options), key=len)
            return self.figure(expr)
        return re.sub(r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]", one, value)

    def figure(self, expr):
        if "GetName" in expr:
            return "South Atlantic Islands"
        named = re.findall(r"'(te_\w+)'", expr)
        for name in named:
            if name in DATA_WIDEST:
                return DATA_WIDEST[name]
        fmt = re.search(r"\|([^\]|]+)$", expr)
        self.assertTrue(fmt, f"a figure with no format: {expr}")
        self.assertIn(fmt.group(1), FORMAT_WIDEST, f"no widest for format |{fmt.group(1)}: {expr}")
        return FORMAT_WIDEST[fmt.group(1)]

    def markup(self, text):
        """The widest a textbox's `text = "..."` shows."""
        if re.fullmatch(r"\w+", text):
            return self.shown(text)
        return self.expressions(text, 0)

    # -- cells --------------------------------------------------------------
    def cell(self, box):
        """(width, font) of a textbox, read from its markup."""
        width = re.search(r"max_width = (\d+)", box) or re.search(r"maximumsize = \{ (\d+) ", box)
        font = re.search(r"using = te_demog_fontsize_(\w+)", box)
        self.assertTrue(width and font, box[:200])
        return int(width.group(1)), font.group(1)

    def type_cell(self, typ, block):
        return self.cell(next(b for _, b in _textboxes(_type_body(self.widgets, typ)) if f'block "{block}"' in b))

    def fits(self, text, cell, what):
        width, font = cell
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, width, f"{what} shows {text!r}: {need:.0f} units in a {width} {font} cell")

    def overridden(self, typ, block, bodies):
        """Each (text, instance) an instance of `typ` sets for `block`."""
        out = []
        for body in bodies:
            for inst in _instances(body, typ):
                over = _override(inst, block)
                if over is not None:
                    out.append(re.search(r'text = "(.*)"', over).group(1))
        return out

    def check_type(self, typ, blocks, bodies, at_least):
        texts = 0
        for block in blocks:
            cell = self.type_cell(typ, block)
            for text in self.overridden(typ, block, bodies):
                texts += 1
                with self.subTest(type=typ, block=block, text=text[:70]):
                    self.fits(self.markup(text), cell, f"{typ} {block}")
        self.assertGreaterEqual(texts, at_least, typ)

    def test_the_overview_cells(self):
        """Every caption, reading and third line, in both overviews, fits the 154 beside the icon box."""
        self.assertEqual(self.type_cell("te_demog_ov_cell", "caption"), (154, "overview"))
        bodies = [_type_body(self.widgets, "te_demog_overview"), _type_body(self.widgets, "te_state_demog_overview")]
        self.check_type("te_demog_ov_cell", ("caption", "word", "third_line"), bodies, 48)

    def test_the_cause_legend(self):
        bodies = [_type_body(self.widgets, s) for s in ("te_demog_sec_causes", "te_state_demog_causes")]
        self.check_type("te_demog_cause_row", ("cause", "deaths", "share"), bodies, 42)
        head = _type_body(self.widgets, "te_demog_cause_head")
        for _, box in _textboxes(head):
            key = re.search(r'text = "(\w+)"', box).group(1)
            with self.subTest(head=key):
                self.fits(self.shown(key), self.cell(box), key)

    def test_the_figure_and_term_rows(self):
        bodies = [self.widgets]
        self.check_type("te_demog_figure_row", ("row_label",), bodies, 20)
        self.check_type("te_demog_term_row", ("row_label", "row_value"), bodies, 5)

    def test_the_state_link_rows(self):
        """Each list's figure fits the link row's 284 at 17, beside the 184 name (2026-10-27 audit, DEM-6)."""
        row = [self.cell(b) for _, b in _textboxes(_type_body(self.widgets, "te_demog_state_link_row"))]
        self.assertEqual(row, [(184, "row"), (284, "row")])
        self.assertEqual(4 + 184 + 4 + 284, 476)
        self.check_type("te_demog_state_link_row", ("link_value",), [self.widgets], 2)
        city = re.search(r'blockoverride "link_value" \{\s*text = "(\w+)"', _type_body(self.widgets, "te_demog_city_row"))
        self.fits(self.shown(city.group(1)), row[1], "te_demog_city_row")

    def test_the_states_table(self):
        head = [b for _, b in _textboxes(_type_body(self.widgets, "te_demog_state_head"))]
        row = [b for _, b in _textboxes(_type_body(self.widgets, "te_demog_state_row"))]
        self.assertEqual([self.cell(b)[0] for b in head], [self.cell(b)[0] for b in row], "the heads sit over the cells")
        for box in head:
            key = re.search(r'text = "(\w+)"', box).group(1)
            with self.subTest(head=key):
                self.fits(self.shown(key), self.cell(box), key)
        for box in row[1:]:     # the name shrinks to 12 rather than elide (FontTest)
            text = re.search(r'text = "(.*)"', box).group(1)
            with self.subTest(cell=text):
                self.fits(self.markup(text), self.cell(box), text)
        self.assertEqual(4 + sum(self.cell(b)[0] for b in row) + 4 * (len(row) - 1), 478, "inside the 480 row")

    def test_the_life_column_at_its_edges(self):
        """Life expectancy in the states list (2026-10-20): a tenth of a year below the cell's first threshold, whole years
        up to the GUI's 10K+ threshold. At each edge, the engine's figure (five decimals) rounded half up by its format
        still fits the column, so no branch prints 1,000.0 or 10,000."""
        row = _type_body(self.widgets, "te_demog_state_row")
        e0 = r"State\.MakeScope\.Var\('te_dg_e0'\)\.GetValue"
        over = re.search(rf"GreaterThanOrEqualTo_CFixedPoint\( {e0}, '\(CFixedPoint\)([\d.]+)' \), "
                         r"'te_demog_states_e0_over', 'te_demog_states_e0_cell'", row)
        small = re.search(rf"LessThan_CFixedPoint\( {e0}, '\(CFixedPoint\)([\d.]+)' \), 'te_demog_states_e0_small', "
                          r"'te_demog_states_e0_whole'", self.loc["te_demog_states_e0_cell"])
        self.assertTrue(over and small)
        over, small = Decimal(over.group(1)), Decimal(small.group(1))
        self.assertLessEqual(over, 10000, "10K+ never stands for a figure the panel shows below 10,000 elsewhere")
        box = next(b for _, b in _textboxes(row) if "te_demog_states_e0_over" in b)
        step = Decimal("0.00001")
        for v in (Decimal(0), small - step, small, Decimal(1000), over - step, over, Decimal(10000), Decimal(100000)):
            if v >= over:
                text = self.shown("te_demog_states_e0_over")
            elif v < small:
                text = f"{v.quantize(Decimal('0.1'), ROUND_HALF_UP):,}"
            else:
                text = f"{v.quantize(Decimal('1'), ROUND_HALF_UP):,}"
            with self.subTest(e0=str(v)):
                self.fits(text, self.cell(box), f"life expectancy {v}")

    def test_the_show_all_button(self):
        body = _type_body(self.widgets, "te_demog_sec_states")
        box = next(b for _, b in _textboxes(body) if "te_demog_states_show_top" in b)
        width = int(re.search(r"max_width = (\d+)", box).group(1))
        text = re.search(r'text = "(.*)"', box).group(1)
        self.fits(self.markup(text), (width, "row"), "Show All")

    def test_the_chart_titles(self):
        chart = _read(CHART)
        title = chart[chart.index("type te_history_chart"):]
        width = int(re.search(r'max_width = (\d+)\s*elide = right\s*align = nobaseline\s*block "chart_title_font"',
                              title).group(1))
        history = _type_body(self.widgets, "te_demog_sec_history")
        titles = [re.search(r'text = "(\w+)"', _override(c, "chart_title")).group(1)
                  for c in _instances(history, "te_history_chart")]
        self.assertEqual(len(titles), 8)
        for key in titles:
            with self.subTest(title=key):
                self.fits(self.shown(key), (width, "heading"), key)


def _doc_tables(heading):
    """Each table row of the icon doc under `heading` (its nearest heading of any level), as its cells."""
    rows, under = [], None
    for line in _read(ICONS_DOC).splitlines():
        if line.startswith("#"):
            under = line.lstrip("#").strip()
        elif under == heading and line.startswith("| ") and not line.startswith("|---") and "`" in line:
            rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows


class IconsTest(unittest.TestCase):
    """docs/systems/demographics_gui_icons.md lists every overview cell's and pip's icon (rule 10)."""

    @classmethod
    def setUpClass(cls):
        cls.widgets = _read(WIDGETS)
        cls.cells = [(r[0], r[1].strip("`"), r[3].strip("`")) for r in _doc_tables("Overview cells")]
        cls.causes = [(int(r[0]), r[3].strip("`")) for r in _doc_tables("The leading cause's icons")]
        cls.pips = [(r[0], r[1].strip("`"), r[2], r[4].strip("`")) for r in _doc_tables("History pips")]

    def cell_icons(self, overview):
        body = _type_body(self.widgets, overview)
        return [re.search(r'texture = "([^"]+)"', _override(c, "icon")).group(1)
                for c in _instances(body, "te_demog_ov_cell")]

    def test_each_cell_draws_the_listed_icon(self):
        self.assertEqual(len(self.cells), 8)
        listed = [placeholder for _, placeholder, _ in self.cells]
        for overview in ("te_demog_overview", "te_state_demog_overview"):
            with self.subTest(overview=overview):
                self.assertEqual(self.cell_icons(overview), listed)

    def test_the_lead_cells_draw_each_causes_icon(self):
        """The Leading Cause cell's headstone shows until deaths by cause are counted, then its cause's icon, by code;
        War also takes the old code 6, as the reading's text does."""
        self.assertEqual([code for code, _ in self.causes], PIE_CODES + [8])
        headstone = PIE_DIR + "ov_leading_cause.dds"
        for overview, ready in (("te_demog_overview", "te_demog_dc_ready_sgui"),
                                ("te_state_demog_overview", "te_demog_state_dc_sgui")):
            with self.subTest(overview=overview):
                cells = [c for c in _instances(_type_body(self.widgets, overview), "te_demog_ov_cell")
                         if headstone in (_override(c, "icon") or "")]
                self.assertEqual(len(cells), 1)
                icon, layers = _override(cells[0], "icon"), _override(cells[0], "icon_layers")
                self.assertIn(f"Not( GetScriptedGui('{ready}')", icon)
                self.assertIn(f"visible = \"[GetScriptedGui('{ready}')", layers)
                drawn = []
                for layer in _instances(layers, "icon"):
                    codes = sorted(int(c) for c in re.findall(r"'\(CFixedPoint\)(\d+)'", layer))
                    drawn.append((codes, re.search(r'texture = "([^"]+)"', layer).group(1)))
                self.assertEqual(drawn, [([code], tex) for code, tex in self.causes[:-1]]
                                 + [([6, 8], self.causes[-1][1])])

    def test_the_cells_name_their_captions(self):
        captions = [self.shown_caption(c) for c in _instances(_type_body(self.widgets, "te_demog_overview"),
                                                                 "te_demog_ov_cell")]
        doc = [name for name, _, _ in self.cells]
        for caption, name in zip(captions, doc):
            with self.subTest(caption=caption):
                self.assertTrue(name.startswith(caption), f"the doc's {name!r} is the cell {caption!r}")

    def shown_caption(self, cell):
        key = re.search(r'text = "(\w+)"', _override(cell, "caption")).group(1)
        return _loc()[key]

    def test_each_pip_draws_the_listed_icon(self):
        self.assertEqual(len(self.pips), 3)
        pips = _type_body(self.widgets, "te_demog_hist_pips")
        legend = _type_body(self.widgets, "te_demog_hist_pip_legend")
        for body in (pips, legend):
            drawn = re.findall(r'size = \{ (\d+) \d+ \}\s*texture = "([^"]+)"', body)
            self.assertEqual([(f"{size} px", tex) for size, tex in drawn],
                             [(size, tex) for _, tex, size, _ in self.pips])

    def test_the_proposed_files_are_the_panels_own(self):
        for _, _, proposed in self.cells:
            self.assertTrue(proposed.startswith(PIE_DIR), proposed)
        for *_, proposed in self.pips:
            self.assertTrue(proposed.startswith(PIE_DIR), proposed)

    def test_the_pies_textures_and_colours_are_listed(self):
        doc = _read(ICONS_DOC)
        colours = re.findall(r"`(#[0-9a-f]{6})`", doc)
        self.assertEqual(colours, [c for _, c in _pie_colours()])


def _pie_colours():
    """The generator's (texture, colour) pairs for the demographics pie, in its order."""
    return re.findall(r'\("icons/demographics_icons/(pie_\w+)\.dds", "(#[0-9a-f]{6})"\)', _read(PIE_GEN))


class PieTest(unittest.TestCase):
    """The stacked progresspie recipe (gui_modding_guide.md, "Pie charts of script-held data"): the largest cumulative
    layer first, so slice n shows between the sums through n - 1 and n."""

    @classmethod
    def setUpClass(cls):
        cls.widgets = _read(WIDGETS)

    def test_the_layers(self):
        pie = _type_body(self.widgets, "te_demog_cause_pie")
        layers = _instances(pie, "progresspie")
        self.assertEqual(len(layers), 7)
        textures = [re.search(r'texture = "([^"]+)"', b).group(1) for b in layers]
        self.assertEqual(textures, [f"{PIE_DIR}pie_{tex}.dds" for _, tex in reversed(PIE_SLICES)])
        self.assertIn("value = 1", layers[0], "the last slice is the whole disc")
        self.assertEqual([re.search(r'block "(cum_\d)"', b).group(1) for b in layers[1:]],
                         [f"cum_{n}" for n in reversed(PIE_CODES)])
        for layer in layers:
            self.assertIn("frame = 2", layer)

    def test_the_generator_makes_each_texture(self):
        self.assertEqual([t for t, _ in _pie_colours()], [f"pie_{tex}" for _, tex in SLICES])

    def test_each_pie_reads_its_hosts_sums(self):
        for section, root in (("te_demog_sec_causes", "Country.MakeScope"),
                              ("te_state_demog_causes", "State.MakeScope")):
            pies = _instances(_type_body(self.widgets, section), "te_demog_cause_pie")
            self.assertEqual(len(pies), 1, section)
            for n in PIE_CODES:
                with self.subTest(section=section, n=n):
                    self.assertIn(f"{root}.ScriptValue('te_demog_dc_cum_{n}')", _override(pies[0], f"cum_{n}"))

    def test_the_sums_run_in_the_slices_order(self):
        display = _read(DISPLAY)
        for prev, n, (name, _tex) in zip(PIE_CODES, PIE_CODES[1:], PIE_SLICES[1:]):
            body = _block_from(display, display.index(f"te_demog_dc_cum_{n} = {{"))
            self.assertIn(f"value = te_demog_dc_cum_{prev}", body)
            self.assertIn(f"add = te_demog_dc_share_{name}", body)
        self.assertNotIn("te_demog_dc_cum_6 = {", display)
        first = _block_from(display, display.index("te_demog_dc_cum_1 = {"))
        self.assertIn(f"value = te_demog_dc_share_{SLICES[0][0]}", first)

    def test_each_legend_names_the_slices_in_order(self):
        for section, root in (("te_demog_sec_causes", "Country"), ("te_state_demog_causes", "State")):
            rows = _instances(_type_body(self.widgets, section), "te_demog_cause_row")
            self.assertEqual(len(rows), 7, section)
            for row, (name, tex) in zip(rows, PIE_SLICES):
                with self.subTest(section=section, slice=name):
                    self.assertIn(f'texture = "{PIE_DIR}pie_{tex}.dds"', _override(row, "swatch"))
                    self.assertIn(f'text = "te_demog_dc_{name}"', _override(row, "cause"))
                    self.assertIn(f"Var('te_dg_dc_{name}')", _override(row, "deaths"))
                    self.assertIn(f"te_demog_dc_share_{name}", _override(row, "share"))
                    self.assertIn(root, _override(row, "deaths"))

    def test_the_history_chart_uses_the_pies_colours(self):
        history = _type_body(self.widgets, "te_demog_sec_history")
        chart = next(c for c in _instances(history, "te_history_chart")
                     if "te_demog_hist_causes_title" in _override(c, "chart_title"))
        layers = re.findall(r"color = \{ ([\d.]+) ([\d.]+) ([\d.]+) 1\.0 \}\s*value = \"\[FixedPointToFloat\( "
                            r"ScriptContainer\.GetVariableValue\('te_dg_h_c(\d)'\) \)\]\"", _override(chart, "bar_body"))
        self.assertEqual([int(k) for *_, k in layers], list(range(8, 0, -1)))
        colours = dict(_pie_colours())
        for *rgb, k in layers:
            hex_ = colours[f"pie_{SLICES[int(k) - 1][1]}"]
            want = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            with self.subTest(layer=k):
                for got, expected in zip(rgb, want):
                    self.assertAlmostEqual(float(got), expected, delta=0.002)


class HistoryTest(unittest.TestCase):
    TITLES = ["te_demog_hist_bd_title", "te_demog_hist_mig_title", "te_demog_hist_e0_title",
              "te_demog_hist_tfr_title", "te_demog_hist_median_title", "te_demog_hist_causes_title",
              "te_demog_hist_gini_title", "te_demog_hist_wc_title"]

    @classmethod
    def setUpClass(cls):
        cls.widgets = _read(WIDGETS)
        cls.history = _type_body(cls.widgets, "te_demog_sec_history")
        cls.charts = _instances(cls.history, "te_history_chart")

    def test_the_eight_charts(self):
        titles = [re.search(r'text = "(\w+)"', _override(c, "chart_title")).group(1) for c in self.charts]
        self.assertEqual(titles, self.TITLES)

    def test_every_chart_draws_the_pips(self):
        for chart in self.charts:
            self.assertEqual(_override(chart, "marker_pips").strip(), "te_demog_hist_pips = {}")
        self.assertEqual(len(_instances(self.history, "te_demog_hist_pip_legend")), 1, "one key under the charts")

    def test_the_pips_have_a_lane_above_the_bars(self):
        """Each frame is 132 tall with its plots (and the zero axis) in a 96 px box at its foot, as te_history_chart's
        96 px frame holds them; the pips sit in the 36 px over them, never on a bar (owner, 2026-10-22)."""
        lane = re.compile(r"^### [^\n]*\n\s*widget = \{\s*size = \{ 100% 96 \}\s*parentanchor = bottom")
        for chart in self.charts:
            self.assertIn("size = { 456 132 }", _override(chart, "plot_size"))
            self.assertRegex(_override(chart, "plot_layouts").strip(), lane)
            if _override(chart, "zero_axis") is not None:
                self.assertRegex(_override(chart, "zero_axis").strip(), lane)
        pips = re.findall(r"position = \{ 0 (-?\d+) \}\s*alwaystransparent = yes\s*size = \{ (\d+) \d+ \}",
                          _type_body(self.widgets, "te_demog_hist_pips"))
        self.assertEqual(len(pips), 3)
        column_top = 36 + 6     # the lane, then the 96 px box's margin above its 84 px bars
        for y, size in pips:
            top = column_top + int(y)
            self.assertGreaterEqual(top, 0, "inside the frame")
            self.assertLessEqual(top + int(size), column_top - 2, "clear of the bars")

    def test_every_sample_variable_read_is_recorded(self):
        recorded = set(re.findall(r"name = (te_dg_h_\w+)", _read(HISTORY)))
        recorded |= set(re.findall(r"TO = (te_dg_h_\w+)", _read(HISTORY)))
        recorded |= {f"te_dg_h_s{k}" for k in range(1, 9)} if "name = te_dg_h_s$K$" in _read(HISTORY) else set()
        reads = set()
        loc = "\n".join(_read(os.path.join(LOC_DIR, n)) for n in os.listdir(LOC_DIR) if n.endswith(".yml"))
        for text in (self.widgets, loc):
            reads |= set(re.findall(r"(?:GetVariableValue|HasVariable)\(\s*'(te_dg_h_\w+)'", text))
        self.assertGreaterEqual(len(reads), 20)
        self.assertEqual(reads - recorded, set(), "read but never recorded")

    def test_the_markers_are_noted(self):
        history = _read(HISTORY)
        for marker in ("te_dg_h_mk_war", "te_dg_h_mk_famine", "te_dg_h_mk_event"):
            self.assertIn(f"name = {marker} value = 1", history)
        self.assertIn("te_demog_history_note_famine = yes", _read(os.path.join(
            REPO, "common", "on_actions", "te_demog_on_actions.txt")))
        wave = _read(os.path.join(REPO, "common", "scripted_effects", "te_demog_wave_effects.txt"))
        self.assertIn("te_demog_history_note_event = yes", wave)

    def test_a_famine_after_the_pulse_marks_the_stored_sample(self):
        """The yearly country pulse falls on each country's own day, so a famine month after it in the calendar year
        marks this year's sample at once, as the event marker does (2026-10-20)."""
        history = _read(HISTORY)
        for name, marker in (("te_demog_history_note_famine", "te_dg_h_mk_famine"),
                             ("te_demog_history_note_event", "te_dg_h_mk_event")):
            body = history.split(f"{name} = {{", 1)[1].split("\n}", 1)[0]
            self.assertIn("variable = te_dg_hist", body, name)
            self.assertIn("limit = { var:te_hist_i = te_demog_year }", body, name)
            self.assertIn(f"set_variable = {{ name = {marker} value = 1 }}", body, name)


class StatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.widgets = _read(WIDGETS)

    def test_a_row_opens_the_state_on_its_demographics_subtab(self):
        row = _type_body(self.widgets, "te_demog_state_row")
        clicks = re.findall(r'(?m)^\t\tonclick = "(.*)"', row)
        self.assertEqual(clicks, ["[InformationPanelBar.OpenStatePanel( State.AccessSelf )]",
                                  "[GetVariableSystem.Set('population_subtab', 'te_demog')]"])
        self.assertIn("GetVariableSystem.HasValue('population_subtab', 'te_demog')", _read(STATES))
        self.assertIn("HighlightState", row)
        self.assertIn("RightClickMenuManager.ShowForState", row)

    def test_ten_rows_then_show_all(self):
        body = _type_body(self.widgets, "te_demog_sec_states")
        self.assertEqual(re.findall(r"datamodel = \"\[Country\.MakeScope\.GetList\('(\w+)'\)\]\"", body),
                         ["te_dg_states_top", "te_dg_states"])
        effects = _read(EFFECTS)
        lists = _block_from(effects, effects.index("te_demog_country_lists = {"))
        top = lists[lists.index("te_dg_states_top"):]
        self.assertRegex(top, r"order_by = te_demog_census_people\s*max = 10\b")
        self.assertIn("add_to_variable_list = { name = te_dg_states_top", top)
        self.assertIn("name = te_dg_states_n", lists)
        sguis = _sgui_names()
        for gate in ("te_demog_states_more_sgui", "te_demog_states_over_sgui"):
            self.assertIn(gate, sguis)
            self.assertIn(gate, body)

    def test_the_civil_war_repair_redraws_the_lists(self):
        self.assertIn("te_demog_country_lists = yes", _read(os.path.join(
            REPO, "common", "scripted_effects", "te_inheritance_effects.txt")))

    def test_every_state_a_list_names_opens_it(self):
        """2026-10-27 audit, DEM-6 and DEM-8: the largest cities, the Youth row's states and the Metropolises are rows
        that open the state on its Demographics subtab, with the States table's onclicks, highlight and menu."""
        row = _type_body(self.widgets, "te_demog_state_row")
        link = _type_body(self.widgets, "te_demog_state_link_row")
        for line in re.findall(r"(?m)^\t\t(on\w+ = \".*\")$", row):
            self.assertIn(line, link)
        self.assertRegex(self.widgets, r"type te_demog_city_row = te_demog_state_link_row \{")
        for section, name in (("te_demog_sec_work", "te_dg_yb_states"), ("te_demog_sec_places", "te_dg_mt_states")):
            with self.subTest(section=section):
                body = _type_body(self.widgets, section)
                at = body.index(f"datamodel = \"[Country.MakeScope.GetList('{name}')]\"")
                item = _block_from(body, body.index("item = {", at))
                self.assertIn("te_demog_state_link_row = {", item)
                self.assertIn('datacontext = "[Scope.GetState]"', item)

    def test_the_youth_and_metropolis_lists_are_built_with_the_census(self):
        effects = _read(EFFECTS)
        lists = _block_from(effects, effects.index("te_demog_country_lists = {"))
        for name, order, test in (("te_dg_yb_states", "te_demog_youth_bulge_shown", "te_demog_youth_bulge_shown > 0"),
                                  ("te_dg_mt_states", "te_demog_mt_share", "var:te_dg_mt >= te_demog_k_mt_metropolis")):
            with self.subTest(list=name):
                at = lists.index(f"clear_variable_list = {name}")
                block = _block_from(lists, lists.index("ordered_scope_state = {", at))
                self.assertIn(test, block)
                self.assertRegex(block, rf"order_by = {order}\s*max = 10\b")
                self.assertIn(f"add_to_variable_list = {{ name = {name} target = scope:te_dg_it }}", block)
        # the Youth row's count and its list read the same test
        conseq = _read(os.path.join(REPO, "common", "scripted_effects", "te_demog_consequence_effects.txt"))
        country = _block_from(conseq, conseq.index("te_demog_consequences_country = {"))
        self.assertIn("te_demog_youth_bulge_shown > 0", country)


class StateWealthTermsTest(unittest.TestCase):
    """Issue #894: the state's Wealth section shows its target term by term, as the country tab does. The rows read
    te_demog_wc_target's own addends (the state's from State, the owner's through State.GetOwner), so a term added to
    the target without a row fails here."""

    @classmethod
    def setUpClass(cls):
        cls.section = _type_body(_read(WIDGETS), "te_state_demog_wealth")
        cls.rows = _instances(cls.section, "te_demog_term_row")
        values = _read(os.path.join(REPO, "common", "script_values", "te_demog_values.txt"))
        target = _block_from(values, values.index("te_demog_wc_target = {"))
        cls.addends = re.findall(r"(?m)^\t(?:value|add) = (owner\.)?(\w+)$", target)

    def _reads(self, row):
        return set(re.findall(r"(State(?:\.GetOwner)?)\.MakeScope\.ScriptValue\('(\w+)'\)", row))

    def test_one_row_for_each_of_the_targets_terms(self):
        # the law term is the owner's law target less 50 (te_demog_wc_law_term), so the nine add up to the target less
        # 50 (r > g since 2026-10-19; public goods and slavery since 2026-10-21)
        want = {("State.GetOwner" if owner else "State",
                 "te_demog_wc_law_term" if name == "te_inh_law_amendment_target" else name)
                for owner, name in self.addends}
        self.assertEqual(len(want), 9)
        got = [self._reads(row) for row in self.rows]
        self.assertTrue(all(len(reads) == 1 for reads in got), got)
        self.assertEqual({next(iter(reads)) for reads in got}, want)
        self.assertEqual(len(got), 9)

    def test_never_the_players_figures(self):
        # nor the context's Country: the state's owner's terms read State.GetOwner.MakeScope
        for row in self.rows:
            self.assertNotIn("GetPlayer", row)
            self.assertNotRegex(row, r"(?<![\w.])Country\.")
        self.assertNotIn("GetPlayer", self.section)
        self.assertNotRegex(self.section, r"(?<![\w.])Country\.")

    def test_the_rows_sit_under_the_scored_gate(self):
        gate = "GetScriptedGui('te_demog_state_wealth_sgui').IsShown( GuiScope.SetRoot( State.MakeScope ).End )"
        container = next(block for block in _instances(self.section, "flowcontainer")
                         if f'visible = "[{gate}]"' in block)
        for row in self.rows:
            self.assertIn(row, container)
        self.assertIn("te_demog_wc_terms_head", container)
        self.assertIn("te_demog_st_wc_pinned_note", container)

    def test_the_state_keys_exist_and_read_the_state(self):
        loc = _loc()
        self.assertIn("te_dg_agr_share", loc["te_demog_st_wc_t_land_tt"])
        self.assertNotIn("Averaged over the states", loc["te_demog_st_wc_t_land_tt"])
        self.assertIn("te_demog_st_wc_pinned_note", loc)


if __name__ == "__main__":
    unittest.main()
