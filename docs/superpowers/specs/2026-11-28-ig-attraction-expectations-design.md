# Interest Group Attraction Against Expectations: the Petty Bourgeoisie in the Late Game

Date: 2026-11-28. From the owner's brainstorm of the same day. Rulings marked
**owner** are the owner's. Everything else is the designer's call, and the
owner may revisit any of it with a stated reason. The numbers are first guesses
from an offline model (§ 8), for the builder to tune. Nothing here is built.

The owner was away when this was written up. Three of the designer's calls
change something the owner saw in the brainstorm: the cap in § 6.1, the
Unions' steady state in § 6.5, and the floor correction in § 6.2. § 10 lists
them, with the way back from each.

Background:
- `docs/vanilla/vanilla_politics_reference.md` § 5.3 (attraction)
- `docs/systems/mod_systems/sol_expectations.md` (the expectations system)
- `docs/superpowers/specs/2026-10-25-first-past-the-post-design.md` (the same
  restate-from-a-generator pattern, for party join weights)
- `ig_feminism.py`

## 1. Why

The owner's one complaint about late-game politics is the strength of the Petty
Bourgeoisie (**owner**). The saves bear it out. Mean clout share in the 20
largest economies:

| Year | AF | Devout | Ind | Intel | Land | PB | Rural | TU |
|---|---|---|---|---|---|---|---|---|
| 1964 | 6 | 22 | 17 | 9 | 7 | 20 | 8 | 11 |
| 2050 | 11 | 16 | 9 | 14 | 1 | 34 | 3 | 12 |

- In 2050 the PB pass 40% in 9 of the 20 and sit in government in 17 of 20.
- Landowners and Rural Folk fall to 1–3%. That is out of scope here (§ 11).
- **The saves:**
  - `te_qa_copy_usa1964_20261126.v3`
  - one later world, in three saves: `te_qa_copy_iua_20261124.v3` (2032),
    `te_qa_copy_iua2043_20261125.v3` and `te_qa_copy_iua2050_20261126.v3`
- **The later world is the owner's all-technology USA game.** ARA, CST and D60
  are the USA's subjects. The calibration in § 8 leaves the USA and its
  subjects out, which leaves 20 countries over 5 million people in 2050.

## 2. What vanilla does, and why it fails late

The PB's attraction (`00_petty_bourgeoisie.txt`, `pop_weight`) grows with
absolute SoL in four places, with no ceiling:

- a lower-strata pop with SoL above 10 adds SoL × 2;
- a middle-strata pop adds SoL × 3;
- clerks add 75 + SoL;
- every non-agricultural pop with SoL ≥ 10 adds SoL × 2 (`URBAN_POP`).

The Unions' two SoL terms run the other way: middle-strata non-agricultural
pops get 50 − (SoL + 10), and clerks get 35 − SoL. That is vanilla's model of
prosperous workers leaving the unions.

**The effect at late-game SoL:**
- A clerk (lower strata) at SoL 30 scores about 225 for the PB, 70 for the
  Intelligentsia and 55 for the Unions.
- A laborer switches from the Unions to the PB at about SoL 38.

**Why this only shows late:** the terms were tuned for 1836–1936. Mean SoL in the
saves, the USA left out:
- 1964: lower strata 9, middle 15.
- 2050: lower 30, middle 37, upper 87.
- Middle over lower falls from 1.6 times to 1.2 times. In two big countries the
  middle strata are at or below the lower.

So by 2050, SoL can't tell a shopkeeper from a laborer, but stratum can.

**Professions:**
- 2050: laborers 24% of pops, clerks 20%, engineers 16%, machinists 10%,
  shopkeepers 7%, academics 7%, farmers and peasants 4% together.
- 1964: laborers 29%, peasants 11%, farmers 10%.

## 3. Goals, non-goals, anti-goals

**Goals**
- **The PB's size in a rich late-game country.** About 10–25% of clout,
  depending on conditions, laws among them. The owner's example is the
  Ministry of Labor (**owner**).
- **Tied to expectations.** The PB's size follows how people fare against the
  mod's SoL Expectations system, not how rich the era is (**owner**).
- **A fall behind expectations polarizes.** Middle-strata pops move toward the
  PB, from status anxiety. Lower-strata pops move toward the Unions. A falling
  SoL then pulls a country apart to the right and the left, "like in Weimar
  Germany" (**owner**).
