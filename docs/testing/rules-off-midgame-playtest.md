# Play-test: a game rule switched off mid-game (2026-11-08)

A game rule can be changed mid-game, from the screen that changes country, and `disable_evaluation` touches only
inactive journal entry records: an active entry ran on after its rule was switched off, with its modifiers, pulses and
events. A Workshop player found Banking doing it (`banking-playtest.md`, "The rule switched off mid-game"). Every
rule-pruned entry now ends on its rule, through a hidden invalid outcome (the Nuclear Program by deactivating), and
each system clears what it left on the country, its states or the world (`scripting_best_practices.md`, the
`disable_evaluation` bullet; `test_journal_entry_shape.py`, `test_rule_off_teardown.py`). Culture merges and an
interstellar probe's transit pause instead.

**How to run a check.** Start a game with the rule on, play until the system is running for the player (the setup line
in each section), save, then set the rule off from the screen that changes country and play on. "Within a week" is the
entry's next update; "within a month" is the first monthly pulse. Each section's last check sets the rule on again.

**What this list can't settle offline.** That `add_journal_entry` brings back a type the country has concluded was
unverified until 2026-11-12, when the Colonial Empire's `ce_reentry` self-check read OK with `ended_before=yes` three
times in one game (`colonial-holdings-playtest.md`). Every "switched back on" check below that expects the entry
back rests on it; Banking's "Switched back on" row still checks its own entry.

## Social movements (Social Movements)

Setup: research Civil Rights Movement (or Mental Health Awareness) and let a debate start; under Civil Rights, switch on
a policy button.

1. **The entry closes** within a week, with "ended … or with the Social Movements game rule switched off" on its page.
   The debate's modifier is gone, and no debate event fires afterwards.
2. **Civil Rights' policy modifiers go** (Grassroots Organizing and the rest, and Cooptation's marker): none is left in
   the country's modifier list.
3. **Event modifiers stay.** A modifier an earlier debate event granted runs to its end.
4. **Switched back on**, the debate does not return in this game (no outcome set the resolved variable, but the concluded
   record is gone).

## Free Market Construction (switched to Disabled, and back)

This rule switches between two construction models, so nothing closes: the buildings are converted. Read live through
the harness on 2026-11-13 in both directions (`direct-construction-playtest.md`, which also lists what is left for a
player to look at). Setup: a market game with Construction Sectors and construction under way.

1. **Switched to Disabled**, within a day: every Construction Sector is a Construction Site of the same level and
   tier, the market's own level-1 sites are gone, no site carries the market's capacity modifier, and every country
   holds Base Construction. `debug.log` has `TE_SELF_CHECK OK construction_rule_switch to=direct`.
2. **A week later** the sites are staffed and construction is what the levels give plus 5.
3. **Switched back on**, within a day: the sites are government-owned Construction Sectors again, Base Construction
   is gone, and each country's capital gets a market site at its next weekly pulse. A player's government purchase
   is 0 until they set it.

## Heir Education

Setup: a monarchy with an heir and the entry running; turn on two focuses.

1. **The entry closes** within a week; the focus modifiers (Trait, Ideology and Interest Group Focus) are gone.
2. **Traits stay.** An heir who already has aptitude traits keeps them, subject to the monthly aptitude cleanup's rule
   table (`heir_education.md`).

## Custom Religion Allowed

Setup: Custom Religion Allowed, a player country, and the builder at stage 2.

1. **The entry closes** within a week, with "ended when the Custom Religion Allowed game rule was switched off", and no
   button founds a religion.
2. **A founded religion stays** where the builder had finished before the switch.

## Grand Monuments

Setup: a dedicated monument and a construction site.

1. **The entry closes** within a week: no Monuments entry, and the national monument modifiers are gone.
2. **The states' modifiers go** within a month: the monument's state has no Grand Monument tourism or dedication
   modifier (`gm_state_rule_off_on_action`), and the building pays no maintenance (its upkeep exemption stays).
3. **No cards.** The state panel shows no monument or site card, so no Dedicate button.
4. **No cultural pull** from monuments or Ancestral Antiquity in the Cultural Hegemony breakdown.
5. **Switched back on**, the entry is back within a month (`gm_country_refresh`), and the state modifiers return.

## Cultural Hegemony

Setup: the Ministry of Culture, program funding raised, one program (World Exposition) running.

