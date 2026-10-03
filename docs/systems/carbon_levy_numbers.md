# Carbon levy: numbers for owner review

Phase 1 of Task 16 (plan: `docs/superpowers/plans/2026-10-02-legislated-tax-code-tasks.md`; research: `.superpowers/sdd/2026-10-02-legislated-tax-code-tasks/research/F_carbon_tax.md`). The owner chose design C on 2026-10-02. This page proposes the magnitudes. **No game script changes until the owner approves them.**

**Labels.** **[static]** is computed from the script at base prices (merged vanilla 1.14.5 snapshot + mod `common/`). **[inf]** is inferred from the engine model and not confirmed in game. **[assume]** is an assumption chosen for illustration. **[ext]** is external economics, given only as orientation.

**Units.** Every building figure is per level, per week, at full staffing and base prices. Profit is taken as **15% of revenue** [inf]. The 1.14.5 defines `BUILDING_PROFIT_TARGET_TO_RAISE_WAGES = 0.20` and `…_TO_LOWER_WAGES = 0.10` move wages until the margin sits between 10% and 20% when labour is the constraint (the mod does not override them). Where labour is plentiful, margins run higher and every "% of profit" figure below shrinks. "Net cost" is positive when the user loses and negative when it gains.

---

## 1. What changes and why

| Today's `carbon_tax_modifier` field | What it actually does | Defect |
|---|---|---|
| `building_group_bg_coal_mining_tax_mult = 1` | nothing | `bg_coal_mining` is a vanilla legacy group with no buildings; coal mines are in `bg_mining` |
| `goods_output_coal_mult` / `goods_output_oil_mult = -0.10` | −10% output for every coal/oil producer in every member, including the carbon-capture plants, whaling and fuel companies | Emissions are measured as market *consumption*, so a supply cut barely moves them: imports fill the gap or the price rises |
| `building_group_bg_oil_extraction_tax_mult = 1` | +100% income tax on oil-rig *workers* (probe R1b) | A payroll tax in one fossil sector. Fuel users and owners pay nothing, and there is no price signal |
| `building_group_bg_manufacturing_tax_mult = 0.1` | +10% income tax on all light and heavy industry workers | A general payroll tax, unrelated to fuel |
| `country_greenhouse_gas_emissions_mult = -0.20` | −20% on the market's figure, by decree, counted only at the leader | Does all of the policy's emissions work, with no mechanism behind it |

A bare `goods_input_coal_mult` / `goods_input_oil_mult` cut is the obvious fix, and it does lower the measured figure in every member that holds it. Alone, though, it is a **subsidy to fuel users**: they produce the same output from less fuel, the fuel price falls as well, and fossil processes become *cheaper* relative to electric ones (research F §c, §d).

**Design C.** Each band is one static modifier, `te_carbon_band_<k>`. It cuts building coal and oil input by a_k, with diminishing returns as k rises. On the named fossil-burning building types it charges a compliance cost as a small throughput cut b_k, so the cost lands where the fuel saving lands. There is no output cut on producers and no payroll tax; coal and oil producers lose through the lower fuel price.

On top of that, a scripted **levy** of τ_k money per unit of residual coal and oil consumed is moved each month from the investment pool into the treasury, overdraft-guarded. Each country pays on its own consumption. With the tax-code rule on, the band is a provision of the market leader's code, and members see it as imposed. With the rule off, the existing Adopt and Repeal controls switch between band 0 and one default band.

---

## 2. Inputs

### 2.1 Base prices [static]

`goods.json` (vanilla 1.14.5) with the mod's `common/goods/timeline_extended_extra_goods.txt` overrides.

| Good | coal | oil | electricity | steel | iron | engines | tools | sulfur | fertilizer ("Chemicals") | merchant marine | construction (mod) | electronic components (mod) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Base price | 30 | 40 | 30 | 50 | 40 | 60 | 40 | 50 | 30 | 50 | 1000 | 80 |

### 2.2 Who burns coal and oil, by consumer group [static]

Coal and oil per level at the group's PMs. Ranges cover a PM group's alternatives, only one of which is active. Sources: research F §b (PM scan of all 545 buildings) and `research/pm_coal_oil.tsv`.

