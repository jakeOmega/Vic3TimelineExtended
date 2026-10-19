# Demographics: the engine's birth and death lines as script-only types (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** every birth and mortality line on a law, technology or institution moves to a script-only modifier type. The
mod re-applies them to each state while the census doesn't set births and deaths, and under Full the census applies
only the ones it doesn't model.

**Architecture:** 36 lines on 29 carriers (14 of them on 9 vanilla laws, 22 the mod's) are moved, in two families:
- `state_demog_absorbed_*`: lines the census models;
- `state_demog_ontop_*`: lines it doesn't.

Each line moves the same way: the engine field is cancelled (a vanilla line by an INJECT of its negative; a mod line by
editing the carrier), and the same value is carried on the family's type. The engine still sums the types per state,
scaled as it scales the fields (institution levels, Impact of Institutions), and script reads the sums with `modifier:`.
- **Rule off, Display only, or Full before a state's first census step:** a monthly state pulse applies a fixed-sign pair of
  static modifiers per field, multiplier = the two families' sum.
- **Full, once the census sets the state's rates:** that pulse clears the pairs. The census's term M applies the on-top
  family's births and deaths at the census's rate (as #885 does for the engine's state lines). It applies Private Health
  Insurance's wealth line through its own pair.
- **The census stops netting these lines out** (`te_demog_absorbed_*` ladders, `te_dg_w_sab` / `_sad`): under Full the
  engine no longer applies them.

**Tech Stack:** Paradox script (Victoria 3 1.14.5), the Python twin and harness (`scripts/analysis/demographics_*.py`),
the generator `scripts/generators/gen_demographics.py`, unittest with the repo's script interpreter
(`test_demographics_registry.py`'s `_Engine`).

**Spec:** this plan's "Design" section (owner, 2026-10-11) amends
`docs/superpowers/archive/plans/2026-10-10-demographics-phase2-engine-rates.md` §2 (the census's term M) and its Amendment
(owner decisions A and B, 2026-10-10). Read both; where they conflict, this plan's Design wins.

## Design (owner, 2026-10-11)

- **The point.** The owner's measure is gameplay, not file layout. With the rule off, a state gets the same births and
  deaths as vanilla: the same values, on the same pops, scaled the same way. Under Full the tooltips stop listing lines
  the census cancels, and the census never has to work out a line's size itself. #889's institution-impact mismatch
  can't recur, because the engine does the summing.
- **What moves:** every live `state_birth_rate_mult`, `state_mortality_mult`, `state_<pop type>_mortality_mult` and
  `state_mortality_wealth_mult` line in a law's `modifier` or `institution_modifier`, a technology's `modifier` or an
  institution's `modifier` (`DM.engine_rate_lines`). On 2026-10-11 that is 36 lines on 29 carriers; the table is in Task 2.
- **What stays engine-applied:** everything else (decrees, principles, amendments, companies, buildings and their
  methods, events, the code static modifiers such as starvation, pollution, devastation and turmoil). Under Full they
  remain lines on top, as today: state-level ones at the census's rate (#885), a pop's own at its bare curve.
- **Families.** A line goes to `absorbed` if the census models it today (`DM.absorbed_carriers`), to `ontop` otherwise
  (`P.ENGINE_LINES_ON_TOP`, `P.ENGINE_FIELDS_ON_TOP`). The family is now written on the carrier, so the files are the
  source of truth and the Python lists become derived.
- **Names.** Each type is named and described like the vanilla field it replaces (`$state_mortality_mult$`), so a law's
  tooltip reads as before. Its description adds one sentence: "Under the Demographics rule's Full setting, the census
  carries this effect in its own rates" (absorbed) or "...applies it at the census's rate" (on top). The re-applied pair
  is named "Laws and Institutions" in a state's breakdown. The census's own pair stays "Census: Births" / "Census:
  Deaths".
- **Timing (owner, 2026-10-11: refresh where the game says something changed).** `te_demog_lines_refresh` runs where
  the inputs change:
  - **on a new game**, after the lobby, in every state;
  - **on a law's activation** (`on_law_activated`, which fires for enactments and for laws script sets), in each of the
    country's states;
  - **on a change of owner** (`on_state_owner_change`) and **on incorporation** (`on_state_incorporation`), in that state;
  - **every month** (`on_monthly_pulse_state`), the fallback for technologies and institution levels, which have no
    on-action, and for old saves.

  A pair is touched only when its sum changed. The country-scope hooks fire the hidden state event `te_demog_events.4`
  in each state, so ROOT is the state, as the multiplier needs. A loaded old save gets the INJECT cancels at once and
  the pairs at its first monthly pulse.
- **The switch to the census.** The pulse applies the pairs unless the census is setting the state's rates
  (`te_demog_effects_run` and the state has `te_dg_mb`). The census's refresh clears them in the same effect that first
  sets M. So under Full a state keeps vanilla's lines until its first census step, the step reads them in the walk as it
  reads any line, and from then on the census applies what it doesn't model.
- **AI.** Vanilla gives every one of these fields `ai_value = 0`; the types copy it, so AI law choices don't change.
- **Releases.** A release has no Demographics rule, so `te_demog_effects_run` reads `always = no`. The new types, the
  INJECTs, the pairs and the monthly pulse ship and run. `scripts/release/comment_out_census_inputs.py` comments out only
  the census's own types (`demographics_modifier_types.txt`), so the new files must not be listed there.
- **Private Health Insurance under Full** (owner decision 1 below): the census applies its wealth line as
  `state_mortality_wealth_mult` = the line × the census's share of the bare curve (`te_dg_tb_d`), floored at
  `P.WEALTH_LINE_FLOOR` (−0.005: the richest pop, wealth 99, then dies at no less than half the census's rate).

## Owner decisions (2026-10-11)

1. **Private Health Insurance's wealth line under Full: (b)** (owner: "Sounds good"). The alternatives, for the record:
   - (a) At the census's rate, no floor. A wealth-99 pop at Ministry of Health level 5 then dies at about 1% of the
     census's rate (the owner's worry, 2026-10-10).
   - (b) At the census's rate, floored at −0.005 a wealth level. No pop dies at less than half the census's rate;
     levels above about 2.5 add nothing for the very richest.
   - (c) Not applied: the census's health-care access (+0.06 a level for Private Health Insurance) carries the law, and
     wealth inequality in mortality comes only from the bare curve.
2. **No month's lag** on a new game or after a law change or a change of owner (owner: "I'd prefer this... we do
   something similar on law changes for law inconsistency"). The refresh hooks are in Design, "Timing", and Task 4.
   Technologies and institution levels have no on-action, so they keep the monthly pulse.
3. **Execution:** native, with a fresh review of Tasks 4 and 5 (the risky script) and a fresh whole-branch review at the
   end (owner: "Sounds good!").

## Global Constraints

- Nothing changes outside Full **in gameplay**: same values, same pops, same scaling as vanilla; only the delivery and a
  state breakdown's names differ (owner, 2026-10-11).
- A static modifier is never applied with a negative multiplier: a fixed-sign pair per field (Global Constraints of the
  2026-10-10 plan).
- Each applied modifier has exactly one refresh site, run where ROOT is the state (CLAUDE.md, dynamic-modifier scaling
  pattern): the pairs in `te_demog_lines_refresh` (monthly state pulse, plus the census's clear), the census's own pairs
  in `te_demog_rates_apply`.
- Generated files are never hand-edited; `gen_demographics.py --check` stays clean.
- Every changed `.txt` keeps exactly one UTF-8 BOM and tab indentation (`scripts/format_paradox_tabs.py --check`).
- Loc keys are added to `localization/english/te_modifiers_l_english.yml` and `organize_loc.py --check` stays clean.

## Review Focus

1. **The rule changed mid-game, Disabled → Full and back.** A state never has both the pairs and the census's term, and
   never neither for more than a month (Task 4 `test_pairs_follow_the_census_term`).
2. **An unincorporated state.** Institution lines read 0 there, so its pairs carry only law and technology lines, as
   vanilla does (Task 4 `test_unincorporated_state_gets_no_institution_lines`).
3. **A state that changes owner, or a country that changes a law.** The pairs follow at once, as vanilla's lines would
   (Task 4 `test_refresh_runs_where_the_inputs_change`).
4. **A vanilla patch adds a birth or mortality line to a law or technology.** CI fails until it is moved (Task 2
   `test_no_carrier_applies_an_engine_birth_or_mortality_line`, run against the rebuilt `vanilla_parsed/`).
5. **Fast mode on the first Full step.** The walk's average multiplier still holds the pairs the refresh is clearing, so
   fast mode's term overshoots for one step. Task 5 `test_first_full_step_takes_the_pairs_off_fast_modes_average`
   subtracts them.

---

## File structure

| File | Change | Responsibility |
|---|---|---|
| `common/modifier_type_definitions/demographics_engine_line_types.txt` | create | the 9 script-only types (absorbed: births, deaths, 4 class deaths; on top: births, deaths, wealth deaths) |
| `localization/english/te_modifiers_l_english.yml` | modify | the types' names and descriptions; the pairs' names |
| `common/laws/te_demog_engine_line_injections.txt` | create | the 14 vanilla lines: cancel + type (INJECTs on 9 vanilla laws) |
| `common/laws/extra_laws.txt`, `common/technology/technologies/era_6.txt`, `era_7.txt`, `era_8.txt`, `era_10.txt`, `era_12.txt`, `common/institutions/extra_institutions.txt` | modify | the 22 mod lines: field → type, in place |
| `scripts/analysis/demographics_params.py` | modify | `ENGINE_LINE_FIELDS`, `ENGINE_LINE_TYPES`, `WEALTH_LINE_FLOOR` |
| `scripts/analysis/demographics_modifiers.py` | modify | `engine_lines()` (the moved lines, by family); `absorbed_carriers` and the on-top lists derived from it |
| `scripts/generators/gen_demographics.py` | modify | write the pairs, their script values and `te_demog_lines_refresh`; drop the state-level absorbed ladders |
| `common/static_modifiers/te_demog_line_modifiers_generated.txt` | create (generated) | 7 fields × up/down pairs |
| `common/script_values/te_demog_line_values_generated.txt` | create (generated) | `te_demog_line_<short>` (both families' sum) and `te_demog_line_<short>_applied` |
| `common/scripted_effects/te_demog_line_effects_generated.txt` | create (generated) | `te_demog_lines_refresh`, `te_demog_lines_clear` |
| `common/scripted_triggers/te_demog_triggers.txt` | modify | `te_demog_lines_apply` |
| `common/on_actions/te_demog_on_actions.txt` | modify | `on_monthly_pulse_state` → `te_demog_lines_on_action` |
| `common/scripted_effects/te_demog_rate_effects.txt` | modify | M with the on-top family; O_s less the pairs; the wealth pair; clear the pairs |
| `common/static_modifiers/te_demog_modifiers.txt` | modify | `te_demog_census_wealth_up` / `_down` |
| `scripts/analysis/demographics_model.py` | modify | `rate_term(..., added=)` |
| `scripts/analysis/demographics_harness.py` | modify | `predict` under the new design |
| `scripts/release/comment_out_census_inputs.py`, `test_release_census_inputs.py` | modify | the new files stay live in a release |
| tests: `test_demographics_registry.py`, `test_demographics_model.py`, `test_demographics_harness.py`, `test_gen_demographics.py` | modify | below |
| docs: `docs/systems/mod_systems.md`, the 2026-10-10 plan's §2, `docs/player_guide/08-states.md` (+ PDF), the results doc | modify | Task 8 |

---

### Task 1: The script-only types and their names

**Files:**
- Create: `common/modifier_type_definitions/demographics_engine_line_types.txt`
- Modify: `scripts/analysis/demographics_params.py` (after `ENGINE_FIELDS_ON_TOP`)
- Modify: `localization/english/te_modifiers_l_english.yml`
- Test: `test_demographics_registry.py` (new `class TestEngineLineTypes`)

**Interfaces:**
- Produces: `P.ENGINE_LINE_FIELDS` (tuple of the 7 engine fields), `P.ENGINE_LINE_TYPES`
  (`{(family, engine_field): type_name}`, family in `("absorbed", "ontop")`), `P.ENGINE_LINE_SHORT`
  (`{engine_field: short}`: `births`, `deaths`, `farmers_deaths`, `laborers_deaths`, `machinists_deaths`,
  `peasants_deaths`, `wealth_deaths`).

- [ ] **Step 1: Write the failing test**

```python
class TestEngineLineTypes(unittest.TestCase):
    """Owner, 2026-10-11: every engine birth and mortality line on a law, tech or institution is carried on a
    script-only type, named like the vanilla field it replaces, with vanilla's format and ai_value."""

    TYPES = ROOT / "common" / "modifier_type_definitions" / "demographics_engine_line_types.txt"

    def _vanilla_types(self):
        import json
        data = json.loads((ROOT / "vanilla_parsed" / "common" / "modifier_types.json").read_text(encoding="utf-8"))
        return data.get("data", data)

    def test_each_type_is_script_only_with_vanillas_format(self):
        blocks = _raw_blocks([self.TYPES])
        vanilla = self._vanilla_types()
        self.assertEqual(set(blocks), set(P.ENGINE_LINE_TYPES.values()))
        for (family, field), name in P.ENGINE_LINE_TYPES.items():
            body = blocks[name]
            self.assertIn("script_only = yes", body, name)
            for key in ("decimals", "color", "percent"):
                want = vanilla[field][1][key][1]
                self.assertRegex(body, rf"\b{key} = {re.escape(str(want))}\b", f"{name}: {key}")
            self.assertRegex(body, r"ai_value = 0\b", name)

    def test_names_splice_the_vanilla_fields(self):
        loc = _text(ROOT / "localization" / "english" / "te_modifiers_l_english.yml")
        for (family, field), name in P.ENGINE_LINE_TYPES.items():
            self.assertRegex(loc, rf'\n {name}:0 "\${field}\$"', name)
            self.assertIn(f" {name}_desc:0 \"${field}_desc$ ", loc, name)
```

- [ ] **Step 2: Run it to see it fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestEngineLineTypes`
Expected: ERROR, `module 'demographics_params' has no attribute 'ENGINE_LINE_TYPES'`.

- [ ] **Step 3: Add the parameters**

```python
# Owner, 2026-10-11: the engine's birth and mortality lines on laws, technologies and institutions move to script-only
# types, one per field and family (demographics_engine_line_types.txt); the mod re-applies them while the census
# doesn't set births and deaths (te_demog_lines_refresh), and under Full the census applies the on-top family.
ENGINE_LINE_FIELDS = ("state_birth_rate_mult", "state_mortality_mult", "state_farmers_mortality_mult",
                      "state_laborers_mortality_mult", "state_machinists_mortality_mult",
                      "state_peasants_mortality_mult", "state_mortality_wealth_mult")
ENGINE_LINE_SHORT = {"state_birth_rate_mult": "births", "state_mortality_mult": "deaths",
                     "state_farmers_mortality_mult": "farmers_deaths", "state_laborers_mortality_mult": "laborers_deaths",
                     "state_machinists_mortality_mult": "machinists_deaths",
                     "state_peasants_mortality_mult": "peasants_deaths",
                     "state_mortality_wealth_mult": "wealth_deaths"}
ENGINE_LINE_TYPES = {
    ("absorbed", "state_birth_rate_mult"): "state_demog_absorbed_birth_rate_mult",
    ("absorbed", "state_mortality_mult"): "state_demog_absorbed_mortality_mult",
    ("absorbed", "state_farmers_mortality_mult"): "state_demog_absorbed_farmers_mortality_mult",
    ("absorbed", "state_laborers_mortality_mult"): "state_demog_absorbed_laborers_mortality_mult",
    ("absorbed", "state_machinists_mortality_mult"): "state_demog_absorbed_machinists_mortality_mult",
    ("absorbed", "state_peasants_mortality_mult"): "state_demog_absorbed_peasants_mortality_mult",
    ("ontop", "state_birth_rate_mult"): "state_demog_ontop_birth_rate_mult",
    ("ontop", "state_mortality_mult"): "state_demog_ontop_mortality_mult",
    ("ontop", "state_mortality_wealth_mult"): "state_demog_ontop_mortality_wealth_mult",
}
# Private Health Insurance's wealth line under Full (owner decision 1, option b): at the census's rate, at least this
# a wealth level, so a wealth-99 pop dies at no less than half the census's rate.
WEALTH_LINE_FLOOR = -0.005
```

- [ ] **Step 4: Create the types file.** Copy `decimals`, `color` and `percent` from vanilla's definition of each
  field (`<base_game>/game/common/modifier_type_definitions/00_modifier_types.txt`; `state_birth_rate_mult`:
  `decimals=0 color=good percent=yes`; `state_mortality_mult`: `decimals=0 color=bad percent=yes`;
  `state_mortality_wealth_mult`: `decimals=1 color=bad percent=yes`; the class fields as vanilla gives them). One block
  per type, BOM first. The formats (vanilla 1.14.5, all `ai_value = 0`):

  | type | decimals | color | percent |
  |---|---|---|---|
  | `state_demog_absorbed_birth_rate_mult`, `state_demog_ontop_birth_rate_mult` | 0 | good | yes |
  | `state_demog_absorbed_mortality_mult`, `state_demog_ontop_mortality_mult` | 0 | bad | yes |
  | `state_demog_absorbed_{farmers,laborers,machinists,peasants}_mortality_mult` | 0 | bad | yes |
  | `state_demog_ontop_mortality_wealth_mult` | 1 | bad | yes |


```
# demographics_engine_line_types.txt
#
# Owner, 2026-10-11 (docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md): the engine's birth and
# mortality lines on laws, technologies and institutions, carried as script-only types the engine sums but doesn't apply.
# The mod re-applies both families while the census doesn't set a state's births and deaths (te_demog_lines_refresh);
# under Full the census models the absorbed family and applies the on-top one at its rate (te_demog_rates_refresh).
# Not in demographics_modifier_types.txt: a release keeps these (scripts/release/comment_out_census_inputs.py).
state_demog_absorbed_birth_rate_mult = {
	decimals = 0
	color = good
	percent = yes
	game_data = {
		ai_value = 0
	}
	script_only = yes
}
```

  The other eight blocks differ only in name and the table's format; write all nine out (the test checks each).

- [ ] **Step 5: Add the loc.** For each type, in `te_modifiers_l_english.yml`:

```
 state_demog_absorbed_mortality_mult:0 "$state_mortality_mult$"
 state_demog_absorbed_mortality_mult_desc:0 "$state_mortality_mult_desc$ Under the Demographics rule's Full setting, the census carries this effect in its own rates."
 state_demog_ontop_mortality_mult:0 "$state_mortality_mult$"
 state_demog_ontop_mortality_mult_desc:0 "$state_mortality_mult_desc$ Under the Demographics rule's Full setting, the census applies it at its own rate."
```

  Then run `.venv/bin/python organize_loc.py` and keep what it moves.

- [ ] **Step 6: Run the tests.** Run: `.venv/bin/python -m unittest test_demographics_registry.TestEngineLineTypes`
  Expected: OK. Also `organize_loc.py --check` and `scripts/analysis/check_localization_files.py` clean.

- [ ] **Step 7: Commit** (`git add` the four files): "Demographics: script-only types for the engine's birth and death lines".

### Task 2: Move the 36 lines

**Files:**
- Create: `common/laws/te_demog_engine_line_injections.txt`
- Modify: the mod carriers listed in the table
- Modify: `scripts/analysis/demographics_modifiers.py` (`engine_lines`)
- Test: `test_demographics_registry.py` (`class TestEngineLinesMoved`)

**Interfaces:**
- Consumes: `P.ENGINE_LINE_TYPES`, `P.ENGINE_LINE_FIELDS` (Task 1).
- Produces: `DM.engine_lines(root=ROOT) -> {(kind, key, block, engine_field): (family, value)}`. kind is law, technology
  or institution; block is `modifier` or `institution_modifier`; value is the net of vanilla and the mod, as
  `engine_rate_lines` sums an INJECT.

The 36 lines (from `DM.engine_rate_lines`, 2026-10-11; "vanilla" means an INJECT cancel plus type in the new file, "mod" means
edit in place):

| kind | key | block | field | value | source | family |
|---|---|---|---|---|---|---|
| institution | institution_ministry_of_consumer_protection | modifier | state_mortality_mult | −0.01 | mod | absorbed |
| law | law_charitable_health_system | institution_modifier | state_mortality_mult | −0.03 | vanilla | absorbed |
| law | law_child_labor_allowed | modifier | state_farmers_mortality_mult | +0.05 | vanilla | absorbed |
| law | law_child_labor_allowed | modifier | state_laborers_mortality_mult | +0.05 | vanilla | absorbed |
| law | law_child_labor_allowed | modifier | state_machinists_mortality_mult | +0.05 | vanilla | absorbed |
| law | law_child_labor_allowed | modifier | state_peasants_mortality_mult | +0.05 | vanilla | absorbed |
| law | law_communal_child_rearing | modifier | state_birth_rate_mult | −0.20 | mod | ontop |
| law | law_full_equality_and_protection | modifier | state_birth_rate_mult | −0.01 | mod | ontop |
| law | law_mandatory_augmentation | institution_modifier | state_mortality_mult | −0.02 | mod | absorbed |
| law | law_medical_augmentation_only | institution_modifier | state_mortality_mult | −0.02 | mod | absorbed |
| law | law_no_womens_rights | modifier | state_birth_rate_mult | +0.05 | vanilla | absorbed |
| law | law_population_control_measures | modifier | state_birth_rate_mult | −0.10 | mod | ontop |
| law | law_private_health_insurance | institution_modifier | state_mortality_wealth_mult | −0.002 | vanilla | ontop |
| law | law_pro_natalist_subsidies | modifier | state_birth_rate_mult | +0.10 | mod | ontop |
| law | law_protected_class | modifier | state_birth_rate_mult | −0.10 | mod | absorbed |
| law | law_public_health_insurance | institution_modifier | state_mortality_mult | −0.05 | vanilla | absorbed |
| law | law_regulated_augmentation_market | institution_modifier | state_mortality_mult | −0.02 | mod | absorbed |
| law | law_restricted_child_labor | modifier | state_farmers_mortality_mult | +0.02 | vanilla | absorbed |
| law | law_restricted_child_labor | modifier | state_laborers_mortality_mult | +0.02 | vanilla | absorbed |
| law | law_restricted_child_labor | modifier | state_peasants_mortality_mult | +0.02 | vanilla | absorbed |
| law | law_state_eugenics_program | modifier | state_birth_rate_mult | +0.10 | mod | ontop |
| law | law_state_sponsored_family_planning | modifier | state_birth_rate_mult | −0.05 | mod | absorbed |
| law | law_unrestricted_augmentation | modifier | state_mortality_mult | −0.05 | mod | absorbed |
| law | law_women_in_the_fields | modifier | state_birth_rate_mult | −0.10 | vanilla | absorbed |
| law | law_women_in_the_workplace | modifier | state_birth_rate_mult | −0.05 | vanilla | absorbed |
| law | law_womens_suffrage | modifier | state_birth_rate_mult | −0.05 | vanilla | absorbed |
| technology | antibiotic_mass_production | modifier | state_birth_rate_mult | +0.05 | mod | absorbed |
| technology | antibiotic_mass_production | modifier | state_mortality_mult | −0.05 | mod | absorbed |
| technology | biological_immortality | modifier | state_mortality_mult | −0.20 | mod | ontop |
| technology | contraceptive_pill | modifier | state_birth_rate_mult | −0.10 | mod | absorbed |
| technology | mental_health_awareness | modifier | state_mortality_mult | −0.05 | mod | ontop |
| technology | mind_backups | modifier | state_mortality_mult | −0.05 | mod | ontop |
| technology | modern_vaccines | modifier | state_birth_rate_mult | +0.05 | mod | absorbed |
| technology | modern_vaccines | modifier | state_mortality_mult | −0.05 | mod | absorbed |
| technology | second_wave_feminism | modifier | state_birth_rate_mult | −0.025 | mod | ontop |
| technology | sexual_revolution | modifier | state_birth_rate_mult | −0.025 | mod | ontop |

- [ ] **Step 1: Write the failing tests**

```python
class TestEngineLinesMoved(unittest.TestCase):
    """Owner, 2026-10-11: no law, technology or institution applies an engine birth or mortality line; each line the
    census used to read sits on its family's type at its old value."""

    # (kind, key, block, engine field) -> (family, value): the table in the plan (2026-10-11)
    MOVED = {
        ("institution", "institution_ministry_of_consumer_protection", "modifier", "state_mortality_mult"): ("absorbed", -0.01),
        ("law", "law_charitable_health_system", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.03),
        ("law", "law_child_labor_allowed", "modifier", "state_farmers_mortality_mult"): ("absorbed", 0.05),
        ("law", "law_child_labor_allowed", "modifier", "state_laborers_mortality_mult"): ("absorbed", 0.05),
        ("law", "law_child_labor_allowed", "modifier", "state_machinists_mortality_mult"): ("absorbed", 0.05),
        ("law", "law_child_labor_allowed", "modifier", "state_peasants_mortality_mult"): ("absorbed", 0.05),
        ("law", "law_communal_child_rearing", "modifier", "state_birth_rate_mult"): ("ontop", -0.2),
        ("law", "law_full_equality_and_protection", "modifier", "state_birth_rate_mult"): ("ontop", -0.01),
        ("law", "law_mandatory_augmentation", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.02),
        ("law", "law_medical_augmentation_only", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.02),
        ("law", "law_no_womens_rights", "modifier", "state_birth_rate_mult"): ("absorbed", 0.05),
        ("law", "law_population_control_measures", "modifier", "state_birth_rate_mult"): ("ontop", -0.1),
        ("law", "law_private_health_insurance", "institution_modifier", "state_mortality_wealth_mult"): ("ontop", -0.002),
        ("law", "law_pro_natalist_subsidies", "modifier", "state_birth_rate_mult"): ("ontop", 0.1),
        ("law", "law_protected_class", "modifier", "state_birth_rate_mult"): ("absorbed", -0.1),
        ("law", "law_public_health_insurance", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.05),
        ("law", "law_regulated_augmentation_market", "institution_modifier", "state_mortality_mult"): ("absorbed", -0.02),
        ("law", "law_restricted_child_labor", "modifier", "state_farmers_mortality_mult"): ("absorbed", 0.02),
        ("law", "law_restricted_child_labor", "modifier", "state_laborers_mortality_mult"): ("absorbed", 0.02),
        ("law", "law_restricted_child_labor", "modifier", "state_peasants_mortality_mult"): ("absorbed", 0.02),
        ("law", "law_state_eugenics_program", "modifier", "state_birth_rate_mult"): ("ontop", 0.1),
        ("law", "law_state_sponsored_family_planning", "modifier", "state_birth_rate_mult"): ("absorbed", -0.05),
        ("law", "law_unrestricted_augmentation", "modifier", "state_mortality_mult"): ("absorbed", -0.05),
        ("law", "law_women_in_the_fields", "modifier", "state_birth_rate_mult"): ("absorbed", -0.1),
        ("law", "law_women_in_the_workplace", "modifier", "state_birth_rate_mult"): ("absorbed", -0.05),
        ("law", "law_womens_suffrage", "modifier", "state_birth_rate_mult"): ("absorbed", -0.05),
        ("technology", "antibiotic_mass_production", "modifier", "state_birth_rate_mult"): ("absorbed", 0.05),
        ("technology", "antibiotic_mass_production", "modifier", "state_mortality_mult"): ("absorbed", -0.05),
        ("technology", "biological_immortality", "modifier", "state_mortality_mult"): ("ontop", -0.2),
        ("technology", "contraceptive_pill", "modifier", "state_birth_rate_mult"): ("absorbed", -0.1),
        ("technology", "mental_health_awareness", "modifier", "state_mortality_mult"): ("ontop", -0.05),
        ("technology", "mind_backups", "modifier", "state_mortality_mult"): ("ontop", -0.05),
        ("technology", "modern_vaccines", "modifier", "state_birth_rate_mult"): ("absorbed", 0.05),
        ("technology", "modern_vaccines", "modifier", "state_mortality_mult"): ("absorbed", -0.05),
        ("technology", "second_wave_feminism", "modifier", "state_birth_rate_mult"): ("ontop", -0.025),
        ("technology", "sexual_revolution", "modifier", "state_birth_rate_mult"): ("ontop", -0.025),
    }

    def test_no_carrier_applies_an_engine_birth_or_mortality_line(self):
        live = {k: v for k, v in DM.engine_rate_lines().items() if abs(v) > 1e-9 and DM.is_engine_rate_field(k[3])}
        self.assertEqual(live, {}, "move each to its type (docs/superpowers/plans/2026-10-11-...)")

    def test_each_line_sits_on_its_familys_type_at_its_old_value(self):
        got = DM.engine_lines()
        self.assertEqual(set(got), set(self.MOVED))
        for k, (family, value) in self.MOVED.items():
            self.assertEqual(got[k][0], family, k)
            self.assertAlmostEqual(got[k][1], value, places=6, msg=k)
```

- [ ] **Step 2: Run them to see them fail.** Expected: the first FAILs listing 36 lines; the second ERRORs,
  `module 'demographics_modifiers' has no attribute 'engine_lines'`.

- [ ] **Step 3: `DM.engine_lines`** (after `engine_rate_lines`):

```python
def engine_lines(root=ROOT):
    """{(kind, key, block, engine field): (family, value)}: the engine's birth and mortality lines moved to script-only
    types (owner, 2026-10-11), read back from the carriers. engine_rate_lines already sums every *_mult line,
    vanilla's and the mod's, so a type's line is found under its own name and mapped back to the field it replaces."""
    back = {name: fam_field for fam_field, name in P.ENGINE_LINE_TYPES.items()}
    out = {}
    for (kind, key, block, field), value in engine_rate_lines(root).items():
        if field in back and abs(value) > 1e-9:
            family, engine_field = back[field]
            out[(kind, key, block, engine_field)] = (family, value)
    return out
```

  `engine_rate_lines` matches fields with `_ENGINE_RATE_FIELD`. If that regex doesn't match `state_demog_*_mult`
  names, widen it to every `*_mult` line (check `test_demographics_modifiers.py` still passes). `is_engine_rate_field`
  must stay false for the new types: add `and field not in P.ENGINE_LINE_TYPES.values()`.

- [ ] **Step 4: The vanilla lines.** Create `common/laws/te_demog_engine_line_injections.txt` (BOM first), one INJECT
  per vanilla law, the field's negative and the type at the field's value, in the block the line came from:

```
# The engine's birth and mortality lines on vanilla's laws, moved to script-only types (owner, 2026-10-11;
# docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md). Each field is cancelled by its negative,
# which the engine sums to 0 and the tooltip drops, and the type carries the value; te_demog_lines_refresh re-applies
# it while the census doesn't set births and deaths. A release keeps this file.
INJECT:law_charitable_health_system = {
	institution_modifier = {
		state_mortality_mult = 0.03
		state_demog_absorbed_mortality_mult = -0.03
	}
}
INJECT:law_private_health_insurance = {
	institution_modifier = {
		state_mortality_wealth_mult = 0.002
		state_demog_ontop_mortality_wealth_mult = -0.002
	}
}
INJECT:law_public_health_insurance = {
	institution_modifier = {
		state_mortality_mult = 0.05
		state_demog_absorbed_mortality_mult = -0.05
	}
}
INJECT:law_child_labor_allowed = {
	modifier = {
		state_farmers_mortality_mult = -0.05
		state_laborers_mortality_mult = -0.05
		state_machinists_mortality_mult = -0.05
		state_peasants_mortality_mult = -0.05
		state_demog_absorbed_farmers_mortality_mult = 0.05
		state_demog_absorbed_laborers_mortality_mult = 0.05
		state_demog_absorbed_machinists_mortality_mult = 0.05
		state_demog_absorbed_peasants_mortality_mult = 0.05
	}
}
INJECT:law_restricted_child_labor = {
	modifier = {
		state_farmers_mortality_mult = -0.02
		state_laborers_mortality_mult = -0.02
		state_peasants_mortality_mult = -0.02
		state_demog_absorbed_farmers_mortality_mult = 0.02
		state_demog_absorbed_laborers_mortality_mult = 0.02
		state_demog_absorbed_peasants_mortality_mult = 0.02
	}
}
INJECT:law_no_womens_rights = {
	modifier = {
		state_birth_rate_mult = -0.05
		state_demog_absorbed_birth_rate_mult = 0.05
	}
}
INJECT:law_women_in_the_fields = {
	modifier = {
		state_birth_rate_mult = 0.1
		state_demog_absorbed_birth_rate_mult = -0.1
	}
}
INJECT:law_women_in_the_workplace = {
	modifier = {
		state_birth_rate_mult = 0.05
		state_demog_absorbed_birth_rate_mult = -0.05
	}
}
INJECT:law_womens_suffrage = {
	modifier = {
		state_birth_rate_mult = 0.05
		state_demog_absorbed_birth_rate_mult = -0.05
	}
}
```

  Before writing, confirm each value against the table with
  `DM.engine_rate_lines(mod=False)[(kind, key, block, field)]`. If a law already has a mod INJECT for the same block
  in another file (`modified_health_system.txt`, `te_demog_law_injections.txt`), the engine merges both INJECTs, as it
  did for #869's first build. Run `test_demographics_registry.TestEngineRateLines` to confirm.

- [ ] **Step 5: The mod lines.** In each mod carrier, replace the field with its family's type at the same value (e.g.
  `extra_laws.txt`, `law_pro_natalist_subsidies`: `state_birth_rate_mult = 0.1` → `state_demog_ontop_birth_rate_mult
  = 0.1`). Find each with `git grep -n "<field>" -- common/laws/extra_laws.txt` inside the carrier's block. Then run
  `.venv/bin/python scripts/format_paradox_tabs.py` on every changed file.

- [ ] **Step 6: Run the tests.** `TestEngineLinesMoved` passes. Then fix the tests that pinned the old layout: run
  `.venv/bin/python -m unittest test_demographics_registry test_demographics_modifiers` and read each failure.
  `TestEngineRateLines` pins lines that now live on types: re-pin it to `DM.engine_lines` with the same values.
  `TestAbsorbedScript` changes in Task 3; leave it failing until then and say so in the commit.

- [ ] **Step 7: Commit** (carriers, the new injection file, `demographics_modifiers.py`, the tests): "Demographics: move
  the engine's birth and death lines to their script-only types".

### Task 3: The census stops netting the moved lines

**Files:**
- Modify: `scripts/analysis/demographics_modifiers.py` (`absorbed_carriers`)
- Modify: `scripts/generators/gen_demographics.py` (`absorbed_terms`, `absorbed_walk`, `_carrier_adds`)
- Regenerate: `common/script_values/te_demog_generated_values.txt`, `common/scripted_effects/te_demog_generated_effects.txt`
- Test: `test_demographics_registry.py` (`TestAbsorbedScript`), `test_gen_demographics.py`

**Interfaces:**
- Consumes: `DM.engine_lines` (Task 2).
- Produces: the walk's replaced sums `te_dg_w_ebr` / `te_dg_w_edr` = each pop's bare curve × (literacy's −0.1 and mild
  starvation's terms) only. The locals `te_dg_w_sab` / `te_dg_w_sad` and the values `te_demog_absorbed_births`,
  `_deaths` and `_<class>_deaths` are gone. `DM.absorbed_carriers` returns `[]`, since no engine-applied
  law/tech/institution line remains. Its callers (`predict`, the generator) drop their law, tech and institution branch.

- [ ] **Step 1: Write the failing test** (replace the class-line and institution-line cases in `TestAbsorbedScript`):

```python
    def test_the_walk_nets_only_the_per_pop_engine_terms(self):
        """Owner, 2026-10-11: the laws', techs' and institutions' lines are script-only, so under Full the engine no
        longer applies them and the walk has nothing of theirs to net. It nets what the engine still applies per pop:
        literacy's -0.1 and mild starvation's terms."""
        b, d = self._run(laws={"law_child_labor_allowed", "law_charitable_health_system", "law_no_womens_rights"},
                         levels={"institution_health_system": 3}, pop_type="laborers", food=0.3, literacy=0.4)
        sb, sd = M.starvation_terms(0.3)
        self.assertAlmostEqual(b, P.LITERACY_BIRTH_PENALTY * 0.4 + sb, places=5)
        self.assertAlmostEqual(d, sd, places=5)
        eng = _OwnerEngine({"literacy_rate": 0.0, "food_security": 1.0}, triggers={"te_demog_effects_run": True})
        eng.call("te_demog_absorbed_walk_init")
        self.assertNotIn("te_dg_w_sab", eng.locals)
        self.assertNotIn("te_dg_w_sad", eng.locals)
```

- [ ] **Step 2: Run it to see it fail** (the class line and the health law still add).

- [ ] **Step 3: Implement.** `absorbed_carriers` now returns `[]` (keep the function and its docstring, explaining
  why, since `predict` and tests call it). In `gen_demographics.py`, `absorbed_walk` stops emitting `te_dg_w_sab` /
  `_sad` and the class reads, and `absorbed_terms` stops emitting the state and class values. Then regenerate:
  `.venv/bin/python scripts/generators/gen_demographics.py`.

- [ ] **Step 4: Run** `test_demographics_registry` and `test_gen_demographics`. Expected: OK, except
  `TestRatesScript`, which still subtracts `te_dg_w_sad` (Task 5). Note that in the commit.

- [ ] **Step 5: Commit**: "Demographics: the walk nets only the per-pop engine terms".

### Task 4: The monthly pulse re-applies the lines

**Files:**
- Modify: `scripts/generators/gen_demographics.py` (new `engine_line_files(root)` writing three generated files)
- Create (generated): `common/static_modifiers/te_demog_line_modifiers_generated.txt`,
  `common/script_values/te_demog_line_values_generated.txt`, `common/scripted_effects/te_demog_line_effects_generated.txt`
- Modify: `common/scripted_triggers/te_demog_triggers.txt` (`te_demog_lines_apply`)
- Modify: `common/on_actions/te_demog_on_actions.txt`
- Modify: `events/te_demog_events.txt` (`te_demog_events.4`)
- Modify: `localization/english/te_modifiers_l_english.yml` (the pairs' names)
- Modify: `docs/auto_generated_files.md` (three rows)
- Test: `test_demographics_registry.py` (new `class TestLinesScript`)

**Interfaces:**
- Consumes: `P.ENGINE_LINE_FIELDS`, `P.ENGINE_LINE_SHORT`, `P.ENGINE_LINE_TYPES` (Task 1).
- Produces:
  - **Modifiers:** `te_demog_line_<short>_up` / `_down`, the field ±1, icon `modifier_system.dds`.
  - **Values:** `te_demog_line_<short>`, the families' sum; `te_demog_line_<short>_applied`, the multiplier in force,
    signed, from `var:te_dg_ln_<short>`, 0 when neither modifier is held.
  - **Effects:** `te_demog_lines_refresh` (THIS = ROOT = a state) and `te_demog_lines_clear`.
  - **Trigger:** `te_demog_lines_apply`.

- [ ] **Step 1: Write the failing tests**

```python
class TestLinesScript(unittest.TestCase):
    """te_demog_lines_refresh (owner, 2026-10-11): the moved lines reach the state while the census doesn't set its
    births and deaths, at the families' sum, by a fixed-sign pair per field."""

    def _eng(self, sums, full=False, census_term=False, held=None):
        fixtures = {f"modifier:{name}": sums.get(name, 0.0) for name in P.ENGINE_LINE_TYPES.values()}
        eng = _Engine(fixtures, triggers={"te_demog_effects_run": full, "te_demog_cohorts_run": full})
        if census_term:
            eng.vars["te_dg_mb"] = -0.3
        for short, m in (held or {}).items():
            eng.vars[f"te_dg_ln_{short}"] = m
            eng.modifiers[f"te_demog_line_{short}_{'up' if m > 0 else 'down'}"] = abs(m)
        return eng

    def test_off_applies_the_families_sum(self):
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03, "state_demog_ontop_mortality_mult": -0.05,
                         "state_demog_absorbed_birth_rate_mult": 0.05, "state_demog_ontop_mortality_wealth_mult": -0.01})
        eng.call("te_demog_lines_refresh")
        self.assertAlmostEqual(eng.modifiers["te_demog_line_deaths_down"], 0.08, places=5)
        self.assertAlmostEqual(eng.modifiers["te_demog_line_births_up"], 0.05, places=5)
        self.assertAlmostEqual(eng.modifiers["te_demog_line_wealth_deaths_down"], 0.01, places=5)
        self.assertNotIn("te_demog_line_deaths_up", eng.modifiers)

    def test_pairs_follow_the_census_term(self):
        # Full but no census step yet: vanilla's lines stay on
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03}, full=True)
        eng.call("te_demog_lines_refresh")
        self.assertIn("te_demog_line_deaths_down", eng.modifiers)
        # Full with the census's term in force: the pairs come off
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03}, full=True, census_term=True,
                        held={"deaths": -0.03})
        eng.call("te_demog_lines_refresh")
        self.assertEqual({k for k in eng.modifiers if k.startswith("te_demog_line_")}, set())
        self.assertNotIn("te_dg_ln_deaths", eng.vars)

    def test_unchanged_sums_are_left_alone(self):
        eng = self._eng({"state_demog_absorbed_mortality_mult": -0.03}, held={"deaths": -0.03})
        eng.call("te_demog_lines_refresh")
        self.assertEqual(eng.removed, [], "a refresh with nothing changed removes no modifier")

    def test_unincorporated_state_gets_no_institution_lines(self):
        # the engine reads an institution line as 0 in an unincorporated state, so the sum is the laws' and techs'
        eng = self._eng({"state_demog_absorbed_birth_rate_mult": 0.05})
        eng.call("te_demog_lines_refresh")
        self.assertEqual({k for k in eng.modifiers if k.startswith("te_demog_line_")}, {"te_demog_line_births_up"})

    def test_refresh_runs_where_the_inputs_change(self):
        """Owner, 2026-10-11: the pairs follow a new game, a law, a change of owner and incorporation at once, with the
        monthly pulse as the fallback. Every caller has ROOT = the state: the state on-actions call it directly, the
        country and global ones through the hidden state event te_demog_events.4."""
        on_actions = _text(ROOT / "common" / "on_actions" / "te_demog_on_actions.txt")
        for hook in ("on_monthly_pulse_state", "on_state_owner_change", "on_state_incorporation",
                     "on_law_activated", "on_game_started_after_lobby"):
            self.assertRegex(on_actions, rf"{hook} = \{{\s*on_actions = \{{\s*te_demog_lines_", hook)
        for name in ("te_demog_lines_country_on_action", "te_demog_lines_world_on_action"):
            self.assertIn("trigger_event = { id = te_demog_events.4 }", _block(on_actions, name), name)
        event = _block(_text(ROOT / "events" / "te_demog_events.txt"), "te_demog_events.4")
        self.assertIn("type = state_event", event)
        self.assertIn("te_demog_lines_refresh = yes", event)
        callers = sorted(p.name for p in [*ROOT.glob("common/**/*.txt"), *ROOT.glob("events/*.txt")]
                         if "te_demog_lines_refresh = yes" in _text(p) and "generated" not in p.name)
        self.assertEqual(callers, ["te_demog_events.txt", "te_demog_on_actions.txt"])
