"""The roster of the assimilation cultures: which languages and heritage groups get a hybrid culture.

A hybrid (``hc_<language>_<group>``, ``hc_anglophone_african``) is the culture a pop of one heritage group
takes when it assimilates under a host of another and the game rule keeps its heritage: it speaks the host's
language and keeps its own heritage group (docs/superpowers/specs/2026-11-25-assimilation-cultures-design.md
§ The cultures). ``gen_assimilation_cultures.py`` writes one for every roster language and every group but the
one group that is the language's own cultures' only group (German needs no European hybrid).

The roster is the single source, a line a language:

* ``COUNTED``: the 30 languages with the most people living under them in 1836, together with the 30 with
  the most speakers, 39 in all. ``scripts/analysis/assimilation_cultures_roster.py`` repeats the count where
  the game is installed and says when the list no longer matches it.
* ``HAND``: the 20 the owner added (2026-11-25), most of them for Africa, which vanilla splits into about 60
  languages none large enough for either count but Fulani and Hausa, and three for the Americas.
* ``merge_languages``: the five languages the tier-2 culture merges mint (``language_cm_latin`` ...), read
  from the merge plan, never typed in.

Every other field is derived. A hybrid takes its name lists and religion from its language's
``names_from`` (the language's largest culture by 1836 population, or for a merge language the merge's
result) and its ethnicities and graphics from its group's ``looks_from`` (the group's largest 1836 culture
with one plain ethnicity). Its name is spliced from vanilla's names for the language and the group, or the
row's ``word`` where vanilla's is a linguist's ("Oghuz European" reads "Turkic European").

The hybrids' heritage is one diaspora trait for each group, minted in vanilla's group
(``heritage_hc_east_asian`` in ``heritage_group_east_asian``), except that the African hybrids take vanilla's
own ``heritage_african_diaspora``, Afro-American's trait. No group is made for Promethean, which one culture
has.

Vanilla comes from the committed ``vanilla_parsed/`` snapshot through ``gen_culture_merges.load_vanilla``,
and the merge results from ``gen_culture_merges.build_plan``.
"""

from __future__ import annotations

from dataclasses import dataclass

import culture_merges_config as cm_cfg


@dataclass(frozen=True)
class Language:
    key: str                 # trait key less "language_": "anglophone", "cm_latin"
    names_from: str          # culture whose name lists and religion the hybrids take
    word: str | None = None  # the hybrids' word for the language where vanilla's sounds bad


@dataclass(frozen=True)
class Group:
    key: str                 # group key less "heritage_group_": "african"
    heritage: str            # the heritage trait its hybrids carry
    looks_from: str          # culture whose ethnicities and graphics they take
    word: str | None = None


@dataclass(frozen=True)
class Pair:
    language: Language
    group: Group
    culture: str             # "hc_<language.key>_<group.key>"


L = Language

# The count: the 30 languages most people lived under in 1836 and the 30 most spoken, by trait key.
COUNTED: tuple[Language, ...] = (
    L("anglophone", "british"),
    L("arabic", "maghrebi"),
    L("berber", "berber"),
    L("dutch", "dutch"),
    L("east_slavic", "russian"),
    L("eastern_romance", "romanian", word="Romanian"),
    L("francophone", "french"),
    L("fulani", "fulbe"),
    L("gaelic", "irish"),
    L("germanophone", "north_german"),
    L("hakka", "hakka"),
    L("hausa", "hausa"),
    L("hindustani", "hindustani"),
    L("hispanophone", "spanish"),
    L("hungarian", "hungarian"),
    L("italian", "north_italian"),
    L("japanese", "japanese"),
    L("jurchenic", "manchu", word="Manchu"),
    L("korean", "korean"),
    L("lusophone", "portuguese"),
    L("magadhan", "bengali", word="Bengali"),
    L("malay", "javan"),
    L("mandarin", "han"),
    L("min", "min"),
    L("northwestern_indic", "panjabi", word="Punjabi"),
    L("occitano_romance", "occitan", word="Occitan"),
    L("oghuz", "turkish", word="Turkic"),
    L("pahari", "nepali", word="Nepali"),
    L("persian", "persian"),
    L("scandinavian", "swedish"),
    L("siamese", "thai", word="Thai"),
    L("south_central", "telegu", word="Telugu"),
    L("southern_indic", "marathi", word="Marathi"),
    L("tamil_tulu", "tamil", word="Tamil"),
    L("tibetan", "tibetan"),
    L("vietic", "vietnamese", word="Vietnamese"),
    L("west_slavic", "polish"),
    L("western_indic", "rajput"),
    L("yue", "yue", word="Cantonese"),
)

