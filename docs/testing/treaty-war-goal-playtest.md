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

## Emissions Reduction (2026-11-08)

The article was named Enforce Emissions Reduction, so its war goal read Enforce Enforce Emissions Reduction. It is
renamed Emissions Reduction, and so is its concept (`concept_emissions_reduction_treaty`), with the Global Warming
panel's links to it; the key `enforce_emissions_reduction` is unchanged. German and Spanish carry the same rename
(*Emissionsreduktion*, *Reducción de emisiones*).

| Check | Expect | If it fails |
|---|---|---|
| **The war goal's name.** Past 0.5 °C, with Intergovernmental Organizations, open a play against a country the article can bind (it holds Global Warming and has Clean Energy Technologies, Pollution Control and Modern Urban Planning) and add the goal. | The goal reads Enforce Emissions Reduction, and the treaty designer lists the article as Emissions Reduction. | Enforce Enforce Emissions Reduction: another loc file still defines `enforce_emissions_reduction` with the old text, and the later file wins (CLAUDE.md, "Editing conventions"). |
| **German and Spanish.** The same, with the game in German, then Spanish. | Vanilla's enforce wording around *Emissionsreduktion* or *Reducción de emisiones* reads as a sentence. | Vanilla's wording wants a verb or an article: change the two name records (`enforce_emissions_reduction`, `concept_emissions_reduction_treaty`) in `i18n/<language>/tm/`. |
