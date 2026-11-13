# Play-test: direct construction (Free Market Construction off), 2026-11-13

Players reported that Base Construction did not work right with the Free Market Construction rule off: for some not at
all, for some not after loading a save. Two faults were found and fixed, both read in the running game through the QA
harness (`python3 -m game_qa`), and the build lens now offers the Construction Site. System reference:
`docs/systems/mod_systems/construction.md` § "Free Market Construction off"; the tests are
`test_construction_rule_switch.py`.

## What was wrong

**1. Base Construction followed the player's last lobby, not the save.** The Disabled setting applied the modifier with
`apply_modifier = all:te_direct_construction_base_modifier`. The base game never uses that line (as read by this
session; not re-read since). The engine did not apply it by the save's rules; the setting it applied was the one the
player last applied in a lobby on their machine (kept, all but certainly, in `player/game_rules/presets.txt`,
`LastAppliedRules`). Every load below was a launch of the QA harness straight into the save (`-loadsave`); the check
by hand further down read the same at a load from the main menu:

| Save loaded | Its rules (`has_game_rule`) | The lobby's last applied rules | What the engine applied |
|---|---|---|---|
| A market game, never switched | Free Market Construction Enabled | Disabled | The Disabled setting's modifier: a marker of 11 on Disabled read 11, a marker of 3 on Enabled read 0, and every country had 5 construction a week |
| The same, with culture merges switched off in the save | Enabled; culture merges disabled | Disabled; culture merges enabled | Markers 1, 10, 100, 1,000 and 10,000 on the five construction settings summed to 10,000 (Disabled alone); markers 1 and 10 on the two culture-merge settings read 1 (enabled alone) |
| The owner's own played save, loaded straight into play | Enabled | Disabled | A marker on every setting read 7 for the player and for two AI countries, so the rule's line is read at load on that path too |

**What was read and what is inferred.** Read directly, in two rules: the modifier the engine applied was not the
one of the save's setting, and `has_game_rule` and the setting's production-method flags did follow the save. Read by
hand on 2026-11-13 ("The check by hand (#1767)" below): a load from the main menu behaves as the harness's
`-loadsave` launch does, in the same session and after a fresh launch. A Disabled save loaded after a lobby that
applied Enabled had no Base Construction. Still inferred, though all but settled: that `LastAppliedRules` is where the
engine keeps the last lobby's setting. It named the applied setting every time (Disabled, and culture merges enabled,
neither of them the default nor both the last setting defined). It was the one file written when the Enabled lobby's
game started. No other file in the user-data folder outside `save games/`, `logs/` and `mod/` names the setting. But
nobody has edited the file by hand to watch the modifier follow. Either way the line could not be relied on, and
script does not use it any more.

So a player who starts a Disabled game has the 5 points while Disabled is what they last set up. Once they start a
game under other rules from any lobby, that game loses its Base Construction at the next load (read by hand), and a
market game loaded after a Disabled lobby gains 5 points it should not have (read through the harness). The save holds no trace of the modifier, and `has_modifier` never saw it.
The production-method flags of a setting are not affected: they followed the save in every run.

Fix: script adds the modifier under `has_game_rule`, which follows the save
(`te_direct_construction_ensure_base`), and no rule setting carries an `apply_modifier` line.

**2. The conversion ran only when a game started.** A rule can be changed in a running game, from the screen that
changes country. A market game switched to Disabled kept its 381 Construction Sectors and its 412 market sites. The
engine moved the sites to a direct method, and each kept the capacity modifier the market's last weekly pulse had put
on it. France's capital site stood at −100% throughput, so France had exactly 5.0 construction a week a month later
(Base Construction alone), and no Construction Site level it built would have added to that. The sector stayed
buildable and sold a good nobody bought.

Fix: `te_construction_market_follow_rule` runs every day and converts in either direction when the rule and the
buildings disagree.

