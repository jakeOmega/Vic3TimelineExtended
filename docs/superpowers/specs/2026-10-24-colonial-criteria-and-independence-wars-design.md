# Colonial Empire: what a colony is, and fighting to keep one (design)

Date: 2026-10-24. Status: proposal, nothing built. Follows the settler-land fix of the same day (acb6dab: a territory
whose people are more than half of our primary cultures is settled land, neither a colony nor releasable; a release
forms with its largest homeland culture, else its largest culture not ours), which this spec takes as given. Owner
decisions are marked *(owner)*; calls I made are marked *(my call)* and listed in § 9; questions for the owner are in
§ 8, each with a recommendation. Figures are first proposals for the play-test.

## Context

The owner's request (2026-10-24), in their words: "we might want to reconsider what the criteria should be from first
principles, rather than just tweak. For example, North Africa is considered too close to southern Europe currently,
but that means France would treat Algeria as not a colony. Given the Algerian war for independence, that doesn't seem
quite right. Similarly, the colonizer has no opportunity to fight to keep their colonies. It should be hard to win,
but given our real history (e.g. Portugal), it seems like a glaring omission."

What runs today (`docs/systems/mod_systems.md` § Decolonization System, `journal_entry_systems.md` § Colonial Empire,
player guide chapter 12):

- **The colony test.** `is_overseas_colonial_state` (`common/scripted_triggers/colonial_empire_triggers.txt`): not a
  homeland of our primary cultures, at least `colonial_territory_min_population` (100,000) people, one of two
  signals (`colonial_state_indigenous_signal`: a culture not ours over a tenth of the state with average acceptance
  below `acceptance_status_4`, 60; `colonial_state_disparity_signal`: some people not ours and average SoL below 80%
  of the national average), `is_overseas_from_capital`, and `colonial_state_settler_majority = no`. The looser
  `is_decolonization_eligible_state` drops the two signals and decides what the release decisions offer.
- **The geography.** `is_overseas_from_capital` groups the strategic regions into fourteen macro-regions
  (`is_in_colonial_macroregion_*`) and calls a state overseas when it lies outside the capital's macro-region **and**
  every macro-region listed as its neighbour (`is_in_or_adjacent_colonial_macroregion_*`). Western Europe's neighbours
  are Eastern Europe and North Africa, so Algeria, Tunisia, Morocco, Libya and Egypt are never overseas from Paris,
  Rome, Madrid or London. Subjects use the overlord's capital (`is_overseas_from_overlord_capital`) in the protectorate
  branch of `is_qualifying_colonial_subject`.
- **A finding:** the comments promise cases the code rejects. `is_qualifying_colonial_subject`'s header says "UK ->
  Egypt qualifies, France -> Tunisia qualifies", and `je_colonial_empire`'s `possible` comment names "France over
  Tunisia/Morocco"; Egypt (`region_nile_basin`) and Tunisia (`region_north_africa`) are both in the North Africa
  macro-region, a neighbour of Western Europe's, so neither protectorate qualifies.
