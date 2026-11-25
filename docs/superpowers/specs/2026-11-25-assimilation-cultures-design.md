# Assimilation cultures: heritage as a limit on assimilation, behind a game rule

Status: design draft, 2026-11-25. The owner answered the draft's questions the same day (§ Decided) and approved the design with the roster below ("I'm happy with the spec with those added!"). Nothing is built.

## Why

Before 1.12 the mod had a rule that a pop could not assimilate into a culture of another heritage. It took up the country's language instead, by moving into a generated culture that kept its own heritage: an African-heritage pop in an English-speaking country became `anglo_african`. The rule went with the 1.12 update (commit e6538d6f), when the define it stood on left the game.

This design brings the rule back behind a game rule, and makes the Bodily Autonomy laws what opens assimilation across heritage: when appearance can be chosen, heritage stops being a barrier to joining the majority.

## What the groundwork found

Five things differ from what the brief assumed.

1. **The define is gone; two replaced it.** `ALLOW_ASSIMILATION_ACROSS_HERITAGES` is not in 1.15.2's `00_defines.txt`, nor in 1.12.4's, the oldest version in the mirror. `NPops` has instead, both `no` by default:
   - `ALLOW_ASSIMILATION_REQUIRE_HERITAGE_GROUP`: "pops can only assimilate into cultures whose heritage trait is in the same heritage group as theirs (slaves always follow this rule)".
   - `ALLOW_ASSIMILATION_REQUIRE_HERITAGE_TRAIT`: the stricter form, the same heritage trait.
   - And a comment: "These rules only filter the cultures tied for the highest acceptance in the state; if none of them qualifies, the pop does not assimilate". So the engine's target is the most accepted culture present in the state, which need not be "the primary culture".

   This is read from the game files. What the define does in play is unverified (§ Unverified).
2. **The old heritages are today's heritage groups.** 1.15 has 110 heritage traits in 11 groups (African, Central Asian, East Asian, European, Indigenous American, Indigenous Oceanic, Middle Eastern, North Asian, South Asian, Southeast Asian, and Promethean, which one culture has) and 198 language traits. The old script's nine heritages (`african_heritage`, `east_asian_heritage`) match the groups, and its `anglophone` is now `language_anglophone`. The triggers it needs exist: `has_discrimination_trait`, `has_discrimination_trait_group`, `shares_heritage_trait_group_with_any_primary_culture`.
3. **Who may assimilate is already on the mod's laws.** The engine reads `country_allow_assimilation_<status>_bool` and `country_assimilation_<status>_mult` for each of the five acceptance statuses, and the mod's seven Minority Rights laws set them (table in § The pass). The old script's own test, acceptance of at least 20 and no Violent Hostility or Ghettoization, has an engine form now.
4. **The old generator was moved, not deleted.** `scripts/generators/assimilation_cultures.py` is still there (2,341 lines, mostly name lists typed in per language, unused since 1.12). Its rate, `pop_culture_conversion_propotion_script_value`, is still in `extra_script_values.txt` with no caller.
5. **A culture costs more than its definition.** The engine expects six static modifiers and three modifier types of every culture, which Culture Merges generates for its 21. A hybrid for every vanilla language and group would be 1,782 cultures beside vanilla's 322.

## Goals, non-goals, anti-goals

Goals:

- With the rule on, assimilation never changes a pop's heritage group until a Bodily Autonomy law allows it. A pop of another heritage group takes up the language and keeps its heritage.
- Under Unrestricted, a game assimilates as vanilla does, as nearly as script can.
- The Bodily Autonomy laws open the heritage step, and still stand on their present lines under Unrestricted.
- A cost of at most one pop walk per state per year.

Non-goals:

- A hybrid culture as a Culture Merge part, a homeland for a hybrid, a journal entry or a panel. A card on the state overview that shows the year's scripted assimilation is a possible later addition (the owner: "we can potentially add a card to the state overview panel if we want to make it more visible"), not part of this build.
- Patching vanilla content that counts a primary culture's share of a state where the minority is of another heritage group (the Algerian departments, Goa). Under Hybrid Cultures those pops become French-speaking, not French, and the share stops rising.
- Hybrids for languages outside the roster (§ The cultures): their countries are treated as under None.

