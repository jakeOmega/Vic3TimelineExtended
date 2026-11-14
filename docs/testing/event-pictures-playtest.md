# Event pictures: in-game checks

What the next play-test should look at in event pictures. The offline preview (`scripts/image_pipeline/contact_sheet.py --window`) draws a picture as the default event window does, from a measurement of one screenshot (#1609); these rows check it against the game. In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): each PR adds its own section, newest last.

Fire an event from the console with `event <id>` (debug mode).

## Subjects moved into the clear half (#1608)

65 pictures were mirrored or shifted left so that their subject sits left of the text panel. The registry entry of each (`scripts/image_pipeline/event_image_prompts.py`) records its edit as `"reframed"`.

| Check | How | Expected | If not |
|---|---|---|---|
| A shifted picture | `event space_race_events.7` (`mars_dusty_landing`, shift 0.2) | The lander is wholly left of the text panel. The reflected strip at the right edge is not noticeable through the panel | A visible seam: the panel is less opaque than the preview assumes, so lower the shifts or render those pictures again |
| A mirrored picture | `event space_race_events.2` (`orbital_earth_view`, mirrored) | The astronaut is at the left, clear of the panel, and nothing in the picture reads backwards | Note the picture and what reads wrong: it needs a shift or a new render instead |
| A long description | Any of the 65 under an event with a long description (the frame grows taller) | The subject stays clear of the panel | A taller frame crops the picture's sides instead of stretching it, which the preview does not model: measure a screenshot of it and adjust `contact_sheet.py` |
