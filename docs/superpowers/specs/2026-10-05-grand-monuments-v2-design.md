# Grand Monuments v2: commissions, names, history, policy and trophies — design

## Context

The September rework (`docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md`, "v1" below) made the Grand
Monument a political instrument: dedications with kinds, grandeur on the doubling curve, national totals on the
Monuments journal entry, contested monuments with Pull Down / Rededicate / Keep as Heritage, skins, vanity backlash and
anniversaries. That design stands. This one fixes what play showed:

- **Too expensive to matter.** A level costs 10,000 construction (`construction_cost_grand_monument`), four base-game
  monuments (2,500 each) and 12 to 50 factory levels (200–800). The first step (5 levels, 50k) buys about what one
  base-game monument gives, plus the dedication's first step. The price is left over from the construction-sink design,
  and the comment above it still argues for that design. The doubling curve already stops spamming, so the price no
  longer needs to.
- **The AI never builds them**, so a player rarely conquers one or sees a foreign monument contested. Price is only part
  of it: `scripting_best_practices.md` § "AI and Cost-Only Buildings" records the Strategic Reserve Hub at `ai_value`
  +10,000 being built by 1 country in 157.
- **A stable country never touches the journal entry.** The entry asks a question only when a regime falls, and a
  stable republic's one regime dedication never falls.
- **No flavour of its own.** A monument has a dedication and a skin but no name, and the world starts with none.

v2 makes monuments cheap enough to build often, gives the AI and stable countries reasons to build them (commissions),
names them, places the ones standing in 1836, adds a national policy, and lets a conqueror carry one home as a trophy.

Baseline: `main` at `c906371` (#743 merged).

## Decisions (owner, 2026-10-05)

| Question | Decision |
|---|---|
| Cost | **1,000 construction a level** (a tenth). Below a base-game monument, but one level is only part of a Grand Monument |
| Vanity backlash | **Stays per level, divided by about ten.** People are angry while the monument goes up, so it is not charged per step |
| Rededicate's price | Down by the same factor |
| AI building | Through **commissions** (§2): the AI gets the same offers the player does and queues construction when it accepts |
| Stable countries | **All three:** a **monument policy** (§5), **commissions from world moments** (§2.2) and **interest-group petitions** (§2.2) |
| The events rule | v1's "every option positive" becomes: **owning a monument is never a penalty; not building one can be.** Declining a petition may cost approval. Anniversary events keep all-positive options |
| Commissions | **One mechanism** for world moments, petitions and AI building; **at most one open at a time** |
| Journal entry | **Appears for an open commission** as well as for an owned monument |
| Names | A monument is named by choice: a **namesake** (city, state, ruler, what it honours, a year, an occasion) and a **form** (column, arch, statue, …). A **typed name** overrides the pair, typed in the base game's company-rename popup on a placeholder company that exists only while the player names (§3.5, tested in game). It costs a company-limit alert for a moment at each end, which the owner accepts |
| History | **Monuments standing in 1836 are placed at the start.** v1's "History places no Grand Monuments" is reversed |
| Historical commissions | **Yes**, as hand-written commissions for whoever holds the state; they fill v1's empty `LANDMARKS` table |
| Trophies | **Yes.** A conqueror may carry a portable monument home. It keeps **half its grandeur** (as Rededicate). **Retaking the site offers to bring it home; it is a choice, not automatic** |
| Phasing | Numbers → commissions with names → policy → 1836 monuments → trophies → historical commissions (§10). The owner swapped the policy ahead of the 1836 monuments on 2026-10-05 |
| Who gets commissions (owner, 2026-10-05, after the build) | **Great and major powers only.** Five levels are 5,000 construction, beyond a minor power's means within five years |
| Refusing (owner, 2026-10-05, after the build) | **A miss costs more than a refusal** (−15 against −5 on the petitioner's ledger), and an unanswered offer is declined: otherwise accepting dominated refusing |
| Vanity (owner, 2026-10-05, after the build) | **−1 legitimacy per ledger unit**, not −0.3, which rendered as "−0" |

## Engine facts this rests on

v1's engine facts all still hold (buildings hold no variables; no effect removes levels; the dedication ratchet; modifiers
flow down only; JE-scoped modifiers; `multiplier = var:` resolves against ROOT). New ones:

- **Typed text reaches script only through a base-game rename popup (tested in game, 1.14.5).** A mod's own editbox
  returns a `CUTF8String`, which nothing converts into the `CString` script takes. A rename popup stores the typed name
  on its object, and that name reads back as a `CString`. Of the carriers tried, only a placeholder company works: a
  state's typed name can't be undone, the hub accessors ignore renames, and armies hold no variables
  (`gui_modding_guide.md` § "Typed text into script", `scripting_best_practices.md` § "Player-Typed Names"). Script
  can't write such a flag (`flag:` takes identifiers only), so typed names override names that script assigns and
  can't replace them (§3).
- **The hub accessors return the map's names.** `State.GetForestryHubName` ignored the player's rename of a logging
  town, and `GetCityHubName` is the same family, so the City namesake prints the map's city name, not a player's.
- **A high `ai_value` does not make the AI build a government building**; an event or decision with `ai_chance` does
  (`scripting_best_practices.md` § "AI and Cost-Only Buildings"). `start_building_construction` (state scope) "starts
  constructing a building in a scoped state as a government construction", so an accepted commission costs the AI
  real construction, unlike `create_building`. The mod uses only `start_privately_funded_building_construction`
  (`extra_effects.txt`); whether the government form adds a level to an existing building, and whether the construction
  AI cancels what script queued, are unverified.
- **History is an effect block.** `common/history/extra_history.txt` (`GLOBAL = { … }`, run last) can `create_building`
  with `activate_production_methods` (the audit flags that key; it carries a `# REVIEWED` comment) and `set_variable`.
- **Script containers** (`create_container = { tags = { … } parent = … }`, `covert_warfare_effects.txt`). One with no
  `parent` outlives every country. The pool is global and unindexed, so a per-country `every_container` scan is
  expensive; one global monthly pass that writes per-country totals is the cheap shape (`scripting_best_practices.md`
  § "Script Containers").
- **What a civil war's winner inherits:** variables, not modifiers or variable lists. Commission state is variables; the
  petitioning interest group is stored as a **flag naming its type**, not an IG scope, because the winner's IGs are
  different objects.
- **Country names from a stored variable:** `Var('x').GetCountry.GetName` failed in this mod's testing; the workaround
  stores a state and reads its owner, or keeps the text generic (`scripting_best_practices.md`, loc accessors).
- **`pm_no_maintenance` is disabled under the default construction market setting** (`disable_pm_no_maintenance` in
  `extra_game_rules.txt`), so a policy cannot cut upkeep by switching methods. Throughput doesn't scale a
  `level_scaled` input either (`scripting_best_practices.md` § "Production Method Modifier Scaling Blocks"), so the
  policy puts `goods_input_construction_mult` on the monument building itself, as the engine's `pm_retooling` does
  (built in phase 3).
- **On-actions for world moments:** 1.14.5's `on_won_war` / `on_lost_war` (ROOT = a country on the winning or losing
  side, `scope:war`, `scope:enemy_country` = the other side's leader, `scope:benefitted_from_wargoal` /
  `scope:victim_of_wargoal`) tell a winner from a loser and fire for capitulations; `scope:war` takes `is_warleader`
  and `war_duration_months`. Also `on_character_death`, `on_new_ruler`, `on_law_activated` (built in phase 2).
