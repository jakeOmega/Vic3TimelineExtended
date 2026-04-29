# Open Issues

A running log of known bugs, suspicious patterns, incomplete features, and tech-debt notes discovered during code review. Items are grouped by severity. Add new items at the top of their section with a date stamp when they are discovered.

Last full review: 2026-04-24 (during Strategic Reserve System implementation).
Last cleanup pass: 2026-04-25 (H1 covert warfare scope pattern; M1 SR var cleanup; M2 unused fund_resistance action; L4 scratch file).

---

## HIGH

*(None outstanding.)*

---

## MEDIUM

### M3. Missing unique icon for space-race phase 6
**File:** [common/production_methods/extra_pms.txt#L15745](../common/production_methods/extra_pms.txt#L15745)

**Problem:** `# TODO: needs unique p6 icon` — the phase-6 rocket PM reuses the phase-5 icon. Cosmetic, but phase 6 is the final achievement and deserves its own art.

**Fix:** Generate a new icon via `gen_image.py` or the `gen_pm_icons.py` pipeline and swap the texture path. Non-urgent.

### M4. `kill_character` in events may lack `exists` guards
**Files:** `events/**` (35 occurrences total)

**Problem:** Spot-check of `space_race_colony_events.txt` shows `kill_character = scope:flavor_speaker` in `after` blocks that don't appear to be wrapped in `exists = scope:flavor_speaker` guards. Per the mod's own gotcha list, event characters without `place_character_in_void = 6` can be garbage-collected by the engine, invalidating the scope ~20 days into an open event.

**Fix:** Audit every `kill_character` in `events/`. For each, confirm either (a) the character was created with `place_character_in_void = 6`, **or** (b) the kill is wrapped in `if = { limit = { exists = scope:X } ... }`. Mechanical but tedious — at least an hour of focused work.

### M5. Statistics workshop mod flooding error.log
**File:** external dependency (Statistics mod, `statistics_effects.txt:1350`)

**Problem:** 1800+ "Division/modulo by zero" entries per session drown out genuine mod errors. Not our code, but impacts debuggability.

**Fix:** Add a `debug.log` / `error.log` filter to `mod_state_server.py` or the Python tools that excludes entries from `statistics_effects.txt` by default. Small Python patch.

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

---

## Policy

- When fixing any item above, delete it from this file in the same PR.
- If a fix is partial, leave the entry but add a note describing what was done and what remains.
- New issues discovered during unrelated work should be appended here rather than silently left in the code.