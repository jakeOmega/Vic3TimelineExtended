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
import functools
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
# The room buildings' cells (gen_solar_sites.render_room_display, #1951).
ROOM_DISPLAY_VALUES = os.path.join(REPO, "common", "script_values", "sr_sites_display_generated.txt")
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
SETTLERS_SENT = 4_096_000  # sr_disp_emig_last_sent: the step at or past the open room (every world's, ~3.4 million at the cap)
SETTLERS_LC_WEEK = 2_835_693  # sr_disp_emig_bill_week: that many settlers x 3 x 12 / 52
OFFWORLD_PEOPLE = 9_999_999  # sr_disp_offworld_pop: the rooms' sum is 945,000 before modules; seven digits
TRANSIT_CEILING = 999     # sr_disp_cf_slot_<n>_months: the longest transit is 611 (chemical, the Kuiper Belt)
WEEKS_CEILING = 9999      # a fleet's legs in weeks (ticks, four a month): the Kuiper Belt's chemical one is about 2,440
END_YEAR = 2136           # sr_disp_cf_slot_<n>_year: END_DATE's year
FAB_RATE_CEILING = 99.9   # sr_disp_fab_rate: the best method gives 25 a month; technology could add more
FAB_STOCK = 200           # sr_disp_fab_stock: sr_mod_fab_stock_cap
SHIP_SLOTS = 8            # sr_disp_ms_waiting / _flying: gen_solar_sites.SHIP_SLOTS
UPKEEP_CEILING = 999      # sr_disp_mod_upkeep_levels: a level past the first per module, 40 worlds x 7 at most
# sr_disp_mod_upkeep_week: those levels x 1% of the Space Program's base Launch Capacity, at most the
# Interstellar Mission's 100,000, Fusion Shipyards' 4,800, the depot's 450 and debris removal's 300 (sr_emig_lc_base)
UPKEEP_LC_WEEK = round(UPKEEP_CEILING * 0.01 * (100_000 + 4_800 + 450 + 300))
EBASE_LEVELS = 99_999     # sr_disp_ebase_levels / _room: 4,335 levels of room before Mining Complexes, 26,535 with every slot one; five digits
FREE_WORLDS = 40          # sr_disp_free_supplied_count: at most every world
FREE_TRADE_RESEARCH = 5   # sr_disp_free_trade_research: sr_free_trade_max_units (5) x 1%
SC_RATE_CEILING = 99.9    # sr_disp_sc_rate: 2 a level a month at most; ten levels for an AI, more for a player
FLEET_STRENGTH = 99_999   # sr_disp_fl_strength / _full: every fleet's, unbounded by script; five digits
SPACE_FLEETS = 9          # sr_disp_fl_count: gen_space_fleets.SLOTS
LEG_DV_CEILING = 9999     # sr_disp_fl_<n>_leg_dv: gen_launch_windows.LEG_DV_CAP
FLEET_UPKEEP_PCT = 9999 * 900   # sr_disp_sc_upkeep_pct: +900% a unit of full strength / 10 (sr_fleet_upkeep_points)
# sr_disp_pers_in_service / _capacity (space forces personnel): 100 a point of strength and 1,000 a battalion, five-digit
# strength and two battalions a carrier point; |K shows three figures, so the longest is any value past 100M.
PERSONNEL = 999_000_000
MIX_WEIGHT = 3            # sr_disp_sc_mix_<role>: sr_sc_mix_max
ORDER_HULLS = 5 * 9999    # sr_disp_sc_order_total: sr_sc_order_max a role, five roles
ORDER_MONTHS = 999        # sr_disp_sc_order_months: its own max
QUEUE_PLACES = 20         # sr_disp_mq_count: gen_solar_sites.QUEUE_SLOTS
WINDOW_MONTHS = 999       # sr_window_disp_next: capped at 999 (the cell reads "No site left" there)
WINDOW_WAIT = 99          # sr_window_wait_months_<body>: the longest wait is Mars's synodic period, 26 months
WINDOW_PREMIUM_SHOWN = 9.99  # sr_disp_win_premium_<body>: capped at +999% for its cell
WINDOW_DESTINATIONS = 14  # sr_disp_win_beyond: gen_solar_sites.WINDOW_ORDER
# The Bases view (Extraplanetary Base ground types design § 9.1)
EB_PACE = 9999            # sr_disp_eb_pace: a 48th of the levels on record, 2,084 at EBASE_LEVELS; four digits
EB_MONTHS = 99            # sr_disp_eb_months: the levels to go over the pace, 49 at most (all of them at a 48th a month)
EB_GAP = 9.99             # sr_disp_eb_gap: clamped to "999%"
EB_MARGIN = 9999          # sr_disp_eb_margin: 5% of the yardstick, £1,812 with every level on Self-Replicating Miners
EB_PROFIT = 999_000_000   # sr_disp_eb_now_profit / _end_profit, £ a week: unbounded by script; "+999M"


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
            # A line may end in a comment (a loc_style REVIEWED note) that holds no quote.
            for k, v in re.findall(r'^ ([\w.]+):\d* "(.*)"\s*(?:#[^"\n]*)?$', _read(path), re.M):
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
    if re.fullmatch(r"sr_disp_cf_slot_\d_months", name):
        return TRANSIT_CEILING
    if re.fullmatch(r"sr_disp_fl_\d_weeks_left|sr_disp_earth_(?:hostile|alert)_weeks", name):
        return WEEKS_CEILING
    if re.fullmatch(r"sr_window_wait_months_\w+", name):
        return WINDOW_WAIT
    if re.fullmatch(r"sr_disp_fl_\d_leg_weeks", name):  # the Fleets window's leg line
        return WEEKS_CEILING
    if re.fullmatch(r"sr_disp_fl_\d_leg_dv", name):  # gen_launch_windows.LEG_DV_CAP
        return LEG_DV_CEILING
    if re.fullmatch(r"sr_transit_months_\w+", name):
        return TRANSIT_CEILING
    if re.fullmatch(r"sr_disp_win_premium_\w+", name):
        return WINDOW_PREMIUM_SHOWN
    if re.fullmatch(r"sr_disp_sc_mix_pct_\w+", name):
        return 100  # a share, in percent
    if re.fullmatch(r"sr_disp_sc_mix_rate_\w+", name):
        return SC_RATE_CEILING  # a share of sr_disp_sc_rate
    if re.fullmatch(r"sr_disp_sc_mix_\w+", name):
        return MIX_WEIGHT
    if re.fullmatch(r"sr_disp_sc_order_(?!total|months)\w+", name):
        return ORDER_HULLS // 5
    if re.fullmatch(r"sr_disp_fl_role_\w+", name):
        return FLEET_STRENGTH
    if re.fullmatch(r"sr_disp_cf_slot_\d_year", name):
        return END_YEAR
    if re.fullmatch(r"sr_fl_\d_strength", name):  # the Transfer popup's Into buttons, "Antimatter 99999"
        return FLEET_STRENGTH
    if re.fullmatch(r"sr_disp_hold_months_\w+", name):  # a hold's months, capped at sr_hold_months_none
        return 999
    if m := re.fullmatch(r"sr_disp_ss_people_room_(\w+)", name):
        return _site_room(m.group(1)) * _room_factor_ceiling()
    fixed = {"sr_current_colonization_stage": STAGE_CEILING, "sr_disp_mq_next_months": 999,
             "sr_interstellar_transit_value": TRANSIT_MONTHS, "sr_total_global_colonies": WORLDS, "sr_sites_world_count": WORLDS,
             "sr_disp_colonies_held": WORLDS, "sr_disp_cf_in_flight": FLEET_SLOTS,
             # The overview's Crews cell (colony people design § 10): our colonies short of crews.
             "sr_disp_understaffed_count": WORLDS,
             "sr_disp_emig_last_sent": SETTLERS_SENT, "sr_disp_emig_bill_week": SETTLERS_LC_WEEK, "sr_disp_offworld_pop": OFFWORLD_PEOPLE,
             "sr_disp_fab_rate": FAB_RATE_CEILING, "sr_disp_fab_stock": FAB_STOCK,
             "sr_disp_ms_waiting": SHIP_SLOTS, "sr_disp_ms_flying": SHIP_SLOTS,
             "sr_disp_mod_upkeep_levels": UPKEEP_CEILING,
             "sr_disp_mod_upkeep_week": UPKEEP_LC_WEEK, "sr_disp_ebase_levels": EBASE_LEVELS,
             "sr_disp_ebase_room": EBASE_LEVELS, "sr_disp_free_supplied_count": FREE_WORLDS,
             "sr_disp_ebase_queued": EBASE_LEVELS, "sr_disp_ebase_total": EBASE_LEVELS,
             "sr_disp_ebase_next_grade": -75,
             # The Resort Room cell (#1948): a level count, measured as the base's is.
             "sr_disp_resort_levels": EBASE_LEVELS, "sr_disp_resort_room": EBASE_LEVELS,
             "sr_disp_resort_queued": EBASE_LEVELS, "sr_disp_resort_total": EBASE_LEVELS,
             "sr_disp_resort_next_draw": -75,
             "sr_disp_free_trade_research": FREE_TRADE_RESEARCH, "sr_disp_sc_rate": SC_RATE_CEILING,
             "sr_disp_fl_strength": FLEET_STRENGTH, "sr_disp_fl_strength_full": FLEET_STRENGTH,
             "sr_disp_fl_count": SPACE_FLEETS,
             "sr_disp_sc_order_total": ORDER_HULLS, "sr_disp_sc_order_months": ORDER_MONTHS,
             "sr_disp_sc_upkeep_pct": FLEET_UPKEEP_PCT, "sr_disp_reserve": FLEET_STRENGTH,
             "sr_disp_pers_in_service": PERSONNEL, "sr_disp_pers_capacity": PERSONNEL, "sr_disp_pers_share_pct": 100,
             "sr_disp_earth_hostile_total": FLEET_STRENGTH, "sr_disp_loc_ours_earth": FLEET_STRENGTH,
             # the colonization overview's cells (audit SPC-6)
             "sr_disp_aut_restless_more": WORLDS - 1, "sr_disp_mq_count": QUEUE_PLACES,
             "sr_mod_fab_stock_cap": FAB_STOCK, "sr_window_disp_next": WINDOW_MONTHS,
             "sr_disp_win_beyond": WINDOW_DESTINATIONS,
             # the Bases view's move area and totals (ground types design § 9.1)
             "sr_disp_eb_pace": EB_PACE, "sr_disp_eb_months": EB_MONTHS, "sr_disp_eb_to_go": EBASE_LEVELS,
             "sr_disp_eb_gap": EB_GAP, "sr_disp_eb_margin": EB_MARGIN, "sr_disp_eb_move_began_year": END_YEAR,
             "sr_disp_eb_last_began_year": END_YEAR, "sr_disp_eb_last_ended_year": END_YEAR,
             "sr_disp_eb_now_profit": EB_PROFIT, "sr_disp_eb_end_profit": EB_PROFIT, "sr_disp_eb_unassigned": EBASE_LEVELS}
    assert name in fixed, f"no longest figure known for {name}: add one to _longest_figure"
    return fixed[name]