- **How a colony leaves.** By our choice (Colonial Holdings' Release, `.402`-`.404`; `.400`/`.401`), by an event
  option we choose (`.1`, `.3`, `.9.c`, `.13.a`), by vanilla (a subject's `dp_independence` play; a cultural
  secession), or by force at bar 0 (`on_fail` → `.201` / `.204`: up to three territories picked at random become
  countries at once). The only "fight" a player can pick against a breakaway is `.13.b` (Blood in the Colonies'
  suppression), which adds `colonial_crackdown_modifier` and radicals and fights nothing.

## 1. What makes a territory a colony

### 1.1 First principles

UN General Assembly Resolution 1541 (XV), 15 December 1960, set the test the UN used to decide which territories were
colonies (its formal question: which territories a member must report on under Article 73 e of the Charter). Two of
its principles carry the definition:

- **Principle IV, prima facie.** A territory "which is geographically separate and is distinct ethnically and/or
  culturally from the country administering it".
- **Principle V, confirming.** Once the prima facie case exists, "other elements may then be brought into
  consideration", "of an administrative, political, juridical, economic or historical nature"; where they
  "arbitrarily [place] the latter in a position or status of subordination", it is a colony. (Quoted as I know the
  text; the UN Digital Library has the resolution.)
- Principle VI names the three ways out: independence, free association with an independent state, and integration
  with an independent state. The mod already has all three (Release; Dominion status for a subject; Common Bonds
  making a territory a homeland once all its people are well accepted, which matches Principle VIII's "complete
  equality").

The resolution adopted on the same day, 1542 (XV), applied it to Portugal, which had renamed its colonies "overseas
provinces" in 1951 and declared them part of the nation: the UN held them colonies anyway. France's Algerian
départements (from 1848) are the same case. So a formal incorporation does not end the test; a lack of it is
evidence for it.

The UN's practice read "geographically separate" as separated by sea (the "salt-water" reading). It kept contiguous
land empires (Russia, China, Ethiopia) out of the decolonization agenda. Those empires broke up later by secession,
which vanilla models with cultural secession movements. The mod's system models the 1945-1975 wave and the pressure
that drove it (anti-colonial great powers, the UN regime, liberation contagion), so it should follow the UN's reading
*(my call; § 8 D3 asks the owner)*.

Mapped onto the game: **separate** is a geography test; **distinct** is a culture test; **subordinated** is the two
signals the mod already reads, plus incorporation. The structure of today's strict test (geography + a signal) is
already 1541's. What is wrong is the geography, and a missing distinctness test.

### 1.2 Candidate geography tests against the cases

The verdict each case should get, my reading of 1541 and of what happened:

| Case | Should count | Why |
|---|---|---|
| France-Algeria | yes | Across the Mediterranean, Arab and Berber, war of independence 1954-62; départements did not change it |
| Britain-India | yes | The model case |
| Portugal-Angola, Mozambique, Cape Verde | yes | Res. 1542; wars 1961-74 |
| Netherlands-Indonesia | yes | War 1945-49 |
| Japan-Korea, Taiwan | yes | Annexed 1910 and 1895, across the Korea Strait and the East China Sea; Koreans and Taiwanese distinct |
| Britain-Ireland | no *(arguable)* | A constituent country with seats at Westminster, a short crossing, a people vanilla gives British heritage; its exit (1919-22) was a national rising that vanilla's secession models |
| Denmark-Iceland | no *(arguable)* | A dependency of shared Nordic heritage, separated peacefully (1918, 1944) |
| Russia-Central Asia, Caucasus | no *(arguable)* | Contiguous; the UN never listed them; they left by secession in 1991 |
| China-Tibet, Xinjiang | no *(arguable)* | Contiguous, as above |
| Ottoman Arabia | no | Contiguous provinces; the Arab Revolt was a secession |
| Ottoman Crete | yes *(arguable)* | An island of Greeks under Turkish rule, risings 1866 and 1897; it left through autonomy and union with Greece |
| USA-Philippines, Hawaii, Puerto Rico | yes | Hawaii and Puerto Rico were on the UN's 1946 list; the Philippines became independent that year after a war of conquest (1899-1902) and four decades of rule |
| Spain-Morocco | yes | The Rif War 1921-26; independence 1956 |
| Italy-Libya | yes | Conquered 1911, settled as the "Fourth Shore" |

The candidates, with the regions each case sits in (`scripts/analysis/demographics_strategic_regions.json`, the 1.14
strategic-region map) and the land and strait adjacency in `scripts/analysis/demographics_state_adjacency.json` (the
mod's state regions plus vanilla's `adjacencies.csv` sea crossings):

- **A. Today's test** (outside the capital's macro-region and its neighbours).
- **B. Macro-region only** (drop the neighbours).
- **C. Salt water**: not connected to our capital over land through states we own (straits: § 1.4).
- **D. Distance.** The engine has no distance trigger (`docs/engine/triggers_parsed.txt` has only
  `has_ship_outside_max_port_distance`, for fleets). The only proxy is hops between strategic regions, which is test A
  with finer regions: Korea is in `region_northeast_asia` with Tokyo, so every region-hop proxy calls it home.
  Rejected.
- **E. Subordination only** (no geography: any non-homeland territory with a distinct, subordinated people).

| Case | A today | B macro only | C salt water | E no geography |
|---|---|---|---|---|
| France-Algeria | **wrong** (North Africa neighbours W. Europe) | right | right | right |
| Britain-India | right | right | right | right |
| Portugal-Angola, Mozambique | right | right | right | right |
| Portugal-Cape Verde (`region_southern_europe`) | **wrong** | **wrong** | right | right |
| Netherlands-Indonesia | right | right | right | right |
| Japan-Korea, Taiwan (both in the East Asia macro-region) | **wrong** | **wrong** | right | right |
| Britain-Ireland | right | right | wrong on geography alone; right with the distinctness test (§ 1.3) | depends on acceptance |
| Denmark-Iceland (both `region_northern_europe`) | right | right | as Ireland | depends |
| Russia-Central Asia (`region_central_asia`), Caucasus (`region_greater_persia`) | right | **wrong** (other macro-regions) | right | **wrong** |
| China-Tibet (`region_himalayas`), Xinjiang (`region_central_asia`) | right | **wrong** | right | **wrong** |
| Ottoman Arabia (Constantinople is in `region_balkans`) | right | **wrong** (Middle East ≠ E. Europe) | right | **wrong** |
| Ottoman Crete (`region_balkans`) | not counted | not counted | counted | counted |
| USA-Philippines, Hawaii | right | right | right | right |
| USA-Puerto Rico (`region_central_america`, same macro-region as Washington) | **wrong** | **wrong** | right | right |
| Spain-Morocco (`STATE_AL_RIF`) | **wrong** | right | right (straits rule) | right |
| Italy-Libya | **wrong** | right | right | right |
| Britain-Malta (`region_southern_europe`) | **wrong** | **wrong** | right | right |
| France-Tunisia, Britain-Egypt (protectorates) | **wrong** | right | right | right |

B fixes North Africa and breaks the contiguous empires: Russia, China and the Ottomans would gain the Colonial Empire
entry for their land conquests. E breaks them all, and with no geography every 1836 conquest of a different people
(Austria's Galicia, Persia's Baluchistan) becomes a colony, which drowns what the system is about. **C gets every
intended verdict**, once distinctness keeps Ireland and Iceland out.

The salt-water test's known misses are the contiguous cases the UN did take up or that look colonial: South West Africa
under South Africa, Eritrea under Ethiopia, East Timor under Indonesia (Timor is one island), Western Sahara under
Morocco. Each was a mandate, an annexation or an occupation rather than a colony in 1541's sense, and vanilla's
secession covers the ones that fought.

### 1.3 Recommendation: the test

A territory (state) is a **colony** when all of these hold *(my call, written as 1541's two steps)*:

1. Not a homeland of our primary cultures (unchanged).
2. At least 100,000 people (unchanged, `colonial_territory_min_population`).
3. Not settled land: our primary cultures at most half its people (unchanged, `colonial_state_settler_majority`).
4. **Separated** (new, replaces `is_overseas_from_capital`): not connected to our capital over land through states we
   own; a strait counts as land only between two of our homeland states (§ 1.4).
5. **Distinct** (new): a culture that shares **no heritage trait** with any of our primary cultures is more than a
   tenth of its people (`shares_heritage_trait_with_any_primary_culture`, culture scope, verified in
   `triggers_parsed.txt`; the share is `colonial_state_indigenous_min_share`, 0.1).
6. **Subordinated**, any one of:
   - that distinct culture's average acceptance there is below 60 (today's indigenous signal, now aimed at the
     distinct culture);
   - average SoL below 80% of the national average (today's disparity signal);
   - **the state is unincorporated** (new, `is_incorporated = no`): its people have severely reduced political
     strength, the game's nearest thing to no representation (`vanilla_states_reference.md` § 2).

A territory is **eligible for release** (`is_decolonization_eligible_state`, what Colonial Holdings lists and the
decisions offer) under 1-5, without 6, as the looser test is today.

Why heritage *trait* and not heritage *group* (`shares_heritage_trait_group_with_any_primary_culture`, which the
protectorate branch uses): vanilla's heritage traits are narrow (`vanilla_parsed/common/cultures.json`): Irish and
Australian share `heritage_british` with British, Icelandic shares `heritage_nordic` with Danish, Ryukyuan shares
`heritage_japanese`, Moro, Javan, Sumatran and Bornean all share `heritage_insulindian`. Korean
(`heritage_korean`), Formosan (`heritage_formosan`), Maghrebi (`heritage_arab`), Berber, Melanesian and Maltese
(`heritage_italic`) are each distinct from their colonizer. Groups are broader (the mod reads
`heritage_group_indigenous_american` in `te_vanilla_turtle_island.txt`); the snapshot does not list them, and if
Japanese and Korean share an East Asian group, the group test would drop Korea. The protectorate branch should move to
the trait test too, for one rule *(my call)*.

What distinctness does that the signals cannot: it keeps a poor shared-heritage territory (British Ireland at 75% of
British SoL) from becoming a colony on the SoL signal alone, and it removes multi-island countries' own islands
(Indonesia's Sumatra, the Philippines' Mindanao, Malaysia's Borneo, Japan's Ryukyu) without a hand list.

**Subjects** (`is_qualifying_colonial_subject`): Colonies and Chartered Companies qualify as now. A Protectorate
qualifies when no state of it borders a state linked to the overlord's capital (§ 1.4) and none of its primary cultures
shares a heritage trait with the overlord's. `is_overseas_from_overlord_capital` goes.

### 1.4 In engine terms: the flood fill, straits and the cache

No trigger answers "connected over land through our states" (searched `triggers_parsed.txt`: `has_coastal_access`
asks about a coastal state, `is_isolated_from_market` counts sea routes, `is_land_adjacent_to_state` is country to
state). It has to be computed, and an effect cannot run inside a trigger, so the answer is cached in state variables.

**The fill** (`ce_refresh_separation`, country scope, a new `common/scripted_effects/colonial_geography_effects.txt`).
The `while` ring fill that `form_decolonized_country` and `_decolonization_preview_region` already run
(`common/scripted_effects/decolonization.txt`):

1. Clear last month's `ce_linked` from our states, then mark the capital (value: the country, so a mark left on a
   state that has since changed hands matches no one).
2. `while` some state of ours is unmarked and has a marked neighbour (`any_neighbouring_state`, verified: "Scopes:
   country, state, state_region, strategic_region"), mark every such state.
3. Strait crossings between our homelands (below).
4. Every state of ours left unmarked gets `ce_separated` = the country; every marked one loses it.

The tests read `var:ce_separated ?= owner` (or the owner saved as a temporary scope, if `?=` against a link does not
parse: unverified). A state that changes hands mid-month keeps a value naming its old owner, which no test matches, so
it reads as not separated until the new owner's pass. That errs toward "not a colony" for at most a month.

**Straits.** Vanilla's map has 26 sea crossings (`demographics_state_adjacency.json` → `strait`): Gibraltar
(`AL_RIF`-`UPPER_ANDALUSIA`), the North Channel (`ULSTER`-`LOWLANDS`), the Bosporus
(`EASTERN_THRACE`-`HUDAVENDIGAR`), Messina (`CALABRIA`-`SICILY`), Japan's (`CHUGOKU`-`KYUSHU`, `CHUGOKU`-`SHIKOKU`,
`TOHOKU`-`HOKKAIDO`, `KYUSHU`-`RYUKYU_ISLANDS`, `HOKKAIDO`-`SAKHALIN`), Denmark's (`JUTLAND`-`ZEALAND`,
`SCANIA`-`ZEALAND`, `SCHLESWIG_HOLSTEIN`-`ZEALAND`), Palk (`CEYLON`-`MADRAS`) and others. None joins Japan to Korea,
Sicily to Tunisia or Crete to anything. Whether `any_neighbouring_state` crosses them is **unverified**: the
demographics self-check `neighbouring_state_reads` (`docs/testing/demographics-playtest.md`) logs `strait=0|1` for
exactly this question, and its answer decides which half below the builder writes.

