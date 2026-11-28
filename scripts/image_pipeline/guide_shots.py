"""
guide_shots.py - The shot manifest: every in-game picture the player guide uses, and the spots that want one (#2056).

One entry per picture. `python3 -m game_qa capture` takes the entries whose recipe is a view (status "pilot" or
"entry") in one session per scene, with nothing of the harness drawn (`start --capture`), and leaves the pictures in a
run folder with a contact sheet of old, new and the difference; `--write` copies the changed ones to their `out`.
`scripts/image_pipeline/guide_shots_stale.py` lists the pictures whose `depends_on` files changed since they were
taken. The manifest is the shot list even for a picture taken by hand.

The owner's rulings (2026-11-25, issue #2056):
  * A figure's state is a minimum, read before the shot (`needs`), not an exact count: "if we had 2 or 80, that is
    still fine, but we probably want at least 1". A need that is not met skips the shot, reported. So a caption
    describes the panel without the counts that change from one capture to the next ("a country holding
    warheads", not "12 warheads"), rewritten once per figure when its first capture replaces it.
  * Base saves are copies of the owner's late saves for now (`te_qa_copy_*`, never the save itself), remade at
    each save-incompatible vanilla version. Keep a figure's needs and setups here, not in the save.
  * Refresh on major releases, or a release known to change what a picture shows; not in every PR.
  * In an event shot the AI picture stays in the crop but is not the focus (`art: True` marks such shots).
  * The guide first, the Workshop second; Workshop carousel images stay local (this manifest is versioned).

Scene keys:
    save            the save's name as `save games/` lists it (a te_qa_copy_* copy of the owner's, or a
                    te_qa_fixture_* save of the harness's)
    as_tag          the country played (a shot can play another: `country`)
    playset         "current" for a copy of a game played on the owner's playset, "mod_only" otherwise
    unresponsive_s  `start --unresponsive-s` (a late save's monthly tick can freeze the window)
    note            what the save is

Shot keys:
    out             the picture's path in the repo, or `workshop/<name>.png` for a Workshop shot: that one stays
                    in the capture folder (the carousel images are kept locally, owner 2026-11-26), and
                    workshop_screenshot_specs.py names it as its `src`
    used_by         the chapters (or "workshop:<spec id>") that show it
    status          pilot (a view recipe run live), entry (a view recipe not yet run live), assisted (needs a
                    scroll, a hover or clicks aimed by hand: not taken by `capture` yet), manual (no session can
                    reach it: the lobby's Game Rules screen), placeholder (the guide marks the spot, no picture yet)
    scene           a SCENES key
    country         the country played for this shot (default: the scene's), or a list of candidates tried in
                    order: the first the save has that meets every need is played (which country holds a state
                    differs from save to save, and a country can be formed away)
    needs           minimums read before the shot: "EXPR OP NUMBER" (OP one of > >= < <= == !=), or a bare
                    trigger that must read yes; `{tag}` is the country played
    setups          {name: effect body}, run (`run-setup`) before the shot: only where the save meets no minimum
    view            the steps that open the view (`game_qa view`; build them with te_window, side_panel or
                    market_tab below)
    scroll          (x, y, notches): turn the wheel there after the view, to bring a section below the panel's
                    fold into it (negative scrolls down; `game_qa wheel`, inside the owner's standing grant of HUD
                    clicks, 2026-11-24). How far a notch goes depends on what the save shows above the section,
                    so look at the contact sheet before trusting a count
    input           a list of steps after the view and the scroll: ("click", x, y), ("wheel", x, y, notches),
                    ("drag", x1, y1, x2, y2), fractions of the window, ("advance", days), time passed on the copy
                    (an event reaches the outliner only then), or ("event", id, option), an event fired and answered
                    at once (a debug event's display refresh). The owner's standing grants cover the HUD
                    (2026-11-24) and the map, the tech tree and map objects (2026-11-26: wheel and drag over the map,
                    clicks on states, buildings and characters), on te_qa_copy_* saves; never with a lens option
                    armed, never the Esc menu, save or load
    hover           (x, y) to leave the cursor on before the shot, fractions of the window (a tooltip)
    event           an event id fired from the console after the view and before the inputs (`event <id>`, which
                    ignores its trigger), answered with its first option after the shot: an event whose text needs
                    no scope but the country's. It arrives minimized: the inputs advance a day and click its
                    outliner row
    crop            a REGIONS key, or (left, top, right, bottom) in fractions of the window
    trim            the empty panel below the content is cut off (capture.trim_bottom): True (the default for the
                    TRIMMED regions) cuts at the first empty run of TRIM_GAP pixels or more, a number sets that run,
                    False keeps the crop whole
    max_kb          the file's cap (images/README.md: about 1 MB)
    depends_on      path globs (git pathspecs) whose change can make the picture stale: the `.gui` files, the
                    scripted GUIs (what a button or section shows), the loc. Not script values: they move figures,
                    which the captions no longer quote
    shows           what the picture shows, for the reviewer who compares the new capture with it
    placeholder     the guide's `<!-- screenshot: ... -->` text, for a placeholder
    art             True when the shot holds an AI picture (an event's, a monument's)
    note            anything else a reviewer or the next entry's author needs

`validate()` returns the problems; test_guide_shots.py runs it.
"""

from __future__ import annotations

import glob
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The window every region below was measured in: the owner's (3840x2160, UI scale 1.5). `capture` refuses any other,
# since a region is a fraction of the window and a side panel's width in pixels follows the UI scale.
WINDOW = (3840, 2160)
UI_SCALE = 1.5

STATUSES = ("pilot", "entry", "assisted", "manual", "placeholder")
TAKEN = ("pilot", "entry")      # what `capture` takes

SCENES = {
    "late_2050": dict(
        save="te_qa_copy_iua2050_20261126", as_tag="USA", playset="mod_only", unresponsive_s=120,
        note="a copy of the owner's February 2050 game as the USA (their exit save of 2026-11-26), loaded on this mod "
             "alone: the owner's other mods (a map mod among them) are not needed to load it"),
    "late_2043": dict(
        save="te_qa_copy_iua2043_20261125", as_tag="USA", playset="mod_only", unresponsive_s=120,
        note="a copy of the owner's June 2043 game as the USA (made 2026-11-25 for the Fleets window session); on "
             "this mod alone, as the 2050 copy of the same game loaded"),
    "mid_1964": dict(
        save="te_qa_copy_usa1964_20261126", as_tag="USA", playset="mod_only", unresponsive_s=120,
        note="a copy of the owner's November 1964 game as the USA (their save of 2026-11-25), for the mid-century "
             "systems: colonial empires still held, a census of an ordinary century"),
    "late_2032": dict(
        save="te_qa_copy_iua_20261124", as_tag="USA", playset="current", unresponsive_s=120,
        note="a copy of the owner's December 2032 game as the USA (the GUI evaluation night of 2026-11-24)"),
}

