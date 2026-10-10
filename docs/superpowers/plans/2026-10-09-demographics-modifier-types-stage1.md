# Demographics modifier types, stage 1 (mortality): implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The census's mortality inputs from laws, technology and institutions become registered modifier types whose values sit on their carriers in the game files. Medicine becomes `1 − access × treatment`, and the values are recalibrated against §2.4's anchors and the fast run.

**Architecture:** `demographics_params.py` loses `TECH_MULT`, `LAW_MULT` and `INSTITUTION_MULT` and keeps only the model's constants. A new resolver, `scripts/analysis/demographics_modifiers.py`, reads each type's carriers from a narrow `ModState`, with vanilla from the committed snapshot, and sums a state's totals from its owner's techs, laws and institution levels. The model takes those totals in `Inputs.mods`. The generator writes `te_demog_mult_*` as reads of the same types (`modifier:` for state types, `owner.modifier:` for country types). The census script that calls them is unchanged.

**Tech Stack:** Python 3.11/3.12 (unittest), Paradox script (`common/`), the existing generator `scripts/generators/gen_demographics.py`.

**Spec:** `docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md` (stage 1). Parent: `docs/superpowers/specs/2026-10-08-demographics-design.md` §2.4, §8.4.

## Owner rulings this plan builds on

