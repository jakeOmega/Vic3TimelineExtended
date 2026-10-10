# Demographics modifier types, stage 2 (fertility): implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The census's fertility inputs from technology and laws become registered modifier types on their carriers in the game files: contraception (the techs' tiers, which now add) and the means shift (the family-planning law, Family Limitation). The contraception values are refitted against §2.3's anchors, with Britain in 1900 added.

**Architecture:** As in stage 1. `demographics_params.py` loses `MEANS_TIERS` and `MEANS_LAW_SHIFT` and keeps the model's constants: the traditional means 0.4, the literacy access 0.3 + 0.7 × literacy, the cap 0.95. `demographics_modifiers.py` resolves the two new types with the mortality ones. `demographics_model.means` and the generated `te_demog_means` read them: means = clamp(clamp(0.4 + contraception, 0, 1) × (0.3 + 0.7 × literacy) + shift, 0, 0.95). `country_fertility_means_add` becomes `state_fertility_means_add`, so every type the census reads is a state type read with `modifier:` (owner, 2026-10-10).

**Tech Stack:** Python 3.11/3.12 (unittest), Paradox script (`common/`), the generator `scripts/generators/gen_demographics.py`.

**Spec:** `docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md` (stage 2). Parent: `docs/superpowers/specs/2026-10-08-demographics-design.md` §2.3. Stage 1's plan (`2026-10-09-demographics-modifier-types-stage1.md`) is the pattern.

## Owner rulings this plan builds on

- The six calls of the modifier-types spec (2026-10-09), in particular call 3: **the means tiers add.** Researching the techs out of order gives a different means than today's highest-tier rule (the three techs are on no common prerequisite chain).
- **Every type is `state_*`**, read with `modifier:` in state scope; states inherit country modifiers, so a tech's, a law's or a country static modifier's line reaches every state (2026-10-10, stage 1). The country/state split is not to come back, so the existing `country_fertility_means_add` is renamed here.
- Values are recalibrated in the harness, not transcribed (spec, Decision 1).

## The types

