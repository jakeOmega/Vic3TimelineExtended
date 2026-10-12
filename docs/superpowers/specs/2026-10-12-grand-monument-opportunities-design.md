# Grand Monuments: commissions become opportunities — design

**Date:** 2026-10-12
**Status:** asked for by the owner on 2026-10-12 ("rework the commission system into an opportunity system"); the
calls below marked *(design)* are this spec's, open to the owner's review on the PR.
**Builds on:** `2026-10-05-grand-monuments-v2-design.md` §2 (commissions, "v2" below) and §3 (names).
**Replaces:** v2 §2.2's sources table, §2.3's life cycle, §2.4's rewards and costs, §2.5's petition pacing.

## Context

v2 made the commission the way an interest group asks for a monument: an offer you accept or refuse, a window of 60 or
120 months, approval and legitimacy if you meet it, and resentment if you refuse (−5) or miss it (−15). Two things read
badly in play:

- **The downside makes it a chore.** A commission is a bill that arrives whether you want a monument or not. Refusing
  costs approval, so the event is a tax on not building.
- **Some of them come from nowhere.** The petition, about once a decade, is a dice roll; nothing in the game prompts it.

The owner's brief (2026-10-12): remove the downsides of not doing them; tie every one, visibly, to something that
happens in the game ("the coronation of a new monarch gives an Opportunity for a To the Crown or a Leader monument;
becoming a great power gives a To the Nation Opportunity"); completing one gives **free grandeur** (the monument is
destroyed and rebuilt bigger), the **IG approval** a commission gives today, and a **flavourful bonus for a time**
(loyalists, authority, assimilation, …).

## Decisions

