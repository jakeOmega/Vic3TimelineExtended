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
| `TE_SELF_CHECK … primogeniture_scaled` | once a game: `START` when the first state with a farm share between 0.1 and 0.9 takes Primogeniture's farm line fresh (a Primogeniture country's first yearly state pulse), the verdict a week later | the engine sums a script-only type on a state modifier scaled by its multiplier (`added` ≈ `expected`) | `added` reads 0.1 (the multiplier is ignored) or 0 (the type isn't summed): Primogeniture's farm births are wrong in every game | Plan B of `docs/superpowers/plans/2026-10-11-demographics-late-marriage.md`, Task 9 |
| `TE_SELF_CHECK … workforce_amendment_type` | any rule, development builds only (a release comments the inputs out and turns the check off): once a game, a week after a country first holds Community Service or Mandatory Minimums on its criminal-justice law | the engine sums a script-only type from an amendment into a state's read (`read` = `expected`) | `read` = `laws_only`: the two amendments' moved working-adult lines are lost in every game | revert both amendments' blocks (`common/amendments/extra_amendments.txt`) to `state_working_adult_ratio_add` at their old values, list them in `P.LIVE_WORKFORCE_LINES` and take them out of `TestWorkforceLinesMoved.BLOCKS` (phase 2 step 1 plan, D12) |
| `TE_SELF_CHECK … workforce_ig_trait_type` | any rule, development builds only: once a game, a week after a country's Trade Unions are first loyal at the trait's plain size (clout neither marginal nor powerful) with no Ministry of Labour law | the engine sums a script-only type from an IG trait into a state's read (`read` = 0.02), and the INJECT added to vanilla's trait block (`remainder` about 0) | `read` 0: the type isn't summed; `remainder` about −0.05: the INJECT replaced vanilla's block. Either way the Trade Unions' two loyal traits' lines are lost in every game | delete `common/interest_group_traits/te_demog_workforce_injections.txt` (vanilla's +0.05 comes back on the engine field), list the two traits in `P.LIVE_WORKFORCE_LINES`, take them out of `TestWorkforceLinesMoved` and accept their two `vanilla_parsed` carriers as live |
| `TE_SELF_CHECK … workforce_lines_net` | any rule, development builds only: once a game, a week after the first country's first monthly pulse, in its capital | the capital's working-adult field less the moved lines' pair is about 0: every vanilla carrier's INJECTed cancel nets out against its own line | `remainder` not 0: an INJECT replaced a vanilla block (a law, Woman Soldiers or a Trade Unions trait), so its cancel stands alone in every game (or the capital has Rosen's androids, which can't happen in 1836) | revert that carrier's INJECT and list it in `P.LIVE_WORKFORCE_LINES`; option l's `TE_DEMOG_MODS` lines show which carrier |
| `TE_SELF_CHECK … pop_workforce_read` | Display only or Full: once a game, at the first country monthly pulse after a capital's walk | a pop's `workforce` reads as a value in the walk (`wf_engine` about 0.2-0.3) | `wf_engine` 0: the walk can't read the engine's workforce | nothing in step 1 uses it; step 2's stop rule (spec §1.8) needs another read of the engine's workforce before its fit |
| `TE_SELF_CHECK … conscription_term_read` | Full: once a game, a week after the first state takes a fresh conscription term of at least 0.005 either way (most states' first count under Full) | the census's conscription pair reaches the state's conscription multiplier (`added` = `expected`, the term) | `added` 0: the pair doesn't reach the state's read. Another figure: a technology or law moved the field inside the week, which says nothing either way: read the state's conscription tooltip for "Census: Fighting-Age Men" | for `added` 0, put the term on `state_conscription_rate_add` as T × the state's own rate (`modifier:state_conscription_rate_add`, read in the refresh, ROOT the state). Whether the read moves the state's conscript battalions is item 2 of § Phase 2 step 4: no script reads them |
| `TE_SELF_CHECK … unemployment_rate_read` | Display only or Full: once a game, the first census state whose `state_unemployment_rate` reads above 0.02 | the read is a share, 0–1: within a factor of 2 of the pops' own count (`pops=`, the workforce of pops with no workplace over all the workforce) | `read` about 100 × `pops`: a percentage. `pops` near 0, or the two far apart otherwise: the read is another figure. Its count sums each pop's `workforce`, so it needs `pop_workforce_read` OK first: with that BROKEN, `pops` reads 0 and this line BROKEN whatever the read | a percentage: divide `te_demog_unemployment` (`te_demog_consequence_values.txt`) by 100. Otherwise sum the unemployed workforce in the walk under the cohorts (`te_demog_work_walk_pop`) and read that |

No `unemployment_rate_read` line after a few years under the census means no state's read ever passed 0.02: compare option t's `unemp=` with the state panel's unemployment in a state with visibly idle workers.
No `primogeniture_scaled` line at all after a game's first year means no state took the line fresh: no country had Primogeniture, or the game was continued from a save where every Primogeniture state already held it. Start a new game, or enact the law. A `START` with no verdict means the state changed hands within the week; the check doesn't run again in that game.
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
should move in any game. Spec: `docs/superpowers/specs/2026-10-12-demographics-phase2-consequences-design.md` §1.10;
plan: `docs/superpowers/plans/2026-10-12-demographics-phase2-interfaces.md`, Task 8. The three workforce self-checks
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

## Phase 2 step 4: conscription, the youth bulge and sex balance

Under Full the census sets each state's conscription from its men aged 20 to 39 against the 1836 world's share and adds
a youth-bulge modifier where young adults are many and work is short; the war dead come from the same ages, under
Display only too. The sex balance's effects are built but held back (`demographics_params.SEX_BALANCE_EFFECTS`, off until
the follow-up on the census's migrant profile), so the census counts and shows the balance and applies nothing from it. Spec: `docs/superpowers/specs/2026-10-12-demographics-phase2-consequences-design.md`
§4; no plan document (owner, 2026-10-12). The two self-checks are in the table above.

1. **The 1836 figures (Full, a new game).** Option t in the capital after its first count (`TE_DEMOG_CONSEQ`): `share`
   about 0.139, `term` and `mc` within ±0.05 and equal, `consc_mod` holding `mc` beside any law's or technology's line,
   `youth` about 0.16, `y_now` and `yb` 0, `sex` 91–98; `sxb` -1, `tfr_sex` 1 and `women_add`, `fewer`, `more` 0 in every
   state while the sex balance's effects are held back. The country line: `fam_share`
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
   row's hover gives; option t's `unemp=` matches the state panel's unemployment (the self-check's scale).
5. ~~**The sex-balance modifiers (Full).**~~ Held back with the switch: no state lists "Census: Fewer Men" or
   "Census: More Men", even one far from 100 men per 100 women; its Sex Balance hover says the effects aren't applied
   yet, and children per woman's breakdown has no "Few men to marry" line. The follow-up that turns them on brings its
   own items.
6. **Display only and Disabled.** No state lists any of the census's modifiers (option t: `mc` and `yb` -1); the
   Fighting-Age Men row's hover says "would set"; the Youth row still shows where a bulge would be. Switching a Full game
   to Display only isn't possible mid-game: start one of each.
7. **The panel's rows.** Fighting-Age Men reads like "28% (×1.00)" on the tab and the subtab, nothing ends in "…", and
   the hover gives the share of people and the 1836 reference; an old save's census reads "After the next count" until
   the state's next count. The sex balance's hover ends in "not applied yet".
8. **`debug.log`:** no "Failed to fetch variable" or script errors from `te_demog_consequence_*`,
   `te_demog_sex_births_store`, `te_debug_demog.30`, `te_debug_demog_unemployment_selfcheck` or option t.
