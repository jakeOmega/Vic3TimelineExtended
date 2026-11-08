# Treaty war goal play-test checklist

What the next play-test should look at in war goals that enforce a treaty article (2026-11-08). In-game checks do not
gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds
what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through with the
commit that fixed it.

Nothing here can be read from script, so there is no self-check line.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **A quick case.** Any play in which the AI presses an enforce goal: an 1860s great-power war draws in subjects and
  unrecognized minors, which the AI picks goals against. As a player, open a play against an Agrarian or Traditionalist
  country while running Laissez-Faire or Interventionism, research Stock Exchange, and add Enforce Privatization.

## Privatization and the modifier headings (2026-11-08)

The report: Britain, at war with France, pressed Enforce Enforce Privatization on Tahiti, a French subject. The tooltip
read "British modifiers: +200 Authority Cost, Force Privatization" and "Tahitian modifiers: +5% Prestige". The
article's script binds its source, the conceding side, and a war goal's target is that source (vanilla's treaty port:
China cedes in the Opium War; `scripting_best_practices.md` § "Directed Treaty Articles: the SOURCE Concedes"). The
headings are vanilla's `ARTICLE_DRAFT_WAR_GOAL_SOURCE_MODIFIERS_TITLE` and `_TARGET_`, which named the holder over the
source's modifiers; the mod now swaps them (`localization/english/replace/timeline_extended_override_l_english.yml`).
The article is renamed Privatization, so its war goal reads Enforce Privatization. The AI demands it only of a country
whose government owns at least `enforce_privatization_ai_min_levels` (10) levels outside the buildings it funds
(`enforce_privatization_ai_demand_weight`, `common/script_values/extra_script_values.txt`), weighted by the source's
GDP rank (1 for the top ten, 0.4 for 11th to 20th, 0.1 below), and a demander without
Laissez-Faire or Interventionism can no longer add the goal (`possible`).

| Check | Expect | If it fails |
|---|---|---|
| **Headings.** Hover any enforce goal whose article has source modifiers: Privatization, Forced Disarmament, Nuclear Program Freeze. | The conceding country's adjective heads Force Privatization (or the disarmament, or the freeze), and the holder's heads what it gains (prestige for Privatization). | Swapped back: the article's source is the holder after all. Revert the two override keys, then review every enforceable mod article with a `source_modifier` (`docs/testing/nuclear-treaty-ai-playtest.md`, "Which side is frozen", asks the same). |
| **Which side privatizes.** Win a war holding Enforce Privatization, then open both countries' modifiers. | The loser carries Force Privatization and the +200 authority cost; the winner has +5% prestige. | The war goal binds the holder: as above, and the article's direction needs reviewing with every other enforceable one. |
| **No empty demands.** Watch AI plays and wars for a while (observer, or a save where great powers fight). | Enforce Privatization appears only against countries with real state-owned industry, never against an unrecognized minor or a tiny subject, and mostly against large economies (Qing, Russia, an Agrarian great power). | The engine ignores `wargoal_score_multiplier` for goals added to a running play: gate the demander's `inherent_accept_score` with the same weight (a large negative term when it is 0), since the war-goal score is built on it. |
| **Still demanded where it matters.** A Laissez-Faire or Interventionist AI at war with an Agrarian or Cooperative country among the ten largest economies that owns state industry. | The AI sometimes adds the goal. | `scope:source_country` isn't bound where the engine reads the weight, so it is 0 for everyone. Drop `proposal_weight` and `wargoal_score_multiplier` (the old behavior) and keep the `possible` test. The nuclear articles read the same scope, so check them too. |
| **GDP rank reads.** Same as above against a large economy. | The goal appears against a top-ten economy noticeably more often than against a mid-sized one. | `gdp_ranking` reads 0, or counts from the other end: a top economy then gets 0.1. Weight by `country_rank` instead (`rank_value:great_power` 1, `major_power` 0.4). |
| **Non-capitalist demander.** As a country with Agrarianism or Command Economy, open a play against a Traditionalist country. | Enforce Privatization isn't offered. | `possible` isn't read for war goals here; the `can_ratify` test still stops a treaty. |