def _site_room(key):
    """A world's people room before Habitats, from the table (gen_solar_sites.SITES)."""
    sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
    import gen_solar_sites as gss
    return next(s.room for s in gss.SITES if s.key == key) * 1000


@functools.lru_cache(maxsize=None)
def _room_factor_ceiling():
    """The most sr_our_room_mult can reach: 1 plus every country_sr_colony_room_add
    a mod file grants (Space Colonization's and Terraforming's +0.5 today), so a
    new source widens the measure without an edit here."""
    total = 0.0
    for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True):
        if os.sep + "modifier_type_definitions" + os.sep in path:
            continue
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        total += sum(max(0.0, float(v)) for v in re.findall(r"\bcountry_sr_colony_room_add = (-?[\d.]+)", text))
    return 1 + total


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


def _k(x):
    """A figure in `|K`, at three significant figures and the suffix ("1.81K",
    "100.0K" at 99,999: a character long, as a bound should be)."""
    for div, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K"), (1, "")):
        if abs(x) >= div:
            break
    v = abs(x) / div
    return (f"{v:.0f}" if v >= 100 else f"{v:.1f}" if v >= 10 else f"{v:.2f}") + suffix


def _render(value, bounds=None):
    """The loc value as the player reads it, every figure at its longest, or
    at its bound in `bounds` for a word shown only under one. `|K` prints a
    figure abbreviated, `+` or `=` with its sign; the money icon is two
    characters wide."""
    for _ in range(5):
        value = re.sub(r"\$(\w+)\$", lambda m: _loc(m.group(1)), value)
    value = re.sub(r"\[[^\[\]]*GetCustom\('(\w+)'\)\]",
                   lambda m: max((_render(_loc(k)) for k in _custom_options(m.group(1))), key=len), value)

    def figure(m):
        name, pct, fmt = m.group(1) or m.group(2), m.group(3), m.group(4)
        assert fmt is not None, f"a figure with no format: {m.group(0)}"
        longest = (bounds or {}).get(name)
        longest = _longest_figure(name) if longest is None else longest
        sign = "+" if set(m.group(5) or "") & {"+", "="} else ""
        if fmt == "K":
            return sign + _k(longest)
        if fmt == "D":  # a whole number with thousands separators
            return sign + f"{longest:,.0f}"
        if pct:
            return sign + f"{longest * 100:.{int(fmt)}f}%"
        return sign + f"{longest:.{int(fmt)}f}"

    value = re.sub(r"\[[^\[\]]*?(?:ScriptValue\('(\w+)'\)|Var\('(\w+)'\)\.GetValue)(?:\|(%?)(\d|D|K)([+=]*))?\]",
                   figure, value)
    value = value.replace("@money!", "\u00a3\u00a3")
    value = value.replace("[State.GetCountry.GetName]", _longest_country_name())
    value = re.sub(r"\[Concept\('\w+',\s*'([^']*)'\)\]", r"\1", value)
    value = re.sub(r"\[(concept_\w+)\]", lambda m: _loc(m.group(1)), value)
    assert "[" not in value, f"an unmeasured expression in {value!r}"
    value = re.sub(r"#[A-Za-z_;]+ ", "", value)
    return value.replace("#!", "")



def _ebase_split_bounds():
    """The Base Room cell's split word ("built +queued / room") shows only
    while sr_disp_ebase_split's limit holds, so each figure it bounds is
    measured at its bound; a figure it leaves unbounded is measured at its
    longest and fails the cell."""
    limit = _block(_read(ROOM_DISPLAY_VALUES), "sr_disp_ebase_split")
    return {m.group(1): int(m.group(2)) - 1 for m in re.finditer(r"\b(sr_disp_ebase_\w+) < (\d+)", limit)}


def _resort_split_bounds():
    """The Resort Room cell's split word (#1948), bounded as Base Room's is by
    sr_disp_resort_split's limit."""
    limit = _block(_read(ROOM_DISPLAY_VALUES), "sr_disp_resort_split")
    return {m.group(1): int(m.group(2)) - 1 for m in re.finditer(r"\b(sr_disp_resort_\w+) < (\d+)", limit)}


# Words the GUI shows only while a script value bounds their figures.
BOUNDED_WORDS = {"je_space_race_widget_ovc_ebase_word_split": _ebase_split_bounds,
                 "je_space_race_widget_ovc_ebase_word_split_past": _ebase_split_bounds,
                 "je_space_race_widget_ovc_resort_word_split": _resort_split_bounds,
                 "je_space_race_widget_ovc_resort_word_split_past": _resort_split_bounds}

