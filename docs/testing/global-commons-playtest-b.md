# Global Commons play-test list: seabed licences (agent B, spec § 2)

Spec: `docs/superpowers/specs/2026-10-16-global-commons-design.md` § 2. System doc:
`docs/systems/mod_systems.md` § Global Commons. The offline gate is `test_seabed_basins.py`,
`test_seabed_allocation.py` (the model) and `test_seabed_script.py`; this list is what only the
game can show. Merge with the other Global Commons lists into one file (integrator).

## Self-checks (every game with `global_commons_rule` on)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … seabed_cap` | each yearly sharing after the first (the global monthly pulse of a new year), after every participant has recorded. OK logs once a game, and only with licences recorded somewhere; BROKEN every year it fails | every basin's records are within last year's ceiling (its pool, or its grandfathered records if more) plus what has been recorded against no share since (`slack` ≥ 0 for all five), and no participant has a Deep-Sea Mine level, built or queued, without a record (`unrecorded_states=0`) | a negative `slack`: a basin's records grew past its ceiling (a recording took a licence no share paid for, outside the three grandfathered cases). `unrecorded_states` above 0: a level escaped recording (a state without a basin variable, or a building the walk can't see) | read the basin's states in the variable inspector: which states hold records beyond their levels, and whose shares went negative. The model (`scripts/analysis/seabed_model.py`) is the reference; reproduce the case there first |
| `TE_SELF_CHECK START/OK/BROKEN seabed_licence_follows_state` | once a game: `START` when the first state that held licences at a recording changes owner (inside `on_state_owner_change`), the verdict at the first global monthly pulse a month or more later | the state's `te_seabed_lic_*` and `te_seabed_holder` read back inside the hook and again a month later: a state keeps its variables when it changes owner (the engine fact § 2.4 rests on; Grand Monuments relies on it too) | `BROKEN` at once: the hook found a watched state with no records or no stamp, so the variables were gone before the hook ran. `BROKEN` a month later: they read back in the hook but were gone after | keep the records in **global variables per coastal state region**, with the holder stamp beside them: `gen_seabed_basins.py` emits, per coastal region, a branch that reads and writes `te_seabed_lic_<basin>_<REGION>` and `te_seabed_holder_<REGION>` (an `if` chain on `state_region = s:STATE_X`, as the basin effect is), and the state steps of `te_seabed_record_country` and `te_seabed_on_state_owner_change` call it in place of the state variables. A region split between two owners then shares one record, charged to the larger part's owner. Not implemented |

Both checks exclude the degenerate case: `seabed_cap` waits for a previous sharing (the ceilings) and
logs OK only with records in the world; `seabed_licence_follows_state` watches only states the
monthly recording saw holding licences (a global list kept apart from the states' own variables).

## Play-test list

1. **The State Panel tile.** A coastal state of a country with Abyssal Plain Mining, the month after
   the research (the first sharing): a **Seabed Licences** tile beside the Solar Collector and
   Antimatter Facility tiles, reading In use / Our share, and Distant while any level works on
   another basin's licence. Hover: this state's records, each basin's held, unbuilt, weight and the
   world's records against the pool, and the room. No "Failed to fetch variable" in `debug.log` while
   hovering, on a coastal state that never had a mine.
2. **The gate.** Build a Deep-Sea Mine in a coastal state: the building's requirements list
   "Seabed Licences to spare: N (unbuilt: …)" with a tick, and a second line saying whether the next
   level takes the state's own basin's licence or another's at -25%. Queue levels until the room is
   0: the button greys with the line crossed, and a level already under construction keeps building.
   An AI country stops queueing at its room (its builder obeys `possible`).
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
   `change_relations`).
7. **The Seabed tab.** The Timeline Extended window shows a Seabed tab on a strip of its own under
   Space Race, Colonial Empire and Grand Monuments, greyed (with its checklist) until the country has
   taken part in a sharing. Choosing it shows the overview (Policy, Regime, ITLOS party while the UN
   rule is on, Licences, From other basins while any, Room to build), the three policy buttons, a row
   per basin where the country has weight or holdings (Home or Distant, weight, share, the world's
   records of the pool) and How Seabed Licences Work, collapsed. Check that switching tabs keeps
   exactly one tab shown, and that no label ends in "…".
8. **The policy buttons and influence.** Sponsor Contractors needs 50 available influence and holds
   50 while it stands (the country's influence breakdown lists "Seabed Policy: Sponsor
   Contractors"); Unilateral Licensing 150. The current policy's button is greyed with "This is not
   already our policy" crossed. The new policy's weight shows at the next January sharing. Under
   Unilateral Licensing, two claimants sharing a home basin lose 10 relations a year with each other
   (−5 from each side of the pair: check that `change_relations` from each side moves the one
   figure, so the year's loss is 10, not 20 or 5).
9. **The AI's policy.** Over a few decades of an observer game past era 11: AI claimants move to
   Sponsor Contractors once Tech-Critical Metals sell above base price at home; Unilateral Licensing
   is rare, held mostly by great powers with poor UN standing or a rival claimant, and never by one
   with Exemplary standing; no AI flips policy every year.
10. **Old saves and the rule switched on mid-game.** Load a save from before the rule with Deep-Sea
    Mines built (the rule reads as off: nothing changes). Switch the rule on: at the first monthly
    pulse every standing level is recorded against no share (grandfathered), and at the next global
    monthly pulse the sharing runs. A country holding more than its new share has room 0; a basin
    whose old levels exceed its pool gives no one room until levels go.
11. **Revolution.** A claimant's revolution wins: the winner keeps the nation's policy (the
    variable, never seeded on the rebels) and its influence modifier comes back at its first monthly
    pulse; the conquered and rebel-held states' records stay with the states.
12. **Rule off.** A new game with `global_commons_disabled`: the Deep-Sea Mine builds without limit,
    no tile, no Seabed tab, no Long-Haul modifier.

## Engine facts the build assumes, unverified

- `level_after_queued_constructions` counts a Deep-Sea Mine that is queued but has no level yet (a
  new building under construction), and `every_scope_building` sees it (the Solar Power Receiver's
  slots assume the same).
- A state keeps its variables across a change of owner (self-check above).
- `ordered_country` with `position = 0` takes the highest `order_by` value (the largest remainder
  first).
- `change_relations` changes the pair's one relations figure from either side (item 8).
- The gate's room walk (`te_seabed_unrecorded_total`, every coastal state's buildings) is affordable
  where the AI builder evaluates `possible`; the Solar Power Receiver's gate walks every state's
  buildings the same way. Watch the script profiler on a late-game save with many claimants.
