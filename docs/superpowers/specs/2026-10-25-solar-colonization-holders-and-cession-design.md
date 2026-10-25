# Solar System Colonization, slices 0 and 1: colony holders and cession — design

Drafted 2026-10-25. Slices 0 and 1 of the scope in
`2026-10-25-solar-colonization-contest-scope.md` (§ 10), whose § Decisions and
§ 11 record the owner's calls; this design assumes them. Slice 0 gives every
colony a record that names its holder, passes a dead holder's colonies on, and
lists the solar system in the panel. Slice 1 makes the setting four levels of
the Space Race rule and adds Cede Colony, a treaty article that moves one colony
from one country to another, by sale, gift or war. The plan is
`../plans/2026-10-25-solar-colonization-holders-and-cession.md`.

## Intent

Today a colony is a global flag that says the world is claimed, and a modifier
on its holder's journal entry; nothing records who holds it
(`space_race_effects.txt:832`, `sr_grant_colony_modifier` at `:1829`). Annexing a
holder removes its colonies from the game, and a colony can never change hands.

After these two slices:

1. **Every world has a holder record**, the source of truth. The holder's
   `<modifier>_held` variables and its journal entry's modifiers become a
   projection of it, so the panel, revolution repair and their tests keep
   working.
2. **A dead holder's colonies pass to whoever owns its last capital**, under
   every setting but off. Worlds whose holder vanished before this change come
   back into the draw.
3. **The panel lists the solar system**: every world, by location, with its
   holder.
4. **The Space Race rule has four settings**: off, races only (today's system,
   still the default), simple colonies and full colonies.
5. **Under simple and full, Cede Colony** moves a named colony between
   countries: a sale (with a Money Transfer the other way), a gift, or a war
   goal enforced in a peace.

## Non-goals

Population, modules, colony fleets that travel, site targeting, free colonies,
fleets: later slices. Nothing here changes how a colony is founded, what a
specialization does, or the launch windows. Races only stays today's system
apart from the dead-holder rule and the released worlds (§ 6).

## Engine facts

**Rests on:**

- Global variables can hold a country, and a stored country compares with `?=`
  (`te_civil_war_repoint_uprisings`: `var:te_cw_origin ?= scope:te_cw_loser`).
- `exists = <var>` plus `is_country_alive = yes` is the mod's guard for a stored
  country that may have died (`banking_rescue_donor_exists`).
- The global monthly pulse runs with no ROOT (`sr_launch_windows_on_actions.txt`),
  and `every_country` works there.
- A variable can hold a capital's state region: nuclear custody records
  `nd_ar_capital_region = scope:nd_ledger_owner.capital.state_region`
  (`nuclear_custody_effects.txt:129`). `ordered_scope_state` iterates a state
  region's states (`docs/engine/effects_summary.txt:1548`).
- Treaty articles: `required_inputs = { building_type }` with a
  `building_type_valid_trigger` (vanilla `acquire_monopoly_for_company`);
  `usage_limit = once_per_side_with_same_inputs` (vanilla `state_transfer`);
  in an input trigger `root` is the source and `scope:input` the candidate
  (`scripting_best_practices.md`, the treaty article scopes);
  `scope:article_options.input_building_type` in `on_entry_into_force`
  (`treaty_article_options|input_building_type`, `docs/engine/event_targets_summary.txt:128`);
  `bt:<building_type>` as a global link (used in `un_dossier_values.txt:898`).
- A building type that can never be built: `potential = { always = no }`, the
  pattern of the retired company buildings (`company_buildings.txt:3505`).
- Game rule settings are read with `has_game_rule = <flag>`, one flag per
  setting named after it, as every rule in `extra_game_rules.txt` does.

**Unverified, each with a self-check (§ 13):**

- What a global variable holding an annexed country reads as: `exists` false, or
  `is_country_alive = no`. Both are guarded.
- That the treaty designer offers a building type that can never be built, that
  `scope:input = bt:<type>` compares a building type, and that
  `input_building_type` reads back in `on_entry_into_force`.
- That a country given a colony without the Moon Base and Mars Landing gets the
  journal entry through `add_journal_entry` and keeps it under the widened
  `possible`.

