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

## Phase 3: Liquid Democracy

1. **The tree.** Liquid Democracy follows Universal Digital Identity in era
   12's society tree, with +10% voting power, and borrows Universal Digital
   Identity's icon until its own is painted.
2. **The law.** It sits in Distribution of Power beside Algorithmic
   Governance, with Publicly Funded Elections' icon for now. Its enactment
   tooltip shows the Continuous Vote line and the modifier's three effects,
   and nothing is granted on enactment.
3. **A voting law.**
   - Enact it from Universal Suffrage: elections and parties carry on, the
     government type stays a democratic one (Presidential or Parliamentary
     Republic, Constitutional Monarchy), and Women's Suffrage, Elected
     Bureaucrats and the campaign finance law in force all stay.
   - Enact it from Algorithmic Governance: parties come back and an election
     campaign starts.
   - A country holding the Tradition of Free Elections keeps it (the amendment
     re-attaches on the new law). Voting Age amendments and First Past the
     Post drop, by design.
   - Under Collective Governance it becomes a Direct Democracy, with the
     Direct Democracy amendment.
4. **The Continuous Vote.** With Neural Lace, the Continuous Vote appears in
   the Nation tab's Governance list within a year of enactment or of
   researching Neural Lace (the yearly pulse), not in the country panel's
   list, and it doesn't stack from year to year. It goes at once when the law
   is repealed. After a revolution that the law's holders win, it comes back
   at the winner's next yearly pulse.
5. **Interest groups.** An Anarchist or Optimist Transhumanist leader's group
   backs it over Universal Suffrage; groups with Republican, Liberal or Social
   Democrat leaders prefer Universal Suffrage and back going back to it.
   Radicals and Populists rate the two the same.
6. **Law consistency.** An anarchist country that loses Cooperative Ownership
   with the technology researched moves to Liquid Democracy, not Universal
   Suffrage.

### Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … liquid_democracy_elections` | once a game: OK at the first election campaign that starts under the law (`on_election_campaign_start`); BROKEN at the yearly pulse of a country that has held it six years, if no campaign has started under it anywhere | The engine holds elections under a mod Distribution of Power law with Universal Suffrage's voting power | It doesn't: no campaign in six years under the law, more than a four-year cycle and its campaign | Check what the engine keys elections on (the party emergence the law's `on_activate` runs, or a list of vanilla laws). If nothing a mod law can carry starts them, remake the law as a variant of Universal Suffrage (`parent = law_universal_suffrage`, shown only with the technology), which takes its stances and passes every `has_law_or_variant` check for it |

No line after a few years means no country has held the law long enough; enact it in a test game.

## Phase 3: Geoengineering

Stratospheric Aerosol Injection, the climate policy Geoengineering unlocks
(`docs/systems/mod_systems/global_warming.md` § Geoengineering). `event
te_debug_gw.1` reaches every state below in minutes: **c** or **d** for the
warming, **j** to adopt everything (Aerosol Injection included), **n** to run a
year of the mask (`GW_AEROSOL` in `debug.log`), **k** then **n** for termination
shock.

1. **The tree.** Geoengineering sits in era 12's society column after
   Environmental Movement and Globalization, on Environmental Movement's icon,
   and its description names the policy.
2. **The row.** Mitigation Policies ends with Aerosol Injection under National,
   on the UN's climate icon. Before the technology, Adopt is greyed with the
   technology crossed; below 1.0 °C beneath the haze, with "Warming beneath any
   aerosol haze has reached 1.0 °C" crossed. The adopt tooltip shows the
   policy's line (Environmental Movement radicalism +10), the weekly expense at
   1% of GDP a year and the objection line. Around the World counts it.
3. **The cost.** The Budget panel's Breakdown lists it under Climate Policy at
   about 1% of GDP a year, and the figure follows GDP month to month without
   stacking (one copy of Aerosol Injection: Running Cost in the country's
   modifiers).
4. **The mask.** After adopting, the overview's table gains an Aerosol Mask row
   that grows a little each month (for a country with a fifth of world GDP,
   about −0.6 °C after a year, heading to −1.00 °C). The temperature headline,
   the bar, the tier and the Warming Penalty cell fall with it; the Climate
   Warming modifier's multiplier is the masked reading. The row's hover gives
   the warming beneath, which keeps rising with emissions.
5. **Termination shock.** Repeal it with no other deployer: the mask shrinks
   month by month (two thirds back within a year), Termination Shock fires for
   every country once if 0.25 °C or more is coming back, and its modifier is
   scaled by the degrees returning. Re-adopt and repeal again: it fires again.
