# Translations

The mod is written in English. `localization/english/` is the only loc the repo holds, and the game shows raw keys (not English) for any key missing from the player's language. So `scripts/deploy.sh` builds every other language's loc at deploy time with `scripts/generators/gen_non_english_loc.py`:

- a language **with** a folder here (`i18n/<language>/tm/`) gets its translations swapped in, key by key, with English wherever a key has no translation yet;
- every other language gets the English as it is.

None of the generated `.yml` is committed. The translation memory is.

## What's here

| Path | What |
|---|---|
| `<language>/BRIEF.md` | The translator's instructions: markup rules, grammar conventions, voice. Every agent run reads it. |
| `<language>/terms.json` | Terms coined during runs, English → translation (the mod's recurring names that aren't loc keys of their own, plus official game terms agents kept getting wrong). `prepare` adds the ones a chunk contains to its glossary; `check-terms` finds translations that disagree. Add to it whenever a report shows two chunks rendering one term differently. |
| `<language>/tm/<file>.json` | The translation memory, one file per English loc file. Each key maps to `{"en": <the English it was translated from>, "de": <the translation>}`. Declined country-name forms (`AFU_DAT`, …) have no English key of their own; they carry `"base": <key>` and sit with that key. |

## When the English changes

A translation stays attached to the English it was made from. When that English changes, the key is **stale**:

- a small change keeps the old translation until the next run. For text of six words or more, that means the same numbers and at least 85% similarity; for shorter text (names, labels), only case, spacing or final punctuation may differ.
- anything larger ships English until the key is translated again.

The next `prepare` offers a stale key again, with the English its translation was made from and that translation as comments above the line (BRIEF.md § Updated lines), so the agent edits the translation rather than starting over. Developer test benches (`DEV_ONLY_FILES` in the script) are never offered.

`python3 scripts/i18n/translate_loc.py status` counts translated, stale and missing keys. A deploy prints the same counts whenever it rewrites a file.

## Running a translation pass

Translation uses Claude Code subagents (on the subscription, not the API). The script does everything deterministic around them:

1. `python3 scripts/i18n/translate_loc.py prepare --set names` writes the glossary chunk: the mod's names (concepts, journal entries, laws, buildings, technologies, formable countries). Translate it first, because every other chunk is given these names as fixed terms.
2. `python3 scripts/i18n/translate_loc.py prepare` writes every other pending key as chunks of about 9,000 words or 700 keys, whichever comes first (`--files te_events` to restrict, `--limit N` for the first N chunks). Each chunk file carries its own glossary: the mod terms and official vanilla German terms that occur in it, and what each referenced key inserts.
3. One Sonnet subagent per chunk reads `i18n/<language>/BRIEF.md` and `build/i18n/<language>/chunks/<id>.txt`, and writes `build/i18n/<language>/out/<id>.NN.txt` part files. `python3 scripts/i18n/translate_loc.py prompt <id>…` prints the prompt to give it. Parts are capped at 100 lines for event prose and 200 otherwise, because an agent whose single response passes 64,000 output tokens fails outright. If one does fail, resume it (its context already holds the chunk) and ask for smaller parts. Eight agents in parallel took 20–30 minutes a wave.
4. `python3 scripts/i18n/translate_loc.py merge` checks every line's markup against the English and adds the lines that pass to the translation memory. Rejects are listed in `build/i18n/<language>/merge_report.json`. They stay pending, so the next `prepare` offers them again. Merge also repairs what it can decide mechanically: a plain `"` closing a „quotation“ (the loader would cut the line there), English-format numbers left in the prose (2.5 → 2,5, 1,000 → 1.000) and, for German, a space before `%` and quotation marks: the English's escaped straight quotes (`\"…\"`) and a wrongly shaped closing mark („…”) become „…“, with ‚…‘ nested inside.
5. Read each agent's report (also saved as `out/<id>.report.md`, in case the session ends before the agent replies). Agents list the terms they coined and the lines they doubted; in the German run they surfaced most of the problems the markup check can't see: a vanilla term applied out of context, an English name kept where the game has an official German one, a guessed game term. Settle each by checking the vanilla loc, add the decision to `terms.json`, and `python3 scripts/i18n/translate_loc.py refresh <ids>` the chunks no agent has started, so they carry it.
6. At the end, `python3 scripts/i18n/translate_loc.py prepare-fixes` writes a correction chunk from every `check-terms` mismatch, plus lines matching `--note 'REGEX=instruction'` or named by `--key-note 'KEY=instruction'`. One agent rewrites those lines, changing only the flagged term, and they merge like any chunk.

The German run (September 2026): 19,590 keys and 264,000 words: a glossary chunk, 35 content chunks and one correction chunk. It took about three hours with eight Sonnet agents in parallel, and cost at most 8 points of a weekly subscription limit and about a third of one 5-hour session, orchestration included (an upper bound: another session ran alongside). Measure a run by the `/usage` change after the first wave, scaled by the share of the words that wave covered; the agents' own token counts are unreliable. 0.4% of lines were rejected, and 207 were corrected for consistency.

Runs are resumable: whatever has merged is done, and `prepare` only offers what is still missing or stale. The merge check passes 97% of the base game's own English/German pairs unchanged; what it rejects there is vanilla German that has drifted from its English.

## Corrections from players

Edit the key's `"de"` value in `<language>/tm/*.json`, keeping `"en"` as it is, and commit. The next deploy ships it.
