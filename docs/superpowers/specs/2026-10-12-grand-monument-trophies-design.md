# Grand Monuments v2 phase 5: trophies — design

**Date:** 2026-10-12
**Status:** approved in conversation by the owner on 2026-10-12 (the decisions below); the calls marked *(design)* are
this spec's, open to review on the PR.
**Builds on:** `2026-10-05-grand-monuments-v2-design.md` (§6, "v2" below) and the landmarks spec's Appendix A
(`2026-10-12-grand-monuments-landmarks-design.md`).
**Replaces:** v2 §6 in full.
**Extended by:** `2026-10-12-grand-monument-loot-and-1836-trophies-design.md` (nineteen landmarks to loot, and the
ten trophies already abroad in 1836).

## Context

v2 let a conqueror carry a monument home in the five years after a conquest. Two things were wrong with that:

- **By then the conqueror already owns it.** Carrying it home mostly halved a monument that already counted for it.
- **It would almost never happen.** States with monuments rarely change hands.

The taking happened during **occupation**. Napoleon's troops took the Quadriga from Berlin in December 1806, seven
months before the peace of Tilsit. The horses of San Marco left Venice in 1797, and the Beijing observatory's
instruments were taken in 1900. So occupation is the main route here. A country's own unincorporated states (recent
conquests and colonies) are the second, and a treaty article, which a war goal can enforce, is the third.

## Decisions (owner, 2026-10-12)

| Question | Decision |
|---|---|
| Main route | **Occupation.** A country at war with a state's owner that holds half or more of its provinces can carry off its monument |
| The AI and players | **The AI may loot players' monuments.** The player gets a notice |
| AI looting odds | Higher where the government's interest groups approve of Total War or of a narrow citizenship law (law stances, not one hard-coded group), **higher for unrecognized countries**, higher for a tall monument, much lower once UNESCO is in force |
| Own colonies | **Unincorporated states only, and only monuments the country didn't raise.** Replaces v2's 60-month window |
| War goal | **Surrender a Monument**, a treaty article that can be enforced, in this PR ("ideally yes, but can be later") |
| UN topic | **A follow-up PR** |
| Shares | 100% (objects), 25% (pieces), 10% (tokens), by form (Appendix A) |
| Value abroad | **Half**, rounded up. It goes home whole |
| Infamy | 2, plus 1 per 5 levels taken, at most 8; doubled once UNESCO is in force |
| Relations | −30 when taken, +40 when returned |
| War support | +10 for the victim, in the war it is fighting with the taker |
| Homecoming | +5 legitimacy for 10 years |

## Engine facts this rests on

