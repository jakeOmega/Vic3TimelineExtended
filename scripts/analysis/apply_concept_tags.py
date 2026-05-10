"""Auto-apply `[concept_X]` tags from the concept_term_audit candidate set.

Conservative: only acts on candidates that pass ALL of these:
  1. Surface form is multi-word (highest precision).
  2. Loc key ends in a description-style suffix
     (`_desc`, `_modifier_desc`, `_tt`, `_tooltip`).
  3. The first occurrence of the surface form in the value is preceded
     by whitespace/start (not part of a longer compound) — already
     handled by word-boundary regex in the scanner.

Ignored cases (left for human review):
  - Single-word matches (Tier 1/2 single-word jargon).
  - Loc keys that are bare labels (`pm_X`, `concept_X`, modifier names).
  - Lines where multiple concepts overlap or compete.

Each edit replaces only the FIRST untagged occurrence per (file, line,
concept) tuple — so a value mentioning "Power Bloc" three times gets one
hyperlink, not three. The remaining occurrences will appear in a re-run
and can be tagged manually if desired.

Run after `concept_term_audit.py`. Reads candidates by re-running the
scan in-process (cheaper than parsing the markdown report).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "analysis"))

import concept_term_audit as audit  # noqa: E402
from path_constants import mod_path  # noqa: E402


# Loc keys that indicate descriptive prose where embedding [concept_X]
# tags is appropriate.
DESCRIPTION_KEY_RE = re.compile(
    r"(?:_desc|_tt|_tooltip|_description|_text|_help)$"
    r"|^je_.*_desc$"
)
# Modifier display labels — `_add` / `_mult` / `_max_*` etc. These render
# in tooltip/effects panels alongside their values; tagging concept terms
# inside them produces a hyperlink in the panel header. Vanilla does this
# heavily (see e.g. `concept_X` references in `country_*_add` modifier
# loc).
MODIFIER_LABEL_KEY_RE = re.compile(
    r"_(?:add|mult|max|min)$"
    r"|_max_[a-z_]+$"
)


def _is_description_key(loc_key: str) -> bool:
    return bool(DESCRIPTION_KEY_RE.search(loc_key))


def _is_modifier_label_key(loc_key: str) -> bool:
    return bool(MODIFIER_LABEL_KEY_RE.search(loc_key))


def _load_canonical_display_names() -> dict[str, str]:
    """Returns concept_id → its canonical display name (the value of the
    `concept_X` loc key). Used to gate auto-application: we only tag when
    the matched text matches the canonical, so the rendered output keeps
    the same inflection as the source."""
    loc: dict[str, str] = {}
    loc_files = [
        Path(audit.base_game_path) / "game" / "localization" / "english" / "concepts_l_english.yml",
        Path(mod_path) / "localization" / "english" / "te_concepts_l_english.yml",
    ]
    for fp in loc_files:
        if fp.is_file():
            for k, v in audit._read_loc_file(fp).items():
                loc[k] = v
    out: dict[str, str] = {}
    for k, v in loc.items():
        # Only the bare `concept_X` keys (not `_short`, `_plural`, etc.).
        if not k.startswith("concept_"):
            continue
        if k.endswith(("_desc", "_short", "_plural", "_possessive", "_added")):
            continue
        if "[" in v or "$" in v:
            continue
        out[k] = v.strip()
    return out


def filter_high_confidence(
    candidates: list[audit.Candidate],
) -> list[audit.Candidate]:
    """Keep candidates where the matched text exactly equals the
    canonical concept display — so [concept_X] expansion preserves the
    rendered inflection — and the loc key is description-style.

    Both multi-word and single-word surfaces qualify, as long as both
    the matched text and the surface form equal the canonical. Single-
    word matches are higher false-positive risk but the audit's tier
    curation has already filtered out the dangerous everyday-English
    cases (Authority/Innovation already context-gated, common nouns
    excluded entirely).

    Skipped (left for human review):
      - Loc keys that are bare labels (not `_desc`-style).
      - Plural / short / alias matches where canonical-render would
        change inflection — those need the Concept() form.
    """
    return _filter(candidates, allow_modifier_labels=False)


def filter_with_modifier_labels(
    candidates: list[audit.Candidate],
) -> list[audit.Candidate]:
    """Same gates as `filter_high_confidence`, plus accepts modifier-label
    keys (`_add`, `_mult`, `_max`). These render in tooltip headers; the
    hyperlink is appropriate, vanilla precedent is heavy."""
    return _filter(candidates, allow_modifier_labels=True)


def _filter(
    candidates: list[audit.Candidate],
    *,
    allow_modifier_labels: bool,
    allow_case_variant: bool = False,
) -> list[audit.Candidate]:
    canonical = _load_canonical_display_names()
    keep: list[audit.Candidate] = []
    for c in candidates:
        is_desc = _is_description_key(c.loc_key)
        is_mod_label = allow_modifier_labels and _is_modifier_label_key(c.loc_key)
        if not (is_desc or is_mod_label):
            continue
        canon = canonical.get(c.cid)
        if canon is None or c.surface != canon:
            continue
        if allow_case_variant:
            # Vanilla convention: tagging "throughput" as `[concept_throughput]`
            # renders "Throughput" capitalized mid-sentence — read as a
            # game-mechanic term. Same for proper-noun-y jargon like
            # "Bureaucracy", "Infamy", "Zaibatsu".
            if c.matched_term.lower() != canon.lower():
                continue
        else:
            if c.matched_term != canon:
                continue
        # Tier 2 (context-gated single-word) is too ambiguous to auto-tag:
        # e.g. "Authority" in `concept_un_authority_desc` would link to
        # vanilla `concept_authority` (the wrong concept). Multi-word
        # matches and Tier 1 single-word jargon stay.
        if c.tier == 2 and " " not in c.surface:
            continue
        keep.append(c)
    return keep


def filter_with_case_variants(
    candidates: list[audit.Candidate],
) -> list[audit.Candidate]:
    """Like `filter_high_confidence` plus case-insensitive matching.
    Tagging lowercase "throughput" as `[concept_throughput]` is fine —
    the engine renders "Throughput" (capitalized canonical), matching
    vanilla's convention of capitalizing game-mechanic terms in flow
    text."""
    return _filter(candidates, allow_modifier_labels=False, allow_case_variant=True)


def filter_with_labels_and_case(
    candidates: list[audit.Candidate],
) -> list[audit.Candidate]:
    return _filter(candidates, allow_modifier_labels=True, allow_case_variant=True)


def filter_other_labels(
    candidates: list[audit.Candidate],
) -> list[audit.Candidate]:
    """Allow tagging in non-_desc, non-modifier-label keys (entity names,
    headers, titles). Stricter requirement: matched text must equal the
    canonical display, AND the value must contain at least one word
    beyond the concept term (skips bare-label keys whose value is just
    the concept name — already handled by the value==surface check).
    Tier 2 single-word excluded (ambiguity risk).
    """
    canonical = _load_canonical_display_names()
    keep: list[audit.Candidate] = []
    for c in candidates:
        if _is_description_key(c.loc_key) or _is_modifier_label_key(c.loc_key):
            continue
        canon = canonical.get(c.cid)
        if canon is None or c.surface != canon:
            continue
        if c.matched_term != canon:
            continue
        if c.tier == 2 and " " not in c.surface:
            continue
        # Skip bare-label values (value identical to concept name —
        # nothing to gain from a hyperlink that just renders the same).
        if c.raw_value.strip().strip(".").lower() == canon.lower():
            continue
        # Skip single-word matches in compound names: avoids "Radical"
        # in "Radical Mentors" tagging to concept_radical.
        if " " not in c.surface:
            words = c.raw_value.split()
            if len(words) > 1:
                continue
        keep.append(c)
    return keep


_QUANT_PRECEDING = {
    "low", "high", "lower", "higher", "more", "less",
    "reduced", "increased", "reduces", "reduce",
    "boosts", "boost", "gains", "gain", "loses", "lose",
    "cost", "costs", "lost", "add", "adds", "extra", "additional",
    "no", "any",
}
_QUANT_NUM_RE = re.compile(r"^[+\-−]?[\d.]+%?\$?$")


def filter_quant_context(
    candidates: list[audit.Candidate],
) -> list[audit.Candidate]:
    """Tier-2 single-word matches in description keys where the matched
    term is preceded by a number or quantity word ('300 authority',
    'costs authority', 'reduces morale'). The numeric/quantitative
    context disambiguates 'this is the game stat' from flavor."""
    canonical = _load_canonical_display_names()
    keep: list[audit.Candidate] = []
    for c in candidates:
        if not _is_description_key(c.loc_key):
            continue
        canon = canonical.get(c.cid)
        if canon is None or c.surface != canon:
            continue
        if c.matched_term.lower() != canon.lower():
            continue
        if " " in c.surface:
            continue
        if c.tier != 2:
            continue
        # Find the preceding token in the raw value.
        pat = re.compile(
            rf"(\S+)\s+{re.escape(c.matched_term)}\b", re.IGNORECASE
        )
        m = pat.search(c.raw_value)
        if m is None:
            continue
        prev = m.group(1).strip().rstrip(",.;:")
        if not (_QUANT_NUM_RE.match(prev) or prev.lower() in _QUANT_PRECEDING):
            continue
        # Skip when the line already contains a concept_<...> identifier
        # whose name embeds this concept-id as a substring — likely the
        # local context refers to that more-specific concept (e.g.
        # `concept_un_authority` shadowing a bare "authority" match).
        line = c.raw_value
        cid_tail = c.cid[len("concept_"):]
        embed_re = re.compile(r"concept_(?!" + re.escape(cid_tail) + r"\b)\w*" + re.escape(cid_tail) + r"\w*")
        if embed_re.search(line):
            continue
        # Same idea on the loc-key side: if the key namespace (e.g.
        # `je_un_preview_npt_tt`) suggests UN context but the cid is
        # bare `concept_authority`, the term likely means UN Authority
        # — skip.
        if cid_tail == "authority" and (
            "un_" in c.loc_key or c.loc_key.lower().startswith("un_")
        ):
            continue
        # Skip when the matched term is immediately followed by another
        # noun that forms a compound (e.g. "election interference",
        # "morale damage", "authority figure"). Heuristic: next token is
        # capitalized OR is a common compound suffix.
        compound_re = re.compile(
            rf"\b{re.escape(c.matched_term)}\s+(interference|damage|figure|rate|system|loss|losses)\b",
            re.IGNORECASE,
        )
        if compound_re.search(line):
            continue
        keep.append(c)
    return keep


def filter_other_labels_lax(
    candidates: list[audit.Candidate],
) -> list[audit.Candidate]:
    """Like `filter_other_labels` but allows case-insensitive matching.
    Multi-word surfaces are unconditional. Tier-1 single-word surfaces
    require the value to have multiple words (so the matched term isn't
    just the entire label, and there's prose around it)."""
    canonical = _load_canonical_display_names()
    keep: list[audit.Candidate] = []
    for c in candidates:
        if _is_description_key(c.loc_key) or _is_modifier_label_key(c.loc_key):
            continue
        canon = canonical.get(c.cid)
        if canon is None or c.surface != canon:
            continue
        if c.matched_term.lower() != canon.lower():
            continue
        if c.raw_value.strip().strip(".").lower() == canon.lower():
            continue
        if " " not in c.surface:
            # Single-word: only when the surrounding value is multi-word
            # AND the concept is Tier 1 (Tier 2 ambiguity gates it out).
            if c.tier != 1:
                continue
            words = c.raw_value.split()
            # 4+ words gives sentence-like context where the concept
            # term is most likely the game-mechanic meaning. Compound
            # noun titles (e.g. "Radical Mentors") usually fit in 2-3
            # words and are skipped.
            if len(words) < 4:
                continue
        keep.append(c)
    return keep


def filter_variants(
    candidates: list[audit.Candidate],
    *,
    allow_non_desc: bool = False,
) -> list[audit.Candidate]:
    """Plural / short / alias matches that need the Concept() form to
    preserve the original surface text.

    Example: "Radicals" plural matches `concept_radical` (singular display
    "Radical"); tagging as `[concept_radical]` would re-render as the
    singular. Instead emit `[Concept('concept_radical', 'Radicals')]`
    which keeps "Radicals" but provides the tooltip hyperlink.
    """
    canonical = _load_canonical_display_names()
    keep: list[audit.Candidate] = []
    for c in candidates:
        if not allow_non_desc and not _is_description_key(c.loc_key):
            continue
        canon = canonical.get(c.cid)
        if canon is None:
            continue
        if c.surface == canon:
            continue
        if c.matched_term.lower() != c.surface.lower():
            continue
        if c.tier == 2 and " " not in c.surface:
            continue
        # Skip bare-label cases.
        if c.raw_value.strip().strip(".").lower() == c.surface.lower():
            continue
        # In non-desc keys, only allow multi-word variants UNLESS the
        # value has 4+ words (sentence-like context, low compound risk
        # — same heuristic as filter_other_labels_lax).
        if allow_non_desc and not _is_description_key(c.loc_key):
            if " " not in c.surface:
                if c.tier != 1:
                    continue
                if len(c.raw_value.split()) < 4:
                    continue
        keep.append(c)
    return keep


def apply_edits(
    candidates: list[audit.Candidate],
    *,
    use_concept_form: bool = False,
) -> dict:
    """Replace the first untagged occurrence of each surface form per
    (file, line, concept). Returns summary counts.

    use_concept_form: emit `[Concept('concept_X', 'matched_text')]` so the
    original surface form is preserved on render. Defaults to the simple
    `[concept_X]` form (which renders the canonical display).
    """
    # Group: file → line → [(surface, cid)]
    grouped: dict[str, dict[int, list[tuple[str, str]]]] = {}
    for c in candidates:
        grouped.setdefault(c.file, {}).setdefault(c.line, []).append((c.surface, c.cid))

    files_touched = 0
    lines_edited = 0
    edits_applied = 0
    edits_skipped = 0

    for rel_file, line_map in sorted(grouped.items()):
        abs_file = Path(mod_path) / rel_file
        try:
            raw_bytes = abs_file.read_bytes()
        except OSError:
            continue
        # Preserve BOM if present — Vic3 loc loader expects utf-8-sig.
        had_bom = raw_bytes.startswith(b"\xef\xbb\xbf")
        text = raw_bytes.decode("utf-8-sig", errors="replace")
        lines = text.splitlines(keepends=True)
        changed = False

        # Sort surface forms longest-first per line so "Power Bloc Member"
        # is replaced before "Power Bloc".
        for line_no, items in sorted(line_map.items()):
            if line_no - 1 >= len(lines):
                continue
            line = lines[line_no - 1]
            items_sorted = sorted(items, key=lambda x: -len(x[0]))
            for surface, cid in items_sorted:
                # Skip if the line has already been tagged with this concept
                # (could happen if the term appears twice, the first was
                # already tagged in vanilla style by a previous run, or a
                # human already tagged it).
                if f"[{cid}]" in line or f"'{cid}'" in line:
                    edits_skipped += 1
                    continue
                # Word-boundary replacement, case-preserving via match.
                pat = re.compile(rf"\b{re.escape(surface)}\b", re.IGNORECASE)
                if use_concept_form:
                    # Preserve the matched text via a callback so the
                    # original case/inflection survives.
                    def _replace(m: re.Match, _cid: str = cid) -> str:
                        return f"[Concept('{_cid}', '{m.group(0)}')]"
                    new_line, n = pat.subn(_replace, line, count=1)
                else:
                    new_line, n = pat.subn(f"[{cid}]", line, count=1)
                if n == 0:
                    edits_skipped += 1
                    continue
                lines[line_no - 1] = new_line
                line = new_line
                edits_applied += 1
                changed = True

        if changed:
            files_touched += 1
            lines_edited_in_file = sum(
                1 for ln, orig in zip(lines, text.splitlines(keepends=True)) if ln != orig
            )
            lines_edited += lines_edited_in_file
            new_text = "".join(lines)
            new_bytes = new_text.encode("utf-8")
            if had_bom:
                new_bytes = b"\xef\xbb\xbf" + new_bytes
            abs_file.write_bytes(new_bytes)

    return {
        "files_touched": files_touched,
        "lines_edited": lines_edited,
        "edits_applied": edits_applied,
        "edits_skipped": edits_skipped,
    }


def main() -> int:
    registered = audit.load_registered_concepts()
    display = audit.load_concept_display_names(registered)
    tiers = [audit.classify(cid, names) for cid, names in display.items()]
    candidates = audit.scan(tiers)
    print(f"total candidates: {len(candidates)}")

    include_labels = "--include-labels" in sys.argv
    case_variant = "--case-variant" in sys.argv
    variants = "--variants" in sys.argv
    other_labels = "--other-labels" in sys.argv
    use_concept_form = variants
    if "--quant-context" in sys.argv:
        keep = filter_quant_context(candidates)
        label = "Tier-2 single-word in quantitative context (desc keys)"
    elif variants:
        keep = filter_variants(candidates, allow_non_desc=other_labels)
        label = "variant matches (Concept() form)"
        if other_labels:
            label += " incl. non-desc"
    elif other_labels:
        if case_variant:
            keep = [c for c in filter_other_labels_lax(candidates)]
            label = "non-desc entity names/titles (multi-word, case-variant)"
        else:
            keep = filter_other_labels(candidates)
            label = "non-desc entity names/titles (canonical match)"
    elif include_labels and case_variant:
        keep = filter_with_labels_and_case(candidates)
        label = "high-conf + modifier labels + case-variant"
    elif include_labels:
        keep = filter_with_modifier_labels(candidates)
        label = "high-conf incl. modifier labels"
    elif case_variant:
        keep = filter_with_case_variants(candidates)
        label = "high-conf + case-variant"
    else:
        keep = filter_high_confidence(candidates)
        label = "high-confidence (description keys)"
    print(f"{label}: {len(keep)}")

    if "--dry-run" in sys.argv:
        for c in keep[:50]:
            if use_concept_form:
                print(f"  {c.file}:{c.line} `{c.loc_key}` — {c.matched_term!r} → [Concept('{c.cid}', '{c.matched_term}')]")
            else:
                print(f"  {c.file}:{c.line} `{c.loc_key}` — {c.surface} → [{c.cid}]")
        print("... (dry-run; no edits applied)")
        return 0

    summary = apply_edits(keep, use_concept_form=use_concept_form)
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
