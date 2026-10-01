"""Nothing a player reads on the Space Race panels ends in "..." (play-test round 3).

A fixed-width cell elides its text with "..." when the text is too long: the
owner's round-3 screenshot had "Next Colo..." in the progress row's 90-wide
label column. Every single-line cell of gui/journal_entry_widgets/
space_race_widget.gui is held here to a width budget measured from the owner's
screenshots: about 10 GUI units a character in the large font and 8.6 in the
medium, plus 10% margin. The small font has no screenshot yet; 8.0 is a
deliberately generous guess (its pixel size is below the medium's).

A label is measured as it renders: `$key$` splices resolved, `[concept_x]`
links replaced by the concept's name, formatting codes stripped. A label built
from script values is measured with the longest figure each value can print,
named in `_longest_figure` below and derived from the script where the script
bounds it. Multi-line text (the notes, the profile, the Rivals list) wraps
instead of eliding and is exempt.

The widths are read from the GUI, so narrowing a column fails here too.

A rival's name is the longest dynamic text: any country's name, vanilla's or
the mod's, dynamic names included. The longest today is 48 characters
("United Socialist Council Republics of California"), which is why the rival
row gives the name a line of its own.
"""
import glob
import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
VALUES = os.path.join(REPO, "common", "script_values", "space_race_values.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")
VANILLA_LOC = os.path.join(REPO, "vanilla_parsed", "localization_english.json")

UNITS_PER_CHAR = {"large": 10.0, "medium": 8.6, "small": 8.0}
MARGIN = 1.1

# The longest figures no script bounds: named here, as the round-3 rules ask.
PACE_CEILING = 99.9       # sr_pace_rate_<m>, "+99.9/mo"; the real pace is a few a month
SETBACKS_CEILING = 99     # sr_setbacks_<m>_value, a count of setbacks
FUNDING_CEILING = 10      # sr_funding_<m> and sr_max_funding_level: 3, plus technology
STAGE_CEILING = 5         # sr_current_colonization_stage, "Stage: 5 of 5"
TRANSIT_MONTHS = 132      # sr_interstellar_transit_value, pinned by the waiting entry's goal
WORLDS = 34               # sr_total_global_colonies, the 34 worlds; sr_disp_colonies_held is a share of them
SECTION_HEADER_WIDTH = 400  # the text of the 520-wide section_header_button, less its arrow


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
    raise AssertionError("unclosed block")


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    return text[m.end():_close(text, m.end() - 1)]


def _block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    assert m, f"{name} not found"
    return text[m.end():_close(text, m.end() - 1)]


def _textboxes(body):
    """Each `textbox = { ... }` in a stretch of GUI, in order."""
    out = []
    for m in re.finditer(r"\btextbox = \{", body):
        out.append(body[m.end():_close(body, m.end() - 1)])
    return out


def _textbox_with(body, marker):
    boxes = [b for b in _textboxes(body) if marker in b]
    assert len(boxes) == 1, f"{len(boxes)} textboxes hold {marker}"
    return boxes[0]


def _font(box):
    m = re.search(r"using = fontsize_(\w+)", box)
    assert m, "a fixed-width cell names its font"
    return m.group(1)


def _width(box):
    """The width a textbox elides at: max_width, maximumsize or a fixed size."""
    for pat in (r"max_width = (\d+)", r"maximumsize = \{ (\d+) -1 \}", r"\bsize = \{ (\d+) \d+ \}"):
        m = re.search(pat, box)
        if m:
            return int(m.group(1))
    raise AssertionError("a textbox with no fixed width")


_LOC = {}


def _loc(key):
    if not _LOC:
        for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
            for k, v in re.findall(r'^ ([\w.]+):\d* "(.*)"\s*$', _read(path), re.M):
                _LOC[k] = v
    assert key in _LOC, f"no loc {key}"
    return _LOC[key]


