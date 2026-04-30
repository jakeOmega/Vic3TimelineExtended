# Tech Tree Balance Review (Eras 6–9)

## Scope and method

Scope: 115 mod-side techs across eras 6–9 (37 + 26 + 24 + 28).

Method: a one-off auditor (`scripts/analysis/tech_balance_audit.py`)
parses each tech's `modifier = { }` block, sums absolute modifier
values, and flags within-era outliers (top 15% sum-abs as STRONG;
zero-modifier techs as WEAK\*).

**Big caveat the metric carries:** sum-abs treats a `+1` flat add the
same as a `+1.0` multiplicative — so a tech with one `country_authority_add = 100`
gets an outsized score next to a tech with `country_innovation_mult = 0.10`.
The auditor surfaces candidates worth inspecting; it does not
resolve balance by itself. Cross-reference against:
- What the tech `unlocks_*` in `unlocking_*` clauses elsewhere.
- Buildings / decrees / PMs / combat-units gated by it
  (`/technology-effects/<tech>` once the mod-state-server is up).
- The actual modifier types in its block (an `_add` of 100 on a
  bureaucracy modifier means very different things to the player than
  100 on `country_authority_add`).

A `WEAK*` flag means **zero modifier-block effects**, which usually
indicates the tech's value is in unlocks (a building, PM, or law),
not in raw modifiers — so WEAK\* is *not* automatically a balance
problem. It just means the audit can't see the value.

---

## Themes

### Theme 1: Modifier inflation across eras

The within-era median sum-abs roughly doubles each era:

| Era | Median sum-abs | Range |
|---|---|---|
| era_6 | 2.50 | 0 – 101.25 |
| era_7 | 10.50 | 0 – 110.10 |
| era_8 | 15.00 | 0 – 101.15 |
| era_9 | 19.27 | 0 – 155.10 |

**Open question (T1):** is this intended power inflation (later techs
should be more valuable) or modifier creep (each new tech feels obliged
to come with bigger numbers)? Vanilla also inflates — comparing
mid-vanilla to late-vanilla median would tell us if mod's curve matches
or exceeds vanilla's.

### Theme 2: A small number of techs dwarf the rest within each era

The top STRONG outlier in each era carries 5×–10× the era's median
modifier value:

- **era_6**: `intergovernmental_organizations` (101.25) and
  `rural_electrification` (100.85) are 40× the era median (2.50).
- **era_7**: `tactical_nuclear_weapons` (110.10) is 10× the median.
- **era_8**: `precision_guided_munitions` (101.15) is 7× the median.
- **era_9**: `network_centric_warfare` (155.10) and
  `unmanned_aerial_vehicles` (151.40) are 8× the median.

These outliers are likely real but they need inspection — many of them
may be using big flat-add modifiers (authority/bureaucracy/construction)
that the metric over-weights. **Open question (T2):** are the topline
ones actually overpowered in play, or are they correctly weighty
"keystone" techs that just look big to the auditor?

### Theme 3: Many era_6/_7 techs have empty modifier blocks

Eight era_6 techs and three era_7 techs have **no modifier block**.
They presumably exist purely to gate buildings / PMs / units / laws:

- **era_6 unlock-only techs:** `isoprene`, `bombing_aircraft`,
  `modern_materials`, `modern_tools`, `motorized_artillery`,
  `semiautomatic_rifle`, `aluminum_mass_production`,
  `modern_management_techniques`.
- **era_7 unlock-only techs:** `advanced_military_aircraft`,
  `pollution_control`, `advanced_submarine_technology`.

