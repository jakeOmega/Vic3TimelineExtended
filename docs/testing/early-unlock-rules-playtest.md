# Play-test: early and late unlock settings (2026-11-13)

Four game rules gained a third setting, prompted by Steam Workshop feedback: *Early Unlock* opens the system at an
earlier technology, with the parts that only make sense later kept behind their own technology; *Late Unlock* is the
system as it was and keeps the old setting name, so a save made before keeps it. Design and wiring:
`docs/systems/mod_systems/game_rules.md` § "Early and late unlock". Nothing here gates a merge; the release play-test
works through it before any early setting becomes a default.

**What the offline checks hold.** `test_rule_unlock_settings.py`: each rule's three settings and one flag each, the
defaults unchanged, no bare `has_game_rule` read of the four systems outside `te_rule_setting_triggers.txt`, the late
gates equal to what they were, the early gates, and what each early setting keeps behind the late gate. For the United Nations it also holds the
League's name (`UnitedNationsLeagueNameTest`): only `un_league_stage` picks it (through `un_ov_league_sgui`), and
outside it each name that splices it reads exactly as before; and German and Spanish keep their translation of it
(`UnitedNationsLeagueTranslationTest`).

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
   Archives open the entry within a week, capped as in 2. A country that had the entry before keeps it uncapped while
   it still holds a late source.
8a. **The cap follows the source (intended).** On *Early Unlock*, a country whose only late source is the Ministry of
   Intelligence and Security law, funded above Professional: repeal the law (or console-activate another law of the
   group). At the next monthly pulse its funding is 2, the stepper's plus is grayed again with the line "Funding above
   Professional needs …", and operations keep running at the lower level. With one of the four technologies as well,
   nothing changes.
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
4a. **The war is classed at the outbreak, not when the entry closes** (review fix, 2026-11-13). Start an early war
   between two powers without Combined Arms; the console shows global `ww_last_war_early` = 1 from the launch.
   (i) Console-research Combined Arms for one belligerent during the war or its three post-war years: when its entry
   completes it holds `ww_early_war_resolved`, not `ww_entry_resolved`, and the entry is back within a month or two.
   (ii) A great power that held Combined Arms and only watched: the same. In both cases the new entry does not
   complete again three years later (it waits until no country still has `ww_peace_concluded`). Failing: a power
   with `ww_entry_resolved` after an early war, or an entry that completes twice on one war.
4b. **A war begun with Combined Arms is the last.** Launch a war where the launcher or its target has Combined Arms:
   `ww_last_war_early` = 0, and every entry that closes on it sets `ww_entry_resolved`, also for a power still
   without Combined Arms.
4c. **Yesterday's Ally** (`world_war_events.105`). After an early war in which a democratic and an authoritarian
   great power fought on the same side, neither communist nor fascist: the event does not fire between them in the
   post-war years. It still fires between former allies of opposed ideologies (democratic and communist, say).
5. **Early to late, mid-game.** With an entry open for a great power without Combined Arms, switch to *Late Unlock*:
   within a week the entry is gone, and it comes back within a month of researching Combined Arms.
6. **Late unlock is unchanged.** On *Late Unlock* (or a save from before this change): no entry before Combined Arms,
   and an authoritarian great power's entry stays inactive.

## United Nations

Setup: a new 1836 game with United Nations on *Early Unlock*, as a great power, console-researching Multilateral
Alliances.

1. **The entry opens with Multilateral Alliances.** Before it, the Diplomacy panel's UN tab is grayed and its tooltip
   names Multilateral Alliances and Intergovernmental Organizations. With it, the UN entry is shown and Found the League
   is offered (item 6), its tooltip naming the same two technologies.
2. **Founding works.** Found it: the charter event reaches other countries, the founder holds a permanent seat, and
   authority starts at 50.