The rule *(my call)*: a strait joins two states only when both are homelands of our primary cultures. Constantinople
then reaches Anatolia (the Ottoman Levant and Arabia stay contiguous), Tokyo reaches Kyushu and Hokkaido, Copenhagen
reaches Jutland, Rome reaches Sicily. A strait does not carry the fill into a territory: Spanish Morocco, Ireland,
Ryukyu and Sakhalin are separated (Ireland and Ryukyu then fail distinctness).

- If the iterator does **not** cross straits (`strait=0`), step 3 is a short list: for each of the 26 pairs, mark the
  far state when the near one is marked and both are our homelands. A test pins the list to the JSON's.
- If it **does** (`strait=1`), the fill would walk from Andalusia into the Rif. A crossing matters only where one side
  can sit in a capital's block and the far side is a distinct people who are not that country's homeland: `AL_RIF`
  (Spain), `CEYLON` (India), `SAKHALIN` (Japan) and `WEST_INDIES` (Venezuela). Ulster, Ryukyu, the Moluccas and North
  Borneo fail distinctness anyway. Each of the four needs its partner excluded in step 2; a state variable naming the
  partner region, set at game start, is one way. If the owner prefers, accept that Spanish Morocco reads as contiguous
  under `strait=1` (§ 8 D5).

**When it runs.** Monthly, from `on_monthly_pulse_country`, for every country that owns a non-homeland state of
100,000 people or more or holds a protectorate (a cheap prefilter; the protectorate test reads the overlord's marks),
and from `on_game_started`. Not only for countries with the
decolonization technology: `law_littoral_defense` and `law_auxiliary_fleet`'s AI weights
(`common/laws/extra_laws.txt`), `ideology_anti_colonialist_leader` (`common/ideologies/extra_ideologies.txt`) and
`un_vote_events.txt` read `is_overseas_colonial_state` for any country at any date.

**Cost.** I ran the fill offline over the adjacency snapshot for test-case empires (a script over the two JSON files;
neighbour tests per fill, one pass):

| Empire | States | Rings | Neighbour tests |
|---|---|---|---|
| Spain with the Rif | 15 | 3 | 96 |
| Britain with Ireland and Malta | 14 | 4-6 | ~100 |
| Japan with Korea and Taiwan | 18 | 3-5 | 94-157 |
| France with North Africa | 28 | 3 | ~295 |
| Ottoman Empire with Crete, Arabia, Libya | 29 | 2-8 | 337-537 |
| China with Tibet and Xinjiang | 42 | 6 | 721 |
| USA with Hawaii, Puerto Rico, the Philippines, Alaska | 55 | 7 | ~1,000 |
| Russia to the Pacific, Central Asia and the Caucasus | 89 | 7 | ~1,900 |

The engine's `while` evaluates its limit and then the `every_scope_state` with the same limit, so double these:
about 4,000 cheap tests a month for the largest empire, and under 30,000 a month for the world, most countries being
small. Against that, one call of today's `is_overseas_from_capital` runs up to fourteen capital-region tests and one
neighbour list of up to five macro-regions, some fifty `region =` comparisons, and the bar alone calls the colony test
for every state about a dozen times a month (the colony, acceptance and overreach counts, each three times through the
monthly cap). A 60-state empire spends some 36,000 region comparisons a month there; the cache turns each into one
variable read. Putting the cached read second in `is_overseas_colonial_state`, before the pop walks of the signals and
the settler test, also skips those walks for every contiguous state. The change should cost less than today.

**Callers.** Every reader of `is_overseas_from_capital` in the colony tests switches: `is_overseas_colonial_state`,
`is_decolonization_eligible_state`, `colonial_state_high_acceptance`, the `.201` / `.204` marking limits, and
`is_qualifying_colonial_subject`. `building_wonder_continental_union_hq` (`common/buildings/wonders.txt`) reads
`is_overseas_from_capital = no` to mean "on the capital's continent", a different question that the macro-regions
answer well: it keeps the old trigger, renamed `is_on_capital_continent` or left with a comment *(my call)*.

### 1.5 What it changes

Holdings in 1836 are from vanilla's history as I know it (not in the repo; the debug census in § 3 confirms them in
game). The entry needs the decolonization technology (era 6), so "at game start" means what a country would hold the
entry for if it kept its 1836 possessions into era 6.

