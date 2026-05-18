# Event Creation Guide

Reference for creating events in the Vic3TimelineExtended mod. Covers boilerplate, style conventions, design principles, and available assets.

## Event Boilerplate

```
namespace_name.N = {
	type = country_event
	placement = ROOT

	title = namespace_name.N.t
	desc = namespace_name.N.d
	flavor = namespace_name.N.f

	event_image = { video = "video_name" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_default.dds"

	duration = 3
	cooldown = { days = long_modifier_time }

	trigger = { ... }
	immediate = { ... }

	option = {
		name = namespace_name.N.a
		default_option = yes
		...
		ai_chance = { base = 5 }
	}
}
```

## Available Event Videos

Vanilla: `africa_animism`, `africa_city_center`, `africa_public_protest`, `africa_soldiers_breaking_protest`, `asia_buddhism`, `asia_confucianism_shinto`, `asia_dead_cattle_poor_harvest`, `asia_factory_accident`, `asia_poor_people_moving`, `asia_sepoy_mutiny`, `asia_union_leader`, `europenorthamerica_before_the_battle`, `europenorthamerica_capitalists_meeting`, `europenorthamerica_political_extremism`, `europenorthamerica_rich_and_poor`, `europenorthamerica_springtime_of_nations`, `europenorthamerica_sufferage`, `middleeast_battlefield_trenches`, `middleeast_courtroom_upheaval`, `middleeast_oil_derricks`, `middleeast_police_breaking_door`, `southamerica_christianity`, `southamerica_election`, `southamerica_factory_opening`, `southamerica_public_figure_assassination`, `southamerica_war_civilians`, `unspecific_airplane`, `unspecific_automobile`, `unspecific_devastation`, `unspecific_factory_closed`, `unspecific_fire`, `unspecific_gears_pistons`, `unspecific_military_parade`, `unspecific_naval_battle`, `unspecific_politicians_arguing`, `unspecific_ruler_speaking_to_people`, `unspecific_sick_in_hospital`, `unspecific_signed_contract`, `unspecific_trains`, `unspecific_vandalized_storefront`, `unspecific_world_fair`, `votp_barricade`, `votp_conspiring`, `votp_cops_march`, `votp_prison`

Mod-added: `event_power_plant`, `event_skyscrapers_sunset`, `event_space_station`

## Available Event Icons

`event_default.dds`, `event_diplomacy.dds`, `event_election.dds`, `event_fire.dds`, `event_industry.dds`, `event_military.dds`, `event_money.dds`, `event_newspaper.dds`, `event_portrait.dds`, `event_protest.dds`, `event_scales.dds`, `event_trade.dds`, `event_urbanization.dds`, `stock_bag.dds`, `waving_flag.dds` (all under `gfx/interface/icons/event_icons/`).

## IG Approval Modifiers (mod-defined)

For IG reactions to events:
- `ig_approval_positive_modifier` (+3 IG approval) — apply to specific IGs with `every_interest_group { limit = { is_interest_group_type = ig_X } add_modifier = { name = ig_approval_positive_modifier ... } }`
- `ig_approval_negative_modifier` (-3 IG approval)
- `ig_approval_very_negative_modifier` (-5 IG approval)

## On_Actions Wiring for Repeatable Events

To make events fire as part of the yearly event cycle, create a file in `common/on_actions/` with:
```
on_yearly_events = {
	random_events = {
		chance_to_happen = 65
		10 = namespace.N
		12 = namespace.M
	}
}
```
The number before `=` is the relative weight. Higher weight = more likely to be picked when the event pool fires. `chance_to_happen = 65` means 65% chance each year.

## Localization for Events