1. **The entry closes** within a week; the hegemony and program modifiers are gone. Its concluded page names both
   reasons (switched off, or to Late Unlock before any country had Mass Media) and says it comes back, wrapped in full.
2. **Programs are shut down** (funding 0, no program variable), and no movement carries the hegemon's model pressure
   (`ch_remove_hegemon_model_pressure`).
3. **Switched back on**, the entry is back within two months for every country with Romanticism once some country
   has Mass Media (the Electric Telegraph under *Early Unlock*), programs at 0 (2026-11-15; before then it did not
   return). The net waits a month first (`ch_entry_net_waiting`), so the first month after the switch shows nothing.
   `debug.log` then has a `TE_CH_ENTRY adding … ended_before=yes on=1 …` line for each, written just before the add,
   and a month later `TE_SELF_CHECK OK ch_entry_return` (Self-checks).

## World War

Setup: World War on, two great powers of opposed ideologies, the entry in its leadup or a world war under way.

1. **The entry closes** within a week; Rising Tensions and the button modifiers are gone. Its concluded page names both
   reasons (switched off, or to Late Unlock before Combined Arms), says it won't return after a switch off and returns
   at Combined Arms after a switch to Late Unlock, wrapped in full.
2. **Variables clear** within a month on every belligerent, the war's target and late joiners included
   (`world_war_events_on_action`).
3. **A war under way** carries on as an ordinary war; no peace-conference event fires.
4. **Switched back on**, the entry does not return in this game (nothing re-adds an entry ended on the rule; a return
   was tried for #1823 and taken out, since after a world war it would restart the leadup: `game_rules.md`, the nets
   note; #1826).
5. **A quick off and on** during a world war or its three-year aftermath: switch the rule off, then on again before a
   month has passed. The monthly sweep clears the war's variables from a country without the entry (the war's target,
   late joiners) only on that country's pulse while the rule reads off. A month later, no country should still hold
   `ww_peace_concluded` or `ww_active_phase` (`scripts/analysis/save_country_probe.py <save> --var "^ww_"`). One left
   over blocks something for the rest of the game without a log line: a stale `ww_peace_concluded` stops every later
   return through `world_war_events_on_action` (a great power switched early to late waiting for Combined Arms), and a
   stale `ww_active_phase` stops every later world war (`world_war_conditions_met`). Not seen yet in a game; whether
   such entry-less holders occur in ordinary play is unknown.

## Colonial Empire (Decolonization)

Setup: a great power with colonies, the entry running, a pressure band reached (Strained or worse), one program raised.

1. **The entry closes** within a week with no event, no reward and no collapse.
2. **Subjects and movements are clear:** no colonial subject carries a Strained, Crumbling or Collapsing modifier, and no
   civil-rights movement a colonial radicalism modifier.
3. **A stance lies dormant.** A great power that condemns or supports colonialism loses the policy modifier and its
   influence cost within a month, and keeps the stance.
4. **Switched back on**, the entry returns about a month later (`ce_reentry_monthly`) with the programs at 0, and the
   stance's modifier comes back.

## Covert Warfare

Setup: funding at 1 or more, two operations running (one hostile), an agent network built.

1. **The entry closes** within a week; funding reads 0. Its concluded page reads, in full and wrapped, not cut off:
   "The journal entry ended, and every operation with it, when the Covert Warfare game rule was switched off, or was
   switched to Late Unlock before Mainframe Computers, Cyber Warfare or the … law. It comes back within two months once
   the rule is on and the conditions to open it are met." (reworded 2026-11-15: the old line was wrong on the
   early-to-late branch).
2. **Operations end** within days, each by its pact breaking (no infamy, no exposure event).
3. **Networks are gone**: the agent-network map is empty, and the Space Race's intelligence tier reads none.
4. **Switched back on** (2026-11-15; before then it did not return), within two months the entry is back for every
   country whose setting's gate is met (Mainframe Computers, Cyber Warfare or the ministry law under *Late Unlock*,
   Central Archives under *Early Unlock*): funding 0, no operations, no networks, Tradecraft as it was. The net waits a
   month first (`iw_entry_net_waiting`), so the first month after the switch shows nothing. `debug.log` has one
   `TE_COVERT_ENTRY ended branch=rule_off` line per country from the switch off, then one
   `TE_COVERT_ENTRY adding … ended_before=yes on=1 …` line per country, written just before the add. A month after the
   adds, `TE_SELF_CHECK OK covert_entry_return` (Self-checks).