# Regions, in fractions of the window at WINDOW and UI_SCALE.
REGIONS = {
    # A vanilla side panel (default_block_window, 540 UI units wide), and so the Timeline Extended window as a side
    # panel: from under the top bar to the bottom of the screen, the sidebar left out.
    "side_panel": (0.0203, 0.0500, 0.2427, 1.0),
    # The same from its tab strip down (the owner's framing, 2026-11-26: the panel's title banner left out, as in the
    # hand-taken pictures). The banner's height depends on the panel: measured on the crops of capture
    # 20261126T041745Z (side_panel, y 108 to 2160).
    "panel_tabs": (0.0203, 0.1269, 0.2427, 1.0),        # Military, Market, Society: a plain banner
    "panel_tabs_tall": (0.0203, 0.1972, 0.2427, 1.0),   # Budget (the balance), Diplomacy (the rank's crest)
    "te_panel_tabs": (0.0203, 0.1426, 0.2427, 1.0),     # the Timeline Extended window: its tab grid, under Map Room
    # The Timeline Extended window full screen: its three columns, under the tab strip (python_tools.md, the GUI
    # evaluation night).
    "te_window_columns": (0.17, 0.11, 0.83, 1.0),
    # One column of it (te_ui_columns_three, shared by every tab), with its section header: measured on the Space
    # Race tab (run 20261126T040928Z, crop_59), not yet on another tab.
    "te_column_1": (0.182, 0.205, 0.390, 1.0),
    "te_column_2": (0.398, 0.205, 0.602, 1.0),
    "te_column_3": (0.613, 0.205, 0.820, 1.0),
    "full": (0.0, 0.0, 1.0, 1.0),
    # The Timeline Extended window full screen from its section header down, the tab strip left out: the framing of
    # the owner's Workshop shots of 2026-11-06 (Pictures/Screenshot 2026-11-06 134035.png and its kin).
    "te_window_body": (0.182, 0.175, 0.821, 1.0),
    # A state panel from its tab row: its banner is two lines (the state, its owner), so the row sits lower.
    "state_panel_tabs": (0.0203, 0.1287, 0.2427, 1.0),
}

TRIMMED = ("side_panel", "panel_tabs", "panel_tabs_tall", "te_panel_tabs", "te_column_1", "te_column_2",
           "te_column_3")
TRIM_GAP = 160      # pixels: a panel's sections are under 80 apart; the Strategic Reserve's footer sits 640 below

CAPTURE_KEY = "te_qa_capture"   # game_qa.capture_gui.CAPTURE_KEY: debug mode's counters hide while it is set
TE_WINDOW_KEYS = ("com_open_window", "te_systems_window_tab", "te_systems_window_wide")
# The mod's popups (a history chart opened full size, the Nation tab's charts): one opened by a shot's click stays up
# over the next view (live 2026-11-26), so every shot clears them first.
POPUP_KEYS = ("te_popup", "te_ni_chart", "sr_fleet_focus")


# A side panel keeps its scroll position when it is closed and opened again (live 2026-11-26: a view after a five-notch
# scroll opened five notches down), so a recipe that scrolls first turns the wheel up past the top, where it clamps.
# A notch moves a side panel 90 pixels at the manifest's window and scale.
SIDE_PANEL_WHEEL = (0.13, 0.6)


# The camera on the played country's capital, then a click on the land beside it and the wheel to the panel's end:
# in the 2050 copy (USA, Washington) the click lands in New Jersey. Measured 2026-11-26 at UI scale 1.5.
STATE_BY_CAPITAL = [("click", 0.594, 0.36), ("wheel", 0.13, 0.6, -40)]


# The tech tree's Reset button, right of its search box (TechTreePanel.Reset<Tab>View): the tree's top at its first
# zoom, the one known start for a pan. Measured 2026-11-26 at UI scale 1.5.
TECH_TREE_RESET = [("click", 0.9694, 0.2523)]


# The Map Room from the Timeline Extended window: its Map Room button (top left of the side panel) opens the page on
# the map picked last (a view's sgui: pick), and closes the window. Then the camera, from the capital (zoom:capital):
# the wheel zooms about the cursor and by uneven steps, and a drag does not pan the map, so these notches, in this
# order, are what put the Atlantic between South America and Africa (1964 copy, 2026-11-26, UI scale 1.5).
MAP_ROOM_BUTTON = ("click", 0.1518, 0.1394)
MAP_ROOM_ATLANTIC = [MAP_ROOM_BUTTON, ("wheel", 0.6, 0.5, -8), ("wheel", 0.75, 0.65, 2), ("wheel", 0.75, 0.65, -1),
                     ("wheel", 0.55, 0.5, -1), ("wheel", 0.82, 0.62, 1)]


# A country played by a tag shows its Colonial Empire rows only after its next monthly pulse
# (colonial_empire_display_ready waits for colonial_empire_tier, set for a played country): the debug event's
# sixth option runs colonial_empire_refresh_display at once, touching nothing else.
COLONIAL_REFRESH = [("event", "te_debug_colonial_empire.1", 5)]


def side_scroll(notches: int) -> list[tuple]:
    """The input steps that scroll a side panel `notches` down from its top."""
    x, y = SIDE_PANEL_WHEEL
    return [("wheel", x, y, 40), ("wheel", x, y, -notches)]


def te_window(tab: str, wide: bool = False, keys: dict | None = None) -> list[list[str]]:
    """The Timeline Extended window on `tab` (a TABS key of scripts/generators/gen_te_systems_window.py), as a side
    panel or full screen, with `keys` ({client-side key: value}) set too: a section opened or closed."""
    step = ["set:te_systems_window_tab=%s" % tab]
    step.append("set:te_systems_window_wide=yes" if wide else "clear:te_systems_window_wide")
    step += ["set:%s=%s" % (k, v) for k, v in (keys or {}).items()]
    step.append("set:com_open_window=te_systems_window")
    return [step]


def side_panel(name: str, tab: str, keys: dict | None = None) -> list[list[str]]:
    """A vanilla side panel on one of its tabs (`InformationPanelBar.OpenPanelTab`): the mod's own tabs there are
    te_banking, te_tax_code and te_breakdown (budget), te_nuclear and te_covert (military), te_ch (society), te_un
    (diplomatic_overview), te_demog (pops_overview)."""
    return [["set:%s=%s" % (k, v) for k, v in (keys or {}).items()] + ["panel:%s:%s" % (name, tab)]]


def market_tab(tab: str, keys: dict | None = None) -> list[list[str]]:
    """The played country's market panel on one of its tabs: te_global_warming, te_strategic_reserve."""
    return [["set:%s=%s" % (k, v) for k, v in (keys or {}).items()] + ["market:%s" % tab]]


def has_je(key: str) -> str:
    return "c:{tag} = { has_journal_entry = %s }" % key


WORKSHOP = "workshop/"


def _workshop_specs() -> set[str]:
    """The image names of workshop_screenshot_specs.py, read without importing it beside this module's name."""
    from importlib import util
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workshop_screenshot_specs.py")
    spec = util.spec_from_file_location("workshop_screenshot_specs_for_guide_shots", path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.SPECS)


