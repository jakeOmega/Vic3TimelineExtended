"""Generate the culture merges' mod data from the roster in culture_merges_config.py.

A culture merge (docs/superpowers/specs/2026-11-07-culture-merges-design.md)
turns closely related cultures (North and South German) into one national
culture. Merges that fold into an existing culture (Hungarian, Han) need no
new data. The rest get a **result culture** (``cm_<merge key>``), and the
merges that start at tier 3 (the roster's highest tier among their core
parts) also get a new language trait, and a new heritage trait unless their
core parts already share one, so that their acceptance sits at least as high
as the parts' acceptance of one another.

Outputs, all rewritten only when their content changes (UTF-8 BOM):

* ``common/cultures/te_merged_cultures.txt``: one culture per new result, in
  roster order. It takes its heritage, language, religion, graphics,
  ethnicities and obsessions from the merge's **first core part** (a result
  that is itself a part, like Latin's ``cm_italian``, supplies what it took),
  and its name lists from **every core and optional part**, in roster order,
  without duplicates. The color comes from the roster. A part without a given
  list adds nothing to it. One exception: a culture with no gendered surname
  list (``female_common_last_names`` ...) names its women from the plain
  surname list, so a part that lacks the gendered list lends that one to the
  gendered list. Otherwise Pan-Slavic's women would draw only on the East
  Slavic parts' surnames, while its men draw on all of them.
* ``common/discrimination_traits/te_merged_culture_traits.txt``: for each
  merge that starts at tier 3, ``language_cm_<key>``, whose group is the
  language group every core part shares, and ``heritage_cm_<key>`` only when
  the core parts do not all have the same heritage trait (R16: East African and
  Pan-Malay share theirs, so their result takes it and mints none). A minted
  heritage takes its group from the **first core part**, so Pan-Turkic's is
  ``heritage_group_middle_eastern`` (from Turkish), although Kazak and Kirgiz
  have the Kipchak heritage (a central Asian group) and Tatar a European one.
  A tier-3 result uses the traits it was given as its language and heritage.
* ``common/static_modifiers/te_merged_culture_static_modifiers.txt``: the six
  static modifiers the engine expects of every culture (vanilla's
  ``07_culture_standard_of_living.txt``, ``10_culture_cultural_acceptance_modifiers.txt``
  and ``11_culture_fervor_target_modifiers.txt``, a positive and a negative
  each), for each new result, in vanilla's shape. Without them the engine logs
  ``Missing expected culture static modifier`` six times per result at every
  load (126 lines, 2026-11-08).
* ``common/modifier_type_definitions/te_merged_culture_modifier_types.txt``: the
  three modifier types those static modifiers use
  (``state_<c>_standard_of_living_add``, ``country_<c>_cultural_acceptance_add``,
  ``country_fervor_target_<c>_add``), which vanilla registers for every culture
  (``99_todo_sort_into_other_files.txt``, ``10_`` and ``11_`` there). The engine
  creates none itself: without them each static modifier logged ``Unknown
  modifier type`` at load and loaded empty (126 lines, the first launch after
  the static modifiers, 2026-11-08). No loc: the engine names them from the
  culture, as it does vanilla's, and ``loc_coverage_audit`` knows the families.
* ``localization/english/te_culture_merges_generated_l_english.yml``: the
  display name of every ``cm_`` culture and new trait, rendered through
  ``organize_loc`` (category CULTURE_MERGES_GENERATED, whose keys
  ``organize_loc.CULTURE_MERGE_RESULT_KEYS`` lists) so that a run of
  ``organize_loc.py`` leaves it intact.
* ``common/scripted_triggers/te_culture_merges_generated_triggers.txt`` and
  ``common/scripted_effects/te_culture_merges_generated_effects.txt``: the yearly
  census and the per-part gates of **every** merge in the roster, absorb merges
  included (they too need their parts held and accepted). Per merge ``<m>``:
  ``te_cmg_<m>_is_candidate``, ``_core_ok``, ``_census_wanted`` (triggers);
  ``te_cmg_<m>_<c>_available``, ``_measured``, ``_years_met`` (tiers 2 and 3),
  ``_switched_in`` and ``_can_join`` per slot culture; ``te_cmg_census_<m>`` /
  ``te_cmg_census_<m>_country`` (effects), ``te_cmg_<m>_result_sol`` (merges with optional
  parts), plus the global ``te_cmg_census_all``.
  A part that has switched is skipped by the census and counts as met in
  ``core_ok``; a part that has joined is walked with its merge's result.
  The hand-written helpers they call are in
  ``common/scripted_effects/te_culture_merge_effects.txt``.
* ``common/journal_entries/te_culture_merges_generated.txt``,
  ``common/scripted_buttons/te_culture_merges_generated_buttons.txt``,
  ``common/scripted_progress_bars/te_culture_merges_generated_bars.txt`` and
  ``common/script_values/te_culture_merges_generated_values.txt``: starting a merge. A
  journal entry ``je_te_cm_<m>``, a start button ``te_cmg_start_<m>_button`` and a bar
  ``te_cmg_<m>_bar`` per merge, the progress values the bar shows, and the entry's loc
  (``entry_loc``) in the generated loc file above. The triggers and effects above gain
  ``te_cmg_<m>_can_start`` (each condition its own custom_tooltip), ``_is_starter``,
  ``_has_other_starter``, ``_starter_gone``, ``_all_switched``, ``te_cmg_<m>_join_ready`` /
  ``_settle`` / ``te_cmg_start_<m>`` and ``te_cmg_release_lost_starters``.
* The same two files carry the running merge (Task 6). Triggers: ``te_cmg_<m>_core_switched`` (no joined core
  part is left unswitched, and one has switched: the merge is then complete), and over every culture that can
  switch into a result ``te_cmg_is_switched_part`` and ``te_cmg_switched_part_kept`` (a switched part's homeland
  that Dynamic Homeland Progress leaves alone while its successor's homeland is in the state). Effects:
  ``te_cmg_yearly_country`` (each country's own conversion of the joined, unswitched parts of the merges it is
  in the sphere of: ``te_cm_convert_part`` at the part's own tier), ``te_cmg_dominance_all`` (the dominance of
  each such part, then its switch: ``te_cm_census_dominance`` and ``te_cm_switch_part``),
  ``te_cmg_monthly_country`` (``te_cm_monthly_switched_culture`` for each switched culture),
  ``te_cmg_copy_fervor_all`` (``te_cm_copy_fervor`` for each switched culture but ``cfg.NO_FERVOR_COPY``, a culture
  after the one it switched into: ``fervor_copy_order``; owner, 2026-11-07, in place of the German unification and
  Balkan League waits), ``te_cmg_set_fervor_from_source`` (the literal ladder it sets with: ``fervor_ladder``),
  ``te_cmg_formed_country`` (the same on ``on_country_formed``, then the result back as a primary culture in a
  sphere country that had begun converting, where a part that joined is primary: R34) and
  ``te_cmg_remove_switched_part_homelands`` (the homeland of every part that switched into the culture whose
  homeland was just removed, and down the chain through ``te_cmg_remove_parts_of_<culture>`` for a part that is
  itself a result). Merges chain only after the lower one is finished (R33): another merge's result is available
  only once that merge is complete with every joined part switched, or has no part joined, and a merge whose
  result has switched into a higher merge's (``te_cmg_<m>_result_switched``, the one place that test is written)
  joins, converts, measures and switches nothing more and is no candidate. A lower merge takes no new part once a
  higher one has joined its result (R38), a complete merge whose starter is gone for good lets go of its joined,
  unswitched parts (R38), and a merge whose core slot a higher merge has switched is no candidate
  (``te_cmg_<m>_core_left``, R38). The hand-written helpers are in the same ``te_culture_merge_effects.txt``.
* A merge with a bespoke gate (``cfg.Gate``, owner, 2026-11-09: Germany formed, slavery settled ...) gains
  ``te_cmg_<m>_gate_ok`` (a trigger calling the gate's hand-written ``te_cm_gate_*`` in
  ``common/scripted_triggers/te_culture_merge_gate_triggers.txt``), a ``can_start`` line after the technology, a status
  row before the slots and, for a standing gate, a ``paused`` row and a whole-merge stall of joining and conversion; a
  milestone is latched in ``te_cm_gate_met_<m>`` by the census and the start. An optional part's own gate joins its
  ``can_join`` and its conversion.
* A switched part leaves the primary cultures once nothing is tied to it (owner, 2026-11-09). The triggers file gains
  ``te_cmg_part_held_<c>`` per culture that can switch (from ``culture_merge_primary_ledger.part_holds``: the ledger of
  vanilla's reads of a part as a primary culture, scanned into ``culture_merge_primary_reads.json``) and
  ``te_cmg_<m>_untouched`` per merge that makes a culture; the effects file ``te_cmg_resolve_switched_result`` (the end
  of a chain of switches), ``te_cmg_strip_untouched_results`` and ``te_cmg_carry_traditions`` (``carried_traditions``).
  ``is_candidate`` and ``can_start`` accept the merge's result beside its core cultures (``_primary_cultures``).
* ``common/country_definitions/zz_te_culture_merge_definitions.txt``: an ``INJECT`` per vanilla formable that lists a
  part and owns no state in 1836, restating its ``cultures`` list with the merged cultures added
  (``definition_additions``), so a country whose parts are gone can still form it. The mod's own formables are
  hand-written; ``mod_definition_gaps`` says what they lack.
* ``common/scripted_triggers/00_a_te_culture_merge_vanilla_triggers.txt``: bare copies of the vanilla triggers in
  ``ledger.TRIGGER_OVERRIDES`` with the merged cultures added (``trigger_override_additions``).
* The effects file ends with ``te_cmg_debug_dump`` (plan Task 8), the console menu's option D: for each merge that is running,
  complete or has this country as a candidate, ``te_cm_debug_dump_merge`` and a ``te_cm_debug_dump_part`` per slot culture a
  starter can bring in (hand-written, ``common/scripted_effects/te_debug_cm_effects.txt``).

Also carried: ``traditions`` is what every core part shares (usually nothing,
so ``{ }``), and ``name_format``, ``seal_and_signature_texture`` and the other
optional fields a vanilla culture may carry (``taboos``, ``assimilation_rate``)
come from the first core part when it has them. ``CARRIED_FIELDS`` names every
field the generator knows; a test fails if a vanilla patch adds one it doesn't.

Vanilla comes from the committed ``vanilla_parsed/`` snapshot (and, for what the
snapshot doesn't hold, the committed ``culture_merge_primary_reads.json``), never
from the live ModState: that one also holds the ``cm_`` cultures this script writes, so
the roster's validation would call them "already defined", and the output
would depend on which vanilla version the machine has installed.

Run ``python3 scripts/generators/gen_culture_merges.py [--dry-run | --check]``.
No game install or running server is needed. Full server reloads call
``regenerate`` (mod_state_server.POST_LOAD_REGENERATORS). Every output is in
``plan_outputs``, one ``render_*`` function each.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import culture_merge_primary_ledger as ledger  # noqa: E402
import culture_merge_primary_reads as primary_reads  # noqa: E402
import culture_merges_config as cfg  # noqa: E402
from culture_merges_config import culture_traits, trait_group, unwrap  # noqa: E402
from organize_loc import _render_loc_file, section_label  # noqa: E402

HEADER = "# AUTO-GENERATED by scripts/generators/gen_culture_merges.py - do not edit manually."

CULTURES_OUT = Path("common/cultures/te_merged_cultures.txt")
TRAITS_OUT = Path("common/discrimination_traits/te_merged_culture_traits.txt")
STATIC_MODIFIERS_OUT = Path("common/static_modifiers/te_merged_culture_static_modifiers.txt")
MODIFIER_TYPES_OUT = Path("common/modifier_type_definitions/te_merged_culture_modifier_types.txt")
LOC_OUT = Path("localization/english/te_culture_merges_generated_l_english.yml")
TRIGGERS_GEN_OUT = Path("common/scripted_triggers/te_culture_merges_generated_triggers.txt")
EFFECTS_GEN_OUT = Path("common/scripted_effects/te_culture_merges_generated_effects.txt")
JE_OUT = Path("common/journal_entries/te_culture_merges_generated.txt")
BUTTONS_OUT = Path("common/scripted_buttons/te_culture_merges_generated_buttons.txt")
BARS_OUT = Path("common/scripted_progress_bars/te_culture_merges_generated_bars.txt")
VALUES_OUT = Path("common/script_values/te_culture_merges_generated_values.txt")
DEFINITIONS_OUT = Path("common/country_definitions/zz_te_culture_merge_definitions.txt")
# Sorts before vanilla's 00_scripted_triggers.txt: the first bare definition of a scripted trigger wins
# (scripting_best_practices.md, Load Order, fact 3).
VANILLA_TRIGGERS_OUT = Path("common/scripted_triggers/00_a_te_culture_merge_vanilla_triggers.txt")
LOC_CATEGORY = "CULTURE_MERGES_GENERATED"

SNAPSHOT_DIR = "vanilla_parsed"
# The tier at which a merge gets its own language and heritage traits.
TRAIT_TIER = 3

# Every name list a vanilla culture may carry, in the order vanilla writes them.
NAME_LISTS = (
    "male_common_first_names",
    "female_common_first_names",
    "noble_last_names",
    "common_last_names",
    "male_noble_first_names",
    "female_noble_first_names",
    "male_regal_first_names",
    "female_regal_first_names",
    "regal_last_names",
    "female_common_last_names",
    "female_noble_last_names",
    "female_regal_last_names",
)
# A gendered surname list and the plain list the engine uses for women without it.
FEMALE_SURNAMES = {
    "female_common_last_names": "common_last_names",
    "female_noble_last_names": "noble_last_names",
    "female_regal_last_names": "regal_last_names",
}
# Single-valued fields copied from the first core part when it has them; written
# before ("name_format") or after the name lists, in vanilla's order.
OPTIONAL_SCALARS = ("name_format", "seal_and_signature_texture", "assimilation_rate")
# Every field a vanilla culture may carry that the generator handles: "color" is
# the roster's, "traditions" the core parts' common ground, the rest the first
# core part's (name lists: merged).
CARRIED_FIELDS = frozenset(
    ("color", "religion", "heritage", "language", "graphics", "ethnicities", "obsessions", "taboos", "traditions")
    + OPTIONAL_SCALARS
    + NAME_LISTS
)
# Lines of a name list wrap at this many characters after the indent.
WRAP = 96

_BARE_TOKEN = re.compile(r"[A-Za-z0-9_.\-]+")


# ---------------------------------------------------------------------------
# Vanilla
# ---------------------------------------------------------------------------


def load_vanilla(root: Path = ROOT) -> dict:
    """Vanilla cultures by id, with the discrimination traits under ``"__traits__"``.

    Reads the two entity types from the committed snapshot rather than
    ``vanilla_parsed.load()``, which decodes all sixty of them.
    """
    import vanilla_parsed

    directory = root / SNAPSHOT_DIR
    manifest = vanilla_parsed.read_manifest(str(directory))
    if manifest is None:
        raise FileNotFoundError(f"no vanilla snapshot at {directory}")
    if manifest.get("format_version") != vanilla_parsed.FORMAT_VERSION:
        raise ValueError("vanilla snapshot format changed; rebuild it with `python3 vanilla_parsed.py build`")

    def read(kind):
        with open(directory / manifest["entity_types"][kind]["file"], encoding="utf-8") as f:
            return vanilla_parsed.decode(json.load(f))

    cultures = dict(read("Cultures"))
    cultures[cfg.TRAITS_KEY] = dict(read("Discrimination Traits"))
    return cultures


# ---------------------------------------------------------------------------
# Planning: what each merge's culture and traits hold
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Trait:
    key: str
    kind: str  # "language" or "heritage"
    group: str
    name: str


@dataclass
class Built:
    merge: cfg.Merge
    fields: dict  # heritage, language, religion, graphics, ethnicities, obsessions, name lists
    traits: tuple[Trait, ...]


def _fields(body) -> dict:
    body = unwrap(body)
    return body if isinstance(body, dict) else {}


def _repeats(value) -> list | None:
    """The values of a key the file wrote more than once, else None.

    The parser returns such a key as a list of (operator, value) pairs, so
    vanilla's ``1 = arab`` and ``1 = slavic`` in one ethnicities block, or
    Marathi's three name lists written twice, arrive as ``[("=", x), ("=", y)]``.
    """
    if isinstance(value, list) and value and all(isinstance(v, tuple) and len(v) == 2 and v[0] in ("=", "?=") for v in value):
        return [unwrap(v) for v in value]
    return None


def _single(fields: dict, name: str, who: str) -> str:
    value = unwrap(fields.get(name))
    if not isinstance(value, str):
        raise ValueError(f"{who} has no single {name}: {value!r}")
    return value


def _list(fields: dict, name: str) -> list[str]:
    """The names in a list field ([] when it is absent or empty), all repeats of it joined.

    Raises ValueError for anything but names, so that a shape the generator
    doesn't know fails loudly instead of being written out as Python.
    """
    value = unwrap(fields.get(name))
    if value is None:
        return []
    names: list[str] = []
    for chunk in _repeats(value) or [value]:
        if chunk == {}:  # `obsessions = { }` parses as an empty dict
            continue
        if not isinstance(chunk, list) or not all(isinstance(v, str) for v in chunk):
            raise ValueError(f"{name} is not a list of names: {chunk!r}")
        names.extend(chunk)
    return names


def _ethnicities(fields: dict) -> list[tuple[str, str]]:
    """The ``ethnicities`` block as (weight, ethnicity) entries in source order.

    A weight vanilla writes twice (``1 = arab`` ``1 = slavic``) is two entries.
    A built result's entries are already in this shape.
    """
    value = unwrap(fields.get("ethnicities"))
    if isinstance(value, list) and not _repeats(value):
        return [tuple(entry) for entry in value]
    if not isinstance(value, dict):
        return []
    entries = []
    for weight, raw in value.items():
        for ethnicity in _repeats(raw) or [unwrap(raw)]:
            if not isinstance(ethnicity, str):
                raise ValueError(f"ethnicity {weight} = {ethnicity!r} is not a name")
            entries.append((weight, ethnicity))
    return entries


def shared_traditions(core_fields: list[dict]) -> list[str]:
    """The traditions every core part has, in the first core part's order."""
    shared = _list(core_fields[0], "traditions")
    for fields in core_fields[1:]:
        have = _list(fields, "traditions")
        shared = [t for t in shared if t in have]
    return shared


