# Transport goods: local transportation, shipping between markets, and free infrastructure — design

## Context

Issue #1050: late-game AI countries pay permanent subsidies on ports and railways. The save reading of 2026-10-21
(issue comment https://github.com/jakeOmega/Vic3TimelineExtended/issues/1050#issuecomment-6325951756; data and
scripts in `/mnt/d/vic3te-data/issue1050-2026-10-21/`) found the cause:

- Ports and railways earn on freight and lose on the method that makes `transportation` (cruise ships, maglev trains).
  That good is local to the state, and these buildings are sized for freight, so their own output floods their state
  and sells at the mod's price floor (£0.03–0.50 against a base of 30; `PRICE_RANGE = 0.999`).
- Infrastructure is 80–99% spare in every state that pays. Companies, not governments, build the levels.

The comment proposed splitting personal transport into its own buildings. The owner rejected that (2026-10-21): the
expensive part of a railway serves passengers and freight alike, and a player whose people grow rich while their
freight is in surplus should not have to downsize railways and build a second network. Talking it through, the owner
found the three roles muddled:

- **Infrastructure** is a free capacity stat (the market-access cliff below 100%, nothing above it). Nobody pays for
  it. The buildings that supply it are paid only through the goods they sell.
- **Bulk Transportation** (engine `merchant_marine`, renamed by the mod) is freight, traded across the whole market,
  and also ocean shipping. It is in effect the channel that pays for infrastructure. But the payment is market-wide and
  the capacity is local, so it sends no signal about where infrastructure is needed (`docs/systems/mod_systems.md`
  § "Bulk Transportation (Merchant Marine relocalization)").
- **Personal Transportation** (engine `transportation`) is local passenger travel.

The bulk/personal split predates vanilla's merchant marine and the current trade system, so its reasons no longer
apply (owner).

## Intent

Give each concept one clear role, cut by geography rather than by customer, as vanilla's goods were:

- **`transportation`, local to the state:** all movement of people and goods inside a state. Pops buy it to travel;
  buildings buy it to move their own inputs and outputs. Railways, highways, urban transit and ports produce it.
- **`merchant_marine`, priced across the market:** movement between markets (trade, port connections, convoys). Ports
  produce it; railways no longer do.
- **Infrastructure:** the free network constraint, supplied by the network buildings.

Why this is the right cut:

- **Shared capital.** One railway's output serves whoever buys it locally. When demand shifts from freight to
  passengers, nothing has to be torn down or switched.
- **Payment where the network is used.** Industry buys freight in its own state, so a busy state with too few railways
  has dear transport, and railways earn and expand there. A state with a surplus has cheap transport, and the surplus
  stops being paid for.
- **No permanent AI subsidy for transport buildings.** Infrastructure no longer depends on a railway's staffing (§ 3.1),
  and the price signal does the job the `must_have` subsidy did.

## Goals

1. AI railways and ports no longer need permanent subsidies, and the AI stops subsidizing both.
2. Personal and industrial demand draw on one local good, so a railway's output follows its state's total demand.
3. Merchant marine means shipping between markets.
4. Infrastructure keeps its role and doesn't collapse when a transport building loses money.

## Non-goals

- Changing `PRICE_RANGE` or `BUY_SELL_DIFF_AT_MAX_FACTOR`. They are global, and the issue's what-if showed little gain
  (India's 2048 port subsidy £42.9M → £33.8M a week at vanilla's floor).
- Level caps on ports or railways. A railway cap is ruled out (owner): nothing else could supply transport or
  infrastructure without limit.
- A separate passenger building (rejected above).
- Migrating old saves. The coming vanilla patch is expected to break saves anyway (owner).
- The other candidates from #1050: 2A (a transport-input ramp on tight states), 2B, 4A, 4C, the `can_build_private`
  gate and the AI-define experiment. Revisit them only if the observer run (§ 7) shows a need.

## Anti-goals

- **Local transport as a hard limit on industry.** It must be possible to build railways in every state (the owner
  says that holds), and a shortage should be a delay while they get built, not a wall.