G = "docs/player_guide/"
IMG = G + "images/"
LOC = "localization/english/"

SHOTS = {
    # ---- the pilot: a view recipe each, run live
    "banking_tab": dict(
        out=IMG + "banking_tab.png", used_by=[G + "04-banking.md"], status="pilot", scene="late_2050",
        needs=[has_je("je_banking_cycle")],
        view=side_panel("budget", "te_banking"), crop="panel_tabs_tall",
        depends_on=["gui/budget_panel.gui", "gui/journal_entry_widgets/banking_*.gui", "common/scripted_guis/*banking*", LOC + "*banking*"],
        shows="the Banking tab of the Budget panel: the four bars, the overview's icons, Active Policies and the start "
              "of Monetary Policy"),
    "nuclear_tab_armed": dict(
        out=IMG + "nuclear_tab_armed.png", used_by=[G + "14-nuclear.md"], status="pilot", scene="late_2050",
        needs=["nd_stockpile > 0"],
        view=side_panel("military", "te_nuclear"), crop="panel_tabs",
        depends_on=["gui/panel_military.gui", "gui/journal_entry_widgets/nuclear_*.gui",
                    "common/scripted_guis/*nuclear*", LOC + "*nuclear*"],
        shows="the Nuclear tab of the Military panel for a country holding warheads: the overview, The Program with "
              "its progress bar, Nuclear Posture, and the start of Forces"),
    "global_warming_tab": dict(
        out=IMG + "global_warming_tab.png", used_by=[G + "15-climate.md"], status="pilot", scene="late_2043",
        needs=["temperature_anomaly_display > 0.5"],
        view=market_tab("te_global_warming"), crop="panel_tabs",
        depends_on=["gui/market_panel.gui", "gui/journal_entry_widgets/global_warming_widget.gui",
                    "common/scripted_guis/*warming*", LOC + "*warming*"],
        shows="the Climate tab of the Market panel with a tier in force: the overview (tier, Market Leader, Penalty, "
              "the Temperature bar and its threshold line, the emissions table and the two pies) and the start of "
              "Mitigation Policies"),
    "hegemony_tab": dict(
        out=IMG + "hegemony_tab.png", used_by=[G + "11-influence.md"], status="pilot", scene="late_2050",
        needs=[has_je("je_cultural_hegemony")],
        view=side_panel("society", "te_ch"), crop="panel_tabs",
        depends_on=["gui/culture_panel.gui", "gui/journal_entry_widgets/cultural_hegemony_widget.gui",
                    "common/scripted_guis/*hegemony*", LOC + "*hegemony*"],
        shows="the Hegemony tab of the Society panel: the overview, Top Cultural Powers with each one's change since "
              "the last recount, Cultural Programs, and where our pull comes from"),
    "un_tab_overview": dict(
        out=IMG + "un_tab_overview.png", used_by=[G + "10-united-nations.md"], status="pilot", scene="late_2050",
        needs=[has_je("je_united_nations")],
        view=side_panel("diplomatic_overview", "te_un"), crop="panel_tabs_tall",
        depends_on=["gui/diplomatic_overview.gui", "gui/journal_entry_widgets/un_*.gui",
                    "common/scripted_guis/*un_*", LOC + "*united_nations*"],
        shows="the UN tab of the Diplomacy panel: the overview (membership, tier, standing, the authority bar, the "
              "countries, GDP and population pies, the Security Council, the agencies and the headquarters) and "
              "Status"),
    "grand_monuments_tab": dict(
        out=IMG + "grand_monuments_tab.png", used_by=[G + "02-timeline.md"], status="pilot", scene="late_2050",
        needs=["gm_live_count_upheld > 0"],
        view=te_window("grand_monuments"), crop="te_panel_tabs",
        depends_on=["gui/te_systems_window*.gui", "gui/journal_entry_widgets/grand_monuments_widget.gui",
                    "common/scripted_guis/*monument*", LOC + "*monument*"],
        shows="the Grand Monuments tab of the Timeline Extended window: the overview's four counts, National Effects "
              "with Interest Group Approval, and the start of Our Monuments"),
    # ---- entries: a view recipe, not yet run live
    "covert_tab": dict(
        out=IMG + "covert_tab.png", used_by=[G + "11-influence.md"], status="pilot", scene="late_2043",
        needs=[has_je("je_covert_warfare"), "covert_operations_active > 0"],
        view=side_panel("military", "te_covert"), crop="panel_tabs",
        depends_on=["gui/panel_military.gui", "gui/journal_entry_widgets/covert_operations_widget.gui",
                    "common/scripted_guis/*covert*", LOC + "*covert*"],
        shows="the Covert tab of the Military panel: the overview, the Operations section with operation rows, and "
              "the start of Funding"),
    "strategic_reserve_tab": dict(
        out=IMG + "strategic_reserve_tab.png", used_by=[G + "03-economy.md"], status="entry", scene="late_2050",
        needs=[has_je("je_strategic_reserve")],
        view=market_tab("te_strategic_reserve", keys={"st_res_row_grain_open": "yes"}), crop="panel_tabs",
        depends_on=["gui/market_panel.gui", "gui/journal_entry_widgets/strategic_reserve_widget.gui",
                    "common/scripted_guis/*strategic_reserve*", LOC + "*strategic_reserve*"],
        shows="the Strategic Reserve tab of the Market panel: the overview above the Reserve Inventory, the Fill by "
              "Month chart and the start of its Policy Settings",
        note="a good's row is opened by its key (st_res_row_<good>_open): Grain, which holds stock in the 2050 copy (its Ammunition, the hand-taken picture's, was empty)"),
    "solar_system_colonization_tab": dict(
        out=IMG + "solar_system_colonization_tab.png", used_by=[G + "16-space.md"], status="entry",
        scene="late_2043",
        needs=[has_je("je_space_race_solar_colonization"),
               "NOT = { has_variable = sr_completed_solar_colonization }"],
        view=te_window("space_race"), crop="te_panel_tabs",
        depends_on=["gui/te_systems_window*.gui", "gui/journal_entry_widgets/space_race_widget.gui",
                    "gui/journal_entry_widgets/sr_*.gui", "common/scripted_guis/*space*", LOC + "*space_race*"],
        shows="the Space Race tab of the Timeline Extended window on Solar System Colonization: the overview and "
              "Program row, Mission Control with the approach buttons and the funding stepper, and Rivals"),
    "banking_rate": dict(
        out=IMG + "banking_rate.png", used_by=[G + "04-banking.md"], status="entry", scene="late_2050",
        needs=[has_je("je_banking_cycle")],
        view=te_window("banking", wide=True), crop="te_column_2",
        depends_on=["gui/journal_entry_widgets/banking_*.gui", "common/scripted_guis/*banking*", LOC + "*banking*"],
        shows="the Monetary Policy block of the banking dashboard: the rates and the Rate Target stepper, the "
              "exchange rate, what borrowing costs, prices, and the central bank's stance, delegation and mandate",
        note="in the side panel the block is below the fixed overview (taken live 2026-11-26: the top of the tab); "
             "the full-screen window puts it alone in column 2 (banking_layout_widget.gui)"),
    "un_authority_moving": dict(
        out=IMG + "un_authority_moving.png", used_by=[G + "10-united-nations.md"], status="entry", scene="late_2050",
        needs=[has_je("je_united_nations")],
        view=te_window("united_nations", wide=True), crop="te_column_2",
        depends_on=["gui/journal_entry_widgets/un_*.gui", "common/scripted_guis/*un_*", LOC + "*united_nations*"],
        shows="the Why UN Authority Is Moving section: authority and its target, the pillars, the tier, the charter, "
              "the champions and underminers, Recent Entries collapsed",
        note="in the side panel the section is below the fixed overview and the Assembly; the full-screen window "
             "starts column 2 with it (te_un_wide_sections, un_layout_widget.gui)"),
    "un_general_assembly": dict(
        out=IMG + "un_general_assembly.png", used_by=[G + "10-united-nations.md"], status="entry",
        scene="late_2050",
        needs=[has_je("je_united_nations"), "has_global_variable = un_active_resolution"],
        view=side_panel("diplomatic_overview", "te_un", keys={"un_chamber_delegations_open": "yes"}),
        input=side_scroll(15), crop="panel_tabs_tall",
        depends_on=["gui/journal_entry_widgets/un_chamber_widget.gui", "common/scripted_guis/*un_*",
                    LOC + "*united_nations*"],
        shows="the General Assembly with a resolution in session: what happens if it carries or falls, how the "
              "Assembly reads our position, the vote buttons and the start of Delegations",
        note="the need is un_chamber_vote_sgui's is_shown (read yes live 2026-11-26). The Assembly's header sits "
             "1,464 pixels down the tab under the fixed overview, so 15 notches bring it under the tab strip"),
    "UN_lobbying": dict(
        out=IMG + "UN_lobbying.png", used_by=[G + "10-united-nations.md"], status="entry", scene="late_2050",
        needs=[has_je("je_united_nations"), "has_global_variable = un_active_resolution"],
        view=side_panel("diplomatic_overview", "te_un", keys={"un_chamber_delegations_open": "yes"}),
        input=side_scroll(21), crop="panel_tabs_tall",
        depends_on=["gui/journal_entry_widgets/un_chamber_widget.gui", LOC + "*united_nations*"],
        shows="the chamber's Delegations section: each row's band and any campaign on it, with the campaign and "
              "pledge buttons",
        note="Delegations (opened by its key) sits inside the Assembly, below the fixed overview and the "
             "resolution's text, whose length varies: 21 notches put its header near the top with the 2050 copy's "
             "UN Peacekeeping Deployment; another resolution moves it"),
    "nuclear_taboo": dict(
        out=IMG + "nuclear_taboo.png", used_by=[G + "14-nuclear.md"], status="entry", scene="late_2050",
        country=["JAP", "KOR", "GER", "SWE", "ARG", "MEX", "BRZ", "SAF"],
        needs=["nd_stockpile == 0", "nuclear_program_display_state == 7"],
        view=side_panel("military", "te_nuclear"), crop="panel_tabs",
        depends_on=["gui/journal_entry_widgets/nuclear_*.gui", LOC + "*nuclear*"],
        shows="the Nuclear tab for a country with no warheads and a Renounced posture: Reputation, The Nuclear Taboo "
              "with its two charts, Delivery and Defense, and the start of Nuclear Powers",
        note="state 7 of nuclear_program_display_state is the overview's Renounced. In the 2043 copy (2026-11-26) "
             "no candidate had it: JAP and KOR read 8 (Disarmed), GER held warheads, the rest do not exist. Widen "
             "the list, or play a country into renouncing, before this picture can be retaken"),
    # ---- assisted: the view is not enough (a scroll, a hover, a click on a map object)
    "construction_market": dict(
        out=IMG + "construction_market.png", used_by=[G + "03-economy.md"], status="entry", scene="late_2050",
        view=[["construction"]], input=[("click", 0.1701, 0.2199)], crop=(0.0203, 0.1713, 0.2427, 0.4097),
        depends_on=["gui/*construction*.gui", LOC + "*construction*"],
        shows="the Construction Market section under Fixed Budget: what the government spends and buys, private "
              "investors' share, the market's balance",
        note="the click is the section's Fixed Budget button (the copy's mode is changed for the shot); the box is "
             "the section under Fixed Budget, two rows taller than under Fixed Quantity"),
    "state_panel": dict(
        out=IMG + "state_panel.png", used_by=[G + "08-states.md"], status="entry", scene="late_2050",
        view=[["zoom:capital"]], input=STATE_BY_CAPITAL, crop="state_panel_tabs", trim=True,
        depends_on=["gui/states_panel.gui", "gui/te_state_panel_widgets.gui", LOC + "*state*"],
        shows="a state panel's Overview scrolled to its end: the mod's tiles in two columns, Arable Land and Local "
              "Climate at their heads, and the tourism card last",
        note="New Jersey, clicked on the map beside the capital (Washington's trophy list pushes its tourism card "
             "far down); the wheel takes the panel to its end"),
    "UN_mission": dict(
        out=IMG + "UN_mission.png", used_by=[G + "10-united-nations.md"], status="assisted", scene="late_2050",
        depends_on=["gui/te_state_panel_widgets.gui", LOC + "*united_nations*"],
        shows="the UN Mission tile on a state panel: an aid mission under way, its strength and progress",
        note="a state panel of a state with a mission: as state_panel, and a need on the mission"),
    "settlement_authority": dict(
        out=IMG + "settlement_authority.png", used_by=[G + "08-states.md"], status="assisted", scene="late_2050",
        depends_on=["gui/building*.gui", LOC + "*settlement*"],
        shows="a Settlement Authority's building panel with its three production method groups and the settlers "
              "tooltip",
        note="a building panel and a hover"),
    "tech_tree_production_era_6_7_8": dict(
        out=IMG + "tech_tree_production_era_6_7_8.jpg", used_by=[G + "02-timeline.md"], status="entry",
        scene="late_2050", view=[["panel:tech_tree:production"]],
        input=TECH_TREE_RESET + [("wheel", 0.5, 0.5, -40), ("drag", 0.5, 0.95, 0.5, 0.3), ("wheel", 0.143, 0.424, 2),
                                 ("drag", 0.5, 0.6, 0.43, 0.6)],
        crop=(0.05, 0.232, 0.815, 0.935), depends_on=["common/technology/technologies/*.txt", "gui/technology*.gui"],
        shows="part of the production tree in eras 6 to 8, the era numeral under each icon",
        note="from the Reset (the tree's top), the widest zoom and one drag put eras VI to VIII mid-screen; two "
             "notches about (0.143, 0.424) fill the frame with them, and a short drag left clears the search box"),
    "disband_company": dict(
        out=IMG + "disband_company.png", used_by=[G + "09-diplomacy.md"], status="assisted", scene="late_2050",
        depends_on=["common/treaty_articles/*", LOC + "*treat*"],
        shows="choosing the company for a Disband Company article: the conceding country's companies",
        note="the treaty draft window, and an article picked: clicks"),
    "principle_picker_tier_v": dict(
        out=IMG + "principle_picker_tier_v.png", used_by=[G + "09-diplomacy.md"], status="assisted",
        scene="late_2050", depends_on=["common/power_bloc_principles/*", "gui/power_bloc*.gui"],
        shows="the Change or Upgrade Companies V window: every principle group in tiers I to V",
        note="a power bloc leader's principle window: clicks"),
    "combined_arms_full_spectrum": dict(
        out=IMG + "combined_arms_full_spectrum.png", used_by=[G + "13-military.md"], status="assisted",
        scene="late_2050", depends_on=["common/character_traits/*", LOC + "*trait*"],
        shows="a general's traits with all six Combined Arms traits",
        note="a character panel (OpenCharacterPanel takes a Character): clicks, or a setup that grants the traits"),
    # ---- manual: no session reaches it
    "game_rules": dict(
        out=IMG + "game_rules.png", used_by=[G + "01-introduction.md"], status="manual",
        depends_on=["common/game_rules/*", LOC + "*game_rule*"],
        shows="the mod's rules on the Game Rules screen, with the Cultural Hegemony tooltip open",
        note="the lobby's Game Rules screen: a session starts on a save, so this one is taken by hand"),
    # ---- the Workshop carousel (out under workshop/: kept in the capture folder, never in the repo; the annotator
    # reads them with --src <capture folder>). Ids are the specs' names in workshop_screenshot_specs.py.
    "ws_01_state_panel": dict(
        out=WORKSHOP + "ws_01_state_panel.png", used_by=["workshop:01_state_panel"], status="entry",
        scene="late_2050", view=[["zoom:capital"]], input=STATE_BY_CAPITAL, crop="state_panel_tabs", trim=True,
        depends_on=["gui/states_panel.gui", "gui/te_state_panel_widgets.gui"],
        shows="a state panel scrolled to its end: the mod's tiles (Local Climate, Dynastic Wealth among them) and "
              "the tourism card"),
    "ws_02_leading_cause_map": dict(
        out=WORKSHOP + "ws_02_leading_cause_map.png", used_by=["workshop:02_leading_cause_map"], status="entry",
        scene="mid_1964", needs=["te_demog_cohorts_run = yes"],
        view=[["zoom:capital"]] + te_window("nation") + [["clear:te_je_see_through",
                                                           "sgui:te_jmap_pick_leading_cause_sgui"]],
        input=MAP_ROOM_ATLANTIC, hover=(0.6, 0.47), crop=(0.245, 0.06, 0.83, 0.94),
        depends_on=["gui/te_map_widgets.gui", "common/scripted_guis/te_journal_map_picks_generated.txt"],
        shows="the Map Room's Leading Cause of Death map over the Atlantic, a striped state's tooltip open",
        note="the hover is Inner Mauritania in the 1964 copy: infection first, chronic illness in the stripes"),
    "ws_03_map_room": dict(
        out=WORKSHOP + "ws_03_map_room.png", used_by=["workshop:03_map_room"], status="entry", scene="mid_1964",
        needs=["te_demog_cohorts_run = yes"],
        view=[["zoom:capital"]] + te_window("nation") + [["clear:te_je_see_through",
                                                           "set:te_jmap_cat_population_open=yes",
                                                           "set:te_jmap_cat_living_open=yes",
                                                           "sgui:te_jmap_pick_life_expectancy_sgui"]],
        input=MAP_ROOM_ATLANTIC, hover=(0.12, 0.93), crop=(0.0203, 0.05, 0.70, 0.80),
        depends_on=["gui/te_map_widgets.gui", "common/scripted_guis/te_journal_map_picks_generated.txt"],
        shows="the Map Room page, two of its categories open, beside the Life Expectancy map",
        note="a category opens on its key (te_jmap_cat_<name>_open)"),
    "ws_04_united_nations": dict(
        out=WORKSHOP + "ws_04_united_nations.png", used_by=["workshop:04_united_nations"], status="pilot",
        scene="late_2050", needs=[has_je("je_united_nations")],
        view=te_window("united_nations", wide=True), crop="te_window_body",
        depends_on=["gui/journal_entry_widgets/un_*.gui"],
        shows="the UN tab full screen: the overview and Security Council, Why UN Authority Is Moving and Missions in "
              "the Field, Our Obligations"),
    "ws_05_demographics": dict(
        out=WORKSHOP + "ws_05_demographics.png", used_by=["workshop:05_demographics"], status="entry",
        scene="mid_1964", needs=["te_demog_cohorts_run = yes"], view=te_window("demographics", wide=True),
        crop="te_window_body", depends_on=["gui/te_demographics_widgets.gui"],
        shows="the Demographics tab full screen: the census, the population pyramid, causes of death",
        note="the 1964 copy: the 2050 game's census is of its speculative era (life expectancy 309 years)"),
    "ws_06_grand_monuments": dict(
        out=WORKSHOP + "ws_06_grand_monuments.png", used_by=["workshop:06_grand_monuments"], status="entry",
        scene="late_2050", needs=[has_je("je_grand_monuments")],
        view=te_window("grand_monuments", wide=True), crop="te_window_body",
        depends_on=["gui/journal_entry_widgets/grand_monuments_widget.gui"],
        shows="the Grand Monuments tab full screen: our monuments, national effects, trophies"),
    "ws_07_colonial_empire": dict(
        out=WORKSHOP + "ws_07_colonial_empire.png", used_by=["workshop:07_colonial_empire"], status="entry",
        scene="mid_1964", country=["TUR", "RUS"],
        needs=[has_je("je_colonial_empire"), "colonial_empire_disp_colonies > 0"],
        view=te_window("colonial_empire", wide=True), input=COLONIAL_REFRESH, crop="te_window_body",
        depends_on=["gui/journal_entry_widgets/colonial_empire*.gui", "gui/journal_entry_widgets/te_ce*.gui"],
        shows="the Colonial Empire tab full screen: stability and the colony list with its Release buttons",
        note="in the 1964 copy only Turkey (two colonies) and Russia (one territory) hold the entry"),
    "ws_08_space_race": dict(
        out=WORKSHOP + "ws_08_space_race.png", used_by=["workshop:08_space_race"], status="entry",
        scene="late_2043", view=te_window("space_race", wide=True), crop="te_window_body",
        depends_on=["gui/journal_entry_widgets/space_race_widget.gui", "gui/journal_entry_widgets/sr_*.gui"],
        shows="the Space Race tab full screen on Mission Control: the milestones, the program, the colonies"),
    "ws_10_technology": dict(
        out=WORKSHOP + "ws_10_technology.png", used_by=["workshop:10_technology"], status="entry", scene="late_2050",
        view=[["panel:tech_tree:production"]],
        input=TECH_TREE_RESET + [("wheel", 0.5, 0.5, -40)] + [("drag", 0.5, 0.95, 0.5, 0.3)] * 2
              + [("wheel", 0.55, 0.45, 2)],
        crop=(0.022, 0.232, 0.978, 0.955), depends_on=["common/technology/technologies/*"],
        shows="the production tree's last eras, from E-Commerce and Machine Learning down",
        note="the tree keeps its pan and zoom across a close and doesn't stop a drag at its end, so the recipe starts "
             "from its Reset button (TechTreePanel.ResetProductionView: the tree's top). Its wheel zooms by a clamped "
             "step: -40 is the widest view, where two drags reach the last row, and two notches in make the names "
             "readable"),
    "ws_11_banking": dict(
        out=WORKSHOP + "ws_11_banking.png", used_by=["workshop:11_banking"], status="entry", scene="late_2050",
        needs=[has_je("je_banking_cycle")], view=te_window("banking", wide=True),
        input=[("click", 0.6906, 0.3456), ("click", 0.5269, 0.3378)], crop="te_window_body",
        depends_on=["gui/journal_entry_widgets/banking_*.gui"],
        shows="the banking dashboard full screen with the Banking Cycle Value chart opened full size over 20 years",
        note="the clicks are the History column's first chart button (te_popup opens it, cleared before every "
             "shot) and the popup's 20 Years. Measured on the 2050 copy, whose history began in 2030"),
    "ws_09_laws": dict(
        out=WORKSHOP + "ws_09_laws.png", used_by=["workshop:09_laws"], status="entry", scene="late_2050",
        view=[["panel:politics:laws"]], input=[("wheel", 0.5, 0.6, 40), ("wheel", 0.5, 0.6, -14)],
        crop=(0.022, 0.125, 0.98, 1.0), depends_on=["common/laws/*", "common/law_groups/*"],
        shows="the Politics panel's Laws tab across the screen, scrolled to the mod's law groups (Inheritance Laws "
              "first in the first column)",
        note="the list scrolls 90 pixels a notch; 14 from the top put Inheritance Laws first in 2050"),
    "ws_13_event": dict(
        out=WORKSHOP + "ws_13_event.png", used_by=["workshop:13_nuclear_event"], status="entry", scene="mid_1964",
        event="space_race_events.32", input=[("advance", 1), ("click", 0.922, 0.2305)], crop=(0.265, 0.17, 0.73, 0.835),
        art=True, depends_on=["gui/eventwindow.gui", "events/space_race_events.txt"],
        shows="a space race event window (Who Goes to the Moon?), its picture, text and three options",
        note="an event whose text names nothing but the country; the click is its outliner row, first under Active "
             "Journal Entries in the 1964 copy (under Civil Rights Movement)"),
    "ws_c1_colonies": dict(
        out=WORKSHOP + "ws_c1_colonies.png", used_by=["workshop:c1_colonies"], status="entry", scene="late_2050",
        needs=["sr_disp_colonies_held > 0"], art=True,
        view=te_window("space_race", wide=True) + [["set:sr_colony_focus=valles_marineris", "set:te_popup=sr_colony"]],
        crop=(0.25, 0.21, 0.75, 0.795), depends_on=["gui/journal_entry_widgets/space_race_widget.gui",
                                                      "gui/journal_entry_widgets/sr_sites_generated_rows.gui"],
        shows="a candidate: the Our Colonies window on Valles Marineris, every colony listed at its left",
        note="a site's row opens it (sr_colony_focus, then te_popup=sr_colony); Valles Marineris, a colony of the "
             "USA in the 2050 copy"),
    "ws_c2_fleets": dict(
        out=WORKSHOP + "ws_c2_fleets.png", used_by=["workshop:c2_fleets"], status="entry", scene="late_2050",
        needs=["sr_disp_fl_1 > 0"], art=True,
        view=te_window("space_race", wide=True) + [["set:sr_fleet_focus=1"]],
        crop=(0.245, 0.2, 0.755, 0.8), depends_on=["gui/journal_entry_widgets/space_race_widget.gui",
                                                    "gui/journal_entry_widgets/sr_fleets_generated_rows.gui"],
        shows="a candidate: the Our Fleets window on the first fleet, its ships, condition and orders",
        note="sr_fleet_focus is the slot shown; the picture at its head is AI art"),
    "ws_12_construction_market": dict(
        out=WORKSHOP + "ws_12_construction_market.png", used_by=["workshop:12_construction_market"],
        status="entry", scene="late_2050", view=[["construction"]], crop=(0.0203, 0.0500, 0.2427, 0.4097),
        depends_on=["gui/*construction*.gui"],
        shows="the top of the construction panel: the Construction Market section"),
    # ---- placeholders: the guide marks the spot
    "space_elevator_site": dict(
        out=IMG + "space_elevator_site.png", used_by=[G + "02-timeline.md"], status="placeholder",
        placeholder="a Space Elevator Construction Site's building panel with the pace production methods and the "
                    "progress modifier visible"),
    "monuments_contested": dict(
        out=IMG + "monuments_contested.png", used_by=[G + "02-timeline.md"], status="placeholder",
        placeholder="the Monuments panel with Contested lit in the overview and a contested monument's row with its "
                    "three buttons"),
    "private_actors_tab": dict(
        out=IMG + "private_actors_tab.png", used_by=[G + "03-economy.md"], status="placeholder",
        placeholder="the Private Actors tab with a firm's details open"),
    "tax_code_light_rates": dict(
        out=IMG + "tax_code_light_rates.png", used_by=[G + "05-tax-code.md"], status="placeholder",
        placeholder="the Tax Code tab under the Light Tax Code, Tax Rates open"),
    "tax_code_enacted": dict(
        out=IMG + "tax_code_enacted.png", used_by=[G + "05-tax-code.md"], status="placeholder",
        placeholder="the Budget panel's Tax Code tab, overview and Enacted Code open"),
    "tax_code_bill_debate": dict(
        out=IMG + "tax_code_bill_debate.png", used_by=[G + "05-tax-code.md"], status="placeholder",
        placeholder="the Bill Under Debate section with the committed-clout bar and interest group cards"),
    "forceful_legislation_event": dict(
        out=IMG + "forceful_legislation_event.png", used_by=[G + "06-politics.md"], status="placeholder", art=True,
        placeholder="the Forceful Legislation event with all three bypass options available"),
    "heir_education": dict(
        out=IMG + "heir_education.png", used_by=[G + "06-politics.md"], status="placeholder",
        placeholder="the Heir Education journal entry with one trait focus, one ideology focus and one mentor focus "
                    "active"),
    "civil_rights_movement": dict(
        out=IMG + "civil_rights_movement.png", used_by=[G + "07-social-movements.md"], status="entry",
        scene="mid_1964", needs=[has_je("je_civil_rights")], view=[["close-panel"]], input=[("click", 0.91, 0.15)],
        crop=(0.0203, 0.05, 0.2427, 0.645),
        depends_on=["common/journal_entries/je_civil_rights.txt", "common/scripted_buttons/*civil*"],
        shows="the Civil Rights Movement journal entry with the Movement Support bar and the policy buttons in view",
        note="the USA in the 1964 copy, where the movement is marginal and its row is the first under Active "
             "Journal Entries in the outliner (the click); the page from its banner to its description"),
    "religious_revival_event": dict(
        out=IMG + "religious_revival_event.png", used_by=[G + "07-social-movements.md"], status="placeholder",
        art=True, placeholder="a religious revival event, such as The Moral Majority, with its three options"),
    "cultural_merge": dict(
        out=IMG + "cultural_merge.png", used_by=[G + "08-states.md"], status="placeholder",
        placeholder="a running Cultural Merge journal entry, its status line and Merge Progress bar in view"),
    "demographics_pyramid": dict(
        out=IMG + "demographics_pyramid.png", used_by=[G + "08-states.md"], status="entry", scene="mid_1964",
        needs=["te_demog_cohorts_run = yes"], view=te_window("demographics"), input=side_scroll(8),
        crop=(0.0203, 0.400, 0.2427, 0.850), depends_on=["gui/te_demographics_widgets.gui"],
        shows="the Demographics tab's Population Pyramid: men and women by age, the pale bars twenty years ahead",
        note="the section alone, eight notches down the side panel in the 1964 copy (its place moves with the "
             "Causes of Death list above it)"),
    "eu_formation": dict(
        out=IMG + "eu_formation.png", used_by=[G + "09-diplomacy.md"], status="placeholder",
        placeholder="the formation panel showing the European Union with its requirements tooltip"),
    "colonial_empire_overview": dict(
        out=IMG + "colonial_empire_overview.png", used_by=[G + "12-decolonization.md"], status="entry",
        scene="mid_1964", country=["TUR", "RUS"],
        needs=[has_je("je_colonial_empire"), "colonial_empire_disp_territories_eligible > 0"],
        view=te_window("colonial_empire"), input=COLONIAL_REFRESH, crop=(0.0203, 0.1426, 0.2427, 0.712),
        depends_on=["gui/journal_entry_widgets/colonial_empire*.gui"],
        shows="the Colonial Empire overview, the stability bar with its red stretch, and Colonial Holdings open: "
              "the territories with their Release buttons",
        note="Turkey in the 1964 copy, which holds no colonial subject, so the subject's Release and Dominion "
             "buttons the placeholder asked for are not in it; the crop ends under Colonial Holdings"),
    "territory_popup": dict(
        out=IMG + "territory_popup.png", used_by=[G + "12-decolonization.md"], status="placeholder",
        placeholder="the popup for one territory, with Grant it independence, the Round Table Conference grayed with "
                    "its reason, and Reconsider"),
    "military_base_level_5": dict(
        out=IMG + "military_base_level_5.png", used_by=[G + "13-military.md"], status="placeholder",
        placeholder="a Military Base building panel at level 5 with Hardened Positions, Territorial Defense and "
                    "Missile Defense Battery selected"),
    "gathering_storm": dict(
        out=IMG + "gathering_storm.png", used_by=[G + "13-military.md"], status="placeholder",
        placeholder="The Gathering Storm journal entry at high tension, with the Begin Rearmament and Provide "
                    "Lend-Lease buttons"),
    "nuclear_crisis": dict(
        out=IMG + "nuclear_crisis.png", used_by=[G + "14-nuclear.md"], status="placeholder",
        placeholder="the Nuclear Crisis section during a Confrontation, with the pressure breakdown tooltip open"),
}

