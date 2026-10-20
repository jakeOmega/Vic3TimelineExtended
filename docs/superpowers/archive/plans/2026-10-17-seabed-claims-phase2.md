# Seabed Claims, Phase 2 (leases, island coast, subjects) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let seabed claims be leased by treaty (enforceable, so winnable in war), let unincorporated coast count toward claim weight at half, and let an overlord take its subject's unused claims by an optional diplomatic action.

**Architecture:** As phase 1: the model (`scripts/analysis/seabed_model.py`) first, then the script mirroring it. A lease moves claims after each sharing and, for the sharing itself, counts the licences built on it as the lessor's holdings, so the lessee's own share is untouched. The subject action is a lease with no total that reuses the same consumption and top-up steps.

**Tech Stack:** Victoria 3 Paradox script (treaty articles, diplomatic actions), localization YAML, Python 3.11/3.12 `unittest`.

**Spec:** `docs/superpowers/archive/specs/2026-10-17-seabed-claims-and-panel-design.md` §§ 4, 5, 8, 9. **Requires phase 1 merged** (`docs/superpowers/archive/plans/2026-10-17-seabed-claims-phase1.md`): floors (`te_seabed_floor_<b>`, `te_seabed_fz_<b>`), the first-sharing flag, the panel.

## Global Constraints

- Everything in phase 1's Global Constraints holds.
- A lease's N is its **total**: licences the lessee built on it plus its unused leased claims never exceed N (spec § 4, my call).
- One treaty lease per basin per lessee; a lessor may lease to several countries.
- Consumption order when the lessee's claims fall: its own claims first, then subject-passed claims, then treaty-leased claims.
- Licences built on a lease are the lessee's for good. Built licences never move by treaty.
- The subject action passes the subject's unused claims at entry and after every sharing, with no total; only the overlord starts or ends it (owner).
- Unincorporated coastal states count at `0.5` in the coast term and the navy spread; their ports count in full.
- Antarctic Treaty parties (`te_seabed_southern_barred`) can neither lease out nor receive Southern claims.
- `docs/vanilla/treaty_articles_reference.md` is CRLF: preserve line endings (`grep -c $'\r$'` vs `wc -l` before and after).

## Review Focus

1. **A lessor that dies or stops claiming while a lease stands** (annexed, loses its coast): the lease ends at the next sharing, the lessee keeps what it built, nothing goes negative. Test: Task 1 `test_lessor_annexed`.
2. **Lease-built levels destroyed**: the licence comes back as the lessee's own claim; the lease's built count is capped at the lessee's holdings so the sharing never sees negative holdings. Test: Task 1 `test_destroyed_lease_level`.
3. **N above what the lessor has**: a partial top-up, never negative claims on either side. Test: Task 1 `test_partial_top_up`.
4. **The subject action ends mid-year**: the overlord keeps already-passed claims until the next sharing, then the subject claims its own share. Test: Task 2 `test_pact_ends_mid_year`.
5. **A second lease in the same basin to the same lessee**: refused by `possible`. Test: Task 3 `test_one_lease_per_basin_per_lessee`.

---

### Task 1: Model — treaty leases

**Files:** Modify `scripts/analysis/seabed_model.py`; Test `test_seabed_allocation.py` (class `LeaseTest`; extend `PoolsHoldTest` with random leases)

**Interfaces:**
- Consumes: phase 1's `share_basin` (freezes on `fit_floors`), `set_floors`, `record_country`.
- Produces: `Country.lease_src / lease_n / lease_built / lease_unused: dict` (basin → value; script `te_seabed_lease_src_<b>` (country), `_n_<b>`, `_built_<b>`, `_unused_<b>`); `World.leases_ended: set` of (cid, b); `start_lease(world, src, dst, b, n) -> None` (`te_seabed_lease_start`), `end_lease(world, dst, b) -> None` (marks it; settled at the next sharing), `lease_consume(world, cid) -> None` (`te_seabed_lease_consume`, end of `record_country`), `share_held(world, cid, b) -> int` (`te_seabed_sh_<b>`: held − built on its lease + built on leases it gave), `settle_leases(world) -> None` (`te_seabed_settle_leases`, after the five sharings).