| Group | Coal / level | Oil / level | Clean alternative already in the PM set |
|---|---|---|---|
| Power (`building_power_plant`) | 5–25 | 25–35 | Separate building types: renewable, hydro, nuclear, fusion |
| Steel (`building_steel_mill`) | 30 (+5–10 with automation) | – | Microgravity alloying only |
| Chemicals (`building_chemical_plant`) | – | 20–220 | Molecular foundry |
| Synthetics (rubber, dyes, silk, synthetic oil, explosives) | 10–180 | 10–100 | – |
| Rail; ports; shipyards | rail 2–6; port 5–10; shipyard 10 | rail 8–11; port 10–15; shipyard 30–35 | Electric trains |
| Road / air (highway, airport) | – | 50 / 10 | – |
| Motor industry, military industry | 5–20 | 5–55 | Electric engines, fuel cells |
| Light industry (glassworks, food, furniture, paper, tooling) | 5–15 | 5–30 | – |
| Mining equipment (every mine, including coal mines) | 4–15 | 1–10 | – |
| Agriculture, fishing, whaling, logging | 1–20 | 2–15 | – |
| Military upkeep (charged to military buildings) | – | 1–20 per unit | – |
| Pops (`popneed_heating`, weights coal 2 / oil 3) | budget-limited | budget-limited | Electricity (weight 3) |

### 2.3 Main users at common PMs: cost structure [static]

The secondary PM groups are set as shown in brackets, and maintenance PMs are included. VA (value added) = revenue − all inputs; wages and profit come out of it.

| User [PMs] | Coal | Oil | Fuel bill | Other inputs | Revenue | VA | Fuel / revenue | Fuel / VA | Employees |
|---|---|---|---|---|---|---|---|---|---|
| Power: coal-fired [manual, maintenance] | 20 | 0 | 600 | 510 | 1500 | 390 | 40% | 154% | 1000 |
| Power: oil-fired [manual, maintenance] | 0 | 25 | 1000 | 750 | 2400 | 650 | 42% | 154% | 1000 |
| Power: modern coal [central control, basic emissions control] | 25 | 0 | 750 | 1470 | 2700 | 480 | 28% | 156% | 580 |
| Power: modern oil [same] | 0 | 35 | 1400 | 1770 | 4200 | 1030 | 33% | 136% | 580 |
| Steel: open hearth [no automation] | 30 | 0 | 900 | 3700 | 6000 | 1400 | 15% | 64% | 5000 |
| Steel: electric arc [rotary valve] | 40 | 0 | 1200 | 5200 | 7500 | 1100 | 16% | 109% | 3000 |
| Steel: chromium substitution [bespoke alloys] | 30 | 0 | 900 | 12070 | 15000 | 2030 | 6% | 44% | 1510 |
| Chemicals: nitrogen fixation [continuous processing] | 0 | 20 | 800 | 3830 | 6000 | 1370 | 13% | 58% | 3850 |
| Chemicals: catalytic cracking [advanced process control] | 0 | 120 | 4800 | 4355 | 12000 | 2845 | 40% | 169% | 2500 |
| Chemicals: polymerisation [same] | 0 | 160 | 6400 | 7605 | 18000 | 3995 | 36% | 160% | 2500 |
| Synthetic rubber: polyisoprene | 0 | 50 | 2000 | 1400 | 4000 | 600 | 50% | 333% | 5500 |
| Motor industry: diesel engines [assembly lines] | 0 | 55 | 2200 | 2950 | 7200 | 2050 | 31% | 107% | 3000 |
| Railway: steam trains [steel carriages] | 5 | 0 | 150 | 700 | 1200 | 350 | 12% | 43% | 1200 |
| Railway: diesel trains [double-decker] | 0 | 8 | 320 | 1150 | 2400 | 930 | 13% | 34% | 1250 |
| Port: industrial [paddleboats] | 10 | 0 | 300 | 850 | 1900 | 750 | 16% | 40% | 1000 |
| Port: modern [cruise ships] | 0 | 15 | 600 | 1800 | 3600 | 1200 | 17% | 50% | 1000 |
| Highway: civil | 0 | 50 | 2000 | 2550 | 5500 | 950 | 36% | 211% | 1500 |
| Glassworks: plastics [bottle blowers] | 0 | 25 | 1000 | 1500 | 4000 | 1500 | 25% | 67% | 2500 |
| *Producer:* coal mine, diesel pump [dynamite, rail] | (115 out) | 5 | 200 | 1175 | 3450 | 2075 | 6% | 10% | 4250 |
| *Producer:* oil rig, combustion derricks | – | (100 out) | 0 | 875 | 4000 | 3125 | 0% | 0% | 4000 |
| *Producer:* oil rig, offshore | – | (300 out) | 0 | 7100 | 12000 | 4900 | 0% | 0% | 1750 |