3. **The league can't reform.** Play (or console-raise authority) until it has held near 70 for 24 months: Why UN
   Authority Is Moving shows the month count and the line "No charter reform yet"; Propose a Resolution's Charter
   Reform row and the AI's button are refused with the line naming Intergovernmental Organizations; no The Charter Has
   Been Outgrown docket event fires.
4. **The age arrives.** Console-research Intergovernmental Organizations for any country: within a month (the global
   pulse) the league line is gone, and a ripe reform can be tabled at once.
5. **Late unlock is unchanged.** On *Late Unlock* (or a save from before this change): no entry and no founding before
   Intergovernmental Organizations, and the founding button's line is the bare technology, as before.
6. **The League's name, before the age.** On *Early Unlock* with Multilateral Alliances and no country with
   Intergovernmental Organizations, each of these reads "League of Nations": the journal entry's title in the journal
   list and its header; the Timeline Extended window's United Nations tab (on two lines, "League of" over "Nations", not
   elided) and its locked tooltip's heading; and the header inside the UN tab of the Diplomacy panel and of National
   Info. Those two tabs' own labels read "UN" and don't change. The founding control under the overview's No UN cell
   reads "Found the League", on one line inside the button. The charter event, body text, event descriptions and "UN"
   stay as they were. The name is picked by the scripted GUI `un_ov_league_sgui` (`un_org_name_ingame`, behind
   je_united_nations's `GetPlayer.IsValid` guard), the form the Timeline Extended tabs' tooltips already evaluate; no
   log line is expected from it. A raw key, a printed `SelectLocalization(...)`, or any new `error.log` or `debug.log`
   line naming `un_ov_league_sgui` or `un_org_name` is a failure.
7. **The League becomes the United Nations.** Console-research Intergovernmental Organizations for any country with the
   League founded: within a month every name in item 6 reads "United Nations" again, and the player (member or not)
   gets one feed notification, The League Becomes the United Nations, saying the League is now the United Nations and
   its charter can be reformed. It doesn't come again the next month, and it doesn't come at all when no League was
   founded before the age.
8. **No League otherwise.** On *Late Unlock*, and in a save from before this change, every name in item 6 reads "United
   Nations" throughout and no such notification comes. With the rule *Disabled* when some country researches
   Intergovernmental Organizations, then switched to *Early Unlock* from the screen that changes country, nothing reads
   "League" even for a month, and no notification comes. As an observer, open a great power's National Info UN tab:
   its header reads "United Nations" (the `GetPlayer.IsValid` guard) and the logs gain no line from it.
9. **German and Spanish.** With the game in German, every name in item 6 reads "Vereinte Nationen" outside the League
   (in Spanish "Naciones Unidas"), as before this change. Inside it the League's keys show English ("League of
   Nations", "Found the League", the notification) until the owner's translation pass.

## Cultural Hegemony

Setup: a new 1836 game with Cultural Hegemony on *Early Unlock*, as France (Romanticism), console-researching the
Electric Telegraph for any country.

1. **The entry opens with the telegraph.** Before it, the Society panel's Hegemony tab is grayed and its tooltip reads
   "Any country has researched the Electric Telegraph or Mass Media". Within a week of the research, the Cultural
   Hegemony entry is active for countries with Romanticism, with their tiers and shares.
2. **What waits for Mass Media.** With the Ministry of Culture enacted (console Mass Propaganda), Begin International
   Cultural Outreach is offered with the telegraph; Launch Global Media Campaign is refused with "Requires Mass Media".
   No event about radio, film or broadcasts fires before Mass Media; The World Is Watching (`.8`) and The Touring
   Collection (`.10`) can.
3. **Early to late, mid-game.** With the entry open and no country holding Mass Media, switch to *Late Unlock*: within
   a week the entry is gone and its programs end. Console-research Mass Media for some country: within a month the entry
   is back.
4. **Late unlock is unchanged.** On *Late Unlock* (or a save from before this change): no entry before some country has
   Mass Media, and International Cultural Outreach needs Mass Media.