- [ ] **Step 1: Write the failing tests**

```python
class LeaseTest(unittest.TestCase):
    def _world(self):
        # country 0 (lessor) and 1 (lessee), each with one Pacific coastal state; one pass
        ...

    def test_entry_moves_claims_at_once(self):
        w = self._world(); before = w.countries[0].unbuilt["pacific"]
        m.start_lease(w, 0, 1, "pacific", 20)
        self.assertEqual(w.countries[0].unbuilt["pacific"], before - 20)
        self.assertEqual(w.countries[1].lease_unused["pacific"], 20)

    def test_own_claims_are_used_first(self):
        # lessee with 5 own claims queues 7 levels: lease_built == 2, lease_unused == 18
        ...

    def test_lessee_share_is_untouched_by_the_lease(self):
        # after building 10 on the lease and a sharing, the lessee's own claims equal what
        # they would be with no lease and no such levels (its share by weight)
        ...

    def test_total_never_exceeds_n(self):
        # 50 random worlds with random leases: lease_built + lease_unused <= lease_n every month
        ...

    def test_partial_top_up(self): ...          # lessor has 3 claims, N = 20: unused 3, no side negative
    def test_lessor_annexed(self): ...          # lessor dies: next pass clears the lease, lessee keeps its built licences
    def test_destroyed_lease_level(self): ...   # lessee demolishes a lease-built level: lease_built <= lessee held, share_held >= 0
    def test_ended_lease_returns_unused_at_next_sharing(self): ...
```

In `PoolsHoldTest`, add a variant (`test_leases`) whose month step starts a random lease between two claimants with probability 0.05 and ends one with 0.03, under every regime, with the existing `_check` plus `lease_built + lease_unused <= lease_n`.

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_seabed_allocation.LeaseTest -v` — Expected: AttributeError.
- [ ] **Step 3: Implement.**
  - `share_held` shifts `lease_built` (capped at the lessee's held) from lessee to lessor. `fit_floors` and `share_basin` use `share_held` where phase 1 used `held`; `unbuilt = ent − share_held`. A lessee's floor counts only its own claims (`unbuilt − lease_unused − subj_unused`).
  - `lease_consume`: `new = min(lease_unused, unbuilt)`; `lease_built += lease_unused − new`; `lease_unused = new`.
  - `settle_leases`: for an ended lease or a dead lessor, move `min(lease_unused, lessee.unbuilt)` back to a living lessor and clear the lease; for a standing one, top up `min(N − lease_built − lease_unused, lessor.unbuilt)` from lessor to lessee.
  - Docstring: a "LEASES" section naming the script effects.
- [ ] **Step 4: Run the file** `2>&1 | grep -E '^(Ran |OK|FAILED)'` — `OK`.
- [ ] **Step 5: Commit** — `"Seabed model: treaty leases"`

### Task 2: Model — subject pooling and unincorporated coast

**Files:** Modify `scripts/analysis/seabed_model.py`; Test `test_seabed_allocation.py` (classes `SubjectTest`, extend `WeightTest`)

**Interfaces:**
- Produces: `UNINCORPORATED_COAST = 0.5` (`te_seabed_uninc_coast`); `World.administer: set` of (overlord, subject) (script: the pact `te_seabed_administer_claims`); `Country.subj_unused: dict` (`te_seabed_subj_unused_<b>`); `pass_subject_claims(world) -> None` (`te_seabed_pass_subject_claims`, at entry and after `settle_leases`).

- [ ] **Step 1: Write the failing tests**

```python
class SubjectTest(unittest.TestCase):
    def test_subject_claims_pass_every_sharing(self): ...   # after a pass, subject.unbuilt == 0, overlord.subj_unused == subject's share - held
    def test_no_pooling_without_the_pact(self): ...
    def test_pact_ends_mid_year(self): ...                   # overlord keeps subj_unused until the pass; then subject keeps its own share
    def test_overlord_floor_excludes_subject_claims(self): ...

