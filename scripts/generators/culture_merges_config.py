"""The roster of culture merges: which cultures merge into which, and how closely.

A merge turns a set of closely related cultures (North and South German) into
one national culture (docs/superpowers/specs/2026-11-07-culture-merges-design.md).
This module is the single source the generator and the dispatch script read.

Conventions
-----------
* A **part** is a slot of one or more alternative culture ids. Usually one id.
  Anglophone's second core slot holds ``("yankee", "cm_american")``: Yankee until
  the American merge finishes, its result afterwards.
* **A merged part is represented by its result** (spec section 3). Two merges that
  share a slot culture are a lower and a higher one, and the lower one's result is
  a slot culture of the higher one, so that once the lower merge has switched the
  shared parts the higher one still takes them. A shared core part takes that result
  as an alternative in its own slot (Anglophone's Yankee); an optional one is covered
  once the result is anywhere in the merge (Latin's Platinean slot takes
  ``cm_platine``, which stands for Argentine and Uruguayan too, since one culture
  fills one slot). ``test_culture_merges_config`` lists every shared pair.
* **Core** parts define the merge; **optional** parts join where the starter
  holds most of them. Core parts are ordered **largest first** (1836 pops), since
  the first core part supplies a new culture's heritage, language, religion and
  graphics. Where pops don't decide (Latin), the order is the owner's.
* **Absorb** merges (``new is None``) fold the parts into an existing culture,
  and that result is their first core part: it is held and acceptance-tested
  only, never joined, converted or switched.
* A **new** result is ``cm_<merge key>``. The ``cm_`` prefix keeps clear of other
  mods that define ``german``, since a duplicate culture key is dropped.
* ``components`` names the tier-1 merges a tier-3 merge waits on: the merges
  whose results are among its core parts (Latin: French, Italian).
* A part's ``wait_for`` names vanilla journal entries that work on its culture (a renaissance, the
  Civil War entries, German unification). The merge neither starts on a core part, nor joins a part,
  while **any** country has one of them active (R37: a switch turns the part's pops into the result
  in every country, and the entry reads their fervor or share there), until it has waited
  ``te_cm_wait_cap_years`` (20) years. Two core parts that wait on the same entry share one start
  condition and one status row.
* **Tiers** are numbers: 1 = same language and heritage, 2 = same language
  across heritages (the spec's "1b"), 3 = same language family only (the spec's
  "tier 2"). A part's tier is **derived** from vanilla's traits (``derive_tier``)
  unless the roster sets it by hand where history disagrees with the traits.

Hand-set tiers (spec section 3: vanilla's traits sometimes disagree with history):
* tier 1: Occitan, Walloon (heritage Netherlandish, not Gallic), French (which
  Walloon's heritage would otherwise put at tier 2), Han with Yue, Hakka and Min
  (four vanilla languages, one Han identity), Japanese with Ryukyuan, and Kannada
  (heritage Deccani, not Carnatic);
* tier 3: Catalan, which shares Occitan's language but stays a later join.
"""

from __future__ import annotations

from dataclasses import dataclass

TRAITS_KEY = "__traits__"
_MAX_RESULT_CHAIN = 8


@dataclass(frozen=True)
class Part:
    """One slot of a merge. ``cultures`` are alternatives filling it, usually one id."""

    cultures: tuple[str, ...]
    tier: int | None = None
    wait_for: tuple[str, ...] = ()


@dataclass(frozen=True)
class NewCulture:
    name: str
    color: tuple[int, int, int]


@dataclass(frozen=True)
class Merge:
    key: str
    result: str
    new: NewCulture | None
    core: tuple[Part, ...]
    optional: tuple[Part, ...] = ()
    components: tuple[str, ...] = ()
    skip_if_dlc: str | None = None


def _p(*cultures: str, tier: int | None = None, wait_for: tuple[str, ...] = ()) -> Part:
    return Part(tuple(cultures), tier, tuple(wait_for))


def _new(name: str, r: int, g: int, b: int) -> NewCulture:
    return NewCulture(name, (r, g, b))


