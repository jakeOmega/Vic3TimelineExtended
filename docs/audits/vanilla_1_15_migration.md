# Vanilla 1.15 migration record (2026-11-05)

What the move to vanilla 1.15.0 ("Ivan-Chai") changed in the mod, what the release-day checks found, and what is
still open. The plan it followed is `docs/audits/vanilla_1_15_prep.md`, written before the patch shipped and treated
as guidance: where the install contradicted it, the install won, and § 4 lists the corrections. What only the game
can show is on the play-test list, `docs/testing/vanilla-1-15-playtest.md`. The general procedure, updated from
this run, is `docs/guides/vanilla_patch_runbook.md`.

## 1. How it was done

- **Inputs.** The 1.15.0 install. A mods-off `script_docs` dump (`~/src/vic3-engine-docs/1.15.0/docs`, matching
  the 1.15.0 Modding-Digest's names). `vanilla_parsed/` rebuilt from the install. The private vanilla clone now has
  1.15.0 on top of 1.13.9: 1.14.x was never committed, so there was no 1.14.5 base for GUI merges or `REPLACE:`
  re-bases (runbook § 2 now says to keep the clone current, hotfixes included).
- **Order.** A foundation commit (the balance snapshot, `vanilla_parsed/`, the engine-doc render, the
  effect/trigger, context and asset catalogs, `metadata.json` at 1.15.0), then nine streams in sparse worktrees
  from it: journal entries, politics, copper, map, loc, three GUI streams, tooling, a script sweep and in-game
  probes. Each owned a fixed set of files and merged into the integration branch `vanilla-1.15`. The regenerators
  ran once on the merged tree.
- **No in-game run before the PR**, by design. One launch of the unconverted mod (§ 2) gave the release-day log.

## 2. First launch of the unconverted mod

A new 1836 game on 1.15.0 with `main` as it stood (611fe8d), run to 1 March 1836 and quit cleanly. `debug.log`
held 8,026 lines in 1,642 distinct messages, none tagged as known noise. No `TE_SELF_CHECK` line read BROKEN.

- **Old journal entry syntax is not accepted (C1).** Every `complete`, `on_complete`, `fail`, `on_fail`,
  `invalid`, `on_invalid`, `on_timeout`, `custom_*_header` and `event_outcome_*_desc` logged `Unexpected token`,
  in every mod entry and in the three vanilla entries the mod replaced. The events those blocks fired were
  reported orphaned. `double_sided_gold` and a mobilization group's `icon` logged the same.
- **Key collisions** (`Duplicated key`): `law_communal_administration`, `building_copper_mine`, and the modifier
  types `building_copper_mine_throughput_add` and `goods_output_fine_art_mult`, all now vanilla's.
- **Removed or renamed:** the four ideologies `modified.txt` replaced, the party its join weights injected into,
  three scripted triggers and values those ideologies used, the journal panel's `CanComplete` family and the
  `IsDoubleSided*` bar looks (2,080 failed lookups a session from one system tab), two ship-template tooltip loc
  keys, `Character.GetRepairingTexture`, the budget panel's average tax collection breakdown, and
  `ideology_icons/authoritarian.dds`.
- **The map.** The mod's 1.14.5 copies of the 17 state-region files broke vanilla's new Russian states:
  `Province crossing multiple state regions`, history naming states the copies lacked, Russia's formations failing.
- **`|q`.** `missing required quote-escaping` was confirmed (283 lines), including plain-looking `$X$` references
  in vanilla-copied keys, which turned out to sit inside function arguments too.
- **New since 1.14.5:** `je_global_warming.txt:24` read a global before it existed (`Value of wrong type … none`,
  582 times); `principle_sacred_civics_1` belongs to no group; vanilla's `custom_tooltip.gui` missed two types the
  mod's stale `tooltip.gui` override didn't define. Countries already holding `je_grand_monuments` were given it
  again (1.14.5 logged that too).

## 3. What changed, by area

**Journal entries.** A one-shot converter (`scripts/generators/convert_je_outcomes.py`, `--check`) turned the mod's
26 old-shape entries into 46 outcomes in 20 entries: 18 success, 14 failure, 8 hidden invalid, 6 timeout. A
trigger that could never pass (`always = no`) got no outcome, which is why the prep's 49 became 46, and its dead
loc went. Each outcome has its own `conclusion_desc`. The five vanilla entries the mod replaces (three tax code,
the Opium Trade, Turtle Island) were rebuilt from 1.15's text plus the mod's lines, not converted. Fourteen test
files read outcomes through `je_test_helpers.py`. The Grand Monuments refresh now also checks
`has_inactive_journal_entry`.

**Bars, groups and mobilization.** The banking bars are two-pole styled bars (`progress_texture`,
`background_texture`, `marker = yes`). Soft Power and Covert Warfare have vanilla group illustrations;
`je_group_environment` is deleted (owner decision 3); the `training` mobilization group has a `background`.

**Politics.** Character `ideology_social_democrat` is `ideology_state_socialist` and `ideology_communist` is
`ideology_communist_leader`; the interest groups' `ideology_socialist` is `ideology_communist`;
`social_democrat_party` is `socialist_party`. `apply_ideologies.py` regenerated `modified.txt` from 1.15, and the
Armed Forces now hold Militarist where they held Patriotic. Vanilla's Communal Administration replaces the mod's
(owner decision 1): the mod's law and `pm_recallable_delegates` are gone, and its Anarchy and Collective Governance
unlocks, Elected Bureaucrats' exclusions with the machine-rule lock, and -2 Legislative Override Capacity are
injected. The ten new laws each got their nearest sibling's mod lines (Labour Suffrage counts as a voting law;
Okhrana, Third Section and the Extraordinary Commission as Secret Police; Caesaropapism as State Religion), 22
plain reads became `has_law_or_variant`, vanilla's citizenship changes were ported, and Subjecthood got back the
Colonial Administration unlock the restated copy had lost.

