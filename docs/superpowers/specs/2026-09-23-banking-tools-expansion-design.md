# Banking cycle tools expansion — design and decisions

## Context

The banking-cycle dashboard (`gui/journal_entry_widgets/banking_dashboard_widget.gui`) groups the
market-economy intervention tools into five categories, and two of them were thin: **Directed Credit**
showed only *Infrastructure* until `corporate_management` unlocked *Export Credit*, and **Monetary
Policy** mixed the policy-rate dial block with two toggles that belonged elsewhere. The owner asked
for (2026-09-23):

1. Open-Market Operations moved beside the rate stepper, visible only under laws that allow it.
2. Moral Suasion moved to Prudential Regulation, leaving Monetary Policy as the dial block alone.
3. New tools in Directed Credit, Prudential Regulation and Crisis Response.

(1) and (2) shipped first, as a GUI-only change (PR "OMO under the rate target, moral suasion in
Prudential"); `docs/systems/mod_systems.md` § Policy Dashboard → *Where the tools sit* records the
result. This document is the design for (3).

## Decisions (owner, 2026-09-23)

| Question | Decision |
|---|---|
| OMO under `banking_system_simplified` (no dial block) | a fallback row under the Monetary header |
| What *hides* the OMO row | the currency regime only (`country_can_create_unbacked_money_bool`); the tech, the Prudential / Narrow lock, the floor and points grey it with a reason |
| OMO placement | a full policy row directly under Rate Target |
| New Directed Credit sectors | Heavy Industry, Agriculture / land banks, Armaments, Electrification & High Tech |
| How sectors combine | **one priority sector at a time**; Directed Credit & Development Banks allows **two**, through a declarative modifier its tooltip shows |
| New Prudential tool | Reserve Requirements |
| New Crisis tools | Bank Holiday, Bail-in Regime |
| Out of scope | command-economy and cooperative panels; External & Currency (phases 4–5 replaced FX buttons with outcomes and treaty articles on purpose) |

**Amended during planning.** The approved stacking option also gave State-Owned Banking the second
sector. It was dropped: `law_state_owned_banking` has `unlocking_laws = { law_command_economy }`, and a
command economy fails `banking_is_market_economy`, so every `cb_*` tool is hidden there and stripped on
the way in (`remove_banking_market_modifiers_effect`). The grant would have been dead text on the law.

## Constraints the design works inside

- **The AI's only path to a tool is the `scripted_button`'s `ai_chance`**, one weighted roll a month
  over every `possible` enable button (`docs/systems/mod_systems.md` § Policy Dashboard). A new button
  is new AI behaviour whether or not a player ever clicks it.
- **Directed credit is the AI's riskiest tool.** `docs/audits/banking_cycle_simulation.md` F11: held
  through a recovery, Infrastructure was 30–45 % of a tooled AI's crashes, fixed by lifting it on
  recovery. Four more sectors must not multiply how often the AI reaches for directed credit.
- **Sixteen registration points per tool, nothing checking them** — button pair, JE line, helpers,
  handlers, the active-policy OR list, the law-change removal list, the history-marker tooltip, two
  GUI rows, loc, and the simulator. `test_banking_tool_roster.py` checks them from now on.
- **Numbers are sized with `scripts/analysis/banking_cycle_sim.py`**, against the targets in the
  study's §2 and §8. The per-tool lines move, never the shared constants the 2026-09-22 retune set.

## B1 — Directed Credit sectors and the priority-sector cap

Four new sectors, each the shape of `cb_directed_credit_infrastructure`: +10 % construction efficiency
for its building groups, an interest-group signature that says who gains and who pays, a little
momentum and bubble pressure, 3 points and `banking_directed_credit_activation_cost` on enabling.

| Tool | Building groups | Interest groups | Gate |
|---|---|---|---|
| `cb_directed_credit_heavy_industry` | `bg_heavy_industry` | Industrialists +3, Landowners −3 (credit pulled off the land) | — |
| `cb_directed_credit_agriculture` | `bg_agriculture`, `bg_plantations`, `bg_ranching` | Landowners +3, Rural Folk +2, Industrialists −3 | — |
| `cb_directed_credit_armaments` | `bg_military_industry`, `bg_ship_construction` | Armed Forces +3, Intelligentsia −2 | — |
| `cb_directed_credit_electrification` | `bg_power`, `bg_high_tech` (both mod-registered) | Intelligentsia +2, Trade Unions +1, Industrialists −3 (private utilities fought the REA and the TVA) | `rural_electrification` (era 6) |

All five sectors share Infrastructure's `country_banking_lock_directed_credit_bool`, so Prudential /
Narrow Banking locks the whole category. `bg_high_tech` is a child of `bg_heavy_industry`
(`common/building_groups/extra_building_groups.txt`), so Heavy Industry already covers high-tech
buildings; Electrification's own addition is `bg_power`. The overlap matters only when both run at
once under the Directed Credit law, where high tech gets +20 %.

**The cap.** `country_directed_credit_sectors_add` (new, `banking_cycle_modifier_types.txt`) is granted
`+1` by `law_directed_credit_development_banks`. `banking_directed_credit_slots_free` = 1 + that
modifier − the number of sectors running; every sector's `possible` (Infrastructure's included)
requires it to be above zero and says so (`banking_dc_sector_cap_tt`). A law change can leave two
sectors running under a cap of one; `banking_directed_credit_enforce_cap`, a step in the journal
entry's monthly pulse, lifts sectors in reverse roster order until the count fits. Monthly rather than
on `on_law_enactment_pass`, so it needs no same-tick modifier read and also catches law swaps that do
not go through that hook.

