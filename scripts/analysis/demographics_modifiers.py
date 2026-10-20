"""The demographics modifier types' totals (mortality and fertility), resolved from the game files.

Spec: docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md, Decision 2:
the values sit beside the techs, laws and institutions that carry them, and the model takes
modifier totals. load_carriers() reads every carrier from a narrow ModState (technologies,
laws, institutions and amendments; vanilla from the committed vanilla_parsed/ snapshot, so no
game is needed). totals() sums what one state reads, given its owner's techs, laws, amendments
and institution investment levels:
    a technology's, law's or amendment's `modifier`   every state the country owns (states inherit it)
    a law's `institution_modifier`          per level of the law's institution, incorporated states
    an institution's own `modifier`         per level, incorporated states
"""

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_params as P  # noqa: E402

# ModState entity type -> directory under common/.
ENTITY_TYPES = {"Technologies": "technology/technologies", "Laws": "laws", "Institutions": "institutions",
                "Amendments": "amendments"}
KINDS = ("technology", "law", "law_institution", "institution", "amendment")


@dataclass(frozen=True)
class Carrier:
    """One line carrying a type: `kind` is one of KINDS, `key` the tech, law or institution,
    `institution` the institution whose level scales it (law_institution and institution)."""
    kind: str
    key: str
    type: str
    value: float
    institution: str | None = None


def _u(v):
    """A parsed value without its ('=', ...) wrapper."""
    return v[1] if isinstance(v, tuple) and len(v) == 2 and v[0] == "=" else v


def _state(root):
    import vanilla_parsed
    from mod_state import ModState

    snap = Path(root) / "vanilla_parsed"
    manifest = vanilla_parsed.read_manifest(str(snap)) or {}
    vanilla = {}
    for et in ENTITY_TYPES:
        info = manifest.get("entity_types", {}).get(et)
        if info:
            with open(snap / info["file"], encoding="utf-8") as fh:
                vanilla[et] = vanilla_parsed.decode(json.load(fh))
    return ModState({et: "" for et in ENTITY_TYPES},
                    {et: os.path.join(str(root), "common", d) for et, d in ENTITY_TYPES.items()},
                    vanilla_data=vanilla)


def _lines(block, types):
    """(type, value) for each line of `types` in a modifier block; a boolean type's `yes` counts 1 (Human Purity's ban)."""
    body = _u(block)
    if not isinstance(body, dict):
        return
    for k, v in body.items():
        if k in types:
            v = _u(v)
            yield k, 1.0 if v == "yes" else float(v)


def load_carriers(root=ROOT, types=P.DEMOG_TYPES):
    """Every line that carries one of `types`, from techs, laws, institutions and amendments (Undivided Farm
    Succession's Late Marriage line, 2026-10-17)."""
    types = set(types)
    ms = _state(root)
    out = []
    for key, entry in ms.get_data("Technologies").items():
        for t, v in _lines(_u(entry).get("modifier"), types):
            out.append(Carrier("technology", key, t, v))
    for key, entry in ms.get_data("Laws").items():
        body = _u(entry)
        for t, v in _lines(body.get("modifier"), types):
            out.append(Carrier("law", key, t, v))
        inst = _u(body.get("institution"))
        for t, v in _lines(body.get("institution_modifier"), types):
            out.append(Carrier("law_institution", key, t, v, inst))
    for key, entry in ms.get_data("Institutions").items():
        for t, v in _lines(_u(entry).get("modifier"), types):
            out.append(Carrier("institution", key, t, v, key))
    for key, entry in ms.get_data("Amendments").items():
        for t, v in _lines(_u(entry).get("modifier"), types):
            out.append(Carrier("amendment", key, t, v))
    return out


def totals(carriers, techs=(), laws=(), institutions=None, incorporated=True, types=P.DEMOG_TYPES,
           institution_impact=1.0, amendments=()):
    """{type: total} that one state reads: its owner's techs, laws and amendments and, in an incorporated
    state, each institution line times the owner's investment level in that institution, times the
    state's Impact of Institutions (1 + state_institution_impact_add, at least 0: Local Vernacular's -0.05,
    obstinance's -1.0 x its share; the probe session, 2026-10-11)."""
    techs, laws, levels, amendments = set(techs), set(laws), institutions or {}, set(amendments)
    out = {t: 0.0 for t in types}
    for c in carriers:
        if c.type not in out:
            continue
        if c.kind == "technology" and c.key in techs:
            out[c.type] += c.value
        elif (c.kind == "law" and c.key in laws) or (c.kind == "amendment" and c.key in amendments):
            out[c.type] += c.value
        elif c.kind == "law_institution" and c.key in laws and incorporated:
            out[c.type] += c.value * levels.get(c.institution, 0) * institution_impact
        elif c.kind == "institution" and incorporated:
            out[c.type] += c.value * levels.get(c.key, 0) * institution_impact
    return out