- **`controller`** is a scope link from a province or a state to the country controlling it (`event_targets.log`). The
  base game uses neither form in script, so what a state's controller returns under partial occupation is unread.
  Occupation is therefore read from the provinces: `any_province = { percent >= 0.5 controller = X }` (state scope).
  The province link reads the occupier, and half the provinces is the rule the base game uses for war-goal control
  since 1.13.9. The occupier is found as the controller of a province the owner doesn't control (`random_province`).
  *(Corrected 2026-10-16: the engine registers the province iterators from a province, so neither ran from a state and
  no occupier was ever found. A script value's `every_province` reads the share instead, and the occupier is found among
  the owner's enemies: `scripting_best_practices.md`, "Who occupies a state".)*
- **`on_state_owner_change` gives only the state** (`scripting_best_practices.md`). The former owner is stamped on the
  state monthly (`gm_holder`) and compared on the change, as the Strategic Reserve hub does.
- **Conquered states restart incorporation** (`vanilla_states_reference.md` §2), except a primary-culture homeland
  taken on a claim. So "unincorporated" covers a recent conquest.
- **Script containers** hold a trophy: no parent, so one outlives every country; a global list indexes them; timed
  variables on a container never expire (`container_timed_variable_audit`). GUI rows read a container through a
  country or state variable list (`Scope.GetScriptContainer`, the covert operations and homeland project rows), and
  `type = container` customizable localization prints from `ScriptContainer.GetCustom`.
- **Event text can't reach a container.** A taking's notices name the monument through the state, whose records the
  taking leaves in place until that state's next monthly pulse clears them (`gm_carried_off`).
- **No effect removes levels.** A piece is taken by the gift's machinery run backwards: the state records its
  dedication (`gm_restore_pm`), the building is removed and rebuilt smaller through the ladder, and the dedication is
  put back (`gm_state_restore_dedication`).
- **Treaty articles.** A directed article with `can_be_enforced` is demandable through the base game's Enforce Treaty
  Article war goal, by its own `wargoal` block. Directed articles may take no inputs (`guarantee_independence`,
  `take_on_debt`) or a state (`free_port_concession`). The treaty designer runs `on_entry_into_force` every frame with
  `scope:article_options` unbound, so every use is guarded (`scripting_best_practices.md` § treaty preview pass).
- **`law_stance`** (interest group scope) reads a group's stance on a law whether or not it is enacted.
  `law_total_war` is the mod's (`lawgroup_rules_of_war`); `law_ethnostate` and `law_national_supremacy` are the base
  game's narrowest citizenship laws.

## 1. What can be taken

A **dedicated** monument, not a Grand Shrine (v1: a conquered shrine becomes heritage), not while its dedication is
being put back (`gm_restore_pm`) or a ceremony is pending, and not within ten years of a piece being taken from it
(`gm_tr_cooldown`, a timed state variable) *(design: without it an occupier could strip a gate a quarter at a time,
month after month)*.

How much goes depends on its form:

| Share | Forms |
|---|---|
| **Object: all of it** (the monument is gone) | column, obelisk, statue, stele, pillar, high cross, rune stone, menorah, sun stone, stela |
| **Piece: 25% of its levels**, at least 1 | arch, gate, tower, bell tower, round tower, rock-cut monument |
| **Token: 10%**, at least 1 | hall, hall of fame, pantheon, forum, stoa, court, colonnade, mausoleum, pyramid, pagoda, memorial church, rock-hewn church, hill shrine, sacred oak, memorial (retired), and the five civic-progress buildings |

A piece or token that would take every level takes the whole monument. Levels taken are rounded up.

- **The trophy counts for half abroad** (rounded up): standing grandeur and the Armed Forces' approval.
- **It goes home whole.** All the levels taken are rebuilt when it returns.
- **A landmark's trophy keeps the landmark's name.** A piece is named for what it is ("the Reliefs of the Arc de
  Triomphe", "the Instruments of the Jantar Mantar"); the Brandenburg Gate's is the Quadriga.

## 2. When

### 2.1 Occupation

A state with a monument can be carried off by a country that (`gm_state_can_be_looted_by`):

- is at war with the state's owner, and is not its civil-war twin (both sides carry `te_cw_role`);
- controls half or more of the state's provinces.

The same holds for **trophies on display** in an occupied state: each can be carried off, and one whose origin the
taker owns goes straight home (§5).

- **Players:** a **Carry It Off** button on the state view's monument card, and a notice the first time a player's
  armies hold such a state in this occupation (`monument_trophy_events.1`: Carry It Off, or Leave It Standing, the
  default). A state with trophies on display has its own card with a button per trophy.
- **The AI:** a roll each month, from the state's own pulse (§7).

### 2.2 Own unincorporated states

A monument the country didn't raise (`gm_built_by`, §4), in a state it hasn't incorporated. A recent conquest restarts
incorporation, so this covers conquests as well as colonies. Once incorporated, it stays. Players use the same button,
on the state card or the monument's row in Our Monuments.

### 2.3 Surrender a Monument (treaty, war goal)

A directed article: the giver hands the monument in a named state (`required_inputs = { state }`) to the receiver as a
trophy. `can_be_enforced`, so a war can demand it; `hostile`. The Treaty of Lahore (1849) made the Punjab surrender the
Koh-i-Noor. Not giftable *(design: a gift would carry the taking's relations hit; gifts stay out of scope, as in v2)*.

## 3. Consequences

| | Occupation | Own unincorporated state | Surrender a Monument |
|---|---|---|---|
| **Taker** | infamy (2 + 1 per 5 levels, at most 8; ×2 under UNESCO); relations −30 with the owner | radicals among 10% of the state's people; no infamy | relations −30 with the giver |
| **Victim** | +10 war support in each war it fights with the taker; a notice | relations −30 if the former owner (`gm_taken_from`) still exists; the row shows under its Held Abroad | — |

While a trophy is held: the holder counts it in standing grandeur (prestige, cultural pull) and the Armed Forces
approve of it (`gm_tr_ig_share_<ig>`: Armed Forces only). The victim has no ongoing penalty; the loss is the cost.

When it goes back: the receiver gets **The Homecoming** (`gm_boon_homecoming`, +5 legitimacy, 120 months), unless
the receiver carried it off itself (`gm_tr_taken_by`, added 2026-10-12); a holder that
returns it to another country gets relations +40 with it. The Armed Forces' approval goes with the trophy.

## 4. Records

**On the state** (beside v1's): `gm_built_by` (the country that first saw it dedicated: written at first sight and by a
ceremony, kept by the gift and a taken piece, cleared by `gm_clear_state`; an old save's monument takes its current
owner), `gm_holder` (its owner last month), `gm_taken_from` (the owner before a change of hands, while it differs),
`gm_tr_cooldown` (ten years after a piece), `gm_carried_off` (until the state pulse clears a monument carried off
whole), `gm_tr_offered_to` (the occupier a player's notice went to).

**The trophy**: a script container tagged `gm_trophy`, no parent, listed in the global list `gm_trophies`:

| Variable | What |
|---|---|
| `gm_tr_origin_region`, `gm_tr_origin` | the state region and state it came from (the state re-found in the region if it stops existing) |
| `gm_tr_site_region`, `gm_tr_site` | the taker's capital at the time: where it stands |
| `gm_tr_levels`, `gm_tr_grandeur` | the levels taken; half of them, rounded up, which it counts for abroad |
| `gm_tr_share` | flag: whole, piece or token |
| `gm_tr_dedication`, `gm_tr_skin`, `gm_tr_form`, `gm_tr_landmark` | its look and what it honoured |
| `gm_tr_picture_code` | its monument's picture, from its look (added 2026-10-13, §6) |
| `gm_tr_namesake`, `gm_tr_name_year`, `gm_tr_name_char`, `gm_tr_name_occasion`, `gm_tr_name_enemy_cap`, `gm_tr_name` | its name |
| `gm_tr_honoree`, `gm_tr_honoree_ig` | To the Leader's records, put back on return |
| `gm_tr_year` | the year it was taken |
| `gm_tr_home_notified` | the holder already told it can bring it home |
| `gm_tr_taken_by` | the country that carried it off (added 2026-10-12; a trophy from before then has none) |

**Holder and claimant** are read, not stored: the holder is the site's owner, the claimant the origin's owner. So
annexation, a civil war or the capture of the site moves a trophy with no special case, and a formable inherits its
states' claims.

**The monthly pass** (`gm_trophy_monthly`, from `on_monthly_pulse`, no root) walks the global list once. It repairs a
vanished origin or site state, and writes every holder's `gm_trophies_held` list and `gm_tr_held_grandeur`, every
claimant's `gm_trophies_abroad` list and every site state's `gm_trophies_here` list, clearing last month's first (the
countries and states it wrote are kept in two global lists). Lists are rebuilt each month, so a civil war's winner,
who inherits no lists, has its rows back within a month. A taking or return reruns the pass at once.

## 5. Ways home

| Way | How |
|---|---|
| **Return It** | the holder's button on the trophy row, while another country owns its origin |
| **Bring It Home** | the same button, while the holder owns its origin (it took its own back, or conquered the site) |
| **Retake it** | occupy the site and carry it off: a trophy whose origin the taker owns goes straight home |
| **Return Cultural Property** | a directed treaty article: the giver returns every trophy whose origin the receiver owns. `can_be_enforced` (the war goal contests the holder's capital, where trophies stand), `giftable` |
| **UN** | a follow-up PR |

**Rebuilt at home** (`gm_trophy_rebuild_home`, container scope): in the receiver's state in the origin region.

- **No monument stands there:** it is built at the trophy's levels (at most 200, the ladder's reach) with the
  trophy's records: skin, form, landmark, name, honoree, `gm_built_by` and, for a bound dedication, `gm_raised_by` = the
  receiver. `gm_seen` and `gm_ceremony_level` are set, so it is never read as a copy, and its dedication is put back
  through `gm_restore_pm`.
- **A monument stands there:** the levels are added to it through the gift's rebuild, keeping its own records and
  dedication. The Quadriga goes back on the Gate.

The receiver gets The Homecoming; a holder returning to another country gets relations +40.

## 6. Interface

- **Trophies** (journal entry, open), while the country holds one or The Homecoming runs: what they count for, The
  Homecoming's months left, and a row per trophy: its name, where it came from and when, the levels it carries and
  what it counts for here, who claims it, and Return It or Bring It Home.
- **The picture** (added 2026-10-13, owner's request; it replaced a statue icon): every trophy row, in Trophies, Held
  Abroad and Trophies on Display, shows the picture of the monument the trophy was taken from, at 96 px as in Our
  Monuments, a piece's too. `gm_tr_update_picture` runs the monuments' own table (`gm_picture_from_look`, split out
  of `gm_state_update_picture`, then `gm_state_picture_landmarks`) on the trophy's look, lent under the state's
  variable names and taken back at once, and stores `gm_tr_picture_code`. It runs when the trophy is made or seeded
  and from the monthly pass, so a landmark whose own picture is drawn later, or a trophy from an older save, catches
  up within a month. The `gm_tr_picture` type holds `gm_picture`'s icons, read from the container, without the
  grandeur frame.
- **The trophy's own picture** (added 2026-10-16, owner's request): what was carried off, on display in a museum
  room (the marbles, the Quadriga, the Luxor obelisk in a glass-roofed court), drawn over the monument's picture in
  the three trophy rows by `gm_tr_trophy_picture`. Each landmark with one has a code, `TROPHY_CODE_BASE` (2,000,000) +
  its `LANDMARKS` row (`TROPHY_PICTURES` in the registry test), and `gm_tr_update_picture` ends by setting
  `gm_tr_trophy_picture_code` from `gm_tr_picture_trophies` (0 for a landmark with none, or a monument that isn't a
  landmark, whose rows show the monument's picture alone). A secondary monument's row keeps `gm_tr_picture` alone:
  it is no trophy.
- **Held Abroad** (open), while trophies taken from the country's lands stand abroad: a row per trophy, its holder and
  where it stands, the ways home on hover.
- **The state card:** Carry It Off under the monument, while the viewer could take it (share, levels, value and
  consequences in its tooltip). A second card, **Trophies on Display**, on a state where trophies stand, with Carry It
  Off or Bring It Home per trophy for an occupier.
- **Trophies on Display has three views** (added 2026-10-13, owner's request), chosen by three buttons in the card's
  header and kept in the client-side `gm_state_tr_view` (`GetVariableSystem`: unset is Full, `short`, `collapsed`; not
  saved, and one choice for every state):
  - **Full:** the pictured rows as before, showing each trophy's Grandeur, with a tooltip explaining that effects are aggregated and can be viewed in the Grand Monuments tab of the Timeline Extended window or in the Journal Entry.
  - **Short:** one line per trophy, no picture: its title and its grandeur in brackets, with the dedication, origin,
    year, worth and (for a landmark) its history on hover (`gm_tr_short_tt`). Carry It Off or Bring It Home ends the
    line as a smaller button (`gm_tr_button`'s `tr_button_layout` block), so an occupier acts without leaving the view.
  - **Collapsed:** the summary line alone, "N trophies, worth G grandeur to <holder>", with what the grandeur feeds
    on hover. The summary also heads Short, and Full when two or more trophies stand there.
  The total is the sum of the trophies' `gm_tr_grandeur`, written by the monthly pass beside the count
  (`gm_tr_here_grandeur`, read by `gm_state_tr_disp_here_grandeur`; an older save reads 0 until the next pass). It is
  grandeur and not a prestige figure because the national effect is a step curve over everything the holder owns
  (`gm_curve_steps_f5`), so a trophy has no flat bonus to add up.
- **Our Monuments:** Carry It Off on an eligible monument's row.
- **Notices:** the occupier's offer (`monument_trophy_events.1`, players), toasts for a taking (both sides), a
  homecoming and a trophy brought within reach.
- **How Grand Monuments Work** gains a Trophies note.

## 7. The AI

- **Loots** an occupied monument (or a trophy on display) with a monthly chance, `gm_tr_ai_loot_chance`: 2%, plus 10%
  times the clout share of the governing interest groups that approve of Total War, Ethnostate or National Supremacy,
  plus 5% if unrecognized, plus 3% for a monument of 10 levels or more; ×0.25 once UNESCO is in force. A trophy whose
  origin it owns it always takes home.
- **Carries home** from its own unincorporated states at 1% a month, when the Armed Forces are in government or the
  monument is 10 levels or more.
- **Brings home** every trophy whose origin it owns, at the monthly pass, except one it carried off itself
  (`gm_tr_held_by_its_taker`, added 2026-10-12). Without that exception an AI that took a monument from its own
  colony brought it straight back at the next pass, for ten years of The Homecoming, and a piece could be taken
  again once its cooldown ran out.
- **Returns** a trophy at 2% a month when the claimant is an ally or in its power bloc.
- **Treaties:** requests Return Cultural Property when it has trophies abroad; requests Surrender a Monument rarely, as
  a major power or greater with a looting-minded government. The giver's reluctance grows with the levels at stake.

## 8. Numbers

| Quantity | Value | Where |
|---|---|---|
| Shares | 1 / 0.25 / 0.1 | `gm_state_tr_share` |
| Value abroad | half the levels, rounded up | `gm_tr_take` |
| Cooldown after a piece | 3,650 days | `gm_tr_cooldown` |
| Infamy | 2 + levels / 5, at most 8; ×2 under UNESCO | `gm_tr_infamy` |
| Relations | −30 taken, +40 returned | `gm_tr_relations_taken`, `_returned` |
| War support | +10 | `gm_tr_war_support` |
| Radicals (own state) | 10% | `gm_state_tr_take_own` |
| The Homecoming | +5 legitimacy, 120 months | `gm_boon_homecoming` |
| AI loot chance | 2% + 10% × looting clout + 5% unrecognized + 3% tall; ×0.25 UNESCO | `gm_tr_ai_loot_chance` |
| AI carry home / return | 1% / 2% a month | `gm_tr_ai_own_chance`, `gm_tr_ai_return_chance` |

## 9. Tests, debug, docs

- **`test_grand_monument_trophies.py`**: `TROPHY_SHARES` covers every form of `FORMS`, `BUILDING_FORMS` and
  `RETIRED_FORMS` once, and its share script value matches; the shrine is never taken; the piece and title loc has a
  branch per form and per landmark; the occupation test reads provinces; the pass is wired to `on_monthly_pulse` and
  clears before it writes; the totals add trophies to standing and to the Armed Forces only; the articles guard the
  preview pass; every new loc key exists.
- **Debug** (`te_debug_monuments.6`): carry off the tallest monument of a country at war with us (bypassing the
  province test); carry off our own tallest monument as if from an unincorporated state; return every trophy we hold;
  run the pass and print `TE_MONUMENTS:` trophy lines.
- **Audits:** `container_timed_variable` (no timed variable on a trophy), `script_argument`, `loc_coverage`,
  `empty_effect`, `silent_variable`, `event_image`, `event_context`, `treaty_evaluation_scope`, `gui_reference`.
- **Docs:** `mod_systems.md` § Grand Monuments; v2 §6 and the landmarks spec's Appendix A point here; the player
  guide's `02-timeline.md` gains *Trophies*; `scripting_best_practices.md` gets what the build teaches.

## 10. In-game checks

1. Occupy half a state's provinces in a war: the card's Carry It Off appears, the notice fires once, and the taking
   leaves a trophy in our capital, the right share of levels, the monument smaller (or gone) with its name and picture.
2. The victim's war support rises by 10; our infamy and relations move as the tooltip said.
3. The trophy row shows in Trophies; the origin's owner sees it in Held Abroad.
4. Return It rebuilds it at home (added to a standing monument, or a new one with its records and dedication), with
   the Homecoming boon.
5. Occupy the site as the origin's owner: Bring It Home on the Trophies on Display card sends it straight home.
6. Conquer an unincorporated state's monument: Carry It Off from the row, radicals in that state.
7. Surrender a Monument and Return Cultural Property appear in the treaty designer and as Enforce Treaty Article war
   goals, and take effect.
8. The AI loots and returns over an observer run; `debug.log` shows no new errors, and no error spam while the treaty
   designer lists either article.
9. **Unverified engine reads:** that `any_province` with `controller` reads occupation as described; that removing
   and rebuilding a monument in a state the actor doesn't own builds it for the owner; what queued levels do when a
   piece is taken (the gift's open question).
10. **The picture (2026-10-13):** each trophy row shows its monument's picture: the Parthenon's for the marbles, the
    Brandenburg Gate's for the Quadriga, and a carried-off column's own style and form. An older save's trophies show
    the draped picture until the next month's pass. **Since 2026-10-16** a landmark's trophy shows its own picture over
    that one (the marbles in a museum room, the Luxor obelisk in a glass-roofed court) in Trophies, Held Abroad and
    Trophies on Display, from the next month's pass; a returned trophy standing as a secondary monument shows its
    monument's picture again.
11. **The three views (2026-10-13):** on the Home Counties (four of the trophies of 1836 stand there) the card opens in Full with a Grandeur line under each row and the summary line above them. Short is a
    line per trophy: check that no title wraps in the 392-wide cell (a long one wrapping is tolerable, but note which),
    that the grandeur in brackets matches the Full rows, that hovering a line shows the dedication, origin, year and
    worth, and a landmark's history, and that Carry It Off, in a war with Britain while we hold the Home Counties,
    ends the line at 112 px without clipping or widening the card. Collapsed shows the summary alone. The buttons
    grey the view that is showing, the choice holds as you move to another state with trophies, and a fresh session
    opens in Full. The totals read 0 on a save from before the change until the next month's pass.
    **Unverified engine reads:** that a `block` with a default body (`tr_button_layout`, `tr_button_text_width`) takes
    a `blockoverride` from the Short row and keeps its default for the Full row; that `parentanchor = right|vcenter`
    seats the buttons at the header's right; that `Or(Exists, GreaterThan_CFixedPoint(...))` hides the summary for one
    trophy in Full only.

## Out of scope

- The UN topic (a follow-up PR).
- A monument as a gift between countries (the Luxor Obelisk).
- ~~A trophy's own picture: rows show a statue icon.~~ Brought in on 2026-10-13: a trophy's row shows the picture of
  the monument it was taken from (§6).
- Taking from a subject country outside a war.
