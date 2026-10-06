# Barracks training methods proposal

Status: implemented prototype for a draft PR against `main`. All new methods
unlock in era 6 or later. Baseline: Victoria 3 1.14.5, including the mod's
wartime ammunition changes and combined-arms traits.

## Design

The existing Training Methods group remains a single choice. Add three modern
methods and two alternatives that trade training throughput against officer
requirements and supply costs. Preserve vanilla's methods, default, law gates
and conscription group. No new technologies, laws, goods, recurring effects or
country modifiers. Cadre also gives a small staffing-scaled state qualification
benefit. No `unit_` modifiers are implemented.

Training rate means manpower trained per week, not experience. Each new method
retains vanilla's flat 50 training and adds a per-level rate. Profession ratios
divide each battalion's manpower between soldiers and officers, so they also
work with the mod's smaller late-game battalions. Goods inputs scale with
staffing. The tooltip lists each method's upkeep.

| Method | Unlock | Training/week at level L | Officers | Additional goods per fully staffed level/week | Goods cost at base prices |
|---|---|---:|---:|---|---:|
| Mobile Warfare Tactics (vanilla reference) | Mobile Armor, era 5 | 50 + 24L | 25% | None | £0 |
| Cadre Training | Combined Arms, era 6 | 50 + 30L | 30% | 1 paper; 0.25 radios | £50 |
| Accelerated Replacement Training | Modern Management Techniques, era 6 | 50 + 36L | 35% | 2 paper; 1 ammunition; 0.5 radios | £150 |
| Combined Arms Instruction | Combined Arms, era 6 | 50 + 28L | 20% | 1 paper; 0.5 ammunition; 0.25 radios | £75 |
| Networked Wargaming | Network Centric Warfare, era 9 | 50 + 34L | 15% | 0.5 radios; 0.5 electronic components; 1 software | £180 |
| Immersive Simulation | Augmented Reality Warfare, era 11 | 50 + 40L | 10% | 1 electronic components; 2 software; 1 services | £310 |

Costs exclude existing battalion upkeep, wages, local prices and supply
multipliers. Software is the existing `digital_assets` good. Ratios sum to 100;
no additional employees are created. Every new method excludes Warrior Caste,
as vanilla's regular training methods do. The added methods do not change
experience, morale, offense or defense.

At levels 1 / 10 / 100, vanilla's last method trains 74 / 290 / 2,450 manpower
per week. Cadre trains 80 / 350 / 3,050; Accelerated Replacement trains
86 / 410 / 3,650; Combined Arms trains 78 / 330 / 2,850; Networked Wargaming
trains 84 / 390 / 3,450; Immersive Simulation trains 90 / 450 / 4,050.
These are base values before laws, institutions or other training modifiers.

Cadre uses instructors instead of expensive exercise equipment: it trains
faster than Combined Arms Instruction with a smaller goods bill, but needs
more officers. Its instructor schools also improve qualifications for the
state's civilian population. Accelerated Replacement trains faster still, with the largest
officer share and a larger exercise bill. Neither is a cheap, universally
superior speed upgrade. Later computer-based methods reduce officer demand
while increasing hardware and software demand. None dominates every other
new method on training speed, officer share and base-price goods costs.

The new methods leave the cheap vanilla ones available. At 100 fully staffed
levels, Immersive Simulation adds £31,000 in weekly goods at base prices.
Officer wages and qualifications remain separate costs. These choices give
players alternatives when equipment, money or qualified officers are scarce.

These methods do not check the army's unit mix. Combined Arms Instruction's
name describes its curriculum; the separate combined-arms trait system still
requires an actual mixed formation.

## State and other local effects

Cadre Training implements `state_pop_qualifications_mult = 0.001` through
`state_modifiers.workforce_scaled`. That is **+0.1% qualification gain per fully
staffed level**: +1% at 10 levels, +10% at 100 and +100% at 1,000. Empty levels
contribute nothing under the normal PM staffing scaling. This is proportional,
not capped; compare large late-game states during playtesting. At 100 levels,
the boost equals one fully staffed Scholastic Education university level
(vanilla uses 0.1 per university level). This is deliberately a much smaller
spillover per level than a university's.

The benefit reaches all professions in that state, not just officers or current
barracks employees. It improves the qualification pipeline; it does not remove
wealth, literacy or acceptance requirements or guarantee that qualified pops
will accept a military job. The design represents instructor schools adding
skills to a garrison town's labor pool. The officer-heavy staffing remains its
cost. A method switch changes the local benefit; it does not grant a permanent
education reward.

These other registered hooks are candidates, not additional scripted effects
in this PR:

| Candidate | Possible curriculum | Benefit and limitation |
|---|---|---|
| `state_education_access_add` | Technical-service schooling, era 7+ | Slow literacy benefit for civilian pops too. Size in percentage points and use tiny staffing-scaled grants or a separate bounded calculation; barracks can number in the hundreds. |
| `building_officers_job_attractiveness_mult` | Officer career development, era 6+ | Improves the barracks' offer to already-qualified officers. Targets hiring/wage competitiveness, not creating qualifications; test alongside military wages. |
| `building_soldiers_job_attractiveness_mult` | Professional service curriculum, era 6+ | Recruitment/retention channel for the barracks' soldiers, without a claim about battlefield performance. |
| `state_officers_mortality_mult` | Occupational safety/medical training, era 7+ | Alters officer-pop mortality in the whole state. It is not combat casualty survival, so do not advertise it as a field-hospital substitute. |

