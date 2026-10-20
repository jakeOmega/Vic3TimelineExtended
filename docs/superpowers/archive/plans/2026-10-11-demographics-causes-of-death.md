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
- **Factors read only what the step stored.** Each seed and step stores the inputs the census used: the drifted
  health-care access and treatments, the law and institution type sums, turmoil and crowding. It also keeps copies of
  the walk's SoL and literacy (`te_dg_in_sol`, `te_dg_in_lit`), since a walk without a step rewrites those (the review
  of #916). Between steps the hover still multiplies to the row's figure.
- **Medicine drifts.** Health-care access and the three treatments move a share of the gap to their targets at each
  census step. The share is `0.1 + modifier:state_medical_diffusion_add`, from six technologies and the Medical
  Outreach decree. Before the numbers are approved, the owner sees how far life expectancy lags its target over 20
  years (Task 3).
- **The deaths added on top are split at both ends of the window dz measured.** Since #907 the census books a window
  at the mean of the engine's rate at its two ends, so the split works at both ends (re-planned 2026-10-11 against
  #907 and #913; Task 6):
  - the pops' own lines at the window's end come from the walk's own sums (`w_ed − w_edr − (1 + read) × w_ed0`);
  - at its start, the refresh that stores the start rate `te_dg_sr_d` stores the start's own lines beside it
    (`te_dg_sp_d`, `te_dg_ss_d`). It is the one place that knows the change in M, and that change doesn't reach a pop
    the engine floors at 0.
  - The window's events less those lines are the whole state's part.
  - Severe starvation's part is summed by one Full-only test per pop in the walk, beside the people it holds.

