# Covert Warfare Slice 3 — Per-Operation Priority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the player (and the AI) put more weight behind one covert operation than another: each operation gets a priority of 1–3 that multiplies its effect, costs disproportionately more upkeep and raises its detection risk, so concentrating resources has diminishing returns.

**Architecture:** Priority is one variable on the operation's script container (`iw_priority`, missing ⇒ 1). Effects cannot use a container-scope script value as an `add_modifier` multiplier — the engine re-evaluates the multiplier against ROOT on every tick — so one helper, `covert_op_add_scaled_modifier`, branches phase × priority into six **constant** script values and replaces every hard-coded `multiplier = 2`. Upkeep reads a country variable `iw_priority_cost_sum` (Σ per-operation cost weights) that is recomputed whenever an operation is created, destroyed or re-prioritised. Detection stages the operation's priority on the operator next to the target data that is already staged there. A row stepper in the operations widget passes the row's container to two scripted GUIs (up / down) in a single `AddScope`, and fails closed if it does not arrive.

**Tech Stack:** Paradox Clausewitz script (`common/`, `events/`, `gui/`, `localization/`), Python 3 structural tests (`unittest`).

**Spec:** `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` § "Slice 3 — Per-operation priority". Slices 1 (#372) and 2 (#374) are merged.

## Global Constraints

- Branch is `covert-per-op-priority`, already created off `main` in the main checkout (`/home/jakef/src/Vic3TimelineExtended`). Never commit to `main`.
- Brace-based Paradox `.txt` files use **tab** indentation and carry a **UTF-8 BOM**. After editing any, run `python3 scripts/format_paradox_tabs.py <files>` and confirm the BOM survived: `head -c3 <file> | xxd` → `efbb bf`. The `.gui` file also has a BOM and tab indentation; do not run the formatter on it, but do check its BOM.
- **Never `git commit -a`.** Stage by explicit path. `docs/engine/*` and `common/buy_packages/00_buy_packages.txt` carry unrelated reload churn — leave them unstaged.
- Use `python3` (there is no `python` alias). Do not start or restart the mod state server; the controller owns it.
- End every commit message with a truthful `Co-Authored-By: <your own model name> <noreply@anthropic.com>` line followed by `Claude-Session: https://claude.ai/code/session_01UGyJJaGL9ByF68uCVsgvzP`.
- After adding localization keys, run `python3 organize_loc.py` and stage whatever it moves. The new key prefixes (`iw_priority_*`, `je_iw_priority_*`, `je_iw_op_row_priority_*`) sit under existing `iw_` / `je_iw_` families; no new `startswith` rule is needed.
- Do not dispatch subagents. Do the work yourself.
- `test_covert_detection_roll.py` (slice 1) and `test_covert_exposure_tiers.py` (slice 2) must stay green after every task. In particular slice 1 pins the `covert_op_sync = { TYPE = … CODE = … }` row shape in `covert_ops_sync_all` and the `name = iw_type_code value = $CODE$` line in both `covert_op_create` and `covert_op_sync` — add new lines **next to** those, never edit them.
- Operation type codes (slice 1): `0` election_interference, `1` financial_subversion, `2` infrastructure_sabotage, `3` comms_disruption, `4` industrial_espionage, `5` military_espionage, `6` influence_campaign, `7` ideological_subversion, `8` destabilization.
- Engine rules that bite here:
  - `add_modifier = { multiplier = <script value> }` is re-evaluated against ROOT on later ticks. Only **constant** script values (no scope reads) may be multipliers in this system.
  - Do not read `scope:<container>.var:x`. To copy a container variable onto a country, go into the country from container scope and read `PREV.var:x` (the proven shape: `covert_warfare.1`'s `immediate`).
  - `change_variable` does not reliably resolve a script-value name as its operand. Accumulate with `set_variable = { name = x value = { value = var:x add = <script value> } }`.
  - `any_*` triggers never take `limit = { }`. `ordered_*` sorts **descending**, so `position = 0` is the largest `order_by`.
  - A trigger needs `var:` on its left; a script value goes only on the right.
  - Event and tooltip loc cannot reach a container (`TopScope` has no container accessor). Tooltips that describe a priority change branch in script and print constants through `GetPlayer.MakeScope.ScriptValue(…)`.

## Numbers this plan implements

| priority | effect × | upkeep weight | raw detection | reached by |
|---|---|---|---|---|
| 1 | 1 | 1 | +0 | default; every new and every pre-slice-3 operation |
| 2 | 1.35 | 1.6 | +2 points | stepper, or AI when rivalled with the target |
| 3 | 1.6 | 2.4 | +4 points | stepper, or a great-power AI at war with the target |

- **Effect** multiplies the phase multiplier: establishing = 1, fully operational = `covert_op_phase_full_mult` = 2 (the literal `multiplier = 2` this slice retires). Preparatory stays at no effect whatever the priority. So the six live multipliers are 1 / 1.35 / 1.6 (establishing) and 2 / 2.7 / 3.2 (fully operational).
- **Upkeep**: `covert_operation_cost_mult` = `(Σ weights + 1) × funding level × covert_operations_cost_scale`, where Σ weights used to be the pact count. Example: three operations at priority 1 cost 4 units; raising one to priority 3 costs 5.4 units (+35 % total upkeep for +60 % on one operation's effect). Cost outruns effect at every step — that is the diminishing return.
- **Detection**: `(priority − 1) × covert_op_priority_detect_add` is added to the raw chance next to the target counterintelligence penalty, **before** the covert-efficiency multiplier and the floor/cap. At base 10 % with no efficiency: 10 / 12 / 14 %. Late game (efficiency multiplier clamped at 0.2) the +4 becomes +0.8. A busier operation is more exposed; better tradecraft still hides it.

The election-interference confidence hit (`covert_op_election_confidence_effect`, −0.05 / −0.1 by phase on the target's election) is **not** scaled by priority in this slice: it is evaluated from the target's side over every attacker's operation and uses `add_electoral_confidence` with a literal. The operation's main modifier (`covert_election_interference`) is scaled. Say so in the docs (Task 7).

## Stepper: the one unproven engine link

The row passes its container as `AddScope('iw_op', ScriptContainer.MakeScope)` into `covert_priority_up_sgui` / `covert_priority_down_sgui` (`saved_scopes = { iw_op }`). Passing an **object** through `AddScope` into a scripted GUI's `saved_scopes` has no vanilla precedent; the stand-down button (#320) relies on the same link for a country and has not yet been confirmed in game. Both handlers are **fail-closed**: `is_valid` requires the scope to exist, to carry the `iw_op` tag and to be in *our* `iw_ops` list, so the worst case is a greyed-out stepper — never a change to the wrong operation or to another country's. The console harness (Task 7) changes a priority through the shipping step effect without the GUI, so every mechanic except the click is testable in game regardless.

**Named contingency — do not build unless the in-game check fails:** if the container does not arrive, replace the two handlers with per-type handlers in the stand-down shape (the row's per-tag markup picks the type; the target country travels as `AddScope('iw_tgt', …Var('iw_target_capital').GetState.GetCountry.MakeScope)`; the direction is a separate handler per type), i.e. 18 handlers. That would be a follow-up commit on this branch after play-testing.

## File structure

| File | Responsibility in this slice |
|---|---|
| `common/script_values/covert_warfare_script_values.txt` | Section 1 constants; six effect multipliers; `covert_op_effect_mult`; cost units; detection penalty; display values |
| `common/scripted_triggers/covert_warfare_triggers.txt` | `covert_op_priority_at_least`; the stepper's fail-closed eligibility |
| `common/scripted_effects/covert_warfare_effects.txt` | `iw_priority` on create/backfill; the scaled-modifier helper and every apply site; cost refresh; detection staging; step effects; AI management |
| `common/journal_entries/je_covert_warfare.txt` | AI priority call in the monthly pulse |
| `common/scripted_guis/covert_warfare_sguis.txt` | two stepper handlers; a ready-gate |
| `gui/journal_entry_widgets/covert_operations_widget.gui` | per-row stepper and priority line |
| `localization/english/te_miscellaneous_l_english.yml`, `te_journal_entries_l_english.yml`, `te_events_l_english.yml` | tooltips, row text, harness option |
| `common/scripted_effects/te_debug_covert_effects.txt`, `events/te_debug_covert_events.txt` | a harness option that maxes one operation's priority |
| `test_covert_priority.py` | new structural test for this slice |
| `docs/systems/mod_systems.md`, `docs/systems/journal_entry_systems.md` (CRLF) | documentation |

## Review Focus

1. **A save made before this slice.** Containers have no `iw_priority` and the country has no `iw_priority_cost_sum` until the first monthly pulse. Expected: nothing errors, the row's priority UI stays hidden until the pulse (like the phase lines), upkeep falls back to the pact count, and the first sync backfills priority 1 before detection is refreshed. Pinned in Task 1 (backfill precedes `covert_op_refresh_detection`), Task 3 (cost fallback) and Task 5 (ready-gate on the row).
2. **A priority-3 operation that ends** — stood down, burned by detection, or reaped by the sync because its pact lapsed. Expected: upkeep drops the same day, not at the next pulse. Pinned in Task 3 (`covert_op_destroy`, `covert_op_create` and `covert_ops_sync_all` all refresh the sum).
3. **The stepper's saved scope arrives unset, or points at something else.** Expected: both buttons are disabled with a readable reason, and a click can never change another row's operation or another country's. Pinned in Task 5 (the trigger requires `exists`, the `iw_op` tag and membership of our own `iw_ops`).
4. **Two operations of the same self-side type at different priority and phase** (e.g. two industrial espionage operations, one fully operational at priority 1, one establishing at priority 3). Expected: the self modifier is applied from the operation with the **largest effect multiplier** (2 vs 1.6 → the fully operational one), not merely the best phase. Pinned in Task 2 (`order_by = covert_op_effect_mult`).
5. **Priority changed while funding is 0.** At funding 0 every pact lapses at its next evaluation, so this is nearly unreachable, but the click is allowed: the variable and the cost sum move, no effects are applied (the step effect gates `covert_ops_apply_all_phase_effects` on funding ≥ 1, exactly as the pulse does), and upkeep stays 0 because funding multiplies it. Pinned in Task 5.

---

### Task 1: The priority variable and the effect multipliers

**Files:**
- Modify: `common/script_values/covert_warfare_script_values.txt` (Section 1 constants; a new section at the end)
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (after `covert_op_is_fully_operational`)
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (`covert_op_create`, `covert_op_sync`, file header comment)
- Test: `test_covert_priority.py` (create)

**Interfaces:**
- Produces: container variable `iw_priority` (1–3; written on create, backfilled by the sync). Scripted trigger `covert_op_priority_at_least = { N = <2|3> }` (container scope; false when the variable is missing). Constants `covert_op_priority_max`, `covert_op_priority_2_effect_mult`, `covert_op_priority_3_effect_mult`, `covert_op_priority_2_cost_mult`, `covert_op_priority_3_cost_mult`, `covert_op_priority_detect_add`, `covert_op_phase_full_mult`. Constant script values `covert_op_mult_p2_pri1`, `…_p2_pri2`, `…_p2_pri3`, `…_p3_pri1`, `…_p3_pri2`, `…_p3_pri3`. Container-scope script value `covert_op_effect_mult`.
- Consumes: `covert_op_is_established`, `covert_op_is_fully_operational` (existing).

- [ ] **Step 1: Write the failing test**

Create `test_covert_priority.py`:

```python
"""Structural tests for covert warfare slice 3 (per-operation priority).

Priority is one container variable. These tests pin where it is written,
that every effect is scaled through constant script values (the engine
re-evaluates an add_modifier multiplier against ROOT, so a container-scope
value cannot be one), that upkeep and detection read it, and that the row
stepper fails closed.
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
SGUIS = ROOT / "common/scripted_guis/covert_warfare_sguis.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"
LOC_DIR = ROOT / "localization/english"

MULT_VALUES = tuple(
    "covert_op_mult_p%d_pri%d" % (phase, pri) for phase in (2, 3) for pri in (1, 2, 3)
)


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    block = body[body.index(header):]
    return block[: block.index("\n}\n") + 3]


def _all_loc():
    return "".join(p.read_text(encoding="utf-8-sig") for p in LOC_DIR.rglob("*.yml"))


class PriorityVariableTests(unittest.TestCase):
    def test_create_writes_priority_one(self):
        create = _top_level_block(_text(EFFECTS), "covert_op_create = {")
        self.assertIn("set_variable = { name = iw_priority value = 1 }", create)

    def test_sync_backfills_priority_before_refreshing_detection(self):
        # Detection reads the priority (Task 4), so an old-save container
        # must have one before covert_op_refresh_detection runs.
        sync = _top_level_block(_text(EFFECTS), "covert_op_sync = {")
        backfill = sync.index("NOT = { has_variable = iw_priority }")
        refresh = sync.rindex("covert_op_refresh_detection")
        self.assertLess(backfill, refresh)

    def test_priority_trigger_is_guarded(self):
        block = _top_level_block(_text(TRIGGERS), "covert_op_priority_at_least = {")
        self.assertIn("has_variable = iw_priority", block)
        self.assertIn("var:iw_priority >= $N$", block)


class EffectMultiplierTests(unittest.TestCase):
    def test_constants_exist(self):
        body = _text(VALUES)
        for name, value in (
            ("covert_op_priority_max", "3"),
            ("covert_op_priority_2_effect_mult", "1.35"),
            ("covert_op_priority_3_effect_mult", "1.6"),
            ("covert_op_priority_2_cost_mult", "1.6"),
            ("covert_op_priority_3_cost_mult", "2.4"),
            ("covert_op_priority_detect_add", "2"),
            ("covert_op_phase_full_mult", "2"),
        ):
            self.assertRegex(body, r"(?m)^%s = %s$" % (name, re.escape(value)))

    def test_six_multipliers_are_derived_from_the_constants(self):
        body = _text(VALUES)
        for name in MULT_VALUES:
            block = _top_level_block(body, "%s = {" % name)
            # Constant: no variable, scope or trigger read, so safe as a
            # multiplier the engine re-evaluates against ROOT.
            self.assertNotIn("var:", block, name)
            self.assertNotIn("limit", block, name)
        self.assertIn("covert_op_phase_full_mult", _top_level_block(body, "covert_op_mult_p3_pri1 = {"))
        self.assertIn("covert_op_priority_3_effect_mult", _top_level_block(body, "covert_op_mult_p3_pri3 = {"))
        self.assertIn("covert_op_priority_2_effect_mult", _top_level_block(body, "covert_op_mult_p2_pri2 = {"))

    def test_effect_mult_is_zero_before_establishing(self):
        block = _top_level_block(_text(VALUES), "covert_op_effect_mult = {")
        self.assertIn("value = 0", block)
        self.assertIn("covert_op_is_fully_operational = yes", block)
        self.assertIn("covert_op_is_established = yes", block)
        self.assertIn("covert_op_priority_at_least = { N = 3 }", block)

    def test_values_file_parses(self):
        parser = ParadoxFileParser()
        parser.parse_file(str(VALUES), apply_directives=False)
        for name in MULT_VALUES + ("covert_op_effect_mult",):
            self.assertIn(name, parser.data)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_priority -v`
Expected: FAIL — `covert_op_create` has no `iw_priority`, and the constants do not exist.

- [ ] **Step 3: Add the constants**

In `common/script_values/covert_warfare_script_values.txt` Section 1, directly after `iw_funding_level_max = 5`, add:

```
# ---- Per-operation priority (slice 3) ----
# An operation's priority (iw_priority on its container, 1 when missing)
# multiplies what it does, what it costs and how exposed it is. Cost outruns
# effect at every step: that is the diminishing return that stops "everything
# at 3" from being the answer.
covert_op_priority_max = 3
covert_op_priority_2_effect_mult = 1.35
covert_op_priority_3_effect_mult = 1.6
# Each operation's share of the covert budget (priority 1 = one share).
covert_op_priority_2_cost_mult = 1.6
covert_op_priority_3_cost_mult = 2.4
# Raw detection points per priority level above 1, added before covert
# efficiency (so late-game tradecraft still hides most of it).
covert_op_priority_detect_add = 2
# A fully operational operation works at this multiple of an establishing one.
# Replaces the literal `multiplier = 2` the apply sites used to carry.
covert_op_phase_full_mult = 2
```

- [ ] **Step 4: Add the multipliers and `covert_op_effect_mult`**

Append to the end of the same file:

```
# ============================================================================
# SECTION: PER-OPERATION PRIORITY (slice 3)
# ============================================================================
# add_modifier's multiplier is stored with the modifier and re-evaluated
# against ROOT on later ticks, so it cannot be a value that reads the
# operation's container. Every apply site therefore goes through
# covert_op_add_scaled_modifier (covert_warfare_effects.txt), which branches
# phase x priority onto one of these six CONSTANT values. Keep them free of
# var:, scope: and trigger reads.

covert_op_mult_p2_pri1 = {
	value = 1
}

covert_op_mult_p2_pri2 = {
	value = covert_op_priority_2_effect_mult
}

covert_op_mult_p2_pri3 = {
	value = covert_op_priority_3_effect_mult
}

covert_op_mult_p3_pri1 = {
	value = covert_op_phase_full_mult
}

covert_op_mult_p3_pri2 = {
	value = covert_op_phase_full_mult
	multiply = covert_op_priority_2_effect_mult
}

covert_op_mult_p3_pri3 = {
	value = covert_op_phase_full_mult
	multiply = covert_op_priority_3_effect_mult
}

# The same product, evaluated ON the container, for choosing between
# operations (never as a multiplier). 0 while preparatory, which is what
# makes a preparatory operation lose to any working one.
# Scope: covert operation container
covert_op_effect_mult = {
	value = 0
	if = {
		limit = { covert_op_is_fully_operational = yes }
		add = covert_op_phase_full_mult
	}
	else_if = {
		limit = { covert_op_is_established = yes }
		add = 1
	}
	if = {
		limit = { covert_op_priority_at_least = { N = 3 } }
		multiply = covert_op_priority_3_effect_mult
	}
	else_if = {
		limit = { covert_op_priority_at_least = { N = 2 } }
		multiply = covert_op_priority_2_effect_mult
	}
}
```

- [ ] **Step 5: Add the priority trigger**

In `common/scripted_triggers/covert_warfare_triggers.txt`, directly after the `covert_op_is_fully_operational` block, add:

```

# True when the operation's priority is at least $N$. A container without
# iw_priority (a save made before slice 3, until the first monthly sync) reads
# as priority 1, so this is false for it.
# Parameters: $N$ = 2 or 3
# Scope: covert operation container
covert_op_priority_at_least = {
	has_variable = iw_priority
	var:iw_priority >= $N$
}
```

- [ ] **Step 6: Write the priority on create and backfill it in the sync**

In `common/scripted_effects/covert_warfare_effects.txt`:

(a) In `covert_op_create`, directly after the line `set_variable = { name = iw_type_code value = $CODE$ }`, add:

```
			set_variable = { name = iw_priority value = 1 }
```

(b) In `covert_op_sync`, in the final `every_in_list` (the one that currently reads `remove_variable = iw_seen`, `set_variable = { name = iw_type_code value = $CODE$ }`, `covert_op_refresh_detection = …`), insert between the `iw_type_code` line and the `covert_op_refresh_detection` line:

```
				# Old-save backfill: detection reads the priority, so it must
				# exist before covert_op_refresh_detection runs.
				if = {
					limit = { NOT = { has_variable = iw_priority } }
					set_variable = { name = iw_priority value = 1 }
				}
```

(c) In the file's header comment, add a line to the `vars` list after `iw_tgt_td`:

```
#           iw_priority        1-3; multiplies effect, upkeep share and detection
#                              (covert_warfare_script_values.txt, slice 3 section)
```

- [ ] **Step 7: Format and run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/covert_warfare_script_values.txt common/scripted_triggers/covert_warfare_triggers.txt common/scripted_effects/covert_warfare_effects.txt
for f in common/script_values/covert_warfare_script_values.txt common/scripted_triggers/covert_warfare_triggers.txt common/scripted_effects/covert_warfare_effects.txt; do head -c3 "$f" | xxd | head -1; done
python3 -m unittest test_covert_priority test_covert_detection_roll test_covert_exposure_tiers -v
```

Expected: each `xxd` line starts `efbb bf`; all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add common/script_values/covert_warfare_script_values.txt common/scripted_triggers/covert_warfare_triggers.txt common/scripted_effects/covert_warfare_effects.txt test_covert_priority.py
git commit -m "feat(covert): give every operation a priority and derive its effect multipliers"
```

---

### Task 2: Scale every effect through one helper

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (`covert_op_apply_target_effect`, `covert_op_apply_self_effect`, `covert_ops_apply_all_phase_effects`, a new helper above them)
- Test: `test_covert_priority.py` (add a class)

**Interfaces:**
- Consumes: the six `covert_op_mult_p*_pri*` values, `covert_op_effect_mult`, `covert_op_priority_at_least` (Task 1).
- Produces: scripted effect `covert_op_add_scaled_modifier = { MODIFIER = <static modifier> MONTHS = <literal> }` — scope: whatever receives the modifier (country, state or political movement); requires `scope:iw_op` = the operation container. Adds nothing while that operation is preparatory. It only **adds**; callers still `remove_modifier` first.

- [ ] **Step 1: Write the failing test**

Append to `test_covert_priority.py` (above the `if __name__` line):

```python
class ScaledApplicationTests(unittest.TestCase):
    def test_no_literal_phase_multiplier_is_left(self):
        body = _text(EFFECTS)
        self.assertNotRegex(
            body,
            r"multiplier = 2\b",
            "every phase multiplier must go through covert_op_add_scaled_modifier",
        )

    def test_helper_uses_all_six_constant_multipliers(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_add_scaled_modifier = {")
        for name in MULT_VALUES:
            self.assertIn("multiplier = %s" % name, block)
        self.assertIn("scope:iw_op = { covert_op_is_fully_operational = yes }", block)
        self.assertIn("scope:iw_op = { covert_op_is_established = yes }", block)

    def test_target_and_self_helpers_call_the_scaled_helper(self):
        body = _text(EFFECTS)
        for name in ("covert_op_apply_target_effect", "covert_op_apply_self_effect"):
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("covert_op_add_scaled_modifier = { MODIFIER = $MODIFIER$", block)

    def test_self_effect_picks_the_strongest_operation_not_the_best_phase(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_apply_self_effect = {")
        self.assertIn("ordered_in_list = {", block)
        self.assertIn("order_by = covert_op_effect_mult", block)
        self.assertIn("position = 0", block)
        self.assertIn("save_scope_as = iw_op", block)

    def test_every_bespoke_site_calls_the_helper(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        for modifier in (
            "covert_infrastructure_sabotage",
            "covert_military_espionage",
            "covert_destabilization_separatist",
            "covert_destabilization_general",
        ):
            self.assertIn(
                "covert_op_add_scaled_modifier = { MODIFIER = %s MONTHS = 3 }" % modifier,
                block,
            )

    def test_ideological_pressure_scales_with_priority(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        for pri in (1, 2, 3):
            self.assertIn("MULT = covert_op_mult_p2_pri%d" % pri, block)
        self.assertNotIn("MULT = 1 ", block)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_priority -v`
Expected: FAIL — `multiplier = 2` still present and the helper does not exist.

- [ ] **Step 3: Add the helper and rewrite the two generic appliers**

In `common/scripted_effects/covert_warfare_effects.txt`, replace the comment block that begins `# PHASE-BASED EFFECT APPLICATION` through the end of `covert_op_apply_self_effect` (currently lines 326–387) with:

```
# ============================================================================
# PHASE-BASED EFFECT APPLICATION
# ============================================================================
# Phase 1 (months 0-5): Preparatory — no effect
# Phase 2 (months 6-11): Establishing — base multiplier
# Phase 3 (months 12+): Fully Operational — covert_op_phase_full_mult
# Each is then scaled by the operation's priority (slice 3). The product is
# one of six constant script values, chosen here, because add_modifier's
# multiplier is re-evaluated against ROOT on later ticks and so cannot read
# the container. Phase triggers (container scope): covert_op_is_established,
# covert_op_is_fully_operational; priority: covert_op_priority_at_least.

# Add $MODIFIER$ to the current scope, scaled by scope:iw_op's phase and
# priority. Adds nothing while that operation is preparatory. Callers remove
# the modifier first, so a preparatory operation leaves none behind.
# Parameters: $MODIFIER$ = static modifier, $MONTHS$ = duration (literal)
# Scope: the country, state or political movement receiving the modifier;
#        scope:iw_op = the operation container
covert_op_add_scaled_modifier = {
	if = {
		limit = { scope:iw_op = { covert_op_is_fully_operational = yes } }
		if = {
			limit = { scope:iw_op = { covert_op_priority_at_least = { N = 3 } } }
			add_modifier = { name = $MODIFIER$ multiplier = covert_op_mult_p3_pri3 months = $MONTHS$ }
		}
		else_if = {
			limit = { scope:iw_op = { covert_op_priority_at_least = { N = 2 } } }
			add_modifier = { name = $MODIFIER$ multiplier = covert_op_mult_p3_pri2 months = $MONTHS$ }
		}
		else = {
			add_modifier = { name = $MODIFIER$ multiplier = covert_op_mult_p3_pri1 months = $MONTHS$ }
		}
	}
	else_if = {
		limit = { scope:iw_op = { covert_op_is_established = yes } }
		if = {
			limit = { scope:iw_op = { covert_op_priority_at_least = { N = 3 } } }
			add_modifier = { name = $MODIFIER$ multiplier = covert_op_mult_p2_pri3 months = $MONTHS$ }
		}
		else_if = {
			limit = { scope:iw_op = { covert_op_priority_at_least = { N = 2 } } }
			add_modifier = { name = $MODIFIER$ multiplier = covert_op_mult_p2_pri2 months = $MONTHS$ }
		}
		else = {
			add_modifier = { name = $MODIFIER$ multiplier = covert_op_mult_p2_pri1 months = $MONTHS$ }
		}
	}
}

# Apply a country-scoped modifier to the TARGET of each $TYPE$ operation,
# at that operation's own phase and priority.
# Parameters: $TYPE$, $MODIFIER$
# Scope: country (ROOT = JE owner / operator)
covert_op_apply_target_effect = {
	every_in_list = {
		variable = iw_ops
		limit = { has_tag = iw_op_$TYPE$ }
		save_scope_as = iw_op
		var:iw_target = {
			remove_modifier = $MODIFIER$
			covert_op_add_scaled_modifier = { MODIFIER = $MODIFIER$ MONTHS = 3 }
		}
	}
}

# Apply a country-scoped modifier to SELF for a given operation type, from the
# operation of that type with the largest effect multiplier (phase x
# priority). ordered_* sorts descending, so position 0 is the strongest; a
# preparatory operation scores 0 and adds nothing.
# Parameters: $TYPE$, $MODIFIER$
# Scope: country (ROOT = JE owner / operator)
covert_op_apply_self_effect = {
	if = {
		limit = { any_in_list = { variable = iw_ops has_tag = iw_op_$TYPE$ } }
		remove_modifier = $MODIFIER$
		ordered_in_list = {
			variable = iw_ops
			limit = { has_tag = iw_op_$TYPE$ }
			order_by = covert_op_effect_mult
			position = 0
			save_scope_as = iw_op
		}
		covert_op_add_scaled_modifier = { MODIFIER = $MODIFIER$ MONTHS = 3 }
	}
}
```

- [ ] **Step 4: Rewrite the bespoke sites in `covert_ops_apply_all_phase_effects`**

Replace the whole `covert_ops_apply_all_phase_effects = { … }` block with:

```
# Master effect: apply ALL 9 operation types' phase-based effects.
# Only runs if funding > 0, after covert_ops_sync_all. Called monthly from the
# JE pulse and after a priority step.
# The helpers it calls iterate iw_ops unguarded; the has_variable_list check here covers them.
# Scope: country (ROOT = JE owner)
covert_ops_apply_all_phase_effects = {
	if = {
		limit = { has_variable_list = iw_ops }
		# ---- Election Interference: country modifier on TARGET ----
		covert_op_apply_target_effect = { TYPE = election_interference MODIFIER = covert_election_interference }

		# ---- Financial Subversion: country modifier on TARGET ----
		covert_op_apply_target_effect = { TYPE = financial_subversion MODIFIER = covert_financial_subversion }

		# ---- Infrastructure Sabotage: country morale modifier + state modifier on a random TARGET state ----
		covert_op_apply_target_effect = { TYPE = infrastructure_sabotage MODIFIER = covert_infra_sabotage_morale }
		every_in_list = {
			variable = iw_ops
			limit = {
				has_tag = iw_op_infrastructure_sabotage
				covert_op_is_established = yes
			}
			save_scope_as = iw_op
			var:iw_target = {
				random_scope_state = {
					limit = { any_scope_building = { level >= 1 } }
					remove_modifier = covert_infrastructure_sabotage
					covert_op_add_scaled_modifier = { MODIFIER = covert_infrastructure_sabotage MONTHS = 3 }
				}
			}
		}

		# ---- Communications Disruption: country modifier on TARGET ----
		covert_op_apply_target_effect = { TYPE = comms_disruption MODIFIER = covert_comms_disruption }

		# ---- Industrial Espionage: self modifiers (innovation + tech spread) ----
		# Innovation is always applied; tech spread always applies since target must have tech advantage
		covert_op_apply_self_effect = { TYPE = industrial_espionage MODIFIER = covert_espionage_base }
		covert_op_apply_self_effect = { TYPE = industrial_espionage MODIFIER = covert_industrial_espionage }
		# Weak counter-intel marker on the TARGET so covert_warfare.2 can notify them (#158)
		covert_op_apply_target_effect = { TYPE = industrial_espionage MODIFIER = covert_industrial_espionage_detected }

		# ---- Military Espionage: self modifiers (unit stats always, tech spread conditional) ----
		covert_op_apply_self_effect = { TYPE = military_espionage MODIFIER = covert_military_espionage_unit }
		# Weak counter-intel marker on the TARGET so covert_warfare.2 can notify them (#158)
		covert_op_apply_target_effect = { TYPE = military_espionage MODIFIER = covert_military_espionage_detected }
		# Conditional tech spread: only if target has tech advantage, from the
		# strongest military espionage operation (phase x priority)
		if = {
			limit = {
				any_in_list = {
					variable = iw_ops
					has_tag = iw_op_military_espionage
					covert_op_is_established = yes
				}
			}
			every_in_list = {
				variable = iw_ops
				limit = { has_tag = iw_op_military_espionage }
				var:iw_target = { save_scope_as = espionage_target }
			}
			if = {
				limit = {
					exists = scope:espionage_target
					espionage_target_tech_advantage > 0
				}
				remove_modifier = covert_military_espionage
				ordered_in_list = {
					variable = iw_ops
					limit = { has_tag = iw_op_military_espionage }
					order_by = covert_op_effect_mult
					position = 0
					save_scope_as = iw_op
				}
				covert_op_add_scaled_modifier = { MODIFIER = covert_military_espionage MONTHS = 3 }
			}
		}

		# ---- Influence Campaign: country modifier on TARGET ----
		covert_op_apply_target_effect = { TYPE = influence_campaign MODIFIER = covert_influence_campaign }

		# ---- Ideological Subversion: country resist modifier + movement modifiers on TARGET ----
		covert_op_apply_target_effect = { TYPE = ideological_subversion MODIFIER = covert_ideological_subversion_resist }
		# Movement pressure from the establishing phase on, at the same
		# strength once fully operational — so it scales by priority only
		# (the establishing-phase column of the multiplier table).
		every_in_list = {
			variable = iw_ops
			limit = {
				has_tag = iw_op_ideological_subversion
				covert_op_is_established = yes
			}
			ROOT = { save_scope_as = cultural_hegemon }
			if = {
				limit = { covert_op_priority_at_least = { N = 3 } }
				var:iw_target = {
					ch_apply_hegemon_movement_pressure = { MODIFIER = covert_ideological_subversion FALLBACK_MODIFIER = covert_ideological_subversion MONTHS = 3 DECAYING = no MULT = covert_op_mult_p2_pri3 }
				}
			}
			else_if = {
				limit = { covert_op_priority_at_least = { N = 2 } }
				var:iw_target = {
					ch_apply_hegemon_movement_pressure = { MODIFIER = covert_ideological_subversion FALLBACK_MODIFIER = covert_ideological_subversion MONTHS = 3 DECAYING = no MULT = covert_op_mult_p2_pri2 }
				}
			}
			else = {
				var:iw_target = {
					ch_apply_hegemon_movement_pressure = { MODIFIER = covert_ideological_subversion FALLBACK_MODIFIER = covert_ideological_subversion MONTHS = 3 DECAYING = no MULT = covert_op_mult_p2_pri1 }
				}
			}
		}

		# ---- Destabilization: country resist modifier + movement modifiers on TARGET ----
		covert_op_apply_target_effect = { TYPE = destabilization MODIFIER = covert_destabilization_resist }
		every_in_list = {
			variable = iw_ops
			limit = {
				has_tag = iw_op_destabilization
				covert_op_is_established = yes
			}
			save_scope_as = iw_op
			var:iw_target = {
				# Separatist movement pressure
				every_political_movement = {
					remove_modifier = covert_destabilization_separatist
					covert_op_add_scaled_modifier = { MODIFIER = covert_destabilization_separatist MONTHS = 3 }
				}
				# General destabilization pressure
				remove_modifier = covert_destabilization_general
				covert_op_add_scaled_modifier = { MODIFIER = covert_destabilization_general MONTHS = 3 }
			}
		}
	}
}
```

`ch_apply_hegemon_movement_pressure` passes `MULT` straight into `add_modifier = { … multiplier = $MULT$ }` (`cultural_hegemony_effects.txt:980`), whose header says `MULT` may be "1, or a script value name"; `covert_op_mult_p2_pri1` is 1, so priority-1 behaviour is unchanged.

- [ ] **Step 5: Format and run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt
head -c3 common/scripted_effects/covert_warfare_effects.txt | xxd | head -1
python3 -m unittest test_covert_priority test_covert_detection_roll test_covert_exposure_tiers -v
```

Expected: `efbb bf`; all PASS.

- [ ] **Step 6: Commit**

```bash
git add common/scripted_effects/covert_warfare_effects.txt test_covert_priority.py
git commit -m "feat(covert): scale every operation effect by phase and priority through one helper"
```

---

### Task 3: Weight upkeep by priority

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (new `covert_refresh_priority_cost`; calls from `covert_op_create`, `covert_op_destroy`, `covert_ops_sync_all`)
- Modify: `common/script_values/covert_warfare_script_values.txt` (`covert_priority_cost_units`; three cost values)
- Modify: `common/journal_entries/je_covert_warfare.txt` (the AI funding comment's cost formula)
- Test: `test_covert_priority.py` (add a class)

**Interfaces:**
- Consumes: `covert_op_priority_at_least`, `covert_op_priority_2_cost_mult`, `covert_op_priority_3_cost_mult` (Task 1).
- Produces: scripted effect `covert_refresh_priority_cost = yes` (operator country scope; recomputes country variable `iw_priority_cost_sum`). Script value `covert_priority_cost_units` (country scope; the sum, or the live pact count when the sum was never computed).

`covert_operations_active` stays: the AI funding branches, `covert_operations_available_slots` and the slot display still read it. Only the three **cost** values switch.

- [ ] **Step 1: Write the failing test**

Append to `test_covert_priority.py`:

```python
class UpkeepTests(unittest.TestCase):
    COST_VALUES = (
        "covert_operation_cost_mult",
        "covert_operation_cost_at_next_up",
        "covert_operation_cost_at_next_down",
    )

    def test_cost_values_read_the_priority_weighted_units(self):
        body = _text(VALUES)
        for name in self.COST_VALUES:
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("add = covert_priority_cost_units", block, name)
            self.assertNotIn("covert_operations_active", block, name)

    def test_units_fall_back_to_the_pact_count_before_the_first_refresh(self):
        block = _top_level_block(_text(VALUES), "covert_priority_cost_units = {")
        self.assertIn("has_variable = iw_priority_cost_sum", block)
        self.assertIn("add = var:iw_priority_cost_sum", block)
        self.assertIn("add = covert_operations_active", block)

    def test_refresh_accumulates_with_set_variable_not_change_variable(self):
        # change_variable does not reliably resolve a script-value operand.
        block = _top_level_block(_text(EFFECTS), "covert_refresh_priority_cost = {")
        self.assertIn("covert_op_priority_3_cost_mult", block)
        self.assertIn("covert_op_priority_2_cost_mult", block)
        self.assertNotIn("change_variable", block)

    def test_every_path_that_adds_or_ends_an_operation_refreshes_the_sum(self):
        body = _text(EFFECTS)
        for name in ("covert_op_create", "covert_op_destroy", "covert_ops_sync_all"):
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("covert_refresh_priority_cost = yes", block, name)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_priority -v`
Expected: FAIL — `covert_priority_cost_units` does not exist.

- [ ] **Step 3: Add the refresh effect**

In `common/scripted_effects/covert_warfare_effects.txt`, directly after `covert_op_burn` (before the `MONTHLY RECONCILIATION` banner), add:

```

# Recompute iw_priority_cost_sum: each running operation's share of the covert
# budget (1 at priority 1, covert_op_priority_2/3_cost_mult above). The upkeep
# values read this instead of the pact count, so a priority-3 operation costs
# 2.4 shares. Called from covert_op_create and covert_op_destroy (every path
# that starts or ends an operation goes through one of them, so upkeep moves
# the same day), from the tail of covert_ops_sync_all (which also reaps
# containers directly), and after a priority step.
# Accumulates with set_variable's inline value block: change_variable does not
# reliably resolve a script-value operand.
# Scope: operator country
covert_refresh_priority_cost = {
	save_scope_as = iw_cost_operator
	set_variable = { name = iw_priority_cost_sum value = 0 }
	if = {
		limit = { has_variable_list = iw_ops }
		every_in_list = {
			variable = iw_ops
			if = {
				limit = { covert_op_priority_at_least = { N = 3 } }
				scope:iw_cost_operator = {
					set_variable = { name = iw_priority_cost_sum value = { value = var:iw_priority_cost_sum add = covert_op_priority_3_cost_mult } }
				}
			}
			else_if = {
				limit = { covert_op_priority_at_least = { N = 2 } }
				scope:iw_cost_operator = {
					set_variable = { name = iw_priority_cost_sum value = { value = var:iw_priority_cost_sum add = covert_op_priority_2_cost_mult } }
				}
			}
			else = {
				scope:iw_cost_operator = {
					set_variable = { name = iw_priority_cost_sum value = { value = var:iw_priority_cost_sum add = 1 } }
				}
			}
		}
	}
}
```

- [ ] **Step 4: Call it wherever an operation starts or ends**

(a) `covert_op_create`: inside the `if = { limit = { exists = scope:iw_new_op } … }`, after the `add_to_variable_list` line, add `covert_refresh_priority_cost = yes`.

(b) `covert_op_destroy`: inside its outer `if`, after `scope:iw_ended_op = { destroy_container = yes }`, add `covert_refresh_priority_cost = yes`.

(c) `covert_ops_sync_all`: after the ninth `covert_op_sync = { … }` row, add:

```
	# The sync reaps lapsed containers without going through covert_op_destroy.
	covert_refresh_priority_cost = yes
```

Also change that effect's header comment from "Reconcile all 9 operation types." to "Reconcile all 9 operation types, then recompute the upkeep weights."

- [ ] **Step 5: Switch the three cost values**

In `common/script_values/covert_warfare_script_values.txt` Section 3, directly after `covert_operations_available_slots`, add:

```

# Operations as the upkeep counts them: the sum of every operation's
# priority-weighted share (iw_priority_cost_sum, covert_refresh_priority_cost).
# A save made before slice 3 has no sum until the first refresh, and gets the
# live pact count — exactly the old formula — in the meantime.
covert_priority_cost_units = {
	value = 0
	if = {
		limit = { has_variable = iw_priority_cost_sum }
		add = var:iw_priority_cost_sum
	}
	else = {
		add = covert_operations_active
	}
}
```

Then, in each of `covert_operation_cost_mult`, `covert_operation_cost_at_next_up` and `covert_operation_cost_at_next_down`, replace the line `add = covert_operations_active` with `add = covert_priority_cost_units`. In `covert_operation_cost_mult` also change its header comment line "Scales with number of active operations + 1 (base maintenance) and funding level" to "Scales with the priority-weighted operation count + 1 (base maintenance) and funding level".

- [ ] **Step 6: Fix the AI comment**

In `common/journal_entries/je_covert_warfare.txt`, the AI funding comment says `# Cost formula: (active_ops + 1) × funding_level × banking_event_expense_small`. Replace that line with:

```
			# Cost formula: (priority-weighted ops + 1) × funding_level × covert_operations_cost_scale
```

- [ ] **Step 7: Format and run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt common/journal_entries/je_covert_warfare.txt
for f in common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt common/journal_entries/je_covert_warfare.txt; do head -c3 "$f" | xxd | head -1; done
python3 -m unittest test_covert_priority test_covert_detection_roll test_covert_exposure_tiers -v
```

Expected: `efbb bf` ×3; all PASS.

- [ ] **Step 8: Commit**

```bash
git add common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt common/journal_entries/je_covert_warfare.txt test_covert_priority.py
git commit -m "feat(covert): weight covert upkeep by each operation's priority"
```

---

### Task 4: Raise detection with priority

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (`covert_op_refresh_detection`)
- Modify: `common/script_values/covert_warfare_script_values.txt` (`covert_op_priority_detect_penalty`; `covert_operation_detection_chance`)
- Test: `test_covert_priority.py` (add a class)

**Interfaces:**
- Consumes: `iw_priority` (Task 1), `covert_op_priority_detect_add` (Task 1).
- Produces: operator country variable `iw_priority_staging` (transient — written and removed inside `covert_op_refresh_detection`). Script value `covert_op_priority_detect_penalty` (operator country scope).

- [ ] **Step 1: Write the failing test**

Append to `test_covert_priority.py`:

```python
class DetectionTests(unittest.TestCase):
    def test_refresh_stages_the_priority_through_prev(self):
        block = _top_level_block(_text(EFFECTS), "covert_op_refresh_detection = {")
        stage = block.index("name = iw_priority_staging value = PREV.var:iw_priority")
        chance = block.index("value = covert_operation_detection_chance")
        self.assertLess(stage, chance, "stage the priority before the chance is computed")
        self.assertNotIn("scope:iw_op.var:", block)
        self.assertIn("remove_variable = iw_priority_staging", block)

    def test_penalty_is_guarded_and_uses_the_constant(self):
        block = _top_level_block(_text(VALUES), "covert_op_priority_detect_penalty = {")
        self.assertIn("has_variable = iw_priority_staging", block)
        self.assertIn("multiply = covert_op_priority_detect_add", block)

    def test_penalty_is_added_before_covert_efficiency(self):
        block = _top_level_block(_text(VALUES), "covert_operation_detection_chance = {")
        add = block.index("add = covert_op_priority_detect_penalty")
        efficiency = block.index("modifier:country_covert_operation_efficiency_mult")
        self.assertLess(add, efficiency)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_priority -v`
Expected: FAIL — no `iw_priority_staging`.

- [ ] **Step 3: Stage the priority**

Replace the whole `covert_op_refresh_detection = { … }` block in `common/scripted_effects/covert_warfare_effects.txt` with:

```
# Recompute the target and detection data the JE shows for one operation.
# covert_operation_detection_chance reads target_max_ic / target_type_defense /
# iw_priority_staging off the operator, so they are staged there first. The
# priority is copied with PREV.var: from inside the operator (PREV is this
# container); a scope:<container>.var: chain is avoided on purpose.
# Parameters: $DEFENSE_MOD$ = type-specific defense modifier
# Scope: operation container; scope:iw_operator = operator country
covert_op_refresh_detection = {
	save_scope_as = iw_op
	if = {
		limit = { has_variable = iw_priority }
		scope:iw_operator = { set_variable = { name = iw_priority_staging value = PREV.var:iw_priority } }
	}
	else = {
		scope:iw_operator = { set_variable = { name = iw_priority_staging value = 1 } }
	}
	var:iw_target = {
		capital = {
			scope:iw_op = { set_variable = { name = iw_target_capital value = PREV } }
		}
		scope:iw_operator = {
			set_variable = { name = target_max_ic value = PREV.intelligence_capacity_total }
			set_variable = { name = target_type_defense value = PREV.modifier:$DEFENSE_MOD$ }
			set_variable = { name = iw_detect_staging value = covert_operation_detection_chance }
		}
	}
	set_variable = { name = iw_detect value = scope:iw_operator.var:iw_detect_staging }
	set_variable = { name = iw_tgt_ic value = scope:iw_operator.var:target_max_ic }
	set_variable = { name = iw_tgt_td value = scope:iw_operator.var:target_type_defense }
	scope:iw_operator = {
		remove_variable = iw_detect_staging
		remove_variable = iw_priority_staging
	}
}
```

- [ ] **Step 4: Add the penalty to the chance**

In `common/script_values/covert_warfare_script_values.txt`, directly after `target_counterintelligence_penalty = { … }`, add:

```

# A higher-priority operation is busier and more exposed: covert_op_priority_detect_add
# raw points per level above 1. var:iw_priority_staging is staged per operation
# by covert_op_refresh_detection; missing reads as priority 1.
# Scope: operator country
covert_op_priority_detect_penalty = {
	value = 0
	if = {
		limit = { has_variable = iw_priority_staging }
		add = var:iw_priority_staging
		subtract = 1
		multiply = covert_op_priority_detect_add
		min = 0
	}
}
```

In `covert_operation_detection_chance`, directly after the line `add = target_counterintelligence_penalty`, add:

```
	# Priority: a busier operation is more exposed (before efficiency, so
	# better tradecraft still hides most of it)
	add = covert_op_priority_detect_penalty
```

And update that value's header formula line to: `# Formula: raw = base - funding_reduction + target_defense_penalty + priority_penalty, final = raw × (1 - efficiency), clamped [covert_ops_detection_floor, 50]`.

- [ ] **Step 5: Format and run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt
for f in common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt; do head -c3 "$f" | xxd | head -1; done
python3 -m unittest test_covert_priority test_covert_detection_roll test_covert_exposure_tiers -v
```

Expected: `efbb bf` ×2; all PASS.

- [ ] **Step 6: Commit**

```bash
git add common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt test_covert_priority.py
git commit -m "feat(covert): a higher-priority operation carries more detection risk"
```

---

### Task 5: The row stepper

**Files:**
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (a new section after STAND DOWN)
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (a new PRIORITY section after STAND DOWN)
- Modify: `common/script_values/covert_warfare_script_values.txt` (two display values in the slice-3 section)
- Modify: `common/scripted_guis/covert_warfare_sguis.txt` (two handlers, one ready-gate, header)
- Modify: `gui/journal_entry_widgets/covert_operations_widget.gui` (a stepper type, three priority lines, header)
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `localization/english/te_journal_entries_l_english.yml`
- Test: `test_covert_priority.py` (add a class)

**Interfaces:**
- Consumes: `covert_op_priority_at_least`, the constants (Task 1); `covert_refresh_priority_cost` (Task 3); `covert_refresh_funding_state`, `covert_ops_apply_all_phase_effects` (existing).
- Produces: triggers `covert_priority_op_is_ours`, `covert_possible_priority_up`, `covert_possible_priority_down` (country scope; `scope:iw_op` = the container). Effects `covert_effect_priority_up`, `covert_effect_priority_down` (country scope; `scope:iw_op`), shared tail `covert_apply_priority_change`. Scripted GUIs `covert_priority_up_sgui`, `covert_priority_down_sgui`, `covert_ops_priority_ready_sgui`. Task 6 (AI) and Task 7 (harness) call `covert_possible_priority_up/_down` and `covert_effect_priority_up`.

- [ ] **Step 1: Write the failing test**

Append to `test_covert_priority.py`:

```python
class StepperTests(unittest.TestCase):
    def test_identification_fails_closed(self):
        block = _top_level_block(_text(TRIGGERS), "covert_priority_op_is_ours = {")
        self.assertIn("exists = scope:iw_op", block)
        self.assertIn("is_target_in_variable_list = { name = iw_ops target = scope:iw_op }", block)
        self.assertIn("has_tag = iw_op", block)
        for name in ("covert_possible_priority_up", "covert_possible_priority_down"):
            gate = _top_level_block(_text(TRIGGERS), "%s = {" % name)
            self.assertIn("covert_priority_op_is_ours = yes", gate, name)
        self.assertIn(
            "covert_op_priority_max",
            _top_level_block(_text(TRIGGERS), "covert_possible_priority_up = {"),
        )

    def test_both_handlers_delegate_and_are_closed_to_the_ai(self):
        body = _text(SGUIS)
        for direction in ("up", "down"):
            block = _top_level_block(body, "covert_priority_%s_sgui = {" % direction)
            self.assertIn("saved_scopes = { iw_op }", block)
            self.assertIn("covert_possible_priority_%s = yes" % direction, block)
            self.assertIn("covert_effect_priority_%s = yes" % direction, block)
            self.assertRegex(block, r"ai_is_valid = \{\s*always = no\s*\}")

    def test_step_refreshes_cost_and_gates_effects_on_funding(self):
        block = _top_level_block(_text(EFFECTS), "covert_apply_priority_change = {")
        self.assertIn("covert_refresh_priority_cost = yes", block)
        self.assertIn("covert_refresh_funding_state = yes", block)
        self.assertIn("var:iw_funding_level >= 1", block)
        self.assertIn("covert_ops_apply_all_phase_effects = yes", block)

    def test_step_clamps_to_the_bounds(self):
        body = _text(EFFECTS)
        for direction in ("up", "down"):
            block = _top_level_block(body, "covert_effect_priority_%s = {" % direction)
            self.assertIn("clamp_variable = { name = iw_priority min = 1 max = covert_op_priority_max }", block)
            self.assertIn("covert_apply_priority_change = yes", block)

    def test_the_row_passes_its_container_in_a_single_addscope(self):
        gui = _text(WIDGET)
        call = "AddScope( 'iw_op', ScriptContainer.MakeScope )"
        self.assertEqual(gui.count(call), 4, "enabled + onclick on each of two buttons")
        self.assertIn("GetScriptedGui('covert_priority_up_sgui')", gui)
        self.assertIn("GetScriptedGui('covert_priority_down_sgui')", gui)

    def test_the_row_hides_priority_until_every_container_has_one(self):
        gui = _text(WIDGET)
        self.assertIn("covert_ops_priority_ready_sgui", gui)
        for pri in (1, 2, 3):
            self.assertIn("je_iw_op_row_priority_%d" % pri, gui)
        gate = _top_level_block(_text(SGUIS), "covert_ops_priority_ready_sgui = {")
        self.assertIn("NOT = { has_variable = iw_priority }", gate)

    def test_loc_keys_exist(self):
        loc = _all_loc()
        for key in (
            "iw_priority_op_known_tt", "iw_priority_op_ours_tt",
            "iw_priority_not_max_tt", "iw_priority_not_min_tt",
            "iw_priority_to_1_tt", "iw_priority_to_2_tt", "iw_priority_to_3_tt",
            "je_iw_priority_stepper_label",
            "je_iw_priority_step_up_tooltip", "je_iw_priority_step_down_tooltip",
            "je_iw_op_row_priority_1", "je_iw_op_row_priority_2", "je_iw_op_row_priority_3",
        ):
            self.assertIn(" %s:" % key, loc, key)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_priority -v`
Expected: FAIL — `covert_priority_op_is_ours` does not exist.

- [ ] **Step 3: Add the eligibility triggers**

In `common/scripted_triggers/covert_warfare_triggers.txt`, directly after `covert_possible_stand_down = { … }` and before the `EXPOSURE TIERS` banner, add:

```

# ============================================================================
# PRIORITY — shared eligibility
# ============================================================================
# Whether the operation a widget row is showing can have its priority changed.
# Called by the row stepper's scripted GUIs (is_valid) and by the AI's
# priority management, so the two cannot diverge.
#
# FAIL-CLOSED BY DESIGN, like covert_possible_stand_down. The row hands the
# operation's container to script as the saved scope iw_op; passing an object
# into a scripted GUI's saved_scopes has no vanilla precedent. If it arrives
# unset, or is anything but one of OUR running operations, the stepper greys
# out and does nothing.
# Scope: operator country; scope:iw_op = the operation container
covert_priority_op_is_ours = {
	custom_tooltip = {
		text = iw_priority_op_known_tt
		exists = scope:iw_op
	}
	custom_tooltip = {
		text = iw_priority_op_ours_tt
		exists = scope:iw_op
		has_variable_list = iw_ops
		is_target_in_variable_list = { name = iw_ops target = scope:iw_op }
		scope:iw_op = { has_tag = iw_op }
	}
}

covert_possible_priority_up = {
	covert_priority_op_is_ours = yes
	custom_tooltip = {
		text = iw_priority_not_max_tt
		scope:iw_op ?= {
			OR = {
				NOT = { has_variable = iw_priority }
				var:iw_priority < covert_op_priority_max
			}
		}
	}
	# Slice 5 adds its Tradecraft gate on the step to priority 3 here, as one
	# more custom_tooltip, so it binds the stepper and the AI alike.
}

covert_possible_priority_down = {
	covert_priority_op_is_ours = yes
	custom_tooltip = {
		text = iw_priority_not_min_tt
		scope:iw_op ?= {
			has_variable = iw_priority
			var:iw_priority > 1
		}
	}
}
```

- [ ] **Step 4: Add the step effects**

In `common/scripted_effects/covert_warfare_effects.txt`, directly after `covert_effect_stand_down = { … }` and before the `EXPOSURE BLOWBACK` banner, add:

```

# ============================================================================
# PRIORITY
# ============================================================================
# Raise or lower one operation's priority (1 .. covert_op_priority_max).
# Called by the row stepper's scripted GUIs, by the console harness, and — for
# the variable change only — mirrored by covert_ai_manage_priorities.
# Eligibility, including the fail-closed scope check, is in
# covert_possible_priority_up / _down (covert_warfare_triggers.txt).
#
# The tooltip branches here in script because tooltip loc cannot reach a
# container: it names the level the operation is moving TO and prints the
# constants for that level.
# Scope: operator country; scope:iw_op = the operation container

# Everything that must be true again once a priority has moved: upkeep, the
# JE's cost modifier and every operation's detection display
# (covert_refresh_funding_state runs the sync, which re-stages detection), and
# the effect modifiers — the last only while funded, exactly as the monthly
# pulse gates them. At funding 0 the click still moves the variable (and the
# upkeep share, which funding 0 multiplies to nothing).
covert_apply_priority_change = {
	covert_refresh_priority_cost = yes
	covert_refresh_funding_state = yes
	if = {
		limit = {
			has_variable = iw_funding_level
			var:iw_funding_level >= 1
		}
		covert_ops_apply_all_phase_effects = yes
	}
}

covert_effect_priority_up = {
	if = {
		limit = { scope:iw_op ?= { covert_op_priority_at_least = { N = 2 } } }
		custom_tooltip = iw_priority_to_3_tt
	}
	else = {
		custom_tooltip = iw_priority_to_2_tt
	}
	hidden_effect = {
		scope:iw_op ?= {
			if = {
				limit = { NOT = { has_variable = iw_priority } }
				set_variable = { name = iw_priority value = 1 }
			}
			change_variable = { name = iw_priority add = 1 }
			clamp_variable = { name = iw_priority min = 1 max = covert_op_priority_max }
		}
		covert_apply_priority_change = yes
	}
}

covert_effect_priority_down = {
	if = {
		limit = { scope:iw_op ?= { covert_op_priority_at_least = { N = 3 } } }
		custom_tooltip = iw_priority_to_2_tt
	}
	else = {
		custom_tooltip = iw_priority_to_1_tt
	}
	hidden_effect = {
		scope:iw_op ?= {
			if = {
				limit = { NOT = { has_variable = iw_priority } }
				set_variable = { name = iw_priority value = 1 }
			}
			change_variable = { name = iw_priority subtract = 1 }
			clamp_variable = { name = iw_priority min = 1 max = covert_op_priority_max }
		}
		covert_apply_priority_change = yes
	}
}
```

(`change_variable … add = 1` with a **literal** is fine; only script-value operands are unreliable. `clamp_variable … max = <script value>` is the existing funding-stepper idiom.)

- [ ] **Step 5: Add the display values**

In the slice-3 section at the end of `common/script_values/covert_warfare_script_values.txt`, append:

```

# The detection points each priority level adds, for the row and the stepper
# tooltips. Derived so they cannot drift from covert_op_priority_detect_add.
covert_op_priority_2_detect_display = {
	value = covert_op_priority_detect_add
	round = yes
}

covert_op_priority_3_detect_display = {
	value = covert_op_priority_detect_add
	multiply = 2
	round = yes
}
```

- [ ] **Step 6: Add the scripted GUIs**

In `common/scripted_guis/covert_warfare_sguis.txt`:

(a) Append at the end of the file:

```

# ---- PRIORITY: the row stepper ----------------------------------------------
# Two handlers, up and down, so the row's container can travel alone in a
# SINGLE AddScope — the shape the stand-down handlers use. Both delegate to
# covert_possible_priority_* / covert_effect_priority_*; the eligibility is
# fail-closed, so an unset or foreign scope greys the button instead of
# changing the wrong operation.
covert_priority_up_sgui = {
	scope = country
	saved_scopes = { iw_op }

	is_shown = {
		always = yes
	}

	is_valid = {
		covert_possible_priority_up = yes
	}

	effect = {
		covert_effect_priority_up = yes
	}

	ai_is_valid = {
		always = no
	}
}

covert_priority_down_sgui = {
	scope = country
	saved_scopes = { iw_op }

	is_shown = {
		always = yes
	}

	is_valid = {
		covert_possible_priority_down = yes
	}

	effect = {
		covert_effect_priority_down = yes
	}

	ai_is_valid = {
		always = no
	}
}

# ---- YES/NO: do all operations carry a priority yet? -------------------------
# iw_priority is new in slice 3. A save made before it has containers without
# it until the first monthly sync backfills them, and a .gui that reads a
# missing variable logs every frame. The row hides its priority stepper and
# line until this answers yes. Same shape as covert_ops_phase_ready_sgui.
covert_ops_priority_ready_sgui = {
	scope = country

	is_shown = {
		OR = {
			NOT = { has_variable_list = iw_ops }
			NOT = {
				any_in_list = {
					variable = iw_ops
					NOT = { has_variable = iw_priority }
				}
			}
		}
	}

	is_valid = {
		always = no
	}

	effect = { }

	ai_is_valid = {
		always = no
	}
}
```

(b) In the file header, change "Four kinds of entry live here." to "Five kinds of entry live here.", add `covert_ops_priority_ready_sgui` to the list in item 3, and add after item 4:

```
# 5. THE PRIORITY STEPPER (covert_priority_up_sgui, covert_priority_down_sgui).
#    One handler per direction; the row's container arrives as the saved scope
#    iw_op. See their section header.
```

- [ ] **Step 7: Add the row stepper and priority lines to the widget**

In `gui/journal_entry_widgets/covert_operations_widget.gui`:

(a) Inside `types covert_operations_widget_types`, directly after the `covert_op_stand_down_button` type, add:

```

	### The priority stepper for one operation row: label, minus, level, plus.
	### Up and down are separate scripted GUIs, each named by its button's own
	### datacontext, so the row's container travels alone in a single AddScope
	### (the stand-down shape). Hidden until every container carries
	### iw_priority, so a pre-slice-3 save never reads a missing variable.
	type covert_op_priority_stepper = flowcontainer {
		direction = horizontal
		spacing = 3
		margin_left = 12
		visible = "[GetScriptedGui('covert_ops_priority_ready_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"

		textbox = {
			text = "je_iw_priority_stepper_label"
			size = { 120 24 }
			align = left|nobaseline
			using = fontsize_small
			parentanchor = vcenter
			elide = right
		}

		button_icon_minus_action = {
			size = { 24 24 }
			parentanchor = vcenter
			datacontext = "[GetScriptedGui('covert_priority_down_sgui')]"
			enabled = "[ScriptedGui.IsValid( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'iw_op', ScriptContainer.MakeScope ).End )]"
			onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'iw_op', ScriptContainer.MakeScope ).End )]"
			tooltip = "je_iw_priority_step_down_tooltip"
		}

		textbox = {
			text = "[ScriptContainer.GetVariableValue('iw_priority')|0]"
			size = { 40 24 }
			align = center|nobaseline
			using = fontsize_small
			parentanchor = vcenter
		}

		button_icon_plus_action = {
			size = { 24 24 }
			parentanchor = vcenter
			datacontext = "[GetScriptedGui('covert_priority_up_sgui')]"
			enabled = "[ScriptedGui.IsValid( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'iw_op', ScriptContainer.MakeScope ).End )]"
			onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'iw_op', ScriptContainer.MakeScope ).End )]"
			tooltip = "je_iw_priority_step_up_tooltip"
		}
	}
