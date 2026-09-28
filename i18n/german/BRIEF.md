# German translation brief

You are translating localization for **Timeline Extended**, a large Victoria 3 mod that extends the game into the 20th and 21st centuries (banking cycles, global warming, nuclear weapons, covert warfare, a space race, the United Nations, and more). Players read this text in the game's German UI, next to the official German translation of the base game. Your German should read as if the same translators wrote it.

The German ships as "machine-translated, corrections welcome". Nobody on the team reads German, so what you write is what players see. Aim for natural, idiomatic game German, not a word-for-word rendering.

## The job

1. Read your chunk file. Its comment header (`#` lines) holds the glossary for this chunk; the `=== LINES ===` section holds the English, one ` key:0 "value"` per line.
2. Translate every line. Write your output as plain-text **part files** of at most 300 lines each, named `<chunk id>.01.txt`, `<chunk id>.02.txt`, … in the output folder you were given. Each output line is ` key:0 "German value"`, with the same key as the input and nothing else on the line. Skip the comments and blank lines.
3. Write every key exactly once. Don't add, drop, rename or reorder keys, and don't merge two lines.
4. When you are done, reply with a short report:
   - any term you had to coin that the glossary didn't cover (English → German)
   - any line where you were unsure, and why

A script checks every line's markup against the English. A line that fails is sent back, so the rules below are the ones that matter.

## Keep the markup exactly

Everything that isn't prose passes through unchanged. The checker compares them as counts per line.

| Markup | Example | Rule |
|---|---|---|
| Script calls in `[...]` | `[GetPlayer.GetName]`, `[SCOPE.sCountry('target').GetName]`, `[GetBuildingType('building_x').GetName]` | Copy verbatim. Never translate inside them. You may move them within the sentence. (Exceptions: concept links and country names, below.) |
| `$...$` references | `$VALUE|+=0$`, `$concept_countries$`, `$iron$` | Copy verbatim. They insert text or numbers. |
| Icons | `@money!`, `@bur!` | Copy verbatim. Keep each next to the word it illustrates. |
| Format codes | `#b text#!`, `#header …#!`, `#v $VAL$#!`, `#tooltippable #tooltip:[…] …#!#!` | Keep every opening code and every `#!` closer. Translate the text between them. |
| Line breaks | `\n` (a backslash and an n, written literally) | Keep the same number, in the same places. Never write a real line break inside a value. |
| Quotation marks | | Never put a plain `"` inside a value; the loader cuts the line there. Use German quotes: „so“. |

A value that contains nothing to translate (only markup, or a bare `$reference$`) is copied as it is.

## Concept links: inflect with `Concept('id', 'text')`

`[concept_legitimacy]` renders the concept's German name, underlined and hoverable, in the **nominative**. When the sentence needs another case or number, write the inflected form as the display text, the way the official German does thousands of times:

```
EN  … have [concept_foreign_investment_rights] in [concept_power_bloc_member] with lower [concept_rank]
DE  … haben [concept_foreign_investment_rights] bei [Concept('concept_power_bloc_member','Blockmitgliedern')] mit niedrigerem [concept_rank]

EN  The efficiency of [Concept('concept_ship_group', '$ship_group_cruisers$')] @ship_construction! [concept_ship_construction]
DE  Die Effizienz des @ship_construction! [Concept('concept_ship_construction', 'Schiffbaus')] für [Concept('concept_ship_group', '$ship_group_cruisers$')]

EN  Allow enacting [Concept('concept_decree', '$concept_decrees$')] on [concept_subject] [Concept('concept_state', '$concept_states$')]
DE  Erlaubt es, [Concept('concept_decree', '$concept_decrees$')] in [Concept('concept_state', '$concept_states$')] von [Concept('concept_subject', 'Klientelländern')] zu beschließen
```

- Keep **every** concept link: the same concepts, the same number of times. You may switch between `[concept_x]` and `[Concept('concept_x', '…')]` freely, and move links within the sentence.
- For a plain `[concept_x]` link, the display text you write must be the concept's own German term, inflected; the glossary's REFERENCED KEYS section shows the nominative. Don't substitute a synonym.
- Where the English already gives its own display text (`[Concept('concept_x', 'construction capacity')]`), translate that text, inflected. The English author chose it on purpose, even when it differs from the concept's name.
- `|l` lowercases a link's rendered name (`[concept_foreign_investment_rights|l]`), `|U` capitalises it. Use them where German capitalisation needs it.

## Country names: decline with `GetAltName`

German needs articles and cases for country names ("die Vereinigten Staaten", "dem Deutschen Reich"). The game provides every country's declined forms. Where the English has `.GetName` on a **country** scope, use `.GetAltName('<FORM>')` when the grammar needs it:

| Form | Gives | Use for |
|---|---|---|
| `NOM` | „die Vereinigten Staaten“ | subject |
| `GEN` | „der Vereinigten Staaten“ | genitive |
| `DAT` | „den Vereinigten Staaten“ | dative object |
| `AKK` | „die Vereinigten Staaten“ | accusative object |
| `VON` | „von den Vereinigten Staaten“ | von + dative |
| `IN` | „in den Vereinigten Staaten“ | in + dative |
| `NACH` | „nach …“ | direction |

