# Play-test: direct construction (Free Market Construction off), 2026-11-13

Players reported that Base Construction did not work right with the Free Market Construction rule off: for some not at
all, for some not after loading a save. Two faults were found and fixed, both read in the running game through the QA
harness (`python3 -m game_qa`), and the build lens now offers the Construction Site. System reference:
`docs/systems/mod_systems/construction.md` § "Free Market Construction off"; the tests are
`test_construction_rule_switch.py`.

## What was wrong

**1. Base Construction followed the player's last lobby, not the save.** The Disabled setting applied the modifier with
`apply_modifier = all:te_direct_construction_base_modifier`. The base game never uses that line. The engine applies it
by the rules the player last applied in a lobby on their machine (`player/game_rules/presets.txt`,
`LastAppliedRules`), whatever save is loaded:

| Save loaded | Its rules (`has_game_rule`) | The lobby's last applied rules | What the engine applied |
|---|---|---|---|
| A market game, never switched | Free Market Construction Enabled | Disabled | The Disabled setting's modifier: a marker of 11 on Disabled read 11, a marker of 3 on Enabled read 0, and every country had 5 construction a week |
| The same, with culture merges switched off in the save | Enabled; culture merges disabled | Disabled; culture merges enabled | Markers 1, 10, 100, 1,000 and 10,000 on the five construction settings summed to 10,000 (Disabled alone); markers 1 and 10 on the two culture-merge settings read 1 (enabled alone) |
| The owner's own played save, loaded straight into play | Enabled | Disabled | A marker on every setting read 7 for the player and for two AI countries, so the rule's line is read at load on that path too |

**What was read and what is inferred.** Read directly, in two rules: the modifier the engine applied was not the
one of the save's setting, and `has_game_rule` and the setting's production-method flags did follow the save. Inferred:
that `LastAppliedRules` is the source. It named the applied setting both times (Disabled, and culture merges enabled,
neither of them the default nor both the last setting defined), and nothing else on the machine did; but the harness
never writes that file, so it could not be flipped to watch the modifier follow. Also inferred: that a load from the
main menu behaves as the harness's `-loadsave` launch does. One check by hand settles both, on the released 1.3.1
build: start a game with the rule Disabled and save it; open New Game, set the rule to Enabled, start and quit; load the
save. If the construction tooltip has lost Base Construction, the source is the last lobby. Either way the line could
not be relied on, and script does not use it any more.

So a player who starts a Disabled game has the 5 points while Disabled is what they last set up. Once they apply other
rules in any lobby, that game loses its Base Construction at the next load, and a market game loaded after a Disabled
lobby gains 5 points it should not have. The save holds no trace of the modifier, and `has_modifier` never saw it.
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
