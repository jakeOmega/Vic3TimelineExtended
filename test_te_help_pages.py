"""The Help pages (spec docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md
§§ 5.2, 7.5; plan docs/superpowers/plans/2026-11-02-charts-help-national-info.md, PRs H1
and H2; the "?" everywhere, owner 2026-11-03).

Each system's "How X Works" section moved into a help body type,
te_<key>_help_body, which only its popup, te_<key>_help_popup, instances. The
popup derives from te_ui_help_popup (gui/te_widget_library.gui) and sits in the
te_popups root (gui/te_popups.gui), shown on te_popup = help_<key>.

A "?" opens it, and nothing else does: the "How X Works" links that H1 and H2
left in the composers are gone (owner, 2026-11-03). Every host that shows a
system has one: a te_help_button in each tab body's header (the vanilla panels'
tabs, the Timeline Extended window narrow and full screen, National Info for
the player's own country), in National Info's header for another country, and
te_help_row (a section-wide row with the "?" at its right) at the top of each
journal entry and of the state panel's Demographics subtab, which have no
header. Each "?" is hidden for an observer, for whom te_popups never opens.

A help body reads only GetPlayer, never JournalEntry, so a page opens from any
host, whether or not the player holds the entry. That holds for the loc it
shows too, in English and in the translation memories deploy ships.

Every tab of the Timeline Extended window has its page
(test_every_system_with_a_tab_has_a_page): a new system's is one row in PAGES.
"""
import collections
import glob
import json
import os
import re
import unittest

from gui_test_helpers import _children, _close, _read, _strip_comments, _type_body

REPO = os.path.dirname(os.path.abspath(__file__))
GUI_DIR = os.path.join(REPO, "gui")
LIBRARY = os.path.join(GUI_DIR, "te_widget_library.gui")
TAB_WIDGETS = os.path.join(GUI_DIR, "te_system_tab_widgets.gui")
POPUPS = os.path.join(GUI_DIR, "te_popups.gui")
LOC_DIR = os.path.join(REPO, "localization", "english")
# The translation memories: deploy ships their German and Spanish lines into the
# same popups (scripts/generators/gen_non_english_loc.py, i18n/README.md).
I18N_DIR = os.path.join(REPO, "i18n")

# Vanilla's gold question mark, shipped unused: a placeholder (style guide rule 10).
HELP_ICON = "gfx/interface/buttons/button_icons/unused/help.dds"

# One row a page.
#   key          the page: te_popup = help_<key>, te_<key>_help_body, te_<key>_help_popup
#   title        the popup's title key (the old section's header)
#   flags        the collapse flags the move to a page retired
#   tabs         the tab body types (te_system_tab_frame) whose headers carry the "?":
#                every mount of the system in a vanilla panel, the Timeline Extended
#                window and National Info's own country (the Space Race's milestones
#                are SpaceRaceHeaderTest's)
#   entries      the journal entries whose overview root (custom_widget_container_1)
#                starts with te_help_row
#   rows         the other headerless hosts, each a type whose first child is te_help_row
#   popup_title  the popup's title block, when it isn't `text = "<title>"` (Tax
#                Code's, which names the code in force; Global Warming's)
Page = collections.namedtuple("Page", "key title flags tabs entries rows popup_title",
                              defaults=((), (), None))

SR_ENTRIES = ("je_space_race_suborbital", "je_space_race_orbital", "je_space_race_moon_landing",
              "je_space_race_probe", "je_space_race_moon_base", "je_space_race_mars_landing",
              "je_space_race_interstellar_probe", "je_space_race_interstellar_results",
              "je_space_race_solar_colonization")

