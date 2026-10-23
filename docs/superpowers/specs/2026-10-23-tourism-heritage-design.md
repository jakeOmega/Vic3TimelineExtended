# Tourism heritage: moving historical monuments out of base appeal (pass 1) — design

Status: owner-approved in conversation, 2026-10-23; builder check done; awaiting the owner's read of this document.
Pass 2 (townscapes) is a later project (§ 11), and the monument policy and prestige rework comes next (§ 15). The per-state moves
are in `2026-10-23-tourism-heritage-moves.csv` and the new monuments in `2026-10-23-tourism-heritage-monuments.csv`,
beside this document.

## 1. Intent

A state's base tourism appeal (`base_tourism_appeal_value`, `common/script_values/tourism.txt`, 671 hand-scored
states) was scored on its natural scenery, its climate *and* its historical monuments. The Grand Monuments system
then added monuments that raise tourism on their own, and seven vanilla wonders standing in 1836 do the same. So
the monuments count twice. Attica scores 100 for "the Acropolis, the Parthenon" and the Parthenon landmark adds
+100% Tourism Industry throughput on top. Upper Egypt (Karnak), Fars (Persepolis), Lebanon (Baalbek), Agra (the Taj
Mahal) and Cambodia (Angkor Wat) are the same.

The fix moves each monument's share of appeal (what the state would lose without it) into the monument. Heritage tourism then follows what happens to the
monument: it is looted, taken in war or dug up. Where a high score rests on a
monument the system doesn't have (Giza, Petra, Isfahan, Kyoto, Borobudur), the monument is added.

At the same time, monument tourism becomes an **output** bonus, as base appeal is, and smaller than today's.

## 2. Goals, non-goals, anti-goals

**Goals**

- No historical monument counts in both base appeal and a monument.
- Heritage tourism lives in monuments. A state's score without its monuments is right for its scenery, climate and
  townscape alone (owner, 2026-10-23: "if the wonder is destroyed, is the score appropriate?").
- At game start a state with its monuments standing scores at least what it does today.
- Every monument's tourism is an output bonus, like base appeal.
- Every monument that carries 20 or more points of a state's appeal is in the game, as a landmark if it stood and drew
  visitors in 1836 or as an archaeology site if it was buried or unvisited.

**Non-goals**

- **Townscapes** ("historic city of X", colonial towns, "Venice, an entire city built on water"). Pass 2, under the
  representative-monument rule (§ 11).
- Natural monuments, climate and culture. They stay in base appeal.
- Rescoring the non-heritage part of any state.
- Final art. New landmarks use placeholder pictures (§ 10).

**Anti-goals** (failure even if it works)

- A state whose monuments stand on 1 January 1836 ends up well below its old total. The exception is ruins nobody
  visited in 1836, whose points come back when they are dug. That one is intended.
- New landmarks shift politics: legitimacy, interest group approval, contests (§ 7 keeps them out).
- A heritage-rich minor (Egypt, Persia) turned into a great power by monument prestige (§ 8, § 13).
- A placeholder picture shipped and forgotten.

## 3. Decisions (owner, 2026-10-23)

| Question | Decision |
|---|---|
| Monument tourism | **Output, +10% Tourism output per step** of the state's grandeur, replacing +25% Tourism Industry throughput |
| Vanilla wonders | Their double count is fixed too |
| What comes off appeal | Points for a **specific structure, ruin, temple, palace or walled old town** a monument could stand for. "Historic capital", "rich history" and city atmosphere stay, for now |
| Townscapes | **Pass 2**, where a representative monument stands for a city's wider heritage, and looting it stands for wider looting (not only the pieces modelled were taken from Greece or Egypt) |
| Floor | **20 points** (two steps). Smaller amounts stay in base appeal, on a revisit list kept for later (Appendix D) |
| Ruins unknown in 1836 | Their points come off now; they come back as **archaeology sites** when dug, which is also when visitors started coming |
| Coverage | **All** gaps at or over the floor get a monument |
| Pictures | Placeholders for now, **clearly marked** so none is forgotten |
| New dedication | Where existing dedications' bonuses don't fit, a new one. **"To History"**: tourism, plus the prestige and cultural pull every monument gives. No legitimacy, no interest group approval, never contested, **cannot be pulled down**; it can still be looted or lost in a war |
| Prestige | **Lower the flat prestige per step and add a small percentage per step**, done in the policy pass (§ 15) |
| The score without the monument | **Must be right on its own**: if the wonder is destroyed, the state keeps what its scenery and climate merit. The Aegean, with its famous weather, mustn't score low without its monuments |
| To History's upkeep and policy | **No upkeep, and the monument policy doesn't scale its tourism.** Upkeep is a fixed £100 or so a level a week, which is small late in the game but a large share of a poor country's budget early on (§ 15) |
| The monument policy | **Its own design, next** (§ 15): the AI mothballs too readily, Mothballed should cut upkeep to zero, and Standard needs a benefit of its own |

## 4. Calls made in writing this (check these)

1. **Pilgrimage stays in appeal.** Where a living holy place draws pilgrims for the faith rather than the building
   (Mecca and Medina, Jerusalem, Varanasi, Bodh Gaya, Santiago, Mashhad, the Shwedagon), its points stay in base
   appeal. Looting or contesting the Kaaba is the wrong model, and pilgrimage outlives damage to the building. The
   same holds for the pilgrimage share of mixed states (the Golden Temple in Punjab, the Temple of the Tooth in
   Ceylon, Qom, Mount Tai, Mount Emei). Appendix E lists them.
2. **A monument takes what the state would lose without it, and never the townscape around it.** It may also take
   other named heritage in its state, up to what it gives (the Arc de Triomphe takes Versailles's points as well as
   its own, 30 in all). The city around it stays for pass 2: pulling down the Arc doesn't take Paris with it. Where a
   monument already stands but the comment credits only the city (Venice, Berlin, Milan), nothing moves in pass 1, and
   the monument is a gain until pass 2 (Appendix F).
3. **A site covers only what it represents.** An archaeology site takes the points of heritage it stands for. A site
   the appeal comment never mentions takes none and is a pure gain when dug (Göbekli Tepe, Sutton Hoo, Ötzi).
4. **Levels come from tourism points** (§ 6.2), not from political standing. A To History landmark carries no
   politics, so its level only sets its tourism, prestige and cultural pull.
5. **No unique dedications ("signatures") for new monuments in pass 1.** A signature is a named family a monument
   carries on top of its dedication (Ancestral Antiquity, Seat of the Throne, Royal Pantheon and four more, player
   guide § Grand Monuments), with its own national effect; Antiquity also adds Tourism Industry throughput. The new
   landmarks' levels are sized without that tourism, so they carry none. Existing landmarks keep theirs. Whether some
   new ones should join Antiquity (Giza, Abu Simbel, Petra) can be settled with the policy pass.
6. **To History is for landmarks and dug sites only.** The ceremony doesn't offer it for a monument a player builds:
   a player-built monument would otherwise get pure tourism and prestige with no politics. Existing landmarks keep
   their dedications.
7. **Vanilla wonders' figures** (§ 5.2) equal the points they take, so each state's total comes out right and the
   score without the wonder passes the scenery check (§ 6.1).
8. **Signature and event tourism convert at the same ratio** as the monuments' own, 0.4 of the throughput figure
   taken as output, rounded to whole fives (owner, 2026-10-23): +0.10 becomes +0.05, +0.25 becomes +0.10.
