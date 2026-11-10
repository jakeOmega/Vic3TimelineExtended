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
  a journal entry that is only on offer and to an unformed country is the
  designer's call, made so that the rule is one sentence ("after 1936 only a
  running journal entry holds a part"); it also bounds the hold the owner
  approved for a dead start tag ("hold the part only while that tag is dead"),
  which would otherwise keep North German for good once Prussia has become
  Germany;
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
               has one of them active, and, until ``WINDOW_END``, while any
               country has one on offer (inactive, waiting on its ``possible``).
               Any country, because an entry also reads other countries'
               cultures (its targets, its overlord), and the scan can't tell
               whose culture a line tests. An entry that never began stops
               holding at vanilla's end date like the cases do; one that is
               running holds whenever, since it could not finish without the
               part.
``unformed``   a formable's own trigger requires the part: held until
               ``WINDOW_END`` while the tag does not exist.
``case``       one of ``CASES``: holds the part until ``WINDOW_END`` if the
               case's ruling is to hold, and not at all otherwise.

A formable whose **definition** lists a part is not a row here: the inventory's
``formables`` section covers it. A tag that owns no state at the 1836 start gets
the part's merged cultures added to its definition; a start tag (Russia,
Prussia) holds the part while it is dead, since listing a merged culture there
would start that country with an empty culture. Only a merge's **new** culture
is added. An absorb merge's result is a vanilla culture with people of its own
(Dutch, for Flemish), and a definition that listed it would hand it to whoever
forms the tag; where vanilla's list lacks it, the part is held while the tag
does not exist, like a start tag's.

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
# entry ends on this day; for an entry on offer and an unformed country that is the designer's call (module docstring).
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
        "Utilitarian movement, and a Bonapartist lobby's dislike of British and German countries.",
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
    "standalone": Case(
        "Events and decisions outside any journal entry",
        "Events that fire from a yearly or monthly pulse, an on-action or a decision: the historical agitators "
        "(British, French, North German), the Emu War, Sweden's monarchy events, Austria's Trialism decision (Croat), "
        "deposing a ruling dynasty (French, Spanish, Portuguese), the Polish rebellion and independence, a freed "
        "people's country (Afro-American, Afro-Brazilian) and the German Confederation's member list.",
        hold=True,
        ruled="2026-11-09",
    ),
}

_COSMETIC_DIRS = {
    "common/government_types/": "ruler titles and government names",
    "common/parties/": "party names",
    "common/interest_groups/": "interest-group names",
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
    "common/technology/": "ai_weights",
    "common/diplomatic_catalysts/": "ai_weights",
    "common/scripted_triggers/00_ai_triggers.txt": "ai_weights",
    "common/political_movements/": "politics",
    "common/ideologies/": "politics",
    "common/political_lobbies/": "politics",
    "common/laws/": "laws",
    "common/amendments/": "laws",
    "common/regional_exile_pools/": "siberian_exile",
    "common/on_actions/": "standalone",
    "common/decisions/": "standalone",
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
    # politics
    "country_has_german_national_movement": Disposition(CASE, case="politics"),
    "country_has_italian_national_movement": Disposition(CASE, case="politics"),
    "country_has_yugoslav_national_movement": Disposition(CASE, case="politics"),
    "character_carlist_or_legitimist_switch_effect": Disposition(CASE, case="politics"),
    # laws
    "second_amendment_add_obsessions_effect": Disposition(CASE, case="laws"),
    "second_amendment_remove_obsessions_effect": Disposition(CASE, case="laws"),
    # outside any journal entry
    "character_has_ideology_conflicting_with_ruling_dynasty": Disposition(CASE, case="standalone"),
    "culture_is_intuitive_slave_revolt_culture": Disposition(CASE, case="standalone"),
    "assemble_german_confederation_list_effect": Disposition(CASE, case="standalone"),
    "on_become_independent_poland_effect": Disposition(CASE, case="standalone"),
    "on_monthly_pulse_country_spanish_monarchs_effect": Disposition(CASE, case="standalone"),
    "on_secession_start_polish_rebellion_effect": Disposition(CASE, case="standalone"),
}
_STANDALONE_EVENT_FILES = ("events/",)


def _prefix(table: dict[str, str], file: str) -> str | None:
    for prefix, value in table.items():
        if file.startswith(prefix):
            return value
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
    if entity in _ENTITIES:
        return _ENTITIES[entity]
    case = _prefix(_CASE_DIRS, file)
    if case:
        return Disposition(CASE, case=case)
    if row.get("entries"):
        return Disposition(ENTRIES, entries=tuple(row["entries"]))
    if file.startswith(_STANDALONE_EVENT_FILES):
        return Disposition(CASE, case="standalone")
    return None


@dataclass(frozen=True)
class Holds:
    """What keeps one part a primary culture after its switch."""

    entries: tuple[str, ...] = ()  # while any country has one active; until WINDOW_END, also while one is on offer
    unformed: tuple[str, ...] = ()  # until WINDOW_END, while one of these tags does not exist
    cases: tuple[str, ...] = ()  # until WINDOW_END: cases ruled to hold, or not ruled yet

    @property
    def any(self) -> bool:
        return bool(self.entries or self.unformed or self.cases)


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
            if formable["exists_at_start"] or unlisted_absorb:
                unformed.setdefault(culture, set()).add(tag)
    return {
        part: Holds(
            tuple(sorted(entries.get(part, ()))),
            tuple(sorted(unformed.get(part, ()))),
            tuple(sorted(cases.get(part, ()))),
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