**An independent review of the branch** (a second agent, told to break it, 2026-11-13) found no way for the harness
change to touch a save that is not the harness's own. Its findings that were fixed: the switch's self-check read OK
when a switch made nothing (it now compares what stands with what the switch should have made); a site-guard record
on a state with no site outlived a market period and would have had the guard build a site from nothing at the next
switch (both switches forget every record first); the weekly pass rebuilt a staffed site to cancel a sector that
never stood (it only cancels now); a harness save named in another letter case passed as switchable; and a named
harness save's kept self-check lines were not shown. Its question whether re-created sectors get the retooling
surcharge was read in the game: they do not (below). One finding is left open as item 7 of the list at the end.

**A second review, by another session, posted on the PR.** Each point was checked against the code before anything
changed. Four held and are in: a switch now applies the new model's Construction Cost Scaling at once (the market's
price and goods per point use the live scaling whether or not the modifier is in force, so a switch that only cleared
the modifier left a rich country's Fixed Budget buying fewer points than it paid for until its yearly pulse); a site
kept because its owner has no Urbanization is set to level 1, as the market's sites are; the switch's self-check
line carries `capped=N`; and the stray-sector walk runs every fourth week. The fifth is a fact for the owner's
decision in #1764: a switch to Disabled and back leaves every sector owned by the government.

**A side finding, fixed with it.** An AI country (Bornu) queued a Construction Sector on a new direct game's first
day, before the conversion closed the sector. Its construction never finished: five months later it still had 100
points left. The weekly pass now cancels a sector under construction in a direct game.

## Live results with the fix (2026-11-13)

