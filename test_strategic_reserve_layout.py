"""The Strategic Reserve panel's layout, rows and display values.

The style-guide pass (docs/guides/gui_style_guide.md): an overview that is always
shown, the inventory open until closed, How the Strategic Reserve Works collapsed,
each section a type composed in one order, collapse flags that say their default,
and one inventory row per good, every row the same shape so that adding a good is
a copy of one row (.claude/skills/add-strategic-reserve-good).
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
WIDGET = os.path.join(REPO, "gui", "journal_entry_widgets", "strategic_reserve_widget.gui")
JE = os.path.join(REPO, "common", "journal_entries", "je_strategic_reserve.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "st_res_triggers.txt")
SVALS = os.path.join(REPO, "common", "script_values", "st_res_script_values.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "st_res_scripted_gui.txt")
BUTTONS = os.path.join(REPO, "common", "scripted_buttons", "st_res_buttons.txt")
HISTORY = os.path.join(REPO, "common", "scripted_effects", "te_history_strategic_reserve_effects.txt")
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

STATUS = ["te_st_res_sec_inventory"]
REFERENCE = ["te_st_res_sec_how"]
ROOTS = {"widget_je_strategic_reserve_overview": ("custom_widget_container_1", "te_st_res_overview_panel"),
         "widget_je_strategic_reserve_inventory": ("custom_widget_container_2", "te_st_res_status_sections"),
         "widget_je_strategic_reserve_reference": ("custom_widget_container_3", "te_st_res_reference_sections")}
# The keys the panel used before the pass; a survivor means a half-renamed flag.
OLD_FLAGS = ["st_res_row_expanded_", "st_res_policy_open_"]
HOW_TOPICS = ["hub", "rates", "status", "decay", "policies", "presets", "income", "history"]
# Per-good loc keys a row reads; the skill's file 14 lists the same set.
ROW_LOC = ["name", "status", "tooltip", "amount", "flow", "last", "decay", "price", "policy", "policy_reason"]
DISPLAY_VALUES = ["disp_policy", "disp_target", "disp_floor", "disp_status"]


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    return "\n".join(line.split("#", 1)[0] if '"' not in line.split("#", 1)[0] or line.count('"') % 2 == 0
                     else line for line in text.split("\n"))


def _body(text, opener):
    """The text inside the first brace of `opener`'s match, up to its matching close."""
    m = re.search(opener, text)
    assert m, f"no {opener}"
    start = text.index("{", m.start())
    depth = 0
    for j in range(start, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:j]
    raise AssertionError(f"{opener} is not closed")


def _type_body(text, name):
    return _body(text, rf"type {name} = \w+ \{{")


def _instances(text, name):
    """Every `name = { ... }` body in text, in order."""
    out = []
    for m in re.finditer(rf"\b{name} = \{{", text):
        out.append(_body(text[m.start():], rf"{name} = \{{"))
    return out


def _goods():
    return re.findall(r"^st_res_(\w+)_unlocked_trigger = \{", _read(TRIGGERS), re.M)


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        for m in re.finditer(r'^ ([\w.\-]+):\d* "(.*)"\s*$', _read(path), re.M):
            keys[m.group(1)] = m.group(2)
    return keys


class OrderTest(unittest.TestCase):
    def test_composers_order_the_sections(self):
        widget = _read(WIDGET)
        for composer, expected in (("te_st_res_status_sections", STATUS),
                                   ("te_st_res_reference_sections", REFERENCE)):
            body = _type_body(widget, composer)
            self.assertEqual(re.findall(r"^\t\t(te_st_res_sec_\w+) = \{", body, re.M), expected, composer)
            self.assertIn('visible = "[JournalEntry.IsActive]"', body, composer)

    def test_the_entry_attaches_three_gated_roots(self):
        je, widget = _read(JE), _read(WIDGET)
        for name, (container, composer) in ROOTS.items():
            self.assertRegex(je, rf'name = "{name}"\s*container = "{container}"', name)
            root = _body(widget, rf'flowcontainer = \{{\s*name = "{name}"')
            self.assertIn('visible = "[JournalEntry.IsActive]"', root, f"{name} lost its IsActive gate (gotcha #14)")
            self.assertIn(f"{composer} = {{}}", root, name)

    def test_the_overview_cannot_be_collapsed(self):
        overview = _type_body(_read(WIDGET), "te_st_res_overview_panel")
        self.assertNotIn("GetVariableSystem", overview)
        self.assertIn('visible = "[JournalEntry.IsActive]"', overview)


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read(WIDGET)

    def test_flags_say_their_default(self):
        flags = set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text))
        self.assertTrue(flags)
        for f in flags:
            self.assertRegex(f, r"^st_res_\w+_(open|closed)$", f"flag {f} does not say its default")
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", self.text))
            bare = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", self.text)) - negated
            if f.endswith("_closed"):   # shown unless closed: one bare Exists, the show-more arrow
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 1, f)
            else:                       # shown only once opened: one negated Exists, the show-more arrow
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 1, f)

    def test_no_old_flag_survives(self):
        for f in OLD_FLAGS:
            self.assertNotIn(f"'{f}", self.text, f)

    def test_inventory_open_and_how_it_works_collapsed(self):
        inventory = _type_body(self.text, "te_st_res_sec_inventory")
        self.assertIn("GetVariableSystem.Toggle('st_res_inventory_closed')", inventory)
        self.assertIn("visible = \"[Not(GetVariableSystem.Exists('st_res_inventory_closed'))]\"", inventory)
        how = _type_body(self.text, "te_st_res_sec_how")
        self.assertIn("GetVariableSystem.Toggle('st_res_how_open')", how)
        self.assertIn("visible = \"[GetVariableSystem.Exists('st_res_how_open')]\"", how)

    def test_rows_and_their_settings_start_collapsed(self):
        for g in _goods():
            self.assertIn(f"GetVariableSystem.Toggle('st_res_row_{g}_open')", self.text, g)
            self.assertIn(f"GetVariableSystem.Toggle('st_res_policy_{g}_open')", self.text, g)


class RowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.widget = _read(WIDGET)
        cls.rows = _instances(_type_body(cls.widget, "te_st_res_sec_inventory"), "te_st_res_good_row")
        cls.goods = _goods()

    def _good_of(self, row):
        m = re.search(r"GetScriptedGui\('st_res_adjust_(\w+)_sgui'\)", row)
        self.assertTrue(m, "a row without its adjust scripted GUI")
        return m.group(1)

    def test_one_row_per_good_in_unlock_order(self):
        self.assertEqual([self._good_of(r) for r in self.rows], self.goods)

    def test_every_row_is_the_same_row(self):
        """Adding a good is a copy of one row with the name swapped: nothing else differs."""
        shapes = {}
        for row in self.rows:
            g = self._good_of(row)
            shapes[g] = row.replace(g, "<G>")
        first = self.goods[0]
        for g, shape in shapes.items():
            self.assertEqual(shape, shapes[first], f"the {g} row differs from the {first} row beyond its name")

    def test_every_row_block_is_filled(self):
        declared = set(re.findall(r'\bblock "(\w+)"', _type_body(self.widget, "te_st_res_good_row")))
        self.assertTrue(declared)
        row = self.rows[0]
        filled = set(re.findall(r'^\t\t\t\tblockoverride "(\w+)"', row, re.M))
        self.assertEqual(filled, declared)

    def test_rows_read_what_exists(self):
        svals = set(re.findall(r"^(\w+) = \{", _read(SVALS), re.M))
        sguis = set(re.findall(r"^(\w+) = \{", _read(SGUIS), re.M))
        loc = _loc()
        for row in self.rows:
            for sv in re.findall(r"ScriptValue\('(\w+)'\)", row):
                self.assertIn(sv, svals, sv)
            for sg in re.findall(r"GetScriptedGui\('(\w+)'\)", row):
                self.assertIn(sg, sguis, sg)
            for key in re.findall(r'(?:text|tooltip) = "(\w+)"', row):
                self.assertIn(key, loc, key)
        for g in self.goods:
            for part in ROW_LOC:
                self.assertIn(f"st_res_row_{g}_{part}", loc, f"{g} {part}")

    def test_markers_and_policy_icon_are_gated(self):
        row = self.rows[0]
        g = self._good_of(row)
        target = _body(row, r'blockoverride "row_target_marker" \{')
        self.assertIn(f"LessThan_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_{g}_disp_target'), '(CFixedPoint)100' )", target)
        floor = _body(row, r'blockoverride "row_floor_marker" \{')
        self.assertIn(f"GreaterThan_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_{g}_disp_floor'), '(CFixedPoint)0' )", floor)
        auto = _body(row, r'blockoverride "row_auto" \{')
        self.assertIn(f"ScriptValue('st_res_{g}_disp_policy')", auto)

    def test_the_rate_buttons_use_the_row_scripted_gui(self):
        """The three buttons live in the type and read the inherited ScriptedGui (gotcha #6)."""
        line = _type_body(self.widget, "te_st_res_good_row")
        for d in (0, 1, 2):
            for call in ("IsShown", "IsValid", "Execute"):
                self.assertIn(f"ScriptedGui.{call}( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope )"
                              f".AddScope( 'dir', MakeScopeValue( '(CFixedPoint){d}' ) ).End )", line, f"{call} {d}")


class DisplayValueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(_read(SVALS))

    def _value(self, name):
        return _body(self.text, rf"^{name} = \{{".replace("^", r"(?m)^"))

    def test_every_good_has_its_display_values(self):
        for g in _goods():
            for part in DISPLAY_VALUES:
                self._value(f"st_res_{g}_{part}")

    def test_display_values_guard_every_read(self):
        names = ["st_res_disp_hub_staffed"] + [f"st_res_{g}_{p}" for g in _goods() for p in DISPLAY_VALUES]
        for name in names:
            body = self._value(name)
            for var in set(re.findall(r"var:(\w+)", body)):
                self.assertIn(f"has_variable = {var}", body, f"{name} reads var:{var} unguarded")

    def test_markers_follow_the_policies_that_use_them(self):
        """Target while the policy can buy (1, 3); protected while it can sell (2, 3)."""
        for g in _goods():
            target = self._value(f"st_res_{g}_disp_target")
            self.assertRegex(target, r"^\s*value = 100")
            self.assertEqual(sorted(re.findall(rf"var:st_res_{g}_policy = (\d)", target)), ["1", "3"], g)
            floor = self._value(f"st_res_{g}_disp_floor")
            self.assertRegex(floor, r"^\s*value = 0")
            self.assertEqual(sorted(re.findall(rf"var:st_res_{g}_policy = (\d)", floor)), ["2", "3"], g)


class HowItWorksTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.widget = _read(WIDGET)
        cls.loc = _loc()

    def test_one_heading_and_note_per_topic(self):
        how = _type_body(self.widget, "te_st_res_sec_how")
        self.assertEqual(re.findall(r'text = "je_strategic_reserve_how_sub_(\w+)"', how), HOW_TOPICS)
        self.assertEqual(re.findall(r'text = "je_strategic_reserve_how_(?!sub_|header)(\w+)"', how), HOW_TOPICS)
        for t in HOW_TOPICS:
            self.assertIn(f"je_strategic_reserve_how_{t}", self.loc, t)

    def test_explanations_live_only_in_how_it_works(self):
        for sec in ("te_st_res_overview_panel", "te_st_res_sec_inventory", "te_st_res_good_row"):
            body = _type_body(self.widget, sec)
            self.assertNotIn("st_res_note", body, sec)
            self.assertNotIn("je_strategic_reserve_how_", body, sec)

    def test_status_text_keeps_only_the_no_hub_line(self):
        """Status text that repeats the overview is removed (owner, 2026-09-29)."""
        je = _read(JE)
        status = _body(je, r"status_desc = \{")
        self.assertEqual(re.findall(r"desc = (\w+)", status), ["je_strategic_reserve_status_no_hub"])
        overview = _type_body(self.widget, "te_st_res_overview_panel")
        for key in ("je_strategic_reserve_ov_cap_tt", "je_strategic_reserve_ov_income_tt"):
            self.assertIn(f'"{key}"', overview, key)
        self.assertIn("st_res_total_sale_profit", self.loc["je_strategic_reserve_ov_income_tt"])
        self.assertIn("country_st_res_weekly_rate_cap_add", self.loc["je_strategic_reserve_ov_cap_tt"])


class TidinessTest(unittest.TestCase):
    def test_panel_loc_has_no_leading_or_trailing_line_break(self):
        """Style rule 8: no tooltip or line ends in a blank line."""
        loc = _loc()
        keys = set(re.findall(r'(?:text|tooltip) = "(\w+)"', _read(WIDGET)))
        keys |= set(re.findall(r"'(je_strategic_reserve_\w+)'", _read(WIDGET)))
        keys |= {f"st_res_row_{g}_{p}" for g in _goods() for p in ROW_LOC}
        for key in sorted(keys):
            value = loc.get(key)
            if value is None:
                continue
            self.assertFalse(value.startswith("\\n") or value.endswith("\\n"), key)

    def test_new_concepts_are_defined_with_loc(self):
        concepts = set(re.findall(r"^(concept_\w+) = \{", _read(CONCEPTS), re.M))
        loc = _loc()
        for c in ("concept_st_res_flow_cap", "concept_st_res_adjustment_step", "concept_st_res_policy"):
            self.assertIn(c, concepts)
            self.assertIn(c, loc)
            self.assertIn(f"{c}_desc", loc)


class SharedButtonsTest(unittest.TestCase):
    """Cycle Step Size and Reset Reserve Rates sit beside the adjustment step (owner, 2026-09-29)."""
    PAIRS = {"st_res_cycle_step_sgui": ("st_res_cycle_step_size_button", "st_res_cycle_step_size_effect"),
             "st_res_reset_rates_sgui": ("st_res_reset_rates_button", "st_res_reset_rates_effect")}

    def test_the_panel_buttons_run_the_scripted_buttons_effects(self):
        sguis, buttons = _read(SGUIS), _read(BUTTONS)
        for sgui, (button, effect) in self.PAIRS.items():
            self.assertIn(f"{effect} = yes", _body(buttons, rf"^{button} = \{{".replace("^", r"(?m)^")), button)
            body = _body(sguis, rf"^{sgui} = \{{".replace("^", r"(?m)^"))
            self.assertIn(f"{effect} = yes", _body(body, r"effect = \{"), sgui)
            self.assertIn("always = no", _body(body, r"ai_is_valid = \{"), sgui)

    def test_the_scripted_buttons_are_the_ais_only(self):
        buttons = _read(BUTTONS)
        for button, _ in self.PAIRS.values():
            visible = _body(_body(buttons, rf"(?m)^{button} = \{{"), r"visible = \{")
            self.assertIn("is_ai = yes", visible, button)

    def test_they_sit_beside_the_step_with_composed_tooltips(self):
        widget = _read(WIDGET)
        inventory = _type_body(widget, "te_st_res_sec_inventory")
        step = inventory.index('"je_strategic_reserve_inv_step"')
        for sgui in self.PAIRS:
            at = inventory.index(f"GetScriptedGui('{sgui}')")
            self.assertLess(abs(at - step), 600, f"{sgui} is not beside the step line")
        button = _type_body(widget, "st_res_shared_button")
        self.assertIn("Concatenate( ScriptedGui.IsValidTooltip(", button)
        self.assertIn("Localize( 'te_tt_break' )", button)
        self.assertIn("ScriptedGui.ExecuteTooltip(", button)


