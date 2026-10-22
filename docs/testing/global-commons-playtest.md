# Global Commons play-test checklist

What the next play-test of the Global Commons (`docs/superpowers/archive/specs/2026-10-16-global-commons-design.md`) should look at. In-game checks don't gate the merge (CLAUDE.md, "In-game checks"): where the build rests on an engine fact nobody has verified, it ships the preferred version with a `TE_SELF_CHECK OK|BROKEN <name>` line in `debug.log` and names its fallback below. Grep `debug.log` for `TE_SELF_CHECK` first.

The seabed and the UN layer need the Global Commons rule (on by default in a new game; a save from before the rule existed has it off until it is switched on). Launch windows and orbital debris follow the Space Race rule.

## Deep-Sea Mine rebalance and Extraplanetary Base logistics (§ 1)

What the next play-test should look at for spec § 1 (`docs/superpowers/archive/specs/2026-10-16-global-commons-design.md`).
The offline gate is `test_deep_sea_rebalance.py` (orderings at base prices, read from the files); these rows are
what only the game can show.

### Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … logistics_input_cut` | once a game: armed on the first monthly pulse of a country with an Extraplanetary Base of level 3 or more on Tethered Launch or Fusion Tugs (a random one if it has several), the verdict a month later on that building (re-armed if it no longer qualifies) | `goods_input_launch_capacity_mult` reads −0.3 per upgrade the building runs (−0.65 to −0.25): the mod-registered type is known to the engine and an `unscaled` building modifier counts once per building | about 0: the type is unknown to the engine (look for `Unknown modifier type` in `debug.log`) or the block isn't summed, so the upgrades do nothing. About −0.3 × `upgrades` × `level`: `unscaled` is read per level, and a large base buys no Launch Capacity. | for 0, fix the registration in `common/modifier_type_definitions/mod_entity_modifier_types.txt`; for a per-level sum, move the cut to a static modifier on the building applied from a yearly pulse (the Strategic Reserve hub's `goods_input_<good>_mult` pattern) |

### In the building panel

1. Research Muon-Catalyzed Fusion Reactors (era 12) and own an Extraplanetary Base. Its Transport in Space group offers
   Fusion Tugs. Switch to it. The Launch Capacity line of the input tooltip shows −30%, and the input drops by 30%
   (a level on Asteroid Mine buys 120 Launch Capacity a week at full staff and base throughput, 84 with Fusion Tugs).
2. Research Space Elevator. Tethered Launch appears in the Launch to Orbit group without an elevator of your own. With
   both upgrades the input is 40% of the base method's (48 a level on Asteroid Mine, 192 on Mining Colony).
3. AI: in an observer run past 2100, AI Extraplanetary Bases take each upgrade within a few years of its technology and
   don't switch back. A base flipping between the two methods of a group means the default `most_profitable` scores
   them by something other than profit; give the groups `ai_selection = most_productive` and an `ai_value` ladder
   (`pmg_emissions_control`'s pattern).
4. The Deep-Sea Mine's new figures: a level on Deep-Sea Mining at full staff employs 500 machinists, 400 engineers and
   100 academics, and produces 260 Structural Metals, 260 Tech-Critical Metals, 150 Conductive and Base Metals, 50 Gold
   and 50 Chemical and Industrial Minerals a week at base throughput. Its profit tooltip at prices near base reads
   about £22,700 a level a week, against about £7,250 for an Extraplanetary Base on Asteroid Mine in the same market.
5. Saves from before the change: existing Deep-Sea Mines keep their levels and change outputs on load, and lay off
   the half of their staff the new method no longer employs. Existing Extraplanetary Bases start on Chemical
   Launch and Chemical Tugs, the groups' defaults. Watch for a base left with no method in a new group.
6. Deep-Sea Mine support vessels: a mine on any extraction method shows a Support Vessels group on Motor Ship
   Tenders, buying 40 Motor Ships a level a week at full staff and base throughput and no ships through its
   extraction method. Research Modern Material Science: Magnetic Drive Tenders appear, and switching buys 20 Magnetic
   Drive Ships instead and adds the Production Method Retooling modifier. A save from before the group starts its
   mines on Motor Ship Tenders, the default; watch for a mine left with no method in it.
7. AI: in an observer run past 2100, AI Deep-Sea Mines move to Magnetic Drive Tenders within a few years of Modern
   Material Science and don't switch back. Mines that never move mean `most_productive` with `ai_value` 1000 / 3000
   doesn't rank cost-only methods as `pmg_emissions_control` assumes (record it there too); mines flipping back and
   forth mean the stickiness doesn't hold them.

## Seabed licences (§ 2)

Spec: `docs/superpowers/archive/specs/2026-10-16-global-commons-design.md` § 2, and for the claims, the
holding fee, Sponsor's protection, the policy lock and the panel
`docs/superpowers/archive/specs/2026-10-17-seabed-claims-and-panel-design.md` (phase 1). System doc:
`docs/systems/mod_systems.md` § Global Commons. The offline gate is `test_seabed_basins.py`,
`test_seabed_allocation.py` (the model), `test_seabed_script.py`, `test_seabed_loc.py` and
`test_seabed_layout.py`; this list is what only the game can show.

### Self-checks (every game with `global_commons_rule` on)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … seabed_cap` | each yearly sharing after the first (the global monthly pulse of a new year), after every participant has recorded. OK logs once a game, and only with licences recorded somewhere; BROKEN every year it fails | every basin's records are within last year's ceiling (its pool, or its grandfathered records if more) plus what has been recorded against no share since (`slack` ≥ 0 for all five); no monthly recording grandfathered a state that carries a stamp (`stamped_noshare=0`); no participant leaves a level unlicensed while it still holds unbuilt share (`escaped=0`). `pending` counts levels waiting for a licence because their owner queued past its room (the gate's under-construction branch): expected, not BROKEN | `stamped_noshare` above 0: a stamped state's levels went against no share, the review's H1 leak (a level a month through the gate's second branch), which the no-share count in `slack` would absorb. `escaped` above 0: a level escaped recording although its owner had share (a state without a basin variable, or a building the walk can't see). A negative `slack`: a basin's records grew past its ceiling some other way | read the basin's states in the variable inspector: which states hold records beyond their levels, and whose shares went negative. The model (`scripts/analysis/seabed_model.py`) is the reference; reproduce the case there first (`UnderConstructionBranchTest` is the H1 case) |
| `TE_SELF_CHECK START/OK/BROKEN seabed_licence_follows_state` | once a game: `START` when the first state that held licences at a recording changes owner (inside `on_state_owner_change`), the verdict at the first global monthly pulse a month or more later | the state's `te_seabed_lic_*` and `te_seabed_holder` read back inside the hook and again a month later: a state keeps its variables when it changes owner (the engine fact § 2.4 rests on; Grand Monuments relies on it too) | `BROKEN` at once: the hook found a watched state with no records or no stamp, so the variables were gone before the hook ran. `BROKEN` a month later: they read back in the hook but were gone after | keep the records in **global variables per coastal state region**, with the holder stamp beside them: `gen_seabed_basins.py` emits, per coastal region, a branch that reads and writes `te_seabed_lic_<basin>_<REGION>` and `te_seabed_holder_<REGION>` (an `if` chain on `state_region = s:STATE_X`, as the basin effect is), and the state steps of `te_seabed_record_country` and `te_seabed_on_state_owner_change` call it in place of the state variables. A region split between two owners then shares one record, charged to the larger part's owner. Not implemented |
| `TE_SELF_CHECK … seabed_floor_fits` | after each sharing in which a Sponsor Contractors floor protected something (`protected` above 0 in some basin); OK once a game, BROKEN every sharing it fails | every basin's entitlements stay within its pool, or its holdings if more, after the floors are fitted (`te_seabed_fit_floors` scaled the protected parts down where they didn't fit) | `over` above 0: a basin's unbuilt claims exceed what its pool leaves beyond its licences, so a floor pushed shares past the pool | reproduce the basin in the model (`FloorTest.test_floors_scale_down_to_fit`); read each participant's `te_seabed_fz_<basin>` and `te_seabed_floor_<basin>` in the variable inspector |
| `TE_SELF_CHECK … seabed_lease_entry` | a day after a Lease Seabed Claims article comes into force (`te_seabed.1`); OK once a game, BROKEN each time it fails | the start event found the in-force article naming the lessee, read its lessor and quantity (`n`), and moved up to that many of the lessor's own claims (`moved`) | no such article a day after entry: the lessee's `every_scope_treaty` walk, the article's `target_country` test or `input_quantity` doesn't read as assumed (or the treaty ended within the day) | read the quantity in the hook instead (`scope:article_options.input_quantity`, unproven), or start the lease at the next sharing, whose walk reads the same article (`te_seabed_lease_shift_basin`) |
| `TE_SELF_CHECK … seabed_pact_read` | a day after an overlord takes Administer Seabed Claims (`te_seabed.2`); OK once a game, BROKEN each time it fails | the subject sees the pact from its own side (`has_diplomatic_pact`), as every sharing reads it (`te_seabed_pact_stands`) | the pact isn't seen from the subject's side, or the overlord ended it within the day: then no sharing passes claims or counts the licences built on them as the subject's | read the pact from the overlord's side (iterate its `every_direct_subject` in `te_seabed_pass_subject_claims` and `te_seabed_lease_shift_held`) |
| `TE_SELF_CHECK INFO/OK/BROKEN seabed_power_projection` | once a game, at the end of the first sharing with a claimant that has a navy (`navy_size` > 0) | `naval_power_projection` reads as a number in a script value (`te_seabed_navy_effective`, `te_seabed_npp_disp`) for at least one of them. Each `INFO` line gives a claimant's `npp`, `navy_size` and their `ratio` | every claimant with a navy reads 0: the read isn't a value (vanilla only ever compares it), so the claim weight's navy term is 0 for everyone | BROKEN: revert `te_seabed_navy_effective` to `navy_size` (no scale) and the hovers' "naval power projection" to "navy". OK: before a release, set `te_seabed_power_projection_scale` to the median `ratio` of the `INFO` lines, so a typical fleet's term stays near its flotilla count; a scale left too low lets navies swamp the coast and port terms |