- **Space race firsts** are recorded on the achiever as `sr_was_first_<milestone>` (`space_race_effects.txt`).
- **Treaty articles** are the mod's own files (`common/treaty_articles/1xx_*.txt`: `kind`, `flags`, `possible`,
  `can_ratify`). **UN topics** are `un_topic_<key>` with `un_propose_<key>_*` buttons (`un_redesign_design.md` §0.12).
- **`is_under_construction`** (building) exists; v2 does not use it (vanity stays per level finished).

## 1. Numbers (phase 1)

| Quantity | v1 | v2 | Where |
|---|---|---|---|
| Construction per level | 10,000 | **1,000** | `construction_cost_grand_monument` (rewrite the construction-sink comment above it) |
| Vanity: radicals in the state, per level finished in hard times | 5% of pops | **0.5%** | `gm_state_vanity_backlash` (`add_radicals_in_state = { value = 0.005 }`) |
| Vanity: legitimacy per unit of `gm_vanity_ledger` | −3 | **−1** (first −0.3, which rendered as "−0") | `gm_step_vanity` and its static modifier (the registry test pins the pair) |
| Rededicate | 5,000 a level | **500 a level** | `gm_state_rededicate_cost` |
| Curve, step values, ledgers | — | unchanged | |

What the curve now costs:

| Steps complete | Grandeur (f = 5) | v1 construction | v2 construction |
|---|---|---|---|
| 1 | 5 | 50k | 5k (two base-game monuments) |
| 3 | 35 | 350k | 35k |
| 5 | 155 | 1.55M | 155k |
| 8 (flat) | 1,275 | 12.75M | 1.275M |

The fifth step alone still takes 80 levels against the first step's 5, so the curve keeps spam from paying.

**Wide gets cheap.** A level-5 monument in each of 30 states falls from 150k to 15k and gives each state a full local
step. National totals are unchanged (they sum grandeur), so the question is the local values alone. They stay as they
are for phase 1 and are checked in an observer run with the debug event. The candidates to cut if wide proves too strong
are Botanical Gardens (−5,000 pollution a step), the Grand Stadium (−10% turmoil effects) and the War Memorial (+0.05
conscription). The fixed caretaker staff (250 a monument, `unscaled`) is the brake already built in.

**Tall gets taller.** The rebuild ladder (`te_construction_market_build_specified_level`) runs to 200, so Rededicate
halves exactly up to level 400 and caps above it, as now. If observer runs show monuments past 400, extend the ladder.

## 2. Commissions (phase 2)

### 2.1 What a commission is

A request from an interest group to raise a monument. One record per country, held in country variables:

| Field | Variable | Notes |
|---|---|---|
| Source | `gm_com_source` (flag) | §2.2 |
| Petitioner | `gm_com_ig` (flag: the IG type) | resolved through a dispatcher, never stored as an IG scope |
| Dedication | `gm_com_dedication` (flag) | one of v1's twelve |
| Where | `gm_com_state` (state) or none | a fixed state (historical commissions, a raise of a named monument) or anywhere |
| Target | `gm_com_target` | grandeur to add; 5 (one step) unless the source says otherwise |
| Baseline | `gm_com_baseline` | the counted grandeur on acceptance |
| Time left | `gm_com_months_left` | counted down by the country pulse; the JE shows it |
| Namesake, form | `gm_com_namesake`, `gm_com_form` and their records (§3) | the name the monument takes on completion |
| Extended | `gm_com_extended` | set once by the extension button |

A commission is **offered** (an event), then **open** (accepted, a row in the journal entry), then **fulfilled**,
**missed** or **lapsed**.

