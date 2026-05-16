# Nightly audit — GUI

For each selected `.gui` file under `gui/`.

## Checks

- **Template resolution.** Every `using = X` reference resolves to a template defined in this file, in another mod-side `.gui` file loaded earlier, or in vanilla `gui/`. Unresolved `using =` references emit `Could not find template 'X'` warnings at type registration. (`docs/guides/gui_modding_guide.md`)
- **Override structural parity.** Override patterns mirror vanilla's panel structure. Compare the file's vanilla counterpart (under `~/src/vic3/game/gui/`) for major divergences in window types, container nesting, or naming.
- **Vanilla-version drift.** Pre-1.13.5 override patterns and renamed-widget references have been updated to match the current vanilla version. The mod has historically silently broken when a vanilla GUI rename changed a widget name the mod referenced. (memory: verify Explore-agent enumerations re: GUI 1.13.5 migration)
- **DLC-only template references.** No template references that exist only in DLC content the mod doesn't strictly require. Flag any DLC-conditional include.
- **Localization references in widgets.** Loc keys referenced in `text =` / `tooltip =` exist (procedural `loc_coverage_audit` covers content entities, but GUI strings may slip through if the keys are referenced only from widget attributes).
