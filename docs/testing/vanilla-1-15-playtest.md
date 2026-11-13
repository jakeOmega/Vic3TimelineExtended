# Vanilla 1.15 migration: play-test checklist

What the next play-test of the vanilla 1.15 migration should look at. In-game checks don't gate the merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): the migration lands on the offline gate, and what only the game
can show is listed here. Record each answer in `docs/audits/vanilla_1_15_prep.md` § 2 under its C-number (and in the
migration record that doc becomes), and an engine fact in `docs/guides/scripting_best_practices.md`.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main` once merged).
- **Logs.** Read `debug.log`, not `error.log`. It rolls over at 512 KB, so copy a once-a-game line out right after the
  run (log-triage skill, 2026-09-27).

## Answered by the first observer game (2026-11-05)

The `te_probe_115` journal entry answered C3, C5, C7, C19, C20 and C21's journal entry questions, and the copper
self-check read OK. So did `gm_world_base`, and `gm_world_gdp_1836` now holds that game's reading (404,100,000). The
answers are in the prep doc's § 2 and `scripting_best_practices.md` § "1.15 journal entries, scaling modifiers and
once-only events (probed)". The probe and the check are deleted (#1408). The load-time lines below were clean in that
game, in English.

## Not probed (needs a player or a save)

- **C5**, the rest: how a `progress_condition` factor of 0, and one read from a named script value, show in the
  panel's Advance and Retreat lists. Civil Rights' Movement Support bar now uses them (#1441): open the entry and
  check that each of its 13 conditional factors is listed, ticked while it applies and unticked otherwise (Social
  Justice Movements unresearched, a policy off), and that "States with low-acceptance pops", whose value is
  `owner.cr_low_acceptance_count` scaled and capped, is listed with its number. If it is counted but not listed,
  that is the named-script-value case: inline the count or accept it. Check too whether the bar's own hover then
  repeats the list.
- **Civil Rights, two-pole bar** (#1434): Movement Support draws green over a red background with the sliding marker
  at the current value, in the panel and its tooltip. If the marker or the textures don't show, `marker = yes` and
  the `progressbar_green` / `progressbar_bad` sets didn't take; go back to `default_green = yes`.
- **Banking, the cycle value as a two-pole bar** (#1434): Banking Cycle Value draws as momentum and the stance do,
  blue over gold with the sliding marker at the value, "Banking Cycle Value — panic" on the left and "frenzy" on the
  right, in the Banking panel and in another country's National Info (`te_banking_bars`). It was green from the left
  before. If it shows neither fill nor marker, go back to `default_green = yes` and the old green bar in
  `te_banking_bars`.
- **Civil Rights, one outcome per ending** (#1431): the panel lists ten endings in order (Victory on Paper, the
  Civil Rights Mandate, the Movement Carries the Day, A Settlement, Reform on Paper, A New Era of Equality, then the
  four collapses), each with its header, the shared victory or collapse condition and its own line, exactly one of
  each kind ticked; run Federal Protection past 18 months and its line ticks while A New Era of Equality's unticks.
  When one concludes, its event fires and the page shows its `conclusion_desc`.
- **C7**: whether a scaling modifier at value 0 shows a row of zeros in the journal entry panel and the country's
  modifier tooltip, or is hidden (open a mod entry that uses one, once § 4.2 builds one); whether a revolution's winner
  gets it back with the inherited entry (the civil-war harness, `docs/audits/civil_war_inheritance_audit.md`; the probe
  entry is `can_revolution_inherit = no`). Since #1404 the entries converted in the design's § 4
  (`docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md`, each system's "As built") declare their standing
  modifiers: open each entry and a country's modifier tooltip. If a zero row shows, hide the scaling-modifier icon
  strip on the mod's entries in `gui/journal_entry.gui`.
  Two once-a-game lines in `debug.log`:
  - `TE_SELF_CHECK OK|BROKEN scaling_live`: the Strategic Reserve's declared sales income reaches the country (needs a
    country with a staffed hub selling for two weeks with no panel change in between). BROKEN: put the weekly
    `add_modifier` back.
  - `TE_SELF_CHECK OK|BROKEN scaling_inherited`: 30 days after revolutionaries win a civil war, the winner's Covert
    Warfare funding cost is declared again (rebels who ran a Covert Warfare entry of their own don't count). BROKEN
    means every inherited entry has lost its declarations, which this change already relies on: Covert Warfare's five,
    Global Warming's fourteen (no restore effects: since #1466 all eleven policies, and the Colonial Empire's five
    bands, come back only through the declarations), and the revolution repairs PRs 3, 7 and 8 delete. Fallback: the
    design's § 5.
  Also look at: the Budget panel's Strategic Reserve Sales, Covert Actions and Nuclear Program rows still list their
  amounts (they read the modifiers' budget mirror fields); a converted modifier's tooltip names its entry as the
  source; and **Carbon Removal's forced coal subsidy**: `carbon_removal_modifier` carries
  `country_building_synthetics_plant_coal_require_subsidies_bool`, and no vanilla scaling modifier carries a `_bool`
  field. With the policy on, a synthetics plant on a coal method should show as subsidized and unable to drop it. If
  it doesn't, add that modifier to the entry by hand again (it is a flat 1).
  Colonial Empire: a step on a program moves its modifier, now on the entry, within a few days, and the
  investment's expense follows. The stability band's modifier (#1466) sits on the entry, named as the source, and
  moves within a few days of the bar crossing an edge (`event te_debug_colonial_empire.1` sets the bar to each band):
  exactly one band at a time, Solidified from 90. Each declaration reads the bar through `je:` from the country
  (`colonial_empire_live_tier`), which no probe has read inside a declared value: this row is the check, by eye. If
  no band shows, declare the bands from vanilla's form instead, `scope:journal_entry.scripted_bar_progress(...)`
  in the value (`je_state_and_revolution`, `00_communism.txt`), or put the monthly swap back (`git show` #1466's
  parent, `je_colonial_empire.txt`'s pulse). Global Warming (#1466): adopting any of the nine
  flat policies (Carbon Tax … Fossil-Fuel Tariffs) shows the policy on the entry within a few days, named as the
  source, and repealing takes it off; the row's active check and the adoption counts move at once (they read the
  variable). A treaty 109 source shows its seven policies adopted, each with its text in the treaty's tooltip.
  **A 1.3.x save** (#1466's one-time migration, `te_flat_toggle_migration_effects.txt`): load a 1.3.0 or 1.3.1
  save with several climate policies adopted (Fossil-Fuel Tariffs among them, as a market leader) and a Colonial
  Empire running. After a week each policy shows adopted once, its modifier on the entry once (not doubled) and
  Repeal offered; repealing takes it off. The colonial entry carries exactly one band modifier. If a copy is still
  doubled, the remove didn't see the saved copy (`has_modifier` on the entry). Cultural Hegemony: ending a program reads "Ends …" in the tooltip, the program
  count drops in the same click and the modifier leaves the entry within a few days; starting Outreach previews
  the program and its cost, which then follows GDP; repealing the Ministry of Culture stops the four programs at
  the next monthly update and the funding pair within days; a country trailing the hegemon shows the Foreign
  Cultural Benchmark on the entry, named as the source. Banking cycle: the Neutral stance (`banking_stance_band_3`,
  an empty modifier declared at 1) still shows in the entry's list; the Budget Breakdown's Banking row still lists the
  planning pool's balance and both external charges; the momentum tooltip names the bubble inertia tier. Grand
  Monuments: a policy change moves the national effects on the entry within a few days; a boon shows on the entry
  while its countdown runs; the dig gate's day-by-day check is in the archaeology play-test's "The gate." row. Tax
  Code, Light setting: a step moves the rate and the tax level at once and the Budget's collected rate within a few
  days (note whether it lands at once, which would mean `should_update_on_player_command` re-reads the
  declarations); the interest group reactions show on the entry, named as the source; under the full code and before
  any step, the entry carries 21 declarations at 0, so it is where a zero row would show first. The two lag windows
  have their own checks in `tax_code_schema.md` § "Light code checks". Space Race: a funding step or an approach
  switch moves the entry's Space Program Cost and the panel's pace within a few days. Open a colony holder's Solar
  System Colonization entry: it should list both the Space Program Cost (declared in `je_space_race.txt`) and the
  colony specializations and discoveries (declared in the generated INJECT,
  `common/journal_entries/sr_sites_generated.txt`). One kind without the other means the INJECT replaced the
  entry's own blocks or was dropped. After a load,
  `debug.log` should name neither that file nor `je_space_race_solar_colonization` in an error. A Shackleton
  depot holder keeps off-window launches (the `propellant_depots_bool` self-check). United Nations: ratifying a
  convention puts its modifier on the entry within five days, named as the source; at Moribund the convention
  modifiers leave the entry while Our Obligations still lists the conventions, and they return when the tier
  rises; starting a program puts its cost and benefit on the entry within days, and a second start in the same
  week is refused when the first one's influence would leave too little (the booking, `un_influence_pending`,
  with its own line in the button's tooltip); a member at Contested or better carries UN Membership Benefits on
  the entry (its gate reads `je:je_united_nations` from inside the entry's own value, unprobed); the Budget
  Breakdown's United Nations expense and income rows still list their amounts.
- **C20**: whether a fired `fire_only_once` event stays fired across a save and load, and for a revolution's winner
  (save before and after, `scripts/analysis/save_country_probe.py`). Since #1404, 32 once-only events rely on it, and
  the canary `society_technology_events.1` (Women in the Workforce) logs `TE_SELF_CHECK BROKEN fire_only_once_kept` in
  `debug.log` if it fires twice for one nation in a game started after the change. It logs nothing while the record
  holds: read a game with saves, loads and a revolution won past the canary's ten-year modifier. Fallback if BROKEN:
  each event sets its variable in `immediate` again and its trigger reads it again
  (`NOT = { has_variable = <name> }`; the names are in `test_once_only_events.py`).
- **C21**, contextless entries: `should_be_involved` re-checks, what `je:` and `JournalEntry.GetCountry` return for one,
  `effect_all_involved`. A contextless probe entry could show in a player's journal, so none was built.
- **Power bloc mandates** (#1442). *Answered 2026-11-06* by the test console's Add and Remove options
  (`event te_debug_pb.1`): `add_power_bloc_mandate = -1` removes a mandate, both changes show straight after the
  click, and the `power_bloc.num_mandates` value link matched the trigger's count each time
  (`docs/systems/mod_systems/power_blocs.md` § "Mandates in Script (1.15)"). Still open: Remove with no mandates held
  (can the count go below 0?), and whether the panel's own mandate display moved with each click. The power bloc
  summit (te_pb_summit.1) depends on the answers; to check it:
  - **The button.** As a bloc leader, Convene a Summit sits beside the mandate count, grayed with "We lead a bloc that
    holds at least one Mandate" ticked off when you have none, and enabled once you have one (the console's Add). It
    should fit the row beside the count without pushing it off-center, and its tooltip should read the initiatives line
    and then the condition.
  - **The event.** It opens as a popup. Each option's tooltip leads with "Spends 1 Mandate" and the modifier it grants;
    Common Purpose also shows the immediate cohesion. Picking one drops the panel's count by one at once and puts the
    modifier on the bloc (or, for Mandate at Home, on the leader). Convene again: the option just taken is gone,
    except Common Purpose. With a bloc holding Navy III and Freedom of Movement III, the Open Borders Accord is gone.
    Spend the last mandate on a principle while the event is open, then answer: only Adjourn is offered.
    *Partly answered 2026-11-06* (Great Britain, Common Purpose): the bloc took Summit: Common Purpose (+10 under
    "Timed Modifiers" in the cohesion tooltip) and cohesion jumped 20, from about 43 to 63, then fell 1 a week
    toward the new target of 53. But the option's modifier line read " gets Summit: Common Purpose", with no
    subject. The bloc options now print their own line: check that Common Purpose, Recruitment Drive, Leverage
    Campaign, Open Borders Accord and Customs Harmonization each read "<bloc name> gets Summit: … for 10 years"
    with the modifier's lines indented under it. Take Common Purpose a second time while it runs: the Timed
    Modifiers line should still say +10, not +20. A +20 means `has_modifier` is false in bloc scope (the engine
    docs' description leaves power blocs out), so the remove-first never runs and the copies stack.
  - **The identity initiative.** Each bloc sees one more option, its identity's. Check at least a Religious
    Convocation (the council's name follows the leader's faith: a Catholic leader's reads "ecumenical council", and
    a faith with no name of its own the plain "council of our faith", never both), and one with "Relations between
    every two members of the bloc rise by 20" (Military Treaty, Cultural Commonwealth, Diplomatic Framework): after
    it, open two members' relations and see the step. Members' initiatives should show on every member's modifiers,
    the leader's included.
  - **The AI.** In an observer game, `debug.log` should carry `TE_PB_SUMMIT <kind> by=ai` lines once AI blocs hold two
    or more mandates, a few a decade per bloc, mostly `rally` and `leverage`. None at all after a decade of blocs
    holding mandates means the monthly roll never fires.
- **C21, formation mandates (#1458).** The four technologies that add a principle slot each carry
  `country_power_bloc_formation_mandates_add = 1`, which vanilla describes as more mandates to spend on principles
  when forming a bloc. One once-a-game line in `debug.log` when a bloc forms: `TE_SELF_CHECK OK|BROKEN
  formation_mandates`, with the new bloc's unspent mandates, its principle levels and the founder's grant. Principles
  taken at formation count: the founder spends the mandates there, so unspent mandates alone can read 0 when the
  modifier works. OK can't tell the extra mandates from vanilla's free formation picks, so found one bloc with the
  technologies and one without and compare the principles each could pick in the formation window. BROKEN: open the
  bloc's panel and count its principles and mandates; if the founder could pick no more than one without the
  technologies, grant them in the on-action with `add_power_bloc_mandate` and drop the technologies' lines. No line
  at all once a bloc has formed means `scope:country` is not set in `on_power_bloc_formed`. Whether `MAX_MANDATES`
  (5) caps the grant shows only if a founder carries more than 5.
  Under the Four principle slots rule, found a bloc with all four technologies and count the principles the
  formation window lets you pick: `te_pb_principle_slot_free` passes while the founder is not yet in a bloc, so the
  pick may exceed the rule's cap of four. If it does, gate the formation pick on the rule or drop the mandates under
  it.
- **New 1.15 modifier hooks (#1453, #1458).** Hover each and read the tooltip, then watch it act once:
  - Civil Rights: Federal Protection's +25% and Segregationist Consolidation's −25% enactment speed for
    Multicultural. Enact Multicultural under each and compare the progress per week.
  - Vassalization V: `country_overlord_law_enactment_success_add` +10% on members. Vanilla's Congress Poland carries
    it on the subject, so it should help an overlord enacting a law in a subject member; if it shows on the leader's
    own enactments instead, move it to `leader_modifier`.
  - Universal Basic Income: +0.5 toward reform in Reform or Revolution's country contribution tooltip (the "bonus
    values" line), once the entry runs.
  - External Trade IV and V: the interest-tier trade advantage lines (+5% to +20%, +10% to +40% from engaged to
    hegemonic). Compare a member's trade advantage in a region where it is hegemonic with one where it is only
    engaged.
- **Stalemates (#1449).** In a long world war, `world_war_events.31` (The Same Line) should also arrive for a
  war leader whose war is in the engine's stalemate countdown (both leaders at minimum war support, the war
  panel's stalemate timer running), whatever its age and battle count; its co-belligerents should not get it
  that way. After Hold the line (+5) the timer should stop; after armistice
  talks it should run on. In the same game, a Binding Ceasefire against one side of a stalemated war should come
  sooner and carry more votes than against a fresh one, and an AI metropole in a war of independence that stalls
  should open talks (the panel's row shows them) before its four years are up.

## Panels and systems

What the migration changed that only a game shows, by area. Any game will do unless a line names a country or a
save. Load-time first: `debug.log` should carry no `Unexpected token` from a mod journal entry, progress bar or
mobilization group, no `Duplicated key` for `law_communal_administration`, `building_copper_mine`,
`building_copper_mine_throughput_add` or `goods_output_fine_art_mult`, no `Province crossing multiple state
regions`, and `grep -c "quote-escaping" debug.log` should be 0 (283 on the first launch), in English and in a German
or Spanish game.
- **No `missing an activation_description trigger` line** at load (29 mod entries logged one on the first 1.15
  launch; each now has vanilla's default, #1408). In the journal, an inactive mod entry's activation hover reads as
  it did.
- **A new game's starting laws** (#1408): `error.log` has no `set_institution_investment_level … invalid institution
  type` line, and Britain, Bavaria and Switzerland hold Religious Schools with a schools level, not No Schools.
  Britain, France and Baden hold Interventionism, not Agrarianism. The north German states (Saxony, Brunswick,
  Hamburg) keep Civic Monolingualism. The first 1.15 game had 36 countries on No Schools and 46 on Agrarianism from
  the law sweep running mid-history.
- **Decentralized nations' starting laws** (2026-11-05): `debug.log` has `TE_SELF_CHECK OK decentralized_law_baseline`,
  and `error.log` has no `is not permitted to retain law` line for Violent Hostility, Penal Labor Camps, Total War,
  State Secrets or Intrusive Surveillance (the first new game after #1408 had 146–158 of each, every one a
  decentralized nation). In a save, a decentralized nation such as Patagonia holds Discrimination, Punishment-Focused
  Criminal Justice, Traditional Rules of War, Informal Government Secrecy and Minimal Privacy Protection. BROKEN: the
  `every_decentralized_country` block in `extra_history.txt` doesn't reach them in history either; the fallback is
  declaring each group's tech-free law first, which reorders the law panel (owner's call).

**Journal entries** (`docs/audits/vanilla_1_15_migration.md` § 3)
- Every mod entry's panel opens and lists its outcomes with headers, colors and effect previews; when one concludes,
  its effect runs and the concluded page shows its `conclusion_desc` (C2).
- C3 in practice, which outcome wins when two come true on one update (the mod puts success first): Colonial
  Empire's bar reaching 0 on the day a capstone completes; Civil Rights' movement disappearing as its bar reaches 100.
- A 1.14.5 save with active and concluded mod entries (C14): active ones stay active and can still conclude. Note
  what a page concluded under 1.14.5 shows.
- Grand Monuments: day one logs no `already has a journal entry of type je_grand_monuments`, and a country with a
  monument still gets the entry active within weeks.
- Banking: momentum and stance draw as two-pole bars with a sliding marker, in the panel and in the `te_banking_bars`
  overlays.
- Art: the Soft Power and Covert Warfare groups show their illustrations, Global Warming sits in Internal Affairs,
  and the training mobilization group shows its background card in the military panel.
- The Opium Trade isn't offered after 1912-01-23, and one still open then fails with the mod's text. Turtle Island
  is hidden for a North American union and goes invalid, with its cleanup, if one forms. The three vanilla tax
  entries complete under the Tax Code rule.
- How the panel shows an `INJECT:`ed outcome: listed as one more, merged, or dropped (the parser assumes one more).
- `disable_evaluation` (#1404): in a game with Social Movements off, no Civil Rights, Digital Rights, Mental Health,
  Morphological Freedom, Human Augmentation or Post-Scarcity entry ever shows; in a game with every rule on, each
  entry appears as before and every country still holds Banking's dormant entry. `debug.log` has no `already has a
  journal entry` line for a pruned type.

**The journal panel and tooltips**
- Every journal entry panel opens, and the concluded page too. No duplicate bars under the bars-on-top marker
  (Global Warming, Strategic Reserve, UN, Climate Engineering); the Nuclear entry's container-4 sections sit
  sensibly now that `_4` is in the description column.
- Tooltips are not clipped and scroll at 835 px; glossary tooltips are 600 wide. `gui.log` no longer reports
  `FancyTooltipGlossaryWidgetType` or `elide_fontsize_min` from vanilla's `custom_tooltip.gui`.

**Economy panels**
- Budget, Taxes tab: 1.15's per-state Unrealized Taxes list and its sort, a relieved state listed; the Banking, Tax
  Code and Breakdown tabs.
- Goods views: the prestige breakdown, and the consumption-tax toggle greyed under the Tax Code rule.
- Market: the six tabs, charts and partners; the prestige list's new name.
- Building details: the Grid Transfer Station's Power Grid section; a building with five or more PM groups (its
  290 px strip beside 1.15's 300×80 extra-items widget: do they overlap?). PM strips scroll and hide maintenance
  groups.
- States: vanilla's Cold tile before the TE tiles, the header's cold icon, Cossack Host tiles on a Russian state, the
  market tile's go-to tooltip, the Demographics subtab. Population: the Demographics tab.
- The Construction Sector's expand hover in a market game: Earnings header, lore section, efficiency warning.
- The Mitsui Trading House description: a hoverable "Zaibatsu" glossary link.

**Military, diplomacy and politics panels**
- Right-click a selected army and a selected fleet: Invasion, Rehome (now greyed by `CanRehome`), Deploy to Front,
  the transport fleet list, the fleet's ship-template construction tooltips.
- Treaty designer: Nuclear Arms Limitation's warhead quantity (right-click input, draft button, signed display), a
  generic company article, Cede Colony's building-type and colony lists, beside 1.15's ship-transfer bundles and
  automatic-withdrawal checkbox.
- Law panel with a taxation law selected: All effects shows the header and hover line, Comparative effects shows
  "Effects compared to current law:" and its hover line; frame rate stays normal in both. A non-tax law shows
  vanilla's text in both views, and its view toggle sits at the same indent as a tax law's. Opening a law no
  longer crashes the game, and error.log has no `can't have an hbox/vbox` line. Both launches of #1402 overflowed
  the stack in the second the panel was built. If it still crashes there without that line, the other suspect is
  the toggle's `visible`, the mod's first call of 1.15's `GetDeltaEffectDesc`: drop that half and relaunch.
