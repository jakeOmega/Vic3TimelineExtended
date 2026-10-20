# Grand Monuments: unique dedications (signatures) — design

**Date:** 2026-10-16
**Status:** asked for by the owner on 2026-10-16 ("unique dedications tied to specific historical monuments and special
dedications unlocked only by completing specific Monument Opportunities"). The owner chose the signature layer over new
dedications and decided the forks in §0, and approved the rest of the first draft the same day. Every other call is this
spec's, marked *(design)*, and open to review on the PR.
**Builds on:** `2026-09-27-grand-monument-rework-design.md` (the curve, kinds, fit, contests),
`2026-10-12-grand-monuments-landmarks-design.md` (landmarks; Appendix B, phase 6's candidates),
`2026-10-12-grand-monument-opportunities-design.md` (moments, boons, the gift), `2026-10-12-grand-monument-trophies-design.md`
(trophies count half), `2026-10-13-multiple-monuments-per-state-design.md` (secondaries as `gm_monument` containers),
`2026-10-14-grand-monument-archaeology-design.md` (buried sites; the deferred Antiquity and Archive dedications, from issue
#939's comment) and `2026-10-16-grand-monument-ageing-design.md` (grandeur = levels + age).
**Replaces:** v2 §7's historical commissions as written (§6 below rebuilds them on the opportunities and on signatures),
and #939's plan to add Antiquity and Archive as the 13th and 14th dedications (§4: they become signature families).

## Intent

Grand Monuments have 87 landmarks, each with its own name, picture and line of history, but each plays as one of the
twelve dedications. 57 of them are To the Nation, which has no national effect of its own, so the Parthenon,
Persepolis, the Terracotta Army and Machu Picchu play like a column in a provincial town, and the 17 crowned palaces and
royal tombs play alike. A completed opportunity leaves nothing behind once its ten-year boon runs out.

This change gives a monument a **signature**: a unique dedication layered on one of the twelve. A historical monument
carries its own; completing certain opportunities gives the monument that completed it one; and phase 6's
historical opportunities raise a landmark that carries one.

Success looks like: the Temple of Heaven's row reads "Temple of Heaven — The Mandate of Heaven", hovering the name says
it is a unique dedication of To the Crown and what it adds, and its effect shows in National Effects; the War Memorial
that completes a Victory opportunity is dedicated To Victory, and the next victory's memorial is too; and Bavaria's
player is offered Walhalla in 1836 and, on completing it, has the landmark.

**Non-goals.** No change to the twelve dedications, their effects, kinds, fit or contests; to the curve or the step
values; to names, styles, forms or pictures other than phase 6's new landmarks; to the opportunities' moments, timers,
gift, approval or boons.
**Anti-goals** (failure even if it works): a signature that counts while its monument is contested, or for a dedication
it was not given on; a signature that is lost when a monument moves to a container, is carried off and returned, or
its state merges (#936); a special dedication that appears in the building panel; anything that rebuilds a monument
inside a tooltip-walked effect.

## 0. The owner's decisions (2026-10-16)

| Question | Decision |
|---|---|
| New dedications, or a layer on the twelve | **The layer** |
| How the name shows | **In place of the dedication's name, with the parent as a tooltip** |
| Specials from opportunities | **One monument per completion:** each completed opportunity gives one monument its special, and completing another of that kind later gives one more. No other cap; "limited by circumstance" (owner's correction, 2026-10-16) |
| One-off effects | **Maybe for a handful; families are probably fine too** (§4.2 proposes four one-offs) |
| A trophy's signature | **Counts for whoever holds it, at half** |
| A signature's own interest group | **Only where it makes sense**, never for its own sake (§2.3) |

## 1. What a signature is

A signature is a **parent dedication plus a signature record**, as a law variant is its parent plus a skin
(`parent = law_x`).

- **The parent does everything it does today:** the production method (the primary's) or `gm_tr_dedication` (a
  container's), the kind, the fit, the contests, the interest-group stances, opportunity progress and the building
  panel. No PM, ratchet, kind, fit, contest or IG-stance code changes.
- **The signature adds** its name, shown in place of the parent's (§3), and its effects (§2).
- **Records** *(design)*:

  | Record | State (primary) | Container (secondary, trophy, shadow, site) | Meaning |
  |---|---|---|---|
  | Signature | `gm_signature` | `gm_tr_signature` | flag: the effect group, a family (§4.1), a one-off (§4.2) or a special (§5) |
  | Its parent | `gm_sig_parent` | `gm_tr_sig_parent` | flag: the dedication it was given on, one of the twelve keys |

  Both pairs join `CONTAINER_RECORDS`, so demotion, the swap, shadows (`gm_sh_mirror`) and adoption carry them; the
  trophy copy points carry them too (§7).
- **On its parent:** the monument's dedication is its `gm_sig_parent` (`gm_state_sig_on_parent`, `gm_mon_sig_on_parent`).
  A monument rededicated to another dedication keeps its signature **dormant**: no effect, the parent's name. Rededicated
  back, it is live again.
- **One per monument.** A monument that carries a signature keeps it; nothing gives it a second (§5.2).
- **Never in the building panel.** A pick there gives the plain parent. A special reaches a monument by completing its
  opportunity, or through the ceremony while the country holds one (§5.2, §5.3).

When a signature counts, by the monument's status:

| Status | Name shown | National effect | Local effect | Its IG |
|---|---|---|---|---|
| Upheld, on its parent (`gm_state_status_fits`) | the signature's | yes | yes | yes |
| Heritage or contested, on its parent | the signature's | no | yes | no |
| Undedicated, or on another dedication (dormant) | the dedication's | no | no | no |
| A trophy abroad | the signature's | **for its holder**, at the trophy's grandeur (§2.4) | no | no |

The national and IG columns follow the parent's own rule (its national sums read `gm_state_status_fits`), and the local
column follows "whatever the monument's status", the rule the local dedication effects already use.

## 2. Effects

### 2.1 National

Each signature with a national effect is one static modifier carrying **one step**, on `je:je_grand_monuments`, with
the multiplier its step count, as the dedications' are (`gm_national_<key>`, `gm_step_<key>` mirrors):

- `gm_sum_sig_<key>`: the grandeur of the country's monuments that carry it and count (primaries through
  `every_scope_state`, secondaries through `gm_monuments_held`, plus held trophies, §2.4). A family's sum counts its
  one-offs too (§4.2). *(design)* The sums run in one walk over the states and one over each list, not a walk per
  signature.
- Through the curve with F = 5 (`gm_set_steps`), then the monument policy's standing factor (`gm_policy_factor_standing`:
  Mothballed halves it) *(design)*, into `gm_national_sig_<key>` from `gm_apply_national_modifiers`, removed in
  `gm_remove_national_modifiers`.
- Antiquity's national effect is cultural pull, which is a script value, not a modifier: `cultural_pull_from_antiquity`
  (its steps × 1, at most +3), added to `cultural_pull_from_monuments` beside `cultural_pull_from_grand_monuments`, whose
  steps it does not share. (That one lost its +5 cap on 2026-10-16, owner: monument cultural pull has diminishing
  returns, not a ceiling. Whether this +3 cap goes the same way is open.)

### 2.2 Local

A signature with a local effect counts the grandeur of every monument in the state that carries it and stands on its
parent, primary and secondaries, in `gm_state_monthly` beside `gm_state_local_steps_one`
(`gm_state_sig_local_steps_one = { SIG = <key> }`), times `gm_policy_factor_local`. Its multiplier variable is zeroed,
never removed. Like the dedications' local effects, it shows on the state card, so it stays out of the state panel's
modifier rows.

### 2.3 Its interest group

A signature may name **one approving group of its own**, added to the parent's, where the history calls for it: three
do (§4.1, §5.4), all the Intelligentsia. In `gm_compute_ig` a monument that carries one and fits adds its grandeur to that
group's net, as an approving dedication does (`gm_state_sig_approved_by_<ig>`, `gm_mon_sig_approved_by_<ig>`). Nothing
opposes a signature *(design)*: #939's Devout objection to Antiquity under State Atheism is out of scope.

### 2.4 Trophies

A trophy keeps its signature records. Its **holder** counts the trophy's grandeur (`gm_tr_grandeur`, which is already
half the levels and age carried off) toward the signature's national sum, whatever the holder's government *(design)*:
a trophy has no fit, and its standing grandeur already counts the same way. No local effect and no IG. The monument a piece
was taken from keeps its signature at its smaller grandeur; one taken whole gives its country nothing until it comes home.

This puts signatures on the trophies of 1836 from the first day: Britain's Parthenon marbles (Antiquity), Rosetta Stone
(Archive) and Tipu's Tiger (Martial Glory) in London and the Kandyan throne (Seat of the Throne) at Windsor; Paris's
Dendera Zodiac (Archive), Luxor
Obelisk and Venus de Milo (Antiquity) and Brest's Baba Merzoug (Martial Glory); Venice's Piraeus Lion and Horses of
Saint Mark (Antiquity). Each is small, a trophy's grandeur.

## 3. The name, and the parent on hover

- **`gm_dedication_name`** (state) and **`gm_tr_dedication_name`** (container) gain branches ahead of the twelve: a
  monument on its signature's parent prints the signature's name. That is the landmark's own name for the signature when
  it has one (§4.3), else the effect group's. These are the plain names, for events and tooltips.
- **The label with a hover,** `gm_dedication_label` (state) / `gm_tr_dedication_label` (container), is what the row
  title (`gm_row_title`, `gm_row_title_named`), the state card's title, the rows of monuments beside another
  (`gm_mon_row_detail`) and the trophy rows (`gm_tr_row_detail`) print instead. For a signature it is the name as a hover
  span, `#tooltippable;tooltip:[State.GetTooltipTag],gm_sig_parent_tt <name>#!`. Hovering it shows "A unique dedication
  of <parent>", then the signature's effect at this monument's grandeur and, when dormant or not counting, why. Without a
  signature it is the plain name.
- **Unverified:** a hover span inside a customizable-localization result, and any tooltip tag for a script container.
  The fallback, which `gm_row_landmark` already uses for a landmark's history, is a row line of its own ("A unique
  dedication of To the Crown") with the tooltip on it (§9).
- **The building panel** keeps the parent's PM name; a production method's name can't be scripted.

## 4. Historical monuments

### 4.1 The families

A family is one effect, shared by its members. Every family with a member stands on that member's historical dedication
(its `LANDMARKS` row), so one family can hold monuments on different parents (Liberty).

| Family | Name | National, per step | Local, per step | IG | Members (`LANDMARKS` keys) |
|---|---|---|---|---|---|
| `antiquity` | Ancestral Antiquity | +1 cultural pull (its own cap +3) | +10% Tourism Industry throughput | Intelligentsia | stelae_of_aksum, parthenon, obelisks_of_karnak, persepolis, luxor_obelisk, venus_de_milo, piraeus_lion, horses_of_saint_mark, great_zimbabwe, uffizi_gallery, capitoline_museums, temples_of_baalbek, palmyra, xanthos, arch_of_ctesiphon; buried: winged_victory_of_samothrace, troy_hisarlik, mycenae_grave_circle, pergamon_altar, deir_el_bahari_cache, ishtar_gate_babylon, palace_of_knossos, oseberg_ship, machu_picchu, bust_of_nefertiti, tomb_of_tutankhamun, royal_cemetery_at_ur, sanxingdui_pits, sutton_hoo, tomb_of_pakal, terracotta_army, tomb_of_philip_ii, tomb_of_marquis_yi, royal_tombs_of_sipan, olympia, delphi, sidon_necropolis, tomb_of_alexander, pompeii |
| `archive` | Epigraphic Archive | +2 innovation cap, +2% technology spread | +10% University throughput | Intelligentsia | rosetta_stone, temple_of_dendera, mesha_stele; buried: nineveh_library, vindolanda_tablets, antikythera_mechanism, mohenjo_daro, lascaux_caves, nag_hammadi_library, dead_sea_scrolls, mawangdui_tombs, otzi_the_iceman, caral_supe, gobekli_tepe, villa_of_the_papyri |
| `throne` | Seat of the Throne | +3% authority | — | — | temple_of_heaven, topkapi_palace, golestan_palace, sans_souci_palace, royal_palace_of_benin, royal_palace_of_kumasi, imperial_city_of_hue, red_fort, royal_palaces_of_abomey, klungkung_palace, royal_palace_of_kandy |
| `royal_pantheon` | Royal Pantheon | +5% loyalists from high legitimacy | — | — | alexander_column, basilica_of_superga, tomb_of_william_the_silent, cenotaph_of_maximilian, arco_de_santa_maria, statue_of_louis_xiv, nikko_toshogu |
| `martial_glory` | Martial Glory | +5% morale recovery | — | — | arc_de_triomphe, brandenburg_gate, lion_monument, bukgwan_victory_stele, tipus_tiger, baba_merzoug, bodrum_castle |
| `liberty` | Liberty | +3% migration pull | — | — | washington_monument_baltimore, liberty_column, lion_of_saint_mark |

- The Antiquity and Archive split follows #939's table for the sites it lists. *(design)* for the rest: an inscription
  or a record of knowledge is Archive (the Rosetta Stone, the Dendera Zodiac, the Mesha Stele, the Villa of the Papyri's
  library); a ruin, a tomb or an artwork is Antiquity.
- **No family** *(design)*: the five civic-progress landmarks (La Scala, the Teatro di San Carlo, the Jantar Mantar, the
  Shalimar Gardens, the Jardim Botânico). Their dedication is already their own building's, so what they would gain is a
  name, not an effect; a "Muses" family is a candidate for later (Out of scope).
- The effects are first estimates (§12). Every field is checked with `/modifier-search` before it is written:
  `unit_morale_recovery_mult` and `state_migration_pull_mult` on a country modifier are the two this spec has not seen
  used that way. The boons prove `state_*` fields on the journal entry act country-wide.

### 4.2 One-offs

A one-off is a family of one with a **flourish**: it counts in its family's sum and adds an effect of its own, so it is
never weaker than the family *(design)*. It has its own row in National Effects (§8).

| Landmark | Name | Family | Flourish, per step |
|---|---|---|---|
| Arc de Triomphe | To the Grande Armée | Martial Glory | +3% prestige |
| Temple of Heaven | The Mandate of Heaven | Seat of the Throne | +1 legitimacy |
| Parthenon | The Glory of Athens | Ancestral Antiquity | +2% influence |
| Terracotta Army | The First Emperor's Army | Ancestral Antiquity | +25% Tourism Industry throughput (local) |

The owner may strike any of them without touching anything else; a struck one becomes an ordinary member of its family.

### 4.3 Names

A member can carry a **name of its own**: one loc key (`gm_sig_name_<landmark>`) and one branch in the name custom locs,
checked by the registry test. Phase A names the four one-offs; any other member shows its family's name until it gets
one. *(design)* No landmark's signature name refers to a person or event after 1836 (the landmarks spec's rule).

### 4.4 When a landmark gets its signature

The signature of a landmark is a function of its key (`gm_sig_from_landmark`, a branch per family and one-off listing
its keys). One writer:

- **The refresh** gives every monument that has `gm_landmark` and no `gm_signature` its signature, with `gm_sig_parent`
  set to its historical dedication. So does the container twin in `gm_monument_monthly` for `gm_tr_landmark`, and
  `gm_trophy_monthly` for trophies. This covers the landmarks of 1836, sites as they are unearthed, trophies of 1836 and
  every existing save, and heals any copy point that misses the records within a month.
- The seeding helpers (`gm_seed_landmark`, `gm_seed_landmark_beside`, `gm_seed_trophy`) and `gm_arch_place` call it too,
  so day one is right *(design)*.

`gm_clear_state = { KEEP_LANDMARK = yes }` (Rededicate) keeps both records; with `KEEP_LANDMARK = no` they go with the
landmark. A rededicated landmark on another dedication is dormant until rededicated back to its historical one (the
Alexander Column made To the Republic is no Royal Pantheon).

## 5. Special dedications from opportunities

### 5.1 One completion, one monument

**Each completion of an opportunity with a special gives one monument that special** (owner, 2026-10-16: "an unlock
should be for one of that monument"). Completing another of the same kind later gives one more. There is no other
cap. The number a country raises is the number of times it completed the moments: Victory and Defeat come with every
qualifying war, A space first with each of the five firsts, Among the Great Powers and each technology once a game.

### 5.2 On completion: the completing monument takes it

- **The completing monument takes the special** where the gift lands. A primary's is written in `monument_events.26`:
  `gm_com_fulfil` marks it with `gm_sig_grant` (the special's flag, from the source by `gm_sig_special_for_source`)
  beside `gm_gift`. A secondary's is written beside the `gm_mon_add_age` call in `gm_com_fulfil`, which writes
  variables only, as the gift does there. The monument's dedication is the opportunity's, which is the special's
  parent, so nothing is rebuilt.
- **Held, when it can't.** When the completing monument already carries a signature (a landmark the fallback chose)
  or no monument can take it, the country **holds** the special instead: `gm_sig_held_<special>`, a count in a country
  variable, so a civil war's winner keeps it (`scripting_best_practices.md` § "What a Civil War's Winner Inherits")
  *(design)*.
- **`monument_events.28`** names the special along with the boon: "The Lisbon Arch is now dedicated To Victory," or,
  when held, "Your next War Memorial can be dedicated To Victory."
- **Spent for good.** A special stays with its monument. Pulled down, rededicated (`gm_clear_state` removes it from a
  monument that is not a landmark) or lost with its building, it is gone; nothing gives it back. Carried off whole, it
  goes with the trophy, counts for the holder at half (§2.4) and comes home with it.

### 5.3 In the ceremony: only for a held special

- One option per special, **hidden** unless the country holds one *(design: hidden, not greyed: the ceremony already
  lists twelve dedications)*, and gated as its parent is (the Grand Stadium's technology for Olympic). Its effect is the
  parent's dedicate helper, then the two records, then one off `gm_sig_held_<special>`. Its tooltip names the parent and
  lists both effects in a `custom_tooltip` (`silent_variable_audit`).
- The AI takes a held special whenever the ceremony offers it, since holding one gains nothing.
- A special counts as its parent everywhere else: the sums, fit, contests and opportunity progress.

### 5.4 The first wave

Each special's effect is **its opportunity's boon made permanent, at a fifth per step** *(design)*: one rule, and every
field is already validated by the boons.

| Opportunity | Special | Parent | Per step | IG |
|---|---|---|---|---|
| Victory | To Victory | War Memorial | +2% prestige | — |
| Defeat | To the Unknown Soldier | War Memorial | −5% radicals from low legitimacy | — |
| Among the Great Powers | To the Concert of Nations | To the Nation | +2% influence | — |
| A space first | To the Conquerors of Space | To the Nation | +2% innovation | Intelligentsia (they ask for it) |
| Television Broadcasting | Olympic | Grand Stadium | −1% mortality | — |

Names are working titles. The source's dedication must be single: A New Reign (Crown or Leader) and A New Order (Crown,
Republic or Revolution) wait until a special can be keyed by source and dedication (Out of scope).

### 5.5 The offer says what is at stake

The offer (`monument_events.21`) and the Opportunity section's "what completing it gives" add "and dedicates the
monument that completes it <special>". For a moment that comes once a game (Among the Great Powers, each space first,
the technologies), the tooltip adds that letting it pass loses that monument's special for good.

### 5.6 Old saves

A save from before this change holds no specials. A one-off pass (`gm_sig_seed_round` against `gm_sig_seed_rounds`,
the pattern of `gm_arch_seed_round`) gives the country one held special for every source whose boon still runs
(`gm_boon_<source>` above 0), so an opportunity completed in the last ten years counts *(design)*. No monument takes it
then; the next ceremony that can raise its parent offers it.

## 6. Historical opportunities (phase 6)

Phase 6's historical commissions, rebuilt on the opportunities and on signatures. The landmarks spec's Appendix B rules
stand: each is offered **once a game**, to whoever holds its state, for **40 years from the year construction began**,
with **no rank gate**, and letting it pass or running out costs nothing.

### 6.1 What one is

- **A source**, `historical`, with `gm_com_landmark` naming the landmark (a new opportunity record, cleared by
  `gm_com_clear`). Its dedication, form and state are its `LANDMARKS` row's; its namesake is `landmark`.
- **Who asks:** the parent's approving group (`DEDICATIONS.approve`), as A New Order does *(design)*.
- **The target:** its `LANDMARKS` level, 5 or 10. **The time:** the rank's months (`gm_com_time_months`) × target ÷ 5
  *(design)*, so a ten-level monument has twice as long.
- **The holder condition** from Appendix B (a German, Russian, Hungarian or Greek primary culture for the national ones,
  crowned for the Victoria Memorial, a republic for the Washington Monument, Sunni for the Muhammad Ali Mosque), held
  when the offer is made and while it is open; when it stops holding, the opportunity lapses.
- **Pacing:** a window, not a moment, so it waits while another opportunity is open and is offered when that closes,
  while its window lasts (v2 §2.5). The once-a-game record is global (`gm_hist_offered_<key>`).
- **No boon** *(design)*: what it gives is the landmark. The gift (+5 age) and the approval are the same as any
  opportunity's.

### 6.2 Completion makes the landmark

The completing monument in the state becomes the landmark: `gm_landmark`, `gm_skin = landmark_<key>`, its form, the
`landmark` namesake (so the historical-name lock holds), its picture (`gm_state_update_picture`), and its signature
(§4.4). Container twins for a secondary. The style and form chosen at its unveiling give way to the landmark's. The
helpers are `gm_state_become_landmark` / `gm_mon_become_landmark`, called where the gift lands (§5.2). "One per state"
from v2 §7 no longer applies: since the multiple-monuments rework, the new monument stands beside the old.

### 6.3 Families for the candidates

The Appendix B candidates join Track A's families, and one new family, **Heroes of the Nation** (`heroes`, +5%
assimilation per step), takes the national pantheons *(design)*:

| Family | Candidates |
|---|---|
| Martial Glory | Bunker Hill Monument, Obelisk of the Second of May, Nelson's Column, Völkerschlachtdenkmal |
| Liberty | Washington Monument, O'Connell Tower, Angel of Independence |
| Royal Pantheon | Victoria Memorial |
| Heroes of the Nation | Walhalla, Hermannsdenkmal, Scott Monument, Millennium of Russia, National Pantheon of Caracas, Millennium Monument, Gateway Arch |
| none (the civic-progress buildings and the shrine) | Muhammad Ali Mosque, Vienna Court Opera, Panathenaic Stadium, Royal Exhibition Building, Teatro Colón, Palace of Fine Arts, Estadio Centenario, Palomar Observatory |

### 6.4 The first batch

The six earliest, so an observer run of a few years sees them offered and built: Walhalla, the Bunker Hill Monument, the
Obelisk of the Second of May and the Muhammad Ali Mosque (1836), Nelson's Column (1840) and the Washington Monument
(1848). Each is a `LANDMARKS` row with `placed=False` and a new `year`, and a row in a new `HISTORICAL_OPPORTUNITIES`
table (key, year, condition, asking IG). It shows a stand-in picture until its own is drawn (code 1,000,000 + its row).

## 7. Records a container carries

| Copy point | What it does with the signature pair |
|---|---|
| `gm_state_demote_primary`, `gm_state_raise_secondary` / `gm_state_tr_take_records_from_moving`, `gm_state_swap_primary` | state ↔ container, through `CONTAINER_RECORDS` |
| `gm_sh_mirror` (shadows), `gm_sh_adopt_beside`, `gm_state_raise_orphan` | mirrored and adopted with the rest |
| `gm_state_tr_make_trophy`, `gm_mon_tr_take_whole`, `gm_mon_tr_take_piece`, `gm_arch_partage` | copied onto the trophy (a piece too) |
| `gm_tr_return_home`, `gm_state_tr_rebuild_from_moving`, `gm_tr_become_monument` | back onto the state, or kept on the container that becomes a secondary |
| `gm_clear_state` | removed, unless `KEEP_LANDMARK = yes` and the monument is a landmark |
| `gm_state_promote_secondary` | the promoted container's records onto the state |

The monthly backfill (§4.4) is the net for a landmark. A special has none, so its copy points are the registry test's
to pin (`CONTAINER_RECORDS` and a `TROPHY_RECORDS` check of the trophy copies) *(design)*.

## 8. Panels

- **National Effects:** a `gm_step_row` per signature in force, after the dedications' rows and before Interest Group
  Approval: label, bar (`gm_disp_frac_sig_<key>`), value, and a tooltip listing the monuments behind it and where its
  next step completes. A one-off's flourish has its own row. Antiquity's row shows its cultural pull. Each row is hidden
  at 0, as today. `test_grand_monuments_layout.py` pins the order.
- **Our Monuments rows, the state card, rows beside another, trophy rows:** the label (§3).
- **The state card's local effect line:** the signature's local effect is a second line under the dedication's, from
  `gm_state_disp_sig_local`, hidden at 0.
- **The ceremony:** the options for held specials (§5.3). **The opportunity's section and offer:** the special's line
  (§5.5).
- **A held special** shows under Opportunities Seized in National Effects: "Held: To Victory, for your next War
  Memorial" *(design)*.
- **How Grand Monuments Work:** a paragraph on unique dedications.

## 9. Engine facts this rests on

- **Nothing new on effects:** one-step static modifiers multiplied from the country pulse on the journal entry, and state
  modifiers from the state pulse, are the dedications' own pattern.
- **Unverified (play-test, not a self-check, since it is UI):** a `#tooltippable;tooltip:[State.GetTooltipTag],<key>`
  span returned through customizable localization (§3), and any tooltip tag on a script container. Fallback: the row
  line with its own tooltip.
- **Unverified:** `unit_morale_recovery_mult` and `state_migration_pull_mult` acting from a country modifier. Checked
  with `/modifier-search` at build; fallback, a field the base game uses on country modifiers (`country_prestige_mult`
  for Martial Glory, `country_influence_mult` for Liberty).

## 10. Tests, debug, audits

- **`test_grand_monument_registry.py`:** a `SIGNATURES` table (key, kind: family / one-off / special, family, name,
  national field and step, local field and step, IG, source), the checklist for adding one. `Landmark` gains `signature`
  (a family or one-off key, or `None`) and `year`; `COMMISSION_SOURCES` gains `special`. The tests fail unless each
  signature has its modifier with one field and an icon, its step mirror, its sum, its national hooks (add and remove),
  its row, its loc; each local one its state-pulse call and card line; each IG one its `gm_compute_ig` term; each landmark
  member its branch in `gm_sig_from_landmark`; each name its custom-loc branches; each special its branch in
  `gm_sig_special_for_source`, its grant on both paths (`.26` and beside `gm_mon_add_age`), its held count, its ceremony
  option and its offer line; both record pairs are in `CONTAINER_RECORDS`.
- **`test_grand_monuments_layout.py`:** the new rows, in order. **`test_grand_monument_trophies.py`:** a trophy carries
  the pair, and its holder's sum counts `gm_tr_grandeur`.
- **Debug, `te_debug_monuments.8`:** a) hold one of every special; b) run the landmark backfill now; c) give the tallest
  monument each signature in turn (as `.4` steps through pictures); d) log every monument's signature, parent and whether
  it counts on `TE_MONUMENTS:` lines.
