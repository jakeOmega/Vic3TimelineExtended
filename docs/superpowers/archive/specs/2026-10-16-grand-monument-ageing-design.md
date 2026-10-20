# Grand Monuments: frozen at dedication, grander with age — design

**Date:** 2026-10-16
**Status:** asked for by the owner on 2026-10-16 ("a rework for Grand Monuments where a monument's building level
freezes upon dedication, and its Grandeur instead grows passively over time as the monument ages (plus through
opportunities/events)"). The owner decided the four forks in §0; every other call is this spec's, marked *(design)*,
open to review on the PR.
**Builds on:** `2026-10-13-multiple-monuments-per-state-design.md` (primary on state variables, secondaries as
`gm_monument` containers), `2026-10-12-grand-monument-opportunities-design.md` (the gift), `2026-10-12-grand-monument-trophies-design.md`
(shares, returns), `2026-09-27-grand-monument-rework-design.md` (the curve, contests).
**Replaces:** "a monument's level is its grandeur" (rework §2.1), the opportunity gift's rebuild (opportunities §3.1),
"a secondary adds no dedication-keyed effect of its own" (multiple-monuments §2, plan Global Constraints).

## Intent

Today a monument's grandeur is its building level, so the way to a grander monument is more construction, forever,
on the same building: the Arc de Triomphe of 1836 is out-grown by any column a rich country keeps adding levels to.
The owner wants a monument to be **finished** when it is dedicated, and to become grander the way real ones do:
**by standing**. An old monument is a venerable one; tearing it down throws away its years; a country that wants more
monument raises a new one, and that new one can stand **beside** the old in the same state, now that a state can hold
several.

Success looks like: a player dedicates a monument and stops building it; its grandeur visibly climbs over the decades
(about one step of the doubling curve every fifty years); the next government's choice to pull it down costs the
years as well as the stone; opportunities ask for a new monument; and a state like Paris can gather the Arc, a later
column and a returned trophy, each with its own name, dedication and politics.

**Non-goals.** No change to the curve, the step values, the dedications' effects, the names, styles, forms or
pictures, the trophy shares or consequences, the archaeology loop, or the monument policy's existing factors.
**Anti-goals** (failure even if it works): a monument that silently stops counting because it moved from the state's
variables to a container; an expansion that quietly adds grandeur to a dedicated monument; a rebuild that drops a
secondary's levels off the building; anything that walks a rebuild inside a tooltip.

## 0. The owner's decisions (2026-10-16)

| Question | Decision |
|---|---|
| Building more levels in a state whose monument is dedicated | **Starts a new monument beside it**, with its own ceremony and name. So a monument standing beside another (a *secondary*) must carry its own dedication's effects and its own contests, which today it does not |
| Ageing rate | **2% of the monument's levels a year**: it doubles in 50 years and triples in 100 |
| Opportunities | Progress counts **new levels** of fitting monuments of the dedication, not ageing. **The gift is +5 grandeur** added to the monument, with no rebuild |
| Issue #936 (a merged state loses its monument's records) | **Fold the fix in, or delegate it to a subagent; it can be deferred** (§9) |
| Anniversaries for monuments standing beside another | **Every monument is ideal; the main monument only is fine for now if needed** (§5): built after §1–§4, and the first thing cut if the branch runs long |

## 0.5 First: the review's fixes to several monuments in one state

The owner's other ask on 2026-10-16 was a review of PR #958's logic. Its fixes land first, as their own commits,
because the rework builds on the same rebuilds:

1. **Two rebuilds of one state in one effect** (Return Cultural Property bringing the Luxor Obelisk and the Dendera
   Zodiac home together; two digs finishing in one month): whether a rebuilt building reads back later in the same
   effect is unread (`scripting_best_practices.md`, "Building Lifecycle Effect Gotchas"), and the second return reads
   the first one's stale level, or no building. Every Grand Monument rebuild goes through one helper that records the
   level it built (`gm_known_level`, one day), and the level and "has a building" reads go through `gm_state_level` /
   `gm_state_has_monument`, which read the record while it stands.
2. **The AI's roll and the player's occupation offer skip a secondary** beside an undedicated primary or a Grand
   Shrine: `gm_state_tr_monthly` gates both on the primary's `gm_state_tr_takeable`. Gate on either route, and aim the
   roll at a secondary when only that route is open.
3. **A rebuilt undedicated primary takes its siblings' dedication** (the engine's copy), because only a dedicated one
   records the method to put back. Record `flag:undedicated` too, put back by the same restore.
