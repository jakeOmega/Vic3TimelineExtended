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
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "space_race_widget.gui")
# The per-world and per-slot rows (gen_solar_sites.py) pass keys into the row
# types above, so their keys are measured against those types' cells.
ROWS = os.path.join(REPO, "gui", "journal_entry_widgets", "sr_sites_generated_rows.gui")
FLEET_ROWS = os.path.join(REPO, "gui", "journal_entry_widgets", "sr_fleets_generated_rows.gui")  # gen_space_fleets.py
WINDOWS = os.path.join(REPO, "gui", "sr_launch_window_widgets.gui")  # Next Windows (colony management design § 6)
VALUES = os.path.join(REPO, "common", "script_values", "space_race_values.txt")
SITES_VALUES = os.path.join(REPO, "common", "script_values", "sr_sites_generated.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")
# Banking's overview cell, which the colonization overview's cells reuse (audit SPC-6).
BANKING = os.path.join(REPO, "gui", "journal_entry_widgets", "banking_dashboard_widget.gui")
CUSTOM_LOC_DIR = os.path.join(REPO, "common", "customizable_localization")
VANILLA_LOC = os.path.join(REPO, "vanilla_parsed", "localization_english.json")

UNITS_PER_CHAR = {"large": 10.0, "medium": 8.6, "small": 8.0}
# The panel's own sizes (te_sr_fontsize_* at the head of the widget file; audit
# SPC-11), scaled as test_banking_layout.py scales Banking's: the serif face at
# 10 a character in 20, the overview's tooltip face at 8.6 in 16.
with open(GUI, encoding="utf-8-sig") as _f:
    _SIZES = {m.group(1): int(m.group(2)) for m in re.finditer(
        r"template te_sr_fontsize_(\w+) \{\s*fontsize = (\d+)", _f.read())}
UNITS_PER_CHAR.update(row=10.0 / 20 * _SIZES["row"], heading=10.0 / 20 * _SIZES["heading"],
                      overview=8.6 / 16 * _SIZES["overview"])
MARGIN = 1.1

# The longest figures no script bounds: named here, as the round-3 rules ask.
PACE_CEILING = 99.9       # sr_pace_rate_<m>, "+99.9/mo"; the real pace is a few a month
SETBACKS_CEILING = 99     # sr_setbacks_<m>_value, a count of setbacks
FUNDING_CEILING = 99      # sr_funding_<m> and sr_max_funding_level: 3 plus every country_space_race_max_funding_add
                          # source (technologies, Advanced Research V), plus 6 past the cap; two digits however they grow
