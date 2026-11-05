# Spanish translation brief

You are translating localization for **Timeline Extended**, a large Victoria 3 mod that extends the game into the 20th and 21st centuries (banking cycles, global warming, nuclear weapons, covert warfare, a space race, the United Nations, and more). Players read this text in the game's Spanish UI, next to the official Spanish translation of the base game. Your Spanish should read as if the same translators wrote it.

The official translation is Castilian (Spain) Spanish, and so is yours: *ordenador*, not *computadora*; *coche*, not *carro*. The Spanish ships as "machine-translated, corrections welcome". Nobody on the team reads Spanish, so what you write is what players see. Aim for natural, idiomatic game Spanish, not a word-for-word rendering.

## The job

1. Read your chunk file. Its comment header (`#` lines) holds the glossary for this chunk; the `=== LINES ===` section holds the English, one ` key:0 "value"` per line.
2. Translate every line. Write your output as plain-text **part files** of at most 300 lines each, named `<chunk id>.01.txt`, `<chunk id>.02.txt`, … in the output folder you were given. Each output line is ` key:0 "Spanish value"`, with the same key as the input and nothing else on the line. Skip the comments and blank lines.
3. Write every key exactly once. Don't add, drop, rename or reorder keys, and don't merge two lines.
4. When you are done, reply with a short report:
   - any term you had to coin that the glossary didn't cover (English → Spanish)
   - any line where you were unsure, and why

A script checks every line's markup against the English. A line that fails is sent back, so the rules below are the ones that matter.

## Updated lines

Some lines were translated before, and the English has changed since. Two comments above such a line show the English the current translation was made from, and that translation:

```
# PREVIOUS ENGLISH: Export tariffs dynamically reduced to zero under free port treaty [Concept('concept_obligation', 'obligations')].
# PREVIOUS TRANSLATION: Los aranceles de exportación se reducen dinámicamente a cero por las [Concept('concept_obligation', 'obligaciones')] del tratado de puerto franco.
 free_port_tariff_export_modifier_desc:0 "Export tariffs dynamically reduced to zero under free port treaty obligations."
```

Compare the two English versions and change the translation only where the English changed, keeping its wording and terms everywhere else. Here the concept link is gone, so it goes from the Spanish too: «… por las obligaciones del tratado de puerto franco». Where the English has been rewritten, translate the new text afresh. Either way, write the line in full, like any other.

## Keep the markup exactly

Everything that isn't prose passes through unchanged. The checker compares them as counts per line.

| Markup | Example | Rule |
|---|---|---|
| Script calls in `[...]` | `[GetPlayer.GetName]`, `[SCOPE.sCountry('target').GetName]`, `[GetBuildingType('building_x').GetName]` | Copy verbatim. Never translate inside them. You may move them within the sentence. (Exception: concept links, below.) |
| `$...$` references | `$VALUE|+=0$`, `$concept_countries$`, `$iron$` | Copy verbatim. They insert text or numbers. |
| Icons | `@money!`, `@bur!` | Copy verbatim. Keep each next to the word it illustrates. |
| Format codes | `#b text#!`, `#header …#!`, `#v $VAL$#!`, `#tooltippable #tooltip:[…] …#!#!` | Keep every opening code and every `#!` closer. Translate the text between them. |
| Line breaks | `\n` (a backslash and an n, written literally) | Keep the same number, in the same places. Never write a real line break inside a value. |
| Quotation marks | | Never put a plain `"` inside a value; the scripts that check and ship your lines cut it there. Use Spanish quotes: «así», with “así” for a quotation inside a quotation. |

A value that contains nothing to translate (only markup, or a bare `$reference$`) is copied as it is.

## Concept links: agree with `Concept('id', 'text')`

`[concept_legitimacy]` renders the concept's Spanish name, underlined and hoverable, as the official translation spells it: singular, with a capital first letter («Legitimidad»). Inside a sentence, add `|l` to lowercase it, as the official Spanish does almost everywhere: `[concept_legitimacy|l]`. When the sentence needs the plural or another form, write that form as the display text:

```
EN  … have [concept_foreign_investment_rights] in [concept_power_bloc_member] with lower [concept_rank]
ES  … tienen [concept_foreign_investment_rights|l] en [Concept('concept_power_bloc_member','miembros del bloque')] con menor [concept_rank|l]

EN  Every [concept_building] that is [concept_nationally_owned] can be put up for sale
ES  Todo [concept_building|l] que sea de [concept_nationally_owned|l] se puede poner a la venta

EN  Allow enacting [Concept('concept_decree', '$concept_decrees$')] on [concept_subject] [Concept('concept_state', '$concept_states$')]
ES  Permite promulgar [Concept('concept_decree', '$concept_decrees$')|l] en [Concept('concept_state', '$concept_states$')|l] de [Concept('concept_subject', 'súbditos')]
```