```

(b) In `widget_je_covert_operation_row`, directly after the three phase lines and before the `# ---- Is it doing anything at all? ----` comment, add:

```

		# ---- Priority: a stepper, then what the current level means ----
		covert_op_priority_stepper = { }
		widget_je_covert_operation_detail = {
			visible = "[And( GetScriptedGui('covert_ops_priority_ready_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ), EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_priority'), '(CFixedPoint)1') )]"
			text = "je_iw_op_row_priority_1"
		}
		widget_je_covert_operation_detail = {
			visible = "[And( GetScriptedGui('covert_ops_priority_ready_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ), EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_priority'), '(CFixedPoint)2') )]"
			text = "je_iw_op_row_priority_2"
		}
		widget_je_covert_operation_detail = {
			visible = "[And( GetScriptedGui('covert_ops_priority_ready_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ), EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_priority'), '(CFixedPoint)3') )]"
			text = "je_iw_op_row_priority_3"
		}
```

(c) In the file header, after the paragraph about the per-row "Stand down" controls, add:

```
###
### The per-row priority stepper also uses no op code: up and down are two
### scripted GUIs (covert_priority_up_sgui / _down_sgui), and the row's
### container travels as the saved scope `iw_op`. Fail-closed: see
### covert_priority_op_is_ours.
```

