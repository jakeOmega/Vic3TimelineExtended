# Covert Warfare Slice 2 — Graduated Exposure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the blowback from a detected covert operation depend on what the operation was and how far along it had got, instead of charging every burn the same +2/+1 infamy and −15/−30 relations.

**Architecture:** One tier table — four parameterized scripted triggers over the operation type code — is the single source every consumer reads: the blowback script values, both custom-loc tier names, and the pre-launch action descriptions. `covert_warfare.1`'s `immediate` copies the burned operation's type code (slice 1 already does) *and* its phase onto the operator country, because the event's options fire days later when the container may be gone and event loc cannot reach a container at all. Severe exposures additionally cool the target's power-bloc partners and treaty allies, through one scripted effect called from both options so the option tooltip previews it.

**Tech Stack:** Paradox Clausewitz script (`common/`, `events/`, `localization/`), Python 3 structural tests via `paradox_file_parser`.

**Spec:** `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` § "Slice 2 — Graduated exposure"

## Global Constraints

- Branch is `covert-graduated-exposure`, already checked out in the main repo checkout (`/home/jakef/src/Vic3TimelineExtended`). Never commit to `main`.
- Brace-based Paradox `.txt` files use **tab** indentation and carry a **UTF-8 BOM**. After editing any, run `python3 scripts/format_paradox_tabs.py <files>` and confirm the BOM survived (`head -c3 <file> | xxd` → `efbb bf`).
- **Never `git commit -a`.** Stage by explicit path. `docs/engine/*` and `common/buy_packages/00_buy_packages.txt` carry unrelated reload churn — leave them unstaged.
- Use `python3` (there is no `python` alias). Do not start or restart the mod state server; it is already running and the controller owns it.
- End every commit message with a truthful `Co-Authored-By: <your own model name> <noreply@anthropic.com>` line followed by `Claude-Session: https://claude.ai/code/session_01QqhVixDW2qsmJspd7HX8Xv`.
- After adding localization keys, run `python3 organize_loc.py` and stage whatever it moves.
- Do not dispatch subagents. Do the work yourself.
- **The tier table lives in exactly one place**: the four `covert_code_tier_*` scripted triggers. No other file may enumerate which codes belong to which tier.
- Operation type codes, fixed by slice 1: `0` election_interference, `1` financial_subversion, `2` infrastructure_sabotage, `3` comms_disruption, `4` industrial_espionage, `5` military_espionage, `6` influence_campaign, `7` ideological_subversion, `8` destabilization.
- `test_covert_detection_roll.py` (slice 1) must stay green. It asserts the **exact text** of this block in `covert_warfare.1`'s `after`, so keep it byte-identical and add any new removal as a *sibling* block:

```
		if = {
			limit = { has_variable = iw_burned_type_code }
			remove_variable = iw_burned_type_code
		}
```

- `any_*` triggers never take `limit = { }`. `ordered_*` sorts descending.

## Blowback table this plan implements

Blowback = tier base × phase factor, then the option's split. Phase factors: preparatory ×0.5, establishing ×1.0, fully operational ×1.5. **Acknowledge** pays full infamy and half the relations hit; **Deny** pays half the infamy and the full relations hit.

| Tier | Types (codes) | base infamy | base relations | third parties |
|---|---|---|---|---|
| mild | industrial_espionage (4), military_espionage (5) | 1 | −10 | none |
| moderate | election_interference (0), financial_subversion (1), influence_campaign (6) | 2 | −20 | none |
| severe | ideological_subversion (7), destabilization (8) | 4 | −40 | target's bloc partners and treaty allies: −10 relations + a feed notice |
| war | infrastructure_sabotage (2), comms_disruption (3) | 1 | none (block skipped) | none |

Today every burn costs +2/+1 infamy and −15/−30 relations. Moderate × establishing lands at 2/−10 (Acknowledge) and 1/−20 (Deny) — the same infamy, a softer relations hit. Severe × fully operational is 6/−30 and 3/−60.

## File structure

| File | Responsibility |
|---|---|
| `common/scripted_triggers/covert_warfare_triggers.txt` | the tier table (four parameterized triggers) — the single source |
| `common/script_values/covert_warfare_script_values.txt` | Section 1 tuning constants; a new exposure-blowback section; three retired values deleted |
| `common/scripted_effects/covert_warfare_effects.txt` | `covert_exposure_third_party_blowback` |
| `common/messages/extra_messages.txt` | the third-party feed notice type |
| `events/covert_warfare_events.txt` | `covert_warfare.1` rewiring; `covert_warfare.2` desc |
| `common/customizable_localization/covert_warfare_custom_loc.txt` | tier names for the attacker's and the defender's event |
| `common/diplomatic_actions/covert_operations.txt` | `is_hostile` on the influence campaign |
| `localization/english/te_*_l_english.yml` | tier names, notice text, the pre-launch tier note |
| `common/scripted_effects/te_debug_covert_effects.txt`, `events/te_debug_covert_events.txt` | a severe operation to plant, so the third-party branch is reachable in game |
| `test_covert_exposure_tiers.py` | new structural test pinning the tier table and every consumer |
| `docs/systems/mod_systems.md` | § Covert Warfare exposure documentation |

---

### Task 1: The tier table and the blowback numbers

**Files:**
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (append)
- Modify: `common/script_values/covert_warfare_script_values.txt` (Section 1 constants; new section; delete three values)
- Test: `test_covert_exposure_tiers.py` (create)

**Interfaces:**
- Produces: scripted triggers `covert_code_tier_mild|_moderate|_severe|_war = { VAR = <variable name> }` (country scope; `$VAR$` is the *name* of a country variable holding a type code, not an accessor). Script values `covert_exposure_infamy_acknowledge`, `covert_exposure_infamy_deny`, `covert_exposure_relations_acknowledge`, `covert_exposure_relations_deny`, `covert_exposure_third_party_relations` (all country scope, all reading `iw_burned_type_code` / `iw_burned_phase` on that country).
- Consumes: nothing from earlier tasks.

- [ ] **Step 1: Write the failing test**

Create `test_covert_exposure_tiers.py`:

```python
"""Structural tests for covert warfare slice 2 (graduated exposure).

The tier table is the single source of truth for how hostile each operation
type is when it is caught. These tests pin that table, pin that every consumer
reads it rather than re-listing codes, and pin the shape of the blowback the
detection event applies.
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
EVENTS = ROOT / "events/covert_warfare_events.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/covert_warfare_custom_loc.txt"
MESSAGES = ROOT / "common/messages/extra_messages.txt"
ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"

# Slice 1's codes, repeated here so this file stands alone.
CODES = {
    "election_interference": 0,
    "financial_subversion": 1,
    "infrastructure_sabotage": 2,
    "comms_disruption": 3,
    "industrial_espionage": 4,
    "military_espionage": 5,
    "influence_campaign": 6,
    "ideological_subversion": 7,
    "destabilization": 8,
}

TIER_CODES = {
    "mild": {4, 5},
    "moderate": {0, 1, 6},
    "severe": {7, 8},
    "war": {2, 3},
}

# Values slice 2 retires. None of them may survive anywhere in the mod.
RETIRED_VALUES = (
    "covert_detection_chance_display",
    "covert_detection_target_ic_display",
    "covert_ops_detected_infamy",
)

MOD_DIRS = ("common", "events", "gui", "localization")
MOD_SUFFIXES = {".txt", ".gui", ".yml"}


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """The text of one top-level `header = { ... }` entry, header through the
    first unindented closing brace. Safe because nested closing braces are
    always tab-indented (format_paradox_tabs.py).
    """
    block = body[body.index(header):]
    return block[: block.index("\n}\n") + 3]


def _tier_block(body, tier):
    return _top_level_block(body, "covert_code_tier_%s = {" % tier)


class TierTableTests(unittest.TestCase):
    def test_tier_triggers_partition_every_operation_code(self):
        # Slice 6 adds three operation types. Each new code must land in
        # exactly one tier, and no code may be forgotten.
        body = _text(TRIGGERS)
        seen = {}
        for tier, expected in TIER_CODES.items():
            codes = {int(m) for m in re.findall(r"var:\$VAR\$ = (\d+)", _tier_block(body, tier))}
            self.assertEqual(codes, expected, "tier %s holds the wrong codes" % tier)
            for code in codes:
                self.assertNotIn(code, seen, "code %d is in two tiers" % code)
                seen[code] = tier
        self.assertEqual(
            set(seen),
            set(CODES.values()),
            "every operation code must belong to exactly one exposure tier",
        )

    def test_tier_triggers_guard_the_variable(self):
        # Reading a variable that does not exist logs an engine error, and
        # these run from custom loc that may render before the code is stamped.
        body = _text(TRIGGERS)
        for tier in TIER_CODES:
            self.assertIn(
                "has_variable = $VAR$",
                _tier_block(body, tier),
                "covert_code_tier_%s must guard $VAR$" % tier,
            )

    def test_triggers_file_parses(self):
        parser = ParadoxFileParser()
        parser.parse_file(str(TRIGGERS), apply_directives=False)
        for tier in TIER_CODES:
            self.assertIn("covert_code_tier_%s" % tier, parser.data)


class BlowbackValueTests(unittest.TestCase):
    def test_blowback_values_read_the_tier_table(self):
        body = _text(VALUES)
        for name in ("covert_exposure_infamy_base", "covert_exposure_relations_base"):
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("covert_code_tier_", block, "%s must branch on the tier table" % name)
            self.assertIn("VAR = iw_burned_type_code", block)

    def test_phase_multiplier_reads_the_burned_phase(self):
        block = _top_level_block(_text(VALUES), "covert_exposure_phase_mult = {")
        self.assertIn("has_variable = iw_burned_phase", block)
        self.assertIn("var:iw_burned_phase", block)

    def test_option_values_exist_and_split_the_blowback(self):
        body = _text(VALUES)
        ack_infamy = _top_level_block(body, "covert_exposure_infamy_acknowledge = {")
        deny_infamy = _top_level_block(body, "covert_exposure_infamy_deny = {")
        ack_rel = _top_level_block(body, "covert_exposure_relations_acknowledge = {")
        deny_rel = _top_level_block(body, "covert_exposure_relations_deny = {")
        # Acknowledge pays the full infamy; Deny halves it.
        self.assertIn("covert_exposure_phase_mult", ack_infamy)
        self.assertIn("covert_exposure_deny_infamy_mult", deny_infamy)
        # Deny takes the full relations hit; Acknowledge halves it.
        self.assertIn("covert_exposure_phase_mult", deny_rel)
        self.assertIn("covert_exposure_acknowledge_relations_mult", ack_rel)

    def test_infamy_is_capped(self):
        block = _top_level_block(_text(VALUES), "covert_exposure_infamy_acknowledge = {")
        self.assertIn("max = covert_exposure_infamy_max", block)

    def test_retired_values_have_no_references_left(self):
        for name in RETIRED_VALUES:
            for directory in MOD_DIRS:
                for path in sorted((ROOT / directory).rglob("*")):
                    if not path.is_file() or path.suffix not in MOD_SUFFIXES:
                        continue
                    self.assertNotIn(
                        name,
                        path.read_text(encoding="utf-8-sig", errors="ignore"),
                        "%s still appears in %s" % (name, path),
                    )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_exposure_tiers -v`