def engine_rate_lines(root=ROOT, mod=True, keep=None):
    """{(kind, key, block, field): net value} for every `*_mult` line in a law's `modifier` or
    `institution_modifier`, a technology's or an institution's `modifier` (`keep`, a predicate on the field, picks
    other fields instead: phase 2 step 1's working-adult families and participation inputs). Vanilla's and (with mod) the
    mod's are summed as the engine sums an INJECT (scripting_best_practices.md § INJECT); a mod REPLACE
    drops vanilla's. kind: law, technology, institution. Since the engine-lines plan (2026-10-11) a moved
    line's engine field nets to zero here (its INJECT's cancel) and its value is under its script-only type
    (engine_lines() reads those back)."""
    from paradox_file_parser import ParadoxFileParser

    files = {"law": ("laws", "laws"), "technology": ("technologies", "technology/technologies"),
             "institution": ("institutions", "institutions")}
    out = {}
    keep = keep or (lambda f: f.endswith("_mult"))

    def w(v):
        """A value without its ("=", ...) wrapper: a tuple from the parser, a list from vanilla_parsed's JSON."""
        return v[1] if isinstance(v, (list, tuple)) and len(v) == 2 and v[0] == "=" else v

    def each(v):
        """A block or value that appears once, or each of its copies when the entity repeats it (vanilla's
        concrete_dockyards has two `modifier` blocks): the engine applies every copy, so they sum."""
        v = w(v)
        if isinstance(v, list):
            return [w(x) for x in v]
        return [] if v is None else [v]

    def add(kind, key, body):
        body = w(body)
        if not isinstance(body, dict):
            return
        for block in ("modifier", "institution_modifier"):
            for lines in each(body.get(block)):
                for field, value in (lines if isinstance(lines, dict) else {}).items():
                    if keep(field):
                        k = (kind, key, block, field)
                        out[k] = out.get(k, 0.0) + sum(float(x) for x in each(value))

    for kind, (snap, sub) in files.items():
        vanilla = json.loads((Path(root) / "vanilla_parsed" / "common" / f"{snap}.json").read_text(encoding="utf-8"))
        for key, body in vanilla.get("data", vanilla).items():
            add(kind, key, body)
        if not mod:
            continue
        for path in sorted((Path(root) / "common" / sub).glob("*.txt")):
            parser = ParadoxFileParser()
            parser.parse_file(str(path), apply_directives=False)
            for name, body in parser.data.items():
                directive, _, key = name.rpartition(":")
                if directive == "REPLACE":
                    for k in [k for k in out if k[0] == kind and k[1] == key]:
                        del out[k]
                add(kind, key, body)
    return out


_ENGINE_RATE_FIELD = re.compile(r"^state_(birth_rate|mortality|mortality_wealth|\w+_mortality)_mult$")


def is_engine_rate_field(field):
    """A field the engine applies to births or deaths: the state's birth or mortality multiplier, a class's
    mortality or wealth mortality. The census's own script-only types (state_work_mortality_mult and the like)
    are inputs, not engine lines."""
    return (bool(_ENGINE_RATE_FIELD.match(field)) and field not in P.DEMOG_TYPES
            and field not in P.ENGINE_LINE_TYPES.values() and field not in P.MEASURE_TYPES)


def engine_lines(root=ROOT):
    """{(kind, key, block, engine field): (family, value)}: the engine's birth and mortality lines moved to script-only
    types (owner, 2026-10-11; docs/superpowers/archive/plans/2026-10-11-demographics-engine-lines-script-only.md), read back
    from the carriers. engine_rate_lines already sums every *_mult line, vanilla's and the mod's, so a type's line is
    found under its own name and mapped back to the field it replaces."""
    back = {name: fam_field for fam_field, name in P.ENGINE_LINE_TYPES.items()}
    out = {}
    for (kind, key, block, field), value in engine_rate_lines(root).items():
        if field in back and abs(value) > 1e-9:
            family, engine_field = back[field]
            out[(kind, key, block, engine_field)] = (family, value)
    return out


def line_carriers(root=ROOT):
    """engine_lines() as Carriers typed by their family's script-only type (owner, 2026-10-11), with the scaling kinds
    the engine applies: a law's institution_modifier line is law_institution (per level of the law's institution,
    incorporated states), an institution's own line institution (per its level), the rest flat. totals() over these
    gives a state's families as the engine sums them (at full Impact of Institutions)."""
    institution = {key: _u(_u(entry).get("institution")) for key, entry in _state(root).get_data("Laws").items()}
    out = []
    for (kind, key, block, field), (family, value) in sorted(engine_lines(root).items()):
        name = P.ENGINE_LINE_TYPES[(family, field)]
        if kind == "law" and block == "institution_modifier":
            out.append(Carrier("law_institution", key, name, value, institution.get(key)))
        elif kind == "institution":
            out.append(Carrier("institution", key, name, value, key))
        else:
            out.append(Carrier(kind, key, name, value))
    return out