**Not relied on:** a setting carrying a second flag that `has_game_rule` reads.
No rule in the mod does it, and if it failed the whole space race would turn off
under simple and full without a word in the log, so § 10 uses one flag per
setting and a scripted gate.

## 1. The site table and its generator

`scripts/generators/gen_solar_sites.py`, a post-load regenerator beside
`gen_launch_windows.py`, holds one table, `SITES`: for each of the 34 worlds, in
today's order, its key (the `sr_colony_<key>` suffix), stage, location (the
owner's nine, for the panel), launch-window body (`gen_launch_windows.BODIES`,
Mercury none), founding event, its two specialization modifiers in option
order, its discoveries, and its icon kind (`colony_<kind>.dds`). A test holds
the table to the colony events, the launch-window bodies and the discovery
seeds, so it can't drift from the script it describes.

It writes:

| File | What |
|---|---|
| `common/scripted_effects/sr_sites_generated.txt` | the founding draw and the stage check (moved out of `space_race_effects.txt`), the per-site monthly step, sync, transfer, release and migration, the choice dispatcher, Cede Colony's apply, the panel snapshot |
| `common/scripted_triggers/sr_sites_generated.txt` | Cede Colony's input filter, `sr_any_site_unclaimed`, `sr_holds_site_<key>` |
| `common/script_values/sr_sites_generated.txt` | `sr_sites_held_count`, the panel's `sr_disp_site_<key>`, the AI's value of a ceded site |
| `common/buildings/sr_site_buildings_generated.txt` | the 34 hidden site building types (§ 11) |
| `common/customizable_localization/sr_sites_generated_custom_loc.txt` | a site's name from its index, for the notices |

**Step one reproduces today's file.** The generator's first output is the
founding draw and the stage check exactly as they stand, moved to the generated
file with nothing else changed, and the existing launch-window tests (which read
the draw) pass against it. The holder records then go in as a reviewable diff
of the generator.

Hand-written beside it: `sr_site_effects.txt` and `sr_site_triggers.txt`
(what is not per site), `sr_sites_on_actions.txt`, the site building group,
the two notice events, the console event, and the loc.

## 2. The site record

Global variables, per world (`<key>` from the table):

| Variable | Holds | Written by |
|---|---|---|
| `sr_colony_<key>` | the claim, as today (`yes`) | the founding draw; cleared by a release (§ 6) |
| `sr_site_holder_<key>` | the holder (a country) | the founding draw, a transfer, a dead holder's heir, the migration |
| `sr_site_spec_<key>` | the specialization chosen: 1 (the event's first option) or 2 | the choice dispatcher (§ 3) |
| `sr_site_region_<key>` | the holder's capital state region | the monthly step, while the holder is alive and has a capital |
| `sr_site_mirror_<key>` | the country whose variables and entry currently show the site | the sync (§ 4) |

Per discovery (`<d>` from the table; each belongs to one world):
`sr_site_disc_<d>` (1 or 2, the option chosen when it was made) and
`sr_site_disc_<d>_pending` (rolled at founding, not yet made).

The country keeps `sr_colony_count`, now recounted from the records
(`sr_sites_held_count`) every time a site it holds or held changes. All its
readers (the entry's `possible` and `fail`, `sr_has_space_colony`, the charter
and election events, `extra_on_actions.txt:2657`) keep working unchanged.

## 3. Founding and choosing

- **The draw** (`sr_establish_colony_effect`, generated) sets the claim as
  today, then `sr_site_holder_<key> = root`, then runs the site's sync.
  Everything else in it stays: the window gate, the discovery seed, the event,
  the count before and after, the first-colony charter.
- **The choice.** The colony events still call
  `sr_grant_colony_modifier = { MODIFIER = m }` for all 68 options (a test
  counts them). Its body gains one line, `sr_site_choose_$MODIFIER$ = yes`, a
  dispatcher with one generated effect per modifier: for a specialization it
  writes `sr_site_spec_<key>`, for a discovery outcome `sr_site_disc_<d>`. The
  discovery events go through the same effect, so their 40 outcomes are covered
  too.
- **Discoveries pending.** `sr_seed_colony_discovery` also sets
  `sr_site_disc_<d>_pending` when its roll succeeds, and
  `sr_finish_colony_discovery` clears it. The country's own
  `sr_discovery_<d>_*` variables, which the monthly rolls read, become the
  holder's working copy (§ 4).

## 4. The projection: the sync

`sr_site_sync_<key>` (generated, any scope) makes the holder show the site and
nobody else:

1. If the mirror names a country other than the holder (or the site has no
   holder), that country, if alive, loses the site: the `_held` variables of both
   specializations and of the site's discoveries are removed, each with its entry
   modifier where the entry has it (`je:je_space_race_solar_colonization ?=`,
   each `remove_modifier` behind its `has_modifier`, which
   `test_the_monthly_sync_removes_only_what_is_there` requires), and its
   discovery `_pending` and `_done`. Its `sr_colony_count` is recounted.
2. The holder gains it: the chosen specialization's `_held` (the other one's
   removed), each made discovery's outcome `_held` and `sr_discovery_<d>_done`,
   each pending discovery's `sr_discovery_<d>_pending`, and the matching entry
   modifiers where its entry is open. Its count is recounted.