5. **Not back every month.** Play two more months after item 4: no further `TE_COVERT_ENTRY ended` line, and the
   journal holds one running Covert Warfare entry, not a new one each month (the Workshop report of 2026-11-15:
   `covert_warfare.md`, Coming back). An `ended` / `adding` pair for one country, then a BROKEN line, is the report's loop:
   copy those lines, with their `branch=` and `on=`/`late=`/`early=`/`off=` fields, into the report.
6. **A game begun with the rule off**, switched to *Late Unlock* later: within two months every country with a late
   source holds the entry (`ended_before=no` on its line).
7. **A double switch inside a month.** In a game begun with the rule off, switch to *Early Unlock*. Just after the
   net's `adding` lines for the countries with Central Archives, switch to *Late Unlock* (those entries end,
   `branch=early_to_late`), then back to *Early Unlock* before the next monthly pulse. At that pulse: one
   `TE_SELF_CHECK BROKEN covert_entry_return … strike=1` line per such country, and no hold; a month later the entry is
   back for each, with a second `adding` line, and the month after that one OK line (once a game). A `strike=2` line
   here would mean the escalation is not working (Self-checks).

## Nuclear Weapons

Setup: an armed country (a warhead built), a nuclear guarantee for a partner, and if possible a crisis open.

1. **The entry leaves the journal** within a week (it deactivates).
2. **Within a month**, the Nuclear Power modifier is gone, the strike actions aren't offered, the guarantee and basing
   treaties lapse, and an open crisis closes with no outcome notice.
3. **No nuclear event** (Close Call, Anti-Nuclear Movement, brinkmanship) fires afterwards.
4. **The UN treats no one as armed**: a nuclear-ban accession offers no exemption for an arsenal.
5. **Switched back on**, the entry does not return in this game (the record is pruned); the stockpile is still there.

## Space Race

Setup: Full Colonies, two milestones running (one with a funding level), Space Command built, orbital debris above 0,
and a probe launched toward another star.

1. **Milestones close** within a week with "ended when the Space Race game rule was switched off"; no "program lost"
   event (.76) arrives, and completed milestones keep their rewards.
2. **Debris modifiers go** within a month (Orbital Debris and both cleanup prestiges), on countries without an entry too.
3. **Space Command** keeps no fleet upkeep or pause modifier.
4. **The probe's transit pauses**: its entry stays open, and its bar doesn't move.
5. **Switched back on**, each milestone a country is due returns within about two months (the re-entry pass), from 0
   progress, and the probe's transit carries on from where it stood.

## United Nations

Setup: a UN founded, the player a member with a seat, a convention ratified, a mission or mandate running.

1. **The entry closes** within a week, and the UN ends the same day: no member, no headquarters building, no agency.
2. **No dissolution**: no "the UN has dissolved" event (`un_events.30`), no power-bloc vacuum modifier, no refounding
   cooldown.
3. **A mandate holder** gets the voided-mandate notice (`un_mandate.1`), as the rule-off sweep always gave.
4. **International Oversight** holders are moved to National Licensing.
5. **Switched back on**, the entry does not return in this game, and a founding conference can't found a UN that
   members could join.

## Legislated Tax Code

Setup: Tax Code Enabled with a bill passed (a rate changed), and a second game under Light Tax Code with a tax set below
its law's rate.

1. **Full code.** Within a month the Legislated Tax Code gives way to the base-game taxation law its code was closest
   to, the tax-level buttons are live, and tax income doesn't fall to nothing at any point (check the weekly income the
   week the rule goes off: the amendments must not drop off before the law is replaced).
2. **Light code.** The entry closes within a week, the relief and the interest groups' reaction modifiers are gone, and
   the taxation law is unchanged. *Partly run through the harness, 2026-11-12 (`game-qa-results-2026-11-12.md`): with
   the rule switched from Light to Disabled in a copy of a fresh save, the rule-off branch ran for all 291 countries
   within the month. The entry, the modifiers and the law were not looked at.*
