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
CONCEPTS = os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

STATUS = ["te_st_res_sec_inventory"]
REFERENCE = ["te_st_res_sec_how"]
ROOTS = {"widget_je_strategic_reserve_overview": ("custom_widget_container_1", "te_st_res_overview_panel"),
         "widget_je_strategic_reserve_inventory": ("custom_widget_container_2", "te_st_res_status_sections"),
         "widget_je_strategic_reserve_reference": ("custom_widget_container_3", "te_st_res_reference_sections")}
# The keys the panel used before the pass; a survivor means a half-renamed flag.
OLD_FLAGS = ["st_res_row_expanded_", "st_res_policy_open_"]
HOW_TOPICS = ["hub", "rates", "status", "decay", "policies", "presets", "income"]
# Per-good loc keys a row reads; the skill's file 14 lists the same set.
ROW_LOC = ["name", "status", "tooltip", "amount", "flow", "last", "decay", "price", "policy", "policy_reason"]
DISPLAY_VALUES = ["disp_policy", "disp_target", "disp_floor"]


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

    def test_status_text_keeps_only_the_hub_line(self):
        je = _read(JE)
        status = _body(je, r"status_desc = \{")
        self.assertNotIn("je_strategic_reserve_profit_line", status)
        self.assertNotIn("je_strategic_reserve_rate_line", status)
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


if __name__ == "__main__":
    unittest.main()
