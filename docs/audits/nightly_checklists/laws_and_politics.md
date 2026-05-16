# Nightly audit — laws, IGs, parties, movements, ideologies, government types

For each selected file in `common/laws/`, `common/law_groups/`, `common/interest_groups/`, `common/interest_group_traits/`, `common/political_movements/`, `common/political_movement_pop_support/`, `common/parties/`, `common/ideologies/`, `common/government_types/`.

## Checks

- **Explicit IG stances on new laws.** New laws declare `approve` / `strongly_approve` / `disapprove` / `strongly_disapprove` for every IG that has an opinion on the law-group's domain. Missing stances default to neutral and quietly distort enactment AI. (`docs/vanilla/vanilla_politics_reference.md`)
- **Movement / demand / pop_support consistency.** New political movements have `triggers`, `demands`, and `pop_support` that map to the laws they actually target. A movement whose demands don't reference any extant law is broken. (`docs/vanilla/vanilla_politics_reference.md`)
- **Declarative modifier routing.** Where a law adds modifiers the player will want a breakdown for (SoL, throughput, prestige, legitimacy, …), the modifiers route through a registered `modifier_type_definition` so `GetValueWithBreakdownFor` renders the source list in tooltips. (memory: declarative modifier transparency)
- **Power bloc principle tiers state absolute values.** Each tier's modifier block is the complete final list when selected — tiers don't stack. Restate absolute values, not deltas from the prior tier. (memory: principle tiers don't stack)
- **Wide-gate, AI-weighted diplomacy / political mechanics.** For new diplomatic or political plays / pacts, prefer continuous AI tilt (every score line tagged with `desc =`) plus explicit blockers, over hard ideology locks. Flag hard locks where a soft gate would work. (memory: diplomacy widegate)
- **Ideology stance accuracy.** Stance triggers reference the right ideology id — `ideology_market_liberal` and `ideology_liberal` are both real and differ in stances. Spot-check any stance/ideology reference against `docs/engine/laws.txt` or vanilla files. (memory: subagent claim verification)
- **IG approval bumps match prior stance.** Same rule as events: when an IG's approval is bumped by event outcome or law passage, the bump matches the IG's prior stance. (`docs/vanilla/vanilla_politics_reference.md`)
- **Anchor rebalance numbers to vanilla strength.** When broadening a gate, don't also lower the floor without justification — check vanilla's power level first. (memory: anchor rebalance to vanilla)