4. **A return during a pending ceremony** records the copy as the method to put back; skip it while the ceremony asks,
   and let the ceremony's answer clear `gm_restore_pm`.
5. **Our Monuments' primary row shows the whole building's level** as its grandeur.
6. **`gm_state_tr_rebuild_from_moving`'s default level ignores secondaries still listed** (a building lost before the
   pass promotes one).
7. **A change of owner leaves the Our Monuments lists stale** for up to a month: the pass runs from
   `gm_state_changed_hands` when secondaries stand.

## 1. Grandeur = levels + age

| Term | Primary (state variables) | Secondary or trophy (container) |
|---|---|---|
| **Levels** — what was built; frozen once dedicated | `gm_state_primary_levels`: the building's level less every secondary's levels, at least 1 (today's `gm_state_primary_grandeur`) | `gm_tr_levels` (unchanged) |
| **Frozen levels** — the record of what was dedicated | `gm_levels`, written at dedication | not needed: nothing builds on a container |
| **Age grandeur** — what years, events and gifts added | `gm_age` | `gm_tr_age` |
| **Grandeur** — what every effect reads | `gm_state_primary_grandeur` = levels + `gm_age` | `gm_mon_grandeur` = `gm_tr_levels` + `gm_tr_age` |

- The state's whole, `gm_state_grandeur`, becomes the primary's grandeur plus every secondary's: tourism and the card
  read it. **It is no longer the building's level.** The building's level gets its own value, `gm_state_level`, and
  every rebuild reads that (`gm_state_tr_add_levels`, `gm_state_tr_shrink_by`, `gm_state_tr_remove_piece`,
  `gm_state_promote_secondary`, `gm_state_rededicate`). Each of today's ~45 readers of `gm_state_grandeur` and
  ~27 of `gm_state_primary_grandeur` is classified in the plan as *grandeur* (effects, sums, displays, frame tier,
  opportunity checks that mean stature) or *levels* (rebuild heights, trophy shares, Rededicate's cost, infamy, the
  ceremony's level gate). A miss rebuilds at the wrong height, so the plan lists every one.
- `gm_state_secondary_levels` (Σ `gm_tr_levels`) is for level arithmetic; `gm_state_secondary_grandeur` becomes
  Σ `gm_mon_grandeur`.
- **Old saves:** no `gm_age` reads 0, so every monument starts the update at exactly today's grandeur. A dedicated
  primary with no `gm_levels` has it written at the next refresh from its levels then, so loading never reads as
  building beside *(design)*; but only once its building is not under construction, so levels a player queued before
  the update join the old monument, once, instead of founding a surprise new one beside it.
- Five decimals: a 1-level monument ages 1 × 2 ÷ 1200 = 0.00167 a month, well inside the engine's 1e-5.

## 2. Ageing

- **Rate:** each month a monument that ages adds levels × 0.02 ÷ 12 to its age grandeur (owner). Written
  `multiply = 2 divide = 1200`: no six-decimal literal.
- **What ages** *(design)*: a dedicated monument (`gm_seen`, not `gm_restore_pm`, not `gm_ceremony_pending`) that is
  not contested. **Heritage ages** (a preserved monument is still venerated). **Undedicated never ages**: it is still
  being built. **Mothballed halves the rate**; no other policy changes it. **A trophy abroad does not age** (it keeps
  the age it was taken with; coming home resumes it), so bringing one home is worth more than holding it.
- **Where:** the primary in `gm_state_monthly`, before it computes the month's steps, so the month's local effects see
  the new grandeur. Secondaries in the monthly pass (`gm_monument_monthly`), for every container in `gm_monuments`.
- **1836 landmarks** *(design)*: start at age 0. Their seeded levels already encode their stature; they age from the
  start like everything else.

| Monument (levels) | 1836 | +25 years | +50 years | +100 years | +164 years |
|---|---|---|---|---|---|
| 5 | 5 (1.0 step) | 7.5 (1.2) | 10 (1.5) | 15 (2.0) | 21 (2.3) |
| 10 | 10 (1.5) | 15 (2.0) | 20 (2.2) | 30 (2.8) | 43 (3.2) |
| 25 | 25 (2.5) | 37.5 (3.1) | 50 (3.4) | 75 (4.0) | 107 (4.4) |
| 50 | 50 (3.4) | 75 (4.0) | 100 (4.3) | 150 (4.9) | 214 (5.4) |

Steps on the f = 5 curve (local effects, prestige, IG approval); legitimacy and cultural pull use f = 10.
Proportional to levels, so splitting a monument still changes nothing nationally (the guide's "twenty small monuments
give the same national effects as one tall one" stays true).

## 3. The freeze, and building beside

### 3.1 Dedication finishes a monument

- At dedication (`gm_state_dedicate`) the primary's levels are recorded in `gm_levels`. After that, its levels change
  only by script: a piece carried off or rejoining, Rededicate, a promotion, a return rebuild, each of which rewrites
  `gm_levels`.
- **The freeze waits for the construction to finish** *(design, changed while planning)*: `gm_levels` is written once
  the dedicated monument's building is not under construction (`is_under_construction`, building scope, as
  `gm_com_monument_under_construction` reads it). The ceremony still asks at the first finished level, as today; the
  levels still queued then join the monument, and only levels started after its construction stopped found a new one.
  (The first draft made the ceremony wait instead, but a copy standing on a dedication while its levels build would
  then be read as dedicated, contested or recorded for weeks; switching it to Undedicated cannot be read back in the
  same effect.)
- **Amended 2026-10-18 (owner): dedicate by button.** No ceremony asks by itself for a player's monument any more. It
  stands undedicated, gaining every level built on it, until its Dedicate button opens the ceremony, which it can only
  while none of its levels are under construction ("pausing is fine, building in parallel is not"). The answer records
  `gm_levels` at once (`gm_state_dedicate`); a level queued while the ceremony asks founds beside. The AI's ceremony
  asks once nothing is queued, so the AI's monuments still finish as above. A pick in the building panel, a landmark
  and a monument dedicated before the button still freeze once their construction stops. Details:
  `docs/systems/mod_systems.md` § Grand Monuments, "Dedicate".

### 3.2 New levels on a dedicated monument found a new one

- **Detection** (`gm_state_found_beside_check`): the primary is dedicated and recorded (`gm_seen`, `gm_levels`) and
  `gm_state_primary_levels` > `gm_levels`. Read in `monument_events.1` (a level finished) and in the refresh's state
  loop (a hook the engine missed, 2026-10-07).
- **What happens** (`gm_state_demote_primary`, then `gm_state_undedicate`): the primary's records go into a new
  `gm_monument` container (every record §5 lists, levels `gm_levels`, its age), which joins the state's lists; the
  state's variables are cleared (`gm_clear_state = { KEEP_LANDMARK = no }`, the landmark goes with its container);
  the building switches to Undedicated. The state's primary is now the new monument: the levels above the old one's,
  under construction, which the ceremony, unveiling and naming treat exactly as any new monument today.
- **The grandest stands first** *(design)*: once the newcomer is settled (dedicated, `gm_seen`, unveiled and named, no
  pending flag), if a secondary's grandeur is greater than its own, the two swap (§3.3), so the Arc de Triomphe stays
  the state's monument and the new column stands beside it. This runs once per newcomer (`gm_settled`), not as
  ageing changes the order.
- **When expansion is blocked** (`can_build_government`, `can_build_private` *(design)*): while the primary is
  contested (decide first, or a level would launder the contest into a secondary), a ceremony or unveiling is pending,
  `gm_restore_pm` or `gm_gift` stands, the monument is being named, or six monuments already stand in the state
  (primary + five; returns and archaeology may exceed it, construction may not). Loc on the building's `possible`-style
  tooltip names the reason. This is UX, not correctness: §3.2's detection runs whatever the engine lets through. A
  `TE_SELF_CHECK` (§10) reads whether the gate stopped an expansion the first time it should.
- **The AI** *(design)*: `ai_value` −25 for each monument already standing in the state, so it founds new monuments
  elsewhere first; the gates above bind it as they bind a player.

### 3.3 Swap: making a secondary the state's monument

A primitive used by §3.2's "grandest stands first" and by Rededicate on a secondary (§4.3):
`gm_state_swap_primary` demotes the primary into a container (as above, but the building keeps its levels) and raises
the chosen container onto the state's variables (`gm_state_raise_secondary`: today's `gm_state_tr_rebuild_from_moving`
copies, without the rebuild), with `gm_restore_pm` set to the raised monument's dedication so the existing restore
path switches the method. No rebuild: the building's level is still the sum.

## 4. Secondaries are whole monuments

Today a secondary counts only in standing grandeur. With building beside, the old crown column a new monument
displaces must keep giving legitimacy, so a secondary carries its dedication's effects and its contests.

### 4.1 Fit

Container-scope twins of the state triggers, reading `gm_tr_dedication` and the state's owner through
`var:gm_tr_origin`: `gm_mon_is_bound`, `gm_mon_kind_regime` / `_ruler` / `_faith`, `gm_mon_message_fits` (regime by
the owner's government, ruler by `gm_tr_honoree` still ruling, faith by `gm_tr_faith`, all only while
`gm_tr_raised_by` owns it), `gm_mon_status_fits`, `gm_mon_is_contested`, `gm_mon_is_heritage`. IG stances:
`gm_mon_approved_by = { IG = … }` / `gm_mon_opposed_by`, one table, which the registry test pins to `DEDICATIONS` as it
pins the state's.

### 4.2 Effects

- **National:** every `gm_sum_*` (regime, leader and each dedication with a national effect) and every
  `gm_compute_ig` net adds each fitting secondary the country holds (`gm_monuments_held`) by its dedication, and
  subtracts each contested one from its `gm_tr_base_ig`. Standing grandeur keeps counting every secondary not
  contested (today: every secondary).
- **Local** *(design)*: each dedication's local effect counts the grandeur **of that dedication** standing in the
  state, primary and secondaries together; tourism counts all of it. So `gm_local_steps` becomes one variable per
  dedication (`gm_local_steps_<key>`), each backing its own `gm_local_<key>` multiplier and zeroed, never removed.
  (Today the primary's dedication counts the whole state, a returned civic obelisk included.)
- **Counts:** the overview's Upheld / Heritage / Undedicated / Contested counts include secondaries.

### 4.3 Contests

- `gm_check_contests` runs the same three branches over the country's secondaries (foreign shrine → heritage;
  contested or heritage that fits again → lifted; fitting no more → contested, `gm_tr_base_ig` / `_supporter_ig`
  recorded from its dedication). `gm_state_changed_hands` does the same for each secondary in the state;
  `gm_state_adopt_for_winner` moves a civil war loser's `gm_tr_raised_by` to the winner, from the global list (lists
  are not inherited; the monthly pass rebuilds them).
