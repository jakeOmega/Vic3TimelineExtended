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

**A side finding, fixed with it.** An AI country (Bornu) queued a Construction Sector on a new direct game's first
day, before the conversion closed the sector. Its construction never finished: five months later it still had 100
points left. The weekly pass now cancels a sector under construction in a direct game.

## Live results with the fix (2026-11-13)

Every run loaded the branch's changed files as a variant mod beside the deployed build. Greece and France were played;
a new game's rules were the owner's last applied (Free Market Construction Disabled).

| Run | What was read | Result |
|---|---|---|
| Market game of three months, rule switched to Disabled | The day after load | `TE_SELF_CHECK OK construction_rule_switch to=direct sites=378 sectors_left=0 market_modifiers_left=0`; all 291 countries hold Base Construction; no sector constructible, the site constructible |
| | Two weeks and four weeks on | France 14.4, then 42.4 construction a week (5.0 without the fix); the United Kingdom 62.4; 376 of 378 sites still standing (the AI had removed 23 in a week before the conversion set the guard's record); `TE_SELF_CHECK OK direct_base_construction holders=291 under_base=0 missing=0` |
| Direct game, rule switched to Enabled | The day after load | `TE_SELF_CHECK OK construction_rule_switch to=market sectors=381 sites_left=0`; France's capital has a level 29 sector on Iron-Frame Buildings |
| | Two weeks on | No country holds Base Construction and Greece reads 0 construction; 399 sectors, 357 sites, every site on the market method; the construction good's price is £1,616 |
| Direct game from before the fix, loaded with it | At load | No country has the modifier, Greece reads 0 (the rule's line is gone) |
| | Two weeks on | All 290 countries hold it; Greece 5.2 (5 and a fifth of a site level), so nothing is counted twice; the base self-check reads OK |
| New game under Disabled, made with the fix | Its second day | All 291 countries hold Base Construction and read 5 construction a week; 376 sites, no sector |
| | A month on | Greece's queued site level is 16 weeks from done on 5.4 points; France 42.6, the United Kingdom 62.6; 387 sites; the base self-check reads OK |
| Market game of three months, never switched (the default most players have) | At load | Nothing converted: 412 sites on the market method, 381 sectors; no country holds Base Construction, and the United Kingdom reads 43.55 construction a week where the old rule line gave it 48.55 |
| | Two weeks on | A Base Construction added to France by hand is gone (the market's weekly pulse removes it); 414 sites, 382 sectors, the sector constructible and the site not; no `construction_rule_switch` line and no construction error in `error.log` |
| Build lens, direct game | Production lens, Development tab | Construction Site is the first option |
| Build lens, market game | The same | No Construction Site (the lens hides a building whose `can_build_government` is false) |

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
| `TE_SELF_CHECK … direct_base_construction` | A direct game, once each time the game becomes one: a week after its first weekly pass | Every country that holds Base Construction has 5 construction a week or more, and at most a tenth as many countries are still without it (new ones that have not had a weekly pulse) | `under_base` above 0: the engine does not sum the modifier's `country_construction_add` for a holder. `missing` large: a week of pulses left countries without it | `under_base`: read `modifier:country_construction_add` for one holder in the harness; if a script-added country modifier's construction is not summed, give the points through the Construction Site instead (a free level in the capital). `missing`: `te_direct_construction_on_weekly_pulse` is not reaching those countries; read `te_construction_market_pulse_events.3` for one |
| `TE_SELF_CHECK … construction_rule_switch` | Once for each time the rule is changed in a running game, the day the buildings follow it | `to=direct`: no Construction Sector is left, standing or under construction, and no site carries the market's capacity modifier. `to=market`: sectors stand | `to=direct` with `sectors_left` or `market_modifiers_left` above 0: `te_direct_construction_convert_state` did not replace the buildings. `to=market` with `sectors=0`: `te_direct_construction_revert_state_site` made none, and nothing sells construction | `to=direct`: check that `remove_building` still removes a site and a sector in one effect (it did on 2026-11-13); otherwise remove in one daily pass and build in the next. `to=market`: `extended_timeline_build_specified_building_level` refused the sector (`create_building` checks its technology and may check `can_build_government`); build it under the `te_cm_placing_site` pattern, with a global the sector's permission accepts |

## Still to look at in a game

The harness reads values and takes screenshots; these need a player.

1. **Queue a site from the lens.** Direct game: production lens, Development, Construction Site, click a state. The
   level queues and builds; the state's site shows it. A state of a country without Urbanization can't take one.
2. **Two texts changed and not yet seen in the game.** The Disabled setting's description in the Game Rules window
   ends with what a change in a running game does, naming the Construction Sector and the Construction Site. The
   construction panel's Direct Construction intro says the sites are built "from the Development tab of the
   Production Lens or from a state's view". A raw `$key$` or `[concept…]` in either is a splice that did not resolve.
3. **The modifier a player sees.** The country's modifier list shows Base Construction (+5 construction), and the
   Nation tab's Economy section has a Construction row whose hover lists it. Neither appears in a market game.
4. **A market game switched to Disabled, as its player.** The day after: the construction panel shows the Direct
   Construction section, each state that had a Construction Sector has a Construction Site of the same level on the
   same tier, and the capital's site hires within a week. Construction Cost Scaling comes back as Construction Goods
   Cost at the next yearly pulse.
5. **Back to the market.** The sectors return at the same level and tier, owned by the government. On the way to
   Disabled the opposite holds: a sector's levels become government Construction Site levels whoever owned them
   (investors, a company, a foreign owner), with no payment. The runs here were AI games of three months, and who owned their
   sectors was not read, so what a private owner loses in a late game has not been seen. Whether that needs a
   compensation pass is the owner's call. The government
   purchase starts at 0 for a player, as in a new market game: set it in the panel. Watch the construction price for
   a year: the sites a direct game built beyond its sectors' old levels come back as extra supply.
6. **A game that was already switched before the fix, with site levels its player built since.** After the first day
   on this build: each state's site is its old sector's level plus the levels built on top of the market's own one.
7. **A late game.** A state with more than 200 sector levels becomes a 200-level site (the cap of
   `te_construction_market_build_specified_level`), and a site of more than 100 levels becomes a 100-level sector on
   the way back (`extended_timeline_build_specified_building_level`). Say so if a real game gets there.
8. **Multiplayer.** Not run. Base Construction no longer depends on each machine's last lobby, which under the old
   line could have differed between host and client.