FUNDING_PAST_CAP = sum(1 / (j + 1) for j in range(1, 7))  # sr_funding_<m>_past_cap_effective: 1/2 + ... + 1/7, "+1.6"
STAGE_CEILING = 5         # sr_current_colonization_stage, "Stage: 5 of 5"
TRANSIT_MONTHS = 132      # sr_interstellar_transit_value, pinned by the waiting entry's goal
WORLDS = 40               # sr_total_global_colonies, the 40 worlds; sr_disp_colonies_held is a share of them
SECTION_HEADER_WIDTH = 400  # the text of the 520-wide section_header_button, less its arrow
FLEET_SLOTS = 6           # sr_disp_cf_in_flight, "6 of 6": gen_solar_sites.FLEET_SLOTS
SETTLERS_A_MONTH = 2000   # sr_disp_emig_per_month at High (sr_emig_level_batches 4 x sr_emig_batch_people 500)
OFFWORLD_PEOPLE = 9_999_999  # sr_disp_offworld_pop: the rooms' sum is 945,000 before modules; seven digits
TRANSIT_CEILING = 999     # sr_disp_cf_slot_<n>_months: the longest transit is 611 (chemical, the Kuiper Belt)
END_YEAR = 2136           # sr_disp_cf_slot_<n>_year: END_DATE's year
FAB_RATE_CEILING = 99.9   # sr_disp_fab_rate: the best method gives 25 a month; technology could add more
FAB_STOCK = 200           # sr_disp_fab_stock: sr_mod_fab_stock_cap
SHIP_SLOTS = 8            # sr_disp_ms_waiting / _flying: gen_solar_sites.SHIP_SLOTS
UPKEEP_CEILING = 999      # sr_disp_mod_upkeep_pct: a level past the first per module, 40 worlds x 7 at most
EBASE_LEVELS = 99_999     # sr_disp_ebase_levels / _room: 4,335 levels of room before Mining Complexes, 26,535 with every slot one; five digits
FREE_WORLDS = 40          # sr_disp_free_supplied_count: at most every world
FREE_TRADE_RESEARCH = 5   # sr_disp_free_trade_research: sr_free_trade_max_units (5) x 1%
SC_RATE_CEILING = 99.9    # sr_disp_sc_rate: 2 a level a month at most; ten levels for an AI, more for a player
FLEET_STRENGTH = 99_999   # sr_disp_fl_strength / _full: every fleet's, unbounded by script; five digits
FLEET_UPKEEP_PCT = 9999   # sr_disp_sc_upkeep_pct: full strength / 10 (sr_fleet_upkeep_points)
MIX_WEIGHT = 3            # sr_disp_sc_mix_<role>: sr_sc_mix_max
QUEUE_PLACES = 20         # sr_disp_mq_count: gen_solar_sites.QUEUE_SLOTS
WINDOW_MONTHS = 999       # sr_window_disp_next: capped at 999 (the cell reads "No site left" there)
WINDOW_WAIT = 99          # sr_window_wait_months_<body>: the longest wait is Mars's synodic period, 26 months
WINDOW_PREMIUM_SHOWN = 9.99  # sr_disp_win_premium_<body>: capped at +999% for its cell
WINDOW_DESTINATIONS = 14  # sr_disp_win_beyond: gen_solar_sites.WINDOW_ORDER


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
    m = re.search(r"using = (?:te_sr_|banking_dash_)?fontsize_(\w+)", box)
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
        # A factor that is not a constant (solar colonization's: 5, then 8 after the Mars
        # Landing) prints at most its base plus every addition.
        for m in re.findall(r"(?m)^sr_cost_factor_(\w+)\s*=\s*\{\s*$", values):
            body = _block(values, f"sr_cost_factor_{m}")
            self.cost_factor[m] = (float(re.search(r"value = ([\d.]+)", body).group(1))
                                   + sum(float(v) for v in re.findall(r"\badd = ([\d.]+)", body)))
        self.values = values

    def goal(self, m):
        """The goal at its largest: the base plus every stage's addition, or for
        solar colonization the largest of the stages' goals it names (generated,
        gen_solar_sites.STAGE_GOALS)."""
        body = _block(self.values, f"sr_{m}_goal")
        stages = re.findall(r"value = sr_colonization_goal_stage_(\d)", body)
        if stages:
            generated = _read(SITES_VALUES)
            return max(float(re.search(rf"(?m)^sr_colonization_goal_stage_{s} = \{{ value = ([\d.]+) \}}",
                                       generated).group(1)) for s in stages)
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
    if re.fullmatch(r"sr_funding_\w+_past_cap_effective", name):
        return FUNDING_PAST_CAP
    if re.fullmatch(r"sr_funding_\w+|sr_max_funding_level", name):
        return FUNDING_CEILING
    if re.fullmatch(r"sr_disp_rival_(lo|hi|est)_\w+|sr_disp_progress_frac_\w+", name):
        return 1.0  # a share of the goal, clamped to 0..1: "100%"
    if re.fullmatch(r"sr_disp_cf_slot_\d_months|sr_disp_fl_\d_months_left", name):
        return TRANSIT_CEILING
    if re.fullmatch(r"sr_window_wait_months_\w+", name):
        return WINDOW_WAIT
    if re.fullmatch(r"sr_transit_months_\w+", name):
        return TRANSIT_CEILING
    if re.fullmatch(r"sr_disp_win_premium_\w+", name):
        return WINDOW_PREMIUM_SHOWN
    if re.fullmatch(r"sr_disp_sc_mix_\w+", name):
        return MIX_WEIGHT
    if re.fullmatch(r"sr_disp_cf_slot_\d_year", name):
        return END_YEAR
    fixed = {"sr_current_colonization_stage": STAGE_CEILING, "sr_disp_mq_next_months": 999,
             "sr_interstellar_transit_value": TRANSIT_MONTHS, "sr_total_global_colonies": WORLDS, "sr_sites_world_count": WORLDS,
             "sr_disp_colonies_held": WORLDS, "sr_disp_cf_in_flight": FLEET_SLOTS,
             "sr_disp_emig_per_month": SETTLERS_A_MONTH, "sr_disp_offworld_pop": OFFWORLD_PEOPLE,
             "sr_disp_fab_rate": FAB_RATE_CEILING, "sr_disp_fab_stock": FAB_STOCK,
             "sr_disp_ms_waiting": SHIP_SLOTS, "sr_disp_ms_flying": SHIP_SLOTS,
             "sr_disp_mod_upkeep_pct": UPKEEP_CEILING, "sr_disp_ebase_levels": EBASE_LEVELS,
             "sr_disp_ebase_room": EBASE_LEVELS, "sr_disp_free_supplied_count": FREE_WORLDS,
             "sr_disp_free_trade_research": FREE_TRADE_RESEARCH, "sr_disp_sc_rate": SC_RATE_CEILING,
             "sr_disp_fl_strength": FLEET_STRENGTH, "sr_disp_fl_strength_full": FLEET_STRENGTH,
             "sr_disp_sc_upkeep_pct": FLEET_UPKEEP_PCT, "sr_disp_reserve": FLEET_STRENGTH,
             # the colonization overview's cells (audit SPC-6)
             "sr_disp_aut_restless_more": WORLDS - 1, "sr_disp_mq_count": QUEUE_PLACES,
             "sr_mod_fab_stock_cap": FAB_STOCK, "sr_window_disp_next": WINDOW_MONTHS,
             "sr_disp_win_beyond": WINDOW_DESTINATIONS}
    assert name in fixed, f"no longest figure known for {name}: add one to _longest_figure"
    return fixed[name]