The checks exclude the degenerate case: `seabed_cap` waits for a previous sharing (the ceilings) and
logs OK only with records in the world; `seabed_licence_follows_state` watches only states the
monthly recording saw holding licences (a global list kept apart from the states' own variables);
`seabed_floor_fits` runs only after a sharing in which some floor protected a claim; `seabed_pact_read`
gives no verdict for a country no longer a subject; `seabed_power_projection` reads only claimants with a
navy, and says BROKEN only when all of them read 0.

`seabed_power_projection` first fired on 2026-10-17 with `OK … claimants=5 reading=4`, but none of
its `INFO` lines printed: they named the country with a bare `[THIS.GetNameNoFormatting]`, which
drops the whole line (so would the lease and pact lines have). Fixed and re-armed
(`te_seabed_npp_check_done_v2`): the first sharing on a build with the fix logs the whole set again,
even in that save, and the scale comes from those lines.

### Play-test list

1. **The State Panel tile.** A coastal state of a country with Abyssal Plain Mining, the month after
   the research (the first sharing): a **Seabed Licences** tile beside the Solar Collector and
   Antimatter Facility tiles. Its rows are this state's (2026-10-17): Basin (its ocean by name; check
   a Pacific, an Arctic and a Southern state against the Seabed tab's Free hover, which lists each
   basin's states), Licences (the licences on its Deep-Sea Mine levels), Long-haul in red while any
   of them is another basin's, Claims (our unused claims in its basin, the Seabed tab's Free figure
   for that basin) and Weight. Each row's hover: the levels built and queued with local and distant
   licences, and a "wait for a licence" line only when a level has none; the long-haul penalty
   (matching Long-Haul Seabed Operations on the state); the weight's coast (2, or 1 unincorporated),
   port levels, naval share and policy factor, with our weight in the basin at the last sharing.
   Check the basin's name renders in the Basin, Claims and Weight hovers (they splice it in), and
   that the "wait for a licence" line renders its number (it reads the state inside a key named by
   `AddLocalizationIf`, as the Grand Monument card's lines do). The Weight rows of our coastal states in a
   basin should add up to about our weight there in the tile's hover (the basin line's "weight"), less
   an Antarctic station's 5 in the Southern, and about the Weight row's own last line; under Unilateral Licensing or a scramble the naval share doubles. A
   relinquished basin, or the Southern for an Antarctic Treaty party, reads 0 with a red line saying
   why. A state just conquered has no basin until the next monthly update: Basin, Claims and Weight
   are hidden until then. Tile hover: the country's licences in use, its share and long-haul ones,
   each basin's held, unbuilt, weight and the world's licences in use against the pool, and the room.
   No "Failed to fetch variable" in `debug.log` while hovering, on a coastal state that never had a
   mine. **At 1080p no row ends in "…"**: "Southern" in the Basin row's 96 px value column, "Long-haul"
   in the 96 px label column.