- Create a separate file per namespace: `localization/english/<namespace>_l_english.yml`
- Must have `l_english:` header line, UTF-8 BOM encoding, one leading space before each key.
- Required keys per event: `.t` (title), `.d` (description), `.f` (flavor text), `.a`/`.b`/`.c` (option button text).
- Conditional descriptions use `_variant` suffix (e.g. `.d_modern`, `.d_tv`, `.d_cyber`).
- Required keys per modifier: `modifier_name:0 "Display Name"`, `modifier_name_desc:0 "Tooltip description."`

## Event Localization Style Guide (Based on Vanilla Conventions)

The following patterns are derived from analysis of 40+ vanilla events across `events_l_english.yml`, `ip2`/`ip3`/`ip4` DLC packs, and `sphere_of_influence` content. **Follow these conventions** so mod events feel consistent with the base game.

### Titles (`.t`)
- **Short and evocative** — typically 2–5 words. Titles are noun phrases, metaphors, or pithy labels, not full sentences.
- **Flavor over mechanics.** Titles hint at the theme without naming specific gameplay effects. "Eye of the Needle" (religion vs industry), "These Dark Satanic Mills" (rural vs industrial), "Pie in the Sky" (devout vs unions).
- **Literary or idiomatic references** are common: biblical phrases, proverbs, famous quotes, cultural allusions. "All Hitherto Existing Society", "Workers of the World", "If You Want Peace".
- **Dynamic titles** using scope interpolation are acceptable for country-specific or character-specific events: `"The [SCOPE.sCountry('owner_country_scope').GetAdjective] Dream"`, `"[SCOPE.gsInterestGroup('ig_on_the_edge').GetName] Have Demands!"`.
- **No trailing punctuation** unless it's an exclamation for dramatic effect ("Gold Rush!", "Bring our Boys Home!").
- **Capitalization:** Title Case for all significant words.

### Descriptions (`.d`)
- **Concise, factual, and in-world.** Descriptions present the situation to the player in 1–3 sentences. They explain *what is happening* and *who is involved* — never reveal mechanical effects or tell the player what to think.
- **Third-person narration** from the government's perspective. The player is the government; NPCs "approach", "petition", "demand", "express concern", etc.
- **Heavy use of scope references** to name IGs, characters, states, countries, and laws dynamically: `[SCOPE.gsInterestGroup('landowners_ig').GetName]`, `[SCOPE.sCharacter('leader').GetFullName]`, `[ROOT.GetCountry.GetAdjectiveNoFormatting]`.
- **Gender-neutral character references** use the engine's pronoun functions: `[SCOPE.sCharacter('X').GetSheHe]`, `[SCOPE.sCharacter('X').GetHerHis]`, `[SCOPE.sCharacter('X').GetHerselfHimself]`.
- **No formatting codes** in descriptions (no `#bold`, `#italic`, `#R`, etc.). Descriptions are plain text with scope interpolation only.
- **Exceptions:**
  - `#N` (newline with emphasis) for mechanical warnings in DLC events.
  - `#G`/`#R`/`#b` for **mechanical thresholds or required actions** — e.g. `#G 2/3 supermajority#!` to highlight a vote threshold, or `#b [concept_migration_pull]#!` to flag a required setup action. Reference: `un_vote.*.d_expulsion*` and `te_map_modes.1.d`. Use only when the highlighted text names a number, threshold, or action the player must understand to choose between options — not for decorative emphasis.
  - `#v` is the engine's **value-formatting convention** (e.g. `#v [SCOPE.…ScriptValue('temperature_anomaly_display')]#! °C`) and is NOT a `#bold`-style color code. It is always permitted where a live numeric value is displayed inside a description. Reference: `environmentalism_events.*.d`.
- **Typical length:** 1–3 sentences (30–80 words). Shorter is better. Let the flavor text carry the literary weight.