_CUSTOM = {}


def _custom_options(name):
    """The loc keys a customizable localization entry can pick."""
    if not _CUSTOM:
        for path in glob.glob(os.path.join(CUSTOM_LOC_DIR, "*.txt")):
            text = _read(path)
            for m in re.finditer(r"(?m)^(\w+) = \{", text):
                body = text[m.end():_close(text, m.end() - 1)]
                _CUSTOM[m.group(1)] = re.findall(r"localization_key = (\w+)", body)
    assert name in _CUSTOM, f"no custom loc {name}"
    return _CUSTOM[name]


def _render(value):
    """The loc value as the player reads it, every figure at its longest."""
    for _ in range(5):
        value = re.sub(r"\$(\w+)\$", lambda m: _loc(m.group(1)), value)
    value = re.sub(r"\[[^\[\]]*GetCustom\('(\w+)'\)\]",
                   lambda m: max((_render(_loc(k)) for k in _custom_options(m.group(1))), key=len), value)

    def figure(m):
        name, pct, fmt = m.group(1) or m.group(2), m.group(3), m.group(4)
        assert fmt is not None, f"a figure with no format: {m.group(0)}"
        if fmt == "D":  # a whole number with thousands separators
            return f"{_longest_figure(name):,.0f}"
        if pct:
            return f"{_longest_figure(name) * 100:.{int(fmt)}f}%"
        return f"{_longest_figure(name):.{int(fmt)}f}"

    value = re.sub(r"\[[^\[\]]*?(?:ScriptValue\('(\w+)'\)|Var\('(\w+)'\)\.GetValue)(?:\|(%?)(\d|D))?\]",
                   figure, value)
    value = value.replace("[State.GetCountry.GetName]", _longest_country_name())
    value = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", value)
    value = re.sub(r"\[(concept_\w+)\]", lambda m: _loc(m.group(1)), value)
    assert "[" not in value, f"an unmeasured expression in {value!r}"
    value = re.sub(r"#[A-Za-z_;]+ ", "", value)
    return value.replace("#!", "")


# Every loc key the panel shows, by the cell it shows in. Keys in more than one
# cell are measured against each.
MULTILINE = (r"je_space_race_widget_(how_\w+|profile_\w+|colonies_empty|solar_system_note"
             r"|powers_(?:more|pending|none)|free_empty|sc_blockaded_note|sc_site_lost_note|space_fleets_empty"
             r"|howc_(?!sub_)\w+|win_none|win_beyond|tp_intro|tp_none|tp_gone)")
