# Social Movements and Religious Revival

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## Social Movement Journal Entries (history)

This section originally documented eight social-movement JEs that all shared a passive-timer-plus-random-events shape. Four have since been deleted (LGBTQ+ Rights, Second-Wave Feminism, Decline of Religion, Environmental Crisis), **along with their dedicated event files** — the surviving content was folded into general-purpose event files with their own dispatch (see *Where the ex-JE content lives now* below). There is no `social_movement_orphans_on_action`; that on_action never shipped. Civil Rights was redesigned around a progress bar + buttons + path-dependent outcomes; see the Civil Rights section in `docs/systems/journal_entry_systems.md`.

### Currently active JEs of this family
- `je_civil_rights` — progress bar, 6 button toggle pairs, path-dependent victory/failure (see `docs/systems/journal_entry_systems.md`)
- `je_human_augmentation` — passive timer (legacy shape; not yet redesigned)
- `je_morphological_freedom` — passive timer, on the augmentation debate's pattern (era 13 phase 3; see [Morphological Freedom Debate and Bodily Autonomy](#morphological-freedom-debate-and-bodily-autonomy))
- `je_digital_rights` — passive timer (legacy shape)
- `je_post_scarcity` — passive timer (legacy shape)
- `je_mental_health` — passive timer (legacy shape)

### Where the ex-JE content lives now

`events/lgbtq_events.txt`, `events/feminist_events.txt`, `events/secular_events.txt` and `events/environmental_events.txt` **no longer exist**. What survived moved into shared event files, each with a real dispatch site:

| Movement | Tech gate | Events today | Dispatched from |
|---|---|---|---|
| LGBTQ+ rights | `LGBTQ_rights_movement` | `society_technology_events.7`–`.8` (§ 5 of that file) | `society_technology_events_on_action` in `common/on_actions/extra_on_actions.txt` |
| Second-wave feminism | `second_wave_feminism` | `society_technology_events.1`–`.2` (§ 1) | same on_action |
| Decline of religion | `decline_of_organized_religion` (OR `sexual_revolution` / `social_media`) | `social_tensions_events.13` (§ Category 7 — Religious Revivals), plus the 7-event `events/religious_revival_events.txt` counterbalance | `common/on_actions/social_tensions_on_actions.txt` random list |
| Environmental crisis | `environmental_movement` / `pollution_control` | `environmentalism_events.*` — warming thresholds `.1`–`.4` and `.22` (4.0°C), cooling recoveries `.17`–`.21` and `.23` | `gw_fire_warming_threshold_event` / `gw_fire_cooling_threshold_event` in `extra_on_actions.txt`, under `je_global_warming` |

The `.100` (failure) and `.200` (victory) capstone events for these four have been removed along with their JE-shape modifiers (`*_struggle_active`, `*_stagnation`, `*_triumph`, `*_crushed`, `*_paralysis`, `*_revivalism`, `feminism_emancipated_character_modifier`, `feminism_backlash_character_modifier`, `env_crisis_reform_window`).

### Summary Table (legacy-shape JEs still in the mod)

| JE | Trigger Tech | Law Group | Complete | Fail |
|---|---|---|---|---|
| Human Augmentation | `biohacking_and_human_augmentation` OR `brain_computer_interfaces` (via `has_augmentation_tech`) | `lawgroup_human_augmentation` | any of `law_regulated_augmentation_market` / `law_mandatory_augmentation` / `law_unrestricted_augmentation` | `law_human_purity` |
| Morphological Freedom | `morphological_freedom` (era 12) | `lawgroup_bodily_autonomy` | `law_morphological_freedom` or `law_clade_citizenship` | `law_natural_form` at the timeout (an `on_timeout` branch, not a `fail` block) |
| Digital Rights | `automated_surveillance` / `cybersecurity` | `lawgroup_privacy_rights` | `law_strong_privacy_rights` | `law_intrusive_surveillance` + ministry of intel |
| Post-Scarcity | `post_work_society` (era 12; `universal_basic_income` until the era 13 split, 2026-10-31) | `lawgroup_welfare` | `law_post-scarcity` | `fail = { always = no }` — timeout only |
| Mental Health | `mental_health_awareness` | `lawgroup_criminal_justice` | `law_rehabilitation_focused_criminal_justice` + social_security ≥ 4 | `law_punishment_focused` or `law_penal_labor_camps`, once `journal_entry_age` ≥ 3650 days (10 years; timeout is 20) |

