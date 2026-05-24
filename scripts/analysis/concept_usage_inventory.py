"""One-shot inventory of every game-concept reference in mod localization.

Companion to the semantic concept-usage audit (docs/audits/concept_usage_audit.md).
Where `concept_reference_audit.py` checks whether a referenced concept *exists*,
this script enumerates every reference instance and joins it to the concept's
display name + meaning, so a human/LLM pass can judge whether the concept's
*meaning* fits the surrounding text (the homonym-misuse class, e.g. "genetic
[concept_screening]" linking to the naval ship-screening concept).

Not wired into POST /reload — run manually:
    python3 scripts/analysis/concept_usage_inventory.py            # writes JSON
    python3 scripts/analysis/concept_usage_inventory.py --summary  # prints stats

Outputs scripts/analysis/concept_usage_inventory.json (gitignored scratch).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from path_constants import mod_path, base_game_path  # noqa: E402

# Reference forms (mirrors concept_reference_audit.py).
_PATTERN_PLAIN = re.compile(r"\[(concept_[A-Za-z0-9_]+)\]")
_PATTERN_CONCEPT_FN = re.compile(r"Concept\(\s*['\"](concept_[A-Za-z0-9_]+)['\"]")
# Free-standing $concept_X$ substitution (renders the loc var, NOT a link).
_PATTERN_DOLLAR = re.compile(r"\$(concept_[A-Za-z0-9_]+)\$")
# A loc-name display key line: `concept_x:0 "Name"` or `concept_x_desc:0 "..."`.
_LOC_KEY_RE = re.compile(r"^\s*(concept_[A-Za-z0-9_]+):\d*\s*\"(.*)\"\s*$")


def _parse_loc_line(raw):
    """Return (key, value, trailing) or None. Mirrors mod_state.add_localization."""
    line = raw.rstrip("\n")
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#") or ":" not in stripped:
        return None
    key, rest = line.split(":", 1)
    key = key.strip()
    if not key:
        return None
    quotes = [i for i, c in enumerate(rest) if c == '"']
    if len(quotes) < 2:
        return None
    return key, rest[quotes[0] + 1: quotes[1]], rest[quotes[1] + 1:]


def load_concept_loc():
    """display-name + first-sentence-of-desc for every concept, vanilla + mod.

    Returns {concept_key: {"name": str, "desc": str}}. Mod values override vanilla.
    """
    out = {}
    sources = [
        os.path.join(base_game_path, "game", "localization", "english"),
        os.path.join(mod_path, "localization", "english"),
    ]
    for root in sources:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for fn in sorted(files):
                if not fn.endswith(".yml"):
                    continue
                try:
                    with open(os.path.join(dirpath, fn), encoding="utf-8-sig",
                              errors="replace") as fh:
                        for raw in fh:
                            m = _LOC_KEY_RE.match(raw)
                            if not m:
                                continue
                            key, val = m.group(1), m.group(2)
                            if key.endswith("_desc"):
                                base = key[:-len("_desc")]
                                out.setdefault(base, {"name": "", "desc": ""})
                                out[base]["desc"] = val
                            else:
                                out.setdefault(key, {"name": "", "desc": ""})
                                out[key]["name"] = val
                except OSError:
                    pass
    return out


def extract_instances():
    """Every concept reference in mod loc. One row per (line, concept, form)."""
    rows = []
    dollar_standalone = []  # $concept_X$ not inside a [Concept(...)] wrapper
    loc_root = os.path.join(mod_path, "localization", "english")
    for dirpath, _dirs, files in os.walk(loc_root):
        for fn in sorted(files):
            if not fn.endswith(".yml"):
                continue
            abs_p = os.path.join(dirpath, fn)
            rel_p = os.path.relpath(abs_p, mod_path)
            try:
                with open(abs_p, encoding="utf-8-sig", errors="replace") as fh:
                    for i, raw in enumerate(fh, start=1):
                        parsed = _parse_loc_line(raw)
                        if parsed is None:
                            continue
                        loc_key, value, _trailing = parsed
                        # Collapse the [Concept('x', '$x$')] wrappers so we don't
                        # double-count the inner $...$ as a free-standing var.
                        masked = _PATTERN_CONCEPT_FN.sub("", value)
                        for cid in _PATTERN_DOLLAR.findall(masked):
                            dollar_standalone.append(
                                {"file": rel_p, "line": i, "loc_key": loc_key,
                                 "concept": cid})
                        seen = set()
                        pairs = (
                            [(c, "[concept_X]") for c in _PATTERN_PLAIN.findall(value)]
                            + [(c, "[Concept(...)]")
                               for c in _PATTERN_CONCEPT_FN.findall(value)]
                        )
                        for concept, form in pairs:
                            if (concept, form) in seen:
                                continue
                            seen.add((concept, form))
                            rows.append({
                                "file": rel_p, "line": i, "loc_key": loc_key,
                                "concept": concept, "form": form,
                                "context": value.strip(),
                            })
            except OSError:
                pass
    return rows, dollar_standalone


def main():
    loc = load_concept_loc()
    rows, dollar = extract_instances()
    for r in rows:
        meta = loc.get(r["concept"], {})
        r["concept_name"] = meta.get("name", "")
        r["concept_desc"] = meta.get("desc", "")
        r["registered"] = r["concept"] in loc or bool(meta)

    distinct = sorted({r["concept"] for r in rows})
    by_concept = {}
    for r in rows:
        by_concept.setdefault(r["concept"], 0)
        by_concept[r["concept"]] += 1

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "concept_usage_inventory.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "dollar_standalone": dollar,
                   "distinct": distinct, "counts": by_concept}, fh, indent=1)

    if "--summary" in sys.argv or True:
        forms = {}
        for r in rows:
            forms[r["form"]] = forms.get(r["form"], 0) + 1
        print(f"total reference instances : {len(rows)}")
        print(f"  by form                 : {forms}")
        print(f"distinct concept keys     : {len(distinct)}")
        print(f"free-standing $concept_X$ : {len(dollar)} (filtered out of refs)")
        unresolved = sorted({r['concept'] for r in rows if not r['concept_name']})
        print(f"refs w/o resolved name    : {len(unresolved)}")
        if unresolved:
            print("   ", ", ".join(unresolved[:40]))
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
