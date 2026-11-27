"""The Fleets window (the owner, 2026-11-25: "space fleets [should] have their
own 'details' type popout window, like bases/colonies have now").

A fleet's page, with every fleet we have a click away beside it, opened by the
arrow at the head of a fleet's card in Space Fleets. Nothing in the game says
when its pieces disagree, so they are held here:

- The window is up on a key of its own (sr_fleet_focus), not on te_popup, so
  the four pickers a page's orders open on te_popup (destination, target,
  Transfer, Marines) draw over it and come back to it. That only works while
  the window is instanced before them, the root is up for either key, the
  pickers never touch the window's key and the window's own close buttons are
  down while a picker is up (two visible buttons would share Escape).
- A page is filled from its card's own blocks, so a block one of the two
  types lacks must not be passed to it, and an order's button must be the
  card's, letter for letter.
- The page's fire is the combat step's own arithmetic, or the tile says
  something the battle doesn't do.
"""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_space_fleets as gsf  # noqa: E402

GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
ROWS = os.path.join(REPO, "gui", "journal_entry_widgets", "sr_fleets_generated_rows.gui")
POPUPS = os.path.join(REPO, "gui", "te_popups.gui")
LOC = os.path.join(REPO, "localization", "english", "te_journal_entries_l_english.yml")
DISPLAY = os.path.join(REPO, "common", "script_values", "sr_fleets_display_generated.txt")
COMBAT = os.path.join(REPO, "common", "scripted_effects", "sr_fleet_combat_effects.txt")
ICONS = "gfx/interface/icons/space_race_icons/"
SLOTS = range(1, gsf.SLOTS + 1)
PICKERS = ("te_sr_dest_popup", "te_sr_ftarget_popup", "te_sr_xfer_popup", "te_sr_land_popup")
# The orders a page shares with its card: one override, used by both.
ORDERS = ("fl_pick_button", "fl_go_button", "fl_transfer_button", "fl_land_button", "fl_embark_button",
          "fl_posture_1_button", "fl_posture_2_button", "fl_posture_3_button", "fl_posture_4_button",
          "fl_target_button", "fl_destroy_button", "fl_orders_visible", "fl_combat_visible")


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


def _override(instance, block):
    """An instance's blockoverride of `block`, braces included."""
    start = instance.index(f'blockoverride "{block}" {{')
    return instance[start:_close(instance, instance.index("{", start)) + 1]


def _sv(name):
    return f"JournalEntry.GetCountry.MakeScope.ScriptValue('{name}')"


def _holds_a_fleet(n):
    return f"GreaterThanOrEqualTo_CFixedPoint( {_sv(f'sr_disp_fl_{n}')}, '(CFixedPoint)1' )"