### 2.2 Where commissions come from

| Source | When | Petitioner | Dedication | Where | Namesake offered first |
|---|---|---|---|---|---|
| Victory | a war leader ends a war having enforced a war goal, after at least a year of war | Armed Forces | War Memorial | anywhere | the occasion: "Arch of the [enemy] War" (falls back to the year) |
| Defeat | a war leader ends a war having had a war goal enforced against it | Armed Forces, or the strongest IG outside government if the Armed Forces are in it | War Memorial | anywhere | "To the Fallen of [year]" |
| Centenary | the 100th or 200th year after `gm_founded_year` | Petty Bourgeoisie (else the strongest IG in government) | To the Nation | the capital | "Centenary [form]" |
| A ruler's death | `on_character_death` of a ruler who reigned 15 years or more | the late ruler's IG | To the Nation (the mausoleum form) | the capital | the late ruler (falls back to the year) |
| A new regime | `on_law_activated` makes Crown, Republic or Revolution fit when no monument of it fits | the dedication's approving IG (v1 table) | that regime's dedication | anywhere | the year |
| Space first | the country becomes `sr_was_first_` on a crewed milestone (the plan names the two) | Intelligentsia | To the Nation | the capital | the achievement |
| Petition | monthly chance (§2.6) for an IG in government that approves a dedication the country can commission and that has less than 5 fitting grandeur | that IG | that dedication | anywhere | the city |
| Historical | §7 | as listed there | as listed | a fixed state | the landmark's own name |

**Founding years.** `gm_founded_year` is set in history for countries with a well-known founding before 1836 (the plan
lists them: the United States 1776, Mexico 1821, Brazil 1822, Belgium 1830 and so on), else to the year the country first
exists (game start, `on_country_formed`, release). It is a variable, so a civil war's winner keeps it.

### 2.3 Life cycle

- **Offered.** A country event names the petitioner, the occasion and the monument asked for, with its namesake. Options:
  **Accept** and **Decline**. Each option's tooltip states what it costs or promises in approval and legitimacy
  (`custom_tooltip` with the effects: the ledgers render nothing by themselves, `silent_variable_audit`).
- **Open.** A row in the journal entry's new **Commission** section: the petitioner, the monument asked for, a progress
  bar (grandeur added / target), months left, and **Ask for More Time** (once: +36 months, the reward halved, as
  vanilla's Government Petition extension).
- **Fulfilled** when progress reaches the target. The monument whose finished level completed it (`monument_events.1`
  sees the building) takes the commission's name. A fixed-state commission counts only that state's monument.
- **Missed** when time runs out first.
- **Lapsed**, with no cost, when it can no longer be done through no choice of the country's: the fixed state changes
  hands, the dedication's commission gate stops holding (a crown falls), or the system's game rule is off.

**What counts as progress:** grandeur added since acceptance to fitting monuments of the commission's dedication (in its
state, if fixed): today's counted grandeur minus `gm_com_baseline`, floored at 0. Raising an old monument counts as much
as founding a new one. While a commission is open, the dedication ceremony (`monument_events.2`) lists the commission's
dedication first and the AI's `ai_chance` picks it.

### 2.4 Rewards and costs

Every reward and cost goes through ledgers, as v1 §4.3 does, so nothing stacks:

| Outcome | Petitioner's IG ledger (`gm_ig_ledger_<ig>`, decays ×0.97 a month, through the per-IG curve) | Legitimacy |
|---|---|---|
| Fulfilled | +15 grandeur (about +2 approval) | +5 to the new `gm_promise_ledger`, decays ×0.97 a month, applied **linearly** (`gm_national_promise`, "A Promise Kept") |
| Fulfilled after an extension | +8 | +2.5 |
| Declined | −5 (about −1 approval; owner, after the build) | — |
| Missed | −15 (about −2: a broken promise costs more than a refusal) | — |
| Lapsed | — | — |

Vanilla's Government Petition pays +10 or +5 decaying legitimacy (`modifier_successfully_met_petition_legitimacy`); a
monument is a smaller promise. A linear ledger is safe here because only one commission is ever open.

### 2.5 Pacing

