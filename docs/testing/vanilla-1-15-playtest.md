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
  panel's Advance and Retreat lists (open an entry that uses one, once one does).
- **C7**: whether a scaling modifier at value 0 shows a row of zeros in the journal entry panel and the country's
  modifier tooltip, or is hidden (open a mod entry that uses one, once § 4.2 builds one); whether a revolution's winner
  gets it back with the inherited entry (the civil-war harness, `docs/audits/civil_war_inheritance_audit.md`; the probe
  entry is `can_revolution_inherit = no`). Since #1404 the Strategic Reserve, Covert Warfare, Global Warming and
  Nuclear Program entries declare their standing modifiers (design
  `docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md` § 4): open each entry and a country's modifier
  tooltip. If a zero row shows, hide the scaling-modifier icon strip on the mod's entries in `gui/journal_entry.gui`.
  Two once-a-game lines in `debug.log`:
  - `TE_SELF_CHECK OK|BROKEN scaling_live`: the Strategic Reserve's declared sales income reaches the country (needs a
    country with a staffed hub selling for two weeks). BROKEN: put the weekly `add_modifier` back.
  - `TE_SELF_CHECK OK|BROKEN scaling_inherited`: 30 days after revolutionaries win a civil war, the winner's Covert
    Warfare funding cost is declared again. BROKEN: the design's § 5 fallback, before PRs 3, 7 and 8's deleted
    revolution repairs matter.
  Also look at: the Budget panel's Strategic Reserve Sales, Covert Actions and Nuclear Program rows still list their
  amounts (they read the modifiers' budget mirror fields); a converted modifier's tooltip names its entry as the
  source; and **Carbon Removal's forced coal subsidy**: `carbon_removal_modifier` carries
  `country_building_synthetics_plant_coal_require_subsidies_bool`, and no vanilla scaling modifier carries a `_bool`
  field. With the policy on, a synthetics plant on a coal method should show as subsidized and unable to drop it. If
  it doesn't, add that modifier to the entry by hand again (it is a flat 1).
- **C20**: whether a fired `fire_only_once` event stays fired across a save and load, and for a revolution's winner
  (save before and after, `scripts/analysis/save_country_probe.py`). Since #1404, 32 once-only events rely on it, and
  the canary `society_technology_events.1` (Women in the Workforce) logs `TE_SELF_CHECK BROKEN fire_only_once_kept` in
  `debug.log` if it fires twice for one nation in a game started after the change. It logs nothing while the record
  holds: read a game with saves, loads and a revolution won past the canary's ten-year modifier. Fallback if BROKEN:
  each event sets its variable in `immediate` again (the triggers still read them).
- **C21**, contextless entries: `should_be_involved` re-checks, what `je:` and `JournalEntry.GetCountry` return for one,
  `effect_all_involved`. A contextless probe entry could show in a player's journal, so none was built.

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