class HistoryTest(unittest.TestCase):
    """Each good's fill by month, charted inside its expanded row (owner, 2026-09-29)."""

    def test_every_unlocked_good_is_recorded(self):
        history = _read(HISTORY)
        for g in _goods():
            self.assertRegex(history, rf"st_res_{g}_unlocked_trigger = yes \}}\s*te_history_record_sample = \{{ "
                                      rf"METRIC = st_res_{g} VALUE = st_res_{g}_fill_pct \}}", g)

    def test_the_entry_records_monthly(self):
        pulse = _body(_read(JE), r"on_monthly_pulse = \{")
        self.assertIn("te_history_record_strategic_reserve_samples = yes", pulse)

    def test_each_row_charts_its_own_good_inside_the_expanded_row(self):
        widget = _read(WIDGET)
        row_type = _type_body(widget, "te_st_res_good_row")
        chart_box = _body(row_type, r"flowcontainer = \{\s*direction = vertical\s*ignoreinvisible = yes\s*spacing = 2\s*margin_bottom = 4")
        self.assertIn('block "row_open" {}', chart_box, "the chart is not gated on the row being expanded")
        self.assertIn('block "row_history" {}', chart_box)
        for row in _instances(_type_body(widget, "te_st_res_sec_inventory"), "te_st_res_good_row"):
            g = re.search(r"st_res_adjust_(\w+)_sgui", row).group(1)
            chart = _body(row, r'blockoverride "row_history" \{')
            self.assertIn(f'tooltip = "st_res_hist_tt_{g}"', chart, g)
            self.assertIn(f"ScriptContainer.HasVariable( 'te_hist_v_st_res_{g}' )", chart, g)
            self.assertIn('blockoverride "marker_pips" {}', chart, g)


class PolicyIconTest(unittest.TestCase):
    """Clicking a good's policy icon opens its settings directly (owner, 2026-09-29)."""

    def test_the_icon_toggles_the_settings(self):
        row_type = _type_body(_read(WIDGET), "te_st_res_good_row")
        icon = _body(row_type, r'button = \{\s*size = \{ 30 28 \}')
        self.assertIn('block "row_settings_toggle" {}', icon)
        self.assertEqual(re.findall(r'texture = "([^"]+)"', icon), [f"{ST_RES_ICONS}policy_automated.dds"] * 2)

    def test_settings_show_under_a_collapsed_row_while_open(self):
        widget = _read(WIDGET)
        for row in _instances(_type_body(widget, "te_st_res_sec_inventory"), "te_st_res_good_row"):
            g = re.search(r"st_res_adjust_(\w+)_sgui", row).group(1)
            shown = _body(row, r'blockoverride "row_settings_shown" \{')
            self.assertIn(f"Or( GetVariableSystem.Exists('st_res_row_{g}_open'), "
                          f"GetVariableSystem.Exists('st_res_policy_{g}_open') )", shown, g)


# ---------------------------------------------------------------------------
# Round 3, rule 1: nothing a player reads may end in "...". Every label in a
# fixed-width cell must fit it: characters x units per character x 1.1 <= the
# cell's width. Units per character are the owner's screenshot measurements
# for the large (10) and medium (8.6) fonts; the small font's 7.3 is scaled
# from those by the font sizes, and is an estimate.
# ---------------------------------------------------------------------------
UPC = {"large": 10.0, "medium": 8.6, "small": 7.3}
MARGIN = 1.1
TEXT_ICON = "XX"  # a @texticon! draws about two characters wide


def _display(value, loc, stand_ins=()):
    """The text a loc value shows, formatting stripped, data replaced by stand-ins."""
    v = value.replace("\\n", "\n")
    v = re.sub(r"\$(\w+)\$", lambda m: loc.get(m.group(1), ""), v)
    v = re.sub(r"\[Concept\(\s*'\w+'\s*,\s*'([^']*)'\s*\)\]", r"\1", v)
    v = re.sub(r"\[(concept_\w+)\]", lambda m: loc[m.group(1)], v)
    fills = iter(stand_ins)
    v = re.sub(r"\[[^\]]*\]", lambda m: next(fills), v)
    self_check = next(fills, None)
    assert self_check is None, f"unused stand-in {self_check!r} for {value!r}"
    v = re.sub(r"@\w+!", TEXT_ICON, v)
    v = v.replace("#!", "")
    v = re.sub(r"#[A-Za-z_]+ ?", "", v)
    return max(v.split("\n"), key=len)


# (loc key, cell width, font, stand-ins for its [data] in order)
STATIC_CELLS = (
    [(f"st_res_row_{g}_name", 150, "medium", ()) for g in
     ("grain", "ammunition", "oil", "small_arms", "artillery", "aeroplanes", "tanks", "fertilizer")]
    + [("je_strategic_reserve_inv_col_good", 150, "small", ()),
       ("je_strategic_reserve_inv_col_stock", 150, "small", ()),
       ("je_strategic_reserve_inv_col_status", 64, "small", ()),
       ("je_strategic_reserve_inv_col_rate", 86, "small", ()),
       ("je_strategic_reserve_inv_step", 240, "medium", ("10,000",)),
       ("st_res_panel_cycle_step", 92, "small", ()),
       ("st_res_panel_reset_rates", 102, "small", ()),
       ("je_strategic_reserve_ov_hub_staffed", 128, "small", ()),
       ("je_strategic_reserve_ov_hub_understaffed", 128, "small", ()),
       ("je_strategic_reserve_ov_cap_label", 128, "small", ()),
       ("je_strategic_reserve_ov_income_label", 128, "small", ()),
       ("je_strategic_reserve_ov_cap_value", 128, "large", ("99,999",)),
       ("je_strategic_reserve_ov_income_value", 128, "large", ("999.9K",)),
       ("st_res_row_settings_header", 390, "medium", ()),
       ("je_strategic_reserve_inv_header", 480, "large", ()),
       ("je_strategic_reserve_how_header", 480, "large", ()),
       ("st_res_hist_title", 484, "large", ())]
    + [(f"st_res_row_label_{k}", 170, "medium", ()) for k in
       ("stored", "rate", "last", "decay", "price", "policy")]
    + [(f"st_res_policy_short_{k}", 102, "small", ()) for k in ("manual", "buy_cheap", "release_high", "stabilize")]
    + [(f"st_res_preset_{k}", 102, "small", ()) for k in ("conservative", "standard", "aggressive")]
    + [(f"st_res_policy_label_{k}", 300, "small", ()) for k in
       ("buy_thr", "sell_thr", "max_flow", "floor_pct", "ceil_pct", "budget", "price_memory", "ramp")]
    + [(f"st_res_policy_panel_{k}_header", 450, "small", ()) for k in ("policy", "preset", "settings")]
)

