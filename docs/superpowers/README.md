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
| [specs/2026-11-20-nuclear-delivery-and-survivability-design.md](specs/2026-11-20-nuclear-delivery-and-survivability-design.md): survivability as a product of its parts in place of the flat ceiling, silos weaker against precision weapons, ICBMs and missile submarines fielded through programme projects, and every value a nuclear decision rests on shown to the player | Phase 1 built, the model and the display (2026-11-20, `nuclear_crisis_design.md` §0.18); phase 2 built, the projects and what the panel tells of them (2026-11-21, §0.19, §0.20); the owner's calls in its §1 answer every open question | §10's later work (thermonuclear weapons, strategic defense, the projects' development events), with no plan yet |
| [plans/2026-11-20-nuclear-delivery-phase1.md](plans/2026-11-20-nuclear-delivery-phase1.md): phase 1 in two PRs, the model (one trigger per delivery leg, survivability as a product, precision weapons as modifiers, the world's view) then the display (Forces, posture, strike previews, crisis and decision figures) | Built: PR 1a (Tasks 1–4) and PR 1b (Tasks 5–9), 2026-11-20 | Nothing; phase 2 gets its own plan |
| [plans/2026-11-20-nuclear-delivery-phase2.md](plans/2026-11-20-nuclear-delivery-phase2.md): phase 2 in two PRs, the projects (the focus and parked progress, the legs on fielded variables with a migration, the holds, the notices, the AI's range score) then what the panel tells (each focus's grants in figures, others' delivery in Nuclear Powers and National Info) | Built: PR 2a (Tasks 1–5) and PR 2b (Tasks 6–7), 2026-11-21 | Nothing |

### Space Race

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-10-25-solar-colonization-holders-and-cession-design.md](specs/2026-10-25-solar-colonization-holders-and-cession-design.md): slices 0 and 1, a holder record for every world (the panel's Solar System list, a dead holder's colonies passing to its capital's owner), four settings of the Space Race rule, and the Cede Colony treaty article; [plan](plans/2026-10-25-solar-colonization-holders-and-cession.md) | Built 2026-10-25 (slices 0 and 1, one PR); as built in the design's § 17 | The play-test list (`docs/testing/solar-colonies-playtest.md`) and its three self-checks |
| [specs/2026-10-25-solar-colonization-population-and-transit-design.md](specs/2026-10-25-solar-colonization-population-and-transit-design.md): slices 2 and 3, a Target button on every world (all settings), transit tables for four drives in the launch-window generator, colony fleets that travel and claim on arrival with distance in place of the stages, colony population with an emigration programme, per-colony priorities, crews and Artificial General Intelligence, and the Off-World Population bonus (simple and full colonies); the build order is its § 14 | Built 2026-10-25 (slices 2 and 3, one branch); as built in its § 15 | The play-test list's slices 2-3 part (`docs/testing/solar-colonies-playtest.md`) and its two self-checks |
| [specs/2026-10-25-solar-colonization-modules-and-bases-design.md](specs/2026-10-25-solar-colonization-modules-and-bases-design.md): slice 4, colony modules (the two specializations sharing four levels, Habitat, and Defences and Spaceport as placeholders), crews and staffing, the Space Program's Module Fabrication method group with a queue, shipments that wait for windows and travel, and Extraplanetary Base room from the near-Earth asteroids and colonies with per-world grades and a penalty past it (simple and full colonies); the build order is its § 14 | Built 2026-10-25 (slice 4, one branch); as built in its § 15 | The play-test list's slice 4 part (`docs/testing/solar-colonies-playtest.md`) and its two self-checks; the grades and costs at a first guess (M1) |
| [specs/2026-10-29-lunar-colonization-design.md](specs/2026-10-29-lunar-colonization-design.md): the Moon Base milestone retired into six lunar worlds at Solar System Colonization's stage 0 (founded the month the fleet leaves, the first lunar colony keeping the Moon Base's first), colonization opened in era 10 by Cislunar Infrastructure with worlds beyond the Moon on the Mars Landing, the Extraplanetary Base from era 10 (In-Situ Resource Utilization, Regolith Processing), lunar worlds assaultable at Earth under Full Colonies, Nuclear Thermal Propulsion as a smaller off-window premium, higher stage goals, and funding past the cap with diminishing returns; the build order is its § 13 | Built 2026-10-29 in #1233–#1238 (PR4 funding past the cap, PR1 the technologies and the era-10 base, 3a Nuclear Thermal Propulsion, 2a six lunar worlds, 3b lunar worlds at Earth, 2b the Moon Base retired), #1239 the wording (colony sites are "sites"); as built in its § 16, with the owner's answers to § 15 | The play-test list's lunar parts (`docs/testing/solar-colonies-playtest.md`) and their self-checks; the owner's open calls in its § 16 |
| [specs/2026-10-26-solar-colonization-free-colonies-design.md](specs/2026-10-26-solar-colonization-free-colonies-design.md): slice 5, colony autonomy (a monthly drift from people, distance by drive, isolation, war and garrisons; a demand at 75 answered by a charter, a garrison or freedom; breaking away at 100), free colonies that wait and trade (supply, trade and ties, a petition to rejoin at full ties), abandonment (people home or left free), a dead holder's peopled worlds left free, Incite Colonial Autonomy and Sabotage Colony, three colony life events, and Simple Colonies as the rule's default; the build order is its § 13 | Built 2026-10-26 (slice 5, one branch) | The play-test list's slice 5 part (`docs/testing/solar-colonies-playtest.md`) and its self-check; the drift's terms at a first guess |
| [specs/2026-10-30-colony-management-design.md](specs/2026-10-30-colony-management-design.md): the owner's play-test notes on the Colonies section: the AI tends and prices its colonies, autonomy settles and builds a colony's own modules, slots grow with technology with a rising price past them, ten facility modules, Next Windows as a table, and the colony boxes and a colony's page; the build order is its § 10 | Built 2026-10-30 in #1257; #1258 finished § 4.1's colors and § 5's slot technologies as markers (five of them), made the drives markers, and took the owner's review of the panel (vanilla's underlining, the name as a button, a colony's page rebuilt, each site's slots and base room in Solar System, the race to the Moon explained); as built in its § 11 | The play-test list's colony management part (`docs/testing/solar-colonies-playtest.md`) and its two self-checks (`drive_marker`, `slot_marker`); the owner's calls in its § 11, fine for now |
| [specs/2026-11-05-extraplanetary-base-ground-types-design.md](specs/2026-11-05-extraplanetary-base-ground-types-design.md): seven ground types (Mixed, Metallic, Rocky, Carbonaceous, Sulfurous, Hydrocarbon, Icy) in place of the single Extraplanetary Base grade, a site being its type and grade (the grade as throughput, the type's mix as a per-building output multiplier that averages to zero), one basket of seven goods for the four mining methods, and where the levels work: a Bases view in Colonies where a player assigns levels to sites, or a checkbox (on by default, the AI's) that moves them at the margin for the most profit a level, every move at a quarter of the base a year | Built (2026-11-21, `feature/ebase-ground-types`); the design rewritten 2026-11-21 after the review and the owner's brief on #1397, the owner's answers in its § 12, and what the build changed in its opening "Built" paragraph | The play-test items in `docs/testing/solar-colonies-playtest.md`; the Resort Colony left in #1950 |
| [plans/2026-11-21-extraplanetary-base-ground-types.md](plans/2026-11-21-extraplanetary-base-ground-types.md): the build in ten tasks over the design's five stages: the types and site map, the basket, the mix modifiers, the month as a Python model, the generated values and per-building mix on today's order, where the levels work in script, the checkbox and buttons with the forecast and notice, the Bases view, the other readings, docs and the guide | Built (2026-11-21, `feature/ebase-ground-types`), with a fixed-point twin of the generated month against the Python model (`test_ebase_assignment.py`) | None |
| [specs/2026-11-22-colony-people-and-off-world-tourism-scope.md](specs/2026-11-22-colony-people-and-off-world-tourism-scope.md): a scope in two parts. A: the Resort Colony's Tourism stops following its Earth state (a modifier on the building cancels the state's share of Tourism output; the country's share and the Spaceport's throughput stay), answering #1953. B: a colony's people, not its slots, limit its modules (slots removed, the Habitat the one capped module, the five slot technologies giving people per Habitat, Artificial Intelligence shrinking crews instead of waiving them, settlers bought with Launch Capacity without a fixed top, autonomy as the limit on a large colony, a panel that shows crews needed against crews available) | Scope (2026-11-22), with the owner's decisions of that day and answers to all ten open calls (§ 5) | Part A: built (#1957). Part B: built, its PR open (the row below) |
| [specs/2026-11-22-colony-people-limit-modules-design.md](specs/2026-11-22-colony-people-limit-modules-design.md): Part B of the scope above. Slots go and crews (10,000 people, 5,000 with Artificial Intelligence) limit modules; the Habitat is the one capped module (the world's old slots, past them at a rising price the module stock must hold); the five slot technologies give +10 points of Habitat room each; settlers are an amount doubling from 500 a month, 3 Launch Capacity each through a multiplier on the Space Program, drawn from every state in proportion to its people (at most 1% of the country's a month) and booked in the census by Organized Colonization's profile; the AI's settlers share fabrication's 5% of weekly income; an Administration costs 25 authority a level; the panel shows crews needed against crews available and the Habitat cap where a destination is picked | Built (2026-11-22, plan `plans/2026-11-22-colony-people-limit-modules.md`), PR open | Review and merge; the play-test list's § Colony people limit modules |
| [specs/2026-11-24-space-forces-personnel-scope.md](specs/2026-11-24-space-forces-personnel-scope.md): fleets and marines limited by a new government building, the Space Forces Base (1,000 jobs a level of a new pop type, the mod's first, and +1,000 Space Forces Personnel, a script-only state type); 100 personnel a point of fleet strength (50 with Artificial Intelligence) and 1,000 a marine battalion; hulls leave the ground reserve and marines come aboard only within the headroom, in an order the player sets, and a fleet short of personnel fights at the share it can crew; occupied bases still count; ships destroyed, marines lost and a seizure's toll on the landing force kill as many of the new type in the bases' states, booked as the census's war dead; old saves get the levels they need and six months' grace | Scope (2026-11-24), with the owner's answers to all ten calls the same day (§ 10); built in one PR from the design below | See the design's row |
| [specs/2026-11-24-space-forces-personnel-design.md](specs/2026-11-24-space-forces-personnel-design.md): the scope's § 11 calls settled (Spacers, one type, lower strata, a toggle for the priority, a toll of half the defence the seizure overcomes, the job-freeing step left out) and every hook named; built as one PR | Built 2026-11-24, not yet seen in game | The owner's calls in the PR (the name, Armed Forces politics, the placeholder icons); the play-test rows and the `pers_pop_type` and `pers_kill` self-checks; the follow-ups: freeing the dead's jobs, the seizure's price in the target hover, a per-fleet priority |

### Technology

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-10-31-era-13-technology-tree-design.md](specs/2026-10-31-era-13-technology-tree-design.md): today's era 12 split into a grounded era 12 and a hard-science-fiction era 13 (costs 1.5M and 3M), Bioenhanced Soldiers up from 11, sixteen new technologies (the era 11 AI wave, Rejuvenation Therapies, Post-Work Society, Compact and Aneutronic Fusion, Von Neumann Machines, the identity line to Self-Directed Evolution), a law-group trio (Bodily Autonomy, Automation Policy, Frontier AI Control), Superintelligence reserved for its own design | Built (2026-11-01): phases 1 and 2 and all twelve of phase 3's items (§ 9); Superintelligence reserved (§ 3.5) | The observer runs (§ 4.1, `docs/testing/era-13-playtest.md`), which size the innovation budget and phase 3's first-estimate magnitudes; the play-test list; the owner's review of each PR's Decisions |

### Migration and climate

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-11-01-local-climate-design.md](specs/2026-11-01-local-climate-design.md): a climate record per state region (summer heat and humidity, winter cold, aridity, malaria, latitude) feeding a comfort penalty in migration attraction, eased by technology (cold early, then disease and water, then air conditioning) and moved by global warming; the mass migration arable land minimum removed; a Local Climate state panel tile | Phase 1 merged (#1307); phases 2–3 in the comfort PR | In-game checks (`docs/testing/local-climate-playtest.md`) |
| [plans/2026-11-01-local-climate.md](plans/2026-11-01-local-climate.md): Tasks 1–9 in two PRs (A: the record, the generator and the tile's readings; B: relief carriers, the comfort formula with warming, the modifier and defines, the Comfort row, docs) | Tasks 1–3 merged (#1307); 4–8 in the comfort PR | Task 9's whole-branch review |
| [specs/2026-11-13-regional-climate-warming-design.md](specs/2026-11-13-regional-climate-warming-design.md): Climate Warming by latitude band (#1681): Tropical Warming between the tropics and High-Latitude Warming 55° or more from the equator, state modifiers on top of the world's, refreshed from the monthly state pulse; the Warming Penalty hover, the help page and the guide | Built (#1681's PR) | In-game checks (`docs/testing/vanilla-1-15-playtest.md`, "Regional warming"); the AI climate will that reads the bands (§ 2, non-goals) |

### Power blocs

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-11-16-power-bloc-identities-design.md](specs/2026-11-16-power-bloc-identities-design.md): three new power bloc identities from the owner's brainstorm: Creditors' Consortium (the leader stands behind members' debts and rescues a defaulter on terms: receivership, imposed economic law, concessions and monopolies), Research Commons (members stop researching and send most of their innovation to the leader, and every member is granted what any member knows) and Dynastic Compact (crowned members joined to the leader in Personal Union by consent or by succession); their requirements, primary principle groups and the parts each identity touches; the build order is its § 9 | Design only (2026-11-16): the owner's rulings in its § 12 | All three identities, one PR each (§ 9); thirteen engine facts to verify (§ 11); Producers' Cartel and Climate Club tabled (§ 2) |

### Military and performance

| Doc | Status | What's left |
|-----|--------|-------------|
| [plans/2026-11-24-supply-ship-scale.md](plans/2026-11-24-supply-ship-scale.md): issue #1984's first fix scoped: supply ships ten times the size (cost, goods, capacity, hit points and, the part that shortens the readout's list, the weekly cap per ship), the three defines that change (the 1.15.2 files read), the battle size and additive cap modifiers, running games (no script read of a pool; a player-only button), and a Stage 0 that times the quick fix first | Quick fix built 2026-11-24: Naval Convoy Defense raises a supply ship's weekly cap from 5 to its cost, 25 (`test_supply_ship_progress_cap.py`); the rescale is not started | Stage 0's timing on the owner's machine; Stages 1–5 only if the quick fix isn't enough |

### Interface

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-11-02-te-window-wide-mode-design.md](specs/2026-11-02-te-window-wide-mode-design.md): a toggle between the Timeline Extended window's side-panel width and a full-screen frame, the ten system tabs that live in vanilla panels mirrored in the window (kept where they are), a wide layout for all fifteen tabs, and the standardization that keeps them maintainable (one tab frame and body type per system, the window's strip generated from a registry, shared column types and a narrow-versus-wide check) | Built 2026-11-02 in #1327–#1337 (its plan's PRs A–D), the owner's calls in its § 12 at their defaults; § 9.9's observer guard landed on its own in #1325 | § 9.7, vanilla bases for the six host overrides (on the owner's machine); the play-test list (`docs/testing/te-window-wide-playtest.md`), where § 12's columns, names and strips are judged in game |
| [plans/2026-11-02-te-window-wide-mode.md](plans/2026-11-02-te-window-wide-mode.md): PRs A–D: A the registry, the tab frame type and the window's five bodies (no visible change, no game needed), B the full-screen frame and the toggle, C the ten hosts' tabs on body types and in the window, D0 the column types and the narrow-versus-wide check, D1–D3 the wide composers | Built 2026-11-02: A #1327, B #1328, C #1330, D0 #1331, D1 #1334, D2 #1335, D3 #1333, then #1337 (a full-screen layout required on every tab) | Its "Later" section (the vanilla bases, spec § 9.7) and the play-test list |
| [specs/2026-11-02-charts-help-national-info-design.md](specs/2026-11-02-charts-help-national-info-design.md): extends the wide-mode work with a full-screen viewer for the 33 history charts, a Help popup per system in place of each collapsed "How X Works" section, and other countries' public panels in the Census Data window renamed ("National Info"), with every body bound to a `Country` and the controls shown only for the player's country | Scoping, nothing built (2026-11-02) | All of it: its § 10 build order (Help, the chart registry and viewer, then the binding rule, National Info and the systems a few at a time), and the owner's calls in its § 11 |
| [plans/2026-11-02-charts-help-national-info.md](plans/2026-11-02-charts-help-national-info.md): nine PRs in three tracks: H1–H2 the Help popups (each "How X Works" section left as a link to its page, a "?" in each tab header), C1–C2 the chart registry and generator (two wrapper types a chart) and the viewer popups, F0 every mount supplying a `Country` with the own-country guard and tests (no visible change), F1 National Info, F2–F5 the public systems bound a few per PR | Not started (2026-11-02) | All of it; the owner's calls in the spec's § 11, each defaulted in the plan |

### Tooling

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-11-10-in-game-qa-harness-design.md](specs/2026-11-10-in-game-qa-harness-design.md): a harness with which a Claude session launches Victoria 3, plays as a chosen country, runs prepared effects, fires events, picks their options from the console and reads triggers and values back, with the owner's saves and logs snapshotted and restored around every run and a permission-and-GPU gate before every launch | Design approved by the owner (2026-11-10); part 1 built and § 7's six assumptions settled in a live session the same day (§ 12: five hold, time does not advance on the country-select screen); part 2 built and run live on 2026-11-11 (§ 13: three launches, the owner's files identical afterwards each time; `try-event` passed on a real mod event) | Issue #1588's three hardenings; what § 13.3 lists as not verified live |
| [plans/2026-11-10-in-game-qa-harness-part1.md](plans/2026-11-10-in-game-qa-harness-part1.md): part 1 of the build, nine tasks in three PRs: the path constants, snapshot and restore of the owner's files, the launch gate, the Windows helper, log following, the console round trip and the debugger client, all tested without a game, then one permitted live session that settles the spec's six assumptions | Built 2026-11-10 (#1577, #1578, #1579): Tasks 1–8 with their reviews, and Task 9's live session (results in the spec's § 12). The command line gained `launch` and `watch`, which the plan did not have | Nothing |
| [plans/2026-11-10-in-game-qa-harness-part2.md](plans/2026-11-10-in-game-qa-harness-part2.md): part 2, nine tasks in three PRs: clicks and a presence reading in the helper, `launch` writing the run's playset, the generated overlay mod, the fixture, the session and its server, the verbs (`start`, `read`, `pick`, `advance`, `try-event`, `stop`, …), two live sessions, the skill | Built 2026-11-11 (#1582, #1585 and the PR with the skill and the live results): all nine tasks, with their reviews; three live launches, results in the spec's § 13. The verbs gained `remove-overlay`, which the plan did not have | Nothing |

### Actors

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-11-28-actors-firms-design.md](specs/2026-11-28-actors-firms-design.md): bodies inside and across countries that pursue interests of their own, from the owner's brainstorm: a chassis (a goal derived from the actor's position, three currencies, holdings that are built and attacked, yearly turns, routine, threshold and declared major moves, a posture per actor) and firms as the first actors on the existing companies, built out at the owner's word so the chassis can be judged: eight goals, seven kinds of holding and five chains. The trust (a cartel under the antitrust laws, buyers and courts against it, a captured regulator, a monopoly charter); pulled abroad (concessions, rivalry, a petition answered by Back, Stand aside or Forbid, and a forbidden firm's ladder up to seeking another protector); politics at home (a signed table of which laws help or burden which sectors, firms on opposite sides, stalling and speeding a law, campaign money as party momentum or as patronage under the Electoral Finance laws, a petition for a law, a press, the same money abroad); the workforce (welfare or strikebreaking, a company town); technology (research, a laboratory, espionage, under the Intellectual Property laws); relief (retrenchment, and a petition answered by Rescue, Stand aside or Let it fail); and the foundation as the source of Standing. AI countries under the same rules with every push visible; hooks for labor, movements, religious organizations and industry associations | Not built: design only (2026-11-28) | Everything: § 16's fifteen in-game probes, then § 17's phases 1 to 7; § 18 has the owner's ten rulings and the two points still open (the name, and the shape of a rescue's relief line) |

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
| [specs/2026-11-14-external-currency-tools-design.md](archive/specs/2026-11-14-external-currency-tools-design.md): the five External & Currency exchange tools given one promise each on every currency, Capital Controls and Sterilization renamed, floating versions of Sterilization and Foreign Exchange Surrender, Limit Foreign-Currency Borrowing hidden on metal at par | #1800, #1807 |

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
