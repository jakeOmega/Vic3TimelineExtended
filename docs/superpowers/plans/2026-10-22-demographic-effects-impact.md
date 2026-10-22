# Demographic effects that matter: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Wealth Concentration and the census's consequence modifiers strong and distinct (a strong condition worth one vanilla law), on curves that keep rising past their reference, with Phase 0's readouts to check the sizes.

**Architecture:** Phase 0's tools come first and need no save: a flat bubble term in the banking simulator, a Python module holding every condition's old and new curve and the new sizes, and the harness's `wc`, `gini` and new `effects` readouts. Then one task per condition re-anchors its script values on the extended curve `(x + min(x, 1)) / 2`, resizes its static modifiers, and pins script to the Python module. Model terms (the fertility scale, the women's rate, crowding) keep their 0–1 ramps; only `add_modifier` multipliers and the panel's shown sizes read the extended strengths.

**Tech Stack:** Paradox script (Victoria 3 1.14.5), Python 3.11/3.12 (`unittest`), the repo's generators `gen_demographics.py` and `gen_nation_tab.py`.

**Spec:** `docs/superpowers/specs/2026-10-22-demographic-effects-impact-design.md`

## Global Constraints

- The extended curve: for a ramp `x` ≥ 0 that reads 1 at the reference, strength = `(x + min(x, 1)) / 2`, capped at 2 only where the scale has no natural end. Wealth Concentration's upper end is straight (no kink).
- In script, every extended strength is `value = <reach> add = { value = <reach> max = 1 } divide = 2` (plus `max = 2` where capped), where `<reach>` is a named script value clamped at `min = 0` and never at a max.
- One script value per modifier multiplier, and each modifier keeps exactly one refresh site.
- Model terms keep their 0–1 ramps: `te_demog_sex_fewer_men` (read by `te_demog_sex_women_shown` and `te_demog_sex_women_add`'s panel), `te_demog_mt_e_pos` (read by `te_demog_mt_fertility_scale` and crowding), `te_demog_mt_e_neg`.
- No modifier field a vanilla law already carries may move on an inheritance law (`TestInheritanceBalance.test_no_inheritance_law_repeats_what_the_score_carries`).
- Brace-based `.txt` files use tabs and exactly one UTF-8 BOM. Loc goes in existing `*_l_english.yml` files, then `python3 organize_loc.py`, and commit what it rewrites.
- Loc names game objects through `$key$` splices, never spelled names; bold is `#b X#!`.
- Never hand-edit generated files: `te_demog_generated_values.txt` comes from `scripts/generators/gen_demographics.py`, the Nation tab's files from `scripts/generators/gen_nation_tab.py`.
- Python must compile on 3.11: no f-string reusing its own quote inside braces.
- Each task runs only its own tests and lints (`.venv/bin/python -m unittest <files>`, from `/home/jakef/src/Vic3TimelineExtended/.venv`); the full suite runs once, in Task 9.

## Review Focus

1. **A save from before the build, or from a Display/Disabled game:** states lack `te_dg_gini`, `te_dg_mt` or the census bands. `effects` skips a missing figure per condition and still prints the others (Task 3 test `test_effects_skips_missing_figures`).
2. **A score just past neutral:** the span drops from 50 to 30, so 50.4 now gives 0.013 and the 0.01 apply threshold lets it through. The threshold test moves to 50.2 (Task 4, `TestWealthStateModifiers`).
3. **The rule switched from Full to Display:** the new crowding modifier must go with Metropolis. `te_demog_mt_state_refresh` removes both before its Full gate (Task 7 test `test_both_go_outside_full`).
4. **Extreme inputs on a capped scale:** 100% youth unemployment, a balance of 40 men, primacy 1.0. Each strength stops at 2 (Task 2 tests `test_caps`).
5. **A banking cycle that never starts, or the banking rule off:** the bubble field must sit only on the national pair, where nothing reads it until `banking_cycle_advance_variables` runs (Task 4 test `test_bubble_pressure_only_on_the_national_pair`).

---

### Task 1: The banking simulator's flat bubble term (Phase 0)

**Files:**
- Modify: `scripts/analysis/banking_cycle_sim.py` (`Config` ~734-814, `advance_variables` ~2034-2079, `main` ~3837-4110)
- Modify: `docs/audits/banking_cycle_simulation.md` (a new last section)
- Test: `test_banking_sim_extensions.py`

**Interfaces:**
- Produces: `Config.extra_bubble: float = 0.0`; CLI `--extra-bubble X`.

- [ ] **Step 1: Write the failing tests** in `test_banking_sim_extensions.py`, class `ExtraBubble`:

```python
def test_default_is_zero(self):
    self.assertEqual(sim.Config().extra_bubble, 0.0)

def test_non_finite_is_rejected(self):
    with self.assertRaises(ValueError):
        sim.Config(extra_bubble=float("nan"))

def test_a_standing_push_raises_bubble_and_crashes(self):
    base = sim.run_cell(... seed=1, runs=40, years=100, extra_bubble=0.0)   # use the module's existing cell runner
    push = sim.run_cell(... seed=1, runs=40, years=100, extra_bubble=0.5)
    self.assertGreater(push["bubble_mean"], base["bubble_mean"])
    self.assertGreaterEqual(push["crashes_per_century_mean"], base["crashes_per_century_mean"])
```

Use whatever runner `_run_cell` / `summarise` already expose; if `summarise` has no mean bubble, add `bubble_mean` through `extension_summary` (opt-in, written only when `extra_bubble` is nonzero).

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_banking_sim_extensions -v`. Expected: the three new tests FAIL; `test_default_market_json_is_byte_identical_to_before_extensions` passes.

- [ ] **Step 3: Implement.** `Config.extra_bubble` with a finiteness check in `__post_init__` (as `wage_pressure`). In `advance_variables`, after the law line (~2045): `if cfg.extra_bubble: state.bubble_pressure += cfg.extra_bubble` (the guard keeps a 0 run bit-identical). Pass the flag through every `Config(...)` in `main` (the matrix ~4052-4081 and the peg-slump, holiday and rescue branches), and add `, extra bubble X` to `print_table`'s header when nonzero.

- [ ] **Step 4: Run** the test file again. Expected: all PASS, including the byte-identical test.

- [ ] **Step 5: Measure.** Run with `--economy market --runs 400 --points 0,5 --only gold` at `--extra-bubble` 0, 0.3, −0.3, 0.5, −0.4. Write the table (crashes a century, mean and p10/p90, untooled and at 5 points) into a new last section of `docs/audits/banking_cycle_simulation.md`, "Wealth Concentration's bubble line (2026-10-22)", with the spec's test: keep ±0.3 if +0.3 raises untooled crashes by 10–30% and −0.3 lowers them by 10–25%; otherwise state the rescaled size. If the size moves, change `BUBBLE_GREAT` / `BUBBLE_DISPERSED` in Task 2's module before Task 4 runs.

- [ ] **Step 6: Commit** `scripts/analysis/banking_cycle_sim.py`, `test_banking_sim_extensions.py`, `docs/audits/banking_cycle_simulation.md`: "Banking simulator: a flat bubble term for Wealth Concentration's line".

---

### Task 2: The curves and sizes in Python (Phase 0)

**Files:**
- Create: `scripts/analysis/demographics_effects.py`
- Test: create `test_demographics_effects.py`

**Interfaces:**
- Produces, in `demographics_effects.py` (imported as `DE`):
  - `extended(x: float, cap: float | None = None) -> float`: `(max(x, 0) + min(max(x, 0), 1)) / 2`, at most `cap`.
  - Reference constants: `WC_NEUTRAL = 50`, `WC_SPAN = 30`; `UP_FLOOR = 0.25`, `UP_SPAN = 0.25`; `MT_FROM = 40`, `MT_FULL = 60`, `MT_DISPERSED_FROM = 20`, `MT_DISPERSED_FULL = 5`; `SEX_MORE_FROM = 110`, `SEX_MORE_FULL = 130`, `SEX_FEWER_FROM = 90`, `SEX_FEWER_FULL = 80`; `YOUTH_FROM = 0.18`, `YOUTH_SPAN = 0.06`, `YOUTH_UNEMPLOYMENT_FULL = 0.2`; `GINI_FROM = 0.45`, `GINI_STEEP = 0.70`, `GINI_SPAN = 0.20`; `CAP = 2.0`.
  - New strengths, each taking the raw figure: `wc_high(score)`, `wc_low(score)`, `primacy(p)`, `metro_up(share)`, `metro_down(share)`, `fewer_men(balance)`, `more_men(balance)`, `youth(share, unemployment)`, `inequality(gini)`. `None` in → 0.
  - Old strengths for comparison, same signatures, suffix `_old`: WC span 50 clamped 0–1, primacy span 0.35 clamped, metro clamped, More Men full at 150 clamped, Fewer Men clamped, youth's two factors clamped, inequality `5 × max(g − 0.45, 0)`.
  - `SIZES: dict[str, dict[str, float]]`: every resized modifier's fields at 1×, copied from the spec's tables (Tasks 4–8 pin script to it). `BUBBLE_GREAT = 0.3`, `BUBBLE_DISPERSED = -0.3` are the national pair's bubble fields inside `SIZES`.
  - `CONDITIONS: dict[str, tuple[old_fn, new_fn]]` keyed `wc_high`, `wc_low`, `primacy`, `metro_up`, `metro_down`, `fewer_men`, `more_men`, `inequality` (youth takes two figures and is handled by name).

- [ ] **Step 1: Write the failing tests** in `test_demographics_effects.py`, the spec's table points:

```python
class TestCurves(unittest.TestCase):
    def test_extended(self):
        self.assertEqual(DE.extended(0.5), 0.5); self.assertEqual(DE.extended(1), 1)
        self.assertEqual(DE.extended(2), 1.5); self.assertEqual(DE.extended(-1), 0)
        self.assertEqual(DE.extended(5, cap=2), 2)
    def test_wealth_concentration(self):
        for score, high, low in ((80, 1, 0), (90, 4/3, 0), (100, 5/3, 0), (20, 0, 1), (10, 0, 7/6), (0, 0, 4/3), (50, 0, 0)):
            self.assertAlmostEqual(DE.wc_high(score), high); self.assertAlmostEqual(DE.wc_low(score), low)
    def test_primacy(self):
        for p, s in ((0.25, 0), (0.5, 1), (0.6, 1.2), (0.8, 1.6), (1.0, 2)):
            self.assertAlmostEqual(DE.primacy(p), s)
    def test_metro(self):
        for share, up in ((40, 0), (60, 1), (80, 1.5), (95, 1.875)):
            self.assertAlmostEqual(DE.metro_up(share), up)
        self.assertAlmostEqual(DE.metro_down(5), 1); self.assertAlmostEqual(DE.metro_down(0), 1)
    def test_sex(self):
        for b, more in ((110, 0), (130, 1), (150, 1.5), (170, 2), (200, 2)):
            self.assertAlmostEqual(DE.more_men(b), more)
        for b, fewer in ((90, 0), (80, 1), (70, 1.5), (60, 2), (40, 2)):
            self.assertAlmostEqual(DE.fewer_men(b), fewer)
    def test_youth(self):
        self.assertAlmostEqual(DE.youth(0.24, 0.2), 1); self.assertAlmostEqual(DE.youth(0.30, 0.2), 1.5)
        self.assertAlmostEqual(DE.youth(0.36, 1.0), 2)      # 2 x 3 capped
        self.assertEqual(DE.youth(0.17, 0.5), 0)
    def test_inequality(self):
        for g, m in ((0.45, 0), (0.65, 1), (0.70, 1.25), (0.80, 2.25), (1.0, 3.75)):
            self.assertAlmostEqual(DE.inequality(g), m)
    def test_caps(self):
        self.assertEqual(DE.primacy(1.0), 2); self.assertEqual(DE.more_men(400), 2)
        self.assertEqual(DE.fewer_men(0), 2); self.assertEqual(DE.youth(1.0, 1.0), 2)
    def test_old_curves(self):
        self.assertAlmostEqual(DE.wc_high_old(80), 0.6); self.assertAlmostEqual(DE.primacy_old(0.6), 1)
        self.assertAlmostEqual(DE.more_men_old(150), 1); self.assertAlmostEqual(DE.inequality_old(0.8), 1.75)
    def test_none_is_zero(self):
        for name, (old, new) in DE.CONDITIONS.items():
            self.assertEqual(new(None), 0, name); self.assertEqual(old(None), 0, name)

class TestSizes(unittest.TestCase):
    def test_the_spec_sizes(self):
        self.assertEqual(DE.SIZES["inh_great_fortunes"], {"country_aristocrats_pol_str_mult": 0.2,
            "country_capitalists_pol_str_mult": 0.2, "country_bubble_pressure_monthly_add": 0.3})
        self.assertEqual(DE.SIZES["inh_dispersed_property"], {"state_political_strength_from_wealth_mult": -0.1,
            "state_pop_qualifications_mult": 0.1, "state_education_access_add": 0.1,
            "state_radicals_from_political_movements_mult": -0.1})
        self.assertNotIn("state_aristocrats_investment_pool_efficiency_mult", DE.SIZES["inh_dispersed_property"])
```

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_demographics_effects -v`. Expected: FAIL (no module).

- [ ] **Step 3: Implement** `scripts/analysis/demographics_effects.py` with the interface above. `SIZES` holds, at 1× (from the spec):

| Modifier | Fields |
|---|---|
| `inh_great_fortunes` | aristocrats/capitalists `pol_str` +0.2, bubble +0.3 |
| `inh_dispersed_wealth` | aristocrats/capitalists `pol_str` −0.2, bubble −0.3 |
| `inh_concentrated_property` | aristocrats/capitalists `investment_pool_efficiency` +0.2, `state_political_strength_from_wealth_mult` +0.2, qualifications −0.2, education access −0.1 |
| `inh_dispersed_property` | political strength from wealth −0.1, qualifications +0.1, education access +0.1, radicals −0.1 |
| `inh_land_hunger` | migration quota +0.3, `state_pop_support_movement_land_reform_mult` +0.25, radicals +0.1 |
| `te_demog_census_inequality` | radicals +0.1, `_socialist_mult` +0.1, `_labor_mult` +0.1 |
| `te_demog_primate_city` | urban center throughput +0.2, migration pull +0.25, `building_university_throughput_add` +0.1 |
| `te_demog_provincial_neglect` | migration pull −0.15, turmoil +0.15, `_cultural_minority_mult` +0.15 |
| `te_demog_mt_metropolis` | infrastructure from population +0.2, urban center throughput +0.1, turmoil +0.1 |
| `te_demog_mt_crowding` | crowding density −0.1 |
| `te_demog_mt_dispersed` | infrastructure from population −0.2 |
| `te_demog_census_youth_bulge` | radicals +0.25, turmoil +0.15 |
| `te_demog_census_fewer_men` | `state_pop_support_movement_feminist_mult` +0.25 |
| `te_demog_census_more_men` | radicals +0.15, turmoil +0.15 |

- [ ] **Step 4: Run** the test file. Expected: PASS. Run `.venv/bin/ruff check scripts/analysis/demographics_effects.py test_demographics_effects.py`.

- [ ] **Step 5: Commit**: "Demographics effects: the old and new curves and the new sizes in Python".

---

### Task 3: The harness readouts (Phase 0)

**Files:**
- Modify: `scripts/analysis/demographics_save_inputs.py` (`read_variables`, ~431)
- Modify: `scripts/analysis/demographics_harness.py` (`cmd_wc` ~474, `cmd_gini` ~157, new `cmd_effects`, `main` ~2477)
- Test: `test_demographics_harness.py` (extend `WC_SAVE` ~820, new class `TestEffects`)

**Interfaces:**
- Consumes: `DE.CONDITIONS`, `DE.youth`, `DE.youth_old`, `DE.SIZES` (Task 2); `census_figures(path)`, `S.state_unemployment(sections)` (existing).
- Produces: `S.read_variables(path, country_vars, state_vars, raw=())`: names in `raw` keep `identity=` as the raw string (a scope reference such as `te_dg_primate_state`); `strength_bins(pairs: list[tuple[float, float]]) -> list[tuple[str, int, float]]` (bins `0`, `0–0.5`, `0.5–1`, `1–1.5`, `1.5–2`, `>2`: label, states, people); `effects_rows(countries, states, census, idle) -> dict`; CLI `effects SAVE [--top N]`.

- [ ] **Step 1: Write the failing tests.** Extend `WC_SAVE` with state variables `te_dg_gini`, `te_dg_mt`, `te_dg_sex_balance`, `te_dg_agr_share` and the country's `te_dg_primacy` and `te_dg_primate_state` (written `type=state`, `identity=5`). Then:

`run(argv)` is a module helper: it calls `H.main(argv)` under `redirect_stdout`, asserts it returned 0, and returns the text. `path` is the extended `WC_SAVE` written in `setUp`, as `TestWealthConcentrationReader` does.

```python
class TestEffects(unittest.TestCase):
    def test_raw_variables_keep_the_reference(self):
        countries, _ = S.read_variables(self.path, ("te_dg_primate_state",), (), raw=("te_dg_primate_state",))
        self.assertEqual(countries["1"]["vars"]["te_dg_primate_state"], "5")
    def test_strength_bins(self):
        rows = H.strength_bins([(0.0, 1e6), (0.3, 2e6), (1.2, 1e6), (2.0, 5e5)])
        self.assertEqual([r[1] for r in rows], [1, 1, 0, 1, 1, 0])
    def test_wc_prints_both_curves(self):        # `wc` gains the state-score histogram, old and new
        self.assertRegex(run(["wc", path]), r"state scores.*\n.*80-90")
        self.assertIn("1-1.5", run(["wc", path]))
    def test_gini_counts_states_above_070(self):  # `gini` gains a line from te_dg_gini
        self.assertRegex(run(["gini", path]), r"above 0\.70: 1 of 2 states")
    def test_effects_prints_every_condition(self):
        text = run(["effects", path])
        for name in ("wc_high", "wc_low", "primacy", "metro_up", "inequality", "more_men", "fewer_men"):
            self.assertIn(name, text)
        self.assertIn("radicals stack", text); self.assertIn("turmoil stack", text)
        self.assertIn("primate Urban Center stack", text)
    def test_effects_skips_missing_figures(self):
        sparse = Path(self.path).with_name("sparse.v3")   # WC_SAVE with every te_dg_* but te_dg_wc removed from state 6
        sparse.write_text(WC_SAVE_SPARSE, encoding="utf-8")
        text = run(["effects", str(sparse)])
        self.assertIn("wc_high", text); self.assertIn("inequality", text)   # state 5 still reports both
```

The spec's late-primate crowding read (`migration_crowding_mult_applied`) is not a script variable `read_variables` decodes, so it moves to the play-test list (Task 9): the primate city's Migration Crowding hover in a late game decides Primate City's fade.

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_demographics_harness.TestEffects test_demographics_harness.TestWealthConcentrationReader -v`. Expected: the new tests FAIL; the existing reader tests pass.

- [ ] **Step 3: Implement.**
  - `read_variables(..., raw=())`.
  - `cmd_wc` appends a histogram of state scores (deciles) and, from `te_dg_wc` weighted by `te_dg_walk_pop`, `strength_bins` under `wc_high_old`/`wc_high` and `wc_low_old`/`wc_low`.
  - `cmd_gini` appends `above 0.70: N of M states (P% of people)` from `te_dg_gini` via `read_variables`.
  - `cmd_effects` reads the variables above plus `census_figures` (youth share, sex balance) and `S.state_unemployment`, then prints, for each condition, one row per bin: old states/people against new. The national pair comes from each country's `te_inh_concentration`, weighted by its states' people.
  - The radicals stack per state at the new sizes (Land Hunger × `te_dg_agr_share`, Dispersed Property, Inequality, the Youth Bulge, More Men), worst ten.
  - The turmoil stack, worst ten: Provincial Neglect on a primate country's other states, Metropolis, the Youth Bulge, More Men.
  - Each primate country's Urban Center stack, Primate City plus Metropolis on `te_dg_primate_state`.
  - A figure a state lacks drops that state from that condition only.
  - Wire the `effects` parser in `main` beside `wc`.

- [ ] **Step 4: Run** the same tests. Expected: PASS. Run `.venv/bin/ruff check scripts/analysis test_demographics_harness.py`.

- [ ] **Step 5: Commit**: "Demographics harness: the effects readout, and wc and gini against the new curves".

---

### Task 4: Wealth Concentration (every rule setting)

**Files:**
- Modify: `common/static_modifiers/te_inheritance_modifiers.txt` (24-61 and the header comment 10-21)
- Modify: `common/script_values/te_inheritance_values.txt` (99-144)
- Modify: `localization/english/te_concepts_l_english.yml` (`concept_inheritance_concentration_desc` 817; `inh_concentrated_property_desc` 1583, `inh_dispersed_property_desc` 1586, `inh_dispersed_wealth_desc` 1588, `inh_great_fortunes_desc` 1594, `inh_land_hunger_desc` 1596)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`TE_STATE_WEALTH_TT` 1051, `TE_STATE_WEALTH_ROW_SCORE_TT` 1049, `te_demog_st_wc_tt` 7040, `te_demog_wc_line_tt` 7218, `te_nation_how_wc` 7518)
- Modify: `localization/english/te_modifiers_l_english.yml` (add `state_pop_support_movement_land_reform_mult_desc`; vanilla has only the name)
- Modify: `docs/player_guide/06-politics.md` (372-384), `docs/player_guide/17-reference.md` (132), `docs/player_guide/04-banking.md` (113), `docs/systems/mod_systems.md` (1558, 1564)
- Test: `test_demographics_registry.py` (`TestWealthStateModifiers` 5438, new class `TestWealthSizes`)

**Interfaces:**
- Consumes: `DE.SIZES`, `DE.wc_high`, `DE.wc_low`, `DE.WC_SPAN`.
- Produces: script values `te_inh_k_wc_span` (30), `te_inh_dispersed_reach`, `te_inh_wc_low_reach`; `te_inh_great_fortunes_mult_value`, `te_inh_dispersed_mult_value`, `te_inh_wc_high_mult_value`, `te_inh_wc_low_mult_value` and `te_inh_land_hunger_mult_value` keep their names.

- [ ] **Step 1: Write the failing tests** in `test_demographics_registry.py`:
  - `TestWealthStateModifiers.test_the_state_modifiers_follow_the_states_own_score`: new cases `(80,0.5)→(1.0,None,0.5)`, `(100,1.0)→(5/3,None,5/3)`, `(100,0.0)→(5/3,None,None)`, `(50,0.8)→none`, `(50.2,0.8)→none`, `(20,0.8)→(None,1.0,None)`, `(10,0.8)→(None,7/6,None)`, `(0,0.3)→(None,4/3,None)`, each checked against `DE.wc_high`/`DE.wc_low`.
  - New `TestWealthSizes`:
    - `test_each_modifier_is_the_spec`: for the five `inh_*` modifiers, the parsed fields equal `DE.SIZES[name]`.
    - `test_bubble_pressure_only_on_the_national_pair`: `country_bubble_pressure_monthly_add` appears in `inh_great_fortunes` and `inh_dispersed_wealth` and in no state modifier.
    - `test_the_national_pair_follows_the_curve`: evaluate `te_inh_great_fortunes_mult_value` and `te_inh_dispersed_mult_value` with the file's existing script-value evaluator at 80, 100, 20 and 0 against `DE.wc_high`/`DE.wc_low`.
    - `test_dispersed_side_has_no_investment_line`.

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_demographics_registry.TestWealthStateModifiers test_demographics_registry.TestWealthSizes -v`. Expected: FAIL.

- [ ] **Step 3: Implement the script values.** `te_inh_k_wc_span = { value = 30 }`. The high side (national and state) is straight: `value = <score> subtract = 50 divide = te_inh_k_wc_span min = 0` (no `max`). The low side uses a reach plus the extended pattern (Global Constraints), giving 4/3 at 0. `te_inh_land_hunger_mult_value` = the high side × `var:te_dg_agr_share`, `min = 0`, no `max`. Update the comments that state "(score − 50) / 50".

- [ ] **Step 4: Implement the modifiers** to `DE.SIZES` (Task 2's table), rewriting each block's comment: capture, capital formation, financial stability, mobility and schooling, land hunger. Each comment is one line with the spec's citation (Kumhof, Rancière and Winant; Galor, Moav and Vollrath).

- [ ] **Step 5: Localization.**
  - `inh_*_desc`: what each now does, with no figures (the engine tooltip shows them) and "full at 80"/"full at 20, and more beyond" in place of "grows with the distance from 50".
  - The concept's second paragraph: concentration speeds investment and inflates bubbles; dispersal steadies the financial cycle and opens schooling.
  - `TE_STATE_WEALTH_ROW_SCORE_TT`: "full at 80 or 20, and stronger beyond".
  - `te_demog_wc_line_tt`: both the Aristocrats and the Capitalists lose strength below 50, and bubble pressure moves.
  - Add `state_pop_support_movement_land_reform_mult_desc`.
  - Run `python3 organize_loc.py`.

- [ ] **Step 6: Player guide and docs.**
  - `06-politics.md`: the table's header becomes "Effect at 80 (or 20)", with the new rows, a Great Fortunes / Dispersed Wealth sentence naming bubble pressure, and "a state at 65 gets half; past 80 the effects keep growing" in place of the 75 sentence.
  - `17-reference.md:132`: the same in a line.
  - `04-banking.md:113`: add that Great Family Fortunes adds up to 0.5 bubble pressure a month and Dispersed Wealth takes up to 0.4 off.
  - `mod_systems.md` § Inheritance (1558, 1564): the new formulas and sizes, pointing to the spec.

- [ ] **Step 7: Run** the Step 2 tests plus `test_demographics_wc_shocks test_hidden_state_modifiers test_nation_tab`, then `python3 scripts/generators/gen_nation_tab.py --check`, `python3 scripts/analysis/check_player_guide_style.py --strict`, `python3 organize_loc.py --check` and `python3 scripts/format_paradox_tabs.py --check common/static_modifiers/te_inheritance_modifiers.txt common/script_values/te_inheritance_values.txt`. Expected: all PASS (if `gen_nation_tab --check` fails, run the generator and include its output).

- [ ] **Step 8: Commit**: "Wealth Concentration: concentration grows faster but crashes more often, dispersal slower but steadier".

---

### Task 5: Inequality (Full only)

**Files:**
- Modify: `common/static_modifiers/te_demog_inequality_modifiers.txt` (10-13 and its header)
- Modify: `common/scripted_effects/te_demog_wealth_effects.txt` (`te_demog_inequality_refresh` 607-640, line 630)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`te_demog_census_inequality_desc` 6224)
- Modify: `docs/player_guide/08-states.md` (337-339), `docs/systems/mod_systems.md` (1716-1719)
- Test: `test_demographics_wc_shocks.py` (`TestInequality` 578)

**Interfaces:**
- Consumes: `DE.inequality`, `DE.SIZES["te_demog_census_inequality"]`.

- [ ] **Step 1: Update the tests in `TestInequality`.**
  - `test_from_045_on_with_no_cap`: Gini 0.30, 0.45 and 0.452 → none; 0.50 → 0.25; 0.65 → 1.0; 0.70 → 1.25; 0.80 → 2.25; 1.0 → 3.75, each also equal to `DE.inequality(g)`.
  - `test_no_max_on_the_multiplier`: pins the new `value = { … }` string (below).
  - `test_the_modifier`: the parsed fields equal `DE.SIZES["te_demog_census_inequality"]`.

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_demographics_wc_shocks.TestInequality -v`. Expected: FAIL.

- [ ] **Step 3: Implement.** Line 630 becomes `set_variable = { name = te_dg_ineq value = { value = var:te_dg_gini subtract = 0.45 multiply = 5 min = 0 add = { value = var:te_dg_gini subtract = 0.70 multiply = 5 min = 0 } } }`. The modifier gains `state_pop_support_movement_socialist_mult = 0.1` and `state_pop_support_movement_labor_mult = 0.1`; the header comment and 607-619 say the slope doubles above 0.70.

- [ ] **Step 4: Loc and docs.**
  - `te_demog_census_inequality_desc`: "…10% more at 0.65, and twice as fast above 0.70; it also lifts support for socialist and labor movements".
  - `08-states.md` 337-339 and `mod_systems.md` 1718: the same.
  - Run `organize_loc.py`.

- [ ] **Step 5: Run** the Step 2 tests plus `test_hidden_state_modifiers`, the style lint and `organize_loc.py --check`. Expected: PASS.

- [ ] **Step 6: Commit**: "Inequality: twice as steep above a Gini of 0.70, and socialist and labor support".

---

### Task 6: The urban pattern (Full only)

**Files:**
- Modify: `common/static_modifiers/te_demog_place_modifiers.txt` (10-21)
- Modify: `common/script_values/te_demog_place_values.txt` (13-34 constants and strength, 93-109 shown values, 123-126 AI constant)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`te_demog_primate_city_desc` 6779, `te_demog_provincial_neglect_desc` 6781, `te_demog_up_eff_display` 7111, `te_demog_up_eff_none` 7113, `te_demog_up_eff_on` 7114, `te_demog_up_eff_primate_named` 7116, `te_demog_up_eff_primate_plain` 7117)
- Modify: `docs/player_guide/08-states.md` (493-509, 547-550), `docs/systems/mod_systems.md` (1852-1863)
- Test: `test_demographics_place.py`

**Interfaces:**
- Consumes: `DE.primacy`, `DE.SIZES["te_demog_primate_city"]`, `DE.SIZES["te_demog_provincial_neglect"]`.
- Produces: `te_demog_up_reach` (the ramp, `min = 0`); `te_demog_up_strength` (extended, `max = 2`, stored in `te_dg_up_s` as before); constants `te_demog_k_up_university = 0.1`, `te_demog_k_up_rest_minority = 0.15`; shown values `te_demog_up_shown_university`, `te_demog_up_shown_rest_minority`.

- [ ] **Step 1: Update the tests in `test_demographics_place.py`.**
  - `test_strength_is_linear_from_the_dominant_floor_to_sixty_percent` (80): rename to `test_strength_follows_the_extended_curve`, asserting the evaluated `te_demog_up_strength` equals `DE.primacy(p)` for p in (0.25, 0.4, 0.5, 0.6, 0.8, 1.0).
  - `test_every_effect_is_small` (216): rename to `test_every_effect_is_at_most_a_quarter`, bound `abs(size) <= 0.25`.
  - `TestModifiers.test_the_fields_are_the_values`: also the fields equal `DE.SIZES[...]`.
  - `test_the_ai_rule` (265, the bound at 272): `ai_strength` = 0.7, the bound `(0.4 - floor) / span`, and a new assertion that `floor + ai_strength × span` = 0.425 (the AI's threshold doesn't move).

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_demographics_place -v`. Expected: FAIL.

- [ ] **Step 3: Implement.**
  - Constants: `te_demog_k_up_span` 0.25, `_uc` 0.2, `_pull` 0.25, `_rest_pull` −0.15, `_rest_turmoil` 0.15, plus the two new ones; `te_demog_k_pc_ai_strength` 0.7, with its comment saying 42.5% primacy (the old comment's "45%" was off).
  - `te_demog_up_strength`: the reach, then the extended pattern with `max = 2`.
  - Modifiers to `DE.SIZES`.
  - The two new shown values follow the existing ones (`te_demog_up_shown_s × k`).

- [ ] **Step 4: Loc and docs.**
  - "from 25% to 60%" becomes "full at 50%, and stronger beyond" in the descs and `te_demog_up_eff_*`.
  - The primate rows add University throughput (`te_demog_up_shown_university`) and the neglect row adds Cultural Minority support, spliced through the vanilla modifier names.
  - `08-states.md` 504-506 sizes, 548 "Primate pattern of 42.5%"; `mod_systems.md` 1856-1857 and 1861.
  - Run `organize_loc.py`.

- [ ] **Step 5: Run** the Step 2 tests, `test_hidden_state_modifiers`, `python3 scripts/analysis/check_gui_lint.py`, the style lint and `organize_loc.py --check`. Expected: PASS.

- [ ] **Step 6: Commit**: "Urban pattern: full at 50% primacy and stronger beyond; universities in the great city, minority movements in the provinces".

---

### Task 7: The metropolitan share (Full only)

**Files:**
- Modify: `scripts/analysis/demographics_params.py` (1289-1300: `MT_EFFECTS`, `MT_DISPERSED_EFFECTS`, new `MT_CROWDING`)
- Modify: `scripts/analysis/demographics_metro.py` (`concentrated` 112, `effects` 123; new `concentrated_strength`)
- Modify: `common/static_modifiers/te_demog_metro_modifiers.txt` (header 1-7, 17-30; new `te_demog_mt_crowding`)
- Modify: `common/script_values/te_demog_metro_values.txt` (57-61 constants; after 323 the new reach and strength; 385-410 shown values)
- Modify: `common/scripted_effects/te_demog_metro_effects.txt` (`te_demog_mt_state_refresh` 49-80)
- Modify: `common/script_values/gui_chart_script_values.txt` (`gui_state_hidden_modifier_count` ~125: a `has_modifier = te_demog_mt_crowding` term)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`te_demog_mt_metropolis_desc` 6593, `te_demog_mt_dispersed_desc` 6583, `te_demog_mt_eff_metro` 6586, `te_demog_mt_eff_dispersed` 6584, `te_demog_mt_eff_display` 6585, `te_demog_mt_eff_none` 6587; new `te_demog_mt_crowding`, `te_demog_mt_crowding_desc`)
- Modify: `docs/player_guide/08-states.md` (511-526), `docs/systems/mod_systems.md` (1864-1873)
- Test: `test_demographics_metro.py`

**Interfaces:**
- Consumes: `DE.metro_up`, `DE.SIZES["te_demog_mt_metropolis"]`, `DE.SIZES["te_demog_mt_crowding"]`, `DE.SIZES["te_demog_mt_dispersed"]`.
- Produces:
  - Params: `P.MT_EFFECTS` (three fields at 1×), `P.MT_CROWDING = {"state_migration_crowding_density_mult": -0.10}`, `P.MT_DISPERSED_EFFECTS = {"state_infrastructure_from_population_mult": -0.20}`.
  - Python: `DMT.concentrated_strength(share) -> float` (extended, equal to `DE.metro_up`).
  - Script values `te_demog_mt_up_reach` and `te_demog_mt_e_pos_strength`; the variable `te_dg_mt_crowd_mult`.
  - The hidden state modifier `te_demog_mt_crowding` (icon `modifier_system.dds`).

- [ ] **Step 1: Update the tests in `test_demographics_metro.py`.**
  - `PINNED` (43-64): map `te_demog_k_mt_crowding` to `P.MT_CROWDING[...]` and the others to the new `P.MT_EFFECTS`.
  - `TestRefresh` (288-328): at share 60 the state carries `{"te_demog_mt_metropolis": DMT.concentrated_strength(60), "te_demog_mt_crowding": DMT.concentrated(60)}`; at 80, 1.5 and 1.0.
  - New `test_both_go_outside_full`: the refresh removes both before its Full gate.
  - `TestModifiers` (359-369): `_modifier("te_demog_mt_metropolis") == P.MT_EFFECTS == DE.SIZES[...]` and `_modifier("te_demog_mt_crowding") == P.MT_CROWDING`.
  - `test_every_effect_is_within_a_tenth` (371): rename to `test_every_effect_is_within_a_fifth` (≤ 0.20).
  - `test_every_field_is_an_engine_modifier` and `test_every_field_has_a_name` cover all three modifiers.
  - `TestFertility` stays as is (it guards the 0–1 ramp).

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_demographics_metro test_hidden_state_modifiers -v`. Expected: FAIL.

- [ ] **Step 3: Implement.**
  - Params and the Python twin.
  - Constants: `_infra_up` 0.2, `_services` 0.1, `_turmoil` 0.1, `_infra_down` −0.2; `_crowding` stays −0.1.
  - `te_demog_mt_up_reach` is `(var:te_dg_mt − from) / (full − from)`, `min = 0` (no max); `te_demog_mt_e_pos_strength` is its extended form (no cap: the share's ceiling is 95).
  - `te_demog_mt_metropolis` loses its crowding field; `te_demog_mt_crowding` carries it with `modifier_system.dds` and a header comment: "a model term: it feeds the share's target, so it keeps the 0–1 strength".
  - The refresh removes both, then under the same gate sets `te_dg_mt_mult = te_demog_mt_e_pos_strength` and `te_dg_mt_crowd_mult = te_demog_mt_e_pos` and adds both.
  - The shown values for infrastructure, services and turmoil read `te_demog_mt_e_pos_strength`; crowding keeps `te_demog_mt_e_pos`.
  - Add the hidden count term.

- [ ] **Step 4: Loc and docs.**
  - "from nothing at 40% to its full size at 60%" becomes "full at 60%, and stronger beyond".
  - Dispersed: −20% infrastructure.
  - Name the new modifier "Metropolitan Crowding", whose desc says it is part of the share's balance.
  - `08-states.md` 522-526, `mod_systems.md` 1866 (drop "at most 10%") and 1869-1870.
  - Run `organize_loc.py`.

- [ ] **Step 5: Run** the Step 2 tests plus `test_nation_tab`, `gen_nation_tab.py --check`, the style lint and `organize_loc.py --check`. Expected: PASS.

- [ ] **Step 6: Commit**: "Metropolitan share: Metropolis twice as strong and rising past 60; crowding keeps its balance".

---

### Task 8: Sex balance and the youth bulge (Full only)

**Files:**
- Modify: `scripts/analysis/demographics_params.py` (333-365: `YOUTH_RADICALS` 0.25, `YOUTH_TURMOIL` 0.15, `SEX_MORE_FULL` 130, `SEX_FEMINIST` 0.25, `SEX_RADICALS` 0.15, new `SEX_MORE_TURMOIL = 0.15`, new `EFFECT_CAP = 2.0`)
- Regenerate: `common/script_values/te_demog_generated_values.txt` (`python3 scripts/generators/gen_demographics.py`: `te_demog_k_sex_more_span` 40 → 20)
- Modify: `scripts/analysis/demographics_model.py` (new `sex_fewer_men_strength`, `sex_more_men_strength`; `youth_bulge` 734 takes the extended factors and the cap)
- Modify: `common/static_modifiers/te_demog_consequence_modifiers.txt` (24-40)
- Modify: `common/script_values/te_demog_consequence_values.txt` (after 76 the reaches and strengths; `te_demog_youth_bulge_now` 212-224; shown 283-300, new `te_demog_sex_turmoil_shown`)
- Modify: `common/scripted_effects/te_demog_consequence_effects.txt` (`te_demog_consequences_apply` 77-99: the two sex multipliers)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`te_demog_census_fewer_men_desc` 6222, `te_demog_census_more_men_desc` 6226, `te_demog_census_youth_bulge_desc` 6236, `te_demog_sex_rule` 6857, `te_demog_st_sex_more` 7017, `te_demog_ov_sex_more` 6686, `te_demog_youth_effects` 7277, `te_demog_youth_rule` 7279)
- Modify: `docs/player_guide/08-states.md` (327-335), `docs/systems/mod_systems.md` (1908-1909)
- Test: `test_demographics_registry.py` (`TestConsequencesScript` 7465), `test_demographics_harness.py` (the `consequences` anchors 1281-1284 if they move)

**Interfaces:**
- Consumes: `DE.fewer_men`, `DE.more_men`, `DE.youth`, `DE.SIZES[...]` for the three `te_demog_census_*` modifiers.
- Produces:
  - Model functions `M.sex_fewer_men_strength(balance)` and `M.sex_more_men_strength(balance)`, equal to `DE.fewer_men` / `DE.more_men` while `P.SEX_BALANCE_EFFECTS`.
  - `M.youth_bulge(share, unemployment)`, now extended and capped, equal to `DE.youth`.
  - Script values `te_demog_sex_fewer_men_reach`, `te_demog_sex_more_men_reach`, `te_demog_sex_fewer_men_strength` and `te_demog_sex_more_men_strength` (each `max = 2`); `te_demog_youth_share_factor` and `te_demog_youth_idle_factor` (each extended).
  - `te_demog_sex_fewer_men` and `te_demog_sex_more_men` keep their 0–1 ramps.

- [ ] **Step 1: Update the tests in `TestConsequencesScript`.**
  - The multiplier comparisons (7481-7522) use `M.sex_fewer_men_strength`, `M.sex_more_men_strength` and `M.youth_applied(M.youth_bulge(...))` at balances 60, 70, 80, 130, 150 and 170, and youth (0.30, 0.2) and (0.36, 1.0).
  - Each is also equal to the `DE` function.
  - `test_the_sizes_are_the_params` (7678) gains `SEX_MORE_TURMOIL` and `te_demog_sex_turmoil_shown`.
  - Each modifier's fields equal `DE.SIZES[...]`.
  - New `test_the_model_ramps_stay_on_0_1`: `te_demog_sex_fewer_men` still has `max = 1` and `M.sex_women_add(60) == P.SEX_WOMEN_RATE`.

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_demographics_registry.TestConsequencesScript test_gen_demographics -v`. Expected: FAIL.

- [ ] **Step 3: Implement.**
  - Params, then `python3 scripts/generators/gen_demographics.py`.
  - The model functions.
  - Script: each reach keeps its ramp's guards (no balance, or the effects switch off → 0); each strength is extended with `max = 2`.
  - `te_demog_youth_bulge_now` = `te_demog_youth_share_factor × te_demog_youth_idle_factor`, `max = 2`.
  - `te_demog_consequences_apply` multiplies the Fewer Men and More Men modifiers by the strengths, with the `> 0` gates reading the strengths.
  - Modifiers to `DE.SIZES`.
  - The shown values read the strengths with the new sizes, plus `te_demog_sex_turmoil_shown`.

- [ ] **Step 4: Loc and docs.**
  - The descs and the rule text: "full at 80"/"full at 130", with "stronger beyond, up to twice"; the youth bulge at "25%" and "15%".
  - `te_demog_st_sex_more` and `te_demog_ov_sex_more` add the turmoil line through `te_demog_sex_turmoil_shown`.
  - `08-states.md` 327-335, `mod_systems.md` 1908-1909.
  - Run `organize_loc.py`.

- [ ] **Step 5: Run** the Step 2 tests plus `test_demographics_harness.TestConsequences`, `test_hidden_state_modifiers`, `test_nation_tab`, the style lint and `organize_loc.py --check`. Expected: PASS.

- [ ] **Step 6: Commit**: "Sex balance and the youth bulge: stronger, rising past their reference, and More Men brings turmoil".

---

### Task 9: Docs, play-test list, the full gate and the PR

**Files:**
- Modify: `docs/superpowers/specs/2026-10-08-demographics-design.md` (design rule 5 at 137 and the §7 table: a pointer to the new spec)
- Modify: `docs/testing/demographics-playtest.md` (a new section, "Stronger demographic effects (2026-10-22)")
- Modify: `docs/superpowers/README.md` (the spec's row: status, plan link)
- Regenerate: `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`

- [ ] **Step 1: Docs.**
  - Rule 5: "Revised 2026-10-22: a strong condition is worth about one vanilla law on its main effect; see `2026-10-22-demographic-effects-impact-design.md`".
  - The README row: built, Phase 0's save readouts pending, and the plan linked.
  - The play-test section, from the spec's list:
    - the tooltips show the new figures;
    - a score past 80 still moves the modifiers;
    - Land Reform support in a land-hungry state with the movement present, and the field's description reads right;
    - Fewer Men's support after a great war;
    - the bubble line in the Banking dashboard's next-month range;
    - Metropolitan Crowding stays out of the state's rows but shows in Migration Crowding's breakdown;
    - the primate city's Migration Crowding hover in a late game, for Primate City's fade;
    - an observer run to about 1950.

- [ ] **Step 2: Rebuild the guide**: `.venv/bin/python scripts/build_player_guide.py`, then `python3 scripts/build_player_guide.py --check`. Expected: no staleness.

- [ ] **Step 3: The full gate**, with the dummy `VIC3_*` variables from CLAUDE.md:
  - `.venv/bin/python -m unittest discover -s . -p 'test_*.py' > /tmp/…/suite.txt 2>&1; grep -E '^(Ran |OK|FAILED)'`
  - `.venv/bin/ruff check .`
  - `python3 -m compileall -q scripts`
  - `python3 scripts/format_paradox_tabs.py --check` on every changed `.txt`
  - `python3 scripts/analysis/check_localization_files.py`, `python3 organize_loc.py --check`
  - `python3 loc_coverage_audit.py --strict`, `python3 modifier_multiplier_var_audit.py --strict`, `python3 duplicate_key_audit.py --strict`, `python3 script_argument_audit.py --strict`
  - the BOM check: exactly one BOM on every changed `.txt` and `.yml`
  - Expected: OK everywhere.

- [ ] **Step 4: Commit** the docs, guide sources and PDF.

- [ ] **Step 5: Open the PR** to `main` (push the branch `demog-effects-impact`):
  - The body lists the five areas.
  - It includes Task 1's simulator table and the spec's tests for when a size moves.
  - It asks the owner for plain-text saves at about 1836, 1880, 1936 and a late year, to run `wc`, `gini` and `effects`.
  - It has a "Player guide: 04-banking, 06-politics, 08-states, 17-reference" line.
  - It ends with the attribution lines.
  - Verify the body landed (`gh pr view --json body`).
