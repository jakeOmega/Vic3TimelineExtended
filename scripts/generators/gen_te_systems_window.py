"""Generate the Timeline Extended window's strip, selection templates and tab
mounts from one registry (spec docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md
§ 9.3).

    python3 scripts/generators/gen_te_systems_window.py           # write the file
    python3 scripts/generators/gen_te_systems_window.py --check   # exit 1 if stale

Writes gui/te_systems_window_generated.gui. Never edit that file: edit TABS,
SR_MILESTONES or the renderers here, and run this script.
test_te_systems_window.py reads TABS and fails while the committed file is
stale. A manual generator, kept out of POST_LOAD_REGENERATORS, so a reload
never rewrites the window. gui/te_systems_window.gui keeps the frame, the
launcher and the root, and instances what this writes:

    te_systems_window_strips_narrow  the fixed_top's strips: one vanilla
                                     tab_buttons per strip, then the developer
                                     tax-probes strip
    te_systems_window_tabs_narrow    the scroll area's column: the tax-probes
                                     panel, then each tab's mount, holding its
                                     body type. Every mount supplies the
                                     player's Country (datacontext GetPlayer),
                                     the Country its sections read (spec
                                     2026-11-02-charts-help-national-info
                                     § 6.3)
    te_sr_window_milestones          the Space Race body's entries: a note
                                     while none runs, then one
                                     te_system_tab_frame per milestone

WHICH TAB IS SHOWN. U = the tab is open (its `open_` gate: for a system tab,
te_window_<system>_tab_sgui, or a mirrored tab's host gate (te_<host>_<system>_
tab_sgui), its rule on and an entry running; the Space Race's stays open once
the country is in the race), R = the tab is on the strip (its `strip` gate,
te_window_<system>_tab_unlock_sgui or the host's unlock gate: its rule on),
S = the player last chose it (te_systems_window_tab), T = the developer tax
tab is chosen and armed. With V = "a system tab last chosen is open" (S and U
for one of the system tabs):

    Nation       not T and not V
    a system t   not T and S_t and U_t

so exactly one tab is shown: Nation unless an open system tab was the last
choice. A system tab's unselected half shows while it is on the strip and not
shown, Nation's while another tab is. And and Or take two arguments, so V is
a balanced binary tree of Or.

ADDING A TAB: a body type (te_<system>_tab_body, on te_system_tab_frame in
gui/te_system_tab_widgets.gui, unless it has no entry and no gate), one Tab
line below, its loc (label, tooltip, locked line), then run this script.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
GUI_OUT = ROOT / "gui" / "te_systems_window_generated.gui"
# vanilla's gui/block_windows.gui, byte for byte (test_te_fullscreen_frame.py
# holds it to the install): the full-screen frame is copied from it
VANILLA_FRAMES = ROOT / "test_fixtures" / "vanilla_gui" / "block_windows.gui"

STORED = "te_systems_window_tab"
BOM = b"\xef\xbb\xbf"   # exactly one, as every .gui carries
SLOTS = ["first", "second", "third", "fourth", "fifth"]


# --- expressions: the exact GUI text the templates and the strip use ---------

# The scope a gate roots on (spec 2026-11-02-charts-help-national-info § 6.3):
# the player, in this window and the vanilla panels' tabs, or the shown
# country, in National Info (PR F1). The registry's gates are written on
# PLAYER_ROOT; rooted() puts one on another root.
PLAYER_ROOT = "GetPlayer.MakeScope"
COUNTRY_ROOT = "Country.MakeScope"


def _root(root: str = PLAYER_ROOT) -> str:
    return f"GuiScope.SetRoot( {root} ).End"


def shown(sgui: str, root: str = PLAYER_ROOT) -> str:
    return f"GetScriptedGui('{sgui}').IsShown( {_root(root)} )"


def valid(sgui: str, root: str = PLAYER_ROOT) -> str:
    return f"GetScriptedGui('{sgui}').IsValid( {_root(root)} )"


def valid_tooltip(sgui: str, root: str = PLAYER_ROOT) -> str:
    return f"GetScriptedGui('{sgui}').IsValidTooltip( {_root(root)} )"


def rooted(expr: str | None, root: str = PLAYER_ROOT) -> str | None:
    """A registry gate (open_, strip, tooltip_expr: written on PLAYER_ROOT)
    on another root: every scripted GUI it asks, asked of that root."""
    return None if expr is None else expr.replace(_root(PLAYER_ROOT), _root(root))


def stored(key: str) -> str:
    return f"GetVariableSystem.HasValue('{STORED}', '{key}')"


def and_(a: str, b: str) -> str:
    return f"And( {a}, {b} )"


def or_(a: str, b: str) -> str:
    return f"Or( {a}, {b} )"


def not_(a: str) -> str:
    return f"Not( {a} )"


def or_all(terms: list[str]) -> str:
    """Or over every term, as a balanced binary tree: Or takes two."""
    assert terms
    if len(terms) == 1:
        return terms[0]
    mid = (len(terms) + 1) // 2
    return or_(or_all(terms[:mid]), or_all(terms[mid:]))


# --- the registry -------------------------------------------------------------

@dataclass(frozen=True)
class Tab:
    """One tab of the window.

    key           the stored value (te_systems_window_tab) and the names'
                  stem: te_systems_window_<key>_tab, _selected, _unselected
    row           its strip (1 = the first)
    label         the tab's name (loc key)
    tooltip       its tooltip while open (loc key)
    locked        the grayed tab's first line, before its checklist (loc key)
    met           the grayed tab's line when the checklist all passes
    open_         the expression for "open", or None for always
    strip         the expression for "on the strip", or None for always
    unlock        the scripted GUI whose IsValid and IsValidTooltip make the
                  grayed tab's checklist
    body          the type the tab's mount instances
    layout        the layout block the body declares, which a wide mount
                  overrides (None: the body is the layout)
    wide          the wide composer the full-screen mount places (every tab has
                  one; test_te_systems_window.py fails on a tab without)
    tooltip_expr  a tooltip expression replacing the three-branch one
    public        another country's panel may show it (National Info, spec
                  2026-11-02-charts-help-national-info § 6.4): its sections
                  read the shown Country and its controls are the player's own
                  (test_te_system_tab_bodies.py's BindingTest and GuardTest,
                  which run over every public tab). Each system's binding PR
                  sets it, on its own line below, and takes the system off
                  that test's UNBOUND.
    readout       (scripted GUI, type): what the tab shows without its entry
                  (Banking's #805 readout, the Colonial Empire's stance and
                  colonial powers), on that scripted GUI, in the body frame's
                  tab_before_gate. National Info's mount for another country
                  draws no frame, so it draws the readout itself, on the
                  scripted GUI rooted on the shown Country, above the wide
                  composer (ni_types; BindingTest and GuardTest walk it too).
    """
    key: str
    row: int
    label: str
    tooltip: str
    body: str
    locked: str | None = None
    met: str = "te_system_tab_met_tt"
    open_: str | None = None
    strip: str | None = None
    unlock: str | None = None
    layout: str | None = None
    wide: str | None = None
    tooltip_expr: str | None = None
    public: bool = False
    readout: tuple[str, str] | None = None


def _system(key: str, body: str, layout: str, row: int = 1, **kw) -> Tab:
    """A tab of the window's own systems: te_window_<key>_tab_sgui opens it and
    te_window_<key>_tab_unlock_sgui puts it on the strip and gives the
    checklist (common/scripted_guis/te_system_tab_sguis.txt)."""
    return Tab(key, row, label=f"te_window_tab_{key}", tooltip=f"te_window_tab_{key}_tt",
               locked=f"te_window_tab_{key}_locked_tt",
               open_=shown(f"te_window_{key}_tab_sgui"), strip=shown(f"te_window_{key}_tab_unlock_sgui"),
               unlock=f"te_window_{key}_tab_unlock_sgui", body=body, layout=layout, **kw)


def _mirror(key: str, row: int, tooltip: str, body: str, layout: str | None, tab_sgui: str, unlock: str,
            locked: str | None = None, open_: str | None = None, **kw) -> Tab:
    """A tab mirrored from a vanilla panel's (spec § 6): the host tab's own
    gates (common/scripted_guis/te_system_tab_sguis.txt), its tooltip where
    the text fits the window (§ 9.6), and the window's own name. The grayed
    line is the window's (te_window_tab_<key>_locked_tt) unless the host's
    names the tab as the window does."""
    return Tab(key, row, label=f"te_window_tab_{key}", tooltip=tooltip,
               locked=locked or f"te_window_tab_{key}_locked_tt",
               open_=open_ or shown(tab_sgui), strip=shown(unlock), unlock=unlock, body=body, layout=layout, **kw)


BANKING_OPEN = or_(shown("te_budget_banking_tab_sgui"), shown("te_budget_banking_readout_sgui"))
# What the Banking tab shows without its entry (#805): its monetary readings.
BANKING_READOUT = ("te_budget_banking_readout_sgui", "te_banking_mon_readout")

# The Colonial Empire tab opens with its entry or, once the country has
# researched Decolonization, without it: the stance on colonialism and the
# colonial powers, which outlive the entry (owner, 2026-11-03;
# te_window_colonial_empire_readout_sgui). Its tooltip has a line for each,
# then the greyed tab's checklist, the research.
CE_OPEN = or_(shown("te_window_colonial_empire_tab_sgui"), shown("te_window_colonial_empire_readout_sgui"))
CE_TOOLTIP = (f"SelectLocalization( {shown('te_window_colonial_empire_tab_sgui')}, 'te_window_tab_colonial_empire_tt', "
              f"SelectLocalization( {shown('te_window_colonial_empire_readout_sgui')}, "
              "'te_window_tab_colonial_empire_readout_tt', "
              f"SelectLocalization( {valid('te_window_colonial_empire_tab_unlock_sgui')}, 'te_system_tab_met_tt', "
              "Concatenate( Localize( 'te_window_tab_colonial_empire_locked_tt' ), "
              f"{valid_tooltip('te_window_colonial_empire_tab_unlock_sgui')} ) ) ) )")
CE_READOUT = ("te_window_colonial_empire_readout_sgui", "te_ce_readout")

TABS: list[Tab] = [
    # Nation: always open (no journal entry, no game rule), so never grayed and
    # never a checklist (style guide rule 9's exception). It is the fallback.
    # The public flag (another country's panel shows the tab) sits on a line of
    # its own for each system National Info is to show (spec § 6.4), so each
    # system's binding PR changes one line and parallel PRs merge cleanly.
    Tab("nation", 1, label="te_window_tab_nation", tooltip="te_window_tab_nation_tt",
        body="te_nation_tab_sections", wide="te_nation_wide_sections",
        public=False),
    _system("space_race", "te_sr_tab_body", "te_sr_tab_layout", wide="te_sr_wide_sections",
            public=False),
    _system("grand_monuments", "te_gm_tab_body", "te_gm_tab_layout", wide="te_gm_wide_sections",
            public=False),
    replace(_system("colonial_empire", "te_ce_tab_body", "te_ce_tab_layout", wide="te_ce_wide_sections",
                    readout=CE_READOUT),
            open_=CE_OPEN, tooltip_expr=CE_TOOLTIP,
            public=False),
    # No journal entry: open once the country has taken part in a seabed
    # sharing, so its own "met" line.
    _system("seabed", "te_seabed_tab_body", "te_seabed_tab_layout", met="te_window_tab_seabed_met_tt",
            wide="te_seabed_wide_sections",
            public=True),

    # The Budget and Market panels' tabs (strip 2). Banking opens with its
    # entry or, for a country with a monetary stance and no entry, its #805
    # readout, and keeps the Budget tab's two-branch tooltip, which has no
    # checklist. Budget Breakdown has no entry and no rule: always open.
    _mirror("banking", 2, "te_budget_tab_banking_tt", "te_banking_tab_body", "te_banking_tab_layout",
            "te_budget_banking_tab_sgui", "te_budget_banking_tab_unlock_sgui",
            locked="te_budget_tab_banking_locked_tt", open_=BANKING_OPEN, readout=BANKING_READOUT,
            tooltip_expr=f"SelectLocalization( {shown('te_budget_banking_tab_sgui')}, 'te_budget_tab_banking_tt', "
                         f"SelectLocalization( {shown('te_budget_banking_readout_sgui')}, "
                         "'te_budget_tab_banking_readout_tt', 'te_budget_tab_banking_locked_tt' ) )",
            wide="te_banking_wide_sections",
            public=False),
    _mirror("tax_code", 2, "te_tax_tab_tt", "te_tax_tab_body", "te_tax_tab_layout",
            "te_budget_tax_tab_sgui", "te_budget_tax_tab_unlock_sgui", locked="te_tax_tab_locked_tt",
            wide="te_tax_wide_sections",
            public=False),
    Tab("budget_breakdown", 2, label="te_window_tab_budget_breakdown", tooltip="te_budget_chart_tab_tt",
        body="te_budget_breakdown_panel", wide="te_budget_breakdown_wide_sections"),
    # The Market tabs' own tooltips speak of another market: the window's own.
    _mirror("strategic_reserve", 2, "te_window_tab_strategic_reserve_tt", "te_st_res_tab_body", "te_st_res_tab_layout",
            "te_market_strategic_reserve_tab_sgui", "te_market_strategic_reserve_tab_unlock_sgui",
            wide="te_st_res_wide_sections"),
    _mirror("global_warming", 2, "te_window_tab_global_warming_tt", "te_gw_tab_body", "te_gw_tab_layout",
            "te_market_global_warming_tab_sgui", "te_market_global_warming_tab_unlock_sgui",
            wide="te_gw_wide_sections"),

    # The Population, Society, Diplomacy and Military panels' tabs (strip 3).
    # Demographics opens with its first census, as on the Population panel;
    # full screen, it takes the Census Data window's three columns.
    _mirror("demographics", 3, "te_pops_tab_demog_tt", "te_demog_window_body", "te_demog_tab_layout",
            "te_pops_demog_tab_sgui", "te_pops_demog_tab_unlock_sgui", locked="te_pops_tab_demog_locked_tt",
            open_=and_(shown("te_pops_demog_tab_sgui"), valid("te_pops_demog_tab_unlock_sgui")),
            wide="te_demog_browser_sections",
            public=True),
    _mirror("cultural_hegemony", 3, "te_society_tab_ch_tt", "te_ch_tab_body", "te_ch_tab_layout",
            "te_society_ch_tab_sgui", "te_society_ch_tab_unlock_sgui", wide="te_ch_wide_sections",
            public=False),
    _mirror("united_nations", 3, "te_diplomacy_tab_un_tt", "te_un_tab_body", "te_un_tab_layout",
            "te_diplomacy_un_tab_sgui", "te_diplomacy_un_tab_unlock_sgui", wide="te_un_wide_sections"),
    _mirror("nuclear_weapons", 3, "te_military_tab_nuclear_tt", "te_nuclear_tab_body", "te_nuclear_tab_layout",
            "te_military_nuclear_tab_sgui", "te_military_nuclear_tab_unlock_sgui", wide="te_nuclear_wide_sections",
            public=False),
    _mirror("covert_warfare", 3, "te_military_tab_covert_tt", "te_covert_tab_body", "te_covert_tab_layout",
            "te_military_covert_tab_sgui", "te_military_covert_tab_unlock_sgui", wide="te_covert_wide_sections"),
]

# The Space Race's nine entries, in je_space_race.txt's order. Each has its
# overview and its live sections (te_sr_<m>_overview, te_sr_<m>_status), but
# the waiting entry, which has the transit overview only.
SR_MILESTONES = ["suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
                 "interstellar_probe", "interstellar_results", "solar_colonization"]
SR_TRANSIT = {"interstellar_results"}

TAX_PROBES = and_(stored("tax_probes"), shown("te_tp_tab_sgui"))


# --- templates ----------------------------------------------------------------

def selected(tab: Tab, root: str = PLAYER_ROOT) -> str:
    if tab.key == TABS[0].key:
        return and_(not_(TAX_PROBES), not_(_any_system_shown(root)))
    mine = stored(tab.key) if tab.open_ is None else and_(stored(tab.key), rooted(tab.open_, root))
    return and_(not_(TAX_PROBES), mine)


def unselected(tab: Tab, root: str = PLAYER_ROOT) -> str:
    if tab.key == TABS[0].key:
        return or_(TAX_PROBES, _any_system_shown(root))
    return (not_(selected(tab, root)) if tab.strip is None
            else and_(rooted(tab.strip, root), not_(selected(tab, root))))


def _any_system_shown(root: str = PLAYER_ROOT) -> str:
    return or_all([stored(t.key) if t.open_ is None else and_(stored(t.key), rooted(t.open_, root))
                   for t in TABS[1:]])


def _template(name: str, expr: str) -> list[str]:
    return [f"template {name} {{", f'\tvisible = "[{expr}]"', "}", ""]


def templates() -> list[str]:
    out = []
    for tab in TABS:
        out += _template(f"te_systems_window_{tab.key}_selected", selected(tab))
        out += _template(f"te_systems_window_{tab.key}_unselected", unselected(tab))
    out += _template("te_systems_window_tax_probes_selected", TAX_PROBES)
    return out


# --- the strip ----------------------------------------------------------------

def _tooltip_value(tab: Tab, root: str = PLAYER_ROOT) -> str:
    """The tab's tooltip as a data-function argument: a quoted key for an
    always-open tab, else the expression _tooltip writes."""
    if tab.tooltip_expr:
        return rooted(tab.tooltip_expr, root)
    if tab.open_ is None:
        return f"'{tab.tooltip}'"
    checklist = f"Concatenate( Localize( '{tab.locked}' ), {valid_tooltip(tab.unlock, root)} )"
    return (f"SelectLocalization( {rooted(tab.open_, root)}, '{tab.tooltip}', "
            f"SelectLocalization( {valid(tab.unlock, root)}, '{tab.met}', {checklist} ) )")


def _tooltip(tab: Tab, root: str = PLAYER_ROOT) -> str:
    if tab.open_ is None and not tab.tooltip_expr:
        return f'tooltip = "{tab.tooltip}"'
    return f'tooltip = "[{_tooltip_value(tab, root)}]"'


def _slot(slot: str, tab: Tab, root: str = PLAYER_ROOT, stored_key: str = STORED,
          prefix: str = "te_systems_window", tooltip: str | None = None) -> list[str]:
    """One tab_buttons slot: the window's (te_systems_window_tab, its
    templates, its tooltip), or with stored_key, prefix and tooltip given,
    National Info's."""
    def override(name, *lines):
        return [f'blockoverride "{slot}_{name}" {{'] + [f"\t{ln}" for ln in lines] + ["}"]
    click = [] if tab.open_ is None else [f'enabled = "[{rooted(tab.open_, root)}]"']
    click.append(f"onclick = \"[GetVariableSystem.Set('{stored_key}', '{tab.key}')]\"")
    return (override("button", f'text = "{tab.label}"')
            + override("button_tooltip", tooltip or _tooltip(tab, root))
            + override("button_click", *click)
            + override("button_visibility", f"using = {prefix}_{tab.key}_selected")
            + override("button_visibility_checked", f"using = {prefix}_{tab.key}_unselected")
            + override("button_selected", f'text = "{tab.label}"'))


