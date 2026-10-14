# Grand Monuments: landmarks to loot, and the trophies of 1836 — design

**Date:** 2026-10-12
**Status:** asked for by the owner on 2026-10-12: "add additional grand monuments for the great powers to loot", from the
places Europe took artifacts from (Greece, Egypt and the colonies), with today's repatriation disputes as inspiration;
and "existing trophies in 1836: are there any we could model?" The picks and the calls marked *(design)* are this spec's,
open to the owner's review on the PR.
**Builds on:** the landmarks spec (`2026-10-12-grand-monuments-landmarks-design.md`, "phase 4") and the trophies spec
(`2026-10-12-grand-monument-trophies-design.md`, "phase 5").

## Context

Phase 5 lets a country carry off a Grand Monument, or a piece of one, as a trophy. But the 23 landmarks of 1836 stand
almost all in Europe and East Asia, so there is little in the places Europe actually took from. And the world of 1836
already held famous trophies: the Parthenon's marbles had been in London for twenty years, the Rosetta Stone for
thirty-four.

This change does two things:

1. **Nineteen new landmarks** in the places where Europe's great looting took place: Greece, Egypt, West Africa, India,
   Persia, Korea, Vietnam, in decentralized territory Great Zimbabwe and Bali, and Italy, Anatolia, the Levant and
   Mesopotamia (§1, §1.1–§1.4).
2. **Ten trophies already abroad on 1 January 1836**, seeded as trophies at game start: the Parthenon Marbles, the
   Rosetta Stone, and eight more (§2). Most are still claimed today, so they start as the diplomatic friction the
   trophy system already models: the claimant sees them under Held Abroad, and its AI asks for them back.

## Engine facts and data this rests on

- **1836 owners are read from the game's `common/history/states/00_states.txt`** (supplied by the owner, 2026-10-12;
  issue #901 is still open). Every row below names the owner of the part it uses. Delhi's city hub province
  (`xE0EFA0`) is the Mughal emperor's (MUG), the rest of the state the Company's (BIC). Algiers is French in one province
  and Abd al-Qadir's Emirate of Mascara (MAS) in 23.
- **Landmarks:** the phase 4 mechanism unchanged (`gm_seed_landmark`, one call per row, an owner that proves wrong places
  nothing and logs `TE_MONUMENTS:`).
- **Trophies:** the phase 5 container unchanged (`gm_trophy`, global list `gm_trophies`). The holder is the site's
  owner and the claimant the origin's owner, both read live, so a seeded trophy needs only its records. The monthly pass
  rebuilds every list from the containers.
- **A trophy coming home rebuilds its landmark.** `gm_state_tr_receive` copies `gm_tr_landmark`, `gm_tr_skin` and
  `gm_tr_form` to the origin state when no monument stands there, so a returned Rosetta Stone stands in Lower Egypt as a
  landmark with its own name and picture. That needs the landmark's names, line of history and picture branch, so a
  trophy with no standing monument of its own gets a **landmark row that is never placed** (§2.2).
- **Event and row text speaks from 1836.** The existing lines of history stop at the game's start (Aksum's leaves out
  1937), and so do the new ones. A player learns of Benin 1897 by playing it.

## 1. Landmarks to loot

