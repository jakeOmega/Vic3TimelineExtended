"""The Solar System tab's map and the Colonies window (the owner, 2026-11-23:
"clicking on a base should open the base in a new window" and "some kind of
schematic view of the solar system").

Three files have to agree, and nothing in the game says when they don't: the
map's backdrop is drawn for one layout (gen_space_map_art.py), the widget is
sized for it (space_race_widget.gui) and the generator places each site's
marker in it (gen_solar_sites.py). The window is filled from the list row's
own blocks, so a block one of the two types lacks must not be passed to it,
and every click that opens the window has to set both of its keys.
"""
import os
import re
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
sys.path.insert(0, os.path.join(REPO, "scripts", "image_pipeline"))

import gen_solar_sites as gss  # noqa: E402
import gen_space_map_art as art  # noqa: E402

GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
ROWS = os.path.join(REPO, "gui", "journal_entry_widgets", "sr_sites_generated_rows.gui")
POPUPS = os.path.join(REPO, "gui", "te_popups.gui")
LOC = os.path.join(REPO, "localization", "english", "te_journal_entries_l_english.yml")
ICONS = "gfx/interface/icons/space_race_icons/"
OPEN = ("onclick = \"[GetVariableSystem.Set('sr_colony_focus', '{k}')]\"",
        "onclick = \"[GetVariableSystem.Set('te_popup', 'sr_colony')]\"")
CONTESTED = ("EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_colonies_contested'), "
             "'(CFixedPoint)1' )")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unbalanced braces")


def _type_body(text, name):
    m = re.search(rf"\n\ttype {name} = \w+ \{{", text)
    assert m, name
    return text[m.end():_close(text, m.end() - 1)]


def _instances(body, name):
    out = []
    for m in re.finditer(rf"\n\t\t{name} = \{{", body):
        out.append(body[m.end():_close(body, m.end() - 1)])
    return out


def _site_value(block, key):
    return f"JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_site_{key}')" in block