3. The mirror is set to the holder.

A site whose specialization hasn't been chosen yet (its event still open)
carries the holder but no `_held`; the choice runs the sync again.

The sync runs at every write (founding, choice, transfer, release) and from the
global monthly pulse for all 34 sites (§ 5), so a missed write is repaired
within a month. The existing per-country `sr_sync_solar_colonization_entry`
stays as the second backstop between `_held` and the entry. The monthly country
pulse's gate widens from `sr_space_race_participant` to that or
`sr_has_space_colony`, so a holder that never ran a programme is synced too.

## 5. The monthly step

`sr_sites_on_actions.txt` adds `sr_sites_on_action` to the global
`on_monthly_pulse`, under the space race gate (§ 10). It runs
`sr_sites_monthly` (generated), which for each site:

1. **Records the capital.** While the holder is alive and has a capital
   (`exists = capital`: a country that has lost every state in a war stays alive
   without one, `vanilla_known_bugs.md`), `sr_site_region_<key>` = its capital's
   state region.
2. **Passes on a dead holder** (§ 6).
3. **Adopts or releases a holderless claim** (§ 7).
4. **Syncs.**

Then, for every player, `sr_sites_refresh_snapshot` (§ 9). A first run also
does the migration (§ 7).

## 6. A dead holder

A site whose holder variable is set but fails `exists` or `is_country_alive`:

- **The heir** is the owner of the most populous state in
  `s:<sr_site_region_<key>>` (`ordered_scope_state`, `order_by = state_population`)
  that can hold a colony (`sr_site_can_hold`: alive, not
  `is_country_type = decentralized`). The holder record is repointed and the
  sync runs; the heir's entry is opened if it has none (§ 8), and a player heir
  gets `space_race_events.91` (§ 12).
- **With no heir** (no region recorded, or no state there that can hold one) the
  site is **released**: holder and claim removed, mirror cleared. A released
  world goes back into the founding draw (below).
- Specialization and discoveries stay with the site, so the heir gets what the
  dead holder had chosen and found.

**Released worlds rejoin the draw.** Each stage's draw in
`sr_establish_colony_effect` also lists every world of the stages before it,
each behind its own `NOT = { has_global_variable = sr_colony_<key> }`. While
those stages are full, which is always until a release, those branches never
pass. A released world is claimed by the next fleet at the current stage's
goal, through its own launch window. No discount for now (the scope's
"at a discount" waits for the derelict status of later slices).