| Type | Loc name | What it is | Carriers (starting value; Task 4 refits the techs) |
|---|---|---|---|
| `state_contraception_add` (new) | Contraception | the methods families have to limit births, added to the traditional 0.4; the census scales the sum by literacy | `vulcanization` +0.15 (INJECT, base game), `contraceptive_pill` +0.25 (mod, era 7, in place), `modern_pharmaceuticals` +0.10 (mod, era 8, in place) |
| `state_fertility_means_add` (renamed from `country_fertility_means_add`) | Fertility Control | a direct shift to the means, not scaled by literacy | `law_state_sponsored_family_planning` +0.10 (mod law, in place); the static modifier `te_demog_family_limitation` +0.6 (France's history; any event can grant it) |

The starting values are today's cumulative tiers (0.4 → 0.55 → 0.8 → 0.9) as increments, so in research order the census gives exactly today's means until Task 4 refits them.

**Not moved here:** the techs' and laws' flat `state_birth_rate_mult` lines (the Pill −0.10, the Family & Reproductive Policy laws). Those are engine modifiers that §8.4 moves into the model in phase 2.

## The fit Task 4 is expected to land near

Measured on 2026-10-10 against main 526e370f (scratch grid, desired-fertility weights and the traditional 0.4 unchanged):

| Scenario | Today | Contraception tiers 0.4 / 0.75 / 0.85 / 0.9 | History |
|---|---|---|---|
| 1836 agrarian reference | 6.03 | 6.03 | about 5.2 |
| Britain 1836 | 5.57 | 5.57 | about 5 |
| France 1836 (Family Limitation; the engine's Forced Heirship cut is not in the model) | 4.90 | 4.90 | about 3.8 |
| **Britain 1900** | **4.27** | **3.85** | about 3.5 |
| West 1950 | 3.07 | 2.55 | 2.5 (Europe) to 3.5 (US) |
| West 1990 | 1.47 | 1.47 | about 1.7 |
| India 1975 | 5.34 | 5.29 | about 5.2 |

Britain 1900 is the drift: stage 1 brought its life expectancy from 54.8 to a historical 46.1, which weakened the child-survival term. The 1836 rows can't move without changing the 1836 census, which no carrier reaches (no country starts with vulcanization, era 3), so the refit leaves them.

## Global Constraints

- Every input to the census that a law or technology changes is a registered type read with `modifier:`; no generated value names `has_technology_researched` or `has_law` for the means.
- Types: `script_only = yes`, `decimals` set, a name and `_desc` in `te_modifiers_l_english.yml` (loc_coverage_audit, modifier_visibility_audit).
- Every type name starts `state_`; none is read through `owner.`.
- A fresh 1836 census is unchanged: no 1836 country holds a contraception carrier, and France's Family Limitation keeps its 0.6.
- Brace-based files use tabs and exactly one UTF-8 BOM; run `scripts/format_paradox_tabs.py` on edited `.txt`.
- Never hand-edit `te_demog_generated_values.txt`: edit `gen_demographics.py` or the params and run `python3 scripts/generators/gen_demographics.py`.
- Local Python is 3.12, CI also 3.11: no PEP 701 f-strings.
- Venv: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` (the worktree has no `.venv`). The suite needs the dummy `VIC3_*` env vars from CLAUDE.md.

## Review Focus

1. **A state whose owner holds no carrier** (every 1836 country but France): means is exactly 0.4 × (0.3 + 0.7 × literacy), the same as before this stage. Pinned in Task 3 (model) and by the registry interpreter fixture.
2. **Out-of-order research** (the Pill without vulcanization, which the AI can do): means is 0.4 + the Pill's own increment, not the Pill's old 0.8 tier. Pinned in Task 3; written into the docs (Task 6).
3. **A negative shift** (a future pronatalist measure granting −0.2): the means floors at 0, never negative, so the fertility factor never exceeds 1. Pinned in Task 3.
4. **The clamp order**: the tier is clamped to [0, 1] before literacy multiplies it, and the 0.95 cap applies after the shift. Pinned in Task 3 (model) and Task 3's generator test (the nested block).
5. **The rename leaves nothing behind**: no file in `common/`, `localization/`, `scripts/`, tests or the live docs still names `country_fertility_means_add` (a save with France's static modifier loads it from the definition, so no migration is needed). Pinned by a grep test in Task 1.

---

### Task 1: The types, their loc, and the rename

**Files:**
- Modify: `common/modifier_type_definitions/demographics_modifier_types.txt`
- Modify: `localization/english/te_modifiers_l_english.yml`
- Modify: `common/static_modifiers/te_demog_modifiers.txt`
- Modify: `scripts/analysis/demographics_params.py`
- Modify: `scripts/generators/gen_demographics.py` (the one `add = owner.modifier:country_fertility_means_add` line)
- Regenerate: `common/script_values/te_demog_generated_values.txt`
- Test: `test_demographics_registry.py`, `test_gen_demographics.py`

**Interfaces:**
- Produces (params): `CONTRACEPTION_TYPE = "state_contraception_add"`, `MEANS_SHIFT_TYPE = "state_fertility_means_add"`, `DEMOG_FERTILITY_TYPES = (CONTRACEPTION_TYPE, MEANS_SHIFT_TYPE)`, `DEMOG_TYPES = DEMOG_MORTALITY_TYPES + DEMOG_FERTILITY_TYPES`, `TRADITIONAL_MEANS = 0.4`, `MEANS_ACCESS_BASE = 0.3` (read from Task 3 on).

- [ ] **Step 1: Write the failing tests.** In `test_demographics_registry.py`, class `TestModifierTypes`, add:

```python
    def test_fertility_types_are_registered_named_and_new(self):
        text, loc = _text(TYPES_FILE), _text(MODIFIERS_LOC)
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        for name in P.DEMOG_FERTILITY_TYPES:
            self.assertTrue(name.startswith("state_"), name)
            body = _block(text, name)
            self.assertIn("script_only = yes", body, name)
            self.assertRegex(body, r"decimals = \d", name)
            self.assertRegex(loc, rf"(?m)^ {name}:0 \"", name)
            self.assertRegex(loc, rf"(?m)^ {name}_desc:0 \"", name)
            self.assertNotIn(name, engine, name)

    def test_the_old_country_means_type_is_gone(self):
        # Review Focus 5: the rename leaves no reader, carrier, loc key or param behind
        old = "country_fertility_means_add"
        for sub in ("common", "localization", "scripts", "events", "gui"):
            for path in (ROOT / sub).rglob("*"):
                if path.is_file() and path.suffix in (".txt", ".yml", ".py", ".gui"):
                    self.assertNotIn(old, path.read_text(encoding="utf-8-sig", errors="ignore"), str(path))
```

and change `test_family_limitation_matches_the_params` (class `TestStep`) to expect `f"{P.MEANS_SHIFT_TYPE} = {P.FAMILY_LIMITATION_MEANS}"`. In `test_gen_demographics.py`, `test_means_read_the_modifier` becomes:

```python
    def test_means_read_the_modifier(self):
        body = self.values.split("te_demog_means = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(f"add = modifier:{P.MEANS_SHIFT_TYPE}", body)
        self.assertNotIn("owner.modifier:", body)
        self.assertLess(body.index(P.MEANS_SHIFT_TYPE), body.index("max = 0.95"))
```

- [ ] **Step 2: Run them to see them fail.** `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent $PY -m unittest test_demographics_registry.TestModifierTypes test_demographics_registry.TestStep.test_family_limitation_matches_the_params test_gen_demographics -v 2>&1 | grep -E '^(FAIL|ERROR|OK|Ran)'` (with `PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`). Expected: AttributeError on `P.DEMOG_FERTILITY_TYPES`, and failures.

- [ ] **Step 3: Params.** In `demographics_params.py`, after `DEMOG_MORTALITY_TYPES`, add:

```python
# ---- Fertility inputs as modifier types (modifier-types design, stage 2) -----------
# Contraception: the methods families have, added to TRADITIONAL_MEANS (the techs' lines add, so
# research order matters); the census scales the sum by literacy. The means shift: laws, history
# (Family Limitation), events and measures, added after literacy. Both are state types read with
# modifier:, their values on their carriers (demographics_modifiers.py).
CONTRACEPTION_TYPE = "state_contraception_add"
MEANS_SHIFT_TYPE = "state_fertility_means_add"
DEMOG_FERTILITY_TYPES = (CONTRACEPTION_TYPE, MEANS_SHIFT_TYPE)
DEMOG_TYPES = DEMOG_MORTALITY_TYPES + DEMOG_FERTILITY_TYPES
# The means to plan a family (§2.3): (TRADITIONAL_MEANS + state_contraception_add, at most 1) x
# (MEANS_ACCESS_BASE + (1 - MEANS_ACCESS_BASE) x literacy) + state_fertility_means_add, within
# 0..MEANS_CAP. Traditional methods everyone has; the techs' lines add to them (the Pill without
# vulcanization is 0.4 + the Pill's line). Values on the carriers: demographics_modifiers.py.
TRADITIONAL_MEANS = 0.4
MEANS_ACCESS_BASE = 0.3
```

and in the comment above `FAMILY_LIMITATION_MEANS` replace `country_fertility_means_add` with `state_fertility_means_add`.

- [ ] **Step 4: The type definitions.** In `demographics_modifier_types.txt`, replace the `country_fertility_means_add` block (and its header comment) with:

```
# Fertility: stage 2 of docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md.
# Read only by the census (te_demog_means, with modifier: in state scope). The means to plan a
# family = (0.4 + contraception, at most 1) x (0.3 + 0.7 x literacy) + the fertility-control
# shift, at most 0.95. Contraception sits on the techs; the shift on laws, history (Family
# Limitation) and events. Values are on the carriers (scripts/analysis/demographics_modifiers.py).
state_contraception_add = {
	color = neutral
	percent = yes
	decimals = 0
	script_only = yes
}
state_fertility_means_add = {
	color = neutral
	percent = yes
	decimals = 0
	script_only = yes
}
```

- [ ] **Step 5: Loc.** In `te_modifiers_l_english.yml`, delete the two `country_fertility_means_add` lines and add (organize_loc files them):

```
 state_contraception_add:0 "Contraception"
 state_contraception_add_desc:0 "The methods families have to space or limit births, beyond the traditional ones everyone has. How much of it people use depends on how many can read. Used by the census on the Demographics tab."
 state_fertility_means_add:0 "Fertility Control"
 state_fertility_means_add_desc:0 "How much more of the gap between the children families want and the children they would have without trying they can close, whatever they can read: programs, clinics and custom. Used by the census on the Demographics tab."
```

- [ ] **Step 6: The static modifier and the generator line.** In `te_demog_modifiers.txt`, `country_fertility_means_add = 0.6` becomes `state_fertility_means_add = 0.6`. In `gen_demographics.py`, the two lines

```python
    o("# history, events and measures: Family Limitation and its kin (country_fertility_means_add)")
    o("add = owner.modifier:country_fertility_means_add")
```

become

```python
    o(f"# laws, history, events and measures: Family Limitation and its kin ({P.MEANS_SHIFT_TYPE})")
    o(f"add = modifier:{P.MEANS_SHIFT_TYPE}")
```

Run `$PY scripts/generators/gen_demographics.py`, then `python3 organize_loc.py` (commit whatever it moves), then `python3 scripts/format_paradox_tabs.py common/modifier_type_definitions/demographics_modifier_types.txt common/static_modifiers/te_demog_modifiers.txt`.

- [ ] **Step 7: Run the tests.** Same command as Step 2, plus `$PY -m unittest test_demographics_model test_demographics_modifiers`. Expected: all OK (the old name may still appear in `docs/`; the grep test reads code and loc only).

- [ ] **Step 8: Commit** by path: the six files above, the regenerated values, any loc file organize_loc moved, and both test files. Message: "Demographics: the fertility types (contraception; fertility control as a state type)".

### Task 2: The carriers in the game files

**Files:**
- Modify: `common/technology/technologies/te_demog_tech_injections.txt` (INJECT on `vulcanization`)
- Modify: `common/technology/technologies/era_7.txt` (`contraceptive_pill`), `era_8.txt` (`modern_pharmaceuticals`)
- Modify: `common/laws/extra_laws.txt` (`law_state_sponsored_family_planning`)
- Modify: `scripts/analysis/demographics_modifiers.py` (default `types=P.DEMOG_TYPES` in `load_carriers` and `totals`)
- Test: `test_demographics_modifiers.py`

**Interfaces:**
- Consumes: `P.DEMOG_TYPES`, `P.CONTRACEPTION_TYPE`, `P.MEANS_SHIFT_TYPE` (Task 1).
- Produces: `DM.totals(...)` returns all nine types; `DM.load_carriers()` returns the fertility carriers too.

- [ ] **Step 1: Write the failing tests.** In `test_demographics_modifiers.py`: `test_nothing_held_is_all_zero` asserts `set(t) == set(P.DEMOG_TYPES)`; `test_every_type_has_a_carrier` loops over `P.DEMOG_TYPES`; `test_each_type_sits_where_its_design_puts_it` adds `P.CONTRACEPTION_TYPE: {"technology"}, P.MEANS_SHIFT_TYPE: {"law"}`. Add:

```python
    def test_contraception_sits_on_the_three_means_techs(self):
        lines = {c.key: c.value for c in self.carriers if c.type == P.CONTRACEPTION_TYPE}
        self.assertEqual(set(lines), {"vulcanization", "contraceptive_pill", "modern_pharmaceuticals"})
        self.assertTrue(all(v > 0 for v in lines.values()), lines)
        # all three together keep the tier at or below 1
        self.assertLessEqual(P.TRADITIONAL_MEANS + sum(lines.values()), 1.0)

    def test_family_planning_law_shifts_the_means(self):
        lines = {c.key: c.value for c in self.carriers if c.type == P.MEANS_SHIFT_TYPE}
        self.assertEqual(lines, {"law_state_sponsored_family_planning": 0.1})
```


- [ ] **Step 2: Run to see them fail.** `$PY -m unittest test_demographics_modifiers -v 2>&1 | grep -E '^(FAIL|ERROR|OK|Ran)'`. Expected: failures (no fertility carriers).

- [ ] **Step 3: The carriers.** Append to `te_demog_tech_injections.txt` (the base game's `vulcanization` has no `modifier` block; the INJECT adds one):

```
# Stage 2 (fertility): rubber condoms. The census adds each means tech's line to the
# traditional 0.4 (demographics_harness.py fertility). contraceptive_pill and
# modern_pharmaceuticals carry theirs in era_7.txt and era_8.txt.
INJECT:vulcanization = {
	modifier = {
		state_contraception_add = 0.15
	}
}
```

In `era_7.txt`, `contraceptive_pill`'s `modifier` block, first line: `state_contraception_add = 0.25	# the census's means (demographics modifier types, stage 2)`. In `era_8.txt`, `modern_pharmaceuticals`, under the existing stage-1 comment: `state_contraception_add = 0.1`, and extend that comment to "(demographics modifier types, stages 1 and 2)". In `extra_laws.txt`, `law_state_sponsored_family_planning`'s `modifier`: add `state_fertility_means_add = 0.1	# the census's means (demographics modifier types, stage 2)`.

- [ ] **Step 4: The resolver defaults.** In `demographics_modifiers.py`, `load_carriers(root=ROOT, types=P.DEMOG_TYPES)` and `totals(..., types=P.DEMOG_TYPES)`; the module docstring's first paragraph says "the census's mortality and fertility types".

- [ ] **Step 5: Run the tests.** `$PY -m unittest test_demographics_modifiers test_demographics_model test_demographics_harness 2>&1 | grep -E '^(FAIL|ERROR|OK|Ran)'`. Expected: OK (the model doesn't read the fertility totals yet).

- [ ] **Step 6: Tabs and BOM.** `python3 scripts/format_paradox_tabs.py` on the four `common/` files; `head -c3 <file> | xxd` shows `efbbbf` once on each.

- [ ] **Step 7: Commit** by path. Message: "Demographics: the fertility types' carriers (the means techs, State-Sponsored Family Planning)".

### Task 3: The model and the generator read the fertility types

**Files:**
- Modify: `scripts/analysis/demographics_params.py` (drop `MEANS_TIERS`, `MEANS_LAW_SHIFT`)
- Modify: `scripts/analysis/demographics_model.py` (`means`)
- Modify: `scripts/generators/gen_demographics.py` (`te_demog_means`)
- Regenerate: `common/script_values/te_demog_generated_values.txt`
- Test: `test_demographics_model.py`, `test_gen_demographics.py`

**Interfaces:**
- Consumes: `inp.mods` (a `{type: total}` from `DM.totals`), `inp.means_add` (sources the resolver doesn't read: static modifiers such as Family Limitation), `P.CONTRACEPTION_TYPE`, `P.MEANS_SHIFT_TYPE`.
- Produces: `M.means(inp) -> float`, unchanged signature.

**Reviewer (one, after this task):** the generated block's clamp order against `M.means` (Review Focus 3 and 4), that nothing in `te_demog_means` names a tech or law, and that the registry interpreter's `te_demog_means` fixture still comes from `M.means`.

- [ ] **Step 1: Write the failing tests.** In `test_demographics_model.py`, add a class:

```python
class TestMeans(unittest.TestCase):
    """The means to plan a family from the fertility types (modifier-types design, stage 2)."""

    def inp(self, literacy=0.5, mods=None, means_add=0.0):
        return M.Inputs(literacy=literacy, mods=dict(mods or {}), means_add=means_add)

    def access(self, literacy):
        return P.MEANS_ACCESS_BASE + (1 - P.MEANS_ACCESS_BASE) * literacy

    def test_no_carrier_is_the_traditional_means(self):
        # Review Focus 1: every 1836 country but France
        self.assertAlmostEqual(M.means(self.inp(0.35)), P.TRADITIONAL_MEANS * self.access(0.35))

    def test_techs_add_in_any_order(self):
        # Review Focus 2: the Pill without vulcanization is the base plus the Pill's own line
        carriers = DM.load_carriers()
        pill_only = DM.totals(carriers, techs={"contraceptive_pill"})
        both = DM.totals(carriers, techs={"vulcanization", "contraceptive_pill"})
        pill = {c.key: c.value for c in carriers if c.type == P.CONTRACEPTION_TYPE}["contraceptive_pill"]
        self.assertAlmostEqual(M.means(self.inp(1.0, pill_only)), P.TRADITIONAL_MEANS + pill)
        self.assertGreater(M.means(self.inp(1.0, both)), M.means(self.inp(1.0, pill_only)))

    def test_the_shift_is_not_scaled_by_literacy(self):
        low = M.means(self.inp(0.0, {P.MEANS_SHIFT_TYPE: 0.1}))
        self.assertAlmostEqual(low, P.TRADITIONAL_MEANS * self.access(0.0) + 0.1)

    def test_static_and_law_shifts_add(self):
        both = M.means(self.inp(0.3, {P.MEANS_SHIFT_TYPE: 0.1}, means_add=P.FAMILY_LIMITATION_MEANS))
        self.assertAlmostEqual(both, min(P.TRADITIONAL_MEANS * self.access(0.3) + 0.1 + P.FAMILY_LIMITATION_MEANS,
                                         P.MEANS_CAP))

    def test_the_tier_is_clamped_before_literacy(self):
        # Review Focus 4: a tier above 1 counts as 1
        self.assertAlmostEqual(M.means(self.inp(0.0, {P.CONTRACEPTION_TYPE: 5.0})), self.access(0.0))

    def test_a_negative_shift_floors_at_zero(self):
        # Review Focus 3: a pronatalist measure never makes the fertility factor exceed 1
        self.assertEqual(M.means(self.inp(0.0, {P.MEANS_SHIFT_TYPE: -2.0})), 0.0)

    def test_cap(self):
        self.assertEqual(M.means(self.inp(1.0, {P.CONTRACEPTION_TYPE: 1.0, P.MEANS_SHIFT_TYPE: 1.0})), P.MEANS_CAP)
```

(add `import demographics_modifiers as DM` at the top if the file lacks it; `scenario()` already uses `DM`). Replace `test_means_capped` in `TestFertility` with nothing (TestMeans.test_cap covers it). In `test_gen_demographics.py` add:

```python
    def test_means_read_the_types_not_techs_or_laws(self):
        body = self.values.split("te_demog_means = {", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn("has_technology_researched", body)
        self.assertNotIn("has_law", body)
        # the tier is clamped inside its own block, before literacy multiplies it
        tier = body.split("value = {", 1)[1].split("}", 1)[0]
        self.assertIn(f"value = modifier:{P.CONTRACEPTION_TYPE}", tier)
        self.assertIn(f"add = {gen.lit(P.TRADITIONAL_MEANS)}", tier)
        self.assertIn("min = 0", tier)
        self.assertIn("max = 1", tier)
        self.assertLess(body.index("multiply = { value = var:te_dg_lit"), body.index(f"modifier:{P.MEANS_SHIFT_TYPE}"))
```

- [ ] **Step 2: Run to see them fail.** `$PY -m unittest test_demographics_model.TestMeans test_gen_demographics -v 2>&1 | grep -E '^(FAIL|ERROR|OK|Ran)'`. Expected: failures (the model and generator still read the tiers).

- [ ] **Step 3: Params.** Delete the `MEANS_TIERS` and `MEANS_LAW_SHIFT` lines (Task 1 added `TRADITIONAL_MEANS` and `MEANS_ACCESS_BASE`). Keep `MEANS_CAP` and `FAMILY_LIMITATION_MEANS`.

- [ ] **Step 4: The model.** Replace `means` in `demographics_model.py`:

```python
def means(inp):
    """The share of the gap to desired fertility a population can close (§2.3; stage 2's types)."""
    tier = clamp(P.TRADITIONAL_MEANS + inp.mods.get(P.CONTRACEPTION_TYPE, 0.0), 0.0, 1.0)
    access = P.MEANS_ACCESS_BASE + (1 - P.MEANS_ACCESS_BASE) * inp.literacy
    shift = inp.mods.get(P.MEANS_SHIFT_TYPE, 0.0) + inp.means_add
    return clamp(tier * access + shift, 0.0, P.MEANS_CAP)
```

and the `Inputs.means_add` comment: `# static modifiers' state_fertility_means_add (Family Limitation 0.6); laws' lines come through mods`.

- [ ] **Step 5: The generator.** Replace the `te_demog_means` writer in `gen_demographics.py` with:

```python
    o("# State scope: the share of the gap to desired fertility a population can close (spec 2.3;")
    o("# demographics modifier types, stage 2): traditional methods plus the techs' contraception,")
    o("# at most 1, scaled by literacy, plus the fertility-control shift.")
    o("te_demog_means = {")
    o("value = {")
    o(f"value = modifier:{P.CONTRACEPTION_TYPE}")
    o(f"add = {lit(P.TRADITIONAL_MEANS)}")
    o("min = 0")
    o("max = 1")
    o("}")
    o(f"multiply = {{ value = var:te_dg_lit multiply = {lit(1 - P.MEANS_ACCESS_BASE)} add = {lit(P.MEANS_ACCESS_BASE)} }}")
    o(f"# laws, history, events and measures: Family Limitation and its kin ({P.MEANS_SHIFT_TYPE})")
    o(f"add = modifier:{P.MEANS_SHIFT_TYPE}")
    o(f"max = {lit(P.MEANS_CAP)}")
    o("min = 0")
    o("}")
    o("")
```

(`Out` indents by brace depth; check the output's tabs match the neighbours.) Run `$PY scripts/generators/gen_demographics.py`.

- [ ] **Step 6: Run the tests.** `$PY -m unittest test_demographics_model test_gen_demographics test_demographics_registry test_demographics_harness test_demographics_modifiers 2>&1 | grep -E '^(FAIL|ERROR|OK|Ran)'`. Expected: OK. In research order the starting values give today's tiers, so `TestFertility.test_sketch_cases` and the registry interpreter's seed tests pass unchanged; if a sketch case moved, a starting value is wrong.

- [ ] **Step 7: Commit** by path. Message: "Demographics: the census reads the means from the fertility types (contraception tiers add)".

### Task 4: Calibration

**Files:**
- Modify: `scripts/analysis/demographics_harness.py` (`fertility` command, `FERTILITY_SCENARIOS`)
- Modify: the three techs' lines (Task 2's files) to the fitted values
- Test: `test_demographics_harness.py`, `test_demographics_model.py` (`test_sketch_cases` gains Britain 1900)

**Interfaces:**
- Consumes: `life(inp)`, `scenario_inputs(carriers, **kw)`, `MED_*`, `CHS`, `PHI`, `HEALTH` (harness, stage 1); `M.fertility(inp, e0)`.
- Produces: `fertility_rows(carriers=None) -> [(label, tfr, low, high)]`, `cmd_fertility`, `FERTILITY_SCENARIOS`.

- [ ] **Step 1: The failing test.** In `test_demographics_harness.py`:

```python
    def test_fertility_anchors_hold(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["fertility"]), 0, out.getvalue())
        for label, _kw, _band in H.FERTILITY_SCENARIOS:
            self.assertIn(label, out.getvalue())
        self.assertNotIn(" OUT", out.getvalue())

    def test_fertility_rows_match_the_models_steady_state(self):
        # the command's shortcut (fertility at the scenario's own e0) is what a constant run settles on
        label, kw, _band = H.FERTILITY_SCENARIOS[1]
        inp = H.scenario_inputs(DM.load_carriers(), **kw)
        _ring, last = M.run_constant(inp, years=200)
        row = next(r for r in H.fertility_rows() if r[0] == label)
        self.assertAlmostEqual(row[1], last["tfr"], places=2)
```

(import `demographics_modifiers as DM` and `demographics_model as M` in the test if absent). In `test_demographics_model.py`, `TestFertility.test_sketch_cases` gains `(BRITAIN_1900, 3.6, "Britain 1900")` with a module-level

```python
BRITAIN_1900 = scenario(sol=16, literacy=0.75, urban_share=0.6,
                        techs=frozenset({"medical_degrees", "pharmaceuticals", "modern_nursing", "vulcanization"}),
                        laws=frozenset({"law_charitable_health_system"}), institutions={"institution_health_system": 4})
```

Its `WEST_1950` holds vulcanization, so its 3.1 drops to the fitted figure (about 2.6 at the table's tiers); `INDIA_1975` (vulcanization and the Pill) moves a little. Update both after Step 4, keeping `delta=0.3`.

- [ ] **Step 2: Run to see them fail.** `$PY -m unittest test_demographics_harness test_demographics_model.TestFertility 2>&1 | grep -E '^(FAIL|ERROR|OK|Ran)'`. Expected: an unknown `fertility` command; Britain 1900 at 4.27 against 3.6.

- [ ] **Step 3: The command.** In `demographics_harness.py`, after the medicine section:

```python
# ---- fertility: children per woman (modifier-types design, stage 2) -----------------------------
# (label, inputs, (low, high)): §2.3's sketch table and history. The 1836 rows hold no means tech, so
# only the traditional means and literacy reach them; France's engine cut from Forced Heirship is
# not in the model, so its band is wide.
MEANS_TECHS = {"vulcanization"}
FERTILITY_SCENARIOS = [
    ("1836 agrarian (reference)", dict(sol=8, literacy=0.2, urban_share=0.1), (4.8, 6.2)),
    ("Britain 1836", dict(sol=11, literacy=0.35, urban_share=0.3, techs=MED_1836, laws={CHS},
                          institutions={HEALTH: 1}), (4.5, 5.8)),
    ("France 1836 (Family Limitation)", dict(sol=11, literacy=0.3, urban_share=0.15, techs=MED_1836,
                                             means_add=P.FAMILY_LIMITATION_MEANS), (3.4, 5.0)),
    ("Britain 1900", dict(sol=16, literacy=0.75, urban_share=0.6, techs=MED_1900 | MEANS_TECHS, laws={CHS},
                          institutions={HEALTH: 4}), (3.2, 4.0)),
    ("West 1950", dict(sol=25, literacy=0.95, urban_share=0.65, techs=MED_1950 | MEANS_TECHS, laws={PHI},
                       institutions={HEALTH: 5}), (2.3, 3.5)),
    ("West 1990", dict(sol=38, literacy=0.98, urban_share=0.75,
                       techs=MED_1990 | MEANS_TECHS | {"contraceptive_pill"}, laws={PHI},
                       institutions={HEALTH: 6}), (1.4, 2.0)),
    ("India 1975", dict(sol=9, literacy=0.35, urban_share=0.2, techs=MED_1950 | MEANS_TECHS | {"contraceptive_pill"},
                        laws={CHS}, institutions={HEALTH: 1}), (4.7, 5.8)),
]


def fertility_rows(carriers=None):
    """[(label, children per woman, low, high)] for FERTILITY_SCENARIOS, with the game files' values."""
    carriers = DM.load_carriers() if carriers is None else carriers
    rows = []
    for label, kw, (lo, hi) in FERTILITY_SCENARIOS:
        inp = scenario_inputs(carriers, **kw)
        rows.append((label, M.fertility(inp, life(inp)["e0"])["tfr"], lo, hi))
    return rows


def cmd_fertility(_args):
    out = 0
    for label, tfr, lo, hi in fertility_rows():
        ok = lo <= tfr <= hi
        out |= not ok
        print(f"{label:34s} children per woman {tfr:4.2f} [{lo:g}-{hi:g}]{'' if ok else ' OUT'}")
    return out
```

`MED_1990` already holds `modern_pharmaceuticals`. Register it in `main`: `sub.add_parser("fertility").set_defaults(fn=cmd_fertility)`, and add the usage line `demographics_harness.py fertility                   # children per woman with the game files' values` to the docstring. If `scenario_inputs` rejects `means_add`, it already passes `**kw` to `M.Inputs`, which has the field.

- [ ] **Step 4: Fit.** A scratch script (not committed) varies the three techs' lines in steps of 0.05, subject to the traditional 0.4 plus all three ≤ 1.0, with the traditional means and the desired-fertility weights fixed (they move the 1836 census). It patches the carriers in memory (`DM.Carrier(..., value=x)`), and ranks the candidates first by total distance outside the bands, then by the sum of squared distances to the history column of this plan's fit table (Britain 1900 3.5, West 1950 2.9, West 1990 1.7, India 1975 5.2; the 1836 rows don't move). Expected to land near vulcanization +0.35, Pill +0.10, modern pharmaceuticals +0.05 (tiers 0.75 / 0.85 / 0.9). Write the winner into the three carriers. If no candidate meets every band, stop and report: raising the survival weight is the next lever and it changes the 1836 census, which is an owner call.

- [ ] **Step 5: Run.** `$PY scripts/analysis/demographics_harness.py fertility` (exit 0), `$PY scripts/analysis/demographics_harness.py medicine` (exit 0; the means don't touch mortality, so this must be unchanged), then the five demographics test files. Update `test_sketch_cases`' West 1950 and West 1990 expectations to the fitted figures (`delta=0.3`).

- [ ] **Step 6: Commit** by path, with the fit table (before, after, history) in the message body. Message: "Demographics: fit the contraception tiers (Britain 1900 back near 3.5)".

### Task 5: The console readout

Built by the controller.

**Files:**
- Modify: `common/script_values/te_debug_demog_values.txt`, `common/scripted_effects/te_debug_demog_effects.txt` (`te_debug_demog_mods_line`), `localization/english/te_events_l_english.yml` (`te_debug_demog.1.l` and `.l.tt`)

- [ ] **Step 1:** Add `te_debug_demog_mod_contra = { value = modifier:state_contraception_add }`, `te_debug_demog_mod_fmeans = { value = modifier:state_fertility_means_add }` and `te_debug_demog_means = { value = te_demog_means }` beside `te_debug_demog_mod_access`. The `TE_DEMOG_MODS` line gains ` contra=[THIS.ScriptValue('te_debug_demog_mod_contra')|3] fmeans=[THIS.ScriptValue('te_debug_demog_mod_fmeans')|3] means=[THIS.ScriptValue('te_debug_demog_means')|3]` before ` date=`. The option's name becomes "Census modifier types: log what our states read", and the tooltip gains: "Contraception and Fertility Control should read the same in both states; as France at the start, Fertility Control is 0.6."
- [ ] **Step 2:** `python3 scripts/analysis/check_localization_files.py`, the tab formatter on the two `.txt` files, then the registry tests (`test_demographics_registry`). Commit: "Demographics console: option l logs the fertility types".

### Task 6: Docs and the player guide

Built by the controller.

**Files:**
- Modify: `docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md` (status line; the table's two fertility rows with the `state_` names and carriers; a "Stage 2 fit" paragraph with the fitted values and the before/after table; out-of-order research)
- Modify: `docs/superpowers/specs/2026-10-08-demographics-design.md` §2.3 (the means table: values now on the carriers, the tiers add; point to the modifier-types spec)
- Modify: `docs/systems/mod_systems.md` (the `country_fertility_means_add` paragraph → `state_fertility_means_add` and `state_contraception_add`, carriers, the rule)
- Modify: `docs/guides/python_tools.md` (the harness row: ten commands, `fertility`)
- Modify: `docs/player_guide/08-states.md`, then rebuild the PDF
- Modify: `docs/testing/demographics-fast-run-2026-10-09.md`? No: the fit goes in the spec; the testing doc is stage 1's run.

- [ ] **Step 1:** The edits above. The guide's sentence "the means to plan a family grow with literacy and medicine" becomes: "the means to plan a family grow with literacy and with contraception: Vulcanization, the Contraceptive Pill and Modern Pharmaceuticals each add some, in any order, and State-Sponsored Family Planning adds more, whoever can read. Their tooltips show each line." Keep the guide's depth: no values.
- [ ] **Step 2:** `python3 scripts/analysis/check_player_guide_style.py --strict docs/player_guide/08-states.md`, then `$PY scripts/build_player_guide.py`, then `$PY scripts/build_player_guide.py --check`. Check the CRLF docs aren't touched (`grep -c $'\r$'`).
- [ ] **Step 3:** Commit the docs, chapter and PDF together. Message: "Demographics stage 2: docs, spec and player guide".

### Task 7: Verify, review, draft PR

- [ ] **Step 1: Whole suite** with the dummy env vars: `$PY -m unittest discover -s . -p 'test_*.py' > /tmp/…/suite.txt 2>&1; grep -E '^(Ran |OK|FAILED)' …`.
- [ ] **Step 2: Lint and audits:** `/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff check .`; `python3 scripts/format_paradox_tabs.py --check` on the changed `.txt`; `python3 organize_loc.py --check`; `python3 scripts/analysis/check_localization_files.py`; the strict audits that touch these files: `loc_coverage_audit.py --strict`, `duplicate_key_audit.py --strict`, `empty_effect_audit.py --strict`, `script_argument_audit.py --strict`; one BOM on every changed `.txt` and `.yml`; the PEP 701 grep from CLAUDE.md on changed `.py`.
- [ ] **Step 3: Whole-branch review:** one fresh reviewer (script and Python), read-only, severity-ranked; fix, then the reviewer's final verdict.
- [ ] **Step 4: Push and open a draft PR** to `main` (`gh pr create --draft --base main`). Body: what changed, the fit table, Review Focus, the owner calls (below), a "Player guide" line naming `08-states.md`, and the in-game checks:
  1. The first launch shows no error naming `state_contraception_add`, `state_fertility_means_add` or `te_demog_generated_values.txt`.
  2. Vulcanization's, the Contraceptive Pill's, Modern Pharmaceuticals' and State-Sponsored Family Planning's tooltips show their line; France's state modifier breakdown shows Fertility Control +60%.
  3. `event te_debug_demog.1` option l as France at the start: `fmeans=0.600` and `contra=0.000` in both lines, `means` equal to 0.4 × (0.3 + 0.7 × the capital's literacy) + 0.6.
  4. France's and Britain's children per woman on the Demographics tab at the start match a pre-stage game (the means did not change in 1836).
  Then write the PR body to a file before returning, as CLAUDE.md asks.

**Owner calls for the PR body:**
1. Before the Pill, vulcanization is the only means tech, and the fit puts most of the 19th-century fall on it (about +0.35). A broader carrier (an era-4 or era-5 social technology for the spread of birth-control knowledge) would spread it; not built.
2. The fit leaves the 1836 rows: Britain 5.57 against about 5, France 4.9 against 3.8 (the engine's Forced Heirship cut comes on top in game). Bringing them down needs the traditional means or the desired-fertility weights, which changes the 1836 census: phase 2's calibration.