# Every loc key the panel shows, by the cell it shows in. Keys in more than one
# cell are measured against each.
MULTILINE = (r"je_space_race_widget_(how_\w+|profile_\w+|colonies_(?:brief_)?empty|solar_system_note"
             r"|powers_(?:more|pending|none)|free_empty|sc_blockaded_note|sc_site_lost_note|space_fleets_empty|space_fleets_no_sc|space_fleets_short"
             r"|howc_(?!sub_)\w+|win_none|win_beyond|tp_intro|tp_none|tp_gone|xf_intro|xf_gone|dp_why_\w+|dp_gone|ft_intro"
             r"|eb_no_gain|cw_gone|ld_intro|fw_gone|fw_in_transit)")
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
    # Another country's estimate in the bar's place (National Info, spec
    # 2026-11-02-charts-help-national-info § 6.4), at the bar row's widths.
    "progress label (te_sr_ov_band_row)": (
        ("te_sr_ov_band_row", 'block "band_label"'),
        r"je_space_race_widget_(ov_progress_label|ov_colony_label)"),
    "progress band in words (te_sr_ov_band_row)": (
        ("te_sr_ov_band_row", 'block "band_text"'),
        r"je_space_race_widget_band_(?!tt$)\w+"),
    "value-row label (te_sr_value_row)": (
        ("te_sr_value_row", 'block "row_label"'),
        r"je_space_race_widget_(setbacks_label|eta_label|colonies_held_label|cf_in_flight_label"
        r"|emig_sent_label|emig_bill_label|offworld_label|orbit_\w+_label|fab_label|shipments_label|mod_upkeep_label"
        r"|ebase_label|ebase_queued_label|eb_unassigned_label|resort_label|resort_queued_label|free_trade_label|sc_rate_label|sc_strength_label|sc_upkeep_label|sc_reserve_label"
        r"|sc_orders_label|sc_order_months_label"
        r"|cf_drive_label|mq_next_label)"),
    "value-row figure (te_sr_value_row)": (
        ("te_sr_value_row", 'block "row_value"'),
        r"je_space_race_widget_((setbacks|eta)_(?!label)\w+|colonies_held_figure|cf_in_flight_figure"
        r"|emig_sent_figure|emig_bill_figure|offworld_figure|fab_figure|shipments_figure|mod_upkeep_figure|ebase_figure|ebase_queued_figure"
        r"|eb_unassigned_figure"
        r"|resort_figure|resort_queued_figure"
        r"|free_trade_figure|sc_rate_figure|sc_rate_paused|sc_strength_figure|sc_upkeep_figure|sc_reserve_figure"
        r"|sc_orders_figure|sc_order_months_figure"
        r"|cf_drive_value|mq_next_(?:months|full|none|held))"),
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
        r"je_space_race_widget_(ss_loc_\w+|powers_others|mq_header|free_header|sc_build_header|howc_sub_\w+"
        r"|windows_header|eb_totals_header|effects_header)"),
    "Program Effects' group captions (te_sr_program_effects)": (
        ("te_sr_program_effects", 'text = "je_space_race_widget_effects_ongoing"'),
        r"je_space_race_widget_effects_(ongoing|timed)"),
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
    "the Revoke button, beside Abandon on a colony's page (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_autonomy_revoke"'),
        r"je_space_race_widget_autonomy_revoke"),
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
        r"|foundry|admin|terra)"),
    # Terraforming's line in the Modules view (era 13 spec § 7.11): its label, and
    # the years left, or that the work is finished or idle.
    "terraforming's label (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_modules_col_terraformed"'),
        r"je_space_race_widget_modules_col_terraformed"),
    **{f"terraforming's {word} (te_sr_colony_row)": (
        ("te_sr_colony_row", f'text = "je_space_race_widget_terra_{word}"'), f"je_space_race_widget_terra_{word}")
       for word in ("years_left", "finished", "idle")},
    "a colony's Habitats label (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_modules_col_slots"'),
        r"je_space_race_widget_modules_col_slots"),
    "a colony's bases label (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_modules_col_bases"'),
        r"je_space_race_widget_modules_col_bases"),
    "the crews' label (te_sr_colony_row)": (
        ("te_sr_colony_row", 'text = "je_space_race_widget_modules_col_crews"'),
        r"je_space_race_widget_modules_col_crews"),
    **{f"the colonies' {head} head ({heads})": (
        (heads, f'text = "je_space_race_widget_ch_{head}"'), f"je_space_race_widget_ch_{head}")
       for heads, names in (("te_sr_colony_heads_people", ("people", "crews")),
                            ("te_sr_colony_heads_autonomy", ("autonomy", "drift", "build")),
                            ("te_sr_colony_heads_defences", ("defences", "integrity", "marines")))
       for head in names},
    # A colony's page (colony management design § 8; the owner's review of 2026-10-30).
    "a section's heading on a colony's page (te_sr_page_heading)": (
        ("te_sr_page_heading", 'block "heading_text"'),
        r"je_space_race_widget_(cv_(people|modules|autonomy|defences)|fw_(ships|condition|orders))"),
    "a tile's caption on a colony's page (te_sr_page_tile)": (
        ("te_sr_page_tile", 'block "tile_caption"'),
        r"je_space_race_widget_(page_(staffing|bases|resorts|status|terraformed)|ch_\w+|modules_col_slots"
        r"|fw_role_(war|rapid|siege|carrier|tender)|fw_drive|fw_fire_(fleets|defences)|fw_dock|fw_repair)"),
    "a word beside a page heading, or a page tile's word (te_sr_page_value)": (
        ("te_sr_page_value", None),
        r"je_space_race_widget_(page_settlers|autonomy_status_\w+|autonomy_held_months_\w+|def_status_\w+"
        r"|terra_(?:years_left|finished|idle)|fw_dock_(?:none|earth|port|flight))"),
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
        r"je_space_race_widget_cv_(people|modules|autonomy|defences|bases|back)"),
    # The Bases view (Extraplanetary Base ground types design § 9.1): the
    # checkbox, a box's words, the totals' rows, and the move area's lines
    # that name no place (MOVE_PLACES has those).
    "the Bases checkbox's label (te_sr_sec_colonies)": (
        ("te_sr_sec_colonies", 'text = "je_space_race_widget_eb_auto"'),
        r"je_space_race_widget_eb_auto"),
    "a base box's profit word (te_sr_eb_level_line)": (
        ("te_sr_eb_level_line", 'text = "je_space_race_widget_eb_a_level"'),
        r"je_space_race_widget_eb_a_level"),
    "a base box's not-serving word (te_sr_eb_level_line)": (
        ("te_sr_eb_level_line", 'text = "je_space_race_widget_eb_blockaded"'),
        r"je_space_race_widget_eb_(blockaded|occupied)"),
    "a base box's levels elsewhere (te_sr_eb_level_line)": (
        ("te_sr_eb_level_line", 'text = "je_space_race_widget_eb_elsewhere"'),
        r"je_space_race_widget_eb_elsewhere"),
    "a Bases totals row's name (te_sr_eb_total_row)": (
        ("te_sr_eb_total_row", 'block "total_label"'),
        r"je_space_race_widget_eb_(now|if_prices_hold|at_assignments)"),
    "a Bases totals row's profit (te_sr_eb_total_row)": (
        ("te_sr_eb_total_row", 'block "total_value"'),
        r"je_space_race_widget_eb_(now|end)_profit"),
    "a line of the Bases move area (te_sr_eb_move_text)": (
        ("te_sr_eb_move_text", None),
        r"je_space_race_widget_eb_(toward|toward_months|at_assignments_line|moving|stay|all_lose|next_month|last|last_one)"),
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
    # The system map (the owner, 2026-11-23) and what it adds to Solar System.
    "back to every location (te_sr_sec_solar_system)": (
        ("te_sr_sec_solar_system", 'text = "je_space_race_widget_ss_all_locations"'),
        r"je_space_race_widget_ss_all_locations"),
    "a location's short name on the map (te_sr_map_location)": (
        ("te_sr_map_location", 'block "loc_name"'),
        r"je_space_race_widget_map_loc_(?!tt_|hint$)\w+"),
    "a word of the map's key (te_sr_map_key)": (
        ("te_sr_map_key", 'block "key_text"'),
        r"je_space_race_widget_(map_key_(?:other|target|inbound)|ss_ours|ss_unclaimed|ss_free)"),
    # The Colonies window (the owner, 2026-11-23): the count over its list.
    "the window's count, its label (te_sr_colony_popup_body)": (
        ("te_sr_colony_popup_body", 'text = "je_space_race_widget_colonies_held_label"'),
        r"je_space_race_widget_colonies_held_label"),
    "the window's count, its figure (te_sr_colony_popup_body)": (
        ("te_sr_colony_popup_body", 'text = "je_space_race_widget_cw_held_figure"'),
        r"je_space_race_widget_cw_held_figure"),
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
    # A fleet's card (owner, 2026-11-14): each bar's caption, each ship role's word.
    **{f"a fleet card's {col} caption (te_sr_fl_gauge)": (
        ("te_sr_fl_gauge", 'block "fg_label"'), f"je_space_race_widget_fl_col_{col}")
       for col in ("strength", "dv", "supply", "marines")},
    "a ship role's word on a fleet's card (te_sr_fl_role_cell)": (
        ("te_sr_fl_role_cell", 'block "rc_label"'),
        r"je_space_race_widget_fl_role_\w+"),
    "a fleet's orders (te_sr_fl_button)": (
        ("te_sr_fl_button", 'block "fl_btn_label"'),
        r"je_space_race_widget_fl_(go|land|embark)"),
    "a fleet's Transfer (te_sr_fleet_row)": (
        ("te_sr_fleet_row", 'text = "je_space_race_widget_fl_transfer"'),
        r"je_space_race_widget_fl_transfer"),
    # The Fleets window (the owner, 2026-11-25): the count over its list, a page's
    # title word, the captions of its orders lines and the leg to the destination picked.
    "the Fleets window's count, its label (te_sr_fleet_popup_body)": (
        ("te_sr_fleet_popup_body", 'text = "je_space_race_widget_fw_count_label"'),
        r"je_space_race_widget_fw_count_label"),
    "the Fleets window's count, its figure (te_sr_fleet_popup_body)": (
        ("te_sr_fleet_popup_body", 'text = "je_space_race_widget_fw_count_figure"'),
        r"je_space_race_widget_fw_count_figure"),
    "a fleet's page, the word before its number (te_sr_fleet_page)": (
        ("te_sr_fleet_page", 'text = "je_space_race_widget_fw_fleet"'),
        r"je_space_race_widget_fw_fleet"),
    "an orders line's caption on a fleet's page (te_sr_fp_caption)": (
        ("te_sr_fp_caption", 'block "caption_text"'),
        r"je_space_race_widget_(fw_destination|fw_posture|fw_target|fw_battle|fl_col_marines)"),
    "the leg to the destination picked, on a fleet's page (te_sr_fleet_page)": (
        ("te_sr_fleet_page", 'block "fp_leg"'),
        r"je_space_race_widget_fw_\d_leg"),
    "the same with too little propellant aboard (te_sr_fleet_page)": (
        ("te_sr_fleet_page", 'block "fp_leg_short"'),
        r"je_space_race_widget_fw_\d_leg_short"),
    # The Transfer popup (UI pass design § 6).
    "the Transfer popup's Into (te_sr_xf_to_line)": (
        ("te_sr_xf_to_line", 'text = "je_space_race_widget_xf_to_label"'),
        r"je_space_race_widget_xf_to_label"),
    "an Into button (te_sr_xf_to_button)": (
        ("te_sr_xf_to_button", 'block "xf_to_label"'),
        r"je_space_race_widget_xf_(new|to_\d)"),
    **{f"the Transfer popup's {col} head (te_sr_xf_head_row)": (
        ("te_sr_xf_head_row", f'text = "je_space_race_widget_xf_col_{col}"'), f"je_space_race_widget_xf_col_{col}")
       for col in ("now", "move", "stay", "there")},
    "Transfer at the popup's foot (te_sr_xf_go_row)": (
        ("te_sr_xf_go_row", 'text = "je_space_race_widget_xf_go"'),
        r"je_space_race_widget_xf_go"),
    "a role's name in the Transfer popup (te_sr_xf_role_row)": (
        ("te_sr_xf_role_row", 'block "xf_name"'),
        r"je_space_race_widget_xf_role_\w+"),
    "a fleet's refit (te_sr_fleet_row)": (
        ("te_sr_fleet_row", 'text = "je_space_race_widget_fl_refit"'),
        r"je_space_race_widget_fl_refit"),
    "a fleet's landing (te_sr_fleet_row)": (
        ("te_sr_fleet_row", 'block "fl_transit"'),
        r"je_space_race_widget_fl_\d_transit"),
    "a fleet's posture (te_sr_posture_choice, UI pass design § 7)": (
        ("te_sr_posture_choice", 'block "pc_label"'),
        r"je_space_race_widget_fl_posture_\d"),
    "a fleet's stance on its card (te_sr_stance_button, 2026-11-25 design § 5.1)": (
        ("te_sr_stance_button", 'text = "je_space_race_widget_fl_stance_1"'),
        r"je_space_race_widget_fl_stance_\d"),
    "a fleet's stance on its page (te_sr_stance_choice, 2026-11-25 design § 5.1)": (
        ("te_sr_stance_choice", 'block "sc_label"'),
        r"je_space_race_widget_fl_stance_\d"),
    "seize or destroy (te_sr_fleet_row)": (
        ("te_sr_fleet_row", 'text = "je_space_race_widget_fl_seize"'),
        r"je_space_race_widget_fl_(seize|destroy)"),
    # The destination popup (UI pass design § 4): the fleet's heads, the rows'
    # heads, Next Windows' window keys in a narrower cell, and Choose.
    **{f"the destination popup's fleet {col} head (te_sr_dest_slot)": (
        ("te_sr_dest_slot", f'text = "je_space_race_widget_fl_col_{col}"'), f"je_space_race_widget_fl_col_{col}")
       for col in ("where", "strength", "dv", "supply")},
    **{f"the destination popup's {col} column head (te_sr_dest_header_row)": (
        ("te_sr_dest_header_row", f'text = "je_space_race_widget_dp_col_{col}"'), f"je_space_race_widget_dp_col_{col}")
       for col in ("where", "weeks", "dv", "window", "ours", "enemy", "inbound", "battle")},
    "a destination's battle forecast (te_sr_dest_row, 2026-11-25 design § 5.4)": (
        ("te_sr_dest_row", 'text = "je_space_race_widget_fc_tier_1"'),
        r"je_space_race_widget_fc_tier_\d"),
    "a destination's window, open (te_sr_dest_row)": (
        ("te_sr_dest_row", 'text = "je_space_race_widget_win_open"'),
        r"je_space_race_widget_win_open"),
    "a destination's window, waiting (te_sr_dest_row)": (
        ("te_sr_dest_row", 'block "dr_win_wait"'),
        r"je_space_race_widget_win_wait_\w+"),
    # The target popup (UI pass design § 7): Solar System's holder words and
    # Target, and Targeted, in the target row's cells.
    **{f"a world's holder in the target popup: {word} (te_sr_ftarget_row)": (
        ("te_sr_ftarget_row", f'text = "je_space_race_widget_ss_{word}"'), f"je_space_race_widget_ss_{word}")
       for word in ("ours", "unknown", "unclaimed", "free", "occupied", "ruined")},
    "the target popup's Target and Targeted (te_sr_ftarget_row)": (
        ("te_sr_ftarget_row", 'text = "je_space_race_widget_ss_target_button"'),
        r"je_space_race_widget_(ss_target_button|ft_targeted)"),
    # The Marines popup: the marines aboard, the amount, the columns' heads,
    # Due, Land and Embark.
    "the Marines popup's marines aboard (te_sr_land_slot)": (
        ("te_sr_land_slot", 'text = "je_space_race_widget_ld_aboard"'), r"je_space_race_widget_ld_aboard"),
    **{f"the Marines popup's {col} column head (te_sr_land_slot)": (
        ("te_sr_land_slot", f'text = "je_space_race_widget_ld_col_{col}"'), f"je_space_race_widget_ld_col_{col}")
       for col in ("colony", "marines", "garrison")},
    "the Marines popup's garrison order (te_sr_land_row)": (
        ("te_sr_land_row", 'text = "je_space_race_widget_ld_due"'), r"je_space_race_widget_ld_due"),
    "the Marines popup's Land (te_sr_land_row)": (
        ("te_sr_land_row", 'text = "je_space_race_widget_ld_button"'), r"je_space_race_widget_ld_button"),
    "the Marines popup's Embark (te_sr_land_row)": (
        ("te_sr_land_row", 'text = "je_space_race_widget_ld_embark_button"'), r"je_space_race_widget_ld_embark_button"),
    "the Marines popup's amount label (te_sr_land_slot)": (
        ("te_sr_land_slot", 'text = "je_space_race_widget_ld_amount"'), r"je_space_race_widget_ld_amount"),
    "a destination's Choose and Chosen (te_sr_dest_row)": (
        ("te_sr_dest_row", 'text = "je_space_race_widget_dp_choose"'),
        r"je_space_race_widget_dp_(choose|chosen)"),
    # Locations is a strip of icons and figures (owner, 2026-11-14): its captions and statuses are hovers.
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
    # Space Command (the owner, 2026-11-25): Launch, the two toggles as "Label:
    # value", each in a button of its width, the yards' three modes, and the
    # Construction table's heads and role words.
    "Launch (te_sr_sc_button)": (
        ("te_sr_sc_button", 'block "sc_label"'), r"je_space_race_widget_sc_launch"),
    "Auto-launch (te_sr_sc_button_mid)": (
        ("te_sr_sc_button_mid", 'block "sc_label"'), r"je_space_race_widget_sc_auto_(on|off)"),
    "the personnel priority (te_sr_sc_button_wide)": (
        ("te_sr_sc_button_wide", 'block "sc_label"'), r"je_space_race_widget_sc_(hulls|marines)_first"),
    "the yards' modes (te_sr_sc_mode_choice)": (
        ("te_sr_sc_mode_choice", 'block "mode_label"'), r"je_space_race_widget_sc_mode_(full|orders|paused)"),
    **{f"the Construction table's {col} head (te_sr_sc_build_heads)": (
        ("te_sr_sc_build_heads", f'text = "je_space_race_widget_sc_col_{col}"'), f"je_space_race_widget_sc_col_{col}")
       for col in ("role", "fleets", "reserve", "mix", "order")},
    "a role's word in the Construction table (te_sr_sc_build_row)": (
        ("te_sr_sc_build_row", 'block "br_name"'), r"je_space_race_widget_fl_role_(war|rapid|siege|carrier|tender)"),
    # Dismantling (owner, 2026-10-31): a module level coming down, under its name.
    "a module coming down on a colony's page (te_sr_page_mod_row)": (
        ("te_sr_page_mod_row", 'text = "je_space_race_widget_mod_coming_down"'),
        r"je_space_race_widget_mod_coming_down"),
    # A discovery's boon under the module it doubles on a colony's page (2026-11-25).
    "a discovery's boon on a colony's page (te_sr_page_boon_line)": (
        ("te_sr_page_boon_line", None),
        r"je_space_race_widget_mod_boon_\w+"),
}
SECTION_HEADERS = (r"je_space_race_widget_(control_header|rivals_header|colonies_header|solar_system_header|how_header"
                   r"|fleets_header|powers_header|orbit_header|howc_header"
                   r"|sc_header|space_fleets_header|locations_header|tp_title|xf_title|dp_title|ft_title|cw_title|ld_title"
                   r"|fw_title)")


