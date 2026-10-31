# Nuclear treaty AI: play-test

The AI demands a Nuclear Program Freeze or a Nuclear Disarmament only of a country the article would stop (2026-10-16). Before this, an AI India pressed a freeze as a secondary war goal against insignificant Mekong, which had the Nuclear Weapons technology but no standing to build. The gates are `nuclear_program_freeze_matters` and `nuclear_disarmament_matters` (`common/scripted_triggers/nuke_triggers.txt`), and the weights the articles use as `proposal_weight` and `wargoal_score_multiplier` (`nuclear_program_pause_ai_demand_weight`, `nuclear_disarmament_ai_demand_weight`, `common/script_values/extra_script_values.txt`). Design notes: `docs/systems/mod_systems/nuclear.md` § Nuclear Program Pause.

Nothing here can be read from script, so there is no self-check line.

## Checks

| Check | Expected | Wrong means | Fallback |
|---|---|---|---|
| **No freeze of a country that can't build.** Late game, watch AI plays (observer, or a save where AI great powers are in plays) against insignificant or minor powers that have researched Nuclear Weapons. | Neither *Enforce Nuclear Program Freeze* nor *Enforce Nuclear Disarmament* appears among the AI's demands on such a country, unless the world believes it armed (Nuclear Power), which allows disarmament. | The engine ignores `wargoal_score_multiplier` for war goals added to a running play, or reads it from another scope. | Gate the requester's whole acceptance in `inherent_accept_score` as well (a large negative term when the source doesn't matter), since the war-goal score is built on it. |
| **Still demanded where it matters.** An AI great power whose rival is a great power funding a program, both at war or in a play. | The AI sometimes adds a freeze or disarmament demand against the rival, as before. | `scope:source_country` isn't bound in `wargoal_score_multiplier` or `proposal_weight`, so the weight reads 0 for everyone and the AI never demands either article. | Drop the two fields from the articles (the old behavior) and keep only the acceptance gates. |
| **Which side is frozen.** Enforce a freeze in a war you win as the holder, against a country with a program. | After peace, the loser's Nuclear Weapons panel shows funding held at zero (the freeze), and yours does not. | The war goal makes the holder concede: the article's source is the holder, not the loser. | Every enforceable mod article with a `source_modifier` needs its direction reviewed (`scripting_best_practices.md` § "Directed Treaty Articles: the SOURCE Concedes"). |

The war goal's tooltip heads the freeze with the holder's name ("Indian modifiers: Nuclear Program Freeze" on India's goal against Mekong). That heading is vanilla's `ARTICLE_DRAFT_WAR_GOAL_SOURCE_MODIFIERS_TITLE`, which names the war goal's holder over the article's source modifiers. The third check settles whether the label or the article direction is wrong.