### Flavor Text (`.f`)
- **Literary, atmospheric, and character-driven.** Flavor text is the creative writing showcase of the event. It sets mood and humanizes the situation. It is not a place to summarize what happened — the description (.d) is where the player learns the facts. Flavor text exists to give that situation texture and a human grain.
- **Typical length:** 3–8 sentences, roughly 50–150 words. Shorter is not better. Flavor text below this range reads as a news ticker and wastes the slot.
- **Default form: direct speech (quotes).** The vast majority of vanilla flavor texts contain dialogue, and this is the defining stylistic signature of Victoria 3 events. Reach for dialogue first. Use one of the other forms only when you have a specific reason — an epigraph that fits the theme, or a vignette that captures something dialogue can't.
- **Dialogue conventions:**
  - Multiple speakers are separated by `\n\n` (paragraph breaks).
  - Speakers are almost never named — they are anonymous voices (a farmer, a politician, a soldier, a shopkeeper). This lets the text feel universal rather than character-specific.
  - Dialogue captures the *emotional tone* of the affected faction — arrogant industrialists, pious clergy, cynical soldiers, earnest workers.
- **Narrative vignettes** are the second common form: short prose scenes anchored in a specific perspective — what a participant or witness sees, hears, or feels in a particular place at a particular moment. A vignette needs a viewpoint, not just an account of events. Written in present or past tense with vivid sensory detail.
- **Famous quotes or literary epigraphs** are occasionally used, attributed with `— Author Name` (em-dash). A genuine, historically attributed quote may stand alone as the entire flavor text without satisfying the 50–150 word guideline — the quote *is* the flavor. This is the only sanctioned single-line flavor form; invented aphorisms do not qualify. Reference: `nuclear_weapon_events.10.f_world_first` ("Now I am become Death, the destroyer of worlds." — Oppenheimer). Use sparingly; if you cannot name the historical author, write dialogue or vignette instead.
- **Anti-patterns to avoid:**
  - **Two-line reportage.** "X happened. Then Y happened." compressed to a single visual line is the most common failure mode. It can technically clear the length minimum if the sentences are long enough, but it reads as a wire summary, not flavor. If the prose could appear unchanged in a newspaper headline rundown, it isn't doing the job of flavor text.
  - **Subject-less observation.** Sentences that describe events from no one's vantage point ("The march filled six city blocks. The police stopped counting heads.") read as sterile reportage. Anchor in a perspective — even an unnamed bystander, organiser, officer, journalist, or letter-writer. This is the "show, don't tell" principle from the General Tone section, applied to flavor specifically.
  - **Formulaic repetition across a chain.** Even if individual entries pass on their own, a journal entry chain where most events share the same compressed structure reads as monotonous and stylistically distinct from the rest of the mod. Vary forms across a chain: dialogue should dominate, with a minority of vignettes and the occasional epigraph for variety. If you've written three events in the chain and they all open with "The [noun] [verbed]. The [other noun]...", stop and rewrite.
- **Attributed fictional quotes with random character names:** For events where dialogue is attributed to a role (scientist, commander, engineer), use `create_character` in `immediate` to generate a culturally-appropriate character name, then `kill_character` in `after` to clean up. This gives each event a unique, culture-matching name without reusing existing game characters. Pattern:
  - **Script:**
    ```
    immediate = {
        create_character = {
            save_scope_as = flavor_speaker
            on_created = {
                place_character_in_void = 6
            }
        }
    }
    after = {
        hidden_effect = {
            if = {
                limit = { exists = scope:flavor_speaker }
                scope:flavor_speaker = { kill_character = { hidden = yes } }
            }
        }
    }
    ```
  - **Loc:** `"\"Quoted dialogue text.\"\n\n— [SCOPE.sCharacter('flavor_speaker').GetFullNameNoFormatting], Role Title"`
  - Example: `"\"The geysers are how we found the ocean.\"\n\n— [SCOPE.sCharacter('flavor_speaker').GetFullNameNoFormatting], Subsurface Exploration Lead"`
  - Use `GetFullNameNoFormatting` instead of `GetFullName` so the character name is plain text (not a tooltipable link to a throwaway character).
  - **CRITICAL: `place_character_in_void = 6`** — Without this, the engine's periodic character pruning (~monthly) garbage-collects roleless characters while the event is still open. The flavor text name disappears after ~20-25 days. `place_character_in_void = N` moves the character to a protected pool for N months, keeping it accessible via `scope:flavor_speaker` and exempt from pruning. The `kill_character` in `after` still cleans up immediately when the player picks an option.
  - **Guard with `exists = scope:flavor_speaker`** — If the player never responds (auto-resolved at `duration`), or if the character is somehow already gone, the guard prevents "Event target link 'scope' returned an invalid object" errors.
  - The em-dash (`—`) followed by the scoped name and role title matches vanilla's attributed-quote convention while adding cultural authenticity.
  - **Do NOT use `random_scope_character`** — countries have few characters (generals, politicians), so the same name would appear across many events.