- **Choices on a contested secondary:** Pull Down (its levels off the building through `gm_state_tr_shrink_by`, its
  grandeur into the teardown ledger, the container destroyed), Keep as Heritage, and **Rededicate**, which swaps it in
  as the state's monument (§3.3) and then runs today's `gm_state_rededicate` on the state. Its row in Our Monuments
  and on the state card carries the buttons; the contest notice (`.16`) lists secondaries too and "decide for all"
  covers them; `gm_ai_decide_contests` decides them as it decides primaries.
- A contested **primary** blocks building beside (§3.2), so a contest is never moved into a container by
  construction. Rededicate on a secondary when the primary is also contested swaps the contest records with it.

### 4.4 Records a container carries

Today's trophy records (`gm_tr_skin`, `_form`, `_landmark`, the name records, `_honoree`, `_honoree_ig`,
`_dedication`, `_picture_code`, `_levels`, `_share`, `_origin`, `_site`) plus: `gm_tr_age`, `gm_tr_raised_by`,
`gm_tr_faith`, `gm_tr_built_by`, `gm_tr_contested` (months), `gm_tr_new_contest`, `gm_tr_heritage`,
`gm_tr_base_ig`, `gm_tr_supporter_ig`, `gm_tr_ceremony_level`, `gm_tr_inscription` if the state keeps one. A
container that becomes a trophy keeps them (they are inert abroad); one raised onto the state hands them over. An old
save's secondary with no `gm_tr_raised_by` gets its state's owner at first sight (`gm_mon_first_sight` in the monthly
pass), as `gm_state_first_sight` does for the state: a missing record would read as "does not fit".