def merged_names(ids, list_name: str, cultures: dict) -> list[str]:
    """Every name of ``list_name`` in the cultures ``ids``, in order, without duplicates.

    A culture without the list adds nothing, except to a gendered surname list
    (see FEMALE_SURNAMES), where it adds the plain list its women use.
    """
    plain = FEMALE_SURNAMES.get(list_name)
    names: list[str] = []
    for culture in ids:
        fields = _fields(cultures[culture])
        found = _list(fields, list_name) or (_list(fields, plain) if plain else [])
        names.extend(n for n in found if n not in names)
    return names


def _has(ids, list_name: str, cultures: dict) -> bool:
    return any(_list(_fields(cultures[c]), list_name) for c in ids)


def start_tier(merge: cfg.Merge, cultures: dict, merges) -> int:
    """The highest tier among the merge's core parts."""
    return max(cfg.derive_tier(merge, part.cultures[0], cultures, merges) for part in merge.core)


def _core_traits(merge: cfg.Merge, cultures: dict, merges) -> list[tuple]:
    """(heritage, language) of each core part (a result part counts as its first core part)."""
    traits = []
    for part in merge.core:
        found = culture_traits(part.cultures[0], cultures, merges)
        if found is None:
            raise ValueError(f"{merge.key}: no traits for {part.cultures[0]}")
        traits.append(found)
    return traits


def _group_of_core_parts(merge: cfg.Merge, cultures: dict, merges, index: int, what: str, strict: bool) -> str:
    """The trait group of the core parts' heritage (index 0) or language (index 1).

    The group every core part shares; when they share none, an error with
    ``strict`` and the first core part's group without.
    """
    groups = [trait_group(traits[index], cultures) for traits in _core_traits(merge, cultures, merges)]
    if None in groups:
        raise ValueError(f"{merge.key}: a core part has no {what} group")
    if len(set(groups)) == 1 or not strict:
        return groups[0]
    raise ValueError(f"{merge.key}: the core parts share no {what} group ({sorted(set(groups))})")


def _traits_for(merge: cfg.Merge, cultures: dict, merges) -> tuple[Trait, ...]:
    """The traits a merge mints: none below tier 3, else a language trait and,
    unless every core part has the same heritage trait (then the result takes
    that one), a heritage trait."""
    if merge.new is None or start_tier(merge, cultures, merges) < TRAIT_TIER:
        return ()
    traits = [Trait(f"language_cm_{merge.key}", "language",
                    _group_of_core_parts(merge, cultures, merges, 1, "language", strict=True), merge.new.name)]
    if len({heritage for heritage, _ in _core_traits(merge, cultures, merges)}) > 1:
        traits.append(Trait(f"heritage_cm_{merge.key}", "heritage",
                            _group_of_core_parts(merge, cultures, merges, 0, "heritage", strict=False), merge.new.name))
    return tuple(traits)


def build_plan(cultures: dict, merges: tuple[cfg.Merge, ...] | None = None) -> list[Built]:
    """The result culture (and traits) of every merge that makes a new culture, in roster order.

    ``cultures`` is vanilla alone (``load_vanilla``). Raises ValueError for a
    roster ``cfg.validate`` rejects.
    """
    merges = cfg.MERGES if merges is None else merges
    errors = cfg.validate(cultures, merges)
    if errors:
        raise ValueError("the culture merge roster is invalid:\n  " + "\n  ".join(errors))

    by_result = {m.result: m for m in merges if m.new is not None}
    # Vanilla's cultures, then each result as it is built, so a result that is
    # itself a part (Latin's cm_italian) is read like any other culture.
    pool = {c: body for c, body in cultures.items() if c != cfg.TRAITS_KEY}
    built: dict[str, Built] = {}
    building: set[str] = set()

    def build(result: str) -> Built:
        if result in built:
            return built[result]
        if result in building:
            raise ValueError(f"{result} is a part of itself")
        building.add(result)
        merge = by_result[result]
        part_ids = [c for part in merge.core + merge.optional for c in part.cultures]
        for culture in part_ids:
            if culture in by_result:
                build(culture)

        traits = _traits_for(merge, cultures, merges)
        first_id = merge.core[0].cultures[0]
        first = _fields(pool[first_id])
        who = f"{merge.key}'s first core part {first_id}"
        fields = {
            "religion": _single(first, "religion", who),
            "heritage": _single(first, "heritage", who),
            "language": _single(first, "language", who),
            "graphics": _single(first, "graphics", who),
            "ethnicities": _ethnicities(first),
            "obsessions": _list(first, "obsessions"),
            "taboos": _list(first, "taboos"),
            "traditions": shared_traditions([_fields(pool[p.cultures[0]]) for p in merge.core]),
        }
        for name in OPTIONAL_SCALARS:
            if name in first:
                fields[name] = _single(first, name, who)
        if not fields["ethnicities"]:
            raise ValueError(f"{who} has no ethnicities")
        for trait in traits:
            fields[trait.kind] = trait.key
        for list_name in NAME_LISTS:
            if list_name in FEMALE_SURNAMES and not _has(part_ids, list_name, pool):
                continue
            names = merged_names(part_ids, list_name, pool)
            if names:
                fields[list_name] = names

        pool[result] = fields
        building.discard(result)
        built[result] = Built(merge, fields, traits)
        return built[result]

    return [build(m.result) for m in merges if m.new is not None]


def result_loc_keys(root: Path = ROOT) -> set[str]:
    """Every loc key the generator writes: the ``cm_`` ids and the new trait keys."""
    keys = set()
    for entry in build_plan(load_vanilla(root)):
        keys.add(entry.merge.result)
        keys.update(trait.key for trait in entry.traits)
    return keys


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _token(value: str) -> str:
    """A name or good as the script writes it: bare, or quoted when it has a space or other symbol."""
    if _BARE_TOKEN.fullmatch(value):
        return value
    if '"' in value or "\n" in value:
        raise ValueError(f"{value!r} can't be written as a script token")
    return f'"{value}"'


def render_name_list(list_name: str, names: list[str]) -> str:
    """A tab-indented ``list_name = { ... }`` block, wrapped at WRAP characters. "" for no names."""
    if not names:
        return ""
    lines = []
    line = ""
    for name in map(_token, names):
        if line and len(line) + 1 + len(name) > WRAP:
            lines.append(line)
            line = ""
        line = f"{line} {name}" if line else name
    lines.append(line)
    body = "".join(f"\t\t{row}\n" for row in lines)
    return f"\t{list_name} = {{\n{body}\t}}\n"


def _part_names(parts) -> str:
    return ", ".join("/".join(part.cultures) for part in parts)


def render_culture(entry: Built) -> str:
    merge, fields = entry.merge, entry.fields
    r, g, b = merge.new.color
    comment = f"# {merge.new.name}: {_part_names(merge.core)}"
    if merge.optional:
        comment += f" (optional: {_part_names(merge.optional)})"
    out = [
        comment + "\n",
        f"{merge.result} = {{\n",
        f"\tcolor = rgb{{ {r} {g} {b} }}\n",
        f"\treligion = {fields['religion']}\n",
        f"\theritage = {fields['heritage']}\n",
        f"\tlanguage = {fields['language']}\n",
    ]
    if "name_format" in fields:
        out.append(f"\tname_format = {fields['name_format']}\n")
    for list_name in ("obsessions", "taboos"):
        if fields[list_name]:
            out.append(f"\t{list_name} = {{\n" + "".join(f"\t\t{_token(o)}\n" for o in fields[list_name]) + "\t}\n")
    out.append("\ttraditions = { " + "".join(f"{_token(t)} " for t in fields["traditions"]) + "}\n")
    out.extend(render_name_list(name, fields.get(name, [])) for name in NAME_LISTS)
    out.append(f"\tgraphics = {fields['graphics']}\n")
    out.append("\tethnicities = {\n" + "".join(f"\t\t{weight} = {ethnicity}\n" for weight, ethnicity in fields["ethnicities"]) + "\t}\n")
    for name in OPTIONAL_SCALARS[1:]:
        if name in fields:
            out.append(f"\t{name} = {fields[name]}\n")
    out.append("}\n")
    return "".join(out)


def render_cultures(plan: list[Built]) -> str:
    return HEADER + "\n\n" + "\n".join(render_culture(entry) for entry in plan)


def render_traits(plan: list[Built]) -> str:
    blocks = []
    for entry in plan:
        for trait in entry.traits:
            blocks.append(
                f"# {entry.merge.new.name}\n"
                f"{trait.key} = {{\n\ttype = {trait.kind}\n\ttrait_group = {trait.group}\n}}\n"
            )
    return HEADER + "\n\n" + "\n".join(blocks)


# The static modifiers the engine expects of every culture: (vanilla file, kind, modifier type pattern, display name).
# Vanilla gives each culture a positive and a negative one of each kind, with the same unit value and the flag icons.
CULTURE_STATIC_MODIFIER_KINDS = (
    ("07_culture_standard_of_living.txt", "standard_of_living", "state_{c}_standard_of_living_add", "Standard of Living"),
    ("10_culture_cultural_acceptance_modifiers.txt", "cultural_acceptance", "country_{c}_cultural_acceptance_add",
     "Cultural Acceptance"),
    ("11_culture_fervor_target_modifiers.txt", "fervor_target", "country_fervor_target_{c}_add", "Fervor Target"),
)
CULTURE_STATIC_MODIFIER_SIGNS = ("positive", "negative")
# Where vanilla registers each kind's modifier type for every one of its cultures. The engine creates none of them
# itself: a static modifier naming an unregistered one logs `Unknown modifier type` at load and loads empty, so the
# effects that scale it (add_culture_standard_of_living_modifier, add_culture_acceptance_modifier,
# add_fervor_target_modifier) do nothing for that culture (126 lines for the 21 results, 2026-11-08). The engine names
# the types from a template (STATE_CULTURE_SOL_MODIFIER, COUNTRY_CULTURE_CULTURAL_ACCEPTANCE_MODIFIER,
# COUNTRY_FERVOR_TARGET_CULTURE_MODIFIER), so vanilla gives them no loc key and neither does the mod.
CULTURE_MODIFIER_TYPE_FILES = {
    "standard_of_living": "99_todo_sort_into_other_files.txt",
    "cultural_acceptance": "10_country_cultural_acceptance_culture_modifier_types.txt",
    "fervor_target": "11_country_fervor_taget_culture_modifier_types.txt",
}


def culture_modifier_types(culture: str) -> list[str]:
    """The three modifier types ``culture``'s expected static modifiers use, in the order they are written."""
    return [pattern.format(c=culture) for _, _, pattern, _ in CULTURE_STATIC_MODIFIER_KINDS]


def culture_static_modifier_keys(culture: str) -> list[str]:
    """The six static modifier keys the engine expects of ``culture``, in the order they are written."""
    return [
        "%s_%s_modifier_%s" % (culture, kind, sign)
        for _, kind, _, _ in CULTURE_STATIC_MODIFIER_KINDS
        for sign in CULTURE_STATIC_MODIFIER_SIGNS
    ]


def render_static_modifiers(plan: list[Built]) -> str:
    """Each new result's six expected static modifiers, in vanilla's shape (vanilla's three files, one section each)."""
    out = [HEADER, "", "# The static modifiers the engine expects of every culture; vanilla's live in three files, named in each section.",
           "# The engine logs `Missing expected culture static modifier <key>` at load for a culture without them."]
    for vanilla_file, kind, pattern, _ in CULTURE_STATIC_MODIFIER_KINDS:
        out += ["", "# ---- as vanilla's %s ----" % vanilla_file]
        for entry in plan:
            culture = entry.merge.result
            for sign in CULTURE_STATIC_MODIFIER_SIGNS:
                out += [
                    "",
                    "%s_%s_modifier_%s = {" % (culture, kind, sign),
                    '\ticon = "gfx/interface/icons/timed_modifier_icons/modifier_flag_%s.dds"' % sign,
                    "\t%s = 1" % pattern.format(c=culture),
                    "}",
                ]
    return "\n".join(out) + "\n"


def render_modifier_types(plan: list[Built]) -> str:
    """Each new result's three culture modifier types, in vanilla's shape (one section per vanilla file)."""
    out = [HEADER, "", "# The modifier types the engine expects of every culture, which its static modifiers",
           "# (te_merged_culture_static_modifiers.txt) use; vanilla's live in three files, named in each section.",
           "# Without them each static modifier logs `Unknown modifier type` at load and does nothing.",
           "# The engine names them from the culture, so they carry no loc key, as vanilla's don't."]
    for _, kind, pattern, _ in CULTURE_STATIC_MODIFIER_KINDS:
        out += ["", "# ---- as vanilla's %s ----" % CULTURE_MODIFIER_TYPE_FILES[kind]]
        for entry in plan:
            out += [
                "",
                "%s = {" % pattern.format(c=entry.merge.result),
                "\tdecimals = 1",
                "\tcolor = good",
                "\tgame_data = {",
                "\t\tai_value = 0",
                "\t}",
                "}",
            ]
    return "\n".join(out) + "\n"


def static_modifier_loc(plan: list[Built]) -> dict[str, str]:
    """Display names of the expected static modifiers (vanilla's carry none; the mod's are named so none shows raw)."""
    out = {}
    for entry in plan:
        culture = entry.merge.result
        for _, kind, _, label in CULTURE_STATIC_MODIFIER_KINDS:
            for sign in CULTURE_STATIC_MODIFIER_SIGNS:
                out["%s_%s_modifier_%s" % (culture, kind, sign)] = "$%s$ %s" % (culture, label)
    return out


def render_loc(plan: list[Built], extra: dict[str, str] | None = None) -> str:
    """The generated loc file: each result and trait name, then ``extra`` (the entries' keys, key -> text)."""
    entries = {}
    for entry in plan:
        name = entry.merge.new.name
        if '"' in name:
            raise ValueError(f"{entry.merge.key}: a display name can't hold a quote mark")
        entries[entry.merge.result] = f'0 "{name}"'
        for trait in entry.traits:
            entries[trait.key] = f'0 "{trait.name}"'
    for key, text in (extra or {}).items():
        if key in entries:
            raise ValueError(f"{key} is defined twice")
        entries[key] = f'0 "{text}"'
    return _render_loc_file([(section_label(LOC_CATEGORY), entries)]).decode("utf-8-sig")


# ---------------------------------------------------------------------------
# The census and the per-part gates (scripted triggers and effects)
# ---------------------------------------------------------------------------


class _Script:
    """A tab-indented script writer: ``with out.block("name"):`` opens ``name = {``."""

    def __init__(self):
        self.lines: list[str] = []
        self.depth = 0

    def line(self, text: str = "") -> None:
        self.lines.append("\t" * self.depth + text if text else "")

    @contextmanager
    def block(self, header: str, comment: str = ""):
        """``header = {``, its body, ``}``; ``comment`` trails the opening line (a REVIEWED tag reads there)."""
        self.line(header + " = {" + (" # " + comment if comment else ""))
        self.depth += 1
        try:
            yield
        finally:
            self.depth -= 1
            self.line("}")

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def slot_cultures(merge: cfg.Merge) -> list[str]:
    """Every culture in the merge's slots, core first, in roster order."""
    return [c for part in merge.core + merge.optional for c in part.cultures]


def _joinable_slot_cultures(merge: cfg.Merge) -> list[str]:
    """Every slot culture a starter can bring in: all but an absorb merge's result, which is never joined."""
    return [c for c in slot_cultures(merge) if not _is_absorb_result(merge, c)]


def _part_of(merge: cfg.Merge, culture: str) -> cfg.Part:
    for part in merge.core + merge.optional:
        if culture in part.cultures:
            return part
    raise ValueError("%s is not a part of the %s merge" % (culture, merge.key))


def _core_cultures(merge: cfg.Merge) -> list[str]:
    return [c for part in merge.core for c in part.cultures]


def _primary_cultures(merge: cfg.Merge) -> list[str]:
    """The cultures that make a country a candidate for the merge when one is primary: its core cultures, and its
    result. A core part that has switched is removed from the primary cultures (te_cm_monthly_switched_culture), so
    after a merge returned to idle with its starter gone, the result is all a country may have left of them. No
    country has an untouched merge's result (te_cmg_strip_untouched_results), so the result opens nothing early."""
    cultures = _core_cultures(merge)
    return cultures if merge.result in cultures else cultures + [merge.result]


def _is_absorb_result(merge: cfg.Merge, culture: str) -> bool:
    """An absorb merge's result culture: held and acceptance-tested only, never joined or switched."""
    return merge.new is None and culture == merge.result


def switchable_cultures(merges: tuple[cfg.Merge, ...]) -> list[str]:
    """Every culture some merge can join and switch, once, in roster order: all slot cultures but an
    absorb merge's own result (British is Anglophone's core part though it is the British merge's result)."""
    seen: dict[str, None] = {}
    for merge in merges:
        for culture in _joinable_slot_cultures(merge):
            seen.setdefault(culture)
    return list(seen)


def _state_idle(key: str) -> str:
    return "NOR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 }" % (key, key)


def _state_running_or_complete(key: str) -> list[str]:
    return ["OR = {", "\tglobal_var:te_cm_state_%s ?= 1" % key, "\tglobal_var:te_cm_state_%s ?= 2" % key, "}"]


def _available_clauses(merge: cfg.Merge, culture: str, merges: tuple[cfg.Merge, ...]) -> list[str]:
    """What makes a slot culture free for this merge.

    Not joined to any other merge that lists it (``te_cm_in_<c>`` holds the index of
    the merge it joined, so each other index is its own ``?=`` test: a missing
    variable is false there, which is the idle case), and, for the result of
    another merge M (an absorb result such as ``french`` or a ``cm_`` id), only once M is
    finished (R33): complete with every part that joined switched, or with no part
    joined at all. Merges chain only after the lower one is done, so a higher merge never
    switches a result that parts of the lower one are still converting into.
    """
    clauses = []
    for index, other in enumerate(merges, start=1):
        if other is not merge and culture in slot_cultures(other):
            clauses.append("NOT = { global_var:te_cm_in_%s ?= %d }" % (culture, index))
    for other in merges:
        if other is not merge and other.result == culture:
            clauses.append("OR = {")
            clauses.append("\tAND = {")
            clauses.append("\t\tglobal_var:te_cm_state_%s ?= 2" % other.key)
            clauses.append("\t\tte_cmg_%s_all_switched = yes" % other.key)
            clauses.append("\t}")
            clauses.append("\tNOR = {")
            for part in _joinable_slot_cultures(other):
                clauses.append("\t\tglobal_var:te_cm_joined_%s_%s ?= 1" % (other.key, part))
            clauses.append("\t}")
            clauses.append("}")
    return clauses


