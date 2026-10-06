# Barracks training methods proposal

Status: implemented prototype for a draft PR against `main`; in-game validation
is required before merge. Baseline: Victoria 3 1.14.5, including the mod's
wartime ammunition changes and combined-arms traits.

## Design

The existing Training Methods group remains a single choice. Add three modern
methods and two alternatives that trade replacement throughput against troop
quality. Preserve vanilla's methods, default, law gates and conscription group.
No new technologies, laws, goods, recurring effects or country modifiers.

Training rate means manpower trained per week, not experience. Each new method
retains vanilla's flat 50 training and adds a per-level rate. Profession ratios
divide each battalion's manpower between soldiers and officers, so they also
work with the mod's smaller late-game battalions. All unit bonuses are unscaled;
goods inputs scale with staffing. The tooltip lists each method's upkeep.

| Method | Unlock | Training/week at level L | Officers | Unit modifiers | Additional goods per fully staffed level/week | Goods cost at base prices |
|---|---|---:|---:|---|---|---:|
| Mobile Warfare Tactics (vanilla reference) | Mobile Armor, era 5 | 50 + 24L | 25% | None | None | £0 |
| Cadre Training | NCO Training, era 5 | 50 + 20L | 30% | +35% army experience gain; −10% morale loss | 1 paper; 0.25 ammunition | £42.5 |
| Accelerated Replacement Training | Wargaming, era 4 | 50 + 36L | 10% | −25% army experience gain; +15% morale loss | 0.5 paper | £15 |
| Combined Arms Instruction | Combined Arms, era 6 | 50 + 28L | 20% | +5% morale recovery | 1 paper; 0.5 ammunition; 0.25 radios | £75 |
| Networked Wargaming | Network Centric Warfare, era 9 | 50 + 34L | 15% | +10% army experience gain; +10% morale recovery | 0.5 radios; 0.5 electronic components; 1 software | £180 |
| Immersive Simulation | Augmented Reality Warfare, era 11 | 50 + 40L | 10% | +20% army experience gain; +15% morale recovery | 1 electronic components; 2 software; 1 services | £310 |

Costs exclude existing battalion upkeep, wages, local prices and supply
multipliers. Software is the existing `digital_assets` good. Ratios sum to 100;
no additional employees are created. Every new method excludes Warrior Caste,
as vanilla's regular training methods do.

At levels 1 / 10 / 100, vanilla's last method trains 74 / 290 / 2,450 manpower
per week. Cadre trains 70 / 250 / 2,050; Accelerated Replacement trains
86 / 410 / 3,650; Combined Arms trains 78 / 330 / 2,850; Networked Wargaming
trains 84 / 390 / 3,450; Immersive Simulation trains 90 / 450 / 4,050.
These are base values before laws, institutions or other training modifiers.

Cadre is the choice for preserving experienced standing troops: its experience
bonus exceeds even the simulator's, but it needs more officers and replaces
casualties slowly. Accelerated Replacement suits severe manpower losses and an
officer shortage; the penalties apply whenever selected, including peacetime.
It is available earlier than the modern methods deliberately. The new methods
do not obsolete the cheap vanilla ones, and industrial training is expensive
at scale: 100 fully staffed Immersive Simulation levels add £31,000 in weekly
goods at base prices. Officer wages and qualifications remain separate costs.

These methods do not check the army's unit mix. Combined Arms Instruction's
name describes its curriculum; the separate combined-arms trait system still
requires an actual mixed formation. Experience gain improves ongoing learning,
not starting experience, and does not immediately grant a veterancy rank.

## Other modifiers considered

- **Experience gain:** implemented. A different benefit from filling vacancies,
  especially for a standing army that retains battalions between wars. Uses
  the army-specific `unit_army_experience_gain_mult`.
- **Morale loss and recovery:** implemented in modest amounts, to distinguish
  mentoring, rushed replacements and rehearsed procedures. These stack with
  laws, traits and mobilization; validate the combined totals in play.
- **Officer share:** implemented. This changes qualifications, wages and the
  number of officer pops, giving manpower organization an economic and social
  consequence beyond a goods bill.