- **The early game barely moves.** The terms were tuned for 1836–1936.

**Non-goals**
- **The other six IGs' formulas**, the Industrialists' SoL terms included
  (§ 6.5).
- **The Unions' steady-state SoL terms** (§ 6.5).
- **New IGs, ideology succession, repurposing Landowners and Rural Folk** (§ 11).
- **The expectations system itself.** Its ceiling was raised from 50 to 200 in
  #2148 (issue #2147), so it now follows SoL to about 180.

**Anti-goals**
- **A cap set at late-game SoL.** It would need retuning whenever late-game SoL
  moves. The cap in § 6.1 sits at the SoL vanilla was tuned for, which doesn't
  move.
- **Deleting the PB's SoL terms outright**, as the Better Politics Mod does. The
  PB stay the middle-class party.
- **A new giant in place of the PB.** No other IG should take over the PB's role
  of 40% in country after country (§ 8 measures this per country).
- **Moving the 1836 start.**

## 4. Approaches considered

1. **A soft cap on the SoL terms, alone.** Rejected as the whole answer: it
   gives a size, but nothing that moves with how people are doing.
2. **Measure against expectations (picked, owner).** There were three ways to
   read it:
   - (a) the national expectations gap, one cached country variable;
   - (b) each pop's own radicals and loyalists;
   - (c) both: (a) for boom and bust, plus a small per-pop term from (b).

   The owner picked (c), with the per-pop term kept small: "as long as the
   per-pop radicals and loyalists term is small, I think it'd just add a
   little flavor without too much balancing needed" (**owner**).
   - (a) alone misses a region or trade in decline inside a growing country.
   - (b) alone mixes anger over laws in with the economy, and vanilla already
     multiplies an opposition IG's pull by its pops' radicals.
3. **What the gap means.** The gap also carries the welfare floor and the
   comparison with richer countries. The alternative was a new running average
   of SoL, so that only a fall polarizes. The owner kept the gap (**owner**).
   Gurr's relative-deprivation account (*Why Men Rebel*, 1970) supports this:
   radicalization follows the gap between what people expect and what they
   get, whatever its source. § 6.2 takes out one part of the gap that is
   neither of those (§ 10 Q1).
4. **The steady-state level.** The middle strata lean to the PB by a fixed
   amount, as a class, not by an amount that grows with SoL. The owner saw
   this in the brainstorm. The question was then how to fix the terms:
   - **Freeze each at its value at a reference SoL.** This was first written up
     and modelled. It *raised* the PB's pull on every pop below the reference,
     which in 1836 means most of them (farmers are middle strata).
   - **Cap each at the reference (picked).** A pop below it keeps vanilla's
     value. A pop above it holds there.
   - **Which IGs to cap:** the PB only, after the model showed that capping the
     Unions too made them the new giant in places (§ 8).

## 5. Engine and mod facts this rests on