What the table decides:

- **Fuel / VA is the abatement-economics number.** Where it exceeds 100% (fossil power, chemicals from cracking onward, synthetic rubber, highways, diesel engines, steel with automation), a 10% fuel saving is worth more than 10% of value added.
- **Power is fuel-heavy at ~1.5× VA**, and it is the one user with a clean *building* substitute. Its in-building profit therefore steers construction between coal and renewables.

### 2.4 Input cuts already in force [static]

All of these are country-scope `goods_input_*_mult` and stack additively with a band [inf]. Nothing floors these keys in script.

| Source | Coal | Oil | Note |
|---|---|---|---|
| Sustainability principle tiers I–V (member modifier) | −5 / −10 / −15 / −20 / −25% | same | Tier V's institution modifier adds −5% more. Each tier *also* carries an equal emissions-multiplier cut, so the principle is counted twice |
| Fossil-fuel divestment (national) | −5% | −5% | |
| Public transit (national) | – | −5% | |
| Company prosperity (`extra_companies_generic.txt:153`) | – | −5% | Per company |
| Worst case today + band 4 (proposed) | −35% −18% = **−53%** | −40% −15.5% = **−55.5%** | Far from −100%. The SR hub idles a good at −1 building-scope flow, and a country-wide −a makes that −a: negative or clamped [inf] |

### 2.5 Emissions-multiplier grantors [static]

`gw_emission_multiplier_script_value` = 1 + the **market leader's** `country_greenhouse_gas_emissions_mult`, floored at 0 (`extra_script_values.txt:897-916`). Members' multipliers never count.

| Cuts | Value | Raises | Value |
|---|---|---|---|
| Carbon tax (today) | −20% | Fossil lobby concessions | +10% |
| Renewable investment | −15% | Climate measures sunset | +10% |
| Emission standards | −10% | Climate dismissal boost | +5% |
| UN climate regime, high emitter | −8% × enforcement | Climate accord rejection | +5% |
| Climate summit leader / pledge | −5% / −3% | Climate deregulation | +5% |
| Ministry of the Environment institution | −5% per investment level (max 9) | Climate victory dividend | +5% |
| Sustainability principle I–V | −5% … −25% | Directed credit, heavy industry | +5% |
| | | Environment grandfather clause (amendment) | +5% |

### 2.6 Emissions metric and price model [static]

- **Metric.** Market emissions = 2 × (market coal + oil `market_goods_consumption`) / 10000 × leader multiplier + capture (`extra_script_values.txt:764-787`). Coal and oil weigh the same per unit. Consumption means buy orders, with exports excluded.
- **Price defines.**

  | Define | Mod (`extra_defines.txt`) | Vanilla 1.14.5 | Consequence |
  |---|---|---|---|
  | `PRICE_RANGE` | 0.999 | 0.75 | Prices can move from 0.1% to 199.9% of base |
  | `BUY_SELL_DIFF_AT_MAX_FACTOR` | 4 | 2 | Price hits its cap or floor at a 4:1 order imbalance |
  | `GOODS_SHORTAGE_PENALTY_THRESHOLD` | 0.25 | 0.5 | No shortage penalty unless supply / demand < 0.25 |

  A 10% demand shift moves the price by **about 4% to 13%** [inf, research F §d bracket].

### 2.7 Measurements still needed (in game)

