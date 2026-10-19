# Grand Monuments: frozen at dedication, grander with age — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Grand Monument stops growing by construction once its construction after dedication is done; its grandeur grows with age (2% of its levels a year) and through events; new levels in such a state found a new monument beside it, and a monument standing beside another carries its own dedication's effects and contests.

**Architecture:** The state's one building keeps standing at the sum of every monument's *levels*. Grandeur becomes levels + age (`gm_age` on the state for the primary, `gm_tr_age` on a `gm_monument` container). Level arithmetic moves to new `*_levels` values so rebuilds keep their heights; every effect reads grandeur. Secondaries gain container twins of the fit, stance and contest triggers, and the national sums and IG nets walk the owner's `gm_monuments_held`. Work that rebuilds or reads its own writes back runs in hidden events (`monument_events.29`, `.30`), never in the refresh tooltips walk.

**Tech Stack:** Paradox Clausewitz script (Victoria 3 1.14.5), `.gui`, customizable localization, Python `unittest` structural pins (`test_grand_monument_registry.py`, `test_grand_monument_trophies.py`, `test_grand_monuments_layout.py`, `test_grand_monument_archaeology.py`).

**Spec:** `docs/superpowers/archive/specs/2026-10-16-grand-monument-ageing-design.md`

## Global Constraints

- Ageing: levels × 2 ÷ 1200 a month (written `multiply = 2 divide = 1200`); ×0.5 under Mothballed; no six-decimal literal anywhere.
- The building's level = Σ levels of every monument in the state, at most 200 (the ladder's reach); every rebuild reads `gm_state_level` / `*_levels`, never grandeur.
- One rebuild a state a day (`gm_rebuilding`, review fix 1): any new rebuilding work waits when it stands.
- A variable backing a `multiplier` is zeroed, never removed. No timed variable on a container.
- Tabs in brace files; exactly one UTF-8 BOM where the file had one; loc into existing `*_l_english.yml`, then `organize_loc.py`.
- Python 3.11-compatible tests (no PEP 701 f-strings).
- Old saves: missing `gm_age` / `gm_tr_age` read 0; missing `gm_levels` is written, never inferred as building beside.

## Review Focus

1. **Queued levels at dedication** (the player queued ten, the ceremony asked at the first): all ten join the monument, and only levels started after construction stopped found a new one. Pinned in Task 4 (`gm_levels` is written only while `is_under_construction` is false).
2. **A walked tooltip never demotes, swaps or rebuilds:** the refresh only triggers `monument_events.29`. Pinned in Task 4/6 (the refresh body contains no `create_container`, `destroy_container`, `remove_building`).
3. **A contested secondary pulled down together with another in the same state** (the notice's Tear Them All Down): one shrink rebuild by the total. Pinned in Task 7.
4. **A trophy taken from an aged monument and brought home** keeps its age both ways. Pinned in Task 2.
5. **Old saves:** a dedicated primary with no `gm_levels` and nothing queued is frozen at its current levels, not demoted. Pinned in Task 4.

---

### Task 1: Levels apart from grandeur (no behaviour change)

**Files:** Modify `common/script_values/gm_values.txt`, `common/script_values/gm_monument_values.txt`, `common/script_values/gm_trophy_values.txt`, `common/script_values/gm_commission_values.txt`, `common/scripted_effects/gm_effects.txt`, `gm_trophy_effects.txt`, `gm_monument_effects.txt`, `gm_commission_effects.txt`, `events/monument_events.txt`, `common/scripted_triggers/monument_triggers.txt`; tests in the four GM test files.

**Interfaces — Produces:**
- `gm_state_level` (state): `b:building_grand_monument.level`, 0 with none.
- `gm_state_secondary_levels` (state): Σ `gm_tr_levels` over `gm_monuments_here`.
- `gm_state_primary_levels` (state): `gm_state_level` − `gm_state_secondary_levels`, min 1; 0 with no building.
- `gm_mon_levels` (container): `gm_tr_levels` or 0.

- [ ] Every level-arithmetic reader switches: rebuild heights in `gm_state_tr_add_levels`, `gm_state_tr_shrink_by`, `gm_state_tr_remove_piece`, `gm_state_promote_secondary`, `gm_state_rededicate`, `gm_state_gift_grandeur`, `gm_state_tr_rebuild_from_moving`'s default; trophy shares (`gm_state_tr_levels`, `_whole`, `_levels_left`, `gm_mon_tr_levels`, `gm_mon_tr_whole`); `gm_state_rededicate_cost`; the ceremony level (`gm_state_start_ceremony`, `gm_state_offer_missed_ceremony`, `.2`'s immediate); the `gm_tr_take_*_tt` loc's "of its N levels".
- [ ] Test `LevelsApartTests.test_rebuilds_read_levels`: each rebuild body above contains `gm_state_level` or `gm_state_secondary_levels` and none contains `gm_state_grandeur` or `gm_state_secondary_grandeur`.
- [ ] Run the four GM test files: OK. Commit.