**Copper and lead (owner decision 2).** Vanilla's `copper` good and `building_copper_mine` replace the mod's mine,
which is deleted. The mine is injected into the mod's discoverable mining group, with its maintenance and tailings
groups, ten late-tier methods copied from the lead mine, and bulk rail. Copper is named "Conductive Metals" and lead
"Base Metals". 46 inputs that stood for conductors moved from lead to copper (motors, telecoms, appliances,
electronics, robots, aircraft, bandwidth, launch vehicles, the space elevator) at the same quantity and cost; 20
stayed on lead (munitions, glass and porcelain, rubber, fission and fusion shielding, generic ore). Eight of the 52
replaced methods vanilla changed were re-based. Companies, customs and the tax code learned copper, and carbon
accounting was regenerated for vanilla's fuel cuts, which renamed some capture variants.

The producers split as follows. The mod's old copper mine ran the lead mine's method groups, so it made lead; the
copper mine now makes copper, and so do Sumitomo's Besshi mine (25, was lead) and the Kirgizian smelter (30, was
iron). The lead mine, the mod's Precious & Minor Base Metals mine, BHP's Broken Hill and generic ore processing
stay on lead. The ocean mines split their old lead output 2:1 copper to lead, and the space mine, space colony
mining and self-replicating miners 3:2, at the same total.

**The map.** `map_data/state_regions/` regenerated from 1.15: KAUNAS is LITHUANIA and TARTARIA is SARATOV (pure
renames), GALICH is VOLOGDA (259 of its 282 provinces), TULA (id 575) and KOSTROMA (id 834) are new, CHUKOTKA is
merged into KAMCHATKA. `resources.py` now fails on a config key that matches no state, deletes copies vanilla no
longer ships, and folds the mod's deposits into vanilla's by the building's group (the larger figure wins, never
both). Where vanilla now puts its own copper belt on a state the mod gives one (Katanga, Zambia, Antofagasta), the
config removes vanilla's so the two don't stack. Every state list and generator followed: formable regions,
tourism, Local Climate, Demographics, region areas, Planned Capital, capital bloc names (with both translation
memories), seabed basins, Largest Cities.

**Loc.** Every `$key$` inside a quoted loc function argument carries `|q`: 266 splices in 14 files, 1,014 in the
translation memories, and the generator that writes power bloc unlock texts. Check 9 in
`check_localization_files.py` fails CI on one left unescaped, in loc and memories alike. The vanilla-copied keys
in `replace/` were re-synced to 1.15; `[concept_zaibatsu]` is `[glossary_zaibatsu]`.

**GUI.** With no 1.14.5 base, each changed override was rebuilt as vanilla 1.15 plus the mod's own hunks (found by
`git blame`) and proved line for line against the new vanilla file; nothing was 3-way merged. That covers the
journal panel, tooltips and system-tab bars; the budget, goods, building, market, states, production-method and
population panels; and the military, politics, power bloc, right-click and treaty panels. The budget panel takes
1.15's per-state Unrealized Taxes list. The law-effects generator handles 1.15's comparison view. Two deviations
were kept with their reasons written down: mobilization groups one to a row, and principle groups one to a row.