**Tech Stack:** Paradox script (Victoria 3 1.14.5), the Python twin and harness (`scripts/analysis/demographics_*.py`),
the generator `scripts/generators/gen_demographics.py`, unittest with the repo's script interpreter
(`test_demographics_registry.py`'s `_Engine`).

**Spec:** the owner's approved design (2026-10-11), restated in "Design" below, and #894's section "The panel: what a
player can't see". It builds on:
- `docs/superpowers/archive/plans/2026-10-10-demographics-phase2-engine-rates.md` (the census's term M and the on-top scales);
- `docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md` (the moved lines);
- the trapezoid fix (#907, b8c993b4: the window at the mean of the engine's rate at its two ends) and severe
  starvation by the starvation value (#913, 209401a6).

Read `docs/systems/mod_systems.md` § Demographics first. An independent review (2026-10-11, approve with fixes) shaped
this revision; its points are folded in.

## Dependencies and shared edits

- **Task 6 builds on #907 and #913, both on main and merged into this branch** (b8c993b4, 209401a6; re-planned
  2026-10-11). It reads:
  - from #907 (the window is the mean of the engine's rate at its two ends):
    - `te_demog_window_events`, the walk's tail. Its limit is `te_demog_effects_run`, `te_dg_sr_b` and `te_dg_sr_d`.
    - `te_dg_sr_b` / `te_dg_sr_d`, the rate per head at the window's start. `te_demog_rates_refresh` stores them,
      `te_demog_fast_refresh_rates` moves them, and four sites remove them: `te_demog_rates_clear`, the refresh's
      no-start branch, `te_demog_seed` and `te_demog_fast_clear_rates`.
    - The walk's locals `te_dg_w_ed0m` / `te_dg_w_eb0m`: the bare curves of the pops the engine doesn't floor at 0.
    - The refresh's locals `te_dg_rate_prev_d` and `te_dg_rate_lines_d`; `te_demog_k_window_start_weight`
      (`P.WINDOW_START_WEIGHT`, 0.5); `demographics_model.window_events(end_rate, start_rate)`.
  - from #913: severe starvation read in 0.05 food-security steps × the starvation value. The generator's
    `_starvation_ladder(o, coefficient, _starvation_buckets(severe=True))` writes the step ladder;
    `demographics_model.starvation_terms` gives the exact term.
- **Shared edits with #906** (Late Marriage and Birth Spacing, branch `docs/demographics-late-marriage-plan`):
  - `te_demog_step_begin`: #906 puts `te_demog_practices_step` before `te_demog_prepare`. This plan puts
    `te_demog_medicine_drift` before it too; tests assert relative order only.
  - `te_demog_seed`.
  - `_engine_for`'s signature: #906 adds `place=`, `targets=`; this plan adds `real_multipliers=`.
  - `demographics_model.Inputs`: both add fields at the end, with defaults.
  - `demographics_params` near `DEMOG_TYPES`.
  - The harness's `fidelity`: #906 notes it won't run on the build's saves; Task 10 rewrites its inputs.
- **Generated files** (`te_demog_generated_values.txt`, `te_demog_generated_effects.txt`) are regenerated after each
  merge, never merged by hand.

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
   | Childbirth | `380 per 100k births` | Medicine |
   | Deaths Added on Top (Full only) | `×1.62`, red from ×1.25 | the census's own deaths per 1,000 against the year's; effects on the whole state (and the census's own lag since its last count); severe starvation `×a (X% of its people)`; other effects on some of its people `×b`; the clamp, when it bit |

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
4. **Under Display only, the drift and turmoil run too** (the census runs under `te_demog_cohorts_run`). The section's
   figures and the shown life expectancy move with them; the game's births and deaths don't, since there is no M
   outside Full. That meets the owner's rule (nothing changes outside Full): Display only shows what Full would do.
5. **The country tab:** not in this change. A TODO comment marks the spot (#894 tracks it).
6. **Germany's excess deaths** (investigation done, 2026-10-11): the per-pop effect behind `dz` +0.6 to +1.0 is severe
   starvation during an in-game famine. The hover splits the pops' own lines into severe starvation,
   `×a (X% of its people)`, and other effects on some of its people, `×b`.

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

Half-lives of a gap: 6.6 years at 0.1 (1836), 3.1 at 0.2 (era 3), 2.4 at 0.25 (era 4), 1.4 at 0.4 (era 10). In life
expectancy that is large: a full treatment gap is about 10 years of e0 at SoL 15, and at 0.1 about 59% of it remains
after 5 years. So the owner approves these numbers from Task 3's lag curve, not from the half-lives. Alternatives if
the owner prefers: Malaria Prevention (era 4, public-health campaigns), Television Broadcasting (era 7), Digital
Education (era 9).

### The Medical Outreach decree (proposal)

`decree_medical_outreach`, "Medical Outreach": doctors and nurses sent to bring a state's practice up to the
country's. Its terms:
- `state_medical_diffusion_add = 0.2`;
- cost 100 authority, as most of the mod's decrees;
- unlocked by Medical Degrees;
- `country_trigger = { te_demog_effects_run = yes }`, which hides it outside Full (vanilla `00_decree.txt`'s header:
  the country trigger decides whether the decree is "permitted/shown in interface");
- `state_trigger`: the state's medicine is behind its targets, or the decree is already issued there (Pollution
  Control's pattern);
- `ai_weight`: by the state's medicine gap, as the owner's shared-mechanics rule wants (the AI uses what the player
  uses).
  - It follows vanilla Road Maintenance's pattern (`00_decree.txt`): +100 above a gap of 0.1, +100 more above 0.3,
    with lower thresholds (0.05, 0.2) where the decree is already issued.
  - The weight is 0 once the state has caught up.
- texture: vanilla's `decree_emergency_relief.dds`, a placeholder. Final-art subject: a doctor's bag over a map pin.

A release comments it out whole (Task 7).

## What the code says (corrections to the brief)

These came out of reading `te_demog_rate_effects.txt`, the walk, the trapezoid branch and the vanilla files. The
independent review (`review-905.md`) confirmed 1–4 against the code. The PR lists them as owner questions.

1. **The whole state's factor includes the moved lines' on-top family.** The engine gives each pop
   `bare × max(0, 1 + S + own)`, S being the state read. Under Full, S = os + M (os: the state-level lines on top) and
   M = tb − 1 − rep − os(1 − tb) + q·tb. Summed over the state (rep cancels the absorbed per-pop terms):

   engine deaths = target × (1 + os_d + **q_d**) + Σ bare_p × (the pops' own lines on top)

   q_d is `state_demog_ontop_mortality_mult` (Mental Health Awareness −0.05, Biological Immortality −0.2, Mind
   Backups −0.05). So the brief's whole-state factor, ×(1 + os_d), leaves those out.
2. **The split must describe the window dz measured, at both of its ends.** `te_demog_on_top_scales` measures dz
   from `te_dg_ed`. Since #907, `te_dg_ed` is the window's events: `w × te_dg_sr_d × people + (1 − w) × te_dg_w_ed`,
   times the window's months (`te_demog_window_events`; w = 0.5).
   - The last refresh's `te_dg_os_d` is one refresh newer than that window, and it holds only the state-level lines.
     A state line that changed in between, a clamped M or a year's drift in the target breaks any identity built on
     it.
   - **Chosen instead:** take the pops' own lines off the window's events at each end. What is left is the whole
     state's part. Each pop gives `bare × max(0, 1 + read + absorbed + own)`.
     - **At the end** (the walk, the same effect): `P_end = w_ed − w_edr − (1 + read) × w_ed0`, read being
       `modifier:state_mortality_mult` (M, the state-level lines, fast mode's term). For an unfloored pop that is
       `bare × own`. For a floored one it is `−bare × (1 + read + absorbed)`: its own lines took its deaths to 0.
     - **At the start:** the refresh that stores `te_dg_sr_d` stores beside it the start's own lines per head:
       `te_dg_sp_d = (P_end' − ΔM × (w_ed0' − w_ed0m')) / people`. Here ΔM = `te_dg_md − te_dg_rate_prev_d −
       te_dg_rate_lines_d`, `te_dg_sr_d`'s own multiplier.
       - The change in M reaches only the pops the engine doesn't floor (`te_dg_sr_d` moves by `ΔM × w_ed0m'`), so
         a floored pop's own lines absorb it.
       - It also stores `te_dg_ss_d = w_sevd' / people`, severe starvation's part, which the change in M doesn't
         touch.
       - Fast mode moves `te_dg_sp_d` by `−ΔF × (w_ed0 − w_ed0m) / people` as it moves `te_dg_sr_d` by
         `ΔF × w_ed0m / people`.
       - Why store them (the review of Task 6):
         - `te_dg_ss_d` can't be rebuilt: the walk at the window's start isn't kept.
         - `te_dg_sp_d` could in principle be rebuilt at walk time from `te_dg_sr_d`, `te_dg_cdr_model`, `te_dg_tb_d`,
           `te_dg_os_d`, `te_dg_md`, `te_dg_rep_d` and fast mode's term. But that is inexact where `te_dg_os_d` hit
           `te_demog_k_rate_total_min`, and it assumes none of them is rewritten before the walk.
         - Storing them is exact. Its cost: the split adds seven state variables under Full (`te_dg_sp_d`,
           `te_dg_ss_d`, `te_dg_ed_state`, `te_dg_ed_sev`, `te_dg_sev_share`, `te_dg_rate_clamp_d`,
           `te_dg_ed_clamp_d`) and one severe-starvation test per pop.
     - **Over the window:** `ED_pop = (w × te_dg_sp_d × people + (1 − w) × P_end) × months / 100,000`, `ED_sev` the
       same with `te_dg_ss_d` and `w_sevd`, and `ED_state = ED − ED_pop`. Where `te_demog_window_events` took the
       snapshot (no start rate), the snapshot's `P_end` and `w_sevd`.
   - Whole state: `ED_state ÷ target`. It holds the state-level lines and the moved lines' on-top family over the
     window, the absorbed lines M nets (mild starvation), and the census's own lag (M a window old, the model's rate
     drifting).
   - Some of its people: `ED ÷ ED_state`. Severe starvation is `(ED_state + ED_sev) ÷ ED_state`; the rest is
     `ED ÷ (ED_state + ED_sev)`.
   - **The product is `ED ÷ target`, which is `1 + dz` except in four cases** (corrected by the review of Task 6):
     - **dz hit either end of its range** (`ON_TOP_SCALE_MIN` −0.9, `ON_TOP_SCALE_MAX` +4).
       (2026-10-20: no longer: dz has only its natural floor, −1, which is no deaths.)
     - **A display value's `min = 1` (one person) bites,** which only happens on a tiny state.
     - **An end's read is below −1 (`1 + read < 0`).** That end's whole-state part is then negative: it counts every
       pop unfloored, while the engine floors them. The split moves deaths into "other effects on some of its people",
       and further down `ED_state` floors at 0 and the product reads 0.
       - M keeps the read at or above −0.8 when it is fitted, unless the read without it is already below that.
         So only the start's whole-state part is at least 0.2 × the bare deaths.
       - The end reaches `1 + read < 0` only through state-level lines falling inside the window after M was fitted,
         or through "other" alone below `te_demog_k_rate_total_min`. Both are rare: vanilla's largest negative state
         line is −0.5.
       - Floor crossings from M's change cancel out of `ED_state`, since both of its parts count every pop. They reach
         the product only through `te_dg_ed`'s own floor at 0 (`te_demog_window_events`).
     - **A second walk in a year without a step** (a state's second yearly pulse, `te_demog_state_yearly`). It
       rewrites `te_dg_ed` and the split but not dz or `te_dg_ed_target`, so until the next step the factors multiply
       to the new `te_dg_ed` over the old target. #907 documents the same case for M and the start rate.
   - A save from #907 but before this build has `te_dg_sr_d` and no start parts. Its window can't be split
     consistently, so the split's variables go and the row waits for the next count.
3. **Vanilla does have turmoil mortality.** The three `state_turmoil*` static modifiers carry none, as the brief says.
   But `state_mortality_turmoil_mult` ("Mortality per Turmoil") sits on several carriers:
   - Militarized Police +0.004 (`00_policing.txt`);
   - the Violent Suppression decree +0.02;
   - the Second Amendment +0.005;
   - `ig_trait_wounded_honor` +0.15;
   - about 18 event modifiers (intercommunal violence +0.2/+0.3, anarchist terror attack +0.2).

   Its scaling is unknown and measured at about 0 (growth probe). The walk leaves it out of `te_demog_pop_death_mult`,
   so it is in neither dz nor the census. The new census term is the violence of unrest itself; those lines stay
   engine-applied on top. Not double counted in practice, but not "no turmoil mortality" either.
4. **The first Full step after a seed has no target.** `te_demog_on_top_scales` writes `te_dg_ed_target = 0` and
   `dz = 0`, so the row would read ×1.00 when nothing was measured. The row's gate asks for `te_dg_ed_target > 0`.
5. **`te_dg_rate_clamped` is one flag for births and deaths, and the refresh writes it after dz is measured.**
   - To say why deaths weren't set, the refresh also stores `te_dg_rate_clamp_d`: 0 none, 1 the floor (the game's rate
     can't fall below a fifth of its base), 2 the cap (+300%).
     - **2026-10-20:** the cap is gone and the floor is the engine's own −1, so `te_dg_rate_clamp_d` is 0 or 1, and
       "can't fall below a fifth of its base" was the mod's −0.8, never the engine's. The floor's hover now says the
       census had no base rate left to take off (`te_demog_st_ontop_end_floor`).
   - That flag describes the next window's M, not the one dz measured. So `te_demog_on_top_scales` copies the last
     refresh's flag to `te_dg_ed_clamp_d` before the refresh runs, and removes the copy when there's no flag. The hover
     and the gate read the copy.
   - With the copy absent, the row also stays hidden on the first Full step after Display only. That step has a target
     (`step_finish` writes `te_dg_cdr_model` under any rule), but its window ran with no M.
6. **The walk's expected deaths leave out turmoil's and wealth's lines** (`te_demog_pop_death_mult`'s comment). So
   dz, and the "some of its people" part, don't include Private Health Insurance's cut for the wealthy or the
   per-turmoil lines. The hover names only what the walk counts.
7. **Chronic's "Laws and Institutions" is Old Age Pension alone today** (`state_chronic_mortality_mult` −0.05). The
   augmentation laws act through chronic treatment, so they show under Medicine.
8. **"Laws and Institutions" on Accidents and Violence includes the Combustion Engine**, a technology
   (`state_external_mortality_mult` +0.3: motor traffic). The label stays the owner's; the hover's note names it.
9. **Fast mode** (console only): `te_demog_fast_deaths` is (K − 1) × the state's average multiplier, the pops' own
   lines included, and it sits in the state's read. So under fast mode the whole state's part also carries K − 1
   times a famine's share. The section isn't a fast-mode tool; `mod_systems.md` says so.

**Note (#894, not planned here):** the "some of its people" figure reads the walk's dz. The walk's severe-starvation
death term (+1.0 × bare) was never fitted and may be about 0.6. Fixing it will move the figure.

## Owner decisions (to confirm in the PR)

1. The corrections above, especially 1–2 (the split, built on the trapezoid) and 3 (turmoil).
2. **The drift numbers, from Task 3's lag curve** (an owner stop before Task 4):
   - `DIFFUSION_BASE` 0.1, `DIFFUSION_MAX` 1.0, `MEDICINE_SNAP` 0.005;
   - six carriers at +0.05 each;
   - the decree +0.2.
   **Approved by the owner, 2026-10-11, as proposed** (from Task 3's lag table; see Task 3's owner stop).
3. The other numbers (proposals):
   - `TURMOIL_EXTERNAL_WEIGHT` 0.5: about −0.46 to −0.64 years of life expectancy at full turmoil, by the model at
     SoL 8–25 (the review confirmed it; accidents and violence are a small cause);
   - `DEATHS_ON_TOP_HIGH` ×1.25. People-weighted dz ran +0.05 in 1900 and +0.19 to +0.24 by 2000–2020 in the fast run;
     Germany's famine states ran +0.6 to +1.0. So ×1.25 flags famine-class states and leaves ordinary late-game ones
     neutral.
4. The carriers and the decree's name, cost and unlock (tables above). The AI weight follows the shared-mechanics
   rule and needs no question.
5. The section's place: after the overview, before the pyramid (life expectancy and its causes sit together, rule 5).
6. Save size: under Full, 18 more variables per census state (11 under Display only), against about 345 now (+5%).
   That is the eleven stored inputs plus Task 6's seven (corrected by the reviews of Task 6 and #916: SoL and literacy
   are kept as the step used them).
   The walk adds one severe-starvation test per pop, under Full only.
7. Execution: native, with a fresh review of Tasks 4–6 (the risky script) and a whole-branch review at the end, as
   the engine-lines plan.

## Global Constraints

- **Nothing changes outside Full** (owner rule). The census's drift and turmoil reach the game only through M (Design
  4). The decree is hidden outside Full through `te_demog_effects_run`, the only reader of the rule besides
  `te_demog_cohorts_run` (`test_only_the_wrappers_read_the_rule`).
- **A release has no census:** `scripts/release/comment_out_census_inputs.py` comments out the new type's carriers and
  the decree whole (Task 7).
- **Generated files are never hand-edited:** `te_demog_generated_values.txt` and `te_demog_generated_effects.txt` come
  from `gen_demographics.py`; `gen_demographics.py --check` stays clean; after a merge, regenerate.
- **The GUI reads variables and cheap script values only** (a `.gui` re-evaluates every frame); nothing walks. A read
  of a missing variable logs every frame, so every figure sits under a scripted-GUI gate (gotchas #14, #23).
- **No new per-pop multiplier in the walk.** The split reads sums the walk already has; the only per-pop addition is
  one severe-starvation test under Full, with two adds inside it (Task 6).
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

1. **An old save, or a census state from before this build.** It has none of the eleven stored inputs.
   - Expected: its next step starts medicine at the targets (no sudden lag) and stores all eleven, and until then the
     section shows "after the next count" with no per-frame "Failed to fetch variable".
   - Pinned by Task 5's `test_an_old_census_starts_at_its_targets` and Task 9's `test_every_read_sits_under_its_gate`.
2. **The first Full step after a seed or after Display only, and any state outside Full.**
   - Expected: no ×1.00 that wasn't measured. Outside Full the row is absent; on those first steps it reads "after
     the next count".
   - Pinned by Task 8's `test_the_on_top_gate_needs_a_measured_window`.
3. **A famine that starts inside the window, a state-level line that changed, or a clamped census term.**
   - Expected: the famine's share lands under severe starvation, not the whole state; a changed state-level line
     lands under the whole state; the hover names the clamp that bit the measured window.
   - Pinned by Task 6's `test_the_whole_state_part_is_the_window_without_the_pops_own_lines`,
     `test_a_famine_inside_the_window_is_severe_starvations` and `test_the_measured_window_keeps_its_clamp`.
4. **A conquered state, or a new health law.** The target jumps.
   - Expected: the drifted values move `r` of the gap per step and never overshoot. A seed doesn't lag. The lag in
     life expectancy is what Task 3 showed the owner.
   - Pinned by Task 4's `test_each_step_closes_its_share_of_the_gap`, Task 5's
     `test_the_step_drifts_medicine_before_its_rates` and Task 3's `test_the_lag_closes_at_the_rate`.
5. **A release build.**
   - Expected: the six carrier lines and the decree are commented out, and the decree isn't left as an empty shell
     with a texture and a cost.
   - Pinned by Task 7's `test_the_census_decree_is_commented_whole`.

---

## File structure

| File | Change | Responsibility |
|---|---|---|
| `scripts/analysis/demographics_params.py` | modify | `CAUSE_FACTORS`, `CAUSE_SHORT`, `TURMOIL_EXTERNAL_WEIGHT`, `DIFFUSION_*`, `MEDICINE_SNAP`, `MEDICAL_OUTREACH_DIFFUSION`, `DEATHS_ON_TOP_HIGH`; `DEMOG_TYPES` gains the diffusion type |
| `scripts/analysis/demographics_model.py` | modify | `Inputs.turmoil`, `Inputs.medicine`, `Ring.medicine`; `medicine_targets`, `diffusion`, `medicine_drift`, `cause_factors`; `medicine`, `cause_multipliers`, `seed`, `step`; `on_top_split` (Task 6) |
| `common/modifier_type_definitions/demographics_modifier_types.txt` | modify | `state_medical_diffusion_add` |
| `common/technology/technologies/te_demog_tech_injections.txt`, `modified.txt`, `era_6.txt`, `era_9.txt`, `era_10.txt` | modify | the six carriers |
| `scripts/generators/gen_demographics.py` | modify | factors, targets, the inputs store, the drift effects, the multipliers as products, constants; the severe-starvation sums in the walk |
| `common/script_values/te_demog_generated_values.txt`, `common/scripted_effects/te_demog_generated_effects.txt` | regenerated | — |
| `common/scripted_effects/te_demog_effects.txt` | modify | prepare/seed/step call the new effects; the walk calls the split; the header inventory |
| `common/scripted_effects/te_demog_fast_effects.txt` | modify | fast mode moves and removes the start's parts beside `te_dg_sr_d` |
| `common/scripted_effects/te_demog_rate_effects.txt` | modify | `te_demog_on_top_split`; `te_dg_rate_clamp_d`, its copy `te_dg_ed_clamp_d`; the start's own lines and severe part `te_dg_sp_d`, `te_dg_ss_d` |
| `common/script_values/te_debug_demog_values.txt`, `common/scripted_effects/te_debug_demog_effects.txt` | modify | guards on the mult reads; option l logs the diffusion rate; option n logs the split |
| `common/decrees/extra_decrees.txt` | modify | `decree_medical_outreach` |
| `common/script_values/te_demog_values.txt`, `common/scripted_triggers/te_demog_triggers.txt` | modify | `te_demog_medicine_gap`, `te_demog_medicine_behind` |
| `scripts/release/comment_out_census_inputs.py`, `test_release_census_inputs.py` | modify | a decree left with no effect goes whole |
| `common/script_values/te_demog_display_values.txt` | modify | the moving flags, the on-top figures, its split and code |
| `common/scripted_guis/te_demog_sguis.txt` | modify | `te_demog_state_causes_sgui`, `_full_sgui`, `_on_top_sgui` |
| `common/game_concepts/extra_concepts.txt` | modify | `concept_health_care_access` |
| `gui/te_demographics_widgets.gui` | modify | `te_state_demog_causes`; its place in `te_state_demog_content`; the country tab's TODO |
| `localization/english/te_miscellaneous_l_english.yml`, `te_modifiers_l_english.yml`, `te_decrees_l_english.yml`, `te_concepts_l_english.yml` | modify | the section, the type, the decree, the concept |
| `scripts/analysis/demographics_harness.py` | modify | `lag` (Task 3); `fidelity` and `history` run the model on the step's stored inputs (Task 10) |
| tests: `test_demographics_model.py`, `test_demographics_modifiers.py`, `test_gen_demographics.py`, `test_demographics_registry.py`, `test_demographics_harness.py`, `test_release_census_inputs.py` | modify | below |
| docs: `docs/systems/mod_systems.md`, `docs/guides/python_tools.md`, `docs/player_guide/08-states.md`, `06-politics.md` (+ PDF) | modify | Task 11 |

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

- [x] **Step 1: Write the failing tests**

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

- [x] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_model.TestCausesOfDeath`
Expected: ERROR, `module 'demographics_params' has no attribute 'CAUSE_FACTORS'`.

- [x] **Step 3: Add the parameters** (after `CROWDING_INFECTION_MAX`)

```python
# ---- Causes of Death (owner, 2026-10-11; docs/superpowers/archive/plans/2026-10-11-demographics-causes-of-death.md) ----
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

- [x] **Step 4: The model**

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

- [x] **Step 5: Run the model's tests**

Run: `.venv/bin/python -m unittest test_demographics_model test_demographics_harness`
Expected: OK. The harness's anchors (`medicine`, `fertility`, `sketch`) run on equilibria, where medicine is at its
targets, so none moves.

- [x] **Step 6: Commit**: "Demographics model: causes of death as factor products, medicine that drifts, turmoil".

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

- [x] **Step 1: Write the failing tests**

In `test_demographics_modifiers.py`, `TestCarriersInTheGameFiles`: add `P.DIFFUSION_TYPE: {"technology"}` to
`test_each_type_sits_where_its_design_puts_it`'s `allowed`. (The decree carries the type too, but `load_carriers`
reads only technologies, laws and institutions; Task 7 pins the decree.) Then:

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

- [x] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_modifiers test_demographics_registry.TestModifierTypes`
Expected: FAIL (no carriers; `te_demog_medical_diffusion` type not found).

- [x] **Step 3: The type** (end of `demographics_modifier_types.txt`)

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

- [x] **Step 4: The carriers**

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

- [x] **Step 5: The names, and the concept they use**

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

- [x] **Step 6: Run the tests, then commit**: "Demographics: the spread of medicine, on six technologies".

Run: `.venv/bin/python -m unittest test_demographics_modifiers test_demographics_registry.TestModifierTypes`, then
`python3 organize_loc.py` and `python3 organize_loc.py --check`.
Expected: OK. Commit what organize_loc moved with the rest.

---

### Task 3: The lag curve, for the owner (owner stop)

How far life expectancy lags its target while medicine spreads, at the proposed rates. The owner approves
`DIFFUSION_BASE`, the carriers' +0.05 and the decree's +0.2 from this table, not from the half-lives (the review: a
full treatment gap is about 10 years of e0 at SoL 15, and at 0.1 about 59% of it remains after 5 years).

**Files:**
- Modify: `scripts/analysis/demographics_harness.py` (a `lag` subcommand beside `medicine`)
- Test: `test_demographics_harness.py` (new `TestLag`)

**Interfaces:**
- Consumes: `M.medicine_targets`, `M.medicine_drift`, `M.diffusion` (Task 1); the carriers (Task 2); the harness's
  `life`, `scenario_inputs`, `MED_*` sets.
- Produces: `H.LAG_SCENARIOS`, `H.LAG_YEARS`, `H.lag_rows(carriers=None) -> [(label, rate, e0_before, e0_target,
  {year: years behind})]`, `demographics_harness.py lag`.

- [x] **Step 1: Write the failing tests**

```python
class TestLag(unittest.TestCase):
    """`lag`: years of life expectancy behind the target while medicine spreads (the Causes of Death plan, Task 3)."""

    @classmethod
    def setUpClass(cls):
        cls.rows = H.lag_rows()

    def test_every_scenario_starts_a_whole_gap_behind_and_closes(self):
        for label, rate, before, target, behind in self.rows:
            with self.subTest(label):
                self.assertAlmostEqual(behind[0], target - before, places=6)
                years = sorted(behind)
                self.assertTrue(all(behind[a] >= behind[b] - 1e-9 for a, b in zip(years, years[1:])), "never widens")
                self.assertGreaterEqual(behind[0], 0.0)

    def test_the_lag_closes_at_the_rate(self):
        # one step closes the rate's share of each input's gap; at a rate of 1 nothing is left after one step
        label, kw_before, kw_after = H.LAG_SCENARIOS[0]
        carriers = DM.load_carriers()
        after = H.scenario_inputs(carriers, **kw_after)
        fast = dataclasses.replace(after, mods={**after.mods, H.P.DIFFUSION_TYPE: 5.0})
        med = M.medicine_drift(M.medicine_targets(H.scenario_inputs(carriers, **kw_before)), fast)
        self.assertEqual(med, M.medicine_targets(fast))

    def test_the_cli_prints_every_scenario(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(H.main(["lag"]), 0)
        for label, _b, _a in H.LAG_SCENARIOS:
            self.assertIn(label, out.getvalue())
```

Add `import dataclasses` to `test_demographics_harness.py`'s imports.

- [x] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_harness.TestLag`
Expected: ERROR (`lag_rows` not defined).

- [x] **Step 3: The harness** (after `cmd_medicine`)

```python
# ---- lag: how far life expectancy trails its target while medicine spreads (the Causes of Death plan) -------------
# (label, before, after): a state's inputs before a change and after it, the communication techs of the era included
# (they set the spread's rate). At year 0 the change has just happened; each year is one census step.
COMMS_1870 = frozenset({"electric_telegraph"})
COMMS_1950 = COMMS_1870 | {"radio"}
COMMS_TODAY = COMMS_1950 | {"intergovernmental_organizations", "world_wide_web"}
LAG_SCENARIOS = [
    ("1840s: Charitable Health System, Ministry of Health 1 to 3",
     dict(sol=10, literacy=0.25, techs=MED_1836, laws={CHS}, institutions={HEALTH: 1}),
     dict(sol=10, literacy=0.25, techs=MED_1836, laws={CHS}, institutions={HEALTH: 3})),
    ("1870s: Modern Nursing arrives",
     dict(sol=13, literacy=0.5, techs=MED_1836 | {"pharmaceuticals"} | COMMS_1870, laws={CHS}, institutions={HEALTH: 3}),
     dict(sol=13, literacy=0.5, techs=MED_1900 | COMMS_1870, laws={CHS}, institutions={HEALTH: 3})),
    ("1900s: Public Health Insurance at 3, before antibiotics",
     dict(sol=16, literacy=0.75, techs=MED_1900 | COMMS_1870, laws={CHS}, institutions={HEALTH: 3}),
     dict(sol=16, literacy=0.75, techs=MED_1900 | COMMS_1870, laws={PHI}, institutions={HEALTH: 3})),
    ("1940s: antibiotics and vaccines arrive",
     dict(sol=22, literacy=0.9, techs=MED_1900 | COMMS_1950, laws={PHI}, institutions={HEALTH: 5}),
     dict(sol=22, literacy=0.9, techs=MED_1950 | COMMS_1950, laws={PHI}, institutions={HEALTH: 5})),
    ("1950s: a colony incorporated into that health system",
     dict(sol=12, literacy=0.4, techs=MED_1950 | COMMS_1950, laws={PHI}, institutions={}),
     dict(sol=12, literacy=0.4, techs=MED_1950 | COMMS_1950, laws={PHI}, institutions={HEALTH: 5})),
    ("Today: Telemedicine arrives",
     dict(sol=40, literacy=0.99, techs=MED_1990 | COMMS_TODAY, laws={PHI}, institutions={HEALTH: 8}),
     dict(sol=40, literacy=0.99, techs=MED_TODAY | COMMS_TODAY, laws={PHI}, institutions={HEALTH: 8})),
]
LAG_YEARS = (0, 1, 2, 3, 5, 10, 15, 20)


def lag_rows(carriers=None):
    """[(label, rate, e0 before, e0 at the target, {year: years of e0 behind the target})] for LAG_SCENARIOS: medicine
    starts at the before-inputs' targets and drifts at the after-inputs' rate (demographics_model.medicine_drift);
    SoL, literacy and everything else are the after-inputs' from year 0."""
    carriers = DM.load_carriers() if carriers is None else carriers
    rows = []
    for label, before, after in LAG_SCENARIOS:
        inp0, inp1 = scenario_inputs(carriers, **before), scenario_inputs(carriers, **after)
        target = life(inp1)["e0"]
        med, behind = M.medicine_targets(inp0), {}
        for year in range(max(LAG_YEARS) + 1):
            if year in LAG_YEARS:
                behind[year] = target - life(dataclasses.replace(inp1, medicine=med))["e0"]
            med = M.medicine_drift(med, inp1)
        rows.append((label, M.diffusion(inp1), life(inp0)["e0"], target, behind))
    return rows


def cmd_lag(_args):
    print("Years of life expectancy behind the target after a change, at the spread's rate (the share of the gap a "
          "census step closes):")
    print(f"{'':56s} rate  e0 before  target  " + "  ".join(f"{y:>4d}y" for y in LAG_YEARS))
    for label, rate, before, target, behind in lag_rows():
        print(f"{label:56s} {rate:4.2f}  {before:9.1f}  {target:6.1f}  "
              + "  ".join(f"{behind[y]:5.2f}" for y in LAG_YEARS))
    return 0
```

Register it: `sub.add_parser("lag").set_defaults(fn=cmd_lag)` beside `medicine`, and add the line to the module
docstring's command list.

- [x] **Step 4: Run the tests, then run `lag` and post its table on the PR**

Run: `.venv/bin/python -m unittest test_demographics_harness.TestLag`, then
`.venv/bin/python scripts/analysis/demographics_harness.py lag`.
Expected: OK; the table prints. Post it on the PR as a comment headed "Lag curve for the drift numbers".
(Done 2026-10-11: the table went to the owner through the controller, not as a comment on #905. The 1940s
scenario's "before" holds the Combustion Engine too; see the commit.)

- [x] **Step 5: Commit**: "Demographics harness: the lag curve of spreading medicine".

- [x] **Owner stop:** the owner approves or changes `DIFFUSION_BASE`, the carriers' +0.05 and the decree's +0.2 from
  the table. Apply any change in `demographics_params.py` (and on the carriers), rerun `lag`, and record the
  approved table in `mod_systems.md` (Task 11) before Task 4.

  **Approved, 2026-10-11:** the owner kept the proposed numbers: `DIFFUSION_BASE` 0.10, +0.05 on each of the six
  carriers, Medical Outreach +0.2. Nothing to apply. The approved table, `demographics_harness.py lag` at 98584051
  (Task 11 copies it into `mod_systems.md`):

  ```
  Years of life expectancy behind the target after a change, at the spread's rate (the share of the gap a census step closes):
                                                           rate  e0 before  target     0y     1y     2y     3y     5y    10y    15y    20y
  1840s: Charitable Health System, Ministry of Health 1 to 3 0.10       38.8    38.8   0.04   0.04   0.03   0.03   0.02   0.01   0.01   0.00
  1870s: Modern Nursing arrives                            0.20       42.4    43.2   0.83   0.67   0.53   0.43   0.27   0.09   0.00   0.00
  1900s: Public Health Insurance at 3, before antibiotics  0.20       46.0    46.7   0.75   0.60   0.48   0.39   0.25   0.08   0.03   0.00
  1940s: antibiotics and vaccines arrive                   0.25       49.9    61.7  11.84   9.11   6.97   5.30   3.04   0.74   0.18   0.00
  1950s: a colony incorporated into that health system     0.25       47.5    58.9  11.39   8.76   6.70   5.10   2.93   0.71   0.17   0.00
  Today: Telemedicine arrives                              0.40       71.0    74.4   3.37   2.16   1.35   0.83   0.31   0.00   0.00   0.00
  ```

  In words: a new medical technology is half felt (in e0) after about 6.6 years in 1850, 3 years in 1900, 2.6 years
  in 1950 and 1.6 years today. Medical Outreach halves a 1950s colony's wait (1.3 years to half). The 1840s row is
  nearly empty: before Modern Nursing there is almost no treatment to spread. The 1940s row's +11.8 years is
  Antibiotics and Modern Vaccines together; in a game they come an era apart.

---

### Task 4: The generator: factors, targets, the step's inputs, the drift

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

- [x] **Step 1: Write the failing generator tests** (`test_gen_demographics.py`, `TestGenerated`; replace
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

- [x] **Step 2: Write the failing script tests** (`test_demographics_registry.py`: replace `TestCauseMultipliersScript`)

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

Put `_stored` and `_mod_fixtures` above `_engine_for` (Task 5 changes `_engine_for` to use `_mod_fixtures`).

- [x] **Step 3: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_gen_demographics test_demographics_registry.TestCauseFactorsScript test_demographics_registry.TestMedicineDriftScript`
Expected: FAIL/ERROR (`te_demog_f_infection_medicine` not found).

- [x] **Step 4: The generator**

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
    o("# te_dg_med_gap, not te_dg_gap: te_demog_state_census, which calls the step, keeps its own te_dg_gap local")
    o("set_local_variable = { name = te_dg_med_gap value = { value = $TARGET$ subtract = var:$VAR$ } }")
    o("if = {")
    o("limit = {")
    o("local_var:te_dg_med_gap < te_demog_k_medicine_snap")
    o("local_var:te_dg_med_gap > te_demog_k_medicine_snap_neg")
    o("}")
    o("set_variable = { name = $VAR$ value = $TARGET$ }")
    o("}")
    o("}")
    o("")
```

- [x] **Step 5: Regenerate and run the tests**

Run: `.venv/bin/python scripts/generators/gen_demographics.py`, then
`.venv/bin/python -m unittest test_gen_demographics test_demographics_registry.TestCauseFactorsScript test_demographics_registry.TestMedicineDriftScript`
Expected: OK. `test_committed_outputs_are_current` passes on the regenerated files.

- [x] **Step 6: Commit** the generator, both generated files and the tests: "Demographics generator: causes of death as
  stored factors, and the drift of medicine".

---

### Task 5: The census stores its inputs and drifts its medicine (review stop)

**Files:**
- Modify: `common/scripted_effects/te_demog_effects.txt` (`te_demog_prepare`, `te_demog_seed`, `te_demog_step_begin`,
  the header inventory)
- Modify: `common/script_values/te_debug_demog_values.txt` (`te_debug_demog_mult_*`),
  `common/scripted_effects/te_debug_demog_effects.txt` (`te_debug_demog_mods_line`)
- Test: `test_demographics_registry.py` (`_engine_for`; new `TestCausesInTheStep`)

**Interfaces:**
- Consumes: `te_demog_cause_inputs_store`, `te_demog_medicine_at_target`, `te_demog_medicine_drift` (Task 4).
- Produces: every seed and step leaves `te_dg_acc`, `te_dg_trt_*`, `te_dg_in_*` on the state; `_engine_for(...,
  real_multipliers=False)`.

- [x] **Step 1: Make `_engine_for` give the step's reads** (`test_demographics_registry.py`)

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

`_mod_fixtures` is Task 4's, defined above `_engine_for`.

- [x] **Step 2: Write the failing tests**

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

    GATE_VARS = ("te_dg_acc", "te_dg_trt_inf", "te_dg_trt_mat", "te_dg_trt_chr", "te_dg_in_ext", "te_dg_in_work",
                 "te_dg_in_chr", "te_dg_in_turm", "te_dg_in_crowd")

    def test_an_old_census_starts_at_its_targets(self):
        """Review Focus 1: a census state from before this build has none of the nine variables
        te_demog_state_causes_sgui asks for. Its first step starts medicine at the targets and leaves all nine."""
        eng = _engine_for(self.INP1, 1837, 250000.0, real_multipliers=True)
        for name in self.GATE_VARS:
            self.assertNotIn(name, eng.vars)
        eng.call("te_demog_medicine_drift")
        eng.call("te_demog_prepare")
        for name in self.GATE_VARS:
            self.assertIn(name, eng.vars, name)
        targets = demographics_model.medicine_targets(self.INP1)
        self.assertAlmostEqual(eng.vars["te_dg_acc"], targets["access"], places=9)
        self.assertAlmostEqual(eng.vars["te_dg_trt_inf"], targets["infection"], places=9)

    def test_the_entry_points_run_in_order(self):
        effects = _raw_blocks([EFFECTS])
        begin = [k for k, _, _ in _parse_script(effects["te_demog_step_begin"])]
        # relative order only: #906 puts te_demog_practices_step before te_demog_prepare as well
        self.assertLess(begin.index("te_demog_medicine_drift"), begin.index("te_demog_prepare"))
        seed = [k for k, _, _ in _parse_script(effects["te_demog_seed"])]
        self.assertLess(seed.index("te_demog_medicine_at_target"), seed.index("te_demog_prepare"))
        prepare = [k for k, _, _ in _parse_script(effects["te_demog_prepare"])]
        first_mult = next(i for i, (k, _, v) in enumerate(_parse_script(effects["te_demog_prepare"]))
                          if k == "set_local_variable" and _find(v, "name") == "te_dg_m_inf")
        self.assertLess(prepare.index("te_demog_cause_inputs_store"), first_mult)
```

- [x] **Step 3: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestCausesInTheStep`
Expected: ERROR (`read of missing variable var:te_dg_acc` in the seed).

- [x] **Step 4: Wire the entry points** (`te_demog_effects.txt`)
  - `te_demog_prepare`: `te_demog_cause_inputs_store = yes` just before
    `set_local_variable = { name = te_dg_m_inf value = te_demog_mult_infection }`, with the comment
    `# the inputs the factors read, stored so the Causes of Death section matches this step until the next (generated)`.
  - `te_demog_seed`: `te_demog_medicine_at_target = yes` just before `te_demog_prepare = yes`
    (`# a seed starts medicine at its targets (the Causes of Death plan)`).
  - `te_demog_step_begin`: `te_demog_medicine_drift = yes` before `te_demog_prepare = yes`
    (`# medicine moves its share of the gap, then the year's rates use it`). If #906 has merged, its
    `te_demog_practices_step` is there too; either order with it works, as long as both precede prepare. Update the
    comment.
  - The header inventory: after the cause multipliers' lines, add:
    ```
    #   te_dg_acc, te_dg_trt_inf, te_dg_trt_mat, te_dg_trt_chr  the drifted health-care access and treatments
    #                       (te_demog_medicine_drift; the Causes of Death plan)
    #   te_dg_in_ext, te_dg_in_work, te_dg_in_chr, te_dg_in_turm, te_dg_in_crowd  the step's other inputs the
    #                       factors read (te_demog_cause_inputs_store)
    ```

- [x] **Step 5: The console's reads**
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

- [x] **Step 6: Run the registry, the model and the harness**

Run: `.venv/bin/python -m unittest test_demographics_registry test_demographics_model test_demographics_harness`
Expected: OK. The cohort tests keep their multiplier fixtures; the drift runs at the targets there.

- [x] **Step 7: Commit**: "Demographics: the census stores its causes' inputs and drifts its medicine".

- [x] **Review stop:** a fresh reviewer reads Tasks 4–5 (the generated factors and drift, the wiring, the old-save
  path) against this plan before Task 6.
  **Passed, 2026-10-11:** APPROVE with four minors, all applied (e4d1ac66).

---

### Task 6: Split the deaths added on top at both ends of the window (review stop)

**Re-planned 2026-10-11** against #907 (b8c993b4, the window is the mean of the engine's rate at its two ends) and #913
(209401a6, severe starvation × the starvation value in 0.05 food-security steps). The design is the owner's, unchanged:
- "Deaths Added on Top ×(1 + dz)" under Full, red from ×1.25;
- split into effects on the whole state and effects on some of its people, the latter as "Severe starvation ×a
  (X% of its people)" and "Other effects on some of its people ×b";
- the hover describes the window dz measured, through the clamp copy `te_dg_ed_clamp_d`;
- the row waits until a measured window exists.

The identity and its departures are in "What the code says" §2.

**Files:**
- Modify: `scripts/generators/gen_demographics.py` (`absorbed_walk`); regenerate.
- Modify: `common/scripted_effects/te_demog_rate_effects.txt`:
  - new `te_demog_on_top_split`, `te_demog_on_top_split_clear` and `te_demog_on_top_clamp_copy`;
  - `te_demog_rates_refresh` (the start's parts beside `te_dg_sr_d`; `te_dg_rate_clamp_d`; the no-start branch);
  - `te_demog_rate_clamp` (the side), `te_demog_on_top_scales` (the copy), `te_demog_rates_clear`, the header.
- Modify: `common/scripted_effects/te_demog_effects.txt`: `te_demog_walks` (the split after
  `te_demog_window_events`), `te_demog_seed` (the start's parts go with `te_dg_sr_*`), the header.
- Modify: `common/scripted_effects/te_demog_fast_effects.txt`: `te_demog_fast_refresh_rates` moves `te_dg_sp_d`;
  `te_demog_fast_clear_rates` removes the start's parts.
- Modify: `common/script_values/te_demog_display_values.txt`: `te_demog_deaths_on_top`, `_whole_state`, `_severe`,
  `_other` (Task 8 adds `_code` and the text).
- Modify: `common/scripted_effects/te_debug_demog_effects.txt`: option n's `TE_DEMOG_RATES` line.
- Modify: `scripts/analysis/demographics_model.py` (`on_top_split`).
- Test:
  - `test_demographics_model.py` (`TestOnTopSplit`) and `test_gen_demographics.py`;
  - `test_demographics_registry.py`: `TestAbsorbedScript` (the severe sum), new `TestOnTopSplitScript`, new
    `TestOnTopClampSide`. The helpers that run the refresh on hand-set walk locals gain `te_dg_w_sevd` and
    `te_dg_w_sev`.

**Interfaces:**
- Consumes:
  - the walk's locals `te_dg_w_ed`, `_ed0`, `_edr`, `_ed0m`, `te_dg_w_pop`, `te_dg_p_ed`, `te_dg_p_md` and
    `te_dg_w_rep`;
  - the refresh's locals `te_dg_rate_prev_d` and `te_dg_rate_lines_d`, and its `te_dg_md`;
  - fast mode's `te_dg_fast_fd` and local `te_dg_fast_prev_d`;
  - `te_dg_sr_b` / `_d`, `te_dg_ed`, `te_demog_k_window_start_weight`, `te_demog_step_months`.
- Produces:
  - walk locals `te_dg_w_sev` (people in severe starvation) and `te_dg_w_sevd` (their deaths' severe term: the bare
    curve × 1.0 × the starvation value's step, pops the engine doesn't floor). They start at 0 for every walk and
    are summed under Full only.
  - state variables:
    - `te_dg_sp_d` and `te_dg_ss_d`, the start's own lines and severe part per head, beside `te_dg_sr_d`, removed
      with it;
    - `te_dg_ed_state`, `te_dg_ed_sev` and `te_dg_sev_share` (Full only);
    - `te_dg_rate_clamp_d` (0 none, 1 the floor, 2 the cap) and its copy for the measured window,
      `te_dg_ed_clamp_d`.
  - `M.on_top_split(end, start=None) -> (events, whole-state part, severe part)`. `end` and `start` are each
    `(rate, pops' own lines, severe)` at that end, in any one unit.
  - display values `te_demog_deaths_on_top`, `te_demog_deaths_whole_state`, `te_demog_deaths_severe` and
    `te_demog_deaths_other`.

**The truth the tests check against:** an engine built from pops, as `TestWindowEvents` builds one.
- Each pop has bare curves, absorbed terms, its own terms on top and, of those, a severe starvation term and its
  people.
- At each end, under that end's read:
  - the engine's deaths are `Σ bare × max(0, 1 + read + absorbed + own)`;
  - the whole state's part is `Σ bare × (1 + read + absorbed)`: the engine without any pop's own lines, unfloored;
  - severe starvation's part is `Σ bare × severe` over the pops the engine doesn't floor.
- The window is the mean of the two ends × months / 100,000. The start runs under the read the refresh left in
  force: the new M, fast mode's new term, no moved lines' pairs.
- The discriminating case is a pop floored at the start while M changes at the refresh. Using `w_ed0` where the start
  needs `w_ed0m` passes every steady case and fails this one.

- [x] **Step 1: Write the failing tests**
  - `test_demographics_model.py`, `TestOnTopSplit`, on `M.on_top_split`:
    - with no start, the snapshot: `events = end[0]` and `state = end[0] − end[1]`;
    - with a start, each part weighted as `window_events` weighs the rate (`P.WINDOW_START_WEIGHT`);
    - a famine only at the end books `(1 − w)` of its severe part;
    - the whole state's part is never below 0.
  - `test_gen_demographics.py`:
    - `te_demog_absorbed_walk_init` starts `te_dg_w_sev` and `te_dg_w_sevd` at 0, outside the Full guard;
    - `te_demog_absorbed_walk_pop` sums them inside it: one `is_in_severe_starvation = yes` test, the people
      unconditionally, the deaths inside `local_var:te_dg_p_md > 0`;
    - the deaths' term is the severe ladder that `te_demog_pop_death_mult` holds, the same text;
    - no new per-pop script value.
  - `test_demographics_registry.py`, `TestAbsorbedScript.test_the_walk_sums_severe_starvation`, per pop through the
    generated effect:
    - severe pops at food security 0.199, 0.15, 0.12, 0.07 and 0.0: people added, deaths `p_ed × 1.0 ×` the step's
      starvation value (equal to `te_demog_pop_death_mult`'s severe part at each);
    - a floored severe pop (`p_md = 0`): people only;
    - a mild pop: nothing;
    - outside Full: nothing.
  - `test_demographics_registry.py`, new `TestOnTopSplitScript`:
    - **The helper.** `window(start_pops, end_pops, ...)` mirrors `TestWindowEvents.window`: the refresh at the start
      under the old read, the terms it left in force, the end's walk, then `te_demog_window_events` and
      `te_demog_on_top_split`. It also runs `te_demog_on_top_scales` (its rate locals at 1) for dz, the target and
      the clamp copy. Pops are `_SPop(bare_b, bare_d, abs_b, abs_d, top_b, top_d, sev_d, people)`, with `sev_d` part
      of `top_d`.
    - **Each case checks** `te_dg_ed_state` and `te_dg_ed_sev` against the truth above, `te_dg_sev_share` against the
      end's people, and `whole × severe × other == 1 + dz` through the display values.
      - `test_a_famine_inside_the_window_is_severe_starvations`: mild at the start (netted by M), severe at the end.
        Half the end's severe part is severe starvation's; mild's netted line stays with the whole state.
      - `test_a_famine_ending_in_the_window`.
      - `test_a_state_level_change_stays_with_the_whole_state`: devastation 0 → +0.3 gives severe ×1.00 and other
        ×1.00.
      - `test_other_lines_on_some_people`: a workplace line on one pop gives other above 1 and severe ×1.00.
      - `test_the_whole_state_part_is_the_window_without_the_pops_own_lines`: the same state with every pop's own
        lines zeroed at both ends books `te_dg_ed` equal to the first's `te_dg_ed_state`.
      - `test_a_floored_pop_under_a_changing_m`: a pop floored at the start while M moves from −0.25 to about +0.4
        at the refresh.
      - `test_fast_mode_moves_the_start_part`: K = 4, the window of 3 months.
      - `test_no_start_rate_splits_the_snapshot`: the first step after a seed.
    - **Exceptions.**
      - `test_a_start_from_before_this_build_waits`: `te_dg_sr_*` without `te_dg_sp_d` / `te_dg_ss_d`. The three
        variables go.
      - `test_outside_full_the_split_goes`.
      - `test_where_dz_is_clamped_the_product_is_not`: ED over five times the target. The product exceeds 1 + dz
        (+4), which the hover says through the clamp text (Task 8).
    - **Removal sites.** `test_the_start_parts_go_with_the_start_rate`: the start's parts go wherever `te_dg_sr_d`
      goes. That is `te_demog_rates_clear`, the refresh's no-start branch (a seed's refresh), `te_demog_seed` and
      `te_demog_fast_clear_rates`, each driven.
  - `test_demographics_registry.py`, new `TestOnTopClampSide`:
    - `test_the_deaths_clamp_records_its_side`: the floor gives 1, the cap 2, neither 0, and births clamped alone
      0. The side resets at each `te_demog_rate_clamp`.
    - `test_the_measured_window_keeps_its_clamp`: `te_demog_on_top_scales` copies the flag before the refresh;
      with no flag the copy goes.
    - `test_rates_clear_takes_the_clamp_and_the_start_parts`.

- [x] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_model.TestOnTopSplit test_gen_demographics test_demographics_registry.TestAbsorbedScript test_demographics_registry.TestOnTopSplitScript test_demographics_registry.TestOnTopClampSide`
Expected: FAIL/ERROR (`on_top_split`, `te_demog_on_top_split`, `te_dg_w_sevd` missing).

- [x] **Step 3: The model** (after `window_events`)

```python
def on_top_split(end, start=None):
    """(events, whole-state part, severe starvation's part) over a step's window (the Causes of Death plan; the script's
    te_demog_on_top_split). end, start: (the engine's rate, the pops' own lines in it, severe starvation's part of
    those) at that end of the window, in one unit; start None where the window took the snapshot. Each part is
    weighted as window_events weighs the rate; the whole state's part is the events less the pops' own lines, at
    least 0."""
    events = window_events(end[0], None if start is None else start[0])
    if start is None:
        own, severe = end[1], end[2]
    else:
        w = P.WINDOW_START_WEIGHT
        own, severe = w * start[1] + (1 - w) * end[1], w * start[2] + (1 - w) * end[2]
    return events, max(0.0, events - own), severe
```

- [x] **Step 4: The generator** (`absorbed_walk`)
  - init, before the Full guard: `set_local_variable = { name = te_dg_w_sev value = 0 }` and
    `set_local_variable = { name = te_dg_w_sevd value = 0 }`.
  - pop, inside `local_var:te_dg_w_rep > 0`, after the `te_dg_w_ed0m` test:
    ```python
    o("# severe starvation's people, and its part of the pop's deaths where the engine doesn't floor them (the Causes")
    o("# of Death section's split, te_demog_on_top_split): the severe ladder te_demog_pop_death_mult holds")
    o("if = {")
    o("limit = { is_in_severe_starvation = yes }")
    o("change_local_variable = { name = te_dg_w_sev add = total_size }")
    o("if = {")
    o("limit = { local_var:te_dg_p_md > 0 }")
    o("change_local_variable = {")
    o("name = te_dg_w_sevd")
    o("add = {")
    o("value = local_var:te_dg_p_ed")
    o("multiply = {")
    o("value = 0")
    _starvation_ladder(o, severe["state_mortality_mult"], _starvation_buckets(severe=True))
    o("}")
    o("}")
    o("}")
    o("}")
    o("}")
    ```
    `absorbed_walk` reads `severe = static_modifier(root, "severe_starvation_penalty")`, as `engine_rate_terms`
    does. Amend its comments.
  - Regenerate.

- [x] **Step 5: The split, the start's parts and the clamp side** (`te_demog_rate_effects.txt`)

```
# THIS = a state, the walk's tail, straight after te_demog_window_events: the Causes of Death section's split of the
# window's deaths (docs/superpowers/archive/plans/2026-10-11-demographics-causes-of-death.md, Task 6). Under Full:
#   te_dg_ed_state  te_dg_ed less the pops' own lines over the window, at least 0: the state-level lines and the moved
#                   lines' on-top family, the absorbed lines M nets, and the census's own lag (M a window old, the
#                   model's rate drifting)
#   te_dg_ed_sev    severe starvation's part of the pops' own lines over the window
#   te_dg_sev_share the share of the state's people in severe starvation at the walk
# Each end as te_demog_window_events weighs it. Today's from the walk: the engine's rate less what it would be without
# any pop's own lines, w_ed - w_edr - (1 + read) x w_ed0 (a floored pop's own lines took its deaths to 0), and
# te_dg_w_sevd. The start's from the refresh that stored te_dg_sr_d: te_dg_sp_d and te_dg_ss_d, per head. A start
# rate without them (a save from before this build) leaves no split, so the row waits for the next count. Outside
# Full the three go.
te_demog_on_top_split = {
	if = {
		limit = { te_demog_effects_run = yes }
		set_local_variable = {
			name = te_dg_split_own
			value = {
				value = modifier:state_mortality_mult
				add = 1
				multiply = local_var:te_dg_w_ed0
				add = local_var:te_dg_w_edr
				multiply = -1
				add = local_var:te_dg_w_ed
			}
		}
		set_local_variable = { name = te_dg_split_sev value = local_var:te_dg_w_sevd }
		set_local_variable = { name = te_dg_split_ok value = 1 }
		# te_demog_window_events' limit: there the window took the start's rate
		if = {
			limit = {
				has_variable = te_dg_sr_b
				has_variable = te_dg_sr_d
			}
			if = {
				limit = {
					has_variable = te_dg_sp_d
					has_variable = te_dg_ss_d
				}
				set_local_variable = {
					name = te_dg_split_own
					value = {
						value = var:te_dg_sp_d
						multiply = state_population
						subtract = local_var:te_dg_split_own
						multiply = te_demog_k_window_start_weight
						add = local_var:te_dg_split_own
					}
				}
				set_local_variable = {
					name = te_dg_split_sev
					value = {
						value = var:te_dg_ss_d
						multiply = state_population
						subtract = local_var:te_dg_split_sev
						multiply = te_demog_k_window_start_weight
						add = local_var:te_dg_split_sev
					}
				}
			}
			else = {
				set_local_variable = { name = te_dg_split_ok value = 0 }
			}
		}
		if = {
			limit = { local_var:te_dg_split_ok > 0 }
			set_variable = {
				name = te_dg_ed_state
				value = {
					value = local_var:te_dg_split_own
					multiply = te_demog_step_months
					divide = 100000
					multiply = -1
					add = var:te_dg_ed
					min = 0
				}
			}
			set_variable = {
				name = te_dg_ed_sev
				value = {
					value = local_var:te_dg_split_sev
					multiply = te_demog_step_months
					divide = 100000
					min = 0
				}
			}
			set_variable = {
				name = te_dg_sev_share
				value = {
					value = local_var:te_dg_w_sev
					divide = { value = local_var:te_dg_w_pop min = 1 }
					max = 1
				}
			}
		}
		else = {
			te_demog_on_top_split_clear = yes
		}
	}
	else = {
		te_demog_on_top_split_clear = yes
	}
}
```

`te_demog_on_top_split_clear` removes the three variables, guarding each with `has_variable`.
`te_demog_on_top_clamp_copy` is the original plan's text: under Full with `te_dg_rate_clamp_d` it sets
`te_dg_ed_clamp_d` to it, and otherwise removes the copy.

Then:
- `te_demog_walks`: `te_demog_on_top_split = yes` straight after `te_demog_window_events = yes`, with the comment
  `# the Causes of Death section's split of the window's deaths (Full only)`. Add the three variables to the
  header's inventory ("Full only").
- `te_demog_on_top_scales`: `te_demog_on_top_clamp_copy = yes` as its first line.
- `te_demog_rate_clamp`: first line `set_local_variable = { name = te_dg_rate_side value = 0 }`; then 1 in the floor
  branch and 2 in the cap branch. Update its comment.
- `te_demog_rates_refresh`, deaths half, after its `te_demog_rate_clamp = yes`:
  `set_variable = { name = te_dg_rate_clamp_d value = local_var:te_dg_rate_side }`, with the comment `# which clamp bit
  deaths, for the next window: 0 none, 1 the floor, 2 the cap (te_demog_on_top_clamp_copy)`. After `te_dg_sr_d`:
  ```
  			# the start's own lines and severe starvation's part, per head (te_demog_on_top_split): today's, less the
  			# change in the census's term on the pops the engine floors at 0, which it doesn't reach (te_dg_sr_d moves
  			# by it on the others)
  			set_variable = {
  				name = te_dg_sp_d
  				value = {
  					value = var:te_dg_md
  					subtract = local_var:te_dg_rate_prev_d
  					subtract = local_var:te_dg_rate_lines_d
  					multiply = { value = local_var:te_dg_w_ed0 subtract = local_var:te_dg_w_ed0m }
  					multiply = -1
  					add = local_var:te_dg_w_ed
  					subtract = local_var:te_dg_w_edr
  					subtract = { value = modifier:state_mortality_mult add = 1 multiply = local_var:te_dg_w_ed0 }
  					divide = { value = state_population min = 1 }
  				}
  			}
  			set_variable = { name = te_dg_ss_d value = { value = local_var:te_dg_w_sevd divide = { value = state_population min = 1 } } }
  ```
  The no-start branch removes `te_dg_sp_d` and `te_dg_ss_d` beside `te_dg_sr_*`.
- `te_demog_rates_clear`: remove `te_dg_sp_d`, `te_dg_ss_d`, `te_dg_rate_clamp_d` and `te_dg_ed_clamp_d`.
- `te_demog_seed` and `te_demog_fast_clear_rates`: remove `te_dg_sp_d` and `te_dg_ss_d` where they remove
  `te_dg_sr_d`.
- `te_demog_fast_refresh_rates`, after it moves `te_dg_sr_d`: under `has_variable = te_dg_sp_d`, a `set_variable`
  with an inline value (the Global Constraints' rule) of `var:te_dg_sp_d − (te_dg_fast_fd − te_dg_fast_prev_d) ×
  (te_dg_w_ed0 − te_dg_w_ed0m) / people`.
- The headers of `te_demog_rate_effects.txt` and `te_demog_effects.txt`: the new variables.

- [x] **Step 6: Option n, and the display values**
  - **Option n** (`TE_DEMOG_RATES`): copy `te_dg_ed_state`, `te_dg_ed_sev`, `te_dg_sev_share`, `te_dg_ed_clamp_d`,
    `te_dg_sp_d` and `te_dg_ss_d` into `te_dg_dbg_eds`, `_edsev`, `_sev`, `_cld`, `_spd` and `_ssd` through
    `te_debug_demog_rate_copy`. Log them before `date=` as ` ed_state= ed_sev= sev= clamp_d= sp_d= ss_d=` and remove
    them after the line.
  - **`te_demog_display_values.txt`:** `te_demog_deaths_on_top` (1 + `te_dg_dz`), `te_demog_deaths_whole_state`,
    `te_demog_deaths_severe` and `te_demog_deaths_other`, as Task 8 Step 3 writes them. Their product is
    `te_dg_ed ÷ te_dg_ed_target`.

- [x] **Step 7: Run the tests**

Run: `.venv/bin/python scripts/generators/gen_demographics.py --check && .venv/bin/python -m unittest test_demographics_model test_gen_demographics test_demographics_registry`
Expected: OK, #907's and #913's own tests included.

- [x] **Step 8: Commit**: "Demographics: split the deaths added on top at both ends of the window".

- [x] **Review stop:** a fresh reviewer reads the re-plan and Task 6 against #907 and #913 before Tasks 8–9.
  **Passed, 2026-10-11:** APPROVE WITH FIXES, the five minors applied (f37e73b0).

---

### Task 7: Medical Outreach, and releases without it

**Files:**
- Modify: `common/decrees/extra_decrees.txt`
- Modify: `common/script_values/te_demog_values.txt` (`te_demog_medicine_gap`),
  `common/scripted_triggers/te_demog_triggers.txt` (`te_demog_medicine_behind`)
- Modify: `localization/english/te_decrees_l_english.yml`
- Modify: `scripts/release/comment_out_census_inputs.py`
- Test: `test_demographics_registry.py` (new `TestMedicalOutreach`), `test_release_census_inputs.py`

**Interfaces:**
- Consumes: `te_demog_access_target`, `te_demog_treatment_target_<cause>`, `te_demog_k_medicine_snap` (Task 4);
  `te_dg_acc`, `te_dg_trt_*` (Task 5); `P.MEDICAL_OUTREACH_DIFFUSION` (Task 1).
- Produces: `decree_medical_outreach`; `te_demog_medicine_behind` (state trigger); the release script's rule 3b.

- [x] **Step 1: Write the failing tests**

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

    def test_the_ai_weighs_it_by_the_gap(self):
        # the shared-mechanics rule: the AI issues it where medicine is behind, and never once the state caught up.
        # has_decree is read as "not issued" (the interpreter doesn't know decrees)
        body = _block(_text(self.DECREES), "decree_medical_outreach")
        weight = _find(_parse_script(body.replace("has_decree = decree_medical_outreach", "always = no")), "ai_weight")
        fixtures = {f"modifier:{t}": 0.0 for t in P.DEMOG_TYPES}
        fixtures[f"modifier:{P.ACCESS_TYPE}"] = 0.6          # access heading for 1.0
        for acc, want in ((1.0, 0.0), (0.95, 0.0), (0.85, 100.0), (0.6, 200.0)):
            eng = _Engine(fixtures)
            eng.vars.update(te_dg_acc=acc, te_dg_trt_inf=0.0, te_dg_trt_mat=0.0, te_dg_trt_chr=0.0)
            with self.subTest(acc=acc):
                self.assertEqual(eng._ops(weight, 0.0), want)
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
technologies and the decree). Replace `test_what_else_it_comments_is_dead_with_the_census` so the decree file is
allowed only inside `decree_medical_outreach`'s entry, not as a whole:

```python
    def _entry_lines(self, text, name):
        """The line indexes of the top-level `name = { ... }` entry, by brace depth."""
        lines, out, depth = text.split("\n"), set(), 0
        for i, line in enumerate(lines):
            if not out and re.match(rf"{re.escape(name)} = \{{", line):
                out.add(i)
                depth = _code(line).count("{") - _code(line).count("}")
                continue
            if out and depth > 0:
                out.add(i)
                depth += _code(line).count("{") - _code(line).count("}")
        return out

    def test_what_else_it_comments_is_dead_with_the_census(self):
        # outside the census's lines: the entries they leave empty, Family Limitation's application, Medical Outreach
        # (its only effect was a census type), the gates' old bodies and the rule
        census = re.compile(rf"^\s*({'|'.join(self.types)})\s*=")
        whole_entries = {"common/laws/te_demog_law_injections.txt",
                         "common/technology/technologies/te_demog_tech_injections.txt"}
        decrees = "common/decrees/extra_decrees.txt"
        outreach = self._entry_lines(self.before[self.root / decrees].decode("utf-8-sig"), "decree_medical_outreach")
        self.assertTrue(outreach, "decree_medical_outreach found")
        for path in self.changed:
            rel = path.relative_to(self.root).as_posix()
            for n, line in enumerate(path.read_text(encoding="utf-8-sig").split("\n")):
                if not line.startswith(TAG):
                    continue
                body = line[len(TAG):]
                with self.subTest(rel=rel, line=body.strip()):
                    if census.match(body) or rel in whole_entries:
                        continue
                    if rel == decrees:
                        self.assertIn(n, outreach, "only Medical Outreach goes whole")
                    elif rel == "common/history/extra_history.txt":
                        self.assertIn("add_modifier = { name = te_demog_family_limitation }", body)
                    else:
                        self.assertIn(rel, {"common/scripted_triggers/te_demog_triggers.txt",
                                            "common/game_rules/extra_game_rules.txt"})
```

A commented line keeps its index (`test_it_only_comments_lines_out`), so `n` matches the original file's.

- [x] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestMedicalOutreach test_release_census_inputs`
Expected: FAIL/ERROR.

- [x] **Step 3: The gap and the trigger**

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

- [x] **Step 4: The decree** (`extra_decrees.txt`, after `decree_natalism_initiative`)

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

	# The AI uses it where the player would (the shared-mechanics rule): by how far the state's medicine is behind,
	# with lower thresholds once issued, and not at all once it has caught up (vanilla Road Maintenance's pattern)
	ai_weight = {
		value = 0
		if = {
			limit = {
				OR = {
					te_demog_medicine_gap > 0.1
					AND = {
						has_decree = decree_medical_outreach
						te_demog_medicine_gap > 0.05
					}
				}
			}
			add = 100
		}
		if = {
			limit = {
				OR = {
					te_demog_medicine_gap > 0.3
					AND = {
						has_decree = decree_medical_outreach
						te_demog_medicine_gap > 0.2
					}
				}
			}
			add = 100
		}
		if = {
			limit = { te_demog_medicine_behind = no }
			multiply = 0
		}
	}
}
```

`te_decrees_l_english.yml`:

```
 decree_medical_outreach:0 "Medical Outreach"
 decree_medical_outreach_desc:0 "Doctors and nurses go out to train this state's practitioners and staff its clinics, so the newest treatments and the reach of our health system arrive here years sooner."
```

- [x] **Step 5: The release script** (`comment_out_census_inputs.py`)

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

- [x] **Step 6: Run the tests, then commit**

Run: `.venv/bin/python -m unittest test_demographics_registry test_release_census_inputs test_demographics_modifiers`
Expected: OK. Also run `.venv/bin/python scripts/release/comment_out_census_inputs.py --check | tail -1`: 46 or more
census lines, and the decree's lines.

Commit: "Demographics: the Medical Outreach decree (Full only), and releases without it".

---

### Task 8: What the section reads: display values, gates, names

**Files:**
- Modify: `common/script_values/te_demog_display_values.txt`
- Modify: `common/scripted_guis/te_demog_sguis.txt`
- Modify: `localization/english/te_miscellaneous_l_english.yml` (the section's keys; `te_demog_st_e0_causes`;
  `te_demog_how_mortality`)
- Test: `test_demographics_registry.py` (new `TestCausesDisplay`)

**Interfaces:**
- Consumes: the variables of Tasks 4–6 (`te_dg_ed_state`, `te_dg_ed_sev`, `te_dg_sev_share`, `te_dg_ed_clamp_d`
  among them) and `te_dg_dz`, `te_dg_ed`, `te_dg_ed_target`, `te_dg_cdr`, `te_dg_cdr_model`;
  `concept_health_care_access` (Task 2); `te_demog_deaths_on_top`, `_whole_state`, `_severe`, `_other` (Task 6).
- Produces:
  - display values: `te_demog_access_from_law`, `te_demog_access_gap`, `te_demog_access_moving`,
    `te_demog_medicine_gap_<cause>`, `te_demog_medicine_moving_<cause>`, `te_demog_deaths_on_top_code`;
  - scripted GUIs: `te_demog_state_causes_sgui`, `te_demog_state_full_sgui`, `te_demog_state_on_top_sgui`;
  - loc keys `te_demog_sec_causes`, `te_demog_st_causes_pending`, and `te_demog_st_<row>`, `_value`, `_tt` for rows
    `acc`, `inf`, `ext`, `chr`, `work`, `mat`, `ontop`, with their parts.

- [x] **Step 1: Write the failing tests**

```python
SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_sguis.txt"


class TestCausesDisplay(unittest.TestCase):
    """The Causes of Death section's reads (the plan's Task 8)."""

    def _shown(self, sgui, eng):
        body = _parse_script(_block(_text(SGUIS), sgui))
        return eng.holds(_find(body, "is_shown"))

    def test_the_on_top_gate_needs_a_measured_window(self):
        # Review Focus 2: the first Full step after a seed writes dz 0 against no target; the first after Display only
        # has a target but its window ran with no M, so no refresh's clamp flag was there to copy (te_dg_ed_clamp_d)
        base = dict(te_dg_ed_target=1000.0, te_dg_ed_state=900.0, te_dg_ed_sev=0.0, te_dg_sev_share=0.0, te_dg_dz=0.0,
                    te_dg_ed_clamp_d=0.0)
        for full, change, shown in ((True, {}, True), (True, {"te_dg_ed_target": 0.0}, False),
                                    (True, {"te_dg_ed_clamp_d": None}, False), (False, {}, False)):
            eng = _Engine({}, triggers={"te_demog_effects_run": full})
            eng.vars.update(base)
            for k, v in change.items():
                if v is None:
                    del eng.vars[k]
                else:
                    eng.vars[k] = v
            with self.subTest(full=full, change=change):
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

- [x] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestCausesDisplay`
Expected: ERROR.

- [x] **Step 3: The display values** (`te_demog_display_values.txt`, a new section at the end)

```
# ============================================================================
# Causes of Death (the state subtab; docs/superpowers/archive/plans/2026-10-11-demographics-causes-of-death.md). State scope,
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

Task 6 wrote the deaths added on top and its split (below, for reference). Add the code beside them:

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
# Its split over the same window (te_demog_on_top_split, Full only): the whole state's part (the state-level lines, the
# moved lines' on-top family, the census's own lag since its last count), severe starvation's, and the other lines on
# some of its people. Their product is te_dg_ed / te_dg_ed_target, which is te_demog_deaths_on_top except: where dz hit
# either end of its range; where a division's min = 1 (a person) bites, on a tiny state; where an end's read was below
# -1 (state-level lines falling inside the window after M was fitted, or the read without M already below the floor),
# which moves deaths into the other effects and can floor te_dg_ed_state at 0; and after a second walk in a year
# without a step, which rewrites te_dg_ed and the split but not dz or the target until the next step.
te_demog_deaths_whole_state = {
	value = var:te_dg_ed_state
	divide = { value = var:te_dg_ed_target min = 1 }
}
te_demog_deaths_severe = {
	value = var:te_dg_ed_state
	add = var:te_dg_ed_sev
	divide = { value = var:te_dg_ed_state min = 1 }
}
te_demog_deaths_other = {
	value = var:te_dg_ed
	divide = { value = var:te_dg_ed_state add = var:te_dg_ed_sev min = 1 }
}
```

- [x] **Step 4: The gates** (`te_demog_sguis.txt`, after `te_demog_state_stepped_sgui`; update the header's count)

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
		has_variable = te_dg_ed_sev
		has_variable = te_dg_sev_share
		has_variable = te_dg_ed_clamp_d
	}
	ai_is_valid = { always = no }
	is_valid = { always = no }
	effect = { }
}
```

- [x] **Step 5: The section's loc** (`te_miscellaneous_l_english.yml`, beside the other `te_demog_st_*`)

The rows read only the state (`State.MakeScope`), never the player (`test_the_state_subtab_gate_needs_no_player`).

Implemented with one change (Task 9, 2026-10-11): the clamp notes are whole endings of the hover
(`te_demog_st_ontop_end`, `_end_rest`, `_end_floor` and `_end_cap`, picked by nested `SelectLocalization`). That way no
value starts with `\n`, which `check_gui_lint.py` flags under style rule 8. `te_demog_st_ontop_floor` and `_cap`
below are gone.

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
 te_demog_st_mat_value:0 "#v [State.MakeScope.Var('te_dg_m_mat').GetValue|0]#! per 100k births"
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
 te_demog_st_ontop_tt_measured:0 "#b Deaths Added on Top#!\nThe census sets this state's deaths at its own rate, and the game adds what the census doesn't model on top. Last count: #v [State.MakeScope.Var('te_dg_cdr_model').GetValue|1]#! deaths per 1,000 people at the census's own rate, #v [State.MakeScope.Var('te_dg_cdr').GetValue|1]#! with the effects on top.\n Effects on the whole state: ×#v [State.MakeScope.ScriptValue('te_demog_deaths_whole_state')|2]#!\n#lore Pollution, devastation, decrees, events, the late laws and technologies the census doesn't model, and the census's own lag since its last count.#!\n Severe starvation: ×#v [State.MakeScope.ScriptValue('te_demog_deaths_severe')|2]#! (#v [State.MakeScope.Var('te_dg_sev_share').GetValue|%0]#! of its people at the count)\n Other effects on some of its people: ×#v [State.MakeScope.ScriptValue('te_demog_deaths_other')|2]#!\n#lore Dangerous workplaces, lines on one class, and people outside their homeland.#![SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.Var('te_dg_ed_clamp_d').GetValue, '(CFixedPoint)1' ), 'te_demog_st_ontop_floor', '' )][SelectLocalization( EqualTo_CFixedPoint( State.MakeScope.Var('te_dg_ed_clamp_d').GetValue, '(CFixedPoint)2' ), 'te_demog_st_ontop_cap', '' )]"
 te_demog_st_ontop_floor:0 "\n\n#R The census couldn't bring deaths down to its own rate this year:#! the game's death rate can't fall below a fifth of its base, so deaths ran higher."
 te_demog_st_ontop_cap:0 "\n\n#R The census couldn't raise deaths to its own rate this year:#! the game's death rate can't rise past four times its base, so deaths ran lower."
```

Also:
- `te_demog_st_e0_causes`: replace its list with
  `"Each cause of death runs at the rates of a poor country without modern medicine, times a multiplier that medicine, health laws, institutions and a higher [concept_sol] bring down. The Causes of Death section below breaks each one down."`
  (rule 2: the figures move one section down, none is lost).
- `te_demog_how_mortality`: append
  `" Medicine reaches a state over years: health care access and each treatment close a share of the gap at each count, a tenth at first and more as communications and medical training improve. Turmoil raises deaths from accidents and violence."`

- [x] **Step 6: Run the tests and the loc checks**

Run:
- `.venv/bin/python -m unittest test_demographics_registry`;
- `python3 organize_loc.py`, then `python3 organize_loc.py --check`;
- `python3 scripts/analysis/check_localization_files.py`;
- `.venv/bin/python concept_reference_audit.py` and `.venv/bin/python loc_coverage_audit.py --strict`.

Expected: OK, and nothing flagged for the new keys.

- [x] **Step 7: Commit** everything organize_loc rewrote with the rest: "Demographics: what the Causes of Death section
  reads".

---

### Task 9: The section on the state subtab, and the country tab's TODO (owner in-game check)

**Files:**
- Modify: `gui/te_demographics_widgets.gui` (new type `te_state_demog_causes` before `te_state_demog_pyramid`; its
  place in `te_state_demog_content`; the file header's list; the TODO in `te_demog_tab_sections`)
- Test: `test_demographics_registry.py` (new `TestCausesSection`)

**Interfaces:**
- Consumes: Task 8's loc keys and gates.
- Produces: `te_state_demog_causes`; the collapse flag `te_demog_st_causes_closed`.

- [x] **Step 1: Write the failing tests**

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
    """The Causes of Death section on the state subtab (the plan's Task 9)."""

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
        split = re.compile(r"te_dg_ed_state|te_dg_ed_sev|te_dg_sev_share|te_dg_ed_clamp_d|te_demog_deaths_")
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

- [x] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_registry.TestCausesSection`
Expected: ERROR (`te_state_demog_causes` not found).

- [x] **Step 3: The section** (before `type te_state_demog_pyramid`)

```
	### Causes of Death (owner, 2026-10-11; docs/superpowers/archive/plans/2026-10-11-demographics-causes-of-death.md):
	### Health Care Access and the five causes the census's life table runs on, each with its factors on hover
	### (the generated te_demog_f_*, which the census multiplies), then, under Full, the deaths the game added on
	### top of the census. Open by default (rule 1), with a flag of its own (te_demog_st_causes_closed). The rows sit
	### under te_demog_state_causes_sgui (the step's inputs exist: a census from before this build waits a step);
	### the on-top row under te_demog_state_full_sgui, its figure picked by te_demog_state_on_top_sgui (a measured
	### scale). Labels fit te_demog_figure_row's 240-unit label cell: "Chronic Illness, Old Age" is the longest, 24
	### characters, about 227 in the medium font with the 10%. Values fit its 200-unit value cell: "670 per 100k
	### births" is the longest, 19 characters, about 180 ("per 100,000 births" would elide at about 208).
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

- [x] **Step 4: The country tab's TODO** (`te_demog_tab_sections`, between `te_demog_overview = {}` and
  `te_demog_sec_pyramid = {}`)

```
			### TODO (#894): the country's Causes of Death, people-weighted over its census states (te_dg_c_*_w
			### in te_demog_country_census already weights the cause multipliers), once the state subtab's
			### te_state_demog_causes has been seen in game (owner, 2026-10-11). It goes here, after the overview.
```

- [x] **Step 5: Run the tests and the GUI checks**

Run:
- `.venv/bin/python -m unittest test_demographics_registry`;
- `python3 scripts/analysis/check_gui_lint.py`;
- `.venv/bin/python gui_reference_audit.py --strict`;
- `python3 scripts/format_paradox_tabs.py --check gui/te_demographics_widgets.gui`.

Expected: OK; no lint error. A warning on markup no mod `.gui` used before must not appear: every element here is
already in the file.

- [x] **Step 6: Commit**: "Demographics: the Causes of Death section on the state subtab".

- [ ] **Owner in-game check** (not done in this run: the PR body carries the list) (before Task 11's docs; see Task 11 Step 4 for the list). Merge `origin/main`, read
  the deploy dry run alone, then deploy from the full checkout, per CLAUDE.md "Play-testing unmerged work".

---

### Task 10: The harness reads the step's inputs (`fidelity` and `history`)

**Files:**
- Modify: `scripts/analysis/demographics_harness.py` (`FIDELITY_VARS`, `fidelity_rows`, `_fidelity`'s header lines;
  `country_figures`, `history_rows`, `cmd_history`; a helper `census_inputs`)
- Test: `test_demographics_harness.py` (`TestFidelity`, `TestHistory` or the file's history tests)

`history` is the calibration's view (the model's life expectancy and growth beside history's). With medicine drifting,
a country's census runs behind its targets after every law and technology, so `history` must see the lag as the census
does (the review's I4). `#906` notes `fidelity` won't run on that branch's saves; this task rewrites only its inputs.

**Interfaces:**
- Consumes: `M.Inputs.turmoil`, `M.Inputs.medicine` (Task 1); the variables of Tasks 4–5.
- Produces: `H.census_inputs(inp, got) -> M.Inputs`. With every input variable in `got`, it returns `inp` with the
  step's medicine, turmoil, crowding and plain type sums; otherwise `inp` unchanged. `H.country_figures(states,
  carriers, stored=None)` and `H.history_rows(sections, year, anchors, carriers=None, stored=None)`, `stored` being
  `{state id: {variable: value}}` from `S.read_variables`.

- [x] **Step 1: Write the failing tests**

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

- [x] **Step 2: Run them to see them fail**

Run: `.venv/bin/python -m unittest test_demographics_harness.TestFidelity`
Expected: ERROR (`census_inputs` not defined).

- [x] **Step 3: The harness**

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

- [x] **Step 4: `history` through the same inputs**

Test first, in `TestHarness` beside its `country_figures` test (the same synthetic states):

```python
    def test_history_sees_the_censuss_lag(self):
        """A state whose stored medicine is behind its targets reads a lower life expectancy than at its targets; with
        nothing stored, the figures are as before (the Causes of Death plan, Task 10)."""
        carriers = DM.load_carriers()
        c = S.CountryInputs("TST")
        c.population, c.sol_x_size, c.wealth_tfr_x_size = 1000.0, 13.0 * 1000.0, M.wealth_tfr(13.0) * 1000.0
        c.workforce, c.literate = 500.0, 100.0
        c.techs = {"medical_degrees", "pharmaceuticals", "modern_nursing"}
        states = [("1", c, True)]
        at_target = H.country_figures(states, carriers)
        behind = {"1": dict(TestFidelity.STORED, te_dg_acc=0.4, te_dg_trt_inf=0.0, te_dg_trt_mat=0.0,
                            te_dg_trt_chr=0.0)}
        self.assertLess(H.country_figures(states, carriers, stored=behind)["e0"], at_target["e0"])
        self.assertEqual(H.country_figures(states, carriers, stored={}), at_target)
```

Then:

```python
def country_figures(states, carriers, stored=None):
    """A country's model figures as the census builds them: each state's own rates (its SoL, literacy, urban share and
    incorporation; with `stored`, the census's own inputs from the save, so medicine as it had spread), weighted by its
    people."""
    stored = stored or {}
    figs = [(st.population, model_figures(census_inputs(inputs_for(st, carriers, incorporated=inc), stored.get(sid, {}))))
            for sid, st, inc in states if st.population > 0]
    tot = sum(p for p, _ in figs) or 1
    return {k: sum(p * f[k] for p, f in figs) / tot for k in ("e0", "imr", "tfr", "r")}
```

`history_rows` passes `stored` to both of its `country_figures` calls. `cmd_history` reads it per save:
`_countries, walked = S.read_variables(path, (), CENSUS_INPUT_VARS)` and
`stored = {sid: rec["vars"] for sid, rec in walked.items()}`. It prints one line under the world line: "N states on the
census's own inputs (medicine as it had spread)".

- [x] **Step 5: Run the harness tests, then commit**

Run: `.venv/bin/python -m unittest test_demographics_harness`
Expected: OK.

Commit: "Demographics harness: fidelity and history read the step's own inputs".

---

### Task 11: Docs, the player guide and the in-game checklist

**Files:**
- Modify: `docs/systems/mod_systems.md` (§ Demographics)
- Modify: `docs/guides/python_tools.md` (the harness's `fidelity` line)
- Modify: `docs/player_guide/08-states.md` (§ Demographics), `docs/player_guide/06-politics.md` (§ New decrees), then
  rebuild `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`
- Modify: `docs/superpowers/archive/plans/2026-10-10-demographics-phase2-engine-rates.md` §2 (one "Amended 2026-10-11 (3)"
  bullet pointing here)

- [x] **Step 1: mod_systems.md.** In § Demographics:
  - **Files table:** the new script values, effects, sguis, the decree, the type's carriers, the GUI type.
  - **Variable families:** add a row "Causes of Death (2026-10-11)": `te_dg_acc`, `te_dg_trt_*`, `te_dg_in_*`; under
    Full `te_dg_ed_state`, `te_dg_ed_sev`, `te_dg_sev_share`, `te_dg_sp_d`, `te_dg_ss_d`, `te_dg_rate_clamp_d`,
    `te_dg_ed_clamp_d`.
  - **A new subsection "Causes of Death (2026-10-11)"** after "The census's births and deaths". It covers:
    - the factor table and why the factors read stored inputs;
    - the drift (rate, carriers, decree, snap, seed and old-save behaviour, the re-seed accepted);
    - turmoil, with the vanilla `state_mortality_turmoil_mult` note;
    - the split at both ends of #907's window (the pops' own lines at the end from the walk, at the start from the
      refresh's `te_dg_sp_d` / `te_dg_ss_d`), with its formula:
      - whole state = `te_dg_ed_state ÷ te_dg_ed_target`;
      - severe starvation = `(te_dg_ed_state + te_dg_ed_sev) ÷ te_dg_ed_state`;
      - other effects = `te_dg_ed ÷ (te_dg_ed_state + te_dg_ed_sev)`;
      - why os_d can't split dz;
    - the red threshold, the clamp side (copied for the measured window) and the severe-starvation share;
    - that under Display only the drift and turmoil move the shown figures but not the game;
    - that under fast mode the whole state's part also carries K − 1 times a famine's share (the fast term sits in the
      read);
    - the #894 note that the walk's severe term (+1.0), never fitted, moves the figure (resolved by #913 before this
      landed: mod_systems says severe starvation scales by the starvation value);
    - the approved lag table from Task 3;
    - the release's handling of the decree;
    - the decree's placeholder icon (`gui_style_guide.md` rule 10). The texture is vanilla's
      `decree_emergency_relief.dds`, set in `common/decrees/extra_decrees.txt`. The final art's subject: a doctor's bag
      over a map pin. Its proposed path: `gfx/interface/icons/decree/decree_medical_outreach.dds`.
  - **"Owner checks in game":** items 11–13 from Step 4 below, short.
  - **`gen_demographics.py`'s bullet:** "the cause multipliers are products of one script value per factor
    (`P.CAUSE_FACTORS`), on the step's stored inputs".

- [x] **Step 2: The player guide.** Match the depth already there (CLAUDE.md "Keep the player guide current").
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
  - `06-politics.md`, § New decrees: "The mod adds 15 decrees." becomes "The mod adds 15 decrees, and development builds
    a 16th under the Demographics rule's Full setting." Add the row `| Medical Outreach (development builds only;
    Demographics, Full only) | Medical Degrees | New medicine reaches the state faster; see [States and
    population](08-states.md#demographics) |`.
  - Run `python3 scripts/analysis/check_player_guide_style.py --strict`, rebuild with
    `.venv/bin/python scripts/build_player_guide.py`, and check `scripts/build_player_guide.py --check`.

- [x] **Step 3: python_tools.md and the phase 2 plan.**
  - `python_tools.md`: the harness list's `fidelity` and `history` lines gain "run the model on the census's stored
    inputs (the drifted medicine, turmoil) when the save holds them", and a new line for `lag` ("years of life
    expectancy behind the target while medicine spreads, the drift numbers' evidence").
  - `python_tools.md`, the console's row (review of Tasks 4–5, minor 1): option **l**'s five cause multipliers are the
    last step's figures, not live ones (−1 before a census's first step), so after a console law or tech change they
    disagree with the type reads on the same line until the next step; the line also logs `diff=`, the spread's rate.
    Option **a** advances the drift one extra step per run (beside its note on a second run in one year).
  - The 2026-10-10 plan's §2: one bullet, "Amended 2026-10-11 (3): the Causes of Death plan
    (`docs/superpowers/archive/plans/2026-10-11-demographics-causes-of-death.md`) adds turmoil to the external cause and
    drifts medicine; both reach M, under Full only."

- [x] **Step 4: The in-game checklist** (for the owner; the PR body carries it, and `mod_systems.md` keeps 11–13):
  1. **Layout.** A new 1836 game under Full: the state subtab shows Causes of Death after the overview, open. No row
     label or value ends in "...". Childbirth's "670 per 100k births" is the longest value.
  2. **Health Care Access.** 40% in an unincorporated colony. More in a Ministry of Health country's incorporated
     states, with the hover's two lines ("Where it is heading:") adding up to the target: the row's figure once
     medicine has arrived, the right-hand figure while it reads "a → b".
  3. **The hovers multiply to their rows.** Check one: Infection and Hunger's factors multiplied give its ×figure.
  4. **Medicine drifts.** Enact a health law or research Modern Nursing through the console: the Medicine line reads
     "×a → ×b" at once. After the state's next count the row has moved about a tenth to a fifth of the way.
  5. **Medical Outreach.** In the decree list under Full only, and absent in a Display only game. Offered only where
     medicine is behind. Issuing it raises the hover's "closes N% of the gap" by 20 points in that state. Option l's
     `diff=` shows the same.
  6. **Deaths Added on Top.** Absent outside Full. "After the next count" on a state's first Full count. A ×figure
     from the next. The same on the first Full count after Display only. Red from ×1.25: try a famine state, or
     late-game India. The hover's three parts multiply to the row, and severe starvation's share reads beside its
     part. Option n's `ed_state=`, `ed_sev=`, `sev=` and `clamp_d=` match the hover.
  7. **Severe starvation's sum parses** (the review of Task 6). In a famine state under Full, option n logs
     `ed_sev=` above 0. `debug.log` shows no load-time parse error in `te_demog_generated_effects.txt`. A failed parse
     would most likely show only as `ed_sev=0`.
     - If it fails, move the walk's severe ladder (`te_demog_absorbed_walk_pop`) into a named pop-scope script value
       and multiply by that.
  8. **Turmoil.** A state in high turmoil shows Turmoil above ×1.00 under Accidents and Violence.
  9. **An old save** from before this build: the section reads "after its next count" until each state's step.
  10. **`debug.log`:** no "Failed to fetch variable" or errors from `te_demog_f_*`, `te_dg_acc`, `te_dg_in_*` or the
     decree.

- [x] **Step 5: Run the whole suite and the checks:**
  - `.venv/bin/python -m unittest discover -s . -p 'test_*.py'` (read the summary with `grep -E '^(Ran |OK|FAILED)'`);
  - `.venv/bin/ruff check .`;
  - `python3 scripts/format_paradox_tabs.py --check` on the changed `.txt`/`.gui`;
  - `python3 organize_loc.py --check`;
  - `.venv/bin/python scripts/generators/gen_demographics.py --check`;
  - `python3 scripts/build_player_guide.py --check`;
  - the CI audits (`.github/workflows/ci.yml`'s list);
  - the PEP 701 grep on the changed `.py` files.

- [x] **Step 6: Commit**: "Demographics: docs, guide and checklist for Causes of Death".

---

## Self-review notes (for the executor)

- **Task 6 writes the four on-top display values** (`te_demog_deaths_on_top`, `_whole_state`, `_severe`, `_other`;
  their text is in Task 8 Step 3); Task 8 adds the rest beside them.
- **Task 6 waits for the trapezoid PR,** and is checked against its merged names first ("Dependencies and shared
  edits"). The other tasks can go ahead of it.
- **`_mod_fixtures` and `_stored`** are defined once in `test_demographics_registry.py`, above `_engine_for`, and used
  by Tasks 4, 5 and 8.
- **The generated files change twice** (Tasks 4 and 6), and the trapezoid and #906 change them too. Regenerate after
  each task and after each merge; never merge them by hand.