class _Script:
    """The bounds the script itself sets."""

    def __init__(self):
        values = _read(VALUES)
        self.per_level = float(re.search(r"(?m)^sr_innovation_per_cost_level = \{\s*value = ([\d.]+)",
                                         values).group(1))
        self.cost_factor = {m: float(v) for m, v in
                            re.findall(r"(?m)^sr_cost_factor_(\w+)\s*=\s*\{\s*value = ([\d.]+)\s*\}", values)}
        self.values = values
        cooldowns = []
        for sub in ("common", "events"):
            for path in glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True):
                cooldowns += [int(v) for v in
                              re.findall(r"name = sr_failure_cooldown value = (\d+)", _read(path))]
        self.cooldown = max(cooldowns)

    def goal(self, m):
        """The goal at its largest: the base plus every stage's addition."""
        body = _block(self.values, f"sr_{m}_goal")
        base = float(re.search(r"^\s*(?:#[^\n]*\n\s*)*value = ([\d.]+)", body).group(1))
        return base + sum(float(v) for v in re.findall(r"\badd = ([\d.]+)", body))

    def pace_floor(self, m):
        return float(re.search(r"min = ([\d.]+)", _block(self.values, f"sr_pace_rate_{m}")).group(1))

    def risk_ceiling(self, m):
        return float(re.search(r"max = ([\d.]+)", _block(self.values, f"sr_risk_pct_{m}")).group(1))


SCRIPT = None
_COUNTRY = []


def _longest_country_name():
    """The longest name a country can carry: every tag's name and every
    dynamic name (dyn_c_*), vanilla's (the committed parse) and the mod's."""
    if not _COUNTRY:
        with open(VANILLA_LOC, encoding="utf-8") as f:
            names = dict(json.load(f))
        _loc("concept_sr_approach")  # fills _LOC with the mod's keys
        names.update(_LOC)
        plain = [v for k, v in names.items()
                 if isinstance(v, str) and (re.fullmatch(r"[A-Z][A-Z0-9]{2}", k) or re.fullmatch(r"dyn_c_\w+", k))
                 and not re.search(r"[$\[#]", v)]
        _COUNTRY.append(max(plain, key=len))
    return _COUNTRY[0]


def _longest_figure(name):
    """The largest number the script value `name` can print."""
    global SCRIPT
    SCRIPT = SCRIPT or _Script()
    if m := re.fullmatch(r"sr_disp_cost_(safe|ambitious)_(\w+)", name):
        return SCRIPT.per_level * SCRIPT.cost_factor[m.group(2)] * (2 if m.group(1) == "ambitious" else 1)
    if m := re.fullmatch(r"sr_progress_(\w+)_value", name):
        return SCRIPT.goal(m.group(1))
    if m := re.fullmatch(r"sr_(\w+)_goal", name):
        return SCRIPT.goal(m.group(1))
    if m := re.fullmatch(r"sr_eta_months_(\w+)", name):
        return SCRIPT.goal(m.group(1)) / SCRIPT.pace_floor(m.group(1))
    if re.fullmatch(r"sr_pace_rate_\w+", name):
        return PACE_CEILING
    if m := re.fullmatch(r"sr_risk_shown_(\w+)", name):
        return SCRIPT.risk_ceiling(m.group(1))
    if re.fullmatch(r"sr_setbacks_\w+_value", name):
        return SETBACKS_CEILING
    if re.fullmatch(r"sr_funding_\w+|sr_max_funding_level", name):
        return FUNDING_CEILING
    if re.fullmatch(r"sr_disp_rival_(lo|hi|est)_\w+", name):
        return 1.0  # a share of the goal, clamped to 0..1: "100%"
    fixed = {"sr_disp_cooldown_months": SCRIPT.cooldown, "sr_current_colonization_stage": STAGE_CEILING,
             "sr_interstellar_transit_value": TRANSIT_MONTHS, "sr_total_global_colonies": WORLDS,
             "sr_disp_colonies_held": WORLDS}
    assert name in fixed, f"no longest figure known for {name}: add one to _longest_figure"
    return fixed[name]