| Question | Decision |
|---|---|
| Name | **Opportunity** everywhere a player reads it: the event, the journal entry section, notices, the guide. Script keeps v2's `gm_com_*` names and files *(design)*: saves carry an open commission as these variables, and renaming them would strand it |
| Downsides | **None.** Letting one pass, running out of time and a lapse all cost nothing. Refusing an offer, v2's −5, and missing one, v2's −15, are gone, and so are the 60-month petition cooldown and Ask for More Time (which halved the reward to dodge a miss that no longer costs anything) |
| What prompts them | **Only moments a player can see** (§1). The petition roll is gone |
| Rewards | (1) **The monument's gift:** the monument that completed it is rebuilt **5 levels taller**, once, keeping its dedication, name, style and records (§3.1). (2) **Approval:** the asking group's ledger +15, as now (about +2 approval, fading). (3) **A boon:** a national modifier for **10 years**, one per moment (§3.2). v2's *A Promise Kept* legitimacy goes; the boon replaces it |
| One at a time | **Kept.** One opportunity open or on offer at a time; a moment that comes while one is open passes. A player frees the slot with **Let It Pass**, in the offer or on the open opportunity's panel |
| Who gets them | **Every rank** (owner, 2026-10-12, reversing v2's great-and-major-power gate now that nothing is lost by passing). A great power has 60 months, a major power 120, any other 180. **The AI below major power lets them pass**: v2's reason (five levels are 5,000 construction) still holds for its construction queue |
| Target | 5 grandeur, as v2 |
| AI | Seizes one as a great or major power when not at war, not in hard times, with under a year of government construction queued and not in debt (v2's test), and then queues the five levels itself; otherwise lets it pass |

## 1. The moments

| Source (`gm_com_source`) | Moment | Seen by | Asks for | Who asks | Where | Named for / form | Boon (10 years) |
|---|---|---|---|---|---|---|---|
| `reign` | **A New Reign**: a new ruler takes power | the world pass: the ruler differs from last month's | To the Crown when crowned, else To the Leader under Autocracy or a Single-Party State; neither (an elected president of a democracy, say), no opportunity: one each election would be noise | Landowners (Crown); the ruler's own group (Leader), else the strongest in government | anywhere | the ruler; column (Crown), statue (Leader) | **The New Reign**: +10% authority |
| `regime` | **A New Order**: a crown, republic or revolution with no fitting monument | the world pass, as v2 | that regime | its approving group (v2) | anywhere | the year; column | **The New Order Proclaimed**: +25% loyalists from legitimacy |
| `great_power` | **Among the Great Powers**: the country becomes a great power for the first time | the world pass, once per game | To the Nation | Petty Bourgeoisie, else the strongest in government | the capital | what it honours ("the Column of the Nation"); column | **A Seat Among the Powers**: +10% influence |
| `victory` | **Victory** in a war of a year or more, as war leader | `on_won_war`, as v2 | War Memorial | Armed Forces | anywhere | the victory; arch | **Victory Parade**: +10% prestige |
| `defeat` | **Defeat** in such a war | `on_lost_war`, as v2 | War Memorial | Armed Forces, or the strongest outside government | anywhere | the fallen; hall | **Lest We Forget**: −25% radicals from legitimacy |
| `centenary` | **Centenary**: the 100th or 200th year since the founding | the world pass, as v2 | To the Nation | Petty Bourgeoisie, else the strongest in government | the capital | the centenary; column | **A Century of Nationhood**: +25% assimilation |
| `ruler_death` | **A Reign Remembered**: a ruler of 15 years or more dies | `on_character_death`, as v2 | To the Nation | the late ruler's group | the capital | the late ruler; mausoleum | **A Nation in Mourning**: +5 legitimacy |
| `space` | **A space race first**: into orbit, onto the Moon, a lunar colony, onto Mars, an interstellar probe (owner, 2026-10-12: "what about Mars") | the world pass, as v2, once each | To the Nation | Intelligentsia | the capital | the achievement; obelisk | **The Space Age**: +10% innovation |
| `faith` | **A New Faith**: the state religion changes | the world pass | Grand Shrine | Devout | anywhere | what it honours ("… of the Faith"); the faith's building | **A Faith Proclaimed**: +25% conversion |
| `tech_artistic` | **Romanticism** researched | the world pass, once per game | Grand Opera House | Intelligentsia | anywhere | the city | **A Golden Age of the Arts**: +10% Creative Industry throughput |
| `tech_scientific` | **Empiricism** researched | the world pass, once per game | Grand Observatory | Intelligentsia | anywhere | the city | **An Age of Inquiry**: +10% technology spread |
| `tech_industrial` | **Marketing Research** researched | the world pass, once per game | Great Exhibition Hall | Industrialists | anywhere | the city | **The Great Exhibition**: +5% Manufacturing Industries throughput |
| `tech_athletic` | **Television Broadcasting** researched | the world pass, once per game | Grand Stadium | Trade Unions | anywhere | the city | **A Sporting Nation**: −5% mortality |
| `tech_naturalist` | **The Environmental Movement** researched | the world pass, once per game | Botanical Gardens | Rural Folk | anywhere | the city | **The Green Movement**: −25% pollution's harm to health |

- **Every dedication has a moment.** Crown, Leader, Republic, Revolution, Nation, War Memorial and Shrine from politics,
  war and faith; the five civic-progress buildings from the technology that makes each possible, Gardens from the
  later Environmental Movement *(design: Romanticism already brings the Opera House)*.
- **Priority** on a month when several are seen *(design)*: the war and death on-actions offer at once; the world
  pass then tries A New Order, A New Reign, Among the Great Powers, A New Faith, the space firsts, the centenary and
  the technologies, in that order. The first takes the slot; the rest pass. A New Reign is seen by the world pass, not
  `on_new_ruler`, so a long-reigning ruler's death (`on_character_death`, at once) takes the slot first and the
  mausoleum wins over the coronation, every time.
- **First sight** *(design)*: the first time the world pass sees a country (a new game, a save from before this
  change, a released country), it records what it already has — great power status, the five technologies, the space
  firsts won, the state religion — and offers nothing. So 1836's great powers and everyone's Empiricism bring no opportunity, and an old
  save does not flood.
- **Civil war:** no offer to a side in one (v2), and neither side records a new faith, as v2 already keeps it from
  recording a regime.

## 2. Life cycle

- **Offered.** Event `monument_events.21`, titled for the moment ("An Opportunity: A New Reign"), says what happened,
  who asks, what for, where, and what completing it gives. Options: **Seize the Opportunity** (the default; it opens)
  and **Let It Pass** (no cost). The same event for the AI.
- **Open.** The journal entry's **Opportunity** section: the moment, who asks for what, the name it would take, a bar
  of grandeur added against the target, the months left, what it gives, and **Let It Pass** (closes it, no cost).
- **Seized** when progress reaches the target: the three rewards (§3), a notice.
- **Passes** when time runs out, or **lapses** when it can no longer be met (its state lost, its dedication no longer
  raisable): both close it with a notice and cost nothing.
- Progress counts as v2 §2.3: grandeur added since it opened to fitting monuments of its dedication (in its state, if
  it names one), floored at 0. A counted monument that drops out lowers the baseline.

## 3. Rewards

### 3.1 The monument's gift: free grandeur

The monument that completed it — the one whose level or dedication last counted (`gm_com_last_state`), else the
tallest counting one — is rebuilt **5 levels taller** (`gm_com_gift`), at most level 200, the rebuild ladder's reach
(`te_construction_market_build_specified_level`). At 200 already, it gets no gift.

**How.** No effect adds levels to a building the state already has predictably (`scripting_best_practices.md`,
"Building Lifecycle Effect Gotchas"), so the monument is removed and built again at the higher level, as Rededicate
does — but **nothing else about it changes**: the state's records (its dedication's raiser, honoree, faith, style,
form, name, picture, `gm_seen`) are kept, and its dedication is put back.

- **A hidden state event does it** (`monument_events.26`), not the fulfilment itself. Fulfilment runs inside
  `gm_country_refresh`, which the policy buttons' tooltips walk without writing (v2's `gm_com_drop` lesson); a
  `set_variable` read back in that walk logs errors, and a removal and rebuild has no business in a tooltip.
  Fulfilment only marks the state (`gm_gift`) and triggers the event.