1. **Building vs pop share (s_B) of coal and oil consumption**, in 3–4 large markets at 1900 / 1950 / 2000 / 2050: Market panel buy-order breakdown, or a `te_debug_gw` dump of `market_goods_consumption` and Σ `state_goods_consumption`. Everything below uses s_B = 0.85 [assume]. The default-band choice holds for s_B anywhere in 0.7–0.9; at 0.95, band 2 (≈ −17%) edges nearer to −20% than band 3 (≈ −23%).
2. **Δprice for a known Δdemand** (apply −20% `goods_input_coal_mult` to one member and log the coal price before and after). This settles the 4–13% bracket and the producer loss in §3.4.
3. **Investment-pool weekly gross income** for 3–4 industrial countries, against the levy in §3.3. This is the main calibration risk (Q4).
4. **How throughput and input mult compose on fuel quantity.** Is it (1 − b)(1 − a) or 1 − a − b? Do country and building contributions of one `_mult` add? The tables assume multiplicative and additive respectively [inf].
5. **SR hub with a country-wide input cut active**: does the oil flow go negative or clamp, and does the booking drift [inf]?
6. **Script readability [inf]:** `modifier:goods_input_coal_mult` in a country-scope script value (for the pie, §4), and `state_goods_consumption` under a state-goods scope (`sg:coal`) as a script-value term (for the levy base).
7. **Realised profit margins** of power plants and steel mills, to replace the 15% assumption.
8. **Does a country `goods_input_oil_mult` reach military unit upkeep?** Vanilla uses the key only in mobilization options. If it does, every band also cuts army oil upkeep.

---

## 3. Proposed bands

### 3.1 Band values

| k | a_coal (`goods_input_coal_mult`) | a_oil (`goods_input_oil_mult`) | b_power (`building_power_plant_throughput_add`) | b_other (4 types, below) | τ_k: levy per unit of residual coal or oil | τ as % of base price, coal / oil | m_k (`country_greenhouse_gas_emissions_mult`) |
|---|---|---|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 | 0 | – | 0 |
| 1 | −6% | −5% | −8% | −2% | 2.5 | 8.3% / 6.3% | −2.5% |
| 2 | −11% | −9.5% | −13% | −3.5% | 5 | 16.7% / 12.5% | −5% |
| 3 | −15% | −13% | −17% | −4.5% | 7.5 | 25% / 18.8% | −7.5% |
| 4 | −18% | −15.5% | −20% | −5.5% | 10 | 33% / 25% | −10% |

b_other applies to `building_steel_mill`, `building_chemical_plant`, `building_synthetics_plant_rubber` and `building_highway` (all registered throughput keys). These are the types whose common PMs nearly all burn coal or oil. Railway, port, motor industry and glassworks get no throughput cut: their fuel-free PMs (electric trains, electric engines, non-plastic glass) sit in the same building, so a throughput cut there would charge them too and carry no substitution signal. Each band modifier holds only the keys above. No `goods_output_*`, no `*_tax_mult` and no `multiplier =` appear anywhere in the family.

How each column was set:

- **τ is linear in k** (a legislated rate: index × 2.5 per unit). It is the same per unit for coal and oil because both weigh 2 per unit in the emissions metric. Coal therefore pays more relative to its price, as a real per-tonne carbon tax does.
- **a is concave in k**: coal increments 6, 5, 4, 3 points, reflecting cheapest abatement first. a_oil ≈ 0.87 × a_coal, because abatement scales with √(τ/p) and τ/p is lower for oil.
- **No user gains from a band, levy included.** Every band satisfies a ≤ τ / (p + τ):

  | Bound | Band 1 | Band 2 | Band 3 | Band 4 |
  |---|---|---|---|---|
  | Coal: τ / (p + τ) | 7.7% | 14.3% | 20% | 25% |
  | Oil: τ / (p + τ) | 5.9% | 11.1% | 15.8% | 20% |

  So even a user with no compliance cost pays more in levy than it saves in fuel. Per unit of base fuel, the margin for coal is 0.55 / 1.15 / 1.88 / 2.80 and for oil 0.38 / 0.73 / 1.33 / 2.25.

  **This holds only at constant prices.** The fuel price fall in §3.4 (6–20% at band 3) hands users 5–17% of their residual fuel bill. That can outweigh the band-3 levy margin (≈ 6% of the fuel bill for coal, ≈ 3% for oil) for users with no throughput cut (rail, motor, glass), because the levy is per unit and does not fall with the price. Measurement 2 decides whether the τ step must rise.
