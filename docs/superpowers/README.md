# Plans and specs: index

This folder holds the design specs (`specs/`) and implementation plans (`plans/`) written with the brainstorming and `/writing-plans` workflows. Each file is dated by when it was written. Once everything a doc set out to build is on `main`, it moves to `archive/`, keeping its `plans/` or `specs/` subfolder.

Status was checked on 2026-10-19 against `main` at `67dca09`. Each doc was checked against the code and the merged PRs, not its own checkboxes, which are mostly never ticked. A doc counts as done when everything it commits to has shipped. Items it calls out of scope or ideas for later don't count against it, and neither do in-game play-tests, since those don't gate a merge (`CLAUDE.md`). Shipped systems are documented in `docs/systems/` (mostly `mod_systems.md`) and their in-game checks in `docs/testing/`. Read those for how a system works now: an archived spec records the design and reasoning, and later work may have changed it.

**Keeping this current:** when a doc's last piece ships, `git mv` it into `archive/`, rewrite every reference to its old path (`git grep -n "superpowers/specs/<name>" -- ':!gfx'`, which covers comments in `common/`, `gui/`, generators and tests), and move its row from Active to Archived below.

## Active

### Demographics

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-10-08-demographics-design.md](specs/2026-10-08-demographics-design.md): the master design (census by age and sex, fertility, causes of death, Wealth Concentration, Gini, urban pattern, panel, rule, phases 0–3) | Partial: phases 0–3 built (phase 0 #828, phase 1 #830, then the phase 2 and 3 PRs through #947) | §5.2 per-state metropolitan share (owner: lowest priority, the event wave uses a stand-in); Internal Resettlement programme profiles (§2.5/§6, moves still go to the migration residual); upward and event-driven Wealth Concentration shocks (§4.2); the r > g term; §2.6's young, male US frontier start; §7's Inequality effect. Map modes are blocked and sit in no phase. `mod_systems.md` § Demographics lists the first three as remaining work |
| [specs/2026-10-09-demographics-modifier-types-design.md](specs/2026-10-09-demographics-modifier-types-design.md): census inputs from laws, techs and institutions as script-only `state_*` modifier types, in three stages | Partial: stages 1–2 built (#850, #852), stage 3 in part (#1009) | Stage 3's `country_female_work_share_add` (`FEMALE_WORK_SHARE` is still a params table) and `country_family_migration_add` (`FAMILY_TRANSPORT_TECHS` in `demographics_params.py`). Owner call 5 (#822's inheritance targets) was declined. Issue #1010 (where the Wealth Concentration types live) is open. Build these or drop them, then archive |
| [specs/2026-10-10-demographics-late-marriage-design.md](specs/2026-10-10-demographics-late-marriage-design.md): Late Marriage and Birth Spacing, two fertility customs with per-state shares, drift and neighbour spread | Partial: phase 2 (#931) and the phase 3 spread (#945) built; plan archived | Phase 3's minimum-marriage-age lever (§6, call 9: no `state_late_marriage_target_add` type, no law carries one) and §2.5's age schedule blended by the shares (the late game added a postponement shift but holds it at 0) |
| [specs/2026-10-16-demographics-uploaded-minds-design.md](specs/2026-10-16-demographics-uploaded-minds-design.md): an "uploaded minds" pool beside the census, and Mind Backups' restore scaled by longevity care | Open: proposal, nothing built | The eight owner calls in §7, then the §8 build. Mind Backups is still a flat −0.5 |
| [plans/2026-10-10-demographics-phase2-calibration.md](plans/2026-10-10-demographics-phase2-calibration.md): the six calibration steps phase 2 needs, plus a gate | Partial, parked: steps 1–4 built (#855, #857, #930, #869), step 5 dropped by the owner | Step 6 (refit the post-1900 schedules against Clio Infra) was never built as a step, though #979 and #1051 cover part of it. The gate's regional items (USA and Canada, Southeast Asia, Europe's flat death rate, India 1837–62) were not met. The owner parked the remaining calibration on 2026-10-18 when closing #894 |

### Legislated tax code

The first playable milestone shipped behind the experimental, default-off `te_tax_code_rule` in #680. The AI and release design (packages 6–7) and the Light code are archived.

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-09-29-legislated-tax-code-design.md](specs/2026-09-29-legislated-tax-code-design.md): the umbrella design (draft, bill, interest-group bargain, commencement, obligations, estimates, AI, civil-war continuity) | Partial: §12 steps 1–4 built (#641, #648, #680, #845) | §12 step 5 (customs and treaty integration, delegation, parliamentary and presidential procedures); step 6 (advanced instruments, behavioural forecasts); promise kinds beyond the four; the carbon tax as one source of truth; the §14 decisions |
| [plans/2026-09-30-legislated-tax-code.md](plans/2026-09-30-legislated-tax-code.md): the package-level plan, packages 0–8 | Partial: packages 0–7 built | Package 8 (catalog expansion: political-reform, colonial, monetary and restraint promises, advanced instruments) and package 3's split of the carbon effects |
| [plans/2026-10-02-legislated-tax-code-tasks.md](plans/2026-10-02-legislated-tax-code-tasks.md): Tasks 1–17 for packages 1–5 | Partial: Tasks 1–15 built (#680), Task 17 replaced by the 10-03 plan's Tasks 25–27 | Task 16, the carbon levy. Only its numbers exist (`docs/systems/carbon_levy_numbers.md`, "parked until #674", which has since landed). `carbon_tax_modifier` is unchanged |

### Laws

| Doc | Status | What's left |
|-----|--------|-------------|
| [specs/2026-10-08-inheritance-laws-design.md](specs/2026-10-08-inheritance-laws-design.md): the inheritance group redesign (new laws, four amendments, Wealth Concentration, rural births, generation events) | Partial: built in #822, balanced in #843 | §5's three second-wave events: *The Hidden Estates* (State as Universal Heir), *The Empty Holding* (Possession by Use), *The First Cohort* (Birthright Endowment) |
| [specs/2026-10-17-judiciary-design.md](specs/2026-10-17-judiciary-design.md): the Judiciary law group (six court laws, Judicial Independence, entrenchment, overhaul shock) | Partial: phase 1 built (#1022, #1025; plan archived); the Nation tab hand-off shipped (#1021) | Phase 2, defying the court (challenge, comply, defy or pack); phase 3, seven amendments; phase 4, landmark cases. Each gets its own plan after the phase 1 play-test |

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
| [plans/2026-10-17-judiciary-phase1.md](archive/plans/2026-10-17-judiciary-phase1.md): Judiciary phase 1 (the spec stays active for phases 2–4) | #1022 (#1025) |
| [plans/2026-10-02-drugs-phase-2-healthcare-demand.md](archive/plans/2026-10-02-drugs-phase-2-healthcare-demand.md): the Healthcare need and opium plantation penalties | #656 (#657, #658) |

### Demographics

| Doc | Shipped in |
|-----|------------|
| [plans/2026-10-08-demographics-phases-0-1.md](archive/plans/2026-10-08-demographics-phases-0-1.md): the age model, harness, census, tab and rule | #828, #830 (#833) |
| [specs/2026-10-12-demographics-phase2-consequences-design.md](archive/specs/2026-10-12-demographics-phase2-consequences-design.md): what the census feeds (interfaces; workforce, pensions and health; Family Policy; conscription and sex balance) | #925, #932, #935, #938, #940, #942, #946 (#989) |
| [plans/2026-10-12-demographics-phase2-interfaces.md](archive/plans/2026-10-12-demographics-phase2-interfaces.md): phase 2 step 1, the interfaces, changing no number | #932 |
| [plans/2026-10-10-demographics-phase2-engine-rates.md](archive/plans/2026-10-10-demographics-phase2-engine-rates.md): calibration step 4, the census sets the engine's births and deaths | #869 (#876, #885, #889, #900, #904, #907, #913) |
| [plans/2026-10-11-demographics-engine-lines-script-only.md](archive/plans/2026-10-11-demographics-engine-lines-script-only.md): the engine's birth and death lines as script-only types | #892 |
| [specs/2026-10-12-demographics-calibration-step3-design.md](archive/specs/2026-10-12-demographics-calibration-step3-design.md): the regional mortality gap | #930 |
| [specs/2026-10-12-demographics-fast-mode-revenue.md](archive/specs/2026-10-12-demographics-fast-mode-revenue.md): should fast mode pay the AI's bills? (decided: no) | #922 (the subsidy follow-up: #980, #981) |
| [plans/2026-10-09-demographics-modifier-types-stage1.md](archive/plans/2026-10-09-demographics-modifier-types-stage1.md): modifier types stage 1, mortality | #850 |
| [plans/2026-10-10-demographics-modifier-types-stage2.md](archive/plans/2026-10-10-demographics-modifier-types-stage2.md): modifier types stage 2, fertility | #852 |
| [plans/2026-10-10-demographics-gini-wealth-bands.md](archive/plans/2026-10-10-demographics-gini-wealth-bands.md): Gini by wealth band | #854 (#860, #867) |
| [plans/2026-10-11-demographics-causes-of-death.md](archive/plans/2026-10-11-demographics-causes-of-death.md): Causes of Death, medicine that spreads, turmoil's violence | #916 (#921, #929; country tab #1041) |
| [plans/2026-10-11-demographics-late-marriage.md](archive/plans/2026-10-11-demographics-late-marriage.md): Late Marriage and Birth Spacing, phase 2 scope (the spec stays active) | #931 |
| [specs/2026-10-11-demographics-late-game-design.md](archive/specs/2026-10-11-demographics-late-game-design.md): old age, work, children and who lives longest | #932, #940, #942, #946, #947, #962 (#979, #989, #1006, #1051) |

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

### Global Commons and seabed claims

| Doc | Shipped in |
|-----|------------|
| [specs/2026-10-16-global-commons-design.md](archive/specs/2026-10-16-global-commons-design.md): seabed licences, Law of the Sea, the Antarctic Treaty, launch windows, orbital debris (`CLAUDE.md` cites its §§ 2.3, 5.2, 5.2a as the design-default examples) | #1002 |
| [specs/2026-10-17-seabed-claims-and-panel-design.md](archive/specs/2026-10-17-seabed-claims-and-panel-design.md): seabed claims, leases and the Seabed panel | #1011, #1017, #1019 |
| [plans/2026-10-17-seabed-claims-phase1.md](archive/plans/2026-10-17-seabed-claims-phase1.md), [phase 2](archive/plans/2026-10-17-seabed-claims-phase2.md), [phase 3](archive/plans/2026-10-17-seabed-claims-phase3.md): claim rules and the panel; leases, island coast, subjects; navies and the rush | #1011, #1017, #1019 |

### Other systems and tooling

| Doc | Shipped in |
|-----|------------|
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
- **Demographics engine rates and engine lines:** small follow-ups in open issue #1046. Fast mode's leftover AI insolvency is open #1050.
- **UN GUI:** round 2 (one visual row per mission, mandate and archive item) never got a spec.
- **Nation tab:** moving Nuclear Power onto its journal entry (§6) was deferred by the owner; `KEEP_IN_LIST` holds `nuclear_power` until then.
- **Seabed claims:** Seabed Sabotage is deferred to v2 by the owner.
- **Banking always-on:** the §10 open points (restructuring before the start, Credit Standing under Simplified, monetary history before the start).
- **Judiciary phase 1:** the six law icons still need their final render on the owner's GPU machine, and the laws use placeholder icons until then.
- **Covert tech theft:** the retired espionage modifiers are marked "PENDING REMOVAL one release after 2026-10-06/07" in `mod_systems.md`.
- **Grand Monuments:** the archaeology spec's deferred list (political brakes, speculative breakthroughs, special-site events); the trophies spec's UN topic for cultural property; signatures' Muses family and further historical opportunities; no landmark row yet uses `gm_seed_landmark_beside`.
