---
paths:
  - "gui/**"
---

# GUI rules

Loaded when you read or edit a file under `gui/`.

- Read `docs/guides/gui_style_guide.md` before designing a panel (who it is for, what stays open, what collapses) and `docs/guides/gui_modding_guide.md` for the how.
- **Offline GUI lint** (before a play-test of `.gui` edits): `python3 scripts/analysis/check_gui_lint.py` — no game needed. Errors on unbalanced markup, a missing BOM and loc keys, scripted GUIs or concepts that don't exist; warns on markup no mod `.gui` has used before (unproven in game). Details: `docs/guides/python_tools.md`.
- **GUI reference audit**: `python3 gui_reference_audit.py --strict` — scans all mod GUIs and JE widget mounts; vanilla-unavailable categories and dynamic saved-scope bindings warn. Runs in CI and `POST_LOAD_AUDITS`; details in `docs/guides/python_tools.md`.
- **A new top-level `gui/*.gui` file or a new generated file fails a test whose name doesn't point at it.** `test_tax_code_bypass` wants every top-level GUI file in `gui_modding_guide.md`'s "This Mod's GUI Files" table, and the table's "Currently N GUI files" count to match. `test_nightly_audit_select` wants every path in `docs/auto_generated_files.md` classified in `scripts/nightly_audit_select.py`: `EXCLUDED_REGISTRY_GLOBS` for generator output, `INTENTIONALLY_NOT_EXCLUDED` for inputs. Run both before pushing.
- A `.gui` file starts with exactly one UTF-8 BOM.