- **Audits that cover the new script:** `silent_variable` (ceremony options), `loc_coverage`, `script_argument`,
  `je_immediate_reset` (nothing written in an unguarded `immediate`), `modifier_multiplier_var` (each multiplier from
  ROOT), `empty_effect`, `event_context`.

## 11. Player guide

`02-timeline.md`: a **Unique dedications** subsection after "Monument dedications": what a signature is, the hover, when
it counts (the status table, shortened), the families with their effects and a few members each, the one-offs, and the
specials with the opportunity that gives each, one monument per completion. The opportunities table gains a "Special"
column; "Monument trophies"
gains a sentence on a trophy's signature; Phase C adds "Historical opportunities" under "Monument opportunities".
`17-reference.md` gains a "Unique dedication" entry. Rebuild the PDF in the same PR.

## 12. Numbers — first estimates

| Quantity | Value | Anchor |
|---|---|---|
| Curve | F = 5 for every signature | the dedications' national effects |
| Antiquity | +1 cultural pull a step (own cap +3); +10% Tourism Industry throughput locally | #939: +1.5 uncapped and +35% against the standard +25% |
| Archive | +2 innovation cap and +2% technology spread a step; +10% University throughput locally | #939: +5 and +3%; the Grand Observatory's +3 |
| Seat of the Throne | +3% authority a step | A New Reign's boon, +10% |
| Royal Pantheon | +5% loyalists from high legitimacy a step | A New Order's boon, +25% |
| Martial Glory | +5% morale recovery a step | |
| Liberty | +3% migration pull a step | |
| Heroes of the Nation | +5% assimilation a step | A Centenary's boon, +25% |
| One-off flourishes | +3% prestige; +1 legitimacy; +2% influence; +25% local tourism | |
| Specials | a fifth of their boon a step | §5.4 |
| A trophy | its `gm_tr_grandeur` (half) toward the holder's sum | trophies spec |
| Historical opportunity time | rank months × target ÷ 5 | |

