# Open Issues

A running log of known bugs, suspicious patterns, incomplete features, and tech-debt notes discovered during code review. Items are grouped by severity. Add new items at the top of their section with a date stamp when they are discovered.

Last full review: 2026-04-24 (during Strategic Reserve System implementation).
Last cleanup pass: 2026-05-04 (M4 verified clean and a regression audit added; M5 statistics-mod log filter landed).
Last project-wide review: 2026-09-10 (static review without a game install: script-layer read, server/parser code review, docs-vs-tree drift, asset + test + lint sweeps). New items carry a 2026-09-10 stamp. Entries that review found already stale: M_NEW2 #4 (done by `orphaned_event_audit.py`), L2 (`je_decline_of_religion.txt` no longer exists), L5 (covered by `effect_trigger_validity_audit.py`), L1/L3 (scripts moved under `scripts/image_pipeline/` and `scripts/generators/`), L8 (`tooltip.gui:231` is now `:293`).

---

## HIGH

_(no open HIGH items — H1–H3 from the 2026-09-10 review were fixed 2026-09-12)_

---

## MEDIUM

### Ticketed 2026-09-12 — items M6–M14 / L18–L22 from the 2026-09-10 review moved to GitHub issues
Detail lives on the issues; this tracker only keeps the pointer so the review header stays meaningful.

