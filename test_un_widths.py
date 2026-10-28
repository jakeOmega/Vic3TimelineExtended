# -*- coding: utf-8 -*-
"""The UN's text fits the boxes it is drawn in, at the house type sizes.

The 2026-10-27 GUI audit's UN-18 (owner decision of the same day): the UN
panels use the house ladder through templates of their own at the head of
``un_chamber_widget.gui`` (``un_fontsize_row`` 17 for rows, values, buttons
and notes, ``un_fontsize_heading`` 20 for subheadings, ``un_fontsize_overview``
16 in the tooltip face for the overview), and every fixed box was re-budgeted
for them. An elided label is engine-silent, so these tests hold each label to
its box by the guide's rule of thumb (gui_style_guide.md rule 3, and
test_banking_layout.WidthBudgetTest, whose model this is): half a unit per
point per character in the serif face, 8.6 a character at 16 in the tooltip
face, plus 10%.

Run: python3 -m unittest test_un_widths -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets")
CHAMBER = os.path.join(GUI, "un_chamber_widget.gui")
OVERVIEW = os.path.join(GUI, "un_overview_widget.gui")
LAYOUT = os.path.join(GUI, "un_layout_widget.gui")
AUTHORITY = os.path.join(GUI, "un_authority_widget.gui")
LOC = os.path.join(REPO, "localization", "english")

SIZES = {"row": 17, "heading": 20, "overview": 16}
UNITS = {"row": 10.0 / 20 * SIZES["row"], "heading": 10.0 / 20 * SIZES["heading"],
         "overview": 8.6 / 16 * SIZES["overview"]}
MARGIN = 1.1
# The longest a number in a label reaches: a month count, a score or a
# percentage ("100"), a strength ("1.30") or a share with a decimal.
NUMBER = "100"


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _loc():
    out = {}
    for name in os.listdir(LOC):
        if name.endswith(".yml"):
            with open(os.path.join(LOC, name), encoding="utf-8-sig") as f:
                for line in f:
                    m = re.match(r'^ ([\w.\-]+):\d* "(.*)"\s*$', line)
                    if m:
                        out[m.group(1)] = m.group(2)
    return out


def _block(text, start):
    j = text.index("{", start)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j + 1:k]
    raise AssertionError("unbalanced block")


def _type(text, name):
    m = re.search(rf"\ttype {re.escape(name)} = \w+ \{{", text)
    assert m, f"no type {name}"
    return _block(text, m.end() - 1)


def _instances(text, name):
    return [_block(text, m.end() - 1) for m in re.finditer(rf"\b{re.escape(name)} = \{{", text)]


class WidthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = _loc()
        cls.chamber = _read(CHAMBER)
        cls.overview = _read(OVERVIEW)
        cls.all = "\n".join(_read(p) for p in (CHAMBER, OVERVIEW, LAYOUT, AUTHORITY))

    def shown(self, key, depth=0):
        """The widest text the key can show: splices and concepts resolved,
        a SelectLocalization at its longest choice, formatting stripped and
        any other data read as NUMBER."""
        self.assertLess(depth, 8, key)
        v = self.loc.get(key)
        self.assertIsNotNone(v, key)
        v = re.sub(r"\$(\w+)\$", lambda m: self.shown(m.group(1), depth + 1), v)
        v = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", v)
        v = re.sub(r"\[(concept_\w+)\]", lambda m: self.shown(m.group(1), depth + 1), v)

        def choice(m):
            keys = re.findall(r"'(je_\w+)'", m.group(0))
            return max((self.shown(k, depth + 1) for k in keys), key=len)
        v = re.sub(r"\[SelectLocalization\(.*?\)\]", choice, v)
        v = re.sub(r"\[[^\[\]]*\]", NUMBER, v)
        v = re.sub(r"#[A-Za-z_]+(?:;\S*)? ", "", v).replace("#!", "")
        # An inline icon (@money!) is about two characters wide.
        v = re.sub(r"@\w+!", "..", v)
        return v.replace("\\n", "")

    def fits(self, key, width, font):
        text = self.shown(key)
        need = len(text) * UNITS[font] * MARGIN
        self.assertLessEqual(need, width, f"{key} shows {text!r}: {need:.0f} units in a {width} {font} box")

    def test_the_templates_are_the_house_sizes(self):
        for name, size in SIZES.items():
            body = _block(self.chamber, self.chamber.index(f"template un_fontsize_{name} {{"))
            with self.subTest(template=name):
                self.assertIn(f"fontsize = {size}", body)
        self.assertIn("using = tooltip_font", _block(self.chamber, self.chamber.index("template un_fontsize_overview {")))
        # No UN panel uses the vanilla ladder's sizes any more.
        self.assertNotRegex(self.all, r"using = fontsize_(small|medium|large|big|xl)\b")

    def test_the_overview_cells(self):
        # te_banking_ov_cell's caption and word column: 154 at 16 (Banking's
        # own type, used as it is).
        keys = set()
        for m in re.finditer(r'blockoverride "caption" \{', self.overview):
            keys.update(re.findall(r'text = "(je_\w+)"', _block(self.overview, m.end() - 1)))
        for body in _instances(self.overview, "te_banking_ov_word"):
            keys.update(re.findall(r'text = "(je_\w+)"', body))
        self.assertGreaterEqual(len(keys), 30)
        for key in sorted(keys):
            with self.subTest(key=key):
                self.fits(key, 154, "overview")

    def test_the_controls(self):
        # un_act_control: 226 unless the instance narrows it.
        default = int(re.search(r'block "act_label_width" \{\s*max_width = (\d+)', _type(self.chamber, "un_act_control")).group(1))
        self.assertEqual(default, 226)
        seen = 0
        for body in _instances(self.all, "un_act_control"):
            width = re.search(r'blockoverride "act_label_width" \{\s*max_width = (\d+)', body)
            size = re.search(r'blockoverride "act_size" \{\s*size = \{ (\d+) \d+ \}', body)
            if width and size:
                self.assertLessEqual(int(width.group(1)), int(size.group(1)) - 6)
            for key in re.findall(r'blockoverride "act_label" \{\s*text = "(je_\w+)"', body):
                seen += 1
                with self.subTest(key=key):
                    self.fits(key, int(width.group(1)) if width else default, "row")
            for keys in re.findall(r'blockoverride "act_label" \{\s*text = "\[SelectLocalization\((.*?)\)\]"', body):
                for key in re.findall(r"'(je_\w+)'", keys):
                    seen += 1
                    with self.subTest(key=key):
                        self.fits(key, int(width.group(1)) if width else default, "row")
        self.assertGreaterEqual(seen, 22)

    def test_the_fixed_buttons(self):
        for typ, block, width in (("un_chamber_action_button", "action_label", 226),
                                  ("un_chamber_deleg_button", "action_label", 74),
                                  ("un_chamber_deleg_stop_button", "action_label", 158),
                                  ("un_chamber_deleg_bulk_button", "action_label", 104)):
            body = _type(self.chamber, typ)
            self.assertIn(f"max_width = {width}", body, typ)
            self.assertIn("using = un_fontsize_row", body, typ)
            keys = set()
            for inst in _instances(self.all, typ):
                keys.update(re.findall(rf'blockoverride "{block}" \{{\s*text = "(je_\w+)"', inst))
            self.assertTrue(keys, typ)
            for key in sorted(keys):
                with self.subTest(button=typ, key=key):
                    self.fits(key, width, "row")
        for typ, keys, width in (("un_chamber_propose_row", ["je_un_chamber_propose_button_label"], 120),
                                 ("un_chamber_mission_row", ["je_un_chamber_mission_join_label",
                                                             "je_un_chamber_mission_withdraw_label"], 226)):
            body = _type(self.chamber, typ)
            self.assertIn(f"max_width = {width}", body, typ)
            for key in keys:
                with self.subTest(row=typ, key=key):
                    self.assertIn(f'text = "{key}"', body)
                    self.fits(key, width, "row")

    def test_the_value_rows(self):
        # un_chamber_value_row: a 360 label and a 100 value, single lines.
        body = _type(self.chamber, "un_chamber_value_row")
        self.assertIn("maximumsize = { 360 -1 }", body)
        self.assertIn("maximumsize = { 100 -1 }", body)
        seen = 0
        for inst in _instances(self.all, "un_chamber_value_row"):
            for block, width in (("row_label", 360), ("row_value", 100)):
                for key in re.findall(rf'blockoverride "{block}" \{{\s*text = "(je_\w+)"', inst):
                    seen += 1
                    with self.subTest(block=block, key=key):
                        self.fits(key, width, "row")
        self.assertGreaterEqual(seen, 10)

    def test_single_line_boxes(self):
        # Every fixed-width single-line box with a literal label: the pillar
        # table's labels, the programme rows' columns and the like.
        seen = 0
        for m in re.finditer(r"\btextbox = \{", self.all):
            box = _block(self.all, m.end() - 1)
            if "multiline = yes" in box or "using = un_fontsize_" not in box:
                continue
            width = re.search(r"maximumsize = \{ (\d+) -1 \}", box) or re.search(r"max_width = (\d+)", box)
            text = re.search(r'\btext = "(je_\w+)"', box)
            if not (width and text):
                continue
            font = re.search(r"using = un_fontsize_(\w+)", box).group(1)
            seen += 1
            with self.subTest(key=text.group(1)):
                self.fits(text.group(1), int(width.group(1)), font)
        self.assertGreaterEqual(seen, 15)

    def test_the_delegation_words(self):
        for key, width in (("je_un_chamber_deleg_lobby_word", 56), ("je_un_chamber_deleg_pledge_word", 64)):
            with self.subTest(key=key):
                self.assertRegex(self.chamber, rf"max_width = {width}\s*text = \"{key}\"")
                self.fits(key, width, "row")


if __name__ == "__main__":
    unittest.main()