PAGES = [
    Page("banking", "banking_dash_how_header", ("banking_dash_how_open",), ("te_banking_tab_body",),
         ("je_banking_cycle",)),
    Page("grand_monuments", "gm_je_how_header", ("gm_how_open",), ("te_gm_tab_body",),
         ("je_grand_monuments",)),
    Page("colonial_empire", "je_colonial_empire_how_header", ("colonial_empire_how_open",), ("te_ce_tab_body",),
         ("je_colonial_empire",)),
    # PR H2
    Page("cultural_hegemony", "je_ch_how_header", ("ch_how_open",), ("te_ch_tab_body",),
         ("je_cultural_hegemony",)),
    Page("nuclear_weapons", "je_nuclear_how_header", ("nuclear_how_open",), ("te_nuclear_tab_body",),
         ("je_nuclear_program",)),
    Page("strategic_reserve", "je_strategic_reserve_how_header", ("st_res_how_open",), ("te_st_res_tab_body",),
         ("je_strategic_reserve",)),
    # no journal entry
    Page("seabed", "te_seabed_how_header", ("te_seabed_how_open",), ("te_seabed_tab_body",)),
    Page("covert_warfare", "je_iw_how_header", ("covert_how_open",), ("te_covert_tab_body",),
         ("je_covert_warfare",)),
    # no journal entry; the tab's frame was added for its header and "?"
    Page("nation", "te_nation_how_header", ("te_nation_how_open",), ("te_nation_tab_body",)),
    Page("budget_breakdown", "te_budget_chart_how", ("te_budget_chart_how_open",),
         ("te_budget_breakdown_tab_body",)),
    Page("united_nations", "je_un_how_header", ("un_how_open",), ("te_un_tab_body",),
         ("je_united_nations",)),
    # no journal entry: the frame, with its header, on the window's tab and the
    # Population panel's; the state subtab a row
    Page("demographics", "te_demog_sec_how", ("te_demog_how_open", "te_demog_st_how_open"),
         ("te_demog_window_body",), rows=("te_state_demog_content",)),
    # one page for both codes, titled for the code in force
    Page("tax_code", "te_tax_how_header", ("te_tax_how_open", "te_tax_light_how_open"), ("te_tax_tab_body",),
         ("je_tax_code",),
         popup_title="text = \"[SelectLocalization( GetScriptedGui('te_tax_show_light_sgui').IsShown( "
                     "GuiScope.SetRoot( GetPlayer.MakeScope ).End ), 'te_tax_lt_how_header', 'te_tax_how_header' )]\""),
    # the nine entries share it; in the window the "?" is in the milestones'
    # generated headers (SpaceRaceHeaderTest)
    Page("space_race", "je_space_race_widget_how_header", ("sr_panel_how_open", "sr_panel_how_colonies_open"), (),
         SR_ENTRIES),
    # titled for the Fossil Transition alone with the Global Warming rule off
    Page("global_warming", "gw_how_header", ("gw_how_open", "rt_how_open"), ("te_gw_tab_body",),
         ("je_global_warming",),
         popup_title="text = \"[SelectLocalization( GetScriptedGui('gw_rule_enabled_sgui').IsShown( GuiScope.SetRoot( GetPlayer.MakeScope ).End ), 'gw_how_header', 'rt_how_header' )]\""),
    # no journal entry: the window's tab and National Info; the station's
    # building panel links to the tab
    Page("power_grids", "te_grid_how_header", (), ("te_grid_tab_body",)),
]

# The vanilla panels' tabs that show a system, each the type it mounts: a tab body
# with its header's "?" or a row host (test_every_vanilla_panel_mount_has_the_button).
VANILLA_MOUNTS = {
    ("budget_panel.gui", "te_banking_tab_body"), ("budget_panel.gui", "te_tax_tab_body"),
    ("budget_panel.gui", "te_budget_breakdown_tab_body"), ("culture_panel.gui", "te_ch_tab_body"),
    ("panel_military.gui", "te_nuclear_tab_body"), ("panel_military.gui", "te_covert_tab_body"),
    ("market_panel.gui", "te_st_res_tab_body"), ("market_panel.gui", "te_gw_tab_body"),
    ("diplomatic_overview.gui", "te_un_tab_body"), ("pops_overview.gui", "te_demog_window_body"),
    ("states_panel.gui", "te_state_demog_content"),
}

NOT_OBSERVER = 'visible = "[Not( GetMetaPlayer.IsObserver )]"'
JE_DIR = os.path.join(REPO, "common", "journal_entries")