MERGES: tuple[Merge, ...] = (
    Merge(
        "german", "cm_german", _new("German", 118, 120, 128),
        # Vanilla's GER formation needs Pan-Nationalism or the variable je_german_unification_idea sets
        # when it completes (common/country_formation/00_major_formables.txt), and the entry completes
        # on North German fervor 40 and South German fervor 30. A part that switched first would leave
        # a would-be unifier without the technology unable to form Germany, so both core parts wait
        # for the entry to end in every country (R37).
        core=(
            _p("north_german", wait_for=("je_german_unification_idea",)),
            _p("south_german", wait_for=("je_german_unification_idea",)),
        ),
        optional=(_p("alemannic"), _p("east_german")),
    ),
    Merge(
        "italian", "cm_italian", _new("Italian", 40, 140, 90),
        core=(_p("north_italian"), _p("south_italian")),
        optional=(_p("corsican"),),
    ),
    Merge(
        "scandinavian", "cm_scandinavian", _new("Scandinavian", 66, 130, 190),
        core=(_p("swedish"), _p("danish"), _p("norwegian")),
        optional=(_p("icelandic"),),
    ),
    Merge(
        "east_slavic", "cm_east_slavic", _new("East Slavic", 168, 62, 52),
        core=(
            _p("russian"),
            _p("ukrainian", wait_for=("je_ukraine_cultural_renaissance",)),
            _p("byelorussian", wait_for=("je_belarus_cultural_renaissance",)),
        ),
    ),
    Merge(
        "yugoslav", "cm_yugoslav", _new("Yugoslav", 28, 84, 150),
        # je_the_balkan_league can only be activated while Serb or Bulgarian fervor is above 75
        # (05_balkan_wars.txt), so Serb and Bulgarian wait for it to end in every country (R37).
        core=(_p("serb", wait_for=("je_the_balkan_league",)), _p("croat"), _p("bosniak")),
        optional=(_p("slovene"), _p("bulgarian", wait_for=("je_the_balkan_league",))),
    ),
    Merge(
        "czechoslovak", "cm_czechoslovak", _new("Czechoslovak", 205, 90, 130),
        core=(_p("czech"), _p("slovak")),
        optional=(_p("sorb"),),
    ),
    Merge("hungarian", "hungarian", None, core=(_p("hungarian"), _p("szekely"))),
    Merge("dutch", "dutch", None, core=(_p("dutch"), _p("flemish"))),
    Merge("finnish", "finnish", None, core=(_p("finnish"), _p("karelian"))),
    Merge(
        "french", "french", None,
        # Walloon (Netherlandish heritage) and Occitan (its own language) read as
        # French from the Third Republic on; Catalan, mostly in Spain, stays a
        # later, tier-3 join.
        core=(_p("french", tier=1), _p("wallonian", tier=1), _p("occitan", tier=1)),
        optional=(_p("catalan", tier=3),),
    ),
    Merge("british", "british", None, core=(_p("british"), _p("scottish"))),
    Merge(
        "american", "cm_american", _new("American", 70, 60, 150),
        core=(_p("yankee"), _p("dixie", wait_for=("je_acw_reincorporate",))),
        optional=(_p("afro_american", wait_for=("je_acw_equality",)),),
    ),
    Merge(
        "anglophone", "cm_anglophone", _new("Anglophone", 124, 66, 150),
        core=(_p("british"), _p("yankee", "cm_american")),
        optional=(
            _p("anglo_canadian"),
            _p("australian"),
            _p("scottish"),
            _p("dixie", wait_for=("je_acw_reincorporate",)),
            _p("afro_american", wait_for=("je_acw_equality",)),
        ),
    ),
    Merge(
        "brazilian", "brazilian", None,
        core=(_p("brazilian"), _p("nordestino"), _p("paulista"), _p("amazonic"), _p("sulista")),
        optional=(_p("afro_brazilian"),),
        skip_if_dlc="rp1_content",
    ),
    Merge(
        "platine", "cm_platine", _new("Platine", 90, 170, 215),
        core=(_p("platinean"), _p("argentine"), _p("uruguayan"), _p("paraguayan")),
    ),
    Merge(
        "andean", "cm_andean", _new("Andean", 196, 132, 40),
        core=(_p("north_andean"), _p("south_andean"), _p("peruvian"), _p("bolivian")),
    ),
    Merge(
        "gran_colombian", "cm_gran_colombian", _new("Gran Colombian", 232, 200, 48),
        core=(_p("colombian"), _p("venezuelan"), _p("ecuadorian")),
    ),
    Merge(
        "chinese", "han", None,
        # Four vanilla languages, one historical Han identity (spec section 3).
        core=(_p("han", tier=1), _p("yue", tier=1), _p("min", tier=1), _p("hakka", tier=1)),
    ),
    Merge("japanese", "japanese", None, core=(_p("japanese", tier=1), _p("ryukyuan", tier=1))),
    Merge(
        "arab", "cm_arab", _new("Arab", 30, 112, 70),
        core=(_p("maghrebi"), _p("misri"), _p("mashriqi"), _p("bedouin"), _p("yemenite")),
        optional=(_p("sudanese"), _p("haratin"), _p("bidan")),
    ),
    Merge(
        "persian", "persian", None,
        core=(_p("persian"), _p("luri")),
        optional=(_p("tajik"), _p("hazara")),
    ),
    Merge(
        "oghuz_turkic", "cm_oghuz_turkic", _new("Oghuz Turkic", 222, 44, 70),
        core=(_p("turkish"), _p("azerbaijani")),
        optional=(_p("turkmen"),),
    ),
    Merge(
        "hindustani", "hindustani", None,
        core=(_p("hindustani"), _p("avadhi"), _p("bundeli"), _p("chhattisgarhi"), _p("bageli")),
    ),
    Merge(
        "dravidian", "cm_dravidian", _new("Dravidian", 156, 92, 34),
        # Kannada is Deccani, Tamil and Malayalam Carnatic; Telugu a separate language.
        core=(_p("tamil"), _p("kannada", tier=1), _p("malayalam")),
        optional=(_p("telegu"),),
    ),
    Merge(
        "indonesian", "cm_indonesian", _new("Indonesian", 214, 76, 40),
        core=(_p("javan"), _p("malay"), _p("sumatran"), _p("bornean")),
        optional=(_p("balinese"),),
    ),
    Merge(
        "filipino", "filipino", None,
        core=(_p("filipino"), _p("visayan"), _p("tagalog"), _p("ilocano")),
    ),
    Merge(
        "nguni", "cm_nguni", _new("Greater Nguni", 110, 70, 40),
        core=(_p("nguni"), _p("zulu"), _p("xhosa")),
    ),
    Merge(
        "latin", "cm_latin", _new("Latin", 170, 110, 200),
        core=(_p("french"), _p("cm_italian"), _p("spanish"), _p("portuguese")),
        # cm_platine stands for Platinean, Argentine and Uruguayan once the Platine merge has switched them
        # (spec section 3); a culture fills one slot, so it sits in the first of the three.
        optional=(
            _p("romanian"), _p("platinean", "cm_platine"), _p("argentine"), _p("uruguayan"), _p("chilean"),
        ),
        components=("french", "italian"),
    ),
    Merge(
        "pan_slavic", "cm_pan_slavic", _new("Pan-Slavic", 150, 30, 30),
        core=(_p("cm_east_slavic"), _p("cm_czechoslovak"), _p("cm_yugoslav")),
        optional=(_p("polish"), _p("slovene"), _p("bulgarian")),
        components=("east_slavic", "czechoslovak", "yugoslav"),
    ),
    Merge(
        "pan_turkic", "cm_pan_turkic", _new("Pan-Turkic", 40, 170, 190),
        core=(_p("cm_oghuz_turkic"), _p("uzbek"), _p("kazak"), _p("tatar"), _p("kirgiz")),
        optional=(_p("bashkir"), _p("crimean_tatar"), _p("caucasian_turk"), _p("uighur")),
        components=("oghuz_turkic",),
    ),
    Merge(
        "pan_malay", "cm_pan_malay", _new("Pan-Malay", 236, 150, 30),
        core=(_p("cm_indonesian"), _p("filipino")),
        components=("indonesian", "filipino"),
    ),
    Merge(
        "east_african", "cm_east_african", _new("East African", 20, 130, 120),
        # Tier 3 with no tier-1 merge to wait for (owner's ruling).
        core=(_p("swahili"), _p("nyamwezi"), _p("sukuma")),
        optional=(_p("yao"), _p("makua"), _p("lacustrine_bantu"), _p("kikuyu")),
    ),
)