# The wide frame's strips keep the narrow slot width: 540, the Census
# window's strip (pop_browser_panel.gui).
WIDE_STRIP = ["minimumsize = { 540 -1 }", "maximumsize = { 540 -1 }"]


def _strip(tabs: list[Tab], wide: bool = False, root: str = PLAYER_ROOT) -> list[str]:
    assert len(tabs) <= len(SLOTS), "vanilla's tab_buttons has five slots"
    out = ["tab_buttons = {"] + ([f"\t{ln}" for ln in WIDE_STRIP] + [""] if wide else [])
    for i, (slot, tab) in enumerate(zip(SLOTS, tabs)):
        if i:
            out.append("")
        out.append(f"\t### {tab.key}")
        out += [f"\t{ln}" for ln in _slot(slot, tab, root)]
    return out + ["}"]


def _tax_probes_strip(wide: bool = False) -> list[str]:
    """TEMPORARY: a strip of its own for the developer tax-probes tab, so
    arming the probes never shrinks the system tabs. Wide, centered in a row
    of its own, which carries the strip's gate."""
    gate = f'visible = "[{shown("te_tp_tab_sgui")}]"'
    strip = (["tab_buttons = {"]
             + ([f"\t{ln}" for ln in WIDE_STRIP] if wide else [f"\t{gate}"])
             + ['\tblockoverride "first_button" { text = "te_tp_tab" }',
                '\tblockoverride "first_button_selected" { text = "te_tp_tab" }',
                '\tblockoverride "first_button_tooltip" { tooltip = "te_tp_tab_tt" }',
                f"\tblockoverride \"first_button_click\" {{ onclick = \"[GetVariableSystem.Set('{STORED}', 'tax_probes')]\" }}",
                '\tblockoverride "first_button_visibility" { using = te_systems_window_tax_probes_selected }',
                f'\tblockoverride "first_button_visibility_checked" {{ visible = "[{not_(TAX_PROBES)}]" }}',
                "}"])
    head = ["# TEMPORARY: a strip of its own for the developer tax-probes tab, so arming",
            "# the probes never shrinks the system tabs."]
    if not wide:
        return head + strip
    return head + ["hbox = {", f"\t{gate}", "\tlayoutpolicy_horizontal = expanding", "\tlayoutpolicy_vertical = fixed", "",
                   "\texpand = {}"] + [f"\t{ln}" for ln in strip] + ["\texpand = {}", "}"]