| Country | Territory | Today | Proposed | Note |
|---|---|---|---|---|
| France | Algiers, Oran, Constantine | not colonies | colonies | France starts with a foothold in Algeria (confirm in the census); the owner's case |
| France | Tunisia, Morocco as protectorates | not colonial subjects | colonial subjects | the comments already promised this |
| France | Corsica | not a colony | **check** | Corsican is `heritage_italic`; depends on whether history makes Corsica a French homeland (not in the repo) |
| Britain | Malta, the Ionian Islands | not colonies | colonies when 100,000+ | Malta is in Southern Europe (Western Europe's own macro-region), the Ionian Islands in the Balkans (a neighbour) |
| Britain | Egypt as a protectorate | not a colonial subject | colonial subject | Suez's metropole |
| Britain | Ireland | not a colony | not a colony | shares `heritage_british` |
| Britain | Australia, New Zealand held directly | eligible for release | not eligible unless Aborigines or Māori are a tenth | shared heritage; they leave by vanilla's release or as dominions |
| Spain | the Rif, Spanish Sahara | not colonies | colonies (Sahara rarely reaches 100,000) | under the straits rule |
| Spain | Cuba, Puerto Rico, the Philippines | colonies | colonies | no change |
| Portugal | Cape Verde | not a colony | a colony once 100,000+ (about 1900-1940) | Angola, Mozambique, Goa, Timor unchanged |
| Italy | Libya, Albania | not colonies | colonies | Eritrea, Somalia, the Dodecanese unchanged |
| Japan | Korea, Taiwan | not colonies | colonies | Ryukyu stays out (shared heritage); Karafuto is settled land |
| USA | Puerto Rico, Cuba | not colonies | colonies | the Philippines and Hawaii unchanged; Alaska separated but under 100,000 until late |
| Ottoman Empire | Crete, Cyprus, Libya | not colonies | colonies, if still held in era 6 | the Levant, Iraq and Arabia stay contiguous |
| Russia | Central Asia, the Caucasus | not colonies | not colonies | contiguous |
| China | Tibet, Xinjiang, Mongolia | not colonies | not colonies | contiguous |
| Denmark | Iceland | not a colony | not a colony | shared heritage; Greenland under 100,000 |
| Australia (as a country) | Eastern New Guinea | not a colony (Southeast Asia neighbours Oceania) | a colony | the UN trust territory of Papua New Guinea |
| Indonesia (as a country) | Western New Guinea | not a colony | a colony if subordinated | Melanesian; a real dispute (1962-69, the "Act of Free Choice"); § 8 D2 |
| Philippines, Malaysia, Indonesia | their other islands | not colonies | not colonies | shared heritage |

Who gains the entry in era 6: France (if Algeria was its only colony left), Japan, Italy, Spain and the United States
in the situations above, the Ottomans in an alternate world where they kept their islands, Australia and an
independent Indonesia. Who loses it: almost nobody; a country whose only holding is a shared-heritage settler land
held directly. The naval laws' AI weights shift with it: a major power whose only colonies are newly counted ones
(Italy with Libya) gains Auxiliary Fleet's weight and loses Littoral Defense's.

## 2. Fighting to keep a colony: the war of independence

### 2.1 What history asks for

| War | What the design should reproduce |
|---|---|
| Algeria 1954-62 | The army won the field (the Challe offensives broke the guerrillas inside Algeria by 1960) and France still lost. A million settlers made it the hardest colony to give up. The war brought down the Fourth Republic (May 1958); de Gaulle negotiated the Évian Accords (March 1962) |
| Portugal 1961-74 | An autocracy with censorship fought three wars at once for thirteen years. The officers who fought them overthrew the regime (the Armed Forces Movement, 25 April 1974), and every African colony was independent by the end of 1975 |
| Indonesia 1945-49 | Two Dutch offensives (1947, 1948) took the cities; American pressure and the Security Council forced the Round Table Conference at The Hague and the transfer of sovereignty (December 1949) |
| Kenya 1952-60, Malaya 1948-60 | Britain defeated both insurgencies, then granted independence anyway (Malaya 1957, during the Emergency; Kenya 1963) |
| Indochina 1946-54 | Defeat in the field (Dien Bien Phu), then Geneva |

So: (1) winning is possible, mostly by outlasting rather than by occupying; (2) winning buys years, not a solution;
(3) a long war breaks governments at home, autocracies included; (4) foreign backing and diplomatic pressure count as
much as battles; (5) settler colonies are fought for hardest; (6) a negotiated end mid-war beats defeat.

### 2.2 When a colony moves to break away

**A directly held territory declares independence** in a new event, **`.70` "Declaration in [territory]"**, fired:

- **From the event pool**, when the bar is below 40 (Under Pressure or Crumbling) and the territory is a colony with
  severely unaccepted people (a pop below acceptance 20, the test `.9` and `.13` use). Weight 20 below 40,
  40 below 20, against the pool's 900 of nothing *(my call)*. The territory picked is the one most likely to rise
  (§ 2.8's order). A territory that declared, or was reconquered, waits ten years (`decol_declared` on the state, 3650
  days), and the country waits two years between declarations outside a collapse.
- **From `.13` "Blood in the Colonies"** when the bar is below 40: its suppression is then the fight. At 40 or above
  `.13` keeps its three options; its suppression stays a police action (the crackdown) and no war is offered,
  because there is no declaration to fight.
- **From the collapse at 0** (§ 2.9).

The band is when a colony declares, not who may fight: once offered, Fight has no gate (owner default "soft caps").
Nothing here rewards switching a setting off and on (owner default "avoid micromanagement"): a declaration follows
the band and the territory's people, not a programme or a law; the home front counts the war-years of every war
together, so conceding one war does not reset the others; the ten-year wait belongs to the territory.

**A colonial subject** already fights for independence through vanilla: at high liberty desire it may start
`dp_independence` against us, and vanilla's play lets the overlord back down (concede) or let it come to war (fight).
The mod pushes subjects' liberty desire by band already. What is missing is only the treatment of that war as a
colonial war (§ 2.5 for subjects). Scripting a subject's declaration is left out: `dp_independence`'s `possible`
wants `can_increase_autonomy = no` or a refused autonomy request, and whether a scripted `create_diplomatic_play`
honours it is unverified *(my call; § 8 D14)*.

### 2.3 The choice: concede, negotiate or fight

`.70` names the territory, the people who would form the country (the `.402` preview: `decol_choose_release_culture`
and `_decolonization_preview_region`), whether settlers live there (our share), and what each option costs.

| Option | What happens |
|---|---|
| **Concede** (default) | `.13.a`'s release, unchanged: the country forms now, Colonial War Exhaustion, the Armed Forces disapprove, the Intelligentsia approve, five months of +1 stability |
| **Negotiate** | `.402.b`'s Round Table release (`decolonization_path_round_table`, so relations +25; `decol_chosen_release_rewards` with twelve months of +1 stability; the Intelligentsia approve, the Landowners disapprove); under Neocolonialism `.13.c`'s neocolonial terms instead. No authority threshold: it costs 100 authority, easing over a year (`country_authority_cost_add`, decaying), so it is a cost, not a gate *(my call)*. The Round Table's own acceptance gate (no severely unaccepted people) is waived: the declaration is the partner |
| **Fight** | The rebels form as a country and we go to war with them at once (§ 2.4) |

A release as a Protectorate (Principle VI's free association, the Netherlands-Indonesian Union of 1949, the Irish Free
State as a dominion in 1922) would be a fourth way, via `create_diplomatic_pact` with a subject type after the
create; whether that works from an event is unverified, so it is § 8 D8.

### 2.4 The war in engine terms

**Recommended: the metropole opens a war of reconquest against a rebel country** *(my call)*.

1. **The rebels form** through `form_decolonized_country`, with a flag on us (`decol_iw_forming`) that makes
   `apply_decolonization_path` defer the aftermath: no `decol_mark_former_colony` (no post-independence events mid-war),
   no legacy laws or relations, no `.15` until the war is lost (§ 2.6). Liberation contagion still fires: the
   declaration is what inspires. The rebels get `decol_collapse_grace` and the fighters' package (§ 2.5).
2. **The war starts the next day** (a hidden `.71` on us), so the new country is settled before a play targets it:
   from our scope, `create_diplomatic_play = { type = dp_te_colonial_war target_country = <rebels> war = yes
   escalation = 100 }` (the form `nuclear_exchange_effects.txt` uses for `dp_nuclear_exchange`; `initiator =` is
   rejected, `scripting_best_practices.md`).
3. **`dp_te_colonial_war`** (new, `common/diplomatic_plays/`): `war_goal = te_colonial_reconquest`,
   `requires_interest_marker = no`, `add_infamy_for_starting_initiator_wargoals = no`, neither side may add war goals,
   `selectable_in_lens = { always = no }`, `possible` only against our own rebels (they hold `decol_iw_metropole` =
   us). Negotiated peace stays allowed: a white peace is independence.
4. **`te_colonial_reconquest`** (new, `common/war_goal_types/`): `kind = annex_country` with `te_reunify_country`'s
   settings, infamy 0, `valid` while the rebels still hold `decol_iw_metropole` = the holder and talks have not
   conceded (§ 2.6). **No `mirrored_wargoal` block**, so it never self-enforces by occupation (`vanilla_war_reference.md`
   § 13): holding the territory does not end the war, only the rebels' capitulation or a peace does. That is the
   guerrilla war in one line. `on_enforced` records the win on the holder.

Alternatives considered:

- **The rebels as initiator**, vanilla's Sepoy Mutiny shape: `dp_sepoy_mutiny` (`annex_country`,
  `allow_negotiated_peace = no`) is a play the rebels open against the colonial state, and `je_sepoy_mutiny` completes
  when the rebel tags are dead (`vanilla_parsed/common/diplomatic_plays.json`, `journal_entries.json`; the event that
  creates them is not in the snapshot). For us the rebels' goal would have to be something other than annexing France.
  The metropole as initiator gives the AI a goal to pursue, which an AI defender does not press.