def switched_into(merges: tuple[cfg.Merge, ...]) -> dict[str, list[str]]:
    """For each result culture some merge makes, the cultures that can switch into it, in roster order. A part
    that is itself a result (cm_italian, a part of Latin) has parts of its own: the chain the homeland tie-in
    follows. The roster nests results one way only, so the chain ends (checked here: no culture is below itself)."""
    below: dict[str, list[str]] = {}
    for merge in merges:
        for culture in _joinable_slot_cultures(merge):
            if culture not in below.setdefault(merge.result, []):
                below[merge.result].append(culture)

    def walk(culture: str, seen: tuple[str, ...]) -> None:
        if culture in seen:
            raise ValueError("the merge roster nests %s inside itself: %s" % (culture, " > ".join(seen + (culture,))))
        for part in below.get(culture, ()):
            walk(part, seen + (culture,))

    for result in below:
        walk(result, ())
    return below


def fervor_copy_order(merges: tuple[cfg.Merge, ...]) -> list[str]:
    """Every culture that can switch, ordered so the fervor copy settles a chain in one pass: a culture copies from the
    one it switched into, so that one is copied first. A culture's height is how many switches lie above it (cm_italian
    switches into cm_latin: 1; North Italian into cm_italian: 2), taken over every merge it could switch in (overlapping
    merges); lower heights first, roster order within a height."""
    above: dict[str, list[str]] = {}
    for merge in merges:
        for culture in _joinable_slot_cultures(merge):
            if merge.result not in above.setdefault(culture, []):
                above[culture].append(merge.result)
    switched_into(merges)  # raises on a roster that nests a culture inside itself, which would loop below

    def height(culture: str) -> int:
        return max((1 + height(result) for result in above.get(culture, ())), default=0)

    cultures = switchable_cultures(merges)
    return sorted(cultures, key=lambda c: (height(c), cultures.index(c)))


def fervor_ladder() -> list[tuple[int, list[float], float]]:
    """The fervor copy's ladder, as data: for each band of ten, from the top, its lower bound, the steps tested inside
    it (highest first) and the value its ``else`` sets. A culture's fervor is set to the highest step at or below the
    source's (0.5 apart), so a copy never reads above the culture it copies and loses less than half a point.
    Vanilla's ``set_fervor`` is documented with a literal only (``set_fervor = 3.0``), and an effect that reads a
    named script value as 0 would zero the culture, so every set is a literal (R41)."""
    bands = []
    for low in range(90, -1, -10):
        top = 100.0 if low == 90 else low + 9.5
        steps = []
        v = top
        while v > low:
            steps.append(v)
            v -= 0.5
        bands.append((low, steps, float(low)))
    return bands


def _fervor_literal(value: float) -> str:
    return ("%.1f" % value).rstrip("0").rstrip(".")


def result_can_switch(merge: cfg.Merge, merges: tuple[cfg.Merge, ...]) -> bool:
    """Some merge lists this merge's result as a part (a ``cm_`` result that is a component, or an absorb result
    such as ``french`` that another merge lists), so it can switch into a wider culture (R33, R36)."""
    return merge.result in switchable_cultures(merges)


def _result_switched(merge: cfg.Merge) -> str:
    """The merge's result has switched into a higher merge's result (R33): the merge does nothing more.

    A call of the generated ``te_cmg_<m>_result_switched``, the one place the rule is written (M6): is_candidate,
    can_start, can_join, join_ready, the start effect, census_wanted, the yearly conversion, dominance, the
    formation hook and the entry's invalid outcome all read it."""
    return "te_cmg_%s_result_switched = yes" % merge.key


def _result_joined_higher(merge: cfg.Merge) -> str:
    """A higher merge has joined this merge's result and not yet switched it (te_cm_in_<r>, R38 I1). The lower merge
    then takes no new part: a late part would make its result unavailable to the higher merge again (R33), and
    once the result switched, the late part would be stranded joined and unswitched."""
    return "has_global_variable = te_cm_in_%s" % merge.result


def _write_result_switched(out: "_Script", merge: cfg.Merge, merges: tuple[cfg.Merge, ...]) -> None:
    """``te_cmg_<m>_result_switched``, any scope (R33, M6). For a result no other merge can take, ``always = no``:
    nothing ever sets ``te_cm_switched_<r>`` for it, and reading the name anyway logs ``is used but is never set`` at
    every load (13 results, 2026-11-08)."""
    out.line()
    out.line("# Any scope. The %s merge's result has switched into a higher merge's (R33): the merge then joins, converts," % merge.key)
    out.line("# measures and switches nothing more, and is no candidate. Never true for a result no other merge lists.")
    with out.block("te_cmg_%s_result_switched" % merge.key):
        if result_can_switch(merge, merges):
            out.line("has_global_variable = te_cm_switched_%s" % merge.result)
        else:
            out.line("always = no")


def _joinable_elsewhere(merge: cfg.Merge, culture: str, merges: tuple[cfg.Merge, ...]) -> bool:
    """Another merge can join and switch ``culture`` (it is a slot culture there and not that merge's own absorb result)."""
    return any(other is not merge and culture in _joinable_slot_cultures(other) for other in merges)


def core_left_slots(merge: cfg.Merge, merges: tuple[cfg.Merge, ...]) -> list[cfg.Part]:
    """The core slots another merge can empty (R38 M2): every alternative is a culture some other merge can join and
    switch. A slot with an alternative only this merge can switch is never empty, since that culture switches only
    after joining here; a slot that is only this merge's absorb result is the result-switched test's."""
    slots = []
    for part in merge.core:
        if all(_joinable_elsewhere(merge, c, merges) for c in part.cultures) and not all(
            _is_absorb_result(merge, c) for c in part.cultures
        ):
            slots.append(part)
    return slots


def _write_core_left(out: "_Script", merge: cfg.Merge, merges: tuple[cfg.Merge, ...]) -> None:
    """``te_cmg_<m>_core_left``, any scope, for a merge with core slots another merge can empty (R38 M2)."""
    key = merge.key
    out.line()
    out.line("# Any scope. Every core slot of the %s merge that another merge can take still has an alternative that has not" % key)
    out.line("# switched there: unswitched, or joined to this merge (and so switched here). Once a higher merge has switched")
    out.line("# a core part, the %s merge can never start: it is no candidate, and a candidate's entry ends." % key)
    with out.block("te_cmg_%s_core_left" % key):
        for part in core_left_slots(merge, merges):
            with out.block("OR"):
                for culture in part.cultures:
                    out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
                    if not _is_absorb_result(merge, culture):
                        out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))


def _live_culture(culture: str) -> list[str]:
    """A slot culture that has neither switched nor vanished from the world."""
    return [
        "AND = {",
        "\tNOT = { has_global_variable = te_cm_switched_%s }" % culture,
        "\tany_country = { culture_percent_country = { target = cu:%s value > 0 } }" % culture,
        "}",
    ]


def _years_clause(tier: int) -> str:
    """The counter a tier-2 or tier-3 part must have reached: the 1b or the tier-2 years."""
    return "te_cm_years_tier2" if tier == 2 else "te_cm_years_tier3"


def _slot_routes(merge: cfg.Merge, part: cfg.Part, tiers: dict[str, int]) -> list[list[str]]:
    """The ways one core slot is met, each a list of clauses all of which must hold.

    An alternative is met when it passes its gates now (and, in tier 1b or tier 2, has its years
    together, and, when its tier is not the one the merge starts at, the technology of its own
    tier: ``is_candidate`` asks only for the start tier's, and ``can_join`` for the part's own),
    or when it joined this merge and has switched. ``core_ok``, ``can_start`` and the status
    line all read the same routes.
    """
    key = merge.key
    start = max(tiers[p.cultures[0]] for p in merge.core)
    routes = []
    for c in part.cultures:
        route = ["te_cmg_%s_%s_measured = yes" % (key, c)]
        if tiers[c] != start:
            route.append("te_cm_tier_tech = { TIER = %d }" % tiers[c])
        if tiers[c] > 1:
            route.append("te_cmg_%s_%s_years_met = yes" % (key, c))
        routes.append(route)
        if not _is_absorb_result(merge, c):
            routes.append(["te_cmg_%s_%s_switched_in = yes" % (key, c)])
    return routes


def _write_routes(out: "_Script", routes: list[list[str]]) -> None:
    if len(routes) == 1:
        for clause in routes[0]:
            out.line(clause)
        return
    with out.block("OR"):
        for route in routes:
            if len(route) == 1:
                out.line(route[0])
            else:
                with out.block("AND"):
                    for clause in route:
                        out.line(clause)


def core_waits(merge: cfg.Merge) -> list[cfg.Part]:
    """The core parts that wait on a vanilla journal entry, one per distinct set of entries.

    Two parts that wait on the same entry (German's North and South, both on the unification idea)
    share a start condition, a status row and a tooltip, named for the first of them, so the entry
    lists the wait once.
    """
    waits: list[cfg.Part] = []
    for part in merge.core:
        if part.wait_for and all(set(w.wait_for) != set(part.wait_for) for w in waits):
            waits.append(part)
    return waits


def _wait_cap_reached(out: "_Script", key: str) -> None:
    """The merge's wait years have reached te_cm_wait_cap_years (false while the counter is unset)."""
    counter = "te_cm_wait_years_%s" % key
    with out.block("AND"):
        out.line("has_variable = %s" % counter)
        out.line("trigger_if = { limit = { has_variable = %s } var:%s >= te_cm_wait_cap_years }" % (counter, counter))


def _wait_entry_open(out: "_Script", entries: tuple[str, ...]) -> None:
    """A vanilla entry the part waits on is open in any country (R37).

    Not only the candidate's: a switch turns the part's pops into the result in every country, and
    the entry's fervor or share reads, in every country that holds it, break with them. ``any_country``
    takes no ``limit``, so the entries sit in one ``OR`` inside it.
    """
    with out.block("any_country"):
        if len(entries) == 1:
            out.line("has_journal_entry = %s" % entries[0])
            return
        with out.block("OR"):
            for entry in entries:
                out.line("has_journal_entry = %s" % entry)


def _gate_ok(merge: cfg.Merge) -> str:
    """The merge's own precondition holds (cfg.Gate): a call of the generated ``te_cmg_<m>_gate_ok``."""
    return "te_cmg_%s_gate_ok = yes" % merge.key


def gate_latch(merge: cfg.Merge) -> str:
    """The country variable that keeps a milestone gate met once it was: the census and the start set it."""
    return "te_cm_gate_met_%s" % merge.key


def standing_gate(merge: cfg.Merge) -> bool:
    """The merge has a gate that is read for as long as it runs (slavery, schooling, independence)."""
    return merge.gate is not None and not merge.gate.milestone


def milestone_gate(merge: cfg.Merge) -> bool:
    """The merge has a gate that, once met, stays met (a formation, the Meiji restoration)."""
    return merge.gate is not None and merge.gate.milestone


def _sentence(clause: str) -> str:
    """A gate's clause as a condition line: capitalized, with a full stop."""
    return clause[0].upper() + clause[1:] + "."


def _write_gate_ok(out: "_Script", merge: cfg.Merge) -> None:
    """``te_cmg_<m>_gate_ok``, country scope, for a merge with a gate. A milestone is met for good once the census or the
    start has latched it; a standing one is its trigger alone."""
    gate = merge.gate
    out.line()
    if gate.milestone:
        out.line("# Country scope. The %s merge's own precondition, a milestone (%s): met now, or latched in %s" % (merge.key, gate.trigger, gate_latch(merge)))
        out.line("# by a census or the start while it was, so a later formation or a civil war's winner keeps it. Read only to start.")
        with out.block("te_cmg_%s_gate_ok" % merge.key):
            with out.block("OR"):
                out.line("has_variable = %s" % gate_latch(merge))
                out.line("%s = yes" % gate.trigger)
    else:
        out.line("# Country scope. The %s merge's own precondition, a standing one (%s): read to start and, on the starter," % (merge.key, gate.trigger))
        out.line("# for as long as the merge runs. While it fails, no culture joins and none converts, complete or not.")
        with out.block("te_cmg_%s_gate_ok" % merge.key):
            out.line("%s = yes" % gate.trigger)


def _result_exists(merge: cfg.Merge) -> str:
    """A new result culture is there to merge into. The engine makes a culture's object when a game starts, so a game
    begun before the culture was added has none: ``cu:<result>`` is empty there, and starting the merge would add that
    empty culture as a primary culture and convert pops into it (a 1883 save from before #1509, 2026-11-08: every
    vanilla trigger that walks a primary culture logged ``Culture (-1)``, about 8,700 lines in two hours). Such a game
    never starts the merge. Vanilla guards a culture the same way (``exists = cu:venezuelan``, 00_major_formables.txt)."""
    return "exists = cu:%s" % merge.result


def _write_start_items(out: "_Script", merge: cfg.Merge, tier: int, tiers: dict[str, int], merges: tuple[cfg.Merge, ...]) -> None:
    """The conditions that let a country start the merge, except its waits, each in its own
    custom_tooltip so the button lists the one that fails. They restate every condition of ``is_candidate``
    (the rule, which the button and the entry gate on their own, apart), so a country that is no candidate
    cannot start: the merge being idle, a core culture primary, the technology, the merge's result not
    switched into a wider culture (R36: pressing the button would start a merge whose result has gone) and
    the skipped DLC absent. Then the merge's own gate (cfg.Gate), ``core_ok``'s slots (the same routes), the
    standard-of-living gate and the component merges. ``test_culture_merge_switch`` pins that none of ``is_candidate``'s conditions is missing."""
    key = merge.key
    if merge.new is not None:
        # The result culture exists (is_candidate's first test), out of the button's reasons: it fails only in a game
        # started before the culture was added.
        with out.block("hidden_trigger"):
            out.line(_result_exists(merge))
    with out.block("custom_tooltip"):
        out.line("text = te_cm_tt_idle")
        out.line(_state_idle(key))
    if result_can_switch(merge, merges):
        with out.block("custom_tooltip"):
            out.line("text = te_cm_tt_result_not_merged_on")
            out.line("NOT = { %s }" % _result_switched(merge))
    if merge.skip_if_dlc:
        with out.block("custom_tooltip"):
            out.line("text = te_cm_tt_dlc_off_%s" % merge.skip_if_dlc)
            out.line("NOT = { has_dlc_feature = %s }" % merge.skip_if_dlc)
    with out.block("custom_tooltip"):
        out.line("text = te_cmg_%s_primary_tt" % key)
        with out.block("OR"):
            for culture in _primary_cultures(merge):
                out.line("country_has_primary_culture = cu:%s" % culture)
    with out.block("custom_tooltip"):
        out.line("text = te_cm_tt_tech_%d" % tier)
        out.line("te_cm_tier_tech = { TIER = %d }" % tier)
    if merge.gate:
        with out.block("custom_tooltip"):
            out.line("text = te_cmg_%s_gate_tt" % key)
            out.line(_gate_ok(merge))
    for index, part in enumerate(merge.core, start=1):
        with out.block("custom_tooltip"):
            out.line("text = te_cmg_%s_core_%d_tt" % (key, index))
            _write_routes(out, _slot_routes(merge, part, tiers))
    # An inactive entry's page lists these lines and no status row (2026-11-09), so the gap line itself names the two
    # ends and the gap once the census has kept them; reading them unset would log on every redraw, hence the guard.
    # The pair tests one gate either way (a trigger_if whose limit fails passes, so the trigger_else must follow it).
    with out.block("trigger_if"):
        out.line("limit = { has_variable = te_cm_sol_gap_%s }" % key)
        with out.block("custom_tooltip"):
            out.line("text = te_cmg_%s_sol_tt" % key)
            out.line("var:te_cm_sol_ok_%s ?= 1" % key)
    with out.block("trigger_else"):
        with out.block("custom_tooltip"):
            out.line("text = te_cm_tt_sol")
            out.line("var:te_cm_sol_ok_%s ?= 1" % key)
    for component in merge.components:
        with out.block("custom_tooltip"):
            out.line("text = te_cmg_%s_comp_%s_tt" % (key, component))
            out.line("global_var:te_cm_state_%s ?= 2" % component)


def _write_wait_items(out: "_Script", merge: cfg.Merge) -> None:
    """One custom_tooltip per wait: its vanilla entries are closed in every country, or the
    merge has waited long enough."""
    key = merge.key
    for part in core_waits(merge):
        with out.block("custom_tooltip"):
            out.line("text = te_cmg_%s_wait_%s_tt" % (key, part.cultures[0]))
            with out.block("OR"):
                with out.block("NOT"):
                    _wait_entry_open(out, part.wait_for)
                _wait_cap_reached(out, key)


