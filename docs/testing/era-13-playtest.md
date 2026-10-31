# Era 13 play-test checklist

What the next play-test of the era 13 technology tree should look at
(`docs/superpowers/specs/2026-10-31-era-13-technology-tree-design.md`). In-game
checks don't gate the merge (CLAUDE.md, "In-game checks"); this list collects
what only the game can show. Phases 1 (the split) and 2 (the AI wave) are in.
Phase 3's items add their own checks here as they land.

Grep `debug.log` for `TE_ERA13_TECH_REPAIR` after loading an old save.

## Phase 1: the split

1. **The tree.** Open the technology panel in a new game. Each of the three
   trees draws a thirteenth era column after era 12. Era 12 lists 12
   technologies and era 13 lists 9. No technology sits left of a prerequisite,
   and no arrow crosses back an era.
2. **Costs.** An era 12 technology shows 1,500,000 research before modifiers,
   and an era 13 one 3,000,000. The tree's "researching ahead" surcharge still
   applies across eras 12 and 13.
3. **The new technologies.**
   - Rejuvenation Therapies (after Personalized Medicine) lists chronic
     treatment, ageing rate, its share of the absorbed deaths line and
     character health in its tooltip.
   - Post-Work Society (after Universal Basic Income) lists its three
     modifiers.
   - Both draw a borrowed icon until the icon pipeline paints theirs:
     Biological Immortality's hourglass, and Universal Basic Income's.
4. **The rename.** Compact Fusion Reactors reads that way in the tree, in the
   Fusion Plant's Compact Fusion Power method, in the launch-window footers
   and in the drives concept. No "Muon-Catalyzed" is left in English; German
   and Spanish show their new names.
5. **The Post-Scarcity Transition.** In a new game the entry stays hidden at
   Universal Basic Income and appears with Post-Work Society. Its statuses
   still name Post-Scarcity Economy as the next technology.
6. **RejoovenEsense** can be formed with Rejuvenation Therapies (era 12)
   rather than Biological Immortality.
7. **Old saves.**
   - Load a save from before this change in which a country holds
     Biological Immortality or Post-Scarcity Economy. In the first month it is
     given Rejuvenation Therapies or Post-Work Society (a
     `TE_ERA13_TECH_REPAIR` line each), and nothing else.
   - A country holding only era 12 technologies gets nothing.
   - An active Post-Scarcity Transition stays active and keeps its timer
     (spec § 5.3: accepted, not repaired).
8. **Global Technological Development.** With a great power holding
   Biological Immortality, the modifier's tooltip rises by 300 for it, not
   200.
9. **Covert tech theft.** A theft of an era 13 technology grants era 13's
   amounts (150,000 to 600,000 by phase and priority), and an era 12 one era
   12's new amounts.

## Phase 2: the AI wave

