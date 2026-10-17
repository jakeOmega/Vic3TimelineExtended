# Seabed claims, leases and the Seabed panel — design

Drafted 2026-10-17 from a brainstorm with the owner, after a play session in which the Seabed tab
was hard to read. It builds on the Global Commons design
(`docs/superpowers/specs/2026-10-16-global-commons-design.md`, §§ 2–3, shipped in #1002), which
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
- **Blockades cut Deep-Sea Mine output**, through vanilla's blockade throughput rule (§ 6). The
  owner pointed out that fishing, whaling and ports already lose throughput to blockades.
- **The rush is announced**: the first country with the technology, a new rival in your basin, a
  basin fully licensed (§ 7).
- **Deferred to v2:** Seabed Sabotage, a covert operation that disables a rival's mines in one
  state for some months (§ 11).

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
- **A number is stale without saying so.** Figures fixed at the January sharing carry "as of
  January 19xx".
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
- **`GetGlobalList` works in `.gui`.** A global-list datamodel was checked in game on 2026-09-28
  (12 entries). It is not in `docs/guides/gui_modding_guide.md` yet; write it up with this work.
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

- **Base**: per state, the licences recorded on it minus its Deep-Sea Mine's built `level`. That
  is the licences held by queued levels. Summed over the owner's coastal states.
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
- **Display**: the overview's licences box shows the fee in red beside the queued count (§ 3.1);
  the gate tooltip says the next level's licence will cost the fee until built.

### 2.2 Sponsor Contractors protects claims

At the January sharing, a country on Sponsor Contractors has a **floor** in each basin:

```
floor = held + floor_down(0.75 × claims)
```

`held` is the licences in its states from that basin (as now) and `claims` its unused share there
going into the sharing (`te_seabed_unbuilt_<basin>`). The water-filling freezes a country at
`max(held, floor)` instead of `held`. Its stored claims after the sharing are `share − held`. So
on Sponsor a claim fades by at most a quarter a year: 100 → 75 → 56 → 42.

- **Floors never exceed a pool.** Last year's shares summed to the pool, and a floor is at most
  last year's share, so floors only overflow where something else did: grandfathered over-pool
  holdings, or a rule that zeroes a share. If the floors' protected parts (`floor − held`) don't
  fit in what remains after holdings, scale them all down by the same factor, rounding down.
  Holdings are never touched.
- **The Antarctic Treaty overrides it.** A party's Southern share is 0; its Southern floor is its
  holdings only.
- **A Scramble voids it** (my call): while the regime is Scramble, nobody has a floor. "Nobody's
  contracts are honoured" is what a scramble means.
- **A subject pooled with its overlord** (§ 5.2) has no floor of its own; its claims go into the
  sharing.
- **Leased claims** (§ 4) count toward the lessee's floor and not the lessor's while the lease
  stands.
- **Display**: the overview's claims box shows "January: lose at most N" on Sponsor and "January:
  all re-divided" otherwise; each basin row's hover gives that basin's figure.

### 2.3 Sponsor Contractors' cost

The owner: 50 influence "is pretty much a token cost". Proposal (my call, numbers to tune):

- **Sponsor Contractors**: 50 + 0.5 influence per claim it protects (its unused claims across all
  basins, refreshed monthly). The owner's screenshot (125 claims) would pay about 112.
- **Unilateral Licensing**: stays above Sponsor for the same claims: 1.5 × Sponsor's figure, and
  at least 150.
- **Before fixing the numbers**, the builder tabulates a typical great, major and minor power's
  influence budget at eras 10–12 from observer-run saves, per the mod's
  evidence-based tuning practice, and sets the per-claim rate so a great power's full protection
  costs a noticeable but affordable slice.
- The cost tooltip (the policy buttons and `te_seabed_policy_effect_2_tt` / `_3_tt`) states the
  formula and today's figure.

### 2.4 Five-year policy lock

- **Any change of seabed policy, in any direction, locks the policy for 5 years.** A variable on
  the country holds the date of the last change, so a revolution's winner inherits the lock.
  Dropping to Scientific Survey is locked too; otherwise a player could pay for Sponsor only
  around January.
- **Carve-out**: a country may switch to Unilateral Licensing at once if, since its own last
  change, a country it shares a home basin with switched to Unilateral Licensing. Reuse
  `te_seabed_shares_home_basin_with_uni` for "shares a home basin"; the rival's switch date comes
  from the same variable.
- **The first choice is free.** A country that has never changed policy (no variable) is unlocked.
  Old saves start unlocked.
- **Interaction with the Law of the Sea**: a party that defects pays today's costs and is a party
  again 5 years after leaving Unilateral Licensing. With the lock, leaving can't happen sooner
  than 5 years after defecting, so a defection keeps a country out of the Law of the Sea for at
  least 10 years. See § 12.
- **The buttons** grey out while locked; the tooltip gives the unlock year and the carve-out
  (`IsValidTooltip`, gotcha #16 of the GUI guide). The overview's policy box shows "next change
  19xx".
- **The AI's yearly choice** (`te_seabed_ai_choose_policy`) obeys the lock and the carve-out.

### 2.5 The model comes first

Each rule above (fee base, floors and their scaling, the Antarctic and Scramble overrides,
subject pooling, leases) goes into `scripts/analysis/seabed_model.py` before the script.
`test_seabed_allocation.py` re-proves the invariants over random worlds: no basin's records rise
above its pool, no recorded licence is taken away, floors never push a basin's shares above its
pool, and leases never create licences. `test_seabed_script.py` keeps the script's names,
constants and call order matched to the model.

## 3. The panel (layout A)

The three mockups are kept at
`docs/superpowers/specs/assets/2026-10-17-seabed-panel-layouts.html` (a fragment for the brainstorm
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

Subheading "Ocean Basins" with "as of January 19xx" on its right. One row per basin, all five
always shown. Columns, at 520 units (fit to the width budget, § 3.7):

| Column | Shows | Hover |
|---|---|---|
| ▸ **Basin** | name; the chevron opens the rivals (§ 3.4) | home or distant coast; our coastal states and ports there |
| **Free here** | our claims in the basin, green when > 0 and we have coast there (building there has no long-haul penalty) | "Build in: <our coastal states in this basin>" (up to five, then "and N more") |
| **Pool** | stacked bar of the whole pool: our built licences, our queued licences (hatched), our claims, rivals' licences, rivals' claims | the five figures and the pool size |
| **Our weight** | our share of the basin's total claim weight, as a percentage | the weight breakdown (coast, ports, navy, policy factor) and the raw figures |
| **+1 licence** | "+X navy", or "full" when nothing is left to share, or "—" when we claim nothing | "+X navy, or +1 coastal state here ≈ +K licences" (§ 3.5) |

Rivals' claims are the part a buildup can win, so the bar's legend says so: "rivals' claims (up
for grabs)". On Sponsor, part of a rival's claims are protected; the bar does not split them (my
call: too fine for the bar), the hover gives the figure.

### 3.4 Rivals

Each basin row has a chevron. Open, it lists that basin's claimants under the row: vanilla's
`flag` widget (name on hover, opens the country on click), then their mines, their claims and
their weight share. Sorted by share, largest first.

- Data: at the sharing, `te_seabed_yearly_pass` fills five global variable lists,
  `te_seabed_claimants_<basin>`, with every country whose share there is above 0, in descending
  order of share (an `ordered_country` pass). The panel reads them through a `GetGlobalList`
  datamodel. Per-country figures are the existing `te_seabed_held_<basin>`,
  `te_seabed_unbuilt_<basin>` and `te_seabed_w_<basin>` over the world total.
- **Cap** (my call): the first 6 rows, then "and N others"; the player's own row always shows,
  marked "us", whether or not it is in the six.
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
  Round up to a whole unit. "Navy" is whatever the weight counts (`navy_size` today; § 12).
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
- **While the article stands**, at every sharing N licences of the source's share in that basin
  count as the target's: the sharing runs as usual, then moves N (or as many as the source's share
  allows) from the source's claims to the target's. At entry into force, up to N of the source's
  current claims move at once, so the lessee can build before January.
