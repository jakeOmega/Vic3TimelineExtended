# Open Issues

A running log of known bugs, suspicious patterns, incomplete features, and tech-debt notes discovered during code review. Items are grouped by severity. Add new items at the top of their section with a date stamp when they are discovered.

Last full review: 2026-04-24 (during Strategic Reserve System implementation).
Last cleanup pass: 2026-05-04 (M4 verified clean and a regression audit added; M5 statistics-mod log filter landed).

---

## HIGH

_(no open HIGH items)_

---

## MEDIUM

### M_NEW2. Deferred event-tooling categories (#2-#4)
**Tooling:** `event_magnitude_audit.py` covers category #1 of a four-part event-quality plan (work landed 2026-05-04, see `docs/engine/event_magnitude_report.md`). Three categories still TODO:

- **#2 Pulse-event narrative drift.** Flavor events fired from `on_yearly_pulse` / `on_monthly_pulse` narrate game actions the player didn't take (e.g. a `events/un_events.txt` veto-flavor event that fires regardless of whether the player used a veto). Tooling needed: scan event localization for action-implying tokens, cross-reference event triggers for matching game-state checks, flag drift.
- **#3 Event-chain invisibility.** Backfires/sequels don't surface their precursor to the player (e.g. `international_relations_events.106` "The Narrative Turns" is a backfire of `international_relations_events.4` Option A but reads as orphan to the player). Tooling needed: build event-chain graph; for events with predecessors, check whether the description references the prior choice and otherwise prepend a contextual reminder.
- **#4 Orphan event-bug detection.** Events meant to fire mechanically but never wired anywhere. Tooling needed: list events that appear in no `trigger_event` call and no `random_events` pool, then cross-reference against titles/descriptions to identify which are mechanically required vs intentionally pulse-only.

Each round should reuse the audit + inline-`# REVIEWED YYYY-MM-DD: rationale` suppression pattern established for category #1.

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

### L9. Mod DDS dimensions: historical-company icons
**Files:**
- `gfx/interface/icons/company_icons/historical_company_icons/japanese_toyota.dds`
- `gfx/interface/icons/company_icons/historical_company_icons/korean_samsung.dds`
- `gfx/interface/icons/company_icons/historical_company_icons/american_google.dds`
- `gfx/interface/icons/company_icons/historical_company_icons/russian_rosatom.dds`

**Problem:** Block-compressed (BC1/BC3) DDS textures need width and height that are multiples of 4. These four historical-company icons fail that constraint and emit `Block compressed texture '…' does not have a height and width that are a multiple of 4, which will cause edge pixels to be …` warnings (source `gfx_dds_loader.cpp:442`) once per file at load. Visual-only — engine still loads the texture; only effect is potential edge-pixel artifacts in the company-icon UI. Filtered from log triage via `docs/audits/mod_known_noise.md`.

**Fix:** Re-export each file through the mod's image pipeline (`scripts/image_pipeline/`) at multiple-of-4 dimensions and overwrite. Verify warning count drops to 0 via `curl -s "http://localhost:8950/logs/debug?summary=true"` after the next launch.

### L10. Mod loc-only variables flagged unused
**Files:**
- `common/scripted_effects/cultural_hegemony_effects.txt` — `ch_rank_*_{sol,art,prs,tech,raw}` globals
- `common/scripted_effects/nuclear_weapon_effects.txt` — `nuke_rank_*_stockpile` globals
- `localization/english/te_concepts_l_english.yml` — `[GetGlobalVariable('…').GetValue]` reads

**Problem:** Mod uses `set_global_variable` to expose per-rank breakdown values (cultural-hegemony component scores, nuclear stockpiles) to tooltip text via `GetGlobalVariable('ch_rank_N_sol')` etc. in concept tooltips. The engine explicitly tracks variable reads but notes "use in localization doesn't count due to technical limitations," emitting `Variable 'X' is set but is never used` (source `jomini_effect.cpp:1135`) once per variable at load. Filtered from log triage via `docs/audits/mod_known_noise.md`.

**Fix:** Re-architect the affected loc tooltips to compute their values from script values (which the engine tracks correctly) rather than globals exposed for read. Large refactor with no functional gain; deferred until the wider concept-tooltip system gets revisited. Or, if the engine ever adds loc-read tracking, this self-resolves.

### L11. Banking-cycle JE title custom-loc scope-validation burst
**Files:**
- `common/customizable_localization/zzz_extra_custom_loc.txt:1` — `te_banking_cycle_title` (`type = country`)
- `localization/english/te_journal_entries_l_english.yml:11` — `je_banking_cycle:0 "[GetPlayer.GetCustom('te_banking_cycle_title')]"`

**Problem:** The Banking Cycle JE name uses `[GetPlayer.GetCustom('te_banking_cycle_title')]` to vary the title by economic law ("Boom & Bust Cycle" / "Logistics & Allocation Gauge" / "Cooperative Finance Dashboard"). The title **renders correctly in-game**, but the engine emits `Object of type 'country' is not valid for 'te_banking_cycle_title'` (source `jomini_custom_text.h:91`) — measured at ~83 writes in a single ~1-second burst per panel render (error.log only, 0 in debug.log). No visual or gameplay effect; the only cost is a brief one-time hitch of synchronous error-log writes when the JE panel renders. Vanilla never uses `GetCustom` in a JE-name loc; the likely cause is that the JE name renders in a `journal_entry` data context that validates the country-typed `GetCustom` against the call-site rather than `GetPlayer`'s return. Filtered from log triage via `docs/audits/mod_known_noise.md`.