**Tooling.** The audits and lint read 1.15's shapes (outcomes, styled bars, glossary links, the new one-time
event fields, `list_scopes`), and `loc_coverage_audit` gained a structural outcome check that all 927 vanilla
outcomes pass. An `INJECT:` adds an outcome rather than merging into one. `vanilla_parsed/` snapshots the
glossary, regional exile pools and AI ship categories. A render guard stops `docs/engine/` being re-rendered from
engine docs newer than both the snapshot and the installed game. `docs/engine/` now lists only the engine's own
modifier types and custom loc: the foundation render had committed 925 of the mod's types, which the server
unions in for its endpoints, and a test of a script-only type caught it.

**Script sweep and defines.** The mod's three devastation overrides go, for 1.15's battle-based devastation;
`INCOHERENCE_FACTOR` stays at 2 (vanilla went from 5 to 2.5). No `$ARG$` is left inside a `debug_log` string: 20
lines in 12 helpers pass their arguments through `te_log_args_set` (`te_debug_log_arg_effects.txt`), and
`test_debug_log_arguments.py` keeps it so. 1.15 re-runs `on_entry_into_force` with `scope:is_renegotiation` set,
for an article carried over and for one a renegotiation adds. Intelligence Sharing skips its +1 infamy then (an
added one charges none, accepted), Seize and Disband Company rely on `exists = input_company` (a carried-over
copy's company is gone, while an added one must still run), and state-modifier articles remove before they re-add. The UN docket counts a war victim by `enemy_occupation > 0.25`, and its strike lists
follow 1.15's new plays. Decolonization's subject-war tracker skips wars with the overlord's own revolutionaries.
The mod's ships take 1.15's construction goods in their modules, and its submarines use
`ai_ship_category_submarines`. The Subjugate replacement ports 1.15's checks, the scripted rules were re-copied,
the Imperial Circle bloc-name replacement went (vanilla now gates it itself), and `formation.17` was re-synced.
Labour Suffrage joins the lists that mean "holds elections", and Religious Mission Rights reads State Religion
with its variants. Global Warming reads its temperature global only once it exists (the 582 log lines). The four
old-save repairs marked for 1.15 are retired, as 1.15 saves don't carry over. Two new vanilla engine lines moved
onto the census's script-only types: the Extraordinary Commission's wealth mortality and Social Revolution's
working-adult share. The known-noise registries carry 1.15's source lines.

**Probes.** A hidden journal entry on one AI major power answers C3, C5, C7, C19, C20 and part of C21 within four
months of any game (`TE_PROBE_115` lines). The play-test list says how to read them and what to delete afterwards.

## 4. Release-day answers, and where the prep was wrong

- **C1:** old journal entry fields are rejected (§ 2). There is no compatibility path.
- **C2, how an outcome maps:** `trigger` takes the old `complete`/`fail`/`invalid`, `effect` the `on_*` block;
  `header` and `effect_header` take the custom headers or the `je_standard_*` pair; `event_outcome_<kind>_desc` and
  `_effect_desc` become `event_outcome_desc` and `event_outcome_effect_desc`; every outcome needs
  `conclusion_desc`. Invalid is `flags = { hidden invalid_outcome }` and timeout `flags = { timeout }` with no
  trigger, at most one each, a timeout outcome being required when `timeout = N` is set.
  `event_outcome_activated_*` stays at entry level. An entry with no outcome never concludes.
- **C3, precedence between two outcomes true at once:** undocumented, and vanilla's own orders vary. The mod puts
  success first; the probe settles it.
- **C4, the panel:** outcomes come from `JournalEntry.GetOutcomes` and `JournalEntryOutcome.*`; all eight custom
  widget containers survive, `custom_widget_container_buttons` is new and hides the scripted-button grid, `_4`
  moved into the description column. The tooltip nesting the prep rated high risk lives in loc, so it carried over.
- **C5, bar looks:** `IsDefault`, `IsDefaultBad`, `IsDefaultGreen`, `IsDynamic`; a two-pole bar is styled fields.
- **C6:** a journal entry map mode has no GUI hook; it is code-driven.
- **C15:** a journal entry group needs `illustration` (`themed` optional); a mobilization group needs `background`.
- **C16:** 782 state regions (781 before). The Modding-Digest lists Chukotka as added; it was removed. Cold fields
  are on 525 of 676 land states and 28 of 106 seas, not every state as the prep assumed. File names, strategic
  regions and straits are unchanged; 1.15 kept the same 106 sea regions.
- **C17:** see Politics above. The Nomenklatura is the Intelligentsia reorganized, not a ninth interest group.
- **C19:** the `|q` errors fired as the prep expected. No `$ARG$`-in-quotes line fired in the two months run, so
  whether 1.15 substitutes inside quotes is the probe's to answer.
- **Not as planned:** the prep's 49 conclusion texts were 46 (above); the mod's copper deposits would have opened
  10,714 capped copper levels in 1836 against vanilla's 609 had the mine stayed in vanilla's capped group.

## 5. Owner calls this leaves open

- **Copper deposits discoverable.** The mine moved into the mod's discoverable group so the mod's endowments arrive
  through discovery, as its other mines' do; vanilla's caps are the discovered part. Left capped they would all
  be open in 1836. Unverified in game: a once-a-game `TE_SELF_CHECK OK|BROKEN copper_mine_discoverable` line
  answers it, and the fallback is a `TRY_REPLACE` of vanilla's entry (play-test list).
- **Communal Administration's old extras** (Trade Unions and Rural Folk +10% political strength, -5% radicalism,
  -10% tax capacity) were left off; vanilla's law has its own balance. Restoring them is three lines.
