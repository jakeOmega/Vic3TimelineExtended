# Spanish localization play-test checklist

What the next play-test in Spanish should look at. The Spanish is machine-translated (`i18n/spanish/`, built into the game's `localization/spanish/` at deploy time), and nobody on the team reads Spanish, so these checks look for what breaks, not for style. In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`). The deploy prints how many Spanish keys it shipped translated.
- **Language.** Set the game to Español in the launcher's settings.
- **Logs.** Read `debug.log`, not `error.log`. Compare against an English session of the same length: search for `Failed parsing localized text`, `Missing loc` and `localization`.

## The first full translation (2026-10-23)

| Check | Expect | If it fails |
|---|---|---|
| **No raw keys.** Open the mod's journal entries (Strategic Reserve, Banking, United Nations, Space Race), the Nation tab, the budget panel and a few mod events; hover their modifiers. | Spanish everywhere, with English only for a line added since the last pass. | A raw key: the English key itself is missing, or the deploy didn't build `localization/spanish/`. English on a line the TM has: its English changed since; `translate_loc.py --language spanish status` counts those. |
| **Concept links.** Hover the underlined terms in a mod tooltip, most of which the Spanish lowercases with `|l`. | Each opens its concept. | A plain-text term: the line lost its link, which merge should have rejected; report the key. |
| **Panels fit.** The Banking dashboard, the Demographics tab, the budget panel's tabs, the UN panel and the Strategic Reserve rows. | Labels fit their boxes. Spanish runs about a quarter longer than English. | Shorten the label's `"es"` in `i18n/spanish/tm/<file>.json`, keeping its `"en"`. |
| **Quotes and numbers.** An event that quotes someone, and a tooltip with a figure over 999 in its prose. | «…» quotation marks; 1 000 with no line break inside it, decimals with a comma (2,5). | A stray `"` cuts the line short: find it in the TM and replace it with « or ». |
| **Country names.** An event or tooltip that names another country. | The bare name, with *de* or *a* before it («Protege a Francia»), never a raw `GetAltName`. | Report the key; merge rejects `GetAltName` for Spanish, so it would have come in by hand. |
| **debug.log.** After a year of play. | No loc errors the English session doesn't have. | Fix the line in the TM. |