**Fix (deferred — user opted to keep the dynamic title):** match the JE render context's scope chain instead of `GetPlayer` (e.g. resolve the country from the `journal_entry` scope), or convert the law-conditional title to a non-`GetCustom` mechanism. Requires in-game iteration to find the accessor that resolves cleanly — not worth it for a cosmetic per-render burst unless the hitch ever becomes noticeable.

### L12. Script-only modifier types emit "defined in script but not in code" (by-design)
**Files:** `common/modifier_type_definitions/*.txt` (~120 mod-defined modifier types across covert_warfare, space_race, mod_entity, banking, strategic-reserve, pb-principles, etc.)

**Problem:** Every mod-defined modifier type that no engine *code* system consumes emits `Modifier type definition X is defined in script but not in code, it should either be added to code or removed` (source `modifier_type_definition_database.cpp:43`) once at load — ~120 entries. **Verified benign (2026-05-24):** these are script-only modifier types, the same construct as vanilla's `00_modifier_types/03_modifier_types_script_only.txt`. They are recognized by `/modifier-search` (e.g. `country_intelligence_capacity_add` → entity_count 42), pass `modifier_visibility_audit`, are applied via `static_modifiers`/techs, and are read via `modifier:X` in script values (`space_race_values.txt:70`, `covert_warfare_script_values.txt:50`, `extra_effects.txt:1142`). The warning only notes they have no engine-code reader — correct for script-side custom modifiers. Filtered from log triage via `docs/audits/mod_known_noise.md`.

**Fix:** None needed — unfixable without deleting the modifiers (which would break the systems that use them). Documented here only to satisfy the noise-registry cross-reference and so a future triage doesn't re-investigate. The signature `is defined in script but not in code` is specific to this benign case; a genuinely-invalid modifier is caught at parse time by `modifier_visibility_audit`, not this runtime warning.

---

## Vanilla 1.13.7 patch impact (2026-05-27)

Verify+flag pass after vanilla released **1.13.7**. The patch is overwhelmingly vanilla-internal (AI fleet logic, naval balance, Japan/USA content, bugfixes); the mod does not override Japan, USA decisions, tolls, treaty articles, or vanilla canals, so most of it needs no action. The real overlap is the **naval domain**.

### Verified safe (no action)
- **Map data absorbed via regen.** `map_data/state_regions/*.txt` are regenerated by `resources.py` (post-load chain) from the live 1.13.7 vanilla files, so map changes flow in for free. Confirmed: `POST /reload` flipped `STATE_SAKHALIN` `arable_resources` to `building_livestock_ranch` (`arable_land = 10`) — exactly the patch's "Fixed Sakhalin having no arable resources." Homelands (Cherokee/Caddoan/Muskogean) and Sinai/Suez province borders live in `history/`/the map bitmap, which the mod doesn't override, so they apply directly.
- **Sovereign Empire INJECT intact.** Patch made Social Monarchy valid for Sovereign Empire blocs; verified `power_bloc_leader_can_make_subjects_bool = yes` still present in `identity_sovereign_empire` (1.13.7), so `common/power_bloc_identities/te_subjugation_identity_overrides.txt` is safe.
- **New modding hooks obsolete nothing here.** Mod has no `can_queue_building_levels` usage and no effect-based maneuver workaround, so `add_maneuvers` / script-value queue changes don't enable any cleanup.
- **No tracked vanilla bugs to retire.** None of the 1.13.7 bugfixes (Sakhalin arable, Kuril/Alaska transfer, Feijó immortality, etc.) were tracked in `docs/vanilla/vanilla_known_bugs.md`.

### Pending verification gate (not done this session)
- **Engine-doc modifier surface is stale.** The breakage gate (`/validate/engine-coverage?filter=vanilla_breakages`) ran clean (0 unknown / 0 suspicious), **but** the engine-doc snapshot is dated 2026-05-20 — pre-1.13.7. A true 1.13.7 engine-surface check requires launching the 1.13.7 game (so it re-dumps `script_docs`), then `POST /reload?engine_only=true`, then re-running the gate. **`Last verified against vanilla:` banners deliberately left at 1.13.5 until this is done.**

### Flagged for follow-up (GitHub issues — naval balance / design)
- **#161** — re-tune mod ship accuracy/speed/visibility for the new hit-chance model (accuracy vs speed+visibility; torpedo craft now fastest).
- **#162** — re-check the 6 mod utility modules (AI weights + usefulness) after vanilla's utility-module pass + AI slot-weighting change.
- **#163** — re-anchor mod blockade strength/resistance to the new `strength / total resistance` formula and rebalanced values.
- **#160** — add `fleet_compositions` so the new role-based AI actually fields the mod's 20+ modern ship types.
- **#164** — verify `merchant_marine` good economy after port-connection / goods-transfer cost cuts (canal companies + late-era PMs).
- **Minor (note only, no issue):** tolls halved + 6-month toll/strait cooldown make the mod's strait-control fortification PMs (`pm_naval_fortification_*` with `state_control_strait_bool`) marginally less rewarding; no balance dependency.

---

## Policy

- When fixing any item above, delete it from this file in the same PR.
- If a fix is partial, leave the entry but add a note describing what was done and what remains.
- New issues discovered during unrelated work should be appended here rather than silently left in the code.