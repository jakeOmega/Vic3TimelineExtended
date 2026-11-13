# Event text rewrites: in-game checks

The event text rewrites (#1539) change wording, and now and then a description's gating. The offline checks cannot show how the new flavor forms render. Each batch adds its rows here; the play-test before a release works through them.

Fire an event from the console with `event <id>` (debug mode). An event fired this way skips its trigger, so its scopes may be empty: a blank party name there is the console's doing, not the text's.

## What to look at in any rewritten event

| Check | Expected | If not |
|---|---|---|
| A list flavor (a heading line, then one item to a line) | The heading, a blank line, then each item on its own line, none running into the next | The `\n` breaks are not rendering in the flavor box: join the items into a paragraph with semicolons, or change the form |
| A document flavor ("To the ..., from ...") | Reads as one paragraph; no stray quotation marks | Check the key for an unescaped `"` |
| A long flavor (over about 120 words) | Fits the event window without the options being pushed off or the text scrolling | Cut to the guide's 150-word ceiling or below |
| A real quotation with its attribution | The quotation, then `— Name` on its own line | The `\n` before the dash is missing |

## Elections (`modern_election_events`, #1540)

| Check | How | Expected |
|---|---|---|
| The list form renders | `event modern_election_events.15`, `.28`, `.30` | As the first row above |
| The gated description | With Universal Basic Income enacted, `event modern_election_events.29` | The description opens "Universal basic income is already law in ..."; without the law, "Universal basic income has become the most argued-over proposal ..." |
| The live figure | `event modern_election_events.3` with Global Warming on | The description shows the world's temperature anomaly as a number with °C, not `0` or a raw key |
| The one-line quotation | `event modern_election_events.19` | "The medium is the message." with its attribution beneath |
| Option names follow whose candidate blundered (#1551) | Let `modern_election_events.9` fire in a campaign a few times (it picks the blundering side at random) | With our governing party's candidate named in the description, the first two options read "Say nothing, and let the networks run it ..." and "Apologize for it and move on."; with the opposition's, "Let it run as often as the networks like." and "Take the high road." Never both, never a raw key. The own-side names key on `scope:own_gaffe_party`, saved only in the `random_list` branch where our party blundered |
| The pilot program hides under Universal Basic Income (#1551) | With Universal Basic Income enacted, `event modern_election_events.29` | Two options, no "Propose a limited pilot program."; without the law, three |

## Space race landing reports (`space_race_events.3`, `.7`)

| Check | How | Expected |
|---|---|---|
| Each option reads as said after the landing | `event space_race_events.7` after choosing each approach in `event space_race_events.83` (and once with none chosen); `event space_race_events.3` with the Sea of Tranquility and far side sites from `.5` | One option, matching the approach or site, in the past or present tense; the two-sentence orbital line fits its button |

## Banking (#1541)

| Check | How | Expected |
|---|---|---|
| A list flavor's layout in the event window | Fire `banking_cycle_events.5` (needs `railways`, expansion) or `.24` with the console | The heading line, a blank line, then one prospectus or warehouse to a line, no bullets, nothing cut off |
| The real quotation | Fire `banking_cycle_events.31` | The Roosevelt line, then the attribution on its own line after a blank line, starting with an em dash |
| The longest flavor in the window | Fire `banking_cycle_events.14` (140 words, two long paragraphs) | Whole text visible or scrollable, no overflow over the options |
| `.34`'s two descriptions | Fire `.34` once with `banking_recent_crash` set and once without | "After the recent bank failures" only with the variable; the calm text otherwise |
| Lists render as one heading and lines | Fire `banking_cycle_events.50`, `.62`, `.104`, `.170` and `banking_debt_events.2` (console `event`) | Heading line ending in a colon, a blank line, then one item to a line with no bullets; no item clipped in the flavor box |
| The one-line real quotation | Fire `banking_cycle_events.48` | The Fisher line, a blank line, "— Irving Fisher"; nothing else in the flavor box |
| New scope names in flavor | Fire `banking_cycle_events.45` (via .68's appeal), `.55`, `.69`, `banking_debt_events.4`, `te_peg.2`, `te_lolr.1`, `te_lolr.2` | Each flavor prints the country's name, not a raw `[SCOPE...]` or an empty string |
| Concept links in a scene | Fire `banking_cycle_events.63` and `.62` | "amendment" / "amendments" render as concept links in the flavor |

## Laws (#1542)

| Check | How | Expected |
|---|---|---|
| `extra_law_events.3` gold flavor | Enact Gold Standard with an IG opposed until the debate checkpoint fires .3 (or `event extra_law_events.3` while enacting) | Flavor shows the Bryan quotation with its "— William Jennings Bryan" line under it. While enacting Fiat Currency it shows the four voices instead |
| `extra_law_events.32` description ladder | Fire .32 while enacting Humanitarian Regulations (rule on), Limited War (rule on), War Crimes Forbidden, and Limited War with the nuclear rule off | `d`, `d_pledge_only`, `d_no_pledge` and `d_no_clause` respectively, each naming only the clauses its options offer. Since #1613 the last case no longer fires from the debate checkpoint (the trigger excludes it); `event extra_law_events.32` still shows `d_no_clause` there |
| List layout | Fire .14, .24 or .31 | Heading line, a blank line, then one item per line with no bullets. .31's items show the interest group names, not raw keys |
| Long flavor | Fire .31 (143 words) or .4 (131) | Fits the event window without the options being pushed off-screen |
| Gated descriptions and flavor in the stall events | Enact Multilingual Federalism (.49), Federal System (.51), Human Purity (.52), Freedom of Testation (.53) and Indifference (.57) with an opposed group, `event extra_law_events.<n>` | Each shows its variant (`_pluralist`, `_central`, `_purity`, `_testation`, `_indifference`); the same events for Civic Monolingualism, Unitary State, Unrestricted Augmentation, Forced Heirship, Protection show the default |
| The four list flavors render as lists | `event extra_law_events.50`, `.62`, `.68`, `.73`, `.79`, `.83` | A heading line, a blank line, then one item to a line; no item cut off; .73 (the longest, about 145 words) fits the flavor box |
| Law names inside parentheses | `event extra_law_events.57` and `.81` under each minority-rights law | "the government's law on minority rights (Affirmative Action)" reads as one phrase |
| `extra_law_events.25` shows a country's own tongue (#1613) | `event extra_law_events.25` as Egypt, Sweden, Ethiopia and Prussia | Egypt reads the Classical Arabic description and Sweden the Old Norse one, each still offered Hebrew or Gothic among the options; Ethiopia (Ge'ez and Coptic) reads "More than one classical language"; Prussia reads the Gothic description |

## Ministries, amendments and courts (#1543)

| Check | How | Expected |
|---|---|---|
| A law name spliced into a sentence reads | Enact any ministry law with debug, fire `ministry_law_events.1` and `.4` (the latter while enacting a `No Ministry of …` law) | "While we are enacting Ministry of War Established, …" and "We are enacting No Ministry of War, which closes a ministry" read as sentences, not garbled |
| A list lays out in the event window | Fire `ministry_law_events.1` and `.16` | Heading line, blank line, one item to a line, no bullets; .1 (150 words) fits without a scrollbar or with an acceptable one |
| IG name in flavor | Fire `ministry_law_events.2` and `.20` while enacting a ministry law some non-marginal group opposes | The opposing group's name renders in the flavor's first sentence, same as in the description |
| The law name reads in apposition in the ministry descriptions | Enact any ministry law and fire `ministry_law_events.43` (or .39) from the console | "The law Ministry of War Established must say..." shows the law name as a link and reads as one sentence |
| A list flavor lays out one item to a line | Fire `ministry_law_events.35` while enacting the Ministry of Consumer Protection | Heading line, blank line, five items each on its own line, all visible in the flavor box without clipping |
| The dissolution description with a "No Ministry of X" name | Start abolishing any ministry and fire `ministry_law_events.42` | "Once No Ministry of X is in force, the ministry it abolishes..." reads correctly |
| The longest flavor (.35, about 150 words) fits the event window | Fire `.35` at the smallest supported UI scale | Text scrolls or fits; no overlap with the options |
| The Religious Exemption petition's gated flavor | Fire `amendment_petition_events.13` as a Catholic or Protestant country, then as a Sunni or Hindu one | The bishop scene for the first; the "councils of our faith" speech for the second |
| The heir's ally named | Fire `heir_education_events.3` with an alliance | The description names the allied country, not a raw key |
| Lists render | Fire `amendment_petition_events.14` and `inheritance_events.16` | A heading line, a blank line, then one item to a line |
| Industrialists' name | Fire `inheritance_events.11` while enacting Freedom of Testation | The description shows the country's name for the Industrialists |

## Movements and social tension (#1544)

| Check | How | Expected |
|---|---|---|
| A list flavor's layout | Fire `movement_events_te.13` (a severe minority law, civil rights entry active) and `social_tensions_events.15` | A heading line, a blank line, then one item per line with no bullets; nothing cut off at the bottom of the flavor box |
| The lone-quotation flavor | Complete `je_civil_rights` with no track over 18 months (`movement_events_te.200`) | The King line and its attribution on two lines, no stray italics |
| `.13`'s desc order | Fire `social_tensions_events.13` with Social Media researched | The online-revival description (`.d_social`), not the television one |
| A state name in a riot description | Fire `social_tensions_events.6` | The description names the rioting state, not a raw key |
| Revival Christian variants | As a Protestant or Catholic country meeting .2 and .5 (`event religious_revival_events.2` / `.5`) | The megachurch desc and pastor flavor in .2, the bishop scene in .5; a Buddhist or Shinto country gets the faith-neutral default for both |
| Revival Hindu gate | Fire .1–.7 as a Theravada or Mahayana country (e.g. Siam) and as a Hindu one | The Buddhist country gets the neutral default (no gurus, caste, Hindutva); the Hindu country gets the `_dharmic` texts |
| Accented attribution | `religious_revival_events.3.f` (default faith) | "— Hélder Câmara" renders with both accents in the event font |
| List layout | `cultural_hegemony.8.f`, `.15.f`, `religious_revival_events.4.f_islamic`, `.5.f` | Heading line, blank line, one item per line, no item cut off in the flavor panel |

## Technology and society (#1545)

| Check | How | Expected |
|---|---|---|
| The lists in `.2.f` and `.22.f` lay out one item to a line | Fire `society_technology_events.2` (Women in the Workplace, second-wave feminism) and `.22` (a nuclear plant) | A heading line, a blank line, then five items each on its own line, no item cut off in the flavor box |
| `.22.d` and `.23.d` name the plant's state | Fire `.22` and `.23` for a country with a nuclear plant (level 3 for `.23`) | The state's name in the first sentence, not a raw `[SCOPE...]` string or a blank |
| Spliced names in `.8.d_comprehensive` and `.23.c` | Fire `.8` under Anti-Discrimination Laws; fire `.23` with the Ministry of Consumer Protection at level 3 | "Our Anti-Discrimination Laws already protect..." and the option "Send in the emergency teams of the Ministry of Consumer Protection." |
| The Wiener quotation in `.26.f` | Fire `society_technology_events.26` | The quotation in one paragraph, the attribution on its own line after a blank line, starting with an em dash |
| A crash's list renders | Force `minor_events_timelineextended.6` with `crash_severity` ≥ 80 | Heading, a blank line, then five items one to a line, no bullets |
| The debate notes render | `repeatable_events.10` during a campaign | Heading line, blank line, five items one to a line |
| The independence name | Release a colony through decolonization and read `minor_events_timelineextended.3` as the new country | The new country's name, not the parent's and not a raw key |
| Contagion scare text names the origin | A scare `.7` from a panic-tier origin (severity 60 to 79) | `d_panic` reads the origin's adjective in "[Adjective] debts" |
| A list flavor lays out in the event window | Fire `surveillance_events.3` and `augmentation_events.5` (`event surveillance_events.3`) | Heading line, a blank line, then one folder or item per line, none clipped; the window scrolls if needed |
| Law-name splices render | Fire `surveillance_events.100`, `.200` and `post_scarcity_events.200` | "Intrusive Surveillance System", "Strong Privacy Rights" and "Post-Scarcity Economy" appear in the descriptions, not `$law_...$` |
| A quotation-only flavor | Fire `post_scarcity_events.200` | Marx's line in quotes with "— Karl Marx" below it, as `nuclear_weapon_events.10.f_world_first` shows |
| A long one-voice flavor | Fire `morphological_freedom_events.1` (144 words in one paragraph) | Fits the flavor box without clipping |
| Each repeatable event shows its own subject (#1616) | Fire `repeatable_events.20` to `.100` and `minor_events_timelineextended.7` and `.8` | `.20` a jammed port, `.30` robots on a factory floor, `.40` viewers at a television, `.50` a control room with failing lights, `.60` a broadcast control room, `.70` debris around the Earth, `.80` a collector satellite under a particle stream, `.90` a laboratory sample, `.100` a server room; `.7` a trading floor, `.8` a man with papers on a wet street. No magenta |
| The prediction software's modifiers (#1616) | Fire `surveillance_events.4` and hover each option | "Predictive Policing", "Prediction for Intelligence Only" and "Predictive Policing Banned": no modifier says AI |

## Decolonization, diplomacy and war (#1546)

| Check | How | Expected |
|---|---|---|
| `.1.f` quotation renders | `event decolonization_events.1` as a colonial power with a subject at liberty desire 50+ | Two sentences in quotes, then "— Harold Macmillan" on its own line; no stray backslash |
| `.15.f` list layout | Free a subject whose GDP a foreign minor power owns over 5% of, read `.15` a week later | Heading line ending in a colon, then five items one to a line, no bullets, fits without a scrollbar |
| `.20.f` names | As a great power, have another great power take `.19.a` | The flavor names the target country and the intervener's adjective (not a raw key or blank) |
| `.50.f_gbr` gate | `event decolonization_events.50` as GBR with debt above 0.4, and as France | Britain gets the Treasury memo naming the City and sterling; France gets "from the treasury" with no sterling |
| `.73.f`'s list renders as a heading and five lines | Win a war of independence for the rebels (or `event decolonization_events.73` with the end scopes set through the debug harness) | One heading line, a blank line, then five items one to a line, no bullets, the territory's name spliced into the heading |
| `.401.f` and `.203.f` lists fit the event window | Planned Full Decolonization from the panel; reach the Iron Fist ending | Five items each, readable without the flavor box clipping |
| `.61.d`'s figure | As a former colony, receive `.61` | The sum shows with the money icon in the value color (`#v`), not bold |
| `.75.f_vote` quotation | A war of independence over 48 months with a voting law and war support in the red for a year | "I have understood you!" with "— Charles de Gaulle" on its own line; title reads "Committee of Public Safety" |
| The two IR lists and the irredentism list lay out one item to a line | Fire `international_relations_events.3`, `.202` (covert warfare off) and `irredentism.8` (`irr_proposed_target`, `irr_unifier` set) | A heading line, a blank line, then five items each on its own line; the flavor box shows all of it without clipping |
| The Nehru quotation renders with its attribution | Form India (BHA) or fire `formation_te.1` as BHA | The quote on one line, a blank line, then "— Jawaharlal Nehru" |
| The culture name reads correctly in the irredentism.1 flavor | Fire `irredentism.1` as a unifier with a candidate | "A teacher from the [culture] community in [country]" with both names filled, not raw keys |
| The four .104 variants each show their own flavor and option | Fire `.8` against a nuclear-armed opponent and pick a, b and c in turn; read the opponent's `.104` | Tension, relief and terror texts and options in turn; the default ("We will keep our nerve.") never shows |
| `world_war_events.20` description variant | As a non-belligerent major power during a world war, fire `.20` once with a great power of each side at war with each other and once when none is | Two sides named in the first; `.20.d_no_side` and no option a in the second, no blank country names |
| Lists in the event window | Fire `world_war_events.4`, `.100` (won or lost), `treaty_article_events.4` and `.11`, `covert_warfare.2` (an operation caught in preparation) | Heading line, blank line, one item to a line, no bullets; `[exchange_partner].GetAdjective` renders as an adjective in `.11.f` |
| `world_war_events.103.f` quotation | Fire `.103` as a great power after a world war | The quotation and its em-dash attribution on two lines, nothing else |
| State names in the minority-protection pair | Fire `treaty_article_events.3` and `.4` with a Minority Protection article on one of our states | The protected state's name in `.3.d`, `.4.d` and `.4.f` |

## United Nations (#1547)

| Check | How | Expected |
|---|---|---|
| The two lists render one item to a line | Fire `un_events.4` (a major-power member, a collapsed state) and `un_events.14` (any member with `nuclear_weapons`) | Heading line, blank line, then six (4) and five (14) separate lines, no bullets, nothing cut off by the window |
| The four quotations keep their attribution line | Fire `un_events.3`, `.38`, `.40`, `.42` | The quoted text, a blank line, then a line starting with an em dash naming the instrument and article |
| The indictment names the ruler | Fire `un_events.33` with an ICC in force | The Registry letter names our current ruler, plain text with a tooltip link, and our country's name |
| Long several-voices flavor fits | Fire `un_events.2` and `un_events.10` | Four paragraphs, each in quotes, no scroll cut-off in the flavor box (about 145 words each) |
| `un_vote.1.f` (several voices) and `un_ceasefire.1.f` (147 words) fit the event window | Table any resolution as a second human member, or fire `un_vote.1` with a resolution open; carry a ceasefire against a human aggressor | Five paragraphs, no scroll bar clipping the last voice |
| `un_court.2.f` / `.3.f` print the region and claimant | Refer a claim to the World Court and let the ruling go against the holder; read both parties' events | The state region's name and the claimant's name, not a raw scope string |
| `un_referendum.1.f`, `.2.f`, `.4.f` print the subject's name | Carry a supervised referendum against a human overlord; hold and refuse in two saves | The subject country's name in the first sentence of each |
| `un_mandate.2.f` prints the target and region | Bind an authorized mandate to a diplomatic play as a human holder | Both names in the document's first two sentences |

## Nuclear (#1548)

| Check | How | Expected |
|---|---|---|
| The Oppenheimer quotation with its new attribution line | Be the first country to finish a warhead (`nuclear_weapon_events.10`, world-first variant) | Italic quotation, a blank line, then "— J. Robert Oppenheimer" on its own line |
| A list in a strike report | Have an incident launch land a strategic strike (`nuclear_weapon_events.2`, `f_incident`; e.g. `te_debug_deterrence.2` option j) | Heading line, then four items one to a line, the dead figure live and the state named; no overflow in the event window |
| The kill figure in the world's notice | Let any strategic strike land between two other countries (`nuclear_weapon_events.15`) | `.15.f`'s third voice shows a real figure (K-formatted), not 0 or a raw key; same in a salvo's `.15` |
| The launch-order list | Order a salvo from the Strike section (`nuclear_weapon_events.31`) | Five items one to a line, readable above the two options |
| The two incident lists render as lists | Force `nuclear_incident.11` as a human crisis opponent (exercise misread), and `.60` after concealing an incident (`.3.b`) | A heading line ending in a colon, then one item to a line, no bullets, the window not overflowing |
| The crisis lists render | Close a crisis (`nuclear_crisis.6`) and take a first warhead as a human (`nuclear_crisis.100`) | Each item on its own line under the heading; `.100`'s five items fit the flavor box |
| New scope splices print names | `nuclear_incident.5`, `.10`, `.11`, `.31` (needs a Nuclear Basing host); `nuclear_crisis.1`, `.2`, `.8`, `.20`, `.24` | Country and state names, no raw `[SCOPE...]` text, no blank; `.31.f`'s adjective reads as a nationality ("French soldiers") |
| Longest flavor texts fit | `nuclear_incident.3.f` (144 words), `.30.f` (144), `.6.f` (144) | No scrollbar cut-off in the event window |
| `nuclear_custody.3.f` and `.11.f` lists render one item to a line under their heading | Console: give a human warheads by custody (`te_debug_nuclear` / a civil war in an armed country) to see `.3`; win a secession holding warheads with a great power pressing to see `.11` | Heading, blank line, then four or five lines, no item running into the next; the 150-word `.3.f` fits the event window without a scroll bar cutting an item |
| `nuclear_loose.2.f` heading splices the struck state's name | Trigger a loose-warhead detonation on a human (`nuclear_loose.1` with a seeded `nd_loose_warheads` pool) | "…going into <state name>:" with the state's real name, then five order lines |
| `nuclear_taboo.2.f` quotation renders as a quote with its attribution | `event te_debug_nuclear.1` to set the taboo just under 50, step it through 50 | The single quoted line, a blank line, then "— Ronald Reagan and Mikhail Gorbachev, joint statement at Geneva" |
| `nuclear_custody.6.f` names the government | Armed AI country's civil war, the player a major power believed armed | The second voice reads "…some of <government country>'s officers…" |

## Space (#1549)

| Check | How | Expected |
|---|---|---|
| The four lists (.5, .21, .31, .34) render one item to a line under their heading | `event space_race_events.5` (and .21, .31, .34) in the console | Heading line, blank line, then each item on its own line with no bullets; .5 at 146 words fits the window without a scrollbar or with an unclipped one |
| .15's descent recording reads as a transcript | Fire `space_race_events.15` | A narrated first line, then six quoted lines alternating between the crew and control, each its own paragraph |
| .26.f names the estranged power | Sour relations with a country holding a space programme, force a Safe setback until .26 fires (te_debug_space_race.1 option j) | The flavor's first sentence names the same country as the description, never a raw key |
| .20's assembled description reads as one paragraph | Have another country complete a milestone, first and then later | Opening and context join with one space: "... on the Moon. No country has done this before, ..." / "... They are not the first to do it, and we have not yet done it ourselves." |
| A list flavor lays out | Fire `space_race_events.51`, `.75` and `.83` from the console | The heading line, a blank line, then one item to a line, each with its full stop; no item runs into the next |
| The probe results' long description and the new cat II–IV flavors fit | Fire `space_race_events.610` (cat II, a long result paragraph) and `.627` (cat IV) | Intro, result paragraph and "…must decide who sees the data." read as three paragraphs; the flavor below shows whole |
| A partner and a site named in flavor | Fire `.52` as a UN member with an orbital partner, and `.94` through `te_debug_space_race` (the autonomy step) | `.52.f` prints the partner's name, `.94.f` the colony's name, never a raw key |
| A list flavor lays out in the event window | Found Shackleton (`space_race_colony_events.35`) or Hygiea (`.10`); console `event space_race_colony_events.35` | The heading line, a blank line, then one item to a line with no bullets; no clipping in the flavor box |
| A long several-voices flavor fits | Fire `space_race_colony_events.6` and `.23` (about 150 words, four paragraphs) | All four paragraphs show, scrolling if the box scrolls, nothing cut off |
| A founding text matches the colony's page | Found any world under Simple or Full Colonies, open Solar System Colonization's Colonies page while the event is up | The colony shows 0 people, and no text in the event puts anyone on site |
| The 22 events without a speaker still open and close cleanly | Fire `.1`, `.14` (it had the multi-line `on_created`) and `.40`, pick an option in each | No "Event target link 'scope' returned an invalid object" in `error.log`; the 18 quotation events still print the speaker's name |
| A discovery list's layout | Fire `space_race_discovery_events.16` (or .2, .6, .11) on a country holding the site | Heading line, a blank line, then one item to a line with no bullets; the window scrolls rather than clipping the last item |
| A long document flavor in the window | Fire `space_race_discovery_events.17` | The whole letter shows, closing request included |
| Attributed quote layout | Fire `space_race_discovery_events.7` and `.19` | The attribution line ("— Glaciologist, Space Program Science Office") sits on its own line under the quote |
| Ribbon strike text | Fire `te_orbital_debris.1` with a Space Elevator | The flavor's "at a price" matches option b's treasury cost in its tooltip |
| `.37` names the probe's target (#1620) | Run the Deep-Space Probe three times past 50%, choosing Venus, Mars and the asteroid belt in `.81`; then `event space_race_events.37` in a country that never had the milestone | Venus's cloud bands, Mars's channels and polar cap, the first asteroid of the belt, each with the frame of Earth; the country with no target reads "its target" and names none |
| `.45` names no planet (#1620) | Let `.45` fire at 30% under each target | The description and all three options read for any target: no Jupiter, no "outer system"; the fastest option is the direct flight |
| The Grand Tour's choice shows its cost | Start the Deep-Space Probe, wait 30 days for `.81`, hover the fourth option | "Grand Tour Mission Profile" with −25% space race progress, and a red figure of 60 innovation a week (two funding levels at the probe's factor), not 0 and not a raw key |
| The tour is billed and slows the program | Take the Grand Tour at funding 3 on Standard; a week later read the probe's entry and the pace hover | Space Program Cost reads 150 innovation a week (90 before the choice); the pace breakdown lists the Grand Tour's −25%; lowering funding to 0 leaves 60 a week; the entry's profile line reads "Target: Grand Tour" |
| The tour's own texts | With the tour chosen, let `.45` fire at 30% and `.37` at 50%, then finish the milestone | `.45` and its three options are about the pass at Jupiter (triggered option names: no option shows two names or a raw key); `.37` reports Jupiter and the frame of Earth; `.4` speaks of the last planet on the tour and offers only "Jupiter, and every planet beyond it." |
| The tour's reward | Take `.4`'s option | "Grand Tour Data" for twenty years, decaying: research +2%, space race progress +0.4, prestige +1%, innovation cap +15 |

## Monuments, environment and people (#1550)

| Check | How | Expected |
|---|---|---|
| A list flavor's layout | Fire `monument_events.6` (or `.15`, `.17`) for a country with a fitting monument of that dedication | Heading line, a blank line, then four items one to a line, none run together |
| The quotation flavor | Complete an opportunity as a player so `monument_events.28` opens | Latin line, the English on the next line, a blank line, then the em-dash attribution |
| The state name in anniversary descriptions | Fire `.3`–`.10` for a country whose grandest fitting monument of that dedication stands beside another | The description names the monument's state, not a blank or a raw key |
| `monument_trophy_events.1` flavor length | Occupy a state holding a monument as a player | The 127-word dispatch fits the event window without overflow |
| `wonder_state` names the right state | Build a Space Elevator site and a Solar Collector site, then fire `wonder_events.1`, `.3`, `.4`, `.10`, `.11` from the console | Each description names the state holding that building, never a raw `[SCOPE...]` or a blank |
| Lists render one item to a line | Fire `wonder_events.4`, `.12`, `.25`, `.35` | Heading line, a blank line, then one item per line with no bullets; `.35` (the longest, 149 words) fits the flavor box |
| Arch abroad and host flavors name the other country | Finish a dig abroad under a concession and under a permit, as sponsor and as host | `.2.f_concession` / `.f_permit` name the host, `.f_host` / `.f_host_concession` name the sponsor, without formatting |
| `resettlement.3` picks its variant by the destination's winter | With one Settlement Authority only, in a cold region (the Dakotas, Siberia) and then in a tropical one (Amazonas, Pará), take `te_debug_resettlement.1` option b month after month until `.3` comes up: 10% a month once settlers have arrived, and `.3` is one entry of the roll's list (clear `rs_event_cooldown` between tries). The console cannot fire `.3` itself, because its trigger needs `scope:rs_event_state` | Cold: "A Hard Winter on the Frontier", the dugouts and the snow. Tropical: "A Hard First Season", the relief officer's walk through the settlement. No raw key in either |
| The lists render as lists | Fire `environmentalism_events.3`, `.14`, `resettlement.6` and `te_demog_wave.8` | One heading line, a blank line, then one item to a line with no bullets; nothing cut off at the foot of the event window |
| The new world figure in the recurring climate events | Fire `environmentalism_events.5`, `.6`, `.8`, `.13` and `.16` at some warming (`event te_debug_gw.1` sets it) | Each description prints the same anomaly the Global Warming entry shows, with "°C" after it, not 0 and not a raw key |
| The two quotations | Fire `resettlement.9` and `resettlement.20` | The quoted line, then the attribution on its own line after an em dash |

## Script fixes the rewrite's reading found (#1612–#1621)

The script bugs the batches reported were fixed after the texts. These rows are what only the game can show of those fixes.

| Check | How | Expected |
|---|---|---|
| A banking draw's bonus counts only inside its gate (#1612) | Under Unregulated Banking or Light Prudence, before `consumer_credit` and `modern_financial_instruments` are researched, let the banking cycle run for some years | No Predatory Lending Scandal (`.44`) and no shadow-banking event (`.20`, `.120`, `.170`) before their technologies; each still arrives in a Boom or Frenzy once its technology is researched, so the nested bonus `if` has not emptied the draw |
| The planned and cooperative twins read as their own measure (#1612) | Under a Command Economy take `banking_cycle_events.104.b` and `.116.a`; under Cooperative Ownership `.154.b` and `.166.a` | "Emergency Stockpiles Opened", "Planning Bureau Upheld", "Federation Relief Fund Opened", "The Old Slate Upheld"; no deposit guarantee and no central bank in the modifier list |
| `decolonization_events.15` names the largest owner (#1617) | Free a subject in which two foreign powers own over 5% of GDP, one of them over 25% | The description names the larger owner every time |
| `decolonization_events.16` names a neighbor of shared heritage (#1617) | Fire `.16` as a young state bordering both a kin state and an unrelated country | The description and option A name the kin state, never the unrelated one |
| A bloc leader is not asked to bless its own union (#1617) | As a bloc leader, propose voluntary union to a member of the bloc and have it accept | No `irredentism.8` arrives, and the union goes ahead |
| A refused demand always opens its play (#1617) | Demand a state with `irredentism.1.c`; in the next five days have either country join another play | `irredentism.2` does not arrive; with neither in a play it arrives and a refusal opens the return-state play |
| `monument_events.4` picture by faith (#1621) | Fire `.4` as an Ibadi country (Oman) | The Islam video, not the animism one |
| The elevator halt stops the site and its cost (#1621) | With a space elevator site on "Construction (1 year)", fire `wonder_events.2` and take "Halt construction". Look at the site's building panel at once, a week later, during the halt after switching it back to "1 year" by hand, and in the month after day 180 | At once the site is on "Construction (Paused)" and the option's tooltip said so. A week later it buys only the paused method's Advanced Materials and its staff is falling toward 500. The progress figure does not move for six months. A speed picked by hand is paused again at the next month's start, and is the speed the site returns to. Within a month of "Elevator Construction Halted" running out the site is back on its speed with no click, and hires again. A site already on Paused when the event came stays paused afterwards. If the scripted switch does not hold on this government building (the site stays on its speed, paying, with no progress), the fallback is a timed state modifier that takes the site's throughput to zero for the halt |
| `environmentalism_events.23` prints the figure that crossed (#1621) | Under stratospheric aerosols, let unmasked warming fall back below 4.0 | The description's figure is just under four degrees, not the lower felt anomaly |
| `nuclear_incident.30` kinds follow the arsenal (#1619) | Take over a nuclear power's warheads as a country without `bombing_aircraft`, then hold high alert | No bomber accident and no cross-country flight; the lost weapon and the exhausted crews still come |
| The Close Call goes to a country with no arsenal (#1619) | As a country with `radar`, no warheads and a nuclear-armed rival, wait on the yearly pool (or `event nuclear_weapon_events.21`); check an armed country over the same years | "A Moment of Terror" arrives; option a adds "Warning Procedures Reviewed"; no line speaks of a launch or an arsenal of ours. The armed country never gets it |
| An arsenal held without the technology lands (#1619) | Annex a nuclear power as a country without `nuclear_weapons`, open the Nuclear tab, then strike an undefended state | Delivery capability reads 100%, its tooltip and the strike's odds tooltip carry "+100% from warheads that were built before we held them", and the strike's success chance is 100%, not 5% |
| Buying power abroad is paid for (#1616) | Fire `repeatable_events.80` and take "Buy power from abroad" | The tooltip lists "Imported Power Costs" beside the import modifier, and the Budget breakdown shows a weekly amount under Energy and Industry Programs for five years |
| Air Raid Relief does not stand in for Home Front Strain (#1617) | In a world war's first year take `world_war_events.11.a`; look at the World War entry at year two, and take the option again after it | Home Front Strain arrives at year two on time; after it the entry shows one Home Front Strain and one Air Raid Relief, never two strains |
| The women's work events reach suffrage countries (#1616) | Research Second-Wave Feminism as a country already under Women's Suffrage | `society_technology_events.1` and `.2` can both arrive |

## What the guarantees tool assumes (#1697)

| Check | How | Expected |
|---|---|---|
| A law with two unlocking technologies needs both | As a country with `social_media` researched and `automated_surveillance` not, then the reverse, open the Privacy Rights laws | Intrusive Surveillance (`law_intrusive_surveillance`, the only law with two) is locked both times: the engine needs all of them. `event_guarantees.py` counts only what each gives, the safe reading while this is unknown; if locked, its `law_gate` may count both, and `extra_law_events.41`'s total gains `pop_culture` (era 7). If either one unlocks it, the tool's reading is the engine's: note it in `law_gate` |
