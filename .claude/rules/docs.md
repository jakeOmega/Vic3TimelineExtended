---
paths:
  - "docs/**"
---

# Docs rules

Loaded when you read or edit a file under `docs/`.

- **Four docs are CRLF: `docs/systems/journal_entry_systems.md`, `docs/guides/gui_modding_guide.md`, `docs/vanilla/treaty_articles_reference.md` and `docs/vanilla/wonder_buildings_reference.md`.** A Python rewrite (`open(...).write`) silently flips them to LF and turns a two-line edit into a 1,100-line diff; preserve line endings (`newline=""` on read/write, or read/write bytes) or edit with `sed`/`Edit`, and confirm afterwards. `file <path>` does **not** always report CRLF (it calls `treaty_articles_reference.md` plain UTF-8); `grep -c $'\r$' <path>` against `wc -l` is the reliable check. `preflight.py`'s `line-endings` check fails on a flipped one.
- `docs/player_guide/` is written for players and has its own house style: `docs/player_guide/STYLE.md`. Rebuild the PDF after any chapter edit (`.venv/bin/python scripts/build_player_guide.py`) and commit both.
- `docs/guides/audits.md` and the files `docs/auto_generated_files.md` lists are generated: edit the generator's input.
- A new system doc under `docs/systems/mod_systems/` needs a row in the index `docs/systems/mod_systems.md`; `test_mod_systems_index.py` fails on a file or `##` section the index leaves out.
- When you learn something the next agent would otherwise rediscover, write it down in the same session, one paragraph or a bullet: engine and scripting behavior in `docs/guides/scripting_best_practices.md`, tooling behavior in `docs/guides/python_tools.md`, git and PR workflow in `docs/guides/git_workflow.md`.