9. **The moves are a gated term, and the scores stay as written** (§ 6.3). With the Grand Monuments rule off, only
   the vanilla wonders' points move: a disabled system keeps its non-system effects (CLAUDE.md), so Lower Egypt
   doesn't sit at 50 forever with no pyramids. A save from before phase 2 keeps the points its new landmarks would
   take, since it never gets them.
10. **Middle Egypt's landmark is the Temple of Seti I at Abydos, not Dendera.** `temple_of_dendera` already exists: it
    is the origin record of the Dendera zodiac, an 1836 trophy in Paris, placed in Upper Egypt, with its own pictures
    and an Archive signature. It stays as it is. If Abydos proves to be in Upper Egypt too, the 20 points go to a
    Middle Egypt temple the builder finds (Amarna's are the Nefertiti site's).
11. **Western Mali takes its cut until someone builds the Djenné wonder.** The Great Mosque lay in ruins in 1836, so
    the ruins rule applies, and vanilla's wonder brings the points back.
12. **Mothballed still halves the country's monument prestige, To History's included.** Splitting standing grandeur
    by dedication would double the national totals' bookkeeping, and once the policy rework (§ 15) limits
    mothballing to a severe crisis, the case is rare. The rework can revisit it.

## 5. Monument tourism becomes output

### 5.1 Grand Monuments

- `gm_local_tourism` (`common/static_modifiers/gm_modifiers.txt`): `building_tourism_industry_throughput_add = 0.25`
  becomes `goods_output_tourism_mult = 0.10`. `gm_step_tourism` (`gm_values.txt`) becomes 0.10. The registry test
  pins them equal.
- The step count is unchanged: the state's summed grandeur on the 1/n curve (`gm_curve_steps_lin_f5`, at most 30
  steps), times the policy's tourism factor (Open ×1.5; State Ceremonial and Mothballed ×0.5).