```

  `eng.removed` is the interpreter's record of `remove_modifier` calls. If `_Engine` has none, add it: a list
  appended in its `remove_modifier` handler.

- [ ] **Step 2: Run them to see them fail** (`te_demog_lines_refresh` unknown).

- [ ] **Step 3: The trigger** in `te_demog_triggers.txt`:

```
# THIS = a state: the moved engine lines (te_demog_lines_refresh) apply unless the census sets this state's births and
# deaths: Full, and its term in force (te_dg_mb, which a census step sets and Display only or Disabled clears).
te_demog_lines_apply = {
	OR = {
		NOT = { te_demog_effects_run = yes }
		NOT = { has_variable = te_dg_mb }
	}
}
```

- [ ] **Step 4: The generator.** In `gen_demographics.py`, add `engine_line_files(root)`, called from `main` beside the
  other writers. For each field in `P.ENGINE_LINE_FIELDS` it writes (short = `P.ENGINE_LINE_SHORT[field]`; the
  families' types from `P.ENGINE_LINE_TYPES`):

  The modifiers file:

```
te_demog_line_deaths_up = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds
	state_mortality_mult = 1
}
te_demog_line_deaths_down = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds
	state_mortality_mult = -1
}
```

  The values file (a family's type is added only if `P.ENGINE_LINE_TYPES` has it for the field):

```
te_demog_line_deaths = {
	value = modifier:state_demog_absorbed_mortality_mult
	add = modifier:state_demog_ontop_mortality_mult
}
te_demog_line_deaths_applied = {
	value = 0
	if = {
		limit = {
			OR = {
				has_modifier = te_demog_line_deaths_up
				has_modifier = te_demog_line_deaths_down
			}
		}
		value = var:te_dg_ln_deaths
	}
}
te_demog_line_deaths_up_mult = {
	value = var:te_dg_ln_deaths
}
te_demog_line_deaths_down_mult = {
	value = var:te_dg_ln_deaths
	multiply = -1
}
```

  The effects file:

```
# THIS = ROOT = a state (its monthly pulse; the census's refresh calls _clear): the engine's moved birth and mortality
# lines, re-applied while te_demog_lines_apply holds, each field's pair touched only when its sum changed.
te_demog_lines_refresh = {
	if = {
		limit = { te_demog_lines_apply = yes }
		set_local_variable = { name = te_dg_ln_new value = te_demog_line_deaths }
		if = {
			limit = {
				OR = {
					NOT = { has_variable = te_dg_ln_deaths }
					NOT = { var:te_dg_ln_deaths = local_var:te_dg_ln_new }
				}
			}
			te_demog_line_deaths_remove = yes
			set_variable = { name = te_dg_ln_deaths value = local_var:te_dg_ln_new }
			if = {
				limit = { var:te_dg_ln_deaths > 0 }
				add_modifier = { name = te_demog_line_deaths_up multiplier = te_demog_line_deaths_up_mult }
			}
			else_if = {
				limit = { var:te_dg_ln_deaths < 0 }
				add_modifier = { name = te_demog_line_deaths_down multiplier = te_demog_line_deaths_down_mult }
			}
		}
	}
	else = {
		te_demog_lines_clear = yes
	}
}
te_demog_line_deaths_remove = {
	if = {
		limit = { has_modifier = te_demog_line_deaths_up }
		remove_modifier = te_demog_line_deaths_up
	}
	if = {
		limit = { has_modifier = te_demog_line_deaths_down }
		remove_modifier = te_demog_line_deaths_down
	}
}
te_demog_lines_clear = {
	te_demog_line_deaths_remove = yes
	if = {
		limit = { has_variable = te_dg_ln_deaths }
		remove_variable = te_dg_ln_deaths
	}
}
```

  The generated `te_demog_lines_refresh` and `te_demog_lines_clear` repeat their field block for each of the 7 fields.
  The generator also writes the loc keys `te_demog_line_<short>_up` / `_down` = "Laws and Institutions" and `_desc` =
  "The birth and death effects of this state's laws, technologies and institutions." into the loc file, if absent.

- [ ] **Step 5: The hooks.** In `te_demog_on_actions.txt`:

```
# The engine's moved birth and mortality lines (owner, 2026-10-11): refreshed where their inputs change, and every
# month for technologies and institution levels, which have no on-action. ROOT must be the state (the multiplier
# resolves against it): the state hooks call the refresh, the others fire te_demog_events.4 in each state.
on_monthly_pulse_state = {
	on_actions = {
		te_demog_lines_on_action
	}
}
on_state_owner_change = {
	on_actions = {
		te_demog_lines_on_action
	}
}
on_state_incorporation = {
	on_actions = {
		te_demog_lines_on_action
	}
}
on_law_activated = {
	on_actions = {
		te_demog_lines_country_on_action
	}
}
on_game_started_after_lobby = {
	on_actions = {
		te_demog_lines_world_on_action
	}
}

