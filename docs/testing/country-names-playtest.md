# Country names play-test checklist

What the next play-test should look at in the dynamic names of vanilla countries the mod renames
(`common/dynamic_country_names/te_vanilla_country_names.txt`). In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can
show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The country's name in the top bar, the Countries list and the diplomacy panel.
- **Logs.** Read `debug.log`, not `error.log`. Search it for `Duplicated key USA` and `dyn_c_`.

## USA (2026-10-22)

The USA block is a `REPLACE:USA` over vanilla's whole block, the first time the mod has overridden a vanilla tag's
dynamic names. The parser reads the file and every `name` resolves in loc, but the mod state server does not load this
database, so whether the engine honors `REPLACE:` here is only visible in the game.

| Check | Expect | If it fails |
|---|---|---|
| **The override takes.** Start a game as any country and read the USA's name (Countries list). | "United States of America" (a presidential republic). `debug.log` has no `Duplicated key USA`. | A duplicate-key line, or a vanilla name ("United Sovereign Archduchy", "North American Technate") under another government, means `REPLACE:` is not honored for this database. Fall back to shipping a full copy of vanilla's `00_dynamic_country_names.txt` with the USA block edited, under the same file name (re-sync it on every vanilla bump). |
| **One name per government.** Give the USA each Governance Principles law in turn (a save from another run that holds the law is fastest): Parliamentary Republic, Council Republic, a monarchy, Theocracy, Corporate State, Neocameralism. | United States of America; Workers' Commonwealth of America; Imperial Union of America; New Canaan; National Estates of America; Associated Trusts of America. | A different name means two entries matched: both are priority 0, so the first in file order wins; check the law's group and variants. |
| **Technocracy splits only the republic.** Presidential or parliamentary republic plus Technocracy; then Council Republic plus Technocracy. | American Technate; Workers' Commonwealth of America. | The second reading "American Technate" means the technocracy entry matched a council republic. |
| **Unmatched laws.** Collective Governance. | "America" (the bare `USA` loc key), as under vanilla's block. | Any other name means a trigger matched more than it should. |
| **Territory.** Reduce the USA to the District of Columbia alone, then to the District and one state. Rare; only if a collapse run reaches it. | Federal District of Columbia; State and District of America. Both beat the government name. | The triggers are vanilla's (the second also requires the District), so a miss points at the second entry's added District condition. |