def render_triggers(vanilla: dict, merges: tuple[cfg.Merge, ...] | None = None,
                    holds: dict[str, ledger.Holds] | None = None) -> str:
    """The per-merge scripted triggers.

    Per merge: ``result_switched``, ``core_left`` (where another merge can take a core part),
    ``is_candidate``, ``core_ok``, ``census_wanted``, ``is_starter``,
    ``has_other_starter``, ``can_start`` (and ``start_basics`` where a core part waits on a
    vanilla entry). Per slot culture: ``available``, ``measured`` (passing its gates now and
    not switched), ``years_met`` (tiers 2 and 3), ``switched_in`` (joined to this merge and
    switched: met for good), ``can_join`` and, where its part waits on a vanilla entry,
    ``waiting``. ``holds`` is the ledger's hold per switchable culture (the real roster's by default; none for a test
    roster).
    """
    if holds is None:
        holds = ledger.part_holds() if merges is None else {}
    merges = cfg.MERGES if merges is None else merges
    out = _Script()
    out.line(HEADER)
    for merge in merges:
        key = merge.key
        tier = start_tier(merge, vanilla, merges)
        optional = {c for part in merge.optional for c in part.cultures}
        tiers = {c: cfg.derive_tier(merge, c, vanilla, merges) for c in slot_cultures(merge)}
        core_left = bool(core_left_slots(merge, merges))
        out.line()
        out.line("# ---- %s (%s) ----" % (key, ", ".join("/".join(p.cultures) for p in merge.core)))
        _write_result_switched(out, merge, merges)
        if core_left:
            _write_core_left(out, merge, merges)
        if merge.gate:
            _write_gate_ok(out, merge)
        out.line()
        out.line("# Country scope. Can this country start the %s merge? The system is on, a core culture is" % key)
        out.line("# primary, the technology of the highest core tier is known, the merge is not complete and, where its result is a")
        out.line("# part of another merge, that result has not switched into it (R33: then the merge does nothing more). Where")
        out.line("# another merge can take a core part, that part has not switched there (te_cmg_<m>_core_left, R38).")
        with out.block("te_cmg_%s_is_candidate" % key):
            out.line("te_cm_system_enabled = yes")
            if merge.new is not None:
                out.line(_result_exists(merge))
            with out.block("OR"):
                for culture in _primary_cultures(merge):
                    out.line("country_has_primary_culture = cu:%s" % culture)
            out.line("te_cm_tier_tech = { TIER = %d }" % tier)
            out.line("NOT = { global_var:te_cm_state_%s ?= 2 }" % key)
            if result_can_switch(merge, merges):
                out.line("NOT = { %s }" % _result_switched(merge))
            if core_left:
                out.line("te_cmg_%s_core_left = yes" % key)
            if merge.skip_if_dlc:
                out.line("NOT = { has_dlc_feature = %s }" % merge.skip_if_dlc)
        out.line()
        out.line("# Country scope. Every core slot is met: an alternative that passes its gates now (and, in tier 1b or")
        out.line("# tier 2, has its years together), or one that joined this merge and has switched.")
        with out.block("te_cmg_%s_core_ok" % key):
            for part in merge.core:
                _write_routes(out, _slot_routes(merge, part, tiers))
        for culture in slot_cultures(merge):
            ctier = tiers[culture]
            out.line()
            out.line("# Any scope. %s is free for the %s merge." % (culture, key))
            with out.block("te_cmg_%s_%s_available" % (key, culture)):
                clauses = _available_clauses(merge, culture, merges)
                for clause in clauses or ["always = yes"]:
                    out.line(clause)
            out.line()
            out.line("# Country scope. %s passes its gates for the %s merge now: held and accepted, free for it," % (culture, key))
            out.line("# and not yet switched (a switched part has no pops left to measure).")
            with out.block("te_cmg_%s_%s_measured" % (key, culture)):
                out.line("var:te_cm_ok_%s_%s ?= 1" % (key, culture))
                out.line("te_cmg_%s_%s_available = yes" % (key, culture))
                out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
            if ctier > 1:
                years = "te_cm_years_%s_%s" % (key, culture)
                out.line()
                out.line("# Country scope. %s (tier %s) has spent the years together its tier asks for." % (culture, ("1", "1b", "2")[ctier - 1]))
                with out.block("te_cmg_%s_%s_years_met" % (key, culture)):
                    out.line("has_variable = %s" % years)
                    out.line("trigger_if = { limit = { has_variable = %s } var:%s >= %s }" % (years, years, _years_clause(ctier)))
            if not _is_absorb_result(merge, culture):
                out.line()
                out.line("# Country scope. %s joined the %s merge and has switched into its result." % (culture, key))
                with out.block("te_cmg_%s_%s_switched_in" % (key, culture)):
                    out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
                    out.line("has_global_variable = te_cm_switched_%s" % culture)
            out.line()
            out.line("# Country scope. %s (tier %s) passes its gates and can join the %s merge now: it has not switched" % (culture, ("1", "1b", "2")[ctier - 1], key))
            if result_can_switch(merge, merges):
                out.line("# (R32), the merge's own result has not (R33) and no higher merge has joined that result (R38), and the rest")
                out.line("# of its gates hold.")
            else:
                out.line("# (R32), the merge's own result has not (R33), and the rest of its gates hold.")
            with out.block("te_cmg_%s_%s_can_join" % (key, culture)):
                out.line("var:te_cm_ok_%s_%s ?= 1" % (key, culture))
                out.line("te_cmg_%s_%s_available = yes" % (key, culture))
                out.line("NOT = { global_var:te_cm_joined_%s_%s ?= 1 }" % (key, culture))
                out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
                out.line("NOT = { %s }" % _result_switched(merge))
                if result_can_switch(merge, merges):
                    out.line("NOT = { %s }" % _result_joined_higher(merge))
                out.line("te_cm_tier_tech = { TIER = %d }" % ctier)
                if ctier > 1:
                    out.line("te_cmg_%s_%s_years_met = yes" % (key, culture))
                if culture in optional:
                    out.line("var:te_cm_sol_ok_%s_%s ?= 1" % (key, culture))
                part_gate = _part_of(merge, culture).gate
                if part_gate:
                    out.line("%s = yes" % part_gate.trigger)
            wait_for = _part_of(merge, culture).wait_for
            if wait_for and not _is_absorb_result(merge, culture):
                out.line()
                out.line("# Country scope. %s waits on a vanilla journal entry that some country holds (%s, R37) and the merge" % (culture, ", ".join(wait_for)))
                out.line("# has not yet waited te_cm_wait_cap_years: it doesn't join, and a core part doesn't let the merge start.")
                with out.block("te_cmg_%s_%s_waiting" % (key, culture)):
                    _wait_entry_open(out, wait_for)
                    with out.block("NOT"):
                        _wait_cap_reached(out, key)
        out.line()
        out.line("# Any scope. Is the yearly census of the %s merge worth running? An idle merge with a" % key)
        out.line("# candidate; or a running or complete one whose starter is alive and which still has a")
        out.line("# part that has neither switched nor left the world (a complete merge keeps its census so")
        out.line("# late parts can join). An absorb merge's result never switches, so it doesn't count. Not once the")
        out.line("# merge's own result has switched into a higher merge's (R33): nothing more is joined or measured.")
        with out.block("te_cmg_%s_census_wanted" % key):
            with out.block("OR"):
                with out.block("AND"):
                    out.line(_state_idle(key))
                    out.line("any_country = { te_cmg_%s_is_candidate = yes }" % key)
                with out.block("AND"):
                    for line in _state_running_or_complete(key):
                        out.line(line)
                    out.line("exists = global_var:te_cm_starter_%s" % key)
                    with out.block("trigger_if"):
                        out.line("limit = { exists = global_var:te_cm_starter_%s }" % key)
                        out.line("global_var:te_cm_starter_%s = { is_country_alive = yes }" % key)
                    out.line("NOT = { %s }" % _result_switched(merge))
                    with out.block("OR"):
                        for culture in slot_cultures(merge):
                            if _is_absorb_result(merge, culture):
                                continue
                            for line in _live_culture(culture):
                                out.line(line)
        out.line()
        out.line("# Any scope. The %s merge's starter is missing, or is no longer a living country. Each read of the" % key)
        out.line("# starter sits in a trigger_if behind its exists: the entry's tooltip lists every child of an AND, so a")
        out.line("# guard beside the read stops nothing there (2026-11-08). A trigger_if passes when its limit fails.")
        with out.block("te_cmg_%s_starter_gone" % key):
            with out.block("trigger_if"):
                out.line("limit = { exists = global_var:te_cm_starter_%s }" % key)
                out.line("global_var:te_cm_starter_%s = { is_country_alive = no }" % key)
        out.line()
        out.line("# Country scope. This country started the %s merge, which is running or complete: it is the global starter," % key)
        out.line("# or it carries te_cm_started_%s (set by te_cm_start_merge, inherited by a civil war's winner, which" % key)
        out.line("# continues the nation) while the global starter is missing or dead.")
        with out.block("te_cmg_%s_is_starter" % key):
            for line in _state_running_or_complete(key):
                out.line(line)
            with out.block("OR"):
                with out.block("AND"):
                    out.line("exists = global_var:te_cm_starter_%s" % key)
                    with out.block("trigger_if"):
                        out.line("limit = { exists = global_var:te_cm_starter_%s }" % key)
                        out.line("this = global_var:te_cm_starter_%s" % key)
                with out.block("AND"):
                    out.line("has_variable = te_cm_started_%s" % key)
                    out.line("te_cmg_%s_starter_gone = yes" % key)
        out.line()
        out.line("# Country scope. The %s merge is running or complete under another living country: this one is not its" % key)
        out.line("# global starter and carries no te_cm_started_%s." % key)
        with out.block("te_cmg_%s_has_other_starter" % key):
            for line in _state_running_or_complete(key):
                out.line(line)
            out.line("exists = global_var:te_cm_starter_%s" % key)
            with out.block("trigger_if"):
                out.line("limit = { exists = global_var:te_cm_starter_%s }" % key)
                out.line("global_var:te_cm_starter_%s = { is_country_alive = yes }" % key)
                out.line("NOT = { this = global_var:te_cm_starter_%s }" % key)
            out.line("NOT = { has_variable = te_cm_started_%s }" % key)
        out.line()
        out.line("# Any scope. No part of the %s merge that joined is still unswitched: a part that joins late, after the" % key)
        out.line("# core has switched and the merge is complete, keeps the merge from concluding until it has switched too.")
        with out.block("te_cmg_%s_all_switched" % key):
            with out.block("NOR"):
                for culture in _joinable_slot_cultures(merge):
                    with out.block("AND"):
                        out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
                        out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
        out.line()
        out.line("# Any scope. The %s merge's core is switched: no core part that joined is left unswitched, and at least one" % key)
        out.line("# has switched. The second clause keeps an optional part that switches first from completing a merge whose core")
        out.line("# has not begun. te_cm_switch_part sets the merge's state to 2 on this.")
        with out.block("te_cmg_%s_core_switched" % key):
            joinable_core = [c for c in _core_cultures(merge) if not _is_absorb_result(merge, c)]
            with out.block("OR"):
                for culture in joinable_core:
                    with out.block("AND"):
                        out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
                        out.line("has_global_variable = te_cm_switched_%s" % culture)
            with out.block("NOR"):
                for culture in joinable_core:
                    with out.block("AND"):
                        out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
                        out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
        waits = core_waits(merge)
        out.line()
        if waits:
            out.line("# Country scope. Everything the %s merge needs to start except its waits on vanilla entries" % key)
            out.line("# (each condition its own custom_tooltip). The census adds a wait year while this holds and an entry is open.")
            with out.block("te_cmg_%s_start_basics" % key):
                _write_start_items(out, merge, tier, tiers, merges)
            out.line()
        out.line("# Country scope. Can this country start the %s merge now? The merge is idle, a core culture is" % key)
        out.line("# primary, the technology is known, every core slot is met, the standard-of-living gap is closed, the" )
        out.line("# component merges are complete and no vanilla entry on a core part is still open in any country (or the wait ran its course)." )
        out.line("# Each condition sits in its own custom_tooltip, which the button and the entry show as a reason.")
        with out.block("te_cmg_%s_can_start" % key):
            if waits:
                out.line("te_cmg_%s_start_basics = yes" % key)
            else:
                _write_start_items(out, merge, tier, tiers, merges)
            _write_wait_items(out, merge)
    cultures = switchable_cultures(merges)
    out.line()
    out.line("# ---- Switched parts ----")
    out.line()
    out.line("# Culture scope. This culture is one of the %d that can switch into a merge's result, and it has." % len(cultures))
    out.line("# A test for the flavor patches of spec 7 (party names, formable names ...); nothing reads it yet.")
    with out.block("te_cmg_is_switched_part"):
        with out.block("OR"):
            for culture in cultures:
                with out.block("AND"):
                    out.line("has_global_variable = te_cm_switched_%s" % culture)
                    out.line("this = cu:%s" % culture)
    out.line()
    out.line("# Culture scope; ROOT = the state, as in te_homeland_removal_candidate. Dynamic Homeland Progress leaves this")
    out.line("# culture's homeland in ROOT alone: it is a part that has switched, and the culture it switched into is")
    out.line("# a homeland of the state too (owner, 2026-11-07). The part's homeland follows its successor's: once that is removed")
    out.line("# (te_cmg_remove_switched_part_homelands) the part's goes with it. Not behind the rule: it is about map state.")
    out.line("# has_global_variable comes first in every clause, so a game with nothing switched prunes all %d at once." % len(cultures))
    with out.block("te_cmg_switched_part_kept"):
        with out.block("OR"):
            for culture in cultures:
                with out.block("AND"):
                    out.line("has_global_variable = te_cm_switched_%s" % culture)
                    out.line("this = cu:%s" % culture)
                    out.line("ROOT.state_region = { is_homeland = global_var:te_cm_switched_%s }" % culture)
    _write_dead_primary_triggers(out, merges, holds)
    return out.text()


def _write_dead_primary_triggers(out: "_Script", merges: tuple[cfg.Merge, ...], holds: dict[str, ledger.Holds]) -> None:
    """``te_cmg_<m>_untouched`` per merge that makes a culture, and ``te_cmg_part_held_<c>`` per culture that can
    switch (owner, 2026-11-09: a switched part leaves the primary cultures once nothing is tied to it)."""
    out.line()
    out.line("# ---- Dead primary cultures ----")
    for merge in merges:
        if merge.new is None:
            continue
        key = merge.key
        out.line()
        out.line("# Any scope. The %s merge never began: it is idle and no part has joined it (a merge returned to idle" % key)
        out.line("# keeps its joined parts). Its result then has no people, and no country should have it as a primary culture:")
        out.line("# a formable's definition lists it (zz_te_culture_merge_definitions.txt), and forming adds every culture listed.")
        with out.block("te_cmg_%s_untouched" % key):
            with out.block("NOR"):
                out.line("global_var:te_cm_state_%s ?= 1" % key)
                out.line("global_var:te_cm_state_%s ?= 2" % key)
                for culture in _joinable_slot_cultures(merge):
                    out.line("has_global_variable = te_cm_joined_%s_%s" % (key, culture))
    out.line()
    out.line("# Any scope, one per culture that can switch. Is anything still tied to this culture being a primary culture? While")
    out.line("# it is, te_cm_monthly_switched_culture leaves the switched culture among a country's primary cultures. From the")
    out.line("# ledger of vanilla's reads (scripts/generators/culture_merge_primary_ledger.py): a vanilla journal entry that")
    out.line("# tests the culture and that some country has active holds it whenever; until %s, vanilla's end date" % ledger.WINDOW_END)
    out.line("# so do the reads the owner ruled to keep (historical characters, flavor events, laws, Siberian exile; \"none should")
    out.line("# hold past 1936\") and, by the designer's extension of that date, such an entry on offer and a formable that needs")
    out.line("# the culture and does not exist. Any country, not this one: an entry also tests its targets' and its overlord's")
    out.line("# cultures.")
    for culture in switchable_cultures(merges):
        hold = holds.get(culture, ledger.Holds())
        out.line()
        with out.block("te_cmg_part_held_%s" % culture):
            if not hold.any:
                out.line("always = no")
                continue
            with out.block("OR"):
                if hold.cases:
                    out.line("game_date < %s # %s" % (ledger.WINDOW_END, ", ".join(hold.cases)))
                elif hold.unformed or hold.entries:
                    with out.block("AND"):
                        out.line("game_date < %s" % ledger.WINDOW_END)
                        with out.block("OR"):
                            for tag in hold.unformed:
                                out.line("NOT = { exists = c:%s }" % tag)
                            if hold.entries:
                                with out.block("any_country"):
                                    with out.block("OR"):
                                        for entry in hold.entries:
                                            out.line("has_inactive_journal_entry = %s" % entry)
                if hold.entries:
                    with out.block("any_country"):
                        with out.block("OR"):
                            for entry in hold.entries:
                                out.line("has_journal_entry = %s" % entry)


def _write_start_effects(out: "_Script", merge: cfg.Merge, merges: tuple[cfg.Merge, ...]) -> None:
    """``join_ready``, ``settle`` and ``start`` of one merge.

    ``join_ready`` (country scope): joins every slot culture, except an absorb merge's result, that
    passes ``can_join`` and isn't waiting on a vanilla entry. The start button and the yearly
    census (for a running or complete merge's starter, so a part that comes up late still joins) run it.
    ``settle`` (country scope) is the tail of the per-country census: a wait year, the journal entry's
    net, the late joins. ``start`` is the button's effect.
    """
    key = merge.key
    index = 1 + merges.index(merge)
    entry = "je_te_cm_%s" % key
    out.line()
    out.line("# Country scope. Joins every part of the %s merge that can join now and isn't waiting on a" % key)
    out.line("# vanilla entry: when the merge starts, and each census while its starter holds it. Nothing joins once the")
    if result_can_switch(merge, merges):
        out.line("# merge's own result has switched into a higher merge's (R33), nor once a higher merge has joined it (R38).")
    else:
        out.line("# merge's own result has switched into a higher merge's (R33).")
    if standing_gate(merge):
        out.line("# Nor while the merge's standing gate (%s) fails." % merge.gate.trigger)
    with out.block("te_cmg_%s_join_ready" % key):
        with out.block("if"):
            if result_can_switch(merge, merges) or standing_gate(merge):
                with out.block("limit"):
                    out.line("NOT = { %s }" % _result_switched(merge))
                    if result_can_switch(merge, merges):
                        out.line("NOT = { %s }" % _result_joined_higher(merge))
                    if standing_gate(merge):
                        out.line(_gate_ok(merge))
            else:
                out.line("limit = { NOT = { %s } }" % _result_switched(merge))
            for culture in slot_cultures(merge):
                if _is_absorb_result(merge, culture):
                    continue
                with out.block("if"):
                    with out.block("limit"):
                        out.line("te_cmg_%s_%s_can_join = yes" % (key, culture))
                        if _part_of(merge, culture).wait_for:
                            out.line("NOT = { te_cmg_%s_%s_waiting = yes }" % (key, culture))
                    out.line("te_cm_join_part = { MERGE = %s CULTURE = %s INDEX = %d }" % (key, culture, index))
    out.line()
    out.line("# Country scope: the button's effect. The country starts the %s merge and brings in the parts it" % key)
    out.line("# holds that qualify now. Only an idle merge starts: a second click on the same day finds it running.")
    if result_can_switch(merge, merges):
        out.line("# Not once its result has switched into a wider culture (R36): that culture has gone, and a start would make it a")
        out.line("# primary culture again. The button's can_start says so too; this is the guard behind it.")
    with out.block("te_cmg_start_%s" % key):
        with out.block("if"):
            if result_can_switch(merge, merges):
                with out.block("limit"):
                    out.line(_state_idle(key))
                    out.line("NOT = { %s }" % _result_switched(merge))
            else:
                out.line("limit = { %s }" % _state_idle(key))
            out.line("te_cm_start_merge = { MERGE = %s RESULT = %s }" % (key, merge.result))
            if milestone_gate(merge):
                # can_start held, so the milestone did: latch it, as the census would.
                out.line("set_variable = { name = %s value = 1 }" % gate_latch(merge))
            out.line("te_cmg_%s_join_ready = yes" % key)
    out.line()
    out.line("# Country scope: the tail of te_cmg_census_%s_country, run after the part gates are fresh." % key)
    out.line("# 1. A wait year, while the merge could start but a vanilla entry on a core part is open in any country (once a census,")
    out.line("#    up to te_cm_wait_cap_years).")
    out.line("# 2. The journal entry's net: an idle merge's candidate that can start, or a running merge's starter,")
    out.line("#    gets the entry back if it holds neither the active nor the inactive record (a rule switched off and on")
    out.line("#    prunes the inactive ones; a concluded entry is gone). It reads the entry's own gate and never adds one for")
    out.line("#    a complete merge, whose finished entry is its end. Merge mechanics never key on the entry.")
    out.line("# 3. Late joins: the starter of a running or complete merge brings in every part that now qualifies.")
    with out.block("te_cmg_%s_settle" % key):
        waits = core_waits(merge)
        if waits:
            counter = "te_cm_wait_years_%s" % key
            with out.block("if"):
                with out.block("limit"):
                    out.line("te_cmg_%s_start_basics = yes" % key)
                    with out.block("OR"):
                        for part in waits:
                            _wait_entry_open(out, part.wait_for)
                with out.block("if"):
                    out.line("limit = { NOT = { has_variable = %s } }" % counter)
                    out.line("set_variable = { name = %s value = 0 }" % counter)
                with out.block("if"):
                    out.line("limit = { var:%s < te_cm_wait_cap_years }" % counter)
                    out.line("change_variable = { name = %s add = 1 }" % counter)
        with out.block("if"):
            with out.block("limit"):
                out.line("te_cm_system_enabled = yes")
                out.line("NOT = { has_journal_entry = %s }" % entry)
                out.line("NOT = { has_inactive_journal_entry = %s }" % entry)
                with out.block("OR"):
                    out.line("te_cmg_%s_can_start = yes" % key)
                    with out.block("AND"):
                        out.line("global_var:te_cm_state_%s ?= 1" % key)
                        out.line("te_cmg_%s_is_starter = yes" % key)
            out.line("add_journal_entry = { type = %s }" % entry)
        with out.block("if"):
            out.line("limit = { te_cmg_%s_is_starter = yes }" % key)
            out.line("te_cmg_%s_join_ready = yes" % key)