and add `covert_ops_priority_ready_sgui` to the list of is_shown-only scripted GUIs in the EDITING RULES bullet.

Then check the BOM: `head -c3 gui/journal_entry_widgets/covert_operations_widget.gui | xxd | head -1` → `efbb bf`.

- [ ] **Step 8: Add the localization**

In `localization/english/te_miscellaneous_l_english.yml`, next to the existing `iw_stand_down_*` keys (one leading space, `:0`):

```
 iw_priority_op_known_tt:0 "The operation on this row can be identified"
 iw_priority_op_ours_tt:0 "This operation is one of ours and is still running"
 iw_priority_not_max_tt:0 "Priority is not already at its maximum ([GetPlayer.MakeScope.ScriptValue('covert_op_priority_max')|0])"
 iw_priority_not_min_tt:0 "Priority is above the lowest level (1)"
 iw_priority_to_1_tt:0 "Priority becomes #v 1#!: the operation works at its base strength, takes one share of the covert budget and adds nothing to its own detection risk."
 iw_priority_to_2_tt:0 "Priority becomes #v 2#!: its effect is multiplied by #G [GetPlayer.MakeScope.ScriptValue('covert_op_priority_2_effect_mult')|2]#!, its share of the covert budget by #R [GetPlayer.MakeScope.ScriptValue('covert_op_priority_2_cost_mult')|1]#!, and its monthly detection risk rises by #R [GetPlayer.MakeScope.ScriptValue('covert_op_priority_2_detect_display')|0]#! points before [concept_covert_efficiency]."
 iw_priority_to_3_tt:0 "Priority becomes #v 3#!: its effect is multiplied by #G [GetPlayer.MakeScope.ScriptValue('covert_op_priority_3_effect_mult')|2]#!, its share of the covert budget by #R [GetPlayer.MakeScope.ScriptValue('covert_op_priority_3_cost_mult')|1]#!, and its monthly detection risk rises by #R [GetPlayer.MakeScope.ScriptValue('covert_op_priority_3_detect_display')|0]#! points before [concept_covert_efficiency].\n#italic The last step buys less than the first and costs more: an agency cannot put everything at the top.#!"
```