## 5. What else changes

| Thing | Today | After |
|---|---|---|
| **Opportunity progress** | fitting grandeur of the dedication above the baseline | fitting **levels** of the dedication (primary and secondaries) above the baseline (owner): ageing never completes one; a new monument, or building beside, does |
| **Raise It / Seize It and Start Building / the AI's queue** | levels on the picked state's monument | the same queue; on a dedicated monument the levels found a new one (§3.2), whose ceremony's first option is "As the opportunity asks". `gm_com_pick_build_state` skips a state where expansion is blocked |
| **The gift** | `gm_state_gift_grandeur`: remove and rebuild 5 levels taller | **+5 age grandeur** (`gm_com_gift`) on the completing monument, the state's primary if it answers the opportunity, else its largest answering secondary *(design)*. No rebuild, so `gm_gift` → `monument_events.26` stays only to move the work out of the refresh's tooltip walk |
| **Rededicate** | rebuilt at half its levels (+ secondaries), dedicated again | the same rebuild, and its age grandeur halves too *(design)*: its grandeur halves. Cost stays 500 a **level** |
| **Pull Down** | the building goes; the largest secondary takes it | the same; its grandeur (age included) goes to the teardown ledger |
| **A piece carried off** | a share of its levels | the same share of its levels **and of its age** *(design)*; infamy still by levels |
| **A whole monument carried off** | the levels | the levels and all its age |
| **A trophy abroad** | counts for ceil(levels ÷ 2), fixed when taken | counts for ceil(grandeur ÷ 2), rewritten by the monthly pass; no ageing abroad |
| **A trophy home** | rejoins, stands beside, or is rebuilt | the same, with its age: rejoining adds it to the monument's `gm_age`, standing beside keeps it, a rebuild sets the state's `gm_age` |
| **Archaeology** | a site placed at its levels | the same; age 0 |
| **Anniversaries** (`.3`–`.10`, `.12`–`.15`) | the paid option buys a modifier; only a state's primary holds them (`gm_state_holds_anniversary`, which reads `b:building_grand_monument.level >= 3` directly) | the paid option also adds 10% of the monument's levels, at least 1, to its age grandeur (`gm_evt_grandeur`) *(design)*; its tooltip says so. The level read becomes the monument's own grandeur. **Every monument holds them** (owner: ideal), so each event picks the grandest fitting monument of its dedication across primaries and secondaries and names a secondary by its container name (`gm_trophy_name`); if the branch runs long, primaries only (owner: fine for now). **Built: every monument** (the dispatcher and each event ask `gm_country_holds_anniversary`; .12–.15 have a `_beside` text) |
| **Vanity backlash** | each finished level in hard times | unchanged: every finished level is still construction |
| **Upkeep, staff** | by the building's level | unchanged (the building's level is still the sum of levels) |
| **Rename, Name It** | the primary | the primary only *(design)*: a secondary keeps its name |

