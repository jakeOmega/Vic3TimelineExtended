# Solar colonies play-test checklist

What the next play-test of the colony record (slices 0 and 1 of the solar colonization scope:
`docs/superpowers/specs/2026-10-25-solar-colonization-holders-and-cession-design.md`) should look at. In-game checks
don't gate the merge (CLAUDE.md, "In-game checks"): where the build rests on an engine fact nobody has verified, it
ships the preferred version with a `TE_SELF_CHECK OK|BROKEN <name>` line in `debug.log` and names its fallback below.
Grep `debug.log` for `TE_SELF_CHECK` first, then for `TE_SR_SITES` (the record's own lines).

The console is `event te_debug_space_race.2` (log every world's record, claim the first free world, give our first
colony away as Cede Colony would, release our first colony, run the monthly step). `event te_debug_space_race.1`
still reaches the milestones.

## Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK site_dead_holder <world>: …` | once a game, the first month a world's holder is no longer alive | which guard caught the dead holder: `exists` on the stored country, or `is_country_alive = no` on a stored country that still exists. Either is fine; record which | `TE_SELF_CHECK BROKEN site_dead_holder <world>: the heir did not take it`: the transfer to the capital region's owner left the dead holder on the record | if neither guard catches it (the world stays on a dead holder, no line), store the holder's tag as well and compare tags (`c:<TAG>` and `exists`) |
| `TE_SELF_CHECK OK/BROKEN site_receiver_entry: …` | once a game, 70 days after a country without the Moon Base and Mars Landing received a colony | it holds Solar System Colonization and the colony | it has no entry (`add_journal_entry` or the widened `possible` failed) or lost the colony | put a received colony's modifiers on the country instead of the entry for a country that cannot hold the entry (`sr_site_show_modifier` would need a country branch) |

## The record

1. **Founding.** Found a colony (`event te_debug_space_race.1` to the colonization entry, or the console's claim). The
   founding event fires as before; after choosing, `event te_debug_space_race.2` option a logs the world as held by us.
   Our Colonies and the colony count read as they did.
2. **Solar System.** Open Solar System Colonization: the Solar System section, closed by default, lists every world
   under eight locations. A world we hold reads "Ours", a rival's shows its flag (its name on hover), an unclaimed one
   "Unclaimed". Check the flags draw and that no row ends in "...".
3. **A dead holder.** Find an AI holding a colony (`te_debug_space_race.2` option a), then `annex <TAG>` it from the
   console. Within a month its worlds show the new holder, the annexer of its capital, and a player heir gets "Heirs
   to a Fallen Programme". The heir's entry opens if it had none, and the colony's specialization modifier is on it.
4. **No heir.** Release a colony (option r): the world reads "Unclaimed" and is drawn again by the next fleet whose
   window is open, even from a later stage.
5. **Revolutions.** A holder whose revolutionaries win: its worlds are the winner's on the day of the win (not a month
   later), and the winner's Our Colonies lists them.
6. **Old saves.** Load a save from before this change in which a colony holder had been annexed. After 45 days its
   worlds read "Unclaimed" (`TE_SR_SITES released <world>` in `debug.log`). Every other world keeps its holder.
7. **A holder without the milestones.** Give a colony (option c) to a great power that has not landed on Mars: its
   Solar System Colonization opens, reads Idle, bills nothing and shows the colony in Our Colonies.