In `localization/english/te_journal_entries_l_english.yml`, next to the existing `je_iw_op_row_*` keys:

```
 je_iw_op_row_priority_1:0 "Priority #v 1#! of [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_op_priority_max')|0] - base strength, one share of the budget"
 je_iw_op_row_priority_2:0 "Priority #v 2#! of [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_op_priority_max')|0] - effect #G x[JournalEntry.GetCountry.MakeScope.ScriptValue('covert_op_priority_2_effect_mult')|2]#!, budget share #R x[JournalEntry.GetCountry.MakeScope.ScriptValue('covert_op_priority_2_cost_mult')|1]#!, detection #R +[JournalEntry.GetCountry.MakeScope.ScriptValue('covert_op_priority_2_detect_display')|0]#! points"
 je_iw_op_row_priority_3:0 "Priority #v 3#! of [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_op_priority_max')|0] - effect #G x[JournalEntry.GetCountry.MakeScope.ScriptValue('covert_op_priority_3_effect_mult')|2]#!, budget share #R x[JournalEntry.GetCountry.MakeScope.ScriptValue('covert_op_priority_3_cost_mult')|1]#!, detection #R +[JournalEntry.GetCountry.MakeScope.ScriptValue('covert_op_priority_3_detect_display')|0]#! points"
 je_iw_priority_stepper_label:0 "Priority"
 je_iw_priority_step_down_tooltip:0 "#bold Lower this operation's priority#!\n[ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'iw_op', ScriptContainer.MakeScope ).End )]\n[ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'iw_op', ScriptContainer.MakeScope ).End )]"
 je_iw_priority_step_up_tooltip:0 "#bold Raise this operation's priority#!\n[ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'iw_op', ScriptContainer.MakeScope ).End )]\n[ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'iw_op', ScriptContainer.MakeScope ).End )]"
```