class WindowTest(unittest.TestCase):
    """The window, its key and how it lives with the pickers."""

    @classmethod
    def setUpClass(cls):
        cls.gui, cls.rows, cls.popups = _read(GUI), _read(ROWS), _read(POPUPS)
        cls.popup = _type_body(cls.gui, "te_sr_fleet_popup")
        cls.body = _type_body(cls.gui, "te_sr_fleet_popup_body")

    def test_it_is_up_on_its_own_key(self):
        self.assertIn('blockoverride "popup_visible" {\n\t\t\tvisible = "[GetVariableSystem.Exists(\'sr_fleet_focus\')]"',
                      self.popup)
        self.assertEqual(gsf.FLEET_FOCUS, "sr_fleet_focus")
        self.assertIn('text = "je_space_race_widget_fw_title"', self.popup)
        self.assertIn("te_sr_fleet_popup_body = {}", self.popup)
        # With the entry gone, one line says so (as every Space Race popup).
        self.assertIn('text = "je_space_race_widget_tp_gone"', self.popup)

    def test_its_close_buttons_clear_its_key_and_stand_down_under_a_picker(self):
        close = _override(self.popup, "popup_close")
        self.assertEqual(re.findall(r'onclick = "(.*)"', close), ["[GetVariableSystem.Clear('sr_fleet_focus')]"])
        self.assertIn("visible = \"[Not( GetVariableSystem.Exists('te_popup') )]\"", close)
        # The shell puts the one block in both buttons (test_te_popups.py), so the
        # click outside and the header's button, with Escape, both follow it.
        shell = _type_body(_read(os.path.join(REPO, "gui", "te_widget_library.gui")), "te_ui_popup")
        self.assertEqual(shell.count('block "popup_close"'), 2)
        # Nothing in the window closes a picker's key, or any other popup.
        self.assertNotIn("Clear('te_popup')", self.popup + self.body + _type_body(self.gui, "te_sr_fleet_page"))

    def test_the_root_holds_it_under_the_pickers(self):
        root = self.popups[self.popups.index('name = "te_popups"'):]
        self.assertEqual(root.count("\tte_sr_fleet_popup = {}"), 1)
        at = root.index("\tte_sr_fleet_popup = {}")
        for picker in PICKERS:
            with self.subTest(picker=picker):
                self.assertLess(at, root.index(f"\t{picker} = {{}}"), "a later sibling draws over an earlier one")
        visible = re.search(r'\n\tvisible = "(.*)"', root).group(1)
        self.assertIn("Or( GetVariableSystem.Exists('te_popup'), GetVariableSystem.Exists('sr_fleet_focus') )", visible)
        self.assertIn("Not( GetMetaPlayer.IsObserver )", visible)

    def test_the_pickers_leave_the_window_alone(self):
        """A picker shows on te_popup alone and closes by clearing it, so closing
        one, or choosing in it, comes back to the window under it."""
        for picker in PICKERS:
            with self.subTest(picker=picker):
                self.assertNotIn("sr_fleet_focus", _type_body(self.gui, picker))
                self.assertNotIn("sr_fleet_focus", _type_body(self.rows, f"{picker}_body"))

    def test_the_content_fits_the_window(self):
        widths = [int(w) for w in re.findall(r"minimumsize = \{ (\d+) -1 \}", self.body)]
        self.assertEqual(widths, [244, 960])
        spacing = int(re.search(r"spacing = (\d+)", self.body).group(1))
        window = int(re.search(r'blockoverride "popup_size" \{\s*size = \{ (\d+) \d+ \}', self.popup).group(1))
        self.assertLessEqual(sum(widths) + spacing + 2 * 35 + 2 * 10 + 16, window)
        self.assertLess(self.body.index("te_sr_fleet_switch_rows = {}"), self.body.index("te_sr_fleet_pages = {}"))
        # What Space Fleets says once above its cards is said once above the page too (rule 6),
        # on the panel's own conditions: with a fleet, and no Space Command or too few personnel.
        some = f"GreaterThanOrEqualTo_CFixedPoint( {_sv('sr_disp_fl_count')}, '(CFixedPoint)1' )"
        notes = dict(re.findall(r'te_sr_fleet_wide_note = \{\s*visible = "\[(.*)\]"\s*text = "je_space_race_widget_(\w+)"', self.body))
        self.assertEqual({key: shown for shown, key in notes.items()}, {
            "space_fleets_empty": f"EqualTo_CFixedPoint( {_sv('sr_disp_fl_count')}, '(CFixedPoint)0' )",
            "space_fleets_no_sc": f"And( {some}, EqualTo_CFixedPoint( {_sv('sr_disp_sc_operational')}, '(CFixedPoint)0' ) )",
            "space_fleets_short": f"And( {some}, EqualTo_CFixedPoint( {_sv('sr_disp_pers_short')}, '(CFixedPoint)1' ) )"})
        section = _type_body(self.gui, "te_sr_sec_space_fleets")   # the panel's own, word for word
        for key in ("space_fleets_no_sc", "space_fleets_short"):
            self.assertIn(f'visible = "[{[s for s, k in notes.items() if k == key][0]}]"\n\t\t\t\ttext = "je_space_race_widget_{key}"', section)
        self.assertLess(self.body.index("space_fleets_short"), self.body.index("te_sr_fleet_pages = {}"))

    def test_the_window_opens_only_popups_drawn_over_it(self):
        """A popup instanced before the window in the root would draw under it,
        and the window's close buttons are hidden while te_popup exists: nothing
        would be in reach. So everything the window holds may set te_popup only
        to its own slot's four pickers, each instanced after the window."""
        root = self.popups[self.popups.index('name = "te_popups"'):]
        at = root.index("\tte_sr_fleet_popup = {}")
        kinds = {"dest": "te_sr_dest_popup", "ftarget": "te_sr_ftarget_popup", "xfer": "te_sr_xfer_popup", "land": "te_sr_land_popup"}
        held = (self.popup + self.body + _type_body(self.gui, "te_sr_fleet_page") + _type_body(self.gui, "te_sr_fleet_switch_row")
                + _type_body(self.rows, "te_sr_fleet_switch_rows"))
        self.assertEqual(re.findall(r"Set\(\s*'te_popup'", held), [])   # none written in the types themselves
        pages = _instances(_type_body(self.rows, "te_sr_fleet_pages"), "te_sr_fleet_page")
        for n, page in zip(SLOTS, pages):
            with self.subTest(slot=n):
                opened = set(re.findall(r"GetVariableSystem\.Set\('te_popup', '(\w+)'\)", page))
                self.assertEqual(opened, {f"sr_{kind}_{n}" for kind in kinds})
        for popup in kinds.values():
            self.assertLess(at, root.index(f"\t{popup} = {{}}"), popup)
        # ... and what the page borrows from the panel opens nothing: the Locations strip.
        self.assertNotIn("te_popup", _type_body(self.rows, "te_sr_location_cells") + _type_body(self.gui, "te_sr_location_cell"))

    def test_only_the_card_and_the_list_open_it(self):
        """The key is set by a card's arrow (the player's own panel) and by the
        window's list, and cleared by its close buttons: an opener anywhere else
        has to be put under the own-country guard, and listed here."""
        import glob
        setters = {}
        for path in sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)):
            for m in re.finditer(r"GetVariableSystem\.(Set|Clear|Toggle)\(\s*'sr_fleet_focus'", _read(path)):
                setters.setdefault(os.path.relpath(path, REPO), []).append(m.group(1))
        self.assertEqual(setters, {"gui/journal_entry_widgets/space_race_widget.gui": ["Clear"],
                                   "gui/journal_entry_widgets/sr_fleets_generated_rows.gui": ["Set"] * (2 * gsf.SLOTS)})