def _render(value):
    """The loc value as the player reads it, every figure at its longest."""
    for _ in range(5):
        value = re.sub(r"\$(\w+)\$", lambda m: _loc(m.group(1)), value)

    def figure(m):
        name, pct, fmt = m.group(1) or m.group(2), m.group(3), m.group(4)
        assert fmt is not None, f"a figure with no format: {m.group(0)}"
        if pct:
            return f"{_longest_figure(name) * 100:.{int(fmt)}f}%"
        return f"{_longest_figure(name):.{int(fmt)}f}"

    value = re.sub(r"\[[^\[\]]*?(?:ScriptValue\('(\w+)'\)|Var\('(\w+)'\)\.GetValue)(?:\|(%?)(\d))?\]",
                   figure, value)
    value = value.replace("[State.GetCountry.GetName]", _longest_country_name())
    value = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", value)
    value = re.sub(r"\[(concept_\w+)\]", lambda m: _loc(m.group(1)), value)
    assert "[" not in value, f"an unmeasured expression in {value!r}"
    value = re.sub(r"#[A-Za-z_;]+ ", "", value)
    return value.replace("#!", "")


# Every loc key the panel shows, by the cell it shows in. Keys in more than one
# cell are measured against each.
MULTILINE = r"je_space_race_widget_(how_\w+|profile_\w+|rival_more_\w+|colonies_empty)"
CELLS = {
    # (type, marker picking the textbox): patterns of the keys it shows
    "state, risk, first and stage (te_sr_ov_icon_label)": (
        ("te_sr_ov_icon_label", 'block "label"'),
        r"je_space_race_widget_(ov_idle|standard_label|ov_safe_\w+|ov_ambitious_\w+|ov_shielded|risk_\w+"
        r"|ov_first_open|ov_first_claimed|ov_stage)"),
    "approach buttons (te_sr_action_button)": (
        ("te_sr_action_button", 'block "action_label"'),
        r"je_space_race_widget_(standard_label|safe_label|ambitious_label)"),
    "progress label (te_sr_ov_bar_row)": (
        ("te_sr_ov_bar_row", 'block "bar_label"'),
        r"je_space_race_widget_(ov_progress_label|ov_colony_label|ov_transit_label)"),
    "progress headline (te_sr_ov_bar_row)": (
        ("te_sr_ov_bar_row", 'block "bar_text"'),
        r"je_space_race_widget_progress_\w+"),
    "value-row label (te_sr_value_row)": (
        ("te_sr_value_row", 'block "row_label"'),
        r"je_space_race_widget_(setbacks_label|eta_label|colonies_held_label)"),
    "value-row figure (te_sr_value_row)": (
        ("te_sr_value_row", 'block "row_value"'),
        r"je_space_race_widget_((setbacks|eta)_(?!label)\w+|colonies_held_figure)"),
    "approach label (te_sr_sec_control)": (
        ("te_sr_sec_control", 'text = "je_space_race_widget_approach_label"'),
        r"je_space_race_widget_approach_label"),
    "funding label (te_sr_sec_control)": (
        ("te_sr_sec_control", 'text = "je_space_race_widget_funding_label"'),
        r"je_space_race_widget_funding_label"),
    "funding figure (te_sr_sec_control)": (
        ("te_sr_sec_control", 'block "funding_value"'),
        r"je_space_race_widget_funding_(?!label)\w+"),
    "worlds pie label (te_sr_ov_pie)": (
        ("te_sr_ov_pie", 'block "pie_label"'),
        r"je_space_race_widget_ov_worlds"),
    "rival name (te_sr_rival_row)": (
        ("te_sr_rival_row", 'text = "je_space_race_widget_rival_name"'),
        r"je_space_race_widget_rival_name"),
    "rival band in words (te_sr_rival_row)": (
        ("te_sr_rival_row", 'block "row_range"'),
        r"je_space_race_widget_rival_range_\w+"),
    "colony stage heading (te_sr_subheader)": (
        ("te_sr_subheader", 'block "subheader_text"'),
        r"je_space_race_widget_colonies_stage_\d"),
    "programme label (te_sr_ov_programme)": (
        ("te_sr_ov_programme", 'text = "je_space_race_widget_programme_header"'),
        r"je_space_race_widget_programme_header"),
}
SECTION_HEADERS = r"je_space_race_widget_(control_header|rivals_header|colonies_header|how_header)"


