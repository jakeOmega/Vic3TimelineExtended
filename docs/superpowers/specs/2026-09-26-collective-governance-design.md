# Collective Governance: generalizing Direct Democracy — design

## Context

`law_direct_democracy` (`common/laws/extra_laws.txt`) is a mod governance principle. Today it requires one of the four
voting laws or Single-Party State, unlocks with `mass_media` (era 6), and carries a referendum package: laws need a
movement behind them, movements draw more support, and so on. Three government types dress it
(`common/government_types/timeline_extended_governments.txt`).

The owner wants a broader principle: a **headless** government, where no individual holds supreme executive power. Under
a voting law that is still a direct democracy. Under Technocracy it is a set of peer bureaus with no chief executive,
under Anarchy a federation of communes, under Oligarchy a council of peers. Autocracy contradicts it.

The design test: vanilla Council Republic already covers councils (`gov_anarchist_commune`, `gov_phalanstere`,
`gov_cybernetic_state`) and has a Chairman. Council Republic is defined by *who* governs (workers' delegates); this law is
defined by *the absence of a supreme executive*, whoever governs. The mechanics have to say so.

Baseline: `main` at `6ca193db` (#478 merged).

## Decisions (owner, 2026-09-26)

| Question | Decision |
|---|---|
| Engine key | **Keep `law_direct_democracy`**. Change loc, prerequisites and mechanics only. Precedent: the `fertilizer` good is displayed as "Chemicals". Renaming would break saves and touch ~50 ideology entries, two generated files, three events and two trigger files |
| Autocracy | **Not allowed** (nor its variants Bakufu and Neo-Absolutism) |
| Unitary / Federal / Devolved / Feudal | A separate axis (`lawgroup_state_power`, no prerequisites). All combine freely; the fiefdom idea is Oligarchy + Feudal Contracts and gets its own government name |
| Effects that depend on Distribution of Power | **A generic base on the law, plus one expression per Distribution of Power group** |
| How the expression is applied | **As an amendment**, attached by script (like the language reform law's amendments) |
| Which law hosts it | **The governance principle** (`law_direct_democracy`), not the Distribution of Power law |
| Enactment preview | **A `custom_tooltip` in the law's `on_enact`**, as `law_state_led_language_reform` does, naming the amendment the current Distribution of Power will give |
| Name | **Collective Governance** |
| Tech gate | **`mass_media` (era 6) → `political_agitation` (era 4).** `democracy` (era 1) was proposed and rejected as too early. `political_agitation` is the mass-politics tech: it already unlocks Single-Party State, and it suits the movement-driven Direct Democracy and Free Federation amendments. Anarchy (era 3) waits one era, Technocracy (era 2) two; Direct Democracy arrives two eras earlier than today. The gate stays in `unlocking_technologies`, because `gen_law_consistency` reads that field and not `can_enact` |
| Algorithmic Governance | **Not a prerequisite** (unchanged from today); follow-up if wanted. **Added 2026-09-27** as a sixth expression, *Algorithmic Commons* (see the note at the end) |
| Ideology stances | **The §6 table** (10 changes) |
| Government and ruler names | **The §4 table** |
| Base effects | **The §1 starting values**; the plan checks defines before fixing them |

## Engine facts this rests on

Verified from script, vanilla files and the engine docs:
- Government types have only `transfer_of_power`, `possible`, ruler/heir titles, `new_leader_on_reform_government` and
  the two `on_*government_type_change` hooks. **No modifiers** (all 444 vanilla types checked).
- **Single-Party State grants `country_voting_power_base_add = 50`**, so `country_has_voting_franchise = yes` under it.
  Technocracy, Oligarchy, Organic Regulation and Anarchy grant no voting power. So today's
  `gov_direct_democracy_autocracy` (`franchise = no`) can never trigger, but once the prerequisites widen it would match
  every new combination: a Lord Protector with dictatorial succession. **It must go.**
- Only niche vanilla government types match without a governance-principle law: chartered companies, domain alliances,
  monarchy-only regencies, the Peru–Bolivia confederation journal. They override every principle already. Vanilla files
  load before ours.
- Government-type selection appears to be **first match in load order** (vanilla puts `gov_papal_commune` first in
  `05_council_republics.txt` because `gov_soviet_republic` would also match).
- Variant laws must be listed explicitly in `unlocking_laws` (vanilla `00_economic_system.txt` lists
  `law_organic_regulation` beside `law_oligarchy`). `law_elder_council` requires `law_chiefdom`, so it can never pair.
- Amendments: `add_amendment = { type sponsor cooldown }` (law scope), `remove_amendment` (amendment scope; "without
  checking cooldown"), `has_amendment` and `amendment_count` (law), `every_scope_amendment`, an amendment's `.type`,
  `active_law:lawgroup_X`. An amendment's modifiers "will be added to the modifiers of the law it is attached to"
  (vanilla `amendments.md`), so they show on the active law's tooltip. No amendment cap in defines or GUI.
- A law's amendments go with it when the law is replaced (vanilla `amendment_geheime_staatskonferenz`: "this can be
  removed by changing Distribution of Power").
- A law's `on_enact` is where vanilla puts preview-only text, with conditions read against the laws in force before
  enactment (the land-reform laws' `farmers_pb_ig_shift_effect_*_tt`; `law_state_led_language_reform`'s `custom_tooltip`).
  `on_activate` also renders in the preview, so anything there that should not show goes in `hidden_effect`.
- **Amendments need a sponsor** (vanilla `land_ownership_law_events.txt`: "amendments need a sponsor"). Vanilla removes one
  by type with `random_scope_amendment = { limit = { amendment_type:X ?= this.type } remove_amendment = yes }`
  (`ep2_tenpo_events.txt`).
- Vanilla's collective-executive precedent: `amendment_geheime_staatskonferenz` (Austria's Secret State Conference) —
  `country_legitimacy_govt_size_add = 1`, `country_authority_mult = -0.25`, enactment speed −0.20, success −0.10.

**Not verified, and designed to work either way** (the first in-game checks, §8):
1. Whether script `remove_amendment` respects `can_repeal`. `can_repeal` is true exactly when the refresh wants the
   amendment gone, so the swap works in both cases.
2. ~~Whether `add_amendment` respects `possible`.~~ Answered: it does; a false `possible` silently skips the add
   (`scripting_best_practices.md` § "`add_amendment` Requirements"). The script only adds the amendment whose `possible`
   holds.
3. Whether the engine drops an amendment by itself when `possible` turns false. The refresh removes it either way.
4. What happens when there is no ruler to supply the sponsor. The refresh skips the add until the next call.
5. Whether `on_activate` sees the law as active (`active_law:lawgroup_governance_principles`). If not,
   `on_law_activated` attaches the amendment on the same day.
6. ~~Whether a law switched by `activate_law` (the consistency cascade) fires `on_law_activated`.~~ Answered: it does
   (vanilla `00_code_on_actions.txt`: "if a law is directly set by script … this will execute"). The monthly pulse stays
   as a backstop and save migration.
7. Whether `amendment_type:X ?= this.type` (vanilla's form) works inside a parameterized scripted effect.
8. What the engine does on a repeal. `on_amendment_repealed` has an empty script handler in vanilla and none in the mod,
   but the engine itself may notify the player or touch the sponsor's approval. Every Distribution of Power change
   repeals one of ours, so watch for a notification or an approval hit on the chair's interest group. If either appears,
   pick a neutral sponsor or suppress it with a named sub-action (the `on_amendment_timeout` pattern in
   `amendment_on_actions.txt`).

## 1. The law

`law_direct_democracy` keeps its key, icon and `progressiveness = 50`. A comment at the top of the block says that the
key is historical and the law is Collective Governance.

- **`unlocking_laws`:** `law_landed_voting`, `law_wealth_voting`, `law_census_voting`, `law_universal_suffrage`,
  `law_single_party_state` (unchanged), plus `law_technocracy`, `law_oligarchy`, `law_organic_regulation`,
  `law_anarchy`.
- **`unlocking_technologies`:** `political_agitation` (era 4; was `mass_media`, era 6).
- **`can_enact`:** the current `NOT = { has_government_type = gov_direct_democracy }` does nothing: that government type
  exists only while the law is already held. Replace it with Neocameralism's `NOT = { has_government_type = gov_chartered_company }`.
- **`modifier`** — the "no head" identity. Starting values:

  | Modifier | Value | Anchor |
  |---|---|---|
  | `country_legitimacy_govt_size_add` | 1 | Council Republic 1, Staatskonferenz 1 |
  | `country_authority_mult` | −0.15 | Staatskonferenz −0.25 (Anarchy's own −0.5 stacks, so less here) |
  | `country_law_enactment_speed_mult` | −0.10 | Staatskonferenz −0.20: consensus is slow |
  | `country_legitimacy_ideological_incoherence_mult` | −0.3 | Kept from today |

  No `country_legitimacy_headofstate_add`: the chair's interest group earns nothing, where Monarchy gives +20 and a
  Presidential Republic +10. Everything else in today's block moves to the Direct Democracy amendment (§2).

  **Balance note:** a Direct Democracy country keeps today's package (via the amendment) and gains +1 legitimacy per
  interest group in government. It loses 15% authority and 10% enactment speed. That is a small nerf, and it is
  intended: the law now claims there is no head.

  **The bigger swing is Single-Party State.** A single-party country holding the law today has the whole referendum
  package: laws need a movement, +30 legitimacy from votes, an extra agitator. After migration it has the base and
  `country_coup_resistance_mult = 0.25`, and nothing else. That follows from the design (a party presidium is not a
  referendum), but it is a large change for any save that has one.
- **`on_enact`:** one `if`/`else_if` over the five expression triggers (§3), each branch showing its
  `custom_tooltip`, then a closing line saying the amendment follows Distribution of Power.
- **`on_activate`:** `hidden_effect = { te_refresh_collective_governance_amendment = yes }`. It fires however the law
  arrives (enactment or the consistency cascade's `activate_law`), and `hidden_effect` keeps `add_amendment`'s own line
  out of the preview.
- **`ai_will_do`:** ruler has `ideology_radical` **or** `ideology_anarchist`.
- **`ai_impose_chance`:** keep the egalitarian-agenda weight. Drop the Council Republic multiplier, which was copied from
  Neocameralism and means nothing here.

Draft loc (`te_laws_l_english.yml`):
- `law_direct_democracy` "Collective Governance"
- `law_direct_democracy_desc` "No one person holds supreme executive power. Authority rests with a body of equals: an
  assembly of voters, a party presidium, a college of bureaus, a federation of communes or a council of the powerful,
  depending on who holds power. Whoever chairs it is first among equals, not a ruler."

## 2. The amendments

Five amendments in `common/amendments/extra_amendments.txt`, one per expression. Each has the same settings:
`allowed_laws = { law_direct_democracy }`, `possible = { <its trigger> = yes }`,
`can_repeal = { custom_tooltip = { text = COLLECTIVE_GOVERNANCE_TT_REPEAL NOT = { <its trigger> = yes } } }`, `would_sponsor = { always = no }`,
`ai_will_revoke = { always = no }`, `amendment_activism_multiplier = 0`. **No `parent`**: IG stance on the amendment would
otherwise count the governance law's approval a second time. If the panel misbehaves without one, fall back to
`parent = law_direct_democracy`.

| Key | Name (usually = government name; see §4) | Trigger (§3) | Effects (starting values) |
|---|---|---|---|
| `amendment_collective_direct_democracy` | Direct Democracy | popular | Today's block, moved verbatim: `country_must_have_movement_to_enact_laws_bool = yes`, `political_movement_pop_attraction_mult = 1`, `political_movement_radicalism_add = 0.5`, `political_movement_radicalism_from_enactment_approval_mult = -0.75`, `political_movement_radicalism_from_enactment_disapproval_mult = -0.75`, `country_legitimacy_govt_total_votes_add = 30`, `state_political_strength_from_wealth_mult = -0.25`, `country_law_enactment_success_add = 0.25`, `country_agitator_slots_add = 1` |
| `amendment_collective_leadership` | Collective Leadership | party | `country_coup_resistance_mult = 0.25`: no single leader for a coup to remove |
| `amendment_collective_administration` | Collegial Administration | technocratic | `country_institution_size_change_speed_mult = 0.5` (the institutions, including the mod's ministries, are the bureaus); `state_decree_cost_mult = 0.25` (no one executive to issue decrees) |
| `amendment_collective_free_federation` | Free Federation | anarchic | `country_must_have_movement_to_enact_laws_bool = yes` (delegates act only on mandates from below); `political_movement_pop_attraction_mult = 0.5` |
| `amendment_collective_patrician_council` | Patrician Council | patrician | `country_aristocrats_pol_str_mult = 0.15`, `country_capitalists_pol_str_mult = 0.15`: the powerful govern as peers |

Every modifier name is validated against `/modifier-search` before use. The plan settles final values using defines, per
the evidence-based-tuning rule.

## 3. Keeping it current

**Triggers** (`common/scripted_triggers/collective_governance_triggers.txt`, country scope). They are the single source
for every site below: amendment `possible`/`can_repeal`, the refresh, the tooltip branches, the government types and the
voting check in §5.

| Trigger | True when the country has |
|---|---|
| `collective_governance_is_popular` | `law_landed_voting`, `law_wealth_voting`, `law_census_voting` or `law_universal_suffrage` |
| `collective_governance_is_party` | `law_single_party_state` |
| `collective_governance_is_technocratic` | `law_technocracy` |
| `collective_governance_is_anarchic` | `law_anarchy` |
| `collective_governance_is_patrician` | `law_oligarchy` or `law_organic_regulation` |

**Effect** `te_refresh_collective_governance_amendment` (`common/scripted_effects/collective_governance_effects.txt`,
country scope). If the country holds `law_direct_democracy`: on `active_law:lawgroup_governance_principles`, remove each
of our five amendments whose trigger no longer holds, then add the one whose trigger holds if it is missing. The sponsor
is the ruler's interest group; with no ruler, skip the add until the next call. If the country does not hold the law,
do nothing: the amendment left with the host law.

**Call sites:**
- the law's `on_activate` (§1), hidden. Whether the new law already counts as active there is unverified (vanilla is
  mixed), which is why `on_law_activated` repeats it;
- `on_law_activated`: a new on-action `te_collective_governance_from_law_scope` (`owner = { … }`), listed after
  `te_fix_inconsistent_laws_from_law_scope` so it sees the laws after the consistency cascade. It covers a change of
  Distribution of Power while the law is held;
- `on_monthly_pulse_country`: `te_collective_governance_country_pulse`. This is the backstop for anything the other two
  miss, and it also migrates saves that already hold the law (the same pattern as `te_fix_inconsistent_laws_country_pulse`).

No `on_game_started` hook: no country holds the law at the 1836 start, and the monthly pulse migrates saves. Nothing is
stored, so a revolution's winner gets the amendment its own laws call for.

## 4. Government types

In `timeline_extended_governments.txt`, ordered most specific first, with a catch-all last. Each is keyed on
`has_law = law_type:law_direct_democracy` plus its §3 trigger. New types use `new_leader_on_reform_government = yes` and
the parliamentary-elective hooks.

| Order | Key | Matches | Name | Ruler | Transfer |
|---|---|---|---|---|---|
| 1 | `gov_collective_noble_commonwealth` (new) | patrician + `law_feudal_contracts` | Noble Commonwealth | Marshal (new `RULER_TITLE_MARSHAL`) | parliamentary_elective |
| 2 | `gov_collective_patrician_council` (new) | patrician | Patrician Council | Syndic (new `RULER_TITLE_SYNDIC`) | parliamentary_elective |
| 3 | `gov_direct_democracy_single_party_state` (key kept) | party | Collective Leadership (was "Managed Democracy") | vanilla `RULER_CHAIRMAN` / `RULER_CHAIRWOMAN` | presidential_elective (kept) |
| 4 | `gov_collective_administration` (new) | technocratic | Collegial Administration | Coordinator (new `RULER_TITLE_COORDINATOR`) | parliamentary_elective |
| 5 | `gov_collective_free_federation` (new) | anarchic | Free Federation | vanilla `RULER_REPRESENTATIVE` | parliamentary_elective |
| 6 | `gov_direct_democracy` (key kept) | popular | Direct Democracy | Speaker (existing `RULER_TITLE_SPEAKER`; was Chancellor) | parliamentary_elective (kept) |
| 7 | `gov_collective_governance` (new, catch-all) | the law alone | Collective Governance | Speaker | parliamentary_elective |

**Removed:** `gov_direct_democracy_autocracy` ("Plebiscitary Autocracy"). It can never trigger today, so no save holds it.

Each government type gets a name and a `_desc` (the existing ones are rewritten for the new meaning).
`gov_algorithmic_directorate`, later in the same file, keys only on Algorithmic Governance, which is not a prerequisite,
so it cannot compete.

## 5. Places that read the law as "a democracy"

- **`ch_set_political_model`** (`cultural_hegemony_effects.txt`). Anarchy (model 2) and Technocracy (13) are classified
  before the democracy tests, so they are already right. The **liberal-democratic branch (11, line ~374)** changes its
  `has_law_or_variant = law_type:law_direct_democracy` to
  `AND = { has_law = law_type:law_direct_democracy collective_governance_is_popular = yes }`, which keeps today's
  behaviour for voting countries and keeps a patrician council out. The **Republican branch (14)** is unchanged: an
  oligarchic council landing there is historically fair (Venice, Hamburg), and Single-Party State lands there today too.
- **`modern_election_events.33.a`** AI weight: add `collective_governance_is_popular = yes`.
- **`extra_law_events.24`, `.60`, `.84`** are all referendum-flavoured. Add `collective_governance_is_popular = yes` to
  each trigger. `.84`'s modifiers apply during enactment only, so no conversion is needed. Reword any line whose text
  reads wrongly now that the law's name renders as "Collective Governance" (`.84.d` "The direct-democracy bill
  [law name]…").
- **`monument_government_is_republican`** is unchanged: the head of state is chosen, not born to it.

## 6. Ideology stances

Changes only. Vanilla ideologies are edited in `ideology_modifications.py` (which regenerates `modified.txt`); the
custom-religion ones are edited by hand in `extra_ideologies.txt`. `gen_law_consistency` uses stances as a tiebreak; its
output changes mainly because of §1's wider prerequisites (see §8).

| Ideology | Now | Proposed | Why |
|---|---|---|---|
| `ideology_anarchist`, `ideology_anarchist_movement` | approve | strongly_approve | No head at all is the anarchist ideal |
| `ideology_bonapartist`, `ideology_bonapartist_movement` | disapprove | strongly_disapprove | Built on one man |
| `ideology_caudillismo` | disapprove | strongly_disapprove | Built on one man |
| `ideology_fascist_movement` | disapprove | strongly_disapprove | The leader principle |
| `ideology_absolutist_movement` | disapprove | strongly_disapprove | Absolute personal rule |
| `ideology_plutocratic` | disapprove | neutral | A council of the wealthy now qualifies |
| `ideology_custom_religion_aristocratic_governance` | disapprove | neutral | A council of nobles now qualifies |
| `ideology_custom_religion_technocratic_governance` | disapprove | neutral | A college of experts now qualifies |

## 7. Loc

- Law name and description: `te_laws_l_english.yml` (§1).
- Amendment names and `_desc`, government-type names and `_desc`, three new ruler titles, and the six on-enact
  tooltip keys (`COLLECTIVE_GOVERNANCE_TT_POPULAR`, `_PARTY`, `_TECHNOCRATIC`, `_ANARCHIC`, `_PATRICIAN`, and
  `COLLECTIVE_GOVERNANCE_TT_FOLLOWS_DOP`), and the repeal requirement `COLLECTIVE_GOVERNANCE_TT_REPEAL`: added to existing
  files, then `organize_loc.py`. Add `startswith` rules for any new family whose base key has 4+ tokens
  (`gov_collective_`, `amendment_collective_`) so a name and its `_desc` don't split across files.
- Tooltip style: name the mechanism in plain words; `#b X#!`, not `[b]`. Draft:
  - `COLLECTIVE_GOVERNANCE_TT_POPULAR` "With a voting franchise this becomes a #b Direct Democracy#!: a law can only be enacted with a political
    movement behind it, movements draw more support, and enacted laws radicalize their opponents less."
  - `COLLECTIVE_GOVERNANCE_TT_FOLLOWS_DOP` "The amendment changes whenever your Distribution of Power does."

## 8. Tests, docs, in-game checks

- **`test_collective_governance.py`**, in the style of `test_un_convention_registry.py`. One `EXPRESSIONS` table
  (trigger, Distribution of Power laws, amendment, government type(s), tooltip key) is checked both ways against: the
  law's `unlocking_laws`; each trigger's law list; each amendment's `allowed_laws`/`possible`/`can_repeal`; the refresh
  effect's branches; the `on_enact` tooltip branches; the government types (order, catch-all last,
  `gov_direct_democracy_autocracy` absent); and loc for every key.
- **Read the regenerated `extra_law_consistency_generated.txt` diff.** For each governance-principle cascade, note
  where it now falls into Collective Governance (nine prerequisites and an era-4 tech make it a valid replacement far
  more often), and bring that list to the owner before merging.
- `/reload` warnings clean, including `loc_coverage_audit`, `duplicate_key_audit` and `effect_trigger_validity_audit`.
- Docs: the governance-principles line in `scripting_best_practices.md` § "Lawgroup Orthogonality"; a short
  "Collective Governance" section in `docs/systems/mod_systems.md`; after the in-game checks, what we learned about
  script-attached amendments (items 1–8 above) in `scripting_best_practices.md`.
- **In-game checklist:**
  - Items 1–8 from *Not verified*.
  - Enact under each of the five Distribution of Power groups. Check the preview tooltip, the amendment on the active
    law, the government name and the ruler title.
  - Switch Distribution of Power while holding the law (voting → Oligarchy → Technocracy). Check the amendment swaps and
    the government type follows.
  - Repeal the law. Check the amendment is gone.
  - Load a save that already holds the law under a voting law. Within a month it should carry the Direct Democracy
    amendment and keep its behaviour.
  - Check the amendment can't be repealed from the law panel while its Distribution of Power still matches.

## Out of scope

- Giving the law to historical collegial governments at game start (Switzerland, the Hanseatic cities, San Marino).
- New enactment events for the non-voting combinations.
- ~~Algorithmic Governance as a prerequisite.~~ Added 2026-09-27; see the follow-up at the end.
- A new icon (the current `direct_democracy.dds` stays).
- A preview tooltip on the Distribution of Power laws saying the amendment will change.

## Follow-up (2026-09-27): Algorithmic Governance

Algorithmic Governance is now a prerequisite. Every other governance principle already paired with it, Monarchy
included, so blocking only the law that says no person stands above the government was inconsistent.
`modern_election_events.33.a` ("neural direct democracy") and `ch_set_political_model`, which counts it as
Technocratic, already treat it as a shared-decision regime.

It is a sixth row, not part of `collective_governance_is_technocratic`, because Collegial Administration's name, text
and tooltip are about bureaus.

| Piece | Value |
|---|---|
| Trigger | `collective_governance_is_algorithmic` (`law_algorithmic_governance`) |
| Amendment | `amendment_collective_algorithmic_commons` "Algorithmic Commons": `state_political_strength_from_wealth_mult = -0.25` (the Direct Democracy value: every citizen's feedback weighs the same), `political_movement_radicalism_add = -0.1` (grievances reach the algorithm before they harden; vanilla's support-regime action is −0.1, the internal-security laws −0.03 to −0.05) |
| Government type | `gov_collective_algorithmic_commons` "Algorithmic Commons", ruler `RULER_TITLE_STEWARD` "Steward", parliamentary_elective, before the catch-all |
| Preview | `COLLECTIVE_GOVERNANCE_TT_ALGORITHMIC` |

Cascade (`extra_law_consistency_generated.txt`): the only change that can fire is that a Collective Governance country
moving to Algorithmic Governance keeps the law. The new candidate lines in the Monarchy and Colonial Administration
cascades (which fire only under Anarchy) and the Parliamentary Republic cascade (only under Autocracy) cannot hold
while Algorithmic Governance does. In the Neocameralism cascade, Monarchy comes first and fails only under Anarchy.
