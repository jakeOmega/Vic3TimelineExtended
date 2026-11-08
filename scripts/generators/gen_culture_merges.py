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
  ``_has_other_starter``, ``te_cmg_<m>_join_ready`` / ``_settle`` / ``te_cmg_start_<m>`` and
  ``te_cmg_release_lost_starters``.

Also carried: ``traditions`` is what every core part shares (usually nothing,
so ``{ }``), and ``name_format``, ``seal_and_signature_texture`` and the other
optional fields a vanilla culture may carry (``taboos``, ``assimilation_rate``)
come from the first core part when it has them. ``CARRIED_FIELDS`` names every
field the generator knows; a test fails if a vanilla patch adds one it doesn't.

Vanilla comes from the committed ``vanilla_parsed/`` snapshot, never from the
live ModState: that one also holds the ``cm_`` cultures this script writes, so
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

import culture_merges_config as cfg  # noqa: E402
from culture_merges_config import culture_traits, trait_group, unwrap  # noqa: E402
from organize_loc import _render_loc_file, section_label  # noqa: E402

HEADER = "# AUTO-GENERATED by scripts/generators/gen_culture_merges.py - do not edit manually."

CULTURES_OUT = Path("common/cultures/te_merged_cultures.txt")
TRAITS_OUT = Path("common/discrimination_traits/te_merged_culture_traits.txt")
LOC_OUT = Path("localization/english/te_culture_merges_generated_l_english.yml")
TRIGGERS_GEN_OUT = Path("common/scripted_triggers/te_culture_merges_generated_triggers.txt")
EFFECTS_GEN_OUT = Path("common/scripted_effects/te_culture_merges_generated_effects.txt")
JE_OUT = Path("common/journal_entries/te_culture_merges_generated.txt")
BUTTONS_OUT = Path("common/scripted_buttons/te_culture_merges_generated_buttons.txt")
BARS_OUT = Path("common/scripted_progress_bars/te_culture_merges_generated_bars.txt")
VALUES_OUT = Path("common/script_values/te_culture_merges_generated_values.txt")
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
    def block(self, header: str):
        self.line(header + " = {")
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


def _part_of(merge: cfg.Merge, culture: str) -> cfg.Part:
    for part in merge.core + merge.optional:
        if culture in part.cultures:
            return part
    raise ValueError("%s is not a part of the %s merge" % (culture, merge.key))


def _core_cultures(merge: cfg.Merge) -> list[str]:
    return [c for part in merge.core for c in part.cultures]


def _is_absorb_result(merge: cfg.Merge, culture: str) -> bool:
    """An absorb merge's result culture: held and acceptance-tested only, never joined or switched."""
    return merge.new is None and culture == merge.result


def _state_idle(key: str) -> str:
    return "NOR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 }" % (key, key)


def _state_running_or_complete(key: str) -> list[str]:
    return ["OR = {", "\tglobal_var:te_cm_state_%s ?= 1" % key, "\tglobal_var:te_cm_state_%s ?= 2" % key, "}"]


def _available_clauses(merge: cfg.Merge, culture: str, merges: tuple[cfg.Merge, ...]) -> list[str]:
    """What makes a slot culture free for this merge.

    Not joined to any other merge that lists it (``te_cm_in_<c>`` holds the index of
    the merge it joined, so each other index is its own ``?=`` test: a missing
    variable is false there, which is the idle case), and, for the result of
    another merge (a ``cm_`` id), that merge complete.
    """
    clauses = []
    for index, other in enumerate(merges, start=1):
        if other is not merge and culture in slot_cultures(other):
            clauses.append("NOT = { global_var:te_cm_in_%s ?= %d }" % (culture, index))
    for other in merges:
        if other.new is not None and other.result == culture:
            clauses.append("global_var:te_cm_state_%s ?= 2" % other.key)
    return clauses


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
    together), or when it joined this merge and has switched. ``core_ok``, ``can_start`` and the
    status line all read the same routes.
    """
    key = merge.key
    routes = []
    for c in part.cultures:
        route = ["te_cmg_%s_%s_measured = yes" % (key, c)]
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
    """The core parts that wait on a vanilla journal entry."""
    return [part for part in merge.core if part.wait_for]


def _wait_cap_reached(out: "_Script", key: str) -> None:
    """The merge's wait years have reached te_cm_wait_cap_years (false while the counter is unset)."""
    counter = "te_cm_wait_years_%s" % key
    with out.block("AND"):
        out.line("has_variable = %s" % counter)
        out.line("trigger_if = { limit = { has_variable = %s } var:%s >= te_cm_wait_cap_years }" % (counter, counter))