**After the last world.** Today a colony-less programme can't start once
`sr_all_colonies_complete` is set. `possible` now asks `sr_any_site_unclaimed`
(generated) instead, so a released world can be claimed after the race ended.
`sr_all_colonies_complete` itself stays set: completion is history, and every
holder still gets Interplanetary Trade Networks through the entry's existing
pulse (the owner's D2, either way).

**Revolutions.** `sr_repair_after_civil_war` gains `sr_sites_repoint_loser`:
when the rebels won and `scope:te_cw_loser` exists, every site whose holder
`?=` the loser is repointed to ROOT and synced. The dead-holder rule would reach
the same result a month later through the capital, so this only makes it
immediate.

## 7. Old saves, and claims with no holder

**Migration.** The first time the monthly step runs in a save
(`sr_sites_initialized` not set), `every_country` with any colony record runs
`sr_sites_migrate_country` (generated): for each of the 108 modifiers whose
`_held` it carries, the dispatcher writes the choice and, for a specialization,
the holder; each `sr_discovery_<d>_pending` it carries becomes the global
pending flag. Then `sr_sites_initialized` is set, and `sr_sites_grace` for 45
days.

**Adopt or release, every month.** A site that is claimed but has no holder
first looks for a country carrying one of its two specializations' `_held` and
adopts it. Once the grace has run out, a claimed site that still has no holder
and no country carrying its `_held` is released (§ 6). The grace keeps a world
whose founding event was still open when the save loaded from being released
before its choice is made. In a save where a holder was annexed before this
change, its worlds are released after the grace and can be colonized again.

## 8. The journal entry

`je_space_race_solar_colonization` (`je_space_race.txt:1252`):

- **`is_shown_when_inactive`**: the rule gate, and either a colony held
  (`sr_has_space_colony`) or today's three (Moon Base, Mars Landing, Directed
  Energy Weapons).
- **`possible`**: either a colony held, or today's colonizing branch with the
  Moon Base and Mars Landing moved into it and `sr_any_site_unclaimed` in place
  of `NOT = { has_global_variable = sr_all_colonies_complete }`. The completion
  variables stay named outside any `NOT`, which
  `test_the_monthly_gate_admits_every_country_with_state` requires.
- **Colonizing needs the milestones.** A country can now hold the entry with
  no Moon Base or Mars Landing (it was given a colony). A new trigger,
  `sr_solar_colonization_qualified` (both completion variables), joins
  `sr_solar_colonization_running`, which gates the pulse's progress, billing
  and the four controls, so such a holder's panel reads Idle and nothing is
  billed. It keeps its colony's modifiers.
- **Opening it for a new holder.** A transfer or an heir that has no such entry
  gets `add_journal_entry = { type = je_space_race_solar_colonization }`; its
  `immediate` runs the existing sync. The widened `possible` keeps it open.
- **Losing the last colony.** The giver's entry fails or deactivates as today.
  `on_fail` reports a programme loss (`space_race_events.76`) only for a
  qualified country, so a non-space country that sold the colony it inherited
  isn't told its programme failed.

## 9. The panel: Solar System

A new section in `gui/journal_entry_widgets/space_race_widget.gui`, solar
colonization's widget only, after Our Colonies: **Solar System**, every world
under its location's subheading (the owner's nine), one row each: the world's
icon and name, then the holder's flag and name, "Ours" or "Unclaimed".
Collapsible, closed by default since it is 43 lines; its flag is
`sr_panel_solar_system_closed`, client-side like the rest.

- **Rows** follow `te_sr_colony_row`, and the holder's name and flag follow the
  Rivals rows (gotcha #15 in `gui_modding_guide.md`: a country is read through a
  stored capital state). `sr_sites_refresh_snapshot` (generated, country scope,
  players only) stores each held site's holder capital as
  `sr_ss_cap_<key>` on the viewer, monthly and after any transfer that involves
  a player; the row's inner widget binds
  `datacontext = "[JournalEntry.GetCountry.MakeScope.Var('sr_ss_cap_<key>').GetState]"`.
