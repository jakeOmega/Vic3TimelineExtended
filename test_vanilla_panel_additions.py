"""The mod's additions to vanilla panels (GUI audit 2026-10-27, slice VAN).

- The construction market's read-out is a label/value table (VAN-2) whose
  labels and values fit their columns at the panel's body font.
- A state-view row with a hover of its own underlines its label, and a row
  without one does not (VAN-10, gui_style_guide.md rule 3).
- The Homeland Dynamics tile shows only where a homeland can change (VAN-6c,
  owner decision 2026-10-27).
- Civil Rights' status names the ending the movement would reach now (JE-4),
  through script values that mirror the entry's on_complete and on_fail.
- Heir Education's skill buttons preview the innovation cost each advance
  applies, at the duration the advance applies it for (JE-5).
"""

import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
CONSTRUCTION = os.path.join(REPO, "gui", "construction_panel.gui")
STATES = os.path.join(REPO, "gui", "states_panel.gui")
WIDGETS = os.path.join(REPO, "gui", "te_state_panel_widgets.gui")
LOC_DIR = os.path.join(REPO, "localization", "english")
CIVIL_RIGHTS = os.path.join(REPO, "common", "journal_entries", "je_civil_rights.txt")
CR_VALUES = os.path.join(REPO, "common", "script_values", "civil_rights_values.txt")
HE_BUTTONS = os.path.join(REPO, "common", "scripted_buttons", "heir_education_buttons.txt")
HE_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "heir_education_effects.txt")

# gui_style_guide.md rule 3: the serif body face runs about 10 units a
# character at 20, so 8.5 at the 17 of this panel's body text, plus 10%.
UNITS_17 = 8.5
MARGIN = 1.1
# The widest a number in these rows prints: a quantity with one decimal and a
# thousands separator, a sum at |1* ("123.4M"), a share at "100%".
QUANTITY = "12,345.6"
MONEY = "123.4M"
ICON = 20  # an @money! icon, in units


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _block_from(text, start):
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


def _loc():
    with open(os.path.join(REPO, "vanilla_parsed", "localization_english.json"), encoding="utf-8") as f:
        keys = dict(json.load(f))
    for name in sorted(os.listdir(LOC_DIR)):
        if name.endswith(".yml"):
            for line in _read(os.path.join(LOC_DIR, name)).splitlines():
                m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"\s*$', line)
                if m:
                    keys[m.group(1)] = m.group(2)
    return keys


def _instances(text, type_names):
    """(type, body) of every instance `<type> = {` of the named types."""
    pattern = re.compile(r"(?m)^\t+(%s) = \{" % "|".join(type_names))
    return [(m.group(1), _block_from(text, m.end() - 1)) for m in pattern.finditer(text)]


class ConstructionMarketTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _read(CONSTRUCTION)
        cls.loc = _loc()
        m = re.search(r"type te_cm_stat_row = te_state_stat_row \{", cls.text)
        cls.assertTrue(cls, m)
        cls.row_type = _block_from(cls.text, m.end() - 1)

    def column(self, block):
        body = re.search(r'blockoverride "%s" \{\s*max_width = (\d+)' % block, self.row_type)
        self.assertIsNotNone(body, block)
        return int(body.group(1))

    def shown(self, key):
        v = self.loc[key]
        v = re.sub(r"\[SelectLocalization\([^\]]*'(\w+)', '' \)\]", lambda m: self.loc[m.group(1)], v)
        icons = len(re.findall(r"@\w+!", v))
        v = re.sub(r"\[[^\[\]]*\|1\*\]", MONEY, v)
        v = re.sub(r"\[[^\[\]]*\|0\]#?!?%", "100%", v)
        v = re.sub(r"\[[^\[\]]*\]", QUANTITY, v)
        v = re.sub(r"#[A-Za-z_]+(?:;\S*)? ", "", v).replace("#!", "")
        v = re.sub(r"@\w+!", "", v)
        return v, icons

    def test_rows_are_the_table(self):
        rows = _instances(self.text, ["te_cm_stat_row"])
        self.assertEqual(len(rows), 6)
        self.assertNotRegex(self.text, r'text = "TE_CM_STAT_\w+"\s*tooltip')
        # The panel's own body font: the row type sets no fontsize template.
        self.assertRegex(self.row_type, r'blockoverride "row_font" \{\}')
        self.assertIn('default_format = "#tooltippable"', self.row_type)
        for _, body in rows:
            label = re.search(r'blockoverride "row_label" \{\s*text = "(\w+)"', body).group(1)
            with self.subTest(row=label):
                self.assertIn('tooltip = "%s_TT"' % label, body)
                self.assertIn('text = "%s_VALUE"' % label, body)
                self.assertIn(label + "_TT", self.loc)

    def test_labels_and_values_fit(self):
        label_width = self.column("label_max_width")
        value_width = self.column("value_max_width")
        for _, body in _instances(self.text, ["te_cm_stat_row"]):
            label = re.search(r'blockoverride "row_label" \{\s*text = "(\w+)"', body).group(1)
            for key, width in ((label, label_width), (label + "_VALUE", value_width)):
                text, icons = self.shown(key)
                need = len(text) * UNITS_17 * MARGIN + icons * ICON
                with self.subTest(key=key):
                    self.assertLessEqual(need, width, f"{key} shows {text!r}: {need:.0f} units in {width}")