class SlotsTest(unittest.TestCase):
    """Every slot has a page, a line saying it is gone, a list row and a way in."""

    @classmethod
    def setUpClass(cls):
        cls.gui, cls.rows = _read(GUI), _read(ROWS)
        cls.card_type, cls.page_type = _type_body(cls.gui, "te_sr_fleet_row"), _type_body(cls.gui, "te_sr_fleet_page")
        cls.switch_type = _type_body(cls.gui, "te_sr_fleet_switch_row")
        cls.cards = _instances(_type_body(cls.rows, "te_sr_fleet_rows"), "te_sr_fleet_row")
        pages = _type_body(cls.rows, "te_sr_fleet_pages")
        cls.pages, cls.gone = _instances(pages, "te_sr_fleet_page"), _instances(pages, "te_sr_note")
        cls.switches = _instances(_type_body(cls.rows, "te_sr_fleet_switch_rows"), "te_sr_fleet_switch_row")

    def test_every_slot_has_a_page_a_list_row_and_a_way_in(self):
        self.assertEqual([len(self.cards), len(self.pages), len(self.gone), len(self.switches)], [gsf.SLOTS] * 4)
        for n, card, page, note, switch in zip(SLOTS, self.cards, self.pages, self.gone, self.switches):
            with self.subTest(slot=n):
                focus = f"GetVariableSystem.HasValue('sr_fleet_focus', '{n}')"
                show = f"onclick = \"[GetVariableSystem.Set('sr_fleet_focus', '{n}')]\""
                self.assertIn(f'blockoverride "fp_visible" {{\n\t\t\t\tvisible = "[And( {focus}, {_holds_a_fleet(n)} )]"', page)
                # ... while another fleet is left to choose; with none, the window says so itself.
                some = f"GreaterThanOrEqualTo_CFixedPoint( {_sv('sr_disp_fl_count')}, '(CFixedPoint)1' )"
                self.assertIn(f'visible = "[And3( {focus}, Not( {_holds_a_fleet(n)} ), {some} )]"', note)
                self.assertIn('text = "je_space_race_widget_fw_gone"', note)
                row = _override(switch, "switch_row")
                self.assertIn(f'visible = "[{_holds_a_fleet(n)}]"', row)
                self.assertIn(f'enabled = "[Not( {focus} )]"', row)
                self.assertIn(show, row)
                self.assertNotIn("te_popup", switch)   # the window is open already
                # The way in: the arrow at the head of the card sets the one key.
                self.assertEqual(_override(card, "fl_open").count("onclick"), 1)
                self.assertIn(show, _override(card, "fl_open"))
                self.assertIn(f'raw_text = "{gsf.NUMERALS[n - 1]}"', _override(page, "fp_number"))
                self.assertIn(f'raw_text = "{gsf.NUMERALS[n - 1]}"', _override(switch, "switch_number"))

    def test_the_card_s_arrow_is_vanilla_s_go_to(self):
        head = self.card_type[:self.card_type.index('block "fl_transit_visible"')]
        arrow = head[head.index("button_icon_goto = {"):]
        arrow = arrow[:_close(arrow, arrow.index("{")) + 1]
        self.assertIn('block "fl_open" {}', arrow)
        self.assertIn('tooltip = "je_space_race_widget_fl_open_tt"', arrow)
        # After the rolled-up wrapper, a full-size sibling: a later sibling takes the click.
        self.assertLess(head.index('block "fl_rolled_visible"'), head.index("button_icon_goto = {"))
        # The head's cells and gaps are the card's line.
        cells = [int(w) for w in re.findall(r"\n\t\t\twidget = \{\n\t\t\t\tsize = \{ (\d+) 30 \}", head)]
        self.assertEqual(cells, [30, 38, 24, 122, 94, 140])   # emblem, number, world, where, drive, the end's slot
        self.assertEqual(sum(cells) + 5 * 4, 468)

    def test_each_instance_gets_its_type_s_blocks_and_no_others(self):
        """The card and the page are filled from one list of blocks
        (_fleet_blocks); each takes what its type has, and leaves no block empty."""
        for kind, typ, instances in (("card", self.card_type, self.cards), ("page", self.page_type, self.pages),
                                     ("list row", self.switch_type, self.switches)):
            declared = set(re.findall(r'block "(\w+)"', typ))
            for n, instance in zip(SLOTS, instances):
                with self.subTest(kind=kind, slot=n):
                    passed = set(re.findall(r'\n\t\t\tblockoverride "(\w+)" \{', "\n" + instance))
                    self.assertEqual(passed, declared)
        shared = set(re.findall(r'\tblockoverride "(\w+)" \{', "\n".join(gsf._fleet_blocks(1))))
        card, page = set(re.findall(r'block "(\w+)"', self.card_type)), set(re.findall(r'block "(\w+)"', self.page_type))
        self.assertEqual(shared, card)
        self.assertEqual({b for b in shared if gsf._FLEET_ROW_ONLY.fullmatch(b)}, card - page)
        self.assertTrue(all(b.startswith("fp_") for b in page - card), page - card)

    def test_a_page_s_orders_are_its_card_s(self):
        """One override for both, so a page's button asks the same scripted GUI,
        greys on the same gate and opens the same picker as the card's."""
        for n, card, page in zip(SLOTS, self.cards, self.pages):
            for block in ORDERS:
                with self.subTest(slot=n, block=block):
                    self.assertEqual(_override(page, block), _override(card, block))
            # ... and each picker it opens is that slot's.
            for block, key in (("fl_pick_button", "dest"), ("fl_target_button", "ftarget"),
                               ("fl_transfer_button", "xfer"), ("fl_land_button", "land"), ("fl_embark_button", "land")):
                with self.subTest(slot=n, opens=key):
                    self.assertIn(f"GetVariableSystem.Set('te_popup', 'sr_{key}_{n}')", _override(page, block))

    def test_the_page_puts_the_card_s_hovers_in_the_open(self):
        for n, page in zip(SLOTS, self.pages):
            with self.subTest(slot=n):
                for role in gsf.ROLES:
                    now, full = _sv(f"sr_fl_{n}_{role.key}_value"), _sv(f"sr_fl_{n}_{role.key}_full_value")
                    self.assertIn(f'raw_text = "#v [{now}|0]#! / [{full}|0]"', _override(page, f"fp_role_{role.key}"))
                picked = f"GreaterThanOrEqualTo_CFixedPoint( {_sv(f'sr_disp_fl_{n}_pick')}, '(CFixedPoint)1' )"
                self.assertIn(f'visible = "[{picked}]"', _override(page, "fp_leg_visible"))
                # The leg's propellant is red while the fleet carries less: the destination popup's own comparison.
                covered = (f"GreaterThanOrEqualTo_CFixedPoint( {_sv(f'sr_fl_{n}_dv_value')}, "
                           f"{_sv(f'sr_disp_fl_{n}_leg_dv')} )")
                self.assertIn(f'visible = "[{covered}]"', _override(page, "fp_leg"))
                self.assertIn(f'text = "je_space_race_widget_fw_{n}_leg"', _override(page, "fp_leg"))
                self.assertIn(f'visible = "[Not( {covered} )]"', _override(page, "fp_leg_short"))
                self.assertIn(f'text = "je_space_race_widget_fw_{n}_leg_short"', _override(page, "fp_leg_short"))
                for code, word in enumerate(("none", "earth", "port", "flight")):
                    self.assertIn(f"EqualTo_CFixedPoint( {_sv(f'sr_disp_fl_{n}_dock')}, '(CFixedPoint){code}' )",
                                  _override(page, f"fp_dock_{word}"))
                self.assertIn(f'raw_text = "[{_sv(f"sr_disp_fl_{n}_repair_pct")}|0]%"', _override(page, "fp_repair"))
                self.assertIn(f"GetCustom('sr_fl_{n}_target_intel')", _override(page, "fp_intel"))
                for kind in ("fleets", "defences"):
                    self.assertIn(f'raw_text = "[{_sv(f"sr_disp_fl_{n}_fire_{kind}")}|1]"', _override(page, f"fp_fire_{kind}"))

    def test_the_page_opens_on_the_picture_of_its_fleet_s_drive(self):
        """The owner, 2026-11-25: "include the fleet banner image (the era
        specific one)". Space Fleets' four pictures, in its order, at the size
        they were painted (twice the panel's slot, the page column's width), the
        one shown the fleet's own drive's."""
        banner, panel = _type_body(self.gui, "te_sr_fleet_page_banner"), _type_body(self.gui, "te_sr_fleet_banner")
        pictures = re.findall(r'block "pb_(\w+)" \{\}\s*background = \{\s*texture = "([^"]+)"\s*fittype = centercrop', banner)
        self.assertEqual([path for _, path in pictures], re.findall(r'texture = "([^"]+)"', panel))
        self.assertEqual([drive for drive, _ in pictures], list(gsf.DRIVES))
        for (drive, path) in pictures:
            self.assertTrue(path.endswith(f"fleet_banner_{drive}.dds"), path)
        width, height = map(int, re.search(r"size = \{ (\d+) (\d+) \}", panel).groups())
        self.assertIn(f"size = {{ {2 * width} {2 * height} }}", banner)
        page = self.page_type
        self.assertEqual(page.count("te_sr_fleet_page_banner = {"), 1)
        head = re.search(r"\n\t\twidget = \{\n\t\t\tsize = \{ (\d+) 58 \}", page)
        self.assertEqual(int(head.group(1)), 2 * width)   # as wide as the page, so nothing is scaled
        self.assertLess(page.index("te_sr_fleet_page_banner = {"), head.start())
        for n, instance in zip(SLOTS, self.pages):
            for code, drive in enumerate(gsf.DRIVES):
                # the last drive's picture also covers any level a later drive adds, as the panel's does
                test = "GreaterThanOrEqualTo" if code == len(gsf.DRIVES) - 1 else "EqualTo"
                with self.subTest(slot=n, drive=drive):
                    self.assertIn(f'visible = "[{test}_CFixedPoint( {_sv(f"sr_fl_{n}_drive_value")}, \'(CFixedPoint){code}\' )]"',
                                  _override(instance, f"fp_banner_{drive}"))

    def test_the_page_s_lines_fit_its_columns(self):
        page = self.page_type
        tile = int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(self.gui, "te_sr_page_tile")).group(1))
        self.assertEqual(page.count("te_sr_page_tile = {"), 10)   # five roles and the drive; the two fires; dock and repair
        self.assertLessEqual(2 * tile + 6, 472)
        gauge = int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(self.gui, "te_sr_fl_gauge")).group(1))
        self.assertEqual(page.count("te_sr_fl_gauge = {"), 4)
        self.assertLessEqual(4 * gauge + 3 * 4, 472)
        caption = int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(self.gui, "te_sr_fp_caption")).group(1))
        # The four postures beside their caption, each narrower than the card's (pc_size).
        self.assertEqual(page.count("te_sr_posture_choice = {"), 4)
        postures = [int(w) for w in re.findall(r'blockoverride "pc_size" \{\s*size = \{ (\d+) 46 \}', page)]
        self.assertEqual(len(postures), 4)
        columns = [int(w) for w in re.findall(r"\n\t\t\t\tminimumsize = \{ (\d+) -1 \}", page)]
        self.assertEqual(columns, [472, 480])
        self.assertLessEqual(caption + 4 + sum(postures) + 3 * 4, columns[1])
        # The widest of the other orders lines: a caption, the target's button and Seize.
        buttons = [int(w) for w in re.findall(r"using = default_button_action\s*size = \{ (\d+) 26 \}", page)]
        self.assertEqual(sorted(buttons), [98, 190, 190])
        self.assertLessEqual(caption + 4 + max(buttons) + 4 + min(buttons), columns[1])
        # A caption a line, in the order a fleet is used: Engage or Avoid first, the
        # one order it takes in flight too (2026-11-25 design § 2.9); then where to,
        # how it fights, what at, its marines.
        captions = re.findall(r'te_sr_fp_caption = \{\s*blockoverride "caption_text" \{\s*text = "je_space_race_widget_(\w+)"', page)
        self.assertEqual(captions, ["fw_battle", "fw_destination", "fw_posture", "fw_target", "fl_col_marines"])
        # Locations, the panel's own strip, in the right column: its captions' column and a column a location.
        self.assertEqual(page.count("te_sr_location_cells = {}"), 1)
        cell = int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(self.gui, "te_sr_location_cell")).group(1))
        captions = int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(self.gui, "te_sr_location_captions")).group(1))
        self.assertLessEqual(captions + len(gsf.LOCATIONS) * cell, columns[1])
        # The two columns and their gap are the head's width, which is the window's page column.
        head = int(re.search(r"\n\t\twidget = \{\n\t\t\tsize = \{ (\d+) 58 \}", page).group(1))
        gap = int(re.search(r"direction = horizontal\n\t\t\tignoreinvisible = yes\n\t\t\tspacing = (\d+)\n\n\t\t\t### Left", page).group(1))
        self.assertEqual(sum(columns) + gap, head)
        self.assertIn(f"minimumsize = {{ {head} -1 }}", _type_body(self.gui, "te_sr_fleet_popup_body"))

    def test_each_tile_wears_an_icon_of_the_set(self):
        pairs = re.findall(r'blockoverride "tile_icon" \{\s*texture = "' + re.escape(ICONS) + r'(\w+)\.dds"\s*\}\s*'
                           r'blockoverride "tile_caption" \{\s*text = "je_space_race_widget_fw_(\w+)"', self.page_type)
        self.assertEqual(pairs, [("role_war", "role_war"), ("role_rapid", "role_rapid"), ("role_siege", "role_siege"),
                                 ("role_carrier", "role_carrier"), ("role_tender", "role_tender"), ("track_ship", "drive"),
                                 ("warship", "fire_fleets"), ("module_def", "fire_defences"),
                                 ("module_port", "dock"), ("page_crews", "repair")])


