# State pictures calibration probe

A logger for one observer game, kept out of the mod. It answers what the banner pictures' floors
should be (`docs/superpowers/specs/2026-11-10-state-pictures-design.md` §§ 5–7): city size by
rung, standard of living and what is expected, inequality, population growth, and each state's
building levels by kind.

## What it writes

Every five years from 1880, on each state's yearly pulse, one `debug.log` line:

    TE_SP_CAL;y=1900;owner=GBR;rung=0;size=3;city=...;pop=...;sol=...;exp=...;wsol=...;osol=...;oexp=...;gini=...;walk=...;walk_prev=...;prov=...;gdp=...;dev=...;poll=...;all=...;oil=...;mine=...;coal=...;heavy=...;manuf=...;tour=...;port=...;urb=...;state=...;date=...

| Field | Is |
|---|---|
| `rung` | how many of the city ladder's five technologies the owner has |
| `size`, `city`, `pop` | the stored size (0 none), the largest city's people, the state's people |
| `sol`, `exp` | the state's `average_sol` and `average_expected_sol` (whether a state reads the second is one of the questions: 0 with a load error if not) |
| `wsol` | the Demographics walk's `te_dg_sol` (-1 before the first walk) |
| `osol`, `oexp` | the owner's `average_sol` and `average_expected_sol` |
| `gini`, `walk`, `walk_prev`, `prov` | `te_dg_gini`, `te_dg_walk_pop`, `te_dg_walk_pop_prev`, `te_dg_provinces` (-1 where unset) |
| `gdp`, `dev` | the state's GDP and devastation (0 to 1) |
| `poll` | the state region's pollution in steps: 0 under 50, 1 from 50, 2 from 100, 3 from 150, 4 from 200 (of 255) |
| `all` … `urb` | building levels, subsistence left out: all, Oil Rigs, `bg_mining`, Coal Mines, `bg_heavy_industry`, `bg_manufacturing`, Tourism Industry, the Port, the Urban Center |

It stores nothing on a state; the sums pass through nine global variables (`te_p_*`).

## Running it

1. Deploy `main` to the game folder as usual (`scripts/deploy.sh`, from the main checkout).
2. Copy `overlay/` into the deployed mod folder and keep the list of files copied. A later
   `deploy.sh --apply` deletes them (its delete pass), which is also how to remove them; check no
   deploy watcher is running in between.
3. Start `follow_cal.py <out file>` before the game: the log keeps six generations of about
   half a megabyte and this probe fills one every few game years.
4. Launch through the harness (`python3 -m game_qa snapshot`, `launch`, `watch`, `restore`) with
   `-debug_mode -handsoff -run_until=<date>`: a new game, AI-only, that quits at the date.
5. Afterwards: remove the overlay's files from the game folder and read the lines.

A first short run past March 1836 with `te_probe_sp_cal_k_from` set to 1836 in the deployed copy
proves the line before a night is spent on it.
