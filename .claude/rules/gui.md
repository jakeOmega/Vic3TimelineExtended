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
- **See a type in the game: `python3 -m game_qa gui-show TYPE`** in a `game_qa` session, run from the checkout holding the change (the `game-qa` skill; a session needs the owner's go-ahead). It syncs the branch's `.gui` files into the harness's overlay, shows the type alone over a flat backdrop, and returns a full-resolution crop and the GUI lines the game logged; `--outlines` draws every widget's box.
- **A long list of rows in a `flowcontainer` costs every row every frame, seen or not; a `fixedgridbox` skips what is out of view.** Put each row's fixed-size part in a one-item `fixedgridbox` (`DataModelFirst(<a list that always has an element>, '(int32)1')`) and give the list `max_update_rate = 10`: the Buildings panel on a 2050 save went from 341 ms a frame to 18 (`gui_modding_guide.md` gotcha #54).