This is a legitimate pattern, but it means **roughly 20% of the early
mod tech tree is "research this and then the value shows up elsewhere"**.
That's fine if the unlocks are well-balanced; problematic if unlocks
are unbalanced (and we wouldn't see it from the modifier audit).

**Open question (T3):** are the unlock-only techs mostly utility-tier
(unlock one or two PMs each) or stack-tier (unlock multi-system content
like the wonder buildings or strategic reserve)? The list spans both —
`bombing_aircraft` clearly unlocks a unit, but `modern_management_techniques`
and `modern_materials` might unlock several PMs/decrees each.

### Theme 4: Society category gets the heaviest modifier blocks

Across all four eras, the highest-`modifier_count` techs are mostly
society-category:

- `decolonization` (era_7): 10 modifiers, sum 53.60
- `television_broadcasting` (era_7): 9 modifiers, sum 54.35
- `pop_culture` (era_8): 7 modifiers, sum 55.20

By contrast, military techs tend to have fewer modifiers but higher
per-modifier magnitudes (offense / defense / morale numbers can be
chunky).

**Open question (T4):** intentional? Society techs may legitimately
need to express many different small effects to model "civil rights /
welfare / TV changes everything a little"; military techs naturally
concentrate into a few big buffs. But it's worth confirming this is
deliberate vs. unevenness across authors/eras.

### Theme 5: Era 9 production techs cluster around 100+ sum-abs

Five era_9 techs all hit 100+: `world_wide_web` (105),
`digital_telecommunications` (104.05), `cloud_computing` (103),
`digital_entertainment` (103), `network_centric_warfare` (155.10).

Many of these likely have `country_innovation_mult = 1.0` or similar
flat huge-add bureaucracy modifiers driving the score. **Open
question (T5):** are these genuinely 5× as powerful as a typical
era_9 tech, or are they hitting the metric because of one or two
big-number modifiers in their block?

---

## Outlier table — flagged subset

(Produced by the auditor. Not exhaustive; OK-flagged techs not shown.
Re-run `.venv/bin/python scripts/analysis/tech_balance_audit.py` for
fresh data.)

| id | era | cat | n_mod | sum_abs | flag |
|---|---|---|---|---|---|
| `intergovernmental_organizations` | era_6 | society | 3 | 101.25 | STRONG |
| `rural_electrification` | era_6 | society | 4 | 100.85 | STRONG |
| `public_works_programs` | era_6 | society | 5 | 66.10 | STRONG |
| `nuclear_weapons` | era_6 | military | 6 | 61.90 | STRONG |
| `combined_arms` | era_6 | military | 2 | 51.00 | STRONG |
| `fluorescent_lamps` | era_6 | production | 2 | 30.20 | STRONG |
| `isoprene` | era_6 | production | 0 | 0.00 | WEAK\* |
| `bombing_aircraft` | era_6 | military | 0 | 0.00 | WEAK\* |
| `modern_materials` | era_6 | production | 0 | 0.00 | WEAK\* |
| `modern_tools` | era_6 | production | 0 | 0.00 | WEAK\* |
| `motorized_artillery` | era_6 | military | 0 | 0.00 | WEAK\* |
| `semiautomatic_rifle` | era_6 | military | 0 | 0.00 | WEAK\* |
| `aluminum_mass_production` | era_6 | production | 0 | 0.00 | WEAK\* |
| `modern_management_techniques` | era_6 | society | 0 | 0.00 | WEAK\* |
| `tactical_nuclear_weapons` | era_7 | military | 4 | 110.10 | STRONG |
| `mainframe_computers` | era_7 | production | 6 | 57.05 | STRONG |
| `television_broadcasting` | era_7 | society | 9 | 54.35 | STRONG |
| `decolonization` | era_7 | society | 10 | 53.60 | STRONG |
| `advanced_military_aircraft` | era_7 | military | 0 | 0.00 | WEAK\* |
| `pollution_control` | era_7 | society | 0 | 0.00 | WEAK\* |
| `advanced_submarine_technology` | era_7 | military | 0 | 0.00 | WEAK\* |
| `precision_guided_munitions` | era_8 | military | 5 | 101.15 | STRONG |
| `computer_networks` | era_8 | production | 6 | 57.50 | STRONG |
| `pop_culture` | era_8 | society | 7 | 55.20 | STRONG |
| `personal_computers` | era_8 | production | 3 | 55.00 | STRONG |
| `advanced_materials_armor` | era_8 | military | 0 | 0.00 | WEAK\* |
| `integrated_circuits` | era_8 | production | 0 | 0.00 | WEAK\* |
| `advanced_assembly_lines` | era_8 | production | 0 | 0.00 | WEAK\* |
| `computer_aided_design` | era_8 | production | 0 | 0.00 | WEAK\* |
| `network_centric_warfare` | era_9 | military | 4 | 155.10 | STRONG |
| `unmanned_aerial_vehicles` | era_9 | military | 5 | 151.40 | STRONG |
| `world_wide_web` | era_9 | production | 5 | 105.00 | STRONG |
| `digital_telecommunications` | era_9 | production | 4 | 104.05 | STRONG |
| `cloud_computing` | era_9 | production | 2 | 103.00 | STRONG |
| `digital_entertainment` | era_9 | society | 4 | 103.00 | STRONG |
| `virtual_reality` | era_9 | society | 0 | 0.00 | WEAK\* |

---

## Open questions for the back-and-forth phase

1. **T1 (modifier inflation curve):** is the era_6 → era_9 doubling-per-era
   power curve intended, or accidental?
2. **T2 (top-tier outliers):** are
   `network_centric_warfare`, `unmanned_aerial_vehicles`,
   `tactical_nuclear_weapons`, `intergovernmental_organizations` etc.
   actually too strong in play, or are they the keystone techs they
   appear to be?
3. **T3 (unlock-only techs):** which of the WEAK\* techs are concerning?
   Walk through the 11 WEAK\* techs and confirm their unlocks are
   appropriately weighty.
4. **T4 (society category density):** intentional that society techs
   carry many small modifiers vs military techs concentrating into
   fewer big ones?
5. **T5 (era_9 100+ cluster):** is the cluster of 5 era_9 techs at
   100+ sum-abs justified, or are some inflating from individual
   too-large modifiers?
6. **Cross-era specific concerns:** `decolonization` at 10 modifiers
   stacked is unusual; worth specifically reviewing.
7. **Vanilla baseline:** would adding vanilla era_5 techs to the same
   audit give us a reference point for "is era_6 modifier density
   higher or lower than vanilla's late-game"?

---

## Recommended follow-up workflow

1. Read this doc; pick which themes / specific techs to drill into.
2. For each tech we want to inspect: open `common/technology/technologies/era_X.txt`
   and check both the modifier block AND the surrounding tech's
   place in the unlocking chain.
3. For unlock-only techs: use `mod_state_server /technology-effects/<id>`
   (or grep `unlocking_technologies = { <id> }` across `common/`) to
   see what they actually unlock.
4. Decide which to retune; that's a separate implementation task.
