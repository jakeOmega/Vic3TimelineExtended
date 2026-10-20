# Demographics play-test checklist

What the next play-test of the Demographics rule should look at. Since 2026-10-12 the owner's in-game checks no
longer gate a merge: a PR lands on the offline gate (CI, the audits, the golden tests, the harness), adds what only
the game can show here, and the play-test before a release works through the list. Where a build rests on an engine
fact nobody has verified, it ships the preferred version with a self-check line in `debug.log` and names its fallback
below; a BROKEN line means swap the fallback in.

Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`). Check the playset has no Workshop copy of
  the mod.
- **Rule.** The Demographics (Experimental) rule is chosen in the lobby: Disabled (the default, and every release),
  Display only, or Full. Each item names its setting.
- **Console.** Vic3's console has no `effect` command: the census's console is `event te_debug_demog.1`, on the
  player's country, with lettered options (the list is at the top of `events/te_debug_demog_events.txt`).
- **Logs.** Read `debug.log`, not `error.log`. Grep it for `TE_SELF_CHECK` first, then `TE_DEMOG`.

## Self-checks (every game; each row's When names the rule settings it runs under)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … primogeniture_scaled` | once a game: `START` when the first state with a farm share between 0.1 and 0.9 takes Primogeniture's farm line fresh (a Primogeniture country's first yearly state pulse), the verdict a week later | the engine sums a script-only type on a state modifier scaled by its multiplier (`added` ≈ `expected`) | `added` reads 0.1 (the multiplier is ignored) or 0 (the type isn't summed): Primogeniture's farm births, and since phase 3 Forced Heirship's (outside Full), are wrong in every game | Plan B of `docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md`, Task 9, for both modifiers |
| `TE_SELF_CHECK … workforce_amendment_type` | any rule, development builds only (a release comments the inputs out and turns the check off): once a game, a week after a country first holds Community Service or Mandatory Minimums on its criminal-justice law | the engine sums a script-only type from an amendment into a state's read (`read` = `expected`) | `read` = `laws_only`: the two amendments' moved working-adult lines are lost in every game, and since 2026-10-17 so is Undivided Farm Succession's Late Marriage line | revert both amendments' blocks (`common/amendments/extra_amendments.txt`) to `state_working_adult_ratio_add` at their old values, list them in `P.LIVE_WORKFORCE_LINES` and take them out of `TestWorkforceLinesMoved.BLOCKS` (phase 2 step 1 plan, D12); for Undivided Farm Succession, take its `state_late_marriage_farms_add` off the amendment and have `te_demog_pr_target_lm` (`gen_demographics.py`) add 0.15 × the farm share again where the owner has `te_inh_has_undivided_farms` |
| `TE_SELF_CHECK … workforce_ig_trait_type` | any rule, development builds only: once a game, a week after a country's Trade Unions are first loyal at the trait's plain size (clout neither marginal nor powerful) with no Ministry of Labour law | the engine sums a script-only type from an IG trait into a state's read (`read` = 0.02), and the INJECT added to vanilla's trait block (`remainder` about 0) | `read` 0: the type isn't summed; `remainder` about −0.05: the INJECT replaced vanilla's block. Either way the Trade Unions' two loyal traits' lines are lost in every game | delete `common/interest_group_traits/te_demog_workforce_injections.txt` (vanilla's +0.05 comes back on the engine field), list the two traits in `P.LIVE_WORKFORCE_LINES`, take them out of `TestWorkforceLinesMoved` and accept their two `vanilla_parsed` carriers as live |
| `TE_SELF_CHECK … workforce_lines_net` | any rule, development builds only: once a game, a week after the first country's first monthly pulse, in its capital | the capital's working-adult field less the moved lines' pair is about 0: every vanilla carrier's INJECTed cancel nets out against its own line | `remainder` not 0: an INJECT replaced a vanilla block (a law, Woman Soldiers or a Trade Unions trait), so its cancel stands alone in every game (or the capital has Rosen's androids, which can't happen in 1836) | revert that carrier's INJECT and list it in `P.LIVE_WORKFORCE_LINES`; option l's `TE_DEMOG_MODS` lines show which carrier |
| `TE_SELF_CHECK … famine_reserves_absorbed` | any rule, development builds only: once a game, a week after the first country whose Landowners are powerful and whose capital has a subsistence-farm pop reading Famine Reserves at its farm (1836 India: the first monthly pulse), on one such pop (`te_debug_demog.40`). No line in a game's first weeks isn't BROKEN: it arms at the first monthly pulse and logs a week later | what the census absorbs for the pop (its owner's read of the agriculture mortality key) equals what the walk reads at its farm (`absorbed` = `walk`, both about −0.2: the trait's −0.1 doubled by the group's power) | `absorbed` 0: a `building_group_*` key reads 0 at country scope, so under Full the census absorbs nothing of the trait and India's deaths stay off. `walk` = `ratio` × `absorbed`, the ratio 2 or 0.5: the group's power reaches one read and not the other | absorbed 0: set `COUNTRY_ABSORBED_FROM_FARM = True` in `demographics_params.py` and regenerate (`gen_demographics.py`): the census absorbs the farm's own read on subsistence farms only, which holds no building-scope line, and commercial farms' workers keep the trait on top. A ratio: set `COUNTRY_ABSORBED_SCALE` to it and regenerate. Either way refit (the spec's §3) |
| `TE_SELF_CHECK … working_conditions_read` | any rule, development builds only: once a game, a week after the first country with a mine of `bg_mining` itself (not the mod's discoverable mines) where working conditions apply at half their size or more (`te_debug_demog.41`: 1 + the building's `building_working_conditions_mult` at least 0.5, so Workplace Safety below three) | the mine's read of working conditions' laborers line is the table's 0.1 × that scale (`read` ≈ `expected`; `scale` 1 in 1836): the group reads the walk takes working conditions through carry the table, so the walk counts it once. Built since 2026-10-17, when the first line read `read=0.100` at a Walloon mine and the walk still added the table on top (§ Log triage 2026-10-17) | `read` 0 against `expected` about 0.1: the read can't see the table there, so the walk misses working conditions | put the table back in `te_demog_pop_death_mult` (`gen_demographics.py`, `engine_rate_terms`) as each row × the workplace's 1 + `building_working_conditions_mult`, and regenerate |
| `TE_SELF_CHECK … malaria_trait_read` | any rule, development builds only: once a game, the first month a country with Quinine owns a state the map files give the mild malaria trait | `has_state_trait` still reads the trait there (`trait_read=1`, `level=1`), though Quinine has switched the trait's modifier off: the malaria factor lasts until Malaria Prevention, as built | `trait_read=0`: the trait test stops at Quinine, so the census's malaria factor ends with it in every game | set `MALARIA_READS_REGION_LIST = True` in `demographics_params.py` and regenerate: the census reads the level from the state regions the map files give the traits (`te_demog_malaria_level_listed`) |
| `TE_SELF_CHECK … pop_workforce_read` | Display only or Full: once a game, at the first country monthly pulse after a capital's walk | a pop's `workforce` reads as a value in the walk (`wf_engine` about 0.2-0.3) | `wf_engine` 0: the walk can't read the engine's workforce | nothing in step 1 uses it; step 2's stop rule (spec §1.8) needs another read of the engine's workforce before its fit |
| `TE_SELF_CHECK … measure_country_types` | once a game, under Full: `START` when the first measure that moves desired family size goes on in any country (Child Allowance, Honours, Parental Leave, Later Longer Fewer, Birth Limit, the Crash Campaign; the AI's included), the verdict a week later from the capital (`te_debug_demog.10`) | the capital's read of the script-only `state_desired_fertility_mult` rose by the measures' lines its owner gained (`added` ≈ `expected`): a script-only state type on a country static modifier reaches the states | `added` reads 0: the census will never see any measure's types (step 3b reads them); `NO_VERDICT` (the measure ended within the week) re-arms the check | put each measure's census types on a state modifier in each of the country's states, applied and removed with the country modifier and re-applied by the yearly state pulse (inheritance's rural modifiers' pattern), and keep the interest groups and upkeep on the country |
| `TE_SELF_CHECK … primate_state_flag` | once a game, under Full: at the first census of a country of three census states or more (game start or 31 December) | its largest city reads as primate (`self=1`) and no other of its states does (`states=1`): a state's `owner = var:te_dg_primate_of` compares its owner with the country the census stored | `self=0` (the comparison never holds: no state takes Primate City, all take Provincial Neglect) or `states` above 1 (it always holds) | compare by numbers instead: the census writes its year on the largest city (`te_dg_primate_year`) and `te_demog_up_is_primate` reads `var:te_dg_primate_year = owner.var:te_dg_census_year`, clearing the year from the country's other states as it clears the flag now (a state that changed hands within the year can read as its new owner's largest city until that owner's census) |
| `TE_SELF_CHECK … planned_capital_moved` | once a game, under Full: `START` when the first country (the AI's included) founds a planned capital, the verdict a week later (`te_debug_demog.60`) | the capital stands in the chosen site: the generated dispatcher's `set_capital = STATE_X` moved it. `penalty=` says whether the base game's Moved Capital Recently came with the move (1) or not (0); `at_once=` whether the capital had moved by the end of the option | the capital is still the old one and never moved (`at_once=0`): the move never happened. `NO_VERDICT` (the capital in neither state, moved at once and back again within the week, or a state changed hands in the week) re-arms the check | re-run `scripts/generators/gen_planned_capital.py` if the site's region is new; if the engine refuses the move, the decision instead marks the site and asks the player to move the capital there with the base game's Move Capital map interaction within a year, and the development modifier and the costs follow the move (an AI keeps its capital) |

No `primogeniture_scaled` line at all after a game's first year means no state took the line fresh: no country had Primogeniture, or the game was continued from a save where every Primogeniture state already held it. Start a new game, or enact the law. A `START` with no verdict means the state changed hands within the week; the check doesn't run again in that game. No `primate_state_flag` line means no country of three states or more ran a census under Full. No `planned_capital_moved` line means nobody founded a planned capital (take the decision, or watch an observer run past Steel-Frame Buildings); with `penalty=1`, the base game's own move penalty stacks on the decision's costs, so consider lowering the authority cost. No `measure_country_types` line means no measure that moves family size went on (start Child Allowance under Pro-Natalist Policy); a `START` with no verdict, that the capital changed hands within the week.
| `TE_SELF_CHECK … measure_country_types` | once a game, under Full: `START` when the first measure that moves desired family size goes on in any country (Child Allowance, Honours, Parental Leave, Later Longer Fewer, Birth Limit, the Crash Campaign; the AI's included), the verdict a week later from the capital (`te_debug_demog.10`) | the capital's read of the script-only `state_desired_fertility_mult` rose by the measures' lines its owner gained (`added` ≈ `expected`): a script-only state type on a country static modifier reaches the states | `added` reads 0: the census sees none of the measures' types, so no measure moves births (step 3b's census reads them from the state); `NO_VERDICT` (the measure ended within the week) re-arms the check | put each measure's census types on a state modifier in each of the country's states, applied and removed with the country modifier and re-applied by the yearly state pulse (inheritance's rural modifiers' pattern), and keep the interest groups and upkeep on the country |
| `TE_SELF_CHECK … workforce_ratio_scale` | Display only or Full: once a game, at the first capital census step before any workforce term (a 1836 game: its first year) | the walk's `wf_engine` is nearer `per_people` (the set ratio as workforce over people: about 0.25 in 1836) than `per_dependents` (the same as workforce over dependents: about 0.20). The spec §1.8's stop rule, as built | `wf_engine` near `per_dependents`: the engine's ratio is workforce over dependents | re-derive `WORKFORCE_SCALE` and W on that scale (spec §1.8) and refit with `demographics_harness.py workforce SAVE`. Offline the 1836 save already reads over people: 82% of the world's people hold exactly 0.250 (§ Phase 2 step 2) |
| `TE_SELF_CHECK … workforce_follows_target` | Full: once a game, at a capital's census once its workforce term has run five census years and the ratio its pops are set to (`set`) stands at least 0.03 from the walk's engine figure when W landed (`engine_at_landing`) | the engine figure has covered at least half of that move (`engine_moved` ≥ `needed`, half of `to_set`); `census_target` says how far the ramp still has to go. Not W's own move: W lands from the moved lines' pair, which the engine may not have reached, so a W falling back to the engine asks nothing of it (the 2026-10-17 line's false BROKEN, § Log triage 2026-10-17). Not a gap alone either: the saves show the game's figure sitting 0.01-0.03 off its ratio in steady state | `engine_moved` under `needed`: the engine's pull is slower than the ramp, so the ramp adds nothing | set `WF_RAMP_STEP` large (the term lands at once, and the engine's own pull is the lag) and keep the panel's engine figure beside the target; no line at all after many years means no capital's set ratio moved 0.03 from its engine figure at the landing (option r shows the capital's `set=` and `engine=`) |
| `TE_SELF_CHECK … conscription_term_read` | Full, while conscription's effect is on (`CONSCRIPTION_EFFECTS`: on since the migrant booking, 2026-10-12; step 4 shipped it held back, with no line): once a game, a week after the first state takes a fresh conscription pair (its term at least 0.01 either way) | the census's conscription pair reaches the state's conscription multiplier (`added` = `expected`, the term) | `added` 0: the pair doesn't reach the state's read. Another figure: a technology or law moved the field inside the week, which says nothing either way: read the state's conscription tooltip for "Census: Fighting-Age Men" | for `added` 0, put the term on `state_conscription_rate_add` as T × the state's own rate (`modifier:state_conscription_rate_add`, read in the refresh, ROOT the state). Whether the read moves the state's conscript battalions is item 2 of § Phase 2 step 4: no script reads them |
| `TE_SELF_CHECK … unemployment_rate_read` | Display only or Full: once a game, the first census state whose walk counts more than 2% of its workforce idle (`walk=`: the walk's own count, the workforce of pops with no workplace over all the workforce, `te_dg_unemp_walk`) | the engine's `state_unemployment_rate` (`read`) is within a quarter below or a third above `per_people` (`walk` × `wf_share`, the walk's workforce over people): the engine's figure is the idle workforce over all the state's people, so the conversion the census stores (`census=`, `te_dg_unemp`: `te_state_unemployment_share`, which the youth bulge, the event wave, the pension AI and the panel read since 2026-10-17) is the share of the workforce, and `census` ≈ `walk`. The same comparison as `unemployment_share_read` (`docs/testing/ai-economy-playtest.md`), made from the census's walk: one engine fact, read twice. The 2026-10-17 line read `read=0.048 pops=0.195` (§ Log triage 2026-10-17) | `read` not near `per_people`: the engine's figure is not per person, so the conversion is wrong for the census and for every other reader | store `te_dg_unemp` from the walk's own count again (`te_dg_unemp_walk` in `te_demog_work_walk_store`, the first round's build) and take `unemployment_share_read`'s fallback for the other readers; correct the notes (`scripting_best_practices.md` § The op slots, `te_demog_consequence_values.txt`) |
| `TE_SELF_CHECK … family_limitation_scaled` | Full: once a game, `START` when the first country's Family Limitation line goes on fresh at 0.02–0.3 (a neighbour of France gaining the practice, usually in the first few years), the verdict a week later from its capital (`te_debug_demog.90`) | the capital's `state_fertility_means_add` rose by the line (`added` ≈ `expected`): the engine scales a script-only state type on a country modifier by its multiplier, and the states read it. The type-on-a-country half is already seen in saves: France's states read history's 0.6 in their means | `added` about 0.6: the multiplier is ignored, so every country's line reads 0.6 once it has any; about 0: the type doesn't reach the states, so no country's practice counts. `NO_VERDICT` (the capital changed hands, or the line came off within the week) re-arms | put the line on a state modifier in each of the country's states, applied by `te_demog_fl_apply` beside the country one (the measures' fallback pattern); or, for an ignored multiplier only, a ladder of static modifiers at tenths of the line |
| `TE_SELF_CHECK … fl_neighbours_read` | Full: once a game, at the first Family Limitation step (31 December 1836) of a country the state-scope test says has a foreign neighbour | `every_neighbouring_state` from country scope returns the states across its borders (`foreign` above 0). `own` above 0 says it returns the country's own states too, which the step leaves out either way | `foreign=0`: the practice never spreads | walk the country's own states and each one's `every_neighbouring_state` in `te_demog_fl_step` (a border state then counts once per own state it touches) |
| `TE_SELF_CHECK … neighbouring_state_reads` | Full or Display only: once a game, at the first country census on 31 December | `every_neighbouring_state` from a state returns a land neighbour (Ulster sees Leinster): Late Marriage and Birth Spacing spread. `strait=1` says it crosses the Ulster–Lowlands strait too, so islands spread with their neighbours across the water; `strait=0`, only through their own conditions (the late-marriage spec 4.4 allows either) | `land=0`: the practices never spread | set `PRACTICE_SPREAD` to 0 in `demographics_params.py` and regenerate (`gen_demographics.py`), so the code says what the game does; with `strait=1`, run the harness's replays with `--straits` |
| `TE_SELF_CHECK … wave_timed_country_type` | Full: once a game, `START` when the first of the event wave's four census-line options is chosen (Missing Girls' ban or payments, `code=1`; The Last Generation?'s licences or payments, `code=2`), the verdict a week later from the capital (`te_debug_demog.81`) | the capital's sum of the type (`state_sex_ratio_at_birth_add` or `state_desired_fertility_mult`) rose by the option's line plus any change in the Family Policy measures' lines of that type (`added` ≈ `expected`): a script-only state type on a timed country modifier reaches the state | `added` 0: the census never sees those four options' lines, so they change no birth, nor the women's-work lines the Baby Boom's and the Greying's options carry on the same kind of modifier; `NO_VERDICT` (a measure offset the line within the week) re-arms the check | add each of the four modifiers (and the three women's-work ones) without `days` and store its end date on the country (`te_dg_wv_<modifier>_until`); `te_demog_wave_yearly` removes it when the date passes and puts it back for a revolution's winner that holds the date (the measures' pattern, `te_demog_ms_keep_all`) |
| `TE_SELF_CHECK … cause_deaths_estimate` | Display only or Full: once a game, at the first census step of a state with at least 1,000 deaths from natural causes and no late game (issue #1029) | the estimate the pie's shares come from, the four causes' rates over the bands last counted, matches the sweep's own deaths (`fit` 0.9–1.1; the model's states read 0.97–1.00), and the slices add up to the deaths, the war dead and the killed (`slices` = `deaths` + `war` + `killed`) | `fit` outside 0.9–1.1: the bands at the step's start aren't the people the sweep killed, so every pie leans; slices that don't add up: a slice read a stale figure | count deaths by cause in the sweep itself (issue #1029's method b): each age group's deaths split by its own causes' rates in `te_demog_sweep` (generated), summed into the eight slices, and drop the estimate and its fit (the late sweep already counts its own this way: `te_demog_lx_cause_deaths`) |

No `unemployment_rate_read` line after a few years under the census means no census state counted more than 2% of its workforce idle: option t's `unemp=` is the capital's stored conversion and `unemp_walk=` the walk's own count (since 2026-10-17); compare them with the state panel's unemployed in a state with visibly idle workers.
The two workforce carrier checks may not fire in a short game: console option p (phase 2 step 1, below) sets up both
carriers in the player's country. **Woman Soldiers and Pollution Impact** carry their moved working-adult lines as a
script-only type on a modifier at a multiplier (×0.5, × the region's impact), the fact `primogeniture_scaled` tests:
if that line reads BROKEN, revert Woman Soldiers' block (`common/static_modifiers/te_demog_workforce_injections.txt`)
and Pollution Impact's line in `common/static_modifiers/extra_modifiers.txt` to the engine field too, and the Trade
Unions' two traits, which the engine scales ×0.5 while the group is marginal and ×2 while it is powerful.

## Late Marriage and Birth Spacing (#906)

1. **Full, a new 1836 game as Britain.**
   - The Population panel's children-per-woman tooltip shows "Late marriage ×0.90" and "women marry at about 26",
     with "Birth spacing ×1.00". The country line reads about 26 and 0%.
   - A Japanese state's Demographics subtab: Birth spacing ×0.80, Late marriage ×1.00, women marry at about 19.
   - A Chinese state: Birth spacing ×0.99.
   - A state in Posen: Late marriage ×0.92 (a share of 0.8), women marry at about 25.
2. **Option l** on the capital after its first census step: `lm=1.000`, `bs=0.000`, `lm_target` near 1 (an
   unincorporated state reads `lm_target=-1.000`), and
   `absorbed_b` holding 0.1 × the capital's agrarian share on top of the laws' own absorbed birth lines.
3. **Disabled, a new game, a farming state in Britain** (Primogeniture). After its first yearly pulse, its birth-rate
   breakdown shows Primogeniture's farm births at +10% × its Peasants' and Farmers' share, as a Laws and Institutions
   line, and no "Cadet Sons Leave the Land" birth line. The modifier still shows its migration line. (The self-check
   above tests the same thing from the log.)
4. **Full, the same state after its first census step:** no Laws and Institutions birth line, Census: Births present,
   and option n's `q_b` at 0.
5. **A split state.** Release or annex part of a state region (debug). At its next census the new state's option l
   shows its sibling's `lm` and `bs`, not the start table's.
6. **A whole state region changing hands** (a debug transfer, or a revolution that wins). At the new state's first
   census, option l shows the old state's last `lm` and `bs` (the region's copy). Option q answers whether
   `on_state_owner_change` still sees the old state's variables: if it does, a follow-up can carry the census's ring
   and medicine through conquests too.
7. **An old save** made under Full before this build: each state's tooltip shows ×1.00 for both practices until its
   next yearly pulse, then its seed.
8. **Fast mode** (option h) for a few clock years: the capital's `lm` moves once a clock year, toward `lm_target`.
9. **`debug.log`:** no error from `te_demog_practice_effects.txt`, the generated `te_demog_pr_*` values, `region =
   sr:` or `state_region = s:` lookups ("Invalid strategic region"), or `te_demog_events.4` fired from the rural
   refresh.
10. **Two yearly plain-text saves of the Full game:** keep them. The harness's `practices-check` (not built yet; the
    late-marriage plan, Task 12 Step 2) compares each state's stepped shares with the model's.
11. Optional, for phase 3: does `every_neighbouring_state` from a British state include a French one?

## Medical Outreach (#929)

1. **Full.** Issue Medical Outreach in a state behind its medicine targets. Once the state has caught up, the decree
   ends on its own; the decree panel names the reason as "This state's medicine is still behind what our technology
   and laws allow", not a raw comparison.
2. **Full, an observer run of a few decades:** AI countries issue it in states behind and let it lapse; few states
   hold it once caught up.

## Phase 2 step 1: the interfaces

The census computes who works, the pensioners, health need and the old-age threshold, and every working-adult line
moves to two script-only families re-applied by one "Laws and Institutions" pair. No birth, death or workforce number
should move in any game. Spec: `docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md` §1.10;
plan: `docs/superpowers/archive/plans/2026-10-12-demographics-phase2-interfaces.md`, Task 8. The three workforce self-checks
are in the table above.

1. **Nothing moves (Disabled).** A Women's Suffrage country's state shows the same working-adult ratio as a game on
   `main` (option l's `wa_mod=`). Its workforce tooltip shows one "Laws and Institutions" line; the law's own tooltip
   still reads "Workforce Ratio +15%".
2. **Laws refresh that day (Disabled).** Enact Women's Suffrage by the console: the pair (`ww_mod=` and `pair=`)
   follows the same day. Raise Old Age Pension's institution level: the line follows within a month.
3. **Under Full the pair stays.** After a state's first census step (its births and deaths term in force), `ww_mod=`
   and `pair=` still hold the families' sum and the workforce tooltip still shows the line.
4. **The figures in 1836 (Display only or Full).** Option l in Britain's capital after its first count: `wa_share`
   about 0.7, `at_work` about 0.45-0.5, `wf_target` about 0.25, `wbase` about 0.25, `old_age` about 58-62, `need` about
   1.0, `pensioners` 0, `pension_kind` 0, `child_work` 0.3 (Child Labor Allowed).
   - **`wf_engine`, step 2's stop rule** (the engine's workforce over people). About 0.25 confirms the census's reading;
     about 0.20 means the engine's ratio is workforce over dependents (as the define's and the modifier's descriptions
     read), and step 2 re-derives the scale and its term on that scale before any fit (spec §1.8). Read it in a few
     states, and in one with many aristocrats or slaves (`wbase` away from 0.25). The `pop_workforce_read` self-check
     says whether the read works at all.
5. **A pension country.** A country with Old Age Pension: `pension_var=65` (the owner's variable, read through the
   `owner.var:` chain) and `pensioners` above 0; a country without one: `pension_var=-1`. Switching the welfare law to
   UBI makes `pension_var=-1` that day and `pensioners` read 0 at the state's next count.
6. **The skew probe** (options f and g, unrun since #828): how fast a working-adult modifier moves a pop's workforce
   share. Step 2's plan is written after this result (spec §2.1): an instant pull needs a ramp, a slow one a lag on the
   panel.
7. **The benchmark** (option d): the step's cost within 25% of `main`'s.
8. **`debug.log`:** no "Failed to fetch variable" or script errors from `te_demog_work_*`, `te_demog_women_rate`,
   `te_demog_old_age_pass`, `te_demog_slot_births`, `te_demog_workforce_lines_refresh` or `te_debug_demog_wf_*`; no
   load error from the two new INJECT files (`te_demog_workforce_injections.txt` under `interest_group_traits` and
   `static_modifiers`) or from `te_debug_demog_triggers.txt`'s define reads.
9. **Call 3's carriers reach a state (option p).** In a new game under Display only (so the self-checks run too), in
   a country whose Trade Unions are neither marginalized nor powerful (a marginal group's traits apply at half size, a
   powerful group's at double), run option p once. Its log gives three pairs of `TE_DEMOG_MODS` / `TE_DEMOG_WORK` lines
   (before, a day later, a month later), and within about five weeks the `workforce_amendment_type` and
   `workforce_ig_trait_type` self-checks:
   - **a day later:** `replaced=` up 0.01 (Community Service) and, once the Trade Unions are loyal, 0.05 more (the
     trait); `part_m=` up 0.01; `part=` up 0.02 with the trait; `womens=` up 0.025 (Woman Soldiers at ×0.5);
     `ww_mod=` (the families' sum) up by their total. `pair=` and `wa_mod=` (the engine's own field) haven't moved yet,
     unless option p enacted the law, which refreshes the pair that day: the month's lag of spec §1.9;
   - **a month later:** `pair=` equal to `ww_mod=`, and `wa_mod=` up by the old flat lines, as on `main`: +0.01,
     +0.05 and +0.025;
   - **the tooltips:** the Trade Unions' trait shows one "Workforce Ratio +5%" line and one "Census: People at Work +2%"
     line, not a +5% and a −5%; Woman Soldiers in the country's modifiers shows one "Workforce Ratio" line; Community
     Service shows "Workforce Ratio +1%" and "Census: Men at Work +1%";
   - **a kind that fails** (its type stays at 0 a month later, or its tooltip shows the cancel): take that row's
     fallback in the Self-checks table. A failed kind loses its line in every game, so fix it before the release.
10. **Pollution Impact, in passing:** in a polluted state of the same game, option l's `cap=` reads −0.1 × the impact
    and `replaced=` −0.05 × the same.

## Calibration step 3: the regional mortality gap

Spec: `docs/superpowers/archive/specs/2026-10-12-demographics-calibration-step3-design.md` (owner calls 1–3, 2026-10-12). Under
Full the census absorbs the Landowners' Famine Reserves per farm pop, and infection gains a malaria factor. The three
self-checks are in the table above (`famine_reserves_absorbed`, `working_conditions_read`, `malaria_trait_read`).

1. **Nothing moves outside Full.** Disabled, a new game as the East India Company: a subsistence-farm pop's mortality
   breakdown shows Famine Reserves (−20% while the Landowners are powerful), and a state's births and deaths are as on
   `main`. Display only: the same, and the Demographics subtab's figures show the malaria factor (below).
2. **Full, the East India Company's states.** After a state's first census step, option n's `rep_d` reads about the
   trait's share of the state's deaths (East Bengal: about −0.2 × its farm workers' share of the bare curve, about −0.19
   in 1841) and `md` rises by as much. The Causes of Death section's "other effects on some of its people" falls from
   about ×0.7 to about ×1.0 (the trait now moves deaths between farm workers and the rest, not out of the state).
3. **Full, a West African state with malaria** (the Gold Coast, which the map files give the trait): the Causes of
   Death section's Infection and Hunger hover lists "Malaria: ×1.08 (until Malaria Prevention)", and the row's
   multiplier is the product of the factors shown. A state without malaria shows no Malaria line. A Pacific state
   with severe malaria (New Guinea) shows ×1.13.
4. **Malaria Prevention** (by the console, or late in a game): the tech's tooltip shows
   "Malaria Control +100%". At the state's next census step the Malaria line goes (×1.00 reads as no line). Quinine
   changes nothing.
5. **An old save** made under Full before this build: each state's Infection and Hunger hover shows no Malaria line
   until its next yearly pulse.
6. **`debug.log`:** no "Failed to fetch variable" or script errors from `te_demog_malaria_level`,
   `te_demog_pop_country_absorbed_deaths`, `te_demog_f_infection_malaria` or `te_debug_demog.40`/`.41`; no unknown
   `has_state_trait` or `state_region = s:` lookups.
7. **The observer run** (Full, 1836–1901, normal speed): India's peacetime births less deaths near +8 to +9 per 1,000
   (the spec's §3 projects it), Africa's inside +3 to +8, and every other region where the spec's table puts it.

## Family Policy measures (step 3a)

The measures and their panel (`docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md` §3.3-§3.7).
Until step 3b the census reads only Free and Restricted Contraception's means lines, so births don't move for the
others; check the switching, the costs and the politics.

1. **Full, a new game; console the Family & Reproductive Policy law** (or enact it). The Demographics tab's Family
   Policy section, open after the pyramid: "Law in Force" names the law and shows the law's tooltip; each measure the
   law allows is a row with its running cost, "Off" and a Start button; the rest sit dimmed under "Under Other Laws",
   their hover naming the laws that allow them. No label, cost or term cut short ("Honours for Large Families",
   "Restricted Contraception", "Barred to 1915").
2. **Start Child Allowance** (Pro-Natalist Policy): the budget shows a new expense line of about 0.5% of GDP a year ×
   (the 0-14 share ÷ 0.3), weekly; the Devout and Trade Unions gain +1 approval; the term reads "On to <year + 5>";
   the button reads End, greyed, its tooltip "Its five-year term runs to <year>". Each 31 December the expense
   follows GDP.
3. **Honours, Later Longer Fewer, Birth Limit, the Crash Campaign**: authority falls by 50, 150, 300, 300 (the
   rebalance of 2026-10-16; Restricted Contraception 200, Birth Limit 400 once tightened to one child). Sex
   Education: the Ministry of Education's bureaucracy cost +10%. Restricted Contraception: feminist movement support
   up, and (option l) the capital's `fmeans` falls by 0.2; Free Contraception raises it by 0.1.
4. **Birth Limit's button**: Start (two children), Tighten (one child, the modifier swaps at once), then End once five
   years have run, which also ends the Rural Exemption. The Rural Exemption's Start is greyed "Needs Birth Limit in
   force" without it.
5. **The Crash Campaign**: no button ends it; five years to the month after it starts it ends with the "Crash Campaign
   Over" notice, legitimacy recovers its 10, and the row reads "Barred to <year + 10>" until then.
6. **Leaving the law**: with measures on, enact another family law (console). Every measure the new law doesn't allow
   ends at once, each with its "… Ended" notice; under a law that allows it again it starts a new term.
7. **Display only**: the section shows, one line above the rows says the measures act only under Full, and every
   button is greyed with that reason.
8. **An AI country with a measure on** (an observer run of a few decades, Full): a shrinking or ageing AI on
   Pro-Natalist Policy takes Child Allowance or Honours, at most one money measure a year; one in a famine on
   Population Control takes Free Contraception, Later Longer Fewer or Birth Limit, never more authority measures
   than its free authority covers; none ends one before five years. Read the country's `te_dg_ms_*` in a plain-text
   save.
9. **A revolution that wins** under Full, the old government holding a measure: at once, the winner has the
   measure's variable (copied from the loser), modifier and cost, or a notice if its law doesn't allow it.
10. **Every game (Disabled)**: the family laws' AI weights: an AI country in famine moves toward Population Control
    Measures; one whose population shrinks by more than 0.1% a year, toward Pro-Natalist Policy. Crowding counts only
    where half a country's people live in states at Migration Crowding's ceiling (none before about 1900).
11. **Parental Leave (Full)**: option l's women's-work family (`womens=`) rises by 0.02 in every state, and the pair
    (`pair=`) follows within a month; its expense follows the capital's women's rate. `debug.log`: no error from
    `te_demog_measure_*`, `te_demog_messages.txt`, `te_demog_ms_law_on_action` or `te_debug_demog.10` (the
    self-check's verdict event: an error there would leave a `START` with no verdict, which reads like a capital
    that changed hands).

## Phase 3: the urban pattern and Planned Capital

The national urban pattern's effects and the Plan a New Capital decision (spec §5.1; mod_systems.md § Demographics,
"The urban pattern's effects and Planned Capital"). Everything here acts under Full only.

1. **Full, a new game, a country of three states or more whose Urban Pattern row reads Primate or Dominant** (in the
   1903 observer census Argentina and Egypt read Dominant, Siam and Colombia Primate). Through 1836 each state takes
   its modifier at its yearly count: the largest city **Primate City** (Urban Center throughput and migration
   attraction up), every other
   state **Provincial Neglect** (migration attraction down, turmoil penalties up), each at the strength the Urban
   Pattern tooltip shows (none at 25% primacy, full at 60%). Hover a state's modifier: its figures are the full sizes
   times that strength. A Balanced or Dispersed country gets neither (in the 1903 observer census Britain, France and
   the United States read Balanced).
2. **The tooltip** (Overview's and Where People Live's Urban Pattern rows): the strength, the largest city by name and
   each field as it applies; "none" with the reason for a Balanced or Dispersed pattern or a country under three
   states. The Primacy row's tooltip names the largest city. No label or value cut short.
3. **Display only**, a new game: no state carries either modifier, and the tooltip's last paragraph says what Full would
   do.
4. **A country of one or two states**: no modifier, though its primacy reads near 100%; the tooltip says why.
5. **The decision** (Full; Modern Sewerage shows it, Steel-Frame Buildings opens it): the greyed reasons read right
   (pattern, peace and plays, moved recently, the 50 years with the next year, 100 authority, a site). Take it: the
   event offers up to three sites, largest first, never the capital or the largest city. Choosing one: the capital
   moves at once; the treasury drops by about 3% of a year's GDP; Building the New Capital takes 100 authority for five
   years; the new capital shows Planned Capital for 20 years; the decision is greyed "the next from <year + 50>". Not
   Now (the default) spends nothing and the decision stays open. While the event is open the decision is greyed "Our
   planners are not already choosing a site"; let the event lapse and nothing moves. Start a war (or lose a site) with
   the event open: that site's option goes. `debug.log`: the `planned_capital_moved` lines.
6. **After the move**: does the base game let you move the capital again at once with its map interaction (the
   `penalty=` line says whether its Moved Capital Recently came with the decision)? Move it back: Planned Capital ends at
   the old site's next yearly count.
7. **An observer run to 2000, Full**: how many AI countries plan a capital, when and where (a plain-text save's
   `te_dg_pc_year`). The rule allows it only to Primate countries of eight census states or more, at 45% primacy or
   more, whose largest city Migration Crowding presses at its ceiling (multiplier 4.5, ten times the reference density;
   no state before 1902 in step 3a's saves), with the money and authority; expect a handful, none before about 1900,
   not dozens. None should move a capital twice within 50 years.
8. **A revolution that wins** within five years of a planned capital: the winner still pays the building's authority
   until the five years end, and the decision stays greyed for the rest of the 50 years.
9. `debug.log`: no error from `te_demog_place_*`, `te_demog_capital.1` or `te_debug_demog.60`, and none while the site
   event is open (the move's 675 branches sit behind a click-only marker).
## Family Policy in the census (step 3b)

The census reads the measures and the family laws (spec §3.2, §3.5; `docs/systems/mod_systems.md`, § Family Policy in
the census). Console option x writes the capital's `TE_DEMOG_FAMILY` line: the six types it reads, the policy term,
Birth Limit's part, the sex ratio's add in force and the census's stored terms. No new self-check: the one unverified
engine fact (a country modifier's script-only type reaching the state) is step 3a's `measure_country_types` row above,
and a BROKEN there means no measure moves births here either.

1. **Full, Pro-Natalist Policy, no measure**: option x reads `desired=0.050`, `measures=0.000`, `policy=1.050`. After
   the capital's next census its Children per Woman tooltip lists "Family policy: ×1.05"; the law's old +10% births
   no longer reaches the census's term (option n's `q_b` excludes it). **Disabled or Display only**, same law: the
   state panel's birth rate keeps its Laws and Institutions line with the +10%, as before; under Display only the
   tooltip shows ×1.05 and births don't move.
2. **Child Allowance on** (Full, Pro-Natalist Policy): option x `desired=0.190`, `measures=0.140` and `policy=1.190`
   at once, while `st_policy=1.050` and the tooltip keep the last census's figure; at the capital's next census
   `st_policy=1.190`, "Family policy: ×1.19", children per woman up by roughly a tenth of a child in a rich state,
   `planned` up and `unplanned` unchanged.
3. **Family Housing**: `urban_relief=0.500`, `urban_left=0.500` at once; at the next census `st_urban_left=0.500` and
   the tooltip's "Urban life" factor moves halfway to 1.
4. **Sex Education** (Population Control or Family Planning): `means_lit=0.200`; `means_live` rises where literacy is
   under 0.8 and stays where it is above.
5. **Restricted Contraception**: `maternal=0.250`; after the capital's next step its Causes of Death Childbirth row
   lists "Family policy: ×1.25" and mothers' deaths per 100,000 births rise by a quarter (`mmr=`).
6. **Birth Limit** (Population Control): `bl_part=-0.30` (−0.45 at one child), `policy` 0.70 (0.55) less the other
   measures. Before Microprocessor `srb=5.0` but `srb_add=0.0`; once it is researched `srb_add=5.0` (10 at one child),
   and over the next censuses the 0-4 band's boys outnumber its girls by about 110 to 100 (115 at one child).
7. **Rural Exemption** with Birth Limit: `bl_relief=0.500`; in a farming capital (`agr=` high) `policy` rises by
   0.5 × `agr` × Birth Limit's 0.30 or 0.45.
8. **A save from step 3a, under Full**: the state subtab's Causes of Death section says it waits for the census until
   each state's next step (the gate now needs `te_dg_in_mat`), then shows the Family policy factor.
9. **`debug.log`**: no error from `te_demog_tfr_policy`, `te_demog_ms_birth_limit_part`, `te_demog_srb_add`,
   `te_demog_newborn_split`, `te_demog_f_maternal_laws` or `te_debug_demog_family_line`.

## Phase 2 step 2: the workforce, pensions and health costs

Under Full the census sets each state's workforce (a term W from who is of working age and who works, moving at most
0.01 a census step), the country chooses a pension position, pays a pension bill and a health bill, and work deaths
split by the census's own workers. Under Display only the figures and the section show and the buttons are greyed;
outside Full nothing changes. Spec: `docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md` §2.
The two self-checks are in the table above. None of these gates the merge.

What the offline evidence already says (2026-10-12):
- **The stop rule (spec §1.8).** In the 1 January 1836 save, 82% of the world's people sit at exactly 0.250 workforce
  over workforce plus dependents, 17% at 0.300 (a +0.05 line) and slaves near 0.5. The engine's ratio is workforce over
  people, as `WORKFORCE_SCALE` assumes; `workforce_ratio_scale` confirms it in game.
- **The pull is slow in the saves.** Pops start at their state's ratio whatever their type (aristocrats at 0.25, not
  0.2) and drift: the aristocrats' gap to the peasants grew 0.0026 to 0.0047 over 1836 (about 0.0002 a month), and by
  1901 is 0.033 of the 0.05 their bases differ by. Countries with Women Own Property (+0.05) sat at 0.276-0.306 against
  0.30 for decades, and countries with no line at 0.22-0.26. So the game's own figure can trail the census's set ratio
  by 0.01-0.03 in fast-growing states; the panel shows it beside the target, and `workforce_follows_target` says
  whether the engine's figure follows the ratio W sets (half of its move there within five years).

1. **Display only, a new 1836 game.** The Population panel's Demographics tab shows Work and Retirement after the
   overview (open), and the state subtab after Causes of Death. Nothing ends in "…": "84 (Linked to Average)" is the
   longest value. The overview shows Working Age (about 70% in Britain) and Old Age From (about 58-62) where the
   dependency ratio was; the Working Age hover gives the dependency ratio.
2. **The buttons under Display only (a country with Old Age Pension; enact it by the console).** All five greyed, one
   line above them ("Pension settings act only under the Full Demographics rule"); each tooltip lists the failing
   condition and the effect. No Pension Bill row.
3. **Full, the same country.** Press Raised (70): the age reads 70 at once; the line above the buttons gives the year
   the term ends; the other four grey with "The setting has held for five years". At the next 31 December the Pension
   Bill row appears (option r's `bill=`, `bill_share=`) and falls against Standard's; the capital's `w=` (option r)
   rises by at most 0.01 at its next census. Option s ends the term to try the next. Trade Unions show the −2 approval
   modifier.
4. **A linked position.** From Early (60), Linked to Average sets 65 at once and then moves at most a year a year
   toward old age from − 5 (option r's `link_target=`), at the yearly census only: enacting another law that year
   doesn't move it.
5. **Leaving Old Age Pension** (enact UBI): the Pension Age, Pensioners and Bill rows and the buttons go, the IG
   modifier with them, and the budget's Old-Age Pensions expense goes the same day; a return to Old Age Pension starts
   at Standard with no term running.
6. **Full, the workforce term.** A state's workforce breakdown shows "Census: Workforce" in place of "Laws and
   Institutions" from its first census step (the pair comes off); option r's `w=` starts at the old pair (`pair=` before
   the step) and moves at most 0.01 a census step. A Women in the Fields state starts near +0.30 and drifts down. The
   state subtab's Workforce hover shows the game's figure, the set ratio and the census's target.
7. **The health bill.** Under Full, from the first census, the Health Need row's hover gives the health system's extra
   bureaucracy cost (about 0 in 1836); the country's modifiers show "Census: Health Care Needs". Its institution cost
   in the budget panel moves by that share.
8. **An AI country picks a position.** In an observer run under Full to the late game, a few AI countries with Old Age
   Pension leave Standard: option r on one (switch to it) or the census log's `TE_DEMOG_WORKC` lines (`pos=`).
9. **The observer gate (spec §2.6).** An observer run under Full to 2100 with the census log on (option b), then
   `demographics_observer_report.py LOGS --work`: the game's workforce follows the set ratio within 0.03 where a term is
   in force, no state's set ratio past 0.8 or under 0.1, and the pension bill's share of revenue across the great
   powers (15-30% expected for a rich country at Standard around 2000-2020).
10. **A late save, please.** No 2000-2020 save existed for the fit, so the rich-today bands were fitted on the harness's
    Rich-today inputs (a 2020-like structure) and B on the 1953 save's revenue over GDP (median 0.27 among the 15
    largest economies). Keep a plain-text save of a rich country around 2000-2020 (debug mode) and run
    `demographics_harness.py workforce SAVE`-style checks on it; `pensions SAVE` reads its revenue over GDP.
11. **Work deaths' split.** Under Full, option r's `fws_wk=` (the census's women among workers 15-64) replaces
    `fws_law=` in the split at the next step: about 0.17 in a 1836 farming state (the law table's 0.1), about 0.46
    under Protected Class (0.48). The Causes of Death section's work row still adds up.
12. **A revolution that wins** under Full, the old government holding Raised and a bill: at once the winner shows the
    same pension age and position, the Trade Unions' −2 modifier, the Old-Age Pensions expense and the health bill; its
    states' "Census: Workforce" continues the old values (option r's `w=` on the capital) rather than the flat lines.
    The same after a conquest of a whole state region: the new state's term lands from the region's copy at its first
    census.
13. **`debug.log`:** no "Failed to fetch variable" or script errors from `te_demog_work_effects.txt`,
    `te_demog_work_values.txt`, the pension scripted GUIs, `te_debug_demog_wf_term_checks` or the `TE_DEMOG_WORKC` line.

## Phase 2 step 4: conscription, the youth bulge and sex balance

The census counts each state's men aged 20 to 39 (its conscription term against the 1836 world's share), its young adults
(the youth bulge) and its sex balance, and takes the war dead from the men's ages, under Display only too. Step 4
shipped the three effects held back (`demographics_params`' `CONSCRIPTION_EFFECTS`, `YOUTH_BULGE_EFFECTS`,
`SEX_BALANCE_EFFECTS`); the migrant booking (2026-10-12, § The migrant booking below) turned them on, so the items
below are written for them on. Spec: `docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md`
§4; no plan document (owner, 2026-10-12). The two self-checks are in the table above.

1. **The 1836 figures (Full, a new game).** Option t in the capital after its first count (`TE_DEMOG_CONSEQ`): `share`
   about 0.139, `term` and `mc` within ±0.05 and equal, `consc_mod` with `mc` in it where `mc` is 0.01 or more either
   way (else only laws' and technologies' lines), `youth` about 0.16, `y_now` and `yb` 0, `sex` 91–98; `sxb` -1 (no
   state starts short of men), `tfr_sex` 1 and `women_add`, `fewer`, `more` 0. The country line: `fam_share`
   about 0.139, `term` about 0, `yb_states` 0.
2. **Conscript battalions follow the term (Full).** The engine fact the self-check can't read. Find a state with a term
   of a tenth or more either way (option t's `mc` in a colony or a frontier state, or the Fighting-Age Men row's ×):
   its conscription tooltip lists "Census: Fighting-Age Men" at that size, and its conscription limit (the battalions
   it can raise; the country panel's "+N" conscript battalions summed) is about the same share above or below the same
   state in a Display only game of the same date. If the line is there and the battalions don't move, take the
   `conscription_term_read` fallback.
3. **The war dead land in the pool's ages (Full or Display only).** During a war with dead, option a's replay of a
   state with dead (`demographics_harness.py replay debug.log` prints OK) and its pyramid: the men's bars of 20–24 to
   35–39 fall, 15–19 and 40–44 don't.
4. **A youth-bulge state shows its modifier (Full).** In a later game (1880s or after), a state whose Demographics
   subtab shows a Youth row: its modifiers list "Census: Youth Bulge", radicals and turmoil effects at the strength the
   row's hover gives; option t's `unemp=` matches its `unemp_walk=` and the state panel's unemployment (the self-check's scale). Until the
   2026-10-16 log triage the Youth row never showed: its gate read `state_unemployment_rate` from a scripted GUI, which
   gets none. The census now stores its read (`te_dg_unemp`) and the row reads that, so in a save from before, a state
   shows the row from its next census. `error.log` has no `te_demog_sguis.txt:516` line.
5. **The sex-balance modifiers (Full).** A state below 90 men per 100 women (after a war with many dead; console
   option t's `sex`) lists "Census: Fewer Men" at the strength its Sex Balance hover gives, its children per woman's
   breakdown shows "Few men to marry" below 1.00, and option t's `sxb` is its balance; a state at 110 or more lists
   "Census: More Men". In peace both should be rare (§ The migrant booking, item 2).
6. **Display only and Disabled.** No state lists any of the census's modifiers (option t: `mc` and `yb` -1); the
   Fighting-Age Men row's hover says "would set"; the Youth row still shows where a bulge would be. Switching a Full game
   to Display only isn't possible mid-game: start one of each.
7. **The panel's rows.** Fighting-Age Men reads like "28% (×1.00)" as Work and Retirement's last row on the tab and the subtab, nothing ends in "…", and
   the hover gives the share of people, the 1836 reference (13.9%) and what the census sets ("The census sets its
   conscription ×…" under Full, "would set" under Display only); an old save's census reads "After the next count" until
   the state's next count. No hover says "not applied yet".
8. **`debug.log`:** no "Failed to fetch variable" or script errors from `te_demog_consequence_*`,
   `te_demog_sex_births_store`, `te_debug_demog.30`, `te_debug_demog_unemployment_selfcheck` or option t.

## Phase 3: the event wave

Ten events (the parent spec's §9) fire when the census crosses their thresholds, at most once a generation per country,
under Full only: `events/te_demog_wave_events.txt`, `docs/systems/mod_systems.md` § Phase 3: the event wave. The owner
judges their text and balance here (owner, 2026-10-12). No plan document; the self-check is in the table above.

1. **Each event from the console (Full, any date).** `event te_debug_demog.1`, option w, then each of the ten in the
   chooser: the picture fits the text (the Baby Boom's switches from a classroom to a family watching television once
   Television is researched), no raw loc keys or `[...]` left in the description, the flavor and the options read in
   the house voice, each option's tooltip lists what it does, and nothing is said that the effects don't do. The
   Lost Generation's figure reads 0% outside a war, as the console fires it with no war behind it.
2. **The options' balance.** For each event, is there a player for whom each option is the best? The two harm menus
   (the Lost Generation, the Empty Villages) give no option an upside: each spares one harm. Note any option that is
   never worth taking, or always.
3. **The Greying's two cases.** Under Old Age Pension: five options, raising the age greyed with its reason while the
   pension setting's five-year term runs (choose a position on the tab first) and, once taken, the tab shows Raised
   Pension Age with its new term; cut benefits and raise contributions show a Pension Reform income row in the Budget
   panel's Breakdown tab. Without the law: three options (the borders, almshouses, the family).
4. **Missing Girls' relax option.** Under Population Control Measures with Birth Limit at one child (Microprocessor
   researched): relaxing returns it to two children on the tab at once, its term running on; at two children with its
   term run, relaxing ends it and the Rural Exemption with it; at two children within its term, the option is greyed.
5. **The Overspill's new towns** in a country with a Settlement Authority and Modern Urban Planning: the Authority's
   settlement plan switches to Planned Towns; without either, the option still works and says nothing about them.
6. **The firing itself (Full, a long game or fast mode).** `debug.log` and the save: an event fires on 31 December after
   the census, at most one of the yearly eight a year, and not again within 25 years (`te_dg_wv_<event>`, a timed
   variable); none in an 1836 game before the end of 1837. The AI answers them too.
7. **The war tracker in a real war (Full).** At war, the country holds `te_dg_wv_war_from`, `_war_dead` (rising with
   the war's dead), `_war_seen` and `_war_men` (its men of fighting age when the war began); the Lost Generation fires
   the month the dead pass a twentieth of them; the variables go the first month at peace, and the Baby Boom fires then
   if the war ran two years and its dead passed a hundredth.
8. **The Last Generation?** fires the day Biological Immortality is researched under Full (a late save, or the tech
   granted by the console), and never again in that game.
9. **Bare Branches in the settler societies.** In the overnight run's 1900 and 1904 saves it was due in 9-12 countries of
   a million people or more: the USA, Canada, Argentina, Chile and Cuba, which had more men than women then, and Mexico,
   Bolivia and Colombia, which are the census's migrant booking (the reason step 4's effects are held back). Note where
   it fires in a play-test; the follow-up on the migrant booking should take the second group out.
10. **`debug.log`:** no script errors from `te_demog_wave_*` or `te_debug_demog.80`/`.81`, and no
    `Failed to fetch variable` or `Data error in loc string` lines naming them.

## Phase 3: the late game

Built 2026-10-12 from the late-game design (`docs/superpowers/archive/specs/2026-10-11-demographics-late-game-design.md`; `docs/systems/mod_systems.md` § Phase 3: the late game). No new self-check: every engine fact it reads is proven (a script-only type on a technology reaching a state, #892; a pop's `wealth` as a value, the Gini walk; the wealth pair's per-pop scaling, probe P6; a building's active method in a state value, `te_state_railway_train_code`). Console option **v** researches the ageing ladder at once, so the items below run in an evening: a Full game, any year, then `observe` or fast mode (h) for some census years. Option **u** logs the capital's late figures (`TE_DEMOG_LATE`) and the country's.

1. **The ladder starts the late game.** After v, each state's next census holds `te_dg_elig` (option u's `elig=`), rising toward its target at the medical diffusion rate; `rate=` reads 0 (immortality's r) and `pull=` 0.03; `s5=`/`d5=` show a band's treated share and deficit. A country with no ladder logs `elig=-1`.
2. **Who is reached.** Under Public Health Insurance with a large health system nearly everyone (`hs_cover=1.00`); under Private Health Insurance only the rich at first (`hs_cover=0.00`, `threshold=` falling about 2 a year from 80); under Human Purity nobody (`banned=1`, `elig=` drifting to 0 while bodies keep their age: `d5=` holds); under Mandatory Augmentation at least 0.9 (`floor=0.90`); under Unrestricted Augmentation `reach=20` and `threshold=` 20 lower.
3. **Deaths fall under Full.** The capital's deaths per 1,000 (the overview) fall over the census years after v; option n's `md=` grows negative. Under immortality the census term may reach its floor (`clamped=1`, the read at −0.8: the engine's deaths can't go below a fifth of the bare curve, about 2.4 per 1,000 at high standard of living, against the census's 2.1): the ring then follows the engine's (the on-top scales).
4. **Rich pops die less (call 14).** A rich pop's mortality tooltip shows a larger "Census: Deaths by Wealth" line than a poor pop's in the same state (option u's `slope=` negative, `wealth_w=` the pair in force); the state's total deaths stay the census's.
5. **The panel.** Life Expectancy reads "100+" past 100; Old Age From reads "None" under immortality, its hover with the untreated's figure; Living to 100 and Biological Age rows appear from the late game; the Longevity section (Longevity Care, Longevity Gap) shows, nothing cut short; children per woman's hover shows the mean age at childbirth and, under immortality, the births to women of 50 and over. The country tab and a state subtab.
6. **The pyramid's toggle.** Shown only where biological bands exist; the biological pyramid moves the treated toward their biological ages (under immortality a tall column at 25-35); the bars stay inside the panel (the scale covers both). The toggle is a `default_button_action` button whose onclick is `GetVariableSystem.Toggle` (until now the mod toggled only section headers that way): it switches on one click and back on the next, on the tab and the subtab apart.
7. **Pensions.** Under Old Age Pension, Linked to Common Longevity heads five years below the untreated's threshold, Linked to Average below the state's (option r's `link_target=`); an AI country with a gap over 20 points picks Linked to Common. The health bill's longevity term shows in option u's `health_lx=`.
8. **Outside Full nothing changes.** Under Display only the late figures show but births and deaths follow the base game: Biological Immortality's, Mental Health Awareness's and Mind Backups' mortality lines show flat under Laws and Institutions as before.
9. **Ectogenesis.** A State Youth Center on Ectogenesis raises `ecto_levels=`; the mean age at childbirth and maternal deaths move as the share grows.
10. **Cost.** Option d (benchmark) in a late save with the ladder: a treated state's step against an untreated one's (the interpreter counts about 2.9× the statements); a late plain-text save with the census against one without (about 100 more variables a treated state, about 6 MB with every state treated).
11. ~~**The gap's politics stay off.**~~ On since 2026-10-16 (owner): § Modern safety and the gap's politics, items 4 and 5, check them on instead.
12. **The panel's unproven GUI.** With the tab and the subtab open in a game with no late game, `debug.log` and `error.log` hold no "Failed to fetch variable" for `te_dg_lx_*`, `te_dg_bb*`, `te_dg_cbb*` or `te_dg_old_age_c` (every read sits under a gate in `te_demog_lx_sguis.txt`). Old Age From's value, a SelectLocalization inside a loc value the GUI picks with its own SelectLocalization, reads "None" or the years, never the raw key. Nothing elides: "38 (calendar 61)", "Show Biological Ages", "Longevity Care". The country tab's Biological Age and Longevity Care hovers read the capital's rate and market threshold.
13. **B's late reading (call 16).** The fit read the one plain-text late save there was, 2062's `Baseline.v3`: 7 of its 15 largest economies raise under 10% of GDP while spending 5-34 times that (the AI's chronic insolvency), and one economy is 40 times the next. Its other eight agree with 0.06 (median 0.26, B 0.059), as do 1949, 1953 and 1959. Keep a plain-text save from a healthy game after 2000 and run `demographics_harness.py pensions SAVE`: the bill should sit at 15-30% of revenue at 18-22% pensioners.
14. **Late births (fixed 2026-10-16).** In a late save (the France → European Union game, `european union_2033_12_21.v3`) every late state's next census holds births above 0 (option u's capital, the overview's births per 1,000 off 0.00) at about the plain sweep's rate for its TFR, and its trend arrows come back (`te_dg_stepped` 1). That first refresh measures a window the frozen terms ran under, so `clamped=1` on it alone is not BROKEN. Before the fix every late state under a TFR of 2 recorded no births and froze its births and deaths terms. The census's under-fives stay few for years after: the fix makes no children for the years already stepped, and the engine's children of those years sit in the ring as migrants at other ages. Console option c_world (`event te_debug_demog.1`) re-seeds every late state in the world: afterwards `TE_DEMOG_RESEED_LATE states=` names how many, every late state's pyramid has a broad base again (the EU's under-fives about 1–2% of its people at a TFR near 1.1, not the 0.06% of the 2033 save), our country's figures follow at once and other countries' on 31 December. Each state seeds again at its next pulse (an off-pulse seed is marked) and first steps a year after that. A seed leaves the births and deaths terms as they were, so the frozen terms stand until that first step, up to about two years: not BROKEN.
15. **The laws' longevity care lines (2026-10-17).** The law tooltips show the census's lines: Public Health Insurance "Longevity Care Through the Health System +100%", Charity Hospitals +25%, Private Health Insurance "Longevity Care Price Fall +100%", Human Purity "Longevity Care Banned" in red, Unrestricted Augmentation "Longevity Care Market Reach +20", the Regulated Augmentation Market's price fall +50%, and Mandatory Augmentation +100% and "Minimum Longevity Care Reach +90%", none showing a raw key, each hover giving its description. `debug.log` holds no `Unknown modifier type` for them. Option u reads them back (item 2). Every engine fact is proven: a script-only state type on a law reaching the states (the augmentation laws' chronic treatment), a script-only country type and a country bool read with `modifier:` (the Banking panel's intervention points and locks), so there is no self-check.
16. **Deaths by cause at the body's age (2026-10-18).** Under immortality (option v, then fast mode for a few decades), the Causes of Death pie's chronic illness slice shrinks as bodies wind back, and infection and accidents and violence take over: the model's rich state with everyone in care has chronic illness at 38% of natural deaths after 30 years and 23% after 50, where the calendar bands this replaced gave it about 90%. The Leading Cause cell follows the pie. The Chronic Illness hover, on the tab and the subtab, adds that the rate is by the body's age and how many years younger bodies are; with no late game it has no such sentence, and `debug.log` holds no "Failed to fetch variable" for `te_dg_lx_age` or `te_dg_lx_bio`. No self-check: the count reads the late sweep's own locals and sums, no new engine fact.

## Phase 3: Family Limitation and Cultural Hegemony's drift

Family Limitation becomes a national practice under Full: a share of couples, 0–1, that France starts at 0.6 (history's
modifier), that rises toward a target from Forced Heirship on the farms, literacy and the church law, and that closes
part of the gap to the countries across its borders. Its one line in the means is the share less what modern
contraception has replaced. Forced Heirship's rural birth cut moved to the moved lines' absorbed family (outside Full the
Laws and Institutions pair re-applies it; under Full Family Limitation stands in). Cultural Hegemony's drift moves each
country's desired fertility a little toward the hegemon's, by how far the hegemon's culture leads its own. Late Marriage
and Birth Spacing now spread from neighbouring states too. Outside Full nothing changes but the Display only panel's
practices, which spread. Spec: `docs/superpowers/specs/2026-10-08-demographics-design.md` §13 and §6; results:
`docs/testing/demographics-family-limitation-2026-10-12.md`. The three self-checks are in the table above.

1. **France at the start (Full, a new 1836 game).** France's modifiers list Family Limitation at +60% means to plan a
   family, as before. The Population panel's children-per-woman hover: "60% of couples practise family limitation" in
   the country line, and in the capital's terms "family limitation's part +60%". A French farming state's birth-rate
   breakdown has no "Divided Holdings" birth line and no Laws and Institutions line for it after its first census step.
2. **The spread (Full, a few years in).** Belgium, Switzerland or Spain shows Family Limitation in its modifiers once
   its share passes 2% (in the first five years or so), at the share the hover's country line gives. Britain shows none
   unless the strait check says the iterator crosses water.
3. **Forced Heirship outside Full (Disabled, a new game).** A French farming state's birth-rate breakdown shows the
   −15% × farm share as a Laws and Institutions line after its first yearly pulse, and Divided Holdings keeps its
   migration line. The same in Display only.
4. **The hegemon's example (Full, a late game with Cultural Hegemony on).** In a country under the foreign benchmark,
   a state's children-per-woman hover shows "The cultural hegemon's example" away from ×1.00 (within ×0.90–×1.10), and
   option l's `hegemon=` matches it. The hegemon itself reads ×1.00.
5. **Display only and Disabled.** France keeps history's modifier at +60% for good; no country gains it; every hover
   reads "The cultural hegemon's example: ×1.00".
6. **`debug.log`:** no "Failed to fetch variable" or script errors from `te_demog_fl_effects.txt`,
   `te_demog_spread_*`, `owner.var:te_dg_pr_fl`, `global_var:ch_rank_1`, `te_debug_demog.90` or the two inline
   self-checks.
7. **A revolution's winner (Full).** It inherits `te_dg_pr_fl` and its line comes back at the next 31 December
   (the line is re-added every census year).

## The migrant booking (2026-10-12)

The census books each state's migration residual (the engine's own migration: the Vic3 save's weekly statistics agree
with it) by its migrant profile, now with a cap on how much of one class and sex a step can take or add (3% and 5%;
the rest over every age and both sexes) and a labour split that moves to half women as a state's men run short or
pile up. Results and the re-walk of the 2026-10-12 run: `docs/testing/demographics-migrant-booking-2026-10-12.md`. It
rests on no new engine fact, so it adds no self-check; `conscription_term_read` (table above) arms again with the
effect on. Display only shows the same pyramids as Full; neither changes the game outside Full.

1. **Emigration leaves women and men (Full or Display only, a game run to the 1870s or later).** A state that loses
   people year after year (its Net Migration row negative most years; in the 2026-10-12 run, Hill Punjab, Hyderabad,
   West Karelia, the Central Provinces) keeps 90 or more men per 100 women aged 20 to 59, and its pyramid's men aged 20
   to 39 are not much shorter than its women. Before the booking such states fell to 2–50.
2. **Few sex-balance modifiers in peace (Full): the band's real test.** In a save with no great war in the last twenty
   years, fewer than one state in fifty lists "Census: Fewer Men" or "Census: More Men" (`demographics_harness.py
   consequences SAVE` prints the share). The re-walk predicts 0–1% to 1901, but runs about a point high, and its
   emigration states sit at 90–91: if the game's settle just under 90 (a few percent of states at a sliver of the
   effect), move `LABOUR_BALANCE_LOW` to 96 → 92 and regenerate.
3. **Frontiers are no longer male (Full).** A frontier filling fast (the American West, the Canadian prairies,
   northern Mexico) stays near 100–110 men per 100 women. This is the band's price, not a bug: the results doc's
   § The frontier gives the owner's choice.
4. **Conscription terms stay moderate (Full).** The great powers' Fighting-Age Men rows read ×0.95 to ×1.10 through the
   19th century; no state below ×0.85 or above ×1.25 (the old ceiling, removed 2026-10-16) from migration alone. The
   next run's `consequences` on its saves should agree with the re-walk (people past ±0.15: under 2%).
   **Hidden (2026-10-16):** a state's modifier list, both the full view and the condensed one, no longer shows "Census:
   Fighting-Age Men" even where the row reads other than ×1.00, and a state with only the hidden census modifiers
   leaves the condensed box faded; the state's conscription rate tooltip still names it; a state far above ×1.25 (a
   frontier or a young-pool boom) is the case to look for, since nothing caps it.
5. **`debug.log`:** no errors from `te_demog_migrant_rates` or `te_demog_labour_balance`.

## Modern safety and the gap's politics (2026-10-16)

Modern safety: work deaths and deaths from accidents and violence × (1 − the share the era 7-9 technologies prevent),
a factor of its own beside laws (`docs/systems/mod_systems.md` § Causes of Death). The gap's politics: call 15 on at
the late-game design's sizes. Both act on the game under Full only; under Display only the census's figures (the
hovers, life expectancy) move with safety but births and deaths don't. Neither rests on a new engine fact (a script-only
type on a technology reaching a state is #892's; approval sums its lines before it rounds, owner 2026-10-16), so no
self-check.

1. **The hovers multiply (Full or Display only).** In a state of a country with Industrial Robotics, the subtab's Work
   row hovers "Laws ×a" and "Safety ×b" and reads a × b; Accidents and Violence hovers laws, safety and turmoil and reads
   their product. A state whose last count came before the change reads "Safety ×1.00" until its next count.
2. **The carriers' tooltips.** Prefabricated Construction, Industrial Robotics, Containerization and Knowledge Economy
   show "Safer Work"; Modern Urban Planning, Computer-Aided Design and Cellular Networks "Safer Streets and Homes".
   Option l doesn't print them; the hover is the check.
3. **Life expectancy moves a little (Full or Display only).** A rich country's life expectancy rises about two and a
   half years over its era 7-9 research (the harness's rich state with the Combustion Engine: 75.9 → 78.3). Nothing
   moves before era 7.
4. **The gap's politics appear (Full, late game).** With longevity care reaching some people and not others (option v,
   a Private Health Insurance country, so the market reaches the rich first), the country carries "The Longevity Gap"
   with Trade Unions and Rural Folk approval down to −3 × the gap × the share not in care, and a state with a wide gap
   carries its own "The Longevity Gap" with labor movement support up to +10% × the gap. The overview's and subtab's
   Longevity Gap hovers no longer say the effects aren't applied.
5. **Sizes, which the play-test now judges.** Under Public Health Insurance with a large health system the gap stays
   small and so do the modifiers; under Private Health Insurance the unions' approval should fall by one or two points
   at most while the market reaches only the rich. If the unions turn on every late country, halve
   `LX_POLITICS_APPROVAL`; if no one notices, the gap may not get wide enough for the sizes to matter.
   **Fractional approval:** the country modifier is −3 × a multiplier between 0 and 1, so it applies fractions such as
   −0.9. The game adds an interest group's approval lines before it rounds (owner, 2026-10-16), so the fraction counts
   toward the whole-number total: the Trade Unions' tooltip lists The Longevity Gap at its fraction, and the total can
   move by a point where the lines together cross a half.
6. **Outside Full nothing changes.** Under Display only and Disabled no "The Longevity Gap" modifier anywhere, and
   births and deaths follow the base game whatever a country researches. A game switched from Full to Disabled loses the
   country's modifier at its next 31 December (`te_demog_lx_politics_clear`) and the state's at its next state pulse.

## Policing, criminal justice, Synthetic Biology and the measures' authority (2026-10-16)

The Ministry of Public Safety and the criminal-justice laws on accidents and violence, Autonomous Vehicles as modern
safety, Synthetic Biology's step on the ageing ladder and the Family Policy measures' new authority upkeep
(`docs/systems/mod_systems.md` § Causes of Death, § Phase 3: the late game, § Family Policy measures). Every line is a
script-only type on a carrier the census already reads (#892's fact), so no self-check.

1. **The carriers' tooltips.** Each police law's institution lines show Deaths from Violence and Accidents a level of
   the Ministry of Public Safety: Local Police and Private Policing −2%, Dedicated and Militarized −3%; Restorative Justice −4%,
   Rehabilitation-Focused −8%; Penal Labor Camps Deaths at Work +10%; Autonomous Vehicles "Safer Streets and Homes"
   +10%; Synthetic Biology Ageing in Longevity Care −5% and Biological Immortality −70%.
2. **The hover moves (Full or Display only).** In an incorporated state of a Dedicated Police country with the
   Ministry at level 5, Accidents and Violence's "Laws and Institutions" factor reads 0.15 lower than with the Ministry
   at 0, after the state's next count; under Rehabilitation-Focused criminal justice a further 0.08 lower. Its lore line
   names the Ministry and both laws. An unincorporated state reads no police line at all (the law's line is per
   Ministry level, which reaches incorporated states only).
3. **The ladder (Full, late game).** With mRNA Therapeutics, Personalized Medicine, Genetic Engineering and Synthetic
   Biology, the Biological Age hover's ageing rate reads 0.70 in the capital (0.75 without Synthetic Biology); with
   Biological Immortality 0.
4. **Birth Limit's row** reads 300 authority, still 300 after Start, and 400 after Tighten; the country's authority
   falls by the same. The Missing Girls event's relax option says the upkeep falls by 100, and authority rises by 100
   when it is taken.
5. **A player's Start needs the upkeep free.** With less free authority than a measure's upkeep its Start is greyed
   with "Needs @aut! N free authority to start", N the upkeep; Birth Limit at two children greys Tighten under 100
   free. End is never greyed for authority. The engine reads `authority >= <script value>` as the UN's buttons read
   `influence >= un_found_influence_cost`.
6. **AI authority (observer run, Full).** A famine AI on Population Control Measures starts Birth Limit only with 325
   or more free authority and tightens it only with 125 more; no AI runs into negative authority from the measures
   alone. Read `te_dg_ms_*` and the country's authority in a plain-text save.
7. **Communal Child-Rearing by who governs (Full).** Under Communal Child-Rearing alone the section's rows are Child
   Allowance, Parental Leave, Family Housing and Free Contraception, and the others sit dimmed, Sex Education's hover
   naming a Council Republic or Anarchy and Honours' and Restricted Contraception's a Single-Party State or Autocracy
   with Outlawed Dissent. Console a Council Republic: Sex Education becomes a row. Console a Single-Party State and
   Outlawed Dissent with Honours on, then Censorship: Honours ends at once with its "Honours for Large Families Ended"
   notice, which names the government as a cause. Birth Limit and the Crash Campaign stay dimmed under every
   government.

## The laws' census and Wealth Concentration lines (2026-10-17)

Five more terms that read laws with `has_law` now read lines the laws carry, so each law's tooltip says what it does
(`docs/systems/mod_systems.md` § Wealth Concentration, § Phase 2 step 1, § Late Marriage and Birth Spacing, § Family
Limitation). The values are the old ones, so no figure moves. Every engine fact but one is proven: a script-only state
type on a law reaching the states (the augmentation laws' chronic treatment) and a script-only country type read with
`modifier:` (the Banking panel's intervention points). The one that isn't, a state type on an amendment (Undivided Farm
Succession), is the `workforce_amendment_type` self-check's.

1. **The tooltips.** Child Labor Allowed "Census: Children at Work +30%", Restricted Child Labor +10%; Primogeniture &
   Entail and Undivided Farm Succession "Late Marriage on the Farms +15%"; State Religion, the Millet System and People
   of the Book "Family Limitation Among the Literate −50%", Total Separation and State Atheism +50%; Serfdom and
   Manorialism "Wealth Concentration: Land Tenure +15", Tenant Farmers and both Latifundias +5, Peasant Proprietorship
   and Homesteading −10, Collectivized Agriculture −20; Graduated Taxation "Wealth Concentration: Taxes on Wealth −5";
   Laissez-Faire "Wealth Concentration: Economic Laws +10", Extraction Economy, Guilds and Chartered Monopolies and
   Freedom of Contract +5, Interventionism, Antitrust Enforcement and Regulated Utilities −5. None shows a raw key, each
   hover gives its description, and `debug.log` holds no `Unknown modifier type` for them.
2. **Wealth Concentration reads them (any rule).** The Demographics tab's Wealth section (Display only or Full) shows
   the Land Tenure, Taxes on Wealth and Economic Laws bars as before: a Serfdom country's Land Tenure bar is 15 × its
   farm share, a Laissez-Faire and Freedom of Contract one's Economic Laws bar +15. With the rule Disabled the
   Inheritance group's description shows the same national score as before the change.
3. **The census reads them (Full).** The workforce hover's working ages are unchanged: under Child Labor Allowed the
   10-14s still work at 30%. A Forced Heirship country that takes Undivided Farm Succession (The Last Division, or the
   console) has its farming states' marriage age rise at the next counts, as under Primogeniture; a State Religion
   country's Family Limitation rises half as fast with literacy as a Freedom of Conscience one's.

## UBI's working ages in the late game, and the Workforce row (2026-10-17)

Under UBI and Post-Scarcity a late-game state's working ages end at its blended old-age threshold, the one the
Demographics tab's Old age from row shows, no longer at the untreated's (`docs/systems/mod_systems.md` § Phase 2 step
1). A threshold of None ends them nowhere. The Workforce row and its hover now add up and name their scales. Pure
script order and loc, pinned by `test_demographics_late.py` and `test_demographics_work.py`, so no self-check.

1. **The EU test game (Full, UBI, longevity care).** Load `european union_2042_04_04` and pass a state's next census
   step (31 December). In the state of the report (save id 456, Old age from 128), the Workforce hover's working age
   reads about 99% of people where it read 50%, at work at most 100% where it read 127%, and workers past the end about
   0%; Census: Workforce is heading for about the term it has (+42%) rather than +19%.
2. **None (Full, UBI).** A state whose Old age from reads None counts nobody as past the working ages: its Workforce
   hover's "Past the working ages and still at work" reads 0.0%.
3. **The Workforce row adds up (country tab and state subtab).** Where people work past the working ages the row
   reads three terms, e.g. "50% × 99% + 14% = 64%", the middle one never above 100%; where nobody does (no pension
   law), two. The `+` term shows no stray space before it and nothing at all when it rounds to 0%.
4. **The state hover's scales.** The game's line names ×0.70 and the census's aim; the Full line's base plus "now"
   equals the "its pops are set to" figure, and its base plus "heading for" equals the aim (25% + 42% = 67%, 25% + 19%
   = 44% in the report's state before this fix).

## Log triage 2026-10-17: three self-checks' verdicts

The 2026-10-17 observer run (Full, a new 1836 game to 1898) logged three BROKEN lines. Two were the engine (their
fallbacks are in), one was the probe (fixed). The Self-checks table above has the new rows.

- **`working_conditions_read`: real.** `read=0.100` at a Walloon mine in January 1836, the table's laborers line at
  full size. Vanilla's code static modifier `working_conditions` applies to each building × (1 + its
  `building_working_conditions_mult`), and Workplace Safety takes −0.2 a level. The growth probe's 1949 capital read
  0 because France held Workplace Safety at five there (its save: investment 5), not because a building's read can't
  see the table. So the walk counted working conditions twice wherever Workplace Safety was below five, and once where
  the engine applied none. The constants are gone: the walk takes working conditions through the group reads alone.
  Under Display only and Full this lowers the walk's estimate of the engine's deaths in mining, logging, oil,
  plantation, rubber and industry states, by the table's share of their workers' deaths (about 1% of curve deaths in
  the probe's 1949 world): their migration residual reads that much less immigration, and under Full the deaths the
  census counts on top of its own (the Causes of Death section's "other effects on some of its people") fall with it.
  The spec's §2.1 choice for building-scope lines (bare weight or the census's rate) is still the owner's to redo; the
  walk keeps bare weight.
- **`unemployment_rate_read`: real.** `read=0.048 pops=0.195` in Mecklenburg-Strelitz: a quarter, about the
  workforce's share of the people in 1836, so the engine's `state_unemployment_rate` reads as the idle workforce over
  all the state's people (vanilla's own `mon_unemployment_estimate` doubles it, "way off actual unemployment rate"). The
  youth bulge took it as a share of the workforce, the harness's figure, so it saw about a quarter of the unemployment
  it was fitted on. The documented fallback is in: the walk counts the workforce of pops with no workplace over all
  the workforce (`te_dg_unemp`, `te_demog_work_walk_pop`), and the youth bulge, the event wave's Youth Bulge and the
  pension AI read that. The AI's 10% and 5% now bite at a tenth and a twentieth of the workforce, so it picks Early
  more often than it did. The self-check now tests the diagnosis (the engine's figure against the count × the
  workforce share); nothing in the census read the engine's figure any more, until the follow-up below.
  **Owner's follow-up (2026-10-17):** one source for every reader. The census now stores the shared conversion,
  `te_state_unemployment_share` (the engine's figure over the workforce's share of the people,
  `te_unemployment_values.txt`), as `te_dg_unemp` at its walk, and keeps the walk's count beside it as
  `te_dg_unemp_walk`, which the self-check now reads and which is the fallback. Where the engine's figure is per
  person, the two agree and nothing the census does moves. The youth bulge was fitted on the pops' count, which the
  harness still takes from a save (`demographics_save_inputs.state_unemployment`), so the fit stands while the
  self-checks read OK. The workforce share it divides by is up to a year old (the conversion's yearly walk), and a
  state the census walks first takes the census walk's own.
- **`workforce_follows_target`: the probe.** Braunschweig's capital: W landed in 1837 from the moved lines' pair
  (0.039) and fell to 0.002 by 1842, its target. The engine stood at 0.249 at the landing, about 0.04 below the 0.289
  its pops were set to, and at 0.252 in 1842, beside the 0.252 they were set to then. W's fall brought the set ratio
  back to the engine, so no move was due (0.003), yet the check asked for half of W's move the other way (0.018). Both
  a fast and a slow pull end at 0.252 here, so the line said nothing about the pull. The check now asks for half of
  the move from the engine's figure at the landing to the ratio set now, and arms only where that move is at least
  0.03. The 1898 save (all census states with 50,000 people or more, n = 788) reads engine ≈ 0.89 × the pops' bases +
  0.52 × W + 0.02: the engine carries about half of W by then, with gaps of 0.02 where W is 0.02-0.05 and 0.06-0.07 in
  Sweden's states (W 0.10-0.11). That leans slow, but W's history is not in a save; the corrected check decides.

What the next game should show:

1. **`working_conditions_read`** OK, `read` ≈ `expected` = 0.1 at `scale=1.00` in 1836.
2. **`unemployment_rate_read`** OK, `read` near `per_people`, `census` ≈ `walk`, and both four times or so `read` in 1836.
   `unemployment_share_read` (any rule, `docs/testing/ai-economy-playtest.md`) agrees: the same fact, read from its own walk.
   **Once both have read OK in a game or two, remove `unemployment_rate_read` and the walk's own count behind it**
   (`te_dg_unemp_walk`, option t's `unemp_walk=`; owner, 2026-10-17). `unemployment_share_read` stays as the one check.
3. **The youth bulge (Full).** A state whose census counts more than a tenth of its workforce idle and whose 20-29
   share is above 0.18 shows the Youth row with an unemployment part about four times what it showed, and its modifier
   at that multiplier; option t's `unemp=` (the stored conversion) is about its `unemp_walk=` (the walk's own count).
4. **`workforce_follows_target`** may not come in an 1836 game's first decades: it needs a capital whose set ratio
   moved 0.03 from its engine figure. Its OK or BROKEN, when it comes, is the pull's verdict for the ramp.

## The panel on Banking's model (issue #1029)

The Demographics tab and the state subtab rebuilt on the Banking panel's pattern: an overview of eight icon cells,
Causes of Death with a pie at both levels, the pyramid, the levers, History's eight charts with pips, and States rows
that open the state. The order, collapse flags, type sizes and widths are pinned offline by
`test_demographics_layout.py`; deaths by cause by `test_demographics_cause_deaths.py` and its self-check, above. What
only the game can show:

1. **The overview (Display only or Full, both hosts).** Eight cells, two to a row, none cut off: the census year
   above, then Natural Change and Net Migration, Life Expectancy and Leading Cause, Fertility and Median Age, Working
   Age and Gini. Before the second count the stepped figures read "Next count" in grey; the arrows show from the
   third. Each cell's hover is the old row's; Life Expectancy's adds women's and men's figures (on an old save, a grey
   line until 31 December). The icons are placeholders (`docs/systems/demographics_gui_icons.md`):
   note any that reads badly at 44 px.
2. **The pie (Display only or Full, after the first step).** Causes of Death shows a ringed pie, slices clockwise from
   12 o'clock in the legend's order, its colours matching the legend's swatches, and the slices' shares adding to
   100%. A state with war dead shows a War slice. Under Full the Added on Top slice and row appear; under Display only
   it stays 0. The country's pie is its states' summed. If the pie draws a single colour or nothing, the stacked
   progresspie recipe fails here: `gui_modding_guide.md`, "Pie charts of script-held data", has the bar fallback.
3. **The legend's hovers.** Each cause row's hover gives its rate against a poor country's, ×m, and its factors (the
   state's own; the country's by people, with the capital's). The Deaths and Share columns hold their longest figures
   without eliding.
4. **History (a tracked country, a few decades in).** Eight charts: Births and Deaths per 1,000, Net Migration, Life
   Expectancy, Children per Woman, Median Age, Deaths by Cause (stacked, in the pie's colours), Gini and Wealth
   Concentration. A year with war dead shows a red pip over its bars, a famine month an amber one, a demographic event
   (the event wave) a blue one, and the key under the charts names them. Hovering a bar names the year's marks.
5. **States (the country tab).** Ten rows, largest first, each the state's name, people, life expectancy, median age,
   children per woman and Gini; Show All appears with more than ten census states and shows them (up to 40; past 40
   the button says so). A click on a row opens the state panel: note **which tab and subtab it opens on**. The row
   sets the Population subtab to Demographics, but the state panel may open on another tab, in which case the click
   lands one tab away from the census. Hovering a row highlights the state; a right click opens its menu.
6. **The state subtab.** The census line names the next count ("Census of 1850, the next in 5 months", "in a month",
   "this month"), a year after the state's last. The subtab's sections follow the country's order, less Family Policy, History, Where People Live and
   States.
7. **Type sizes.** Rows at 17, headings at 20, the overview at 16: nothing overlaps or elides at 1080p and at the UI
   scale the owner plays at.

## The state's Wealth Concentration terms (2026-10-18)

The state subtab's Wealth section lists What Sets the Target under the score's bar, as the country tab does: the
Inheritance law, land tenure, who owns capital, income inequality, taxes on wealth and the economic laws. Land tenure,
ownership and inequality are the state's own; the law, tax and economic terms are its owner's, read through
`State.GetOwner.MakeScope` (a new read in this file, though `states_panel.gui` uses it). What only the game can show:

1. **The rows render (Display only or Full, a scored state).** Six pillars, each with a bar and a signed figure, none
   blank. 50 plus the six figures is the target in the score row (`te_demog_st_wc_value`), unless the target is at 0
   or 100, or Continuity of Title holds.
2. **The owner's terms.** Open a foreign state on its Demographics subtab: the law, tax and economic rows show its
   owner's laws, not yours.
3. **Land Tenure's hover** gives the state's share of peasants and farmers as a percentage (`te_dg_agr_share`).
4. **Continuity of Title.** While it holds (`inheritance_events.6`), the note under the rows shows.

## Adults' infection and the late carriers (#1045, 2026-10-18)

Infection at ages 15-64 takes medicine a second time (`te_demog_infection_adult`, the local `te_dg_inf_ad`), so a rich
state's adults die of infection at the rich world's rate in eras 9-10, and Personalized Medicine (era 11) and Advanced
Nanofabrication (era 12) take infection treatment to its new cap, 0.99. `test_demographics_registry` and
`test_demographics_cause_deaths` hold the life table, the Causes of Death estimate and the late sweep's count to the
model; `demographics_harness.py lategame` prints the 15-44s' infection deaths by era. No new engine fact (a local and a
script value, as the other factors), so no self-check. What only the game can show:

1. **The hover's line (Display only or Full).** In a state with antibiotics, the subtab's Infection and Hunger hover
   ends its factors with "Aged 15–64, a further ×0.xx"; a state with no infection treatment (an 1836 colony) shows no
   such line. A rich state reads about ×0.25; a state whose last count came before the change reads its stored
   medicine, so the line is right at once, while its life expectancy and deaths move only at its next count.
2. **The pie (a rich country, Display only or Full).** Infection and Hunger's slice is smaller than before: today it
   should sit well under chronic illness and accidents and violence in a rich state.
3. **The technologies' tooltips.** Personalized Medicine shows Treatment of Infection +3% beside its chronic line;
   Advanced Nanofabrication +2%.
4. **Immortals (Full or Display only, a country with Biological Immortality and everyone in care).** The state's
   Leading Cause is Accidents and Violence, and infection is a sliver (the harness: 3% of deaths at 50 years).
5. **The outline.** The Demographics tab's twenty-year outline moves with the state figures (the country's factor,
   `te_dg_inf_ad`, set at each count beside access).

## Women at work and families among migrants on their carriers (modifier-types stage 3, 2026-10-19)

The migrant profile's two inputs were a `has_law` ladder and a `has_technology_researched` ladder; they are now
census-only types on their carriers, so each law's and technology's tooltip says what it does (`docs/systems/mod_systems.md`
§ The census, Flows). The values are the old tables', so no figure moves, except that Commercial Aviation and Jet Engine
Technology now add families too, which moves a late-game state's migrant profile toward families. No new engine fact: a
state type on a tech's or law's `modifier` read in state scope is check a (option l, 2026-10-10), and a mod tech carrying
a census type is the Contraceptive Pill's. So no self-check. What only the game can show:

1. **The tooltips.** Women in the Fields "Women's Work Outside the Home +15%", Women Own Property +20%, Women in the
   Workplace +35%, Women's Suffrage +37%, Protected Class +38%; No Women's Rights shows no such line. Paddle Steamer and
   Railways "Families Among Migrants +10%", Combustion Engine +15% (beside its Deaths from Violence and Accidents line),
   Commercial Aviation and Jet Engine Technology +5%. None shows a raw key, each hover gives its description, and
   `debug.log` holds no `Unknown modifier type` for them.
2. **The capital's reads (option l, any rule).** `TE_DEMOG_WORK` logs `fws=` (0.10 under No Women's Rights, 0.48 under
   Protected Class) and `fam_mig=` (0.20 with Paddle Steamer and Railways, 0.55 with all five).
3. **The census reads them (Full or Display only).** A state with net migration keeps the profile it had before the
   change, unless its owner has an aviation tech: there the young-adult bulge of its arrivals or departures is a little
   flatter.
