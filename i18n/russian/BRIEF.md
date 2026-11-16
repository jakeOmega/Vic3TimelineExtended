# Russian translation brief

You are translating localization for **Timeline Extended**, a large Victoria 3 mod that extends the game into the 20th and 21st centuries (banking cycles, global warming, nuclear weapons, covert warfare, a space race, the United Nations, and more). Players read this text in the game's Russian UI, next to the official Russian translation of the base game. Your Russian should read as if the same translators wrote it.

The Russian ships as "machine-translated, corrections welcome" («машинный перевод, исправления приветствуются»). Nobody on the team reads Russian, so what you write is what players see. Aim for natural, idiomatic game Russian, not a word-for-word rendering.

## The job

1. Read your chunk file. Its comment header (`#` lines) holds the glossary for this chunk; the `=== LINES ===` section holds the English, one ` key:0 "value"` per line.
2. Translate every line. Write your output as plain-text **part files** of at most 300 lines each, named `<chunk id>.01.txt`, `<chunk id>.02.txt`, … in the output folder you were given. Each output line is ` key:0 "Russian value"`, with the same key as the input and nothing else on the line. Skip the comments and blank lines.
3. Write every key exactly once. Don't add, drop, rename or reorder keys, and don't merge two lines.
4. When you are done, reply with a short report:
   - any term you had to coin that the glossary didn't cover (English → Russian)
   - any line where you were unsure, and why

A script checks every line's markup against the English. A line that fails is sent back, so the rules below are the ones that matter.

## Updated lines

Some lines were translated before, and the English has changed since. Two comments above such a line show the English the current translation was made from, and that translation:

```
# PREVIOUS ENGLISH: Export tariffs dynamically reduced to zero under free port treaty [Concept('concept_obligation', 'obligations')].
# PREVIOUS TRANSLATION: Экспортные пошлины динамически снижаются до нуля в силу [Concept('concept_obligation', 'обязательств')] по договору о свободном порте.
 free_port_tariff_export_modifier_desc:0 "Export tariffs dynamically reduced to zero under free port treaty obligations."
```

Compare the two English versions and change the translation only where the English changed, keeping its wording and terms everywhere else. Here the concept link is gone, so it goes from the Russian too: «… в силу обязательств по договору о свободном порте». Where the English has been rewritten, translate the new text afresh. Either way, write the line in full, like any other.

## Template lines

A generated file repeats some lines once for each copy of a system (each culture merge, say), with only their `$...$` references and `[...]` values changed. Your chunk holds one copy of such a line, under a comment naming what changes:

```
# TEMPLATE: the script copies this translation to 96 more lines, replacing $dixie$, [ROOT.GetCountry.MakeScope.Var('te_cm_held_american_dixie').GetValue|%0] with each line's own. …
 je_te_cm_american_status_hold_dixie:0 "$dixie$ pops are out of reach: our sphere holds only [ROOT.GetCountry.MakeScope.Var('te_cm_held_american_dixie').GetValue|%0] of them in their homeland, …"
```

A script writes your translation into every other copy, swapping in each one's own references. Keep the ones the comment names exactly as written: one with a case flag added can't be swapped, and its copies stay English. Translate the line so it reads right whatever they insert. Here every merge's culture takes the place of `$dixie$`, and a bare name can't be declined, so put it after a noun that carries the case: «Население культуры $dixie$ вне досягаемости…» (Country names, below, explains why.)

## Keep the markup exactly

Everything that isn't prose passes through unchanged. The checker compares them as counts per line.

| Markup | Example | Rule |
|---|---|---|
| Script calls in `[...]` | `[GetPlayer.GetName]`, `[SCOPE.sCountry('target').GetName]`, `[GetBuildingType('building_x').GetName]` | Copy verbatim. Never translate inside them. You may move them within the sentence. (Exception: concept links, below.) |
| `$...$` references | `$VALUE|+=0$`, `$concept_countries$`, `$iron$` | Copy verbatim. They insert text or numbers. |
| Icons | `@money!`, `@bur!` | Copy verbatim. Keep each next to the word it illustrates. |
| Format codes | `#b text#!`, `#header …#!`, `#v $VAL$#!`, `#tooltippable #tooltip:[…] …#!#!` | Keep every opening code and every `#!` closer. Translate the text between them. |
| Line breaks | `\n` (a backslash and an n, written literally) | Keep the same number, in the same places. Never write a real line break inside a value. |
| Quotation marks | | Never put a plain `"` inside a value; the scripts that check and ship your lines cut it there. Use Russian quotes: «так», with „так“ for a quotation inside a quotation. |

