# Solar System Colonization, slice 5: autonomy, free colonies, abandonment, covert operations and colony life — design

Drafted 2026-10-26. Slice 5 of the scope in
`docs/superpowers/archive/specs/2026-10-25-solar-colonization-contest-scope.md` (§ 10: "Covert operations,
free colonies (waiting and trade), autonomy, abandonment, colony life events
(§§ 6.4–6.6). Simple becomes the default"), whose § Decisions and § 11 record
the owner's calls; this design assumes them and the records of slices 0 to 4
(`2026-10-25-solar-colonization-holders-and-cession-design.md`,
`2026-10-25-solar-colonization-population-and-transit-design.md`,
`2026-10-25-solar-colonization-modules-and-bases-design.md`). There is no
separate plan: § 13 is the build order.

## Intent

After this slice, under Simple Colonies and Full Colonies:

1. **Every colony has an autonomy figure**, 0 to 100, which drifts each month:
   up with its people, its distance from Earth by its holder's drive, a year
   without contact, its holder's wars and a garrison's resentment; down with the
   pull of home and a charter. At 75 its holder must answer it: grant a
   charter (it keeps the colony, at a share of the colony's output), garrison it
   (for ten years, at an upkeep, and resented), or let it go. At 100 it breaks
   away.
2. **A colony that leaves becomes a free colony**: a world with people and
   modules and no holder. It gives no one its modifiers. It waits and trades:
   any country with a Space Program can supply it, which costs Launch Capacity
   and earns a share of its trade; a free colony grows only while someone
   supplies it, and its ties to each supplier grow. At full ties it asks to join
   that supplier.
3. **A holder can abandon a colony**: its people come home (to the capital) or
   stay as a free colony.
4. **A dead holder with no heir leaves a free colony** when the world has
   people, rather than releasing it (slices 2-3 design, call 11).
5. **Two covert operations act on colonies**: Incite Colonial Autonomy and
   Sabotage Colony.
6. **Colony life**: three events, the first child born on a world, a strike and
   a dome breach.
7. **Simple Colonies becomes the Space Race rule's default.**

Races only is unchanged: no autonomy, no free colonies, a dead holder's world
with no heir released as before.

## Non-goals

Reclaiming a free colony by force, garrisons as marines, Defences and the
Spaceport's work, destruction and its autonomy cost, blockades cutting a
colony's contact (slice 6, the fleets). **Survey Colony Defences** waits for
slice 6 as well: Defences are placeholders until then (slice 4, owner's
decision), so there is nothing to survey. **The outer-space convention against
seizure** waits for slice 6's seizure and destruction: under Simple Colonies a
colony changes hands only by treaty, and a convention against Cede Colony as a
war goal would forbid the one way war takes a colony. Free colonies as the
default for a dead holder's, free colonies under the UN, free colonies as
actors with diplomacy of their own, and emigration by culture stay later
(scope §§ 6.5, 7).

## Engine facts

**Rests on:**

- Everything slices 0 to 4 rest on: the global record, the sync, the global
  monthly step, `$PARAM$` substitution in variable names, a static modifier on
  the journal entry at `multiplier =` removed first, the scripted GUIs' saved
  `scope:site`.
- Timed global variables (`set_global_variable = { … days = N }`), as
  `sr_sites_grace`.
- `random_list` entries take a `trigger` (vanilla events throughout).
- A pop's `culture` and `religion` links (`docs/engine/event_targets_summary.txt`).
- Local variables survive scope changes within one effect run, so the covert
  pass hands an operation's multiplier to the colony effect it calls
  (`covert_op_effect_mult`, the operation container's own value).

**Unverified, with a self-check (§ 11):**

- `create_pop` at run time in a state, then `change_pop_religion` and
  `change_pop_culture` with a saved-scope target on the new pops. Evacuees come
  home through it in batches of 1,000. (First written as `create_pop = { culture =
  scope:x religion = scope:y }`, which fails load-time validation with "Missing
  culture": `create_pop` reads only literal keys. The batches are now made as
  vanilla's placeholder culture `promethean` and converted, 2026-10-26 log
  triage.)

## 1. The record

Global variables per world, beside slices 0 to 4:

| Variable | Holds | Set by | Cleared by |
|---|---|---|---|
| `sr_site_free_<key>` | `yes`: a free colony (claimed, no holder) | breaking away, letting go, abandonment, a dead holder with no heir | a rejoin, a release |
| `sr_site_autonomy_<key>` | autonomy, 0–100 (absent reads 0) | the monthly drift, events, Incite Colonial Autonomy, Sabotage Colony | becoming free, a release |
| `sr_site_charter_<key>` | `yes`: chartered | the autonomy event | becoming free, a release |
| `sr_site_garrison_<key>` | `yes`, timed ten years | the autonomy event | a cession or heir, becoming free, a release |
| `sr_site_aut_asked_<key>` | `yes`, timed five years: the autonomy event's cooldown | the autonomy event | a release |
| `sr_site_contact_<key>` | the month index of the last contact from Earth | a founding, settlers landing, a module landing, a supplier's month | a release |
| `sr_site_suppliers_<key>` | a free colony's suppliers this month | the monthly step | a release |
| `sr_site_born_<key>` | `yes`: its first child's event has fired | the life events | a release |
| `sr_site_petition_<key>` | `yes`, timed one year: the petition's cooldown | the petition | a release |

Per country: `sr_free_supply_<key>` (it supplies the free colony) and
`sr_free_ties_<key>` (its ties with it, 0–100), both cleared on every country
when the world rejoins a holder or is released.

The charter is the colony's and goes with it on a cession, as its people and
modules do; the garrison is its holder's and goes home. Autonomy stays with the
world.

**The monthly step** (`sr_site_monthly_<key>`) gains, after growth: for a held
colony under simple and full, the drift and its thresholds (§ 2); for a free
colony, its suppliers, ties and petition (§ 3). Its branch for a claim with no
holder skips a free colony, which would otherwise be released after the grace.
Growth runs at a free colony only while someone supplies it.

## 2. Autonomy

**The drift**, a month, percentage points (`sr_site_aut_drift_<key>`, holder
scope):

| Term | Points a month |
|---|---|
| The pull of home | −0.25 |
| People | +0.05 a 10,000 (a full 50,000 colony +0.25; with four Habitats, 150,000, +0.75) |
| Distance | +0.01 a month of the holder's transit to the world's body (`sr_transit_months_<body>`), at most +0.5 |
| No contact for more than 12 months | +0.25 |
| The holder at war | +0.25 |
| Garrisoned | +0.2 |
| Chartered | −0.4 |

So a 40,000-person Mars colony on chemical rockets with settlers arriving gains
about half a point a year and never needs answering; the same colony at
Jupiter gains about 3.4 a year and reaches 75 in about 22 years; at Saturn
about 5.4 a year. With a fusion torch the distance term all but vanishes: the
drive is what keeps the outer colonies close. Destruction of other colonies
(scope § 6.5) joins with slice 6.

**Contact** is a founding, settlers landing (emigration), a module landing or,
at a free colony, a supplier's month. A colony on Closed, or full, gets no
settlers, and a year later starts drifting.

**At 75** (once in five years per world, `sr_site_aut_asked_<key>`) the holder
gets `space_race_events.94`, *<World> Demands Self-Government*:

| Option | Now | After |
|---|---|---|
| Grant a charter | −30 autonomy | the colony keeps a fifth of its output: its specializations at 80% for good; −0.4 a month |
| Garrison it | −25 autonomy | ten years of +0.2 a month resentment, and +2% Space Program throughput a garrisoned colony (Colonial Garrisons on the entry) |
| Let it go | the colony becomes free, with ties 50 to us | — |

The AI grants a charter while it is a space power (`sr_ai_should_participate`),
garrisons when it is at war, and lets the colony go when it runs no programme.

**At 100** the colony breaks away whatever its status: free, ties 0 to its old
holder, and a player holder gets `.98`, *<World> Declares Itself Free*.

## 3. Free colonies

A free colony keeps its people, modules, specialization levels and discoveries;
it loses autonomy, charter, garrison and cooldowns. Nobody shows its modifiers
(the sync unmirrors a world with no holder). It is claimed: no colony fleet can
found it, and a fleet arriving there is diverted as at any claimed world. A
module already on its way lands and is installed.

**Supply.** Any country with the solar colonization entry, a Space Program and
simple or full colonies may supply a free colony (a button on its row, § 9).
Each month a supplier:

- pays: Free Colony Supply on its entry, +3% Space Program throughput a colony
  supplied (its Launch Capacity bill);
- earns: Free Colony Trade on its entry, +1% research speed and +2% influence
  a 20,000 of the colony's people, shared among its suppliers, at most five
  units (`sr_free_trade_units`);
- builds ties, +2 a month to 100; a country that stops loses 1 a month.

A free colony with a supplier grows at the usual 0.2% a month, and counts the
supplier's month as contact; with none, it waits, unchanged.

**The petition.** When a supplier's ties reach 100 (once a year per world,
`sr_site_petition_<key>`), the supplier with the strongest ties gets `.99`,
*<World> Asks to Join Us*: welcome it (it rejoins, at autonomy 20, with
everything it holds) or not now (ties back to 50). The AI welcomes it. A
colony let go amicably starts with ties 50 to its old holder, so a holder that
keeps supplying it can have it back in about two years; one that broke away
starts at 0. Reclaiming by force is slice 6's.

**The AI's supply review**, each January: a space power among the top three with
a positive weekly income, out of default, supplies up to two free colonies,
stopping none it already supplies; any other AI stops.

## 4. Abandonment

Each held colony's row has an Abandon button (§ 9), which asks first
(`space_race_events.93`, *Abandon <World>?*):

- **Bring them home**: its people return to the capital in batches of 1,000
  (`create_pop`, then converted to the culture and religion of the capital's
  largest pop), and the
  world is released, its modules lost. An outpost with no one in it is closed.
- **Leave them to govern themselves** (1,000 people or more): a free colony, with
  ties 50.
- **Keep the colony.**

The colony's upkeep stops because it is no longer held. The AI never abandons;
it lets colonies go only at the autonomy event.

## 5. A dead holder with no heir

Under simple and full, a world whose dead holder leaves no heir (holders and
cession design § 6) becomes free when it holds at least 1,000 people, and is
released as before otherwise. Races only releases it.

## 6. Covert operations

On the covert framework's pattern (registry `test_covert_op_registry.py`), each
acting once established, monthly, through a colony effect in the target's
scope with the operation's phase × priority multiplier (1 to 3.2):

| Operation | Code | Axis | Tier | Each month |
|---|---|---|---|---|
| Incite Colonial Autonomy | 15 | ideological | moderate | +0.5 × the multiplier autonomy at every colony the target holds (`sr_cov_incite_autonomy`) |
| Sabotage Colony | 16 | military | severe (Seasoned to launch) | the target's most populous colony loses 1% × the multiplier of its people and gains 0.25 × the multiplier autonomy (`sr_cov_sabotage_colony`) |

Both need simple or full colonies and a target holding a colony. Neither
leaves a modifier on its target.

## 7. Colony life

Three events, under simple and full, from the holder's entry pulse, one
pending at a time (`sr_life_site_pending`, 60 days); each names its world
(`sr_life_site`, a country variable, read by generated custom loc). They are
kept rare (owner, 2026-10-26: a few two-option events seen too often break
immersion): about one every fifteen years per nation, four or so in a late game.

- **`.95` The First Child of <World>**, once per nation, when its first colony
  holds 2,000 people: *a citizen of our nation* (+5% prestige for five years,
  −5 autonomy) or *a child of <World>* (+10% prestige for five years, +5
  autonomy).
- **`.96` A Strike at <World>**, 1% a month for a holder of a colony of
  10,000 people or more (the colony drawn among those): *meet their demands*
  (+5% Space Program throughput for three years, −5 autonomy) or *break the
  strike* (+10 autonomy).
- **`.97` A Dome Breach at <World>**, 0.5% a month for a holder of a colony of
  5,000 or more: a tenth of its people die; *rebuild at once* (+10% Space
  Program throughput for a year, −5 autonomy) or *leave it to the colonists*
  (+10 autonomy).

A strike or a breach starts a ten-year cooldown on both (`sr_life_cooldown`).

## 8. The rule's default

`space_race_rule`'s default becomes `space_race_colonies_simple` (scope § 9:
"simple becomes the default when slice 5 ships"). A save records its setting by
name, so a save from before keeps races only.

## 9. The panel

- **Solar System**: a free world's holder column reads Free (`sr_disp_site_<key>`
  = 4).
