# Grand Monuments: archaeology rework — fixed dig costs, sized digs, site events, foreign excavation articles

**Date:** 2026-10-16
**Status:** asked for by the owner on 2026-10-16: "Review the Archaeological Expeditions / Buried Sites system. Propose and
implement improvements to dig costs and mechanics (not a fan of the GDP-scaled costs), update discovery/completion events so
they explicitly state the location, the find, and a brief real-world historical blurb, and add diplomatic treaty articles for
foreign excavation rights." Picks marked *(design)* are this spec's, open to the owner's review on the PR.
**Builds on:** the archaeology MVP (`2026-10-14-grand-monument-archaeology-design.md`, #939, #959) and the trophies spec
(`2026-10-12-grand-monument-trophies-design.md`), whose machinery a partage trophy uses unchanged.

## What was wrong

A review of the MVP found four things worth changing.

1. **The cost read the sponsor's GDP.** One dig cost `gdp × 0.0002` a week (at least £100) times 1, 2.5 or 5 by method: about
   1%, 2.6% and 5.2% of GDP a year. For the Ottoman Empire in the 1840s an Antiquarian dig at Nineveh cost about as much as
   its whole weekly income; for Greece the same dig cost a tenth of that. The price said nothing about the dig, only about the
   country, and the button's number moved every week with the economy.
2. **Every site took as long as every other.** A 5-level find (the Winged Victory, Nefertiti's bust) and a 15-level one
   (Machu Picchu, the Terracotta Army) both took 25, 40 or 29 months.
3. **The events named the site and nothing else**, and through a country variable (`gm_arch_last`) that the next find or
   finished dig overwrote, so two popups open at once both named the second. Survey sites, twenty of the thirty-five, opened
   with no event at all.
4. **Only the holder of the ground could dig.** Foreign digs were the first thing the MVP deferred.

## 1. What a dig costs

### Innovation, and no money (owner, 2026-10-16)

A dig costs weekly innovation and nothing else: the country already pays for its innovation through its universities, so a
treasury charge on top counted the scholars twice. By method:

| Method | Weekly innovation a dig |
|---|---|
| Antiquarian | 5 |
| Systematic | 20 |
| Forensic | 100 |

`gm_arch_innovation_<method>` holds the figure (the MVP's 5 / 15 / 30, with the later methods raised by the owner); the
monthly pass sums the sponsor's digs into `gm_arch_innovation_units`, the multiplier of `gm_arch_diversion`
(`country_weekly_innovation_add = -1`). The cap never falls (owner, 2026-10-14). `gm_arch_site_innovation` (container scope)
gives a dig's figure by its method, for its row. A dig diverts its innovation for as long as it runs, so a great site, dug
for longer, costs more in all.

A player may launch a dig only while the country makes at least the weekly innovation it would divert
(`gm_arch_spares_<method>`: `country_innovation`, which is net of the digs already running, against
`gm_arch_innovation_<method>`), so a launch never takes the weekly innovation below zero (owner, 2026-10-16). The launch
buttons are greyed below it with a line of their own, the find event offers only a method the country can spare, and
`arch_events.10` checks again (`gm_arch_order_spared`). A dig already running is not stopped if the innovation later falls.

This replaces a first rework, which priced a dig at its levels times £20 / £50 / £200 a week instead of the MVP's share of
GDP. `gm_arch_expense` is retired, not deleted: nothing adds it, `gm_arch_remove_national` strips it from a save made while
it was applied, and its Budget Breakdown row (Archaeological Digs) stays empty.

### Time: by the site's size *(design)*

The MVP's months are kept for a 10-level site, and a site's months scale with `(levels + 5) / 15`:

| Method | 5 levels | 10 levels | 15 levels |
|---|---|---|---|
| Antiquarian | 17 months | 25 | 34 |
| Systematic | 27 | 40 | 54 |
| Forensic | 20 | 29 | 39 |

The progress a month is the method's rate times `gm_arch_size_factor` (`15 / (levels + 5)`, container scope), so a small find
comes out quickly and a great one is a commitment of years: the innovation a dig diverts in all grows with its months. The Forensic bonus (+2 levels) is added at the end and does not lengthen the dig.

### The AI

An AI starts a dig only when the weekly innovation it makes (`country_innovation`, net of the digs it already runs) is at
least four times what an Antiquarian dig diverts. It picks the grandest site waiting and digs it by the best method whose
innovation it makes four times over (`gm_arch_ai_affords_<method>`, `gm_arch_start_affordable`): Forensic needs 400 weekly
innovation, Systematic 80, Antiquarian 20. Otherwise it is as before: at peace, out of default, fewer than two digs, an 8%
chance a month.

## 2. The events

### What each says

Each of the thirty-five sites has four lines of its own (`gm_arch_site_<key>_place`, `_found`, `_dug`, `_history`):

- **The location**: the place (the mound of Hisarlik above the Dardanelles; the Valley of the Kings), and the state in the
  game, by name, so a site in a state the map calls Hüdavendigâr says so.
- **The find**: when it is turned up or located, what the plough, the sponge divers or the scholars found; when the dig is
  finished, what came out of the ground.
- **A historical note**: in two or three sentences, who found it in our world, when, and what became of it (where it went,
  what it changed).

The discovery event reads `_found`, the finished dig `_dug`; both end with the historical note.

### Naming the right site *(design)*

An event cannot reach a container's custom localization, and a country variable is overwritten by the next event. Instead the
effect that fires the event saves the state the site lies in under a name of its own for each site (`gm_arch_ev_<key>`), after
clearing every such name (`gm_arch_ev_mark`, 35 branches in LANDMARKS order). Saved scopes travel with `trigger_event`, so each
popup holds exactly one of them, and its description picks the site's text by `exists = scope:gm_arch_ev_<key>` (a
`first_valid` of 35 branches, with a plain fallback). The same scope names the state in the text
(`[SCOPE.sState('gm_arch_ev_<key>').GetName]`). Only proven forms are used: `exists` on a saved scope (`nuclear_pg_accepted`),
and `sState` in event loc. `gm_arch_last` and the `gm_arch_site_name` custom localization go.

### The events

- **arch_events.1, the discovery**, now for both kinds of site. An incidental find tells the finder (*Something Under the
  Spade*); a survey site tells every player who may dig it, once, the first time it is listed for them (*The Scholars Know
  Where to Look*; `gm_site_told`, a list of countries on the container). Both offer a dig (Systematic if we have it, else
  Antiquarian) or to leave it for now.
- **arch_events.2, the finished dig**, in one event with variants: our own dig (*An Excavation Is Finished*), an Antiquarian
  dig that destroyed half (*Stratigraphic Destruction*, which was arch_events.3), our expedition abroad (*Our Expedition
  Returns*), and the host of a foreign dig (*A Foreign Expedition Finishes*). The title, flavour and option say which; the
  description is the site's.

## 3. Foreign excavation: two treaty articles

### What they grant

Both are directed, with a state input: the **source** is the host, who grants the right in a state it owns; the **target** is
the sponsor, who digs there and pays the influence upkeep. While one is in force, the sponsor may dig any site in that state's
region that is open to it (`gm_arch_may_dig_ground`): a survey site whose technology the sponsor has, or an incidental one
already turned up. It diverts the dig's innovation as at home. The host may still dig its own sites, and whoever
launches first holds the dig.

The treaty is the record: nothing is written on the state. `gm_arch_state_conceded_to` asks the sponsor's treaties live for an
article of the type, with the state's owner as its source and the state as its input (the shape of
`te_country_concedes_state_article`), so a treaty withdrawn, broken or ended by annexation, or a state that changes hands,
ends the right at once. A dig whose right ends is suspended with its progress kept, and the host (or whoever holds the ground
next) may take it up: the Host's change of heart is the vanilla Withdraw button. The state-input roster test gains a third kind
for this (`LIVE`).

| | Excavation Concession (`archaeological_concession`) | Excavation Permit (`excavation_permit`) |
|---|---|---|
| History | The Ottoman firmans (Layard at Nimrud, Humann at Pergamon, the Germans at Babylon), France's monopoly in Persia (1895–1927), Egypt's division of finds | The antiquities laws that ended the export of finds (Ottoman 1884, Egypt after 1922, Iraq 1934), and the foreign schools that dig under licence today |
| Sponsor needs | Romanticism | Empiricism |
| Influence upkeep (sponsor) | 75 | 40 |
| The finds | **Partage**: half the levels, rounded down (at least one), go to the sponsor's capital as a trophy; the host keeps the rest standing as the monument. A rock-cut site has nothing to carry: the host keeps it whole and the sponsor gains Foreign Scholarship. | The host keeps the whole monument; the sponsor gains **Foreign Scholarship** (+10 prestige, +1 cultural pull, ten years). |
| Flags | Can be enforced (a war goal on the state), giftable, renegotiable | Friendly, giftable |
| AI host | Reluctant (−50), much more so once it has Pan-nationalism (−40 more); less with a friendly attitude or as a subject or bloc partner | Mildly reluctant (−10), less with a friendly attitude |
| AI sponsor | A major power or greater with Empiricism and fewer than two digs asks now and then | The same, less often |

A state may be named only when a site in its region is open to the target, so a concession is never signed for nothing.

### Partage *(design)*

The partage trophy is made from the dig's own records (`gm_arch_partage`), as `gm_state_tr_make_trophy` makes one from a
state: a container tagged `gm_trophy` in `gm_trophies`, standing in the sponsor's capital, its origin the host's state, a
piece (`gm_tr_share = piece`, so it is named "Troy — Priam's Treasure" where the site has a part name), counting for half its
levels abroad, `gm_tr_taken_by` the sponsor, taken this year. Then the site, with its levels less the piece, stands in the
host's state as any finished dig does. Nothing about trophies is new: the host may claim the piece back (Return Cultural
Property, the AI's own requests), and a returned piece rejoins the monument it came from (`gm_tr_rejoins_primary`,
`gm_tr_rejoins_secondary`). No infamy and no relations penalty: the host signed for it.

