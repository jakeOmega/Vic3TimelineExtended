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

## Phase 3: Frontier AI Control

1. **A new game.** The laws panel shows Frontier AI Control among the power
   structure groups from 1836, every country on No Frontier AI Policy, and no
   other law of the group enactable. The six laws borrow other laws' icons (No
   Internet Policy's, Corporate Genetic Licensing's, Ministry of Science's,
   State Intellectual Property's, Ministry of International Aid's and Open
   Source Innovation's) until theirs are painted.
2. **The opening.** The day a country researches AI Agents (or gets it by
   spread) it moves to Private Labs, with no enactment. No Frontier AI Policy then reads as not enactable, with its
   tooltip.
3. **Tooltips.** Each law lists its lines: innovation, Economic Covert Defense,
   authority, intelligence capacity, diplomatic reputation, technology spread,
   the interest group lines and International Oversight's UN Authority Target
   +0.50. Open Weights' enactment tooltip names the 100 and the 300;
   International Oversight's says it falls to National Licensing.
4. **International Oversight.** With the United Nations rule off the law is not
   in the panel. A non-member sees it greyed with "We are a member of the
   United Nations". A member enacts it; then pressing Leave the United Nations
   shows the line that the law falls to National Licensing, and the law is
   National Licensing the same day. The same on the UN's dissolution, for every
   member holding it.
5. **Open Weights' world share.** With a great or major power holding Open
   Weights, the Global Technological Development tooltip of every country,
   recognized or not, rises by 100 at the next yearly pulse (up to 300 with
   three or more holders). A minor power's Open Weights adds nothing.
6. **Interest groups.** In a late game, the Armed Forces back State Monopoly,
   the Industrialists Private Labs and the Intelligentsia Open Weights in the
   law panel's interest group view, and most others National Licensing.
7. **Old saves.** Load a save from before this change. Every country holds No
   Frontier AI Policy (the group's first law), with no `two laws are active in
   the same group` assert in `error.log`, and each AI Agents holder moves to
   Private Labs at its next technology, law change or yearly pulse.
8. **New countries.** A country released or formed after AI Agents holds a law
   of the group (copied from its parent or the placeholder), and one that is
   not a UN member does not keep International Oversight past its next yearly
   pulse.
