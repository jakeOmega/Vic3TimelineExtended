# Protected Class and women in office: play-test list

`common/character_interactions/te_vanilla_women_in_office.txt` restates vanilla's Grant Leadership and both Grant
Command interactions with `REPLACE:` so that Protected Class, like Women's Suffrage, lets a woman lead an interest
group or take command. The copies were rebuilt from the committed `vanilla_parsed/` snapshot (1.15.2), not from the
installed game, and passed the offline gate only (`test_women_in_office_interactions.py`, the audits). In-game checks
don't gate a merge (CLAUDE.md, "In-game checks"); work through these the next time the game is up.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main` once merged).
- **A save** with a country under Protected Class that has a female agitator, and a female ruler if one is at hand.
- **Logs.** Read `debug.log` first, then `error.log`. Search both for `te_vanilla_women_in_office.txt`.

| # | Check | What to look for | If it fails |
|---|---|---|---|
| 1 | Grant Leadership | Hover Grant Leadership on a female agitator. "At least one of:" lists three lines: not a woman, any variant of Women's Suffrage, and Protected Class, and the Protected Class line is met. The interaction works once the group is pressured. | Only two lines: vanilla's copy is still loaded, so the `REPLACE:` didn't apply. Look for `inject/replace to a non-existing entry` naming the file. |
| 2 | Grant Command | The same three lines on Grant Command for a female agitator, and on a female ruler's Grant Command. | As check 1. |
| 3 | Unchanged elsewhere | Under Women's Suffrage, and for male characters, all three behave as in vanilla: the same requirements, cooldowns and sounds. | Diff the file against vanilla's text in the installed game: the snapshot may have lost something the parse can't hold. |
| 4 | Load-time errors | No line naming `te_vanilla_women_in_office.txt` in either log, including `Event target link 'ruler'` from a rulerless country. | Fix the named line; a `ruler` line means the AI weight's guard isn't holding. |