# The owner's additions (2026-11-25): Europe, Southeast Asia, Africa (Ethiopia's three primary cultures, Mali's two
# languages), the Americas.
HAND: tuple[Language, ...] = (
    L("greek", "greek"),
    L("south_slavic", "serb"),
    L("philippinic", "visayan", word="Filipino"),
    L("amharic", "amhara"),
    L("burmic", "burmese", word="Burmese"),
    L("galla", "oromo", word="Oromo"),  # vanilla's "Galla" is a name the Oromo reject
    L("tigrinya", "tigray"),
    L("somali", "somali"),
    L("lacustrine_bantu", "lacustrine_bantu", word="Great Lakes Bantu"),
    L("equatorial_bantu", "equatorial_bantu"),
    L("nguni", "nguni"),
    L("swahili", "swahili"),
    L("yoruba", "yoruba"),
    L("quechuan", "quechua", word="Quechua"),
    L("guarani", "guarani"),
    L("siouan", "siouan"),
    L("akan", "akan"),
    L("malagasy", "malagasy"),
    L("mande", "mande"),
    L("manding", "bambara"),
)

del L

# Every heritage group a vanilla culture has but Promethean. ``looks_from`` is the group's largest 1836 culture with
# one plain ethnicity (Turkish, the largest Middle Eastern one, mixes two).
GROUPS: tuple[Group, ...] = (
    Group("african", "heritage_african_diaspora", "hausa"),
    Group("central_asian", "heritage_hc_central_asian", "uzbek"),
    Group("east_asian", "heritage_hc_east_asian", "han"),
    Group("european", "heritage_hc_european", "north_german"),
    Group("indigenous_american", "heritage_hc_indigenous_american", "quechua"),
    Group("indigenous_oceanic", "heritage_hc_indigenous_oceanic", "melanesian"),
    Group("middle_eastern", "heritage_hc_middle_eastern", "maghrebi"),
    Group("north_asian", "heritage_hc_north_asian", "manchu"),
    Group("south_asian", "heritage_hc_south_asian", "bengali"),
    Group("southeast_asian", "heritage_hc_southeast_asian", "javan"),
)

# The hybrid whose existence tells the script the cultures are loaded (a game begun before them has none).
SENTINEL = "hc_anglophone_african"

PREFIX = "hc_"
MINTED_HERITAGE_PREFIX = "heritage_hc_"
LANGUAGE_PREFIX = "language_"
GROUP_PREFIX = "heritage_group_"


def merge_languages(plan) -> tuple[Language, ...]:
    """One language per language trait a culture merge mints, in plan order; its names come from the merge's result."""
    return tuple(
        Language(trait.key.removeprefix(LANGUAGE_PREFIX), entry.merge.result)
        for entry in plan
        for trait in entry.traits
        if trait.kind == "language"
    )


def languages(plan) -> tuple[Language, ...]:
    """The roster in its order: the counted languages, the owner's, then the merges'."""
    return COUNTED + HAND + merge_languages(plan)


def _bodies(cultures: dict, plan) -> dict:
    """Every culture's fields by id: vanilla's, then each merge result's."""
    bodies = {c: cm_cfg.unwrap(body) for c, body in cultures.items() if c != cm_cfg.TRAITS_KEY}
    bodies.update((entry.merge.result, entry.fields) for entry in plan)
    return bodies


def _trait_groups(cultures: dict, plan) -> dict[str, str]:
    """trait key -> trait group, for vanilla's traits and those the merges mint."""
    groups = {}
    for key in cm_cfg.unwrap(cultures.get(cm_cfg.TRAITS_KEY)) or {}:
        group = cm_cfg.trait_group(key, cultures)
        if group is not None:
            groups[key] = group
    for entry in plan:
        for trait in entry.traits:
            groups[trait.key] = trait.group
    return groups


def _language_of(body) -> str | None:
    value = cm_cfg.unwrap(body.get("language")) if isinstance(body, dict) else None
    return value if isinstance(value, str) else None


def _group_of(body, trait_groups: dict[str, str]) -> str | None:
    """A culture's heritage group key (``european``), or None."""
    heritage = cm_cfg.unwrap(body.get("heritage")) if isinstance(body, dict) else None
    group = trait_groups.get(heritage) if isinstance(heritage, str) else None
    return group.removeprefix(GROUP_PREFIX) if group else None


def language_groups(language: Language, cultures: dict, plan) -> frozenset[str]:
    """The heritage group keys of every culture that speaks ``language``, the merges' results included."""
    trait_groups = _trait_groups(cultures, plan)
    trait = LANGUAGE_PREFIX + language.key
    return frozenset(
        group
        for body in _bodies(cultures, plan).values()
        if _language_of(body) == trait and (group := _group_of(body, trait_groups)) is not None
    )


def _pairs(cultures: dict, plan) -> tuple[Pair, ...]:
    out = []
    for language in languages(plan):
        own = language_groups(language, cultures, plan)
        for group in GROUPS:
            if own == {group.key}:
                continue
            out.append(Pair(language, group, f"{PREFIX}{language.key}_{group.key}"))
    return tuple(out)