Anti-goals:

- A leak: pops still assimilating across heritage, by the engine, under Hybrid Cultures or None.
- An Unrestricted game that plays noticeably unlike vanilla for a player who never touched the rule.
- A block of script per language-and-heritage pair, or anything run for every state every month.

## Approaches considered

1. **The group define on for everyone, and one scripted pass that does all assimilation across heritage groups under every setting** (chosen by the owner, 2026-11-25: "I like it with the rule"). The engine keeps every assimilation within a heritage group, as now. Across groups it does nothing, and script converts: into the hybrid under Hybrid Cultures, into the majority primary culture under Unrestricted, and under None not at all until a law allows it. One pass, branching on the rule. Its cost is that Unrestricted is an imitation of the engine, not the engine (§ What Unrestricted gets wrong).
2. **No rule: the define on and hybrids for everyone**, as before 1.12. Nothing to imitate, and half the testing. No way out for a player who dislikes it, and the brief asks for a rule.
3. **The define untouched, and script that gets to a pop before the engine does.** Off would then be vanilla itself, with no script at all. Rejected: nothing switches the engine's assimilation off for some pops of a state and not others (the levers are per state or per acceptance status), so with the rule on the engine would keep moving the same pops straight into the majority culture, a tenth to a fifth of them a year in a late game.
4. **The heritage trait define** instead of the group one. Rejected: it would stop a Pole assimilating in Germany, and the hybrids would number 110 heritages times the languages. The group is the old rule's grain.

## The design

### The define

`ALLOW_ASSIMILATION_REQUIRE_HERITAGE_GROUP = yes` in `extra_defines.txt`, in place of the dead commented line. It applies to every game on the mod, whatever the rule says and whenever the game began: a define is read at load.

### The cultures

