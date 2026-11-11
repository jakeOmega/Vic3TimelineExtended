---
description: Add one or more new events to the Vic3TimelineExtended mod, end to end - script, wiring, picture, localization and the audits that guard each. Use whenever the user asks to add, create or scaffold an event or an event chain, to "fire an event when X", to add an option to an existing event, or to wire an event to an on_action, journal entry or button. Covers the pieces an event needs so that it fires, shows a picture, reads correctly and passes CI. For the wording itself use the event-text skill.
---

# Adding an event

An event that parses can still never fire, draw a magenta blob, show raw keys, or silently change a number. Each of those has an audit; this is the order that avoids tripping them.

## Before writing

1. **Read the system's doc** in `docs/systems/mod_systems/` (index: `docs/systems/mod_systems.md`) and the namespace's existing events, so the new one uses the system's variables, helpers and vocabulary.
2. **Read `docs/guides/event_creation_guide.md`**: the boilerplate, § "Event Design Guidelines" (option tradeoffs, agency, AI weights) and § "Making an Event Open at Once".
3. **Look up what you have not used before:** `python3 scripts/lessons.py <effect or trigger name>`. `.claude/rules/script.md` holds the engine gotchas and loads when you open a file under `events/`.
4. **Pick the ids:** `python3 scripts/generators/gen_event.py next-id <namespace> --count N`.

## The pieces, in order

1. **Script**, in `events/<system>_events.txt`. Scaffold with `python3 scripts/generators/gen_event.py scaffold ... --dry-run` or a JSON spec with `batch` (`docs/guides/python_tools.md` § "Event Scaffolding"), or copy the boilerplate. Tabs, one UTF-8 BOM.
   - There is no `is_triggered_only` in Victoria 3.
   - A system's event checks its game rule in `trigger`, or fires only from something that does.
   - `add_modifier` durations are literals or a bare named value; the `*_modifier_time` values are days.
   - An option that changes a variable the UI shows says so in a `custom_tooltip`: `change_variable` prints nothing.
   - Every option does something, and one is `default_option = yes`.
   - A `create_character` for a flavor speaker follows the guide's pattern exactly (`place_character_in_void`, guarded `kill_character` in `after`).
2. **Something fires it.** An on_action in `common/on_actions/`, a `trigger_event` from an effect or another event, or a button. An event nothing fires is dead content.
3. **A picture.** `event_image = { texture = ... }` or `{ video = ... }`. A visible event without one draws a magenta blob and logs nothing. Reuse an existing picture only after looking at it (`python3 scripts/image_pipeline/contact_sheet.py --window --event <id>`): the window's text panel covers the right half of the picture, so what the event is about should sit in the left half (`reframe_event_image.py --mirror` or `--shift` moves it there; the event guide says when each works). A new picture is a pending entry in `scripts/image_pipeline/event_image_prompts.py` with interim art on the event.
4. **Text.** Keys `<ns>.<n>.t`, `.d`, `.f`, `.a`, `.b`... in `localization/english/te_events_l_english.yml`, written with the `event-text` skill. Then `python3 organize_loc.py` and commit what it rewrote.
5. **Balance of the options:** the checks in the event guide § "Verifying Option Balance". No option should be better than another on every count.

## Verify

```sh
.venv/bin/python scripts/run_audits.py orphaned_event event_image event_context silent_variable empty_effect \
    script_loc_reference loc_coverage effect_trigger_validity script_argument modifier_duration kill_character
python3 scripts/analysis/check_loc_style.py --check
python3 scripts/analysis/flavor_forms.py --check
.venv/bin/python scripts/preflight.py --quick
```

A failing audit prints what its flag means and the comment that suppresses an intended one (`docs/guides/audits.md`). With a server up, `POST /reload?mod_only=true&audits_only=true` and read `warnings`: `event_magnitude_audit` (a hardcoded amount for a fast-growing resource) runs only there.

## What only the game shows

The event firing when it should, its picture, its tooltips, and the options' effects are in-game checks. They do not gate the merge: add them to the system's play-test list under `docs/testing/`, and test in game with `event <id>` in the console (Victoria 3 has no `effect` console command).

## The PR

A "Player guide" line: an event chain a player works through may need a sentence in its system's chapter; a one-off event does not (`19-appendix-events.md` lists some chains, check it).
