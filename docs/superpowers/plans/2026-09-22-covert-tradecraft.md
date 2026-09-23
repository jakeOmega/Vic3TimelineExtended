# Covert Agency Experience — "Tradecraft" (Slice 5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every covert agency a persistent experience score, `iw_tradecraft` (0–100). It grows while operations run past the preparatory phase, falls when one is burned, and drifts down when the agency is idle. Its tier grants intelligence capacity and faster network growth. It also unlocks priority 3, the slice-6 severe operations and one extra operation per type.

**Architecture:** The score is one country variable on the operator. Its only writers are `covert_tradecraft_gain` and `covert_tradecraft_loss`, and gains shrink above 50 while losses do not (the `un_standing` shape). The journal entry's monthly pulse calls a single effect, `covert_tradecraft_monthly`, after durations age. That effect seeds the variable, gains or decays it, and refreshes one static modifier on the journal entry, applied with `multiplier = tier`. The burn loss runs in `covert_warfare.1`'s `after`, keyed on the burned type code's tier. The tier is exposed as four scripted triggers plus three named unlock triggers. The priority stepper, the per-type cap and (in slice 6) the new operations read those triggers. The command centre gains one header and one line.

**Tech Stack:** Paradox Clausewitz script (Victoria 3), `.gui`, YAML loc, Python `unittest` structural tests.

**Spec:** `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` § Slice 5 (and § Slices and build order, § Verification). Read the slice-4 plan's "Engine rules" section too (`docs/superpowers/plans/2026-09-22-covert-per-target-networks.md`); its rules are restated below where this slice depends on them.

## Global Constraints