- **Goods demand:** implemented. Paper/live-fire exercises and later software
  provide an upkeep tradeoff. Training inputs remain in peacetime as well as
  war; they are not a second mobilization option.
- **Offense/defense:** deferred. Combat-unit upgrades, experience and combined
  arms already grant these, and direct percentages amplify the mod's very high
  late-game stats. Establish the quality tradeoffs first.
- **Casualty recovery (`unit_recovery_rate_add`):** possible for a future combat
  lifesaver course, but it adds percentage points and overlaps field hospitals,
  medical mobilization options and their caps. Do not confuse casualty survival
  with morale recovery or replacement training.
- **Terrain bonuses and attrition:** leave with the existing formation training
  and logistics mobilization options. A barracks cannot know the terrain where
  its battalions will fight.
- **Political strength, technology spread and war support:** deferred. These are
  country or state effects that could stack across barracks and spill into
  unrelated troops or civilian pops. Officer share already provides a social
  tradeoff without another political multiplier.
- **Separate curriculum PM group:** viable later, to combine a technology tier
  with a quality/speed doctrine. It multiplies combinations, permits bonus
  stacking and needs additional AI balancing. One exclusive group makes this
  first proposal easier to compare and tune.

## Engine and AI limits

The committed vanilla snapshot registers all modifiers used here. Vanilla's
naval-theory PMs place `unit_morale_loss_mult` in
`building_modifiers.unscaled`; this prototype follows that placement for army
quality. Registration and a vanilla precedent do **not** prove that 1.14.5
propagates each modifier from a barracks to its battalions. That is a merge
condition, not a completed test. Do not move them to country/state scope as a
shortcut: that would grant unrelated units bonuses and allow stacking.

The existing group uses `ai_selection = most_productive`. Modern methods retain
the default weight; Cadre has weight 0.5 and Accelerated Replacement weight 0
to discourage the throughput scorer from choosing an emergency doctrine
everywhere. There is no scripted wartime AI switch in this proposal. Verify
that zero weight excludes the option in the engine and that advanced-method
selection respects costs and shortages. If it does not, adjust weights or
defer AI adoption; do not claim context-sensitive AI behavior.

## Before merging

1. Load a pre-change save and a new campaign. All original training choices
   must remain, conscription must be unchanged, and Warrior Caste must exclude
   the five new methods. Check technology unlocks, names, descriptions and icons.
2. In one country, put otherwise identical battalions in two barracks, with one
   formation and no general traits that differ. Change one barracks to Cadre.
   Inspect individual battalion modifiers and morale loss; sample experience
   over several weeks. Only that barracks' troops should get its bonuses.
   Repeat for Networked/Immersive morale recovery and Accelerated penalties.
   If quality modifiers are ignored or shared formation-wide, resolve the
   mechanic and rewrite the descriptions before merge.
3. Compare level 1, 10 and 100 barracks. Training should follow the table before
   other modifiers; troop-quality bonuses must not grow with building level.
   Verify officer ratios across 1,000- and 100-man battalions, hiring and wage
   costs. Changing a method must not create extra battalion manpower capacity.
4. Compare staffed and empty barracks. Only staffed levels should buy the added
   goods. Check shortages, market access, ordinary upkeep and input tooltips.
   Mobilize a subset of the battalions: measure whether basic supplies' +300%
   ammunition also multiplies the PM's exercise ammunition. If so, adjust the
   live-fire amount against the mod's intended wartime demand.
5. Compare otherwise identical battles and experience accumulation under each
   method, especially Professional Army plus Cadre and late-game simulators
   with combined-arms traits and morale mobilization options. Ensure the total
   morale-loss reductions remain useful without making troops immune.
6. Observe AI choices with early/late technology, scarce officers, an expensive
   software market and both peace/war. Confirm Accelerated is excluded by its
   weight and that the AI can afford its selected modern methods.

Offline checks cover merged PM-group wiring, modifier/technology/goods/law
references, staffing ratios, unscaled quality, localization, script formatting
and the player guide. No in-game results are claimed by this draft.