def _wait_entry_open(out: "_Script", entries: tuple[str, ...]) -> None:
    """A vanilla entry the part waits on is open in this country."""
    if len(entries) == 1:
        out.line("has_journal_entry = %s" % entries[0])
        return
    with out.block("OR"):
        for entry in entries:
            out.line("has_journal_entry = %s" % entry)


def _write_start_items(out: "_Script", merge: cfg.Merge, tier: int, tiers: dict[str, int]) -> None:
    """The conditions that let a country start the merge, except its waits, each in its own
    custom_tooltip so the button lists the one that fails. They restate ``is_candidate``'s
    primary culture and technology, the merge being idle, ``core_ok``'s slots (the same routes),
    the standard-of-living gate and the component merges."""
    key = merge.key
    with out.block("custom_tooltip"):
        out.line("text = te_cm_tt_idle")
        out.line(_state_idle(key))
    with out.block("custom_tooltip"):
        out.line("text = te_cmg_%s_primary_tt" % key)
        with out.block("OR"):
            for culture in _core_cultures(merge):
                out.line("country_has_primary_culture = cu:%s" % culture)
    with out.block("custom_tooltip"):
        out.line("text = te_cm_tt_tech_%d" % tier)
        out.line("te_cm_tier_tech = { TIER = %d }" % tier)
    for index, part in enumerate(merge.core, start=1):
        with out.block("custom_tooltip"):
            out.line("text = te_cmg_%s_core_%d_tt" % (key, index))
            _write_routes(out, _slot_routes(merge, part, tiers))
    with out.block("custom_tooltip"):
        out.line("text = te_cm_tt_sol")
        out.line("var:te_cm_sol_ok_%s ?= 1" % key)
    for component in merge.components:
        with out.block("custom_tooltip"):
            out.line("text = te_cmg_%s_comp_%s_tt" % (key, component))
            out.line("global_var:te_cm_state_%s ?= 2" % component)


def _write_wait_items(out: "_Script", merge: cfg.Merge) -> None:
    """One custom_tooltip per core part that waits: its vanilla entries are closed here, or the
    merge has waited long enough."""
    key = merge.key
    for part in core_waits(merge):
        with out.block("custom_tooltip"):
            out.line("text = te_cmg_%s_wait_%s_tt" % (key, part.cultures[0]))
            with out.block("OR"):
                if len(part.wait_for) == 1:
                    out.line("NOT = { has_journal_entry = %s }" % part.wait_for[0])
                else:
                    with out.block("NOR"):
                        for entry in part.wait_for:
                            out.line("has_journal_entry = %s" % entry)
                _wait_cap_reached(out, key)