# H2's pages' topics, in order: every key each body shows (text = "<key>",
# a type it instances read in place: the UN's te_un_help_authority and
# te_un_help_standing), headings and notes together, as each section had
# them (H1's three are pinned in their layout tests). A second section's
# topics follow the first's: Tax Code's Light code before the full code, each
# under its gate; Solar Colonization's (howc) after the Space Race's; the
# Fossil Transition's (rt_how_*) after the climate's; the state's two notes
# (te_demog_how_sub_state) before Sources. Generated from the bodies of
# 2026-11-02, after a node-by-node check against the old sections.
TOPICS = {
    "cultural_hegemony": [
        "je_ch_how_sub_share", "je_ch_how_share", "je_ch_how_sub_bonus", "je_ch_how_bonus",
        "je_ch_how_sub_programmes", "je_ch_how_programmes",
        "je_ch_how_sub_pull", "je_ch_how_pull", "je_ch_how_sub_board", "je_ch_how_board",
        "je_ch_how_sub_models", "je_ch_widget_models_legend", "je_ch_how_models", "ch_model_order_tt",
        "je_ch_how_sub_benchmark", "je_ch_how_benchmark",
    ],
    "nuclear_weapons": [
        "je_nuclear_how_sub_programme", "je_nuclear_how_programme", "je_nuclear_how_sub_crisis",
        "nd_w_crisis_actions_legend", "je_nuclear_how_sub_strike", "je_nuclear_how_strike",
        "je_nuclear_how_sub_posture", "je_nuclear_how_posture", "je_nuclear_how_sub_home", "nd_w_home_legend",
        "je_nuclear_how_sub_reputation", "nd_w_reputation_legend", "je_nuclear_how_sub_taboo",
        "je_nuclear_how_taboo", "je_nuclear_how_sub_delivery", "je_nuclear_program_widget_odds_note",
        "je_nuclear_how_sub_powers", "je_nuclear_program_widget_powers_legend",
    ],
    "strategic_reserve": [
        "je_strategic_reserve_how_sub_hub", "je_strategic_reserve_how_hub",
        "je_strategic_reserve_how_sub_rates", "je_strategic_reserve_how_rates",
        "je_strategic_reserve_how_sub_status", "je_strategic_reserve_how_status",
        "je_strategic_reserve_how_sub_decay", "je_strategic_reserve_how_decay",
        "je_strategic_reserve_how_sub_policies", "je_strategic_reserve_how_policies",
        "je_strategic_reserve_how_sub_presets", "je_strategic_reserve_how_presets",
        "je_strategic_reserve_how_sub_income", "je_strategic_reserve_how_income",
        "je_strategic_reserve_how_sub_history", "je_strategic_reserve_how_history",
    ],
    "seabed": [
        "te_seabed_how_sub_pools", "te_seabed_how_pools", "te_seabed_how_sub_weight", "te_seabed_how_weight",
        "te_seabed_how_sub_licences", "te_seabed_how_licences", "te_seabed_how_distant",
        "te_seabed_how_sub_claims", "te_seabed_how_claims", "te_seabed_how_sub_leases", "te_seabed_how_leases",
        "te_seabed_how_sub_policy", "te_seabed_how_policy", "te_seabed_how_regime",
    ],
    "covert_warfare": [
        "je_iw_how_sub_ops", "je_iw_how_ops", "je_iw_how_sub_funding", "je_iw_how_funding",
        "je_iw_how_sub_detection", "je_iw_how_detection", "je_iw_how_sub_networks", "je_iw_net_header_tooltip",
        "je_iw_how_sub_tradecraft", "je_iw_how_tradecraft", "je_iw_how_sub_ci", "je_iw_how_ci",
        "je_iw_how_sub_watching", "je_iw_how_watching", "je_iw_how_sub_standing", "je_iw_how_standing",
    ],
    "nation": [
        "te_nation_how_sub_tab", "te_nation_how_tab", "te_nation_how_sub_rows", "te_nation_how_rows",
        "te_nation_how_sub_override", "te_nation_how_override", "te_nation_how_sub_jud", "te_nation_how_jud",
        "te_nation_how_sub_mandate", "te_nation_how_mandate", "te_nation_how_sub_wc", "te_nation_how_wc",
        "te_nation_how_sub_construction", "te_nation_how_construction", "te_nation_how_sub_tech",
        "te_nation_how_tech", "te_nation_how_sub_lists", "te_nation_how_lists",
    ],
    "budget_breakdown": [
        "te_budget_chart_how_sub_admin", "te_budget_chart_how_admin", "te_budget_chart_how_sub_civil",
        "te_budget_chart_how_civil", "te_budget_chart_how_sub_military", "te_budget_chart_how_military",
        "te_budget_chart_how_sub_journal", "te_budget_chart_how_journal", "te_budget_chart_how_sub_charts",
        "te_budget_chart_how_charts",
    ],
    "united_nations": [
        "je_un_how_sub_authority", "je_un_auth_help_1", "je_un_auth_help_2", "je_un_auth_help_3",
        "je_un_auth_help_4", "je_un_auth_help_5", "je_un_auth_help_6", "je_un_auth_help_7", "je_un_auth_help_8",
        "je_un_auth_log_intro", "je_un_how_sub_standing", "je_un_standing_help_intro",
        "je_un_standing_help_sources", "je_un_standing_help_losses", "je_un_standing_help_limits",
        "je_un_how_sub_missions", "je_un_chamber_missions_intro", "je_un_chamber_missions_help",
        "je_un_how_sub_delegations", "je_un_chamber_deleg_intro", "je_un_chamber_reasons_intro",
        "je_un_how_sub_dues", "je_un_chamber_obligations_help", "je_un_how_sub_record",
        "je_un_chamber_exposure_help",
    ],
    "demographics": [
        "te_demog_how_sub_census", "te_demog_how_census", "te_demog_how_applied", "te_demog_how_sub_fertility",
        "te_demog_how_fertility", "te_demog_how_sub_mortality", "te_demog_how_mortality",
        "te_demog_how_sub_causes", "te_demog_how_causes", "te_demog_how_sub_work", "te_demog_how_work",
        "te_demog_how_pensions", "te_demog_how_men", "te_demog_how_sub_longevity", "te_demog_how_longevity",
        "te_demog_how_longevity_laws", "te_demog_how_minds", "te_demog_how_sub_family", "te_demog_how_family",
        "te_demog_how_sub_outline", "te_demog_how_outline", "te_demog_how_sub_migration",
        "te_demog_how_migration", "te_demog_how_sub_wealth", "te_demog_how_gini", "te_demog_how_wc",
        "te_demog_how_sub_places", "te_demog_how_places", "te_demog_how_sub_state", "te_demog_how_gini_state",
        "te_demog_how_modifiers", "te_demog_how_sub_sources", "te_demog_how_sources",
    ],
    "tax_code": [
        "te_tax_lt_how_sub_rates", "te_tax_lt_how_rates", "te_tax_lt_how_law", "te_tax_lt_how_sub_level",
        "te_tax_lt_how_level", "te_tax_lt_how_sub_groups", "te_tax_lt_how_groups", "te_tax_lt_how_relief",
        "te_tax_lt_how_sub_native", "te_tax_lt_how_native", "te_tax_lt_how_ai", "te_tax_how_sub_drafting",
        "te_tax_how_drafting", "te_tax_how_drafting_baseline", "te_tax_how_sub_passage", "te_tax_how_passage",
        "te_tax_how_passage_rule", "te_tax_how_passage_offers", "te_tax_how_passage_force",
        "te_tax_how_sub_commencement", "te_tax_how_commencement", "te_tax_how_commencement_sunset",
        "te_tax_how_commencement_held", "te_tax_how_sub_promises", "te_tax_how_promises",
        "te_tax_how_promises_kinds", "te_tax_how_promises_outcomes", "te_tax_how_sub_replaces",
        "te_tax_how_replaces", "te_tax_how_replaces_views", "te_tax_how_sub_customs", "te_tax_how_customs",
        "te_tax_how_customs_sync",
    ],
    "space_race": [
        "je_space_race_widget_how_sub_approach", "je_space_race_widget_how_approach",
        "je_space_race_widget_how_sub_funding", "je_space_race_widget_how_funding",
        "je_space_race_widget_how_sub_setbacks", "je_space_race_widget_how_setbacks",
        "je_space_race_widget_how_sub_first", "je_space_race_widget_how_first",
        "je_space_race_widget_how_sub_rivals", "je_space_race_widget_how_rivals",
        "je_space_race_widget_how_sub_programme", "je_space_race_widget_how_programme",
        "je_space_race_widget_how_sub_powers", "je_space_race_widget_how_powers",
        "je_space_race_widget_how_sub_orbit", "je_space_race_widget_how_orbit",
        "je_space_race_widget_howc_header", "je_space_race_widget_howc_sub_fleets",
        "je_space_race_widget_howc_fleets", "je_space_race_widget_howc_sub_windows",
        "je_space_race_widget_howc_windows", "je_space_race_widget_howc_sub_settlers",
        "je_space_race_widget_howc_settlers", "je_space_race_widget_howc_sub_modules",
        "je_space_race_widget_howc_modules", "je_space_race_widget_howc_sub_autonomy",
        "je_space_race_widget_howc_autonomy", "je_space_race_widget_howc_sub_space_command",
        "je_space_race_widget_howc_space_command", "je_space_race_widget_howc_sub_defences",
        "je_space_race_widget_howc_defences",
    ],
    "global_warming": [
        "gw_how_sub_warming", "gw_how_warming_1", "gw_how_warming_2", "gw_how_sub_penalty", "gw_how_penalty",
        "gw_how_sub_emissions", "gw_how_emissions_1", "gw_how_emissions_2", "gw_how_sub_policies",
        "gw_how_policies_1", "gw_how_policies_2", "gw_how_policies_3", "gw_how_sub_aerosols",
        "gw_how_aerosols_1", "gw_how_aerosols_2", "rt_how_header", "rt_how_laws_head", "rt_how_laws",
        "rt_how_programmes_head", "rt_how_programmes", "rt_how_emissions_head", "rt_how_emissions",
    ],
}