6. **Objection.** On adopting, countries in the monsoon regions and those whose
   will is a band short (the `l` option's `aerosol=` figure below 45) lose 10
   relations with us; each January while it runs, 5 more. No relations change
   with ourselves, and no `Attempted to create relations between a country and
   itself` assertion in `error.log`.
7. **Weakened Monsoon.** With a mask up, India, Indochina, Indonesia, southern
   China and West African countries carry Weakened Monsoon on the entry, scaled
   by the mask; it goes when the mask reaches 0.
8. **No false recovery.** A mask that pushes the felt reading below 3, 2 or
   1 °C fires none of the recovery events (The Heat Recedes and the rest); they
   still fire when the warming beneath falls.
9. **AI.** In an observer run past 3 °C, some AIs adopt it (laissez-faire
   exporters first), none adopts while in default, none adopts once the mask
   is at its 2 °C ceiling, and a deployer doesn't drop it once its mask works.
   Record when the first AI deploys and whether a termination shock happens.
10. **Civil war.** A revolution that wins in a deploying country keeps the
    policy (the row stays lit within a month) and its cost.

## Phase 3: AI Tutors

1. **The tree.** AI Tutors sits in era 11's society column, its arrow from
   Digital Education (era 9), and borrows Digital Education's icon until its
   own is painted. Its tooltip lists qualifications +10%, literacy growth,
   education access +10 and the Ministry of Thought Control's maximum
   investment +1.
2. **The ministry's ceiling.** Human Augmentation now lists +2 for the
   Ministry of Thought Control, not +3. Under the Ministry of Thought Control
   law with Cyber Warfare, Brain-Computer Interfaces, Human Augmentation and AI
   Tutors researched, the ministry's maximum investment reads 9. In an old
   save, a country at level 9 without AI Tutors now has a ceiling of 8: record
   whether the engine lowers its investment at once or holds it until it
   changes (no repair grants AI Tutors for it).
3. **Education access.** A state's education access rises by 10 points when
   AI Tutors completes, and its breakdown names the technology.
4. **Lessons Between the Lines** (`event society_technology_events.36` in a
   country under Unregulated Internet with AI Tutors). It shows the
   whistleblower picture. The first option gives Open Curricula, capitalist
   radicals, and the Intelligentsia's and Industrialists' approval lines; the
   second gives Contracted Curriculum and the reverse approvals.
5. **The Ministry's Syllabus** (`event society_technology_events.37`). Its
   description names the Ministry of Thought Control, the Ministry of
   Propaganda, or the censors under State-Controlled Internet alone. The
   second option radicalizes bureaucrats.
6. **The loyalty line.** Contracted Curriculum and The State Syllabus show a
   Monthly Loyalists line of 0.1%. The type sets no `decimals`, so confirm it
   doesn't render as 0%. After either, an incorporated state's pops gain
   loyalists each month, even in a country without a Ministry of Thought
   Control (the state's Monthly Loyalists breakdown names the modifier), and
   the line fades over ten years.
7. **Once each.** Neither event comes back in the same country, whichever
   option was taken.

## Phase 3: Aneutronic Fusion

1. **The tree.** Aneutronic Fusion sits in era 13's military column after
   Compact Fusion Reactors, and Microfusion Cells' (formerly Fusion Batteries) arrow now comes from it, not
   from Compact Fusion Reactors. It borrows Compact Fusion Reactors' icon
   until its own is painted. Its tooltip names Aneutronic Fusion Power, Fusion
   Torch Reclamation and the Interstellar Mission; Compact Fusion Reactors'
   no longer names the Interstellar Mission.
2. **Aneutronic Fusion Power.** A Fusion Plant offers it after Compact Fusion
   Power, with a purple bolt as a borrowed icon. A level employs 950 (450
   laborers, 300 machinists, 100 engineers, 100 academics) and makes 16,000
   electricity before throughput. Its description shows in the tooltip.
3. **The AI-managed option on it.** With Smart Grids, a Fusion Plant on
   Aneutronic Fusion Power shows one AI Managed Power Plant option, and on it
   the building employs only the 1,000-engineer crew, with no laborers,
   machinists or academics left. Switching the base back to Compact Fusion
   Power swaps it for the reactor option (one AI-managed option either way).
   Centralized Control and Integrated Smart Systems leave 30 laborers and 20
   machinists a level on the new base, never a negative count.
4. **Fusion Torch Reclamation.** A Steel Mill offers it after Microgravity
   Alloying: 50 iron and 600 electricity for 600 steel a level, 3,000 staff,
   pollution 10. Bespoke Alloys can run beside it, and its carbon-capture group
   shows only the not-applicable option.
5. **The Interstellar Probe** in a new game: the Interstellar Mission method,
   Begin the Interstellar Mission and the inactive Interstellar Probe entry
   all wait for Aneutronic Fusion. A country with Compact Fusion Reactors and
   the Deep-Space Probe and Mars Landing done sees none of them.
6. **Old saves** (a save from before this change):
   - A Microfusion Cells holder is given Aneutronic Fusion in the first month.
   - A Compact Fusion Reactors holder whose Space Program runs the
     Interstellar Mission is given it too, whether its probe is running,
     finished or not yet started.
   - A Compact Fusion Reactors holder on a lower mission gets nothing.
   - One `TE_ERA13_TECH_REPAIR` line per grant.
   - **A probe under way keeps its progress.** Its entry's `possible` now
     names Aneutronic Fusion, so it may deactivate before the repair month and
     re-activate on the grant. Record whether the bar comes back where it was,
     or at 0 (the monthly milestone cleanup ran between them), and whether the
     engine moved the Space Program off the Interstellar Mission at the load
     (the entry would then fail with Program Discontinued). Either one means
     the repair needs a day-one on-action.

## Phase 3: Vactrains

1. **The tree.** Vactrains sits in era 12's production column, after
   Autonomous Vehicles (era 11) and Quantum Materials, and borrows Quantum
   Materials' icon until its own is painted. Its tooltip names two Railway
   methods, Vactrains and Vactrain Freight, and no modifiers.
2. **Rolling Stock.** On a railway in a state with Electricity, Vactrains
   follows Maglev Trains in the passenger group: 160 Transportation and +15
   infrastructure a level, on steel, electronic components, tech metals and
   electricity. In a state with no Electricity it can't be picked
   (`required_input_goods`), and the AI's railways stay on Maglev Trains there.
3. **Freight.** Vactrain Freight follows Autonomous Trains in the base group:
   170 Transportation and 60 infrastructure a level, 10 engineers, on
   electricity, electronic components, tech metals and digital assets. Its
   tooltip shows no emissions or pollution line.
4. **Maintenance.** A railway switched to Vactrain Freight settles on Heavy
   Maintenance (0.15 construction a level); one switched from steam trains
   straight to it steps up through Standard within a few days, as for
   Containerized Cargo.
5. **The AI.** Both groups are `most_productive`, so AI railways in electrified
   states move to the two methods after the technology, each switch a
   five-year retool. Watch that railways in states short of Electricity are
   not pulled onto them and starved.
6. **Retooling waiver.** A railway in a Transport principle tier 3 bloc that
   switches from a diesel variant to Vactrain Freight pays the full
   Retooling: the change is not read as the principle swap
   (`te_state_railway_train_code` 13 to 8).

## Phase 3: Von Neumann Machines

1. **The tree.** Von Neumann Machines sits in era 13's production column with
   arrows from Molecular Assemblers and Orbital Manufacturing. It borrows
   Molecular Assemblers' icon until its own is painted. Its tooltip names
   Self-Replicating Construction and Self-Replicating Miners and lists +100
   maximum weekly construction progress.
2. **Construction Sector (market game).** Self-Replicating Construction is the
   last method of the base group, after Nanomaterial Buildings, and makes 24
   construction a level before throughput (Nanomaterial Buildings: 16). It
   borrows Nanorobots' icon. All four automation methods stay selectable on it
   (Prefabricated Building Components, Tower Cranes, Computer-Aided Design, 3D
   Printed Buildings), and none takes its employment below zero. The
   construction principle's method applies to it. An AI sector moves up to it
   once the technology arrives (the group is `most_productive`).
3. **Construction Site (direct game).** The site lists eight tiers, the new one
   hidden until researched, and gives 24 points a level on it. The construction
   panel's Construction Capacity hover reads "from 1 a week for Wooden
   Buildings to 24 for Self-Replicating Construction". An AI site on the new
   tier that the AI downsizes comes back on the new tier at the next weekly
   pulse (the guard's tier 8). In a market game the direct tier never shows.
4. **Extraplanetary Base.** Self-Replicating Miners is the last base method,
   after Resort Colony, with Intelligent Drilling Rigs' borrowed icon. Its
   crew (400 engineers, 100 academics) fills at any level. With neither
   logistics upgrade the method's tooltip shows 320 Launch Capacity a level;
   Fusion Tugs and Tethered Launch each still cut it by 30%. The
   `logistics_input_cut` self-check reads OK on a base running it, since the
   method carries no launch multiplier of its own. An AI base on Mining Colony
   switches to it (the group's default `most_profitable`).

## Phase 3: Advanced Fission

1. **The tree.** Advanced Fission sits in era 11's military tree after Nuclear
   Energy, on Nuclear Energy's icon until its own is painted.
2. **The method.** A Nuclear Plant offers Generation IV Reactors beside Nuclear
   Power once Advanced Fission is researched. At the same staff it makes 3,500
   electricity a level (Nuclear Power 2,000) and buys Advanced Materials. The
   AI-managed reactor automation still shows for a plant on either method.
3. **The AI switches.** An AI Nuclear Plant moves to Generation IV Reactors
   within a year of the technology, where Advanced Materials are on its market.
