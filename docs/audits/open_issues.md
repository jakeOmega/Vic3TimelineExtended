# Open Issues

A running log of known bugs, suspicious patterns, incomplete features, and tech-debt notes discovered during code review. Items are grouped by severity. Add new items at the top of their section with a date stamp when they are discovered.

Last full review: 2026-04-24 (during Strategic Reserve System implementation).
Last cleanup pass: 2026-05-04 (M4 verified clean and a regression audit added; M5 statistics-mod log filter landed).

---

## HIGH

*(None outstanding.)*

---

## MEDIUM

### M_NEW2. Deferred event-tooling categories (#2-#4)
**Tooling:** `event_magnitude_audit.py` covers category #1 of a four-part event-quality plan (work landed 2026-05-04, see `docs/engine/event_magnitude_report.md`). Three categories still TODO:

- **#2 Pulse-event narrative drift.** Flavor events fired from `on_yearly_pulse` / `on_monthly_pulse` narrate game actions the player didn't take (e.g. a `events/un_events.txt` veto-flavor event that fires regardless of whether the player used a veto). Tooling needed: scan event localization for action-implying tokens, cross-reference event triggers for matching game-state checks, flag drift.
- **#3 Event-chain invisibility.** Backfires/sequels don't surface their precursor to the player (e.g. `international_relations_events.106` "The Narrative Turns" is a backfire of `international_relations_events.4` Option A but reads as orphan to the player). Tooling needed: build event-chain graph; for events with predecessors, check whether the description references the prior choice and otherwise prepend a contextual reminder.
- **#4 Orphan event-bug detection.** Events meant to fire mechanically but never wired anywhere. Tooling needed: list events that appear in no `trigger_event` call and no `random_events` pool, then cross-reference against titles/descriptions to identify which are mechanically required vs intentionally pulse-only.

Each round should reuse the audit + inline-`# REVIEWED YYYY-MM-DD: rationale` suppression pattern established for category #1.

### M3. Missing unique icon for space-race phase 6
**File:** [common/production_methods/extra_pms.txt#L15745](../common/production_methods/extra_pms.txt#L15745)

**Problem:** `# TODO: needs unique p6 icon` — the phase-6 rocket PM reuses the phase-5 icon. Cosmetic, but phase 6 is the final achievement and deserves its own art.

**Fix:** Generate a new icon via `gen_image.py` or the `gen_pm_icons.py` pipeline and swap the texture path. Non-urgent.

---

## LOW

### L1. Bare `except Exception:` in Python generators
**File:** [convert_event_image.py#L78](../convert_event_image.py#L78) (and L185, L190), [generate_event_images.py](../generate_event_images.py)

**Problem:** Broad except clauses hide the actual error type. When a batch image job fails, it reports "failed" with no indication whether it was a network error, disk error, or model error.

**Fix:** Narrow to `except (IOError, OSError, RuntimeError, requests.RequestException):` and log the exception class. Trivial.

### L2. Design-note TODO in JE gating
**File:** [common/journal_entries/je_decline_of_religion.txt#L52](../common/journal_entries/je_decline_of_religion.txt#L52)

**Problem:** `# TODO: could also gate on total secularization / state atheism`. Design note, no behavioral bug.

**Fix:** Either implement the additional gate or delete the TODO. Trivial.

### L3. Generator template leaves TODO placeholders in output
**File:** [gen_event.py#L391-L399](../gen_event.py#L391)

**Problem:** The event scaffolding template emits `title = "TODO: Event Title"`-style placeholders. Expected for a scaffolding tool, but worth a reminder that any generated event must have its placeholders filled before shipping.

**Fix:** No code change needed. Consider adding a post-generation lint that greps generated events for `TODO:` and warns. Nice-to-have.

### L5. Scripted-effect-invocation false-positive audit
**Across:** repo-wide

**Problem:** No formal tool checks that every `foo = yes` call in a script body resolves to a defined `scripted_effect`. A typo like `sr_monthly_updatte_effect = yes` would silently do nothing.

**Fix:** Extend `mod_state_server.py` with an endpoint that cross-references scripted-effect invocations against definitions. Medium complexity; useful for the whole mod.

### L6. `PMG name =` override used in some older PMs
**File:** various (minor)

**Problem:** Some PMGs use `name = "UPPERCASE_LOC_KEY"` overrides instead of relying on the default id-based loc key. Not a bug, but inconsistent with the mod's prevailing convention and makes loc harder to find.

**Fix:** Standardize on id-based loc keys over time. Not urgent.

### L7. Mod harvest-condition sound-entity states missing
**File:** `gfx/models/environment/` (mod-side `.asset` override does not exist yet)

**Problem:** `common/harvest_condition_types/extra_harvest_condition_types.txt` defines `bull_market` / `bear_market` / `market_downturn` / `financial_panic`, but `harvest_condition_sound_entity` (in vanilla `gfx/models/environment/harvest_conditions.asset`) has no corresponding states. Engine emits `Couldn't find any animation state for harvest condition type 'bull_market'` (etc.) once per condition activation, source `harvest_condition_graphics.cpp:52`. Functional impact: silent — engine just doesn't play a sound. Filtered from log triage via `docs/audits/mod_known_noise.md`.

**Fix:** Add a mod-side `.asset` file (e.g. `gfx/models/environment/harvest_conditions_extra.asset`) with ~16 silent-sound state entries (4 intensity levels × 4 mod conditions), modelled on vanilla `harvest_condition_sound_entity` entries like `drought_1`. Verify in-game by activating the conditions in a test save and watching `game.log` for the warning to disappear.

### L8. Mod tooltip.gui vertical scrollbar template warning
**File:** [gui/tooltip.gui:231](../gui/tooltip.gui#L231)

**Problem:** Mod's scrollable `FancyTooltipWidgetType` uses `scrollbar_vertical = { using = vertical_scrollbar }` — the same exact pattern vanilla uses successfully in `block_windows.gui` and `building_browser_panel.gui`. The engine emits `gui/tooltip.gui:231 - Could not find template 'vertical_scrollbar'` (source `pdx_gui_factory.cpp:628`) once at type registration. Likely a parse-time false-positive resolved in pass-2; scrollable tooltips render correctly in-game. Filtered from log triage via `docs/audits/mod_known_noise.md`.

**Fix:** Investigate why vanilla's identical syntax doesn't trigger the warning while the mod's use does. Candidate angle: the surrounding `type FancyTooltipWidgetType = container { ... }` declaration may differ from the vanilla `type default_popup = window { ... }` used by `block_windows.gui` in a way that affects template resolution timing. If a syntactic change silences it, apply; otherwise leave filtered.

---

## Policy

- When fixing any item above, delete it from this file in the same PR.
- If a fix is partial, leave the entry but add a note describing what was done and what remains.
- New issues discovered during unrelated work should be appended here rather than silently left in the code.