`[concept_covert_efficiency]` is already used by `je_iw_detection_factors`, so the concept exists. Use `#b`/`#bold` markup only, never `[b]`.

Then run: `python3 organize_loc.py && git diff --stat localization/`

- [ ] **Step 9: Format and run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_triggers/covert_warfare_triggers.txt common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt common/scripted_guis/covert_warfare_sguis.txt
for f in common/scripted_triggers/covert_warfare_triggers.txt common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt common/scripted_guis/covert_warfare_sguis.txt gui/journal_entry_widgets/covert_operations_widget.gui; do head -c3 "$f" | xxd | head -1; done
python3 scripts/analysis/check_localization_files.py
python3 -m unittest test_covert_priority test_covert_detection_roll test_covert_exposure_tiers -v
```

Expected: `efbb bf` ×5; the loc check passes; all tests PASS.

- [ ] **Step 10: Commit**

```bash
git add common/scripted_triggers/covert_warfare_triggers.txt common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt common/scripted_guis/covert_warfare_sguis.txt gui/journal_entry_widgets/covert_operations_widget.gui localization/english/te_miscellaneous_l_english.yml localization/english/te_journal_entries_l_english.yml test_covert_priority.py
git status --short localization/   # stage anything else organize_loc moved
git commit -m "feat(covert): a per-operation priority stepper in the operations widget"
```

---

### Task 6: The AI sets priorities

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (new `covert_ai_manage_priorities` in the PRIORITY section)
- Modify: `common/journal_entries/je_covert_warfare.txt` (call it in the monthly pulse)
- Test: `test_covert_priority.py` (add a class)

**Interfaces:**
- Consumes: `covert_possible_priority_up`, `covert_possible_priority_down` (Task 5), `covert_refresh_priority_cost` (Task 3).
- Produces: scripted effect `covert_ai_manage_priorities = yes` (country scope).

Rule, per operation: in default or bankrupt → 1; a great power at war with the target → 3; rivalled with the target → 2; otherwise 1. The AI moves toward that level one step at a time **through the same `covert_possible_priority_*` triggers the stepper uses**, so slice 5's Tradecraft gate on priority 3 will bind the AI too. It sets the variable directly rather than calling `covert_effect_priority_up` per operation (that would re-run the sync and every effect once per step); the pulse runs the sync and the effects right after.

- [ ] **Step 1: Write the failing test**

Append to `test_covert_priority.py`:

```python
class AITests(unittest.TestCase):
    def test_ai_steps_through_the_shared_gates(self):
        block = _top_level_block(_text(EFFECTS), "covert_ai_manage_priorities = {")
        self.assertIn("covert_possible_priority_up = yes", block)
        self.assertIn("covert_possible_priority_down = yes", block)
        self.assertIn("covert_refresh_priority_cost = yes", block)
        self.assertIn("rank_value:great_power", block)
        self.assertIn("type = rivalry", block)
        self.assertIn("in_default = yes", block)
        self.assertIn("declared_bankruptcy", block)

    def test_pulse_runs_it_for_the_ai_before_the_sync(self):
        body = _text(JE)
        pulse = body[body.index("on_monthly_pulse = {"):]
        call = pulse.index("covert_ai_manage_priorities = yes")
        sync = pulse.index("covert_ops_sync_all = yes")
        self.assertLess(call, sync, "the sync must see the new priorities")
        guard = pulse.rfind("is_player = no", 0, call)
        self.assertNotEqual(guard, -1)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_priority -v`
Expected: FAIL — `covert_ai_manage_priorities` does not exist.

- [ ] **Step 3: Add the AI effect**

Append to the PRIORITY section of `common/scripted_effects/covert_warfare_effects.txt` (after `covert_effect_priority_down`):

```