def strips_narrow() -> list[str]:
    out = ["### The strips, in fixed_top: vanilla's five-slot strip (as the Military",
           "### and Diplomacy panels use it) per row of the registry. tab_buttons",
           "### derives from hbox, and a flowcontainer cannot own box layouts, so this",
           "### is a vbox.",
           "type te_systems_window_strips_narrow = vbox {",
           "\tlayoutpolicy_horizontal = expanding",
           "\tlayoutpolicy_vertical = fixed",
           "\tignoreinvisible = yes",
           ""]
    for row in sorted({t.row for t in TABS}):
        out += [f"\t{ln}" if ln else "" for ln in _strip([t for t in TABS if t.row == row])]
        out.append("")
    out += [f"\t{ln}" for ln in _tax_probes_strip()]
    return out + ["}"]


def strips_wide() -> list[str]:
    out = ["### The full-screen frame's strips: the narrow strips side by side in one",
           "### centered row, each at its narrow width, so one strip of up to fifteen",
           "### tabs at the narrow slot width; then the developer strip.",
           "type te_systems_window_strips_wide = vbox {",
           "\tlayoutpolicy_horizontal = expanding",
           "\tlayoutpolicy_vertical = fixed",
           "\tignoreinvisible = yes",
           "",
           "\thbox = {",
           "\t\tlayoutpolicy_horizontal = expanding",
           "\t\tlayoutpolicy_vertical = fixed",
           "",
           "\t\texpand = {}"]
    for row in sorted({t.row for t in TABS}):
        out += [f"\t\t{ln}" if ln else "" for ln in _strip([t for t in TABS if t.row == row], wide=True)]
    out += ["\t\texpand = {}", "\t}", ""]
    out += [f"\t{ln}" if ln else "" for ln in _tax_probes_strip(wide=True)]
    return out + ["}"]