3. **Both.** No `te_tax_ig_view_*` or relief modifier is left on the country or its states.
4. **Switched back on**, the full code migrates the country again on the next monthly dispatch, from its base-game law.
5. **The Tax Code tab after the rule is switched on during play** (2026-11-13, a Workshop report: the tab greyed for
   ten years under the full code, its tooltip saying the conditions were met and the entry was not running). A game
   started with the rule Disabled, switched to Tax Code Enabled a few months in; and the game of item 4. Within two
   months the Budget panel's Tax Code tab opens, the Tax Code entry is in the journal, and `debug.log` has a
   `TE_TAX full_entry_net` line for each country the net reached. Failing: the tab still greyed with "Its conditions
   are met" after two months: read `has_journal_entry` and `has_inactive_journal_entry` for `je_tax_code` on the
   country; if an inactive copy exists that the engine never activates, the net's last condition is what stops it.
   **Self-check:** `TE_SELF_CHECK BROKEN tax_entry_inactive_stuck country=… months=3` in `debug.log` (either
   setting; there is no OK line) says exactly that for the country named: the code in force, the entry not active
   and an inactive copy held for three months running. The greyed tab's tooltip cannot tell this from a country
   with no record, which is why the line exists. If it appears, the nets do not cover the reported bug; the fallback
   is the owner's call (the candidates: take the entry off `disable_evaluation` so the record is never pruned and
   re-made, or open the tab on the code being in force instead of on the entry).

## Banking: Full to Simplified

The banking rule has a third setting: Simplified keeps the entry and the cycle and switches off the monetary layer
(`banking_cycle.md`, "Full to Simplified mid-game"). Setup: Banking set to Full, a national bank on fiat money with
inflation above the comfort band, a loose or tight stance, Sterilization on, and, in a second game, a gold
standard the peg crisis suspended. For row 6, sign a swap line (drawn on in a crisis, if one comes), a lender of last
resort and, against a defaulted country, a debt receivership, inside their binding periods, and note both parties'
infamy, relations and legitimacy. Switch the rule to Simplified.

1. **The entry stays**, and within a month none of the inflation-band, stance-politics, real-wage, minting, exchange-rate
   or arrangement modifiers is left on the entry or the country. The rate paid is still there.
2. **The rate paid** stops counting inflation: within a month it is the reference rate plus the risk premium, with no
   inflation, expectations, monetisation or exchange-rate term in its breakdown.
3. **The stance band** on the entry is the neutral one, and the cycle panel shows no stance push.
4. **Sterilization is off**, its history marker is drawn, and its weekly bill is gone from the budget a week
   later. The same for any other External & Currency tool that was on.
5. **The suspended gold standard** counts as convertible again (the simplified End the Gold Standard event can fire in
   a downturn).
6. **The monetary treaties end** soon after the switch: a "… invalidated" notification for each swap line, lender of
   last resort, receivership and peg, and the article is gone from its treaty (a treaty with nothing else in it is
   gone). Nobody is charged for it: neither party's infamy rises and no relations hit or "treaty broken" line appears,
   on either side. The receivership's debtor gets its 10 legitimacy back, and the leverage lines are gone from the
   influence breakdown. A swap line that was drawn on is settled in one payment, with both parties' notices. The next
   imported crash is not eased by the old guarantee. A bloc keeps a monetary-union principle it held.
   Read `TE_SELF_CHECK mon_rule_switch_treaties` (below).
7. **Switched back to Full**, the dial, inflation and exchange rate start again from the neutral seeds, and the log has
   one `TE_MONETARY: … left the full monetary system` line per country from the earlier switch.

## Private Actors

Setup: a game with Private Actors Enabled, played a year so every firm has taken a turn, with a firm of the player's
past 40% of its sector or failing (its notice posted), and, played on, a cartel (open or secret) and a foundation
somewhere (the console can set `te_pa_share` to 0.6 on a Dominance firm before its turn), a petition under way with its
alert showing, one of the state's actions taken (a suit or an inquiry), and some firm's patronage on an interest
group (a "Patronage from Firms" modifier on the country), and a petition for a law or a tariff taken up, so some firm
holds the government's pledge (`te_pa_pl_kind`; its tariff, if one, set). Note a few firms' `te_pa_goal`,
`te_pa_funds`, `te_pa_cartel`, `te_pa_found` and `te_pa_turn_in` and the player's `te_pa_ledger`.

