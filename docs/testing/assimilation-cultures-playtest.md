# Assimilation cultures play-test checklist

What the next play-test should look at for the assimilation cultures. In-game checks do not gate a merge: a PR lands on the offline gate (CI, the audits, the tests) and adds here what only the game can show.

Design: `docs/superpowers/specs/2026-11-25-assimilation-cultures-design.md`. Mechanics: `docs/systems/mod_systems/assimilation_cultures.md`.

## How to run

- **Deploy** per `docs/guides/git_workflow.md`, "Play-testing unmerged work". Check the playset has no Workshop copy of the mod.
- **The rule.** `assimilation_cultures_rule`: Unrestricted (the default), Hybrid Cultures or None. It can be changed mid-game from the screen that changes country.
- **A new game** for Hybrid Cultures: a game begun before the hybrid cultures were added has no object for them and plays as Unrestricted whatever the rule says.
- **Where to look.** The pass runs once a year for each country, on that country's own yearly pulse, in incorporated states. The United States (Yankee and Dixie, with African-heritage pops), Brazil, and any colonial power with an incorporated colony show it within a few years. Paraguay (Platinean and Guarani primary cultures) is the two-heritage case.
- **Logs.** Read `debug.log`, not `error.log`, and grep it for `TE_SELF_CHECK`. `debug.log` rolls over at 512 KB: copy the lines out as they appear.

## Self-checks

Two checks, each a once-a-game line behind a latch global, both TEMPORARY: `common/scripted_effects/te_assimilation_culture_selfcheck_effects.txt`, the on_action `te_hc_chk_define_on_action`, and one call in `te_hc_convert_pop`.

| Line | Means | Fallback if BROKEN |
|---|---|---|
| `TE_SELF_CHECK … hc_define_blocks` | From 30 days after the first monthly pulse, a walk of every incorporated state's pops that the engine is assimilating. OK: at least one pop that shares a heritage group with a primary culture of its country is assimilating (`assimilating_same_group`, so the trigger is known to read), and none that shares no group is (`assimilating_other_group` 0). BROKEN: some of the second kind are. `of_those_with_kin_in_state` counts those whose state holds another culture of their own heritage group: the engine's target is the most accepted culture in the state, which need not be primary, so a BROKEN where the two figures are equal may be only assimilation within the group. `NOT_JUDGED` after three pulses with nobody of the first kind assimilating. | The define does not do what vanilla's comment says. Set the rule's default aside: ship with the pass switched off and no hybrids used until the define's behavior is read by hand (the pop panel of a pop of another heritage group in an incorporated state outside its homeland). |
| `TE_SELF_CHECK … hc_rate_inputs` | At the first pop the pass converts whose country carries an assimilation line of its own (`country_part` not 0). OK: the state's read of `state_assimilation_mult` from pop scope is not 0 either (`state_assimilation`), the yearly rate is between 0 and 0.5, and the country's `country_allow_assimilation_full_acceptance_bool` reads yes. No line after a few years under Hybrid Cultures or Unrestricted: the country-scope read of a `state_` modifier gives 0 everywhere, and the first half rests on the 2026-10-08 probe alone (`scripting_best_practices.md`, "Reading Pops, Buildings and Wars for a Yearly Model"). | Read the country's sum and add the state's own modifiers; a `has_law` ladder over the Minority Rights laws in place of the status switches. |

## What only the game shows

| Check | How | Expect |
|---|---|---|
| The hybrids' names | The culture panel of a hybrid pop; a few with an override word (Turkic, Oromo, Great Lakes Bantu) and a few spliced | "Anglophone African", "Turkic European"; no raw key, no `$` |
| The hybrids' portraits and name lists | A generated character of a hybrid culture (an agitator, a general) | The heritage group's look, the language's names |
| The language step | Under Hybrid Cultures, a pop of another heritage group in an incorporated state outside its homeland, a year apart | A hybrid pop of the host's language appears and the source pop shrinks by about the yearly rate (2.4% with no modifiers) |
| A later pass merges into the hybrid pop an earlier one made | The pop count of a state over two passes | No second hybrid pop of the same type, religion and workplace (Culture Merges' pending `cm_conversion_merges_pops` asks the same of the engine) |
| The local culture | The United States: a Yoruba or other African-heritage immigrant pop in New York and in Georgia | Afro-American in both. Britain after taking one Southern state: Afro-American there, Anglophone African in London |
| The host in a country with primary cultures of two heritage groups | Paraguay's first decade | European pops are left to the engine; a pop of a third group takes the language of the state's larger primary culture |
| The host where no primary culture lives | A newly incorporated colony | Pops convert toward the capital's primary culture |
| Unincorporated states | A same-heritage-group pop in an unincorporated state outside its homeland: does the engine assimilate it at all, and how fast? | The pass skips these states. If the engine assimilates there, slowly, Unrestricted is slower than vanilla in colonies: record the engine's rate here |
| The heritage step | A Hybrid Cultures game with Licensed Modification, then Morphological Freedom, enacted by console | Hybrid pops and other pops that speak the host's language join the host: at half the language step's pace, then at the same pace |
| Ancestral Citizenship | Enact it under each setting | No pop joins the host; under Hybrid Cultures hybrids still form |
| The law tooltips | Each Bodily Autonomy law and Ancestral Citizenship | "+50% Assimilation Across Heritages", "+100%"; "Pops Never Join a Culture of Another Heritage Group" |
| Unrestricted against the base game | The share of a primary culture in an immigrant state over 20 years, against the same game on a build without the define | Close. The engine's `country_assimilation_delta_threshold_add` (Affirmative Action carries −100 of it) is not imitated: record what it does to a fully accepted pop |
| A rule change mid-game | Hybrid Cultures to Unrestricted, to None, and back | To Unrestricted: hybrid pops join the host at the yearly rate. To None: they stay. Back: the language step resumes. Nothing in the log |
| A save from before the build | A 1.3.x save, the rule set to Hybrid Cultures from the change-country screen | It plays as Unrestricted; no `Culture (-1)` line, no hybrid named in the log |
| The engine assimilating into a hybrid | A hybrid at Full Acceptance beside a non-hybrid pop of its own heritage group | Harmless either way; record whether it happens |
| Load time and the monthly tick | Launch to menu and a month of 1836 and of a late save, against `main` | 584 more cultures: no visible change. `ticktask_timings.csv` if it is visible |
| Mod files that iterate cultures | The Culture Merges list's row (24 mod files): any that divides by, averages over or lists cultures with no people | Unchanged by 584 more empty cultures |
