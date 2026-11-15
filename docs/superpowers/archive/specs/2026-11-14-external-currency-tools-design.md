# External & Currency tools: one promise each, on every currency — design

Date: 2026-11-14. Owner's request, after asking whether Restrict Speculative
Inflows, Sterilize Capital Inflows, Foreign Exchange Surrender and Capital
Controls work on fiat or digital currency: make the five exchange tools (those
four and Limit Foreign-Currency Borrowing) clearer to players, abstracting their
effects where that helps but staying faithful to each policy. Two PRs: the first
changes only what the player reads, the second the mechanics.

**Built** in jakeOmega/Vic3TimelineExtended#1800 (PR 1) and
jakeOmega/Vic3TimelineExtended#1807 (PR 2), as written here. Two things the build added: the panel's
text is in its neutral voice ("On this currency", "the country's"), since the
banking panel can show another country; and the label is "On this currency"
throughout. How it works now: `docs/systems/mod_systems/banking_cycle.md`
§ External & Currency tools.

## Why

The five tools sit in one menu but act on two different models of the external
economy (`docs/systems/mod_systems/monetary_policy.md`, phases 3–5):

- **Convertible gold with a national bank** (`te_mon_has_gold_flows`): the rate
  gap moves gold in and out of the bank's vault (`te_gold_flow`), arriving gold
  raises prices (`te_mon_pressure_gold_flow`), Borrowed Gold can leave, and Peg
  Confidence drains when gold runs out or the parity is overvalued. The Exchange
  Rate Index stays at par unless the country devalues.
- **A floating currency with a national bank** (`te_mon_has_dial` and
  `te_mon_fx_floats`: fiat, digital, a suspended gold standard): the index
  drifts toward a target built from the real-rate gap, the inflation gap, the
  risk premium and event shocks (`te_mon_fx_target_value`). Below par it adds
  risk premium (`te_mon_premium_fx`); a fall below its three-year average raises
  prices.

What the tools did on each, as of `main` at 8433e18:

| Tool | Gold flows | Floating | Anchored, commodity money, no bank |
|---|---|---|---|
| Capital Controls (Outflows) | rate gap ×¼ both ways (gold flow, the drain on Peg Confidence) | rate term of the target ×¼ both ways | treaty peg: overvaluation drain ×¼; otherwise nothing |
| Restrict Speculative Inflows | gold inflow ×½ | positive rate term ×½ | commodity money: available, does nothing |
| Sterilize Capital Inflows | price pressure from gold coming in ×¼ | not available | not available |
| Foreign Exchange Surrender | buys gold for the vault | not available | not available |
| Limit Foreign-Currency Borrowing | available, does nothing at par | weak-currency premium ×½ over 24 months | anchored: as floating |