# Value cells whose text is data: the longest reading each can show.
DYNAMIC_CELLS = [
    ("st_res_row_ammunition_amount", 270, "medium", ("999,999", "999,999", "100")),
    ("st_res_row_ammunition_flow", 270, "medium", ("-10,000",)),
    ("st_res_row_ammunition_last", 270, "medium", ("-10,000.0",)),
    ("st_res_row_oil_decay", 270, "medium", ("25.00%", "9,999.9")),
    ("st_res_row_ammunition_price", 270, "medium", ("-100%", "+100")),
]
# The longest names the policy value cell (270, medium) and the stepper value
# cells (90, small) can show.
LONGEST_POLICY_NAME_KEYS = ("st_res_policy_manual", "st_res_policy_buy_cheap",
                            "st_res_policy_release_high", "st_res_policy_stabilize")
LONGEST_STEPPER_VALUE = "9,999,999"  # the weekly budget's ceiling grows with the hub


class WidthBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()

    def _check(self, key, width, font, stand_ins=()):
        text = _display(self.loc[key], self.loc, stand_ins)
        need = len(text) * UPC[font] * MARGIN
        self.assertLessEqual(need, width, f"{key} {text!r}: {need:.0f} > {width} ({font})")

    def test_static_labels_fit_their_cells(self):
        for key, width, font, stand_ins in STATIC_CELLS:
            with self.subTest(key=key):
                self._check(key, width, font, stand_ins)

    def test_dynamic_values_fit_their_cells(self):
        for key, width, font, stand_ins in DYNAMIC_CELLS:
            with self.subTest(key=key):
                self._check(key, width, font, stand_ins)
        longest = max((self.loc[k] for k in LONGEST_POLICY_NAME_KEYS), key=len)
        self.assertLessEqual(len(longest) * UPC["medium"] * MARGIN, 270, longest)
        self.assertLessEqual(len(LONGEST_STEPPER_VALUE) * UPC["small"] * MARGIN, 90)

    def test_the_cells_are_the_widths_the_budget_assumes(self):
        widget = _read(WIDGET)
        row = _type_body(widget, "te_st_res_good_row")
        self.assertIn("size = { 150 28 }", row)            # the name's text
        stepper = _type_body(widget, "widget_je_st_res_policy_stepper")
        self.assertIn("size = { 300 24 }", stepper)        # the label
        self.assertIn("size = { 90 24 }", stepper)         # the value
        self.assertIn("max_width = 102", _type_body(widget, "widget_je_st_res_policy_choice"))
        self.assertIn("minimumsize = { 170 -1 }", _type_body(widget, "st_res_value_row"))
        self.assertIn("minimumsize = { 270 -1 }", _type_body(widget, "st_res_value_row"))


class StatusIconTest(unittest.TestCase):
    """One icon per status (owner, 2026-09-30); exactly one drawn at a time."""
    CODES = {"idle": 0, "storing": 1, "withdrawing": 2, "blocked": 3}

    def test_each_status_icon_is_gated_on_one_code(self):
        widget = _read(WIDGET)
        cell = _body(_type_body(widget, "te_st_res_good_row"), r'widget = \{\s*size = \{ 30 28 \}')
        textures = re.findall(r'texture = "([^"]+)"', cell)
        self.assertEqual(len(textures), 4)
        self.assertEqual(len(set(textures)), 4, "two statuses share an icon")
        for row in _instances(_type_body(widget, "te_st_res_sec_inventory"), "te_st_res_good_row"):
            g = re.search(r"st_res_adjust_(\w+)_sgui", row).group(1)
            self.assertIn(f'tooltip = "st_res_row_{g}_status"', row)
            for status, code in self.CODES.items():
                body = _body(row, rf'blockoverride "row_status_{status}" \{{')
                self.assertEqual(re.findall(r"visible = ", body), ["visible = "], f"{g} {status}")
                self.assertIn(f"EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue("
                              f"'st_res_{g}_disp_status'), '(CFixedPoint){code}' )", body, f"{g} {status}")

    def test_the_status_code_groups_as_the_status_word_does(self):
        """st_res_<good>_disp_status and st_res_<good>_mode_text read the same code the same way."""
        values = _strip_comments(_read(SVALS))
        custom = _read(os.path.join(REPO, "common", "customizable_localization", "st_res_custom_loc.txt"))
        for g in _goods():
            disp = _body(values, rf"(?m)^st_res_{g}_disp_status = \{{")
            self.assertIn(f"has_variable = st_res_{g}_last_status", disp)
            self.assertRegex(disp, rf"var:st_res_{g}_last_status = 1\s*var:st_res_{g}_last_status = 3\s*\}}\s*\}}\s*value = 1")
            self.assertRegex(disp, rf"var:st_res_{g}_last_status = 2\s*var:st_res_{g}_last_status = 4\s*\}}\s*\}}\s*value = 2")
            self.assertRegex(disp, rf"var:st_res_{g}_last_status >= 5 \}}\s*value = 3")
            mode = _body(custom, rf"(?m)^st_res_{g}_mode_text = \{{")
            self.assertRegex(mode, rf"var:st_res_{g}_last_status = 1\s*var:st_res_{g}_last_status = 3\s*\}}\s*\}}\s*localization_key = st_res_mode_storing")
            self.assertRegex(mode, rf"var:st_res_{g}_last_status = 2\s*var:st_res_{g}_last_status = 4\s*\}}\s*\}}\s*localization_key = st_res_mode_withdrawing")
            self.assertRegex(mode, rf"var:st_res_{g}_last_status >= 5\s*\}}\s*localization_key = st_res_mode_blocked")

    def test_the_hover_gives_the_word_and_the_reason(self):
        loc = _loc()
        for g in _goods():
            value = loc[f"st_res_row_{g}_status"]
            self.assertIn(f"GetCustom('st_res_{g}_mode_text')", value)
            self.assertIn(f"GetCustom('st_res_{g}_reason_text')", value)


