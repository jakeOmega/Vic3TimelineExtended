# Social Movements and Religious Revival

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## Social Movement Journal Entries (history)

This section originally documented eight social-movement JEs that all shared a passive-timer-plus-random-events shape. Four have since been deleted (LGBTQ+ Rights, Second-Wave Feminism, Decline of Religion, Environmental Crisis), **along with their dedicated event files** — the surviving content was folded into general-purpose event files with their own dispatch (see *Where the ex-JE content lives now* below). There is no `social_movement_orphans_on_action`; that on_action never shipped. Civil Rights was redesigned around a progress bar + buttons + path-dependent outcomes; see the Civil Rights section in `docs/systems/journal_entry_systems.md`.

### Currently active JEs of this family
- `je_civil_rights` — progress bar, 6 button toggle pairs, path-dependent victory/failure (see `docs/systems/journal_entry_systems.md`)
- `je_human_augmentation` — passive timer (legacy shape; not yet redesigned)
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
| Digital Rights | `automated_surveillance` / `cybersecurity` | `lawgroup_privacy_rights` | `law_strong_privacy_rights` | `law_intrusive_surveillance` + ministry of intel |
| Post-Scarcity | `universal_basic_income` | `lawgroup_welfare` | `law_post-scarcity` | `fail = { always = no }` — timeout only |
| Mental Health | `mental_health_awareness` | `lawgroup_criminal_justice` | `law_rehabilitation_focused_criminal_justice` + social_security ≥ 4 | `law_punishment_focused` or `law_penal_labor_camps`, once `journal_entry_age` ≥ 3650 days (10 years; timeout is 20) |

**After a revolution.** A revolution's winner gets fresh records of every finished journal entry (`scripting_best_practices.md` § "What a Civil War's Winner Inherits"). For Human Augmentation and Mental Health, `possible` is tech-only and the end conditions are laws, so a finished debate would re-activate on the winner. It would then end again at once and replay its outcome event, or, after a timeout, run another twenty years. Both set a resolved variable (`human_augmentation_resolved`, `mental_health_crisis_resolved`) in `on_complete`, `on_fail` and `on_timeout`, and their `is_shown_when_inactive` / `possible` require its absence. Their `is_shown_when_inactive` also requires `is_revolutionary = no`, as civil rights' does. So rebels can't start their own debate mid-war, win, and keep a fresh outcome. The check is not in `possible`, so it can't affect an inherited active record. Their 10-year outcome modifiers are not rebuilt on the winner; civil rights' are (`journal_entry_systems.md` § Civil Rights). Digital Rights and Post-Scarcity have no such guard yet. Their completion is blocked while the target law holds, but on a winner a failed Digital Rights entry re-arms and fails again at once, and a timed-out entry of either starts a new timer.

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
| Environmental Crisis | (JE deleted; folded into `je_global_warming`) | `events/environmentalism_events.txt` | `common/static_modifiers/extra_modifiers.txt` (event-flavor only) |
| Digital Rights | `common/journal_entries/je_digital_rights.txt` | `events/surveillance_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Post-Scarcity | `common/journal_entries/je_post_scarcity.txt` | `events/post_scarcity_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Mental Health | `common/journal_entries/je_mental_health.txt` | `events/mental_health_events.txt` | `common/static_modifiers/extra_modifiers.txt` |
| Decline of Religion | (JE deleted) | `social_tensions_events.13`; `events/religious_revival_events.txt` | `common/static_modifiers/extra_modifiers.txt` (`rre_*`) |
| Religious Revivals | — (no JE, event-driven) | `events/religious_revival_events.txt` | `common/static_modifiers/extra_modifiers.txt` |

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