**The attraction formula:**
- **An `INJECT` into an interest group's script-value field replaces the whole
  field** and keeps the IG's other fields. This was read in game on 2026-10-10
  for the female-chance fields and on 2026-10-25 for party `join_weight`. So
  the mod restates the whole of vanilla's `pop_weight` for each IG it changes,
  from a generator (`ig_feminism.py`; FPTP's `gen_party_join_weights.py`).
- **Scope in `pop_weight`:** root is the pop, `scope:interest_group` is the IG,
  and `owner` is the country. Vanilla's own `pop_weight` already reads these:
  - `owner = { has_law = ... }`
  - `standard_of_living`, `strata`, `pop_typically_counts_as_middle_strata`
  - `pop_employment_building_group`
  - `pop_loyalist_fraction` and `pop_radical_fraction`
- **One read has no vanilla precedent:** a variable inside `pop_weight`, whether
  `has_variable` or a value (`owner.var:X`). Vanilla's IG files test
  `has_variable` only in other fields (`priority_cultures`,
  `magnate_leader_weight`), and script values read `var:` everywhere else. So
  this is expected to work, and the attraction tooltip shows the result (§ 9).
- **`interest_group_ig_<ig>_pop_attraction_mult` exists for every vanilla IG**
  (`docs/engine/modifier_patterns.md`) and multiplies its attraction. Laws
  already carry it: Freedom of Contract gives the Unions +20%.

**Strata:**
- **The default hierarchy** (`00_default.txt`):
  - middle strata: academics, bureaucrats, clergymen, engineers, farmers,
    officers, shopkeepers;
  - lower strata: clerks, laborers, machinists, peasants, slaves, soldiers, and
    the mod's Spacers (`te_spacers_classes.txt`).
- **The caste and Edo hierarchies differ.** Vanilla's PB terms test
  `strata = lower` first, then `pop_typically_counts_as_middle_strata`, which
  is a fixed list of pop types.
- **The PB's `pop_potential` already bars aristocrats and capitalists**, so
  upper-strata pops reach the PB only under the caste and Edo hierarchies.

**The two expectations variables:**
- **`sol_expectations_gap_cached`:**
  - It's a country variable that `sol_expectations_monthly_update` writes every
    month from `on_monthly_pulse_country`.
  - It equals average SoL + target add − average expected SoL.
  - The system is always on, with no game rule. A new or released country lacks
    the variable until its first month, so a missing variable reads as 0.
  - A revolution's winner inherits variables.
- **`sol_expectations_shift`:**
  - It's the adaptive shift. The same update stores it already clamped to
    [floor, 200] (`sol_expectations_effects.txt`: `set_variable` from
    `sol_expectations_shift_clamped_value`).
  - The floor is 0 plus `country_sol_expectations_shift_min_add`, which the
    welfare laws raise: Poor Laws +1, Wage Subsidies +2, Old Age Pension +3,
    Universal Basic Income +10, Post-Scarcity +15.

**The floor regime:**
- **How it arises.** The target add starts at −10 (`base_values`,
  `extra_modifiers.txt`). Below an average SoL of about 17–23, the shift sits at
  its floor, and the gap is negative even though pops are 0–9 points *above*
  their expected SoL.
- **In the saves:**

  | Save | Countries at the floor | Mean gap at the floor | Mean gap above it |
  |---|---|---|---|
  | 1964 | 34 of 35 | −5.8 | −1.4 (one country) |
  | 2032 | 8 of 24 | −5.0 | +3.2 |
  | 2050 | 1 of 20 | −8.8 | +7.4 |

- **It is neither of the two things the owner kept the gap for** (§ 4.3). It is
  the default floor holding expectations at the base game's while the mod's
  own target sits lower.

## 6. Design

The changes are to the PB's and the Unions' `pop_weight`, plus modifiers on
three laws. `REF_LOWER` = 10 and `REF_MIDDLE` = 20 are the reference SoL values.
The 1964 save's means were 9 and 15, and vanilla's own era sits at or below
them.

### 6.1 Cap the PB's SoL-scaled terms at the SoL vanilla was tuned for

Each term reads `min(SoL, REF)` in place of SoL. Below the reference a pop is
exactly as in vanilla; above it the term holds at the reference.

| Term (desc) | Vanilla | Capped |
|---|---|---|
| `POP_BASE_ATTRACTION`, lower strata, SoL > 10 | SoL × 2 | 2 × min(SoL, 10), so 20 |
| `POP_BASE_ATTRACTION`, middle strata | SoL × 3 | 3 × min(SoL, 20) |
| `POP_CLERKS` | 75 + SoL | 75 + min(SoL, 10) |
| `URBAN_POP` (non-agricultural, SoL ≥ 10) | SoL × 2 | 2 × min(SoL, the pop's reference) |

- **The pop's reference is REF_LOWER for lower-strata pops and REF_MIDDLE for
  the rest.** Upper-strata pops reach the PB only under the caste and Edo
  hierarchies (§ 5), and they take REF_MIDDLE.
- **Each term keeps its desc key and its strata test** (the same `if`/`else_if`
  as vanilla). Each line still means what it meant.
- **Vanilla's SoL gates stay:** SoL > 10 for the lower-strata base and SoL ≥ 10
  for the urban term.
- **Everything else in the PB's formula is unchanged:** shopkeepers 150,
  engineers 50, Elected Bureaucrats 50, Homesteading farmers 25, the managerial
  halving, the India branches, and every multiplier.

### 6.2 Boom and bust, from the national gap

**Reading the gap.** Let `gap` be the pop's country's
`sol_expectations_gap_cached` (`owner.var:` from the pop; 0 when missing) and
`shift` be its `sol_expectations_shift`. The terms read

> g = max(gap, −shift)

So a fall can't run deeper than the expectations the mod built up:

- **The default floor (shift 0):** no bust at all. This is the floor regime of
  § 5, where pops sit above their expected SoL.
- **A welfare floor F:** a bust down to −F. The welfare floor stops
  expectations from adapting down to hardship, which is one of the grievances
  the owner kept.
- **The adaptive regime** (shifts of 1–24 in the 2050 save): the gap as it is,
  down to the cap of 15 below, as long as the gap is no deeper than the shift.

**The cost.** A country whose expectations sit only a little above the base
game's polarizes little in a downturn. The EU's shift in 2050 is 2.9, so its
bust could reach only −2.9. Vanilla's own radicals and the per-pop term
(§ 6.3) still respond.

This is the designer's correction of the owner's call (§ 10 Q1). It needs no
new variable.

**The terms:**
- **g < 0, falling behind.**
  - Middle-strata pops add `A × min(−g, 15)` to the PB.
  - Lower-strata pops that the Unions' `pop_potential` admits add
    `B × min(−g, 15)` to the Unions.
  - First guesses: A = B = 10.
- **g > 0, ahead.** Non-agricultural pops add `C × min(g, 10)` to the PB. First
  guess: C = 2. The middle and the aspiring do well in good times, and the
  lift fades as expectations catch up (10-year half-life).
- **The new terms test the pop's own `strata`**, so they follow each country's
  hierarchy. Under the Strict Edo System, Japan's townspeople (shopkeepers,
  clerks, engineers) are lower strata, so a bust sends them to the Unions. The
  country holds that law until it reforms it.

**Why national:** one cached read per pop is cheap, and Weimar's crisis was
national. The per-pop term (§ 6.3) covers regional decline.

**Ties to other systems:**
- A Banking cycle panic lowers SoL, so the gap falls and the country polarizes,
  with no wiring of its own.
- Algorithmic Governance's mandate reads the same gap.

### 6.3 The per-pop term, kept small (owner)

| Pops | Multiplier |
|---|---|
| Middle strata | PB weight × (1 + 0.25 × `pop_radical_fraction`) |
| Lower strata | Unions weight × (1 + 0.25 × `pop_radical_fraction`) |
| Lower strata | PB weight × (1 + 0.25 × `pop_loyalist_fraction`) |

- **The size matches vanilla's own loyalist and radical multipliers**, which
  reach × 1.25 at most.
- **It catches what the national gap misses:** a trade or region in decline,
  and a few affluent, content workers drifting to the PB.
- **The overlap with vanilla's opposition-radicals multiplier is accepted** at
  this size. Radicals that come from anger over a law also count, and a
  backlash in the middle strata leaning PB is the same politics.
- **The model ran the two radical lines but not the loyalist line** (§ 8).

### 6.4 Laws

These are ordinary modifiers on the laws
(`interest_group_ig_<ig>_pop_attraction_mult`), not branches in `pop_weight`, so
each shows in the law's tooltip where the player chooses it:

| Law | Effect |
|---|---|
| `law_pro_labor_ministry_of_labor` | PB −15%, Unions +15% |
| `law_pro_capital_ministry_of_labor` | PB +10%, Industrialists +10% |
| `law_trust_busting` | PB +15%: small business against the trusts |

- **Freedom of Contract and Guilds and Chartered Monopolies are left alone.**
  Every country starts with one of them (`extra_history.txt`), so a term on
  either would move 1836. Freedom of Contract keeps its existing Unions +20%.
- **Vanilla's Elected Bureaucrats and Homesteading terms stay** in `pop_weight`.
- **The owner's example was the Ministry of Labor** (**owner**). Which other
  laws to use is § 10 Q2.

### 6.5 What stays as it is

- **The Unions' steady-state SoL terms.**
  - Vanilla's two falling terms are kept: middle-strata non-agricultural pops at
    50 − (SoL + 10), clerks at 35 − SoL. That is vanilla's account of
    prosperous workers leaving the unions, not the PB's bug.
  - With them capped as well, the model had the Unions take over: one country
    went from 17% to 48% and another from 44% to 61%, against the anti-goal
    (§ 8).
  - The Unions' formula is still restated, for the bust and per-pop terms of
    §§ 6.2–6.3.
- **The other six IGs' `pop_weight`.**
  - The Industrialists' SoL terms are the same kind (capitalists 250 + SoL,
    engineers 50 + 2 × SoL, shopkeepers 25 + 2.5 × SoL). But the Industrialists
    halved rather than swelled (17% → 9%), and they gain in the model.
  - Revisit if the play-test shows them swelling.