def render_triggers(vanilla: dict, merges: tuple[cfg.Merge, ...] | None = None) -> str:
    """The per-merge scripted triggers.

    Per merge: ``is_candidate``, ``core_ok``, ``census_wanted``, ``is_starter``,
    ``has_other_starter``, ``can_start`` (and ``start_basics`` where a core part waits on a
    vanilla entry). Per slot culture: ``available``, ``measured`` (passing its gates now and
    not switched), ``years_met`` (tiers 2 and 3), ``switched_in`` (joined to this merge and
    switched: met for good), ``can_join`` and, where its part waits on a vanilla entry,
    ``waiting``.
    """
    merges = cfg.MERGES if merges is None else merges
    out = _Script()
    out.line(HEADER)
    for merge in merges:
        key = merge.key
        tier = start_tier(merge, vanilla, merges)
        optional = {c for part in merge.optional for c in part.cultures}
        tiers = {c: cfg.derive_tier(merge, c, vanilla, merges) for c in slot_cultures(merge)}
        out.line()
        out.line("# ---- %s (%s) ----" % (key, ", ".join("/".join(p.cultures) for p in merge.core)))
        out.line()
        out.line("# Country scope. Can this country start the %s merge? The system is on, a core culture is" % key)
        out.line("# primary, the technology of the highest core tier is known, and the merge is not complete.")
        with out.block("te_cmg_%s_is_candidate" % key):
            out.line("te_cm_system_enabled = yes")
            with out.block("OR"):
                for culture in _core_cultures(merge):
                    out.line("country_has_primary_culture = cu:%s" % culture)
            out.line("te_cm_tier_tech = { TIER = %d }" % tier)
            out.line("NOT = { global_var:te_cm_state_%s ?= 2 }" % key)
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
            out.line("# Country scope. %s (tier %s) passes its gates and can join the %s merge now." % (culture, ("1", "1b", "2")[ctier - 1], key))
            with out.block("te_cmg_%s_%s_can_join" % (key, culture)):
                out.line("var:te_cm_ok_%s_%s ?= 1" % (key, culture))
                out.line("te_cmg_%s_%s_available = yes" % (key, culture))
                out.line("NOT = { global_var:te_cm_joined_%s_%s ?= 1 }" % (key, culture))
                out.line("te_cm_tier_tech = { TIER = %d }" % ctier)
                if ctier > 1:
                    out.line("te_cmg_%s_%s_years_met = yes" % (key, culture))
                if culture in optional:
                    out.line("var:te_cm_sol_ok_%s_%s ?= 1" % (key, culture))
            wait_for = _part_of(merge, culture).wait_for
            if wait_for and not _is_absorb_result(merge, culture):
                out.line()
                out.line("# Country scope. %s waits on a vanilla journal entry of this country (%s) and the merge" % (culture, ", ".join(wait_for)))
                out.line("# has not yet waited te_cm_wait_cap_years: it doesn't join, and a core part doesn't let the merge start.")
                with out.block("te_cmg_%s_%s_waiting" % (key, culture)):
                    _wait_entry_open(out, wait_for)
                    with out.block("NOT"):
                        _wait_cap_reached(out, key)
        out.line()
        out.line("# Any scope. Is the yearly census of the %s merge worth running? An idle merge with a" % key)
        out.line("# candidate; or a running or complete one whose starter is alive and which still has a")
        out.line("# part that has neither switched nor left the world (a complete merge keeps its census so")
        out.line("# late parts can join). An absorb merge's result never switches, so it doesn't count.")
        with out.block("te_cmg_%s_census_wanted" % key):
            with out.block("OR"):
                with out.block("AND"):
                    out.line(_state_idle(key))
                    out.line("any_country = { te_cmg_%s_is_candidate = yes }" % key)
                with out.block("AND"):
                    for line in _state_running_or_complete(key):
                        out.line(line)
                    out.line("exists = global_var:te_cm_starter_%s" % key)
                    out.line("global_var:te_cm_starter_%s = { is_country_alive = yes }" % key)
                    with out.block("OR"):
                        for culture in slot_cultures(merge):
                            if _is_absorb_result(merge, culture):
                                continue
                            for line in _live_culture(culture):
                                out.line(line)
        out.line()
        out.line("# Country scope. This country started the %s merge, which is running or complete." % key)
        with out.block("te_cmg_%s_is_starter" % key):
            for line in _state_running_or_complete(key):
                out.line(line)
            out.line("exists = global_var:te_cm_starter_%s" % key)
            out.line("this = global_var:te_cm_starter_%s" % key)
        out.line()
        out.line("# Country scope. The %s merge is running or complete under another country." % key)
        with out.block("te_cmg_%s_has_other_starter" % key):
            for line in _state_running_or_complete(key):
                out.line(line)
            out.line("exists = global_var:te_cm_starter_%s" % key)
            out.line("NOT = { this = global_var:te_cm_starter_%s }" % key)
        waits = core_waits(merge)
        out.line()
        if waits:
            out.line("# Country scope. Everything the %s merge needs to start except its waits on vanilla entries" % key)
            out.line("# (each condition its own custom_tooltip). The census adds a wait year while this holds and an entry is open.")
            with out.block("te_cmg_%s_start_basics" % key):
                _write_start_items(out, merge, tier, tiers)
            out.line()
        out.line("# Country scope. Can this country start the %s merge now? The merge is idle, a core culture is" % key)
        out.line("# primary, the technology is known, every core slot is met, the standard-of-living gap is closed, the" )
        out.line("# component merges are complete and no vanilla entry on a core part is still open (or the wait ran its course)." )
        out.line("# Each condition sits in its own custom_tooltip, which the button and the entry show as a reason.")
        with out.block("te_cmg_%s_can_start" % key):
            if waits:
                out.line("te_cmg_%s_start_basics = yes" % key)
            else:
                _write_start_items(out, merge, tier, tiers)
            _write_wait_items(out, merge)
    return out.text()


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
    out.line("# vanilla entry: when the merge starts, and each census while its starter holds it.")
    with out.block("te_cmg_%s_join_ready" % key):
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
    out.line("# holds that qualify now.")
    with out.block("te_cmg_start_%s" % key):
        out.line("te_cm_start_merge = { MERGE = %s RESULT = %s }" % (key, merge.result))
        out.line("te_cmg_%s_join_ready = yes" % key)
    out.line()
    out.line("# Country scope: the tail of te_cmg_census_%s_country, run after the part gates are fresh." % key)
    out.line("# 1. A wait year, while the merge could start but a vanilla entry on a core part is open (once a census,")
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
        out.line("# result's (walked only then, and only while an optional part is neither joined nor switched).")
        with out.block("te_cmg_census_%s_country" % key):
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
            with out.block("if"):
                out.line("limit = { local_var:te_cm_sg_n > 0 }")
                out.line("set_local_variable = { name = te_cm_sg_gap value = local_var:te_cm_sg_max }")
                out.line("change_local_variable = { name = te_cm_sg_gap subtract = local_var:te_cm_sg_min }")
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
            if optional:
                out.line("set_local_variable = { name = te_cm_sg_ref value = 0 }")
                with out.block("if"):
                    with out.block("limit"):
                        out.line("local_var:te_cm_sg_n = 0")
                        out.line("local_var:te_cm_sg_all = 1")
                        with out.block("OR"):
                            for culture in optional:
                                with out.block("AND"):
                                    out.line("NOT = { global_var:te_cm_joined_%s_%s ?= 1 }" % (key, culture))
                                    out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
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
    out.line("# Any scope. A running merge whose starter no longer exists, or is no longer a living country, goes back")
    out.line("# to idle (te_cm_release_starter), so another country can start it. Run first by te_cm_yearly_on_action.")
    with out.block("te_cmg_release_lost_starters"):
        for merge in merges:
            key = merge.key
            with out.block("if"):
                with out.block("limit"):
                    out.line("global_var:te_cm_state_%s ?= 1" % key)
                    with out.block("OR"):
                        out.line("NOT = { exists = global_var:te_cm_starter_%s }" % key)
                        with out.block("AND"):
                            out.line("exists = global_var:te_cm_starter_%s" % key)
                            out.line("global_var:te_cm_starter_%s = { is_country_alive = no }" % key)
                out.line("te_cm_release_starter = { MERGE = %s }" % key)

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
    return out.text()


