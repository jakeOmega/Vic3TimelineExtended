# The Nation tab: the country's standing scores in one place — design

## Context

The mod keeps a growing number of national scores and dials, and a player meets them in three scattered forms:

- **Scaled modifiers in the country panel's modifier list.** Script re-applies them every month or year with a
  multiplier (Wealth Concentration's `inh_great_fortunes`, the Algorithmic Mandate, construction cost scaling). They
  never expire, so they sit in the Information tab's "MODIFIERS" list beside the event outcomes and timed penalties a
  player looks there for, and a row such as "Great Family Fortunes" means little without the score behind it.
- **Modifier sums with no display at all.** Legislative Override Capacity has about 40 sources (laws, institutions,
  technologies, principles, a decaying penalty) and decides which Forceful Legislation options appear and whether the
  tax code's Force Through is open, but a player sees it only in event tooltips and its concept.
- **Variables shown only in a concept's description**, such as Wealth Concentration's "Now 62, heading for 68".

The Judiciary (spec `2026-10-17-judiciary-design.md`, PR #1016) adds a score and four more scaled modifiers, and its
§ 13 hands this tab off. The state panel already solves half of the problem for states: it hides the mod's bookkeeping
modifiers from its rows by name (`gui_modding_guide.md` gotcha #40, `test_hidden_state_modifiers.py`). Countries have
no equivalent.

**What the mod applies today (inventory, 2026-10-17).** 367 static modifiers with country-level fields are added
without a duration somewhere in script, 67 of them with a multiplier. They fall into four kinds:

1. **Standing scores and dials of the country**: what this tab is for (§ 1).
2. **A system's own modifiers, where the system has a panel**: the UN (`un_*`), Banking, covert operations, the Seabed,
   the Space Race (`te_orbital_debris`), Cultural Hegemony, the tax code's group reactions. Their panels own them.
3. **Money carriers**: `country_expenses_add` and income lines with a `country_te_budget_*` twin (UN dues, seabed fees,
   station upkeep, the pension bill), which the budget panel itemizes (§ 1.3).
4. **Event outcomes and narrative modifiers**, which belong in the list.

## Decisions (owner, 2026-10-17)

| Question | Decision |
|---|---|
| Where | A tab of its own in the Timeline Extended window, dedicated to the country's standing modifiers, so that Judicial Independence, Legislative Override Capacity and their like can be seen and understood in one place |
| The country panel | Its modifier section hides what the tab shows, as the state panel hides its bookkeeping modifiers |
| A spec of its own | Yes: cross-cutting, so not part of the Judiciary |

## 1. What belongs on the tab

**The rule.** A row is a national score or dial that:

1. script keeps current (a pulse refreshes it, or it is a modifier sum the engine keeps),
2. says something about the country as a whole rather than one system's state, and
3. no system panel already shows.

The modifiers that carry it are hidden from the country panel's list. A **timed consequence with a duration** (Forceful
Legislation's decaying penalty, the Judiciary's Court Overhaul) is not a standing score: it stays in the list, where a
player looks for what just happened to them.

### 1.1 Phase 1 rows (what exists on `main`)

| Section | Row | Reads | Hidden from the list |
|---|---|---|---|
| Governance | Legislative Override Capacity | the sum of `country_legislative_override_capacity_add` | nothing: the dial has no modifier of its own |
| Governance | Algorithmic Mandate (only under Algorithmic Governance) | `algorithmic_mandate_value` | `algorithmic_mandate` |
| Society | Wealth Concentration | `te_inh_concentration_display`, `te_inh_concentration_target` | `inh_great_fortunes`, `inh_dispersed_wealth` |
| Economy | Construction Cost | `var:prior_construction_scaling`, the multiplier the yearly pulse applied (either rule's branch) | `construction_cost_scaling`, `construction_cost_scaling_direct` |
| Economy | Private Construction (only while excess private construction or Overinvestment is in force) | `var:too_much_private_construction_cached` | `too_much_private_construction`, `overinvestment_modifier` |

### 1.2 Rows the Judiciary adds

When the Judiciary's phase 1 lands, whichever of the two merges second adds them:

- **Governance:** Judicial Independence.
- **Hidden:** `te_judicial_independence`, `te_jud_votes_legitimacy`, `te_jud_unelected_authority`,
  `te_jud_algorithmic_capture`.
- `te_jud_court_overhaul` stays in the list (a timed consequence).

### 1.3 Candidates the owner decides (§ 7)

- **Credit Standing**, the structural premium's dial (`country_credit_standing_add`). The Banking tab shows it, but
  only while the banking cycle's journal entry runs; a row here would show it always, with the breakdown.
- **The armed forces' standing from training** (`te_officer_academies_standing`,
  `te_political_commissars_indoctrination`).
- **The private share of construction** (`te_construction_market_private_share_modifier`), under the construction
  market rule.
- **Money carriers** (kind 3): hidden from the list with no row, since the budget panel's breakdown already itemizes
  each one, or left as they are.

## 2. The tab

- **Name (proposal): "Nation".** Short, and it reads as the country's own state beside the systems' tabs.
  Alternatives: "Governance" (but Wealth Concentration and construction cost aren't governance), "State of the
  Nation".
- **Placement:** the second slot of the Seabed strip (`gui/te_systems_window.gui`). Three tabs already share the
  first strip at about 160 each, and a fourth there would leave 115. The strip shows whenever either of its tabs is on
  it.
- **Always open, never greyed.** The tab has no journal entry and no game rule, so it is the exception to style rule
  9's "greyed until the system's journal entry is active"; the file says so where the gate would be. The launcher's
  gate (`te_window_launcher_sgui`) gains it, so the window is reachable with all four system rules off.
- **Selection:** always open and last in precedence, so the window still opens on a system tab unless the player last
  chose Nation. `test_te_systems_window.py`'s case-by-case check of the selection templates grows to five tabs.
- **The player's own country only**, read through `GetPlayer` (observer mode shows nothing, as the window's other gates
  do).

### 2.1 Layout (`docs/guides/gui_style_guide.md`)

- A fixed 520 root (rule 8).
- **Overview**, always shown: a grid of reading boxes, two to a row (rule 4, the Banking overview's
  `te_banking_ov_cell`). Each box is a caption, a word and a figure: Override Capacity (the Forceful Legislation tier
  open, e.g. "Push decisively", and the value), Wealth Concentration ("62 → 68"), Construction Cost ("+35%"), then
  Judicial Independence once it exists.
- **Governance, Society, Economy**, open by default (rule 1), each row "Label: value" (rule 3) at 17 with subheadings at
  20 (the 2026-10-17 type sizes, in the tab's own templates):
  - A 0–100 score is a **bar heading for its target**, the translucent segment showing where it is going, green when
    the change is good for the player (rule 5).
  - The value's **hover is the engine's breakdown** (`GetPlayer.GetModifier.GetValueWithBreakdownFor('<type>')`,
    `gui_modding_guide.md` § Modifier Access in GUI) for a dial, or the concept's explanation for a score.
  - **"What it gives now"** is the hidden modifier's own tooltip. The row finds the modifier in
    `GetPlayer.GetTimedModifiers` by name (gotcha #40's `EqualTo_string(TimedModifier.GetName, Localize('<key>'))`) and
    shows `TimedModifier.GetTooltip`, so the engine renders the scaled effects (§ 6).
- **"How the Nation Works"**, collapsed (rule 1), a subheading per row: what moves it, and what it does.

### 2.2 Phase 1 rows in detail

- **Legislative Override Capacity: 2.5.** A bar from −6 to +8 with thin threshold lines at 0, 2 and 4 (rule 5), each
  with its own hover: at 0 the Forceful Legislation event appears, at 2 its decisive option and the tax code's Force
  Through, at 4 its strongest. Under the bar, "Forceful Legislation: Push decisively", naming the strongest option
  open, or "Not offered" below 0. Hover: every source with its contribution, the decaying penalty among them. This is
  the row the tab is most needed for.
- **Algorithmic Mandate: +12 legitimacy**, under Algorithmic Governance only. Hover: how the mandate follows living
  standards against expectations.
- **Wealth Concentration: 62 → 68**, as a bar. Hover: the concept's explanation; "what it gives now" is Great Family
  Fortunes' or Dispersed Wealth's tooltip.
- **Construction Cost: +35%.** Hover: GDP per capita against the reference, and the curve's floor and ceiling.
- **Private Construction**, while either modifier is in force: the per-project cap it raises and the construction
  efficiency it costs, with "Overinvestment" when that is in force. Hover: why it exists (an investment pool the
  private queue can't spend) and how it ends.

## 3. Hiding them from the country panel

- **Where the list is.** Vanilla's `gui/country_panel.gui` (1.14, from the owner's upload). The Information tab's type
  `country_panel_information_content` (lines 379–1412, about 1,030 lines) ends with a "MODIFIERS" `default_header` and
  a `flowcontainer` over `Country.GetTimedModifiers`: icon, name, remaining duration, the modifier's tooltip on hover.
  The panel's Modifiers tab (`modifier_list`) is a different view, the summed modifier types with their breakdowns.
  It is left alone: the Judiciary's tooltip lines belong there.
- **How (proposal): redefine that one type, not the file.** A mod file `gui/00_te_country_panel_information.gui`
  redefines `country_panel_information_content` (gotcha #30: the Community Mod Framework redefines 29 vanilla types
  this way, and doesn't touch this one). Which of two definitions wins is unread, but CMF's `00_` naming wins under both
  orders the guide leaves open: first loaded alphabetically, or mods after vanilla with the last definition winning.
  The type is copied from vanilla verbatim, with only the timed-modifier block changed and marked `# TE:`, as
  `te_tradition_of_free_elections.txt` marks its changes:
  - each item `visible = "[Not(Or(EqualTo_string(TimedModifier.GetName, Localize('<key>')), …))]"`, two-argument
    `Or`s, with `ignoreinvisible = yes` on the flowcontainer;
  - the header and the flowcontainer shown on
    `GreaterThan_int32(GetDataModelSize(Country.GetTimedModifiers), FixedPointToInt(Country.MakeScope.ScriptValue('gui_country_hidden_modifier_count')))`,
    the state panel's form (`states_panel.gui`), so the header doesn't stand over an empty list;
  - `gui_country_hidden_modifier_count`, a country script value with one `has_modifier` term per hidden modifier.
- **Every country's panel, the player's and the AI's.** The Information tab shows any country, and one filter serves all. An AI
  country's hidden standing then shows only in breakdowns until the tab can show another country (§ 5).
- **Hidden isn't gone.** Breakdown tooltips (legitimacy's, the Modifiers tab's) still name each source. The hidden
  modifiers keep their own icons, since the tab may draw them (the Grand Monument card's precedent in gotcha #40),
  rather than the state bookkeeping's blank `modifier_system.dds`.
- **Vanilla drift.** The copied type joins the GUI overrides the vanilla patch runbook 3-way merges on every patch
  (`docs/guides/vanilla_patch_runbook.md`, `gui_modding_guide.md` § "GUI 3-way merge across vanilla patches"), with the
  vanilla version it was copied from recorded in the file's header.
- **The fallback**, if the redefinition loses to vanilla's: replace the whole `country_panel.gui` (4,420 lines), as the
  mod already replaces `states_panel.gui`.

## 4. Tests

- **`test_hidden_country_modifiers.py`**, the country twin of `test_hidden_state_modifiers.py`. Three sets must agree,
  so adding a row means a row, a filter entry and a count term or the test fails:
  - the name filter in the redefined type;
  - the terms of `gui_country_hidden_modifier_count`;
  - a table in the test of each row's hidden modifiers.

  It also fails on a modifier hidden with no row, and on any icon comparison (gotcha #40).
- **The redefined type is vanilla's but for the `# TE:` block.** CI has no vanilla GUI, so the test diffs the file
  against a committed copy of vanilla's type taken when it was copied; the runbook refreshes that copy on a patch.
- **`test_te_systems_window.py`**: the fifth tab in the selection cases, the strip, the launcher gate, and the tab's
  composition (overview first, the three sections, How It Works last and collapsed).
- **The tab's own layout test** (the `*_layout.py` pattern): each row's value, hover and "what it gives now" read the
  key the row table names, and widths fit at the 17 and 20 sizes (`WidthBudgetTest`'s method).

## 5. Phases

1. **The tab and the hiding**: § 1.1's rows, § 3, § 4. It doesn't wait on the Judiciary.
2. **The Judiciary's rows** (§ 1.2), in whichever of the two lands second.
3. **Later rows**, as systems add standing scores, each by the § 1 rule and the test's checklist. A later version could
   show the viewed country's scores, for any country the player opens; that's out of scope here.

## 6. Engine facts to verify

| Fact | Check |
|---|---|
| `00_te_country_panel_information.gui`'s type replaces vanilla's | Play-test: the hidden modifiers are gone from the Information tab, and nothing else in it changed. Fallback: the whole-file replacement (§ 3) |
| A timed modifier found by name in `GetPlayer.GetTimedModifiers` renders its scaled tooltip inside the tab | Play-test: Wealth Concentration's "what it gives now" matches the modifier's tooltip. Fallback: a script-value line per effect |
| `GetValueWithBreakdownFor` lists every source of the override sum | Play-test: the hover lists the laws, institutions and the decaying penalty. The recipe is documented; the covert panel uses it for hovers only, so a failure loses a tooltip, not a number |

## 7. Questions for the owner

1. **The tab's name**: "Nation", or another?
2. **Phase 1 rows** (§ 1.1): these five, or more or fewer?
3. **Credit Standing** (§ 1.3): a row here too, though the Banking tab shows it while its journal entry runs?
4. **Money carriers** (§ 1.3): hide them from the list with no row (the budget panel itemizes them), or leave them?
5. **The armed forces' training standing and the private construction share** (§ 1.3): rows, or leave them where
   they are?
