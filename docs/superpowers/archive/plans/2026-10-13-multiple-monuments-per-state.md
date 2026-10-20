# Grand Monuments: Multiple Monuments per State via Script Containers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow multiple distinct Grand Monuments and returned cultural heritage to co-exist in a single state by abstracting `building_grand_monument` to have levels equal to the combined grandeur of all monuments in the state and the production method of the primary monument, while tracking each individual monument via script containers.

**Architecture:** 
- The physical Victoria 3 building (`building_grand_monument`) serves as the state-level engine anchor. Its building level equals `sum(gm_grandeur)` of all monuments located in that state, and its production method matches the primary monument's dedication.
- Each distinct monument/landmark in the state is represented by a `gm_monument` script container listed in `gm_monuments_here` on the state scope, retaining its own name, landmark ID, skin, form, picture code, dedication, and grandeur.
- When returning a trophy (`gm_state_tr_receive`), if the trophy is an exact piece of the standing landmark (e.g. Quadriga -> Brandenburg Gate, Parthenon Marbles -> Parthenon), it rejoins the existing landmark. If it is an independent monument (e.g. Luxor Obelisk or Temple of Dendera returning to Upper Egypt where Obelisks of Karnak stands), it creates a distinct `gm_monument` container in the origin state and expands `building_grand_monument`'s level to the new combined grandeur without discarding the returned artifact's identity.
- National effects (prestige, cultural pull, Armed Forces approval) continue to aggregate across all monuments in the realm.

**Tech Stack:** Paradox Clausewitz script (Victoria 3 1.14.5), `.gui`, customizable localization, Python `unittest` (`test_grand_monument_registry.py`, `test_grand_monument_trophies.py`).

**Spec:** `docs/superpowers/archive/specs/2026-10-13-multiple-monuments-per-state-design.md` on `docs/superpowers/archive/specs/2026-10-12-grand-monument-loot-and-1836-trophies-design.md`.

---

## Global Constraints

- **Engine 1-building rule:** The engine allows only **one** `building_grand_monument` per state. Multiple monuments in a state share this building, scaling its level to their combined grandeur (`max = 200`).
- **PM inheritance:** The state's `building_grand_monument` runs the active PM of the **primary** monument (`gm_mon_is_primary = yes`). If the primary monument is removed or looted, the largest remaining monument becomes primary and its PM is activated.
- **Trophy containers:** Trophies abroad remain `gm_trophy` containers in global list `gm_trophies`. Repatriated distinct monuments transition to `gm_monument` containers in the state's `gm_monuments_here`.
- **Single-monument backward compatibility:** States with only 1 monument mirror container properties into state variables (`gm_grandeur`, `gm_skin`, `gm_form`, `gm_landmark`, `gm_name`) so existing triggers and modifiers continue to function seamlessly.
- **Formatting & Style:** Brace files use tabs; exactly one UTF-8 BOM on `.txt` and `.gui`. Localization keys go into `localization/english/te_miscellaneous_l_english.yml` and are sorted via `python3 organize_loc.py`.
- **Python / CI:** Local Python 3.12, CI also runs 3.11. All tests must pass `python3 -m unittest discover -s . -p 'test_*.py'` and `.venv/bin/ruff check .`.

---

## Review Focus

1. **Building level resizing:** When adding, returning, or looting a monument, the recalculation of `building_grand_monument` must be clamped between 1 and 200, matching the construction ladder's reach.
2. **PM preservation:** Returning a trophy of a different dedication (e.g. a civic obelisk to a state whose primary monument has a crown dedication) must not overwrite the primary monument's active PM.
3. **Occupation looting target:** When occupying a state with multiple monuments, the player and AI must be able to loot each monument independently without wiping the other monuments in the state.
4. **List rebuilding after civil war:** Civil war winners inherit variables but no variable lists. The monthly pass (`gm_trophy_monthly` / `gm_monument_monthly`) must rebuild `gm_monuments_here` from active containers.
5. **No double-counting in national aggregation:** National grandeur curves (`gm_curve_steps_f5`) must sum individual monument grandeur once, whether read from containers or state totals.