def render_effects(vanilla: dict, merges: tuple[cfg.Merge, ...] | None = None) -> str:
    """The per-merge census effects and te_cmg_census_all."""
    merges = cfg.MERGES if merges is None else merges
    out = _Script()
    out.line(HEADER)
    for merge in merges:
        key = merge.key
        cultures = slot_cultures(merge)
        optional = [c for part in merge.optional for c in part.cultures]
        out.line()
        out.line("# ---- %s ----" % key)
        if optional:
            out.line()
            out.line("# Country scope: the candidate (or the running merge's starter). The %s result's average standard of" % key)
            out.line("# living, pop-weighted, over its pops in the sphere's part of the core parts' homeland states (a state")
            out.line("# that is the homeland of several counts once). Sets te_cm_sg_ref, 0 when the result has no pops there.")
            out.line("# The reference an optional part is held against once no core part has a figure left; run only then.")
            with out.block("te_cmg_%s_result_sol" % key):
                out.line("save_temporary_scope_as = te_cm_starter")
                out.line("set_local_variable = { name = te_cm_sg_rpops value = 0 }")
                out.line("set_local_variable = { name = te_cm_sg_rsolw value = 0 }")
                with out.block("every_country"):
                    out.line("limit = { te_cm_in_sphere = yes }")
                    with out.block("every_scope_state"):
                        with out.block("limit"):
                            with out.block("OR"):
                                for culture in _core_cultures(merge):
                                    out.line("state_region = { is_homeland = cu:%s }" % culture)
                        with out.block("every_scope_pop"):
                            out.line("limit = { culture = cu:%s }" % merge.result)
                            out.line("change_local_variable = { name = te_cm_sg_rpops add = total_size }")
                            out.line("change_local_variable = { name = te_cm_sg_rsolw add = { value = standard_of_living multiply = total_size } }")
                with out.block("if"):
                    out.line("limit = { local_var:te_cm_sg_rpops >= 1 }")
                    with out.block("set_local_variable"):
                        out.line("name = te_cm_sg_ref")
                        with out.block("value"):
                            out.line("value = local_var:te_cm_sg_rsolw")
                            out.line("divide = local_var:te_cm_sg_rpops")
        out.line()
        out.line("# Country scope: one candidate (or the running merge's starter). Measures every part that hasn't")
        out.line("# switched, then the standard-of-living gap over the core parts, te_cm_sol_ok_%s, with hysteresis:" % key)
        out.line("# it closes above te_cm_sol_gap_close and reopens below te_cm_sol_gap_open, and opens only while every")
        out.line("# core slot is met (has a figure, or joined and switched). Each optional part then gets its own gate,")
        out.line("# te_cm_sol_ok_%s_<culture>, over the core range plus that part; with no core figure left, against the" % key)
        out.line("# result's (walked only then, and only while an optional part whose own gates are on has not switched, joined or")
        out.line("# not: the gate of a part that has joined must keep following the result, or one dip would freeze it for good).")
        out.line("# The status row names the core gap's two ends: te_cm_sol_best_%s and te_cm_sol_worst_%s (cultures)," % (key, key))
        out.line("# te_cm_sol_hi_%s, te_cm_sol_lo_%s and te_cm_sol_gap_%s, removed while no core part has a figure." % (key, key, key))
        with out.block("te_cmg_census_%s_country" % key):
            if milestone_gate(merge):
                # The milestone, once met, stays met (cfg.Gate): a later formation changes the tag the trigger reads.
                with out.block("if"):
                    with out.block("limit"):
                        out.line("NOT = { has_variable = %s }" % gate_latch(merge))
                        out.line("%s = yes" % merge.gate.trigger)
                    out.line("set_variable = { name = %s value = 1 }" % gate_latch(merge))
            for culture in cultures:
                tier = cfg.derive_tier(merge, culture, vanilla, merges)
                with out.block("if"):
                    out.line("limit = { NOT = { has_global_variable = te_cm_switched_%s } }" % culture)
                    out.line(
                        "te_cm_census_part = { MERGE = %s CULTURE = %s RESULT = %s TIER = %d }"
                        % (key, culture, merge.result, tier)
                    )
            out.line("set_local_variable = { name = te_cm_sg_min value = 999 }")
            out.line("set_local_variable = { name = te_cm_sg_max value = -1 }")
            out.line("set_local_variable = { name = te_cm_sg_n value = 0 }")
            out.line("set_local_variable = { name = te_cm_sg_slots value = 0 }")
            out.line("set_local_variable = { name = te_cm_sg_all value = 0 }")
            for part in merge.core:
                for culture in part.cultures:
                    with out.block("if"):
                        out.line("limit = { te_cmg_%s_%s_measured = yes }" % (key, culture))
                        out.line("te_cm_sol_track = { MERGE = %s CULTURE = %s }" % (key, culture))
                met = ["te_cmg_%s_%s_measured = yes" % (key, c) for c in part.cultures]
                met += ["te_cmg_%s_%s_switched_in = yes" % (key, c) for c in part.cultures if not _is_absorb_result(merge, c)]
                with out.block("if"):
                    if len(met) == 1:
                        out.line("limit = { %s }" % met[0])
                    else:
                        with out.block("limit"):
                            with out.block("OR"):
                                for clause in met:
                                    out.line(clause)
                    out.line("change_local_variable = { name = te_cm_sg_slots add = 1 }")
            with out.block("if"):
                out.line("limit = { local_var:te_cm_sg_slots = %d }" % len(merge.core))
                out.line("set_local_variable = { name = te_cm_sg_all value = 1 }")
            with out.block("if"):
                out.line("limit = { NOT = { has_variable = te_cm_sol_ok_%s } }" % key)
                out.line("set_variable = { name = te_cm_sol_ok_%s value = 0 }" % key)
            # The figures the gate reads, kept for the status row: the best- and worst-off core cultures (culture
            # scopes), their standards of living and the gap. None while no core part has a figure.
            kept = (("best", "te_cm_sg_best"), ("worst", "te_cm_sg_worst"), ("hi", "te_cm_sg_max"),
                    ("lo", "te_cm_sg_min"), ("gap", "te_cm_sg_gap"))
            with out.block("if"):
                out.line("limit = { local_var:te_cm_sg_n > 0 }")
                out.line("set_local_variable = { name = te_cm_sg_gap value = local_var:te_cm_sg_max }")
                out.line("change_local_variable = { name = te_cm_sg_gap subtract = local_var:te_cm_sg_min }")
                for name, local in kept:
                    out.line("set_variable = { name = te_cm_sol_%s_%s value = local_var:%s }" % (name, key, local))
                with out.block("if"):
                    out.line("limit = { var:te_cm_sol_ok_%s = 1 }" % key)
                    with out.block("if"):
                        out.line("limit = { local_var:te_cm_sg_gap > te_cm_sol_gap_close }")
                        out.line("set_variable = { name = te_cm_sol_ok_%s value = 0 }" % key)
                with out.block("else"):
                    with out.block("if"):
                        with out.block("limit"):
                            out.line("local_var:te_cm_sg_gap < te_cm_sol_gap_open")
                            out.line("local_var:te_cm_sg_all = 1")
                        out.line("set_variable = { name = te_cm_sol_ok_%s value = 1 }" % key)
            with out.block("else"):
                for name, _ in kept:
                    out.line("remove_variable = te_cm_sol_%s_%s" % (name, key))
            if optional:
                # The walk only feeds te_cm_sol_gate_part, which reads its figure only for a part whose own gates are on
                # (R38 M1): no walk for a finished merge whose optional parts don't qualify.
                out.line("set_local_variable = { name = te_cm_sg_ref value = 0 }")
                with out.block("if"):
                    with out.block("limit"):
                        out.line("local_var:te_cm_sg_n = 0")
                        out.line("local_var:te_cm_sg_all = 1")
                        with out.block("OR"):
                            for culture in optional:
                                with out.block("AND"):
                                    out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
                                    out.line("var:te_cm_ok_%s_%s ?= 1" % (key, culture))
                    out.line("te_cmg_%s_result_sol = yes" % key)
            for culture in optional:
                with out.block("if"):
                    out.line("limit = { NOT = { has_global_variable = te_cm_switched_%s } }" % culture)
                    out.line("te_cm_sol_gate_part = { MERGE = %s CULTURE = %s }" % (key, culture))
            out.line("te_cmg_%s_settle = yes" % key)
        _write_start_effects(out, merge, merges)
        out.line()
        out.line("# Any scope. An idle merge: every country that can start it. A running or complete one: only its")
        out.line("# starter, so a part that comes up late can still join.")
        with out.block("te_cmg_census_%s" % key):
            with out.block("if"):
                out.line("limit = { %s }" % _state_idle(key))
                with out.block("every_country"):
                    out.line("limit = { te_cmg_%s_is_candidate = yes }" % key)
                    out.line("te_cmg_census_%s_country = yes" % key)
            with out.block("else_if"):
                out.line("limit = { exists = global_var:te_cm_starter_%s }" % key)
                with out.block("global_var:te_cm_starter_%s" % key):
                    out.line("te_cmg_census_%s_country = yes" % key)

    # ---- a running merge whose starter is gone ----
    out.line()
    out.line("# ---- All merges ----")
    out.line()
    out.line("# Any scope. A merge whose starter no longer exists, or is no longer a living country, is picked up by the")
    out.line("# country that carries te_cm_started_<m> (a civil war's winner inherits the loser's variables and continues the")
    out.line("# nation): the first such living country becomes the starter. Only a running merge with no such country goes")
    out.line("# back to idle (te_cm_release_starter), so another country can start it. A complete merge with no such country")
    out.line("# lets go of every part that joined and has not switched (te_cm_unjoin_part, R38), so it is finished and a higher")
    out.line("# merge can take its result (R33). Run first by te_cm_yearly_on_action.")
    with out.block("te_cmg_release_lost_starters"):
        for index, merge in enumerate(merges, start=1):
            key = merge.key
            with out.block("if"):
                with out.block("limit"):
                    for line in _state_running_or_complete(key):
                        out.line(line)
                    out.line("te_cmg_%s_starter_gone = yes" % key)
                with out.block("every_country"):
                    with out.block("limit"):
                        out.line("is_country_alive = yes")
                        out.line("has_variable = te_cm_started_%s" % key)
                    # The first one takes it; once the global names a living country, the rest find it is not gone.
                    with out.block("if"):
                        out.line("limit = { te_cmg_%s_starter_gone = yes }" % key)
                        out.line("set_global_variable = { name = te_cm_starter_%s value = this }" % key)
            with out.block("if"):
                with out.block("limit"):
                    out.line("global_var:te_cm_state_%s ?= 1" % key)
                    out.line("te_cmg_%s_starter_gone = yes" % key)
                out.line("te_cm_release_starter = { MERGE = %s }" % key)
            with out.block("if"):
                with out.block("limit"):
                    out.line("global_var:te_cm_state_%s ?= 2" % key)
                    out.line("te_cmg_%s_starter_gone = yes" % key)
                for culture in _joinable_slot_cultures(merge):
                    out.line("te_cm_unjoin_part = { MERGE = %s CULTURE = %s INDEX = %d }" % (key, culture, index))

    # ---- the global census ----
    wanting: dict[str, list[cfg.Merge]] = {}
    for merge in merges:
        for culture in slot_cultures(merge):
            wanting.setdefault(culture, []).append(merge)
    out.line()
    out.line("# Any scope. Measures every culture of a merge that is worth censusing, once, then runs each")
    out.line("# merge's census. A culture that has switched is skipped; one that has joined a merge is walked")
    out.line("# together with that merge's result (te_cm_census_culture_joined), the others alone. Called from")
    out.line("# te_cm_yearly_on_action behind the rule, the year and the 330-day lock.")
    with out.block("te_cmg_census_all"):
        for culture, owners in wanting.items():
            joinable = [m for m in owners if not _is_absorb_result(m, culture)]
            with out.block("if"):
                with out.block("limit"):
                    out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
                    if len(owners) == 1:
                        out.line("te_cmg_%s_census_wanted = yes" % owners[0].key)
                    else:
                        with out.block("OR"):
                            for owner in owners:
                                out.line("te_cmg_%s_census_wanted = yes" % owner.key)
                for index, owner in enumerate(joinable):
                    with out.block("if" if index == 0 else "else_if"):
                        out.line("limit = { global_var:te_cm_joined_%s_%s ?= 1 }" % (owner.key, culture))
                        out.line("te_cm_census_culture_joined = { CULTURE = %s RESULT = %s }" % (culture, owner.result))
                if joinable:
                    with out.block("else"):
                        out.line("te_cm_census_culture = { CULTURE = %s }" % culture)
                else:
                    out.line("te_cm_census_culture = { CULTURE = %s }" % culture)
        for merge in merges:
            with out.block("if"):
                out.line("limit = { te_cmg_%s_census_wanted = yes }" % merge.key)
                out.line("te_cmg_census_%s = yes" % merge.key)
    _write_conversion_effects(out, vanilla, merges)
    _write_debug_dump(out, merges)
    return out.text()


def _write_debug_dump(out: "_Script", merges: tuple[cfg.Merge, ...]) -> None:
    """``te_cmg_debug_dump`` (plan Task 8): the console menu's option D. Country scope. For each merge that is running or
    complete, or that this country is a candidate for, ``te_cm_debug_dump_merge`` and, per joinable slot culture,
    ``te_cm_debug_dump_part`` (te_debug_cm_effects.txt), which log every te_cm_ variable the merge keeps. The names embed
    the merge key and the culture, so the list is generated from the roster."""
    out.line()
    out.line("# ---- The console menu's dump (events/te_debug_cm_events.txt, option D) ----")
    out.line()
    out.line("# Country scope. Logs (TE_CM_DEBUG) every te_cm_ variable of each merge that is running or complete, or that this country")
    out.line("# is a candidate for: te_cm_debug_dump_merge, then te_cm_debug_dump_part per slot culture a starter can bring in.")
    # Each call names only variables something sets, since a read of a name nothing sets logs "is used but is never
    # set" at every load (116 names, 2026-11-08): the wait counter only for a merge with a core wait, and a part's own
    # standard-of-living gate only for an optional part (a core part's is the merge's, te_cm_sol_ok_<m>).
    with out.block("te_cmg_debug_dump"):
        for merge in merges:
            key = merge.key
            optional = {c for part in merge.optional for c in part.cultures}
            with out.block("if"):
                out.line(
                    "limit = { OR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 te_cmg_%s_is_candidate = yes } }"
                    % (key, key, key)
                )
                if core_waits(merge):
                    out.line("te_cm_debug_dump_merge_waiting = { MERGE = %s }" % key)
                else:
                    out.line("te_cm_debug_dump_merge = { MERGE = %s }" % key)
                # Only a milestone has a latch: naming it for a standing gate would read a name nothing sets.
                if milestone_gate(merge):
                    out.line("te_cm_debug_dump_gate_milestone = { MERGE = %s }" % key)
                elif standing_gate(merge):
                    out.line("te_cm_debug_dump_gate = { MERGE = %s }" % key)
                for culture in _joinable_slot_cultures(merge):
                    gate = "te_cm_sol_ok_%s_%s" % (key, culture) if culture in optional else "te_cm_sol_ok_%s" % key
                    out.line("te_cm_debug_dump_part = { MERGE = %s CULTURE = %s SOL_OK = %s }" % (key, culture, gate))