# --- the mounts ---------------------------------------------------------------

def _content(tab: Tab, wide: bool = False) -> list[str]:
    """What a mount holds: the tab's body, or full screen its wide layout
    (in the body's layout block, so with its gate, its entry and its
    controls, or alone where the body declares none)."""
    if not wide or tab.wide is None:
        return [f"{tab.body} = {{}}"]
    if tab.layout is None:
        return [f"{tab.wide} = {{}}"]
    return [f"{tab.body} = {{", f'\tblockoverride "{tab.layout}" {{', f"\t\t{tab.wide} = {{}}", "\t}", "}"]


def _mount(tab: Tab, wide: bool = False) -> list[str]:
    content = [f"\t{ln}" for ln in _content(tab, wide)]
    return ["flowcontainer = {",
            f'\tname = "te_systems_window_{tab.key}_tab{"_wide" if wide else ""}"',
            '\tdatacontext = "[GetPlayer]"',
            f"\tusing = te_systems_window_{tab.key}_selected",
            "\tusing = default_fade_in_out",
            "\tparentanchor = hcenter",
            "\tdirection = vertical",
            "\tignoreinvisible = yes",
            "\tmargin_top = 10",
            "\tmargin_bottom = 15",
            ""] + content + ["}"]


def tabs_narrow() -> list[str]:
    out = ["### The scroll area's column: one fixed width (style guide rule 8), so",
           "### switching tabs never moves the content sideways. Each tab's content",
           "### is up only while its tab is shown (the *_selected templates), so a",
           "### closed tab's panels are never built.",
           "type te_systems_window_tabs_narrow = flowcontainer {",
           '\tname = "te_systems_window_content"',
           "\tusing = default_list_position",
           "\tdirection = vertical",
           "\tignoreinvisible = yes",
           "\tminimumsize = { 540 -1 }",
           "",
           "\tte_tp_panel = {",
           "\t\tusing = te_systems_window_tax_probes_selected",
           "\t}"]
    for tab in TABS:
        out.append("")
        out += [f"\t{ln}" if ln else "" for ln in _mount(tab)]
    return out + ["}"]