- **Formatting in flavor text:** `#bold text#!` for emphasis, `#italic text#!` for italics, `\n` / `\n\n` for line/paragraph breaks. Used sparingly.
- **Tone:** Sardonic, wry, occasionally darkly humorous. Victoria 3 flavor text frequently has an ironic or world-weary quality.

### Option Text (`.a`, `.b`, `.c`, etc.)
- **Short, punchy, and in the voice of the player/ruler.** Option text is what the player "says" when choosing.
- **Typical length:** 5–15 words. One sentence or a short phrase. Never more than two sentences.
- **Common patterns:**
  - Declarative statements of policy: "Capital drives progress." / "Workers deserve the fruits of their labor."
  - Commands or directives: "Spread the word!" / "Crack down hard!"
  - Concessive or diplomatic: "We shall address their grievances."
  - Dismissive or defiant: "What an utterly ludicrous idea." / "Not our business."
  - Resigned reactions (for forced events): "Unfortunate." / "Blast!" / "A terrible shame."
- **NO mechanical language.** Option text never says things like "Gain +5 prestige".
- **Dynamic references** to IGs, characters, and countries are common.
- **Each option should have a distinct voice** — one aggressive, one moderate, one cautious, etc.
- **Tooltip text** (`.a.tt`, `.b.tt`) is used sparingly for extra mechanical clarification.

### General Tone and Voice
- **Formal but not archaic.** The writing should feel polished and professional, suitable for a game spanning 1836 to the 2030s. Use language that is timeless where possible.
- **Modern language is preferred over archaic language** to avoid immersion-breaking anachronisms. For example, use "scientists" not "natural philosophers", since the mod's events often fire in the 20th–21st century. When referencing specific technologies, use the appropriate era's terminology.
- **Political and class-conscious.** Events frequently frame situations through the lens of class conflict, political ideology, national identity, and institutional power — the core themes of Victoria 3.
- **Show, don't tell.** Events present situations and let the player interpret them. Descriptions don't editorialize, and flavor text grounds events in a perspective rather than narrating them from nowhere.
- **Dark humor and irony** are staples.
- **No modern anachronisms in tone** (no slang, no internet-speak), but the writing should be accessible to modern readers.
- **Avoid dichotomous and epigrammatic styles.** Two common failure modes that read as authored rather than observed:
  - **Dichotomous framing** sets up a clean "on the one hand X, on the other hand Y" or "some say A, others B" structure. It reads as a debate-club summary rather than a situation. People living through an event don't experience it as a balanced two-sided dilemma — they experience it from inside one perspective with the other side as an obstacle, irritant, or absence. If you find yourself writing a balanced pro/con paragraph in flavor or description, rewrite from one specific viewpoint (a worker, a clerk, a soldier) and let the other side appear only as it intrudes on that perspective.
  - **Epigrammatic writing** packs every sentence into a pithy, aphoristic, quotable form ("Bread today, freedom tomorrow." / "Capital flows where conscience cannot follow."). Occasional epigrams are fine — vanilla uses attributed historical quotes as flavor — but stringing them back-to-back reads as a slogan generator rather than text. Aphorisms work because of contrast with surrounding ordinary prose; without the contrast they wear thin within two sentences. If multiple sentences in a row sound like they could be embroidered on a banner, rewrite the connective tissue as plain observation or dialogue.