- **The mod's flat attraction modifiers** (Devout revival, the bloc principles,
  barracks), which multiply on top.
- **The expectations system.** The correction in § 6.2 reads its two variables
  and writes nothing.

### 6.6 Tooltip lines

Each new term gets a `desc` with a loc key, shown in the IG's attraction
breakdown. The labels are short, like vanilla's ("Non-Agricultural
Employment"); the wording follows the `event-text` skill. Then run
`organize_loc.py`.

| Line | Proposed label |
|---|---|
| Bust, PB | "Falling Behind Expectations" |
| Bust, Unions | "Falling Behind Expectations" |
| Boom | "Ahead of Expectations" |
| Middle-strata radicals | "Radicalized Middle Class" |
| Lower-strata radicals | "Radicalized Workers" |
| Lower-strata loyalists | "Content Workers" |

## 7. Tooling

- **A generator restates vanilla's PB and Unions `pop_weight` from the game
  files.** It follows `ig_feminism.py`'s approach: copy each vanilla line,
  then change or add.
  - For the PB it applies §§ 6.1–6.3. For the Unions it applies §§ 6.2–6.3 only.
  - It needs `--check`, which exits 1 when the committed file is stale and
    needs the game.
  - Register it among the post-load regenerators and on the vanilla patch
    runbook's regenerate list.