# ---------------------------------------------------------------------------
# Starting a merge: values, bars, buttons, journal entries and their loc
# ---------------------------------------------------------------------------

# Vanilla's waving flag, the icon Russification and the cultural renaissances use.
JE_ICON = "gfx/interface/icons/event_icons/waving_flag.dds"


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


def _either(cultures) -> str:
    """Loc splices as alternatives: ``$a$``, ``$a$ or $b$``, ``$a$, $b$ or $c$``."""
    names = ["$%s$" % c for c in cultures]
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " or " + names[-1]


def _joinable_core(merge: cfg.Merge) -> list[str]:
    """The core cultures a starter can bring in: every one except an absorb merge's result."""
    return [c for c in _core_cultures(merge) if not _is_absorb_result(merge, c)]


def render_values(merges: tuple[cfg.Merge, ...] | None = None) -> str:
    """Per merge, the progress the entry's bar shows (country scope, the starter).

    ``lowest_dom``: the smallest result share (te_cm_dom_<m>_<c>, Task 6's) among the core parts
    that joined and haven't switched; a joined part with no figure yet counts as 0. 1 when there is
    none. ``progress`` is that over te_cm_switch_share, capped at 1, and 0 until a core part has
    joined; ``bar_pct`` is the bar's 0 to 100.
    """
    merges = cfg.MERGES if merges is None else merges
    out = _Script()
    out.line(HEADER)
    for merge in merges:
        key = merge.key
        core = _joinable_core(merge)
        out.line()
        out.line("# ---- %s ----" % key)
        out.line()
        out.line("# Country scope (the starter). The smallest result share among the core parts of the %s merge that joined and" % key)
        out.line("# haven't switched: 1 with none left, 0 for a joined part Task 6's census hasn't measured yet.")
        with out.block("te_cmg_%s_lowest_dom" % key):
            out.line("value = 1")
            for culture in core:
                with out.block("if"):
                    with out.block("limit"):
                        out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
                        out.line("NOT = { has_global_variable = te_cm_switched_%s }" % culture)
                    with out.block("if"):
                        out.line("limit = { has_global_variable = te_cm_dom_%s_%s }" % (key, culture))
                        out.line("max = global_var:te_cm_dom_%s_%s" % (key, culture))
                    with out.block("else"):
                        out.line("max = 0")
        out.line()
        out.line("# Country scope. How far the %s merge is from its switch, 0 to 1: the lowest result share over the share at" % key)
        out.line("# which the rest of a part switches. 0 until a core part has joined.")
        with out.block("te_cmg_%s_progress" % key):
            out.line("value = 0")
            with out.block("if"):
                with out.block("limit"):
                    with out.block("OR"):
                        for culture in core:
                            out.line("global_var:te_cm_joined_%s_%s ?= 1" % (key, culture))
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

    Complete, running, running under another country, then an idle merge's first failing condition: no
    longer a candidate, not yet measured, each core slot (busy in another merge, not held, not accepted,
    not together long enough), the standard-of-living gap, a component merge, a vanilla wait, and last
    that the button is ready.
    """
    key = merge.key
    base = "je_te_cm_%s_status_" % key
    result = "$%s$" % merge.result
    tiers = {c: cfg.derive_tier(merge, c, vanilla, merges) for c in slot_cultures(merge)}
    sv = "[ROOT.GetCountry.MakeScope.ScriptValue('{}')|{}]"
    rows = [
        Row(
            base + "complete",
            ["te_cmg_%s_is_starter = yes" % key, "global_var:te_cm_state_%s ?= 2" % key],
            "The merge is complete: %s is the national culture across the sphere. Parts that qualify later can still join." % result,
        ),
        Row(
            base + "running",
            ["te_cmg_%s_is_starter = yes" % key],
            "The merge is running. In the least converted part's homeland, %s holds %s of the pops; at %s the rest of that part "
            "switches. Culture merge speed: +%s."
            % (result, sv.format("te_cmg_%s_lowest_dom" % key, "%0"), sv.format("te_cm_switch_share", "%0"),
               sv.format("te_cm_speed_display", "%0")),
        ),
        Row("te_cm_status_elsewhere", ["te_cmg_%s_has_other_starter = yes" % key]),
        Row("te_cm_status_not_candidate", _negated(["te_cmg_%s_is_candidate = yes" % key])),
        Row("te_cm_status_unmeasured", _negated(["has_variable = te_cm_ok_%s_%s" % (key, _core_cultures(merge)[0])])),
    ]
    for index, part in enumerate(merge.core, start=1):
        unmet = _negated(_lines(lambda s, part=part: _write_routes(s, _slot_routes(merge, part, tiers))))
        rows.append(
            Row(
                base + "busy_%d" % index,
                unmet + ["NOR = {"] + ["\tte_cmg_%s_%s_available = yes" % (key, c) for c in part.cultures] + ["}"],
                "%s pops are already part of another merge, which has to finish with them first." % _either(part.cultures),
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
            accept = "te_cm_accept_high_open" if tier == 2 else "te_cm_accept_open"
            rows.append(
                Row(
                    base + "accept_%s" % culture,
                    unmet + free + ["has_variable = %s" % ok, "var:%s = 0" % ok],
                    "$%s$ pops are second-class where many of them live: their acceptance in our sphere is below %s."
                    % (culture, sv.format(accept, "0")),
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
                        "$%s$ pops have not been with us long enough: [ROOT.GetCountry.MakeScope.Var('%s').GetValue|0] of %s years."
                        % (culture, years, sv.format(needed, "0")),
                    )
                )
    rows.append(Row("te_cm_status_sol", _negated(["var:te_cm_sol_ok_%s ?= 1" % key])))
    for component in merge.components:
        rows.append(
            Row(
                base + "component_%s" % component,
                _negated(["global_var:te_cm_state_%s ?= 2" % component]),
                "The %s merge has to finish first." % _names([merge_by_key(component).result]),
            )
        )
    for part in core_waits(merge):
        culture = part.cultures[0]
        rows.append(
            Row(
                base + "wait_%s" % culture,
                ["te_cmg_%s_start_basics = yes" % key, "te_cmg_%s_%s_waiting = yes" % (key, culture)],
                "The merge waits for %s to end here. It goes ahead after %s years at most."
                % (_names(part.wait_for), sv.format("te_cm_wait_cap_years", "0")),
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
    in the way, or the progress of the run. It concludes when the merge is complete, and silently when
    another country starts the merge first. A rule switched off pauses everything: `disable_evaluation`
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
            with out.block("disable_evaluation"):
                out.line("NOT = { te_cm_system_enabled = yes }")
            with out.block("is_shown_when_inactive"):
                out.line("te_cm_system_enabled = yes")
                out.line("te_cmg_%s_is_candidate = yes" % key)
            with out.block("possible"):
                with out.block("OR"):
                    out.line("te_cmg_%s_can_start = yes" % key)
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
                with out.block("trigger"):
                    out.line("te_cmg_%s_is_starter = yes" % key)
                    out.line("global_var:te_cm_state_%s ?= 2" % key)
            out.line()
            out.line("# Another country started this merge first (or it is complete under one): the entry ends silently.")
            with out.block("outcome"):
                out.line("flags = { hidden invalid_outcome }")
                out.line("conclusion_desc = te_cm_je_invalid_conclusion_desc")
                with out.block("trigger"):
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
        core = [c for part in merge.core for c in part.cultures[:1]]
        optional = [c for part in merge.optional for c in part.cultures[:1]]
        out[entry] = "Cultural Merge: %s" % result
        if merge.new is not None:
            reason = (
                "Closely related peoples can come to see themselves as one nation. The core of this merge is %s. Over the "
                "decades their pops become %s, and once it holds most of a part's homeland, every remaining pop of that "
                "part follows." % (_names(core), result)
            )
        else:
            reason = (
                "Closely related peoples can come to see themselves as one nation. Here %s pops would become part of the existing "
                "%s culture: over the decades their pops assimilate into it, and once it holds most of a part's homeland, every "
                "remaining pop of that part follows." % (_names([c for c in core if c != merge.result]), result)
            )
        if optional:
            reason += " %s can join once they qualify as well." % _names(optional)
        out[entry + "_reason"] = reason
        out[entry + "_complete_conclusion_desc"] = (
            "The merge is complete. %s is the national culture across the sphere, and the parts it brought in are one people." % result
        )
        for row in status_rows(merge, vanilla, merges):
            if row.text is not None:
                out[row.key] = row.text
        button = "te_cmg_start_%s_button" % key
        out[button] = "Begin the %s Merge" % result
        out[button + "_desc"] = (
            "Starts the merge of %s. %s becomes a primary culture here%s, and every part we hold begins to assimilate into it: "
            "a slice of its pops each year, those in subjects and bloc members more slowly. Once %s holds %s of a part's "
            "homeland, every remaining pop of that part switches at once."
            % (_names(core), result, "" if merge.new is not None else " if it isn't one already", result,
               sv.format("te_cm_switch_share", "%0"))
        )
        out["te_cmg_start_%s_effect_tt" % key] = (
            "%s becomes a primary culture here%s and the merge begins. Each part we hold that qualifies starts to assimilate into it."
            % (result, "" if merge.new is not None else " if it isn't one already")
        )
        out["te_cmg_%s_primary_tt" % key] = "A core culture of the merge is a primary culture here: %s." % _either(_core_cultures(merge))
        for index, part in enumerate(merge.core, start=1):
            tier = tiers[part.cultures[0]]
            head = "%s pops are" % _either(part.cultures)
            if tier == 1:
                tail = "held and accepted: our sphere holds most of their homeland pops, and the countries where many of them live accept them."
            elif tier == 2:
                tail = ("held and very highly accepted for decades: our sphere holds most of their homeland pops, and the countries "
                        "where many of them live accept them far above the usual mark.")
            else:
                tail = ("held and accepted for generations: our sphere holds most of their homeland pops, and the countries "
                        "where many of them live have accepted them for half a century.")
            out["te_cmg_%s_core_%d_tt" % (key, index)] = "%s %s" % (head, tail)
        for component in merge.components:
            out["te_cmg_%s_comp_%s_tt" % (key, component)] = "The %s merge is complete." % _names([merge_by_key(component).result])
        for part in core_waits(merge):
            out["te_cmg_%s_wait_%s_tt" % (key, part.cultures[0])] = (
                "%s is not open here, or the merge has already waited %s years for it to end."
                % (_names(part.wait_for), sv.format("te_cm_wait_cap_years", "0"))
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
        LOC_OUT: render_loc(plan, entry_loc(vanilla)),
        TRIGGERS_GEN_OUT: render_triggers(vanilla),
        EFFECTS_GEN_OUT: render_effects(vanilla),
        JE_OUT: render_journal_entries(vanilla),
        BUTTONS_OUT: render_buttons(),
        BARS_OUT: render_bars(),
        VALUES_OUT: render_values(),
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