**After a revolution.** A revolution's winner gets fresh records of every finished journal entry (`scripting_best_practices.md` § "What a Civil War's Winner Inherits"). For Human Augmentation, Morphological Freedom and Mental Health, `possible` is tech-only and the end conditions are laws, so a finished debate would re-activate on the winner. It would then end again at once and replay its outcome event, or, after a timeout, run another twenty years. Each sets a resolved variable (`human_augmentation_resolved`, `morphological_freedom_resolved`, `mental_health_crisis_resolved`) in `on_complete`, `on_fail` and `on_timeout` (Morphological Freedom has no `on_fail`), and their `is_shown_when_inactive` / `possible` require its absence. Their `is_shown_when_inactive` also requires `is_revolutionary = no`, as civil rights' does. So rebels can't start their own debate mid-war, win, and keep a fresh outcome. The check is not in `possible`, so it can't affect an inherited active record. Their 10-year outcome modifiers are not rebuilt on the winner; civil rights' are (`journal_entry_systems.md` § Civil Rights). Digital Rights and Post-Scarcity have no such guard yet. Their completion is blocked while the target law holds, but on a winner a failed Digital Rights entry re-arms and fails again at once, and a timed-out entry of either starts a new timer.

### Event Design Patterns

Each surviving JE has monthly pulse events plus a fail-state event (except Post-Scarcity, whose `fail` block is `always = no`). Events follow these design principles:

- **Three-option structure:** Option A (progressive/reformist), Option B (moderate/compromise), Option C (regressive/oppressive). Most options have meaningful tradeoffs — treasury costs for spending decisions, opposition radicals for partisan choices.
- **Fire-once events:** Policy-debate events that represent one-time historical moments use `has_global_variable` gates so they only fire once per game. Currently: `lgbtq_military_debate_happened`, `women_military_debate_happened`, `ai_predictive_policing_debate_happened`, `ai_bureaucracy_debate_happened`, `state_religion_debate_happened`.
- **Law-gated options:** Some regressive options require specific laws to be available (e.g., surveillance expansion requires `law_intrusive_surveillance`). AI chance modifiers weight options contextually based on current laws.
- **Law-gated AI weights:** AI preference for certain options increases when the country has relevant laws (e.g., `law_laissez_faire` boosts "protect industry" choice, `law_outlawed_dissent` boosts "label as terrorists" choice).
- **Cooldowns:** Routine debate events use `normal_modifier_time`; serious incidents and fire-once events use `long_modifier_time`. Digital Rights also spaces its three leak stories (`surveillance_events.1`–`.3`): each sets `te_dr_leak_recent` for two years and none fires while it holds, and its pool's no-event weight is 400, not 200.

### Files

| System | JE Definition | Events | Modifiers |
|---|---|---|---|
| LGBTQ+ Rights | (JE deleted) | `society_technology_events.7`–`.8` | `common/static_modifiers/extra_modifiers.txt` (event-flavor only) |
| Second-Wave Feminism | (JE deleted) | `society_technology_events.1`–`.2` | `common/static_modifiers/extra_modifiers.txt` (event-flavor only) |
| Human Augmentation | `common/journal_entries/je_human_augmentation.txt` | `events/augmentation_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Morphological Freedom | `common/journal_entries/je_morphological_freedom.txt` | `events/morphological_freedom_events.txt` | `common/static_modifiers/extra_modifiers.txt` (`morphological_freedom_*`, `natural_form_*`, `mf_*`) |
| Environmental Crisis | (JE deleted; folded into `je_global_warming`) | `events/environmentalism_events.txt` | `common/static_modifiers/extra_modifiers.txt` (event-flavor only) |
| Digital Rights | `common/journal_entries/je_digital_rights.txt` | `events/surveillance_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Post-Scarcity | `common/journal_entries/je_post_scarcity.txt` | `events/post_scarcity_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Mental Health | `common/journal_entries/je_mental_health.txt` | `events/mental_health_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Decline of Religion | (JE deleted) | `social_tensions_events.13`; `events/religious_revival_events.txt` | `common/static_modifiers/extra_modifiers.txt` (`rre_*`) |
| Religious Revivals | — (no JE, event-driven) | `events/religious_revival_events.txt` | `common/static_modifiers/extra_modifiers.txt` |

