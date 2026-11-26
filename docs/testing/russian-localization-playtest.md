# Russian localization play-test checklist

What the next play-test in Russian should look at. The Russian is machine-translated (`i18n/russian/`, built into the game's `localization/russian/` at deploy time), and nobody on the team reads Russian, so these checks look for what breaks, not for style. In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`). The deploy prints how many Russian keys it shipped translated.
- **Language.** Set the game to Русский in the launcher's settings.
- **Logs.** Read `debug.log`, not `error.log`. Compare against an English session of the same length: search for `Failed parsing localized text`, `Missing loc` and `localization`.

## The first full translation (2026-11-15)

The run had no game install, so the base game's Russian terms were not looked up: the brief's table (`i18n/russian/BRIEF.md` § Terminology) and `terms.json` hold the renderings the agents used for the base game's own terms (pop types, interest groups, power bloc, authority, infamy …). The first checks compare those with what vanilla's own Russian says.

| Check | Expect | If it fails |
|---|---|---|
| **No raw keys.** Open the mod's journal entries (Strategic Reserve, Banking, United Nations, Space Race), the Nation tab, the budget panel and a few mod events; hover their modifiers. | Russian everywhere, with English only for a line added since the last pass. | A raw key: the English key itself is missing, or the deploy didn't build `localization/russian/`. English on a line the TM has: its English changed since; `translate_loc.py --language russian status` counts those. |
| **Base-game terms.** Compare the mod's words for pops, interest groups and their pop types, power blocs, authority, infamy, subjects, states and journal entries with vanilla's own Russian on the same screen (the Politics panel, the power bloc panel, a vanilla tooltip). | The same word in both. | Where vanilla says otherwise, change the entry in `i18n/russian/terms.json` and the brief's table, then run `translate_loc.py --language russian check-terms` and `prepare-fixes` (`i18n/README.md` § Running a translation pass) to bring the lines into line. |
| **Concept links.** Hover the underlined terms in a mod tooltip; most carry an inflected display text (`Concept('concept_x', 'легитимности')`) or `|l`. | Each opens its concept, and its word reads in the right case. | A plain-text term: the line lost its link, which merge should have rejected; report the key. |
| **Country names.** An event or tooltip that names another country (a diplomatic play, a power bloc invitation, a war). | The name in the nominative after a noun that carries the case («стране Франция», «правительство страны Франция»), never a raw `GetAltName`. | Report the key. Merge rejects `GetAltName` for Russian; a later pass with the game files can take up vanilla's declined forms (`GetAltName('RU_CL_RP')` and the rest, issue #566), after checking which forms vanilla defines for every tag and for the mod's formables. |
| **Panels fit.** The Banking dashboard, the Demographics tab, the budget panel's tabs, the UN panel and the Strategic Reserve rows. | Labels fit their boxes. Russian runs about a fifth longer than English. | Shorten the label's `"ru"` in `i18n/russian/tm/<file>.json`, keeping its `"en"`. |
| **Quotes and numbers.** An event that quotes someone, and a tooltip with a figure over 999 in its prose. | «…» quotation marks, with „…“ inside; 1 000 with no line break inside it, decimals with a comma (2,5). | A stray `"` cuts the line short: find it in the TM and replace it with « or ». |
| **Cyrillic in custom fonts.** The mod's own panels that set a font (the Banking dashboard, `docs/testing/banking-font-playtest.md`). | Cyrillic renders, no boxes or blanks. | A font without Cyrillic glyphs: the panel needs vanilla's default font for this language. |
| **debug.log.** After a year of play. | No loc errors the English session doesn't have. | Fix the line in the TM. |

## The eleventh update pass (2026-11-26)

Run with no game install, so the hybrid cultures' language words and the space race's new words were not checked against vanilla's Russian.

| Check | Expect | If it fails |
|---|---|---|
| **Hybrid culture names.** Under the Assimilation Across Heritages rule's Hybrid Cultures setting, a pop that takes up another heritage's language: hover its culture. The mod writes some names itself («Бирманская $heritage_group_african$», «Банту Великих озёр …»), and the rest insert vanilla's own language and heritage-group names (`$language_akan$ $heritage_group_central_asian$`). | Both kinds read alike: the language word, then the heritage group, in the same case and gender. | Change the mod-written names in `i18n/russian/tm/te_hybrid_cultures_generated.json` to vanilla's form. Each language word repeats in all nine of its heritage-group names (`hc_<language>_<group>`), so swap it in every one, by a script-written correction chunk merged like any other (`i18n/README.md` § Running a translation pass, step 6). |
| **A world's "room".** The Space Race tab's Extraplanetary Bases tooltips and the colony pages. | One word for the room a world has for base levels and for Resort Colony levels. | The memory calls the bases' room «зал» (hall) in 12 lines and the resorts' «Место для курортных колоний»; settle one and correct the other lines with a correction chunk. |