- **Licences built on leased claims are the lessee's for good.** A licence belongs to its level
  (the earlier design's § 2.4). When the lease ends, only the lessee's unused leased claims return
  to the lessor, at the next sharing.
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

### 5.2 Subjects pool with their overlord

An overlord diplomatic action, **"Administer Seabed Claims"** (my working name), modelled on Raise
Payments:

- Overlord → direct subject; no approval; not for protectorates or personal unions (as Raise
  Payments); no DLC gate.
- **While it stands**: at the sharing, the subject's claim weight in each basin is added to the
  overlord's, and the subject's own weight is 0. The subject's licences stay its own (they belong
  to its levels); its unused claims go into the sharing.
- **Cost**: liberty desire rises while it stands, at Raise Payments' rate (my call), and the
  subject's opinion of the overlord falls.
- **Ends** when the overlord revokes it (any time), or the subject is no longer its subject.
- **AI**: an overlord uses it when the subject has seabed weight and its liberty desire is low.
- Add a line to the player guide's diplomacy chapter where subject actions are listed.

## 6. Navies: blockades cut seabed output

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
- **System docs**: `docs/systems/mod_systems.md` § Global Commons and the state-tile row;
  `docs/guides/gui_modding_guide.md` gets the `GetGlobalList` datamodel recipe (a CRLF file).