- **An engine secession** (`dp_secession`, the hooks in `te_civil_war_on_actions.txt`, `decol_fighting_colonial_war`
  already counts it). The engine would split the states and raise the armies itself, and a crushed secession is
  annexed back by the engine. But no effect starts one: there is no civil-war effect, movements' activism cannot be set,
  and `add_civil_war_progress` needs a civil war already brewing (`effects_summary.txt`). Vanilla's own cultural
  secessions in colonies stay as they are, and § 2.5 treats them as colonial wars.
- **`annex_as_civil_war = yes`** on the play (a `create_diplomatic_play` field vanilla uses,
  `scripting_best_practices.md` § diplomatic plays): a reconquest would then merge the rebels with a civil war's
  inheritance (buildings, pops). Worth a try in the play-test; unverified what it changes for a non-civil war.

The rebels need an army. A new dynamic country inherits the territory's barracks levels with the states but no
formations, and the AI must build them. The package below doubles conscription and speeds training (vanilla's
`native_conscription_*` and `modifier_kenesary_revolt` shapes); `create_military_formation` (an engine effect,
`effects_summary.txt`) could seed one army, syntax unverified. Our own formations in the colony at the declaration
either stay on the new front or are pulled to another headquarters: unverified, a play-test entry.

### 2.5 Making it hard

| Lever | What | Engine form |
|---|---|---|
| The rebels fight like guerrillas | Morale loss −50%, defence in their own provinces +50%, provinces lost after a defeat −65%, conscription ×2, training +50% | `decol_iw_fighters_modifier` on the rebels while the war runs: `unit_morale_loss_mult`, `battle_defense_owned_province_mult`, `unit_provinces_lost_mult`, `state_conscription_rate_mult`, `building_training_rate_mult` (all in `modifiers_summary.txt`; vanilla's `caucasus_war_defender_circassia` and `modifier_kenesary_revolt` carry the same set) |
| Occupation does not win | The goal does not self-enforce | no `mirrored_wargoal` (§ 2.4) |
| The rebels keep fighting | "Fighting for independence" +0.5 war support a beat; "Foreign arms" +0.25 while a backer arms them | lines in `zz_te_war_support_injections.txt`, the mod's hook into vanilla's `war_support_from_journal_entries` (`mod_systems.md` § War Support Feeds); conditions are `has_modifier` reads |
| The home front tires | "A war to keep a colony" −0.25 a beat; "The world condemns it" −0.25 when the condemners hold a third of great-power prestige, −0.5 at two thirds (the cached `colonial_empire_condemner_share`); "Settlers to defend" +0.25 while our people are a tenth or more of the territory | the same file, on us |
| The bar drains | −0.5 a month per running war, on top of the existing at-war −0.5 | a new leaf `colonial_stability_term_independence_war` in the domestic group (`colonial_empire_values.txt`), a line in `colonial_stability_bar`, a row in `mod_systems.md`'s formula table; the monthly cap still applies |
| Legitimacy and the interest groups | −2 legitimacy per year of war, up to −10, counted over all running wars; each year the Intelligentsia and Trade Unions disapprove; the Armed Forces approve for two years, then disapprove (they blame the politicians) | `decol_iw_home_front_modifier`, re-applied each month at multiplier = war-years summed (remove, then add: one refresh site); `ig_approval_effect` yearly |
| The world takes sides | Anti-colonial great powers condemn, arm the rebels or intervene (§ 2.7) | phase 3 |
| More wars, more strain | No cap on the number of wars a player may choose; each one adds its drain and its war-years | three record slots (§ 2.10) |

Calibration targets for the play-test, not formulas *(my call)*: vanilla war support drifts toward 50 and its
duration term already grinds both sides, so the asymmetric lines are small. A democracy with free speech, no settlers
and condemned by a third of the great powers should reach the red band (25 and below) in four to six years; an
autocracy with censorship and settlers should last eight to twelve, as Portugal did. A great power with a strong army
against one unbacked rising should win about a quarter of the time; against a backed one, rarely; a minor power
fighting two at once, almost never.

**Subjects and secessions count too.** An independence war a colonial subject wages against us, and a secession by a
people sharing no heritage with ours, are colonial wars by `decol_fighting_colonial_war` already. They get the bar
term, the home-front lines and the rebels' lines (the subject or the secessionist carries the fighters' package while
at war with us), and their outcomes (§ 2.6) read `on_become_independent` and the secession hooks
(`te_civil_war_on_secession_end`) *(phase 3)*.

