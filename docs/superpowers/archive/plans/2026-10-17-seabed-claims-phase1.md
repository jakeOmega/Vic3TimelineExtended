# Seabed Claims, Phase 1 (claim rules and the Seabed panel) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Seabed tab answer the owner's four questions in plain words, and add the claim rules behind them: a holding fee after a year's grace, Sponsor Contractors' protection and scaled cost, a five-year policy lock, relinquishing claims, and the "+1 licence" readout.

**Architecture:** Every rule goes into the Python model `scripts/analysis/seabed_model.py` first, with random-world invariants in `test_seabed_allocation.py`. The Paradox script then mirrors the model function by function (each effect names its model function, `ModelNamesTest` holds that), and `test_seabed_script.py` pins names, constants and call order. The panel (`gui/te_seabed_widgets.gui`) reads guarded `*_disp_*` script values through `GetPlayer.MakeScope`, as today.

**Tech Stack:** Victoria 3 Paradox script (`common/`), `.gui`, localization YAML, Python 3.11/3.12 `unittest`.

**Spec:** `docs/superpowers/archive/specs/2026-10-17-seabed-claims-and-panel-design.md` (§§ 1–3, 9), building on `docs/superpowers/archive/specs/2026-10-16-global-commons-design.md` §§ 2–3.

## Global Constraints