- **Infrastructure that falls when a railway loses money** (the spiral vanilla's `must_have` guards against).
- **Ports or railways flooding their own state again** through a passenger tier that carries costly inputs of its own.

## 1. Goods

### 1.1 `transportation`

- Stays `local = yes`, base price 30 (`REPLACE:transportation`, `common/goods/timeline_extended_extra_goods.txt:71-81`).
- Loc: drop "Personal". A plain name such as "Transportation" (vanilla's) or "Local Transportation" is the builder's
  call. The name is set in `localization/english/replace/timeline_extended_override_l_english.yml:26`.
- Consumers: today's consumers stay (pops' needs, urban centre retail, tourism, national parks, youth centres,
  resettlement), plus every Bulk Transportation consumer that moves to it (§ 2).

### 1.2 `merchant_marine`

- Stays as vanilla defines it (base price 50, market-wide, `traded_quantity`, `convoy_cost_multiplier`).
- Loc: back to shipping. "Merchant Marine" (vanilla) or a near name is the builder's call
  (`timeline_extended_override_l_english.yml:23`).
- **Consumers, first pass: trade only** (owner), meaning Trade Centres and any mod production method whose
  input stands for trade between markets. The engine's own consumers stay automatically: port connections for
  overseas states, convoys and goods-transfer treaties aren't production methods. Other candidates may be added
  after a review of the list (§ 2).
- **Producers: ports, company buildings that stand for shipping or trade, and possibly airports** (owner). Railways and
  highways stop producing it.

### 1.3 Prestige goods

A local good can't carry a prestige good (owner's experiments; `prestige_good_roster_audit` already flags one). So every
transport prestige good stays on `merchant_marine`: vanilla's `prestige_good_generic_merchant_marine` and the mod's
`prestige_good_integrated_logistics` (`common/prestige_goods/extra_prestige_goods.txt:67-71`).

Every company listing one must keep a roster building (`building_types`, not `extension_building_types`) that still
produces merchant marine. At the time of writing:
- Jardine Matheson (generic merchant marine; roster port, trade centre): ports keep producing it.
- Amazon, SAP and Shopify (integrated logistics). Amazon's roster has `building_port`; check SAP and Shopify. Any
  whose roster no longer makes merchant marine needs a different prestige good, or a roster building that makes
  merchant marine.

`prestige_good_roster_audit --strict` catches each one in CI.

Also check `company_amazon`'s `possible` trigger: it uses `"goods_production_rank(g:merchant_marine)" <= 3`
(`extra_companies_flavored.txt:831`). Whether it should read `transportation` after the change is the builder's call.

### 1.4 External Trade principles

The `goods_input_merchant_marine_mult` discounts stay (owner: on-brand, and now apply only to external trade, which
fits). They may be strengthened, since they now touch a smaller base: −0.10 and −0.25
(`common/power_bloc_principles/modified.txt:55,66`), −0.25 and −0.30 (`extra_power_bloc_principles.txt:606,636`). The
amount is the builder's call.

## 2. Consumer conversion

About 106 production methods take `goods_input_merchant_marine_add` today: 100 in `common/production_methods/extra_pms.txt`
and 6 in `te_construction_market_pms.txt`. Each one is classified:

- **Moves to `transportation`** (the default): rail and road transport tiers in extraction and agriculture, cold chain,
  construction sectors, mine techniques, advanced industry and automation, retail.
- **Stays on `merchant_marine`**: trade only in the first pass. List the ones kept and why in the PR.

**Construction Sectors move too** (owner, 2026-10-21: "conceptually cleaner … not super hard to swap back"). They are
most of the good's building demand. In the #1050 extracts (`/mnt/d/vic3te-data/issue1050-2026-10-21/ex/b_*.json`)
they bought 69% of the merchant marine that buildings bought in 2040, 76% in 2048 and 68% in 2058; Trade Centres
bought 14–18%. Two consequences:

- **Ports become several-fold fewer**, because the good's buyers are now trade and the engine's own uses only. Their
  methods stay as they are (owner): the number of levels falls to match demand (§ 3.2).
- **Construction buys its freight where Construction Sectors sit.** Converting the 2048 save as it stands would leave
  its biggest construction hubs 5–13× short of local transport. Those hubs have Construction Sectors of 2,341–5,182
  levels beside 4–81 railway levels. In a fresh game the two should grow together through the price branch of the
  railway's auto-expand. The earlier-saves check (§ 7) shows whether the hubs are short in earlier eras too.
- **The fallback** if the observer run shows construction choking: return the construction methods' input to
  `merchant_marine`. The conversion script should make that a one-flag rerun.

How the conversion is done:

- **Scale the quantity by price**, so each method's spend is unchanged: units × 50/30. Rounding is the builder's call;
  methods' input quantities are usually whole or half numbers.
- **Write the conversion as a Python script** (owner: largely scriptable). It is a one-off, and can live under
  `scripts/generators/` or a scratch path. The cost comments the regenerator owns (`# Price: …`) come from `pm_costs` and
  are regenerated, not hand-edited (`docs/auto_generated_files.md`).
