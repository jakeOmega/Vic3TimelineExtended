# Writing in-game text

**Adopted 2026-11-09**, after the owner read two rounds of sample text written from its drafts. Two lints hold new text to the parts a machine can check (§ "What the machine checks").

**Who writes it.** Event text is written by the strongest model available (owner, 2026-11-09: Opus-class or better; in the trials a smaller model followed the rules but wrote flatter text and checked less of the script). Labels, tooltips and modifier descriptions are within any model's reach with this guide.

This is the house style for everything under `localization/english/`: what a player reads in the game. It says how each kind of text should read. Where it and `event_creation_guide.md` differ on voice, this guide wins; that guide keeps the mechanics of events (keys, scope references, images, option design). Other homes:

- Labels that fit their cells, type sizes, what goes in a tooltip and what in a How section: `gui_style_guide.md`.
- Loc syntax (scope references, `#b`, concept links, quoting): `.claude/rules/localization.md` and `scripting_best_practices.md`.
- The player guide, which is prose about the game, not text in it: `docs/player_guide/STYLE.md`.

## The voice

The game's text is plain and particular. It names the thing, gives the figure, and stops.

Three tests cover most cases.

**Could this sentence be about anything else?** "The resolution has brought stability and improved relations with our neighbors" fits a treaty, a wedding or a new bus route. "The loan and a tenth more, over five years" fits one thing. If a sentence would survive being moved to a different modifier, event or law, it is filler: replace it with the particular fact, or cut it.

