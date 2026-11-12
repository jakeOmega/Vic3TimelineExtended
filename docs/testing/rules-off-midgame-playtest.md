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

**What this list can't settle offline.** That `add_journal_entry` brings back a type the country has concluded is
unverified (the Colonial Empire's `ce_reentry` self-check and Banking's "Switched back on" row ask the same thing).
Every "switched back on" check below that expects the entry back depends on it.

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

1. **The entry closes** within a week; the hegemony and program modifiers are gone.
2. **Programs are shut down** (funding 0, no program variable), and no movement carries the hegemon's model pressure
   (`ch_remove_hegemon_model_pressure`).
3. **Switched back on**, the entry does not return in this game (nothing re-adds it).

## World War

Setup: World War on, two great powers of opposed ideologies, the entry in its leadup or a world war under way.

1. **The entry closes** within a week; Rising Tensions and the button modifiers are gone.
2. **Variables clear** within a month on every belligerent, the war's target and late joiners included
   (`world_war_events_on_action`).
3. **A war under way** carries on as an ordinary war; no peace-conference event fires.

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

1. **The entry closes** within a week; funding reads 0.
2. **Operations end** within days, each by its pact breaking (no infamy, no exposure event).
3. **Networks are gone**: the agent-network map is empty, and the Space Race's intelligence tier reads none.
4. **Switched back on**, the entry does not return in this game.

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
   the taxation law is unchanged.
3. **Both.** No `te_tax_ig_view_*` or relief modifier is left on the country or its states.
4. **Switched back on**, the full code migrates the country again on the next monthly dispatch, from its base-game law.

## Banking: Full to Simplified

The banking rule has a third setting: Simplified keeps the entry and the cycle and switches off the monetary layer
(`banking_cycle.md`, "Full to Simplified mid-game"). Setup: Banking set to Full, a national bank on fiat money with
inflation above the comfort band, a loose or tight stance, Sterilize Capital Inflows on, and, in a second game, a gold
standard the peg crisis suspended. For row 6, sign a swap line (drawn on in a crisis, if one comes), a lender of last
resort and, against a defaulted country, a debt receivership, inside their binding periods, and note both parties'
infamy, relations and legitimacy. Switch the rule to Simplified.

1. **The entry stays**, and within a month none of the inflation-band, stance-politics, real-wage, minting, exchange-rate
   or arrangement modifiers is left on the entry or the country. The rate paid is still there.
2. **The rate paid** stops counting inflation: within a month it is the reference rate plus the risk premium, with no
   inflation, expectations, monetisation or exchange-rate term in its breakdown.
3. **The stance band** on the entry is the neutral one, and the cycle panel shows no stance push.
4. **Sterilize Capital Inflows is off**, its history marker is drawn, and its weekly bill is gone from the budget a week
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

## Self-checks

Every other check above is a look at the panels and the modifier list. A failure's fallback is in the system's own doc,
under its "Switched off mid-game" note.

| Self-check | OK means | BROKEN means, and the fallback |
|---|---|---|
| `mon_rule_switch_treaties` (Banking: Full to Simplified, row 6; logged once a game, one to two months after the switch, by a country that held a swap line, guarantee or receivership on its last Full pulse) | the country stands in none of the three articles any more: the `te_mon_full_system` requirement ended it | the article is still in force: the engine does not end an in-force article on a failed requirement, or not this soon. Script has no penalty-free way to end one article (`withdraw` is a treaty effect, and inside the binding period it is a break), so the fallback is the owner's: withdraw the treaty from `te_monetary_leave_full_system` (step 4) and accept what that charges, or leave the articles in force with their mechanics stopped, as before #1507. The same if row 6 shows a penalty |