ICONS_DOC = os.path.join(REPO, "docs", "systems", "strategic_reserve_gui_icons.md")
ST_RES_ICONS = "gfx/interface/icons/st_res_icons/"
# The row's status icons (PR #586), by the block that gates each.
STATUS_ICONS = {"row_status_idle": "status_idle", "row_status_storing": "status_storing",
                "row_status_withdrawing": "status_withdrawing", "row_status_blocked": "status_blocked"}
# The vanilla textures that stood in before #586; none may come back.
PLACEHOLDERS = ("generic_icons/trend_nochange.dds", "generic_icons/trend_up.dds", "generic_icons/trend_down.dds",
                "generic_icons/warning.dds", "production_methods/auto_expand.dds")
# Interface chrome, not icons: the transparent overlay and the UN's bar marker.
CHROME = {"gfx/interface/icons/generic_icons/transparent.dds", "gfx/interface/progressbar/progressbar_marker.dds"}


class IconsTest(unittest.TestCase):
    def test_each_status_draws_its_own_icon(self):
        """Like the UN's UnIconsTest: each status's block is held to its file."""
        row_type = _type_body(_read(WIDGET), "te_st_res_good_row")
        found = dict(re.findall(r'block "(row_status_\w+)" \{\}\s*texture = "([^"]+)"', row_type))
        self.assertEqual(found, {b: f"{ST_RES_ICONS}{n}.dds" for b, n in STATUS_ICONS.items()})

    def test_no_placeholder_is_left(self):
        widget = _read(WIDGET)
        for p in PLACEHOLDERS:
            self.assertNotIn(p, widget, p)

    def test_every_icon_is_listed(self):
        """Style rule 10: every icon, placeholder or final, is in the icons doc."""
        doc = _read(ICONS_DOC)
        textures = set(re.findall(r'texture = "([^"]+)"', _read(WIDGET))) - CHROME
        self.assertTrue(textures)
        for t in textures:
            if t.startswith(ST_RES_ICONS):   # listed by file name under the folder, as the UN's list is
                self.assertIn(ST_RES_ICONS, doc)
                self.assertIn(f"`{t[len(ST_RES_ICONS):]}`", doc, t)
            else:
                self.assertIn(t, doc, t)



MARKET = os.path.join(REPO, "gui", "market_panel.gui")
TAB_SGUIS = os.path.join(REPO, "common", "scripted_guis", "te_system_tab_sguis.txt")
SR_TAB_GATE = ("GetScriptedGui('te_market_strategic_reserve_tab_sgui').IsShown( "
               "GuiScope.SetRoot( GetPlayer.MakeScope ).End )")
SR_TAB_UNLOCK = "GetScriptedGui('te_market_strategic_reserve_tab_unlock_sgui')"
# Vanilla's test for "the player's own market" (budget_panel.gui's tariff buttons): the
# market its capital is in, whether it leads it or joined it.
OWN_MARKET = "MarketPanel.GetMarket.IsSame( GetPlayer.GetCapital.GetMarket )"
BUTTONS_TAG = "### TE: Climate and Reserve tabs (te_global_warming, te_strategic_reserve) ###"
# One slot of six in the house width budget (test_global_warming_layout.py's MarketTabTest).
SIX_SLOT = (540 - 6 - 10) / 6


def _te_blocks(text, tag):
    """Each block of market_panel.gui opened by `tag`, up to its END TE line."""
    out = []
    start = text.find(tag)
    while start != -1:
        end = text.index("### END TE ###", start)
        out.append(text[start:end])
        start = text.find(tag, end)
    return out


def _overrides(body):
    """{blockoverride name: its body, whitespace collapsed}, for one-level blocks."""
    return {m.group(1): " ".join(m.group(2).split())
            for m in re.finditer(r'blockoverride "(\w+)" \{([^{}]*)\}', body)}