| Review item | Issue |
|---|---|
| M6 parser: `!=`/`?=` dropped, operator overwrite on repeated keys, duplicate collapse, dup top-level key aborts file | #241 |
| M7 `/reload`: crashing generator never reaches `warnings`; writers run after the parse | #242 |
| M8 `path_constants` eager resolution blocks audits/tests without the game | #243 |
| M9 red tests: stale `test_pm_costs` assertion, unconditional PIL import | #244 |
| M10 `format_paradox_tabs.py` is Python 3.12-only | #245 |
| M11 724 MB of uncompressed textures, 318 MB unreferenced `backup_originals/` | #246 |
| M12 no CI, `.github/` gitignored | #247 |
| M13 docs drift sweep | #248 |
| M14 anchor slug rule / registry cache key | #249 |
| Suggestion: iterator-`limit` and multiplier-variable parse-time audits | #250 |
| L18 pulse-wiring leftovers | #251 |
| L19 stray tracked files from the import commit | #252 |
| L20 `ruff --select F` findings | #253 |
| L21 server hardening nits | #254 |
| L22 packaging nits | #255 |

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
**File:** [gui/tooltip.gui:293](../gui/tooltip.gui#L293)

**Problem:** Mod's scrollable `FancyTooltipWidgetType` uses `scrollbar_vertical = { using = vertical_scrollbar }` — the same exact pattern vanilla uses successfully in `block_windows.gui` and `building_browser_panel.gui`. The engine emits `gui/tooltip.gui:293 - Could not find template 'vertical_scrollbar'` (source `pdx_gui_factory.cpp:628`) once at type registration. Likely a parse-time false-positive resolved in pass-2; scrollable tooltips render correctly in-game. Filtered from log triage via `docs/audits/mod_known_noise.md`.

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

### L13. Mod event override duplicate-event-ID notices
**Files:** `events/te_formation_overrides.txt:21` (vs vanilla `events/misc_unifications.txt:1042`)

**Problem:** Overriding vanilla `formation.17` logs `Duplicated event ID 'formation.17' found. New Location: 'events/misc_unifications.txt:1042', Previous Location: 'events/te_formation_overrides.txt:21'` once per launch. Benign **because the mod file is `Previous`** — the engine keeps `Previous` and rejects `New`, so the mod's copy wins (see the 2026-05-24 log-triage lesson). Only investigate if a future entry shows the **mod** file as `New`.

**Fix:** None needed while the override is intentional; delete this entry if `te_formation_overrides.txt` is ever retired.

### L14. GUI-injected event targets flagged never-set
**Files:** `common/script_values/gui_chart_script_values.txt`, `gui/market_panel.gui`

**Problem:** The market-panel trade charts inject `base_market` via `GuiScope…AddScope('base_market', …)` and read it as `scope:base_market` inside script values. The parse-time validator can't see GUI `AddScope` calls, so it logs `Event target 'base_market' is used but is never set` once per launch. The chart works (documented at `gui_chart_script_values.txt:60-62`).

**Fix:** None possible script-side — the scope genuinely is set only from GUI data context.

### L15. Vanilla principles orphaned by REPLACE:principle_group overrides
**Files:** `common/power_bloc_principle_groups/extra_power_bloc_principle_groups.txt:173`

**Problem:** `REPLACE:principle_group_sacred_civics` swaps the group's member list to the mod's `principle_sacred_civics_N_mod` variants, leaving vanilla `principle_sacred_civics_1..N` in the database but in no group → `Principle principle_sacred_civics_1 is not part of any group` once per launch. Harmless: group-less principles are unpickable.

**Fix:** None needed — inherent to the REPLACE-group pattern. Same applies to any future `REPLACE:principle_group_*` that drops vanilla members.

### L16. Historical law seeding vs `unlocking_technologies` retention warnings (1.13.9+)
**Files:** `common/history/extra_history.txt`, `common/laws/extra_laws.txt` (lawgroup file order)

**Problem:** Vanilla 1.13.9 added a load-time validation that logs `Country <TAG> is not permitted to retain law <Name>` for every country holding a law whose `unlocking_technologies` it lacks. Two mod cases, both warning-only:

1. **Init-order noise (158 countries × 3 laws):** the mod's lawgroups list laws in progressiveness/menu order, so the tech-gated late-era law sits first in `lawgroup_privacy_rights` / `lawgroup_rules_of_war` / `lawgroup_right_to_information`. At country init the engine auto-assigns the **first law in the group** to every unseeded country and the new validation logs it — then `extra_history.txt` GLOBAL (`every_country`, "executed last among all history") activates the intended tech-free baselines (`law_minimal_privacy_protection`, `law_traditional_rules_of_war`, `law_informal_government_secrecy`). Final game state is correct; the warnings describe a transient. Keeping file order is deliberate (menu ordering).
2. **Deliberate historical seeds (~36 pairs):** GBR on Gold Standard since 1821, Prussian Kriegsministerium 1808, Statute of Anne 1710, north-German Civic Monolingualism, colonial-slavery seeds, … — history flavor trumps tech gates. Countries keep the law (they can never lose a tech requirement they never had).

**Fix:** By design; keep. If a *new* law name appears in these warnings that matches neither class, investigate instead of assuming noise.

### L17. Strategic-reserve silo missing-texture warning (unresolved)
**Files:** `common/buildings/strategic_reserve.txt:61`

**Problem:** `Database type building_strategic_reserve_silo has missing texture` (guitexturehandler.h:155) once per launch. The building's `icon` points at a vanilla dds that exists; the missing texture is some other UI slot (map/entity/background) not yet identified. Cosmetic — panels render with fallback art.

**Fix:** Unresolved; next investigation step is comparing against a warning-free mod building's full gfx surface (icon + any `city_gfx`/entity/asset references) to find the queried-but-missing slot.

---

## Vanilla 1.13.7 patch impact (2026-05-27)

Verify+flag pass after vanilla released **1.13.7**. The patch is overwhelmingly vanilla-internal (AI fleet logic, naval balance, Japan/USA content, bugfixes); the mod does not override Japan, USA decisions, tolls, treaty articles, or vanilla canals, so most of it needs no action. The real overlap is the **naval domain**.

### Verified safe (no action)
- **Map data absorbed via regen.** `map_data/state_regions/*.txt` are regenerated by `resources.py` (post-load chain) from the live 1.13.7 vanilla files, so map changes flow in for free. Confirmed: `POST /reload` flipped `STATE_SAKHALIN` `arable_resources` to `building_livestock_ranch` (`arable_land = 10`) — exactly the patch's "Fixed Sakhalin having no arable resources." Homelands (Cherokee/Caddoan/Muskogean) and Sinai/Suez province borders live in `history/`/the map bitmap, which the mod doesn't override, so they apply directly.
- **Sovereign Empire INJECT intact.** Patch made Social Monarchy valid for Sovereign Empire blocs; verified `power_bloc_leader_can_make_subjects_bool = yes` still present in `identity_sovereign_empire` (1.13.7), so `common/power_bloc_identities/te_subjugation_identity_overrides.txt` is safe.
- **New modding hooks obsolete nothing here.** Mod has no `can_queue_building_levels` usage and no effect-based maneuver workaround, so `add_maneuvers` / script-value queue changes don't enable any cleanup.
- **No tracked vanilla bugs to retire.** None of the 1.13.7 bugfixes (Sakhalin arable, Kuril/Alaska transfer, Feijó immortality, etc.) were tracked in `docs/vanilla/vanilla_known_bugs.md`.

### Pending verification gate — RESOLVED 2026-07-03
- ~~Engine-doc modifier surface is stale.~~ Resolved by the 1.13.9 migration (commit 2de1c4c): a fresh vanilla-pure `script_docs` dump from the live 1.13.9 game now lives at `~/src/vic3-docs-snapshots/1.13.9/` (`vanilla_snapshot_docs_path` in `paths.local.json`), and the breakage gate ran clean against it (0 unknown / 0 suspicious). Banners bumped to 1.13.9.

### Flagged for follow-up (GitHub issues — naval balance / design)
- **#161** — re-tune mod ship accuracy/speed/visibility for the new hit-chance model (accuracy vs speed+visibility; torpedo craft now fastest).
- **#162** — re-check the 6 mod utility modules (AI weights + usefulness) after vanilla's utility-module pass + AI slot-weighting change.
- **#163** — re-anchor mod blockade strength/resistance to the new `strength / total resistance` formula and rebalanced values.
- **#160** — add `fleet_compositions` so the new role-based AI actually fields the mod's 20+ modern ship types.
- **#164** — verify `merchant_marine` good economy after port-connection / goods-transfer cost cuts (canal companies + late-era PMs).
- **Minor (note only, no issue):** tolls halved + 6-month toll/strait cooldown make the mod's strait-control fortification PMs (`pm_naval_fortification_*` with `state_control_strait_bool`) marginally less rewarding; no balance dependency.

---

## Vanilla 1.13.9 "Matcha" migration (2026-07-03)

Full correctness pass for the cumulative 1.13.6–1.13.9 bump (commit 2de1c4c), per the runbook. Two engine-silent breakage classes found by the modifier-type-definitions name diff and fixed:

- **`country_law_enactment_time_mult` → `country_law_enactment_speed_mult`** with sign flip (4 sites; per-law variants also renamed, unused by mod).
- **Harvest-condition modifier deregistration**: 1.13.9 removed the `state_harvest_condition_{hailstorm,torrential_rains}_*` modifier *types* while keeping the conditions; the mod's global-warming lines silently no-opped. Re-registered in `global_warming_modifier_types.txt`.

Verified safe: all 55 mod define overrides exist in 1.13.9; no use of removed `days_obsolete` trigger or tobacco-export-tariff modifiers; all 66+6 vanilla loc keys the mod shadows are string-identical in 1.13.9; company INJECTs (append-only) preserve vanilla's 1.13.7/1.13.9 requirement changes (Rheinmetall, Fundição Ipanema, Witkowitzer); `migration_pull` engine docs unchanged → `te_map_mode_*` stays dormant. 13 GUI overrides re-merged (closes #208). #160's fleet_compositions verdict (ship_group-keyed, no change needed) re-verified against 1.13.9.

Follow-ups filed as GitHub issues: naval rebalance for 1.13.9's capital-ship/gun-module/crit changes; capacity-cost modifier migration; new-primitive adoption (variable maps, movement defeat, `should_target_state_in_unification_play`).

---

## Policy

- When fixing any item above, delete it from this file in the same PR.
- If a fix is partial, leave the entry but add a note describing what was done and what remains.
- New issues discovered during unrelated work should be appended here rather than silently left in the code.