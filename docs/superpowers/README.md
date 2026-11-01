# Plans and specs: index

This folder holds the design specs (`specs/`) and implementation plans (`plans/`) written with the brainstorming and `/writing-plans` workflows. Each file is dated by when it was written. Once everything a doc set out to build is on `main`, it moves to `archive/`, keeping its `plans/` or `specs/` subfolder.

Status was checked on 2026-10-19 against `main` at `67dca09`, and again on 2026-10-25 at `dd43038` for the PRs merged in between. Each doc was checked against the code and the merged PRs, not its own checkboxes, which are mostly never ticked. A doc counts as done when everything it commits to has shipped. Items it calls out of scope or ideas for later don't count against it, and neither do in-game play-tests, since those don't gate a merge (`CLAUDE.md`). Shipped systems are documented in `docs/systems/` (mostly in `mod_systems/`, one file per system, indexed by `mod_systems.md`) and their in-game checks in `docs/testing/`. Read those for how a system works now: an archived spec records the design and reasoning, and later work may have changed it.

**Keeping this current:** when a doc's last piece ships, `git mv` it into `archive/`, rewrite every reference to its old path (`git grep -n "superpowers/specs/<name>" -- ':!gfx'`, which covers comments in `common/`, `gui/`, generators and tests), and move its row from Active to Archived below. A new spec or plan gets its row under Active in the PR that adds it.

## Active

