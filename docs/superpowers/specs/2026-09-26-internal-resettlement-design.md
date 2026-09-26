# Internal resettlement: the Settlement Authority — design

## Context

The mod's internal resettlement system is two buildings: a **Resettlement Camp** in a source state and a **Resettlement
Colony** in a destination state (`common/buildings/resettlement.txt`, `resettlement_pms.txt`, `resettlement_pmgs.txt`,
`resettlement_transfer_effect` in `extra_effects.txt`). Each month the effect `move_pop`s every laborer or slave pop
employed at the camp to a random colony state. The review found:

- The volume the player sees is not the volume that moves. `state_resettlement_transfer_add` is read only as a `> 0`
  gate; hiring rate and laborer slots set the real flow. The PM comments, the effect header and the code give three
  different numbers, and the headers describe code (`move_partial_pop`, `ordered_scope_pop`) that does not exist.
- The player cannot choose who moves, and the destination is re-rolled each month.
- Closed Borders, an external-migration law, blocks an internal programme.
- The transport PM group does not touch the transfer.
- Arrivals land unemployed and can drift home; slaves moved to a free state are silently freed.
- After construction there are no decisions: no events, no consequences beyond static modifiers.

An earlier version (`b60fd696`, 2024) used a source decree and a destination decree that spawned a hidden migrant camp
with a custom `deportee` pop type. The owner dropped it because it was **opaque**, **ethnic-only** (valid only where a
discriminated culture lived) and had **no real costs** (decrees cost only authority).

This design replaces both. International transfers (Lausanne-style exchanges) stay with the `population_transfer`
treaty article and are out of scope.