# THIS = ROOT = a state.
te_demog_lines_on_action = {
	effect = {
		te_demog_lines_refresh = yes
	}
}

# ROOT = a country whose law changed: each of its states, as its own ROOT.
te_demog_lines_country_on_action = {
	effect = {
		every_scope_state = {
			trigger_event = { id = te_demog_events.4 }
		}
	}
}

# No ROOT (after the lobby, so the rule is settled): every state, as its own ROOT.
te_demog_lines_world_on_action = {
	effect = {
		every_state = {
			trigger_event = { id = te_demog_events.4 }
		}
	}
}
```

  And in `events/te_demog_events.txt`:

```
# ======================================================================
#  4 – The engine's moved birth and mortality lines (hidden)
#  Fired in each state by the country and global hooks (te_demog_on_actions.txt), so ROOT is the
#  state, as te_demog_lines_refresh's multipliers need.
# ======================================================================
te_demog_events.4 = {
	type = state_event
	hidden = yes

	immediate = {
		te_demog_lines_refresh = yes
	}
}
```

  Check `on_state_owner_change` and `on_state_incorporation` run with ROOT = the state. Vanilla's comment above
  `on_state_incorporation` says so, and `on_state_owner_change`'s vanilla effect reads `owner` and `state_region`.
  Confirm in game with the Task 8 checklist.

- [ ] **Step 6: Generate and run.** `.venv/bin/python scripts/generators/gen_demographics.py`; then
  `test_demographics_registry.TestLinesScript`, `test_gen_demographics`, the tab check and `organize_loc --check`.
  Expected: OK. Add the three generated files' rows to `docs/auto_generated_files.md`.

- [ ] **Step 7: Commit**: "Demographics: the monthly pulse re-applies the moved lines".

### Task 5: Under Full the census applies the on-top family

**Files:**
- Modify: `scripts/analysis/demographics_model.py` (`rate_term`)
- Modify: `common/scripted_effects/te_demog_rate_effects.txt` (`te_demog_rates_refresh`, `te_demog_rates_apply`,
  `te_demog_rates_remove`, `te_demog_rates_clear`)
- Modify: `common/static_modifiers/te_demog_modifiers.txt` (`te_demog_census_wealth_up` / `_down`)
- Modify: `common/script_values/te_demog_values.txt` (`te_demog_rate_wealth`, `_up`, `_down`)
- Modify: `common/scripted_effects/te_demog_fast_effects.txt` (the first Full step)
- Modify: `common/scripted_effects/te_debug_demog_effects.txt` (option n logs `q_b`, `q_d`, `w`)
- Test: `test_demographics_model.py` (`TestRateTerm`), `test_demographics_registry.py` (`TestRatesScript`, `TestFastMode`, `TestConsole`)

**Interfaces:**
- Consumes: `te_demog_line_<short>_applied` and `te_demog_lines_clear` (Task 4), the on-top types (Task 1).
- Produces: `rate_term(target, bare, absorbed=0.0, other=0.0, on_top=0.0, added=0.0)`, where `added` is the on-top
  family's sum that the census applies at its rate: m = t/b − 1 − a/b − on_top·(1 − t/b) + added·t/b. The state
  variables `te_dg_q_b`, `te_dg_q_d` (the on-top family's sums, for option n) and `te_dg_w` (the wealth line applied,
  signed). The modifiers `te_demog_census_wealth_up` / `_down`.

- [ ] **Step 1: Write the failing tests.**

```python
    # test_demographics_model.TestRateTerm
    def test_the_census_applies_the_on_top_family_at_its_rate(self):
        """Owner, 2026-10-11: a moved on-top line (a family-policy law, a late tech) is script-only, so under Full the
        census applies it: every pop gets bare x (target / bare) x (1 + Q)."""
        m, _ = M.rate_term(target=60.0, bare=100.0, added=0.10)
        self.assertAlmostEqual(100.0 * (1 + m), 60.0 * 1.10)
        m, _ = M.rate_term(target=60.0, bare=100.0, on_top=0.3, added=0.10)
        self.assertAlmostEqual(100.0 * (1 + m + 0.3), 60.0 * (1 + 0.3 + 0.10))