- Military panel: mobilization groups one card a row with their backgrounds; the Nuclear and Covert tabs.
- Power bloc panel: principle slots 5-8 and the remove button; the formation panel's primary principles one a row.
- Descriptions added offline (#897; not part of the migration, listed here because these are the panels that show
  them). Laws panel: the Minority Rights group's tooltip opens with a sentence, not `lawgroup_minority_rights_desc`.
  Military panel: the Training mobilization group's tooltip, and the Heavy Tanks and Aircraft unit groups wherever a
  group's tooltip shows, read as sentences, not `training_desc` or `combat_unit_group_*_desc`. Power bloc panel: a
  tier IV or V principle (and Sacred Civics at any tier) shows its group's description in its tooltip, as most tiers I to
  III do. Whether a principle with no `_desc` key shows the raw key or nothing was never checked; none is left to look
  at, so that needs a key commented out.
- Politics overview: the ruler's aptitude traits in the featured slots.

**Politics**
- Russia at start: Okhrana, Third Section, Official Nationality and Caesaropapism stand where Secret Police,
  Subjecthood and State Religion would, and their tooltips show the mod's lines.
- A council republic can enact Labour Suffrage, then Elected Bureaucrats or Communal Administration; Electoral
  Finance moves off No Campaign Finance Laws, and the First Past the Post petition can fire.