1. **The tree.** Era 11 lists 24 technologies. AI Agents follows Generative
   AI. Self-Driving Laboratories and Humanoid Robotics follow AI Agents.
   Autonomous Weapons follows Swarm Technology and JADC2. Artificial General
   Intelligence's arrows come from Self-Driving Laboratories and Humanoid
   Robotics. The four new technologies borrow icons (Generative AI's, Additive
   Manufacturing's, Autonomous Vehicles' and Swarm Technology's) until theirs
   are painted.
2. **The moved unlocks.**
   - AI Agents' tooltip names the Automated Bureaucracy law and Fully
     Automated Content Creation.
   - Self-Driving Laboratories names AI Assisted Research.
   - Humanoid Robotics names Robotic Service Providers and Neuromorphic
     Computing.
   - Autonomous Weapons names Robotic Soldiers.
   - None of them shows on its old technology any more: Brain-Computer
     Interfaces, Generative AI, AGI and JADC2.
3. **Innovation cap.** AI Agents +100, Self-Driving Laboratories +200, AGI
   +300, Neural Lace +100, Mind Backups +200.
4. **Administration by Algorithm** (`society_technology_events.27`) fires
   after AI Agents, not Generative AI.
5. **Old saves** (a save from before phase 2):
   - An AGI holder is given AI Agents, Self-Driving Laboratories and Humanoid
     Robotics.
   - A country running AI Assisted Research, Neuromorphic Computing or Fully
     Automated Content Creation keeps the method and gets its technology and
     AI Agents.
   - A country under Automated Bureaucracy keeps the law and gets AI Agents.
   - A country fielding Robotic Soldiers keeps them and gets Autonomous
     Weapons.
   - One `TE_ERA13_TECH_REPAIR` line per grant. Whether the engine moved the
     building or dropped the battalions before the first month is the open
     question: if it did, record which, and the repair needs a day-one
     on-action instead.
6. **Law consistency.** A country holding Automated Bureaucracy without AI
   Agents stays on it: a held law's technology is not a violation.

## Gate: the observer runs (spec § 4.1)

Phase 1 ends with an AI-observer run on main before this change and one after,
each read with `scripts/analysis/save_world_report.py` at intervals to 2136.
Record, for the three leading great powers, the year each enters eras 11, 12
and 13 and finishes era 13. Record the early eras' entry years too (spec § 8:
the lag around eras 6 and 7). The pacing target is a leading great power
finishing era 13 by about 2136. Phase 2 shipped § 4.2's proposed innovation
budget before the runs, so the "after" run should be made with phase 2 in.
The budget is then sized to land the target: trimmed if the leaders still run
ahead, raised if they fall short.

| Run | Eras 6, 7 entered | Era 11 entered | Era 12 entered | Era 13 entered | Era 13 finished |
|---|---|---|---|---|---|
| Before (main at 6b71e07) | | | | | |
| After (phases 1 and 2) | | | | | |

## Phase 3: Automation Policy

1. **The group.** In a new game the Economy laws list Automation Policy with
   Unrestricted Automation in force for every country, and its three other
   laws greyed out until Humanoid Robotics. The group's tooltip shows the
   automated share (0% before the first count). A country released or formed
   later holds Unrestricted Automation, or its creator's law; record which.
2. **The share.** With Humanoid Robotics, a country whose Tooling Workshops or
   Urban Centers run Robotic Assembly Lines or Robotic Service Providers shows
   a share above 0% after the next month, and it rises as more buildings take
   robotic or AI-managed methods. Check it against the buildings' levels for
   one small country.
3. **Human Labor Quotas.**
   - The preview names the withdrawn methods. After enactment no building runs
     one: each AI-managed or robotic factory falls back to an earlier
     automation tier, Urban Centers to E-Commerce or earlier, Railways to
     Automated Loading and Unloading, farms to Automated Mechanical
     Harvesters. Record which method the engine picks (the first in the
     group, or the best still allowed) and whether the switch charges
     retooling.
   - Grep `debug.log` for `TE_SELF_CHECK OK|BROKEN automation_quotas`. BROKEN
     means levels still run a withdrawn method two months on: the law then
     needs a scripted switch.
   - Employment rises and output falls in the affected buildings. The withdrawn
     methods can't be picked in the building panel while the law holds.
4. **Robot Tax.** The month after enactment the country carries Robot Tax in
   the Nation tab's Economy list, with tax collection +10% and capitalists'
   investment-pool contribution −0.05 at a share of 100%, scaled by the share.
   The budget's tax lines rise to match. Repealing it removes the modifier at
   the next month.
5. **Automation Dividend.** The modifier gives the lower strata +2 and the
   middle strata +1 standard of living at a share of 100%, scaled by the
   share, and 1.5 times that with Universal Basic Income or Post-Scarcity
   Economy. The Nation tab's living-standards rows show the two strata lines.
   Only one of the two scaled modifiers is ever held, and neither stacks from
   month to month.
6. **Interest groups.** The Trade Unions approve of Human Labor Quotas and the
   Industrialists of Unrestricted Automation in the law's tooltip. Watch
   whether AI countries enact the quotas, and what it costs their output.
7. **The observer run** (spec § 7.1 sizes the magnitudes from it): for the
   leading great powers, the share at eras 11, 12 and 13, which Automation
   Policy law each holds, and its tax income and lower-strata standard of
   living beside a country under Unrestricted Automation.