### Task 2: Age grandeur

**Interfaces — Produces:** `gm_state_primary_age`, `gm_mon_age` (0 if unset); `gm_state_primary_grandeur` = primary levels + age (0 none); `gm_mon_grandeur` = levels + age; `gm_state_secondary_grandeur` = Σ `gm_mon_grandeur`; `gm_state_grandeur` = primary + secondary grandeur (0 none). `gm_tr_value_of` (container): ceil(`gm_mon_grandeur` ÷ 2), written monthly into `gm_tr_grandeur` for trophies.

- [ ] `gm_clear_state` removes `gm_age`. Taking: the trophy's `gm_tr_age` = the share of age that its levels are of the levels (primary: of `gm_state_primary_levels`; secondary piece: of its own); whole: all of it. The state / source container keeps the rest.
- [ ] Return: rejoining the primary adds the trophy's age to `gm_age`; rejoining a secondary adds to its `gm_tr_age`; standing beside keeps it; `gm_state_tr_take_records_from_moving` (split out of `gm_state_tr_rebuild_from_moving`) writes `gm_age` from it. Promotion carries the promoted container's age.
- [ ] Tests `AgeTests`: `gm_state_grandeur` sums primary and secondary grandeur; a piece's age share is written before the source loses it; the four return paths move `gm_tr_age`; `gm_tr_grandeur` is rewritten by the trophy pass.
- [ ] Commit.

### Task 3: Ageing

**Interfaces — Produces:** `gm_state_ages` (trigger, state): dedicated, `gm_seen`, not contested, no `gm_restore_pm` / `gm_ceremony_pending` / `gm_rebuilding`; `gm_mon_ages` (container): has `gm_tr_dedication`, at home (`gm_tr_origin` exists), not contested; `gm_policy_factor_age` (state: owner Mothballed 0.5 else 1; container via its state); `gm_state_age_step` = primary levels × 2 ÷ 1200 × factor; `gm_mon_age_step`.

- [ ] `gm_state_monthly` adds `gm_state_age_step` to `gm_age` before `gm_curve_in` is set; `gm_monument_monthly` adds `gm_mon_age_step` to each ageing container.
- [ ] Tests `AgeingTests`: the step's literal form (`multiply = 2 divide = 1200`), the order in `gm_state_monthly`, the four exclusions, trophies (tag `gm_trophy`) never age.
- [ ] Commit.

### Task 4: The freeze and building beside

**Interfaces — Produces:** state var `gm_levels`; `gm_state_record_frozen_levels`; trigger `gm_state_has_new_levels`; effect `gm_state_demote_primary` (state; reads `var:gm_demote_levels`; makes a `gm_monument` container with every record and clears the state); `gm_state_found_beside`; trigger `gm_state_can_expand`; hidden state event `monument_events.29` (immediate: `gm_state_found_beside` if new levels, then the settle check of Task 6).

- [ ] `gm_levels` = `gm_state_primary_levels` once dedicated, `gm_seen`, not under construction, no restore or ceremony pending (refresh and `.1`). Rewritten by every script change of the primary's levels (rejoin, piece taken, promotion, take-records); removed by `gm_clear_state` and Rededicate.
- [ ] New levels: `gm_state_primary_levels` > `gm_levels`, dedicated, `gm_seen`, no restore/rebuild pending. `.1` runs `gm_state_found_beside` directly; the refresh triggers `.29`. Founding: demote (levels `gm_levels`), `gm_newcomer`, `gm_state_undedicate`, `gm_state_start_ceremony`.
- [ ] `building_grand_monument` gets `can_build_government` / `can_build_private` = `gm_state_can_expand` (custom tooltips per reason: contested, a ceremony/unveiling/naming pending, a rebuild or restore pending, six monuments) and `ai_value` −25 × monuments standing.
- [ ] Self-check `monument_expansion_gated` (once a game: the first contested player primary's state logs whether `can_build_government` would read false — through the trigger, as the engine evaluates it) and `monument_frozen` (the first player monument frozen logs its levels).
- [ ] Tests `FreezeTests`: `gm_levels` gate includes `is_under_construction = no`; the refresh has no `create_container`; demote copies each record in `CONTAINER_RECORDS` (a list in the test); expansion gate reasons each have loc.
- [ ] Commit.

### Task 5: Secondaries' fit and effects

**Interfaces — Produces (container scope unless noted):** `gm_mon_is = { KEY }`, `gm_mon_is_bound`, `gm_mon_kind_regime`, `gm_mon_kind_ruler`, `gm_mon_kind_faith`, `gm_mon_raised_by_owner`, `gm_mon_message_fits`, `gm_mon_is_contested`, `gm_mon_is_heritage`, `gm_mon_status_fits`, `gm_mon_approved_by_<ig>` / `gm_mon_opposed_by_<ig>` (8 IGs), `gm_mon_first_sight` (effect: `gm_tr_raised_by` = owner for a bound one, `gm_tr_faith`, `gm_tr_built_by`, `gm_tr_seen`), `gm_mon_status_code` (2/3/4). State: `gm_local_steps_<key>` vars.

- [ ] `gm_sum_regime`, `gm_sum_<dedication>` and `gm_compute_ig` add the owner's fitting secondaries (`gm_monuments_held`) by dedication; contested ones subtract from `gm_tr_base_ig`. `gm_sum_standing` drops contested secondaries. The four `gm_disp_count_*` count secondaries.
- [ ] `gm_state_monthly`'s local effects per dedication: each `gm_local_<key>` on `gm_local_steps_<key>` = curve(that dedication's grandeur here) × the local policy factor; `gm_local_steps` stays as the primary's for the card.
- [ ] Tests `SecondaryFitTests`: each container stance trigger matches `DEDICATIONS` like the state's; every sum walks `gm_monuments_held`; `gm_state_monthly` writes all twelve step variables.
- [ ] Commit.