class MarketTabTest(unittest.TestCase):
    """The Market panel's Reserve tab (style guide rule 9; feasibility §5.1):
    the journal entry's own composers under GetPlayerJournalEntry, gated,
    greyed until the entry runs, ending with Open Journal Entry, and shown on
    the player's own market only."""

    @classmethod
    def setUpClass(cls):
        cls.market = _read(MARKET)
        cls.buttons = _te_blocks(cls.market, BUTTONS_TAG)
        cls.content = _te_blocks(cls.market, "### TE: Reserve tab (te_strategic_reserve) ###")

    def _sr_buttons(self):
        return {k: v for k, v in _overrides(self.buttons[0]).items() if k.startswith("sixth_button")}

    def test_one_button_block_and_one_content_block(self):
        self.assertEqual(len(self.buttons), 1)
        self.assertEqual(len(self.content), 1)
        self.assertIn('name = "te_market_strategic_reserve_tab"', self.content[0])
        self.assertIn("visible = \"[InformationPanel.IsTabSelected('te_strategic_reserve')]\"", self.content[0])

    def test_the_reserve_tab_is_slot_six(self):
        halves = self._sr_buttons()
        self.assertEqual(set(halves), {"sixth_button", "sixth_button_tooltip", "sixth_button_click",
                                       "sixth_button_visibility", "sixth_button_visibility_checked",
                                       "sixth_button_selected"})
        self.assertEqual(halves["sixth_button"], 'text = "te_market_tab_strategic_reserve"')
        self.assertEqual(halves["sixth_button_selected"], 'text = "te_market_tab_strategic_reserve"')
        self.assertIn("te_tab_buttons_six = {", self.market)

    def test_the_tab_composes_the_journal_roots_types_in_order(self):
        body = self.content[0]
        found = re.findall(r"^\t+(te_\w+) = \{\}", body, re.M)
        self.assertEqual(found, [wrapped for _, wrapped in ROOTS.values()])
        self.assertGreater(body.index('text = "te_system_tab_open_journal"'), body.index("te_st_res_reference_sections"))
        self.assertIn("onclick = \"[InformationPanelBar.OpenJournalEntryPanel(JournalEntry.AccessSelf)]\"", body)

    def test_the_gate_sits_above_the_journal_entry_datacontext(self):
        body = self.content[0]
        dc = body.index("datacontext = \"[GetPlayerJournalEntry('je_strategic_reserve')]\"")
        gate = body.index(f'visible = "[And( {SR_TAB_GATE}, {OWN_MARKET} )]"')
        self.assertLess(gate, dc)
        self.assertLess(body.index('text = "je_strategic_reserve"'), gate)   # the header sits outside it
        opener = body.rindex("flowcontainer = {", 0, dc)
        self.assertNotIn("visible", body[opener:dc])

    def test_the_column_is_as_wide_as_the_journal_roots(self):
        body = self.content[0]
        dc = body.index("GetPlayerJournalEntry('je_strategic_reserve')")
        head = body[dc:body.index("te_st_res_overview_panel", dc)]
        self.assertIn("minimumsize = { 520 -1 }", head)
        self.assertIn("parentanchor = hcenter", head)

    def test_the_button_is_greyed_until_the_entry_runs(self):
        halves = self._sr_buttons()
        self.assertEqual(halves["sixth_button_click"],
                         f'enabled = "[{SR_TAB_GATE}]" onclick = "[InformationPanel.SelectTab(\'te_strategic_reserve\')]"')
        self.assertIn(f"{SR_TAB_UNLOCK}.IsValidTooltip(", halves["sixth_button_tooltip"])
        self.assertIn("'te_market_tab_strategic_reserve_tt'", halves["sixth_button_tooltip"])
        self.assertIn("'te_market_tab_strategic_reserve_locked_tt'", halves["sixth_button_tooltip"])
        for half in ("sixth_button_visibility", "sixth_button_visibility_checked"):
            self.assertIn("IsTabSelected('te_strategic_reserve')", halves[half], half)
            self.assertIn(f"{SR_TAB_UNLOCK}.IsShown(", halves[half], half)
        loc = _loc()
        for key in ("te_market_tab_strategic_reserve", "te_market_tab_strategic_reserve_tt",
                    "te_market_tab_strategic_reserve_locked_tt", "te_market_strategic_reserve_open_journal_tt",
                    "st_res_entry_unlock_tt", "te_market_strategic_reserve_elsewhere",
                    "te_market_strategic_reserve_open_own", "te_market_strategic_reserve_open_own_tt"):
            self.assertTrue(loc.get(key), key)

    def test_the_tab_shows_on_the_players_own_market_only(self):
        """The clickable half asks which market the panel shows; the selected
        half does not, so a panel opened on another market with the tab still
        selected marks it and shows the note instead of an empty body."""
        halves = self._sr_buttons()
        self.assertIn(OWN_MARKET, halves["sixth_button_visibility_checked"])
        self.assertNotIn(OWN_MARKET, halves["sixth_button_visibility"])
        body = self.content[0]
        note = body.index(f'visible = "[Not( {OWN_MARKET} )]"')
        note_body = body[note:body.index(f'visible = "[And( {SR_TAB_GATE}, {OWN_MARKET} )]"')]
        self.assertIn('text = "te_market_strategic_reserve_elsewhere"', note_body)
        # The link opens the player's market (the sidebar's AccessFirstMarket) at this tab,
        # through vanilla's OpenMarketPanelTab (states_panel.gui).
        self.assertIn("onclick = \"[InformationPanelBar.OpenMarketPanelTab(AccessPlayer.AccessFirstMarket.Self, "
                      "'te_strategic_reserve')]\"", note_body)
        for vanilla in ((os.path.join(REPO, "gui", "budget_panel.gui"), "IsSame(GetPlayer.GetCapital.GetMarket)"),
                        (os.path.join(REPO, "gui", "states_panel.gui"), "InformationPanelBar.OpenMarketPanelTab("),
                        (os.path.join(REPO, "gui", "topbar.gui"), "AccessPlayer.AccessFirstMarket.Self")):
            self.assertIn(vanilla[1], _read(vanilla[0]), vanilla)

    def test_the_tooltip_has_three_branches(self):
        """Open: the tab's own tooltip. Conditions met but the entry not
        running: te_market_tab_met_tt, since IsValidTooltip prints nothing for
        a passing test. Otherwise: the locked line and the checklist."""
        root = "GuiScope.SetRoot( GetPlayer.MakeScope ).End"
        expected = (f"tooltip = \"[SelectLocalization( {SR_TAB_GATE}, 'te_market_tab_strategic_reserve_tt', "
                    f"SelectLocalization( {SR_TAB_UNLOCK}.IsValid( {root} ), 'te_market_tab_met_tt', "
                    f"Concatenate( Localize( 'te_market_tab_strategic_reserve_locked_tt' ), "
                    f"{SR_TAB_UNLOCK}.IsValidTooltip( {root} ) ) ) )]\"")
        self.assertEqual(self._sr_buttons()["sixth_button_tooltip"], expected)
        met = _loc()["te_market_tab_met_tt"]
        self.assertTrue(met.startswith("#b Not open yet#!"), met)
        self.assertIn("conditions are met", met)

    def test_no_tab_icon(self):
        """System tabs carry no icon, as vanilla's tabs don't (the owner, 2026-09-30)."""
        self.assertEqual([k for k in _overrides(self.buttons[0]) if k.endswith("_icon")], [])
        self.assertNotIn("@", _loc()["te_market_tab_strategic_reserve"])

    def test_the_label_fits_one_of_six_slots(self):
        word = _loc()["te_market_tab_strategic_reserve"]
        self.assertLessEqual(len(word) * UPC["large"] * MARGIN, SIX_SLOT, word)

    def test_the_gates_read_the_entry(self):
        sguis = _read(TAB_SGUIS)
        gate = _body(sguis, r"(?m)^te_market_strategic_reserve_tab_sgui = \{")
        self.assertIn("is_shown = { has_journal_entry = je_strategic_reserve }", gate)
        unlock = _body(sguis, r"(?m)^te_market_strategic_reserve_tab_unlock_sgui = \{")
        self.assertIn("is_valid = { st_res_entry_unlocked = yes }", unlock)
        # No game rule: the tab is on the strip exactly when the greyed entry is in the journal.
        shown = re.search(r"is_shown = \{\s*(.*?)\s*\}", unlock).group(1)
        inactive = _body(_read(JE), r"is_shown_when_inactive = \{")
        self.assertEqual(" ".join(shown.split()), " ".join(inactive.split()))

    def test_the_checklist_is_the_entrys_own_test_in_one_line(self):
        trig = _body(_read(TRIGGERS), r"(?m)^st_res_entry_unlocked = \{")
        m = re.search(r"custom_tooltip = \{\s*text = st_res_entry_unlock_tt\s*(.*)\s*\}\s*$", trig, re.S)
        self.assertTrue(m, trig)
        possible = _body(_read(JE), r"possible = \{")
        self.assertEqual(" ".join(m.group(1).split()), " ".join(possible.split()))
        self.assertIn("$building_strategic_reserve_hub$", _loc()["st_res_entry_unlock_tt"])

    def test_what_the_journal_draws_besides_the_roots_needs_nothing_in_the_tab(self):
        """§5.1: no goal bar, no scripted bars, status text only without a hub
        (before the first one, or while the entry waits for a new one), and
        both scripted buttons the AI's."""
        je = _strip_comments(_read(JE))
        self.assertNotIn("progressbar", je)
        self.assertNotIn("scripted_progress_bar", je)
        status = _body(je, r"status_desc = \{")
        self.assertEqual(re.findall(r"desc = (\w+)", status), ["je_strategic_reserve_status_no_hub"])
        self.assertIn("building_strategic_reserve_hub", _body(status, r"trigger = \{"))
        names = re.findall(r"(?m)^\tscripted_button = (\w+)", je)
        self.assertEqual(len(names), 2)
        buttons = _read(BUTTONS)
        for name in names:
            self.assertRegex(_body(buttons, rf"(?m)^{name} = \{{"), r"visible = \{\s*is_ai = yes", name)

    def test_the_types_read_nothing_from_the_panel(self):
        """No section type reads the Market panel's ambient Market or Country."""
        ambient = re.findall(r"(?<![\w.'])(Market|Country|GetPlayer|GetMetaPlayer)\.\w+", _read(WIDGET))
        self.assertEqual(ambient, [])

    def test_one_visible_per_widget(self):
        for i, block in enumerate(self.buttons + self.content):
            stack = [0]
            for line in block.splitlines():
                s = line.strip()
                if s.startswith("visible ="):
                    stack[-1] += 1
                    self.assertLessEqual(stack[-1], 1, f"block {i}: two visibles near {s[:60]}")
                stack.extend([0] * line.count("{"))
                for _ in range(line.count("}")):
                    if len(stack) > 1:
                        stack.pop()


if __name__ == "__main__":
    unittest.main()