- Model first: no script task starts before its model task's tests pass. Every new `te_seabed_*` name a model docstring mentions must exist in script (`ModelNamesTest`).
- State lives in variables, never only in modifiers or lists (a revolution's winner inherits variables only). Each modifier has exactly one refresh site.
- Values (spec): floor keeps `0.75` of claims; fee rate `0.02` of a level's base output value a week; grace = unbuilt at both of the last two first-sharings-of-a-year; policy lock `60` months; Sponsor influence `50 + 0.5` per protected claim, uncapped; Unilateral `1.5 ×` Sponsor's figure, at least `150`; a defector is a party again `60` months after it defected.
- "The year's first sharing" means the sharing that finds `global_var:te_seabed_pass_year` below `te_history_current_year` (or absent): January, or the first mid-year one in a year with no January pass.
- No player-facing string contains "recorded" or "record" (spec § 1). Variable and effect names keep "records".
- Words: **licence** (held by a built or queued level), **claim** (unused share), **share** (licences + claims).
- Panel text sizes: rows 17, subheadings 20, overview 16 (`docs/guides/gui_style_guide.md` rule 3); no cell elides ("…") or overflows.
- Brace-based `.txt` and `.gui` files: tabs, exactly one UTF-8 BOM. Run `python3 scripts/format_paradox_tabs.py <files>` after large edits.
- Loc: add keys to `localization/english/te_miscellaneous_l_english.yml` (concept `_desc` keys to `te_concepts_l_english.yml`), then `python3 organize_loc.py` and commit everything it moves.
- Python must run on 3.11: no PEP 701 f-strings (`grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>`).
- Work in a sparse worktree; never `POST /reload` from it. Per task run that task's tests plus `ruff`; CI runs the full suite.

## Review Focus

1. **A country leaves the sharing while it holds stored floors** (loses its last coast or the technology): its floors and claims must go with it, or a dead floor keeps licences out of the pool. Test: Task 1 `test_a_non_participant_keeps_no_floor`.
2. **Old saves and a revolution's winner** have none of the new variables (no floors, no snapshots, no lock date): no floor, no fee in the first year, unlocked. Test: Task 1 `test_missing_floor_is_no_floor`, Task 3 `test_no_snapshots_no_fee`, Task 8 `test_no_change_date_is_unlocked`.
3. **A conquered state with queued levels**: its snapshots travel with it; the fee base never exceeds the licences on its unbuilt levels and is never negative. Test: Task 3 `test_fee_base_bounds_under_conquest`.
4. **Floors that don't fit** (grandfathered over-pool holdings, Antarctic bar, a Scramble): holdings untouched, protected parts scaled down, no pool exceeded. Test: Task 1 `test_floors_scale_down_to_fit` and the random-world invariant.
5. **Relinquish then Claim Again around a sharing**: never leaves the country ahead of not relinquishing. Test: Task 2 `test_relinquish_never_pays`.

---

### Task 1: Model — Sponsor floors

**Files:**
- Modify: `scripts/analysis/seabed_model.py`
- Test: `test_seabed_allocation.py` (new class `FloorTest`; extend `PoolsHoldTest._check`)

**Interfaces:**
- Produces: constant `FLOOR_KEEP = 0.75`; `Country.floor: dict` (basin → share-level floor, 0 = none; script `te_seabed_floor_<b>`); `set_floors(world: World, cid) -> None` (`te_seabed_set_floors`); `fit_floors(world: World, b: str, part: list) -> dict` (`te_seabed_fit_floors`, returns cid → frozen-at amount); `yearly_pass(world, *, first_of_year: bool = True)`.

- [ ] **Step 1: Write the failing tests** (add `import math` to the file's imports)

```python
class FloorTest(unittest.TestCase):
    def _one_basin_world(self, policy=m.SPONSOR):
        # two claimants on the Pacific; country 0 on `policy`
        w = m.World({0: m.Country(0, policy=policy, navy=10), 1: m.Country(1, policy=m.SPONSOR, navy=10)},
                    {0: m.State(0, "pacific", 0), 1: m.State(1, "pacific", 1)})
        m.yearly_pass(w)
        return w

    def test_sponsor_claims_fade_by_a_quarter_at_most(self):
        w = self._one_basin_world()
        before = w.countries[0].unbuilt["pacific"]            # 150
        w.countries[1].navy = 1000                            # a rival's buildup
        m.yearly_pass(w)
        self.assertGreaterEqual(w.countries[0].unbuilt["pacific"], math.floor(0.75 * before))

    def test_survey_claims_are_fully_re_divided(self):
        w = self._one_basin_world(policy=m.SURVEY)
        w.countries[1].navy = 1000
        m.yearly_pass(w)
        self.assertLess(w.countries[0].unbuilt["pacific"], 10)

    def test_mid_year_sharing_honours_the_stored_floor(self):
        w = self._one_basin_world()
        w.countries[1].navy = 1000
        m.yearly_pass(w)                                      # floor fixed: 112
        kept = w.countries[0].unbuilt["pacific"]
        m.yearly_pass(w, first_of_year=False)
        self.assertEqual(w.countries[0].unbuilt["pacific"], kept)   # no 0.75 × 0.75

    def test_scramble_voids_floors(self):
        w = self._one_basin_world()
        w.regime = m.SCRAMBLE
        w.countries[1].navy = 1000
        m.yearly_pass(w)
        self.assertLess(w.countries[0].unbuilt["pacific"], 10)

    def test_barred_southern_floor_is_holdings(self): ...
        # country 0 Sponsor with Southern claims, then barred=True: unbuilt["southern"] == 0 after the pass

    def test_floors_scale_down_to_fit(self):
        # grandfather 280 Pacific licences on country 1 (State.lic), country 0 Sponsor with floor 150 → after the pass
        # sum(ent) <= max(pool, sum(held)) and country 1's ent >= its held
        ...

    def test_a_non_participant_keeps_no_floor(self):
        w = self._one_basin_world()
        w.countries[0].tech = False
        m.yearly_pass(w)
        self.assertEqual(w.countries[0].floor["pacific"], 0)
        self.assertEqual(w.countries[0].unbuilt["pacific"], 0)

    def test_missing_floor_is_no_floor(self):
        w = self._one_basin_world()
        w.countries[0].floor = dict.fromkeys(m.BASINS, 0)      # an old save
        w.countries[1].navy = 1000
        m.yearly_pass(w, first_of_year=False)
        self.assertLess(w.countries[0].unbuilt["pacific"], 10)
```

Fill in the two `...` bodies as their comments say. In `PoolsHoldTest._check` keep every existing assertion; the random worlds already mix policies, so floors are exercised.

- [ ] **Step 2: Run, expect failures**

Run: `.venv/bin/python -m unittest test_seabed_allocation.FloorTest -v` — Expected: errors (`yearly_pass() got an unexpected keyword argument 'first_of_year'`, no `floor`).

- [ ] **Step 3: Implement in `seabed_model.py`**

- `set_floors(world, cid)`: called for every participant at the year's first sharing, after recording and held, before weights. If the country is on `SPONSOR` and `world.regime != SCRAMBLE`: `floor[b] = held[b] + floor(FLOOR_KEEP * unbuilt[b])` for each basin, except `floor["southern"] = held["southern"]` when `barred`. Otherwise all 0.
- Mid-year (`first_of_year=False`): floors as stored, but treated as 0 for a country no longer on Sponsor or when the regime is Scramble.
- `fit_floors(world, b, part)`: `h'[cid] = max(held, floor)`. If `sum(h') > max(POOLS[b], sum(held))`, scale every protected part `h' − held` by one factor, rounding down. Returns `h'`.
- `share_basin` freezes on `h'` (from `fit_floors`) instead of `held`; a frozen country's entitlement is its `h'`. `unbuilt = ent − held` as now.
- Step 7 of `yearly_pass` (non-participants) also zeroes `floor`.
- Update the module docstring: a "FLOORS" paragraph naming `te_seabed_set_floors`, `te_seabed_fit_floors`, `te_seabed_floor_<basin>` and the first-sharing rule.

- [ ] **Step 4: Run the whole file**

Run: `.venv/bin/python -m unittest test_seabed_allocation -v 2>&1 | grep -E '^(Ran |OK|FAILED)'` — Expected: `OK`.

- [ ] **Step 5: Commit** — `git add scripts/analysis/seabed_model.py test_seabed_allocation.py && git commit -m "Seabed model: Sponsor Contractors' floors"`

### Task 2: Model — relinquishing claims

**Files:** Modify `scripts/analysis/seabed_model.py`; Test `test_seabed_allocation.py` (class `RelinquishTest`)

**Interfaces:**
- Consumes: Task 1's `floor`, `yearly_pass(first_of_year=)`.
- Produces: `Country.relinquished: dict` (basin → bool; script `te_seabed_relinq_<b>`); `relinquish(world, cid, b) -> None` (`te_seabed_relinquish`); `claim_again(world, cid, b) -> None` (`te_seabed_claim_again`).

- [ ] **Step 1: Write the failing tests**

```python
class RelinquishTest(unittest.TestCase):
    def test_relinquish_drops_claims_now_and_keeps_licences(self):
        # country 0 with 3 Pacific licences recorded and claims > 0
        ...
        m.relinquish(w, 0, "pacific")
        self.assertEqual(w.countries[0].unbuilt["pacific"], 0)
        self.assertEqual(w.basin_records("pacific"), 3)
        self.assertEqual(w.countries[0].floor["pacific"], 0)

    def test_no_weight_until_claim_again(self):
        ...
        m.relinquish(w, 0, "pacific"); m.yearly_pass(w)
        self.assertEqual(w.countries[0].weight["pacific"], 0)
        self.assertEqual(w.countries[0].ent["pacific"], w.countries[0].held["pacific"])
        m.claim_again(w, 0, "pacific"); m.yearly_pass(w)
        self.assertGreater(w.countries[0].weight["pacific"], 0)

    def test_relinquish_never_pays(self):
        # 200 random worlds: deep-copy the world, relinquish then claim_again in one copy
        # between two passes; after the second pass the relinquisher's
        # sum(ent) is <= the untouched copy's. Drive each copy's months with its own
        # random.Random seeded alike, so the copies differ only by the relinquishing.
        ...
```

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_seabed_allocation.RelinquishTest -v` — Expected: `AttributeError: module 'seabed_model' has no attribute 'relinquish'`.

- [ ] **Step 3: Implement** `relinquish` (claims to 0, `relinquished[b] = True`, `floor[b] = 0`; does **not** trigger a sharing), `claim_again` (`relinquished[b] = False`), and in `compute_weights` a relinquished basin's weight is 0. Docstring line naming `te_seabed_relinquish` / `te_seabed_claim_again` and that relinquishing never sets `te_seabed_reshare` (spec § 2.5).

- [ ] **Step 4: Run the file** — Expected: `OK`.

- [ ] **Step 5: Commit** — `"Seabed model: relinquishing claims"`

### Task 3: Model — holding fee base with a year's grace

**Files:** Modify `scripts/analysis/seabed_model.py`; Test `test_seabed_allocation.py` (class `FeeTest`)

**Interfaces:**
- Produces: `State.snap1: int = 0`, `State.snap2: int = 0` (script `te_seabed_unb_snap1/2`); `State.built` property (`levels − queued`); `take_snapshots(world) -> None` (`te_seabed_take_snapshots`, run at the year's first sharing after recording); `fee_base_state(s) -> int` and `fee_base(world, cid) -> int` (`te_seabed_fee_base`); `queued_by_basin(world, cid) -> dict` (basin → licences held by the country's queued levels; script `te_seabed_queued_<b>`, written by the monthly recording).

- [ ] **Step 1: Write the failing tests**

```python
class FeeTest(unittest.TestCase):
    def test_grace_then_fee(self):
        s = m.State(0, "pacific", 0, levels=4, queued=4); s.lic["pacific"] = 4
        w = m.World({0: m.Country(0)}, {0: s})
        self.assertEqual(m.fee_base(w, 0), 0)                 # no snapshots
        m.take_snapshots(w); self.assertEqual(m.fee_base(w, 0), 0)   # one January
        m.take_snapshots(w); self.assertEqual(m.fee_base(w, 0), 4)   # two Januaries
        s.queued = 1                                           # three finished
        self.assertEqual(m.fee_base(w, 0), 1)

    def test_no_snapshots_no_fee(self): ...               # old save: fee_base == 0 whatever is queued

    def test_queued_by_basin(self):
        # an Atlantic state with 5 levels, 2 queued, licences atlantic 3 + arctic 2:
        # the 2 queued count against the distant (Arctic) licences first
        s = m.State(0, "atlantic", 0, levels=5, queued=2); s.lic["atlantic"] = 3; s.lic["arctic"] = 2
        w = m.World({0: m.Country(0)}, {0: s})
        self.assertEqual(m.queued_by_basin(w, 0), {**dict.fromkeys(m.BASINS, 0), "arctic": 2})
        s.queued = 4                                           # then the state's own basin
        self.assertEqual(m.queued_by_basin(w, 0)["atlantic"], 2)
        # random worlds: sum over basins == sum over states of min(queued, records), every month
        ...

    def test_fee_base_bounds_under_conquest(self):
        # random worlds (annex and split on), take_snapshots at each pass:
        # 0 <= fee_base_state(s) <= s.records() - s.built for every coastal state, every month
        ...
```

- [ ] **Step 2: Run** `... FeeTest -v` — Expected: AttributeError.
- [ ] **Step 3: Implement**: `fee_base_state(s) = max(0, min(s.records() - s.built, s.snap1, s.snap2))`; `take_snapshots`: for every coastal state `snap2 = snap1; snap1 = max(0, records − built)`. `yearly_pass(first_of_year=True)` calls it after recording, before held. A split's new state starts at 0 and 0 (the dataclass defaults).

In script (Task 7) the call sits in `te_seabed_yearly_pass` between `te_seabed_record_country` and `te_seabed_compute_held`; Task 7 adds `"te_seabed_take_snapshots"` to `FloorScriptTest.test_pass_order`'s list there.
- [ ] **Step 4: Run the file** — `OK`.
- [ ] **Step 5: Commit** — `"Seabed model: holding fee base with a year's grace"`

### Task 4: Model — the "+1 licence" readout

**Files:** Modify `scripts/analysis/seabed_model.py`; Test `test_seabed_allocation.py` (class `ReadoutTest`)

**Interfaces:**
- Consumes: Task 1's `share_basin` with floors.
- Produces: `World.final: dict` (basin → `{"rem_res", "rem_open", "wsum_res", "wsum_all", "active": set, "frozen_at": dict}`, written by `share_basin` after its loop); `need_weight(world, b, cid) -> float | None` (`te_seabed_readout`, None = "full"); `need_navy(world, cid, b) -> int | None`; `exact_need_weight(world, b, cid) -> float | None` (test-only reference: bisection on the country's weight, re-running `share_basin` on a deep copy, to 0.01).

- [ ] **Step 1: Write the failing tests**

```python
class ReadoutTest(unittest.TestCase):
    def test_closed_form_matches_exact_in_open_worlds(self):
        rng = random.Random(77)
        for _ in range(40):
            w = m.random_world(rng, regime=m.OPEN)
            m.yearly_pass(w)
            for cid, c in w.countries.items():
                for b in m.BASINS:
                    if c.weight[b] <= 0:
                        continue
                    exact, closed = m.exact_need_weight(w, b, cid), m.need_weight(w, b, cid)
                    if exact is None:
                        self.assertIsNone(closed); continue
                    # the closed form ignores largest-remainder rounding, which can
                    # hand the licence over sooner: it may overstate, never understate
                    self.assertGreaterEqual(closed - exact, -0.01, (cid, b))
                    self.assertLessEqual(closed - exact, max(0.25 * exact, 1.0), (cid, b))

    def test_full_basin_reads_none(self): ...               # a pool fully held: need_weight is None

    def test_navy_conversion(self):
        # home basin, 1 of 2 coastal states there, Sponsor, navy multiplier 1:
        # need_navy == ceil(need_weight / (1.0 * 1 * 1/2)); distant: ceil(need_weight / (0.05 * 1.0 * 1))
        ...
```

- [ ] **Step 2: Run** `... ReadoutTest -v` — Expected: AttributeError.
- [ ] **Step 3: Implement.** Active country: `t = ent + 1`, `Δw = (t·W − R·w) / (R − t)` on the open half (`R = rem_open`, `W = wsum_all`); an eligible party also on the reserved half, keeping the smaller; `None` when `R − t ≤ 0`; clamp at 0. Frozen country: `t = frozen_at + 1`, with `R + frozen_at` and `W + w`. `need_navy`: home `ceil(Δw / (factor × navy mult × n_b / N))`, distant `ceil(Δw / (DISTANT_NAVY_SHARE × factor × navy mult))`; `None` passes through.
- [ ] **Step 4: Run the file** — `OK`.
- [ ] **Step 5: Commit** — `"Seabed model: the +1 licence readout"`

### Task 5: Script — floors in the sharing

**Files:**
- Modify: `common/scripted_effects/te_global_commons_seabed_effects.txt` (`te_seabed_yearly_pass`, `te_seabed_share_basin`, `te_seabed_share_freeze`, `te_seabed_share_round`, `te_seabed_clear_share`, `te_seabed_cap_check`), `common/script_values/te_global_commons_seabed_values.txt`, `common/scripted_triggers/te_global_commons_seabed_triggers.txt`
- Test: `test_seabed_script.py` (new class `FloorScriptTest`; `ConstantsTest`; `YearlyPassOrderTest.test_order`)

**Interfaces:**
- Consumes: Task 1's model names.
- Produces: trigger `te_seabed_first_sharing_of_year` (no scope; true before `te_seabed_yearly_pass` sets `te_seabed_pass_year`; the pass caches it as global flag `te_seabed_first_of_year` for its own steps); effect `te_seabed_set_floors` (country); effect `te_seabed_fit_floors = { B = <basin> }` (no scope) writing country var `te_seabed_fz_<b>` (frozen-at amount); value `te_seabed_floor_keep = 0.75`.

- [ ] **Step 1: Write the failing tests**

```python
class FloorScriptTest(unittest.TestCase):
    def test_constant(self):
        self.assertEqual(literal(read(VALUES), "te_seabed_floor_keep"), m.FLOOR_KEEP)

    def test_pass_order(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        order = ["te_seabed_first_of_year", "te_seabed_record_country",
                 "te_seabed_compute_held", "te_seabed_set_floors", "te_seabed_compute_weights",
                 "te_seabed_fit_floors = { B = pacific }", "te_seabed_share_basin = { B = pacific }"]
        at = [body.index(s) for s in order]
        self.assertEqual(at, sorted(at))

    def test_freeze_reads_the_floor(self):
        share = strip_comments(block(read(EFFECTS), "te_seabed_share_basin"))
        self.assertIn("var:te_seabed_fz_$B$ >= var:te_seabed_e_$B$", share)
        self.assertNotIn("var:te_seabed_held_$B$ >= var:te_seabed_e_$B$", share)

    def test_scramble_and_bar(self):
        floors = strip_comments(block(read(EFFECTS), "te_seabed_set_floors"))
        self.assertIn("te_seabed_regime_scramble", floors)
        self.assertIn("te_seabed_southern_barred", floors)

    def test_clear_share_clears_the_floor(self):
        self.assertIn("te_seabed_floor_$B$", block(read(EFFECTS), "te_seabed_clear_share"))
```

Update `YearlyPassOrderTest.test_order` to include the two floor steps. (Task 7 adds `te_seabed_take_snapshots` between recording and held, and extends this order test.)

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_seabed_script -v 2>&1 | grep -E '^(Ran |OK|FAILED)'` — Expected: `FAILED`.
- [ ] **Step 3: Implement** to the model (Task 1): `te_seabed_set_floors` writes `te_seabed_floor_<b>`; `te_seabed_fit_floors` writes `te_seabed_fz_<b>` = max(held, floor), scaled when they don't fit; `te_seabed_share_freeze` and `te_seabed_share_round` use `te_seabed_fz_$B$` where they used `te_seabed_held_$B$` for the frozen amount (unbuilt stays `ent − held`); a mid-year pass reads stored floors but treats them as 0 off Sponsor or in a Scramble. Extend `te_seabed_cap_check` with a once-a-game `TE_SELF_CHECK OK|BROKEN seabed_floor_fits` (BROKEN when any basin's entitlements exceed `max(pool, Σ held)` after a sharing with floors). Each new effect's comment names its model function.
- [ ] **Step 4: Run** `test_seabed_script` and `test_seabed_allocation` — `OK`. Run `python3 scripts/format_paradox_tabs.py --check` on the changed files.
- [ ] **Step 5: Commit** — `"Seabed: Sponsor floors in the sharing"`

### Task 6: Script — Relinquish and Claim Again

**Files:**
- Modify: `common/scripted_effects/te_global_commons_seabed_effects.txt` (`te_seabed_weight_set`), `common/scripted_guis/te_global_commons_seabed_sguis.txt`, `localization/english/te_miscellaneous_l_english.yml`
- Test: `test_seabed_script.py` (class `RelinquishScriptTest`)

**Interfaces:**
- Produces: effects `te_seabed_relinquish = { B = <basin> }`, `te_seabed_claim_again = { B = <basin> }` (country); scripted GUIs `te_seabed_relinquish_<b>_sgui` and `te_seabed_claim_again_<b>_sgui` (5 each; scope country; `ai_is_valid = { always = no }`); loc `te_seabed_relinquish_btn` ("Relinquish"), `te_seabed_claim_again_btn` ("Claim Again"), `te_seabed_relinquish_tt`, `te_seabed_claim_again_tt`.

- [ ] **Step 1: Write the failing tests**

```python
class RelinquishScriptTest(unittest.TestCase):
    def test_relinquish_never_reshares(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_relinquish"))
        self.assertIn("te_seabed_relinq_$B$", body)
        self.assertNotIn("te_seabed_reshare", body)

    def test_weight_is_zero_while_relinquished(self):
        self.assertIn("te_seabed_relinq_$B$", block(read(EFFECTS), "te_seabed_weight_set"))

    def test_buttons(self):
        sguis = read("common/scripted_guis/te_global_commons_seabed_sguis.txt")
        for b in m.BASINS:
            self.assertIn(f"te_seabed_relinquish = {{ B = {b} }}", block(sguis, f"te_seabed_relinquish_{b}_sgui"))
            self.assertIn(f"te_seabed_claim_again = {{ B = {b} }}", block(sguis, f"te_seabed_claim_again_{b}_sgui"))
```

- [ ] **Step 2: Run** — `FAILED`.
- [ ] **Step 3: Implement** to Task 2's model. Relinquish: `te_seabed_unbuilt_$B$` to 0, set `te_seabed_relinq_$B$`, remove `te_seabed_floor_$B$`. Weight: a relinquished basin's `te_seabed_w_$B$` is 0 (home flag still set, so coast rules elsewhere hold). Relinquish `is_valid`: claims there > 0; Claim Again `is_valid`: relinquished there. The relinquish tooltip says the claims wait for the next sharing; Claim Again's says it counts from the next sharing.
- [ ] **Step 4: Run** `test_seabed_script` — `OK`.
- [ ] **Step 5: Commit** — `"Seabed: Relinquish and Claim Again"`

### Task 7: Script — the holding fee

**Files:**
- Modify: `common/scripted_effects/te_global_commons_seabed_effects.txt` (new `te_seabed_take_snapshots`, `te_seabed_fee_refresh`; call from `te_seabed_monthly_country`), `common/script_values/te_global_commons_seabed_values.txt`, `common/static_modifiers/te_global_commons_seabed_modifiers.txt`, `common/script_values/te_global_commons_un_values.txt` (`te_seabed_royalties_total_value`)
- Test: `test_seabed_script.py` (class `FeeScriptTest`), `test_global_commons_un.py` if it pins the royalty total

**Interfaces:**
- Consumes: Task 3's model.
- Routing: the fee joins the World Development Fund's (or the UN budget's) weekly total only for countries that would pay royalties, i.e. Law of the Sea parties under the Regulated regime (`te_seabed_royalty_payer`'s party and regime tests, without its "has levels" test); for everyone else it is a plain expense.
- Produces: values `te_seabed_fee_rate = 0.02`, `te_seabed_fee_base` (country), `te_seabed_fee_weekly_value` (country: base × `te_seabed_level_output_value` × rate), `te_seabed_fee_grace_disp` (country: licences on unbuilt levels still in grace); variable `te_seabed_fee_cached` (country); static modifier `te_seabed_holding_fee_modifier` (`country_expenses_add = 1`, plus the budget-category key the royalty modifier carries if `docs/systems/budget_breakdown.md` needs one).

- [ ] **Step 1: Write the failing tests**

```python
class FeeScriptTest(unittest.TestCase):
    def test_rate(self):
        self.assertEqual(literal(read(VALUES), "te_seabed_fee_rate"), m.FEE_RATE)

    def test_base_is_the_smallest_of_now_and_two_snapshots(self):
        body = strip_comments(block(read(VALUES), "te_seabed_fee_base"))
        for v in ("te_seabed_unb_snap1", "te_seabed_unb_snap2", "level"):
            self.assertIn(v, body)

    def test_one_refresh_site(self):
        effects = strip_comments(read(EFFECTS))
        self.assertEqual(effects.count("name = te_seabed_holding_fee_modifier"), 1)
        self.assertIn("te_seabed_fee_refresh = yes", block(read(EFFECTS), "te_seabed_monthly_country"))

    def test_fee_joins_royalties_under_regulation(self):
        self.assertIn("te_seabed_fee_cached", block(read("common/script_values/te_global_commons_un_values.txt"),
                                                    "te_seabed_royalties_total_value"))
```

Add `FEE_RATE = 0.02` to the model's constants block.

- [ ] **Step 2: Run** — `FAILED`.
- [ ] **Step 3: Implement.** `te_seabed_take_snapshots` (state scope) from the yearly pass on the year's first sharing, after recording: `te_seabed_unb_snap2 = snap1; te_seabed_unb_snap1 = records − built level`. `te_seabed_fee_refresh` (country, monthly, the modifier's single refresh site): cache `te_seabed_fee_weekly_value`, re-add the modifier with `multiplier = var:te_seabed_fee_cached` when > 0, else remove it; off with the rule off. Royalties total adds `te_seabed_fee_cached` for countries that pay it while `te_seabed_regime_regulated = yes`.
- [ ] **Step 4: Run** `test_seabed_script`, `test_global_commons_un` — `OK`.
- [ ] **Step 5: Commit** — `"Seabed: holding fee on licences of unbuilt levels"`

### Task 8: Script — Sponsor's cost, the policy lock, and the defection clock

**Files:**
- Modify: `common/static_modifiers/te_global_commons_seabed_modifiers.txt`, `common/scripted_effects/te_global_commons_seabed_effects.txt` (`te_seabed_set_policy`, `te_seabed_refresh_policy_cost`, `te_seabed_policy_cost_check`, `te_seabed_ai_choose_policy`), `common/script_values/te_global_commons_seabed_values.txt`, `common/scripted_triggers/te_global_commons_seabed_triggers.txt` (`te_seabed_can_choose_*`), `common/scripted_effects/te_seabed_un_hooks.txt` (`te_seabed_un_on_policy_change`), `common/script_values/te_global_commons_un_values.txt`
- Test: `test_seabed_script.py` (`ConstantsTest.test_influence_modifiers_restate_their_values` rewritten; class `LockTest`), `test_global_commons_un.py`

**Interfaces:**
- Produces: values `te_seabed_influence_per_claim = 0.5`, `te_seabed_unilateral_cost_mult = 1.5`, `te_seabed_policy_lock_months = 60`, `te_seabed_protected_claims` (country: Σ unused claims, excluding relinquished basins), `te_seabed_sponsor_cost_value`, `te_seabed_unilateral_cost_value`, `te_seabed_policy_unlock_month_value`; variable `te_seabed_policy_changed` (month index of the last change); triggers `te_seabed_policy_locked`, `te_seabed_unilateral_answer_open` (a country sharing a home basin with ROOT switched to Unilateral after ROOT's last change), `te_seabed_influence_deficit` (`influence < 0`); the two cost modifiers become `country_influence_cost_add = 1` with a multiplier.

- [ ] **Step 1: Write the failing tests**

```python
class LockTest(unittest.TestCase):
    def test_constants(self):
        v = read(VALUES)
        self.assertEqual(literal(v, "te_seabed_influence_sponsor"), 50)
        self.assertEqual(literal(v, "te_seabed_influence_per_claim"), 0.5)
        self.assertEqual(literal(v, "te_seabed_unilateral_cost_mult"), 1.5)
        self.assertEqual(literal(v, "te_seabed_influence_unilateral"), 150)
        self.assertEqual(literal(v, "te_seabed_policy_lock_months"), 60)

    def test_costs_are_unit_modifiers_with_a_multiplier(self):
        mods = read(MODIFIERS)
        for key in ("sponsor", "unilateral"):
            self.assertIn("country_influence_cost_add = 1", block(mods, f"te_seabed_policy_{key}_cost"))
        refresh = strip_comments(block(read(EFFECTS), "te_seabed_refresh_policy_cost"))
        self.assertIn("multiplier = te_seabed_sponsor_cost_value", refresh)
        self.assertIn("multiplier = te_seabed_unilateral_cost_value", refresh)

    def test_set_policy_stamps_the_change(self):
        self.assertIn("name = te_seabed_policy_changed", block(read(EFFECTS), "te_seabed_set_policy"))

    def test_buttons_obey_the_lock_and_carve_outs(self):
        t = read(TRIGGERS)
        self.assertIn("te_seabed_policy_locked", block(t, "te_seabed_can_choose_sponsor"))
        self.assertIn("te_seabed_unilateral_answer_open", block(t, "te_seabed_can_choose_unilateral"))
        self.assertIn("te_seabed_influence_deficit", block(t, "te_seabed_can_choose_survey"))

    def test_ai_obeys_the_lock(self):
        self.assertIn("te_seabed_can_choose_", block(read(EFFECTS), "te_seabed_ai_choose_policy"))

    def test_no_change_date_is_unlocked(self):
        body = strip_comments(block(read(TRIGGERS), "te_seabed_policy_locked"))
        self.assertIn("has_variable = te_seabed_policy_changed", body)
```

In `test_global_commons_un.py`: the defection stores the month (`name = te_seabed_defected value = te_history_month_index`), and leaving sets `te_seabed_party_cooldown_end` from `var:te_seabed_defected + te_seabed_party_cooldown_months` only when that is still in the future.

- [ ] **Step 2: Run** both files — `FAILED`.
- [ ] **Step 3: Implement.**
  - Cost: Sponsor `te_seabed_influence_sponsor + te_seabed_influence_per_claim × te_seabed_protected_claims`; Unilateral `max(te_seabed_influence_unilateral, te_seabed_unilateral_cost_mult × that)`. `te_seabed_policy_cost_check` re-adds the modifier monthly when the figure moves (cache it in `te_seabed_policy_cost_cached`; single refresh site stays `te_seabed_refresh_policy_cost`).
  - Lock: `te_seabed_set_policy` sets `te_seabed_policy_changed` (not on the yearly pass's forced reset to Survey for a non-claimant). Locked = variable present and `te_history_month_index < var + 60`. Survey allowed when unlocked or `te_seabed_influence_deficit`; Unilateral when unlocked or `te_seabed_unilateral_answer_open`; Sponsor only when unlocked. Each greyed button's tooltip names the unlock date (`te_seabed_policy_locked_tt`, `te_seabed_policy_answer_tt`, `te_seabed_policy_deficit_tt`).
  - AI: `te_seabed_ai_choose_policy` switches only to a policy whose `te_seabed_can_choose_*` holds.
  - Defection clock: an old save's flag-only `te_seabed_defected` (value below 12) keeps today's rule (`te_seabed_party_cooldown_end_value`).
- [ ] **Step 4: Run** `test_seabed_script`, `test_global_commons_un`, `test_seabed_allocation` — `OK`.
- [ ] **Step 5: Commit** — `"Seabed: Sponsor's scaled cost, the five-year lock, the defection clock"`

### Task 9: Script — readout, rankings and panel values

**Files:**
- Modify: `common/scripted_effects/te_global_commons_seabed_effects.txt` (`te_seabed_share_round`, `te_seabed_yearly_pass` step 10), `common/script_values/te_global_commons_seabed_values.txt`, `common/scripted_guis/te_global_commons_seabed_sguis.txt`
- Test: `test_seabed_script.py` (class `PanelDataTest`)

**Interfaces:**
- Consumes: Task 4's model.
- Produces (all read by Task 11's panel):
  - country vars `te_seabed_need_navy_<b>` (whole units; `-1` = full) written in `te_seabed_share_round` by `te_seabed_readout = { B }` before the active flags are removed; display `te_seabed_need_navy_disp_<b>`. The navy conversion needs the coast counts `te_seabed_compute_weights` keeps only in locals today: `te_seabed_weight_set` also stores `te_seabed_coast_<b>` (n) and `te_seabed_coast_all` (N) on the country.
  - `te_seabed_weight_pct_disp_<b>` (country: `w ÷ global_var:te_seabed_world_w_<b> × 100`).
  - country vars `te_seabed_queued_<b>`, written by `te_seabed_record_country`'s state walk (model `queued_by_basin`: a state's queued levels count against its distant licences first, basin order, then its own).
  - pool-bar cumulative fractions per basin, 0..1: `te_seabed_bar_<b>_1` (our built licences), `_2` (+ our queued licences), `_3` (+ our claims), `_4` (+ rivals' licences); the bar's background is rivals' claims. The mockup's five segments.
  - `te_seabed_ent_value_<b>` (country: `var:te_seabed_ent_<b>`, guarded; the `order_by` for the ranking, as `te_seabed_frac_value_$B$` is for the rounding).
  - `te_seabed_jan_loss_disp` (country: at most what next January can take, Σ claims − floor-protected part; equals all claims off Sponsor); `te_seabed_last_sharing_month` (global, month index of the last sharing) for "as of".
  - effect `te_seabed_rank_basin = { B }` (no scope, step 10): globals `te_seabed_rk_<b>_<n>` (n = 1..6, by entitlement, `ordered_country` with `position = n−1` and `order_by = te_seabed_ent_value_<b>`), stale ranks removed; `te_seabed_rk_more_<b>` = claimants beyond six; on every `is_player = yes` country with `te_seabed_shared`, `te_seabed_rkcap_<b>_<n>` = that country's capital.
  - scripted GUI `te_seabed_rival_row_sgui` (`saved_scopes = { op }`, op = 10 × basin index + n; pattern `ch_board_row_sgui`): `is_shown` = slot filled; effect enters `global_var:te_seabed_rk_<b>_<n> ?=` and prints `te_seabed_rival_row_<b>` with `custom_tooltip_no_bullet`.

- [ ] **Step 1: Write the failing tests**

```python
class PanelDataTest(unittest.TestCase):
    def test_readout_written_before_active_flags_go(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_share_round"))
        self.assertLess(body.index("te_seabed_readout = { B = $B$ }"), body.index("remove_variable = te_seabed_act_$B$"))

    def test_ranks_every_basin(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        for b in m.BASINS:
            self.assertIn(f"te_seabed_rank_basin = {{ B = {b} }}", body)

    def test_rank_flags_go_through_the_capital(self):
        self.assertIn("te_seabed_rkcap_$B$_", block(read(EFFECTS), "te_seabed_rank_basin"))

    def test_rival_row_follows_the_leaderboard_pattern(self):
        body = block(read("common/scripted_guis/te_global_commons_seabed_sguis.txt"), "te_seabed_rival_row_sgui")
        self.assertIn("saved_scopes = { op }", body)
        self.assertIn("custom_tooltip_no_bullet", body)
        self.assertIn("?=", body)

    def test_bar_values_exist(self):
        v = read(VALUES)
        for b in m.BASINS:
            for k in (1, 2, 3, 4):
                block(v, f"te_seabed_bar_{b}_{k}")

    def test_recording_writes_queued_per_basin(self):
        self.assertIn("te_seabed_queued_", block(read(EFFECTS), "te_seabed_record_country"))
```

- [ ] **Step 2: Run** — `FAILED`.
- [ ] **Step 3: Implement** to the model and the names above. Guard every display value to read 0 when its variable is missing (the file's `*_disp_*` pattern).
- [ ] **Step 4: Run** `test_seabed_script` — `OK`.
- [ ] **Step 5: Commit** — `"Seabed: readout, rankings and panel values"`

### Task 10: Words — licence and claim everywhere

**Files:**
- Modify: `localization/english/te_miscellaneous_l_english.yml` (every `te_seabed_*` and `TE_STATE_SEABED_*` key), `localization/english/te_concepts_l_english.yml` (`concept_seabed_licence_desc`, new `concept_seabed_claim_desc`), `localization/english/te_journal_entries_l_english.yml` (`je_un_terms_law_of_sea_seabed`, `je_un_chamber_seabed_*`), `localization/english/te_notifications_l_english.yml` (seabed notices), `common/game_concepts/extra_concepts.txt` (`concept_seabed_claim`)
- Test: Create `test_seabed_loc.py`

**Interfaces:**
- Produces: concept `concept_seabed_claim`; new keys the panel uses: `te_seabed_ov_room_cap`, `te_seabed_ov_licences_cap`, `te_seabed_ov_longhaul_cap`, `te_seabed_ov_claims_cap`, `te_seabed_ov_policy_cap`, `te_seabed_ov_regime_cap` (captions) and their `_word`, `_fig`, `_tt` keys; `te_seabed_policy_short_1/2/3` ("Survey", "Sponsor", "Unilateral"); column heads `te_seabed_col_free`, `te_seabed_col_pool`, `te_seabed_col_weight`, `te_seabed_col_next` with `_tt`; `te_seabed_basins_asof`; `te_seabed_rival_row_<b>`, `te_seabed_rivals_more_<b>`, `te_seabed_rival_us_<b>`; `te_seabed_how_sub_claims` + `te_seabed_how_claims`.

- [ ] **Step 1: Write the failing test**

```python
"""No seabed string a player reads says "recorded" (spec § 1)."""
import os, re, unittest
REPO = os.path.dirname(os.path.abspath(__file__))
PREFIXES = ("te_seabed_", "TE_STATE_SEABED", "concept_seabed", "je_un_terms_law_of_sea_seabed",
            "je_un_chamber_seabed", "notification_te_seabed")

class SeabedWordsTest(unittest.TestCase):
    def test_no_recorded(self):
        bad = []
        loc = os.path.join(REPO, "localization", "english")
        for f in os.listdir(loc):
            with open(os.path.join(loc, f), encoding="utf-8-sig") as fh:
                for line in fh:
                    m = re.match(r'\s*([\w.]+):\d*\s*"(.*)"\s*$', line)
                    if m and m.group(1).startswith(PREFIXES) and re.search(r"\brecord", m.group(2), re.I):
                        bad.append(m.group(1))
        self.assertEqual(bad, [])

    def test_claim_concept(self):
        with open(os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt"), encoding="utf-8-sig") as f:
            self.assertRegex(f.read(), r"(?m)^concept_seabed_claim = \{")
```

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_seabed_loc -v` — Expected: FAIL listing today's "recorded" keys.
- [ ] **Step 3: Rewrite** in the spec's words (§ 1, § 2's display lines): "in use" for the world's licences, "claims" for unused shares, "as of <month year>". Keep every `[...]` data call the old text had unless the panel no longer needs it. Write the How section's new subsections (Claims and Protection; Leases waits for phase 2). Then `python3 organize_loc.py` and `python3 scripts/analysis/check_localization_files.py`.
- [ ] **Step 4: Run** `test_seabed_loc` — `OK`; `python3 organize_loc.py --check` exits 0.
- [ ] **Step 5: Commit** (loc files plus whatever `organize_loc` moved) — `"Seabed: licence and claim, no more 'recorded'"`

### Task 11: The panel (layout A) and its width test

**Files:**
- Modify: `gui/te_seabed_widgets.gui`, `gui/states_panel.gui` (only if the tile's text keys change)
- Test: Create `test_seabed_layout.py`

**Interfaces:**
- Consumes: Task 9's values and scripted GUIs, Task 10's keys, Task 6's buttons.
- Produces: types `te_seabed_ov_cell` (icon inset, caption, word, figure; pattern `te_banking_ov_cell`), `te_seabed_basin_row` (rewritten: chevron+name 104, free 64, pool bar 150, weight 72, next 90 = 480), `te_seabed_rival_row` (flag 24 + text 440), and font templates `te_seabed_fontsize_row` (17), `_heading` (20), `_overview` (16) at the head of the file.

- [ ] **Step 1: Write the failing test** — reuse the Banking test's helpers.

```python
import re, unittest
import os
from test_banking_layout import _all_loc, _custom_options, _read, _block_from, UNITS, MARGIN, NUMBER

REPO = os.path.dirname(os.path.abspath(__file__))
GUI = os.path.join(REPO, "gui", "te_seabed_widgets.gui")   # _read opens the path as given

class SeabedWidthTest(unittest.TestCase):
    """Every fixed-width seabed cell fits its longest text (spec § 3.7)."""
    # Port WidthBudgetTest.shown/_text/fits/box from test_banking_layout.py, reading
    # fonts from the te_seabed_fontsize_* templates. Then one test per cell:
    def test_policy_buttons(self): ...      # te_seabed_policy_short_1..3 in the button's text box
    def test_overview_cells(self): ...      # every te_seabed_ov_*_cap/_word/_fig in te_seabed_ov_cell
    def test_basin_columns(self): ...       # basin names, the five column heads, "full", readout "+9999"
    def test_rival_rows(self): ...          # te_seabed_rival_row_<b> at the longest country name in
                                            # localization (a scan of country name keys), numbers at NUMBER

class SeabedPanelTest(unittest.TestCase):
    def test_four_sections_in_order(self): ...   # overview, policy, basins, how — by type instance order
    def test_rival_rows_use_the_leaderboard_sgui(self):
        self.assertIn("te_seabed_rival_row_sgui", _read(GUI))
    def test_flags_go_through_the_capital(self):
        self.assertIn(".Var('te_seabed_rkcap_", _read(GUI))
    def test_rivals_collapse_flags_are_open_named(self): ...  # rule 7: _open suffix for a collapsed-by-default section
```

Fill the `...` bodies from `test_banking_layout.py`'s `WidthBudgetTest`, the same assertions with this file's cells.

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_seabed_layout -v` — Expected: FAIL (the types don't exist; the buttons overflow).
- [ ] **Step 3: Build the panel** to spec § 3 and the mockup (`docs/superpowers/archive/specs/assets/2026-10-17-seabed-panel-layouts.html`, option A): overview 2×3 grid; three short policy buttons centred; Ocean Basins with "as of"; five rows each with a chevron toggling its rivals (six `te_seabed_rival_row` instances with `op` 10×basin+n, the "us" row with Relinquish/Claim Again, "and N others"; each rival row's `visible`, flag included, is the same `te_seabed_rival_row_sgui` `IsShown` its text uses, so an unfilled slot reads no missing `te_seabed_rkcap_*` variable); the stacked pool bar as four overlaid `progressbar`s over a rivals'-claims background, the queued segment hatched or a lighter shade of ours (stacked-bar precedent: `gui/te_budget_generated_charts.gui`); How Seabed Licences Work collapsed at the bottom. Icons: existing vanilla textures only.
- [ ] **Step 4: Verify**: `test_seabed_layout`, `test_te_systems_window` → `OK`; `python3 scripts/analysis/check_gui_lint.py` → no errors; `python3 gui_reference_audit.py --strict` → exit 0.
- [ ] **Step 5: Commit** — `"Seabed panel: layout A"`

### Task 12: Docs, guide and play-test list

**Files:**
- Modify: `docs/player_guide/02-timeline.md` (§ Seabed licences), `docs/player_guide/17-reference.md` (glossary: Seabed licence, new Seabed claim, Reserved half), `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`, `docs/systems/mod_systems.md` (§ Global Commons, the state-tile row), `docs/testing/global-commons-playtest.md`

- [ ] **Step 1:** Rewrite the guide's Seabed section at its current depth: licence and claim, the fee's grace, Sponsor's protection and cost, the lock and both carve-outs, Relinquish, the panel's four questions, pioneer-investor spill into the reserved half. No figures the tooltips already show. Then `python3 scripts/analysis/check_player_guide_style.py --strict`.
- [ ] **Step 2:** `.venv/bin/python scripts/build_player_guide.py` and `scripts/build_player_guide.py --check` → exit 0.
- [ ] **Step 3:** `mod_systems.md`: new variables, effects and the four new self-check/play-test items; play-test list: add `seabed_floor_fits` to the self-checks table and rows for: rival rows render and open; the fee appears after the grace; Relinquish frees claims at the next sharing; the lock greys buttons and both carve-outs free them; the panel at 1080p has no overflow; in an observer run, AI holding-fee totals stay small (the engine's builder knows nothing of the fee; if AIs queue far ahead, lower the rate or lengthen the grace, never an `is_ai` rule, spec § 8).
- [ ] **Step 4:** `python3 scripts/analysis/check_post_load_rosters.py` → exit 0 (no roster change expected).
- [ ] **Step 5: Commit** — `"Seabed phase 1: guide, system docs, play-test list"`