class FireTest(unittest.TestCase):
    """The page's fire is what the combat step counts."""

    def test_the_display_values_are_the_combat_step_s_arithmetic(self):
        display, combat = _read(DISPLAY), _read(COMBAT)
        # On fleets (sr_fl_gather_at) and on Defences (sr_cb_add_target), before a survey's edge, which is the target's.
        self.assertIn("value = { value = sr_fl_$N$_fire_fleets multiply = sr_fleet_quality multiply = sr_fleet_readiness }", combat)
        self.assertRegex(combat, r"value = sr_fl_\$N\$_fire_defences\s*multiply = sr_fleet_quality\s*multiply = sr_fleet_readiness\s*"
                                 r"multiply = sr_cb_edge_\$KEY\$")
        # What the figure leaves out is said on its hover: the survey's edge, and the share
        # hostile fleets stationed at the colony draw (sr_cb_fd_total_<key>).
        hover = dict(re.findall(r'(?m)^ (\w+):\d* "(.*)"$', _read(LOC)))["je_space_race_widget_fw_fire_defences_tt"]
        self.assertIn("raises it past this figure", hover)
        self.assertIn("Enemy fleets stationed at the colony draw a share of it", hover)
        values = _read(os.path.join(REPO, "common", "script_values", "sr_fleets_generated.txt"))
        total = values[values.index("\nsr_cb_fd_total_valles_marineris = {"):]
        self.assertIn("add = { value = var:sr_cb_fd3_valles_marineris multiply = sr_site_target_strength_valles_marineris "
                      "divide = { value = sr_site_target_strength_valles_marineris add = sr_cb_hs_value } }", total[:900])
        for n in SLOTS:
            for kind in ("fleets", "defences"):
                with self.subTest(slot=n, kind=kind):
                    self.assertIn(f"sr_disp_fl_{n}_fire_{kind} = {{\n\tvalue = sr_fl_{n}_fire_{kind}\n"
                                  "\tmultiply = sr_fleet_quality\n\tmultiply = sr_fleet_readiness\n}", display)