Baseline: `main` at `80ad254a` (#479 merged).

## Decisions (owner, 2026-09-26)

| Question | Decision |
|---|---|
| What the player never does | **Select a culture or religion to move.** No "enact internment of culture X" |
| Acceptance | May **restrict eligibility** for a benefit (voluntary programmes take Second-rate citizens or better). A programme that systemically draws on low-acceptance pops is historically defensible and acceptable, but is **not in v1** (see Out of scope) |
| Shape | **A: destination-driven Settlement Authority.** One building in the destination; the programme PM decides who is recruited and how; sources are ranked automatically; an optional Recruitment Drive decree steers them |
| Costs | Real money, goods and staff, through the building |
| Transport | **Stays a PM group**, but made real (adds capacity, costs transportation) |
| Where the building works | **Frontier only.** The frontier closes when it fills |
| Frontier measure (amended after calibration, 2026-09-26) | **People per km² of real land area**, over the whole state region, from a generated area table. A frontier **opens below 2/km²** and **closes at 10/km²**, both scaled by the existing `state_migration_crowding_density_mult` (§6). Replaces "below the crowding floor", which counted Connecticut, D.C. and Rio de Janeiro as frontier and Kolyma as settled |
| Managed Retreat's sources (amended) | Global-warming damage is country-level, so: coastal states of a country carrying `coastal_flooding_modifier` or `coastal_relocation_modifier`, plus states carrying `nuclear_strike_aftermath` or `nd_weapons_accident_contamination`. Per-state GW damage is a future expansion of that system |
| Homesteads' payoff | **No permanent arable land.** A temporary agriculture/ranching throughput and subsistence-output bonus |
| IG reactions | **One country modifier per programme, scaled by volume**, never per building. Positives small and capped; magnitudes on the scale of vanilla's approval from *changing* a law, since a running programme is an ongoing action, not the status quo (§7.2) |
| Land pressure on existing frontier inhabitants | **Kept**: a real cost, never a benefit |
| Violating the UN Declaration | Allowed, with a modifier that scales with intensity, and **communicated clearly** at every step |
| Old saves with camps | Assumed to load (the engine drops unknown building types); no dedicated check |

## Engine facts this rests on

From the engine docs and vanilla script:
- `move_partial_pop = { state = <state> population = <script value> }` moves an exact count (vanilla ACW events pass an
  inline script value); `population_ratio` moves a share. Moved pops become unemployed; a pop type that cannot be
  unemployed, or a slave type moved to a free state, becomes the default type.
- `kill_population_in_state = { value = <int> pop_type = <type> }` kills a count in a state, filtered by pop type or strata
  (vanilla and the mod only ever pass constants).
- `add_radicals_in_state = { value = <share> culture = <cu> pop_type = <type> }` radicalizes a share of matching pops.
- `add_modifier` works on buildings as well as states and countries.
- Pop triggers: `is_employed`, `is_pop_type`, `strata`, `pop_acceptance`, `pop_radical_fraction`,
  `pop_employment_building_group`; state triggers `turmoil`, `state_unemployment_rate`, `has_decree`.
- `activate_production_method = { building_type = <type> production_method = <pm> }` works in state and country scope
  (engine docs; the mod's own `te_construction_market_direct_effects.txt` and `monument_events.txt` use it).
- A `state_region` scope holds variables (vanilla `krakatoa_events.txt` sets one). Script cannot iterate a state's
  provinces, so land area has to come from a generated table (§6).
- Engine-doc `<int>` fields may silently ignore a script value (the owner's notes record `add_escalation` doing so), so
  deaths are removed in steps of 100 with `while = { count = <value> kill_population_in_state = { value = 100 … } }`.
- PMs have no state trigger, so a PM cannot test whether its state is coastal.
- There is no modifier that blocks emigration, and a state's migration attraction cannot be read in script (`migration_pull`
  returns the country's mass-migration value). Retention can only come from making the destination attractive.
- No modifier adds radicals directly; source unrest must be an effect.
- Vanilla PMs never carry IG approval; vanilla puts political strength only on unique monuments.
- Multiplicative modifiers in a `workforce_scaled` block multiply by level; vanilla uses `unscaled` blocks for them
  (`02_agro.txt`).

**Verify in-game before building on them** (the debug event in §13 reports each):
1. Does `move_partial_pop` create a cultural community at the destination, as vanilla mass migration does?
2. Does a script-value `population` move the exact count, and do farmers arrive as farmers?
3. Does `kill_population_in_state` with a pop-type filter kill only that type?
4. Does removing the building when the frontier closes leave nothing behind (employees, construction queue)?
5. Does `move_partial_pop` carry a pop's radical and loyalist shares proportionally? Penal Transportation's premise
   (it drains radicals) and Rustication's (it cuts urban radicals) depend on it.

## 1. The Settlement Authority

- **Key:** `building_resettlement_colony` (kept, so existing saves keep their destination buildings), displayed as
  *Settlement Authority*. Building group `bg_resettlement` (government, under `bg_bureaucracy`).
- **Available from 1836:** no unlocking technology; programmes are gated individually (§3).
- **Level cap:** `state_building_resettlement_colony_max_level_add`. `base_values` gives **5** (replacing today's 1), and
  nationalism, civilizing_mission, mass_propaganda, keynesian_economics and civil_rights_movement each add **5**, as they
  do for the camp today. Maximum 30. Level is capacity: throughput and every cost scale with it. The cap is the only bound
  on how fast one state fills, since vanilla's per-state immigration cap does not apply to `move_partial_pop`.
- **Frontier gate (`possible`):** a new Authority needs an **open** frontier (below the opening density, §6); a state
  that already has one may add levels until the closing density. Tested as `resettlement_frontier_open_margin > 0` /
  `resettlement_frontier_close_margin > 0`. A script value compared inside a trigger is existing practice in this repo
  (`migration_crowding_mult` does `limit = { migration_crowding_ratio <= 0 }`). Lombardy, Paris or the Ruhr cannot host
  one. No Closed Borders gate.
- **Closure:** when the destination reaches the closing density, the monthly pulse removes the building and the country is told
  *The Frontier Is Closed* (§8). The player moves the programme to the next frontier.
- **PM groups:** Programme (§3), Settlement (§5), Transport (§4).

## 2. The monthly transfer

Runs on `on_monthly_pulse_country` (replacing `resettlement_transfer_on_action`), in a new
`common/scripted_effects/resettlement_effects.txt`. The country pulse resets every state's monthly counters, walks its
Settlement Authorities one after another, then refreshes every readout and the political layer, all in one execution.
Several destinations can draw on one source in a month, and a state pulse per destination would leave the source's
counter at the mercy of pulse order. Every per-state computation still runs in state scope inside `every_scope_state`.

**Capacity.** The Programme and Transport PMs grant `state_resettlement_transfer_add`, **half in a `level_scaled` block
and half in a `workforce_scaled` block** (vanilla uses both in `state_modifiers`). The pulse moves exactly the total, so
the number in the state's modifier breakdown is the flow. The split exists because the building hires from the
destination's own population, which starts sparse: `workforce_scaled` follows the whole building's occupancy, so a
purely workforce-scaled capacity could stall at zero in an empty frontier. The level-scaled half guarantees a flow from
the first month; arrivals then take the building's jobs and the workforce-scaled half rises. Understaffing or a goods
shortage costs at most half the capacity. Staff per level stays modest for the same reason (§12).

**Recruitment rule.** Each programme defines which pops are eligible (§3). Culture and religion are never tested.

**Source ranking.** The pulse ranks the owner's other states (never the destination, never another Settlement Authority
state) by eligible population (for Penal Transportation, whose eligible pops are the radical ones, that is each state's
radical population), and walks down the list, taking from each state until capacity is met or states run out. From each eligible pop it takes
at most **2%** of the pop per month, and each source gives at most **2%** of its eligible population a month across all
Authorities: a destination's walk starts from 2% of the people at that source its programme may recruit, less what
earlier destinations took from it this month (`rs_recruits`), and every take is held to what is left. Vanilla's
emigration ceiling is 0.5% of a state's population per week, about 2% a month, so a programme drains no faster than a
crisis would. Takes under 100 people are skipped, so the walk does not splinter the destination into tiny pops.

**Recruitment Drive decree** (`decree_resettlement_recruitment_drive`, costs authority, AI weight in §10). All drive states
form a priority tier: every destination walks the drive states first, in order of eligible population, and reaches
other states only when drive states hit their cap. A drive raises its state's per-pop cap to **4%**. A drive
changes where people come from, never who is eligible. Several drives are allowed; each costs authority. The decree's
`country_trigger` requires the owner to run at least one Settlement Authority, so a drive is never bought for nothing and
lapses when the last programme ends.

**Deaths in transit** (coercive programmes, §3). Of each month's recruits, the programme's transit-mortality share is
removed at the source with `kill_population_in_state`, in steps of 100, filtered to the programme's recruits (farmers for
Special Settlements, laborers for Rustication, the lower strata for Penal Transportation), and the rest are moved. Each
source carries the fraction of a step from month to month (`rs_death_carry`), so a small programme's dead (Penal
Transportation at 5% needs 2,000 recruits for one step) are killed and counted once they add up to 100; the destination's
*Died in transit* counts only those actually killed.

**Readouts** (dynamic-modifier pattern: a static modifier re-applied monthly with the month's count as its multiplier):

| Modifier | Where | Shows |
|---|---|---|
| `resettlement_arrivals` (`building_resettlement_arrivals_add`) | the building | settlers who arrived last month |
| `resettlement_transit_deaths` (`building_resettlement_transit_deaths_add`) | the building | recruits who died in transit last month (coercive only) |
| `resettlement_recruits` (`state_resettlement_recruits_add`) | each source state | people recruited here last month; its description names the programme's source consequences (§7.1) |

All three types are display-only (registered like today's `state_resettlement_transfer_add`, `ai_value = 0`). Each
applies only while its count is above zero.

## 3. Programmes (PM group 1: `pmg_resettlement_programme`)

Each programme sets who is recruited, capacity per level, staff and goods, destination effects (its `state_modifiers`,
which land on the destination) and transit mortality. Its political reactions are **not** in the PM (§7.2).
Multiplicative destination effects sit in `unscaled` blocks; additive ones in `workforce_scaled` blocks.

| Programme | Anchors | Unlock / law gates | Recruits | Destination effects | Transit deaths |
|---|---|---|---|---|---|
| **Land Grants** | Homestead Act 1862, Dominion Lands Act 1872, Argentine colonisation laws | none | Unemployed and peasants, lower strata, `pop_acceptance >= acceptance_status_4`. No peasants under Serfdom | incorporation and colony growth | — |
| **Military Colonies** | Russian military settlements, Cossack hosts, *tondenhei* 1874–1904, Xinjiang *bingtuan* | `standing_army` | As Land Grants, but `acceptance_status_5` only; staffed by soldiers and officers | turmoil effects reduced (`state_turmoil_effects_mult`, unscaled), faster incorporation | — |
| **Penal Transportation** | Australia to 1868, French Guiana 1852–1953, New Caledonia, Sakhalin *katorga*, the Andamans | `law_enforcement`; disallowed by Guaranteed Liberties | Lower-strata pops with `pop_radical_fraction` of at least 0.2 | higher mortality (harsh conditions) | low |
| **Organized Colonization** | Stolypin resettlement 1906–14 (~3M to Siberia), Brazilian state colonies | `railways` | Unemployed, peasants and laborers, `acceptance_status_4`+ | incorporation and colony growth | — |
| **Special Settlements** | Soviet dekulakization 1930–33 (~1.8M deported) | `mass_propaganda` + Collectivized Agriculture; disallowed by Guaranteed Liberties, Protected Speech, Right of Assembly | Farmers | higher mortality | high |
| **Development Program** | Virgin Lands 1954, FELDA 1956, Transmigrasi, Brasília, British New Towns | `keynesian_economics` | The voluntary pool plus machinists, engineers and clerks, `acceptance_status_4`+ | infrastructure | — |
| **Rustication** | China's Down to the Countryside 1968–80 (~17M) | `mass_media` (era 6) + Single-Party State | Laborers and clerks not employed in agriculture, plantations, ranching or subsistence (`pop_employment_building_group`) | — | near zero |
| **Managed Retreat** | Chernobyl exclusion zone 1986, Jakarta → Nusantara, Newtok | `environmental_movement` (era 8) | Everyone except slaves, from coastal states of a country carrying `coastal_flooding_modifier` or `coastal_relocation_modifier`, and from states carrying `nuclear_strike_aftermath` or `nd_weapons_accident_contamination` | — | — |

Every programme's PM description states who it recruits and from where, and each coercive PM's description carries the
Declaration line (§7.4).

## 4. Transport (PM group 3: `pmg_resettlement_transportation`)

Each PM adds `state_resettlement_transfer_add` per level (additive, so safe as levels stack) and costs transportation.

| PM | Unlock |
|---|---|
| Overland (wagons, marching columns) | — |
| Rail and Steamship | `railways` (steamships fold in because a PM cannot test for a coast) |
| Motor Transport | `combustion_engine` |
| Airlift | `commercial_aviation` |

## 5. Settlement (PM group 2: `pmg_resettlement_settlement`)

What the settlers build. Any pairing with any programme is allowed. Homesteads and Work Settlements need no unlock.

| Settlement | Anchors | Effect |
|---|---|---|
| **Homesteads** | prairie homesteads, Stolypin farmsteads, Virgin Lands | *Virgin soil*: `building_group_bg_agriculture_throughput_add` and `building_group_bg_ranching_throughput_add` (unscaled) and `building_subsistence_output_add`. **No arable land is added.** Ends with the building |
| **Work Settlements** | Kolyma, Norilsk, the Belomorkanal, the Baikal–Amur Mainline; company towns | The building employs laborers (the arrivals fill the slots); infrastructure; mining and logging throughput |
| **Planned Towns** | Brasília, the British New Towns, Akademgorodok | Infrastructure, construction, migration pull; engineer staff. Unlocked by `modern_urban_planning` (era 7); expensive |

Every Settlement Authority also adds a modest additive, level-scaled `state_migration_pull_add` so the frontier is less
likely to become an emigration source while the programme runs. Retention otherwise comes from jobs and standard of
living. A legal ban on leaving (special settlers, *propiska*) is **not modelled**: a pull strong enough to hold them would
also draw volunteers, so coercive programmes leak somewhat more than they did historically.

## 6. The frontier: people per km²

The crowding floor (people per unit of arable land) was the first candidate and failed against 1836 data: at the floor it
counts Connecticut, Delaware, D.C., Rio de Janeiro, Buenos Aires and Slovenia as frontier, and at any lower fraction it
drops Kolyma and Yakutsk, the classic penal and mining frontiers, because they have almost no farmland. The frontier is
measured against **land area** instead.

**The area table.** `scripts/generators/gen_region_area.py` counts each province's pixels in the game's
`map_data/provinces.png`, weights each pixel by its map row (14.5 km² per pixel between about 50°N and 50°S, falling to
about 5 km² near 70°), and sums a state region's provinces. Checked against real areas: Hokkaido 1.00, Île-de-France 1.02,
Iceland 1.02, Ceylon 1.03, New Zealand's South Island 0.96, Alaska 0.92, Kansas 0.91, Kola 0.88. It writes
`common/scripted_effects/te_region_area_generated.txt`, one `set_variable` per land state region; a monthly global pulse
runs it once per save (guarded by a version number), and `on_game_started` runs it for new games. The resettlement
country pulse also calls the guarded effect first, since on an old save a country pulse may run before the global one
and would otherwise read 1 km² and close every frontier.

**The measure.** `resettlement_frontier_density` = the population of the whole state region (every owner's part) ÷ its
area in km². The frontier is geographic, so a split region is measured as one.

**The thresholds.** A frontier **opens below 2 people per km²** and **closes at 10 per km²**, both multiplied by
`1 + state_migration_crowding_density_mult` — the crowding system's own modifier, which techs, principles and institutions
already raise. The 1836 set at 2/km² is the American West and upper Midwest, Siberia, the steppe and the Russian north,
Hokkaido, Manchuria, Xinjiang and Mongolia, the Brazilian interior, the Argentine pampas, Norrland, the Guianas and
Newfoundland; no European core. 2/km² is close to the US Census's 1890 frontier line (2 people per square mile, about
0.8/km²) scaled up for a game with no unsettled "empty" provinces. Closing at 10/km² puts Kansas at about 1.9 million and
Hokkaido at about 0.8 million, near their populations at the end of their historical settlement booms (1.4 million in
1890; about 1 million in 1901).

Temporary destination benefits stay at full strength until closure; the frontier gate is what bounds them. The building's
tooltip shows the density and both thresholds.

## 7. Consequences

### 7.1 At the source (per month, from the pulse)
- **Deaths in transit:** §2.
- **Unrest** (Special Settlements, Rustication): `add_radicals_in_state` on the remaining pops of the recruited type
  (farmers; urban laborers and clerks), share = **10 ×** this month's recruits ÷ that type's population in the state,
  capped at **0.1**. Penal Transportation causes none; removing radicals is its point. The effect does not show as a named
  cause in pop radicalism, so the `resettlement_recruits` modifier description states it.

### 7.2 Political reactions: one country modifier per programme, scaled by volume
- Each programme has a counter on the country: `resettlement_<programme>_volume = volume × 11/12 + this month's
  settlers`. At steady state it approximates a year's flow. Once the programme stops it keeps (11/12)^12, about a third
  (35%), of its level a year later, and the modifier goes once intensity falls below 0.01: after several years (about
  four and a half from full intensity, nearly six from four times the reference), sooner for a small programme.
- **Intensity** = counter ÷ (country population × `resettlement_intensity_reference`), clamped to [0, 1]. First estimate
  0.0025 (0.25% of the population a year; Stolypin's peak was about that).
- The monthly country pulse applies `resettlement_<programme>_politics` with `multiplier = intensity`. Twenty buildings
  running one programme apply it once.

A running programme is an ongoing action, not the status quo, so the yardstick is vanilla's approval from *changing* a
law (`00_defines.txt`: 5 for a change, 10 for a major one, 20 for an extreme one), not the ±5 clamp on laws already on
the books. (Owner ruling, 2026-09-26: a first calibration against the on-the-books clamp shrank these to +2/−5 and was
reverted.)

| Programme | At full intensity |
|---|---|
| Land Grants | Rural Folk +3, Landowners −3 (Southern planters blocked the Homestead Act until secession) |
| Military Colonies | Armed Forces +3, Rural Folk −3 |
| Penal Transportation | Intelligentsia −3 |
| Organized Colonization | Rural Folk +3 |
| Special Settlements | Rural Folk −10, Intelligentsia −5 |
| Rustication | Intelligentsia −10, Petty Bourgeoisie −5 |
| Development Program, Managed Retreat | none |

Only costs (bureaucracy, wages, goods) remain per building. Anything country-wide goes through this layer.

### 7.3 Land pressure on existing frontier inhabitants
In the destination, pops below `acceptance_status_4` gain radicals each month: `add_radicals_in_state`, once per such
culture, share = **5 ×** arrivals ÷ state population, capped at **0.05**. It is only ever a cost; nothing rewards it. It
feeds the Land Disputes event (§8).

### 7.4 The UN Declaration
A country carrying `un_human_rights_declaration_modifier` that runs Penal Transportation, Special Settlements or
Rustication receives `resettlement_declaration_violation`: prestige down (first estimate −10% at full intensity), applied
with `multiplier = intensity` summed over its coercive programmes (clamped to 1). With
`un_human_rights_reservations_modifier` it applies at half strength. It must be unmissable:

1. **Before choosing:** each coercive PM's description says a party to the Declaration will incur the modifier.
2. **When it starts:** the first month a party runs a coercive programme, or a country running one becomes a party, event
   `resettlement.20` explains the modifier, its scaling and how to end it. Options: *continue*, or *end our coercive
   programmes*, which switches every coercive Programme PM to the best available voluntary one (the Development Program
   once `keynesian_economics` is known, else Organized Colonization once `railways` is, else Land Grants). The modifier
   follows the coercive volume counters (§7.2), so it does not end when the programmes do: it keeps about a third of its
   level a year after they stop and is gone after several years, sooner for a small programme. Both the event and the
   option's tooltip say it fades over the following years.
3. **While it runs:** the modifier's name and description say what causes it, that it grows with the programme and that
   it fades over the following years once the programme stops.
4. **At the vote:** the Declaration's proposal and vote text (`un_propose_human_rights_*`, `un_vote.1.d_*`) mention that
   parties running coercive resettlement will be penalised.

The modifier is added to the convention registry so `test_un_convention_registry.py` pins it. The registry's
`Convention` row has fixed columns and no place for a violation modifier, so the test gains one (`None` for every other
convention).

## 8. Events (`events/resettlement_events.txt`, namespace `resettlement`)

Rolled from the pulse, weighted by programme activity, each with a cooldown. They follow the mod's conventions:
`event_image`, `custom_tooltip` for variable changes, competitive options (`event_creation_guide.md`).

| Id | Event | Anchors | Fires for | Options |
|---|---|---|---|---|
| .1 | **Land Rush** | Oklahoma 1889 | voluntary programmes | Open the land at once (capacity surge for a year, more land pressure) / Survey first (no surge) |
| .2 | **The Speculators** | railroad land grants, homestead fraud | voluntary | Crack down (authority) / Tolerate (Landowners and Industrialists approval, capacity down) |
| .3 | **Hard Winter** | the first winters on the prairie | any | Fund relief (money) / Let them endure (deaths and radicals at the destination) |
| .4 | **Dust Storms** | the Dust Bowl, Virgin Lands 1960–65 | Homesteads running for years | Conservation programme (cost; smaller bonus kept) / Press on (bonus ends, temporary farm-output malus) |
| .5 | **Reform Campaign** | Anti-Transportation League 1851, Chekhov's *Sakhalin Island*, Albert Londres 1923 | penal / coercive | End the programme (prestige, Intelligentsia approval) / Defy (both down) |
| .6 | **Famine in the Settlements** | 1930s special settlements, Nazino 1933 | Special Settlements | Relief (money) / Ignore (mortality spike, radicals) |
| .7 | **Petition to Return** | release of special settlers 1954, the zhiqing strikes 1978–79 | coercive, after years | Allow return (this destination's programme switches to the best voluntary one; one in twenty of its lower strata who are at least second-class citizens moves back, so the inhabitants §7.3 protects stay) / Refuse (radicals) |
| .8 | **Land Disputes** | reservations and treaty negotiations | destinations under land pressure (§7.3) | Negotiate reserves (costs authority and money, capacity down, inhabitants calmed) / Back the settlers (costs nothing now; inhabitants' radicals rise). No option rewards the pressure (§7.3) |
| .9 | **The Frontier Is Closed** | the 1890 census and Turner | closure | notification |
| .20 | **The Declaration and Our Programme** | — | §7.4 | continue / end coercive programmes |

## 9. Integrations

- **Laws:** §3 gates. The Closed Borders gate is removed.
- **Homelands:** left emergent. Settlers shift culture shares at the destination, which may eventually trigger homeland
  creation or removal; the homeland system's own unlock gates and ten-year timer govern that. Documented, not special-cased.
- **Global warming and nuclear:** Managed Retreat's source rule (§3). GW damage is country-level
  (`coastal_flooding_modifier` sits on the country), so it is read through the owner and the state's coast; the nuclear
  markers are state-level. The meltdown event's modifier is country-level and cannot be traced to a state, so it is not
  read.
- **Existing decrees:** `decree_encourage_emigration` and `decree_subsidize_immigration` stay; they tune natural
  migration.
- **Vanilla content:** the system never targets a culture, so it cannot collide with `je_indian_removal`, the Circassian
  expulsion or Hokkaido.
- **Treaty article:** unchanged.

## 10. Game rule and AI

- **Game rule** `internal_resettlement_rule` in `extra_game_rules.txt`: *Enabled* (default) / *Enabled, AI voluntary
  only* / *Disabled*. Disabled makes the building impossible and stops the pulse. *AI voluntary only* has the pulse
  switch AI buildings off coercive PMs.
- **Building `ai_value`:** frontier headroom, plus crowding and unemployment in the AI's own states; a soft cap on how
  many it runs.
- **PM `ai_value`:** flat numbers (engine limitation); coercive PMs low.
- **Recruitment Drive `ai_weight`:** the AI's most crowded, highest-unemployment state, only while it runs a Settlement
  Authority.

## 11. Replacing the old system

- Delete `building_resettlement_camp`, `pmg_resettlement_method` and its five PMs, `resettlement_transfer_effect`,
  `resettlement_transfer_on_action` and `state_building_resettlement_camp_max_level_add` (type definition and the five
  tech grants, which move to the colony key).
- Rewrite `building_resettlement_colony` and its PM groups; keep `state_resettlement_transfer_add` as the capacity type.
- Existing colonies in saves: their deleted PMs fall back to each group's first PM, and a colony in a state that is not a
  frontier is removed by the closure rule on the first pulse (with the §8 notification). No other migration step.
- Update `common/_meta/duplicate_image_allowlist.yml`, loc, `docs/systems/mod_systems.md` (replace the one-liner) and
  `docs/engine` regenerated reports.

## 12. Numbers — first estimates, calibrated in the plan

| Quantity | First estimate | Anchor |
|---|---|---|
| Capacity per level | Land Grants 300, Military Colonies 250, Penal 100, Organized Colonization 500, Special Settlements 1,000, Development Program 800, Rustication 800, Managed Retreat 600 people/month | Organized Colonization with rail at 10 levels moves 84,000 a year: an empty Kansas closes in about 23 years (historically 1860–1890). Three Siberian Authorities at 15 levels move about 378,000 a year, Stolypin's rate |
| Staff per level | about 100 bureaucrats + 100 clerks (coercive programmes: soldiers instead of clerks); Work Settlements add 100 laborer slots | small enough that a sparse frontier can staff the first levels (§2) |
| Transport add per level | Overland 0, Rail and Steamship +200, Motor +400, Airlift +600 | — |
| Per-pop monthly cap | 2% (4% under a drive) | vanilla emigration ceiling |
| Transit mortality | Penal 5%, Special Settlements 15%, Rustication 1% | archival counts for the special settlements run to hundreds of thousands |
| Intensity reference | 0.25% of population a year | Stolypin's peak |
| IG caps | §7.2 | `00_defines.txt` law-change approval (5 / 10 / 20) |
| Frontier thresholds | open < 2/km², close ≥ 10/km² | §6 |

The frontier thresholds and IG caps were calibrated against data before the plan. The remaining numbers are first
estimates, checked in play (the debug event prints each month's flows).

## 13. Tests, docs, in-game checks

- **`test_resettlement_programme_registry.py`:** one `PROGRAMMES` table pinning every site a programme touches (PM,
  loc, recruitment-rule branch, transit mortality, volume counter, politics modifier, law gates, events, Declaration
  line). It is the add-a-programme checklist, like `test_covert_op_registry.py` and `test_un_convention_registry.py`.
- **`test_region_area.py`:** every land state region has exactly one positive area in the generated file, and spot
  areas stay within 12% of reality.
- **Debug:** `te_debug_resettlement` in `events/te_debug_*` (force a destination, jump a month, print flows) and
  `TE_RESETTLEMENT:` lines in `debug.log` for each month's sources, recruits, deaths and arrivals. The first run answers
  the five engine questions above.
- **CI:** the `--strict` audits (`event_image`, `silent_variable`, `event_context`, `modifier_multiplier_var`,
  `loc_render`) cover the new events and modifiers.
- **Docs:** a `mod_systems.md` section, `concept_internal_resettlement`, and an in-game checklist in the PR body.

## Out of scope (possible extensions)

- A programme that systemically draws on low-acceptance pops (owner: acceptable in principle, not needed now). It would
  never offer a culture or religion by name.
- A destination absorption limit tied to infrastructure (the Trans-Siberian bottleneck).
- Later events: a penal-colony mutiny, tickets of leave, soldier-settler petitions, boomtowns, managed-retreat holdouts.
- Wartime evacuation of industry (the Soviet 1941 move east).
- A state-panel tile.
- Per-state global-warming damage (so Managed Retreat can read a flooded state directly).