**The base is 10 now (#1768, after these runs).** Every reading below was taken when Base Construction was 5 points a
week, and they stand as read: the 5.0, 5.1, 5.2 and 5.4 figures are 5 plus a fraction of a site level, and a new game's
countries read 5. On the current build the same rows should read 5 more (10.0, 10.2, 10.4, …; France 47.4 where it read 42.4: expected,
not read), and the base self-check counts a holder under 10 as `under_base`. Nothing else in the runs depended on the
figure.

Every run loaded the branch's changed files as a variant mod beside the deployed build. Greece and France were played;
a new game's rules were the owner's last applied (Free Market Construction Disabled).

| Run | What was read | Result |
|---|---|---|
| Market game of three months, rule switched to Disabled | The day after load | `TE_SELF_CHECK OK construction_rule_switch to=direct sites=378 sectors_left=0 market_modifiers_left=0`; all 291 countries hold Base Construction; no sector constructible, the site constructible |
| | Two weeks and four weeks on | France 14.4, then 42.4 construction a week (5.0 without the fix); the United Kingdom 62.4; 376 of 378 sites still standing (the AI had removed 23 in a week before the conversion set the guard's record); `TE_SELF_CHECK OK direct_base_construction holders=291 under_base=0 missing=0` |
| Direct game, rule switched to Enabled | The day after load | `TE_SELF_CHECK OK construction_rule_switch to=market sectors=381 sites_left=0`; France's capital has a level 29 sector on Iron-Frame Buildings |
| | Two weeks on | No country holds Base Construction and Greece reads 0 construction; 399 sectors, 357 sites, every site on the market method; the construction good's price is £1,616 |
| The switch to Disabled, run again after the review's fixes | The day after load, and three weeks on | `… construction_rule_switch to=direct sites=378 expected=378 sectors_left=0 market_modifiers_left=0`; France 42.4; 376 sites, no sector; the base self-check OK |
| Both switches, run again after the second review's changes, with the United Kingdom given a full share of its scaling first | The day after load | To Disabled: `… to=direct sites=378 expected=378 capped=0 sectors_left=0 market_modifiers_left=0`, and the United Kingdom holds `construction_cost_scaling_direct` at 0.0022, the size its scaling had. To Enabled: `… to=market sectors=375 expected=375 capped=0 sites_left=0`, and it holds `construction_cost_scaling` at 0.0029. Neither waited for a yearly pulse |
| The switch to Enabled, run again after the review's fixes | Four days and two weeks on | `… construction_rule_switch to=market sectors=375 expected=375 sites_left=0`. No retooling follows the switch: 935 buildings moved from No Maintenance to Maintenance and none of the 375 re-created sectors carries `pm_retooling` (France's capital sector: Iron-Frame Buildings, Maintenance, no Retooling). Retooling buildings in the world went 3, 12, 64, the AI's own method changes |
| Direct game from before the fix, loaded with it | At load | No country has the modifier, Greece reads 0 (the rule's line is gone) |
| | Two weeks on | All 290 countries hold it; Greece 5.2 (5 and a fifth of a site level), so nothing is counted twice; the base self-check reads OK |
| New game under Disabled, made with the fix (run again on the final files, after the base left country setup: the same) | Its second day | All 291 countries hold Base Construction and read 5 construction a week; 376 sites, no sector |
| | A month on | Greece's queued site level is 16 weeks from done on 5.4 points; France 42.6, the United Kingdom 62.6; 387 sites; the base self-check reads OK |
| Market game of three months, never switched (the default most players have) | At load | Nothing converted: 412 sites on the market method, 381 sectors; no country holds Base Construction, and the United Kingdom reads 43.55 construction a week where the old rule line gave it 48.55 |
| | Two weeks on | A Base Construction added to France by hand is gone (the market's weekly pulse removes it); 414 sites, 382 sectors, the sector constructible and the site not; no `construction_rule_switch` line and no construction error in `error.log` |
| Build lens, direct game | Production lens, Development tab | Construction Site is the first option |
| Build lens, market game | The same | No Construction Site (the lens hides a building whose `can_build_government` is false) |

**Not run in its final form: the weekly pass's cancel.** A sector under construction in a converted game is now
cancelled by a bare `remove_building`, without rebuilding the state's site. No stray sector appeared in the last
new-game runs, so that branch has not run in a game. What it rests on was read by hand in the first run
(`remove_building` on Bornu's level-0 sector took it out of the queue, 2 queued levels to 1), and
`test_construction_rule_switch.py` pins the wiring.

**One log line to expect at a switch.** A Construction Sector that was queued and had not started building when the
rule went to Disabled cannot start afterwards. The engine drops it, once, with `Assertion failed: Failed creating
backing building for Building Type building_construction_sector` and, at the same second, two `Scoped object is not
valid. Type: Building` errors from the hooks that ran on the building that was never made
(`te_construction_market_building_events.txt:14`, `te_construction_market_on_actions.txt:344`). Seen for one queue
element (Württemberg's) in the switched market game, and not again in the four weeks after.

Before the fix, in a new direct game: Greece queued a second site level on its 5.1 points and had it built in 18
weeks; a country made in play (Byzantium, from a Greek state) had 5 points at once and its AI queued a first site.
Those hold with the script-owned base, which reaches a new country at its first weekly pulse.

## The check by hand (#1767)

The harness cannot settle where a rule setting's `apply_modifier` comes from: it never writes the owner's
`presets.txt` (owner, 2026-11-12), its snapshot does not cover `player/game_rules/`, and it always launches straight
into a save. Since this change, `start`'s reply names a rule whose setting in the loaded save is not the one
`LastAppliedRules` names (`rules.lobby_differs`), so a later harness reading says when the two disagreed; the
readings above predate that, and none of the recorded session files holds the presets file's contents.

**What the repo's records add.** A fixture's key follows `LastAppliedRules`, so a `start` that finds one rather than
making it was under the rules the fixture was made with. The last such start recorded, at 08:57 UTC on 2026-11-13
(`docs/testing/game_qa_probe/captures/session_2026-11-13_qa_prs/sessionD_steps.jsonl`), found a fixture whose save
carries `free_market_construction_enabled` and `culture_merges_enabled`; the runs above, later that day, were under a
last lobby of Disabled. So the owner applied Disabled in a lobby in between. That fits the runs' account and is not
evidence for the source either way.
No other recorded session switched a rule that carried an `apply_modifier` line: Base Construction's was the mod's
only one (added 2026-10-16, removed 2026-11-13).

**What the check needs.** The released 1.3.1 build, which still has the line and a base of 5: a playset that loads
it (the Workshop release) and not the local development copy, which no longer has the line. No harness, no console.
About ten minutes.

0. Close the game. Open `player/game_rules/presets.txt` in the user-data folder (the folder that holds `save games/`
   and `mod/`) and copy down the `setting={ … }` list of the preset named `LastAppliedRules`: at least its
   `free_market_construction_*` entry. Copy the whole file somewhere first if you like; nothing below writes it by
   hand.
1. Launch the game with the 1.3.1 playset. **New Game**, open **Game Rules**, set **Free Market Construction** to
   **Disabled**, leave the rest, pick any country and start. In the game, hover the construction figure in the top
   bar (or the construction panel's construction per week): its tooltip lists the sources of construction. Copy
   down the total and whether **Base Construction +5** is listed (it should be: the lobby just applied Disabled). Save under a name of your own, say `te1767`. Quit to the
   main menu.
2. **New Game** again, set **Free Market Construction** to **Enabled**, start (any country), and once the map is up
   quit to the main menu. Do not save.
3. Without closing the game, **Load** `te1767`. Hover the top bar's construction figure. Copy down the total and
   whether Base Construction is listed.
4. Quit to the desktop. Open `presets.txt` again and copy down `LastAppliedRules`' `free_market_construction_*`
   entry: it should now say `free_market_construction_enabled`. If it still says Disabled, step 2 did not apply its
   rules: redo steps 2 to 4.
5. Launch the game again with the same playset and load `te1767` from the main menu. Hover and copy down as in step 3.

**What each outcome means**, with `LastAppliedRules` at Enabled after step 2 (step 4):

| Step 3 (same session) | Step 5 (fresh launch) | Means |
|---|---|---|
| Base Construction gone, total 5 lower | gone | A main-menu load follows the last lobby as `-loadsave` did: inference (2) holds and loses "inferred". The source survives a restart, and `LastAppliedRules` is the one candidate recorded, so (1) is all but settled; the variant below proves it |
| gone | listed | Inference (1) does not hold as stated: after a fresh launch the main-menu load followed the save, so what step 3 followed was the running game's last lobby, not the file; and a fresh main-menu load differs from the harness's `-loadsave`, which followed the lobby. The lesson is rewritten to that |
| listed | listed | A main-menu load applies the save's setting: the harness's `-loadsave` differs. The lesson's heading stands (the harness's loads did not follow the save) and its first paragraph is corrected to that launch; players' reports then need another explanation |
| listed | gone | Unexpected: write down both readings and the presets lines, and say so on #1767 |

If step 1 does not list Base Construction, the 1.3.1 build is not the one loaded: check the playset. Write down
the presets lines from steps 0 and 4, the three readings, the date and the game's version on #1767.

### Readings, 2026-11-13

Run by the owner as Greece on Victoria 3 1.15.1, with a session reading the files. A watcher read `presets.txt`, the
Continue pointer and the `save games/` listing every two seconds from step 0 to the end.

**Build.** The run did not load the Workshop 1.3.1 copy that "What the check needs" asks for. It loaded the owner's
usual playset: Headlines, GDP Plotline Plus, Global Stats (GDP and POP) and the local `mod/Vic3TimelineExtended`
folder (the game's log of each launch, at 16:07:33 and 16:25:17). That folder held local `main` at `a0fd0c0bd`
(#1759), from before #1763, and its 1,164 `common/` and `events/` files all matched that commit. Its
`extra_game_rules.txt` was byte for byte the same as tag 1.3.1's, `apply_modifier` line included. Base Construction
was `country_construction_add = 5`, and no script in the folder added or removed the modifier, so the rule's line was
its only source. The folder did not change during the run. The owner judged a second run on the Workshop copy not
needed.

| Step | `LastAppliedRules` (`free_market_construction_*`) | Construction (top bar) | Base Construction +5 listed |
|---|---|---|---|
| 0. Game closed (16:02) | `disabled` (file of 10:53 that morning) | — | — |
| 1. New game from a lobby set to Disabled; saved as `te1767` (16:13:37) | `disabled`; the file was not written | 5 | Yes |
| 2. New game from a lobby set to Enabled, quit at the map | `enabled`, written at 16:13:56 as the game started (the only change: that entry) | — | — |
| 3. Same session: Load `te1767` from the main menu | `enabled` | 0 at load; 0.1 a week later, all of it from the Construction Site | No, at load or a week later |
| 4. Quit to the desktop | `enabled`, not written again | — | — |
| 5. Fresh launch (a new game process), Load `te1767` from the main menu | `enabled` | 0 at load; 0.1 a week later, from the site | No, at load or a week later |

The save `te1767` carries `free_market_construction_disabled` in both its `meta` and its `gamestate`, and no
`te_direct_construction_base_modifier`. It was a direct game throughout: its only construction was the site's.

**Outcome: the first row of the table above (gone, gone).** Inference (2) holds and is no longer an inference: a load
from the main menu applied the last lobby's setting (Enabled) to a save whose rule said Disabled, in the same session
and after a fresh launch, as the harness's `-loadsave` launches did. Inference (1) is all but settled, not proved. What
was applied survived a restart, so it is kept on disk. In the whole run `presets.txt` was written once, when the
Enabled lobby's game started, and a load wrote nothing. Searched after the run, no other file in the user-data folder
outside `save games/`, `logs/` and `mod/` names a `free_market_construction` setting. The variant below, which edits
the file by hand, was not run.

After the run `presets.txt` was copied back from the copy taken at step 0, and `cmp` found the two byte-identical
(sha256 `e0b4a91a…`). `te1767` was deleted, and the `save games/` listing (name, size, time) matched the one taken
before the run; the autosaves matched their copies byte for byte. The Continue pointer was left naming `te1767`.

**A further variant, to prove (1)**, if the owner wants it: with the game closed, copy
`presets.txt` aside, change only the `free_market_construction_*` entry of `LastAppliedRules` by hand to the other
setting, launch, load `te1767` from the main menu, read the tooltip, then put the copy back. Base Construction
following the edit proves the file is the source. It is a write to the owner's own settings file, which the harness
never makes; the risk is a mistake in the edit (what the game does with an entry it cannot read is not known), which
putting the copy back undoes.

## Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … direct_base_construction` | A direct game, once each time the game becomes one: a week after its first weekly pass | Every country that holds Base Construction has 10 construction a week or more (5 before #1768), and at most a tenth as many countries are still without it (new ones that have not had a weekly pulse) | `under_base` above 0: the engine does not sum the modifier's `country_construction_add` for a holder. `missing` large: a week of pulses left countries without it | `under_base`: read `modifier:country_construction_add` for one holder in the harness; if a script-added country modifier's construction is not summed, give the points through the Construction Site instead (a free level in the capital). `missing`: `te_direct_construction_on_weekly_pulse` is not reaching those countries; read `te_construction_market_pulse_events.3` for one |
| `TE_SELF_CHECK … construction_rule_switch` | Once for each time the rule is changed in a running game, the day the buildings follow it | `to=direct`: as many sites stand as the switch should have made (`expected`), no Construction Sector is left, standing or under construction, and no site carries the market's capacity modifier. `to=market`: as many sectors stand as `expected`, and at least one. `capped` is the number of states whose levels the switch cut to what the builder can make (200 to a site, 100 back to a sector); it does not change the verdict | `to=direct` with `sites` under `expected`: `create_building` refused a site, and that state's sector levels are lost; with `sectors_left` or `market_modifiers_left` above 0: `te_direct_construction_convert_state` did not replace the buildings. `to=market` with `sectors` under `expected`: `te_direct_construction_revert_state_site` removed a site and its sector was refused | `to=direct`: check that `remove_building` still removes a site and a sector in one effect (it did on 2026-11-13); otherwise remove in one daily pass and build in the next. `to=market`: `extended_timeline_build_specified_building_level` refused the sector (`create_building` checks its technology and may check `can_build_government`); build it under the `te_cm_placing_site` pattern, with a global the sector's permission accepts |

## Still to look at in a game

The harness reads values and takes screenshots; these need a player.

1. **Queue a site from the lens.** Direct game: production lens, Development, Construction Site, click a state. The
   level queues and builds; the state's site shows it. A state of a country without Urbanization can't take one.
2. **Two texts changed and not yet seen in the game.** The Disabled setting's description in the Game Rules window
   ends with "If the rule is changed in a running game, sectors and sites are converted within a day", whole inside
   its four lines (`test_game_rule_desc_length.py`), where it used to tell the player to build from the state view. The
   construction panel's Direct Construction intro says the sites are built "from the Development tab of the
   Production Lens or from a state's view". A raw `$key$` or `[concept…]` in either is a splice that did not resolve.
3. **The modifier a player sees.** The country's modifier list shows Base Construction (+10 construction), and the
   Nation tab's Economy section has a Construction row whose hover lists it. Neither appears in a market game.
4. **A market game switched to Disabled, as its player.** The day after: the construction panel shows the Direct
   Construction section, each state that had a Construction Sector has a Construction Site of the same level on the
   same tier, and the capital's site hires within a week. Construction Cost Scaling shows as Construction Goods
   Cost from the same day, for a country rich and fully employed enough to have any. Compare two countries of very
   different GDP per capita in the Nation tab's Construction row: each must show its own figure. The switch runs in
   one country's event, and until 2026-11-13 it set every country's modifier there, where the multiplier reads that
   one country; it now goes through a hidden event for each country (`te_construction_market_recalc_events.4`).
   Not run in the game.
5. **Back to the market.** The sectors return at the same level and tier, owned by the government. On the way to
   Disabled the opposite holds: a sector's levels become government Construction Site levels whoever owned them
   (investors, a company, a foreign owner), with no payment. The runs here were AI games of three months, and who owned their
   sectors was not read, so what a private owner loses in a late game has not been seen. Whether that needs a
   compensation pass is the owner's call. The way back makes government-owned sectors, so a switch to Disabled and
   back leaves every sector the government's, with its dividends (#1764; the player guide says so). The government
   purchase starts at 0 for a player, as in a new market game: set it in the panel. Watch the construction price for
   a year: the sites a direct game built beyond its sectors' old levels come back as extra supply.
6. **A game that was already switched before the fix, with site levels its player built since.** After the first day
   on this build: each state's site is its old sector's level plus the levels built on top of the market's own one.
7. **A sector whose owner has no Urbanization, at a switch to Disabled.** The conversion removes the sector and makes
   the site without testing the technology (the way back does test it). If `create_building` honours the site's
   `possible`, which needs Urbanization in a direct game, those levels are lost and the switch's self-check reads
   BROKEN with `sites` under `expected`. A sector can only reach such an owner by conquest. Not seen.
8. **A late game.** A state with more than 200 sector levels becomes a 200-level site (the cap of
   `te_construction_market_build_specified_level`), and a site of more than 100 levels becomes a 100-level sector on
   the way back (`extended_timeline_build_specified_building_level`). Say so if a real game gets there.
9. **Multiplayer.** Not run. Base Construction no longer depends on each machine's last lobby, which under the old
   line could have differed between host and client.