- Branch `covert-tradecraft` off `main` (already created); one PR; `gh pr create --base main`.
- Brace-based `.txt`/`.gui` files use tab indentation; run `python3 scripts/format_paradox_tabs.py <files>` on every touched `.txt`/`.gui`.
- Every touched `.txt`/`.gui` keeps its UTF-8 BOM if it had one (all covert files do). Check with `head -c3 <f> | xxd` (expect `efbbbf`).
- Loc: `je_iw_*` keys go in `localization/english/te_journal_entries_l_english.yml`, `te_debug_covert.*` in `te_events_l_english.yml`, and every other new key (`covert_tradecraft_*_tt`, `iw_tradecraft_*`, `iw_priority_3_needs_tradecraft_tt`, `iw_tradecraft_bonus`) in `te_miscellaneous_l_english.yml`. Then run `python3 organize_loc.py`, which may re-home some keys (e.g. static-modifier names land in `te_concepts_l_english.yml`); that is fine. Confirm with `git diff --stat localization/` that **nothing new lands in `te_unused_l_english.yml`**.
- Vic3 loc formatting: `#b X#!`, `#v`, `#R`, `#G`, `#bold`, `#italic` — never `[b]…[/b]`.
- `docs/systems/journal_entry_systems.md` is CRLF: edit with `Edit` only; confirm `grep -c $'\r$' docs/systems/journal_entry_systems.md` equals `wc -l < docs/systems/journal_entry_systems.md` afterwards.
- Never `git commit -a`; stage by path (the tree carries unrelated `common/buy_packages/00_buy_packages.txt` and `docs/engine/*` churn).
- Commit trailer (both lines, every commit):
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LzWgjf8JaejpTAvUoAm2TG`
- Constants (Section 1 of `covert_warfare_script_values.txt`), verbatim from the spec: gain `1.0` per operation at establishing or better, counting at most `4` operations, scaled by `(100 − x) / 50` clamped `[0.1, 1]`; burn losses mild `3`, moderate `6`, severe `9`, war `3` (unscaled); decay `0.25`/month while no operation runs; tier floors `20 / 40 / 60 / 80`; `country_intelligence_capacity_mult +0.05` per tier; network growth `×(1 + 0.15 per tier)`.
- Unlocks, verbatim: Established (40) → priority 3; Seasoned (60) → the two new severe operations (slice 6 consumes the trigger; this slice only ships it); Veteran (80) → +1 per-type cap. **Existing operations are never gated.** An operation already at priority 3, or a third operation of a type already running, keeps running when the score falls.

### Engine rules this plan relies on

1. **`change_variable` does not reliably resolve a script-value operand** (slice-4 rule 5). Every score write uses `set_variable = { name = iw_tradecraft value = { value = var:iw_tradecraft add = … } }` followed by `clamp_variable`. Do **not** copy `un_standing_gain` verbatim; it uses the `change_variable` form. `change_variable = { add = 1 }` with a literal is fine.
2. **Cross-scope reads into a container go through `scope:<country>.var:x`**, the proven shape of `covert_op_refresh_detection`'s `set_variable = { name = iw_detect value = scope:iw_operator.var:iw_detect_staging }`. Never read `parent` from a container-scope script value, and never `scope:<container>.<script_value>`.
3. **A multiplier on a journal-entry modifier is evaluated with the journal entry as scope**, so the script value must hop `owner = { }`. `intelligence_capacity_modifier_mult` and `covert_ops_funding_ci_mult` have the same shape and say so in comments.
4. **`add_modifier`'s multiplier is re-evaluated on later ticks**, so it must never read a variable that gets removed. `iw_tradecraft` is permanent once seeded, so reading it is safe.
5. **`covert_warfare.1`'s `after` may be walked by the option tooltips' render pass**, where a saved scope may be unset. The loss reads only the country variable `iw_burned_type_code`, which `immediate` wrote on ROOT.
6. **The scripted triggers `covert_code_tier_*` take a variable NAME** (`VAR = iw_burned_type_code`), not a literal, so the tier cannot be decided inside `covert_op_burn` from its `$CODE$` parameter.

### Decisions this plan makes where the spec is silent or inconsistent

- **Tier names.** The spec lists five names (Fledgling / Established / Seasoned / Veteran / Storied) against four floors, but its unlock lines bind *Established = 40, Seasoned = 60, Veteran = 80*. Those unlock lines agree with its balance prose ("Seasoned (60) is reachable with a single long-running op"), so they win. The five bands are **0–19 Untested, 20–39 Fledgling, 40–59 Established, 60–79 Seasoned, 80–100 Veteran**. "Storied" is dropped. The names are loc only (`iw_tradecraft_tier_name_0..4`), so renaming later is a one-file change.
- **Tier number = number of floors reached, 0–4.** `covert_tradecraft_tier` is 0 below 20, so an untested agency carries no modifier. At most (Veteran) the agency gets +20% intelligence capacity and ×1.6 network growth.
- **Separate DR constants** `covert_tradecraft_dr_divisor = 50` / `covert_tradecraft_dr_floor = 0.1`, rather than reusing `covert_net_dr_*`, so either curve can be retuned alone.
- **"No operation is running" = `covert_operations_active < 1`**, the journal entry's own empty-state idiom. An agency whose operations are all still preparatory neither gains nor decays, and its last-reason line is left alone.
- **Pulse position.** `covert_tradecraft_monthly` runs right after `covert_ops_age_all_durations` (so `covert_op_is_established` sees this month's duration), and before the phase effects and the detection roll. It runs regardless of funding, because decay has to work at funding 0. Networks tick earlier in the same pulse (`covert_nets_sync`), so they grow at **last month's** tier, a one-month lag that matches slice 4's detection lag.
- **The burn loss lives in `after`**, immediately after the nine-way `covert_op_burn` branch and **before** `remove_variable = iw_burned_type_code`. It sits inside the same `exists = scope:detected_by_country` guard as the burn, so "on each burn" is exact: if the target vanished and nothing was burned, nothing is charged. The options show the amount through the existing `covert_op_burned_tt`, which prints `covert_tradecraft_burn_loss_value`, the same script value the effect branches mirror.
- **Stand-down never costs Tradecraft.** It is not a burn.
- **Old saves / countries whose entry never activated.** `covert_tradecraft_gain` and `covert_tradecraft_loss` are no-ops while `iw_tradecraft` is missing. `covert_tradecraft_init` seeds 0 in the entry's `immediate` and again at the top of `covert_tradecraft_monthly`, because `immediate` does not re-run for an entry already active in a loaded save.
- **Reason codes** (`iw_tradecraft_last_reason`), mirroring the UN ranges: `1` operations maturing (gain); `20` mild burn, `21` moderate burn, `22` severe burn, `23` wartime burn, `24` idle decay. An unrecognised type code is charged as moderate, like the blowback values.
- **Network growth is multiplied into the nominal gain** (`covert_net_tick_gain`), before `covert_net_gain_scale`, so the diminishing-returns floor keeps its meaning. The operator stages `iw_tc_net_mult_staging` once at the top of `covert_nets_sync`. Each network copies it into `iw_net_tc_mult` just before its gain, and the staging variable is removed at the end.
- **Debug harness** gets its own event, `te_debug_covert.3`, rather than two more options on `te_debug_covert.2` (which already has eight).

## Review Focus

1. **Clicking the funding or priority stepper must not move Tradecraft.** `covert_refresh_funding_state` runs `covert_ops_sync_all` on every click, so the monthly effect must be called from the journal entry pulse and nowhere else. Pinned by `test_monthly_called_only_from_pulse` (Task 2).
2. **A burn in a save made before this slice** (no `iw_tradecraft`) must not error or create the variable half-way. Loss is a no-op without the variable. Pinned by `test_writers_guard_missing_variable` (Task 2).
3. **The loss must be decided before the type code is cleaned up.** In `after`, the call must come before `remove_variable = iw_burned_type_code`, or every burn reads as moderate. Pinned by `test_burn_loss_before_cleanup` (Task 3).
4. **An operation already at priority 2 or 3 must not be blocked from stepping *down*, or kept from running, when Tradecraft falls.** The gate sits only on `covert_possible_priority_up`, and it lets through any operation below 2. Pinned by `test_priority_gate_only_on_step_to_three` (Task 4).
5. **Every network must get its own growth multiplier before its gain is computed.** A network read before the copy would grow at ×1, or at a stale value from an earlier month. Pinned by `test_net_multiplier_copied_before_gain` (Task 4).

---

## File map

| File | Change |
|---|---|
| `common/script_values/covert_warfare_script_values.txt` | Section 1 Tradecraft constants; new § "TRADECRAFT (slice 5)" script values; `covert_ops_max_per_type` +1 at Veteran; `covert_net_tick_gain` × `iw_net_tc_mult` |
| `common/scripted_triggers/covert_warfare_triggers.txt` | § TRADECRAFT: `covert_tradecraft_tier_1..4`, three unlock triggers; priority-3 gate in `covert_possible_priority_up` |
| `common/scripted_effects/covert_warfare_effects.txt` | § TRADECRAFT: init / gain / loss / clamp / burn loss / bonus refresh / monthly; staging in `covert_nets_sync` |
| `common/journal_entries/je_covert_warfare.txt` | `immediate` seeds; pulse calls `covert_tradecraft_monthly` |
| `events/covert_warfare_events.txt` | `after` calls `covert_tradecraft_burn_loss` |
| `common/static_modifiers/extra_modifiers.txt` | `iw_tradecraft_bonus` |
| `common/customizable_localization/covert_warfare_custom_loc.txt` | `covert_tradecraft_tier_name`, `covert_tradecraft_last_reason` |
| `gui/journal_entry_widgets/covert_operations_widget.gui` | TRADECRAFT header + line in the command centre; header comment |
| `localization/english/te_journal_entries_l_english.yml` | `je_iw_tradecraft_*`; `je_iw_slots_detail_tooltip` mentions Veteran |
| `localization/english/te_miscellaneous_l_english.yml` | tier names, reason lines, `covert_op_burned_tt`, priority gate, modifier name/desc |
| `localization/english/te_events_l_english.yml` | `te_debug_covert.3.*` |
| `common/scripted_effects/te_debug_covert_effects.txt`, `events/te_debug_covert_events.txt` | Harness event `te_debug_covert.3` |
| `test_covert_tradecraft.py` | New structural test file |
| `docs/systems/mod_systems.md` § Covert Warfare System, `docs/systems/journal_entry_systems.md` § Covert Warfare, spec § Slice 5 | Docs |

Test command used throughout: `python3 -m unittest test_covert_tradecraft -v`. The existing covert suites must stay green: `python3 -m unittest test_covert_detection_roll test_covert_exposure_tiers test_covert_networks test_covert_priority test_covert_stand_down`.

---

### Task 1: Constants, tier triggers and Tradecraft script values

**Files:**
- Create: `test_covert_tradecraft.py`
- Modify: `common/script_values/covert_warfare_script_values.txt` (Section 1 tail after `covert_net_head_start_max = 5`; new section appended at end of file)
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (new section appended at end of file)

**Interfaces:**
- Produces (script values, country scope unless noted): constants `covert_tradecraft_max`, `covert_tradecraft_gain_per_op`, `covert_tradecraft_ops_counted`, `covert_tradecraft_dr_divisor`, `covert_tradecraft_dr_floor`, `covert_tradecraft_loss_mild/_moderate/_severe/_war`, `covert_tradecraft_decay`, `covert_tradecraft_tier_1_floor.._4_floor`, `covert_tradecraft_net_gain_per_tier`; values `covert_tradecraft_gain_scale`, `covert_tradecraft_monthly_gain_nominal` (reads `var:iw_tradecraft_ops`), `covert_tradecraft_tier` (0–4), `covert_tradecraft_bonus_mult` (owner hop, for the JE modifier), `covert_tradecraft_net_gain_mult`, `covert_tradecraft_burn_loss_value` (reads `iw_burned_type_code`), `covert_tradecraft_net_gain_pct_display`, `covert_tradecraft_display`.
- Produces (triggers, country scope): `covert_tradecraft_tier_1` … `covert_tradecraft_tier_4`; `covert_tradecraft_unlocks_priority_3`, `covert_tradecraft_unlocks_severe_ops`, `covert_tradecraft_unlocks_extra_per_type`.

- [ ] **Step 1: Write the failing tests**

Create `test_covert_tradecraft.py`:

```python
"""Structural tests for covert warfare slice 5 (agency experience, "Tradecraft").

Tradecraft is one country variable, iw_tradecraft (0-100), written only by
covert_tradecraft_gain / covert_tradecraft_loss. These tests pin the spec's
constants, the tier table, that the score moves once a month and only from the
journal entry pulse, that a burn is charged by tier before the event cleans up
the type code, that the unlocks gate only what the spec says they gate, and
that the widget, loc and harness exist.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
EVENTS = ROOT / "events/covert_warfare_events.txt"
JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
STATIC = ROOT / "common/static_modifiers/extra_modifiers.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/covert_warfare_custom_loc.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"
LOC_DIR = ROOT / "localization/english"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _all_loc():
    return "".join(p.read_text(encoding="utf-8-sig") for p in LOC_DIR.rglob("*.yml"))


class ConstantTests(unittest.TestCase):
    def test_constants_exist(self):
        body = _text(VALUES)
        for name, value in (
            ("covert_tradecraft_max", "100"),
            ("covert_tradecraft_gain_per_op", "1"),
            ("covert_tradecraft_ops_counted", "4"),
            ("covert_tradecraft_dr_divisor", "50"),
            ("covert_tradecraft_dr_floor", "0.1"),
            ("covert_tradecraft_loss_mild", "3"),
            ("covert_tradecraft_loss_moderate", "6"),
            ("covert_tradecraft_loss_severe", "9"),
            ("covert_tradecraft_loss_war", "3"),
            ("covert_tradecraft_decay", "0.25"),
            ("covert_tradecraft_tier_1_floor", "20"),
            ("covert_tradecraft_tier_2_floor", "40"),
            ("covert_tradecraft_tier_3_floor", "60"),
            ("covert_tradecraft_tier_4_floor", "80"),
            ("covert_tradecraft_net_gain_per_tier", "0.15"),
        ):
            self.assertRegex(body, r"(?m)^%s = %s$" % (name, re.escape(value)))

    def test_losses_rise_with_tier(self):
        body = _text(VALUES)
        get = lambda n: float(re.search(r"(?m)^%s = ([\d.]+)$" % n, body).group(1))
        self.assertLess(get("covert_tradecraft_loss_mild"), get("covert_tradecraft_loss_moderate"))
        self.assertLess(get("covert_tradecraft_loss_moderate"), get("covert_tradecraft_loss_severe"))


class ScriptValueTests(unittest.TestCase):
    def test_gain_scale_mirrors_un_idiom(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_gain_scale = {")
        self.assertIn("covert_tradecraft_dr_divisor", block)
        self.assertIn("min = covert_tradecraft_dr_floor", block)
        self.assertIn("max = 1", block)
        self.assertIn("has_variable = iw_tradecraft", block)

    def test_monthly_gain_reads_counted_ops(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_monthly_gain_nominal = {")
        self.assertIn("var:iw_tradecraft_ops", block)
        self.assertIn("covert_tradecraft_gain_per_op", block)

    def test_tier_counts_all_four_floors(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_tier = {")
        for n in range(1, 5):
            self.assertIn("covert_tradecraft_tier_%d = yes" % n, block)

    def test_bonus_mult_hops_owner(self):
        # Evaluated as a journal-entry modifier multiplier: JE scope.
        block = _top_level_block(_text(VALUES), "covert_tradecraft_bonus_mult = {")
        self.assertIn("owner = {", block)
        self.assertIn("covert_tradecraft_tier", block)

    def test_net_gain_mult_is_one_plus_tier_share(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_net_gain_mult = {")
        self.assertIn("covert_tradecraft_tier", block)
        self.assertIn("covert_tradecraft_net_gain_per_tier", block)
        self.assertIn("add = 1", block)

    def test_burn_loss_value_branches_every_tier(self):
        block = _top_level_block(_text(VALUES), "covert_tradecraft_burn_loss_value = {")
        for tier in ("mild", "severe", "war"):
            self.assertIn("covert_code_tier_%s = { VAR = iw_burned_type_code }" % tier, block)
            self.assertIn("covert_tradecraft_loss_%s" % tier, block)
        # Unrecognised codes read as moderate, like the blowback values.
        self.assertRegex(block, r"else = \{\s*add = covert_tradecraft_loss_moderate")


class TriggerTests(unittest.TestCase):
    def test_tier_triggers_use_floors_and_guard(self):
        body = _text(TRIGGERS)
        for n in range(1, 5):
            block = _top_level_block(body, "covert_tradecraft_tier_%d = {" % n)
            self.assertIn("has_variable = iw_tradecraft", block)
            self.assertIn("var:iw_tradecraft >= covert_tradecraft_tier_%d_floor" % n, block)

    def test_unlock_triggers_map_to_spec_tiers(self):
        body = _text(TRIGGERS)
        for name, tier in (
            ("covert_tradecraft_unlocks_priority_3", 2),
            ("covert_tradecraft_unlocks_severe_ops", 3),
            ("covert_tradecraft_unlocks_extra_per_type", 4),
        ):
            block = _top_level_block(body, name + " = {")
            self.assertIn("covert_tradecraft_tier_%d = yes" % tier, block)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest test_covert_tradecraft -v`
Expected: FAIL / ERROR on every test (`AssertionError` for the missing constants, `ValueError: substring not found` for the missing blocks).

- [ ] **Step 3: Add the Section 1 constants**

In `common/script_values/covert_warfare_script_values.txt`, insert directly after the line `covert_net_head_start_max = 5` (and before the blank line and the `# SECTION 2` banner):

```
# ---- Agency experience: Tradecraft (slice 5) ----
# A country's covert service's accumulated experience, 0 to
# covert_tradecraft_max, in the country variable iw_tradecraft. It grows while
# operations run past the preparatory phase, falls when one is burned and
# drifts down while the agency sits idle. Gains shrink above half (the
# UN-standing idiom); losses do not. Writers: covert_tradecraft_gain /
# covert_tradecraft_loss (covert_warfare_effects.txt, § TRADECRAFT).
covert_tradecraft_max = 100
# Monthly gain per operation at establishing phase or better, counting at most
# covert_tradecraft_ops_counted of them.
covert_tradecraft_gain_per_op = 1
covert_tradecraft_ops_counted = 4
covert_tradecraft_dr_divisor = 50
covert_tradecraft_dr_floor = 0.1
# What a burn costs, by the exposed operation's tier. Unscaled. Net of these,
# at 10% monthly detection a moderate operation still earns about +0.4 a
# month, a severe one +0.1 and a mild one +0.7 (spec § Slice 5).
covert_tradecraft_loss_mild = 3
covert_tradecraft_loss_moderate = 6
covert_tradecraft_loss_severe = 9
covert_tradecraft_loss_war = 3
# Monthly drift while no operation runs at all.
covert_tradecraft_decay = 0.25
# Tier floors: Untested < 20 <= Fledgling < 40 <= Established < 60 <= Seasoned
# < 80 <= Veteran. Unlocks: covert_tradecraft_unlocks_* (scripted triggers).
covert_tradecraft_tier_1_floor = 20
covert_tradecraft_tier_2_floor = 40
covert_tradecraft_tier_3_floor = 60
covert_tradecraft_tier_4_floor = 80
# Networks grow this much faster per tier (x1.6 at Veteran). The intelligence
# capacity bonus per tier is the iw_tradecraft_bonus static modifier itself.
covert_tradecraft_net_gain_per_tier = 0.15
```

- [ ] **Step 4: Append the Tradecraft script-value section**

Append at the end of `common/script_values/covert_warfare_script_values.txt`:

```

# ============================================================================
# SECTION: TRADECRAFT (slice 5)
# ============================================================================
# Constants: Section 1, "Agency experience". Writers and the monthly pass:
# covert_warfare_effects.txt, § TRADECRAFT. Tiers and unlocks:
# covert_warfare_triggers.txt, § TRADECRAFT.
#
# Equilibrium: gains diminish and losses do not, so the score settles where
# N x gain x (100 - x) / 50 = p x L. Two moderate operations at 10% detection
# settle near 85, one near 70.
# Projection, moderate operations at 10% detection (net +0.4/op-month below 50):
#   ops running   months to 25   to 50   to 60
#   1             63             125     ~165
#   2             31             63      ~85
#   4             16             31      ~45
# Scope: operator country throughout, unless noted.

# Diminishing returns on gains: 1 up to half, falling linearly to
# covert_tradecraft_dr_floor at the top. Same shape as un_standing_gain_scale.
covert_tradecraft_gain_scale = {
	value = covert_tradecraft_max
	if = {
		limit = { has_variable = iw_tradecraft }
		subtract = var:iw_tradecraft
	}
	divide = covert_tradecraft_dr_divisor
	min = covert_tradecraft_dr_floor
	max = 1
}

# This month's nominal gain, before diminishing returns. var:iw_tradecraft_ops
# (operations at establishing or better, already capped at
# covert_tradecraft_ops_counted) is written by covert_tradecraft_monthly just
# before this is read.
covert_tradecraft_monthly_gain_nominal = {
	value = 0
	if = {
		limit = { has_variable = iw_tradecraft_ops }
		add = var:iw_tradecraft_ops
		multiply = covert_tradecraft_gain_per_op
	}
}

# How many tier floors the score has reached: 0 (Untested) to 4 (Veteran).
covert_tradecraft_tier = {
	value = 0
	if = {
		limit = { covert_tradecraft_tier_1 = yes }
		add = 1
	}
	if = {
		limit = { covert_tradecraft_tier_2 = yes }
		add = 1
	}
	if = {
		limit = { covert_tradecraft_tier_3 = yes }
		add = 1
	}
	if = {
		limit = { covert_tradecraft_tier_4 = yes }
		add = 1
	}
}

# Multiplier for the iw_tradecraft_bonus static modifier on the journal entry.
# owner = { } makes it safe from JE scope, where the engine re-evaluates it
# (a no-op from country scope) — same shape as intelligence_capacity_modifier_mult.
covert_tradecraft_bonus_mult = {
	value = 0
	owner = {
		add = covert_tradecraft_tier
	}
}

# Network growth multiplier: 1 + covert_tradecraft_net_gain_per_tier per tier.
# Staged by covert_nets_sync onto every network before its gain.
covert_tradecraft_net_gain_mult = {
	value = covert_tradecraft_tier
	multiply = covert_tradecraft_net_gain_per_tier
	add = 1
}

# What the burn now being resolved costs. Reads iw_burned_type_code, which
# covert_warfare.1's immediate copies onto the operator; an unrecognised code
# reads as moderate, like covert_exposure_infamy_base. The loss effect
# (covert_tradecraft_burn_loss) branches the same way; the options' tooltip
# (covert_op_burned_tt) prints this value.
# Scope: country (the operator, while covert_warfare.1 is open)
covert_tradecraft_burn_loss_value = {
	value = 0
	if = {
		limit = { covert_code_tier_mild = { VAR = iw_burned_type_code } }
		add = covert_tradecraft_loss_mild
	}
	else_if = {
		limit = { covert_code_tier_severe = { VAR = iw_burned_type_code } }
		add = covert_tradecraft_loss_severe
	}
	else_if = {
		limit = { covert_code_tier_war = { VAR = iw_burned_type_code } }
		add = covert_tradecraft_loss_war
	}
	else = {
		add = covert_tradecraft_loss_moderate
	}
}

# Display: covert_tradecraft_net_gain_per_tier as a whole percentage (15).
covert_tradecraft_net_gain_pct_display = {
	value = covert_tradecraft_net_gain_per_tier
	multiply = 100
	round = yes
}

# Display: the score, rounded, 0 when unseeded.
covert_tradecraft_display = {
	value = 0
	if = {
		limit = { has_variable = iw_tradecraft }
		add = var:iw_tradecraft
	}
	round = yes
}
```

- [ ] **Step 5: Append the tier and unlock triggers**

Append at the end of `common/scripted_triggers/covert_warfare_triggers.txt`:

```

# ============================================================================
# TRADECRAFT (slice 5)
# ============================================================================
# The agency-experience tiers. These four are the only place the floors are
# compared; covert_tradecraft_tier (script value) counts them. A country with
# no iw_tradecraft (an entry never activated, or a save from before slice 5
# until its first pulse) is in no tier.
# Scope: country

covert_tradecraft_tier_1 = {
	has_variable = iw_tradecraft
	var:iw_tradecraft >= covert_tradecraft_tier_1_floor
}

covert_tradecraft_tier_2 = {
	has_variable = iw_tradecraft
	var:iw_tradecraft >= covert_tradecraft_tier_2_floor
}

covert_tradecraft_tier_3 = {
	has_variable = iw_tradecraft
	var:iw_tradecraft >= covert_tradecraft_tier_3_floor
}

covert_tradecraft_tier_4 = {
	has_variable = iw_tradecraft
	var:iw_tradecraft >= covert_tradecraft_tier_4_floor
}

# What each tier unlocks. One trigger per unlock, so every gate is one
# custom_tooltip line and the tier it needs is stated once, here. None of
# them ever ends something already running: they gate starting it.

# Established: an operation may be raised to priority 3
# (covert_possible_priority_up).
covert_tradecraft_unlocks_priority_3 = {
	covert_tradecraft_tier_2 = yes
}

# Seasoned: the severe operations added in slice 6 (regime change, nuclear
# programme sabotage) may be launched.
covert_tradecraft_unlocks_severe_ops = {
	covert_tradecraft_tier_3 = yes
}

# Veteran: one more operation of each type (covert_ops_max_per_type).
covert_tradecraft_unlocks_extra_per_type = {
	covert_tradecraft_tier_4 = yes
}
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python3 -m unittest test_covert_tradecraft -v`
Expected: all 10 tests PASS.

- [ ] **Step 7: Format, BOM check, commit**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/covert_warfare_script_values.txt common/scripted_triggers/covert_warfare_triggers.txt
head -c3 common/script_values/covert_warfare_script_values.txt | xxd; head -c3 common/scripted_triggers/covert_warfare_triggers.txt | xxd
git add test_covert_tradecraft.py common/script_values/covert_warfare_script_values.txt common/scripted_triggers/covert_warfare_triggers.txt
git commit -m "feat(covert): Tradecraft constants, tiers and script values (slice 5)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LzWgjf8JaejpTAvUoAm2TG"
```

(The script-values file has no BOM today — `git show origin/main:common/script_values/covert_warfare_script_values.txt | head -c3 | xxd` tells you; keep whatever it had.)

---

### Task 2: The writers, the monthly pass and the bonus modifier

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (header doc block lines 1–51; new section inserted before `# MONTHLY RECONCILIATION`)
- Modify: `common/journal_entries/je_covert_warfare.txt` (`immediate`; `on_monthly_pulse` after `covert_ops_age_all_durations = yes`)
- Modify: `common/static_modifiers/extra_modifiers.txt` (after `iw_domestic_defense`)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (modifier name/desc)
- Test: `test_covert_tradecraft.py`

**Interfaces:**
- Consumes: Task 1 values and triggers.
- Produces (effects, operator-country scope): `covert_tradecraft_init`, `covert_tradecraft_gain = { AMOUNT REASON }`, `covert_tradecraft_loss = { AMOUNT REASON }`, `covert_tradecraft_clamp`, `covert_tradecraft_refresh_bonus`, `covert_tradecraft_monthly`. Variables: `iw_tradecraft`, `iw_tradecraft_last_reason`, `iw_tradecraft_ops`. Static modifier `iw_tradecraft_bonus`.

- [ ] **Step 1: Write the failing tests**

Append to `test_covert_tradecraft.py`, above the `if __name__` line:

```python
class WriterTests(unittest.TestCase):
    def test_writers_guard_missing_variable(self):
        body = _text(EFFECTS)
        for name in ("covert_tradecraft_gain = {", "covert_tradecraft_loss = {"):
            block = _top_level_block(body, name)
            self.assertIn("has_variable = iw_tradecraft", block)
            self.assertIn("covert_tradecraft_clamp = yes", block)
            self.assertIn("iw_tradecraft_last_reason", block)
            # Rule 1: never change_variable with a script-value operand.
            self.assertNotIn("change_variable", block)

    def test_gain_scaled_loss_unscaled(self):
        body = _text(EFFECTS)
        self.assertIn("covert_tradecraft_gain_scale", _top_level_block(body, "covert_tradecraft_gain = {"))
        self.assertNotIn("covert_tradecraft_gain_scale", _top_level_block(body, "covert_tradecraft_loss = {"))

    def test_clamp_bounds(self):
        block = _top_level_block(_text(EFFECTS), "covert_tradecraft_clamp = {")
        self.assertIn("clamp_variable = { name = iw_tradecraft min = 0 max = covert_tradecraft_max }", block)


class MonthlyTests(unittest.TestCase):
    def test_monthly_called_only_from_pulse(self):
        # covert_ops_sync_all / covert_refresh_funding_state run on every click;
        # the score must move once a month.
        effects = _text(EFFECTS)
        calls = re.findall(r"covert_tradecraft_monthly = yes", effects)
        self.assertEqual(calls, [], "covert_tradecraft_monthly must not be called from another effect")
        je = _text(JE)
        self.assertEqual(je.count("covert_tradecraft_monthly = yes"), 1)
        pulse = je[je.index("on_monthly_pulse"):]
        self.assertLess(pulse.index("covert_ops_age_all_durations = yes"), pulse.index("covert_tradecraft_monthly = yes"))
        self.assertLess(pulse.index("covert_tradecraft_monthly = yes"), pulse.index("covert_ops_roll_detection_all = yes"))

    def test_monthly_counts_established_ops_capped(self):
        block = _top_level_block(_text(EFFECTS), "covert_tradecraft_monthly = {")
        self.assertIn("covert_tradecraft_init = yes", block)
        self.assertIn("covert_op_is_established = yes", block)
        self.assertIn("max = covert_tradecraft_ops_counted", block)
        self.assertIn("covert_tradecraft_gain = { AMOUNT = covert_tradecraft_monthly_gain_nominal REASON = 1 }", block)
        self.assertIn("covert_operations_active < 1", block)
        self.assertIn("covert_tradecraft_loss = { AMOUNT = covert_tradecraft_decay REASON = 24 }", block)
        self.assertIn("covert_tradecraft_refresh_bonus = yes", block)

    def test_immediate_seeds(self):
        je = _text(JE)
        immediate = je[je.index("immediate = {"):je.index("complete = {")]
        self.assertIn("covert_tradecraft_init = yes", immediate)

    def test_bonus_modifier(self):
        block = _top_level_block(_text(STATIC), "iw_tradecraft_bonus = {")
        self.assertIn("country_intelligence_capacity_mult = 0.05", block)
        refresh = _top_level_block(_text(EFFECTS), "covert_tradecraft_refresh_bonus = {")
        self.assertIn("multiplier = covert_tradecraft_bonus_mult", refresh)
        self.assertIn("je:je_covert_warfare", refresh)
        loc = _all_loc()
        self.assertRegex(loc, r"(?m)^ iw_tradecraft_bonus:0 ")
        self.assertRegex(loc, r"(?m)^ iw_tradecraft_bonus_desc:0 ")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest test_covert_tradecraft -v`
Expected: the 7 new tests FAIL/ERROR; the 10 from Task 1 PASS.

- [ ] **Step 3: Document the variables in the effects header**

In `common/scripted_effects/covert_warfare_effects.txt`, replace the header lines

```
# Always remove_list_variable before destroy_container, so iw_ops never holds
```

with

```
# The operator also carries its agency's experience (slice 5, § TRADECRAFT):
#
#   iw_tradecraft              0 - covert_tradecraft_max. Written ONLY by
#                              covert_tradecraft_gain / covert_tradecraft_loss
#   iw_tradecraft_last_reason  code of the most recent change (see § TRADECRAFT)
#   iw_tradecraft_ops          operations counted towards this month's gain (display)
#
# Always remove_list_variable before destroy_container, so iw_ops never holds
```

- [ ] **Step 4: Add the TRADECRAFT effects section**

In the same file, insert this block directly before the line `# MONTHLY RECONCILIATION` (i.e. before its `# ====` banner line — anchor on the banner line immediately above `# MONTHLY RECONCILIATION`, after the closing `}` of `covert_nets_sync`):

```
# ============================================================================
# TRADECRAFT (slice 5)
# ============================================================================
# The agency's experience score, iw_tradecraft on the operator. Constants and
# projections: covert_warfare_script_values.txt (Section 1 and § TRADECRAFT);
# tiers and unlocks: covert_warfare_triggers.txt § TRADECRAFT.
#
# REASON CODES (iw_tradecraft_last_reason; kept in step with
# covert_tradecraft_last_reason in covert_warfare_custom_loc.txt):
#    1 operations maturing (monthly gain)
#   20 a mild-tier operation burned        23 a wartime operation burned
#   21 a moderate-tier operation burned    24 idle: no operation running
#   22 a severe-tier operation burned
#
# OLD SAVES: the gain and loss writers are no-ops until the variable exists.
# covert_tradecraft_init seeds it, from the journal entry's immediate and at
# the top of every monthly pass (immediate does not re-run for an entry that
# was already active when the save was made).

# Seed an agency that has no score.
# Scope: operator country
covert_tradecraft_init = {
	if = {
		limit = { NOT = { has_variable = iw_tradecraft } }
		set_variable = { name = iw_tradecraft value = 0 }
	}
}

# Hold the score inside [0, covert_tradecraft_max]. Straight after every write.
# Scope: operator country (expects iw_tradecraft to exist)
covert_tradecraft_clamp = {
	clamp_variable = { name = iw_tradecraft min = 0 max = covert_tradecraft_max }
}

# Add experience. $AMOUNT$ is nominal; diminishing returns scale it down above
# half (covert_tradecraft_gain_scale). set_variable with an inline value block,
# not change_variable, which does not reliably resolve a script-value operand.
# Parameters: $AMOUNT$ = nominal points (number or script value, >= 0)
#             $REASON$ = reason code (table above)
# Scope: operator country
covert_tradecraft_gain = {
	if = {
		limit = { has_variable = iw_tradecraft }
		set_variable = {
			name = iw_tradecraft
			value = {
				value = var:iw_tradecraft
				add = {
					value = $AMOUNT$
					multiply = covert_tradecraft_gain_scale
				}
			}
		}
		covert_tradecraft_clamp = yes
		set_variable = { name = iw_tradecraft_last_reason value = $REASON$ }
	}
}

# Lose experience. Not scaled: a burn costs the same at any score.
# Parameters: $AMOUNT$ = points (number or script value, >= 0)
#             $REASON$ = reason code (table above)
# Scope: operator country
covert_tradecraft_loss = {
	if = {
		limit = { has_variable = iw_tradecraft }
		set_variable = {
			name = iw_tradecraft
			value = {
				value = var:iw_tradecraft
				subtract = $AMOUNT$
			}
		}
		covert_tradecraft_clamp = yes
		set_variable = { name = iw_tradecraft_last_reason value = $REASON$ }
	}
}

# Re-apply the tier bonus on the journal entry. The ONE refresh site for
# iw_tradecraft_bonus: called only from covert_tradecraft_monthly.
# Scope: operator country
covert_tradecraft_refresh_bonus = {
	if = {
		limit = { covert_tradecraft_tier >= 1 }
		je:je_covert_warfare = { remove_modifier = iw_tradecraft_bonus }
		je:je_covert_warfare = { add_modifier = { name = iw_tradecraft_bonus multiplier = covert_tradecraft_bonus_mult } }
	}
	else_if = {
		limit = { je:je_covert_warfare = { has_modifier = iw_tradecraft_bonus } }
		je:je_covert_warfare = { remove_modifier = iw_tradecraft_bonus }
	}
}

# The monthly Tradecraft pass. Called ONCE a month from je_covert_warfare's
# pulse, after covert_ops_age_all_durations (so the phase is this month's) —
# never from covert_ops_sync_all or covert_refresh_funding_state, which run on
# every stepper click.
#   1. Seed if missing.
#   2. Count operations at establishing or better, capped at
#      covert_tradecraft_ops_counted, into iw_tradecraft_ops.
#   3. Gain if any count; else decay if no operation runs at all. Operations
#      still preparatory neither gain nor decay.
#   4. Refresh the tier bonus.
# Scope: operator country
covert_tradecraft_monthly = {
	save_scope_as = iw_tc_operator
	covert_tradecraft_init = yes
	set_variable = { name = iw_tradecraft_ops value = 0 }
	if = {
		limit = { has_variable_list = iw_ops }
		every_in_list = {
			variable = iw_ops
			limit = { covert_op_is_established = yes }
			scope:iw_tc_operator = { change_variable = { name = iw_tradecraft_ops add = 1 } }
		}
	}
	clamp_variable = { name = iw_tradecraft_ops min = 0 max = covert_tradecraft_ops_counted }
	if = {
		limit = { var:iw_tradecraft_ops >= 1 }
		covert_tradecraft_gain = { AMOUNT = covert_tradecraft_monthly_gain_nominal REASON = 1 }
	}
	else_if = {
		limit = { covert_operations_active < 1 }
		covert_tradecraft_loss = { AMOUNT = covert_tradecraft_decay REASON = 24 }
	}
	covert_tradecraft_refresh_bonus = yes
}

```

- [ ] **Step 5: Wire the journal entry**

In `common/journal_entries/je_covert_warfare.txt`, in `immediate`, after the `iw_funding_level` initialisation `if` block (still inside `immediate = { }`), add:

```
		# Agency experience starts at 0 (slice 5). Also seeded by the monthly
		# pass, for saves whose entry was already active.
		covert_tradecraft_init = yes
```

In `on_monthly_pulse`, directly after the line `covert_ops_age_all_durations = yes`, add:

```

			# ---- Tradecraft (slice 5) ----
			# Once a month, here and only here (the steppers re-run the sync).
			# After aging, so an operation that just reached establishing
			# counts this month. Runs at any funding: idle decay needs it.
			covert_tradecraft_monthly = yes
```

- [ ] **Step 6: Add the static modifier and its loc**

In `common/static_modifiers/extra_modifiers.txt`, directly after the closing `}` of `iw_domestic_defense = { … }`, add:

```

# Agency experience (slice 5). Applied to je_covert_warfare by
# covert_tradecraft_refresh_bonus with multiplier = the Tradecraft tier (0-4).
# Network growth per tier is scripted (covert_tradecraft_net_gain_mult), not a
# modifier field.
iw_tradecraft_bonus = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
	country_intelligence_capacity_mult = 0.05
}
```

In `localization/english/te_miscellaneous_l_english.yml`, add (anywhere under `l_english:`; `organize_loc.py` re-homes it):

```
 iw_tradecraft_bonus:0 "Agency Tradecraft"
 iw_tradecraft_bonus_desc:0 "Our intelligence service's accumulated experience sharpens everything it does. Each tier of Tradecraft adds to our [concept_intelligence_capacity] and speeds the growth of our networks abroad."
```

(`concept_intelligence_capacity` exists: `iw_funding_defense_desc` already uses it.)

- [ ] **Step 7: Run tests**

Run: `python3 -m unittest test_covert_tradecraft -v`
Expected: 17 PASS.

- [ ] **Step 8: Format, BOM check, commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt common/journal_entries/je_covert_warfare.txt common/static_modifiers/extra_modifiers.txt
for f in common/scripted_effects/covert_warfare_effects.txt common/journal_entries/je_covert_warfare.txt common/static_modifiers/extra_modifiers.txt; do head -c3 $f | xxd; done
git add test_covert_tradecraft.py common/scripted_effects/covert_warfare_effects.txt common/journal_entries/je_covert_warfare.txt common/static_modifiers/extra_modifiers.txt localization/english/te_miscellaneous_l_english.yml
git commit -m "feat(covert): Tradecraft writers, monthly pass and tier bonus (slice 5)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LzWgjf8JaejpTAvUoAm2TG"
```

---

### Task 3: The burn loss

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (§ TRADECRAFT, after `covert_tradecraft_loss`)
- Modify: `events/covert_warfare_events.txt` (`covert_warfare.1` `after`)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`covert_op_burned_tt`)
- Test: `test_covert_tradecraft.py`

**Interfaces:**
- Consumes: `covert_tradecraft_loss` (Task 2), `covert_tradecraft_burn_loss_value` and the loss constants (Task 1), `covert_code_tier_*` (existing).
- Produces: effect `covert_tradecraft_burn_loss` (operator scope; reads `var:iw_burned_type_code`).

- [ ] **Step 1: Write the failing tests**

Append to `test_covert_tradecraft.py`:

```python
class BurnLossTests(unittest.TestCase):
    def test_burn_loss_branches_by_tier(self):
        block = _top_level_block(_text(EFFECTS), "covert_tradecraft_burn_loss = {")
        for tier, reason in (("mild", 20), ("severe", 22), ("war", 23)):
            self.assertIn("covert_code_tier_%s = { VAR = iw_burned_type_code }" % tier, block)
            self.assertIn(
                "covert_tradecraft_loss = { AMOUNT = covert_tradecraft_loss_%s REASON = %d }" % (tier, reason),
                block,
            )
        self.assertIn(
            "covert_tradecraft_loss = { AMOUNT = covert_tradecraft_loss_moderate REASON = 21 }", block
        )

    def test_burn_loss_before_cleanup(self):
        body = _text(EVENTS)
        event = _top_level_block(body, "covert_warfare.1 = {")
        after = event[event.index("\tafter = {"):]
        call = after.index("covert_tradecraft_burn_loss = yes")
        self.assertLess(after.index("covert_op_burn = { TYPE = destabilization"), call)
        self.assertLess(call, after.index("remove_variable = iw_burned_type_code"))
        # Inside the same guard as the burn: charged only when a burn happened.
        guard = after.index("exists = scope:detected_by_country")
        self.assertLess(guard, call)
        self.assertLess(call, after.index("trigger_event = { id = covert_warfare.2 }"))

    def test_burned_tooltip_names_loss(self):
        self.assertRegex(
            _all_loc(),
            r"(?m)^ covert_op_burned_tt:0 .*covert_tradecraft_burn_loss_value",
        )
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest test_covert_tradecraft -v`
Expected: the 3 new tests FAIL/ERROR.

- [ ] **Step 3: Add the burn-loss effect**

In `common/scripted_effects/covert_warfare_effects.txt`, directly after the closing `}` of `covert_tradecraft_loss`, add:

```

# Charge the burn now being resolved, by its tier. Called from
# covert_warfare.1's `after`, inside the same guard as covert_op_burn and BEFORE
# the event removes iw_burned_type_code (which it reads). Mirrors
# covert_tradecraft_burn_loss_value, which the options' tooltip prints; an
# unrecognised code is charged as moderate there and here.
# Scope: operator country (while covert_warfare.1 is open)
covert_tradecraft_burn_loss = {
	if = {
		limit = { covert_code_tier_mild = { VAR = iw_burned_type_code } }
		covert_tradecraft_loss = { AMOUNT = covert_tradecraft_loss_mild REASON = 20 }
	}
	else_if = {
		limit = { covert_code_tier_severe = { VAR = iw_burned_type_code } }
		covert_tradecraft_loss = { AMOUNT = covert_tradecraft_loss_severe REASON = 22 }
	}
	else_if = {
		limit = { covert_code_tier_war = { VAR = iw_burned_type_code } }
		covert_tradecraft_loss = { AMOUNT = covert_tradecraft_loss_war REASON = 23 }
	}
	else = {
		covert_tradecraft_loss = { AMOUNT = covert_tradecraft_loss_moderate REASON = 21 }
	}
}
```

- [ ] **Step 4: Call it from `covert_warfare.1`'s `after`**

In `events/covert_warfare_events.txt`, inside `after`, find the end of the nine-way branch (the closing `}` of `else_if = { limit = { var:iw_burned_type_code = 8 } covert_op_burn = { TYPE = destabilization … } }`) followed by a blank line and `scope:detected_by_country = {`. Insert between them:

```

			# The agency's experience takes the hit (slice 5), by tier. Here,
			# while iw_burned_type_code still exists; removed further down.
			covert_tradecraft_burn_loss = yes
```

so the block reads: nine-way branch → `covert_tradecraft_burn_loss = yes` → `scope:detected_by_country = { trigger_event = { id = covert_warfare.2 } }`, all inside the `if = { limit = { exists = scope:detected_by_country has_variable = iw_burned_type_code } … }`.

Also extend the event's header comment (the `# Fired by covert_ops_roll_detection_all …` paragraph) with one line: `# after also charges the agency's Tradecraft by the burned operation's tier.`

- [ ] **Step 5: Name the loss in the options' tooltip**

In `localization/english/te_miscellaneous_l_english.yml`, replace

```
 covert_op_burned_tt:0 "The compromised operation will be terminated, and our network in their country loses #R [GetPlayer.MakeScope.ScriptValue('covert_net_burn_loss')|0]#! strength."
```

with

```
 covert_op_burned_tt:0 "The compromised operation will be terminated, our network in their country loses #R [GetPlayer.MakeScope.ScriptValue('covert_net_burn_loss')|0]#! strength, and our agency's Tradecraft falls by #R [GetPlayer.MakeScope.ScriptValue('covert_tradecraft_burn_loss_value')|0]#!."
```

- [ ] **Step 6: Run tests**

Run: `python3 -m unittest test_covert_tradecraft -v` → 20 PASS.
Run: `python3 -m unittest test_covert_detection_roll test_covert_exposure_tiers -v` → PASS (they pin the `after` branch structure).

- [ ] **Step 7: Format, BOM check, commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt events/covert_warfare_events.txt
head -c3 events/covert_warfare_events.txt | xxd
git add test_covert_tradecraft.py common/scripted_effects/covert_warfare_effects.txt events/covert_warfare_events.txt localization/english/te_miscellaneous_l_english.yml
git commit -m "feat(covert): a burn costs Tradecraft by tier (slice 5)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LzWgjf8JaejpTAvUoAm2TG"
```

---

### Task 4: The consumers — priority-3 gate, per-type cap, network growth

**Files:**
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (`covert_possible_priority_up`)
- Modify: `common/script_values/covert_warfare_script_values.txt` (`covert_ops_max_per_type`, `covert_net_tick_gain`)
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (`covert_nets_sync`; the `iw_net` header doc)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`iw_priority_3_needs_tradecraft_tt`)
- Modify: `localization/english/te_journal_entries_l_english.yml` (`je_iw_slots_detail_tooltip`)
- Test: `test_covert_tradecraft.py`

**Interfaces:**
- Consumes: `covert_tradecraft_unlocks_priority_3`, `covert_tradecraft_unlocks_extra_per_type`, `covert_tradecraft_net_gain_mult`, `covert_tradecraft_tier_2_floor`, `covert_tradecraft_tier_4_floor`.
- Produces: network variable `iw_net_tc_mult`; operator staging variable `iw_tc_net_mult_staging` (transient).

- [ ] **Step 1: Write the failing tests**

Append to `test_covert_tradecraft.py`:

```python
class ConsumerTests(unittest.TestCase):
    def test_priority_gate_only_on_step_to_three(self):
        body = _text(TRIGGERS)
        up = _top_level_block(body, "covert_possible_priority_up = {")
        self.assertIn("text = iw_priority_3_needs_tradecraft_tt", up)
        self.assertIn("covert_tradecraft_unlocks_priority_3 = yes", up)
        # An operation below priority 2 steps freely.
        self.assertIn("NOT = { covert_op_priority_at_least = { N = 2 } }", up)
        down = _top_level_block(body, "covert_possible_priority_down = {")
        self.assertNotIn("tradecraft", down)
        # The AI goes through the same trigger.
        ai = _top_level_block(_text(EFFECTS), "covert_ai_manage_priorities = {")
        self.assertIn("covert_possible_priority_up = yes", ai)

    def test_per_type_cap_veteran(self):
        block = _top_level_block(_text(VALUES), "covert_ops_max_per_type = {")
        self.assertIn("covert_tradecraft_unlocks_extra_per_type = yes", block)
        self.assertIn("mainframe_computers", block)

    def test_net_multiplier_copied_before_gain(self):
        block = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        stage = block.index("set_variable = { name = iw_tc_net_mult_staging value = covert_tradecraft_net_gain_mult }")
        tick = block.index("# ---- 3. Tick ----")
        copy = block.index("set_variable = { name = iw_net_tc_mult value = scope:iw_net_operator.var:iw_tc_net_mult_staging }")
        gain = block.index("covert_net_gain = { AMOUNT = covert_net_tick_gain }")
        self.assertLess(stage, tick)
        self.assertLess(tick, copy)
        self.assertLess(copy, gain)
        self.assertIn("remove_variable = iw_tc_net_mult_staging", block[gain:])

    def test_tick_gain_reads_multiplier(self):
        block = _top_level_block(_text(VALUES), "covert_net_tick_gain = {")
        self.assertIn("has_variable = iw_net_tc_mult", block)
        self.assertIn("multiply = var:iw_net_tc_mult", block)

    def test_gate_loc(self):
        loc = _all_loc()
        self.assertRegex(loc, r"(?m)^ iw_priority_3_needs_tradecraft_tt:0 .*covert_tradecraft_tier_2_floor")
        self.assertRegex(loc, r"(?m)^ je_iw_slots_detail_tooltip:0 .*covert_tradecraft_tier_4_floor")
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest test_covert_tradecraft -v`
Expected: the 5 new tests FAIL.

- [ ] **Step 3: Gate priority 3**

In `common/scripted_triggers/covert_warfare_triggers.txt`, in `covert_possible_priority_up`, replace the two placeholder comment lines

```
	# Slice 5 adds its Tradecraft gate on the step to priority 3 here, as one
	# more custom_tooltip, so it binds the stepper and the AI alike.
```

with

```
	# Tradecraft gate (slice 5): the step TO priority 3 needs an Established
	# agency. Only the step up is gated — an operation already at 3 stays
	# there when the score falls, and stepping down is never blocked. The AI
	# steps through this same trigger (covert_ai_manage_priorities).
	custom_tooltip = {
		text = iw_priority_3_needs_tradecraft_tt
		OR = {
			scope:iw_op ?= { NOT = { covert_op_priority_at_least = { N = 2 } } }
			covert_tradecraft_unlocks_priority_3 = yes
		}
	}
```

Add to `te_miscellaneous_l_english.yml`:

```
 iw_priority_3_needs_tradecraft_tt:0 "Priority #v 3#! needs an agency of at least #bold Established#! Tradecraft (#v [GetPlayer.MakeScope.ScriptValue('covert_tradecraft_tier_2_floor')|0]#!)"
```

(Phrased as a condition: `IsValidTooltip` renders it with a tick when it holds, like the other `iw_priority_*_tt` lines.)

- [ ] **Step 4: Veteran per-type cap**

In `common/script_values/covert_warfare_script_values.txt`, replace

```
# Maximum operations of the same type that can run simultaneously
# Scales with technology: 1 base + 1 with mainframe_computers + 1 with cyber_warfare
covert_ops_max_per_type = {
	value = 1
	if = { limit = { has_technology_researched = mainframe_computers } add = 1 }
	if = { limit = { has_technology_researched = cyber_warfare } add = 1 }
}
```

with

```
# Maximum operations of the same type that can run simultaneously
# 1 base + 1 with mainframe_computers + 1 with cyber_warfare + 1 for a Veteran
# agency (slice 5). Only gates launching: an operation over the cap after the
# score falls keeps running.
covert_ops_max_per_type = {
	value = 1
	if = { limit = { has_technology_researched = mainframe_computers } add = 1 }
	if = { limit = { has_technology_researched = cyber_warfare } add = 1 }
	if = { limit = { covert_tradecraft_unlocks_extra_per_type = yes } add = 1 }
}
```

In `localization/english/te_journal_entries_l_english.yml`, replace the tail of `je_iw_slots_detail_tooltip`:

```
\n\n#italic An unused slot is not wasted: each one is redirected to counterintelligence.#!"
```

with

```
\n\n#italic An unused slot is not wasted: each one is redirected to counterintelligence.#!\n#italic Up to one operation of each type, plus one each from Mainframe Computers and Cyber Warfare, plus one for a #bold Veteran#! agency (Tradecraft #v [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_tier_4_floor')|0]#!).#!"
```

- [ ] **Step 5: Network growth**

In `common/script_values/covert_warfare_script_values.txt`, replace the whole `covert_net_tick_gain = { … }` block with:

```
covert_net_tick_gain = {
	value = var:iw_net_ops
	max = 3
	subtract = 1
	min = 0
	multiply = covert_net_extra_op_factor
	add = 1
	multiply = covert_net_gain_base
	# The operator's Tradecraft (slice 5): staged onto the network by
	# covert_nets_sync just before this is read; missing reads as x1.
	if = {
		limit = { has_variable = iw_net_tc_mult }
		multiply = var:iw_net_tc_mult
	}
}
```

and add a line to its comment block above: `# Multiplied by the operator's Tradecraft network multiplier (var:iw_net_tc_mult).`

In `common/scripted_effects/covert_warfare_effects.txt`, `covert_nets_sync`:

(a) directly after its first line `save_scope_as = iw_net_operator`, add

```
	# Tradecraft's network growth multiplier (slice 5), staged once for the
	# tick to copy onto each network (rule: containers read the operator via
	# scope:<country>.var:, never parent). Removed at the end of the pass.
	set_variable = { name = iw_tc_net_mult_staging value = covert_tradecraft_net_gain_mult }
```

(b) inside `# ---- 3. Tick ----`'s `every_in_list = { variable = iw_nets`, as the first statement before `if = { limit = { var:iw_net_ops >= 1 }`, add

```
				set_variable = { name = iw_net_tc_mult value = scope:iw_net_operator.var:iw_tc_net_mult_staging }
```

(c) as the last statement of `covert_nets_sync` (after the closing `}` of the outer `if = { limit = { has_variable_list = iw_nets } … }`, before the effect's own closing `}`), add

```
	remove_variable = iw_tc_net_mult_staging
```

(d) in the file header's `iw_net` variable table, add a row under `iw_net_head_start_offer`:

```
#           iw_net_tc_mult          operator's Tradecraft growth multiplier, copied each tick (slice 5)
```

and in the `covert_nets_sync` comment's step 3, append: `Gains are multiplied by the operator's Tradecraft (iw_net_tc_mult).`

- [ ] **Step 6: Run tests**

Run: `python3 -m unittest test_covert_tradecraft test_covert_networks test_covert_priority -v`
Expected: all PASS. If a slice-4/slice-3 test pinned an exact block that this task extended, update that test's expectation to the new text **only** where the change is the one this task specifies, and say so in the commit message.

- [ ] **Step 7: Format, BOM check, commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_triggers/covert_warfare_triggers.txt common/script_values/covert_warfare_script_values.txt common/scripted_effects/covert_warfare_effects.txt
git add test_covert_tradecraft.py common/scripted_triggers/covert_warfare_triggers.txt common/script_values/covert_warfare_script_values.txt common/scripted_effects/covert_warfare_effects.txt localization/english/te_miscellaneous_l_english.yml localization/english/te_journal_entries_l_english.yml
git commit -m "feat(covert): Tradecraft unlocks priority 3 and a per-type slot, speeds networks (slice 5)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LzWgjf8JaejpTAvUoAm2TG"
```

---

### Task 5: Command-centre row, custom loc and harness

**Files:**
- Modify: `common/customizable_localization/covert_warfare_custom_loc.txt` (append)
- Modify: `gui/journal_entry_widgets/covert_operations_widget.gui` (header comment; command centre between FUNDING and DETECTION FACTORS)
- Modify: `localization/english/te_journal_entries_l_english.yml`, `te_miscellaneous_l_english.yml`, `te_events_l_english.yml`
- Modify: `common/scripted_effects/te_debug_covert_effects.txt` (append), `events/te_debug_covert_events.txt` (append `te_debug_covert.3`)
- Test: `test_covert_tradecraft.py`

**Interfaces:**
- Consumes: `covert_tradecraft_display`, `covert_tradecraft_max`, `covert_tradecraft_tier_1..4`, `iw_tradecraft_last_reason`, `iw_tradecraft_ops`, `covert_tradecraft_monthly`.
- Produces: custom loc `covert_tradecraft_tier_name`, `covert_tradecraft_last_reason`; loc `je_iw_tradecraft_header/_line/_tooltip`; harness effects `te_debug_covert_set_tradecraft = { VALUE }`, `te_debug_covert_tick_tradecraft`; event `te_debug_covert.3`.

- [ ] **Step 1: Write the failing tests**

Append to `test_covert_tradecraft.py`:

```python
class DisplayTests(unittest.TestCase):
    def test_custom_loc_tier_names_cover_every_band(self):
        block = _top_level_block(_text(CUSTOM_LOC), "covert_tradecraft_tier_name = {")
        for n in range(0, 5):
            self.assertIn("iw_tradecraft_tier_name_%d" % n, block)
        for n in range(1, 5):
            self.assertIn("covert_tradecraft_tier_%d = yes" % n, block)

    def test_custom_loc_reasons_cover_every_code(self):
        block = _top_level_block(_text(CUSTOM_LOC), "covert_tradecraft_last_reason = {")
        for code in (1, 20, 21, 22, 23, 24):
            self.assertIn("var:iw_tradecraft_last_reason = %d" % code, block)
            self.assertIn("iw_tradecraft_reason_%d" % code, block)

    def test_widget_row(self):
        body = _text(WIDGET)
        cc = body[body.index('name = "widget_je_covert_command_centre"'):body.index('name = "widget_je_covert_operations"')]
        self.assertIn('text = "je_iw_tradecraft_header"', cc)
        self.assertIn('text = "je_iw_tradecraft_line"', cc)
        self.assertIn('tooltip = "je_iw_tradecraft_tooltip"', cc)
        self.assertLess(cc.index("je_iw_funding_header"), cc.index("je_iw_tradecraft_header"))
        self.assertLess(cc.index("je_iw_tradecraft_header"), cc.index("je_iw_detection_header"))

    def test_loc_keys_exist(self):
        loc = _all_loc()
        keys = ["je_iw_tradecraft_header", "je_iw_tradecraft_line", "je_iw_tradecraft_tooltip"]
        keys += ["iw_tradecraft_tier_name_%d" % n for n in range(5)]
        keys += ["iw_tradecraft_reason_%d" % c for c in (0, 1, 20, 21, 22, 23, 24)]
        keys += ["te_debug_covert.3.t", "te_debug_covert.3.d", "te_debug_covert.3.f"]
        keys += ["te_debug_covert.3.%s" % o for o in "abc"]
        for key in keys:
            self.assertRegex(loc, r"(?m)^ %s:0 " % re.escape(key), key)

    def test_harness(self):
        effects = _text(DEBUG_EFFECTS)
        setter = _top_level_block(effects, "te_debug_covert_set_tradecraft = {")
        self.assertIn("covert_tradecraft_init = yes", setter)
        self.assertIn("covert_tradecraft_clamp = yes", setter)
        self.assertIn("covert_tradecraft_refresh_bonus = yes", setter)
        tick = _top_level_block(effects, "te_debug_covert_tick_tradecraft = {")
        self.assertIn("covert_tradecraft_monthly = yes", tick)
        event = _top_level_block(_text(DEBUG_EVENTS), "te_debug_covert.3 = {")
        self.assertIn("REVIEWED", event.splitlines()[0])
        self.assertIn("te_debug_covert_set_tradecraft = { VALUE = 45 }", event)
        self.assertIn("te_debug_covert_set_tradecraft = { VALUE = 85 }", event)
        self.assertIn("te_debug_covert_tick_tradecraft = yes", event)
```

Note: `test_monthly_called_only_from_pulse` (Task 2) checks `covert_warfare_effects.txt` only, so the harness calling `covert_tradecraft_monthly` from `te_debug_covert_effects.txt` is allowed.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest test_covert_tradecraft -v` → the 5 new tests FAIL.

- [ ] **Step 3: Custom loc**

Append to `common/customizable_localization/covert_warfare_custom_loc.txt`:

```

# The agency's Tradecraft tier name (slice 5). Branches on the tier triggers,
# never on a number, so the floors live only in covert_warfare_triggers.txt.
covert_tradecraft_tier_name = {
	type = country
	random_valid = no

	text = {
		trigger = { covert_tradecraft_tier_4 = yes }
		localization_key = iw_tradecraft_tier_name_4
	}
	text = {
		trigger = { covert_tradecraft_tier_3 = yes }
		localization_key = iw_tradecraft_tier_name_3
	}
	text = {
		trigger = { covert_tradecraft_tier_2 = yes }
		localization_key = iw_tradecraft_tier_name_2
	}
	text = {
		trigger = { covert_tradecraft_tier_1 = yes }
		localization_key = iw_tradecraft_tier_name_1
	}
	text = {
		localization_key = iw_tradecraft_tier_name_0
	}
}

# Why the score last moved. Codes: covert_warfare_effects.txt § TRADECRAFT.
covert_tradecraft_last_reason = {
	type = country
	random_valid = no

	text = {
		trigger = {
			has_variable = iw_tradecraft_last_reason
			var:iw_tradecraft_last_reason = 1
		}
		localization_key = iw_tradecraft_reason_1
	}
	text = {
		trigger = {
			has_variable = iw_tradecraft_last_reason
			var:iw_tradecraft_last_reason = 20
		}
		localization_key = iw_tradecraft_reason_20
	}
	text = {
		trigger = {
			has_variable = iw_tradecraft_last_reason
			var:iw_tradecraft_last_reason = 21
		}
		localization_key = iw_tradecraft_reason_21
	}
	text = {
		trigger = {
			has_variable = iw_tradecraft_last_reason
			var:iw_tradecraft_last_reason = 22
		}
		localization_key = iw_tradecraft_reason_22
	}
	text = {
		trigger = {
			has_variable = iw_tradecraft_last_reason
			var:iw_tradecraft_last_reason = 23
		}
		localization_key = iw_tradecraft_reason_23
	}
	text = {
		trigger = {
			has_variable = iw_tradecraft_last_reason
			var:iw_tradecraft_last_reason = 24
		}
		localization_key = iw_tradecraft_reason_24
	}
	text = {
		localization_key = iw_tradecraft_reason_0
	}
}
```

- [ ] **Step 4: Loc**

Add to `te_miscellaneous_l_english.yml`:

```
 iw_tradecraft_tier_name_0:0 "Untested"
 iw_tradecraft_tier_name_1:0 "Fledgling"
 iw_tradecraft_tier_name_2:0 "Established"
 iw_tradecraft_tier_name_3:0 "Seasoned"
 iw_tradecraft_tier_name_4:0 "Veteran"
 iw_tradecraft_reason_0:0 "#italic No operation has yet taught our service anything.#!"
 iw_tradecraft_reason_1:0 "#italic Last change: #G operations past their preparatory phase#! taught our officers their trade.#!"
 iw_tradecraft_reason_20:0 "#italic Last change: #R an espionage operation was exposed.#!#!"
 iw_tradecraft_reason_21:0 "#italic Last change: #R an operation meddling in a foreign government was exposed.#!#!"
 iw_tradecraft_reason_22:0 "#italic Last change: #R an operation against a foreign state itself was exposed.#!#!"
 iw_tradecraft_reason_23:0 "#italic Last change: #R a wartime sabotage operation was exposed.#!#!"
 iw_tradecraft_reason_24:0 "#italic Last change: #R with no operation running, our officers' skills are going stale.#!#!"
```

Add to `te_journal_entries_l_english.yml` (next to the other `je_iw_*` keys):

```
 je_iw_tradecraft_header:0 "#bold Tradecraft#!"
 je_iw_tradecraft_line:0 "Score #v [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_display')|0]#! of [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_max')|0] - #bold [JournalEntry.GetCountry.GetCustom('covert_tradecraft_tier_name')]#!\n[JournalEntry.GetCountry.GetCustom('covert_tradecraft_last_reason')]"
 je_iw_tradecraft_tooltip:0 "#bold How Tradecraft moves#!\nEach month, every operation past its preparatory phase adds up to #G [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_gain_per_op')|1]#! (at most [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_ops_counted')|0] operations count; this month #v [JournalEntry.GetCountry.MakeScope.Var('iw_tradecraft_ops').GetValue|0]#!). Gains shrink above half.\nAn exposed operation costs #R [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_loss_mild')|0]#! (espionage), #R [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_loss_moderate')|0]#! (meddling), #R [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_loss_severe')|0]#! (attacking the state) or #R [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_loss_war')|0]#! (wartime sabotage). With no operation running it drifts down by #R [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_decay')|2]#! a month.\n\n#bold Each tier#! adds to [concept_intelligence_capacity] and grows our networks #G [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_net_gain_pct_display')|0]%#! faster:\n[JournalEntry.GetCountry.GetModifier.GetValueWithBreakdownFor('country_intelligence_capacity_mult')]\n\n#bold Unlocks#!\nFledgling at [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_tier_1_floor')|0]; #bold Established#! at [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_tier_2_floor')|0]: operations may run at priority 3; #bold Seasoned#! at [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_tier_3_floor')|0]; #bold Veteran#! at [JournalEntry.GetCountry.MakeScope.ScriptValue('covert_tradecraft_tier_4_floor')|0]: one more operation of each type.\n#italic Nothing already running is ever ended when Tradecraft falls.#!"
```

The Seasoned rung names only the tier and its number: the operations it unlocks arrive in slice 6, which adds the text then. Loc must not promise what the code does not deliver.

`MakeScope.Var('x').GetValue` is the proven accessor for a country variable in this mod (see `je_colonial_empire_band_headline`).

- [ ] **Step 5: Widget row**

In `gui/journal_entry_widgets/covert_operations_widget.gui`, in the command centre, insert between the funding-dormant-banner `covert_cc_line` (the one whose `visible` is `covert_ops_dormant_sgui`) and `### ---- DETECTION FACTORS ----`:

```

	### ---- TRADECRAFT (slice 5) ----
	### Score, tier name (custom loc, branching on the tier triggers) and why it
	### last moved; the tooltip carries the rules, the capacity breakdown and
	### the unlock ladder.
	covert_cc_header = {
		blockoverride "header_text" { text = "je_iw_tradecraft_header" }
	}
	covert_cc_line = {
		blockoverride "line_text" { text = "je_iw_tradecraft_line" }
		blockoverride "line_extra" { tooltip = "je_iw_tradecraft_tooltip" }
	}
```

In the file header, extend the `widget_je_covert_command_centre` description: `Intelligence capacity, operation slots, the funding ladder and its stepper, Tradecraft (slice 5), the detection factors and the defensive side.`

- [ ] **Step 6: Harness**

Append to `common/scripted_effects/te_debug_covert_effects.txt`:

```

# Put the agency's Tradecraft at an exact score (slice 5) and re-apply the tier
# bonus at once, so the command centre's line, the capacity breakdown and the
# unlocks can be checked without months of play. Records no reason: the line
# keeps showing whatever last moved the score for real.
# Parameters: $VALUE$ = 0 .. covert_tradecraft_max
# Scope: country
te_debug_covert_set_tradecraft = {
	covert_tradecraft_init = yes
	set_variable = { name = iw_tradecraft value = $VALUE$ }
	covert_tradecraft_clamp = yes
	covert_tradecraft_refresh_bonus = yes
}

# One monthly Tradecraft pass without waiting for the pulse (gain, or idle
# decay with no operations running).
# Scope: country
te_debug_covert_tick_tradecraft = {
	covert_tradecraft_monthly = yes
}
```

Append to `events/te_debug_covert_events.txt` (after `te_debug_covert.2`'s closing brace):

```

te_debug_covert.3 = { # REVIEWED 2026-09-22: console-only test event (`event te_debug_covert.3`); never fired by script on purpose
	type = country_event
	placement = ROOT

	event_image = { texture = "gfx/event_pictures/espionage_dead_drop.dds" }

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_default.dds"

	title = te_debug_covert.3.t
	desc = te_debug_covert.3.d
	flavor = te_debug_covert.3.f

	# ---- Tradecraft (slice 5): Established. Priority 3 unlocks; the stepper's
	#      up button on a priority-2 row turns valid. Capacity +10%.
	option = {
		name = te_debug_covert.3.a
		default_option = yes
		te_debug_covert_set_tradecraft = { VALUE = 45 }
	}

	# ---- Veteran. "At most N of any one type" rises by one; capacity +20%;
	#      networks grow x1.6 from the next tick.
	option = {
		name = te_debug_covert.3.b
		te_debug_covert_set_tradecraft = { VALUE = 85 }
	}

	# ---- One monthly Tradecraft pass now.
	option = {
		name = te_debug_covert.3.c
		te_debug_covert_tick_tradecraft = yes
	}
}
```

Add to `te_events_l_english.yml` next to the `te_debug_covert.2.*` keys:

```
 te_debug_covert.3.t:0 "DEBUG: Covert Tradecraft"
 te_debug_covert.3.d:0 "Console test harness for the agency experience score (slice 5). Set the score, then check the command centre's Tradecraft line, its tooltip, the priority stepper and the per-type cap."
 te_debug_covert.3.f:0 "Not for play."
 te_debug_covert.3.a:0 "Set Tradecraft to 45 (Established)"
 te_debug_covert.3.b:0 "Set Tradecraft to 85 (Veteran)"
 te_debug_covert.3.c:0 "Run one monthly Tradecraft pass"
```

(Match the exact wording style of the existing `te_debug_covert.2.*` keys; read them first.)

- [ ] **Step 7: organize_loc, run tests**

```bash
python3 organize_loc.py
git diff --stat localization/
```
Confirm `te_unused_l_english.yml` gained no new key. If `organize_loc` splits a 4+-token family (memory: base key to MISCELLANEOUS, `_desc` to CONCEPTS), add a `startswith` rule for the prefix in `organize_loc.py` and re-run.

Run: `python3 -m unittest test_covert_tradecraft -v` → 30 PASS.

- [ ] **Step 8: Format, BOM check, commit**

```bash
python3 scripts/format_paradox_tabs.py common/customizable_localization/covert_warfare_custom_loc.txt gui/journal_entry_widgets/covert_operations_widget.gui common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt
for f in common/customizable_localization/covert_warfare_custom_loc.txt gui/journal_entry_widgets/covert_operations_widget.gui common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt; do head -c3 $f | xxd; done
git add test_covert_tradecraft.py common/customizable_localization/covert_warfare_custom_loc.txt gui/journal_entry_widgets/covert_operations_widget.gui common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt localization/english/
git commit -m "feat(covert): Tradecraft row in the command centre; console harness (slice 5)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LzWgjf8JaejpTAvUoAm2TG"
```

(`git add localization/english/` is safe only if `git status localization/` shows no unrelated change; otherwise add the specific files.)

---

### Task 6: Docs, full verification, PR

**Files:**
- Modify: `docs/systems/mod_systems.md` § Covert Warfare System (starts ~line 1533)
- Modify: `docs/systems/journal_entry_systems.md` § Covert Warfare (~line 288) — **CRLF**
- Modify: `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` § Slice 5 (append an "As built" paragraph)

- [ ] **Step 1: mod_systems.md**

Read the whole § Covert Warfare System first. Add a **Tradecraft (slice 5)** bullet in the same style as the slice-4 networks bullet, covering the variable and its only writers, the gain/loss/decay figures, the tier table (Untested/Fledgling/Established/Seasoned/Veteran at 0/20/40/60/80), the bonus modifier and its single refresh site, the three unlock triggers, the pulse position, the one-month network lag, and the spec's own limitation: *Tradecraft only accrues while the journal entry is active (its pulse is the only clock).* Also update the per-type-cap sentence wherever the section states the cap, and the pulse-order list if the section has one.

- [ ] **Step 2: journal_entry_systems.md (CRLF)**

With `Edit` only, add the Tradecraft header/line to the command-centre description and `te_debug_covert.3` to the console-harness list. Then:

```bash
grep -c $'\r$' docs/systems/journal_entry_systems.md; wc -l < docs/systems/journal_entry_systems.md
```
The two numbers must be equal.

- [ ] **Step 3: Spec "As built"**

Append to § Slice 5 of the spec: `**As built (plan docs/superpowers/plans/2026-09-22-covert-tradecraft.md).**` followed by the departures: tier names (Untested / Fledgling / Established / Seasoned / Veteran; "Storied" dropped, because the spec's unlock lines bind Established = 40); reason codes 1/20–24; the loss runs in `covert_warfare.1`'s `after`; networks grow at last month's tier; the Seasoned unlock is a trigger only until slice 6.

- [ ] **Step 4: Full verification**

```bash
ruff check .
python3 -m unittest test_covert_tradecraft test_covert_detection_roll test_covert_exposure_tiers test_covert_networks test_covert_priority test_covert_stand_down
python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt' '*.gui')
python3 scripts/analysis/check_localization_files.py
curl -s http://localhost:8950/status | head -c 300
curl -s -X POST 'http://localhost:8950/reload?mod_only=true&audits_only=true' | python3 -m json.tool > /tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/57371aef-add3-4f31-941a-23e6ee782124/scratchpad/reload.json; python3 -c "import json;d=json.load(open('/tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/57371aef-add3-4f31-941a-23e6ee782124/scratchpad/reload.json'));print(d.get('warnings'));print(d.get('parse_failures'))"
```

If the server is down, start it (standing approval): `.venv/bin/python mod_state_server.py` with `run_in_background`, then poll `/status`. The full suite (`python3 -m unittest discover -s . -p 'test_*.py'`) runs from the main checkout only.

Expected: `warnings` empty, or containing only findings that predate this branch (compare against a reload on `main` if unsure). Specifically check `docs/engine/loc_coverage_report.md`, `modifier_visibility_report.md` (`iw_tradecraft_bonus` at ×1 shows `+5%`), `modifier_multiplier_var_report.md` (`covert_tradecraft_bonus_mult` reads a permanent variable; if flagged, add `# REVIEWED 2026-09-22: iw_tradecraft is permanent once seeded, never removed` on the `multiplier =` line) and `effect_trigger_validity_report.md`. Then confirm `/modifier-search?q=country_intelligence_capacity_mult` lists `iw_tradecraft_bonus` as a grant.

**Do not commit** the `docs/engine/*` churn the reload writes (it predates this branch in the tree), and do not commit the untracked reload output.

- [ ] **Step 5: Commit docs**

```bash
git add docs/systems/mod_systems.md docs/systems/journal_entry_systems.md docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md docs/superpowers/plans/2026-09-22-covert-tradecraft.md
git commit -m "docs(covert): Tradecraft (slice 5)

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LzWgjf8JaejpTAvUoAm2TG"
```

- [ ] **Step 6: PR**

Write the body to `/tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/57371aef-add3-4f31-941a-23e6ee782124/scratchpad/pr_slice5.md` first. It should give a summary, the balance projection table from the spec (and the equilibria: one moderate op at 10% settles near 70, two near 85), the tier/unlock table, the decisions list above, and these **in-game checks** for `te_debug_covert.3`:
1. Set 45 → the command-centre line reads "Established", and the tooltip's capacity breakdown shows Agency Tradecraft +10%. On a priority-2 row, the up button is valid.
2. Set 15 → the same up button greys out with `iw_priority_3_needs_tradecraft_tt` crossed.
3. Set 85 → the slots line reads one more "of any one type". **Launch a second operation of a type already at cap** to prove `covert_ops_max_per_type` resolves the tier inside `any_scope_diplomatic_pact = { count >= … }` (the display alone does not prove it).
4. `te_debug_covert.2` option b (force a burn) → the options' tooltip names the Tradecraft loss, and after the click the score falls by the tier's amount with the matching reason line.
5. Stand everything down, then run option c → the score drifts down by 0.25, with the idle reason.
6. Read `debug.log` through the `log-triage` skill afterwards.

Then:

```bash
git push -u origin covert-tradecraft
gh pr create --base main --title "feat(covert): agency experience — Tradecraft (slice 5)" --body-file /tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/57371aef-add3-4f31-941a-23e6ee782124/scratchpad/pr_slice5.md
```

End the body with:

```
🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LzWgjf8JaejpTAvUoAm2TG
```

- [ ] **Step 7: Update the memory file** `project_covert_warfare_expansion_slices.md`: slice 4 merged (#377), slice 5 PR number, branch `covert-tradecraft`, and the tier-name decision.