| # | Key | Name | State | 1836 owner | Dedication | Form (share) | Stand-in | Level |
|---|---|---|---|---|---|---|---|---|
| 24 | `parthenon` | Parthenon | `STATE_ATTICA` | GRE | To the Nation | Pantheon (token) | Greek · Pantheon | 10 |
| 25 | `obelisks_of_karnak` | Obelisks of Karnak | `STATE_UPPER_EGYPT` | EGY | To the Nation | Obelisk (whole) | Generic · Obelisk | 5 |
| 26 | `royal_palace_of_benin` | Royal Palace of Benin | `STATE_BENIN` | BEN | To the Crown | Hall (token) | Generic · Hall | 5 |
| 27 | `royal_palace_of_kumasi` | Royal Palace of Kumasi | `STATE_GOLD_COAST` (Asante's part) | ASH | To the Crown | Hall (token) | Generic · Hall | 5 |
| 28 | `bukgwan_victory_stele` | Bukgwan Victory Stele | `STATE_SARIWON` (Hamgyong) | KOR | War Memorial | Stele (whole) | Ge'ez · Stele | 5 |
| 29 | `imperial_city_of_hue` | Imperial City of Huế | `STATE_ANNAM` | DAI | To the Crown | Gate (piece) | Chinese · Gate | 10 |
| 30 | `persepolis` | Persepolis | `STATE_FARS` | PER | To the Nation | Hall (token) | Avestan · Hall | 5 |
| 31 | `red_fort` | Red Fort | `STATE_DELHI` (the Mughal part) | MUG | To the Crown | Gate (piece) | Avestan · Gate | 10 |

**What each is for.**

- **Parthenon.** The case that defines the modern argument. Greece made Athens its capital in 1834 for the Acropolis.
  Its marbles in London are §2's first trophy. Returned, they are added back to the temple.
- **Obelisks of Karnak.** In 1836 Egypt's obelisks were diplomatic currency: Muhammad Ali gave Luxor's pair to France and
  Alexandria's to Britain. An obelisk is an object, so an occupier takes the whole monument.
- **Royal Palace of Benin.** The Benin Bronzes: sacked in the 1897 punitive expedition, Germany's 2022 return, the
  Horniman's and Cambridge's. The palace's piece is "the Bronzes".
- **Royal Palace of Kumasi.** The Asante gold regalia, taken in 1874 and 1896. The British Museum and the V&A lent part
  of it back to the Manhyia Palace in 2024. The piece is "the gold regalia".
- **Bukgwan Victory Stele.** Raised in 1707 to the 1592 victory over the Japanese in Hamgyong. Japan's army took it to
  Tokyo in 1905; it went back in 2005 and on to North Korea in 2006. A stele goes whole.
- **Imperial City of Huế.** The Nguyen capital, its Meridian Gate finished in 1833. French troops sacked its treasury in
  1885. The piece is "the imperial treasury".
- **Persepolis.** Known in Persia as Takht-e Jamshid, the throne of the Shahnameh's king, so it carried weight in 1836.
  European travellers carried off its reliefs through the nineteenth century. The piece is "the reliefs".
- **Red Fort.** The Mughal emperor still held court there in 1836. The British looted it after 1857; the Koh-i-Noor's
  and Shah Jahan's cup's claims start here. The piece is "the Mughal regalia".

**How they pass phase 4's rules.**

- **One per state**, none in a state that already has a landmark. Benin, Kumasi, Huế, Delhi and Hamgyong have one each.
- **Ancient monuments with weight in 1836 come first.** The Parthenon (the new kingdom's reason for its capital), the
  obelisks (gifts of state in the 1830s) and Persepolis (Jamshid's throne) have it. One without it may still stand as a
  heritage site, lower priority all else equal (owner, 2026-10-12, revising phase 4's rule).
- **No holy site another faith holds.** The Parthenon's small Ottoman mosque was out of use by 1836 (the garrison left in
  1833), and the Red Fort's Pearl Mosque is the palace's own.
- **Nothing refers to a person or event after 1836.**
- **No duplicate** of a base-game monument or a mod wonder.

**Asked of the rule "none means mainly a live grievance today"** *(design)*. The owner's brief asks for today's
repatriation disputes, and these monuments are where they start. None of them means mainly a grievance: the Parthenon
means Athens, the Red Fort Indian sovereignty. The grievance is the taking, which is play.

**Left out.**

- **The Old Summer Palace** (the bronze zodiac heads), the Beijing observatory and the Forbidden City's treasures: Beijing
  holds the Temple of Heaven, and one monument a state is the rule. Its piece would be the city's case.
- **Borobudur, Amaravati, Sanchi, Xanthos:** no weight in 1836, which under the revised rule makes them lower priority,
  not excluded. Xanthos was added (§1.3); Borobudur and Amaravati stand in split states, left out for now. Great
  Zimbabwe (§1.1) and Halicarnassus (as Bodrum Castle, §1.2) were added.
- **The Pergamon Altar, the Ishtar Gate, the Nimrud lamassu, Nefertiti:** still buried in 1836.
- **Magdala:** Tewodros's fortress dates from the 1850s.
- **Mexico's Sun Stone:** `STATE_MEXICO` is phase 6's Angel of Independence, and Mexico's dispute is a featherwork
  headdress (below).
- **The Porcelain Tower of Nanjing:** a Buddhist temple's pagoda, so a Grand Shrine, which is never taken.
- **Mahamuni, the Golden Stool, the Somnath gates:** living holy objects, or a sectarian grievance.

**Phase 6's Panathenaic Stadium** (landmarks spec, Appendix B) would need Attica, which the Parthenon now holds. If phase 6
is built, its stadium adds its levels to the standing monument, or is dropped.

### 1.1 Added on the owner's second ask: decentralized territory (2026-10-12)

The owner confirmed that a building can be placed in a decentralized country's state, and asked for looted places
there, with the Throne of Kandy (§2).

| # | Key | Name | State | 1836 owner | Dedication | Form (share) | Stand-in | Level |
|---|---|---|---|---|---|---|---|---|
| 40 | `great_zimbabwe` | Great Zimbabwe | `STATE_ZAMBEZI` (the Mashona's part) | MSH | To the Nation | Round tower (piece) | Irish · Round tower | 5 |
| 41 | `royal_palaces_of_abomey` | Royal Palaces of Abomey | `STATE_DAHOMEY` (Dahomey's part) | DAH | To the Crown | Hall (token) | Generic · Hall | 5 |
| 42 | `klungkung_palace` | Klungkung Palace | `STATE_SUNDA_ISLANDS` (Bali's part) | BAL | To the Crown | Gate (piece) | Sanskrit · Gate | 5 |

- **Great Zimbabwe.** Its piece is "the soapstone birds": Willi Posselt and Cecil Rhodes took them in 1889–1891, and South
  Africa (1981) and Germany (2003) gave them back. The bird is on Zimbabwe's flag. The form is the round tower (the
  Great Enclosure's conical tower), so a looter takes a quarter. In 1836 its weight was local and religious, not
  political: a heritage site, which the revised rule allows.
- **Royal Palaces of Abomey.** Dahomey is centralized, so this belonged in §1 and was missed. French troops took the
  palaces' thrones and royal statues in 1892, and France gave 26 of them back to Benin in 2021, under a law passed for
  that return. The piece is "the thrones and royal statues".
- **Klungkung Palace.** The Dewa Agung was Bali's paramount king. The Dutch took the regalia in 1908, and the Kris of
  Klungkung came back in 2023. The piece is "the royal regalia". Bali's part of the Sunda Islands is two provinces
  beside the Dutch East Indies' eight.

**Considered and left out.**

- **The moai Hoa Hakananai'a** (Rapa Nui's request to the British Museum): `STATE_EASTER_ISLAND` has no owner in 1836.
- **Māori meeting houses** (Mataatua, Hinemihi) and **the Nisga'a and Haisla poles** returned from Edinburgh and Sweden:
  carved after 1836.
- **Bamum's throne, Mandu Yenu** (Berlin): made after 1836.
- **The Ngonnso** (Nso's founding figure, returned from Berlin in 2022): a sacred figure that still serves its people's
  rites, which phase 4's holy-site rule keeps out.
- **The Cape Cross padrão** (Berlin, returned to Namibia in 2019): a Portuguese marker of a claim, not Herero or Nama work.
- **The Lombok treasure** (2023's Dutch return): the obvious Lombok site, Cakranegara, may not be in Bali's two
  provinces, and one Balinese palace is enough.
- **Tibet's monasteries** (1903–1904): holy sites.

### 1.2 Italy, Turkey and the Levant (owner's third ask, 2026-10-12)

| # | Key | Name | State | 1836 owner | Dedication | Form (share) | Stand-in | Level |
|---|---|---|---|---|---|---|---|---|
| 44 | `uffizi_gallery` | Uffizi | `STATE_TUSCANY` | TUS | To the Nation | Hall (token) | Generic · Hall | 10 |
| 45 | `capitoline_museums` | Capitoline Museums | `STATE_LAZIO` | PAP | To the Nation | Forum (token) | Latin · Forum | 5 |
| 46 | `bodrum_castle` | Bodrum Castle | `STATE_AYDIN` | TUR | War Memorial | Tower (piece) | Gothic · Tower | 5 |
| 47 | `temples_of_baalbek` | Temples of Baalbek | `STATE_LEBANON` | EGY | To the Nation | Colonnade (token) | Aramaic · Colonnade | 5 |

Each state has one owner in 1836, so none is exposed to #936.

- **Uffizi.** Napoleon's looting of Italy, which the phase 5 spec cites (the horses of San Marco). He carried off the
  Medici Venus in 1802, and it went back to Florence after his fall. Its piece is "the Medici Venus".
- **Capitoline Museums.** The Treaty of Tolentino (1797) made the Pope surrender the Dying Gaul, the Capitoline Venus
  and a hundred more works: a war goal like Surrender a Monument. Its piece is "the Dying Gaul". To the Nation, since
  the Papal States are not crowned (`monument_government_is_crowned`) and a crown monument would start contested.
- **Bodrum Castle.** The Knights of Saint John built it from the Mausoleum of Halicarnassus, and slabs of the
  Mausoleum's frieze were set in its walls. The Sultan gave them to Britain in 1846, and Newton dug up the statues in
  1856–1857; Turkey asks the British Museum for them. The castle, not the Mausoleum, is the landmark: an Ottoman
  fortress since 1523 carried weight in 1836, while the Mausoleum was a lost ruin until Newton found it. Its piece is
  "the Mausoleum friezes"; War Memorial for the conquest of the Knights' last stronghold in Anatolia *(design)*.
- **Temples of Baalbek.** The Levant's grandest ruin, walled as a citadel in the Middle Ages and credited to Solomon
  by local legend, which is its claim to weight in 1836 *(design)*. No famous piece left it: it is here as the
  Levant's monument for an occupier to loot. Its piece is "the temple carvings". Egypt holds the Levant in 1836.
  Since nobody else holds part of the state, its passing back to the Ottomans, or to anyone, is a whole transfer and
  keeps its records.

**Considered and left out.**

- **Still buried in 1836:** the Pergamon Altar (1878), Priam's Treasure (1873), the Sidon sarcophagi (1855, 1887),
  Nineveh's and Nimrud's reliefs (1840s). The Siloam inscription (1880) lay in Hezekiah's tunnel under Jerusalem.
  Monuments uncovered during the game are issue #939, built as `2026-10-14-grand-monument-archaeology-design.md`.
- **Standing but unknown to Europe in 1836:** the Nereid Monument at Xanthos (1838) and the Mesha Stele at Dhiban
  (1868). Both added under the revised rule (§1.3).
- **Palmyra:** like Great Zimbabwe, its weight in 1836 was legend and travellers' romance (Lady Hester Stanhope, 1813),
  and its funerary busts left from the 1870s. Added under the revised rule (§1.3).
- **Ctesiphon's arch** (Taq Kasra, `STATE_BAGHDAD`): added at the owner's ask (§1.4).
- **The Serpent Column and the Obelisk of Theodosius** in Constantinople: they could be 1836 trophies held by the
  Ottomans (from Delphi and Karnak), but nobody claims them, and Greece's and Egypt's AI would start asking.
- **Italy:** the Vatican (a base-game monument), Michelangelo's David (never taken, and Tuscany has the Uffizi), the
  Last Supper (Milan has La Scala), Raphael's Saint Cecilia (an altarpiece in a church).
- **Jerusalem, Hebron, Damascus's Umayyad Mosque:** holy sites.

### 1.3 Heritage sites the revised rule opens (owner's fourth ask, 2026-10-12)

The owner's revision: an ancient monument without weight in 1836 can stand as a heritage site, lower priority all else
equal. Of the candidates it opened, the owner asked for those in single-owner states (none exposed to #936).

| # | Key | Name | State | 1836 owner | Dedication | Form (share) | Stand-in | Level |
|---|---|---|---|---|---|---|---|---|
| 48 | `palmyra` | Palmyra | `STATE_SYRIA` | EGY | To the Nation | Colonnade (token) | Aramaic · Colonnade | 5 |
| 49 | `xanthos` | Xanthos | `STATE_KONYA` | TUR | To the Nation | Rock-cut (piece) | Aramaic · Rock-cut | 5 |
| 50 | `mesha_stele` | Mesha Stele | `STATE_TRANSJORDAN` | EGY | War Memorial | Stele (whole) | Ge'ez · Stele | 5 |

- **Palmyra.** Its funerary busts went to European museums from the 1870s; that is its piece. It lies between Syria
  (Homs, the nearest hub) and Deir ez-Zor, both with one owner, so either state is safe.
- **Xanthos.** Fellows shipped the Nereid Monument and the Harpy Tomb's reliefs to the British Museum in 1842–1844,
  and Turkey asks for them. Its piece is "the Nereid Monument"; the rock-cut form for the Lycian tombs cut into its
  cliffs, a quarter to a looter. In Konya, whose port hub is Antalya (Aydin already holds Bodrum).
- **Mesha Stele.** Broken up in 1868 and pieced together in the Louvre; Jordan asks for it. A stele goes whole, and
  War Memorial suits a king's record of his victory. In Transjordan (Kerak is the hub beside Dhiban).

**Left out, split states (owner, 2026-10-12):** Borobudur (Central Java: the Dutch East Indies, Yogyakarta and
Surakarta) and Amaravati (Circars or Madras, both shared with the Company).

### 1.4 The Arch of Ctesiphon (owner, 2026-10-12)

| # | Key | Name | State | 1836 owner | Dedication | Form (share) | Stand-in | Level |
|---|---|---|---|---|---|---|---|---|
| 51 | `arch_of_ctesiphon` | Arch of Ctesiphon | `STATE_BAGHDAD` | TUR | To the Nation | Arch (piece) | Avestan · Gate | 5 |

Taq Kasra, the Sasanian kings' audience hall, carried weight in 1836: al-Buhturi's ode on it is a classic of Arabic
poetry, and it stood for Persian kingship. Nothing left it in modern times. Its piece is "the treasures of Khosrow",
which its Arab conquerors carried off in 637, the Spring of Khosrow carpet among them. The stand-in is the Persian
gate, an iwan like the arch's, rather than a Roman triumphal arch. Baghdad is the Ottomans' alone in 1836.

## 2. The trophies of 1836

### 2.1 Which

| Trophy | Landmark | Came from (1836 owner) | Stands in (holder) | Taken | Levels | Share |
|---|---|---|---|---|---|---|
| Parthenon — the Marbles | `parthenon` (§1) | `STATE_ATTICA` (GRE) | `STATE_HOME_COUNTIES` (GBR) | 1801 | 5 | piece |
| Rosetta Stone | `rosetta_stone` | `STATE_LOWER_EGYPT` (EGY) | `STATE_HOME_COUNTIES` (GBR) | 1801 | 3 | whole |
| Tipu's Tiger | `tipus_tiger` | `STATE_MYSORE` (MYS) | `STATE_HOME_COUNTIES` (GBR) | 1799 | 2 | whole |
| Royal Palace of Kandy — the throne | `royal_palace_of_kandy` | `STATE_CEYLON` (BCE) | `STATE_HOME_COUNTIES` (GBR, at Windsor) | 1815 | 2 | piece |
| Temple of Dendera — the Zodiac | `temple_of_dendera` | `STATE_UPPER_EGYPT` (EGY) | `STATE_ILE_DE_FRANCE` (FRA) | 1821 | 2 | piece |
| Luxor Obelisk | `luxor_obelisk` | `STATE_UPPER_EGYPT` (EGY) | `STATE_ILE_DE_FRANCE` (FRA) | 1831 | 5 | whole |
| Venus de Milo | `venus_de_milo` | `STATE_WEST_AEGEAN_ISLANDS` (GRE) | `STATE_ILE_DE_FRANCE` (FRA) | 1820 | 3 | whole |
| Baba Merzoug | `baba_merzoug` | `STATE_ALGIERS` (MAS) | `STATE_BRITTANY` (FRA, at Brest) | 1830 | 2 | whole |
| Piraeus Lion | `piraeus_lion` | `STATE_ATTICA` (GRE) | `STATE_VENETIA` (AUS) | 1687 | 2 | whole |
| Horses of Saint Mark | `horses_of_saint_mark` | `STATE_EASTERN_THRACE` (TUR) | `STATE_VENETIA` (AUS) | 1204 | 5 | whole |

- **Still claimed today:** the Marbles (Greece's demand, the 2023 cancelled meeting), the Rosetta Stone and the Dendera
  Zodiac (Egypt's 2022 petitions), Baba Merzoug (Algeria's request, renewed since 1962), and Tipu's relics.
- **The Throne of Kandy** (added on the owner's ask): sent to Windsor in 1815 and given back to Ceylon in 1934. Its
  claimant is British Ceylon, Britain's own colony, until it goes free. It is a piece of the Royal Palace of Kandy, a
  landmark that is never placed (§2.2), so a returned throne rebuilds the palace.
- **The precedents:** the Horses of Saint Mark were taken twice (1204, 1797) and returned once (1815), and the Piraeus Lion
  has guarded Venice's Arsenal since 1687. Both stand in Venice, so whoever holds Venetia holds them: Austria, and Italy
  after 1866, as history went. An occupier of Venetia can carry them off again, as Napoleon did.
- **Two were not taken by force** *(design)*: Muhammad Ali gave the Luxor Obelisk to France in 1830, and the Venus de Milo
  was bought from the Ottoman authorities in 1820. Each still counts as abroad, and its history line says how it left.
- **Levels** *(design)*: 5 for the largest (the marbles, a whole obelisk, the four horses), 3 for a famous single
  object, 2 for the rest. Each counts for half abroad, rounded up: Britain starts with 7 standing grandeur from
  trophies, France 7, Austria 4. France's Arc de Triomphe alone is 15.
- **Share:** whole for an object, piece for what was cut from a building (the marbles, the zodiac). The share picks the
  title: a piece reads "Parthenon — the Marbles".
- **Dedication** of a trophy with its own landmark row (§2.2): To the Nation, but War Memorial for Baba Merzoug, the
  cannon that defended Algiers. A returned trophy is rebuilt with it.

**Left out.**

- **Diponegoro's kris:** a weapon, not a monument. Its claimant would be Yogyakarta, not the Netherlands.
- **Not monuments:** the Koh-i-Noor (in Lahore in 1836), Moctezuma's headdress (Vienna) and the Gweagal shield.
- **Since returned:** the Quadriga (1814), the Laocoön and Napoleon's other Italian spoils (1815–1816).
- **Too slight a claim:** the Aegina and Bassae marbles, Philae's obelisk at Kingston Lacy, the Serpent Column and
  Rome's obelisks.

### 2.2 Landmarks that are never placed

A trophy with no standing monument of its own (all but the Marbles) gets a landmark row, marked `placed = False` in
`LANDMARKS`. It has every landmark site except the seeding call: its name, history line, name in running text,
trophy name, picture branch and debug log line. Its state and owner are its origin's, checked
against the trophy row. Picture codes follow `LANDMARKS` order, so these take 1,000,032 to 1,000,039, and Kandy's,
added after §1.1's three, 1,000,043.

| # | Key | Name | Form | Stand-in |
|---|---|---|---|---|
| 32 | `rosetta_stone` | Rosetta Stone | Stele | Ge'ez · Stele |
| 33 | `temple_of_dendera` | Temple of Dendera | Colonnade | Aramaic · Colonnade |
| 34 | `luxor_obelisk` | Luxor Obelisk | Obelisk | Generic · Obelisk |
| 35 | `venus_de_milo` | Venus de Milo | Statue | Generic · Statue |
| 36 | `piraeus_lion` | Piraeus Lion | Statue | Generic · Statue |
| 37 | `horses_of_saint_mark` | Horses of Saint Mark | Statue | Generic · Statue |
| 38 | `tipus_tiger` | Tipu's Tiger | Statue | Generic · Statue |
| 39 | `baba_merzoug` | Baba Merzoug | Column | Generic · Column |
| 43 | `royal_palace_of_kandy` | Royal Palace of Kandy | Hall | Generic · Hall |

"One per state" counts placed rows only: the Dendera Zodiac and the Luxor Obelisk come from Upper Egypt, where the
Obelisks of Karnak stand. **Superseded 2026-10-13** (`2026-10-13-multiple-monuments-per-state-design.md` §4.1): a
trophy that goes home to a state with a monument adds its levels to it only when it is a *piece of that monument* (the
Quadriga goes back on the Gate, the Marbles on the Parthenon). Anything else stays a monument of its own beside the
one standing, on the state's one building: the Luxor Obelisk and the Dendera Zodiac in Upper Egypt, the Piraeus Lion
in Attica, the Horses of Saint Mark in Eastern Thrace. It is the same container, retagged `gm_monument`, and keeps its
name, form, landmark, picture and dedication.

### 2.2.1 Landmarks placed beside another (2026-10-13)

A second *placed* landmark in a state (a row with `beside=True` in `LANDMARKS`, after the state's first row) is
seeded by the same `gm_seed_landmark` call. Where a monument already stands in the part, the call stands it beside
that one (`gm_seed_landmark_beside`, `gm_monument_effects.txt`): a secondary monument whose levels go on the state's
building, which keeps the first one's dedication. A landmark already standing there is not placed again, so the
debug event can run twice. No row uses it yet. The next candidates are Rome (the Colosseum and the Roman Forum beside
the Capitoline Museums), Beijing (the Forbidden City and the Old Summer Palace beside the Temple of Heaven) and Athens
(the Panathenaic Stadium beside the Parthenon). Each is an ordinary landmark row first: key, state, owner, dedication,
form, stand-in picture and level, with the name, history line and picture branch the registry's failures list; then
`beside=True`.

### 2.3 Seeding

`gm_seed_trophies` (in `gm_trophy_effects.txt`) runs once per game, after the landmarks, from the same on-action
(`gm_landmarks_on_game_started_after_lobby`, behind `gm_system_enabled` and `gm_landmarks_seeded`). One call per
`TROPHIES_1836` row:

```
gm_seed_trophy = { LANDMARK = parthenon ORIGIN = STATE_ATTICA ORIGIN_TAG = GRE SITE = STATE_HOME_COUNTIES SITE_TAG = GBR DEDICATION = civic FORM = pantheon SHARE = piece LEVELS = 5 YEAR = 1801 }
```

`gm_seed_trophy` creates the container in the site state, as a taking does. It sets the origin and site (with their
regions), the levels, half of them rounded up as `gm_tr_grandeur`, the share, dedication, skin (`landmark_<key>`), form,
landmark, `gm_tr_namesake = landmark` and the year. It writes nothing else: no infamy, relations or notices.

It places nothing, and logs a `TE_MONUMENTS:` line, when:

- the origin's or the site's part is not the named owner's;
- one country owns both, which would bring it home at the first pass;
- a trophy of this landmark already exists, so the debug re-run never doubles one.

Then `gm_trophy_pass` writes the lists, and every country it listed gets a refresh (`monument_events.20`), which opens
its journal entry.

### 2.4 Trophies outside a capital

A taking puts the trophy in the taker's capital, but that is the only place the capital is read. After that its site is
a fixed state, its holder whoever owns that state. So Brest and Venice behave as a trophy left behind when its holder
moved its capital: the Trophies on Display card shows them there, occupying Brittany or Venetia reaches them, and
conquering the state takes them. The one place the capital still counts: Return Cultural Property's war goal contests the
holder's capital (`control_target_country_capital`), not the trophy's state. The article still returns every trophy,
wherever it stands.

### 2.5 Who carried it off (owner's question, 2026-10-12)

Phase 5's AI brought home every trophy whose origin it owned, which made its own-colony route a loop. It carried a
monument off from its unincorporated colony, then brought it straight back at the next monthly pass and took The
Homecoming's ten years of legitimacy. A whole monument came back marked as built by its owner, which ended the loop. A
piece left the monument standing with its old builder, so it could be taken again once the ten-year cooldown ran out.
A player could do the same deliberately with Bring It Home.

A trophy now records its taker (`gm_tr_taken_by`): the country that made it, a looter that carries it off its site, or
for a seeded trophy its 1836 holder. While its taker still holds it (`gm_tr_held_by_its_taker`):

- the AI doesn't bring it home, and a player isn't told it is within reach;
- Bring It Home still works but only moves it, with no Homecoming (`gm_tr_bring_home_own_tt` says so);
- a trophy taken *from* its holder (retaken, or its site conquered) comes home as before, with The Homecoming.

A trophy from before this change has no record and behaves as before.

## 3. A trophy's line of history

A trophy row today shows its name, dedication, origin and year. A trophy from a landmark now adds the state card's
"Historical monument" line: same text, and the same tooltip read from the trophy (`gm_tr_landmark_desc`, a container
twin of `gm_landmark_desc`). It shows in the Trophies, Held Abroad and Trophies on Display rows, only for a trophy with
`gm_tr_landmark` (`gm_tr_disp_is_landmark`). So "Rosetta Stone" on Britain's list says on hover what it is and how
Britain came to hold it.

## 4. The lines of history

Each ends with a full stop and speaks from 1836, as phase 4's do.

| Key | Line |
|---|---|
| `parthenon` | Raised for Athena on the Acropolis of Athens in the fifth century BC. Lord Elgin's agents took about half its surviving sculpture to London between 1801 and 1812. |
| `obelisks_of_karnak` | Raised before the temples of Amun at Karnak. Hatshepsut's, almost thirty metres of a single stone, is the tallest still standing in Egypt. |
| `royal_palace_of_benin` | The Oba's palace in Benin City, home to the brass and ivory works the kingdom's royal guilds have cast and carved for centuries. |
| `royal_palace_of_kumasi` | The Asantehene's palace in Kumasi, with the stone treasure house Osei Bonsu built to hold the kingdom's gold. |
| `bukgwan_victory_stele` | Raised at Kilju in 1707 to the volunteer army that defeated the Japanese invaders in Hamgyong in 1592. |
| `imperial_city_of_hue` | The Nguyen emperors' citadel at Huế, begun under Gia Long in 1804. Minh Mang finished its Meridian Gate in 1833. |
| `persepolis` | The palace city of the Achaemenid kings, burned by Alexander in 330 BC. Persians call it Takht-e Jamshid, the throne of the Shahnameh's king Jamshid. |
| `red_fort` | Shah Jahan's fortress-palace at Delhi, finished in 1648, where the Mughal emperor still holds court. |
| `rosetta_stone` | A decree of 196 BC in hieroglyphs, Demotic and Greek, found by French soldiers at Rosetta in 1799. Britain took it under the capitulation of 1801, and Champollion read the hieroglyphs from it in 1822. |
| `temple_of_dendera` | The temple of Hathor at Dendera. Its stone zodiac was cut from a chapel ceiling in 1821 and sold to Louis XVIII. |
| `luxor_obelisk` | One of the two obelisks of Ramesses II before the temple of Luxor, given to France by Muhammad Ali in 1830 and raised on the Place de la Concorde in 1836. |
| `venus_de_milo` | A marble Aphrodite found by a farmer on Milos in 1820, bought by the French ambassador and given to Louis XVIII. |
| `piraeus_lion` | A marble lion that guarded the harbour of Piraeus, carried off by the Venetian commander Morosini in 1687 to stand at the gate of the Arsenal in Venice. |
| `horses_of_saint_mark` | Four bronze horses from the Hippodrome of Constantinople, carried off by Venice in 1204. Napoleon took them to Paris in 1797, and they came back to Saint Mark's in 1815. |
| `tipus_tiger` | A wooden tiger mauling a European soldier, made for Tipu Sultan of Mysore and taken when Seringapatam fell in 1799. It growls in the East India Company's museum in London. |
| `baba_merzoug` | The great cannon that guarded Algiers harbour from 1542, taken by the French in 1830 and set up in the arsenal at Brest as a column crowned with a cockerel. |

## 5. Tests, debug, docs

- **`test_grand_monument_registry.py`:** `Landmark` gains `placed` (default true). Placed rows only: a seeding call,
  one per state, level 5 or more. Every row: names, line of history, name in running text, picture branch, debug log
  line, trophy name.
- **`test_grand_monument_trophies.py`:** `TROPHIES_1836`, one `gm_seed_trophy` call per row in order. Each row's landmark
  is in `LANDMARKS`. An unplaced landmark's origin and owner are its row's, and every unplaced landmark has a trophy
  row. The share is whole exactly for an object form. Origin and site owners differ. The seed sets every record and
  guards both owners and duplicates. The on-action runs it after the landmarks. The part names (`gm_tr_part_name`) list
  the landmark branches first (the Quadriga, then the new ones), then the forms. `gm_tr_landmark_desc` has a branch per
  landmark, and the trophy rows have their history line.
  `TakerTests`: every place a trophy gets a taker records it, the AI's pass and its notice skip a trophy its taker
  holds, and The Homecoming and its tooltip leave the taker out (§2.5).
- **Debug:** `te_debug_monuments.5` gains option c, which seeds the 1836 trophies (for a save made before this change).
- **Docs:** `mod_systems.md` § Grand Monuments; the player guide's `02-timeline.md` (the landmark paragraph and
  *Monument trophies*); the trophies spec gets a pointer here.
- **Pictures (drawn 2026-10-12):** each placed landmark has its own picture, as it stood in 1836 (the Parthenon a
  roofless ruin with its small mosque, Karnak half in sand, Xanthos's temple-tomb fallen). Each takes its
  code from 1,000,000 and its `gm_picture` entry in the icon pipeline, and stops showing its stand-in. The stand-in
  columns above record what each showed before. So do the unplaced rows of §2.2, as each would stand once its trophy
  goes home (Luxor's obelisk before its pylon, the Horses on the Hippodrome), all but the Venus de Milo: three rounds
  drew her with arms, from behind or over a lettered plaque, so she keeps the generic statue.

## 6. In-game checks

1. A new game: the nineteen new landmarks stand at their levels, and no `TE_MONUMENTS: landmark … not placed` line is
   logged. Benin and Asante are both centralized in 1836 (owner, 2026-10-12), and a building can be placed in a
   decentralized country's state too.
2. Britain's Trophies section lists the Marbles, the Rosetta Stone, Tipu's Tiger and the Kandyan throne. France's lists
   four and Austria's two. Greece, Egypt, the Ottomans, Mysore, Mascara and British Ceylon each list theirs under Held
   Abroad.
3. The history line's tooltip on a trophy row reads its landmark's line.
4. Return the Marbles (debug `te_debug_monuments.6` option c, as Britain): the Parthenon grows by 5. Return the Rosetta
   Stone: a "Rosetta Stone" landmark stands in Lower Egypt with its own picture.
5. Occupy Venetia at war with Austria: the Trophies on Display card offers the Horses and the Lion.
6. Play Britain or France for a few years: Greece, Egypt and the rest ask for Return Cultural Property now and then
   (its existing 2% evaluation chance), not every month. If they ask too often, lower `evaluation_chance` for
   claimants that have never held their trophy.

## Known limits

- **A split state that merges loses its monument's records.** A landmark in a country's part of a state (the Red Fort in
  the Mughals' province of Delhi, the Jantar Mantar, the Shalimar Gardens, Aksum, and from §1.1 Great Zimbabwe,
  Abomey and Klungkung) is recorded on that part. If the
  country holding the rest annexes it (the Company annexing the Mughals), the engine merges the two. The records go with
  the merged part, and the building reads as an unrecorded monument. This is a phase 4 limit and is not fixed here: it
  needs the landmark's identity kept by state region and restored after a merge (issue #936, with the engine reads it
  needs first).
- **A holder keeps a trophy it carried off itself, even once it owns the origin** (`gm_tr_held_by_its_taker`, added
  2026-10-12 with this change; the seeded trophies' taker is their 1836 holder). A France that conquers all of Algiers
  keeps Baba Merzoug at Brest, and Britain keeps the Rosetta Stone if it takes Egypt. A trophy taken *from* its holder
  still goes home: the AI brings it back, with The Homecoming.