- At most one commission open or on offer at a time.
- World moments (victory, defeat, centenary, a ruler's death, a new regime, a space first) are offered when they happen
  if nothing is open; otherwise they are dropped, not queued.
- Petitions: a monthly chance of 1/120 while an IG is eligible (about one a decade), and none for 60 months after any
  commission closes.
- Historical commissions (§7) ignore the cooldown but not the one-at-a-time cap; one blocked by an open commission is
  offered when it closes, while its window lasts.

### 2.6 The AI

- **Accepts** (the offer event's `ai_chance`) when not at war, not in hard times (`gm_country_hard_times`), with the
  government construction queue under a year (`construction_queue_government_duration`) and a treasury that is not in
  debt; otherwise declines.
- **On accepting,** it queues the target's levels with `start_building_construction = building_grand_monument` in the
  commission's state, or else in the first of: a state already holding a fitting monument of the dedication, the
  capital if it has none, the most populous incorporated state without one.
- **Extends** when progress is past half and time is short; never otherwise.
- The ceremony's `ai_chance` takes the commission's dedication (§2.3).

The plan verifies in an observer run that AI monuments now appear and are finished, which v1's `ai_value` never managed.

### 2.7 The journal entry

- `is_shown_when_inactive` / `possible`: owns a Grand Monument **or** has a commission on offer or open (and, from phase
  5, holds a trophy or has one held abroad). `invalid` adds "no commission" to its existing conditions.
  `gm_entry_unlocked` gains the same clause, so the Timeline Extended window's tab unlocks too.
- A **Commission** section between the overview and National Effects, shown while one is open. National Effects gains
  "A Promise Kept" while its ledger is in force.
- Everything else as v1 (`grand_monuments_widget.gui`, the layout test).

## 3. Names (phase 2, with commissions)

### 3.1 Namesake and form

A monument's name is a **namesake** and a **form**: "Nelson's Column", "the Arch of 1856", "the Lisbon Gate".

| Namesake | Pattern | Records on the state | Offered |
|---|---|---|---|
| City | "the [city] [form]" | none: the state's city hub, as the map names it (a player's rename of the city doesn't show, engine facts) | always |
| State | "the [state] [form]" | none | always |
| Ruler | "[ruler]'s [form]" | `gm_name_char` (the ruler at the naming) | always |
| What it honours | "[form] of the Crown / Republic / Revolution / Nation", "[form] of the Faith" | none (the dedication) | always |
| Year | "the [form] of [year]" | `gm_name_year` | always |
| Occasion | "Arch of the [enemy] War", "Centenary [form]", "[achievement] Monument" | `gm_name_year`, `gm_name_country` (or its capital state, see engine facts) | from a commission |
| Landmark | the landmark's own name ("Arc de Triomphe") | the skin `landmark_<key>` | from history or a historical commission |
| Custom | the player's own text | `gm_name` (a flag made from the typed text) | players only, from the JE row (§3.5) |

Records: `gm_namesake` (flag) and `gm_form` (flag) on the state, beside v1's `gm_skin`. A customizable localization,
`gm_monument_name`, switches on the pair; a state with `gm_name` prints that instead. The typed name sits on top of
namesake and form, which stay set underneath: clearing it brings them back, and the AI, history and commissions never
write it. The name replaces the skin's generic title wherever v1 names a monument: the
JE row, the ceremony and anniversary events, contest notices, trophy rows.

### 3.2 Forms

The **skin** is the style and the art, the **form** is the noun. Each skin offers its forms; art follows the skin
only, so forms add no art.

| Skins | Forms offered |
|---|---|
| Generic (neoclassical) | column, arch, obelisk, statue, gate, hall, tower, memorial; mausoleum (ruler's death, historical) |
| Latin | column, arch, forum |
| Greek | pantheon, stoa, column |
| Hebrew | gate, court, pillar |
| Sanskrit | pillar, gate |
| Ge'ez | stele |
| Slavonic | memorial church, column |
| Avestan | gate, hall |
| Arabic | hall, gate |
| Chinese | hall, gate, pagoda |
| Irish | round tower, high cross |
| Nahuatl, Mayan | pyramid |
| Norse | rune stone, hall |
| Gothic | hall of fame, tower |
| Prussian | hill shrine |
| Aramaic | rock-cut monument |
| Faith skins | one each: the skin's own building (basilica, great mosque, great temple, pagoda, …) |
| Landmarks | fixed by the landmark |

The table is a first draft; the plan fixes it with the loc.

### 3.3 When a monument is named

- **The unveiling.** v1's skin follow-up (`monument_events.11`) becomes one event that sets skin, form and namesake. It
  still fires only for a newly dedicated monument, and asks only what has more than one fitting answer.
- **Commissions** arrive with namesake and form filled in. The unveiling shows them first, and the player can change
  them.
- **The AI** takes the commission's name, else the most specific skin, its first form and the city.
- **Rename** from the monument's JE row, at any time, at no cost: choose namesake and form again, or type a name in the
  base game's rename box (§3.5). The unveiling can't open that box (it is an event), so it mentions the row.
  Rededication asks again. A contested, heritage or trophy monument keeps its name.

### 3.4 Checks

- A stored ruler still prints its name after death (`gm_name_char`). If not, the ruler namesake prints the year.
- A stored country prints its name; else the occasion falls back to the year, or uses the capital-state workaround.
- The city hub's name renders in loc from a state scope. It is the map's name: check that `GetCityHubName` ignores a
  player's rename as `GetForestryHubName` does.
- **Typed names** were tested in game on 2026-10-05; §3.5 has the result, and what is still to check.

### 3.5 Typed names: the company carrier

Tested in game on 2026-10-05 (1.14.5), over a day of prototype builds. A mod's own editbox can't hand its text to script,
but the base game's company-rename popup can: it stores the typed name on the company, and
`Company.GetNameNoFormatting` returns it as a `CString`, which `MakeScopeFlag` takes. So a naming borrows a placeholder
company for the few seconds it takes. The other carriers tried, and why they fail, are in `gui_modding_guide.md`
§ "Typed text into script"; the engine facts behind them are in `scripting_best_practices.md` § "Player-Typed Names".

**What the player does.** Typing is offered from the JE row only, because the popup must be opened from the GUI; the
unveiling (§3.3) can say so.

1. **Name It** on the monument's row. The game's "Change name" box opens on the placeholder company.
2. Type the name and confirm. The monument's title changes and the placeholder company is gone.
3. Closing the box without confirming leaves the naming open; the row then shows the name so far with **Rename**
   (reopen the box), **Use This Name** and **Cancel**.

**The cost.** `add_company` lands at once, but the slot modifier that pays for the company lands at the next modifier
update. So for a moment at the start a country at its limit is over it ("Above Company Limit"), and at the end it has a
spare slot ("We have only established X/Y"). Adding the slot first only swaps the alerts, and no company type is exempt
from the limit. The owner accepted this on 2026-10-05.

**What ran and what is specified.** Build 4 ran the company route end to end with a second click (**Use This Name**);
build 7 ran the one-click watcher with a state as the carrier. The two together, as written here, have not been
launched. Build numbers are the prototype's test rounds, one commit each on the reference branch
`proto/gm-typed-name` (not for merging): build 4 is `ab1cde32`, 4.1 `aa3f9b34` (the company route as it ran) and 7
`5a05cc5f` (the watcher).

| Step | Status |
|---|---|
| `add_company` and the slot modifier from a scripted GUI; `company:<type>` resolving in the same effect | ran (build 4) |
| `PopupManager.ShowCompanyChangeName( ….Var('gm_name_carrier').GetCompany.Self )` from the JE row; Confirm renames it | ran (build 4) |
| Opening the popup from a `_show` state once the company exists (in the same click it opens on nothing) | ran (build 4.1) |
| `MakeScopeFlag( Company.GetNameNoFormatting )` → the state's `gm_name` → the row's title; survives save and reload | ran (build 4) |
| Cancel removes the company and the slot | ran (build 4) |
| The `trigger_when` watcher taking the name without a second click | ran with a state carrier (build 7) |
| Storing the starting name on the country from `_show` (`gm_name_mark_old_sgui`) | specified (build 9 tried it on an army, which holds no variables) |
| The monthly sweep of an abandoned naming | specified |

**Files.** Script names as in the prototype; the prototype kept them in their own files.

```
# common/company_types/: on screen only while a naming is open, never by the AI
company_gm_name_carrier = {
	icon = "gfx/interface/icons/company_icons/basic_construction.dds"
	background = "gfx/interface/icons/company_icons/company_backgrounds/comp_illu_manufacturing_light.dds"
	category = bureaucrat_owned
	flavored_company = no
	uses_dynamic_naming = no
	building_types = { building_gm_name_carrier_anchor }	# every company type lists one
	potential = { has_variable = gm_naming_active }
	attainable = { always = yes }
	possible = { always = yes }
	prosperity_modifier = { }
	ai_will_do = { always = no }
}

# common/buildings/ (+ pmg_gm_name_carrier_anchor, pm_gm_name_carrier_anchor with only a texture): never built
building_gm_name_carrier_anchor = {
	building_group = bg_grand_monuments
	icon = "gfx/interface/icons/building_icons/building_grand_monument.dds"
	city_type = city
	levels_per_mesh = -1
	buildable = no
	expandable = no
	downsizeable = no
	production_method_groups = { pmg_gm_name_carrier_anchor }
}

# common/static_modifiers/
gm_name_carrier_slot = {
	icon = "gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds"
	country_max_companies_add = 1
}
```

Once released, keep the anchor building type: a save made with it lists the type, and loading that save without it
logs `Failed to read key reference: building_gm_name_carrier_anchor` (seen after build 5 removed it).

Scripted GUIs, country scope, each with `ai_is_valid = { always = no }`:

- **`gm_name_start_sgui`** (saved scope `gm_state`; valid while `scope:gm_state` is ours and no naming is open,
  `NOT = { has_variable = gm_name_carrier }`). The order matters:

  ```
  scope:gm_state = { set_variable = gm_being_named }
  set_variable = gm_naming_active			# before add_company: the type's potential reads it
  set_variable = { name = gm_naming_open days = 30 }	# the monthly sweep's clock
  add_modifier = { name = gm_name_carrier_slot }
  add_company = company_type:company_gm_name_carrier
  capital = { state_region = { save_scope_as = gm_name_carrier_hq } }
  company:company_gm_name_carrier = { set_company_state_region = scope:gm_name_carrier_hq }
  set_variable = { name = gm_name_carrier value = company:company_gm_name_carrier }
  ```

- **`gm_name_mark_old_sgui`** (saved scope `gm_old_name`): `set_variable = { name = gm_name_old value =
  scope:gm_old_name }` on the country. Not on the company: whether companies hold variables is untested.
- **`gm_name_use_sgui`** (saved scopes `gm_state`, `gm_name`). The watcher can send it twice before the first has
  landed, so the effect repeats the validity check: inside `if = { limit = { scope:gm_state = { has_variable =
  gm_being_named } } }` it sets the state's `gm_name` to `scope:gm_name`, then `gm_name_carrier_close`.
- **`gm_name_cancel_sgui`**: `gm_name_carrier_close`.
- **`gm_name_carrier_close`** (scripted effect): `remove_company` and `remove_modifier` (each behind its `has_` check),
  then remove `gm_name_carrier`, `gm_naming_active`, `gm_naming_open`, `gm_name_old` and every state's
  `gm_being_named`.
- **The monthly sweep**, in `gm_country_monthly`: a naming whose `gm_naming_open` has expired is abandoned (the box was
  closed and the row left), so `gm_name_carrier_close`. Closing the company popup itself can't cancel the naming: it is
  vanilla's `companies_panel.gui`, which the mod doesn't override.

A state script value `gm_is_being_named` (1 while `gm_being_named`, else 0) switches the row, and a country value
`gm_has_name_old` (1 while `gm_name_old`) holds the watcher until the starting name is stored.

The JE row (`gm_monument_row`), with `C` = `JournalEntry.GetCountry.MakeScope.Var('gm_name_carrier').GetCompany` and
`ROOT` = `GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope )`:

- Mode 0 (`gm_is_being_named` 0): **Name It** (`gm_name_start_sgui`, `gm_state` = `State.MakeScope`) and **Clear
  Name**.
- Mode 1: a container whose `visible` is mode 1 and which holds:

  ```
  state = {
  	name = _show
  	on_start = "[GetScriptedGui('gm_name_mark_old_sgui').Execute( ROOT.AddScope( 'gm_old_name', MakeScopeFlag( C.GetNameNoFormatting ) ).End )]"
  	on_start = "[PopupManager.ShowCompanyChangeName( C.Self )]"
  }
  widget = {
  	size = { 1 1 }
  	state = {
  		trigger_when = "[And( EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_has_name_old'), '(CFixedPoint)1' ), Not( EqualTo_string( C.GetNameNoFormatting, JournalEntry.GetCountry.MakeScope.Var('gm_name_old').GetFlagName ) ) )]"
  		on_finish = "[GetScriptedGui('gm_name_use_sgui').Execute( ROOT.AddScope( 'gm_state', State.MakeScope ).AddScope( 'gm_name', MakeScopeFlag( C.GetNameNoFormatting ) ).End )]"
  	}
  }
  ```

  then "New name: `[C.GetNameNoFormatting]`" and **Rename** (`ShowCompanyChangeName`), **Use This Name** (the
  watcher's `on_finish` as an `onclick`) and **Cancel** (`gm_name_cancel_sgui`). Every read of
  `Var('gm_name_carrier')` sits in mode 1, where the start has set it.
- The title: a second textbox on `gm_row_title_named` (`"#b [State.MakeScope.Var('gm_name').GetFlagName]#! — …"`),
  the two toggled on a state value for `has_variable = gm_name`. A `Var(…).IsSet` check is untested; a script value is
  the proven idiom.

Loc: the company's default name (`company_gm_name_carrier`, shown in the box when it opens), the anchor building, its
group and method, the slot modifier, the row's labels and tooltips, and `gm_name_one_at_a_time_tt`.

**Still to check when this is built**, beyond the table:

- The default name. The box opens on it. A blank value would start the box empty, but whether an empty loc value gives
  an empty company name or the raw key is untested; "Unnamed Monument" worked.
- The name through `gm_monument_name` (customizable localization) and in event loc: `GetFlagName` has only run in the
  row.
- A `"`, `#b` or `[` in a name, through the save and through `GetFlagName`.
- Multiplayer: the rename and the scripted GUIs are commands; the watcher runs on the naming player's client.

## 4. Monuments standing in 1836 (phase 4)

Placed in `common/history/extra_history.txt` (or a new `common/history/grand_monuments_history.txt` if the order
allows), each with its dedication PM, `gm_raised_by` = its owner, `gm_seen`, a landmark skin and the landmark namesake:

| Landmark (`landmark_<key>`) | State | Owner | Dedication | Level | Note |
|---|---|---|---|---|---|
| Arc de Triomphe (`arc_de_triomphe`) | `STATE_ILE_DE_FRANCE` | FRA | War Memorial | 10 | opened July 1836 |
| Alexander Column (`alexander_column`) | `STATE_INGRIA` | RUS | To the Crown | 10 | contested if Russia loses its crown |
| Brandenburg Gate (`brandenburg_gate`) | `STATE_BRANDENBURG` | PRU | To the Nation | 10 | its Quadriga was carried to Paris in 1806 and back in 1814 |
| Washington Monument, Baltimore (`washington_monument_baltimore`) | `STATE_MARYLAND` | USA | To the Republic | 5 | completed 1829 |

- **Owners activate the journal entry from day one**, and each is an AI monument a player can meet, conquer or watch
  being contested.
- **`LANDMARKS`** in `test_grand_monument_registry.py` gets these four (each a skin flag, a `monument_events.11` option
  whose trigger names its state, the loc `gm_skin_landmark_<key>`, reused art viewed on a contact sheet first).
- **Duplicates checked:** none of these, nor §7's, is a base-game wonder (Big Ben, the White House, St Basil's, the
  Kaiserforum and the rest) or one of the mod's 37 `building_wonder_*`.
- **One per state:** London and Paris each hold one Grand Monument, so Wellington Arch and the July Column are left
  out (London waits for Nelson's Column, §7).

## 5. Monument policy (phase 3)

One national policy, set from the journal entry by three buttons (a fourth state, **Standard**, is the default and has
no effect). A country variable, `gm_policy` (flag), so a civil war's winner keeps it. After a change, no other change for
60 months (`gm_policy_cooldown`); the first choice is free.

| Policy | Gives | Costs |
|---|---|---|
| **Open to the Public** | local Tourism Industry throughput ×1.5 per step; anniversary events twice as likely | monuments' upkeep ×1.5 |
| **State Ceremonial** | regime grandeur counts ×1.5 toward legitimacy and the Leader's authority | local tourism ×0.5 |
| **Mothballed** | monuments' upkeep ×0.5 | prestige (standing) ×0.5; local effects ×0.5; no anniversaries |

- **How:** the factors multiply the per-step values in `gm_compute_totals` and `gm_state_monthly` through one
  `gm_policy_factor_*` script value each. Upkeep moves through `gm_policy_upkeep_open` / `_mothballed`
  (`goods_input_construction_mult` ±0.5) on each monument building, refreshed by the state pulse; throughput would not
  have moved it (engine facts).
- **AI:** Mothballed in hard times or with a negative treasury; State Ceremonial with legitimacy under 40 and regime
  grandeur above 0; Open to the Public when a monument stands in a state with a Tourism Industry; else Standard.
  Re-evaluated yearly; the cooldown applies to the AI as well.
- **Display:** the policy's name and factors on a line under the overview; the buttons in National Effects.

## 6. Trophies (phase 5)

### 6.1 Which monuments

Portable ones: **To the Crown, the Republic, the Revolution, the Leader, the Nation and the War Memorial** (columns,
arches, statues, steles). **Never a Grand Shrine** (v1's line: a conquered shrine becomes heritage). Not the Opera,
Gardens, Observatory, Exhibition Hall or Stadium: they are buildings, not objects.

### 6.2 Carry It Home

- **When:** a state with a portable monument changes hands by conquest (v1 §4.1's test: not a civil war), and for 60
  months after (`gm_taken_from`, a timed state variable). The conquest notice (`monument_events.16`/`.17`) adds the
  choice, beside Pull Down, Rededicate and Keep as Heritage. For a timeless monument, which v1 never contests, the notice
  offers Carry It Home or leaving it as it is.
- **What happens:** the building is removed (its state records cleared, as Pull Down does). The state's pops take
  radicals (10% of pops, once). A **trophy** is created: a freestanding script container tagged `gm_trophy` with its
  origin country and state, dedication, skin, name records, **half its grandeur rounded up**, and its **site**, the
  holder's capital at the time.
- **The former owner:** `change_relations` −30 with the holder.

### 6.3 What a trophy does

- **The holder** is whoever owns the site, read live. Annexation, a civil war or the capture of the site moves it with no
  special case. A third country that takes the site takes the trophy, as the Quadriga changed hands.
- **For the holder,** its grandeur counts toward standing grandeur (prestige, cultural pull) and positive in the Armed
  Forces' per-IG total, through the same curves. A row under **Trophies** in the JE names it, its origin and the ways
  home.
- **For the origin country,** a row under **Held Abroad** in its JE. While it holds such a row the journal entry stays
  active.
- **One global monthly pass** (`every_container` with `gm_trophy`) writes each holder's trophy grandeur and each origin's
  held-abroad count into country variables, which the country pulses read. No per-country scan.

### 6.4 Ways home

| Way | How | Effects |
|---|---|---|
| **Return it** | the holder's button on the trophy row | the trophy is rebuilt at home (§6.5); relations +40 with the origin; the holder loses its grandeur |
| **Treaty article** | `return_cultural_property`, a new directed article: the giver returns every trophy whose origin is the receiver | as Return it. Whether an article can be a peace term is a plan check; Axum's return was written into the 1947 peace treaty |
| **UN** | a topic, `un_topic_cultural_property`, accusing a holder; designed with the UN's own topic table when phase 5 is planned | as Return it, on compliance |
| **Retake the site** | the origin country (or whoever holds the origin state) takes the site | an event **offers** to bring it home or leave it standing as a trophy of its own, a choice as decided |

### 6.5 Rebuilding at home

The trophy is rebuilt in its origin state, if the receiving country holds it, at the trophy's grandeur, with its
dedication, skin and name, through the rebuild ladder; the ceremony does not run. If a monument already stands there, the
trophy's grandeur is added to it (whether `create_building` adds levels to an existing building is a check; the fallback
is a rebuild at the combined level keeping the standing monument's dedication). If the receiver does not hold the origin
state, it keeps the trophy as its own until it does, then the row offers the return.

### 6.6 The AI

Carries home a portable monument it conquers when the Armed Forces are in government or the monument is tall (10+),
otherwise follows v1 §4.6. Returns a trophy when relations with the origin matter to it (an ally, a power bloc partner)
or the UN asks. Brings home what it retakes.

## 7. Historical commissions (phase 6)

Hand-written commissions (§2) for whoever holds the state, offered from their year while the conditions hold, for up to 40
years, **once per game** (a global variable per landmark). Each has a fixed state, its landmark's name, skin and target
level, and fills a `LANDMARKS` row.

| Landmark | From | State | Dedication | Target | Condition |
|---|---|---|---|---|---|
| Nelson's Column | 1840 | `STATE_HOME_COUNTIES` | War Memorial | 5 | |
| Walhalla | 1842 | `STATE_BAVARIA` | To the Nation | 5 | |
| Bunker Hill Monument | 1843 | `STATE_MASSACHUSETTS` | War Memorial | 5 | |
| Washington Monument | 1848 | `STATE_DISTRICT_OF_COLUMBIA` | To the Republic | 10 | |
| Hermannsdenkmal | 1875 | Lippe's state (`STATE_WESTPHALIA`, to confirm) | To the Nation | 5 | Germany formed |
| Vittoriano | 1885 | `STATE_LAZIO` | To the Crown | 10 | Italy formed and crowned; a later republic keeping it as heritage is what happened in 1946 |
| Angel of Independence | 1910 | `STATE_MEXICO` | To the Nation | 5 | |
| Völkerschlachtdenkmal | 1913 | `STATE_SAXONY` | War Memorial | 10 | |
| Lenin's Mausoleum | 1924 | `STATE_MOSCOW` | To the Revolution | 5 | Council Republic or Single-Party State |
| Sun Yat-sen Mausoleum | 1929 | `STATE_NANJING` | To the Republic | 5 | |
| India Gate | 1931 | `STATE_DELHI` | War Memorial | 5 | |
| Anıtkabir | 1953 | `STATE_ANKARA` | To the Republic | 5 | |
| Monument to the People's Heroes | 1958 | `STATE_BEIJING` | To the Revolution | 5 | Council Republic |

- **One per state.** A historical commission is offered only if its state has no monument or one of the same dedication,
  which it then raises and renames. That is why the July Column, the Monument to the Conquerors of Space and Mexico
  City's Monument to the Revolution are not listed.
- **Left out on purpose:** monuments whose main meaning today is an atrocity or a live grievance (the Valley of the
  Fallen, Yasukuni).
- **v1's Shahyad landmark is dropped:** the mod already has the Azadi Tower (`building_wonder_azadi_tower`).
- v1's other phase-2 landmark candidates (a Hall of Dynasties in a Chinese monarchy's capital, a new Stele of Aksum,
  Mexico City's Monument to the Revolution) are not historical commissions; they can be added later as landmark skins
  offered by the unveiling event.

## 8. Numbers — first estimates

| Quantity | Value | Anchor |
|---|---|---|
| Construction per level | 1,000 | §1 |
| Vanity | 0.5% radicals a level; −0.3 legitimacy per ledger unit | v1 ÷ 10 |
| Rededicate | 500 a level | v1 ÷ 10 |
| Commission target | 5 grandeur (one step); historical: the landmark's level | |
| Commission time | 60 months; extension +36, once | vanilla Government Petition |
| Fulfilled | IG ledger +15; promise ledger +5 (decays ×0.97) | vanilla petition +10 / +5 legitimacy |
| Fulfilled after extension | +8; +2.5 | half, as vanilla |
| Declined / missed | IG ledger −10 / −5 | |
| Petition chance | 1/120 a month while eligible; 60-month cooldown | about one a decade |
| Policy factors | ×1.5 / ×0.5; upkeep via throughput ±0.5 | |
| Policy cooldown | 60 months | |
| 1836 monuments | levels 10, 10, 10, 5 | |
| Trophy | half grandeur, rounded up; radicals 10% once; relations −30, return +40 | Rededicate's half |
| Trophy window | 60 months after the conquest | |
| Historical window | 40 years from its year | |

Checked in observer runs with the debug event (§9).

## 9. Tests, docs, in-game checks

- **`test_grand_monument_registry.py`** grows a table per new list, each the checklist for adding a row:
  `COMMISSION_SOURCES` (source, trigger, petitioner, dedication, namesake, offer event, loc), `NAMESAKES` (pattern,
  records, loc), `FORMS` (form, skins, loc), `POLICIES` (button, factors, AI rule, loc), `TROPHY_DEDICATIONS` (the six,
  and that the Shrine is not one), `HISTORY_SEEDS` (§4), and `LANDMARKS` (§4 and §7: state, dedication, level, year,
  condition, skin, loc, art). Plus: the §1 values; the ledgers' decay; that every new ledger is in `gm_ledgers_idle`.
- **Debug** (`te_debug_monuments`): offer each commission source; fulfil, miss or lapse the open one; set the policy;
  create, move and return a trophy; print commission state, policy and trophies on `TE_MONUMENTS:` lines.
- **Audits** that cover the new script: `je_immediate_reset` (no commission state written in an unguarded `immediate`),
  `silent_variable` (the offer's and buttons' tooltips), `event_image`, `event_context`, `empty_effect`,
  `script_argument`, `loc_coverage`, `container_timed_variable` (trophy containers carry no timed variables).
- **Docs, per phase:** `mod_systems.md` § Grand Monuments; the player guide's `02-timeline.md` § Grand monuments (the
  10,000 figure, vanity's 5% and −3, Rededicate's 5,000, then a subsection per new system) and `17-reference.md`; rebuild
  the PDF. Lessons into `scripting_best_practices.md`.
- **In-game checklist** (each phase's PR body carries its part):
  1. A level costs 1,000; vanity lands at the new size, only in hard times.
  2. Each commission source fires once, at the right moment, with the right petitioner and name; the scopes the war
     on-actions carry tell a victory from a defeat.
  3. The AI accepts, queues construction with `start_building_construction`, and the levels are built, not cancelled; the
     government form adds a level to an existing monument.
  4. Progress, extension, fulfilment, a miss and a lapse each do what their tooltips say.
  5. The unveiling sets skin, form and namesake; the name shows in the JE row, events and notices; renaming works; a
     typed name survives a save and reload (§3.5).
  6. A ruler's name still prints after the ruler dies; the City namesake prints the map's city name.
  7. The four 1836 monuments stand at start with their names and dedications; their owners' journal entries are active.
  8. The policy's factors show in the totals; throughput moves the monuments' upkeep.
  9. Carry It Home removes the monument and creates the trophy; the trophy counts for the holder; annexation and capture
     of the site move it; each way home rebuilds it.
  10. A historical commission fires for whoever holds its state, once per game, and not while another is open.

## 10. Phasing

Each phase is its own PR, except phases 1–3, which the owner asked for as one (2026-10-05; plan
`docs/superpowers/plans/2026-10-05-grand-monuments-v2-phases-1-3.md`).

| Phase | Content | Needs |
|---|---|---|
| 1 | §1 numbers | — |
| 2 | §2 commissions and §3 names (commissions supply names) | 1 |
| 3 | §5 policy | 1 |
| 4 | §4 monuments standing in 1836 | 2 (their names) |
| 5 | §6 trophies | 2 (names on trophy rows) |
| 6 | §7 historical commissions | 2, 4 (`LANDMARKS`) |

## Out of scope (possible extensions)

- **A monument as a gift** between countries (the Luxor Obelisk was Muhammad Ali's gift to France, raised in 1836).
- From v1's list, still out: a covert defacement operation; prestige lost while a monument's state is occupied;
  superlinear upkeep; a state-panel tile; skins with effects; base-game wonders and the mod's megaprojects in the legacy
  mechanic.
- Art per form.