- Generated files are never hand-edited; if a generator emits these inputs, edit its input.

Producers outside the four buildings: the company buildings in `unique_pms.txt` (26 output sites) and in `extra_pms.txt`.

- Logistics, fulfilment, rail and road hubs move to `transportation`.
- Trading houses, shipping companies, docks and wharves stay on `merchant_marine`.
- Rescale outputs by 50/30 the same way.

## 3. The four infrastructure buildings

### 3.1 Railway

- **Base methods produce `transportation` instead of `merchant_marine`**, rescaled by 50/30 to keep margins
  (`pm_early_trains` … `pm_autonomous_trains`; several are `REPLACE:` in `extra_pms.txt` from line 13825).
- **Total local demand will rise** once industry's freight moves to `transportation`. Railway output per level has to
  be enough to meet it at a sensible number of levels. Check it against the 2048 and 2058 saves' consumption (§ 7).
- **Infrastructure per level, not per worker** (owner): move each base method's `state_infrastructure_add` from
  `workforce_scaled` to `level_scaled`. An unstaffed or unprofitable railway still supplies its network.
- **Passenger group**: keep it as vanilla has it, an upgrade that buys extra output for extra inputs (owner). Rename the
  group in the mod's replace loc to **"Rolling Stock"** (owner), since much of the output now goes to industry. The
  tiers stay. The mod's `pm_bullet_trains` and `pm_maglev_trains`, injected into vanilla's `pmg_passenger_trains`
  (`common/production_method_groups/extra_pm_groups.txt:661-667`), get modest inputs per unit of output. Their numbers
  are the builder's call.