def _page_keys(types, body):
    """The loc keys a body shows, in order: each text = "<key>", with a mod
    type it instances (te_un_help_authority = {}) read in place."""
    keys = []
    for m in re.finditer(r'text = "(\w+)"|\b(\w+) = \{\}', body):
        if m.group(1):
            keys.append(m.group(1))
        elif m.group(2) in types:
            keys.extend(_page_keys(types, types[m.group(2)][1]))
    return keys


def _open(key):
    return f"[GetVariableSystem.Set('te_popup', 'help_{key}')]"


def _gui_paths():
    return sorted(glob.glob(os.path.join(GUI_DIR, "**", "*.gui"), recursive=True))


def _all_types():
    """Every mod GUI type: name -> (base, body), comments cut."""
    types = {}
    for path in _gui_paths():
        text = _strip_comments(_read(path))
        for m in re.finditer(r"^\s*type (\w+) = (\w+) \{", text, re.M):
            types[m.group(1)] = (m.group(2), text[m.end():_close(text, m.end() - 1)])
    return types


def _closure(types, start):
    """The types a type reaches: itself, its bases and every type it
    instances, all the way down (mod types only)."""
    reached, todo = set(), [start]
    while todo:
        name = todo.pop()
        if name in reached or name not in types:
            continue
        reached.add(name)
        base, body = types[name]
        todo.append(base)
        todo += re.findall(r"\b(\w+) = \{", body)
    return reached