- 2026-10-09: all six of the spec's owner calls are accepted as recommended.
- 2026-10-09: build stage 1 up to a draft PR, with no merge and no deploy.
- **A deviation from the spec's names, for the PR body.** Treatment and the flat law and tech terms become **`country_*`** types, carried by techs' and laws' `modifier` and read in state scope as `owner.modifier:`. Only the per-level institution terms are **`state_*`** types, carried in `institution_modifier` or an institution's own `modifier`.
  - Why: a mod `state_*` type in a country `modifier` flowing down to state `modifier:` is unproven (the spec's check a). If it failed, every treatment would read 0 and nothing would log it. The `country_*` path is proven: `owner.modifier:country_fertility_means_add` is live in the census.
  - The trade-off: a tech's line shows on the country's breakdown, and access shows on the state's.

## The types

| Type | Scope | Carriers | Read in the census |
|---|---|---|---|
| `state_health_care_access_add` | state | `institution_modifier` of Charitable Health System, Private Health Insurance and Public Health Insurance (per level, incorporated states only) | `modifier:` |
| `country_infection_treatment_add` | country | techs' `modifier`: medical_degrees, pharmaceuticals, modern_nursing, antibiotics, modern_vaccines, antibiotic_mass_production | `owner.modifier:` |
| `country_maternal_treatment_add` | country | techs: modern_nursing, antibiotics, modern_pharmaceuticals | `owner.modifier:` |
| `country_chronic_treatment_add` | country | techs: modern_pharmaceuticals, telemedicine, personalized_medicine | `owner.modifier:` |
| `country_external_mortality_mult` | country | combustion_engine (+); Local, Dedicated and Militarized Police (−) | `owner.modifier:` |
| `state_external_mortality_mult` | state | `institution_ministry_of_consumer_protection`'s own `modifier` (per level) | `modifier:` |
| `country_work_mortality_mult` | country | Child Labor Allowed (+) | `owner.modifier:` |
| `state_work_mortality_mult` | state | `institution_modifier` of Regulatory Bodies and Worker Protections (Workplace Safety, per level) | `modifier:` |
| `country_chronic_mortality_mult` | country | Old Age Pension (−) | `owner.modifier:` |

Combination (spec Decision 1):
- Medicine for infection, maternal and chronic deaths is `1 − access × treatment`.
  - access = `clamp(BASE_ACCESS + state_health_care_access_add, 0, 1)`;
  - treatment = `clamp(country_<cause>_treatment_add, 0, TREATMENT_CAP[cause])`.
- Every other term is `max(MORTALITY_MULT_FLOOR, 1 + Σ its types)`: external and work sum a country type and a state type; chronic's plain term is the pension.
- Standard of living, literacy and crowding stay as they are.

**Starting values** (Task 7 recalibrates every medicine value; external and work keep these):

| Carrier | Line |
|---|---|
| medical_degrees | infection treatment 0.10 |
| pharmaceuticals | infection 0.14 |
| modern_nursing | infection 0.11, maternal 0.5 |
| antibiotics | infection 0.26, maternal 0.3 |
| modern_vaccines | infection 0.16 |
| antibiotic_mass_production | infection 0.04 |
| modern_pharmaceuticals | maternal 0.1, chronic 0.25 |
| telemedicine | chronic 0.07 |
| personalized_medicine | chronic 0.27 |
| combustion_engine | country external +0.3 |
| law_local_police / law_dedicated_police / law_militarized_police | country external −0.05 / −0.1 / −0.1 |
| law_child_labor_allowed | country work +0.1 |
| law_old_age_pension | country chronic −0.05 |
| law_charitable_health_system / law_private_health_insurance / law_public_health_insurance | access +0.03 / +0.08 / +0.12 a level |
| law_regulatory_bodies, law_worker_protections | state work −0.1 a level |
| institution_ministry_of_consumer_protection | state external −0.08 a level |

Constants: `BASE_ACCESS = 0.4`, `TREATMENT_CAP = {"infection": 0.95, "maternal": 0.99, "chronic": 0.8}`, `MORTALITY_MULT_FLOOR = 0.2`.

Per-level additive values replace compounding ones: Workplace Safety `0.85 ** level` was 0.44 at level 5; `1 − 0.1 × 5` is 0.5. The floor holds level 8 and above at 0.2, where `0.85 ** 9` was 0.23.

## Global Constraints

- Brace files use tab indentation (`python3 scripts/format_paradox_tabs.py <files>`) and keep **exactly one** UTF-8 BOM on every `.txt` and `.yml` the plan creates or edits.
- Script literals have at most five decimals (`test_gen_demographics.test_five_decimals_at_most`).
- New loc keys go in `localization/english/te_modifiers_l_english.yml`; run `python3 organize_loc.py` and commit what it moves (CI `organize_loc.py --check`).
- Never hand-edit `common/script_values/te_demog_generated_values.txt` or `common/scripted_effects/te_demog_generated_effects.txt`: edit `gen_demographics.py` and run `python3 scripts/generators/gen_demographics.py`.
- A second `INJECT:` of `institution_modifier` on a law that already has one is unverified: add the access line inside `common/laws/modified_health_system.txt`'s existing blocks. A second `INJECT:` of `modifier` on a law is already used (Regulatory Bodies, Old Age Pension).
- No new type name may already be an engine modifier (`docs/engine/modifiers_summary.txt`); the registry test enforces this.
- Python must compile on 3.11 (no PEP 701 f-strings).
- No deploy, and no `POST /reload` from the worktree. Run the suite with the dummy env vars:
  `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent ~/src/Vic3TimelineExtended/.venv/bin/python -m unittest discover -s . -p 'test_*.py' > /tmp/…/suite.txt 2>&1; grep -E '^(Ran |OK|FAILED)' …`
- Commits end with the session's `Co-Authored-By` / `Claude-Session` lines.

## Review Focus

1. **A carrier that no game read reaches.** A treatment line on a tech whose `modifier` the engine never reads (a typo in the INJECT target, or a mod tech edited in the wrong file) gives 0, so medicine is 1 everywhere. The registry test resolves every carrier through `ModState` and asserts each type has one. The probe (Task 8) reads the totals in game.
2. **A state type in a country block, or the reverse.** `state_health_care_access_add` in a law's `modifier` would apply in every state, unincorporated ones too, and is the unproven case (a). The registry test asserts that `country_*` types sit only in techs' and laws' `modifier`, and `state_*` types only in `institution_modifier` or an institution's `modifier`.
3. **Unincorporated states.** Access there is the base alone. The resolver's `incorporated=False` path and the probe's unincorporated-state line pin it.
4. **A 1836 game with no carrier.** A country with no medical tech and no health law must give exactly today's figures (medicine 1). The model test pins `cause_multipliers(Inputs())` against the SoL and literacy terms alone.
5. **The floor.** Workplace Safety at level 9 (−0.9) and a country with Child Labor plus Workplace Safety must stay at or above `MORTALITY_MULT_FLOOR`. The interpreter test runs the generated script at level 9.

---

### Task 1: The fast run's results doc

**Files:**
- Create: `docs/testing/demographics-fast-run-2026-10-09.md`

The doc goes first so the findings outlive this session. The data is on D:
- `/mnt/d/vic3te-data/vic3te-demog-fast-data/`: saves 1836–1860, logs to 19:56, and the post-crash log generations for 1869–1872.
- `/mnt/d/vic3te-data/vic3te-demog-gate-data/`: the gate run, saves 1837–1877.

- [ ] **Step 1: Write the doc** with these sections:
  - **The run.** K=12, observer, census log on, main 3d5e5807. Census year 2124 at game 1860.1.1. The C: disk filled at 19:56, so logs from 19:56 to 21:41 and saves from 1860 to about 1869 are missing. The game ran to December 1872 (census year 2279).
  - **What fast mode is.** Medicine and research run 12 times faster; standard of living, literacy and laws keep the calendar. So census year 2124 is an 1860 society with every medical tech of its time. That explains why TFR stays about 5 to the end: world 5.05, GBR 4.40, FRA 3.68.
  - **Health-law adopters.** At 1860.1.1 there are 11 Public Health Insurance adopters (NET 1839.1, BEL 1839.2, SAR 1839.7, D08/D09 1841, PEU 1844, BTN 1849, AFG 1850.11, GER 1850.5, D60 1851, NEJ 1853) and 43 Charitable. Private Health Insurance has none.
  - **The gap.** Median e0 for PHI adopters with all eight medical techs, against countries with no health system: 1900: 53.5 vs 44.2; 1950: 53.6 vs 44.8; 2000: 61.6 vs 52.5; 2075: 64.9 vs 59.5; 2124: 67.3 vs 62.0.
  - **Medicine with no health system.** IMR 135 → 39 and e0 44 → 62 at 1860-level standard of living.
  - **Wider figures.** Gini (GBR 0.78 at 2124), 65+ share 4–6%, and the Closed Borders `mig_raw` check from `demographics_observer_report.py --closed-borders` on the fast saves.
  - **Runtime errors.** None from the demographics code; only the load-time set-but-unused notices.
  - **Confounds.** Vanilla's PHI `institution_modifier` also adds +0.5 standard of living a level, and the census line has no SoL. So Task 7's `adopters` command compares at matched SoL.
  - **Reproduce.** The commands used, and Task 7's commands once they exist.
- [ ] **Step 2: Commit** `docs/testing/demographics-fast-run-2026-10-09.md`: "Demographics fast run: results to 1860 (census year 2124)".

### Task 2: The modifier types and their loc

**Files:**
- Modify: `common/modifier_type_definitions/demographics_modifier_types.txt`
- Modify: `localization/english/te_modifiers_l_english.yml`
- Modify: `scripts/analysis/demographics_params.py` (only the type names; the values come in Task 4)
- Test: `test_demographics_registry.py` (new class `TestModifierTypes`)

**Interfaces:**
- Produces, in `demographics_params`:
  - `ACCESS_TYPE = "state_health_care_access_add"`
  - `MEDICINE_CAUSES = ("infection", "maternal", "chronic")`
  - `TREATMENT_TYPE = {cause: f"country_{cause}_treatment_add" for cause in MEDICINE_CAUSES}`
  - `MORTALITY_TYPES = {"external": ("country_external_mortality_mult", "state_external_mortality_mult"), "work": ("country_work_mortality_mult", "state_work_mortality_mult"), "chronic": ("country_chronic_mortality_mult",)}`
  - `DEMOG_MORTALITY_TYPES`: a tuple of all nine names in the table's order.

- [ ] **Step 1: Write the failing test** in `test_demographics_registry.py`:

```python
TYPES_FILE = ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt"
MODIFIERS_LOC = ROOT / "localization" / "english" / "te_modifiers_l_english.yml"
ENGINE_MODIFIERS = ROOT / "docs" / "engine" / "modifiers_summary.txt"


class TestModifierTypes(unittest.TestCase):
    """Stage 1 of the modifier-types design: every mortality input is a registered, named type."""

    def test_every_type_is_registered_script_only(self):
        text = _text(TYPES_FILE)
        for name in P.DEMOG_MORTALITY_TYPES:
            body = _block(text, name)
            self.assertIn("script_only = yes", body, name)
            self.assertRegex(body, r"decimals = \d", name)

    def test_every_type_has_a_name_and_a_description(self):
        loc = _text(MODIFIERS_LOC)
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertRegex(loc, rf"(?m)^ {name}:0 \"", name)
            self.assertRegex(loc, rf"(?m)^ {name}_desc:0 \"", name)

    def test_no_type_is_an_engine_modifier(self):
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertNotIn(name, engine, name)

    def test_scope_follows_the_prefix(self):
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertTrue(name.startswith(("country_", "state_")), name)
```

(Check the `modifiers_summary.txt` format before relying on `split("|")[1]`: line 6105 reads `country|country_workflow_opt_pb_principles_bool|`.)

- [ ] **Step 2: Run** `python3 -m unittest test_demographics_registry.TestModifierTypes -v` (with the dummy env vars). Expected: FAIL (`AttributeError: … DEMOG_MORTALITY_TYPES`).
- [ ] **Step 3: Add the names to params** (under a new `# ---- Mortality inputs as modifier types` header, beside the old tables, which Task 4 removes), the nine entries in the types file, and the loc.

Types file, appended after `country_fertility_means_add`:

```
# Mortality: stage 1 of docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md.
# Read by the census only (te_demog_mult_*): the engine never applies them. Medicine is
# 1 - access x treatment; the other terms are 1 + their types' sum, floored.
# Country types sit in techs' and laws' modifier blocks; state types in a law's
# institution_modifier or an institution's modifier, per investment level, incorporated states only.
state_health_care_access_add = {
	color = good
	percent = yes
	decimals = 0
	script_only = yes
}
country_infection_treatment_add = {
	color = good
	percent = yes
	decimals = 0
	script_only = yes
}
```

…and the same block for `country_maternal_treatment_add` and `country_chronic_treatment_add`. The six `*_mortality_mult` types take `color = bad` (a cut shows green), `percent = yes`, `decimals = 0`, `script_only = yes`.

Loc (in `te_modifiers_l_english.yml`, next to `country_fertility_means_add`). Every description ends with the census sentence, because phase 1 applies nothing:

```yaml
 state_health_care_access_add:0 "Health Care Access"
 state_health_care_access_add_desc:0 "How many people can reach a doctor, a nurse or a hospital. Medicine saves lives only as far as it reaches. Markets and charity give some access everywhere, and a health law adds more with each level of its institution. Used by the census on the Demographics tab."
 country_infection_treatment_add:0 "Treatment of Infection"
 country_infection_treatment_add_desc:0 "The share of deaths from infection and hunger that medicine can prevent where people can reach it. Used by the census on the Demographics tab."
 country_maternal_treatment_add:0 "Treatment in Childbirth"
 country_maternal_treatment_add_desc:0 "The share of mothers' deaths in childbirth that medicine can prevent where people can reach it. Used by the census on the Demographics tab."
 country_chronic_treatment_add:0 "Treatment of Chronic Disease"
 country_chronic_treatment_add_desc:0 "The share of deaths from the diseases of age that medicine can prevent where people can reach it. Used by the census on the Demographics tab."
 country_external_mortality_mult:0 "Deaths from Violence and Accidents"
 country_external_mortality_mult_desc:0 "Deaths from violence, traffic and everyday accidents, mostly of young men. Used by the census on the Demographics tab."
 state_external_mortality_mult:0 "Deaths from Violence and Accidents"
 state_external_mortality_mult_desc:0 "Deaths from violence, traffic and everyday accidents, mostly of young men. Used by the census on the Demographics tab."
 country_work_mortality_mult:0 "Deaths at Work"
 country_work_mortality_mult_desc:0 "Deaths in mines, mills and workshops, shared between women and men by their part of the workforce. Used by the census on the Demographics tab."
 state_work_mortality_mult:0 "Deaths at Work"
 state_work_mortality_mult_desc:0 "Deaths in mines, mills and workshops, shared between women and men by their part of the workforce. Used by the census on the Demographics tab."
 country_chronic_mortality_mult:0 "Deaths from Chronic Disease"
 country_chronic_mortality_mult_desc:0 "Deaths from the diseases of age, which poverty in old age makes more common. Used by the census on the Demographics tab."
```

Then run `python3 organize_loc.py` and keep what it moves.
- [ ] **Step 4: Run the test again.** Expected: PASS.
- [ ] **Step 5: Commit** the types file, loc, params and test: "Demographics: register the mortality modifier types".

### Task 3: The resolver

**Files:**
- Create: `scripts/analysis/demographics_modifiers.py`
- Test: `test_demographics_modifiers.py`

**Interfaces:**
- Consumes: `P.DEMOG_MORTALITY_TYPES` (Task 2).
- Produces:
  - `Carrier(kind: str, key: str, type: str, value: float, institution: str | None)`, a frozen dataclass. `kind` is one of `"technology"`, `"law"`, `"law_institution"`, `"institution"`.
  - `load_carriers(root: Path = ROOT, types=P.DEMOG_MORTALITY_TYPES) -> list[Carrier]`
  - `totals(carriers, techs=(), laws=(), institutions=None, incorporated=True) -> dict[str, float]`: every type in `types` gets a key, 0.0 when nothing carries it.

```python
"""The demographics modifier types' totals, resolved from the game files.

Spec: docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md, Decision 2:
the values sit beside the techs, laws and institutions that carry them, and the model takes
modifier totals. load_carriers() reads every carrier from a narrow ModState (technologies,
laws and institutions; vanilla from the committed vanilla_parsed/ snapshot, so no game is
needed). totals() sums what one state reads, given its owner's techs, laws and institution
investment levels:
    a technology's or law's `modifier`      country types, every state
    a law's `institution_modifier`          per level of the law's institution, incorporated states
    an institution's own `modifier`         per level, incorporated states
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_params as P  # noqa: E402

ENTITY_TYPES = {"Technologies": "technology/technologies", "Laws": "laws", "Institutions": "institutions"}


@dataclass(frozen=True)
class Carrier:
    kind: str
    key: str
    type: str
    value: float
    institution: str | None = None


def _u(v):
    """A parsed value without its ('=', …) wrapper."""
    return v[1] if isinstance(v, tuple) and len(v) == 2 and v[0] == "=" else v


def _state(root):
    import vanilla_parsed
    from mod_state import ModState

    snap = Path(root) / "vanilla_parsed"
    manifest = vanilla_parsed.read_manifest(str(snap)) or {}
    vanilla = {}
    for et in ENTITY_TYPES:
        info = manifest.get("entity_types", {}).get(et)
        if info:
            with open(snap / info["file"], encoding="utf-8") as fh:
                vanilla[et] = vanilla_parsed.decode(json.load(fh))
    return ModState({et: "" for et in ENTITY_TYPES},
                    {et: os.path.join(str(root), "common", d) for et, d in ENTITY_TYPES.items()},
                    vanilla_data=vanilla)


def _lines(block, types):
    for k, v in (_u(block) or {}).items():
        if k in types:
            yield k, float(_u(v))


def load_carriers(root=ROOT, types=P.DEMOG_MORTALITY_TYPES):
    """Every line that carries one of `types`, from techs, laws and institutions."""
    types = set(types)
    ms = _state(root)
    out = []
    for key, entry in ms.get_data("Technologies").items():
        for t, v in _lines(_u(entry).get("modifier"), types):
            out.append(Carrier("technology", key, t, v))
    for key, entry in ms.get_data("Laws").items():
        body = _u(entry)
        for t, v in _lines(body.get("modifier"), types):
            out.append(Carrier("law", key, t, v))
        inst = _u(body.get("institution"))
        for t, v in _lines(body.get("institution_modifier"), types):
            out.append(Carrier("law_institution", key, t, v, inst))
    for key, entry in ms.get_data("Institutions").items():
        for t, v in _lines(_u(entry).get("modifier"), types):
            out.append(Carrier("institution", key, t, v, key))
    return out


def totals(carriers, techs=(), laws=(), institutions=None, incorporated=True, types=P.DEMOG_MORTALITY_TYPES):
    """{type: total} that one state reads: its owner's techs and laws, and, in an incorporated
    state, each institution line times the owner's investment level in that institution."""
    techs, laws, levels = set(techs), set(laws), institutions or {}
    out = {t: 0.0 for t in types}
    for c in carriers:
        if c.type not in out:
            continue
        if c.kind == "technology" and c.key in techs:
            out[c.type] += c.value
        elif c.kind == "law" and c.key in laws:
            out[c.type] += c.value
        elif c.kind == "law_institution" and c.key in laws and incorporated:
            out[c.type] += c.value * levels.get(c.institution, 0)
        elif c.kind == "institution" and incorporated:
            out[c.type] += c.value * levels.get(c.key, 0)
    return out
```

(Check `ModState.get_data`'s return shape and `vanilla_parsed.read_manifest`'s argument type against `principle_tier_audit.load_state` before you rely on them. The probe on 2026-10-09 showed `get_data("Laws")` is a dict of `('=', {...})` tuples.)

- [ ] **Step 1: Write the failing tests** in `test_demographics_modifiers.py`:

```python
"""scripts/analysis/demographics_modifiers.py: carriers from the game files and a state's totals."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402

C = DM.Carrier


class TestTotals(unittest.TestCase):
    CARRIERS = [
        C("technology", "antibiotics", "country_infection_treatment_add", 0.26),
        C("law", "law_child_labor_allowed", "country_work_mortality_mult", 0.1),
        C("law_institution", "law_public_health_insurance", "state_health_care_access_add", 0.12,
          "institution_health_system"),
        C("institution", "institution_ministry_of_consumer_protection", "state_external_mortality_mult", -0.08,
          "institution_ministry_of_consumer_protection"),
    ]

    def test_nothing_held_is_all_zero(self):
        self.assertEqual(set(DM.totals(self.CARRIERS).values()), {0.0})
        self.assertEqual(set(DM.totals(self.CARRIERS)), set(P.DEMOG_MORTALITY_TYPES))

    def test_techs_and_laws_count_everywhere(self):
        t = DM.totals(self.CARRIERS, techs={"antibiotics"}, laws={"law_child_labor_allowed"}, incorporated=False)
        self.assertAlmostEqual(t["country_infection_treatment_add"], 0.26)
        self.assertAlmostEqual(t["country_work_mortality_mult"], 0.1)

    def test_institution_lines_scale_by_level_in_incorporated_states(self):
        levels = {"institution_health_system": 3, "institution_ministry_of_consumer_protection": 2}
        t = DM.totals(self.CARRIERS, laws={"law_public_health_insurance"}, institutions=levels)
        self.assertAlmostEqual(t["state_health_care_access_add"], 0.36)
        self.assertAlmostEqual(t["state_external_mortality_mult"], -0.16)

    def test_unincorporated_states_get_no_institution_line(self):
        levels = {"institution_health_system": 3, "institution_ministry_of_consumer_protection": 2}
        t = DM.totals(self.CARRIERS, laws={"law_public_health_insurance"}, institutions=levels, incorporated=False)
        self.assertEqual(t["state_health_care_access_add"], 0.0)
        self.assertEqual(t["state_external_mortality_mult"], 0.0)

    def test_a_law_institution_line_needs_its_law(self):
        t = DM.totals(self.CARRIERS, institutions={"institution_health_system": 3})
        self.assertEqual(t["state_health_care_access_add"], 0.0)


class TestCarriersInTheGameFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.carriers = DM.load_carriers()

    def test_every_type_has_a_carrier(self):
        carried = {c.type for c in self.carriers}
        for name in P.DEMOG_MORTALITY_TYPES:
            self.assertIn(name, carried, name)

    def test_country_types_only_in_country_blocks_and_state_types_only_per_level(self):
        for c in self.carriers:
            if c.type.startswith("country_"):
                self.assertIn(c.kind, ("technology", "law"), c)
            else:
                self.assertIn(c.kind, ("law_institution", "institution"), c)

    def test_health_laws_carry_access_on_the_health_institution(self):
        access = {c.key: c for c in self.carriers if c.type == P.ACCESS_TYPE}
        self.assertEqual(set(access), {"law_charitable_health_system", "law_private_health_insurance",
                                       "law_public_health_insurance"})
        for c in access.values():
            self.assertEqual(c.institution, "institution_health_system")
        self.assertLess(access["law_charitable_health_system"].value, access["law_private_health_insurance"].value)
        self.assertLess(access["law_private_health_insurance"].value, access["law_public_health_insurance"].value)
```

Task 5 adds the carriers, so `TestCarriersInTheGameFiles` stays red until then. `TestTotals` must pass now.
- [ ] **Step 2: Run** `python3 -m unittest test_demographics_modifiers.TestTotals -v`. Expected: FAIL (no module).
- [ ] **Step 3: Write `demographics_modifiers.py`** as above.
- [ ] **Step 4: Run** `TestTotals`. Expected: PASS. `TestCarriersInTheGameFiles` FAILS (no carriers yet).
- [ ] **Step 5: Commit** the resolver and its test: "Demographics: resolve the mortality types' totals from the game files".

### Task 4: The model reads modifier totals

**Files:**
- Modify: `scripts/analysis/demographics_params.py` (delete `TECH_MULT`, `LAW_MULT`, `INSTITUTION_MULT`; add the constants)
- Modify: `scripts/analysis/demographics_model.py` (`Inputs.mods`, `medicine`, `plain_multiplier`, `cause_multipliers`)
- Modify: `test_demographics_model.py` (scenarios resolve their `mods`), `test_demographics_harness.py` and `test_demographics_registry.py` wherever they build `Inputs` with techs or laws that should still change mortality
- Modify: `scripts/analysis/demographics_harness.py` `inputs_for` (passes `mods`; see Task 7 for institutions)

**Interfaces:**
- Consumes: `DM.load_carriers`, `DM.totals` (Task 3); the type names (Task 2).
- Produces: `Inputs.mods: dict` (`{type: total}`, default empty); `M.medicine(inp, cause) -> float`; `M.plain_multiplier(inp, cause) -> float`; `cause_multipliers(inp)` unchanged in signature.

Params (replacing the `TECH_MULT` … `INSTITUTION_MULT` block; keep the SoL, literacy and crowding constants):

```python
# Medicine for infection, maternal and chronic deaths is 1 - access x treatment (the
# modifier-types design, Decision 1). Access is what a state reaches: this base (markets and
# charity, everywhere, colonies and 1836 too) plus state_health_care_access_add, at most 1.
# Treatment is the cause's country_<cause>_treatment_add, at most its cap. The values of both
# live on their carriers in the game files (demographics_modifiers.py).
BASE_ACCESS = 0.4
TREATMENT_CAP = {"infection": 0.95, "maternal": 0.99, "chronic": 0.8}
# Every other law, technology or institution term is 1 + its types' sum, at least this.
MORTALITY_MULT_FLOOR = 0.2
```

Model:

```python
@dataclass
class Inputs:
    ...
    mods: dict = field(default_factory=dict)   # {modifier type: total} the state reads (demographics_modifiers.totals)


def medicine(inp, cause):
    """1 - access x treatment for one of P.MEDICINE_CAUSES (modifier-types design, Decision 1)."""
    access = clamp(P.BASE_ACCESS + inp.mods.get(P.ACCESS_TYPE, 0.0), 0.0, 1.0)
    treatment = clamp(inp.mods.get(P.TREATMENT_TYPE[cause], 0.0), 0.0, P.TREATMENT_CAP[cause])
    return 1 - access * treatment


def plain_multiplier(inp, cause):
    """1 + the cause's types' sum, at least P.MORTALITY_MULT_FLOOR."""
    return max(P.MORTALITY_MULT_FLOOR, 1 + sum(inp.mods.get(t, 0.0) for t in P.MORTALITY_TYPES.get(cause, ())))


def cause_multipliers(inp):
    """One multiplier per cause from the state's inputs; 1.0 at the base (§2.4). The script's
    te_demog_mult_<cause> computes the same, in the same order."""
    mult = {c: 1.0 for c in ("infection", "work", "external", "maternal", "chronic")}
    for cause in P.MEDICINE_CAUSES:
        mult[cause] *= medicine(inp, cause)
    for cause in P.MORTALITY_TYPES:
        mult[cause] *= plain_multiplier(inp, cause)
    mult["infection"] *= lerp_sol(inp.sol, 1.0, P.SOL_INFECTION_AT_HIGH)
    mult["infection"] *= 1 - P.LITERACY_INFECTION_WEIGHT * inp.literacy
    if inp.crowding and inp.institutions.get("institution_ministry_of_urban_planning", 0) == 0:
        mult["infection"] *= P.CROWDING_INFECTION_MULT
    mult["chronic"] *= lerp_sol(inp.sol, 1.0, P.SOL_CHRONIC_AT_HIGH)
    return mult
```

Tests: the scenarios in `test_demographics_model.py` keep their techs, laws and institutions, and gain `mods` from the resolver, so they stay readable:

```python
import demographics_modifiers as DM  # noqa: E402

CARRIERS = DM.load_carriers()


def scenario(**kw):
    """Inputs whose mods come from the game files' carriers for its techs, laws and institutions."""
    inp = M.Inputs(**kw)
    inp.mods = DM.totals(CARRIERS, inp.techs, inp.laws, inp.institutions)
    return inp
```

`WEST_1950`, `WEST_1990`, `INDIA_1975` and `BRITAIN_1836` become `scenario(...)` with the same fields. The bounds in `TestMortality` stay; Task 7 tightens them.

New model tests:

```python
class TestMedicine(unittest.TestCase):
    def test_no_carrier_is_exactly_the_old_base(self):
        inp = M.Inputs(sol=11, literacy=0.35)
        m = M.cause_multipliers(inp)
        self.assertEqual(m["maternal"], 1.0)
        self.assertEqual(m["work"], 1.0)
        self.assertEqual(m["external"], 1.0)
        self.assertAlmostEqual(m["infection"], M.lerp_sol(11, 1.0, P.SOL_INFECTION_AT_HIGH) * (1 - 0.3 * 0.35))

    def test_treatment_reaches_only_as_far_as_access(self):
        mods = {P.TREATMENT_TYPE["infection"]: 0.8}
        base = M.medicine(M.Inputs(mods=mods), "infection")
        full = M.medicine(M.Inputs(mods={**mods, P.ACCESS_TYPE: 1.0}), "infection")
        self.assertAlmostEqual(base, 1 - P.BASE_ACCESS * 0.8)
        self.assertAlmostEqual(full, 1 - 0.8)

    def test_access_without_treatment_does_nothing(self):
        self.assertEqual(M.medicine(M.Inputs(mods={P.ACCESS_TYPE: 0.6}), "maternal"), 1.0)

    def test_caps_hold(self):
        mods = {P.ACCESS_TYPE: 5.0, P.TREATMENT_TYPE["chronic"]: 5.0}
        self.assertAlmostEqual(M.medicine(M.Inputs(mods=mods), "chronic"), 1 - P.TREATMENT_CAP["chronic"])

    def test_plain_terms_are_floored(self):
        inp = M.Inputs(mods={"state_work_mortality_mult": -0.9, "country_work_mortality_mult": 0.1})
        self.assertEqual(M.plain_multiplier(inp, "work"), P.MORTALITY_MULT_FLOOR)
```

- [ ] **Step 1:** Write `TestMedicine` and the `scenario()` change. Run `python3 -m unittest test_demographics_model -v`. Expected: FAIL (`Inputs` has no `mods`).
- [ ] **Step 2:** Change params and the model as above. Delete `TECH_MULT`, `LAW_MULT` and `INSTITUTION_MULT`. Run `git grep -n -E 'TECH_MULT|LAW_MULT|INSTITUTION_MULT'`; the generator still uses them, and Task 6 rewrites it.
- [ ] **Step 3:** Run `test_demographics_model`, `test_demographics_harness` and `test_demographics_registry`. Expected: the model tests pass once Task 5's carriers exist. Before that, the scenarios resolve empty `mods` and `test_rich_country_today` fails. Commit Tasks 4 and 5 together if that is cleaner (one commit, "the model reads the types").
- [ ] **Step 4: Commit** (with Task 5's carriers, after Task 5 Step 4).

### Task 5: The carriers in the game files

**Files:**
- Create: `common/technology/technologies/te_demog_tech_injections.txt` (vanilla techs: medical_degrees, pharmaceuticals, modern_nursing, antibiotics, combustion_engine)
- Modify: `common/technology/technologies/era_6.txt` (modern_vaccines), `era_7.txt` (antibiotic_mass_production), `era_8.txt` (modern_pharmaceuticals), `era_10.txt` (telemedicine), `era_11.txt` (personalized_medicine): add lines to each tech's own `modifier`
- Create: `common/laws/te_demog_law_injections.txt` (`modifier` INJECTs on Local, Dedicated and Militarized Police, Child Labor Allowed and Old Age Pension; `institution_modifier` INJECTs on Regulatory Bodies and Worker Protections)
- Modify: `common/laws/modified_health_system.txt` (the access line inside each existing block)
- Modify: `common/institutions/extra_institutions.txt` (`institution_ministry_of_consumer_protection`'s `modifier`)

**Interfaces:**
- Consumes: the type names (Task 2).
- Produces: the carriers `DM.load_carriers()` returns (Task 3's `TestCarriersInTheGameFiles` turns green).

Tech INJECT file (header style as in `te_monetary_tech_injections.txt`, one BOM):

```
# Demographics: the medical techs' treatment lines and the motor age's road deaths.
# Spec: docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md (stage 1).
# Read only by the census (te_demog_mult_*); the engine never applies them. Values are
# calibrated in scripts/analysis/demographics_harness.py medicine (see
# docs/testing/demographics-fast-run-2026-10-09.md). The mod's own medical techs carry
# their lines in their own definitions (era_6.txt to era_11.txt).

INJECT:medical_degrees = {
	modifier = {
		country_infection_treatment_add = 0.1
	}
}

INJECT:pharmaceuticals = {
	modifier = {
		country_infection_treatment_add = 0.14
	}
}

INJECT:modern_nursing = {
	modifier = {
		country_infection_treatment_add = 0.11
		country_maternal_treatment_add = 0.5
	}
}

INJECT:antibiotics = {
	modifier = {
		country_infection_treatment_add = 0.26
		country_maternal_treatment_add = 0.3
	}
}

INJECT:combustion_engine = {
	modifier = {
		country_external_mortality_mult = 0.3
	}
}
```

`pharmaceuticals` already has an `INJECT` in `modified.txt` that adds `modifier`. A second `INJECT` of `modifier` follows the pattern Regulatory Bodies already uses (two files), and the probe confirms it. If the owner would rather not have two, move the line into `modified.txt`'s block. Record this in the PR body.

Mod techs: add the line inside the tech's existing `modifier = { … }` (e.g. `modern_vaccines`: `country_infection_treatment_add = 0.16`).

Law file:

```
# Demographics: law terms for the census's causes of death (modifier-types design, stage 1).
# Country lines (modifier) apply in every state; the Workplace Safety lines
# (institution_modifier) scale with the institution's level and apply in incorporated states.

INJECT:law_local_police = {
	modifier = {
		country_external_mortality_mult = -0.05
	}
}
```

…the same for Dedicated and Militarized Police (−0.1), Child Labor Allowed (`country_work_mortality_mult = 0.1`) and Old Age Pension (`country_chronic_mortality_mult = -0.05`). Then:

```
INJECT:law_regulatory_bodies = {
	institution_modifier = {
		state_work_mortality_mult = -0.1
	}
}

INJECT:law_worker_protections = {
	institution_modifier = {
		state_work_mortality_mult = -0.1
	}
}
```

`modified_health_system.txt`: inside each block's `institution_modifier`, add `state_health_care_access_add = 0.03` (Charitable), `0.08` (Private) or `0.12` (Public). Extend the header comment with one line on access.

`extra_institutions.txt`: add `state_external_mortality_mult = -0.08` to `institution_ministry_of_consumer_protection`'s `modifier`, with a comment. Keep its `state_mortality_mult = -0.01` (§8.4 removes that in phase 2).

- [ ] **Step 1:** Write the files. Check one BOM each: `head -c 3 <file> | xxd` shows `efbbbf`, and `head -c 6` does not show it twice. Run `python3 scripts/format_paradox_tabs.py --check` on them.
- [ ] **Step 2:** Run `test_demographics_modifiers` (all), `test_demographics_registry.TestModifierTypes`, `test_demographics_model`. Expected: PASS, apart from model bounds that Task 7 recalibrates. Record which fail and by how much.
- [ ] **Step 3:** Run `python3 duplicate_key_audit.py --strict`, `python3 loc_coverage_audit.py --strict`, `python3 modifier_visibility_audit.py` (check that its report flags none of the new lines as rendering "+0%"). Expected: clean.
- [ ] **Step 4: Commit** Tasks 4 and 5: "Demographics: the model reads the mortality types, carried by their techs, laws and institutions".

**Reviewer (one, after this task):** check every carrier's target exists (a mistyped `INJECT:` target is silent), that no `state_*` type sits in a `modifier` of a tech or law, that the access lines are inside the existing `institution_modifier` blocks, and that the BOMs and tabs are right.

### Task 6: The generator writes the reads

**Files:**
- Modify: `scripts/generators/gen_demographics.py` (`multipliers`, `render_values`; delete `max_institution_investment` if nothing else uses it)
- Modify: `test_gen_demographics.py` (drop `test_institution_chain_reaches_the_defines_maximum` and `test_missing_institution_maximum_raises`; add shape tests)
- Modify: `test_demographics_registry.py` (an interpreter test of `te_demog_mult_*`)
- Regenerate: `common/script_values/te_demog_generated_values.txt`

**Interfaces:**
- Consumes: `P.MEDICINE_CAUSES`, `P.TREATMENT_TYPE`, `P.ACCESS_TYPE`, `P.MORTALITY_TYPES`, `P.BASE_ACCESS`, `P.TREATMENT_CAP`, `P.MORTALITY_MULT_FLOOR`.
- Produces: `te_demog_mult_<cause>` script values (same names, state scope).

```python
def _read(t):
    """A type as the census reads it in state scope: a country type through the owner."""
    return f"owner.modifier:{t}" if t.startswith("country_") else f"modifier:{t}"


def multipliers(o):
    for cause in CAUSES:
        if cause == "maternal":
            o("# State scope: maternal deaths per 100,000 births (an MMR, not a multiplier): the base rate")
            o("# times the cause's multiplier (demographics_model.cause_multipliers, group_rates).")
        else:
            o(f"# State scope: the {cause} cause's multiplier (demographics_model.cause_multipliers).")
        o(f"te_demog_mult_{cause} = {{")
        o("value = 1")
        if cause in P.MEDICINE_CAUSES:
            o("# medicine: 1 - access x treatment (modifier-types design, Decision 1)")
            o("subtract = {")
            o(f"value = {_read(P.ACCESS_TYPE)}")
            o(f"add = {lit(P.BASE_ACCESS)}")
            o("min = 0")
            o("max = 1")
            o(f"multiply = {{ value = {_read(P.TREATMENT_TYPE[cause])} min = 0 max = {lit(P.TREATMENT_CAP[cause])} }}")
            o("}")
        if cause in P.MORTALITY_TYPES:
            adds = " ".join(f"add = {_read(t)}" for t in P.MORTALITY_TYPES[cause])
            o(f"multiply = {{ value = 1 {adds} min = {lit(P.MORTALITY_MULT_FLOOR)} }}")
        ...   # infection's SoL, literacy and crowding, chronic's SoL and maternal's base rate, as today
        o("}")
        o("")
```

Keep the rest of `multipliers` (women's work share, the means) as it is. `render_values` stops passing `max_institution_investment(root)`. Update the module docstring's "Inputs" paragraph, since `MAX_INSTITUTION_INVESTMENT` is no longer read.

Generator shape tests:

```python
    def test_causes_read_the_types_not_the_owners_techs(self):
        for cause in gen.CAUSES:
            body = self.values.split(f"te_demog_mult_{cause} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertNotIn("has_technology_researched", body)
            self.assertNotIn("has_law", body)
            self.assertNotIn("institution_investment_level = { institution = institution_health_system", body)

    def test_medicine_reads_access_and_the_causes_treatment(self):
        for cause in P.MEDICINE_CAUSES:
            body = self.values.split(f"te_demog_mult_{cause} = {{", 1)[1].split("\n}\n", 1)[0]
            self.assertIn(f"value = modifier:{P.ACCESS_TYPE}", body)
            self.assertIn(f"value = owner.modifier:{P.TREATMENT_TYPE[cause]}", body)

    def test_country_types_are_read_through_the_owner(self):
        for name in P.DEMOG_MORTALITY_TYPES:
            if name.startswith("country_"):
                self.assertNotRegex(self.values, rf"(?<!owner\.)modifier:{name}\b", name)
```

Interpreter test (registry): run each generated `te_demog_mult_<cause>` through `_Engine`, with the type reads as fixtures, against `cause_multipliers`:

```python
class TestCauseMultipliersScript(unittest.TestCase):
    """te_demog_mult_<cause> (generated) against demographics_model.cause_multipliers."""

    CASES = [
        {},
        {P.TREATMENT_TYPE["infection"]: 0.81, P.TREATMENT_TYPE["maternal"]: 0.9, P.TREATMENT_TYPE["chronic"]: 0.59},
        {P.ACCESS_TYPE: 0.6, P.TREATMENT_TYPE["infection"]: 0.81, P.TREATMENT_TYPE["maternal"]: 2.0,
         P.TREATMENT_TYPE["chronic"]: 0.3, "country_chronic_mortality_mult": -0.05},
        {"state_work_mortality_mult": -0.9, "country_work_mortality_mult": 0.1,
         "country_external_mortality_mult": 0.3, "state_external_mortality_mult": -0.4},
    ]

    def test_script_matches_the_model(self):
        for mods in self.CASES:
            for sol, lit in ((8, 0.0), (20, 0.5), (40, 1.0)):
                inp = demographics_model.Inputs(sol=sol, literacy=lit, mods=dict(mods))
                want = demographics_model.cause_multipliers(inp)
                fixtures = {("owner.modifier:" if t.startswith("country_") else "modifier:") + t: mods.get(t, 0.0)
                            for t in P.DEMOG_MORTALITY_TYPES}
                eng = _Engine(fixtures)
                eng.vars.update(te_dg_sol=float(sol), te_dg_lit=float(lit))
                for cause in ("infection", "work", "external", "chronic"):
                    with self.subTest(mods=mods, sol=sol, cause=cause):
                        got = eng.value(eng._tree(eng.values, f"te_demog_mult_{cause}"))
                        self.assertAlmostEqual(got, want[cause], places=9)
                got = eng.value(eng._tree(eng.values, "te_demog_mult_maternal"))
                self.assertAlmostEqual(got, want["maternal"] * P.MATERNAL_PER_100K_BIRTHS, places=6)
```

(`_Engine.number` looks fixture tokens up whole, so `owner.modifier:x` works as a key. The crowding `if` tests `has_modifier = migration_crowding` first, so with no modifiers the `owner = { … }` part is never evaluated. Check that before relying on it.)

- [ ] **Step 1:** Write the generator tests and the interpreter test. Run them. Expected: FAIL (the old ladders).
- [ ] **Step 2:** Change the generator, then run `python3 scripts/generators/gen_demographics.py`.
- [ ] **Step 3:** Run `test_gen_demographics`, `test_demographics_registry`, `test_demographics_model`. Expected: PASS, except model bounds that wait for Task 7. Run `.venv/bin/ruff check scripts/generators/gen_demographics.py`.
- [ ] **Step 4: Commit**: "Demographics: the census reads medicine as access x treatment from the modifier types".

**Reviewer (one, after this task):** in the generated values, check min and max order inside the nested blocks. Clamps apply where they stand, so access must be clamped before it multiplies. Check that every `country_*` read goes through `owner.`, that no `state_*` read does, and that the result matches `cause_multipliers` at the floor and the caps.

### Task 7: Calibration

**Files:**
- Modify: `scripts/analysis/demographics_save_inputs.py` (read `institutions` and states' `incorporation`)
- Modify: `scripts/analysis/demographics_harness.py` (`inputs_for` with `mods`; commands `medicine` and `adopters`)
- Modify: the carriers' values (Task 5 files) and `demographics_params.py` constants, to the fit
- Modify: `test_demographics_model.py` bounds; `test_demographics_save_inputs.py`, `test_demographics_harness.py`
- Modify: `docs/testing/demographics-fast-run-2026-10-09.md` (the fit)

**Interfaces:**
- Consumes: `DM.load_carriers`, `DM.totals`, `M.cause_multipliers`, `M.life_table`, `M.group_rates`.
- Produces:
  - `S.SECTIONS["institutions"] = ("institution", "investment", "country")`, and `"incorporation"` in `S.SECTIONS["states"]`.
  - `CountryInputs.institutions: dict` (institution → investment level) and `CountryInputs.incorporated_people: float`.
  - Harness commands `medicine` and `adopters SAVE…`.

Save reader: state records carry `\tincorporation=<0..1>`; it is absent when a state is not incorporated. Count a state as incorporated when it is ≥ 1. Institution records look like `<id>={ institution=institution_health_system investment=1 country=<id> }` inside the top-level `institutions={`. Test both against `test_fixtures/demographics/gb_1836_slice.v3`. If the slice lacks those sections, extend `write_slice` and regenerate the slice from an 1836 save on D:, and say so in the commit.

`inputs_for(c, carriers)`:

```python
def inputs_for(c, carriers=None):
    """Model inputs for a save's country, for its incorporated states: the modifier totals come
    from the game files' carriers (demographics_modifiers) for its techs, laws and institution levels."""
    carriers = DM.load_carriers() if carriers is None else carriers
    mods = DM.totals(carriers, c.techs, c.laws, c.institutions, incorporated=True)
    return M.Inputs(sol=c.sol, literacy=c.literacy, urban_share=c.urban_share, techs=frozenset(c.techs),
                    laws=frozenset(c.laws), institutions=dict(c.institutions), wealth_tfr=c.wealth_tfr, mods=mods)
```

`medicine` prints, for each scenario, e0, IMR, e65 and maternal deaths per 100,000 births against its target band, marked in or out:

| Scenario | Inputs | Targets (§2.4 and history) |
|---|---|---|
| Britain 1836 | SoL 11, literacy 0.35, urban 0.3, medical_degrees, Charitable level 1 | IMR 150–250; e0 35–43; e65 10–14; MMR 500–1000 |
| Britain 1900 | SoL 16, literacy 0.75, urban 0.6, techs of eras 1–3, Private level 2 | IMR 120–170; e0 44–52 |
| West 1950 | the model test's WEST_1950 | IMR 25–55; e0 64–70 |
| West 1990 | the model test's WEST_1990 | IMR ≤ 12; e0 72–80; e65 17–23; MMR ≤ 20 |
| India 1975 | INDIA_1975 | IMR 110–150; e0 48–56 |
| Medicine, no health system | SoL 10, literacy 0.3, all medical techs to era 8, no health law | IMR 70–130 |
| PHI early vs none | SoL 12, literacy 0.4, eras 1–3; PHI at level 3 vs no law | e0 gap ≤ 3 years |

`adopters SAVE…`: for every country with a health law, the median model e0 for its incorporated states, against the median of countries with no health law within ±1.5 SoL and ±0.1 literacy, using today's game-file values. Print one row per law and save, with the count of peers. Read SoL and literacy from the save, never from the census line (Public Health Insurance adds standard of living).

- [ ] **Step 1:** Save-reader tests (institutions, incorporation), then the reader change. Run `test_demographics_save_inputs`. Expected: PASS.
- [ ] **Step 2:** Harness `medicine` and `adopters`, with a smoke test each in `test_demographics_harness.py` (`medicine` exits 0 and prints every scenario label; `adopters` on the fixture slice exits 0).
- [ ] **Step 3: Fit.** Run `medicine`, change the values (carriers, `BASE_ACCESS`, the caps), and rerun until every scenario is in its band or the doc says why not. Then run `adopters` on the fast saves (`/mnt/d/vic3te-data/vic3te-demog-fast-data/saves/`, one every five game years) and on the gate saves. Record both tables, before and after, in the results doc. Keep the infection treatment's order: the 19th-century techs small, antibiotics and vaccines large.
- [ ] **Step 4:** Tighten `TestMortality`'s bounds to the bands that now hold. Add `test_india_1975`, `test_medicine_without_a_health_system` and `test_early_public_health_insurance_gap` from the table. Run the model tests. Expected: PASS.
- [ ] **Step 5:** Regenerate (`gen_demographics.py`, since params constants moved) and run the whole demographics test set. Commit: "Demographics: calibrate medicine against the anchors and the fast run".

### Task 8: The in-game probe for the engine checks

**Files:**
- Modify: `events/te_debug_demog_events.txt` (option `l`)
- Modify: `common/scripted_effects/te_debug_demog_effects.txt` (`te_debug_demog_modifier_reads`)
- Modify: `localization/english/te_events_l_english.yml` (`te_debug_demog.1.l`, `.l.tt`)

Option `l` writes one `TE_DEMOG_MODS` line for the capital and one for the first unincorporated state the country owns, if it has one. Each line shows the state's incorporation, the owner's Health System, Workplace Safety and Consumer Protection levels, every type as the census reads it, and the composed `te_demog_mult_*` values. Use `THIS`-based accessors (scripting_best_practices: `debug_log` reads THIS, not ROOT; no `$PARAM$`). For the plain-number reads, follow the existing `te_debug_demog_*` script values that wrap a read (`te_debug_demog_census_year` and the like). Add the values to `common/script_values/te_debug_demog_values.txt` or wherever those live. A modifier read inside a `debug_log` string is not proven, so wrap each read in a script value.

What the owner checks (into the PR body):
- (a′) `owner.modifier:country_infection_treatment_add` equals the sum of the researched techs' lines.
- (b) `modifier:state_health_care_access_add` in the capital equals the health law's line × the Health System level, and is 0 in the unincorporated state. Workplace Safety and Consumer Protection read the same way.
- (c) hovering a medical tech, a health law and the capital's state modifiers shows the new lines.
- No `Unknown modifier type` lines in `error.log` for the nine types.

- [ ] **Step 1:** Write the option, effect, values and loc.
- [ ] **Step 2:** Run `python3 scripts/analysis/check_localization_files.py`, `python3 loc_render_audit.py --strict`, `python3 script_loc_reference_audit.py --strict`, `python3 orphaned_event_audit.py --strict`, `python3 script_argument_audit.py --strict`, `python3 empty_effect_audit.py --strict` and the registry test. Expected: clean.
- [ ] **Step 3: Commit**: "Demographics: a console probe for the mortality types' reads".

### Task 9: Docs and the player guide

**Files:**
- Modify: `docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md`:
  - status line: owner calls accepted on 2026-10-09; stage 1 in this PR;
  - "What changes" table: the `country_*`/`state_*` names;
  - a short "Ruling: the country/state split" paragraph.
- Modify: `docs/superpowers/specs/2026-10-08-demographics-design.md` §2.4's "Lowered by" column only if it names the tables (it names levers, so probably no change).
- Modify: `docs/guides/python_tools.md` or `docs/testing/demographics-harness-2026-10-08.md`, wherever the harness commands are listed: `medicine` and `adopters`.
- Modify: `docs/player_guide/08-states.md` § Demographics: one or two sentences. Medicine saves lives only as far as health care reaches. Access comes from the health law and its institution's level in incorporated states, plus a base everywhere. The techs' and laws' lines show in their tooltips. Rebuild the PDF: `.venv/bin/python scripts/build_player_guide.py` (from the main checkout's venv), and lint: `python3 scripts/analysis/check_player_guide_style.py --strict`.
- Modify: `docs/testing/demographics-fast-run-2026-10-09.md` (final).

- [ ] **Step 1:** Write the doc changes.
- [ ] **Step 2:** Rebuild the PDF, run `scripts/build_player_guide.py --check` and the style lint. Expected: clean.
- [ ] **Step 3: Commit**: "Demographics docs: stage 1's types, the harness commands, the guide".

### Task 10: Verify, review, draft PR

- [ ] **Step 1:** The whole suite with the dummy env vars (grep the summary). Then:
  - `ruff check .` and `compileall -q .`;
  - `scripts/format_paradox_tabs.py --check` on the changed `.txt`;
  - `organize_loc.py --check` and `check_localization_files.py`;
  - `gen_demographics.py --check`;
  - `scripts/analysis/check_post_load_rosters.py`;
  - every CI audit in its strict mode (CLAUDE.md's list);
  - the f-string scan for 3.11.
- [ ] **Step 2:** One whole-branch reviewer (script and docs), then fix what holds up.
- [ ] **Step 3:** Push and open a **draft** PR against `main`. The body lists:
  - **Summary.**
  - **The country/state split ruling.**
  - **The fit table.**
  - **Data used.** Fast-run saves 1836–1860 and logs to census year 2124 on D:, plus the 1869–1872 generations; the gate-run saves.
  - **Owner calls:**
    - the base access value;
    - `law_medical_augmentation_only` also links the Health System, but carries no access line;
    - the second `modifier` INJECT on `pharmaceuticals`;
    - equal Workplace Safety per level for both labour laws;
    - Consumer Protection on the institution's own `modifier`;
    - GBR, SPA and SPC start with Charitable, so their 1836 census moves.
  - **In-game checks.** Option `l`, before merge.
  - **Player guide line.**
  - **Not merged until the probe passes.**

  Write the body to a file first, then `gh pr create --draft --base main --body-file <file>`.