def _write_conversion_effects(out: "_Script", vanilla: dict, merges: tuple[cfg.Merge, ...]) -> None:
    """The yearly conversion, the switch, the monthly upkeep of the primary cultures, the fervor copy and the homeland
    tie-in (plan Task 6): ``te_cmg_yearly_country``, ``te_cmg_dominance_all``, ``te_cmg_monthly_country``,
    ``te_cmg_copy_fervor_all``, ``te_cmg_formed_country`` and ``te_cmg_remove_switched_part_homelands``."""
    cultures = switchable_cultures(merges)

    # ---- the yearly conversion ----
    out.line()
    out.line("# ---- Conversion, the switch and the primary cultures ----")
    out.line()
    out.line("# Country scope. This country's own yearly pulse (te_cm_yearly_on_action, behind the rule, not behind the census's")
    out.line("# year guard): for each running or complete merge whose starter is alive and has this country in its sphere, every")
    out.line("# part that joined and has not switched converts here (te_cm_convert_part). The starter is saved before the sphere")
    out.line("# test reads it: a scope left over from the census in the same on_action may hold another country.")
    out.line("# - While the merge runs (state 1), the whole merge stalls when its starter fails te_cmg_<m>_core_ok or")
    out.line("#   te_cm_sol_ok_<m>: both cover the core cultures only. A complete merge has no core part left to stall it.")
    out.line("# - Nothing converts once the merge's own result has switched into a higher merge's (R33).")
    out.line("# - A merge with a standing gate (cfg.Gate: slavery, schooling, independence) stalls whole, complete or not, while")
    out.line("#   its starter fails te_cmg_<m>_gate_ok.")
    out.line("# - One part stalls on its own gates, read on the starter: te_cm_ok_<m>_<c> (the hold alone, once joined: R29) and,")
    out.line("#   for an optional part, its own standard-of-living gate te_cm_sol_ok_<m>_<c> (R23) and any gate of its own (Afro-American")
    out.line("#   pops once slavery is banned). Progress is kept while stalled.")
    with out.block("te_cmg_yearly_country"):
        for merge in merges:
            key = merge.key
            optional = {c for part in merge.optional for c in part.cultures}
            with out.block("if"):
                with out.block("limit"):
                    for line in _state_running_or_complete(key):
                        out.line(line)
                    out.line("exists = global_var:te_cm_starter_%s" % key)
                    out.line("NOT = { %s }" % _result_switched(merge))
                out.line("global_var:te_cm_starter_%s = { save_temporary_scope_as = te_cm_starter }" % key)
                with out.block("if"):
                    with out.block("limit"):
                        out.line("scope:te_cm_starter = { is_country_alive = yes }")
                        out.line("te_cm_in_sphere = yes")
                        with out.block("OR"):
                            out.line("global_var:te_cm_state_%s ?= 2" % key)
                            with out.block("scope:te_cm_starter"):
                                out.line("te_cmg_%s_core_ok = yes" % key)
                                out.line("var:te_cm_sol_ok_%s ?= 1" % key)
                        if standing_gate(merge):
                            out.line("scope:te_cm_starter = { %s }" % _gate_ok(merge))
                    for culture in _joinable_slot_cultures(merge):
                        tier = cfg.derive_tier(merge, culture, vanilla, merges)
                        part_gate = _part_of(merge, culture).gate
                        with out.block("if"):
                            with out.block("limit"):
                                out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
                                out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
                                with out.block("scope:te_cm_starter"):
                                    out.line("var:te_cm_ok_%s_%s ?= 1" % (key, culture))
                                    if culture in optional:
                                        out.line("var:te_cm_sol_ok_%s_%s ?= 1" % (key, culture))
                                    if part_gate:
                                        out.line("%s = yes" % part_gate.trigger)
                            out.line(
                                "te_cm_convert_part = { MERGE = %s CULTURE = %s RESULT = %s TIER = %d }"
                                % (key, culture, merge.result, tier)
                            )

    # ---- dominance and the switch ----
    out.line()
    out.line("# Any scope. Run by te_cm_yearly_on_action at the end of the census, behind the rule, the year and the lock: the")
    out.line("# dominance of every part that joined a running or complete merge and has not switched (te_cm_census_dominance reads")
    out.line("# the census's figures, no walk of its own), then the switch of each part at or over te_cm_switch_share. Only for a")
    out.line("# merge whose starter is alive (a dead one's census wasn't taken) and whose own result has not switched into a higher")
    out.line("# merge's (R33). Debug targets call it on its own.")
    with out.block("te_cmg_dominance_all"):
        for merge in merges:
            key = merge.key
            with out.block("if"):
                with out.block("limit"):
                    for line in _state_running_or_complete(key):
                        out.line(line)
                    out.line("NOT = { te_cmg_%s_starter_gone = yes }" % key)
                    out.line("NOT = { %s }" % _result_switched(merge))
                for culture in _joinable_slot_cultures(merge):
                    with out.block("if"):
                        with out.block("limit"):
                            out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
                            out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
                        out.line("te_cm_census_dominance = { MERGE = %s CULTURE = %s }" % (key, culture))
                        out.line("te_cm_switch_part = { MERGE = %s CULTURE = %s RESULT = %s }" % (key, culture, merge.result))

    # ---- the monthly upkeep ----
    out.line()
    out.line("# Country scope. Run monthly (on_monthly_pulse_country, behind the rule) and by te_cmg_formed_country: for every")
    out.line("# culture that has switched, the culture its people ended up in becomes a primary culture where the part is one, pops")
    out.line("# of the part that came back convert, and the part leaves the primary cultures once nothing is tied to it")
    out.line("# (te_cm_monthly_switched_culture). One variable check per culture while nothing has switched.")
    with out.block("te_cmg_monthly_country"):
        for culture in cultures:
            with out.block("if"):
                out.line("limit = { has_global_variable = te_cm_switched_%s }" % culture)
                out.line("te_cm_monthly_switched_culture = { CULTURE = %s }" % culture)
    _write_dead_primary_effects(out, vanilla, merges)

    # ---- the fervor copy ----
    out.line()
    out.line("# Any scope. Once a month, with no rule gate (te_cm_fervor_on_action, on the global on_monthly_pulse): every culture that has")
    out.line("# switched takes the fervor of the culture it switched into (te_cm_copy_fervor), so vanilla's reads of its fervor read")
    out.line("# the merged culture's. A culture is copied after the one it switched into (fervor_copy_order): cm_italian, which")
    out.line("# switches into cm_latin, before North Italian, so a chain settles in one pass. One variable check per culture while")
    out.line("# nothing has switched.")
    out.line("# Not Ukrainian or Byelorussian (cfg.NO_FERVOR_COPY): vanilla reads their fervor only for an identity apart from")
    out.line("# Russian (their renaissances, the Russian Civil War's releases), which their merge into East Slavic has ended.")
    with out.block("te_cmg_copy_fervor_all"):
        for culture in fervor_copy_order(merges):
            if culture in cfg.NO_FERVOR_COPY:
                continue
            with out.block("if"):
                out.line("limit = { has_global_variable = te_cm_switched_%s }" % culture)
                out.line("te_cm_copy_fervor = { CULTURE = %s }" % culture)

    out.line()
    out.line("# Culture scope = the culture to set; scope:te_cm_fervor_source = the culture whose fervor it takes. Sets the")
    out.line("# fervor to the highest half point at or below the source's (fervor_ladder), with literals only: set_fervor is")
    out.line("# documented with a literal, and a named value it read as 0 would zero the culture. Two levels, bands of ten and")
    out.line("# then half points, so a set costs at most 30 tests.")
    with out.block("te_cmg_set_fervor_from_source"):
        bands = fervor_ladder()
        for i, (low, steps, rest) in enumerate(bands):
            opener = "if" if i == 0 else ("else" if i == len(bands) - 1 else "else_if")
            with out.block(opener):
                if opener != "else":
                    out.line("limit = { scope:te_cm_fervor_source = { culture_current_fervor >= %d } }" % low)
                for j, step in enumerate(steps):
                    with out.block("if" if j == 0 else "else_if"):
                        out.line("limit = { scope:te_cm_fervor_source = { culture_current_fervor >= %s } }" % _fervor_literal(step))
                        out.line("set_fervor = %s" % _fervor_literal(step))
                with out.block("else"):
                    out.line("set_fervor = %s" % _fervor_literal(rest))

    # ---- the formation hook ----
    out.line()
    out.line("# Country scope = the newly formed country (on_country_formed, behind the rule). The monthly upkeep first, so a country")
    out.line("# formed from a definition that lists only parts gets the result at once. Then, for every running or complete merge whose")
    out.line("# starter has this country in its sphere and which has already converted here (te_cm_converted_<m>, set by")
    out.line("# te_cm_convert_part), the result as a primary culture if the formation dropped it, but only where a part that joined is")
    out.line("# primary here, as te_cm_convert_part gives it (R34); the starter, which carries te_cm_started_<m>, always qualifies.")
    out.line("# Not once the merge's result has switched into a higher merge's (R33): that culture has no pops left, and the")
    out.line("# monthly upkeep above already gives the higher result.")
    with out.block("te_cmg_formed_country"):
        out.line("te_cmg_monthly_country = yes")
        for merge in merges:
            key = merge.key
            with out.block("if"):
                with out.block("limit"):
                    for line in _state_running_or_complete(key):
                        out.line(line)
                    out.line("exists = global_var:te_cm_starter_%s" % key)
                    with out.block("OR"):
                        out.line("has_variable = te_cm_started_%s" % key)
                        with out.block("AND"):
                            out.line("has_variable = te_cm_converted_%s" % key)
                            with out.block("OR"):
                                for culture in _joinable_slot_cultures(merge):
                                    with out.block("AND"):
                                        out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
                                        out.line("country_has_primary_culture = cu:%s" % culture)
                    out.line("NOT = { country_has_primary_culture = cu:%s }" % merge.result)
                    out.line("NOT = { %s }" % _result_switched(merge))
                out.line("global_var:te_cm_starter_%s = { save_temporary_scope_as = te_cm_starter }" % key)
                with out.block("if"):
                    out.line("limit = { te_cm_in_sphere = yes }")
                    out.line("add_primary_culture = cu:%s" % merge.result)

    # ---- the homeland tie-in ----
    out.line()
    parts_of = switched_into(merges)
    out.line("# State region scope. Dynamic Homeland Progress has just removed the homeland of scope:te_cm_removed_culture here")
    out.line("# (te_homeland_removal_monthly_effect): the homeland of every part that switched into that culture goes with it, so an old")
    out.line("# homeland never outlives its successor. It follows the chain: a part that is itself a result (cm_italian into cm_latin,")
    out.line("# Corsican into cm_italian) takes the parts that switched into it with it, through te_cmg_remove_parts_of_<culture>.")
    out.line("# Not behind the rule: it is about map state.")
    with out.block("te_cmg_remove_switched_part_homelands"):
        for culture in cultures:
            with out.block("if"):
                with out.block("limit"):
                    out.line("global_var:te_cm_switched_%s ?= scope:te_cm_removed_culture" % culture)
                    out.line("is_homeland = cu:%s" % culture)
                out.line("remove_homeland = cu:%s" % culture)
                if culture in parts_of:
                    out.line("te_cmg_remove_parts_of_%s = yes" % culture)
    for result in parts_of:
        if result not in cultures:
            continue  # a result that is no part of another merge is never removed through the tie-in, so nothing calls this
        out.line()
        out.line("# State region scope. The homeland of %s has just been removed here: so is that of each part that switched into it," % result)
        out.line("# and, down the chain, of the parts that switched into those.")
        with out.block("te_cmg_remove_parts_of_%s" % result):
            for part in parts_of[result]:
                with out.block("if"):
                    with out.block("limit"):
                        out.line("global_var:te_cm_switched_%s ?= cu:%s" % (part, result))
                        out.line("is_homeland = cu:%s" % part)
                    out.line("remove_homeland = cu:%s" % part)
                    if part in parts_of:
                        out.line("te_cmg_remove_parts_of_%s = yes" % part)


def _chain_order(merges: tuple[cfg.Merge, ...]) -> list[str]:
    """The results that can themselves switch, the lowest in a chain first (cm_italian before cm_latin), so one pass
    over them follows a chain to its end."""
    results = {merge.result for merge in merges}
    return [culture for culture in reversed(fervor_copy_order(merges)) if culture in results]


def own_traditions(culture: str, vanilla: dict, merges: tuple[cfg.Merge, ...]) -> list[str]:
    """The traditions a culture is defined with: vanilla's, or for a new result the ones every core part shares."""
    for merge in merges:
        if merge.new is not None and merge.result == culture:
            shared = own_traditions(merge.core[0].cultures[0], vanilla, merges)
            for part in merge.core[1:]:
                have = own_traditions(part.cultures[0], vanilla, merges)
                shared = [t for t in shared if t in have]
            return shared
    body = vanilla.get(culture)
    return _list(_fields(body), "traditions") if body is not None else []


def carried_traditions(vanilla: dict, merges: tuple[cfg.Merge, ...]) -> dict[tuple[str, str], list[str]]:
    """(merge key, part) -> the traditions the part gives the merge's result when it switches: its own and the ones it
    took from its own parts (cm_east_slavic passes Russian's on into Pan-Slavic), less what the result is defined
    with. Only the parts ``cfg.carries_traditions`` names; a pair with nothing to give is left out."""

    def all_of(culture: str, seen: tuple[str, ...] = ()) -> list[str]:
        found = list(own_traditions(culture, vanilla, merges))
        if culture in seen:
            return found
        for merge in merges:
            if merge.result != culture:
                continue
            for part in _joinable_slot_cultures(merge):
                if cfg.carries_traditions(merge, part):
                    found.extend(t for t in all_of(part, seen + (culture,)) if t not in found)
        return found

    carried: dict[tuple[str, str], list[str]] = {}
    for merge in merges:
        have = own_traditions(merge.result, vanilla, merges)
        for part in _joinable_slot_cultures(merge):
            if cfg.carries_traditions(merge, part):
                gives = [t for t in all_of(part) if t not in have]
                if gives:
                    carried[(merge.key, part)] = gives
    return carried


def _write_dead_primary_effects(out: "_Script", vanilla: dict, merges: tuple[cfg.Merge, ...]) -> None:
    """The effects behind removing a switched part from the primary cultures (owner, 2026-11-09):
    ``te_cmg_resolve_switched_result``, ``te_cmg_strip_untouched_results`` and ``te_cmg_carry_traditions``."""
    out.line()
    out.line("# Any scope; scope:te_cm_switched_result = the culture a part switched into. Follows the chain to the culture")
    out.line("# its people are in now: North Italian switched into cm_italian, and cm_italian into cm_latin, so the answer is")
    out.line("# cm_latin. The lowest result first, so one pass reaches the end. Without it the monthly upkeep would give a")
    out.line("# country cm_italian back each month after removing it.")
    with out.block("te_cmg_resolve_switched_result"):
        chain = _chain_order(merges)
        if not chain:
            out.line("# no result of this roster is a part of another merge")
        for culture in chain:
            with out.block("if"):
                with out.block("limit"):
                    out.line("has_global_variable = te_cm_switched_%s" % culture)
                    out.line("scope:te_cm_switched_result ?= cu:%s" % culture)
                out.line("global_var:te_cm_switched_%s = { save_temporary_scope_as = te_cm_switched_result }" % culture)

    out.line()
    out.line("# Country scope. Monthly and on formation, with no rule gate (te_cm_strip_on_action). A formable's definition lists")
    out.line("# the merged cultures beside their parts, so that a country whose parts are gone can still form it, and forming a")
    out.line("# tag adds every culture its definition lists. A merged culture whose merge never began has no people: it is taken")
    out.line("# off again here, unless it is the country's only primary culture. te_cm_chk_strip is the TEMPORARY self-check")
    out.line("# cm_untouched_stripped.")
    with out.block("te_cmg_strip_untouched_results"):
        for merge in merges:
            if merge.new is None:
                continue
            with out.block("if"):
                with out.block("limit"):
                    out.line(_result_exists(merge))
                    out.line("country_has_primary_culture = cu:%s" % merge.result)
                    out.line("te_cmg_%s_untouched = yes" % merge.key)
                    out.line("any_primary_culture = { NOT = { this = cu:%s } }" % merge.result)
                out.line("remove_primary_culture = cu:%s" % merge.result)
                out.line("te_cm_chk_strip = { CULTURE = %s }" % merge.result)

    carried = carried_traditions(vanilla, merges)
    out.line()
    out.line("# Any scope. Once a month, with no rule gate (te_cm_fervor_on_action): a merged culture takes the traditions of the")
    out.line("# core parts that have switched into it (owner, 2026-11-09), so the acceptance a part's tradition gave other")
    out.line("# cultures doesn't end when the part leaves the primary cultures. Not an optional part's, nor the pairs in")
    out.line("# culture_merges_config.TRADITIONS_NOT_CARRIED. A result that is itself a part passes on what it took. Guarded,")
    out.line("# so it adds each tradition once; te_cm_chk_traditions is the TEMPORARY self-check cm_tradition_carried.")
    with out.block("te_cmg_carry_traditions"):
        for (key, part), traditions in carried.items():
            result = merge_by_key_in(merges, key).result
            for tradition in traditions:
                with out.block("if"):
                    with out.block("limit"):
                        out.line("global_var:te_cm_switched_%s ?= cu:%s" % (part, result))
                        out.line("cu:%s = { NOT = { has_discrimination_trait = %s } }" % (result, tradition))
                    out.line("cu:%s = { add_tradition_trait = %s }" % (result, tradition))
                    out.line("set_local_variable = { name = te_cm_trad_added value = 1 }")
        out.line("te_cm_chk_traditions = yes")


def merge_by_key_in(merges: tuple[cfg.Merge, ...], key: str) -> cfg.Merge:
    for merge in merges:
        if merge.key == key:
            return merge
    raise KeyError(key)


def definition_additions(inventory: dict, merges: tuple[cfg.Merge, ...] | None = None) -> dict[str, list[str]]:
    """Vanilla formable tag -> the merged cultures its definition gains, for each tag that owns no state at the 1836
    start and lists a part. A part's new results all the way up its chain (North Italian: cm_italian and cm_latin); an
    absorb merge's result is a vanilla culture with people of its own, never added (forming the tag would hand it out)."""
    merges = cfg.MERGES if merges is None else merges
    new_results = {merge.result for merge in merges if merge.new is not None}
    parts = set(inventory["parts"])
    additions: dict[str, list[str]] = {}
    for tag, formable in inventory["formables"].items():
        if formable["exists_at_start"]:
            continue
        gains: list[str] = []
        for culture in formable["cultures"]:
            if culture not in parts:
                continue
            for successor in sorted(cfg.successors_of(culture)):
                if successor in new_results and successor not in formable["cultures"] and successor not in gains:
                    gains.append(successor)
        if gains:
            additions[tag] = gains
    return additions


MOD_DEFINITIONS = Path("common/country_definitions/te_formable_countries.txt")
MOD_FORMATIONS = Path("common/country_formation/te_formable_countries.txt")


def mod_formable_definitions(root: Path = ROOT) -> dict[str, list[str]]:
    """The mod's own formables (bare entries of its country_formation file) -> their definition's ``cultures`` list.
    The definitions are hand-written; ``mod_definition_gaps`` says what they lack."""
    formables = [
        tag for tag, _tokens in primary_reads._top_blocks((root / MOD_FORMATIONS).read_text(encoding="utf-8-sig"))
        if re.fullmatch(r"[A-Z0-9]{3}", tag)
    ]
    definitions = {
        tag: primary_reads._list_field(tokens, "cultures") or []
        for tag, tokens in primary_reads._top_blocks((root / MOD_DEFINITIONS).read_text(encoding="utf-8-sig"))
    }
    return {tag: definitions[tag] for tag in formables if tag in definitions}