- **Auto-expand stays vanilla's for now** (owner, 2026-10-21). Vanilla's rule
  (`11_private_infrastructure.txt:212-231`) has three parts:
  - 80% staffing
  - cash reserves above half, or a subsidy
  - dear transport (`sg:transportation` more than 50% above base) or an infrastructure shortfall of 20.

  The owner wanted the shortfall branch to ignore staffing. That needs a `REPLACE:building_railway`, because
  `should_auto_expand` is a trigger block. The engine refuses a second one from an INJECT ("Trigger section already
  read earlier", `docs/guides/scripting_best_practices.md` § "A second trigger block is rejected at load"), and an
  added block couldn't lift vanilla's staffing test anyway. The REPLACE is deferred because two things already cover
  most short states:
  - Infrastructure per level removes the main spiral.
  - Under the new model, a state short of infrastructure with industry has dear transport, so the price branch fires.

  If the observer run shows states staying short (§ 7), take the REPLACE: restate vanilla's whole building, including
  its `ai_value` branches, plus the mod's `pmg_maintenance_heavy` INJECT (`common/buildings/extra_buildings.txt:1134-1138`).
- **Subsidies: the AI stops subsidizing railways** (owner), with an observer run first (§ 7). Set `building_railway =
  should_remove` in the seven administrative strategies (`common/ai_strategies/te_power_plant_subsidy_strategies.txt`,
  the route #981 proved for power plants). Extend `test_power_plant_subsidy_strategies.py` or add a sibling test.
- With infrastructure per level and no subsidy, the engine's own auto-downsize trims railways that stay unprofitable
  and empty. It needs privately held empty levels and a six-month wait (`AUTO_DOWNSIZE_*`, `00_defines.txt:395-399`).
  That's intended: it removes surplus where nobody buys.

### 3.2 Port

- **Base methods produce `merchant_marine` plus infrastructure.** At normal prices shipping alone should pay for the
  port (owner).
- **The base methods stay as they are** (owner). Construction no longer buys merchant marine (§ 2), so demand falls
  to trade and the engine's uses. Port levels should fall several-fold to match, through ordinary construction and
  auto-downsizing. Coastal states lose that port infrastructure, and railways supply it instead.
- **Infrastructure per level as well**, for consistency. Today's amounts (15–50 per unit) can be trimmed, since the
  AI's preference for big buildings piles them into hubs (Bombay 2048: 163,071 against 2,099 used). Whether to trim is
  the builder's call.
- Ports may also produce a little `transportation` in their base methods, for ferries and moving goods around the docks.
  The amount is the builder's call: small next to merchant marine (owner).
- **The passenger group** (`pmg_water_personal_transport`, the mod's own,
  `common/production_method_groups/extra_pm_groups.txt:1380-1391`) **stays separate** (owner: it gives control).
  - Its tiers get modest inputs, so a flooded tier loses little. Magnetic Drive Cruise Ships today costs £2,400 of
    inputs per unit for £3,150 of output at base price.
  - **Revisit `ai_selection`.** `most_productive` was set in #735 because a port that was nearly its state's only
    supplier swung the price from floor to ceiling when it turned the method off. Once industry buys transport
    locally, a port is one supplier among many, and `most_profitable` should settle. Pick one and say why.
- **Subsidies: the AI stops subsidizing ports too** (owner): `building_port = should_remove` in the same seven
  strategies as railways (§ 3.1), tested in the same observer run.

### 3.3 Highway

- Its methods' `merchant_marine` output becomes `transportation`, rescaled.
- **Auto-expand stays at 80% staffing alone** (owner: these are built mainly for their modifiers, so expanding while
  unprofitable is usually wanted).
- The construction-system laws' forced subsidies stay (owner: highways are level-capped, so the bill is bounded).

### 3.4 Airport

- `transportation` for passengers, plus possibly some `merchant_marine` for air cargo between markets (owner: "maybe").
  The ratio is the builder's call; keep merchant marine the smaller part.
- Auto-expand and forced subsidies as for highways.

## 4. Infrastructure

- It stays a free stat, with market access as vanilla computes it.
- Its sources move to per level on railways and ports (§ 3.1, § 3.2). Highways, airports, population and the base value
  are unchanged.
- Pre-railway industry tiers that need transport have the same problem vanilla has with infrastructure. That's
  accepted (owner).

## 5. Player-facing text and the guide

- **Loc:**
  - the two goods' names and descriptions (§ 1)
  - every loc string that names Bulk or Personal Transportation (`git grep -i "bulk transportation\|personal
    transportation" -- localization/english`)
  - "Rolling Stock" for the passenger-trains group.
- **Player guide** (one PR with the change, PDF rebuilt): `02-timeline.md` (goods rename table, lines 233-238; Transport
  row, line 431), `03-economy.md` § "Bulk Transportation and freight" (line 362 on, rewrite as the transport model),
  `15-climate.md` (Public Transit row), `17-reference.md` (lines 17, 67), `01-introduction.md` (line 184). Follow
  `docs/player_guide/STYLE.md`.
- **Docs:**
  - `docs/systems/mod_systems.md` § "Bulk Transportation (Merchant Marine relocalization)": rewrite to the new
    model, keeping the Trade Centre seeding paragraph.
  - `docs/vanilla/vanilla_economy_reference.md` § 17.1 cross-references it.

## 6. Other references to check

- AI `goods_stances` that name either good (`common/ai_strategies/edited_default_strategy.txt`; vanilla's
  `00_default_strategy.txt`).
- The tax system's generated merchant marine values (`common/script_values/te_tax_generated_support_values.txt`,
  customs import/export slots). These are generated: rerun their generator, don't edit.
- Modifier types: `goods_input_merchant_marine_mult` / `goods_output_merchant_marine_mult` stay registered
  (`mod_entity_modifier_types.txt:641,650`). Register `goods_input_transportation_mult` only if something uses it.
- Strategic reserve, treaty articles, events and GUI that read either good: `git grep -n "merchant_marine\|g:transportation\|sg:transportation"`.
- `test_*.py` files that pin Bulk Transportation behaviour (search for `merchant_marine`).

## 7. Verification

- **Offline:** the full CI gate (`docs` § Common commands in `CLAUDE.md`), including `prestige_good_roster_audit
  --strict`, `organize_loc.py --check`, the player guide style and staleness checks, and the audits on `POST /reload`
  from a server started in this worktree.
- **Before release, an observer run** (owner: "nothing weird"). The run's length is the builder's call: a late-game
  start or a run into the 2040s. Things to look at, my call as the definition of "weird":
  - AI subsidy totals on railways and ports, against the #1050 table (£24–55M a week on ports, £27–48M on railways).
  - Local `transportation` prices: not pinned at the floor or the ceiling in most states.
  - Market access: few states below 100% that weren't before; no rising count of states short of infrastructure after
    subsidies stop.
  - Shortage penalties on industry: not widespread.
  - Railway and port levels: growing where transport is dear, not piling into states with a large surplus.
  - Passenger-group switching and `pm_retooling` share on ports and railways: not higher than the #933/#1050 baselines.
  - Bankrupt AI countries: not more than the 80–83 of about 110 in #1050.
- `scripts/analysis/save_world_report.py` and the #1050 scripts (`/mnt/d/vic3te-data/issue1050-2026-10-21/scripts/`)
  read most of these from saves.

- **Before building: the earlier-saves check** (owner). Rerun the construction-hub shortage check on earlier saves of
  the same game (1866–2023) to see whether the hubs are short of local transport in earlier eras too. Result: § 10.
- **Observer run, if construction chokes:** construction hubs short of `transportation` with output penalties, or
  construction points falling against the baseline. Then take the § 2 fallback.

## 8. Open

(Settled 2026-10-21: the AI unpins **both** railways and ports in the first build, owner. If neither causes trouble,
the fix is complete. The saves can tell the two apart by building type: ports sit in coastal states, carry their own
subsidy and staffing records, and supply their own share of infrastructure.)

## 9. Left to the builder

- Exact quantities: rescaling, railway output against the new demand, passenger tiers' inputs, ports' small
  `transportation` output, the airport ratio, the strength of the External Trade discounts.
- Names for the two goods (§ 1.1, § 1.2).
- The full consumer and producer classification (§ 2), listed in the PR.
- `ai_selection` for the water passenger group (§ 3.2).
- How the conversion script is written and where it lives.

## 10. Earlier-saves check (2026-10-21)

The construction-hub test, rerun on earlier saves:
- **A**, a state's local `transportation` demand from buildings after the change: their own transportation input plus
  their merchant marine input × 50/30, Trade Centres excepted.
- **B**, its local supply after the change: today's transportation output plus railway and highway merchant marine
  output × 50/30.

The saves are the France → EU playthrough (c480d386) from 1867 to 2048, plus Wallachia 1849 and Greece 1866 from
other playthroughs. All are 1.14.5. Data:
`/tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/6ce56e21-fca8-4323-9941-ecaa9b9da181/scratchpad/early_saves/out/`
(copied to `/mnt/d/vic3te-data/issue1050-2026-10-21/early_saves/out/`).

| Save | Construction's share of merchant marine bought by buildings | Construction's converted demand in states over 2× short | Top hub (Construction Sector / railway levels, A/B) |
|---|---|---|---|
| Wallachia 1849 | 1.8% | 6% | New York 24 / 0, 0.45 |
| Greece 1866 | 2.0% | 12% | New York 34 / 0, 0.24 |
| France 1867 | 2.9% | 8% | Île-de-France 28 / 1, 0.55 |
| Fr. Commune 1917 | 29% | 10% | Lombardy 47 / 5, 3.1 |
| Fr. Commune 1949 | 48% | 27% | Corsica 155 / 1, 4.6 |
| Fr. Commune 1976 | 50% | 40% | Corsica 356 / 1, 5.4 |
| France 1990 | 51% | 65% | Alsace-Lorraine 1,342 / 11, 4.4 |
| EU 2023 | 75% | 63% | Alsace-Lorraine 2,691 / 81, 5.0 |
| EU 2048 | 76% | 53% | Galicia 5,182 / 4, 14.0 |

- **Not in the 19th century.** Construction's freight is negligible then: the construction methods take 0, 0.5, 10,
  20 and 25 merchant marine per unit from the wooden tier to era 7. Every top hub has spare local transport.
- **From about 1917 to 1949 on, yes.** Hubs of 140–360 Construction Sector levels sit next to 1–7 railway levels and
  are 2–7× short. By 1990 most of construction's freight sits in states more than 2× short.
- **These saves can't say whether railways would follow construction under the new model**, because the old model
  gave them no reason to: construction bought its freight market-wide. Over 180 years Alsace-Lorraine's Construction
  Sectors went from 3 to 4,380 levels and its railways from 1 to 81. The saves show the build-out needed, not whether it
  happens. For scale, Construction Sectors bought 47 merchant marine a level in 2048 (about 2× the nominal 25, from throughput),
  which is 79 `transportation` a level after conversion. A late railway method makes 108–133 a unit before throughput.
  So a 4,380-level hub would need roughly 1,500–3,000 railway levels in its own state, depending on the railways' throughput.
- **From 1917 on the top hubs are the player's** (France, then the EU). The AI's hubs are 3–7× short too (Louisiana,
  Sichuan, Tennessee), with a smaller share of its construction in them.
- **The early saves look fine partly because of the passenger surplus.** The test counts today's transportation output,
  mostly ports' passenger output, as available to construction. Counting only the railways' and highways' converted
  output, every save is short, the 19th century included (80–96% of construction's demand).
- **What this means for players:** a player will have to build railways in their construction hub states. The hub's
  transport price shows the need. The player guide's economy chapter should say so (§ 5).