- **A new section, Colony Autonomy** (simple and full, open by default, flag
  `sr_panel_autonomy_closed`): a note; one row per colony we hold, generated:
  its icon and name, its autonomy and its drift a month (the drift's terms on
  hover), its status (Chartered, Garrisoned or nothing), and Abandon
  (`sr_colony_abandon_sgui`); then **Free Colonies**, one row per free world: its
  icon and name, its people, our ties, and Supply or Stop (`sr_free_supply_sgui`).

## 10. Notices

`.93` (abandon, asked), `.94` (autonomy at 75), `.98` (broken away), `.99`
(petition) and the three life events, all to the country concerned, players
seeing them and the AI choosing by `ai_chance`. Each event's world is a country
variable read by generated custom loc (`sr_aut_site`, `sr_abandon_site`,
`sr_freed_site`, `sr_petition_site`, `sr_life_site`), and each option that moves
a record says so in a `custom_tooltip` (`silent_variable_audit`).

## 11. Self-check and the play-test list

Added to `docs/testing/solar-colonies-playtest.md`:

- **`colony_evacuation`**: the first evacuation logs the receiving state's
  population before and after the batches, and the placeholder people left once
  they are converted; OK when it rose by at least 90% of the people sent home and
  none are left, BROKEN otherwise (fallback: the evacuees are lost, as a
  release always lost them).

