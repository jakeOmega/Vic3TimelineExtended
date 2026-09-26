# Nuclear Umbrella, Recessed Readiness, Automatic Retaliation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship owner items 4 and 7 — subjects under their armed overlord's nuclear umbrella (withdrawable by a liberty-desire pact), Recessed readiness (level 0), and Automatic Retaliation (authority 4) — as a play-testable PR into `main`.

**Architecture:** Paradox script only, on top of the existing posture/crisis/guarantee code. New *states* are new values of the existing variables (`nd_readiness = 0`, `nd_authority = 4`); coverage by umbrella is folded into the existing guarantee triggers so every reader follows. Static consistency tests in `test_nuclear_deterrence.py` pin each wiring decision (this repo's way to "test" engine script).

**Tech Stack:** Victoria 3 Clausewitz script (`common/`, `events/`, `gui/`, `localization/`), Python 3 `unittest` static tests, the repo's audits.

**Spec:** `docs/superpowers/specs/2026-09-25-nuclear-umbrella-recessed-dead-hand-design.md`

**Worktree / branch:** `~/src/vic3te-nuclear-home`, branch `nuclear-umbrella-deadhand` (off `origin/main` `b84eae02`). Never `git commit -a`; stage by path. Test runs in the worktree use the dummy env: `export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent` only for the suite; the nuclear test file needs none.

## Global Constraints

- Every `var:nd_*` read in a trigger is guarded by `has_variable` (triggers file header).
- Never pass `PREV` or a bare `var:` as a scripted-trigger/effect parameter; save a (temporary) scope first.
- Option/tooltip previews do not run effects: anything shown reads only scopes that already exist; saved scopes made inside the effect are absent in the preview. Launch/strike bodies are fenced (`save_scope_as = X` then `limit = { exists = scope:X }`) or hidden.
- Every visible `set_variable`/`change_variable` in an option sits inside a `custom_tooltip = { text = … }` naming it (`silent_variable_audit`).
- Loc: `#v`/`#R`/`#G`/`#b … #!`, never `[b]`; explanatory, causal wording; `$KEY$` references for tech names as siblings do.
- Tabs for indentation in `.txt`/`.gui`; UTF-8 **with BOM** on every `.txt`, `.gui` and `.yml` touched or created.
- `docs/systems/journal_entry_systems.md` is CRLF — edit with the Edit tool and confirm `grep -c $'\r$'` vs `wc -l` afterwards.
- Recessed carries **no** readiness static modifier (the `nd_readiness_mod_on` tracker uses 0 for "none").
- Numbers (verbatim from the spec): withdrawal +10 liberty desire once, −20 relations, +0.10/week while withdrawn; abandoning a subject +10 liberty desire; Recessed custody 0.1 units/warhead, incident base 0.5 ‰, danger part −8, pressure part −10, Restraint +1 / Officers −1 / Militarists −1; Automatic Retaliation needs `radar` + `ICBMs` + `mainframe_computers`, +3 upkeep units, full answer = 3 warheads (fewer if fewer), cooldown 6 months per attacker, AI adopts at 25 % per review.

## Review Focus

1. **A Recessed country struck while a stand-down lock holds** — the assemble option must still raise it to Routine (the lock holds readiness *at or below* Routine). Pinned in Task 2 (`nd_assemble_for_retaliation` sets the target directly, and `nd_can_set_readiness` lets Routine through a lock via `LOCK_OK`).
2. **A stand-down or concession applied to a Recessed country** must not raise it to Routine. Pinned in Task 1 (static test on both sites).
3. **Two Automatic Retaliation countries striking each other** must not loop: only `.1` fires automatically, never `.11`, and the per-attacker cooldown gates a second automatic answer. Pinned in Task 3 (static test that `.11` has no automatic option and that `.1`'s automatic option reads the cooldown).
4. **An overlord that also holds a `nuclear_guarantee` article to its own subject** (signed before subjugation) must be asked once, not twice. Pinned in Task 4 (static test that each umbrella sibling branch excludes a treaty-guarantor).
5. **A guarantor that cannot actually enter the war** (truce, engine refusal) must not strike a country it is not at war with. Pinned in Task 6 (the strike runs from hidden `nuclear_crisis.22`, whose body requires `has_war_with`; static test).

---

### Task 1: Recessed readiness — the level, its costs, odds, crisis sites, domestic terms, AI, panel row

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (READINESS AND AUTHORITY block; `nd_can_set_readiness`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_set_readiness_target_*`, `nd_set_readiness_target`, `nd_ai_review_posture` readiness block, `nd_monthly_update` AI block)
- Modify: `common/script_values/nuclear_deterrence_values.txt` (upkeep units, `nd_incident_permille`, `nd_yp_*`, `nd_yield_pressure_value`, `nd_ig_term_readiness_value`, `nd_upkeep_weekly_at_readiness_*`)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (dispute-5 resolution ~733, concession ~1339, counter/hold ~1666, `nd_standdown_one_side` ~1615, `nd_crisis_refresh_figures`, `nd_crisis_clear_figures`)
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` (op 20; LOCK_OK on 20–23; `nd_crisis_pressure_breakdown_sgui`)
- Modify: `common/customizable_localization/nuclear_deterrence_custom_loc.txt` (`nd_readiness_name`, `nd_readiness_moving`)
- Modify: `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` (Recessed row above Routine; header op table)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (new/changed `nd_` keys)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Produces: triggers `nd_readiness_recessed`, `nd_forces_assembled`; effect `nd_set_readiness_target_0`; `nd_can_set_readiness = { R = <0-3> LOCK_OK = yes|no }`; values `nd_upkeep_units_custody`, `nd_upkeep_units_fixed`, `nd_upkeep_weekly_at_readiness_0`, `nd_yp_recessed_value`; stored crisis part `nd_yp_recessed`; loc `nd_tt_forces_assembled`.

- [ ] **Step 1: Write the failing tests** (append to `test_nuclear_deterrence.py`; add `"nd_yp_recessed"` to `PRESSURE_PARTS` right after `"nd_yp_alert"`; change the readiness family in `test_custom_tooltip_keys` to `range(0, 4)`)

```python
class TestRecessed(unittest.TestCase):
    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(EFFECTS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.values = strip_comments(read(VALUES))

    def test_triggers_exist(self):
        for name in ("nd_readiness_recessed", "nd_forces_assembled"):
            self.assertRegex(self.triggers, rf"(?m)^{name} = \{{")

    def test_standdowns_never_raise_a_recessed_country(self):
        # A stand-down sets the target to Routine only when it is above Routine.
        self.assertIn("var:nd_readiness_target > 1", block(self.crisis, "nd_standdown_one_side"))
        concession = self.crisis[self.crisis.index("nd_crisis_programme_freeze"):]
        concession = concession[:concession.index("nd_readiness_lock_months_value")]
        self.assertIn("var:nd_readiness_target > 1", concession)

    def test_stood_down_alert_includes_recessed(self):
        self.assertIn("var:nd_readiness_target <= 1", self.crisis)
        self.assertNotRegex(self.crisis, r"var:nd_readiness_target = 1\b")

    def test_recessed_has_no_readiness_modifier(self):
        self.assertNotIn("nd_readiness_mod_0", read(MODIFIERS))
        self.assertNotIn("nd_readiness_mod_0", self.effects)

    def test_every_readiness_level_has_upkeep_and_a_row(self):
        for r in range(0, 4):
            self.assertRegex(self.values, rf"(?m)^nd_upkeep_weekly_at_readiness_{r} = \{{")
            self.assertRegex(self.effects, rf"(?m)^nd_set_readiness_target_{r} = \{{")
        self.assertIn(20, gui_ops(read(GUI), "nd_posture_sgui"))

    def test_lock_lets_routine_through(self):
        sg = strip_comments(read(SGUIS))
        for op, ok in ((20, "yes"), (21, "yes"), (22, "no"), (23, "no")):
            r = op - 20
            self.assertIn(f"nd_can_set_readiness = {{ R = {r} LOCK_OK = {ok} }}", sg)
        self.assertIn("always = $LOCK_OK$", block(self.triggers, "nd_can_set_readiness"))
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m unittest test_nuclear_deterrence -v 2>&1 | tail -30`
Expected: FAIL/ERROR in `TestRecessed.*`, `TestCrisisFigures.*` (new part), `test_custom_tooltip_keys` (`nd_tt_readiness_target_0`).

- [ ] **Step 3: Triggers** — after `nd_readiness_high_alert`:

```
# Recessed (spec 2026-09-25 §2): warheads stored apart from their delivery
# systems. Level 0, below Routine.
nd_readiness_recessed = {
	has_variable = nd_readiness
	var:nd_readiness = 0
}

# Are our warheads mated to their delivery systems? Every launch needs it
# (spec 2026-09-25 §2.3). A country that never set a readiness is at
# Routine, the default, so it is assembled.
nd_forces_assembled = {
	OR = {
		NOT = { has_variable = nd_readiness }
		var:nd_readiness >= 1
	}
}
```

`nd_can_set_readiness`: replace the lock tooltip's OR with

```
	# An agreed or conceded stand-down holds readiness at Routine or below:
	# lowering, and returning to Routine from Recessed (LOCK_OK), are never
	# blocked.
	custom_tooltip = {
		text = nd_tt_readiness_locked
		OR = {
			nd_readiness_locked = no
			var:nd_readiness_target > $R$
			always = $LOCK_OK$
		}
	}
```

- [ ] **Step 4: Effects** — wrappers and the direction-aware stand-down line:

```
nd_set_readiness_target_0 = { nd_set_readiness_target = { R = 0 STANDDOWN = yes } }
nd_set_readiness_target_1 = { nd_set_readiness_target = { R = 1 STANDDOWN = yes } }
```

and in `nd_set_readiness_target` the stand-down tooltip gains `var:nd_readiness_target > $R$` in its limit (the preview reads the current target, so a raise from Recessed to Routine is not called a stand-down):

```
	if = {
		limit = {
			always = $STANDDOWN$
			nd_in_crisis = yes
			var:nd_readiness_target > $R$
		}
		custom_tooltip = nd_tt_standdown_signal
	}
```

(The `custom_tooltip = { text … set_variable … }` above it runs first in the real run, but this line only matters in the preview.)

AI review readiness block — replace the final `else = { … target 1 }` with:

```
		# Recessed: at peace, nothing to deter, and a reason to save the money
		# or the risk (spec §2.5).
		else_if = {
			limit = {
				is_at_war = no
				nd_in_crisis = no
				nd_has_plausible_attacker = no
				nd_regime_is_militarist = no
				OR = {
					ruler_is_cautious = yes
					nd_doctrine_nfu = yes
					in_default = yes
				}
			}
			if = {
				limit = { NOT = { var:nd_readiness_target = 0 } }
				nd_set_readiness_target_0 = yes
			}
		}
		else = {
			if = {
				limit = { NOT = { var:nd_readiness_target = 1 } }
				nd_set_readiness_target_1 = yes
			}
		}
```

`nd_monthly_update`, inside the `is_ai = yes` block before the six-month counter:

```
			# A recessed AI that finds itself at war or in a crisis mates its
			# warheads at once, not at its next review (spec §2.5).
			if = {
				limit = {
					var:nd_readiness_target = 0
					OR = {
						is_at_war = yes
						nd_in_crisis = yes
					}
				}
				nd_set_readiness_target_1 = yes
			}
```

- [ ] **Step 5: Values** — upkeep split so every level's preview is exact:

```
nd_upkeep_units_custody = {
	value = nd_stockpile_capped
	multiply = 0.2
}

# Custody at Recessed: warheads in storage cost half to keep.
nd_upkeep_units_custody_recessed = {
	value = nd_upkeep_units_custody
	multiply = 0.5
}

# What does not depend on readiness: safeguards, hardening, and an Automatic
# Retaliation system (Task 3 adds its line).
nd_upkeep_units_fixed = {
	value = 0
	if = {
		limit = { has_variable = nd_safeguards }
		add = {
			value = var:nd_safeguards
			multiply = 2
		}
	}
	if = {
		limit = { has_variable = nd_hardening }
		add = {
			value = var:nd_hardening
			multiply = 3
		}
	}
}

nd_upkeep_units_base = {
	value = nd_upkeep_units_fixed
	if = {
		limit = { nd_readiness_recessed = yes }
		add = nd_upkeep_units_custody_recessed
	}
	else = {
		add = nd_upkeep_units_custody
	}
}
```

The four previews (replace `_1.._3`, add `_0`): `_0` = fixed + custody_recessed; `_1` = fixed + custody; `_2` = `_1` + readiness_2; `_3` = `_1` + readiness_3; each `max = 40` then `multiply = { value = gdp divide = 100000 }` as today. Update the header comment table (custody 0.1 at Recessed).

`nd_incident_permille`: after the `var:nd_readiness = 3` branch add

```
	else_if = {
		limit = { nd_readiness_recessed = yes }
		value = 0.5
	}
```

and the comment line `recessed 0.5, routine 1, heightened 4, high alert 10`.

Pressure part (after `nd_yp_alert_value`), and add `add = nd_yp_recessed_value` after `add = nd_yp_alert_value` in `nd_yield_pressure_value`:

```
# Weapons stored apart from their delivery systems cannot be used for weeks:
# the threat is that much further from being carried out (Recessed).
nd_yp_recessed_value = {
	value = 0
	scope:nd_issuer = {
		if = {
			limit = { nd_readiness_recessed = yes }
			add = -10
		}
	}
}
```

`nd_ig_term_readiness_value` — militarist: `var:nd_readiness = 1` → `var:nd_readiness <= 1`; restraint: add `else_if = { limit = { var:nd_readiness = 0 } add = 1 }`; professional: first branch becomes

```
				if = {
					limit = { var:nd_readiness = 0 }
					add = -1
				}
				else_if = {
					limit = {
						var:nd_readiness = 1
						nd_has_plausible_attacker = yes
					}
					add = -1
				}
```

- [ ] **Step 6: Crisis sites** (`nuclear_crisis_effects.txt`)
  - dispute 5 resolution: `var:nd_readiness_target = 1` → `var:nd_readiness_target <= 1`.
  - concession branch and `nd_standdown_one_side`: wrap `nd_set_readiness_target_1 = yes` in `if = { limit = { var:nd_readiness_target > 1 } … }` (the lock line stays outside it).
  - hold-alert text: `if = { limit = { var:nd_readiness = 0 } custom_tooltip = nd_tt_hold_alert_6w } else_if = { limit = { var:nd_readiness = 1 } custom_tooltip = nd_tt_hold_alert_4w } else = { … 2w }`.
  - `nd_crisis_refresh_figures`: `nd_crisis_store_yp = { C = nd_yp_recessed V = nd_yp_recessed_value }` right after the `nd_yp_alert` line; `nd_crisis_clear_figures`: the matching `if = { limit = { has_variable = nd_yp_recessed } remove_variable = nd_yp_recessed }`.
  - `nd_crisis_pressure_breakdown_sgui` (sguis): `nd_crisis_breakdown_line = { C = nd_yp_recessed KEY = nd_yp_recessed_line }` after the alert line.

- [ ] **Step 7: Panel** — sgui op 20 in both `is_valid` (`nd_can_set_readiness = { R = 0 LOCK_OK = yes }`) and `effect` (`nd_set_readiness_target_0 = yes`); ops 21–23 gain `LOCK_OK = yes|yes|no|no`; header op table `20..23 set readiness target 0..3`. Widget: copy the Routine `nd_choice_row` above it with `nd_w_readiness_choice_0`, `nd_w_readiness_choice_0_tt`, `(CFixedPoint)20`; header comment `20..23 readiness 0..3`. Custom loc: `nd_readiness_name` gains a `var:nd_readiness = 0` → `nd_readiness_0` entry; `nd_readiness_moving` gains target-0 → `nd_readiness_moving_0`.

- [ ] **Step 8: Loc** (`te_miscellaneous_l_english.yml`, then `python3 organize_loc.py`)

```
 nd_readiness_0:0 "Recessed"
 nd_readiness_moving_0:0 " #lore (standing down to Recessed)#!"
 nd_tt_readiness_target_0:0 "Our warheads are taken off their delivery systems and put into storage: #v Recessed#!, one step every two weeks. Nothing can be launched until they are back at #v Routine#!. Upkeep at this level: @money!#v [GetPlayer.MakeScope.ScriptValue('nd_upkeep_weekly_at_readiness_0')|D]#!/week"
 nd_w_readiness_choice_0:0 "Recessed"
 nd_w_readiness_choice_0_tt:0 "#tooltip_header Recessed#!\n$TOOLTIP_DELIMITER$\nWarheads stored apart from their delivery systems. The cheapest and safest posture — custody costs half, incidents are half as likely as at Routine, and a crisis with us is less dangerous — and the least usable: #R nothing can be launched, not even in retaliation, until our forces are back at Routine, two weeks away.#! A threat we make is taken less seriously. Restraint-minded groups approve; the officers do not.\n\nUpkeep at this level: @money!#v [GetPlayer.MakeScope.ScriptValue('nd_upkeep_weekly_at_readiness_0')|D]#!/week"
 nd_tt_forces_assembled:0 "Our warheads are mated to their delivery systems (readiness #v Routine#! or higher; from #v Recessed#! that is two weeks away)"
 nd_tt_hold_alert_6w:0 "Our forces reach #v High Alert#! in #v 6#! weeks. At High Alert their pressure to concede rises by #G 10#!, and so do our upkeep and the odds of an accident"
 nd_yp_recessed_line:0 "#v [THIS.Var('nd_yp_recessed').GetValue|+0]#!  The threatening side's warheads are in storage, weeks from use"
```

Changed: `nd_tt_readiness_locked` → "No stand-down agreement or concession holds our readiness at Routine or below"; `nd_w_readiness_legend` → "Readiness moves one step every two weeks toward the level ordered. An agreed or conceded stand-down holds it at Routine or below for two years."; `nd_w_readiness_tt` gains "Recessed takes the warheads off their delivery systems: nothing can be launched from it." before "A change takes two weeks per step."

- [ ] **Step 9: Run the tests** — `python3 -m unittest test_nuclear_deterrence -v 2>&1 | tail -5` → OK. Then `python3 scripts/format_paradox_tabs.py --check` on the touched `.txt`/`.gui` files.

- [ ] **Step 10: Commit**

```bash
git add common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_deterrence_effects.txt \
  common/script_values/nuclear_deterrence_values.txt common/scripted_effects/nuclear_crisis_effects.txt \
  common/scripted_guis/nuclear_deterrence_sguis.txt common/customizable_localization/nuclear_deterrence_custom_loc.txt \
  gui/journal_entry_widgets/nuclear_deterrence_widget.gui localization/english/*.yml test_nuclear_deterrence.py
git commit -m "Nuclear posture: a Recessed readiness below Routine"
```

---

### Task 2: Recessed forbids every launch; the licence to answer waits for the forces

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_retaliation_permitted`, `nd_incident_eligible_commander`, `nd_monopoly_window_conditions`)
- Modify: `common/diplomatic_actions/nuke.txt` (both `possible`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (both dispatch fences; `nd_weekly_update`; new `nd_assemble_for_retaliation`)
- Modify: `events/nuclear_crisis_events.txt` (`.4.g`, `.7.a`)
- Modify: `events/nuclear_incident_events.txt` (`.20` trigger)
- Modify: `events/nuclear_weapon_events.txt` (`.1` option d; new `.24`)
- Modify: `localization/english/te_events_l_english.yml`, `te_miscellaneous_l_english.yml`
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: `nd_forces_assembled`, `nd_set_readiness_target_1` (Task 1).
- Produces: effect `nd_assemble_for_retaliation = { ENEMY = <scope> }` (country scope); variable `nd_pending_retaliation` (a country); saved scope `nd_ready_enemy` in `.24`; event `nuclear_weapon_events.24`.

- [ ] **Step 1: Failing tests**

```python
WEAPON_EVENTS = ROOT / "events/nuclear_weapon_events.txt"


class TestLaunchGate(unittest.TestCase):
    def test_every_launch_path_needs_assembled_forces(self):
        nuke = strip_comments(read(NUKE))
        for action in ("nuke_diplo_action", "tactical_nuke_diplo_action"):
            self.assertIn("nd_forces_assembled = yes", block(block(nuke, action), "possible"), action)
        t = strip_comments(read(TRIGGERS))
        for name in ("nd_retaliation_permitted", "nd_incident_eligible_commander", "nd_monopoly_window_conditions"):
            self.assertIn("nd_forces_assembled = yes", block(t, name), name)
        e = strip_comments(read(EFFECTS))
        for name in ("nd_dispatch_strategic_strike", "nd_dispatch_tactical_strike"):
            self.assertIn("nd_forces_assembled = yes", block(e, name), name)
        ev = strip_comments(read(CRISIS_EVENTS))
        for opt in ("nuclear_crisis.4.g", "nuclear_crisis.7.a"):
            self.assertIn("nd_forces_assembled = yes", option_body(ev, opt), opt)

    def test_struck_while_recessed_can_wait_and_answer(self):
        ev = strip_comments(read(WEAPON_EVENTS))
        self.assertIn("nd_assemble_for_retaliation = { ENEMY = scope:attacking_country }",
                      option_body(ev, "nuclear_weapon_events.1.d"))
        self.assertRegex(ev, r"(?m)^nuclear_weapon_events\.24 = \{")
        weekly = block(strip_comments(read(EFFECTS)), "nd_weekly_update")
        self.assertIn("nd_pending_retaliation", weekly)
        self.assertIn("id = nuclear_weapon_events.24", weekly)
        body = block(ev, "nuclear_weapon_events.24")
        self.assertIn("has_war_with = scope:nd_ready_enemy", body)
```

- [ ] **Step 2: Run** — expect `TestLaunchGate` failures.

- [ ] **Step 3: Gates.** Add, in each named place, the line (inside a `custom_tooltip` where the block is a player-facing gate):

`nuke.txt` `possible` (both actions), and `nd_retaliation_permitted`:
```
		custom_tooltip = {
			text = nd_tt_forces_assembled
			nd_forces_assembled = yes
		}
```
`nd_incident_eligible_commander`, `nd_monopoly_window_conditions` (after `nd_is_armed = yes`), `.4.g` / `.7.a` triggers (after `nd_is_armed = yes`), Silence from the Capital's `trigger` (`nuclear_incident.20`), and both dispatch fences' `limit` (after `nd_is_armed = yes`): `nd_forces_assembled = yes`.

- [ ] **Step 4: Assemble and wait** — in `nuclear_deterrence_effects.txt`, INCIDENT CONSEQUENCES section:

```
# Struck while Recessed (spec 2026-09-25 §2.4): mate the warheads to their
# delivery systems — the readiness target goes to Routine unless it is already
# higher — and remember whom to answer. nd_weekly_update asks again
# (nuclear_weapon_events.24) the week the forces reach Routine. Country scope
# = the struck country. Set directly, not through nd_can_set_readiness: a
# stand-down lock holds readiness at Routine or below, and Routine is where
# this goes.
nd_assemble_for_retaliation = {
	custom_tooltip = {
		text = nd_tt_assemble_for_retaliation
		set_variable = { name = nd_pending_retaliation value = $ENEMY$ }
	}
	if = {
		limit = {
			has_variable = nd_readiness_target
			var:nd_readiness_target < 1
		}
		nd_set_readiness_target_1 = yes
	}
}
```

`nd_weekly_update`, at the end of the readiness-transition block (after `nd_apply_posture_modifiers = yes`, still inside the step branch) — and also once outside it so a pending answer whose forces were already moving is caught:

```
	# ---- an answer that waited for the forces (spec §2.4) ------------------
	if = {
		limit = {
			has_variable = nd_pending_retaliation
			nd_forces_assembled = yes
		}
		if = {
			limit = {
				exists = var:nd_pending_retaliation
				nd_is_armed = yes
				has_war_with = var:nd_pending_retaliation
			}
			var:nd_pending_retaliation = { save_scope_as = nd_ready_enemy }
			trigger_event = { id = nuclear_weapon_events.24 popup = yes }
		}
		remove_variable = nd_pending_retaliation
	}
```

(Place this block once, after the readiness-transition `if`, not inside it.)

- [ ] **Step 5: `.1` option d** — add after option c:

```
	# Struck while Recessed (spec 2026-09-25 §2.4): the weapons cannot fly
	# yet. Mate them and answer when they are ready — .24 asks again.
	option = {
		name = nuclear_weapon_events.1.d
		trigger = {
			scope:target_country = {
				nd_is_armed = yes
				nd_forces_assembled = no
			}
		}
		scope:target_country = {
			nd_assemble_for_retaliation = { ENEMY = scope:attacking_country }
		}
		ai_chance = {
			base = 10
			modifier = {
				trigger = {
					NOT = { scope:target_country = { nd_ai_nuclear_use_justified = { ENEMY = scope:attacking_country } } }
				}
				factor = 0
			}
		}
	}
```

- [ ] **Step 6: `.24` "Our Forces Are Ready"** — append after `.23`:

```
# ---- .24 Our Forces Are Ready ----------------------------------------------------
# A country struck while Recessed chose to answer once its warheads were
# mated (.1 option d, nd_assemble_for_retaliation); nd_weekly_update sends
# this the week readiness reaches Routine, if it is still at war with the
# attacker (scope:nd_ready_enemy) and still armed. The options are .1's b and
# c with the roles saved under the names nuclear_response_strike reads:
# target_country = us, the answering side; attacking_country = them.
nuclear_weapon_events.24 = {
	type = country_event
	placement = root

	event_image = { texture = "gfx/event_pictures/nuclear_bunker_life.dds" }

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_military.dds"

	title = nuclear_weapon_events.24.t
	desc = nuclear_weapon_events.24.d
	flavor = nuclear_weapon_events.24.f

	duration = 3

	trigger = {
		exists = scope:nd_ready_enemy
		nd_is_armed = yes
		has_war_with = scope:nd_ready_enemy
	}

	immediate = {
		save_scope_as = target_country
		scope:nd_ready_enemy = { save_scope_as = attacking_country }
	}

	# Stand down: the moment has passed.
	option = {
		name = nuclear_weapon_events.24.a
		default_option = yes
		ai_chance = { base = 1 }
	}

	# One warhead.
	option = {
		name = nuclear_weapon_events.24.b
		trigger = {
			var:nuclear_weapon_stockpile > 0
			nd_retaliation_permitted = { ENEMY = scope:attacking_country }
		}
		highlighted_option = yes
		scope:attacking_country = {
			ordered_scope_state = {
				order_by = nuclear_industrial_strike_target_score
				position = 0
				nuclear_response_strike = yes
			}
		}
		nd_record_nuclear_use = { VICTIM = scope:attacking_country }
		ai_chance = {
			base = 8
			modifier = {
				trigger = { NOT = { nd_ai_nuclear_use_justified = { ENEMY = scope:attacking_country } } }
				factor = 0
			}
		}
	}

	# Everything we promised.
	option = {
		name = nuclear_weapon_events.24.c
		trigger = {
			var:nuclear_weapon_stockpile > 2
			nd_retaliation_permitted = { ENEMY = scope:attacking_country }
		}
		highlighted_option = yes
		scope:attacking_country = {
			ordered_scope_state = {
				order_by = nuclear_industrial_strike_target_score
				position = 0
				nuclear_response_strike = yes
			}
			ordered_scope_state = {
				order_by = nuclear_industrial_strike_target_score
				position = 1
				nuclear_response_strike = yes
			}
			ordered_scope_state = {
				order_by = nuclear_industrial_strike_target_score
				position = 2
				nuclear_response_strike = yes
			}
		}
		nd_record_nuclear_use = { VICTIM = scope:attacking_country }
		ai_chance = {
			base = 3
			modifier = {
				trigger = { ruler_is_aggressive = yes }
				add = 8
			}
			modifier = {
				trigger = { NOT = { nd_ai_nuclear_use_justified = { ENEMY = scope:attacking_country } } }
				factor = 0
			}
		}
	}
}
```

(Task 3 adds the Automatic Retaliation variant: a `nd_authority_automatic = no` line in a/b/c's triggers and an `e` option.)

- [ ] **Step 7: Loc**

`te_events_l_english.yml`:
```
 nuclear_weapon_events.1.d:0 "Mate the warheads — we answer when they are ready"
 nuclear_weapon_events.24.t:0 "Our Forces Are Ready"
 nuclear_weapon_events.24.d:0 "Our warheads are back on their delivery systems, two weeks after [SCOPE.sCountry('attacking_country').GetName] struck us while they lay in storage. We are still at war with [SCOPE.sCountry('attacking_country').GetName], and the answer we held back can be given now."
 nuclear_weapon_events.24.f:0 "\"The keys are in. Say the word.\""
 nuclear_weapon_events.24.a:0 "The moment has passed. Stand the crews down."
 nuclear_weapon_events.24.b:0 "One weapon, on their most important city."
 nuclear_weapon_events.24.c:0 "Everything we promised them."
```
`te_miscellaneous_l_english.yml`:
```
 nd_tt_assemble_for_retaliation:0 "Our warheads are put back on their delivery systems (readiness #v Routine#!, two weeks away). When they are ready, and if we are still at war with the country that struck us, we decide how to answer"
```

- [ ] **Step 8: Run tests** → OK. Tab check on touched files.

- [ ] **Step 9: Commit** — `git commit -m "Nuclear posture: nothing launches from Recessed; a struck recessed country can answer once assembled"` (stage the files listed above by path).

---

### Task 3: Automatic Retaliation (authority 4)

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (authority block; new `nd_auto_answers_strike`; `nd_strike_from_incident`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_set_authority_*`, `nd_set_authority`, AI authority block, `nd_monthly_update` countdown, `nd_start_unconfirmed_warning` routing unchanged but verified, new `nd_auto_answer_record`, new `nd_system_reads_attack`)
- Modify: `common/script_values/nuclear_deterrence_values.txt` (`nd_yp_answer_value`, `nd_ig_term_authority_value`, `nd_upkeep_units_fixed`, `nd_upkeep_weekly_automatic_step`)
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` (op 34), widget (fourth authority row), custom loc (`nd_authority_name`)
- Modify: `events/nuclear_weapon_events.txt` (`.1` a/b/c/d gating and option e; `.24` a/b/c gating and option e; `.2` desc variant)
- Modify: `events/nuclear_incident_events.txt` (`.30` immediate + desc variants)
- Modify: loc files
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: `nd_forces_assembled`, `nd_retaliation_permitted` (Task 2).
- Produces: triggers `nd_authority_automatic`, `nd_can_adopt_automatic_retaliation`, `nd_auto_answers_strike = { ENEMY }`; effect `nd_set_authority_4`; variables `nd_auto_answered_country`, `nd_auto_answered_months`; `nd_launch_or_intercept` KIND `system`.

- [ ] **Step 1: Failing tests** (and `test_custom_tooltip_keys` authority family → `range(1, 5)`)

```python
class TestAutomaticRetaliation(unittest.TestCase):
    def setUp(self):
        self.t = strip_comments(read(TRIGGERS))
        self.ev = strip_comments(read(WEAPON_EVENTS))

    def test_authority_triggers(self):
        for name in ("nd_authority_automatic", "nd_can_adopt_automatic_retaliation", "nd_auto_answers_strike"):
            self.assertRegex(self.t, rf"(?m)^{name} = \{{")
        deleg = block(self.t, "nd_authority_delegated_or_warning")
        self.assertNotIn(">= 2", deleg)
        self.assertIn("var:nd_authority = 2", deleg)
        self.assertIn("var:nd_authority = 3", deleg)
        self.assertIn("mainframe_computers", block(self.t, "nd_can_adopt_automatic_retaliation"))
        self.assertIn(34, gui_ops(read(GUI), "nd_posture_sgui"))

    def test_first_strike_is_answered_automatically_and_only_there(self):
        auto = option_body(self.ev, "nuclear_weapon_events.1.e")
        self.assertIn("nd_auto_answers_strike = { ENEMY = scope:attacking_country }", auto)
        for opt in ("nuclear_weapon_events.1.a", "nuclear_weapon_events.1.b", "nuclear_weapon_events.1.c"):
            self.assertIn("nd_auto_answers_strike = { ENEMY = scope:attacking_country }", option_body(self.ev, opt), opt)
        # .11 (being answered) never fires by itself: no loop between two systems.
        self.assertNotIn("nd_auto_answers_strike", block(self.ev, "nuclear_weapon_events.11"))
        self.assertIn("nd_auto_answered_months", block(self.t, "nd_auto_answers_strike"))

    def test_accident_branch_goes_through_the_launch_path(self):
        inc = strip_comments(read(INCIDENT_EVENTS))
        body = block(inc, "nuclear_incident.30")
        self.assertIn("nd_system_reads_attack = yes", body)
        e = block(strip_comments(read(EFFECTS)), "nd_system_reads_attack")
        self.assertIn("KIND = system", e)
        self.assertIn("nd_authority_automatic = yes", e)
```

- [ ] **Step 2: Run** — expect failures.

- [ ] **Step 3: Triggers**

```
nd_authority_delegated_or_warning = {
	has_variable = nd_authority
	OR = {
		var:nd_authority = 2
		var:nd_authority = 3
	}
}

# Automatic Retaliation (spec 2026-09-25 §3): a strike on our territory is
# answered in full without a further decision. It routes an early warning to
# the government, as Central Authorization does, and has no delegated
# commanders.
nd_authority_automatic = {
	has_variable = nd_authority
	var:nd_authority = 4
}

nd_can_adopt_automatic_retaliation = {
	has_technology_researched = radar
	has_technology_researched = ICBMs
	has_technology_researched = mainframe_computers
}

# The struck country (scope:target_country in nuclear_weapon_events.1): does
# its system answer $ENEMY$'s first strike by itself? Only here, never when
# being answered (.11), so two systems cannot empty each other's arsenals;
# and not twice against the same country within nd_auto_answered_months.
nd_auto_answers_strike = {
	nd_authority_automatic = yes
	nd_is_armed = yes
	nd_retaliation_permitted = { ENEMY = $ENEMY$ }
	NOT = {
		AND = {
			has_variable = nd_auto_answered_months
			has_variable = nd_auto_answered_country
			var:nd_auto_answered_country ?= $ENEMY$
		}
	}
}
```

`nd_strike_from_incident` gains `nd_strike_from_incident_of = { KIND = system }` in its OR.

- [ ] **Step 4: Effects**

```
nd_set_authority_1 = { nd_set_authority = { A = 1 DELEGATED = no AUTOMATIC = no } }
nd_set_authority_2 = { nd_set_authority = { A = 2 DELEGATED = yes AUTOMATIC = no } }
nd_set_authority_3 = { nd_set_authority = { A = 3 DELEGATED = yes AUTOMATIC = no } }
nd_set_authority_4 = { nd_set_authority = { A = 4 DELEGATED = no AUTOMATIC = yes } }
```

`nd_set_authority` gains, after the DELEGATED line, `if = { limit = { always = $AUTOMATIC$ } custom_tooltip = nd_tt_authority_consequence_automatic }`, and ends with `nd_apply_posture_modifiers = yes` (upkeep changes with authority 4).

AI authority block — insert after the launch-on-warning branch:

```
		else_if = {
			limit = {
				nd_can_adopt_automatic_retaliation = yes
				nd_regime_is_militarist = no
				ruler_is_cautious = no
				nd_has_plausible_attacker = yes
				var:nd_survivability < 50
				NOT = { var:nd_authority = 4 }
			}
			random = {
				chance = 25
				nd_set_authority_4 = yes
			}
		}
```

`nd_monthly_update`, countdowns: `nd_tick_countdown = { VAR = nd_auto_answered_months }`.

Record helper (used by `.1.e` and `.24.e`):

```
# After an automatic answer to $ENEMY$: the per-attacker cooldown (spec §3.4).
nd_auto_answer_record = {
	set_variable = { name = nd_auto_answered_country value = $ENEMY$ }
	set_variable = { name = nd_auto_answered_months value = 6 }
}
```

The accident branch (`.30`), country scope, called from `.30`'s immediate after the accident kind is drawn:

```
# The Cost of Permanent Alert under Automatic Retaliation (spec §3.3): a
# bomber breaking up with weapons aboard, or a silo exploding, while at war or
# in an acute crisis, reads to the system as an attack. Someone in the chain
# may still stop it (nd_hold_chance); if nobody does, it launches at the most
# likely attacker through the one launch path — a strike in a war, an order
# recalled at the last moment outside one. Writes nd_system_reacted
# (1 halted, 2 launched) for .30's text. Country scope = the country.
nd_system_reads_attack = {
	if = {
		limit = {
			nd_authority_automatic = yes
			nd_forces_assembled = yes
			nd_is_armed = yes
			has_variable = nd_accident_kind
			OR = {
				var:nd_accident_kind = 1
				var:nd_accident_kind = 2
			}
			OR = {
				is_at_war = yes
				nd_crisis_stage_at_least = { STAGE = 3 }
			}
		}
		save_scope_as = nd_system_country
		if = {
			limit = {
				nd_in_crisis = yes
				var:nd_crisis_opponent ?= { nd_believed_armed = yes }
			}
			var:nd_crisis_opponent = { save_scope_as = nd_system_suspect }
		}
		else = {
			random_country = {
				limit = {
					has_war_with = scope:nd_system_country
					nd_believed_armed = yes
				}
				save_scope_as = nd_system_suspect
			}
		}
		if = {
			limit = { exists = scope:nd_system_suspect }
			nd_roll_launch_hold = yes
			if = {
				limit = { var:nd_launch_held = 1 }
				set_variable = { name = nd_system_reacted value = 1 }
			}
			else = {
				set_variable = { name = nd_system_reacted value = 2 }
				nd_launch_or_intercept = { VICTIM = scope:nd_system_suspect NARRATE = yes KIND = system }
			}
		}
	}
}
```

- [ ] **Step 5: Values** — `nd_upkeep_units_fixed` gains `if = { limit = { nd_authority_automatic = yes } add = 3 }`; `nd_upkeep_weekly_automatic_step = { value = gdp divide = 100000 multiply = 3 }`; `nd_yp_answer_value`: `else_if = { limit = { var:nd_survivability >= 50 } … }` becomes

```
	else_if = {
		limit = {
			OR = {
				nd_authority_automatic = yes
				AND = {
					has_variable = nd_survivability
					var:nd_survivability >= 50
				}
			}
		}
		subtract = 25
	}
```

`nd_ig_term_authority_value`: `owner = { nd_authority_launch_on_warning = yes }` → `owner = { OR = { nd_authority_launch_on_warning = yes nd_authority_automatic = yes } }`.

- [ ] **Step 6: Events**
  - `.1` options a, b, c, d: add `NOT = { scope:target_country = { nd_auto_answers_strike = { ENEMY = scope:attacking_country } } }` to each trigger (a gains a `trigger = { … }`), and d gains `nd_authority_automatic = no` is NOT added — under Automatic Retaliation while Recessed, d is the only option left (a, b, c are excluded by an extra line: a's trigger also requires `NOT = { scope:target_country = { nd_authority_automatic = yes nd_is_armed = yes nd_forces_assembled = no } }`).
  - `.1` option e:

```
	# Automatic Retaliation (spec 2026-09-25 §3.3): the system answers in
	# full, and nobody is asked. The salvo is sized from the stock before it
	# flies, so the tooltip and the run agree.
	option = {
		name = nuclear_weapon_events.1.e
		trigger = {
			scope:target_country = { nd_auto_answers_strike = { ENEMY = scope:attacking_country } }
		}
		highlighted_option = yes
		scope:attacking_country = {
			ordered_scope_state = {
				order_by = nuclear_industrial_strike_target_score
				position = 0
				nuclear_response_strike = yes
			}
		}
		if = {
			limit = { scope:target_country = { var:nuclear_weapon_stockpile >= 3 } }
			scope:attacking_country = {
				ordered_scope_state = {
					order_by = nuclear_industrial_strike_target_score
					position = 1
					nuclear_response_strike = yes
				}
				ordered_scope_state = {
					order_by = nuclear_industrial_strike_target_score
					position = 2
					nuclear_response_strike = yes
				}
			}
		}
		else_if = {
			limit = { scope:target_country = { var:nuclear_weapon_stockpile >= 2 } }
			scope:attacking_country = {
				ordered_scope_state = {
					order_by = nuclear_industrial_strike_target_score
					position = 1
					nuclear_response_strike = yes
				}
			}
		}
		scope:target_country = {
			nd_record_nuclear_use = { VICTIM = scope:attacking_country }
			hidden_effect = { nd_auto_answer_record = { ENEMY = scope:attacking_country } }
		}
		ai_chance = { base = 1 }
	}
```

  **Order inside the option:** the sized `if` / `else_if` (extra warheads at positions 1–2) comes **first** and the position-0 strike **last**, so the stock the limits read is the stock before anything flies — the same in the tooltip preview and the run. Each `ordered_scope_state` call re-orders by score, so issuing positions 1–2 before 0 is harmless.

  - `.24`: a, b, c triggers gain `nd_authority_automatic = no`; option e mirrors `.1.e` in `.24`'s scopes (ROOT is the country: `var:nuclear_weapon_stockpile`, `nd_record_nuclear_use`, `nd_auto_answer_record` in ROOT; trigger `nd_authority_automatic = yes` and `nd_retaliation_permitted = { ENEMY = scope:attacking_country }`).
  - `.2` desc: `triggered_desc = { trigger = { nd_strike_from_incident_of = { KIND = system } } desc = nuclear_weapon_events.2.d_system }` before the warning variant.
  - `.30` immediate: after the `random_scope_state` accident-state block, `nd_system_reads_attack = yes`; desc `first_valid` gains, at the top,

```
			triggered_desc = {
				trigger = {
					nd_accident_kind_is = { K = 1 }
					has_variable = nd_system_reacted
				}
				desc = nuclear_incident.30.d_bomber_system
			}
			triggered_desc = {
				trigger = {
					nd_accident_kind_is = { K = 2 }
					has_variable = nd_system_reacted
				}
				desc = nuclear_incident.30.d_silo_system
			}
```

    and `after` gains `if = { limit = { has_variable = nd_system_reacted } remove_variable = nd_system_reacted }`. The two descs name both outcomes via custom loc `nd_system_outcome` (country; `nd_system_reacted = 1` → `nd_system_outcome_held`, else `nd_system_outcome_fired`).

- [ ] **Step 7: Panel** — sgui op 34 (`nd_can_set_authority = { A = 4 }` + `custom_tooltip = { text = nd_tt_need_computers nd_can_adopt_automatic_retaliation = yes }`; effect `nd_set_authority_4 = yes`); widget fourth authority row (`nd_w_authority_choice_4`, `_tt`, `(CFixedPoint)34`); header op tables `31..34`; custom loc `nd_authority_name` gains 4 → `nd_authority_4`.

- [ ] **Step 8: Loc**

`te_miscellaneous_l_english.yml`:
```
 nd_authority_4:0 "Automatic Retaliation"
 nd_tt_authority_adopted_4:0 "Launch authority becomes #v Automatic Retaliation#!. It can next be changed in a year."
 nd_tt_authority_consequence_automatic:0 "#R A nuclear strike on our cities will be answered in full — three warheads — without a decision from us,#! and a weapons accident at home during a war or an acute crisis can be read as an attack. Upkeep rises by @money!#v [GetPlayer.MakeScope.ScriptValue('nd_upkeep_weekly_automatic_step')|D]#!/week"
 nd_tt_need_computers:0 "We have researched $radar$, $ICBMs$ and $mainframe_computers$"
 nd_w_authority_choice_4:0 "Automatic Retaliation"
 nd_w_authority_choice_4_tt:0 "#tooltip_header Automatic Retaliation#!\n$TOOLTIP_DELIMITER$\nA system that answers a nuclear strike on our territory by itself, whether or not anyone is left to give the order. Retaliation becomes certain however vulnerable our forces are, so a threat against us carries less weight. An early warning still goes to the government, which can wait for proof.\n\n#R A strike on our cities is answered in full, with no choice left to us; a weapons accident at home during a war or an acute crisis can set it off.#! Restraint-minded groups disapprove.\n\nExtra upkeep: @money!#v [GetPlayer.MakeScope.ScriptValue('nd_upkeep_weekly_automatic_step')|D]#!/week"
 nd_system_outcome_held:0 "An officer at the relay station refused to pass the order on until the capital answered. Nothing flew."
 nd_system_outcome_fired:0 "The system did what it was built to do. By the time the capital understood, the missiles were in the air."
```
Changed: `nd_w_authority_legend` → "Launch authority can be changed once a year. Delegation needs radar; launch on warning needs missiles as well; automatic retaliation also needs mainframe computers."; `nd_w_authority_tt` gains "Under automatic retaliation, a strike on our cities is answered in full by the system." before its last sentence.

`te_events_l_english.yml`:
```
 nuclear_weapon_events.1.e:0 "The system has already answered."
 nuclear_weapon_events.24.e:0 "The system answers, now that it can."
 nuclear_weapon_events.2.d_system:0 "Our [concept_nuclear_strike] has fallen on [SCOPE.sState('target_state').GetName]. No one in the government ordered it: our automatic retaliation system read an accident on our own soil as an attack, and answered."
 nuclear_incident.30.d_bomber_system:0 "A bomber carrying nuclear weapons broke up over [SCOPE.sState('nd_accident_state').GetName], and one of the weapons partly detonated. To the automatic retaliation system, a nuclear flash on our soil in wartime could mean only one thing.\n\n[ROOT.GetCountry.GetCustom('nd_system_outcome')]"
 nuclear_incident.30.d_silo_system:0 "A missile silo in [SCOPE.sState('nd_accident_state').GetName] exploded. To the automatic retaliation system, a blast of that size on our soil in wartime could mean only one thing.\n\n[ROOT.GetCountry.GetCustom('nd_system_outcome')]"
```

- [ ] **Step 9: Run tests** → OK; tab check.

- [ ] **Step 10: Commit** — `git commit -m "Nuclear posture: Automatic Retaliation launch authority"`.

---

### Task 4: The umbrella — coverage everywhere the guarantee reaches

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (new `nd_umbrella_withdrawn`, `nd_under_an_umbrella`, `nd_under_umbrella_of`, `nd_is_guaranteed_by_treaty`, `nd_beneficiary_threatened_by`; extended `nd_has_armed_guarantor_against`, `nd_is_guaranteed`, `nd_is_guaranteed_by`, `nd_dispute_guarantee_against`)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_classify_dispute`, `nd_crisis_notify_guarantors`, `nd_guarantee_act_abandon`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_record_nuclear_use`)
- Modify: `common/treaty_articles/115_nuclear_guarantee.txt` (`possible`)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: the pact type `nd_withdraw_umbrella_action` (Task 5 defines it; the trigger only names it, so order does not matter for loading, but the test in Task 5 checks it exists).
- Produces: `nd_under_an_umbrella` (subject scope), `nd_under_umbrella_of = { OVERLORD }`, `nd_is_guaranteed_by_treaty = { GUARANTOR }`.

- [ ] **Step 1: Failing tests**

```python
class TestUmbrellaCoverage(unittest.TestCase):
    GUARANTEE_READERS = {"nd_has_armed_guarantor_against", "nd_is_guaranteed", "nd_is_guaranteed_by_treaty",
                         "nd_dispute_guarantee_against", "nd_crisis_classify_dispute", "nd_crisis_notify_guarantors",
                         "nd_record_nuclear_use", "nd_guarantee_act_abandon", "nd_covered_country_struck_by",
                         "nd_covered_country_struck"}

    def test_umbrella_triggers(self):
        t = strip_comments(read(TRIGGERS))
        for name in ("nd_umbrella_withdrawn", "nd_under_an_umbrella", "nd_under_umbrella_of",
                     "nd_is_guaranteed_by_treaty", "nd_beneficiary_threatened_by"):
            self.assertRegex(t, rf"(?m)^{name} = \{{")
        self.assertIn("nd_withdraw_umbrella_action", block(t, "nd_umbrella_withdrawn"))
        for name in ("nd_has_armed_guarantor_against", "nd_is_guaranteed", "nd_is_guaranteed_by",
                     "nd_dispute_guarantee_against"):
            self.assertIn("umbrella", block(t, name), name)

    def test_every_guarantee_read_is_a_known_site(self):
        """A new `has_type = nuclear_guarantee` read outside the known sites
        would see treaties but not umbrellas."""
        for path in (TRIGGERS, EFFECTS, CRISIS_EFFECTS):
            text = strip_comments(read(path))
            for m in re.finditer(r"has_type = nuclear_guarantee", text):
                owner = re.findall(r"(?m)^(\w+) = \{", text[:m.start()])[-1]
                self.assertIn(owner, self.GUARANTEE_READERS, f"{path.name}: {owner}")

    def test_umbrella_loops_exist_beside_treaty_loops(self):
        c = strip_comments(read(CRISIS_EFFECTS))
        e = strip_comments(read(EFFECTS))
        for body in (block(c, "nd_crisis_notify_guarantors"), block(e, "nd_record_nuclear_use")):
            self.assertIn("nd_under_an_umbrella = yes", body)
            self.assertIn("nd_is_guaranteed_by_treaty", body)   # asked once, not twice
        self.assertIn("every_direct_subject", block(c, "nd_guarantee_act_abandon"))
        self.assertIn("random_direct_subject", block(c, "nd_crisis_classify_dispute"))

    def test_article_refuses_own_subject(self):
        self.assertIn("nd_tt_already_under_umbrella", block(strip_comments(read(ARTICLE)), "possible"))
```

- [ ] **Step 2: Run** — fail.

- [ ] **Step 3: Triggers** (in PERCEIVED RETALIATION AND MONOPOLY, before `nd_has_armed_guarantor_against`)

```
# ---- The nuclear umbrella (spec 2026-09-25 §1) ------------------------------
# A direct subject of an overlord believed armed is covered as if that
# overlord had signed a nuclear_guarantee for it, unless the overlord has
# withdrawn it (nd_withdraw_umbrella_action, a pact). Coverage by umbrella is
# coverage by guarantee: it is folded into nd_has_armed_guarantor_against,
# nd_is_guaranteed and nd_is_guaranteed_by, and the three effect loops that
# walk guarantee articles (nd_crisis_notify_guarantors, nd_record_nuclear_use,
# nd_guarantee_act_abandon) each have an umbrella branch beside the treaty one.

# Has our overlord withdrawn its umbrella from us? The pact only exists between
# an overlord and its direct subject (requirement_to_maintain).
nd_umbrella_withdrawn = {
	any_scope_diplomatic_pact = {
		is_diplomatic_action_type = nd_withdraw_umbrella_action
	}
}

nd_under_an_umbrella = {
	is_subject = yes
	overlord ?= { nd_believed_armed = yes }
	NOT = { nd_umbrella_withdrawn = yes }
}

nd_under_umbrella_of = {
	is_direct_subject_of = $OVERLORD$
	nd_under_an_umbrella = yes
}

# The treaty half of nd_is_guaranteed_by: does $GUARANTOR$ hold a
# nuclear_guarantee article for this country? The umbrella branches ask this
# so an overlord that also signed a guarantee for its subject is asked once.
nd_is_guaranteed_by_treaty = {
	save_temporary_scope_as = nd_guarantee_ben3
	any_scope_treaty = {
		any_scope_article = {
			has_type = nuclear_guarantee
			target_country = scope:nd_guarantee_ben3
			source_country = $GUARANTOR$
		}
	}
}

# Is this country in a play or war against $TARGET$ — the dispute a guarantor
# may open a crisis over (dispute 3)?
nd_beneficiary_threatened_by = {
	OR = {
		has_war_with = $TARGET$
		AND = {
			is_diplomatic_play_enemy_of = $TARGET$
			any_diplomatic_play = {
				is_war = no
				OR = {
					initiator_is = $TARGET$
					target_is = $TARGET$
				}
			}
		}
	}
}
```

Extended bodies:

```
nd_has_armed_guarantor_against = {
	save_temporary_scope_as = nd_guarantee_ben
	OR = {
		any_scope_treaty = {
			any_scope_article = {
				has_type = nuclear_guarantee
				target_country = scope:nd_guarantee_ben
				source_country = {
					nd_believed_armed = yes
					NOT = { this = $AGAINST$ }
				}
			}
		}
		# ...or under an overlord's umbrella that is not $AGAINST$.
		AND = {
			nd_under_an_umbrella = yes
			overlord ?= { NOT = { this = $AGAINST$ } }
		}
	}
}

nd_is_guaranteed = {
	save_temporary_scope_as = nd_guarantee_ben2
	OR = {
		any_scope_treaty = {
			any_scope_article = {
				has_type = nuclear_guarantee
				target_country = scope:nd_guarantee_ben2
			}
		}
		nd_under_an_umbrella = yes   # the umbrella
	}
}

nd_is_guaranteed_by = {
	OR = {
		nd_is_guaranteed_by_treaty = { GUARANTOR = $GUARANTOR$ }
		nd_under_umbrella_of = { OVERLORD = $GUARANTOR$ }   # the umbrella
	}
}
```

`nd_dispute_guarantee_against`: the `any_scope_treaty` block's `target_country = { OR = {…} }` becomes `target_country = { nd_beneficiary_threatened_by = { TARGET = $TARGET$ } }`, wrapped with a sibling in an `OR`:

```
	OR = {
		any_scope_treaty = { … as today, with the helper … }
		# ...or a subject under our umbrella.
		any_direct_subject = {
			nd_under_umbrella_of = { OVERLORD = scope:nd_dg_self }
			nd_beneficiary_threatened_by = { TARGET = $TARGET$ }
		}
	}
```

(Every caller passes a saved scope for `$TARGET$`, which the header's rule allows inside nested scopes.)

- [ ] **Step 4: Effects**

`nd_crisis_classify_dispute`, dispute-3 branch, after the treaty loop and before `if = { limit = { exists = scope:nd_crisis_ben } … }`:

```
		# ...or a subject under our umbrella (spec 2026-09-25 §1.2).
		if = {
			limit = { NOT = { exists = scope:nd_crisis_ben } }
			random_direct_subject = {
				limit = {
					nd_under_umbrella_of = { OVERLORD = scope:nd_issuer }
					nd_beneficiary_threatened_by = { TARGET = scope:nd_target }
				}
				save_scope_as = nd_crisis_ben
			}
		}
```

`nd_crisis_notify_guarantors`, after the treaty loop inside `scope:nd_target = { … }`:

```
		# The umbrella: our overlord, unless it is the issuer or the treaty loop
		# above has already asked it (spec 2026-09-25 §1.2).
		if = {
			limit = {
				nd_under_an_umbrella = yes
				overlord = { NOT = { this = scope:nd_issuer } }
			}
			overlord = { save_scope_as = nd_umb_guarantor }
			if = {
				limit = { NOT = { nd_is_guaranteed_by_treaty = { GUARANTOR = scope:nd_umb_guarantor } } }
				scope:nd_umb_guarantor = {
					save_scope_as = nd_guarantor
					set_variable = { name = nd_guarantee_context value = 1 }
					trigger_event = { id = nuclear_crisis.20 }
				}
			}
		}
```

`nd_record_nuclear_use`, after the victim's treaty loop, inside `$VICTIM$ = { … }`:

```
			# The umbrella: the victim's overlord, unless it is the attacker or
			# already asked through a treaty (spec 2026-09-25 §1.2).
			if = {
				limit = {
					nd_under_an_umbrella = yes
					overlord = { NOT = { this = scope:nd_guarantee_attacker } }
				}
				overlord = { save_scope_as = nd_umb_guarantor }
				if = {
					limit = { NOT = { nd_is_guaranteed_by_treaty = { GUARANTOR = scope:nd_umb_guarantor } } }
					scope:nd_umb_guarantor = {
						set_variable = { name = nd_guarantee_context value = 2 }
						trigger_event = { id = nuclear_crisis.20 }
					}
				}
			}
```

`nd_guarantee_act_abandon`: the visible liberty-desire cost (outside `hidden_effect`, before it; ROOT is the guarantor in `.20`):

```
	# Abandoning a subject under our umbrella feeds its wish to be free
	# (spec 2026-09-25 §1.4). The umbrella stays.
	if = {
		limit = {
			exists = scope:nd_guarantee_beneficiary
			scope:nd_guarantee_beneficiary = { nd_under_umbrella_of = { OVERLORD = ROOT } }
		}
		scope:nd_guarantee_beneficiary = { add_liberty_desire = 10 }
	}
```

and, beside the "every other beneficiary" treaty loop in the hidden block:

```
			every_direct_subject = {
				limit = {
					nd_under_umbrella_of = { OVERLORD = scope:nd_guarantor_self }
					NOT = { this = scope:nd_guarantee_beneficiary }
				}
				change_relations = { country = scope:nd_guarantor_self value = -10 }
			}
```

- [ ] **Step 5: Article** — `possible` gains:

```
		# A direct subject is already covered by our umbrella (spec 2026-09-25
		# §1.2); a treaty on top would ask us twice.
		custom_tooltip = {
			text = nd_tt_already_under_umbrella
			NOT = { scope:other_country = { is_direct_subject_of = ROOT } }
		}
```

Loc: `nd_tt_already_under_umbrella:0 "They are not our direct subject — a subject is already under our nuclear umbrella"`.

- [ ] **Step 6: Run tests** → OK (Task 5's test for the pact follows). Tab check.

- [ ] **Step 7: Commit** — `git commit -m "Nuclear guarantee: an armed overlord's subjects are covered by its umbrella"`.

---

### Task 5: Withdrawing the umbrella; the panel line

**Files:**
- Create: `common/diplomatic_actions/nuclear_umbrella_actions.txt` (UTF-8 BOM)
- Modify: `common/script_values/nuclear_deterrence_values.txt` (`nd_display_umbrella_count`)
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` (`nd_umbrella_sgui` display handler; header count)
- Modify: `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` (umbrella row in the posture summary)
- Modify: loc
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: `nd_under_an_umbrella` (Task 4).
- Produces: diplomatic action / pact type `nd_withdraw_umbrella_action`.

- [ ] **Step 1: Failing tests**

```python
UMBRELLA_ACTIONS = ROOT / "common/diplomatic_actions/nuclear_umbrella_actions.txt"


class TestUmbrellaWithdrawal(unittest.TestCase):
    def test_action_is_a_liberty_desire_pact(self):
        text = strip_comments(read(UMBRELLA_ACTIONS))
        body = block(text, "nd_withdraw_umbrella_action")
        self.assertIn("overlord", block(body, "groups"))
        self.assertIn("add_liberty_desire = 10", block(body, "accept_effect"))
        self.assertIn("value = -20", block(body, "accept_effect"))
        self.assertIn("country_liberty_desire_add = 0.10", block(block(body, "pact"), "second_modifier"))
        self.assertIn("is_direct_subject_of = root", block(block(body, "pact"), "requirement_to_maintain"))
        self.assertIn("always = no", block(block(body, "ai"), "will_propose"))

    def test_action_loc(self):
        a = "nd_withdraw_umbrella_action"
        needed = {a, a + "_desc", a + "_action_propose_name", a + "_action_break_name", a + "_pact_desc",
                  a + "_action_notification_name", a + "_action_notification_desc",
                  a + "_action_notification_break_name", a + "_action_notification_break_desc"}
        self.assertFalse(sorted(needed - loc_keys()))

    def test_panel_line(self):
        self.assertIn("nd_umbrella_sgui", read(GUI))
        self.assertIn("is_valid = { always = no }", block(strip_comments(read(SGUIS)), "nd_umbrella_sgui"))
        self.assertRegex(strip_comments(read(VALUES)), r"(?m)^nd_display_umbrella_count = \{")
```

- [ ] **Step 2: Run** — fail.

- [ ] **Step 3: The action**

```
# ============================================================================
# NUCLEAR UMBRELLA — withdrawing it from a subject (spec 2026-09-25 §1.3)
# ============================================================================
# An armed overlord's direct subjects are under its nuclear umbrella by
# default (nd_under_an_umbrella, nuclear_deterrence_triggers.txt). This pact is
# the withdrawal: while it stands the subject is not covered and its liberty
# desire grows 0.1 a week (vanilla Raise Subject Payments' rate); making it
# costs +10 liberty desire at once (law imposition's size) and 20 relations.
# Breaking it — "Restore Nuclear Umbrella" — is free and restores coverage.
# The AI never withdraws, and restores any withdrawal it inherits.
# Precedent for an overlord action without a DLC gate: annex_subject_peaceful
# (extra_diplo_actions.txt).
# ============================================================================
nd_withdraw_umbrella_action = {
	groups = {
		overlord
	}
	requires_approval = no
	show_confirmation_box = yes
	show_in_lens = no

	texture = "gfx/interface/icons/diplomatic_action_icons/exempt_from_service.dds"

	potential = {
		has_game_rule = nuclear_weapons_enabled
		scope:target_country = {
			is_direct_subject_of = root
		}
	}

	possible = {
		custom_tooltip = {
			text = nd_tt_umbrella_needs_arsenal
			nd_believed_armed = yes
		}
	}

	accept_effect = {
		custom_tooltip = nd_tt_umbrella_withdrawn
		scope:target_country = {
			add_liberty_desire = 10
			change_relations = { country = root value = -20 }
		}
	}

	pact = {
		cost = 0

		second_modifier = {
			country_liberty_desire_add = 0.10
		}

		second_country_gets_income_transfer = no
		income_transfer_based_on_second_country = no

		actor_can_break = {
			always = yes
		}

		requirement_to_maintain = {
			trigger = {
				scope:target_country = {
					is_direct_subject_of = root
				}
			}
		}
	}

	ai = {
		evaluation_chance = {
			value = 0
		}
		propose_score = {
			value = 0
		}
		will_propose = {
			always = no
		}
		will_break = {
			always = yes
		}
	}
}
```

(Verify the icon path exists in vanilla `gfx/interface/icons/diplomatic_action_icons/`; if the file is absent, use `raise_payments.dds`.)

- [ ] **Step 4: Display** — values:

```
# Direct subjects under our nuclear umbrella (spec 2026-09-25 §1.6).
nd_display_umbrella_count = {
	value = 0
	every_direct_subject = {
		limit = { nd_under_an_umbrella = yes }
		add = 1
	}
}
```

(vanilla precedent for an iterator in a script value: `india_values.txt`, `every_subject_or_below = { limit … add = 1 }`.) sgui:

```
# Does anyone shelter under our umbrella? Draws the posture panel's umbrella line.
nd_umbrella_sgui = {
	scope = country
	is_shown = {
		any_direct_subject = { nd_under_an_umbrella = yes }
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = { }
}
```

Widget, in the posture summary after the authority `nd_row`:

```
		nd_row = {
			visible = "[GetScriptedGui('nd_umbrella_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
			blockoverride "row_label" {
				text = "nd_w_umbrella_label"
			}
			blockoverride "row_value" {
				text = "nd_w_umbrella_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "nd_w_umbrella_tt"
			}
		}
```

(If `nd_row` does not forward `visible`, wrap it in a `flowcontainer = { visible = … }`; check the type definition at the top of the file.)

- [ ] **Step 5: Loc** (`te_miscellaneous_l_english.yml` / diplomacy file per `organize_loc.py`)

```
 nd_withdraw_umbrella_action:0 "Withdraw Nuclear Umbrella"
 nd_withdraw_umbrella_action_desc:0 "Stop counting [TARGET_COUNTRY.GetName] under our [concept_nuclear_weapon] umbrella. An attacker will no longer fear our arsenal on their behalf, and we will no longer be asked to answer threats against them — but a [concept_subject] left to face the bomb alone will want to be free of us."
 nd_withdraw_umbrella_action_propose_name:0 "$nd_withdraw_umbrella_action$"
 nd_withdraw_umbrella_action_break_name:0 "Restore Nuclear Umbrella"
 nd_withdraw_umbrella_action_pact_desc:0 "[SCOPE.GetRootScope.GetDiplomaticPact.GetFirstCountry.GetName] has withdrawn its nuclear umbrella from [SCOPE.GetRootScope.GetDiplomaticPact.GetSecondCountry.GetName]."
 nd_withdraw_umbrella_action_action_notification_name:0 "[INITIATOR_COUNTRY.GetName] withdraws its nuclear umbrella"
 nd_withdraw_umbrella_action_action_notification_desc:0 "[INITIATOR_COUNTRY.GetName] no longer counts us under its nuclear umbrella. Our [concept_liberty_desire] grows while it stays withdrawn."
 nd_withdraw_umbrella_action_action_notification_break_name:0 "[INITIATOR_COUNTRY.GetName] restores its nuclear umbrella"
 nd_withdraw_umbrella_action_action_notification_break_desc:0 "[INITIATOR_COUNTRY.GetName] counts us under its nuclear umbrella again."
 nd_tt_umbrella_needs_arsenal:0 "We have tested a nuclear weapon"
 nd_tt_umbrella_withdrawn:0 "They are no longer under our nuclear umbrella: no relief from the nuclear shadow on their war support, no protection counted in a crisis against them, and we are not asked to answer threats against them. While this stands their #v liberty desire#! grows by #R 0.1#! a week"
 nd_w_umbrella_label:0 "Nuclear umbrella"
 nd_w_umbrella_value:0 "#v [JournalEntry.GetCountry.MakeScope.ScriptValue('nd_display_umbrella_count')|0]#! subjects"
 nd_w_umbrella_tt:0 "#tooltip_header Nuclear umbrella#!\n$TOOLTIP_DELIMITER$\nOur direct subjects count as under our nuclear guarantee without a treaty: an attacker's war support suffers our arsenal's shadow and not theirs, a crisis against them weighs our arsenal, and we are asked to answer when they are threatened or struck. A nuclear strike on one of them lets us retaliate under any doctrine. Withdrawing it is a diplomatic action on the subject: #R +10#! liberty desire at once and more every week while it stands."
```

- [ ] **Step 6: Run tests, `python3 organize_loc.py`, rerun tests** → OK; BOM check on the new file (`head -c3 | xxd`).

- [ ] **Step 7: Commit** — `git commit -m "Nuclear umbrella: withdraw it from a subject at a liberty-desire cost; the panel counts it"`.

---

### Task 6: Extended deterrence — a strike on someone we cover licenses us and pulls us in

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_was_struck_by`; new `nd_covered_country_struck_by`, `nd_covered_country_struck`; `nd_war_law_exception`)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_guarantee_act_honour`, `nd_guarantee_act_retaliate`; new `nd_guarantor_join_war`, `nd_guarantor_schedule_answer`)
- Modify: `events/nuclear_crisis_events.txt` (`.20.b` trigger; new hidden `.22`)
- Modify: loc
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: `nd_under_an_umbrella`, `nd_forces_assembled`.
- Produces: `nd_covered_country_struck_by = { ENEMY }`; variable `nd_answer_strike_target`; event `nuclear_crisis.22` (hidden).

- [ ] **Step 1: Failing tests**

```python
class TestExtendedDeterrence(unittest.TestCase):
    def setUp(self):
        self.t = strip_comments(read(TRIGGERS))
        self.c = strip_comments(read(CRISIS_EFFECTS))
        self.ev = strip_comments(read(CRISIS_EVENTS))

    def test_strike_on_covered_country_licenses(self):
        self.assertIn("nd_covered_country_struck_by = { ENEMY = $ENEMY$ }", block(self.t, "nd_was_struck_by"))
        body = block(self.t, "nd_covered_country_struck_by")
        self.assertIn("nd_under_an_umbrella = yes", body)
        self.assertIn("has_type = nuclear_guarantee", body)
        self.assertIn("nd_covered_country_struck = yes", block(self.t, "nd_war_law_exception"))

    def test_retaliate_no_longer_needs_our_doctrine_or_a_prior_war(self):
        opt = option_body(self.ev, "nuclear_crisis.20.b")
        trig = block(opt, "trigger")
        self.assertNotIn("nd_doctrine_permits_strike", trig)
        self.assertNotIn("has_war_with = scope:nd_guarantee_attacker", trig.split("scope:nd_guarantee_beneficiary")[0])
        self.assertIn("nd_forces_assembled = yes", trig)

    def test_answering_joins_the_war_then_strikes_only_at_war(self):
        self.assertIn("join_war", block(self.c, "nd_guarantor_join_war"))
        for act in ("nd_guarantee_act_honour", "nd_guarantee_act_retaliate"):
            self.assertIn("nd_guarantor_join_war = yes", block(self.c, act), act)
        self.assertIn("id = nuclear_crisis.22", block(self.c, "nd_guarantor_schedule_answer"))
        hidden = block(self.ev, "nuclear_crisis.22")
        self.assertIn("hidden = yes", hidden)
        self.assertIn("has_war_with = var:nd_answer_strike_target", hidden)
        self.assertIn("nuclear_response_strike = yes", hidden)
```

- [ ] **Step 2: Run** — fail.

- [ ] **Step 3: Triggers**

`nd_was_struck_by`'s OR gains, as its last member:

```
		# A country we cover — a treaty beneficiary or a subject under our
		# umbrella — was struck by them (spec 2026-09-25 §1.5). Answering a
		# nuclear strike on a protected country is not first use, under any
		# doctrine.
		nd_covered_country_struck_by = { ENEMY = $ENEMY$ }
```

New:

```
# Did $ENEMY$ strike a country we cover? The struck country's
# nuked_by_country (set by both strike kinds) names the last striker.
nd_covered_country_struck_by = {
	save_temporary_scope_as = nd_ccs_self
	OR = {
		any_direct_subject = {
			nd_under_an_umbrella = yes
			has_variable = nuked_by_country
			var:nuked_by_country ?= $ENEMY$
		}
		any_scope_treaty = {
			any_scope_article = {
				has_type = nuclear_guarantee
				source_country = scope:nd_ccs_self
				target_country = {
					has_variable = nuked_by_country
					var:nuked_by_country ?= $ENEMY$
				}
			}
		}
	}
}

# The Rules of War law yields to retaliation for a covered country as it
# does for our own cities (nd_war_law_exception): a country we cover carries
# a fresh strike's aftermath.
nd_covered_country_struck = {
	save_temporary_scope_as = nd_ccs2_self
	OR = {
		any_direct_subject = {
			nd_under_an_umbrella = yes
			any_scope_state = {
				OR = {
					has_modifier = nuclear_strike_aftermath
					has_modifier = tactical_nuke_aftermath
				}
			}
		}
		any_scope_treaty = {
			any_scope_article = {
				has_type = nuclear_guarantee
				source_country = scope:nd_ccs2_self
				target_country = {
					any_scope_state = {
						OR = {
							has_modifier = nuclear_strike_aftermath
							has_modifier = tactical_nuke_aftermath
						}
					}
				}
			}
		}
	}
}
```

`nd_war_law_exception`'s OR gains `nd_covered_country_struck = yes`.

- [ ] **Step 4: Effects**

```
# Enter the beneficiary's war with the attacker, on the beneficiary's side
# (spec 2026-09-25 §1.5: a strike on someone we protect pulls us in). Visible:
# the engine's join_war line renders in the option. Guarantor scope, ROOT =
# the guarantor (nuclear_crisis.20). Precedent: world_war_events.txt.
nd_guarantor_join_war = {
	if = {
		limit = {
			exists = scope:nd_guarantee_attacker
			exists = scope:nd_guarantee_beneficiary
			NOT = { has_war_with = scope:nd_guarantee_attacker }
			scope:nd_guarantee_beneficiary = { has_war_with = scope:nd_guarantee_attacker }
		}
		custom_tooltip = nd_tt_guarantee_join_war
		scope:nd_guarantee_beneficiary = {
			every_scope_war = {
				limit = { is_war_participant = scope:nd_guarantee_attacker }
				join_war = {
					target = root
					side = scope:nd_guarantee_beneficiary
				}
			}
		}
	}
}

# The strike itself waits a day (nuclear_crisis.22), so it runs only once we
# are actually at war with the attacker — join_war's effect on has_war_with
# inside the same effect is unverified, and a refused join must not become a
# strike on a country we are not fighting.
nd_guarantor_schedule_answer = {
	custom_tooltip = {
		text = nd_tt_guarantor_answer_strike
		set_variable = { name = nd_answer_strike_target value = scope:nd_guarantee_attacker }
	}
	hidden_effect = {
		trigger_event = { id = nuclear_crisis.22 days = 1 }
	}
}
```

`nd_guarantee_act_honour`: the context-2 ultimatum `if` becomes an `else_if` after a new first branch:

```
	if = {
		limit = {
			exists = scope:nd_guarantee_attacker
			exists = scope:nd_guarantee_beneficiary
			var:nd_guarantee_context = 2
			scope:nd_guarantee_beneficiary = { has_war_with = scope:nd_guarantee_attacker }
		}
		nd_guarantor_join_war = yes
	}
	else_if = { … the existing ultimatum branch, unchanged … }
```

`nd_guarantee_act_retaliate`:

```
nd_guarantee_act_retaliate = {
	custom_tooltip = nd_tt_guarantee_retaliate
	custom_tooltip = {
		text = nd_tt_credibility_up_10
		nd_change_credibility = { AMOUNT = 10 }
	}
	nd_guarantor_join_war = yes
	if = {
		limit = { exists = scope:nd_guarantee_attacker }
		nd_guarantor_schedule_answer = yes
	}
	hidden_effect = {
		scope:nd_guarantee_beneficiary ?= {
			set_variable = { name = nd_guarantee_answer value = 1 }
			trigger_event = { id = nuclear_crisis.21 }
		}
	}
}
```

- [ ] **Step 5: Events** — `.20.b` trigger:

```
		trigger = {
			var:nd_guarantee_context = 2
			nd_is_armed = yes
			nd_forces_assembled = yes
			scope:nd_guarantee_beneficiary = { has_war_with = scope:nd_guarantee_attacker }
			nd_pledge_permits_strike = { ENEMY = scope:nd_guarantee_attacker }
			nd_war_law_permits_strategic_strike = yes
		}
```

and its comment: "Answer the strike in kind (spec 2026-09-25 §1.5): after a strike, under any doctrine — a strike on someone we cover is not ours to start — joining their war first if we are not in it; the strike follows a day later through .22." `.22`, after `.21`:

```
# ---- .22 Hidden: the guarantor's answer lands ------------------------------------
# A day after "answer in kind" (.20.b, nd_guarantor_schedule_answer): strike
# the attacker named in nd_answer_strike_target once, as retaliation
# (nuclear_response_strike, not a first strike), but only if we are at war
# with it by now — the join may have been refused.
nuclear_crisis.22 = {
	type = country_event
	hidden = yes

	trigger = {
		has_variable = nd_answer_strike_target
	}

	immediate = {
		if = {
			limit = {
				exists = var:nd_answer_strike_target
				has_war_with = var:nd_answer_strike_target
				nd_is_armed = yes
				nd_forces_assembled = yes
			}
			save_scope_as = target_country
			var:nd_answer_strike_target = {
				save_scope_as = attacking_country
				ordered_scope_state = {
					order_by = nuclear_industrial_strike_target_score
					position = 0
					nuclear_response_strike = yes
				}
			}
			nd_record_nuclear_use = { VICTIM = scope:attacking_country }
		}
		remove_variable = nd_answer_strike_target
	}
}
```

- [ ] **Step 6: Loc**

```
 nd_tt_guarantee_join_war:0 "#R We enter the war#! against [SCOPE.sCountry('nd_guarantee_attacker').GetName] on [SCOPE.sCountry('nd_guarantee_beneficiary').GetName]'s side"
 nd_tt_guarantor_answer_strike:0 "#R A day from now, if we are at war with [SCOPE.sCountry('nd_guarantee_attacker').GetName], one of our warheads falls on their most important city.#! It counts as retaliation, not a first strike"
```
Changed `nd_tt_guarantee_honour`: "We stand with them publicly: their attacker faces our guarantee, and our #v credibility#! rises" (unchanged text; the join line renders separately). `nuclear_crisis.20.b` loc gets its wording checked to not say "we are at war".

- [ ] **Step 7: Run tests** → OK; `test_every_crisis_strike_option_checks_the_law` still passes (`.20.b` keeps the law line).

- [ ] **Step 8: Commit** — `git commit -m "Nuclear guarantee: a strike on a covered country licenses retaliation under any doctrine and pulls the guarantor into the war"`.

---

### Task 7: Harness, rates, docs, full verification, PR

**Files:**
- Modify: `events/te_debug_deterrence_events.txt` (`.1` gains Recessed and Automatic Retaliation options; `.1.c` adds `mainframe_computers`). No subject harness: putting a country under the player needs a war or vanilla tooling, so §0.9 describes the manual path.
- Modify: `scripts/analysis/nuclear_incident_rates.py` (Recessed rows)
- Modify: `docs/systems/nuclear_crisis_design.md` (§0.2, §0.3, §0.4 table, §0.5, §0.9 items 30+), `docs/systems/journal_entry_systems.md` (op table, CRLF), the spec (note the kept trigger name `nd_dispute_guarantee_against`)
- Loc for new harness options

- [ ] **Step 1: Harness** — `.1` gains:

```
	# Readiness straight to Recessed: every launch is greyed until Routine.
	option = {
		name = te_debug_deterrence.1.f
		if = {
			limit = { nd_is_initialized = yes }
			set_variable = { name = nd_readiness value = 0 }
			set_variable = { name = nd_readiness_target value = 0 }
			nd_apply_posture_modifiers = yes
		}
	}

	# Automatic Retaliation now, technology and tenure included.
	option = {
		name = te_debug_deterrence.1.g
		add_technology_researched = radar
		add_technology_researched = ICBMs
		add_technology_researched = mainframe_computers
		if = {
			limit = { nd_is_initialized = yes }
			nd_set_authority_4 = yes
		}
	}
```

`.1.c` also adds `mainframe_computers`. Loc: `te_debug_deterrence.1.f:0 "Recessed at once (warheads in storage)"`, `te_debug_deterrence.1.g:0 "Automatic Retaliation at once"`. Update the file header's `.1` line.

- [ ] **Step 2: Rates script** — `READINESS_NAMES[0] = "Recessed"`, `BASE_PERMILLE[0] = 0.5`, loop `for readiness in (0, 1, 2, 3)`; strain step for 0 is −6 (the `else` branch already). Run it; paste the new table into §0.4 and add one sentence: "Recessed halves Routine's odds; Automatic Retaliation adds no peacetime launch risk (its accident branch needs a war or an acute crisis)."

- [ ] **Step 3: Docs** — §0.2: "`nd_readiness` 0–3 (0 Recessed)", "`nd_authority` 1–4 (4 Automatic Retaliation)", a Recessed paragraph and an Automatic Retaliation paragraph (the §2.2/§3 facts), the upkeep table's custody row "0.1 at Recessed" and "Automatic Retaliation 3"; §0.3: the new `nd_yp_recessed` part and the Automatic Retaliation answer term; §0.4: incident odds line and `.30` system branch; §0.5: "The nuclear umbrella" subsection (coverage, withdrawal pact, abandonment, licence, joining, `.22`); §0.9 items:
  30. A subject of an armed overlord is spared the nuclear shadow and its overlord gets `.20` when it is warned or struck; an overlord that also signed it a treaty gets one `.20`, not two.
  31. "Withdraw Nuclear Umbrella" appears on a direct subject, shows +10 liberty desire and −20 relations; the pact shows +0.1 liberty desire/week; "Restore Nuclear Umbrella" ends it.
  32. Under Existential Deterrence, a strike on a covered country offers `.20` Retaliate; choosing it (or Honour) while not in the war puts us in it (and whether a truce blocks `join_war`); the strike lands a day later only if we are then at war.
  33. At Recessed, the strike actions and every retaliation option are greyed with the storage reason; being struck offers "Mate the warheads"; `.24` arrives the week readiness reaches Routine.
  34. Under Automatic Retaliation, `.1` has a single option and three warheads fly; a second first strike by the same country within six months gets the normal choices; `.11` never answers by itself.
  35. A `.30` bomber or silo accident under Automatic Retaliation in a war rolls the hold and, unheld, launches through `nd_launch_or_intercept` with the `.2` "system" text.
  `journal_entry_systems.md`: ops `| 20–23 |` and `| 31–34 |` rows.

- [ ] **Step 4: Full verification** (worktree; dummy env for the suite)

```bash
python3 -m unittest test_nuclear_deterrence -v 2>&1 | tail -3
VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent \
VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent \
  sh -c "ls test_*.py | grep -v test_reload_post_load | sed 's/\.py$//' | xargs python3 -m unittest 2>&1 | tail -3"
ruff check .
python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt' '*.gui')
python3 scripts/analysis/check_localization_files.py
for a in duplicate_key any_limit loc_render orphaned_event iterator_limit modifier_multiplier_var event_image \
         treaty_leverage_side event_context silent_variable prev_scope; do python3 -m ${a}_audit --strict || echo "FAIL $a"; done
```

(Use the exact module paths CI uses — read `.github/workflows/ci.yml` for them.) Then a second mod-state server from the worktree on another port (`docs/guides/python_tools.md` § Starting the Server), `POST /reload?mod_only=true&audits_only=true`, and read `warnings`, `parse_failures`.

- [ ] **Step 5: Commit docs/harness**, push `git push -u origin nuclear-umbrella-deadhand`, open the PR with `--base main` (body written to a file first; `Closes` nothing; owner-away calls listed; §0.9 items 30–35 as the play-test list).

- [ ] **Step 6: Independent review** — a fresh reviewer agent reads the spec, the plan and `git diff origin/main`, reports findings; fix what survives verification; push.
