# Covert Per-Target Networks (Slice 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every country a covert operator targets gets a persistent intelligence *network* (strength 0–100) that grows while operations run against it, decays when they stop, is set back by a burn, and in return gives new operations a head start and every operation against that target a lower detection chance.

**Architecture:** One script container per (operator, target), tagged `iw_net`, parented on the operator and listed in the operator's `iw_nets` variable list — the same shape as the `iw_op` containers. A single monthly effect, `covert_nets_sync`, called from the journal entry pulse right after `covert_ops_sync_all`, creates missing networks, counts the operations against each, grows or decays it, and reaps dead ones. Operations read the network at three points: head start at creation, strength when detection is refreshed, loss on burn. A third journal-entry widget lists the networks.

**Tech Stack:** Paradox Clausewitz script (Victoria 3 1.13.10+ script containers), `.gui`, YAML loc, Python `unittest` structural tests.

**Spec:** `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` § Slice 4 (and § Slices and build order, § Verification).

## Global Constraints

- Branch `covert-per-target-networks` off `main`; one PR; `--base main`.
- Brace-based `.txt` files use tab indentation; run `python3 scripts/format_paradox_tabs.py <files>` on every touched `.txt`/`.gui`.
- Every touched `.txt` keeps its UTF-8 BOM if it had one (all covert files do). Check with `head -c3 <f> | xxd`.
- Loc goes in `localization/english/te_journal_entries_l_english.yml` for `je_iw_*` keys (that is where `je_iw_op_row_*` live; `organize_loc.py` routes every `je_` key there), `te_events_l_english.yml` for `te_debug_covert.*`, `te_miscellaneous_l_english.yml` for `covert_*` tooltips. Then `python3 organize_loc.py`; confirm nothing new lands in `te_unused_l_english.yml`.
- Vic3 loc formatting: `#b X#!`, `#v`, `#R`, `#G`, `#Y` — never `[b]…[/b]`.
- `docs/systems/journal_entry_systems.md` is CRLF: edit with `Edit` only; confirm with `grep -c $'\r$'` equal to `wc -l` afterwards.
- Never `git commit -a`; stage by path (the tree carries unrelated `common/buy_packages/00_buy_packages.txt` and `docs/engine/*` churn).
- Commit trailer: `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_0186Y88kcPZt85ybHbJ6HCcA`.
- Constants (Section 1 of `covert_warfare_script_values.txt`), verbatim from the spec: `covert_net_max 100`, `covert_net_dr_divisor 50`, `covert_net_dr_floor 0.1`, `covert_net_gain_base 2`, `covert_net_extra_op_factor 0.5`, `covert_net_decay_base 1.5`, `covert_net_maintain_funding_level 3`, `covert_net_maintain_decay_mult 0.5`, `covert_net_burn_loss 25`, `covert_net_detect_factor 0.05`, `covert_net_head_start_per_point 0.05`, `covert_net_head_start_max 5`.
- No tenth "maintain presence" pact. Funding ≥ 3 halves decay; nothing else.

### Engine rules this plan relies on (from `docs/guides/scripting_best_practices.md` § Per-Entity State and this file's own comments)