## 6. Panels

- **State card:** Grandeur shows grandeur (levels + age), its hover splits it: "N from its N levels, M from its
  years"; for the whole state when secondaries stand. The local-effect line is the primary's dedication's (§4.2). Each
  Also Standing Here row gains its status, dedication, grandeur, and on a contested one the three choices; Carry It
  Off stays. A line under the primary's details while building beside is possible: "Build here to raise a new monument
  beside it" (or the blocked reason).
- **Our Monuments:** secondary rows get the same status / dedication / grandeur / contest buttons as primary rows.
- **How Grand Monuments Work:** grandeur and age, the freeze, building beside.
- **Ceremony (`.2`):** its description says dedicating finishes the monument.

## 7. Player guide

`02-timeline.md` § Grand monuments: "A monument's level is its grandeur, and it has no cap" (→ levels + age, frozen
at dedication); the opening paragraph's "Each level costs 1,000 construction" (still true, for building); Several
monuments in one state (building beside, secondaries' own dedications and contests, the grandest stands first,
"its dedication gives nothing of its own" is gone, "Rededicate applies to the first monument only" is gone); Monument
dedications ("the ceremony asks again at its next level" → after construction; dedicating finishes it); Monument
opportunities ("Grandeur you add … whether you raise an old monument or build a new one" → levels, new monuments;
the Completed row's "rebuilt 5 levels taller" → +5 grandeur; "reaches level 200 at most" goes); Contested monuments
(Rededicate: half its grandeur; secondaries' choices); Monument trophies ("A quarter of its levels … rebuilt smaller",
"counts for half the levels carried off" → half its grandeur); anniversaries if the guide lists them. `08-states.md`'s
card row. `17-reference.md` if it repeats any of these.

## 8. Engine facts this rests on

| Fact | Status | If wrong |
|---|---|---|
| `can_build_government` / `can_build_private` false blocks *expanding* an existing building | precedent: the fossil construction ban (`extra_buildings.txt`), unverified for expansion | Self-check (§10); expansion goes through and §3.2 founds a monument beside, which is the owner's chosen behaviour anyway, minus the blocked cases |
| `create_building` (the rebuild ladder) ignores those gates | believed (script effect) | Self-check: the first rebuild in a dedicated state logs whether the level came back; fallback: lift the gate for one day around a rebuild (`gm_rebuilding` already marks it) |
| `is_under_construction` on a building is true while any of its levels are queued | used by Raise It since 2026-10-12 | the ceremony asks at the first level, as today |

## 9. Issue #936, a merged state (owner: fold in or delegate; deferrable)

A record of every primary kept by **region**, so a merge cannot lose it: each month the pass writes the primary's
records into a shadow container (`gm_shadow`, global `gm_shadows`, the same copy §3.2 demotes with). After a merge, a
state in the region whose levels exceed its primary's `gm_levels` + secondaries adopts an orphaned shadow (its state
gone, or no longer holding it) as a secondary instead of founding a new monument (§3.2 checks shadows first); a
building with no records adopts it as its primary. Engine behaviour unread (which part survives, whether buildings
merge their levels), so it ships behind a `TE_SELF_CHECK` and the probe in the issue goes on the play-test list. Built
last; a subagent may take it once §1–§5 are on the branch.