Expected: FAIL — `ValueError: substring not found` on the missing `covert_code_tier_mild = {` block.

- [ ] **Step 3: Append the tier table to the triggers file**

At the end of `common/scripted_triggers/covert_warfare_triggers.txt`, after the last top-level entry's closing brace:

```
# ============================================================================
# EXPOSURE TIERS
# ============================================================================
# How hostile the world considers an operation when it is caught. This is THE
# tier table: the blowback script values, both custom-loc tier names and the
# pre-launch action descriptions all read these four triggers, so a new
# operation type is one code added to one OR list here and nowhere else.
#
# Parameters: $VAR$ = the NAME of a country variable holding an operation type
#             code — iw_burned_type_code on the operator while
#             covert_warfare.1 is open, iw_last_exposed_type on the target
#             afterwards. Each trigger guards the variable itself, because
#             reading one that does not exist is an engine error and custom
#             loc can render before anything has been exposed.
# Scope: country
# ============================================================================

# "Everyone spies" — stealing designs is not an attack on the state.
covert_code_tier_mild = {
	has_variable = $VAR$
	OR = {
		var:$VAR$ = 4
		var:$VAR$ = 5
	}
}

# Meddling in how the target governs itself.
covert_code_tier_moderate = {
	has_variable = $VAR$
	OR = {
		var:$VAR$ = 0
		var:$VAR$ = 1
		var:$VAR$ = 6
	}
}

# Attacking the state itself. These are the ones third parties hear about.
covert_code_tier_severe = {
	has_variable = $VAR$
	OR = {
		var:$VAR$ = 7
		var:$VAR$ = 8
	}
}

# Operations that only make sense against someone you are already fighting:
# infamy alone, because the relationship is already what it is.
covert_code_tier_war = {
	has_variable = $VAR$
	OR = {
		var:$VAR$ = 2
		var:$VAR$ = 3
	}
}
```

- [ ] **Step 4: Add the tuning constants to Section 1 of the script values**

In `common/script_values/covert_warfare_script_values.txt`, **replace** the two lines

```
# Infamy on detection
covert_ops_detected_infamy = 5
```

with:

```
# ---- Exposure blowback ----
# What being caught costs, before the phase factor and the option's split.
# Which tier a type is in lives in covert_code_tier_* (scripted triggers).
# Anchored on the flat +2 infamy / -15 relations every burn used to cost:
# a moderate operation caught while establishing still lands about there.
covert_exposure_infamy_mild = 1
covert_exposure_infamy_moderate = 2
covert_exposure_infamy_severe = 4
covert_exposure_infamy_war = 1

covert_exposure_relations_mild = -10
covert_exposure_relations_moderate = -20
covert_exposure_relations_severe = -40

# How far along the operation was. A network barely laid costs half; one that
# has been running a year costs half again as much.
covert_exposure_phase_mult_preparatory = 0.5
covert_exposure_phase_mult_establishing = 1
covert_exposure_phase_mult_operational = 1.5

# The two options' split. Owning it costs the infamy but keeps the bilateral
# damage down; denying it halves the infamy and takes the full relations hit.
covert_exposure_acknowledge_relations_mult = 0.5
covert_exposure_deny_infamy_mult = 0.5

# What a severe exposure costs with everyone tied to the target.
covert_exposure_third_party_relations = -10

# Guardrail, matching te_force_become_subject's own infamy cap.
covert_exposure_infamy_max = 25
```

- [ ] **Step 5: Delete the two dead display values**

Delete the whole top-level `covert_detection_chance_display = { ... }` and `covert_detection_target_ic_display = { ... }` entries (around lines 360 and 366) together with their comment headers. Nothing references either — `covert_detection_base_display`, `covert_detection_efficiency_pct_display` and `covert_ops_funding_detection_reduction_display` are live (they render `je_iw_detection_factors`); **do not touch those three.**

- [ ] **Step 6: Add the blowback section to the script values**

Append a new section at the end of `common/script_values/covert_warfare_script_values.txt`:

```
# ============================================================================
# SECTION: EXPOSURE BLOWBACK
# ============================================================================
# What a detected operation costs. covert_warfare.1's immediate copies the
# burned operation's type code and phase onto the operator country
# (iw_burned_type_code / iw_burned_phase) because the options fire days later,
# by which time the container may be gone — and event loc cannot reach a
# container in any case. Everything here reads those two country variables.
# Scope: country (the operator, while covert_warfare.1 is open)
# ============================================================================

# How far along the operation was when it was caught. A missing phase reads as
# establishing, which is the middle of the range and today's behaviour.
covert_exposure_phase_mult = {
	value = 0
	if = {
		limit = {
			has_variable = iw_burned_phase
			var:iw_burned_phase = 1
		}
		add = covert_exposure_phase_mult_preparatory
	}
	else_if = {
		limit = {
			has_variable = iw_burned_phase
			var:iw_burned_phase >= 3
		}
		add = covert_exposure_phase_mult_operational
	}
	else = {
		add = covert_exposure_phase_mult_establishing
	}
}

# The tier's base infamy. An unrecognised code reads as moderate.
covert_exposure_infamy_base = {
	value = 0
	if = {
		limit = { covert_code_tier_mild = { VAR = iw_burned_type_code } }
		add = covert_exposure_infamy_mild
	}
	else_if = {
		limit = { covert_code_tier_severe = { VAR = iw_burned_type_code } }
		add = covert_exposure_infamy_severe
	}
	else_if = {
		limit = { covert_code_tier_war = { VAR = iw_burned_type_code } }
		add = covert_exposure_infamy_war
	}
	else = {
		add = covert_exposure_infamy_moderate
	}
}

# The tier's base relations hit. The war tier is zero here, but the event also
# skips the relations effect outright so the option never reads "-0".
covert_exposure_relations_base = {
	value = 0
	if = {
		limit = { covert_code_tier_war = { VAR = iw_burned_type_code } }
		add = 0
	}
	else_if = {
		limit = { covert_code_tier_mild = { VAR = iw_burned_type_code } }
		add = covert_exposure_relations_mild
	}
	else_if = {
		limit = { covert_code_tier_severe = { VAR = iw_burned_type_code } }
		add = covert_exposure_relations_severe
	}
	else = {
		add = covert_exposure_relations_moderate
	}
}

# Acknowledging it: the full infamy.
covert_exposure_infamy_acknowledge = {
	value = covert_exposure_infamy_base
	multiply = covert_exposure_phase_mult
	min = 0
	max = covert_exposure_infamy_max
}

# Denying it: half the infamy.
covert_exposure_infamy_deny = {
	value = covert_exposure_infamy_acknowledge
	multiply = covert_exposure_deny_infamy_mult
}

# Denying it: the full bilateral relations hit.
covert_exposure_relations_deny = {
	value = covert_exposure_relations_base
	multiply = covert_exposure_phase_mult
	min = -100
	max = 0
}

# Acknowledging it: half of that.
covert_exposure_relations_acknowledge = {
	value = covert_exposure_relations_deny
	multiply = covert_exposure_acknowledge_relations_mult
}
```