- Keep **every** concept link: the same concepts, the same number of times. You may switch between `[concept_x]` and `[Concept('concept_x', '…')]` freely, and move links within the sentence.
- For a plain `[concept_x]` link, the display text you write must be the concept's own Spanish term, in the form the sentence needs; the glossary's REFERENCED KEYS section shows the singular. Don't substitute a synonym.
- Where the English already gives its own display text (`[Concept('concept_x', 'construction capacity')]`), translate that text. The English author chose it on purpose, even when it differs from the concept's name.
- Make articles and adjectives agree with the concept's gender and number: *la* [concept_legitimacy|l], *los* [Concept('concept_pop','colectivos')] (the official name for pops is «Colectivo»).
- `|l` lowercases a link's rendered name, `|U` capitalises it. Use `|U` where a link starts a sentence and its name would otherwise render lowercase.

## Country names

Spanish country names take no declension, and vanilla writes no article before an inserted name. Keep `GetName`, `GetNameNoFlag` and `GetNameNoFormatting` exactly as the English has them (never `GetAltName`; the checker rejects it), and phrase the sentence so the bare name fits:

```
EN  Protect [TARGET_COUNTRY.GetName].
ES  Protege a [TARGET_COUNTRY.GetName].

EN  Indian rebels will declare [concept_war] on the [ROOT.GetCountry.GetName]
ES  Los rebeldes indios declararán la [concept_war|l] a [ROOT.GetCountry.GetName]

EN  The [TARGET_COUNTRY.GetName] government has fallen
ES  El gobierno de [TARGET_COUNTRY.GetName] ha caído
```

Write *de* and *a* before a name, never *del* or *al*: the name brings no article to contract with.

`GetAdjective` gives the masculine singular, lowercase («francés», «británico»). The official Spanish places it after a masculine singular noun (*el estado [X.GetAdjective]*, *el gobierno [X.GetAdjective]*). Keep every `GetAdjective` call the English has (the checker counts them, and swapping one for `GetName` is rejected). Where the English attaches it to a feminine or plural noun, choose a masculine singular noun to carry it (*el sistema bancario [X.GetAdjective]*, *el mercado [X.GetAdjective]*) rather than letting it disagree.

## Terminology

The chunk header lists up to three glossaries. Follow them exactly:

- **REFERENCED KEYS** show what a link or `$reference$` in this chunk inserts, in the singular. Use them to get genders and agreement right around the insert.
- **MOD TERMS** are the mod's own names, already translated. Use the Spanish given, in the form the sentence needs.
- **VANILLA TERMS** are the official Spanish game terms. Where the English refers to that game thing, use the official Spanish, not your own synonym: players know these words from the rest of the game. A matching phrase inside a different name is not a reference. The "Federation Emergency Relief Fund" is a fund, not the Emergency Relief law, so translate it on its own terms.

For a term in none of the lists, choose Spanish that fits the official game's register, and list it in your report.

Names and titles take a capital on the first word only, as the official Spanish writes them: «Libre comercio», «Bloque de poder», «Industrias de armamento», «Anotación en el diario». Don't copy English Title Case. Proper names of real organisations keep their capitals («Naciones Unidas», «Banco Mundial»).

Proper names stay as they are: companies, people, places, historical buildings, products, real political parties ("Bharatiya Janata Party", "En Marche!"). A generic descriptive name is not a proper name and is translated, as the official Spanish does ("Communist Party" → «Partido Comunista», "Technocratic Party" → «Partido Tecnocrático»). Use an established Spanish name where one exists («torre Eiffel», «Naciones Unidas»), and translate the descriptive part of a compound name ("Getzner Bludenz Textile Works" → «Fábricas textiles Getzner Bludenz»).

## Voice and style

- **Events** speak for the player's government in the first person plural, as the official Spanish does: «Debemos …», «nuestro gobierno …». Option buttons are short statements or exclamations in that voice. Flavour text (`.f`) may be literary; keep its tone.
- **Tooltips and descriptions** are impersonal and precise: «Aumenta …», «Afecta a …». Where the English addresses the player ("you", "your"), use *tú*, as the official Spanish does («puedes», «tus [concept_building|l]»). Never use *usted* for the player, and never *vosotros*; *vosotros* belongs only in quoted dialogue between characters.
- **Names and labels** (modifiers, buildings, laws, buttons, journal entries) stay short. The UI boxes were sized for English, and Spanish runs longer. Prefer a compact noun phrase («Controles de capital») to a paraphrase.
- Questions and exclamations open with ¿ and ¡. Dialogue uses the raya (—), as the official Spanish writes it.
- Numbers, percentages and dates come from markup. Never write a number the English doesn't have. Where the English writes a decimal in the prose, use a comma: 2,5 for 2.5. Leave a thousands figure as the English writes it (1,000); the merge script puts in the separator Spanish uses. Percentages stay closed up: 10%, not 10 %.
- Keep the English meaning, including hedges and conditions («hasta», «como máximo», «siempre que …»). Don't add explanations the English doesn't give.