### Demographics

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-10-08-demographics-design.md](specs/2026-10-08-demographics-design.md): the master design (census by age and sex, fertility, causes of death, Wealth Concentration, Gini, urban pattern, panel, rule, phases 0–3) | Partial: phases 0–3 built (phase 0 #828, phase 1 #830, then the phase 2 and 3 PRs through #947); Wealth Concentration's remaining shocks, the r > g term and §7's Inequality effect (2026-10-19, #1068); Internal Resettlement's moves booked by programme profile with its transit dead as known kills (§2.5), and §2.6's young, male US frontier start (both 2026-10-19, #1069); §5.2's per-state metropolitan share (#1071); the safeguards pass's chronic treatment to 0.99, the means' cap 1, no floor on the laws factors, no crowding ceiling and the life tables' open last interval (2026-10-20, #1081); the owner's follow-ups of 2026-10-20 (#1085): the hyperinflation crisis's Wealth Concentration shock (§4.2's Money bullet), no cap on the Inequality effect, the Old Southwest and Florida in the 1836 frontier, and all six chronic carriers in the health bill | Map modes are blocked and sit in no phase |
| [specs/2026-10-22-demographic-effects-impact-design.md](specs/2026-10-22-demographic-effects-impact-design.md): stronger, distinct demographic effects (Wealth Concentration, Inequality, the urban pattern and metropolitan share, sex balance, the youth bulge): a strong condition worth a vanilla law, curves that keep rising past their reference, an upside and a cost at each pole; [plan](plans/2026-10-22-demographic-effects-impact.md) | Built 2026-10-22 (#1101): Phase 0's tools and phases 1 and 2 at the starting sizes; the bubble line measured (`banking_cycle_simulation.md` §27) | The owner's save readouts (`demographics_harness.py wc`, `gini`, `effects`) can still move the Gini slope; the play-test list; Phase 3 (urban share as an amplifier, the Demographic Dividend, threshold events, Primate City's fade) |
| [specs/2026-10-10-demographics-late-marriage-design.md](specs/2026-10-10-demographics-late-marriage-design.md): Late Marriage and Birth Spacing, two fertility customs with per-state shares, drift and neighbour spread | Partial: phase 2 (#931) and the phase 3 spread (#945) built; plan archived | Phase 3's minimum-marriage-age lever (§6, call 9: no `state_late_marriage_target_add` type, no law carries one) and §2.5's age schedule blended by the shares (the late game added a postponement shift but holds it at 0) |
| [plans/2026-10-10-demographics-phase2-calibration.md](plans/2026-10-10-demographics-phase2-calibration.md): the six calibration steps phase 2 needs, plus a gate | Partial, parked: steps 1–4 built (#855, #857, #930, #869), step 5 dropped by the owner | Step 6 (refit the post-1900 schedules against Clio Infra) was never built as a step, though #979 and #1051 cover part of it. The gate's regional items (USA and Canada, Southeast Asia, Europe's flat death rate, India 1837–62) were not met. The owner parked the remaining calibration on 2026-10-18 when closing #894 |

### Legislated tax code

The first playable milestone shipped behind the experimental, default-off `te_tax_code_rule` in #680. The AI and release design (packages 6–7) and the Light code are archived.

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-09-29-legislated-tax-code-design.md](specs/2026-09-29-legislated-tax-code-design.md): the umbrella design (draft, bill, interest-group bargain, commencement, obligations, estimates, AI, civil-war continuity) | Partial: §12 steps 1–4 built (#641, #648, #680, #845) | §12 step 5 (customs and treaty integration, delegation, parliamentary and presidential procedures); step 6 (advanced instruments, behavioural forecasts); promise kinds beyond the four; the carbon tax as one source of truth; the §14 decisions |
| [plans/2026-09-30-legislated-tax-code.md](plans/2026-09-30-legislated-tax-code.md): the package-level plan, packages 0–8 | Partial: packages 0–7 built | Package 8 (catalog expansion: political-reform, colonial, monetary and restraint promises, advanced instruments) and package 3's split of the carbon effects |
| [plans/2026-10-02-legislated-tax-code-tasks.md](plans/2026-10-02-legislated-tax-code-tasks.md): Tasks 1–17 for packages 1–5 | Partial: Tasks 1–15 built (#680), Task 17 replaced by the 10-03 plan's Tasks 25–27 | Task 16, the carbon levy. Only its numbers exist (`docs/systems/carbon_levy_numbers.md`, "parked until #674", which has since landed). `carbon_tax_modifier` is unchanged |

### Nuclear weapons

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-10-28-nuclear-crisis-rework-design.md](specs/2026-10-28-nuclear-crisis-rework-design.md): survivability measured against the enemy's arsenal, payoffs for Delegation and Launch on Warning, accident risk calibrated to the Cold War, accident claims, a strike planner with counterforce and decapitation, range, and new crisis disputes and concessions | Design only (2026-10-28): the owner's calls in its §1 | All four phases (§13); open question 1 reverses part of a 2026-09-26 ruling |

### Space Race

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-10-25-solar-colonization-holders-and-cession-design.md](specs/2026-10-25-solar-colonization-holders-and-cession-design.md): slices 0 and 1, a holder record for every world (the panel's Solar System list, a dead holder's colonies passing to its capital's owner), four settings of the Space Race rule, and the Cede Colony treaty article; [plan](plans/2026-10-25-solar-colonization-holders-and-cession.md) | Built 2026-10-25 (slices 0 and 1, one PR); as built in the design's § 17 | The play-test list (`docs/testing/solar-colonies-playtest.md`) and its three self-checks |
| [specs/2026-10-25-solar-colonization-population-and-transit-design.md](specs/2026-10-25-solar-colonization-population-and-transit-design.md): slices 2 and 3, a Target button on every world (all settings), transit tables for four drives in the launch-window generator, colony fleets that travel and claim on arrival with distance in place of the stages, colony population with an emigration programme, per-colony priorities, crews and Artificial General Intelligence, and the Off-World Population bonus (simple and full colonies); the build order is its § 14 | Built 2026-10-25 (slices 2 and 3, one branch); as built in its § 15 | The play-test list's slices 2-3 part (`docs/testing/solar-colonies-playtest.md`) and its two self-checks |
| [specs/2026-10-25-solar-colonization-modules-and-bases-design.md](specs/2026-10-25-solar-colonization-modules-and-bases-design.md): slice 4, colony modules (the two specializations sharing four levels, Habitat, and Defences and Spaceport as placeholders), crews and staffing, the Space Program's Module Fabrication method group with a queue, shipments that wait for windows and travel, and Extraplanetary Base room from the near-Earth asteroids and colonies with per-world grades and a penalty past it (simple and full colonies); the build order is its § 14 | Built 2026-10-25 (slice 4, one branch); as built in its § 15 | The play-test list's slice 4 part (`docs/testing/solar-colonies-playtest.md`) and its two self-checks; the grades and costs at a first guess (M1) |
| [specs/2026-10-29-lunar-colonization-design.md](specs/2026-10-29-lunar-colonization-design.md): the Moon Base milestone retired into six lunar worlds at Solar System Colonization's stage 0 (founded the month the fleet leaves, the first lunar colony keeping the Moon Base's first), colonization opened in era 10 by Cislunar Infrastructure with worlds beyond the Moon on the Mars Landing, the Extraplanetary Base from era 10 (In-Situ Resource Utilization, Regolith Processing), lunar worlds assaultable at Earth under Full Colonies, Nuclear Thermal Propulsion as a smaller off-window premium, higher stage goals, and funding past the cap with diminishing returns; the build order is its § 13 | Built 2026-10-29 in #1233–#1238 (PR4 funding past the cap, PR1 the technologies and the era-10 base, 3a Nuclear Thermal Propulsion, 2a six lunar worlds, 3b lunar worlds at Earth, 2b the Moon Base retired), #1239 the wording (colony sites are "sites"); as built in its § 16, with the owner's answers to § 15 | The play-test list's lunar parts (`docs/testing/solar-colonies-playtest.md`) and their self-checks; the owner's open calls in its § 16 |
| [specs/2026-10-26-solar-colonization-free-colonies-design.md](specs/2026-10-26-solar-colonization-free-colonies-design.md): slice 5, colony autonomy (a monthly drift from people, distance by drive, isolation, war and garrisons; a demand at 75 answered by a charter, a garrison or freedom; breaking away at 100), free colonies that wait and trade (supply, trade and ties, a petition to rejoin at full ties), abandonment (people home or left free), a dead holder's peopled worlds left free, Incite Colonial Autonomy and Sabotage Colony, three colony life events, and Simple Colonies as the rule's default; the build order is its § 13 | Built 2026-10-26 (slice 5, one branch) | The play-test list's slice 5 part (`docs/testing/solar-colonies-playtest.md`) and its self-check; the drift's terms at a first guess |
| [specs/2026-10-30-colony-management-design.md](specs/2026-10-30-colony-management-design.md): the owner's play-test notes on the Colonies section: the AI tends and prices its colonies, autonomy settles and builds a colony's own modules, slots grow with technology with a rising price past them, ten facility modules, Next Windows as a table, and the colony boxes and a colony's page; the build order is its § 10 | Built 2026-10-30 in #1257; #1258 finished § 4.1's colors and § 5's slot technologies as markers (five of them), made the drives markers, and took the owner's review of the panel (vanilla's underlining, the name as a button, a colony's page rebuilt, each site's slots and base room in Solar System, the race to the Moon explained); as built in its § 11 | The play-test list's colony management part (`docs/testing/solar-colonies-playtest.md`) and its two self-checks (`drive_marker`, `slot_marker`); the owner's calls in its § 11, fine for now |

### Technology

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-10-31-era-13-technology-tree-design.md](specs/2026-10-31-era-13-technology-tree-design.md): today's era 12 split into a grounded era 12 and a hard-science-fiction era 13 (costs 1.5M and 3M), Bioenhanced Soldiers up from 11, sixteen new technologies (the era 11 AI wave, Rejuvenation Therapies, Post-Work Society, Compact and Aneutronic Fusion, Von Neumann Machines, the identity line to Self-Directed Evolution), a law-group trio (Bodily Autonomy, Automation Policy, Frontier AI Control), Superintelligence reserved for its own design | Built (2026-11-01): phases 1 and 2 and all twelve of phase 3's items (§ 9); Superintelligence reserved (§ 3.5) | The observer runs (§ 4.1, `docs/testing/era-13-playtest.md`), which size the innovation budget and phase 3's first-estimate magnitudes; the play-test list; the owner's review of each PR's Decisions |

### Migration and climate

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-11-01-local-climate-design.md](specs/2026-11-01-local-climate-design.md): a climate record per state region (summer heat and humidity, winter cold, aridity, malaria, latitude) feeding a comfort penalty in migration attraction, eased by technology (cold early, then disease and water, then air conditioning) and moved by global warming; the mass migration arable land minimum removed; a Local Climate state panel tile | Phase 1 in PR #1307; phases 2–3 building | Comfort, relief, the defines and warming (`feat/local-climate-comfort`) |
| [plans/2026-11-01-local-climate.md](plans/2026-11-01-local-climate.md): Tasks 1–9 in two PRs (A: the record, the generator and the tile's readings; B: relief carriers, the comfort formula with warming, the modifier and defines, the Comfort row, docs) | Tasks 1–3 in PR #1307; 4–5 done on `feat/local-climate-comfort` | Tasks 6–9 |

## Archived — `archive/`

Everything below has shipped. PR numbers are the main build first, then follow-ups.

### Covert warfare

| Doc | Shipped in |
|-----|------------|
| [specs/2026-09-22-covert-warfare-expansion-design.md](archive/specs/2026-09-22-covert-warfare-expansion-design.md): design menu and build order, seven slices | #372, #374, #375, #377, #379, #384, #409 |
| [plans/2026-09-22-covert-per-op-detection-roll.md](archive/plans/2026-09-22-covert-per-op-detection-roll.md): slice 1, a detection roll per operation | #372 |
| [plans/2026-09-22-covert-graduated-exposure.md](archive/plans/2026-09-22-covert-graduated-exposure.md): slice 2, graduated exposure | #374 (#486, #491) |
| [plans/2026-09-22-covert-per-op-priority.md](archive/plans/2026-09-22-covert-per-op-priority.md): slice 3, priority per operation | #375 |
| [plans/2026-09-22-covert-per-target-networks.md](archive/plans/2026-09-22-covert-per-target-networks.md): slice 4, a network per target | #377 |
| [plans/2026-09-22-covert-tradecraft.md](archive/plans/2026-09-22-covert-tradecraft.md): slice 5, agency experience ("Tradecraft") | #379 |
| [plans/2026-09-23-covert-new-operations.md](archive/plans/2026-09-23-covert-new-operations.md): slice 6, four new operation types | #384 |
| [plans/2026-09-24-covert-network-intelligence.md](archive/plans/2026-09-24-covert-network-intelligence.md): slice 7, intelligence a network reveals | #409 |
| [specs/2026-10-06-covert-tech-theft-design.md](archive/specs/2026-10-06-covert-tech-theft-design.md) and [plan](archive/plans/2026-10-06-covert-tech-theft.md): espionage steals technology progress | #780, #783, #814 |
| [specs/2026-10-16-covert-counterintel-backlash-design.md](archive/specs/2026-10-16-covert-counterintel-backlash-design.md) and [plan](archive/plans/2026-10-16-covert-counterintel-backlash.md): watching caught operations, domestic backlash, Counterintelligence Support | #974 |

### Nuclear weapons

| Doc | Shipped in |
|-----|------------|
| [specs/2026-09-25-nuclear-crisis-communication-design.md](archive/specs/2026-09-25-nuclear-crisis-communication-design.md) and [plan](archive/plans/2026-09-25-nuclear-crisis-communication.md): bluffs priced in, tooltips with numbers, the crisis panel's breakdowns, At Home by Rules of War | #452, #454 (#750) |
| [specs/2026-09-25-nuclear-umbrella-recessed-dead-hand-design.md](archive/specs/2026-09-25-nuclear-umbrella-recessed-dead-hand-design.md) and [plan](archive/plans/2026-09-25-nuclear-umbrella-recessed-dead-hand.md): the umbrella over subjects, Recessed readiness, Automatic Retaliation | #455 |
| [specs/2026-09-26-nuclear-custody-design.md](archive/specs/2026-09-26-nuclear-custody-design.md): custody through civil wars and annexation, the arsenal ledger | #467 (#474) |
| [specs/2026-09-26-nuclear-loose-warheads-design.md](archive/specs/2026-09-26-nuclear-loose-warheads-design.md): Deny Them the Bomb, foreign reaction, the Budapest path, loose warheads | #474 (#484) |
| [specs/2026-09-26-nuclear-taboo-design.md](archive/specs/2026-09-26-nuclear-taboo-design.md) and [plan](archive/plans/2026-09-26-nuclear-taboo.md): the world nuclear taboo; phase 3, the Prohibition convention, shipped as UN phase 7 | #522 (#528, #542), #651 |

### United Nations

| Doc | Shipped in |
|-----|------------|
| [plans/2026-07-06-multilateral-institutions-principle-group.md](archive/plans/2026-07-06-multilateral-institutions-principle-group.md): the Multilateral Institutions principle group and the Foreign Service rename | #239 (the UN redesign, #411, later reworked parts) |
| [plans/2026-07-06-un-authority-global-variable-fix.md](archive/plans/2026-07-06-un-authority-global-variable-fix.md): `un_authority` as one global variable | #239 |
| [plans/2026-09-25-un-subject-membership.md](archive/plans/2026-09-25-un-subject-membership.md): UN membership for subjects | #466 |
| [specs/2026-09-27-un-vote-lobbying-design.md](archive/specs/2026-09-27-un-vote-lobbying-design.md) and [plan](archive/plans/2026-09-27-un-vote-lobbying.md): late AI ballots, visible leans, lobbying | #531 (#612, #649) |
| [specs/2026-09-28-un-gui-pass-design.md](archive/specs/2026-09-28-un-gui-pass-design.md) and [plan](archive/plans/2026-09-28-un-gui-pass.md): UN GUI pass, round 1 | #567 |
| [specs/2026-10-02-un-narcotics-convention-design.md](archive/specs/2026-10-02-un-narcotics-convention-design.md): the Single Convention on Narcotic Drugs | #658 |

### Banking and monetary policy

| Doc | Shipped in |
|-----|------------|
| [plans/2026-09-19-monetary-policy-phase1.md](archive/plans/2026-09-19-monetary-policy-phase1.md): policy rate, credit standing, delegation and mandates | #335 (#346) |
| [plans/2026-09-20-monetary-policy-phase2.md](archive/plans/2026-09-20-monetary-policy-phase2.md): inflation, monetisation, wage pressure, stance politics | #339 |
| [specs/2026-09-23-banking-tools-expansion-design.md](archive/specs/2026-09-23-banking-tools-expansion-design.md): Directed Credit sectors, Reserve Requirements, Bank Holiday, Bail-in | #381, #382 (#716) |
| [specs/2026-10-17-banking-always-on-design.md](archive/specs/2026-10-17-banking-always-on-design.md): the banking entry for every country, its cycle dormant until it starts | #1020, #1027 |

### Tax code, laws and drugs

| Doc | Shipped in |
|-----|------------|
| [specs/2026-10-03-tax-code-ai-and-release-design.md](archive/specs/2026-10-03-tax-code-ai-and-release-design.md) and [tasks](archive/plans/2026-10-03-tax-code-ai-and-release-tasks.md): tax code packages 6–7, AI legislation and release validation | #680 |
| [specs/2026-10-09-tax-code-light-design.md](archive/specs/2026-10-09-tax-code-light-design.md): the Light Tax Code setting | #845 |
| [specs/2026-10-01-bureaucracy-laws-design.md](archive/specs/2026-10-01-bureaucracy-laws-design.md): machine administration vs. machine rule, Contracted and Communal Administration, the Spoils System | #623, #625 (#638) |
| [specs/2026-10-04-policing-laws-design.md](archive/specs/2026-10-04-policing-laws-design.md): Private Policing and its amendments | #697 |
| [specs/2026-10-08-inheritance-laws-design.md](archive/specs/2026-10-08-inheritance-laws-design.md): the inheritance group redesign (new laws, four amendments, Wealth Concentration, rural births, generation events; the second wave of events in its § 11) | #822, #843, #1154 |
| [specs/2026-10-17-judiciary-design.md](archive/specs/2026-10-17-judiciary-design.md): the Judiciary law group (six court laws, Judicial Independence, entrenchment, overhaul shock); phases 2–4 (defying the court, seven amendments, landmark cases) as built in its § 14 | #1022 (#1025, #1021), #1154 |
| [plans/2026-10-17-judiciary-phase1.md](archive/plans/2026-10-17-judiciary-phase1.md): Judiciary phase 1 | #1022 (#1025) |
| [plans/2026-10-02-drugs-phase-2-healthcare-demand.md](archive/plans/2026-10-02-drugs-phase-2-healthcare-demand.md): the Healthcare need and opium plantation penalties | #656 (#657, #658) |

### Demographics

| Doc | Shipped in |
|-----|------------|
| [plans/2026-10-08-demographics-phases-0-1.md](archive/plans/2026-10-08-demographics-phases-0-1.md): the age model, harness, census, tab and rule | #828, #830 (#833) |
| [specs/2026-10-12-demographics-phase2-consequences-design.md](archive/specs/2026-10-12-demographics-phase2-consequences-design.md): what the census feeds (interfaces; workforce, pensions and health; Family Policy; conscription and sex balance) | #925, #932, #935, #938, #940, #942, #946 (#989) |
| [plans/2026-10-12-demographics-phase2-interfaces.md](archive/plans/2026-10-12-demographics-phase2-interfaces.md): phase 2 step 1, the interfaces, changing no number | #932 |
| [plans/2026-10-10-demographics-phase2-engine-rates.md](archive/plans/2026-10-10-demographics-phase2-engine-rates.md): calibration step 4, the census sets the engine's births and deaths; its floor moved to the engine's own −1 and its ceilings went on 2026-10-20 (owner; the plan carries a dated note) | #869 (#876, #885, #889, #900, #904, #907, #913, #1082) |
| [plans/2026-10-11-demographics-engine-lines-script-only.md](archive/plans/2026-10-11-demographics-engine-lines-script-only.md): the engine's birth and death lines as script-only types | #892 |
| [specs/2026-10-12-demographics-calibration-step3-design.md](archive/specs/2026-10-12-demographics-calibration-step3-design.md): the regional mortality gap | #930 |
| [specs/2026-10-12-demographics-fast-mode-revenue.md](archive/specs/2026-10-12-demographics-fast-mode-revenue.md): should fast mode pay the AI's bills? (decided: no) | #922 (the subsidy follow-up: #980, #981) |
| [plans/2026-10-09-demographics-modifier-types-stage1.md](archive/plans/2026-10-09-demographics-modifier-types-stage1.md): modifier types stage 1, mortality | #850 |
| [plans/2026-10-10-demographics-modifier-types-stage2.md](archive/plans/2026-10-10-demographics-modifier-types-stage2.md): modifier types stage 2, fertility | #852 |
| [plans/2026-10-10-demographics-gini-wealth-bands.md](archive/plans/2026-10-10-demographics-gini-wealth-bands.md): Gini by wealth band | #854 (#860, #867) |
| [plans/2026-10-11-demographics-causes-of-death.md](archive/plans/2026-10-11-demographics-causes-of-death.md): Causes of Death, medicine that spreads, turmoil's violence | #916 (#921, #929; country tab #1041) |
| [plans/2026-10-11-demographics-late-marriage.md](archive/plans/2026-10-11-demographics-late-marriage.md): Late Marriage and Birth Spacing, phase 2 scope (the spec stays active) | #931 |
| [specs/2026-10-11-demographics-late-game-design.md](archive/specs/2026-10-11-demographics-late-game-design.md): old age, work, children and who lives longest | #932, #940, #942, #946, #947, #962 (#979, #989, #1006, #1051) |
| [specs/2026-10-09-demographics-modifier-types-design.md](archive/specs/2026-10-09-demographics-modifier-types-design.md): census inputs from laws, techs and institutions as script-only `state_*` modifier types, in three stages | #850, #852, #1009, #1066 |
| [specs/2026-10-16-demographics-uploaded-minds-design.md](archive/specs/2026-10-16-demographics-uploaded-minds-design.md): an "uploaded minds" pool beside the census, and Mind Backups' restore scaled by longevity care | #1070 |

### Grand Monuments

| Doc | Shipped in |
|-----|------------|
| [specs/2026-09-27-grand-monument-rework-design.md](archive/specs/2026-09-27-grand-monument-rework-design.md) and [plan](archive/plans/2026-09-27-grand-monument-rework.md): v1, monuments as a political instrument (its phase 2 was superseded by v2, landmarks and pictures) | #541 |
| [specs/2026-10-05-grand-monuments-v2-design.md](archive/specs/2026-10-05-grand-monuments-v2-design.md): v2's six phases; 1–3 built, 4–6 superseded by the landmarks, trophies and signatures specs | #759 |
| [plans/2026-10-05-grand-monuments-v2-phases-1-3.md](archive/plans/2026-10-05-grand-monuments-v2-phases-1-3.md): v2 phases 1–3, numbers, commissions and names, policy | #759 |
| [specs/2026-10-11-grand-monument-pictures-design.md](archive/specs/2026-10-11-grand-monument-pictures-design.md) and [plan](archive/plans/2026-10-11-grand-monument-pictures.md): pictures, forms and styles | #909, #910 |
| [specs/2026-10-12-grand-monuments-landmarks-design.md](archive/specs/2026-10-12-grand-monuments-landmarks-design.md) and [plan](archive/plans/2026-10-11-grand-monuments-landmarks.md): landmarks standing in 1836 | #912 |
| [specs/2026-10-12-grand-monument-trophies-design.md](archive/specs/2026-10-12-grand-monument-trophies-design.md): trophies | #924 (#948, #951, #952, #972, #997) |
| [specs/2026-10-12-grand-monument-loot-and-1836-trophies-design.md](archive/specs/2026-10-12-grand-monument-loot-and-1836-trophies-design.md): landmarks to loot, the trophies of 1836 | #941 |
| [specs/2026-10-12-grand-monument-opportunities-design.md](archive/specs/2026-10-12-grand-monument-opportunities-design.md): commissions become opportunities | #915, #920 |
| [specs/2026-10-13-multiple-monuments-per-state-design.md](archive/specs/2026-10-13-multiple-monuments-per-state-design.md) and [plan](archive/plans/2026-10-13-multiple-monuments-per-state.md): several monuments in one state (its level-sum model was superseded by construction sites) | #958 (#971) |
| [specs/2026-10-14-grand-monument-archaeology-design.md](archive/specs/2026-10-14-grand-monument-archaeology-design.md): buried sites and the archaeology loop (its treasury cost was replaced by the rework) | #959 (#970, #972) |
| [specs/2026-10-16-grand-monument-archaeology-rework-design.md](archive/specs/2026-10-16-grand-monument-archaeology-rework-design.md): fixed dig costs, sized digs, site events, foreign excavation | #965 |
| [specs/2026-10-16-grand-monument-ageing-design.md](archive/specs/2026-10-16-grand-monument-ageing-design.md) and [plan](archive/plans/2026-10-16-grand-monument-ageing.md): grander with age (the freeze at dedication was superseded by construction sites) | #971 (#1055, #1058, #1064) |
| [specs/2026-10-16-grand-monument-signatures-design.md](archive/specs/2026-10-16-grand-monument-signatures-design.md): unique dedications | #998 (#1064) |
| [specs/2026-10-18-grand-monument-sites-and-world-wealth-design.md](archive/specs/2026-10-18-grand-monument-sites-and-world-wealth-design.md): construction sites, recorded size, grandeur priced by world wealth | #1057, #1058, #1059, #1060 (#1064) |
| [plans/2026-10-18-grand-monument-sites-plan-a.md](archive/plans/2026-10-18-grand-monument-sites-plan-a.md): size in records, construction sites, level-1 monuments | #1057, #1058 |
| [plans/2026-10-18-grand-monument-sites-plan-b.md](archive/plans/2026-10-18-grand-monument-sites-plan-b.md): grandeur set by world wealth | #1059 |
| [plans/2026-10-18-gm-sites-inventory/](archive/plans/2026-10-18-gm-sites-inventory/): four read-only code maps behind the sites plans (line numbers are as of `823dc25c`) | — |
| [plans/2026-10-23-tourism-heritage-phase1.md](archive/plans/2026-10-23-tourism-heritage-phase1.md): tourism heritage phase 1, monument tourism as output and the heritage of existing monuments out of base appeal | #1118 |
| [specs/2026-10-23-gm-policy-prestige-design.md](archive/specs/2026-10-23-gm-policy-prestige-design.md) and [plan](archive/plans/2026-10-23-gm-policy-prestige.md): four monument policies, each best at one thing; no upkeep, so Mothballed and Standard go; prestige +10 and +1% a step | #1121 |
| [specs/2026-10-23-tourism-heritage-design.md](archive/specs/2026-10-23-tourism-heritage-design.md), with its [moves](archive/specs/2026-10-23-tourism-heritage-moves.csv) and [monuments](archive/specs/2026-10-23-tourism-heritage-monuments.csv): monument tourism as output, and the heritage a monument stands for leaves base appeal while the monument can exist; the To History dedication, 51 landmarks of 1836 and 14 sites (pass 1; its As built notes record the builder's corrections; pass 2, townscapes, is a later project) | #1118, #1139 |

### Global Commons and seabed claims

| Doc | Shipped in |
|-----|------------|
| [specs/2026-10-16-global-commons-design.md](archive/specs/2026-10-16-global-commons-design.md): seabed licences, Law of the Sea, the Antarctic Treaty, launch windows, orbital debris (`CLAUDE.md` cites its §§ 2.3, 5.2, 5.2a as the design-default examples) | #1002 |
| [specs/2026-10-17-seabed-claims-and-panel-design.md](archive/specs/2026-10-17-seabed-claims-and-panel-design.md): seabed claims, leases and the Seabed panel | #1011, #1017, #1019 |
| [plans/2026-10-17-seabed-claims-phase1.md](archive/plans/2026-10-17-seabed-claims-phase1.md), [phase 2](archive/plans/2026-10-17-seabed-claims-phase2.md), [phase 3](archive/plans/2026-10-17-seabed-claims-phase3.md): claim rules and the panel; leases, island coast, subjects; navies and the rush | #1011, #1017, #1019 |

### Space Race

| Doc | Shipped in |
|-----|------------|
| [specs/2026-10-25-solar-colonization-contest-scope.md](archive/specs/2026-10-25-solar-colonization-contest-scope.md): scope for contested solar colonies (holder records, cession by treaty, fleets with a location and real transit times, blockades and sieges), colony population as crews, modules and Extraplanetary Bases from colonies, and four levels of the Space Race rule; slices 0 to 6, the slice designs under Active above and the fleets design below (its § 10's other ideas are for later) | #1140, #1145, #1157, #1172, #1179, #1192, #1193 |
| [specs/2026-10-26-solar-colonization-fleets-design.md](archive/specs/2026-10-26-solar-colonization-fleets-design.md) and [plan](archive/plans/2026-10-26-solar-colonization-fleets.md): slice 6, Full Colonies' fleets: Space Command and five ship roles, legs between nine locations, combat by posture under the square law, Defences and integrity, blockades, seizure, destruction, war support, Survey Colony Defences, interdiction in peace, the outer-space convention, and Earth orbit (the ground reserve, ground-to-orbit batteries, Earth's blockade, orbital fire support); Full Colonies the default. Its §§ 22-24 record the build; the play-test list is `docs/testing/solar-colonies-playtest.md` | #1173 (design), #1179 (6a, 6b), #1192 (6c), #1193 |

### Colonial Empire

| Doc | Shipped in |
|-----|------------|
| [specs/2026-10-24-colonial-criteria-and-independence-wars-design.md](archive/specs/2026-10-24-colonial-criteria-and-independence-wars-design.md): what a colony is from first principles (UN Resolution 1541: separated, distinct, subordinated), and a war of independence a colonizer can choose to fight; § 10 says what the build settled | #1130 |

### Other systems and tooling

| Doc | Shipped in |
|-----|------------|
| [specs/2026-10-21-transport-goods-design.md](archive/specs/2026-10-21-transport-goods-design.md) and [plan](archive/plans/2026-10-21-transport-goods.md): Transportation inside a state, Merchant Marine between markets, infrastructure per railway and port level, and the AI stops subsidizing railways and ports (#1050) | #1095 |
| [specs/2026-09-26-collective-governance-design.md](archive/specs/2026-09-26-collective-governance-design.md) and [plan](archive/plans/2026-09-26-collective-governance.md): Direct Democracy generalized into Collective Governance | #482, #516 (#841, #871) |
| [specs/2026-09-26-internal-resettlement-design.md](archive/specs/2026-09-26-internal-resettlement-design.md) and [plan](archive/plans/2026-09-26-internal-resettlement.md): the Settlement Authority | #500, #518, #743 |
| [specs/2026-10-17-national-modifiers-tab-design.md](archive/specs/2026-10-17-national-modifiers-tab-design.md) and [plan](archive/plans/2026-10-17-nation-tab.md): the Nation tab | #1021, #1031, #1039 |
| [specs/2026-10-17-economy-growth-sim-design.md](archive/specs/2026-10-17-economy-growth-sim-design.md) and [plan](archive/plans/2026-10-17-economy-growth-sim.md): the yearly economy model (its hindcast misses; see `docs/systems/economy_growth_sim.md`) | #1037, #1040 |
| [specs/2026-10-16-ai-managed-flat-staff-design.md](archive/specs/2026-10-16-ai-managed-flat-staff-design.md): AI-managed methods with a flat human crew | #993, #996 |
| [specs/2026-09-26-icon-pipeline-design.md](archive/specs/2026-09-26-icon-pipeline-design.md): FLUX-generated UI icons; every category in its inventory is done, and the pipeline stays in use | #504 … #908 |
| [plans/2026-05-04-event-magnitude-audit.md](archive/plans/2026-05-04-event-magnitude-audit.md): the event magnitude audit | 2026-05-04 commits `4c92a960`…`b12b53e2` (before PRs) |

`archive/specs/assets/` holds the icon pipeline's prototype sheets and the seabed panel's layout mock-ups.

### Loose ends in archived docs

Nothing below blocks its doc's archiving. Each is out of scope by the doc's own terms, an owner call, or tracked elsewhere. They're listed so they aren't lost in the archive:

- **Nuclear loose warheads:** buying loose warheads (§0.10 step 5's phase 2) is unbuilt. The owner never confirmed the spec's "Calls made without the owner" list, and two review questions are open: may a former parent press its own secession, and should a terror detonation apply the UN world-order shock?
- **Tax code AI and release:** §2.9's customs follow-up (native control and the AI customs template) waits on an owner call. The P09b lock didn't bind and the P09c carrier depends on the tariff level (`docs/testing/tax-code-capability-ledger.md`, Known limitations).
- **Demographics calibration step 3:** call 4 (the USA's births, Japan's long life) and the building-scope choice that reopened when `working_conditions_read` read BROKEN. The owner parked both on 2026-10-18 (#894).
- **Demographics modifier types:** issue #1010 (where the Wealth Concentration types live) is open, and so are #1067 (the migrant profile's family weight saturates, so labour migrants fall to zero late) and #1072 (an audit for modifier fields with no loc). Owner call 5 (#822's inheritance targets) was declined.
- **Demographics uploaded minds:** the Devout's switch stays off until a play-test sizes it (`docs/testing/demographics-playtest.md` § Uploaded minds).
- **Demographics engine rates and engine lines:** small follow-ups in open issue #1046.
- **UN GUI:** round 2 (one visual row per mission, mandate and archive item) never got a spec.
- **Nation tab:** moving Nuclear Power onto its journal entry (§6) was deferred by the owner; `KEEP_IN_LIST` holds `nuclear_power` until then.
- **Seabed claims:** Seabed Sabotage is deferred to v2 by the owner.
- **Banking always-on:** the §10 open points (restructuring before the start, Credit Standing under Simplified, monetary history before the start).
- **Judiciary:** Phases 2–4 were built before phase 1's play-test, at the owner's request; § 14.4 lists the calls made without the owner (the strike-down thresholds, the amendments' parents and sizes, the landmark cases' triggers), and `docs/testing/judiciary-playtest.md` § Phases 2–4 the engine facts the build rests on.
- **Covert tech theft:** the retired espionage modifiers are marked "PENDING REMOVAL one release after 2026-10-06/07" in `mod_systems/covert_warfare.md`.
- **Grand Monuments:** the archaeology spec's deferred list (political brakes, speculative breakthroughs, special-site events); the trophies spec's UN topic for cultural property; signatures' Muses family and further historical opportunities; no landmark row yet uses `gm_seed_landmark_beside`. The policy pass's audit gap, a `ScriptValue('x')` in loc or a GUI that names no script value, is open #1120.
- **Transport goods:** two fallbacks wait on the observer run in `docs/testing/ai-economy-playtest.md`: the `REPLACE:building_railway` whose shortfall branch ignores staffing (§ 3.1), if states stay short of Transportation, and construction's input handed back to Merchant Marine (§ 2), if construction hubs choke.