- **BHP's Broken Hill** stays on lead (it is silver, lead and zinc), though vanilla moved BHP's company to copper.
- **The 8 hidden invalid outcomes** each have their own conclusion text; they could share a standard key instead.
- **The states panel:** vanilla's new Cold tile sits beside the mod's Local Climate tile. **The market panel:**
  vanilla's Monthly Price Report stays out, where the mod's trade charts stand (the mod's copy never had it).
- **The tooltip header** lost vanilla's `margin_top = 5` in the rebuilt `tooltip.gui`, as the mod's copy had.
- **Two panel hints went with the old fields.** The Nuclear Weapons Program's "First Nuclear Weapon Created and
  Stockpiled…" / "Additional Nuclear Weapon Created…" and Solar Colonization's "A new colony has been established
  in the solar system" were `on_complete` tooltips under a `complete = { always = no }`. They only told the player
  what filling the bar does. The converter drops a never-true ending, so the three loc keys went too. Restoring
  them is an outcome with `trigger = { always = no }` holding the tooltip, if 1.15's panel shows one.
- **Battle and growth numbers 1.15 moved under the mod.** Fixing the double-counted kill rate halves every one of
  the mod's 29 kill-rate sources, so battle deaths (and the census's war deaths) roughly halve: scale them up?
  Base literacy growth went from 0.0005 to 0.002, so the mod's 17 literacy-growth adds went from about a tenth of
  it to a fortieth: retune? `military_formation_interest_gain_mult` now applies, up to +90% at the mod's
  investment cap. The mod's 32 `unit_devastation_mult` values meet the battle-only model. `INCOHERENCE_FACTOR`
  stays at 2, still cheaper than vanilla's 2.5.
- **Ship costs.** The mod's ships follow 1.15's move of goods into modules at the same multiple of their vanilla
  analogue, which raises them about 20% (carriers 42%); holding totals flat would have priced the Fleet Carrier
  below the vanilla carrier it succeeds.
- **Collective Governance under Labour Suffrage** gets no amendment until Labour Suffrage joins both
  `collective_governance_is_popular` and Collective Governance's `unlocking_laws`, which a test pins equal; adding
  it changes who may enact the law.
- **Design calls from the new laws**, with the sweep's recommendation: whether a council republic counts as democratic in the world war triggers,
  whether Internal Colonization joins the colonization-law lists, and whether Revolutionary Guard unlocks the
  reserve cadre. Leave the first (Labour Suffrage needs a Council Republic, which the communist check already
  catches), don't add the second (it settles an internal frontier, like Frontier Colonization, which the lists
  leave out), and yes to the third (a militia and conscription army, like the two laws that unlock it now).

## 6. Follow-ups

Filed as issues from the PR: the features in the prep's § 4 and § 7 (scaling modifiers, map modes,
`disable_evaluation` on the mod's 28 entries, `fire_only_once` for cooldown variables, more outcomes than
complete and fail); copper where the mod still lacks it (grid buildings, nuclear and fusion wiring, a Strategic
Reserve good, a prestige good, vanilla's copper and lead split in the mod's munitions); `gui_reference_audit`'s
built-in list with the game configured; `je_multiplier_scope_audit` and `scaling_modifiers_while_active`; and
retiring `convert_je_outcomes.py` once nothing needs it.