1. `remove_list_variable` **before** `destroy_container`; never edit `iw_nets` while iterating it (collect into a temporary list first).
2. Guard every `iw_nets` / `iw_ops` iteration with `has_variable_list`.
3. **Guard every `random_in_list … save_scope_as` lookup with a matching `any_in_list` limit**, and give each lookup its own scope name. Inside a loop, an unmatched `random_in_list` leaves the *previous* iteration's saved scope in place, so the next operation would read the wrong network.
4. Cross-container reads go through `PREV.var:` from inside the receiving scope (the shape of `covert_op_refresh_detection`'s `PREV.var:iw_priority`). Never `scope:<container>.var:x` or `scope:<container>.<script_value>`.
5. `change_variable` does not reliably resolve a *script-value* operand. Accumulate with `set_variable = { name = x value = { value = var:x add = <sv> } }`.
6. `covert_op_refresh_detection` does `save_scope_as = iw_op`, so anything that runs the sync clobbers a caller's `scope:iw_op` (rule 14).

### Decisions this plan makes where the spec is silent or stale

- **The tick is NOT inside `covert_ops_sync_all`.** That effect also runs on every funding or priority click (`covert_refresh_funding_state`). Called from there, networks would grow per click. `covert_nets_sync` is called once, from the JE monthly pulse, between `covert_ops_sync_all` and `covert_ops_age_all_durations`. Consequence: the detection refresh inside `covert_ops_sync_all` stages *last month's* strength. The lag is one month, accepted and documented.
- **Funding halves decay by branching in the effect**, on `scope:iw_net_operator`'s `iw_funding_level`, rather than staging funding onto the network. Same result, one less staging variable, and still never reads `parent` inside a script value (the spec's actual concern).
- **Operation count is accumulated, not counted with `any_in_list = { count >= N }`.** There's no vanilla precedent for `count` on `any_in_list`. The tick zeroes `iw_net_ops` on every network, then walks `iw_ops` once and adds 1 to the matching network.
- **`iw_net_trend`**: 1 = growing (≥ 1 operation, below `covert_net_max`); 2 = decaying (no operations); 0 = holding (≥ 1 operation, already at `covert_net_max`). A network at 0 with no operations is reaped the same month, so "decaying at 0" never displays.
- **`iw_net_head_start` is rounded to whole months** at creation (`round = yes`, per the repo's round-over-floor rule), so `iw_phase_months_left` stays an integer. Maximum 5, so phase 1 is never skipped (5 < 6).
- **Detection floor stays `covert_ops_detection_floor` (0.1).** The spec's "floor `min = 1` stays" predates slice 2. The network term is subtracted after the four funding `if`s and before `add = target_counterintelligence_penalty`, so covert efficiency scales it like the rest of the raw score.
- **A network is also created at operation creation** (guarded by `exists = scope:iw_new_op`), not only by the monthly sync, so the network row appears on the day the first operation starts. That creation happens *after* the head-start lookup, so a first operation gets head start 0.
- **The target's display capital is refreshed on the network every tick** (capitals move).
- **Reaping a network whose target no longer exists** uses `NOT = { var:iw_target ?= { is_country_alive = yes } }` (vanilla `00_acw_entries.txt:102` uses `is_country_alive`); an annexed tag can persist as a dead country, which `exists` would not catch.

## Review Focus

1. **Networks tick exactly once a month regardless of clicks.** Mashing the funding or priority stepper must not grow a network. Pinned by `test_nets_sync_only_called_from_monthly_pulse` (Task 2).
2. **Two operations against different targets in one refresh pass must not share a network.** Where op A's target has a network and op B's has none, B must stage 0, not A's strength. Pinned by `test_detection_lookup_guarded_and_zeroed` (Task 3) and `test_head_start_lookup_guarded` (Task 3).
3. **An operation restored from a pre-slice-4 save** (no `iw_net_head_start`) must keep its phase: the effective duration must treat the missing variable as 0, and the sync must backfill it before refreshing detection. Pinned by `test_effective_duration_guards_missing_head_start` and `test_sync_backfills_head_start_before_detection` (Task 3).
4. **A target that is annexed or dies** must not leave a network row forever or a dangling list entry. Pinned by `test_reap_removes_before_destroy` and `test_reap_checks_dead_target` (Task 2).
5. **The widget must not render for a country whose entry never activated or which has no networks.** The root is gated on `JournalEntry.IsActive` and the header on a non-empty list. Pinned by `test_network_widget_gated` (Task 4).

---

## File map

| File | Change |
|---|---|
| `common/script_values/covert_warfare_script_values.txt` | Section 1 constants; new § "PER-TARGET NETWORKS (slice 4)" script values; network term in `covert_operation_detection_chance` |
| `common/scripted_effects/covert_warfare_effects.txt` | Header doc for the `iw_net` container; new § "PER-TARGET NETWORKS"; edits to `covert_op_create`, `covert_op_refresh_detection`, `covert_op_sync`, `covert_op_refresh_phase`, `covert_op_burn` |
| `common/scripted_triggers/covert_warfare_triggers.txt` | Phase triggers read `covert_op_effective_duration` |
| `common/journal_entries/je_covert_warfare.txt` | Pulse calls `covert_nets_sync`; third `widget = { }` on `custom_widget_container_3`; header comment |
| `gui/journal_entry_widgets/covert_operations_widget.gui` | `widget_je_covert_networks` + row type; header comment |
| `localization/english/te_journal_entries_l_english.yml` | `je_iw_net_*` |
| `localization/english/te_miscellaneous_l_english.yml` | `covert_op_burned_tt` mentions the network setback |
| `localization/english/te_events_l_english.yml` | Harness option loc |
| `common/scripted_effects/te_debug_covert_effects.txt`, `events/te_debug_covert_events.txt` | Harness: set every network's strength; run a network tick |
| `test_covert_networks.py` | New structural test file |
| `docs/systems/mod_systems.md` § Covert Warfare System, `docs/systems/journal_entry_systems.md` § Covert Warfare | Docs |

---

### Task 1: Constants and network script values

**Files:**
- Modify: `common/script_values/covert_warfare_script_values.txt` (Section 1 tail, after `covert_op_phase_full_mult = 2`; and a new section appended at end of file)
- Create: `test_covert_networks.py`

**Interfaces:**
- Produces (script values; scope noted):
  - constants listed in Global Constraints, plus `covert_net_decay_maintained` (= base × maintain mult)
  - `covert_net_gain_scale` — network container; diminishing-returns factor from `var:iw_net_strength`
  - `covert_net_tick_gain` — network container; nominal monthly gain from `var:iw_net_ops`
  - `covert_net_head_start_value` — network container; months of head start, rounded, capped
  - `covert_op_effective_duration` — operation container; `iw_duration + iw_net_head_start` (missing = 0)
  - `covert_net_detect_reduction` — operator country; `var:iw_net_strength_staging × covert_net_detect_factor` (missing = 0)

- [ ] **Step 1: Write the failing test**

Create `test_covert_networks.py`:

```python
"""Structural tests for covert warfare slice 4 (per-target networks).

A network is one script container per (operator, target), listed in the
operator's iw_nets. These tests pin the constants, that the monthly tick runs
once a month and only from the journal entry pulse, that every lookup of a
network from inside a loop is guarded (an unmatched random_in_list would leave
the previous iteration's scope behind), that old-save operations keep their
phase, and that the widget and loc exist.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"
LOC_DIR = ROOT / "localization/english"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    # Anchored on a preceding newline so the header only matches a top-level
    # definition, never a mention inside a comment or an indented call.
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _all_loc():
    return "".join(p.read_text(encoding="utf-8-sig") for p in LOC_DIR.rglob("*.yml"))


class ConstantTests(unittest.TestCase):
    def test_constants_exist(self):
        body = _text(VALUES)
        for name, value in (
            ("covert_net_max", "100"),
            ("covert_net_dr_divisor", "50"),
            ("covert_net_dr_floor", "0.1"),
            ("covert_net_gain_base", "2"),
            ("covert_net_extra_op_factor", "0.5"),
            ("covert_net_decay_base", "1.5"),
            ("covert_net_maintain_funding_level", "3"),
            ("covert_net_maintain_decay_mult", "0.5"),
            ("covert_net_burn_loss", "25"),
            ("covert_net_detect_factor", "0.05"),
            ("covert_net_head_start_per_point", "0.05"),
            ("covert_net_head_start_max", "5"),
        ):
            self.assertRegex(body, r"(?m)^%s = %s$" % (name, re.escape(value)))

    def test_head_start_never_skips_preparatory(self):
        # Phase 2 starts at duration 6 (covert_op_is_established); a head start
        # of 6 or more would start an operation already establishing.
        body = _text(VALUES)
        cap = float(re.search(r"(?m)^covert_net_head_start_max = ([\d.]+)$", body).group(1))
        self.assertLess(cap, 6)


class ScriptValueTests(unittest.TestCase):
    def test_gain_scale_mirrors_un_idiom(self):
        block = _top_level_block(_text(VALUES), "covert_net_gain_scale = {")
        self.assertIn("covert_net_dr_divisor", block)
        self.assertIn("min = covert_net_dr_floor", block)
        self.assertIn("max = 1", block)

    def test_tick_gain_caps_at_three_ops(self):
        block = _top_level_block(_text(VALUES), "covert_net_tick_gain = {")
        self.assertIn("var:iw_net_ops", block)
        self.assertIn("max = 3", block)
        self.assertIn("covert_net_extra_op_factor", block)

    def test_head_start_rounded_and_capped(self):
        block = _top_level_block(_text(VALUES), "covert_net_head_start_value = {")
        self.assertIn("round = yes", block)
        self.assertIn("max = covert_net_head_start_max", block)

    def test_effective_duration_guards_missing_head_start(self):
        block = _top_level_block(_text(VALUES), "covert_op_effective_duration = {")
        self.assertIn("value = var:iw_duration", block)
        self.assertIn("has_variable = iw_net_head_start", block)

    def test_detection_subtracts_network_before_target_penalty(self):
        block = _top_level_block(_text(VALUES), "covert_operation_detection_chance = {")
        net = block.index("subtract = covert_net_detect_reduction")
        funding5 = block.index("covert_ops_detection_funding_5_reduction")
        target = block.index("add = target_counterintelligence_penalty")
        self.assertLess(funding5, net)
        self.assertLess(net, target)
        self.assertIn("min = covert_ops_detection_floor", block)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 test_covert_networks.py`
Expected: FAIL / ERROR — `covert_net_max` regex no match; `ValueError: substring not found` for the new script values.

- [ ] **Step 3: Add the Section 1 constants**

In `common/script_values/covert_warfare_script_values.txt`, directly after the line `covert_op_phase_full_mult = 2`, insert:

```paradox

# ---- Per-target networks (slice 4) ----
# An operator's standing presence inside one target country, 0 to
# covert_net_max. It grows while operations run against the target and
# decays when none do. Gains shrink above half strength (the UN-standing
# idiom); losses do not.
covert_net_max = 100
covert_net_dr_divisor = 50
covert_net_dr_floor = 0.1
# Monthly gain with one operation running; each extra operation against the
# same target adds covert_net_extra_op_factor of it (2 ops x1.5, 3 ops x2,
# counted up to 3).
covert_net_gain_base = 2
covert_net_extra_op_factor = 0.5
# Monthly decay with no operations running. Funding at or above
# covert_net_maintain_funding_level keeps the handlers paid, halving it.
covert_net_decay_base = 1.5
covert_net_maintain_funding_level = 3
covert_net_maintain_decay_mult = 0.5
# Being caught rolls up part of the network (about a year of single-op work).
covert_net_burn_loss = 25
# Raw detection points removed per point of strength (-5 at full strength),
# before covert efficiency like the rest of the raw score.
covert_net_detect_factor = 0.05
# Months of head start a new operation gets per point of strength, rounded.
# The cap stays below the 6-month establishing threshold, so phase 1 is never
# skipped: a full network puts a new operation one month from establishing.
covert_net_head_start_per_point = 0.05
covert_net_head_start_max = 5
```

- [ ] **Step 4: Append the network script-value section**

At the end of `common/script_values/covert_warfare_script_values.txt`, append:

```paradox

# ============================================================================
# SECTION: PER-TARGET NETWORKS (slice 4)
# ============================================================================
# A network is an iw_net script container (covert_warfare_effects.txt,
# § PER-TARGET NETWORKS). The values below are evaluated in the scope noted;
# none of them reads `parent` — anything the network needs from its operator
# is decided in the effect that calls them.
#
# Projection (months from 0; linear below 50, diminishing above):
#   strength   1 op   2 ops   3 ops
#   25         12.5   8.3     6.3
#   50         25     16.7    12.5
#   75         42     28      21
#   90         65     44      33
# Decay from 50 with no operations: 33 months (67 at funding >= 3).

# Monthly decay at or above covert_net_maintain_funding_level.
covert_net_decay_maintained = {
	value = covert_net_decay_base
	multiply = covert_net_maintain_decay_mult
}

# Diminishing returns on gains: 1 up to half strength, then falling linearly
# to covert_net_dr_floor at full. Same shape as un_standing_gain_scale.
# Scope: network container
covert_net_gain_scale = {
	value = 1
	if = {
		limit = { has_variable = iw_net_strength }
		subtract = 1
		add = {
			value = covert_net_max
			subtract = var:iw_net_strength
			divide = covert_net_dr_divisor
		}
	}
	min = covert_net_dr_floor
	max = 1
}

# Nominal gain this month, before diminishing returns: covert_net_gain_base
# for one operation against the target, plus covert_net_extra_op_factor of it
# for each further one, counted up to three. var:iw_net_ops is written by the
# tick just before this is read.
# Scope: network container
covert_net_tick_gain = {
	value = var:iw_net_ops
	max = 3
	subtract = 1
	min = 0
	multiply = covert_net_extra_op_factor
	add = 1
	multiply = covert_net_gain_base
}

# Head start, in whole months, that a new operation against this network's
# target starts with. Fixed on the operation at creation.
# Scope: network container
covert_net_head_start_value = {
	value = 0
	if = {
		limit = { has_variable = iw_net_strength }
		add = var:iw_net_strength
		multiply = covert_net_head_start_per_point
	}
	round = yes
	min = 0
	max = covert_net_head_start_max
}

# The duration the phase thresholds are measured against: months actually run
# plus the network's head start. A container from a save made before slice 4
# has no head start until the next monthly sync backfills it, and reads as 0.
# Scope: operation container
covert_op_effective_duration = {
	value = var:iw_duration
	if = {
		limit = { has_variable = iw_net_head_start }
		add = var:iw_net_head_start
	}
}

# Raw detection points the target network hides. var:iw_net_strength_staging
# is staged on the operator by covert_op_refresh_detection (0 when the target
# has no network). Scope: operator country
covert_net_detect_reduction = {
	value = 0
	if = {
		limit = { has_variable = iw_net_strength_staging }
		add = var:iw_net_strength_staging
		multiply = covert_net_detect_factor
	}
}

# Display: the most a full network takes off the raw detection score.
covert_net_detect_reduction_max_display = {
	value = covert_net_max
	multiply = covert_net_detect_factor
}
```

- [ ] **Step 5: Wire the network term into detection**

In `covert_operation_detection_chance`, directly after the `if` block that subtracts `covert_ops_detection_funding_5_reduction` and before `# Target's counterintelligence increases detection risk`, insert:

```paradox
	# A network inside the target hides the operation (slice 4). Staged per
	# operation by covert_op_refresh_detection; 0 without a network.
	subtract = covert_net_detect_reduction
```

Also update the formula comment above the value from `raw = base - funding_reduction + target_defense_penalty + priority_penalty` to `raw = base - funding_reduction - network + target_defense_penalty + priority_penalty`.

- [ ] **Step 6: Run the tests**

Run: `python3 test_covert_networks.py && python3 test_covert_priority.py && python3 test_covert_detection_roll.py`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/covert_warfare_script_values.txt
git add common/script_values/covert_warfare_script_values.txt test_covert_networks.py
git commit -m "feat(covert): network constants and script values (slice 4)"
```

---

### Task 2: Network containers and the monthly tick

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (header comment; new section inserted before `# MONTHLY RECONCILIATION`)
- Modify: `common/journal_entries/je_covert_warfare.txt` (monthly pulse)
- Test: `test_covert_networks.py`

**Interfaces:**
- Consumes: `covert_net_gain_scale`, `covert_net_tick_gain`, `covert_net_head_start_value`, `covert_net_decay_maintained`, constants (Task 1).
- Produces:
  - `covert_net_create = { TARGET = <country scope ref> }` — operator scope; no-op if a network for TARGET exists; leaves nothing saved.
  - `covert_net_gain = { AMOUNT = <number|sv> }` — network scope; × `covert_net_gain_scale`, clamped.
  - `covert_net_loss = { AMOUNT = <number|sv> }` — network scope; unscaled, clamped.
  - `covert_net_clamp = yes` — network scope.
  - `covert_nets_sync = yes` — operator scope; monthly only.
  - Network container vars: `iw_target`, `iw_target_capital`, `iw_net_strength`, `iw_net_ops`, `iw_net_trend`, `iw_net_head_start_offer` (display + the value `covert_op_create` copies).

- [ ] **Step 1: Write the failing tests**

Append to `test_covert_networks.py`, before `if __name__ == "__main__":`:

```python
class NetworkEffectTests(unittest.TestCase):
    def test_create_is_tagged_parented_listed(self):
        block = _top_level_block(_text(EFFECTS), "covert_net_create = {")
        self.assertIn("tags = { iw_net }", block)
        self.assertIn("parent = scope:iw_net_operator", block)
        self.assertIn("add_to_variable_list = { name = iw_nets", block)
        self.assertIn("exists = scope:iw_new_net", block)
        # No duplicate network per target.
        self.assertIn("any_in_list", block)

    def test_gain_scaled_loss_not(self):
        body = _text(EFFECTS)
        gain = _top_level_block(body, "covert_net_gain = {")
        loss = _top_level_block(body, "covert_net_loss = {")
        self.assertIn("covert_net_gain_scale", gain)
        self.assertNotIn("covert_net_gain_scale", loss)
        self.assertIn("covert_net_clamp = yes", gain)
        self.assertIn("covert_net_clamp = yes", loss)

    def test_tick_counts_by_accumulation(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        self.assertIn("set_variable = { name = iw_net_ops value = 0 }", block)
        self.assertIn("change_variable = { name = iw_net_ops add = 1 }", block)
        self.assertNotRegex(block, r"count\s*>=")

    def test_tick_halves_decay_on_funding(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        self.assertIn("covert_net_maintain_funding_level", block)
        self.assertIn("covert_net_loss = { AMOUNT = covert_net_decay_maintained }", block)
        self.assertIn("covert_net_loss = { AMOUNT = covert_net_decay_base }", block)
        self.assertIn("covert_net_gain = { AMOUNT = covert_net_tick_gain }", block)

    def test_reap_removes_before_destroy(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        reap = block[block.index("add_to_temporary_list = iw_reaped_nets"):]
        self.assertLess(
            reap.index("remove_list_variable = { name = iw_nets"),
            reap.index("destroy_container = yes"),
        )

    def test_reap_checks_dead_target(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        self.assertIn("is_country_alive = yes", block)

    def test_tick_lookups_guarded(self):
        # Every random_in_list over iw_nets inside the tick sits under an
        # any_in_list limit on the same target, so an unmatched lookup can
        # never leave the previous operation's network in the saved scope.
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        self.assertEqual(
            block.count("random_in_list = {"),
            block.count("save_scope_as = iw_tick_net"),
        )
        self.assertGreaterEqual(block.count("any_in_list = {"), block.count("random_in_list = {"))


class PulseOrderTests(unittest.TestCase):
    def test_nets_sync_only_called_from_monthly_pulse(self):
        # covert_ops_sync_all also runs on every funding / priority click;
        # a tick in there would grow networks per click.
        effects = _text(EFFECTS)
        sync_all = _top_level_block(effects, "covert_ops_sync_all = {")
        refresh = _top_level_block(effects, "covert_refresh_funding_state = {")
        self.assertNotIn("covert_nets_sync", sync_all)
        self.assertNotIn("covert_nets_sync", refresh)
        callers = [
            p for p in ROOT.glob("common/**/*.txt")
            if "covert_nets_sync = yes" in p.read_text(encoding="utf-8-sig")
        ]
        self.assertEqual([p.name for p in callers], ["je_covert_warfare.txt"])

    def test_pulse_order(self):
        je = _text(JE)
        ops = je.index("covert_ops_sync_all = yes")
        nets = je.index("covert_nets_sync = yes")
        age = je.index("covert_ops_age_all_durations = yes")
        self.assertLess(ops, nets)
        self.assertLess(nets, age)
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 test_covert_networks.py`
Expected: FAIL — `ValueError: substring not found` for `covert_net_create = {` etc.

- [ ] **Step 3: Document the container in the file header**

In the header comment of `covert_warfare_effects.txt`, after the paragraph ending `list, never every_container: the global iterator scans every container in\n# the game, parent filter or not.`, insert:

```paradox
#
# Every country the operator has run operations against also has a NETWORK
# container (slice 4, § PER-TARGET NETWORKS below):
#
#   tags    iw_net
#   parent  operator country
#   vars    iw_target               target country
#           iw_target_capital       display chain, as on operations
#           iw_net_strength         0 - covert_net_max
#           iw_net_ops              operations against the target this month (display)
#           iw_net_trend            1 growing, 2 decaying, 0 holding at max (display)
#           iw_net_head_start_offer months of head start a new operation would get
#
# listed in the operator's `iw_nets`. It outlives the operations: that is the
# point. Operations read it at creation (head start), at every detection
# refresh (strength) and on a burn (loss).
```

- [ ] **Step 4: Add the network section**

In `covert_warfare_effects.txt`, directly before the block

```paradox
# ============================================================================
# MONTHLY RECONCILIATION
# ============================================================================
```

insert:

```paradox
# ============================================================================
# PER-TARGET NETWORKS (slice 4)
# ============================================================================
# One iw_net container per (operator, target). Grows monthly while operations
# run against the target, decays when none do, loses covert_net_burn_loss when
# one of them is burned. Constants and projections:
# covert_warfare_script_values.txt, § PER-TARGET NETWORKS.
#
# Lookups of "the network for target X" always sit under an any_in_list limit
# on the same target, and each call site saves its own scope name: inside a
# loop, an unmatched random_in_list would leave the previous iteration's
# network in the saved scope.

# Create the network for $TARGET$ if there isn't one. Leaves the operator's
# iw_nets unchanged when one exists.
# Parameters: $TARGET$ = target country (a scope: reference)
# Scope: operator country
covert_net_create = {
	save_scope_as = iw_net_operator
	if = {
		limit = {
			NOT = {
				AND = {
					has_variable_list = iw_nets
					any_in_list = {
						variable = iw_nets
						var:iw_target ?= $TARGET$
					}
				}
			}
		}
		create_container = {
			tags = { iw_net }
			parent = scope:iw_net_operator
			save_scope_as = iw_new_net
		}
		if = {
			limit = { exists = scope:iw_new_net }
			scope:iw_new_net = {
				set_variable = { name = iw_target value = $TARGET$ }
				set_variable = { name = iw_net_strength value = 0 }
				set_variable = { name = iw_net_ops value = 0 }
				set_variable = { name = iw_net_trend value = 1 }
				set_variable = { name = iw_net_head_start_offer value = 0 }
				var:iw_target = {
					capital ?= {
						scope:iw_new_net = { set_variable = { name = iw_target_capital value = PREV } }
					}
				}
			}
			add_to_variable_list = { name = iw_nets target = scope:iw_new_net }
		}
	}
}

# Hold iw_net_strength inside [0, covert_net_max]. change_variable has no
# clamp argument, so this runs straight after every write.
# Scope: network container
covert_net_clamp = {
	clamp_variable = { name = iw_net_strength min = 0 max = covert_net_max }
}

# Grow the network, scaled down above half strength (covert_net_gain_scale).
# Parameters: $AMOUNT$ = points (number or script value, >= 0)
# Scope: network container
covert_net_gain = {
	set_variable = {
		name = iw_net_strength
		value = {
			value = var:iw_net_strength
			add = {
				value = $AMOUNT$
				multiply = covert_net_gain_scale
			}
		}
	}
	covert_net_clamp = yes
}

# Shrink the network. Not scaled: a loss costs the same at any strength.
# Parameters: $AMOUNT$ = points (number or script value, >= 0)
# Scope: network container
covert_net_loss = {
	set_variable = {
		name = iw_net_strength
		value = {
			value = var:iw_net_strength
			subtract = $AMOUNT$
		}
	}
	covert_net_clamp = yes
}

# The monthly network pass. Called ONCE a month from je_covert_warfare's pulse,
# straight after covert_ops_sync_all — never from covert_ops_sync_all itself,
# which also runs on every funding and priority click and would grow networks
# per click.
#   1. Ensure a network exists for every operation's target.
#   2. Count operations per network (zero every count, then walk iw_ops once).
#   3. Tick: grow with >= 1 operation, otherwise decay (halved at funding
#      >= covert_net_maintain_funding_level); restate trend, head-start offer
#      and display capital.
#   4. Reap networks whose target is gone, or that hit 0 with no operations:
#      temporary list -> remove_list_variable -> destroy_container.
# Detection (staged inside covert_ops_sync_all) therefore reads last month's
# strength — a one-month lag, accepted.
# Scope: operator country
covert_nets_sync = {
	save_scope_as = iw_net_operator
	# ---- 1. Ensure ----
	if = {
		limit = { has_variable_list = iw_ops }
		every_in_list = {
			variable = iw_ops
			var:iw_target ?= {
				save_scope_as = iw_net_ensure_tgt
				scope:iw_net_operator = { covert_net_create = { TARGET = scope:iw_net_ensure_tgt } }
			}
		}
	}
	if = {
		limit = { has_variable_list = iw_nets }
		# ---- 2. Count ----
		every_in_list = {
			variable = iw_nets
			set_variable = { name = iw_net_ops value = 0 }
		}
		if = {
			limit = { has_variable_list = iw_ops }
			every_in_list = {
				variable = iw_ops
				var:iw_target ?= {
					save_scope_as = iw_net_count_tgt
					scope:iw_net_operator = {
						if = {
							limit = {
								any_in_list = {
									variable = iw_nets
									var:iw_target ?= scope:iw_net_count_tgt
								}
							}
							random_in_list = {
								variable = iw_nets
								limit = { var:iw_target ?= scope:iw_net_count_tgt }
								save_scope_as = iw_tick_net
							}
							scope:iw_tick_net = { change_variable = { name = iw_net_ops add = 1 } }
						}
					}
				}
			}
		}
		# ---- 3. Tick ----
		every_in_list = {
			variable = iw_nets
			if = {
				limit = { var:iw_net_ops >= 1 }
				covert_net_gain = { AMOUNT = covert_net_tick_gain }
				if = {
					limit = { var:iw_net_strength >= covert_net_max }
					set_variable = { name = iw_net_trend value = 0 }
				}
				else = {
					set_variable = { name = iw_net_trend value = 1 }
				}
			}
			else = {
				if = {
					limit = {
						scope:iw_net_operator = {
							has_variable = iw_funding_level
							var:iw_funding_level >= covert_net_maintain_funding_level
						}
					}
					covert_net_loss = { AMOUNT = covert_net_decay_maintained }
				}
				else = {
					covert_net_loss = { AMOUNT = covert_net_decay_base }
				}
				set_variable = { name = iw_net_trend value = 2 }
			}
			set_variable = { name = iw_net_head_start_offer value = covert_net_head_start_value }
			save_scope_as = iw_net_display
			var:iw_target ?= {
				capital ?= {
					scope:iw_net_display = { set_variable = { name = iw_target_capital value = PREV } }
				}
			}
		}
		# ---- 4. Reap ----
		every_in_list = {
			variable = iw_nets
			limit = {
				OR = {
					NOT = { var:iw_target ?= { is_country_alive = yes } }
					AND = {
						var:iw_net_ops < 1
						var:iw_net_strength <= 0
					}
				}
			}
			add_to_temporary_list = iw_reaped_nets
		}
		every_in_list = {
			list = iw_reaped_nets
			scope:iw_net_operator = { remove_list_variable = { name = iw_nets target = PREV } }
			destroy_container = yes
		}
	}
}
```

Note `test_tick_lookups_guarded` counts `random_in_list = {` against `save_scope_as = iw_tick_net` in this block; the block above has one of each and one guarding `any_in_list` (plus the one inside `covert_net_create`, which is a separate top-level block).

- [ ] **Step 5: Call it from the pulse**

In `common/journal_entries/je_covert_warfare.txt`, directly after the line `covert_ops_sync_all = yes` in `on_monthly_pulse` (and before `# ---- Age operation durations ----`), insert:

```paradox

			# ---- Per-target networks (slice 4) ----
			# Once a month, here and only here: covert_ops_sync_all also runs on
			# every funding / priority click, so the tick cannot live inside it.
			# Ensures a network per target, grows or decays each, reaps the dead.
			covert_nets_sync = yes
```

- [ ] **Step 6: Run the tests**

Run: `python3 test_covert_networks.py`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt common/journal_entries/je_covert_warfare.txt
git add common/scripted_effects/covert_warfare_effects.txt common/journal_entries/je_covert_warfare.txt test_covert_networks.py
git commit -m "feat(covert): per-target network containers and their monthly tick (slice 4)"
```

---

### Task 3: Operations consume the network (head start, detection, burn)

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` — `covert_op_create`, `covert_op_refresh_detection`, `covert_op_sync`, `covert_op_refresh_phase`, `covert_op_burn`, header var list
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` — phase triggers
- Modify: `localization/english/te_miscellaneous_l_english.yml` — `covert_op_burned_tt`
- Test: `test_covert_networks.py`

**Interfaces:**
- Consumes: `covert_net_create`, `covert_net_loss` (Task 2); `covert_op_effective_duration`, `covert_net_detect_reduction`, `covert_net_burn_loss` (Task 1); network var `iw_net_head_start_offer`, `iw_net_strength`.
- Produces: operation var `iw_net_head_start` (whole months, fixed at creation); operator transient `iw_net_strength_staging`.

- [ ] **Step 1: Write the failing tests**

Append to `test_covert_networks.py` before the `__main__` guard:

```python
class ConsumerTests(unittest.TestCase):
    def test_head_start_set_before_phase_refresh(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_create = {")
        self.assertLess(
            block.index("iw_net_head_start"),
            block.index("covert_op_refresh_phase = yes"),
        )
        self.assertIn("PREV.var:iw_net_head_start_offer", block)

    def test_head_start_lookup_guarded(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_create = {")
        self.assertIn("set_variable = { name = iw_net_head_start value = 0 }", block)
        self.assertIn("save_scope_as = iw_create_net", block)
        guard = block.index("any_in_list")
        pick = block.index("save_scope_as = iw_create_net")
        self.assertLess(guard, pick)

    def test_op_create_ensures_network_after_lookup(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_create = {")
        self.assertLess(
            block.index("save_scope_as = iw_create_net"),
            block.index("covert_net_create"),
        )

    def test_detection_lookup_guarded_and_zeroed(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_refresh_detection = {")
        zero = block.index("set_variable = { name = iw_net_strength_staging value = 0 }")
        pick = block.index("save_scope_as = iw_det_net")
        chance = block.index("covert_operation_detection_chance")
        self.assertLess(zero, pick)
        self.assertLess(pick, chance)
        self.assertIn("PREV.var:iw_net_strength", block)
        self.assertIn("remove_variable = iw_net_strength_staging", block)
        self.assertNotRegex(block, r"scope:iw_det_net\.var:")

    def test_sync_backfills_head_start_before_detection(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_sync = {")
        backfill = block.index("NOT = { has_variable = iw_net_head_start }")
        refresh = block.rindex("covert_op_refresh_detection")
        self.assertLess(backfill, refresh)

    def test_phase_triggers_read_effective_duration(self):
        body = _text(TRIGGERS)
        est = _top_level_block(body, "covert_op_is_established = {")
        full = _top_level_block(body, "covert_op_is_fully_operational = {")
        self.assertIn("covert_op_effective_duration >= 6", est)
        self.assertIn("covert_op_effective_duration >= 12", full)
        self.assertNotIn("var:iw_duration", est + full)

    def test_refresh_phase_uses_effective_duration(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_refresh_phase = {")
        self.assertEqual(block.count("subtract = covert_op_effective_duration"), 2)
        self.assertNotIn("subtract = var:iw_duration", block)

    def test_burn_costs_the_network(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_burn = {")
        self.assertIn("covert_net_loss = { AMOUNT = covert_net_burn_loss }", block)
        self.assertLess(block.index("any_in_list"), block.index("save_scope_as = iw_burn_net"))
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 test_covert_networks.py`
Expected: FAIL on the `ConsumerTests`.

- [ ] **Step 3: Phase triggers**

In `common/scripted_triggers/covert_warfare_triggers.txt`, replace:

```paradox
# Operation phase checks. Phase 2 (establishing) starts at month 6, phase 3
# (fully operational) at month 12; see covert_warfare_effects.txt.
# Scope: covert operation container
covert_op_is_established = {
	var:iw_duration >= 6
}

covert_op_is_fully_operational = {
	var:iw_duration >= 12
}
```

with:

```paradox
# Operation phase checks. Phase 2 (establishing) starts at month 6, phase 3
# (fully operational) at month 12, measured on covert_op_effective_duration:
# months run plus the head start the target's network gave the operation at
# creation (slice 4). These two are the ONLY place the thresholds live.
# Scope: covert operation container
covert_op_is_established = {
	covert_op_effective_duration >= 6
}

covert_op_is_fully_operational = {
	covert_op_effective_duration >= 12
}
```

- [ ] **Step 4: `covert_op_refresh_phase` subtracts the effective duration**

In `covert_op_refresh_phase`, replace the establishing branch's

```paradox
		set_variable = { name = iw_phase_months_left value = 12 }
		change_variable = { name = iw_phase_months_left subtract = var:iw_duration }
		clamp_variable = { name = iw_phase_months_left min = 0 max = 12 }
```

with

```paradox
		set_variable = { name = iw_phase_months_left value = { value = 12 subtract = covert_op_effective_duration } }
		clamp_variable = { name = iw_phase_months_left min = 0 max = 12 }
```

and the preparatory branch's

```paradox
		set_variable = { name = iw_phase_months_left value = 6 }
		change_variable = { name = iw_phase_months_left subtract = var:iw_duration }
		clamp_variable = { name = iw_phase_months_left min = 0 max = 6 }
```

with

```paradox
		set_variable = { name = iw_phase_months_left value = { value = 6 subtract = covert_op_effective_duration } }
		clamp_variable = { name = iw_phase_months_left min = 0 max = 6 }
```

(Inline value blocks, because `change_variable` does not reliably resolve a script-value operand.)

- [ ] **Step 5: Head start in `covert_op_create`**

Replace the body of `covert_op_create` from `if = {\n\t\tlimit = { exists = scope:iw_new_op }` to the end of that `if` with:

```paradox
	if = {
		limit = { exists = scope:iw_new_op }
		scope:iw_new_op = {
			set_variable = { name = iw_target value = $TARGET$ }
			set_variable = { name = iw_duration value = 0 }
			set_variable = { name = iw_type_code value = $CODE$ }
			set_variable = { name = iw_priority value = 1 }
			# Head start from the target's network, fixed now (slice 4). Set
			# before the phase is derived, which reads it.
			set_variable = { name = iw_net_head_start value = 0 }
		}
		if = {
			limit = {
				has_variable_list = iw_nets
				any_in_list = {
					variable = iw_nets
					var:iw_target ?= $TARGET$
				}
			}
			random_in_list = {
				variable = iw_nets
				limit = { var:iw_target ?= $TARGET$ }
				save_scope_as = iw_create_net
			}
			scope:iw_create_net = {
				scope:iw_new_op = { set_variable = { name = iw_net_head_start value = PREV.var:iw_net_head_start_offer } }
			}
		}
		scope:iw_new_op = {
			# Initialise the display phase so the widget never reads a variable
			# that does not exist yet; covert_op_refresh_phase derives it from
			# then on.
			covert_op_refresh_phase = yes
		}
		add_to_variable_list = { name = iw_ops target = scope:iw_new_op }
		# The network row appears on the day the first operation starts,
		# not at the next monthly pulse. After the lookup, so a first
		# operation gets no head start from an empty network.
		covert_net_create = { TARGET = $TARGET$ }
		covert_refresh_priority_cost = yes
	}
```

Note: `covert_net_create` re-saves `iw_net_operator`, not `iw_operator`, so `scope:iw_operator` (which `covert_op_refresh_detection` reads after this in `covert_op_start`) is untouched.

- [ ] **Step 6: Detection staging in `covert_op_refresh_detection`**

Replace the `var:iw_target = { … }` block and the cleanup block of `covert_op_refresh_detection` with:

```paradox
	var:iw_target = {
		save_scope_as = iw_det_tgt
		capital = {
			scope:iw_op = { set_variable = { name = iw_target_capital value = PREV } }
		}
		scope:iw_operator = {
			set_variable = { name = target_max_ic value = PREV.intelligence_capacity_total }
			set_variable = { name = target_type_defense value = PREV.modifier:$DEFENSE_MOD$ }
			# The target network's strength (slice 4), 0 without one. Zeroed
			# first and looked up under an any_in_list guard: this runs once per
			# operation in a loop, and an unmatched lookup must not inherit the
			# previous operation's network.
			set_variable = { name = iw_net_strength_staging value = 0 }
			if = {
				limit = {
					has_variable_list = iw_nets
					any_in_list = {
						variable = iw_nets
						var:iw_target ?= scope:iw_det_tgt
					}
				}
				random_in_list = {
					variable = iw_nets
					limit = { var:iw_target ?= scope:iw_det_tgt }
					save_scope_as = iw_det_net
				}
				scope:iw_det_net = {
					scope:iw_operator = { set_variable = { name = iw_net_strength_staging value = PREV.var:iw_net_strength } }
				}
			}
			set_variable = { name = iw_detect_staging value = covert_operation_detection_chance }
		}
	}
	set_variable = { name = iw_detect value = scope:iw_operator.var:iw_detect_staging }
	set_variable = { name = iw_tgt_ic value = scope:iw_operator.var:target_max_ic }
	set_variable = { name = iw_tgt_td value = scope:iw_operator.var:target_type_defense }
	scope:iw_operator = {
		remove_variable = iw_detect_staging
		remove_variable = iw_priority_staging
		remove_variable = iw_net_strength_staging
	}
```

Also update the comment above the effect: "covert_operation_detection_chance reads target_max_ic / target_type_defense / iw_priority_staging / iw_net_strength_staging off the operator, so they are staged there first."

- [ ] **Step 7: Backfill in `covert_op_sync`**

In `covert_op_sync`, after the existing `iw_priority` backfill `if` and before `covert_op_refresh_detection = { DEFENSE_MOD = $DEFENSE_MOD$ }`, insert:

```paradox
			# Old-save backfill (slice 4): an operation from before networks
			# gets no head start. covert_op_effective_duration already reads
			# a missing one as 0; this makes the widget and saves consistent.
			if = {
				limit = { NOT = { has_variable = iw_net_head_start } }
				set_variable = { name = iw_net_head_start value = 0 }
			}
```

- [ ] **Step 8: Burn costs the network**

Replace `covert_op_burn`'s body with:

```paradox
covert_op_burn = {
	remove_diplomatic_pact = { country = $TARGET$ type = $ACTION$ }
	covert_op_destroy = { TYPE = $TYPE$ TARGET = $TARGET$ }
	# The exposure rolls up part of the network in that country (slice 4).
	if = {
		limit = {
			has_variable_list = iw_nets
			any_in_list = {
				variable = iw_nets
				var:iw_target ?= $TARGET$
			}
		}
		random_in_list = {
			variable = iw_nets
			limit = { var:iw_target ?= $TARGET$ }
			save_scope_as = iw_burn_net
		}
		scope:iw_burn_net = { covert_net_loss = { AMOUNT = covert_net_burn_loss } }
	}
	$TARGET$ = {
		set_variable = { name = iw_last_exposed_country value = ROOT }
		set_variable = { name = iw_last_exposed_type value = $CODE$ }
		set_variable = { name = iw_last_exposed_age value = 0 }
	}
}
```

and add to its header comment: "Also costs the target's network covert_net_burn_loss (slice 4). Runs from covert_warfare.1's `after`, which is never rendered as a tooltip."

- [ ] **Step 9: Header var list and tooltip loc**

In the header's operation var list, after the `iw_priority` lines, add:

```paradox
#           iw_net_head_start  whole months of head start from the target's
#                              network, fixed at creation (slice 4)
```

In `localization/english/te_miscellaneous_l_english.yml`, change

```yaml
 covert_op_burned_tt:0 "The compromised operation will be terminated."
```

to

```yaml
 covert_op_burned_tt:0 "The compromised operation will be terminated, and our network in their country loses #R [GetPlayer.MakeScope.ScriptValue('covert_net_burn_loss')|0]#! strength."
```

- [ ] **Step 10: Run all covert tests**

Run: `python3 test_covert_networks.py && python3 test_covert_priority.py && python3 test_covert_detection_roll.py && python3 test_covert_exposure_tiers.py`
Expected: all PASS. If an older test pins text that moved (e.g. `covert_op_create`'s layout), update that assertion to the new text, not the code.

- [ ] **Step 11: Commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt
git add common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt localization/english/te_miscellaneous_l_english.yml test_covert_networks.py
git commit -m "feat(covert): operations take a head start and cover from their target's network; a burn sets it back (slice 4)"
```

---

### Task 4: The networks widget

**Files:**
- Modify: `gui/journal_entry_widgets/covert_operations_widget.gui` (header; new row type in `types`; new root widget at end)
- Modify: `common/journal_entries/je_covert_warfare.txt` (third `widget = { }`, header comment)
- Modify: `localization/english/te_journal_entries_l_english.yml`
- Test: `test_covert_networks.py`

**Interfaces:**
- Consumes: network vars `iw_target_capital`, `iw_net_strength`, `iw_net_ops`, `iw_net_trend`, `iw_net_head_start_offer`; script values `covert_net_max`, `covert_net_detect_factor`, `covert_net_detect_reduction_max_display`.
- Produces: `widget_je_covert_networks` on `custom_widget_container_3`; loc `je_iw_net_header`, `je_iw_net_header_tooltip`, `je_iw_net_row_title`, `je_iw_net_row_strength`, `je_iw_net_row_trend_growing`, `je_iw_net_row_trend_decaying`, `je_iw_net_row_trend_holding`, `je_iw_net_row_benefit`.

- [ ] **Step 1: Write the failing tests**

Append before the `__main__` guard:

```python
NET_LOC_KEYS = (
    "je_iw_net_header",
    "je_iw_net_header_tooltip",
    "je_iw_net_row_title",
    "je_iw_net_row_strength",
    "je_iw_net_row_trend_growing",
    "je_iw_net_row_trend_decaying",
    "je_iw_net_row_trend_holding",
    "je_iw_net_row_benefit",
)


class WidgetTests(unittest.TestCase):
    def test_je_mounts_network_widget_on_container_3(self):
        je = _text(JE)
        self.assertRegex(
            je,
            r'name = "widget_je_covert_networks"\s*\n\s*container = "custom_widget_container_3"',
        )

    def test_network_widget_gated(self):
        gui = _text(WIDGET)
        root = gui[gui.index('name = "widget_je_covert_networks"'):]
        self.assertIn('visible = "[JournalEntry.IsActive]"', root[:400])
        self.assertIn("GetList('iw_nets')", root)
        self.assertIn("IsDataModelEmpty", root)

    def test_trend_lines_cover_all_three_codes(self):
        gui = _text(WIDGET)
        for code in ("0", "1", "2"):
            self.assertIn(
                "EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_net_trend'), '(CFixedPoint)%s')" % code,
                gui,
            )

    def test_loc_keys_exist(self):
        loc = _all_loc()
        for key in NET_LOC_KEYS:
            self.assertRegex(loc, r"(?m)^ %s:0 " % re.escape(key))
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 test_covert_networks.py`
Expected: FAIL on `WidgetTests`.

- [ ] **Step 3: Row type**

In `covert_operations_widget.gui`, inside `types covert_operations_widget_types`, directly before its closing `}` (after `widget_je_covert_operation_row`'s closing brace), add:

```
	### ---- NETWORK ROW (slice 4) ---------------------------------------

	### One row per network in the operator's iw_nets. All numbers are
	### variables the monthly tick (covert_nets_sync) writes on the container;
	### the trend line is chosen by the stored code, never by comparing
	### strength against a literal.
	type widget_je_covert_network_row = flowcontainer {
		direction = vertical
		ignoreinvisible = yes
		parentanchor = hcenter
		margin = { 20 6 }

		background = {
			using = entry_bg_fancy_dark
			alpha = 0.5
		}

		widget_je_covert_operation_text = {
			text = "je_iw_net_row_title"
		}
		widget_je_covert_operation_detail = {
			text = "je_iw_net_row_strength"
		}
		widget_je_covert_operation_detail = {
			visible = "[EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_net_trend'), '(CFixedPoint)1')]"
			text = "je_iw_net_row_trend_growing"
		}
		widget_je_covert_operation_detail = {
			visible = "[EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_net_trend'), '(CFixedPoint)2')]"
			text = "je_iw_net_row_trend_decaying"
		}
		widget_je_covert_operation_detail = {
			visible = "[EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_net_trend'), '(CFixedPoint)0')]"
			text = "je_iw_net_row_trend_holding"
		}
		widget_je_covert_operation_detail = {
			text = "je_iw_net_row_benefit"
		}
	}
```

- [ ] **Step 4: Root widget**

Append at end of the `.gui` file:

```
### One row per network (slice 4). Mounted on custom_widget_container_3,
### below the journal entry's buttons. The header only shows when there is
### at least one network, so a country that has never run an operation sees
### nothing here.
flowcontainer = {
	name = "widget_je_covert_networks"
	direction = vertical
	parentanchor = hcenter
	spacing = 4
	visible = "[JournalEntry.IsActive]"

	covert_cc_header = {
		blockoverride "header_text" {
			text = "je_iw_net_header"
			tooltip = "je_iw_net_header_tooltip"
			visible = "[Not( IsDataModelEmpty( JournalEntry.GetCountry.MakeScope.GetList('iw_nets') ) )]"
		}
	}

	flowcontainer = {
		direction = vertical
		parentanchor = hcenter
		spacing = 4
		datamodel = "[JournalEntry.GetCountry.MakeScope.GetList('iw_nets')]"

		item = {
			widget_je_covert_network_row = {
				datacontext = "[Scope.GetScriptContainer]"
			}
		}
	}
}
```

Update the file's header comment: "Two widgets" → "Three widgets", and add after the `widget_je_covert_operations` lines:

```
###   widget_je_covert_networks        custom_widget_container_3  (below the buttons)
###     One row per per-target network, from the operator's `iw_nets` list
###     (slice 4; see covert_warfare_effects.txt § PER-TARGET NETWORKS).
```

Also change "Both roots are gated on [JournalEntry.IsActive]" to "All three roots are gated on [JournalEntry.IsActive]".

- [ ] **Step 5: Mount it in the JE**

In `je_covert_warfare.txt`, after the `widget_je_covert_operations` `widget = { … }` block, add:

```paradox
	widget = {
		gui = "gui/journal_entry_widgets/covert_operations_widget.gui"
		name = "widget_je_covert_networks"
		container = "custom_widget_container_3"
	}
```

And in the header comment (line ~4-11) change "Two custom widgets" to "Three custom widgets", adding "widget_je_covert_networks lists each per-target network (slice 4)".

- [ ] **Step 6: Loc**

Add to `localization/english/te_journal_entries_l_english.yml` next to the `je_iw_op_row_*` keys:

```yaml
 je_iw_net_header:0 "Networks"
 je_iw_net_header_tooltip:0 "Every country we have run operations against keeps a network of agents that outlives the operations. It grows while operations run there, #v faster with more of them#! and #v slower above half strength#!, and decays once they stop — #v half as fast#! at funding level [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_net_maintain_funding_level')|0] or above. A burned operation costs its network #R [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_net_burn_loss')|0]#! strength.\n\nA strong network lowers the detection risk of every operation in that country (up to #G -[JournalEntry.GetCountry.MakeScope.ScriptValue('covert_net_detect_reduction_max_display')|1]#! points before efficiency) and gives a new operation there a head start of up to #G [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_net_head_start_max')|0]#! months."
 je_iw_net_row_title:0 "• #Y Network#! in [ScriptContainer.MakeScope.Var('iw_target_capital').GetState.GetCountry.GetName]"
 je_iw_net_row_strength:0 "Strength #v [ScriptContainer.GetVariableValue('iw_net_strength')|0]#! / [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_net_max')|0] - [ScriptContainer.GetVariableValue('iw_net_ops')|0] operations running there"
 je_iw_net_row_trend_growing:0 "#G Growing#! while operations run there"
 je_iw_net_row_trend_decaying:0 "#R Decaying#! - no operations running there"
 je_iw_net_row_trend_holding:0 "#G At full strength#!"
 je_iw_net_row_benefit:0 "A new operation here starts #v [ScriptContainer.GetVariableValue('iw_net_head_start_offer')|0]#! months along"
```

(The detection benefit is on the header tooltip and inside each operation's own detection line, which already reflects it; the row only states what is unique to the network.)

Then run `python3 organize_loc.py` and check `git diff --stat localization/` shows only the intended files and nothing new in `te_unused_l_english.yml`.

- [ ] **Step 7: Run tests, commit**

Run: `python3 test_covert_networks.py`
Expected: PASS.

```bash
python3 scripts/format_paradox_tabs.py common/journal_entries/je_covert_warfare.txt
git add gui/journal_entry_widgets/covert_operations_widget.gui common/journal_entries/je_covert_warfare.txt localization/english/te_journal_entries_l_english.yml test_covert_networks.py
git commit -m "feat(covert): networks widget on the covert journal entry (slice 4)"
```

(`format_paradox_tabs.py` is for `.txt` only; indent the `.gui` with tabs by hand.)

---

### Task 5: Console harness

**Files:**
- Modify: `common/scripted_effects/te_debug_covert_effects.txt`
- Modify: `events/te_debug_covert_events.txt` (two options on `te_debug_covert.2`; header comment)
- Modify: `localization/english/te_events_l_english.yml`
- Test: `test_covert_networks.py`

**Interfaces:**
- Consumes: `covert_nets_sync`, `covert_net_create`, `covert_net_clamp`, `covert_ops_sync_all`.
- Produces: `te_debug_covert_set_net_strength = { VALUE = <n> }`, `te_debug_covert_tick_nets = yes`; options `te_debug_covert.2.i`, `.2.j`.

- [ ] **Step 1: Write the failing test**

Append before the `__main__` guard:

```python
class HarnessTests(unittest.TestCase):
    def test_harness_effects(self):
        body = _text(DEBUG_EFFECTS)
        setter = _top_level_block(body, "te_debug_covert_set_net_strength = {")
        self.assertIn("covert_nets_sync = yes", setter)  # ensures nets exist first
        self.assertIn("covert_ops_sync_all = yes", setter)  # re-stages detection
        tick = _top_level_block(body, "te_debug_covert_tick_nets = {")
        self.assertIn("covert_nets_sync = yes", tick)

    def test_harness_options_have_loc(self):
        events = _text(DEBUG_EVENTS)
        loc = _all_loc()
        for opt in ("te_debug_covert.2.i", "te_debug_covert.2.j"):
            self.assertIn("name = %s" % opt, events)
            self.assertRegex(loc, r"(?m)^ %s:0 " % re.escape(opt))
```

Also update `test_nets_sync_only_called_from_monthly_pulse` so the harness is an allowed caller — replace its last assertion with:

```python
        self.assertEqual(
            sorted(p.name for p in callers),
            ["je_covert_warfare.txt", "te_debug_covert_effects.txt"],
        )
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 test_covert_networks.py`
Expected: FAIL on `HarnessTests` and the updated caller test.

- [ ] **Step 3: Harness effects**

Append to `common/scripted_effects/te_debug_covert_effects.txt`:

```paradox

# Put every network at an exact strength (slice 4). Runs the real network pass
# first so every running operation's target has one, then overwrites the
# strength and re-runs the operation sync so each row's detection line shows
# the new cover at once. The head start only reaches operations started
# after this — it is fixed at creation.
# Note: the network pass also ticks once, which is why the strength is
# written after it, not before.
# Parameters: $VALUE$ = 0 .. covert_net_max
# Scope: country
te_debug_covert_set_net_strength = {
	covert_nets_sync = yes
	if = {
		limit = { has_variable_list = iw_nets }
		every_in_list = {
			variable = iw_nets
			set_variable = { name = iw_net_strength value = $VALUE$ }
			covert_net_clamp = yes
			set_variable = { name = iw_net_head_start_offer value = covert_net_head_start_value }
		}
	}
	covert_ops_sync_all = yes
}

# One month of network growth / decay without waiting for the pulse. Stand an
# operation down first to watch its network decay instead.
# Scope: country
te_debug_covert_tick_nets = {
	covert_nets_sync = yes
	covert_ops_sync_all = yes
}
```

- [ ] **Step 4: Harness options**

In `events/te_debug_covert_events.txt`, append inside `te_debug_covert.2` after the `.2.h` option:

```paradox

	# ---- Networks (slice 4): every network to full strength. Each row's
	#      detection line drops at once; an operation started afterwards
	#      begins with the maximum head start.
	option = {
		name = te_debug_covert.2.i
		trigger = { covert_operations_active >= 1 }
		te_debug_covert_set_net_strength = { VALUE = 100 }
	}

	# ---- Networks: run one monthly network pass now.
	option = {
		name = te_debug_covert.2.j
		te_debug_covert_tick_nets = yes
	}
```

And add to the file header's `te_debug_covert.2` line: `operations at each phase boundary, detection, priority, and networks`.

- [ ] **Step 5: Loc**

Add to `localization/english/te_events_l_english.yml` after `te_debug_covert.2.h`:

```yaml
 te_debug_covert.2.i:0 "Raise every network to full strength (detection drops now; new operations start 5 months along)"
 te_debug_covert.2.j:0 "Run one month of network growth and decay now"
```

Then `python3 organize_loc.py`.

- [ ] **Step 6: Run tests, commit**

Run: `python3 test_covert_networks.py`
Expected: PASS.

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt
git add common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt localization/english/te_events_l_english.yml test_covert_networks.py
git commit -m "test(covert): console harness for networks (slice 4)"
```

---

### Task 6: Docs, full verification, PR

**Files:**
- Modify: `docs/systems/mod_systems.md` § Covert Warfare System
- Modify: `docs/systems/journal_entry_systems.md` § Covert Warfare (CRLF)
- Modify: `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` (mark slice 4 built; note the decisions above that departed from the spec)

- [ ] **Step 1: `mod_systems.md`**

In § Covert Warfare System:
- Key Files table: `covert_operations_widget.gui` row → "Three JE widgets: … and `widget_je_covert_networks` (one row per per-target network, slice 4)". `covert_warfare_effects.txt` row → add "per-target networks (`covert_nets_sync`, create / gain / loss)".
- Add a `### Per-Target Networks (slice 4)` subsection after `### System Architecture` containing: the container shape (tags/vars/list); the monthly pass and why it is not in `covert_ops_sync_all`; the three consumers (head start fixed at creation, rounded, cap 5 < 6; detection −`covert_net_detect_factor` × strength raw points before efficiency, one-month lag; burn −25); decay halving at funding ≥ 3 and why there is no maintenance pact; reaping (dead target via `is_country_alive`, or 0 strength with no ops); the projection table copied from the script-value section header.
- If the "fourteen hand-maintained per-code sites" list exists in this section, note that networks add none (they are type-agnostic).

- [ ] **Step 2: `journal_entry_systems.md` (CRLF)**

With `Edit` only, in § Covert Warfare: add to the variables paragraph "Operator: `iw_nets` (network list), transient `iw_net_strength_staging`. Network container: `iw_target`, `iw_target_capital`, `iw_net_strength`, `iw_net_ops`, `iw_net_trend` (1 growing / 2 decaying / 0 holding), `iw_net_head_start_offer`. Operation container: `iw_net_head_start`." and change "Two custom widgets … `_1` … and `_2`" to three, naming `widget_je_covert_networks` on `custom_widget_container_3`. Add `covert_net_detect_reduction_max_display` to the display-only reads. Then verify:

```bash
f=docs/systems/journal_entry_systems.md; echo "$(grep -c $'\r$' $f) $(wc -l < $f)"
```
Expected: the two numbers are equal.

- [ ] **Step 3: Spec status**

In the spec's build-order table, row 4 → "Persistent per-target networks — built on branch covert-per-target-networks". Under § Slice 4 add a short "As built" paragraph listing: tick outside `covert_ops_sync_all`; count by accumulation; funding branch in the effect instead of staging; head start rounded; floor is `covert_ops_detection_floor`; network also created at op creation; loc in `te_journal_entries`.

- [ ] **Step 4: Full verification**

```bash
.venv/bin/python -m ruff check .
python3 scripts/format_paradox_tabs.py --check common/script_values/covert_warfare_script_values.txt common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt common/journal_entries/je_covert_warfare.txt common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt
python3 scripts/analysis/check_localization_files.py
for f in common/script_values/covert_warfare_script_values.txt common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt common/journal_entries/je_covert_warfare.txt common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt gui/journal_entry_widgets/covert_operations_widget.gui; do printf '%s ' $f; head -c3 $f | xxd -p; done
curl -s http://localhost:8950/status | head -c 300
curl -s -X POST 'http://localhost:8950/reload?mod_only=true&audits_only=true' | python3 -c 'import json,sys; r=json.load(sys.stdin); print(json.dumps({k:r.get(k) for k in ("warnings","parse_failures")}, indent=1)[:4000])'
python3 -m unittest discover -s . -p 'test_*.py'
```

Expected: ruff clean; tab check clean; loc check clean; every file prints `efbbbf` (BOM) — compare against `git show origin/main:<f> | head -c3 | xxd -p` for any that differ; `warnings` empty (or only pre-existing findings — diff them against a reload on `main` if non-empty); parse_failures empty; the full suite passes. Then grep the reports for the new names:

```bash
grep -n 'iw_net\|covert_net\|je_iw_net' docs/engine/loc_coverage_report.md docs/engine/modifier_visibility_report.md docs/engine/modifier_multiplier_var_report.md docs/engine/iterator_limit_report.md docs/engine/effect_trigger_validity_report.md docs/engine/localization_accessor_report.md docs/engine/loc_render_report.md
```
Expected: no hits (or each explained in the PR body). Revert unrelated `docs/engine/*` churn from the reload before staging (`git checkout -- docs/engine/` for files not relevant to this change).

- [ ] **Step 5: Commit docs**

```bash
git add docs/systems/mod_systems.md docs/systems/journal_entry_systems.md docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md
git commit -m "docs(covert): per-target networks (slice 4)"
```

- [ ] **Step 6: PR**

Write the PR body to `$SCRATCHPAD/pr_slice4.md` first. It should include: summary, the "decisions where the spec was silent/stale" list, the projection table, and **in-game checks still owed**: (1) `event te_debug_covert.2` → option a (seed), wait one month: a network row appears per target and grows by 2 × (1 + 0.5 × (ops−1)); (2) option i: every row's detection line drops by up to 5 × (1 − efficiency); start a new operation against the same target and see "N months until it establishes" = 1; (3) option b (force detection): the network loses 25; (4) option c (funding 0): networks show Decaying; (5) `debug.log` quiet about `iw_net`, `iw_det_net`, `iw_create_net`, `iw_burn_net`, `iw_tick_net` (log-triage skill). Then:

```bash
git push -u origin covert-per-target-networks
gh pr create --base main --title "feat(covert): persistent per-target networks (slice 4)" --body-file "$SCRATCHPAD/pr_slice4.md"
```

End the PR body with the attribution lines from Global Constraints' PR form:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_0186Y88kcPZt85ybHbJ6HCcA
```