So two tools were gold-only, one was available and inert on gold, one was
available and inert on commodity money, and the text (button descriptions, the
display-only modifiers' names and descriptions) mostly spoke gold:
"Pull of the Rate Gap" names the gold flow and Peg Confidence to a floating
currency that has neither, "Pull of Money Coming In" says it "draws gold in", and
Restrict Speculative Inflows promises "a vault that fills more slowly". The
"(Outflows)" in Capital Controls' name is wrong too: the controls act both ways
on purpose (`te_mon_gold_gap_value`'s comment: "controls that stop capital
leaving also stop it arriving, so they are no way to bank a high rate's
inflow").

Historically all five are at least as much tools of paper money as of gold:
surrender requirements under Bretton Woods and in Russia in 2022, Chile's tax on
short-term inflows in the 1990s, China's sterilized intervention in the 2000s,
capital controls in Malaysia (1998), Iceland (2008) and Cyprus (2013).

## Owner's calls (2026-11-14)

1. Sterilize Capital Inflows becomes **Sterilization**, since on a floating
   currency it acts on money leaving too.
2. Limit Foreign-Currency Borrowing is **hidden on metal at par**, where there is
   no weak-currency premium for it to protect against.
3. Both PRs.

## The five promises

Each tool keeps one sentence a player can plan around, true on every currency
it is available on. The mechanism differs by currency; the tooltip says which
applies to the player's own.

| Tool | Promise | Gold flows | Floating |
|---|---|---|---|
| Capital Controls | Your interest rate moves a quarter as much money across the border, either way | rate gap ×¼; Peg Confidence lost to overvaluation ×¼ | rate term ×¼ |
| Restrict Speculative Inflows | Money drawn in by a rate above the world's arrives at half speed; money leaving is not slowed | gold inflow ×½ | positive rate term ×½ |
| Sterilization | Money crossing the border does not jolt prices at home | price pressure from gold coming in ×¼ | **(PR 2)** the index moves toward its target at half speed, either way |
| Foreign Exchange Surrender Requirement | Exporters sell what they earn abroad to the central bank | buys gold for the vault with treasury cash | **(PR 2)** up to +4 on the exchange-rate target, by export reliance |
| Limit Foreign-Currency Borrowing | A weak currency costs you less risk premium | **(PR 2)** hidden at par | weak-currency premium ×½ over 24 months |

## PR 1: what the player reads

No change to any script value, trigger or effect a pulse runs.

- **Names.** Capital Controls (Outflows) → **Capital Controls** (the button, its
  End button, the modifier). Sterilize Capital Inflows → **Sterilization** (the
  button, End Sterilization, the modifier, the display modifier). The event
  modifier also called "Capital Controls" (`banking_crisis_capital_controls_modifier`,
  `minor_events_timelineextended.7`) becomes "Targeted Capital Controls", the
  option's own word, so the two can be told apart in a modifier list.
- **Descriptions** (`CB_*_DESC`, which the buttons and the modifiers share): the
  promise first, in words true on every currency, then the cost. What differs by
  currency moves out of them.
- **"On this currency:"**, a new line in each tool's dashboard tooltip
  (`banking_dash_tt_cb_*`), right under the description. A custom localization
  per tool (`banking_ext_now_<tool>`, `common/customizable_localization/banking_dash_custom_loc.txt`)
  picks the branch for the player's currency and gives the figure the tool
  changes, now and with the tool, from display-only script values
  (`banking_ext_disp_*`, `banking_external_values.txt`):
  - Capital Controls: on gold, the rate gap and the gap it moves gold as under
    controls; floating, the rate term of the target with and without controls;
    a treaty peg, that the rate moves nothing and controls quarter the
    overvaluation drain; anything else, that nothing of the country's moves money
    across the border, so controls do only what their modifier lines say.
  - Restrict Speculative Inflows: on gold, the gap and the halving of what it
    draws in; floating, the rate term with and without the restriction (a rise
    halved, a fall untouched); commodity money, that there is nothing to restrict.
  - Sterilization: on gold, the price pressure gold coming in adds, and with
    sterilization; with no gold coming in, that it has nothing to absorb now; off
    gold, that it needs the gold standard (PR 2 replaces this with the floating
    line).
  - Foreign Exchange Surrender: on gold, the vault's fill and this month's
    purchase (the line that was "Current monthly reserve purchase"); off gold,
    that it needs the gold standard (PR 2: floating line).
  - Limit Foreign-Currency Borrowing: below par, the premium the weak currency
    adds and what is left of it after the protection built so far; at or above
    par, that there is no such premium now; on metal at par, that there is none
    unless the country devalues.
- **Display-only modifiers** (GUI audit BNK-6): "Pull of the Rate Gap" and "Pull
  of Money Coming In" get descriptions that say what moves on each currency.
  "Price Pressure from Gold Coming In" and "Gold Bought for the Bank" stay, being
  gold-only.
- **Player guide** (`04-banking.md` and the appendix): the table by promise,
  the renames, and a sentence per tool on what it does off gold.

## PR 2: the mechanics

- **Sterilization on a floating currency.** While sterilization is active,
  eligible and funded on a floating currency, the index closes a 24th of the
  distance to its target a month instead of a 12th
  (`te_mon_fx_shadow_step × banking_external_fx_adjust_factor`, 0.5). It is
  sterilized intervention: the central bank buys or sells foreign money against
  the move and sells bills to absorb what it paid, so a sudden fall reaches
  prices (through the three-year average) more slowly and a sudden rise reaches
  exporters more slowly. Same bill as on gold, 0.01% of annual GDP a month.
  Event shocks decay at their own speed, so a shock moves a sterilized currency
  less than half as far. Restrict Speculative Inflows only halves the rise from
  a high rate; sterilization slows every move, inflation's and the premium's
  included, which is what tells the two apart.
- **Foreign Exchange Surrender on a floating currency.** Adds a term to the
  target, `te_mon_fx_term_surrender` = 4 × the export share (0, ¼, ½ or 1 by
  `market_exports_reliance` bands: 0, up to 10%, up to 30%, above), so up to +4.
  Exporters who must sell their foreign earnings for the home currency hold up
  its price; 4 points is what a real rate one point above the world's buys. No
  treasury cash changes hands: the central bank pays in its own money. The −10%
  export advantage and −3% bureaucracy stand, and the stronger currency costs a
  further 1.25% export advantage a point, so it is a tool for a currency that is
  falling, not a free one. The reserve purchase and the Breakdown's surrender
  line stay gold-only.
- **One requirement for the three flow tools.** Restrict Speculative Inflows,
  Sterilization and the surrender requirement need
  `banking_external_rate_moves_money`: a national bank setting its own rate, on
  convertible gold or a floating currency. Commodity money, which met Restrict
  Inflows' old requirement and gained nothing from it, no longer does. The
  surrender requirement's cash and vault-room tests apply on gold only.
- **Limit Foreign-Currency Borrowing hidden at par on metal**
  (`te_mon_fx_pinned_at_par`: metal, not anchored, not devalued): not drawn, the
  AI's button not visible, and an active one lifted by the monthly cleanup, as
  any tool whose requirement lapses is. The protection stock unwinds over 24
  months as on any repeal. A devalued metal currency can use it until the index
  is back at par.
- **AI.** Sterilization on a float when the target is at least 8 points from
  the index; surrender on a float when the index is below 95 (the borrowing
  limits' test). Gold keeps its tests.
- **Simulator.** `scripts/analysis/banking_cycle_sim.py` holds the index at par,
  so the floating versions have nothing to act on there and stay out of its AI
  selection, like the borrowing limits; its Restrict Inflows gate follows the
  new requirement. The script scenarios in `test_banking_external_tools.py` test
  the floating versions instead.
- **Exchange-rate tooltip** (`banking_dash_mon_fx_tt`): a line for the surrender
  term while it adds one, and a line saying the index closes a twenty-fourth of
  the distance while sterilization slows it (`te_mon_fx_surrender_note`,
  `te_mon_fx_sterilized_note`).

## Out of scope

- A stock of foreign-exchange reserves for a floating currency. It would let
  surrender and sterilization build and spend a buffer, as the vault does on
  gold, but it is a new system with its own crisis; the two tools above give each
  policy its effect without one.
- Retuning the gold versions or Capital Controls' fatigue.
- Translations: renamed keys ship English in German and Spanish until the next
  translation pass.