## AI demand weights for the other enforceable articles (2026-11-08)

Privatization's fix, extended: every enforceable article now gives the AI a weight that is 0 where the demand buys
nothing, read by `proposal_weight` and `wargoal_score_multiplier`, or carries a reviewed exemption
(`docs/systems/mod_systems/treaties.md`, "AI demand weights", lists each with its test). An article that names a company
or state reads the chosen one (`scope:article.input_company` / `.input_state`) and, with none bound, asks whether any of
the source's would do. Forced Disarmament, Free Port Concession and Enforce Emissions Reduction are then weighted by the
source's GDP rank, as Privatization is (`treaty_ai_demand_economy_factor`), so the "GDP rank reads" check above covers
them too. Minority Protection's protector bloc, Religious Mission Rights' missionary bloc and Excavation
Concession's Romanticism test moved into `possible`, and Seize Company's company list leaves out any type the receiver
already has (`company_valid_trigger`).

| Check | Expect | If it fails |
|---|---|---|
| **No empty demands.** Watch AI plays and wars for a while (observer, or a save where great powers fight), and hover each enforce goal. | No Forced Disarmament of a country with under 10 battalions and flotillas and no arms industry; no Free Port Concession in a state without a port or in the demander's own market; no Religious Mission Rights in a state of the missionary's faith; no Minority Protection where the protector's people and faith aren't discriminated; no Seize or Disband Company of a company under 5 levels; no Enforce Emissions Reduction of a country under 1% of world emissions; no Imposed Currency Peg of a pegged country, nor Debt Receivership of one already under a receivership. Forced Disarmament, Free Port and Emissions Reduction fall mostly on large economies. | As Privatization's "No empty demands": the engine ignores `wargoal_score_multiplier` for goals added to a running play, and the fix is a large negative `inherent_accept_score` term for the demander when the weight is 0. |
| **The chosen input is read.** In the same run, note the company or state each AI-pressed Seize, Disband, Minority Protection, Free Port, Mission Rights or Demilitarized Zone goal names. | The named input passes the test itself (a company of 5 levels or more, a port state, a state with other-faith people), not just some other company or state of the source. | `scope:article.input_*` is unbound where the engine reads the weight, so only the any-input walk decides, and a worthless input in a country with a worthy one gets through. Move the input test into the article's `inherent_accept_score` for the demander, which binds `scope:article`. |
| **Still demanded where it matters.** A great-power AI at war with a rival that has a large army, or with an Agrarian neighbor whose border state holds Barracks. | The AI sometimes adds Forced Disarmament or a Demilitarized Zone, as before. | `scope:source_country` or `scope:target_country` isn't bound where the engine reads the weights, so they are 0 for everyone. The nuclear and Privatization weights read the same scopes: drop the fields from every article together and keep the `possible` tests. |
| **Bloc and tech gates in a war goal.** As a player outside any Cultural or Religious bloc, open a play and look for Minority Protection and Religious Mission Rights among the enforce goals; outside a Religious bloc, for Mission Rights alone; without Romanticism, for Excavation Concession against a country with a buried site. Then the same in a treaty draft. | Not offered in the play. In the draft the article shows as unavailable, with "The protecting power belongs to a Power Bloc with the Cultural or Religious identity" (or the missionary's or the sponsor's line), the text reading cleanly. | Offered in the play: `possible` isn't read for war goals here, and `can_ratify` still stops a treaty. A raw key or a broken line: the tooltip's text needs a loc fix. |
| **Seize Company's list.** Draft a treaty, then open a play, against a country that owns a company whose type you already have and one whose type you don't, and add Seize Company. | The list offers only the type you don't have, in both. Disband Company still lists both. | Empty for every country: `scope:other_country` isn't the target in `company_valid_trigger` as the 1.14.4 doc says; drop the line and keep `can_ratify`'s SEIZE_COMPANY_ALREADY_HAS and the AI weight. Both listed in the play: the war goal's picker doesn't read the valid trigger, so a player can still seize a company the holder already has (the source loses it, the holder gains nothing). |
