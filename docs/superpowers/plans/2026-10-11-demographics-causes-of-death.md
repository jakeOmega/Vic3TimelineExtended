# Demographics: Causes of Death on the state subtab, medicine that spreads, and turmoil's violence (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the state panel's Demographics subtab gets a Causes of Death section that shows what drives each state's
deaths. Medicine reaches a state over years, not at once. Turmoil raises deaths from accidents and violence. Under the
Full setting the section also shows the deaths the game added on top of the census, and why.

**Architecture:**
- **One factor table.** `demographics_params.CAUSE_FACTORS` names each cause's factors. The model computes them
  (`cause_factors`), and the generator writes one script value per factor (`te_demog_f_<cause>_<factor>`) and each
  `te_demog_mult_<cause>` as their product. The section's hovers read the same script values, so the display and the
  census can't disagree.
- **Factors read only what the step stored.** Each seed and step stores the inputs the census used that aren't stored
  already: the drifted health-care access and treatments, the law and institution type sums, turmoil and crowding.
  Between steps the hover still multiplies to the row's figure.
- **Medicine drifts.** Health-care access and the three treatments move a share of the gap to their targets at each
  census step. The share is `0.1 + modifier:state_medical_diffusion_add`, from six technologies and the Medical
  Outreach decree.
- **The deaths added on top are measured, not inferred.** The yearly walk sums, under Full, each pop's deaths from the
  state's read and the absorbed terms alone. Over the target that is the whole state's part; the walk's own expected
  deaths over it are the part of the pops' own lines. The walk also counts the people in severe starvation.

**Tech Stack:** Paradox script (Victoria 3 1.14.5), the Python twin and harness (`scripts/analysis/demographics_*.py`),
the generator `scripts/generators/gen_demographics.py`, unittest with the repo's script interpreter
(`test_demographics_registry.py`'s `_Engine`).

**Spec:** the owner's approved design (2026-10-11), restated in "Design" below, and #894's section "The panel: what a
player can't see". It builds on `docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md` (the census's
term M and the on-top scales) and `docs/superpowers/plans/2026-10-11-demographics-engine-lines-script-only.md` (the
moved lines). Read `docs/systems/mod_systems.md` § Demographics first.

## Design (owner, 2026-10-11)

1. **A Causes of Death section on the state subtab, open by default.** One table, "Label: value" rows, each row's
   breakdown on hover (`docs/guides/gui_style_guide.md` rules 1, 3, 5):

   | Row | Value | Hover |
   |---|---|---|
   | Health Care Access | `62% → 68%` | 40% everywhere from markets and charity; the health law × Ministry of Health level (incorporated states, × Impact of Institutions); the spread of medicine |
   | Infection and Hunger | `×0.85` | Medicine `×0.75 → ×0.60`, Standard of Living, Poverty, Literacy, Crowding |
   | Accidents and Violence | `×0.90` | Laws and Institutions (policing, consumer protection, the combustion engine), Turmoil |
   | Chronic Illness, Old Age | `×0.95` | Medicine, Standard of Living, Laws and Institutions (pensions) |
   | Work | `×1.10` | Laws (child labour, Regulatory Bodies, Worker Protections) |
   | Childbirth | `380 per 100,000 births` | Medicine |
   | Deaths Added on Top (Full only) | `×1.62`, red from ×1.25 | the census's own deaths per 1,000 against the year's; the whole state's effects; some of its people's, above all severe starvation; the clamp, when it bit |

   Medicine is `1 − access × treatment`. The arrow appears while the drifted value is more than the snap from its
   target.
2. **Medicine drifts.** At each census step, health-care access and each cause's treatment move a share `r` of the
   way to today's target. Standard of living, literacy, crowding, the laws and turmoil take the step's values.
   - `r = 0.1 + modifier:state_medical_diffusion_add`, at most 1.
   - `state_medical_diffusion_add` is a new script-only state type carried by six technologies (+0.05 each, so 0.4
     with all six) and by the Medical Outreach decree (+0.2, in one state).
   - A value within 0.005 of its target takes the target, so the arrow goes away.
   - Drifted values start at their targets on a seed, on a new state (seeded at its first pulse) and on an old save's
     state (no drifted value yet).
   - A state re-seeded after a merge or a split (people moving more than 25% in a year) starts at its targets again.
     This is accepted.
3. **Turmoil raises Accidents and Violence:** a factor `1 + 0.5 × turmoil`, turmoil read as the 0–1 share the census
   already reads in `te_demog_crisis`. It reaches the game through M, under Full only.