```

```python
    # test_demographics_registry.TestRatesScript
    def test_full_applies_the_on_top_family_and_clears_the_pairs(self):
        """The first Full step: the pairs are in the read and are cleared in the same effect; M carries the on-top
        family at the census's rate, and the wealth line goes on the census's own pair at its share, floored."""
        ed0 = 430e6
        eng = self._eng(read_d=-0.08 + 0.32, edr=0.0)   # the pairs' -0.08 and pollution's +0.32 in the read
        eng.fixtures.update({"modifier:state_demog_ontop_mortality_mult": -0.05,
                             "modifier:state_demog_absorbed_mortality_mult": -0.03,
                             "modifier:state_demog_ontop_mortality_wealth_mult": -0.01})
        eng.modifiers["te_demog_line_deaths_down"] = 0.08
        eng.vars["te_dg_ln_deaths"] = -0.08
        eng.call("te_demog_rates_refresh")
        target = 31.0 * self.POP * 100 / 12
        _, md = self._want(38.0, 31.0, 475e6, ed0, self.EBR, 0.05, 0.32, added_d=-0.05)
        self.assertAlmostEqual(eng.vars["te_dg_md"], md, places=5)
        self.assertAlmostEqual(ed0 * (1 + md + 0.32), target * (1 + 0.32 - 0.05), delta=target * 1e-5)
        self.assertNotIn("te_demog_line_deaths_down", eng.modifiers)
        tb = target / ed0
        self.assertAlmostEqual(eng.modifiers["te_demog_census_wealth_down"], max(-0.01, P.WEALTH_LINE_FLOOR) * -tb, places=5)