- [ ] **Step 7: Format, check the BOM, run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_triggers/covert_warfare_triggers.txt common/script_values/covert_warfare_script_values.txt
head -c3 common/scripted_triggers/covert_warfare_triggers.txt | xxd | head -1
head -c3 common/script_values/covert_warfare_script_values.txt | xxd | head -1
python3 -m unittest test_covert_exposure_tiers test_covert_detection_roll -v
```

Expected: both `xxd` lines start `efbb bf`; all tests PASS.

- [ ] **Step 8: Commit**

```bash
git add common/scripted_triggers/covert_warfare_triggers.txt common/script_values/covert_warfare_script_values.txt test_covert_exposure_tiers.py
git commit -m "feat(covert): add the exposure tier table and graduated blowback values"
```

---

### Task 2: Third-party blowback on a severe exposure

**Files:**
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (append a new section)
- Modify: `common/messages/extra_messages.txt` (append one notice type)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (two keys)
- Test: `test_covert_exposure_tiers.py` (add a class)

**Interfaces:**
- Consumes: `covert_exposure_third_party_relations` (Task 1).
- Produces: scripted effect `covert_exposure_third_party_blowback` (country scope; ROOT must be the operator and `scope:detected_by_country` must exist — the caller guards both). Message type `covert_severe_exposure_notice`.

- [ ] **Step 1: Write the failing test**

Append to `test_covert_exposure_tiers.py`, before the `if __name__` block:

```python
class ThirdPartyBlowbackTests(unittest.TestCase):
    def test_effect_previews_in_a_tooltip(self):
        block = _top_level_block(_text(EFFECTS), "covert_exposure_third_party_blowback = {")
        # Only a custom_tooltip renders an every_country loop in an option
        # tooltip; without it the option previews as doing nothing.
        self.assertIn("custom_tooltip = {", block)
        self.assertIn("covert_exposure_third_party_tt", block)

    def test_effect_excludes_the_operator_and_the_target(self):
        block = _top_level_block(_text(EFFECTS), "covert_exposure_third_party_blowback = {")
        self.assertIn("NOT = { this = root }", block)
        self.assertIn("NOT = { this = scope:detected_by_country }", block)

    def test_bloc_audience_requires_the_target_to_have_a_bloc(self):
        # Without this guard two countries that are both in no power bloc can
        # read as being in the same one, which would spray the whole world.
        block = _top_level_block(_text(EFFECTS), "covert_exposure_third_party_blowback = {")
        self.assertIn("is_in_power_bloc = yes", block)
        self.assertIn("is_in_same_power_bloc = scope:detected_by_country", block)
        self.assertIn("has_treaty_alliance_with = { TARGET = scope:detected_by_country }", block)

    def test_effect_moves_relations_and_posts_the_notice(self):
        block = _top_level_block(_text(EFFECTS), "covert_exposure_third_party_blowback = {")
        self.assertIn("value = covert_exposure_third_party_relations", block)
        self.assertIn("post_notification = covert_severe_exposure_notice", block)

    def test_notice_type_is_defined(self):
        self.assertIn("covert_severe_exposure_notice = {", _text(MESSAGES))
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_exposure_tiers -v`
Expected: FAIL on the missing `covert_exposure_third_party_blowback = {` block.

- [ ] **Step 3: Add the scripted effect**

Append to `common/scripted_effects/covert_warfare_effects.txt`:

```
# ============================================================================
# EXPOSURE BLOWBACK
# ============================================================================

# The severe tier's third-party cost: everyone tied to the target — their power
# bloc and their treaty allies — hears what we were caught doing and cools
# towards us. Called from BOTH options of covert_warfare.1 rather than from
# `after`, because only an option's own effects render in its tooltip, and
# custom_tooltip is what makes an every_country loop previewable at all
# (banking_effect_cb_capital_controls_outflow is the same shape).
#
# The caller guards the tier and the existence of scope:detected_by_country.
# The bloc audience is guarded on the TARGET actually having a bloc: two
# countries that are both in none can otherwise read as being in the same one,
# which would hit every unaligned country on the map.
# Scope: country (the operator); scope:detected_by_country = the target
covert_exposure_third_party_blowback = {
	custom_tooltip = {
		text = covert_exposure_third_party_tt
		every_country = {
			limit = {
				NOT = { this = root }
				NOT = { this = scope:detected_by_country }
				OR = {
					AND = {
						scope:detected_by_country = { is_in_power_bloc = yes }
						is_in_same_power_bloc = scope:detected_by_country
					}
					has_treaty_alliance_with = { TARGET = scope:detected_by_country }
				}
			}
			change_relations = {
				country = root
				value = covert_exposure_third_party_relations
			}
			post_notification = covert_severe_exposure_notice
		}
	}
}
```

- [ ] **Step 4: Add the notice type**

Append to `common/messages/extra_messages.txt`:

```
covert_severe_exposure_notice = {
	type = country
	texture = "gfx/interface/icons/notification_icons/interest_group_bad.dds"
	notification_type = feed
	color = bad
}
```

- [ ] **Step 5: Add the two loc keys**

Add to `localization/english/te_miscellaneous_l_english.yml` (organize_loc will file them):

```
 covert_exposure_third_party_tt:0 "Every country in the target's [concept_power_bloc] and every one of their treaty allies loses #R 10#! [concept_relations] with us"
 covert_severe_exposure_notice:0 "A foreign power has been caught running a campaign to bring down a government we stand behind."
```

The notice text names nobody on purpose: a feed notification is rendered on the recipient, and whether the event's saved scopes reach it is unverified. Keep it scope-free.

- [ ] **Step 6: Format, organize loc, run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/covert_warfare_effects.txt common/messages/extra_messages.txt
python3 organize_loc.py
python3 -m unittest test_covert_exposure_tiers test_covert_detection_roll -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add common/scripted_effects/covert_warfare_effects.txt common/messages/extra_messages.txt localization/english test_covert_exposure_tiers.py
git commit -m "feat(covert): cool the target's bloc and allies when a severe operation is exposed"
```

---

### Task 3: Rewire covert_warfare.1 onto the graduated blowback

**Files:**
- Modify: `events/covert_warfare_events.txt` (`covert_warfare.1` only)
- Test: `test_covert_exposure_tiers.py` (add a class)

**Interfaces:**
- Consumes: the four option script values and `covert_exposure_third_party_blowback` (Tasks 1-2), plus the tier triggers.
- Produces: the country variable `iw_burned_phase` (set in `immediate`, removed in `after`).

- [ ] **Step 1: Write the failing test**

Append to `test_covert_exposure_tiers.py`:

```python
def _event_1(body):
    return body[body.index("covert_warfare.1 = {"): body.index("covert_warfare.2 = {")]


class ExposureEventTests(unittest.TestCase):
    def test_immediate_copies_the_phase_as_well_as_the_code(self):
        ev = _event_1(_text(EVENTS))
        immediate = ev[ev.index("immediate = {"): ev.index("option = {")]
        self.assertIn("name = iw_burned_type_code", immediate)
        self.assertIn("name = iw_burned_phase", immediate)
        self.assertIn("PREV.var:iw_phase", immediate)

    def test_options_use_the_graduated_values_not_literals(self):
        ev = _event_1(_text(EVENTS))
        options = ev[ev.index("option = {"): ev.index("after = {")]
        self.assertIn("value = covert_exposure_infamy_acknowledge", options)
        self.assertIn("value = covert_exposure_infamy_deny", options)
        self.assertIn("value = covert_exposure_relations_acknowledge", options)
        self.assertIn("value = covert_exposure_relations_deny", options)
        for literal in ("change_infamy = 2", "change_infamy = 1", "value = -15", "value = -30"):
            self.assertNotIn(literal, options, "%s survived the rewiring" % literal)

    def test_relations_are_skipped_for_the_war_tier(self):
        ev = _event_1(_text(EVENTS))
        options = ev[ev.index("option = {"): ev.index("after = {")]
        self.assertEqual(
            2,
            options.count("NOT = { covert_code_tier_war = { VAR = iw_burned_type_code } }"),
            "both options must skip the relations hit for war-tier operations",
        )

    def test_both_options_call_the_third_party_blowback_on_the_severe_tier(self):
        ev = _event_1(_text(EVENTS))
        options = ev[ev.index("option = {"): ev.index("after = {")]
        self.assertEqual(2, options.count("covert_exposure_third_party_blowback = yes"))
        self.assertEqual(
            2,
            options.count("covert_code_tier_severe = { VAR = iw_burned_type_code }"),
        )

    def test_after_clears_both_copied_variables(self):
        ev = _event_1(_text(EVENTS))
        after = ev[ev.index("after = {"):]
        self.assertIn("remove_variable = iw_burned_type_code", after)
        self.assertIn("remove_variable = iw_burned_phase", after)
        # Neither removal may sit inside the detected_by_country guard, or a
        # burn whose target has vanished leaves the variable stuck forever.
        guarded = after[: after.index("scope:detected_by_country = {\n\t\t\t\ttrigger_event")]
        self.assertNotIn("remove_variable = iw_burned_type_code", guarded)
        self.assertNotIn("remove_variable = iw_burned_phase", guarded)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_exposure_tiers -v`
Expected: FAIL — `iw_burned_phase` is not in `immediate`.

- [ ] **Step 3: Copy the phase in `immediate`**

In `events/covert_warfare_events.txt`, inside `covert_warfare.1`'s `immediate`, extend the `ROOT = { ... }` block so it copies both variables:

```
			ROOT = {
				set_variable = { name = iw_burned_type_code value = PREV.var:iw_type_code }
				set_variable = { name = iw_burned_phase value = PREV.var:iw_phase }
			}
```

and extend the comment above it with one sentence: the phase is copied for the same reason as the code — the options fire days later and read only country variables.

- [ ] **Step 4: Rewire the Acknowledge option**

Replace the body of the first option (`name = covert_warfare.1.a`) between `custom_tooltip = covert_op_burned_tt` and `ai_chance` with:

```
			custom_tooltip = covert_op_burned_tt
			change_infamy = { value = covert_exposure_infamy_acknowledge }
			if = {
				limit = {
					exists = scope:detected_by_country
					NOT = { covert_code_tier_war = { VAR = iw_burned_type_code } }
				}
				change_relations = {
					country = scope:detected_by_country
					value = covert_exposure_relations_acknowledge
				}
			}
			if = {
				limit = {
					exists = scope:detected_by_country
					covert_code_tier_severe = { VAR = iw_burned_type_code }
				}
				covert_exposure_third_party_blowback = yes
			}
```

- [ ] **Step 5: Rewire the Deny option**

Replace the body of the second option (`name = covert_warfare.1.b`) the same way, keeping the vigilance modifier on the target:

```
			custom_tooltip = covert_op_burned_tt
			change_infamy = { value = covert_exposure_infamy_deny }
			if = {
				limit = {
					exists = scope:detected_by_country
					NOT = { covert_code_tier_war = { VAR = iw_burned_type_code } }
				}
				change_relations = {
					country = scope:detected_by_country
					value = covert_exposure_relations_deny
				}
			}
			if = {
				limit = { exists = scope:detected_by_country }
				scope:detected_by_country = {
					add_modifier = {
						name = covert_op_heightened_vigilance_modifier
						days = normal_modifier_time
						is_decaying = yes
					}
				}
			}
			if = {
				limit = {
					exists = scope:detected_by_country
					covert_code_tier_severe = { VAR = iw_burned_type_code }
				}
				covert_exposure_third_party_blowback = yes
			}
```

- [ ] **Step 6: Clear the phase in `after`**

Add a sibling block immediately after the existing `iw_burned_type_code` removal — **do not modify that block, `test_covert_detection_roll.py` pins its exact text**:

```
		if = {
			limit = { has_variable = iw_burned_phase }
			remove_variable = iw_burned_phase
		}
```

- [ ] **Step 7: Format and run the tests**

```bash
python3 scripts/format_paradox_tabs.py events/covert_warfare_events.txt
python3 -m unittest test_covert_exposure_tiers test_covert_detection_roll -v
```

Expected: PASS, including every slice-1 test.

- [ ] **Step 8: Commit**

```bash
git add events/covert_warfare_events.txt test_covert_exposure_tiers.py
git commit -m "feat(covert): charge exposure by operation tier and phase"
```

---

### Task 4: Name the tier in both events

**Files:**
- Modify: `common/customizable_localization/covert_warfare_custom_loc.txt` (append two entries)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (four tier names)
- Modify: `localization/english/te_events_l_english.yml` (`covert_warfare.1.d`, `covert_warfare.2.d`)
- Test: `test_covert_exposure_tiers.py` (add a class)

**Interfaces:**
- Consumes: the tier triggers (Task 1), `iw_burned_type_code` (Task 3), `iw_last_exposed_type` (already written by `covert_op_burn`).
- Produces: custom loc `covert_burned_tier_name`, `covert_last_exposed_tier_name`.

- [ ] **Step 1: Write the failing test**

Append to `test_covert_exposure_tiers.py`:

```python
class TierNameLocTests(unittest.TestCase):
    def test_both_tier_names_read_the_tier_table(self):
        body = _text(CUSTOM_LOC)
        for entry, var in (
            ("covert_burned_tier_name", "iw_burned_type_code"),
            ("covert_last_exposed_tier_name", "iw_last_exposed_type"),
        ):
            block = _top_level_block(body, "%s = {" % entry)
            for tier in TIER_CODES:
                self.assertIn(
                    "covert_code_tier_%s = { VAR = %s }" % (tier, var),
                    block,
                    "%s must name the %s tier through the tier table" % (entry, tier),
                )
                self.assertIn("localization_key = iw_exposure_tier_%s" % tier, block)
            # No custom loc may re-list codes; that is the tier table's job.
            self.assertNotIn("var:%s = " % var, block)

    def test_tier_name_keys_exist(self):
        loc = (ROOT / "localization/english").rglob("*.yml")
        body = "".join(p.read_text(encoding="utf-8-sig") for p in loc)
        for tier in TIER_CODES:
            self.assertIn("iw_exposure_tier_%s:" % tier, body)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_exposure_tiers -v`
Expected: FAIL on the missing `covert_burned_tier_name = {` block.

- [ ] **Step 3: Add the two custom-loc entries**

Append to `common/customizable_localization/covert_warfare_custom_loc.txt`:

```
# How hostile the world considers the operation covert_warfare.1 is reporting.
# The tier table (covert_code_tier_*) is the only place the codes are listed;
# this just picks the word for it.
covert_burned_tier_name = {
	type = country
	random_valid = no

	text = {
		trigger = { covert_code_tier_mild = { VAR = iw_burned_type_code } }
		localization_key = iw_exposure_tier_mild
	}
	text = {
		trigger = { covert_code_tier_severe = { VAR = iw_burned_type_code } }
		localization_key = iw_exposure_tier_severe
	}
	text = {
		trigger = { covert_code_tier_war = { VAR = iw_burned_type_code } }
		localization_key = iw_exposure_tier_war
	}
	text = {
		trigger = { covert_code_tier_moderate = { VAR = iw_burned_type_code } }
		localization_key = iw_exposure_tier_moderate
	}
	text = {
		localization_key = iw_exposure_tier_moderate
	}
}

# The same word, for the operation our counter-intelligence last exposed.
covert_last_exposed_tier_name = {
	type = country
	random_valid = no

	text = {
		trigger = { covert_code_tier_mild = { VAR = iw_last_exposed_type } }
		localization_key = iw_exposure_tier_mild
	}
	text = {
		trigger = { covert_code_tier_severe = { VAR = iw_last_exposed_type } }
		localization_key = iw_exposure_tier_severe
	}
	text = {
		trigger = { covert_code_tier_war = { VAR = iw_last_exposed_type } }
		localization_key = iw_exposure_tier_war
	}
	text = {
		trigger = { covert_code_tier_moderate = { VAR = iw_last_exposed_type } }
		localization_key = iw_exposure_tier_moderate
	}
	text = {
		localization_key = iw_exposure_tier_moderate
	}
}
```

- [ ] **Step 4: Add the four tier names**

Add to `localization/english/te_miscellaneous_l_english.yml`:

```
 iw_exposure_tier_mild:0 "routine espionage"
 iw_exposure_tier_moderate:0 "interference in their internal affairs"
 iw_exposure_tier_severe:0 "an attempt to bring down their government"
 iw_exposure_tier_war:0 "wartime sabotage"
```

These are noun phrases that read inside a sentence, not headings.

- [ ] **Step 5: Name the tier in both event descriptions**

In `localization/english/te_events_l_english.yml`, replace the two keys (keep everything else in each string):

```
 covert_warfare.1.d:0 "Our intelligence services report a catastrophic security breach. One of our [concept_covert_operations] ([ROOT.GetCountry.GetCustom('covert_burned_type_name')]) has been detected by [SCOPE.sCountry('detected_by_country').GetName]. They will present it to the world as [ROOT.GetCountry.GetCustom('covert_burned_tier_name')]. The operation must be terminated immediately, and the diplomatic fallout will be considerable."
 covert_warfare.2.d:0 "Our counterintelligence services have uncovered evidence of a sustained foreign covert campaign against us — [ROOT.GetCountry.GetCustom('covert_last_exposed_tier_name')], conducted by agents of a power that has so far denied everything. We must decide how to respond."
```

- [ ] **Step 6: Organize loc and run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/customizable_localization/covert_warfare_custom_loc.txt
python3 organize_loc.py
python3 -m unittest test_covert_exposure_tiers test_covert_detection_roll -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add common/customizable_localization/covert_warfare_custom_loc.txt localization/english test_covert_exposure_tiers.py
git commit -m "feat(covert): name the exposure tier in both detection events"
```

---

### Task 5: Show the tier before launch, and mark the influence campaign hostile

**Files:**
- Modify: `localization/english/te_concepts_l_english.yml` (nine `covert_*_action_desc` keys)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (four note keys)
- Modify: `common/diplomatic_actions/covert_operations.txt` (one line)
- Test: `test_covert_exposure_tiers.py` (add a class)

**Interfaces:**
- Consumes: the tier table's assignment of codes to tiers (Task 1), by hand — these are static loc strings, so the mapping is transcribed, and the test below is what keeps it honest.

**Why this is in scope:** without it the graduated system is invisible until the player is caught, and choosing between operations is the decision the tiers exist to inform.

- [ ] **Step 1: Write the failing test**

Append to `test_covert_exposure_tiers.py`:

```python
ACTION_TIER = {
    "election_interference": "moderate",
    "financial_subversion": "moderate",
    "infrastructure_sabotage": "war",
    "comms_disruption": "war",
    "industrial_espionage": "mild",
    "military_espionage": "mild",
    "influence_campaign": "moderate",
    "ideological_subversion": "severe",
    "destabilization": "severe",
}


class PreLaunchTierNoteTests(unittest.TestCase):
    def test_the_hand_written_mapping_matches_the_tier_table(self):
        body = _text(TRIGGERS)
        for op_type, tier in ACTION_TIER.items():
            codes = {int(m) for m in re.findall(r"var:\$VAR\$ = (\d+)", _tier_block(body, tier))}
            self.assertIn(
                CODES[op_type],
                codes,
                "%s is documented as %s but the tier table disagrees" % (op_type, tier),
            )

    def test_every_action_description_shows_its_tier(self):
        loc = "".join(
            p.read_text(encoding="utf-8-sig")
            for p in sorted((ROOT / "localization/english").rglob("*.yml"))
        )
        for op_type, tier in ACTION_TIER.items():
            line = next(
                l for l in loc.splitlines()
                if l.strip().startswith("covert_%s_action_desc:" % op_type)
            )
            self.assertIn(
                "$iw_exposure_tier_%s_note$" % tier,
                line,
                "covert_%s_action_desc must show the %s tier" % (op_type, tier),
            )

    def test_every_covert_action_is_hostile(self):
        body = _text(ACTIONS)
        self.assertEqual(
            len(CODES),
            body.count("is_hostile = yes"),
            "every covert operation must be marked hostile",
        )
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_exposure_tiers -v`
Expected: FAIL — the descriptions carry no note and only eight actions are hostile.

- [ ] **Step 3: Add the four note keys**

Add to `localization/english/te_miscellaneous_l_english.yml`:

```
 iw_exposure_tier_mild_note:0 "\n#lore If this is exposed, the world treats it as routine espionage: little infamy, a modest cooling with the target.#!"
 iw_exposure_tier_moderate_note:0 "\n#lore If this is exposed, the world treats it as interference in another country's internal affairs: real infamy and a serious bilateral breach.#!"
 iw_exposure_tier_severe_note:0 "\n#lore If this is exposed, the world treats it as an attempt to bring down a government: heavy infamy, a severe breach with the target, and every country tied to them cools towards us as well.#!"
 iw_exposure_tier_war_note:0 "\n#lore If this is exposed, the world shrugs: sabotage between belligerents costs a little infamy and nothing else.#!"
```

- [ ] **Step 4: Append the matching note to all nine action descriptions**

In `localization/english/te_concepts_l_english.yml`, append the tier's note reference inside the closing quote of each `covert_<type>_action_desc` value, using the mapping in `ACTION_TIER` above. For example:

```
 covert_destabilization_action_desc:0 "Covertly fund separatist movements and general unrest in a rival nation.$iw_exposure_tier_severe_note$"
```

Do this for all nine. Do not otherwise reword the descriptions.

- [ ] **Step 5: Mark the influence campaign hostile**

In `common/diplomatic_actions/covert_operations.txt`, `covert_influence_campaign_action` (around line 877) is the only covert action without `is_hostile = yes`. Add it in the same position the other eight put it (immediately after the action's `requires_approval`/header lines — match `covert_ideological_subversion_action`'s placement exactly).

- [ ] **Step 6: Organize loc and run the tests**

```bash
python3 organize_loc.py
python3 -m unittest test_covert_exposure_tiers test_covert_detection_roll -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add localization/english common/diplomatic_actions/covert_operations.txt test_covert_exposure_tiers.py
git commit -m "feat(covert): state each operation's exposure tier before launch"
```

---

### Task 6: Reach the severe branch from the console, and document the system

**Files:**
- Modify: `common/scripted_effects/te_debug_covert_effects.txt` (one more plant in `te_debug_covert_seed_phases`)
- Modify: `docs/systems/mod_systems.md` (§ Covert Warfare)
- Test: `test_covert_exposure_tiers.py` (add a class)

**Interfaces:**
- Consumes: `te_debug_covert_plant_op` (unchanged signature, slice 1).

- [ ] **Step 1: Write the failing test**

Append to `test_covert_exposure_tiers.py`:

```python
class DebugHarnessTests(unittest.TestCase):
    def test_the_seed_plants_a_severe_operation(self):
        block = _top_level_block(_text(DEBUG_EFFECTS), "te_debug_covert_seed_phases = {")
        planted = {int(m) for m in re.findall(r"CODE = (\d+)", block)}
        self.assertTrue(
            planted & TIER_CODES["severe"],
            "the seed must plant a severe operation so the third-party "
            "blowback branch is reachable in game",
        )
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_exposure_tiers -v`
Expected: FAIL — the seed plants codes 4, 6 and 5 only.

- [ ] **Step 3: Plant a severe operation**

In `common/scripted_effects/te_debug_covert_effects.txt`, add a fourth `te_debug_covert_plant_op` call to `te_debug_covert_seed_phases`, matching the three existing calls' shape exactly:

```
		te_debug_covert_plant_op = {
			TYPE = destabilization
			ACTION = covert_destabilization_action
			DEFENSE_MOD = country_covert_defense_ideological_add
			CODE = 8
			MONTHS = 14
		}
```

`country_covert_defense_ideological_add` is the modifier the shipping `covert_ops_sync_all` row for `destabilization` passes (`covert_warfare_effects.txt:277`); keep the two in step. Update the effect's comment header so it lists four operations, noting that the destabilization plant is fully operational and severe, which is the worst-case exposure.

- [ ] **Step 4: Document the system**

In `docs/systems/mod_systems.md` § Covert Warfare (starts at line 1533):

1. Replace whatever the section says about detection blowback with the tier × phase table from the top of this plan, stating both options' split and that severe exposures also cost −10 relations with the target's bloc partners and treaty allies.
2. Say that the tier table is the four `covert_code_tier_*` triggers and that adding an operation type means adding its code to exactly one of them.
3. Fix the "unreferenced values" note: `covert_detection_chance_display`, `covert_detection_target_ic_display` and `covert_ops_detected_infamy` have been deleted; `covert_detection_base_display`, `covert_detection_efficiency_pct_display` and `covert_ops_funding_detection_reduction_display` remain and are live.

This file is LF — an ordinary edit is fine. (`docs/systems/journal_entry_systems.md` is the CRLF one; this slice does not touch it.)

- [ ] **Step 5: Format and run the full covert test set**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/te_debug_covert_effects.txt
python3 -m unittest test_covert_exposure_tiers test_covert_detection_roll -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add common/scripted_effects/te_debug_covert_effects.txt docs/systems/mod_systems.md test_covert_exposure_tiers.py
git commit -m "docs(covert): document graduated exposure; plant a severe operation in the harness"
```

---

---

### Task 7: Lower the detection floor to 0.1% a month

**Files:**
- Modify: `common/script_values/covert_warfare_script_values.txt` (one Section 1 constant; one line in `covert_operation_detection_chance`)
- Modify: `localization/english/te_journal_entries_l_english.yml` (one decimal on the per-operation risk)
- Test: `test_covert_exposure_tiers.py` (add a class)

**Why:** with severe exposures now costing up to 6 infamy and −60 relations, a well-funded agency should be able to work a defenceless target almost with impunity — but never with *no* risk. The floor is easy to reach: base risk is 10 and full funding subtracts 19, so a maxed agency is already negative before the target's counterintelligence is added. 1%/month is 11.4% a year; 0.1%/month is 1.2% a year.

**Engine fact this depends on, already checked:** `random = { chance = <fraction> }` really rolls fractions — vanilla's Montenegro raiding journal entry (`common/journal_entries/05_montenegro_je.txt:184-195` in the vanilla tree) passes computed chances of 0.15 and 0.45. Do not re-verify; do not replace the floor with an integer.

- [ ] **Step 1: Write the failing test**

Append to `test_covert_exposure_tiers.py`:

```python
class DetectionFloorTests(unittest.TestCase):
    def test_the_floor_is_a_named_constant_at_a_tenth_of_a_percent(self):
        body = _text(VALUES)
        self.assertIn("covert_ops_detection_floor = 0.1", body)
        block = _top_level_block(body, "covert_operation_detection_chance = {")
        self.assertIn("min = covert_ops_detection_floor", block)
        self.assertNotIn("\n\tmin = 1\n", block)

    def test_the_operation_row_shows_a_decimal(self):
        # At the floor the risk is 0.1%/month. Rendered with |0 that reads as
        # "0%", which tells the player they are safe when they are not.
        loc = _text(ROOT / "localization/english/te_journal_entries_l_english.yml")
        line = next(
            l for l in loc.splitlines()
            if l.strip().startswith("je_iw_op_row_detection:")
        )
        self.assertIn("GetVariableValue('iw_detect')|1", line)
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_exposure_tiers -v`
Expected: FAIL — the constant does not exist and the row still renders `|0`.

- [ ] **Step 3: Add the constant**

In Section 1 of `common/script_values/covert_warfare_script_values.txt`, immediately after the `covert_ops_detection_multi_op_scale` block, add:

```
# The lowest monthly detection risk any operation can carry. Full funding
# subtracts more than the base risk on its own, so a well-funded agency
# against a target with no counterintelligence sits exactly here: 0.1%/month
# is 1.2% a year, which is "almost with impunity" without ever being "safe".
# Fractions are real rolls, not a silent zero — vanilla's Montenegro raiding
# journal entry passes computed chances of 0.15 and 0.45 to `random`.
covert_ops_detection_floor = 0.1
```

- [ ] **Step 4: Use it as the floor**

In `covert_operation_detection_chance`, replace the line `	min = 1` (the one directly above `	max = 50`, at one tab of indentation — there are other `min = 1` lines in the file at deeper indentation, leave those alone) with:

```
	min = covert_ops_detection_floor
```

- [ ] **Step 5: Show one decimal on the operation row**

In `localization/english/te_journal_entries_l_english.yml`, in `je_iw_op_row_detection`, change `[ScriptContainer.GetVariableValue('iw_detect')|0]` to `[ScriptContainer.GetVariableValue('iw_detect')|1]`. Change nothing else in that string — `iw_tgt_ic` and `iw_tgt_td` stay at `|0`.

- [ ] **Step 6: Format and run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/covert_warfare_script_values.txt
python3 -m unittest test_covert_exposure_tiers test_covert_detection_roll -v
```

- [ ] **Step 7: Commit**

```bash
git add common/script_values/covert_warfare_script_values.txt localization/english/te_journal_entries_l_english.yml test_covert_exposure_tiers.py
git commit -m "feat(covert): drop the detection floor to 0.1% a month"
```

---

### Task 8: Let the wartime operations start during a diplomatic play

**Files:**
- Modify: `common/diplomatic_actions/covert_operations.txt` (`covert_infrastructure_sabotage_action` and `covert_comms_disruption_action`, three gates each)
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (one new trigger)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (rename and reword one tooltip key)
- Modify: `events/covert_warfare_events.txt` (`immediate` copies the war state; `after` clears it; both options' guards)
- Modify: `common/script_values/covert_warfare_script_values.txt` (two constants; the war branch of both base values)
- Modify: `docs/systems/mod_systems.md`
- Test: `test_covert_exposure_tiers.py` (add two classes)

**Why:** sabotage and comms disruption are gated on already being at war, so the spies can only start preparing once the shooting has begun. If a diplomatic play against the target is under way, that preparation is exactly what an intelligence service would be doing.

**The consequence that ships with it.** The war tier's blowback was written for operations that only exist during a war. Once they can start during a play, *when* you are caught matters more than the operation type does:

- **Caught once the war has started: nothing at all.** No infamy, no relations. Blowing up a bridge does not make the international community angrier at a country that is already at war — it is just war. Today's war tier charges 1 infamy for this; that goes to zero.
- **Caught during the play, before the war: the worst look there is.** Sabotage in the run-up reads as manufacturing the war, so it carries **severe-tier infamy** (base 4, the same as bankrolling a coup) and the moderate relations hit (base −20).

Third parties are not notified either way: that branch stays keyed to the severe *tier*, and the international reaction to pre-war sabotage is carried by the infamy.

Because the war can begin between the event firing and the player clicking, the war state is copied onto the country in `immediate` as `iw_burned_at_war`, the same pattern the type code and phase already use, and one scripted trigger — `covert_exposure_is_costless` — is the single place that answers "is this the free case", read by both script values and both options.

- [ ] **Step 1: Write the failing test**

Append to `test_covert_exposure_tiers.py`:

```python
WAR_ACTIONS = ("covert_infrastructure_sabotage_action", "covert_comms_disruption_action")


class DiplomaticPlayGateTests(unittest.TestCase):
    def test_both_wartime_actions_accept_a_play_in_all_three_gates(self):
        body = _text(ACTIONS)
        for action in WAR_ACTIONS:
            block = _top_level_block(body, "%s = {" % action)
            self.assertEqual(
                3,
                block.count("is_diplomatic_play_enemy_of = scope:target_country"),
                "%s must accept a diplomatic play in `possible`, in "
                "`requirement_to_maintain` and in the AI's `will_propose`" % action,
            )
            self.assertEqual(
                3,
                block.count("has_war_with = scope:target_country"),
                "%s must still accept an actual war in all three gates" % action,
            )
            # The old blanket "are you at war with anyone" clause is gone.
            self.assertNotIn("is_at_war = yes", block)

    def test_the_gate_tooltip_was_renamed_to_match_what_it_now_says(self):
        body = _text(ACTIONS)
        self.assertNotIn("iw_at_war_tt", body)
        self.assertEqual(4, body.count("iw_at_war_or_play_tt"))
        loc = _text(ROOT / "localization/english/te_miscellaneous_l_english.yml")
        self.assertIn("iw_at_war_or_play_tt:", loc)
        self.assertNotIn("iw_at_war_tt:", loc)


class WartimeExposureTests(unittest.TestCase):
    def test_the_costless_case_is_one_trigger(self):
        block = _top_level_block(_text(TRIGGERS), "covert_exposure_is_costless = {")
        self.assertIn("covert_code_tier_war = { VAR = iw_burned_type_code }", block)
        self.assertIn("has_variable = iw_burned_at_war", block)
        self.assertIn("var:iw_burned_at_war = 1", block)

    def test_immediate_copies_the_war_state(self):
        ev = _event_1(_text(EVENTS))
        immediate = ev[ev.index("immediate = {"): ev.index("option = {")]
        self.assertIn("name = iw_burned_at_war", immediate)
        self.assertIn("has_war_with = scope:detected_by_country", immediate)

    def test_after_clears_the_war_state(self):
        ev = _event_1(_text(EVENTS))
        after = ev[ev.index("after = {"):]
        self.assertIn("remove_variable = iw_burned_at_war", after)
        guarded = after[: after.index("scope:detected_by_country = {\n\t\t\t\ttrigger_event")]
        self.assertNotIn("remove_variable = iw_burned_at_war", guarded)

    def test_wartime_sabotage_during_the_war_costs_nothing(self):
        body = _text(VALUES)
        self.assertIn("covert_exposure_infamy_war = 0", body)
        for name in ("covert_exposure_infamy_base", "covert_exposure_relations_base"):
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("covert_exposure_is_costless = yes", block)

    def test_wartime_sabotage_before_the_war_is_charged_as_severe(self):
        body = _text(VALUES)
        # Severe-tier infamy, moderate relations -- stated as their own named
        # constants so the pre-war case can be retuned without touching either
        # tier it borrows its magnitude from.
        self.assertIn("covert_exposure_infamy_war_prewar = 4", body)
        self.assertIn("covert_exposure_relations_war_prewar = -20", body)
        self.assertIn(
            "covert_exposure_infamy_war_prewar",
            _top_level_block(body, "covert_exposure_infamy_base = {"),
        )
        self.assertIn(
            "covert_exposure_relations_war_prewar",
            _top_level_block(body, "covert_exposure_relations_base = {"),
        )

    def test_both_options_skip_infamy_and_relations_in_the_costless_case(self):
        ev = _event_1(_text(EVENTS))
        options = ev[ev.index("option = {"): ev.index("after = {")]
        # Once per option for infamy, once per option for relations: a zero
        # would otherwise render as "+0" / "-0" in the option tooltip.
        self.assertEqual(4, options.count("NOT = { covert_exposure_is_costless = yes }"))
```

- [ ] **Step 2: Run it to make sure it fails**

Run: `python3 -m unittest test_covert_exposure_tiers -v`
Expected: FAIL — the actions still gate on war alone and the trigger does not exist.

- [ ] **Step 3: Relax both actions' `possible` gate**

In `common/diplomatic_actions/covert_operations.txt`, in **both** `covert_infrastructure_sabotage_action` and `covert_comms_disruption_action`, replace this pair of clauses in `possible`:

```
		custom_tooltip = {
			text = iw_at_war_tt
			is_at_war = yes
		}
		has_war_with = scope:target_country
```

with:

```
		custom_tooltip = {
			text = iw_at_war_or_play_tt
			OR = {
				has_war_with = scope:target_country
				is_diplomatic_play_enemy_of = scope:target_country
			}
		}
```

The blanket `is_at_war = yes` goes: it was redundant once the gate names the target, and it would have blocked the play case.

- [ ] **Step 4: Relax both actions' `requirement_to_maintain`**

In both actions, replace:

```
				custom_tooltip = {
					text = iw_at_war_tt
					has_war_with = scope:target_country
				}
```

with:

```
				custom_tooltip = {
					text = iw_at_war_or_play_tt
					OR = {
						has_war_with = scope:target_country
						is_diplomatic_play_enemy_of = scope:target_country
					}
				}
```

A play that resolves without war therefore stands the operation down, which is the intended fiction.

- [ ] **Step 5: Relax both actions' AI gate**

In both actions' `ai` block, the bare `has_war_with = scope:target_country` inside `will_propose` becomes:

```
			OR = {
				has_war_with = scope:target_country
				is_diplomatic_play_enemy_of = scope:target_country
			}
```

- [ ] **Step 6: Reword the tooltip key**

In `localization/english/te_miscellaneous_l_english.yml`, replace the `iw_at_war_tt` entry with:

```
 iw_at_war_or_play_tt:0 "Must be at war with them, or in a [concept_diplomatic_play] against them (wartime operation)"
```

- [ ] **Step 7: Add the costless-case trigger**

Append to `common/scripted_triggers/covert_warfare_triggers.txt`, after the tier table:

```
# A wartime operation caught once the war has actually started costs nothing:
# no infamy, no relations. Sabotage does not make the world angrier at a
# country that is already fighting. Caught during the diplomatic play that
# precedes the war it is the opposite — see covert_exposure_infamy_war_prewar.
#
# THE one place that question is answered: both blowback script values and
# both options of covert_warfare.1 read this.
# Scope: country (the operator, while covert_warfare.1 is open)
covert_exposure_is_costless = {
	covert_code_tier_war = { VAR = iw_burned_type_code }
	has_variable = iw_burned_at_war
	var:iw_burned_at_war = 1
}
```

- [ ] **Step 8: Retune the war tier's constants**

In Section 1 of `common/script_values/covert_warfare_script_values.txt`, change `covert_exposure_infamy_war = 1` to `0` and add the two pre-war constants beside it:

```
covert_exposure_infamy_war = 0

# Caught in the run-up instead of during the war: sabotage before the shooting
# reads as manufacturing the war, so it is charged at the severe tier's infamy
# and the moderate tier's relations. Named separately from those tiers so this
# case can be retuned without moving either of them.
covert_exposure_infamy_war_prewar = 4
covert_exposure_relations_war_prewar = -20
```

- [ ] **Step 9: Branch both base values on the costless trigger**

In `covert_exposure_infamy_base`, replace the war branch:

```
	else_if = {
		limit = { covert_code_tier_war = { VAR = iw_burned_type_code } }
		add = covert_exposure_infamy_war
	}
```

with:

```
	else_if = {
		limit = { covert_exposure_is_costless = yes }
		add = covert_exposure_infamy_war
	}
	else_if = {
		limit = { covert_code_tier_war = { VAR = iw_burned_type_code } }
		add = covert_exposure_infamy_war_prewar
	}
```

In `covert_exposure_relations_base`, replace the war branch:

```
	if = {
		limit = { covert_code_tier_war = { VAR = iw_burned_type_code } }
		add = 0
	}
```

with:

```
	if = {
		limit = { covert_exposure_is_costless = yes }
		add = 0
	}
	else_if = {
		limit = { covert_code_tier_war = { VAR = iw_burned_type_code } }
		add = covert_exposure_relations_war_prewar
	}
```

Leave the mild / severe / else branches of both values exactly as they are.

- [ ] **Step 10: Copy the war state in `immediate`**

In `events/covert_warfare_events.txt`, inside `covert_warfare.1`'s `immediate`, add to the existing `ROOT = { ... }` block, after the two `set_variable` lines:

```
				if = {
					limit = { has_war_with = scope:detected_by_country }
					set_variable = { name = iw_burned_at_war value = 1 }
				}
				else = {
					set_variable = { name = iw_burned_at_war value = 0 }
				}
```

`scope:detected_by_country` is saved on the line above, so it resolves here. Extend the block comment: the war state is copied for the same reason as the code and the phase, and additionally because the war may begin between the event firing and the player clicking.

- [ ] **Step 11: Clear it in `after`**

Add a third sibling removal block alongside the two already there — do not edit the existing ones:

```
		if = {
			limit = { has_variable = iw_burned_at_war }
			remove_variable = iw_burned_at_war
		}
```

- [ ] **Step 12: Guard both costs in both options**

In each option of `covert_warfare.1`, the infamy call is currently unconditional and the relations call is guarded on `NOT = { covert_code_tier_war = ... }`. Both now hang off the same question. In **both** options, replace:

```
			change_infamy = { value = covert_exposure_infamy_acknowledge }
```

(and the `_deny` equivalent in the other option) with:

```
			if = {
				limit = { NOT = { covert_exposure_is_costless = yes } }
				change_infamy = { value = covert_exposure_infamy_acknowledge }
			}
```

and replace the relations guard's tier clause:

```
					NOT = { covert_code_tier_war = { VAR = iw_burned_type_code } }
```

with:

```
					NOT = { covert_exposure_is_costless = yes }
```

A war-tier burn during the war therefore emits neither effect, so neither renders as "+0" or "-0"; a war-tier burn during a play emits both.

- [ ] **Step 13: Correct the war tier's pre-launch note and tier name**

Task 5 wrote `iw_exposure_tier_war_note` when the war tier cost a flat 1 infamy either way. This task
makes that text **false**, so it has to move with the mechanic. In
`localization/english/te_miscellaneous_l_english.yml`, replace it with a note that states both cases:

```
 iw_exposure_tier_war_note:0 "\n#lore If this is exposed once the war has started, the world shrugs — sabotage between belligerents costs nothing at all. Exposed during the run-up, it reads as manufacturing the war, and costs as much infamy as an attempt to bring down a government.#!"
```

That also closes a Minor from Task 5's review: the other three notes follow "the world treats it as
`<characterization>`: `<consequence>`" while the old war note never named what the world was
reacting to.

Leave `iw_exposure_tier_war` (the short noun phrase "wartime sabotage", used inside both event
descriptions) as it is — it names the operation, not its price, and is still accurate.

Re-run the Task 5 drift test after this edit: `python3 -m unittest
test_covert_exposure_tiers.PreLaunchTierNoteTests -v`. It must stay green, since the key name is
unchanged and the nine descriptions still reference it.

- [ ] **Step 14: Format, organize loc, run the tests**

```bash
python3 scripts/format_paradox_tabs.py common/diplomatic_actions/covert_operations.txt events/covert_warfare_events.txt common/script_values/covert_warfare_script_values.txt common/scripted_triggers/covert_warfare_triggers.txt
python3 organize_loc.py
python3 -m unittest test_covert_exposure_tiers test_covert_detection_roll -v
```

Then the full suite once.

- [ ] **Step 15: Document both changes**

In `docs/systems/mod_systems.md` § Covert Warfare, add: the detection floor is now `covert_ops_detection_floor` (0.1%/month, reachable at high funding against a weak target, which is why the operation row shows one decimal); the two wartime operations may be started and maintained while a diplomatic play against the target is running, and stand down if that play ends without war; and the war tier's blowback now turns on *when* the operation was caught — nothing at all once the war has started, severe-tier infamy plus a moderate relations hit if it was caught during the run-up.

- [ ] **Step 16: Commit**

```bash
git add common/diplomatic_actions/covert_operations.txt common/scripted_triggers/covert_warfare_triggers.txt events/covert_warfare_events.txt common/script_values/covert_warfare_script_values.txt localization/english docs/systems/mod_systems.md test_covert_exposure_tiers.py
git commit -m "feat(covert): let sabotage start during a diplomatic play; price it by when it is caught"
```

---

### Task 9: Make the structural tests assert nesting, not text position

**Files:**
- Modify: `test_covert_exposure_tiers.py` (helpers + tighten the guard-placement assertions)

**Why:** two independent reviews flagged the same gap. Every guard-placement assertion in this file
checks that a string appears *somewhere* inside a text slice — so a guard attached to the wrong `if`,
or a `remove_variable` nested inside the `exists = scope:detected_by_country` block but textually
after the anchor the test slices on, would still pass. The placements are all correct today
(verified by direct code inspection during review); this task stops them from silently rotting. It
is scheduled as its own task, rather than folded into Tasks 1-3, because the weakness spans
assertions written across all of them and is worth fixing once, coherently.

**No production code changes.** If a tightened assertion fails, that is a real defect — stop and
report it rather than loosening the assertion to make it pass.

**Interfaces:**
- Consumes: everything Tasks 1-8 wrote. This task adds no new behaviour.

- [ ] **Step 1: Add brace-matching helpers**

Add these next to the existing `_top_level_block` helper in `test_covert_exposure_tiers.py`:

```python
def _block_span(body, from_index):
    """(start, end) of the brace-balanced block whose opening `{` is at or
    after from_index; end is the index just past the matching `}`.

    Counts braces instead of trusting indentation, so it is correct even for
    a block that a future edit re-indents or collapses.
    """
    open_at = body.index("{", from_index)
    depth = 0
    for i in range(open_at, len(body)):
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
            if depth == 0:
                return from_index, i + 1
    raise AssertionError("unbalanced braces from index %d" % from_index)


def _innermost_enclosing(body, needle, opener):
    """The text of the innermost `opener { ... }` block that contains needle.

    This is what lets a test say "the war-tier exclusion is in the limit of
    the `if` that guards THIS effect", rather than "the string appears
    somewhere nearby".
    """
    target = body.index(needle)
    best = None
    pos = 0
    while True:
        at = body.find(opener, pos)
        if at == -1 or at > target:
            break
        start, end = _block_span(body, at)
        if start <= target < end and (best is None or start > best[0]):
            best = (start, end)
        pos = at + 1
    if best is None:
        raise AssertionError("no %r block encloses %r" % (opener, needle))
    return body[best[0]:best[1]]


def _limit_of(block):
    """The `limit = { ... }` sub-block of a block, brace-balanced."""
    start, end = _block_span(block, block.index("limit = {"))
    return block[start:end]


def _is_outside(container, body, needle):
    """True when needle's position in body falls outside container's span."""
    at = body.index(needle)
    start = body.index(container)
    return not (start <= at < start + len(container))
```

- [ ] **Step 2: Prove the helpers work before relying on them**

Add a test class that pins the helpers themselves — they are now load-bearing, so a bug in
`_block_span` would silently weaken every assertion built on it:

```python
class HelperTests(unittest.TestCase):
    SAMPLE = (
        "outer = {\n"
        "\tif = {\n"
        "\t\tlimit = { a = 1 }\n"
        "\t\teffect_one = yes\n"
        "\t}\n"
        "\teffect_two = yes\n"
        "}\n"
    )

    def test_block_span_stops_at_the_matching_brace(self):
        start, end = _block_span(self.SAMPLE, self.SAMPLE.index("if = {"))
        self.assertEqual("effect_one = yes\n\t}", self.SAMPLE[start:end][-20:])
        self.assertNotIn("effect_two", self.SAMPLE[start:end])

    def test_innermost_enclosing_picks_the_inner_block(self):
        block = _innermost_enclosing(self.SAMPLE, "effect_one = yes", "if = {")
        self.assertIn("limit = { a = 1 }", block)
        self.assertNotIn("effect_two", block)

    def test_innermost_enclosing_raises_when_nothing_encloses(self):
        with self.assertRaises(AssertionError):
            _innermost_enclosing(self.SAMPLE, "effect_two = yes", "if = {")

    def test_limit_of_returns_only_the_limit(self):
        block = _innermost_enclosing(self.SAMPLE, "effect_one = yes", "if = {")
        self.assertEqual("limit = { a = 1 }", _limit_of(block))
```

- [ ] **Step 3: Run the helper tests**

Run: `python3 -m unittest test_covert_exposure_tiers.HelperTests -v`
Expected: PASS (4 tests). If any fails, fix the helper before going further.

- [ ] **Step 4: Tighten every guard-placement assertion**

Rewrite the assertions below to use the helpers. Keep each test's name and intent; change only
*how* it checks. Leave alone the assertions that are genuinely membership questions (that a literal
no longer appears, that a key exists, that the tier codes partition) — those are the right tool
already.

1. **`after` clears the variables outside the target guard.** Replace the anchor-slicing in
   `test_after_clears_both_copied_variables` (and the `iw_burned_at_war` equivalent from Task 8) with:
   take the `after` block, find the innermost `if = {` enclosing
   `trigger_event = { id = covert_warfare.2 }` — that is the guarded block — and assert each
   `remove_variable = iw_burned_*` call lies outside its brace-balanced span, using `_is_outside`.

2. **Each option's relations call carries the right guard.** For each of
   `covert_exposure_relations_acknowledge` and `covert_exposure_relations_deny`: take the innermost
   `if = {` enclosing that value, take `_limit_of` it, and assert that limit contains both
   `exists = scope:detected_by_country` and the war-tier exclusion — including, after Task 8, the
   `var:iw_burned_at_war = 1` clause. Assert the limit does **not** contain
   `covert_code_tier_severe`, which would mean the guards had been swapped.

3. **Each third-party call carries the severe guard.** For each occurrence of
   `covert_exposure_third_party_blowback = yes`: take the innermost enclosing `if = {`, take
   `_limit_of` it, assert it contains `covert_code_tier_severe` and **not** `covert_code_tier_war`.
   Iterate over both occurrences rather than checking only the first.

4. **The bloc guard applies to the target, not the iterated country.** In
   `test_bloc_audience_requires_the_target_to_have_a_bloc`, assert that `is_in_power_bloc = yes`
   sits inside the innermost `scope:detected_by_country = {` block — that is the whole point of the
   guard, and the current assertion would pass if it were applied to `this`.

5. **`immediate` writes the variables on the country.** Assert each
   `set_variable = { name = iw_burned_* ... }` in `covert_warfare.1`'s `immediate` lies inside the
   innermost `ROOT = {` block, not merely somewhere in `immediate`.

- [ ] **Step 5: Run the covert tests**

Run: `python3 -m unittest test_covert_exposure_tiers test_covert_detection_roll -v`
Expected: PASS. **If a tightened assertion fails, the production code has a real placement bug —
report it as DONE_WITH_CONCERNS with the specifics rather than weakening the test.**

- [ ] **Step 6: Prove the tightened tests actually bite**

For one of them — the relations guard is the clearest — temporarily move the war-tier exclusion from
the relations `if` to the third-party `if` in `events/covert_warfare_events.txt`, re-run that single
test, and confirm it now FAILS. Then `git checkout -- events/covert_warfare_events.txt` to restore.
Record the failing output in your report: this is the evidence that the fix is real rather than
cosmetic. Do not commit the temporary change.

- [ ] **Step 7: Run the full suite and commit**

```bash
python3 -m unittest discover -s . -p 'test_*.py'
git add test_covert_exposure_tiers.py
git commit -m "test(covert): assert guard nesting by brace matching, not text position"
```

---

## Verification (controller, after Task 9)

- `python3 -m unittest discover -s . -p 'test_*.py'` from the main checkout — whole suite green.
- `ruff check .`, `python3 scripts/format_paradox_tabs.py --check` on the changed `.txt`, `python3 scripts/analysis/check_localization_files.py`.
- `curl -X POST "http://localhost:8950/reload?mod_only=true&audits_only=true"` — `warnings` empty, `parse_failures` empty. Check `docs/engine/loc_coverage_report.md` for the new keys and `docs/engine/loc_render_report.md` for the new custom loc.
- In game: `event te_debug_covert.2` option a plants four operations including a fully-operational destabilization; option b forces a detection. Confirm the event names the operation and the tier, that the option tooltips preview the infamy, the relations hit and (on the severe one) the third-party line, and that a bloc partner of the target actually loses relations.
- PR body: the full tier × phase × option table, and the before/after against today's flat +2/+1 and −15/−30.