CELLS = {
    # (type, marker picking the textbox): patterns of the keys it shows
    "state, risk, first and stage (te_sr_ov_icon_label)": (
        ("te_sr_ov_icon_label", 'block "label"'),
        r"je_space_race_widget_(ov_idle|standard_label|ov_safe_\w+|ov_ambitious_\w+|risk_\w+"
        r"|ov_first_open|ov_first_claimed|ov_stage(?:_moon)?)"),
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
        r"je_space_race_widget_(setbacks_label|eta_label|colonies_held_label|cf_in_flight_label"
        r"|emig_month_label|offworld_label|orbit_\w+_label|fab_label|shipments_label|mod_upkeep_label"
        r"|ebase_label|free_trade_label|sc_rate_label|sc_strength_label|sc_upkeep_label|sc_reserve_label"
        r"|cf_drive_label|mq_next_label)"),
    "value-row figure (te_sr_value_row)": (
        ("te_sr_value_row", 'block "row_value"'),
        r"je_space_race_widget_((setbacks|eta)_(?!label)\w+|colonies_held_figure|cf_in_flight_figure"
        r"|emig_month_figure|offworld_figure|fab_figure|shipments_figure|mod_upkeep_figure|ebase_figure"
        r"|free_trade_figure|sc_rate_figure|sc_strength_figure|sc_upkeep_figure|sc_reserve_figure"
        r"|cf_drive_value|mq_next_(?:months|full|none))"),
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
    "colony stage and location heading (te_sr_subheader)": (
        ("te_sr_subheader", 'block "subheader_text"'),
        r"je_space_race_widget_(ss_loc_\w+|powers_others|mq_header|free_header|sc_mix_header|howc_sub_\w+"
        r"|windows_header)"),
    "a world's holder: ours (te_sr_site_row)": (
        ("te_sr_site_row", 'text = "je_space_race_widget_ss_ours"'),
        r"je_space_race_widget_ss_ours"),
    "a world's holder: unknown (te_sr_site_row)": (
        ("te_sr_site_row", 'text = "je_space_race_widget_ss_unknown"'),
        r"je_space_race_widget_ss_unknown"),
    "a world's holder: none (te_sr_site_row)": (
        ("te_sr_site_row", 'text = "je_space_race_widget_ss_unclaimed"'),
        r"je_space_race_widget_ss_unclaimed"),
    "a power's estimate (te_sr_power_lead_text, the Space Race tab)": (
        ("te_sr_power_lead_text", None),
        r"je_space_race_widget_power_(lead|own)_\w+"),
    "a world's holder: free (te_sr_site_row)": (
        ("te_sr_site_row", 'text = "je_space_race_widget_ss_free"'),
        r"je_space_race_widget_ss_free"),
    "a colony's status (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_autonomy_status_none"'),
        r"je_space_race_widget_autonomy_status_\w+"),
    "the Abandon button (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_autonomy_abandon"'),
        r"je_space_race_widget_autonomy_abandon"),
    "the Supply and Stop buttons (te_sr_free_row)": (
        ("te_sr_free_row", 'text = "je_space_race_widget_free_supply"'),
        r"je_space_race_widget_free_(supply|stop)"),
    "a world's holder: our target (te_sr_site_row)": (
        ("te_sr_site_row", 'text = "je_space_race_widget_ss_target"'),
        r"je_space_race_widget_ss_target"),
    "the Target button (te_sr_site_row)": (
        ("te_sr_site_row", 'text = "je_space_race_widget_ss_target_button"'),
        r"je_space_race_widget_ss_target_button"),
    "the Clear button (te_sr_site_row)": (
        ("te_sr_site_row", 'text = "je_space_race_widget_ss_target_clear"'),
        r"je_space_race_widget_ss_target_clear"),
    "a fleet's landing (te_sr_cf_slot_row)": (
        ("te_sr_cf_slot_row", 'block "slot_eta"'),
        r"je_space_race_widget_cf_slot_\d_eta"),
    "a colony's crews under AGI (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_settlers_agi"'),
        r"je_space_race_widget_settlers_agi"),
    "a colony's priority (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_emig_prio_0"'),
        r"je_space_race_widget_emig_prio_\d"),
    "emigration label (te_sr_sec_colonies)": (
        ("te_sr_sec_colonies", 'text = "je_space_race_widget_emig_label"'),
        r"je_space_race_widget_emig_label"),
    "emigration level (te_sr_sec_colonies)": (
        ("te_sr_sec_colonies", 'text = "je_space_race_widget_emig_level_0"'),
        r"je_space_race_widget_emig_level_\d"),
    "a module cell's label (te_sr_mod_cell)": (
        ("te_sr_mod_cell", 'block "cell_label"'),
        r"je_space_race_widget_modules_col_(a|b|hab|port|def|mine|yard|lab|culture|resort|black|train|bunker"
        r"|foundry|admin)"),
    "a colony's slots label (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_modules_col_slots"'),
        r"je_space_race_widget_modules_col_slots"),
    "a colony's bases label (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_modules_col_bases"'),
        r"je_space_race_widget_modules_col_bases"),
    "the crew share's label (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_modules_col_staffing"'),
        r"je_space_race_widget_modules_col_staffing"),
    **{f"the colonies' {head} head ({heads})": (
        (heads, f'text = "je_space_race_widget_ch_{head}"'), f"je_space_race_widget_ch_{head}")
       for heads, names in (("te_sr_colony_heads_people", ("people", "crews")),
                            ("te_sr_colony_heads_autonomy", ("autonomy", "drift", "build")),
                            ("te_sr_colony_heads_defences", ("defences", "integrity", "marines")))
       for head in names},
    # A colony's page (colony management design § 8; the owner's review of 2026-10-30).
    "a section's heading on a colony's page (te_sr_page_heading)": (
        ("te_sr_page_heading", 'block "heading_text"'),
        r"je_space_race_widget_cv_(people|modules|autonomy|defences)"),
    "a tile's caption on a colony's page (te_sr_page_tile)": (
        ("te_sr_page_tile", 'block "tile_caption"'),
        r"je_space_race_widget_(page_(staffing|bases|status)|ch_\w+|modules_col_slots)"),
    "a word beside a page heading, or a page tile's word (te_sr_page_value)": (
        ("te_sr_page_value", None),
        r"je_space_race_widget_(page_settlers|autonomy_status_\w+|def_status_\w+|settlers_agi)"),
    "a module's name on a colony's page (te_sr_page_mod_row)": (
        ("te_sr_page_mod_row", 'block "row_name"'),
        r"je_space_race_widget_mod_name_\w+"),
    "the colonization tabs (te_sr_tab_button)": (
        ("te_sr_tab_button", 'block "tab_label"'),
        r"je_space_race_widget_tab_(fleets|colonies)"),
    "the wide colonization tabs (te_sr_tab_button_wide)": (
        ("te_sr_tab_button_wide", 'block "tab_label"'),
        r"je_space_race_widget_tab_(mission|system)"),
    "the colony views (te_sr_colony_view_button)": (
        ("te_sr_colony_view_button", 'block "view_label"'),
        r"je_space_race_widget_cv_(people|modules|autonomy|defences|back)"),
    "the next fleet's label (te_sr_cf_dest_row)": (
        ("te_sr_cf_dest_row", 'block "dest_label"'),
        r"je_space_race_widget_cf_(target_label|next_label)"),
    "the next fleet's Change and Choose (te_sr_sec_colony_fleets)": (
        ("te_sr_sec_colony_fleets", 'text = "je_space_race_widget_cf_change"'),
        r"je_space_race_widget_cf_(change|choose)"),
    "the next fleet's world (te_sr_cf_dest_row)": (
        ("te_sr_cf_dest_row", 'block "dest_value"'),
        r"je_space_race_widget_cf_(target_value|next_auto)"),
    "show all or fewer worlds (te_sr_sec_solar_system)": (
        ("te_sr_sec_solar_system", 'text = "je_space_race_widget_ss_show_all"'),
        r"je_space_race_widget_ss_show_(all|fewer)"),
    "the overview cells' captions (te_banking_ov_cell)": (
        ("te_banking_ov_cell", None),
        r"je_space_race_widget_ovc_\w+_cap"),
    "the overview cells' words and figures (te_banking_ov_word)": (
        ("te_banking_ov_word", None),
        r"je_space_race_widget_ovc_\w+_(word|fig)(_\w+)?"),
    "programme label (te_sr_ov_programme)": (
        ("te_sr_ov_programme", 'text = "je_space_race_widget_programme_header"'),
        r"je_space_race_widget_programme_header"),
    # The fleets (slice 6, Full Colonies).
    **{f"the fleets' {col} column head (te_sr_fleet_header_row)": (
        ("te_sr_fleet_header_row", f'text = "je_space_race_widget_fl_col_{col}"'), f"je_space_race_widget_fl_col_{col}")
       for col in ("where", "strength", "drive", "dv", "supply", "marines")},
    "a fleet's orders (te_sr_fl_button)": (
        ("te_sr_fl_button", 'block "fl_btn_label"'),
        r"je_space_race_widget_fl_(go|merge|detach|land|embark)"),
    "a fleet's refit (te_sr_fleet_row)": (
        ("te_sr_fleet_row", 'text = "je_space_race_widget_fl_refit"'),
        r"je_space_race_widget_fl_refit"),
    "a fleet's landing (te_sr_fleet_row)": (
        ("te_sr_fleet_row", 'block "fl_transit"'),
        r"je_space_race_widget_fl_\d_transit"),
    "a fleet's posture (te_sr_fleet_row)": (
        ("te_sr_fleet_row", 'text = "je_space_race_widget_fl_posture_1"'),
        r"je_space_race_widget_fl_posture_\d"),
    "seize or destroy (te_sr_fleet_row)": (
        ("te_sr_fleet_row", 'text = "je_space_race_widget_fl_seize"'),
        r"je_space_race_widget_fl_(seize|destroy)"),
    **{f"the locations' {col} column head (te_sr_location_header_row)": (
        ("te_sr_location_header_row", f'text = "je_space_race_widget_loc_col_{col}"'), f"je_space_race_widget_loc_col_{col}")
       for col in ("where", "ours", "others", "inbound", "status")},
    "a location's status (te_sr_location_row)": (
        ("te_sr_location_row", 'text = "je_space_race_widget_loc_status_blockading"'),
        r"je_space_race_widget_loc_status_\w+"),
    "a colony's defense status (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_def_status_calm"'),
        r"je_space_race_widget_def_status_(calm|blockaded|assault|interdicted)"),
    "an occupied colony (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_def_status_occupied"'),
        r"je_space_race_widget_def_status_occupied"),
    "a world's holder: occupied (te_sr_site_row)": (
        ("te_sr_site_row", 'text = "je_space_race_widget_ss_occupied"'),
        r"je_space_race_widget_ss_occupied"),
    "a world's holder: ruined (te_sr_site_row)": (
        ("te_sr_site_row", 'text = "je_space_race_widget_ss_ruined"'),
        r"je_space_race_widget_ss_ruined"),
    # Next Windows (colony management design § 6).
    "a destination's name and its head (te_sr_window_row)": (
        ("te_sr_window_row", 'block "win_name"'),
        r"je_space_race_widget_win_col_dest"),
    "a destination's window, any month, and its head (te_sr_window_row)": (
        ("te_sr_window_row", 'block "win_any_text"'),
        r"je_space_race_widget_win_(any|col_window)"),
    "a destination's window, open (te_sr_window_row)": (
        ("te_sr_window_row", 'text = "je_space_race_widget_win_open"'),
        r"je_space_race_widget_win_open"),
    "a destination's window, waiting (te_sr_window_row)": (
        ("te_sr_window_row", 'block "win_wait"'),
        r"je_space_race_widget_win_wait_\w+"),
    "a destination's window with depots (te_sr_window_row)": (
        ("te_sr_window_row", 'block "win_paid"'),
        r"je_space_race_widget_win_paid_\w+"),
    # The colony target popup's window column (UI pass design § 5): Next
    # Windows' keys, in a narrower cell.
    "a site's window, any month (te_sr_site_window_cell)": (
        ("te_sr_site_window_cell", 'text = "je_space_race_widget_win_any"'),
        r"je_space_race_widget_win_any"),
    "a site's window, open (te_sr_site_window_cell)": (
        ("te_sr_site_window_cell", 'text = "je_space_race_widget_win_open"'),
        r"je_space_race_widget_win_open"),
    "a site's window, waiting (te_sr_site_window_cell)": (
        ("te_sr_site_window_cell", 'block "win_wait"'),
        r"je_space_race_widget_win_wait_\w+"),
    "a site's window with depots (te_sr_site_window_cell)": (
        ("te_sr_site_window_cell", 'block "win_paid"'),
        r"je_space_race_widget_win_paid_\w+"),
    "a destination's transit and its head (te_sr_window_row)": (
        ("te_sr_window_row", 'block "win_transit"'),
        r"je_space_race_widget_win_(col_transit|transit_\w+)"),
    "the build mix, Launch and Auto (te_sr_sc_mix_button)": (
        ("te_sr_sc_mix_button", 'block "mix_label"'),
        r"je_space_race_widget_sc_(mix_(war|rapid|siege|carrier|tender)|launch|auto_on|auto_off)"),
    # Dismantling (owner, 2026-10-31): a module level coming down, under its name.
    "a module coming down on a colony's page (te_sr_page_mod_row)": (
        ("te_sr_page_mod_row", 'text = "je_space_race_widget_mod_coming_down"'),
        r"je_space_race_widget_mod_coming_down"),
}
SECTION_HEADERS = (r"je_space_race_widget_(control_header|rivals_header|colonies_header|solar_system_header|how_header"
                   r"|fleets_header|powers_header|orbit_header|howc_header"
                   r"|sc_header|space_fleets_header|locations_header|tp_title)")