```

  `_want` gains `added_b=0.0, added_d=0.0`, passed as `added=` to `rate_term`. The `other` it passes is the read less
  the pairs (`te_demog_line_*_applied`), and that is also its `on_top`.

```python
    # test_demographics_registry.TestFastMode
    def test_first_full_step_takes_the_pairs_off_fast_modes_average(self):
        """Review Focus 5: on the first Full step the walk's average still holds the pairs the refresh clears; fast
        mode's term subtracts them, so the engine runs K x (the census's target plus what's on top)."""
        eng = self._eng_full()
        eng.modifiers["te_demog_line_deaths_down"] = 0.08
        eng.vars["te_dg_ln_deaths"] = -0.08
        eng.fixtures["modifier:state_mortality_mult"] = -0.08
        self._both(eng, eb=475e3, eb0=475e3, ed=0.92 * 430e3, ed0=430e3)
        td = 24.0 * 1000.0 * 100 / 12 / 430e3
        self.assertAlmostEqual(eng.vars["te_dg_fast_fd"], 3 * td, places=5)
```

- [ ] **Step 2: Run them to see them fail.**

- [ ] **Step 3: `rate_term`.** Add the `added=0.0` parameter and `+ added * target / bare` to `m`; document it in the
  docstring.

- [ ] **Step 4: The refresh.** In `te_demog_rates_refresh`, births and deaths blocks:
  - `te_dg_rate_os` subtracts `te_demog_line_births_applied` / `te_demog_line_deaths_applied` instead of
    `local_var:te_dg_w_sab` / `_sad` (Task 3 removed those);
  - add `set_local_variable = { name = te_dg_rate_q value = modifier:state_demog_ontop_mortality_mult }` (births:
    `..._birth_rate_mult`);
  - `te_dg_rate_m` gains `add = { value = local_var:te_dg_rate_q multiply = local_var:te_dg_rate_tb }`;
  - store `te_dg_q_d` / `te_dg_q_b` beside `te_dg_os_*`.

  The clamp's `te_dg_rate_lo` also subtracts the pairs' applied values (they leave the read when cleared). After both
  blocks, before `te_demog_rates_apply`:

```
			# the wealth line (Private Health Insurance; owner decision 1, option b): at the census's share of the bare
			# curve, at least te_demog_k_wealth_line_floor a wealth level
			set_variable = {
				name = te_dg_w
				value = {
					value = modifier:state_demog_ontop_mortality_wealth_mult
					min = te_demog_k_wealth_line_floor
					multiply = var:te_dg_tb_d
				}
			}
			te_demog_lines_clear = yes