- **b_power is sized to in-building neutrality** for fossil plants: b = a·F / (VA + a·F) with F / VA ≈ 1.5 from §2.3. Coal-fired plants come out at −1% to −4% of profit (a slight gain) and oil-fired at +0.5% to +2% (a slight cost). See Q1 for the alternative.
- **b_other ≈ 0.25–0.3 × the user's total fuel cut**, which is the owner's example ratio (10% output for 25% fuel), slightly lower.
- **m is small**: −2.5% per band. It stands for coal-to-gas switching and process controls, which the goods model cannot show because there is no gas good (Q3).

### 3.2 Effect per user [static, given the §2 assumptions]

Fuel cut = 1 − (1 − b)(1 − a); output change = −b. The two net-cost columns:

- **In-building net** = b × VA − (1 − b) × a × F. This is what the engine's investment and PM logic sees.
- **Attributed total** = in-building net + levy on the user's residual fuel. The levy is paid from the investment pool, not by the building.

| Band | User | Fuel use | Output | In-building net, % of profit | Levy / level / week | Attributed total, % of profit |
|---|---|---|---|---|---|---|
| 1 | Coal-fired power plant | −13.5% | −8% | −0.9% (gain) | 43 | +18% |
| 1 | Steel mill, electric arc | −7.9% | −2% | −4.3% (gain) | 92 | +3.9% |
| 2 | Coal-fired power plant | −22.6% | −13% | −3.0% (gain) | 77 | +31% |
| 2 | Steel mill, electric arc | −14.1% | −3.5% | −7.9% (gain) | 172 | +7.4% |
| 3 | Coal-fired power plant | −29.4% | −17% | −3.7% (gain) | 106 | +43% |
| 3 | Steel mill, electric arc | −18.8% | −4.5% | −10.9% (gain) | 244 | +10.8% |
| 4 | Coal-fired power plant | −34.4% | −20% | −3.7% (gain) | 131 | +55% |
| 4 | Steel mill, electric arc | −22.5% | −5.5% | −12.8% (gain) | 310 | +14.8% |

The other main users at band 3, the proposed default:

| User | Fuel use | Output | In-building net, % of profit | Attributed total, % of profit |
|---|---|---|---|---|
| Oil-fired power plant | −27.8% | −17% | +0.7% | +38% |
| Modern coal power plant | −29.4% | −17% | −2.9% (gain) | +30% |
| Steel mill, open hearth | −18.8% | −4.5% | −7.3% (gain) | +13% |
| Chemicals, catalytic cracking | −16.9% | −4.5% | −26% (gain) | +15.5% |
| Motor industry, diesel | −13% | 0 | −26.5% (gain) | +6.7% |
| Glassworks, plastics | −13% | 0 | −21.7% (gain) | +5.5% |
| Railway, diesel | −13% | 0 | −11.6% (gain) | +2.9% |

Reading the tables:

- **Output falls much less than fuel** everywhere except power. Steel loses 4.5% of output for an 18.8% fuel cut, a ratio of 0.24. Power's ratio is about 0.58, because neutrality costs a fuel-heavy user more output (Q1).
- **Every user net-loses once the levy is attributed, at constant prices.** The §3.4 price fall can turn the users without a throughput cut back into slight gainers (§3.1). Most lose slightly (3–15% of profit at band 3). Fossil power loses heavily (30–43%), which is where a real carbon price bites hardest [ext].
- **The in-building gain stays for every fuel-heavy user except power.** Chemicals, motor and glass gain 20–27% of profit before the levy. That is the free lunch research F finding 6 warns about: these buildings look *more* profitable to the investment logic, and their fossil PMs look cheaper next to electric ones. Only the pool levy offsets it, and only in aggregate. Power is the user where it matters most, because it is the one with a clean substitute *building*, which is why b_power is sized to neutrality. Elsewhere there is no clean building to steer towards, and a PM-level design (research F variant D) is the only full fix.