def mod_definition_gaps(root: Path = ROOT, merges: tuple[cfg.Merge, ...] | None = None) -> dict[str, list[str]]:
    """Mod formable tag -> the merged cultures its definition should list and does not: every new result a listed
    part can become, as ``definition_additions`` gives vanilla's tags. Empty when the file is right."""
    merges = cfg.MERGES if merges is None else merges
    new_results = {merge.result for merge in merges if merge.new is not None}
    parts = set(primary_reads.part_cultures(merges))
    gaps: dict[str, list[str]] = {}
    for tag, cultures in mod_formable_definitions(root).items():
        missing: list[str] = []
        for culture in cultures:
            if culture in parts:
                missing.extend(
                    s for s in sorted(cfg.successors_of(culture))
                    if s in new_results and s not in cultures and s not in missing
                )
        if missing:
            gaps[tag] = missing
    return gaps


def render_definitions(inventory: dict | None = None) -> str:
    """``INJECT`` blocks that restate each vanilla formable's ``cultures`` list with the merged cultures added."""
    inventory = primary_reads.load() if inventory is None else inventory
    out = _Script()
    out.line(HEADER)
    out.line("#")
    out.line("# Forming a country needs a primary culture from its definition's list, and vanilla's lists name the parts of the")
    out.line("# culture merges. A part that has switched leaves a country's primary cultures (te_cm_monthly_switched_culture), so")
    out.line("# each list gains the merged cultures its parts become (owner, 2026-11-09): a Germany that is only German can still")
    out.line("# form the Holy Roman Empire. Only tags that own no state at the 1836 start, so no country begins with a merged")
    out.line("# culture that has no people; a start tag (RUS, PRU, GBR) holds its parts while it is dead instead")
    out.line("# (te_cmg_part_held_<c>). Each block restates vanilla's whole list (from culture_merge_primary_reads.json), so the")
    out.line("# result is right whether the engine appends an injected list to vanilla's or puts it in its place; the self-check")
    out.line("# cm_definition_inject reads one tag. Forming adds every listed culture, so te_cmg_strip_untouched_results takes a")
    out.line("# merged culture whose merge never began off again.")
    for tag, gains in definition_additions(inventory).items():
        out.line()
        with out.block("INJECT:%s" % tag):
            out.line("cultures = { %s }" % " ".join(inventory["formables"][tag]["cultures"] + gains))
    return out.text()


def trigger_override_additions(inventory: dict, merges: tuple[cfg.Merge, ...] | None = None) -> dict[str, list[str]]:
    """Restated vanilla trigger -> the cultures added to its list: every culture a listed part can become."""
    merges = cfg.MERGES if merges is None else merges
    parts = set(inventory["parts"])
    additions: dict[str, list[str]] = {}
    for name in ledger.TRIGGER_OVERRIDES:
        listed = inventory["trigger_lists"][name]["cultures"]
        gains: list[str] = []
        for culture in listed:
            if culture in parts:
                gains.extend(c for c in sorted(cfg.successors_of(culture)) if c not in listed and c not in gains)
        additions[name] = gains
    return additions


def render_vanilla_triggers(inventory: dict | None = None) -> str:
    """Bare copies of the vanilla triggers in ``ledger.TRIGGER_OVERRIDES``, the merged cultures added."""
    inventory = primary_reads.load() if inventory is None else inventory
    new_results = {merge.result for merge in cfg.MERGES if merge.new is not None}
    out = _Script()
    out.line(HEADER)
    out.line("#")
    out.line("# VANILLA OVERRIDE. Each trigger here is vanilla's own, restated with the merged cultures beside the parts it")
    out.line("# lists (owner, 2026-11-09: a small helper is worth overriding, a whole journal entry is not), so a country whose")
    out.line("# parts have left its primary cultures still passes. This file sorts before vanilla's, and the first bare")
    out.line("# definition of a scripted trigger wins (scripting_best_practices.md, Load Order, fact 3); the engine logs one")
    out.line("# `Duplicated key` line per trigger at load, naming vanilla's copy. Vanilla's list is read from")
    out.line("# culture_merge_primary_reads.json, whose scan fails if the trigger becomes anything but a plain list.")
    for name, gains in trigger_override_additions(inventory).items():
        entry = inventory["trigger_lists"][name]
        out.line()
        out.line("# vanilla: %s" % entry["file"])
        with out.block(name):
            with out.block("OR"):
                for culture in entry["cultures"]:
                    out.line("country_has_primary_culture = cu:%s" % culture)
                for culture in gains:
                    if culture in new_results:
                        # A game begun before the culture was added has no object for it (te_cmg_<m>_is_candidate).
                        out.line("AND = { exists = cu:%s country_has_primary_culture = cu:%s }" % (culture, culture))
                    else:
                        out.line("country_has_primary_culture = cu:%s" % culture)
    return out.text()


# ---------------------------------------------------------------------------
# Starting a merge: values, bars, buttons, journal entries and their loc
# ---------------------------------------------------------------------------

# Vanilla's waving flag, the icon Russification and the cultural renaissances use.
JE_ICON = "gfx/interface/icons/event_icons/waving_flag.dds"
# The technology that opens each tier (te_cm_tier_tech_<tier> in te_culture_merge_triggers.txt).
TIER_TECH = {1: "pan-nationalism", 2: "mass_media", 3: "television"}


def _lines(write) -> list[str]:
    """The lines a writer function produces, relative to a block's indentation."""
    sub = _Script()
    write(sub)
    return sub.lines


def _names(cultures) -> str:
    """Loc splices read as a list: ``$a$``, ``$a$ and $b$``, ``$a$, $b$ and $c$``."""
    names = ["$%s$" % c for c in cultures]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def _part_label(part: cfg.Part) -> str:
    """A slot named in a list of parts: its first culture, then any alternatives, ``$yankee$ (or $cm_american$)``."""
    first = "$%s$" % part.cultures[0]
    if len(part.cultures) == 1:
        return first
    return "%s (or %s)" % (first, _either(part.cultures[1:]))


def _part_labels(parts) -> str:
    """Slots read as a list, each with its alternatives: ``$british$ and $yankee$ (or $cm_american$)``."""
    labels = [_part_label(part) for part in parts]
    if len(labels) <= 1:
        return "".join(labels)
    return ", ".join(labels[:-1]) + " and " + labels[-1]


def _either(cultures) -> str:
    """Loc splices as alternatives: ``$a$``, ``$a$ or $b$``, ``$a$, $b$ or $c$``."""
    names = ["$%s$" % c for c in cultures]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " or " + names[-1]


def _joinable_core(merge: cfg.Merge) -> list[str]:
    """The core cultures a starter can bring in: every one except an absorb merge's result."""
    return [c for c in _core_cultures(merge) if not _is_absorb_result(merge, c)]


def _write_lowest(out: "_Script", key: str, name: str, cultures: list[str]) -> None:
    """A script value: the smallest result share among those of ``cultures`` that joined and haven't switched.

    0 until one of them has joined (a merge that has started but brought nothing in has no progress, not
    full progress); 1 when every part that joined has switched; a joined part Task 6's census hasn't
    measured yet counts as 0."""
    with out.block(name):
        out.line("value = 0")
        with out.block("if"):
            with out.block("limit"):
                with out.block("OR"):
                    for culture in cultures:
                        out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
            out.line("value = 1")
            for culture in cultures:
                with out.block("if"):
                    with out.block("limit"):
                        out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
                        out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
                    with out.block("if"):
                        out.line("limit = { has_global_variable = te_cm_dom_%s_%s }" % (key, culture))
                        out.line("max = global_var:te_cm_dom_%s_%s" % (key, culture))
                    with out.block("else"):
                        out.line("max = 0")


def render_values(merges: tuple[cfg.Merge, ...] | None = None) -> str:
    """Per merge, the progress the entry's bar shows (country scope, the starter).

    ``lowest_dom``: the smallest result share (te_cm_dom_<m>_<c>, Task 6's) among the core parts
    that joined and haven't switched, which is what completes the merge; ``lowest_dom_all`` the same
    over every part that joined, optional and late ones too, which is what is left once the merge
    is complete and a late part is still converting. ``progress`` is the first while the merge runs
    and the second once it is complete, over te_cm_switch_share, capped at 1; ``bar_pct`` is the
    bar's 0 to 100.
    """
    merges = cfg.MERGES if merges is None else merges
    out = _Script()
    out.line(HEADER)
    for merge in merges:
        key = merge.key
        out.line()
        out.line("# ---- %s ----" % key)
        out.line()
        out.line("# Country scope (the starter). The smallest result share among the core parts of the %s merge that joined and" % key)
        out.line("# haven't switched: 0 until one has joined, 1 once every joined one has switched.")
        _write_lowest(out, key, "te_cmg_%s_lowest_dom" % key, _joinable_core(merge))
        out.line()
        out.line("# Country scope (the starter). The same over every part that joined, optional and late ones included.")
        _write_lowest(out, key, "te_cmg_%s_lowest_dom_all" % key, _joinable_slot_cultures(merge))
        out.line()
        out.line("# Country scope. How far the %s merge is from its switch, 0 to 1: the lowest result share over the share at" % key)
        out.line("# which the rest of a part switches. The core's while it runs; once it is complete (state 2) the lowest among")
        out.line("# the parts still converting, which are the late ones.")
        with out.block("te_cmg_%s_progress" % key):
            out.line("value = 0")
            with out.block("if"):
                out.line("limit = { global_var:te_cm_state_%s ?= 2 }" % key)
                out.line("value = te_cmg_%s_lowest_dom_all" % key)
                out.line("divide = te_cm_switch_share")
                out.line("max = 1")
            with out.block("else"):
                out.line("value = te_cmg_%s_lowest_dom" % key)
                out.line("divide = te_cm_switch_share")
                out.line("max = 1")
        out.line()
        out.line("# Country scope. The same, 0 to 100, for the bar.")
        with out.block("te_cmg_%s_bar_pct" % key):
            out.line("value = te_cmg_%s_progress" % key)
            out.line("multiply = 100")
    return out.text()


def render_bars(merges: tuple[cfg.Merge, ...] | None = None) -> str:
    """One scripted progress bar per merge, 0 to 100. The entry's monthly pulse sets it."""
    merges = cfg.MERGES if merges is None else merges
    out = _Script()
    out.line(HEADER)
    for merge in merges:
        out.line()
        with out.block("te_cmg_%s_bar" % merge.key):
            out.line('name = "te_cm_bar_name"')
            out.line('desc = "te_cm_bar_desc"')
            out.line("default_green = yes")
            out.line("start_value = 0")
            out.line("min_value = 0")
            out.line("max_value = 100")
    return out.text()


def render_buttons(merges: tuple[cfg.Merge, ...] | None = None) -> str:
    """One start button per merge. Visible while the merge is idle; possible when the country can start
    it (each condition its own custom_tooltip, in te_cmg_<m>_can_start); the AI presses it at once."""
    merges = cfg.MERGES if merges is None else merges
    out = _Script()
    out.line(HEADER)
    out.line()
    out.line("# The AI starts a merge as soon as it qualifies (spec section 4: the merge has no direct cost, so there is")
    out.line("# nothing to weigh). A human sees the same button on the merge's journal entry.")
    for merge in merges:
        key = merge.key
        out.line()
        with out.block("te_cmg_start_%s_button" % key):
            out.line('name = "te_cmg_start_%s_button"' % key)
            out.line('desc = "te_cmg_start_%s_button_desc"' % key)
            with out.block("visible"):
                out.line(_state_idle(key))
            out.line("ai_chance = { value = 100 }")
            with out.block("possible"):
                with out.block("custom_tooltip"):
                    out.line("text = te_cm_tt_rule_on")
                    out.line("te_cm_system_enabled = yes")
                out.line("te_cmg_%s_can_start = yes" % key)
            with out.block("effect"):
                with out.block("custom_tooltip"):
                    out.line("text = te_cmg_start_%s_effect_tt" % key)
                    out.line("te_cmg_start_%s = yes" % key)
    return out.text()


@dataclass
class Row:
    """One line of an entry's status text: the loc key, the lines of its trigger, and its text.

    ``text`` is None for a shared phrase (a hand-written ``te_cm_*`` key)."""

    key: str
    lines: list[str]
    text: str | None = None


def _negated(lines: list[str]) -> list[str]:
    return ["NOT = {"] + ["\t" + line for line in lines] + ["}"]


def status_rows(merge: cfg.Merge, vanilla: dict, merges: tuple[cfg.Merge, ...]) -> list[Row]:
    """The rows of the status text in order; the first whose trigger holds is shown.

    Complete (every part that joined has switched), complete for its core with a late part still
    converting (after a paused row for a standing gate that fails), running, running under another country, then an
    idle merge's first failing condition: no longer a candidate, not yet measured, a component merge, the merge's
    own gate, each core slot (busy in another merge, not
    held, not accepted, not together long enough, a technology of its own tier missing), the
    standard-of-living gap, a vanilla wait, and last that the button is ready. The rule being off comes
    before all of them: is_candidate needs the rule, so a later row would never show, and a starter's
    merge pauses with it (review B, M1).
    """
    key = merge.key
    base = "je_te_cm_%s_status_" % key
    result = "$%s$" % merge.result
    tiers = {c: cfg.derive_tier(merge, c, vanilla, merges) for c in slot_cultures(merge)}
    sv = "[ROOT.GetCountry.MakeScope.ScriptValue('{}')|{}]"
    start = max(tiers[p.cultures[0]] for p in merge.core)
    # The figure alone read as arbitrary (2026-11-08): hovering it gives the modifier's breakdown by source and what raises it.
    speed = "#tooltippable;tooltip:[GetPlayer.GetTooltipTag],te_cm_speed_tt $country_culture_merge_speed_mult$: +%s#!" % sv.format(
        "te_cm_speed_display", "%0")
    rows = [
        Row("te_cm_status_rule_off", _negated(["te_cm_system_enabled = yes"])),
        Row(
            base + "complete",
            ["te_cmg_%s_is_starter = yes" % key, "global_var:te_cm_state_%s ?= 2" % key, "te_cmg_%s_all_switched = yes" % key],
            "The merge is complete: %s is the national culture across the sphere. Cultures that qualify later can still join." % result,
        ),
    ]
    # A standing gate that fails pauses a running or complete merge whole (cfg.Gate): before the late and running rows,
    # which would otherwise report a merge that converts nothing as under way.
    if standing_gate(merge):
        rows.append(
            Row(
                base + "paused",
                ["te_cmg_%s_is_starter = yes" % key] + _negated([_gate_ok(merge)]),
                "The merge is paused: no constituent culture joins or converts until this holds again. %s"
                % _sentence(merge.gate.clause),
            )
        )
    rows += [
        Row(
            base + "late",
            ["te_cmg_%s_is_starter = yes" % key, "global_var:te_cm_state_%s ?= 2" % key],
            "The merge is complete for its core cultures, and %s is their national culture. A culture that joined later is still "
            "converting: in its homeland %s holds %s of the pops, and at %s every remaining pop of that culture switches. %s."
            % (result, result, sv.format("te_cmg_%s_lowest_dom_all" % key, "%0"), sv.format("te_cm_switch_share", "%0"), speed),
        ),
        Row(
            base + "running",
            ["te_cmg_%s_is_starter = yes" % key],
            "The merge is running. In the homeland of the least converted constituent culture, %s holds %s of the pops; at %s "
            "every remaining pop of that culture switches. %s."
            % (result, sv.format("te_cmg_%s_lowest_dom" % key, "%0"), sv.format("te_cm_switch_share", "%0"), speed),
        ),
        Row("te_cm_status_elsewhere", ["te_cmg_%s_has_other_starter = yes" % key]),
        Row("te_cm_status_not_candidate", _negated(["te_cmg_%s_is_candidate = yes" % key])),
        Row("te_cm_status_unmeasured", _negated(["has_variable = te_cm_ok_%s_%s" % (key, _core_cultures(merge)[0])])),
    ]
    # A component merge that hasn't finished comes before any slot: its result isn't available to join until it has.
    for component in merge.components:
        rows.append(
            Row(
                base + "component_%s" % component,
                _negated(["global_var:te_cm_state_%s ?= 2" % component]),
                "The %s merge has to finish first." % _names([merge_by_key(component).result]),
            )
        )
    # The merge's own precondition comes before the slots: it is the history that keeps these peoples apart, and a slot's
    # hold or acceptance row would hide it (owner, 2026-11-09).
    if merge.gate:
        rows.append(Row(base + "gate", _negated([_gate_ok(merge)]), merge.gate.why))
    for index, part in enumerate(merge.core, start=1):
        unmet = _negated(_lines(lambda s, part=part: _write_routes(s, _slot_routes(merge, part, tiers))))
        # A slot that only another merge's result fills is waiting for that merge, not taken by it (review B, M8).
        if all(any(o is not merge and o.result == c for o in merges) for c in part.cultures):
            busy_text = "%s is still forming in its own merge, which has to finish first." % _either(part.cultures)
        else:
            busy_text = "%s pops are already part of another merge, which has to finish with them first." % _either(part.cultures)
        rows.append(
            Row(
                base + "busy_%d" % index,
                unmet + ["NOR = {"] + ["\tte_cmg_%s_%s_available = yes" % (key, c) for c in part.cultures] + ["}"],
                busy_text,
            )
        )
        for culture in part.cultures:
            tier = tiers[culture]
            free = ["te_cmg_%s_%s_available = yes" % (key, culture), "NOT = { has_global_variable = te_cm_switched_%s }" % culture]
            held = "te_cm_held_%s_%s" % (key, culture)
            ok = "te_cm_ok_%s_%s" % (key, culture)
            rows.append(
                Row(
                    base + "hold_%s" % culture,
                    unmet + free + ["has_variable = %s" % held, "var:%s < te_cm_hold_open" % held],
                    "$%s$ pops are out of reach: our sphere holds only [ROOT.GetCountry.MakeScope.Var('%s').GetValue|%%0] of them "
                    "in their homeland, and %s is needed." % (culture, held, sv.format("te_cm_hold_open", "%0")),
                )
            )
            # Accepted is vanilla's Full Acceptance (R39); the status names are spliced, so the mod's own names for them
            # (replace/ calls acceptance_status_4 Provisional Acceptance) show as the pop panel shows them.
            if tier == 2:
                accept_text = (
                    "$%s$ pops are not accepted highly enough where many of them live: their acceptance in our sphere is "
                    "below %s, beyond the $full_acceptance$ a more closely related culture needs." % (culture, sv.format("te_cm_accept_high_open", "0"))
                )
            else:
                accept_text = (
                    "$%s$ pops are not fully accepted where many of them live: their acceptance in our sphere is below "
                    "$full_acceptance$ (%s), and $second_rate_citizen$ is not enough." % (culture, sv.format("te_cm_accept_open", "0"))
                )
            rows.append(
                Row(
                    base + "accept_%s" % culture,
                    unmet + free + ["has_variable = %s" % ok, "var:%s = 0" % ok],
                    accept_text,
                )
            )
            if tier > 1:
                years = "te_cm_years_%s_%s" % (key, culture)
                needed = "te_cm_years_tier2" if tier == 2 else "te_cm_years_tier3"
                rows.append(
                    Row(
                        base + "years_%s" % culture,
                        unmet + free + ["var:%s ?= 1" % ok, "has_variable = %s" % years,
                                        "NOT = { te_cmg_%s_%s_years_met = yes }" % (key, culture)],
                        "$%s$ pops have not been held and accepted together long enough: [ROOT.GetCountry.MakeScope.Var('%s').GetValue|0] "
                        "of %s years."
                        % (culture, years, sv.format(needed, "0")),
                    )
                )
            if tier != start:
                rows.append(
                    Row(
                        base + "tech_%s" % culture,
                        unmet + free + ["NOT = { te_cm_tier_tech = { TIER = %d } }" % tier],
                        "$%s$ pops need $%s$ as well." % (culture, TIER_TECH[tier]),
                    )
                )
    # The gap's two ends and the gap itself, from the last census (2026-11-09: "too wide" alone left the player to find which
    # cultures). A gap already under the open value with the gate shut means a slot was unmet at that census and is met now;
    # the generic row is left for no figure at all (no core part measured, or a save from before the figures were kept).
    sol_shut = _negated(["var:te_cm_sol_ok_%s ?= 1" % key])
    var = "[ROOT.GetCountry.MakeScope.Var('te_cm_sol_%s_" + key + "')%s]"
    rows.append(
        Row(
            base + "sol_wide",
            sol_shut + ["has_variable = te_cm_sol_gap_%s" % key, "var:te_cm_sol_gap_%s >= te_cm_sol_gap_open" % key],
            "The core cultures live at standards of living too far apart: %s pops are the best off, at %s, and %s pops the "
            "worst off, at %s. The gap of %s must be under %s to begin."
            % (var % ("best", ".GetCulture.GetName"), var % ("hi", ".GetValue|1"), var % ("worst", ".GetCulture.GetName"),
               var % ("lo", ".GetValue|1"), var % ("gap", ".GetValue|1"), sv.format("te_cm_sol_gap_open", "0")),
        )
    )
    rows.append(
        Row(
            base + "sol_close",
            sol_shut + ["has_variable = te_cm_sol_gap_%s" % key],
            "The core cultures' standards of living are close enough now: the gap between the best and the worst off is %s, "
            "under %s. The next yearly census will count it." % (var % ("gap", ".GetValue|1"), sv.format("te_cm_sol_gap_open", "0")),
        )
    )
    rows.append(Row("te_cm_status_sol", sol_shut))
    for part in core_waits(merge):
        culture = part.cultures[0]
        rows.append(
            Row(
                base + "wait_%s" % culture,
                ["te_cmg_%s_start_basics = yes" % key, "te_cmg_%s_%s_waiting = yes" % (key, culture)],
                "The merge waits while a country still has %s open. It goes ahead after %s years at most."
                % (_either(part.wait_for), sv.format("te_cm_wait_cap_years", "0")),
            )
        )
    rows.append(Row("te_cm_status_ready", ["te_cmg_%s_can_start = yes" % key]))
    return rows