- **Where to write the `pop_weight` INJECTs is the builder's call.**
  `zz_te_ig_female_chance.txt` already holds an `INJECT:ig_petty_bourgeoisie`
  and an `INJECT:ig_trade_unions` for the female-chance fields. Either add the
  `pop_weight` field to those same blocks (one generated file, two generators'
  worth of fields), or check that two INJECT blocks for one IG from two files
  both apply, and record the result in `scripting_best_practices.md`.
- **Tests**, in the style of `test_ig_feminism.py` and
  `test_first_past_the_post.py`:
  - every SoL read in the PB's restated `pop_weight` sits inside a `min` with
    its reference, apart from vanilla's level gates;
  - the Unions' SoL terms equal vanilla's;
  - the gap and shift reads guarded for a missing variable
    (`variable_guard_audit` rules);
  - every new desc key has loc;
  - the constants (REF_LOWER, REF_MIDDLE, A, B, C, the caps, 0.25) match this
    doc;
  - the three laws carry their modifiers;
  - the committed file matches a fresh generation.
- **The offline model** is archived, not in the repo, at
  `/mnt/d/vic3te-data/ig_attraction_model_2026-11-28/model/`.
  - **Files.** It holds the scripts, the pickled extracts of the 1964, 2032,
    2043 and 2050 saves, and the tables:
    - `model_cap.py` is this design, with the `CAP` and `TU_VANILLA` flags.
    - The `*_corr.pkl` extracts carry the corrected gap of § 6.2.
    - `out*_b.md` are this design's results. `pc_tuv*.txt` are the same
      country by country.
  - **Running it.** Run it from that folder with
    `python3 evaluate_b.py s2050_corr.pkl` or the `pc_tuv_*.py` scripts, which
    import the model from beside them.
  - **After building.** Port the built formulas into its `rework` and rerun
    before tuning.

## 8. Calibration (the offline model)

**The model:**
- It ports vanilla's eight `pop_weight` formulas to Python and splits each pop's
  *stored* political strength across IGs in proportion to their weights.
- Per-country multipliers make the vanilla port reproduce the engine's own
  membership split of each pop, which the save stores.
- Its error is 2.6 clout points per IG against the engine's memberships (the
  PB worst, at 7), and 4.5 against observed clout.
- Its projections are where things settle; memberships in game change slowly.
- No 1836 save was read.

**This design, 2050, the 20 countries, at g = 0:**

| | Value |
|---|---|
| PB mean | 21.2% (observed 32.2) |
| PB range | 2.9–40.5% |
| Inside 10–25% | 11 of 20 |
| Unions mean | 15.0% (observed 12.1) |
| Countries with any IG over 40% | 9 (observed 11) |
| Countries where the Unions are the largest IG | 3 (observed 1) |

**Where the PB's loss goes:** Intelligentsia +2.9, Unions +2.9, Devout +2.7,
Industrialists +1.4, Armed Forces +1.0.