## Morphological Freedom Debate and Bodily Autonomy

Era 13 phase 3 (`docs/superpowers/specs/2026-10-31-era-13-technology-tree-design.md` § 7.1, § 7.2, § 7.3). The **Morphological Freedom** technology (era 12, society; after Human Augmentation and the LGBTQ+ Rights Movement) opens a law group and a debate journal entry. The group is about how a body looks, chosen for self-expression: appearance, sex characteristics, fur, tails. What a body can do stays in Human Augmentation, a separate group, so the interest groups split differently on the two. **Self-Directed Evolution** (era 13, society; after Morphological Freedom and Rejuvenation Therapies) adds the fourth law, Clade Citizenship.

**The law group.** `lawgroup_bodily_autonomy` (Human Rights, opinion impact 0.5, carried by regime change), in `common/laws/te_bodily_autonomy_laws.txt`:

| Law | Unlocked by | Modifier |
|---|---|---|
| `law_natural_form` | none; every country's law from 1836 | none |
| `law_licensed_modification` | `morphological_freedom` | acceptance without a shared heritage trait +5, migration pull +5%, institution bureaucracy cost +5% |
| `law_morphological_freedom` | `morphological_freedom` | acceptance without a shared heritage trait +10, migration pull +10%, cultural hegemony art +5% |
| `law_clade_citizenship` | `self_directed_evolution` | acceptance without a shared heritage trait +10 (Morphological Freedom's), then the heritage parity below; migration pull +15%, cultural hegemony art +5% |

- **Natural Form first.** It is first in its file, so it is what any country without a law in the group gets: an old save loading the group, a country created later. `common/history/extra_history.txt` seeds it as well, beside `law_no_augmentation`.
- **Natural Form carries nothing, and every ideology is neutral on it.** Every country holds it for two centuries before the technology, so a modifier or a stance on it would apply all that time with no law to answer it. The groups that want it show it by opposing the others.
- **The acceptance hook** (`country_acceptance_no_shared_heritage_trait_add`) adds to the citizenship law in force. The mod's citizenship laws (`common/laws/modified.txt`) are not vanilla's: no shared heritage reads −20 to 0, and Civil Rights Movement and Social Justice Movements add +10 each, so by era 12, under four of the six, a pop with no shared heritage trait already gets +20, against +20 to +25 for one sharing a heritage trait or group. The bonus lifts no-shared above them; whether the engine then gives a shared-trait pop the higher figure is on the play-test list (`scripting_best_practices.md` § "Citizenship Acceptance: Read the Mod's Laws, Not Vanilla's").
- **Stances** (`ideology_modifications.py`, `BODILY_AUTONOMY_LISTS` and `BODILY_AUTONOMY_STANCES`, applied by the loop at the end of the file; hand-written in `extra_ideologies.txt` for the mod's own ideologies). Five classes, Natural / Licensed / Freedom / Clade: *traditional* N D SD SD (the Devout's ideologies of every religion, patriarchal, traditionalist, reactionary, integralist, fascist, ethno-nationalist, agrarian, isolationist); *cautious* N N D SD (paternalistic and its variants, particularist, patriotic, jingoist, loyalist, authoritarian, populist, proletarian, communist, vanguardist); *regulated* N A N D (egalitarian, socialist, social democrat, reformer, plutocratic, technocratic, positivist, meritocratic, modernizer); *liberal* N A SA SA (the Intelligentsia's liberal, liberal modern, anti-clerical and republican, radical, egalitarian modern, humanitarian, feminist, multicultural); *libertarian* N D SA SA (laissez-faire, individualist, market liberal, anarchist). The transhumanist leader (and `movement_transhumanist`, whose ideology it is) is N A A SA: a group backs enacting a law only when it ranks it above the law in force, so the classes at SA for Morphological Freedom can't carry the step to Clade Citizenship, and the transhumanists do. The custom religions' societies follow their class (traditionalist, imperial cult and theocratic SD; totalitarian SD; meritocratic D; inclusive SA).
- `gen_law_consistency.py` lists the group after Human Augmentation; its laws have no `unlocking_laws` or `disallowing_laws`, so the generated sweep has nothing to check in it.

**The journal entry.** `je_morphological_freedom`, on `je_human_augmentation`'s pattern: the Social Movements rule, not decentralized, `is_revolutionary = no` in `is_shown_when_inactive`, the resolved variable `morphological_freedom_resolved` set in `on_complete` and `on_timeout`, and a 7,300-day timeout. While active, `morphological_freedom_debate_active_modifier` (+5% cultural hegemony art, +5% turmoil penalties).

| Ending | When | Result |
|---|---|---|
| Success (`.200`, popup) | `law_morphological_freedom` or `law_clade_citizenship` enacted | `morphological_freedom_embraced_modifier` (+10% art, +5% prestige) for ten years, decaying; small loyalists among academics |
| Failure (`.100`, popup) | `law_natural_form` in force at the timeout | Enforce (`natural_form_enforced_modifier`: −10% art, −5% migration pull; Devout and Rural Folk approve, Intelligentsia disapprove) or look away (`natural_form_tolerated_modifier`: +10% turmoil penalties, −2% prestige) |
| Unsettled | `law_licensed_modification` in force at the timeout | `morphological_freedom_unsettled_modifier` (+10% turmoil penalties), ten years, decaying |

The failure is a branch of `on_timeout`, not a `fail` block: the engine has no "failed at the deadline" hook, and a `fail` on the entry's age would race the timeout.

**Events** (`events/morphological_freedom_events.txt`, pooled at 240 = 0 beside six 10s): `.1` the first clinics, `.2` a television host's transformation, `.3` sport and eligibility, `.4` parents and children (not under Natural Form), `.5` a religious backlash (a powerful Devout), `.6` a fashion that sweeps a generation (not under Natural Form). All six share a two-year lockout, `te_mf_event_recent`; `.1`, `.3`, `.4` and `.6` have a twenty-year cooldown (once per debate) and `.2` and `.5` a ten-year one, so a full debate brings about eight at most. Options trade the Devout and Rural Folk against the Intelligentsia, with small modifiers and treasury costs.

**Clade Citizenship and the heritage parity** (spec § 7.3). The fourth law, last in the file at progressiveness 80, is the right to leave the human body plan behind and remain a citizen, and it takes heritage out of acceptance. A static line can't do that here: with Civil Rights Movement and Social Justice Movements, a shared heritage trait, a shared trait group and none read 20 / 20–25 / 20 under Sovereign Subjecthood and Cultural, Assimilatory and Universal Citizenship, 40 / 30 / 10 under Ancestral and 60 / 60 / 0 under Racialized Citizenship, so the spec's +20 to no shared heritage alone would rank those pops 20 above a shared trait under the first four and leave 30 to 60 points of heritage under the other two. So the law keeps Morphological Freedom's +10 (no pop is worse off than under it), and `te_clade_parity_refresh` (`te_bodily_autonomy_effects.txt`, from `on_monthly_pulse_country` in `te_bodily_autonomy_on_actions.txt`, its one refresh site) lifts each of the three figures to the highest of them: `te_clade_parity_trait`, `_group`, `_none` (`te_bodily_autonomy_modifiers.txt`, one point of one figure each) at `multiplier = var:te_clade_lift_<trait|group|none>`. Each base (`te_clade_base_*_value`, `te_bodily_autonomy_values.txt`) is the `modifier:` read less last month's lift, subtracted only while its modifier is there (a revolution's winner keeps the variables, not the modifiers); the three lifts go into locals before any variable is overwritten; each modifier is removed before it is re-added; without the law the modifiers go before their variables. Every pop then reads one heritage figure, at least the shared trait's, and the inversion of the paragraph above can't arise under this law. The law's tooltip says so (`te_clade_law_parity_tt` from `on_enact`, as Automation Policy's laws do); the Nation tab lists the three modifiers under Society and the three heritage types as Acceptance rows (`gen_nation_tab.py`). Up to a month passes between enacting or repealing the law and the parity. Self-check `clade_heritage_parity` (`docs/testing/era-13-playtest.md`): once a game, the month after a country's parity closed a gap of at least 1, OK if the three reads are equal. `test_self_directed_evolution.py` pins the script's shape and runs the arithmetic on the citizenship laws' own figures. A fifth law goes last in the file, with a code in each `BODILY_AUTONOMY_LISTS` row and each hand-written block (`ideology_lawgroup_audit` names a miss), then `scripts/generators/regen_ideologies_offline.py`.

## Religious Revival Events

**Purpose:** Counterbalance the natural decline of the Devout IG caused by urbanization, literacy, and modernization techs. Inspired by 20th/21st century religious-political movements.

**Mechanism:** 7 events fire from the `society_technology_events_on_action` random list, each tied to a different social tech (eras 7–9). Each offers three options:
- **Strong option:** Adds a 20-year modifier (`very_long_modifier_time`) with large `interest_group_ig_devout_pop_attraction_mult` (0.25–0.50) and `interest_group_ig_devout_pol_str_mult` (0.20–0.50). Four hold at full strength for the 20 years (events 1, 2, 3, 5); three decay over them (events 4, 6, 7). Some include costs (authority, research speed, prestige). These stack — a player who embraces multiple religious movements will see a very strong Devout IG.
- **Moderate option:** Adds a decaying modifier lasting 20 years with moderate attraction/pol_str bonuses.
- **Secular option:** No devout boost or negative (radicals), with alternative benefits.

**Law Gating:**
- **State atheism** blocks events 1, 2, 4, 5, 6 (mainstream religious organizing implausible under state suppression).
- Events 3 (Liberation Theology) and 7 (Faith-Based Welfare) CAN fire under state atheism — representing underground religious movements for justice/welfare. They get special variant text describing clandestine faith communities.
- AI weights are modified by relevant laws: `law_ministry_of_religion` boosts embrace options, `law_total_separation` and `law_no_ministry_of_religion` favor secular options.

**Religion-Variant Localization:**
- Descriptions and flavor text use `first_valid`/`triggered_desc` blocks based on the country's religion heritage trait (`heritage_islamic`, `heritage_dharmic`, `heritage_jewish`).
- **Islamic variants:** Reference ummah, Quran, fatwas, zakat, masjid, khutba, dawah, Sharia.
- **Dharmic variants:** Reference dharma, swamis/gurus, ashrams, satsangs, seva, darshan, saffron, Hindutva.
- **Jewish variants:** Event 4 has a religious Zionist variant.
- **Default:** Covers Christian and other religions with generic or broadly Western religious language.
- Some events also have variant titles (e.g., "The Satellite Minbar" for Islamic event 2, "One Ummah, One Law" for Islamic event 4).

**Removal:** The "Secularization Campaign" decision (requires `decline_of_organized_religion` tech) removes all seven strong-option modifiers at once, with a radicals cost, instead of waiting out their 20 years.

**Events:**
1. **The Moral Majority** (`television_broadcasting`, era 7) — Religious political organizing via broadcast media
2. **The Electronic Pulpit** (`pop_culture`, era 7) — Televangelism and megachurches
3. **The Preferential Option** (`civil_rights_movement`, era 7) — Liberation theology (fires under state atheism)
4. **One Nation Under God** (`globalization`, era 9) — Religious nationalism
5. **The Digital Pulpit** (`social_media`, era 9) — Online faith communities
6. **The Culture War** (`sexual_revolution`, era 8) — Religious conservative backlash
7. **The Faithful Hand** (`social_justice_movements`, era 9) — Faith-based welfare (fires under state atheism)

**Files:**
- Events: `events/religious_revival_events.txt`
- Modifiers: `common/static_modifiers/extra_modifiers.txt` (search for `rre_`)
- On_action: `common/on_actions/extra_on_actions.txt` (in `society_technology_events_on_action`)
- Decision: `common/decisions/extra_decisions.txt` (`secularization_campaign`)
- Loc: `localization/english/te_events_l_english.yml` (variant keys with `_islamic`, `_dharmic`, `_jewish`, `_atheism` suffixes)

---