# Cells that wrap to a second line on purpose: the overview's state cell, where
# Safe and Ambitious carry their weekly cost under the word (audit SPC-11).
TWO_LINE = {"te_sr_ov_icon_label": 2}


def _cell(gui, type_name, marker):
    if type_name in ("te_banking_ov_word", "te_banking_ov_cell"):  # Banking's cell (audit SPC-6)
        gui = _read(BANKING)
        if type_name == "te_banking_ov_cell":
            box = _textbox_with(_type_body(gui, type_name), 'block "caption"')
            return int(re.search(r"max_width = (\d+)", _type_body(gui, type_name)).group(1)), _font(box)
        box = _type_body(gui, type_name)
        return _width(box), _font(box)
    if marker is None:  # the type is the textbox: its instances set the text
        assert re.search(rf"type {type_name} = textbox \{{", gui), type_name
        box = _type_body(gui, type_name)
        return _width(box), _font(box)
    boxes = [b for b in _textboxes(_type_body(gui, type_name)) if marker in b]
    assert boxes, f"no textbox holds {marker}"
    # A label shown twice (a colony's list row and its page) is held to the narrower cell.
    box = boxes[0] if len(boxes) == 1 else min(boxes, key=_width)
    if type_name == "te_sr_ov_pie":  # the label is as wide as the pie's widget
        return int(re.search(r"size = \{ (\d+) \d+ \}", _type_body(gui, type_name)).group(1)), _font(box)
    if type_name == "te_sr_ov_programme":  # centred in the 480 column
        return 480, _font(box) if "using" in box else "medium"
    return _width(box), _font(box)