4. **The country tab:** not in this change. A TODO comment marks the spot (#894 tracks it).
5. **Germany's excess deaths** (investigation done, 2026-10-11): the per-pop effect behind `dz` +0.6 to +1.0 is severe
   starvation during an in-game famine. The "some of its people" hover names it, with the share of the state's
   people in severe starvation, and calls the rest "other effects on some of its people".

### The carriers of `state_medical_diffusion_add` (proposal)

Communication and medical training spread practice: news of a method, schools that teach it, programs that carry it.
Each carrier is +0.05; none is researched in 1836, so every 1836 state starts at 0.1.

| Technology | Era | Why | Where the line goes |
|---|---|---|---|
| Electric Telegraph (`electric_telegraph`) | 3 | Medical news in days, not months (antisepsis spread by journal and wire) | new INJECT in `te_demog_tech_injections.txt` |
| Modern Nursing (`modern_nursing`) | 3 | Nursing schools carry new practice into hospitals | its INJECT in `te_demog_tech_injections.txt` |
| Radio (`radio`) | 4 | Public-health broadcasting | its INJECT in `common/technology/technologies/modified.txt` (one INJECT per tech) |
| Intergovernmental Organizations (`intergovernmental_organizations`) | 6 | International health organizations (the WHO, 1948) | `era_6.txt` |
| World Wide Web (`world_wide_web`) | 9 | Medical literature and training online | `era_9.txt` |
| Telemedicine (`telemedicine`) | 10 | Specialists reach any clinic | `era_10.txt` |

Half-lives of a gap: 6.6 years at 0.1 (1836), 3.1 at 0.2 (era 3), 2.4 at 0.25 (era 4), 1.4 at 0.4 (era 10).
Alternatives if the owner prefers: Malaria Prevention (era 4, public-health campaigns), Television Broadcasting
(era 7), Digital Education (era 9).

### The Medical Outreach decree (proposal)

`decree_medical_outreach`, "Medical Outreach": doctors and nurses sent to bring a state's practice up to the
country's. Its effects:
- `state_medical_diffusion_add = 0.2`;
- cost 100 authority, as most of the mod's decrees;
- unlocked by Medical Degrees;
- `country_trigger = { te_demog_effects_run = yes }`, which hides it outside Full (vanilla `00_decree.txt`'s header:
  the country trigger decides whether the decree is "permitted/shown in interface");
- `state_trigger`: the state's medicine is behind its targets, or the decree is already issued there (Pollution
  Control's pattern);
- `ai_weight` 0, as the mod's other decrees;
- texture: vanilla's `decree_emergency_relief.dds`, a placeholder. Final-art subject: a doctor's bag over a map pin.

A release comments it out whole (Task 6).

## What the code says (corrections to the brief)

These came out of reading `te_demog_rate_effects.txt`, the walk and the vanilla files. The PR lists them as owner
questions.

1. **The whole state's factor includes the moved lines' on-top family.** The engine gives each pop
   `bare × max(0, 1 + S + own)`, S being the state read. Under Full, S = os + M (os: the state-level lines on top) and
   M = tb − 1 − rep − os(1 − tb) + q·tb. Summed over the state (rep cancels the absorbed per-pop terms):

   engine deaths = target × (1 + os_d + **q_d**) + Σ bare_p × (the pops' own lines on top)

   q_d is `state_demog_ontop_mortality_mult` (Mental Health Awareness −0.05, Biological Immortality −0.2, Mind
   Backups −0.05). So the brief's whole-state factor, ×(1 + os_d), leaves those out.
2. **`te_dg_os_d` is one refresh newer than `te_dg_dz`.** `te_demog_on_top_scales` measures dz over the window just
   run, which ran on the previous refresh's M. Then `te_demog_rates_refresh` overwrites `te_dg_os_d`/`te_dg_q_d` for
   the next window. A state line that changed in between (devastation arriving) would be split by the wrong os, and
   a clamped M or a year's drift in the target breaks the identity too.
   - **Chosen instead:** the walk measures the split. Under Full it sums each pop's bare deaths × `max(0, 1 + S +
     the absorbed terms)` (`te_dg_ed_state`, over the same window as `te_dg_ed`).
   - Whole state: `te_dg_ed_state ÷ te_dg_ed_target`. This holds os, q and the census term's own miss (the clamp,
     the target's drift since the last refresh).
   - Some of its people: `te_dg_ed ÷ te_dg_ed_state`, exactly the pops' own lines.
   - The product is 1 + dz unless dz hit its cap (×5).
3. **Vanilla does have turmoil mortality.** The three `state_turmoil*` static modifiers carry none, as the brief says.
   But `state_mortality_turmoil_mult` ("Mortality per Turmoil") sits on several carriers:
   - Militarized Police +0.004;
   - the Violent Suppression decree +0.02;
   - the Second Amendment +0.005;
   - `ig_trait_wounded_honor` +0.15;
   - about 18 event modifiers (intercommunal violence +0.2/+0.3, anarchist terror attack +0.2).

   Its scaling is unknown and measured at about 0 (growth probe). The walk leaves it out of `te_demog_pop_death_mult`,
   so it is in neither dz nor the census. The new census term is the violence of unrest itself; those lines stay
   engine-applied on top. Not double counted in practice, but not "no turmoil mortality" either.
4. **The first Full step after a seed has no target.** `te_demog_on_top_scales` writes `te_dg_ed_target = 0` and
   `dz = 0`, so the row would read ×1.00 when nothing was measured. The row's gate asks for `te_dg_ed_target > 0`.
5. **`te_dg_rate_clamped` is one flag for births and deaths.** To say why deaths weren't set, the refresh also stores
   `te_dg_rate_clamp_d`: 0 none, 1 the floor (the game's rate can't fall below a fifth of its base), 2 the cap (+300%).
6. **The walk's expected deaths leave out turmoil's and wealth's lines** (`te_demog_pop_death_mult`'s comment). So
   dz, and the "some of its people" part, don't include Private Health Insurance's cut for the wealthy or the
   per-turmoil lines. The hover names only what the walk counts.
7. **Chronic's "Laws and Institutions" is Old Age Pension alone today** (`state_chronic_mortality_mult` −0.05). The
   augmentation laws act through chronic treatment, so they show under Medicine.
8. **"Laws and Institutions" on Accidents and Violence includes the Combustion Engine**, a technology
   (`state_external_mortality_mult` +0.3: motor traffic). The label stays the owner's; the hover's note names it.

**Note (#894, not planned here):** the "some of its people" figure reads the walk's dz. The walk's severe-starvation
death term (+1.0 × bare) was never fitted and may be about 0.6, and the ring applies the step-day snapshot to the
whole year. Fixing either will move the figure.

## Owner decisions (to confirm in the PR)

1. The corrections above, especially 1–2 (the measured split) and 3 (turmoil).
2. The numbers (all proposals):
   - `DIFFUSION_BASE` 0.1, `DIFFUSION_MAX` 1.0, `MEDICINE_SNAP` 0.005;
   - six carriers at +0.05 each, the decree +0.2;
   - `TURMOIL_EXTERNAL_WEIGHT` 0.5: about −0.4 to −0.7 years of life expectancy at full turmoil, by the model at SoL
     8–25 (accidents and violence are a small cause);
   - `DEATHS_ON_TOP_HIGH` ×1.25. People-weighted dz ran +0.05 in 1900 and +0.19 to +0.24 by 2000–2020 in the fast run;
     Germany's famine states ran +0.6 to +1.0. So ×1.25 flags famine-class states and leaves ordinary late-game ones
     neutral.
3. The carriers and the decree (tables above): its name, cost, unlock and AI weight.
4. The section's place: after the overview, before the pyramid (life expectancy and its causes sit together, rule 5).
5. Save size: under Full, 12 more variables per census state (9 under Display only), against about 345 now (+3.5%).
6. Execution: native, with a fresh review of Tasks 3–5 (the risky script) and a whole-branch review at the end, as
   the engine-lines plan.

## Global Constraints

- **Nothing changes outside Full** (owner rule). The census's drift and turmoil reach the game only through M; the
  decree is hidden outside Full (`te_demog_effects_run`, the only reader of the rule besides `te_demog_cohorts_run`:
  `test_only_the_wrappers_read_the_rule`).
- **A release has no census:** `scripts/release/comment_out_census_inputs.py` comments out the new type's carriers and
  the decree whole (Task 6).
- **Generated files are never hand-edited:** `te_demog_generated_values.txt` and `te_demog_generated_effects.txt` come
  from `gen_demographics.py`; `gen_demographics.py --check` stays clean.
- **The GUI reads variables and cheap script values only** (a `.gui` re-evaluates every frame); nothing walks. A read
  of a missing variable logs every frame, so every figure sits under a scripted-GUI gate (gotchas #14, #23).
- **No `TimedModifier.GetIcon` comparisons** (gui_modding_guide gotcha #40). The section shows no modifiers.
- **Script literals:** at most five decimals. Set a variable from a script value with `set_variable`'s inline
  `value = { ... }` block, never `change_variable`'s operands (`scripting_best_practices.md`, the paris-commune note).
- **Each changed `.txt`/`.yml` keeps exactly one UTF-8 BOM and tab indentation** (`scripts/format_paradox_tabs.py
  --check`).
- **Loc:** add keys to the existing files named in each task, run `python3 organize_loc.py`, commit what it moves;
  `organize_loc.py --check` stays clean. Loc uses `#b X#!`, never `[b]`. Don't touch the two strings PR #902 changes
  (`te_demog_st_census_tt` and the country tab's census tooltip).
- **Python:** 3.11-compatible (no PEP 701 f-strings: `grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>`).
- **Running Python in a worktree:** `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python` with
  `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent
  VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`. No `/reload` from a worktree.
- **Commits:** by path, never `git commit -a`; end each message with the session's `Co-Authored-By` and
  `Claude-Session` lines.

## Review Focus

1. **An old save, or a census state from before this build.** It has no `te_dg_acc` or `te_dg_in_*`.
   - Expected: its next step starts medicine at the targets (no sudden lag), and until then the section shows "after
     the next count" with no per-frame "Failed to fetch variable".
   - Pinned by Task 4's `test_an_old_census_starts_at_its_targets` and Task 8's `test_every_read_sits_under_its_gate`.
2. **The first Full step after a seed, and any state outside Full.**
   - Expected: no ×1.00 that wasn't measured. Outside Full the row is absent; on the first Full step it reads "after
     the next count".
   - Pinned by Task 7's `test_the_on_top_gate_needs_a_measured_target`.
3. **A state whose state-level lines changed between steps, or whose census term was clamped.**
   - Expected: the split still multiplies to the scale, and the hover says which clamp bit.
   - Pinned by Task 5's `test_the_split_multiplies_to_the_scale` and `test_the_deaths_clamp_records_its_side`.
4. **A conquered state, or a new health law.** The target jumps.
   - Expected: the drifted values move `r` of the gap per step and never overshoot. A seed doesn't lag.
   - Pinned by Task 3's `test_each_step_closes_its_share_of_the_gap` and Task 4's
     `test_the_step_drifts_medicine_before_its_rates`.
5. **A release build.**
   - Expected: the six carrier lines and the decree are commented out, and the decree isn't left as an empty shell
     with a texture and a cost.
   - Pinned by Task 6's `test_the_census_decree_is_commented_whole`.

---

## File structure

| File | Change | Responsibility |
|---|---|---|
| `scripts/analysis/demographics_params.py` | modify | `CAUSE_FACTORS`, `CAUSE_SHORT`, `TURMOIL_EXTERNAL_WEIGHT`, `DIFFUSION_*`, `MEDICINE_SNAP`, `MEDICAL_OUTREACH_DIFFUSION`, `DEATHS_ON_TOP_HIGH`; `DEMOG_TYPES` gains the diffusion type |
| `scripts/analysis/demographics_model.py` | modify | `Inputs.turmoil`, `Inputs.medicine`, `Ring.medicine`; `medicine_targets`, `diffusion`, `medicine_drift`, `cause_factors`; `medicine`, `cause_multipliers`, `seed`, `step` |
| `common/modifier_type_definitions/demographics_modifier_types.txt` | modify | `state_medical_diffusion_add` |
| `common/technology/technologies/te_demog_tech_injections.txt`, `modified.txt`, `era_6.txt`, `era_9.txt`, `era_10.txt` | modify | the six carriers |
| `scripts/generators/gen_demographics.py` | modify | factors, targets, the inputs store, the drift effects, the multipliers as products, constants; the walk's on-top sums and `te_demog_pop_state_death_mult` |
| `common/script_values/te_demog_generated_values.txt`, `common/scripted_effects/te_demog_generated_effects.txt` | regenerated | — |
| `common/scripted_effects/te_demog_effects.txt` | modify | prepare/seed/step call the new effects; the walk stores `te_dg_ed_state`, `te_dg_sev_share`; the header inventory |
| `common/scripted_effects/te_demog_rate_effects.txt` | modify | `te_dg_rate_clamp_d` |
| `common/script_values/te_debug_demog_values.txt`, `common/scripted_effects/te_debug_demog_effects.txt` | modify | guards on the mult reads; option l logs the diffusion rate; option n logs the split |
| `common/decrees/extra_decrees.txt` | modify | `decree_medical_outreach` |
| `common/script_values/te_demog_values.txt`, `common/scripted_triggers/te_demog_triggers.txt` | modify | `te_demog_medicine_gap`, `te_demog_medicine_behind` |
| `scripts/release/comment_out_census_inputs.py`, `test_release_census_inputs.py` | modify | a decree left with no effect goes whole |
| `common/script_values/te_demog_display_values.txt` | modify | the moving flags, the on-top figures and code |
| `common/scripted_guis/te_demog_sguis.txt` | modify | `te_demog_state_causes_sgui`, `_full_sgui`, `_on_top_sgui` |
| `common/game_concepts/extra_concepts.txt` | modify | `concept_health_care_access` |
| `gui/te_demographics_widgets.gui` | modify | `te_state_demog_causes`; its place in `te_state_demog_content`; the country tab's TODO |
| `localization/english/te_miscellaneous_l_english.yml`, `te_modifiers_l_english.yml`, `te_decrees_l_english.yml`, `te_concepts_l_english.yml` | modify | the section, the type, the decree, the concept |
| `scripts/analysis/demographics_harness.py` | modify | `fidelity` runs the model on the step's stored inputs |
| tests: `test_demographics_model.py`, `test_demographics_modifiers.py`, `test_gen_demographics.py`, `test_demographics_registry.py`, `test_demographics_harness.py`, `test_release_census_inputs.py` | modify | below |
| docs: `docs/systems/mod_systems.md`, `docs/guides/python_tools.md`, `docs/player_guide/08-states.md`, `06-politics.md` (+ PDF) | modify | Task 10 |

---

### Task 1: The model: factors, medicine that drifts, turmoil

**Files:**
- Modify: `scripts/analysis/demographics_params.py` (after `CROWDING_INFECTION_MAX`, and `DEMOG_TYPES`)
- Modify: `scripts/analysis/demographics_model.py` (`Inputs`, `Ring`, `medicine`, `cause_multipliers`, `seed`, `step`)
- Test: `test_demographics_model.py` (new `class TestCausesOfDeath`)

**Interfaces:**
- Produces:
  - Parameters: `P.CAUSE_FACTORS: dict[str, tuple[str, ...]]`, `P.CAUSE_SHORT: dict[str, str]`,
    `P.TURMOIL_EXTERNAL_WEIGHT`, `P.DIFFUSION_TYPE = "state_medical_diffusion_add"`, `P.DIFFUSION_BASE`,
    `P.DIFFUSION_MAX`, `P.MEDICINE_SNAP`, `P.MEDICAL_OUTREACH_DIFFUSION`, `P.DEATHS_ON_TOP_HIGH`.
  - Inputs and ring: `M.Inputs.turmoil: float` (0–1), `M.Inputs.medicine: dict | None` (keys `"access"`,
    `"infection"`, `"maternal"`, `"chronic"`), `M.Ring.medicine: dict | None`.
  - Functions: `M.medicine_targets(inp) -> dict`, `M.diffusion(inp) -> float`, `M.medicine_drift(prev, inp) -> dict`,
    `M.cause_factors(inp) -> {cause: {factor: float}}`.

- [ ] **Step 1: Write the failing tests**

```python
class TestCausesOfDeath(unittest.TestCase):
    """The Causes of Death plan (2026-10-11): each cause's multiplier is the product of P.CAUSE_FACTORS' factors;
    health-care access and the treatments drift toward their targets at each census step; turmoil raises
    accidents and violence."""

    MODS = {P.ACCESS_TYPE: 0.3, P.TREATMENT_TYPE["infection"]: 0.4, P.TREATMENT_TYPE["maternal"]: 0.35,
            P.TREATMENT_TYPE["chronic"]: 0.1, "state_external_mortality_mult": -0.1,
            "state_work_mortality_mult": 0.1, "state_chronic_mortality_mult": -0.05}

    def test_factors_multiply_to_each_multiplier(self):
        for sol, lit, turm, crowd in ((3, 0.1, 0.0, 0.0), (6.5, 0.2, 0.4, 0.05), (20, 0.5, 1.0, 0.6), (40, 1.0, 0.2, 0.0)):
            inp = M.Inputs(sol=sol, literacy=lit, turmoil=turm, crowding=crowd, mods=dict(self.MODS))
            factors, mult = M.cause_factors(inp), M.cause_multipliers(inp)
            self.assertEqual(list(factors), list(P.CAUSE_FACTORS))
            for cause, fs in factors.items():
                self.assertEqual(tuple(fs), P.CAUSE_FACTORS[cause])
                self.assertAlmostEqual(math.prod(fs.values()), mult[cause], places=12, msg=cause)

    def test_turmoil_raises_accidents_and_violence_only(self):
        calm = M.cause_multipliers(M.Inputs(sol=12, literacy=0.3))
        unrest = M.cause_multipliers(M.Inputs(sol=12, literacy=0.3, turmoil=1.0))
        self.assertAlmostEqual(unrest["external"], calm["external"] * (1 + P.TURMOIL_EXTERNAL_WEIGHT))
        for cause in ("infection", "work", "maternal", "chronic"):
            self.assertEqual(unrest[cause], calm[cause], cause)
        # read as a 0-1 share
        self.assertEqual(M.cause_multipliers(M.Inputs(sol=12, literacy=0.3, turmoil=1.7))["external"],
                         unrest["external"])

    def test_a_seed_starts_medicine_at_its_targets(self):
        inp = M.Inputs(sol=12, literacy=0.3, mods=dict(self.MODS))
        ring = M.seed(inp, 1836, 1e6)
        self.assertEqual(ring.medicine, M.medicine_targets(inp))
        self.assertEqual(M.medicine_drift(None, inp), M.medicine_targets(inp))

    def test_medicine_moves_a_share_of_the_gap_each_step(self):
        inp0 = M.Inputs(sol=12, literacy=0.3)
        ring = M.seed(inp0, 1836, 1e6)
        inp1 = M.Inputs(sol=12, literacy=0.3, mods=dict(self.MODS))
        M.step(ring, inp1, 1837)
        r = P.DIFFUSION_BASE
        self.assertAlmostEqual(ring.medicine["access"], P.BASE_ACCESS + r * 0.3)
        self.assertAlmostEqual(ring.medicine["infection"], r * 0.4)
        self.assertAlmostEqual(ring.medicine["maternal"], r * 0.35)
        # the step's rates use the drifted values, not the targets
        drifted = M.cause_multipliers(dataclasses.replace(inp1, medicine=ring.medicine))
        at_target = M.cause_multipliers(inp1)
        self.assertGreater(drifted["infection"], at_target["infection"])

    def test_diffusion_rises_with_its_type_and_is_capped(self):
        self.assertAlmostEqual(M.diffusion(M.Inputs()), P.DIFFUSION_BASE)
        self.assertAlmostEqual(M.diffusion(M.Inputs(mods={P.DIFFUSION_TYPE: 0.3})), P.DIFFUSION_BASE + 0.3)
        self.assertEqual(M.diffusion(M.Inputs(mods={P.DIFFUSION_TYPE: 5.0})), P.DIFFUSION_MAX)

    def test_a_value_near_its_target_takes_it(self):
        inp = M.Inputs(mods={P.ACCESS_TYPE: 0.3})
        target = M.medicine_targets(inp)
        prev = dict(target, access=target["access"] - 0.004 / (1 - P.DIFFUSION_BASE))
        self.assertEqual(M.medicine_drift(prev, inp)["access"], target["access"])
        far = dict(target, access=target["access"] - 0.2)
        self.assertLess(M.medicine_drift(far, inp)["access"], target["access"])

    def test_constant_inputs_keep_the_calibration(self):
        # medicine at its targets from the seed on: run_constant (the anchors' equilibria) is what it was
        inp = M.Inputs(sol=14, literacy=0.4, mods=dict(self.MODS))
        _ring, last = M.run_constant(inp, years=60)
        qf, qm, _mmr = M.group_rates(inp)
        self.assertAlmostEqual(last["e0"], (M.life_table(qf)["e0"] + M.life_table(qm)["e0"]) / 2, places=9)
```

Add `import dataclasses` and `import math` at the top of `test_demographics_model.py` if missing.

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_model.TestCausesOfDeath`
Expected: ERROR, `module 'demographics_params' has no attribute 'CAUSE_FACTORS'`.

- [ ] **Step 3: Add the parameters** (after `CROWDING_INFECTION_MAX`)

```python
# ---- Causes of Death (owner, 2026-10-11; docs/superpowers/plans/2026-10-11-demographics-causes-of-death.md) ----
# Each cause's multiplier is the product of these factors, in this order. The generator writes one script value per
# factor (te_demog_f_<cause>_<factor>) and each te_demog_mult_<cause> as their product; the state subtab's Causes of
# Death section reads the same values, so the display and the census can't disagree.
CAUSE_FACTORS = {
    "infection": ("medicine", "sol", "poverty", "literacy", "crowding"),
    "work": ("laws",),
    "external": ("laws", "turmoil"),
    "maternal": ("medicine",),
    "chronic": ("medicine", "laws", "sol"),
}
# Short names of the state variables (te_dg_m_<short>, te_dg_trt_<short>, te_dg_in_<short>).
CAUSE_SHORT = {"infection": "inf", "work": "work", "external": "ext", "maternal": "mat", "chronic": "chr"}
# Turmoil (owner, 2026-10-11): accidents and violence x (1 + this x the state's turmoil, a 0-1 share). Vanilla's
# state_turmoil modifiers carry no mortality; state_mortality_turmoil_mult's carriers (Violent Suppression, Militarized
# Police, events) stay engine lines on top, which the walk leaves out (scaling unknown, measured about 0).
TURMOIL_EXTERNAL_WEIGHT = 0.5
# Medicine spreads (owner, 2026-10-11): at each census step health-care access and each cause's treatment move this
# share of the gap to their targets: DIFFUSION_BASE everywhere, plus DIFFUSION_TYPE (communication and medical-training
# technologies, the Medical Outreach decree), at most DIFFUSION_MAX. Within MEDICINE_SNAP of its target a value takes
# the target. A seed, a new state and an old save's state start at their targets.
DIFFUSION_TYPE = "state_medical_diffusion_add"
DIFFUSION_BASE = 0.1
DIFFUSION_MAX = 1.0
MEDICINE_SNAP = 0.005
MEDICAL_OUTREACH_DIFFUSION = 0.2   # decree_medical_outreach's line (a test pins the decree to it)
DEATHS_ON_TOP_HIGH = 1.25          # 1 + te_dg_dz at or above this reads red on the state subtab
```

Change `DEMOG_TYPES = DEMOG_MORTALITY_TYPES + DEMOG_FERTILITY_TYPES` to
`DEMOG_TYPES = DEMOG_MORTALITY_TYPES + DEMOG_FERTILITY_TYPES + (DIFFUSION_TYPE,)`.

- [ ] **Step 4: The model**

In `demographics_model.py`: import `replace` from `dataclasses`. Add to `Inputs` (last, with defaults):

```python
    turmoil: float = 0.0                 # 0..1: the state's turmoil at the step (te_dg_in_turm)
    medicine: dict | None = None         # the drifted access and treatments the step holds; None = at the targets
```

Add `medicine: dict | None = None` to `Ring` (after `total`). Replace `medicine` and `cause_multipliers`, and add the
new functions after `plain_multiplier`:

```python
def medicine_targets(inp):
    """Where medicine is heading: {"access", and each of P.MEDICINE_CAUSES' treatment}, clamped as the census
    clamps them (te_demog_access_target, te_demog_treatment_target_<cause>)."""
    out = {"access": clamp(P.BASE_ACCESS + inp.mods.get(P.ACCESS_TYPE, 0.0), 0.0, 1.0)}
    for cause in P.MEDICINE_CAUSES:
        out[cause] = clamp(inp.mods.get(P.TREATMENT_TYPE[cause], 0.0), 0.0, P.TREATMENT_CAP[cause])
    return out


def diffusion(inp):
    """The share of the gap medicine closes at a census step (te_demog_medical_diffusion)."""
    return clamp(P.DIFFUSION_BASE + inp.mods.get(P.DIFFUSION_TYPE, 0.0), 0.0, P.DIFFUSION_MAX)


def medicine_drift(prev, inp):
    """One census step of the drifted medicine (te_demog_medicine_drift): each value moves diffusion(inp) of the way
    to its target and takes the target once within MEDICINE_SNAP of it. prev None (a seed, a new state, an old save's
    state) starts at the targets. The order of operations is the script's: (target - prev) x rate + prev."""
    target = medicine_targets(inp)
    if prev is None:
        return dict(target)
    rate = diffusion(inp)
    out = {}
    for key, t in target.items():
        x = (t - prev[key]) * rate + prev[key]
        out[key] = t if -P.MEDICINE_SNAP < t - x < P.MEDICINE_SNAP else x
    return out


def medicine(inp, cause):
    """1 - access x treatment for one of P.MEDICINE_CAUSES, at the drifted values the step holds (inp.medicine) or,
    with none, at the targets (modifier-types design, Decision 1)."""
    m = inp.medicine if inp.medicine is not None else medicine_targets(inp)
    return 1 - m["access"] * m[cause]


def cause_factors(inp):
    """{cause: {factor: value}} in P.CAUSE_FACTORS' order: the script's te_demog_f_<cause>_<factor>."""
    def one(factor, cause):
        if factor == "medicine":
            return medicine(inp, cause)
        if factor == "sol":
            return lerp_sol(inp.sol, 1.0, P.SOL_INFECTION_AT_HIGH if cause == "infection" else P.SOL_CHRONIC_AT_HIGH)
        if factor == "poverty":
            return poverty_infection(inp.sol)
        if factor == "literacy":
            return 1 - P.LITERACY_INFECTION_WEIGHT * inp.literacy
        if factor == "crowding":
            return 1 + min(P.CROWDING_INFECTION_PER_PULL * inp.crowding, P.CROWDING_INFECTION_MAX)
        if factor == "laws":
            return plain_multiplier(inp, cause)
        if factor == "turmoil":
            return 1 + P.TURMOIL_EXTERNAL_WEIGHT * clamp(inp.turmoil, 0.0, 1.0)
        raise KeyError(factor)
    return {cause: {f: one(f, cause) for f in factors} for cause, factors in P.CAUSE_FACTORS.items()}


def cause_multipliers(inp):
    """One multiplier per cause from the state's inputs; 1.0 at the base (§2.4): the product of its factors, in
    P.CAUSE_FACTORS' order, as the script's te_demog_mult_<cause> computes it."""
    out = {}
    for cause, factors in cause_factors(inp).items():
        m = 1.0
        for v in factors.values():
            m *= v
        out[cause] = m
    return out
```

In `seed`, after `ring = Ring(year=year)`: `ring.medicine = medicine_targets(inp)`.

In `step`, as the first lines of the `if rates is None:` branch:

```python
        # medicine spreads (the Causes of Death plan): the drifted values move, then the year's rates use them
        ring.medicine = medicine_drift(ring.medicine, inp)
        inp = replace(inp, medicine=ring.medicine)
```

Update `step`'s docstring: "medicine drifts before the rates (te_demog_medicine_drift before te_demog_prepare)".

- [ ] **Step 5: Run the model's tests**

Run: `.venv/bin/python -m unittest test_demographics_model test_demographics_harness`
Expected: OK. The harness's anchors (`medicine`, `fertility`, `sketch`) run on equilibria, where medicine is at its
targets, so none moves.

- [ ] **Step 6: Commit**: "Demographics model: causes of death as factor products, medicine that drifts, turmoil".

---

### Task 2: The spread of medicine as a modifier type, on six technologies

**Files:**
- Modify: `common/modifier_type_definitions/demographics_modifier_types.txt`
- Modify: `common/technology/technologies/te_demog_tech_injections.txt`, `modified.txt` (`INJECT:radio`), `era_6.txt`
  (`intergovernmental_organizations`), `era_9.txt` (`world_wide_web`), `era_10.txt` (`telemedicine`)
- Modify: `localization/english/te_modifiers_l_english.yml`, `te_concepts_l_english.yml`
- Modify: `common/game_concepts/extra_concepts.txt`
- Test: `test_demographics_modifiers.py`, `test_demographics_registry.py` (`TestModifierTypes`)

**Interfaces:**
- Consumes: `P.DIFFUSION_TYPE`, `P.DIFFUSION_BASE` (Task 1).
- Produces: the type on six carriers, read by `DM.load_carriers()` (it reads `P.DEMOG_TYPES`);
  `concept_health_care_access`.

- [ ] **Step 1: Write the failing tests**

In `test_demographics_modifiers.py`, `TestCarriersInTheGameFiles`: add `P.DIFFUSION_TYPE: {"technology"}` to
`test_each_type_sits_where_its_design_puts_it`'s `allowed`. (The decree carries the type too, but `load_carriers`
reads only technologies, laws and institutions; Task 6 pins the decree.) Then:

```python
    def test_medicine_spreads_from_a_tenth_to_two_fifths(self):
        """The Causes of Death plan: communication and medical-training techs carry the spread of medicine, +0.05 each,
        so a state closes 10% of the gap a year in 1836 and 40% with all six."""
        carried = {c.key: c.value for c in self.carriers if c.type == P.DIFFUSION_TYPE}
        self.assertEqual(set(carried), {"electric_telegraph", "modern_nursing", "radio",
                                        "intergovernmental_organizations", "world_wide_web", "telemedicine"})
        t = DM.totals(self.carriers, techs=set(carried))
        self.assertAlmostEqual(P.DIFFUSION_BASE + t[P.DIFFUSION_TYPE], 0.4)
        self.assertAlmostEqual(P.DIFFUSION_BASE + DM.totals(self.carriers)[P.DIFFUSION_TYPE], P.DIFFUSION_BASE)
```

In `test_demographics_registry.py`, `TestModifierTypes`:

```python
    def test_the_spread_of_medicine_is_registered_named_and_new(self):
        text, loc = _text(TYPES_FILE), _text(MODIFIERS_LOC)
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        body = _block(text, P.DIFFUSION_TYPE)
        for line in ("script_only = yes", "percent = yes", "color = good"):
            self.assertIn(line, body)
        self.assertRegex(loc, rf"(?m)^ {P.DIFFUSION_TYPE}:0 \"")
        self.assertRegex(loc, rf"(?m)^ {P.DIFFUSION_TYPE}_desc:0 \"")
        self.assertNotIn(P.DIFFUSION_TYPE, engine)
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_modifiers test_demographics_registry.TestModifierTypes`
Expected: FAIL (no carriers; `te_demog_medical_diffusion` type not found).

- [ ] **Step 3: The type** (end of `demographics_modifier_types.txt`)

```
# Medicine spreads (the Causes of Death plan, owner 2026-10-11): the share of the gap between a state's health-care
# access and treatments and their targets that each census step closes, on top of 10% everywhere
# (te_demog_medical_diffusion). On communication and medical-training techs and the Medical Outreach decree.
# Read only by the census; a release comments its carriers out (scripts/release/comment_out_census_inputs.py).
state_medical_diffusion_add = {
	color = good
	percent = yes
	decimals = 0
	script_only = yes
}
```

- [ ] **Step 4: The carriers**

`te_demog_tech_injections.txt`: add `state_medical_diffusion_add = 0.05` inside `INJECT:modern_nursing`'s `modifier`,
and after it:

```
# Medicine spreads faster with communication and medical training (the Causes of Death plan): the census's share of the
# gap closed each year, 10% everywhere plus 5% for each of Electric Telegraph, Modern Nursing, Radio (modified.txt),
# Intergovernmental Organizations, World Wide Web and Telemedicine (in their own definitions).
INJECT:electric_telegraph = {
	modifier = {
		state_medical_diffusion_add = 0.05
	}
}
```

`modified.txt`, inside `INJECT:radio`'s `modifier`:
`state_medical_diffusion_add = 0.05	# the census's spread of medicine (te_demog_tech_injections.txt)`.
`era_6.txt` `intergovernmental_organizations`, `era_9.txt` `world_wide_web`, `era_10.txt` `telemedicine` (beside its
chronic treatment): `state_medical_diffusion_add = 0.05`, with a one-line comment
`# the census's spread of medicine (the Causes of Death plan)` above it.

- [ ] **Step 5: The names, and the concept they use**

`te_modifiers_l_english.yml`, beside `state_health_care_access_add`:

```
 state_medical_diffusion_add:0 "Spread of Medicine"
 state_medical_diffusion_add_desc:0 "How fast new medicine reaches each state: the share of the gap between its [concept_health_care_access] and treatments and the best the country has that closes at each yearly count. 10% everywhere; communications and medical training add more. Used by the census on the Demographics tab."
```

The concept (a new game term in the section's first label, rule 3): `common/game_concepts/extra_concepts.txt` gets
`concept_health_care_access = {}` with the comment
`# the census's health-care access (docs/systems/mod_systems.md § Demographics, Causes of Death)`.
`te_concepts_l_english.yml` (organize_loc files the four-token name in `te_miscellaneous_l_english.yml`):

```
 concept_health_care_access:0 "Health Care Access"
 concept_health_care_access_desc:0 "How many of a state's people can reach a doctor, a nurse or a hospital, from 0% to 100%. Medicine saves lives only as far as it reaches: a treatment that prevents half the deaths from infection prevents a fifth of them where access is 40%. Markets and charity give 40% everywhere; a health law adds more with each level of the Ministry of Health, in incorporated states. A change reaches a state over years, a share at each yearly count. Used by the census on the Demographics tab."
```

Add to `TestModifierTypes`:

```python
    def test_health_care_access_is_a_concept(self):
        self.assertIn("concept_health_care_access = {}",
                      _text(ROOT / "common" / "game_concepts" / "extra_concepts.txt"))
```

- [ ] **Step 6: Run the tests, then commit**: "Demographics: the spread of medicine, on six technologies".

Run: `.venv/bin/python -m unittest test_demographics_modifiers test_demographics_registry.TestModifierTypes`, then
`python3 organize_loc.py` and `python3 organize_loc.py --check`.
Expected: OK. Commit what organize_loc moved with the rest.

---

### Task 3: The generator: factors, targets, the step's inputs, the drift

**Files:**
- Modify: `scripts/generators/gen_demographics.py` (`multipliers`, `constants`, `render_effects`)
- Regenerate: `common/script_values/te_demog_generated_values.txt`, `common/scripted_effects/te_demog_generated_effects.txt`
- Test: `test_gen_demographics.py`, `test_demographics_registry.py` (`TestCauseMultipliersScript` rewritten as
  `TestCauseFactorsScript`; new `TestMedicineDriftScript`)

**Interfaces:**
- Consumes: `P.CAUSE_FACTORS`, `P.CAUSE_SHORT`, `P.DIFFUSION_*`, `P.MEDICINE_SNAP`, `P.TURMOIL_EXTERNAL_WEIGHT` (Task 1).
- Produces, in the generated values (state scope):
  - targets: `te_demog_access_target`, `te_demog_treatment_target_<cause>` (infection, maternal, chronic),
    `te_demog_medical_diffusion`;
  - factors: `te_demog_f_<cause>_<factor>` for every `P.CAUSE_FACTORS` entry, and `te_demog_f_<cause>_medicine_target`;
  - `te_demog_mult_<cause>`, now the product of its factors;
  - constants: `te_demog_k_medicine_snap`, `_medicine_snap_neg`, `_deaths_on_top_high`, `_base_access`,
    `_maternal_base`.
- Produces, in the generated effects (THIS = a state):
  - `te_demog_cause_inputs_store`: sets `te_dg_in_ext`, `te_dg_in_work`, `te_dg_in_chr`, `te_dg_in_turm`,
    `te_dg_in_crowd`;
  - `te_demog_medicine_at_target`: sets `te_dg_acc`, `te_dg_trt_inf`, `te_dg_trt_mat`, `te_dg_trt_chr`;
  - `te_demog_medicine_drift`;
  - `te_demog_medicine_drift_one = { VAR = <variable> TARGET = <script value> }`.
- The factors read only stored variables: `te_dg_sol`, `te_dg_lit`, `te_dg_acc`, `te_dg_trt_*`, `te_dg_in_*`.

- [ ] **Step 1: Write the failing generator tests** (`test_gen_demographics.py`, `TestGenerated`; replace
  `test_medicine_reads_access_and_the_causes_treatment`)

```python
    def _value(self, name):
        return self.values.split(f"\n{name} = {{", 1)[1].split("\n}\n", 1)[0]

    def test_each_multiplier_is_the_product_of_its_factors(self):
        for cause, factors in P.CAUSE_FACTORS.items():
            lines = [line.strip() for line in self._cause(cause).strip().splitlines()]
            want = [f"value = te_demog_f_{cause}_{factors[0]}"]
            want += [f"multiply = te_demog_f_{cause}_{f}" for f in factors[1:]]
            if cause == "maternal":
                want.append(f"multiply = {P.MATERNAL_PER_100K_BIRTHS}")
            self.assertEqual(lines, want, cause)

    def test_factors_read_only_what_the_step_stored(self):
        # the hover multiplies to the row between steps only if no factor reads a live modifier, turmoil or crowding
        for cause, factors in P.CAUSE_FACTORS.items():
            for f in factors:
                body = self._value(f"te_demog_f_{cause}_{f}")
                with self.subTest(cause=cause, factor=f):
                    self.assertNotIn("modifier:", body)
                    self.assertNotIn("has_modifier", body)
                    self.assertIsNone(re.search(r"(?<![\w:])turmoil\b", body))
                    self.assertRegex(body, r"var:te_dg_(sol|lit|acc|trt_\w+|in_\w+)\b")

    def test_the_targets_read_the_types(self):
        self.assertIn(f"value = modifier:{P.ACCESS_TYPE}", self._value("te_demog_access_target"))
        self.assertIn(f"value = modifier:{P.DIFFUSION_TYPE}", self._value("te_demog_medical_diffusion"))
        for cause in P.MEDICINE_CAUSES:
            self.assertIn(f"value = modifier:{P.TREATMENT_TYPE[cause]}",
                          self._value(f"te_demog_treatment_target_{cause}"))

    def test_the_inputs_store_reads_each_plain_type(self):
        body = self.effects.split("te_demog_cause_inputs_store = {", 1)[1].split("\n}\n", 1)[0]
        for cause, types in P.MORTALITY_TYPES.items():
            for t in types:
                self.assertIn(f"add = modifier:{t}", body)
            self.assertIn(f"name = te_dg_in_{P.CAUSE_SHORT[cause]}", body)
        self.assertIn("value = turmoil", body)
        self.assertIn("var:migration_crowding_mult_applied", body)
```

`test_causes_read_the_types_not_the_owners_techs_or_laws` and `test_every_type_is_read_in_state_scope` keep passing
(the targets read the types in state scope); keep them.

- [ ] **Step 2: Write the failing script tests** (`test_demographics_registry.py`: replace `TestCauseMultipliersScript`)

```python
def _stored(inp):
    """The variables a step stores for `inp`: te_demog_cause_inputs_store's, and the drifted medicine (inp.medicine,
    or the targets)."""
    med = inp.medicine if inp.medicine is not None else demographics_model.medicine_targets(inp)
    out = {"te_dg_sol": float(inp.sol), "te_dg_lit": float(inp.literacy), "te_dg_acc": med["access"],
           "te_dg_in_turm": min(max(inp.turmoil, 0.0), 1.0), "te_dg_in_crowd": inp.crowding}
    for cause in P.MEDICINE_CAUSES:
        out[f"te_dg_trt_{P.CAUSE_SHORT[cause]}"] = med[cause]
    for cause, types in P.MORTALITY_TYPES.items():
        out[f"te_dg_in_{P.CAUSE_SHORT[cause]}"] = sum(inp.mods.get(t, 0.0) for t in types)
    return out


def _mod_fixtures(inp):
    """The engine reads the step makes: every census type, turmoil."""
    out = {f"modifier:{t}": inp.mods.get(t, 0.0) for t in P.DEMOG_TYPES}
    out["turmoil"] = inp.turmoil
    return out


class TestCauseFactorsScript(unittest.TestCase):
    """te_demog_f_<cause>_<factor> and te_demog_mult_<cause> (generated) against demographics_model.cause_factors,
    on the step's stored inputs (the Causes of Death plan)."""

    CASES = [
        {},
        {P.TREATMENT_TYPE["infection"]: 0.81, P.TREATMENT_TYPE["maternal"]: 0.9, P.TREATMENT_TYPE["chronic"]: 0.59},
        {P.ACCESS_TYPE: 0.6, P.TREATMENT_TYPE["infection"]: 0.81, P.TREATMENT_TYPE["maternal"]: 2.0,
         P.TREATMENT_TYPE["chronic"]: 0.3, "state_chronic_mortality_mult": -0.05},
        {P.ACCESS_TYPE: 1.5, P.TREATMENT_TYPE["infection"]: 0.3},
        {"state_work_mortality_mult": -0.9, "state_external_mortality_mult": -0.1},
        {"state_work_mortality_mult": 0.1, "state_external_mortality_mult": 0.3, "state_chronic_mortality_mult": -0.9},
    ]
    STATES = ((3, 0.1, 0.0, 0.0), (6.5, 0.2, 0.4, 0.05), (8, 0.0, 1.0, 0.0), (20, 0.5, 0.2, 0.6), (40, 1.0, 0.0, 0.0))

    def _eng(self, inp):
        eng = _Engine({})
        eng.vars.update(_stored(inp))
        return eng

    def test_each_factor_matches_the_model(self):
        for mods in self.CASES:
            for sol, lit, turm, crowd in self.STATES:
                inp = demographics_model.Inputs(sol=sol, literacy=lit, turmoil=turm, crowding=crowd, mods=dict(mods))
                eng = self._eng(inp)
                for cause, factors in demographics_model.cause_factors(inp).items():
                    for f, want in factors.items():
                        with self.subTest(mods=mods, sol=sol, cause=cause, factor=f):
                            got = eng.value(eng._tree(eng.values, f"te_demog_f_{cause}_{f}"))
                            self.assertAlmostEqual(got, want, places=9)

    def test_each_multiplier_matches_the_model(self):
        for mods in self.CASES:
            for sol, lit, turm, crowd in self.STATES:
                inp = demographics_model.Inputs(sol=sol, literacy=lit, turmoil=turm, crowding=crowd, mods=dict(mods))
                eng, want = self._eng(inp), demographics_model.cause_multipliers(inp)
                for cause in P.CAUSE_FACTORS:
                    scale = P.MATERNAL_PER_100K_BIRTHS if cause == "maternal" else 1.0
                    with self.subTest(mods=mods, sol=sol, cause=cause):
                        got = eng.value(eng._tree(eng.values, f"te_demog_mult_{cause}"))
                        self.assertAlmostEqual(got, want[cause] * scale, places=6)

    def test_the_factors_read_the_drifted_medicine(self):
        inp = demographics_model.Inputs(sol=12, literacy=0.3, mods=dict(self.CASES[2]),
                                        medicine={"access": 0.45, "infection": 0.2, "maternal": 0.3, "chronic": 0.05})
        eng = self._eng(inp)
        for cause in P.MEDICINE_CAUSES:
            got = eng.value(eng._tree(eng.values, f"te_demog_f_{cause}_medicine"))
            self.assertAlmostEqual(got, demographics_model.medicine(inp, cause), places=9)
        # the target is today's, read live
        eng.fixtures.update(_mod_fixtures(inp))
        target = demographics_model.medicine(dataclasses.replace(inp, medicine=None), "infection")
        got = eng.value(eng._tree(eng.values, "te_demog_f_infection_medicine_target"))
        self.assertAlmostEqual(got, target, places=9)

    def test_the_inputs_store_takes_the_steps_reads(self):
        inp = demographics_model.Inputs(sol=12, literacy=0.3, turmoil=1.4, mods=dict(self.CASES[5]))
        eng = _Engine(_mod_fixtures(inp))
        eng.call("te_demog_cause_inputs_store")
        want = _stored(inp)
        for name in ("te_dg_in_ext", "te_dg_in_work", "te_dg_in_chr", "te_dg_in_turm", "te_dg_in_crowd"):
            self.assertAlmostEqual(eng.vars[name], want[name], places=9, msg=name)
        self.assertEqual(eng.vars["te_dg_in_turm"], 1.0, "turmoil is a 0-1 share")

    def test_crowding_needs_both_the_modifier_and_the_stored_multiplier(self):
        # a save from before the stored multiplier (the modifier alone), and a variable outliving its modifier,
        # store no crowding (review I1 of the crowding term)
        for label, modifier, variable in (("both", True, True), ("modifier only", True, False),
                                          ("variable only", False, True)):
            eng = _Engine(_mod_fixtures(demographics_model.Inputs()))
            if modifier:
                eng.modifiers["migration_crowding"] = 1.5
            if variable:
                eng.vars["migration_crowding_mult_applied"] = 1.5
            eng.call("te_demog_cause_inputs_store")
            want = 1.5 * P.MIGRATION_CROWDING_PULL_PER_MULT if label == "both" else 0.0
            with self.subTest(label):
                self.assertAlmostEqual(eng.vars["te_dg_in_crowd"], want, places=9)


class TestMedicineDriftScript(unittest.TestCase):
    """te_demog_medicine_drift and te_demog_medicine_at_target (generated) against demographics_model.medicine_drift."""

    INP = demographics_model.Inputs(mods={P.ACCESS_TYPE: 0.3, P.TREATMENT_TYPE["infection"]: 0.4,
                                          P.TREATMENT_TYPE["maternal"]: 0.35, P.TREATMENT_TYPE["chronic"]: 0.1})
    VARS = {"access": "te_dg_acc", **{c: f"te_dg_trt_{P.CAUSE_SHORT[c]}" for c in P.MEDICINE_CAUSES}}

    def _read(self, eng):
        return {k: eng.vars[v] for k, v in self.VARS.items()}

    def test_a_state_without_medicine_starts_at_its_targets(self):
        eng = _Engine(_mod_fixtures(self.INP))
        eng.call("te_demog_medicine_drift")
        for k, v in self._read(eng).items():
            self.assertAlmostEqual(v, demographics_model.medicine_targets(self.INP)[k], places=9, msg=k)

    def test_a_seed_sets_the_targets(self):
        eng = _Engine(_mod_fixtures(self.INP))
        eng.vars.update(te_dg_acc=0.9, te_dg_trt_inf=0.9, te_dg_trt_mat=0.9, te_dg_trt_chr=0.9)
        eng.call("te_demog_medicine_at_target")
        self.assertEqual(self._read(eng), demographics_model.medicine_targets(self.INP))

    def test_each_step_closes_its_share_of_the_gap(self):
        prev = {"access": 0.4, "infection": 0.0, "maternal": 0.6, "chronic": 0.1}
        for spread in (0.0, 0.15, 0.3, 5.0):
            inp = dataclasses.replace(self.INP, mods={**self.INP.mods, P.DIFFUSION_TYPE: spread})
            eng = _Engine(_mod_fixtures(inp))
            eng.vars.update({self.VARS[k]: v for k, v in prev.items()})
            eng.call("te_demog_medicine_drift")
            want = demographics_model.medicine_drift(prev, inp)
            for k, v in self._read(eng).items():
                with self.subTest(spread=spread, value=k):
                    self.assertAlmostEqual(v, want[k], places=9)
                    lo, hi = sorted((prev[k], demographics_model.medicine_targets(inp)[k]))
                    self.assertTrue(lo - 1e-9 <= v <= hi + 1e-9, "never overshoots")

    def test_near_its_target_a_value_takes_it(self):
        target = demographics_model.medicine_targets(self.INP)["access"]
        eng = _Engine(_mod_fixtures(self.INP))
        eng.vars.update(te_dg_acc=target - 0.005, te_dg_trt_inf=0.4, te_dg_trt_mat=0.35, te_dg_trt_chr=0.1)
        eng.call("te_demog_medicine_drift")
        self.assertAlmostEqual(eng.vars["te_dg_acc"], target, places=12)
```

Put `_stored` and `_mod_fixtures` above `_engine_for` (Task 4 changes `_engine_for` to use `_mod_fixtures`).

- [ ] **Step 3: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_gen_demographics test_demographics_registry.TestCauseFactorsScript test_demographics_registry.TestMedicineDriftScript`
Expected: FAIL/ERROR (`te_demog_f_infection_medicine` not found).

- [ ] **Step 4: The generator**

Replace `multipliers(o)`'s per-cause loop (keep the female work share and `te_demog_means` that follow it) with:

```python
def _factor_body(o, cause, factor):
    """One factor's body, reading only what the step stored (te_demog_cause_inputs_store, the drifted medicine, the
    walk's te_dg_sol and te_dg_lit), in demographics_model.cause_factors' arithmetic."""
    s = P.CAUSE_SHORT[cause]
    span = P.WEALTH_TFR_HIGH_SOL - P.WEALTH_TFR_LOW_SOL
    if factor == "medicine":
        o("value = 1")
        o(f"subtract = {{ value = var:te_dg_acc multiply = var:te_dg_trt_{s} }}")
    elif factor == "sol":
        at_high = P.SOL_INFECTION_AT_HIGH if cause == "infection" else P.SOL_CHRONIC_AT_HIGH
        o(f"value = var:te_dg_sol subtract = {P.WEALTH_TFR_LOW_SOL} divide = {span} min = 0 max = 1")
        o(f"multiply = {lit(at_high - 1)} add = 1")
    elif factor == "poverty":
        o(f"value = {P.POVERTY_INFECTION_SOL} subtract = var:te_dg_sol "
          f"divide = {P.POVERTY_INFECTION_SOL - P.POVERTY_INFECTION_FLOOR_SOL} min = 0 max = 1")
        o(f"multiply = {lit(P.POVERTY_INFECTION_AT_FLOOR - 1)} add = 1")
    elif factor == "literacy":
        o(f"value = var:te_dg_lit multiply = {lit(-P.LITERACY_INFECTION_WEIGHT)} add = 1")
    elif factor == "crowding":
        o(f"value = var:te_dg_in_crowd multiply = {lit(P.CROWDING_INFECTION_PER_PULL)}")
        o(f"max = {lit(P.CROWDING_INFECTION_MAX)} add = 1")
    elif factor == "laws":
        o(f"value = 1 add = var:te_dg_in_{s} min = {lit(P.MORTALITY_MULT_FLOOR)}")
    elif factor == "turmoil":
        o(f"value = var:te_dg_in_turm multiply = {lit(P.TURMOIL_EXTERNAL_WEIGHT)} add = 1")
    else:
        raise KeyError(factor)


def medicine_target_values(o):
    o("# State scope: where medicine is heading, read live from the census's types (the Causes of Death plan):")
    o("# health-care access (the base plus the health law's lines), each cause's treatment, and the share of the gap")
    o("# a census step closes (demographics_model.medicine_targets, diffusion).")
    o("te_demog_access_target = {")
    o(f"value = modifier:{P.ACCESS_TYPE}")
    o(f"add = {lit(P.BASE_ACCESS)}")
    o("min = 0")
    o("max = 1")
    o("}")
    for cause in P.MEDICINE_CAUSES:
        o(f"te_demog_treatment_target_{cause} = {{")
        o(f"value = modifier:{P.TREATMENT_TYPE[cause]}")
        o("min = 0")
        o(f"max = {lit(P.TREATMENT_CAP[cause])}")
        o("}")
    o("te_demog_medical_diffusion = {")
    o(f"value = modifier:{P.DIFFUSION_TYPE}")
    o(f"add = {lit(P.DIFFUSION_BASE)}")
    o("min = 0")
    o(f"max = {lit(P.DIFFUSION_MAX)}")
    o("}")
    for cause in P.MEDICINE_CAUSES:
        o(f"# State scope: {cause}'s medicine at its targets (the section's arrow).")
        o(f"te_demog_f_{cause}_medicine_target = {{")
        o("value = 1")
        o(f"subtract = {{ value = te_demog_access_target multiply = te_demog_treatment_target_{cause} }}")
        o("}")
    o("")


def multipliers(o):
    medicine_target_values(o)
    for cause, factors in P.CAUSE_FACTORS.items():
        for factor in factors:
            o(f"# State scope: {cause}'s {factor} factor (demographics_model.cause_factors), on the step's stored inputs.")
            o(f"te_demog_f_{cause}_{factor} = {{")
            _factor_body(o, cause, factor)
            o("}")
        if cause == "maternal":
            o("# State scope: maternal deaths per 100,000 births (an MMR, not a multiplier): the base rate")
            o("# times the cause's factors (demographics_model.cause_multipliers, group_rates).")
        else:
            o(f"# State scope: the {cause} cause's multiplier, the product of its factors (demographics_model.cause_multipliers).")
        o(f"te_demog_mult_{cause} = {{")
        o(f"value = te_demog_f_{cause}_{factors[0]}")
        for factor in factors[1:]:
            o(f"multiply = te_demog_f_{cause}_{factor}")
        if cause == "maternal":
            o(f"multiply = {P.MATERNAL_PER_100K_BIRTHS}")
        o("}")
        o("")
```

The rest of `multipliers`, from `te_demog_female_work_share` on, stays as it is. Each cause's factors come before its
multiplier in the file, as above. `CAUSES` stays; assert `tuple(P.CAUSE_FACTORS) == CAUSES` at import.

Add to `constants`' dict: `"medicine_snap": P.MEDICINE_SNAP`, `"medicine_snap_neg": -P.MEDICINE_SNAP`,
`"deaths_on_top_high": P.DEATHS_ON_TOP_HIGH`, `"base_access": P.BASE_ACCESS`,
`"maternal_base": P.MATERNAL_PER_100K_BIRTHS`.

Add a `medicine_effects(o)` and call it from `render_effects`:

```python
def medicine_effects(o):
    o("# THIS = a state, at the top of te_demog_prepare (a seed or a step): the census's inputs that aren't stored")
    o("# already, so te_demog_f_* (and the state subtab's Causes of Death) read what the step used until the next one.")
    o("te_demog_cause_inputs_store = {")
    for cause, types in P.MORTALITY_TYPES.items():
        adds = " ".join(f"add = modifier:{t}" for t in types)
        o(f"set_variable = {{ name = te_dg_in_{P.CAUSE_SHORT[cause]} value = {{ value = 0 {adds} }} }}")
    o("# turmoil as the 0-1 share te_demog_crisis reads")
    o("set_variable = { name = te_dg_in_turm value = { value = turmoil min = 0 max = 1 } }")
    o("# crowding: the migration penalty the crowding refresh applied (te_update_migration_crowding_modifier)")
    o("set_variable = { name = te_dg_in_crowd value = 0 }")
    o("if = {")
    o("limit = {")
    o("has_modifier = migration_crowding")
    o("has_variable = migration_crowding_mult_applied")
    o("}")
    o("set_variable = { name = te_dg_in_crowd value = { value = var:migration_crowding_mult_applied "
      f"multiply = {lit(P.MIGRATION_CROWDING_PULL_PER_MULT)} }} }}")
    o("}")
    o("}")
    o("")
    pairs = [("te_dg_acc", "te_demog_access_target")]
    pairs += [(f"te_dg_trt_{P.CAUSE_SHORT[c]}", f"te_demog_treatment_target_{c}") for c in P.MEDICINE_CAUSES]
    o("# THIS = a state: the drifted medicine at its targets (te_demog_seed; te_demog_medicine_drift for a state")
    o("# without it: a census from before the Causes of Death plan).")
    o("te_demog_medicine_at_target = {")
    for var, target in pairs:
        o(f"set_variable = {{ name = {var} value = {target} }}")
    o("}")
    o("")
    o("# THIS = a state at the start of its step (te_demog_step_begin): health-care access and each cause's treatment")
    o("# move te_demog_medical_diffusion of the way to today's targets (demographics_model.medicine_drift).")
    o("te_demog_medicine_drift = {")
    o("if = {")
    o("limit = {")
    for var, _target in pairs:
        o(f"has_variable = {var}")
    o("}")
    o("set_local_variable = { name = te_dg_diff value = te_demog_medical_diffusion }")
    for var, target in pairs:
        o(f"te_demog_medicine_drift_one = {{ VAR = {var} TARGET = {target} }}")
    o("}")
    o("else = {")
    o("te_demog_medicine_at_target = yes")
    o("}")
    o("}")
    o("")
    o("# One drifted value: (target - value) x the step's share + value; within te_demog_k_medicine_snap of the target,")
    o("# the target. set_variable's inline block, not change_variable (scripting_best_practices.md).")
    o("te_demog_medicine_drift_one = {")
    o("set_variable = {")
    o("name = $VAR$")
    o("value = {")
    o("value = $TARGET$")
    o("subtract = var:$VAR$")
    o("multiply = local_var:te_dg_diff")
    o("add = var:$VAR$")
    o("}")
    o("}")
    o("set_local_variable = { name = te_dg_gap value = { value = $TARGET$ subtract = var:$VAR$ } }")
    o("if = {")
    o("limit = {")
    o("local_var:te_dg_gap < te_demog_k_medicine_snap")
    o("local_var:te_dg_gap > te_demog_k_medicine_snap_neg")
    o("}")
    o("set_variable = { name = $VAR$ value = $TARGET$ }")
    o("}")
    o("}")
    o("")
```

- [ ] **Step 5: Regenerate and run the tests**

Run: `.venv/bin/python scripts/generators/gen_demographics.py`, then
`.venv/bin/python -m unittest test_gen_demographics test_demographics_registry.TestCauseFactorsScript test_demographics_registry.TestMedicineDriftScript`
Expected: OK. `test_committed_outputs_are_current` passes on the regenerated files.

- [ ] **Step 6: Commit** the generator, both generated files and the tests: "Demographics generator: causes of death as
  stored factors, and the drift of medicine".

---

### Task 4: The census stores its inputs and drifts its medicine (review stop)

**Files:**
- Modify: `common/scripted_effects/te_demog_effects.txt` (`te_demog_prepare`, `te_demog_seed`, `te_demog_step_begin`,
  the header inventory)
- Modify: `common/script_values/te_debug_demog_values.txt` (`te_debug_demog_mult_*`),
  `common/scripted_effects/te_debug_demog_effects.txt` (`te_debug_demog_mods_line`)
- Test: `test_demographics_registry.py` (`_engine_for`; new `TestCausesInTheStep`)

**Interfaces:**
- Consumes: `te_demog_cause_inputs_store`, `te_demog_medicine_at_target`, `te_demog_medicine_drift` (Task 3).
- Produces: every seed and step leaves `te_dg_acc`, `te_dg_trt_*`, `te_dg_in_*` on the state; `_engine_for(...,
  real_multipliers=False)`.

- [ ] **Step 1: Make `_engine_for` give the step's reads** (`test_demographics_registry.py`)

```python
def _engine_for(inp, year, pop, effects=None, engine=None, real_multipliers=False):
    """A state with the census on, the walk's sums set from `inp`, and the owner's multipliers
    (script values that read the owner's techs and laws) taken from the model. The step's own reads (the census's
    types and turmoil) are fixtures too, for te_demog_cause_inputs_store and the drift; real_multipliers runs the
    generated te_demog_mult_* on them instead of taking the model's."""
    mult = demographics_model.cause_multipliers(inp)
    fixtures = {
        "year": float(year),
        "state_population": float(pop),
        "te_demog_female_work_share": demographics_model.female_work_share(inp),
        "te_demog_means": demographics_model.means(inp),
        f"modifier:{P.NATURAL_FERTILITY_TYPE}": inp.mods.get(P.NATURAL_FERTILITY_TYPE, 0.0),
        **_mod_fixtures(inp),
    }
    if not real_multipliers:
        fixtures.update({
            "te_demog_mult_infection": mult["infection"],
            "te_demog_mult_external": mult["external"],
            "te_demog_mult_chronic": mult["chronic"],
            "te_demog_mult_work": mult["work"],
            "te_demog_mult_maternal": mult["maternal"] * P.MATERNAL_PER_100K_BIRTHS,
        })
    eng = (engine or _Engine)(fixtures, triggers={"te_demog_cohorts_run": True}, effects=effects)
    eng.vars.update(te_dg_lit=inp.literacy, te_dg_urban_share=inp.urban_share,
                    te_dg_wtfr=demographics_model.wealth_tfr(inp.sol), te_dg_sol=float(inp.sol))
    if inp.crowding:
        eng.modifiers["migration_crowding"] = inp.crowding / P.MIGRATION_CROWDING_PULL_PER_MULT
        eng.vars["migration_crowding_mult_applied"] = inp.crowding / P.MIGRATION_CROWDING_PULL_PER_MULT
    return eng
```

`_mod_fixtures` (Task 3) must be defined above `_engine_for`; move it there.

- [ ] **Step 2: Write the failing tests**

```python
class TestCausesInTheStep(unittest.TestCase):
    """The Causes of Death plan: a seed starts medicine at its targets, a step drifts it before the year's rates, and
    both store the inputs the factors read."""

    INP0 = TestCohortScript.INP
    INP1 = dataclasses.replace(TestCohortScript.INP, turmoil=0.4, mods={
        P.ACCESS_TYPE: 0.3, P.TREATMENT_TYPE["infection"]: 0.4, P.TREATMENT_TYPE["maternal"]: 0.35,
        "state_external_mortality_mult": -0.1, P.DIFFUSION_TYPE: 0.15})

    def test_a_seed_starts_at_its_targets_and_stores_its_inputs(self):
        eng = _engine_for(self.INP1, 1836, 250000.0, real_multipliers=True)
        eng.call("te_demog_seed")
        targets = demographics_model.medicine_targets(self.INP1)
        self.assertAlmostEqual(eng.vars["te_dg_acc"], targets["access"], places=9)
        self.assertAlmostEqual(eng.vars["te_dg_in_turm"], 0.4, places=9)
        self.assertAlmostEqual(eng.vars["te_dg_m_inf"], demographics_model.cause_multipliers(self.INP1)["infection"],
                               places=9)

    def test_the_step_drifts_medicine_before_its_rates(self):
        eng = _engine_for(self.INP0, 1836, 250000.0, real_multipliers=True)
        eng.call("te_demog_seed")
        eng.fixtures.update(_mod_fixtures(self.INP1))
        eng.call("te_demog_medicine_drift")
        eng.call("te_demog_prepare")
        med = demographics_model.medicine_drift(demographics_model.medicine_targets(self.INP0), self.INP1)
        drifted = dataclasses.replace(self.INP1, medicine=med)
        want = demographics_model.cause_multipliers(drifted)
        for cause, var in (("infection", "te_dg_m_inf"), ("external", "te_dg_m_ext"), ("chronic", "te_dg_m_chr")):
            self.assertAlmostEqual(eng.vars[var], want[cause], places=9, msg=cause)
        self.assertAlmostEqual(eng.vars["te_dg_m_mat"], want["maternal"] * P.MATERNAL_PER_100K_BIRTHS, places=6)
        qf, qm, _ = demographics_model.group_rates(drifted)
        e0 = (demographics_model.life_table(qf)["e0"] + demographics_model.life_table(qm)["e0"]) / 2
        self.assertAlmostEqual(eng.vars["te_dg_e0"], e0, places=6)

    def test_an_old_census_starts_at_its_targets(self):
        # a census state from before this build: no drifted medicine, no stored inputs
        eng = _engine_for(self.INP1, 1837, 250000.0, real_multipliers=True)
        eng.call("te_demog_medicine_drift")
        self.assertAlmostEqual(eng.vars["te_dg_acc"], demographics_model.medicine_targets(self.INP1)["access"])

    def test_the_entry_points_run_in_order(self):
        effects = _raw_blocks([EFFECTS])
        begin = [k for k, _, _ in _parse_script(effects["te_demog_step_begin"])]
        self.assertEqual(begin[:2], ["te_demog_medicine_drift", "te_demog_prepare"])
        seed = [k for k, _, _ in _parse_script(effects["te_demog_seed"])]
        self.assertLess(seed.index("te_demog_medicine_at_target"), seed.index("te_demog_prepare"))
        prepare = [k for k, _, _ in _parse_script(effects["te_demog_prepare"])]
        first_mult = next(i for i, (k, _, v) in enumerate(_parse_script(effects["te_demog_prepare"]))
                          if k == "set_local_variable" and _find(v, "name") == "te_dg_m_inf")
        self.assertLess(prepare.index("te_demog_cause_inputs_store"), first_mult)
```

- [ ] **Step 3: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestCausesInTheStep`
Expected: ERROR (`read of missing variable var:te_dg_acc` in the seed).

- [ ] **Step 4: Wire the entry points** (`te_demog_effects.txt`)
  - `te_demog_prepare`: `te_demog_cause_inputs_store = yes` just before
    `set_local_variable = { name = te_dg_m_inf value = te_demog_mult_infection }`, with the comment
    `# the inputs the factors read, stored so the Causes of Death section matches this step until the next (generated)`.
  - `te_demog_seed`: `te_demog_medicine_at_target = yes` just before `te_demog_prepare = yes`
    (`# a seed starts medicine at its targets (the Causes of Death plan)`).
  - `te_demog_step_begin`: `te_demog_medicine_drift = yes` first
    (`# medicine moves its share of the gap, then the year's rates use it`). Update its comment.
  - The header inventory: after the cause multipliers' lines, add:
    ```
    #   te_dg_acc, te_dg_trt_inf, te_dg_trt_mat, te_dg_trt_chr  the drifted health-care access and treatments
    #                       (te_demog_medicine_drift; the Causes of Death plan)
    #   te_dg_in_ext, te_dg_in_work, te_dg_in_chr, te_dg_in_turm, te_dg_in_crowd  the step's other inputs the
    #                       factors read (te_demog_cause_inputs_store)
    ```

- [ ] **Step 5: The console's reads**
  - `te_debug_demog_values.txt`: guard each `te_debug_demog_mult_*` (all five) on the step's inputs, −1 without them:
    ```
    te_debug_demog_mult_external = {
    	value = -1
    	if = {
    		limit = {
    			has_variable = te_dg_in_turm
    			has_variable = te_dg_acc
    		}
    		value = te_demog_mult_external
    	}
    }
    ```
    (infection and chronic keep their `te_dg_sol`/`te_dg_lit` conditions as well).
  - `te_debug_demog_mods_line` (option l): add ` diff=[THIS.ScriptValue('te_demog_medical_diffusion')|3]` beside
    `impact=`. Extend `test_option_l_logs_the_fertility_types`' neighbour with
    `self.assertIn(" diff=[THIS.ScriptValue('te_demog_medical_diffusion')|3]", line)`.

- [ ] **Step 6: Run the registry, the model and the harness**

Run: `.venv/bin/python -m unittest test_demographics_registry test_demographics_model test_demographics_harness`
Expected: OK. The cohort tests keep their multiplier fixtures; the drift runs at the targets there.

- [ ] **Step 7: Commit**: "Demographics: the census stores its causes' inputs and drifts its medicine".

- [ ] **Review stop:** a fresh reviewer reads Tasks 3–4 (the generated factors and drift, the wiring, the old-save
  path) against this plan before Task 5.

---

### Task 5: Measure the deaths added on top (walk sums, the clamp's side)

**Files:**
- Modify: `scripts/generators/gen_demographics.py` (`absorbed_terms`, `absorbed_walk`); regenerate
- Modify: `common/scripted_effects/te_demog_effects.txt` (`te_demog_walks`, after `te_dg_ed` is set; the header)
- Modify: `common/scripted_effects/te_demog_rate_effects.txt` (`te_demog_rate_clamp`, `te_demog_rates_refresh`,
  `te_demog_rates_clear`, the header)
- Modify: `common/scripted_effects/te_debug_demog_effects.txt` (option n's `TE_DEMOG_RATES` line)
- Modify: `common/script_values/te_demog_display_values.txt` (`te_demog_deaths_on_top`, `_whole_state`,
  `_some_people`; text in Task 7 Step 3)
- Test: `test_gen_demographics.py`, `test_demographics_registry.py` (`TestRatesScript`, new `TestDeathsOnTopSplit`)

**Interfaces:**
- Consumes: the walk's locals `te_dg_p_ed`, `te_dg_w_pop`, `te_dg_w_rep` (Full only), `te_demog_step_months`.
- Produces:
  - state variables (Full only): `te_dg_ed_state` (the engine's deaths over the window from the state's read and the
    absorbed terms alone, people) and `te_dg_sev_share` (the share of people in severe starvation at the walk);
  - `te_dg_rate_clamp_d` (0 none, 1 floor, 2 cap; set by every Full refresh, removed by `te_demog_rates_clear`);
  - pop scope: `te_demog_pop_state_death_mult`.

**Why measured:** see "What the code says" 1–2.
- Whole state = `te_dg_ed_state ÷ te_dg_ed_target`. This is os + q + the census term's own miss.
- Some of its people = `te_dg_ed ÷ te_dg_ed_state`, exactly the pops' own lines the walk counts: severe starvation,
  their class's, workplace's and working conditions' lines, and non-homeland mortality.
- The product is 1 + dz unless dz hit `ON_TOP_SCALE_MAX`.

- [ ] **Step 1: Write the failing tests**

`test_gen_demographics.py`:

```python
    def test_the_state_part_of_a_pops_deaths(self):
        body = self.values.split("te_demog_pop_state_death_mult = {", 1)[1].split("\n}\n", 1)[0]
        self.assertEqual([line.strip() for line in body.strip().splitlines()],
                         ["value = 1", "add = state.modifier:state_mortality_mult",
                          "add = te_demog_pop_absorbed_deaths", "min = 0"])
        full = self.values.split("te_demog_pop_death_mult = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("add = state.modifier:state_mortality_mult", full)
        self.assertIn("is_in_severe_starvation = yes", full)

    def test_the_walk_sums_the_split_under_full(self):
        init = self.effects.split("te_demog_absorbed_walk_init = {", 1)[1].split("\n}\n", 1)[0]
        pop = self.effects.split("te_demog_absorbed_walk_pop = {", 1)[1].split("\n}\n", 1)[0]
        for name in ("te_dg_w_eds", "te_dg_w_sev"):
            self.assertIn(f"name = {name} value = 0", init)
        guarded = pop.split("local_var:te_dg_w_rep > 0", 1)[1]
        self.assertIn("multiply = te_demog_pop_state_death_mult", guarded)
        self.assertIn("is_in_severe_starvation = yes", guarded)
```

`test_demographics_registry.py`, `TestRatesScript`:

```python
    def test_the_deaths_clamp_records_its_side(self):
        """The Causes of Death section says why the census couldn't set deaths: 1 at the floor, 2 at the cap, 0 when it
        could; births clamped alone leave 0."""
        for kw, side in ((dict(cdr=400.0), 2), (dict(cdr=0.5, read_d=-0.5), 1),
                         (dict(cbr=2.0, read_b=-0.5), 0), ({}, 0)):
            eng = self._eng(**kw)
            eng.call("te_demog_rates_refresh")
            with self.subTest(kw=kw):
                self.assertEqual(eng.vars["te_dg_rate_clamp_d"], side)

    def test_outside_full_the_clamp_side_goes(self):
        eng = self._eng(full=False)
        eng.vars["te_dg_rate_clamp_d"] = 2.0
        eng.call("te_demog_rates_refresh")
        self.assertNotIn("te_dg_rate_clamp_d", eng.vars)
```

New class:

```python
class TestDeathsOnTopSplit(unittest.TestCase):
    """te_demog_deaths_whole_state x te_demog_deaths_some_people (display values, Task 7) is 1 + te_dg_dz: the walk
    measures the split over the same window as dz (the Causes of Death plan)."""

    def test_the_split_multiplies_to_the_scale(self):
        for ed_target, ed_state, ed in ((1000.0, 1080.0, 1700.0), (1000.0, 950.0, 940.0), (500.0, 900.0, 1200.0)):
            eng = _Engine({})
            dz = min(max(ed / ed_target - 1, P.ON_TOP_SCALE_MIN), P.ON_TOP_SCALE_MAX)
            eng.vars.update(te_dg_ed_target=ed_target, te_dg_ed_state=ed_state, te_dg_ed=ed, te_dg_dz=dz)
            whole = eng.value(eng._tree(eng.values, "te_demog_deaths_whole_state"))
            some = eng.value(eng._tree(eng.values, "te_demog_deaths_some_people"))
            total = eng.value(eng._tree(eng.values, "te_demog_deaths_on_top"))
            with self.subTest(ed=ed):
                self.assertAlmostEqual(whole * some, total, places=9)

    def test_a_pops_state_part_floors_at_zero(self):
        eng = _Engine({"state.modifier:state_mortality_mult": -1.4, "te_demog_pop_absorbed_deaths": 0.1})
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_pop_state_death_mult")), 0.0)
        eng.fixtures["state.modifier:state_mortality_mult"] = 0.2
        self.assertAlmostEqual(eng.value(eng._tree(eng.values, "te_demog_pop_state_death_mult")), 1.3)

    def test_the_walk_stores_the_split_only_under_full(self):
        walks = _block(_text(EFFECTS), "te_demog_walks")
        tail = walks.split("name = te_dg_ed\n", 1)[1]
        self.assertIn("local_var:te_dg_w_rep > 0", tail)
        for name in ("te_dg_ed_state", "te_dg_sev_share"):
            self.assertIn(f"name = {name}", tail)
            self.assertIn(f"remove_variable = {name}", tail)
```

(`test_the_split_multiplies_to_the_scale` reads Task 7's display values. Write those three values now, in Step 5
below, or move the test to Task 7.)

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_gen_demographics test_demographics_registry.TestRatesScript test_demographics_registry.TestDeathsOnTopSplit`
Expected: FAIL/ERROR.

- [ ] **Step 3: The generator**
  - In `absorbed_terms`, after `te_demog_pop_absorbed_deaths`:
    ```python
    o("# Pop scope: the engine's mortality multiplier for this pop from its state's read and the terms the census absorbs")
    o("# alone, without its own lines on top (severe starvation, its class's, its workplace's, non-homeland mortality):")
    o("# the walk's te_dg_ed over its sum is the per-pop part of the deaths added on top (the Causes of Death plan).")
    o("te_demog_pop_state_death_mult = {")
    o("value = 1")
    o("add = state.modifier:state_mortality_mult")
    o("add = te_demog_pop_absorbed_deaths")
    o("min = 0")
    o("}")
    o("")
    ```
  - In `absorbed_walk`'s init, after `te_dg_w_rep`'s line:
    `set_local_variable = { name = te_dg_w_eds value = 0 }` and `set_local_variable = { name = te_dg_w_sev value = 0 }`.
  - In `absorbed_walk`'s pop, inside the `local_var:te_dg_w_rep > 0` block:
    ```python
    o("change_local_variable = { name = te_dg_w_eds add = { value = local_var:te_dg_p_ed multiply = te_demog_pop_state_death_mult } }")
    o("if = {")
    o("limit = { is_in_severe_starvation = yes }")
    o("change_local_variable = { name = te_dg_w_sev add = total_size }")
    o("}")
    ```
    and amend the two comments: "the replaced sums, and under Full the deaths-on-top split's".
  - Regenerate.

- [ ] **Step 4: The walk and the refresh**
  - `te_demog_walks`, straight after `set_variable = { name = te_dg_ed ... }`:
    ```
    	# the Causes of Death section's split of the deaths added on top (Full only, te_dg_w_rep): the engine's deaths
    	# over the step from the state's read and the absorbed terms alone, and the share of people in severe starvation
    	if = {
    		limit = { local_var:te_dg_w_rep > 0 }
    		set_variable = {
    			name = te_dg_ed_state
    			value = {
    				value = local_var:te_dg_w_eds
    				multiply = te_demog_step_months
    				divide = 100000
    			}
    		}
    		set_variable = { name = te_dg_sev_share value = { value = local_var:te_dg_w_sev divide = { value = local_var:te_dg_w_pop min = 1 } max = 1 } }
    	}
    	else = {
    		if = {
    			limit = { has_variable = te_dg_ed_state }
    			remove_variable = te_dg_ed_state
    		}
    		if = {
    			limit = { has_variable = te_dg_sev_share }
    			remove_variable = te_dg_sev_share
    		}
    	}
    ```
    Add both to the header's walk inventory ("Full only").
  - `te_demog_rate_clamp`: first line `set_local_variable = { name = te_dg_rate_side value = 0 }`; in the floor branch
    `set_local_variable = { name = te_dg_rate_side value = 1 }`, in the cap branch `... value = 2`. Update its comment.
  - `te_demog_rates_refresh`, deaths half, after its `te_demog_rate_clamp = yes`:
    `set_variable = { name = te_dg_rate_clamp_d value = local_var:te_dg_rate_side }`
    (`# which clamp bit deaths, for the Causes of Death section: 0 none, 1 the floor, 2 the cap`).
  - `te_demog_rates_clear`: remove `te_dg_rate_clamp_d` as it removes `te_dg_rate_clamped`.
  - The file header: add `te_dg_rate_clamp_d` beside `te_dg_rate_clamped`.

- [ ] **Step 5: Option n, and the display values the split test reads**
  - Option n (`TE_DEMOG_RATES`): copy `te_dg_ed_state`, `te_dg_sev_share` and `te_dg_rate_clamp_d` into
    `te_dg_dbg_eds`, `te_dg_dbg_sev`, `te_dg_dbg_cld` (0 when absent, as the line's other copies), append
    ` ed_state=[THIS.Var('te_dg_dbg_eds').GetValue|0]; sev=[THIS.Var('te_dg_dbg_sev').GetValue|3]; clamp_d=[THIS.Var('te_dg_dbg_cld').GetValue|0]`
    before `date=`, and remove the three after the line.
  - `te_demog_display_values.txt`: add `te_demog_deaths_on_top`, `te_demog_deaths_whole_state` and
    `te_demog_deaths_some_people` (Task 7, Step 3 gives their text).

- [ ] **Step 6: Run the tests**

Run: `.venv/bin/python scripts/generators/gen_demographics.py --check && .venv/bin/python -m unittest test_gen_demographics test_demographics_registry`
Expected: OK.

- [ ] **Step 7: Commit**: "Demographics: measure the deaths added on top by the walk, and say which clamp bit".

- [ ] **Review stop:** the same fresh reviewer as Task 4 reads Task 5 (the walk's new sums, the clamp side) before
  Task 6.

---

### Task 6: Medical Outreach, and releases without it

**Files:**
- Modify: `common/decrees/extra_decrees.txt`
- Modify: `common/script_values/te_demog_values.txt` (`te_demog_medicine_gap`),
  `common/scripted_triggers/te_demog_triggers.txt` (`te_demog_medicine_behind`)
- Modify: `localization/english/te_decrees_l_english.yml`
- Modify: `scripts/release/comment_out_census_inputs.py`
- Test: `test_demographics_registry.py` (new `TestMedicalOutreach`), `test_release_census_inputs.py`

**Interfaces:**
- Consumes: `te_demog_access_target`, `te_demog_treatment_target_<cause>`, `te_demog_k_medicine_snap` (Task 3);
  `te_dg_acc`, `te_dg_trt_*` (Task 4); `P.MEDICAL_OUTREACH_DIFFUSION` (Task 1).
- Produces: `decree_medical_outreach`; `te_demog_medicine_behind` (state trigger); the release script's rule 3b.

- [ ] **Step 1: Write the failing tests**

```python
class TestMedicalOutreach(unittest.TestCase):
    """The Causes of Death plan: a decree that speeds the spread of medicine in one state, under Full only."""

    DECREES = ROOT / "common" / "decrees" / "extra_decrees.txt"

    def test_the_decree_carries_the_spread_of_medicine(self):
        body = _block(_text(self.DECREES), "decree_medical_outreach")
        modifier = _parse_script(body)
        lines = _find(modifier, "modifier")
        self.assertEqual([(k, float(v)) for k, _, v in lines], [(P.DIFFUSION_TYPE, P.MEDICAL_OUTREACH_DIFFUSION)])
        self.assertEqual(_find(modifier, "cost"), "100")

    def test_it_exists_only_under_full(self):
        # vanilla 00_decree.txt: country_trigger decides whether a decree is shown; the rule's wrapper, never the rule
        trig = _find(_parse_script(_block(_text(self.DECREES), "decree_medical_outreach")), "country_trigger")
        self.assertEqual(trig, [("te_demog_effects_run", "=", "yes")])

    def test_it_is_offered_where_medicine_is_behind(self):
        fixtures = {f"modifier:{t}": 0.0 for t in P.DEMOG_TYPES}
        fixtures[f"modifier:{P.ACCESS_TYPE}"] = 0.3
        eng = _Engine(fixtures)
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_medicine_gap")), 0.0, "no census medicine yet")
        eng.vars.update(te_dg_acc=0.4, te_dg_trt_inf=0.0, te_dg_trt_mat=0.0, te_dg_trt_chr=0.0)
        self.assertTrue(eng.holds(_parse_script("te_demog_medicine_behind = yes")))
        eng.vars["te_dg_acc"] = 0.7
        self.assertFalse(eng.holds(_parse_script("te_demog_medicine_behind = yes")))
```

`test_release_census_inputs.py`:

```python
    def test_the_census_decree_is_commented_whole(self):
        """Medical Outreach's only effect is the census's spread of medicine: a release has no census, so the decree
        goes whole, not as a shell with a texture and a cost (the Causes of Death plan)."""
        entries = self._entries(self._text("common/decrees/extra_decrees.txt"))
        self.assertNotIn("decree_medical_outreach", entries)
        for kept in ("decree_natalism_initiative", "decree_pollution_control", "decree_war_propaganda"):
            self.assertIn(kept, entries)
```

In `test_it_found_the_carriers`, raise the floor from 30 to 46 (39 census lines on 2026-10-11, plus the six
technologies and the decree). In `test_what_else_it_comments_is_dead_with_the_census`, add
`"common/decrees/extra_decrees.txt"` to `whole_entries`.

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestMedicalOutreach test_release_census_inputs`
Expected: FAIL/ERROR.

- [ ] **Step 3: The gap and the trigger**

`te_demog_values.txt`, after `te_demog_crisis`:

```
# State scope: how far the census's drifted medicine is behind where it is heading, summed over health-care access and
# the three treatments (only the shortfalls); 0 for a state without the census's medicine (the Causes of Death plan).
# Medical Outreach's state_trigger reads it through te_demog_medicine_behind.
te_demog_medicine_gap = {
	value = 0
	if = {
		limit = {
			has_variable = te_dg_acc
			has_variable = te_dg_trt_inf
			has_variable = te_dg_trt_mat
			has_variable = te_dg_trt_chr
		}
		add = { value = te_demog_access_target subtract = var:te_dg_acc min = 0 }
		add = { value = te_demog_treatment_target_infection subtract = var:te_dg_trt_inf min = 0 }
		add = { value = te_demog_treatment_target_maternal subtract = var:te_dg_trt_mat min = 0 }
		add = { value = te_demog_treatment_target_chronic subtract = var:te_dg_trt_chr min = 0 }
	}
}
```

`te_demog_triggers.txt`:

```
# THIS = a state: its medicine is still spreading, more than the snap behind its targets in all (te_demog_medicine_gap),
# so Medical Outreach would do something. False for a state without the census's medicine.
te_demog_medicine_behind = {
	te_demog_medicine_gap > te_demog_k_medicine_snap
}
```

- [ ] **Step 4: The decree** (`extra_decrees.txt`, after `decree_natalism_initiative`)

```
# Medical Outreach (the Causes of Death plan, owner 2026-10-11): doctors and nurses bring the country's latest medicine
# to one state, so its health-care access and treatments close the gap faster (the census's spread of medicine,
# +MEDICAL_OUTREACH_DIFFUSION in demographics_params.py). The census is its only reader, so it exists only under the
# Demographics rule's Full setting: vanilla 00_decree.txt, "country_trigger ... determines if the Decree is
# permitted/shown in interface". Offered where the state's medicine is behind; an issued decree stays valid (Pollution
# Control's pattern). A release comments it out whole (scripts/release/comment_out_census_inputs.py). The texture is a
# placeholder (vanilla Emergency Relief's); the final art: a doctor's bag over a map pin.
decree_medical_outreach = {
	texture = "gfx/interface/icons/decree/decree_emergency_relief.dds"
	modifier = {
		state_medical_diffusion_add = 0.2
	}

	unlocking_technologies = {
		medical_degrees
	}

	cost = 100

	country_trigger = {
		te_demog_effects_run = yes
	}

	state_trigger = {
		OR = {
			te_demog_medicine_behind = yes
			has_decree = decree_medical_outreach
		}
	}

	ai_weight = {
		value = 0
	}
}
```

`te_decrees_l_english.yml`:

```
 decree_medical_outreach:0 "Medical Outreach"
 decree_medical_outreach_desc:0 "Doctors and nurses go out to train this state's practitioners and staff its clinics, so the newest treatments and the reach of our health system arrive here years sooner."
```

- [ ] **Step 5: The release script** (`comment_out_census_inputs.py`)

Add to the docstring's list: "3b. every decree whose `modifier` block is left with no effect line is commented out
whole (Medical Outreach: the census is its only reader)." Add:

```python
def _modifier_emptied(lines):
    """True when an entry's `modifier = { ... }` block holds no live line: a decree whose only effects were census
    types (its texture and cost would ship as an empty decree otherwise)."""
    depth, inside = 0, False
    for line in lines:
        code = _code(line)
        if not inside and re.match(r"\s*modifier\s*=\s*\{", code):
            inside = True
        if inside:
            depth += code.count("{") - code.count("}")
            if re.sub(r"[\w:.@-]+\s*=\s*\{|[{}\s]", "", code):
                return False
            if depth == 0:
                return True
    return False
```

and in `run`'s entry loop, beside the `static_modifiers` branch:

```python
            elif path.parent.name == "decrees" and _modifier_emptied(new[start:end + 1]):
                for i in range(start, end + 1):
                    _tag(new, i)
```

- [ ] **Step 6: Run the tests, then commit**

Run: `.venv/bin/python -m unittest test_demographics_registry test_release_census_inputs test_demographics_modifiers`
Expected: OK. Also run `.venv/bin/python scripts/release/comment_out_census_inputs.py --check | tail -1`: 46 or more
census lines, and the decree's lines.

Commit: "Demographics: the Medical Outreach decree (Full only), and releases without it".

---

### Task 7: What the section reads: display values, gates, names

**Files:**
- Modify: `common/script_values/te_demog_display_values.txt`
- Modify: `common/scripted_guis/te_demog_sguis.txt`
- Modify: `localization/english/te_miscellaneous_l_english.yml` (the section's keys; `te_demog_st_e0_causes`;
  `te_demog_how_mortality`)
- Test: `test_demographics_registry.py` (new `TestCausesDisplay`)

**Interfaces:**
- Consumes: the variables of Tasks 3–5 and `te_dg_dz`, `te_dg_ed`, `te_dg_ed_target`, `te_dg_cdr`, `te_dg_cdr_model`;
  `concept_health_care_access` (Task 2); `te_demog_deaths_on_top`, `_whole_state`, `_some_people` (Task 5).
- Produces:
  - display values: `te_demog_access_from_law`, `te_demog_access_gap`, `te_demog_access_moving`,
    `te_demog_medicine_gap_<cause>`, `te_demog_medicine_moving_<cause>`, `te_demog_deaths_on_top_code`;
  - scripted GUIs: `te_demog_state_causes_sgui`, `te_demog_state_full_sgui`, `te_demog_state_on_top_sgui`;
  - loc keys `te_demog_sec_causes`, `te_demog_st_causes_pending`, and `te_demog_st_<row>`, `_value`, `_tt` for rows
    `acc`, `inf`, `ext`, `chr`, `work`, `mat`, `ontop`, with their parts.

- [ ] **Step 1: Write the failing tests**

```python
SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt"


class TestCausesDisplay(unittest.TestCase):
    """The Causes of Death section's reads (the plan's Task 7)."""

    def _shown(self, sgui, eng):
        body = _parse_script(_block(_text(SGUIS), sgui))
        return eng.holds(_find(body, "is_shown"))

    def test_the_on_top_gate_needs_a_measured_target(self):
        # Review Focus 2: the first Full step after a seed writes dz 0 against no target
        base = dict(te_dg_ed_target=0.0, te_dg_ed_state=900.0, te_dg_sev_share=0.0, te_dg_dz=0.0, te_dg_rate_clamp_d=0.0)
        for full, target, shown in ((True, 0.0, False), (True, 1000.0, True), (False, 1000.0, False)):
            eng = _Engine({}, triggers={"te_demog_effects_run": full})
            eng.vars.update(base, te_dg_ed_target=target)
            with self.subTest(full=full, target=target):
                self.assertEqual(self._shown("te_demog_state_on_top_sgui", eng), shown)

    def test_the_causes_gate_needs_the_steps_inputs(self):
        eng = _Engine({})
        self.assertFalse(self._shown("te_demog_state_causes_sgui", eng))
        eng.vars.update(_stored(demographics_model.Inputs()))
        self.assertTrue(self._shown("te_demog_state_causes_sgui", eng))

    def test_red_from_the_threshold(self):
        for dz, code in ((0.0, 0), (P.DEATHS_ON_TOP_HIGH - 1 - 0.01, 0), (P.DEATHS_ON_TOP_HIGH - 1, 1), (0.8, 1)):
            eng = _Engine({})
            eng.vars["te_dg_dz"] = dz
            with self.subTest(dz=dz):
                self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_deaths_on_top_code")), code)

    def test_the_arrow_shows_while_medicine_moves(self):
        inp = demographics_model.Inputs(mods={P.ACCESS_TYPE: 0.3})
        eng = _Engine(_mod_fixtures(inp))
        eng.vars.update(_stored(dataclasses.replace(inp, medicine={"access": 0.5, "infection": 0.0,
                                                                   "maternal": 0.0, "chronic": 0.0})))
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_access_moving")), 1)
        eng.vars["te_dg_acc"] = demographics_model.medicine_targets(inp)["access"]
        self.assertEqual(eng.value(eng._tree(eng.values, "te_demog_access_moving")), 0)

    def test_every_key_the_section_names_exists(self):
        loc = _text(ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml")
        rows = ("acc", "inf", "ext", "chr", "work", "mat", "ontop")
        keys = ["te_demog_sec_causes", "te_demog_st_causes_pending"]
        keys += [f"te_demog_st_{r}{s}" for r in rows for s in ("", "_value", "_tt")]
        for key in keys:
            self.assertRegex(loc, rf"(?m)^ {key}:0 \"", key)
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestCausesDisplay`
Expected: ERROR.

- [ ] **Step 3: The display values** (`te_demog_display_values.txt`, a new section at the end)

```
# ============================================================================
# Causes of Death (the state subtab; docs/superpowers/plans/2026-10-11-demographics-causes-of-death.md). State scope,
# read under te_demog_state_causes_sgui (the step's inputs exist) or te_demog_state_on_top_sgui (a measured scale
# under Full). The factors themselves are generated (te_demog_f_<cause>_<factor>, te_demog_generated_values.txt).
# ============================================================================

# The health law's share of health-care access, read live (the hover's breakdown under the base).
te_demog_access_from_law = {
	value = modifier:state_health_care_access_add
}

# How far health-care access is from its target, and 1 while that is more than the snap (the row's "62% → 68%").
te_demog_access_gap = {
	value = te_demog_access_target
	subtract = var:te_dg_acc
}
te_demog_access_moving = {
	value = 0
	if = {
		limit = {
			OR = {
				te_demog_access_gap > te_demog_k_medicine_snap
				te_demog_access_gap < te_demog_k_medicine_snap_neg
			}
		}
		value = 1
	}
}
```

and, for each of infection, maternal and chronic (`<c>`):

```
te_demog_medicine_gap_<c> = {
	value = te_demog_f_<c>_medicine_target
	subtract = te_demog_f_<c>_medicine
}
te_demog_medicine_moving_<c> = {
	value = 0
	if = {
		limit = {
			OR = {
				te_demog_medicine_gap_<c> > te_demog_k_medicine_snap
				te_demog_medicine_gap_<c> < te_demog_k_medicine_snap_neg
			}
		}
		value = 1
	}
}
```

Task 5 wrote the deaths added on top and its split (below, for reference). Add the code beside them:

```
# 1 + te_dg_dz: how far the engine's deaths over the last step ran from the census's own (te_demog_on_top_scales).
te_demog_deaths_on_top = {
	value = var:te_dg_dz
	add = 1
}
# 1 at or above te_demog_k_deaths_on_top_high (the row reads red), else 0: the threshold is script's (gotcha #23).
te_demog_deaths_on_top_code = {
	value = 0
	if = {
		limit = { te_demog_deaths_on_top >= te_demog_k_deaths_on_top_high }
		value = 1
	}
}
# Its split, measured by the walk over the same window (te_dg_ed_state, Full only): the whole state's part (the state's
# read: os, the moved lines' on-top family, the census term's own miss) and the pops' own lines'. Their product is
# te_demog_deaths_on_top unless the scale hit its cap.
te_demog_deaths_whole_state = {
	value = var:te_dg_ed_state
	divide = { value = var:te_dg_ed_target min = 1 }
}
te_demog_deaths_some_people = {
	value = var:te_dg_ed
	divide = { value = var:te_dg_ed_state min = 1 }
}
```

- [ ] **Step 4: The gates** (`te_demog_sguis.txt`, after `te_demog_state_stepped_sgui`; update the header's count)

```
# The state's last seed or step stored the Causes of Death inputs (te_demog_cause_inputs_store, the drifted
# medicine). A census from before the Causes of Death plan has none until its next step: the section says so.
te_demog_state_causes_sgui = {
	scope = state
	is_shown = {
		has_variable = te_dg_acc
		has_variable = te_dg_trt_inf
		has_variable = te_dg_trt_mat
		has_variable = te_dg_trt_chr
		has_variable = te_dg_in_ext
		has_variable = te_dg_in_work
		has_variable = te_dg_in_chr
		has_variable = te_dg_in_turm
		has_variable = te_dg_in_crowd
	}
	ai_is_valid = { always = no }
	is_valid = { always = no }
	effect = { }
}

# The rule's Full setting: only then does the census set births and deaths, so only then is there a Deaths Added on
# Top row.
te_demog_state_full_sgui = {
	scope = state
	is_shown = { te_demog_effects_run = yes }
	ai_is_valid = { always = no }
	is_valid = { always = no }
	effect = { }
}

# A measured scale under Full: the step had a target (the first Full step after a seed writes te_dg_ed_target 0 and
# dz 0), the walk measured the split, and the refresh noted its clamp.
te_demog_state_on_top_sgui = {
	scope = state
	is_shown = {
		te_demog_effects_run = yes
		has_variable = te_dg_ed_target
		var:te_dg_ed_target > 0
		has_variable = te_dg_dz
		has_variable = te_dg_ed_state
		has_variable = te_dg_sev_share
		has_variable = te_dg_rate_clamp_d
	}
	ai_is_valid = { always = no }
	is_valid = { always = no }
	effect = { }
}
```

- [ ] **Step 5: The section's loc** (`te_miscellaneous_l_english.yml`, beside the other `te_demog_st_*`)

The rows read only the state (`State.MakeScope`), never the player (`test_the_state_subtab_gate_needs_no_player`).

```
 te_demog_sec_causes:0 "Causes of Death"
 te_demog_st_causes_pending:0 "#lore This state's causes of death appear after its next count.#!"
 te_demog_st_acc:0 "[concept_health_care_access]"
 te_demog_st_acc_value:0 "[SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.ScriptValue('te_demog_access_moving'), '(CFixedPoint)1' ), 'te_demog_st_acc_moving', 'te_demog_st_acc_still' )]"
 te_demog_st_acc_still:0 "#v [State.MakeScope.Var('te_dg_acc').GetValue|%0]#!"
 te_demog_st_acc_moving:0 "#v [State.MakeScope.Var('te_dg_acc').GetValue|%0]#! → #v [State.MakeScope.ScriptValue('te_demog_access_target')|%0]#!"
 te_demog_st_acc_tt:0 "#b [concept_health_care_access]#!\nHow many of the state's people medicine reaches; each cause's treatment saves lives only this far.\n Markets and charity, everywhere: #v [State.MakeScope.ScriptValue('te_demog_k_base_access')|%0]#!\n The health law and the Ministry of Health: #v [State.MakeScope.ScriptValue('te_demog_access_from_law')|+%0]#!\n#lore The health law adds its share at each level of the Ministry of Health, in incorporated states only, times the Impact of Institutions.#!\n\nNew medicine and a larger health system reach the state over years: each count closes #v [State.MakeScope.ScriptValue('te_demog_medical_diffusion')|%0]#! of the gap ($state_medical_diffusion_add$)."
 te_demog_st_inf:0 "Infection and Hunger"
 te_demog_st_inf_value:0 "×#v [State.MakeScope.Var('te_dg_m_inf').GetValue|2]#!"
 te_demog_st_inf_tt:0 "#b Infection and Hunger#!\nDeaths from infection and hunger, most of them young children's, at a poor country's rates times:\n$te_demog_st_med_inf$\n [concept_sol]: ×#v [State.MakeScope.ScriptValue('te_demog_f_infection_sol')|2]#!\n Poverty: ×#v [State.MakeScope.ScriptValue('te_demog_f_infection_poverty')|2]#!\n Literacy: ×#v [State.MakeScope.ScriptValue('te_demog_f_infection_literacy')|2]#!\n Crowding: ×#v [State.MakeScope.ScriptValue('te_demog_f_infection_crowding')|2]#!\n#lore Medicine is 1 − [concept_health_care_access] × the share of these deaths treatment prevents.#!"
 te_demog_st_med_inf:0 "[SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.ScriptValue('te_demog_medicine_moving_infection'), '(CFixedPoint)1' ), 'te_demog_st_med_inf_moving', 'te_demog_st_med_inf_still' )]"
 te_demog_st_med_inf_still:0 " Medicine: ×#v [State.MakeScope.ScriptValue('te_demog_f_infection_medicine')|2]#!"
 te_demog_st_med_inf_moving:0 " Medicine: ×#v [State.MakeScope.ScriptValue('te_demog_f_infection_medicine')|2]#! → ×#v [State.MakeScope.ScriptValue('te_demog_f_infection_medicine_target')|2]#!"
 te_demog_st_ext:0 "Accidents and Violence"
 te_demog_st_ext_value:0 "×#v [State.MakeScope.Var('te_dg_m_ext').GetValue|2]#!"
 te_demog_st_ext_tt:0 "#b Accidents and Violence#!\nDeaths from violence, traffic and everyday accidents, most of them young men's, at a poor country's rates times:\n Laws and Institutions: ×#v [State.MakeScope.ScriptValue('te_demog_f_external_laws')|2]#!\n#lore Policing, the Ministry of Consumer Protection and, from the Combustion Engine, motor traffic.#!\n [concept_turmoil]: ×#v [State.MakeScope.ScriptValue('te_demog_f_external_turmoil')|2]#!"
 te_demog_st_chr:0 "Chronic Illness, Old Age"
 te_demog_st_chr_value:0 "×#v [State.MakeScope.Var('te_dg_m_chr').GetValue|2]#!"
 te_demog_st_chr_tt:0 "#b Chronic Illness and Old Age#!\nDeaths from the illnesses of age, rising from 40, at a poor country's rates times:\n$te_demog_st_med_chr$\n [concept_sol]: ×#v [State.MakeScope.ScriptValue('te_demog_f_chronic_sol')|2]#!\n Laws and Institutions: ×#v [State.MakeScope.ScriptValue('te_demog_f_chronic_laws')|2]#!\n#lore Old-age pensions. The augmentation laws act through treatment, under Medicine.#!"
 te_demog_st_med_chr:0 "[SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.ScriptValue('te_demog_medicine_moving_chronic'), '(CFixedPoint)1' ), 'te_demog_st_med_chr_moving', 'te_demog_st_med_chr_still' )]"
 te_demog_st_med_chr_still:0 " Medicine: ×#v [State.MakeScope.ScriptValue('te_demog_f_chronic_medicine')|2]#!"
 te_demog_st_med_chr_moving:0 " Medicine: ×#v [State.MakeScope.ScriptValue('te_demog_f_chronic_medicine')|2]#! → ×#v [State.MakeScope.ScriptValue('te_demog_f_chronic_medicine_target')|2]#!"
 te_demog_st_work:0 "Work"
 te_demog_st_work_value:0 "×#v [State.MakeScope.Var('te_dg_m_work').GetValue|2]#!"
 te_demog_st_work_tt:0 "#b Work#!\nDeaths at work among people aged 15 to 64, shared between women and men by their share of the work, at a poor country's rates times:\n Laws: ×#v [State.MakeScope.ScriptValue('te_demog_f_work_laws')|2]#!\n#lore Child labor raises it; Regulatory Bodies and Worker Protections lower it.#!"
 te_demog_st_mat:0 "Childbirth"
 te_demog_st_mat_value:0 "#v [State.MakeScope.Var('te_dg_m_mat').GetValue|0]#! per 100,000 births"
 te_demog_st_mat_tt:0 "#b Childbirth#!\nMothers who die in childbirth: #v [State.MakeScope.Var('te_dg_m_mat').GetValue|0]#! in 100,000 births, against #v [State.MakeScope.ScriptValue('te_demog_k_maternal_base')|0]#! without modern medicine.\n$te_demog_st_med_mat$"
 te_demog_st_med_mat:0 "[SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.ScriptValue('te_demog_medicine_moving_maternal'), '(CFixedPoint)1' ), 'te_demog_st_med_mat_moving', 'te_demog_st_med_mat_still' )]"
 te_demog_st_med_mat_still:0 " Medicine: ×#v [State.MakeScope.ScriptValue('te_demog_f_maternal_medicine')|2]#!"
 te_demog_st_med_mat_moving:0 " Medicine: ×#v [State.MakeScope.ScriptValue('te_demog_f_maternal_medicine')|2]#! → ×#v [State.MakeScope.ScriptValue('te_demog_f_maternal_medicine_target')|2]#!"
 te_demog_st_ontop:0 "Deaths Added on Top"
 te_demog_st_ontop_value:0 "[SelectLocalization( GetScriptedGui('te_demog_state_on_top_sgui').IsShown( GuiScope.SetRoot( State.MakeScope ).End ), 'te_demog_st_ontop_measured', 'te_demog_st_next' )]"
 te_demog_st_ontop_measured:0 "[SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.ScriptValue('te_demog_deaths_on_top_code'), '(CFixedPoint)1' ), 'te_demog_st_ontop_high', 'te_demog_st_ontop_normal' )]"
 te_demog_st_ontop_high:0 "#R ×[State.MakeScope.ScriptValue('te_demog_deaths_on_top')|2]#!"
 te_demog_st_ontop_normal:0 "×#v [State.MakeScope.ScriptValue('te_demog_deaths_on_top')|2]#!"
 te_demog_st_ontop_tt:0 "[SelectLocalization( GetScriptedGui('te_demog_state_on_top_sgui').IsShown( GuiScope.SetRoot( State.MakeScope ).End ), 'te_demog_st_ontop_tt_measured', 'te_demog_st_ontop_tt_pending' )]"
 te_demog_st_ontop_tt_pending:0 "#b Deaths Added on Top#!\nHow far the game's deaths in this state ran from the census's own rate. Measured from the census's second count under the Full setting."
 te_demog_st_ontop_tt_measured:0 "#b Deaths Added on Top#!\nThe census sets this state's deaths at its own rate, and the game adds what the census doesn't model on top. Last count: #v [State.MakeScope.Var('te_dg_cdr_model').GetValue|1]#! deaths per 1,000 people at the census's own rate, #v [State.MakeScope.Var('te_dg_cdr').GetValue|1]#! with the effects on top.\n Effects on the whole state: ×#v [State.MakeScope.ScriptValue('te_demog_deaths_whole_state')|2]#!\n#lore Pollution, devastation, decrees, events, and the late laws and technologies the census doesn't model.#!\n Effects on some of its people: ×#v [State.MakeScope.ScriptValue('te_demog_deaths_some_people')|2]#!\n#lore Above all severe starvation, where #v [State.MakeScope.Var('te_dg_sev_share').GetValue|%0]#! of the people were at the count; also dangerous workplaces and lines on one class or on people outside their homeland.#![SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.Var('te_dg_rate_clamp_d').GetValue, '(CFixedPoint)1' ), 'te_demog_st_ontop_floor', '' )][SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.Var('te_dg_rate_clamp_d').GetValue, '(CFixedPoint)2' ), 'te_demog_st_ontop_cap', '' )]"
 te_demog_st_ontop_floor:0 "\n\n#R The census couldn't bring deaths down to its own rate this year:#! the game's death rate can't fall below a fifth of its base, so deaths ran higher."
 te_demog_st_ontop_cap:0 "\n\n#R The census couldn't raise deaths to its own rate this year:#! the game's death rate can't rise past four times its base, so deaths ran lower."
```

Also:
- `te_demog_st_e0_causes`: replace its list with
  `"Each cause of death runs at the rates of a poor country without modern medicine, times a multiplier that medicine, health laws, institutions and a higher [concept_sol] bring down. The Causes of Death section below breaks each one down."`
  (rule 2: the figures move one section down, none is lost).
- `te_demog_how_mortality`: append
  `" Medicine reaches a state over years: health care access and each treatment close a share of the gap at each count, a tenth at first and more as communications and medical training improve. Turmoil raises deaths from accidents and violence."`

- [ ] **Step 6: Run the tests and the loc checks**

Run:
- `.venv/bin/python -m unittest test_demographics_registry`;
- `python3 organize_loc.py`, then `python3 organize_loc.py --check`;
- `python3 scripts/analysis/check_localization_files.py`;
- `.venv/bin/python concept_reference_audit.py` and `.venv/bin/python loc_coverage_audit.py --strict`.

Expected: OK, and nothing flagged for the new keys.

- [ ] **Step 7: Commit** everything organize_loc rewrote with the rest: "Demographics: what the Causes of Death section
  reads".

---

### Task 8: The section on the state subtab, and the country tab's TODO (owner in-game check)

**Files:**
- Modify: `gui/te_demographics_widgets.gui` (new type `te_state_demog_causes` before `te_state_demog_pyramid`; its
  place in `te_state_demog_content`; the file header's list; the TODO in `te_demog_tab_sections`)
- Test: `test_demographics_registry.py` (new `TestCausesSection`)

**Interfaces:**
- Consumes: Task 7's loc keys and gates.
- Produces: `te_state_demog_causes`; the collapse flag `te_demog_st_causes_closed`.

- [ ] **Step 1: Write the failing tests**

```python
WIDGETS = ROOT / "gui" / "te_demographics_widgets.gui"
MISC_LOC = ROOT / "localization" / "english" / "te_miscellaneous_l_english.yml"


def _gui_type(text, name):
    start = text.index(f"type {name} = ")
    depth, i = 0, text.index("{", start)
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
        if depth == 0:
            return text[start:i]


class TestCausesSection(unittest.TestCase):
    """The Causes of Death section on the state subtab (the plan's Task 8)."""

    @classmethod
    def setUpClass(cls):
        cls.gui = _text(WIDGETS)
        cls.section = _gui_type(cls.gui, "te_state_demog_causes")
        cls.loc = dict(re.findall(r'(?m)^ ([\w.]+):0 "(.*)"$', _text(MISC_LOC)))

    def test_it_sits_after_the_overview(self):
        content = _gui_type(self.gui, "te_state_demog_content")
        order = re.findall(r"(te_state_demog_\w+) = \{\}", content)
        self.assertEqual(order, ["te_state_demog_overview", "te_state_demog_causes", "te_state_demog_pyramid",
                                 "te_state_demog_wealth", "te_state_demog_how"])

    def test_open_by_default(self):
        # rule 7: a section that starts open names its flag _closed
        self.assertIn("te_demog_st_causes_closed", self.section)
        self.assertNotIn("_open'", self.section)

    def test_every_read_sits_under_its_gate(self):
        """Review Focus 1: a key that reads the step's inputs is reached only inside the causes gate's container, and
        one that reads the measured split only through a SelectLocalization on the on-top gate."""
        inner = self.section.split("te_demog_state_causes_sgui').IsShown", 2)[2]   # past the pending line's Not(...)
        outer = self.section[: len(self.section) - len(inner)]
        for key in re.findall(r'(?:text|tooltip) = "(te_demog_st_\w+)"', outer):
            self.assertIn(key, ("te_demog_sec_causes", "te_demog_st_causes_pending"), key)
        split = re.compile(r"te_dg_ed_state|te_dg_sev_share|te_dg_rate_clamp_d|te_demog_deaths_")
        for key in ("te_demog_st_ontop_value", "te_demog_st_ontop_tt"):
            self.assertIsNone(split.search(self.loc[key]), key)
            self.assertIn("te_demog_state_on_top_sgui", self.loc[key])

    def test_the_on_top_row_is_full_only(self):
        label = self.section.index('"te_demog_st_ontop"')
        row = self.section[self.section.rindex("te_demog_figure_row", 0, label):label]
        self.assertIn("te_demog_state_full_sgui", row)
        self.assertEqual(self.section.count("te_demog_state_full_sgui"), 1, "only the on-top row is Full-only")

    def test_the_country_tab_keeps_its_todo(self):
        tab = _gui_type(self.gui, "te_demog_tab_sections")
        self.assertRegex(tab, r"### TODO \(#894\): .*Causes of Death")
```

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestCausesSection`
Expected: ERROR (`te_state_demog_causes` not found).

- [ ] **Step 3: The section** (before `type te_state_demog_pyramid`)

```
	### Causes of Death (owner, 2026-10-11; docs/superpowers/plans/2026-10-11-demographics-causes-of-death.md):
	### Health Care Access and the five causes the census's life table runs on, each with its factors on hover
	### (the generated te_demog_f_*, which the census multiplies), then, under Full, the deaths the game added on
	### top of the census. Open by default (rule 1), with a flag of its own (te_demog_st_causes_closed). The rows sit
	### under te_demog_state_causes_sgui (the step's inputs exist: a census from before this build waits a step);
	### the on-top row under te_demog_state_full_sgui, its figure picked by te_demog_state_on_top_sgui (a measured
	### scale). Labels fit te_demog_figure_row's 240-unit cell: "Chronic Illness, Old Age" is the longest, 24
	### characters, about 227 in the medium font with the 10%; "380 per 100,000 births" is the longest value, 22,
	### about 208: check it doesn't elide in game.
	type te_state_demog_causes = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes
		spacing = 2

		te_demog_section_header = {
			blockoverride "left_text" {
				text = "te_demog_sec_causes"
			}
			blockoverride "onclick" {
				onclick = "[GetVariableSystem.Toggle('te_demog_st_causes_closed')]"
			}
			blockoverride "onclick_showmore" {
				visible = "[GetVariableSystem.Exists('te_demog_st_causes_closed')]"
			}
			blockoverride "onclick_showless" {
				visible = "[Not(GetVariableSystem.Exists('te_demog_st_causes_closed'))]"
			}
		}

		te_demog_panel = {
			visible = "[Not(GetVariableSystem.Exists('te_demog_st_causes_closed'))]"

			te_demog_text = {
				visible = "[Not( GetScriptedGui('te_demog_state_causes_sgui').IsShown( GuiScope.SetRoot( State.MakeScope ).End ) )]"
				text = "te_demog_st_causes_pending"
			}

			flowcontainer = {
				visible = "[GetScriptedGui('te_demog_state_causes_sgui').IsShown( GuiScope.SetRoot( State.MakeScope ).End )]"
				direction = vertical
				ignoreinvisible = yes
				spacing = 3

				te_demog_figure_row = {
					tooltip = "te_demog_st_acc_tt"
					blockoverride "row_label" {
						text = "te_demog_st_acc"
					}
					blockoverride "row_value" {
						text = "te_demog_st_acc_value"
					}
				}
				te_demog_figure_row = {
					tooltip = "te_demog_st_inf_tt"
					blockoverride "row_label" {
						text = "te_demog_st_inf"
					}
					blockoverride "row_value" {
						text = "te_demog_st_inf_value"
					}
				}
				te_demog_figure_row = {
					tooltip = "te_demog_st_ext_tt"
					blockoverride "row_label" {
						text = "te_demog_st_ext"
					}
					blockoverride "row_value" {
						text = "te_demog_st_ext_value"
					}
				}
				te_demog_figure_row = {
					tooltip = "te_demog_st_chr_tt"
					blockoverride "row_label" {
						text = "te_demog_st_chr"
					}
					blockoverride "row_value" {
						text = "te_demog_st_chr_value"
					}
				}
				te_demog_figure_row = {
					tooltip = "te_demog_st_work_tt"
					blockoverride "row_label" {
						text = "te_demog_st_work"
					}
					blockoverride "row_value" {
						text = "te_demog_st_work_value"
					}
				}
				te_demog_figure_row = {
					tooltip = "te_demog_st_mat_tt"
					blockoverride "row_label" {
						text = "te_demog_st_mat"
					}
					blockoverride "row_value" {
						text = "te_demog_st_mat_value"
					}
				}
				te_demog_figure_row = {
					visible = "[GetScriptedGui('te_demog_state_full_sgui').IsShown( GuiScope.SetRoot( State.MakeScope ).End )]"
					tooltip = "te_demog_st_ontop_tt"
					blockoverride "row_label" {
						text = "te_demog_st_ontop"
					}
					blockoverride "row_value" {
						text = "te_demog_st_ontop_value"
					}
				}
			}
		}
	}
```

`te_state_demog_content`: `te_state_demog_causes = {}` between `te_state_demog_overview = {}` and
`te_state_demog_pyramid = {}`. Add `te_state_demog_causes` to the subtab comment's "Sections:" list and the file
header's list, and `te_demog_st_causes_closed` to the flags sentence ("Four flags of this subtab's own").

- [ ] **Step 4: The country tab's TODO** (`te_demog_tab_sections`, between `te_demog_overview = {}` and
  `te_demog_sec_pyramid = {}`)

```
			### TODO (#894): the country's Causes of Death, people-weighted over its census states (te_dg_c_*_w
			### in te_demog_country_census already weights the cause multipliers), once the state subtab's
			### te_state_demog_causes has been seen in game (owner, 2026-10-11). It goes here, after the overview.
```

- [ ] **Step 5: Run the tests and the GUI checks**

Run:
- `.venv/bin/python -m unittest test_demographics_registry`;
- `python3 scripts/analysis/check_gui_lint.py`;
- `.venv/bin/python gui_reference_audit.py --strict`;
- `python3 scripts/format_paradox_tabs.py --check gui/te_demographics_widgets.gui`.

Expected: OK; no lint error. A warning on markup no mod `.gui` used before must not appear: every element here is
already in the file.

- [ ] **Step 6: Commit**: "Demographics: the Causes of Death section on the state subtab".

- [ ] **Owner in-game check** (before Task 10's docs; see Task 10 Step 4 for the list). Merge `origin/main`, read
  the deploy dry run alone, then deploy from the full checkout, per CLAUDE.md "Play-testing unmerged work".

---

### Task 9: The harness reads the step's inputs

**Files:**
- Modify: `scripts/analysis/demographics_harness.py` (`FIDELITY_VARS`, `fidelity_rows`, `_fidelity`'s header lines; a
  helper `census_inputs`)
- Test: `test_demographics_harness.py` (`TestFidelity`)

**Interfaces:**
- Consumes: `M.Inputs.turmoil`, `M.Inputs.medicine` (Task 1); the variables of Tasks 3–4.
- Produces: `H.census_inputs(inp, got) -> M.Inputs`. With every input variable in `got`, it returns `inp` with the
  step's medicine, turmoil, crowding and plain type sums; otherwise `inp` unchanged.

- [ ] **Step 1: Write the failing tests**

In `TestFidelity.save`, accept extra variables: `def save(self, crowded, m_inf, m_mat=None, extra=())`, appending
`extra`'s `(name, value)` pairs to the variable block. Then:

```python
    STORED = (("te_dg_acc", 0.45), ("te_dg_trt_inf", 0.2), ("te_dg_trt_mat", 0.3), ("te_dg_trt_chr", 0.0),
              ("te_dg_in_ext", 0.0), ("te_dg_in_work", 0.0), ("te_dg_in_chr", 0.0), ("te_dg_in_turm", 0.5),
              ("te_dg_in_crowd", 0.0))

    def test_a_census_from_this_build_is_read_on_its_own_inputs(self):
        """The Causes of Death plan: medicine drifts, so the save's techs and laws give the targets, not what the step
        used. fidelity runs the model on the step's stored inputs."""
        stored = dict(self.STORED)
        inp = M.Inputs(sol=self.GAME_SOL, literacy=self.GAME_LIT, turmoil=0.5,
                       medicine={"access": 0.45, "infection": 0.2, "maternal": 0.3, "chronic": 0.0})
        mult = M.cause_multipliers(inp)
        path = self.save(False, mult["infection"], mult["maternal"] * H.P.MATERNAL_PER_100K_BIRTHS, extra=self.STORED)
        (_tag, _sid, _people, pairs, _sol, _lit), = H.fidelity_rows(path, DM.load_carriers())
        for cause in ("infection", "maternal"):
            game, model = pairs[cause]
            self.assertAlmostEqual(game / model, 1.0, places=4, msg=cause)
        self.assertEqual(stored["te_dg_in_turm"], H.census_inputs(inp, stored).turmoil)

    def test_a_census_from_before_reads_the_save(self):
        got = {"te_dg_sol": 8.0, "te_dg_lit": 0.2}
        inp = M.Inputs(sol=8.0, literacy=0.2)
        self.assertIs(H.census_inputs(inp, got), inp)
```

(The tiny save's state carries no health law or treatment tech, so the stored medicine is off its targets and the old
path would read a mismatch.)

- [ ] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_harness.TestFidelity`
Expected: ERROR (`census_inputs` not defined).

- [ ] **Step 3: The harness**

```python
# The step's own inputs (the Causes of Death plan): with them the model runs on what the census used, so a mismatch is
# the script against the model; a census from before them is read from the save's techs, laws and modifiers.
CENSUS_INPUT_VARS = ("te_dg_acc", "te_dg_trt_inf", "te_dg_trt_mat", "te_dg_trt_chr", "te_dg_in_ext",
                     "te_dg_in_work", "te_dg_in_chr", "te_dg_in_turm", "te_dg_in_crowd")
FIDELITY_VARS = ("te_dg_sol", "te_dg_lit") + tuple(var for _c, var, _s in FIDELITY_CAUSES) + CENSUS_INPUT_VARS


def census_inputs(inp, got):
    """`inp` with the step's stored inputs, when the save holds them all; `inp` itself otherwise."""
    if not all(v in got for v in CENSUS_INPUT_VARS):
        return inp
    medicine = {"access": got["te_dg_acc"]}
    medicine.update({c: got[f"te_dg_trt_{P.CAUSE_SHORT[c]}"] for c in P.MEDICINE_CAUSES})
    mods = dict(inp.mods)
    for cause, types in P.MORTALITY_TYPES.items():
        for t in types:
            mods[t] = 0.0
        mods[types[0]] = got[f"te_dg_in_{P.CAUSE_SHORT[cause]}"]
    return dataclasses.replace(inp, medicine=medicine, turmoil=got["te_dg_in_turm"], crowding=got["te_dg_in_crowd"],
                               mods=mods)
```

In `fidelity_rows`, after building `inp`: `inp = census_inputs(inp, got)`. In `_fidelity`, count the states read on
their own inputs and print one line, for example "N states read on the census's stored inputs (medicine as it had
spread, turmoil); M from the save's techs and laws". Count also the states whose stored medicine is more than
`P.MEDICINE_SNAP` from the targets the save's techs and laws give, and print "medicine still spreading in K".

- [ ] **Step 4: Run the harness tests, then commit**

Run: `.venv/bin/python -m unittest test_demographics_harness`
Expected: OK.

Commit: "Demographics harness: fidelity reads the step's own inputs".

---

### Task 10: Docs, the player guide and the in-game checklist

**Files:**
- Modify: `docs/systems/mod_systems.md` (§ Demographics)
- Modify: `docs/guides/python_tools.md` (the harness's `fidelity` line)
- Modify: `docs/player_guide/08-states.md` (§ Demographics), `docs/player_guide/06-politics.md` (§ New decrees), then
  rebuild `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`
- Modify: `docs/superpowers/plans/2026-10-10-demographics-phase2-engine-rates.md` §2 (one "Amended 2026-10-11 (3)"
  bullet pointing here)

- [ ] **Step 1: mod_systems.md.** In § Demographics:
  - **Files table:** the new script values, effects, sguis, the decree, the type's carriers, the GUI type.
  - **Variable families:** add a row "Causes of Death (2026-10-11)": `te_dg_acc`, `te_dg_trt_*`, `te_dg_in_*`; under
    Full `te_dg_ed_state`, `te_dg_sev_share`, `te_dg_rate_clamp_d`.
  - **A new subsection "Causes of Death (2026-10-11)"** after "The census's births and deaths". It covers:
    - the factor table and why the factors read stored inputs;
    - the drift (rate, carriers, decree, snap, seed and old-save behaviour, the re-seed accepted);
    - turmoil, with the vanilla `state_mortality_turmoil_mult` note;
    - the measured split with its formula (whole state = `te_dg_ed_state ÷ te_dg_ed_target`, some of its people =
      `te_dg_ed ÷ te_dg_ed_state`), and why os_d can't split dz;
    - the red threshold, the clamp side and the severe-starvation share;
    - the #894 note that the walk's severe term (+1.0) and the step-day snapshot move the figure;
    - the release's handling of the decree.
  - **"Owner checks in game":** items 11–13 from Step 4 below, short.
  - **`gen_demographics.py`'s bullet:** "the cause multipliers are products of one script value per factor
    (`P.CAUSE_FACTORS`), on the step's stored inputs".

- [ ] **Step 2: The player guide.** Match the depth already there (CLAUDE.md "Keep the player guide current").
  - `08-states.md`, "What the tab shows": "The subtab shows one state's overview, pyramid and wealth" becomes "The
    subtab shows one state's overview, causes of death, pyramid and wealth".
  - `08-states.md`, "Reading the figures", after "...reaches less than half the people.":

    "Medicine also takes time to arrive. A new medical technology, health law or Ministry of Health level moves a
    state's medicine part of the way at each yearly count: a tenth of the gap at first, and up to two fifths once
    the Electric Telegraph, Modern Nursing, Radio, Intergovernmental Organizations, the World Wide Web and
    Telemedicine are researched. Under Full, the Medical Outreach decree adds a fifth more in one state. Turmoil
    raises deaths from accidents and violence, by half at full turmoil. The subtab's Causes of Death section shows a
    state's health care access and each cause's multiplier; hover a row for what makes it up and where medicine is
    heading. Under Full it also shows the deaths added on top of the census's own, in red from a quarter above it,
    split into effects on the whole state and effects on some of its people, such as severe starvation."
  - `06-politics.md`, § New decrees: "The mod adds 15 decrees." becomes "The mod adds 15 decrees, and a 16th under the
    Demographics rule's Full setting." Add the row `| Medical Outreach (Demographics, Full only) | Medical Degrees |
    New medicine reaches the state faster; see [States and population](08-states.md#demographics) |`.
  - Run `python3 scripts/analysis/check_player_guide_style.py --strict`, rebuild with
    `.venv/bin/python scripts/build_player_guide.py`, and check `scripts/build_player_guide.py --check`.

- [ ] **Step 3: python_tools.md and the phase 2 plan.**
  - `python_tools.md`: the harness list's `fidelity` line gains "runs the model on the census's stored inputs (the
    drifted medicine, turmoil) when the save holds them".
  - The 2026-10-10 plan's §2: one bullet, "Amended 2026-10-11 (3): the Causes of Death plan
    (`docs/superpowers/plans/2026-10-11-demographics-causes-of-death.md`) adds turmoil to the external cause and
    drifts medicine; both reach M, under Full only."

- [ ] **Step 4: The in-game checklist** (for the owner; the PR body carries it, and `mod_systems.md` keeps 11–13):
  1. **Layout.** A new 1836 game under Full: the state subtab shows Causes of Death after the overview, open. No row
     label or value ends in "...". Childbirth's "670 per 100,000 births" is the longest value.
  2. **Health Care Access.** 40% in an unincorporated colony. More in a Ministry of Health country's incorporated
     states, with the hover's two lines adding up to the row.
  3. **The hovers multiply to their rows.** Check one: Infection and Hunger's factors multiplied give its ×figure.
  4. **Medicine drifts.** Enact a health law or research Modern Nursing through the console: the Medicine line reads
     "×a → ×b" at once. After the state's next count the row has moved about a tenth to a fifth of the way.
  5. **Medical Outreach.** In the decree list under Full only, and absent in a Display only game. Offered only where
     medicine is behind. Issuing it raises the hover's "closes N% of the gap" by 20 points in that state. Option l's
     `diff=` shows the same.
  6. **Deaths Added on Top.** Absent outside Full. "After the next count" on a state's first Full count. A ×figure
     from the next. Red from ×1.25: try a famine state, or late-game India. The severe-starvation share reads in the
     hover. Option n's `ed_state=`, `sev=` and `clamp_d=` match the hover.
  7. **Turmoil.** A state in high turmoil shows Turmoil above ×1.00 under Accidents and Violence.
  8. **An old save** from before this build: the section reads "after its next count" until each state's step.
  9. **`debug.log`:** no "Failed to fetch variable" or errors from `te_demog_f_*`, `te_dg_acc`, `te_dg_in_*` or the
     decree.

- [ ] **Step 5: Run the whole suite and the checks:**
  - `.venv/bin/python -m unittest discover -s . -p 'test_*.py'` (read the summary with `grep -E '^(Ran |OK|FAILED)'`);
  - `.venv/bin/ruff check .`;
  - `python3 scripts/format_paradox_tabs.py --check` on the changed `.txt`/`.gui`;
  - `python3 organize_loc.py --check`;
  - `.venv/bin/python scripts/generators/gen_demographics.py --check`;
  - `python3 scripts/build_player_guide.py --check`;
  - the CI audits (`.github/workflows/ci.yml`'s list);
  - the PEP 701 grep on the changed `.py` files.

- [ ] **Step 6: Commit**: "Demographics: docs, guide and checklist for Causes of Death".

---

## Self-review notes (for the executor)

- **Order of the two Task 5 tests that read display values:** write `te_demog_deaths_on_top`, `_whole_state` and
  `_some_people` in Task 5 (Step 5) so `TestDeathsOnTopSplit` runs there; Task 7 adds the rest of the display values
  beside them.
- **`_mod_fixtures` and `_stored`** are defined once in `test_demographics_registry.py`, above `_engine_for`, and used
  by Tasks 3, 4 and 7.
- **The generated files change twice** (Tasks 3 and 5). Regenerate after each; never merge them by hand.
