"""The demographics modifier types' totals (mortality and fertility), resolved from the game files.

Spec: docs/superpowers/specs/2026-10-09-demographics-modifier-types-design.md, Decision 2:
the values sit beside the techs, laws and institutions that carry them, and the model takes
modifier totals. load_carriers() reads every carrier from a narrow ModState (technologies,
laws and institutions; vanilla from the committed vanilla_parsed/ snapshot, so no game is
needed). totals() sums what one state reads, given its owner's techs, laws and institution
investment levels:
    a technology's or law's `modifier`      every state the country owns (states inherit it)
    a law's `institution_modifier`          per level of the law's institution, incorporated states
    an institution's own `modifier`         per level, incorporated states
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import demographics_params as P  # noqa: E402

# ModState entity type -> directory under common/.
ENTITY_TYPES = {"Technologies": "technology/technologies", "Laws": "laws", "Institutions": "institutions"}
KINDS = ("technology", "law", "law_institution", "institution")


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
    body = _u(block)
    if not isinstance(body, dict):
        return
    for k, v in body.items():
        if k in types:
            yield k, float(_u(v))


def load_carriers(root=ROOT, types=P.DEMOG_TYPES):
    """Every line that carries one of `types`, from techs, laws and institutions."""
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
    return out


def totals(carriers, techs=(), laws=(), institutions=None, incorporated=True, types=P.DEMOG_TYPES):
    """{type: total} that one state reads: its owner's techs and laws and, in an incorporated
    state, each institution line times the owner's investment level in that institution."""
    techs, laws, levels = set(techs), set(laws), institutions or {}
    out = {t: 0.0 for t in types}
    for c in carriers:
        if c.type not in out:
            continue
        if c.kind == "technology" and c.key in techs:
            out[c.type] += c.value
        elif c.kind == "law" and c.key in laws:
            out[c.type] += c.value
        elif c.kind == "law_institution" and c.key in laws and incorporated:
            out[c.type] += c.value * levels.get(c.institution, 0)
        elif c.kind == "institution" and incorporated:
            out[c.type] += c.value * levels.get(c.key, 0)
    return out


def engine_rate_lines(root=ROOT, mod=True):
    """{(kind, key, block, field): net value} for every `*_mult` line in a law's `modifier` or
    `institution_modifier`, a technology's or an institution's `modifier`. Vanilla's and (with mod) the
    mod's are summed as the engine sums an INJECT (scripting_best_practices.md § INJECT); a mod REPLACE
    drops vanilla's. kind: law, technology, institution. Phase 2 step 4: which birth and mortality lines
    the census absorbs (they net to zero) and which stay on top (P.ENGINE_LINES_ON_TOP)."""
    from paradox_file_parser import ParadoxFileParser

    files = {"law": ("laws", "laws"), "technology": ("technologies", "technology/technologies"),
             "institution": ("institutions", "institutions")}
    out = {}

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
                    if field.endswith("_mult"):
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