def tabs_wide() -> list[str]:
    out = ["### The full-screen frame's column: three 520 columns and their 30 px",
           "### gaps wide (spec § 4.3), centered, so the frame scrolls sideways",
           "### below that width. Each tab's mount as narrow, holding its wide",
           "### layout once the registry names one (its `wide`), else its body.",
           "type te_systems_window_tabs_wide = flowcontainer {",
           '\tname = "te_systems_window_content_wide"',
           "\tparentanchor = hcenter",
           "\tdirection = vertical",
           "\tignoreinvisible = yes",
           "\tminimumsize = { 1620 -1 }",
           "",
           "\tte_tp_panel = {",
           "\t\tusing = te_systems_window_tax_probes_selected",
           "\t}"]
    for tab in TABS:
        out.append("")
        out += [f"\t{ln}" if ln else "" for ln in _mount(tab, wide=True)]
    return out + ["}"]


# The Space Race's Help page (spec docs/superpowers/specs/2026-11-02-charts-help-
# national-info-design.md § 5.2): the "?" (te_help_button, gui/te_system_tab_widgets.gui)
# that every header of the tab's entries carries, its last child, as each other
# tab's header does in its body type. Its lines, at a header's child depth.
SR_HELP_BUTTON = ["te_help_button = {",
                  "\tonclick = \"[GetVariableSystem.Set('te_popup', 'help_space_race')]\"",
                  "}"]


def _milestone(m: str) -> list[str]:
    if m in SR_TRANSIT:
        content = ["te_sr_overview_transit = {}"]
    else:
        content = [f"te_sr_{m}_overview = {{}}", f"te_sr_{m}_status = {{", '\tblockoverride "sr_debris" {}', "}"]
    return ([f"### {m}",
             "te_system_tab_frame = {",
             f'\tvisible = "[{shown(f"te_window_space_race_{m}_sgui")}]"',
             '\tblockoverride "tab_header" {',
             "\t\tdefault_header = {",
             "\t\t\tusing = default_list_position",
             '\t\t\tblockoverride "text" {',
             f'\t\t\t\ttext = "je_space_race_{m}"',
             "\t\t\t}"]
            + [f"\t\t\t{ln}" for ln in SR_HELP_BUTTON]
            + ["\t\t}",
             "\t}",
             '\tblockoverride "tab_entry" {',
             f"\t\tdatacontext = \"[GetPlayerJournalEntry('je_space_race_{m}')]\"",
             "\t}",
             '\tblockoverride "tab_content" {']
            + [f"\t\t{ln}" for ln in content]
            + ["\t}",
               '\tblockoverride "tab_open_journal_tooltip" {',
               '\t\ttooltip = "te_window_space_race_open_journal_tt"',
               "\t}",
               "}"])


def sr_milestones() -> list[str]:
    out = ["### The Space Race body's entries (te_sr_tab_body, space_race_widget.gui):",
           "### GetPlayerJournalEntry takes one literal key, so each entry has its own",
           "### frame, in je_space_race.txt's order, shown only while the player holds",
           "### it (te_window_space_race_<m>_sgui, on the frame's root, so its header",
           "### goes with it), and a note in their place while none runs",
           "### (te_window_space_race_idle_sgui). Several can run at once. Each shows",
           "### the types its journal roots wrap, the debris row overridden out (Orbit",
           "### shows it once), then Open Journal Entry for that entry. Every header",
           "### here, the note's too, ends on the \"?\" that opens the Help page.",
           "type te_sr_window_milestones = flowcontainer {",
           "\tparentanchor = hcenter",
           "\tdirection = vertical",
           "\tignoreinvisible = yes",
           "\tspacing = 10",
           "",
           "\t### No milestone running: one note in the entries' place, so the tab",
           "\t### never ends on the reference alone.",
           "\tflowcontainer = {",
           '\t\tname = "te_systems_window_space_race_idle"',
           f'\t\tvisible = "[{shown("te_window_space_race_idle_sgui")}]"',
           "\t\tparentanchor = hcenter",
           "\t\tdirection = vertical",
           "\t\tignoreinvisible = yes",
           "\t\tspacing = 10",
           "\t\tminimumsize = { 520 -1 }",
           "",
           "\t\tdefault_header = {",
           "\t\t\tusing = default_list_position",
           '\t\t\tblockoverride "text" {',
           '\t\t\t\ttext = "te_window_space_race_idle_header"',
           "\t\t\t}"]
    out += [f"\t\t\t{ln}" for ln in SR_HELP_BUTTON]
    out += ["\t\t}",
            "\t\tte_sr_panel = {",
            "\t\t\tte_sr_text = {",
            '\t\t\t\ttext = "te_window_space_race_idle_note"',
            "\t\t\t}",
            "\t\t}",
            "\t}"]
    for m in SR_MILESTONES:
        out.append("")
        out += [f"\t{ln}" for ln in _milestone(m)]
    return out + ["}"]