1. **Within a month** the country's `te_pa_rows` list and its containers are gone, `te_pa_q_in` is gone, and no firm
   holds `te_pa_row`, `te_pa_n_failing` or `te_pa_n_big`. No modifier of the system's is on the country or its states:
   no "<company> Cartel" or "Restricted Supply (author unknown)" on any country, no "<company> Foundation" on any state,
   and `te_pa_cartels` is gone. The declared move's variables (`te_pa_move_firm`, `te_pa_move_months`,
   `te_pa_move_hand`) and the month's candidates are gone, so neither top-bar alert shows, and no interest group holds
   "State Action Against Its Firm" or "Resents a Monopoly Charter". No "Patronage from Firms: <group>" is on any
   country, the Politics section's rows (`te_pa_pol_view`), `te_pa_presses` and `te_pa_elect_end` are gone. The
   petition's record (`te_pa_pt_firm` and the rest of `te_pa_pt_*`) is gone, and no firm holds a pledge
   (`te_pa_pl_kind`, `te_pa_pl_back`) or an ask (`te_pa_move_ask`): the pledges lapse with the rule, unbroken. A
   tariff a pledge set stays at its level (it is the market's own setting now).
2. **The records stay**: each firm keeps `te_pa_init`, its goal, its currencies, its holdings (`te_pa_cartel`,
   `te_pa_reg`, `te_pa_found`) and its `te_pa_turn_in`, which no longer counts down; a foundation's state keeps
   `te_pa_st_found_str`. The ledger stays as it was.
3. **Nothing runs**: over the next year no `te_pa_turns` rises and no ledger line is written.
4. **Switched back on**, within a month the rows are back (one a firm), the turns count down from where they stopped,
   and a firm still past a threshold posts its notice once more. A case under way (`te_pa_case_end`) reaches its
   verdict at the next month if its time has passed; a levy, an inquiry and a charter resume from the firm's record.
   A petition that was under way counts as ended at the switch, so the next waits 12 months from it. The foundations' modifiers are back at the next month,
   the cartels' and the patronage modifiers at the next quarter, at the strengths and totals the records held; a
   press, the sides on a law and a wager resume from the records (`te_pa_press`, `te_pa_side_law`, `te_pa_bet_ig`).
   No pledge comes back, and none is counted broken: a firm may petition again once the twelve months have passed.

## Self-checks

Every other check above is a look at the panels and the modifier list. A failure's fallback is in the system's own doc,
under its "Switched off mid-game" note.

| Self-check | OK means | BROKEN means, and the fallback |
|---|---|---|
| `covert_entry_return` (Covert Warfare, items 4 to 7; per add, OK once a game, logged by the monthly pass after the net added the entry) | the entry the net added last month is running: `add_journal_entry` brought it back and the outcome did not end it again | the entry is not running though the country is still due it: it ended at once (read the `TE_COVERT_ENTRY ended` line before it, whose `branch=` and `on=`/`late=`/`early=`/`off=` fields say what the outcome read; `branch=neither`, or `on=0` beside the BROKEN line's `on=1`, is a rule read that differs between an outcome and an on_action, and two settings at 1 a setting name no rule file defines), or the add failed (no `ended` line between the `adding` line and BROKEN). A first BROKEN (`strike=1`) marks the country for 400 days (`iw_entry_net_strike`) and the net tries again; a second while the mark stands (`strike=2`) holds the net off it for a year (`iw_entry_net_hold`), so the loop the Workshop player saw slows from monthly to twice in sixteen months, and a player's quick double switch (item 7) gives one `strike=1` and no hold. The fallback is the owner's: what the fields show decides it (`covert_warfare.md`, Coming back) |
| `ch_entry_return` (Cultural Hegemony, item 3; as above) | the entry the net added last month is running | as `covert_entry_return`, for `je_cultural_hegemony` (`ch_entry_net_strike`, `ch_entry_net_hold`), with the same `strike=` and `on=`/`late=`/`early=`/`off=` fields and `late_gate` (some country has Mass Media); its outcome writes no line of its own, so the BROKEN line's fields are the reading |
| `mon_rule_switch_treaties` (Banking: Full to Simplified, row 6; logged once a game, one to two months after the switch, by a country that held a swap line, guarantee or receivership on its last Full pulse) | the country stands in none of the three articles any more: the `te_mon_full_system` requirement ended it | the article is still in force: the engine does not end an in-force article on a failed requirement, or not this soon. Script has no penalty-free way to end one article (`withdraw` is a treaty effect, and inside the binding period it is a break), so the fallback is the owner's: withdraw the treaty from `te_monetary_leave_full_system` (step 4) and accept what that charges, or leave the articles in force with their mechanics stopped, as before #1507. The same if row 6 shows a penalty |
