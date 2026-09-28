# Translations

The mod is written in English. `localization/english/` is the only loc the repo holds, and the game shows raw keys (not English) for any key missing from the player's language. So `scripts/deploy.sh` builds every other language's loc at deploy time with `scripts/generators/gen_non_english_loc.py`:

- a language **with** a folder here (`i18n/<language>/tm/`) gets its translations swapped in, key by key, with English wherever a key has no translation yet;
- every other language gets the English as it is.

None of the generated `.yml` is committed. The translation memory is.

## What's here

| Path | What |
|---|---|
| `<language>/BRIEF.md` | The translator's instructions: markup rules, grammar conventions, voice. Every agent run reads it. |
| `<language>/tm/<file>.json` | The translation memory, one file per English loc file. Each key maps to `{"en": <the English it was translated from>, "de": <the translation>}`. Declined country-name forms (`AFU_DAT`, …) have no English key of their own; they carry `"base": <key>` and sit with that key. |

## When the English changes

A translation stays attached to the English it was made from. When that English changes, the key is **stale**:

- a small change keeps the old translation until the next run. For text of six words or more, that means the same numbers and at least 85% similarity; for shorter text (names, labels), only case, spacing or final punctuation may differ.
- anything larger ships English until the key is translated again.

`python3 scripts/i18n/translate_loc.py status` counts translated, stale and missing keys. A deploy prints the same counts whenever it rewrites a file.

## Running a translation pass

Translation uses Claude Code subagents (on the subscription, not the API). The script does everything deterministic around them:

1. `python3 scripts/i18n/translate_loc.py prepare --set names` writes the glossary chunk: the mod's names (concepts, journal entries, laws, buildings, technologies, formable countries). Translate it first, because every other chunk is given these names as fixed terms.
2. `python3 scripts/i18n/translate_loc.py prepare` writes every other pending key as chunks of about 4,500 words (`--files te_events` to restrict, `--limit N` for the first N chunks). Each chunk file carries its own glossary: the mod terms and official vanilla German terms that occur in it, and what each referenced key inserts.
3. One agent per chunk reads `i18n/<language>/BRIEF.md` and `build/i18n/<language>/chunks/<id>.txt`, and writes `build/i18n/<language>/out/<id>.NN.txt` part files.
4. `python3 scripts/i18n/translate_loc.py merge` checks every line's markup against the English and adds the lines that pass to the translation memory. Rejects are listed in `build/i18n/<language>/merge_report.json`. They stay pending, so the next `prepare` offers them again.

Runs are resumable: whatever has merged is done, and `prepare` only offers what is still missing or stale. The merge check passes 97% of the base game's own English/German pairs unchanged; what it rejects there is vanilla German that has drifted from its English.

## Corrections from players

Edit the key's `"de"` value in `<language>/tm/*.json`, keeping `"en"` as it is, and commit. The next deploy ships it.