def pairs(cultures: dict, plan) -> tuple[Pair, ...]:
    """Every hybrid in roster order: each language's, its groups in ``GROUPS`` order, less its own only group.

    Raises ValueError for a roster ``validate`` rejects.
    """
    validate(cultures, plan)
    return _pairs(cultures, plan)


def minted_heritages() -> tuple[tuple[str, str], ...]:
    """(trait key, group key) for each group whose hybrids carry a heritage trait of the mod's own."""
    return tuple((group.heritage, group.key) for group in GROUPS if group.heritage.startswith(MINTED_HERITAGE_PREFIX))


def _check_word(errors: list[str], who: str, word: str | None) -> None:
    if word is None:
        return
    if not word.strip():
        errors.append(f"{who}: an empty word")
    if '"' in word or "\n" in word or "$" in word:
        errors.append(f"{who}: the word {word!r} holds a quote mark, a line break or a $")


def validate(cultures: dict, plan) -> None:
    """Raise ValueError naming every broken row of the roster.

    A language vanilla (or a merge) lacks; a ``names_from`` that is no culture or speaks another language; a
    group vanilla lacks, or Promethean; a ``looks_from`` that is no vanilla culture or is of another group; a
    heritage that is neither vanilla's trait of the group nor ``heritage_hc_<group>``, or a minted one vanilla
    already defines; a key twice; a hybrid key that is a vanilla or merge culture; a word holding a quote mark.
    """
    errors: list[str] = []
    traits = cm_cfg.unwrap(cultures.get(cm_cfg.TRAITS_KEY)) or {}
    trait_groups = _trait_groups(cultures, plan)
    bodies = _bodies(cultures, plan)
    minted_languages = {trait.key for entry in plan for trait in entry.traits if trait.kind == "language"}

    def kind_of(trait: str) -> str | None:
        entry = cm_cfg.unwrap(traits.get(trait))
        value = cm_cfg.unwrap(entry.get("type")) if isinstance(entry, dict) else None
        return value if isinstance(value, str) else None

    seen_languages: set[str] = set()
    for language in languages(plan):
        who = f"language {language.key}"
        if language.key in seen_languages:
            errors.append(f"{who}: listed twice")
        seen_languages.add(language.key)
        trait = LANGUAGE_PREFIX + language.key
        if kind_of(trait) != "language" and trait not in minted_languages:
            errors.append(f"{who}: vanilla lacks the language trait {trait}")
        source = bodies.get(language.names_from)
        if source is None:
            errors.append(f"{who}: names_from {language.names_from} is no culture")
        elif _language_of(source) != trait:
            errors.append(f"{who}: names_from {language.names_from} speaks {_language_of(source)}")
        _check_word(errors, who, language.word)

    vanilla_groups = {group.removeprefix(GROUP_PREFIX) for group in trait_groups.values() if group.startswith(GROUP_PREFIX)}
    seen_groups: set[str] = set()
    for group in GROUPS:
        who = f"group {group.key}"
        if group.key in seen_groups:
            errors.append(f"{who}: listed twice")
        seen_groups.add(group.key)
        if group.key not in vanilla_groups or group.key == "promethean":
            errors.append(f"{who}: not a heritage group a hybrid can have")
        if group.heritage.startswith(MINTED_HERITAGE_PREFIX):
            if group.heritage != MINTED_HERITAGE_PREFIX + group.key:
                errors.append(f"{who}: a minted heritage is {MINTED_HERITAGE_PREFIX}{group.key}, not {group.heritage}")
            if group.heritage in traits:
                errors.append(f"{who}: vanilla already defines the heritage {group.heritage}")
        elif kind_of(group.heritage) != "heritage" or trait_groups.get(group.heritage) != GROUP_PREFIX + group.key:
            errors.append(f"{who}: heritage {group.heritage} is no vanilla heritage trait of the group")
        source = cultures.get(group.looks_from)
        if source is None:
            errors.append(f"{who}: looks_from {group.looks_from} is no vanilla culture")
        elif _group_of(cm_cfg.unwrap(source), trait_groups) != group.key:
            errors.append(f"{who}: looks_from {group.looks_from} is not in the group")
        _check_word(errors, who, group.word)

    seen_cultures: set[str] = set()
    for pair in _pairs(cultures, plan):
        if pair.culture in seen_cultures:
            errors.append(f"{pair.culture}: made twice")
        seen_cultures.add(pair.culture)
        if pair.culture in bodies:
            errors.append(f"{pair.culture}: already a vanilla or merge culture")
    if errors:
        raise ValueError("the assimilation culture roster is invalid:\n  " + "\n  ".join(errors))