def _loc():
    """The mod's English loc, key -> value (the last file in name order wins, as in game)."""
    keys = {}
    for path in sorted(glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True)):
        if path.endswith("te_unused_l_english.yml"):
            continue
        for line in _read(path).splitlines():
            m = re.match(r'\s+([\w.\-]+):\d*\s*"(.*)"', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def _translations():
    """Every translation memory's text, key -> [(file, field, text)]: each
    record's English and its translation (a stale record ships its old
    translation, binding and all)."""
    out = collections.defaultdict(list)
    for path in sorted(glob.glob(os.path.join(I18N_DIR, "*", "tm", "**", "*.json"), recursive=True)):
        with open(path, encoding="utf-8") as f:
            records = json.load(f)
        rel = os.path.relpath(path, REPO)
        for key, record in records.items():
            for field, value in record.items():
                if isinstance(value, str) and field != "base":
                    out[key].append((rel, field, value))
    return out


# What a loc text reaches: a splice ($key$), a key quoted as a loc function's
# argument (Localize('key'), SelectLocalization( …, 'a', 'b' ), AddLocalizationIf,
# AddTextIf) and an inline tooltip (#tooltippable;tooltip:key).
_LOC_REFS = re.compile(r"\$(\w+)\$|'(\w+)'|tooltip:(\w+)")


def _keys_reached(text, loc, translations=None):
    """The loc keys a GUI text names (a quoted key, a quoted argument), and
    every key those reach (_LOC_REFS), in English or in a translation,
    recursively."""
    found = {k for k in re.findall(r"""["'](\w+)["']""", text) if k in loc}
    todo = list(found)
    while todo:
        key = todo.pop()
        texts = [loc[key]] + [value for _, _, value in (translations or {}).get(key, ())]
        for value in texts:
            for groups in _LOC_REFS.findall(value):
                k = next(g for g in groups if g)
                if k in loc and k not in found:
                    found.add(k)
                    todo.append(k)
    return found


# A popup sits in te_popups, a root with no datacontext: the only objects a
# page can read are the global ones. Every data chain in a page's markup and
# loc must start at one of these (a chain's head: a name followed by a dot,
# not itself after a dot). Functions (Localize(…), GetScriptedGui(…),
# Concept(…)) take no context. Country, JournalEntry, State, ScriptContainer
# and the host panels are what a page must not read.
GLOBAL_HEADS = {"GetPlayer", "GetMetaPlayer", "GetVariableSystem", "GuiScope", "PdxGuiWidget"}


def _chain_heads(text):
    """The heads of the data chains in a text's [ … ] expressions, quoted
    arguments left out."""
    heads = set()
    for expr in re.findall(r"\[([^\[\]]*)\]", text):
        expr = re.sub(r"'[^']*'", "''", expr)
        heads.update(re.findall(r"(?<![\w.])([A-Za-z_]\w*)\.", expr))
    return heads


def _override(body, name):
    m = re.search(rf'blockoverride "{name}" \{{', body)
    return None if m is None else body[m.end():_close(body, m.end() - 1)]


def _opener(text, pos):
    """The innermost block opening around pos: `name` for `name = {`, or
    `blockoverride "x"` / `block "x"`."""
    depth = 0
    for i in range(pos - 1, -1, -1):
        c = text[i]
        if c == "}":
            depth += 1
        elif c == "{":
            if depth == 0:
                line = text[text.rfind("\n", 0, i) + 1:i].strip()
                return re.sub(r"\s*=$", "", line)
            depth -= 1
    return None


def _entry_overviews():
    """Each journal entry's overview root: the widget it mounts in
    custom_widget_container_1, entry -> root name."""
    out = {}
    for path in sorted(glob.glob(os.path.join(JE_DIR, "*.txt"))):
        text = _strip_comments(_read(path))
        for m in re.finditer(r"^(je_\w+) = \{", text, re.M):
            body = text[m.end():_close(text, m.end() - 1)]
            for w in re.finditer(r'\bwidget = \{([^{}]*)\}', body):
                name = re.search(r'name = "(\w+)"', w.group(1))
                if name and 'container = "custom_widget_container_1"' in w.group(1):
                    out[m.group(1)] = name.group(1)
    return out


def _gui_roots():
    """Every named top-level widget outside a types block: name -> body."""
    roots = {}
    for path in _gui_paths():
        text = _strip_comments(_read(path))
        for m in re.finditer(r'^\w+ = \{\n\tname = "(\w+)"', text, re.M):
            start = text.index("{", m.start())
            roots[m.group(1)] = text[start + 1:_close(text, start)]
    return roots


class ShellTest(unittest.TestCase):
    """The two shared types (plan Task H1.1)."""

    def test_the_shells(self):
        library = _strip_comments(_read(LIBRARY))
        self.assertRegex(library, r"(?m)^\ttype te_ui_help_popup = te_ui_popup \{")
        popup = _children(_type_body(library, "te_ui_help_popup"))
        self.assertEqual([(kind, name) for kind, name, _ in popup], [("blockoverride", "popup_size")])
        self.assertEqual(popup[0][2].strip(), "size = { 640 820 }")

        widgets = _strip_comments(_read(TAB_WIDGETS))
        self.assertRegex(widgets, r"(?m)^\ttype te_help_button = button_icon_round \{")
        button = _children(_type_body(widgets, "te_help_button"))
        props = {name: value for kind, name, value in button if kind == "property"}
        self.assertEqual(props, {"parentanchor": "right|vcenter", "position": "{ -10 0 }",
                                 "tooltip": '"te_help_button_tt"'})
        overrides = {name: inner.strip() for kind, name, inner in button if kind == "blockoverride"}
        self.assertEqual(overrides, {"size": "size = { 29 29 }", "icon": f'texture = "{HELP_ICON}"'})
        # an instance adds its own onclick, and nothing gates the type
        self.assertNotIn("onclick", _type_body(widgets, "te_help_button"))
        self.assertNotIn("visible", _type_body(widgets, "te_help_button"))

    def test_the_row(self):
        """te_help_row, the "?" where there is no header: a section-wide row,
        hidden for an observer (on the row, so it collapses in its host), with
        the button at its right and the instance's onclick through one block."""
        widgets = _strip_comments(_read(TAB_WIDGETS))
        self.assertRegex(widgets, r"(?m)^\ttype te_help_row = widget \{")
        row = _children(_type_body(widgets, "te_help_row"))
        props = {name: value for kind, name, value in row if kind == "property"}
        self.assertEqual(props, {"visible": '"[Not( GetMetaPlayer.IsObserver )]"', "parentanchor": "hcenter",
                                 "size": "{ 520 29 }"})
        others = [(kind, name) for kind, name, _ in row if kind != "property"]
        self.assertEqual(others, [("widget", "te_help_button")])
        button = [inner for kind, name, inner in row if name == "te_help_button"][0]
        self.assertEqual(_children(button), [("block", "help_onclick", "")])

    def test_the_loc(self):
        loc = _loc()
        self.assertIn("te_help_button_tt", loc)
        # the links' hover went with them
        self.assertNotIn("te_help_link_tt", loc)


class PageTest(unittest.TestCase):
    """Each page: its popup, its body, the link and the "?" (plan Task H1.2)."""

    @classmethod
    def setUpClass(cls):
        cls.types = _all_types()
        cls.gui = "\n".join(_strip_comments(_read(p)) for p in _gui_paths())
        cls.loc = _loc()
        cls.translations = _translations()

    def test_each_page_has_its_popup(self):
        for page in PAGES:
            with self.subTest(page=page.key):
                base, body = self.types[f"te_{page.key}_help_popup"]
                self.assertEqual(base, "te_ui_help_popup")
                items = _children(body)
                self.assertEqual(sorted(name for _, name, _ in items), ["popup_list", "popup_title", "popup_visible"])
                self.assertEqual(_override(body, "popup_visible").strip(),
                                 f"visible = \"[GetVariableSystem.HasValue('te_popup', 'help_{page.key}')]\"")
                self.assertEqual(_override(body, "popup_title").strip(), page.popup_title or f'text = "{page.title}"')
                self.assertEqual(_override(body, "popup_list").strip(), f"te_{page.key}_help_body = {{}}")

    def test_every_page_is_in_the_root(self):
        root = _strip_comments(_read(POPUPS))
        for page in PAGES:
            with self.subTest(page=page.key):
                self.assertEqual(len(re.findall(rf"^\tte_{page.key}_help_popup = \{{\}}$", root, re.M)), 1)

    def test_the_body_is_only_in_its_popup(self):
        for page in PAGES:
            with self.subTest(page=page.key):
                base, body = self.types[f"te_{page.key}_help_body"]
                self.assertEqual(base, "flowcontainer")
                own = {name: value for kind, name, value in _children(body) if kind == "property"}
                self.assertEqual({k: own.get(k) for k in ("direction", "ignoreinvisible", "spacing")},
                                 {"direction": "vertical", "ignoreinvisible": "yes", "spacing": "4"})
                self.assertNotIn("visible", own)
                self.assertEqual(len(re.findall(rf"\bte_{page.key}_help_body = \{{", self.gui)), 1)

    def test_every_system_with_a_tab_has_a_page(self):
        """Every tab of the Timeline Extended window has its Help page, and
        no page is for a system without one (gen_te_systems_window.TABS)."""
        from scripts.generators import gen_te_systems_window as gen
        self.assertEqual(sorted(page.key for page in PAGES), sorted(tab.key for tab in gen.TABS))
        self.assertEqual(len(PAGES), len({page.key for page in PAGES}))

    def test_every_page_opens(self):
        """Something opens each page (its link at least), and nothing opens a
        page that isn't there."""
        opened = set(re.findall(r"GetVariableSystem\.Set\('te_popup', 'help_(\w+)'\)", self.gui))
        self.assertEqual(opened, {page.key for page in PAGES})

    def test_no_link_is_left(self):
        """A "?" is the only thing that opens a page (owner, 2026-11-03): every
        GetVariableSystem.Set('te_popup', 'help_<key>') is a te_help_button's
        onclick, or te_help_row's help_onclick, and nothing is left of the "How
        X Works" links (their hover, a te_*_sec_how type)."""
        for path in _gui_paths():
            text = _strip_comments(_read(path))
            rel = os.path.relpath(path, REPO)
            self.assertNotIn("te_help_link_tt", text, rel)
            self.assertNotRegex(text, r"\btype te_\w+_sec_how(?:_\w+)? =", rel)
            for m in re.finditer(r"GetVariableSystem\.Set\('te_popup', 'help_\w+'\)", text):
                with self.subTest(file=rel, at=text.count("\n", 0, m.start()) + 1):
                    opener = _opener(text, m.start())
                    if opener == "te_help_button":
                        continue
                    self.assertEqual(opener, 'blockoverride "help_onclick"', "only a \"?\" opens a page")
                    outer = _opener(text, text.rfind('blockoverride "help_onclick"', 0, m.start()))
                    self.assertEqual(outer, "te_help_row")

    def test_every_button_is_hidden_for_an_observer(self):
        """te_popups is down for an observer, so a "?" would do nothing: each
        te_help_button instance carries the gate, but te_help_row's, whose row
        carries it (ShellTest.test_the_row)."""
        widgets = _strip_comments(_read(TAB_WIDGETS))
        row = _type_body(widgets, "te_help_row")
        for path in _gui_paths():
            text = _strip_comments(_read(path))
            rel = os.path.relpath(path, REPO)
            for m in re.finditer(r"\bte_help_button = \{", text):
                body = text[m.end():_close(text, m.end() - 1)]
                if path == TAB_WIDGETS and body in row:
                    continue
                with self.subTest(file=rel, at=text.count("\n", 0, m.start()) + 1):
                    props = [(name, value) for kind, name, value in _children(body) if kind == "property"]
                    self.assertEqual(props[0], ("visible", NOT_OBSERVER.split(" = ", 1)[1]))
                    self.assertEqual([name for name, _ in props], ["visible", "onclick"])

    def test_no_flag_is_left(self):
        raw = "\n".join(_read(p) for p in _gui_paths())
        for page in PAGES:
            for flag in page.flags:
                with self.subTest(flag=flag):
                    self.assertNotIn(f"'{flag}'", raw)
                    self.assertNotIn(flag, raw)

    def test_the_body_reads_the_player(self):
        """No JournalEntry read in what the popup reaches, nor in the loc it
        names, and no read of any context the popups root lacks (Country,
        State, a host panel): a page opens from any host, the entry held or
        not."""
        for page in PAGES:
            with self.subTest(page=page.key):
                reached = _closure(self.types, f"te_{page.key}_help_popup")
                self.assertIn(f"te_{page.key}_help_body", reached)
                self.assertIn("te_ui_popup", reached)
                text = "\n".join(self.types[name][1] for name in sorted(reached))
                self.assertNotRegex(text, r"\bJournalEntry\b|GetPlayerJournalEntry")
                self.assertLessEqual(_chain_heads(text), GLOBAL_HEADS, "the markup reads a context a popup lacks")
                keys = _keys_reached(text, self.loc, self.translations)
                self.assertIn(page.title, keys)
                for key in sorted(keys):
                    # in English, and in German and Spanish, which ship into the same popup
                    for where, value in [("English", self.loc[key])] + [
                            (f"{rel} ({field})", value) for rel, field, value in self.translations.get(key, ())]:
                        self.assertNotIn("JournalEntry", value, f"{key}, {where}")
                        self.assertLessEqual(_chain_heads(value), GLOBAL_HEADS,
                                             f"{key}, {where}: reads a context a popup lacks")

    def test_each_page_keeps_its_topics(self):
        """H2's pages show their keys in order, headings and notes together,
        each in the loc: deleting a note or a heading, or moving a note under
        another heading, fails."""
        self.assertLessEqual(set(TOPICS), {page.key for page in PAGES})
        for key, keys in TOPICS.items():
            with self.subTest(page=key):
                self.assertEqual(_page_keys(self.types, self.types[f"te_{key}_help_body"][1]), keys)
                for k in keys:
                    self.assertIn(k, self.loc)

    def test_each_header_has_its_button(self):
        """Every default_header in a tab body's tab_header holds one "?" that
        opens the page, as its last child, hidden for an observer."""
        for page in PAGES:
            for tab in page.tabs:
                with self.subTest(tab=tab):
                    base, body = self.types[tab]
                    self.assertEqual(base, "te_system_tab_frame")
                    headers = [inner for kind, name, inner in _children(_override(body, "tab_header"))
                               if kind == "widget" and name == "default_header"]
                    self.assertTrue(headers)
                    for header in headers:
                        items = _children(header)
                        self.assertEqual(items[-1][:2], ("widget", "te_help_button"))
                        self.assertEqual([name for _, name, _ in items].count("te_help_button"), 1)
                        self.assertEqual([line.strip() for line in items[-1][2].strip().splitlines()],
                                         [NOT_OBSERVER, f'onclick = "{_open(page.key)}"'])
                    # a frame without an entry draws no Open Journal Entry
                    if "tab_entry" not in body or "GetPlayerJournalEntry" not in _override(body, "tab_entry"):
                        self.assertEqual(_override(body, "tab_open_journal").strip(), "")

    def test_each_journal_entry_has_the_row(self):
        """Each entry's overview root (its custom_widget_container_1 widget)
        starts with te_help_row, outside te_je_country, so outside the
        composer the entry shares with its tab, whose header has its own "?"."""
        overview = _entry_overviews()
        roots = _gui_roots()
        listed = {entry for page in PAGES for entry in page.entries}
        # every entry with an overview root is a page's, but the Map Room: its widget is a row of map picks on a
        # contextless page the map buttons open, not a system's overview (journal_map_modes.md)
        self.assertEqual(set(overview) - {"je_te_map_room"}, listed)
        self.assertIn("je_te_map_room", overview, "the Map Room's exemption is still needed")
        for page in PAGES:
            for entry in page.entries:
                with self.subTest(entry=entry):
                    body = roots[overview[entry]]
                    items = [(kind, name, inner) for kind, name, inner in _children(body) if kind != "property"]
                    self.assertEqual(items[0][:2], ("widget", "te_help_row"))
                    self.assertEqual([name for _, name, _ in items].count("te_help_row"), 1)
                    self.assertIn(("widget", "te_je_country"), [item[:2] for item in items])
                    self.assertEqual(_override(items[0][2], "help_onclick").strip(), f'onclick = "{_open(page.key)}"')
                    props = {name: value for kind, name, value in _children(body) if kind == "property"}
                    # stacked, the row above the overview
                    self.assertEqual(props.get("direction"), "vertical")
                    self.assertEqual(props.get("ignoreinvisible"), "yes")
                    self.assertNotIn("te_help_row", "".join(inner for kind, name, inner in items if name == "te_je_country"))

    def test_each_row_host_has_the_row(self):
        """The Demographics host with no header, the state subtab: te_help_row
        first, outside its census gate, so "Census pending" has it too."""
        for page in PAGES:
            for host in page.rows:
                with self.subTest(host=host):
                    _, body = self.types[host]
                    items = [(kind, name, inner) for kind, name, inner in _children(body) if kind != "property"]
                    self.assertEqual(items[0][:2], ("widget", "te_help_row"))
                    self.assertEqual(_override(items[0][2], "help_onclick").strip(), f'onclick = "{_open(page.key)}"')
                    props = {name: value for kind, name, value in _children(body) if kind == "property"}
                    self.assertEqual(props.get("ignoreinvisible"), "yes")
        # and nowhere else: every row is an entry's or a row host's
        self.assertEqual(len(re.findall(r"\bte_help_row = \{", self.gui)),
                         sum(len(page.entries) + len(page.rows) for page in PAGES))

    def test_every_window_tab_has_the_button(self):
        """Every tab of the Timeline Extended window mounts a body whose header
        has the "?" (narrow, full screen in the body's layout block, and National
        Info for the player's own country), but the Space Race's, whose
        milestones' generated headers have it (SpaceRaceHeaderTest)."""
        from scripts.generators import gen_te_systems_window as gen
        pages = {page.key: page for page in PAGES}
        for tab in gen.TABS:
            with self.subTest(tab=tab.key):
                if tab.key == "space_race":
                    self.assertEqual(tab.body, "te_sr_tab_body")
                    continue
                self.assertIn(tab.body, pages[tab.key].tabs)
                # full screen keeps the body: its wide layout goes in the body's block
                self.assertIsNotNone(tab.layout)

    def test_national_info_headers_have_the_button(self):
        """National Info's mount for another country draws its own header over
        the wide composer: its last child is the "?", hidden for an observer."""
        from scripts.generators import gen_te_systems_window as gen
        generated = _strip_comments(_read(os.path.join(GUI_DIR, "te_national_info_generated.gui")))
        for tab in gen.ni_tabs():
            with self.subTest(tab=tab.key):
                m = re.search(rf'name = "te_ni_{tab.key}_other"', generated)
                self.assertTrue(m)
                at = generated.index("default_header = {", m.end())
                header = generated[at + len("default_header = {"):_close(generated, at + len("default_header = {") - 1)]
                items = _children(header)
                self.assertEqual(items[-1][:2], ("widget", "te_help_button"))
                self.assertEqual([line.strip() for line in items[-1][2].strip().splitlines()],
                                 [NOT_OBSERVER, f'onclick = "{_open(tab.key)}"'])

    def test_every_vanilla_panel_mount_has_the_button(self):
        """Each vanilla panel's tab that shows a system mounts a tab body with
        its header's "?" or a row host, and no vanilla panel mounts a system's
        body or sections that VANILLA_MOUNTS doesn't list."""
        hosts = {t for page in PAGES for t in page.tabs + page.rows}
        found = set()
        for path in sorted(glob.glob(os.path.join(GUI_DIR, "*.gui"))):
            name = os.path.basename(path)
            if name.startswith("te_") or name.startswith("00_te_"):
                continue
            text = _strip_comments(_read(path))
            outer = []   # the mounts' spans: a composer in a mounted body's block is the body's
            for m in re.finditer(r"\b(te_\w+_(?:tab_body|window_body|tab_sections|demog_content))\s*=\s*\{", text):
                if any(a < m.start() < b for a, b in outer):
                    continue
                outer.append((m.start(), _close(text, m.end() - 1)))
                found.add((name, m.group(1)))
        self.assertEqual(found, VANILLA_MOUNTS)
        for name, mount in sorted(VANILLA_MOUNTS):
            with self.subTest(panel=name, mount=mount):
                self.assertIn(mount, hosts)


class SpaceRaceHeaderTest(unittest.TestCase):
    """The Space Race tab's body is no frame: its entries' frames, and the note
    in their place while none runs, are generated (gen_te_systems_window.py's
    _milestone and sr_milestones). Every header there ends on the "?",
    hidden for an observer, who reaches the frames through National Info and
    for whom te_popups never opens."""

    def test_every_milestone_header_has_the_button(self):
        from scripts.generators import gen_te_systems_window as gen
        _, body = _all_types()["te_sr_window_milestones"]
        headers = [m.end() - 1 for m in re.finditer(r"\bdefault_header = \{", body)]
        self.assertEqual(len(headers), len(gen.SR_MILESTONES) + 1)   # each entry's and the idle note's
        for at in headers:
            items = _children(body[at + 1:_close(body, at)])
            with self.subTest(header=re.search(r'text = "(\w+)"', body[at:_close(body, at)]).group(1)):
                self.assertEqual(items[-1][:2], ("widget", "te_help_button"))
                self.assertEqual([name for _, name, _ in items].count("te_help_button"), 1)
                button = [line.strip() for line in items[-1][2].strip().splitlines()]
                self.assertEqual(button, [f'visible = "[{gen.NOT_OBSERVER}]"', f'onclick = "{_open("space_race")}"'])


if __name__ == "__main__":
    unittest.main()