- **Its dedication.** A rebuilt building starts on the production method most of its owner's monuments use, or
  Undedicated (`grand_monument_pms.txt`, "the engine's copy"). The state records the dedication before the rebuild
  (`gm_restore_pm`, a flag naming it) and `gm_state_restore_dedication` activates it: in the event, again in every
  refresh and in the state's monthly pulse, until it reads back, when the flag goes. Whether a `create_building`
  result is visible within the same effect is unknown, so each attempt is guarded by `has_building`, and only the
  refresh's later read removes the flag.
- **While the flag stands** nothing judges the monument by its method: no ceremony starts
  (`gm_state_start_ceremony`), no contest check reads it (`gm_check_contests`) and its picture is not recomputed. A
  copy that read as another dedication would otherwise be contested, and one that read as Undedicated would open the
  ceremony.
- **Vanity backlash** skips the rebuild's own `on_building_built`, as Rededicate's does (`gm_rebuilding`, one day).

### 3.2 The boon

A national modifier on the journal entry, as every other national effect (`gm_apply_national_modifiers`), for 120
months (`gm_boon_months`). Each moment has its own (§1's last column), `gm_boon_<source>`; a second of the same kind
restarts its clock. Kept as a country variable counting the months down (`gm_boon_<source>`), so a civil war's winner
keeps it (variables are inherited, modifiers are not) and the panel can show the months left.

- **The panel:** National Effects gains **Opportunities Seized**, a row per boon in force with its months left; its
  tooltip names the effect.
- **The entry and the pulse stay** while a boon runs (`gm_boons_idle` joins `gm_ledgers_idle`), so demolishing the
  last monument doesn't drop a boon.

### 3.3 Approval

The asking group's ledger +15 grandeur (about +2 approval, fading ×0.97 a month), as v2.

## 4. Save compatibility

- An open commission continues as an opportunity. One from a petition has no boon (no `gm_boon_petition`); it still
  gives the gift and approval.
- The promise ledger and *A Promise Kept* are retired: the static modifier stays defined, and its `remove_modifier`
  stays in `gm_remove_national_modifiers`, so a save carrying it sheds it on the first refresh; first sight removes
  the ledger variable.
- `gm_com_extended` and `gm_com_cooldown` are cleared by `gm_com_clear` and first sight.

## 5. Tests, docs, in-game checks

- `test_grand_monument_registry.py`: `COMMISSION_SOURCES` gains the new rows and a boon column; `BOONS` pins each boon
  to its static modifier, its loc and its number; the rewards test pins the gift, the approval and no cost on any
  close; the first-sight and priority order are pinned.
- `te_debug_monuments.2`: an option per source, seize now (with the gift), pass, lapse, print.
- Docs: `mod_systems.md` § Grand Monuments; the player guide's *Monument opportunities* (replacing *Monument
  commissions*), rebuilt PDF.
- **In-game checklist:**
  1. Each moment offers once, at the right time; first sight offers nothing in 1836 or in an old save.
  2. Seizing and completing one rebuilds the monument 5 levels taller, keeping its dedication, name and picture; no
     ceremony opens, no contest; the dedication reads back within a month.
  3. A monument with levels still queued when the gift lands: what happens to the queue (as Rededicate).
  4. The boon shows on the journal entry with its months, and ends after 10 years.
  5. Let It Pass, a run-out and a lapse cost nothing.

## 6. Usability (follow-up, owner 2026-10-12)

The first build showed the offer and the rewards clearly but left the doing to the player: queue five levels by hand,
then pick the right dedication at the ceremony, with the target state in a tooltip and a progress bar that stood at 0
while construction ran. The owner approved all five fixes below.

1. **Raise It** on the Opportunity section queues the levels still missing (target less progress) as government
   construction, where the AI's picker would put them (the opportunity's state; the tallest fitting monument of its
   dedication; an undedicated one; the capital without a monument; the most populous incorporated state without one).
   Its tooltip names the state, the levels and the construction. Script can't count queued levels, so the button is
   greyed while any Grand Monument of ours `is_under_construction`, and for a week after a press. The queue runs in a
   hidden event (`monument_events.27`): the button's tooltip walks its effect without writing, and the queue sets a
   variable and reads it back.
2. **Seize It and Start Building**, a third offer option for players, seizes and queues at once.
3. **The ceremony** lists "As the opportunity asks: [dedication]" first when the monument can answer the open
   opportunity, and makes it the default then. A default whose trigger fails doesn't fall back, so the default moves
   between it and a copy of "Leave it undedicated" by complementary triggers.
4. **Visibility:** a Where line in the section, a line while levels are under construction ("levels count once they
   are finished"), and "Counts toward the opportunity" on each counting monument's row and state card.
5. **Reminders:** a notice at 12 months left; completion is an event (`monument_events.28`) naming the monument, its
   gift and the boon, in place of the toast.

In-game checks: `start_building_construction` from a player's button (only the AI has run it); `is_under_construction`
true for a monument with an expansion queued as well as a new one; the ceremony's default moving between the two
options.

