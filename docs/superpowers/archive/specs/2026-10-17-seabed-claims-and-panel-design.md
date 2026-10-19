# Seabed claims, leases and the Seabed panel — design

Drafted 2026-10-17 from a brainstorm with the owner, after a play session in which the Seabed tab
was hard to read. It builds on the Global Commons design
(`docs/superpowers/archive/specs/2026-10-16-global-commons-design.md`, §§ 2–3, shipped in #1002), which
it assumes. Read that document's § 2.4 (licences, records, the water-filling) and the Python
model `scripts/analysis/seabed_model.py` before planning: every rule change below goes into the
model first.

## Intent

The owner opened the Seabed tab mid-game and couldn't tell what it said:

- Button labels overflow their buttons ("Sponsor Contractors", "Unilateral Licensing").
- The words come from the design's internals. "The world: 0 recorded of 300" means "licences in
  use by mines anywhere, as of last January, against the pool". "Recorded" is the model's term for
  a licence attached to a state, and it should never have reached a player.
- The **World** column is a January snapshot, while **Licences** is updated monthly, so the Pacific
  read "0 / 300" while our share there was 85.
- **Weight** is a raw score (6,878.5 in the Atlantic, 13.0 in the Indian) with nothing to compare
  it against.

Underneath, the owner found two design problems:

1. **"Licence" sounds like ownership.** A player reads "Licences 304 / 429" as 429 slots they own.
   In fact the 125 unused ones are re-divided every January, and a rival's naval buildup can take
   them. Nothing tells the player to hurry.
2. **Queueing a mine already locks its licence in, for free and forever.** A queued level is
   recorded at the next monthly pass (`te_seabed_state_levels` counts
   `level_after_queued_constructions`), and the sharing never takes a recorded licence back. Vic3
   only charges for construction as it is worked on, so a player can queue the whole share and
   keep it out of rivals' hands at no cost. The panel says neither.

The owner also wants the system to be more engaging. They want three things from it: a **land rush** for a
new resource and the competition it brings; **more uses for navies**, including hurting a rival's
mines; and **geographic strategy**, such as taking land in the Pacific to stake a claim there.

## The four questions the panel answers (owner, 2026-10-17)

In this order:

1. **How many more Deep-Sea Mines can I build?**
2. **Where can I build them without the −25% long-haul penalty?**
3. **What is left to fight over, and what would a naval buildup win me?** Phrased as "you need X
   more navy to get one more licence".
4. **Who else is in each basin?** Their mines (locked in) and their unused claims (which a
   buildup could take).

## Decisions (owner, 2026-10-17)

- **Two words.** A **licence** is held by a mine level, built or queued, and is permanent. A
  **claim** is a country's unused share, re-divided every January (§ 1).
- **Licences on queued levels cost a weekly holding fee** (the brainstorm's option A, § 2.1).
  Queueing still locks a licence. Hoarding stays possible, at a price.
- **Sponsor Contractors protects claims.** On that policy a country's unused claims can shrink by
  at most a quarter each January (§ 2.2). Its influence cost goes up: "50 influence is pretty much
  a token cost" (§ 2.3).
- **A five-year lock on changing seabed policy**, with a carve-out: a country may switch to
  Unilateral Licensing at once if a rival in one of its basins has switched to it (§ 2.4). This
  replaces a "held since last January" rule that was more fiddly to explain.
- **Layout A for the panel**, chosen from three mockups: an overview of boxes, the policy buttons,
  then one table of all five basins in which each basin opens to show its rivals (§ 3).
- **"Lease Seabed Claims" treaty articles**, with a money transfer the usual price. They are
  **enforceable**, so a war's winner can impose one; that is the "Seize Seabed Claims" war goal
  for free, and the separate war goal of the earlier design's § 10 is dropped (§ 4).
- **Unincorporated coastal states count toward claim weight**, at a fraction (§ 5.1).
- **Subjects' claims can count toward their overlord**, through an optional overlord action like
  Raise Payments (§ 5.2).
- **Blockades cut Deep-Sea Mine output**, through vanilla's blockade throughput rule (§ 6.2). The
  owner pointed out that fishing, whaling and ports already lose throughput to blockades.
- **The rush is announced**: the first country with the technology, a new rival in your basin, a
  basin fully licensed (§ 7).
- **Deferred to v2:** Seabed Sabotage, a covert operation that disables a rival's mines in one
  state for some months (§ 11).

Second round (owner, 2026-10-17, on the reviewer's questions):

- **A year's grace before the fee.** The fee starts only on a licence whose level has stayed
  unbuilt through a full year, so honest building, private investors' included, never pays it
  (§ 2.1).
- **Sponsor's cost scales with claims, uncapped**: "claiming the whole basin should be expensive".
  A country may drop to Scientific Survey at any time while its influence is in deficit (§§ 2.3,
  2.4).
- **A way to give claims up**: "maybe we add a revoke claims option?" (§ 2.5).
- **Protection may take from the reserved half** when the Law of the Sea comes into force, as the
  real convention's pioneer investors kept their registered sites (§ 2.2).
- **Naval power projection, not navy size**, counts toward claim weight, if script can read it as
  a number (§ 6.1).
- **Pooling a subject's claims is an automatic lease** to the overlord, and only ever the
  overlord's choice: "as long as you don't have to take your subject's claims" (§ 5.2).
- **A defection lasts 5 years in all**: the Law of the Sea's rejoin clock starts at the defection
  (§ 2.4).

## Goals

- Each of the four questions is answered in the panel without a hover; the hover gives the
  breakdown.
- A player understands, from the panel alone, that unused claims can be lost and when.
- Locking in a licence before building it costs something every week.
- Seabed shares can be bought, sold and won in war.
- Coastline anywhere, a subject's coastline and a navy at sea all matter to seabed shares.
- AI and players run under the same rules, with no `is_ai` branches in the mechanics.

## Non-goals

- Changing the pools, the basins, the long-haul penalty or the Law of the Sea regimes.
- Per-basin yields, pools that grow with technology (still the earlier design's § 10).
- Moving a built mine's licence by treaty. Built licences change hands only with their state.
- Seabed Sabotage (v2).

## Anti-goals (would make this a failure even if it technically works)

- **Anything a player reads ends in "…" or overflows its box.** This is how the review started.
- **A number is stale without saying so.** Figures fixed at a sharing carry "as of <month
  year>".
- **A queued or built mine loses its licence.** The fee and the protection must never strip one.
- **Switching policy pays.** Nobody gains by flipping to Sponsor Contractors just before January,
  or by flipping away to stop paying.
- **Early movers lock a basin forever without paying for it.** Protection fades by a quarter a
  year; only the fee keeps a licence held on an unbuilt level.
- **The panel asks for five decisions a year** (inherited). Policy is still one national choice.

## Engine facts this rests on

- **A queued level is recorded at once** (`level_after_queued_constructions`). The earlier design's
  header in `te_global_commons_seabed_effects.txt` says why: it stops a sharing from stranding a
  level under construction without a licence. This design keeps it and prices it.
- **Script cannot cancel a queued construction.** No effect in `docs/engine/effects_summary.txt`
  does. So no rule here may leave a queued level needing a licence it can't get.
- **Blockades.** `00_defines.txt`: `BLOCKADE_THROUGHPUT_IMPACT_SCALING = 0.75`, "reduction of
  throughput for buildings affected by blockades, scales against blockade level". The define's
  neighbour names "buildings affected by blockades (such as fisheries and shipyards)", and
  `concept_blockade_resistance_desc` speaks of "coastal building output". The only field the
  blockade-affected vanilla buildings share is **`city_type = port`** (fishing wharf, whaling
  station, shipyard, port, the naval buildings), across four different building groups. The
  Deep-Sea Mine is `city_type = city` (`common/buildings/extra_buildings.txt`,
  `REPLACE_OR_CREATE:building_ocean_mine`). Nothing documents that `city_type` is the switch.
  One side effect, if it is: `BLOCKADE_TARGET_STRENGTH_PER_PRODUCED_UNIT = 0.075` makes a state's
  blockade-affected output raise the strength needed to blockade it, so a big seabed state is
  harder to blockade.
- **Treaty article inputs.** `required_inputs` takes `state`, `country`, `company`, `goods`,
  `law_type`, `building_type`, `strategic_region`, `text`, `ship` and `quantity`. Vanilla combines
  two (Goods Transfer: `quantity` and `goods`). The mod's `117_nuclear_arms_limitation.txt` takes a
  `quantity` alone, with `quantity_min_value`, `quantity_max_value` and `quantity_input_value`, and
  reads `scope:article.input_quantity`. The flag **`can_be_enforced`** lets a war's winner impose
  an article (Money Transfer has it); 19 mod articles use it.
- **Raise Payments** (`vanilla_parsed/common/diplomatic_actions.json`, `raise_payments`) is an
  overlord action with `requires_approval = no` and a pact. Its `potential` excludes protectorates
  and personal unions. Its `selectable` requires the DLC feature `subject_and_bloc_actions`; the
  seabed action must not.
- **A country can't be read straight out of a GUI list** (`docs/guides/gui_modding_guide.md`,
  gotcha #15). A datamodel of countries and `Scope.GetCountry` are unproven in `.gui`. Two routes
  work: a scripted GUI's `ExecuteTooltip` in fixed rows whose effect enters
  `global_var:<rank>` and prints `[THIS.GetCountry.GetName]` (the Cultural Hegemony leaderboard,
  `ch_board_row_sgui`), and a country variable holding a state, read as
  `….Var('x').GetState.GetCountry` for a `flag` widget (the Cultural Hegemony leader flags,
  `ch_leader_seat_N`).
- **The policy's influence** is a static modifier, `te_seabed_policy_sponsor_cost` /
  `_unilateral_cost`, rebuilt from the policy variable by `te_seabed_refresh_policy_cost`. A
  scaled cost becomes `add_modifier = { name = … multiplier = … }` from the same monthly country
  pulse, its one refresh site.
- **Both halves of a regulated pool are water-filled together** (`seabed_model.py`'s header). A
  country's tentative entitlement is its reserved-half share, if eligible, plus its open-half
  share, and it is frozen when its holdings reach that sum. So a floor on the basin total slots in
  without tracking halves.

## 1. Words: licence and claim

| Term | Means | Lasts |
|---|---|---|
| **Licence** | What a Deep-Sea Mine level holds, built or queued. Recorded on its state; passes with the state. | Permanent. Comes back to its owner's claims when the level is downsized or destroyed. |
| **Claim** | A country's unused share of a basin: entitled to, not yet attached to any level. | Until the next January sharing, which re-divides it (protected on Sponsor Contractors, § 2.2). |
| **Share** | Licences plus claims in a basin: what the January sharing gave the country. | The year. |

- "Recorded" leaves every player-facing string: the panel, `TE_STATE_SEABED_TT` (the state tile),
  the gate tooltips, `te_seabed_how_*`, `je_un_terms_law_of_sea_seabed` and the notifications.
  Variable and effect names keep "records"; they are the model's.
- A new concept, `concept_seabed_claim`, beside `concept_seabed_licence`. Rewrite
  `concept_seabed_licence_desc` to say a licence is held by a level and that unused shares are
  claims. Note: `organize_loc.py` files concept keys by token count (CLAUDE.md, Editing
  conventions), so run it and commit what it moves.
- "Room to build" stays: it is the sum of claims, less levels queued past them.

## 2. Claim rules

### 2.1 Holding fee on licences of unbuilt levels

- **Base**: per state, the licences held by levels that have stayed unbuilt through a full year.
  Each January the state stores its unbuilt licences (records minus its Deep-Sea Mine's built
  `level`), keeping the last two snapshots. The base is the smallest of the unbuilt licences now
  and the two snapshots, so a level pays only once it was already unbuilt at the January before
  last: a grace of 12 to 24 months (owner). Summed over the owner's coastal states. The snapshots
  are state variables, so they pass with the state.
- **Who queued it doesn't matter.** Private investors queue Deep-Sea Mines too, and the player may
  not be able to cancel those. The grace keeps their building, and any honest building, from
  paying; a level that waits a year in the queue pays whoever queued it.
- **Rate** (my call, first estimate): **half the royalty**, 2% of a level's base output value a
  week, about @money!900 a level at the base method (the royalty is 4%, about 1,800,
  `te_seabed_royalty_per_level`). A year of holding 100 unbuilt licences then costs about 4.7
  million. Tune in play-test.
- **Billing**: a country modifier with a multiplier, refreshed monthly from the country pulse (its
  one refresh site), exactly as `te_seabed_royalty_modifier` is billed. The cached figure is a
  variable, so a revolution's winner keeps paying from its next pulse.
- **Where the money goes**: under the Regulated regime, to the same place as royalties (the World
  Development Fund while it stands, else the UN budget); under Open or Scramble it is simply an
  expense (my call). Royalties apply to built levels only, so a level pays the fee while queued and
  royalties once built, never both.
- **Display**: the overview's licences box shows the fee in red beside the queued count (§ 3.1),
  and its hover how many queued licences pay and how many are still in their grace. The gate
  tooltip says a licence costs the fee if its level is still unbuilt after its grace.

### 2.2 Sponsor Contractors protects claims

At the January sharing, a country on Sponsor Contractors has a **floor** in each basin:

```
floor = held + floor_down(0.75 × claims)
```

`held` is the licences in its states from that basin (as now) and `claims` its unused share there
going into the sharing (`te_seabed_unbuilt_<basin>`). The water-filling freezes a country at
`max(held, floor)` instead of `held`. Its stored claims after the sharing are `share − held`. So
on Sponsor a claim fades by at most a quarter a year: 100 → 75 → 56 → 42.

- **The floor is fixed in January.** The script also shares mid-year, the month after a new
  claimant appears or a recorded country wins a civil war (`te_seabed_reshare`,
  `te_seabed_pass_due`). The January sharing stores each basin's floor on the country, and a
  mid-year sharing honours the stored floor without recomputing it, so protection never compounds
  within a year (my call). A country that moves onto Sponsor mid-year gets its floor from the next
  January. *Amended after the phase 1 review (2026-10-17, builder's call):* the sharing freezes a
  country at `max(held, min(floor, held + P))`, with `P` January's protected claims stored beside
  the floor, so building on claims mid-year keeps the floor but a licence lost mid-year (conquest,
  demolition) doesn't come back as a protected claim.

- **Floors never exceed a pool.** Last year's shares summed to the pool, and a floor is at most
  last year's share, so floors only overflow where something else did: grandfathered over-pool
  holdings, or a rule that zeroes a share. If the floors' protected parts (`floor − held`) don't
  fit in what remains after holdings, scale them all down by the same factor, rounding down.
  Holdings are never touched.
- **The Antarctic Treaty overrides it.** A party's Southern share is 0; its Southern floor is its
  holdings only.
- **A Scramble voids it** (my call): while the regime is Scramble, nobody has a floor. "Nobody's
  contracts are honoured" is what a scramble means.
- **Protection may take from the reserved half** (owner). When the Law of the Sea comes into
  force after Open years, rich countries' floors can exceed the open half; the deficit then comes
  out of the reserved half, as the water-filling already moves a half's deficit to the other. The
  real convention did the same: its pioneer investors (France, Japan, India, the USSR) kept the
  sites they registered before it came into force. Floors fade by a quarter a year, so the
  reserved half refills within a few years, and the model needs no floors by half. The player
  guide says so.
- **A subject's claims leased to its overlord** (§ 5.2) follow the lease rule below.
- **Leased claims** (§ 4) are kept apart from own claims: the lease tops them up, so no floor
  protects them, and the lessor's floor counts only the claims it has not leased out.
- **Display**: the overview's claims box shows "January: lose at most N" on Sponsor and "January:
  all re-divided" otherwise; each basin row's hover gives that basin's figure.

### 2.3 Sponsor Contractors' cost

The owner: 50 influence "is pretty much a token cost", and the cost is **uncapped**: "claiming
the whole basin should be expensive". Rates are my call, first estimates to tune:

- **Sponsor Contractors**: 50 + 0.5 influence per claim it protects (its unused claims across all
  basins, refreshed monthly). The owner's screenshot (125 claims) would pay about 112; a first
  claimant handed the whole Pacific (300) about 200.
- **Unilateral Licensing**: stays above Sponsor for the same claims: 1.5 × Sponsor's figure, and
  at least 150.
- **Two ways out of a cost a country can't carry**: give up a basin's claims (§ 2.5), which cuts
  the cost from the next monthly refresh, or drop to Scientific Survey while influence is in
  deficit (§ 2.4).
- **No save covers eras 10–12 yet**: the observer runs stop near 2015, with the AI at eras 7–8.
  Ship the first estimates and tune them in the play-test, from the owner's late-game saves where
  there are any (my call). The tuning aim: a great power's full protection costs a noticeable but
  affordable slice of its influence.
- The cost tooltip (the policy buttons and `te_seabed_policy_effect_2_tt` / `_3_tt`) states the
  formula and today's figure.

### 2.4 Five-year policy lock

- **Any change of seabed policy, in any direction, locks the policy for 5 years.** A variable on
  the country holds the date of the last change, so a revolution's winner inherits the lock.
  Dropping to Scientific Survey is locked too; otherwise a player could pay for Sponsor only
  around January.
- **Carve-outs**:
  - a country may switch to Unilateral Licensing at once if, since its own last change, a country
    it shares a home basin with switched to Unilateral Licensing. Reuse
    `te_seabed_shares_home_basin_with_uni` for "shares a home basin"; the rival's switch date comes
    from the same variable;
  - a country may drop to Scientific Survey at any time while its influence is in deficit (owner).
    Nothing is gained by it: the country loses its protection and its weight falls to a quarter.
- **The first choice is free.** A country that has never changed policy (no variable) is unlocked.
  Old saves start unlocked.
- **Interaction with the Law of the Sea** (owner): a defecting party is a party again **5 years
  after it defected**, once it has left Unilateral Licensing; today the clock starts when it
  leaves. With the lock, it can't leave sooner than 5 years after defecting, so a country that
  returns as soon as the lock lets it is a party again at once. Update `te_seabed_party_cooldown_left`,
  `te_seabed_party_cooldown_tt` and the Law of the Sea's terms text.
- **The buttons** grey out while locked; the tooltip gives the unlock year and the carve-out
  (`IsValidTooltip`, gotcha #16 of the GUI guide). The overview's policy box shows "next change
  19xx".
- **The AI's yearly choice** (`te_seabed_ai_choose_policy`) obeys the lock and the carve-out.

### 2.5 Giving claims up

The owner asked for a way to revoke claims. Design (my calls on the details):

- **"Relinquish"**, one button per basin, in that basin's open rivals rows beside our own row (rule
  6: beside the item it acts on). It gives up all our claims in the basin at once and stops us
  claiming there: our weight there counts as 0 at every sharing until we press **"Claim Again"**,
  which takes effect at the next sharing.
- **The relinquished claims wait for the next scheduled sharing.** Our claims go at once (the
  influence cost falls from the next monthly refresh), but the freed licences stay unclaimed until
  the next January sharing, or a mid-year one something else triggers. Relinquishing must **not**
  set `te_seabed_reshare`: a mid-year sharing honours January's floors, so a Sponsor country whose
  weight has grown since January could relinquish one claim and take every rival's unprotected
  claims, in every basin, months early.
- The existing mid-year triggers (a new claimant, a civil war's winner) carry the same asymmetry
  once floors exist: Sponsor countries keep their floors and others are re-divided. That is
  intended (protection is what Sponsor buys); don't remove the floors from mid-year sharings to
  "fix" it.
- Licences on built and queued levels are untouched. Our floor there becomes our holdings.
- It is not a policy change, so the lock doesn't apply. Nothing is gained by relinquishing and
  claiming again: the claims are gone until the next sharing gives some back by weight.
- The real seabed contracts have the same idea: a contractor must relinquish parts of its area it
  does not work.
- AI: an AI in influence deficit drops to Survey (§ 2.4); it does not relinquish (my call, the
  simplest rule).

### 2.6 The model comes first

Each rule above (fee base and grace, floors and their scaling, the reserved-half spill, the
Antarctic and Scramble overrides, relinquishing, subject pooling, leases) goes into `scripts/analysis/seabed_model.py` before the script.
`test_seabed_allocation.py` re-proves the invariants over random worlds: no basin's records rise
above its pool, no recorded licence is taken away, floors never push a basin's shares above its
pool, leases never create licences, and relinquishing then claiming again never leaves a country
ahead of not relinquishing. `test_seabed_script.py` keeps the script's names,
constants and call order matched to the model.

## 3. The panel (layout A)

The three mockups are kept at
`docs/superpowers/archive/specs/assets/2026-10-17-seabed-panel-layouts.html` (a fragment for the brainstorm
companion's frame); the owner chose A. The house style
(`docs/guides/gui_style_guide.md`) governs; this section names only what is specific. The panel is
520 GUI units wide (`te_seabed_panel`).

### 3.1 Overview: six boxes, two to a row

Rule 4's grid (`te_banking_ov_cell` is the pattern): icon inset on the left, then caption, word
and figure.

| Box | Word | Figure | Hover |
|---|---|---|---|
| **Room to build** | "125 mines" | free claims by basin, largest first: "Pacific 85 · Southern 39 · Indian 1" | Room's arithmetic: claims less levels queued past them |
| **Our licences** | "304" | "285 built · 19 queued, −¤N/wk" | Fee (§ 2.1); licences stay with their level and pass with the state |
| **Long-haul** | "55 mines" (red when > 0) | "at −25%, swap when local frees" | Which basins they borrow from |
| **Unused claims** | "125" | "January: lose at most 31", or "January: all re-divided" | § 2.2, per basin |
| **Policy** | "Sponsor" | "next change 19xx" or "can change" | Policy factor, influence held, lock and carve-out |
| **Regime** | "Regulated" | "Law of the Sea party ✓ · royalties ¤N/mine" | The regime table and the party's terms |

"Long-haul" shows only when nonzero (the box keeps its place, its word reads "none").

### 3.2 Policy buttons

Three buttons labelled **Survey**, **Sponsor**, **Unilateral**; the full name, its factor, its
influence and the lock are on hover (rule 3, option 2). Centred under the subheading (rule 6).

### 3.3 Ocean Basins table

Subheading "Ocean Basins" with "as of <month year>", the last sharing, on its right. One row per basin, all five
always shown. Columns, at 520 units (fit to the width budget, § 3.7):

| Column | Shows | Hover |
|---|---|---|
| ▸ **Basin** | name; the chevron opens the rivals (§ 3.4) | home or distant coast; our coastal states and ports there |
| **Free here** | our claims in the basin, green when > 0 and we have coast there (building there has no long-haul penalty) | "Build in: <our coastal states in this basin>" (up to five, then "and N more") |
| **Pool** | stacked bar of the whole pool: our built licences, our queued licences (hatched), our claims, rivals' licences, rivals' claims | the five figures and the pool size |
| **Our weight** | our share of the basin's total claim weight, as a percentage | the weight breakdown (coast, ports, navy, policy factor) and the raw figures |
| **+1 licence** | "+X" (navy needed; the unit is in the header's hover), or "full" when nothing is left to share, or "—" when we claim nothing | "+X navy, or +1 coastal state here ≈ +K licences" (§ 3.5) |

Rivals' claims are the part a buildup can win, so the bar's legend says so: "rivals' claims (up
for grabs)".

Our queued licences per basin come from the monthly recording, which already walks every coastal
state: a state's queued levels (`level_after_queued_constructions − level`) count against its
distant licences first, then its own basin's. That is exact wherever a state's licences all come
from one basin, the usual case; a level takes a distant licence only once the local share is gone,
so distant licences are normally the newest (my call). Only the bar's shading rests on it. On Sponsor, part of a rival's claims are protected; the bar does not split them (my
call: too fine for the bar), the hover gives the figure.

### 3.4 Rivals

Each basin row has a chevron. Open, it lists that basin's claimants under the row: vanilla's
`flag` widget (name on hover, opens the country on click), then one line of their mines, their
claims and their weight share. Sorted by share, largest first.

- Data, by the two proven routes of § Engine facts (gotcha #15): at the sharing,
  `te_seabed_yearly_pass` writes the six largest shares in each basin to global variables
  `te_seabed_rk_<basin>_<n>` (n = 1..6, an `ordered_country` pass per rank), and writes each
  ranked country's capital to `te_seabed_rkcap_<basin>_<n>` on every player country, for the flag.
  The row's text is a scripted GUI's `ExecuteTooltip`, as `ch_board_row_sgui` prints a
  leaderboard row. Per-country figures are the existing `te_seabed_held_<basin>`,
  `te_seabed_unbuilt_<basin>` and `te_seabed_w_<basin>` over the world total.
- **Cap** (my call): the first 6 rows, then "and N others"; the player's own row always shows,
  marked "us", whether or not it is in the six.
- **Our own row carries the basin's "Relinquish" or "Claim Again" button** (§ 2.5).
- Collapsed by default (rule 1 treats a live list as open, but five open lists would push the
  explanation off the panel; the table row already carries the headline). Collapse flags follow
  rule 7's naming (`_open`).

### 3.5 The "+1 licence" readout

Computed at the January sharing, stored per country per basin, and shown as "about".

- In the sharing's final round, let `R` be the licences left to the active set and `W` the active
  set's total weight. An active country with weight `w` gets about `R·w/W`. For one more licence,
  `t = share + 1`, it needs extra weight

  ```
  Δw = (t·W − R·w) / (R − t)
  ```

  (no answer when `t ≥ R`: show "full"). A frozen country (its holdings or floor above its
  share) needs `t = max(held, floor) + 1`, with `R` and `W` taken as if it were active.
- Under the Regulated regime an eligible party's share comes from both halves. Use the open half's
  `R` and `W` (every claimant is there), and for an eligible party also the reserved half's, and
  show the smaller `Δw`.
- **Weight to navy**: at home, `Δnavy = Δw ÷ (policy factor × navy multiplier × coastal states in
  the basin ÷ all coastal states)`; distant, `Δw ÷ (0.05 × policy factor × navy multiplier)`.
  Round up to a whole unit. "Navy" is whatever the weight counts: naval power projection, or
  `navy_size` if that can't be read (§ 6.1).
- **A coastal state** adds about `2 × policy factor` weight plus its ports, and shifts the navy's
  spread; the hover gives "≈ +K licences" from `R·Δw/W`, rounded down.
- `seabed_model.py` gets the exact answer (re-run the sharing with only that country's weight
  raised); a test checks the closed form against it over random worlds, within one unit of navy or
  10%.

### 3.6 How Seabed Licences Work (collapsed)

Rewrite the five subsections in the new words, and add two: **Claims and Protection** (§ 2.2,
the fee, the lock) and **Leases** (§ 4). Each stays short; the reader is a learner.

### 3.7 Elsewhere, and the width test

- **State tile** (`TE_STATE_SEABED_TT`, `gui/states_panel.gui`): same words; the per-basin lines
  become "held, claims; world in use of pool".
- **Building gate tooltips** (`te_seabed_gate_*_tt`): "the next level here takes a licence from
  this basin's claims and costs ¤N a week until built".
- **A width-budget test**, `test_seabed_layout.py`, on `test_banking_layout.py`'s
  `WidthBudgetTest` pattern: every fixed-width cell fits its longest text at its font, the buttons
  included. The overflow is what started this.
- `scripts/analysis/check_gui_lint.py` passes before the play-test.

## 4. Leasing claims

**Five directed treaty articles**, one per basin: "Lease Pacific Seabed Claims" and so on (my
call: `quantity` alone is the proven input; a `state` input to name the basin would need a
`quantity` + `state` pair that nothing in vanilla or the mod uses). Generate them from one
template if the builder prefers; the existing generators show how.

- **Kind** `directed`. The **source** leases N of its claims in the basin to the **target**.
  `required_inputs = { quantity }`, minimum 1, maximum the source's claims there at the time.
- **N is the lease's total** (my call). The licences the lessee has built on the lease plus its
  unused leased claims never exceed N. At entry into force, up to N of the source's current claims
  move at once, so the lessee can build before January. At every sharing after, the sharing runs
  as usual and then tops the lessee's unused leased claims back up to `N − built on the lease`,
  from the source's share in that basin, as far as that share goes.
- **Each lease keeps two counters**, its built and unused leased claims, apart from the lessee's
  own claims (variables on the lessee per basin and source, or a list; builder's choice). A level
  the lessee records takes its own claims first, then leased ones, so a lease is only drawn on
  when needed.
- **Licences built on leased claims are the lessee's for good.** A licence belongs to its level
  (the earlier design's § 2.4). When the lease ends, its unused leased claims return to the
  source at the next sharing; its built licences stay. *Amended after the phase 2 review
  (2026-10-17, builder's call on the owner's "switching off and on shouldn't pay" default):* the
  built licences also go on counting against the source's share, not the lessee's, for as long
  as both countries take part in the sharing, and while they do the lessee may lease that
  basin's claims again only from the same source. Were they the lessee's own once the lease
  ended, ending and re-signing a lease each year would move their cost onto third parties.
- **Flags**: `can_be_enforced`, `can_be_renegotiated`, `giftable`. `can_be_enforced` makes "take
  their seabed claims" a war goal. Usage limit `once_per_treaty` per basin article.
- **Price**: the usual pairing is a Money Transfer the other way, in the same treaty. The article
  sets no price itself.
- **Possible**: both sides are claimants (Abyssal Plain Mining, a coastal state); the source has
  claims in the basin; the Antarctic Treaty forbids a party leasing Southern claims to anyone and
  receiving them.
- **AI** (`article_ai_usage`, per `docs/vanilla/treaty_articles_reference.md`): offer when the
  source has claims it is unlikely to use (no Deep-Sea Mine levels queued, or claims well above its
  construction pace); request when the target's room is near 0 and Tech-Critical Metals sell above
  base price. Exact weights: builder, in the AI values table.
- The article's tooltip shows N, the basin and the protected status.
- Add it to `docs/vanilla/treaty_articles_reference.md` (a CRLF file: preserve line endings) and
  to the player guide's treaty article list.

## 5. Geography

### 5.1 Unincorporated coast counts

Claim weight's coast term counts **unincorporated coastal states at half** (my call on the
fraction), as overseas islands give real powers their economic zones. Ports in them count in full.
The navy's spread over the coast (`navy × coastal states in this basin ÷ all coastal states`)
counts them at the same half. A basin with only unincorporated coast is still "home".

### 5.2 Subjects lease their claims to their overlord

An overlord diplomatic action, **"Administer Seabed Claims"** (my working name), modelled on Raise
Payments. It is **an automatic lease** (owner): it reuses § 4's machinery instead of adding
weight rules.

- Overlord → direct subject; no approval; not for protectorates or personal unions (as Raise
  Payments); no DLC gate.
- **Only ever the overlord's choice** (owner: "as long as you don't have to take your subject's
  claims"). Nothing pools without the action, and the overlord can end it at any time.
- **While it stands**: the subject still claims by its own weight. At entry and at every sharing,
  its unused claims in every basin pass to the overlord as leased claims, kept in § 4's counters.
  Unlike a treaty lease it has **no total**: each sharing passes on whatever the subject has unused
  then, with no cap. The subject's licences stay its own; they belong to its levels.
- **Where the overlord can use them**: in its own states only. In a basin where it has no coast,
  its levels on those claims are long-haul at −25% (owner: acceptable). Building in the subject's
  waters would change the gate and recording, and is out of scope.
- **Cost**: liberty desire rises while it stands, at Raise Payments' rate (my call), and the
  subject's opinion of the overlord falls.
- **Ends** when the overlord ends it, or the subject is no longer its subject; unused leased
  claims return to the subject at the next sharing, as for a lease. *Amended after the phase 2
  review (2026-10-17):* the licences the overlord built on them go on counting against the
  subject's share while both take part, as for a lease, so ending the action and taking it again
  moves nothing onto a third party; only an action by another overlord starts afresh.
- **AI**: an overlord uses it when the subject has unused claims and its liberty desire is low.
- Add a line to the player guide's diplomacy chapter where subject actions are listed.

## 6. Navies

### 6.1 Naval power projection counts toward claim weight

- The navy term of claim weight (`te_seabed_navy_effective`, now `navy_size`, "number of
  flotillas") becomes the country's **naval power projection** (owner), so a modern fleet
  outweighs a large obsolete one.
- **Unverified as a number.** `docs/engine/triggers_parsed.txt` documents
  `naval_power_projection` only as a comparison, and `event_targets_summary.txt` lists
  `navy_size` but not it. Vanilla does read it as the right-hand side of comparisons
  (`c:JAP.naval_power_projection`, `ryukyu_rivalry_buttons.txt:403`;
  `scope:other_country.naval_power_projection`, `static_treaty_acceptance.txt:270`), which
  suggests a value link. Check offline first (`/engine-docs`), then ship with a once-a-game
  `TE_SELF_CHECK OK|BROKEN seabed_power_projection` line logging it beside `navy_size`. The
  fallback is `navy_size`, and the header and hover say "navy".
- **Scale.** Power projection runs on a different scale from flotillas. Divide it by a constant
  so a typical fleet's term matches today's flotilla term, keeping the coast and port terms'
  balance; set the constant from a save and record it in the values file.
- The readout cell (§ 3.5) shows the figure only, "+X"; the column header and the hover name the
  unit, so the cell never has to fit "naval power projection".

### 6.2 Blockades cut seabed output

- Set `building_ocean_mine` to **`city_type = port`**, the field every blockade-affected vanilla
  building shares (§ Engine facts). Then a blockade cuts its throughput by up to 75% at full
  blockade level, as it does a fishing wharf's.
- Check the visual: `city_type` also decides which city mesh the level draws. Port meshes on a
  coastal state are the right picture for a mine ship's home port.
- **Unverified.** Put it on the play-test list: blockade a state with Deep-Sea Mine levels and read
  the building's throughput breakdown. If it does not apply, the fallback is a state modifier from
  `on_monthly_pulse_state`, `building_ocean_mine_throughput_add = −0.75 × blockade_level`
  (state-scoped scaling from a state pulse, one refresh site), which the play-test list names.

## 7. The rush, announced

Notifications (the `te_notifications_l_english.yml` pattern), no events:

- **"The Seabed Rush Begins"**, to every country, when the first country researches Abyssal Plain
  Mining.
- **"A New Claimant in the <Basin>"**, to each claimant there, when a sharing first gives a
  country a share in a basin where the receiver has a share.
- **"The <Basin> Is Fully Licensed"**, to each claimant there, when the world's licences in a
  basin reach its pool.

**Amended in phase 3 (owner, 2026-10-17):** "The Seabed Rush Begins" is an event, not a
notification, because the research already had a headline notification
(`headlines_tech_abyssal_plain_mining`) saying much the same. While the Global Commons rule is on,
the event (`te_seabed.3`) goes to every player in its place; with the rule off the headline stays.
The other two stay notifications.

## 8. AI, in one place

- Policy: the existing yearly score, obeying the lock (§ 2.4). Sponsor's protection raises its
  value for a country with large claims; the score's terms are the builder's.
- Building: the engine's builder obeys the gate and knows nothing of the fee. Watch AI fee totals
  in an observer run; if AIs queue far ahead of their construction, the fix is a lower rate or a
  fee that starts after a grace period, not an `is_ai` rule.
- Leases (§ 4) and the subject action (§ 5.2) carry their own AI blocks.

## 9. Docs, tests and the play-test list

- **Player guide**: `02-timeline.md` § Seabed licences (licence and claim, fee, protection, lock,
  leases, blockades, islands, the panel); `17-reference.md`'s glossary rows (Seabed licence; add
  Seabed claim); the treaty article list in `09-diplomacy.md`; the subject action. Rebuild the
  PDF.
- **System docs**: `docs/systems/mod_systems.md` § Global Commons and the state-tile row.
- **Tests**: the model and its random-world invariants (§ 2.5), the readout check (§ 3.5), the
  width budget (§ 3.7), and the existing seabed tests updated.
- **Self-check**: extend `te_seabed_cap_check` to log `TE_SELF_CHECK OK|BROKEN seabed_floor_fits`
  with the figures, the first January a floor is applied.
- **Play-test list**: blockade enrolment (§ 6.2); the power-projection self-check (§ 6.1); the
  rivals list renders and opens; the fee shows in the budget after the grace; relinquishing frees
  claims for others the next month; a lease moves claims at entry into force and at the sharing;
  an enforced lease from a war; the lock greys the buttons and both carve-outs free them.

## 10. Phasing

| Phase | Contents | Depends on |
|---|---|---|
| 1 | Words (§ 1), fee, protection, cost, lock (§ 2), the panel (§ 3), the model and tests, guide | — |
| 2 | Leases (§ 4), unincorporated coast and subjects (§ 5) | 1 (floors, the sharing's hooks) |
| 3 | Power projection and blockades (§ 6), the rush notifications (§ 7) | — (independent) |

Phase 3 can run beside phase 1.

## 11. Deferred (v2)

- **Seabed Sabotage**: a covert operation that disables a rival's Deep-Sea Mine levels in one
  state for some months; deniable, works in peacetime, like real cable-cutting. Owner: good idea,
  later.
- The earlier design's "Seize Seabed Claims" war goal is **dropped**, not deferred: an enforced
  lease does its job.

## 12. My calls, for the owner to check

1. The fee rate: half the royalty (§ 2.1), and where it goes outside the Regulated regime. The
   grace is measured from two January snapshots per state, assuming levels finish in the order
   they were queued.
2. The per-claim cost rate (0.5 influence) and Unilateral at 1.5× and at least 150 (§ 2.3).
3. Protection lapses in a Scramble (§ 2.2), and the floor is fixed in January, not recomputed by
   a mid-year sharing.
4. Relinquishing is all of a basin's claims at once, reversed by "Claim Again" from the next
   sharing; the AI doesn't use it (§ 2.5).
5. Five per-basin lease articles rather than one with a state input; a lease's N is its total,
   built plus unused (§ 4).
6. Unincorporated coast at half (§ 5.1); the subject action's cost at Raise Payments' rate (§ 5.2).
7. Rivals: first six and "us", collapsed by default (§ 3.4).
8. Notifications, not events, for the rush (§ 7). Owner, 2026-10-17: the first is an event, in
   place of the research's headline (§ 7's amendment).
9. Power projection scaled by a constant to today's flotilla term (§ 6.1).