## Event Design Guidelines

### Option Tradeoff Principles
- **Every multi-option event must present a meaningful choice.** No option should be strictly better or strictly worse than all alternatives.
- **A modifier can be all-upside or all-downside** — but if so, other options must be comparably attractive/unattractive. The audit isn't "force every option to have a tradeoff"; it's "no option is strictly dominated."
- **Outcome direction must match the setup.** The pop direction (loyalists vs radicals) and modifier direction (beneficial vs costly) of an option should match the in-fiction reception of that choice given the event's premise. An option that nets loyalists in the strata most aggrieved by the event's premise is a *coherence* bug even if it's competitive on balance — e.g., during an unpopular war, "let the peace rally proceed" giving lower-strata loyalists implies the underlying anger was satisfied by being heard, when nothing about the war actually changed. Re-anchor the trigger (gate on `is_at_war = yes`?) or flip the offending pop direction.
- **"Do nothing" / passive options** must have at least one tangible benefit (e.g., upper-strata loyalists, authority preserved).
- **Ambitious / expensive options** must have at least one tangible cost (e.g., bureaucracy drain, IG disapproval, radicals).
- **Single-option events** (forced crises) are acceptable.
- **Option text does NOT need to spell out the tradeoff.** Keep button text thematic and concise.

### Verifying Option Balance

The mod state server has an `/event-balance` family of endpoints for catching dominated options.

**What it does.** Walks each option's body (descending into `if`/`else_if`, `random_list`, `every_*`/`ordered_*`/`random_*` scope iterators, scope-change keys like `je:je_X` / `ig:ig_X` / `s:STATE_X`, `custom_tooltip`, `hidden_effect`). For every `add_modifier` and `add_enactment_modifier` it finds, it looks up the static modifier in `common/static_modifiers/`, reads each numeric field's `color` from the modifier-type definition, and computes a player-perspective `polarity` from value-sign × color:

| color | value > 0 | value < 0 |
|-------|-----------|-----------|
| good  | positive  | negative  |
| bad   | negative  | positive  |
| neutral | neutral | neutral   |

It then aggregates `polarity_totals = {positive, negative, neutral, unknown}` per option.

**Inspection (single event or batch).**

```bash
# One event, human-readable
curl -s 'http://localhost:8950/event-balance/banking_cycle_events.10?format=text' | python3 -c "import json,sys;print(json.load(sys.stdin)['text'])"

# All events in a file
curl -s 'http://localhost:8950/event-balance?file=events/banking_cycle_events.txt&format=text' | …

# Every event in a namespace
curl -s 'http://localhost:8950/event-balance?prefix=banking_cycle_events&format=text' | …
```

**Audit (find dominated options across the mod).** Two modes:

```bash
# Strict — flag events where one option is pure-positive on modifiers
# (≥1 positive, 0 negatives) and another is pure-negative (0 positives, ≥1 negative)
curl -s 'http://localhost:8950/event-balance/issues?format=text' | …

# Soft — flag events where one option has ≥ as many positive fields AND ≤ as many
# negative fields as another, with combined gap ≥ threshold (default 2). Catches
# mixed-vs-mixed dominance the strict check misses.
curl -s 'http://localhost:8950/event-balance/issues?mode=soft&threshold=3&format=text' | …
```

Both modes accept `?prefix=<namespace>` / `?file=events/foo.txt` filters.

**Always verify each flag against the source `.txt` before editing.** The audit only sees `add_modifier` / `add_enactment_modifier` field polarity. Common false-positive sources:

- **Non-modifier compensation** — `add_treasury`, `add_radicals` / `add_loyalists`, `add_momentum` (party momentum is the actual point of most election-event choices), `change_variable` (mod-defined journal-entry pressures), `change_relations` / `change_infamy`, `set_ideology`.
- **Modifiers applied to other actors** — `scope:detected_by_country = { add_modifier = ... }` boosts a rival; the audit counts that as a positive on the player's option.
- **Choice-routing via `set_variable`** — space race events use this to gate downstream events with different rewards; the *immediate* modifier is just the cost.
- **Trigger-gated alternatives** — options with `trigger = { has_variable = X }` or `has_law = Y` are visible only in specific scenarios, not actually competing.
- **Scripted effects** (e.g. `sr_apply_moon_base_reward = yes`) and **`activate_law`** — the structural payoff is invisible to the audit.
- **Conditional `if` branches** — modifier applications inside disjoint `if`/`else_if` siblings are all counted, even though only one fires per playthrough.
- **Durations** — the audit counts modifier *fields* not `days = …`. An option with a 2-field modifier at `long_modifier_time` may be much stronger than one with a 5-field modifier at `short_modifier_time`.

**Intentional asymmetries are fine** — regressive options gated by `law_active_persecution` / `law_no_womens_rights` / `country_is_fascist`, ministry-investment payoffs gated by `has_intelligence_ministry_3`, and isolationist/sovereigntist refusal options are deliberate roleplay choices.

After editing modifier or event files, `POST /reload` to refresh the server's view before re-running.

### Toggle vs Cooldown Design Preference
- **For policy choices reflecting long-term strategic orientations, prefer toggles over one-shot actions with cooldowns.**
- **Toggle pattern:** Two button pairs — "Enable X" (visible when NOT active) and "Disable X" (visible when active). The "Enable" button adds a permanent modifier. The "Disable" button removes it. Ongoing effects are processed in the relevant pulse.
- **Cooldown pattern is appropriate for discrete actions** — things that happen once and resolve.

### Interest Group Reactions as Balancing Tool
- Use strata-based `add_radicals` / `add_loyalists` to create faction-based tradeoffs:
  - **Upper strata (industrialists):** Generally oppose government spending on social/environmental programs; approve of laissez-faire.
  - **Academics (intelligentsia):** Generally support progressive, scientific, or diplomatic approaches.
  - **Lower strata (workers/peasants):** React to standard-of-living impacts; oppose austerity; approve of relief spending.
- For IG leader ideology changes (`set_ideology`), always pair with some cost — these are powerful effects.

### Modifier Design
- **Modifiers in `common/static_modifiers/extra_modifiers.txt`** — every new modifier needs an `icon`, gameplay fields, and two loc keys.
- **Differentiate options mechanically**, not just by magnitude. Each option should apply a different modifier with distinct effects.
- **Duration tiers:** `short_modifier_time` (1 year), `normal_modifier_time` (3 years), `long_modifier_time` (5 years). Use `is_decaying = yes` for most event modifiers.
- **Icon convention:** `modifier_coins_negative.dds` for economic costs, `modifier_lightbulb_positive.dds` for research/innovation, `modifier_flag_positive/negative.dds` for political/prestige, `modifier_gear_positive/negative.dds` for production/throughput, `modifier_military_negative.dds` for military costs.

### Localization Scope References
- **In event loc strings**, use typed scope syntax: `[SCOPE.sCountry('scope_name').GetName]` — not `[scope:scope_name.GetName]`.
- Common patterns: `[SCOPE.sCountry('X').GetName]` for countries, `[SCOPE.sState('X').GetName]` for states.