- **Tests**: the model and its random-world invariants (§ 2.5), the readout check (§ 3.5), the
  width budget (§ 3.7), and the existing seabed tests updated.
- **Self-check**: extend `te_seabed_cap_check` to log `TE_SELF_CHECK OK|BROKEN seabed_floor_fits`
  with the figures, the first January a floor is applied.
- **Play-test list**: blockade enrolment (§ 6); the rivals list renders and opens; the fee shows
  in the budget; a lease moves claims at entry into force and at the sharing; an enforced lease
  from a war; the lock greys the buttons and the carve-out frees them.

## 10. Phasing

| Phase | Contents | Depends on |
|---|---|---|
| 1 | Words (§ 1), fee, protection, cost, lock (§ 2), the panel (§ 3), the model and tests, guide | — |
| 2 | Leases (§ 4), unincorporated coast and subjects (§ 5) | 1 (floors, the sharing's hooks) |
| 3 | Blockades (§ 6), the rush notifications (§ 7) | — (independent) |

Phase 3 can run beside phase 1.

## 11. Deferred (v2)

- **Seabed Sabotage**: a covert operation that disables a rival's Deep-Sea Mine levels in one
  state for some months; deniable, works in peacetime, like real cable-cutting. Owner: good idea,
  later.
- The earlier design's "Seize Seabed Claims" war goal is **dropped**, not deferred: an enforced
  lease does its job.

## 12. My calls, for the owner to check

1. The fee rate: half the royalty (§ 2.1), and where it goes outside the Regulated regime.
2. Protection lapses in a Scramble (§ 2.2).
3. Sponsor's cost scales with the claims it protects; Unilateral at 1.5× and at least 150 (§ 2.3).
4. The lock covers dropping to Survey; with the Law of the Sea's 5-year rejoin wait, a defection
   keeps a country out for at least 10 years (§ 2.4).
5. Five per-basin lease articles rather than one with a state input (§ 4).
6. Unincorporated coast at half (§ 5.1); the subject action's cost at Raise Payments' rate (§ 5.2).
7. Rivals: first six and "us", collapsed by default (§ 3.4).
8. Notifications, not events, for the rush (§ 7).
