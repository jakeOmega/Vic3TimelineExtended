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
    out             the picture's path in the repo
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
    hover           (x, y) to leave the cursor on before the shot, fractions of the window (a tooltip)
    crop            a REGIONS key, or (left, top, right, bottom) in fractions of the window
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
    "late_2043": dict(
        save="te_qa_copy_iua2043_20261125", as_tag="USA", playset="current", unresponsive_s=120,
        note="a copy of the owner's June 2043 game as the USA (made 2026-11-25 for the Fleets window session)"),
    "late_2032": dict(
        save="te_qa_copy_iua_20261124", as_tag="USA", playset="current", unresponsive_s=120,
        note="a copy of the owner's December 2032 game as the USA (the GUI evaluation night of 2026-11-24)"),
}

# Regions, in fractions of the window at WINDOW and UI_SCALE.
REGIONS = {
    # A vanilla side panel (default_block_window, 540 UI units wide), and so the Timeline Extended window as a side
    # panel: from under the top bar to the bottom of the screen, the sidebar left out.
    "side_panel": (0.0203, 0.0500, 0.2427, 1.0),
    # The Timeline Extended window full screen: its three columns, under the tab strip (python_tools.md, the GUI
    # evaluation night).
    "te_window_columns": (0.17, 0.11, 0.83, 1.0),
    # One column of it (te_ui_columns_three, shared by every tab), with its section header: measured on the Space
    # Race tab (run 20261126T040928Z, crop_59), not yet on another tab.
    "te_column_1": (0.182, 0.205, 0.390, 1.0),
    "te_column_2": (0.398, 0.205, 0.602, 1.0),
    "te_column_3": (0.613, 0.205, 0.820, 1.0),
    "full": (0.0, 0.0, 1.0, 1.0),
}

CAPTURE_KEY = "te_qa_capture"   # game_qa.capture_gui.CAPTURE_KEY: debug mode's counters hide while it is set
TE_WINDOW_KEYS = ("com_open_window", "te_systems_window_tab", "te_systems_window_wide")


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


G = "docs/player_guide/"
IMG = G + "images/"
LOC = "localization/english/"