**The AI — one weight, shared.** Every directed-credit enable button scores the **same** weight,
`banking_dc_ai_weight` (Infrastructure's `ai_chance` as it stood: downturn 40, stagnation 30, stable
and falling 15, gated flavour, frenzy −35, panic −30), and the weight is **split** among the sectors
that fit the government:

- A new sector is a *candidate* when it has an **affinity** and could be clicked (`possible`, not
  running): Heavy Industry — Industrialists in government; Agriculture — Landowners or Rural Folk in
  government; Armaments — at war, or Armed Forces in government; Electrification — Intelligentsia in
  government.
- With `n > 0` candidates, each candidate scores `weight / n` and Infrastructure scores 0. With none,
  Infrastructure scores the whole weight, as before.

So the AI reaches for directed credit exactly as often as it did before this change, whichever
interest groups hold power, and picks the sector its government favours. The one deliberate increase
is the Directed Credit law's second slot. Disable buttons copy Infrastructure's F11 weights verbatim
(panic 45, stable-unless-falling 20, expansion 30, boom 35, frenzy 55).

*(Planning sketched per-sector bonuses with an Infrastructure penalty; that still roughly doubled the
directed-credit weight wherever one sector had an affinity. The split is exact.)*

## B2 — Reserve Requirements (Prudential)

A leaning tool for every era: no tech, no lock, 2 points. Bubble and momentum down, a small cost to
capitalists' investment-pool efficiency, and `country_inflation_pressure_add` −0.5 pp — tighter
reserves shrink the money the banks create, and the line shows in the dashboard's Price Pressure
breakdown (inert under the simplified rule). Small radicals on enabling and lifting, like the buffer
and margin requirements. Weaker than the buffer, which needs `international_exchange_standards`; it is
what an early economy leans on a boom with besides margin requirements and moral suasion. AI: the
buffer's weights, plus a gated +15 while the buffer is still locked — and ×0 while the buffer could be
bought instead. *(Amended after simulation: with the buffer's weights alone the AI split its leaning
between the two, and fiat / digital at 3 points crashed up to 1.3 times a century more —
`banking_cycle_simulation.md` §11.)*

## B3 — Bank Holiday (Crisis)

The 1933 holiday and the nineteenth century's suspensions of payment: shut the banks, stop the run.

- Usable only in **panic or downturn**, 2 points, no tech — the one crisis tool a country without a
  lender of last resort has.
- Enabling adds `banking_bank_holiday` to the journal entry **for 90 days** (a timed modifier; ending
  it early is the Disable action), halves a negative momentum once, and starts a **five-year
  cooldown**.
- While it runs: crash chance −90 % (`country_banking_crash_chance_mult`, which both the origin and the
  contagion checks multiply by — so it shields against imported crashes too), services output −20 %,
  tax collection −5 %. Small middle-strata radicals: depositors cannot reach their money.
- AI: ELIQ's core (panic; downturn at momentum ≤ −4), +20 while ELIQ is still locked; lifted early only
  once the cycle is back at stable.

## B4 — Bail-in Regime (Crisis)

The post-2008 answer to the bailout: creditors, not the treasury, recapitalise the banks.

- `globalization` (era 9), 3 points, **no treasury cost**. No law lock: Unregulated Banking's budget
  (1, or 2 with a national bank) cannot afford it anyway.
- **Mutually exclusive with Asset Relief** — a government bails out or bails in.
- Standing: `country_finance_value_monthly_add` about half Asset Relief's, bubble pressure down (the
  moral hazard goes), `country_risk_premium_add` +0.1 pp (bail-in-able debt costs more). Enabling
  radicalises the upper strata.
- AI: Asset Relief's core, +20 when `scaled_debt ≥ 0.5` (a country that cannot afford a bailout);
  disable side copies Asset Relief's.

## Numbers (starting point; `banking_cycle_sim.py` sizes them)

| Tool | Points | Momentum / month | Bubble / month | Other |
|---|---|---|---|---|
| Infrastructure (unchanged) | 3 | +0.05 | +0.3 | infrastructure construction +10 %, decree cost −10 %, IG as shipped |
| Heavy Industry | 3 | +0.05 | +0.3 | heavy-industry construction +10 % |
| Agriculture | 3 | +0.04 | +0.4 | agriculture / plantation / ranching construction +10 % |
| Armaments | 3 | +0.05 | +0.2 | military-industry / shipyard construction +10 % |
| Electrification & High Tech | 3 | +0.05 | +0.3 | power / high-tech construction +10 % |
| Reserve Requirements | 2 | −0.04 | −0.9 | capitalists' pool efficiency −5 %, inflation pressure −0.5 pp |
| Bank Holiday (90 days) | 2 | one-shot: halve a negative momentum | 0 | crash chance −90 %, services −20 %, tax −5 % |
| Bail-in Regime | 3 | — | −0.3 | finance value +0.15 / month, risk premium +0.1 pp |

## Acceptance (simulator)

Crash bands of §2 / §8 hold; the budget curve stays flat (the 2-point cell within 0.9–1.1× its
neighbours); no new tool raises crashes in a leave-one-out; directed-credit clicks per century stay
near today's with no affinity and with one; boom rescue with reserve requirements added to the
leaning tools is re-baselined and recorded (it should rise; trim the tool if booms become trivial).
