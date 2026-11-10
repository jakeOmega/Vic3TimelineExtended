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
* A merge's ``gate`` is its own historical precondition (owner, 2026-11-09): Germany formed, slavery settled, Public
  Schools, independence. A milestone gate opens the start for good once met; a standing one also pauses a running
  merge while it fails. An optional part can carry a standing gate of its own (Afro-American and Afro-Brazilian pops
  join only once slavery is banned). See ``Gate``.
* **Tiers** are numbers: 1 = same language and heritage, 2 = same language
  across heritages (the spec's "1b"), 3 = same language family only (the spec's
  "tier 2"). A part's tier is **derived** from vanilla's traits (``derive_tier``)
  unless the roster sets it by hand where history disagrees with the traits.

Hand-set tiers (spec section 3: vanilla's traits sometimes disagree with history):
* tier 1: Occitan, Walloon (heritage Netherlandish, not Gallic), French (which
  Walloon's heritage would otherwise put at tier 2), Han with Yue, Hakka and Min
  (four vanilla languages, one Han identity), Japanese with Ryukyuan, Kannada
  (heritage Deccani, not Carnatic), and Mazanderani (Tabari, its own language);
* tier 3: Catalan, which shares Occitan's language but stays a later join.
"""

from __future__ import annotations

from dataclasses import dataclass

TRAITS_KEY = "__traits__"
_MAX_RESULT_CHAIN = 8


@dataclass(frozen=True)
class Gate:
    """A merge's own historical precondition (owner, 2026-11-09): what had to be settled before these peoples could
    become one, beyond the gates every merge has. A formation (Germany), a law (slavery), independence.

    ``trigger`` is a hand-written country-scope scripted trigger in
    ``common/scripted_triggers/te_culture_merge_gate_triggers.txt``, read on the candidate or the starter.
    A **milestone** stays met once met: it is a start condition only, latched in ``te_cm_gate_met_<m>`` at each
    census, so a later formation (Germany into United Europe) or a civil war's winner keeps it. A **standing**
    condition is also read while the merge runs: while it fails, no culture joins and none converts, complete or not.
    ``clause`` is player text, lowercase and with no full stop, read after "only once" ("we have formed $GER$");
    ``why`` is the status sentence for an idle merge it holds back. Both splice names, never spell them.
    """

    trigger: str
    milestone: bool
    clause: str
    why: str


@dataclass(frozen=True)
class Part:
    """One slot of a merge. ``cultures`` are alternatives filling it, usually one id.

    ``gate``, on an optional part only and only a standing one: a condition of its own for joining and converting,
    read on the starter (Afro-American pops join only once slavery is banned)."""

    cultures: tuple[str, ...]
    tier: int | None = None
    wait_for: tuple[str, ...] = ()
    gate: Gate | None = None


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
    gate: Gate | None = None


def _p(*cultures: str, tier: int | None = None, wait_for: tuple[str, ...] = (), gate: Gate | None = None) -> Part:
    return Part(tuple(cultures), tier, tuple(wait_for), gate)


def _new(name: str, r: int, g: int, b: int) -> NewCulture:
    return NewCulture(name, (r, g, b))


# Cultures the monthly fervor copy leaves out (owner, 2026-11-07, R41: a switched culture's fervor follows the
# culture it switched into, so vanilla's reads of it read the merged culture's). Ukrainian and Byelorussian merge
# with Russian into East Slavic, and vanilla reads their fervor only for a separate identity: their Cultural
# Renaissances open on it (Ukrainian at 15, Byelorussian at 20; 08_cultural_renaissances.txt) and the Russian Civil
# War releases a homeland culture's states on it (10; 05_russian_civil_war_triggers.txt). Copied, East Slavic's
# fervor would reopen a renaissance for a culture with no people, so theirs drifts to 0 and that content stays shut.
NO_FERVOR_COPY: tuple[str, ...] = ("ukrainian", "byelorussian")


# Traditions a merged culture takes from its parts (owner, 2026-11-09: once a switched part is no longer a primary
# culture, "give the result the component culture's traditions where it makes sense"). A primary culture's traits
# count for acceptance whether or not it has people, so removing Russian from an East Slavic Russia would end the
# acceptance its Russosphere tradition gave Tatars and Bashkirs. The rule: a **core** part's traditions pass to the
# result when the part switches, an optional part's do not (Alemannic's Helvetic tradition says nothing about
# Germans), and these core parts are left out by hand.
TRADITIONS_NOT_CARRIED: dict[tuple[str, str], str] = {
    ("japanese", "ryukyuan"): "the Sinosphere tradition of one prefecture would raise Japan's acceptance of every "
                              "Sinosphere culture",
}


def carries_traditions(merge: "Merge", culture: str) -> bool:
    """Does ``culture``, switching into ``merge``'s result, pass its traditions on?"""
    if (merge.key, culture) in TRADITIONS_NOT_CARRIED:
        return False
    return any(culture in part.cultures for part in merge.core)


# The bespoke gates (owner, 2026-11-09): what history says had to be settled before a set of peoples became one. Each
# trigger is hand-written in common/scripted_triggers/te_culture_merge_gate_triggers.txt, with its reasoning there. A
# formation gate names every tag that stands for the union, vanilla's and the mod's. The texts are player-facing:
# names are spliced ($GER$, $law_slavery_banned$), never spelled, and they hold no digit.
def _formed(name: str, tags: str, why: str) -> Gate:
    return Gate("te_cm_gate_formed_%s" % name, True, "we have formed %s" % tags,
                "%s The merge begins once we have formed %s." % (why, tags))


GATE_FORMED_GERMANY = _formed(
    "germany", "$GER$ or $HRE$",
    "Princes and confessions kept the north and the south apart, and a nation-state of their own is what joined them.")
GATE_FORMED_ITALY = _formed(
    "italy", "$ITA$",
    "Unification came first and the nation after it: once the country was made, its people still had to be made one.")
GATE_FORMED_SCANDINAVIA = _formed(
    "scandinavia", "$SCA$",
    "The northern kingdoms shared a heritage but never a state, and their union movement faded once each went its own way.")
GATE_FORMED_YUGOSLAVIA = _formed(
    "yugoslavia", "$YUG$",
    "Three faiths and two empires divided the South Slavs, and only a kingdom of their own set out to make one nation of them.")
GATE_FORMED_CZECHOSLOVAKIA = _formed(
    "czechoslovakia", "$CZH$",
    "One people was ruled from Vienna and the other from Budapest. A single nation was the doctrine of the republic they "
    "founded together.")
GATE_FORMED_LA_PLATA = _formed(
    "la_plata", "$PLT$",
    "The provinces of the River Plate broke apart into rival republics, and only their union can undo what separate "
    "statehood made.")
GATE_FORMED_GRAN_COLOMBIA = _formed(
    "gran_colombia", "$GCO$",
    "Bolívar's republic broke into three, each building an identity of its own, and only their union can undo it.")
GATE_FORMED_ANDES = _formed(
    "andes", "$PBC$ or $FND$",
    "Peru and Bolivia were one confederation until war split them, and only a union can undo what separate statehood made.")
GATE_FORMED_DRAVIDA_NADU = _formed(
    "dravida_nadu", "$DRA$",
    "Four literary languages divide the south, and each won a state of its own. Only the movement for a southern nation "
    "ever claimed them as one people.")
# The mod's Nusantara (NUS) counts too, and is called Indonesia in game as well, so the text names one.
GATE_FORMED_INDONESIA = _formed(
    "indonesia", "$IDN$",
    "A common national language came with the independence movement and the republic it founded.")
GATE_MEIJI = Gate(
    "te_cm_gate_meiji", True,
    "the restoration crisis is over: $je_meiji_restoration$ has concluded, or the $law_bakufu$ law is gone",
    "The shogunate kept Ryukyu nominally foreign to protect its trade with China. The modern state that followed annexed "
    "it and schooled its people in the standard language. The merge begins once $je_meiji_restoration$ has concluded, or "
    "the $law_bakufu$ law is gone.")
GATE_SLAVERY_SETTLED = Gate(
    "te_cm_gate_slavery_settled", False,
    "slavery is settled one way or the other, and any civil war over it has ended: the $law_slavery_banned$ law with "
    "$je_acw_countdown$ over, or slavery legal in every state under $law_slave_trade$ or $law_debt_slavery$",
    "A house divided against itself cannot stand. While slavery is legal in some states and not in others, these "
    "peoples stay apart. The merge begins once slavery is banned and $je_acw_countdown$ is over, or once it is legal in "
    "every state under $law_slave_trade$ or $law_debt_slavery$, and any civil war over it has ended.")
GATE_SLAVERY_BANNED = Gate(
    "te_cm_gate_slavery_banned", False,
    "the $law_slavery_banned$ law is in force",
    "No common identity was ever on offer between a free country and a slaveholding one. The merge begins once the "
    "$law_slavery_banned$ law is in force.")
GATE_PUBLIC_SCHOOLS = Gate(
    "te_cm_gate_public_schools", False,
    "the $law_public_schools$ law is in force",
    "Spoken languages this far apart gave way to one only once schools taught the national standard in every village. "
    "The merge begins once the $law_public_schools$ law is in force.")
GATE_INDEPENDENT = Gate(
    "te_cm_gate_independent", False,
    "we are not a subject of another country",
    "A national culture here was the work of the independence movement and the state it won, not of foreign rule. The "
    "merge begins once we are not a subject of another country.")
GATE_INDEPENDENT_SCHOOLS = Gate(
    "te_cm_gate_independent_schools", False,
    "we are not a subject of another country, and the $law_public_schools$ law is in force",
    "The shared standard language spread through the schools and broadcasts of independent states, not under foreign "
    "rule. The merge begins once we are not a subject of another country and the $law_public_schools$ law is in force.")


MERGES: tuple[Merge, ...] = (
    Merge(
        "german", "cm_german", _new("German", 118, 120, 128),
        # je_german_unification_idea completes on North German fervor 40 and South German fervor 30. No
        # wait: a switched part's fervor follows the merged culture's (te_cmg_copy_fervor_all; owner,
        # 2026-11-07, in place of R37's wait), so the entry reads German fervor once a part has switched.
        core=(_p("north_german"), _p("south_german")),
        optional=(_p("alemannic"), _p("east_german")),
        gate=GATE_FORMED_GERMANY,
    ),
    Merge(
        "italian", "cm_italian", _new("Italian", 40, 140, 90),
        core=(_p("north_italian"), _p("south_italian")),
        optional=(_p("corsican"),),
        gate=GATE_FORMED_ITALY,
    ),
    Merge(
        "scandinavian", "cm_scandinavian", _new("Scandinavian", 66, 130, 190),
        core=(_p("swedish"), _p("danish"), _p("norwegian")),
        optional=(_p("icelandic"),),
        gate=GATE_FORMED_SCANDINAVIA,
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
        # je_the_balkan_league can only be activated while Serb, Bulgarian or Greek fervor is above 75
        # (05_balkan_wars.txt:58-62). No wait: a switched part's fervor follows Yugoslav fervor
        # (te_cmg_copy_fervor_all; owner, 2026-11-07, in place of R37's wait).
        core=(_p("serb"), _p("croat"), _p("bosniak")),
        optional=(_p("slovene"), _p("bulgarian")),
        gate=GATE_FORMED_YUGOSLAVIA,
    ),
    Merge(
        "czechoslovak", "cm_czechoslovak", _new("Czechoslovak", 205, 90, 130),
        core=(_p("czech"), _p("slovak")),
        optional=(_p("sorb"),),
        gate=GATE_FORMED_CZECHOSLOVAKIA,
    ),
    Merge("hungarian", "hungarian", None, core=(_p("hungarian"), _p("szekely"))),
    Merge("dutch", "dutch", None, core=(_p("dutch"), _p("flemish"))),
    Merge("finnish", "finnish", None, core=(_p("finnish"), _p("karelian"))),
    Merge(
        "french", "french", None,
        # Walloon (Netherlandish heritage) and Occitan (its own language) read as
        # French from the Third Republic on; Catalan, mostly in Spain, stays a
        # later, tier-3 join. Walloon is optional (owner, 2026-11-09): its homeland
        # is Belgium's, which France's sphere holds only by annexing Belgium or
        # making it a subject, so as a core culture it held back the whole merge,
        # Occitan included. It still joins at tier 1 once the sphere holds Wallonia.
        core=(_p("french", tier=1), _p("occitan", tier=1)),
        optional=(_p("wallonian", tier=1), _p("catalan", tier=3)),
        gate=GATE_PUBLIC_SCHOOLS,
    ),
    Merge("british", "british", None, core=(_p("british"), _p("scottish"))),
    Merge(
        "american", "cm_american", _new("American", 70, 60, 150),
        core=(_p("yankee"), _p("dixie", wait_for=("je_acw_reincorporate",))),
        optional=(_p("afro_american", wait_for=("je_acw_equality",), gate=GATE_SLAVERY_BANNED),),
        gate=GATE_SLAVERY_SETTLED,
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
        gate=GATE_SLAVERY_BANNED,
    ),
    Merge(
        "brazilian", "brazilian", None,
        core=(
            _p("brazilian"), _p("nordestino"), _p("paulista"), _p("amazonic"),
            _p("sulista", wait_for=("ragamuffin_war",)),
        ),
        optional=(_p("afro_brazilian", gate=GATE_SLAVERY_BANNED),),
        skip_if_dlc="rp1_content",
    ),
    Merge(
        "platine", "cm_platine", _new("Platine", 90, 170, 215),
        core=(_p("platinean"), _p("argentine"), _p("uruguayan"), _p("paraguayan")),
        gate=GATE_FORMED_LA_PLATA,
    ),
    Merge(
        "andean", "cm_andean", _new("Andean", 196, 132, 40),
        core=(_p("north_andean"), _p("south_andean"), _p("peruvian"), _p("bolivian")),
        gate=GATE_FORMED_ANDES,
    ),
    Merge(
        "gran_colombian", "cm_gran_colombian", _new("Gran Colombian", 232, 200, 48),
        core=(_p("colombian"), _p("venezuelan"), _p("ecuadorian")),
        gate=GATE_FORMED_GRAN_COLOMBIA,
    ),
    Merge(
        "chinese", "han", None,
        # Four vanilla languages, one historical Han identity (spec section 3).
        core=(_p("han", tier=1), _p("yue", tier=1), _p("min", tier=1), _p("hakka", tier=1)),
        gate=GATE_PUBLIC_SCHOOLS,
    ),
    Merge("japanese", "japanese", None, core=(_p("japanese", tier=1), _p("ryukyuan", tier=1)), gate=GATE_MEIJI),
    Merge(
        "arab", "cm_arab", _new("Arab", 30, 112, 70),
        core=(_p("maghrebi"), _p("misri"), _p("mashriqi"), _p("bedouin"), _p("yemenite")),
        optional=(_p("sudanese"), _p("haratin"), _p("bidan")),
        gate=GATE_INDEPENDENT_SCHOOLS,
    ),
    Merge(
        "persian", "persian", None,
        # Both added by the owner, 2026-11-09. Mazanderani (Tabari, its own language in vanilla) joins at tier 1,
        # like Occitan: Shia and Persianate, its homeland wholly Iran's, and no separatist movement. Baluchi keeps
        # the tier its traits give (3): a Sunni people living mostly outside Persia in 1836, which only a long,
        # accepted hold would fold in.
        core=(_p("persian"), _p("luri")),
        optional=(_p("tajik"), _p("hazara"), _p("mazanderani", tier=1), _p("baluchi")),
    ),
    Merge(
        "oghuz_turkic", "cm_oghuz_turkic", _new("Oghuz Turkic", 222, 44, 70),
        core=(_p("turkish"), _p("azerbaijani")),
        optional=(_p("turkmen"),),
    ),
    Merge(
        "hindustani", "hindustani", None,
        core=(_p("hindustani"), _p("avadhi"), _p("bundeli"), _p("chhattisgarhi"), _p("bageli")),
        gate=GATE_INDEPENDENT,
    ),
    Merge(
        "dravidian", "cm_dravidian", _new("Dravidian", 156, 92, 34),
        # Kannada is Deccani, Tamil and Malayalam Carnatic; Telugu a separate language.
        core=(_p("tamil"), _p("kannada", tier=1), _p("malayalam")),
        optional=(_p("telegu"),),
        gate=GATE_FORMED_DRAVIDA_NADU,
    ),
    Merge(
        "indonesian", "cm_indonesian", _new("Indonesian", 214, 76, 40),
        core=(_p("javan"), _p("malay"), _p("sumatran"), _p("bornean")),
        optional=(_p("balinese"),),
        gate=GATE_FORMED_INDONESIA,
    ),
    Merge(
        "filipino", "filipino", None,
        core=(_p("filipino"), _p("visayan"), _p("tagalog"), _p("ilocano")),
        gate=GATE_INDEPENDENT,
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
        gate=GATE_INDEPENDENT_SCHOOLS,
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

        gates = ([m.gate] if m.gate else []) + [p.gate for p in m.core + m.optional if p.gate]
        for gate in gates:
            if not gate.trigger.startswith("te_cm_gate_"):
                errors.append("%s: gate trigger %s must be a te_cm_gate_ trigger" % (where, gate.trigger))
            if not gate.clause or gate.clause[-1] == "." or not gate.why.endswith("."):
                errors.append("%s: gate %s needs a clause with no full stop and a why sentence" % (where, gate.trigger))
        for part in m.core:
            if part.gate:
                # A core part's gate would belong in core_ok, the start and the whole-merge stall: that is the merge's gate.
                errors.append("%s: a gate on core part %s; give the merge the gate" % (where, "/".join(part.cultures)))
        for part in m.optional:
            if part.gate and part.gate.milestone:
                errors.append("%s: optional part %s has a milestone gate; only a standing one gates a part" % (where, "/".join(part.cultures)))

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