### 3.3 Market effect and transfer: a mid-size industrial country, c. 1960 [assume inventory; static per-level values]

| Users | Levels | PM | Coal / week | Oil / week |
|---|---|---|---|---|
| Power plants | 20 + 20 | coal-fired / oil-fired | 400 | 500 |
| Steel mills | 30 | electric arc + rotary valve | 1200 | – |
| Chemical plants | 10 | catalytic cracking | – | 1200 |
| Synthetic rubber | 5 | polyisoprene | – | 250 |
| Motor industry | 10 | diesel + assembly lines | – | 550 |
| Railways | 60 | diesel | – | 480 |
| Ports | 10 | modern | – | 150 |
| Highways | 10 | civil | – | 500 |
| Glassworks | 10 | plastics | – | 250 |
| Coal mines | 40 | diesel pump | – | 200 |
| Military upkeep | – | – | – | 150 |
| **Buildings** | | | **1600** | **4230** |
| Pops' heating (s_B = 0.85; split 35/65 coal/oil [assume]) | | | 360 | 669 |
| **Total** | | | **1960** | **4899** |

The fuel bill is 255k / week (13.2M / year). The fuel-using sectors above earn 928k / week in revenue, about 139k / week in profit at the 15% margin.

| Band | Building fuel use | Market consumption (× s_B) | Emissions cut incl. m_k | Levy / week | Levy / year | % of fuel bill | % of fuel-sector profit |
|---|---|---|---|---|---|---|---|
| 1 | −7.5% | −6.3% | **−8.7%** | 16.1k | 0.84M | 6.3% | 12% |
| 2 | −13.4% | −11.4% | **−15.8%** | 30.4k | 1.58M | 11.9% | 22% |
| 3 | −17.9% | −15.2% | **−21.6%** | 43.6k | 2.27M | 17.1% | 31% |
| 4 | −21.2% | −18.1% | **−26.3%** | 56.2k | 2.92M | 22.1% | 40% |

How these figures work:

- **Emissions cut** = 1 − (1 − market consumption cut) × (1 + m_k), measured against no carbon policy. Other input cuts already in force (§2.4) make each band's relative cut slightly larger.
- **The levy as a share of the pool is the open risk.** The pool receives only part of profits (roughly 20% of capitalist dividends at base, per `vanilla_economy_reference.md` §10.2). So a levy at 22–31% of the fuel sectors' *profit* may take a large share of the country's weekly pool *income*. That would slow private construction well beyond "slightly" (measurement 3, Q4).
- **Against GDP [assume].** If GDP is about 4× the fuel-using sectors' revenue (~190M / year), band 3 collects ≈ 1.2% of GDP. Real carbon taxes raise about 0.3–1% [ext].

### 3.4 Producers [inf]

- **The price fall.** At band 3, market coal and oil demand falls ≈ 15%, so the price falls ≈ 6% to 20% (§2.6 bracket).
- **Coal mines.** A diesel-pump coal mine (revenue 3450, profit ≈ 518) loses 200–680 a week, or 40% to more than 100% of its profit before its wages adjust.
- **Oil rigs** lose similar shares.
- **Where it settles.** Wage cuts and auto-downsizing (after 6 months, `AUTO_DOWNSIZE_BUILDING_MONTHS_TO_WAIT`) absorb part of the loss, and exports to other markets absorb part of the surplus.

This is the "coal and oil less profitable in general" downside the owner asked for. Its size depends on measurement 2.

---

## 4. Mapping

