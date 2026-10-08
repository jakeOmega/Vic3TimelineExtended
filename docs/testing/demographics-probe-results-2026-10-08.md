# Demographics engine probe results — 2026-10-08

**Tester:** Jake, repository owner. **Game:** Victoria 3 1.14.5. **Mod revision:** `f0265ba4` plus the probe
(local branch `probe/demographics`, one commit, not merged). **Other mods:** none.
**Run:** a fresh 1836 game as Great Britain, played unpaused from 1 January 1836 to 24 February 1837. The probe ran
by itself from the first monthly pulse, one stage a month, and wrote `TE_DEMOG` lines to `debug.log`. Saves were made on
1 January 1836 (`great britain_temptst.v3`, before the probe's first pulse) and after the benchmark
(`great britain_temptst2.v3`).

It answers the engine checks in [the demographics design](../superpowers/specs/2026-10-08-demographics-design.md) § 14.
The spec now states each answer where the design uses it; this file keeps the evidence.

**Read the numbers with these limits:**
- **One save, one country, 1836.** Every number comes from the first fourteen months of one game. The benchmark has
  not been run in a late-game save.
- **The natural-change check failed.** Its birth and death curves used literals with six decimal places, which the
  engine rejects at load (finding 1 below). Its predicted births and deaths are wrong, so this file uses only the
  populations it logged. The births side is checked through Qing instead (Q7).
- **Large numbers were logged in groups** (`2_803_898` is 2,803,898; a group drops its leading zeros, so `0_490_84` is
  490,084). They are written out in full below.

## Engine facts the run settled

| § 14 | Question | Answer |
|---|---|---|
| Q1 | Can one pop walk fill several sums? | **Yes, every way tried.** All three forms gave sums identical to one script-value walk per sum in London (94 pops): local variables (`change_local_variable` from pop scope), the state's variables (`state = { change_variable = { add = PREV.total_size } }`), and a named pop-scope script value read through `PREV` (`add = PREV.te_dp_pop_lit`) |
| Q1 | The same for a building walk | **Yes.** One walk summed levels × each ownership fraction into local variables; the results matched the script-value walks |
| Q2 | Ownership fractions as values | **Yes.** `add = private_ownership_fraction` and `multiply = …_fraction` read the value. London: 650 levels = 103 private + 390 self + 157 country. The trigger-only brackets agreed |
| Q2 | What "self-owned" covers | **The ownership buildings own themselves.** Britain's three largest buildings were a Manor House (173 levels) and a Financial District (159), both reading self = 1, and a Subsistence Farm (140) reading private = 1. A Construction Sector read country = 1 |
| Q2 | Foreign ownership | `"fraction_of_levels_owned_by_country(scope:x)"` reads as a value. It returned 1 for every London level, self-owned and state-owned included. So the foreign share is 1 minus it |
| Q3 | `wealth_share` as a value | **No.** `"wealth_share(pop_type:aristocrats)"` fails at load (`PostValidate of trigger 'wealth_share' returned false`) and reads 0. The block trigger works, but measures political strength from wealth: GB's aristocrats passed `value > 0.2` while holding 2.8% of the country's pop wealth × size (6.34M of 225.75M) |
| Q4 | War counters as values | **Yes** in war scope: `"num_country_dead(scope:x)"`, `"num_country_wounded(…)"`, `"num_country_casualties(…)"` and `add = num_dead`. Casualties = dead + wounded on every line, and `num_dead` is the dead of all sides |
| Q4 | Do the counters survive the war's end? | **Probably not.** At `on_war_end` the war scope still exists (ROOT, the diplomatic play, has a `war`), but all counters printed 0. The line had no control value, so a register that fails to print under a diplomatic-play ROOT would look the same. Seven wars ended during the run and all seven read 0. At least five had logged casualties the month before: their lines vanish from the next month's war lines (12 → 8, 8 → 4, 4 → 2) |
| Q5 | Does `modifier:state_birth_rate_mult` on a state include country modifiers? | **Yes.** A test modifier on the country (+0.0123 births, +0.0456 mortality, +0.0078 working adults) raised a non-capital state's reads by 0.012, 0.045 and 0.008. A second one on the capital added its own share on top (+0.0789 births, +0.0321 mortality) |
| Q7 | What happens below a total birth multiplier of −1? | **At −3 births stopped; they don't turn negative.** At −0.9 they ran at about a tenth. Between the two is unmeasured. See [Q7](#q7-the-birth-floor) |
| Q9 | Cost of the yearly cohort step | One run across all 887 states: 5-year cohorts about 0.1–0.15 s, 1-year cohorts 0.75–1.0 s. See [Q9](#q9-benchmark) |
| — | When do the pulses fire? | **The yearly state pulse is spread over the year:** GB's 26 states fired on 26 different days, from 20 March 1836 to 17 January 1837. The yearly country pulse fired on 31 December. The monthly country pulse comes every 30 days at a per-country offset (30 January, 1 March, 31 March …). The capital's monthly state pulse came on a different day (25 February, 27 March, 26 April) |
| — | The year as a value | `add = year` gives 1836 |
| — | #822's `te_inh_agrarian_share_value` | **Correct.** London 0.174, the same as a bareword `divide = state_population`. Its nested `divide = { value = state_population min = 1 }` works, despite `scripting_best_practices.md`'s warning about nested `value =` population reads |

**Finding 1: a literal may have at most five decimal places** (already in `scripting_best_practices.md`; this run adds
that such a literal reads as 0). Every literal with six, including trailing zeros
(`0.025000`, `-16.458333`), logs `Badly read script value <x> at <file>:<line>` at load and reads as 0. The benchmark's
seeds were `state population × 0.025000`, and the save stored every one as 0. `0.01234` (five places) printed exactly.

## Q7: the birth floor

The test country was the most populous AI country at peace: **Qing**, 366.7 million, with a country-level birth
multiplier of +0.05. Each state's total birth multiplier was recorded before the test. A −1 birth modifier was then
added, with a multiplier that brought the total to −0.9 (phase A) and then to −3 (phase B).

| Month (pulse to pulse) | Birth multiplier | Qing's population change |
|---|---|---|
| 30 Jan → 1 Mar | about +0.05 (none added) | +211,937 |
| 1 Mar → 31 Mar | −0.9 (applied 1 Mar) | −1,378,950 |
| 31 Mar → 30 Apr | −0.9 | −1,325,244 |
| 30 Apr → 30 May | −3 (applied 30 Apr) | −1,447,908 |
| 30 May → 29 Jun | −3 | −1,516,252 |
| 29 Jun → 29 Jul | removed 29 Jun | −43,264 |
| 29 Jul → 28 Aug | none | +193,588 |

Assuming births follow 1 + the total, the baseline and phase A give 1.049 × B − D = +0.212M and
0.1 × B − D = −1.325M. That gives base births
B ≈ 1.62M a month (0.44% of the population, against the define's 0.475% at SoL 11 and below) and deaths D ≈ 1.49M
(0.41%). For phase B the hypotheses predict:

| If a total below −1 … | Predicted monthly change | Observed |
|---|---|---|
| gives negative births (1 − 3 = −2 × B) | −4.73M | |
| stops births (floor at 0) | −1.49M | **−1.52M** |
| counts as −0.9 | −1.33M | |

Adding phase A showed in full in its first month (−1.38M against −1.33M the month after). The switch to phase B
showed only partly in its first month (−1.45M against −1.52M), and the month after removal recovered only part of the
way (−43,264) before the next was back to normal. So a change shows within a month, not at once.

## Q9: benchmark

Generated script, 30 five-year slots or 150 one-year slots per state, each slot running the § 2.1 step (five causes of
death for women, four for men, births from women 15–49, then a scale pass to the engine's population). It ran across
every state in the world: 887 states, 25,046 pops, 31 March 1836. `debug.log` timestamps are whole seconds, so a
time is a span of whole seconds divided by the runs inside it.

| Variant | Runs | `debug.log` span | Per run |
|---|---|---|---|
| 5-year, 20 of 30 slots occupied (ages 0–99) | 10 | 17:05:56 → :57, after seeding | about 0.1 s |
| 5-year, all 30 occupied | 10 | :57 → :59 | about 0.15 s |
| 1-year, 100 of 150 occupied | 4 | :59 → 17:06:02 | 0.75 s |
| 1-year, all 150 occupied | 4 | :02 → :06 | 1.0 s |
| Pop walk, 8 script-value walks per state | 3 | inside 17:06:06 | under 0.1 s |
| Pop walk, one effect walk into 8 local variables | 3 | inside 17:06:06 | under 0.1 s |
| Building walk, 4 script-value walks per state | 3 | inside 17:06:06 | under 0.1 s |

For scale, a game month took 11–16 s of wall-clock time at the speed played (`TICK` lines: 16, 15, 13, 13, 13, 12, 11,
12, 13, 12, 14, 14 s; the benchmark month took 36 s, including the stall and a save).

**Save size.** The second save carried the full one-year ring: 266,100 variables (887 states × 300) plus 10,644 walk
results. In the plain-text save each takes **61 bytes** (`{ flag=… data={ type=value } }`, no `value=` line because
every value was 0). A non-zero value adds a `value=` line, about 25 bytes more. The variables came to 16.9 MB of the
file's 48.5 MB growth (197.4 MB to 245.9 MB); the rest is three months of ordinary game state.

## Observations for the calibration harness

Not § 14 questions, but measured in the same run (populations from the `NC` lines):
- **World growth, early 1836:** +843,283 in the first month (+0.085%), about 1.0% a year. The world without Qing grew
  +458,000 to +631,000 a month (0.07–0.10%) across the run.
- **Great Britain shrank every month:** −14,715 to −22,914 a month, −0.06% to −0.09%. Natural growth at its SoL should
  be positive, so this is most likely emigration. The harness's Britain case has to include migration.
- **Qing's crude rates** under today's defines: births about 53 per 1,000 a year, deaths about 49.

## The older `TE_PROBE_LOC` probe

The loc-accessor probe from #488 (`common/on_actions/te_debug_probe_on_actions.txt`, marker `_v3`) fired in the same
game and finally logged. Kept here so the result can't rotate away again; acting on it is a separate change.

| Line | Accessor | Printed (7 is correct) |
|---|---|---|
| 1 | `THIS.GetVariable('x').GetValue` | 7 |
| 2 | `SCOPE.sCountry('c').GetVariable('x').GetValue` | `Data error in loc string` |
| 3 | `THIS.GetCountry.MakeScope.Var('x').GetValue` | 7 |
| 4 | `SCOPE.sCountry('c').MakeScope.Var('x').GetValue` | 0 (silently wrong) |
| 5 | `THIS.Var('x').GetValue` | 7 |
| 6 | `SCOPE.ScriptValue('sv')` | 7 |
| 7 | `THIS.GetCountry.MakeScope.ScriptValue('sv')` | 7 |
| 8 | `SCOPE.sCountry('c').MakeScope.ScriptValue('sv')` | −1 (the wrapper's "unset") |
| 9 | `THIS.ScriptValue('sv')` from the capital | 9: the current scope |
| 10 | `SCOPE.ScriptValue('sv')` from the capital | 7: ROOT |
| 11 | `SCOPE.ScriptValue` of a value that reads a saved scope | −1: the saved scope is invisible to it |

The demographics probe saw the same thing from another side. A scope saved with `save_scope_as` inside an
`every_country` loop printed an empty name through `[SCOPE.sCountry('x').GetNameNoFormatting]`. On `on_war_end` the
engine's own `scope:actor` and `scope:target` printed their names.
