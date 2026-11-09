---
description: Write or rewrite in-game text for the Vic3TimelineExtended mod to the house style - event titles, descriptions, flavor and options, and also tooltips, modifier and law descriptions and concepts. Use whenever the user asks to write, rewrite, polish, vary or review event text or any localization prose, mentions flavor text, "the style guide", a rewrite batch (#1539 and its sub-issues), text that "reads as AI", or asks why a loc style lint failed. Not for adding keys' plumbing (see add-event) or for translation (see i18n/README.md).
---

# Writing in-game text

The house style is `docs/guides/loc_style_guide.md`. Read it in full before writing; this skill is the order of work around it, not a summary of it. Event text is written by the strongest model available (owner, 2026-11-09): if you are a smaller model asked to write more than a few events, say so and offer to delegate.

## The order of work

1. **Read the guide**, and `docs/guides/event_creation_guide.md` § "Event Localization Style Guide" for the per-key conventions. Where they differ on voice, the style guide wins.
2. **Read the script before the text.** For each event: its `trigger`, what fires it (an on_action, another event's `trigger_event`, a button), and what each option does. `grep -n "<namespace>\.<n> = {" events/*.txt` finds it. For a modifier or law description, find what adds or defines it under `common/` and `events/`.
3. **Write down what the triggers guarantee** before writing a sentence. `python3 scripts/analysis/event_guarantees.py <event id or namespace>` prints each event's required technologies, what follows from them (prerequisites, and everything more than two eras behind), and the rest of its trigger. Work out which technology, law, system, scope or state of the world must hold for this text to be shown. Check the table in the guide (§ "What a chain's triggers already guarantee") and add or correct the chain's row. This is a deliverable, not a note to self.
4. **For flavor, look at the chain's mix:** `python3 scripts/analysis/flavor_forms.py <namespace>` (add `--list` for each key's form). Choose a form the chain is short of. No form takes more than a third of a chain.
5. **Write.** The three tests from the guide, on every sentence: could it be about anything else, could a game make it false, is it trying to be admired.
6. **Fix other text only where it breaks the guide** when the task is a rewrite: a stock metaphor, a claim the script does not back, an option whose wording misstates what it does, a report label for a title. Leave text that is plain and correct. In the pilot chain that still meant every description; budget for it.
7. **Check each text against the script again**, option wording included, then run the checklist at the end of the guide.

## What goes wrong most

- **The closing line built to land.** Cover the last sentence; if the text is complete without it, delete it. This is banned, not rationed.
- **Every flavor text becoming a two-voice exchange**, or, after reading this, every one becoming a memo. Spread the forms.
- **A detail a game can contradict:** an elapsed time, a quantity the game tracks, a technology, a faith, a named country, weather, a cabinet post. Read it from scope, gate it, or write it one level more general.
- **Hedging what is guaranteed.** If the trigger requires an election campaign, there are parties and voters; say so plainly.
- **Restating a modifier's effects** as its description. Name what was done.
- **A form growing its own formula:** every several-voices text ending on the pointed voice, every list ending on its sharpest item.
- **Under-explaining.** The reader arrives cold. Say who is speaking and to whom in words that can mean one thing, and give each instruction in a list its reason.
- **Jokes on every option.** Options may be light, in the base game's manner; lean flat before quippy, and grave events get grave options.

## Mechanics

- **Keep every key and every scope reference** in a rewrite. A new gated variant (`first_valid`, a triggered `desc`) needs its script change and its loc key in the same change.
- **Loc syntax:** `.claude/rules/localization.md`. One BOM, `\"` for a quote inside a value, `#b text#!` for bold, no text ending in `\n`.
- **After editing loc:** `python3 organize_loc.py`, and commit everything it rewrote.
- **The lints:** `python3 scripts/analysis/check_loc_style.py --check` and `python3 scripts/analysis/flavor_forms.py --check`. After rewriting old text both will report stale baseline entries: run each with `--update` and commit the smaller baseline. A word the lint flags that is meant takes `# REVIEWED YYYY-MM-DD (loc_style): why` trailing on the loc line.
- **Do not translate.** A rewritten key's German and Spanish go stale and ship English until the next translation pass; that is expected.
- **Script bugs found while reading** (an option that does not do what its name says, a trigger that does not guarantee what the text needs) are reported as their own issues, not written around.
- **Before pushing:** `.venv/bin/python scripts/preflight.py`.

## For a rewrite batch (#1539)

One PR per batch, or two for a batch over about 60 texts. The PR body shows `flavor_forms.py <namespace>` before and after for each chain, five events before and after, the count of keys changed by kind, the script bugs filed, and what the guide got wrong or left out for these chains. Player guide line: "no player-facing change" unless a chapter quotes the text.