KEYS = {"out", "used_by", "status", "scene", "country", "needs", "setups", "view", "scroll", "input", "hover", "event",
        "crop", "trim", "max_kb", "depends_on", "shows", "placeholder", "art", "note"}
INPUTS = {"click": 2, "wheel": 3, "drag": 4, "advance": 1, "event": 2}


def _input_ok(step) -> bool:
    if not (isinstance(step, (list, tuple)) and step and step[0] in INPUTS and len(step) == INPUTS[step[0]] + 1):
        return False
    kind, args = step[0], list(step[1:])
    if kind == "event":
        return (isinstance(args[0], str) and re.fullmatch(r"[a-z0-9_]+\.\d+", args[0]) is not None
                and isinstance(args[1], int) and not isinstance(args[1], bool) and 0 <= args[1] <= 9)
    if kind == "advance":
        return isinstance(args[0], int) and not isinstance(args[0], bool) and 0 < args[0] <= 31
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in args):
        return False
    if kind == "wheel":
        return all(0 <= v <= 1 for v in args[:2]) and isinstance(args[2], int) and 0 < abs(args[2]) <= 40
    return all(0 <= v <= 1 for v in args)
NEED = re.compile(r"^(?P<expr>.+?)\s*(?P<op>>=|<=|==|!=|>|<)\s*(?P<num>-?\d+(?:\.\d+)?)$")
_TAG = re.compile(r"^[A-Z0-9_]{1,16}$")
_SETUP = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
DEFAULT_MAX_KB = 1000