```

  `te_demog_k_wealth_line_floor` = `P.WEALTH_LINE_FLOOR`, generated with the other `te_demog_k_*` constants. Note
  `min` before `multiply`: the floor is on the line a wealth level, before the census's share.

  In `te_demog_rates_apply`, a third pair: `te_demog_census_wealth_down` when `var:te_dg_w < 0` with
  `multiplier = te_demog_rate_wealth_down` (= `var:te_dg_w` × −1), `_up` when above 0.
  `te_demog_rates_remove` removes it, and `te_demog_rates_clear` removes `te_dg_w`, `te_dg_q_b` and `te_dg_q_d`.
  The static modifiers go in `te_demog_modifiers.txt`:

```
te_demog_census_wealth_up = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds
	state_mortality_wealth_mult = 1
}
te_demog_census_wealth_down = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_system.dds
	state_mortality_wealth_mult = -1
}
```

  with the loc "Census: Deaths by Wealth" and a `_desc` saying it is Private Health Insurance's line at the census's
  rate.

- [ ] **Step 5: Fast mode.** In `te_demog_fast_refresh_rates`, the deaths and births averages also subtract the pairs
  in force before the refresh (`te_demog_line_*_applied`, read before `te_demog_lines_clear`). The refresh leaves them
  in locals `te_dg_rate_lines_b` / `_d` for fast mode, as it leaves `te_dg_rate_prev_*`.

- [ ] **Step 6: Option n** logs `q_b`, `q_d` and `w` (copies `te_dg_q_b`, `te_dg_q_d`, `te_dg_w`), and
  `TestConsole.test_option_n_logs_the_rates_click_only` lists them.

- [ ] **Step 7: Run** `test_demographics_model`, `test_demographics_registry`. Expected: OK.

- [ ] **Step 8: Commit**: "Demographics: under Full the census applies the on-top lines and the wealth line".

### Task 6: The harness

**Files:**
- Modify: `scripts/analysis/demographics_harness.py` (`predict_state`, `predict_save`, the report groups)
- Test: `test_demographics_harness.py` (`TestPredict`)

**Interfaces:**
- Consumes: `DM.engine_lines`, `DM.totals` with the families' types, `rate_term(..., added=)`.
- Produces: `predict_state(pops, cbr, cdr, d, on_top_b=0, on_top_d=0, added_b=0, added_d=0, wealth=0, groups=None)`.
  It drops `absorbed_b` / `absorbed_d`, since nothing engine-applied is absorbed at state level. `wealth` is the on-top
  wealth line a wealth level, applied per pop as `wealth_level × max(wealth, P.WEALTH_LINE_FLOOR) × target / bare`.
  Report groups: `child_labour`, `womens_rights`, `health`, `other_lines` now report the absorbed family's lines at
  the bare curves (what the census models in their place). `mild` is unchanged.

- [ ] **Step 1: Write the failing tests.**

```python
    def test_the_on_top_family_applies_at_the_census_rate(self):
        out = H.predict_state([H.Pop(1e6, 9.0, 0.0, 0.8)], 40.0, 30.0, self.D, added_b=0.10)
        self.assertAlmostEqual(out["births"] / 1e3, 40.0 * 1.10, places=6)

    def test_the_wealth_line_is_floored_and_scaled(self):
        rich = H.Pop(1e6, 30.0, 0.0, 0.8, wealth=99)
        out = H.predict_state([rich], 40.0, 30.0, self.D, wealth=-0.01)
        self.assertAlmostEqual(out["deaths"] / 1e3, 30.0 * (1 + 99 * H.P.WEALTH_LINE_FLOOR), places=4)
