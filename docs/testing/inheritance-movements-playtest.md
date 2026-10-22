# Reform movements against entail: play-test list

The liberal, liberal-republican, national-liberal, radical, socialist and land-reformer movements gained inheritance
stances (2026-10-22, `ideology_modifications.py`; sets in `docs/systems/mod_systems.md` § Inheritance, "Ideology
stances"). Before them only the traditionalist movements held one, and they defend Primogeniture & Entail. The owner's
2019 observer save held 77 countries and 2.7 B people on it, against Britain and Japan in 1836. The change passed the
offline gate (`ideology_lawgroup_audit --strict`, `test_apply_ideologies.py`); what it does to the AI and to movements
only the game shows. In-game checks don't gate a merge (CLAUDE.md, "In-game checks").

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main` once merged).
- **Count the laws** in a save with `python3 scripts/analysis/demographics_harness.py wc SAVE`. It reads ordinary
  binary saves once #1101 is in, and its last table gives each inheritance law's countries.

| # | Check | What to look for | If it fails |
|---|---|---|---|
| 1 | The stances show | Britain, 1836: the Liberal Movement's tooltip lists Primogeniture & Entail among the laws it opposes and Freedom of Testation among those it supports; the Land Reform movement supports Customary Inheritance and Forced Heirship. | `common/ideologies/modified.txt` didn't load: look for the movement ideologies in `error.log`. |
| 2 | Radicalism | The same movements are a little more radical under Primogeniture than before (vanilla's `MOVEMENT_RADICALISM_FROM_ACTIVE_LAW_STANCE`, −0.05 times the stance on each law in force), and calmer after a country leaves it. Nothing near revolution from this alone. | Too radical: soften the liberal sets' Primogeniture line to `disapprove`. |
| 3 | An observer run to 2000 | Countries on Primogeniture at 1900, 1950 and 2000, against the 2019 save's 77 (Russia enacted it in 1841, the North American Union in 1940, China in 1972). Fewer, and reforms toward Freedom of Testation, Customary Inheritance or Forced Heirship. Countries made mid-game appear to take their parent's law (the 2019 save's got a spread of all four), so they follow the reforms. | Still most of the world: the next lever is an `ai_enact_weight_modifier` on the alternatives while a country holds Primogeniture. |