def parse_need(text: str) -> tuple[str, str | None, float | None]:
    """(expression, operator, number) of a need; a bare trigger is (text, None, None)."""
    m = NEED.match(text.strip())
    if m and "{" not in m["expr"]:
        return m["expr"], m["op"], float(m["num"])
    return text.strip(), None, None


def shot_countries(shot: dict) -> list[str]:
    """The countries a shot may be taken as, in the order tried: its `country` (a tag or a list), else the scene's."""
    country = shot.get("country")
    if isinstance(country, (list, tuple)):
        return list(country)
    scene = SCENES.get(shot.get("scene"))
    return [country or (scene or {}).get("as_tag")]


def shot_country(shot: dict) -> str | None:
    """The first country a shot is tried as."""
    return shot_countries(shot)[0]


def shot_trim(shot: dict) -> int | None:
    """The empty run (pixels) at which a shot's picture is cut, or None for no trim."""
    trim = shot.get("trim", isinstance(shot.get("crop"), str) and shot.get("crop") in TRIMMED)
    if trim is True:
        return TRIM_GAP
    if isinstance(trim, int) and not isinstance(trim, bool) and trim > 0:
        return trim
    return None


def crop_box(shot: dict) -> tuple[float, float, float, float]:
    crop = shot["crop"]
    return tuple(REGIONS[crop]) if isinstance(crop, str) else tuple(crop)