A value that contains nothing to translate (only markup, or a bare `$reference$`) is copied as it is.

## Concept links: inflect with `Concept('id', 'text')`

`[concept_legitimacy]` renders the concept's Russian name, underlined and hoverable, in the **nominative singular with a capital first letter** («Легитимность»). Russian needs cases, so when the sentence needs another case or number, write the inflected form, in lowercase inside a sentence, as the display text:

```
EN  … have [concept_foreign_investment_rights] in [concept_power_bloc_member] with lower [concept_rank]
RU  … имеют [concept_foreign_investment_rights|l] у [Concept('concept_power_bloc_member','членов блока')] с более низким [Concept('concept_rank','рангом')]

EN  The efficiency of [Concept('concept_ship_group', '$ship_group_cruisers|q$')] @ship_construction! [concept_ship_construction]
RU  Эффективность @ship_construction! [Concept('concept_ship_construction', 'кораблестроения')] для [Concept('concept_ship_group', '$ship_group_cruisers|q$')|l]

EN  Raises [concept_legitimacy] by $VAL$
RU  Повышает [concept_legitimacy|l] на $VAL$
```

- Keep **every** concept link: the same concepts, the same number of times. You may switch between `[concept_x]` and `[Concept('concept_x', '…')]` freely, and move links within the sentence.
- A `$reference$` inside a quoted argument carries `|q` (`[Concept('concept_state', '$concept_states|q$')]`). Keep it, and add it to any you write there yourself: the game logs an error for each one without it. A `$reference$` inserts the base game's own Russian text, in the nominative; where the case matters, write the inflected word yourself as the display text instead.
- For a plain `[concept_x]` link, the display text you write must be the concept's own Russian term, inflected; the glossary's REFERENCED KEYS section shows the nominative where it is known. Don't substitute a synonym.
- Where the English already gives its own display text (`[Concept('concept_x', 'construction capacity')]`), translate that text, inflected. The English author chose it on purpose, even when it differs from the concept's name.
- `|l` lowercases a link's rendered name (`[concept_legitimacy|l]`), `|U` capitalises it. Inside a sentence a plain link in the nominative takes `|l`, since Russian doesn't capitalise common nouns; at the start of a sentence it needs nothing.

## Country names: keep `GetName`, put a noun before it

Russian declines country names, and the base game reaches its declined forms through `GetAltName`, but this mod doesn't use them yet: keep `GetName`, `GetNameNoFlag` and `GetNameNoFormatting` exactly as the English has them (never `GetAltName`; the checker rejects it). The name then always renders in the **nominative** («Франция», «Соединённые Штаты»), so phrase the sentence so a nominative fits:

- After a preposition, or in any case but the nominative, put a noun before the name that takes the case instead: *страна*, *государство*, *правительство*, *народ*. The name then stands in apposition, in the nominative, as Russian allows.
- As the subject, a bare name is fine with a present-tense verb, which doesn't show gender. A past-tense verb agrees in gender and number, which you can't know («Франция объявила», «Китай объявил», «Соединённые Штаты объявили»), so either put *страна* before the name and agree with it, or use the present tense.

```
EN  Protect [TARGET_COUNTRY.GetName].
RU  Защитить страну [TARGET_COUNTRY.GetName].

EN  Indian rebels will declare [concept_war] on the [ROOT.GetCountry.GetName]
RU  Индийские повстанцы объявят [Concept('concept_war','войну')] стране [ROOT.GetCountry.GetName]

EN  The [TARGET_COUNTRY.GetName] government has fallen
RU  Правительство страны [TARGET_COUNTRY.GetName] пало

EN  [INITIATOR_COUNTRY.GetName] has [concept_foreign_investment_rights] in [TARGET_COUNTRY.GetName]
RU  Страна [INITIATOR_COUNTRY.GetName] имеет [concept_foreign_investment_rights|l] в стране [TARGET_COUNTRY.GetName]
```