### 2.6 How it ends

| Ending | How the game knows | We get | The territory and the rebels |
|---|---|---|---|
| **We win**: the rebels capitulate | `te_colonial_reconquest`'s `on_enforced`; backed up monthly by the recorded capital state being ours again | `.72` "Order Restored": twelve months of +1 stability; twelve months added to the Garrison counter (the ending leans to The Iron Fist); the Armed Forces approve, the Intelligentsia disapprove | Back to us, radicalized (`add_radicals_in_state`, large), `decol_declared` for ten years. Its people are as unaccepted as before, so the bar's terms return with it: the win buys time |
| **We lose**: we capitulate, or a white peace | The war is over (no war with the recorded rebels) and they are alive and hold the capital state | `.73` "The Flag Comes Down": `decol_iw_lost_modifier` (prestige −15%, legitimacy −10, both decaying over five years), the Armed Forces strongly disapprove for three years (the veterans' protest `.54` gains weight), twelve months of −1 stability (the loss emboldens the rest) | The deferred aftermath runs: `decol_mark_former_colony`, the Bloody Decolonization legacy (relations −50, whatever programme we ran: a war of independence is a bloody exit), `.15` a week later |
| **Talks** (phase 3): Évian | We opened talks from the panel or an event, six months passed, the goal is dropped and the rebels accept a white peace | as a loss, but legitimacy −5, no Armed Forces penalty beyond the year, no −1 stability months | The legacy of our longest programme instead of Bloody (relations as `apply_decolonization_path` gives them), and the Neocolonial terms if we hold the law |

**Talks in engine terms.** No effect makes peace (`effects_summary.txt` has `end_play` for plays and nothing for
wars). Talks set `decol_iw_conceded` on the rebels, which makes `te_colonial_reconquest`'s `valid` false so the
engine drops the goal; with no goals left against them the AI rebels should accept a white peace, and a player sends
one through the peace screen. Both halves are unverified: a self-check (§ 2.12).

### 2.7 The world takes sides (phase 3)

Each great power with `gp_anti_colonial_stance` (set by `.14`) gets **`.74` "War in [territory]"** when a war starts:

| Option | AI weight | Effect |
|---|---|---|
| Condemn (default) | base 5 | Relations −20 with us. Its condemnation already counts on the bar and in "The world condemns it" |
| Arm the rebels | base 2, +3 if it is our rival, +2 if it has 50% more army power projection than the rebels need | The rebels take `decol_iw_foreign_arms_modifier` (offense and defence +10% per backer, up to three: vanilla's `polish_rebel_funding_modifier` and `patagonia_supplied_with_weapons` are the precedent) and the "Foreign arms" war-support line; the backer pays a monthly sum moved to the rebels' treasury (`add_treasury` on both) while the war lasts; relations −30 with us |
| Intervene | base 0, +2 if it is our rival and its army power projection exceeds ours | Joins the war on the rebels' side (`join_war`, the form `nd_guarantor_join_war` and `ww_enter_war_on_defender_side` use) |
| Stay out | base 2 | Nothing |

A great power without the stance, or with `gp_pro_colonial_stance`, may offer us arms (`.74`'s mirror, a smaller
package) but never joins. The UN's Binding Ceasefire and the decolonization regime could take up a colonial war; left
for later.

**The home front breaks** (phase 3). When a war of independence has run 48 months and our war support in it has been
25 or below for 12 consecutive months (a monthly counter on the record, read with `has_war_support`, war scope,
verified), **`.75`** fires:

- Without a voting law, **"The Captains' Revolt"** (Portugal 1974): *step aside*: talks open on every war at once,
  `colonial_empire_effect_planned_decolonization` frees the rest, and the government changes (a strong version
  activates a parliamentary law with `activate_law`, as `apply_decolonization_path` does; § 8 D11); or *crush the
  officers*: legitimacy −20 for two years, large radicals among officers and soldiers, and the event returns a year
  later.
- With one, **"The Republic in Danger"** (France 1958): *call the general*: a presidential law with `activate_law`,
  +authority for three years, and talks become possible with no legitimacy cost; or *hold the line*: legitimacy −15,
  the Armed Forces disapprove.

### 2.8 The AI

**At `.70`** *(my call)*:

| Option | Base | Modifiers |
|---|---|---|
| Concede | 4 | +4 not a great power; +3 per condemning great power (up to +9); +4 at war with anyone else; +3 bar below 20 |
| Negotiate | 3 | +3 a voting law; +2 Neocolonialism |
| Fight | 1 | +4 great power; +3 Armed Forces powerful; +3 our people a tenth or more of the territory; +2 no voting law; +2 Garrison at level 2 or more; −2 per war already running; 0 in default or at war with a great power |

That gives an autocratic great power with settlers, a strong army lobby and no condemners about two chances in three
to fight, and a democratic great power with no settlers and two condemners about one in four.

**Which territory rises first** (the pool's pick and the collapse's order): the most severely unaccepted share of
people first, then the largest *(my call)*: `ordered_scope_state` with `order_by` (verified) over a per-state value.

**In the war** the engine runs both sides. Two risks for the play-test: whether the AI sends an army across the sea at
all (it has to, for every case this system is about), and whether the AI rebels capitulate too early despite the
war-support lines (1.14.5's capitulation desire floors civil wars, secessions and native uprisings, not a dynamic
country).

### 2.9 Collapse becomes a wave

At bar 0 the entry still fails, and `.201` / `.204` keep their endings (Colonial Empire Collapsed or Negotiated
Withdrawal, the ten-year lockout, the subjects' aftershock). Their option no longer releases three random territories at
once *(owner's suggestion)*: it picks up to three by § 2.8's order and fires `.70` for each, at 0, 60 and 120 days.
Each offers concede, negotiate or fight; the AI's weights already lean to concede at bar 0 (+3) and when other wars run
(+4, then −2 per war on Fight). A player who concedes all three gets what happens today, in a sequence. The declarations
need no entry, only that the territory is still ours and a colony.

### 2.10 Records, revolutions and old saves

The wars live in variables on us, three slots *(my call: Portugal fought three)*: `decol_iw_rebels_<n>`,
`decol_iw_state_<n>` (the rebels' capital, for the ownership checks and for the panel, gotcha #11),
`decol_iw_months_<n>`, `decol_iw_red_months_<n>`, `decol_iw_talks_<n>`; the rebels hold `decol_iw_metropole`. A
fourth declaration while three wars run offers concede and negotiate only. That is a storage limit on a rare state,
not a rule a player plans around; five slots cost nothing more if the owner prefers (§ 8 D9).

The monthly settle (`decol_iw_monthly`, from `decolonization_events_on_action` before its pool, so it runs whether or not
the entry is active: a war can outlast a failed entry) checks each slot, counts months, and re-applies the home-front
modifier: its one refresh site. A revolution's winner inherits the variables but not the modifiers
(`scripting_best_practices.md` § What a Civil War's Winner Inherits), so the next settle rebuilds them, and
`decol_repair_after_civil_war` (from `te_civil_war_on_won`) calls it at once. Whether the winner is still at war with
the rebels after a revolution is unknown: a record whose war has ended while the rebels live settles as a loss.

Old saves hold no records and no cache: the first monthly pass fills the cache; nothing else is needed.

### 2.11 What the player sees

- **`.70`**, with the options' costs in their tooltips (`custom_tooltip` where a variable moves, per
  `silent_variable_audit`).
- **Colonial Holdings** gains a "Wars of Independence" block above the territories: a row per war (the rebels' name
  through the stored capital state, months, our war support in it if a GUI getter reads it (unverified, else left out),
  backers, an Open Talks button in phase 3).
- **The bar's hover** gains the new term; the panel's "why stability is moving" groups it under domestic.
- **Notices** to us, the rebels and the great powers when a war starts and ends.
- **The colony test's hovers** (`IS_OVERSEAS_COLONIAL_STATE_TT`, `IS_DECOLONIZATION_ELIGIBLE_STATE_TT` in
  `te_miscellaneous_l_english.yml`, the Colonial Holdings row hovers) state the new test in the player's terms:
  "not joined to our capital by land through our own states", "a people sharing no heritage with ours".

### 2.12 Engine facts to verify

| Fact | Check | If it fails |
|---|---|---|
| `any_neighbouring_state` crosses straits | The existing `TE_SELF_CHECK neighbouring_state_reads` (`strait=0|1`) | Build the matching half of § 1.4 |
| `var:x ?= owner` compares a stored country with the owner | Static parse plus the debug census | Save the owner as a temporary scope first |
| A play created the day after the rebels form becomes a war | `TE_SELF_CHECK OK|BROKEN decol_iw_war_started` seven days after Fight: we `has_war_with` the rebels | Create it from the rebels' scope (the Sepoy shape) |
| The rebels raise an army | `TE_SELF_CHECK decol_iw_rebels_armed` sixty days in: `has_military_formation` or `any_military_formation` on the rebels | Seed one with `create_military_formation` |
| Our formations in the colony stay on the front | Play-test entry | Accept: the war opens with a landing; say so in the guide |
| The AI lands troops overseas | Play-test entry: a fast AI run with an AI France facing an Algerian declaration | Give the AI metropole's `ai_chance` a heavier lean to concede when its navy cannot reach (a script value of the colony's sea access) |
| `on_enforced` sees the rebels before the annexation | Logged when a reconquest is won | The monthly ownership check alone |
| A dropped goal ends the war in a white peace | `TE_SELF_CHECK decol_iw_talks_peace`: war over within six months of `decol_iw_conceded` | Talks end the war by the player's peace offer only; the AI's talks just lower the drain |
| `create_diplomatic_pact` makes a released territory a protectorate | Only if D8 is taken | Drop the option |

Each self-check is a once-a-game `debug_log` with the numbers, skips degenerate cases (no declaration yet), and goes
in a new `docs/testing/colonial-wars-playtest.md` with its fallback, per the owner's rule on in-game checks.

## 3. Phasing

**Phase 1: the colony test.** Ships alone; no war.

- `common/scripted_triggers/colonial_empire_triggers.txt`: `is_separated_from_capital`,
  `colonial_state_distinct_people`, the signals aimed at the distinct culture, the unincorporated signal; rewire
  `is_overseas_colonial_state`, `is_decolonization_eligible_state`, `colonial_state_high_acceptance`,
  `is_qualifying_colonial_subject` (and fix its comment); `is_overseas_from_capital` kept for the wonder;
  `is_overseas_from_overlord_capital` removed.
- New `common/scripted_effects/colonial_geography_effects.txt`: `ce_refresh_separation` and the strait list.
- `common/on_actions/extra_on_actions.txt` (or a new `colonial_geography_on_actions.txt`): the monthly pass and the
  game-start pass.
- `events/decolonization_events.txt`: the `.201` / `.204` marking limits read the eligible test.
- `common/script_values/colonial_empire_values.txt`: the panel's hover values if they restate the test.
- `localization/english/te_miscellaneous_l_english.yml` (the `IS_*_TT` lines) and the Colonial Holdings hovers.
- `events/te_debug_colonial_empire_events.txt`: `te_debug_colonial_empire.4`, a census logging every country's
  separated, distinct and colony states under the new test, for the play-test and for § 1.5's table.
- Tests: the strait list against `scripts/analysis/demographics_state_adjacency.json`, the callers, the wonder's
  trigger left alone.
- Docs: `mod_systems.md` § Decolonization System, `journal_entry_systems.md` § Colonial Empire.
- **Player guide, chapter 12**: the definition under "The Colonial Empire journal entry" (the bullet list and the "The
  regions in that test are large ones" paragraph), the eligibility sentence in "Releasing colonies", and the
  protectorate clause. Rebuild the PDF.

**Phase 2: wars of independence for directly held territories, and the wave.**

- `events/decolonization_events.txt`: `.70` (declaration), `.71` (hidden, starts the war), `.72` (won), `.73`
  (lost); `.13` split at bar 40; `.201` / `.204` fire the wave.
- `common/scripted_effects/decolonization.txt`: the deferral flag in `form_decolonized_country` /
  `apply_decolonization_path`, `decol_iw_start`, `decol_iw_monthly`, the settle and repair effects; the civil-war repair
  hook.
- New `common/diplomatic_plays/te_colonial_war_play.txt` and `common/war_goal_types/te_colonial_reconquest.txt`.
- `common/script_values/zz_te_war_support_injections.txt`: the five lines, with `WAR_SUPPORT_TE_*` loc.
- `common/script_values/colonial_empire_values.txt` and `common/scripted_progress_bars/extra_progress_bars.txt`: the
  new leaf and its bar line.
- `common/static_modifiers/extra_modifiers.txt`: the fighters', home-front and lost-war modifiers (and the Nation
  tab registry, `scripts/generators/gen_nation_tab.py`, for any added without a duration).
- `common/on_actions/extra_on_actions.txt`: `.70`'s pool entry and the monthly settle.
- `gui/journal_entry_widgets/colonial_empire_widget.gui`, `common/scripted_guis/colonial_empire_sguis.txt`,
  `common/scripted_effects/colonial_empire_display_effects.txt`: the Wars of Independence block.
- `common/messages/extra_messages.txt`: the notices.
- Loc in `te_events_l_english.yml`, `te_journal_entries_l_english.yml`, `te_miscellaneous_l_english.yml`; then
  `organize_loc.py`.
- New `docs/testing/colonial-wars-playtest.md`; `mod_systems.md` (the war section and the formula table's new row).
- **Player guide, chapter 12**: a new section "Wars of independence" after "Freeing colonial subjects"; the Collapse
  row in "How a colonial empire ends"; "How the AI runs its colonies". Rebuild the PDF.

**Phase 3: the world and the home front.**

- `.74` (great powers take sides) and its mirror, `.75` (the regime crisis), talks (`.76` and the panel button, the
  goal's `valid`), subjects' and secessions' wars treated as colonial wars (the fighters' package, the outcome hooks in
  `common/on_actions/te_civil_war_on_actions.txt` and the existing `on_become_independent` handler).
- Files as phase 2, plus `common/on_actions/te_civil_war_on_actions.txt`.
- **Player guide, chapter 12** ("Wars of independence" grows: backers, talks, the crisis at home). Rebuild the PDF.

The UN's part (a ceasefire order or a resolution on a colonial war, `un_order_*`) can follow as a phase 4 if the owner
wants it.

## 4. Tests and audits

- Offline: the strait list matches the JSON; `is_overseas_from_capital` has only the wonder as caller; the cache
  effect is called from the monthly and start hooks; `te_colonial_reconquest` has `kind = annex_country`, no
  `mirrored_wargoal`, zero infamy; `dp_te_colonial_war`'s `possible` reads `decol_iw_metropole`; every record variable
  is repaired after a civil war (the pattern `test_decolonization_civil_war.py` pins); the war-support lines carry loc.
- The audits that will look at this: `loc_coverage`, `event_image` (four new events), `silent_variable` (options that
  move a record), `modifier_duration` (literal durations only), `je_immediate_reset`, `script_argument`,
  `empty_effect`.

## 5. Notes for the builder

- `form_decolonized_country`'s twelve colour branches each call `apply_decolonization_path` only after the
  `random_list`; the deferral flag belongs there, read on `scope:decolonizing_parent`.
- The wave's three `.70`s and a player's own Release can collide on `decol_offer_pending`; `.70` should set and clear it
  like `.402`.
- `colonial_crackdown_modifier` stays for the police action at bar 40 and above.

## 6. Docs this would amend

`docs/systems/mod_systems.md` (§ Decolonization System, its formula table, § War Support Feeds' table, § Colonial
Collapse's note on `.201`/`.204`), `docs/systems/journal_entry_systems.md` (§ Colonial Empire), player guide chapter 12,
`docs/systems/decolonization_ui_followups.md` (negotiated independence for subjects ties into § 2.3's protectorate
option), and a new `docs/testing/colonial-wars-playtest.md`.

## 7. Recommendations in brief

1. Define a colony as Resolution 1541 does: separated (by sea from our capital, through our own land), distinct (a
   tenth of its people share no heritage with ours) and subordinated (low acceptance, poorer, or unincorporated), with
   the homeland, size and settler rules kept. Cache the separation monthly with a ring fill; it should cost less than
   today's region tests.
2. Let a colony declare independence when the bar is below 40, and at the collapse; offer concede, negotiate or fight.
3. Fight is a war of reconquest we open against a rebel country, whose goal never self-enforces, against rebels with a
   guerrilla package and war-support lines, while our war support, legitimacy and bar drain.
4. Winning buys ten years; losing is a bloody independence; phase 3 adds backers, talks and the crisis at home.

## 8. Open decisions

| # | Question | Recommendation |
|---|---|---|
| D1 | The geography test | Salt water (C), with straits only between our homelands |
| D2 | Distinctness | By heritage trait. It keeps Ireland, Iceland and multi-island countries' own islands out; it makes an independent Indonesia's West New Guinea and Australia's Papua colonies |
| D3 | Contiguous "internal colonies" (Russia's Central Asia, China's Tibet) | Leave them to vanilla's secession, as the UN did |
| D4 | Unincorporated as a third subordination signal | Yes. It adds few colonies (unincorporated territories whose people are accepted and as rich as ours), and each adds to overreach |
| D5 | If `any_neighbouring_state` crosses straits | Build the four-state exclusion so Spanish Morocco counts; or accept it as contiguous |
| D6 | Does the release (Colonial Holdings) list also need a distinct people | Yes: directly held Australia and New Zealand leave by vanilla's release |
| D7 | Who opens the war, and its infamy | We do, at zero infamy; condemnation comes from the great powers and the bar |
| D8 | A fourth option at `.70`: release as a protectorate (free association) | Only after the pact effect is verified; not in phase 2 |
| D9 | Wars at once | Three record slots (five if preferred); no cap on choosing to fight below that |
| D10 | The collapse at 0 | A wave of three declarations, worst first, 60 days apart |
| D11 | The regime crisis | Ship with the law change (`activate_law`): it is the history; the modifiers-only version is the fallback |
| D12 | The reward for winning | Twelve months of +1 stability and ten years without a declaration from that territory; nothing permanent |
| D13 | Can an anti-colonial great power join the war | Yes, rarely (rivals with more army) |
| D14 | Script subjects' declarations | No: vanilla's `dp_independence` already offers the fight; add only the colonial-war treatment |
| D15 | The band for declarations | Below 40 (Under Pressure and Crumbling) |
| D16 | The legacy of a war lost | Bloody Decolonization's modifier, laws and relations −50, whatever programme ran; or only the modifier and relations, with the laws of the programme path |

## 9. Calls I made

- Following the UN's salt-water reading (D3), and the heritage-trait distinctness test (D2).
- Moving the protectorate branch from heritage group to heritage trait.
- Keeping `is_overseas_from_capital` for the Continental Union HQ.
- The straits rule (homeland to homeland only).
- The cache's prefilter (a non-homeland state of 100,000 people) and running it for countries without the technology.
- Negotiate costing 100 authority instead of needing 200.
- The metropole as the war's initiator; the next-day start.
- Deferring the former-colony aftermath until the war is lost.
- Every figure in §§ 2.3-2.8: weights, war-support lines, the bar term, the home-front ladder, the outcome modifiers.
- Three record slots.