**Outside the band:**
- **Above 25%:** France 36%, the EU 35%, BHA 29%, AFG 28%, and Japan 41%. Japan's
  figures are unreliable because the model doesn't follow its Edo hierarchy.
  The laws of § 6.4 are the lever for these.
- **Below 10%:** union- or army-run countries (one is 80% Armed Forces). That is
  "depending on conditions".

**The variants modelled, 2050 at g = 0:**

| Variant | PB mean (range) | Unions | Largest Union rise | Any IG over 40% |
|---|---|---|---|---|
| Freeze PB and Unions at 10/20 (first draft) | 18 (2–34) | 20 | 17 → 48% | 9 |
| Cap PB and Unions at 10/20 | 19 (2–34) | 20 | 17 → 48%, 44 → 61% | 8 |
| **Cap PB only at 10/20 (this design)** | **21 (3–40)** | **15** | 15 → 23%, 44 → 51% | 9 |
| Cap PB, Unions' clerk term capped too | 21 (3–40) | 16 | 15 → 26%, 44 → 55% | 9 |
| Cap PB only at 10/15 | 20 (3–37) | 15 | | |
| Cap PB only at 15/20 | 23 (3–41) | 14 | | |

**Boom and bust (this design, A = B = 10, C = 2):**

| g | +15 | +5 | 0 | −5 | −10 | −15 |
|---|---|---|---|---|---|---|
| PB, mean (range) | 24 (3–43) | 22 (3–42) | 21 (3–41) | 23 (3–45) | 25 (3–49) | 26 (3–52) |
| Unions | 14 | 15 | 15 | 18 | 20 | 21 |

- A = B = 20 gives the PB 29% and the Unions 23% at −15.
- A = 20 with B = 5 gives the PB 31%. A = 5 with B = 20 gives the Unions 24%.
- A = B = 10 is the first guess: both sides grow, and neither runs away.

**1964 check (35 countries, observed PB 18.4%):**
- At g = 0, the PB change by −1.9 points and the Unions by +0.7.
- At each country's own corrected gap, the PB change by −1.7 and the Unions by
  +0.9.
- **With the raw gap the bust is larger.**
  - The bust alone adds PB +1.1 and Unions +1.3 on average, up to PB +4.4 and
    Unions +3.5 (Poland, Romania, RSM, Japan).
  - The Unions' total change passes 2 points in 14 of 35 countries, against 4
    with the corrected gap, where the bust adds +0.2 to each.
  - 1836's gaps run deeper than 1964's (−8 to −11 by the formula), so the raw
    gap's effect there would be larger.
- **In 2050 the raw and corrected gaps give nearly the same result.** The bust
  adds PB +1.6 with the raw gap and +1.5 with the corrected one, because only
  AFG sits at the floor.
- **Country by country, 11 of 35 move the PB by more than 2 points.** All are
  ones whose SoL already passes the reference in 1964: Britain 54 → 47%, France
  43 → 37%, EGY 35 → 30%, UNL 44 → 39%, Romania 26 → 22%. That is the late-game
  change arriving where the SoL is already late-game.
- **The 1836 start:** pops below the reference keep vanilla's values, and the
  corrected gap gives no bust at the default floor. So only the per-pop term
  and a rare positive gap can move the start. Play-test item 3 checks it.

**Limits:**
- The model holds the IG-level strength multipliers fixed.
- It doesn't model acceptance or culture gates, or Japan's strata.
- It doesn't apply the Industrialists' +10% under the pro-capital ministry, or
  the loyalist line of § 6.3.

## 9. Self-check and play-test

**No self-check.** The one unverified fact, a variable read inside `pop_weight`,
shows directly in the attraction tooltip. Script can't read a pop's attraction
result to test it any other way. So it goes on the play-test list.

**Play-test list,** a new `docs/testing/ig-attraction-playtest.md`:

1. A middle-strata pop in a country with a falling SoL (a shift above 0 and a
   negative gap): the PB tooltip shows the bust line at A × min(−g, 15). A
   lower-strata worker shows the Unions' line. A country at the default floor
   shows none. A country released this month shows no line and no error.
2. A clerk at SoL 30: the PB's Clerks line reads 85 and its urban line 20. The
   Unions' lines are vanilla's.
3. **The 1836 start.** PB, Rural Folk and Unions clout in the first year,
   against a start with vanilla's formulas. If any moves by more than about 2
   points, raise § 10 Q1 again with the figures. An 1836 save for the model
   would settle this before the build, but making one needs a game launch, and
   a launch needs the owner's go-ahead.