def _shown_keys(gui):
    """Every loc key the GUI shows as a textbox's text, with the value-driven
    keys the roots pass in (sr_label_safe, sr_risk_label, sr_progress_text …),
    and the funding figure's two keys, which a SelectLocalization picks between
    at and past the cap (lunar colonization design § 5.1)."""
    keys = set(re.findall(r'\btext = "(je_space_race_widget_\w+)"', gui))
    keys |= set(re.findall(r"'(je_space_race_widget_funding_\w+)'", gui))
    # and the queue's next-module figure, which one picks among three
    keys |= set(re.findall(r"'(je_space_race_widget_mq_next_\w+)'", gui))
    return sorted(keys)


class LabelBudgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Next Windows' table and its row (the rest of that file, the Staged in
        # Orbit line, is an overview row measured with the overview's).
        windows = _read(WINDOWS)
        cls.gui = _read(GUI) + "".join(f"\ntype {name} = flowcontainer {{{_type_body(windows, name)}}}\n"
                                       for name in ("te_sr_sec_windows", "te_sr_window_row"))
        cls.keys = _shown_keys(cls.gui + _read(ROWS) + _read(FLEET_ROWS))

    def _fits(self, key, width, font, lines=1):
        text = _render(_loc(key))
        parts = text.split("\\n")
        self.assertLessEqual(len(parts), lines, f"{key} has more lines than its cell holds")
        for part in parts:
            need = len(part) * UNITS_PER_CHAR[font] * MARGIN
            self.assertLessEqual(need, width, f"{key} renders {part!r}: {need:.0f} units in a {width}-wide cell")

    def test_every_single_line_label_fits_its_cell(self):
        for cell, ((type_name, marker), pattern) in CELLS.items():
            width, font = _cell(self.gui, type_name, marker)
            keys = [k for k in self.keys if re.fullmatch(pattern, k)]
            self.assertTrue(keys, f"no keys for {cell}")
            for key in keys:
                with self.subTest(cell=cell, key=key):
                    self._fits(key, width, font, lines=TWO_LINE.get(type_name, 1))

    def test_the_panel_is_on_the_house_ladder(self):
        """Rows 17, headings 20, the overview 16, through the panel's own
        templates; no bare vanilla size is left (audit SPC-11)."""
        self.assertEqual(_SIZES, {"row": 17, "heading": 20, "overview": 16})
        for path in (GUI, ROWS, FLEET_ROWS):
            with self.subTest(file=os.path.basename(path)):
                self.assertNotRegex(_read(path), r"using = fontsize_(?:small|medium|large|xsmall|xl)\b")

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
        self.assertEqual(_render(_loc("je_space_race_widget_ov_ambitious_interstellar_probe")),
                         "Ambitious\\n−360 a week")
        self.assertEqual(_render(_loc("je_space_race_widget_ov_safe_orbital")), "Safe\\n−22.5 a week")
        self.assertEqual(_render(_loc("je_space_race_widget_progress_solar_colonization")), "800 / 800 (+99.9/mo)")
        self.assertEqual(_render(_loc("je_space_race_widget_eta_solar_colonization")), "1600 months")
        self.assertEqual(_render(_loc("je_space_race_widget_funding_past_cap_suborbital")), "99 / 99 (+1.6)")
        self.assertEqual(_render(_loc("je_space_race_widget_progress_interstellar_results")), "132 / 132 months")
        self.assertEqual(_render(_loc("je_space_race_widget_risk_mars_landing")), "Risk: 50%/mo")
        self.assertEqual(_render(_loc("je_space_race_widget_ov_colony_label")), "Next Colony")
        self.assertEqual(_render(_loc("je_space_race_widget_approach_label")), "Approach")
        self.assertEqual(_render(_loc("je_space_race_widget_funding_label")), "Funding")
        self.assertEqual(_longest_country_name(), "United Socialist Council Republics of California")
        self.assertEqual(_render(_loc("je_space_race_widget_rival_range_mars_landing")), "100%–100%")
        self.assertEqual(_render(_loc("je_space_race_widget_power_lead_suborbital")), "Suborbital Flight: 100%–100%")

    def test_the_owners_overrun_is_caught(self):
        """The budget flags what the owner saw: "Next Colony" in the old 90."""
        need = len("Next Colony") * UNITS_PER_CHAR["medium"] * MARGIN
        self.assertGreater(need, 90)