Add `|U` when the form starts a sentence, so its article is capitalised. The same applies to `GetNameNoFlag` → `GetAltNameNoFlag('…')` and `GetNameNoFormatting` → `GetAltNameNoFormatting('…')`.

```
EN  [INITIATOR_COUNTRY.GetName] has [concept_foreign_investment_rights] in [TARGET_COUNTRY.GetName]
DE  [INITIATOR_COUNTRY.GetAltName('NOM')|U] hat [concept_foreign_investment_rights|l] [TARGET_COUNTRY.GetAltName('IN')]

EN  Indian rebels will declare [concept_war] on the [ROOT.GetCountry.GetName]
DE  Indische Rebellen werden [ROOT.GetCountry.GetAltName('DAT')] den [concept_war] erklären
```

Use `GetAltName` only on scopes that are certainly countries: names like `COUNTRY`, `TARGET_COUNTRY`, `INITIATOR_COUNTRY`, any accessor ending in `Country` (`.GetCountry`, `.GetFirstCountry`, `.GetSecondCountry`), `.GetOwner`, `.GetOverlord`, `sCountry(…)`, `sC(…)`, `GetPlayer`. States, characters, interest groups, buildings and everything else keep `GetName`. If you can't tell, keep `GetName` and phrase the sentence so the bare name fits.

`GetAdjective` gives an uninflected stem. The official German writes `[X.GetAdjective|l]en` or `…e` to decline it. Do the same.

### Country name forms (glossary chunk only)

The glossary chunk ends with a `=== COUNTRY NAME FORMS ===` section listing the mod's formable countries and dynamic country names. For each one, translate the name as a normal line (` AFU:0 "Afrikanische Union"`), then write its seven declined forms as extra keys, `<KEY>_NOM`, `_GEN`, `_DAT`, `_AKK`, `_VON`, `_IN`, `_NACH`, each including its article or preposition:

```
 dyn_c_american_federation_NOM:0 "die Amerikanische Föderation"
 dyn_c_american_federation_GEN:0 "der Amerikanischen Föderation"
 dyn_c_american_federation_DAT:0 "der Amerikanischen Föderation"
 dyn_c_american_federation_AKK:0 "die Amerikanische Föderation"
 dyn_c_american_federation_VON:0 "von der Amerikanischen Föderation"
 dyn_c_american_federation_IN:0 "in der Amerikanischen Föderation"
 dyn_c_american_federation_NACH:0 "in die Amerikanische Föderation"
```

A name that takes no article in German (most plain country names, "Deutschland") has forms without one: `Deutschland`, `Deutschlands`, `Deutschland`, `Deutschland`, `von Deutschland`, `in Deutschland`, `nach Deutschland`.

## Terminology

The chunk header lists up to three glossaries. Follow them exactly:

- **REFERENCED KEYS** show what a link or `$reference$` in this chunk inserts, in the nominative. Use them to get genders and cases right around the insert.
- **MOD TERMS** are the mod's own names, already translated. Use the German given, inflected as the sentence needs.
- **VANILLA TERMS** are the official German game terms. Where the English refers to that game thing, use the official German, not your own synonym: players know these words from the rest of the game. A matching phrase inside a different name is not a reference. The "Federation Emergency Relief Fund" is a fund, not the Emergency Relief law, so translate it on its own terms.

For a term in none of the lists, choose German that fits the official game's register, and list it in your report.

Proper names stay as they are: companies, people, places, historical buildings, products, real political parties ("Bharatiya Janata Party", "En Marche!"). A generic descriptive name is not a proper name and is translated, as the official German does ("Communist Party" → „Kommunistische Partei", "Technocratic Party" → „Technokratische Partei"). Use an established German name where one exists ("Eiffelturm", "Vereinte Nationen"), and translate the descriptive part of a compound name ("Getzner Bludenz Textile Works" → „Textilwerke Getzner Bludenz“).

## Voice and style

- **Events** speak for the player's government in the first person plural: „Wir müssen …“, „unsere Regierung …“. Option buttons are short statements or exclamations in that voice. Flavour text (`.f`) may be literary; keep its tone.
- **Tooltips and descriptions** are impersonal and precise: „Erhöht die …“, „Wirkt sich auf … aus“. Address the player directly (Sie) only where the English does, and sparingly.
- **Names and labels** (modifiers, buildings, laws, buttons, journal entries) stay short. The UI boxes were sized for English, and German runs longer. Prefer a compact noun („Kapitalverkehrskontrollen“) to a paraphrase.
- Numbers, percentages and dates come from markup. Never write a number the English doesn't have. Where the English writes a number in the prose, use German format: 2,5 for 2.5, and 1.000 for 1,000.
- Keep the English meaning, including hedges and conditions („bis zu“, „höchstens“, „sofern …“). Don't add explanations the English doesn't give.