4. A late save: the PB in rich AI countries mostly inside 10–25%. No IG takes
   the PB's place at 40% in country after country.
5. A Banking panic: over the following year the PB and the Unions both gain, and
   both fade as expectations catch up.

**Player guide:** the build's PR adds a short paragraph where the guide covers
adaptive expectations (`03-economy.md`), saying that falling behind
expectations moves the middle class toward the Petty Bourgeoisie and workers
toward the Trade Unions. It also adds the three laws' new effects wherever the
guide states those laws' effects. This doc's own PR changes nothing a player
sees.

## 10. Open questions for the owner

These calls were made while the owner was away. Each one is in the design
above as written. The way back from each is given, and none changes the
build's shape.

1. **The floor correction (§ 6.2).**
   - **What the owner was told:** the gap also carries the welfare floor and
     the comparison with richer countries. The owner kept it on that basis.
   - **The larger cause:** the default floor. Below an average SoL of about
     17–23, the gap is negative while pops sit above their expected SoL.
   - **Provisional:** read `max(gap, −shift)`. That keeps the welfare floor's
     part and the adaptive regime, and removes the default floor's part.
     - With the raw gap, the 1964 bust adds about a point each to the PB and the
       Unions, and up to 4 in some countries. 1836's deeper gaps would add more.
     - With the correction, the bust adds 0.2 each.
     - The cost is in § 6.2: a country only just above the floor polarizes
       little in a downturn.
   - **Alternative:** correct only while the shift sits at its floor (there,
     `max(gap, −F)`, with F the welfare floor; above the floor, the raw gap).
     That gives a recently adapted country its full bust. But the bust drops
     suddenly when a long slump brings the shift down to its floor.
   - **The way back:** drop the `max` and read the raw gap.
2. **The laws (§ 6.4).**
   - **Provisional:** modifiers on the Ministry of Labor's two laws and on
     Trust Busting, and none on the two starting antitrust laws.
   - **Open:** other candidates.
3. **The cap, and the Unions' steady state (§§ 6.1, 6.5).**
   - **Provisional:** cap the PB's terms at the reference instead of freezing
     them, so the start keeps vanilla's values. Leave the Unions' falling terms
     as vanilla's, so the Unions don't become the new giant. The PB then land at
     21% at g = 0, against 18% in the first draft.
   - **The way back:** freeze (§ 4.4), or cap the Unions too. § 8's variant
     table has both.
4. **The Edo hierarchy (§ 6.2).**
   - **Provisional:** the new terms read the pop's own `strata`, so Japan's
     townspeople count as lower while the Strict Edo System holds.
   - **The alternative:** test `pop_typically_counts_as_middle_strata` (a fixed
     list of pop types), which treats them as middle in every country.

## 11. Later, not in scope

- **Ideology succession.** When an IG's founding demands have been law for a
  generation, it trades that ideology for the next fight. The owner liked this
  (**owner**).
  - Leftover ideologies like Anti-Colonialist in 2050 are benign: they act as
    memory, so the IG resists bringing the old policy back (**owner**). Retire
    an old ideology only where its stances would misfire.
  - The Better Politics Mod's one-ideology-per-topic slots are a model for
    swapping one topic at a time.
- **Landowners and Rural Folk near zero after 2030.** Repurpose them where their
  base is gone: finance and property owners, and pensioners in ageing
  countries.
- **A ninth IG,** following the Better Politics Mod (Workshop 2932134122):
  - Every IG exists from 1836 and stays dormant, with `pop_potential` admitting
    no pops until script activates it.
  - It reuses a vanilla revolution map `layer`.
  - It needs an icon and its `_30` variant, loc including `ig_X_only_icon`, and
    a texticon.
  - This was read from that mod's files, not tested here.
- **Other attraction work:**
  - The Devout's attraction from existential security in place of literacy.
  - An Armed Forces military-industrial term (Armed Forces: boost, don't cut).
  - A political home for Spacers, whom no formula names.
  - The Intelligentsia's literacy term, which is worth +20 at most and is a low
    priority.
- **Long term (owner):** polarization, performance legitimacy and dealignment.
  The Actors work (organized labor, religious organizations, industry
  associations; `2026-11-28-actors-firms-design.md`) is in progress in another
  session.