2. **The gate.** Build a Deep-Sea Mine in a coastal state: the building's requirements list
   "Seabed Licences to spare: N (unbuilt: …)" with a tick, and a second line saying whether the next
   level takes the state's own basin's licence or another's at -25%. Queue levels until the room is
   0: the button greys with the line crossed, and a level already under construction keeps building.
   An AI country stops queueing at its room (its builder obeys `possible`).
   **The deciding unknown for the gate's second branch** (a state with a level under construction
   passes at room 0): does the engine re-check `possible` for construction already queued, and halt
   or cancel it when `possible` fails? Test it: at room 0 with one level under construction, use
   the console to take the country's last unbuilt share away (or watch a country whose share shrinks
   at a January sharing) and see whether the queued level keeps building. If construction under way
   is never halted, the branch is unnecessary and can go (`te_seabed_gate`). While it stays, it lets
   one extra level in at room 0, in a state already under construction: that level must **wait
   unlicensed** (the tile's In use doesn't count it, Room to build reads 0, and the button stays grey
   everywhere, branch 2 included) until a share pays for it, never be recorded against no share. Check
   that the same state can't take a third level the month after, and that the Arctic (or whichever
   basin) never shows more licences than its pool in the Seabed tab's pool bar (its hover).
3. **A level on a distant licence, the penalty and the swap.** Use up a basin's share (or build in
   a basin where the country has only a distant claim): the next level records another basin's
   licence, and within a month the state carries **Long-Haul Seabed Operations** at -25% × the
   distant share of its licences (the Deep-Sea Mine's throughput breakdown shows it). When a local
   licence frees up (a level demolished in the same basin, or a larger share at the January sharing),
   the next monthly recording swaps it and the next monthly state pulse lowers or removes the
   modifier.
4. **A conquered state's licences arriving with it.** Take a state with Deep-Sea Mine levels in a
   war: its records stay on it (variable inspector: `te_seabed_lic_*`), `te_seabed_holder` names
   the conqueror, the conqueror's tile counts them as in use, and the loser's unbuilt shares are
   untouched until the next sharing. Then demolish one of the conquered levels: its licence goes to
   the conqueror's unbuilt share at the next monthly recording. The self-check above logs its
   verdict on the first such conquest.
5. **A level finished and conquered before its recording.** Queue a level, let it finish, and lose
   the state in the same month: the loser's unbuilt share pays for it (it falls by one), not the
   conqueror's.
6. **The yearly sharing.** On 1 January (the first global monthly pulse of the year) every
   claimant's share is worked out again: the Seabed tab's rows and the tile update. A country that
   researches Abyssal Plain Mining mid-year gets its share at the next monthly pulse, not in January.
   A country over its new share keeps every level it has (its room is 0), and builds again only when
   it falls back under. No error in `debug.log` from the pass (`while`, `ordered_country`,
   `change_relations`). A new claimant's mid-year sharing re-divides every pool, but charges no
   Unilateral relations (they fall on the year's first sharing only).
7. **The Seabed tab (layout A).** The Timeline Extended window shows a Seabed tab, the strip's fifth,
   after the Colonial Empire, greyed (with its checklist) until the
   country has taken part in a sharing. Choosing it shows the overview's six boxes two to a row (Room
   to build, Our licences, Long-haul, Unused claims, Policy, Regime), each with its icon in an inset,
   the three short policy buttons (Survey, Sponsor, Unilateral), the Ocean Basins table with "as of
   <month year>" (all five basins: Free, the pool bar, Weight, +1 licence) and its legend, and How
   Seabed Licences Work, collapsed. Check that switching tabs keeps exactly one tab shown. **At
   1080p, no label ends in "…" or overflows its box**, the buttons and the overview's third lines
   included; hover every cell and check each figure against the variable inspector. The pool bar's
   five segments read left to right: our built mines (gold), queued (lighter gold), our claims
   (green), rivals' mines (red), rivals' claims (the dark background).
8. **The policy buttons and influence.** Sponsor Contractors needs and holds 50 influence plus 0.5
   per unused claim (the country's influence breakdown lists "Seabed Policy: Sponsor Contractors" at
   that figure, and it follows the claims month by month); Unilateral Licensing 1.5 times that, at
   least 150. The current policy's button is greyed with "This is not already our policy" crossed. The new policy's weight shows at the next January sharing. Under
   Unilateral Licensing, two claimants that both have coast in a basin lose 10 relations a year with each other
   (−5 from each side of the pair: check that `change_relations` from each side moves the one
   figure, so the year's loss is 10, not 20 or 5).
9. **The AI's policy.** Over a few decades of an observer game past era 11: AI claimants move to
   Sponsor Contractors once Tech-Critical Metals sell above base price at home; Unilateral Licensing
   is rare, held mostly by great powers with poor UN standing or a rival claimant, and never by one
   with Exemplary standing; no AI flips policy every year.
10. **Old saves and the rule switched on mid-game.** Load a save from before the rule with Deep-Sea
    Mines built (the rule reads as off: nothing changes). Switch the rule on: at the first monthly
    pulse every standing level is recorded against no share (grandfathered), and at the next global
    monthly pulse the sharing runs. The same after switching the rule off and on again in a running
    game: levels built while it was off are grandfathered (the stamps are cleared when it comes back
    on), not left waiting. A country holding more than its new share has room 0; a basin
    whose old levels exceed its pool gives no one room until levels go.
11. **Revolution.** A claimant's revolution wins: the winner keeps the nation's policy (the
    variable is never seeded on the rebels, and the AI writes none for a revolution's side) and its
    influence modifier comes back at its first monthly pulse; the conquered and rebel-held states'
    records stay with the states. The month after the war ends a sharing runs (`on_civil_war_won`),
    so the winner's unbuilt shares are the nation's again, not the rebel claimant's.
12. **Rule off.** A new game with `global_commons_disabled`: the Deep-Sea Mine builds without limit,
    no tile, no Seabed tab, no Long-Haul modifier.
13. **The rivals.** Click a basin's chevron: its claimants open under the row, largest share first,
    each with a tiny flag (hover: the country's name; click: it opens) and a line of mines, claims
    and weight share; six at most, then "and N other claimants"; our own row last with Relinquish
    (or Claim Again). The rows fill at the first sharing after the update and change at each
    sharing. No "Failed to fetch variable" while the list is open, in a basin with fewer than six
    claimants (the empty rows hide, and their flags read no seat). Close it again: the flag is
    `te_seabed_rivals_<basin>_open`, so every basin starts collapsed.
14. **The holding fee after its grace.** Queue a Deep-Sea Mine level and keep it unbuilt (pause the
    construction, or queue past your construction speed) across two January sharings: no fee after
    the first, the fee from the month after the second (Our licences' third line turns red,
    "−¤N.Nk a week"; the budget's expenses list "Seabed Holding Fee" and the Budget Breakdown counts
    it under United Nations). Let the level finish: the fee stops at the next monthly pulse. A party
    under the Regulated regime: its fee joins the World Development Fund's (or the UN budget's)
    weekly total with its royalties.
15. **Sponsor's protection.** On Sponsor Contractors, with unused claims in a basin a rival's
    buildup is about to take: the next January leaves you at least three quarters of them (rounded
    down); the overview's "Jan: lose ≤N" said so beforehand. Off Sponsor, they are divided again in
    full ("Jan: re-divided"). A new claimant's mid-year sharing leaves a Sponsor country's January
    figure unchanged. In a Scramble, protection lapses.
16. **Relinquish and Claim Again.** Relinquish a basin from our own row: our claims there read 0 at
    once, Sponsor Contractors' influence falls at the next monthly pulse, nothing is shared before
    the next sharing (no mid-year sharing starts), and at that sharing the other claimants divide
    them. Claim Again: our weight there counts from the sharing after; the licences on our levels
    there are untouched throughout.
17. **The five-year lock and its carve-outs.** Change policy: every other policy button greys with
    "Five years have passed since we last changed our seabed policy" crossed and the year changes
    are allowed from; the overview's Policy box reads "next change <year>". Then (a) let a rival
    with coast in one of our home basins switch to Unilateral Licensing: our Unilateral button opens
    at once; (b) run the influence into deficit: our Survey button opens. A revolution's winner
    inherits the lock (the variable). The AI's yearly choice keeps to it.
18. **The "+1 licence" readout and the Free hover.** In a basin where we claim, "+N" (navy) under +1
    licence; build that much navy (or note a rival's change) and check the next sharing gives at least
    one more licence there, all else equal. "full" in a basin with nothing left to win, "—" where we
    claim nothing. Hover a basin's Free figure: "Build at full throughput in:" and up to five of our
    incorporated coastal states there by name, then "and N more" (no stray header line, no state
    listed twice), or the no-coast line where we have none.
19. **AI holding fees, observer run.** Over a few decades of an observer game past era 11, read the
    AI countries' Seabed Holding Fee (budget, or `te_seabed_fee_cached`): it should stay small. The
    engine's builder knows nothing of the fee, so if AIs queue far ahead of their construction and pay
    much, lower the rate or lengthen the grace, never add an `is_ai` rule (spec § 8).
20. **Sponsor's cost at scale.** In a late-game save, a great power on Sponsor Contractors with most
    of a basin's claims: its influence bill (50 + 0.5 a claim) should be noticeable but affordable;
    tune `te_seabed_influence_per_claim` from the figures.
21. **A lease at entry and at the sharing.** Sign a treaty with Lease Pacific Seabed Claims for 20
    claims to us: a day later our Pacific claims rise by up to 20 and the lessor's fall as much, and
    the overview's claims hover says how many are leased. Queue levels past our own claims: the
    leased count falls and the licences hover counts those built on the lease. At the next sharing
    the lease is topped back up to 20 less what we built on it, from the lessor's new share, and the
    lessor's own share is short by those licences, not ours.
22. **An enforced lease from a war.** Win a war with Lease <Basin> Seabed Claims as a war goal: the
    loser's claims pass at once. An AI presses it only against a country with claims there, and
    only when it is short of claims itself.
23. **A lease ends.** Break the treaty, or let it lapse: our unused leased claims stay until the
    next sharing, then go back; the levels we built on it keep their licences, and the lessor's
    share at that sharing still pays for them (a third party's share doesn't move). A new lease from
    the same lessor is offered; one from another lessor in that basin is refused, with the tooltip
    naming the old lease. A lessor annexed by a third country clears the record at the next
    sharing. Re-sign with the same lessor before the next sharing: check the new lease's claims
    arrive (the old lease's licences may still count against the new total until that sharing).
24. **Administer Seabed Claims.** As an overlord with Abyssal Plain Mining, take the action on a
    puppet or dominion that claims: its claims read 0 and ours rise by them, its liberty desire
    rises and relations fall. A protectorate or personal union isn't offered it; Raise Subject
    Payments' DLC isn't needed. Build on the passed claims: the subject's share at the next sharing
    pays for those licences. End it: the passed claims stay until the next sharing, then the
    subject keeps its own, less the licences built on them; take it again and nothing is lost or
    gained.
25. **Unincorporated coast.** A country whose only coast in a basin is unincorporated: the basin is
    home, its weight hover shows the coast at half ("1.5 coast" for one incorporated and one
    unincorporated state) with the ports in full, and the Free hover lists the unincorporated states
    too: a level there works at full throughput.
26. **AI leases and pacts, observer run.** Over a few decades past era 11, AIs lease out claims they
    aren't using and ask for them when short; a lessor shouldn't lease away claims it then needs
    (if it does, raise `te_seabed_ai_lease_margin`). AI overlords take Administer Seabed Claims on
    content subjects and end it as liberty desire climbs. Watch for an AI overlord taking and
    returning it on the same subject year after year (will_propose below 25 liberty desire,
    will_break at 50): it should now cost a third party nothing, but it churns. Watch, too, AIs
    leasing out almost all their claims as soon as they have the technology (nothing queued yet).
27. **Naval power projection in the claim weight** (seabed claims spec § 6.1). Hover a home basin's
    weight: the naval term's figure is the military panel's naval power projection (twice it under
    Unilateral Licensing or a scramble), divided by the scale (300). The "+1 licence" cell reads in the
    same units. Build or modernise ships: the term rises at the next sharing; a large obsolete fleet
    should now weigh less than a smaller modern one. Read the `seabed_power_projection` lines first.
28. **A blockade cuts the Deep-Sea Mine** (seabed claims spec § 6.2). The building is now
    `city_type = port`, the field every blockade-affected vanilla building shares (fishing wharf,
    whaling station, shipyard, port, the naval buildings); nothing documents that it is the switch.
    (a) Blockade an enemy state with Deep-Sea Mine levels and read the building's throughput
    breakdown: a blockade line up to −75% at blockade level 1 (`BLOCKADE_THROUGHPUT_IMPACT_SCALING`
    = 0.75), as the state's fishing wharf shows. The state should also need more blockade strength
    (`BLOCKADE_TARGET_STRENGTH_PER_PRODUCED_UNIT`). (b) The state's map look: port meshes, or
    nothing new (`levels_per_mesh = -1`), on a coastal state are fine; a mesh out at sea or on an
    inland city is not. **Fallback** if (a) shows no blockade line: put the field back to
    `city_type = city` and add a unit state modifier `te_seabed_blockaded`
    (`building_ocean_mine_throughput_add = -0.75`, already a registered type) applied from
    `on_monthly_pulse_state` with `multiplier = blockade_level`, its one refresh site.
    `blockade_level` is documented only as a comparison trigger, so if it can't be read as a value
    step the multiplier through an `if` chain (`blockade_level >= 0.25`, `0.5`, `0.75`, `1`).
    If (b) fails alone, keep the port and look for a mesh-free `city_type`.
29. **The rush, announced** (seabed claims spec § 7: an event, `te_seabed.3`, then two feed
    notifications, `common/messages/te_global_commons_seabed_messages.txt`). (a) A new game, the
    month after the first coastal country researches Abyssal Plain Mining: every player gets "The
    Seabed Rush Begins" as a pop-up, naming that country (that country's own text if it is us; a
    landlocked country's if we have no coast), and no "turning to the ocean floor" headline for the
    research. With the Global Commons rule off the headline comes as before and no event. An old
    save past its first sharing gets nothing. (b) A later country's first share in
    a basin on our coast where we have one: "A New Claimant in the <Basin> Ocean", naming it;
    nothing for a basin we only claim from afar, nothing at the game's first sharing, nor when a
    country wins back a share it lost. Message Settings lists both notices under Seabed Licences,
    and muting them works. When two countries win their
    first share at one sharing, check each notice names its own country (the scope is saved again
    for each). (c) A basin's licences all held: "The <Basin> Ocean Is Fully Licensed" to each
    player with a share there or coast on it (one with coast and no mines there too), once; destroy or downsize a level and refill it for the second.

### Engine facts the build assumes, unverified

- `level_after_queued_constructions` counts a Deep-Sea Mine that is queued but has no level yet (a
  new building under construction), and `every_scope_building` sees it (the Solar Power Receiver's
  slots assume the same).
- A state keeps its variables across a change of owner (self-check above).
- `ordered_country` with `position = 0` takes the highest `order_by` value (the largest remainder
  first).
- `change_relations` changes the pair's one relations figure from either side (item 8).
- The gate's room walk (`te_seabed_unrecorded_total`, every coastal state's buildings) is affordable
  where the AI builder evaluates `possible`; the Solar Power Receiver's gate walks every state's
  buildings the same way. Every room read now sits behind a cheap test (the unbuilt sum, or a mine
  under construction in the state), so a country with no licences never walks. Watch the script
  profiler (`ScriptProfiling.Dump`) on a late-game save with many claimants.
- Whether a failing `possible` halts construction already under way (item 2): it decides whether
  the gate's second branch is needed at all.
- `is_revolutionary` reads true for a revolution's side in a civil war (the AI's policy choice skips
  it).
- The rivals list rests on four reads nothing in the mod has shown for this shape: an
  `ordered_country` with `check_range_bounds = no` and no `max` visits every match (Cultural
  Hegemony's leaderboard relies on it); a custom tooltip printed in a ranked country's scope reads
  that country's figures through `THIS.GetCountry.MakeScope.ScriptValue` (the Space Race launch
  windows' lines use it); `var:x > root.var:x` compares two countries' variables in a trigger (the
  Unilateral carve-out); and a state saved with `save_temporary_scope_as` inside a tooltip-only
  `ordered_scope_state` prints through `SCOPE.sState(...)` (the UN mission list's pattern, used for
  countries). Items 13, 17 and 18 test them.
- A Lease Seabed Claims article's `on_entry_into_force` runs with `scope:article_options`'
  `source_country` and `target_country` bound (the guard skips the designer's preview pass), and a
  day later the lessee's `every_scope_treaty` / `every_scope_article` walk finds the article with
  `target_country = scope:x` and reads `input_quantity` (self-check `seabed_lease_entry`).
- `quantity_max_value` reads ROOT as the source, as vanilla Money Transfer's `fixed_income` does.
- A notification keeps the saved scopes as they were when it was posted, so
  `te_seabed_claimant_notice`, which saves `te_seabed_newcomer` again for each newcomer of a
  sharing, names the right one in each (item 29 b).
- `city_type = port` is what makes a building blockade-affected (item 28). The defines speak of
  "buildings affected by blockades (such as fisheries and shipyards)"; the six vanilla
  `city_type = port` buildings include both, across four building groups.
- `naval_power_projection` reads as a number in a script value (`value = naval_power_projection`).
  The engine docs list it only as a comparison trigger (`docs/engine/triggers_parsed.txt`) and
  `event_targets_summary.txt` lists `navy_size` but not it; vanilla reads it only as a
  comparison's right-hand side (`naval_power_projection > root.naval_power_projection`,
  `brazil_navy.txt`; `c:JAP.naval_power_projection`, `ryukyu_rivalry_buttons.txt`), which suggests
  a value link (self-check `seabed_power_projection`).
- A no-approval pact action's `accept_effect` runs with ROOT the overlord and
  `scope:target_country` the subject, as vanilla Rivalry's does, and `has_diplomatic_pact` sees the
  pact from the subject's side (self-check `seabed_pact_read`); `every_direct_subject` visits an
  overlord's direct subjects.
- The policy cost's multiplier, `var:te_seabed_policy_cost_cached`, reads the variable on ROOT, and
  every caller that adds the modifier has ROOT = the country (item 8: the figure in the influence
  breakdown).

## The UN layer: the Law of the Sea, the Antarctic Treaty and the anti-satellite moratorium (§ 3, § 4, § 6.5)

The UN's part of the Global Commons (`docs/superpowers/archive/specs/2026-10-16-global-commons-design.md`
§3, §4, §6.5; `docs/systems/mod_systems.md` § Global Commons: the UN layer). In-game checks
don't gate the merge (CLAUDE.md, "In-game checks"); the play-test before a release works through
this list.

### How to run

- A late-game save with the UN founded (`event te_debug_un.1`, first option, founds it and seats
  the powers), Space Exploration researched, and, for §3, Abyssal Plain Mining somewhere.
- The seabed allocation calls `te_seabed_un_update_regime` once a year. To see
  a regime change without waiting, research Abyssal Plain Mining and wait for the yearly pass, or
  pass the Convention on the Law of the Sea from the chamber.
- The anti-satellite strike calls `te_asat_un_on_strike`. Without a war, the
  docket item can be seen by striking in a test war.

### Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … antarctic_policy_grant` | once a game: `START` the first month a country becomes an Antarctic Treaty party (its monthly pulse adds `un_antarctic_policy_modifier`), the verdict a week later (`te_global_commons_un.1`) | the country's `country_un_authority_target_add` rose by the treaty's 0.25 (`added` ≈ `expected`): a script-only type added by `add_modifier` reaches the modifier read the Policy pillar sums (un_redesign_design.md §0.10's checklist, never yet seen in game) | `added` 0: the Policy pillar sees no modifier grant added by script, the treaty's and the nuclear doctrines' alike. A whole-step gap is a law change in the week (the line prints both figures) | grant the 0.25 through a script value the pillar adds directly (`un_policy_contribution` + a party term), and check the doctrine grants the same way |

No `antarctic_policy_grant` line means nobody ratified an Antarctic Treaty: open a station (the
decision), wait for the docket's item, and vote the treaty through. A `START` with no verdict means
the country left the treaty within the week; the check re-arms for the next party.

Nothing else here rests on an unverified engine fact: the royalty is billed as dues are
(`multiplier = var:` from the country pulse), the station's and the treaty's modifiers are vanilla
types, and every trigger, docket item and vote follows a pattern already seen in game.

### The Law of the Sea and the seabed

- [ ] With the Law of the Sea in force and nobody holding Abyssal Plain Mining, the Seabed section
      reads the regime as Open, and Our Obligations shows no seabed lines under the convention.
- [ ] The first country researches Abyssal Plain Mining; at the next yearly pass the regime is
      Regulated and every country with the technology gets "The Law of the Sea Regulates the Seabed".
- [ ] The convention's hover (Table a Resolution, Our Obligations, the ITLOS icon) lists the seabed
      terms.
- [ ] A party with Deep-Sea Mines pays royalties: Our Obligations shows "Royalties: N a week",
      N ≈ 1,788 × its levels, and the Budget panel's Breakdown counts them under United Nations.
- [ ] With the World Development Fund standing, its pot (the chamber's Fund row) grows by the
      royalties; without it, the UN budget does.
- [ ] A poorer party sees "Reserved half" in Our Obligations; a richer one does not.
- [ ] A party switches to Unilateral Licensing: +10 infamy, −5 standing (Our Record: "we licensed
      seabed mining on our own terms"), +10 case strength, and "Defected" in Our Obligations; no
      royalties from the next month.
- [ ] It switches back to Sponsor Contractors: "Returning: a party again in 60 months", counting down;
      switching to Scientific Survey in between does not restart it.
- [ ] A member that refused the convention switches to Unilateral Licensing: no infamy, standing or
      case cost.
- [ ] Two great powers on Unilateral Licensing: at the next yearly pass the regime is a Scramble
      ("A Scramble for the Seabed"), and royalties stop. One leaves: two yearly passes later the
      regime is Regulated again.
- [ ] Under the disabled United Nations rule the regime stays Open.
- [ ] A revolution's winner that was a party pays royalties again the month after the war, and
      keeps a defection's cooldown.

### The Antarctic research station and the Antarctic Treaty

- [ ] With Space Exploration, the decision Open an Antarctic Research Station is offered (under the
      Global Commons rule only); taking it shows +2% research speed and +25 innovation cap, and an
      upkeep of 0.1% of GDP a year, at least 1,000 a week, under Space Race in the Breakdown.
- [ ] The AI opens stations: great and major powers with the surplus, smaller powers only with a
      Southern coastline or as treaty parties, none in default. About thirty countries is the
      target (the real number); far more means the weights in `te_decision_open_antarctic_station`
      need lowering.
- [ ] The first station puts the Antarctic Treaty on the docket (the chamber's last item: "the first
      Antarctic research station of X, and the Antarctic Treaty"); a human member with Space
      Exploration is offered it first.
- [ ] The treaty carries: the ATS icon lights, parties gain +2% prestige (×E), a party with a station
      gains "Station science shared" (+3% research speed) at its next monthly UN review, and the
      Policy row of Why Authority Is Moving rises by about 0.25 × each party's weight.
- [ ] A party holds no new Southern seabed licences in the seabed section; its built Southern levels
      keep theirs.
- [ ] A party denounces it by decision: +10 infamy, −5 standing ("we denounced the Antarctic Treaty"),
      +10 case; the treaty's line leaves Our Obligations; leaving and rejoining the UN does not
      re-ratify it.
- [ ] Two great powers outside the treaty hold Southern licences: within a month the treaty lapses,
      every member gets "The Antarctic Treaty Lapses", the ATS icon goes dark, and the docket does not
      raise it again while the condition holds.
- [ ] Closing the station removes its modifiers and the treaty's station term at the next review.
- [ ] A revolution's winner keeps its station (research and upkeep back the month after the war).

### The Moratorium on Destructive Anti-Satellite Tests

- [ ] Before any strike the moratorium's chamber row says a strike must have been made.
- [ ] After a strike the docket takes it up (score 55; "a destructive anti-satellite strike by X, and
      the Moratorium on Destructive Anti-Satellite Tests"); the striker is never offered it and cannot
      table it for two years.
- [ ] It carries: the UNODA icon lights, parties gain +5% prestige (×E).
- [ ] A party's own strike costs twice the infamy and twice the case strength (the strike's tooltip).
- [ ] Once a year a party with a debris-removal method books "a party to the anti-satellite
      moratorium kept orbit clean" in Recent Entries, and the Delivery pillar rises by about
      0.25 × its weight.
- [ ] Under the disabled Space Race rule the row is hidden and the docket never raises it.

## Launch windows (§ 5)

What the next play-test should look at for Solar System Colonization's launch windows (spec
`docs/superpowers/archive/specs/2026-10-16-global-commons-design.md` § 5 and § 8). In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): the change lands on the offline gate (`test_launch_windows.py`, the
audits) and this is what only the game can show. A fixed item is struck through with the commit that fixed it.

### How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work". Space Race rule on.
- **Reach Solar System Colonization**: a great or major power with the Moon Base and Mars Landing done, Directed Energy Weapons
  and the Solar Colonization method on its Space Program. `event te_debug_space_race.1` option b finishes running milestones;
  research the rest from the console.
- **Console.** `event te_debug_launch_windows.1`: a stages two and a half colony fleets (the bar at 2.5 × the goal); b writes
  every body's cached window, the date's own answer, the premium and our cost to `debug.log` (`TE_LAUNCH_WINDOWS` lines); c lets
  the self-checks log again.
- **Logs.** Read `debug.log`; grep `TE_SELF_CHECK` and `TE_LAUNCH_WINDOWS`. The self-check lines name the body by its number (`body=1` is Mars; the line spells out the key), because a debug line can't print a script parameter; `TE_LAUNCH_WINDOWS` lines name it.
- **Reference.** `docs/engine/launch_windows_report.md` lists every body's premium curve, the Mars windows of 2030–2060 and the
  historical launches the method is checked against. Mars windows: 2030.12–2031.02, 2033.02–2033.04, 2035.06–2035.08,
  2037.07–2037.09, 2039.08–2039.10, 2041.09–2041.11, 2043.10–2043.12, 2045.11–2046.01, 2048.01–2048.03.

### Self-checks

Logged once a game each. Nothing logged means the premise never came up (no chemical-only colony founded, or nothing ever waited).

| Line | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN window_gate` | the first colony founded by a country with neither Asteroid Mining nor Muon-Catalyzed Fusion Reactors after a closed window has held its full bar at least once (OK), or any such colony founded while its body's window is closed (BROKEN) | closed windows held the bar and the fleet left in its window: the global cache (`sr_window_is_open_<body>`) agreed with the date's own answer (`sr_window_open_<body>`, the generated chain) and the draw read it | a colony was founded outside its window: the cache was stale or wrong (`cache_month` against `month`, `cached_wait` against `months_to_next`), or a site's draw trigger didn't hold | if `cache_month` lags `month`, the global pulse reads last month's index: make `sr_launch_window_cache_current` the only path (refresh from the entry's pulse every month) or compare against `te_history_month_index` directly in `sr_launch_departs_free`; if the cache is current, read the site's `trigger` in `sr_establish_colony_effect` |
| `TE_SELF_CHECK OK window_gate_paid` | the first off-window launch by a country with Asteroid Mining | `premium_cached` = `premium_date`, and `spent` = `goal` × (1 + premium) | the two premiums differ (stale cache) or `spent` is another figure | as above for the cache; for `spent`, `sr_launch_fleet_cost` is read before the colony effect in `sr_launch_month` |

### Checklist

1. **The panel before a window.** With the bar below the goal: no Staged in Orbit line; Mission Control's Next Windows lists
   Mars and the five asteroids with "window in N months" (or "window open"), in that order, and nothing for a world already
   claimed. With Muon-Catalyzed Fusion Reactors it reads one line, "Fusion drives: no launch windows". The months agree with the
   report (Mars) and with option b's `wait_by_date`.
2. **Fleets staged in orbit departing when the window opens.** Option a, with every stage-1 window closed (option b says which):
   the overview shows Staged in Orbit: 2.5 fleets, its hover lists each destination's next window, one fleet a month while open,
   and what Asteroid Mining and fusion drives change. Nothing is founded while every window is closed. When the first window
   opens, one colony is founded that month and the bar drops by one goal; the next month another, while the window stays open
   and a goal is left; what is left waits. Founded worlds belong to the open body only.
3. **A setback while fleets are staged.** With 2.5 fleets staged, fire a setback (`event te_debug_space_race.1` option j while
   solar colonization is the most advanced running milestone, or wait for the roll): the bar loses 25% (Ambitious) or 15%
   (Safe, Standard) of one goal, plus any flat amount, not of the whole bar. The option's tooltip says so.
4. **An off-window launch after Asteroid Mining.** Research Asteroid Mining, Standard approach, every stage-1 window closed and
   staged progress above one goal. Next Windows gives each closed destination today's premium and the verdict, months saved (to
   the stage's next window, option b's `stage_wait`) against months cost (goal × premium ÷ pace). A colony is founded off-window
   exactly when a line says "our approach would launch now", at the cheapest such destination, and the bar drops by goal × (1 +
   its premium). The month after a Mars window closes, Mars is about +43%; with the next asteroid window more than a year away,
   a pace above about 8 a month launches there on Standard (about 4 on Ambitious). On Safe every line says the Safe approach
   waits, and nothing launches off-window.
5. **Fusion drives end the windows.** With Muon-Catalyzed Fusion Reactors a full bar founds a colony in its first month, any
   month, at the plain goal.
6. **Stage change with fleets staged.** Let a rival take the stage's last world while fleets are staged: the staged progress
   carries into the next stage, whose goal is higher, and leaves in that stage's windows. When the last of the 34 worlds goes,
   any staged progress is gone and the entry finishes.
   **A programme with no colony that stops while fleets are staged** (review L2): with 2.5 fleets staged and no colony held,
   switch the Space Program off Solar Colonization (the entry fails) and back on. The entry reopens with an empty bar; on its
   first running month the bar holds 2 goals (the half-built colony is gone). The same after a revolution's winner inherits
   the programme, and after dropping below major power and back.
7. **Mercury.** In stage 3 with Mercury unclaimed and Saturn closed, a full bar founds Mercury at once; Saturn's sites wait for
   their window.
8. **The AI.** An AI power in the top three running colonization founds colonies only in windows before Asteroid Mining (check
   its colony months against option b's log or the report); its funding doesn't drop to zero while a bar waits.
9. **Old save.** Load a save from before launch windows with colonization running: the panel shows no destination lines until the
   1st of the next month (the cache is built then), and nothing errors in `error.log` about `sr_window_*` globals.
10. **Optional flavour skipped.** The colony events don't mention the arrival month (spec § 5.3's "the fleet reached Mars in
    November"); nothing to check.

### Engine facts this rests on, unverified

- The global `on_monthly_pulse` reads the new month's `te_history_month_index` (inferred in `scripting_best_practices.md`);
  if not, the entry's own refresh still corrects the cache before any launch (`sr_launch_windows_ensure_cache`). The
  `window_gate` self-check reads the date directly and would show a stale cache.
- `floor = yes` and two-decimal literals (`24395.26`) in script values decode exactly; `test_launch_windows.py` reads the
  generated chains back for every month 1900–2136 with the same arithmetic.
- `ExecuteTooltip` as a textbox's text, with `custom_tooltip_no_bullet` lines reading `THIS.GetCountry.MakeScope.ScriptValue`
  (the Cultural Hegemony leaderboard does the former; the line format is the UN chamber's).

## Orbital debris and the anti-satellite strike (§ 6)

Spec: `docs/superpowers/archive/specs/2026-10-16-global-commons-design.md` § 6.1–6.4 and § 7's
event `.31`. Systems doc: `docs/systems/mod_systems.md` → Space Race → *Orbital debris*.
In-game checks don't gate the merge (CLAUDE.md § "In-game checks"); the play-test before a
release works through this list. The console harness is `event te_debug_orbital_debris.1`:
it sets the pools to each tier, runs the month's step at once, fires a ribbon strike and puts
the Space Program on its best removal method, and every option writes a `TE_DEBRIS` line to
`debug.log`.

### Self-checks (every game, space race rule on)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … debris_removal` | once a game: armed at the first global monthly pulse at which some country's Space Program runs a debris removal method at half staff or more, the verdict a month later on that country (re-armed if it no longer qualifies) | that country's `country_orbital_debris_removal_add` reads above 0 (`removal` > 0): a secondary method group's workforce-scaled country modifier reaches the country, and the registered type is read | `removal` 0: no country's removal counts, so debris is never cleared by anyone | compute the removal in script: `te_debris_removal_country` reads the Space Program's active method (`has_active_production_method`) times its `occupancy` times the method's rate (mirror values beside `te_debris_units_*`), and the UN's Delivery term reads that value in place of the modifier |

No line at all means no Space Program has yet run a removal method at half staff: take the
decision Begin Orbital Debris Removal and wait a month.

### Play-test items

1. **The Mission Control row.** On any running milestone's panel, in the journal and on the
   Timeline Extended window's Space Race tab: "Orbital Debris: N (tier)" below the Estimate.
   Hover: the two pools, the costs at this level, the ribbon line from Hazardous, the cascade
   line from Kessler Cascade, and the cleanup line (the world's removal, how many countries,
   the largest cleaner's name, ours), or the "Nobody is removing debris" line. Check the
   largest cleaner's name renders (it reads the global `te_debris_top_cleaner` through
   `GetGlobalVariable(...).GetCountry.GetName`, a form proven in loc but not in this row), and
   that the row never pushes the panel wider. In solar colonization's passive mode the row
   is the first thing in Mission Control: check the section doesn't look cramped.
2. **The penalty.** With the console at Hazardous (60): a country with a Space Program shows
   Orbital Debris in its modifiers at multiplier 60 (setback risk +60%, pace −18%), the
   panel's risk and pace move with it, and an Extraplanetary Base, Space Elevator, Orbital
   Battlestation and Solar Receiver each show −12% throughput. The Orbital Solar Collector
   itself must show no throughput change (deliberate: see mod_systems.md). Check the
   Battlestation's unit bonuses fall with its throughput (the mod's docs say workforce-scaled
   country modifiers scale with throughput; if they don't, the Battlestation's penalty only
   saves upkeep, and should move to a unit modifier instead). A country with none of those
   buildings has no Orbital Debris modifier.
3. **A ribbon strike** (play-test list of the spec). Own a Space Elevator, console to
   Hazardous, option g: the event Ribbon Strike, its picture, both option tooltips stating the
   −50% for 6 or 2 months, the repair option showing its treasury cost. After either option
   the elevator building shows Ribbon Strike, and option g again does nothing until it ends.
4. **A Kessler cascade cleared by Fusion Sweepers** (play-test list of the spec). Console to
   Kessler Cascade (90), research Muon-Catalyzed Fusion Reactors, own a Space Elevator of ten
   levels, take Begin Orbital Debris Removal: the Space Program switches to Fusion Sweepers,
   the hover shows our removal near 1.0 a month, the index falls under 75 within about
   15 months and to near the background level within about 8 years, and Orbital Cleanup gives
   about +10% prestige. With Active Debris Removal alone the index must stay at 75 or above.
5. **The ceiling.** Console to Kessler Cascade, then strike several times (or option c again):
   the index stops at 100, and the high pool keeps its share (the low pool gives way).
6. **The anti-satellite strike.** At war with a country that has a Space Program: the action
   Anti-Satellite Strike appears in its diplomatic actions (and in the lens bar, with the
   placeholder icon), greyed with each failing requirement's line until all hold. The
   confirmation box lists the network penalty (and its six-month and half-strength cases),
   the infamy, the case strength, the relations and the debris. After the strike: the target
   holds Orbital Network Disrupted for a year (half strength with a Battlestation, six months
   on the Mars Mission or higher), we gain 5 infamy, Our Record on the UN tab shows
   Anti-satellite strikes 15 (with a UN), every other country in orbit likes us 30 less, the
   index rises by 12, both notifications read correctly (ours and the third party's), and the
   action is greyed against that target for 12 months for every country.
7. **The AI and the strike.** In an observer run with a late war between space powers: an AI
   strikes only an enemy with more in orbit than itself, rarely, and almost never once the
   index is 50 or more unless it is losing. An AI should never strike a country with no
   Space Program or orbital megaproject (the action's `possible` forbids it).
8. **The AI and removal (watch item).** In the same run, once the index reaches 25: AI orbit
   users take Begin Orbital Debris Removal. Watch whether the AI's own production-method
   choice then holds the method, flips it back to No Debris Removal (`ai_selection =
   most_productive` with cost-only methods is unobserved), or turns removal on by itself at
   a low index. Either flip-back or always-on is survivable; flip-back with re-taking every
   month is the one to fix (a `cooldown` on the decision, or `ai_value` on the methods).
9. **Event `.31`** (The Kessler Threshold) at Cluttered or above, for a programme outside
   Orbital Flight: the description names the tier, and its options add progress to every
   running milestone.
10. **The game rule off.** Space Race disabled: no Orbital Debris row (no panels), no strike
    action, no decision, and the Space Program's Debris Removal methods other than None are
    unavailable (the rule's `disable_pm_*` flags; the mod's first use of them).
11. **A revolution.** A country holding Orbital Debris and Orbital Cleanup loses a civil war
    to its rebels: the winner has both back after its next monthly pulse, and a struck
    country's 12-month cooldown carries over.

### Placeholder art

| Where | Now | Final art (icon-pipeline subject) | Proposed path |
|---|---|---|---|
| `te_asat_strike_action`'s `texture` | `diplomatic_action_icons/covert_space_espionage_action.dds` | an interceptor missile streaking up toward a small satellite that is breaking into fragments | `gfx/interface/icons/diplomatic_action_icons/te_asat_strike_action.dds` |
| the lens bar | `lens_toolbar_icons/te_asat_strike_action.dds`, a byte copy of the same placeholder | the same picture (the pipeline's lens copy) | unchanged |
| `pm_debris_active_removal` | `cat_star_purple_p1.dds` | a small servicer spacecraft grappling a dead satellite with a robotic arm | `gfx/interface/icons/production_method_icons/debris_active_removal.dds` |
| `pm_debris_laser_broom` | `cat_star_purple_p2.dds` | a ground observatory dome firing a thin green laser beam up at a tiny tumbling fragment | `gfx/interface/icons/production_method_icons/debris_laser_broom.dds` |
| `pm_debris_fusion_sweepers` | `cat_rocket_purple_p5.dds` | a fusion-drive tug with a wide mesh net gathering debris in orbit | `gfx/interface/icons/production_method_icons/debris_fusion_sweepers.dds` |