def merge_by_key(key: str) -> cfg.Merge:
    return cfg.merge_by_key(key)


def render_journal_entries(vanilla: dict, merges: tuple[cfg.Merge, ...] | None = None) -> str:
    """One journal entry per merge, modelled on je_colonial_empire.

    Inactive (listed for a candidate) until the country can start the merge, then active with the start
    button and the progress bar; it stays (`can_deactivate = no`). The status text says the first thing
    in the way, or the progress of the run. It concludes when the merge is complete and no part that
    joined is left unswitched (R5), and silently when another living country is the starter. A rule switched off pauses everything: `disable_evaluation`
    only prunes other countries' inactive records, and the yearly census re-adds one that is missing.
    """
    merges = cfg.MERGES if merges is None else merges
    out = _Script()
    out.line(HEADER)
    out.line()
    out.line("# Each entry is added two ways: the engine activates a candidate's inactive record once both")
    out.line("# is_shown_when_inactive and possible hold, and the yearly census (te_cmg_<m>_settle) adds one to a country")
    out.line("# that holds no record, behind the entry's own gate and a skip of any inactive copy")
    out.line("# (test_add_journal_entry_guard.py). Merge mechanics never key on the entry.")
    for merge in merges:
        key = merge.key
        entry = "je_te_cm_%s" % key
        out.line()
        out.line("# ---- %s (%s) ----" % (key, ", ".join("/".join(p.cultures) for p in merge.core)))
        with out.block(entry):
            out.line('icon = "%s"' % JE_ICON)
            out.line("group = je_group_internal_affairs")
            out.line()
            out.line("# 1.15 asks every entry for this; always = yes is vanilla's own default.")
            with out.block("activation_description"):
                out.line("always = yes")
            out.line()
            out.line("# With the rule off, drop other countries' inactive records for good; the census re-adds one.")
            out.line("# An active merge outlives the rule (no invalid outcome on it): it pauses where it stands")
            out.line("# and resumes when the rule is switched back on (R19), and converted pops keep their culture.")
            with out.block("disable_evaluation", "REVIEWED 2026-11-08 (rule_outlives): R19, a paused merge "
                           "resumes where it stood"):
                out.line("NOT = { te_cm_system_enabled = yes }")
            with out.block("is_shown_when_inactive"):
                out.line("te_cm_system_enabled = yes")
                out.line("te_cmg_%s_is_candidate = yes" % key)
            # The starter test in a custom_tooltip: bare, the page printed its script ("They are", "has the variable in
            # question") and logged a nullptr promote for the empty starter on every redraw (2026-11-09, 1,243 a session).
            with out.block("possible"):
                with out.block("OR"):
                    out.line("te_cmg_%s_can_start = yes" % key)
                    with out.block("custom_tooltip"):
                        out.line("text = te_cm_tt_done_starter")
                        out.line("te_cmg_%s_is_starter = yes" % key)
            out.line()
            out.line("should_be_pinned_by_default_uninvolved_or_context = yes")
            out.line("scripted_button = te_cmg_start_%s_button" % key)
            out.line("scripted_progress_bar = te_cmg_%s_bar" % key)
            out.line("progressbar = no")
            out.line()
            out.line("# The first row whose trigger holds. Rows after the run's are an idle merge's first failing condition.")
            with out.block("status_desc"):
                with out.block("first_valid"):
                    for row in status_rows(merge, vanilla, merges):
                        with out.block("triggered_desc"):
                            out.line("desc = %s" % row.key)
                            with out.block("trigger"):
                                for line in row.lines:
                                    out.line(line)
                    out.line("desc = te_cm_status_pending")
            out.line()
            with out.block("outcome"):
                out.line("header = je_standard_completion_header")
                out.line("effect_header = je_standard_on_completion_header")
                out.line('color = "gold_positive"')
                out.line("conclusion_desc = %s_complete_conclusion_desc" % entry)
                # Each condition in its own custom_tooltip: the panel's "Will complete if" list would otherwise
                # spell out the scripted triggers, nested ORs of "has the variable in question" (2026-11-08).
                with out.block("trigger"):
                    for text, condition in (
                        ("te_cm_tt_done_starter", "te_cmg_%s_is_starter = yes" % key),
                        ("te_cmg_%s_done_core_tt" % key, "global_var:te_cm_state_%s ?= 2" % key),
                        ("te_cm_tt_done_all", "te_cmg_%s_all_switched = yes" % key),
                    ):
                        with out.block("custom_tooltip"):
                            out.line("text = %s" % text)
                            out.line(condition)
            out.line()
            out.line("# Another country started this merge first (or it is complete under one): the entry ends silently.")
            switches = result_can_switch(merge, merges)
            core_left = bool(core_left_slots(merge, merges))
            if switches:
                out.line("# So does a candidate's entry once the merge's result has switched into a wider culture (R36): it can no")
                out.line("# longer start, and only the starter (who has the complete outcome above) keeps the entry.")
            if core_left:
                out.line("# And a candidate's entry once a higher merge has switched one of its core parts (R38): it can never start.")
            with out.block("outcome"):
                out.line("flags = { hidden invalid_outcome }")
                out.line("conclusion_desc = te_cm_je_invalid_conclusion_desc")
                with out.block("trigger"):
                    if switches or core_left:
                        with out.block("OR"):
                            out.line("te_cmg_%s_has_other_starter = yes" % key)
                            if switches:
                                with out.block("AND"):
                                    out.line(_result_switched(merge))
                                    out.line("NOT = { te_cmg_%s_is_starter = yes }" % key)
                            if core_left:
                                with out.block("AND"):
                                    out.line("NOT = { te_cmg_%s_core_left = yes }" % key)
                                    out.line("NOT = { te_cmg_%s_is_starter = yes }" % key)
                    else:
                        out.line("te_cmg_%s_has_other_starter = yes" % key)
            out.line()
            out.line("# The bar follows Task 6's dominance figures. Each month the country's variable takes the script")
            out.line("# value and the entry's bar takes the variable (the heir education entry's pattern). A paused system")
            out.line("# leaves the bar where it stood.")
            with out.block("on_monthly_pulse"):
                with out.block("effect"):
                    with out.block("if"):
                        out.line("limit = { te_cm_system_enabled = yes }")
                        out.line("set_variable = { name = te_cm_bar_%s value = te_cmg_%s_bar_pct }" % (key, key))
                        with out.block("scope:journal_entry"):
                            out.line("set_bar_progress = { name = te_cmg_%s_bar value = root.var:te_cm_bar_%s }" % (key, key))
            out.line()
            out.line("can_revolution_inherit = yes")
            out.line("can_deactivate = no")
    return out.text()


def entry_loc(vanilla: dict, merges: tuple[cfg.Merge, ...] | None = None) -> dict[str, str]:
    """Every loc key the entries, buttons and their tooltips use, key -> text (without quotes).

    The shared phrases (``te_cm_*``) are hand-written in te_miscellaneous_l_english.yml. Culture and
    vanilla entry names are spliced (``$german$``), never spelled.
    """
    merges = cfg.MERGES if merges is None else merges
    sv = "[GetPlayer.MakeScope.ScriptValue('{}')|{}]"
    out: dict[str, str] = {}
    for merge in merges:
        key = merge.key
        entry = "je_te_cm_%s" % key
        result = "$%s$" % merge.result
        tiers = {c: cfg.derive_tier(merge, c, vanilla, merges) for c in slot_cultures(merge)}
        core = _part_labels(merge.core)
        optional = _part_labels(merge.optional)
        out[entry] = "Cultural Merge: %s" % result
        if merge.new is not None:
            reason = (
                "Closely related peoples can come to see themselves as one nation. The core of this merge is %s. Over the "
                "decades their pops become %s, and once it holds most of a constituent culture's homeland, every remaining pop "
                "of that culture follows." % (core, result)
            )
        else:
            reason = (
                "Closely related peoples can come to see themselves as one nation. Here %s pops would become part of the existing "
                "%s culture: over the decades they assimilate into it, and once it holds most of a constituent culture's "
                "homeland, every remaining pop of that culture follows."
                % (_part_labels([p for p in merge.core if p.cultures[0] != merge.result]), result)
            )
        if optional:
            reason += " %s pops can join once they qualify as well" % optional
            gated = [part for part in merge.optional if part.gate]
            if gated and len(merge.optional) == 1:
                reason += ", and only once %s" % gated[0].gate.clause
            else:
                for part in gated:
                    reason += "; %s pops only once %s" % (_part_label(part), part.gate.clause)
            reason += "."
        if merge.gate:
            reason += " The merge begins only once %s." % merge.gate.clause
            if not merge.gate.milestone:
                reason += " It pauses whenever that stops being true."
            out["te_cmg_%s_gate_tt" % key] = _sentence(merge.gate.clause)
        out[entry + "_reason"] = reason
        # The complete outcome's middle condition: the merge's state is 2 once every core slot has switched. An absorb
        # merge's result is one of its core cultures, and it doesn't switch into itself.
        out["te_cmg_%s_done_core_tt" % key] = "%s pops have all switched to %s." % (
            _part_labels([p for p in merge.core if p.cultures[0] != merge.result]), result)
        out[entry + "_complete_conclusion_desc"] = (
            "The merge is complete. %s is the national culture across the sphere, and the cultures it brought in are one people." % result
        )
        for row in status_rows(merge, vanilla, merges):
            if row.text is not None:
                out[row.key] = row.text
        button = "te_cmg_start_%s_button" % key
        out[button] = "Begin the %s Merge" % result
        out[button + "_desc"] = (
            "Starts the merge of %s. %s becomes a primary culture here%s. Each constituent culture we hold that qualifies begins "
            "to assimilate into it: a slice of its pops each year, those in subjects and bloc members more slowly. A culture "
            "that qualifies later joins then. Once %s holds %s of a culture's homeland, every remaining pop of that culture "
            "switches at once."
            % (core, result, "" if merge.new is not None else " if it isn't one already", result,
               sv.format("te_cm_switch_share", "%0"))
        )
        out["te_cmg_start_%s_effect_tt" % key] = (
            "%s becomes a primary culture here%s and the merge begins. Each constituent culture we hold that qualifies starts to "
            "assimilate into it."
            % (result, "" if merge.new is not None else " if it isn't one already")
        )
        out["te_cmg_%s_primary_tt" % key] = "A core culture of the merge, or its result, is a primary culture here: %s." % _either(_primary_cultures(merge))
        start = max(tiers[p.cultures[0]] for p in merge.core)
        for index, part in enumerate(merge.core, start=1):
            tier = tiers[part.cultures[0]]
            head = "%s pops are" % _either(part.cultures)
            if tier == 1:
                tail = ("held and accepted: our sphere holds most of their homeland pops, and the countries where many of them "
                        "live give them $full_acceptance$.")
            elif tier == 2:
                tail = ("held and very highly accepted for %s years: our sphere holds most of their homeland pops, and the countries "
                        "where many of them live accept them at %s or more, beyond $full_acceptance$."
                        % (sv.format("te_cm_years_tier2", "0"), sv.format("te_cm_accept_high_open", "0")))
            else:
                tail = ("held and accepted for %s years: our sphere holds most of their homeland pops, and the countries "
                        "where many of them live give them $full_acceptance$." % sv.format("te_cm_years_tier3", "0"))
            if tier != start:
                tail += " They also need $%s$." % TIER_TECH[tier]
            out["te_cmg_%s_core_%d_tt" % (key, index)] = "%s %s" % (head, tail)
        var = "[ROOT.GetCountry.MakeScope.Var('te_cm_sol_%s_" + key + "')%s]"
        out["te_cmg_%s_sol_tt" % key] = (
            "The core cultures live at similar standards of living: the gap between the best and the worst off is under %s "
            "to begin, counted once every core culture is held and accepted, and a running merge stalls once it passes %s. "
            "At the last census, %s pops were the best off, at %s, and %s pops the worst off, at %s: a gap of %s."
            % (sv.format("te_cm_sol_gap_open", "0"), sv.format("te_cm_sol_gap_close", "0"),
               var % ("best", ".GetCulture.GetName"), var % ("hi", ".GetValue|1"),
               var % ("worst", ".GetCulture.GetName"), var % ("lo", ".GetValue|1"), var % ("gap", ".GetValue|1"))
        )
        for component in merge.components:
            out["te_cmg_%s_comp_%s_tt" % (key, component)] = "The %s merge is complete." % _names([merge_by_key(component).result])
        for part in core_waits(merge):
            out["te_cmg_%s_wait_%s_tt" % (key, part.cultures[0])] = (
                "No country has %s open, or the merge has already waited %s years for it to end."
                % (_either(part.wait_for), sv.format("te_cm_wait_cap_years", "0"))
            )
    for text_key, text in out.items():
        if '"' in text or "\n" in text:
            raise ValueError("%s: a loc text can't hold a quote mark or a newline" % text_key)
    return out


def plan_outputs(root: Path = ROOT) -> dict[Path, str]:
    """Relative output path -> its text (without the BOM). Later tasks add outputs here."""
    vanilla = load_vanilla(root)
    plan = build_plan(vanilla)
    return {
        CULTURES_OUT: render_cultures(plan),
        TRAITS_OUT: render_traits(plan),
        STATIC_MODIFIERS_OUT: render_static_modifiers(plan),
        MODIFIER_TYPES_OUT: render_modifier_types(plan),
        LOC_OUT: render_loc(plan, {**static_modifier_loc(plan), **entry_loc(vanilla)}),
        TRIGGERS_GEN_OUT: render_triggers(vanilla),
        EFFECTS_GEN_OUT: render_effects(vanilla),
        JE_OUT: render_journal_entries(vanilla),
        BUTTONS_OUT: render_buttons(),
        BARS_OUT: render_bars(),
        VALUES_OUT: render_values(),
        DEFINITIONS_OUT: render_definitions(),
        VANILLA_TRIGGERS_OUT: render_vanilla_triggers(),
    }


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def regenerate(mod_state=None, *, root: Path = ROOT, dry_run: bool = False) -> dict:
    """Post-load entry point (mod_state_server.POST_LOAD_REGENERATORS) and CLI body.

    Reads only the vanilla snapshot; ``mod_state`` is unused. Writes a file
    only when its content changed, with one UTF-8 BOM.
    """
    changed = []
    for relative, text in plan_outputs(root).items():
        target = root / relative
        expected = text.encode("utf-8-sig")
        if not target.exists() or target.read_bytes() != expected:
            changed.append(str(relative))
            if not dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(expected)
    return {"changed": bool(changed), "changed_files": changed}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    mode.add_argument("--check", action="store_true", help="exit 1 if any output is stale")
    args = parser.parse_args(argv)
    result = regenerate(dry_run=args.dry_run or args.check)
    verb = "stale" if args.check else "would write" if args.dry_run else "wrote"
    for path in result["changed_files"]:
        print(f"{verb}: {path}")
    if not result["changed"]:
        print("culture merges: current")
    return int(args.check and result["changed"])


if __name__ == "__main__":
    sys.exit(main())