# --- the full-screen frame ----------------------------------------------------

CLEAR_OPEN = "[GetVariableSystem.Clear('com_open_window')]"
FRAME_CHANGES = [
    ("type fullscreen_block_window = widget {", "type te_fullscreen_block_window = widget {"),
    ('onclick = "[InformationPanelBar.OpenPreviousPanel]"', f'onclick = "{CLEAR_OPEN}"'),
    ('onclick = "[InformationPanelBar.ClosePanel]"', f'onclick = "{CLEAR_OPEN}"'),
]


def fullscreen_frame() -> list[str]:
    """Vanilla's fullscreen_block_window under the mod's name, Back and Close
    clearing the window's open state: vanilla's call the information panel
    bar, which a scripted widget isn't in (spec § 4.1). Each change must match
    exactly once, so a patch that moves them fails here."""
    text = VANILLA_FRAMES.read_text(encoding="utf-8-sig")
    m = re.search(r"^\ttype fullscreen_block_window = widget \{$", text, re.M)
    if not m:
        raise ValueError(f"{VANILLA_FRAMES.name}: no fullscreen_block_window")
    depth, end = 0, None
    for i in range(m.end() - 1, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            end = i
            break
    frame = text[m.start():end + 1]
    for old, new in FRAME_CHANGES:
        if frame.count(old) != 1:
            raise ValueError(f"vanilla's fullscreen_block_window changed: {old!r} is there {frame.count(old)} times")
        frame = frame.replace(old, new)
    body = [ln[1:] if ln.startswith("\t") else ln for ln in frame.split("\n")]
    return ["### The full-screen frame: vanilla's fullscreen_block_window (copied from",
            "### test_fixtures/vanilla_gui/block_windows.gui), its type name, Back and Close",
            "### changed. It fills the screen from its origin, as vanilla's full-screen",
            "### panels do (ingame_hud.gui), its own top filler under the top bar."] + body


# --- National Info (spec 2026-11-02-charts-help-national-info §§ 6.2, 7.3) -------
#
# The Census Data window (gui/pop_browser_panel.gui, vanilla's, overridden),
# renamed National Info, shows the country it was opened for: vanilla's pops
# (Pops), then each public tab (Tab.public), for that country, whoever it is.
# This writes its strip, its selection templates and its mounts into a second
# file, NI_OUT; the window instances them in its ### MOD: National Info blocks.
# Driven by `public` alone: a system joins with its flag and a rerun.
#
# WHICH TAB IS SHOWN: the last one chosen (te_ni_tab, a client-side value)
# while it is open for the window's country, otherwise Pops, which always is.
# So switching countries never shows a tab that isn't running there. Every
# gate is the registry's, rooted on the window's Country (COUNTRY_ROOT).
#
# TWO MOUNTS A TAB. For the player's own country, the window's full-screen
# mount (the body with its layout override: its gate, its entry, its
# controls). For another, the tab's header (its name and its "?"), its
# readout if it has one, and its wide composer under the window's Country,
# with no journal entry and no frame (the frame's tab_country is GetPlayer).

NI_OUT = ROOT / "gui" / "te_national_info_generated.gui"
NI_STORED = "te_ni_tab"
NI_FALLBACK = "pops"
NI_PREFIX = "te_ni"
# The window's tabs in their order (spec § 6.2): Pops, then the systems, five
# a strip. A public tab not listed here fails _validate_ni.
NI_ORDER = ["pops", "demographics", "nation", "banking", "tax_code",
            "grand_monuments", "colonial_empire", "seabed", "cultural_hegemony", "space_race",
            "nuclear_weapons"]
NI_PER_STRIP = len(SLOTS)
# The Pops tab: vanilla's window, always open.
NI_POPS_LABEL = "te_pop_browser_tab_pops"
NI_POPS_TOOLTIP = "te_pop_browser_tab_pops_tt"
# Another country's tooltips (spec § 6.2): open, what it shows the world; grayed,
# one line (the player's checklist doesn't fit another country).
NI_OTHER_TT = "te_ni_tab_other_tt"
NI_NOT_RUNNING_TT = "te_ni_tab_not_running_tt"
LOCAL = "Country.IsLocalPlayer"


def ni_types(tab: Tab) -> set[str]:
    """The types National Info's mount for another country draws for the tab,
    beyond its header: the wide composer and the readout. BindingTest,
    GuardTest and te_rebind_country.py walk these."""
    return {tab.wide} | ({tab.readout[1]} if tab.readout else set())


def ni_tabs() -> list[Tab]:
    """The public tabs, in NI_ORDER."""
    by_key = {t.key: t for t in TABS if t.public}
    return [by_key[k] for k in NI_ORDER if k in by_key]


def ni_stored(key: str) -> str:
    return f"GetVariableSystem.HasValue('{NI_STORED}', '{key}')"


def ni_selected(tab: Tab) -> str:
    """The tab is shown: chosen last, and open for the window's country."""
    return ni_stored(tab.key) if tab.open_ is None else and_(ni_stored(tab.key), rooted(tab.open_, COUNTRY_ROOT))


def ni_unselected(tab: Tab) -> str:
    """On the strip for the window's country and not shown."""
    return (not_(ni_selected(tab)) if tab.strip is None
            else and_(rooted(tab.strip, COUNTRY_ROOT), not_(ni_selected(tab))))


def ni_any_shown() -> str | None:
    """A public tab is shown (so not Pops), or None while none is public."""
    tabs = ni_tabs()
    return or_all([ni_selected(t) for t in tabs]) if tabs else None


def ni_pops_selected() -> str:
    shown_ = ni_any_shown()
    return "yes" if shown_ is None else not_(shown_)


def ni_strip_shown() -> str | None:
    """The strip shows while a public tab could be on it: or_all of their
    strip gates, or always (None) once one has none (Nation)."""
    tabs = ni_tabs()
    if not tabs:
        return "no"
    if any(t.strip is None for t in tabs):
        return None
    return or_all([rooted(t.strip, COUNTRY_ROOT) for t in tabs])


def ni_tooltip(tab: Tab) -> str:
    """Open for another country, what it shows the world; grayed, not running
    there; for the player's own, the window's tooltip (its checklist too), on
    the window's Country. SelectLocalization nests in its third argument
    only, as the window's three-branch tooltips do."""
    player = _tooltip_value(tab, COUNTRY_ROOT)
    if tab.open_ is None:
        return f"tooltip = \"[SelectLocalization( {LOCAL}, {player}, '{NI_OTHER_TT}' )]\""
    other_open = and_(not_(LOCAL), rooted(tab.open_, COUNTRY_ROOT))
    return (f"tooltip = \"[SelectLocalization( {other_open}, '{NI_OTHER_TT}', "
            f"SelectLocalization( {not_(LOCAL)}, '{NI_NOT_RUNNING_TT}', {player} ) )]\"")


def _ni_template(name: str, expr: str) -> list[str]:
    if expr in ("yes", "no"):
        return [f"template {name} {{", f"\tvisible = {expr}", "}", ""]
    return _template(name, expr)


def ni_templates() -> list[str]:
    out = _ni_template(f"{NI_PREFIX}_pops_selected", ni_pops_selected())
    out += _ni_template(f"{NI_PREFIX}_pops_unselected", ni_any_shown() or "no")
    for tab in ni_tabs():
        out += _ni_template(f"{NI_PREFIX}_{tab.key}_selected", ni_selected(tab))
        out += _ni_template(f"{NI_PREFIX}_{tab.key}_unselected", ni_unselected(tab))
    strip = ni_strip_shown()
    out += _ni_template(f"{NI_PREFIX}_strip_shown", "yes" if strip is None else strip)
    # the column's scroll area: up exactly while Pops isn't (the window's
    # vanilla rows carry te_ni_pops_selected), so the same expression as the
    # Pops tab's unselected half
    out += _ni_template(f"{NI_PREFIX}_content_shown", ni_any_shown() or "no")
    return out


def _ni_pops_slot(slot: str) -> list[str]:
    def override(name, *lines):
        return [f'blockoverride "{slot}_{name}" {{'] + [f"\t{ln}" for ln in lines] + ["}"]
    return (override("button", f'text = "{NI_POPS_LABEL}"')
            + override("button_tooltip", f'tooltip = "{NI_POPS_TOOLTIP}"')
            + override("button_click", f"onclick = \"[GetVariableSystem.Set('{NI_STORED}', '{NI_FALLBACK}')]\"")
            + override("button_visibility", f"using = {NI_PREFIX}_pops_selected")
            + override("button_visibility_checked", f"using = {NI_PREFIX}_pops_unselected")
            + override("button_selected", f'text = "{NI_POPS_LABEL}"'))


def ni_strips() -> list[str]:
    """te_ni_strips: the window's strips side by side in one centered row,
    one vanilla tab_buttons per five tabs, each at the narrow width (540), as
    the Timeline Extended window's full-screen frame has them."""
    keys = [NI_FALLBACK] + [t.key for t in ni_tabs()]
    by_key = {t.key: t for t in TABS}
    out = ["### The strips: Pops, then each public tab in NI_ORDER, five a strip, side by",
           "### side and centered, each at the narrow strip width.",
           "type te_ni_strips = hbox {",
           "\tlayoutpolicy_horizontal = expanding",
           "\tlayoutpolicy_vertical = fixed",
           "",
           "\texpand = {}"]
    for i in range(0, len(keys), NI_PER_STRIP):
        out += ["\ttab_buttons = {"] + [f"\t\t{ln}" for ln in WIDE_STRIP] + [""]
        for j, (slot, key) in enumerate(zip(SLOTS, keys[i:i + NI_PER_STRIP])):
            if j:
                out.append("")
            out.append(f"\t\t### {key}")
            lines = (_ni_pops_slot(slot) if key == NI_FALLBACK
                     else _slot(slot, by_key[key], COUNTRY_ROOT, NI_STORED, NI_PREFIX, ni_tooltip(by_key[key])))
            out += [f"\t\t{ln}" for ln in lines]
        out.append("\t}")
    return out + ["\texpand = {}", "}"]


def ni_help_button(tab: Tab) -> list[str]:
    """The header's "?": the system's Help page, which only reads."""
    return ["te_help_button = {", f"\tonclick = \"[GetVariableSystem.Set('te_popup', 'help_{tab.key}')]\"", "}"]


def _ni_own(tab: Tab) -> list[str]:
    return (["### The player's own country: the window's full-screen mount, with its gate,",
             "### its entry and its controls.",
             "flowcontainer = {",
             f'\tname = "{NI_PREFIX}_{tab.key}_own"',
             f'\tvisible = "[{LOCAL}]"',
             "\tparentanchor = hcenter",
             "\tdirection = vertical",
             "\tignoreinvisible = yes",
             ""]
            + [f"\t{ln}" for ln in _content(tab, wide=True)] + ["}"])


def _ni_other(tab: Tab) -> list[str]:
    out = ["### Another country: the tab's header, its readout if it has one, then its",
           "### sections under the window's Country, with no journal entry and no frame.",
           "flowcontainer = {",
           f'\tname = "{NI_PREFIX}_{tab.key}_other"',
           f'\tvisible = "[{not_(LOCAL)}]"',
           "\tparentanchor = hcenter",
           "\tdirection = vertical",
           "\tignoreinvisible = yes",
           "\tspacing = 10",
           "",
           "\tdefault_header = {",
           "\t\tusing = default_list_position",
           '\t\tblockoverride "text" {',
           f'\t\t\ttext = "{tab.label}"',
           "\t\t}"]
    out += [f"\t\t{ln}" for ln in ni_help_button(tab)] + ["\t}"]
    if tab.readout:
        sgui, readout = tab.readout
        out += ["",
                "\t### What the tab shows without its entry, as the frame's tab_before_gate does.",
                "\tflowcontainer = {",
                f'\t\tvisible = "[{shown(sgui, COUNTRY_ROOT)}]"',
                "\t\tusing = default_list_position",
                "\t\tdirection = vertical",
                "\t\tignoreinvisible = yes",
                "",
                f"\t\t{readout} = {{}}",
                "\t}"]
    return out + ["", f"\t{tab.wide} = {{}}", "}"]


def ni_tabs_type() -> list[str]:
    """te_ni_tabs: the window's column, one flowcontainer a public tab, up only
    while its tab is shown, holding its two mounts."""
    out = ["### The window's column, in its scroll area (te_ni_content): each public tab's",
           "### pair of mounts, up only while its tab is shown.",
           "type te_ni_tabs = flowcontainer {",
           '\tname = "te_ni_tabs"',
           "\tparentanchor = hcenter",
           "\tdirection = vertical",
           "\tignoreinvisible = yes",
           "\tmargin_top = 10",
           "\tmargin_bottom = 15"]
    for tab in ni_tabs():
        out += ["",
                f"\t### {tab.key}",
                "\tflowcontainer = {",
                f'\t\tname = "{NI_PREFIX}_{tab.key}_tab"',
                f"\t\tusing = {NI_PREFIX}_{tab.key}_selected",
                "\t\tparentanchor = hcenter",
                "\t\tdirection = vertical",
                "\t\tignoreinvisible = yes",
                ""]
        out += [f"\t\t{ln}" if ln else "" for ln in _ni_own(tab)]
        out.append("")
        out += [f"\t\t{ln}" if ln else "" for ln in _ni_other(tab)]
        out.append("\t}")
    return out + ["}"]


NI_HEADER = [
    "### AUTO-GENERATED by scripts/generators/gen_te_systems_window.py from its TABS registry (the public",
    "### tabs, in NI_ORDER). Do not edit.",
    "### National Info, the Census Data window (gui/pop_browser_panel.gui): its selection templates,",
    "### its strip (te_ni_strips) and its column of mounts (te_ni_tabs), which the window instances in",
    "### its ### MOD: National Info blocks. The generator's National Info section has the rule.",
    "",
]


def _validate_ni() -> None:
    keys = {t.key for t in TABS}
    if NI_ORDER[0] != NI_FALLBACK or len(set(NI_ORDER)) != len(NI_ORDER) or set(NI_ORDER[1:]) - keys:
        raise ValueError("NI_ORDER: Pops first, then tab keys, each once")
    for t in TABS:
        if t.public and t.key not in NI_ORDER:
            raise ValueError(f"{t.key} is public: give it a place in NI_ORDER")
        if t.public and t.wide is None:
            raise ValueError(f"{t.key} is public: National Info draws its wide layout")


def render_ni() -> str:
    _validate()
    _validate_ni()
    lines = list(NI_HEADER)
    lines += ["### Which tab is shown: the last one chosen while it is open for the window's",
              "### country, otherwise Pops. A tab's unselected half shows while it is on the",
              "### strip for that country and not shown. Then the strip's gate and the",
              "### column's (every tab but Pops).", ""]
    lines += ni_templates()
    lines += ["types te_national_info_generated_types", "{"]
    for i, part in enumerate((ni_strips(), ni_tabs_type())):
        if i:
            lines.append("")
        lines += [f"\t{ln}" if ln else "" for ln in part]
    lines.append("}")
    return "\n".join(lines) + "\n"


# --- the file -----------------------------------------------------------------

HEADER = [
    "### AUTO-GENERATED by scripts/generators/gen_te_systems_window.py from its TABS registry. Do not edit.",
    "### The Timeline Extended window's strip, selection templates and tab mounts;",
    "### gui/te_systems_window.gui instances them. The generator's docstring has the",
    "### selection rule and how to add a tab.",
    "",
]


def _validate() -> None:
    if not (TABS[0].key == "nation" and TABS[0].open_ is None and TABS[0].strip is None):
        raise ValueError("Nation is the first tab and the fallback: always open, always on the strip")
    if len({t.key for t in TABS}) != len(TABS) or "tax_probes" in {t.key for t in TABS}:
        raise ValueError("tab keys are unique and never the developer tab's")
    for t in TABS:
        if t.open_ is not None and t.tooltip_expr is None and not (t.unlock and t.locked):
            raise ValueError(f"{t.key}: a tab with an open gate shows a checklist while grayed: "
                             "give it unlock and locked, or a tooltip_expr")


def render() -> str:
    _validate()
    lines = list(HEADER)
    lines += ["### Which tab is shown: the last one chosen while it is open, otherwise",
              "### Nation, which always is. A system tab's unselected half shows while it",
              "### is on the strip and not shown; Nation's while another tab is.", ""]
    lines += templates()
    lines += ["types te_systems_window_generated_types", "{"]
    for i, part in enumerate((fullscreen_frame(), strips_narrow(), tabs_narrow(), strips_wide(), tabs_wide(),
                              sr_milestones())):
        if i:
            lines.append("")
        lines += [f"\t{ln}" if ln else "" for ln in part]
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    outputs = [(GUI_OUT, BOM + render().encode("utf-8")), (NI_OUT, BOM + render_ni().encode("utf-8"))]
    if "--check" in argv:
        stale = [path for path, data in outputs if not path.exists() or path.read_bytes() != data]
        for path in stale:
            print(f"stale: {path} (run python3 scripts/generators/gen_te_systems_window.py)")
        return 1 if stale else 0
    for path, data in outputs:
        path.write_bytes(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