```

  `Pop` gains a `wealth` field, default 0, read from the save's pop `wealth`.

- [ ] **Step 2: Run them to see them fail.**

- [ ] **Step 3: Implement.** In `predict_save`:
  - read each state's families from the owner's laws, techs and institutions:
    `DM.totals(<engine_lines as carriers>, ..., types=<the families' types>, institution_impact=1.0)`;
  - pass the on-top birth and death sums as `added_b` / `added_d` and the on-top wealth sum as `wealth`;
  - pass the absorbed family's sums to the report groups only.

  Add this adapter to `demographics_modifiers.py`, so `DM.totals` works unchanged:

```python
def line_carriers(root=ROOT):
    """engine_lines() as Carriers typed by their family's script-only type (owner, 2026-10-11), with the
    scaling kinds absorbed_carriers used: a law's institution_modifier line is law_institution (per level of the
    law's institution, incorporated states), an institution's own line institution, the rest flat."""
    institution = {key: _u(_u(entry).get("institution")) for key, entry in _state(root).get_data("Laws").items()}
    out = []
    for (kind, key, block, field), (family, value) in sorted(engine_lines(root).items()):
        name = P.ENGINE_LINE_TYPES[(family, field)]
        if kind == "law" and block == "institution_modifier":
            out.append(Carrier("law_institution", key, name, value, institution.get(key)))
        elif kind == "institution":
            out.append(Carrier("institution", key, name, value, key))
        else:
            out.append(Carrier(kind, key, name, value))
    return out
```

  Test it beside `TestEngineLinesMoved`: `{c.type for c in DM.line_carriers()} <= set(P.ENGINE_LINE_TYPES.values())`,
  and the Charitable Health System carrier is `law_institution` with institution `institution_health_system`.

- [ ] **Step 4: Run** `test_demographics_harness`. Then re-run the offline gate:
  `predict` on the six normal-speed gate saves (`/mnt/d/vic3te-data/vic3te-demog-gate-data/saves/`). Record the
  multiple next to #885's ×1.642 in the results doc.

- [ ] **Step 5: Commit**: "Demographics harness: predict with the moved lines".

### Task 7: Releases keep the moved lines

**Files:**
- Modify: `test_release_census_inputs.py`
- Modify (only if a test shows it touching the new files): `scripts/release/comment_out_census_inputs.py`

- [ ] **Step 1: Write the failing test.**

```python
    def test_the_moved_engine_lines_ship(self):
        """Owner, 2026-10-11: a release has no Demographics rule, so the moved lines must reach the states through the
        monthly pulse: the script leaves their types, injections, pairs and pulse alone."""
        changed = R.run(ROOT, check=True)
        for path in ("common/modifier_type_definitions/demographics_engine_line_types.txt",
                     "common/laws/te_demog_engine_line_injections.txt",
                     "common/static_modifiers/te_demog_line_modifiers_generated.txt",
                     "common/script_values/te_demog_line_values_generated.txt",
                     "common/scripted_effects/te_demog_line_effects_generated.txt",
                     "common/on_actions/te_demog_on_actions.txt"):
            self.assertNotIn(ROOT / path, changed, path)
        # and the mod carriers' lines stay
        for carrier in ("common/laws/extra_laws.txt", "common/technology/technologies/era_7.txt"):
            old, new = changed.get(ROOT / carrier, ("", ""))
            self.assertNotIn("# RELEASE: \tstate_demog_", new)
```

  (`R` is the release module as the file already imports it; match its `run` signature.)

- [ ] **Step 2: Run it.** It passes as-is if the script only reads `demographics_modifier_types.txt`'s names. If it
  fails, narrow the script so it never touches the new types. Then run all of `test_release_census_inputs.py`; the
  "every other rule and trigger is left alone" test may need `te_demog_lines_apply` named as untouched.

- [ ] **Step 3: Commit**: "Release script: the moved engine lines ship".

### Task 8: Docs, guide and the in-game checklist

**Files:**
- Modify: `docs/systems/mod_systems.md` (§ The census's births and deaths: the arithmetic, the absorbed and on-top
  bullets, a new "The moved lines" bullet)
- Modify: `docs/superpowers/archive/plans/2026-10-10-demographics-phase2-engine-rates.md` §2 (an "Amended 2026-10-11 (2)"
  bullet pointing here)
- Modify: `docs/player_guide/08-states.md` (the paragraph on what applies on top), then rebuild the PDF
- Modify: `docs/testing/demographics-phase2-engine-rates-2026-10-10.md` (results and the checklist)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`te_demog_how_applied`)

