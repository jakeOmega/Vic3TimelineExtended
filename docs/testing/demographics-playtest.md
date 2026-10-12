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
| `TE_SELF_CHECK … famine_reserves_absorbed` | any rule, development builds only: once a game, a week after the first country whose Landowners are powerful and whose capital has a subsistence-farm pop reading Famine Reserves at its farm (1836 India: the first monthly pulse), on one such pop (`te_debug_demog.40`). No line in a game's first weeks isn't BROKEN: it arms at the first monthly pulse and logs a week later | what the census absorbs for the pop (its owner's read of the agriculture mortality key) equals what the walk reads at its farm (`absorbed` = `walk`, both about −0.2: the trait's −0.1 doubled by the group's power) | `absorbed` 0: a `building_group_*` key reads 0 at country scope, so under Full the census absorbs nothing of the trait and India's deaths stay off. `walk` = `ratio` × `absorbed`, the ratio 2 or 0.5: the group's power reaches one read and not the other | absorbed 0: set `COUNTRY_ABSORBED_FROM_FARM = True` in `demographics_params.py` and regenerate (`gen_demographics.py`): the census absorbs the farm's own read on subsistence farms only, which holds no building-scope line, and commercial farms' workers keep the trait on top. A ratio: set `COUNTRY_ABSORBED_SCALE` to it and regenerate. Either way refit (the spec's §3) |
| `TE_SELF_CHECK … working_conditions_read` | any rule, development builds only: once a game, a week after the first country with a mine outside its capital (`te_debug_demog.41`) | a mine outside the capital reads working conditions' laborers line as about 0, as the capital did in the 2026-10-09 growth probe: the walk's constant is its only copy | `read` about 0.1: the building's read carries the table, which the walk also adds as a constant, so the walk counts working conditions twice (the spec's 2.4× regression) | drop the constants from `te_demog_pop_death_mult` (`gen_demographics.py`, `engine_rate_terms`), regenerate, and redo the spec's §2.1 choice for building-scope lines |
| `TE_SELF_CHECK … malaria_trait_read` | any rule, development builds only: once a game, the first month a country with Quinine owns a state the map files give the mild malaria trait | `has_state_trait` still reads the trait there (`trait_read=1`, `level=1`), though Quinine has switched the trait's modifier off: the malaria factor lasts until Malaria Prevention, as built | `trait_read=0`: the trait test stops at Quinine, so the census's malaria factor ends with it in every game | set `MALARIA_READS_REGION_LIST = True` in `demographics_params.py` and regenerate: the census reads the level from the state regions the map files give the traits (`te_demog_malaria_level_listed`) |
| `TE_SELF_CHECK … pop_workforce_read` | Display only or Full: once a game, at the first country monthly pulse after a capital's walk | a pop's `workforce` reads as a value in the walk (`wf_engine` about 0.2-0.3) | `wf_engine` 0: the walk can't read the engine's workforce | nothing in step 1 uses it; step 2's stop rule (spec §1.8) needs another read of the engine's workforce before its fit |
| `TE_SELF_CHECK … measure_country_types` | once a game, under Full: `START` when the first measure that moves desired family size goes on in any country (Child Allowance, Honours, Parental Leave, Later Longer Fewer, Birth Limit, the Crash Campaign; the AI's included), the verdict a week later from the capital (`te_debug_demog.10`) | the capital's read of the script-only `state_desired_fertility_mult` rose by the measures' lines its owner gained (`added` ≈ `expected`): a script-only state type on a country static modifier reaches the states | `added` reads 0: the census sees none of the measures' types, so no measure moves births (step 3b's census reads them from the state); `NO_VERDICT` (the measure ended within the week) re-arms the check | put each measure's census types on a state modifier in each of the country's states, applied and removed with the country modifier and re-applied by the yearly state pulse (inheritance's rural modifiers' pattern), and keep the interest groups and upkeep on the country |
| `TE_SELF_CHECK … workforce_ratio_scale` | Display only or Full: once a game, at the first capital census step before any workforce term (a 1836 game: its first year) | the walk's `wf_engine` is nearer `per_people` (the set ratio as workforce over people: about 0.25 in 1836) than `per_dependents` (the same as workforce over dependents: about 0.20). The spec §1.8's stop rule, as built | `wf_engine` near `per_dependents`: the engine's ratio is workforce over dependents | re-derive `WORKFORCE_SCALE` and W on that scale (spec §1.8) and refit with `demographics_harness.py workforce SAVE`. Offline the 1836 save already reads over people: 82% of the world's people hold exactly 0.250 (§ Phase 2 step 2) |
| `TE_SELF_CHECK … workforce_follows_target` | Full: once a game, at a capital's census once its workforce term has run five census years and moved at least 0.03 since it landed | the walk's `engine` figure has moved W's way since the landing (`engine_at_landing`) by at least half of W's move (`needed`); `set` and `census_target` say how far the ramp still has to go. Not a gap to the set ratio: the saves show the game's figure sitting 0.01-0.03 off its ratio in steady state | `engine_moved` under `needed`: the engine's pull is slower than the ramp, so the ramp adds nothing | set `WF_RAMP_STEP` large (the term lands at once, and the engine's own pull is the lag) and keep the panel's engine figure beside the target; no line at all after many years means no capital's term moved 0.03 (option r shows the capital's) |

No `primogeniture_scaled` line at all after a game's first year means no state took the line fresh: no country had Primogeniture, or the game was continued from a save where every Primogeniture state already held it. Start a new game, or enact the law. A `START` with no verdict means the state changed hands within the week; the check doesn't run again in that game. No `measure_country_types` line means no measure that moves family size went on (start Child Allowance under Pro-Natalist Policy); a `START` with no verdict, that the capital changed hands within the week.
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

## Calibration step 3: the regional mortality gap

Spec: `docs/superpowers/specs/2026-10-12-demographics-calibration-step3-design.md` (owner calls 1–3, 2026-10-12). Under
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

The measures and their panel (`docs/superpowers/specs/2026-10-12-demographics-phase2-consequences-design.md` §3.3-§3.7).
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
3. **Honours, Later Longer Fewer, Birth Limit, the Crash Campaign**: authority falls by 25, 50, 100, 100. Sex
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
outside Full nothing changes. Spec: `docs/superpowers/specs/2026-10-12-demographics-phase2-consequences-design.md` §2.
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
  whether the engine's figure follows a change of W (half of W's move within five years).

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