A list or label line ("Leader: [X.GetName]") needs nothing: «Лидер: [X.GetName]».

`GetAdjective` gives the masculine nominative singular, lowercase («французский»). Keep every `GetAdjective` call the English has (the checker counts them, and swapping one for `GetName` is rejected). Put it before a masculine noun the sentence leaves in the nominative singular (*[X.GetAdjective] народ*, *[X.GetAdjective] рынок*, *[X.GetAdjective] капитал*, *[X.GetAdjective] флот*), and rearrange the sentence so that phrase is its subject or stands after a colon, rather than letting it disagree.

The same goes for people. `[CHARACTER.GetFullName]` renders the nominative, and a past-tense verb would show a gender you can't know: put a noun before it that fixes the agreement (*лидер [X.GetFullName] заявил*, *наш правитель*), use the present tense, or keep the name in a label. Keep pronoun calls such as `[CHARACTER.GetHeShe]` or `[CHARACTER.GetHerHis]` where the Russian pronoun goes; they render Russian.

A `$key$` reference that inserts a name (a country tag such as `$CZH$`, a culture, a technology, a building) gives its bare nominative, and nothing can decline it. Phrase around it the same way: «после того как мы образовали государство $CZH$», «Технология $mass_media$ изучена» (not «$mass_media$ изучены»: the name may be of any gender and number), «население культуры $yankee$».

## Numbers and agreement

Numbers, percentages and dates come from markup. Never write a number the English doesn't have.

- A noun after an inserted number (`$N$ years`) would need 1 год / 2 года / 5 лет, which you can't choose. Put the noun first, with a colon or in the genitive plural after a word that governs it, or use a standard abbreviation: «Продолжительность: $N$ мес.», «на $N$ мес.», «групп населения: $N$», «$N$ ед.». Abbreviations: *г.* or *лет* after "years" only where the sentence allows, *мес.*, *дн.*, *нед.*, *тыс.*, *млн*, *ед.*
- Where the English writes a number in the prose, use Russian format: 2,5 for 2.5. Leave a thousands figure as the English writes it (1,000); the merge script puts in the no-break space Russian uses (1 000). Percentages stay closed up: 10%, not 10 %.

## Terminology

The chunk header lists up to three glossaries. Follow them exactly:

- **REFERENCED KEYS** show what a link or `$reference$` in this chunk inserts, in the nominative. Use them to get genders and cases right around the insert.
- **MOD TERMS** are the mod's own names, already translated, and the core base-game terms the Russian memory has settled on. Use the Russian given, inflected as the sentence needs.
- **VANILLA TERMS**, when present, are the official Russian game terms. Where the English refers to that game thing, use the official Russian, not your own synonym. (The first Russian run had no game install, so its chunks have no VANILLA TERMS; use the table below and your knowledge of the official Russian Victoria 3.)

These base-game terms recur everywhere. Use them, inflected, wherever the English means that game thing:

| English | Russian |
|---|---|
| pop / pops | группа населения / группы населения (as a mass noun, *население*) |
| interest group | группа интересов |
| political movement | политическое движение |
| journal entry | запись журнала |
| diplomatic play | дипломатическая игра |
| power bloc | силовой блок (*блок* on its own once it's clear) |
| great / major / minor power | великая / крупная / малая держава |
| subject / overlord | зависимое государство / сюзерен |
| state (map region) | область |
| strategic region | стратегический регион |
| incorporated / unincorporated | включённая / невключённая |
| authority / influence / bureaucracy | авторитет / влияние / бюрократия |
| legitimacy | легитимность |
| radicals / loyalists | радикалы / лоялисты |
| turmoil | беспорядки |
| standard of living | уровень жизни |
| literacy | грамотность |
| infamy | дурная слава |
| prestige | престиж |
| treaty / article / obligation | договор / статья / обязательство |
| leverage | рычаги влияния |
| war goal / war support | цель войны / поддержка войны |
| mobilization / conscription | мобилизация / призыв |
| building / production method | здание / метод производства |
| construction (sector) | строительство (строительный сектор) |
| goods / market | товары / рынок |
| treasury / gold reserves / debt | казна / золотой запас / долг |
| tax / tariff | налог / пошлина |
| law / institution / decree | закон / институт / указ |
| technology / innovation | технология / инновации |
| homeland | историческая родина |
| strata (lower, middle, upper) | слои (низшие, средние, высшие) |
| wealth / wage | богатство / зарплата |
| character / ruler / heir | персонаж / правитель / наследник |
| company | компания |
| United Nations / UN | Организация Объединённых Наций / ООН |

For a term in none of the lists, choose Russian that fits the official game's register, and list it in your report.

The first run settled these mod words too, which are too short or too common for the glossaries to catch:

| English | Russian |
|---|---|
| amendment / bill | поправка / законопроект |
| census | перепись населения |
| the player | игрок |
| a Strategic Reserve hub | узел |
| the Drugs good (vanilla's opium, renamed) | препараты; *лекарства* where the text means medicine, *наркотики* where it means narcotics |
| devastation | опустошение |
| a country's (UN, international) standing | международный авторитет |
| clout (of interest groups) | вес |
| the Tender ship role | суда снабжения |
| Grand Monument(s) | великий монумент (великие монументы) |
| launch window | стартовое окно |

Level and band names read as their labels do, quoted or agreeing with *уровень*: UN authority — Угасающий / Оспариваемый / Устоявшийся / Сильный / Надгосударственный; tradecraft — Необстрелянный / Новичок / Состоявшийся / Опытный / Ветеран; nuclear readiness — пониженная / обычная / усиленная; colonial stability — Упрочена / Стабильна / Напряжена / Рушится / Разваливается; UN standing — Образцовый / Уважаемый / Нейтральный / Плохой / Опозоренный; the UN authority pillars — Участие / Приверженность / Финансирование / Политика / Доверие / Результативность; seabed regimes — Открытый / Регулируемый / Схватка.

Some inserted names have a fixed form to write around: ocean basins (`$te_seabed_basin_*$`) are masculine adjectives, so write «океан» after them («Тихий океан»); the merged cultures (`$cm_*$`) are feminine adjectives agreeing with *культура* («культура $cm_american$»); a power bloc named after its capital is «Лига $X$» or «Пакт $X$».

Names and titles take a capital on the first word only, as Russian writes them: «Свободная торговля», «Силовой блок», «Оружейная промышленность», «Запись журнала». Don't copy English Title Case. Proper names of real organisations follow their official Russian form («Организация Объединённых Наций», «Всемирный банк», «Совет Безопасности»).

Proper names stay as they are, or in their established Russian form: people, places, companies, historical buildings, products. Transliterate a foreign proper name the usual Russian way (Eiffel Tower → «Эйфелева башня», Siemens → «Сименс», but a brand normally written in Latin letters may stay Latin), and translate the descriptive part of a compound name ("Getzner Bludenz Textile Works" → «Текстильная фабрика Гецнер Блуденц»). A generic descriptive name is not a proper name and is translated ("Communist Party" → «Коммунистическая партия», "Technocratic Party" → «Технократическая партия»).

## Voice and style

- **Events** speak for the player's government in the first person plural: «Мы должны …», «наше правительство …». Option buttons are short statements or exclamations in that voice. Flavour text (`.f`) may be literary; keep its tone.
- **Tooltips and descriptions** are impersonal and precise: «Повышает …», «Влияет на …». Where the English addresses the player ("you", "your"), use *вы* and *ваш*, lowercase, never *ты*; *ты* belongs only in quoted dialogue between characters.
- **Names and labels** (modifiers, buildings, laws, buttons, journal entries) stay short. The UI boxes were sized for English, and Russian runs longer. Prefer a compact noun phrase («Контроль капитала») to a paraphrase, and a verbal noun or infinitive for a button («Ввести», «Отменить»).
- Write *ё* where the word has it (её, ещё, всё, объединённый).
- Dialogue and asides use the em dash with spaces ( — ), as Russian prints them.
- Keep the English meaning, including hedges and conditions («до», «не более», «при условии, что …»). Don't add explanations the English doesn't give.