**Could a game make this sentence false?** See [Detail that cannot be wrong](#detail-that-cannot-be-wrong).

**Is the sentence trying to be admired?** See [No kicker](#no-kicker). This is the commonest fault in the mod's event text and in drafts written from this guide.

The register is a capable official briefing the government. Not a press release ("a hallmark of a modern, healthy society"), not a textbook ("this represents a significant shift"), not a film trailer ("the cultural establishment is reeling"), and not a columnist either: the official does not polish a remark and wait for the laugh.

## No kicker

A kicker is a last line built to land: a dry reversal, a hint left hanging, a neat irony, a short sentence after long ones. Examples from the mod and from drafts:

- "Nobody has yet said whether the books were wrong or were written to be."
- "If we don't, what exactly are we for?"
- "They sent me a pamphlet about cultural enrichment."
- "The bankers reply that they were leaned on once before."
- "Keeps it. Very carefully."

Each is fine alone. The trouble is that a writer, and a language model above all, reaches for one every time, so every text in the game ends on the same beat, and by the tenth event the player hears the machinery. An earlier draft of this guide said "end on a fact, not a mood", and the writers it was tested on swapped the mood for a quip, which is the same habit.

What marks the first example as machine-written, taken apart:

- **It reports something that has not happened.** "Nobody has yet said" is the narrator pointing at a silence so that the reader will fill it. The narrator knows nothing the sentence does not hint at.
- **Its grammar is ornamental.** "Were wrong or were written to be" leaves out a word so that the reader has to complete the phrase, and the pleasure of completing it is the sentence's whole content.
- **It is the paragraph's last sentence,** where a draft feels something is owed.

The rules:

- **A text ends when the facts are told.** The last sentence is as plain as the others: the last thing that happened, or what is now being asked of the government. If the paragraph is complete without its final sentence, delete the final sentence.
- **The narrator does not insinuate.** Say what is known. If fraud is suspected, somebody in the text suspects it: "The auditors have asked who signed the quarterly counts."
- **No sentence that needs the reader to finish it,** and no two-part sentence whose second half reverses the first.
- **This is a ban, not a ration** (owner, 2026-11-09). A turn at the end is acceptable when it is rare, and the ones that slip through will keep it from being absent. Do not write one on purpose.

> **Kicker:** An audit of the grain reserve has found that a tenth of the stock has rotted in its silos. The warehouse books listed every sack as sound. Nobody has yet said whether the books were wrong or were written to be.
> **Plain:** An audit of the grain reserve has found that a tenth of the stock has rotted in its silos. The warehouse books list every sack as sound, and the quartermaster's office signed each count. The auditors want to know who did the counting.

## Detail that cannot be wrong

An invented detail makes a text particular, and is welcome, **as long as no game can contradict it.** The same event fires for Sweden in 1850 and for Singapore in 2020. Before keeping a detail, ask what a country would have to be for the sentence to be false, and whether the event's trigger rules that country out.

Things an event may not assume unless its trigger guarantees them or the text reads them from a scope:

| Assumption | How it goes wrong |
|---|---|
| Elapsed time, dates, "for two years", "since the war", "a generation ago" | The reserve was built last year; there was no war |
| Quantities of anything the game tracks (tons in the reserve, the size of the army, the price of bread) | The game shows a different figure one click away |
| Crowds and audiences by the number: "millions shared it", "thirty million watched", "a hundred thousand marched" | Population is tracked too, and the country may have two million people |
| Era and technology (telegrams, radio, cars, cameras, the internet, a railway) | The event fires in 1840, or in 2030 |
| Religion, clergy, holy days, places of worship | A sermon in a country with no church |
| Culture: personal names, food, dress, forms of address | "Sir" and "Father" are English and Christian |
| Climate and land: snow, monsoon, a coast, a river, mountains, a desert | A landlocked tropical country |
| Government: a king, a parliament, elections, parties, a free press, ministries | An absolute monarchy has no opposition benches |
| A cabinet post or a minister by title; "the bill", "the chamber", "the vote" in an enactment event | Laws are enacted under every form of government, and no trigger backs a foreign minister |
| Economy: factories, a stock exchange, private banks, wage labor, slavery | A command economy, a subsistence one |
| Other countries: "the Americans", a neighbor, a great power, an empire | They may not exist, or may be us |
| Peace or war, colonies, a navy | Any of them may be absent |
| "Overseas": a coast, ships or quays for a colony | In this mod a colony is a separated territory, and may be reached across another country's land |
| A delivery system for a nuclear weapon: missiles, silos, bombers, submarines, a test site | Each is a technology and a geography. "The weapon", "the crews" and "the bases of our nuclear forces" are always safe |
| People at a space colony: colonists, settlers, scientists on site | A site can start with nobody and stay an automated outpost |
| That the reader is the one who acted | A notice sent to both sides of an act (the holder and the occupier), or to every country, is read by each of them |

Three ways to keep a detail that is at risk:

1. **Read it from the game.** `[ROOT.GetCountry.GetAdjective]`, a state's name, a law's name, a script value for the figure.
2. **Gate it.** A variant description or flavor (`first_valid`, a triggered `desc`) for the countries where it holds, with a neutral default last. "The Old Rules" does this for its priest.
3. **Write it one level more general.** "A message arrived before dawn", not "the telegram"; "the district's elders", not "the parish council"; "for as long as the ledgers go back", not "for two years"; "a tenth of the stock", which is the mechanic, not "twelve thousand tons".

Details that are always safe are the ones the game holds no fact about: what a clerk said, the state of a ledger, a queue, the hour, someone's hands, the order in which things were found. An invented, unnamed person's own history is safe ("forty years on the line"); an office they held is not ("three terms in cabinet" assumes a cabinet).

**Pronouns.** An invented person in a description is "they". In flavor, a speaker or a figure in a scene may be "she" or "he", unless the role is one the country's laws may close to them (a woman candidate where women cannot stand): then read the law, gate the text, or leave the person ungendered.

**A real quotation** may be older or younger than the game's year; leave the date off its attribution.

### What a chain's triggers already guarantee

The other half of the rule: do not hedge what is secured. Read the event's `trigger`, and what fires it, and use what they guarantee. `python3 scripts/analysis/event_guarantees.py <event id or namespace>` prints an event's required technologies, what follows from them, the rest of its trigger, and what the gates outside the trigger add. Each batch of event work records what it found, so the next writer in that chain starts from it. The rows that hold for every chain are in the table below, with the elections pilot's row and the rows written before the rewrite; **the rows for every other chain are in [`event_text_guarantees.md`](event_text_guarantees.md)**, one section per system (2026-11-12, #1539). Read the chain's row there before writing, and correct it when the script changes.

Most gates sit outside the event's own `trigger`, and since #1622 the tool follows them. It lists each under the label of where it came from, then totals the technology: `from outside` is what every route that reaches the event gives, and `in all` adds the event's own trigger. A guarantee from outside holds only if **every** route gives it, so one route the tool marks `not followed` leaves nothing from outside until you have read that route yourself.

- **An event that tests `is_enacting_law`** (`law X unlocks at`) has the law's own `unlocking_technologies` and one of its `unlocking_laws` (Ministry of Thought Control needs a single-party state, a secret police law or outlawed dissent). Of several unlocking technologies only what each gives is sure: whether the engine needs all of them or any one is unverified (Intrusive Surveillance, `social_media` and `automated_surveillance`, is the only such law). The law is being enacted, not in force: what it would create does not exist yet. **A law in force guarantees no technology** (#1653): `has_law`, and the laws that unlock the one being enacted, can be laws the country began the game with or was handed by `activate_law`, and neither checks the technology. Serbia and Greece begin 1836 with State-Led Language Reform, which unlocks at `mass_media` (era 6), so its events can reach the 1840s. The tool prints that technology on its own line, `if enacted in play`, under `in all` and never in it; a text may not rest on it.
- **An event a journal entry fires** (`journal entry Y requires`) has that entry's `possible` and `is_shown_when_inactive` (the world war events have `combined_arms`; the post-scarcity events have Post-Work Society, era 12), and can never see the law or outcome that ends the entry. The tool reads them as they were when the entry activated, so it totals their technology only: a law or a rank the entry tested may have changed. An entry that an effect also adds (`add_journal_entry` skips both tests) gives only what the add's own tests share with them, and an add the tool cannot tie to one entry (`type = je_$M$` with no call that says which) counts against every entry it could name.
- **An event drawn from a weighted pool** (`pool weight tests`) whose base weight is 0 has every technology and phase its `modifier` blocks test, one branch of them at least, and nothing an `if` outside them adds (`banking_cycle_effects.txt`). The tool marks such an add `! weight added outside that gate`; it is a script bug.
- **An event another event or an effect sends** (`sent by`) has what its sender's effect did and the tests around the `trigger_event`, and nothing of the sender's own technology.
- **A scripted trigger** (`scripted trigger X tests`, as for `has_augmentation_tech`) is opened one level.

What the tool still cannot follow, so look for it by hand: a decision, a scripted button, a treaty article or a diplomatic action that fires the event (each prints as `not followed`); a latch variable (the banking draws have `stock_exchange` because `te_banking_cycle_running` reads a variable set behind it); a building's own technology (`wonder_events` test a megaproject's site); `owner = { ... }` in a state event; a trigger vanilla gives one of its own on-actions; and anything about a country other than the receiver.

| Where | Guaranteed | Not guaranteed |
|---|---|---|
| Any event behind a technology | That technology, its prerequisites all the way down, and **every technology more than two eras behind it** (owner, 2026-11-09). A technology cannot require one from another category, so the prerequisites alone miss the obvious: `social_media` (era 9, society) does not require the telephone (era 4, production). Technology spread makes anything three eras back as good as certain, so an era 9 event may assume all of eras 1 to 6. `python3 scripts/analysis/event_guarantees.py <event id>` prints both lists | A technology one or two eras back that is not a prerequisite; later technology; that the *other* country has any of it |
| Any event of a system with a game rule | The system's journal entry and its vocabulary | That the player has opened the tab |
| An option with its own `trigger` | What that trigger tests, in that option's text only | The same in the description |
| A flavor or description shown beside a `first_valid`, or under every outcome of a notice | Only what every branch and every reader has in common | Any one branch's outcome: "their answer came" read as a refusal under the acceptance (`society_technology_events.35`) |
| An event sent to every country, or to both sides of an act | That the act happened | Anything about the receiver, even the technology the actor used |
| A state with a Local Climate record (`te_climate_winter_eff`, `te_climate_aridity`, `te_climate_malaria`, at state scope) | Weather, where a variant is gated on the record: `resettlement.3` shows its winter only where the coldest month freezes | Local weather on a trigger that reads only the world's temperature anomaly |
| `modern_election_events` (all 35 sit at weight 1 in vanilla's `elections_monthly_events` pool and need `in_election_campaign`, no single-party state and no `election_event_cooldown`, so any can follow any other or a vanilla election event) | An election campaign: parties standing, candidates, voters, a vote still to come. Newspapers (every event is at least era 5). Each event's own technology: television only where its tree reaches `television_broadcasting` (.1, .4–.10, .19, .22, .24, .29, .32); the web only in .2, .4, .28, .33, .35. Film and newsreels in .11 and .12. Radio in .11, and no television there (neither `television` nor `television_broadcasting`). The industrialists' party in .7 and .13 (`corp_party`, `press_party`). An opposition party in .1, .2, .5, .9, .22; a governing party only in .9. A colony in .32 only with the space race on; a surveillance apparatus in .25; a civil rights movement in .16; a running banking cycle in its expansion, boom or frenzy phase in .15; the `brain_computer_interfaces` technology in .33 and `lab-grown_food` in .34; a global anomaly of 1.0 °C in .3 and .27, readable as `temperature_anomaly_display` | `govt_party` and `opp_party` anywhere else: every event `exists`-guards them, and .28 has a variant for the case. The issue parties (`scope:<FOR>` and `scope:<AGAINST>` from `me_save_issue_parties`, in .3, .14, .16, .20, .21, .23, .24, .26, .27, .29, .31–.35): either can be missing. Television in .14, .16–.18, .20, .21, .23 and the other late events not listed. A telephone: the society and production trees cross less than they look, so `social_media` does not bring `telephone` and `cyber_warfare` does not bring the web. A free press (outlawed dissent is possible), a parliament or court of a given shape, two-party politics ("bipartisan"), a war fought, private firms, local weather or refugees at our border (.3 and .27 need only the global figure), neural-interface voting already in use (.33: the interfaces exist, the vote by them is a proposal) or synthetic food on sale (.34: the Cultured Meat Plant and Cultured Produce Facility can be built but need not exist). Whether the vote is days or months away |
| The events that report what was done to us (2026-11-10: `minor_events_timelineextended.10`, `un_vote.8`, `te_union.2`, `te_inflation.2`, `irredentism.12` / `.13`, `te_pb_summit.2`, `nuclear_weapon_events.33`, `te_orbital_debris.2`). Each is sent by the effect it reports, so that effect has run | `.10`: a year at an average standard of living below 4, a capital, not decentralized. `un_vote.8`: a United Nations, a carried vote and its count, the proposer. `te_union.2`: we had adopted a bloc's common currency. `te_inflation.2`: a hyperinflation, dollarization since, a monetary law now in force. `irredentism.12` / `.13`: the member is in a power bloc it does not lead, both countries exist, a proposal of union was welcomed. `te_pb_summit.2`: we are in a bloc another country leads. `.33`: we were struck, accepted the strike as unordered and asked for reparations. `te_orbital_debris.2`: we are at war with the striker and have a Space Program or an orbital megaproject | `.10`: that the country had any of the nine buildings or any institution to lose, a coast, a railway, an unpaid civil service (the treasury may be full). `un_vote.8`: that we are a member or have a delegation seated. `te_union.2`: that we are still in the bloc; which of the causes ended the currency (the text is gated on the first only). `te_inflation.2`: notes or coin (the law may be digital or commodity money). `te_pb_summit.2`: that we share the bloc's faith or governing movement. `.33`: that the struck place was a city of any size |
| `space_race_events.3` and `.7`, the Moon and Mars landing reports (2026-11-11). Each is fired by its milestone entry's completion in `je_space_race.txt`, after `sr_complete_moon_landing_effect` / `sr_complete_mars_landing_effect` has recorded the milestone. The milestone's reward is paid by the option, not before it | The landing has happened and the crew is down, so descriptions and options speak after it. In each option, the site (`.3`) or approach (`.7`) chosen earlier in `.5` or `.83`, which is that option's `trigger`, and the ten-year modifier it pays | That we were first: `sr_was_first_moon_landing` / `sr_was_first_mars_landing` pick the description and flavor, and every option shows under both. That a site or approach was chosen at all (the fallback options `.3.c` and `.7.e`). Any technology beyond the milestone entry's: the events test none, and `event_guarantees.py` finds only what the entry's `possible` requires, `space_exploration` (era 7, so eras 1 to 4) for the Moon and `knowledge_economy` (era 9, so eras 1 to 6) for Mars; the re-entry after a programme loss adds the entry by effect, behind `sr_reentry_due_<milestone>`, which repeats that test. A station, a robot or a flag as anything the game tracks |

## Who is speaking

**"We", nearly always.** The player's country speaks as itself in events, options, modifier descriptions, notifications, journal entries and tooltips: "we", "our". This is the base game's voice.

The exceptions, in order of precedence:

1. **Flavor text has its own speakers,** who talk as themselves.
2. **Text the game displays on a country that is not the player's** (a modifier listed on a foreign country, a tooltip on a foreign state, a diplomatic row) says "this country" or names it, because "we" would be false there. If the player only ever sees the text on their own country, it is "we", even when other countries hold the same modifier unseen.
3. **A concept description states a rule about any country:** "a country", "the holder". Where the rule is easier to follow from the player's side, "we" is fine. "You" is for a control the player's hand works: "Where you want the policy rate to end up."

## Each kind of text

Lengths are in words, counting a scope reference or a spliced name as one. "Now" is what the mod's text measures today (median, and the 90th percentile).

| Kind | Keys | Its job | Length | Now |
|---|---|---|---|---|
| Name | most keys without a suffix | Say what it is in the fewest words that tell it apart | 1–4, Title Case | |
| Modifier description | `*_modifier_desc` | Why the country has this, in the world's terms | one sentence, under 20 | 15, 26 |
| Law description | `law_*_desc` | What the law provides, concretely enough to tell it from its neighbors | 1–3 sentences, under 45 | 23, 42 |
| Button | `*_button`, `*_button_desc` | Name: the action as a verb. Description: what pressing it does, then what it costs or ends | name 2–5; description 1–2 sentences | 15, 21 |
| Tooltip | `*_tt`, `*_tooltip` | Answer the question the hover asks: what is this, why this value, why greyed | 1–3 sentences; a breakdown is one "Label: value" line each | 13, 46 |
| Concept description | `concept_*_desc` | The rule, complete enough to plan around, with links to the concepts it touches | 40–120 | 54, 145 |
| Journal entry text | `je_*_reason`, `_goal`, outcome keys | What is happening, what ends it, what each ending does | as long as the rules need; lists for lists | |
| Notification | `notification_*_desc` | What just happened and what it changes for us | 1–2 sentences | |
| Event title | `<ns>.<n>.t` | Hint at the theme | 2–5, Title Case | 3, 5 |
| Event description | `.d` | What is happening and who is involved | 30–80 | 41, 67 |
| Event flavor | `.f` | One scene or exchange, from someone's point of view | 50–150 | 44, 78 |
| Event option | `.a`, `.b`... | What the ruler says | 5–15 | 5, 9 |

### Names

A name tells the thing apart from its neighbors in a list. Prefer the plain noun to the grand one: "Family Planning", not "Comprehensive Family Planning Initiative". A button's name is what pressing it does: "Stop Retiring Oil Rigs", "Bring It Home".

### Modifier descriptions

The modifier's lines already show what it does. The description says why we have it, in one concrete sentence, and does not restate the effects.

> **Before** (`border_dispute_resolved_modifier_desc`): The resolution of a border dispute has brought stability and improved relations with our neighbors.
> **After:** We have settled a border dispute with a neighbor.

> **Before** (`predictive_intelligence_only_modifier_desc`): AI is used only for intelligence analysis, not direct policing, balancing security with civil liberties.
> **After:** Our analysts use prediction software to sort intelligence reports. The police do not use it.

"Brought stability" and "balancing security with civil liberties" are the effects restated as abstractions; the modifier's own lines say them better. Where the terms are the interesting part, give them:

> **As it should be** (`un_loan_repayment_modifier_desc`): This country is repaying an emergency loan from the United Nations: the loan and a tenth more, over five years.

**Find the reason in the script, not in the modifier's lines.** Look up what adds the modifier (`/references/<name>` on the server, or grep `common/` and `events/`): the event option, the journal entry's completion, the button. The description names that cause. If you find yourself turning an effect into a story ("scientists are leaving" for an innovation penalty), you are restating the effect. Say what was done ("We have put every citizen under watch") and leave the consequence to the numbers.

**A timed modifier describes the event, not a standing state.** The tooltip shows the time left, so the text does not say "temporarily". But a modifier that fades should not read as a law in force: "We have banned non-medical augmentation" sounds permanent and may sit beside an augmentation law that says otherwise. Write what happened: "Our government has ordered an end to non-medical augmentation, and the clinics are closing." For a modifier that lasts while something else does, name that thing: "while the relief lasts", "until the loan is repaid".

### Law descriptions

Say what the law provides and who decides, plainly enough that a player can tell it from the law beside it. Do not argue for the law.

> **Before** (`law_state_sponsored_family_planning_desc`): Empowering citizens with the knowledge and means to choose the size of their own family is a hallmark of a modern, healthy society. The state provides education and access to contraception to manage population growth.
> **After:** The state teaches family planning and supplies contraception to anyone who asks.

> **As it should be** (`law_statutory_courts_desc`): Judges hold office for life or by career and cannot be dismissed for their rulings, but they apply the law as written. Whoever makes the law, a parliament or a king in council, has the last word: no court can strike it down.

### Tooltips, concepts and journal entry text

These explain rules, so they are judged on whether a player could act on them.

- **Lead with the answer.** The first sentence says what the thing is or does. Conditions and exceptions follow.
- **Give the figure and its unit together, where the reader meets it:** "rises 2 a month", "for a year", "3% of its throughput". Not "a small amount", and not a unit stranded at the end of the clause.
- **Write a formula as a sentence with an example**, not as compressed prose: "divided by its owner's transmission efficiency: a third more at 75%", not "pays this over its owner's transmission efficiency".
- **Several figures are a list**, one "Label: value" line each, with the explanation after.
- **Name the tab, not the journal entry**, when sending the player somewhere.
- **Link a concept the first time it appears** in a text, and not again.
- **A historical or setting term links a glossary entry, not a concept.** Concepts explain mechanics; the glossary explains vocabulary such as "zaibatsu" or "the Sejm" (`[glossary_zaibatsu]`). Link vanilla's entry where it has one; a new term gets a glossary entry. The rule and the syntax: `scripting_best_practices.md` § "A historical or setting term gets a glossary entry, a mechanic gets a concept".
- **Say only what the script does.** A tooltip that promises an effect the script does not produce is a bug. Read the script first.
- **A limit nobody reaches is not a figure to give.** "Up to 15 legitimacy" was true of a gap of 100 points, which no game sees. Give the rate and one worked case: "0.15 for each point of the gap: 4.5 at a gap of 30".

> **As it should be** (`concept_banking_rate_target_desc`): Where you want the [policy rate] to end up. Stepping it does not move the rate today: the rate closes the gap a little each month. There is no fee and no cooldown for changing it.

It answers the three things a player wonders on first seeing the control: what it is, why nothing happened when they clicked, and what it costs.

### Events

`event_creation_guide.md` has the mechanics. For the voice:

**The description reports particulars.** A reader should see the situation, not be told how serious it is.

> **Before** (`banking_cycle_events.3.d`): Banks are sitting on mountains of reserves while businesses starve for credit. Lending has ground to a near-halt as financial institutions, scarred by recent uncertainty, refuse to take on risk. Merchants and manufacturers are demanding that the government intervene to restart the flow of capital - but bankers warn that forcing premature lending could plant the seeds of the next crisis.
> **After:** Our banks hold more in reserve than they have in years and are lending almost none of it. Sound businesses with goods in their warehouses cannot borrow against them to pay wages. Merchants and manufacturers have asked the government to make the banks lend. The banks say they will lend when borrowers look safer.

The first version has four stock metaphors (mountains, starving, grinding to a halt, planting seeds). The second says who cannot borrow, who is asking for what, and what the banks answer, and it stops there.

**Options are where the ruler speaks,** and the one place a light or exclaiming tone belongs. They are short because the button is: 5 to 15 words. The base game's usual note is a brief, human reaction: "Thank goodness for quick-thinking engineers!" That is the ideal. Plain is acceptable; **lean flat before quippy** (owner, 2026-11-09). A grave event gets grave options, and no event needs a joke on every button.

> **Too flat to be the ruler speaking:** Use the data.
> **Good:** Buy the records. Every other campaign will.
> **Trying too hard:** Knowledge is power, and power is on sale.

An option's wording is also a claim like any other. "Rush a replacement vehicle to the next pad" was the slowest of its event's three options. Read what each option does before naming it, and promise no speed, safety or saving the script does not deliver.

**An option speaks at the moment its event reports.** Where an event reports something done and shows the option that matches a choice made earlier, the option is the ruler's reaction to the result, not the choice again. The Mars landing's options read "Establish orbital infrastructure first." under a description in which the crew had already landed; it is now "Building in Mars orbit first was the right call. The station stays in service."

**Titles hint,** in two to five words: "A Routine Mishap", not "Hacker Collective Attack". A title needs no wordplay. Two cautions from the rewrite (2026-11-12). A title that works as a name stays one: the thirty-four resolution topics of `un_vote.1` ("Arms Embargo Vote") and the crash's severity tiers are how the player tells which question is in front of them. And a title is quoted elsewhere: before renaming one, `grep -rnF "<old title>" docs/ localization/english/` and change the player guide's chapters, the system docs and any tooltip that names the event in the same change.

### Flavor text: vary the form

Flavor is the slot where sameness shows most. Of the mod's 1,155 flavor texts, 44% are an exchange between two unnamed voices, and in several chains nearly all are (banking 72 of 83, elections 35 of 35, movements 31 of 32, wonders 25 of 26). Most of those end on a dry last line. A player who has read five has read them all.

So the form is a choice to make each time, and the two-voice exchange is no longer the default. Forms that work:

| Form | What it is | Suits |
|---|---|---|
| One voice | A single speaker at some length: testimony, a complaint, a speech, an order, an explanation to a child | Anger, pride, fear, fatigue |
| A document | A letter, a diary entry, a dispatch, minutes, a memorandum, a notice posted on a wall, a line from a ledger, a newspaper paragraph, an advertisement | Institutions; things discovered; distance |
| A scene without speech | What one person sees and does, in a place, over a minute or an hour | Aftermath, labor, waiting |
| Several voices | Three or four unconnected remarks overheard in different places about the same thing | A public mood; disagreement |
| A real quotation | A historical line, attributed with `— Name` | A moment with a famous witness |
| A list | An inventory, a schedule, the items of a report, the contents of a room | Bureaucracy; loss |
| An exchange | Two voices, back and forth | Conflict between two people who both have a point |

The rules:

- **In a chain, no form takes more than a third of the events,** and events that can fire one after another differ in form. Where a chain's events share one random pool, any can follow any other, so the rule becomes an even spread across the chain. `python3 scripts/analysis/flavor_forms.py <namespace>` prints a chain's current mix: run it before adding to a chain, and write in a form the chain is short of.
- **The register varies too.** Dry is one register among several: a text can be angry, proud, frightened, tired, formal or tender. Most events are not funny, and their flavor is not either.
- **Most flavor texts stop without turning** ([No kicker](#no-kicker)). A scene can end in the middle of the work; a letter can end with its closing; a speaker can simply finish.
- **The space program keeps its signature form at about half** (owner, 2026-11-12). In `space_race_events` and `space_race_colony_events` the attributed quote, a remark with `— Role` or a generated speaker beneath it, stays in 40 to 50% of the texts, and no other form passes a quarter. The quote that stays is still held to the rest of this guide: the speaker says what they saw or did, and it is not an aphorism for a visitor center's wall.
- **No form grows a formula of its own.** The election pilot's several-voices texts each ended on the one voice that made the pointed demand, which is the kicker again. In a several-voices text the order should not matter: if one voice has to be last, move it up or cut it.
- **The reader arrives cold.** The first sentence of a flavor text says, without a word that could mean two things, who is speaking or writing and to whom. "Lines for the government's speakers" could be loudspeakers; "Notes from the government's campaign office, for its candidates' speeches" cannot.
- **Someone is there.** Every form has a point of view: who is writing the letter, who is counting the sacks. Narration from nowhere reads as a news summary.
- **Speakers are unnamed and unplaced** unless a scope supplies the name ([Detail that cannot be wrong](#detail-that-cannot-be-wrong)). A document's letterhead, date and place are assumptions like any other.
- **Length:** 50 to 150 words. A short exchange under 50 words is usually a setup and a punchline; give it a different form.

**How `flavor_forms.py` reads a layout.** It classifies by shape, so lay a text out as the form it is. One voice is a single quoted paragraph. The speaker says who they are and whom they address in the first quoted sentence ("You are the relief officer, so I will tell you how we stand"), or one narrated line above the quote does ("A merchant, to the manager:"); more narration than that line, or a speech tag inside the quote, makes it a scene. Several voices are a heading line and three or more quoted remarks. The heading says where the remarks were heard and opens with "Remarks", "Heard", "Overheard", "Voices", "Statements" or "What ... said" ("Remarks heard at the peace rally in the capital."), and it ends in a full stop, since a heading ending in a colon makes a list. That opening is all that tells several voices from an exchange: quoted paragraphs under any other heading ("Two officials argued the proposal.") or under none are an exchange, and count against the exchange's third. So do remarks whose heading puts them in one meeting ("Remarks at the program's logistics meeting, from the minutes."): people in one room answer each other, and several voices are unconnected remarks heard in different places. A quotation is any text whose last paragraph begins with an em dash.

**A real quotation, an invented one and a historical note.** A real quotation is worded exactly as its author or its instrument has it and carries no date: a speech, a judgment, an article of a treaty or a declaration ("— Universal Declaration of Human Rights, Article 1"). If the wording cannot be confirmed, write another form. A line the writer made up and signed with a role is the attributed quote, which is the space program's form and is rare elsewhere; it is never signed with a real person's name. A historical note (what happened at Ust-Kamenogorsk in 1994) is narration from outside the game's world: it is allowed where a chain echoes real cases, counts as narration, runs to at least 50 words like any other flavor, and ends when the facts are told. In such a note the word "only" is usually the kicker.

**Laying out a list or a document.** A list opens with one heading line that says whose list it is, ending in a colon, then `\n\n`, then one item to a line (`\n` between them), each a full sentence or two with its full stop, and no bullets. **Each item carries its reason** (owner, 2026-11-09): not "Do not use the word boom." but "The opposition has been saying that a boom always ends in a bust. Do not use the word boom; say growth." A reader who has to guess why an instruction was given is being teased. Over-explain before you under-explain, in a list and everywhere else. A document opens by saying who writes to whom ("To the government, from the examiners of the grain reserve."), carries no date, place or letterhead, and closes the way such a paper closes: with its request, its next step or the writer's office.

**A closing or a kicker?** A document's last line is plain when it is what that paper would end on whoever wrote it: "We ask for instructions on the remainder." "I will report again when the count is done." It is a kicker when it is a detail held back for the end: "His coat. His umbrella is still on the stand." In a list, the test is whether the last item could change places with the third without loss. If it has to be last, it is a kicker.

The same event in three forms, none ending on a turn:

> **A document.** To the government, from the examiners of the grain reserve. We opened one sack in every twenty and found the grain in a tenth of them black with rot. The store ledgers show every sack as sound. We attach the counts as we made them, the ledger pages for the same bays, and the names of the officers who signed them. We ask for instructions on the remainder.

> **A scene without speech.** The examiner worked along the bay with a knife and a light. He cut each sack below the seam, took a handful and held it to the light. Good grain went back in. When a handful came out gray and warm he tied a strip of red cloth to the sack and moved on. By evening he had reached the far wall, and there was red cloth on one sack in ten.

> **One voice.** "I signed the counts because the storemen gave me the counts. That is how it has always been done. I have forty bays and two clerks. If the government wants every sack opened at every count, it may send me the men to open them. I did not spoil the grain. I wrote down what I was told, and I will say so to whoever asks."

## Sentences

- **Concrete nouns, plain verbs.** A person, a place, a number, a thing that happened. Verbs like *is, has, pays, loses, takes, ends*.
- **No stock metaphors.** *Mountains of, a flood of, grinds to a halt, plants the seeds, a double-edged sword, a ticking clock, sends shockwaves, hangs in the balance, a new dawn, the winds of change.* If the phrase arrived without effort, it is one.
- **No verdict words.** *Devastating, harrowing, staggering, unprecedented, sophisticated, massive, miraculously, fundamentally.* Give the fact that would make a reader think the word.
- **No balanced pairs for their own sake.** "X claim to be freedom fighters; the state calls them criminals." Write from inside one side and let the other intrude.
- **No slogans in a row.** One aphorism can land. Two in succession read as a slogan generator.
- **The patterns `docs/player_guide/STYLE.md` lists as machine-written apply here too**: inflated words (*comprehensive, crucial, robust, landscape, testament*), *serves as* for *is*, "not just X but Y", groups of three for rhythm, a closing sentence about significance.
- **Modern, plain vocabulary.** The mod runs from 1836 past 2030, and most of its events fire after 1900: "scientists", not "natural philosophers". No slang.
- **American spelling.**

## Punctuation and formatting

- **A dash is rare.** Prefer a comma, a colon, parentheses or a new sentence. Never ` - ` (a spaced hyphen) as a dash. In dialogue, an em dash may mark speech cut off: `"In my day —"`. An attribution line under a quote starts with one: `— Lead Propulsion Engineer`.
- **A colon introduces what the sentence promised:** the terms, the list, the consequence. One per sentence.
- **Semicolons** join two short facts that belong together in a rule ("Its ties rise 2 a month and fall 1 a month without supply; at full ties it asks to join"). In event prose, use a full stop.
- **No ellipsis** at the end of a text.
- **Quotes** in loc are `\"`, straight, and paired.
- **Formatting codes mean something.** `#v` marks a live figure, `#G` / `#R` good and bad for the player, `#b` a heading inside a tooltip or a word the player must not miss. None of them is decoration, and an event description carries none except to mark a threshold or a required action.
- **No text ends with `\n`,** except a fragment a `desc` block splices in front of another (`un_events.*.d_cause_*`), which ends in `\n\n` by design and carries `# REVIEWED … (loc_style)` on its line.

## Words

- **One name per thing.** Use the in-game name, spelled and capitalized as its own key renders it, and splice it (`$key$`) rather than retyping it, so a rename reaches every mention. Splice only a name that reads as a noun in the sentence: a law whose name is "Ministry of Intelligence and Security Established" goes in a list of laws, or the sentence is written around it.
- **Props that fit every era the event can fire in.** "Crates", not "bales"; "a message", not "a telegram", unless the event is gated to the years that had them.
- **A coined term says what it means** the first time, or links the concept that does.
- **Do not put one faith's furniture in a scene any country can get** (a priest, a pew, a sermon). Write the scene without a named faith or gate the version. `event_creation_guide.md` has the pattern, and `faith_scene_audit` fails CI on a faith's word that another faith's country can be shown (§ "What the machine checks").

## Before you commit a text

1. Check the key is live: it is not in `te_unused_l_english.yml`, and something in `common/`, `events/` or `gui/` uses it.
2. Read the script the text describes. Check every claim against it, option wording included.
3. Read the text without its key. Can you tell what it is attached to? If not, it is generic: find the sentence that would survive being moved to another entry, and replace or cut it.
4. Ask of each invented detail what country or year would make it false.
5. Cover the last sentence. If the text is complete without it, delete it.
6. For flavor, run `scripts/analysis/flavor_forms.py <namespace>` and pick a form the chain is short of.
7. Read the longest it can render (the longest country name, the largest figure) against the cell or tooltip it sits in.

## What the machine checks

Two lints run in `scripts/preflight.py` and CI. Both are ratchets: the mod's older text is recorded in a baseline, and only new text is held to the rule.

- `python3 scripts/analysis/check_loc_style.py --check` fails on a new stock metaphor, verdict word, inflated word or phrase, "not just X but Y", ` - ` as a dash, or a text ending in an ellipsis or `\n`. A use that is meant takes `# REVIEWED YYYY-MM-DD (loc_style): why` trailing on the loc line. After rewriting old text, run it with `--update` and commit the smaller baseline.
- `python3 scripts/analysis/flavor_forms.py --check` fails when a form that is over a third of its chain gains a text. After rewriting a chain, `--update`.

Neither can judge whether a sentence is particular, whether a game could make it false, or whether it ends on a kicker. Those are the writer's.

One audit reads the script beside the text, and is not a ratchet: `python3 faith_scene_audit.py --strict` (CI runs it with the other audits) fails when an event can show a text with one faith's word in it (a priest, a mosque, a guru, the faith's name) to a country whose state religion the word does not fit (#1531). It covers what an event shows: titles, descriptions, flavor, options, tooltips and the modifiers it adds. It reads religion gates only, so a text gated on culture or on a variable, a real quotation and a metaphor ("Cathedrals of Coral") are flagged and take `# REVIEWED YYYY-MM-DD (faith_scene): why` trailing on the loc line. `--explain <key>` lists where a key is named and the gate read there. The word list, with the faiths each word fits, is `VOCABULARY` in the audit: add a word there when a scene gets past it.

## Still open

1. **Existing text.** The election chain was the pilot (2026-11-09), and the other ten batches of #1539 followed on 2026-11-12: every chain's flavor was rewritten, and nearly every description, since most had a verdict word, a stock metaphor, a closing line or an unbacked claim. What each chain's triggers guarantee is in `event_text_guarantees.md`. Not yet done: the `te_debug_*` test benches (out of scope), and text outside events (modifier and law descriptions, tooltips, concepts), which the lint's baseline still lists.
2. **Semicolons in rules text.** About 250 tooltips and 70 concept descriptions use them. The guide allows them for paired facts and discourages them in event prose.
3. **Documents that close "We ask ...".** The guide's model for a document ends on its request, and many of the rewrite's documents do: 74 of 205 close on "We ask ..." or "I ask ..." (2026-11-12). Read in a row that is a formula too; the next pass should vary how a paper closes (its next step, the writer's office, the enclosure). `flavor_forms.py` prints the count for each chain in its `We ask` column and marks each such document under `--list`.
4. **Gates `event_guarantees.py` does not follow**: a decision, button, treaty article or diplomatic action that fires an event, a latch variable, a building's technology, `owner = { }` in a state event. They are listed under "What a chain's triggers already guarantee".