class StateRowUnderlineTest(unittest.TestCase):
    ROWS = ["te_state_stat_row", "te_state_tile_row", "te_state_tile_word_row", "te_state_wide_row", "te_state_gm_row"]

    def rows(self):
        for path in (STATES, WIDGETS):
            text = _read(path)
            meters = [_block_from(text, m.end() - 1) for m in re.finditer(r"(?m)^\t+te_state_meter = \{", text)]
            for kind, body in _instances(text, self.ROWS):
                in_meter = any(body in meter for meter in meters)
                yield os.path.basename(path), kind, body, in_meter

    def test_a_row_with_its_own_hover_is_underlined(self):
        seen = 0
        for name, kind, body, in_meter in self.rows():
            own_hover = 'blockoverride "row_tooltip"' in body or in_meter
            underlined = re.search(r'blockoverride "label_format" \{\s*default_format = "#tooltippable"', body)
            # The homeland project row's hover is its own label (the culture's
            # name, which can elide), not a hover of its own to find.
            if "te_homeland_project_culture_sgui" in body:
                self.assertIsNone(underlined)
                continue
            with self.subTest(file=name, row=body[:160]):
                self.assertEqual(bool(underlined), own_hover)
            seen += own_hover
        self.assertGreaterEqual(seen, 25)

    def test_the_row_type_leaves_the_label_plain(self):
        text = _read(WIDGETS)
        m = re.search(r"type te_state_stat_row = flowcontainer \{", text)
        body = _block_from(text, m.end() - 1)
        self.assertIn('block "label_format" {}', body)


class HomelandTileTest(unittest.TestCase):
    def test_hidden_where_nothing_can_change(self):
        text = _read(STATES)
        at = text.index('tooltip = "TE_STATE_HOMELAND_TT"')
        tile = text[text.rindex("state_panel_status_item_small = {", 0, at):at]
        self.assertIn("te_homeland_relevant", tile)
        self.assertIn("visible", tile)
        self.assertNotIn("TE_HOMELAND_NOTHING_TO_CHANGE", _read(WIDGETS))

    def test_one_unit_for_the_rate(self):
        loc = _loc()
        for key in ("TE_STATE_HOMELAND_TT", "TE_HOMELAND_TRACK_ACTIVE", "TE_HOMELAND_REMOVAL_TRACK_ACTIVE"):
            with self.subTest(key=key):
                self.assertIn("a year", loc[key])
                self.assertNotIn("points", loc[key])


class CivilRightsEndingMirrorTest(unittest.TestCase):
    """cr_win_ending_now / cr_fail_ending_now take the branches of on_complete
    / on_fail in the same order, over the display copies of the counters."""

    @staticmethod
    def limits(block):
        out = []
        for m in re.finditer(r"limit = \{", block):
            body = _block_from(block, m.start())[1:-1]
            out.append(" ".join(body.split()))
        return out

    def check(self, dispatcher, value):
        je = _read(CIVIL_RIGHTS)
        m = re.search(r"(?m)^\t%s = \{" % dispatcher, je)
        script = self.limits(_block_from(je, m.end() - 1))
        values = _read(CR_VALUES)
        m = re.search(r"(?m)^%s = \{" % value, values)
        mirror = self.limits(_block_from(values, m.end() - 1))
        script = [re.sub(r"var:cr_(\w+?)_months", r"cr_months_disp_\1", s) for s in script]
        self.assertEqual(mirror, script)

    def test_win(self):
        self.check("on_complete", "cr_win_ending_now")

    def test_fail(self):
        self.check("on_fail", "cr_fail_ending_now")


class HeirEducationCostPreviewTest(unittest.TestCase):
    def test_each_skill_button_previews_its_advance_cost(self):
        buttons = _read(HE_BUTTONS)
        effects = _read(HE_EFFECTS)
        for skill in ("admin", "diplo", "military"):
            with self.subTest(skill=skill):
                m = re.search(r"(?m)^heir_ed_gain_%s = \{" % skill, effects)
                gain = _block_from(effects, m.end() - 1)
                applied = re.search(r"add_modifier = \{ name = heir_education_innovation_cost days = (\d+) \}", gain)
                m = re.search(r"(?m)^he_enable_%s_focus = \{" % skill, buttons)
                button = _block_from(buttons, m.end() - 1)
                shown = re.search(r"show_as_tooltip = \{\s*add_modifier = \{ name = heir_education_innovation_cost days = (\d+) \}", button)
                self.assertIsNotNone(applied)
                self.assertIsNotNone(shown)
                self.assertEqual(shown.group(1), applied.group(1))
                self.assertIn("custom_tooltip = HE_SKILL_ADVANCE_COST_TT", button)


if __name__ == "__main__":
    unittest.main()
