# Writing in-game text

**Draft for the owner's review (2026-11-09).** The questions at the end are open; nothing lints against this yet.

This is the house style for everything under `localization/english/`: what a player reads in the game. It says how each kind of text should read. It does not repeat the rules that already have a home:

- Event titles, descriptions, flavor and options in depth, with the vanilla conventions they follow: `event_creation_guide.md` § "Event Localization Style Guide".
- Labels that fit their cells, type sizes, what goes in a tooltip and what in a How section: `gui_style_guide.md`.
- Loc syntax (scope references, `#b`, concept links, quoting): `.claude/rules/localization.md` and `scripting_best_practices.md`.
- The player guide, which is prose about the game, not text in it: `docs/player_guide/STYLE.md`.

## The voice

The game's text is written by someone who knows exactly what happened and sees no need to dress it up. It names the thing, gives the figure, and stops. When it is funny, it is funny because it is exact: "The intruder was a bear."

Two tests cover most cases.

**Could this sentence be about anything else?** "The resolution has brought stability and improved relations with our neighbors" fits a treaty, a wedding or a new bus route. "The loan and a tenth more, over five years" fits one thing. If a sentence would survive being moved to a different modifier, event or law, it is filler: replace it with the particular fact, or cut it.

**Would a minister's private secretary say it?** The register is a capable official briefing the government: dry, specific, unimpressed. Not a press release ("a hallmark of a modern, healthy society"), not a textbook ("this represents a significant shift"), not a film trailer ("the cultural establishment is reeling").

## Who is speaking

- **Events and their options, modifier descriptions, notifications and tooltips about the player's own country speak as the country: "we", "our".** "Our people's average standard of living has fallen below 4." This is the base game's voice and most of the mod's.
- **Text that can appear on any country** (a modifier another country holds, a law's description, a tooltip on a foreign state) **says "this country" or names it.** "This country is repaying an emergency loan from the United Nations."
- **Concept descriptions and How sections state the rule impersonally:** "a country", "the holder", "a milestone". They say "you" only for a control the player works: "Where you want the policy rate to end up."
- **Flavor text has its own speakers.** Whoever is talking in it talks as themselves.

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

The modifier's lines already show what it does. The description says why the country has it, in one concrete sentence, and does not restate the effects.

> **Before** (`border_dispute_resolved_modifier_desc`): The resolution of a border dispute has brought stability and improved relations with our neighbors.
> **After:** A border dispute with a neighbor has been settled.

> **Before** (`predictive_intelligence_only_modifier_desc`): AI is used only for intelligence analysis, not direct policing, balancing security with civil liberties.
> **After:** AI sorts intelligence reports. It does not direct the police.

"Brought stability" and "balancing security with civil liberties" are the effects, restated as abstractions; the modifier's own lines say them better. Where the terms are the interesting part, give them:

> **As it should be** (`un_loan_repayment_modifier_desc`): This country is repaying an emergency loan from the United Nations: the loan and a tenth more, over five years.

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
- **Say only what the script does.** A tooltip that promises an effect the script does not produce is a bug. Read the script first.

> **As it should be** (`concept_banking_rate_target_desc`): Where you want the [policy rate] to end up. Stepping it does not move the rate today: the rate closes the gap a little each month. There is no fee and no cooldown for changing it.

It answers the three things a player wonders on first seeing the control: what it is, why nothing happened when they clicked, and what it costs.

### Events

`event_creation_guide.md` has the full conventions. What matters most for the voice:

**The description reports particulars.** A reader should see the situation, not be told how serious it is.

> **Before** (`banking_cycle_events.3.d`): Banks are sitting on mountains of reserves while businesses starve for credit. Lending has ground to a near-halt as financial institutions, scarred by recent uncertainty, refuse to take on risk. Merchants and manufacturers are demanding that the government intervene to restart the flow of capital - but bankers warn that forcing premature lending could plant the seeds of the next crisis.
> **After:** The banks hold more in reserve than they have in years and are lending none of it. A mill owner with a full warehouse cannot borrow against it to meet his payroll. Merchants and manufacturers want the government to lean on the banks. The bankers reply that they were leaned on once before.

The first version has four stock metaphors (mountains, starving, grinding to a halt, planting seeds) and ends on a balanced "but". The second has one case the reader can picture and lets the bankers have the last, dry word.

**Flavor is a scene, with someone in it.** The model is `nuclear_incident.40.f`: two unnamed voices, a forty-page report, and "Most of them say 'check it twice.'" Nothing in it states that the incident was absurd or alarming; the exchange shows it.

**The description's last sentence is the one most worth rereading.** Drafts tend to close on a summary of the mood ("The cultural establishment is reeling.", "The survivors' accounts are harrowing."). End on a fact instead: the last thing that happened, or the question now on the table.

**Options are what the ruler says, not labels.** "Fix the procedure that failed, and check the ones that didn't." beats "Hire the hackers".

**Titles hint.** "A Routine Mishap", not "Hacker Collective Attack".

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
- **No text ends with `\n`.**

## Words

- **One name per thing.** Use the in-game name, spelled and capitalized as its own key renders it, and splice it (`$key$`) rather than retyping it, so a rename reaches every mention.
- **A coined term says what it means** the first time, or links the concept that does.
- **Do not put one faith's furniture in a scene any country can get** (a priest, a pew, a sermon). Write the scene without a named faith or gate the version. `event_creation_guide.md` has the pattern.

## Before you commit a text

1. Read it without its key. Can you tell what it is attached to? If not, it is generic.
2. Find the sentence that would survive being moved to another entry, and replace or cut it.
3. Check every claim about an effect against the script.
4. Check the last sentence: a fact, not a mood.
5. Read the longest it can render (the longest country name, the largest figure) against the cell or tooltip it sits in.

## Open questions for the owner

1. **"We" or "you" in tooltips.** The mod uses "we/our" in about 500 tooltips and "you/your" in about 80, and concept descriptions use "you" more than "we". The rule above ("we" for the country, "you" only for a control the player works) is my reading of the majority. Is it yours?
2. **How dry.** The examples lean toward the driest text in the mod (`nuclear_incident.40`). Some older events are warmer and more literary (`environmentalism_events.5.f`, the farmer and the cracked soil). Is that range welcome, or is the dry end the target?
3. **Semicolons in rules text.** About 250 tooltips and 70 concept descriptions use them. I've allowed them for paired facts and discouraged them in event prose.
4. **Existing text.** About 110 lines match the machine-writing list, 114 event descriptions use ` - ` as a dash and 150 use an em dash. A lint would start from an allowlist of today's hits and fail only new ones. Rewriting the old lines is a separate pass, and each changed line needs retranslating into German and Spanish.