# The AI's priorities. Per operation, a wanted level: 1 in default or
# bankruptcy; 3 for a great power at war with the target; 2 against a rival;
# otherwise 1. It then steps toward that level one at a time, through the same
# covert_possible_priority_* gates the stepper uses, so any gate added there
# (slice 5's Tradecraft requirement) binds the AI as well. Two steps each way
# covers the whole 1-3 range. The variable is set directly: the monthly pulse
# runs the sync and the effects straight after this.
# Scope: country (is_player = no; the caller guards it)
covert_ai_manage_priorities = {
	save_scope_as = iw_ai_operator
	if = {
		limit = { has_variable_list = iw_ops }
		every_in_list = {
			variable = iw_ops
			save_scope_as = iw_op
			set_variable = { name = iw_ai_priority value = 1 }
			if = {
				limit = {
					scope:iw_ai_operator = {
						NOT = { in_default = yes }
						NOT = { has_modifier = declared_bankruptcy }
					}
				}
				var:iw_target ?= {
					save_scope_as = iw_ai_target
					if = {
						limit = {
							scope:iw_ai_operator = {
								country_rank >= rank_value:great_power
								has_war_with = scope:iw_ai_target
							}
						}
						scope:iw_op = { set_variable = { name = iw_ai_priority value = 3 } }
					}
					else_if = {
						limit = {
							scope:iw_ai_operator = {
								has_diplomatic_pact = { who = scope:iw_ai_target type = rivalry }
							}
						}
						scope:iw_op = { set_variable = { name = iw_ai_priority value = 2 } }
					}
				}
			}
			if = {
				limit = { NOT = { has_variable = iw_priority } }
				set_variable = { name = iw_priority value = 1 }
			}
			# Up, at most twice
			if = {
				limit = {
					var:iw_priority < var:iw_ai_priority
					scope:iw_ai_operator = { covert_possible_priority_up = yes }
				}
				change_variable = { name = iw_priority add = 1 }
			}
			if = {
				limit = {
					var:iw_priority < var:iw_ai_priority
					scope:iw_ai_operator = { covert_possible_priority_up = yes }
				}
				change_variable = { name = iw_priority add = 1 }
			}
			# Down, at most twice
			if = {
				limit = {
					var:iw_priority > var:iw_ai_priority
					scope:iw_ai_operator = { covert_possible_priority_down = yes }
				}
				change_variable = { name = iw_priority subtract = 1 }
			}
			if = {
				limit = {
					var:iw_priority > var:iw_ai_priority
					scope:iw_ai_operator = { covert_possible_priority_down = yes }
				}
				change_variable = { name = iw_priority subtract = 1 }
			}
			remove_variable = iw_ai_priority
		}
	}
	covert_refresh_priority_cost = yes
}
```

`scope:iw_ai_target` is saved and read inside the same `var:iw_target ?= { }` block, so an operation whose target no longer exists can never read the previous operation's target. `iw_ai_priority` is a container variable that nothing else reads and no modifier multiplier references, so removing it is safe.

- [ ] **Step 4: Call it from the pulse**

In `common/journal_entries/je_covert_warfare.txt`, directly before the comment `# ---- Reconcile operation containers with pacts ----`, add:

```
			# ---- AI priorities ----
			# Before the sync, so the sync's detection refresh and the upkeep
			# weights see the new levels. A human's priorities come from the
			# operations widget and are never touched here.
			if = {
				limit = { is_player = no }
				covert_ai_manage_priorities = yes
			}

```

- [ ] **Step 5: Format and run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt common/journal_entries/je_covert_warfare.txt
for f in common/scripted_effects/covert_warfare_effects.txt common/journal_entries/je_covert_warfare.txt; do head -c3 "$f" | xxd | head -1; done
python3 -m unittest test_covert_priority test_covert_detection_roll test_covert_exposure_tiers -v
```

Expected: `efbb bf` ×2; all PASS.

- [ ] **Step 6: Commit**

```bash
git add common/scripted_effects/covert_warfare_effects.txt common/journal_entries/je_covert_warfare.txt test_covert_priority.py
git commit -m "feat(covert): the AI raises priority against rivals and wartime enemies"
```

---

### Task 7: Console harness and documentation

**Files:**
- Modify: `common/scripted_effects/te_debug_covert_effects.txt` (new `te_debug_covert_max_priority`)
- Modify: `events/te_debug_covert_events.txt` (option `h` on `te_debug_covert.2`, header comment)
- Modify: `localization/english/te_events_l_english.yml` (`te_debug_covert.2.h`; a sentence in `.2.d`)
- Modify: `docs/systems/mod_systems.md` (§ Covert Warfare)
- Modify: `docs/systems/journal_entry_systems.md` (§ Covert Warfare → Command Centre) — **CRLF**
- Modify: `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` (mark slice 3's status)
- Test: `test_covert_priority.py` (add a class)

**Interfaces:**
- Consumes: `covert_effect_priority_up` (Task 5).

- [ ] **Step 1: Write the failing test**

Append to `test_covert_priority.py`:

```python
class HarnessTests(unittest.TestCase):
    def test_the_harness_changes_priority_through_the_shipping_effect(self):
        block = _top_level_block(_text(DEBUG_EFFECTS), "te_debug_covert_max_priority = {")
        self.assertIn("save_scope_as = iw_op", block)
        self.assertEqual(block.count("covert_effect_priority_up = yes"), 2)

    def test_the_operations_console_offers_it(self):
        block = _top_level_block(_text(DEBUG_EVENTS), "te_debug_covert.2 = {")
        self.assertIn("te_debug_covert_max_priority = yes", block)
        self.assertIn(" te_debug_covert.2.h:", _all_loc())
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_priority -v`
Expected: FAIL — `te_debug_covert_max_priority` does not exist.

- [ ] **Step 3: Add the harness effect and option**

Append to `common/scripted_effects/te_debug_covert_effects.txt`:

```