A landmark of 10 levels stands at 1.5 steps on day one and 2.25 after fifty years (grandeur 20); a completed
opportunity's monument (5 levels and the gift's 5) at 1.5. Checked in observer runs with the debug event before the PR.

## 13. Play-test list

A new `docs/testing/grand-monuments-signatures-playtest.md` (the owner's 2026-10-12 rule: in-game checks don't gate a
merge):

1. The Temple of Heaven's row and state card read "The Mandate of Heaven", and hovering the name shows To the Crown and
   the effect (or the fallback line shows).
2. National Effects shows Seat of the Throne and The Mandate of Heaven for China at the start; Britain's trophies show
   Antiquity, Archive, Martial Glory and Seat of the Throne at their small values.
3. A contested crown landmark loses its national signature and keeps its local one; kept as heritage, the same.
4. Rededicating the Alexander Column To the Republic shows To the Republic and no Royal Pantheon.
5. Carrying off a landmark piece moves part of its signature to the taker at half; bringing it home restores it.
6. Completing a Victory opportunity gives the completing memorial To Victory and `.28` says so; the next ceremony does
   not offer To Victory; a second Victory completed gives a second memorial To Victory.
7. A completing landmark keeps its own signature; the country holds the special, National Effects shows it held, and
   the next War Memorial's ceremony offers it once; the AI takes it.
8. A once-a-game offer's tooltip says letting it pass loses that monument's special.
9. An old save picks up landmark signatures within a month, and a held special for a boon still running.
10. Phase C: Bavaria is offered Walhalla in 1836; completing it turns the new monument into Walhalla, with its picture
   (or stand-in), its locked name and Heroes of the Nation.

## 14. Phasing

Each phase is its own PR.

| Phase | Content | Needs |
|---|---|---|
| A | §1–§4 and §7–§8: the layer, the six families, the four one-offs, the backfill, trophies at half | — |
| B | §5: the grant on completion, held specials and their ceremony options, the offer lines, the first five specials, old saves | A |
| C | §6: historical opportunities, the first six, Heroes of the Nation | A, B (the grant point) |

## Out of scope

- #939's Antiquity contest rule (contested under violent hostility toward its heritage culture) and its "+2 legitimacy
  when the owner's culture matches"; either needs more than a layer.
- A "Muses" family for the civic-progress landmarks and buildings.
- Specials for A New Reign and A New Order (keyed by source and dedication), and a second wave for the Centenary,
  A Reign Remembered, A New Faith and the other four technologies.
- A name of its own for every family member; the later phase-6 candidates; their pictures.
- A signature given by an anniversary event or an archaeological breakthrough.
