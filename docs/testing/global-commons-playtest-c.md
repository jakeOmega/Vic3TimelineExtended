# Global Commons: launch windows, play-test checklist (agent C)

What the next play-test should look at for Solar System Colonization's launch windows (spec
`docs/superpowers/specs/2026-10-16-global-commons-design.md` § 5 and § 8). In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): the branch lands on the offline gate (`test_launch_windows.py`, the
audits) and this is what only the game can show. A fixed item is struck through with the commit that fixed it. The integrator
merges this file with the other four agents' lists.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work". Space Race rule on.
- **Reach Solar System Colonization**: a great or major power with the Moon Base and Mars Landing done, Directed Energy Weapons
  and the Solar Colonization method on its Space Program. `event te_debug_space_race.1` option b finishes running milestones;
  research the rest from the console.
- **Console.** `event te_debug_launch_windows.1`: a stages two and a half colony fleets (the bar at 2.5 × the goal); b writes
  every body's cached window, the date's own answer, the premium and our cost to `debug.log` (`TE_LAUNCH_WINDOWS` lines); c lets
  the self-checks log again.
- **Logs.** Read `debug.log`; grep `TE_SELF_CHECK` and `TE_LAUNCH_WINDOWS`.
- **Reference.** `docs/engine/launch_windows_report.md` lists every body's premium curve, the Mars windows of 2030–2060 and the
  historical launches the method is checked against. Mars windows: 2030.12–2031.02, 2033.02–2033.04, 2035.06–2035.08,
  2037.07–2037.09, 2039.08–2039.10, 2041.09–2041.11, 2043.10–2043.12, 2045.11–2046.01, 2048.01–2048.03.

## Self-checks

Logged once a game each. Nothing logged means the premise never came up (no chemical-only colony founded, or nothing ever waited).

| Line | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK/BROKEN window_gate` | the first colony founded by a country with neither Asteroid Mining nor Muon-Catalyzed Fusion Reactors after a closed window has held its full bar at least once (OK), or any such colony founded while its body's window is closed (BROKEN) | closed windows held the bar and the fleet left in its window: the global cache (`sr_window_is_open_<body>`) agreed with the date's own answer (`sr_window_open_<body>`, the generated chain) and the draw read it | a colony was founded outside its window: the cache was stale or wrong (`cache_month` against `month`, `cached_wait` against `months_to_next`), or a site's draw trigger didn't hold | if `cache_month` lags `month`, the global pulse reads last month's index: make `sr_launch_window_cache_current` the only path (refresh from the entry's pulse every month) or compare against `te_history_month_index` directly in `sr_launch_departs_free`; if the cache is current, read the site's `trigger` in `sr_establish_colony_effect` |
| `TE_SELF_CHECK OK window_gate_paid` | the first off-window launch by a country with Asteroid Mining | `premium_cached` = `premium_date`, and `spent` = `goal` × (1 + premium) | the two premiums differ (stale cache) or `spent` is another figure | as above for the cache; for `spent`, `sr_launch_fleet_cost` is read before the colony effect in `sr_launch_month` |

## Checklist

1. **The panel before a window.** With the bar below the goal: no Staged in Orbit line; Mission Control's Next Windows lists
   Mars and the five asteroids with "window in N months" (or "window open"), in that order, and nothing for a world already
   claimed. With Muon-Catalyzed Fusion Reactors it reads one line, "Fusion drives: no launch windows". The months agree with the
   report (Mars) and with option b's `wait_by_date`.
2. **Fleets staged in orbit departing when the window opens.** Option a, with every stage-1 window closed (option b says which):
   the overview shows Staged in Orbit: 2.5 fleets, its hover lists each destination's next window, one fleet a month while open,
   and what Asteroid Mining and fusion drives change. Nothing is founded while every window is closed. When the first window
   opens, one colony is founded that month and the bar drops by one goal; the next month another, while the window stays open
   and a goal is left; what is left waits. Founded worlds belong to the open body only.
3. **A setback while fleets are staged.** With 2.5 fleets staged, fire a setback (`event te_debug_space_race.1` option j while
   solar colonization is the most advanced running milestone, or wait for the roll): the bar loses 25% (Ambitious) or 15%
   (Safe, Standard) of one goal, plus any flat amount, not of the whole bar. The option's tooltip says so.
4. **An off-window launch after Asteroid Mining.** Research Asteroid Mining, Standard approach, every stage-1 window closed and
   staged progress above one goal. Next Windows gives each closed destination today's premium and the verdict, months saved (to
   the stage's next window, option b's `stage_wait`) against months cost (goal × premium ÷ pace). A colony is founded off-window
   exactly when a line says "our approach would launch now", at the cheapest such destination, and the bar drops by goal × (1 +
   its premium). The month after a Mars window closes, Mars is about +43%; with the next asteroid window more than a year away,
   a pace above about 8 a month launches there on Standard (about 4 on Ambitious). On Safe every line says the Safe approach
   waits, and nothing launches off-window.
5. **Fusion drives end the windows.** With Muon-Catalyzed Fusion Reactors a full bar founds a colony in its first month, any
   month, at the plain goal.
6. **Stage change with fleets staged.** Let a rival take the stage's last world while fleets are staged: the staged progress
   carries into the next stage, whose goal is higher, and leaves in that stage's windows. When the last of the 34 worlds goes,
   any staged progress is gone and the entry finishes.
7. **Mercury.** In stage 3 with Mercury unclaimed and Saturn closed, a full bar founds Mercury at once; Saturn's sites wait for
   their window.
8. **The AI.** An AI power in the top three running colonization founds colonies only in windows before Asteroid Mining (check
   its colony months against option b's log or the report); its funding doesn't drop to zero while a bar waits.
9. **Old save.** Load a save from before the branch with colonization running: the panel shows no destination lines until the
   1st of the next month (the cache is built then), and nothing errors in `error.log` about `sr_window_*` globals.
10. **Optional flavour skipped.** The colony events don't mention the arrival month (spec § 5.3's "the fleet reached Mars in
    November"); nothing to check.

## Engine facts this rests on, unverified

- The global `on_monthly_pulse` reads the new month's `te_history_month_index` (inferred in `scripting_best_practices.md`);
  if not, the entry's own refresh still corrects the cache before any launch (`sr_launch_windows_ensure_cache`). The
  `window_gate` self-check reads the date directly and would show a stale cache.
- `floor = yes` and two-decimal literals (`24395.26`) in script values decode exactly; `test_launch_windows.py` reads the
  generated chains back for every month 1900–2136 with the same arithmetic.
- `ExecuteTooltip` as a textbox's text, with `custom_tooltip_no_bullet` lines reading `THIS.GetCountry.MakeScope.ScriptValue`
  (the Cultural Hegemony leaderboard does the former; the line format is the UN chamber's).
