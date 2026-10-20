# Grand Monuments phase 4 (landmarks) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Place the twelve Grand Monuments standing in 1836 as locked "landmarks" with their own names and pictures.

**Architecture:** A landmark is an ordinary monument with five state records (`gm_landmark`, `gm_skin = landmark_<key>`, `gm_form`, `gm_namesake = landmark`, `gm_ceremony_level`). Placement runs once from `on_game_started_after_lobby`. Two triggers (`gm_state_is_landmark`, `gm_state_has_historical_name`) gate every writer of the skin, form and name. Its picture is a code from 1,000,000 set after the rest of `gm_state_update_picture`.

**Tech Stack:** Victoria 3 script, customizable localization, `.gui`, Python unittest (`test_grand_monument_registry.py`), the FLUX icon pipeline (`gm_picture` category).

**Spec:** `docs/superpowers/archive/specs/2026-10-12-grand-monuments-landmarks-design.md` (merged in #903). It builds on the pictures spec (`2026-10-11-grand-monument-pictures-design.md`, PR #909); this branch is stacked on `feat/gm-pictures` and its PR targets `main`.

## Global Constraints

- Owners checked in the game files (2026-10-11): FRA, RUS, PRU, USA, AUS, SIC, **JAI** (Dhundhar holds Jaipur; the spec guessed RAJ), PAN, BRZ, TGR (Aksum's part of `STATE_GONDER`), DEN, SWI.
- Picture codes are 1,000,000 + the row number in `LANDMARKS` order, append-only.
- `gm_clear_state` takes `KEEP_LANDMARK = yes/no` at every call; only `gm_state_rededicate` passes `yes`.
- Skins change name, wording and art, never effects. A landmark takes no inscription.
- `.11` gets no landmark option.
- Every new `.txt`: one UTF-8 BOM, tabs. Loc in existing files, then `organize_loc.py`.

## Review Focus

1. The landmark's picture must survive `gm_state_update_picture`'s form-only building lines (La Scala would read 400): landmark lines go last.
2. `gm_skin_name`'s landmark branches must precede the five building-form branches.
3. `gm_state_unveil` must not reset a landmark's form (`gm_state_current_form_fits` is false for a landmark skin).
4. A Rededicate keeps the look and picture but renames; the namesake choice offers "Its historical name".
5. `create_building` on a state that already has a monument takes the larger level: the seed skips such a state.

---

### Task 1: The registry table, the seeding and the names

**Files:** `test_grand_monument_registry.py` (LANDMARKS rows; LandmarkTests), new `common/scripted_effects/gm_landmark_effects.txt`, `common/on_actions/monument_events_on_actions.txt`, `common/scripted_triggers/monument_triggers.txt` (`gm_state_is_landmark`, `gm_state_has_historical_name`), `common/customizable_localization/gm_custom_loc.txt` (`gm_skin_name` landmark branches first; `gm_landmark_name_evt`, `gm_landmark_desc`), loc.

- `LANDMARKS = (Landmark(key, state, tag, dedication, form, standin_skin, standin_form, level), ...)`.
- `gm_seed_landmark = { KEY STATE TAG DEDICATION FORM LEVEL }`: in `s:$STATE$.region_state:$TAG$ ?= { … }`, skip a state with a monument; `create_building` with `level` and `activate_production_methods`; the five records; `gm_rebuilding` 1 day; `owner = { trigger_event = monument_events.20 }`; `debug_log` the placement. An `else` logs a landmark not placed.
- On-action `gm_landmarks_on_game_started_after_lobby` (`on_actions` form) behind `gm_system_enabled` and global `gm_landmarks_seeded`.
- Tests: each row's call with its values; one state per row; key not a vanilla monument (`bg_monuments`) or mod wonder; loc `gm_skin_landmark_<key>` and `gm_landmark_<key>_desc`; branches ahead of the building branches; form in FORMS or BUILDING_FORMS; stand-in pair in PICTURES; `.11` has no landmark option.

### Task 2: The lock

**Files:** `gm_effects.txt` (`gm_state_offer_skins`, `gm_clear_state` + 3 callers, `gm_ai_decide_contests`), `gm_name_effects.txt` (`gm_state_unveil`, `gm_state_name_if_unnamed`), `te_debug_monuments_events.txt` (3 `gm_clear_state` calls: `no`), `gm_sguis.txt` (Rename, Name It), `gm_commission_effects.txt` (`gm_com_fulfil`).

- `gm_state_offer_skins`: a landmark keeps its skin, asks nothing, sets `gm_unveil_pending`, fires `.20`.
- `gm_clear_state = { KEEP_LANDMARK = yes }` keeps `gm_landmark`, `gm_skin`, `gm_form` and `gm_picture_code`.
- Rename / Name It: greyed while `gm_state_has_historical_name` ("A landmark keeps its historical name").
- `gm_com_fulfil`: no rename while it has its historical name.
- AI: Preserve ×3 for a landmark.
- Tests: one per §3.2 row.

### Task 3: Rededication renames it

**Files:** `gm_custom_loc.txt` (`gm_monument_name_row`/`_evt` landmark branch before the year), `monument_events.txt` (`.25`: `keep_landmark` name branch in the same place; "Its historical name" option), loc.

- Ruling: the event form needs an article ("the Arc de Triomphe", but "La Scala"), so `gm_name_landmark_evt` prints `gm_landmark_name_evt`, a per-landmark custom loc splicing `$gm_skin_landmark_<key>$`.

### Task 4: Pictures

**Files:** `test_grand_monument_registry.py` (PICTURES 1000001–1000012; tests), `gm_picture_effects.txt` (`gm_state_picture_landmarks` called last in `gm_state_update_picture`; sweep chain), `gm_effects.txt` (`gm_state_undedicate` keeps a landmark's picture), `grand_monuments_widget.gui` (12 icons), `icon_prompts.py` (12 entries), 12 DDS.

- Ruling: all twelve pictures ship here, so every branch holds its own code; the test still checks own-code-if-drawn-else-stand-in.

### Task 5: The civic-progress technologies

**Files:** `grand_monument_pms.txt` (no `unlocking_technologies` on artistic, naturalist, scientific), `monument_triggers.txt` (`gm_state_lacks_dedication_tech`), `gm_effects.txt` (`gm_state_first_sight` sends such a pick to the ceremony), test (`PM_TECH_GATES` split from `TECH_GATES`).

### Task 6: The landmark line in the row and on the card

**Files:** `grand_monuments_widget.gui`, `te_state_panel_widgets.gui`, `gm_values.txt` (`gm_disp_is_landmark`), loc.

- Ruling: a "Historical monument" line (tooltippable, landmarks only) carries the desc and the lock on hover: one tooltip on a line that exists only for a landmark, rather than a conditional tooltip on every title.

### Task 7: Debug

**Files:** `te_debug_monuments_events.txt` (`.5`: place every landmark whose state has no monument), `gm_landmark_effects.txt` (per-landmark `TE_MONUMENTS:` line).

### Task 8: Docs and checks

- `02-timeline.md` paragraph (§9), PDF; `mod_systems.md`; the spec's owner table (JAI).
- Suite, ruff, tabs, BOM, organize_loc, loc files, gui lint, strict audits, post-load rosters, guide lint/check.
- Final review (fresh reviewer, most capable model), then the PR (`--base main`).