- Communal Administration under Anarchy or Collective Governance (with Socialism) is enactable, and Government
  Administrations switch to Communal Representatives. Under Algorithmic Governance, Military Bureaucrats isn't.

**Copper and lead**
- Katanga or Zambia: copper shows as a discoverable resource with vanilla's cap available from 1836. The INJECTed
  `building_group` took: the first observer game logged `TE_SELF_CHECK OK copper_mine_discoverable` (2026-11-05), and
  the check is deleted (#1408). What's left to see is the panel: the deposit's discovered and undiscovered parts.
- Copper mines climb the late tiers and switch to mechanized maintenance at the condensing pump.
- Tooltips say Conductive Metals and Base Metals, including through the `$copper$` splices; Mount Whaleback and
  Sumitomo show their copper bonuses.
- An old save: the mod's old copper mines and renamed carbon-capture variants fall back to their groups' defaults.
- Copper discovery pacing over a few decades; one copper belt each in Katanga, Zambia and Antofagasta.
- The copper follow-ups (#1405): Conductive Metals shows in the Strategic Reserve with Electrical Generation, a
  ninth row named "Conductors" with the copper icon and 0% decay; the hub stores and releases it (its intake needs
  the newly registered `goods_input_copper_mult`: no `Unknown modifier type` for it in `debug.log`). BHP Group and
  Vale list High-Conductivity Copper, drawn with the base game's copper goods icon until a painted one is made. A
  Grid Transfer Station buys 2 Conductive Metals a week, and an HVDC Undersea Interconnector 6. Copper's price over a
  few decades now that power, construction, munitions and assembly lines take it. The modern coal and oil plants burn
  20% and 14% less fuel for the same power, so the next observer run's warming at 2015 (about 1.1 °C before) may
  read a little lower.

**The map**
- TULA, KOSTROMA and the renamed states (LITHUANIA, SARATOV, VOLOGDA) have tourism, a Local Climate tile, an area,
  Planned Capital, capital bloc names and a seabed basin where coastal; KAMCHATKA holds the old Chukotka.
- A Cossack Host reads as cooperative in the Demographics rural-work split, and its workers count for the state's
  farming town in Largest Cities, not the capital (#1407).

**Defines, treaties, the UN and ships**
- Devastation without the mod's overrides, and whether the UN docket's `un_docket_war_devastation` (0.3) is still
  reachable under per-battle devastation; the docket's 0.25 occupation threshold.
- Renegotiate a treaty to add Seize Company or Disband Company: it takes effect. Since #1407 neither is
  renegotiable, so a copy carried over from the old treaty is locked and doesn't seize or disband a second time.
- The six one-off articles (Disband and Seize Company, Return Cultural Property, Surrender a Monument, Cede Colony,
  the population transfer) carry `is_one_time` (#1407): an AI that received mostly one-offs withdraws once the
  binding period ends, so it stops paying their upkeep. No vanilla article is both one-time and enforceable, and
  these six are. Watch an AI that won a war on mostly one-offs plus Forced Disarmament or a demilitarized zone: if it
  withdraws when the binding period ends, the restriction lifts with it. The loser could leave then anyway (neither
  article has a `can_withdraw`), so this matters only where the loser would have stayed.
- Forced Disarmament: the conceding country can't queue a warship (vanilla's "cannot construct military ships" reason
  names the article), and can still build supply ships. A demilitarized zone's state shows "Disallow Barracks
  Construction" (#1407).
- A demilitarized zone renegotiated, and a seabed lease's quantity on renegotiation; the money transfer's
  contextual score.
- Decolonization: a subject's war against the overlord's own revolutionaries or secessionists isn't tracked.
- Ships: module costs in the ship designer; AI submarines built only under Jeune École or Merchant Navy and sailing
  in `submarine_raiding_fleet`.
- The population transfer's timed modifiers decay (1.15 fixed scaled effects that read a saved scope).
- A marginal interest group's halved trait line; Foreign Affairs' formation-interest gain; literacy curves; war
  deaths in the census (all moved by vanilla, § 5 of the migration record).
- `debug_log` lines that pass arguments through `te_log_args_set` print the names, not blanks.

**Pre-1.15 leftovers (#1406)**
- The Buildings map list's profit column: a Naval Fortification or Naval Logistics Center reads Upkeep (a Barracks
  shows its Units column there instead), a Construction Sector in a Free Market Construction game reads Earnings (its
  group is under heavy industry, not government funded), and National Parks read Upkeep. The mod's copy of the
  header, which named only Government Administration, is gone.
- Japan on Shinsengumi: the law's tooltip lists Secret Police's tourism, intelligence capacity, colonial stability
  drift and a flat +0.1 colonial garrison effectiveness (it has no institution to scale it), and
  the Ministry of Propaganda can be enacted once Mass Media is in. The Ottomans on the Millet System: the Ministry of
  Religion can be enacted, and the law shows State Religion's bureaucracy cost line.

**1.15 opportunities (#1445–#1452)**

From the prep doc's § 7.1 shortlist and § 4.11. Thresholds here are first guesses: note what each AI did, and tune.
- **World Climate (#1448).** Under the Global Warming rule, once the world reaches 0.1 °C a World Climate entry opens
  in every country's journal, lists every country as involved (decentralized nations too), and carries Climate
  Warming, named as the source in a country's modifier tooltip; Global Warming's own entry no longer lists it. One
  line in `debug.log`, once a game at 0.5 °C or more: `TE_SELF_CHECK OK|BROKEN gw_world_climate` (the largest
  economy's capital reads `state_harvest_condition_wildfire_duration_mult` at 0.5 a degree, and the country is
  involved). BROKEN: put the declaration back on `je_global_warming` and `gw_warming_felt` back on
  `has_journal_entry = je_global_warming` (the parent of #1448's commit). Also note: a `TE_GW_WORLD
  fallback_involved` line, and its date, says the engine doesn't involve a country created after activation on its
  own (C21); none after a revolution won means it does. A revolution's winner carries Climate Warming within a month.
  The recurring climate events (coastal flooding, crop failures) still fire. The page's Involved Countries list and
  the entry's tooltip are long: say if either is a problem.
- **Losing a war (#1447).** A country a quarter of whose GDP sits in blockaded states, or whose enemies press it at
  0.5 or more (`enemy_pressure`), now counts as losing: its covert-operations AI, ASAT strikes and nuclear first use
  under Flexible First Use follow. Watch an armed AI under a naval blockade, and note `enemy_pressure` readings
  through a war if a probe is cheap. A war goal on a nuclear power's state that nobody advances or contests
  (`has_stalled_state_wargoal_against`) no longer counts as a threat to its core unless it is losing.
- **Military reach (#1450).** `te_military_reach_values.txt` holds the thresholds (0.4 reach for an army, 0.2 for a
  union's link, shipping as much army strength as the target's at once). Check: a great power across an ocean
  without a navy no longer intervenes for colonial rebels; a metropole whose army can't reach a colony fights its war
  of independence half as often; Voluntary Union and Integrate Decentralized Power are no longer offered between two
  coasts merely because both have one (note how far 0.2 reaches by sea); the AI rarely sends a peacekeeping contingent it can't reach; a Military Treaty
  bloc's 5× army bond needs the reach. Note any slowdown in an AI month: the reach reads sit in an AI loop (the
  absorption effect, the UN missions) and in Subjugate's `possible` (C21).
- **Environmentalist leaders (#1446).** `interest_group_ideology_environmentalists_leader_chance_mult` shows on an
  interest group with Green Leadership Drift as "Environmentalist Leader Chance +100%", with no `Unknown modifier
  type` line in `debug.log`, and the group's next leader is more often an Environmentalist. Only The Reckoning (3 °C)
  still converts a sitting leader (the Intelligentsia's).
- **Institution names (#1451).** The Ministry of War reads Ministry of Defense with Combined Arms, and Department of
  War or of Defense in a presidential republic; Britain's National Bank reads Bank of England, America's Bank of the
  United States (Federal Reserve from 1913), and any under State-Owned Banking, State Bank; Labor, Intelligence and
  Propaganda follow the form of government. Check the institution panel, the budget's institution rows and a
  tooltip that names one, and that a country without a matching name reads the plain one.
- **Formal names (#1452).** With the Country Names on Map rule, the mod's tags show their `_DEF` names (Union of
  India, State of Indonesia, State of China, Intermarium Federation, Union of Dar-Al-Islam; the unions as they
  are). C21: whether a formable under a government-flavored dynamic name shows that name or the `_DEF` one, and what
  a country with no `_DEF` key shows. If a dynamic name shows its key with `_DEF` appended, its 84 names need one each.
- **Latitude triggers (#1454).** The offline lists in the PR took each state's latitude from the reference place in
  `scripts/generators/data/local_climate.csv`; the engine reads the state region's centre point, so a state near a
  tropic may fall the other way. Disease outbreak
  (`environmentalism_events.14`): at 2 °C a country with no incorporated tropical state never gets it. Antarctic
  station AI: smaller powers on a coast south of the tropics (Chile, Argentina, New Zealand, South Africa,
  Australia) open stations more often than before; well past thirty stations means its +20 needs lowering.
- **`list_scopes` (#1436).** C10's display half. The United Nations of Earth's requirements (formation, or the
  unification play) list the great powers under "at most one outside the bloc", "aligned" and "no friction", each
  passing or failing on its own line; with the UN rule off, see whether the bloc-unanimity line inside its
  `custom_tooltip` lists them too (that answers C10). The Imperial Federation Act and the Civilizing Mission Compact
  list the overseas colonies under their four-colonies line. If a list shows every country or every state, add a
  `filter` (UNE has one; the colony count doesn't). The logic is pinned offline (`test_une_formation_gates.py`), so
  a gate that passes or fails differently from before means the engine reads `filter` or `count = all` otherwise
  than vanilla's tsar buttons suggest.

- **Treaty articles: `can_propose` and the lens (#1440).** In the treaty designer, add Extensive Modernization Aid
  before Modernization Aid, Joint Military Exercises before an alliance, and a Nuclear Guarantee before a Guarantee
  Independence: each draft accepts the article and the proposal goes through once the partner is in; without the
  partner the Propose button is greyed with the requirement's line. Also note whether an AI ever proposes one of the
  three, and whether the Budapest offer's guarantees (`nuclear_custody.11`) are still created (C21: whether
  `create_treaty` runs `can_propose`). The diplomatic lens's Treaty Articles tab lists the mod's articles with no
  input; with the Nuclear Weapons rule off, or the banking system on its simplified setting, their articles are absent.
- **Cessions and reparations as treaties (#1457).** One line each in `debug.log`, once a game:
  `TE_SELF_CHECK OK|BROKEN treaty_state_transfer` (three days after `irredentism.2.b` "Cede peacefully" or a
  complied UN court ruling, the state is the taker's) and `TE_SELF_CHECK OK|BROKEN treaty_reparations` (three days
  after `decolonization_events.6.a` "We acknowledge the debt" or a nuclear crisis's reparations, the Reparations
  article's `on_entry_into_force` paid). Either BROKEN leaves play correct (the check has already made the transfer
  directly); the line says which failure it was. `treaty=yes`: the treaty exists but its `on_entry_into_force` did
  not run for `is_draft = no` (C21), so put the direct `set_state_owner` / paired `add_treasury` back at the four
  call sites (the parent of #1457's commit) and drop the two helpers. `treaty=no`: `create_treaty` made nothing
  although `can_create_treaty` passed, so the treaty block is wrong (the `inputs` form, the binding period) rather
  than the hook: compare it with vanilla's 1.15 uses before dropping the helpers. A
  `TE_SELF_CHECK BROKEN treaty_reparations_gate` line means `can_create_treaty` refused the Reparations article with
  the payer's record just set (its `visible` / `possible` don't see the record, or `scope:other_country` is unbound
  there), so every reparation is paid directly and neither verdict above can appear: fix the article's gate. Also check: the treaty shows in both countries' diplomacy panels, named and with the state or
  Reparations article; the treasuries move by the sum the option's tooltip showed, once; the state does not move
  back, and nothing is paid twice, if the treaty is later withdrawn.

## 1.15.1 hotfix (2026-11-11)

What the 1.15.1 bump (`docs/audits/vanilla_1_15_1_migration.md`) leaves for the game. Any new 1.15.1 game will do
unless a line names a save.

- **Load.** `debug.log` has no `Unexpected token`, `Unknown modifier type` or `inject/replace to a non-existing
  entry` line from a mod file, and the launcher shows no version warning for the mod.
- **Stake Colonial Claim.** As a colonizer beside a decentralized nation, the action's tooltip shows 1.15.1's
  infamy (half the state's infamy value, where it was 5 to 20). A country that has renounced its claims through
  Decolonization still sees the action closed with the mod's reason.
- **AI subsidies (owner call 2 of the record).** Vanilla reworked them, and the mod's `should_remove` on power
  plants, railways and ports was last read on 1.14.5. A few years into a game, count AI power plants, railways and
  ports with `subsidized=yes` in a plain-text save, as `docs/testing/ai-economy-playtest.md` did. Near none: the
  setting still works, or vanilla's new logic does the job. To tell which, read the same counts in a game with
  `common/ai_strategies/te_ai_subsidy_strategies.txt` taken out: if they match, the file can go. If railways or
  ports that lose money and carry a state's infrastructure are now stripped where vanilla would keep them, the
  workaround has turned harmful.
- **Copper.** The seven states that now hold vanilla's copper (New Brunswick among them) can build a Copper Mine
  from the start; the copper price through the 1840s and 1850s sits nearer its base than on 1.15.0; Telephones and
  Arc-Welded Buildings stay profitable with their new inputs.
- **Ports and railways** start a new game unsubsidized (vanilla's change). Watch an early AI country's railways
  for a state whose infrastructure collapses.
- **Merged panels.** A broken GUI merge logs nothing, so open each:
  - *Market panel, Trade tab*: the order and spacing of the capacity boxes, the filters, vanilla's charts, the
    mod's three chart blocks, the All Goods rows (on their darker background) and the goods list; the world market
    hub filter button and its menu. With a hub selected, vanilla's charts show the hub and the mod's the whole
    market (owner call 6).
  - *Formation panel*: one of your fleets shows Formation Settings with only Auto-replace lost ships; an army shows
    only borrow and lending; another country's fleet shows no section, and another country's army shows the section
    as before (`Or(IsArmy, GetCountry.IsLocalPlayer)` is a new combination on this panel). Mobilize and Raise
    Conscripts keep their text clear of their icons, here and on the military overview.
  - *Journal*: a historical outcome's own box; the tighter bars; a mod entry that draws its bars on top still hides
    vanilla's.
  - *Treaty panel*: the binding-period box, and a law commitment's icon opening the law group. *Right-click on a
    state*: the world market hub entry. *Building details* on a hub's state: the second go-to button.

## Harness run, 2026-11-11 (1.15.1)

Run through `python3 -m game_qa` on a fresh 1836 game; figures and run folders in `docs/testing/game-qa-results-2026-11-11.md`.

1.15.1 hotfix, "Ports and railways": no country starts with a subsidized port or railway. `decentralized_law_baseline` OK again.

## Infamy ported to `country_infamy_value`, and the naturalization amendment (#387, #1384)

| Check | Expect | If it fails |
|---|---|---|
| **Subjugate's infamy.** As a bloc leader, subjugate a member; read your infamy before and after, and `debug.log`. | `TE_SELF_CHECK OK force_subject_infamy`, and a rise of a fifth of the annexation figure the State Infamy map mode shows for the target (summed over its states), at most 25; half that for a Sovereign Empire. The action's preview shows the same figure. | `BROKEN` (0 infamy): `country_infamy_value` doesn't resolve in a diplomatic action. Sum `state_infamy_value` over the target's states with `every_scope_state` in a script value instead, after `save_temporary_scope_as = target_country` (vanilla's stake-colonial-claim action saves its state first). |
| **UN mandate goal without a mandate.** Only reachable if `possible` lets one through (a lapsed mandate keeps the goal: `valid` doesn't read it); add the goal and let the mandate lapse, or read the preview. | The goal's infamy equals a plain `return_state` on the same state. | Different: compare the block with vanilla's `21_return_state.txt`. |
| **Language Requirement for Naturalization.** Under National Supremacy with the amendment and no other restrictiveness (no Migration Controls), hover the migration restrictiveness: 21. Find a culture sharing no language, heritage or tradition (acceptance 20). | It can't migrate in; under Cultural Exclusion (acceptance 40) it can. | It migrates under National Supremacy: restrictiveness isn't compared with the acceptance shown, or not strictly. Record what the tooltip shows. If the engine bars a pop *at* the threshold, 20 would do the same as 21. |