class MapLayoutTest(unittest.TestCase):
    """The backdrop, the widget and the markers' places are one layout."""

    @classmethod
    def setUpClass(cls):
        cls.gui, cls.rows = _read(GUI), _read(ROWS)
        cls.map = _type_body(cls.gui, "te_sr_system_map")
        cls.column = _type_body(cls.gui, "te_sr_map_location")
        cls.columns = _instances(_type_body(cls.rows, "te_sr_map_locations"), "te_sr_map_location")

    def test_the_backdrop_is_drawn_for_the_widget(self):
        self.assertEqual(self.map.count(f"size = {{ {art.MAP_W} {art.MAP_H} }}"), 2)   # the map and its backdrop
        self.assertIn(f'texture = "{ICONS}map_backdrop.dds"', self.map)
        # The columns start where the backdrop's first orbit column does, and are as wide.
        self.assertRegex(self.map, rf"te_sr_map_locations = \{{\s*position = \{{ {art.COLUMN_X0} \d+ \}}")
        width = int(re.search(r"size = \{ (\d+) \d+ \}", self.column).group(1))
        self.assertEqual((width, len(self.columns)), (art.COLUMN_W, art.COLUMNS))
        self.assertEqual(width, gss.MAP_COLUMN)
        self.assertLessEqual(art.COLUMN_X0 + art.COLUMNS * art.COLUMN_W, art.MAP_W)
        # An orbit passes through its column's icon: the icon's box is centred on the icons' line.
        icon = re.search(r"icon = \{\s*size = \{ (\d+) (\d+) \}\s*position = \{ (\d+) (\d+) \}\s*block \"loc_icon\"", self.column)
        w, h, x, y = (int(n) for n in icon.groups())
        self.assertEqual(x + w / 2, art.COLUMN_W / 2)
        top = int(re.search(r"te_sr_map_locations = \{\s*position = \{ \d+ (\d+) \}", self.map).group(1))
        self.assertEqual(top + y + h / 2, art.ROW_Y + 2)   # within two units of the line: the frame's own inset
        self.assertEqual(art.BELTS, (gss.LOCATIONS.index("asteroids"), gss.LOCATIONS.index("kuiper")))

    def test_a_column_per_location_in_order(self):
        self.assertEqual(len(self.columns), len(gss.LOCATIONS))
        # The fleets' strip draws the same worlds, but the Earth where the map draws the Moon.
        self.assertEqual({k for k in gss.LOCATIONS if gss.MAP_ICONS[k] != gss.LOCATION_ICONS[k]}, {"earth"})
        self.assertTrue(gss.MAP_ICONS["earth"].endswith("colony_moon.dds"))
        for loc, column in zip(gss.LOCATIONS, self.columns):
            with self.subTest(location=loc):
                self.assertIn(f'texture = "{gss.MAP_ICONS[loc]}"', column)
                self.assertIn(f'text = "je_space_race_widget_map_loc_{loc}"', column)
                picked = f"GetVariableSystem.HasValue('sr_ss_loc', '{loc}')"
                self.assertIn(f"onclick = \"[GetVariableSystem.Set('sr_ss_loc', '{loc}')]\"", column)
                self.assertIn(f'visible = "[Not( {picked} )]"', column)        # the button that picks it
                self.assertIn("onclick = \"[GetVariableSystem.Clear('sr_ss_loc')]\"", column)
                self.assertEqual(column.count(f'tooltip = "je_space_race_widget_map_loc_tt_{loc}"'), 2)

    def test_neighbouring_names_never_share_a_line(self):
        """A name is wider than its column (the type's comment), so the two lines
        alternate; each name's text, centred on its column, stays inside the
        map (at test_space_race_labels' budget for the overview's 16)."""
        loc = _read(LOC)
        lines = []
        for i, (key, column) in enumerate(zip(gss.LOCATIONS, self.columns)):
            m = re.search(r'blockoverride "loc_name" \{\s*position = \{ (-?\d+) (\d+) \}', column)
            x, y = int(m.group(1)), int(m.group(2))
            lines.append(y)
            self.assertEqual(x + gss.MAP_NAME_WIDTH / 2, art.COLUMN_W / 2)   # centred on the column
            name = re.search(rf'(?m)^ je_space_race_widget_map_loc_{key}:0 "(.*)"$', loc).group(1)
            need = len(name) * 8.6 * 1.1
            centre = art.COLUMN_X0 + i * art.COLUMN_W + art.COLUMN_W / 2
            with self.subTest(location=key):
                self.assertLessEqual(need, gss.MAP_NAME_WIDTH)
                self.assertGreaterEqual(centre - need / 2, 0)
                self.assertLessEqual(centre + need / 2, art.MAP_W + 2)
        self.assertTrue(all(a != b for a, b in zip(lines, lines[1:])))
        box = re.search(r'textbox = \{\s*size = \{ (\d+) (\d+) \}[^{}]*block "loc_name"', self.column)
        self.assertEqual(int(box.group(1)), gss.MAP_NAME_WIDTH)
        # Two columns hold a name's width, so same-line names (two columns apart) can't meet.
        self.assertLessEqual(gss.MAP_NAME_WIDTH, 2 * art.COLUMN_W)
        self.assertLess(max(lines) + int(box.group(2)), gss.MAP_PIPS_TOP + 1)

    def test_every_site_has_one_marker_in_its_own_column(self):
        height = int(re.search(r"size = \{ \d+ (\d+) \}", self.column).group(1))
        seen = []
        for loc, column in zip(gss.LOCATIONS, self.columns):
            sites = [s for s in gss.SITES if s.location == loc]
            pips = [column[m.end():_close(column, m.end() - 1)] for m in re.finditer(r"te_sr_map_pip = \{", column)]
            self.assertEqual(len(pips), len(sites), loc)
            places = set()
            for i, (site, pip) in enumerate(zip(sites, pips)):
                k = site.key
                with self.subTest(site=k):
                    seen.append(k)
                    self.assertTrue(_site_value(pip, k))
                    x, y = (int(n) for n in re.search(r"position = \{ (\d+) (\d+) \}", pip).groups())
                    self.assertEqual((x, y), gss.map_pip_position(i, len(sites)))
                    self.assertTrue(0 <= x and x + gss.MAP_PIP <= gss.MAP_COLUMN and y + gss.MAP_PIP <= height)
                    places.add((x, y))
                    # Its seven states, each a marker of its own; the flag reads the holder's capital.
                    for block, code in (("unclaimed", 0), ("ours", 1), ("other", 2), ("unknown", 3), ("free", 4),
                                        ("occupied", 5), ("ruined", 6)):
                        self.assertRegex(pip, rf'blockoverride "pip_{block}_visible" \{{\s*visible = "\[EqualTo_CFixedPoint\( '
                                              rf"JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('sr_disp_site_{k}'\), "
                                              rf"'\(CFixedPoint\){code}' \)\]\"")
                    self.assertIn(f"Var('sr_ss_cap_{k}').GetState", pip)
                    self.assertIn(f"ScriptValue('sr_disp_site_target_{k}'), '(CFixedPoint)2' )", pip)
                    self.assertIn(f"ScriptValue('sr_disp_site_inbound_{k}'), '(CFixedPoint)1' )", pip)
                    # Ours opens the window; any other lists its location. One of the two shows.
                    ours = (f"And( {CONTESTED}, EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope."
                            f"ScriptValue('sr_disp_site_{k}'), '(CFixedPoint)1' ) )")
                    opened = pip[pip.index('blockoverride "pip_open"'):pip.index('blockoverride "pip_select"')]
                    selected = pip[pip.index('blockoverride "pip_select"'):]
                    self.assertIn(f'visible = "[{ours}]"', opened)
                    for line in OPEN:
                        self.assertIn(line.format(k=k), opened)
                    self.assertIn(f'visible = "[Not( {ours} )]"', selected)
                    self.assertIn(f"onclick = \"[GetVariableSystem.Set('sr_ss_loc', '{loc}')]\"", selected)
                    self.assertEqual(pip.count(f'tooltip = "je_space_race_widget_ss_site_tt_{k}"'), 2)
            self.assertEqual(len(places), len(sites), f"two markers share a place at {loc}")
        self.assertEqual(sorted(seen), sorted(s.key for s in gss.SITES))

    def test_the_marker_draws_each_state_once(self):
        pip = _type_body(self.gui, "te_sr_map_pip")
        self.assertEqual(sorted(re.findall(rf'texture = "{re.escape(ICONS)}(\w+)\.dds"', pip)),
                         sorted(["map_target", "map_pip_unclaimed", "map_pip_ours", "map_pip_other", "map_pip_free",
                                 "map_pip_occupied", "map_pip_ruined", "track_ship"]))
        # The flag is drawn, not vanilla's flag button: the click must stay the marker's.
        self.assertNotIn("tiny_flag", pip)
        self.assertIn('texture = "[Country.GetFlag.GetSmallFlagTexture]"', pip)

    def test_the_list_follows_the_map(self):
        """A location picked on the map lists its sites alone, every one; with
        none picked the list is the usual one. The colony target popup's list
        does not read the map."""
        system = _type_body(self.rows, "te_sr_solar_system_rows")
        rows = _instances(system, "te_sr_site_row")
        self.assertEqual(len(rows), len(gss.SITES))
        by_key = {re.search(r'text = "sr_site_name_(\w+)"', row).group(1): row for row in rows}
        for site in gss.SITES:
            with self.subTest(site=site.key):
                usual = (f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                         f"'sr_disp_ss_shown_{site.key}'), '(CFixedPoint)1' )")
                self.assertIn(f"visible = \"[Or( GetVariableSystem.HasValue('sr_ss_loc', '{site.location}'), And( Not( "
                              f"GetVariableSystem.Exists('sr_ss_loc') ), Or( GetVariableSystem.Exists("
                              f"'sr_panel_solar_system_all_open'), {usual} ) ) )]\"", by_key[site.key])
        self.assertEqual(system.count("GetVariableSystem.HasValue('sr_ss_loc', "), len(gss.SITES) + len(gss.LOCATIONS))
        self.assertNotIn("sr_ss_loc", _type_body(self.rows, "te_sr_target_picker_rows"))
        section = _type_body(self.gui, "te_sr_sec_solar_system")
        self.assertLess(section.index("te_sr_system_map = {}"), section.index("te_sr_solar_system_rows = {}"))
        self.assertIn("onclick = \"[GetVariableSystem.Clear('sr_ss_loc')]\"", section)

    def test_the_art_is_tracked(self):
        tracked = set(subprocess.run(["git", "-C", REPO, "ls-files", ICONS], capture_output=True, text=True,
                                     check=True).stdout.split())
        for stem in art.STEMS:
            with self.subTest(file=stem):
                self.assertIn(f"{ICONS}{stem}.dds", tracked)

    @unittest.skipIf(art.Image is None, "Pillow is not installed (CI)")
    def test_the_art_is_as_the_script_draws_it(self):
        if not os.path.exists(os.path.join(REPO, ICONS, "map_backdrop.dds")):
            self.skipTest("this checkout has no gfx/ (CI's main job, a sparse worktree)")
        check = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "image_pipeline", "gen_space_map_art.py"),
                                "--check"], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    @unittest.skipIf(art.Image is None, "Pillow is not installed (CI)")
    def test_the_art_is_drawn_at_its_sizes(self):
        self.assertEqual(art.render("map_backdrop").size, (2 * art.MAP_W, 2 * art.MAP_H))
        for stem in art.MARKERS:
            with self.subTest(file=stem):
                self.assertEqual(art.render(stem).size, (art.SIZE, art.SIZE))
        self.assertEqual(art.dds_bytes("map_target"), art.dds_bytes("map_target"))


