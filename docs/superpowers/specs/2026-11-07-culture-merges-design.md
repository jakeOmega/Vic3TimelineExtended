# Culture Merges: building a shared national culture from its regional parts

Date: 2026-11-07. Owner request, reached in conversation. The owner pointed at
the Steam Workshop mod *Syncretic Cultures* (2952980917, local copy under
`/mnt/c/Program Files (x86)/Steam/steamapps/workshop/content/529340/2952980917`)
and asked for something like it that starts **dynamically** instead of by
country tag and does not run a fixed 100-year process. A country that holds most
of a set of closely related cultures, treats them as equals and has the right
technology can start a merge. Over a few decades the parts assimilate into one
national culture (North and South German into German), and once it dominates,
every remaining pop of the parts, anywhere in the world, switches at once.

Calls the owner did not make are marked *(designer's call)*; the builder may
revisit those with a stated reason. Everything unmarked is the owner's.

## 1. Why

- **Performance.** Pops are split by state, building, profession, culture and
  religion, so every extra culture living in a place multiplies the pops the
  engine simulates. Two German cultures in one city are roughly twice the pops
  of one.
- **Thresholds count the parts separately.** Homelands, map modes and every
  share test see North German and South German as two cultures. A state that
  is 40% North German and 30% South German does not clear a 50% homeland bar,
  though it is 70% German in any sense a player means.
- **The story.** Nineteenth- and twentieth-century states built national
  identities out of regional ones: Germany, Italy ("we have made Italy; now we
  must make Italians"), France's Third Republic turning Occitans and Bretons
  into Frenchmen, Indonesia's 1928 Youth Pledge. The mod has no way to show it.

### What the reference mod does (and what we change)

*Syncretic Cultures* ships 64 merged cultures, generated from configs by the
author's script. One decision per merge, player-only and tied to a tag (only
GER can make German), needs Pan-Nationalism. Taking it adds the merged culture
as primary and gives it a homeland wherever a part has one. Each year a hidden
event converts a slice of every part pop: the slice depends on profession,
literacy and the radio, film and propaganda techs, is a tenth for
discriminated pops and much larger outside the parts' homelands. A 100-year
bar with 30/50/70-year popups offers to strip the old homelands. Optional
"add-on" cultures (Czech, Slovene, Sorb into German) are offered by popup. Per
merged culture it defines its own heritage and language traits, and it has
religion-swap events and per-culture game rules (never/manual/auto).

We keep: the per-pop conversion slice driven by development, the merged
culture added as primary, and a generator. We change: dynamic eligibility
instead of tags, AI participation, no fixed duration, homeland growth left to
the mod's Dynamic Homeland Progress, optional parts chosen by circumstance
instead of popups, and a worldwide switch at the end.

## 2. Goals, non-goals, anti-goals

**Goals**

1. A country that meets the conditions (§4) can start a merge; the AI does
   too.
2. While it runs, the parts' pops in the country assimilate into the merged
   culture at a rate driven by long-term development and policy (§5), with no
   fixed duration. Roughly a few decades in a well-developed country.
3. When the merged culture dominates (§6), every pop of the parts worldwide
   converts, homelands and primary cultures follow, and the parts are gone as
   living cultures.
4. Three tiers of closeness (§3), all generated from one config: same
   language and heritage, same language across heritages, and same language
   family (a Latin culture).
5. Nothing vanilla or the mod checks about the parts breaks silently (§7).

**Non-goals (v1)**

- Religion changes. The reference mod's religion-swap events are out; pops
  keep their religion when their culture changes.
- Cultures across language families (Swiss, Belgian, Canadian, Welsh into
  British, Breton into French). The owner prefers merges of a common or very
  closely related language. The per-part share test (§4.2) already stops the
  worst case, a Swiss merge turning every French pop in the world Swiss; a
  later version could admit cross-family merges where one country holds most
  of every part (Belgium, Canada).
- **A civic tier** for historical supranational identities (Ottomanism,
  Habsburg, Indian, Soviet, Swiss, Belgian, Ethiopian): deferred to a later
  design (owner, 2026-11-07). The best fit is Ottomanism: in 1836 the Ottomans
  hold 94% of Turks, 70% of Greeks, 97% of Bulgarians, all Albanians and
  Bosniaks, 61% of Kurds and 55% of Armenians. Avoid China's 1912 "Five Races"
  with Tibetans and Uighurs, given today's Xinjiang and Tibet *(designer's
  call)*.
- Creating cultures at runtime. The engine can't; every merged culture is
  defined in files ahead of time. "Dynamic" means when and to whom a merge
  becomes available, and which optional parts join, not which merged cultures
  exist.