- **One hybrid for each roster language and heritage group**, `hc_<language>_<group>` (`hc_anglophone_african`), less the group that is the only one the language's own cultures have: German needs no European hybrid. The prefix is for the reason `cm_` has one.
- **Roster**, a list in the generator's config, where a language is one line. The rule: the 30 languages with the most people living under them in 1836 together with the 30 with the most speakers, 39 in all, since a count by rulers alone misses the languages of colonized peoples (Bengali's language is second in the world by speakers and 70th by rulers). The count was taken over every country in the 1836 history, the 158 decentralized nations among them. To those the owner added 20 by hand (2026-11-25), most of them for Africa, which vanilla splits into about 60 languages, none large enough to make either count but Fulani and Hausa; and three for the Americas. The mod's formables are why they matter: the African Union lists 49 primary cultures and the East African Federation 18, and under the majority rule each state's host is its largest one. With the five languages the tier-2 merges mint (`language_cm_latin` and its kin) the roster is 64 languages and 584 cultures (539 for the 59 vanilla languages, and nine for each merge language, whose one culture has one heritage group), covering 90% of 1836's people by the language they speak. Considered and left out: Fluvial Bantu, which only five decentralized nations hold and no formable lists. Every language that is primary somewhere in 1836 would be 130 languages and about 1,220 cultures; every language, 1,782.

  | Region | Languages (vanilla's name, then its main cultures) |
  |---|---|
  | Europe | Anglophone (English, Yankee, Dixie, Scottish), Germanophone, Francophone, Hispanophone (Spanish, Mexican and 17 more), Lusophone (Portuguese, Brazilian), Italian, Dutch (Dutch, Flemish, Boer), East Slavic (Russian, Ukrainian, Byelorussian), West Slavic (Polish, Czech, Slovak), Scandinavian, Hungarian, Eastern Romance (Romanian), Occitano-Romance (Occitan, Catalan), Gaelic (Irish, Gael); by hand: Greek, South Slavic (Serbian, Croatian, Bosniak) |
  | Middle East, North Africa | Arabic, Oghuz (Turkish, Azerbaijani, Turkmen), Persian, Berber |
  | South Asia | Hindustani, Magadhan (Bengali, Bihari, Oria), Tamil-Tulu (Tamil, Kannada, Malayalam), Southern Indic (Marathi, Sinhala), Western Indic (Rajput, Gujarati), Northwestern Indic (Punjabi, Sindi), South-Central (Telugu, Gondi), Pahari (Nepali) |
  | East Asia | Mandarin (Han), Yue, Min, Hakka, Jurchenic (Manchu), Japanese, Korean, Tibetan |
  | Southeast Asia | Malay (Javan, Malay, Sumatran), Vietic (Vietnamese), Siamese (Thai); by hand: Philippinic (Tagalog, Visayan), Burmic (Burmese) |
  | Africa | Fulani, Hausa; by hand: Amharic, Oromo (vanilla's `language_galla`) and Tigrinya, which are Ethiopia's three primary cultures, Somali, Lacustrine Bantu (Baganda, Ruanda, Rundi), Equatorial Bantu, Nguni (Zulu, Xhosa), Swahili, Yoruba, Akan (Ashanti), Malagasy, Mande and Manding (Bambara), the two languages of vanilla's Mali |
  | The Americas | by hand: Quechuan (Quechua), Guarani (a primary culture of Paraguay), Siouan (Lakota, Dakota) |
- **Traits.** The language is the host's. The heritage is one diaspora trait for each group, minted in vanilla's group (`heritage_hc_east_asian` in `heritage_group_east_asian`), except that the African hybrids use vanilla's `heritage_african_diaspora`, Afro-American's own trait.
- **Name**, spliced from vanilla's own names for the language and the group, so it follows any rename or translation: `$language_anglophone$ $heritage_group_african$` reads "Anglophone African"; "Lusophone East Asian", "Mandarin European". Where vanilla's word is a linguist's ("Oghuz European", "Jurchenic African", "Eastern Romance African"), the config gives that language or group a word of its own for the hybrids' names ("Turkic", "Manchu", "Romanian"), by the owner's rule: "we should try to make them sound good if there are any cases where the default rule makes something that sounds bad". Vanilla's "Galla" is a name the Oromo reject, so those hybrids say "Oromo". The build's PR lists every name for a read-through.
- **Other fields**, derived, none typed in: name lists and religion from the language's largest culture by 1836 population; ethnicities and graphics from the group's largest; a color between the two; no traditions, obsessions or homelands. The six static modifiers and three modifier types come from the functions `gen_culture_merges.py` already has, opened to take a list of culture keys.
- They exist from 1836 with no pops, under every setting of the rule: a culture can't be gated at load.

**What a hybrid gains.** In 1.15 a culture's acceptance in a country comes from the traits it shares with that country's primary cultures; cultures do not accept each other. A hybrid shares the language trait and nothing of heritage, so it gains the citizenship law's figure for a shared language and keeps the figure for no shared heritage. The brief's question about hybrids accepting each other has no object in this engine. It becomes the choice of heritage trait above.

### The pass

One hand-written effect, run for each of a country's states from that country's yearly pulse (the engine spreads the countries' pulses over the year), under every setting.

1. **Skip** a state where no culture of another heritage group lives (`any_scope_culture`, which walks the state's cultures, not its pops).
2. **The host culture** of the state is the majority primary culture (the owner's correction, 2026-11-25): the owner's primary culture with the most people in that state. It sets both the language a hybrid takes and the culture a pop joins. No primary culture present: nothing converts, as in the engine, unless the state carries `state_allow_assimilation_without_presence_bool`. So Quebec's host is Franco-Canadian and Ontario's Anglo-Canadian. Counting costs one more pop walk for each primary culture, and only where the owner has more than one.
3. **One walk of the state's pops.** A pop is taken when:
   - its culture shares no heritage group with any primary culture of the owner;
   - the state is not a homeland of its culture, or carries `state_allow_assimilation_in_homeland_bool`;
   - the owner's laws let its acceptance status assimilate (`country_allow_assimilation_<status>_bool`).

   Under Ancestral Citizenship (`law_ethnostate`) no pop joins a culture of another heritage group, under any setting and whatever the Bodily Autonomy law (owner, 2026-11-25). The law carries a bool the pass reads, `country_cross_heritage_assimilation_blocked_bool`, so its tooltip says so. The language step still runs there. Under Unrestricted, where every conversion crosses heritage, that leaves nothing: an Ancestral Citizenship country assimilates only within its heritage group, which is not vanilla's behavior; the owner kept it ("let's keep, I think it is good"). Within a group the engine runs assimilation and no law can filter it by heritage trait; that is left to acceptance, where the law already puts a pop sharing only the group 20 points below one sharing the trait.

   | Minority Rights law | Statuses that assimilate |
   |---|---|
   | Violent Hostility | Open Prejudice and above |
   | Ghettoization | Second-class Citizen and Full Acceptance |
   | Discrimination, Indifference | Cultural Erasure and above |
   | Cultural Assimilation, Protection, Affirmative Action | all five |

4. **What it becomes:**

   | The pop | Hybrid Cultures | Unrestricted | None |
   |---|---|---|---|
   | does not speak the host's language | the hybrid of the host's language and its own heritage group (the language step) | the host culture | the host culture, at the rate times the crossing share |
   | speaks it: a hybrid, or a vanilla culture such as Afro-American under a Yankee host | the host culture (the heritage step), at the rate times the crossing share | the host culture | the same |

   The crossing share is the country's `country_cross_heritage_assimilation_add`, 0 without a Bodily Autonomy law. So None is Hybrid Cultures without the hybrids (owner, 2026-11-25): a wall until a law opens it, then straight across. A host whose language is off the roster is treated as under None (my call, which the owner approved), so that a Bodily Autonomy law opens the wall there too.

5. **The rate**, the fraction of the pop that converts that year: 12 × 0.002 (the engine's monthly `ASSIMILATION_RATE`) × (1 + the state's `state_assimilation_mult`) × (1 + the owner's `country_assimilation_<status>_mult`), each factor no lower than 0, × (1 − the pop's radical share) × the culture's fervor factor (the mod's define, 0.0075 a point) × 0.75 in a homeland, capped at one half. It reads the engine's own sums, so every law, institution, decree and Cultural Hegemony bonus that speeds assimilation speeds this, with no second list to keep. With no modifiers that is 2.4% a year, half a community in 29 years; at the +690% of the owner's 2039 New York it is 19% a year.
6. **The hybrids' scopes**, under Hybrid Cultures: a generated ladder with one branch per roster language tests the host's language trait once per state and saves that language's ten hybrids, each behind `exists = cu:<hybrid>`. It is the only generated script; the pass itself is written by hand, and its conversions name the saved scopes.

Cost: the old pulse ran about 300 blocks for every state every month, and two pop walks for each block that matched the owner's language. This is one culture test per state per year, and one pop walk in a state that passes it.

**Slaves** *(my call)*. Under Hybrid Cultures a slave pop takes the language step and never the heritage step: it is what the engine's exception protects, and what Afro-Brazilian is. Under Unrestricted slaves are left out, as the engine leaves them.

### The rule

- **"Assimilation Across Heritages"**, three settings (the third is the owner's, 2026-11-25: "a disabled rule, where there is just no assimilation across heritage groups"):
  - **Hybrid Cultures**: the language step, and the heritage step once a law opens it.
  - **Unrestricted**: the imitation of vanilla. The default in the release that adds the rule; Hybrid Cultures becomes the default once an observer run and a played game have been read.
  - **None**: Hybrid Cultures without the hybrids. No pop changes heritage group by assimilation until a Bodily Autonomy law opens it, and then it joins the host culture directly.
- **Key** `assimilation_cultures_rule`, settings `assimilation_cultures_hybrid`, `assimilation_cultures_unrestricted` and `assimilation_cultures_none`. Each branch is a positive test of its own setting, and the hybrid branch also asks `exists = cu:hc_anglophone_african`; a game that names none of the three takes the Unrestricted branch.
- **A game begun before the cultures existed** has no object for them and lists no setting for the rule. It goes on assimilating across heritage as it did, through the Unrestricted branch, and no hybrid is ever named.
- **Changed mid-game**: nothing to tear down, since the system keeps no modifier, variable or journal entry. Hybrid pops stay hybrids. Under Unrestricted they are ordinary pops of another heritage group from the next pass, so they drain into the host culture at the yearly rate; under None they stay as they are until a law opens the wall. Back on Hybrid Cultures, the language step resumes.

### The Bodily Autonomy laws

A new script-only modifier, `country_cross_heritage_assimilation_add` ("Assimilation Across Heritages", a percentage, read capped at 100%), on four of the five laws. It is the share of the normal rate at which the heritage step runs, and each law's present assimilation line then speeds or slows both steps, because the rate reads it:

| Law | New line | Its present line | Language step, heritage step a year: a state at +100% | at +690% |
|---|---|---|---|---|
| Natural Form | none | none | 4.8%, closed | 19.0%, closed |
| Licensed Modification | +50% | none | 4.8%, 2.4% | 19.0%, 9.5% |
| Morphological Freedom | +100% | assimilation −100% | 2.4%, 2.4% | 16.6%, 16.6% |
| Clade Citizenship | +100% | assimilation −300% | none, none | 11.8%, 11.8% |
| Prescribed Form | +100% | assimilation +200% | 9.6%, 9.6% | 23.8%, 23.8% |

The rates are before a pop's own factors (status, radicals, fervor). This is the brief's table with one lever in place of five rules. So under Licensed Modification a pop crosses heritage at half the speed it would assimilate at if it shared the host's heritage group, in the same state and at the same acceptance status; under the other three at the same speed. "Prescribed Form faster" and "Clade Citizenship at its reduced rate" come from lines the laws already carry. Under Unrestricted the new line does nothing and its description says so; the other lines act as they do today.

### Culture Merges

- **Two grains of one idea.** A merge works on named peoples in their homelands, from a roster. This works on everyone else, by trait. A merge's tier 1b (Afro-American joining American) is the heritage step taken early for one named culture, on its own gates.
- **A hybrid is never a merge part.** A merge measures everything in a part's homeland states, and a hybrid has none. The roster and its validation don't change.
- **When a host's cultures merge.** A tier-1 or absorbing merge keeps the language, so its hybrids are unaffected; the state's host passes from the part to the result at the switch, since a host must have people in the state. The five tier-2 merges mint a language: after the switch the old hybrids no longer speak the host's language and take the language step again, at the yearly rate, into the new language's hybrids. That is why those five languages are in the roster.
- **A part of another heritage group than its host** (Afro-American) can be converted by both systems. They don't conflict: a merge converts it into the result, and this into the host, which the merge then converts into the result.
- **`test_culture_merge_mod_refs.py`** asks that a test naming a part also names what the part merges into. This system names no vanilla culture in script, only traits and `hc_` cultures, so it asks nothing, and a test of the system's own holds it to that. Its generated file must stay free of part names, or the pinned set of generated restatements fails.
- The play-test row for the `cm_` cultures (24 mod files iterate cultures; do any divide by, average over or list the empty ones) now covers 584 more.

## What Unrestricted gets wrong

Compared with the engine doing the same assimilation itself:

- **Once a year, not monthly**: a step on each country's yearly pulse, and a slightly different total, since twelve monthly steps compound.
- **Nothing in the interface.** The pop panel's "assimilating into" line and `has_ongoing_assimilation` stay empty for these pops. No vanilla or mod script reads that trigger today.
- **The target.** The host culture by the rule above, where the engine takes the most accepted culture present, which under generous laws can be one that is not primary.
- **`country_assimilation_delta_threshold_add`** is not imitated: its base value is in no define, so how much more accepted the target must be is unknown. Affirmative Action carries −100 of it. A row on the play-test list.
- **The fervor factor** is a guess at the formula from the define's comment.
- **The engine's minimum of one person a month** has no counterpart; a pop too small for a fraction converts whole.

## Unverified

Self-checks, once a game, `TE_SELF_CHECK OK|BROKEN <name>` with the numbers:

| Name | What it reads | If BROKEN |
|---|---|---|
| `hc_define_blocks` | 30 days into a new game, before the first pass has run: some pop of its owner's heritage group has an ongoing assimilation (so the trigger is known to read), and no pop of another group has | the define does not do what its comment says; the rule ships hidden and off until it is read by hand |
| `hc_rate_inputs` | from pop scope, the state's assimilation sum includes a law of the owner's, and the status switches read as the law in force sets them | read the country's sum and add the state's own; a `has_law` ladder for the switches |
| `hc_scoped_target` | `change_pop_culture` with a saved scope as its target moved the people (the mod does this in two places; vanilla always names the culture) | a generated ladder of literal culture names |

Play-test rows, in `docs/testing/assimilation-cultures-playtest.md`: the spliced names in the culture panel; whether a later pass merges into the hybrid pop an earlier one made (Culture Merges' pending `cm_conversion_merges_pops`); load time and the monthly tick with the extra cultures; the engine assimilating a pop into a hybrid of its own group that ties for the highest acceptance (harmless, the same direction); an old save.

## Decided

The owner, 2026-11-25, on the draft's eight questions:

1. **The shape**: the rule, with script doing the work across heritage groups ("I like it with the rule").
2. **Name and default**: as recommended, with a third setting, None (§ The rule).
3. **Which pairs get a culture**: a config roster, listed in § The cultures, with 20 languages added by hand over three rounds; Jurchenic, Occitano-Romance and Gaelic, which I offered to drop, stay ("yes, keep").
4. **Who may convert**: the Minority Rights laws' per-status switches.
5. **The hybrids' heritage trait**: one diaspora trait per group, the African one vanilla's own.
6. **The names**: spliced, with a word of the mod's own where vanilla's sounds bad.
7. **The law table**: as drawn, the conversion reading the state's assimilation modifier.
8. **The heritage step takes any culture that speaks the host's language**, not only a generated hybrid.

Also the owner's: the host is the majority primary culture; the imitation's differences from the engine are acceptable ("That's fine"); Ancestral Citizenship blocks joining a culture of another heritage group ("Good idea - agreed"); None "is hybrid cultures without the hybrids".

Calls of mine the owner has seen and approved ("good"): the group define, not the trait one; slaves take the language step only; the host counted per state; no patch for vanilla's share tests.

## Left to the build

A fresh reviewer reads this file before the plan is written.

- The generator `scripts/generators/gen_assimilation_cultures.py` and its config, reading `vanilla_parsed/` and `culture_merges_config.py`, never the live mod state; in `POST_LOAD_REGENERATORS` before `organize_loc`, `docs/auto_generated_files.md` and `scripts/nightly_audit_select.py`. The old `assimilation_cultures.py` and the orphaned script value are deleted.
- The pass and its values by hand (`te_hc_*`), each engine figure it restates (`ASSIMILATION_RATE`, the fervor effect, the homeland factor) pinned to the define files by a test that runs where the game is installed.
- The two modifier types, the four Bodily Autonomy lines and Ancestral Citizenship's, the rule and its loc; `organize_loc.py`.
- Tests: the roster and its derived fields; every hybrid's nine expected entries; the ladder against the roster; the pass's branches through a small interpreter, as Culture Merges tests its own; no vanilla culture named in the system's files.
- A system doc in `docs/systems/mod_systems/` with its index row; the play-test list; the player guide (the rule in `01-introduction.md`'s table, the mechanics beside Culture Merges in `08-states.md`, the law lines where the Bodily Autonomy laws are listed).