---

## File Map

| File | Responsibility |
|---|---|
| `docs/superpowers/archive/specs/2026-10-13-multiple-monuments-per-state-design.md` | Core architecture, lifecycle diagrams, decisions |
| `docs/superpowers/archive/plans/2026-10-13-multiple-monuments-per-state.md` | This implementation plan |
| `common/scripted_effects/gm_effects.txt` | Monument container synchronization, combined grandeur recalculation |
| `common/scripted_effects/gm_trophy_effects.txt` | Refactor `gm_state_tr_receive` and `gm_tr_take` for multi-monument states |
| `common/scripted_triggers/monument_triggers.txt` | Triggers for multi-monument detection, piece vs distinct landmark check |
| `common/script_values/gm_values.txt` | Script values for combined grandeur, monument count per state |
| `gui/te_state_panel_widgets.gui` | Multi-monument display layout in state panel |
| `gui/gm_trophy_widgets.gui` | Per-monument Carry It Off and display widgets |
| `gui/grand_monuments_widget.gui` | "Our Monuments" list container iteration |
| `test_grand_monument_registry.py` | Unit tests for landmark registry and multi-monument state handling |
| `test_grand_monument_trophies.py` | Unit tests for trophy repatriation to multi-monument states |

---

## Tasks

- [ ] ### Task 1: Data Model & State Monument Container Synchronization
  **Files:** `common/scripted_effects/gm_effects.txt`, `common/scripted_triggers/monument_triggers.txt`, `common/script_values/gm_values.txt`, `test_grand_monument_registry.py`.
  - Define `gm_monument` container structure: `gm_mon_landmark`, `gm_mon_skin`, `gm_mon_form`, `gm_mon_picture_code`, `gm_mon_dedication`, `gm_mon_grandeur`, `gm_mon_name`, `gm_mon_built_by`, `gm_mon_is_primary`.
  - Add scripted effect `gm_state_sync_monuments`: walks `gm_monuments_here` on the state, computes total grandeur `gm_state_grandeur = sum(gm_mon_grandeur)`, and sets `building_grand_monument` level via `te_construction_market_build_specified_level`.
  - For states with a legacy single monument and no containers: automatically initialize a primary `gm_monument` container mirroring state variables on monthly pulse.
  - Script value `gm_state_monument_count`: returns the number of monuments standing in the state.
  - Unit tests: verify single-monument sync, container variable integrity, and total grandeur calculation.

- [ ] ### Task 2: Building Level and Production Method Management
  **Files:** `common/scripted_effects/gm_effects.txt`, `common/scripted_effects/gm_commission_effects.txt`.
  - Ensure `building_grand_monument` level equals `gm_state_grandeur` (clamped to 1–200).
  - Production method handling:
    - Primary monument sets active dedication PM (`pm_grand_monument_<dedication>`).
    - If the primary monument is removed or looted, identify the next largest monument container in `gm_monuments_here`, tag it `gm_mon_is_primary = yes`, and activate its PM.
  - Ensure commission completion (`gm_com_fulfil`) adds grandeur to the commissioned monument container and invokes `gm_state_sync_monuments`.
  - Unit tests: test building level scaling when adding/removing secondary monuments, and PM fallback when the primary is removed.

- [ ] ### Task 3: Trophy Repatriation & Homecoming Refactor
  **Files:** `common/scripted_effects/gm_trophy_effects.txt`, `test_grand_monument_trophies.py`.
  - Refactor `gm_state_tr_receive`:
    - **Piece/Token match:** Check `scope:gm_tr_moving.var:gm_tr_landmark = var:gm_landmark` and `scope:gm_tr_moving.var:gm_tr_share != flag:whole`. If matched, add levels to the matching landmark, increase total grandeur, and destroy the trophy container.
    - **Distinct Monument / Whole artifact:** If the trophy represents a distinct landmark (e.g. Luxor Obelisk or Temple of Dendera in Upper Egypt, or Piraeus Lion in Attica), create a new `gm_monument` container in the origin state preserving all trophy records (skin, form, landmark, name, picture, grandeur). Add container to `gm_monuments_here`.
    - Invoke `gm_state_sync_monuments` to resize `building_grand_monument` to the combined grandeur.
    - Apply The Homecoming boon (+5 legitimacy for 10 years) and relations improvement as before.
  - Unit tests: test returning Luxor Obelisk to Upper Egypt with Obelisks of Karnak present; assert both exist as distinct monuments, total grandeur equals 10, and both retain their names and pictures.

