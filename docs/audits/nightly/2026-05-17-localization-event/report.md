# Nightly audit report — 2026-05-17 (targeted: localization, include=*event*)

## Slice audited

- `localization/english/te_events_l_english.yml` lines 1–600 (~600 lines)

## Prefixes encountered

- `augmentation_events.*`
- `banking_cycle_events.*`
- `covert_warfare.*`
- `cultural_hegemony.*` (partial — runs past line 600)

All four are `event_`-flavored prefixes, matched the heuristic.

## Findings

### 1. Style drift in BC.50–67 and BC.101–170 (consolidated issue)

Three clustered patterns concentrated in the banking_cycle_events central-planning (events 50–57, 101–120) and cooperative (events 60–67, 151–170) subsets. All three suggest the subset was authored in a distinct voice that drifts from the rest of the file. Filed as **one issue** rather than several patches because each pattern hinges on a design-intent question.

#### 1a. Colon-as-em-dash punctuation (~17 instances)

Paired form (`X: Y, Z, W: V…`, ~8 occurrences) at lines 70, 88, 94, 100, 106, 178, 470, 494 — colon used where em-dash would set off a parenthetical insert.

Unpaired form (`X: but/or/until/and Y`, ~9 occurrences) at lines 106, 417, 428, 429, 441, 465, 471, 483, 488, 501 — colon used where em-dash would attach a contrasting clause.

Reference: lines 376, 382, 388, 447, 453 in the same file use em-dash correctly for attribution (`— Broker on the trading floor`), so the inconsistency is within-file, not deliberate house style.

#### 1b. Sub-guideline flavor text length (~14 single-sentence aphorisms)

`docs/guides/event_creation_guide.md` § Flavor Text recommends 3–8 sentences / 50–150 words / dialogue-anchored ("Shorter is not better. Flavor text below this range reads as a news ticker and wastes the slot.").

The BC.50–67 and 154–170 ranges (plus a few in CH.10–13) deliver single-sentence aphoristic flavor instead. Examples: lines 405, 411, 417, 423, 429, 435, 441, 465, 471, 477, 483, 489, 495, 501, 507. The rest of the BC subsystem (~70 events) uses dialogue.

#### 1c. Soviet-specific terminology in command-economy-gated events

`banking_cycle_events.116` and `.117` are gated by `has_law = law_command_economy` (verified in `common/scripted_effects/banking_cycle_effects.txt:336–365`) — so they fire for any country running command economy, not just the Soviet Union. The loc references `Gosplan` (line 100), `Party Secretary` (line 100), and `blat networks` (line 106), all Russian-Soviet-specific terminology. Likely jarring for a command-economy Brazil, India, or Spain. Could be deliberate flavor or could be a rewrite candidate.

**Recommended action:** rewrite the BC central-planning/cooperative cluster (events 50–67 + 101–170) for stylistic consistency with the rest of the file — em-dashes in place of colon-substitutes, dialogue-anchored flavor matching the 3–8 sentence guideline, generic command-economy vocabulary instead of Soviet-specific terms. ~30 events / ~120 lines affected. Out of auto-fix budget and squarely in design-intent territory.

## Auto-fix decisions

None this run. Findings cluster on authorial-voice questions where mechanical patching would erase potentially-intentional style.

## Loc-heuristic feedback (per prompt § Loc-file self-instrumentation)

- Pre-loaded docs (`docs/guides/event_creation_guide.md`) were the right call — used § Flavor Text and § General Tone directly.
- Also reached for `docs/audits/nightly_checklists/localization.md` and `common/scripted_effects/banking_cycle_effects.txt` (to verify event-firing context for the Gosplan question).
- The heuristic's prediction of `event_`-prefixed loc held — no surprise prefixes in the slice.

## Wrap-up artifacts

- 1 issue filed (consolidated)
- 0 auto-fix PRs
- 1 state-bump-only PR (this report + `.nightly_coverage.json` diff)