class WeightTest(...):   # existing class
    def test_unincorporated_coast_counts_half(self):
        # one incorporated + two unincorporated Pacific states, no ports, navy 0, Sponsor:
        # w["pacific"] == 2 * (1 + 0.5 * 2) == 4.0; a basin with only unincorporated coast is home
        ...
```

- [ ] **Step 2: Run** — Expected: failures.
- [ ] **Step 3: Implement**: `compute_weights` counts every coastal state, unincorporated at `UNINCORPORATED_COAST` in both `n` and `N`; ports full. `pass_subject_claims` moves each subject's `unbuilt` to its overlord's `unbuilt` and `subj_unused`; `lease_consume` drains `subj_unused` before `lease_unused`. Phase 1's `random_world` already makes 15% of states unincorporated; add random pacts (0.2 of countries are subjects of a random overlord, pact on with 0.5).
- [ ] **Step 4: Run the file** — `OK`.
- [ ] **Step 5: Commit** — `"Seabed model: subject pooling, unincorporated coast at half"`

### Task 3: Script — the five lease articles

**Files:**
- Create: `common/treaty_articles/122_seabed_lease.txt` (articles `te_seabed_lease_pacific`, `_atlantic`, `_indian`, `_arctic`, `_southern`)
- Modify: `common/scripted_effects/te_global_commons_seabed_effects.txt` (`te_seabed_lease_start`, `te_seabed_lease_consume`, `te_seabed_settle_leases`, share-held step), `common/scripted_triggers/te_global_commons_seabed_triggers.txt` (`te_seabed_can_lease = { B }`), `common/script_values/te_global_commons_seabed_values.txt`, `localization/english/te_miscellaneous_l_english.yml`
- Test: Create `test_seabed_leases.py`

**Interfaces:**
- Consumes: Task 1's names; phase 1's `te_seabed_fz_<b>`, `te_seabed_set_floors`.
- Produces: per-article `required_inputs = { quantity }`, `quantity_min_value = 1`, `quantity_max_value` = the source's claims in the basin; `flags = { can_be_enforced can_be_renegotiated giftable }`; `usage_limit = once_per_treaty`; `kind = directed`; `on_entry_into_force` → `te_seabed_lease_start = { B = <b> }` with the source and target saved as `scope:te_sb_lessor` / `scope:te_sb_lessee` and N from `scope:article.input_quantity` (read the scope links in `docs/vanilla/treaty_articles_reference.md` and vanilla `05_transfer_money.txt`); the sharing reads in-force articles with `every_scope_treaty = { every_scope_article = { limit = { has_type = te_seabed_lease_<b> } … } }` (pattern: `nd_taboo_refresh_treaty_ceiling`), so an article that ended for any reason, annexation included, ends its lease. `requirement_to_maintain`: both sides still `te_seabed_is_claimant = yes`, so a lessee or lessor that loses its coast or the technology ends the article, and the next sharing's end-detection clears the lease.

- [ ] **Step 1: Write the failing tests**

```python
class LeaseArticleTest(unittest.TestCase):
    def test_five_articles(self):
        text = read("common/treaty_articles/122_seabed_lease.txt")
        for b in m.BASINS:
            body = block(text, f"te_seabed_lease_{b}")
            self.assertIn("kind = directed", body)
            self.assertIn("can_be_enforced", body)
            self.assertRegex(body, r"required_inputs = \{\s*quantity\s*\}")
            self.assertIn(f"te_seabed_lease_start = {{ B = {b} }}", body)
            self.assertIn(f"te_seabed_can_lease = {{ B = {b} }}", body)

    def test_one_lease_per_basin_per_lessee(self):
        self.assertIn("te_seabed_lease_src_$B$", block(read(TRIGGERS), "te_seabed_can_lease"))

    def test_antarctic_bar_on_both_sides(self):
        self.assertIn("te_seabed_southern_barred", block(read(TRIGGERS), "te_seabed_can_lease"))

    def test_sharing_order(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        at = [body.index(s) for s in ("te_seabed_compute_held", "te_seabed_lease_shift_held",
                                      "te_seabed_share_basin = { B = southern }", "te_seabed_settle_leases",
                                      "te_seabed_world_totals = { B = pacific }")]
        self.assertEqual(at, sorted(at))

    def test_consume_after_recording(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_record_country"))
        self.assertGreater(body.index("te_seabed_lease_consume"), body.index("te_seabed_state_swap_local"))
```

(`read`, `block`, `strip_comments`, `m` and the path constants as in `test_seabed_script.py`; import them from it.)

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_seabed_leases -v` — `FAILED`.
- [ ] **Step 3: Implement** to Task 1's model. `te_seabed_lease_shift_held` writes `te_seabed_sh_<b>` for every participant after `te_seabed_compute_held`; phase 1's floor, fit and freeze steps read `te_seabed_sh_<b>` instead of `te_seabed_held_<b>`. Loc: article names ("Lease Pacific Seabed Claims" …), descriptions, `possible` tooltips, the AI `desc` keys of Task 6. Icon: an existing vanilla article icon (no new art).
- [ ] **Step 4: Run** `test_seabed_leases`, `test_seabed_script`, `test_seabed_allocation` — `OK`; `python3 treaty_leverage_side_audit.py --strict` and `python3 loc_coverage_audit.py --strict` → exit 0.
- [ ] **Step 5: Commit** — `"Seabed: Lease Seabed Claims treaty articles"`

### Task 4: Script — unincorporated coast at half

**Files:** Modify `common/scripted_effects/te_global_commons_seabed_effects.txt` (`te_seabed_compute_weights`, `te_seabed_weight_tally`), `common/script_values/te_global_commons_seabed_values.txt`, `common/scripted_triggers/te_global_commons_seabed_triggers.txt` (the comment on `te_seabed_shares_home_basin_with_uni`), loc `te_seabed_how_weight`, `te_seabed_col_weight_tt`; Test `test_seabed_script.py`

**Interfaces:** Produces `te_seabed_uninc_coast = 0.5`.

- [ ] **Step 1: Write the failing test** — `ConstantsTest.test_weights` asserts `literal(values, "te_seabed_uninc_coast") == m.UNINCORPORATED_COAST`; a new test asserts `te_seabed_compute_weights`' state walk no longer limits on `is_incorporated = yes` and `te_seabed_weight_tally` adds `te_seabed_uninc_coast` for an unincorporated state.
- [ ] **Step 2: Run** — `FAILED`.
- [ ] **Step 3: Implement** to Task 2's model; rewrite the two loc strings ("unincorporated coastal states count half").
- [ ] **Step 4: Run** `test_seabed_script`, `test_seabed_allocation` — `OK`.
- [ ] **Step 5: Commit** — `"Seabed: unincorporated coast counts half"`

### Task 5: Script — Administer Seabed Claims

**Files:**
- Create: `common/diplomatic_actions/te_seabed_administer_claims.txt`
- Modify: `common/scripted_effects/te_global_commons_seabed_effects.txt` (`te_seabed_pass_subject_claims`; call after `te_seabed_settle_leases`), `localization/english/te_miscellaneous_l_english.yml`
- Test: `test_seabed_leases.py` (class `SubjectActionTest`)

**Interfaces:**
- Produces: diplomatic action and pact type `te_seabed_administer_claims`, modelled on vanilla `raise_payments` (`vanilla_parsed/common/diplomatic_actions.json`): `groups = { overlord }`, `requires_approval = no`, potential: target is a direct subject of root and not `subject_type_protectorate` / `subject_type_personal_union`, root is a claimant; **no `has_dlc_feature`**; `pact = { cost = 25 relations_progress_per_day = -1 second_modifier = { country_liberty_desire_add = 0.10 } requirement_to_maintain = { at peace; still its subject } }`; `ai = { will_propose: target's unused claims > 0 and liberty desire < 25; will_break: target's liberty desire >= 50 }`.

- [ ] **Step 1: Write the failing tests**

```python
class SubjectActionTest(unittest.TestCase):
    def test_action_shape(self):
        body = block(read("common/diplomatic_actions/te_seabed_administer_claims.txt"), "te_seabed_administer_claims")
        self.assertIn("requires_approval = no", body)
        self.assertIn("country_liberty_desire_add = 0.10", body)
        self.assertNotIn("has_dlc_feature", body)
        self.assertIn("subject_type_protectorate", body)

    def test_claims_pass_after_the_leases_settle(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        self.assertLess(body.index("te_seabed_settle_leases"), body.index("te_seabed_pass_subject_claims"))
```

- [ ] **Step 2: Run** — `FAILED`.
- [ ] **Step 3: Implement** to Task 2's model; the action's tooltip states that the subject keeps its licences and that levels on passed claims outside the overlord's own coast are long-haul. Entry: pass the subject's current claims at once (`on_accept` or the pact's start hook; read `docs/vanilla/vanilla_politics_reference.md` and a mod pact action, `common/diplomatic_actions/extra_diplo_actions.txt:245` `diplomatic_alignment`, for the hook).
- [ ] **Step 4: Run** `test_seabed_leases` — `OK`; `python3 loc_coverage_audit.py --strict` → exit 0.
- [ ] **Step 5: Commit** — `"Seabed: Administer Seabed Claims"`

### Task 6: AI, panel lines, docs

**Files:**
- Modify: `common/script_values/te_global_commons_seabed_ai_values.txt` (lease AI), `common/treaty_articles/122_seabed_lease.txt` (`ai` blocks), `localization/english/te_miscellaneous_l_english.yml` (`te_seabed_ov_licences_tt` lists leased and subject-passed claims; How section `te_seabed_how_sub_leases` + `te_seabed_how_leases`), `docs/player_guide/02-timeline.md`, `docs/player_guide/09-diplomacy.md` (treaty article list; subject actions), `docs/player_guide/17-reference.md`, the PDF, `docs/vanilla/treaty_articles_reference.md` (CRLF), `docs/systems/mod_systems.md`, `docs/testing/global-commons-playtest.md`
- Test: `test_seabed_leases.py` (class `LeaseAiTest`)

**Interfaces:**
- Produces: values `te_seabed_ai_lease_offer_value` (source country: unused claims it is unlikely to use — claims in the basin above 12 months of its Deep-Sea Mine construction pace, 0 when it has queued none), `te_seabed_ai_lease_request_value` (target: room ≤ 5 and Tech-Critical Metals above base price in its market). Articles: `article_ai_usage = { offer request }`, `evaluation_chance` > 0 only when the matching value > 0, `quantity_input_value` = the source's spare claims, `inherent_accept_score` with `desc` lines.

- [ ] **Step 1: Write the failing test** — each article's `ai` block references `te_seabed_ai_lease_offer_value` or `_request_value`, has `article_ai_usage = { offer request }`, and every `desc = "…"` key exists in loc.
- [ ] **Step 2: Run** — `FAILED`.
- [ ] **Step 3: Implement**; then write the guide (leases, enforceability, island coast, the subject action) at its existing depth, rebuild the PDF, run `check_player_guide_style.py --strict` and `build_player_guide.py --check`; add the article to `treaty_articles_reference.md` (CRLF preserved); play-test rows: a lease moves claims at entry and at the sharing; an enforced lease from a war; the subject action passes claims and raises liberty desire.
- [ ] **Step 4: Run** `test_seabed_leases`, `test_seabed_script`, `test_seabed_allocation` — `OK`.
- [ ] **Step 5: Commit** — `"Seabed phase 2: AI, docs, play-test list"`