### Event Scoping Patterns
- **For rival countries:** Use `random_country` with `limit = { has_diplomatic_pact = { who = ROOT type = rivalry } }` — not `random_rival_country` (which doesn't resolve properly for loc).
- **For former colonies:** Use `was_formed_from = ROOT` in limits.
- **For colonial states:** Use the `is_overseas_colonial_state` scripted trigger.
- **Always `save_scope_as`** in the `immediate` block when an option needs to reference the scoped entity later.

### AI Weights in Events
- **`ai_chance` blocks in events use MTTH (Mean Time To Happen) syntax**, NOT script value syntax.
- **Correct:** `ai_chance = { base = 5 modifier = { trigger = { <condition> } add = 3 } }`
- **WRONG:** `ai_chance = { base = 5 if = { limit = { <condition> } add = 3 } }` — causes silent failures.
- **Nested conditions:** Use AND inside `trigger = { }`, or `OR = { }` inside `trigger`.

#### Authority-Spending Options (and Other "Spend a Resource" Choices)
When an option costs authority (or any resource), AI weights need three pieces of care that aren't obvious:

1. **Gate on free authority, not produced authority.** `produced_authority` is total generated and is essentially always above any cost threshold late-game; the AI will pick options it can't actually pay for, and end up authority-negative. Use `authority > <cost>` instead. (See `docs/guides/scripting_best_practices.md` § Authority Triggers.)
2. **Don't put all the weight on a single threshold modifier.** A single `modifier = { trigger = { authority > 750 } add = 6 }` flips from 0 to 6 the moment the country has *just* enough — the AI will spend its last 750 authority on the largest tier. Stack incremental bumps (`+1` at the threshold, `+1` at 2× threshold, `+1` at 3× threshold) so the AI prefers the largest tier only when it has comfortable surplus.
3. **Bump the default option's `base` weight.** A `base = 1` default versus three `+0…+6` paid options means the paid options dominate the random pick. Default should usually win for routine plays — set its `base` to 2–3 and tune the paid-option ramps so they only overcome it when the country has obvious surplus.

**Reference pattern** — `events/minor_events.txt:34-187` (Forceful Legislation event, options B/C/E). Each tier's weight starts at 0, gains +1 at the cost threshold, and gains another +1 at each surplus band above. Authority below cost → weight 0 → AI never goes negative.

### Law Enactment Mechanics — Modifiers That Actually Push a Law Through
When designing events that interact with an in-progress law enactment, distinguish "make IGs willing to talk" from "make the law actually pass". The mechanics:

- **`country_amenability_add`** — bumps IG amenability. This is *willingness to negotiate*, not active push. By itself it does little to fight a hostile enactment.
- **`country_law_enactment_success_add`** — flat **percentage points** added to the success roll each tick. Powerful: a +25 here is "+25% chance per check that the law passes". Bypasses opposition-driven failure odds.
- **`country_law_enactment_stall_mult`** — multiplier on the chance the enactment stalls due to opposition. **Negative reduces stalls** (e.g., `-0.50` = half as likely to stall).
- **`country_law_enactment_max_setbacks_add`** — how many enactment setbacks the country can absorb before the law fails. `+1` is meaningfully more resilience.
- **`country_law_enactment_time_mult`** — affects total enactment duration. **Negative is faster** (e.g., `-0.20` = 20% faster passage).
- **`add_enactment_phase = N`** — *one-shot effect, not a modifier.* Directly advances the enacting law N phases toward `NPolitics::LAW_ENACTMENT_MAX_PHASES` (which is the pass condition). The most direct way to "force a law through" mechanically.
- **`add_enactment_setback = N`** — inverse: pushes toward failure.

**`add_enactment_modifier`** scopes a static modifier to *the current enactment only* — it clears when the enactment ends, however it ends. Apply enactment-passage modifiers via `add_enactment_modifier`, not via `add_modifier` with a `years = N` duration. Apply lasting consequences (legitimacy hits, IG approval drops) via regular `add_modifier`.

**Reference:** `common/static_modifiers/extra_modifiers.txt` (`forced_law_through_event_enactment_*`) for stacked-passage modifiers; `events/minor_events.txt:144-186` (option E of the Forceful Legislation event) for an `add_enactment_phase = 1` one-shot.
