# Covert Warfare Slice 1: Per-Operation Detection Roll — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the covert journal entry's single country-level monthly detection roll (which burns a *random* operation) with one honest roll per running operation, at most one burn a month, and hand the burned operation to the detection event as a saved scope.

**Architecture:** Every running covert operation is already a script container (`iw_op` + `iw_op_<TYPE>` tags, listed in the operator's `iw_ops` variable list) carrying its own detection percentage `iw_detect`, refreshed at the top of every monthly pulse by `covert_ops_sync_all`. A new scripted effect walks that list, rolls `random = { chance = covert_op_roll_chance }` per container, collects successes in a temporary list, picks one at random, and fires `covert_warfare.1` with it saved as `scope:iw_burned_op`. The event reads the container in `immediate` only (copying its type code onto a ROOT variable, because event loc and delayed option/`after` blocks cannot safely reach a container) and branches on that variable to burn the right pact.

**Tech Stack:** Victoria 3 Clausewitz script (Paradox `.txt`, tab-indented, UTF-8 BOM), Python 3 unittest for a structural regression test, the mod state server's `POST /reload` audits, the in-game console harness `event te_debug_covert.2`.

**Spec:** `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` § Slice 1.

## Global Constraints

- Brace-based `.txt` files use **tab** indentation and keep their UTF-8 BOM (`head -c3 <file> | xxd -p` = `efbbbf`). Run `python3 scripts/format_paradox_tabs.py <files>` after large edits.
- `any_*` triggers never take `limit = { }`.
- `random_in_list` / `every_in_list` over a saved scope of a **container**: never chain `scope:<container>.var:X`; hop through a country scope (`scope:c = { ROOT = { set_variable = { … value = PREV.var:X } } }`).
- Guard every use of a saved scope that may be unset with `if = { limit = { exists = scope:x } }`.
- The JE monthly pulse effect runs in **country** scope (it already calls `every_scope_diplomatic_pact` directly); only `multiplier =` and loc are JE-rooted.
- No `is_ai` forks in mechanics.
- Every new player-visible key needs an entry in `localization/english/te_miscellaneous_l_english.yml` (covert keys live there) or `te_events_l_english.yml` (event text); run `python3 organize_loc.py` after adding keys.
- Commit by path (`git add <files>`), never `git commit -a`; leave the `docs/engine/*` and `common/buy_packages/00_buy_packages.txt` reload churn unstaged.
- Use `python3`; for server-touching commands use `.venv/bin/python`.

## File Structure

| File | Responsibility in this slice |
|---|---|
| `common/script_values/covert_warfare_script_values.txt` | New Section-1 constant `covert_ops_detection_multi_op_scale`; new container-scope value `covert_op_roll_chance`. |
| `common/scripted_effects/covert_warfare_effects.txt` | `covert_op_sync` gains `CODE`; `covert_ops_sync_all` rows pass it; new `covert_ops_roll_detection_all`. |
| `common/journal_entries/je_covert_warfare.txt` | Pulse calls the new effect; the "restore target_max_ic" block and the old `random_list` are deleted. |
| `events/covert_warfare_events.txt` | `covert_warfare.1` takes `scope:iw_burned_op`; `immediate` copies the type code to ROOT; `after` branches on it. |
| `common/customizable_localization/covert_warfare_custom_loc.txt` | New `covert_burned_type_name` (reads `iw_burned_type_code`) so the event names the operation. |
| `common/scripted_effects/te_debug_covert_effects.txt`, `events/te_debug_covert_events.txt` | Harness option "force a detection" now pins one operation's `iw_detect` to 100 and calls the real roll effect. |
| `localization/english/te_events_l_english.yml`, `te_miscellaneous_l_english.yml` | Event text names the burned operation; harness option label. |
| `test_covert_detection_roll.py` (new) | Structural regression test: parses the four script files and pins the invariants of the new roll. |
| `docs/systems/mod_systems.md` § Covert Warfare System | Detection paragraph rewritten; the "single roll" Known Behaviour deleted. |

---

### Task 1: Structural regression test (red)

**Files:**
- Create: `test_covert_detection_roll.py`

**Interfaces:**
- Consumes: `paradox_file_parser.ParadoxFileParser().parse_file(path, apply_directives=False)` → populates `parser.data`, a dict keyed by top-level name whose every field is an `('=', value)` tuple (nested blocks are dicts of the same shape) — hence the `_val` helper.
- Produces: nothing for later tasks; every later task turns one of these assertions green.

- [ ] **Step 1: Write the failing test**

```python
"""Structural regression test for the covert per-operation detection roll
(spec: docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md,
slice 1).

The engine cannot be run in CI, so these tests pin the *shape* of the script
the slice changed: the pulse rolls per operation through one named effect, the
old country-level roll and its target_max_ic restore block are gone, the
detection event is driven by scope:iw_burned_op, and every sync row carries a
type code. A refactor that silently re-introduces the single roll, or drops a
CODE from one of the nine rows, fails here rather than in a play test.

Run: python3 test_covert_detection_roll.py
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
JE = ROOT / "common/journal_entries/je_covert_warfare.txt"
EVENTS = ROOT / "events/covert_warfare_events.txt"

OP_TYPES = [
    "election_interference",
    "financial_subversion",
    "infrastructure_sabotage",
    "comms_disruption",
    "industrial_espionage",
    "military_espionage",
    "influence_campaign",
    "ideological_subversion",
    "destabilization",
]


def _parse(path):
    p = ParadoxFileParser()
    p.parse_file(str(path), apply_directives=False)
    return p.data


def _val(node):
    """The parser stores every field as an ('=', value) tuple; unwrap one."""
    return node[1] if isinstance(node, tuple) else node


def _text(path):
    return path.read_text(encoding="utf-8-sig")


class RollEffectTests(unittest.TestCase):
    def test_roll_effect_is_defined_and_rolls_per_container(self):
        data = _parse(EFFECTS)
        self.assertIn("covert_ops_roll_detection_all", data)
        body = _text(EFFECTS)
        block = body[body.index("covert_ops_roll_detection_all = {"):]
        self.assertIn("random = {", block)
        self.assertIn("chance = covert_op_roll_chance", block)
        self.assertIn("add_to_temporary_list = iw_detected_ops", block)
        self.assertIn("random_in_list = {", block)
        self.assertIn("save_scope_as = iw_burned_op", block)
        self.assertIn("exists = scope:iw_burned_op", block)
        self.assertIn("trigger_event = { id = covert_warfare.1 }", block)

    def test_roll_chance_value_reads_the_container(self):
        data = _parse(VALUES)
        self.assertIn("covert_op_roll_chance", data)
        self.assertIn("covert_ops_detection_multi_op_scale", data)
        sv = _val(data["covert_op_roll_chance"])
        self.assertEqual(_val(sv["value"]), "var:iw_detect")
        self.assertEqual(_val(sv["multiply"]), "covert_ops_detection_multi_op_scale")

    def test_every_sync_row_passes_a_distinct_code(self):
        body = _text(EFFECTS)
        block = body[body.index("covert_ops_sync_all = {"):]
        block = block[: block.index("\n}\n") + 3]
        codes = {}
        for t in OP_TYPES:
            m = re.search(
                r"covert_op_sync = \{[^}]*TYPE = %s [^}]*CODE = (\d+)" % re.escape(t),
                block,
            )
            self.assertIsNotNone(m, f"no CODE on the {t} sync row")
            codes[t] = int(m.group(1))
        self.assertEqual(sorted(codes.values()), list(range(9)))
        # The codes must match covert_last_exposed_type_name's mapping.
        self.assertEqual(codes["election_interference"], 0)
        self.assertEqual(codes["destabilization"], 8)
        sync = body[body.index("covert_op_sync = {"):]
        self.assertIn("name = iw_type_code value = $CODE$", sync)


class PulseTests(unittest.TestCase):
    def test_pulse_calls_the_roll_and_drops_the_country_roll(self):
        body = _text(JE)
        pulse = body[body.index("on_monthly_pulse = {"):]
        self.assertIn("covert_ops_roll_detection_all = yes", pulse)
        self.assertNotIn("covert_operation_detection_chance", pulse)
        self.assertNotIn("name = target_max_ic value = 0", pulse)
        self.assertNotIn("random_list", pulse)
        self.assertLess(
            pulse.index("covert_ops_apply_all_phase_effects = yes"),
            pulse.index("covert_ops_roll_detection_all = yes"),
            "the roll must run after phase effects, at the end of the pulse",
        )


class DetectionEventTests(unittest.TestCase):
    def test_event_is_driven_by_the_burned_op_scope(self):
        body = _text(EVENTS)
        ev = body[body.index("covert_warfare.1 = {"): body.index("covert_warfare.2 = {")]
        trigger = ev[ev.index("trigger = {"): ev.index("immediate = {")]
        self.assertIn("exists = scope:iw_burned_op", trigger)
        self.assertNotIn("random_scope_diplomatic_pact", ev)
        self.assertNotIn("scope:burned_pact", ev)
        immediate = ev[ev.index("immediate = {"): ev.index("option = {")]
        self.assertIn("save_scope_as = detected_by_country", immediate)
        self.assertIn("name = iw_burned_type_code", immediate)
        after = ev[ev.index("after = {"):]
        for code in range(9):
            self.assertIn(f"var:iw_burned_type_code = {code}", after)
        self.assertNotIn("scope:iw_burned_op", after)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 test_covert_detection_roll.py`
Expected: 6 tests, several FAIL/ERROR (`covert_ops_roll_detection_all` not in data; `covert_op_roll_chance` missing; no CODE on sync rows; pulse still contains `random_list`; event still uses `random_scope_diplomatic_pact`).

- [ ] **Step 3: Commit the red test**

```bash
git add test_covert_detection_roll.py
git commit -m "test(covert): pin the per-operation detection roll shape (red)"
```

---

### Task 2: Script values — the per-container roll chance

**Files:**
- Modify: `common/script_values/covert_warfare_script_values.txt` (Section 1 after line 30 `covert_ops_detection_funding_5_reduction = 6`; new block after `target_counterintelligence_penalty`, ~line 255)

**Interfaces:**
- Produces: `covert_op_roll_chance` (script value, **container scope**, 0–100) and `covert_ops_detection_multi_op_scale` (constant, default 1).

- [ ] **Step 1: Add the tuning constant to Section 1**

Insert after the line `covert_ops_detection_funding_5_reduction = 6`:

```
# Per-operation roll scale. Every running operation rolls its own iw_detect
# each month, so with N operations the chance that at least one burns is
# 1 - prod(1 - c_i). 1 = honest per-operation odds; lower it (0.6 puts three
# 10% operations near the old single-roll 18%) if N-operation risk lands hot.
covert_ops_detection_multi_op_scale = 1
```

- [ ] **Step 2: Add the container-scope roll value after `target_counterintelligence_penalty`**

```
# The chance one operation rolls against this month. iw_detect is written on
# the container by covert_op_refresh_detection at the top of the same pulse
# (covert_ops_sync_all), so it is never a month stale here. A named script
# value is the proven form for `random = { chance = ... }`
# (space_race_effects.txt); `chance = var:` is not.
# Scope: covert operation container
covert_op_roll_chance = {
	value = var:iw_detect
	multiply = covert_ops_detection_multi_op_scale
	min = 0
	max = 100
}
```

- [ ] **Step 3: Run the value test**

Run: `python3 test_covert_detection_roll.py RollEffectTests.test_roll_chance_value_reads_the_container`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add common/script_values/covert_warfare_script_values.txt
git commit -m "feat(covert): per-operation roll chance script value"
```

---

### Task 3: Effects — type codes on every operation, and the roll

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (`covert_op_sync` ~line 189; `covert_ops_sync_all` ~line 260; new effect after `covert_ops_apply_all_phase_effects`, before the `ELECTION INTERFERENCE` banner ~line 521)

**Interfaces:**
- Consumes: `covert_op_roll_chance` (Task 2).
- Produces: `covert_ops_roll_detection_all` (country scope, no params); every op container carries `iw_type_code` 0–8 after the first pulse; `covert_op_sync` signature becomes `{ TYPE ACTION DEFENSE_MOD CODE }`.

- [ ] **Step 1: Give `covert_op_sync` a `CODE` parameter**

In the header comment of `covert_op_sync` add a parameter line:

```
#             $CODE$ = operation type code 0-8 (the covert_last_exposed_type_name
#                      mapping); written on every container so old saves gain it
```

Inside the final `every_in_list` of `covert_op_sync` (the one that calls `covert_op_refresh_detection`), add the code write before the refresh:

```
			every_in_list = {
				variable = iw_ops
				limit = { has_tag = iw_op_$TYPE$ }
				remove_variable = iw_seen
				set_variable = { name = iw_type_code value = $CODE$ }
				covert_op_refresh_detection = { DEFENSE_MOD = $DEFENSE_MOD$ }
			}
```

- [ ] **Step 2: Pass the codes from `covert_ops_sync_all`**

Replace the nine rows with (codes match `covert_last_exposed_type_name`):

```
covert_ops_sync_all = {
	covert_op_sync = { TYPE = election_interference ACTION = covert_election_interference_action DEFENSE_MOD = country_covert_defense_ideological_add CODE = 0 }
	covert_op_sync = { TYPE = financial_subversion ACTION = covert_financial_subversion_action DEFENSE_MOD = country_covert_defense_economic_add CODE = 1 }
	covert_op_sync = { TYPE = infrastructure_sabotage ACTION = covert_infrastructure_sabotage_action DEFENSE_MOD = country_covert_defense_military_add CODE = 2 }
	covert_op_sync = { TYPE = comms_disruption ACTION = covert_comms_disruption_action DEFENSE_MOD = country_covert_defense_military_add CODE = 3 }
	covert_op_sync = { TYPE = industrial_espionage ACTION = covert_industrial_espionage_action DEFENSE_MOD = country_covert_defense_economic_add CODE = 4 }
	covert_op_sync = { TYPE = military_espionage ACTION = covert_military_espionage_action DEFENSE_MOD = country_covert_defense_military_add CODE = 5 }
	covert_op_sync = { TYPE = influence_campaign ACTION = covert_influence_campaign_action DEFENSE_MOD = country_covert_defense_ideological_add CODE = 6 }
	covert_op_sync = { TYPE = ideological_subversion ACTION = covert_ideological_subversion_action DEFENSE_MOD = country_covert_defense_ideological_add CODE = 7 }
	covert_op_sync = { TYPE = destabilization ACTION = covert_destabilization_action DEFENSE_MOD = country_covert_defense_ideological_add CODE = 8 }
}
```

- [ ] **Step 3: Add the roll effect** (new section between `covert_ops_apply_all_phase_effects` and the `ELECTION INTERFERENCE` banner)

```
# ============================================================================
# DETECTION ROLL
# ============================================================================
# One roll per running operation against that operation's own iw_detect, then
# at most ONE burn a month, chosen at random among the operations whose roll
# landed. Rolling every operation first and choosing afterwards is order-free:
# P(any burn) = 1 - prod(1 - c_i) whichever order the list is walked, and no
# type gets the full odds just for being synced first.
#
# The burned operation reaches covert_warfare.1 as scope:iw_burned_op (saved
# scopes survive trigger_event). The event reads it in `immediate` only.
#
# Scope: country (the journal entry pulse runs here). Caller gates on funding.
covert_ops_roll_detection_all = {
	if = {
		limit = { has_variable_list = iw_ops }
		every_in_list = {
			variable = iw_ops
			random = {
				chance = covert_op_roll_chance
				add_to_temporary_list = iw_detected_ops
			}
		}
		random_in_list = {
			list = iw_detected_ops
			save_scope_as = iw_burned_op
		}
		if = {
			limit = { exists = scope:iw_burned_op }
			trigger_event = { id = covert_warfare.1 }
		}
	}
}
```

- [ ] **Step 4: Run the effect tests**

Run: `python3 test_covert_detection_roll.py RollEffectTests`
Expected: 3 PASS

- [ ] **Step 5: Tab-normalise and commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt
head -c3 common/scripted_effects/covert_warfare_effects.txt | xxd -p   # efbbbf
git add common/scripted_effects/covert_warfare_effects.txt
git commit -m "feat(covert): roll detection per operation; stamp a type code on every container"
```

---

### Task 4: Journal entry pulse — call the roll, delete the country roll

**Files:**
- Modify: `common/journal_entries/je_covert_warfare.txt:304-349`

**Interfaces:**
- Consumes: `covert_ops_roll_detection_all` (Task 3).

- [ ] **Step 1: Replace the two blocks at the end of the pulse**

Delete everything from the comment `# ---- Restore target_max_ic to actual maximum for detection roll ----` (line 304) through the closing brace of the `random_list` detection block (line 349). In their place:

```
			# ---- Detection: one roll per operation, at most one burn ----
			# Each container's iw_detect was refreshed by covert_ops_sync_all at
			# the top of this pulse. Funding 0 has no operations to roll (every
			# pact's requirement_to_maintain lapses), so the gate is belt and braces.
			if = {
				limit = {
					has_variable = iw_funding_level
					var:iw_funding_level >= 1
				}
				covert_ops_roll_detection_all = yes
			}
```

- [ ] **Step 2: Verify `target_max_ic` is still written where it is read**

Run: `grep -n "target_max_ic" common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt common/journal_entries/je_covert_warfare.txt`
Expected: writes in `covert_op_refresh_detection`, reads in `target_counterintelligence_penalty`; **no** hit in the journal entry.

- [ ] **Step 3: Run the pulse test**

Run: `python3 test_covert_detection_roll.py PulseTests`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add common/journal_entries/je_covert_warfare.txt
git commit -m "feat(covert): journal pulse rolls detection per operation"
```

---

### Task 5: Detection event — driven by the burned operation

**Files:**
- Modify: `events/covert_warfare_events.txt:11-150` (`covert_warfare.1`)
- Modify: `common/customizable_localization/covert_warfare_custom_loc.txt` (append after `covert_last_exposed_type_name`)
- Modify: `localization/english/te_events_l_english.yml:570` (`covert_warfare.1.d`)

**Interfaces:**
- Consumes: `scope:iw_burned_op` (Task 3), `iw_type_code` on the container (Task 3).
- Produces: ROOT variable `iw_burned_type_code` (0–8) for the event's lifetime; customizable loc `covert_burned_type_name` (country scope).

- [ ] **Step 1: Rewrite the trigger and immediate**

Replace the `trigger` and `immediate` blocks of `covert_warfare.1` with:

```
	trigger = {
		exists = scope:iw_burned_op
	}

	immediate = {
		# The burned operation arrives as scope:iw_burned_op from
		# covert_ops_roll_detection_all. Read it HERE and only here: the options
		# and `after` run when the player clicks, up to `duration` days later, by
		# which time stand-down or the monthly sync may have destroyed it.
		# Event loc cannot reach a container either, so the type code is copied
		# onto ROOT (scripting_best_practices.md, container rule 10).
		scope:iw_burned_op = {
			var:iw_target = { save_scope_as = detected_by_country }
			ROOT = {
				set_variable = { name = iw_burned_type_code value = PREV.var:iw_type_code }
			}
		}
	}
```

- [ ] **Step 2: Rewrite `after` to branch on the ROOT variable**

Replace the `after` block with:

```
	after = {
		# Always burn the operation (pact + container) and notify the target,
		# whichever option was chosen. Branch on the code copied in `immediate`;
		# covert_op_destroy is idempotent, so a container that already vanished
		# is harmless.
		if = {
			limit = {
				exists = scope:detected_by_country
				has_variable = iw_burned_type_code
			}
			if = {
				limit = { var:iw_burned_type_code = 0 }
				covert_op_burn = { TYPE = election_interference ACTION = covert_election_interference_action TARGET = scope:detected_by_country CODE = 0 }
			}
			else_if = {
				limit = { var:iw_burned_type_code = 1 }
				covert_op_burn = { TYPE = financial_subversion ACTION = covert_financial_subversion_action TARGET = scope:detected_by_country CODE = 1 }
			}
			else_if = {
				limit = { var:iw_burned_type_code = 2 }
				covert_op_burn = { TYPE = infrastructure_sabotage ACTION = covert_infrastructure_sabotage_action TARGET = scope:detected_by_country CODE = 2 }
			}
			else_if = {
				limit = { var:iw_burned_type_code = 3 }
				covert_op_burn = { TYPE = comms_disruption ACTION = covert_comms_disruption_action TARGET = scope:detected_by_country CODE = 3 }
			}
			else_if = {
				limit = { var:iw_burned_type_code = 4 }
				covert_op_burn = { TYPE = industrial_espionage ACTION = covert_industrial_espionage_action TARGET = scope:detected_by_country CODE = 4 }
			}
			else_if = {
				limit = { var:iw_burned_type_code = 5 }
				covert_op_burn = { TYPE = military_espionage ACTION = covert_military_espionage_action TARGET = scope:detected_by_country CODE = 5 }
			}
			else_if = {
				limit = { var:iw_burned_type_code = 6 }
				covert_op_burn = { TYPE = influence_campaign ACTION = covert_influence_campaign_action TARGET = scope:detected_by_country CODE = 6 }
			}
			else_if = {
				limit = { var:iw_burned_type_code = 7 }
				covert_op_burn = { TYPE = ideological_subversion ACTION = covert_ideological_subversion_action TARGET = scope:detected_by_country CODE = 7 }
			}
			else_if = {
				limit = { var:iw_burned_type_code = 8 }
				covert_op_burn = { TYPE = destabilization ACTION = covert_destabilization_action TARGET = scope:detected_by_country CODE = 8 }
			}

			scope:detected_by_country = {
				trigger_event = { id = covert_warfare.2 }
			}
			remove_variable = iw_burned_type_code
		}
	}
```

Also update the header comment of the event (lines 3–9) to: "Fired by `covert_ops_roll_detection_all` with the burned operation in `scope:iw_burned_op`. The pact and container are removed in `after`; the attacker gains infamy and the target is notified."

- [ ] **Step 3: Name the operation in the event text**

Append to `common/customizable_localization/covert_warfare_custom_loc.txt`:

```

# The operation covert_warfare.1 is reporting on. Same mapping as
# covert_last_exposed_type_name, read from the code covert_warfare.1's
# `immediate` copied onto the country (the event's loc cannot see the container).
covert_burned_type_name = {
	type = country
	random_valid = no

	text = {
		trigger = { var:iw_burned_type_code = 0 }
		localization_key = iw_op_name_election_interference
	}
	text = {
		trigger = { var:iw_burned_type_code = 1 }
		localization_key = iw_op_name_financial_subversion
	}
	text = {
		trigger = { var:iw_burned_type_code = 2 }
		localization_key = iw_op_name_infrastructure_sabotage
	}
	text = {
		trigger = { var:iw_burned_type_code = 3 }
		localization_key = iw_op_name_comms_disruption
	}
	text = {
		trigger = { var:iw_burned_type_code = 4 }
		localization_key = iw_op_name_industrial_espionage
	}
	text = {
		trigger = { var:iw_burned_type_code = 5 }
		localization_key = iw_op_name_military_espionage
	}
	text = {
		trigger = { var:iw_burned_type_code = 6 }
		localization_key = iw_op_name_influence_campaign
	}
	text = {
		trigger = { var:iw_burned_type_code = 7 }
		localization_key = iw_op_name_ideological_subversion
	}
	text = {
		trigger = { var:iw_burned_type_code = 8 }
		localization_key = iw_op_name_destabilization
	}
	text = {
		localization_key = iw_op_name_unknown
	}
}
```

Then change `covert_warfare.1.d` in `localization/english/te_events_l_english.yml` to:

```
 covert_warfare.1.d:0 "Our intelligence services report a catastrophic security breach. Our [ROOT.GetCountry.GetCustom('covert_burned_type_name')] operation has been detected by [SCOPE.sCountry('detected_by_country').GetName]. The operation must be terminated immediately, and the diplomatic fallout will be considerable."
```

(`[ROOT.GetCountry.Custom('key')]` is the accessor form the existing `covert_last_exposed_*` widget text uses for customizable loc in country scope; keep the `[concept_covert_operations]` link if you prefer by writing "One of our [concept_covert_operations] — [ROOT.GetCountry.GetCustom('covert_burned_type_name')] — has been detected…".)

- [ ] **Step 4: Run the event test**

Run: `python3 test_covert_detection_roll.py DetectionEventTests`
Expected: PASS

- [ ] **Step 5: Whole test file, loc hygiene, commit**

```bash
python3 test_covert_detection_roll.py           # 6 PASS
python3 organize_loc.py
python3 scripts/analysis/check_localization_files.py
git add events/covert_warfare_events.txt common/customizable_localization/covert_warfare_custom_loc.txt localization/english/te_events_l_english.yml
git commit -m "feat(covert): detection event burns the operation whose roll landed"
```

If `organize_loc.py` moved lines in other loc files, add those files to the commit too (it is a generator; its output is the convention).

---

### Task 6: Console harness — force a specific operation's roll

**Files:**
- Modify: `common/scripted_effects/te_debug_covert_effects.txt` (append)
- Modify: `events/te_debug_covert_events.txt:85-90` (option `te_debug_covert.2.b`)
- Modify: `localization/english/te_events_l_english.yml:3837` (`te_debug_covert.2.b`)

**Interfaces:**
- Consumes: `covert_ops_roll_detection_all` (Task 3).

- [ ] **Step 1: Add the harness effect**

Append to `te_debug_covert_effects.txt`:

```

# Make the detection roll land on one specific operation: pin a random running
# operation's iw_detect to 100 and run the shipping roll effect, so the roll,
# the temporary-list pick and the scope hand-off to covert_warfare.1 are all
# exercised. The next monthly sync restores the honest figure.
# Scope: country
te_debug_covert_force_detection = {
	if = {
		limit = { has_variable_list = iw_ops }
		random_in_list = {
			variable = iw_ops
			set_variable = { name = iw_detect value = 100 }
		}
		covert_ops_roll_detection_all = yes
	}
}
```

- [ ] **Step 2: Point the harness option at it**

Replace option `te_debug_covert.2.b`:

```
	# ---- Force the detection roll to land on one running operation, through the
	#      real per-operation roll. The target gets covert_warfare.2 and, whether
	#      or not that event's cooldown lets it through, the "last exposed" record
	#      the command centre reads.
	option = {
		name = te_debug_covert.2.b
		trigger = { covert_operations_active >= 1 }
		te_debug_covert_force_detection = yes
	}
```

And the label at `te_events_l_english.yml:3837`:

```
 te_debug_covert.2.b:0 "Force a detection now (one operation is pinned to 100% and the real roll is run)"
```

- [ ] **Step 3: Confirm nothing else fires the event by hand**

Run: `git grep -n "trigger_event = { id = covert_warfare.1 }" -- common events`
Expected: exactly one hit, inside `covert_ops_roll_detection_all`.

- [ ] **Step 4: Commit**

```bash
git add common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt localization/english/te_events_l_english.yml
git commit -m "test(covert): console harness forces the per-operation roll"
```

---

### Task 7: Offline audits and the mod state server reload

**Files:** none new.

- [ ] **Step 1: Run the CI-equivalent checks**

```bash
python3 -m compileall -q .
python3 test_covert_detection_roll.py
ruff check .
python3 scripts/format_paradox_tabs.py --check common/scripted_effects/covert_warfare_effects.txt common/script_values/covert_warfare_script_values.txt common/journal_entries/je_covert_warfare.txt events/covert_warfare_events.txt common/customizable_localization/covert_warfare_custom_loc.txt common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt
python3 duplicate_key_audit.py --strict
python3 any_limit_audit.py --strict
python3 loc_render_audit.py --strict
python3 orphaned_event_audit.py --strict
python3 iterator_limit_audit.py --strict
python3 modifier_multiplier_var_audit.py --strict
python3 event_image_audit.py --strict
```
Expected: every command exits 0. `orphaned_event_audit` must still see `covert_warfare.1` as reachable (it is fired from a scripted effect); if it flags the event, the audit follows `trigger_event` through scripted effects — check its report before adding any suppression.

- [ ] **Step 2: Reload the server and read the warnings**

```bash
curl -s http://localhost:8950/status | head -c 300      # start it with .venv/bin/python mod_state_server.py if down
curl -s -X POST "http://localhost:8950/reload?mod_only=true&audits_only=true" | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps({k: d.get(k) for k in ('warnings','parse_failures','generators_wrote_files','reparsed_after_generators')}, indent=1))"
```
Expected: `warnings` empty (or only pre-existing entries unrelated to covert files — compare against a reload on `main`), `parse_failures` empty. Then check `docs/engine/effect_trigger_validity_report.md` has no `covert_` unresolved-helper line and `docs/engine/loc_coverage_report.md` has no new covert key.

- [ ] **Step 3: Full unit suite** (this is the main checkout, so `test_reload_post_load.py` may run)

Run: `python3 -m unittest discover -s . -p 'test_*.py' 2>&1 | tail -3`
Expected: `OK` (skips allowed).

No commit in this task unless an audit forced a fix; if it did, commit that fix on its own with a message naming the audit.

---

### Task 8: Documentation

**Files:**
- Modify: `docs/systems/mod_systems.md` § Covert Warfare System — the **Detection** bullet under "System Architecture" (~line 1560) and the first **Known Behaviours** bullet (~line 1594)
- Modify: `docs/guides/scripting_best_practices.md` — one bullet appended to the container rules list (after rule 12, ~line 1480)

- [ ] **Step 1: Rewrite the Detection bullet**

Replace the `- **Detection:** …` bullet with:

```
- **Detection:** each running operation carries its own monthly chance, `iw_detect` = `(base 10 − funding stealth + target counterintelligence penalty) × (1 − covert efficiency, floored at 0.2)`, clamped 1–50 %, refreshed by `covert_ops_sync_all` at the top of the pulse. `covert_ops_roll_detection_all` (last in the pulse) rolls every operation against `covert_op_roll_chance` (= `iw_detect × covert_ops_detection_multi_op_scale`, default 1), collects the successes in a temporary list and burns **at most one** per month, chosen at random among them, by firing `covert_warfare.1` with the container in `scope:iw_burned_op`. With N equal operations at c each, P(any burn) = 1 − (1 − c)^N: 10 % → 19 % at two, 27 % at three. The event reads the container only in `immediate` (target → `scope:detected_by_country`, `iw_type_code` → ROOT `iw_burned_type_code`) and branches on that variable in `after`; `covert_burned_type_name` names the operation in the text. The target penalty is `((target IC + target type defense) / attacker IC − 1) × 15`, capped at +20. Funding stealth is the cumulative reduction listed above.
```

- [ ] **Step 2: Replace the first Known Behaviour**

Delete the bullet beginning `- **The monthly detection roll is a single country-level roll, slightly mis-weighted.**` and put in its place:

```
- **Detection was a single country-level roll until 2026-09 (covert slice 1).** It rolled once against the worst target's intelligence capacity combined with an arbitrary target's type defence, then burned a *random* operation, and the `random_list { 1 = { add = c } 99 }` form made the odds (1 + c) / (100 + c) rather than c %. It now rolls per operation (see **Detection** above). The four `covert_detection_*_display` script values that the old roll would have needed remain unreferenced; the command centre deliberately shows no country-level detection number.
```

- [ ] **Step 3: Add the rolling-per-container bullet to the best-practices container rules**

Append after rule 12 in the container-rules list (`docs/guides/scripting_best_practices.md`):

```
13. **Roll per container, choose afterwards.** `every_in_list = { random = { chance = <named script value> add_to_temporary_list = hits } }` then `random_in_list = { list = hits save_scope_as = x }` gives every container its own honest odds and an order-free pick (P(any) = 1 − Π(1 − cᵢ)); stopping at the first success hands the full odds to whichever tag was walked first. The `chance` must be a **named** script value in container scope (`chance = var:x` is not the proven form). `covert_ops_roll_detection_all` is the worked example; the harness `te_debug_covert.2` pins one container to 100 to exercise the pick. And note the old `random_list { 1 = { add = c } 99 = { } }` idiom is not a c % roll — its odds are (1 + c) / (100 + c).
```

- [ ] **Step 4: Confirm the docs stayed LF and commit**

```bash
grep -c $'\r$' docs/systems/mod_systems.md docs/guides/scripting_best_practices.md   # both 0
git add docs/systems/mod_systems.md docs/guides/scripting_best_practices.md
git commit -m "docs(covert): per-operation detection roll; retire the single-roll known behaviour"
```

---

### Task 9: In-game verification and the PR

**Files:** none.

- [ ] **Step 1: Deploy and launch**

```bash
./scripts/deploy.sh --apply
```
Launch Victoria 3 with the mod (no Workshop copy of it in the playset), a save or new game past `television` with `covert_warfare_enabled`, as a country whose `je_covert_warfare` is active.

- [ ] **Step 2: Console sequence**

1. `event te_debug_covert.2` → option **a** (three operations against one neighbour at months 5 / 11 / 14).
2. Open the journal entry; note each row's detection %.
3. `event te_debug_covert.2` → option **b**. Expected: `covert_warfare.1` opens **immediately** and its text names one of the three operation types; after choosing an option that row is gone from the widget, the outliner pact is gone, and the target got `covert_warfare.2` (or, if its 24-month cooldown blocked it, its command centre "last exposed" line names you and the type).
4. Let two monthly pulses pass with the remaining two operations. Expected: no burn unless the rows' own percentages land; `debug.log` shows no `Undefined event target 'iw_burned_op'` and no `iw_type_code` "used but never set".
5. Break one operation from the outliner while `covert_warfare.1` is open for another (sanity: the event's `after` must not error when a different container is gone).

- [ ] **Step 3: Log triage**

Use the `log-triage` skill (`.claude/skills/log-triage/SKILL.md`): read `debug.log` via `/logs`, filter to the covert files, fix anything mod-side, and note anything non-obvious in `scripting_best_practices.md`.

- [ ] **Step 4: Open the PR**

Write the body to `/tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/8b17b6f1-d54c-4cc8-a267-39c1196a4c1e/scratchpad/pr_slice1.md` first (a killed session loses anything not on disk), including the balance table (1 op 10→10 %, 2 ops 10→19 %, 3 ops 10→27 %, 5 ops 10→41 % per month at c = 10 %), the console sequence run and its outcome, and `Spec: docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md § Slice 1`.

```bash
git push -u origin covert-per-op-roll
gh pr create --base main --title "feat(covert): roll detection per operation; at most one burn a month" --body-file /tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/8b17b6f1-d54c-4cc8-a267-39c1196a4c1e/scratchpad/pr_slice1.md
```
Then wait for CI and confirm every job is green before reporting done.
