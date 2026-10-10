# Demographics Gini by wealth band: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The census's Gini measures the game's own income distribution: pops are grouped by wealth band, not by stratum, and the panel shows the grouped figure with no map. Wealth Concentration's inequality term is set afresh on the new figures: +30 × (Gini − 0.15), at most +15.

**Architecture:** The yearly pop walk adds each pop's people and stand-in income to one of 14 wealth bands (the income knots: wealth 1 or less, 2–5, 6–10, …, 56–60, 61 or more) instead of one of three strata. Each state stores its 28 sums, and the country adds its states' sums. One generated formula takes the Gini over the 14 ordered bands. Bands follow income because the stand-in rises with wealth, so the formula needs no sort, unlike today's three strata. The panel shows that figure, clamped to 0–0.9. `GINI_FLOOR` (0.30, chosen) and `GINI_SCALE` (0.85, fitted to a historical 0.52) go.

**Tech Stack:** Python 3.11/3.12 (unittest), Paradox script, `scripts/generators/gen_demographics.py`.

**Spec:** `docs/superpowers/specs/2026-10-08-demographics-design.md` §4.1 (the Gini) and §4.2 (Wealth Concentration's inequality term). Evidence: the offline check of 2026-10-10 (14 saves, 1836–1953), archived at `/mnt/d/vic3te-data/gini-check-2026-10-10/`, written up in Task 6's results doc.

## Owner rulings this plan builds on (2026-10-10)

- The Gini should measure the game's distribution, not history's. The stand-in income (spending per head at the pop's wealth) is right: in Britain 1836, aristocrats earn about 139× laborers per head in the engine; the stand-in gives 115×.
- Wealth bands with no map, if they are not expensive. Per pop they add one short chain of wealth comparisons to a walk that already makes dozens of reads; the Gini needs no sort; each state keeps 28 sums instead of 6.
- Wealth Concentration moves with it, as a follow-up to stage 2: evaluated fresh, not fitted to the old values; 30 × (Gini − 0.15), a shallow bottom, rounded for players.

## The evidence (the offline check)

- Today's panel figure (0.30 + 0.85 × the strata Gini) reads above the game's pop-by-pop Gini in 99% of country-saves, by +0.19 on average. Britain 1877: shown 0.776, pop-by-pop 0.659. Britain 1836: 0.36, not 0.52.
- The 14 wealth bands reproduce the pop-by-pop Gini with no map: mean −0.014, R² 0.98, worst miss 0.045 for countries; mean −0.008, R² 0.99 for states.
- The script's country figure sums its states' groups and then takes one Gini, and the check mirrored that; it matched the game's logged figures to a mean difference of 0.0004.

## Wealth Concentration's inequality term (owner, 2026-10-10)

Today: +50 × (the state's Gini − 0.40), capped ±15. The owner asked for a fresh evaluation, not a fit to the old values
(the system is unreleased). The new term is **+30 × (Gini − 0.15), capped at +15**, rounded for players: +3 points
for every 0.1 of Gini above 0.15.

- **Centre 0.15**, on 1836's measured median state (0.15–0.16, people-weighted), as the ownership term is centred on
  1836's measured private share. The 1836 world starts near 0 on this term; the differences come from play.
- **The cap at a Gini of 0.65**, Britain's industrial peak in the runs (0.63–0.65 in 1877–1887), the most unequal
  great power they produce.
- **A shallow bottom:** a Gini is at least 0, so the term is at least −4.5. Equal incomes stop fortunes growing but
  don't break existing ones up; that is the inheritance laws' and the taxes' work (their own terms).

| Gini (state or country) | 1836 median 0.15–0.16 | France 1836 0.19 | Britain 1836 0.35 | Median 1887 0.24 | Median 1953 0.28 | Russia 1953 0.40 | France 1953 0.55 | Britain 1877 0.65 | 0 |
|---|---|---|---|---|---|---|---|---|---|
| Term | +0.3 | +1.2 | +6 | +2.7 | +3.9 | +7.5 | +12 | +15 | −4.5 |

## Global Constraints

- Never hand-edit `te_demog_generated_effects.txt` or `te_demog_generated_values.txt`: edit `gen_demographics.py` or the params and regenerate.
- Brace-based files: tabs, exactly one UTF-8 BOM; `scripts/format_paradox_tabs.py` on hand-edited `.txt`.
- Script values are i64 × 1e-5: turn sums into shares before multiplying them (as today's formula does).
- No PEP 701 f-strings (CI runs 3.11). Venv `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`; the dummy `VIC3_*` env vars from CLAUDE.md for the suite.

## Review Focus

1. **A save from before this change.** States hold the old six strata sums and none of the 28 band sums until their own yearly pulse. A country census on 31 December must add only states that have band sums (`has_variable = te_dg_gn1`), and a state's walk removes the old six. Pinned in Task 3.
2. **Wealth at the edges:** 0, 1, a knot (5, 60), just past one (6, 61), and far above the cap (99). Each lands in exactly one band, the one `M.wealth_band` names. Pinned in Task 2.
3. **No people or no income** (an empty state, a state of 0-wealth pops): the Gini is 0, not a division error. Pinned in Task 2.
4. **Everyone in one band:** the Gini is 0. Pinned in Task 2.
5. **Large countries:** China's people (~4 × 10⁸) × income per head stays inside i64 × 1e-5, and shares keep their precision: the formula divides each band's sums by the totals before it multiplies. Pinned by the interpreter test with `truncate=True` on a China-sized country in Task 3.

---

### Task 1: The bands in the model and the params

**Files:**
- Modify: `scripts/analysis/demographics_params.py` (§4.1 block), `scripts/analysis/demographics_model.py` (`shown_gini`, new `wealth_band`), `scripts/generators/gen_demographics.py` (the constants block at ~885: drop `gini_floor`, `gini_scale`)
- Test: `test_demographics_model.py` (`TestInequality`)

**Interfaces:**
- Produces: `P.GINI_BAND_KNOTS` (the 13 knots: 1, 5, 10, …, 60), `P.GINI_BANDS = 14`; `M.wealth_band(wealth) -> int` (1–14); `M.shown_gini(grouped) -> float` = `clamp(grouped, 0, 0.9)`.

- [ ] **Step 1: Failing tests.** In `TestInequality` replace the Britain-0.52 anchor test with:

```python
    def test_the_panel_shows_the_grouped_figure(self):
        self.assertEqual(M.shown_gini(0.36), 0.36)
        self.assertEqual(M.shown_gini(0.95), 0.9)
        self.assertEqual(M.shown_gini(-0.01), 0.0)

    def test_wealth_bands_follow_the_income_knots(self):
        # Review Focus 2: each wealth lands in one band; the knots are each band's top
        cases = {0: 1, 1: 1, 2: 2, 5: 2, 6: 3, 10: 3, 11: 4, 55: 12, 56: 13, 60: 13, 61: 14, 99: 14}
        for wealth, band in cases.items():
            self.assertEqual(M.wealth_band(wealth), band, wealth)
        self.assertEqual(P.GINI_BANDS, len(P.GINI_BAND_KNOTS) + 1)
```

- [ ] **Step 2:** run `TestInequality`; expected AttributeError (`wealth_band`, `GINI_BANDS`) and the shown-figure failure.
- [ ] **Step 3: Params.** Replace `GINI_FLOOR` and `GINI_SCALE` (and their comment) with:

```python
# The Gini (§4.1) groups pops by wealth band: the income stand-in's knots are each band's top
# (wealth 1 or less, 2-5, 6-10, ..., 56-60, 61 or more). Income rises with wealth, so the bands
# are in income order and the grouped Gini needs no sort. The panel shows it as it is: the game's
# own distribution, not history's (owner, 2026-10-10; the check: docs/testing/
# demographics-gini-check-2026-10-10.md). Mean -0.014 against pop by pop, R^2 0.98.
GINI_BAND_KNOTS = (1, *range(5, INCOME_WEALTH_CAP + 1, 5))
GINI_BANDS = len(GINI_BAND_KNOTS) + 1
```

- [ ] **Step 4: Model.** `shown_gini` returns `clamp(grouped, 0.0, 0.9)` with docstring "The panel's Gini: the grouped figure over wealth bands (§4.1), clamped." Add:

```python
def wealth_band(wealth):
    """The Gini's band (1..GINI_BANDS) for a pop's wealth: the first knot at or above it."""
    for i, knot in enumerate(P.GINI_BAND_KNOTS, start=1):
        if wealth <= knot:
            return i
    return P.GINI_BANDS
```

In `gen_demographics.py`'s constants block drop the `"gini_floor"` and `"gini_scale"` entries; `INCOME_KNOTS` there becomes `P.GINI_BAND_KNOTS` if they are the same set (assert it).
- [ ] **Step 5:** run `test_demographics_model`; then `grep -rn 'GINI_FLOOR\|GINI_SCALE\|te_demog_k_gini' --include=*.py --include=*.txt .` lists what Tasks 2–5 still change.
- [ ] **Step 6:** commit "Demographics Gini: wealth bands in the model; no map".

### Task 2: The generated band effects and formula

**Files:**
- Modify: `scripts/generators/gen_demographics.py` (new `gini_bands(o)` in `render_effects`)
- Regenerate: `common/scripted_effects/te_demog_generated_effects.txt`, `common/script_values/te_demog_generated_values.txt` (the two constants go)
- Test: `test_demographics_registry.py` (new `TestGiniBands`)

**Interfaces:**
- Produces (scripted effects, all generated):
  - `te_demog_gini_band_init`: the walk's 28 locals `te_dg_w_gn<k>`, `te_dg_w_gy<k>` = 0.
  - `te_demog_gini_band_add` (pop scope): adds `total_size` and `te_demog_pop_income` to band `M.wealth_band(wealth)`'s locals, by a split-in-half chain of `wealth > knot` tests (four tests a pop).
  - `te_demog_gini_band_store` (state): `te_dg_gn<k>`, `te_dg_gy<k>` from the walk's locals; removes an old save's `te_dg_n_lo/_mi/_up`, `te_dg_y_lo/_mi/_up`.
  - `te_demog_gini_band_load` (state): locals `te_dg_g_n<k>`, `te_dg_g_y<k>` from the state's sums.
  - `te_demog_gini_band_zero` (country): those locals = 0.
  - `te_demog_gini_band_add_state` (a state, in the country's loop): adds the state's sums to the locals.
  - `te_demog_gini_from_locals`: G = 1 − Σ p_k (S_k + S_{k−1}) over the 14 bands in order; writes `var:te_dg_gini` clamped 0–0.9. Replaces the hand-written one in `te_demog_wealth_effects.txt` (Task 3 deletes it).

- [ ] **Step 1: Failing tests** (`test_demographics_registry.py`):

```python
class TestGiniBands(unittest.TestCase):
    """The generated wealth-band effects (§4.1, wealth bands): each pop's band, and the formula."""

    def band_of(self, wealth):
        eng = _Engine({"wealth": float(wealth), "total_size": 10.0, "te_demog_pop_income": 3.0})
        eng.call("te_demog_gini_band_init")
        eng.call("te_demog_gini_band_add")
        hit = [k for k in range(1, P.GINI_BANDS + 1) if eng.locals[f"te_dg_w_gn{k}"]]
        self.assertEqual(len(hit), 1, wealth)
        self.assertEqual(eng.locals[f"te_dg_w_gy{hit[0]}"], 3.0)
        return hit[0]

    def test_every_wealth_lands_in_the_models_band(self):
        # Review Focus 2
        for wealth in range(0, 100):
            self.assertEqual(self.band_of(wealth), demographics_model.wealth_band(wealth), wealth)

    def gini(self, bands, truncate=False):
        eng = _Engine({}, truncate=truncate)
        for k in range(1, P.GINI_BANDS + 1):
            n, y = bands.get(k, (0.0, 0.0))
            eng.locals[f"te_dg_g_n{k}"], eng.locals[f"te_dg_g_y{k}"] = float(n), float(y)
        eng.call("te_demog_gini_from_locals")
        return eng.vars["te_dg_gini"]

    def test_the_formula_matches_the_model(self):
        rng = random.Random(11)
        for _ in range(200):
            bands, per_head = {}, 0.0
            for k in range(1, P.GINI_BANDS + 1):
                per_head += rng.uniform(0.0, 30.0)          # bands follow income
                n = rng.choice([0, rng.randint(1, 200000)])
                bands[k] = (n, n * per_head)
            want = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
            self.assertAlmostEqual(self.gini(bands), want, places=9)

    def test_nobody_or_no_income_or_one_band_is_zero(self):
        # Review Focus 3 and 4
        self.assertEqual(self.gini({}), 0.0)
        self.assertEqual(self.gini({1: (500, 0), 2: (20, 0)}), 0.0)
        self.assertAlmostEqual(self.gini({7: (1000, 4321)}), 0.0, places=9)

    def test_the_constants_of_the_old_map_are_gone(self):
        self.assertNotIn("te_demog_k_gini", _text(GENERATED_VALUES))
```

- [ ] **Step 2:** run `TestGiniBands`; expected KeyError/AssertionError on the missing effects.
- [ ] **Step 3: Generator.** Add to `gen_demographics.py` and call it from `render_effects` after `country_bands(o)`:

```python
def gini_bands(o):
    """§4.1's Gini over wealth bands: the walk's sums, a state's store, the country's sum, the formula."""
    knots, n = P.GINI_BAND_KNOTS, P.GINI_BANDS
    o("# THIS = a state, before its pop walk: the Gini's wealth-band sums (§4.1).")
    o("te_demog_gini_band_init = {")
    for k in range(1, n + 1):
        o(f"set_local_variable = {{ name = te_dg_w_gn{k} value = 0 }}")
        o(f"set_local_variable = {{ name = te_dg_w_gy{k} value = 0 }}")
    o("}")
    o("")

    def chain(lo, hi):
        if lo == hi:
            o(f"change_local_variable = {{ name = te_dg_w_gn{lo} add = total_size }}")
            o(f"change_local_variable = {{ name = te_dg_w_gy{lo} add = te_demog_pop_income }}")
            return
        mid = (lo + hi) // 2      # bands lo..mid hold wealth up to knots[mid - 1]
        o("if = {")
        o(f"limit = {{ wealth > {knots[mid - 1]} }}")
        chain(mid + 1, hi)
        o("}")
        o("else = {")
        chain(lo, mid)
        o("}")

    o("# THIS = a pop in the walk: its people and stand-in income into its wealth band. The knots are")
    o(f"# each band's top ({', '.join(map(str, knots))}; above {knots[-1]} income is capped), split in")
    o("# halves, so a pop takes four tests.")
    o("te_demog_gini_band_add = {")
    chain(1, n)
    o("}")
    o("")
    o("# THIS = a state, after its walk: keep the bands for the country's sum. An old save's strata")
    o("# sums (before the wealth bands, 2026-10-10) are removed.")
    o("te_demog_gini_band_store = {")
    for k in range(1, n + 1):
        o(f"set_variable = {{ name = te_dg_gn{k} value = local_var:te_dg_w_gn{k} }}")
        o(f"set_variable = {{ name = te_dg_gy{k} value = local_var:te_dg_w_gy{k} }}")
    o("if = {")
    o("limit = { has_variable = te_dg_n_lo }")
    for name in ("n_lo", "n_mi", "n_up", "y_lo", "y_mi", "y_up"):
        o(f"remove_variable = te_dg_{name}")
    o("}")
    o("}")
    o("")
    o("# THIS = a state: its bands into the formula's locals.")
    o("te_demog_gini_band_load = {")
    for k in range(1, n + 1):
        o(f"set_local_variable = {{ name = te_dg_g_n{k} value = var:te_dg_gn{k} }}")
        o(f"set_local_variable = {{ name = te_dg_g_y{k} value = var:te_dg_gy{k} }}")
    o("}")
    o("")
    o("# THIS = a country, before its states add their bands.")
    o("te_demog_gini_band_zero = {")
    for k in range(1, n + 1):
        o(f"set_local_variable = {{ name = te_dg_g_n{k} value = 0 }}")
        o(f"set_local_variable = {{ name = te_dg_g_y{k} value = 0 }}")
    o("}")
    o("")
    o("# THIS = a state in its country's loop: add its bands (the caller checks it has them).")
    o("te_demog_gini_band_add_state = {")
    for k in range(1, n + 1):
        o(f"change_local_variable = {{ name = te_dg_g_n{k} add = var:te_dg_gn{k} }}")
        o(f"change_local_variable = {{ name = te_dg_g_y{k} add = var:te_dg_gy{k} }}")
    o("}")
    o("")
    o("# THIS = a state or a country, with its bands in te_dg_g_n<k> and te_dg_g_y<k> (a country's summed")
    o("# over its states, so its Gini is taken over all their people, not averaged). The bands are in")
    o("# income order, so G = 1 - sum p_k (S_k + S_k-1), with p_k a band's share of people and S_k the")
    o("# running share of income. Each sum becomes a share before it multiplies (values are i64 x 1e-5).")
    o("# With no people or no income the Gini is 0. Writes var:te_dg_gini, the panel's figure, 0-0.9.")
    o("te_demog_gini_from_locals = {")
    o("set_local_variable = { name = te_dg_g_pop value = 0 }")
    o("set_local_variable = { name = te_dg_g_inc value = 0 }")
    for k in range(1, n + 1):
        o(f"change_local_variable = {{ name = te_dg_g_pop add = local_var:te_dg_g_n{k} }}")
        o(f"change_local_variable = {{ name = te_dg_g_inc add = local_var:te_dg_g_y{k} }}")
    o("set_local_variable = { name = te_dg_g_gini value = 0 }")
    o("if = {")
    o("limit = {")
    o("local_var:te_dg_g_pop > 0")
    o("local_var:te_dg_g_inc > 0")
    o("}")
    o("set_local_variable = { name = te_dg_g_gini value = 1 }")
    o("set_local_variable = { name = te_dg_g_s value = 0 }")
    for k in range(1, n + 1):
        o(f"set_local_variable = {{ name = te_dg_g_s2 value = {{ value = local_var:te_dg_g_y{k} "
          "divide = local_var:te_dg_g_inc add = local_var:te_dg_g_s } }")
        o(f"set_local_variable = {{ name = te_dg_g_t value = {{ value = local_var:te_dg_g_n{k} "
          "divide = local_var:te_dg_g_pop multiply = { value = local_var:te_dg_g_s2 add = local_var:te_dg_g_s } } }")
        o("change_local_variable = { name = te_dg_g_gini subtract = local_var:te_dg_g_t }")
        o("set_local_variable = { name = te_dg_g_s value = local_var:te_dg_g_s2 }")
    o("}")
    o("set_variable = { name = te_dg_gini value = { value = local_var:te_dg_g_gini min = 0 max = 0.9 } }")
    o("}")
    o("")
```

Run the generator.
- [ ] **Step 4:** run `TestGiniBands`, `test_gen_demographics`; expected OK. A generated `te_demog_gini_from_locals` now sits beside the hand-written one: the hand-written file still defines it until Task 3, and `_raw_blocks` keeps the later file's (check which wins in `_Engine` and in the game — duplicate scripted effects are dropped: `Duplicated key ... will not be created`). If the duplicate shadows the generated one in tests, do Task 3's deletion in this commit.
- [ ] **Step 5:** commit "Demographics Gini: the generated wealth-band effects and formula".

### Task 3: The walk, the state and the country use the bands

**Files:**
- Modify: `common/scripted_effects/te_demog_effects.txt` (the walk: strata locals and branches → `te_demog_gini_band_init` / `_add` / `_store`), `common/scripted_effects/te_demog_wealth_effects.txt` (`te_demog_state_gini` → `te_demog_gini_band_load`; delete the hand-written `te_demog_gini_from_locals`; `te_demog_wc_national`: `te_demog_gini_band_zero`, and per scored state `if = { limit = { has_variable = te_dg_gn1 } te_demog_gini_band_add_state = yes }`; comments naming strata), and `te_demog_effects.txt`'s variable list at the top (te_dg_n_*/te_dg_y_* → te_dg_gn<k>/te_dg_gy<k>)
- Test: `test_demographics_registry.py` (`TestStateGini` rewritten on `_Engine`; the national test's `scored()` takes bands; a new old-save test)

**Reviewer (one, after this task):** the walk's band chain runs in pop scope inside `every_scope_pop` with the walk's locals (as the strata branches did); every reader of the old six variables is gone; the country loop's guard; the per-state sums' magnitude for a large country.

- [ ] **Step 1: Failing tests.** Rewrite `TestStateGini` to set `te_dg_gn<k>`/`te_dg_gy<k>` on a state, call `te_demog_state_gini` through `_Engine`, and compare with `M.shown_gini(M.grouped_gini(bands))` on random monotone bands; change `scored()` in the Wealth Concentration tests to take `bands={k: (n, y)}` and the national Gini expectation to the summed bands. Add:

```python
    def test_a_state_from_an_old_save_adds_no_bands(self):
        # Review Focus 1: before its own pulse a state has only the old strata sums
        old = self.scored(60, 55)
        for k in range(1, P.GINI_BANDS + 1):
            old.pop(f"te_dg_gn{k}"), old.pop(f"te_dg_gy{k}")
        old.update(te_dg_n_lo=900.0, te_dg_y_lo=1350.0)
        new = self.scored(40, 50, bands={2: (900e3, 1.2e6), 9: (1e4, 2e5)})
        v = self.national([old, new])
        want = demographics_model.shown_gini(demographics_model.grouped_gini([(900e3, 1.2e6), (1e4, 2e5)]))
        self.assertAlmostEqual(v["te_dg_gini"], want, places=9)

    def test_a_china_sized_country_keeps_its_precision(self):
        # Review Focus 5: 4e8 people at up to ~900 a head, with the engine's fixed point
        bands = {2: (3.2e8, 3.2e8 * 2.0), 6: (6e7, 6e7 * 9.0), 12: (2e7, 2e7 * 300.0), 14: (1e6, 1e6 * 945.0)}
        state = self.scored(50, 50, bands=bands)
        eng = _CountryEngine(states=[state], effects=APPLIED, truncate=True, fixtures={...same as national...})
        eng.call("te_demog_wc_national")
        want = demographics_model.shown_gini(demographics_model.grouped_gini(list(bands.values())))
        self.assertAlmostEqual(eng.vars["te_dg_gini"], want, places=3)
```

And in the walk text test: the walk calls the three generated effects and no longer tests `strata =`.
- [ ] **Step 2:** run the registry's Gini and Wealth Concentration tests; expected failures.
- [ ] **Step 3: The edits** listed under Files. In the walk, `te_demog_gini_band_init = yes` replaces the six `te_dg_w_n*/y*` locals, `te_demog_gini_band_add = yes` replaces the three strata branches inside `every_scope_pop`, and `te_demog_gini_band_store = yes` replaces the six `set_variable` lines after it.
- [ ] **Step 4:** tabs, BOM, run the five demographics test files; expected OK.
- [ ] **Step 5:** commit "Demographics Gini: the walk, states and countries sum wealth bands".

### Task 4: Wealth Concentration's inequality term

**Files:**
- Modify: `common/script_values/te_demog_values.txt` (`te_demog_wc_inequality_term`), `localization/english/te_miscellaneous_l_english.yml` (`te_demog_wc_t_ineq_tt`)
- Test: `test_demographics_registry.py` (the target tests at ~1873–1897 and the national test's `mean(5, -5)`)

- [ ] **Step 1: Failing tests.** Update the expectations: `(0.5 − 0.15) × 30 = 10.5` in `test_the_target_sums_its_terms` (target 95.5, and 85.5 with econ −10); in the caps test, `two_thirds` takes Gini 0.15 for "no term", `state_owned` (Gini 0) gives 50 − 20 − 4.5; the national test's inequality bar is `mean(10.5, 4.5)`.
- [ ] **Step 2:** run them; expected failures.
- [ ] **Step 3:** the term:

```
# State scope: the inequality term. The rich save more, so fortunes grow from unequal
# incomes: +30 x (the state's Gini - 0.15), so +3 for every 0.1 above 0.15, at most 15 (from a
# Gini of 0.65, Britain's industrial peak in the observer runs) and at least -4.5 (a Gini is at
# least 0: equal incomes stop fortunes growing, the inheritance laws and taxes break them up).
# Centred on 1836's measured median state with the wealth-band Gini (owner, 2026-10-10).
te_demog_wc_inequality_term = {
	value = var:te_dg_gini
	subtract = 0.15
	multiply = 30
	min = -15
	max = 15
}
```

and the tooltip: `"#b Income Inequality#!\nThe rich save more, so unequal incomes build fortunes: +3 for every 0.1 of the state's Gini above 0.15, at most +15 (a Gini of 0.65); below 0.15 it takes up to 4.5 off."`
- [ ] **Step 4:** tests, loc check, commit "Demographics: Wealth Concentration's inequality term re-centred for the wealth-band Gini".

### Task 5: The harness and the observer report

**Files:**
- Modify: `scripts/analysis/demographics_harness.py` (`country_groups` → by band; `cmd_gini` prints per country the band Gini (the panel's figure), the pop-by-pop Gini and today's strata figure, with no anchor or scale), `scripts/analysis/demographics_observer_report.py` (the GBR 1836 Gini anchor "about 0.5 (owner check 4)" becomes "about 0.36, the game's own (wealth bands, 2026-10-10)" with its band 0.3–0.45)
- Test: `test_demographics_harness.py` (`test_gini_on_the_slice`, `test_gini_exits_1_when_the_anchor_tag_has_no_pops` → `..._when_the_tag_has_no_pops`)

- [ ] **Step 1: Failing tests.** `test_gini_on_the_slice`: the output has a GBR line with three figures in 0–1 and the band figure within 0.05 of the pop-by-pop one; no `GINI_SCALE`. The no-pops test passes `--tag XXX` and expects exit 1.
- [ ] **Step 2:** run them; expected failures.
- [ ] **Step 3:** implement: `band_groups(pops, costs)` returns `[(people, income)]` by `M.wealth_band`; `pop_groups` one group per pop; `cmd_gini` prints `TAG  bands 0.xxx  pop-by-pop 0.xxx  strata-map (old) 0.xxx`, exit 1 when a requested tag has no pops. Drop `--anchor`/`--anchor-tag`.
- [ ] **Step 4:** tests; commit "Demographics harness: the Gini by wealth band, beside pop by pop".

### Task 6: Loc, docs and the results doc

Built by the controller.

- Loc (`te_miscellaneous_l_english.yml`): `te_demog_gini_tt`, `te_demog_how_gini`, `te_demog_how_gini_state`, `te_demog_ov_gini_tt`, `te_demog_states_head_gini_tt` say "how unequally income is spread over the people, grouped by wealth" instead of "over the lower, middle and upper strata", and "Britain in 1836 stands at about 0.52" becomes "about 0.36".
- `docs/testing/demographics-gini-check-2026-10-10.md`: the check (data, method, the tables, the fitted maps, the bands' fit, `weekly_budget`, caveats), from the archived report.
- Parent spec §4.1 (the measure: wealth bands, no map; Britain 1836 0.36 is the game's own) and §4.2's table row (the new term); `docs/systems/mod_systems.md` (the inequality bullet at ~1431, the Gini paragraph at ~1439, the gate item at ~1465, the walk's variables at ~1416); `docs/guides/python_tools.md` (the harness's `gini`).
- Player guide: it states no Gini figure or formula, so no change; the PR says so.
- Commit "Demographics Gini by wealth band: loc, docs and the check's results".

### Task 7: Verify, review, draft PR

- Full suite, ruff, tabs, BOMs, `organize_loc --check`, `check_localization_files`, the strict audits (`loc_coverage`, `duplicate_key`, `empty_effect`, `script_argument`, `script_loc_reference`, `loc_render`), `check_post_load_rosters`.
- Whole-branch review (one fresh reviewer).
- Push, draft PR to `main`. In-game checks:
  1. No error naming `te_demog_gini_*` or the generated files on load.
  2. A new 1836 game: Britain's Gini on the Demographics tab about 0.36, France about 0.20; Wealth Concentration's Income Inequality bar near 0 for most countries, as before.
  3. An old save loads; on 31 December the country Gini is computed (states not yet pulsed are left out that year); a pulsed state has no `te_dg_n_lo`.
  4. No visible slowdown at the yearly pulses in a large late-game save.
  The inequality term is the owner's (30 × (G − 0.15), 2026-10-10).
