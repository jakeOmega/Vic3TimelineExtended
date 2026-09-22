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

## Verification (controller, after Task 6)

- `python3 -m unittest discover -s . -p 'test_*.py'` from the main checkout — whole suite green.
- `ruff check .`, `python3 scripts/format_paradox_tabs.py --check` on the changed `.txt`, `python3 scripts/analysis/check_localization_files.py`.
- `curl -X POST "http://localhost:8950/reload?mod_only=true&audits_only=true"` — `warnings` empty, `parse_failures` empty. Check `docs/engine/loc_coverage_report.md` for the new keys and `docs/engine/loc_render_report.md` for the new custom loc.
- In game: `event te_debug_covert.2` option a plants four operations including a fully-operational destabilization; option b forces a detection. Confirm the event names the operation and the tier, that the option tooltips preview the infamy, the relations hit and (on the severe one) the third-party line, and that a bloc partner of the target actually loses relations.
- PR body: the full tier × phase × option table, and the before/after against today's flat +2/+1 and −15/−30.
