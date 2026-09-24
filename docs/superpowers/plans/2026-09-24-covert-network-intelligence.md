# Covert Warfare slice 7 — Network-revealed intelligence

Spec: `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` § Slice 7.

> At network strength ≥ 50 the operation/network row shows the target's intelligence
> capacity and tech count; at ≥ 75 it shows how many operations the target runs against
> **you**. Gated behind a strong network so the "defender never sees undetected ops" rule is
> broken only by having penetrated their service. Display-only; no new mechanics.

**Goal:** each network row (`widget_je_covert_networks`) gains an intelligence block that
grows with the network: nothing below 50, the target's service (intelligence capacity and
technology count, each beside our own) from 50, and the number of covert operations the
target is running against us from 75. Nothing in script reads any of it back.

## Design decisions

1. **Network row only, not the operation row.** Strength belongs to the network, and a
   network outlives its operations, so its row is the one place the report can sit for a
   target with no operation running. The operation row's detection line already prints the
   target's intelligence capacity (`iw_tgt_ic`) as a detection input — it has since the
   widget shipped, because the player needs their odds. That stays: it is only available
   while an operation (a slot, upkeep, detection risk) is running there, and it is not an
   intelligence reveal in the slice-7 sense. The network's report is what persists.

2. **A stored tier code, not a literal comparison in `.gui`.** The widget's editing rules
   forbid comparing a game number against a literal, so the 50 / 75 thresholds live in two
   Section 1 constants and the widget reads a code, `iw_net_intel_tier` (0 none, 1 service,
   2 service and operations), exactly as it reads `iw_phase` and `iw_net_trend`.

3. **The code is restated in `covert_net_clamp`**, which already runs straight after every
   strength write to restate the head-start offer. A burn therefore hides a tier on the
   same day, rather than leaving last month's report on screen for a network that no longer
   earns it. `covert_net_clamp` sits on tooltip-walked paths (`covert_warfare.1`'s `after`,
   via `covert_op_burn`), so it only sets a variable from a container-scope script value —
   no saved scope.

4. **The report values are refreshed monthly in the network pass**, by a new
   `covert_net_refresh_intel` called in `covert_nets_sync` step 3 straight after the
   strength write (so the values always match the tier the same pass computed). Values are
   written only at the tier that reveals them; below it the stale values stay stored but
   hidden. Strength only *rises* inside the tick (or the console harness, which refreshes
   too), so no path shows a tier whose values were never refreshed at that tier.

   | var | written at tier | source |
   |---|---|---|
   | `iw_net_intel_ic` | ≥ 1 | target's `intelligence_capacity_total` |
   | `iw_net_intel_techs` | ≥ 1 | target's `techs_researched` (event-target value link) |
   | `iw_net_intel_ops` | 2 | covert pacts with `first_country` = target, `second_country` = operator |

   The operations count reads **pacts** — the source of truth for whether an operation
   exists — not the target's `iw_ops` containers, whose sync only runs while the target's
   own journal entry is active. Every phase counts. It is accumulated
   (`change_variable add = 1` per pact), the shape slice 4 chose over `any_* count >= N`.
   Target read through `var:iw_target ?=` plus `is_country_alive = yes` (the reap step, which
   runs after, still collects a dead target's network).

5. **Our side of the comparison is live**, through two display reads: the existing
   `intelligence_capacity_total` and a new `covert_techs_researched_display`
   (`value = techs_researched`). Their numbers are last month's report; ours are current.

6. **Old saves.** A network from a save made before this slice has no `iw_net_intel_tier`
   until its first pass (every network gains or decays every tick, so every one is clamped).
   Every intelligence line is gated on `ScriptContainer.HasVariable('iw_net_intel_tier')`
   (the shape the history charts already use), so for that month the row simply shows none.

7. **The defender-side rule** (`covert_op_burn`'s header, the command centre's comment):
   "nothing aggregates hostile operations the defender has not detected". The tier-2 count is
   the one deliberate exception, and both comments say so: it is earned by holding a strong
   network inside the other service, not handed to the defender.

## Constants (Section 1, after slice 6)

```
# ---- Network intelligence (slice 7) ----
covert_net_intel_tier_1_strength = 50
covert_net_intel_tier_2_strength = 75
```

With one operation a network reaches 50 in ~25 months and 75 in ~42; cultivate assets alone
takes ~17 / ~28 (slice 6's projection). A burn (−25) from 75 drops straight to tier 1.

## Files

- `common/script_values/covert_warfare_script_values.txt` — constants; `covert_net_intel_tier_value`
  (network scope, § PER-TARGET NETWORKS); `covert_techs_researched_display` (§ 5).
- `common/scripted_effects/covert_warfare_effects.txt` — header var list; `covert_net_clamp`
  writes the code; new `covert_net_refresh_intel`; `covert_nets_sync` step 3 calls it; the
  `covert_op_burn` defender-rule comment.
- `common/scripted_effects/te_debug_covert_effects.txt`, `events/te_debug_covert_events.txt`
  — new `event te_debug_covert.5`: every network to 50 (tier 1) / to 80 (tier 2), and every
  network's target plants cultivate assets against us (so the tier-2 count reads non-zero).
  `te_debug_covert_set_net_strength` also refreshes the report.
- `gui/journal_entry_widgets/covert_operations_widget.gui` — four lines on the network row.
- `localization/english/te_journal_entries_l_english.yml` — row keys, header tooltip
  paragraph; `te_events_l_english.yml` — harness keys.
- `test_covert_net_intel.py` — structural pins.
- Docs: `mod_systems.md` § Per-Target Networks, `journal_entry_systems.md` § Covert Warfare
  (CRLF), the spec's "As built" note.

## Widget lines (network row, after the head-start line)

| visible when | key | text |
|---|---|---|
| has tier, tier = 0 | `je_iw_net_row_intel_none` | no view inside yet; strength 50 opens one |
| has tier, tier ≥ 1 | `je_iw_net_row_intel_service` | their capacity (ours), their technologies (ours) |
| has tier, tier = 1 | `je_iw_net_row_intel_ops_locked` | their operations against us: strength 75 |
| has tier, tier = 2 | `je_iw_net_row_intel_ops` | N operations against us |

Tier ≥ 1 is `Or( EqualTo(tier, 1), EqualTo(tier, 2) )` — the stored code against its own code
values, as the phase lines do.

## Verification

- `python3 -m unittest discover -s . -p 'test_*.py'`, `ruff check .`, the CI `--strict`
  audits, `scripts/format_paradox_tabs.py --check`, `check_localization_files.py`.
- Mod state server `POST /reload?mod_only=true&audits_only=true` → `warnings` empty; check
  `loc_coverage_report.md`, `loc_render_report.md`, `effect_trigger_validity_report.md`.
- In game: `event te_debug_covert.2` (seed), then `event te_debug_covert.5` a → tier-1 lines;
  b → tier-2 line reading 0; c → reads 1 on each network; `te_debug_covert.2` b (force a
  detection) on an operation whose network sits at 80 → the row drops to tier 1 at once.