The play-test list adds what script can't see: the Colony Autonomy section and
its rows, Free in the Solar System list, the events' text, and the two covert
operations in the diplomatic actions list.

**Console** (`te_debug_space_race.5`): log every world's autonomy, freedom and
ties; set our first colony's autonomy to 74 or to 99 (the event, or the break,
next month); free our first colony; supply every free colony; give us full
ties with every free colony we supply (a petition next month).

## 12. My calls, for the owner to check

1. **Autonomy's terms and sizes** (§ 2), and **the drive as distance**: a
   colony's distance is the holder's transit time to it, so better drives bind
   colonies closer. First guesses, to tune in play.
2. **The charter costs a fifth of the colony's output for good**; the garrison
   is temporary, costs upkeep and is resented. Neither involves marines until
   slice 6.
3. **A free colony grows only while supplied**, and **asks to join its closest
   supplier at full ties**: the one way back under Simple Colonies, where there
   is no force. The scope leaves free colonies' diplomacy for later; a petition
   is less than a treaty, and is easy to drop.
4. **Trade is shared among a free colony's suppliers**, so supplying a colony
   others already supply earns less.
5. **Evacuees come home to the capital** as the culture and religion of its
   largest pop.
6. **Survey Colony Defences and the convention wait for slice 6** (Non-goals).
7. **The AI never abandons**, and never supplies more than two free colonies.
8. **Life events are per country, not per colony**: a nation of ten colonies
   strikes as often as one of a single large colony, and the first child is
   the nation's, once.