- `gm_local_sig_antiquity` +0.10 throughput becomes +0.05 output a step. `gm_local_sig_first_emperor` +0.25 becomes
  +0.10. `gm_evt_pilgrim_hostels` (an event's timed modifier, `monument_events.txt`) +0.10 becomes +0.05.
- Loc that names throughput: `gm_state_tourism_tt`, `monument_events.2.common_tt`, the Antiquity and First Emperor
  signature lines, the pilgrim hostels option, and any `$building_tourism_industry_throughput_add$` splice in a GM key
  (grep `gm_` keys for it). `gui_chart_script_values.txt:190` reads `gm_local_tourism` and needs checking.

### 5.2 The vanilla wonders and other `bg_monuments`

`tourism_throughput_from_monuments` (`tourism.txt`) gives +0.25 throughput for each `bg_monuments` building (vanilla's
wonders, the mod's 37 in `wonders.txt`, the Space Program, the power bloc statue) and +0.10 for a Skyscraper. The
monuments move to a new output value, `tourism_bonus_from_monuments`, added to `total_tourism_output_bonus_percent`:

| Building | Output |
|---|---:|
| Taj Mahal | +40% |
| Angkor Wat | +30% |
| Hagia Sophia, Vatican City, Forbidden City, Saint Basil's Cathedral, White House | +20% |
| Great Mosque of Djenné (in ruins in 1836; vanilla's wonder rebuilds it) | +20% |
| Every other `bg_monuments` building | +10% |

The Skyscraper isn't a monument and keeps its +10% throughput, in a value of its own
(`tourism_throughput_from_skyscraper`). `extra_building_groups.txt:109` documents the old behaviour and needs the same
edit.

### 5.3 Why +10% output

Tourism Industry's inputs cost nearly as much as its output at base prices (1,380 against 1,500 for the first method).
So throughput, which scales inputs and outputs together, is worth little where the state has little output bonus and
a lot where it has much. Here is one +25% throughput step converted to the output bonus worth the same profit, with
+50% throughput from other sources and total output bonus M:

| Method | M = 0.2 | M = 0.5 | M = 1.0 | M = 1.5 |
|---|---:|---:|---:|---:|
| Tourism (1,380 in / 1,500 out) | +5% | +10% | +18% | +26% |
| Mass Tourism (2,800 / 3,000) | +4% | +9% | +18% | +26% |
| Jet Age (6,450 / 6,000) | +2% | +7% | +15% | +24% |
| Modern (11,300 / 10,000) | +1% | +6% | +14% | +23% |

So +10% output a step breaks even in a mid-appeal state. It is a cut in the high-appeal states, which is where the
double count was, and a gain in a low-appeal state. It also gives a clean exchange rate: **one step is 10 appeal
points.**

### 5.4 The tourism card

`te_state_tourism_card` (`gui/te_state_panel_widgets.gui`) shows Monuments in the throughput column
(`tourism_throughput_from_monuments`, line 460). It moves to the output column and reads `tourism_bonus_from_monuments`
(still uncapped, no bar). The Grand Monument card's tourism line (`gm_state_disp_tourism`) now reads as output. The
throughput column gains the Skyscraper row, or folds it into infrastructure's tooltip (builder's choice).

## 6. Base appeal

### 6.1 What comes off

For each listed state, read its comment and take off the points its named structures, ruins, temples, palaces and
walled old towns account for: what the state would lose without them (call 2). Townscape and pilgrimage (call 1)
stay.

Then the **scenery check**: the score left must be right for the state's scenery, climate and townscape alone,
judged against peers with no heritage to speak of. The references the pass used:

| Kind of state | Peers | Score |
|---|---|---:|
| Mediterranean or Aegean islands and coasts | Balearics, Canaries, Cyclades, Corsica, Cyprus | 80–85 |
| Mountain coast | Al Rif, Montenegro, Calabria | 75–80 |
| Temperate plain | Hannover, Anhalt, Posen, Mazovia, Zhili | 50–60 |
| River plain in the tropics or the Ganges | East Bengal, Central Provinces | 40–60 |
| Desert or arid steppe | Western Sahara, Kordofan, Libyan Desert, Aktobe | 30–40 |

Where the first figure left the state below its peers, fewer points move. The Aegean coast of Aydın keeps 70, not
50; Crete keeps 75, not 65. Where the check left the heritage share under the 20-point floor, the monument goes to
the revisit list instead (Wales's castles, Stonehenge, old Rhodes, Malta's temples). Where the points to move reach
20 and no monument covers them, a monument is added (§ 9).

### 6.2 Sizing

One step is 10 points. On the 1/n curve, step n ends at 5n(n+1)/2 grandeur, and an 1836 level is 5 grandeur. A
monument more than 100 years old in 1836 is already at its age cap, so its grandeur is fixed at level × 5:

| Points | Steps | Grandeur | Level (ancient) |
|---:|---:|---:|---:|
| 20 | 2 | 15 | 3 |
| 30 | 3 | 30 | 6 |
| 40 | 4 | 50 | 10 |
| 50 | 5 | 75 | 15 |

The curve runs on the state's **summed** grandeur, so a monument added beside another adds less than it would alone:
Petra at level 3 beside the Mesha Stele (level 5) makes 40 grandeur, three steps. Size against the sum. A landmark built
within 100 years of 1836 (the Grand Palace in Bangkok, Khiva's walls) starts smaller and grows by ageing, as the Arc
de Triomphe does.

### 6.3 Applying it

The moves are a **separate, gated term**, not edits to the scores (call 9). `base_tourism_appeal_value` keeps every
state's value as scored, and the points come off only while the monuments that take them can exist in the game:

- `scripts/generators/data/tourism_heritage_moves.csv`: state, points, monument, monument kind (wonder, existing
  landmark or site, new landmark, new site), reason. Appendix A in machine form, kept for pass 2 with the revisit and
  pilgrimage rows at 0 points. It starts as a copy of `2026-10-23-tourism-heritage-moves.csv`, beside this document.
- A generator, `scripts/generators/gen_tourism_heritage.py` (with `--check`), writes
  `common/script_values/tourism_heritage_generated.txt`: `tourism_heritage_moved`, a ladder by state region whose
  value is the sum of that state's moves whose gate holds, divided by 100. The gates:
  - moves to vanilla wonders: always, since the wonders exist whatever the rules;
  - moves to existing landmarks: while `gm_system_enabled` and the landmarks were seeded (`gm_landmarks_seeded`);
  - moves to existing and new archaeology sites: while `gm_system_enabled` (the seeding rounds give old saves new
    sites, `gm_arch_seed_rounds`);
  - moves to new landmarks: while `gm_system_enabled` and a new flag the phase-2 seeding sets
    (`gm_landmarks_seeded_2`). A save started before phase 2 never gets it, so it keeps those points. Landmarks for old
    saves stay out of scope, as the landmarks spec decided.
- `tourism_bonus_from_base_appeal` becomes `base_tourism_appeal_value` less `tourism_heritage_moved`, floored at 0.
  The card's appeal row shows the net, and its tooltip names the points moved to monuments.
  `tourism_fill_base_appeal_pct` reads the net.
- Each listed state's comment in `tourism.txt` gains a short note, e.g. `(50 moved to the Parthenon and Delphi:
  tourism_heritage_generated.txt)`, so a reader of the table sees it. Its value doesn't change.
- The generated file goes in `docs/auto_generated_files.md` and in `scripts/nightly_audit_select.py`'s
  `EXCLUDED_REGISTRY_GLOBS` (the CSV in `INTENTIONALLY_NOT_EXCLUDED`). It isn't a post-load regenerator.
- A test (`test_tourism_heritage.py`): the generated file matches the CSV (`--check`), every monument the CSV names
  exists (landmark, site or wonder), and every CSV state is one `tourism.txt` lists.

States moved: 93. Points moved: 2,320, about 5% of all listed appeal. The unlisted default (20) is unchanged.

### 6.4 Split states

Base appeal applies to the whole state region, so every owner's part loses the points. A monument helps only the part
it stands in. That is right where the monument really is in one part (Giza is Egypt's), and imprecise where a state
is split among many owners. Yemen gets two landmarks (Sana'a in the Zaidi imamate's part, Shibam in the Kathiri
sultanate's), so 20 comes off and each part gets a level-3 landmark. Elsewhere the builder places each monument in
the part that holds it and lists the parts that lose points with nothing back: Rajputana (Jodhpur's and Udaipur's
palaces are below the floor), Central Java, Gonder, Madras, Malwa, the Central Highlands, Khiva, Merz and the
Rhineland.

### 6.5 Side effects

- `tourism_throughput_from_parks` keeps reading the raw score (`base_tourism_appeal_value`), so a National Park's
  bonus doesn't change.
- The map mode that reads appeal (`te_map_modes_events.txt`) is dormant.
- With ruins counted at their dig, several 1836 states open lower than today: Xi'an 55 (from 95), Mexico and the
  Peloponnese 65, Guatemala 70, Yucatán and Crete 75, Ica 60. That is the agreed rule.
- Where an existing landmark gives more than its share, the state opens higher than today: Tuscany 130 (from 100),
  Paris, Constantinople and Beijing about 120, St Petersburg 110, Lebanon 100. That is the monument's tourism value
  beyond its share of the old score, which the 0–100 scale capped.

## 7. The To History dedication

A new dedication, `historic`: `pm_monument_historic` in `grand_monument_pms.txt` and `pmg_grand_monument`, with the
other dedications' wiring (fit triggers, kind, name, loc, ceremony list, panel rows, registry tables).

- **Effects:** tourism (§ 5.1) and the standing grandeur every uncontested monument adds (prestige § 8, cultural
  pull). No national effect of its own, no local effect beyond tourism (no `gm_local_historic`), no interest group
  stance.
- **Fit:** fits every regime, so it is never contested (as To the Nation) and never becomes Heritage. A conquest
  doesn't contest it.
- **Pull Down:** not offered. Demolition from the building panel can't be stopped by script, so a demolished To
  History landmark ends as any landmark does. The play-test list checks how the AI treats it.
- **Rededicate:** unreachable, since only contested monuments can be rededicated.
- **Trophies:** yes, by form share (pieces of structures 25%, tokens 10%), as any monument.
- **Ageing:** as any dedicated, uncontested monument.
- **Upkeep:** none. `gm_upkeep` counts the levels a state's monuments record; it leaves out To History monuments'
  levels, so Petra beside the Mesha Stele pays only for the stele.
- **Monument policy:** its tourism ignores `gm_policy_factor_tourism`. In a state where it stands beside a monument of
  another dedication (Syria, Transjordan), the factor applies to the steps in proportion to the other monuments'
  share of the state's grandeur. The national prestige and cultural pull factor (`gm_policy_factor_standing`) applies
  to the country's total as today (call 12).
- **Who gets it:** new landmarks (Appendix B) and new sites when dug (Appendix C). The ceremony doesn't offer it to a
  player-built monument (call 6).

## 8. Prestige (done in the policy pass)

Every standing monument feeds the country's standing grandeur, and `gm_national_prestige` gives +25 prestige a step on
the open 1/n curve (`gm_set_steps_lin_open`). The new landmarks raise standing grandeur a lot in a few countries. The
owner's change (lower the flat part, add a small percentage) is part of the policy pass (§ 15), and these are its
starting figures: **`country_prestige_add = 10` a step, plus a new `gm_national_prestige_pct` with
`country_prestige_mult = 0.01` a step**.

| Country | Steps now → with new landmarks | Prestige now | At +25 a step | At 10 a step + 1% |
|---|---:|---:|---:|---:|
| Egypt | 7 → 11 | +175 | +275 | +110 and +11% |
| France | 5 → 7 | +125 | +175 | +70 and +7% |
| Ottoman Empire | 6 → 7 | +150 | +175 | +70 and +7% |
| China | 4 → 6 | +100 | +150 | +60 and +6% |
| Persia | 5 → 6 | +125 | +150 | +60 and +6% |
| Russia | 4 → 6 | +100 | +150 | +60 and +6% |
| Japan | 2 → 5 | +50 | +125 | +50 and +5% |
| Spain, Korea | 2 → 4 | +50 | +100 | +40 and +4% |
| a minor with one level-3 landmark | 0 → 2 | 0 | +50 | +20 and +2% |

So phase 2 of this design (the new landmarks) should land after the prestige change, or Egypt's monument prestige
rises from +175 to +275 in the meantime (§ 13).

## 9. New monuments

- **52 new landmarks** (Appendix B): placed in 1836 by `gm_seed_landmarks` with `gm_seed_landmark` (or
  `gm_seed_landmark_beside` where the state already has one: Petra beside the Mesha Stele, Tōdai-ji beside
  Kinkaku-ji), each its own skin `landmark_<key>` with one form, a stand-in picture, a `Landmark(...)` row in
  `test_grand_monument_registry.py`'s `LANDMARKS`, a picture code (append-only), its historical name, and loc. All are
  To History. An owner that proves wrong places nothing and logs it, as today.
- **14 new archaeology sites** (Appendix C): `gm_arch_seed_site` rows and `ARCH_SITES` rows, with the place, find and
  history loc the archaeology rework's events use. To History when dug.
- Existing landmarks and sites are unchanged.

The 1836 owners come from vanilla's state history. Where a state is split, the builder finds the province, as the
landmarks spec did for Jaipur and Lahore.

## 10. Placeholder pictures

Every new landmark shows a stand-in picture until its own exists, as the landmarks spec allows. To keep them visible:

- `test_grand_monument_registry.py` gains `PLACEHOLDER_PICTURES`, the keys of landmarks still on a stand-in. A test
  fails if a landmark without its own picture is missing from the tuple, or if one in it has a picture (so the tuple
  can't go stale either way). It prints the count.
- The art backlog (the icon session's list) gets one line per placeholder.

## 11. Pass 2 and the revisit list

Pass 2 takes townscapes: a representative monument stands for a city's heritage (Prague, Vienna, Venice,
Florence, Paris, Toledo, Bruges, Fez, Kraków, Old Havana), and looting it stands for wider looting. My
keyword scan found about 125 states whose comments rest on an old town.

Appendix D lists the 75 states whose named heritage was under the floor, at first or after the scenery check, and
stays in appeal. Appendix E lists the pilgrimage states, and Appendix F the 14 states where a monument already stands
but the comment credits only the city. All three are kept for pass 2. The CSV in § 6.3 carries them too, as rows with
0 points moved.

## 12. Tests, tools and docs

- Tests: `test_tourism_heritage.py` (§ 6.3); the registry's `LANDMARKS`, `PICTURES`, `PLACEHOLDER_PICTURES`, dedication
  tables and `gm_step_*` pins; `ARCH_SITES`.
- Audits after `/reload`: `loc_coverage`, `modifier_visibility` (the new output modifiers), `script_loc_reference`.
- `organize_loc.py` for the new keys, and CI's `--check`.
- Docs: `docs/systems/mod_systems.md` (Tourism; Grand Monuments: tourism, prestige, To History),
  `extra_building_groups.txt`'s header comment.
- Player guide: `08-states.md` (State tourism: monuments are an output source), `02-timeline.md` (Grand Monuments:
  +10% output a step, To History, the policy table's wording) and the appendix that lists
  landmarks if it does (`20-appendix-reference-lists.md`). Rebuild the PDF.
- Play-test list (`docs/testing/tourism-playtest.md`): the card shows Monuments under output; Giza and Petra stand on
  day one with their names and stand-ins; To History offers no Pull Down; a dug site's tourism arrives.

## 13. Phasing

Each set of moves lands in the same PR as the monuments that take them, so no state loses points with nothing back
in between. The gates (§ 6.3) keep that true for saves already running when a phase ships.

1. **Mechanics and existing coverage:** § 5 (output conversion, vanilla wonders, card, loc) and the moves of the 30
   states in Appendix A whose points go only to existing landmarks, sites and wonders. Moscow moves whole in phase 2.
2. **To History and the new landmarks** (§ 7, Appendix B) with their moves, **after the policy pass's prestige change**
   (§ 8, § 15). Could split by region.
3. **New archaeology sites** (Appendix C) with their moves. It doesn't wait for the prestige change: a site adds
   standing grandeur only once dug.

## 14. Left to the builder

- Each new landmark's owner where the state is split, and its form and stand-in pair (the forms in Appendix B are
  suggestions; Egypt's pyramids want a stand-in that isn't Aztec).
- Each new site's technology and vector, by discovery date, and its loc.
- Loc text for names, descriptions and inscriptions, in the house style.
- The tourism card layout for the Skyscraper row.
- AI weights for To History where the GM AI reads dedications.

## 15. Follow-up: the monument policy and prestige

The owner's notes (2026-10-23), for its own design right after this one:

- **Prestige:** lower the flat prestige a step and add a small percentage a step, so monuments can't by themselves
  turn a minor into a great power and still matter to a large country with a lot of prestige (§ 8 has starting
  figures). The new modifier is one script adds without a duration, so it needs a line in
  `scripts/generators/gen_nation_tab.py`'s registry; the registry test pins `gm_step_prestige` and the new
  `gm_step_prestige_pct`; the play-test checks Egypt's and Persia's rank in 1836–1846.
- **The AI mothballs on any debt** (`gm_policy_ai_choose`, `gm_policy_effects.txt`: hard times or `scaled_debt > 0`).
  It should mothball only in a severe crisis, such as defaulting on its debt or declared bankruptcy.
- **Mothballed only halves upkeep** (`gm_policy_upkeep_mothballed`, `goods_input_construction_mult = -0.5`), while the
  player guide says "No maintenance". It should cut the input to zero.
- **Standard needs a benefit of its own.** The owner nearly always plays Open to the Public or State Ceremonial: the
  upkeep Standard saves is small. In a 1927 game with a GDP of £309M, weekly expenses of £7.4M and 13 monuments, all
  Open and with construction about 40% over its base price, the monuments cost £56k a week (0.8%).
- **Early in the game the same upkeep is large**, because a level costs about the same throughout while budgets grow
  roughly a hundredfold. Weekly spending in a binary save from 1843 (`yemen_1843_10_30.v3`) against today's landmark
  levels at about £100 a level a week:

  | Country | Weekly spending | Levels | Upkeep | Share |
  |---|---:|---:|---:|---:|
  | Greece | £5,400 | 10 (Parthenon) | £1,000 | 18% |
  | Egypt | £80,000 | 30 | £3,000 | 4% |
  | Persia | £40,000 | 15 | £1,500 | 4% |
  | Japan | £59,000 | 5 | £500 | 1% |

  The rework should decide whether upkeep scales down early, for instance with the world-wealth rate that prices
  grandeur (`gm_world_rate_value`).

## Appendices

The tables below come from a judgement pass over all 671 comments (scratch data, to become the CSV in § 6.3).

### Appendix A. Points moved, by state

Old and *New* are base-appeal points; *New* is the score with every moved point gone, which § 6.1 checks against peers with similar scenery and climate. *At start* adds what stands on 1 January 1836; *Later* adds every monument the state will have (sites dug, the Djenné mosque rebuilt). Monuments count on the summed 1/n curve at +10 a step, plus the vanilla wonder's figure. Signature tourism (Antiquity) is left out, and so are two effects on existing political landmarks: they take the monument policy's factor (a solvent AI with a Tourism Industry plays Open, ×1.5; Mothballed is ×0.5), and those built within a century of 1836 grow by ageing (§ 6.2). The figures are at factor ×1 and starting grandeur.

| State | Old | Moved | New | Moved to | At start | Later |
|---|---:|---:|---:|---|---:|---:|
| Attica | 100 | 40 | 60 | 40 to Parthenon (landmark): the Acropolis | 100 | 110 |
| Ile De France | 100 | 30 | 70 | 30 to Arc De Triomphe (landmark): the Arc and Versailles | 120 | 120 |
| Kyoto | 100 | 40 | 60 | 40 to Kinkaku-ji (**new landmark**): Kyoto's temples (Tōdai-ji beside it) | 100 | 100 |
| Lazio | 100 | 40 | 60 | 20 to Vatican City (wonder): St Peter's and the Vatican; 20 to Capitoline Museums (landmark): the Capitol, Colosseum and Forum | 100 | 100 |
| Lower Egypt | 100 | 50 | 50 | 50 to Pyramids of Giza (**new landmark**): Giza and the Sphinx | 100 | 120 |
| Tuscany | 100 | 10 | 90 | 10 to Uffizi Gallery (landmark): the Uffizi | 130 | 130 |
| Upper Egypt | 100 | 50 | 50 | 30 to Obelisks Of Karnak (landmark): Karnak and Luxor; 20 to Deir El Bahari Cache (site): the Valley of the Kings | 90 | 120 |
| Beijing | 95 | 40 | 55 | 20 to Temple Of Heaven (landmark): Temple of Heaven, the Great Wall; 20 to Forbidden City (wonder): the Forbidden City | 115 | 115 |
| Campania | 95 | 30 | 65 | 30 to Pompeii (site): Pompeii and Herculaneum | 85 | 135 |
| Crete | 95 | 20 | 75 | 20 to Palace Of Knossos (site): Knossos | 75 | 115 |
| Eastern Thrace | 95 | 35 | 60 | 15 to Topkapi Palace (landmark): Topkapı; 20 to Hagia Sophia (wonder): Hagia Sophia | 120 | 120 |
| Himalayas | 95 | 20 | 75 | 20 to Swayambhunath (**new landmark**): Kathmandu's temple cities | 95 | 95 |
| Isfahan | 95 | 40 | 55 | 40 to Naqsh-e Jahan Square (**new landmark**): Isfahan's Islamic architecture | 95 | 95 |
| Mexico | 95 | 30 | 65 | 30 to Teotihuacan (**new site**): Teotihuacan | 65 | 95 |
| Peloponnese | 95 | 30 | 65 | 15 to Mycenae Grave Circle (site): Mycenae; 15 to Olympia (site): Olympia | 65 | 125 |
| Provence | 95 | 20 | 75 | 20 to Palais des Papes (**new landmark**): the Papal Palace, Roman ruins | 95 | 95 |
| Sicily | 95 | 20 | 75 | 20 to Valley of the Temples (**new landmark**): Greek and Roman temples | 95 | 95 |
| Xian | 95 | 40 | 55 | 40 to Terracotta Army (site): the Terracotta Army | 55 | 105 |
| Yucatan | 95 | 20 | 75 | 20 to Chichén Itzá (**new site**): Chichén Itzá, Tulum | 75 | 95 |
| Aleppo | 90 | 30 | 60 | 30 to Citadel of Aleppo (**new landmark**): the citadel | 90 | 90 |
| Aydin | 90 | 20 | 70 | 20 to Ephesus (**new site**): Ephesus (Pergamon's site is a gain when dug) | 90 | 120 |
| Cambodia | 90 | 30 | 60 | 30 to Angkor Wat (wonder): Angkor | 90 | 90 |
| Dalmatia | 90 | 20 | 70 | 20 to Diocletian's Palace (**new landmark**): Split and Dubrovnik | 90 | 90 |
| Fars | 90 | 40 | 50 | 40 to Persepolis (landmark): Persepolis and Pasargadae | 90 | 90 |
| Guatemala | 90 | 20 | 70 | 20 to Tikal (**new site**): Tikal | 70 | 90 |
| Ica | 90 | 30 | 60 | 30 to Machu Picchu (site): Nazca, Cuzco, Machu Picchu | 60 | 110 |
| Ingria | 90 | 20 | 70 | 20 to Alexander Column (landmark): St Petersburg's palaces | 110 | 110 |
| Kanto | 90 | 20 | 70 | 20 to Nikko Toshogu (landmark): Nikkō | 90 | 90 |
| Lhasa | 90 | 20 | 70 | 20 to Potala Palace (**new landmark**): the Potala | 90 | 90 |
| Lower Andalusia | 90 | 20 | 70 | 20 to Mezquita of Córdoba (**new landmark**): Moorish Córdoba and Seville | 90 | 90 |
| Syria | 90 | 20 | 70 | 20 to Palmyra (landmark): Palmyra, Krak des Chevaliers | 90 | 90 |
| Transjordan | 90 | 30 | 60 | 30 to Petra (**new landmark**): Petra (with the Mesha Stele beside it) | 90 | 90 |
| Upper Andalusia | 90 | 20 | 70 | 20 to Alhambra (**new landmark**): Granada | 90 | 90 |
| Uzbekia | 90 | 40 | 50 | 40 to Registan (**new landmark**): Samarkand and Bukhara | 90 | 90 |
| Agra | 85 | 40 | 45 | 40 to Taj Mahal (wonder): the Taj Mahal and Agra Fort | 85 | 85 |
| Baghdad | 85 | 20 | 65 | 20 to Ishtar Gate Babylon (site): Babylon | 85 | 115 |
| Central Java | 85 | 20 | 65 | 20 to Borobudur (**new landmark**): Borobudur and Prambanan | 85 | 85 |
| Chiapas | 85 | 20 | 65 | 20 to Tomb Of Pakal (site): Palenque | 65 | 105 |
| Delhi | 85 | 40 | 45 | 40 to Red Fort (landmark): Sultanate and Mughal sites | 85 | 85 |
| Egyptian Desert | 85 | 40 | 45 | 40 to Abu Simbel (**new landmark**): Abu Simbel | 85 | 85 |
| Estremadura | 85 | 20 | 65 | 20 to Jerónimos Monastery (**new landmark**): Belém, Sintra | 85 | 85 |
| Khiva | 85 | 30 | 55 | 30 to Itchan Kala (**new landmark**): walled Khiva | 85 | 85 |
| Languedoc | 85 | 20 | 65 | 20 to Pont du Gard (**new landmark**): Pont du Gard, Nîmes | 85 | 85 |
| Lebanon | 85 | 25 | 60 | 25 to Temples Of Baalbek (landmark): Baalbek, Byblos, Tyre | 100 | 110 |
| Lima | 85 | 20 | 65 | 20 to Caral Supe (site): pre-Columbian sites | 65 | 105 |
| Moscow | 85 | 40 | 45 | 20 to Saint Basils Cathedral (wonder): Red Square; 20 to Moscow Kremlin (**new landmark**): the Kremlin | 85 | 85 |
| Oaxaca | 85 | 20 | 65 | 20 to Monte Albán (**new site**): Monte Albán | 65 | 85 |
| Seoul | 85 | 30 | 55 | 30 to Changdeokgung (**new landmark**): palaces and walls | 85 | 85 |
| Sichuan | 85 | 20 | 65 | 20 to Leshan Giant Buddha (**new landmark**): the Giant Buddha | 85 | 105 |
| Suzhou | 85 | 20 | 65 | 20 to Humble Administrator's Garden (**new landmark**): the classical gardens | 85 | 85 |
| Tunisia | 85 | 20 | 65 | 20 to Amphitheatre of El Djem (**new landmark**): El Djem | 85 | 85 |
| Bangkok | 80 | 30 | 50 | 30 to Grand Palace (**new landmark**): the Grand Palace and temples | 80 | 80 |
| Chugoku | 80 | 20 | 60 | 20 to Itsukushima Shrine (**new landmark**): the floating torii | 80 | 80 |
| Gonder | 80 | 20 | 60 | 20 to Fasil Ghebbi (**new landmark**): the castles of Gondar | 90 | 90 |
| Kiev | 80 | 20 | 60 | 20 to Saint Sophia Cathedral (**new landmark**): churches and monasteries | 80 | 80 |
| Libya | 80 | 20 | 60 | 20 to Cyrene (**new site**): Cyrene | 60 | 80 |
| Madras | 80 | 20 | 60 | 20 to Shore Temple of Mahabalipuram (**new landmark**): Dravidian temples | 80 | 80 |
| Normandy | 80 | 20 | 60 | 20 to Mont-Saint-Michel (**new landmark**): Mont-Saint-Michel | 80 | 80 |
| Rajputana | 80 | 20 | 60 | 20 to Jantar Mantar (landmark): forts and palaces of Jaipur, Jodhpur, Udaipur | 80 | 80 |
| Rhineland | 80 | 20 | 60 | 20 to Marksburg (**new landmark**): the Rhine Gorge castles | 80 | 80 |
| Thessalia | 80 | 20 | 60 | 20 to Meteora (**new landmark**): Meteora's monasteries | 80 | 80 |
| Umbria | 80 | 20 | 60 | 20 to Basilica of Saint Francis (**new landmark**): Assisi | 80 | 80 |
| Yemen | 80 | 20 | 60 | 20 to Old City of Sana'a (**new landmark**): Sana'a | 80 | 80 |
| Zealand | 80 | 20 | 60 | 20 to Liberty Column (landmark): Copenhagen's castles | 80 | 80 |
| Annam | 75 | 20 | 55 | 20 to Imperial City Of Hue (landmark): the Imperial City | 95 | 95 |
| Busan | 75 | 20 | 55 | 20 to Bulguksa (**new landmark**): Gyeongju | 75 | 75 |
| Central Highlands | 75 | 20 | 55 | 20 to Buddhas of Bamiyan (**new landmark**): Bamiyan | 75 | 75 |
| Henan | 75 | 20 | 55 | 20 to Longmen Grottoes (**new landmark**): Longmen, Shaolin | 75 | 75 |
| Middle Egypt | 75 | 20 | 55 | 20 to Temple of Seti I at Abydos (**new landmark**): Abydos (Dendera is the zodiac trophy's origin) | 75 | 85 |
| Mosul | 75 | 25 | 50 | 25 to Nineveh Library (site): Nineveh | 50 | 90 |
| Mysore | 75 | 20 | 55 | 20 to Hampi (**new site**): Hampi (verify its state) | 55 | 75 |
| Orleans | 75 | 20 | 55 | 20 to Château de Chambord (**new landmark**): the Loire châteaux | 75 | 75 |
| Shandong | 75 | 20 | 55 | 20 to Temple of Confucius (**new landmark**): Qufu | 75 | 75 |
| Shanxi | 75 | 20 | 55 | 20 to Yungang Grottoes (**new landmark**): Yungang | 75 | 75 |
| Talinn | 75 | 20 | 55 | 20 to Walls of Tallinn (**new landmark**): the walled city | 75 | 75 |
| Tripoli | 75 | 30 | 45 | 30 to Leptis Magna (**new site**): Leptis Magna, Sabratha | 45 | 75 |
| Ankara | 70 | 30 | 40 | 30 to Hattusa (**new site**): Hattusa | 40 | 70 |
| District Of Columbia | 70 | 20 | 50 | 20 to White House (wonder): the White House | 70 | 70 |
| Diyarbakir | 70 | 20 | 50 | 20 to Mount Nemrut (**new site**): the Nemrut statues | 50 | 100 |
| Dongola | 70 | 30 | 40 | 30 to Pyramids of Meroë (**new landmark**): Meroë | 70 | 70 |
| Gansu | 70 | 20 | 50 | 20 to Mogao Library Cave (**new site**): the Mogao Caves | 50 | 70 |
| Herat | 70 | 20 | 50 | 20 to Musalla of Herat (**new landmark**): Herat's Islamic architecture | 70 | 70 |
| Home Counties | 70 | 20 | 50 | 20 to Windsor Castle (**new landmark**): Windsor, Canterbury, Oxford | 70 | 70 |
| Hyderabad | 70 | 20 | 50 | 20 to Charminar (**new landmark**): Charminar and Golconda | 70 | 70 |
| Khuzestan | 70 | 20 | 50 | 20 to Chogha Zanbil (**new site**): Susa, Chogha Zanbil | 50 | 70 |
| Merz | 70 | 20 | 50 | 20 to Mausoleum of Sultan Sanjar (**new landmark**): Merv | 70 | 70 |
| North Rhine | 70 | 20 | 50 | 20 to Aachen Cathedral (**new landmark**): Aachen and Cologne | 70 | 70 |
| Bundelkhand | 65 | 20 | 45 | 20 to Khajuraho (**new site**): Khajuraho | 45 | 65 |
| Kazan | 65 | 20 | 45 | 20 to Kazan Kremlin (**new landmark**): the Kremlin | 65 | 65 |
| Malwa | 65 | 20 | 45 | 20 to Gwalior Fort (**new landmark**): Gwalior | 65 | 65 |
| Sindh | 65 | 25 | 40 | 25 to Mohenjo Daro (site): Mohenjo-daro | 40 | 80 |
| Western Mali | 60 | 20 | 40 | 20 to Mosque Of Djenne (wonder): the Great Mosque (in ruins in 1836; vanilla's wonder rebuilds it) | 40 | 60 |
| Extremadura | 50 | 20 | 30 | 20 to Roman Theatre of Mérida (**new site**): Roman Mérida | 30 | 50 |

### Appendix B. New landmarks

Owner is the country holding the state's provinces on 1 January 1836 (vanilla history); `?` or a list means the builder places it by province, as the landmarks spec did. Levels are set by the points the landmark takes (§ 6.2), not by its political standing.

| Key | Name | State | Owner | Level | Built | Form | Note |
|---|---|---|---|---:|---:|---|---|
| `pyramids_of_giza` | Pyramids of Giza | Lower Egypt | EGY | 15 | -2560 | pyramid |  |
| `petra` | Petra | Transjordan | EGY | 3 | -100 | rock_cut | beside the Mesha Stele |
| `moscow_kremlin` | Moscow Kremlin | Moscow | RUS | 3 | 1495 | tower | beside St Basil's (vanilla) |
| `fasil_ghebbi` | Fasil Ghebbi | Gonder | ? (state split: QWR 7, BGM 22, AWS 3, TGR 14, GJM 11) | 3 | 1636 | hall | Gondar's part, not Tigray's |
| `valley_of_the_temples` | Valley of the Temples | Sicily | SIC | 3 | -500 | pantheon |  |
| `borobudur` | Borobudur | Central Java | DEI (state split: DEI 9, YOG 1, SRK 1) | 3 | 825 | gate | Kedu was Dutch |
| `old_city_of_sanaa` | Old City of Sana'a | Yemen | ZAI (state split: ZAI 27, HDJ 5, LAH 8, MAH 12, KAT 35) | 3 | 600 | hall |  |
| `shibam` | Shibam | Yemen | KAT (state split: ZAI 27, HDJ 5, LAH 8, MAH 12, KAT 35) | 3 | 1530 | tower | Hadhramaut's part |
| `amphitheatre_of_el_djem` | Amphitheatre of El Djem | Tunisia | TUN | 3 | 238 | forum |  |
| `abu_simbel` | Abu Simbel | Egyptian Desert | EGY | 10 | -1264 | rock_cut |  |
| `temple_of_seti_abydos` | Temple of Seti I at Abydos | Middle Egypt | EGY | 3 | -1290 | colonnade | verify Abydos is in Middle Egypt; Dendera is the zodiac trophy's origin, not this |
| `pyramids_of_meroe` | Pyramids of Meroë | Dongola | EGY | 6 | -300 | pyramid | Ferlini looted them in 1834 |
| `windsor_castle` | Windsor Castle | Home Counties | GBR | 3 | 1070 | tower |  |
| `pont_du_gard` | Pont du Gard | Languedoc | FRA | 3 | 50 | arch |  |
| `palais_des_papes` | Palais des Papes | Provence | FRA (state split: SAR 1, FRA 8) | 3 | 1364 | hall |  |
| `mont_saint_michel` | Mont-Saint-Michel | Normandy | FRA | 3 | 1228 | tower | a prison in 1836 |
| `chateau_de_chambord` | Château de Chambord | Orleans | FRA | 3 | 1547 | hall |  |
| `jeronimos_monastery` | Jerónimos Monastery | Estremadura | POR | 3 | 1601 | hall |  |
| `alhambra` | Alhambra | Upper Andalusia | SPA (state split: SPA 12, GBR 1) | 3 | 1354 | hall | verify Granada's state |
| `mezquita_of_cordoba` | Mezquita of Córdoba | Lower Andalusia | SPA | 3 | 987 | hall | verify Córdoba's state |
| `shore_temple` | Shore Temple of Mahabalipuram | Madras | ? (state split: FRA 1, DEN 1, BIC 23, PUD 1) | 3 | 700 | pillar |  |
| `charminar` | Charminar | Hyderabad | HYD | 3 | 1591 | gate |  |
| `gwalior_fort` | Gwalior Fort | Malwa | ? (state split: IND 9, GWA 19, BHO 2) | 3 | 1486 | gate |  |
| `meteora` | Meteora | Thessalia | TUR | 3 | 1382 | memorial_church | Ottoman until 1881 |
| `citadel_of_aleppo` | Citadel of Aleppo | Aleppo | EGY | 6 | 1213 | gate |  |
| `naqsh_e_jahan_square` | Naqsh-e Jahan Square | Isfahan | PER | 10 | 1629 | hall |  |
| `buddhas_of_bamiyan` | Buddhas of Bamiyan | Central Highlands | ? (state split: KAB 16, HER 7, KAN 4) | 3 | 570 | statue |  |
| `musalla_of_herat` | Musalla of Herat | Herat | ? | 3 | 1417 | tower |  |
| `grand_palace_bangkok` | Grand Palace | Bangkok | SIA | 6 | 1782 | hall | built 1782: ages |
| `changdeokgung` | Changdeokgung | Seoul | KOR | 6 | 1610 | hall | Gyeongbokgung lay in ruins until 1867 |
| `bulguksa` | Bulguksa | Busan | KOR | 3 | 774 | pagoda |  |
| `kinkaku_ji` | Kinkaku-ji | Kyoto | JAP | 6 | 1397 | pagoda |  |
| `todai_ji` | Tōdai-ji | Kyoto | JAP | 5 | 752 | hall | beside Kinkaku-ji |
| `itsukushima_shrine` | Itsukushima Shrine | Chugoku | JAP | 3 | 1168 | gate |  |
| `potala_palace` | Potala Palace | Lhasa | TIB | 3 | 1694 | hall |  |
| `swayambhunath` | Swayambhunath | Himalayas | NEP | 3 | 460 | pagoda |  |
| `leshan_giant_buddha` | Leshan Giant Buddha | Sichuan | CHI | 3 | 803 | statue |  |
| `temple_of_confucius` | Temple of Confucius | Shandong | CHI | 3 | 1499 | hall |  |
| `yungang_grottoes` | Yungang Grottoes | Shanxi | CHI | 3 | 494 | rock_cut |  |
| `humble_administrators_garden` | Humble Administrator's Garden | Suzhou | CHI | 3 | 1513 | pagoda | not the gardens form: that is Naturalist's |
| `longmen_grottoes` | Longmen Grottoes | Henan | CHI | 3 | 675 | rock_cut |  |
| `registan` | Registan | Uzbekia | BUK | 10 | 1660 | gate |  |
| `itchan_kala` | Itchan Kala | Khiva | KHI (state split: KHI 23, KZH 13, TRM 5) | 6 | 1800 | gate | walls of c. 1800: ages |
| `mausoleum_of_sultan_sanjar` | Mausoleum of Sultan Sanjar | Merz | ? (state split: TRM 30, BUK 6, KHI 7) | 3 | 1157 | mausoleum |  |
| `kazan_kremlin` | Kazan Kremlin | Kazan | RUS | 3 | 1562 | tower |  |
| `saint_sophia_kiev` | Saint Sophia Cathedral | Kiev | RUS | 3 | 1037 | memorial_church |  |
| `diocletians_palace` | Diocletian's Palace | Dalmatia | AUS | 3 | 305 | colonnade |  |
| `marksburg` | Marksburg | Rhineland | ? (state split: PRU 4, BAV 2) | 3 | 1283 | tower | Rhine Gorge: Nassau's or Prussia's part |
| `aachen_cathedral` | Aachen Cathedral | North Rhine | PRU | 3 | 805 | hall | Cologne's was unfinished until 1880 |
| `basilica_of_saint_francis` | Basilica of Saint Francis | Umbria | PAP | 3 | 1253 | hall |  |
| `walls_of_tallinn` | Walls of Tallinn | Talinn | RUS | 3 | 1355 | gate |  |

### Appendix C. New archaeology sites

Technology is a first guess from the discovery date; the builder picks it as the archaeology spec does.

| Key | Name | State | Level | Built | Form | Technology (guess) | Discovery |
|---|---|---|---:|---:|---|---|---|
| `ephesus` | Ephesus | Aydin | 3 | -550 | colonnade | empiricism | Wood, 1863-69 |
| `tikal` | Tikal | Guatemala | 3 | 750 | pyramid | romanticism | Méndez, 1848 |
| `chichen_itza` | Chichén Itzá | Yucatan | 3 | 1000 | pyramid | empiricism | Carnegie, 1924 |
| `teotihuacan` | Teotihuacan | Mexico | 6 | 200 | pyramid | empiricism | Batres, 1905-10 |
| `monte_alban` | Monte Albán | Oaxaca | 3 | -500 | pyramid | ? | Caso, 1931 (Tomb 7) |
| `leptis_magna` | Leptis Magna | Tripoli | 6 | 200 | forum | ? | 1920s |
| `cyrene` | Cyrene | Libya | 3 | -630 | pantheon | ? | 1860s, 1910s |
| `merida_theatre` | Roman Theatre of Mérida | Extremadura | 3 | -16 | forum | ? | 1910-15 |
| `chogha_zanbil` | Chogha Zanbil | Khuzestan | 3 | -1250 | pyramid | ? | Ghirshman, 1951-62 |
| `hattusa` | Hattusa | Ankara | 6 | -1650 | gate | ? | Winckler, 1906 |
| `mount_nemrut` | Mount Nemrut | Diyarbakir | 3 | -62 | statue | ? | Sester, 1881 |
| `mogao_caves` | Mogao Library Cave | Gansu | 3 | 1000 | rock_cut | ? | Wang Yuanlu, 1900; Stein, 1907 |
| `khajuraho` | Khajuraho | Bundelkhand | 3 | 1000 | pillar | romanticism | Burt, 1838 |
| `hampi` | Hampi | Mysore | 3 | 1500 | pillar | ? | verify Bellary's state |

### Appendix D. Revisit list (left in base appeal)

Points are the heritage share judged for each; 0 means the scenery check found the old score already left none.

| State | Appeal | Points | What | Why left |
|---|---:|---:|---|---|
| Agra | 85 | 10 | Fatehpur Sikri | the residue after the Taj Mahal's 40 |
| Albania | 75 | 10 | Butrint | below floor (archaeology candidate, 1928) |
| Alentejo | 70 | 10 | megaliths, Évora's temple | below floor |
| Apulia | 80 | 10 | trulli | below floor |
| Arakan | 65 | 10 | Mrauk U | below floor after the scenery check: the coast scores like Tenasserim's |
| Arkhangelsk | 50 | 10 | Solovetsky Monastery | below floor |
| Armenia | 75 | 10 | monasteries (Geghard, Tatev) | below floor |
| Azerbaijan | 75 | 10 | Fire Temple, Gobustan | below floor |
| Bajo Paraguay | 65 | 10 | Jesuit missions | below floor |
| Balkh | 65 | 10 | Bactria, Mazar-i-Sharif | below floor |
| Bavaria | 90 | 10 | Neuschwanstein | built 1869-86: not standing in 1836 |
| Bombay | 75 | 10 | Ajanta and Ellora, Elephanta | below floor; Ajanta and Ellora lie in Hyderabad's lands |
| Brittany | 80 | 10 | Carnac megaliths | below floor |
| Cajamarca | 70 | 10 | Inca Cajamarca, Chan Chan | below floor |
| Cauca | 70 | 10 | San Agustín | below floor (archaeology candidate, 1913) |
| Ceylon | 85 | 10 | Anuradhapura | below floor after the scenery check: beaches and highlands carry the score |
| Chiang Mai | 75 | 10 | temples | below floor |
| Chongqing | 75 | 10 | Dazu Rock Carvings | below floor |
| Colorado | 85 | 10 | Mesa Verde | below floor (archaeology candidate, 1888) |
| Constantine | 70 | 10 | Roman ruins (Djémila, Timgad) | below floor (archaeology candidate) |
| Crimea | 85 | 10 | Bakhchisaray, Chersonesos | below floor |
| Cyprus | 80 | 10 | ancient ruins | below floor |
| Deir Ez Zor | 40 | 10 | Dura-Europos, Mari | below floor after the scenery check: an arid valley scores 30 on its own |
| Eastern Himalayas | 80 | 10 | Tiger's Nest, dzongs | below floor after the scenery check: Himalayan scenery carries the score |
| Eastern Mali | 65 | 10 | Dogon country | below floor |
| East Aegean Islands | 85 | 0 | old Rhodes | below floor after the scenery check: the East Aegean already scores like the Cyclades (85) |
| East Hausaland | 50 | 10 | walled Kano | below floor |
| East Java | 80 | 10 | temple complexes | below floor |
| East Karelia | 60 | 10 | Kizhi Pogost | below floor |
| Erzurum | 65 | 10 | Ani | below floor |
| Fujian | 70 | 10 | Tulou | below floor |
| Gold Coast | 50 | 10 | slave forts (Elmina, Cape Coast) | below floor; coastal parts, not Kumasi's |
| Gonder | 80 | 10 | Lalibela | below floor; may lie in another state |
| Gotland | 65 | 10 | Visby | below floor after the scenery check: Gotland's coast scores like Scania's: its old score left little for Visby |
| Gujarat | 70 | 10 | Indus Valley sites (Dholavira, Lothal) | below floor (archaeology candidates) |
| Guyenne | 75 | 10 | Lascaux | the site already sits in Aquitaine |
| Honduras | 75 | 10 | Copán | below floor after the scenery check: the Caribbean coast and Bay Islands carry the score |
| Istria | 85 | 10 | Pula Arena | below floor after the scenery check: the coast carries the score |
| Kars | 65 | 10 | Ani | below floor |
| Kosovo | 60 | 10 | medieval monasteries | below floor |
| Kurnool | 60 | 10 | notable ruins | below floor; see Hampi |
| Leinster | 70 | 10 | Newgrange | below floor after the scenery check: Wicklow and the Boyne carry the score |
| Maine Anjou | 75 | 10 | Loire châteaux | below floor; Chambord stands in Orléans |
| Malta | 75 | 10 | megalithic temples | below floor after the scenery check: a Mediterranean island scores 60 or more on its own |
| Moldavia | 60 | 10 | painted monasteries of Bukovina | below floor; most lie outside the state |
| Murcia | 75 | 10 | Cartagena | below floor |
| Nakhon Ratchasima | 65 | 10 | Khmer ruins (Phimai) | below floor |
| Nejd | 50 | 10 | Diriyah | below floor; ruined in 1818 |
| New Mexico | 75 | 10 | Chaco Canyon, Taos Pueblo | below floor |
| Ningxia | 55 | 10 | Western Xia tombs | below floor |
| Nizhny Novgorod | 70 | 10 | kremlin | below floor |
| Oman | 70 | 10 | forts (Nizwa, Bahla) | below floor |
| Orissa | 60 | 10 | Konark Sun Temple | below floor after the scenery check: the coast scores like the Circars' |
| Piaui | 50 | 10 | Serra da Capivara paintings | below floor |
| Picardy | 55 | 0 | Amiens Cathedral | below floor after the scenery check: Picardy already scores like the flat plains (50); its cathedral added little |
| Pskov | 65 | 10 | kremlin | below floor |
| Romagna | 80 | 10 | Ravenna's mosaics | below floor |
| Ryazan | 45 | 10 | kremlin | below floor |
| Ryukyu Islands | 85 | 10 | Shuri Castle | below floor after the scenery check: subtropical islands carry the score |
| San Salvador | 70 | 10 | Mayan sites | below floor |
| Sardinia | 80 | 10 | Nuragic ruins | below floor after the scenery check: the coast scores like Corsica's |
| Senegal | 60 | 10 | Gorée | below floor |
| Shengjing | 55 | 10 | Mukden Palace | below floor after the scenery check: Manchuria's neighbours score 45-50 |
| Slovakia | 70 | 10 | castles | below floor |
| Southern Transylvania | 75 | 10 | castles (Bran, Hunedoara) | below floor |
| Syrdarya | 60 | 10 | Yasawi mausoleum | below floor |
| Syria | 90 | 10 | Krak des Chevaliers | the residue after Palmyra's 20; Damascus is townscape |
| Trabzon | 70 | 10 | Sumela Monastery | below floor |
| Tunisia | 85 | 10 | Carthage | below floor after the scenery check: the coast carries the score; El Djem takes the ruins' 20 |
| Turkmenia | 65 | 10 | Merv | below floor; Merv stands in Merz |
| Veracruz | 75 | 10 | El Tajín | below floor |
| Wales | 75 | 10 | castles | below floor after the scenery check: Snowdonia and the coast carry most of the score |
| Western Hubei | 75 | 10 | Wudang temples | below floor |
| West Country | 75 | 10 | Stonehenge | below floor after the scenery check: the coast carries most of the score |
| Xian | 95 | 10 | Big Wild Goose Pagoda | below floor |
| Yaroslavl | 70 | 10 | Golden Ring churches | below floor |

### Appendix E. Pilgrimage, left in base appeal

| State | Appeal | Holy place |
|---|---:|---|
| Hedjaz | 90 | Mecca and Medina |
| Palestine | 95 | Jerusalem |
| Sinai | 80 | Mount Sinai, St Catherine's |
| Awadh | 80 | Varanasi |
| Bihar | 70 | Bodh Gaya |
| Galicia | 70 | Santiago de Compostela |
| Khorasan | 75 | Mashhad |
| Pegu | 70 | Shwedagon Pagoda |
| Ngari | 80 | Mount Kailash |
| Shikoku | 70 | the 88-temple pilgrimage |

### Appendix F. A monument already stands, but the score is townscape (pass 2)

Nothing moves here in pass 1: the comment credits the city, not the monument. The monument is a gain until pass 2 moves the townscape.

| State | Appeal | Monument |
|---|---:|---|
| Maryland | 60 | Washington Monument (Baltimore) |
| Haiti | 75 | Sans-Souci Palace |
| Old Castile | 70 | Arco de Santa María |
| Dahomey | 45 | Royal Palaces of Abomey |
| Benin | 50 | Royal Palace of Benin |
| Rhone | 90 | Statue of Louis XIV |
| Holland | 80 | Tomb of William the Silent |
| Punjab | 75 | Shalimar Gardens |
| Irakajemi | 80 | Golestan Palace |
| Konya | 85 | Xanthos |
| Brandenburg | 65 | Brandenburg Gate |
| Piedmont | 85 | Basilica of Superga |
| Lombardy | 85 | La Scala |
| Venetia | 95 | Lion of Saint Mark |