| Item | Proposal |
|---|---|
| **Rule off: default band** | **Band 3.** The Adopt button applies `te_carbon_band_3` to the market; Repeal returns to band 0. Today's policy claims −20% by decree, with the output cut adding ≈ 0. Band 3 gives ≈ −21.6% (−15.2% through consumption, −7.5% residual), the closest to today, so warming with the rule off keeps its pace. Band 2 (−15.8%) is the milder alternative (Q2) |
| **Rule off: the levy** | Runs in both modes (the carbon-tax correction applies with the rule off). It is collected monthly in country scope by the existing GW monthly sweep: base = Σ over the country's states of coal + oil `state_goods_consumption` (pops included) × τ × 52/12; transfer = min(levy, `investment_pool`), as `add_investment_pool = -x` then `add_treasury = x`, following the banking `ce_pool_withdraw_amount` overdraft pattern. It is shown in the Carbon Tax row tooltip |
| **Rule on: levy provision** | Provision `carbon`, index 0–4 = band. **Only the market leader legislates it.** Every member's code shows the leader's index as "Imposed by the market leader" and cannot amend it. Each member pays the levy on its *own* consumption into its *own* treasury, as a Budget line under the tax code. The sync swaps static band modifiers from the leader's enacted index (no `multiplier =`; the global pulse has no ROOT). The index is stored as a variable, so it survives a civil war |
| **AI will → band (rule on)** | Step up to band k when `gw_ai_will_carbon_tax` ≥ T_k, with T = 55 / 65 / 75 / 85. Step down from band k when will < T_k − 15. The hysteresis equals `gw_ai_repeal_band` (15), above the largest yes/no IG weight (12). One step per decision. Rule off: unchanged (adopt ≥ 55 selects the default band; repeal below 40) |
| **AI rationale row** | The `global_warming_ai_values.txt:54-55` text ("oil and coal extraction taxed double…") is false. Replace it with "fuel efficiency with a compliance cost, a levy on residual fuel paid from private capital: fuel users and exporters pay". Weights unchanged. `test_gw_ai_policy_table.py:169` pins the header table |
| **Treaty 109 minimum band** | Minimum = the default band (3). `on_entry_into_force` raises every member below 3 to band 3. `non_fulfillment` freezes the treaty when the source's band is below 3. The sync never lowers a treaty-bound member below 3. The AI evaluation lines (`:250`, `:316`) read the same "band ≥ 3" trigger (Q6) |
| **"Emissions Cut" pie** | Today it shows 1 − leader multiplier, so under the bands it would show only m_k (−7.5% at band 3) plus the other grantors. Proposed: 1 − M × (1 − ŝ × Ā), labelled "estimated". M is the leader multiplier as now. Ā is the leader's −`modifier:goods_input_coal_mult` and −`…oil_mult`, weighted by the market's coal and oil consumption and clamped to 0–1. ŝ = 0.85 until measurement 1. This also starts showing the principle, divestment and transit cuts, which already lower emissions today but never appear [inf: measurement 6]. The UN emitter test reads emission *shares*, so it needs no change |
| **Readers of `has_modifier = carbon_tax_modifier`** | Converted to `gw_policy_carbon_tax_active = yes` (any band ≥ 1) or a band-index trigger: `extra_on_actions.txt:1092` (fossil-lobby roll); `environmentalism_events.txt:872`; `new_ideological_movements.txt:252`; `global_warming_buttons.txt:39,69`; `global_warming_triggers.txt:33,129,144`; `global_warming_effects.txt:23-39`; `extra_effects.txt:1253-1264` (sync); `109_enforce_emissions_reduction.txt:114-116,184,250,316`; `te_debug_gw_effects.txt:130`. The counters and display values already use the trigger |
| **Save migration** | A save from before this change holds `carbon_tax_modifier` on members' journal entries. The first monthly reconcile replaces it with the default band on every holder (remove the old modifier, add band 3), and the band sync takes over from there. `legacy_modifier_cleanup.txt:181` stays as the final removal |
| **Other touch points (phase 2)** | Loc: `carbon_tax_modifier` desc, `GW_CARBON_TAX_DESC`, and `gw_how_policies_1` plus `concept_climate_policy_desc`, which say only the three market-wide policies cut emissions (no longer true). Guide `14-climate.md:160, 169-171, 209`. `test_global_warming_layout.py:27,179`. The modifier-type registrations in §5 |

---

## 5. Dead keys

