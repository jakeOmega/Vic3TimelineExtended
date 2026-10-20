# The Nation tab: what the country carries for good, in one place — design

## Context

The mod applies a large and growing number of modifiers to a country with no duration. A player meets them in the
country panel's Information tab, whose "MODIFIERS" list mixes them with the timed penalties and event outcomes a
player looks there for, and in forms that say little on their own:

- **Scaled modifiers** that script re-applies every month or year (Wealth Concentration's `inh_great_fortunes`, the
  Algorithmic Mandate, construction cost scaling). "Great Family Fortunes" means little without the score behind it.
- **Permanent rewards, memberships and policies**: agricultural diffusion, space race milestones, UN conventions, the
  Antarctic research station, the pension age, the officer academies' standing. Each sits in the list for the rest of
  the game.
- **Money carriers** (`country_expenses_add` and income lines with a `country_te_budget_*` twin), which the budget
  panel already itemizes.
- **Modifier sums with no display at all.** Legislative Override Capacity has about 40 sources and decides which
  Forceful Legislation options appear and whether the tax code's Force Through is open, but a player sees it only in
  event tooltips and its concept.

The Judiciary (spec `2026-10-17-judiciary-design.md`, PR #1016) adds a score and four more scaled modifiers, and its
§ 13 hands this tab off. The state panel already hides the mod's bookkeeping modifiers from its rows by name
(`gui_modding_guide.md` gotcha #40, `test_hidden_state_modifiers.py`). Countries have no equivalent.

**Inventory (2026-10-17).** Script adds 695 static modifiers without a duration, counting the parameterized names
(`agdiff_$TECH$`, the space race's `$MILESTONE$` rewards) expanded from their callers. 489 carry a country-level field;
206 carry only state, building or goods fields. Fields don't say where a modifier lands: agricultural diffusion's
`agdiff_*` carry only `state_arable_land_mult` and `overinvestment_modifier` only state fields, yet both are added to the
country and sit in its list, while Grand Monuments' national modifiers land on a journal entry and never reach it. So
§ 4's registry says where each of the 695 lands, and a test keeps it complete.

## Decisions (owner, 2026-10-17)

| Question | Decision |
|---|---|
| Where | A tab in the Timeline Extended window named **Nation**, the **first tab**. Colonial Empire moved to a second strip, beside Seabed; since the owner's play-test of 2026-10-17 all five tabs share one strip |
| What goes on it | **Everything that would sit in the country's modifier list forever**: standing scores and dials, and the permanent rewards, memberships and policies. Named: Legislative Override Capacity, Judicial Independence, Wealth Concentration, arable land from agricultural diffusion, space race rewards not already in the journal, demographic policies, the Antarctic research station, UN conventions, global technological development, the armed forces' standing from training, the private share of construction |
| The country panel | Its modifier list hides what the tab shows, as the state panel hides its bookkeeping modifiers |
| Money carriers | Hidden from the list, with no row: the budget panel itemizes them |
| Credit Standing | No row: the Banking tab owns it. The owner's follow-up (separate work): run the banking cycle's entry always, with its interactions disabled until it activates |
| Nuclear Power | No row. The `nuclear_power` modifier should move onto the Nuclear Program journal entry, where it belongs; **deferred** (owner), since about 60 checks across the mod use it as the "is a nuclear power" test (§ 6). Until then an override keeps it in the country's list |
| Wealth Concentration | Hidden from the lists, nationally on a Nation row and per state in a new section of the state view (§ 5) |
| A spec of its own | Yes: cross-cutting, so not part of the Judiciary |
| Permanent event outcomes | On the tab by default, in the section of the system that granted them. Case by case, an **override** keeps a chosen modifier in the country's list (`KEEP_IN_LIST`, § 4) |
| The space race's colonies | Hidden (owner). The dry run found them already on the Solar Colonization entry, never the country, so nothing changes: the Space Race tab's Our Colonies lists them |
| Section order | Governance, Society, Economy, Science and Space, International |
| Modifier types, not modifiers (2026-10-18, #1030) | Each section's list becomes rows of the modifier types its modifiers carry, "Arable Land: +45%" with every source on hover; the lists move, collapsed, to the bottom. The owner took the issue's eight recommendations (§ 10) |

## 1. What goes where

A modifier the mod applies to a country with no duration goes to exactly one place:

| Kind | Shown | In the country panel's list |
|---|---|---|
| A standing score or dial | A Nation **row**: value, bar where bounded, the engine's breakdown on hover | Hidden |
| A permanent reward, membership or policy | A Nation section's **list**: icon and name, the modifier's own tooltip on hover | Hidden |
| A money carrier | The budget panel's breakdown | Hidden |
| Timed (a duration), or applied to a journal entry or a state | Where it is today | Unchanged |
| An override (`KEEP_IN_LIST`), chosen case by case | Where it is today | Unchanged |

A permanent **event outcome** follows the same rule: by default it goes to the list of the section whose system granted
it, unless an override keeps it in the country's list (owner). A **timed consequence** (Forceful Legislation's decaying penalty, the Judiciary's Court Overhaul) stays in the list,
where a player looks for what just happened to them.

## 2. The tab

- **Nation, the first tab** (owner). The first strip reads Nation, Space Race, Grand Monuments; the second, Colonial
  Empire and Seabed. Three tabs a strip keeps every name at about 160 units (`test_te_systems_window.py`'s budget).
- **Always open, never greyed.** It has no journal entry and no game rule: the exception to style rule 9's "greyed
  until the system's journal entry is active", said where the gate would be. The launcher loses its rule gate
  (`te_window_launcher_sgui` goes), so the window is up for every played country, with every system rule off.
- **Selection.** Nation is first in precedence: the window opens on the tab the player last chose while that tab is
  open, else on Nation, which always is. `test_te_systems_window.py`'s case-by-case check of the selection templates
  grows to five tabs and the two strips' new order.
- **The player's own country**, through `GetPlayer` (observer mode shows nothing, as the window's other gates do).

### 2.1 Layout (`docs/guides/gui_style_guide.md`)

- A fixed 520 root (rule 8), rows at 17 and subheadings at 20 in the tab's own templates (rule 3).
- **Overview**, always shown: reading boxes two to a row (rule 4, the Banking overview's `te_banking_ov_cell`), each a
  caption, a word and a figure: Override Capacity (the Forceful Legislation tier open, and the value), Wealth
  Concentration ("Concentrating", "62 → 68"), Construction Cost ("Scaled by wealth", "+35%") and Global Technology
  ("Spreading", "+60 spread"). Judicial Independence makes a fifth once it exists.
- **Five sections, open** (rule 1), each its score **rows** first, then its **list** (since #1030 its **type rows**, and the lists collapsed at the bottom: § 10). Each list is the country's own
  timed modifiers filtered to the section's names: icon, name, and `TimedModifier.GetTooltip` on hover, so the engine
  renders the effects at their current scale (§ 8). A row's own modifiers ("what it gives now") are a one-line list of
  the same kind under it. An empty list draws nothing, and a section with nothing to show draws nothing (rule 8).
- **How the Nation Works**, collapsed (rule 1), a subheading per row and per list.

| Section | Rows | List |
|---|---|---|
| Governance | Legislative Override Capacity; Judicial Independence (with the Judiciary); Algorithmic Mandate (under Algorithmic Governance) | The armed forces' standing from training (`te_officer_academies_standing`, `te_political_commissars_indoctrination`); heir education's focus (`heir_ed_*`) |
| Society | Wealth Concentration | Demographic policies: the measures (`te_demog_ms_*`), the pension-age positions, the health bill, `te_demog_family_limitation`, `te_demog_lx_gap_politics`; living-standard expectations by strata; the civil rights strategy (`cr_*`); resettlement's politics and the declaration's violation; a dynasty's continuity of title |
| Economy | Construction Cost; Private Construction (while excess private construction or Overinvestment is in force) | Agricultural diffusion (`agdiff_*`); the private share of construction; the tax code's interest-group views, reactions and relief; the monetary arrangements, inflation and exchange-rate bands while the banking cycle's entry isn't running (on the entry otherwise); the colonial programmes |
| Science and Space | Global Technological Development | Space race milestones (`sr_first_<m>`, `sr_<m>`), the probe's data, the commercial space dividend; orbital debris and its clearance's prestige; the Antarctic research station and the Antarctic regime; seabed policy's costs and the long haul |
| International | — | UN conventions the country is bound by outside the organisation's entry, membership benefits and non-member penalties, regime terms, embargoes, sanctions, mandates, development grants and electoral observers; intelligence sharing; the nuclear taboo; a colonial subject's overlord in decline |

The List column is the section's systems; since #1030 the lists sit under these names in Where These Come From, and § 10's table says which rows each section shows. The registry (§ 4) holds the exact names. The dry run (2026-10-17) found the space race's discoveries and colonies, the UN's own conventions and standing, Grand Monuments' and the banking cycle's modifiers on their journal entries, never the country, and kept the covert operations' effects on a target in its list (`KEEP_IN_LIST`): what a foreign operation is doing to a country belongs where a player looks for what just happened, and one shares its display name with a timed modifier.

### 2.2 The rows

- **Legislative Override Capacity: 2.5.** A bar from 0 to +30 (−6 to +8 until the owner's play-test of 2026-10-17: every value below 0 plays the same, so that stretch was wasted) with thin threshold lines at 0, 2 and 4 (rule 5), each
  with its own hover: at 0 the Forceful Legislation event appears, at 2 its decisive option and the tax code's Force
  Through, at 4 its strongest. Under the bar, "Forceful Legislation: Push decisively", naming the strongest option open,
  or "Not offered" below 0. Hover: every source with its contribution
  (`GetPlayer.GetModifier.GetValueWithBreakdownFor('country_legislative_override_capacity_add')`, `gui_modding_guide.md`
  § Modifier Access in GUI), the decaying penalty among them. This is the row the tab is most needed for.
- **Judicial Independence: 63 → 100**, as a bar heading for its ceiling, once the Judiciary lands. Hover: the ceiling's
  breakdown (the court law's line and the paper court's); "what it gives now" is the score modifier's line under it.
- **Algorithmic Mandate: +12 legitimacy**, under Algorithmic Governance only (`algorithmic_mandate_value`). Hover: how
  the mandate follows living standards against expectations.
- **Wealth Concentration: 62 → 68**, as a bar (`te_inh_concentration_display`, `te_inh_concentration_target`). Hover:
  the concept's explanation; "what it gives now" is Great Family Fortunes' or Dispersed Wealth's line under it. The detail
  (the target's five terms, the most and least concentrated states) stays in the Demographics tab of the Population
  panel, and the row says so (style rule 9: send players to the tab).
- **Construction Cost: +35%** (`var:prior_construction_scaling`, the multiplier the yearly pulse applied, either rule's
  branch). Hover: GDP per capita against the reference, and the curve's floor and ceiling.
- **Private Construction**, while either modifier is in force (`too_much_private_construction`,
  `overinvestment_modifier`), each modifier's line under it. Hover: why it exists (an investment pool the private queue
  can't spend) and how it ends.
- **Global Technological Development: +60 technology spread** (`global_tech_spread_script_value`, a flat
  `country_tech_spread_add`). Hover: what moves it, +20 for each of several modern technologies (Television, Modern
  Automotive Technology and others) once any great power has researched it.

## 3. Hiding them from the country panel

- **Where the list is.** Vanilla's `gui/country_panel.gui` (1.14, from the owner's upload). The Information tab's type
  `country_panel_information_content` (lines 379–1412, about 1,030 lines) ends with a "MODIFIERS" `default_header` and
  a `flowcontainer` over `Country.GetTimedModifiers`: icon, name, remaining duration, the modifier's tooltip on hover.
  The panel's Modifiers tab (`modifier_list`) is a different view, the summed modifier types with their breakdowns.
  It is left alone; the Judiciary's tooltip lines belong there.
- **How (proposal): redefine that one type, not the file.** A mod file `gui/00_te_country_panel_information.gui`
  redefines `country_panel_information_content` (gotcha #30: the Community Mod Framework redefines 29 vanilla types this
  way, and not this one). Which of two definitions wins is unread, but CMF's `00_` naming wins under both orders the
  guide leaves open: first loaded alphabetically, or mods after vanilla with the last definition winning. The type is
  copied from vanilla verbatim, changed only in three `### MOD: Nation tab` blocks that keep each vanilla line they
  replace as a `# vanilla:` comment (the tax code's convention in `goods_panel.gui`). The generator (§ 4) writes it
  from a committed copy of vanilla's file, so a vanilla patch is a new fixture and a rerun:
  - the item takes `using = te_nation_hidden_filter`, a generated template (§ 4) holding
    `visible = "[Not(Or(EqualTo_string(TimedModifier.GetName, Localize('<key>')), …))]"`, two-argument `Or`s (gotcha
    #40) in a balanced tree, so its nesting stays about log₂ of the names;
  - the flowcontainer takes `ignoreinvisible = yes`;
  - the header and the flowcontainer are shown on
    `GreaterThan_int32(GetDataModelSize(Country.GetTimedModifiers), FixedPointToInt(Country.MakeScope.ScriptValue('gui_country_hidden_modifier_count')))`,
    the state panel's form (`states_panel.gui`), so the header doesn't stand over an empty list.
- **Every country's panel, the player's and the AI's.** The Information tab shows any country, and one filter serves
  all. An AI country's hidden modifiers then show only in breakdowns, until a later version lets the tab show the
  viewed country.
- **Hidden isn't gone.** Breakdown tooltips (legitimacy's, the Modifiers tab's) still name each source. The hidden
  modifiers keep their own icons, since the tab draws them (the Grand Monument card's precedent in gotcha #40).
- **Vanilla drift.** The fixture is vanilla's `country_panel.gui` byte for byte (`test_fixtures/vanilla_gui/`, as
  `topbar.gui`'s), and a test fails when the installed game's differs. A patch replaces the fixture and reruns the
  generator, which raises if vanilla moved a line a block hooks onto.
- **The fallback**, if the redefinition loses to vanilla's: replace the whole `country_panel.gui` (4,420 lines), as the
  mod already replaces `states_panel.gui`.
- **Cost.** The filter is 233 comparisons per modifier row (the dry run's count), evaluated only while the
  Information tab is open, in one `visible` of about 20,000 characters. A generated GUI already ships a 24,619-character
  expression (`te_budget_generated_charts.gui`). If the play-test shows a stutter, the filter shrinks by moving names to
  `KEEP_IN_LIST`.

## 4. The registry and its generator

The names must agree in four places: each section's list, the rows' lines, the country panel's filter and the counts.
They come from one registry, as the budget breakdown's generated files do.

- **`scripts/generators/gen_nation_tab.py`** holds:
  - `SECTIONS`: per section, the names its list shows;
  - `ROWS`: per row, its section and the modifiers it explains (shown under the row, "what it gives now");
  - `KEEP_IN_LIST`: the overrides, kept in the country's list, each with its reason (owner: case by case);
  - `NOT_ON_COUNTRY`: candidates that land on a journal entry, a state, a building, an interest group, a movement or a
    power bloc, with where.
  - The money carriers are not listed: they are the budget breakdown's sources (`gen_budget_breakdown.SOURCES`),
    hidden with no row wherever they land.
- **It writes** `gui/te_nation_generated.gui` (`te_nation_hidden_filter`, `te_nation_list_<section>` and
  `te_nation_row_<row>`), `common/script_values/te_nation_generated_values.txt` (`gui_country_hidden_modifier_count`
  and `te_nation_list_<section>_count`) and the country panel's type (§ 3). All three are generated, never hand-edited
  (`docs/auto_generated_files.md`).
- **`test_nation_tab.py`:**
  - the generated files match a fresh run;
  - every candidate is placed by exactly one registry line: every static modifier script adds without a duration,
    whatever its fields (parameterized names expanded from their callers; 695 on 2026-10-17). An entry may name a
    family with one `*` (`sr_first_*`, `sr_probe_*_data`), and an exact name wins over a family;
  - every registry line places at least one candidate (a renamed modifier fails, not lingers);
  - no hidden name shares its display name with a modifier the list keeps, since the filter matches names;
  - the redefined type is vanilla's but for its marked blocks, and the fixture is the installed game's file (skipped
    without a game).
- **Adding something later** is one registry line and a regeneration; the test fails until the line exists.

## 5. Wealth Concentration in the state view (owner)

- **Where:** the state panel's Demographics subtab already has a Wealth section (`te_state_demog_wealth`,
  `gui/te_demographics_widgets.gui`): the state's Gini, then once the census has scored the state its Wealth
  Concentration and a bar heading for its target ("58 → 64"). Phase 2 adds, under them, the state's own modifiers from
  the score and the law, each its tooltip on hover, found in `State.GetTimedModifiers` by name:
  - **what the score does here**: whichever of `inh_concentrated_property`, `inh_dispersed_property` and
    `inh_land_hunger` the state carries;
  - **what the inheritance law does here**: `inh_forced_heirship_rural`, `inh_primogeniture_rural` or
    `inh_undivided_farm_rural`, scaled by the state's farming share.
- **Hidden from the state's modifier rows** by the card precedent (gotcha #40): the six names in both rows' filters,
  count terms in `gui_state_hidden_modifier_count`, and the six in a new `SHOWN_ON_A_CARD_NAMES` in
  `test_hidden_state_modifiers.py` (a prefix `inh_` would also catch the country's own inheritance modifiers). That
  test learns the card list's form, a `visible` that picks names out rather than leaving them out. The state filters
  keep their own test rather than the registry: they are inline in a full-file `states_panel.gui` and already held to
  the static modifiers there.
- **Gated on its data:** the list sits outside the scored part's gate, so the law's line shows on a state the census
  hasn't scored, and an item shows only while its modifier is there, so no hidden modifier goes unshown.
- **Nationally**, `inh_great_fortunes` and `inh_dispersed_wealth` are hidden from the country's list and shown under the
  Nation row (§ 2.2).

## 6. Nuclear Power: deferred (owner)

`nuclear_power` belongs on the Nuclear Program journal entry rather than the country, where the rest of the programme's
state already shows. The move is deferred because it is sizable next to this spec:

- **About 60 checks read `has_modifier = nuclear_power` as "is a nuclear power"**, many on another country (`nuke.txt`,
  `un_regime_triggers.txt`, the war support values, the nuclear events). They first switch to one variable-backed
  trigger (`nd_believed_armed` already wraps the check, but few use it), set where the modifier is granted and removed.
- **Then the modifier moves** onto `je:je_nuclear_program`, re-applied by the entry's weekly pulse (its guard already
  makes that safe), with an old-save repair to remove the country's copy.
- **A decision first:** an entry closes when a country drops below `possible` (a great power losing rank), which would
  take the modifier's prestige with it while the country is still armed. Either an armed country keeps its entry, or
  the effects stop while it is closed.

Until then, the registry's `KEEP_IN_LIST` holds `nuclear_power`, with this section as its reason.

## 7. Phases

1. **The tab and the hiding**: §§ 2–4, and the Colonial Empire tab's move.
2. **Wealth Concentration in the state view** (§ 5).
3. **The Judiciary's rows**, in whichever of this and the Judiciary's phase 1 lands second: Judicial Independence's
   row; `te_judicial_independence`, `te_jud_votes_legitimacy`, `te_jud_unelected_authority` and
   `te_jud_algorithmic_capture` into the registry (Governance). `te_jud_court_overhaul` has a duration, so it is no
   candidate.
4. **Later**, as systems add standing modifiers: a registry line each. A later version could show the viewed country.
   Nuclear Power's move (§ 6) is its own piece of work.

## 8. Engine facts to verify

| Fact | Check |
|---|---|
| `00_te_country_panel_information.gui`'s type replaces vanilla's | Play-test: the hidden modifiers are gone from the Information tab, and nothing else in it changed. Fallback: the whole-file replacement (§ 3) |
| A timed modifier found by name in `GetPlayer.GetTimedModifiers` renders its scaled tooltip inside the tab | Play-test: Wealth Concentration's "what it gives now" matches the modifier's tooltip. Fallback: a script-value line per effect |
| `GetValueWithBreakdownFor` lists every source of the override sum | Play-test: the hover lists the laws, institutions and the decaying penalty. The recipe is documented; the covert panel uses it for hovers only, so a failure loses a tooltip, not a number |
| A template can carry a generated `visible` expression | Precedent: the window's own selection templates (`te_systems_window_*_selected`) |
| A blockoverride can paste a template (`blockoverride "filter" { using = te_nation_list_<section> }`) into a type's list item | Play-test: each section lists only its own modifiers. Fallback: the generator writes one list type per section |
| A `visible` of about 20,000 characters parses | Precedent: a 24,619-character expression in `te_budget_generated_charts.gui`. The play-test reads `error.log` for a GUI parse error on `te_nation_generated.gui` |

## 9. Rulings

The owner answered the first draft's five questions and the revision's three (2026-10-17); the Decisions table
records them. Nothing is open. The implementation plan (`docs/superpowers/archive/plans/2026-10-17-nation-tab.md`) was dry-run
against the repository the same day; its findings are folded in above (the colonies already off the country, covert
effects kept in the list, the budget's sources as the carriers, the state view's Wealth section already there).

## 10. Type rows (#1030, 2026-10-18)

The owner's play-test (2026-10-17): "It would be better to have the modifier types listed in the Nation tab rather
than the modifiers themselves. For example — Arable Land, with a breakdown of tech, spread modifiers, etc. As is, it is
not clear to a new player where or why these modifiers are there." "Green Revolution Diffusion" says nothing about what
it does or why the player has it; **Arable Land: +45%**, with a hover listing Intensive Agriculture, Nitrogen Fixation
and Green Revolution Diffusion, answers both.

**Engine fact, settled** (owner, 2026-10-17): the country's own modifier holds the `state_` fields its modifiers carry,
so `GetPlayer.GetModifier.GetValueWithBreakdownFor('state_arable_land_mult')` reads Arable Land with its sources, as the
country panel's Modifiers tab does (`docs/systems/modifier_scope_reference.md`).

**Rulings** (owner, 2026-10-18: the issue's recommendations, all eight):

| Question | Ruling |
|---|---|
| Replace the per-modifier lists? | Keep them, collapsed, in one panel at the bottom, **Where These Come From**, under each section's name (rule 2: the two modifiers that carry no field, `cr_cooptation_expired` and `te_inflation_band_comfort`, and each modifier's full effects stay one click away) |
| Re-cut the sections by what a type affects? | Yes: one national total can't repeat in up to four sections. Prestige is International's even where a space milestone grants it, and the milestone shows in its breakdown. The section names stay |
| Every type, or a curated handful? | Every type the tab's modifiers carry, gated, but for 35 `NOT_A_ROW` exclusions. Demote by one registry line if the play-test finds a section long |
| When does a row show? | While the country holds one of the tab's own modifiers (its lists' or its score rows') that carries the type, not whenever the total is non-zero, which would make the tab a copy of the Modifiers tab. Vanilla sources still appear in the breakdown |
| Interest-group approval | Rows in Governance (79 of the 212 listed modifiers carry an approval line, and the Interest Group panel shows one group at a time). An icon strip of the eight groups is a later refinement |
| State-level rows | The national contribution, with a note on hover that a state's own sources are in its panel (the capital's total would mix in that state's decrees and buildings). The same note for building, interest-group and character rows |
| Score rows' "what it gives now" | Unchanged: there the modifier's scaled tooltip is exactly what the score gives |
| `_bool` types | Status lines: "Nuclear Program Freeze: In force", `GetFullEntryDescFor` on hover, as vanilla shows `country_disallow_law_no_schools_bool` |

**Layout.** Each section: its score rows (unchanged), then its type rows under small subheadings (`te_nation_subheader`).
A row reads "**Label:** value": the label is the type's own loc name (`$state_arable_land_mult$`), the value
`GetValueWithBreakdownFor` (the engine's format; its hover lists every source: technologies, laws, institutions,
principles, timed modifiers and the tab's own, a scaled one with its multiplier). The row's hover is the type's `_desc`,
plus the scope note for a `state_`, `building_`, `interest_group_` or `character_` type. A subheading shows over its
rows only; International draws nothing without one, Science and Space nothing without a row or a technology spread.

| Section | Rows | Groups |
|---|---|---|
| Governance | 23 | Authority and Bureaucracy; Legitimacy and Laws; Interest Groups (the eight approvals, three political strengths, two attractions) |
| Society | 25 | Living Standards; Acceptance and Assimilation; Unrest; Population; Demography (most under the Demographics rule) |
| Economy | 29 | Production (Arable Land, throughputs, construction efficiency); Taxes and Minting; Investment and Credit; Trade |
| Science and Space | 10 | Research; Space and the Seabed |
| International | 27 | Standing Abroad; Covert Defense; War Support; Nuclear Weapons (two status lines); Commitments |
| Not rows | 35 | A score row's: Wealth Concentration's political strengths, Construction Cost's two, Legislative Override Capacity, Judicial Independence's votes and radicalism lines, Overinvestment's 13 pool contributions and weekly construction cap under Private Construction, the technology spread. The Banking tab's six. The arms embargo's seven goods trade advantages, folded into its own line |

**Registry** (`gen_nation_tab.py`, beside § 4's): `TYPE_ROWS` (section → group → types; a family with one `*`, such as
`interest_group_ig_*_approval_add`, lists its types alphabetically in its place), `STATUS_ROWS` (the bools, same shape)
and `NOT_A_ROW` (type or family → what shows it). A type's feeders are the tab's modifiers whose static block carries it
(`carried_types`). `test_nation_tab.py`'s `TypeRowsTest` holds every carried type to exactly one line, an exact name
winning over a family, and every line to at least one type; bools only to status lines; every row to a loc name and a
`_desc`, mod or vanilla; and each generated count to its row's feeders.

**Generated.** `gui/te_nation_generated.gui` gains `te_nation_types_<section>`. The values file gains
`te_nation_type_<type>_count` (the row's feeders), `te_nation_group_<group>_count` and `te_nation_types_<section>_count`
(the unions under them, so a hidden group or section evaluates no row), and `te_nation_lists_count` (Where These Come
From's gate). `localization/english/te_nation_generated_l_english.yml` holds each row's text and hover, splicing the
type's name and `_desc` (organize_loc's `NATION_GENERATED`); the group names and the scope notes are hand-written, in
`te_miscellaneous_l_english.yml`.

**Edge cases.** A `state_` row is the national contribution, not a state's total: they agree for Arable Land, whose
sources are all national, and not for Migration Attraction, which decrees and production methods also feed. Feeders of
opposite sign can leave a row at 0 with a non-empty breakdown; it shows anyway. The totals include timed modifiers, so a
row can show more than the tab's own sources. Four names repeat (Prestige, Authority, Minting and Cultural Pull each have
an `_add` and a `_mult` row), told apart by their format, as the Modifiers tab does.

**Engine facts to verify** (play-test list, checks 14–21): the generated types resolving `te_nation_row` from
`te_nation_tab.gui`, which loads after them; the figure's breakdown hover winning over the row's own tooltip; the
longest breakdown (Maximum Innovation Investment, fed by more than 80 technologies) fitting on screen;
`GetFullEntryDescFor` on a bool; no stutter with about 30 rows.