- Homeland *growth*. Dynamic Homeland Progress already forms homelands where a
  primary culture clears its threshold; a merged culture that is primary uses
  it unchanged. The only homeland work here is the switch (§6).
- Player policies. A handful of toggleable policies that speed a merge up or
  trade something for it are welcome later, **only if they make sense and are
  fun**. v1 ships without them *(designer's call)*.

**Anti-goals**

- **Identity targeting.** A merge models a nation that genuinely includes its
  parts, which needs good relations with them, the opposite of persecution.
  The equality conditions (§4) make that concrete: a Russia that treats
  Ukrainians as second-class, legally or economically, can't build an East
  Slavic culture. No player choice picks a named minority to absorb; optional
  parts join by circumstance (§4.3).
- **Colonial nation-making by the colonizer.** A country can't merge cultures
  none of which is its own primary (§4.1). The British East India Company holds
  97% of the Bengali group and the Dutch East Indies 70% of what would become
  Indonesian; neither may start those merges. An independent Indonesia can.
- **A merge that costs more performance than it saves.** The bookkeeping (a
  world census of the parts, §8) must stay far cheaper than the pops it
  removes.
- **Micromanagement.** Progress made while a merge is stalled is kept for when
  the stall lifts; hysteresis stops a merge flickering on and off near a
  threshold (owner, design defaults in `CLAUDE.md`).
- **A Russian merge that reads as "one people" propaganda.** The East Slavic
  merge produces a new culture named East Slavic, never Russian absorbing the
  others *(designer's call, given present-day use of that rhetoric)*.

## 3. Merges, parts and tiers

A **merge** has a **result** culture and a list of **parts**. Parts are
**core** (the merge is defined by them; at least one must be the starter's
primary culture) or **optional** (join only where the starter holds most of
them, §4.3). The result is either a **new** culture (German) or, for an
**absorb** merge, an existing one: Occitans and Catalans become French,
Paulistas become Brazilian, Yue and Hakka become Han *(designer's call, raised
by the owner's question "if France conquers Catalonia in 1837, would it be
considered French?": Roussillon, French since 1659, largely was by 1900)*.

Vanilla gives every culture a language, the language's family (its trait
group: Romance, Germanic, Slavic ...) and a heritage. That gives the tiers:

| Tier | Parts share | Examples | Extra conditions to start (§4.4) |
|---|---|---|---|
| 1 | Language and heritage | North + South German, Swedish + Norwegian + Danish, Russian + Ukrainian + Byelorussian | None |
| 1b | Language, across heritages | Afro-American joining American; English + Yankee as Anglophone | Very high acceptance; decades together under one state; a media-era technology |
| 2 | Language family | Latin (French, Italian, Spanish, Portuguese) | Its tier-1 merges finished in this country first; a long stretch with every part accepted |

**Tiers belong to parts, not to merges** *(designer's call)*. A part's tier is
its distance from the merge's other core parts. The core parts' tier sets when a
merge can start; each optional part's own tier sets when it can join. American
is a tier-1 merge of Yankee and Dixie (both settler heritage, same language),
which Afro-American joins as a tier-1b part once its stricter conditions hold;
French is tier 1 (French, Walloon, Occitan) with Catalan joining as tier 2.

**The config can set a part's tier by hand** where history disagrees with
vanilla's traits *(designer's call)*. Occitan is a separate language in vanilla
but joins French as tier 1 (owner: "I thought southern France saw themselves as
French comparatively early"). The Midi had been under the French crown for
centuries, and its national identity formed in the 19th century without a
separatist movement; the Félibrige (1854) was a literary revival. Catalan stays
tier 2: most Catalans live in Spain with a strong identity of their own.

**Overlapping merges** *(designer's call)*. A culture can be a part of several
merges (Scottish in British and Anglophone, Yankee in American and
Anglophone). A culture is in at most one running merge at a time, and a part
that has already merged is represented by its result: once American has
switched, Anglophone's Yankee part is American.

Tier 1b and tier 2 are both in v1, since the roster is generated and the extra
cost is mostly config (owner). Vanilla's language traits sometimes disagree
with history (Han, Yue, Hakka and Min are four languages in vanilla; Polish
shares a language with Czech and Slovak), so the roster is curated, not
derived mechanically from traits. Settler, diaspora and colonial cultures that
share a language with a European one (Boer with Dutch, Franco-Canadian with
French) are left out of tier 1 by default.

The full candidate roster, with 1836 numbers and a historical read for each,
is in **Appendix A**.

## 4. Starting a merge

A merge is started by the country (a decision or journal-entry button) once
every condition holds; the AI starts any merge it qualifies for (owner: the AI
runs merges). The AI starts it as soon as it qualifies *(designer's call: the
merge has no direct cost, so there is nothing for the AI to weigh; revisit if a
cost is added)*. A game rule turns the system off, following the mod's
convention for major systems *(designer's call)*.

### 4.1 Primary culture

At least one core part is a primary culture of the starter.

### 4.2 Holding most of each part

For **each** part, the starter together with its subjects (at any depth,
*designer's call*) and the members of a power bloc it leads holds a large share of that part's
pops **living in its homeland states** (owner: "you must have most of them"; subjects and bloc members
count so a dominant Germany can merge with an Austria still separate). The
share is tested per part, not on the parts' combined total, so a merge can't
fold in a part it doesn't hold. Starting value: 60% (owner).

**Proportions count homeland states only** (owner, 2026-11-07: "the Germans in
the USA that haven't assimilated yet don't matter for any of the proportion
gate stuff"). Every share in this design (this hold test, the meaningful
share in §4.3, and dominance at the switch in §6) is taken over the part's
pops living in the part's homeland states, wherever those states are and
whoever holds them. Diaspora pops still convert at the switch; they just don't
weigh on the gates. A part with no homeland state anywhere falls back to its
world population *(designer's call)*.

A core part that fails this blocks the merge. An optional part that fails it
simply sits out.

### 4.3 Equality

Every joining part, in each country where the merge converts it (the starter,
its subjects and the bloc members it leads, §5), is:

- **accepted**, and
- **close in standard of living** to the others.

Each converting country tests acceptance for its own pops (owner, 2026-11-07).
*(Designer's calls:)*

- **Accepted** is that country's average acceptance of the part's pops
  (vanilla trigger `country_average_culture_pop_acceptance`) against the
  threshold for accepted status.
- **Close** compares the parts with each other, as the owner put it ("all the
  cultures have similar SoL"): each part's average standard of living across
  the converting countries, weighted by pops, must be within a limit of the
  others'. The census (§8) gathers it.
- **Where the test runs**: a part joins when acceptance holds in every
  converting country that holds a meaningful share of it (starting value a
  tenth of what the starter's sphere holds of it in its homeland states); countries holding only a
  sliver neither count nor block. The test has to run where the part lives:
  Sweden holds almost no Danes, so a test in Sweden alone could never admit
  them. After a part has joined, a converting country that fails pauses
  conversion inside its own borders only.

On paper, Sweden in 1836: Swedes are tested in Sweden, Norwegians in its
subject Norway, Danes in a Danish bloc member; each is primary and accepted at
home, so the merge turns on whether their standards of living are close.

These conditions keep applying after the merge starts. A part that stops
meeting them **stalls** the merge (the core parts) or its own progress (an
optional part); progress is kept while stalled. Each condition has
**hysteresis** (owner): it stops at one value and resumes only at a stricter
one, for example a standard-of-living gap that stalls above 4 resumes only
below 3.

Parts can **join late** (owner): an optional part that starts meeting §4.2 and
§4.3 after the merge began, or after its switch (Germany later absorbing
Switzerland, its Alemannic pops accepted and prosperous), joins then. It
assimilates at the usual rate and gets its own switch (§6).

### 4.4 Technology and tier conditions

| Tier | Technology *(designer's call)* | Further |
|---|---|---|
| 1 | Pan-Nationalism (as the reference mod) | none |
| 1b | Mass Media | **very high** acceptance of every part (owner, for Afro-American in American), and a counter of years spent together under one state meeting §4.2–4.3 that must reach a few decades (owner: "under the same state for a period of time, and with good enough tech (and therefore common media)") |
| 2 | a later media or society technology the builder picks | each of the merge's tier-1 component merges (French, Italian, Spanish ... as config lists them) finished, with its result held in this country's sphere like any part (§4.2), so an Italy that ran its own merge inside France's bloc counts, and a long counter of years with every part accepted (owner liked this as the way to get "a century under France" without a fixed date) |

Counters keep their progress while a condition fails and resume when it holds
again (no-micromanagement default). Store them as country **variables**, not
modifiers or variable lists, so a revolution's winner carries them on
(`CLAUDE.md`, "A revolution's winner inherits the loser's variables").

## 5. While a merge runs

**Passive** (owner). On a regular pulse, a slice of each joined part's pops
changes culture to the result, via `change_pop_culture`'s fractional form.

**Where it converts** (owner, 2026-11-07): in the starter, its subjects and the
members of a power bloc it leads, the same countries whose holdings count
toward §4.2. Otherwise a starter that qualifies through them could never reach
the switch: Sweden in 1836 qualifies with its subject Norway and a Danish bloc
member, but holds almost no Norwegians or Danes itself. Conversion in subjects
and bloc members runs **somewhat slower** than in the starter (owner; *starting
value half the rate, designer's call*), at a rate built from that country's
own education, institutions and development. A country that leaves the bloc or
stops being a subject stops converting; pops it already converted stay
converted *(designer's call)*.

**The result becomes primary when conversion starts** in a country: the
starter when the merge begins, a subject or bloc member when it starts
converting *(designer's call)*. This serves the owner's second motive. Dynamic
Homeland Progress forms homelands only for primary cultures, so a state that is
40% North German and 30% South German forms a German homeland during the run
only if German is already primary. It also keeps Austria's growing German pops
from being non-primary in Austria for decades. The switch-time effect (§6, §7)
then only catches countries that never converted.

**The rate** comes from long-term choices and development (owner): public
education, the Ministry of Culture (`institution_ministry_of_culture`, already
in the mod), urbanization, literacy; media technologies (radio, film, mass
propaganda, as in the reference mod) fit too *(designer's call)*. Following the
mod's declarative-modifier practice, the speed should be a registered modifier
(for example `country_culture_merge_speed_mult`) granted by the laws,
institutions and techs that speed it, so its tooltip lists every source; per-pop
factors (profession, literacy) multiply it *(designer's call)*. As in the
reference mod, discriminated pops barely convert and pops living outside the
parts' homelands convert faster *(designer's call)*.

**Pace target** (owner): a tier-1 merge in a literate, urbanizing country
reaches its switch in about 20 years; a slow one takes about 40. Because a
running merge carries extra pops (below), the conditions to *start* are the
lever for keeping merges rare, not a long duration (owner). Tune from evidence
(pop sizes and rates, a days-to-switch table) before choosing numbers.

**Pop count during the merge.** Partial conversion splits pops: each building
gets a result-culture pop beside its part pops, so the pop count rises until
the switch removes the parts. The owner accepts the bump, since merges across
the roster save more than they cost. Converting in fewer, larger steps keeps it
small *(designer's call)*.

**Display.** The reference mod's fixed 100-year bar is replaced by real
progress *(designer's call)*: a journal entry per active merge showing the
result's share against the switch threshold, the current rate with its sources,
and the status of each condition and part (joined, sitting out and why,
stalled and why). Follow `docs/guides/gui_style_guide.md`.

## 6. The switch

When the result culture is **sufficiently dominant** (owner) over a joined
part, that part switches. *(Designer's call, revised while planning:)* dominance
is measured **per part, in that part's homeland states**: the result's share of
result plus part pops living there, at 60%, the hold that opens a merge (owner,
2026-11-07, replacing the designer's starting value of two thirds, which left a
sphere holding 60–66% of a part unable to finish; gaining more of the homeland
is the lever). A world total
of result plus parts doesn't work for absorb merges, whose result already
exists: French alone outnumbers Occitan and Walloon three to one, so a merge
measured that way would switch the day it started. Measured in the part's
homelands, German has to win Bavaria, and French has to win the Midi. The
merge is complete when every joined core part has switched. When a part
switches:

1. **Every pop of the joined parts, anywhere in the world, converts to the
   result** (owner: "the diaspora stops seeing themselves as from Bavaria and
   thinks of themselves as from Germany"), whoever owns it.
2. **Homelands**: every state that is a homeland of a joined part becomes a
   homeland of the result as well, including states other countries hold
   (owner: otherwise a North German homeland in France decays and a German
   one never forms, because homelands only form for primary cultures). The
   part's homeland **is kept** beside the new one (owner approved): with no
   pops left it costs nothing, and formables that count states by their
   cultures' homelands keep finding them (§7). Dynamic Homeland Progress
   would otherwise remove it wherever a law raises the removal threshold
   above 0 and the owner lacks the part as primary
   (`te_homeland_removal_candidate`), so that trigger skips a switched part
   **while the state is also a homeland of the culture it switched into**
   (owner, 2026-11-07). When Dynamic Homeland Progress removes the result's
   homeland from a state, the same step removes the homelands there of every
   part that switched into it, so an old homeland never outlives its
   successor.
3. **Primary cultures**: every country with a joined part as primary gets the
   result as primary too (§7).

A late-joining part (§4.3) switches the same way, on its own homeland states.

After the switch the merge stays open for late joiners; the journal entry
shrinks to what's left (late parts in progress) or completes when there are
none *(designer's call)*.

## 7. Keeping vanilla and the mod working

The parts remain **primary cultures** of every country that had them, forever
(the reference mod does the same). A primary culture with no pops is harmless,
and it keeps working every vanilla and mod check of the form
`country_has_primary_culture = cu:north_german`: the German unification
journal entry, pan-national movements, two technologies in vanilla
`30_society.txt`, AI strategies and the rest.

**By effect, not by generator** (owner): a monthly effect gives the result
culture to every country that has one of its switched parts as primary. That
covers Austria at the switch, a country formed or released later from a
definition that lists only the parts, and any formation that resets primary
cultures. Run the same effect from `on_country_formed` so a formation doesn't
leave a month's gap *(designer's call)*.

**What no effect can reach**: the culture lists in country definition files
(`cultures = { north_german south_german }`). Formables with
`use_culture_states = yes` (vanilla Italy, and the mod's formables in
`common/country_definitions/te_formable_countries.txt`, 154 cultures, and
`te_city_states.txt`, 25) count states by those cultures' homelands. Keeping
the parts' homelands at the switch (§6) keeps them working without editing the
lists.

**What goes dark after a switch**: pop-level checks on a part
(`has_pop_culture = south_german`), culture-keyed flavor (party and interest
group names, ruler titles in customizable localization, character templates,
clothing and portrait triggers), and in the mod: party names
(`populist_party`, `green_party`, `technocratic_party`,
`zz_te_party_join_weights`), flavored companies, formable dynamic names, Grand
Monument flavor (Greek, Irish, Mayan), the FPTP triggers (Yankee, Dixie) and
the Spanish/Catalan/Basque ideologies. The builder lists every reference to a part that is still live after a switch
and patches the ones that matter, giving the result culture its own entry where
flavor is keyed on culture *(designer's call)*. Appendix A gives per-merge
counts.

**Vanilla content that already works on the parts.** Some vanilla journal
entries convert, count or promote exactly the cultures a merge removes, and
several are open from 1836 or from Pan-Nationalism:

- `02_brazilian_nation_building.txt` and `events/brazil/culture_brazil_events.txt`
  (Colossus of the South, `has_dlc_feature = rp1_content`) already turn
  Paulista, Sulista, Nordestino and Amazonic into Brazilian, worldwide.
- `08_russification.txt` (`ip5_content`, from Pan-Nationalism) completes on
  `culture_percent_state target = cu:russian`, a share that falls as Russians
  become East Slavic; `08_cultural_renaissances.txt` builds Ukrainian and
  Belarusian fervor and movements.
- `00_acw_entries.txt`: `je_acw_reincorporate` reads Dixie homelands and
  loyalists; `je_acw_equality` reads Afro-American acceptance.
- `events/iberia_events/philippines_events.txt` converts Mestizo pops to
  Filipino.

The rule *(designer's call, following the owner's preference for INJECT over
REPLACE of vanilla)*: **a merge never overrides vanilla content.** A merge does
not start, and a part does not join, while a vanilla journal entry that works
on that part is active in the country; the config lists those entries per part.
The wait is capped *(designer's call: 20 years from when the merge first
qualifies)*, after which the merge goes ahead and the vanilla entry may no longer
complete. The renaissances, the Civil War entries and Brazilian nation building
have timeouts, but Russification has none: it ends only on completion, on Russia
losing every state in Finland, the Baltics and Poland, or on
`law_no_colonial_affairs`.

**Russification gets an injected outcome instead of a wait** *(designer's call,
owner asked whether an INJECT could do it)*. The entry targets Finns, Balts and
Poles, not the East Slavic parts; it clashes with the merge only through its
success outcome's test that 65% of the region's states are at least 15%
Russian (`je_russification_state_russian_culture_min`), since Russians turning
East Slavic lower that share. That test is inline in vanilla's outcome, so an
INJECT can't edit it, but it can add a second success outcome: vanilla's copied,
with the culture test widened to count East Slavic. One trigger reads one
culture's share, so during a merge a state 9% Russian and 9% East Slavic would
pass neither; the builder either accepts an approximation (either share at
15%, or both at 7.5%) or sums pop sizes in a helper, which is cheap over the
region's 23 states while the entry is open. The map's highlight reads the
scripted trigger `je_russification_state_is_russian_assimilated`, overridable on
its own. The copy duplicates vanilla's completion effect, so a vanilla patch to
the entry must be mirrored; that is still a smaller footprint than a REPLACE.
What the engine does with an injected outcome is unverified
(`scripting_best_practices.md` § "journal entries end through outcome blocks"),
so ship it with a self-check and fall back to the 20-year wait if it doesn't
apply. With it, East Slavic doesn't wait for Russification at all; it still
waits for the Ukrainian and Belarusian renaissances, which time out.

**Fervor follows the merged culture** (owner, 2026-11-07, after review, in
place of the build's waits on German National Identity and the Balkan League).
Vanilla reads parts' fervor in journal entries (German National Identity's
completion, the Balkan League's start condition) and in the German, Italian and
Yugoslav pan-national movements, and a switched part, with no pops, drifts
toward 0. Once a month every switched culture's fervor is set to that of the
culture it switched into, and at the switch the result takes the part's fervor
where its own is lower. An INJECT couldn't widen the Balkan League, whose test
sits in its start condition; this writes a culture's state, not vanilla
content, so the rule above holds.

**A switched part that reappears** (a vanilla event converting pops into it
after its switch) is converted on the next monthly pass *(designer's call)*;
the builder lists vanilla's `change_pop_culture` targets among the parts.
A row vanilla already performs is skipped where its content is present: the
Brazilian merge runs only without `rp1_content`, and otherwise vanilla's
nation building does the job. The builder checks the roster for more of these
before settling it.

## 8. The merged culture

Generated by a Python generator from one config (owner; the mod's usual
pattern, see `docs/auto_generated_files.md`). Per merge, the config names the
tier, the result (new or absorb), core and optional parts, and for tier 2 its
component tier-1 merges. For a **new** result culture the generator writes the
culture: name, color, name lists drawn from the parts', graphics and religion
of the largest part, and traits.

**Traits.** In 1.15 acceptance comes partly from shared traits, so the result
must sit at least as close to each part as the parts sit to each other: tier 1
takes the parts' shared language and heritage; tier 1b and tier 2 need a
language or heritage choice the builder settles (a new trait in the shared
family, as the reference mod did, or the largest part's) *(designer's call)*.

**Census.** No engine value returns a culture's pop count, so §4.2 and §6 need
one built by iteration. Because every share is taken in the part's homeland
states, the census walks those states (`every_scope_homeland_state` on the
culture), not the world. It must be cheap: run it rarely (a yearly pulse is the
starting point), only for parts of merges that are eligible-but-unstarted or
running, and never per pop per month *(designer's call)*. The conversion pulse's cost scales with the whole sphere (starter,
subjects, bloc members), not the starter alone; the performance anti-goal (§2)
is measured against that.

## 9. What's left to the builder

- All numbers: shares, hysteresis margins, counters' lengths, rates, the
  switch threshold, the pace target's calibration.
- The census mechanism and its cadence.
- The exact technologies per tier.
- Journal entry layout, and whether starting is a decision or a button.
- The v1 roster, starting from Appendix A's "include" rows; the owner reviews
  it.
- Traits for tier 1b and tier 2 results.
- Which post-switch references to patch (§7).
- Usual mod obligations: a `docs/systems/mod_systems/` file and index row, a
  player guide section, loc in American English, audits clean, a play-test
  list entry for what only the game can show.

## 10. Engine facts to verify

Ship the preferred version with a once-a-game `TE_SELF_CHECK` line where the
build rests on one of these (`CLAUDE.md`, "In-game checks"):

- `change_pop_culture` with a fraction splits the pop and merges the converted
  share into an existing pop of the result culture in the same building and
  profession, if there is one.
- Whether forming a country *adds* its definition's cultures to its primaries
  or *replaces* them (`scripting_best_practices.md` says adds; the reference
  mod's comments say formation can leave a country with no cultures).
- A homeland of a culture with no pops anywhere has no visible or mechanical
  side effect beyond the state panel listing it.
- `country_average_culture_pop_acceptance` reads acceptance the way the
  equality condition needs, and what value marks accepted status in 1.15.

---

## Appendix A: candidate roster

Sources: `vanilla_parsed/` (1.15), start-date pops from vanilla
`common/history/pops/`, and a whole-token scan of vanilla and mod `common/` and
`events/`. **States**: state and owner pairs where a part lives in 1836;
**shared**: those where two or more parts live side by side, which is where a
merge removes pops at the start (German shares 1 of 78; most of its saving
comes later from migration). **Top holder**: the largest holder's share of the
parts' world population (§4.2 now reads homeland states only, which raises these
for parts with a large diaspora); low values mean a
unification must come first. **Logic files**: vanilla events, journal entries,
decisions, triggers, effects, techs, movements and AI strategies naming a part.
The French and British rows' numbers include Occitan, Catalan, Breton and Welsh.

The **Read** column is the designer's. The owner has agreed the tiers, Latin,
American with Afro-American and English with Yankee, but has not reviewed the
roster row by row.

| Merge | Tier | Result | Core parts | Optional parts | Pop 1836 (M) | States / shared | Top holder | Logic files | Read |
|---|---|---|---|---|---|---|---|---|---|
| German | 1 | new | North German, South German | Alemannic, Eastern German | 38.2 | 110 / 5 | PRU 31% | 37 | Include. Strongest case; needs unification. Ashkenazi speak Yiddish in vanilla with their own heritage: not a part. |
| Italian | 1 | new | North Italian, South Italian | Corsican | 20.8 | 30 / 1 | SIC 34% | 24 | Include. |
| Scandinavian | 1 | new | Swedish, Danish, Norwegian | Icelandic | 5.5 | 25 / 1 | SWE 49% | 6 | Include. Pan-Scandinavianism was real (1840s–1864). |
| East Slavic | 1 | new | Russian, Ukrainian, Byelorussian | | 42.6 | 101 / 36 | RUS 94% | 50 | Include, named East Slavic (§2). Reachable from 1836; big saving; the equality conditions are the filter. Russification gets an injected outcome; waits for the renaissances (§7). |
| Yugoslav | 1 | new | Serb, Croat, Bosniak | Slovene, Bulgarian | 4.5 (7.4) | 17 / 12 | TUR 30% | 32 | Include. Illyrian movement, Yugoslavism; three religions. |
| Czechoslovak | 1 | new | Czech, Slovak | Sorb | 5.7 | 13 / 1 | AUS 67% | 10 | Include. Polish excluded though vanilla shares the language. |
| Hungarian | 1 | absorb | Hungarian, Szekler | | 4.7 | 14 / 3 | HUN 85% | 22 | Include. Small. |
| Dutch | 1 | absorb | Dutch, Flemish | | 5.1 | 22 / 1 | NET 50% | 3 | Include. Boer, Griqua excluded. |
| Finnish | 1 | absorb | Finnish, Karelian | | 1.5 | 17 / 2 | FIN 80% | 5 | Include. Estonian is its own nation. |
| French | 1 (Catalan 2) | absorb | French, Walloon, Occitan | Catalan (tier 2) | 34.2 | 49 / 9 | FRA 88% | 39 | Include. The owner's Catalonia case. Breton is Celtic, another family (§2). |
| British | 1 | absorb | English, Scottish | | 17.6 | 55 / 11 | GBR 99% | 20 | Include. Welsh, Irish and Gael are Celtic, another family (§2). |
| American | 1 (Afro-American 1b) | new | Yankee, Dixie | Afro-American | 15.0 | 43 / 24 | USA 100% | 23 | Include; Afro-American only with very high acceptance (owner). Waits for the Civil War entries (§7). |
| Anglophone | 1b | new | English, Yankee | Anglo-Canadian, Australian, Scottish, Dixie, Afro-American (1b) | | | | | Include (owner): needs one state holding both cores for decades. Overlaps British and American (§3). |
| Brazilian | 1 | absorb | Brazilian, Paulista, Nordestino, Sulista, Amazonic | Afro-Brazilian | 4.5 | 24 / 17 | BRZ 87% | 13 | Include only without Colossus of the South, whose nation building already does this (§7). |
| Platine | 1 | new | Argentine, Uruguayan, Paraguayan, Platinean | | 0.9 | 15 / 0 | ARG 73% | 9 | Include. |
| Andean | 1 | new | Peruvian, Bolivian, North Andean, South Andean | | 3.8 | 28 / 0 | | 13 | Include. Peru–Bolivian Confederation, 1836–39. |
| Gran Colombian | 1 | new | Colombian, Venezuelan, Ecuadorian | | 0 | | | 6 | Check: these cultures have no pops in 1836. |
| Chinese | 1 | absorb into Han | Han, Yue, Hakka, Min | | 338.7 | 76 / 12 | CHI 100% | 129 | Include. Four vanilla languages, one historical Han identity. Absorbing keeps Han's 129 references working. |
| Japanese | 1 | absorb | Japanese, Ryukyuan | | 32.7 | 15 / 3 | JAP 99% | 29 | Include. |
| Arab | 1 | new | Maghrebi, Misri, Mashriqi, Bedouin, Yemenite | Sudanese, Haratin, Bidan | 15.7 | 77 / 24 | EGY 38% | 12 | Include. Maltese excluded (Catholic, European heritage). |
| Persian | 1 | absorb | Persian, Luri | Tajik, Hazara | 6.4 | 50 / 17 | PER 59% | 11 | Include. |
| Oghuz Turkic | 1 | new | Turkish, Azerbaijani, Turkmen | | 10.4 | 64 / 2 | TUR 72% | 14 | Include. Pan-Turkism; Shia/Sunni split. |
| Hindustani | 1 | absorb | Hindustani, Avadhi, Bagheli, Bundeli, Chhattisgarhi | | 36.0 | 28 / 7 | BIC 72% | 6 | Include. Pathan, Deccani excluded (other heritages). |
| Dravidian | 1 (Telugu 2) | new | Tamil, Malayalam, Kannada | Telugu | 26.8 | 21 / 11 | BIC 60% | 7 | Include. Dravida Nadu demand, 1940s–60s. |
| Indonesian | 1 | new | Javan, Sumatran, Malay, Bornean | Balinese | 11.7 | 34 / 0 | DEI 70% | 2 | Include; the colonizer can't start it (§2). |
| Filipino | 1 | absorb | Tagalog, Visayan, Ilocano, Filipino | Filipino Hispanophone, Filipino Mestizo | 2.5 | 6 / 4 | PHI 100% | 3 | Include. Moro, Lumad: other religions, equality decides if added. |
| Nguni | 1 | new | Zulu, Xhosa, Nguni | | 1.1 | 13 / 3 | ZUL 28% | 2 | Include. Small. |
| Latin | 2 | new | French, Italian, Spanish, Portuguese results | Romanian; Argentine, Platinean, Uruguayan, Chilean | 51.7 | 108 / 5 | FRA 37% | 73 | Include (owner). Pan-Latinism (Chevalier, Napoleon III, the Latin Monetary Union of 1865). Romanians made Latin descent central to their identity (the Transylvanian School, the Latin alphabet from 1860). New World parts (owner: the ones that didn't see themselves as of Native American heritage): the Southern Cone, which saw itself as European and embraced *latinidad* (Rodó's *Ariel*, Uruguay 1900). Mexico (*mestizaje*, Vasconcelos), the Andes (*indigenismo*) and Brazil (Freyre's mixed "racial democracy") are left out. Argentine, Uruguayan and Chilean have no pops in 1836; vanilla splits them off later. |
| Pan-Slavic | 2 | new | East Slavic, Czechoslovak, Yugoslav results | Polish, Slovene, Bulgarian | | | | | Include *(designer's call, owner didn't object)*. The Prague Slavic Congress of 1848; Russian pan-Slavism. |
| Pan-Turkic | 2 | new | Oghuz Turkic result, Tatar, Kazakh, Kyrgyz, Uzbek | Bashkir, Crimean Tatar, Caucasian Turk, Uighur | | | | | Include *(designer's call)*. Gasprinski's "unity in language, thought and deed". |
| Pan-Malay | 2 | new | Indonesian, Filipino results | | | | | | Include *(designer's call)*. Malay comes through Indonesian (§3, overlapping merges). Rizal's "Malay race"; the Maphilindo proposal of 1963. |
| East African (Swahili) | 2 | new | Swahili, Nyamwezi, Sukuma | Yao, Makua, Lacustrine Bantu, Kikuyu | | | | | Include *(designer's call)*. Nyerere's Tanzania built a national identity on Swahili across more than 120 peoples. Builder checks the parts' languages and holders. |
| Pan-Germanic (German, Dutch, Scandinavian) | | | | | | | | | Skip: the only state project for it was the Nazis' "Greater Germanic Reich". The 19th-century Pan-Germanism of all German speakers is the tier-1 German merge. |
| Pan-Bantu | | | | | | | | | Skip: "Bantu" as an identity was a colonial and apartheid category (Bantu Education, the Bantustans); no movement claimed it. |
| Latvian + Lithuanian | | | | | 1.6 | 13 / 4 | | 6 | Skip: distinct nations, religion split. |
| Irish + Gael; Breton + Welsh | | | | | | | | | Skip. |
| Bengali + Bihari + Oria | | | | | 55.5 | 15 / 0 | BIC 97% | 6 | Skip: three distinct linguistic nationalisms. |
| One Hispanic culture (19 cultures) | | | | | 20.3 | 101 / 47 | SPA 37% | 47 | Skip; the regional blocs above are the plausible ones. |
| Small groups (Sotho + Tswana, Lacustrine Bantu, Siouan, Apachean, Numic, Kru, Gbe ...) | | | | | under 1 each | | | 0–1 | Skip: negligible saving, thin historical case. |

The Latin row's numbers sum its five largest component cultures (French, North
and South Italian, Spanish, Portuguese).