class DockTest(unittest.TestCase):
    """Where a fleet stands for refill and repair, as the month's step has it."""

    def test_the_dock_and_its_repair_follow_the_month_s_step(self):
        display = _read(DISPLAY)
        effects = _read(os.path.join(REPO, "common", "scripted_effects", "sr_fleet_effects.txt"))
        month = effects[effects.index("\nsr_fl_month_at = {"):]
        # sr_fl_month_at: a docked fleet is repaired by its dock's share, and only with a Space Command.
        self.assertIn("limit = { sr_fl_$N$_docked = yes }", month)
        self.assertRegex(month, r"set_local_variable = \{ name = sr_fl_share value = sr_fl_\$N\$_repair_share \}\s*if = \{\s*"
                                r"limit = \{ local_var:sr_fl_share > 0 sr_sc_operational = yes \}")
        for n in SLOTS:
            with self.subTest(slot=n):
                self.assertIn(f"sr_disp_fl_{n}_dock = {{\n\tvalue = 0\n"
                              f"\tif = {{ limit = {{ sr_fl_{n}_at_earth = yes }} value = 1 }}\n"
                              f"\telse_if = {{ limit = {{ sr_fl_{n}_docked = yes }} value = 2 }}\n"
                              f"\telse_if = {{ limit = {{ NOT = {{ has_variable = sr_fl_{n}_loc }} has_variable = sr_fl_{n}_dest }} value = 3 }}\n}}",
                              display)
                self.assertIn(f"sr_disp_fl_{n}_repair_pct = {{\n\tvalue = 0\n\tif = {{\n"
                              f"\t\tlimit = {{ sr_fl_{n}_docked = yes sr_sc_operational = yes }}\n"
                              f"\t\tvalue = sr_fl_{n}_repair_share\n\t\tmultiply = 100\n\t}}\n}}", display)

    def test_the_hovers_give_the_script_s_figures(self):
        loc = dict(re.findall(r'(?m)^ (\w+):\d* "(.*)"$', _read(LOC)))
        values = _read(os.path.join(REPO, "common", "script_values", "sr_fleet_values.txt"))
        for value, figure, key in (("sr_fl_repair_earth = { value = 0.2 }", "#v 20%#! at Earth", "fw_repair_tt"),
                                   ("sr_fl_repair_port_level = { value = 0.1 }", "#v 10%#! a Spaceport level", "fw_repair_tt"),
                                   ("sr_fl_attrition_share = { value = 0.05 }", "#v 5%#! of its strength a month", "fw_dock_tt"),
                                   ("sr_fl_port_refill_share = { value = 0.25 }", "#v 25%#! of its capacity at any other Spaceport", "fw_dock_tt"),
                                   ("sr_fl_port_refill_share = { value = 0.25 }", "#v 25%#! of capacity a month at any other Spaceport", "fl_dv_tt")):
            with self.subTest(figure=figure):
                self.assertIn(value, values)
                self.assertIn(figure, loc[f"je_space_race_widget_{key}"])

    def test_the_refill_rule_is_the_script_s(self):
        """Full at Earth and at a Spaceport on a propellant world, a quarter of
        capacity a month at any other Spaceport (sr_fl_month_at): three hovers
        and the player guide had it the other way round until the review of #2055."""
        effects = _read(os.path.join(REPO, "common", "scripted_effects", "sr_fleet_effects.txt"))
        month = effects[effects.index("\nsr_fl_month_at = {"):]
        self.assertRegex(month, r"limit = \{ sr_fl_\$N\$_refills_fully = yes \}\s*set_variable = \{ name = sr_fl_\$N\$_dv value = sr_fl_\$N\$_dv_capacity \}"
                                r"\s*\}\s*else = \{[^}]*value = sr_fl_\$N\$_dv_capacity\s*multiply = sr_fl_port_refill_share")
        triggers = _read(os.path.join(REPO, "common", "scripted_triggers", "sr_fleets_generated.txt"))
        fully = triggers[triggers.index("\nsr_fl_1_refills_fully = {"):]
        fully = fully[:fully.index("\n}\n")]
        self.assertIn("var:sr_fl_1_loc = 1", fully)
        self.assertIn("sr_loc_propellant_port_mars = yes", fully)
        loc = dict(re.findall(r'(?m)^ (\w+):\d* "(.*)"$', _read(LOC)))
        for key in ("fw_dock_tt", "fl_dv_tt", "dp_dv_short_tt"):
            with self.subTest(key=key):
                text = loc[f"je_space_race_widget_{key}"]
                self.assertIn("at a Spaceport on a site that makes propellant", text)
                self.assertIn("any other Spaceport", text)
        guide = _read(os.path.join(REPO, "docs", "player_guide", "16-space.md"))
        self.assertNotIn("propellant only on a site that makes it", guide)
        self.assertIn("by a quarter a month anywhere else", guide)

    def test_a_dock_s_work_needs_a_space_command_in_a_state_we_control(self):
        """sr_sc_operational, not the building's mere existence: the hovers say so."""
        loc = dict(re.findall(r'(?m)^ (\w+):\d* "(.*)"$', _read(LOC)))
        for key in ("fw_dock_tt", "fw_repair_tt", "fw_fire_fleets_tt"):
            with self.subTest(key=key):
                self.assertIn("$building_space_command$ in a state we control", loc[f"je_space_race_widget_{key}"])
        # Away from a dock supply counts down only at a location (sr_fl_month_at acts on a slot with one).
        self.assertIn("At a location with no dock its supply counts down", loc["je_space_race_widget_fw_dock_tt"])

    def test_supply_holds_in_flight_and_the_texts_say_so(self):
        """sr_fl_month_at acts only on a slot with a location, so a fleet in
        flight spends no supply however long the leg. The concept, the Supply
        hover and the player guide said it counted down "away from a dock"
        until #2057, which read as a month of supply for each month of a leg."""
        effects = _read(os.path.join(REPO, "common", "scripted_effects", "sr_fleet_effects.txt"))
        month = effects[effects.index("\nsr_fl_month_at = {"):]
        month = month[:month.index("\n}\n")]
        self.assertTrue(month.startswith("\nsr_fl_month_at = {\n\tif = {\n\t\tlimit = { has_variable = sr_fl_$N$_loc }"))
        self.assertNotRegex(month, r"\n\telse", "an outer else would act on a fleet in flight")
        self.assertIn("subtract = 1", month)
        loc = dict(re.findall(r'(?m)^ (\w+):\d* "(.*)"$', _read(LOC)))
        concepts = dict(re.findall(r'(?m)^ (\w+):\d* "(.*)"$', _read(os.path.join(
            REPO, "localization", "english", "te_concepts_l_english.yml"))))
        guide = _read(os.path.join(REPO, "docs", "player_guide", "16-space.md"))
        texts = {"concept": concepts["concept_sr_space_fleet_desc"],
                 "supply hover": loc["je_space_race_widget_fl_supply_tt"], "guide": guide}
        for name, text in texts.items():
            with self.subTest(text=name):
                self.assertNotIn("away from a dock", text.lower())
        self.assertIn("spending propellant but no supply", texts["concept"])
        self.assertIn("holds while the fleet is in flight", texts["supply hover"])
        self.assertIn("A fleet in flight\nuses none, however long the leg.", guide)


