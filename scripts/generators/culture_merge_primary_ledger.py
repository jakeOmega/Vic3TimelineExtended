"""What each vanilla read of a merge part as a primary culture means for removing the part.

``culture_merge_primary_reads.json`` lists every vanilla entity that tests a
part as a primary culture. This ledger gives each one a **disposition**, and
from the dispositions a part's **holds**: the conditions under which the part,
though it has switched and has no people left, stays a primary culture.

The rulings are the owner's (2026-11-09):

* "don't hold for cosmetic (party names, train graphics) or company
  eligibility";
* mirror without overriding vanilla where that can be done (formables: the
  merged cultures join the definition lists, ``gen_culture_merges``);
* "if other stuff would need holds, let me know and we can decide case by
  case": such reads are grouped into ``CASES``, each with the owner's ruling;
* of the cases that hold, "none should hold past 1936 - vanilla's end date"
  (``WINDOW_END``). The owner said it of the cases. Applying the same date to
  an unformed country is the designer's call, made so that the rule is one
  sentence ("after 1936 only a running journal entry holds a part");
* a small helper can be overridden ("is it not possible to override something
  like 'Is Indian' though? That seems small, unlike replacing a whole JE"):
  ``TRIGGER_OVERRIDES``.

Dispositions:

``cosmetic``   names, titles, flags, graphics. No hold.
``company``    a company's eligibility. No hold.
``moot``       can't matter once the part has switched; ``why`` says why. No hold.
``mirrored``   the mod restates the vanilla entity with the merged cultures
               beside the parts: a trigger in ``TRIGGER_OVERRIDES``, or a
               government type whose title belonged to the whole merged people
               (``restated_government_types``). No hold.
``entries``    belongs to journal entries: the part is held while **any** country
               has one of them running, whenever that is, since the entry could
               not finish without the part. Any country, because an entry also
               reads other countries' cultures (its targets, its overlord), and
               the scan can't tell whose culture a line tests. An entry that is
               only on offer (inactive, waiting on its ``possible``) holds
               nothing (owner, 2026-11-09: "only on offer shouldn't block, but
               there may be exceptions"): German National Identity is offered to
               a country *because* North German is still a primary culture. The
               exceptions go in ``ON_OFFER_HOLDS`` and hold until ``WINDOW_END``.
``unformed``   a formable's own trigger requires the part: held until
               ``WINDOW_END`` while the tag does not exist.
``case``       one of ``CASES``: holds the part until ``WINDOW_END`` if the
               case's ruling is to hold (only while its ``condition`` is true,
               where it has one), and not at all otherwise.

A formable whose **definition** lists a part is not a row here: the inventory's
``formables`` section covers it. A tag that owns no state at the 1836 start gets
the part's merged cultures added to its definition. A start tag (Russia,
Prussia) does not, since its country would begin the game with an empty
culture, and it holds nothing either: the first build held the part while the
tag was dead, so that a country could re-form it, and the owner's point about
Prussia ended that (2026-11-09: the German merge follows Germany's formation,
and Germany, an empire, cannot form a kingdom). So a country that has only the
merged culture cannot re-form a dead start tag. Only a merge's **new** culture
is added. An absorb merge's result is a vanilla culture with people of its own
(Dutch, for Flemish), and a definition that listed it would hand it to whoever
forms the tag; where vanilla's list lacks it, the part is held while the tag
does not exist.

``test_culture_merge_primary_reads.py`` fails on a row no rule covers, so a
vanilla patch that adds a read has to be classified here before it lands.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import culture_merge_primary_reads as reads  # noqa: E402
import culture_merges_config as cfg  # noqa: E402

COSMETIC, COMPANY, MOOT, MIRRORED, ENTRIES, UNFORMED, CASE = (
    "cosmetic", "company", "moot", "mirrored", "entries", "unformed", "case",
)
# Vanilla's end date (owner, 2026-11-09, of the cases: "none should hold past 1936"). Every hold but a running journal
# entry ends on this day; for an unformed country that is the designer's call (module docstring).
# Journal entries important enough to hold a part while they are only on offer, until WINDOW_END. None so far (owner,
# 2026-11-09: "We can make that the default for now and change if we encounter ones that are important enough").
ON_OFFER_HOLDS: tuple[str, ...] = ()
WINDOW_END = "1936.1.1"
# Vanilla scripted triggers the mod restates, the merged cultures added beside the parts they list: a trigger that is
# nothing but a list of cultures, so the copy is small and a vanilla patch to it shows as a changed list in the
# inventory (``trigger_lists``). gen_culture_merges writes the copies.
TRIGGER_OVERRIDES: tuple[str, ...] = ("has_indian_primary_culture",)


def restated_government_types(inventory: dict | None = None) -> dict[str, list[str]]:
    """Vanilla government type -> the merged cultures added to its culture test (owner, 2026-11-09: ruler titles are
    worth keeping). Only where the type names **every core culture** of the merge: then its title already belonged
    to the whole merged people (Kaiser names North and South German, so a German country keeps it), and no country
    gains a title that was another nation's. The French republics name French alone of Latin's core cultures, the
    Swahili sultanates Swahili alone of East African's, Folkhemmet Swedish alone of Scandinavian's: a Latin Spain
    would become a French Third Republic, so those are left to vanilla and fall back with the part. Only a merge's
    own new culture, never one further up the chain (Anglophone for the American types), for the same reason."""
    inventory = reads.load() if inventory is None else inventory
    named: dict[str, set[str]] = {}
    for row in inventory["reads"]:
        if row["file"].startswith("common/government_types/"):
            named.setdefault(row["entity"], set()).add(row["part"])
    found: dict[str, list[str]] = {}
    for name in inventory.get("government_types", {}):
        results = [
            merge.result for merge in cfg.MERGES
            if merge.new is not None and all(any(c in named[name] for c in slot.cultures) for slot in merge.core)
        ]
        if results:
            found[name] = results
    return found


_RESTATED_TYPES: dict[str, list[str]] | None = None


@dataclass(frozen=True)
class Disposition:
    kind: str
    why: str = ""
    entries: tuple[str, ...] = ()
    tag: str = ""
    case: str = ""


@dataclass(frozen=True)
class Case:
    """A group of reads the owner rules on as one. ``hold`` is the ruling (a held case holds until ``WINDOW_END``);
    ``ruled`` its date, or "" while it waits (an unruled case holds: nothing is dropped on a guess)."""

    title: str
    what: str
    hold: bool
    ruled: str = ""
    # For a held case, a one-line trigger (any scope) that says the content can still matter: the case then holds only
    # while it is true, still no later than WINDOW_END. "" holds through the whole window.
    condition: str = ""


CASES: dict[str, Case] = {
    "ai_weights": Case(
        "AI strategy and research weights",
        "Vanilla's AI weighs a country by its primary culture: the German and Italian unification strategies and the "
        "catalyst that switches to them, research priority for Nationalism and Corporatism, Japan's and China's "
        "wariness of a Russian neighbor, state values such as Portugal wanting Gaza, Russia's Orthodox Balkan clients.",
        hold=False,
        ruled="2026-11-09",
    ),
    "historical_characters": Case(
        "Historical characters",
        "176 character templates for Spain, Portugal, Peru, Chile and one American (Mark Twain) appear only in a "
        "country with the part as a primary culture.",
        hold=True,
        ruled="2026-11-09",
    ),
    "politics": Case(
        "Political movements, ideologies and lobbies",
        "The pan-national movements (German, Italian, Yugoslav), the Carlist and Miguelist movements and ideologies, "
        "Russian royalists, the Spanish anarchists' bonus, the anti-slavery movement's Yankee and Dixie terms, the "
        "Utilitarian movement, and a Bonapartist lobby's dislike of British and German countries. Filed here too, as "
        "the same kind of read (the designer's filing, 2026-11-09, after review): the terms in six parties' "
        "`join_weight` (the antebellum Northern and Southern interests, French legitimism), an interest group's pop "
        "attraction and membership effects (French intelligentsia, Zanzibar's Bedouin), and the Carlist swap when "
        "Corporatism is researched.",
        hold=False,
        ruled="2026-11-09",
    ),
    "laws": Case(
        "Laws and amendments",
        "Serfdom and Manorialism rules for Romanian and Polish countries, the Council Republic's Lenin, the American "
        "Second Amendment and Fugitive Slave Act, and the French, Spanish and Portuguese historical chambers.",
        hold=True,
        ruled="2026-11-09",
    ),
    "siberian_exile": Case(
        "Siberian exile",
        "Only a country with Russian as a primary culture can use the Siberian exile pool.",
        hold=True,
        ruled="2026-11-09",
    ),
    "one_off_events": Case(
        "Single flavor events",
        "One-off events that fire from a yearly or monthly pulse or an on-action, each for one culture: four historical "
        "agitators (Lassalle for North German, Dickens and two more for British), the Emu War (Australian), Sweden's "
        "two Bernadotte events, the Halloween event (Romanian), Zanzibar's change of ruler (Bedouin), Spain's monarchs, "
        "the Polish rebellion and independence, and the trigger that pairs a slave-holding people with the enslaved "
        "(Yankee and Dixie with Afro-American, Uzbek with Persian). The owner, shown that North German was held for an "
        "agitator event and one other read: \"Holding for just these two means the hold is way too strict.\" The "
        "rest of the list is filed by the same reasoning, which is the designer's reading.",
        hold=False,
        ruled="2026-11-09",
    ),
    "depose_dynasty": Case(
        "Deposing a ruling dynasty",
        "A French, Spanish or Portuguese monarchy can back a disloyal commander of a rival house (Legitimist, Orleanist, "
        "Bonapartist, Carlist, Miguelist) in a coup. The decision is shown by culture. The owner: \"if Latin has formed, "
        "the politics of the region have changed enough that I don't know that those ideologies make sense anymore, so "
        "having that be lost doesn't seem like a big deal to me.\"",
        hold=False,
        ruled="2026-11-09",
    ),
    "trialism": Case(
        "Austria's Trialism",
        "Austria, in the dual monarchy, can propose a third crown when a subject that is NOT Croat owns part of Croatia. "
        "The read is a negation on the subject, so removing Croat from a Yugoslav subject that owns Croatia would let "
        "Austria propose Trialism against the very people it is for (the owner: \"this is not great\", and a Yugoslav "
        "merge under Austria \"isn't that hard to occur\"). Held only while that can happen, which is the designer's "
        "narrowing: Austria exists, is a monarchy, has not organised Trialism, and a subject of its owns part of Croatia.",
        hold=True,
        ruled="2026-11-09",
        condition="c:AUS ?= { country_has_monarchy_law = yes NOT = { has_variable = aus_organised_trialism } "
                  "any_subject_or_below = { any_scope_state = { state_region = s:STATE_CROATIA } } }",
    ),
}

_COSMETIC_DIRS = {
    "common/government_types/": "ruler titles and government names",
    "common/customizable_localization/": "text",
    "common/power_bloc_names/": "power bloc names",
    "common/dynamic_country_names/": "country names",
    "common/dynamic_country_map_colors/": "map colors",
    "common/coat_of_arms/": "coats of arms",
    "common/flag_definitions/": "flags",
    "common/scripted_triggers/00_gfx_": "map graphics (trains, ships, buildings, armies)",
    "common/scripted_triggers/00_clothes_triggers.txt": "clothing",
    "common/scripted_effects/00_dynamic_state_names_": "state names",
}
_MOOT_DIRS = {
    "common/achievements/": "a mod that changes the checksum turns achievements off",
    "common/history/": "read once, when the game starts in 1836",
}
_CASE_DIRS = {
    "common/character_templates/": "historical_characters",
    "common/ai_strategies/": "ai_weights",
    "common/diplomatic_catalysts/": "ai_weights",
    "common/scripted_triggers/00_ai_triggers.txt": "ai_weights",
    "common/political_movements/": "politics",
    "common/ideologies/": "politics",
    "common/political_lobbies/": "politics",
    "common/laws/": "laws",
    "common/amendments/": "laws",
    "common/regional_exile_pools/": "siberian_exile",
}

# Rows the folder rules and the trace don't settle, by entity. A helper trigger or effect takes the disposition of
# what calls it.
_ENTITIES: dict[str, Disposition] = {
    # helpers of one journal entry that the trace lost (a second root, or a name too common to follow)
    "dp_annex_subject": Disposition(ENTRIES, entries=("je_peru_bolivia",)),
    "is_oppressor_of_schleswig_holstein": Disposition(ENTRIES, entries=("je_schleswig_holstein_question",)),
    "je_danubian_federation_polish_button_possible": Disposition(ENTRIES, entries=("je_danubian_federation",)),
    "eastern_question_russia.1": Disposition(ENTRIES, entries=("je_eastern_question_russia",)),
    "kazakhstan_events.2": Disposition(ENTRIES, entries=("je_pacify_the_steppes",)),
    "utilitarian.8": Disposition(ENTRIES, entries=("je_imperialism_of_promise",)),
    # Rebuilt every month from an on-action, so the trace sees no journal entry; its list (the German Confederation's
    # countries with North or South German as a primary culture) is read only by the Gründerzeit entry: the share of
    # them with Mutual Funds and a railway opens it, and their GDP is summed while it runs.
    "assemble_german_confederation_list_effect": Disposition(ENTRIES, entries=("je_grunderzeit",)),
    # politics
    "country_has_german_national_movement": Disposition(CASE, case="politics"),
    "country_has_italian_national_movement": Disposition(CASE, case="politics"),
    "country_has_yugoslav_national_movement": Disposition(CASE, case="politics"),
    "character_carlist_or_legitimist_switch_effect": Disposition(CASE, case="politics"),
    # laws
    "second_amendment_add_obsessions_effect": Disposition(CASE, case="laws"),
    "second_amendment_remove_obsessions_effect": Disposition(CASE, case="laws"),
    # a journal entry's after all: the on-action that fires them asks for the entry
    "italian_unification.7": Disposition(ENTRIES, entries=("je_risorgimento",)),
    "italian_unification.8": Disposition(ENTRIES, entries=("je_risorgimento",)),
    # can't matter once the part has switched
    "german_unification.6": Disposition(
        MOOT, why="a small German state asks to join a unification candidate for Germany, and there is none once "
                  "Germany exists: the German merge starts only after Germany has formed, and the mod's voluntary union "
                  "covers the case after (owner, 2026-11-09)"),
    "culture_brazil.1": Disposition(
        MOOT, why="needs Colossus of the South's nation-building entry, and under that content the Brazilian merge "
                  "does not run (skip_if_dlc)"),
    "on_country_released_as_independent": Disposition(
        MOOT, why="read at the moment a country is released, when it has the cultures its definition lists"),
    "slave_revolt_events.1": Disposition(
        MOOT, why="fired when a country is created, when it has the cultures its definition lists"),
    # single flavor events
    "historical_agitators.4": Disposition(CASE, case="one_off_events"),
    "historical_agitators.14": Disposition(CASE, case="one_off_events"),
    "historical_agitators.18": Disposition(CASE, case="one_off_events"),
    "historical_agitators.22": Disposition(CASE, case="one_off_events"),
    "emu_war.1": Disposition(CASE, case="one_off_events"),
    "sweden_monarchy.2": Disposition(CASE, case="one_off_events"),
    "sweden_monarchy.3": Disposition(CASE, case="one_off_events"),
    "spooky_halloween_events.1": Disposition(CASE, case="one_off_events"),
    "on_new_ruler": Disposition(CASE, case="one_off_events"),
    "on_monthly_pulse_country_spain": Disposition(CASE, case="one_off_events"),
    "on_monthly_pulse_country_spanish_monarchs_effect": Disposition(CASE, case="one_off_events"),
    "on_become_independent_poland_effect": Disposition(CASE, case="one_off_events"),
    "on_secession_start_polish_rebellion_effect": Disposition(CASE, case="one_off_events"),
    "culture_is_intuitive_slave_revolt_culture": Disposition(CASE, case="one_off_events"),
    # decisions
    "aus_organise_trialism": Disposition(CASE, case="trialism"),
    "austria_trialism.2": Disposition(CASE, case="trialism"),
    "austria_trialism.3": Disposition(CASE, case="trialism"),
    "decision_depose_ruling_dynasty": Disposition(CASE, case="depose_dynasty"),
    "character_has_ideology_conflicting_with_ruling_dynasty": Disposition(CASE, case="depose_dynasty"),
}
# One entity, different answers by culture: vanilla's on_secession_start fires the Risorgimento's events for an Italian
# secession (and asks for that entry) and the Polish rebellion for a Polish one.
_ENTITY_PARTS: dict[tuple[str, str], Disposition] = {
    ("on_secession_start", "north_italian"): Disposition(ENTRIES, entries=("je_risorgimento",)),
    ("on_secession_start", "south_italian"): Disposition(ENTRIES, entries=("je_risorgimento",)),
    ("on_secession_start", "polish"): Disposition(CASE, case="one_off_events"),
    # 1.15.1: a subject may join a Polish secession's initiator only while the Whites are weak, a test the play makes
    # only of a subject that has the Congress Poland entry (`subject_join_initiator_trigger`).
    ("dp_secession", "polish"): Disposition(ENTRIES, entries=("je_congress_poland",)),
}


def _prefix(table: dict[str, str], file: str) -> str | None:
    for prefix, value in table.items():
        if file.startswith(prefix):
            return value
    return None


def _by_field(file: str, blocks: set[str]) -> Disposition | None:
    """The folders where one entity holds reads of different kinds, told apart by the field the read sits in
    (review, 2026-11-09: a folder rule called an interest group's ideology setup and a party's `join_weight` "names")."""
    if file.startswith("common/interest_groups/"):
        if blocks <= {"on_enable"}:
            return Disposition(MOOT, why="run once, when the group is enabled: the name, ideology or trait it sets then "
                                         "stays, and a country created later starts with the cultures its definition lists")
        if blocks <= {"on_enable", "priority_cultures"}:
            return Disposition(COSMETIC, why="which cultures a group's generated leaders are drawn from")
        return Disposition(CASE, case="politics")
    if file.startswith("common/parties/"):
        return Disposition(COSMETIC, why="party names") if blocks <= {"name"} else Disposition(CASE, case="politics")
    if file.startswith("common/technology/"):
        return Disposition(CASE, case="ai_weights" if blocks <= {"ai_weight"} else "politics")
    return None


def classify(row: dict) -> Disposition | None:
    """The disposition of one inventory row, or None when no rule covers it."""
    global _RESTATED_TYPES
    file, entity = row["file"], row["entity"]
    if file.startswith("common/government_types/"):
        if _RESTATED_TYPES is None:
            _RESTATED_TYPES = restated_government_types()
        if entity in _RESTATED_TYPES:
            return Disposition(MIRRORED, why="restated with the merged culture")
    by_field = _by_field(file, set(row.get("blocks", ())))
    if by_field is not None:
        return by_field
    why = _prefix(_COSMETIC_DIRS, file)
    if why:
        return Disposition(COSMETIC, why=why)
    if file.startswith("common/company_types/"):
        return Disposition(COMPANY)
    why = _prefix(_MOOT_DIRS, file)
    if why:
        return Disposition(MOOT, why=why)
    if file.startswith("common/country_formation/"):
        return Disposition(UNFORMED, tag=entity)
    if entity in TRIGGER_OVERRIDES:
        return Disposition(MIRRORED, why="restated with the merged cultures")
    if (entity, row["part"]) in _ENTITY_PARTS:
        return _ENTITY_PARTS[(entity, row["part"])]
    if entity in _ENTITIES:
        return _ENTITIES[entity]
    case = _prefix(_CASE_DIRS, file)
    if case:
        return Disposition(CASE, case=case)
    if row.get("entries"):
        return Disposition(ENTRIES, entries=tuple(row["entries"]))
    return None  # an event, on-action or decision no journal entry reaches: it needs a line above, and maybe a ruling


@dataclass(frozen=True)
class Holds:
    """What keeps one part a primary culture after its switch."""

    entries: tuple[str, ...] = ()  # while any country has one running
    on_offer: tuple[str, ...] = ()  # until WINDOW_END, while any country has one on offer: entries in ON_OFFER_HOLDS
    unformed: tuple[str, ...] = ()  # until WINDOW_END, while one of these tags does not exist
    cases: tuple[str, ...] = ()  # until WINDOW_END: cases ruled to hold, or not ruled yet
    conditional: tuple[str, ...] = ()  # until WINDOW_END, while the case's `condition` holds

    @property
    def any(self) -> bool:
        return bool(self.entries or self.on_offer or self.unformed or self.cases or self.conditional)


def part_holds(inventory: dict | None = None) -> dict[str, Holds]:
    """Every part's holds, in the inventory's part order. A part nothing holds maps to an empty ``Holds``."""
    inventory = reads.load() if inventory is None else inventory
    entries: dict[str, set[str]] = {}
    unformed: dict[str, set[str]] = {}
    cases: dict[str, set[str]] = {}
    for row in inventory["reads"]:
        disposition = classify(row)
        if disposition is None:
            raise ValueError("no disposition for %s in %s" % (row["entity"], row["file"]))
        part = row["part"]
        if disposition.kind == ENTRIES:
            entries.setdefault(part, set()).update(disposition.entries)
        elif disposition.kind == UNFORMED:
            unformed.setdefault(part, set()).add(disposition.tag)
        elif disposition.kind == CASE and CASES[disposition.case].hold:
            cases.setdefault(part, set()).add(disposition.case)
    new_results = {merge.result for merge in cfg.MERGES if merge.new is not None}
    for tag, formable in inventory["formables"].items():
        listed = set(formable["cultures"])
        for culture in formable["cultures"]:
            if culture not in inventory["parts"]:
                continue
            unlisted_absorb = any(s not in new_results and s not in listed for s in cfg.successors_of(culture))
            if unlisted_absorb and not formable["exists_at_start"]:
                unformed.setdefault(culture, set()).add(tag)
    return {
        part: Holds(
            tuple(sorted(entries.get(part, ()))),
            tuple(sorted(e for e in entries.get(part, ()) if e in ON_OFFER_HOLDS)),
            tuple(sorted(unformed.get(part, ()))),
            tuple(sorted(c for c in cases.get(part, ()) if not CASES[c].condition)),
            tuple(sorted(c for c in cases.get(part, ()) if CASES[c].condition)),
        )
        for part in inventory["parts"]
    }


def case_parts(inventory: dict | None = None) -> dict[str, list[str]]:
    """case id -> the parts it has a read of, whatever its ruling."""
    inventory = reads.load() if inventory is None else inventory
    found: dict[str, set[str]] = {case: set() for case in CASES}
    for row in inventory["reads"]:
        disposition = classify(row)
        if disposition is not None and disposition.kind == CASE:
            found[disposition.case].add(row["part"])
    return {case: [part for part in inventory["parts"] if part in parts] for case, parts in found.items()}


def main() -> int:
    inventory = reads.load()
    holds = part_holds(inventory)
    free = [part for part, hold in holds.items() if not hold.any]
    print("%d parts; %d with no hold" % (len(holds), len(free)))
    for part, hold in holds.items():
        if hold.any:
            bits = []
            if hold.cases:
                bits.append("until %s: %s" % (WINDOW_END, ", ".join(hold.cases)))
            if hold.conditional:
                bits.append("until %s while it can matter: %s" % (WINDOW_END, ", ".join(hold.conditional)))
            if hold.unformed:
                bits.append("while unformed: " + " ".join(hold.unformed))
            if hold.entries:
                bits.append("entries: " + " ".join(hold.entries))
            print("  %-16s %s" % (part, "; ".join(bits)))
    for case, parts in case_parts(inventory).items():
        print("%s (%s): %s" % (case, "hold" if CASES[case].hold else "no hold", ", ".join(parts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