## 13. Build order

1. The generator: the record's variables in release, transfer, sync and the
   monthly step; per-world autonomy, free, rejoin, supply and evacuation
   blocks; values; dispatchers by index; custom loc; the panel's rows.
2. The hand-written effects (`sr_colony_autonomy_effects.txt`): the drift's
   thresholds, the events' effects, supply, the AI reviews, the covert hooks,
   the entry's three new modifiers in its one refresh.
3. Events, scripted GUIs, the panel section, the static modifiers, loc.
4. The two covert operations (registry rows and their sites).
5. The rule's default; tests; docs; the player guide; the play-test list.

## 14. As built (2026-10-26)

Where the build departs from the sections above, or fills in what they leave
open:

- **Modifier names.** The garrisons' upkeep is `sr_colonial_garrisons` and the
  life events' are `sr_birth_citizen`, `sr_birth_native`, `sr_strike_settlement`
  and `sr_dome_breach_repairs`: every `sr_colony_*` static modifier is a
  specialization and every `sr_first_*` a milestone's first-to-finish reward,
  and the tests and the Nation tab registry read each family as one.
- **The life events' modifiers are on the country, timed**, each removed before
  it is added again (a same-name `add_modifier` stacks), so a second strike
  within three years renews the settlement rather than doubling it.
- **An event's world is a country variable with a 60-day `_pending`**
  (`sr_site_event_open`); `sr_site_events_clear_stale`, in the entry's pulse,
  clears one whose event never showed, so a lost event can't block its kind for
  good.
- **One dispatcher for every per-world action**: `sr_site_by_index` (a world's
  index in `local_var:sr_site_idx`) and `sr_site_by_scope` (the scripted GUIs'
  `scope:site`) call `sr_site_<action>_at = { KEY = <key> }`, hand-written and
  parameterized by `$KEY$`, so each action is written once rather than generated
  34 times.
- **The panel's status column reads Ruled** for a colony with neither a charter
  nor a garrison, and Both for one with each.
- **Free colony trade shows as a count and research** ("2 · +2.0%") in a 130-wide
  value cell; the influence is on hover.
- **Colony life is rarer than § 7's first draft** (owner, 2026-10-26, on the
  PR): the first draft fired the first child at every colony and rolled a
  strike at 2% and a breach at 1% a month with no cooldown, about twenty events
  in a 60-year late game. Now the first child is once per nation, the chances
  are 1% and 0.5%, and either starts ten quiet years. The breach's half percent
  is rolled as 1% then 50%, since no fractional `random` chance is used in the
  mod or vanilla.
- **The covert operations** were built on the registry's pattern
  (`test_covert_op_registry.py`), each with no target modifier and its own block
  in `covert_ops_apply_all_phase_effects`; mod_systems.md § Covert Warfare
  System has their gates and AI.
