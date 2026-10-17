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

**Inventory (2026-10-17).** 367 static modifiers with country-level fields are added without a duration somewhere in
script, 67 of them with a multiplier; parameterized names (`agdiff_$TECH$`, the space race's `$MILESTONE$` rewards) add
more. Some of them land on a journal entry rather than the country (Grand Monuments' national modifiers, the space race's
mission choices) and never reach the country panel's list. § 4's registry classifies every one, and a test keeps it
complete.

## Decisions (owner, 2026-10-17)

| Question | Decision |
|---|---|
| Where | A tab in the Timeline Extended window named **Nation**, the **first tab**. Colonial Empire moves to the second strip, beside Seabed |
| What goes on it | **Everything that would sit in the country's modifier list forever**: standing scores and dials, and the permanent rewards, memberships and policies. Named: Legislative Override Capacity, Judicial Independence, Wealth Concentration, arable land from agricultural diffusion, space race rewards not already in the journal, demographic policies, the Antarctic research station, UN conventions, global technological development, the armed forces' standing from training, the private share of construction |
| The country panel | Its modifier list hides what the tab shows, as the state panel hides its bookkeeping modifiers |
| Money carriers | Hidden from the list, with no row: the budget panel itemizes them |
| Credit Standing | No row: the Banking tab owns it. The owner's follow-up (separate work): run the banking cycle's entry always, with its interactions disabled until it activates |
| Nuclear Power | No row. The `nuclear_power` modifier moves onto the Nuclear Program journal entry: it is odd as a country modifier (§ 6) |
| Wealth Concentration | Hidden from the lists, nationally on a Nation row and per state in a new section of the state view (§ 5) |
| A spec of its own | Yes: cross-cutting, so not part of the Judiciary |

## 1. What goes where

A modifier the mod applies to a country with no duration goes to exactly one place:

| Kind | Shown | In the country panel's list |
|---|---|---|
| A standing score or dial | A Nation **row**: value, bar where bounded, the engine's breakdown on hover | Hidden |
| A permanent reward, membership or policy | A Nation section's **list**: icon and name, the modifier's own tooltip on hover | Hidden |
| A money carrier | The budget panel's breakdown | Hidden |
| One a system panel already lists (the space race's colonies, in the Space Race tab's Our Colonies) | That panel | Hidden |
| Timed (a duration), or applied to a journal entry or a state | Where it is today | Unchanged |

A **timed consequence** (Forceful Legislation's decaying penalty, the Judiciary's Court Overhaul) stays in the list,
where a player looks for what just happened to them.

## 2. The tab

- **Nation, the first tab** (owner). The first strip reads Nation, Space Race, Grand Monuments; the second, Colonial
  Empire and Seabed. Three tabs a strip keeps every name at about 160 units (`test_te_systems_window.py`'s budget).
- **Always open, never greyed.** It has no journal entry and no game rule: the exception to style rule 9's "greyed
  until the system's journal entry is active", said where the gate would be. The launcher's gate
  (`te_window_launcher_sgui`) gains it, so the window is reachable with every system rule off.
- **Selection.** Nation is first in precedence: the window opens on the tab the player last chose while that tab is
  open, else on Nation, which always is. `test_te_systems_window.py`'s case-by-case check of the selection templates
  grows to five tabs and the two strips' new order.
- **The player's own country**, through `GetPlayer` (observer mode shows nothing, as the window's other gates do).

### 2.1 Layout (`docs/guides/gui_style_guide.md`)

- A fixed 520 root (rule 8), rows at 17 and subheadings at 20 in the tab's own templates (rule 3).
- **Overview**, always shown: reading boxes two to a row (rule 4, the Banking overview's `te_banking_ov_cell`), each a
  caption, a word and a figure: Override Capacity (the Forceful Legislation tier open and the value), Wealth
  Concentration ("62 → 68"), Construction Cost ("+35%"), and Judicial Independence once it exists.
- **Five sections, open** (rule 1), each its score **rows** first, then its **list**. Each list is the country's own
  timed modifiers filtered to the section's names: icon, name, and `TimedModifier.GetTooltip` on hover, so the engine
  renders the effects at their current scale (§ 8). An empty list draws nothing, and a section with nothing to show
  draws nothing (rule 8).
- **How the Nation Works**, collapsed (rule 1), a subheading per row and per list.

| Section | Rows | List |
|---|---|---|
| Governance | Legislative Override Capacity; Judicial Independence (with the Judiciary); Algorithmic Mandate (under Algorithmic Governance) | The armed forces' standing from training (`te_officer_academies_standing`, `te_political_commissars_indoctrination`) |
| Society | Wealth Concentration | Demographic policies: `te_demog_family_limitation`, the pension-age positions (`te_demog_pension_pos_*`), the health bill (`te_demog_health_bill_up`/`_down`), `te_demog_lx_gap_politics` |
| Economy | Construction Cost; Private Construction (while excess private construction or Overinvestment is in force) | Agricultural diffusion (`agdiff_*`, the arable land and yields a world-first farming technology spreads); the private share of construction (`te_construction_market_private_share_modifier`) |
| Science and Space | Global Technological Development | Space race rewards not already in the journal: milestones (`sr_first_<m>`, `sr_<m>`), discoveries (`sr_discovery_*`), the probe's data and the mission choices that land on the country; orbital debris (`te_orbital_debris`); the Antarctic research station (`te_antarctic_station_modifier`, `un_regime_antarctic_station_modifier`, `un_antarctic_policy_modifier`) |
| International | — | UN conventions and regime terms the country is bound by (`un_*_modifier` from `un_vote_cast_effects.txt`, `un_regime_effects.txt`, `un_justice_effects.txt`, `un_teeth_effects.txt`) |

The registry (§ 4) holds the exact names; the families above are what it starts from.

### 2.2 The rows

- **Legislative Override Capacity: 2.5.** A bar from −6 to +8 with thin threshold lines at 0, 2 and 4 (rule 5), each
  with its own hover: at 0 the Forceful Legislation event appears, at 2 its decisive option and the tax code's Force
  Through, at 4 its strongest. Under the bar, "Forceful Legislation: Push decisively", naming the strongest option open,
  or "Not offered" below 0. Hover: every source with its contribution
  (`GetPlayer.GetModifier.GetValueWithBreakdownFor('country_legislative_override_capacity_add')`, `gui_modding_guide.md`
  § Modifier Access in GUI), the decaying penalty among them. This is the row the tab is most needed for.
- **Judicial Independence: 63 → 100**, as a bar heading for its ceiling, once the Judiciary lands. Hover: the ceiling's
  breakdown (the court law's line and the paper court's); "what it gives now" is the score modifier's tooltip.
- **Algorithmic Mandate: +12 legitimacy**, under Algorithmic Governance only (`algorithmic_mandate_value`). Hover: how
  the mandate follows living standards against expectations.
- **Wealth Concentration: 62 → 68**, as a bar (`te_inh_concentration_display`, `te_inh_concentration_target`). Hover:
  the concept's explanation; "what it gives now" is Great Family Fortunes' or Dispersed Wealth's tooltip. The detail
  (the target's five terms, the most and least concentrated states) stays in the Demographics tab of the Population
  panel, and the row says so (style rule 9: send players to the tab).
- **Construction Cost: +35%** (`var:prior_construction_scaling`, the multiplier the yearly pulse applied, either rule's
  branch). Hover: GDP per capita against the reference, and the curve's floor and ceiling.
- **Private Construction**, while either modifier is in force (`var:too_much_private_construction_cached`): the
  per-project cap it raises and the construction efficiency it costs, with "Overinvestment" when that is in force.
  Hover: why it exists (an investment pool the private queue can't spend) and how it ends.
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
  copied from vanilla verbatim, with three lines changed and marked `# TE:`, as `te_tradition_of_free_elections.txt`
  marks its changes:
  - the item takes `using = te_nation_hidden_filter`, a generated template (§ 4) holding
    `visible = "[Not(Or(EqualTo_string(TimedModifier.GetName, Localize('<key>')), …))]"`, two-argument `Or`s (gotcha
    #40);
  - the flowcontainer takes `ignoreinvisible = yes`;
  - the header and the flowcontainer are shown on
    `GreaterThan_int32(GetDataModelSize(Country.GetTimedModifiers), FixedPointToInt(Country.MakeScope.ScriptValue('gui_country_hidden_modifier_count')))`,
    the state panel's form (`states_panel.gui`), so the header doesn't stand over an empty list.
- **Every country's panel, the player's and the AI's.** The Information tab shows any country, and one filter serves
  all. An AI country's hidden modifiers then show only in breakdowns, until a later version lets the tab show the
  viewed country.
- **Hidden isn't gone.** Breakdown tooltips (legitimacy's, the Modifiers tab's) still name each source. The hidden
  modifiers keep their own icons, since the tab draws them (the Grand Monument card's precedent in gotcha #40).
- **Vanilla drift.** The copied type joins the GUI overrides the vanilla patch runbook 3-way merges on every patch
  (`docs/guides/vanilla_patch_runbook.md`, `gui_modding_guide.md` § "GUI 3-way merge across vanilla patches"), with the
  vanilla version it was copied from in the file's header.
- **The fallback**, if the redefinition loses to vanilla's: replace the whole `country_panel.gui` (4,420 lines), as the
  mod already replaces `states_panel.gui`.
- **Cost.** The filter is a chain of about 150 comparisons per modifier row, evaluated only while the Information tab
  is open. If the play-test shows a stutter, the chain splits by section into nested `Or`s (no fewer comparisons, but
  each list of the tab already uses its own).

## 4. The registry and its generator

The names must agree in five places: each section's list, the tab's rows, the country panel's filter, the hidden count
and the state panel's filter (§ 5). They come from one registry, as the tax code's generated files do.

- **`scripts/generators/gen_nation_tab.py`** holds:
  - `SECTIONS`: per section, its row keys and list keys;
  - `BUDGET_CARRIERS`: hidden, no row;
  - `SHOWN_ELSEWHERE`: hidden, with the panel that shows each (the space race colonies);
  - `NOT_ON_COUNTRY`: candidates that land on a journal entry or a state, with where;
  - `STAYS`: candidates kept in the list, each with its reason.
- **It writes** `gui/te_nation_generated.gui` (the `te_nation_hidden_filter` template and one filter template per
  section list) and `common/script_values/te_nation_generated_values.txt` (`gui_country_hidden_modifier_count`). Both
  are generated, never hand-edited (`docs/auto_generated_files.md`).
- **`test_nation_tab.py`:**
  - the generated files match a fresh run;
  - every candidate is classified exactly once: every static modifier with a country-level field that script adds
    without a duration (parameterized names expanded from their callers);
  - every registry key is a static modifier;
  - the redefined type is vanilla's but for the three `# TE:` lines (diffed against a committed copy of vanilla's type,
    refreshed by the runbook; CI has no vanilla GUI).
- **Adding something later** is one registry line and a regeneration; the test fails until the line exists.

## 5. Wealth Concentration in the state view (owner)

- **Where:** the state panel's Demographics subtab (`te_state_demog_content`, `gui/te_demographics_widgets.gui`),
  which already shows the state's score as a figure in its stat row. A **Wealth Concentration** section after its
  figures:
  - the state's score as a bar heading for its target ("58 → 64", `var:te_dg_wc` and the state's target), as the
    national bar in the Population panel's Demographics tab;
  - **what the score does here**: the tooltips of whichever of `inh_concentrated_property`,
    `inh_dispersed_property` and `inh_land_hunger` the state carries, found in `State.GetTimedModifiers` by name;
  - **what the inheritance law does here**: `inh_forced_heirship_rural`, `inh_primogeniture_rural` or
    `inh_undivided_farm_rural`, scaled by the state's farming share.
- **Hidden from the state's modifier rows** by the card precedent (gotcha #40): the six names in both rows' filters,
  count terms in `gui_state_hidden_modifier_count`, and `"inh_"` in `test_hidden_state_modifiers.py`'s
  `SHOWN_ON_A_CARD_PREFIXES`. The state filter's names come from the same registry (§ 4).
- **Gated on its data**, part by part: the bar on a scored state (states are scored under the Demographics rule), the
  law's line on the modifier being there, so no hidden modifier goes unshown.
- **Nationally**, `inh_great_fortunes` and `inh_dispersed_wealth` are hidden from the country's list and shown by the
  Nation row (§ 2.2).

## 6. Nuclear Power moves to its journal entry (owner)

`nuclear_power` is added to the country once the stockpile reaches a warhead (`je_nuclear_program.txt`, guarded by
`NOT = { has_modifier = nuclear_power }`). It moves onto `je:je_nuclear_program`, where the rest of the programme's state
already shows:

- the guard reads the entry's modifier;
- a journal entry's modifiers end when it closes, and a revolution's inherited copy arrives with none, so the entry's
  pulse re-applies it (the guard already makes that safe), and `je_immediate_reset_audit` checks the entry's `immediate`;
- a save from before keeps the country's copy, which an old-save repair removes once the entry carries its own.

`nuclear_power` doesn't enter the registry: on the entry, it isn't a country modifier.

## 7. Phases

1. **The tab and the hiding**: §§ 2–4, the Colonial Empire tab's move, and Nuclear Power's (§ 6).
2. **Wealth Concentration in the state view** (§ 5).
3. **The Judiciary's rows**, in whichever of this and the Judiciary's phase 1 lands second: Judicial Independence's
   row; `te_judicial_independence`, `te_jud_votes_legitimacy`, `te_jud_unelected_authority` and
   `te_jud_algorithmic_capture` into the registry (Governance); `te_jud_court_overhaul` into `STAYS` (timed).
4. **Later**, as systems add standing modifiers: a registry line each. A later version could show the viewed country.

## 8. Engine facts to verify

| Fact | Check |
|---|---|
| `00_te_country_panel_information.gui`'s type replaces vanilla's | Play-test: the hidden modifiers are gone from the Information tab, and nothing else in it changed. Fallback: the whole-file replacement (§ 3) |
| A timed modifier found by name in `GetPlayer.GetTimedModifiers` renders its scaled tooltip inside the tab | Play-test: Wealth Concentration's "what it gives now" matches the modifier's tooltip. Fallback: a script-value line per effect |
| `GetValueWithBreakdownFor` lists every source of the override sum | Play-test: the hover lists the laws, institutions and the decaying penalty. The recipe is documented; the covert panel uses it for hovers only, so a failure loses a tooltip, not a number |
| A template can carry a generated `visible` expression | Precedent: the window's own selection templates (`te_systems_window_*_selected`) |

## 9. Questions for the owner

1. **Permanent event outcomes.** A few events grant a modifier with no duration. By § 1 they go to the tab, in the
   section of the system that granted them. Or keep them in the list as event outcomes?
2. **The space race's colonies**: hidden, since the Space Race tab's Our Colonies lists them (§ 1)?
3. **Section order**: Governance, Society, Economy, Science and Space, International?