class ColoniesWindowTest(unittest.TestCase):
    """A colony opens in a window of its own, with our other colonies beside it."""

    @classmethod
    def setUpClass(cls):
        cls.gui, cls.rows = _read(GUI), _read(ROWS)
        cls.row, cls.page = _type_body(cls.gui, "te_sr_colony_row"), _type_body(cls.gui, "te_sr_colony_page")

    def test_no_page_is_left_in_the_list(self):
        for text in (self.gui, self.rows):
            self.assertNotIn("'detail'", text)
        self.assertNotIn("te_sr_page_tile", self.row)
        self.assertNotIn("je_space_race_widget_cv_back", self.gui + _read(LOC))
        # Races Only has nothing to manage: the name is plain text and the arrow is hidden.
        name = self.row[self.row.index("using = clean_button") - 200:self.row.index("using = clean_button")]
        self.assertIn(f'button = {{\n\t\t\t\tvisible = "[{CONTESTED}]"', name)
        self.assertRegex(self.row, rf'button_icon_goto = \{{\s*visible = "\[{re.escape(CONTESTED)}\]"')
        self.assertIn(f'visible = "[Not( {CONTESTED} )]"', self.row)

    def test_the_window_is_in_the_popups_root(self):
        popup = _type_body(self.gui, "te_sr_colony_popup")
        self.assertIn("visible = \"[GetVariableSystem.HasValue('te_popup', 'sr_colony')]\"", popup)
        self.assertIn("te_sr_colony_popup_body = {}", popup)
        # The names' hovers read Country, as in the journal entry: the gate's block gives the player's.
        self.assertIn('datacontext = "[GetPlayer]"', popup)
        self.assertEqual(_read(POPUPS).count("\tte_sr_colony_popup = {}"), 1)
        body = _type_body(self.gui, "te_sr_colony_popup_body")
        self.assertLess(body.index("te_sr_colony_switch_rows = {}"), body.index("te_sr_colony_pages = {}"))
        # The content fits the window: its width, the window's margins, the list's and a scrollbar.
        widths = [int(w) for w in re.findall(r"minimumsize = \{ (\d+) -1 \}", body)]
        spacing = int(re.search(r"spacing = (\d+)", body).group(1))
        window = int(re.search(r'blockoverride "popup_size" \{\s*size = \{ (\d+) \d+ \}', popup).group(1))
        self.assertLessEqual(sum(widths) + spacing + 2 * 35 + 2 * 10 + 16, window)
        # Nothing the body draws reads Country, so it can be shown alone under the entry's context.
        self.assertNotIn("je_space_race_widget_colonies_held_figure", body)

    def test_every_colony_has_a_page_a_list_row_and_a_way_in(self):
        pages = _instances(_type_body(self.rows, "te_sr_colony_pages"), "te_sr_colony_page")
        switches = _instances(_type_body(self.rows, "te_sr_colony_switch_rows"), "te_sr_colony_switch_row")
        listed = _instances(_type_body(self.rows, "te_sr_colony_rows"), "te_sr_colony_row")
        gone = _instances(_type_body(self.rows, "te_sr_colony_pages"), "te_sr_note")
        order = [s.key for s in gss.panel_order()]
        self.assertEqual([len(pages), len(switches), len(listed), len(gone)], [len(order)] * 4)
        system = _instances(_type_body(self.rows, "te_sr_solar_system_rows"), "te_sr_site_row")
        system = {re.search(r'text = "sr_site_name_(\w+)"', row).group(1): row for row in system}
        for k, page, switch, row, note in zip(order, pages, switches, listed, gone):
            with self.subTest(site=k):
                focus = f"GetVariableSystem.HasValue('sr_colony_focus', '{k}')"
                ours = (f"Or( EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('sr_disp_def_{k}'), "
                        f"'(CFixedPoint)1' ), EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                        f"'sr_disp_site_{k}'), '(CFixedPoint)1' ) )")
                self.assertIn(f'visible = "[And( {focus}, {ours} )]"', page)
                self.assertIn(f'visible = "[And( {focus}, Not( {ours} ) )]"', note)
                self.assertIn(f'visible = "[{ours}]"', switch)
                self.assertIn(f'enabled = "[Not( {focus} )]"', switch)
                self.assertIn(f"onclick = \"[GetVariableSystem.Set('sr_colony_focus', '{k}')]\"", switch)
                self.assertNotIn("te_popup", switch)   # the window is open already
                self.assertIn(f'text = "sr_site_name_{k}"', page)
                # The ways in: the list's name and arrow (one block, used twice), and Solar System's arrow.
                for opener, block in ((row, "colony_focus"), (system[k], "site_open")):
                    start = opener.index(f'blockoverride "{block}" {{')
                    override = opener[start:_close(opener, opener.index("{", start)) + 1]
                    for line in OPEN:
                        self.assertIn(line.format(k=k), override)
        picker = _type_body(self.rows, "te_sr_target_picker_rows")
        self.assertNotIn('blockoverride "site_open"', picker)   # a popup does not open another
        site_row = _type_body(self.gui, "te_sr_site_row")
        self.assertRegex(site_row, r'block "site_open" \{\s*visible = no\s*\}')

    def test_each_instance_gets_only_its_type_s_blocks(self):
        """The page and the row are filled from one list of blocks (_colony_blocks);
        each instance leaves out what its type lacks, and lacks nothing it has."""
        declared = {"row": set(re.findall(r'block "(\w+)"', self.row)), "page": set(re.findall(r'block "(\w+)"', self.page))}
        passed = {"row": _instances(_type_body(self.rows, "te_sr_colony_rows"), "te_sr_colony_row"),
                  "page": _instances(_type_body(self.rows, "te_sr_colony_pages"), "te_sr_colony_page")}
        for kind in ("row", "page"):
            for site, instance in zip(gss.panel_order(), passed[kind]):
                with self.subTest(kind=kind, site=site.key):
                    names = set(re.findall(r'\n\t\t\tblockoverride "(\w+)" \{', "\n" + instance))
                    self.assertEqual(names - declared[kind], set())
        everything = set()
        for site in gss.SITES:
            everything |= set(re.findall(r'\tblockoverride "(\w+)" \{', "\n".join(gss._colony_blocks(site))))
        self.assertEqual({b for b in everything if gss._PAGE_ONLY.fullmatch(b)}, (everything & declared["page"]) - declared["row"])
        self.assertEqual({b for b in everything if gss._ROW_ONLY.fullmatch(b)}, (everything & declared["row"]) - declared["page"])

    def test_a_site_s_name_fits_the_window_s_list(self):
        switch = _type_body(self.gui, "te_sr_colony_switch_row")
        start = switch.rindex("textbox = {", 0, switch.index('block "switch_name"'))
        box = switch[start:_close(switch, switch.index("{", start))]
        width = int(re.search(r"max_width = (\d+)", box).group(1))
        self.assertIn("using = te_sr_fontsize_row", box)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertLessEqual(len(site.name) * 8.5 * 1.1, width)   # test_space_race_labels' budget at 17


if __name__ == "__main__":
    unittest.main()