- [ ] **Step 1: Player guide, chapter 8.** Replace the sentences about the census cancelling lines its tooltips still
  list with:

  "The birth and death effects of laws, technologies and institutions reach a state as one line, Laws and
  Institutions. Under the Full setting the census sets each state's births and deaths instead, and those effects work
  through it: the ones it models, such as the child labor and women's rights laws, the health laws, vaccines,
  antibiotics and the pill, become part of its own rates, and the rest apply at its rate."

  Rebuild with `.venv/bin/python scripts/build_player_guide.py`, and run
  `scripts/analysis/check_player_guide_style.py --strict`.

- [ ] **Step 2: The tab's text** (`te_demog_how_applied`): the same change, one sentence shorter.

- [ ] **Step 3: mod_systems and the plan.** Describe the arithmetic: m = tb − 1 − rep − os·(1 − tb) + q·tb. rep is now
  literacy and mild starvation only; os is the engine's state lines; q is the on-top family. Also describe the pairs,
  their trigger and pulse, the wealth pair and floor, and the release behaviour.

- [ ] **Step 4: The in-game checklist** (results doc, "Still to run"), for the owner:
  1. **Off (Disabled), a new 1836 game, Britain:** after the first month, a pop's mortality tooltip in the capital lists
     "Laws and Institutions" at the Ministry of Health's value (−3% × the institution impact) and the child labour line
     on laborers. A law's tooltip reads as before. Enacting Women in the Workplace changes the birth-rate line within a
     month.
  2. **At once:** on a new game, the capital's tooltip has the Laws and Institutions lines on day 1. Enacting a law
     changes them that day. A conquered state shows its new owner's lines the day it changes hands.
  3. **Full:** after the capital's first census step, the Laws and Institutions lines are gone, "Census: Births" and
     "Census: Deaths" are present, and option n's `q_b`, `q_d`, `w` are 0 in 1837.
  4. **A Private Health Insurance country under Full** (debug: enact it, Ministry of Health level 5): "Census: Deaths by
     Wealth" appears on a rich pop's tooltip at about wealth × max(−0.01, −0.005) × the census's share.
  5. **`debug.log`:** no error from `te_demog_line_*` or `te_demog_engine_line_injections.txt`.

- [ ] **Step 5: Run the whole suite and the checks:**
  - `.venv/bin/python -m unittest discover -s . -p 'test_*.py'` (read the summary with `grep -E '^(Ran |OK|FAILED)'`);
  - `ruff check .`;
  - the tab check;
  - `organize_loc.py --check`;
  - `gen_demographics.py --check`;
  - `scripts/build_player_guide.py --check`;
  - the CI audits.

- [ ] **Step 6: Commit**: "Demographics: docs and guide for the moved engine lines".