_BY_KEY = {m.key: m for m in MERGES}


def merge_by_key(key: str) -> Merge:
    try:
        return _BY_KEY[key]
    except KeyError:
        raise KeyError("no culture merge with key %r" % key) from None


def parts_of(result: str) -> set[str]:
    """Every culture that fills a slot of a merge whose result is ``result``, the
    result itself left out (an absorb merge's result is its own first core part).

    A slot with alternatives (Anglophone's ``yankee`` / ``cm_american``) gives
    all of them. Merges that share a result add their parts together.
    """
    return {
        c
        for m in MERGES
        if m.result == result
        for p in m.core + m.optional
        for c in p.cultures
        if c != result
    }


def successors_of(culture: str) -> set[str]:
    """The cultures a part's pops can end up in: the result of every merge the
    culture is a part of, and those results' own results, down the chain.

    ``corsican`` gives ``{cm_italian, cm_latin}``, and ``scottish`` ``{british,
    cm_anglophone}``. A culture is never its own successor, so an absorb merge's
    result (``french``) is skipped in its own merge but still gets the next
    link (``cm_latin``). It is empty for a culture no merge folds away
    (``hungarian``).

    This is the whole chain on purpose. A pop-level read (``has_pop_culture``)
    follows the pops, and they change culture at every link, so the test must
    name every result that can hold them. A country-level read
    (``country_has_primary_culture``) loses nothing, because a part stays a
    primary culture of every country that had it (spec section 7), so the later
    links there are a judgment call about flavor, and
    ``test_culture_merge_mod_refs`` lets a line decline them with a ``REVIEWED``
    comment and a reason.
    """
    found: set[str] = set()
    frontier = [culture]
    for _ in range(_MAX_RESULT_CHAIN):
        nxt = []
        for c in frontier:
            for m in MERGES:
                if m.result == c:
                    continue
                if any(c in p.cultures for p in m.core + m.optional) and m.result not in found and m.result != culture:
                    found.add(m.result)
                    nxt.append(m.result)
        if not nxt:
            break
        frontier = nxt
    return found