No registered officer-only qualification modifier was found in the current
catalog. Do not invent `state_officers_qualifications_mult`. Broad qualifications
are an explicit civilian spillover. Education access is deferred here to avoid
turning a large garrison into a replacement for public education. Political
strength and suppression would similarly affect local civilians and need their
own ideological and balance rationale.

## What we know about unit modifiers

We do **not** have confirmation that 1.14.5 passes a barracks'
`building_modifiers` containing `unit_` fields to its battalions. A valid
modifier name proves registration, not that a building is a working source.

The original prototype relied on vanilla's naval-theory PM definitions, which
place `unit_morale_loss_mult` in `building_modifiers.unscaled`. That is weak
current-version evidence: `pmg_naval_theory` remains defined in the committed
1.14.5 snapshot, but no vanilla building mounts it. The current barracks
training methods contain training-rate modifiers and profession ratios, with
no unit modifiers. Sources: `vanilla_parsed/common/buildings.json`,
`pm_groups.json` and `pms.json`.

Paradox's [patch 1.1 developer diary](https://www.paradoxinteractive.com/games/victoria-3/news/victoria-3-dev-diary-67-patch-1-1-pt3)
describes combat effects from the old military-building PMs. This establishes
historical behavior, not present behavior after the military-system changes.
The engine's modifier documentation describes flow through a modifier graph;
it does not document a current building-to-battalion link.

Consequently, unit effects have been removed from the script and its player
text. To reconsider them, use a separate diagnostic PM on one of two otherwise
identical barracks. Check its own battalions' effective modifier values and
actual morale/experience changes, in and out of battle, while the other
barracks supplies a control. A PM tooltip alone is not sufficient. Verify the
specific modifier; do not assume that one working unit field proves all others.
Do not replace an unverified local effect with a country/state grant, which
would affect unrelated troops and could stack across barracks.

## Other modifiers considered

- **State qualifications:** implemented for Cadre, with a small per-staffed-level
  grant using the same state hook as vanilla universities. It has a civilian
  spillover and no direct troop-stat effect.
- **Officer share:** implemented. This changes qualifications, wages and the
  number of officer pops, giving manpower organization an economic and social
  consequence beyond a goods bill.
- **Goods demand:** implemented. Manuals, live-fire exercises and later software
  provide an upkeep tradeoff, including in peacetime.
- **Experience gain and morale loss/recovery:** deferred until a current-version
  runtime test confirms barracks propagation. These remain interesting ways to
  distinguish troop quality from replacement speed, but are not promised here.
- **Offense/defense:** deferred for the same engine uncertainty, and because
  unit upgrades, veterancy and combined arms already grant these effects.
- **Casualty recovery (`unit_recovery_rate_add`):** requires the same runtime
  verification, plus checking overlap and caps with medical mobilization.
  Casualty survival differs from morale recovery and replacement training.
- **Terrain bonuses and attrition:** leave with the existing formation training
  and logistics mobilization options. A barracks cannot know where its troops
  will fight.
- **Political strength, technology spread and war support:** deferred. Country
  or state effects could stack across barracks and spill into unrelated troops
  or civilians. The small local qualification benefit and officer share provide
  an explicit social tradeoff without national political bonuses.
- **Separate curriculum PM group:** viable later, to combine a technology tier
  with an instructor/equipment choice. It multiplies combinations and needs
  additional AI balancing. One exclusive group keeps this proposal manageable.

## AI and playtest

The existing group uses `ai_selection = most_productive`. Modern methods retain
the default weight; Cadre has weight 0.5 and Accelerated Replacement weight 0
for conservative AI adoption of instructor-intensive methods. There is no
scripted wartime switch. Verify what these weights do in the engine and how
selection responds to shortages, costs and officer qualifications.

Before merging:

1. Load a pre-change save and a new campaign. All original training choices
   must remain, conscription must be unchanged, Warrior Caste must exclude the
   five new methods, and no new method may unlock before era 6. Check names,
   descriptions, icons and technology unlocks.
2. Compare level 1, 10 and 100 barracks. Training should follow the table before
   other modifiers. Verify officer ratios with 1,000- and 100-man battalions,
   hiring and wage costs. Method changes must not create extra manpower capacity.
3. Check the state qualification tooltip at 10 and 100 staffed Cadre levels
   (+1% and +10%) and with empty barracks (no staffing contribution). Verify
   that the bonus stays in the hosting state, benefits civilian qualifications,
   falls with staffing and disappears when the method changes. Check late-game
   concentrations at 1,000 levels for excessive education spillover.
4. Compare staffed and empty barracks. Only staffed levels should buy the added
   goods. Check shortages, market access, ordinary upkeep and input tooltips.
   Mobilize a subset of battalions: measure whether basic supplies' +300%
   ammunition also multiplies the PM's exercise ammunition. If so, tune the
   live-fire amount against the intended wartime demand.
5. Observe AI choices with scarce officers, expensive software and both
   peace/war. Confirm Accelerated is excluded by its weight and that the AI can
   afford its selected methods.

Offline checks cover PM-group wiring, references, era gates, staffing ratios,
staffing-scaled state qualifications, absence of unverified unit effects,
localization, formatting and the player guide. No in-game results are claimed by this draft.
