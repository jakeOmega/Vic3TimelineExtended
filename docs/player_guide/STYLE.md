# Writing the player guide

This is the house style for the chapters in this folder. Read it before you
write or edit one. `scripts/analysis/check_player_guide_style.py` checks the
mechanical parts; the rest is judgement.

## Who reads it

Players who have played Victoria 3 and want to know what this mod changes. They
know vanilla: pops, interest groups, laws, markets, construction, diplomatic
plays, journal entries. They do not know the mod's systems, and they do not read
script.

So:

- Explain the mod, not the base game. A clause of vanilla context is fine ("the
  construction points your queue spends"); a paragraph explaining vanilla
  construction is not.
- Tell players what they see, what they decide and what follows. For each
  system: where it appears in the interface, when it appears (the technology,
  law, date or condition that starts it), what its numbers mean, what each
  choice does, what can go wrong, how the AI behaves, and how it connects to
  other systems.
- Give the numbers a player plans around: thresholds, tiers, durations, caps,
  costs in the units the game shows. Leave out coefficients and formulas. The
  in-game tooltips carry the exact figures, so say so when a figure varies.
- Practical advice is welcome when it follows from the mechanics ("Build the
  reserve while prices are low; it drains into the market when war cuts supply").
  Don't invent strategy you can't justify from how the system works.
- Where players choose among a set of tools or options, say when each is worth
  it: a table of what you gain and what you pay, a line on when to use it, and
  how the AI uses it. "Managing foreign capital and import credit" in the banking
  chapter is the model. Name the benefits a player could miss, such as the
  leverage a treaty article earns a bloc leader.
- Describe the mod as it is now. Leave out change history: what an earlier
  version did, what was retired or renamed, what happens to saved games from
  before a change, what was "reworked recently". Leave out trivia a player can't
  act on, such as how many base-game companies there are or which expansion's
  content is covered. Comparing with the base game is fine; comparing with an
  older version of the mod is not.

## Accuracy

- **The script on the current branch is the authority.** Journal entries,
  buttons, effects, events and their localization decide what the game does.
  The design documents under `docs/systems/` explain intent, but several
  describe phases that were never built or were built differently; their `§0`
  sections say what shipped. When a design doc and the script disagree, the
  script wins.
- **Use in-game names.** Every name of a journal entry, button, law, building,
  modifier, technology or concept comes from `localization/english/`, spelled
  and capitalised as the game shows it. Never write a script key
  (`je_banking_cycle`, `law_post-scarcity`) or a file path.
- **Count things yourself.** The repository README and the Steam description
  disagree with each other and with the files on several counts. If you give a
  number of laws, milestones or buttons, count it from `common/`.
- **Describe only what exists.** Nothing from open pull requests or unbuilt
  design phases. If you can't confirm a mechanic from the script, leave it out
  and list it in your notes instead of guessing.

## Voice

Plain, direct, second person, present tense, American spelling (as the base game uses; keep in-game names exactly as spelled, e.g. "Nuclear Programme Sabotage"). "You", not "the player". "The
reserve drains", not "the reserve will drain". Write the way a good strategy-game
manual reads: short declarative sentences, concrete nouns, the verb *is* when
something is something.

These patterns make text read as machine-written. Avoid them (the list follows
Wikipedia's [Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)):

| Avoid | Write instead |
|---|---|
| Inflated words: *pivotal, crucial, key, vital role, vibrant, robust, seamless, comprehensive, intricate, nuanced, landscape, tapestry, testament, journey, realm* | Say what the thing does. "Crashes are rare below Boom" beats "managing the cycle is crucial". |
| Promotional verbs: *showcase, highlight, underscore, emphasize, enhance, foster, bolster, empower, elevate, leverage (as a verb)* | *show, raise, increase, help, use* |
| Copula avoidance: *serves as, stands as, acts as a, functions as, represents a* | *is* |
| Negative parallelism: "It's not just X, it's Y", "not only X but also Y", "no X, no Y, just Z" | State Y. |
| Stock openers: *Additionally, Furthermore, Moreover, Notably, Importantly, Ultimately, Overall, In summary* | Start with the subject. Often no connective is needed. |
| Significance padding: "marking a turning point", "reflecting the broader shift", "a testament to" | Cut it. Mechanics are the point. |
| Rule of three as decoration: "faster, cheaper, and more reliable" when one adjective is true | List the items that exist, however many there are. |
| Vague association: "is associated with", "in connection with" | Name the relation: *raises, requires, unlocks, is part of*. |
| Hedged summaries: "Overall, the system offers a variety of options for a wide range of playstyles." | Delete the sentence. |
| Chatty asides: "Let's look at", "You might be wondering", "Whether you're a new player or a veteran" | Delete. |

Other habits to avoid: a closing "Conclusion", "Summary" or "Tips and tricks"
section that repeats the chapter; ending a section with a sentence about how
flexible or rich the system is; and more than one em dash in a paragraph (prefer
none: use a comma, colon, parentheses or a new sentence).

## Format

The PDF is built with pandoc from GitHub-flavoured Markdown, and the same files
render on GitHub. Stick to this subset:

- **Headings.** Each chapter file opens with exactly one `#` heading, the chapter
  title. Sections are `##`, subsections `###`, and `####` only when needed. Don't
  skip a level. Sentence case: "The policy rate", not "The Policy Rate" (proper
  names keep their capitals: "Strategic Reserve", "United Nations"). Put at least
  one sentence between a heading and its first subheading.
- **Headings must be unique across the whole guide**, because the PDF is one
  document and each heading becomes a link target. Prefer specific headings:
  "Banking tools" rather than "Tools", "Space race funding" rather than "Funding".
- **Links.** To a section in the same chapter: `[text](#heading-anchor)`, where
  the anchor is the heading in lower case with spaces as hyphens and punctuation
  dropped. To another chapter: `[text](04-banking.md)` for the chapter, or
  `[text](04-banking.md#the-policy-rate)` for a section. The build turns these
  into links inside the PDF. The lint checks that targets exist.
- **Tables** for data that has rows and columns: buttons and what they do, tiers
  and thresholds, rules and defaults. Not for prose chopped into cells. A table
  that only lists content (every wonder with its state, every unit or ship) goes
  in [Appendix: reference lists](19-appendix-reference-lists.md), with a sentence
  or two and a link in the chapter. Keep a table in the chapter when it is short
  or explains a mechanic or a choice.
- **Lists** for real lists. Write each item as a sentence or a plain phrase. No
  bold lead-ins (`- **Term**: description`); if every item needs a label, it is a
  table.
- **Bold** only for a term at the point you define it, and rarely. *Italics* for
  the occasional emphasis or a title.
- **Block quotes** (`> ...`) render as a shaded note. Use them sparingly, for a
  caveat or tip that stands apart from the flow, and write them as plain
  sentences (no "**Tip:**" label).
- **Screenshots** will be added later. Where one would help, put a placeholder
  comment alone on its own line, with a blank line before and after:
  `<!-- screenshot: the Banking Cycle dashboard during a Boom, policy buttons in view -->`.
  One to three per chapter is plenty. Never start a line with a comment and then
  continue with text on the same line: CommonMark drops the whole line.
- No emoji, no horizontal rules (`---`), no raw HTML, no footnotes. Straight
  quotes (`"`, `'`); the PDF build curls them.
- Symbols the PDF font covers and you may use: `°C`, `×`, `≥`, `≤`, `→`, `±`,
  `½`, `¼`, `CO₂`, the en dash in ranges (`1919–1945`).

## The lint

```sh
python3 scripts/analysis/check_player_guide_style.py            # every chapter
python3 scripts/analysis/check_player_guide_style.py docs/player_guide/04-banking.md
python3 scripts/analysis/check_player_guide_style.py --stats    # word counts
```

It flags the vocabulary and patterns above, script keys and file paths, broken
links, duplicate headings and heading-structure problems. When a flagged word is
used literally (a *key* on the keyboard, the *landscape* of a map), add
`<!-- style: allow ai-vocab -->` at the **end** of that line. Don't use the
suppression to keep a phrase the rule is right about. CI runs the lint with
`--strict`.

## Building the PDF

```sh
.venv/bin/pip install -r requirements-docs.txt   # once: pandoc and Typst wheels
.venv/bin/python scripts/build_player_guide.py
```

Commit the rebuilt PDF with the chapter change. CI's `--check` step fails when
the committed PDF was built from different sources.
