# Vanilla War Reference (Victoria 3)

A primer on how the **base game's** war systems work, written for AI agents that need context before touching mod content that hooks the war/military layer (anti-war movement events, war-support modifiers, mobilization-side modifiers, treaty articles tied to war outcomes, etc.). Mod-specific systems (covert warfare, nuclear weapons, the world-war journal entry, etc.) live in `docs/systems/mod_systems.md` and `docs/systems/journal_entry_systems.md`.

> **Last verified against vanilla:** 1.13 ("The Great Wave"). When `mod_state_server` reports a different vanilla version (`/status`), assume sections may be stale until cross-checked. **Revisit this file on every vanilla bump per `docs/guides/vanilla_patch_runbook.md`.** The wiki source for this doc is roughly a week post-1.13 patch and may be slightly inaccurate in places — verify any specific name or number via the server before relying on it.
>
> **Verify before relying on names.** Modifier names, unit type IDs, and trigger names cited below should be confirmed via the mod state server (`/modifier-search?q=`, `/engine-docs/modifiers`, `/raw/CombatUnitType/<id>`) before you reference them in code. Vanilla renames things across patches.
>
> **This doc captures concepts, structure, and gameplay shape — not numerical truth.** It is *not* a source of accurate values. Specific unit stats, base rates, infamy costs, mobilization-option costs, command-limit numbers, exhaustion factors, etc. change between vanilla patches and even hotfixes; treat any number you see here as **illustrative only**. When a balance number actually matters, pull it from the source: `common/defines/`, `common/static_modifiers/<base>_modifier.txt` and similar `base_values` blocks, `common/combat_unit_types/`, `common/mobilization_options/`, `common/admiral_orders/` / `common/general_orders/`, `common/country_ranks/`, or the live tooltip in-game. The structural claims (organization is a per-formation scalar, war support is what gates a war's duration, supply is HQ-routed and Supply-Ship-consumed) are what this doc is designed to be reliable about — not the numbers attached to them.

## 1. Diplomatic plays

Most wars in Victoria 3 begin with a **diplomatic play**. The country starting the play is the **initiator**; the country receiving the demand is the **target**. These are the **primary participants**. Most plays require an active interest in the strategic region the demand targets, and they cannot be started against countries with cordial-or-better relations, an outstanding obligation, an existing truce, or a subject/overlord relationship with the initiator.

Starting a play creates a diplomatic incident that damages relations with all interested countries proportional to the infamy cost of the chosen war goal.

Non-autonomous subjects (puppets, vassals, personal unions) cannot start plays except for independence, automatically join their overlord's plays, and have the overlord take control if they're targeted. Autonomous subjects (protectorates, tributaries) can join plays only if they qualify normally as potential participants.

### 1.1 Phases

A diplomatic play has three phases driven by an **escalation** value (a 0–100 scalar that climbs each day):

- **Opening Moves** (low escalation) — target sets first demand free. Both sides add demands and promote them to primary. Only overlords / non-autonomous subjects of primary participants auto-join. Other countries can lean. Neither side can back down.
- **Diplomatic Maneuvering** (mid escalation) — other potential participants join, lean, declare neutrality, or remain neutral. Sways are exchanged. Either side can back down.
- **Countdown to War** (high escalation) — sides locked in; no new demands or sways. Only `back down` / `give in` actions remain.

Each demand or sway pauses escalation for a few days (with a cap when batched), so a play takes a few months to escalate to war if neither side backs down. Specific phase thresholds and pause durations are in `common/defines/`.

### 1.2 Maneuvers

Maneuvers gate how many demands and sways a primary participant can make. Base count scales with rank — great powers get the largest pool, scaling down through major / minor / insignificant. Various technologies add maneuvers (the philosophy chain has historically been the home for these adds). **As of 1.13, maneuver-from-tech bonuses scale against your base maneuvers from rank**, so a great power in the late game ends up with a much larger absolute pool than the small flat additions of older patches would suggest. Pull the current per-rank base, the per-tech adds, and the scaling formula from `common/country_ranks/` and the relevant tech files when an actual number matters.

### 1.3 Primary vs secondary demands

- **Primary demands** are enforced if the other side backs down or gives in before war.
- **Secondary demands** are only enforceable through a peace deal or capitulation.

The initial demand and the target's first demand are automatically primary. Sways against the primary participants are primary; sways against backers are secondary. Promoting a demand to primary costs additional maneuvers and infamy on top of its base cost. Demands cannot be removed or demoted.

If a war goal is not pressed in the final peace deal, the infamy generated by adding it is partially or fully refunded.

### 1.4 Sways

Sways are demands or [obligations](#) offered to potential participants for support. Each sway costs maneuvers from the offering side — offering an obligation, calling in an existing obligation, and adding a demand-as-sway each have their own per-action cost. Pull current values from `common/diplomatic_actions/` if it matters.

Acceptance is computed from the swayed country's **Preference** (relations, attitudes, ideology, power-bloc membership, sympathy) minus the higher of (Preference for the opposing side) or (a **Neutrality** value driven by army strength, turmoil, truces, AI strategy). The engine also has a strong override the AI uses to decline proposals it judges unachievable.

Autonomous subjects can only be swayed via the *Liberate Subject* war goal, and only if their attitude is `rebellious` — otherwise they auto-join the overlord regardless of displayed preference.

### 1.5 War goals

Each war goal carries an **objective**: fulfilling it accelerates the enemy's war-support loss, and war support cannot drop below 0 while any unfulfilled war goal targets that enemy. Occupying the target country's capital is a universal objective for all war goals against it.

Common regular war goals (verify infamy/maneuver costs via the server, since they're balance levers):

- **Annex Country / Annex Subject** — annex the target. Highest infamy. Requires insignificant-or-worse target for non-subject annexation.
- **Conquer State / Return State** — cede a single state. Return State requires an existing claim on the state and bypasses the normal interest requirement.
- **Take Treaty Port** — converts/cedes a coastal state as a treaty port.
- **Make Dominion / Make Protectorate / Make Tributary** — turn an independent target into a subject. The valid type depends on initiator/target rank, recognition status, and whether the target is colonial.
- **Liberate Country / Liberate Subject** — release a country (releasable nation, or a third-party subject of the target).
- **Increase Autonomy / Independence** — used by subjects against their overlord. Requires sufficient liberty desire and a recent rejected diplo request.
- **Reduce Autonomy / Transfer Subject** — used by overlords or rivals against subjects.
- **Humiliation** — applies a multi-year penalty modifier reducing the target's prestige and leverage generation, and locks them out of opposing plays during the penalty window.
- **Ban Slavery / Open Market** — force a law change.
- **Force Nationalization** — nationalize all foreign-owned buildings.
- **Investment Rights** — gain investment rights in the target (requires Sphere of Influence or Charters of Commerce DLC).
- **Join Power Bloc / Leave Power Bloc** — bloc membership coercion.
- **Cut Down to Size** — pariah-only goal. Releases all subjects and recently conquered states; cancels the target's other war-goal claims.
- **Regime Change** — target's IGs are reshuffled toward initiator's. Requires sufficient ideological distance.
- **Revoke Claim** — removes a target claim.

Special / event-only war goals: **Colonization Rights**, **Native Uprising**, **Revoke All Claims**, **Revolution** (annex other side of civil war), **Secession**. These are added programmatically and don't follow the normal infamy/maneuver shape.

The mod adds unification war goals (Pan-X major-unify, X-Leadership candidate-suppression). Those live in `common/diplomatic_plays/te_unification_plays.txt`; consult that file rather than this section for behavior.

## 2. Formations: armies and fleets

A country's military is organized into **formations**: armies (land) and fleets (naval). Each formation has a home HQ (a strategic region) and can be stationed at other HQs or deployed to fronts/sea nodes.

- **Home HQ** gives a substantial attrition reduction. Significant for any deployment beyond a country's borders.
- **Armies** at a front can `advance` or `defend`; must be mobilized to participate in battles. An army without a general can defend a front, but degrades past 10 battalions.
- **Fleets** at a sea node can `intercept`, `raid supply lines`, `protect supply lines`, `blockade`, `project power`, `port bombardment`, `hunt pirates`, `privateer`, or (unrecognized only) `piracy`. Fleets are always mobilized when deployed and always require an admiral. (1.13 renamed "raid/escort convoys" to "raid/protect supply lines" to match the new Supply Ships system; see § 9.8.)

### Organization

Formations have an **organization** value (a percentage, with 100% = fully effective and 0% = collapsed). Reductions come from:
- changing mobilization options
- exceeding command limit
- having more than the engine's threshold of "special" units in the composition
- being in supply shortage

Penalties scale linearly between full and zero organization. They cut combat effectiveness (offense, defense, blockade strength, supply-line raid/protect efficiency), morale recovery, and recovery rate — combat-effective at 100%, severely degraded by ~0%.

Organization regenerates at a slow per-day rate when not under penalty, with a smaller rate for formations over command limit. Some technologies boost regen. Organization above the cap (e.g. after a mobilization-option change) decays back down per tick. Specific regen rates and penalty curve are in `common/defines/`.

## 3. Land units: battalions and conscripts

### Barracks and conscription centers

Battalions come from **Barracks** (regulars, standing) or **Conscription Centers** (conscripts, only during wars/plays). Both are auto-built when battalions are added to an army — not manually placed. Each level employs 1000 individuals, split between Servicemen and Officers, and produces one battalion at full employment.

Conscription centers spawn instantly on activation (no construction queue), pull pops from other buildings, and hire faster than barracks. Their max level depends on the state's workforce and the country's Army Model law.

### Army Model laws

The four Army Model law variants each shift four axes: max barracks count, max conscription centers, conscription rate, and morale-loss / experience modifiers. Qualitatively:

- **Peasant Levies** — wide conscription base but morale and experience penalties. **Conscripts can only be Irregular Infantry — not Artillery, Cavalry, or modern infantry types.** This is the structural difference, not just balance.
- **Professional Army** — narrow conscription base, big improvements to morale loss and experience gain. The "fewer-but-better" shape.
- **National Militia** — heavy conscription centers and conscription rate, smaller morale-loss benefit.
- **Mass Conscription** — both barracks and conscription centers expanded; faster training rate but morale-loss penalty.

Conscription rate stacks additively from several sources: Army Model + the `enlistment_efforts` decree + the `national_guard` law (scaled by Home Affairs institution level), reaching a base around 10–12% in extremes. Multiplicative modifiers exist separately (military techs that grant "Conscriptable Battalions" in tooltips) and stack on top of the additive base. Unincorporated states get a multiplicative penalty to conscription rate. Pull current per-law numbers and tech adds from `common/laws/` and the relevant tech files.

### Unit categories

Land battalions come in three categories, each with several tech-gated unit types (verify IDs via `/raw/CombatUnitType/<id>`):

- **Infantry**: Irregular → Line → Skirmish → Trench → Squad → Mechanized. Defense-leaning. Armies need a substantial Infantry share to avoid organization penalties from too-many-special-units. Modern infantry (Mechanized) adds devastation.
- **Artillery**: Cannon → Mobile → Shrapnel → Siege → Heavy Tanks. Offense-leaning, raises kill-rate and devastation. Artillery types impose a stacking penalty to army mobilization and movement speed scaled by composition share — heavy-artillery armies are slow.
- **Cavalry**: Hussars → Dragoons / Cuirassiers → Lancers → Light Tanks. Battle-occupation specialists. Hussars boost movement/mobilization; modern armor (Light Tanks) adds devastation.

Veterancy levels (Recruit → Regular → Seasoned → Veteran → Elite) raise offense, defense, and morale damage at higher tiers. Units gain experience over time, faster while in battle. Casualties dilute experience proportionally with the new manpower; upgrading a unit type drops the unit one veterancy tier.

## 4. Mobilization

### Mobilization itself

Armies must be **mobilized** to receive orders. Mobilization takes 5–20 days depending on state infrastructure. Demobilizing manually costs a 90-day decaying expense equal to mobilization cost and locks the army out of remobilization for 90 days. Peace + no diplo plays = free demobilization.

Fleets are always active and never need mobilization.

### Mobilization options

Armies can stack additional consumption-cost options for combat bonuses. All require the goods to be available in the country's market; costs apply only while mobilized.

| Category | Inclusive? | Options |
|----------|-----------|---------|
| Supplies | inclusive | Basic Supplies (always required), Extra Supplies, Luxurious Supplies — each tier raises morale/offense/defense and gates on tech. |
| Supplements | inclusive | Chocolate, Tobacco, Liquor, Opium — each raises morale recovery. |
| Transportation | exclusive | Forced March (faster but raises morale loss), Truck Transport, Rail Transport. |
| Special Weapons | inclusive | Machine Gunners, Chemical Weapons (raise offense / kill rate at the cost of recovery), Flamethrowers (raise offense, devastation, and morale damage). |
| Reconnaissance | inclusive | Motorized, Balloon, Aerial — affect battle occupation and combat conditions; Aerial has an occupation ceiling. |
| Medic Support | exclusive | First Aid, Field Hospitals — raise recovery rate. |

Activating most options imposes an organization penalty while mobilized; deactivating mid-war costs additional organization or morale. Plan switches around lulls between battles. Specific cost values are in `common/mobilization_options/`.

### Conscription

Conscript battalions activate army-by-army during plays/wars. Once activated, they cannot return to civilian life until demobilization. They take time to reach full strength and disappear (with all experience) on demobilization.

## 5. Commanders

Commanders are characters with general/admiral roles, hired through formations. **As of 1.13 each formation has a single commander** (the old up-to-four-commanders model is gone). Commanders can be freely unassigned and reassigned between formations, but take some time to travel to their new posting; while in transit their trait benefits are suspended and they cannot advance on the front, though they still provide command limit. A single commander can participate in multiple battles simultaneously, capped by distance and rank. Orders apply to the whole formation, not per-commander as before. Male rulers of dictatorships and monarchies can also serve as Commander-in-Chief.

There are five commander ranks per branch: Brigadier General → Field Marshal for armies, Commodore → Grand Admiral for fleets. Each rank up the ladder grants more IG political strength, costs more bureaucracy upkeep, and raises the commander's command limit (battalions for generals, flotillas for admirals). A monarch / dictator serving as Commander-in-Chief sits in a separate rank with its own modifier set.

Promotion requires bureaucracy surplus. Per-rank command-limit values now scale up with technology (1.13 change: command limit from rank increases with research progress, so absolute command limits in the late game are noticeably higher than at game start). Pull current per-rank numbers from `common/character_roles/` or the relevant role definition. Commander traits gate access to specialized orders (Reckless Advance, Pillage, Last Stand, Carrier Sorties, etc.) and tilt battle-condition probabilities (Mountain Combat Expert, Open Terrain Commander, etc.).

**Unnecessary-promotion penalty (1.13).** Promoting a commander when you already have ample command limit causes IG approval loss for the Armed Forces and for any non-Armed-Forces IG that has commanders not benefiting from the promotion. Use `under-command-limit` swaps as the canonical way to recover from a commander dying or retiring rather than always promoting fresh.

## 6. Orders

### Land orders

Formations on a front operate under an Advance or Defend order set by their commander (1.13: orders apply to the whole formation, not per-general — consistent with the single-commander-per-formation change in § 5). Specialized variants of each order unlock based on the commander's traits and the formation's composition.

- **Advance** orders push the front into enemy territory. Variants are unlocked by trait-and-composition gates: Advance Front (default), Reckless Advance (Reckless trait — high-offense / high-morale-cost), Pillage (cruel-trait variants — devastation-heavy, occupation-light), Cautious Advance (Cautious trait — slower but lower morale loss), Heavy Barrage (artillery commander + sufficient artillery share), Rapid Advance (cavalry-heavy composition — high-offense / high-casualty), Heavy Advance (heavy-armor composition).
- **Defend** orders prevent enemy advances and recapture friendly territory but do not occupy enemy territory. Variants: Defend Front (default), Adamant Defense (defensive-strategist trait), Counter Charge (Brave trait + cavalry share), Last Stand (defender traits — increased defense at higher casualty cost), Delaying Tactics (pillager-style trait + irregular composition — favors surprise/camouflage conditions).

Orders have no effect when the army is not assigned to a front.

### Naval missions

Fleets are assigned to one mission at a time; the catalog of available missions (Project Power, Interception, Protect / Raid Supply Lines, Blockade, Port Bombardment, Hunt Pirates, Privateering, Piracy) is documented in § 9.8. Each (except Blockade) has trait- or composition-gated variants — e.g. Wolf Pack with high-submarine fleets, Carrier Sorties with Innovative-trait admirals on carrier-heavy fleets — though the specific variants and trait gates were partially churned by the 1.13 naval rework. Verify any specific variant's trigger set against `common/admiral_orders/` rather than older wiki tables.

A fleet's mission is changed from the fleet screen.

## 7. Fronts, theaters, invasion

When a play starts, **fronts** appear at every land border between the two sides. A front is created for each pair of contiguous **theaters** (single-side territory blocks). An ocean or neutral country interrupting the border doesn't split the front if the line continues on the same country (e.g. Russia / Ottomans around the Black Sea), and small interruptions of a single state region merge fronts even on opposite sides of that state.

Fronts dynamically merge / split / vanish as battles occupy states and new participants join. Armies on a vanished front auto-route to the nearest accessible front or back to an HQ.

### Movement between fronts

Send to Front requires a supply line from the army's home HQ to the front. Landlocked fronts may be unreachable until friendly territory or military access bridges the gap. Travel between fronts is uninterceptable — fleet position cannot block transit. Mid-battle front reassignment finishes the current battle before moving.

### Invasion

- **Land invasion** requires only an army and military access through a neutral country. Creates a new front at the targeted state. (1.13 also removed the *strategic land adjacency* requirement on military access treaties — adjacency is no longer a gate.)
- **Naval invasion** in 1.13 requires a fleet with enough **transport capacity** (a ship attribute set per ship type and customizable in the Ship Designer). Land units **embark** the fleet, travel, and **disembark** at the target state. A Marine formation permanently attached to the fleet (see § 9.5) is more efficient at this than a regular army being shuttled.
  - Units in transit consume more supply because they're far from their Logistics Center — naval invasions are now genuinely costly to keep mobilized.
  - Naval Fortifications at the target state set a **minimum strength** the invading fleet must beat before invasion can even be attempted, plus a defense bonus to the invasion battles that do happen (see § 9.9).
  - The older flotilla-count / `landing_craft`-tech penalties may have been replaced or restructured — verify against the live game's tooltip before relying on the specific numbers from older docs.

The defender auto-creates a front at the targeted state, but defending armies parked in HQ are *not* auto-assigned to the new front — repeated naval invasions force defender micromanagement.

## 8. Battles

### Advancement and triggering

Each general on Advance accumulates personal advancement progress at the front. At 100 progress an offensive battle starts; if both sides are advancing they alternate. The UI shows only the highest current progress.

Defenders pick a general by command-limit weight + defensive traits (terrain/artillery traits aren't considered in this pick — only command strength and defense traits).

### How many battalions fight

Battle size goes through several conceptual gates (specific formulas live in `common/script_values/command_values.txt` — pull from there if the actual numbers matter):

1. **Total available battalions on the front** — from any allied formation deployed there, unless a formation toggles "disable unit lending."
2. **Low-concentration penalty** — long fronts with many provinces eat a randomized down-scaling on the available pool. Short fronts barely notice.
3. **Combat width cap** — a per-state cap driven by the state's infrastructure scaled by terrain. Mountain provinces in particular cap battle size hard, neutralizing numerical advantage.
4. **Numerical bonus** (non-naval-invasion only) — the larger side can field beyond the cap by a multiplier scaling with the side ratio, hitting a ceiling at heavy outnumbering.

The final size cannot exceed total available battalions or fall below 1.

Battalion selection prefers the strongest units on the front (manpower × morale × mobilization × offense/defense, with a multiplier favoring units in the general's own formation). Battalions below very-low morale or manpower are unfit to fight. Command limit doesn't cap battle size — borrowed battalions count and don't penalize the borrowing general.

### Battle resolution

Combat ticks four times daily, exchanging manpower and morale damage. Combat width again caps how many of the fielded battalions actually engage each tick. No reinforcement and no early retreat once started. The side that runs out of morale or manpower first retreats; the other side gets occupation progress.

### Occupation

Battle wins yield occupation score scaled by terrain and infrastructure. A state takes 2–4 consecutive wins to fully occupy. Occupation only matters for war-goal control during the war; buildings continue to function and supply their domestic market while occupied.

### Battle conditions

A weighted-random battle condition is rolled per side at battle start; rerolled with increasing probability after 10 days. Condition weights are added per terrain feature (a Mountain province is both *Elevated* and *Hazardous*) and multiplied by the commander's per-condition multiplier.

Condition families:
- **Maneuver** — Aggressive (+morale damage, +casualties), Careful (−casualties, −morale loss), Blunder (−morale, +casualties).
- **Visibility / terrain** — Good Visibility (defender bonus), Poor Visibility (penalizes both sides), Mud, Charted Terrain, Camouflaged, Dug In, Lost.
- **Supply** — Logistics Secured (−morale loss), Broken Supply Line (+morale loss), Exhausted (+morale loss).
- **Pursuit / retreat** — Pursuit (instant, no morale loss while pursuing), Panicked Retreat / Controlled Retreat (asymmetric retreat handling).
- **Maneuver outcomes** — Surprise Maneuver, Rapid Advance.
- **Naval-only** — Death from Below (gated on submarine share, raises kill rate), Ramming Maneuver, Rough Waters, Strong Winds.

The full table lives in `common/combat_unit_groups/`-adjacent definitions and on the wiki; verify behavior of any specific condition before scripting against it.

## 9. Naval-specific systems (1.13 rework)

The 1.13 patch (The Great Wave) **replaced almost the entire naval layer**. Anything written about navies before 1.13 — including older mod docs and the wiki's older ship-category breakdowns — is suspect. This section captures the post-rework concepts.

### 9.1 Ships as individual objects

Pre-1.13, navies were abstract pools of "flotilla units" recruited like battalions. 1.13 replaced that with **persistent individual ships**:

- Ships are constructed using **Ship Construction**, a new resource produced at **Shipyards** (1.13 also re-merged civilian and military shipyards into a single building type — both military and Supply Ships now come from the same Shipyards, which still produce the civilian goods Clippers and Steamers as before).
- Ships have **hull damage** and **crew damage** that accumulate over their lifetime. Enough damage sinks a ship; less than that forces it to **return to port to repair**, consuming goods at the shipyard.
- Ships need a **crew** drawn from sailors produced at **Naval Administration** buildings (the sailor-producing role still exists; the building stayed). Without crew a ship sits idle.
- Ship type cannot be changed once built — the old "convert flotilla to a different unit type" pattern is gone. New tech unlocks new ship types you build alongside the old ones.
- Ship construction times are significantly longer than the old "recruit 1000 sailors" model.
- The two military goods **Man-o-War** and **Ironclad** were *removed* in 1.13 — they were the consumable goods the old shipyards required to recruit flotilla units of those types, and don't exist anymore now that ships are individual objects built from Ship Construction. If you find them referenced as goods in mod or older content (PMs, trade routes, buy packages, treaty articles), that reference is broken.

### 9.2 The Ship Designer

Each ship type can be customized through saved **templates** (per-playthrough scoped). The Ship Designer exposes four main axes:

- **Armor** — damage reduction.
- **Armament** — attack and damage potential.
- **Propulsion** — speed and detection-related attributes.
- **Supply Capacity** — how much fuel/supply the ship carries (impacts overseas operation cost).

Plus **Utility modifications** that shift secondary stats (e.g. Patrol Boat utility on light ships increases blockade strength). Higher-tier customization scales construction cost **non-linearly**, so maxing every axis is intentionally expensive.

### 9.3 Flagships

A ship can be designated a **Flagship** with a unique figurehead ornament. Flagships generate **prestige from successful battles** they participate in (and *lose* prestige from defeats). A fleet containing a Flagship also generates extra **involvement** in the strategic regions where the fleet is active (the diplomacy hook, see `vanilla_diplomacy_reference.md` § 6).

### 9.4 20 ship types and Naval Doctrine

1.13 ships ship in **20 different types**, all modeled on historical templates. The taxonomy is now wider than the simple Capital / Light / Support split older docs use, and ship type IDs and unlocking technologies have largely been renamed. **Always verify ship type IDs and unlocks via `/raw/CombatUnitType/<id>` and `/raw/Technology/<id>` rather than relying on older wiki tables.**

A new **Naval Doctrine** law group provides bonuses to construction of different ship types — choose the law variant matched to your intended fleet composition.

### 9.5 Marines

Marines are a new special **land unit** type. All-marine formations can be **permanently attached to fleets** and are more efficient at conducting naval invasions than regular troops. They live in the land-unit table but their natural posting is at sea. Britain, France, Spain (and others) start 1836 with marine formations historically.

### 9.6 Naval combat

The combat model itself was rewritten. Each ship has an **Initiative** value driving turn order. On its turn a ship either attacks or attempts to retreat. Attacks deal **hull damage** or **crew damage** based on attack vs armor and the engaged ships' specific stats. The **wood-to-steel transition is intentionally very impactful** — a steel-hulled ironclad-class ship decisively outclasses a wooden capital ship in a way the old offense/defense flotilla model didn't capture.

Naval battles are visualized as **dioramas** showing the two clashing fleet compositions.

### 9.7 Sea nodes, presence, detection

Fleets still operate at **sea nodes**, but the engagement model changed:

- Fleets can be **present in multiple nodes simultaneously** at reduced mission efficiency.
- Engagements are gated by a **detection vs visibility** comparison — a fleet looking for the enemy may or may not actually find it. Stealthier fleets can go unnoticed.
- Fleets in transit through a sea node can be **intercepted** if the opposing side spots them in time.

Mission effectiveness still scales with the fleet's presence, but the old "always-engages-at-the-node" model is gone.

### 9.8 Naval missions

The full mission list as of 1.13:

- **Project Power** — apply diplomatic involvement to the region; threaten the coast.
- **Interception** — engage hostile fleets crossing the node.
- **Protect Supply Lines** — defend friendly Supply Ships.
- **Raid Supply Lines** — attack enemy Supply Ships (the renamed "raid convoys" mission).
- **Blockade** — cut off coastal economy of a state.
- **Port Bombardment** *(1.13 new)* — fire on a coastal state to cause devastation and destroy buildings.
- **Hunt Pirates** *(1.13 new)* — engages any fleet on Piracy/Privateering missions in the node.
- **Privateering** *(1.13 new)* — recognized-nation version of Piracy, available during war or active naval hostilities.
- **Piracy** *(1.13 new)* — unrecognized-nation only; captures trade through the node and sells it in the actor's market.

A new treaty article exists to **enforce abandonment of Piracy**. Gunboat diplomacy (offering treaty terms backed by **Naval Hostilities** if declined) is the stated 1.13 design intent — the "blurred line between peace and war" framing.

### 9.9 Naval Fortifications and straits

1.13 added **Naval Fortifications** as a new building family:

- Provides a **minimum-strength threshold** an attacker must beat before a naval invasion can even be attempted.
- Adds a **defense bonus** to invasions that do happen, scaled by the ratio of attacking and defending forces.
- Acts as the toll/access-control mechanism for **straits** (also new in 1.13). Numerous historical strong forts were placed around the world in 1836.
- New treaty articles let countries demand **strait exemption** or forbid a country from closing a strait.

### 9.10 Battle-size sizing rules

The actual size of a naval battle is gated by admiral command limit. The smaller-command-limit admiral can field meaningfully beyond their limit; the larger-command-limit admiral has their effective contribution proportionally reduced. Available flotillas in the fleet still cap the absolute maximum. Specific scaling factors moved with the 1.13 rework — verify against the live game before scripting against any specific number.

## 10. Supply, attrition, devastation

### Supply (1.13 rework)

Each formation has a **Logistics Center** at its HQ. Formations fighting overseas trace a supply route from the front back to the Logistics Center, consuming **Supply Ships** in proportion to supply consumption × distance to HQ. Supply Ships are built at Shipyards from Ship Construction (like military ships) and are stored as a national stockpile — the active count and total available appear in the top bar where convoys used to live.

The 1.13 patch **removed convoys** and split the old single resource into:

- **Merchant Marine** — covers all civilian usage (port connections, trade routes).
- **Supply Ships** — covers all military usage (formation supply, troop transport).

Older script that talks about "convoy raiding" should be read as "Supply Ship interception"; the mechanic is the same shape, with the new noun. Mod content that explicitly references the `convoys` resource will have broken at 1.13 — verify all such references on patch upgrade.

Enemy interception of Supply Ships reduces supply efficiency proportionally; supply degradation directly reduces morale recovery, and past a high threshold it eats into maximum organization. Goods shortages at the unit's barracks/naval base also reduce supply with the same downstream effects.

### Attrition

Mobilized formations suffer attrition, producing wounded and killed pops. The base attrition rate, the per-week casualty range, and the home-HQ stationing discount are all in `common/defines/`. Two structural points survive any rebalance: home HQ stationing significantly cuts attrition, and battalions actively in battle don't take attrition (battle casualties replace it).

### Devastation

Battles and enemy occupation increase **state devastation**. Devastation is also generated by certain mobilization options (notably Flamethrowers; Chemical Weapons indirectly) and certain unit types (Mechanized Infantry, Light Tanks, Heavy Tanks, Siege Artillery — modern infantry and armor add devastation). Devastation hurts migration attraction, infrastructure, construction efficiency, and mortality. After the cause resolves it decays slowly — high-level devastation can persist for years.

## 11. Combat stats

The primary stats are **offense** (attackers) and **defense** (defenders). Both increase casualties and morale damage.

**Morale** is the percent of manpower able to continue fighting. Each unit type has a base morale-loss rate per tick in battle. Morale recovers at a slow per-day rate when not in battle, modified by morale-recovery modifiers, capped by supply.

**Manpower** is the unit's pop count, with a per-battalion ceiling. Casualties from combat or attrition reduce it. Officers take fewer casualties than Servicemen (the difference is a defines value). Combat enforces a minimum casualty count per unit per tick so units aren't damage-immune.

### Prestige goods

Units consuming prestige goods gain bonuses to offense, defense, and morale recovery, scaled by the share of the unit's input value that's prestige-grade. The bonuses cap at the share-100% case. Pull current cap values from `common/defines/`.

## 12. Power projection and prestige

Power projection = average of (offense + defense) × manpower-ratio, summed across all units. It produces:
- prestige (0.03 per army unit, 0.1 per navy unit; subjects contribute at 0.0005 / 0.01 respectively)
- naval power projection contributes to **involvement** in the strategic regions a fleet patrols (the 1.13 tiered-interest system; see `vanilla_diplomacy_reference.md` § 6 — the old "extra declared interest per 100 naval power projection" formulation is from the pre-1.13 binary interest model and no longer applies)

## 13. War support — the political ceiling on a war

This is the section that matters most for anti-war movement and wartime-event design. **War support** is a per-country value in roughly [−100, +100], starting full when war begins and decreasing each week from **exhaustion**.

### Exhaustion sources

War-support exhaustion is the *sum* of several contributing sources, each tunable in `common/defines/`. The structural categories (durable across patches):

- **Base trickle** every week regardless of conditions.
- **War-goal control** — the enemy controlling unfulfilled war goals against you accelerates exhaustion, scaled by the fraction occupied.
- **Radicals** — every percentage point of radicalized population adds exhaustion. **A country with significant radical population bleeds noticeably more war support per week from population alone.** Movement-driven radicalization is a real wartime cost, not just flavor; it compounds with casualties and occupation.
- **Casualties vs max manpower** — exhaustion scales with the casualty fraction; "losing all battles" multiplies the casualty-driven exhaustion several-fold over "winning all battles."
- **Cultural casualties** — casualties of accepted cultures on both sides add exhaustion.
- **Lobby clout** — opposed-to-war lobbies add exhaustion; supportive lobbies subtract it.
- **Occupation tiers** — capital and home-state occupation by the enemy generate large exhaustion bumps that escalate sharply as occupation deepens. Heavy occupation can drive multi-points-per-week loss.

**Floor logic.** A country cannot fall below 0 war support **unless** an enemy occupies all its war goals or its capital state. Subjects do not capitulate independently of their overlord.

### Capitulation

At minimum war support a country auto-capitulates: all war goals against it are enforced, and it leaves the war. Voluntary capitulation is also possible at any time. If all countries on one side fully capitulate, the war ends.

### Peace negotiation

Aside from capitulation, peace deals require unanimous agreement from all **negotiating participants** (countries with or targeted by war goals) on each war goal pressed. Subjects don't get a say. The deal applies to the entire war — no partial peace with a subset of belligerents.

### Modifier names that touch war support

(Names that follow are the *handle* into the system — useful for searching the catalog. Their values are tuning balance, found in their owning files.)

- `country_war_exhaustion_casualties_mult` (vanilla) — scales the casualties-driven portion of war exhaustion. Negative values reduce exhaustion from casualties (a wartime upside).
- `state_war_support_monthly_add` (mod-added) — direct per-state war-support gain.
- `state_loyalists_from_political_movements_mult`, `state_radicals_from_political_movements_mult` (vanilla) — gate how movement activism translates to pop loyalty/radicalization (and therefore into war-support exhaustion).
- `political_movement_pop_attraction_mult`, `political_movement_radicalism_add` (vanilla) — applied **to a movement scope** to shrink/grow its size and activism. Used by mod modifiers like `anti_war_movement_suppressed`.
- Diplomatic-play modifiers (vanilla): `country_diplomatic_play_maneuvers_add`, `country_diplomatic_play_maneuvers_mult`, `country_infamy_decay_mult`, `country_infamy_generation_mult`, `country_infamy_generation_against_unrecognized_mult`. Verify the current list with `/modifier-search?q=infamy` and `/modifier-search?q=diplomatic_play`.

## 14. Where to look in the codebase

- `common/combat_unit_types/` — unit type definitions (offense/defense/morale base stats); now includes **20 ship types** post-1.13.
- `common/mobilization_options/` — mobilization options and their `unit_modifier` blocks.
- `common/military_formations/` — formation type definitions.
- `common/admiral_orders/` and `common/general_orders/` — naval mission and land order definitions, including 1.13-added Port Bombardment / Piracy / Hunt Pirates / Privateering.
- `common/buildings/` — Shipyards (merged civilian+military in 1.13), Naval Administration (sailors), and Naval Fortifications (1.13 new) — verify exact IDs via `/buildings`.
- `common/strategic_regions/` — consolidated set in 1.13; verify region IDs against this directory before referencing them in mod content.
- `common/laws/00_naval_doctrines.txt` (or similar) — Naval Doctrine law group added in 1.13.
- `common/character_traits/` — commander aptitude traits and their modifiers.
- `common/diplomatic_plays/` — war goal definitions; mod additions live in `te_unification_plays.txt`.
- `common/laws/extra_laws.txt` — search for `country_war_exhaustion_casualties_mult` to see how mod-side laws gate wartime resilience.
- `common/power_bloc_principles/extra_power_bloc_principles.txt` — power-bloc-level military bonuses.
- `events/<system>_events.txt` — wartime events. Anti-war movement: `events/movement_events_te.txt`. Active wars (mobilization, fronts, capitulation): vanilla `events/war_events.txt` and mod overlays.
- `common/on_actions/extra_on_actions.txt` — wartime pulse hooks (`on_war_started`, `on_war_lost`, monthly pulses gated on `is_at_war = yes`).
- `common/scripted_triggers/` — `is_at_war`, `any_scope_war`, etc. (defined in vanilla `common/scripted_triggers/`).
- `common/script_values/command_values.txt` (vanilla) — battle-size and naval-battle-size formulas.

## 15. Anti-war movement design notes

The mod has an active anti-war movement system surfacing as `movement_anti_war` political movements. Events in `events/movement_events_te.txt` (5–8) gate on the movement's existence and, where appropriate, on `is_at_war = yes`. When designing or rebalancing these events:

- Prefer real war-mechanic levers (`country_war_exhaustion_casualties_mult`, `political_movement_pop_attraction_mult`, `political_movement_radicalism_add`) over invented or fake modifier names. The engine silently no-ops invalid names.
- Anti-war movement scope is reachable via `random_political_movement = { limit = { is_political_movement_type = movement_anti_war } save_scope_as = anti_war_movement }` in the event's `immediate` block. Apply movement-side modifiers to that saved scope.
- War support is *the* mechanical ceiling on a war's duration. Options that radicalize the lower strata also accelerate war-support loss via the radical → exhaustion linkage. This is intended pressure, not a bug.
- Lobby clout is also a war-support lever (see § 13 exhaustion table — opposed lobby clout adds 0.01/week per percent, supportive lobby clout subtracts 0.01/week). The hooks are vanilla lobby-strength mechanics rather than a single named modifier; use `add_lobby_appeasement_*` effects, `country_lobby_leverage_generation_mult` modifiers, and IG-clout shifts to move lobbies the way you want.