# The Bases move area's lines that name a place, through the controls' custom
# loc (sr_eb_place_*): measured at the longest place name (test_the_move_line_fits).
MOVE_PLACES = r"je_space_race_widget_eb_(from_to|gain|loss|last_from_to)"


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
    body = _type_body(gui, type_name)
    if type_name == "te_sr_colony_row":  # and its page in the Colonies window, filled from the row's blocks
        body += _type_body(gui, "te_sr_colony_page")
    boxes = [b for b in _textboxes(body) if marker in b]
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
    # and the queue's next-module figure, which one picks among four
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
        text = _render(_loc(key), BOUNDED_WORDS[key]() if key in BOUNDED_WORDS else None)
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

    def test_the_base_room_word_counts_the_queue(self):
        """The Base Room cell's word counts queued levels, as its red and its
        "next at" do (owner, 2026-11-04): apart while the split's bounds hold,
        and their sum, at five digits, otherwise."""
        bounds = _ebase_split_bounds()
        self.assertEqual(bounds, {"sr_disp_ebase_queued": 999, "sr_disp_ebase_levels": 9999, "sr_disp_ebase_room": 9999})
        self.assertEqual(_render(_loc("je_space_race_widget_ovc_ebase_word_split"), bounds), "9999 +999 / 9999")
        self.assertEqual(_render(_loc("je_space_race_widget_ovc_ebase_word")), "99999 / 99999")
        for key in ("je_space_race_widget_ovc_ebase_word_split", "je_space_race_widget_ovc_ebase_word_split_past"):
            self.assertIn(key, self.keys)

    def test_the_base_room_cell_names_the_next_place(self):
        """The cell's last line names where the next level goes (ground types design
        § 9.3) in the overview's short forms, measured at the longest place name in the
        cell's column ("next: " would not fit beside the 16-character names); past the
        room it reads "next at -75%"."""
        width, font = _cell(self.gui, "te_banking_ov_word", None)
        self.assertEqual(width, 154)
        names = [_render(_loc(k)) for k in _custom_options("sr_eb_place_next_short")]
        self.assertEqual(len(names), 41 + 2)   # the places, past the room, the fallback
        longest = max(names, key=len)
        self.assertEqual(len(longest), 16)
        self.assertEqual(_render(_loc("je_space_race_widget_ovc_ebase_fig")), longest)
        self.assertLessEqual(len(longest) * UNITS_PER_CHAR[font] * MARGIN, width, longest)
        self.assertEqual(_render(_loc("je_space_race_widget_ovc_ebase_fig_past")), "next at -75%")
        for key in ("je_space_race_widget_ovc_ebase_fig", "je_space_race_widget_ovc_ebase_fig_past"):
            self.assertIn(key, self.keys)

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
        patterns = [p for _, p in CELLS.values()] + [SECTION_HEADERS, MULTILINE, MOVE_PLACES]
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

    def test_the_move_line_fits(self):
        """The Bases view's move area (ground types design § 9.1): each line
        that names a place, at the longest of the 41 places' names, fits the
        line it shows in, its figures at their longest."""
        sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
        import ebase_ground as eg
        longest = max((_loc(f"sr_site_name_{k}") for k in eg.PLACES), key=len)
        self.assertEqual(longest, "Near-Earth Asteroids")
        width, font = _cell(self.gui, "te_sr_eb_move_text", None)
        self.assertEqual(width, 472)
        keys = [k for k in self.keys if re.fullmatch(MOVE_PLACES, k)]
        self.assertEqual(len(keys), 4)
        for key in keys:
            with self.subTest(key=key):
                text = re.sub(r"\[JournalEntry\.GetCountry\.GetCustom\('sr_eb_place_\w+'\)\]", longest, _loc(key))
                self.assertNotIn("GetCustom", text)
                need = len(_render(text)) * UNITS_PER_CHAR[font] * MARGIN
                self.assertLessEqual(need, width, f"{key} renders {_render(text)!r}: {need:.0f} units")
        # no count before a plural unit, so 1 reads right (final review, finding 13)
        self.assertEqual(_render(_loc("je_space_race_widget_eb_toward")), "Levels to move to our assignments: 99999")
        self.assertEqual(_render(_loc("je_space_race_widget_eb_moving")), "Moving since 2136, up to 9999 a month")
        self.assertEqual(_render(_loc("je_space_race_widget_eb_toward_months")), "Months to go: about 99, at up to 9999 a month")
        self.assertEqual(_loc("je_space_race_widget_eb_elsewhere"), "working elsewhere until freed")

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
        "settler_people": "999.9K / 999.9K", "settler_crews": "99/99", "settler_crews_exact": "99/99",
        "settler_crews_short": "99/99", "module_staffing": "100%",
        "module_crews": "99/99", "module_crews_short": "99/99",
        "aut_figure": "100%", "aut_drift": "+0.99", "def_level": "99", "def_integrity": "100%", "def_marines": "99",
        # slots used of slots (4 + 5 technologies + 4 past), base room (60 + 10 levels x 10),
        # what the colony builds of its own (colony management design §§ 4.3, 5)
        "module_slots": "13/9", "module_slots_past": "13/9", "module_bases": "160", "aut_build": "100% (+5.0)",
        # a site's grade beside its room (gen_solar_sites.SITES: -45% to +30%)
        "module_grade": "(\u221245%)",
        # Terraforming (era 13 spec § 7.11): the room its work has added (at most
        # gen_solar_sites.TERRA_MAX_LEVELS shares of +100%), and the years left,
        # shown up to 999 (one level at the least staffing would take longer)
        "terra_pct": "+300%", "terra_years": "999",
    }
    # a module cell (te_sr_mod_cell): a level, two digits with no slots (colony people design § 10),
    # and what is on its way
    CELL = {"cell_level": "88", "cell_pending": "+8"}
    FREE = {"free_people": "999.9K", "free_ties": "100"}
    # A fleet's card: its number and, rolled up, its strength in the head; a bar's
    # figure, now of full (strength, and propellant at 5000 km/s the longest); a
    # ship role's count.
    FLEET = {"fl_number": "VIII", "fl_strength_brief": "9999/9999"}
    GAUGE = {"fg_figure": "9999/9999"}
    ROLE = {"rc_count": "9999"}
    # The Transfer popup's role rows: a role, the marines or the total, now, the amount, after
    TRANSFER = {"xf_now": "99999", "xf_amount": "99999", "xf_stay": "99999", "xf_there": "99999"}
    # The destination popup (UI pass design § 4): the fleet's figures, its
    # propellant to a tenth; a leg's months (611 the longest), its delta-v
    # (gen_launch_windows.LEG_DV_CAP, 9999), our worlds there (six at Jupiter
    # and at Earth) and the enemy's strength there and on its way.
    DEST_FLEET = {"dp_strength": "9999/9999", "dp_dv": "5000.0", "dp_supply": "36"}
    DEST = {"dr_weeks": "9999", "dr_dv_covered": "9999.0", "dr_dv_short": "9999.0", "dr_worlds": "6",
            "dr_enemy": "99999", "dr_inbound": "99999"}
    LOCATION = {"loc_ours": "99999", "loc_others": "99999", "loc_inbound_ours": "9·999"}  # weeks held to 999 (sr_disp_loc_inbound_weeks_<loc>)
    # The Fleets window (the owner, 2026-11-25): a slot's number and strength in
    # its list; on its page a role now of full, its fire to a tenth and, in the
    # drive's tile, a refit's months.
    FLEET_SWITCH = {"switch_number": "VIII", "switch_strength": "9999"}
    # Space Command's Construction table (the owner, 2026-11-25): every fleet's
    # strength in a role and the reserve's, five digits as the overview's; a
    # weight (sr_sc_mix_max), its share, and an order (sr_sc_order_max).
    BUILD = {"br_fleets": "99999", "br_reserve": "99999", "br_mix_weight": "3", "br_mix_share": "100%", "br_order": "9999"}
    FLEET_PAGE = {"fp_role_war": "9999 / 9999", "fp_role_rapid": "9999 / 9999", "fp_role_siege": "9999 / 9999",
                  "fp_role_carrier": "9999 / 9999", "fp_role_tender": "9999 / 9999",
                  "fp_fire_fleets": "99999.9", "fp_fire_defences": "99999.9", "fl_refit": "3", "fp_repair": "100%"}
    FLEET_PAGE_WORDS = ("fl_drive", "fp_dock_none", "fp_dock_earth", "fp_dock_port", "fp_dock_flight")
    # Solar System's line: the inbound weeks, and a world's Habitat cap (1 to 4,
    # gen_solar_sites.SITES' slots; test_a_site_s_habitat_cap holds it to the table)
    SITE = {"site_inbound_ours": "9·999", "site_slots": "4"}
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
        """A colony's page (te_sr_colony_page, in the Colonies window) shows the
        list's figures again, in its tiles' te_sr_page_value (colony management
        design § 8), and the specialization names in full in its module rows."""
        gui = _read(GUI)
        row = _type_body(gui, "te_sr_colony_page")
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

    def test_a_site_s_habitat_cap(self):
        """The slots cell holds one digit: SITE's figure is the largest Habitat
        cap a world has, which no technology changes (gen_solar_sites.SITES'
        slots). The resort cell took the room a second digit had (2026-11-28)."""
        sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
        import gen_solar_sites as gss
        self.assertEqual(self.SITE["site_slots"], str(max(s.slots for s in gss.SITES)))

    def test_a_site_s_resort_room(self):
        """The same line ends in the site's Resort Colony room and draw
        ("100 (+25%)", #1948), as each generated row prints it, the draw with
        its Cultural Centers' points at two digits and a sign. The room is the
        RESORTS table's, three digits at Mars since the owner doubled it
        (2026-11-28)."""
        box = _textbox_with(_type_body(_read(GUI), "te_sr_site_row"), 'block "site_resorts"')
        figures = re.findall(r'blockoverride "site_resorts" \{\s*raw_text = "([^"]*)"', _read(ROWS))
        self.assertEqual(len(figures), 80)   # Solar System's and the colony target popup's
        for figure in figures:
            with self.subTest(figure=figure):
                # The draw's "|+0" (sign first) is a form _render doesn't read: put in its longest.
                text = _render(re.sub(r"\[[^\[\]]*sr_disp_site_resort_draw_\w+'\)\|\+0\]", "+99", figure))
                self.assertLessEqual(len(text) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), text)

    def test_a_site_s_ground_type(self):
        """The same line ends in the site's ground type ("300 (+30%) Metallic",
        ground types design § 9.2): each type's word fits its cell, and the icon,
        the figure's cell and the word's cell, with their spacing, fit the widget
        that holds them and carries the type's hover."""
        body = _type_body(_read(GUI), "te_sr_site_row")
        box = _textbox_with(body, 'block "site_ground"')
        words = re.findall(r'blockoverride "site_ground" \{\s*text = "(sr_ground_\w+)"', _read(ROWS))
        self.assertEqual(len(words), 80)   # Solar System's and the colony target popup's
        for key in sorted(set(words)):
            with self.subTest(key=key):
                text = _render(_loc(key))
                self.assertLessEqual(len(text) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), text)
        m = re.search(r'widget = \{\s*size = \{ (\d+) 22 \}\s*parentanchor = vcenter\s*block "site_bases_tooltip" \{\}'
                      r'(.*?)block "site_ground"', body, re.S)
        self.assertTrue(m, "the base room's widget holds the type's word")
        inner = m.group(2)
        icon = int(re.search(r"icon = \{\s*size = \{ (\d+) \d+ \}", inner).group(1))
        spacing = int(re.search(r"spacing = (\d+)", inner).group(1))
        figure_box = _textbox_with(body, 'block "site_bases"')
        self.assertLessEqual(icon + _width(figure_box) + _width(box) + 2 * spacing, int(m.group(1)))

    def test_a_site_s_second_line_fits_the_row(self):
        """Solar System's line under a site's name (slots, base room and ground
        type, resort room and draw) fits the row inside its margins: the first
        line's 24 icon + 180 name + 122 holder + 65 inbound + 3 x 3 spacing,
        400 in Solar System's 408. Each cell's width is held to its figure by the
        tests above; this holds the cells' sum, which each side's own test missed
        when the ground word and the resort cell landed together (#1950)."""
        body = _type_body(_read(GUI), "te_sr_site_row")
        line = body[body.index("sr_disp_colonies_contested"):]
        spacing = int(re.search(r"spacing = (\d+)", line).group(1))
        margin = int(re.search(r"margin_left = (\d+)", line).group(1))
        widths = [int(w) for w in re.findall(r"\n\t\t\twidget = \{\s*size = \{ (\d+) 22 \}", line)]
        self.assertEqual(len(widths), 3, "slots, base room and resort room")
        self.assertLessEqual(margin + sum(widths) + spacing * (len(widths) - 1), 24 + 180 + 122 + 65 + 3 * 3)

    def test_the_target_popup_s_people_room(self):
        """The colony target popup's line under a site's name starts with the
        world's people room as ours (the owner, 2026-11-22): each figure, as the
        popup's rows print it at the most our room factor reaches ("100,000" at
        Valles Marineris with Space Colonization and Terraforming), fits its cell,
        the icon and the figure fit the cell's widget, and the line with it fits
        the popup's rows inside their margins."""
        gui = _read(GUI)
        cell = _type_body(gui, "te_sr_site_people_cell")
        box = _textbox_with(cell, 'block "people_room"')
        figures = re.findall(r'blockoverride "people_room" \{\s*raw_text = "([^"]*)"', _read(ROWS))
        self.assertEqual(len(figures), 40)   # the popup's rows; Solar System's line has no width for it
        for figure in figures:
            with self.subTest(figure=figure):
                text = _render(figure)
                self.assertLessEqual(len(text) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), text)
        cell_width = int(re.search(r"size = \{ (\d+) 22 \}", cell).group(1))
        icon = int(re.search(r"icon = \{\s*size = \{ (\d+) \d+ \}", cell).group(1))
        self.assertLessEqual(icon + int(re.search(r"spacing = (\d+)", cell).group(1)) + _width(box), cell_width)
        body = _type_body(gui, "te_sr_site_row")
        line = body[body.index("sr_disp_colonies_contested"):]
        self.assertIn('block "site_people" {}', line)
        spacing = int(re.search(r"spacing = (\d+)", line).group(1))
        margin = int(re.search(r"margin_left = (\d+)", line).group(1))
        widths = [cell_width] + [int(w) for w in re.findall(r"\n\t\t\twidget = \{\s*size = \{ (\d+) 22 \}", line)]
        row = int(re.search(r"minimumsize = \{ (\d+) -1 \}", _type_body(gui, "te_sr_target_popup_body")).group(1))
        row_margin = int(re.search(r"margin = \{ (\d+) \d+ \}", body).group(1))
        self.assertLessEqual(margin + sum(widths) + spacing * (len(widths) - 1), row - 2 * row_margin)

    def test_colony_rows(self):
        self._check("te_sr_colony_row", self.FIGURES)
        self._check("te_sr_mod_cell", self.CELL)
        self._check("te_sr_free_row", self.FREE)
        self._check("te_sr_mq_row", self.QUEUE)
        self._check("te_sr_site_row", self.SITE)

    def test_a_base_box(self):
        """The Bases view's boxes (ground types design § 9.1): the levels over
        the room ("99999 / 99999", "→ 99999"), the profit a level ("+999K"
        and the money icon), the levels away; a good's figure at five digits
        (seven to a line); the grade; each ground type's word, as each row
        prints it; and the near-Earth asteroids' name in its wider cell."""
        self._check("te_sr_eb_level_line", {"ebl_levels": "99999 / 99999", "ebl_target": "\u2192 99999",
                                            "ebl_profit": "\u00a3\u00a3+999K", "ebl_away": "99999"})
        self._check("te_sr_eb_good_cell", {"good_figure": "99999"})
        self._check("te_sr_eb_ground_part", {"ebg_grade": "\u221245%"})
        # the word's cell is fixed, so the grades form a column (final review, finding 14)
        self.assertIn("minimumsize = { 116 -1 }", _textbox_with(_type_body(_read(GUI), "te_sr_eb_ground_part"), 'block "ebg_ground"'))
        gui, rows = _read(GUI), _read(ROWS)
        box = _textbox_with(_type_body(gui, "te_sr_eb_ground_part"), 'block "ebg_ground"')
        words = re.findall(r'blockoverride "eb_ground" \{\s*text = "(sr_ground_\w+)"', rows)
        self.assertEqual(len(words), 81)   # the 40 colonies' rows, their pages and the near-Earth box
        for key in sorted(set(words)):
            with self.subTest(key=key):
                self.assertLessEqual(len(_loc(key)) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), _loc(key))
        grade = _textbox_with(_type_body(gui, "te_sr_eb_ground_part"), 'block "ebg_grade"')
        for figure in re.findall(r'blockoverride "eb_grade" \{\s*raw_text = "([^"]*)"', rows):
            self.assertLessEqual(len(figure) * UNITS_PER_CHAR[_font(grade)] * MARGIN, _width(grade), figure)
        name = _textbox_with(_type_body(gui, "te_sr_eb_near_earth_box"), 'text = "sr_site_name_near_earth"')
        self.assertLessEqual(len(_loc("sr_site_name_near_earth")) * UNITS_PER_CHAR[_font(name)] * MARGIN, _width(name))

    def test_a_base_box_fits_a_row(self):
        """A box's lines in a colony row's 472 (the 480 column less the row's
        margins): line 1 with the ground part, line 2's cells and buttons,
        and the seven goods."""
        gui = _read(GUI)
        part = _type_body(gui, "te_sr_eb_ground_part")
        part_width = sum(_width(b) for b in _textboxes(part)) + int(re.search(r"spacing = (\d+)", part).group(1))
        row = _type_body(gui, "te_sr_colony_row")
        self.assertIn("size = { 180 24 }", row)
        self.assertLessEqual(24 + 4 + 180 + 4 + 24 + 4 + part_width, 472)
        line = _type_body(gui, "te_sr_eb_level_line")
        second = line[:line.index('block "ebl_away_visible"')]
        cells = [int(w) for w in re.findall(r"size = \{ (\d+) 24 \}", second)]
        self.assertEqual(cells, [200, 24, 24, 150])
        self.assertLessEqual(28 + sum(cells) + 4 * (len(cells) - 1), 472)
        levels = [_width(b) for b in _textboxes(second) if 'block "ebl_levels"' in b or 'block "ebl_target"' in b]
        self.assertLessEqual(sum(levels) + 4, 200)
        profit = [_width(b) for b in _textboxes(second) if 'block "ebl_profit"' in b or "eb_a_level" in b]
        self.assertLessEqual(sum(profit) + 4, 150)
        away = [_width(b) for b in _textboxes(line[line.index('block "ebl_away_visible"'):])]
        self.assertLessEqual(28 + max(away[:2]) + sum(away[2:]) + 4 * 2, 472)
        cell = int(re.search(r"size = \{ (\d+) 22 \}", _type_body(gui, "te_sr_eb_good_cell")).group(1))
        goods = _type_body(gui, "te_sr_eb_goods_line")
        self.assertEqual(goods.count("te_sr_eb_good_cell = {"), 7)
        spacing, margin = (int(re.search(rf"{w} = (\d+)", goods).group(1)) for w in ("spacing", "margin_left"))
        self.assertLessEqual(margin + 7 * cell + 6 * spacing, 472)
        figure = _textbox_with(_type_body(gui, "te_sr_eb_good_cell"), 'block "good_figure"')
        self.assertLessEqual(17 + _width(figure), cell)

    def test_fleet_and_location_rows(self):
        self._check("te_sr_fleet_row", self.FLEET)
        self._check("te_sr_fl_gauge", self.GAUGE)
        self._check("te_sr_fl_role_cell", self.ROLE)
        self._check("te_sr_sc_build_row", self.BUILD)
        self._check("te_sr_xf_role_row", self.TRANSFER)
        self._check("te_sr_location_cell", self.LOCATION)

    def test_the_fleets_window(self):
        """The Fleets window's list and a fleet's page (the owner, 2026-11-25):
        the list's figures in their cells, the page's in its tiles'
        te_sr_page_value, and the custom-loc names (where, drive, destination,
        target) at their longest option, as on the card."""
        gui = _read(GUI)
        self._check("te_sr_fleet_switch_row", self.FLEET_SWITCH)
        self._check("te_sr_fleet_page", {"fp_number": "VIII"})
        page = _type_body(gui, "te_sr_fleet_page")
        width, font = _width(_type_body(gui, "te_sr_page_value")), _font(_type_body(gui, "te_sr_page_value"))
        shown = re.findall(r'te_sr_page_value = \{[^{}]*block "(\w+)"', page)
        self.assertEqual(sorted(shown), sorted([*self.FLEET_PAGE, *self.FLEET_PAGE_WORDS]))
        for block, figure in self.FLEET_PAGE.items():
            with self.subTest(block=block):
                need = len(figure) * UNITS_PER_CHAR[font] * MARGIN
                self.assertLessEqual(need, width, f"{figure!r}: {need:.0f} units in a {width}-wide cell")
        longest = max((_render(_loc(k)) for k in _custom_options("sr_fl_1_drive_name")), key=len)
        self.assertLessEqual(len(longest) * UNITS_PER_CHAR[font] * MARGIN, width, longest)
        for typ, blocks in (("te_sr_fleet_page", ("fl_where", "fl_target", "fl_pick")), ("te_sr_fleet_switch_row", ("fl_where",))):
            body = _type_body(gui, typ)
            for block in blocks:
                with self.subTest(type=typ, block=block):
                    box = _textbox_with(body, f'block "{block}"')
                    options = _custom_options({"fl_where": "sr_fl_1_where_name", "fl_target": "sr_fl_1_target_name",
                                               "fl_pick": "sr_fl_1_pick_name"}[block])
                    longest = max((_render(_loc(k)) for k in options), key=len)
                    need = len(longest) * UNITS_PER_CHAR[_font(box)] * MARGIN
                    self.assertLessEqual(need, _width(box), f"{longest!r} in {block}")
        # A posture's word in the page's narrower choice (pc_label_width).
        narrow = int(re.search(r'blockoverride "pc_label_width" \{\s*max_width = (\d+)', page).group(1))
        for code in "1234":
            with self.subTest(posture=code):
                word = _render(_loc(f"je_space_race_widget_fl_posture_{code}"))
                self.assertLessEqual(len(word) * UNITS_PER_CHAR["row"] * MARGIN, narrow, word)
        # The list's line: its cells and gaps are the button's width.
        switch = _type_body(gui, "te_sr_fleet_switch_row")
        self.assertIn("size = { 244 26 }", switch)
        cells = [_width(_textbox_with(switch, f'block "{block}"')) for block in ("switch_number", "fl_where", "switch_strength")]
        self.assertEqual(4 + cells[0] + 4 + 20 + 4 + cells[1] + 4 + cells[2] + 4, 244)
        # (The window's and the page's widths are held in test_space_fleet_window.py, from the file.)

    def test_the_destination_popup(self):
        self._check("te_sr_dest_slot", self.DEST_FLEET)
        self._check("te_sr_dest_row", self.DEST)
        gui = _read(GUI)
        # Where the fleet is (custom loc) and every location's name.
        box = _textbox_with(_type_body(gui, "te_sr_dest_slot"), 'block "dp_where"')
        longest = max((_render(_loc(k)) for k in _custom_options("sr_fl_1_where_name")), key=len)
        self.assertLessEqual(len(longest) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), longest)
        box = _textbox_with(_type_body(gui, "te_sr_dest_row"), 'block "dr_name"')
        names = re.findall(r'text = "(sr_loc_name_\w+)"', _read(FLEET_ROWS))
        self.assertTrue(names)
        for key in set(names):
            with self.subTest(key=key):
                self.assertLessEqual(len(_render(_loc(key))) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), key)
        # The body holds the widest row: the rows' cells and their gaps.
        row = _type_body(gui, "te_sr_dest_row")
        cells = [int(w) for w in re.findall(r"(?m)^\t\twidget = \{\n\t\t\tsize = \{ (\d+) 24 \}", row)]
        self.assertEqual(len(cells), 9)
        width = sum(cells) + 4 * (len(cells) - 1) + 2 * 4
        self.assertEqual(width, int(re.search(r"minimumsize = \{ (\d+) -1 \}", _type_body(gui, "te_sr_dest_slot")).group(1)))
        heads = [int(w) for w in re.findall(r"size = \{ (\d+) 20 \}", _type_body(gui, "te_sr_dest_header_row"))]
        self.assertEqual(heads, cells[:8])

    def test_the_target_popup(self):
        """Every world's name fits the target row's name cell (UI pass design § 7)."""
        gui = _read(GUI)
        box = _textbox_with(_type_body(gui, "te_sr_ftarget_row"), 'block "fr_name"')
        names = set(re.findall(r'text = "(sr_site_name_\w+)"', _read(FLEET_ROWS)))
        self.assertEqual(len(names), 40)
        for key in names:
            with self.subTest(key=key):
                self.assertLessEqual(len(_render(_loc(key))) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), key)

    def test_the_land_popup(self):
        """Every world's name fits the Marines row's name cell; the marines
        (aboard of the room, the amount, at a colony) fit theirs; the row's cells
        sum to no more than the slot's width and its heads match them."""
        gui = _read(GUI)
        row = _type_body(gui, "te_sr_land_row")
        box = _textbox_with(row, 'block "lr_name"')
        names = set(re.findall(r'text = "(sr_site_name_\w+)"', _type_body(_read(FLEET_ROWS), "te_sr_land_popup_body")))
        self.assertEqual(len(names), 40)
        for key in names:
            with self.subTest(key=key):
                self.assertLessEqual(len(_render(_loc(key))) * UNITS_PER_CHAR[_font(box)] * MARGIN, _width(box), key)
        self._check("te_sr_land_row", {"lr_marines": "99999"})
        self._check("te_sr_land_slot", {"ld_aboard": "9999/9999", "ld_amount": "99999"})
        cells = [int(w) for w in re.findall(r"(?m)^\t\twidget = \{\n\t\t\tsize = \{ (\d+) 24 \}", row)]
        self.assertEqual(cells, [24, 180, 80, 80, 80, 80])
        slot = _type_body(gui, "te_sr_land_slot")
        self.assertLessEqual(sum(cells) + 3 * (len(cells) - 1) + 2 * 4,
                             int(re.search(r"minimumsize = \{ (\d+) -1 \}", slot).group(1)))
        heads = [int(w) for w in re.findall(r"size = \{ (\d+) 20 \}", slot)]
        self.assertEqual(heads, cells[:4])

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
        Solar System's (with a third while the map has a location picked), and
        the colony target popup's (UI pass design § 5)."""
        for type_name, keys in (("te_sr_sec_solar_system", ("ss_filtered", "ss_all", "ss_one_location")),
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