class FigureBudgetTest(unittest.TestCase):
    """The figures the generated rows print (raw_text, no loc to measure) fit
    their cells at the row font (audit SPC-11): each cell is read from its
    block's textbox, and held to the longest figure its value prints."""

    # block: the longest figure it shows
    FIGURES = {
        # Colonies (te_sr_colony_row): people and room in K, crews, crew share,
        # a module level and what is on its way, autonomy and drift, Defenses
        "settler_people": "999.9K / 999.9K", "settler_crews": "99", "module_staffing": "100%",
        "aut_figure": "100%", "aut_drift": "+0.99", "def_level": "99", "def_integrity": "100%", "def_marines": "99",
        # slots used of slots (4 + 5 technologies + 4 past), base room (60 + 10 levels x 10),
        # what the colony builds of its own (colony management design §§ 4.3, 5)
        "module_slots": "13/9", "module_slots_past": "13/9", "module_bases": "160", "aut_build": "100% (+5.0)",
        # a site's grade beside its room (gen_solar_sites.SITES: -45% to +30%)
        "module_grade": "(\u221245%)",
    }
    # a module cell (te_sr_mod_cell): a level (10 past a world's slots at most) and what is on its way
    CELL = {"cell_level": "8", "cell_pending": "+8"}
    FREE = {"free_people": "999.9K", "free_ties": "100"}
    FLEET = {"fl_strength": "9999/9999", "fl_dv": "5000", "fl_supply": "36", "fl_marines": "99"}
    LOCATION = {"loc_ours": "99999", "loc_others": "99999", "loc_inbound_ours": "9·999"}
    SITE = {"site_inbound_ours": "9·999", "site_slots": "99"}
    QUEUE = {"mq_place": "20."}

    def _check(self, typ, figures):
        body = _type_body(_read(GUI), typ)
        for block, figure in figures.items():
            with self.subTest(type=typ, block=block):
                box = _textbox_with(body, f'block "{block}"')
                width, font = _width(box), _font(box)
                need = len(figure) * UNITS_PER_CHAR[font] * MARGIN
                self.assertLessEqual(need, width, f"{figure!r}: {need:.0f} units in a {width}-wide cell")

    def test_a_colony_page_s_figures(self):
        """A colony's page shows the list's figures again, in its tiles'
        te_sr_page_value (colony management design § 8), and the specialization
        names in full in its module rows."""
        gui = _read(GUI)
        row = _type_body(gui, "te_sr_colony_row")
        width, font = _width(_type_body(gui, "te_sr_page_value")), _font(_type_body(gui, "te_sr_page_value"))
        shown = re.findall(r'te_sr_page_value = \{[^{}]*block "(\w+)"', row)
        self.assertGreaterEqual(len(shown), 12)
        for block in shown:
            figure = self.FIGURES.get(block)
            if figure is None:
                continue
            with self.subTest(block=block):
                need = len(figure) * UNITS_PER_CHAR[font] * MARGIN
                self.assertLessEqual(need, width, f"{figure!r}: {need:.0f} units in a {width}-wide cell")
        mod_row = _type_body(gui, "te_sr_page_mod_row")
        for block, figure in (("row_level", self.CELL["cell_level"]), ("row_pending", self.CELL["cell_pending"])):
            with self.subTest(block=block):
                box = _textbox_with(mod_row, f'block "{block}"')
                self.assertLessEqual(len(figure) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box))
        name_box = _textbox_with(mod_row, 'block "row_name"')
        sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
        import gen_solar_sites as gss
        for site in gss.SITES:
            for mod in gss.spec_modifiers(site):
                with self.subTest(specialization=mod):
                    need = len(_render(_loc(mod))) * UNITS_PER_CHAR[_font(name_box)] * MARGIN
                    self.assertLessEqual(need, _width(name_box), _loc(mod))

    def test_a_site_s_base_room(self):
        """Solar System's line under a site's name: its base room and grade,
        as each generated row prints it (the owner, 2026-10-30)."""
        box = _textbox_with(_type_body(_read(GUI), "te_sr_site_row"), 'block "site_bases"')
        figures = re.findall(r'blockoverride "site_bases" \{\s*raw_text = "([^"]*)"', _read(ROWS))
        self.assertEqual(len(figures), 80)   # Solar System's and the colony target popup's
        for figure in figures:
            with self.subTest(figure=figure):
                text = _render(figure)
                self.assertLessEqual(len(text) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), text)

    def test_colony_rows(self):
        self._check("te_sr_colony_row", self.FIGURES)
        self._check("te_sr_mod_cell", self.CELL)
        self._check("te_sr_free_row", self.FREE)
        self._check("te_sr_mq_row", self.QUEUE)
        self._check("te_sr_site_row", self.SITE)

    def test_fleet_and_location_rows(self):
        self._check("te_sr_fleet_row", self.FLEET)
        self._check("te_sr_location_row", self.LOCATION)

    def test_the_fleet_names(self):
        """A fleet's where, drive and target are custom loc: their longest option."""
        body = _type_body(_read(GUI), "te_sr_fleet_row")
        for block, entry in (("fl_where", "sr_fl_1_where_name"), ("fl_drive", "sr_fl_1_drive_name"),
                             ("fl_target", "sr_fl_1_target_name"), ("fl_pick", "sr_fl_1_pick_name")):
            with self.subTest(block=block):
                box = _textbox_with(body, f'block "{block}"')
                longest = max((_render(_loc(k)) for k in _custom_options(entry)), key=len)
                need = len(longest) * UNITS_PER_CHAR[_font(box)] * MARGIN
                self.assertLessEqual(need, _width(box), f"{longest!r} in {block}")

    def test_the_solar_system_count(self):
        """The count line is a SelectLocalization of two keys (not a text = key):
        Solar System's, and the colony target popup's (UI pass design § 5)."""
        for type_name, keys in (("te_sr_sec_solar_system", ("ss_filtered", "ss_all")),
                                ("te_sr_target_popup_body", ("tp_count", "tp_all"))):
            sec = _type_body(_read(GUI), type_name)
            box = _textbox_with(sec, f"'je_space_race_widget_{keys[0]}'")
            for key in (f"je_space_race_widget_{k}" for k in keys):
                with self.subTest(key=key):
                    text = re.sub(r"\[[^\[\]]*\]", "40", _loc(key))
                    text = re.sub(r"#[A-Za-z_;]+ ", "", text).replace("#!", "")
                    self.assertLessEqual(len(text) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), key)

    def test_overview_names_fit(self):
        """Audit SPC-6: a world named in an overview cell (154 wide, the
        overview face) uses its short form where its name is too long."""
        sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
        import gen_solar_sites as gss
        for site in gss.SITES:
            with self.subTest(world=site.key):
                name = _loc(gss.overview_name_key(site))
                self.assertLessEqual(len(name) * UNITS_PER_CHAR["overview"] * MARGIN, 154, name)

if __name__ == "__main__":
    unittest.main()
