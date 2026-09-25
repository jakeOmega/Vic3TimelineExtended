# Nuclear Crisis Communication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the nuclear crisis system say what it does (action preview, act tooltips, outcome notice, crisis panel), price bluffs, close the crisis-strike war-law hole, and rebuild "At Home" as per-interest-group opinions classed by Rules of War stance.

**Architecture:** Paradox script (Clausewitz) in `common/`, `events/`, `gui/`, `localization/`, guarded by structural Python unit tests in `test_nuclear_deterrence.py` (no game needed) and by the mod state server's post-load audits. Every displayed number is either stored by script (crisis figure components, per-IG opinion terms) and printed by a display scripted GUI, or a literal in loc pinned to its script constant by a unit test.

**Tech Stack:** Victoria 3 script (scripted effects/triggers/values, customizable localization, scripted GUIs, `.gui`), YAML localization, Python 3 `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-25-nuclear-crisis-communication-design.md` (read it first; §-references below are to it). Background: `docs/systems/nuclear_crisis_design.md` §0.

## Global Constraints

- Work only in the worktree `~/src/vic3te-nuclear-comms` (branch `nuclear-crisis-communication` for PR 1; `nuclear-at-home`, cut from PR 1's tip, for PR 2). Never `POST /reload` the main server (port 8950) from here; reload-check on a second server (Task 8, Task 11).
- Brace-based Paradox files use **tabs**; run `python3 scripts/format_paradox_tabs.py <files>` on every `.txt`/`.gui` you touch.
- Every touched `.txt`, `.gui`, `.yml` keeps its **UTF-8 BOM** (check: `head -c3 <file> | xxd` shows `efbbbf`).
- Loc formatting: `#v …#!`, `#R …#!`, `#G …#!`, `#Y …#!`, `#lore …#!`, `#tooltip_header …#!`, `$TOOLTIP_DELIMITER$`. **Never** `[b]…[/b]`.
- New `nd_*` loc keys go in `localization/english/te_miscellaneous_l_english.yml`; `nuclear_crisis.*` event keys in `te_events_l_english.yml`. Every new loc key must appear **literally** in a `.txt`/`.gui` file — no `$PARAM$`-built keys or script-value names (`organize_loc.py` only sees literal tokens; a built name strands its key in `te_unused_l_english.yml`). Run `python3 organize_loc.py` after adding keys.
- Custom-localization target keys (`localization_key = X`) are plain text: **no** `[…]` accessors inside them (gui_modding_guide.md gotcha #20).
- Tooltip previews run effects without running them: `save_scope_as` does not run, so scopes saved inside an effect do not exist in its own tooltip. Preview-visible lines may read only ROOT/THIS, the scopes the caller already has (`scope:target_country`; an event's saved scopes), and variables.
- A write to a variable the UI reads, inside an event option, must sit in a `custom_tooltip = { text = <key with the number> … }` (silent_variable_audit, `--strict` in CI).
- Script-built text (display scripted GUIs printed with `ExecuteTooltip`) prints a scope's own lines before lines from nested scopes (gotcha #18): keep line order at one scope level.
- Unit tests: `python3 -m unittest test_nuclear_deterrence -v` (no game, no server). **Rerun them after tab-formatting**, before each commit: some tests match exact text.
- Scripted-trigger parameters (`nuclear_deterrence_triggers.txt` header): **never pass `PREV` or a bare `var:`** as a parameter — they are substituted textually and change meaning inside the trigger's own scope changes. Save a temporary scope (`save_temporary_scope_as`, which does run inside a `limit` in a tooltip preview) and pass that. **`is_losing_war_against` reads ROOT** as the country asked; do not call it from a scope that is not ROOT.
- Commit by path, never `git commit -a`. End every commit message with:
  ```
  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk
  ```
- `docs/systems/journal_entry_systems.md` is **CRLF**: edit with `Edit` only, then confirm `grep -c $'\r$'` equals `wc -l`.

## Review Focus

1. **A crisis already open in a save made before this update** has no `nd_ft_reason`, no `nd_cd_*`/`nd_yp_*` components and no pending record. The panel must print nothing for missing parts (no "Failed to fetch variable"), and a closing crisis must still notify. Pinned by Task 7's `test_breakdown_lines_guard_their_variable` and Task 4's `test_outcome_option_guards_pending`.
2. **A non-nuclear target** (no posture variables): every figure and custom-loc read has a `has_variable` guard or `_or_default` value, and every custom-loc block ends in an unconditional fallback. Pinned by Task 7's `test_new_custom_loc_blocks_have_fallbacks`.
3. **Two closes before one click** (a second crisis closes before the first outcome notice is answered): the first record is flushed, never lost or applied twice. Pinned by Task 4's `test_close_flushes_before_recording`.
4. **Hovering an action that is not possible** (target already in another crisis): the preview must read nothing from a crisis record. Pinned by Task 5's `test_preview_reads_no_crisis_scopes`.
5. **Outcome 9** (a party vanished): no pending record, no notice. Pinned by Task 4's `test_outcome_nine_records_nothing`.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `common/scripted_triggers/nuclear_deterrence_triggers.txt` | war-law gate; follow-through; either-role crisis questions; IG classes | 1, 2, 3, 6, 7, 9, 10 |
| `common/scripted_effects/nuclear_crisis_effects.txt` | classification, figure refresh, preview, acts, pending outcomes | 2, 3, 4, 5, 6 |
| `common/scripted_effects/nuclear_deterrence_effects.txt` | per-IG opinion storage, band, At Home lines, site switches | 9, 10, 11 |
| `common/script_values/nuclear_deterrence_values.txt` | pressure/danger components; display values; IG terms | 3, 7, 10 |
| `common/scripted_guis/nuclear_deterrence_sguis.txt` | display handlers: role rows, breakdowns, next pressure, At Home list | 7, 11 |
| `common/customizable_localization/nuclear_deterrence_custom_loc.txt` | role-aware words; concession; follow-through; stakes | 4, 7, 11 |
| `common/diplomatic_actions/nuke.txt` | strike actions call the shared law gate | 1 |
| `events/nuclear_crisis_events.txt` | strike options gated by law; `.6` applies consequences | 1, 4 |
| `events/nuclear_incident_events.txt` | IG reward sites switch triggers | 9 |
| `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` | crisis panel rows; At Home list | 7, 11 |
| `localization/english/te_miscellaneous_l_english.yml`, `te_events_l_english.yml` | text | all |
| `test_nuclear_deterrence.py` | structural guards | all |
| docs (`nuclear_crisis_design.md`, `mod_systems.md`, `journal_entry_systems.md`, `scripting_best_practices.md`) | record what shipped | 8, 11 |

---

# PR 1 — the crisis (§1–§3)

### Task 1: One war-law gate for every nuclear strike

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (insert after the `nd_doctrine_permits_strike = { … }` block, before `# A bilateral non-use pledge with $TARGET$ is in force.`)
- Modify: `common/diplomatic_actions/nuke.txt:31-60` and `:206-231`
- Modify: `events/nuclear_crisis_events.txt` (`.4.g`, `.7.a`, `.20.b` option triggers)
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Produces: `nd_war_law_permits_strategic_strike = yes`, `nd_war_law_permits_tactical_strike = yes`, `nd_war_law_exception = yes` (country scope, no parameters). Task 2 uses the strategic gate.

- [ ] **Step 1: Write the failing test**

Add near the top of `test_nuclear_deterrence.py`, after `LENS_ICONS`:

```python
NUKE = ROOT / "common/diplomatic_actions/nuke.txt"
```

and extend `SCRIPT_FILES` so the loc tests see `nuke.txt`:

```python
SCRIPT_FILES = (EFFECTS, CRISIS_EFFECTS, TRIGGERS, ACTIONS, ARTICLE, JE, SGUIS,
                CRISIS_EVENTS, INCIDENT_EVENTS, DEBUG_EVENTS, NUKE)
```

Add the helper and class before `class TestManagedFamilies`:

```python
def option_body(text, option_name):
    """The body of the `option = { … }` whose `name` is option_name."""
    m = re.search(r"name = " + re.escape(option_name) + r"\s", text)
    if not m:
        raise AssertionError(f"{option_name} not found")
    start = text.rfind("option = {", 0, m.start())
    return block(text[start:], "option")


class TestWarLawGate(unittest.TestCase):
    def test_gate_triggers_exist(self):
        t = read(TRIGGERS)
        for name in ("nd_war_law_permits_strategic_strike",
                     "nd_war_law_permits_tactical_strike",
                     "nd_war_law_exception"):
            self.assertRegex(t, rf"(?m)^{name} = \{{")

    def test_strike_actions_use_the_shared_gate(self):
        text = strip_comments(read(NUKE))
        self.assertNotIn("has_law = law_type:law_limited_war", text)
        self.assertIn("nd_war_law_permits_strategic_strike = yes", block(text, "nuke_diplo_action"))
        self.assertIn("nd_war_law_permits_tactical_strike = yes", block(text, "tactical_nuke_diplo_action"))

    def test_every_crisis_strike_option_checks_the_law(self):
        text = strip_comments(read(CRISIS_EVENTS))
        for opt in ("nuclear_crisis.4.g", "nuclear_crisis.7.a", "nuclear_crisis.20.b"):
            self.assertIn("nd_war_law_permits_strategic_strike = yes", option_body(text, opt), opt)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestWarLawGate -v`
Expected: 3 FAIL (`nd_war_law_permits_strategic_strike not found`-style assertion messages).

- [ ] **Step 3: Add the triggers**

Insert into `nuclear_deterrence_triggers.txt` after the closing `}` of `nd_doctrine_permits_strike`:

```
# The Rules of War gate on a nuclear strike, shared by the strike actions
# (nuke.txt) and every crisis option that can end in a strike (.4.g, .7.a,
# .20.b), which used to skip it. Country scope. Humanitarian Regulations and
# Limited War forbid a strategic strike and Limited War a tactical one, unless
# nd_war_law_exception holds. A threat the law forbids carrying out is a bluff
# (nd_threat_law_permits).
nd_war_law_permits_strategic_strike = {
	OR = {
		NOT = {
			OR = {
				has_law = law_type:law_humanitarian_regulations
				has_law = law_type:law_limited_war
			}
		}
		nd_war_law_exception = yes
	}
}

nd_war_law_permits_tactical_strike = {
	OR = {
		NOT = { has_law = law_type:law_limited_war }
		nd_war_law_exception = yes
	}
}

# Either lifts the law: we have been struck, or a war we are fighting carries an
# annexation-type war goal against us.
nd_war_law_exception = {
	save_temporary_scope_as = nd_wl_self
	OR = {
		any_scope_state = {
			OR = {
				has_modifier = nuclear_strike_aftermath
				has_modifier = tactical_nuke_aftermath
			}
		}
		any_scope_war = {
			is_target_of_wargoal_in_war = scope:nd_wl_self
			OR = {
				has_war_goal = make_protectorate
				has_war_goal = make_dominion
				has_war_goal = make_tributary
				has_war_goal = make_personal_union
				has_war_goal = make_crown_land
				has_war_goal = make_chartered_company
				has_war_goal = annex_country
				has_war_goal = te_reunify_country
			}
		}
	}
}
```

- [ ] **Step 4: Replace the two blocks in `nuke.txt`**

In `nuke_diplo_action`'s `possible`, replace the whole block from `		OR = {` / `			# Normal: can use if no humanitarian/limited war laws` through its closing `		}` (lines 31–60) with:

```
		custom_tooltip = {
			text = nd_tt_war_law_permits_strike
			nd_war_law_permits_strategic_strike = yes
		}
```

In `tactical_nuke_diplo_action`, replace the block from `		OR = {` / `			# Normal: can use if no limited war law` through its closing `		}` (lines 206–231) with:

```
		custom_tooltip = {
			text = nd_tt_war_law_permits_tactical_strike
			nd_war_law_permits_tactical_strike = yes
		}
```

- [ ] **Step 5: Gate the three crisis strike options**

In `events/nuclear_crisis_events.txt`, add one line to each option's `trigger`:
- `.4.g` (option `name = nuclear_crisis.4.g`): after `nd_pledge_permits_strike = { ENEMY = scope:nd_target }` add `nd_war_law_permits_strategic_strike = yes`.
- `.7.a`: same place, same line.
- `.20.b`: after `nd_pledge_permits_strike = { ENEMY = scope:nd_guarantee_attacker }` add `nd_war_law_permits_strategic_strike = yes`.

- [ ] **Step 6: Loc**

Add to `te_miscellaneous_l_english.yml` (any position; `organize_loc.py` sorts):

```yaml
 nd_tt_war_law_permits_strike:0 "Our #v Rules of War#! law permits a nuclear strike — neither Humanitarian Regulations nor Limited War — unless we have been struck, or face annexation in this war"
 nd_tt_war_law_permits_tactical_strike:0 "Our #v Rules of War#! law is not Limited War — unless we have been struck, or face annexation in this war"
```

- [ ] **Step 7: Run tests**

Run: `python3 -m unittest test_nuclear_deterrence -v`
Expected: all PASS (including the existing loc tests, which now scan `nuke.txt`).

- [ ] **Step 8: Tab-format and commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_triggers/nuclear_deterrence_triggers.txt common/diplomatic_actions/nuke.txt events/nuclear_crisis_events.txt
git add common/scripted_triggers/nuclear_deterrence_triggers.txt common/diplomatic_actions/nuke.txt events/nuclear_crisis_events.txt localization/english/te_miscellaneous_l_english.yml test_nuclear_deterrence.py
git commit -m "Nuclear crisis: crisis strike options respect the Rules of War law" -m "The deadline strike (.4.g), 'they chose war' (.7.a) and a guarantor's retaliation (.20.b) checked doctrine and pledges but not the war-law gate the strike actions enforce, so a country under Limited War could strike through a crisis. The gate is now one trigger family both paths call.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

---

### Task 2: Follow-through — backed, uncertain or a bluff

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (new block after Task 1's gate; AI triggers `nd_ai_would_warn`, `nd_ai_would_issue_ultimatum`)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (new effect after `nd_crisis_classify_dispute`)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: `nd_war_law_permits_strategic_strike` (Task 1).
- Produces (issuer scope, `$TARGET$` = the threatened country): triggers `nd_threat_bluff_nfu`, `nd_threat_law_permits`, `nd_threat_existential_stake`, `nd_threat_backed`, `nd_threat_uncertain`, `nd_enemy_threatens_existence_in_play = { ENEMY }`; effect `nd_crisis_classify_follow_through = { TARGET = X }` writing `nd_ft_reason` on the issuer:

| `nd_ft_reason` | meaning | level |
|---|---|---|
| 1 | at war, doctrine permits a strike now | backed |
| 2 | Compellence or higher (defiance licenses it) | backed |
| 3 | not at war, Flexible first use | uncertain |
| 4 | not at war, Existential with a stake | uncertain |
| 5 | doctrine does not allow it | bluff |
| 6 | the Rules of War law forbids it | bluff |
| 7 | No First Use | bluff |

- [ ] **Step 1: Write the failing test**

```python
class TestFollowThrough(unittest.TestCase):
    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_triggers_exist(self):
        for name in ("nd_threat_bluff_nfu", "nd_threat_law_permits", "nd_threat_existential_stake",
                     "nd_threat_backed", "nd_threat_uncertain", "nd_enemy_threatens_existence_in_play"):
            self.assertRegex(self.triggers, rf"(?m)^{name} = \{{")

    def test_classification_writes_every_reason_once(self):
        body = block(self.effects, "nd_crisis_classify_follow_through")
        codes = re.findall(r"name = nd_ft_reason value = (\d)", body)
        self.assertEqual(sorted(codes), [str(c) for c in range(1, 8)])

    def test_ai_never_bluffs_in_public(self):
        self.assertIn("nd_threat_backed = { TARGET = $TARGET$ }",
                      block(self.triggers, "nd_ai_would_issue_ultimatum"))

    def test_ai_bluffs_in_private_only_when_aggressive(self):
        warn = block(self.triggers, "nd_ai_would_warn")
        self.assertRegex(warn, r"OR = \{\s*nd_threat_backed = \{ TARGET = \$TARGET\$ \}\s*ruler_is_aggressive = yes\s*\}")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestFollowThrough -v`
Expected: 4 FAIL.

- [ ] **Step 3: Add the triggers**

Insert after Task 1's `nd_war_law_exception` block:

```
# ----------------------------------------------------------------------------
# FOLLOW-THROUGH — can the threatening side carry its threat out? (2026-09-25
# spec §1.1). Issuer scope; $TARGET$ is the country threatened. Written for a
# tooltip preview as well as a live crisis: they read only ROOT-side state and
# $TARGET$. nd_crisis_classify_follow_through records which branch held
# (nd_ft_reason); the pressure on the target reads that record.
# ----------------------------------------------------------------------------

# $ENEMY$'s side in a diplomatic play holds an annexation-type goal against us —
# nd_enemy_threatens_existence's goal list, for a play not yet a war.
nd_enemy_threatens_existence_in_play = {
	$ENEMY$ = {
		OR = {
			play_side_has_war_goal_of_type_against = { type = annex_country target = PREV }
			play_side_has_war_goal_of_type_against = { type = te_reunify_country target = PREV }
			play_side_has_war_goal_of_type_against = { type = make_protectorate target = PREV }
			play_side_has_war_goal_of_type_against = { type = make_dominion target = PREV }
			play_side_has_war_goal_of_type_against = { type = make_tributary target = PREV }
			play_side_has_war_goal_of_type_against = { type = make_personal_union target = PREV }
			play_side_has_war_goal_of_type_against = { type = make_crown_land target = PREV }
			play_side_has_war_goal_of_type_against = { type = make_chartered_company target = PREV }
		}
	}
}

# No First Use, and they have not struck us (retaliation is allowed under
# every doctrine).
nd_threat_bluff_nfu = {
	nd_doctrine_nfu = yes
	NOT = { nd_was_struck_by = { ENEMY = $TARGET$ } }
}

# The Rules of War law would let us carry it out: in a war, the strike gate
# itself; in a play, the law, or an annexation-type goal against us in it.
nd_threat_law_permits = {
	OR = {
		nd_war_law_permits_strategic_strike = yes
		nd_enemy_threatens_existence_in_play = { ENEMY = $TARGET$ }
	}
}

# Existential deterrence has something to deter here: a country we guarantee,
# our core, or our existence.
nd_threat_existential_stake = {
	OR = {
		nd_dispute_guarantee_against = { TARGET = $TARGET$ }
		nd_core_threatened_by = { ENEMY = $TARGET$ }
		nd_enemy_threatens_existence_in_play = { ENEMY = $TARGET$ }
	}
}

nd_threat_backed = {
	NOT = { nd_threat_bluff_nfu = { TARGET = $TARGET$ } }
	nd_threat_law_permits = { TARGET = $TARGET$ }
	OR = {
		AND = {
			has_war_with = $TARGET$
			nd_doctrine_permits_strike = { ENEMY = $TARGET$ }
		}
		nd_doctrine_at_least_compellence = yes
	}
}

nd_threat_uncertain = {
	NOT = { nd_threat_backed = { TARGET = $TARGET$ } }
	NOT = { nd_threat_bluff_nfu = { TARGET = $TARGET$ } }
	nd_threat_law_permits = { TARGET = $TARGET$ }
	NOT = { has_war_with = $TARGET$ }
	OR = {
		nd_doctrine_flexible = yes
		AND = {
			nd_doctrine_existential = yes
			nd_threat_existential_stake = { TARGET = $TARGET$ }
		}
	}
}
```

- [ ] **Step 4: Add the classification effect**

Insert in `nuclear_crisis_effects.txt` after the closing `}` of `nd_crisis_classify_dispute`:

```
# Issuer scope. Records which follow-through branch holds against $TARGET$
# (nd_ft_reason, table in nuclear_deterrence_triggers.txt § FOLLOW-THROUGH).
# Called by nd_crisis_refresh_figures on opening and every week, so a doctrine
# change or a war turning against us counts the same week.
nd_crisis_classify_follow_through = {
	if = {
		limit = { nd_threat_bluff_nfu = { TARGET = $TARGET$ } }
		set_variable = { name = nd_ft_reason value = 7 }
	}
	else_if = {
		limit = { NOT = { nd_threat_law_permits = { TARGET = $TARGET$ } } }
		set_variable = { name = nd_ft_reason value = 6 }
	}
	else_if = {
		limit = {
			has_war_with = $TARGET$
			nd_doctrine_permits_strike = { ENEMY = $TARGET$ }
		}
		set_variable = { name = nd_ft_reason value = 1 }
	}
	else_if = {
		limit = { nd_threat_backed = { TARGET = $TARGET$ } }
		set_variable = { name = nd_ft_reason value = 2 }
	}
	else_if = {
		limit = {
			nd_threat_uncertain = { TARGET = $TARGET$ }
			nd_doctrine_flexible = yes
		}
		set_variable = { name = nd_ft_reason value = 3 }
	}
	else_if = {
		limit = { nd_threat_uncertain = { TARGET = $TARGET$ } }
		set_variable = { name = nd_ft_reason value = 4 }
	}
	else = {
		set_variable = { name = nd_ft_reason value = 5 }
	}
}
```

- [ ] **Step 5: The AI stops bluffing in public**

In `nd_ai_would_issue_ultimatum`, add `nd_threat_backed = { TARGET = $TARGET$ }` as its second line (after `nd_ai_would_warn = { TARGET = $TARGET$ }`). The proliferation ultimatum (`nuclear_weapon_events.18` option a) zeroes its AI weight unless this trigger holds, so it inherits the rule.

In `nd_ai_would_warn`'s coercion branch (the `AND` holding `NOT = { nd_faces_retaliation_from = { ENEMY = $TARGET$ } }`), add after that line:

```
			OR = {
				nd_threat_backed = { TARGET = $TARGET$ }
				ruler_is_aggressive = yes
			}
```

- [ ] **Step 6: Run tests**

Run: `python3 -m unittest test_nuclear_deterrence -v`
Expected: all PASS.

- [ ] **Step 7: Format and commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_crisis_effects.txt
git add common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_crisis_effects.txt test_nuclear_deterrence.py
git commit -m "Nuclear crisis: classify a threat as backed, uncertain or a bluff" -m "Follow-through triggers read only issuer-side state and the target, so the action preview and the live crisis agree. The AI no longer issues a public ultimatum it could not carry out, and bluffs privately only under an aggressive ruler.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

---

### Task 3: Pressure and danger as stored, named parts

**Files:**
- Modify: `common/script_values/nuclear_deterrence_values.txt` (replace `nd_crisis_danger_value` and `nd_yield_pressure_value`, lines ~426–607)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (add `nd_crisis_danger_dampened`)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_open`, `nd_crisis_weekly_tick`, `nd_crisis_clear_vars`, new effects)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: `nd_crisis_classify_follow_through` (Task 2).
- Produces: `nd_crisis_refresh_figures = yes` (issuer scope, `scope:nd_issuer`/`scope:nd_target` saved) — the **only writer** of `nd_crisis_danger`, `nd_yield_pressure`, `nd_ft_reason`, the danger components `nd_cd_stage nd_cd_issuer_readiness nd_cd_target_readiness nd_cd_public nd_cd_counter nd_cd_reliability nd_cd_weeks nd_cd_talks nd_cd_backed nd_cd_exercise nd_cd_dampened` and the pressure components `nd_yp_base nd_yp_answer nd_yp_protector nd_yp_credibility nd_yp_alert nd_yp_danger nd_yp_exercise nd_yp_temperament nd_yp_war nd_yp_follow_through`, **all stored on both parties**. Issuer-scope script value `nd_credibility_pressure_term` (Task 5 prints it). Task 7 prints the components.

- [ ] **Step 1: Write the failing test**

```python
DANGER_PARTS = ["nd_cd_stage", "nd_cd_issuer_readiness", "nd_cd_target_readiness", "nd_cd_public",
                "nd_cd_counter", "nd_cd_reliability", "nd_cd_weeks", "nd_cd_talks", "nd_cd_backed",
                "nd_cd_exercise"]
PRESSURE_PARTS = ["nd_yp_base", "nd_yp_answer", "nd_yp_protector", "nd_yp_credibility", "nd_yp_alert",
                  "nd_yp_danger", "nd_yp_exercise", "nd_yp_temperament", "nd_yp_war",
                  "nd_yp_follow_through"]


class TestCrisisFigures(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def summed(self, total):
        body = block(self.values, total)
        return re.findall(r"(?:value|add) = (nd_(?:cd|yp)_\w+)_value\b", body)

    def test_totals_are_exactly_their_parts(self):
        self.assertEqual(self.summed("nd_crisis_danger_value"), DANGER_PARTS)
        self.assertEqual(self.summed("nd_yield_pressure_value"), PRESSURE_PARTS)

    def test_every_part_has_a_value(self):
        for part in DANGER_PARTS + PRESSURE_PARTS:
            self.assertRegex(self.values, rf"(?m)^{part}_value = \{{", part)

    def test_refresh_stores_every_part_under_its_own_value(self):
        body = block(self.effects, "nd_crisis_refresh_figures")
        stored = re.findall(r"nd_crisis_store_(?:cd|yp) = \{ C = (\w+) V = (\w+) \}", body)
        self.assertEqual([c for c, _ in stored], DANGER_PARTS + PRESSURE_PARTS)
        for c, v in stored:
            self.assertEqual(v, c + "_value")

    def test_clear_removes_every_part(self):
        body = block(self.effects, "nd_crisis_clear_figures")
        for var in DANGER_PARTS + PRESSURE_PARTS + ["nd_cd_dampened", "nd_ft_reason"]:
            self.assertIn(f"remove_variable = {var}", body, var)

    def test_losing_war_is_read_from_the_target(self):
        self.assertNotIn("is_losing_war_against", block(self.values, "nd_yp_war_value"))
        self.assertIn("nd_is_losing_war_to = { ENEMY = scope:nd_issuer }", block(self.values, "nd_yp_war_value"))
        self.assertNotIn("ROOT", block(strip_comments(read(TRIGGERS)), "nd_is_losing_war_to"))

    def test_refresh_is_the_only_writer_of_the_totals(self):
        for path in (CRISIS_EFFECTS, EFFECTS, CRISIS_EVENTS, INCIDENT_EVENTS):
            text = strip_comments(read(path))
            if path == CRISIS_EFFECTS:
                text = text.replace(block(text, "nd_crisis_refresh_figures"), "")
            self.assertNotRegex(text, r"name = nd_(?:crisis_danger|yield_pressure) value", path.name)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestCrisisFigures -v`
Expected: FAIL (`nd_crisis_refresh_figures not found`, part lists empty).

- [ ] **Step 3: Replace the two totals with their parts**

In `nuclear_deterrence_values.txt`, replace everything from the comment `# How dangerous the crisis is, 0–100` through the end of `nd_yield_pressure_value`'s block with:

```
# ----------------------------------------------------------------------------
# CRISIS FIGURES — danger and pressure, as named parts (2026-09-25 spec §1.2).
# nd_crisis_refresh_figures stores every part on both parties, so the panel's
# breakdowns print stored numbers that sum to the stored totals. Parts are
# rounded so the printed lines add up.
# ----------------------------------------------------------------------------

# ---- Danger, 0–100 (§5.1: a shared assessment, not a trigger for weapons).
# Issuer scope; needs scope:nd_target.
nd_cd_stage_value = {
	value = 0
	if = {
		limit = { has_variable = nd_crisis_stage }
		add = {
			value = var:nd_crisis_stage
			multiply = 10
		}
	}
}

nd_cd_issuer_readiness_value = {
	value = nd_readiness_or_routine
	subtract = 1
	multiply = 8
}

nd_cd_target_readiness_value = {
	value = 0
	scope:nd_target = {
		add = {
			value = nd_readiness_or_routine
			subtract = 1
			multiply = 8
		}
	}
}

nd_cd_public_value = {
	value = 0
	if = {
		limit = { nd_crisis_is_public = yes }
		add = 10
	}
}

nd_cd_counter_value = {
	value = 0
	if = {
		limit = {
			has_variable = nd_crisis_counter
			var:nd_crisis_counter = 1
		}
		add = 10
	}
}

# Unreliable command makes every step more dangerous.
nd_cd_reliability_value = {
	value = 100
	subtract = nd_reliability_or_default
	divide = 5
	round = yes
}

nd_cd_weeks_value = {
	value = 0
	if = {
		limit = { has_variable = nd_crisis_weeks }
		add = {
			value = var:nd_crisis_weeks
			max = 26
			divide = 2
		}
	}
	round = yes
}

nd_cd_talks_value = {
	value = 0
	if = {
		limit = {
			has_variable = nd_crisis_talks
			var:nd_crisis_talks = 1
		}
		subtract = 15
	}
}

nd_cd_backed_value = {
	value = 0
	if = {
		limit = {
			has_variable = nd_crisis_backed
			var:nd_crisis_backed = 1
		}
		add = 10
	}
}

# An exercise either side can see (nd_crisis_act_exercise,
# nuclear_incident.10) runs hot for a few weeks.
nd_cd_exercise_value = {
	value = 0
	if = {
		limit = {
			has_variable = nd_crisis_exercise_weeks
			var:nd_crisis_exercise_weeks > 0
		}
		add = 10
	}
}

nd_crisis_danger_value = {
	value = nd_cd_stage_value
	add = nd_cd_issuer_readiness_value
	add = nd_cd_target_readiness_value
	add = nd_cd_public_value
	add = nd_cd_counter_value
	add = nd_cd_reliability_value
	add = nd_cd_weeks_value
	add = nd_cd_talks_value
	add = nd_cd_backed_value
	add = nd_cd_exercise_value
	# With no arsenal on the other side there is no reciprocal alert to
	# misread; the danger is our own hand, not an exchange.
	if = {
		limit = { nd_crisis_danger_dampened = yes }
		multiply = 0.7
	}
	min = 0
	max = 100
	round = yes
}

# ---- Pressure to concede, 0–100: the one explanation both the AI's event
# weights and the player's panel read (§9). Target scope; needs scope:nd_issuer.
nd_yp_base_value = {
	value = 30
}

# Can we answer in kind?
nd_yp_answer_value = {
	value = 0
	if = {
		limit = { nd_believed_armed = no }
		add = 20
	}
	else_if = {
		limit = {
			has_variable = nd_survivability
			var:nd_survivability >= 50
		}
		subtract = 25
	}
	else = {
		subtract = 10
	}
}

# A protector: an armed guarantor that has not walked away, more so once it
# has said publicly that it stands with us (nuclear_crisis.20).
nd_yp_protector_value = {
	value = 0
	if = {
		limit = {
			nd_has_armed_guarantor_against = { AGAINST = scope:nd_issuer }
			NOT = {
				scope:nd_issuer = {
					has_variable = nd_crisis_abandoned
					var:nd_crisis_abandoned = 1
				}
			}
		}
		subtract = 20
	}
	if = {
		limit = {
			scope:nd_issuer = {
				has_variable = nd_crisis_backed
				var:nd_crisis_backed = 1
			}
		}
		subtract = 15
	}
}

# Issuer scope: what the issuer's record of following through is worth.
# Also printed by the action preview (nd_crisis_preview).
nd_credibility_pressure_term = {
	value = nd_credibility_or_default
	subtract = 50
	divide = 2
	round = yes
}

nd_yp_credibility_value = {
	value = 0
	scope:nd_issuer = {
		add = nd_credibility_pressure_term
	}
}

nd_yp_alert_value = {
	value = 0
	scope:nd_issuer = {
		if = {
			limit = { nd_readiness_high_alert = yes }
			add = 10
		}
	}
}

nd_yp_danger_value = {
	value = 0
	scope:nd_issuer = {
		if = {
			limit = { has_variable = nd_crisis_danger }
			add = {
				value = var:nd_crisis_danger
				divide = 5
			}
		}
	}
	round = yes
}

nd_yp_exercise_value = {
	value = 0
	scope:nd_issuer = {
		if = {
			limit = {
				has_variable = nd_crisis_exercise_weeks
				var:nd_crisis_exercise_weeks > 0
			}
			add = 10
		}
	}
}

# Our own temperament.
nd_yp_temperament_value = {
	value = 0
	if = {
		limit = { ruler_is_aggressive = yes }
		subtract = 15
	}
	if = {
		limit = { ruler_is_cautious = yes }
		add = 10
	}
}

# What the dispute costs us to give up.
nd_yp_war_value = {
	value = 0
	if = {
		limit = {
			has_war_with = scope:nd_issuer
			nd_is_losing_war_to = { ENEMY = scope:nd_issuer }
		}
		add = 15
	}
	if = {
		limit = { nd_enemy_threatens_existence = { ENEMY = scope:nd_issuer } }
		subtract = 15
	}
}

# Can they carry it out? (spec §1.1) Their doctrine is public.
nd_yp_follow_through_value = {
	value = 0
	scope:nd_issuer = {
		if = {
			limit = {
				has_variable = nd_ft_reason
				var:nd_ft_reason <= 2
			}
			add = 10
		}
		else_if = {
			limit = {
				has_variable = nd_ft_reason
				var:nd_ft_reason = 7
			}
			subtract = 35
		}
		else_if = {
			limit = {
				has_variable = nd_ft_reason
				var:nd_ft_reason >= 5
			}
			subtract = 25
		}
	}
}

nd_yield_pressure_value = {
	value = nd_yp_base_value
	add = nd_yp_answer_value
	add = nd_yp_protector_value
	add = nd_yp_credibility_value
	add = nd_yp_alert_value
	add = nd_yp_danger_value
	add = nd_yp_exercise_value
	add = nd_yp_temperament_value
	add = nd_yp_war_value
	add = nd_yp_follow_through_value
	min = 0
	max = 100
	round = yes
}
```

`nd_yp_war_value` deliberately uses `nd_is_losing_war_to` (Step 4), not the old `is_losing_war_against`: that fixes the perspective bug described there. Mention it in the PR body.

- [ ] **Step 4: Add the dampening trigger, and a losing-war test that does not read ROOT**

`is_losing_war_against` (`nuke_triggers.txt`) reads ROOT as the country asked. The old pressure formula called it in the **target's** scope while ROOT was the **issuer** (the weekly pulse, the diplomatic action), so "the target is losing to us" fired when the *issuer* was losing battles. Add a ROOT-free twin to `nuclear_deterrence_triggers.txt` (next to `nd_core_threatened_by`), used by `nd_yp_war_value` above and by the preview (Task 5):

```
# The scoped country is losing its war with $ENEMY$: a quarter of its land
# occupied, or, after five significant battles in a war with them, under 35 %
# of the battles won. is_losing_war_against's rule, with the loser read from
# this scope rather than ROOT.
nd_is_losing_war_to = {
	save_temporary_scope_as = nd_lw_self
	OR = {
		enemy_occupation >= 0.25
		any_scope_war = {
			is_war_participant = $ENEMY$
			num_significant_battles >= 5
			scope:nd_lw_self = {
				size_weighted_won_battles_fraction = { target = PREV value < 0.35 }
			}
		}
	}
}
```

Then add to `nuclear_deterrence_triggers.txt` in the `# CRISIS STATE` section (after `nd_crisis_is_public`):

```
# Issuer scope, scope:nd_target saved: the target has no arsenal and no armed
# protector, so the crisis danger is scaled by 0.7 (nd_crisis_danger_value).
nd_crisis_danger_dampened = {
	scope:nd_target = {
		nd_believed_armed = no
		NOT = { nd_has_armed_guarantor_against = { AGAINST = scope:nd_issuer } }
	}
}
```

- [ ] **Step 5: Add the refresh, store and clear effects**

Insert in `nuclear_crisis_effects.txt` right before the `# THE WEEKLY TICK` section header:

```
# ----------------------------------------------------------------------------
# FIGURES — the one writer of the crisis's numbers (2026-09-25 spec §1.2)
# ----------------------------------------------------------------------------
# Issuer scope, parties saved. Classifies follow-through, then stores every
# danger part (issuer-scope values) and every pressure part (target-scope
# values) on BOTH parties, then the totals. The panel's breakdowns print the
# stored parts (nd_crisis_*_breakdown_sgui), so what it shows always sums to
# what the AI weighs.
nd_crisis_refresh_figures = {
	nd_crisis_classify_follow_through = { TARGET = scope:nd_target }
	scope:nd_target = {
		set_variable = { name = nd_ft_reason value = scope:nd_issuer.var:nd_ft_reason }
	}
	nd_crisis_store_cd = { C = nd_cd_stage V = nd_cd_stage_value }
	nd_crisis_store_cd = { C = nd_cd_issuer_readiness V = nd_cd_issuer_readiness_value }
	nd_crisis_store_cd = { C = nd_cd_target_readiness V = nd_cd_target_readiness_value }
	nd_crisis_store_cd = { C = nd_cd_public V = nd_cd_public_value }
	nd_crisis_store_cd = { C = nd_cd_counter V = nd_cd_counter_value }
	nd_crisis_store_cd = { C = nd_cd_reliability V = nd_cd_reliability_value }
	nd_crisis_store_cd = { C = nd_cd_weeks V = nd_cd_weeks_value }
	nd_crisis_store_cd = { C = nd_cd_talks V = nd_cd_talks_value }
	nd_crisis_store_cd = { C = nd_cd_backed V = nd_cd_backed_value }
	nd_crisis_store_cd = { C = nd_cd_exercise V = nd_cd_exercise_value }
	if = {
		limit = { nd_crisis_danger_dampened = yes }
		set_variable = { name = nd_cd_dampened value = 1 }
	}
	else = {
		set_variable = { name = nd_cd_dampened value = 0 }
	}
	scope:nd_target = {
		set_variable = { name = nd_cd_dampened value = scope:nd_issuer.var:nd_cd_dampened }
	}
	set_variable = { name = nd_crisis_danger value = nd_crisis_danger_value }
	scope:nd_target = {
		nd_crisis_store_yp = { C = nd_yp_base V = nd_yp_base_value }
		nd_crisis_store_yp = { C = nd_yp_answer V = nd_yp_answer_value }
		nd_crisis_store_yp = { C = nd_yp_protector V = nd_yp_protector_value }
		nd_crisis_store_yp = { C = nd_yp_credibility V = nd_yp_credibility_value }
		nd_crisis_store_yp = { C = nd_yp_alert V = nd_yp_alert_value }
		nd_crisis_store_yp = { C = nd_yp_danger V = nd_yp_danger_value }
		nd_crisis_store_yp = { C = nd_yp_exercise V = nd_yp_exercise_value }
		nd_crisis_store_yp = { C = nd_yp_temperament V = nd_yp_temperament_value }
		nd_crisis_store_yp = { C = nd_yp_war V = nd_yp_war_value }
		nd_crisis_store_yp = { C = nd_yp_follow_through V = nd_yp_follow_through_value }
		set_variable = { name = nd_yield_pressure value = nd_yield_pressure_value }
	}
}

# Issuer scope, parties saved: one danger part, stored and mirrored.
nd_crisis_store_cd = {
	set_variable = { name = $C$ value = $V$ }
	scope:nd_target = {
		set_variable = { name = $C$ value = scope:nd_issuer.var:$C$ }
	}
}

# Target scope, parties saved: one pressure part, stored and mirrored.
nd_crisis_store_yp = {
	set_variable = { name = $C$ value = $V$ }
	scope:nd_issuer = {
		set_variable = { name = $C$ value = scope:nd_target.var:$C$ }
	}
}

# Either party: drop the stored figures (nd_crisis_clear_vars).
nd_crisis_clear_figures = {
	if = {
		limit = { has_variable = nd_ft_reason }
		remove_variable = nd_ft_reason
	}
	if = {
		limit = { has_variable = nd_cd_dampened }
		remove_variable = nd_cd_dampened
	}
	if = {
		limit = { has_variable = nd_cd_stage }
		remove_variable = nd_cd_stage
	}
	if = {
		limit = { has_variable = nd_cd_issuer_readiness }
		remove_variable = nd_cd_issuer_readiness
	}
	if = {
		limit = { has_variable = nd_cd_target_readiness }
		remove_variable = nd_cd_target_readiness
	}
	if = {
		limit = { has_variable = nd_cd_public }
		remove_variable = nd_cd_public
	}
	if = {
		limit = { has_variable = nd_cd_counter }
		remove_variable = nd_cd_counter
	}
	if = {
		limit = { has_variable = nd_cd_reliability }
		remove_variable = nd_cd_reliability
	}
	if = {
		limit = { has_variable = nd_cd_weeks }
		remove_variable = nd_cd_weeks
	}
	if = {
		limit = { has_variable = nd_cd_talks }
		remove_variable = nd_cd_talks
	}
	if = {
		limit = { has_variable = nd_cd_backed }
		remove_variable = nd_cd_backed
	}
	if = {
		limit = { has_variable = nd_cd_exercise }
		remove_variable = nd_cd_exercise
	}
	if = {
		limit = { has_variable = nd_yp_base }
		remove_variable = nd_yp_base
	}
	if = {
		limit = { has_variable = nd_yp_answer }
		remove_variable = nd_yp_answer
	}
	if = {
		limit = { has_variable = nd_yp_protector }
		remove_variable = nd_yp_protector
	}
	if = {
		limit = { has_variable = nd_yp_credibility }
		remove_variable = nd_yp_credibility
	}
	if = {
		limit = { has_variable = nd_yp_alert }
		remove_variable = nd_yp_alert
	}
	if = {
		limit = { has_variable = nd_yp_danger }
		remove_variable = nd_yp_danger
	}
	if = {
		limit = { has_variable = nd_yp_exercise }
		remove_variable = nd_yp_exercise
	}
	if = {
		limit = { has_variable = nd_yp_temperament }
		remove_variable = nd_yp_temperament
	}
	if = {
		limit = { has_variable = nd_yp_war }
		remove_variable = nd_yp_war
	}
	if = {
		limit = { has_variable = nd_yp_follow_through }
		remove_variable = nd_yp_follow_through
	}
}
```

- [ ] **Step 6: Call it from the open, the tick and the clear**

In `nd_crisis_open`:
1. Delete the line `set_variable = { name = nd_crisis_danger value = nd_crisis_danger_value }` (in the issuer's record block).
2. In the `scope:nd_target = { … }` mirror block, delete `set_variable = { name = nd_yield_pressure value = nd_yield_pressure_value }`.
3. Directly after that mirror block's closing `}` (before `# ---- what the world sees`), add:

```
			# ---- the crisis's figures, before anyone weighs them ------------
			nd_crisis_refresh_figures = yes
```

In `nd_crisis_weekly_tick`, replace:

```
		set_variable = { name = nd_crisis_danger value = nd_crisis_danger_value }
		scope:nd_target = {
			set_variable = { name = nd_yield_pressure value = nd_yield_pressure_value }
		}
```

with:

```
		nd_crisis_refresh_figures = yes
```

In `nd_crisis_clear_vars`, add as its last line (before the final `}`):

```
	nd_crisis_clear_figures = yes
```

- [ ] **Step 7: Run tests**

Run: `python3 -m unittest test_nuclear_deterrence -v`
Expected: all PASS.

- [ ] **Step 8: Format and commit**

```bash
python3 scripts/format_paradox_tabs.py common/script_values/nuclear_deterrence_values.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_crisis_effects.txt
git add common/script_values/nuclear_deterrence_values.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_crisis_effects.txt test_nuclear_deterrence.py
git commit -m "Nuclear crisis: danger and pressure are stored, named parts; bluffs cost pressure" -m "nd_crisis_refresh_figures is the one writer of the crisis's numbers. It stores every part on both parties so the panel can print a breakdown that sums to the total, and adds the follow-through part: +10 backed, -25 a bluff, -35 under No First Use.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

---

### Task 4: The outcome notice applies its own consequences

**Files:**
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_close`; replace `nd_crisis_apply_outcome`)
- Modify: `events/nuclear_crisis_events.txt` (`nuclear_crisis.6`)
- Modify: `common/customizable_localization/nuclear_deterrence_custom_loc.txt` (new `nd_crisis_concession_past`)
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `te_events_l_english.yml`
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: `nd_ft_reason` (Tasks 2–3), still set when `nd_crisis_close` runs.
- Produces: per-party pending record `nd_crisis_pending_outcome/_role/_opponent/_dispute/_public/_defensive/_bluff`; effects `nd_crisis_record_pending`, `nd_crisis_write_pending = { ROLE OPPONENT }`, `nd_crisis_flush_pending`, `nd_crisis_apply_outcome_side`, `nd_crisis_bluff_called`, `nd_crisis_clear_pending`. Loc keys `nd_tt_credibility_up_10`, `nd_tt_credibility_up_15`, `nd_tt_credibility_down_15`, `nd_tt_credibility_down_5_bluff` (Tasks 5–6 reuse them).

- [ ] **Step 1: Write the failing test**

```python
class TestOutcomeNotice(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.events = strip_comments(read(CRISIS_EVENTS))

    def test_close_no_longer_applies_consequences(self):
        self.assertNotRegex(self.effects, r"(?m)^nd_crisis_apply_outcome = \{")
        self.assertNotIn("nd_crisis_apply_outcome = yes", block(self.effects, "nd_crisis_close"))

    def test_close_flushes_before_recording(self):
        body = block(self.effects, "nd_crisis_close")
        flush = body.index("nd_crisis_flush_pending = yes")
        record = body.index("nd_crisis_record_pending = yes")
        self.assertLess(flush, record)
        self.assertEqual(body.count("nd_crisis_flush_pending = yes"), 2)

    def test_outcome_nine_records_nothing(self):
        body = block(self.effects, "nd_crisis_close")
        self.assertRegex(body, r"NOT = \{ var:nd_crisis_outcome_now = 9 \}(\s*\})+\s*nd_crisis_record_pending = yes")

    def test_outcome_option_guards_pending(self):
        body = option_body(self.events, "nuclear_crisis.6.a")
        self.assertIn("has_variable = nd_crisis_pending_outcome", body)
        self.assertIn("var:nd_crisis_pending_opponent ?= scope:nd_outcome_other", body)
        self.assertIn("nd_crisis_apply_outcome_side = yes", body)
        self.assertIn("custom_tooltip = nd_tt_outcome_already_settled", body)

    def test_every_credibility_change_says_its_number(self):
        body = block(self.effects, "nd_crisis_apply_outcome_side") + block(self.effects, "nd_crisis_bluff_called")
        pairs = re.findall(r"text = nd_tt_credibility_(up|down)_(\d+)(?:_bluff)?\s*nd_change_credibility = \{ AMOUNT = (-?\d+) \}", body)
        self.assertTrue(pairs)
        for direction, n, amount in pairs:
            self.assertEqual(int(amount), int(n) if direction == "up" else -int(n))
        self.assertEqual(body.count("nd_change_credibility"), len(pairs), "a credibility change without its number line")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestOutcomeNotice -v`
Expected: FAIL.

- [ ] **Step 3: Rewrite `nd_crisis_close`**

Replace the whole `nd_crisis_close = { … }` block with:

```
nd_crisis_close = {
	save_scope_as = nd_crisis_closing
	if = {
		limit = {
			exists = scope:nd_crisis_closing
			exists = scope:nd_issuer
			exists = scope:nd_target
			scope:nd_issuer = { nd_is_crisis_owner = yes }
		}
		# An outcome notice still unanswered from an earlier crisis settles
		# now, before this crisis's record replaces it (2026-09-25 spec §2.3).
		scope:nd_issuer = { nd_crisis_flush_pending = yes }
		scope:nd_target = { nd_crisis_flush_pending = yes }
		scope:nd_issuer = {
			set_variable = { name = nd_crisis_outcome_now value = $OUTCOME$ }
		}
		# Each side's consequences wait on its outcome notice's option
		# (nd_crisis_apply_outcome_side), so the option's tooltip shows them.
		if = {
			limit = { scope:nd_issuer = { NOT = { var:nd_crisis_outcome_now = 9 } } }
			nd_crisis_record_pending = yes
		}
		scope:nd_issuer = {
			set_variable = { name = nd_crisis_last_outcome value = $OUTCOME$ }
			set_variable = { name = nd_crisis_last_opponent value = scope:nd_target }
			set_variable = { name = nd_crisis_last_role value = 1 }
			set_variable = { name = nd_crisis_cooldown_target value = scope:nd_target }
			set_variable = { name = nd_crisis_cooldown_months value = nd_crisis_cooldown_months_value }
			nd_crisis_clear_vars = yes
		}
		scope:nd_target = {
			if = {
				limit = {
					nd_is_crisis_target = yes
					var:nd_crisis_opponent ?= scope:nd_issuer
				}
				nd_crisis_clear_vars = yes
			}
			set_variable = { name = nd_crisis_last_outcome value = $OUTCOME$ }
			set_variable = { name = nd_crisis_last_opponent value = scope:nd_issuer }
			set_variable = { name = nd_crisis_last_role value = 2 }
		}
		if = {
			limit = { scope:nd_issuer = { NOT = { var:nd_crisis_last_outcome = 9 } } }
			scope:nd_issuer = { trigger_event = { id = nuclear_crisis.6 } }
			scope:nd_target = { trigger_event = { id = nuclear_crisis.6 } }
		}
	}
}
```

Then update the file-header comment line that says `nd_crisis_close = { OUTCOME = N } applies an outcome once` (if present) to say the consequences are applied by the outcome notice.

- [ ] **Step 4: Replace `nd_crisis_apply_outcome` with the per-side effects**

Delete the whole `nd_crisis_apply_outcome = { … }` block (and its header comment) and insert in its place:

```
# Issuer scope, parties saved, var:nd_crisis_outcome_now set, the crisis
# record still in place. Writes each party's outcome-notice record: what
# nuclear_crisis.6's option applies (nd_crisis_apply_outcome_side).
nd_crisis_record_pending = {
	scope:nd_issuer = {
		nd_crisis_write_pending = { ROLE = 1 OPPONENT = scope:nd_target }
	}
	scope:nd_target = {
		nd_crisis_write_pending = { ROLE = 2 OPPONENT = scope:nd_issuer }
	}
}

# Country scope. The crisis facts come from scope:nd_issuer, which holds the
# record for both sides.
nd_crisis_write_pending = {
	set_variable = { name = nd_crisis_pending_outcome value = scope:nd_issuer.var:nd_crisis_outcome_now }
	set_variable = { name = nd_crisis_pending_role value = $ROLE$ }
	set_variable = { name = nd_crisis_pending_opponent value = $OPPONENT$ }
	set_variable = { name = nd_crisis_pending_dispute value = scope:nd_issuer.var:nd_crisis_dispute }
	set_variable = { name = nd_crisis_pending_public value = scope:nd_issuer.var:nd_crisis_public }
	if = {
		limit = { scope:nd_issuer = { nd_crisis_issuer_is_defensive = yes } }
		set_variable = { name = nd_crisis_pending_defensive value = 1 }
	}
	else = {
		set_variable = { name = nd_crisis_pending_defensive value = 0 }
	}
	if = {
		limit = {
			scope:nd_issuer = {
				has_variable = nd_ft_reason
				var:nd_ft_reason >= 5
			}
		}
		set_variable = { name = nd_crisis_pending_bluff value = 1 }
	}
	else = {
		set_variable = { name = nd_crisis_pending_bluff value = 0 }
	}
}

# Country scope. Settles an outcome notice still waiting on a click, so a new
# close cannot overwrite it. The stale notice's option then finds its pair's
# record gone and says so (nuclear_crisis.6). Reached only through
# nd_crisis_close, which runs from pulses and hidden_effects: never call it
# from a visible option, or its credibility lines would render there.
nd_crisis_flush_pending = {
	if = {
		limit = { has_variable = nd_crisis_pending_outcome }
		var:nd_crisis_pending_opponent ?= { save_scope_as = nd_outcome_other }
		nd_crisis_apply_outcome_side = yes
	}
}

# Country scope, the pending record set, scope:nd_outcome_other saved (the
# other party: nuclear_crisis.6's immediate, or nd_crisis_flush_pending).
# One side's consequences of a closed crisis (§6 of the nuclear design).
# Every line renders in the outcome notice's option tooltip.
nd_crisis_apply_outcome_side = {
	# ---- the objective was achieved (1, 4) ----------------------------------
	if = {
		limit = {
			OR = {
				var:nd_crisis_pending_outcome = 1
				var:nd_crisis_pending_outcome = 4
			}
		}
		if = {
			limit = { var:nd_crisis_pending_role = 1 }
			if = {
				limit = { var:nd_crisis_pending_public = 1 }
				custom_tooltip = {
					text = nd_tt_credibility_up_15
					nd_change_credibility = { AMOUNT = 15 }
				}
			}
			else = {
				custom_tooltip = {
					text = nd_tt_credibility_up_10
					nd_change_credibility = { AMOUNT = 10 }
				}
			}
			add_modifier = {
				name = nd_crisis_coercive_success
				days = normal_modifier_time
				is_decaying = yes
			}
			if = {
				limit = { exists = scope:nd_outcome_other }
				custom_tooltip = {
					text = nd_tt_outcome_hawks_approve
					nd_reward_hawks = { OTHER = scope:nd_outcome_other LIST = nd_lob_iw GOOD = yes }
				}
				nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = anti AMOUNT = 3 EVENT = negative }
				nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = pro AMOUNT = -3 EVENT = negative }
			}
		}
		else = {
			custom_tooltip = {
				text = nd_tt_credibility_down_5
				nd_change_credibility = { AMOUNT = -5 }
			}
			add_modifier = {
				name = nd_crisis_yielded
				days = normal_modifier_time
				is_decaying = yes
			}
			if = {
				limit = { exists = scope:nd_outcome_other }
				custom_tooltip = {
					text = nd_tt_outcome_hawks_disapprove
					nd_reward_hawks = { OTHER = scope:nd_outcome_other LIST = nd_lob_tl GOOD = no }
				}
				nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = anti AMOUNT = -3 EVENT = positive }
				nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = pro AMOUNT = 2 EVENT = positive }
			}
		}
	}
	# ---- the issuer backed down (2, 5) ----------------------------------------
	else_if = {
		limit = {
			OR = {
				var:nd_crisis_pending_outcome = 2
				var:nd_crisis_pending_outcome = 5
			}
		}
		if = {
			limit = { var:nd_crisis_pending_role = 1 }
			if = {
				limit = { var:nd_crisis_pending_public = 1 }
				custom_tooltip = {
					text = nd_tt_credibility_down_15
					nd_change_credibility = { AMOUNT = -15 }
				}
				nd_crisis_bluff_called = yes
				add_modifier = {
					name = nd_crisis_climbdown
					days = normal_modifier_time
					is_decaying = yes
				}
				if = {
					limit = { exists = scope:nd_outcome_other }
					custom_tooltip = {
						text = nd_tt_outcome_hawks_disapprove
						nd_reward_hawks = { OTHER = scope:nd_outcome_other LIST = nd_lob_il GOOD = no }
					}
					nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = anti AMOUNT = -4 EVENT = positive }
					nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = pro AMOUNT = 2 EVENT = positive }
				}
			}
			else = {
				custom_tooltip = {
					text = nd_tt_credibility_down_5
					nd_change_credibility = { AMOUNT = -5 }
				}
			}
		}
		else = {
			custom_tooltip = {
				text = nd_tt_credibility_up_10
				nd_change_credibility = { AMOUNT = 10 }
			}
			add_modifier = {
				name = nd_crisis_stood_firm
				days = normal_modifier_time
				is_decaying = yes
			}
			if = {
				limit = { exists = scope:nd_outcome_other }
				custom_tooltip = {
					text = nd_tt_outcome_hawks_approve
					nd_reward_hawks = { OTHER = scope:nd_outcome_other LIST = nd_lob_tw GOOD = yes }
				}
				nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = anti AMOUNT = 3 EVENT = negative }
				nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = pro AMOUNT = -2 EVENT = negative }
			}
		}
	}
	# ---- reciprocal stand-down (3) --------------------------------------------
	else_if = {
		limit = { var:nd_crisis_pending_outcome = 3 }
		# A public demand traded away for a stand-down it did not ask for is
		# half an audience cost; a defensive issuer got what it wanted.
		if = {
			limit = {
				var:nd_crisis_pending_role = 1
				var:nd_crisis_pending_public = 1
				var:nd_crisis_pending_defensive = 0
			}
			custom_tooltip = {
				text = nd_tt_credibility_down_5
				nd_change_credibility = { AMOUNT = -5 }
			}
			if = {
				limit = { exists = scope:nd_outcome_other }
				nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = anti AMOUNT = -2 EVENT = positive }
			}
		}
		else = {
			custom_tooltip = {
				text = nd_tt_credibility_up_5
				nd_change_credibility = { AMOUNT = 5 }
			}
		}
		if = {
			limit = { exists = scope:nd_outcome_other }
			nd_lobby_react = { OTHER = scope:nd_outcome_other TYPE = pro AMOUNT = 2 EVENT = positive }
		}
		add_modifier = {
			name = nd_crisis_mutual_restraint
			days = normal_modifier_time
			is_decaying = yes
		}
		custom_tooltip = {
			text = nd_tt_outcome_doves_approve
			nd_reward_doves = yes
		}
	}
	# ---- an ultimatum left to lapse (8) ---------------------------------------
	else_if = {
		limit = {
			var:nd_crisis_pending_outcome = 8
			var:nd_crisis_pending_role = 1
			var:nd_crisis_pending_public = 1
		}
		custom_tooltip = {
			text = nd_tt_credibility_down_10
			nd_change_credibility = { AMOUNT = -10 }
		}
		nd_crisis_bluff_called = yes
	}
	# ---- the cooldown, for the side that made the threat ---------------------
	if = {
		limit = { var:nd_crisis_pending_role = 1 }
		custom_tooltip = nd_tt_outcome_cooldown
	}
	nd_crisis_clear_pending = yes
}

# A public threat our doctrine or law never let us carry out, called: every
# government knew (spec §1.3).
nd_crisis_bluff_called = {
	if = {
		limit = { var:nd_crisis_pending_bluff = 1 }
		custom_tooltip = {
			text = nd_tt_credibility_down_5_bluff
			nd_change_credibility = { AMOUNT = -5 }
		}
	}
}

nd_crisis_clear_pending = {
	if = {
		limit = { has_variable = nd_crisis_pending_outcome }
		remove_variable = nd_crisis_pending_outcome
	}
	if = {
		limit = { has_variable = nd_crisis_pending_role }
		remove_variable = nd_crisis_pending_role
	}
	if = {
		limit = { has_variable = nd_crisis_pending_opponent }
		remove_variable = nd_crisis_pending_opponent
	}
	if = {
		limit = { has_variable = nd_crisis_pending_dispute }
		remove_variable = nd_crisis_pending_dispute
	}
	if = {
		limit = { has_variable = nd_crisis_pending_public }
		remove_variable = nd_crisis_pending_public
	}
	if = {
		limit = { has_variable = nd_crisis_pending_defensive }
		remove_variable = nd_crisis_pending_defensive
	}
	if = {
		limit = { has_variable = nd_crisis_pending_bluff }
		remove_variable = nd_crisis_pending_bluff
	}
}
```

- [ ] **Step 5: Make `.6` apply it**

In `nuclear_crisis.6`, add an `immediate` block right after `trigger = { has_variable = nd_crisis_last_outcome }`:

```
	# The other party of THIS notice, from the scopes it was sent with. The
	# option applies the pending record only if it is still this pair's.
	immediate = {
		if = {
			limit = {
				has_variable = nd_crisis_pending_role
				var:nd_crisis_pending_role = 1
				exists = scope:nd_target
			}
			scope:nd_target = { save_scope_as = nd_outcome_other }
		}
		else_if = {
			limit = { exists = scope:nd_issuer }
			scope:nd_issuer = { save_scope_as = nd_outcome_other }
		}
	}
```

and replace its option with:

```
	option = {
		name = nuclear_crisis.6.a
		default_option = yes
		if = {
			limit = {
				has_variable = nd_crisis_pending_outcome
				exists = scope:nd_outcome_other
				var:nd_crisis_pending_opponent ?= scope:nd_outcome_other
			}
			nd_crisis_apply_outcome_side = yes
		}
		else = {
			custom_tooltip = nd_tt_outcome_already_settled
		}
	}
```

- [ ] **Step 6: The concession, in the notice's text**

Add to `nuclear_deterrence_custom_loc.txt` after `nd_crisis_demand_text`:

```
# What the target gave up, for the outcome notice. Reads the reader's own
# pending record (nd_crisis_write_pending): role 1 speaks of "they", role 2
# of "we". Empty when there is no record.
nd_crisis_concession_past = {
	type = country
	random_valid = no
	text = {
		trigger = {
			has_variable = nd_crisis_pending_role
			var:nd_crisis_pending_role = 1
			has_variable = nd_crisis_pending_dispute
			var:nd_crisis_pending_dispute = 1
		}
		localization_key = nd_concession_past_they_1
	}
	text = {
		trigger = {
			has_variable = nd_crisis_pending_role
			var:nd_crisis_pending_role = 1
			has_variable = nd_crisis_pending_dispute
			var:nd_crisis_pending_dispute = 2
		}
		localization_key = nd_concession_past_they_2
	}
	text = {
		trigger = {
			has_variable = nd_crisis_pending_role
			var:nd_crisis_pending_role = 1
			has_variable = nd_crisis_pending_dispute
			var:nd_crisis_pending_dispute = 3
		}
		localization_key = nd_concession_past_they_3
	}
	text = {
		trigger = {
			has_variable = nd_crisis_pending_role
			var:nd_crisis_pending_role = 1
			has_variable = nd_crisis_pending_dispute
			var:nd_crisis_pending_dispute = 4
		}
		localization_key = nd_concession_past_they_4
	}
	text = {
		trigger = {
			has_variable = nd_crisis_pending_role
			var:nd_crisis_pending_role = 1
		}
		localization_key = nd_concession_past_they_5
	}
	text = {
		trigger = {
			has_variable = nd_crisis_pending_dispute
			var:nd_crisis_pending_dispute = 1
		}
		localization_key = nd_concession_past_we_1
	}
	text = {
		trigger = {
			has_variable = nd_crisis_pending_dispute
			var:nd_crisis_pending_dispute = 2
		}
		localization_key = nd_concession_past_we_2
	}
	text = {
		trigger = {
			has_variable = nd_crisis_pending_dispute
			var:nd_crisis_pending_dispute = 3
		}
		localization_key = nd_concession_past_we_3
	}
	text = {
		trigger = {
			has_variable = nd_crisis_pending_dispute
			var:nd_crisis_pending_dispute = 4
		}
		localization_key = nd_concession_past_we_4
	}
	text = {
		trigger = {
			has_variable = nd_crisis_pending_dispute
			var:nd_crisis_pending_dispute = 5
		}
		localization_key = nd_concession_past_we_5
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_concession_past_none
	}
}
```

In `te_events_l_english.yml`, append ` [ROOT.GetCountry.GetCustom('nd_crisis_concession_past')]` before the closing quote of **both** `nuclear_crisis.6.d_yielded_issuer` and `nuclear_crisis.6.d_yielded_target`.

- [ ] **Step 7: Loc**

Add to `te_miscellaneous_l_english.yml`:

```yaml
 nd_tt_credibility_up_10:0 "Our #v credibility#! rises by #G 10#!"
 nd_tt_credibility_up_15:0 "Our #v credibility#! rises by #G 15#!"
 nd_tt_credibility_down_15:0 "Our #v credibility#! falls by #R 15#!"
 nd_tt_credibility_down_5_bluff:0 "Every government knew our doctrine did not allow this: our #v credibility#! falls by #R 5#! more"
 nd_tt_outcome_hawks_approve:0 "Our militarists and officers approve (a decaying approval bonus)"
 nd_tt_outcome_hawks_disapprove:0 "Our militarists and officers disapprove (a decaying approval penalty)"
 nd_tt_outcome_doves_approve:0 "Our advocates of restraint approve (a decaying approval bonus)"
 nd_tt_outcome_cooldown:0 "No new crisis with them for #v 24#! months, unless we are at war"
 nd_tt_outcome_already_settled:0 "#lore This outcome was already settled when a later crisis closed. Nothing more happens.#!"
 nd_concession_past_they_1:0 "They backed down in the diplomatic play, and our side won it."
 nd_concession_past_they_2:0 "Their war support in our war fell by #R 35#!."
 nd_concession_past_they_3:0 "They left the country we protect alone: they backed down in the play, or their war support in that war fell by #R 35#!."
 nd_concession_past_they_4:0 "Their weapons programme is frozen for #v 10#! years."
 nd_concession_past_they_5:0 "Their forces stood down to #v Routine#!, and are held there for #v 24#! months."
 nd_concession_past_we_1:0 "We backed down in the diplomatic play, and their side won it."
 nd_concession_past_we_2:0 "Our war support in the war with them fell by #R 35#!."
 nd_concession_past_we_3:0 "We left the country they protect alone: we backed down in the play, or our war support in that war fell by #R 35#!."
 nd_concession_past_we_4:0 "Our weapons programme is frozen for #v 10#! years."
 nd_concession_past_we_5:0 "Our forces stood down to #v Routine#!, and are held there for #v 24#! months."
 nd_concession_past_none:0 ""
```

- [ ] **Step 8: Run tests**

Run: `python3 -m unittest test_nuclear_deterrence -v`
Expected: all PASS.

- [ ] **Step 9: Format and commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/nuclear_crisis_effects.txt events/nuclear_crisis_events.txt common/customizable_localization/nuclear_deterrence_custom_loc.txt
git add common/scripted_effects/nuclear_crisis_effects.txt events/nuclear_crisis_events.txt common/customizable_localization/nuclear_deterrence_custom_loc.txt localization/english/te_miscellaneous_l_english.yml localization/english/te_events_l_english.yml test_nuclear_deterrence.py
git commit -m "Nuclear crisis: the outcome notice applies and shows its consequences" -m "Each side's credibility, modifiers, interest-group and lobby reactions move from nd_crisis_close into nuclear_crisis.6's option, so its tooltip renders them. The concession stays at the moment of yielding and is named in the notice's text. A notice left unanswered when another crisis closes is flushed first. A public bluff that is called costs 5 more credibility.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

---

### Task 5: The warning and the ultimatum say what they do

**Files:**
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_open`; new `nd_crisis_preview`)
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `te_unused_l_english.yml` (delete `nd_tt_crisis_opens_yes/no`)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: `nd_threat_*` (Task 2), `nd_credibility_pressure_term` (Task 3), component literals in `nd_yp_*_value` (Task 3).
- Produces: `nd_crisis_preview = { TARGET PUBLIC }` (issuer scope), called by `nd_crisis_open`.

- [ ] **Step 1: Write the failing test**

```python
PREVIEW_PINS = {
    # loc key: (script value holding the constant, operation, number)
    "nd_tt_open_f_unarmed": ("nd_yp_answer_value", "add", 20),
    "nd_tt_open_f_survivable": ("nd_yp_answer_value", "subtract", 25),
    "nd_tt_open_f_armed": ("nd_yp_answer_value", "subtract", 10),
    "nd_tt_open_f_protector": ("nd_yp_protector_value", "subtract", 20),
    "nd_tt_open_f_aggressive": ("nd_yp_temperament_value", "subtract", 15),
    "nd_tt_open_f_cautious": ("nd_yp_temperament_value", "add", 10),
    "nd_tt_open_f_losing": ("nd_yp_war_value", "add", 15),
    "nd_tt_open_f_existence": ("nd_yp_war_value", "subtract", 15),
    "nd_tt_open_f_alert": ("nd_yp_alert_value", "add", 10),
    "nd_tt_open_backed": ("nd_yp_follow_through_value", "add", 10),
    "nd_tt_open_bluff_existential": ("nd_yp_follow_through_value", "subtract", 25),
    "nd_tt_open_bluff_flexible": ("nd_yp_follow_through_value", "subtract", 25),
    "nd_tt_open_bluff_law": ("nd_yp_follow_through_value", "subtract", 25),
    "nd_tt_open_bluff_nfu": ("nd_yp_follow_through_value", "subtract", 35),
}


def loc_value(key):
    for path in LOC_DIR.glob("*.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"\s+" + re.escape(key) + r":\d*\s+\"(.*)\"\s*$", line)
            if m:
                return m.group(1)
    raise AssertionError(f"loc key {key} not found")


class TestActionPreview(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.values = strip_comments(read(VALUES))

    def test_open_uses_the_preview(self):
        body = block(self.effects, "nd_crisis_open")
        self.assertIn("nd_crisis_preview = { TARGET = $TARGET$ PUBLIC = $PUBLIC$ }", body)
        self.assertNotIn("nd_tt_crisis_opens_", body)
        self.assertNotIn("change_infamy", body)
        self.assertNotIn("change_relations", body)

    def test_preview_reads_no_crisis_scopes(self):
        body = block(self.effects, "nd_crisis_preview")
        self.assertNotRegex(body, r"scope:nd_(?!pv_self\b)")
        self.assertNotRegex(body, r"(?<!temporary_)save_scope_as")
        self.assertNotRegex(body, r"= PREV\b", "PREV passed as a parameter")

    def test_preview_numbers_match_the_formula(self):
        preview = block(self.effects, "nd_crisis_preview")
        for key, (value, op, n) in PREVIEW_PINS.items():
            self.assertIn(key, preview, key)
            self.assertRegex(block(self.values, value), rf"{op} = {n}\b", f"{value} lost {op} {n}")
            self.assertIn(str(n), loc_value(key), key)

    def test_preview_stakes_and_deadlines(self):
        self.assertRegex(self.values, r"nd_crisis_deadline_public_weeks = 8\b")
        self.assertRegex(self.values, r"nd_crisis_deadline_private_weeks = 10\b")
        self.assertRegex(self.values, r"nd_crisis_pressure_interval_weeks = 6\b")
        self.assertIn("8", loc_value("nd_tt_open_next_public"))
        self.assertIn("10", loc_value("nd_tt_open_next_private"))
        for key in ("nd_tt_open_next_public", "nd_tt_open_next_private"):
            self.assertIn("6", loc_value(key))
        for n in ("15", "10"):
            self.assertIn(n, loc_value("nd_tt_open_stakes_public"))
        for n in ("10", "5"):
            self.assertIn(n, loc_value("nd_tt_open_stakes_private"))
```

Also, in `TestLocalization.test_custom_tooltip_keys`, delete the line
`expanded |= {"nd_tt_crisis_opens_yes", "nd_tt_crisis_opens_no"}`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestActionPreview -v`
Expected: FAIL.

- [ ] **Step 3: Add `nd_crisis_preview`**

Insert in `nuclear_crisis_effects.txt` directly before `nd_crisis_open`:

```
# Issuer scope. What opening a crisis against $TARGET$ does and risks, for the
# diplomatic actions' confirmation box and the event options that open one
# (2026-09-25 spec §2.1). Reads only our own state and $TARGET$, which exist in
# a tooltip preview (a temporary scope saved inside a `limit` does exist
# there; a scope saved by an effect does not). Every line sits at this scope
# level so the lines print in order (gui_modding_guide.md gotcha #18). The infamy and relations lines are
# the real effects: every caller has already checked that the crisis opens
# (nd_crisis_parties_free), so they are not fenced.
nd_crisis_preview = {
	# ---- what the world sees ------------------------------------------------
	if = {
		limit = { always = $PUBLIC$ }
		change_infamy = 5
		change_relations = { country = $TARGET$ value = -20 }
	}
	else = {
		change_relations = { country = $TARGET$ value = -5 }
	}
	# ---- what it is about, and what conceding would cost them ----------------
	if = {
		limit = { nd_dispute_war_with = { TARGET = $TARGET$ } }
		custom_tooltip = nd_tt_open_over_war
	}
	else_if = {
		limit = { nd_dispute_play_with = { TARGET = $TARGET$ } }
		custom_tooltip = nd_tt_open_over_play
	}
	else_if = {
		limit = { nd_dispute_guarantee_against = { TARGET = $TARGET$ } }
		custom_tooltip = nd_tt_open_over_guarantee
	}
	else_if = {
		limit = { nd_dispute_proliferation_by = { TARGET = $TARGET$ } }
		custom_tooltip = nd_tt_open_over_proliferation
	}
	else = {
		custom_tooltip = nd_tt_open_over_alert
	}
	# ---- can we carry it out? ---------------------------------------------------
	if = {
		limit = { nd_threat_bluff_nfu = { TARGET = $TARGET$ } }
		custom_tooltip = nd_tt_open_bluff_nfu
	}
	else_if = {
		limit = { NOT = { nd_threat_law_permits = { TARGET = $TARGET$ } } }
		custom_tooltip = nd_tt_open_bluff_law
	}
	else_if = {
		limit = { nd_threat_backed = { TARGET = $TARGET$ } }
		custom_tooltip = nd_tt_open_backed
	}
	else_if = {
		limit = { nd_threat_uncertain = { TARGET = $TARGET$ } }
		custom_tooltip = nd_tt_open_uncertain
	}
	else_if = {
		limit = { nd_doctrine_flexible = yes }
		custom_tooltip = nd_tt_open_bluff_flexible
	}
	else = {
		custom_tooltip = nd_tt_open_bluff_existential
	}
	# ---- what else weighs on them (nd_yp_*; danger and exercises come later) --
	custom_tooltip = nd_tt_open_factors_header
	if = {
		limit = { $TARGET$ = { nd_believed_armed = no } }
		custom_tooltip = nd_tt_open_f_unarmed
	}
	else_if = {
		limit = {
			$TARGET$ = {
				has_variable = nd_survivability
				var:nd_survivability >= 50
			}
		}
		custom_tooltip = nd_tt_open_f_survivable
	}
	else = {
		custom_tooltip = nd_tt_open_f_armed
	}
	if = {
		limit = {
			save_temporary_scope_as = nd_pv_self
			$TARGET$ = { nd_has_armed_guarantor_against = { AGAINST = scope:nd_pv_self } }
		}
		custom_tooltip = nd_tt_open_f_protector
	}
	custom_tooltip = nd_tt_open_f_credibility
	if = {
		limit = { nd_readiness_high_alert = yes }
		custom_tooltip = nd_tt_open_f_alert
	}
	if = {
		limit = { $TARGET$ = { ruler_is_aggressive = yes } }
		custom_tooltip = nd_tt_open_f_aggressive
	}
	if = {
		limit = { $TARGET$ = { ruler_is_cautious = yes } }
		custom_tooltip = nd_tt_open_f_cautious
	}
	if = {
		limit = {
			save_temporary_scope_as = nd_pv_self
			$TARGET$ = {
				has_war_with = scope:nd_pv_self
				nd_is_losing_war_to = { ENEMY = scope:nd_pv_self }
			}
		}
		custom_tooltip = nd_tt_open_f_losing
	}
	if = {
		limit = {
			save_temporary_scope_as = nd_pv_self
			$TARGET$ = { nd_enemy_threatens_existence = { ENEMY = scope:nd_pv_self } }
		}
		custom_tooltip = nd_tt_open_f_existence
	}
	# ---- the stakes, and what happens next ------------------------------------
	if = {
		limit = { always = $PUBLIC$ }
		custom_tooltip = nd_tt_open_stakes_public
		if = {
			limit = {
				NOT = { nd_threat_backed = { TARGET = $TARGET$ } }
				NOT = { nd_threat_uncertain = { TARGET = $TARGET$ } }
			}
			custom_tooltip = nd_tt_open_stakes_bluff
		}
		custom_tooltip = nd_tt_open_next_public
	}
	else = {
		custom_tooltip = nd_tt_open_stakes_private
		custom_tooltip = nd_tt_open_next_private
	}
}
```

- [ ] **Step 4: Rewire `nd_crisis_open`**

1. Replace its first line `custom_tooltip = nd_tt_crisis_opens_$PUBLIC$` with `nd_crisis_preview = { TARGET = $TARGET$ PUBLIC = $PUBLIC$ }`.
2. Delete the whole `# ---- what the world sees ----` block inside the fence (the `if = { limit = { always = $PUBLIC$ } change_infamy = 5 scope:nd_target = { change_relations … } } else = { … }`).
3. Update the header comment: the preview owns the infamy and relations effects.

- [ ] **Step 5: Loc**

Delete `nd_tt_crisis_opens_no` and `nd_tt_crisis_opens_yes` from `te_unused_l_english.yml`. Add to `te_miscellaneous_l_english.yml`:

```yaml
 nd_tt_open_over_war:0 "Over: #v our war with them#!. If they concede, their war support in that war falls by #R 35#!, which can force them to capitulate"
 nd_tt_open_over_play:0 "Over: #v the diplomatic play#!. If they concede, they back down and our side wins it"
 nd_tt_open_over_guarantee:0 "Over: #v the country we protect#!. If they concede, they leave it alone: they back down in the play, or their war support in that war falls by #R 35#!"
 nd_tt_open_over_proliferation:0 "Over: #v their weapons programme#!. If they concede, it is frozen for #v 10#! years"
 nd_tt_open_over_alert:0 "Over: #v their forces on alert#!. If they concede, they stand down to #v Routine#! and are held there for #v 24#! months"
 nd_tt_open_backed:0 "#G Backed:#! our doctrine lets us carry this out if they defy it. Their pressure to concede #G +10#!"
 nd_tt_open_uncertain:0 "#Y Uncertain:#! our doctrine would let us carry this out only if this became a war that threatened what it protects. No effect on their pressure"
 nd_tt_open_bluff_existential:0 "#R A bluff:#! #v Existential Deterrence#! permits a first strike only when they threaten our survival, or our territory while we are losing. They know our doctrine: their pressure to concede #R -25#!"
 nd_tt_open_bluff_flexible:0 "#R A bluff:#! #v Flexible First Use#! permits a strike only when we are losing to them or they threaten our territory. They know our doctrine: their pressure to concede #R -25#!"
 nd_tt_open_bluff_law:0 "#R A bluff:#! our #v Rules of War#! law forbids a nuclear strike. Their pressure to concede #R -25#!"
 nd_tt_open_bluff_nfu:0 "#R A bluff:#! we have pledged #v No First Use#!. Their pressure to concede #R -35#!"
 nd_tt_open_factors_header:0 "What else weighs on them, from a starting point of #v 30#!:"
 nd_tt_open_f_unarmed:0 "  They cannot answer in kind: #G +20#!"
 nd_tt_open_f_survivable:0 "  Their own arsenal would survive a strike: #R -25#!"
 nd_tt_open_f_armed:0 "  They have an arsenal of their own: #R -10#!"
 nd_tt_open_f_protector:0 "  An armed power guarantees them: #R -20#!"
 nd_tt_open_f_credibility:0 "  Our #v credibility#!: #v [THIS.ScriptValue('nd_credibility_pressure_term')|+0]#!"
 nd_tt_open_f_alert:0 "  Our forces are at #v High Alert#!: #G +10#!"
 nd_tt_open_f_aggressive:0 "  Their ruler is aggressive: #R -15#!"
 nd_tt_open_f_cautious:0 "  Their ruler is cautious: #G +10#!"
 nd_tt_open_f_losing:0 "  They are losing the war to us: #G +15#!"
 nd_tt_open_f_existence:0 "  We threaten their very existence: #R -15#!"
 nd_tt_open_stakes_public:0 "Stakes: if they concede, our #v credibility#! rises by #G 15#!. If we back down it falls by #R 15#!; if the deadline lapses, by #R 10#!"
 nd_tt_open_stakes_private:0 "Stakes: if they concede, our #v credibility#! rises by #G 10#!. If we back down it falls by #R 5#!"
 nd_tt_open_stakes_bluff:0 "If this bluff is called, every government will know it: #R 5#! more credibility lost"
 nd_tt_open_next_public:0 "The crisis opens at #v Confrontation#!. They answer now, and are pressed again every #v 6#! weeks; our deadline is #v 8#! weeks. Follow it in the #v Nuclear Weapons#! journal entry"
 nd_tt_open_next_private:0 "The crisis opens as a private #v Warning#!. They answer now; if they refuse, they are pressed every #v 6#! weeks. Our deadline is #v 10#! weeks. Follow it in the #v Nuclear Weapons#! journal entry"
```

- [ ] **Step 6: Run tests**

Run: `python3 -m unittest test_nuclear_deterrence -v`
Expected: all PASS.

- [ ] **Step 7: Format and commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_effects/nuclear_crisis_effects.txt
git add common/scripted_effects/nuclear_crisis_effects.txt localization/english/te_miscellaneous_l_english.yml localization/english/te_unused_l_english.yml test_nuclear_deterrence.py
git commit -m "Nuclear crisis: the warning and the ultimatum say what they do" -m "The confirmation box shows the infamy and relations as real effects, what the crisis is about and what conceding costs the target, whether our doctrine backs the threat, the factors in their pressure, the stakes and the deadline. A unit test pins every preview number to the pressure formula.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

---

### Task 6: Every crisis move states its numbers

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`# CRISIS STATE`: two either-role triggers)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (the `nd_crisis_act_*` effects)
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: Task 4's credibility keys; `nd_ft_reason` (own variable, both parties).
- Produces: triggers `nd_crisis_dispute_is = { D }` and `nd_crisis_public_either` (either party; Task 7 uses them); effects `nd_crisis_yield_lines`, `nd_crisis_talks_credibility_lines`.

Every line added here must read only our own variables and `var:nd_crisis_opponent`, never `scope:nd_issuer`/`scope:nd_target`: the same acts render in the panel's `ExecuteTooltip`, where no scope is saved.

- [ ] **Step 1: Write the failing test**

```python
ACT_LINES = {
    "nd_crisis_act_yield": ["nd_crisis_yield_lines = yes", "custom_tooltip = nd_tt_then_yield"],
    "nd_crisis_yield_lines": ["nd_tt_yield_war", "nd_tt_yield_play", "nd_tt_yield_guarantee",
                              "nd_tt_yield_freeze", "nd_tt_yield_alert"],
    "nd_crisis_act_reject": ["nd_tt_stage_to_confrontation", "nd_tt_reject_defiance"],
    "nd_crisis_act_counter_threat": ["nd_tt_stage_to_confrontation", "nd_tt_counter_danger"],
    "nd_crisis_act_propose_talks": ["nd_tt_talks_terms", "nd_crisis_talks_credibility_lines = yes",
                                    "nd_tt_talks_meanwhile"],
    "nd_crisis_act_accept_standdown": ["nd_tt_standdown_terms", "nd_crisis_talks_credibility_lines = yes"],
    "nd_crisis_act_hold": ["nd_tt_hold_deadline", "nd_tt_hold_alert_4w", "nd_tt_hold_alert_2w"],
    "nd_crisis_act_extend": ["text = nd_tt_credibility_down_3"],
    "nd_crisis_act_back_down": ["nd_tt_then_back_down_public", "nd_tt_then_back_down_private",
                                "nd_tt_then_bluff_called"],
    "nd_crisis_act_go_public": ["change_infamy = 5", "change_relations", "nd_tt_go_public_terms"],
    "nd_crisis_act_exercise": ["text = nd_tt_strain_up_5", "text = nd_tt_credibility_up_3",
                               "nd_tt_exercise_effect"],
}


class TestActLines(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_every_act_names_its_numbers(self):
        for act, needles in ACT_LINES.items():
            body = block(self.effects, act)
            for needle in needles:
                self.assertIn(needle, body, f"{act} lacks {needle}")

    def test_visible_act_lines_read_no_saved_scopes(self):
        """The panel renders these acts with no saved scopes."""
        for act in ACT_LINES:
            body = block(self.effects, act)
            hidden = re.findall(r"hidden_effect = \{", body)
            visible = body
            for _ in hidden:
                visible = visible.replace("hidden_effect = {" + block(visible, "hidden_effect") + "}", "")
            self.assertNotRegex(visible, r"scope:nd_(issuer|target)", act)

    def test_act_numbers_match_their_constants(self):
        values = strip_comments(read(VALUES))
        self.assertRegex(values, r"nd_crisis_deadline_extension_weeks = 6\b")
        self.assertIn("6", loc_value("nd_tt_hold_deadline"))
        self.assertIn("6", loc_value("nd_tt_act_extend"))
        self.assertIn("6", loc_value("nd_tt_act_refuse_talks"))
        self.assertRegex(block(values, "nd_cd_counter_value"), r"add = 10\b")
        self.assertIn("10", loc_value("nd_tt_counter_danger"))
        self.assertRegex(block(values, "nd_cd_talks_value"), r"subtract = 15\b")
        self.assertIn("15", loc_value("nd_tt_talks_meanwhile"))
        self.assertRegex(block(values, "nd_yp_alert_value"), r"add = 10\b")
        self.assertIn("10", loc_value("nd_tt_hold_alert_2w"))
        self.assertIn("name = nd_crisis_exercise_weeks value = 6", block(self.effects, "nd_crisis_act_exercise"))
        self.assertIn("6", loc_value("nd_tt_exercise_effect"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestActLines -v`
Expected: FAIL.

- [ ] **Step 3: Either-role triggers**

Add to `# CRISIS STATE` in `nuclear_deterrence_triggers.txt`:

```
# Either party: the crisis's dispute code is $D$. The record is the issuer's;
# the target reads it through its mirror (var:nd_crisis_opponent).
nd_crisis_dispute_is = {
	OR = {
		AND = {
			nd_is_crisis_owner = yes
			has_variable = nd_crisis_dispute
			var:nd_crisis_dispute = $D$
		}
		AND = {
			nd_is_crisis_target = yes
			var:nd_crisis_opponent ?= {
				has_variable = nd_crisis_dispute
				var:nd_crisis_dispute = $D$
			}
		}
	}
}

# Either party: the threat is public.
nd_crisis_public_either = {
	OR = {
		AND = {
			nd_is_crisis_owner = yes
			nd_crisis_is_public = yes
		}
		AND = {
			nd_is_crisis_target = yes
			var:nd_crisis_opponent ?= { nd_crisis_is_public = yes }
		}
	}
}
```

- [ ] **Step 4: Rewrite the acts' visible parts**

Keep every act's `hidden_effect = { … }` body unchanged except where noted. New visible parts:

`nd_crisis_act_yield` — replace its first line (`custom_tooltip = nd_tt_act_yield`) with:

```
	custom_tooltip = nd_tt_act_yield
	nd_crisis_yield_lines = yes
	custom_tooltip = nd_tt_then_yield
```

and add after the act:

```
# Target scope: the concession this crisis demands, in one line.
nd_crisis_yield_lines = {
	if = {
		limit = { nd_crisis_dispute_is = { D = 2 } }
		custom_tooltip = nd_tt_yield_war
	}
	else_if = {
		limit = { nd_crisis_dispute_is = { D = 1 } }
		custom_tooltip = nd_tt_yield_play
	}
	else_if = {
		limit = { nd_crisis_dispute_is = { D = 3 } }
		custom_tooltip = nd_tt_yield_guarantee
	}
	else_if = {
		limit = { nd_crisis_dispute_is = { D = 4 } }
		custom_tooltip = nd_tt_yield_freeze
	}
	else_if = {
		limit = { nd_crisis_dispute_is = { D = 5 } }
		custom_tooltip = nd_tt_yield_alert
	}
}
```

`nd_crisis_act_reject` — after `custom_tooltip = nd_tt_act_reject` add:

```
	if = {
		limit = { NOT = { nd_crisis_stage_at_least = { STAGE = 2 } } }
		custom_tooltip = nd_tt_stage_to_confrontation
	}
	if = {
		limit = { nd_crisis_public_either = yes }
		custom_tooltip = nd_tt_reject_defiance
	}
```

`nd_crisis_act_counter_threat` — after `custom_tooltip = nd_tt_act_counter` add the same stage `if` as reject, then `custom_tooltip = nd_tt_counter_danger`.

`nd_crisis_act_propose_talks` — after `custom_tooltip = nd_tt_act_talks` add:

```
	custom_tooltip = nd_tt_talks_terms
	nd_crisis_talks_credibility_lines = yes
	custom_tooltip = nd_tt_talks_meanwhile
```

`nd_crisis_act_accept_standdown` — after `custom_tooltip = nd_tt_act_accept_standdown` add:

```
	custom_tooltip = nd_tt_standdown_terms
	nd_crisis_talks_credibility_lines = yes
```

and add after the acts:

```
# Either party: what a stand-down does to our credibility (applied by the
# outcome notice; nd_crisis_apply_outcome_side, outcome 3).
nd_crisis_talks_credibility_lines = {
	if = {
		limit = {
			nd_is_crisis_owner = yes
			nd_crisis_is_public = yes
			nd_crisis_issuer_is_defensive = no
		}
		custom_tooltip = nd_tt_talks_cred_public_demand
	}
	else = {
		custom_tooltip = nd_tt_talks_cred_plus
	}
}
```

`nd_crisis_act_hold` — replace the whole act with:

```
nd_crisis_act_hold = {
	custom_tooltip = nd_tt_act_hold
	custom_tooltip = nd_tt_hold_deadline
	hidden_effect = {
		if = {
			limit = { nd_is_crisis_owner = yes }
			set_variable = { name = nd_crisis_stage value = 3 }
			set_variable = { name = nd_crisis_deadline value = var:nd_crisis_weeks }
			change_variable = { name = nd_crisis_deadline add = nd_crisis_deadline_extension_weeks }
			set_variable = { name = nd_crisis_deadline_fired value = 0 }
			set_variable = { name = nd_crisis_pressure_weeks value = nd_crisis_pressure_interval_weeks }
		}
	}
	if = {
		limit = {
			nd_is_armed = yes
			nd_readiness_locked = no
			var:nd_readiness_target < 3
		}
		nd_set_readiness_target_3 = yes
		if = {
			limit = { var:nd_readiness = 1 }
			custom_tooltip = nd_tt_hold_alert_4w
		}
		else = {
			custom_tooltip = nd_tt_hold_alert_2w
		}
	}
}
```

`nd_crisis_act_extend` — replace `nd_change_credibility = { AMOUNT = -3 }` with:

```
	custom_tooltip = {
		text = nd_tt_credibility_down_3
		nd_change_credibility = { AMOUNT = -3 }
	}
```

`nd_crisis_act_back_down` — replace the act with:

```
nd_crisis_act_back_down = {
	custom_tooltip = nd_tt_act_back_down
	if = {
		limit = { nd_crisis_is_public = yes }
		custom_tooltip = nd_tt_then_back_down_public
		if = {
			limit = {
				has_variable = nd_ft_reason
				var:nd_ft_reason >= 5
			}
			custom_tooltip = nd_tt_then_bluff_called
		}
	}
	else = {
		custom_tooltip = nd_tt_then_back_down_private
	}
	hidden_effect = {
		nd_crisis_close_from_either = { OUTCOME = 2 }
	}
}
```

`nd_crisis_act_go_public` — make the relations change visible and add terms:

```
nd_crisis_act_go_public = {
	custom_tooltip = nd_tt_act_go_public
	change_infamy = 5
	if = {
		limit = { exists = var:nd_crisis_opponent }
		change_relations = { country = var:nd_crisis_opponent value = -15 }
	}
	custom_tooltip = nd_tt_go_public_terms
	hidden_effect = {
		nd_crisis_save_parties = yes
		if = {
			limit = { exists = scope:nd_target }
			set_variable = { name = nd_crisis_public value = 1 }
			if = {
				limit = { var:nd_crisis_stage < 2 }
				set_variable = { name = nd_crisis_stage value = 2 }
			}
			set_variable = { name = nd_crisis_deadline value = var:nd_crisis_weeks }
			change_variable = { name = nd_crisis_deadline add = nd_crisis_deadline_public_weeks }
			set_variable = { name = nd_crisis_deadline_fired value = 0 }
		}
	}
}
```

`nd_crisis_act_exercise` — replace with:

```
nd_crisis_act_exercise = {
	custom_tooltip = nd_tt_act_exercise
	add_modifier = {
		name = nd_exercise_cost
		multiplier = sv_money_flow_event_large
		days = 90
	}
	custom_tooltip = {
		text = nd_tt_strain_up_5
		change_variable = { name = nd_strain add = 5 }
		clamp_variable = { name = nd_strain min = 0 max = 100 }
	}
	if = {
		limit = { nd_is_crisis_owner = yes }
		custom_tooltip = {
			text = nd_tt_credibility_up_3
			nd_change_credibility = { AMOUNT = 3 }
		}
	}
	custom_tooltip = nd_tt_exercise_effect
	hidden_effect = {
		nd_crisis_save_parties = yes
		if = {
			limit = { exists = scope:nd_issuer }
			scope:nd_issuer = {
				if = {
					limit = { var:nd_crisis_stage < 2 }
					set_variable = { name = nd_crisis_stage value = 2 }
				}
				set_variable = { name = nd_crisis_exercise_weeks value = 6 }
			}
		}
	}
}
```

- [ ] **Step 5: Loc**

Replace the text of these existing keys in `te_miscellaneous_l_english.yml`, and add the new ones:

```yaml
 nd_tt_act_yield:0 "We give them what they demand, and the crisis ends:"
 nd_tt_yield_war:0 "Our war support in the war with them falls by #R 35#!, which can force us to capitulate"
 nd_tt_yield_play:0 "We back down in the diplomatic play: their side wins it"
 nd_tt_yield_guarantee:0 "We leave the country they protect alone: we back down in the play, or our war support in that war falls by #R 35#!"
 nd_tt_yield_freeze:0 "Our weapons programme is frozen for #v 10#! years"
 nd_tt_yield_alert:0 "Our forces stand down to #v Routine#! and are held there for #v 24#! months"
 nd_tt_then_yield:0 "The outcome notice that follows settles our reputation: our #v credibility#! falls by #R 5#!, and our militarists and officers resent it"
 nd_tt_act_reject:0 "We refuse, and leave them to decide what their threat meant"
 nd_tt_stage_to_confrontation:0 "The crisis becomes a #v Confrontation#!: from now on they press us every #v 6#! weeks"
 nd_tt_reject_defiance:0 "The threat was public, so our refusal is recorded as #R defiance#!: under #v Nuclear Compellence#!, that licenses them to strike us in a war"
 nd_tt_act_counter:0 "We answer threat with threat"
 nd_tt_counter_danger:0 "The crisis danger rises by #R 10#! while our counter-threat stands"
 nd_tt_act_talks:0 "We propose a mutual stand-down"
 nd_tt_talks_terms:0 "If they accept, both sides stand down to #v Routine#!, held there for #v 24#! months, and pledge never to use nuclear weapons on each other; renouncing that pledge later costs #R 15#! credibility and #R 5#! infamy. The war or play goes on"
 nd_tt_talks_meanwhile:0 "While they consider it, the pressure events stop and the crisis danger falls by #G 15#!"
 nd_tt_act_accept_standdown:0 "We accept, and the crisis ends:"
 nd_tt_standdown_terms:0 "Both sides stand down to #v Routine#!, held there for #v 24#! months, and pledge never to use nuclear weapons on each other; renouncing that pledge later costs #R 15#! credibility and #R 5#! infamy. The war or play goes on"
 nd_tt_talks_cred_public_demand:0 "Trading a public demand for a stand-down costs our #v credibility#! #R 5#!"
 nd_tt_talks_cred_plus:0 "A stand-down raises our #v credibility#! by #G 5#!"
 nd_tt_act_refuse_talks:0 "We refuse to stand down. Talks close, and the pressure events resume in #v 6#! weeks"
 nd_tt_act_hold:0 "We hold firm: the crisis turns #R Acute#!"
 nd_tt_hold_deadline:0 "Their new deadline is #v 6#! weeks from now, and they are pressed again next week"
 nd_tt_hold_alert_4w:0 "Our forces reach #v High Alert#! in #v 4#! weeks. At High Alert their pressure to concede rises by #G 10#!, and so do our upkeep and the odds of an accident"
 nd_tt_hold_alert_2w:0 "Our forces reach #v High Alert#! in #v 2#! weeks. At High Alert their pressure to concede rises by #G 10#!, and so do our upkeep and the odds of an accident"
 nd_tt_act_extend:0 "We give them #v 6#! more weeks. Hesitation is noticed"
 nd_tt_act_back_down:0 "We abandon the threat, and the crisis ends"
 nd_tt_then_back_down_public:0 "The outcome notice that follows settles our reputation: our #v credibility#! falls by #R 15#!, the climb-down is remembered, and our militarists and officers turn on us"
 nd_tt_then_back_down_private:0 "The outcome notice that follows settles our reputation: our #v credibility#! falls by #R 5#!. Nothing was public, so nothing else"
 nd_tt_then_bluff_called:0 "Our doctrine never allowed this, and every government knew it: #R 5#! more"
 nd_tt_act_go_public:0 "The threat becomes a public ultimatum"
 nd_tt_go_public_terms:0 "The crisis becomes a #v Confrontation#! with a new deadline #v 8#! weeks from now. From here, backing down costs #R 15#! credibility instead of #R 5#!, and letting the deadline lapse costs #R 10#!"
 nd_tt_act_exercise:0 "An exercise they can see — and could mistake for the real thing"
 nd_tt_strain_up_5:0 "#v Crew strain#! rises by #R 5#!"
 nd_tt_credibility_up_3:0 "Our #v credibility#! rises by #G 3#!"
 nd_tt_exercise_effect:0 "For #v 6#! weeks the crisis danger rises by #R 10#!, and if we made the threat, their pressure to concede rises by #G 10#!"
 nd_tt_act_stand_firm:0 "We do not bend. Nothing changes: they press again in #v 6#! weeks, and the deadline is theirs to act on"
```

- [ ] **Step 6: Run tests**

Run: `python3 -m unittest test_nuclear_deterrence -v`
Expected: all PASS.

- [ ] **Step 7: Format and commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_crisis_effects.txt
git add common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_crisis_effects.txt localization/english/te_miscellaneous_l_english.yml test_nuclear_deterrence.py
git commit -m "Nuclear crisis: every move states its numbers" -m "Each nd_crisis_act_* adds lines naming what changes and by how much: this crisis's concession, the stage, the deadline, alert timing, credibility, strain, danger and pressure. Lines read only our own record and our opponent's, so the panel renders them too.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

---

### Task 7: The crisis panel shows our moves, the stakes and the breakdowns

**Files:**
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` (display handlers)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_crisis_breakdown_line`)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_crisis_talks_open_either`)
- Modify: `common/script_values/nuclear_deterrence_values.txt` (`nd_display_next_pressure_weeks`)
- Modify: `common/customizable_localization/nuclear_deterrence_custom_loc.txt`
- Modify: `gui/journal_entry_widgets/nuclear_deterrence_widget.gui`
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: stored parts (Task 3), `nd_ft_reason` (Tasks 2–3), `nd_crisis_dispute_is`/`nd_crisis_public_either` (Task 6).
- Produces: display handlers `nd_crisis_we_issued_sgui`, `nd_crisis_we_are_target_sgui`, `nd_crisis_private_sgui`, `nd_crisis_pressure_breakdown_sgui`, `nd_crisis_danger_breakdown_sgui`, `nd_crisis_next_pressure_sgui`; custom loc `nd_crisis_pressure_label`, `nd_crisis_concede_label`, `nd_crisis_concession_short`, `nd_crisis_concession_long`, `nd_crisis_ft_label`, `nd_crisis_ft_word`, `nd_crisis_ft_reason`, `nd_crisis_stakes_short`, `nd_crisis_stakes_long`, `nd_crisis_stage_next`.

- [ ] **Step 1: Write the failing test**

```python
BREAKDOWN_KEYS = {p: p + "_line" for p in DANGER_PARTS + PRESSURE_PARTS}


class TestCrisisPanel(unittest.TestCase):
    def setUp(self):
        self.sguis = strip_comments(read(SGUIS))
        self.gui = read(GUI)
        self.custom = strip_comments(read(CUSTOM_LOC))
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_display_handlers_exist_and_are_display_only(self):
        for name in ("nd_crisis_we_issued_sgui", "nd_crisis_we_are_target_sgui", "nd_crisis_private_sgui",
                     "nd_crisis_pressure_breakdown_sgui", "nd_crisis_danger_breakdown_sgui",
                     "nd_crisis_next_pressure_sgui"):
            body = block(self.sguis, name)
            self.assertIn("is_valid = { always = no }", body, name)
            self.assertIn("ai_is_valid = { always = no }", body, name)
            self.assertIn(name, self.gui, f"{name} is never drawn")

    def test_breakdowns_print_every_stored_part(self):
        pressure = block(self.sguis, "nd_crisis_pressure_breakdown_sgui")
        danger = block(self.sguis, "nd_crisis_danger_breakdown_sgui")
        for part in PRESSURE_PARTS:
            self.assertIn(f"nd_crisis_breakdown_line = {{ C = {part} KEY = {BREAKDOWN_KEYS[part]} }}", pressure)
        for part in DANGER_PARTS:
            self.assertIn(f"nd_crisis_breakdown_line = {{ C = {part} KEY = {BREAKDOWN_KEYS[part]} }}", danger)

    def test_breakdown_lines_guard_their_variable(self):
        body = block(self.effects, "nd_crisis_breakdown_line")
        self.assertIn("has_variable = $C$", body)
        for part, key in BREAKDOWN_KEYS.items():
            self.assertIn(f"THIS.Var('{part}').GetValue", loc_value(key), key)

    def test_role_rows_are_gated(self):
        for key, sgui in (("nd_w_crisis_act_public", "nd_crisis_private_sgui"),
                          ("nd_w_crisis_act_yield", "nd_crisis_we_are_target_sgui"),
                          ("nd_w_crisis_act_back_down", "nd_crisis_we_issued_sgui"),
                          ("nd_w_crisis_act_exercise", "nd_armed_sgui")):
            i = self.gui.index(f'text = "{key}"')
            row = self.gui.rfind("nd_choice_row = {", 0, i)
            self.assertIn(f"GetScriptedGui('{sgui}')", self.gui[row:i], key)

    def test_new_custom_loc_blocks_have_fallbacks(self):
        for name in ("nd_crisis_pressure_label", "nd_crisis_concede_label", "nd_crisis_concession_short",
                     "nd_crisis_concession_long", "nd_crisis_ft_label", "nd_crisis_ft_word",
                     "nd_crisis_ft_reason", "nd_crisis_stakes_short", "nd_crisis_stakes_long",
                     "nd_crisis_concession_past", "nd_crisis_stage_next"):
            body = block(self.custom, name)
            self.assertRegex(body, r"text = \{\s*trigger = \{ always = yes \}\s*localization_key = \w+\s*\}\s*$", name)

    def test_localize_keys_in_gui_exist(self):
        keys = set(re.findall(r"Localize\( '(\w+)' \)", self.gui))
        self.assertTrue(keys)
        missing = sorted(k for k in keys if k not in loc_keys())
        self.assertFalse(missing, missing)

    def test_pressure_thresholds_match_the_events(self):
        events = strip_comments(read(CRISIS_EVENTS))
        concede = option_body(events, "nuclear_crisis.5.a")
        for n in ("50", "70", "85"):
            self.assertIn(f"var:nd_yield_pressure >= {n}", concede)
            self.assertIn(n, loc_value("nd_w_crisis_pressure_tt"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestCrisisPanel -v`
Expected: FAIL.

- [ ] **Step 3: Trigger, value and line helper**

Trigger (`# CRISIS STATE`):

```
# Either party: talks are open (the pressure events are paused).
nd_crisis_talks_open_either = {
	OR = {
		AND = {
			nd_is_crisis_owner = yes
			has_variable = nd_crisis_talks
			var:nd_crisis_talks = 1
		}
		AND = {
			nd_is_crisis_target = yes
			var:nd_crisis_opponent ?= {
				has_variable = nd_crisis_talks
				var:nd_crisis_talks = 1
			}
		}
	}
}
```

Value (after `nd_display_yield_pressure` in the values file):

```
# Weeks until the target is pressed again (nd_crisis_weekly_tick fires the
# event on the tick at which the counter reaches the interval), from either
# side. At least 1: the soonest is next week.
nd_display_next_pressure_weeks = {
	value = 0
	if = {
		limit = {
			nd_is_crisis_owner = yes
			has_variable = nd_crisis_pressure_weeks
		}
		add = nd_crisis_pressure_interval_weeks
		subtract = var:nd_crisis_pressure_weeks
	}
	else_if = {
		limit = {
			nd_is_crisis_target = yes
			exists = var:nd_crisis_opponent
		}
		var:nd_crisis_opponent = {
			if = {
				limit = { has_variable = nd_crisis_pressure_weeks }
				add = nd_crisis_pressure_interval_weeks
				subtract = var:nd_crisis_pressure_weeks
			}
		}
	}
	min = 1
}
```

Line helper (`nuclear_crisis_effects.txt`, after `nd_crisis_clear_figures`):

```
# Country scope, display only: one breakdown line for a stored part, when it
# is set and non-zero (nd_crisis_*_breakdown_sgui). KEY is passed literally so
# organize_loc.py sees it.
nd_crisis_breakdown_line = {
	if = {
		limit = {
			has_variable = $C$
			NOT = { var:$C$ = 0 }
		}
		custom_tooltip_no_bullet = $KEY$
	}
}
```

- [ ] **Step 4: Display handlers**

Append to `nuclear_deterrence_sguis.txt` (and add the six names to its header's display-handler list):

```
# ---- Which side are we on? (the panel's move rows) ---------------------------
nd_crisis_we_issued_sgui = {
	scope = country
	is_shown = {
		nd_is_crisis_owner = yes
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = { }
}

nd_crisis_we_are_target_sgui = {
	scope = country
	is_shown = {
		nd_is_crisis_target = yes
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = { }
}

nd_crisis_private_sgui = {
	scope = country
	is_shown = {
		nd_is_crisis_owner = yes
		nd_crisis_is_public = no
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = { }
}

# ---- Script-built text: breakdowns and the next pressure event ---------------
# Printed with ExecuteTooltip; every line reads our own stored figures
# (nd_crisis_refresh_figures mirrors them onto both parties).
nd_crisis_pressure_breakdown_sgui = {
	scope = country
	is_shown = {
		nd_in_crisis = yes
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = {
		nd_crisis_breakdown_line = { C = nd_yp_base KEY = nd_yp_base_line }
		nd_crisis_breakdown_line = { C = nd_yp_answer KEY = nd_yp_answer_line }
		nd_crisis_breakdown_line = { C = nd_yp_protector KEY = nd_yp_protector_line }
		nd_crisis_breakdown_line = { C = nd_yp_credibility KEY = nd_yp_credibility_line }
		nd_crisis_breakdown_line = { C = nd_yp_alert KEY = nd_yp_alert_line }
		nd_crisis_breakdown_line = { C = nd_yp_danger KEY = nd_yp_danger_line }
		nd_crisis_breakdown_line = { C = nd_yp_exercise KEY = nd_yp_exercise_line }
		nd_crisis_breakdown_line = { C = nd_yp_temperament KEY = nd_yp_temperament_line }
		nd_crisis_breakdown_line = { C = nd_yp_war KEY = nd_yp_war_line }
		nd_crisis_breakdown_line = { C = nd_yp_follow_through KEY = nd_yp_follow_through_line }
		custom_tooltip_no_bullet = nd_yp_total_line
	}
}

nd_crisis_danger_breakdown_sgui = {
	scope = country
	is_shown = {
		nd_in_crisis = yes
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = {
		nd_crisis_breakdown_line = { C = nd_cd_stage KEY = nd_cd_stage_line }
		nd_crisis_breakdown_line = { C = nd_cd_issuer_readiness KEY = nd_cd_issuer_readiness_line }
		nd_crisis_breakdown_line = { C = nd_cd_target_readiness KEY = nd_cd_target_readiness_line }
		nd_crisis_breakdown_line = { C = nd_cd_public KEY = nd_cd_public_line }
		nd_crisis_breakdown_line = { C = nd_cd_counter KEY = nd_cd_counter_line }
		nd_crisis_breakdown_line = { C = nd_cd_reliability KEY = nd_cd_reliability_line }
		nd_crisis_breakdown_line = { C = nd_cd_weeks KEY = nd_cd_weeks_line }
		nd_crisis_breakdown_line = { C = nd_cd_talks KEY = nd_cd_talks_line }
		nd_crisis_breakdown_line = { C = nd_cd_backed KEY = nd_cd_backed_line }
		nd_crisis_breakdown_line = { C = nd_cd_exercise KEY = nd_cd_exercise_line }
		if = {
			limit = {
				has_variable = nd_cd_dampened
				var:nd_cd_dampened = 1
			}
			custom_tooltip_no_bullet = nd_cd_dampened_line
		}
		custom_tooltip_no_bullet = nd_cd_total_line
	}
}

nd_crisis_next_pressure_sgui = {
	scope = country
	is_shown = {
		nd_in_crisis = yes
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = {
		if = {
			limit = { NOT = { nd_crisis_stage_at_least = { STAGE = 2 } } }
			custom_tooltip_no_bullet = nd_next_pressure_none
		}
		else_if = {
			limit = { nd_crisis_talks_open_either = yes }
			custom_tooltip_no_bullet = nd_next_pressure_paused
		}
		else = {
			custom_tooltip_no_bullet = nd_next_pressure_weeks
		}
	}
}
```

- [ ] **Step 5: Custom localization**

Append to `nuclear_deterrence_custom_loc.txt` (every block ends in an unconditional fallback; targets are plain text):

```
# ---- The crisis panel's role-aware words (2026-09-25 spec §3) ----------------
nd_crisis_pressure_label = {
	type = country
	random_valid = no
	text = {
		trigger = { nd_is_crisis_target = yes }
		localization_key = nd_w_crisis_pressure_label_us
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_w_crisis_pressure_label
	}
}

nd_crisis_concede_label = {
	type = country
	random_valid = no
	text = {
		trigger = { nd_is_crisis_target = yes }
		localization_key = nd_w_crisis_concede_label_us
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_w_crisis_concede_label_them
	}
}

nd_crisis_concession_short = {
	type = country
	random_valid = no
	text = {
		trigger = { nd_crisis_dispute_is = { D = 1 } }
		localization_key = nd_concession_short_1
	}
	text = {
		trigger = { nd_crisis_dispute_is = { D = 2 } }
		localization_key = nd_concession_short_2
	}
	text = {
		trigger = { nd_crisis_dispute_is = { D = 3 } }
		localization_key = nd_concession_short_3
	}
	text = {
		trigger = { nd_crisis_dispute_is = { D = 4 } }
		localization_key = nd_concession_short_4
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_concession_short_5
	}
}

nd_crisis_concession_long = {
	type = country
	random_valid = no
	text = {
		trigger = { nd_crisis_dispute_is = { D = 1 } }
		localization_key = nd_concession_long_1
	}
	text = {
		trigger = { nd_crisis_dispute_is = { D = 2 } }
		localization_key = nd_concession_long_2
	}
	text = {
		trigger = { nd_crisis_dispute_is = { D = 3 } }
		localization_key = nd_concession_long_3
	}
	text = {
		trigger = { nd_crisis_dispute_is = { D = 4 } }
		localization_key = nd_concession_long_4
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_concession_long_5
	}
}

nd_crisis_ft_label = {
	type = country
	random_valid = no
	text = {
		trigger = { nd_is_crisis_target = yes }
		localization_key = nd_w_crisis_ft_label_them
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_w_crisis_ft_label_us
	}
}

nd_crisis_ft_word = {
	type = country
	random_valid = no
	text = {
		trigger = {
			has_variable = nd_ft_reason
			var:nd_ft_reason <= 2
		}
		localization_key = nd_ft_word_backed
	}
	text = {
		trigger = {
			has_variable = nd_ft_reason
			var:nd_ft_reason <= 4
		}
		localization_key = nd_ft_word_uncertain
	}
	text = {
		trigger = { has_variable = nd_ft_reason }
		localization_key = nd_ft_word_bluff
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_ft_word_unknown
	}
}

nd_crisis_ft_reason = {
	type = country
	random_valid = no
	text = {
		trigger = {
			has_variable = nd_ft_reason
			var:nd_ft_reason = 1
		}
		localization_key = nd_ft_reason_1
	}
	text = {
		trigger = {
			has_variable = nd_ft_reason
			var:nd_ft_reason = 2
		}
		localization_key = nd_ft_reason_2
	}
	text = {
		trigger = {
			has_variable = nd_ft_reason
			var:nd_ft_reason = 3
		}
		localization_key = nd_ft_reason_3
	}
	text = {
		trigger = {
			has_variable = nd_ft_reason
			var:nd_ft_reason = 4
		}
		localization_key = nd_ft_reason_4
	}
	text = {
		trigger = {
			has_variable = nd_ft_reason
			var:nd_ft_reason = 5
		}
		localization_key = nd_ft_reason_5
	}
	text = {
		trigger = {
			has_variable = nd_ft_reason
			var:nd_ft_reason = 6
		}
		localization_key = nd_ft_reason_6
	}
	text = {
		trigger = {
			has_variable = nd_ft_reason
			var:nd_ft_reason = 7
		}
		localization_key = nd_ft_reason_7
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_ft_reason_unknown
	}
}

nd_crisis_stakes_short = {
	type = country
	random_valid = no
	text = {
		trigger = { nd_is_crisis_target = yes }
		localization_key = nd_stakes_short_target
	}
	text = {
		trigger = { nd_crisis_is_public = yes }
		localization_key = nd_stakes_short_public
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_stakes_short_private
	}
}

nd_crisis_stakes_long = {
	type = country
	random_valid = no
	text = {
		trigger = { nd_is_crisis_target = yes }
		localization_key = nd_stakes_long_target
	}
	text = {
		trigger = { nd_crisis_is_public = yes }
		localization_key = nd_stakes_long_public
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_stakes_long_private
	}
}

# What would move THIS crisis to its next stage (§0.3's rules, by stage).
nd_crisis_stage_next = {
	type = country
	random_valid = no
	text = {
		trigger = { nd_crisis_stage_at_least = { STAGE = 3 } }
		localization_key = nd_stage_next_3
	}
	text = {
		trigger = { nd_crisis_stage_at_least = { STAGE = 2 } }
		localization_key = nd_stage_next_2
	}
	text = {
		trigger = { always = yes }
		localization_key = nd_stage_next_1
	}
}
```

- [ ] **Step 6: The widget**

In `nuclear_deterrence_widget.gui`, inside the live-crisis `nd_panel`:

1. Change the pressure row's label to `text = "nd_w_crisis_pressure_label_value"` and its tooltip blockoverride to:

```
			blockoverride "row_tooltip" {
				tooltip = "[Concatenate( Localize( 'nd_w_crisis_pressure_tt' ), GetScriptedGui('nd_crisis_pressure_breakdown_sgui').ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ) )]"
			}
```

2. Change the danger row's tooltip blockoverride to:

```
			blockoverride "row_tooltip" {
				tooltip = "[Concatenate( Localize( 'nd_w_crisis_danger_tt' ), GetScriptedGui('nd_crisis_danger_breakdown_sgui').ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ) )]"
			}
```

3. After the pressure row, before `nd_text = { text = "nd_w_crisis_actions_legend" … }`, add four rows:

```
		nd_row = {
			blockoverride "row_label" {
				text = "nd_w_crisis_concede_label_value"
			}
			blockoverride "row_value" {
				text = "nd_w_crisis_concession_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "nd_w_crisis_concession_tt"
			}
		}
		nd_row = {
			blockoverride "row_label" {
				text = "nd_w_crisis_ft_label_value"
			}
			blockoverride "row_value" {
				text = "nd_w_crisis_ft_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "nd_w_crisis_ft_tt"
			}
		}
		nd_row = {
			blockoverride "row_label" {
				text = "nd_w_crisis_next_pressure_label"
			}
			blockoverride "row_value" {
				text = "[GetScriptedGui('nd_crisis_next_pressure_sgui').ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
			}
			blockoverride "row_tooltip" {
				tooltip = "nd_w_crisis_next_pressure_tt"
			}
		}
		nd_row = {
			blockoverride "row_label" {
				text = "nd_w_crisis_stakes_label"
			}
			blockoverride "row_value" {
				text = "nd_w_crisis_stakes_value"
			}
			blockoverride "row_tooltip" {
				tooltip = "nd_w_crisis_stakes_tt"
			}
		}
```

4. Gate four of the five move rows by adding a `visible` line as the first line inside each `nd_choice_row = {`:
   - the row with `text = "nd_w_crisis_act_public"`: `visible = "[GetScriptedGui('nd_crisis_private_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"`
   - `nd_w_crisis_act_exercise`: `visible = "[GetScriptedGui('nd_armed_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"`
   - `nd_w_crisis_act_yield`: `visible = "[GetScriptedGui('nd_crisis_we_are_target_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"`
   - `nd_w_crisis_act_back_down`: `visible = "[GetScriptedGui('nd_crisis_we_issued_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"`

5. Change the stage row's tooltip blockoverride to `tooltip = "nd_w_crisis_stage_tt"` (unchanged key; its text gains the next-stage line in Step 7).

6. Update the file header: the move rows are hidden for the side that cannot make them, by display handlers (the op-branching rule is untouched); name the new handlers.

- [ ] **Step 7: Loc**

Replace `nd_w_crisis_pressure_tt`, `nd_w_crisis_danger_tt`, `nd_w_crisis_actions_legend`, `nd_w_crisis_stage_tt`; add the rest:

```yaml
 nd_w_crisis_pressure_tt:0 "#tooltip_header Pressure to concede#!\n$TOOLTIP_DELIMITER$\nWhat pushes the threatened government to give way, part by part. When it is pressed, below #v 50#! it does not concede; from #v 70#! it concedes about half the time, and from #v 85#! about two times in three. A human government in its place sees the same figure.\n$TOOLTIP_DELIMITER$\n"
 nd_w_crisis_danger_tt:0 "#tooltip_header Danger#!\n$TOOLTIP_DELIMITER$\nHow easily this could go wrong. As it rises, accidents and misreadings grow likelier on both sides, and at #v 70#! a Confrontation turns Acute. It fires nothing by itself.\n$TOOLTIP_DELIMITER$\n"
 nd_w_crisis_actions_legend:0 "Our moves. The other side answers through its own decisions. The crisis also ends if the war or play it is about ends."
 nd_w_crisis_stage_tt:0 "#tooltip_header Stage#!\n$TOOLTIP_DELIMITER$\nWarning, confrontation, acute. Stages are not a ladder to war: a crisis can be settled at any of them.\n\n[JournalEntry.GetCountry.GetCustom('nd_crisis_stage_next')]"
 nd_stage_next_1:0 "Now a private #v Warning#!. It becomes a #v Confrontation#! if the threat is refused or answered with a counter-threat, made public, or backed by an exercise."
 nd_stage_next_2:0 "Now a #v Confrontation#!. It turns #R Acute#! at danger #v 70#!, when the threatening side holds firm at its deadline, when it is at High Alert while the other side is at Heightened or higher, if the play becomes a war, or after an intercepted launch."
 nd_stage_next_3:0 "Now #R Acute#!, the last stage. From here it ends only in an outcome."
 nd_w_crisis_pressure_label_value:0 "[JournalEntry.GetCountry.GetCustom('nd_crisis_pressure_label')]"
 nd_w_crisis_pressure_label_us:0 "Pressure on us"
 nd_w_crisis_concede_label_value:0 "[JournalEntry.GetCountry.GetCustom('nd_crisis_concede_label')]"
 nd_w_crisis_concede_label_them:0 "If they concede"
 nd_w_crisis_concede_label_us:0 "If we concede"
 nd_w_crisis_concession_value:0 "[JournalEntry.GetCountry.GetCustom('nd_crisis_concession_short')]"
 nd_w_crisis_concession_tt:0 "#tooltip_header What conceding costs#!\n$TOOLTIP_DELIMITER$\n[JournalEntry.GetCountry.GetCustom('nd_crisis_concession_long')]"
 nd_concession_short_1:0 "Loses the play"
 nd_concession_short_2:0 "War support #R -35#!"
 nd_concession_short_3:0 "Leaves the protected alone"
 nd_concession_short_4:0 "Programme frozen #v 10#! years"
 nd_concession_short_5:0 "Stands down #v 24#! months"
 nd_concession_long_1:0 "The side that concedes backs down in the diplomatic play, and the other side wins it — war goals and all."
 nd_concession_long_2:0 "The side that concedes loses #R 35#! war support in the war, which can force it to capitulate."
 nd_concession_long_3:0 "The side that concedes leaves the protected country alone: it backs down in the play, or loses #R 35#! war support in that war."
 nd_concession_long_4:0 "The side that concedes has its weapons programme frozen for #v 10#! years."
 nd_concession_long_5:0 "The side that concedes stands its forces down to Routine, held there for #v 24#! months."
 nd_w_crisis_ft_label_value:0 "[JournalEntry.GetCountry.GetCustom('nd_crisis_ft_label')]"
 nd_w_crisis_ft_label_us:0 "Can we carry it out?"
 nd_w_crisis_ft_label_them:0 "Can they carry it out?"
 nd_w_crisis_ft_value:0 "[JournalEntry.GetCountry.GetCustom('nd_crisis_ft_word')]"
 nd_w_crisis_ft_tt:0 "#tooltip_header Follow-through#!\n$TOOLTIP_DELIMITER$\n[JournalEntry.GetCountry.GetCustom('nd_crisis_ft_reason')]\n\nDoctrine is public: every government knows whether a threat can be carried out, and weighs it."
 nd_ft_word_backed:0 "#G Backed#!"
 nd_ft_word_uncertain:0 "#Y Uncertain#!"
 nd_ft_word_bluff:0 "#R A bluff#!"
 nd_ft_word_unknown:0 "—"
 nd_ft_reason_1:0 "Backed: the threatening side's doctrine permits a nuclear strike in this war now. Pressure to concede +10."
 nd_ft_reason_2:0 "Backed: under Nuclear Compellence, a threat that is defied licenses a strike. Pressure to concede +10."
 nd_ft_reason_3:0 "Uncertain: Flexible First Use would allow a strike only if this became a war that went badly or reached core territory."
 nd_ft_reason_4:0 "Uncertain: Existential Deterrence covers what is at stake here — survival, core territory, or a protected country — if this becomes a war."
 nd_ft_reason_5:0 "A bluff: the threatening side's doctrine does not allow a first strike here. Pressure to concede -25."
 nd_ft_reason_6:0 "A bluff: the threatening side's Rules of War law forbids a nuclear strike. Pressure to concede -25."
 nd_ft_reason_7:0 "A bluff: the threatening side has pledged No First Use. Pressure to concede -35."
 nd_ft_reason_unknown:0 "Not yet assessed: the figures update each week."
 nd_w_crisis_next_pressure_label:0 "Next pressure"
 nd_w_crisis_next_pressure_tt:0 "From the Confrontation stage on, the threatened government is asked again every #v 6#! weeks whether to concede. Open talks pause it."
 nd_next_pressure_none:0 "Not before a Confrontation"
 nd_next_pressure_paused:0 "Paused: talks are open"
 nd_next_pressure_weeks:0 "In #v [THIS.ScriptValue('nd_display_next_pressure_weeks')|0]#! weeks"
 nd_w_crisis_stakes_label:0 "Our stakes"
 nd_w_crisis_stakes_value:0 "[JournalEntry.GetCountry.GetCustom('nd_crisis_stakes_short')]"
 nd_w_crisis_stakes_tt:0 "#tooltip_header What this crisis does to our credibility#!\n$TOOLTIP_DELIMITER$\n[JournalEntry.GetCountry.GetCustom('nd_crisis_stakes_long')]"
 nd_stakes_short_public:0 "#G +15#! / #R -15#!"
 nd_stakes_short_private:0 "#G +10#! / #R -5#!"
 nd_stakes_short_target:0 "#R -5#! / #G +10#!"
 nd_stakes_long_public:0 "If they concede, our credibility rises by 15. If we back down it falls by 15, and by 5 more if our doctrine made it a bluff; if the deadline lapses, by 10. A mutual stand-down costs 5, unless we were defending."
 nd_stakes_long_private:0 "If they concede, our credibility rises by 10. If we back down it falls by 5. A mutual stand-down raises it by 5."
 nd_stakes_long_target:0 "If we concede, our credibility falls by 5. If they back down, ours rises by 10. A mutual stand-down raises it by 5."
 nd_yp_base_line:0 "#v [THIS.Var('nd_yp_base').GetValue|+0]#!  Starting point"
 nd_yp_answer_line:0 "#v [THIS.Var('nd_yp_answer').GetValue|+0]#!  Whether the threatened side can answer in kind"
 nd_yp_protector_line:0 "#v [THIS.Var('nd_yp_protector').GetValue|+0]#!  An armed protector behind the threatened side"
 nd_yp_credibility_line:0 "#v [THIS.Var('nd_yp_credibility').GetValue|+0]#!  The threatening side's credibility"
 nd_yp_alert_line:0 "#v [THIS.Var('nd_yp_alert').GetValue|+0]#!  The threatening side at High Alert"
 nd_yp_danger_line:0 "#v [THIS.Var('nd_yp_danger').GetValue|+0]#!  How dangerous the crisis has become"
 nd_yp_exercise_line:0 "#v [THIS.Var('nd_yp_exercise').GetValue|+0]#!  An exercise they can see"
 nd_yp_temperament_line:0 "#v [THIS.Var('nd_yp_temperament').GetValue|+0]#!  The threatened ruler's temperament"
 nd_yp_war_line:0 "#v [THIS.Var('nd_yp_war').GetValue|+0]#!  How the war is going for the threatened side"
 nd_yp_follow_through_line:0 "#v [THIS.Var('nd_yp_follow_through').GetValue|+0]#!  Whether the threat can be carried out"
 nd_yp_total_line:0 "#v = [THIS.ScriptValue('nd_display_yield_pressure')|0]#!  (held between 0 and 100)"
 nd_cd_stage_line:0 "#v [THIS.Var('nd_cd_stage').GetValue|+0]#!  The stage"
 nd_cd_issuer_readiness_line:0 "#v [THIS.Var('nd_cd_issuer_readiness').GetValue|+0]#!  The threatening side's readiness"
 nd_cd_target_readiness_line:0 "#v [THIS.Var('nd_cd_target_readiness').GetValue|+0]#!  The threatened side's readiness"
 nd_cd_public_line:0 "#v [THIS.Var('nd_cd_public').GetValue|+0]#!  The threat is public"
 nd_cd_counter_line:0 "#v [THIS.Var('nd_cd_counter').GetValue|+0]#!  It was answered with a counter-threat"
 nd_cd_reliability_line:0 "#v [THIS.Var('nd_cd_reliability').GetValue|+0]#!  The threatening side's command reliability"
 nd_cd_weeks_line:0 "#v [THIS.Var('nd_cd_weeks').GetValue|+0]#!  How long it has run"
 nd_cd_talks_line:0 "#v [THIS.Var('nd_cd_talks').GetValue|+0]#!  Talks are open"
 nd_cd_backed_line:0 "#v [THIS.Var('nd_cd_backed').GetValue|+0]#!  A protector has declared for the threatened side"
 nd_cd_exercise_line:0 "#v [THIS.Var('nd_cd_exercise').GetValue|+0]#!  An exercise is under way"
 nd_cd_dampened_line:0 "#v ×0.7#!  The threatened side has no arsenal and no armed protector"
 nd_cd_total_line:0 "#v = [THIS.ScriptValue('nd_display_crisis_danger')|0]#!  (held between 0 and 100)"
```

Keep the existing `nd_w_crisis_pressure_label` ("Pressure on the target") as the fallback target.

- [ ] **Step 8: Run tests**

Run: `python3 -m unittest test_nuclear_deterrence -v`
Expected: all PASS (existing op tests unchanged: no op code moved).

- [ ] **Step 9: Format, BOM check and commit**

```bash
python3 scripts/format_paradox_tabs.py common/scripted_guis/nuclear_deterrence_sguis.txt common/scripted_effects/nuclear_crisis_effects.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/script_values/nuclear_deterrence_values.txt common/customizable_localization/nuclear_deterrence_custom_loc.txt gui/journal_entry_widgets/nuclear_deterrence_widget.gui
for f in gui/journal_entry_widgets/nuclear_deterrence_widget.gui common/scripted_guis/nuclear_deterrence_sguis.txt common/customizable_localization/nuclear_deterrence_custom_loc.txt; do head -c3 "$f" | xxd | grep -q efbbbf || echo "NO BOM: $f"; done
git add common/scripted_guis/nuclear_deterrence_sguis.txt common/scripted_effects/nuclear_crisis_effects.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/script_values/nuclear_deterrence_values.txt common/customizable_localization/nuclear_deterrence_custom_loc.txt gui/journal_entry_widgets/nuclear_deterrence_widget.gui localization/english/te_miscellaneous_l_english.yml test_nuclear_deterrence.py
git commit -m "Nuclear crisis panel: our moves only, the concession, follow-through, stakes and breakdowns" -m "The issuer no longer sees Concede, a public crisis no longer offers Go public, and Exercise shows only when armed, all through display handlers. New rows name what conceding costs, whether the threat is backed or a bluff, when the next pressure comes, and the credibility stakes. The pressure and danger tooltips list every stored part.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

---

### Task 8: Docs, reload check, PR 1

**Files:**
- Modify: `docs/systems/nuclear_crisis_design.md` (§0.3, §0.7, §0.9)
- Modify: `docs/systems/mod_systems.md` (§ Nuclear Deterrence and Crisis Diplomacy → **Crises**, **Launch gates**)
- Modify: `docs/systems/journal_entry_systems.md` (CRLF; § Nuclear Deterrence Widget)
- Modify: `docs/guides/scripting_best_practices.md` (one bullet)

- [ ] **Step 1: Docs**

`nuclear_crisis_design.md`:
- §0.3, after the credibility list: a **Follow-through** paragraph (the seven `nd_ft_reason` codes, the pressure part, the called-bluff −5, the AI rule) and an **Outcome notice** paragraph (pending record, `.6` applies it, flush, the concession stays at yielding).
- §0.7: add "A strike through a crisis option now needs the war-law gate too (it used to skip it)."
- §0.9: append the seven in-game checks from the spec's *Testing* section, numbered 17–23, plus 24: "the accessors first used here render: `[THIS.ScriptValue(…)]` in the ultimatum's confirmation box (`nd_tt_open_f_credibility`), `[THIS.Var(…)]` in the panel breakdowns, `[ROOT.GetCountry.GetCustom('nd_crisis_concession_past')]` in the outcome notice"; and 25: "with Canada winning battles against us, the pressure breakdown shows no +15 'how the war is going' line for Canada" (the `nd_is_losing_war_to` fix).

`mod_systems.md` **Crises** paragraph: append "`nd_crisis_refresh_figures` is the one writer of the crisis's numbers and stores every part on both parties; the outcome notice (`nuclear_crisis.6`) applies each side's consequences from a pending record." **Launch gates** paragraph: append "`nd_war_law_permits_strategic_strike` / `_tactical_strike` carry the Rules of War gate for the strike actions and the crisis strike options alike."

`journal_entry_systems.md` (Edit only; keep CRLF): in § Nuclear Deterrence Widget, extend **Handlers** with the six new display handlers and **Areas (crisis)** with the four new rows, the role-gated moves and the breakdown tooltips. Then verify:

```bash
f=docs/systems/journal_entry_systems.md; [ "$(grep -c $'\r$' $f)" = "$(wc -l < $f)" ] && echo CRLF-ok
```

`scripting_best_practices.md`: add under the nuclear/gates material (or at the end):

```markdown
- **A second path to the same action must repeat the action's gates — share them as a scripted trigger.** The crisis deadline's "carry out the threat" dispatched a strike through the same effect as `nuke.txt` but checked only doctrine and pledges; the Rules of War gate lived inline in the diplomatic action, so a country under Limited War could strike through a crisis. `nd_war_law_permits_strategic_strike` now serves both.
```

- [ ] **Step 2: Game-independent checks**

```bash
ls test_*.py | grep -v test_reload_post_load | sed 's/\.py$//' | VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent xargs ~/src/Vic3TimelineExtended/.venv/bin/python -m unittest
~/src/Vic3TimelineExtended/.venv/bin/ruff check . || python3 -m ruff check .
python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt' '*.gui')
python3 scripts/analysis/check_localization_files.py
```

Expected: all pass.

- [ ] **Step 3: Reload-check on a second server**

Start it (background task, not `&`):

```bash
VIC3_SKIP_DIGESTS_FETCH=1 ~/src/Vic3TimelineExtended/.venv/bin/python -c "import mod_state_server as m; m.PORT=8951; m.main()"
```

Then:

```bash
curl -s -X POST http://127.0.0.1:8951/reload | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({k: d.get(k) for k in ('warnings','generators_wrote_files','parse_failures','reparsed_after_generators')}, indent=1))"
```

Expected: no `warnings` entry naming a file this branch touched, `parse_failures` empty. For each warning that does name one (likely candidates: `silent_variable_audit` on `.6`'s option, `event_context_audit` on `.6`, `loc_coverage_audit`), fix it in the file, or — only when the flag is intended — add the audit's check-tagged `# REVIEWED 2026-09-25 (<check>): <why>` comment where that audit documents it. Reload again until clean. Then sort `git status`: discard `docs/engine/*` (`git checkout -- docs/engine/`); commit `localization/` churn that `organize_loc` produced for this branch's keys. Stop the server by its PID file.

- [ ] **Step 4: Commit docs and churn**

```bash
git add docs/systems/nuclear_crisis_design.md docs/systems/mod_systems.md docs/systems/journal_entry_systems.md docs/guides/scripting_best_practices.md localization/english/
git commit -m "Docs: nuclear crisis communication, bluffs, outcome notice, war-law gate" -m "Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

- [ ] **Step 5: File the organize_loc issue (spec §2.4)**

```bash
gh issue create --label enhancement --label tooling --title "organize_loc.py: keys built from \$PARAM\$ are stranded in te_unused" --body "organize_loc.py marks a key used only when its literal token appears in a .txt/.yml/.gui file. Keys built by a parameterised scripted effect — nd_tt_readiness_target_\$R\$, nd_tt_doctrine_adopted_\$D\$, nd_tt_authority_adopted_\$A\$, nd_tt_\$VAR\$_\$OP\$ in the nuclear posture effects — are therefore moved to te_unused_l_english.yml although they render. Proposal: when a token contains \$…\$, expand it against the literal values the callers pass (or treat the prefix as a wildcard) before deciding a key is unused. Workaround used meanwhile: pass loc keys literally (nd_crisis_breakdown_line takes KEY = <key>)."
```

- [ ] **Step 6: Independent review, then PR**

Dispatch a fresh reviewer agent over `git diff origin/main...HEAD` with the spec. Fix what it confirms. Then write the PR body to `/tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/1d58d4ec-3693-4687-8777-b48b5e48353c/scratchpad/pr1_body.md` (summary per spec section, the war-law bug, the in-game checklist, ending with the attribution block from the session), push, and open:

```bash
git push -u origin nuclear-crisis-communication
gh pr create --base main --title "Nuclear crisis: say what it does, price bluffs, close the crisis-strike law hole" --body-file /tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/1d58d4ec-3693-4687-8777-b48b5e48353c/scratchpad/pr1_body.md
```

Do not merge: the owner play-tests first.

---

# PR 2 — At Home (§4)

Cut `nuclear-at-home` from PR 1's tip in the same worktree (`git switch -c nuclear-at-home`); open the PR with `--base main` (CLAUDE.md § Stacked PRs).

### Task 9: Interest-group classes by Rules of War stance

**Files:**
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (replace `nd_ig_leader_is_hawk`, `nd_ig_leader_is_dove`, `nd_ig_class_warfighting`, `nd_ig_class_professional`, `nd_ig_class_dove`, `nd_ig_class_business`)
- Modify: `common/scripted_effects/nuclear_crisis_effects.txt` (`nd_reward_hawks`, `nd_reward_doves`, `nd_crisis_act_fight_conventional`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (every `nd_ig_class_*` use, including `nd_refresh_domestic_stance`)
- Modify: `events/nuclear_incident_events.txt` (7 sites)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Produces (IG scope): `nd_ig_stance_militarist_full`, `nd_ig_stance_militarist_mild`, `nd_ig_stance_restraint_full`, `nd_ig_stance_restraint_mild`, `nd_ig_stance_militarist`, `nd_ig_stance_restraint`, `nd_ig_stance_full`, `nd_ig_is_fixed_class`, `nd_ig_class_professional`, `nd_ig_class_business`, `nd_ig_class_militarist`, `nd_ig_class_restraint`, `nd_ig_is_hawk`, `nd_ig_is_restraint`.

- [ ] **Step 1: Write the failing test**

```python
class TestInterestGroupClasses(unittest.TestCase):
    OLD = ("nd_ig_leader_is_hawk", "nd_ig_leader_is_dove", "nd_ig_class_warfighting", "nd_ig_class_dove")
    NEW = ("nd_ig_stance_militarist_full", "nd_ig_stance_militarist_mild", "nd_ig_stance_restraint_full",
           "nd_ig_stance_restraint_mild", "nd_ig_stance_militarist", "nd_ig_stance_restraint",
           "nd_ig_stance_full", "nd_ig_is_fixed_class", "nd_ig_class_professional", "nd_ig_class_business",
           "nd_ig_class_militarist", "nd_ig_class_restraint", "nd_ig_is_hawk", "nd_ig_is_restraint")

    def test_new_triggers_exist(self):
        t = read(TRIGGERS)
        for name in self.NEW:
            self.assertRegex(t, rf"(?m)^{name} = \{{", name)

    def test_old_triggers_are_gone_everywhere(self):
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").glob("*.txt")):
            text = strip_comments(read(path))
            for name in self.OLD:
                self.assertNotIn(name, text, f"{path.name} still uses {name}")

    def test_stances_read_the_rules_of_war_laws(self):
        t = strip_comments(read(TRIGGERS))
        for name in ("nd_ig_stance_militarist_full", "nd_ig_stance_restraint_full"):
            body = block(t, name)
            self.assertIn("law_type:law_total_war", body)
            self.assertIn("law_type:law_limited_war", body)

    def test_rewards_pay_hawks_and_doves(self):
        effects = strip_comments(read(CRISIS_EFFECTS))
        self.assertIn("nd_ig_is_hawk = yes", block(effects, "nd_reward_hawks"))
        self.assertIn("nd_ig_is_restraint = yes", block(effects, "nd_reward_doves"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestInterestGroupClasses -v`
Expected: FAIL.

- [ ] **Step 3: Replace the class triggers**

Delete `nd_ig_leader_is_hawk`, `nd_ig_leader_is_dove`, `nd_ig_class_warfighting`, `nd_ig_class_professional`, `nd_ig_class_dove`, `nd_ig_class_business` and their comments; insert:

```
# ----------------------------------------------------------------------------
# INTEREST GROUPS AND THE BOMB (2026-09-25 spec §4). IG scope.
# ----------------------------------------------------------------------------
# The Armed Forces are professional officers and the Industrialists business,
# whatever their politics; every other group is militarist or restraint by
# its Rules of War stance, or has no view. A stance already folds in the
# leader's ideology, so a fascist-led Intelligentsia is militarist with no
# special case. law_stance compares one law at a time, so "its stance on Total
# War beats its stance on Limited War" is spelled out. Strongly approving is a
# full view (±2); approving is a mild one (±1).

nd_ig_stance_militarist_full = {
	law_stance = {
		law = law_type:law_total_war
		value > approve
	}
	NOT = {
		law_stance = {
			law = law_type:law_limited_war
			value > approve
		}
	}
}

nd_ig_stance_militarist_mild = {
	law_stance = {
		law = law_type:law_total_war
		value > neutral
	}
	NOT = {
		law_stance = {
			law = law_type:law_total_war
			value > approve
		}
	}
	NOT = {
		law_stance = {
			law = law_type:law_limited_war
			value > neutral
		}
	}
}

nd_ig_stance_restraint_full = {
	law_stance = {
		law = law_type:law_limited_war
		value > approve
	}
	NOT = {
		law_stance = {
			law = law_type:law_total_war
			value > approve
		}
	}
}

nd_ig_stance_restraint_mild = {
	law_stance = {
		law = law_type:law_limited_war
		value > neutral
	}
	NOT = {
		law_stance = {
			law = law_type:law_limited_war
			value > approve
		}
	}
	NOT = {
		law_stance = {
			law = law_type:law_total_war
			value > neutral
		}
	}
}

nd_ig_stance_militarist = {
	OR = {
		nd_ig_stance_militarist_full = yes
		nd_ig_stance_militarist_mild = yes
	}
}

nd_ig_stance_restraint = {
	OR = {
		nd_ig_stance_restraint_full = yes
		nd_ig_stance_restraint_mild = yes
	}
}

nd_ig_stance_full = {
	OR = {
		nd_ig_stance_militarist_full = yes
		nd_ig_stance_restraint_full = yes
	}
}

nd_ig_is_fixed_class = {
	OR = {
		is_interest_group_type = ig_armed_forces
		is_interest_group_type = ig_industrialists
	}
}

nd_ig_class_professional = {
	is_interest_group_type = ig_armed_forces
}

nd_ig_class_business = {
	is_interest_group_type = ig_industrialists
}

nd_ig_class_militarist = {
	nd_ig_is_fixed_class = no
	nd_ig_stance_militarist = yes
}

nd_ig_class_restraint = {
	nd_ig_is_fixed_class = no
	nd_ig_stance_restraint = yes
}

# Who crisis outcomes pay (§4.5). Hawks: militarist groups and leans, and the
# Armed Forces unless they lean restraint. Restraint: restraint groups and
# leans.
nd_ig_is_hawk = {
	OR = {
		nd_ig_stance_militarist = yes
		AND = {
			nd_ig_class_professional = yes
			nd_ig_stance_restraint = no
		}
	}
}

nd_ig_is_restraint = {
	nd_ig_stance_restraint = yes
}
```

- [ ] **Step 4: Switch the call sites**

- `nd_reward_hawks` (crisis effects): replace `OR = { nd_ig_class_warfighting = yes nd_ig_class_professional = yes }` with `nd_ig_is_hawk = yes`.
- `nd_reward_doves`: `nd_ig_class_dove = yes` → `nd_ig_is_restraint = yes`.
- `nd_crisis_act_fight_conventional` and every other `limit = { nd_ig_class_warfighting = yes }` in `nuclear_deterrence_effects.txt` and `nuclear_incident_events.txt`: → `limit = { nd_ig_stance_militarist = yes }`.
- Every `limit = { nd_ig_class_dove = yes }` in those files: → `limit = { nd_ig_is_restraint = yes }`.
- `nd_refresh_domestic_stance`: `nd_ig_class_warfighting` → `nd_ig_class_militarist`; `nd_ig_class_dove` → `nd_ig_class_restraint` (Task 10 rewrites the effect).

Verify: `git grep -n "nd_ig_class_warfighting\|nd_ig_class_dove\|nd_ig_leader_is_" -- common events` prints nothing.

- [ ] **Step 5: Run tests, format, commit**

```bash
python3 -m unittest test_nuclear_deterrence -v
python3 scripts/format_paradox_tabs.py common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_crisis_effects.txt common/scripted_effects/nuclear_deterrence_effects.txt events/nuclear_incident_events.txt
git add common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_crisis_effects.txt common/scripted_effects/nuclear_deterrence_effects.txt events/nuclear_incident_events.txt test_nuclear_deterrence.py
git commit -m "Nuclear posture: interest groups classed by their Rules of War stance" -m "The Armed Forces are professional officers and the Industrialists business; every other group is militarist or restraint by its stance on Total War against Limited War, strongly or mildly. Crisis and incident reactions pay hawks and restraint groups by the new classes.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

Expected: tests PASS.

---

### Task 10: Each interest group's opinion, stored on the group

**Files:**
- Modify: `common/script_values/nuclear_deterrence_values.txt` (replace `nd_stance_warfighting_value`, `nd_stance_professional_value`, `nd_stance_dove_value`, `nd_stance_business_value`)
- Modify: `common/scripted_triggers/nuclear_deterrence_triggers.txt` (`nd_ig_posture_judged`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_refresh_domestic_stance`, `nd_clear_domestic_stance`, `nd_ig_set_band`)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: Task 9's triggers.
- Produces: triggers `nd_posture_judged` (country) and `nd_ig_posture_judged` (IG); IG variables `nd_ig_class` (1 militarist, 2 restraint, 3 professional, 4 business), `nd_ig_lean` (0 none, 1 hawkish, 2 restrained), `nd_ig_strength` (1 mild, 2 full), `nd_ig_term_doctrine`, `nd_ig_term_readiness`, `nd_ig_term_authority`, `nd_ig_term_strain`, `nd_ig_term_business`, `nd_ig_stance`; country value `nd_display_stance_months_left`. Task 11 prints them.

- [ ] **Step 1: Write the failing test**

```python
IG_VARS = ["nd_ig_class", "nd_ig_lean", "nd_ig_strength", "nd_ig_term_doctrine", "nd_ig_term_readiness",
           "nd_ig_term_authority", "nd_ig_term_strain", "nd_ig_term_business", "nd_ig_stance"]


class TestInterestGroupOpinion(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.effects = strip_comments(read(EFFECTS))

    def test_country_level_stance_values_are_gone(self):
        for old in ("nd_stance_warfighting_value", "nd_stance_professional_value",
                    "nd_stance_dove_value", "nd_stance_business_value"):
            self.assertNotRegex(self.values, rf"(?m)^{old} = \{{")

    def test_ig_values_exist(self):
        for name in ("nd_ig_doctrine_militarist_value", "nd_ig_doctrine_restraint_value",
                     "nd_ig_doctrine_professional_value", "nd_ig_term_doctrine_value",
                     "nd_ig_term_readiness_value", "nd_ig_term_authority_value", "nd_ig_term_strain_value",
                     "nd_ig_term_business_value", "nd_ig_stance_value", "nd_display_stance_months_left"):
            self.assertRegex(self.values, rf"(?m)^{name} = \{{", name)

    def test_store_writes_and_clear_removes_every_variable(self):
        store = block(self.effects, "nd_ig_store_opinion")
        clear = block(self.effects, "nd_ig_clear_opinion")
        for var in IG_VARS:
            self.assertIn(f"name = {var} value", store, var)
            self.assertIn(f"remove_variable = {var}", clear, var)

    def test_band_reads_the_stored_stance(self):
        band = block(self.effects, "nd_ig_set_band")
        self.assertIn("var:nd_ig_stance >= 2", band)
        self.assertNotIn("owner", band)

    def test_business_terms_do_not_wait_for_tenure(self):
        body = block(self.values, "nd_ig_term_business_value")
        self.assertNotIn("nd_ig_posture_judged", body)
        for name in ("nd_ig_term_doctrine_value", "nd_ig_term_readiness_value",
                     "nd_ig_term_authority_value", "nd_ig_term_strain_value"):
            self.assertIn("nd_ig_posture_judged = yes", block(self.values, name), name)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestInterestGroupOpinion -v`
Expected: FAIL.

- [ ] **Step 3: The tenure trigger**

Add after Task 9's block in the triggers file:

```
# Country scope: our posture is judged at home only once the doctrine has
# been held six months (§0.2 of the nuclear design: months, not a toggle).
# The business terms do not wait.
nd_posture_judged = {
	nd_is_initialized = yes
	has_variable = nd_doctrine_months
	var:nd_doctrine_months >= nd_stance_tenure_months
}

# IG scope: the same question, about the group's country.
nd_ig_posture_judged = {
	owner = { nd_posture_judged = yes }
}
```

- [ ] **Step 4: Replace the four country stance values**

Delete `nd_stance_warfighting_value`, `nd_stance_professional_value`, `nd_stance_dove_value`, `nd_stance_business_value` and their comments; insert:

```
# ----------------------------------------------------------------------------
# AT HOME — one interest group's opinion of our posture (2026-09-25 spec §4.2).
# IG scope; reads the owner's posture. nd_refresh_domestic_stance stores each
# term on the group, and the At Home list prints the stored terms.
# ----------------------------------------------------------------------------

# The doctrine tables a group can judge with.
nd_ig_doctrine_militarist_value = {
	value = 0
	owner = {
		if = {
			limit = { nd_doctrine_nfu = yes }
			add = -2
		}
		else_if = {
			limit = { nd_doctrine_existential = yes }
			add = -1
		}
		else_if = {
			limit = { nd_doctrine_compellence = yes }
			add = 1
		}
		else_if = {
			limit = { nd_doctrine_warfighting = yes }
			add = 2
		}
	}
}

nd_ig_doctrine_restraint_value = {
	value = 0
	owner = {
		if = {
			limit = { nd_doctrine_nfu = yes }
			add = 2
		}
		else_if = {
			limit = { nd_doctrine_existential = yes }
			add = 1
		}
		else_if = {
			limit = { nd_doctrine_flexible = yes }
			add = -1
		}
		else = {
			add = -2
		}
	}
}

nd_ig_doctrine_professional_value = {
	value = 0
	owner = {
		if = {
			limit = {
				OR = {
					nd_doctrine_nfu = yes
					nd_doctrine_warfighting = yes
				}
			}
			add = -1
		}
		else_if = {
			limit = { nd_doctrine_flexible = yes }
			add = 1
		}
	}
}

# A militarist or restraint stance picks its table, for any group (a class,
# or the Armed Forces' and Industrialists' lean); the Armed Forces with no
# lean judge as officers; the Industrialists with none have no doctrine view.
# A mild stance is capped at ±1.
nd_ig_term_doctrine_value = {
	value = 0
	if = {
		limit = { nd_ig_posture_judged = yes }
		if = {
			limit = { nd_ig_stance_militarist = yes }
			add = nd_ig_doctrine_militarist_value
		}
		else_if = {
			limit = { nd_ig_stance_restraint = yes }
			add = nd_ig_doctrine_restraint_value
		}
		else_if = {
			limit = { nd_ig_class_professional = yes }
			add = nd_ig_doctrine_professional_value
		}
		if = {
			limit = {
				OR = {
					nd_ig_stance_militarist = yes
					nd_ig_stance_restraint = yes
				}
				nd_ig_stance_full = no
			}
			min = -1
			max = 1
		}
	}
}

nd_ig_term_readiness_value = {
	value = 0
	if = {
		limit = { nd_ig_posture_judged = yes }
		if = {
			limit = { nd_ig_class_militarist = yes }
			owner = {
				if = {
					limit = { var:nd_readiness = 1 }
					add = -1
				}
				else_if = {
					limit = { var:nd_readiness = 3 }
					add = 1
				}
			}
		}
		else_if = {
			limit = { nd_ig_class_restraint = yes }
			owner = {
				if = {
					limit = { var:nd_readiness = 3 }
					add = -1
				}
			}
		}
		else_if = {
			limit = { nd_ig_class_professional = yes }
			owner = {
				if = {
					limit = {
						var:nd_readiness = 1
						nd_has_plausible_attacker = yes
					}
					add = -1
				}
				else_if = {
					limit = { var:nd_readiness = 2 }
					add = 1
				}
			}
		}
	}
}

nd_ig_term_authority_value = {
	value = 0
	if = {
		limit = {
			nd_ig_posture_judged = yes
			nd_ig_class_restraint = yes
			owner = { nd_authority_launch_on_warning = yes }
		}
		add = -1
	}
}

nd_ig_term_strain_value = {
	value = 0
	if = {
		limit = {
			nd_ig_posture_judged = yes
			nd_ig_class_professional = yes
			owner = {
				var:nd_readiness = 3
				has_variable = nd_strain
				var:nd_strain >= 50
			}
		}
		add = -1
	}
}

# Prolonged alerts and open crises are bad for business. Not tenure-gated.
nd_ig_term_business_value = {
	value = 0
	if = {
		limit = { nd_ig_class_business = yes }
		owner = {
			if = {
				limit = {
					nd_is_initialized = yes
					var:nd_readiness = 3
					has_variable = nd_readiness_months
					var:nd_readiness_months >= 3
				}
				add = -1
			}
			if = {
				limit = { nd_crisis_stage_at_least = { STAGE = 2 } }
				add = -1
			}
		}
	}
}

# The capped total the approval band is read from: ±1 for a mild militarist
# or restraint group, ±2 otherwise.
nd_ig_stance_value = {
	value = nd_ig_term_doctrine_value
	add = nd_ig_term_readiness_value
	add = nd_ig_term_authority_value
	add = nd_ig_term_strain_value
	add = nd_ig_term_business_value
	if = {
		limit = {
			nd_ig_is_fixed_class = no
			nd_ig_stance_full = no
		}
		min = -1
		max = 1
	}
	min = -2
	max = 2
}

# Country scope: months until our posture starts being judged at home.
nd_display_stance_months_left = {
	value = nd_stance_tenure_months
	if = {
		limit = { has_variable = nd_doctrine_months }
		subtract = var:nd_doctrine_months
	}
	min = 0
}
```

- [ ] **Step 5: Rewrite the refresh, band and clear effects**

Replace `nd_refresh_domestic_stance`, `nd_clear_domestic_stance` and `nd_ig_set_band` (keep `nd_ig_clear_band` unchanged) with:

```
nd_refresh_domestic_stance = {
	# Marks that bands may be on our interest groups, so the country pulse can
	# take them off if the entry deactivates (nd_country_monthly_cleanup).
	set_variable = { name = nd_stance_applied value = 1 }
	# The country-level class scores before 2026-09-25, in an old save.
	if = {
		limit = { has_variable = nd_stance_warfighting }
		remove_variable = nd_stance_warfighting
	}
	if = {
		limit = { has_variable = nd_stance_professional }
		remove_variable = nd_stance_professional
	}
	if = {
		limit = { has_variable = nd_stance_dove }
		remove_variable = nd_stance_dove
	}
	if = {
		limit = { has_variable = nd_stance_business }
		remove_variable = nd_stance_business
	}
	every_interest_group = {
		if = {
			limit = {
				OR = {
					nd_ig_is_fixed_class = yes
					nd_ig_stance_militarist = yes
					nd_ig_stance_restraint = yes
				}
			}
			nd_ig_store_opinion = yes
			nd_ig_set_band = yes
		}
		else = {
			nd_ig_clear_opinion = yes
			nd_ig_clear_band = yes
		}
	}
}

nd_clear_domestic_stance = {
	every_interest_group = {
		nd_ig_clear_band = yes
		nd_ig_clear_opinion = yes
	}
}

# IG scope: store this group's class, lean, strength, each term and the total.
nd_ig_store_opinion = {
	if = {
		limit = { nd_ig_class_militarist = yes }
		set_variable = { name = nd_ig_class value = 1 }
	}
	else_if = {
		limit = { nd_ig_class_restraint = yes }
		set_variable = { name = nd_ig_class value = 2 }
	}
	else_if = {
		limit = { nd_ig_class_professional = yes }
		set_variable = { name = nd_ig_class value = 3 }
	}
	else = {
		set_variable = { name = nd_ig_class value = 4 }
	}
	if = {
		limit = {
			nd_ig_is_fixed_class = yes
			nd_ig_stance_militarist = yes
		}
		set_variable = { name = nd_ig_lean value = 1 }
	}
	else_if = {
		limit = {
			nd_ig_is_fixed_class = yes
			nd_ig_stance_restraint = yes
		}
		set_variable = { name = nd_ig_lean value = 2 }
	}
	else = {
		set_variable = { name = nd_ig_lean value = 0 }
	}
	if = {
		limit = {
			OR = {
				nd_ig_stance_militarist = yes
				nd_ig_stance_restraint = yes
			}
			nd_ig_stance_full = no
		}
		set_variable = { name = nd_ig_strength value = 1 }
	}
	else = {
		set_variable = { name = nd_ig_strength value = 2 }
	}
	set_variable = { name = nd_ig_term_doctrine value = nd_ig_term_doctrine_value }
	set_variable = { name = nd_ig_term_readiness value = nd_ig_term_readiness_value }
	set_variable = { name = nd_ig_term_authority value = nd_ig_term_authority_value }
	set_variable = { name = nd_ig_term_strain value = nd_ig_term_strain_value }
	set_variable = { name = nd_ig_term_business value = nd_ig_term_business_value }
	set_variable = { name = nd_ig_stance value = nd_ig_stance_value }
}

nd_ig_clear_opinion = {
	if = {
		limit = { has_variable = nd_ig_class }
		remove_variable = nd_ig_class
	}
	if = {
		limit = { has_variable = nd_ig_lean }
		remove_variable = nd_ig_lean
	}
	if = {
		limit = { has_variable = nd_ig_strength }
		remove_variable = nd_ig_strength
	}
	if = {
		limit = { has_variable = nd_ig_term_doctrine }
		remove_variable = nd_ig_term_doctrine
	}
	if = {
		limit = { has_variable = nd_ig_term_readiness }
		remove_variable = nd_ig_term_readiness
	}
	if = {
		limit = { has_variable = nd_ig_term_authority }
		remove_variable = nd_ig_term_authority
	}
	if = {
		limit = { has_variable = nd_ig_term_strain }
		remove_variable = nd_ig_term_strain
	}
	if = {
		limit = { has_variable = nd_ig_term_business }
		remove_variable = nd_ig_term_business
	}
	if = {
		limit = { has_variable = nd_ig_stance }
		remove_variable = nd_ig_stance
	}
}

# IG scope. Idempotent across months: whatever band is on comes off, and the
# one nd_ig_stance asks for goes on.
nd_ig_set_band = {
	nd_ig_clear_band = yes
	if = {
		limit = { var:nd_ig_stance >= 2 }
		add_modifier = { name = nd_posture_approval_plus_2 }
	}
	else_if = {
		limit = { var:nd_ig_stance >= 1 }
		add_modifier = { name = nd_posture_approval_plus_1 }
	}
	else_if = {
		limit = { var:nd_ig_stance <= -2 }
		add_modifier = { name = nd_posture_approval_minus_2 }
	}
	else_if = {
		limit = { var:nd_ig_stance <= -1 }
		add_modifier = { name = nd_posture_approval_minus_1 }
	}
}
```

Check with `git grep -n "nd_ig_set_band = {" -- common` that no caller still passes `VAR = …`.

- [ ] **Step 6: Run tests, format, commit**

```bash
python3 -m unittest test_nuclear_deterrence -v
python3 scripts/format_paradox_tabs.py common/script_values/nuclear_deterrence_values.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_deterrence_effects.txt
git add common/script_values/nuclear_deterrence_values.txt common/scripted_triggers/nuclear_deterrence_triggers.txt common/scripted_effects/nuclear_deterrence_effects.txt test_nuclear_deterrence.py
git commit -m "Nuclear posture: each interest group's opinion is stored on the group" -m "nd_refresh_domestic_stance scores every group by its class and lean, stores each term and the capped total on the group, and sets the approval band from that total. Every term but the Industrialists' business concerns still waits for six months of doctrine tenure.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

Expected: PASS. (The At Home rows now show their fallback words until Task 11 replaces them.)

---

### Task 11: At Home lists each group with its numbers; docs; PR 2

**Files:**
- Modify: `common/scripted_guis/nuclear_deterrence_sguis.txt` (`nd_home_list_sgui`)
- Modify: `common/scripted_effects/nuclear_deterrence_effects.txt` (`nd_home_line`)
- Modify: `gui/journal_entry_widgets/nuclear_deterrence_widget.gui` (At Home panel)
- Modify: `common/customizable_localization/nuclear_deterrence_custom_loc.txt` (delete the four `nd_stance_*_word` blocks)
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Modify: docs (`journal_entry_systems.md`, `nuclear_crisis_design.md` §0.2, `mod_systems.md` **Domestic stance**)
- Test: `test_nuclear_deterrence.py`

**Interfaces:**
- Consumes: Task 10's IG variables, `nd_posture_judged` and `nd_display_stance_months_left`.

**Amended from spec §4.4.** The spec drew a `dynamicgridbox` over `Country.AccessActiveInterestGroups` with a per-row tooltip. No JE widget in this mod has proven a dynamic list, and a datamodel item's tooltip loses the `JournalEntry` context (gui_modding_guide.md gotchas #15 and #24). The list is therefore script-built text through a display handler (the UN ledger's proven pattern), with `[THIS.GetInterestGroup.GetName]` (vanilla `04_negotiation_scripted_effects.txt`), and each group's terms print as an inline second line instead of a tooltip. Say so in the PR body.

- [ ] **Step 1: Write the failing test**

```python
HOME_LINES = ["nd_home_line_militarist", "nd_home_line_militarist_mild", "nd_home_line_restraint",
              "nd_home_line_restraint_mild", "nd_home_line_officers", "nd_home_line_officers_hawkish",
              "nd_home_line_officers_restrained", "nd_home_line_business", "nd_home_line_business_hawkish",
              "nd_home_line_business_restrained"]
HOME_TERMS = ["nd_home_terms_militarist", "nd_home_terms_restraint", "nd_home_terms_officers",
              "nd_home_terms_business", "nd_home_terms_business_lean"]


class TestAtHome(unittest.TestCase):
    def test_every_class_line_is_printed_and_localised(self):
        body = block(strip_comments(read(EFFECTS)), "nd_home_line")
        for key in HOME_LINES + HOME_TERMS:
            self.assertIn(f"custom_tooltip_no_bullet = {key}", body, key)
            self.assertIn("THIS.Var('nd_ig_", loc_value(key), key)
        for key in HOME_LINES:
            self.assertIn("[THIS.GetInterestGroup.GetName]", loc_value(key), key)

    def test_list_is_drawn_and_old_rows_are_gone(self):
        gui = read(GUI)
        self.assertIn("nd_home_list_sgui", gui)
        for old in ("nd_w_home_warfighting_value", "nd_w_home_professional_value",
                    "nd_w_home_dove_value", "nd_w_home_business_value"):
            self.assertNotIn(old, gui)
        custom = strip_comments(read(CUSTOM_LOC))
        self.assertNotIn("nd_stance_warfighting_word", custom)

    def test_list_handler_is_display_only(self):
        body = block(strip_comments(read(SGUIS)), "nd_home_list_sgui")
        self.assertIn("is_valid = { always = no }", body)
        self.assertIn("every_interest_group", body)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m unittest test_nuclear_deterrence.TestAtHome -v`
Expected: FAIL.

- [ ] **Step 3: The line effect and the handler**

Add to `nuclear_deterrence_effects.txt` after `nd_ig_set_band`:

```
# IG scope, display only (nd_home_list_sgui): this group's line and its terms.
# Both lines sit at this scope level, so each group's pair prints together.
nd_home_line = {
	if = {
		limit = { var:nd_ig_class = 1 }
		if = {
			limit = { var:nd_ig_strength = 2 }
			custom_tooltip_no_bullet = nd_home_line_militarist
		}
		else = {
			custom_tooltip_no_bullet = nd_home_line_militarist_mild
		}
		custom_tooltip_no_bullet = nd_home_terms_militarist
	}
	else_if = {
		limit = { var:nd_ig_class = 2 }
		if = {
			limit = { var:nd_ig_strength = 2 }
			custom_tooltip_no_bullet = nd_home_line_restraint
		}
		else = {
			custom_tooltip_no_bullet = nd_home_line_restraint_mild
		}
		custom_tooltip_no_bullet = nd_home_terms_restraint
	}
	else_if = {
		limit = { var:nd_ig_class = 3 }
		if = {
			limit = { var:nd_ig_lean = 1 }
			custom_tooltip_no_bullet = nd_home_line_officers_hawkish
		}
		else_if = {
			limit = { var:nd_ig_lean = 2 }
			custom_tooltip_no_bullet = nd_home_line_officers_restrained
		}
		else = {
			custom_tooltip_no_bullet = nd_home_line_officers
		}
		custom_tooltip_no_bullet = nd_home_terms_officers
	}
	else = {
		if = {
			limit = { var:nd_ig_lean = 1 }
			custom_tooltip_no_bullet = nd_home_line_business_hawkish
		}
		else_if = {
			limit = { var:nd_ig_lean = 2 }
			custom_tooltip_no_bullet = nd_home_line_business_restrained
		}
		else = {
			custom_tooltip_no_bullet = nd_home_line_business
		}
		if = {
			limit = { var:nd_ig_lean > 0 }
			custom_tooltip_no_bullet = nd_home_terms_business_lean
		}
		else = {
			custom_tooltip_no_bullet = nd_home_terms_business
		}
	}
}
```

Add to `nuclear_deterrence_sguis.txt`:

```
# ---- At Home: each interest group with a view, and its numbers ----------------
# Script-built text (ExecuteTooltip). Reads the variables nd_refresh_domestic_stance
# stores on each group; the numbers are the ones in the group's approval breakdown.
nd_home_list_sgui = {
	scope = country
	is_shown = {
		nd_is_armed = yes
		nd_is_initialized = yes
	}
	is_valid = { always = no }
	ai_is_valid = { always = no }
	effect = {
		if = {
			limit = {
				any_interest_group = { has_variable = nd_ig_class }
			}
			every_interest_group = {
				limit = { has_variable = nd_ig_class }
				nd_home_line = yes
			}
		}
		else = {
			custom_tooltip_no_bullet = nd_home_none
		}
		if = {
			limit = { nd_posture_judged = no }
			custom_tooltip_no_bullet = nd_home_waiting
		}
	}
}
```

- [ ] **Step 4: The widget**

In the At Home `nd_panel`, keep `nd_text = { text = "nd_w_home_legend" … }` and replace the four `nd_row` blocks with:

```
		nd_script_line = {
			datacontext = "[GetScriptedGui('nd_home_list_sgui')]"
			blockoverride "line_text" {
				text = "[ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
			}
		}
```

Delete the four `nd_stance_*_word` blocks from the custom-loc file, and the keys `nd_w_home_*_label`, `nd_w_home_*_value`, `nd_w_home_*_tt`, `nd_stance_word_*` from the loc file (confirm with `git grep -n "nd_stance_word_\|nd_w_home_warfighting\|nd_w_home_professional\|nd_w_home_dove\|nd_w_home_business" -- common gui` that nothing still references them).

- [ ] **Step 5: Loc**

```yaml
 nd_w_home_legend:0 "How each interest group receives our posture. The Armed Forces judge it as officers and the Industrialists as business; every other group by its stance on the Rules of War — #v Total War#! makes it militarist, #v Limited War#! restrained. A group's own politics can make the Armed Forces or the Industrialists #v hawkish#! or #v restrained#! about doctrine too. Totals are capped at ±2, or ±1 for a mild view; the number is the one in the group's approval breakdown."
 nd_home_line_militarist:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — militarist"
 nd_home_line_militarist_mild:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — militarist (mild)"
 nd_home_line_restraint:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — restraint"
 nd_home_line_restraint_mild:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — restraint (mild)"
 nd_home_line_officers:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — officers"
 nd_home_line_officers_hawkish:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — officers, hawkish"
 nd_home_line_officers_restrained:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — officers, restrained"
 nd_home_line_business:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — business"
 nd_home_line_business_hawkish:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — business, hawkish"
 nd_home_line_business_restrained:0 "#v [THIS.Var('nd_ig_stance').GetValue|+0]#!  [THIS.GetInterestGroup.GetName] — business, restrained"
 nd_home_terms_militarist:0 "#lore       doctrine [THIS.Var('nd_ig_term_doctrine').GetValue|+0] · readiness [THIS.Var('nd_ig_term_readiness').GetValue|+0]#!"
 nd_home_terms_restraint:0 "#lore       doctrine [THIS.Var('nd_ig_term_doctrine').GetValue|+0] · readiness [THIS.Var('nd_ig_term_readiness').GetValue|+0] · launch authority [THIS.Var('nd_ig_term_authority').GetValue|+0]#!"
 nd_home_terms_officers:0 "#lore       doctrine [THIS.Var('nd_ig_term_doctrine').GetValue|+0] · readiness [THIS.Var('nd_ig_term_readiness').GetValue|+0] · crew strain [THIS.Var('nd_ig_term_strain').GetValue|+0]#!"
 nd_home_terms_business:0 "#lore       long alerts and open crises [THIS.Var('nd_ig_term_business').GetValue|+0]#!"
 nd_home_terms_business_lean:0 "#lore       long alerts and open crises [THIS.Var('nd_ig_term_business').GetValue|+0] · doctrine [THIS.Var('nd_ig_term_doctrine').GetValue|+0]#!"
 nd_home_none:0 "#lore No interest group holds a view on our posture.#!"
 nd_home_waiting:0 "#lore Opinions of our doctrine and readiness start in #v [THIS.ScriptValue('nd_display_stance_months_left')|0]#! months; the Industrialists' business concerns count already. Reviewed monthly.#!"
```

- [ ] **Step 6: Tests, format, BOM**

```bash
python3 -m unittest test_nuclear_deterrence -v
python3 scripts/format_paradox_tabs.py common/scripted_guis/nuclear_deterrence_sguis.txt common/scripted_effects/nuclear_deterrence_effects.txt common/customizable_localization/nuclear_deterrence_custom_loc.txt gui/journal_entry_widgets/nuclear_deterrence_widget.gui
for f in gui/journal_entry_widgets/nuclear_deterrence_widget.gui common/scripted_guis/nuclear_deterrence_sguis.txt; do head -c3 "$f" | xxd | grep -q efbbbf || echo "NO BOM: $f"; done
```

Expected: PASS, no "NO BOM".

- [ ] **Step 7: Docs**

- `nuclear_crisis_design.md` §0.2, **Domestic stance** list: replace the four class bullets with the new classes, strength and leans; say the opinion is stored on the group and At Home prints it.
- `mod_systems.md` **Domestic stance** paragraph: "classes are by interest-group type (Armed Forces, Industrialists) and Rules of War stance (`nd_ig_class_*`, `nd_ig_stance_*`); `nd_refresh_domestic_stance` stores each group's terms and total on the group (`nd_ig_*`) and sets the band from it."
- `journal_entry_systems.md` (Edit only, CRLF check as in Task 8): At Home is now the script-built list `nd_home_list_sgui`.

- [ ] **Step 8: Reload-check, review, PR 2**

Repeat Task 8 Steps 2–3 on this branch. Commit the code and docs:

```bash
git add common/scripted_guis/nuclear_deterrence_sguis.txt common/scripted_effects/nuclear_deterrence_effects.txt common/customizable_localization/nuclear_deterrence_custom_loc.txt gui/journal_entry_widgets/nuclear_deterrence_widget.gui localization/english/ docs/systems/nuclear_crisis_design.md docs/systems/mod_systems.md docs/systems/journal_entry_systems.md test_nuclear_deterrence.py
git commit -m "At Home lists each interest group with its approval and terms" -m "A script-built list replaces the four class rows: each group with a view, its class and lean, the approval number its breakdown shows, and the terms behind it; a footer while doctrine tenure is under six months.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01J7jQeEPzj8XPNiXozzxnYk"
```

Independent reviewer over `git diff nuclear-crisis-communication...HEAD`; fix confirmed findings. Write the PR body (it depends on PR 1; say so, and that it must merge after it), then:

```bash
git push -u origin nuclear-at-home
gh pr create --base main --title "Nuclear posture: At Home by interest group, classed by Rules of War" --body-file /tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/1d58d4ec-3693-4687-8777-b48b5e48353c/scratchpad/pr2_body.md
```

Do not merge.
