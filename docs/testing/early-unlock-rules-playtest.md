# Play-test: early and late unlock settings (2026-11-13)

Four game rules gained a third setting, prompted by Steam Workshop feedback: *Early Unlock* opens the system at an
earlier technology, with the parts that only make sense later kept behind their own technology; *Late Unlock* is the
system as it was and keeps the old setting name, so a save made before keeps it. Design and wiring:
`docs/systems/mod_systems/game_rules.md` § "Early and late unlock". Nothing here gates a merge; the release play-test
works through it before any early setting becomes a default.

**What the offline checks hold.** `test_rule_unlock_settings.py`: each rule's three settings and one flag each, the
defaults unchanged, no bare `has_game_rule` read of the four systems outside `te_rule_setting_triggers.txt`, the late
gates equal to what they were, the early gates, and what each early setting keeps behind the late gate.

**How to run a check.** A setting is chosen on the Game Rules screen of a new game, or changed mid-game from the screen
that changes country. "Within a week" is a journal entry's next update; "within a month" is the first monthly pulse.

## Covert Warfare

Setup: a new 1836 game with Covert Warfare on *Early Unlock*, as a great power (Prussia or Russia) that researches
Central Archives early.

1. **The entry opens with Central Archives.** Before it, the Military panel's Covert tab is grayed and its tooltip names
   Central Archives first, then the late sources. Within a week of the research, the Covert Warfare entry is active.
2. **Funding stops at Professional.** The Level stepper's plus button grays at level 2, and its tooltip has a crossed
   line naming Mainframe Computers and the other late sources. The overview still reads "level 2 of 5".
3. **Only the early operations are offered.** Another great power's diplomatic actions offer Covert: Industrial
   Espionage, Military Espionage, Cultivate Assets and (to a friend) Counterintelligence Support; Election Interference,
   Influence Campaign and the other technology-gated ones are listed with their technology unmet. At war, Infrastructure
   Sabotage is offered too.
4. **One slot is enough.** A minor with an early entry (one slot) can launch one operation; a great power runs three at
   priority 1, and the Operation Slots row shows 3. Domestic defense (Unused Operation Slots) appears on the entry's
   modifiers while slots are free.
5. **The AI copes.** By 1850, in the observer view, some AI great powers hold the entry, their funding is never above 2
   (the overview tooltip of a few), and some run espionage against a rival. Nothing in `error.log` names `iw_`,
   `covert_agency` or `te_covert_warfare`.
6. **The cap lifts at the late gate.** Console-research Mainframe Computers (or enact the Ministry of Intelligence and
   Security): the stepper goes past 2, and the AI's great powers fund at 3 again within a month.
7. **Early to late, mid-game.** With an early entry running two operations and no late source, switch the rule to *Late
   Unlock*: within a week the entry is gone, the operations end (funding 0) and the agent networks are cleared. Research
   Mainframe Computers: within a month the entry is back, at funding 0, Tradecraft kept.
8. **Late to early, mid-game.** In a game started on *Late Unlock*, switch to *Early Unlock*: countries with Central
   Archives open the entry within a week, capped as in 2. A country that had the entry before keeps it uncapped.
9. **Late unlock is unchanged.** A game on *Late Unlock* (or a save from before this change, which reads as it): no
   entry before Mainframe Computers or the Ministry, and funding goes to 5.

## World War

Setup: a new 1836 game with World War on *Early Unlock*, observed or played as Great Britain, run with the console
researching Trench Works for two or three great powers of each camp (democratic: Great Britain, France; authoritarian:
Russia, Austria, Prussia).

1. **The entry opens with Trench Works.** A great power with Trench Works and a rivalry with an opposed great power
   holds The Gathering Storm within a week; its status names its camp (Democratic or Authoritarian). Without Trench
   Works it has none.
2. **Democratic against authoritarian counts until Combined Arms.** With Great Britain rivaling Russia, its status
   reaches "Tensions are rising" and Begin Rearmament's tooltip asks for "Trench Works or Combined Arms researched".
   Console-research Combined Arms for Russia: within a month that pair no longer raises Britain's tension.
3. **A war can start and end.** Let tension reach the crisis band: The Brink of War (`.5`) fires for one side, the play
   becomes a war, and after it the peace conference and the post-war years run as under *Late Unlock*. Strategic
   Bombing (`.11`) never fires while no enemy has Bombing Aircraft.
4. **A second world war.** After the early war's entry completes (or fails), the country has no entry until Combined
   Arms; console-research it and, within a month, the entry is back (inactive or active).
5. **Early to late, mid-game.** With an entry open for a great power without Combined Arms, switch to *Late Unlock*:
   within a week the entry is gone, and it comes back within a month of researching Combined Arms.
6. **Late unlock is unchanged.** On *Late Unlock* (or a save from before this change): no entry before Combined Arms,
   and an authoritarian great power's entry stays inactive.