The issue's design gave the host the ruin at 5 levels and the sponsor a 5-level trophy for a 10-level site; half the levels is
the same rule for every size *(design)*.

### Why two articles

The concession is the nineteenth century's bargain: the great power digs, and half of what it finds goes to its museums. The
permit is the twentieth century's: the finds stay, and the foreign school gets the publication and the name. An AI host signs
a permit far more readily, and a nationalist one (Pan-nationalism) hardly ever signs a concession, so the arc follows the
game's technology without a rule that switches one off.

## 4. The panel

- The launch buttons' tooltips give this site's months for that method, read from the container, and the method's weekly
  innovation.
- A dig's row gains the weekly innovation it diverts, and, abroad, a line naming the host and the terms.
- An open site we would dig abroad says so, and on what terms (two display-only scripted GUIs,
  `gm_arch_abroad_concession_sgui`, `gm_arch_abroad_permit_sgui`; the row is shared by every country that may dig it, so the
  line is decided for the viewer).

## 5. Pompeii, and an audit of the site list

Asked for by the owner the same day: "audit our current list of 35 buried archaeological sites. Add Pompeii as a
'discoverable' site already being excavated, review the existing list for gaps, and propose additional plausible fictional
sites to add."

**Pompeii** is row 87 (`pompeii`, Campania, a forum, 15 levels, Romanticism, the Alexander Mosaic as its piece). It was being
dug in 1836, by the Bourbons since 1748, so it is seeded as a dig already under way: a third vector, `excavating`, makes the
seeding start an Antiquarian dig by the owner of its ground at 30% (`gm_arch_seed_dig`, `gm_arch_excavating_progress`). The
owner diverts its 5 weekly innovation from the first month and may suspend it, or restart it by Systematic Stratigraphy, keeping the progress;
with no owner it waits as a known site. A game seeded before this change gets Pompeii the next month: the seeding now runs
again whenever `gm_arch_seed_round` is below `gm_arch_seed_rounds` (2), and makes no site twice. *(design: 30% and the
Antiquarian method stand for the Bourbon treasure-hunting before Fiorelli's methods of 1863.)*

The audit of the list (gaps by region and era, real sites to fill them, and plausible speculative ones) is
`docs/audits/grand_monument_buried_sites_audit.md`. Nothing from it is built beyond Pompeii.

## Tests, debug, docs

- `test_grand_monument_archaeology.py`: the innovation figures, no money cost (no `gdp`, no treasury charge, the money
  modifier a retired stub), the size factor and the month table, the AI's innovation floors, the event plumbing (`gm_arch_ev_mark` branches in LANDMARKS
  order, each event's `first_valid` the same, every site's four lines, each naming its scope), the two articles and the live
  check, partage.
- `test_state_treaty_article_sync.py`: the `LIVE` kind.
- Docs: `mod_systems.md` § Grand Monuments; the player guide's Buried sites (PDF rebuilt);
  `docs/testing/grand-monuments-archaeology-playtest.md`.

## Deferred (unchanged from the MVP, less what this builds)

The political brakes (interest groups, Hard Times backlash), the antiquity and archive dedications, the speculative
breakthroughs, the special-site events, the sites' own pictures.