def guide_placeholders() -> list[str]:
    """The `<!-- screenshot: ... -->` texts the chapters hold, the style and README examples left out."""
    found = []
    for path in sorted(glob.glob(os.path.join(REPO, G, "*.md"))):
        if os.path.basename(path) in ("STYLE.md",):
            continue
        with open(path, encoding="utf-8") as f:
            found += [m.strip() for m in re.findall(r"<!-- screenshot: (.*?) -->", f.read(), flags=re.S)]
    return found


def guide_images() -> list[str]:
    """The `images/...` files the chapters show, as repo paths."""
    found = set()
    for path in sorted(glob.glob(os.path.join(REPO, G, "*.md"))):
        with open(path, encoding="utf-8") as f:
            found |= {IMG + name for name in re.findall(r"\]\(images/([^)\s]+\.(?:png|jpg|jpeg))\)", f.read())}
    return sorted(found)


def validate() -> list[str]:
    """Every problem with the manifest, as text: an empty list means none."""
    from importlib import util
    problems: list[str] = []
    for name, scene in SCENES.items():
        if not scene.get("save") or not _TAG.match(scene.get("as_tag") or ""):
            problems.append("scene %s: needs a save and an as_tag" % name)
        if scene.get("playset") not in ("current", "mod_only"):
            problems.append("scene %s: playset is current or mod_only" % name)
    for name, box in REGIONS.items():
        if len(box) != 4 or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
            problems.append("region %s: not a box inside the window" % name)
    view_ok = util.find_spec("game_qa") is not None
    if view_ok:
        from game_qa import capture_gui
    outs: dict[str, str] = {}
    for sid, shot in SHOTS.items():
        where = "shot %s" % sid
        unknown = set(shot) - KEYS
        if unknown:
            problems.append("%s: unknown keys %s" % (where, sorted(unknown)))
        status = shot.get("status")
        if status not in STATUSES:
            problems.append("%s: status is one of %s" % (where, ", ".join(STATUSES)))
            continue
        out = shot.get("out", "")
        workshop = out.startswith(WORKSHOP)
        if workshop:
            if not out.endswith(".png") or status not in TAKEN + ("assisted",):
                problems.append("%s: a Workshop shot is a .png under %s, status pilot, entry or assisted"
                                % (where, WORKSHOP))
        elif not out.startswith(IMG) or not out.endswith((".png", ".jpg")):
            problems.append("%s: out is a .png or .jpg under %s" % (where, IMG))
        if out in outs:
            problems.append("%s: out %s is shot %s's too" % (where, out, outs[out]))
        outs[out] = sid
        exists = workshop or os.path.isfile(os.path.join(REPO, out))
        if status == "placeholder":
            if exists:
                problems.append("%s: %s exists, so it is no placeholder: give it a recipe and a status" % (where, out))
            if not shot.get("placeholder"):
                problems.append("%s: a placeholder quotes the guide's screenshot comment" % where)
        elif not exists:
            problems.append("%s: %s is not there" % (where, out))
        for chapter in shot.get("used_by") or []:
            if not chapter.startswith("workshop:") and not os.path.isfile(os.path.join(REPO, chapter)):
                problems.append("%s: used_by %s is not a file" % (where, chapter))
        if not shot.get("used_by"):
            problems.append("%s: used_by names the chapters that show it" % where)
        if status != "placeholder" and not shot.get("shows"):
            problems.append("%s: shows says what the picture shows" % where)
        if status != "placeholder" and not shot.get("depends_on"):
            problems.append("%s: depends_on lists the files that can make it stale" % where)
        if status in ("pilot", "entry", "assisted") and shot.get("scene") not in SCENES:
            problems.append("%s: scene is one of %s" % (where, ", ".join(SCENES)))
        country = shot.get("country")
        if country is not None and not (
                (isinstance(country, str) and _TAG.match(country))
                or (isinstance(country, (list, tuple)) and country
                    and all(isinstance(c, str) and _TAG.match(c) for c in country))):
            problems.append("%s: country is a tag or a non-empty list of tags" % where)
        for need in shot.get("needs") or []:
            if not isinstance(need, str) or not need.strip():
                problems.append("%s: a need is text" % where)
        for setup, body in (shot.get("setups") or {}).items():
            if not _SETUP.match(setup) or not isinstance(body, str) or not body.strip():
                problems.append("%s: setup %r is a lower-case name and an effect body" % (where, setup))
        event = shot.get("event")
        if event is not None and not (isinstance(event, str) and re.fullmatch(r"[a-z0-9_]+\.\d+", event)):
            problems.append("%s: event is an event id (namespace.N)" % where)
        if status in TAKEN:
            if not shot.get("view") and not event:
                problems.append("%s: a %s shot has a view" % (where, status))
            elif view_ok and shot.get("view"):
                try:
                    capture_gui.parse_steps(shot["view"])
                except capture_gui.CaptureGuiError as e:
                    problems.append("%s: view: %s" % (where, e.detail))
            crop = shot.get("crop")
            if isinstance(crop, str):
                if crop not in REGIONS:
                    problems.append("%s: crop %r is not a region" % (where, crop))
            elif not (isinstance(crop, (tuple, list)) and len(crop) == 4
                      and 0 <= crop[0] < crop[2] <= 1 and 0 <= crop[1] < crop[3] <= 1):
                problems.append("%s: crop is a region or a box inside the window" % where)
            hover = shot.get("hover")
            if hover is not None and not (len(hover) == 2 and all(0 <= v <= 1 for v in hover)):
                problems.append("%s: hover is (x, y), fractions of the window" % where)
            for step in shot.get("input") or []:
                if not _input_ok(step):
                    problems.append("%s: an input step is (\"click\", x, y), (\"wheel\", x, y, notches), "
                                    "(\"drag\", x1, y1, x2, y2), fractions of the window, (\"advance\", days) or "
                                    "(\"event\", id, option): %r" % (where, step))
            trim = shot.get("trim")
            if trim is not None and not (isinstance(trim, bool) or (isinstance(trim, int) and trim > 0)):
                problems.append("%s: trim is True, False or an empty run in pixels" % where)
            scroll = shot.get("scroll")
            if scroll is not None and not (
                    isinstance(scroll, (list, tuple)) and len(scroll) == 3 and all(0 <= v <= 1 for v in scroll[:2])
                    and isinstance(scroll[2], int) and not isinstance(scroll[2], bool) and 0 < abs(scroll[2]) <= 40):
                problems.append("%s: scroll is (x, y, notches): fractions of the window and 1 to 40 notches, "
                                "negative down" % where)
    for sid, shot in SHOTS.items():
        for chapter in shot.get("used_by") or []:
            if chapter.startswith("workshop:") and chapter[len("workshop:"):] not in _workshop_specs():
                problems.append("shot %s: used_by %s names no spec in workshop_screenshot_specs.py" % (sid, chapter))
    images = set(guide_images())
    listed = {shot["out"] for shot in SHOTS.values()}
    generated = {IMG + "pop_spending_by_wealth.png"}     # scripts/player_guide_figures.py draws it
    for image in sorted(images - listed - generated):
        problems.append("the guide shows %s, which no shot lists" % image)
    wanted = {" ".join(shot["placeholder"].split()) for shot in SHOTS.values() if shot.get("placeholder")}
    for text in guide_placeholders():
        if " ".join(text.split()) not in wanted:
            problems.append("the guide's placeholder %r has no shot" % text[:80])
    return problems


if __name__ == "__main__":
    import sys
    found = validate()
    for p in found:
        print(p)
    sys.exit(1 if found else 0)
