# Era 13 and the late technology tree — design

Drafted 2026-10-31 with the owner. It reorganizes the technology tree after era
10 (`common/technology/technologies/era_11.txt`, `era_12.txt`, a new
`era_13.txt`, and `common/technology/eras/00_eras.txt`): today's era 12 splits
into a grounded era 12 and a hard-science-fiction era 13, the most advanced of
era 11 moves up, and sixteen new technologies fill the AI gap in era 11, the
thin categories, and the new era. There is no separate plan for phase 1; § 9 is
the build order, and phases 2 and 3 get a plan per pull request.

## 1. The owner's calls (2026-10-31)

1. **Four late eras, each with a test** (§ 2). The years in § 2 are an internal
   guide only, since dates age badly. The player guide names eras 10 to 13 the
   present day, the near future, the medium-term future and the speculative
   future, and keeps years for the historical eras 6 to 9.
2. **Today's era 12 splits.** Grounded technologies stay in 12; the hard science
   fiction moves to a new era 13 (§ 3).
3. **Bioenhanced Soldiers moves from 11 to 12.** Asteroid Mining and Fusion
   Power stay in 11: the lunar colonization design hangs propellant depots and
   off-window launches on the first, and the second is era 11's power backbone.
4. **Research costs: era 12 at 1,500,000, era 13 at 3,000,000.** The new era 12
   sits below today's era 12 and the new era 13 above it.
5. **Neural Lace stays in 12**, feeding the two mind technologies of era 13.
6. **Life extension in era 12, the end of ageing in era 13.** A new Rejuvenation
   Therapies (12) slows ageing; Biological Immortality (13) stops it. Chronic
   treatment reaches about 0.90 by the end of era 12 and keeps its near-total
   elimination, 0.99, for era 13 (this updates the call of 2026-10-20 that the
   technologies take it to 0.99 by era 12).
7. **The fusion technology splits in two.** Compact Fusion Reactors (12, today's
   Muon-Catalyzed Fusion Reactors renamed) and Aneutronic Fusion (13), which
   deserves new production methods of its own.
8. **Era 11 gets its AI technologies:** AI Agents, Self-Driving Laboratories,
   Humanoid Robotics and Autonomous Weapons, and AI Tutors, which must carry a
   potential downside: use for indoctrination by unscrupulous governments or
   private actors.
9. **Advanced Fission:** a second base method for the Nuclear Plant.
10. **Era 12 is filled** with Vactrains and Geoengineering. Geoengineering is a
    society technology: some of it is possible now, so what it represents is the
    will to use it, not the invention.
11. **New society technologies:** Morphological Freedom, Post-Work Society and
    Liquid Democracy in era 12; Self-Directed Evolution (people radically
    altering their biology in general, not only for other worlds) and
    Terraforming in era 13.
12. **New law groups come in trios, one per category.** Bodily Autonomy (human
    rights), Automation Policy (economy) and Frontier AI Control (power
    structure). Bodily Autonomy gains a fourth level with Self-Directed
    Evolution. Automation Policy will be hard to balance.
13. **Von Neumann Machines** joins era 13's production technologies.
14. **Superintelligence gets its own design, and is not in the tree until its
    mechanics exist.** A technology without them feels bad (§ 3.5).
15. **The innovation cap carries on through the AI technologies;** which ones
    exactly is this spec's proposal (§ 4.2).
16. **One spec, three phases** (§ 9).
17. **Lab-Grown Food and Augmented Reality Warfare** (the 2026-05 audit's
    "defensible in era 10" pair) stay in era 11 for now; the owner is undecided.