- **`sr_disp_site_<key>`** (generated): 0 unclaimed, 1 ours, 2 someone else's,
  3 claimed by someone with no capital to show (the row then reads "Another
  power"). The outer widget's `visible` gates on it, so an empty slot is never
  read.
- The 34 rows are written by hand (one-shot script), as Our Colonies' 68 are,
  and a test holds them to the site table.

## 10. The rule: four settings

`space_race_rule` (`extra_game_rules.txt:140`):

| Setting | Flag | Loc |
|---|---|---|
| `space_race_colonies_full` | `space_race_colonies_full` | Full Colonies |
| `space_race_colonies_simple` | `space_race_colonies_simple` | Simple Colonies |
| `space_race_enabled` | `space_race_enabled` | Races Only (the name kept, so saves from before keep today's colonies) |
| `space_race_disabled` | as today | Disabled |

The default stays `space_race_enabled` until the later slices ship (scope § 9).

**Gates** (`sr_site_triggers.txt`): `sr_space_race_on` (any of the first three),
`sr_colonies_contested_enabled` (simple or full) and `sr_colonies_full_enabled`.
The 61 `has_game_rule = space_race_enabled` checks in 22 files become
`sr_space_race_on = yes`; the 9 `has_game_rule = space_race_disabled` checks stay.
A test fails on any bare `has_game_rule = space_race_enabled` outside the gate,
so a later check can't read "races only" by mistake. Simple and full do nothing
more than races only until slice 1's article, so changing the setting is safe
from the first commit.

## 11. Cede Colony

### 11.1 The site building types

`building_sr_site_<key>` (generated, 34): `building_group = bg_sr_colony_sites`
(a new group, `is_shown_in_outliner = no`), the world's icon kind
(`gfx/interface/icons/space_race_icons/colony_<kind>.dds`), `potential = { always = no }`,
`can_build_government` and `can_build_private` `always = no`, and a single
marker production method that does nothing, if the engine needs one. Loc:
`building_sr_site_<key>` is "<World> Colony", with a description. They exist only
to name a colony in the treaty designer.

### 11.2 The article

`te_cede_colony` (`common/treaty_articles/123_cede_colony.txt`), modelled on
vanilla `state_transfer` and the seabed lease:

- `kind = directed`, `cost = 0`, `maintenance_paid_by = source_country`,
  `flags = { can_be_enforced giftable }`,
  `usage_limit = once_per_side_with_same_inputs` (several colonies in one treaty,
  either way, so a swap works), `required_inputs = { building_type }`.
- `visible`: `sr_colonies_contested_enabled = yes` and the prospective source
  holds a colony. `possible`: the source holds one.
- `building_type_valid_trigger = { sr_cede_site_input_valid = yes }`
  (generated): `scope:input` is one site's building type and that site's holder
  `?=` root.
- `on_entry_into_force`: the source and target saved from
  `scope:article_options`, then `sr_cede_colony_apply` (generated): the site
  whose building type is the input and whose holder is still the source is
  transferred to the target (`sr_site_transfer_<key>`: repoint, sync, open the
  target's entry, snapshot, notices). A cession is permanent: no
  `requirement_to_maintain`, nothing on break or withdrawal.
- **AI** (`treaty_categories = { expansion }`, as `state_transfer`;
  `article_ai_usage = { offer request }`):
  - `evaluation_chance` (root only, per `treaty_evaluation_scope_audit`): 0.02 if
    root runs a colonization programme and some other country holds a colony
    (it may ask for one); 0.02 if root holds a colony and runs no programme (it
    may sell one, such as an inherited colony).
  - `inherent_accept_score`: the source −10 and minus the site's value; the
    target plus the site's value, halved if it runs no programme. The value
    (`sr_cede_ai_input_value`, generated, from `scope:article.input_building_type`)
    is 20 plus 5 a stage, 25 to 45. A Money Transfer the other way is what makes
    a sale acceptable, as vanilla adds the articles' scores.
  - `proposal_weight`: 1 when the source holds the input site.
  - `wargoal_score_multiplier`: 1 when ROOT runs a programme.
- **War goal**: `contestion_type = control_any_target_incorporated_state` (as the
  seabed lease); maneuvers 5 and infamy 10, flat, to tune in play.

### 11.3 What the player sees

The treaty designer lists the source's colonies by name ("Valles Marineris
Colony"). The panel's Solar System section shows who holds what, so a player
knows what to ask for. When a colony changes hands, a player on either side
gets `space_race_events.90` (§ 12).

## 12. Notices

Two events in `events/space_race_events.txt`, players only, each naming the
world through `sr_sites_generated_custom_loc.txt` (a country variable,
`sr_site_notice_index`, set before the event):

- **`.90` A Colony Changes Hands**: to the receiver and the giver of a cession,
  with the cause in a triggered description (treaty or peace).
- **`.91` Heirs to a Fallen Programme**: to the heir of a dead holder, naming the
  world and the country it came from (the region's former owner, saved as a
  scope before the repoint).

An event has one image, so both use an existing colony image (Valles
Marineris's), and `event_image_audit` passes.

## 13. Self-checks and the play-test list

Each a once-a-game `debug_log` line, `TE_SELF_CHECK OK|BROKEN <name>`, listed
in a new `docs/testing/solar-colonies-playtest.md`:

- **`site_dead_holder`**: the first dead holder logs which guard caught it
  (`exists` or `is_country_alive`), the site and the heir. BROKEN if the next
  month's step still finds the same dead holder on that site.
- **`cede_colony_input`**: OK when a Cede Colony entered into force and matched a
  site; BROKEN when `on_entry_into_force` ran and no site matched its input.
- **`site_receiver_entry`**: two monthly steps after a country without the
  milestones received a colony: OK when its entry is active and carries the
  specialization's modifier, BROKEN otherwise.

The play-test list adds what script can't see: that the site building types
appear nowhere but the treaty designer (the build menu, the production overview,
the encyclopedia); that the designer shows them by name and icon; that the
Solar System rows draw flags; and the annexation path end to end (the console's
`annex <TAG>` on a holder).

**Console** (`events/te_debug_space_race_events.txt`, `te_debug_space_race.2`):
log every site's record; claim the first free world for us; give one of our
colonies to the largest other space power through the article's own transfer;
release one of our colonies; run the monthly step now; refresh our snapshot.

## 14. Tests

`test_solar_sites.py`:

- The generated files are current, carry one BOM and the generated header.
- The site table matches the colony events (each event's two
  `sr_grant_colony_modifier` calls in order), `gen_launch_windows.BODIES`, the
  discovery seeds and the discovery events' outcomes.
- Every modifier `sr_grant_colony_modifier` receives (68 + 40) has a dispatcher
  effect; every site has a sync, transfer, release, migration branch, building
  type with loc, Cede Colony branch, snapshot slot, panel row and custom loc
  entry.
- The draw: each stage lists its own worlds and every earlier stage's, each
  behind its claim test; every global variable read is guarded (`?=` or
  `has_global_variable`).
- The rule: four settings, the races-only setting keeps the name
  `space_race_enabled`, no bare `has_game_rule = space_race_enabled` outside
  `sr_space_race_on`.
- The entry: `is_shown_when_inactive` and `possible` have the colony branch;
  `sr_solar_colonization_running` includes the qualification.
- The article: the flags, the usage limit, the input, and the filter's call.

Existing tests updated: `test_launch_windows.py` reads the draw from the
generated file, and its stage test admits the earlier stages' worlds.

## 15. Docs

`mod_systems.md` § Space Race (the record, the dead-holder rule, Cede Colony,
the rule), `journal_entry_systems.md` (the entry's conditions, the Solar System
section; CRLF), `treaty_articles_reference.md` (Cede Colony; CRLF), the player
guide's `16-space.md` (who holds a colony, a dead holder, the Solar System
list, Cede Colony, the rule's settings) and the rules and diplomacy chapters
where they list settings and articles, rebuilt into the PDF;
`auto_generated_files.md`, `python_tools.md` and `CLAUDE.md`'s regenerator
roster (`check_post_load_rosters.py`), `scripts/nightly_audit_select.py`'s
classification of the generated files; `scripting_best_practices.md` for what
the self-checks confirm.

## 16. My calls, for the owner to check

1. **The record is the truth, `_held` a mirror.** The alternative, keeping
   `_held` as the truth and copying it on transfer, can't hand on a dead
   holder's colonies: its variables can't be read once it is gone.
2. **One flag per setting and a gate**, not a second flag on each setting: 61
   mechanical edits instead of a silent failure mode.
3. **The heir is the owner of the capital region's most populous state that can
   hold a colony**; no one else (not the annexer of most states, not a power
   bloc leader).
4. **A released world rejoins the draw at the current stage's goal**, with no
   discount, and can be claimed after the race ended.
5. **Old saves:** worlds whose holder vanished before this change are released
   after a 45-day grace, so they can be colonized again. That is a visible
   change to an old save.
6. **Cede Colony is permanent** (no lease), costs no influence, and its war goal
   is flat (maneuvers 5, infamy 10).
7. **The AI proposes a sale only of a colony it holds without a programme, and
   asks for one only while it runs one.** That governs only what it brings up
   on its own. Acceptance has no programme test: any AI weighs a cession by its
   score, so a racing power accepts an offer that pays more than the colony is
   worth to it (owner's question, 2026-10-25).
8. **Solar System is closed by default** (43 lines); Our Colonies stays open.
9. **A holder without the milestones keeps its colony and its modifiers but
   can't colonize**, and its panel reads Idle.