def engine_workforce_lines(root=ROOT):
    """{(kind, key, block, field): (family, value)}: the working-adult lines moved to the women's-work and replaced
    types (phase 2 step 1), read back from the laws and technologies as engine_lines() reads the births and deaths
    ones. The amendments, IG traits and static modifiers are no reader's: TestWorkforceLinesMoved reads their blocks."""
    names = set(P.WORKFORCE_LINE_TYPES.values())
    back = {name: fam_field for fam_field, name in P.WORKFORCE_LINE_TYPES.items()}
    out = {}
    for (kind, key, block, field), value in engine_rate_lines(root, keep=lambda f: f in names).items():
        if abs(value) > 1e-9:
            family, engine_field = back[field]
            out[(kind, key, block, engine_field)] = (family, value)
    return out


def workforce_line_carriers(root=ROOT):
    """engine_workforce_lines() as Carriers typed by their family's type, with the engine's scaling kinds (as
    line_carriers)."""
    institution = {key: _u(_u(entry).get("institution")) for key, entry in _state(root).get_data("Laws").items()}
    out = []
    for (kind, key, block, field), (family, value) in sorted(engine_workforce_lines(root).items()):
        name = P.WORKFORCE_LINE_TYPES[(family, field)]
        if kind == "law" and block == "institution_modifier":
            out.append(Carrier("law_institution", key, name, value, institution.get(key)))
        elif kind == "institution":
            out.append(Carrier("institution", key, name, value, key))
        else:
            out.append(Carrier(kind, key, name, value))
    return out


def absorbed_carriers(root=ROOT, lines=None):
    """Phase 2 step 4 (owner amendment, 2026-10-10): any engine birth or mortality line still live on a law,
    technology or institution that the census would absorb, as Carriers (`type` is the engine field). Since the
    engine-lines plan (2026-10-11) every such line sits on a script-only type, so this returns [] (the walk nets
    nothing for them; TestEngineLinesMoved fails CI on a new one). Every live line not on top (P.ENGINE_LINES_ON_TOP's carriers,
    P.ENGINE_FIELDS_ON_TOP's fields) is absorbed. Kinds follow the engine's scaling: a law's
    institution_modifier line is law_institution (per level of the law's institution, incorporated states), an
    institution's own line is institution (per its level, incorporated states), the rest are flat."""
    lines = engine_rate_lines(root) if lines is None else lines
    institution = {key: _u(_u(entry).get("institution")) for key, entry in _state(root).get_data("Laws").items()}
    out = []
    for (kind, key, block, field), value in sorted(lines.items()):
        if abs(value) < 1e-12 or not is_engine_rate_field(field):
            continue
        if key in P.ENGINE_LINES_ON_TOP or field in P.ENGINE_FIELDS_ON_TOP:
            continue
        if kind == "law" and block == "institution_modifier":
            out.append(Carrier("law_institution", key, field, value, institution.get(key)))
        elif kind == "institution":
            out.append(Carrier("institution", key, field, value, key))
        else:
            out.append(Carrier(kind, key, field, value))
    return out


def engine_line_totals(lines, laws=(), techs=()):
    """{field: total} of the flat `modifier` lines (engine_rate_lines' keys) a country's laws and techs carry.
    Per-level law lines are left out: after phase 2 step 4 none of the birth or mortality ones is live
    (the health laws' are absorbed), and predict says so if one ever is."""
    laws, techs = set(laws), set(techs)
    out = {}
    for (kind, key, block, field), value in lines.items():
        if block == "modifier" and ((kind == "law" and key in laws) or (kind == "technology" and key in techs)):
            out[field] = out.get(field, 0.0) + value
    return {k: v for k, v in out.items() if v}


# ---- Phase 2 step 3b: the Family Policy measures' lines (demographics_harness.py measures) --------------------------
MEASURE_MODIFIERS = Path("common") / "static_modifiers" / "te_demog_measure_modifiers.txt"
MEASURE_PREFIX = "te_demog_ms_"


def measure_lines(root=ROOT):
    """{measure: {field: value}} of each measure's country modifier (te_demog_measure_modifiers.txt; Birth Limit's one
    child as birth_limit_one), the _cost modifiers left out: the game file is the source of the census types' sizes, as
    load_carriers reads the laws' and techs'. A measure's census types reach every state of its country."""
    from paradox_file_parser import ParadoxFileParser

    parser = ParadoxFileParser()
    parser.parse_file(str(Path(root) / MEASURE_MODIFIERS), apply_directives=False)
    out = {}
    for name, body in parser.data.items():
        if not name.startswith(MEASURE_PREFIX) or name.endswith("_cost"):
            continue
        lines = {}
        for field, value in (_u(body) or {}).items():
            try:
                lines[field] = float(_u(value))
            except (TypeError, ValueError):
                continue   # the icon
        out[name[len(MEASURE_PREFIX):]] = lines
    return out
