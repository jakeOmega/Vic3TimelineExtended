# Heir Education

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## Heir Education System (`je_heir_education`)

### Overview
Allows monarchies to shape their heir's education through focus selection and random events. Inspired by EU4/CK3 heir education mechanics. The system uses a monthly probabilistic pulse where active focuses each have a small chance to advance investments, ultimately resolving into ruler aptitude traits, ideology, and interest group alignment when the heir reaches adulthood.

### Architecture
- **Journal Entry:** `je_heir_education` — main controller with monthly pulse, scripted buttons, progress bar
- **Scripted Effects:** `heir_education_effects.txt` — gain effects (intelligence-modified), resolve effect (5-tier), adult initialization, cleanup, IG reactions, non-heir trait assignment
- **Scripted Buttons:** `heir_education_buttons.txt` — 16 toggle buttons (enable/disable pairs for 8 focuses)
- **Progress Bar:** `heir_education_progress_bars.txt` — 0-20 range
- **Static Modifiers:** `heir_education_modifiers.txt` — innovation cost, grace period, event cooldown
- **Events:** `heir_education_events.txt` — 3 events (Promising Pupil, Difficult Student, Foreign Correspondence)
- **Traits:** `ruler_aptitude_traits.txt` — 15 traits (5 tiers × 3 categories: admin, diplomat, commander)
- **Localization:** Spread across `te_concepts_l_english.yml` (traits), `te_journal_entries_l_english.yml` (JE status), `te_events_l_english.yml` (events)

### Key Variables (Country Scope)
| Variable | Purpose |
|---|---|
| `heir_ed_admin` / `diplo` / `military` | Trait investment counters (0+) |
| `heir_ed_ideology` | Ideology direction (positive=progressive, negative=conservative) |
| `heir_ed_ig_radical` / `moderate` / `regressive` | IG alignment counters |
| `heir_ed_total` | Sum of all investments (progress bar value) |
| `heir_ed_intelligence` | Hidden (1-5), affects gain amount per tick |
| `heir_ed_focus_*` | Active focus flags (8 possible) |

### 5-Tier Trait Resolution
Investment levels map to probability distributions across 5 tiers:

| Investment | Terrible | Poor | Average | Skilled | Exceptional |
|---|---|---|---|---|---|
| 0 (none) | 35% | 30% | 25% | 8% | 2% |
| 1-2 (light) | 15% | 25% | 35% | 20% | 5% |
| 3-4 (moderate) | 5% | 15% | 30% | 35% | 15% |
| 5-7 (heavy) | 2% | 5% | 18% | 45% | 30% |
| 8+ (extreme) | 0% | 2% | 10% | 38% | 50% |

### Intelligence System
- Randomly assigned 1-5 (uniform) at JE initialization
- **High (4-5):** 30% chance of double gain (+2) per successful pulse
- **Medium (3):** Standard +1 gain
- **Low (1-2):** 25% chance of wasted opportunity (no gain on success)
- Player sees subtle hint: "quick study" (4-5) or "struggles to grasp concepts" (1-2)
- Effectively creates a 1.5%-4.5% range around the 3% base pulse chance

### Monthly Pulse Mechanics
- **Base chance per focus:** 3% per month (down from original 5%)
- 8 possible focuses: admin/diplo/military (trait), progressive/conservative (ideology), radical/moderate/regressive (IG)
- Each successful pulse calls an intelligence-modified gain effect
- IG reaction modifiers applied on each gain (short-duration decaying)

### Rebel Child Mechanic
- 8% chance at resolution that ideology score inverts (`multiply = -1`)
- Applied BEFORE ideology is mapped to specific ideology types
- Creates strategic tension: focused ideology investment isn't guaranteed

### Adult Heir Initialization
At JE start, heirs older than newborn receive pre-initialized investments:
- **Age 5-9:** 40% chance of +1 per trait
- **Age 10-14:** +1-2 per trait (50/50)
- **Age 15+:** +1-3 per trait (25/50/25) + random ideology lean ±1 + random IG lean

### Non-Educated Characters
`assign_aptitude_traits_effect` (yearly) assigns traits to adult characters who lack them: 20% terrible, 30% poor, 35% average, 12% skilled, 3% exceptional. Generals/admirals (including a ruler or heir who also holds a command) get a better military distribution (5/15/30/35/15). It skips an heir whose country has `je_heir_education` active — that heir's traits come from education.

**Rule gating** (`te_aptitude_traits_enabled` in `misc_triggers.txt` = Heir Education **or** Universal Aptitude Traits):

| Heir Education | Universal | Who has aptitude traits | Monthly `aptitude_traits_cleanup_effect` |
|---|---|---|---|
| off | off | nobody | strips every character |
| on | off | rulers and heirs (roles overlap — a ruler who is also a general qualifies) | strips traits from anyone holding neither role but keeps their `ruler_*_tier` vars; `restore_aptitude_traits_effect` gives the same tiers back the month they return to power (the yearly pass also restores before rolling). Keeping traits for life was rejected: the traits also work outside the throne (`command_modifier`, `interest_group_modifier`), so a voted-out exceptional commander would become the only such general in a world of trait-less ones |
| off | on | every adult (traits can't be shaped by education) | no-op |
| on | on | every adult | no-op |

Only the both-off state also clears the `ruler_*_tier` vars; in the Heir-Education-only state they are the memory that restoration reads. The traits' `possible` blocks carry the same trigger but can't enforce it — `possible` only filters random trait generation and `add_trait` ignores it, which is how rule-off games leaked traits to every ruler after #183 un-wrapped the effect.

### Simulation
`sim_heir_education.py` — Monte Carlo simulation (20,000 runs per scenario) that validates the probability distributions. Key scenarios: newborn with 1-3 focuses, adult heirs, neglected education, intelligence impact analysis. Run this to tune parameters before changing thresholds.

### Design Lessons
- **Simulation-driven tuning:** Write a Python sim BEFORE implementing Paradox script changes. The sim reveals non-obvious distribution outcomes (e.g., that even terrible heirs have a small exceptional chance, creating memorable moments).
- **Intelligence as gain modifier, not chance modifier:** Modifying the gain AMOUNT instead of the pulse CHANCE keeps Paradox script clean (no need for cascading if/else with different random_list weights per intelligence tier). One `random_list = { 3 = { gain_effect } 97 = { } }` per focus regardless of intelligence.
- **Scripted effects for gain encapsulation:** Each focus has a dedicated `heir_ed_gain_X` effect that handles intelligence, variable updates, bar progress, and IG reactions. This keeps the JE monthly pulse compact.
- **`change_variable multiply = -1`** is valid Paradox script for negation (used in rebel child mechanic).