- [ ] ### Task 4: Looting & Occupation in Multi-Monument States
  **Files:** `common/scripted_effects/gm_trophy_effects.txt`, `common/scripted_guis/gm_trophy_sguis.txt`, `gui/gm_trophy_widgets.gui`.
  - Update `gm_tr_take` to operate on a targeted `gm_monument` container (`scope:gm_mon`).
  - If a specific monument in the state is carried off:
    - Reduce that monument's grandeur (or remove container if whole).
    - Create `gm_trophy` container in the occupier's capital.
    - Invoke `gm_state_sync_monuments` to shrink `building_grand_monument` by the taken levels.
    - Other monuments in `gm_monuments_here` remain untouched.
  - Scripted GUI `gm_tr_take_monument_sgui`: validates occupation and eligibility per monument container.
  - Unit tests: test occupying Upper Egypt and looting Luxor Obelisk; verify Karnak remains unaffected, building shrinks by 5 levels, and Luxor Obelisk lands in the occupier's capital as a trophy.

- [ ] ### Task 5: State View User Interface Pass
  **Files:** `gui/te_state_panel_widgets.gui`, `localization/english/te_miscellaneous_l_english.yml`.
  - In `te_state_gm_card`:
    - When `gm_state_monument_count == 1`: preserve the clean single-monument layout.
    - When `gm_state_monument_count > 1`: render a multi-monument flow:
      - Header: combined grandeur meter and aggregated state tourism/local effects.
      - Container list: iterate over `gm_monuments_here`, rendering a compact row per monument (picture icon, title, form, dedication, individual grandeur, and landmark tooltip).
      - During enemy occupation: show "Carry It Off" button on each eligible monument row.
  - Add tooltips explaining combined building level and individual monument contributions.
  - Offline GUI linting via `python3 scripts/analysis/check_gui_lint.py`.

- [ ] ### Task 6: Our Monuments & Journal Entry Window Pass
  **Files:** `gui/grand_monuments_widget.gui`, `localization/english/te_miscellaneous_l_english.yml`.
  - In the "Our Monuments" section of `je_grand_monuments`:
    - Iterate over country monument containers (or list states with monuments, expanding co-located monuments).
    - Ensure every distinct monument/landmark is visible with its own picture and attributes.
  - Verify sorting and status indicators for contested, heritage, or normal status.

- [ ] ### Task 7: Seeding 1836 Co-located Landmarks & Historical Opportunities
  **Files:** `common/scripted_effects/gm_landmark_effects.txt`, `docs/superpowers/archive/specs/2026-10-12-grand-monument-loot-and-1836-trophies-design.md`.
  - Enable co-located landmarks in 1836 seeding where appropriate without building collisions.
  - Ensure Upper Egypt starts with Obelisks of Karnak, while repatriated Luxor Obelisk and Temple of Dendera integrate smoothly upon return.
  - Document expansion path for future landmarks (e.g. Rome, Beijing, Athens).

- [ ] ### Task 8: Verification, Audits & Player Guide Update
  **Files:** `docs/player_guide/02-timeline.md`, `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`, `docs/systems/mod_systems.md`.
  - Run full test suite: `python3 -m unittest discover -s . -p 'test_*.py'`.
  - Run linter and formatting: `.venv/bin/ruff check .`, `python3 organize_loc.py --check`, `python3 scripts/format_paradox_tabs.py --check`.
  - Run audits: `loc_coverage_audit.py --strict`, `gui_reference_audit.py --strict`.
  - Update Player Guide: describe co-located monuments and returning artifacts to states with existing landmarks; rebuild PDF via `scripts/build_player_guide.py`.