# Raise one running operation to the top priority through the shipping step
# effect, twice — the same code the row stepper's scripted GUI runs, minus
# the GUI. This exercises everything about priority except the click itself,
# so it still works if the stepper's saved scope turns out not to arrive.
# Scope: country
te_debug_covert_max_priority = {
	if = {
		limit = { has_variable_list = iw_ops }
		random_in_list = {
			variable = iw_ops
			save_scope_as = iw_op
		}
		covert_effect_priority_up = yes
		covert_effect_priority_up = yes
	}
}
```

In `events/te_debug_covert_events.txt`, add as the last option of `te_debug_covert.2` (after option `g`):

```

	# ---- Max one operation's priority through the real step effect, so the
	#      scaled effects, the upkeep and the detection line can be checked
	#      without depending on the stepper's saved scope.
	option = {
		name = te_debug_covert.2.h
		trigger = { covert_operations_active >= 1 }
		te_debug_covert_max_priority = yes
	}
```

and add `and priority` to the header line `event te_debug_covert.2     operations at each phase boundary, and detection` so it reads `… detection, and priority`.

In `localization/english/te_events_l_english.yml`, next to `te_debug_covert.2.g`:

```
 te_debug_covert.2.h:0 "Raise one operation to maximum priority (through the real step effect)"
```

and append to the end of the `te_debug_covert.2.d` string (before its closing quote): `\n\nRaising priority runs the same effect as the row's priority stepper, without the button, so it works even if the stepper stays greyed out.`

Run `python3 organize_loc.py`.

- [ ] **Step 4: Document the system in `mod_systems.md`**

In `docs/systems/mod_systems.md` § Covert Warfare System (starts at the `## Covert Warfare System` heading), make these edits — this file is LF, an ordinary edit is fine:

1. In **System Architecture**, after the **Phases** bullet, add a bullet **Priority (2026-09, covert slice 3)** stating: `iw_priority` 1–3 on each container (missing ⇒ 1; written by `covert_op_create`, backfilled by `covert_op_sync` before detection is refreshed); the numbers table from the top of this plan; that every apply site goes through `covert_op_add_scaled_modifier`, which branches phase × priority onto six **constant** script values `covert_op_mult_p{2,3}_pri{1,2,3}` because `add_modifier`'s multiplier is re-evaluated against ROOT; that self-side modifiers now come from the operation with the largest `covert_op_effect_mult` (phase × priority) via `ordered_in_list … position = 0`, not merely the best phase; that ideological subversion's movement pressure scales by priority only (it was already phase-flat); that the election-interference confidence hit is **not** priority-scaled; the stepper (two fail-closed scripted GUIs, the container as saved scope `iw_op`, unproven engine link, named per-type contingency); and the AI rule.
2. Replace the **Cost** bullet's formula with `(Σ priority weights + 1) × funding_level × covert_operations_cost_scale`, where the sum is `iw_priority_cost_sum` (refreshed by `covert_refresh_priority_cost` from `covert_op_create`, `covert_op_destroy`, the tail of `covert_ops_sync_all`, and every priority step) and falls back to the pact count for a save loaded before the first refresh.
3. In the **Detection** bullet's formula, add `+ (priority − 1) × covert_op_priority_detect_add` to the raw term (before efficiency), and say it is staged per operation as `iw_priority_staging`.
4. In **Adding an operation type**, add nothing — priority is type-agnostic — but in **AI Behavior** add a bullet for the priority rule, and in the **Variables** list of `journal_entry_systems.md` (next step) add the new variables.

- [ ] **Step 5: Document the widget in `journal_entry_systems.md` (CRLF)**

`docs/systems/journal_entry_systems.md` is **CRLF**. Edit it only with the `Edit` tool (never a Python rewrite), then confirm:

```bash
grep -c $'\r$' docs/systems/journal_entry_systems.md; wc -l < docs/systems/journal_entry_systems.md
```

The two numbers must be equal.

In § Covert Warfare:
1. **Variables**: add `iw_priority_cost_sum` and the transient `iw_priority_staging` to the country list; `iw_priority` to the operation-container list.
2. **Handlers / Shared helpers**: add `covert_priority_up_sgui`, `covert_priority_down_sgui`, `covert_ops_priority_ready_sgui`; `covert_priority_op_is_ours`, `covert_possible_priority_up`, `covert_possible_priority_down`; `covert_effect_priority_up`, `covert_effect_priority_down`, `covert_apply_priority_change`.
3. **Areas** item 7 (operation rows): add "a priority stepper and a line stating what the current level multiplies".
4. **Op table**: add a row `| — | per-row priority [-] / [+] | covert_possible_priority_down/_up / covert_effect_priority_down/_up; the container arrives as the saved scope iw_op |`.
5. After the **Stand down** paragraph, add a **Priority** paragraph: two handlers (one per direction) so the container travels in a single `AddScope`; fail-closed identification (`exists`, `iw_op` tag, membership of our own `iw_ops`); the step's shared tail (`covert_apply_priority_change`: cost, funding-state refresh, effects when funded); tooltips branch in script because tooltip loc cannot reach a container; the ready-gate; and the named per-type contingency.
6. **Traced scenarios**: add "priority 1→3 on one row (effect, upkeep and that row's detection move in the same click); stepper at either bound (greys, with the bound as its reason); save made before slice 3 (stepper and priority line hidden for at most one month, upkeep falls back to the pact count)".

- [ ] **Step 6: Mark the spec**

In `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md`, in the Slices table, append ` — built on branch covert-per-op-priority` to slice 3's "Slice" cell. Under `## Slice 3 — Per-operation priority`, add one line: `Implementation plan: docs/superpowers/plans/2026-09-22-covert-per-op-priority.md. Election-interference confidence is not priority-scaled (see the plan).`

- [ ] **Step 7: Format and run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt
for f in common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt; do head -c3 "$f" | xxd | head -1; done
python3 scripts/analysis/check_localization_files.py
python3 -m unittest test_covert_priority test_covert_detection_roll test_covert_exposure_tiers -v
```

Expected: `efbb bf` ×2; loc check passes; all PASS.

- [ ] **Step 8: Commit**

```bash
git add common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt localization/english/te_events_l_english.yml docs/systems/mod_systems.md docs/systems/journal_entry_systems.md docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md test_covert_priority.py
git status --short localization/   # stage anything else organize_loc moved
git commit -m "docs(covert): document per-operation priority; a console option to max one"
```

---

## Verification (controller, after Task 7)

- The server-independent checks, excluding the test that fires a real reload: `ls test_*.py | grep -v test_reload_post_load | sed 's/\.py$//' | VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent xargs .venv/bin/python -m unittest` — green.
- `ruff check .`; `python3 scripts/format_paradox_tabs.py --check` on every changed `.txt`; `python3 scripts/analysis/check_localization_files.py`; `python3 scripts/analysis/check_post_load_rosters.py`.
- The CI `--strict` audits that touch this slice: `modifier_multiplier_var_audit --strict` (the new multipliers must not be flagged), `loc_render_audit --strict`, `iterator_limit_audit --strict`, `any_limit_audit --strict`.
- Start the mod state server if it is down (standing approval), then `curl -X POST "http://localhost:8950/reload?mod_only=true&audits_only=true"` — `warnings` empty, `parse_failures` empty. Check `docs/engine/loc_coverage_report.md` for the 16 new keys, `docs/engine/loc_render_report.md`, and `docs/engine/effect_trigger_validity_report.md` for `ordered_in_list`, `is_target_in_variable_list` and the parameterized `covert_op_priority_at_least`.
- **In game** (the PR is a draft until these are done): `event te_debug_covert.2` → option a (seed) → option h (max one operation's priority). Confirm: the row shows priority 3 and the ×1.6 / ×2.4 / +4 line; the target's (or, for espionage, our own) modifier tooltip shows the stronger values; the command centre's weekly cost rises; that row's detection figure rises. Then click the row's `[-]` and `[+]`: **the saved-scope question** — if both stay greyed with "The operation on this row can be identified" unticked, the container does not arrive and the named per-type contingency is needed. Read `debug.log` via the `log-triage` skill for `iw_op`, `iw_priority`, `covert_op_mult` and `Undefined event target` lines.
- PR body: the numbers table; the upkeep example (4 → 5.4 units); detection 10 / 12 / 14 % at base and the late-game +0.8; the election-interference non-scaling; the saved-scope open question and its contingency; `Closes` nothing (no issue). End with the attribution lines.
