# The banking entry for every country, its cycle dormant until it starts — design

## Context

The owner, reviewing the Nation tab spec (PR #1018, 2026-10-17): the banking entry "is almost always running; if
anything, we should make it always running but disable most interactions until it activates". The Nation tab gives
Credit Standing no row because the Banking tab owns it, and that only holds if every country can open the tab.

**What starts `je_banking_cycle` today.** Its `possible` is `always = yes`, so the engine activates it as soon as its
`is_shown_when_inactive` holds (both must be true, `scripting_best_practices.md` § "JE Auto-Activation Requires BOTH").
That trigger is:

- `te_banking_system_on`: the Banking System rule is Enabled or Simplified, not Disabled;
- `te_banking_entry_unlocked` (`banking_policy_triggers.txt`): **Stock Exchange** researched (an era 1 society
  technology) **and** a state with an **Urban Center of level 5** or more.

No event, decision or `add_journal_entry` adds it. Once active it never ends (no `invalid`, no `can_deactivate`), and
a revolution's winner inherits it. `immediate` seeds the cycle at 50 / 0 / 0.

**Who goes without it.** Countries that haven't researched Stock Exchange (mostly unrecognised ones), countries with
no Urban Center of level 5 (small ones, and most countries in the first decades), every country under the Disabled
rule, and the rebels of a running revolution until they win. For them:

- the Budget panel's Banking tab is greyed, except for a country with a central-bank dial or an anchored currency,
  which gets the read-only monetary readout (#805, `te_budget_banking_readout_sgui`);
- nothing shows Credit Standing, the risk premium or Rate You Pay, though the monetary layer prices every country's
  debt from 1836 (`te_monetary_monthly_update` runs off the country's own pulse, not the entry's);
- a player with a National Bank can't touch the dial: the bank runs the Dual Mandate (`te_monetary_effects.txt`, the
  `NOT = { has_journal_entry = je_banking_cycle }` branches; `te_mon_mandate_runs_bank`).

## Decisions (owner, 2026-10-17)

| Question | Decision |
|---|---|
| What "activates" means | **The cycle starts.** The condition is today's unlock test, unchanged: Stock Exchange and an Urban Center of level 5 (§ 1) |
| Does the cycle move before it starts? | **No.** A dormant entry holds no cycle readings: no phase, crashes, events or contagion, as today. The alternative, a cycle that runs from 1836 with the tools locked, is § 9 |
| What works before the start | **Nothing: the Monetary Policy section is read-only.** Its readings show (Rate You Pay, Credit Standing, the dial's rate), its controls are greyed, and a bank keeps running the Dual Mandate as it does today. Every interaction waits for the cycle (§ 3) |
| Rebels | **No entry while revolutionary.** The winner inherits the loser's entry, the path #465 fixed (§ 5). Decentralized nations get none either, as with the mod's other every-country entries |

## 1. What "activates" means

The entry is active for every country from the first days of the game. What starts later is the **financial cycle**:
its three readings, its phase modifiers, crashes, events, contagion and the tools.

- **The start condition** is `te_banking_cycle_unlocked`, today's `te_banking_entry_unlocked` renamed: Stock Exchange
  and an Urban Center of level 5. Both are physical prerequisites (the technology and the building where the financial
  sector lives), which the design defaults let stay hard gates. Keeping the test unchanged keeps the balance the
  simulator tuned against (`banking_cycle_simulation.md`): the same countries run a cycle from the same moment.
- **The latch** is `finance_cycle_value`. A new trigger, `te_banking_cycle_running` (`has_journal_entry` plus
  `has_variable = finance_cycle_value`), names it. Every writer of the three variables already goes through the entry
  or the `banking_change_*` helpers, which gate on the entry (the helpers' header), so the variable exists exactly when
  a cycle has started. Once started, a cycle keeps running if the Urban Center is later lost, as the entry does today.
- **Starting.** `banking_cycle_start` seeds 50 / 0 / 0 (each guarded, as `immediate` does now) and draws the bars. It
  runs from `immediate` (a new game's founding countries, a released country, a revolution's winner) and from the
  dormant branch of the monthly pulse. A start from the pulse posts a feed notice to a human player,
  `banking_cycle_started_notice`: the moment the old activation announced.

## 2. The entry from game start

```
is_shown_when_inactive = {
	te_banking_entry_expected = yes   # the rule on, not decentralized, not revolutionary
}
possible = { always = yes }
```

- **`immediate`** keeps its unguarded stance-tracker reset and the bank-holiday marker cleanup, then calls
  `banking_cycle_start` only when `finance_cycle_value` is absent and `te_banking_cycle_unlocked` holds, and draws the
  bars only once the cycle is running.
- **The monthly pulse** runs today's body only while `te_banking_cycle_running` holds. Otherwise it tests the start
  condition: Stock Exchange first, so most dormant countries never reach the building scan. **The weekly pulse**
  (the investment pool's weekly share) is gated the same way.
- **The status text** goes. The dormant entry draws an overview (§ 4), so `banking_cycle_status_not_started` would
  repeat it (style guide rule 1).
- `should_be_pinned_by_default_uninvolved_or_context` stays `yes`, so the entry is pinned from 1836, as it is today
  for most players from the first decades.

## 3. What waits for the cycle

| | Before the start | Where it is gated |
|---|---|---|
| The 40 tools (22 market, 10 command, 8 cooperative) | Greyed in the dashboard, invisible to the AI | First line of each `banking_possible_*` helper: `te_banking_cycle_started_tt` (a `custom_tooltip` on `te_banking_cycle_running`); each enable button's `visible` also asks `te_banking_cycle_running`, so the AI never scores a dormant entry's tool (its `ai_chance` reads unguarded `var:finance_cycle_value`) |
| Phase and bubble-inertia modifiers, stance band, fiscal-policy effect, command-economy pool balance | None | the pulse's running branch |
| Banking events, crashes, contagion received, the Great Depression event, crisis waves | None | the pulse; `banking_cycle_spread_contagion` and `banking_crisis_wave_check_great_depression` ask `te_banking_cycle_running` |
| Event options and law runs that move the cycle | Skipped, tooltip line hidden | `banking_change_*`, `banking_enactment_run_shock`, `un_events.35`, `banking_cycle_post_event_refresh` |
| Restructure the Public Debt, bailouts, the UN emergency loan, the UN grant into the pool | Not offered | `banking_restructuring_shown`, `banking_is_bailout_recipient` / `banking_can_offer_bailout`, `un_docket_loan_candidate`, `un_dev_fund_pays_into_pool` |
| History charts | Not sampled, section hidden | `te_history_record_banking_samples` / `_marker` |
| The phase icon in the top bar | Hidden | `te_banking_topbar_gate` |
| Monetary Policy's controls: the dial, delegation, mandate, monetisation, recapitalisation | Greyed; the bank runs the Dual Mandate (or its act's mandate under Central Bank Independence), as without the entry today | `banking_mon_control_sgui`'s `is_valid` opens with `te_banking_cycle_started_tt`; the mandate branches in `te_monetary_update_target` and `te_mon_mandate_runs_bank` ask `te_banking_controls_open` |
| **Monetary Policy's readings: Rate You Pay, Credit Standing, Risk Premium, prices, exchange rate, gold and peg** | **Shown** (Enabled rule) | unchanged |

`te_banking_controls_open` is its own trigger, today the same test as `te_banking_cycle_running`, so opening the
monetary controls before the cycle later is a one-line change. `te_mandate.1` (an act for an independent bank) asks
any country, entry or not, as it does now.

## 4. Panels

The GUI's cycle gates are `JournalEntry.IsActive` today: the overview, the status sections, the reference sections, the
history panel and the top bar. Each moves to a scripted GUI on `te_banking_cycle_running`
(`banking_dash_cycle_running`), and a twin (`banking_dash_cycle_dormant`) draws the dormant state:

- **Overview** (always shown, rule 1): the bars and the cycle's cells (phase, momentum, bubble, budget) only once the
  cycle runs. Before that, one cell in the overview's shape (rule 4): caption *Cycle Phase*, word *Not Started*, the
  Stable icon dimmed, third line *1 of 2 met* (`banking_disp_unlock_met`), the checklist with ticks on hover
  (`te_budget_banking_tab_unlock_sgui`'s `IsValidTooltip`, asked `IsValid` first for the month between meeting the
  test and the pulse that starts the cycle). The monetary row (Policy Stance, prices) shows as it does now.
- **Active Policies**: hidden while dormant (rule 7: content for one state only).
- **Monetary Policy**: every reading as now; each control greyed, its tooltip's first line crossed (rule 6). The
  reason is said once, at the top of the section, for a country with a control there
  (`banking_dash_monetary_dormant_note`: a dial, or under Simplified the Open-Market Operations row).
- **Available Interventions**: every row as now, its Enable greyed, the tooltip's first line crossed (rule 6). The
  reason is said once, under the heading: *The financial cycle has not started* (rule 6: "said once, above the
  rows"), with the checklist on hover.
- **History**: hidden while dormant. **How Banking Works**: shown, with a line on when the cycle starts.
- **The Banking tab** opens whenever the entry is held (`te_budget_banking_tab_sgui` unchanged). Its greyed state and
  the #805 readout remain for a country without the entry: the first fortnight of a game, and the rebels of a running
  revolution, whom a player can switch to. The greyed tab's tooltip no longer lists the start test, which is not what
  opens it: it says the tab opens with the entry.
- **Style guide rule 9.** Banking stops being the exception: the tab is greyed only until the entry is active, and
  every country holds it. The rule gains a line for an entry whose system starts later: the entry and the tab open
  first, and the system's controls carry the start condition.

## 5. Old saves, new countries, revolutions

- **New game.** Every country's entry auto-activates within the engine's first two-week check; founding countries
  that meet the test start their cycle in `immediate`, the rest on the monthly pulse that first finds them unlocked.
- **Old saves.** A country already holding the entry is unchanged: its cycle runs. A country without it has the
  inactive record a type gets from game start, and the wider `is_shown_when_inactive` activates it (dormant: it
  didn't meet the test, or it would hold the entry already).
- **Safety net.** Whether an inactive record exists in every old save, and for every released country, is unread.
  `te_banking_entry_net` (`on_yearly_pulse_country`) adds the entry (`add_journal_entry`) to a country that should
  hold it (`te_banking_entry_expected`: the rule on, not a decentralized nation, not revolutionary) and doesn't, and
  counts the adds. Once a game
  the first yearly pulse arms `te_debug_banking.1` for 30 days on, which logs `TE_SELF_CHECK OK|BROKEN
  banking_entry_everywhere missing=<n> added_by_net=<m>` (CLAUDE.md's self-check pattern). OK needs both at 0, so the
  net can't hide a gap; BROKEN means the engine left records out and the net carried them. The row is in
  `docs/testing/banking-playtest.md`'s Self-checks table.
  *Since 2026-10-17 the net runs on `on_monthly_pulse_country`, the row's fallback: the owner's EU game read BROKEN
  `missing=3 added_by_net=0`, so the engine does leave records out. The BROKEN line now names the countries missing.*
- **New countries** (releases, formables by `change_tag`, which keeps entries) get the entry like any other country,
  and start on `immediate` if they meet the test.
- **Revolutions.** `is_revolutionary = no` keeps the rebels out of the entry. Today unlocked rebels would get their
  own record and seed 50 / 0 / 0; at a win the winner's own values take precedence (§ "What a Civil War's Winner
  Inherits"), so a fresh rebel cycle would replace the nation's. Without a record of their own the winner inherits the
  loser's entry, `immediate` runs after the merge and finds the cycle running. A loyalist win changes nothing.

## 6. The AI

- **Dormant:** no tool is visible to it, so its banking choices are exactly today's no-entry ones. Its central bank
  is delegated and runs the AI mandate rule, as now (`is_player = no` comes first in every mandate branch).
- **Running:** unchanged. Every `ai_chance`, hold gate and simulator figure stands.
- **Restructuring** stays a cycle-holder's decision, so the AI's debt behaviour doesn't change either.

## 7. Cost

Today the engine evaluates the inactive entry's `is_shown_when_inactive`, building scan included, for every country
without the entry. After the change the dormant entry's monthly pulse runs the same test once a month (technology
first). Running countries pay what they pay now. No world sweep is added: the two `every_country` sweeps (contagion,
the Great Depression) still filter on a running cycle (`scripting_best_practices.md` § "Making an entry active for
every country turns its per-country pulse sweeps quadratic"). The monetary layer's modifiers move onto the entry for
every country (`te_monetary_settle_modifier_home`, built for an entry that appears mid-game).

## 8. The readers

Every `has_journal_entry = je_banking_cycle` outside the entry, classified (`scripting_best_practices.md` § "Widening an
entry's gate breaks every `has_journal_entry = X`"):

| Means | Sites | Change |
|---|---|---|
| **The cycle runs** | `banking_change_*` (3), `banking_enactment_run_shock`, `banking_cycle_spread_contagion`, `banking_crisis_wave_check_great_depression`, `banking_cycle_post_event_refresh`, `te_history_record_banking_samples` / `_marker`, `banking_is_bailout_recipient`, `banking_can_offer_bailout`, `banking_restructuring_shown`, `un_dev_fund_pays_into_pool`, `un_docket_loan_candidate`, `te_ap_economy_faltering`, `banking_external_available`, `banking_cycle_events.68`, `society_technology_events.30`'s `after`, `modern_election_events.15` (the boom story), `extra_law_events.62` (the panic desc), `un_events.35` | `te_banking_cycle_running` |
| **Has the controls** | `banking_mon_control_sgui`, the two mandate branches in `te_monetary_update_target`, `te_mon_mandate_runs_bank`, the eight `te_peg` tooltip switches (their `.tt` texts name controls a dormant country can't use) | `te_banking_controls_open` |
| **Has the panel** | the tab gates (`te_budget_banking_tab_sgui`, `_readout_sgui`) | keep |
| **The entry object** (its modifiers) | `te_monetary_settle_modifier_home`, `te_mon_mod_strip`, `te_mon_mod_has`, the FX and swap-line migrations, the two law cleanups in `extra_on_actions.txt`, the 38 `banking_tool_*_active` checks | keep |

A test holds every reader to one of the four rows, so a new one has to choose.

## 9. Not recommended: the cycle runs from 1836

The other reading of "always running": every country's cycle moves from game start and only the tools wait. Against
it:

- Every country without a stock exchange or a large city, most of the world for the first decades, would meet
  crashes, contagion and the Great Depression with no tool to answer them. The simulator's targets (crashes a century, tool response) were set for countries with a
  financial sector.
- Contagion reaches every trade-linked country with a cycle, so small economies would multiply each wave's count, and
  the Great Depression's ten-country threshold would fall early.
- Every country would pay the full monthly pulse (crash check, random events, phase modifiers) from 1836.

If the owner wants it, the start condition becomes `always = yes` and the tool gate becomes its own trigger (the
unlock test), with a simulator pass before shipping.

## 10. Open points

1. **Restructuring before the start.** The debt premium applies to every country, so a dormant country can be deep in
   default with nothing to negotiate. Opening Restructure the Public Debt to it is one trigger, but it is new AI
   behaviour. Recommended later, with its own simulator check.
2. **Credit Standing under Simplified.** The Monetary Policy section, Credit Standing with it, is hidden under the
   Simplified rule (`banking_mon_system_shown`), and there is no entry under Disabled, though both price debt the
   same way. So the Nation spec's "the Banking tab owns it" holds only under Enabled. Either the What Borrowing Costs
   rows show under Simplified too, or the Nation tab carries Credit Standing where the Banking tab doesn't. That
   belongs to PR #1018.
3. **Monetary history before the start.** The policy rate, rate paid and inflation could be sampled from 1836 (the
   store already caps itself at players and major powers), with the cycle charts hidden while dormant. Small; a
   follow-up.

## 11. Verification

- `test_banking_always_on.py`: the entry's gate (the rule and `is_revolutionary` only); the pulses' running branch and
  start branch; `immediate`'s start guard; the first line of every `banking_possible_*`; every enable button's
  `visible`; every reader in one row of § 8; every cycle gate in the banking GUIs on `banking_dash_cycle_running`, and
  `JournalEntry.IsActive` on the containers only; the safety net and its self-check.
- The strict audits, `organize_loc.py`, the GUI lint, the suite.
- The player guide: `04-banking.md` (the entry's start, the tab, "holds the journal entry" in contagion, the Great
  Depression, the UN loan and restructuring), and the guide's reference chapter where it says the same.
- Play-test list (`docs/testing/banking-playtest.md`): a new game's dormant entry and tab; the start notice; an old
  save's countries activating; the self-check line.