SHOTS = {
    # ---- the pilot: a view recipe each, run live
    "banking_tab": dict(
        out=IMG + "banking_tab.png", used_by=[G + "04-banking.md"], status="pilot", scene="late_2043",
        needs=[has_je("je_banking_cycle")],
        view=side_panel("budget", "te_banking"), crop="side_panel",
        depends_on=["gui/budget_panel.gui", "gui/journal_entry_widgets/banking_*.gui", "common/scripted_guis/*banking*", LOC + "*banking*"],
        shows="the Banking tab of the Budget panel: the four bars, the overview's icons, Active Policies and the start "
              "of Monetary Policy"),
    "nuclear_tab_armed": dict(
        out=IMG + "nuclear_tab_armed.png", used_by=[G + "14-nuclear.md"], status="pilot", scene="late_2043",
        needs=["nd_stockpile > 0"],
        view=side_panel("military", "te_nuclear"), crop="side_panel",
        depends_on=["gui/panel_military.gui", "gui/journal_entry_widgets/nuclear_*.gui",
                    "common/scripted_guis/*nuclear*", LOC + "*nuclear*"],
        shows="the Nuclear tab of the Military panel for a country holding warheads: the overview, The Program with "
              "its progress bar, Nuclear Posture, and the start of Forces"),
    "global_warming_tab": dict(
        out=IMG + "global_warming_tab.png", used_by=[G + "15-climate.md"], status="pilot", scene="late_2043",
        needs=["temperature_anomaly_display > 0.5"],
        view=market_tab("te_global_warming"), crop="side_panel",
        depends_on=["gui/market_panel.gui", "gui/journal_entry_widgets/global_warming_widget.gui",
                    "common/scripted_guis/*warming*", LOC + "*warming*"],
        shows="the Climate tab of the Market panel with a tier in force: the overview (tier, Market Leader, Penalty, "
              "the Temperature bar and its threshold line, the emissions table and the two pies) and the start of "
              "Mitigation Policies"),
    "hegemony_tab": dict(
        out=IMG + "hegemony_tab.png", used_by=[G + "11-influence.md"], status="pilot", scene="late_2043",
        needs=[has_je("je_cultural_hegemony")],
        view=side_panel("society", "te_ch"), crop="side_panel",
        depends_on=["gui/culture_panel.gui", "gui/journal_entry_widgets/cultural_hegemony_widget.gui",
                    "common/scripted_guis/*hegemony*", LOC + "*hegemony*"],
        shows="the Hegemony tab of the Society panel: the overview, Top Cultural Powers with each one's change since "
              "the last recount, Cultural Programs, and where our pull comes from"),
    "un_tab_overview": dict(
        out=IMG + "un_tab_overview.png", used_by=[G + "10-united-nations.md"], status="pilot", scene="late_2043",
        needs=[has_je("je_united_nations")],
        view=side_panel("diplomatic_overview", "te_un"), crop="side_panel",
        depends_on=["gui/diplomatic_overview.gui", "gui/journal_entry_widgets/un_*.gui",
                    "common/scripted_guis/*un_*", LOC + "*united_nations*"],
        shows="the UN tab of the Diplomacy panel: the overview (membership, tier, standing, the authority bar, the "
              "countries, GDP and population pies, the Security Council, the agencies and the headquarters) and "
              "Status"),
    "grand_monuments_tab": dict(
        out=IMG + "grand_monuments_tab.png", used_by=[G + "02-timeline.md"], status="pilot", scene="late_2043",
        needs=["gm_live_count_upheld > 0"],
        view=te_window("grand_monuments"), crop="side_panel",
        depends_on=["gui/te_systems_window*.gui", "gui/journal_entry_widgets/grand_monuments_widget.gui",
                    "common/scripted_guis/*monument*", LOC + "*monument*"],
        shows="the Grand Monuments tab of the Timeline Extended window: the overview's four counts, National Effects "
              "with Interest Group Approval, and the start of Our Monuments"),
    # ---- entries: a view recipe, not yet run live
    "covert_tab": dict(
        out=IMG + "covert_tab.png", used_by=[G + "11-influence.md"], status="entry", scene="late_2043",
        needs=[has_je("je_covert_warfare")],
        view=side_panel("military", "te_covert"), crop="side_panel",
        depends_on=["gui/panel_military.gui", "gui/journal_entry_widgets/covert_operations_widget.gui",
                    "common/scripted_guis/*covert*", LOC + "*covert*"],
        shows="the Covert tab of the Military panel: the overview, the Operations section with operation rows, and "
              "the start of Funding"),
    "strategic_reserve_tab": dict(
        out=IMG + "strategic_reserve_tab.png", used_by=[G + "03-economy.md"], status="entry", scene="late_2043",
        needs=[has_je("je_strategic_reserve")],
        view=market_tab("te_strategic_reserve"), crop="side_panel",
        depends_on=["gui/market_panel.gui", "gui/journal_entry_widgets/strategic_reserve_widget.gui",
                    "common/scripted_guis/*strategic_reserve*", LOC + "*strategic_reserve*"],
        shows="the Strategic Reserve tab of the Market panel: the overview above the Reserve Inventory, the Fill by "
              "Month chart and the start of its Policy Settings",
        note="the old picture has the Ammunition row expanded: find its key before the first capture"),
    "solar_system_colonization_tab": dict(
        out=IMG + "solar_system_colonization_tab.png", used_by=[G + "16-space.md"], status="entry",
        scene="late_2043", needs=[has_je("je_space_race_solar_colonization")],
        view=te_window("space_race"), crop="side_panel",
        depends_on=["gui/te_systems_window*.gui", "gui/journal_entry_widgets/space_race_widget.gui",
                    "gui/journal_entry_widgets/sr_*.gui", "common/scripted_guis/*space*", LOC + "*space_race*"],
        shows="the Space Race tab of the Timeline Extended window on Solar System Colonization: the overview and "
              "Program row, Mission Control with the approach buttons and the funding stepper, and Rivals"),
    "banking_rate": dict(
        out=IMG + "banking_rate.png", used_by=[G + "04-banking.md"], status="entry", scene="late_2043",
        needs=[has_je("je_banking_cycle")],
        view=te_window("banking", wide=True), crop="te_column_2",
        depends_on=["gui/journal_entry_widgets/banking_*.gui", "common/scripted_guis/*banking*", LOC + "*banking*"],
        shows="the Monetary Policy block of the banking dashboard: the rates and the Rate Target stepper, the "
              "exchange rate, what borrowing costs, prices, and the central bank's stance, delegation and mandate",
        note="in the side panel the block is below the fixed overview (taken live 2026-11-26: the top of the tab); "
             "the full-screen window puts it alone in column 2 (banking_layout_widget.gui)"),
    "un_authority_moving": dict(
        out=IMG + "un_authority_moving.png", used_by=[G + "10-united-nations.md"], status="entry", scene="late_2043",
        needs=[has_je("je_united_nations")],
        view=te_window("united_nations", wide=True), crop="te_column_2",
        depends_on=["gui/journal_entry_widgets/un_*.gui", "common/scripted_guis/*un_*", LOC + "*united_nations*"],
        shows="the Why UN Authority Is Moving section: authority and its target, the pillars, the tier, the charter, "
              "the champions and underminers, Recent Entries collapsed",
        note="in the side panel the section is below the fixed overview and the Assembly; the full-screen window "
             "starts column 2 with it (te_un_wide_sections, un_layout_widget.gui)"),
    "un_general_assembly": dict(
        out=IMG + "un_general_assembly.png", used_by=[G + "10-united-nations.md"], status="assisted",
        scene="late_2043",
        needs=[has_je("je_united_nations"), "has_global_variable = un_active_resolution"],
        view=side_panel("diplomatic_overview", "te_un"), crop="side_panel",
        depends_on=["gui/journal_entry_widgets/un_chamber_widget.gui", "common/scripted_guis/*un_*",
                    LOC + "*united_nations*"],
        shows="the General Assembly with a resolution in session: what happens if it carries or falls, how the "
              "Assembly reads our position, the vote buttons and the start of Delegations",
        note="the need is un_chamber_vote_sgui's is_shown (read yes live 2026-11-26). The Assembly starts under "
             "the fixed overview in the side panel and in column 1 of the full-screen window alike, so the shot "
             "needs a `scroll` by the overview's height (the same in every save): notches not yet measured"),
    "UN_lobbying": dict(
        out=IMG + "UN_lobbying.png", used_by=[G + "10-united-nations.md"], status="assisted", scene="late_2043",
        needs=[has_je("je_united_nations"), "has_global_variable = un_active_resolution"],
        view=side_panel("diplomatic_overview", "te_un", keys={"un_chamber_delegations_open": "yes"}),
        crop="side_panel",
        depends_on=["gui/journal_entry_widgets/un_chamber_widget.gui", LOC + "*united_nations*"],
        shows="the chamber's Delegations section: each row's band and any campaign on it, with the campaign and "
              "pledge buttons",
        note="Delegations (opened by its key) sits inside the Assembly, below the fixed overview and the "
             "resolution's text, whose length varies: a `scroll` whose count depends on the save, and a "
             "campaign on a row, likely a setup"),
    "nuclear_taboo": dict(
        out=IMG + "nuclear_taboo.png", used_by=[G + "14-nuclear.md"], status="entry", scene="late_2043",
        country=["JAP", "KOR", "GER", "SWE", "ARG", "MEX", "BRZ", "SAF"],
        needs=["nd_stockpile == 0", "nuclear_program_display_state == 7"],
        view=side_panel("military", "te_nuclear"), crop="side_panel",
        depends_on=["gui/journal_entry_widgets/nuclear_*.gui", LOC + "*nuclear*"],
        shows="the Nuclear tab for a country with no warheads and a Renounced posture: Reputation, The Nuclear Taboo "
              "with its two charts, Delivery and Defense, and the start of Nuclear Powers",
        note="state 7 of nuclear_program_display_state is the overview's Renounced. In the 2043 copy (2026-11-26) "
             "no candidate had it: JAP and KOR read 8 (Disarmed), GER held warheads, the rest do not exist. Widen "
             "the list, or play a country into renouncing, before this picture can be retaken"),
    # ---- assisted: the view is not enough (a scroll, a hover, a click on a map object)
    "construction_market": dict(
        out=IMG + "construction_market.png", used_by=[G + "03-economy.md"], status="assisted", scene="late_2043",
        depends_on=["gui/*construction*.gui", LOC + "*construction*"],
        shows="the Construction Market section under Fixed Budget: what the government spends and buys, private "
              "investors' share, the market's balance",
        note="in the construction panel: OpenConstructionPanel takes no key form the view has yet"),
    "state_panel": dict(
        out=IMG + "state_panel.png", used_by=[G + "08-states.md"], status="assisted", scene="late_2043",
        depends_on=["gui/states_panel.gui", "gui/te_state_panel_widgets.gui", LOC + "*state*"],
        shows="a state panel with the tourism card above the status grid and the Homeland Dynamics, Arable Land and "
              "Migration Crowding tiles at the bottom",
        note="OpenStatePanel takes a State: needs an action that names one (the capital)"),
    "UN_mission": dict(
        out=IMG + "UN_mission.png", used_by=[G + "10-united-nations.md"], status="assisted", scene="late_2043",
        depends_on=["gui/te_state_panel_widgets.gui", LOC + "*united_nations*"],
        shows="the UN Mission tile on a state panel: an aid mission under way, its strength and progress",
        note="a state panel of a state with a mission: as state_panel, and a need on the mission"),
    "settlement_authority": dict(
        out=IMG + "settlement_authority.png", used_by=[G + "08-states.md"], status="assisted", scene="late_2043",
        depends_on=["gui/building*.gui", LOC + "*settlement*"],
        shows="a Settlement Authority's building panel with its three production method groups and the settlers "
              "tooltip",
        note="a building panel and a hover"),
    "tech_tree_production_era_6_7_8": dict(
        out=IMG + "tech_tree_production_era_6_7_8.jpg", used_by=[G + "02-timeline.md"], status="assisted",
        scene="late_2043", depends_on=["common/technology/technologies/*.txt", "gui/technology*.gui"],
        shows="part of the production tree in eras 6 to 8, the era numeral under each icon",
        note="panel:tech_tree:production opens it; eras 6 to 8 need a drag or a wheel"),
    "disband_company": dict(
        out=IMG + "disband_company.png", used_by=[G + "09-diplomacy.md"], status="assisted", scene="late_2043",
        depends_on=["common/treaty_articles/*", LOC + "*treat*"],
        shows="choosing the company for a Disband Company article: the conceding country's companies",
        note="the treaty draft window, and an article picked: clicks"),
    "principle_picker_tier_v": dict(
        out=IMG + "principle_picker_tier_v.png", used_by=[G + "09-diplomacy.md"], status="assisted",
        scene="late_2043", depends_on=["common/power_bloc_principles/*", "gui/power_bloc*.gui"],
        shows="the Change or Upgrade Companies V window: every principle group in tiers I to V",
        note="a power bloc leader's principle window: clicks"),
    "combined_arms_full_spectrum": dict(
        out=IMG + "combined_arms_full_spectrum.png", used_by=[G + "13-military.md"], status="assisted",
        scene="late_2043", depends_on=["common/character_traits/*", LOC + "*trait*"],
        shows="a general's traits with all six Combined Arms traits",
        note="a character panel (OpenCharacterPanel takes a Character): clicks, or a setup that grants the traits"),
    # ---- manual: no session reaches it
    "game_rules": dict(
        out=IMG + "game_rules.png", used_by=[G + "01-introduction.md"], status="manual",
        depends_on=["common/game_rules/*", LOC + "*game_rule*"],
        shows="the mod's rules on the Game Rules screen, with the Cultural Hegemony tooltip open",
        note="the lobby's Game Rules screen: a session starts on a save, so this one is taken by hand"),
    # ---- placeholders: the guide marks the spot
    "space_elevator_site": dict(
        out=IMG + "space_elevator_site.png", used_by=[G + "02-timeline.md"], status="placeholder",
        placeholder="a Space Elevator Construction Site's building panel with the pace production methods and the "
                    "progress modifier visible"),
    "monuments_contested": dict(
        out=IMG + "monuments_contested.png", used_by=[G + "02-timeline.md"], status="placeholder",
        placeholder="the Monuments panel with Contested lit in the overview and a contested monument's row with its "
                    "three buttons"),
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
        out=IMG + "civil_rights_movement.png", used_by=[G + "07-social-movements.md"], status="placeholder",
        placeholder="the Civil Rights Movement journal entry with the Movement Support bar and the policy buttons in "
                    "view"),
    "religious_revival_event": dict(
        out=IMG + "religious_revival_event.png", used_by=[G + "07-social-movements.md"], status="placeholder",
        art=True, placeholder="a religious revival event, such as The Moral Majority, with its three options"),
    "cultural_merge": dict(
        out=IMG + "cultural_merge.png", used_by=[G + "08-states.md"], status="placeholder",
        placeholder="a running Cultural Merge journal entry, its status line and Merge Progress bar in view"),
    "demographics_pyramid": dict(
        out=IMG + "demographics_pyramid.png", used_by=[G + "08-states.md"], status="placeholder",
        placeholder="the Demographics tab with the population pyramid and its twenty-year outline"),
    "eu_formation": dict(
        out=IMG + "eu_formation.png", used_by=[G + "09-diplomacy.md"], status="placeholder",
        placeholder="the formation panel showing the European Union with its requirements tooltip"),
    "colonial_empire_overview": dict(
        out=IMG + "colonial_empire_overview.png", used_by=[G + "12-decolonization.md"], status="placeholder",
        placeholder="the Colonial Empire overview with the stability bar showing a red stretch, and Colonial Holdings "
                    "open with its territories, their Release buttons and a colonial subject's Release and Dominion "
                    "buttons"),
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

KEYS = {"out", "used_by", "status", "scene", "country", "needs", "setups", "view", "scroll", "hover", "crop",
        "max_kb",
        "depends_on", "shows", "placeholder", "art", "note"}
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
        if not out.startswith(IMG) or not out.endswith((".png", ".jpg")):
            problems.append("%s: out is a .png or .jpg under %s" % (where, IMG))
        if out in outs:
            problems.append("%s: out %s is shot %s's too" % (where, out, outs[out]))
        outs[out] = sid
        exists = os.path.isfile(os.path.join(REPO, out))
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
        if status in TAKEN:
            if not shot.get("view"):
                problems.append("%s: a %s shot has a view" % (where, status))
            elif view_ok:
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
            scroll = shot.get("scroll")
            if scroll is not None and not (
                    isinstance(scroll, (list, tuple)) and len(scroll) == 3 and all(0 <= v <= 1 for v in scroll[:2])
                    and isinstance(scroll[2], int) and not isinstance(scroll[2], bool) and 0 < abs(scroll[2]) <= 40):
                problems.append("%s: scroll is (x, y, notches): fractions of the window and 1 to 40 notches, "
                                "negative down" % where)
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