# ---------------------------------------------------------------------------
# Traits
# ---------------------------------------------------------------------------


def unwrap(value):
    """Strip the ("=", x) pair the parser wraps every value in. A key the file
    writes more than once comes back as a list of such pairs, which this leaves
    alone."""
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def culture_traits(culture, cultures, merges, depth=0):
    """(heritage, language) of a culture, or None when it is unknown.

    A ``cm_`` result counts as having its merge's first core part's traits.
    """
    body = cultures.get(culture) if culture != TRAITS_KEY else None
    if body is not None:
        body = unwrap(body)
        if isinstance(body, dict):
            return unwrap(body.get("heritage")), unwrap(body.get("language"))
        return None
    if depth < _MAX_RESULT_CHAIN:
        for m in merges:
            if m.new is not None and m.result == culture:
                return culture_traits(m.core[0].cultures[0], cultures, merges, depth + 1)
    return None


def trait_group(trait, cultures):
    """The trait_group of a language or heritage trait (language_group_romance,
    heritage_group_european), or None for an unknown trait."""
    traits = unwrap(cultures.get(TRAITS_KEY)) or {}
    entry = unwrap(traits.get(trait)) if trait else None
    if isinstance(entry, dict):
        entry = unwrap(entry.get("trait_group"))
    return entry if isinstance(entry, str) else None


def _slot_of(merge: Merge, culture: str) -> Part:
    for part in merge.core + merge.optional:
        if culture in part.cultures:
            return part
    raise ValueError("%s is not a part of the %s merge" % (culture, merge.key))