`bg_coal_mining` is a vanilla legacy group with no buildings (`~/src/vic3/game/common/building_groups/00_building_groups.txt:754-757`). Coal mines are `bg_mining`, which also holds the iron, gold, lead and sulfur mines. The only live coal-specific key is `building_coal_mine_throughput_add` (vanilla-registered).

| Site | Dead key | Action | Why |
|---|---|---|---|
| `carbon_tax_modifier` (`extra_modifiers.txt:1317`) | `building_group_bg_coal_mining_tax_mult = 1` | Remove; whole modifier retired into `te_carbon_band_<k>` | The levy replaces every fiscal part. The live `bg_oil_extraction_tax_mult = 1` and `bg_manufacturing_tax_mult = 0.1` and both `goods_output_*` −10% are retired with it, not carried over |
| `fossil_fuel_divestment_modifier` (`:1367`) | `building_group_bg_coal_mining_tax_mult = 0.25` | Remove; **no replacement** | No per-type tax key exists, and `bg_mining` would tax every other miner. This leaves the live oil-rig +25% alone (Q5) |
| Treaty 109 `source_modifier` (`109_enforce_emissions_reduction.txt:54`) | `building_group_bg_coal_mining_throughput_add = -0.10` | → `building_coal_mine_throughput_add = -0.10` | Same intent (cut the bound leader's coal extraction), matching the oil line beside it |
| `fossil_lobby_concessions_modifier` / `_no_gw_` (`:1540`, `:1549`) | `building_group_bg_coal_mining_throughput_add = 0.10` | → `building_coal_mine_throughput_add = 0.10` | Same intent (boost coal extraction), pairs with the oil-extraction +10% |
| `climate_accord_rejection_modifier` / `_no_gw_` (`:1667`, `:1675`) | `building_group_bg_coal_mining_throughput_add = 0.05` | → `building_coal_mine_throughput_add = 0.05` | As above, at +5% |
| `global_warming_modifier_types.txt:75`, `:84` | Type registrations for both dead keys | Remove | Nothing reads them after the above |

Graphite mines also output coal, because they run the coal-mine PM groups. They are a nuclear-era discoverable themed on the graphite moderator, so they stay out of the coal-extraction keys.

---

## 6. Open questions for the owner

1. **Power-plant compliance cost.**
   - **Neutral b_power (−8 / −13 / −17 / −20%).** No in-building gain for fossil plants, so fossil plants look no more attractive to investment than renewables. Fossil-power output falls 17% at band 3 for a 29% fuel cut.
   - **The owner's ratio (b_power −3 / −5 / −6.5 / −7.5%).** Output falls only 6.5% at band 3, but coal plants gain 26% of profit in-building and look more attractive than renewables to the investment logic.

   *Recommended: neutral.* Power is the one user with a clean substitute building, and a dearer fossil kilowatt is how real carbon prices move generation.
2. **Rule-off default band.** *Recommended: band 3*: ≈ −22% against today's −20%, so warming keeps its pace. Band 2 gives ≈ −16% at about half the cost.
3. **Residual emissions multiplier, −2.5% per band.** *Recommended: keep it*, for coal-to-gas switching the goods model cannot show. With none, band 3 gives ≈ −15%, and the default becomes band 4 to stay near −20%.
4. **Levy base and guard.**
   - *Base: recommended* own coal + oil consumption, pops' heating included (it emits too), charged per unit at τ rather than at market price. That makes it a specific tax, steady under price swings.
   - *Guard: recommended* min(levy, pool), plus a provisional cap of 25% of weekly pool gross income until measurement 3 says the uncapped levy is affordable. Without a cap, the levy may starve private construction.
5. **Divestment's surviving oil-rig wage tax (+25%).** With the coal key gone, divestment taxes oil workers only. *Recommended: remove it too.* A payroll tax on rig workers is not divestment, and under the tax code it duplicates the wage schedule. That leaves divestment as the −5% input cut plus its authority cost, and the AI row (fossil −25) is reworded. Keeping it is the alternative.
6. **Treaty 109 minimum band.** *Recommended: the default band (3)*, so "bound to a carbon tax" means the standard one. A lower minimum (band 1) would let a bound leader satisfy the treaty with a token levy.