### Task 6: Secondaries' contests, choices, and the swap

**Interfaces — Produces:** container vars `gm_tr_contested`, `gm_tr_heritage`, `gm_tr_base_ig`, `gm_tr_supporter_ig`, `gm_tr_new_contest`; effects `gm_mon_contest`, `gm_mon_lift_contest`, `gm_mon_ledger_ig = { WHO FACTOR }`, `gm_mon_preserve`, `gm_mon_order_choice = { CHOICE }` (tear_down / rededicate; sets `gm_mon_order`, triggers `.30` on its state); `gm_state_raise_secondary` (state; `scope:gm_mon_raise`); `gm_state_swap_primary`; hidden state event `monument_events.30` (one rebuild-type action a run: all ordered tear-downs in one shrink, else one rededicate via swap; re-triggers itself a day later while orders remain or `gm_rebuilding` stands); sguis `gm_mon_tear_down_sgui`, `gm_mon_rededicate_sgui`, `gm_mon_preserve_sgui` (saved scope `gm_mon`).

- [ ] `gm_check_contests`, `gm_state_changed_hands`, `gm_state_adopt_for_winner` (by the global list), the monthly contested counter, `gm_ai_decide_contests` (Pull Down / Keep as Heritage; no Rededicate for the AI), `gm_notify_new_contests` and `.16` (a/b cover secondaries through orders; c leaves them to their rows) cover containers.
- [ ] The settle check (`.29`): a `gm_newcomer` primary that is dedicated, frozen, unveiled and named swaps with the grandest secondary when that one's grandeur is greater, once.
- [ ] Tests `SecondaryContestTests`, `SwapTests`: `.30` batches tear-downs into one `gm_state_tr_shrink_by`; a swap copies every record both ways; the settle swap runs only from `.29`.
- [ ] Commit.

### Task 7: Opportunities, Rededicate, anniversaries

- [ ] `gm_com_fit_grandeur` counts **levels**: fitting primary levels plus fitting secondaries' `gm_tr_levels` of the dedication (`gm_mon_com_counts`). `gm_com_pick_build_state` skips states where `gm_state_can_expand` fails.
- [ ] The gift: `gm_state_gift_grandeur` adds `gm_com_gift` to `gm_age` of the primary when it answers, else to the largest answering secondary's `gm_tr_age`; no rebuild, `gm_restore_pm` untouched.
- [ ] Rededicate halves the age as it halves the levels, kept through `gm_clear_state`; removes `gm_levels`.
- [ ] Anniversaries: `gm_state_holds_anniversary` reads the primary's grandeur ≥ 3; each paid option adds `gm_evt_grandeur` (10% of levels, at least 1) to the monument's age. Secondaries hold anniversaries if time allows (spec §5; owner: primary-only acceptable).
- [ ] Tests `OpportunityLevelTests`, `GiftAgeTests`, `RededicateAgeTests`, `AnniversaryAgeTests`. Commit.

### Task 8: Panels and loc

- [ ] State card: Grandeur value and hover (levels / years), the build-beside line (`gm_state_disp_can_expand` with its reason), beside rows' status, dedication, grandeur. JE secondary rows add status, grandeur and the three choice buttons (`blockoverride "mon_choices"`). Ceremony and How It Works text.
- [ ] `check_gui_lint.py`, `gui_reference_audit.py --strict`, `loc_coverage_audit.py --strict`, layout tests. Commit.

### Task 9: Docs, guide, play-test list

- [ ] `mod_systems.md` § Grand Monuments; `02-timeline.md` and `08-states.md` per spec §7; rebuild the PDF; `docs/testing/grand-monuments-ageing-playtest.md` with the self-checks.
- [ ] Full suite, ruff, every strict audit, `organize_loc.py`. Commit.

### Task 10: Issue #936 (owner: fold in or delegate; deferrable)

- [ ] Shadow records by region (spec §9), last; may be delegated once Tasks 1–9 are on the branch.
