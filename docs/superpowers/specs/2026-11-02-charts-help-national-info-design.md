# System panels: full-screen charts, Help pages and other countries' panels (2026-11-02)

> **Status: scoping, nothing built.** Checked against `main` at `e3aecaa`, after the
> wide-mode work ([spec](2026-11-02-te-window-wide-mode-design.md), #1320, built in
> #1327–#1337). Counts below come from regex sweeps of `gui/` and `localization/` on
> 2026-11-02: they size the work, and are not exact. Several pieces rest on what only the
> game can show (§ 9). The implementation plan is
> [plans/2026-11-02-charts-help-national-info.md](../plans/2026-11-02-charts-help-national-info.md);
> writing it changed §§ 4.3, 5.2, 6.6, 7.1 and 10, as its self-review lists.

## 1. The request

The owner, 2026-11-02, extending the wide-mode work:
- **Charts:** open any graph in a full-screen window, to see it better.
- **Help:** move each system's explanation to a Help page, opened with a "?" button.
- **Other countries:** open the panels that hold public but country-specific information
  for another country, without the plots where no history is kept. Examples given: a
  rival's banking boom or crash and the interventions it uses, its tax code, its
  demographics (already possible through the Census Data button), its grand monuments,
  its colonial policy and its seabed mining.
- **One host to consider, among others:** rename the Census Data button to something
  like "National Info" and make each of these tabs a tab of that window, as Demographics
  already is, with every control shown only for the player's own country.

## 2. Decided by the owner (2026-11-02)

- **Public:** Banking's cycle phase (boom or crash) and its interventions, the tax code,
  demographics, grand monuments, colonial policy and seabed mining. § 6.4 proposes the
  other systems.
- **Plots may be left out** for a country whose history isn't stored.
- **The Census Data window is a candidate host**, to be weighed against others (§ 6.1).
- **Not shown for another country (owner, on this spec's first draft):**
  - **Global Warming.** The one thing about another country a player acts on is who emits
    most, so as to make treaties that cut their CO2, and Top Emitters already shows that.
  - **The United Nations.** Most of its panel shows the same world to every country.
    What is the country's own (membership, standing, dues arrears) becomes lines on the
    Nation tab instead (§ 6.4).

## 3. What exists today

### 3.1 Charts

- **33 history charts**, all instances of `te_history_chart`
  (`gui/journal_entry_widgets/te_history_chart.gui:336`). Each is written inline in its
  system's section type with blockoverrides; none is a type of its own:
  - Banking: 8 (`banking_history_widget.gui`);
  - Strategic Reserve: 8, one per good, in the inventory rows;
  - Demographics: 8, annual (`te_demographics_widgets.gui:3294`);
  - Colonial Empire, Global Warming, the UN and Nuclear Weapons: 2 each;
  - Cultural Hegemony: 1, an annual stacked chart (`cultural_hegemony_widget.gui:2473`).
- **The monthly charts** draw a 480 px plot, which divides 240 / 60 / 12 months into 2 / 8 /
  40 px bars, 84 px tall in a 496 × 96 frame
  ([history_charts.md](../../systems/mod_systems/history_charts.md)). **The annual charts**
  (Cultural Hegemony, Demographics) draw 400 px for 100 / 20 / 5 years. The range is a GUI
  variable that all charts of a kind share (`te_hist_range`, `ch_model_hist_range`,
  `te_demog_hist_range`).
- **Fixed in pixels:**
  - the bar height, the title and legend widths (484), the empty state's (420);
  - the range buttons, the marker pips and the axis labels;
  - the two hand-placed zero lines of the policy-rate and inflation charts
    (`banking_history_widget.gui:451`, `:585`: 6 + 0.2 × 84 and 6 + 0.25 × 84).
- **Whose history:**
  - The monthly store records players and major powers, the AI included
    (`te_history_country_is_tracked`).
  - The Demographics history records the same countries. Its census runs for every country.
  - Cultural Hegemony's history is global.
  - The Tax Code history rows are text, not a chart. They are recorded for every country
    under the full code (`te_tax_schedule_effects.txt:224`), and only the player's are shown.
- **Nothing enlarges a chart.** The wide frame lays sections out in 520 columns and the
  charts stay at 496.

### 3.2 The "How X Works" sections

- **What there is.** Style guide rule 1 puts each system's explanation in one collapsed
  section at the bottom. There are 18 of them, 72 to 187 GUI lines each, with 2,000 to
  18,400 characters of loc. The long ones:
  - Banking: 18.4k characters, 10 topics;
  - Demographics: 12.5k, 12 topics, plus the state subtab's own 10.5k, mostly the same keys;
  - Grand Monuments: 10.0k;
  - Tax Code and Covert Warfare: 9.4k each;
  - the UN: 9.0k.
- **Where they appear.** Each sits in up to four hosts: the journal entry, the vanilla
  panel's tab, the Timeline Extended window narrow, and its wide composer. Each has its own
  collapse flag (`banking_dash_how_open`, `un_how_open`, …).
- **No buttons, and no live country figures.** The few live reads are:
  - tuning constants, read through `JournalEntry.GetCountry` (Colonial Empire, Covert
    Warfare) or `GetPlayer` (Seabed, Tax Code);
  - topic gates: Banking's monetary topics (`banking_mon_system_shown`), the Space Race's
    colony topics (`sr_disp_colonies_*`), the Light code's section.
- **Explanations that stay.** Other explanatory sections carry live data and stay in the
  panels: Nation's Where These Come From, the UN's Why Authority Is Moving, Colonial
  Empire's Why Stability Is Moving, and each chart's legend.
- **Nothing to build on.** There is no "?" button anywhere in the mod. Vanilla's journal
  entries have TELL_ME_HOW / TELL_ME_WHY tutorial hooks (`gui/journal_entry.gui:941`),
  which the mod doesn't use.

### 3.3 Hosts, and whose country they read

- **The GUI can't read another country's journal entry** (`gui_modding_guide.md`
  gotcha #35). `Country.GetJournalEntry` silently fell back to the player's own entry in
  game. What works is a `Country` datacontext, reading the country's variables, script
  values and scripted GUIs.
  - **Entry modifiers stay reachable.** A modifier an entry holds can still be read for any
    country from script (`je:<entry> ?= { has_modifier … }`, as the Market panel's Climate
    tab reads another market's Mitigation Policies, `global_warming_triggers.txt:44`).
- **Nothing hands a scripted widget a country.** No global data function turns a tag or a
  string into a `Country`. The 1.15 data types have `GetPlayer`,
  `GetPlayerJournalEntry` and `GetMapPerspectiveCountry`, and `GetVariableSystem` holds
  only strings. So the Timeline Extended window can show another country only from a
  variable saved in the game (§ 6.1, B).
- **The Census Data window** (`gui/pop_browser_panel.gui`, an override of vanilla's
  `fullscreen_block_window`):
  - **It already carries a country:** `datacontext = "[PopBrowserPanel.GetCountry]"`.
  - **Vanilla opens it for any country:** for another country from the foot of its
    Politics tab (`InformationPanelBar.OpenPopBrowserPanel( Country.Self )`,
    `country_politics_panel.gui:688–696`, a vanilla file this repository doesn't hold), and
    for the player from the Population panel's footer (`gui/pops_overview.gui:582–590`).
  - **Both buttons and the window's title are one key, `POP_BROWSER`:** "Census Data", with
    the country's adjective added for another country ("French Census Data").
  - **It already shows another country's Demographics.** The mod's strip (Pops,
    Demographics) does it, with that country's figures and no buttons (`Country.IsLocalPlayer`
    gates them), as the play-test confirmed (`docs/testing/demographics-playtest.md`,
    "Another country").
- **The TE window and the Census window are never open together.** A vanilla panel opening
  closes the TE window, and the TE window opening closes the side panels (its header in
  `gui/te_systems_window.gui`).
- **The popups root** (`gui/te_popups.gui`, on `layer = popups`) shows one `te_ui_popup` at a
  time on the client key `te_popup`. Each popup body reads the player through
  `GetPlayerJournalEntry`. It hasn't been seen in game yet (`gui_modding_guide.md`, "This
  mod's popups").

## 4. Full-screen charts

### 4.1 Options

| | What | For | Against |
|---|---|---|---|
| **A** | **A chart viewer**: a "⤢" button on each chart opens that chart alone in a full-screen popup, about 2.5× its width | every host, narrow or wide, the journal entry included; one chart at a time, as large as the screen allows | each chart has to exist at two sizes (§ 4.3) |
| B | Charts in a full-width row across the wide layouts, above the columns | no popup | only in full screen; rewrites every wide layout; still one size |
| C | Nothing new: the wide frame already shows more at once | free | the charts stay 496 wide |

**Recommendation: A.**

### 4.2 The viewer

- **What it is.** A `te_ui_popup` holding one chart at a large size, with the same title,
  legend, range buttons, marker pips and bar hovers. Escape, the close button or a click
  outside closes it.
- **The range stays shared.** The viewer opens at the panel's range, and changing it
  changes both.
- **Size: one plot width, 1200, for every chart.** 1200 divides both the monthly counts
  (240 / 60 / 12 months, giving 5 / 20 / 100 px bars) and the annual ones (100 / 20 / 5
  years, giving 12 / 60 / 240 px).
  - Bars about 336 px tall (4×).
  - The two hand-placed zero lines are recomputed for the new height.
  - The popup comes to about 1,320 px wide (1,360 for the annual charts, whose axis labels
    take 48 more), which fits 1600 × 900 and up at UI scale 1, but not 1280-wide screens
    (open question 7).
- **Which charts.** The 33 history charts. Pies, dials and the population pyramid stay as
  they are: they read at their size, and none is a time series.
- **Later, not now:** year ticks along the bottom at the large size. Each sample stores
  `te_hist_y` / `te_hist_mo`, so a label can sit under each January.

### 4.3 One definition per chart, drawn at two sizes

The viewer needs each chart's blockoverrides (its datamodel, bar body, legend and tooltip)
a second time, at the viewer's size.
- **A shortcut that may fail.** The short way would be a named type per chart derived from
  `te_history_chart`, instanced at both sizes. But gotcha #37 is that shape failing: a
  chart's plot blocks in a type derived from `te_history_plot` drew nothing and logged
  nothing. Whether a type derived from `te_history_chart` itself draws is unknown.
- **Recommendation: a chart registry and a generator.**
  - **The generator.** `scripts/generators/gen_te_history_charts.py` holds each chart once,
    as its instance's text with each size a placeholder. It writes two wrapper types per
    chart, `te_hist_<id>` and `te_hist_<id>_large`: a plain `flowcontainer` holding the
    chart inline. That is the shape that draws today, since every history section is a type
    holding its charts inline. The sections stay hand-written and instance the small one.
  - **Kept manual.** It stays out of `POST_LOAD_REGENERATORS`, like `gen_te_systems_window.py`,
    with a `--check` its test runs.
  - **The cost.** The 33 hand-written instances move into the registry: the largest piece of
    the chart work, with no visible change.
  - **No diagnostic needed** (this paragraph once proposed trying a derived type in game).
    A wrapper is not a type derived from `te_history_chart`; it holds an instance, as the
    sections do.
- **Sizes are in axis units too.** The bars' thin caps and floors are written in the
  chart's units (`banking_history_widget.gui:354`, `:359`), so the large size scales them by
  the height ratio, or a cap 3 px tall today draws 13 px tall.

### 4.4 Where it opens, for whose country

- **The player's own charts.**
  - **Where it lives.** The viewer is a popup in `te_popups`, one body per chart, each
    shown on `te_popup = chart_<id>`. Its datacontext is the player: `GetPlayer` once the
    charts read `Country` (§ 6.3), `GetPlayerJournalEntry('<key>')` until then.
  - **From every host.** It opens from any host: a vanilla panel's tab, the journal entry,
    the TE window, and the National Info window for the player's own country.
- **Another country's charts** (§ 6).
  - **Where it lives.** The National Info window instances the same viewer at window level,
    outside its scroll area, under its own `Country`, shown on a second key, `te_ni_chart`.
  - **The button.** Each chart's "⤢" is two buttons in one slot: one shown for the player's
    country (it sets `te_popup`), one for another (it sets `te_ni_chart`). So no section
    needs to know which window it is in.
- **Closing.** Both keys are cleared when the window under them closes, so a stale key
  doesn't reopen the viewer next time.

## 5. Help pages

### 5.1 Options

| | What | For | Against |
|---|---|---|---|
| **A** | **A Help popup per system**: a "?" beside each tab's title opens "How X Works" in a popup | one place for the text, reached from every host; the panels get shorter; needs no country, so it works for another country's panel too | rests on the popups root's layer (§ 9, item 1) |
| B | An in-place help mode: the "?" swaps the tab's live sections for its explanation | no popup, works in every host | a 520 column; the player loses the live view while reading |
| C | A Help tab in the TE window, with a sub-strip of systems | findable in one place | not reachable from the vanilla panels' tabs or the journal; a sixteenth tab |
| D | Vanilla's tutorial lessons (TELL_ME_HOW / TELL_ME_WHY) | vanilla's own help | step-by-step tutorials with highlights, not reference pages; far more work |
| E | A game concept per topic, the "?" a tooltip | vanilla's mechanism | `long_tooltip_audit` caps a tooltip at 500 characters; Banking's text is 18,400 |

**Recommendation: A.** Concepts (E) stay what they are: the hover for a term in live text.

### 5.2 The Help popup

- **What moves.** Each "How X Works" section's content becomes a help body type,
  `te_<system>_help_body`. Its topics and subheadings are kept as they are. The 18 sections
  make 15 pages (below), and the Fossil Transition's inline How joins Global Warming's.
- **What stays: the section, as a link.** `te_<system>_sec_how` keeps its name and its
  place in every composer, shrunk to its header, which opens the page instead of
  expanding. So the composers, the wide layouts and their order tests are unchanged, and
  every host keeps it where it was: the journal entry, the state subtab, and the tabs with
  no header (Nation, Budget Breakdown).
- **The popup.** A `te_ui_popup` in `te_popups`, 640 × 820, titled with the section's own
  name ("How Banking Works"). It shows on `te_popup = help_<system>`. The text keeps the
  sections' own widths (480 to 520); a wider column would mean rewidening every textbox, so
  it waits for the play-test.
- **Data.** None, apart from the tuning constants and topic gates of § 3.2. A help body reads
  `GetPlayer` only, never `JournalEntry`, so a page needs no entry and opens whether or not
  the player holds one. A Help page opened from another country's panel describes the rules
  as they stand for the player. That is what a rule explanation should say.
- **The "?" button.**
  - **Where.** Right-aligned in each frame-based tab's header: a `te_help_button` added as a
    child of the body's `default_header`, vanilla's own shape for a button in a header
    (`states_panel_buildings.gui:180`). The Space Race milestones' headers get it through
    the window's generator. Hosts without a header have the link.
  - **Art.** A placeholder texture to begin with (style guide rule 10), vanilla's Vickypedia
    button, listed in the icons docs.
- **The names keep a `help` token,** so `gui_tree.how_named` still exempts their text from
  `long_tooltip_audit`'s 500-character cap.
- **What stays in the panels:**
  - the live explanations of § 3.2 (Where These Come From, Why Authority Is Moving, Why
    Stability Is Moving);
  - the chart legends;
  - every hover.
  - Only the "How X Works" sections move.
- **Space Race.** The panel's section and the colonies' second section become one help
  page, the colony topics gated as now. The nine milestone entries share it.
- **Demographics.** The country's and the state's sections are mostly the same keys, so one
  page, with the state topics under their own subheading.

### 5.3 The long pages

Banking's page is about 3,000 words. A single scrolling page is the first build. A topic
list down the left with one topic at a time would read better for the six longest pages, at
the cost of splitting each section into one block per topic with a client key for the chosen
one. Leave it until the play-test says the long pages read badly.

## 6. Other countries' panels

### 6.1 Where: options

| | Host | For | Against |
|---|---|---|---|
| **A** | **The Census Data window, renamed (say "National Info"), with a tab per public system**, as the owner suggested | carries the country for free (`PopBrowserPanel.GetCountry`); vanilla already opens it for any country; in the panel stack, so Back returns to the country panel and Escape works; full screen, already proven in game; Demographics there is the precedent for another country's figures with the controls hidden | a second full-screen host for the bodies the TE window shows (both generated from one registry, § 7.3); a vanilla override a patch may touch (its base is already committed and tested) |
| B | The TE window in a "viewing" mode | one host, both widths | a button saves the viewed country to a game variable on every click (a synced command, saved with the game); the window isn't in the panel stack, so Back can't return to the country panel; a stored country can die |
| C | A new tab in the vanilla country panel | where players look for another country | side-panel width only; a full-file override of `country_panel.gui`; a strip of systems inside a tab (style guide rule 9 allows one strip per window) |
| D | A one-line summary per system on the country panel's Information tab, nothing more | cheap; where players look | no panels, no charts |

**Recommendation: A**, with D's Information-tab line as a second way in (§ 6.2).

### 6.2 National Info: the window

- **Its name.** Replacing `POP_BROWSER` in
  `localization/english/replace/timeline_extended_override_l_english.yml`, keeping its
  adjective splice, renames the window's title and both buttons in one line ("French
  National Info"). The alternative gives only the foreign button a label of its own: an
  override of `country_politics_panel.gui`, with its vanilla base (the owner's copy)
  committed as `test_fixtures/vanilla_gui/country_politics_panel.gui` (open question 2).
  The name itself is open question 1.
- **Ways in:**
  1. vanilla's button on another country's Politics tab;
  2. the Population panel's button, for the player;
  3. a goto on the line the mod already draws on the country panel's Information tab
     (`te_nation_panel_line`, `gui/00_te_country_panel_information.gui:1058`, generated by
     `gen_nation_tab.py`), which today shows its goto only for the player.
     - For another country it opens National Info on its Nation tab
       (`OpenPopBrowserPanel( Country.Self )` and the window's tab key).
     - This puts the way in on the tab players see first.
- **The strip.** Today's two tabs (Pops, Demographics) become up to three strips of five,
  side by side, as in the TE window's full-screen frame. The window shows each tab's wide
  composer (`te_<system>_wide_sections`, built in #1333–#1335) under its `Country`.
  - **Which tabs:** Pops and Demographics, then the systems § 6.4 makes public: Nation,
    Banking, Tax Code, Grand Monuments, Colonial Empire, Seabed, Cultural Hegemony, the
    Space Race and Nuclear Weapons. That is 11 tabs: two strips of five and a third of one.
  - **Generated, not hand-written.** The strip and its mounts are generated from the TABS
    registry (§ 7.3), and the hand-written two-tab strip moves there.
  - **The shown tab:** one client key, `te_ni_tab` (Pops when unset), replacing
    `te_pop_browser_demog`.
  - **A grayed tab** (the system isn't running for that country) says so in one line, "Not
    running in France": the player's checklist ("You have a coastal state") doesn't fit.
- **The player's own country** (open question 3). Recommended: the same window with the
  player's controls, since every control is gated on `Country.IsLocalPlayer` anyway (§ 6.5).
  - **Two mounts per tab.** Each tab gets two generated mounts: one for the player's
    country, under a `GetPlayerJournalEntry` datacontext so its entry-only parts work, and
    one for any other country, with no entry.
  - **One body.** Both mount the same body.

### 6.3 Binding every body to a Country

This is the main cost of the feature, and any host needs it.

- **The rule.**
  - **Read `Country`.** Every section reads the shown country as `Country`, and its mount
    supplies it:
    - the vanilla hosts and the TE window: `datacontext = "[JournalEntry.GetCountry]"`
      under the entry, or `[GetPlayer]`;
    - National Info: `[PopBrowserPanel.GetCountry]`.
  - **No journal entry for another country.** National Info's mounts for another country
    have no `JournalEntry` in context. So a body may read `JournalEntry` only inside
    own-country parts (§ 6.5), and a test holds it to that (§ 7.1).
- **Mostly mechanical.** `JournalEntry.GetCountry.X` becomes `Country.X`. The mod's lists
  hold states and script containers, not countries, and `Country` resolves to the nearest
  Country context (vanilla's `pop_browser_panel.gui:895` relies on that).
- **The one real case of a row's country shadowing the shown one** is Banking's bloc-leader
  row (`banking_dashboard_widget.gui:2793`): its `datacontext` is the bloc's leader, while
  its `visible` and a loc key read the panel's own country.
- **Entry-only parts** have no Country form:
  - the composers' `JournalEntry.IsActive` gates;
  - the scripted bars (`te_je_scripted_bars`);
  - Colonial Empire's stability bar;
  - Nuclear Weapons' goal bar;
  - the Open Journal Entry button.
  
  Each either goes into an own-country part or reads the variable behind it:
  - Banking's four bars are written from country variables;
  - Colonial stability has `colonial_empire_live_bar`, which reads the bar through `je:`
    and works from a foreign `Country`.
- **`GetPlayer` reads**, in hand-written GUI and generated files alike. The generated ones
  change in their generators:
  - Tax Code: about 560, plus about 3,500 in `te_tax_generated_rows.gui`;
  - Seabed: 111;
  - Nation: 31, plus 142 generated;
  - Budget Breakdown: 65, generated.
- **The gates.** Every tab gate roots on `GetPlayer` (`_root()` in `gen_te_systems_window.py`),
  so the generator takes the root as a parameter.
- **Loc that reads the entry or the player** renders in the widget's context and is
  rewritten too. In the systems § 6.4 makes public:
  - about 850 keys read `JournalEntry.` (the Space Race 417, Grand Monuments 145, Nuclear
    Weapons 97, Banking 93, Cultural Hegemony 56, Colonial Empire 40);
  - about 530 read `GetPlayer` (Tax Code 228, Nation 160, Seabed 65, …).
  - A key the journal entry's own text also uses (its status or description, where only
    `JournalEntry` is in context) must be split, not rewritten.

| Tab | `JournalEntry.GetCountry` | `GetPlayer` | Controls (Execute) | Notes |
|---|---|---|---|---|
| Nation | 0 | 31 + 142 gen | 0 | the modifier list reads `GetPlayer.GetTimedModifiers` (`te_nation_tab.gui:164`) |
| Space Race | 363 + about 22,000 gen | 17 | 19 + about 4,800 gen | the generated site and fleet rows (`gen_solar_sites.py`, `gen_space_fleets.py`); the rival estimates are worked out from the viewer's side |
| Grand Monuments | 149 | 35 | 16 | |
| Colonial Empire | 142 | 8 | 11 | the stability bar (above) |
| Seabed | 0 | 111 | 2 types, many rows | the claimant rankings are player-only lists; the own row's `flag_context` is already a block |
| Banking | 303 | 17 | 14, all in Monetary Policy | the one shadowing case; 72 "you" keys |
| Tax Code | 0 | about 560 + about 3,300 gen | 37 | the interest-group cards iterate `AccessPlayer.AccessAllInterestGroups` |
| Budget Breakdown | 0 | 65 gen | 0 | `Predict*` getters untested on a foreign country |
| Strategic Reserve | 254 | 1 | 25 | |
| Global Warming | 40 | 1 | 2, already disabled off the player | not shown (§ 2): not rebound |
| Demographics | (done) | 22 | 2, already hidden | already reads `Country` |
| Cultural Hegemony | 155 | 3 | 10 | |
| United Nations | 1,895 | 1 | 212 (delegations 122, proposals 68, missions 16) | not shown (§ 2): not rebound. Its three lines on Nation read country variables |
| Nuclear Weapons | 272 | 5 | 40 | the goal bar |
| Covert Warfare | 97 | 3 | 6 | private (§ 6.4): not rebound |

In the systems to be shown, that comes to about 1,400 hand-written `JournalEntry.GetCountry`
reads. The UN alone held 1,895, so leaving it out halves the hand-written work.

### 6.4 What each system shows another country

The owner's six are decided, and so are Global Warming and the UN (§ 2). The rest are
proposals, from what each system stores and what is public in real-world terms.

| System | Another country sees | Hidden |
|---|---|---|
| **Banking** (owner) | the cycle phase, momentum and bubble (boom or crash), policy rate, inflation and exchange rate, the interventions in force (entry modifiers, read through script: `market_triggers.txt:81`), the history (§ 6.6) | every control; r\* and the forecast error, already hidden from the owner |
| **Tax Code** (owner) | the enacted code, the approved schedule, the bill under debate, the history rows (recorded for every country) | the draft (`te_tax_dr_*`), the offers and promises (`te_tax_off_*`), the workbench, the interest-group bargaining |
| **Demographics** (owner) | as today | as today: the controls, and the 20-year pyramid outline (players only) |
| **Grand Monuments** (owner) | monuments built and under way, the national effects, trophies, works abroad, archaeology | the open opportunity and the interest groups' ledgers (open question 5) |
| **Colonial Empire** (owner) | holdings, stability, the programs (its colonial policy), pressure, the history | controls |
| **Seabed** (owner) | its policy, basins, mines and claims (the claimant rows show these already) | controls |
| Nation | the national modifiers. The country panel's Information tab hides them for another country today and shows a count (`00_te_country_panel_information.gui:1013`), so this reverses a choice. Also the UN lines: membership, standing and dues arrears, from country variables (`un_standing`, the membership mirrors `<modifier>_on`), so the UN needs no rebinding | — |
| **Global Warming** (owner) | not shown. Top Emitters already names the five largest emitters, the countries a treaty would target, and the Climate tab shows another market's policies | everything |
| Cultural Hegemony | score, rank, its programs and where its pull comes from (the breakdown) | controls. The board and the models are the same world for every country |
| **United Nations** (owner) | not a tab: the lines on Nation above. The Assembly, missions, mandates, the archive and the authority history are the same for every country, and the case against a country already shows in the chamber when a motion names it | everything else |
| Space Race | the milestones reached, program icons, colonies, and a progress band (`sr_fuzz_<m>`, as the Rivals rows show) | exact progress, funding, approach, setbacks, fleets |
| Nuclear Weapons | the public estimate (`nd_believed_stockpile`, `nd_display_public_estimate`), crises, guarantees; nothing before a first test | the true stockpile, progress, funding, readiness, custody |
| Strategic Reserve | private in this work. At most later: that a reserve exists, its hub and the goods it covers | stocks, rates and policies (six of its goods are military) |
| Budget Breakdown | private in this work: whether the budget's `Predict*` getters work for another country is untested, and its Covert Actions and Nuclear Program rows would leak a secret (nuclear upkeep scales with the stockpile) | everything |
| Covert Warfare | private: the design's rule is that nothing tells a country of operations it hasn't caught (`covert_warfare.md`) | everything |

A partly public system needs a little new content, not just hiding: the Space Race's band in
place of exact progress, and Nuclear Weapons' estimate in place of the true count.

### 6.5 Controls

- **Hidden, not grayed.** For another country, every control is hidden, as in the
  Demographics precedent ("no pension buttons or their gray notes"). That includes buttons,
  steppers, pickers, the popups' openers and Open Journal Entry.
- **One guard.** Controls, entry-only parts and private sections sit under one template,
  `te_own_country_only` (`visible = "[Country.IsLocalPlayer]"`), on a wrapper where the
  widget has its own `visible` (one `visible` per widget). A test finds any `Execute`
  `onclick` in a body outside it (§ 7.2).
- **Another human's country** in multiplayer is read-only too (`IsLocalPlayer` is false).
  **An observer** gets read-only views of every country. With no `GetPlayer` read left in a
  body, it logs no null-country errors (#1325).

### 6.6 History for another country

- **What it shows.**
  - A major power's monthly charts draw.
  - A minor's are empty. The empty state says why ("No history is kept below major power"),
    as the Demographics charts already do, rather than "nothing recorded yet".
  - Cultural Hegemony's chart is global, so it is the same for every country.
- **The chart type defaults to the entry.** `te_history_chart`'s `sample_datamodel`,
  `sample_visible` and `empty_visible` blocks read `JournalEntry.GetCountry`
  (`te_history_chart.gui:253`, `:270`, `:423`). The list reads become `Country`.
  `sample_visible` reads the month index, the same for every country, so it reads the
  player.
- **Found in passing: a scrambled history becomes visible.** A store that stops recording
  is already sorted, since every eviction re-sorts (`te_history_effects.txt:125`). The
  stores out of order are ones scrambled before that sort existed and untouched since: the
  newest months first, then the oldest.
  - `history_charts.md` calls that unreachable rather than broken, since "the charts live on
    that country's own journal entry". Another country's view makes it reachable.
  - The fix: an old-save repair that sorts each store once
    (`common/on_actions/te_old_save_repairs.txt`). `check_save_history_order.py` then fails
    on a `frozen` store out of order rather than labeling it, and scans Demographics'
    `te_dg_hist`, which it skips today.

### 6.7 Display data only players get

Some lists in the systems to be shown are written for players only:
- Colonial Empire's blocs, subject capitals and great-power rows
  (`colonial_empire_display_effects.txt:213`);
- Cultural Hegemony's leader flags and board (`cultural_hegemony_effects.txt:43`, `:1029`);
- the Space Race's rival estimates and powers list (`space_race_on_actions.txt:78`, `:157`);
- the seabed claimant rankings.

Most of them describe the world, not the country. For those, the foreign view reads the
player's copy (`GetPlayer`, under a comment saying why), which is the same world. The
viewer-relative ones (the Space Race's rival estimates) are hidden. Each system's PR makes the
call per list.

### 6.8 Wording

- **The house voice is "our" and "we",** in about 410 of the keys the shown systems use,
  against about 100 that say "you" (72 of them Banking's). Read for another country, "Our arsenal" credits the player with
  France's figures.
- **Recommended:**
  - neutral labels where a line is a label ("Arsenal: 120");
  - a `SelectLocalization` on `Country.IsLocalPlayer` where a sentence needs its subject,
    as Global Warming does;
  - each system's PR covers its own keys.
- The alternative, accepting "our" as the panel's voice, is free but reads wrong (open
  question 6).

## 7. Standardization

### 7.1 A body reads the country its mount supplies: **do it**

One rule for every body: `Country` is the shown country. `JournalEntry` and `GetPlayer`
appear only inside `te_own_country_only`, or under a comment naming a world list (§ 6.7). It
is a test in `test_te_system_tab_bodies.py`, run over each body's type closure. CI runs it,
so a `check_gui_lint.py` warning would only repeat it.

### 7.2 One own-country guard: **do it**

`te_own_country_only`, a template in `gui/te_system_tab_widgets.gui`, with the test of § 6.5.
Without it, each system's PR would guard its controls its own way, as the eight journal-entry
mounts once drifted (wide-mode spec § 9.1).

### 7.3 National Info's strip and mounts from the TABS registry: **do it**

- **The registry.** A Tab gains `public` (shown in National Info) and the root its gates
  take.
- **What it writes.** `gen_te_systems_window.py` writes National Info's strip, its selection
  templates and its two mounts per tab into a second generated file, so adding a system to
  National Info is one flag.
- **Kept to vanilla.** `test_demographics_census_window.py` keeps holding the override to
  vanilla's file outside its mod blocks.

### 7.4 One definition per chart: **do it** (§ 4.3)

The chart registry and generator, unless the diagnostic shows a derived type draws.

### 7.5 One help body per system: **do it** (§ 5.2)

`te_<system>_help_body`, instanced only by its popup. The `*_how_open` flags retire. A test
holds that every system with a tab has a help page, its link, and a "?" in each header it
has.

### 7.6 Sort a stopped history once: **do it** (§ 6.6)

### 7.7 Not in this work

- a topic list for the long Help pages (§ 5.3);
- year ticks on the large charts (§ 4.2);
- Budget Breakdown and the Strategic Reserve for another country (§ 6.4);
- Global Warming and the UN as tabs for another country (§ 2);
- vanilla's tutorial lessons (§ 5.1, D);
- recording history for countries below major power, which would cost 240 containers each.

## 8. Tests, loc and docs

- **Tests:**
  - **`test_te_systems_window.py`:** the `public` flag and National Info's generated strip
    and mounts.
  - **`test_demographics_census_window.py`:** the larger mod blocks.
  - **Each `test_<system>_layout.py`:** orders without `sec_how`.
  - **`assert_wide_matches_narrow`** (`gui_test_helpers.py`): the help bodies are out of
    both layouts.
  - **New:** the chart registry (every `te_history_chart` instance generated, the viewer
    holding every chart, the widths dividing every range); the body rule (§ 7.1); the guard
    (§ 7.2); the help pages (§ 7.5).
- **New GUI files** (the viewer's and National Info's generated files):
  - a row and the count in `gui_modding_guide.md`'s "This Mod's GUI Files"
    (`test_tax_code_bypass`);
  - `docs/auto_generated_files.md`;
  - `EXCLUDED_REGISTRY_GLOBS` in `scripts/nightly_audit_select.py` (`test_nightly_audit_select`).
- **Loc:**
  - `POP_BROWSER`'s replacement, or the foreign button's own key;
  - the "?" and "⤢" tooltips;
  - the help popups' titles, reusing each section's own;
  - National Info's tab names, reusing `te_window_tab_*`;
  - "Not running in <country>";
  - the history empty state for a minor power;
  - the § 6.8 wording, per system.
- **Docs:**
  - **The style guide:** rule 1 (explanations live on the system's Help page, behind the
    "?"); rule 9 (National Info is the second window with more than one strip, and what
    another country's view shows); a line on the chart viewer.
  - **`gui_modding_guide.md`:** the window section and the popups section. It is a CRLF
    file, so keep its line endings.
  - **`history_charts.md`:** the history fix, the viewer, and the stale lines two sweeps
    found: the bar width is fixed, not `{0 84}` expanding; the banking gate is
    `te_banking_cycle_running`; Banking has eight charts, on container 3, not three on
    container 2; the plot is a flowcontainer of fixed widths, not an `hbox`; the charts open
    by default; the cap is 240 containers, not 120.
  - **`system_panels_feasibility.md`.**
  - **The icons docs:** the "?" and "⤢" placeholders.
  - **A play-test list,** `docs/testing/charts-help-national-info-playtest.md` (§ 9).
  - **The player guide:**
    - `01-introduction.md` (the window, National Info);
    - `08-states.md` (the Census Data window);
    - the chapters that send players to a "How X Works" section: `01`, `02`, `03`, `04`,
      `05`, `08`, `10`, `11`, `12`, `14`, `15`, `16`;
    - `17-reference.md`;
    - then a PDF rebuild.

## 9. In-game checks

None gates a merge (`CLAUDE.md`). They go on the play-test list:
1. **The popups layer.**
   - Do the Help and chart popups draw above the TE window in both widths, above the vanilla
     side panels and the journal, and above the Census window?
   - Does Escape close the popup and leave the window under it open?
   - `te_popups` hasn't been seen in game. Fallback: instance the popups at window level in
     each full-screen host, as § 4.4 already does for National Info.
2. **The chart viewer.**
   - At 1200 the bars draw 5, 20 and 100 px wide, and each hovers.
   - The two zero lines sit at 0%.
   - The popup fits 1600 × 900 at UI scale 1.
   - If the diagnostic of § 4.3 runs: whether a type derived from `te_history_chart` draws.
3. **Another country, in National Info, for each public tab.**
   - Its figures, not the player's: compare with what the player's own tab showed when
     playing that country, or with a known value.
   - No controls.
   - No `wanted context of type 'JournalEntry'`, `Failed to fetch variable` or null-country
     lines in `debug.log`.
   - The entry modifiers read through `je:` show the AI's own (Banking's interventions,
     Cultural Hegemony's programs).
4. **The player's own country in National Info:** the controls work.
5. **A former major power's history** after the sort fix: oldest month on the left.
6. **The renamed title and buttons** read as intended, for the player and another country.
7. **An observer** opens National Info for any country with no errors.

## 10. Build order

| PR | Contents | Size | Depends on |
|---|---|---|---|
| 0 | This spec | — | — |
| H1 | The Help popup type, the "?" in `te_system_tab_frame` and the other headers, the first three systems' sections moved; style guide rule 1 | medium | — |
| H2 | The other systems' sections moved; the player guide chapters | medium | H1 |
| C1 | The chart registry and generator, writing today's history sections (no visible change) | medium–large | — |
| C2 | The chart viewer for the player's country, and the "⤢" buttons | medium | C1 |
| F0 | The binding rule: mounts supply `Country`, `te_own_country_only`, the chart defaults, the gates' root as a parameter, the tests of §§ 7.1–7.2 (no visible change) | medium | H2, so the How sections are moved, not rebound; C1, so the charts are rebound once, in the registry |
| F1 | National Info: the rename, the strip and mounts from the registry (Pops and Demographics at first), the foreign chart viewer, the history fix and empty state | medium | F0, C2 |
| F2–F5 | Each system bound and made public, in parallel: F2 Nation (with its UN lines and the Information tab's goto, which opens it), Banking, Tax Code (with its generator); F3 Grand Monuments, Colonial Empire, Seabed; F4 Cultural Hegemony, Nuclear Weapons (the estimate); F5 the Space Race (its two generators and the band) | medium–large each | F1 |

- **Independent work.** H and C are independent and can run in parallel.
- **Self-contained PRs.** Each PR carries its own docs, play-test items and player guide
  changes.
- **When to play-test.** After H1 and C2, which settle the popups layer, and after F1,
  before most systems are bound against it.

## 11. Open questions for the owner

1. **The host and its name:** the Census Data window as "National Info" (§ 6.1, A), or another
   name ("Country Profile", "National Records")?
2. **The rename:** replace `POP_BROWSER`, which renames the window and both buttons, or give
   only the foreign button its own label, which takes an override of
   `country_politics_panel.gui`?
3. **The player's own country in National Info:** the same view with the player's controls
   (recommended), or Pops and Demographics only?
4. **The public list beyond the six** (§ 6.4): Nation (with the UN lines) and Cultural
   Hegemony public; the Space Race and Nuclear Weapons partly; the Strategic Reserve,
   Budget Breakdown and Covert Warfare private?
5. **Grand Monuments:** keep the open opportunity and the interest groups' ledgers private?
6. **Wording:** neutral labels and `SelectLocalization` (recommended), or keep "our"?
7. **The chart viewer's width:** 1200 for every chart, too wide below about 1,300 px of
   screen; or 960 for monthly charts and 800 for annual ones, which fit 1280?
8. **Help:** a popup per system (recommended), or the in-place help mode (§ 5.1, B)?
