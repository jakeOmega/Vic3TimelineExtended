---
paths:
  - "localization/**"
  - "i18n/**"
---

# Localization rules

Loaded when you read or edit a file under `localization/` or `i18n/`.

- Localization keys: prefer adding to existing `*_l_english.yml` files, then run `python organize_loc.py` and commit everything it changes; CI's `organize_loc.py --check` fails otherwise. It files by key shape (`categorize_key`): a four-token `concept_*` name belongs in `te_miscellaneous_l_english.yml` and its `_desc` in `te_concepts_l_english.yml`, and a key added elsewhere moves on the next reload. A key defined in two loc files takes the last file's text (name order), so a stale copy in `te_unused_l_english.yml` overrides live text in another file; delete the stale copy (#617). Detail in `docs/guides/python_tools.md`.
- **Loc and player-guide text are American English** (program, defense, license, labor, color, center, -ize; owner, 2026-10-27), as the base game is; an official name keeps its own spelling (Kenyatta International Convention Centre). `python3 scripts/analysis/check_loc_spelling.py --check` lists stragglers (CI runs it); without `--check` it fixes them.
- **The engine emits no warning for a missing loc key**: the player sees the raw key. `loc_coverage_audit` catches it.
- **File sanity** (`python3 scripts/analysis/check_localization_files.py`, in CI): one BOM, an `l_<language>:` header matching the file name, no duplicate keys, a literal `"` inside a value written `\"` and paired, no value split across lines, no version digit glued to its quote (`key:0"`), a `$key$` inside a loc function's quoted argument carries `|q`, and a key `replace/` overrides is not defined again in an ordinary file. What each rule protects against: `docs/guides/python_tools.md`.
- Bold and italic are `#b text#!` and `#i text#!`, never `[b]text[/b]`: the bracket form errors on every render.
- **The ten non-English languages ship English copies generated at deploy time.** The game shows raw keys, not English, for a key the player's language lacks, so `deploy.sh` runs `scripts/generators/gen_non_english_loc.py` into `build/localization/` (gitignored, and ignored by the watcher) and syncs it as `localization/<language>/`. Never commit a non-English loc folder; the copies follow `localization/english/` on every deploy. A language with a translation memory (`i18n/<language>/tm/`, German and Spanish so far) gets its translations swapped in, key by key; run passes and apply corrections per `i18n/README.md`.