def derive_tier(merge: Merge, culture: str, cultures: dict, merges: tuple[Merge, ...] | None = None) -> int:
    """How close a part is to the merge's core parts: 1, 2 or 3.

    The hand-set tier if the roster gives one. Otherwise it is measured against
    every core part other than its own slot (a hand-set core part still counts
    as a neighbor; the slot is excluded whole, so Yankee and ``cm_american``,
    which fill one slot, don't make each other tier 1):

    * 1: shares a language with a core part that also shares its heritage;
    * 2: shares a language, but no such core part has its heritage;
    * 3: shares only a language group.

    Raises ValueError for a culture outside the merge, or one sharing no
    language group with any core part (``validate`` reports the latter).
    """
    merges = MERGES if merges is None else merges
    slot = _slot_of(merge, culture)
    if slot.tier is not None:
        return slot.tier
    refs = [c for p in merge.core if p is not slot for c in p.cultures]
    mine = culture_traits(culture, cultures, merges)
    if mine is None:
        raise ValueError("%s: no traits for %s" % (merge.key, culture))
    heritage, language = mine
    group = trait_group(language, cultures)
    tier = None
    for ref in refs:
        theirs = culture_traits(ref, cultures, merges)
        if theirs is None:
            raise ValueError("%s: no traits for %s" % (merge.key, ref))
        if theirs[1] == language:
            if theirs[0] == heritage:
                return 1
            tier = 2
        elif tier is None and group is not None and trait_group(theirs[1], cultures) == group:
            tier = 3
    if tier is None:
        raise ValueError("%s: %s shares no language group with the core parts" % (merge.key, culture))
    return tier


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate(cultures: dict, merges: tuple[Merge, ...] | None = None) -> list[str]:
    """Errors in the roster against vanilla's cultures, [] when it is clean.

    ``cultures`` is the parsed Cultures dict (id -> body with heritage and
    language), with the Discrimination Traits dict under ``"__traits__"``. Pass
    vanilla alone: a ``cm_`` culture the mod already generates would read as
    defined twice. ``merges`` defaults to the roster; tests pass a modified one.
    """
    merges = MERGES if merges is None else merges
    errors: list[str] = []
    vanilla = {c for c in cultures if c != TRAITS_KEY}
    new_results = {m.result for m in merges if m.new is not None}
    keys = [m.key for m in merges]
    for key in sorted({k for k in keys if keys.count(k) > 1}):
        errors.append("merge key %s is used twice" % key)

    for m in merges:
        where = m.key
        if not m.core or any(not p.cultures for p in m.core + m.optional):
            errors.append("%s: core parts, and every part's cultures, must not be empty" % where)
            continue

        if m.new is None:
            if m.result != m.core[0].cultures[0]:
                errors.append("%s: an absorb merge's result %s must be its first core part" % (where, m.result))
            if m.result not in vanilla:
                errors.append("%s: absorb result %s is not a vanilla culture" % (where, m.result))
        else:
            if m.result != "cm_" + m.key:
                errors.append("%s: a new culture's id must be cm_%s, not %s" % (where, m.key, m.result))
            if m.result in vanilla:
                errors.append("%s: vanilla already defines %s" % (where, m.result))
            color = m.new.color
            if len(color) != 3 or not all(isinstance(v, int) and 0 <= v <= 255 for v in color):
                errors.append("%s: color %r is not three 0-255 integers" % (where, color))

        seen: set[str] = set()
        for part in m.core + m.optional:
            if part.tier not in (None, 1, 2, 3):
                errors.append("%s: tier %r on %s is not 1, 2 or 3" % (where, part.tier, "/".join(part.cultures)))
            for c in part.cultures:
                if c in seen:
                    errors.append("%s: %s is in two slots" % (where, c))
                seen.add(c)
                if c == m.result and m.new is not None:
                    errors.append("%s: %s is the merge's own result" % (where, c))
                elif c not in vanilla and c not in new_results:
                    errors.append("%s: %s is not a vanilla culture or a merge result" % (where, c))

        for comp in m.components:
            if comp not in keys:
                errors.append("%s: component %s is not a merge key" % (where, comp))
            elif comp == m.key:
                errors.append("%s: a merge can't be its own component" % where)

        # A part with no language group in common with a core part is cross-family.
        for part in m.core + m.optional:
            ref_groups = {
                trait_group(t[1], cultures)
                for p in m.core
                if p is not part
                for c in p.cultures
                for t in [culture_traits(c, cultures, merges)]
                if t is not None
            }
            ref_groups.discard(None)
            for c in part.cultures:
                traits = culture_traits(c, cultures, merges)
                if traits is None or not ref_groups:
                    continue  # unknown culture, already reported
                group = trait_group(traits[1], cultures)
                if group is None:
                    errors.append("%s: %s has no language group" % (where, c))
                elif group not in ref_groups:
                    errors.append("%s: %s shares no language group with the core parts (cross-family)" % (where, c))
    return errors