**Built (2026-10-16, subagent):** `gm_shadow_monthly` writes the shadows (`gm_state_write_shadow`, refreshed in place,
set-or-remove); `gm_clear_state` and a whole taking drop a state's shadow at once (no stale shadow beside its demoted
container). An orphan's region goes to the hidden `monument_events.31`; `.1`, `.29` and a change of owner adopt first
wherever `gm_state_merge_pending` holds, and the refresh only asks `.29`. `gm_state_adopt_orphans` waits a day for a
rebuild in the region, repairs the orphaned secondaries to the building that holds their levels, then raises each
orphan (landmarks first) onto the building no record describes that holds the most unaccounted levels, stands the rest beside a recorded
monument with unaccounted levels (no more levels than it holds unaccounted; a primary still being built accounts for its
ceremony level), and drops the rest. Self-check `monument_merge_kept`. Undedicated primaries have no shadow.

## 10. Self-checks and the play-test list

`docs/testing/grand-monuments-ageing-playtest.md`, with two `TE_SELF_CHECK` lines (pattern: `gm_monument_self_check`):
`monument_expansion_gated` (the first month a player's contested or six-monument state is in reach of the gate, whether
`can_build_government` reads false there) and `monument_rebuild_ungated` (after the first rebuild in a dedicated state,
whether the level read back equals what was asked). In-game checks: ageing visible on the card after a year; a
ceremony that waits for ten queued levels; building beside in Paris; the grandest swapping back; a contested secondary's
three choices; a returned piece bringing its age; the gift as +5.

## 11. Left to the builder

Variable and helper names beyond those above; the exact loc; the card's layout within the house style
(`docs/guides/gui_style_guide.md`); test structure. Every new state/container write that backs a multiplier is zeroed,
never removed; every new effect a tooltip can walk runs under a click marker or in a hidden event, as the trophies do.