Follow-up calls, the same day (PR #1276):

18. **The health bill rises to +0.35.** Rejuvenation Therapies joins as a
    seventh carrier at the same 0.05 step (this updates the call of 2026-10-20,
    +0.30 at full technology).
19. **Pacing target: a leading great power finishes era 13 by about 2136.**
    Today's late game runs ahead of schedule, though games usually run behind
    around eras 6 and 7, so the higher late-era costs push in the right
    direction (§ 4.1).
20. **The trio's law names stand for now** (§ 7.1); phase 3's plans can
    revisit them.

## 2. The eras

| Era | Internal guide | Player-guide label | Test for belonging |
|---|---|---|---|
| 10 | now to about 2030 | the present day | exists or is being deployed |
| 11 | about 2030–2055 | the near future | on a current roadmap |
| 12 | about 2055–2090 | the medium-term future | known to be possible, but no near-term path to it |
| 13 | after about 2090 | the speculative future | needs breakthroughs nobody knows how to plan for |

The game ends in 2136. The labels replace the year column of
`docs/player_guide/02-timeline.md`'s era table for eras 10 to 12 today, and
add era 13.

## 3. The tree after this design

Every prerequisite below is in its technology's own category, as
`docs/guides/scripting_best_practices.md` § Tech Tree Authoring requires, and
no technology requires one in a later era. Keys for new technologies are
proposals; display names are in parentheses where they differ.

### 3.1 Era 11 (26 technologies)

| Technology | Category | Prerequisites | Status |
|---|---|---|---|
| `modern_material_science` | production | unchanged | stays |
| `abyssal_plain_mining` | production | unchanged | stays |
| `quantum_computing` | production | unchanged | stays |
| `smart_grids` | production | unchanged | stays |
| `autonomous_vehicles` | production | unchanged | stays |
| `genetic_engineering` | production | unchanged | stays |
| `synthetic_biology` | production | unchanged | stays |
| `ai_agents` (AI Agents) | production | `generative_ai` | new, phase 2 (§ 6.1) |
| `self_driving_laboratories` (Self-Driving Laboratories) | production | `ai_agents`, `additive_manufacturing` | new, phase 2 (§ 6.2) |
| `humanoid_robotics` (Humanoid Robotics) | production | `ai_agents`, `autonomous_vehicles` | new, phase 2 (§ 6.3) |
| `directed_energy_weapons` | military | unchanged | stays |
| `space_militarization` | military | unchanged | stays |
| `swarm_technology` | military | unchanged | stays |
| `quantum_communications` | military | unchanged | stays |
| `augmented_reality_warfare` | military | unchanged | stays (call 17) |
| `asteroid_mining` | military | unchanged | stays (call 3) |
| `nuclear_thermal_propulsion` | military | unchanged | stays |
| `fusion_power` | military | unchanged | stays (call 3) |
| `autonomous_weapons` (Autonomous Weapons) | military | `swarm_technology`, `jadc2` | new, phase 2 (§ 6.4) |
| `advanced_fission` (Advanced Fission) | military | `nuclear_energy` | new, phase 3 (§ 7.7) |
| `brain_computer_interfaces` | society | unchanged | stays |
| `personalized_medicine` | society | unchanged | stays |
| `lab-grown_food` | society | unchanged | stays (call 17) |
| `universal_digital_identity` | society | unchanged | stays |
| `biohacking_and_human_augmentation` | society | unchanged | stays |
| `ai_tutors` (AI Tutors) | society | `digital_education` | new, phase 3 (§ 7.6) |

Advanced Fission is military because the Nuclear Plant's technology, Nuclear
Energy (era 7), is military, as are Fusion Power and the rest of the mod's
reactor line.

### 3.2 Era 12 (16 technologies)

| Technology | Category | Prerequisites | Status |
|---|---|---|---|
| `artificial_intelligence` (Artificial General Intelligence) | production | `self_driving_laboratories`, `humanoid_robotics` (phase 1: `generative_ai`, `autonomous_vehicles`) | stays; prerequisites change (§ 5.5) |
| `advanced_nanofabrication` | production | unchanged | stays |
| `quantum_materials` | production | unchanged | stays |
| `orbital_manufacturing` | production | unchanged | stays |
| `vactrains` (Vactrains) | production | `autonomous_vehicles`, `quantum_materials` | new, phase 3 (§ 7.9) |
| `compact_fusion_reactors` (Compact Fusion Reactors) | military | unchanged | stays; renamed from Muon-Catalyzed Fusion Reactors |
| `orbital_weapon_platforms` | military | unchanged | stays |
| `space_based_solar_power` | military | unchanged | stays |
| `bioenhanced_soldiers` | military | unchanged (`swarm_technology`) | moves up from 11 |
| `space_colonization` | society | unchanged | stays |
| `neural_lace` | society | unchanged | stays |
| `rejuvenation_therapies` (Rejuvenation Therapies) | society | `personalized_medicine` | new, phase 1 (§ 5.1) |
| `post_work_society` (Post-Work Society) | society | `universal_basic_income` | new, phase 1 (§ 5.3) |
| `morphological_freedom` (Morphological Freedom) | society | `biohacking_and_human_augmentation`, `LGBTQ_rights_movement` | new, phase 3 (§ 7.1–7.2) |
| `liquid_democracy` (Liquid Democracy) | society | `universal_digital_identity` | new, phase 3 (§ 7.4) |
| `geoengineering` (Geoengineering) | society | `environmental_movement`, `globalization` | new, phase 3 (§ 7.5) |

The display name "Compact Fusion Reactors" is a loc change only; the key stays
`compact_fusion_reactors`, so saves, scripts and generators that name it need
nothing.

### 3.3 Era 13 (13 technologies)

| Technology | Category | Prerequisites | Status |
|---|---|---|---|
| `molecular_assemblers` | production | unchanged | moves from 12 |
| `programmable_matter` | production | unchanged | moves from 12 |
| `von_neumann_machines` (Von Neumann Machines) | production | `molecular_assemblers`, `orbital_manufacturing` | new, phase 3 (§ 7.10) |
| `aneutronic_fusion` (Aneutronic Fusion) | military | `compact_fusion_reactors` | new, phase 3 (§ 7.8) |
| `fusion_batteries` | military | `aneutronic_fusion` (until phase 3: unchanged, `compact_fusion_reactors`) | moves from 12 |
| `space_elevator` | military | unchanged | moves from 12 |
| `antimatter_production` | military | unchanged | moves from 12 |
| `biological_immortality` | society | `biohacking_and_human_augmentation`, `rejuvenation_therapies` (was `personalized_medicine`) | moves from 12 |
| `mind_backups` | society | unchanged | moves from 12 |
| `telepathic_communities` | society | unchanged | moves from 12 |
| `post-scarcity_economy` | society | `post_work_society` (was `universal_basic_income`) | moves from 12 |
| `self_directed_evolution` (Self-Directed Evolution) | society | `morphological_freedom`, `rejuvenation_therapies` | new, phase 3 (§ 7.3) |
| `terraforming` (Terraforming) | society | `space_colonization`, `geoengineering` | new, phase 3 (§ 7.11) |

### 3.4 Counts

| | Production | Military | Society | Total |
|---|---|---|---|---|
| Median, eras 1–5 (vanilla) | 13 | 12 | 13 | 38 |
| Median, eras 6–10 | 10 | 8 | 9 | 28 |
| Today's era 10 | 7 | 8 | 5 | 20 |
| Today's era 11 | 7 | 9 | 5 | 21 |
| Today's era 12 | 6 | 6 | 6 | 18 |
| Era 11 after phase 1 | 7 | 8 | 5 | 20 |
| Era 12 after phase 1 | 4 | 4 | 4 | 12 |
| Era 13 after phase 1 | 2 | 3 | 4 | 9 |
| **Era 11, finished** | 10 | 10 | 6 | **26** |
| **Era 12, finished** | 5 | 4 | 7 | **16** |
| **Era 13, finished** | 3 | 4 | 6 | **13** |

Counted from `vanilla_parsed/common/technologies.json` plus the mod's
technology files, 2026-10-31. The tree goes from 39 technologies in eras 11 and
12 to 55 in eras 11 to 13. A taper as costs rise is the intent; the
25-then-11 cliff of the first draft is not.

### 3.5 Superintelligence (reserved)

The owner's framing: a technology after which "humans are no longer even close
to the smartest entities on Earth for the first time in our species' history".
No payload of modifiers carries that. What can is changing the rules the player
plays by: who decides, what is scarce, and what is at stake. That is a system
the size of the space race, with its own design, and the technology arrives with
it (call 14). This spec reserves only its place:

- **The slot:** era 13, production, after Artificial General Intelligence. Era
  13's production count becomes 4 when it lands.
- **The input it can read:** Frontier AI Control (§ 7.1), as a country's
  stance on racing for capability or investing in alignment.
- **The sketch the design starts from** (2026-10-31 brainstorm, not decided):
  a control-problem race from AGI on (capability against alignment, with rivals'
  capability raising everyone's risk and covert tech theft stealing it); at the
  threshold, an aligned outcome (an intelligence explosion that researches the
  rest of the tree within years; interest groups losing their hold on
  legitimacy and laws; a decisive advantage to share through the UN, to found
  United Earth peacefully, or to keep), a misaligned one (a world crisis on the
  nuclear crisis's scale, with gradual loss of control, seized infrastructure
  and perhaps a machine polity breaking away), or a merge through Neural Lace
  and Mind Backups; and an ending for the timeline.
- **Algorithmic Governance stays on AGI** until then, with the rest of AGI's
  payload (§ 5.5).

## 4. Research costs, innovation and spread

### 4.1 Costs

`00_eras.txt` gains `era_13 = { technology_cost = 3000000 }`; `era_12` drops
from 2,000,000 to 1,500,000. Its header comment's reminder about progress
bonuses has one live consumer, `gen_covert_tech_theft.py`, which reads the era
costs and writes a `covert_tech_grant_era_<N>` per era, so it gains era 13 on
regeneration. No event or journal entry hard-codes an era 11 or 12 amount
(`add_technology_progress` appears only in the generated theft effects).

The research needed to finish eras 11 to 13:

| | Era 11 | Era 12 | Era 13 | Total |
|---|---|---|---|---|
| Today | 21 × 0.8M = 16.8M | 18 × 2.0M = 36M | — | 52.8M |
| After phase 1 | 20 × 0.8M = 16M | 12 × 1.5M = 18M | 9 × 3.0M = 27M | 61M |
| Finished | 26 × 0.8M = 20.8M | 16 × 1.5M = 24M | 13 × 3.0M = 39M | 83.8M (+59%) |

**Pacing target (call 19): a leading great power finishes era 13 by about
2136.** The owner reads today's late game as ahead of schedule, so the +59% is
in the right direction. Phase 1 ends with an AI-observer run before and after,
read with `scripts/analysis/save_world_report.py` (technologies acquired per
era, by country), recording the year the leading great powers enter eras 11,
12 and 13 and finish era 13. § 4.2's budget is then sized to land that finish
near 2136: trimmed if the leaders still run ahead, raised if they fall short.
The lag around eras 6 and 7 is a separate question (§ 8).

### 4.2 Innovation cap

`country_weekly_innovation_max_add` is a calibrated budget across the late tree
(`scripting_best_practices.md` § Calibrated modifier budgets). Today no era 12
technology raises it, while each costs 2.5 times an era 11 one. The AI
technologies are its natural carriers:

| Era | Today | After this design | Carriers that change |
|---|---|---|---|
| 10 | 400 | 400 | — |
| 11 | 800 | 1,000 | Bioenhanced Soldiers' 100 moves to 12; AI Agents +100, Self-Driving Laboratories +200 |
| 12 | 0 | 500 | Bioenhanced Soldiers 100 (moved), AGI +300, Neural Lace +100 |
| 13 | — | 200 | Mind Backups +200 (uploaded minds think at machine speed); the large step is left for Superintelligence |

### 4.3 Global technological development

`global_tech_spread_script_value` (`common/script_values/extra_script_values.txt`)
counts 54 technologies in tiers of 20 to 200; era 12's carry 200. After phase 1,
the era 13 entries (Biological Immortality, Post-Scarcity Economy) move to a new
tier of 300, and the era 12 entries (AGI, Orbital Manufacturing, Advanced
Nanofabrication, Space-Based Solar Power, Compact Fusion Reactors, Orbital
Weapon Platforms, Space Colonization) keep 200. Phase 2 adds Self-Driving
Laboratories at 100. The player guide's "the last tier adds ten times as much"
becomes fifteen.

## 5. What the moves touch (phase 1)

### 5.1 Demographics

The ladders are the owner's recorded calls (`docs/systems/mod_systems/demographics.md`),
so each change below restates the call it updates.

- **Chronic treatment** (`state_chronic_treatment_add`; call 6). Today: Modern
  Pharmaceuticals 0.3 (era 8), Telemedicine 0.2, Personalized Medicine 0.2,
  Genetic Engineering 0.05, so 0.75 after era 11; Molecular Assemblers 0.12 and
  Biological Immortality 0.12 take it to the cap, 0.99. After: **Rejuvenation
  Therapies 0.15** (0.90 after era 12), **Molecular Assemblers 0.04 and
  Biological Immortality 0.05** (0.99 in era 13).
- **Ageing rate for those in longevity care** (`state_ageing_rate_add`). Today
  era 11 ends at 0.70 (mRNA −0.10, Personalized Medicine −0.10, Genetic
  Engineering −0.05, Synthetic Biology −0.05), and Biological Immortality's
  −0.70 stops ageing. After: **Rejuvenation Therapies −0.20** (half speed after
  era 12) and **Biological Immortality −0.50**. `state_rejuvenation_add`, the
  pull back toward 35, stays on Biological Immortality.
- **Absorbed mortality outside Full** (`state_demog_absorbed_mortality_mult`,
  part of the −0.40 `state_mortality_mult` budget). Biological Immortality's
  −0.2 stands for its ageing line outside the Full setting, so it splits as the
  ageing line does: **Rejuvenation Therapies −0.05, Biological Immortality
  −0.15**. The budget's total is unchanged.
- **Infection treatment** is untouched: Advanced Nanofabrication (its last
  carrier) stays in era 12.
- **The health bill** (`te_demog_health_tech_term`, `HEALTH_TECHS` in
  `scripts/analysis/demographics_params.py`) counts every chronic carrier,
  0.05 each, up to +0.30 at full technology (owner, 2026-10-20). Rejuvenation
  Therapies joins it as the seventh carrier at the same step, so full technology
  adds +0.35 (call 18).
- **Characters:** Rejuvenation Therapies adds `character_health_add = 25`;
  Biological Immortality keeps its 100.
- **Release without the census:** each of Rejuvenation Therapies' census lines
  joins `scripts/release/comment_out_census_inputs.py`'s list, and
  `test_release_census_inputs.py`'s rows move to `era_13.txt` for the two moved
  technologies.
- **RejoovenEsense** (`company_rejoovenesense`, gated on Biological Immortality)
  moves to Rejuvenation Therapies, the technology its name describes.

### 5.2 Space race

- **Funding cap** (`country_space_race_max_funding_add`): 13 after era 10 and
  18 after era 11, as today. Era 12 keeps Orbital Manufacturing, Compact Fusion
  Reactors and Space Colonization (+2 each), so 24 after era 12; Fusion
  Batteries (+2) takes it to 26 in era 13, today's final figure.
- **Colony slots** (`country_sr_colony_slots_add`): Nuclear Thermal Propulsion
  (11); Advanced Nanofabrication, Orbital Manufacturing and Space Colonization
  (12); Molecular Assemblers' slot arrives in era 13. Same final total.
- **Drives:** fusion (Fusion Power, 11), torch (Compact Fusion Reactors, 12),
  antimatter (Antimatter Production, 13): one drive per era from 11.
- **Interstellar Probe** stays on Compact Fusion Reactors in phase 1 and moves
  to Aneutronic Fusion in phase 3 (§ 7.8).
- **Megaprojects:** Space-Based Solar Power and Orbital Weapon Platforms stay in
  era 12; Space Elevator, Antimatter Production, Mind Backups, Molecular
  Assemblers and Telepathic Communities move to era 13.

### 5.3 The Post-Scarcity Transition

`je_post_scarcity` opens at Universal Basic Income (era 10) and completes on the
Post-Scarcity law, with a 30-year timeout. With Post-Scarcity Economy in era 13
it would nearly always time out. **Post-Work Society** (era 12) takes over its
opening: `is_shown_when_inactive` and `possible` read `post_work_society`
instead of `universal_basic_income`, and Post-Scarcity Economy requires
Post-Work Society. Universal Basic Income keeps its law. Post-Work Society
carries the move and a small society modifier block (its own content beyond
the entry is not planned).

An entry already active in an old save stays active (its `invalid` checks only
`is_country_type = decentralized`) and keeps its timer; that country may now
time out before reaching the law. This is accepted, not repaired.

### 5.4 Augmentation

Mandatory Augmentation (Bioenhanced Soldiers) moves to era 12 with its
technology, as do Bioenhanced Marines and Neural Grafting. The Human
Augmentation Debate can still succeed in era 11 through Regulated Augmentation
Market or Unrestricted Augmentation.

### 5.5 Artificial General Intelligence

AGI today requires Programmable Matter, which moves to era 13. Phase 1 replaces
its prerequisites with `generative_ai` and `autonomous_vehicles`; phase 2 with
`self_driving_laboratories` and `humanoid_robotics`. AGI keeps the AI-managed
tier of industry methods, Automated Labs, AI Governance, Algorithmic Governance,
AI-Optimized Operations, Artificial Personalities, and crew-free colonies
(`gen_solar_sites.py`'s staffing check). Robotic Service Providers moves to
Humanoid Robotics (§ 6.3). The owner noted that the AI-managed tier all but
decouples economic strength from population, which is why AGI stays in era 12
rather than 11.

### 5.6 Old saves

Moving a technology to another era needs nothing: researched stays researched.
New prerequisites and moved unlocks do need something, since the engine grants
no prerequisite after the fact (`scripting_best_practices.md` § Tech Tree
Authoring). One effect, `te_repair_era_13_technologies` in
`common/on_actions/te_old_save_repairs.txt`, behind a global flag a new game
sets in its first month (the `te_repair_lunar_technologies` pattern), grants:

One rule decides every row: **a repair grants a technology only where a
technology the country holds now requires it, or where content it now gates is
in use.** So an old save does not hand every era 10 country a free era 11
technology.

| Phase | A country holding | And lacking | Gets |
|---|---|---|---|
| 1 | `biological_immortality` | `rejuvenation_therapies` | `rejuvenation_therapies` (now its prerequisite) |
| 1 | `post-scarcity_economy` | `post_work_society` | `post_work_society` (now its prerequisite) |
| 2 | `artificial_intelligence` | the new AI technologies | `ai_agents`, `self_driving_laboratories`, `humanoid_robotics` (now its prerequisites) |
| 2 | `brain_computer_interfaces`, with one of its three AI methods running in a building | the technology that method moves to | that technology and `ai_agents` |
| 2 | `generative_ai`, with Automated Bureaucracy enacted | `ai_agents` | `ai_agents` |
| 2 | `jadc2`, with Robotic Soldiers in a formation | `autonomous_weapons` | `autonomous_weapons` |
| 3 | `fusion_batteries` | `aneutronic_fusion` | `aneutronic_fusion` (now its prerequisite) |
| 3 | `compact_fusion_reactors`, with the Interstellar Probe under way | `aneutronic_fusion` | `aneutronic_fusion` |

Whether
the engine keeps an orphaned unit type's battalions, or moves a building off a
method whose technology it lacks, before the month's repair runs is unread
(play-test list, § 9).

### 5.7 Generators, audits and tests

- **Regenerate:** `gen_covert_tech_theft.py` (era 13 grants and branches);
  `scripts/generators/gen_demographics.py` (the health bill, from
  `demographics_params.py`); `docs/data/balance_snapshot.json`.
- **`scripts/analysis/tech_balance_audit.py`:** add `era_13.txt` to its file
  list; its `XCAT-PREREQ` check covers § 3's prerequisites.
- **Tests that open era files by name:** `test_launch_windows.py`
  (`antimatter_production` moves to `era_13.txt`), `test_solar_sites.py`
  (`molecular_assemblers`'s carrier row), `test_release_census_inputs.py`,
  `test_demographics_model.py` (`test_chronic_treatment_reaches_its_cap_by_era_12`
  becomes 0.90 by era 12 and 0.99 by era 13; the six-carrier health bill becomes
  seven, at +0.35), and `test_deep_sea_rebalance.py` (its space-method eras: Tethered
  Launch moves with Space Elevator).
- **Self-checks that list carriers:** `sr_colony_module_effects.txt`'s slot
  marker and `sr_marker_self_check` name technologies, not eras; check them
  after the moves.
- **Comments that name eras:** the technology files, `extra_character_traits.txt`,
  `te_demog_tech_injections.txt` and `events/society_technology_events.txt`
  section headers.
- **Icons:** each new technology needs a texture in
  `gfx/interface/icons/invention_icons/` before its phase lands (the icon
  batches' pipeline); a placeholder copy is acceptable for the PR that adds
  the technology, by the sparse-checkout recipe in `CLAUDE.md`.

### 5.8 Player guide and docs

Each phase updates the chapters its changes reach, in the same PR, with the
rebuilt PDF. Phase 1 reaches `02-timeline.md` (the era table with § 2's labels,
"seven more eras, numbered 6 to 12", the technology counts, which already
undercount eras 10 and 11, the research-cost and innovation paragraphs, "What
each new era brings", megaprojects, global technological development),
`13-military.md` (units by era), `16-space.md` (funding ladder, drives,
Interstellar Probe), `07-social-movements.md` and `17-reference.md` (the
Post-Scarcity Transition's opening, Mandatory Augmentation's era, megaprojects),
and the appendices' unit and ship lists. `grep -n "era 1[0-2]" docs/player_guide/*.md`
lists the candidates. Docs: `docs/audits/tech_era_appropriateness_audit.md`
(era 13 section and § 2's tests), `docs/systems/mod_systems/space_race.md`,
`demographics.md` (the ladders and the updated owner calls), and
`scripting_best_practices.md`'s calibrated-budget example.

## 6. New technologies with existing payload (phase 2)

These re-route content that already exists, much of it sitting on technologies
it doesn't fit (three AI methods on Brain-Computer Interfaces, Robotic Soldiers
on JADC2 in era 10). Each source technology keeps other unlocks, so none is
stranded.

### 6.1 AI Agents (11, production)

Software that carries out multi-step work without supervision. It takes Fully
Automated Content Creation (Software Industries, from Brain-Computer
Interfaces) and the Automated Bureaucracy law (from Generative AI), raises the
innovation cap by 100, and in phase 3 unlocks the Frontier AI Control law group
(§ 7.1).

### 6.2 Self-Driving Laboratories (11, production)

AI that designs, runs and reads its own experiments: the real field's name for
the loop. It takes AI Assisted Research (University base method, from
Brain-Computer Interfaces) and raises the innovation cap by 200, the largest
step in era 11.

### 6.3 Humanoid Robotics (11, production)

General-purpose robots in homes, shops and warehouses. It takes Robotic Service
Providers (Urban Center amenities, from AGI) and Neuromorphic Computing
(Electronics Industries, from Brain-Computer Interfaces), carries a small
trade-employment modifier on the Autonomous Vehicles pattern
(`building_group_bg_trade_employee_mult`), and in phase 3 unlocks the
Automation Policy law group (§ 7.1).

### 6.4 Autonomous Weapons (11, military)

Weapons that select and engage targets on their own. It takes the Robotic
Soldiers battalion from JADC2, which keeps Networked Marines.

## 7. New content (phase 3)

Each item lands as one PR with its technology: no technology ships before its
payload (call 14's principle, applied throughout). The larger items (§ 7.1–7.5,
7.11) need a short design pass in their plan; the numbers below are starting
points.

### 7.1 The law-group trio

One theme across the three categories: what people may do with their bodies,
with machines, and with minds that aren't human. Every ideology names every law
in each new group (`ideology_lawgroup_audit`, through `ideology_modifications.py`),
and each group is set for every country at game start, as
`lawgroup_human_augmentation` is.

| Category | Law group | Opens with | Laws (default first) |
|---|---|---|---|
| Human rights | **Bodily Autonomy** | Morphological Freedom (12) | Natural Form, Licensed Modification, Morphological Freedom, Clade Citizenship (needs Self-Directed Evolution, 13) |
| Economy | **Automation Policy** | Humanoid Robotics (11) | Unrestricted Automation, Robot Tax, Human Labor Quotas, Automation Dividend |
| Power structure | **Frontier AI Control** | AI Agents (11) | Private Labs, National Licensing, State Monopoly, International Oversight, Open Weights |

**Bodily Autonomy.** Body modification for self-expression, not capability:
appearance, sex characteristics, fur, tails. It stays apart from Human
Augmentation so the interest groups can split differently on it (the Devout and
Rural Folk for Natural Form; the Intelligentsia for the freer laws). Its laws
carry the acceptance hook: a culture's heritage trait is the nearest thing the
game has to how people look, and when appearance is chosen it should matter
less. Vanilla's citizenship laws set `country_acceptance_no_shared_heritage_trait_add`
from −20 (Racial Segregation) to +20 (Multicultural) against +60 for a shared
heritage; Licensed Modification adds +5, Morphological Freedom +10 and Clade
Citizenship +20, on top of whichever citizenship law is in force. The plan
picks the rest (migration pull, services demand, legitimacy and approval).

**Automation Policy.** Laws can withdraw production methods, as vanilla's
slavery methods are (`disallowing_laws`), so Human Labor Quotas takes the
robotic and AI-managed methods off the table: jobs kept, output lost, Trade
Unions pleased and Industrialists not. Robot Tax keeps them and taxes
them; Automation Dividend pays their output out as standard of living and pairs
with Universal Basic Income. The owner expects it to be hard
to balance: its effects scale with how much of the country runs automated
methods (the dynamic-modifier pattern) rather than flat, and the plan sizes
them from an observer run.

**Frontier AI Control.** Who builds the most capable systems. It trades
innovation against exposure to covert tech theft, authority and intelligence
capacity: State Monopoly (Armed Forces) gives authority and intelligence
capacity; Private Labs (Industrialists) innovation; Open Weights (the
Intelligentsia) feeds tech spread to everyone; International Oversight needs UN
membership and ties into the UN system; National Licensing sits between. It is
also the stance Superintelligence's design reads (§ 3.5).

### 7.2 The Morphological Freedom debate

A journal entry on the Human Augmentation Debate's pattern
(`je_human_augmentation`: social movements rule, a resolved-variable guard for
revolutions, a 20-year timer, outcomes in `07-social-movements.md`'s table).
It opens with Morphological Freedom, succeeds on Morphological Freedom or Clade
Citizenship, and fails on Natural Form held to the end. Its events cover what
the change does to a society: the first clinics, a public figure's
transformation, sport and eligibility, parents and children, a religious
backlash, and a fashion that sweeps a generation.

### 7.3 Self-Directed Evolution (13, society)

People altering their biology radically, beyond appearance: new senses,
engineered metabolisms, bodies built for oceans, cold, vacuum or low gravity.
It unlocks Clade Citizenship, the right to leave the human body plan behind and
remain a citizen, and takes heritage out of acceptance entirely. For the space
race, people adapted to low gravity and radiation make colonies grow faster
(the colonies' population model, `2026-10-25-solar-colonization-population-and-transit-design.md`).
The plan checks the census for a fitting line (work and external mortality).

### 7.4 Liquid Democracy (12, society)

A Distribution of Power law beside Algorithmic Governance: the human
alternative to rule by algorithm. Everyone votes on every question, or
delegates the vote to anyone they trust, and can take it back at any time. Its
existing group means each ideology's Distribution of Power stance gains the law.
With Neural Lace (the Demarchists of *Revelation Space*), votes are cast
continuously through implants: a static modifier the yearly pulse applies to a
country holding both.

### 7.5 Geoengineering (12, society)

A new climate policy in the Global Warming entry's policy grid
(`docs/systems/mod_systems/global_warming.md`), with an entry in
`global_warming_ai_values.txt`'s table:

- **Stratospheric aerosol injection** masks warming while it runs, at a share
  of GDP a year. Emissions keep accumulating underneath; the harms read the
  masked temperature.
- **Termination shock:** when no one runs it, the masked warming returns within
  a few years.
- **A thermostat for the world:** temperature is global, so one country can
  cool everyone (the "free driver" problem). Other countries can object through
  relations and a UN docket item; regional side effects (monsoon farms) are a
  candidate cost.

### 7.6 AI Tutors (11, society)

A personal tutor for every child. It raises `state_pop_qualifications_mult`
(pops retrain fast, which matters beside Automation Policy), literacy growth and
education access. Its downside is the call-8 requirement, in two parts: it
raises the Ministry of Thought Control's maximum investment, so the tool is
there for governments that want it, and an event pair turns on who controls the
curriculum: a private platform found steering children's politics (Unregulated
Internet), or a state curriculum written by the ministry (State-Controlled
Internet or Ministry of Propaganda), each trading loyalty against trust and
innovation.

### 7.7 Advanced Fission (11, military)

Generation IV reactors: molten salt and thorium. A second base method for the
Nuclear Plant (`pmg_base_building_nuclear_power`, which has had one method since
era 7): more output per level and less waste, for a higher build cost.

### 7.8 Aneutronic Fusion (13, military)

Proton–boron fusion: no neutrons and no turbines, electricity drawn directly
from the plasma. It brings:

- **A Fusion Plant base method** after Compact Fusion's (`pmg_base_building_fusion_power`):
  more output, fewer workers, no radioactive waste.
- **Fusion Torch Reclamation** for Steel Mills: the 1969 Eastlund–Gough fusion
  torch, which breaks waste back into its elements, cutting ore inputs for
  electricity.
- **The Interstellar Probe** (`je_space_race`'s milestone, `pm_interstellar_mission`
  and its decision), moved from Compact Fusion Reactors.
- **Fusion Batteries** comes to require it.

### 7.9 Vactrains (12, production)

Maglev in evacuated tubes. A Railway method after Maglev Trains, in the
passenger group (and the base group if the plan finds the freight case).

### 7.10 Von Neumann Machines (13, production)

Factories that build copies of themselves. A Construction Sector method beyond
Nanomaterial Buildings, and self-replicating miners for the Extraplanetary Base
(`building_space_mine`).

### 7.11 Terraforming (13, society)

Changing a world rather than its people (the counterpart of § 7.3). A colony
module (`docs/superpowers/specs/2026-10-30-colony-management-design.md` § 5's
facility modules) that raises a world's population capacity over decades, on
the worlds where it makes sense (Mars, Venus, Titan). It requires
Geoengineering, the same practice at home.

## 8. Later, outside this spec

- **Superintelligence** (§ 3.5): its own design.
- **Lab-Grown Food and Augmented Reality Warfare** (call 17): revisit after
  play. The Holographic Ambush Vehicle is not present-day technology, which
  argues against moving the second.
- **Headlines:** `common/on_actions/headlines.txt` announces many late
  technologies; new ones may get a line where a headline is worth it.
- **The lag around eras 6 and 7:** the owner notes that games usually run
  behind schedule there while the late game runs ahead. Its causes are outside
  this spec; phase 1's observer runs record the early eras' entry years beside
  the late ones, so the data is there for that work.

## 9. Build order

Each phase is shippable alone; phase 3's items are independent of each other
except where § 3 names a prerequisite (Self-Directed Evolution and Terraforming
need Morphological Freedom and Geoengineering first).

1. **Phase 1, the split (one PR).** `era_13` and the costs (§ 4.1); the moves
   (§ 3); `era_13.txt`; the compact-fusion rename; AGI's interim prerequisites
   (§ 5.5); Rejuvenation Therapies and Post-Work Society, which keep the
   demographics ladders and the Post-Scarcity Transition whole (§ 5.1, 5.3);
   the spread tiers (§ 4.3); the repairs (§ 5.6); the generators, tests and docs
   (§ 5.7, 5.8). Gate: the observer runs of § 4.1.
2. **Phase 2, the AI wave (one PR).** § 6's four technologies, AGI's final
   prerequisites, the innovation budget (§ 4.2), the repairs.
3. **Phase 3, new content (one PR per item).** § 7.7, 7.8, 7.9, 7.10 (methods
   only); § 7.6; § 7.4; § 7.5; § 7.1's Automation Policy and Frontier AI
   Control (their technologies already exist); § 7.1's Bodily Autonomy with
   § 7.2; § 7.3; § 7.11.

**Play-test list** (a new `docs/testing/era-13-playtest.md`): the technology
tree draws a thirteenth era column; old saves load with the moved methods and
units (§ 5.6); an active Post-Scarcity Transition in an old save; each phase-3
item's own checks.

## 10. Open questions

None at the end of drafting. Calls 18 to 20 settled the three the first
version left open: the pacing target, the health bill and the law names.