def _cell(gui, type_name, marker):
    box = _textbox_with(_type_body(gui, type_name), marker)
    if type_name == "te_sr_ov_pie":  # the label is as wide as the pie's widget
        return int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(gui, type_name)).group(1)), _font(box)
    if type_name == "te_sr_ov_programme":  # centred in the 480 column
        return 480, _font(box) if "using" in box else "medium"
    return _width(box), _font(box)


def _shown_keys(gui):
    """Every loc key the GUI shows as a textbox's text, with the value-driven
    keys the roots pass in (sr_label_safe, sr_risk_label, sr_progress_text …)."""
    return sorted(set(re.findall(r'\btext = "(je_space_race_widget_\w+)"', gui)))


class LabelBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(GUI)
        cls.keys = _shown_keys(cls.gui)

    def _fits(self, key, width, font):
        text = _render(_loc(key))
        self.assertNotIn("\\n", text, f"{key} is one line in a fixed-width cell")
        need = len(text) * UNITS_PER_CHAR[font] * MARGIN
        self.assertLessEqual(need, width, f"{key} renders {text!r}: {need:.0f} units in a {width}-wide cell")

    def test_every_single_line_label_fits_its_cell(self):
        for cell, ((type_name, marker), pattern) in CELLS.items():
            width, font = _cell(self.gui, type_name, marker)
            keys = [k for k in self.keys if re.fullmatch(pattern, k)]
            self.assertTrue(keys, f"no keys for {cell}")
            for key in keys:
                with self.subTest(cell=cell, key=key):
                    self._fits(key, width, font)

    def test_section_headers_fit(self):
        for key in (k for k in self.keys if re.fullmatch(SECTION_HEADERS, k)):
            with self.subTest(key=key):
                self._fits(key, SECTION_HEADER_WIDTH, "large")

    def test_every_key_is_measured_or_wraps(self):
        """A new label must join a cell above, or be multi-line text."""
        patterns = [p for _, p in CELLS.values()] + [SECTION_HEADERS, MULTILINE]
        for key in self.keys:
            with self.subTest(key=key):
                self.assertTrue(any(re.fullmatch(p, key) for p in patterns), f"{key} is in no cell")

    def test_the_longest_figures(self):
        """The budget's worst cases, spelled out: a change to the goals, the
        costs or the pace floor that lengthens one fails the cell test above."""
        self.assertEqual(_render(_loc("je_space_race_widget_ov_ambitious_interstellar_probe")), "Ambitious −360/wk")
        self.assertEqual(_render(_loc("je_space_race_widget_ov_safe_orbital")), "Safe −22.5/wk")
        self.assertEqual(_render(_loc("je_space_race_widget_progress_solar_colonization")), "650 / 650 (+99.9/mo)")
        self.assertEqual(_render(_loc("je_space_race_widget_eta_solar_colonization")), "1300 months")
        self.assertEqual(_render(_loc("je_space_race_widget_progress_interstellar_results")), "132 / 132 months")
        self.assertEqual(_render(_loc("je_space_race_widget_ov_shielded")), "Shielded: 6 mo")
        self.assertEqual(_render(_loc("je_space_race_widget_risk_mars_landing")), "Risk: 50%/mo")
        self.assertEqual(_render(_loc("je_space_race_widget_ov_colony_label")), "Next Colony")
        self.assertEqual(_render(_loc("je_space_race_widget_approach_label")), "Approach")
        self.assertEqual(_render(_loc("je_space_race_widget_funding_label")), "Funding")
        self.assertEqual(_longest_country_name(), "United Socialist Council Republics of California")
        self.assertEqual(_render(_loc("je_space_race_widget_rival_range_mars_landing")), "100%–100%")

    def test_the_owners_overrun_is_caught(self):
        """The budget flags what the owner saw: "Next Colony" in the old 90."""
        need = len("Next Colony") * UNITS_PER_CHAR["medium"] * MARGIN
        self.assertGreater(need, 90)


if __name__ == "__main__":
    unittest.main()