class TextTest(unittest.TestCase):
    """The window's own words."""

    @classmethod
    def setUpClass(cls):
        cls.loc = dict(re.findall(r'(?m)^ (\w+):\d* "(.*)"$', _read(LOC)))

    def test_a_leg_line_a_slot_reads_that_slot(self):
        for n in SLOTS:
            with self.subTest(slot=n):
                for key in (f"je_space_race_widget_fw_{n}_leg", f"je_space_race_widget_fw_{n}_leg_short"):
                    self.assertEqual(re.findall(r"ScriptValue\('(\w+)'\)", self.loc[key]),
                                     [f"sr_disp_fl_{n}_leg_weeks", f"sr_disp_fl_{n}_leg_dv"])
                # One text, the propellant's figure red in the second.
                self.assertEqual(self.loc[f"je_space_race_widget_fw_{n}_leg"].replace("propellant: #v ", "propellant: #R "),
                                 self.loc[f"je_space_race_widget_fw_{n}_leg_short"])

    def test_a_role_s_hover_is_its_concept(self):
        for role, concept in (("war", "warship"), ("rapid", "rapid"), ("siege", "siege"), ("carrier", "carrier"), ("tender", "tender")):
            with self.subTest(role=role):
                text = self.loc[f"je_space_race_widget_fw_role_{role}_tt"]
                self.assertIn(f"$concept_sr_role_{concept}_desc$", text)
                self.assertTrue(text.startswith(f"#header $concept_sr_role_{concept}$s#!\\n"))

    def test_the_fire_hovers_name_what_the_script_multiplies(self):
        """sr_fleet_quality's three technologies by their own keys, the crewed
        share and the half without a Space Command (sr_fleet_readiness)."""
        values = _read(os.path.join(REPO, "common", "script_values", "sr_fleet_values.txt"))
        quality = values[values.index("\nsr_fleet_quality = {"):]
        quality = quality[:quality.index("\n}\n")]
        techs = re.findall(r"has_technology_researched = (\w+)", quality)
        self.assertEqual(len(techs), 3)
        text = self.loc["je_space_race_widget_fw_fire_fleets_tt"]
        for tech in techs:
            self.assertIn(f"${tech}$", text)
        self.assertIn("sr_fleet_quality_step = { value = 0.25 }", values)
        self.assertIn("#v 25%#!", text)
        self.assertIn("sr_fleet_readiness_grounded = { value = 0.5 }", values)
        self.assertIn("at half without a $building_space_command$", text)
        self.assertIn("multiply = sr_pers_share_value", values[values.index("\nsr_fleet_readiness = {"):])
        self.assertIn("at the share crewed", text)


if __name__ == "__main__":
    unittest.main()
