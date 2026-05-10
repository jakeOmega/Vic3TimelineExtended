"""One-shot scanner: find plain-text mentions of vanilla/mod concept display
names in mod localization that are not yet tagged with `[concept_X]` /
`[Concept('concept_X', '...')]` references.

Inverse of `concept_reference_audit.py` (which flags brackets pointing at
unregistered concepts). This one flags untagged mentions where adding a
bracket would link the term to its in-game tooltip.

Output: a candidate list under `docs/audits/concept_term_candidates.md`,
grouped by concept, listing each `(file, line, loc_key, surface_term,
tier)`. Human reviews and decides whether each match should be tagged.

Tier model:
  Tier 1 — always-on. Multi-word display names and curated single-word
           jargon whose plain-English use is essentially absent.
  Tier 2 — non-event files only. Single-word concepts whose name overlaps
           everyday English; in mechanical contexts (laws, JE, tech, misc,
           concept descriptions) they almost always mean the game stat,
           but in event flavor they're usually narrative.
  Tier 3 — excluded entirely. Single-word concepts whose name is so
           common in English that even mechanical-context tagging would
           produce more false positives than true positives.

The tier sets are CURATED EMPIRICALLY by walking vanilla concept display
names. They start small; expand by reviewing the `_uncategorized.md`
sidecar that this script produces, then editing the sets and re-running.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from path_constants import base_game_path, mod_path  # noqa: E402


# ---------------------------------------------------------------------------
# Tier curation
# ---------------------------------------------------------------------------

# Concept ids whose single-word display name is unambiguous Vic3 jargon.
# These get scanned everywhere (Tier 1).
#
# Curated empirically by walking vanilla `concepts_l_english.yml` + mod
# `te_concepts_l_english.yml`. Bias toward inclusion when the word is rare
# in everyday English (Infamy, Bureaucracy, Pronunciamento), Vic3-specific
# jargon (Pop, HQ, Throughput), or named after a mechanic with no common
# narrative use of the bare noun (Decree, Institution, Vassal).
TIER1_SINGLE_WORD: set[str] = {
    # already-confirmed core
    "concept_infamy",
    "concept_prestige",
    "concept_legitimacy",
    "concept_bureaucracy",
    "concept_devastation",
    "concept_turmoil",
    "concept_obstinance",
    "concept_discrimination",
    "concept_radical",
    "concept_loyalist",
    # added from uncategorized walk-through
    "concept_agitator",
    "concept_amenability",
    "concept_amendment",
    "concept_political_lobby_appeasement",
    "concept_assimilation",
    "concept_attrition",
    "concept_battalion",
    "concept_blockade",
    "concept_bolster",
    "concept_clout",
    "concept_power_bloc_cohesion",
    "concept_contravention",
    "concept_coup",
    "concept_decolonization_system",
    "concept_decree",
    "concept_morale_demoralized",
    "concept_dependents",
    "concept_disenfranchised",
    "concept_dividends",
    "concept_dominion",
    "concept_embargo",
    "concept_fervor",
    "concept_fortification_system",
    "concept_gdp",
    "concept_heir",
    "concept_homeland",
    "concept_hq",
    "concept_humiliation",
    "concept_infrastructure",
    "concept_ch_instability",
    "concept_institution",
    "concept_insurrection",
    "concept_jobseeker",
    "concept_literacy",
    "concept_magnate",
    "concept_marginalized",
    "concept_ch_megaprojects",
    "concept_budget_minting",
    "concept_obligation",
    "concept_obsession",
    "concept_occupancy",
    "concept_overlord",
    "concept_pollution_system",
    "concept_pop",
    "concept_power_bloc_principle",
    "concept_privatize",
    "concept_profession",
    "concept_prominence",
    "concept_pronunciamento",
    "concept_protectorate",
    "concept_puppet",
    "concept_pop_qualifications",
    "concept_screening",
    "concept_secession",
    "concept_strait",
    "concept_subventions",
    "concept_throughput",
    "concept_tolls",
    "concept_tourism_system",
    "concept_tributary",
    "concept_un_veto",
    "concept_vassal",
    "concept_workforce",
    "concept_zaibatsu",
}

# Concept ids whose single-word display name overlaps everyday English but
# is reliably mechanical in non-event mod loc. Skipped inside event files.
TIER2_CONTEXT_GATED: set[str] = {
    "concept_authority",
    "concept_innovation",
    "concept_acceptance",
    "concept_admiral",
    "concept_alliance",
    "concept_approval",
    "concept_autonomy",
    "concept_canal",
    "concept_claim",
    "concept_colony",
    "concept_colony_subject",
    "concept_commander",
    "concept_conversion",
    "concept_election",
    "concept_famine",
    "concept_flagship",
    "concept_fleet",
    "concept_front",
    "concept_manpower",
    "concept_market",
    "concept_migration",
    "concept_monopoly",
    "concept_morale",
    "concept_rank",
    "concept_shortage",
    "concept_starvation",
    "concept_tariffs",
    "concept_treaty",
    "concept_modifier",
}

# Concept ids whose single-word display name is too common in English to
# tag safely even in mechanical contexts. Never produce candidates.
# (Listed mainly to document the explicit rejection — the default is also
# Tier 3, so omitting an id has the same effect.)
TIER3_EXCLUDED: set[str] = {
    "concept_presence",
    "concept_order",
    "concept_religion",
    "concept_law",
    "concept_war",
    "concept_party",
    "concept_leader",
    "concept_influence",
    "concept_sway",
    "concept_production",
    "concept_good_production",
    "concept_movement",
    "concept_ideology",
    "concept_liberty",
    "concept_equality",
    "concept_tradition",
    # "holding" appears overwhelmingly as a verb ("holding steady", "holding
    # a photograph") or as a financial-asset noun ("dump every holding they
    # own"). The Vic3 Holding mechanic is rare in flow text — tagging produced
    # 5 false positives, 0 true positives.
    "concept_holding",
    # `concept_detection` is the SHIP COMBAT detection (fleet visibility);
    # `concept_operation_detection` is the mod's covert-warfare detection.
    # The bare word "detection" overwhelmingly appears in covert-warfare
    # contexts in this mod (operation_detection chance, counterintelligence
    # detection, etc.) where the ship-combat tag would mislead. Sensor /
    # radar / sonar contexts that DO want the ship concept must be tagged
    # by hand. 14 false positives, 7 (radar/sonar) correct hand-tags.
    "concept_detection",
    # "institution" / "institutions" is the worst false-positive vector
    # in this mod's prose: it appears constantly as generic English
    # (financial institutions = banks; religious institutions = churches;
    # the family-as-an-institution; the UN-as-an-institution; civic
    # institutions in propaganda/colonial-development contexts). The Vic3
    # `concept_institution` mechanic IS valid when paired with a specific
    # Vic3 institution name (Ministry of X) — those existing hand-tags
    # stay. Auto-tagging the bare word produced 17 false positives, so
    # block future auto-runs and require manual judgment.
    "concept_institution",
}

# File-name suffix → file kind (used by Tier 2 gating).
EVENT_LOC_RE = re.compile(r"_events_l_english\.yml$")

# Loc files known to be auto-generated. `te_power_bloc_unlocks_l_english.yml`
# is fully regenerated each /reload by `gen_pb_principle_unlock_descs.py`,
# so hand-edits would be overwritten — skip. `te_buildings_l_english.yml`
# is technically a sink for `gen_vanilla_company_buildings.py`, but that
# script only APPENDS new `building_<company>:0` keys and never rewrites
# existing throughput / description keys, so hand-edits to those survive
# (organize_loc.py preserves values verbatim). Don't skip it here.
AUTO_GEN_LOC_BASENAMES = {
    "te_power_bloc_unlocks_l_english.yml",
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

# Reuse the loc-line parser idiom from concept_reference_audit.py.
def _parse_loc_line(raw: str) -> tuple[str, str, str] | None:
    line = raw.rstrip("\n")
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#") or ":" not in stripped:
        return None
    key, rest = line.split(":", 1)
    key = key.strip()
    if not key:
        return None
    quote_locations = [i for i, c in enumerate(rest) if c == '"']
    if len(quote_locations) < 2:
        return None
    value = rest[quote_locations[0] + 1: quote_locations[1]]
    trailing = rest[quote_locations[1] + 1:]
    return key, value, trailing


# `concept_X = { ... }` or `concept_X = {}` at the top level of a Paradox
# concept file. We don't need to fully parse — the engine treats every
# top-level identifier as the concept id.
_CONCEPT_DEF_RE = re.compile(r"^\s*(concept_[A-Za-z0-9_]+)\s*=\s*\{")


def load_registered_concepts() -> set[str]:
    """All concept ids declared in vanilla + mod `common/game_concepts/`."""
    ids: set[str] = set()
    dirs = [
        Path(base_game_path) / "game" / "common" / "game_concepts",
        Path(mod_path) / "common" / "game_concepts",
    ]
    for d in dirs:
        if not d.is_dir():
            continue
        for fp in sorted(d.glob("*.txt")):
            try:
                text = fp.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                m = _CONCEPT_DEF_RE.match(line)
                if m:
                    ids.add(m.group(1))
    return ids


# Loc lines look like ` concept_x:0 "Display Name"` or ` concept_x: "..."`.
_LOC_KEY_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)(?::\d+)?\s")


def _read_loc_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            for raw in fh:
                parsed = _parse_loc_line(raw)
                if parsed is None:
                    continue
                key, value, _ = parsed
                # `concept_great_powers:1` — strip the version suffix from key.
                # Already handled by _parse_loc_line: it splits on `:` first.
                # But keys appear as `concept_great_powers` with the `:1`
                # consumed as part of the version separator.
                out[key] = value
    except OSError:
        pass
    return out


def load_concept_display_names(registered: set[str]) -> dict[str, list[str]]:
    """Returns concept_id → list of display strings (display, _short, _plural).

    Only includes display strings for concept ids that are registered, so
    we don't suggest tagging with brackets the engine would reject.
    """
    loc: dict[str, str] = {}
    loc_files = [
        Path(base_game_path) / "game" / "localization" / "english" / "concepts_l_english.yml",
        Path(mod_path) / "localization" / "english" / "te_concepts_l_english.yml",
    ]
    for fp in loc_files:
        if fp.is_file():
            for k, v in _read_loc_file(fp).items():
                loc[k] = v

    out: dict[str, list[str]] = {}
    for cid in registered:
        names: list[str] = []
        seen: set[str] = set()
        for variant in (cid, f"{cid}_short", f"{cid}_plural", f"{cid}s"):
            v = loc.get(variant)
            if not v:
                continue
            # Skip values that are pure substitution placeholders like "$bankroll$"
            # or rich `[Get...]` expressions — those don't correspond to a literal
            # surface form we'd grep for in mod loc.
            if v.startswith("$") and v.endswith("$") and v.count("$") == 2:
                continue
            if "[" in v or "$" in v:
                continue
            v_clean = v.strip()
            if not v_clean:
                continue
            if v_clean.lower() in seen:
                continue
            seen.add(v_clean.lower())
            names.append(v_clean)
        if names:
            out[cid] = names
    return out


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------

@dataclass
class SurfaceForm:
    cid: str
    surface: str
    tier: int  # 1, 2, or 3 (3 == excluded)
    reason: str


@dataclass
class ConceptTier:
    cid: str
    canonical: str
    surface_forms: list[str]   # all known display variants
    forms: list[SurfaceForm]   # per-surface tiers
    tier: int  # min tier across forms (3 if all forms excluded) — used in summaries
    reason: str  # tier reason for canonical surface


def _surface_tier(cid: str, surface: str) -> tuple[int, str]:
    word_count = len(surface.split())
    if word_count >= 2:
        return 1, "multi-word surface form"
    # Single-word: gate by concept-id curation.
    if cid in TIER3_EXCLUDED:
        return 3, "Tier 3 concept (everyday-English single word)"
    if cid in TIER2_CONTEXT_GATED:
        return 2, "Tier 2 concept (skip event files)"
    if cid in TIER1_SINGLE_WORD:
        return 1, "Tier 1 single-word jargon"
    return 3, "uncurated single-word (default exclude)"


def classify(cid: str, names: list[str]) -> ConceptTier:
    canonical = names[0]
    forms: list[SurfaceForm] = []
    for surface in names:
        tier, reason = _surface_tier(cid, surface)
        forms.append(SurfaceForm(cid, surface, tier, reason))
    canonical_form = forms[0]
    min_tier = min((f.tier for f in forms), default=3)
    return ConceptTier(
        cid=cid,
        canonical=canonical,
        surface_forms=names,
        forms=forms,
        tier=min_tier,
        reason=canonical_form.reason,
    )


# ---------------------------------------------------------------------------
# Mod loc scan
# ---------------------------------------------------------------------------

# Strip already-tagged spans so we don't re-flag them.
_TAGGED_SPAN_RE = re.compile(
    r"\[concept_[A-Za-z0-9_]+\]"
    r"|\[Concept\(\s*['\"]concept_[A-Za-z0-9_]+['\"][^]]*\]"
)
# Strip `$concept_X$` interpolations — those *are* tagged (rendered by the
# engine, link-styled when rendered in tooltip context).
_INTERP_RE = re.compile(r"\$concept_[A-Za-z0-9_]+\$")
# Strip `[Get...]` and similar bracket expressions that aren't concept refs;
# these are unrelated and we don't want to match terms inside them.
_BRACKET_EXPR_RE = re.compile(r"\[(?!concept_|Concept\()[^\]]*\]")
# Strip `#bold ... #!` formatting bounds (terms inside formatted spans
# are still real text — keep them — just remove the `#bold`/`#!` markers).
_FMT_OPEN_RE = re.compile(r"#\w+\s*")
_FMT_CLOSE_RE = re.compile(r"#!")


def _scrub(value: str) -> str:
    """Replace already-tagged spans with placeholders so word-boundary
    matching doesn't trip on text inside them. Returns the same length so
    column offsets are preserved (we don't actually use offsets, but it's
    cheap insurance)."""
    def blank(m: re.Match) -> str:
        return " " * (m.end() - m.start())

    v = _TAGGED_SPAN_RE.sub(blank, value)
    v = _INTERP_RE.sub(blank, v)
    v = _BRACKET_EXPR_RE.sub(blank, v)
    v = _FMT_OPEN_RE.sub(blank, v)
    v = _FMT_CLOSE_RE.sub(blank, v)
    return v


@dataclass
class Candidate:
    file: str
    line: int
    loc_key: str
    cid: str
    surface: str
    matched_term: str
    tier: int
    raw_value: str  # full unscrubbed loc value for context


def _build_term_index(tiers: list[ConceptTier]) -> list[tuple[re.Pattern[str], str, str, int]]:
    """Compile word-boundary patterns per active surface form.

    Returns list of (regex, surface_form, concept_id, tier) — tier is the
    surface-form tier, NOT the concept's min tier. Surfaces in Tier 3 are
    skipped entirely.
    """
    entries: list[tuple[re.Pattern[str], str, str, int]] = []
    for t in tiers:
        for f in t.forms:
            if f.tier == 3:
                continue
            esc = re.escape(f.surface)
            pat = re.compile(rf"\b{esc}\b", re.IGNORECASE)
            entries.append((pat, f.surface, f.cid, f.tier))
    entries.sort(key=lambda e: -len(e[1]))
    return entries


def _is_canonical_loc_key(key: str, cid: str) -> bool:
    """A loc line that defines the concept's surface form rather than uses
    it. Tagging these is circular ("[concept_X]" inside "concept_X:0")."""
    if key == cid:
        return True
    for suffix in ("_short", "_plural", "s", "_possessive"):
        if key == cid + suffix:
            return True
    return False


def scan(
    tiers: list[ConceptTier],
    *,
    skip_auto_gen: bool = True,
) -> list[Candidate]:
    loc_root = Path(mod_path) / "localization"
    if not loc_root.is_dir():
        return []

    term_index = _build_term_index(tiers)
    candidates: list[Candidate] = []

    for root, _dirs, files in os.walk(loc_root):
        for fname in sorted(files):
            if not fname.endswith(".yml"):
                continue
            if skip_auto_gen and fname in AUTO_GEN_LOC_BASENAMES:
                continue
            abs_p = Path(root) / fname
            rel_p = str(abs_p.relative_to(mod_path))
            is_event_file = bool(EVENT_LOC_RE.search(fname))

            try:
                with open(abs_p, encoding="utf-8-sig", errors="replace") as fh:
                    for i, raw in enumerate(fh, start=1):
                        parsed = _parse_loc_line(raw)
                        if parsed is None:
                            continue
                        key, value, _ = parsed
                        scrubbed = _scrub(value)
                        if not scrubbed.strip():
                            continue
                        # Track spans we've already matched on this line so
                        # we don't double-flag overlapping surface forms
                        # ("Power Bloc Member" + "Power Bloc").
                        consumed: list[tuple[int, int]] = []
                        for pat, surface, cid, tier in term_index:
                            if tier == 2 and is_event_file:
                                continue
                            # Skip the concept's own definition lines —
                            # tagging there is circular.
                            if _is_canonical_loc_key(key, cid):
                                continue
                            for m in pat.finditer(scrubbed):
                                s, e = m.span()
                                # Skip if overlapping a previously consumed span.
                                if any(not (e <= cs or s >= ce) for cs, ce in consumed):
                                    continue
                                # Skip when the value (stripped of formatting)
                                # is exactly the surface form — pure label, no
                                # descriptive context to embed a hyperlink in.
                                stripped_value = value.strip().strip(".")
                                if stripped_value.lower() == surface.lower():
                                    continue
                                consumed.append((s, e))
                                candidates.append(Candidate(
                                    file=rel_p,
                                    line=i,
                                    loc_key=key,
                                    cid=cid,
                                    surface=surface,
                                    matched_term=value[s:e],
                                    tier=tier,
                                    raw_value=value,
                                ))
            except OSError:
                continue
    return candidates


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def render_uncategorized(tiers: list[ConceptTier]) -> str:
    """List of concepts whose single-word surface forms fell into Tier 3
    by default. Reviewer promotes any that should be Tier 1 or Tier 2 by
    adding the cid to the corresponding set at the top of this file.

    A concept is shown if it has at least one single-word surface form
    that defaulted to Tier 3 (uncurated). Multi-word forms on the same
    concept are still being scanned at Tier 1.
    """
    rows: list[ConceptTier] = []
    for t in tiers:
        has_uncurated_single = any(
            f.tier == 3 and f.reason == "uncurated single-word (default exclude)"
            for f in t.forms
        )
        if has_uncurated_single:
            rows.append(t)
    rows.sort(key=lambda t: t.canonical.lower())
    out = [
        "# Uncategorized single-word concept surface forms",
        "",
        "These concept ids have at least one single-word surface form (the",
        "canonical display, a `_short` variant, etc.) that defaulted to",
        "Tier 3. Multi-word forms on the same concept are still scanned at",
        "Tier 1, but the single-word form is currently skipped.",
        "",
        "Promote a concept's single-word form to Tier 1 (scan everywhere)",
        "or Tier 2 (skip event files) by adding its `concept_X` id to the",
        "corresponding set at the top of `concept_term_audit.py`.",
        "",
        f"Count: {len(rows)}",
        "",
        "| Concept id | Canonical | Single-word forms (uncurated) |",
        "|---|---|---|",
    ]
    for t in rows:
        single_word = [
            f.surface for f in t.forms
            if f.tier == 3 and f.reason == "uncurated single-word (default exclude)"
        ]
        out.append(f"| `{t.cid}` | {t.canonical} | {' · '.join(single_word)} |")
    out.append("")
    return "\n".join(out) + "\n"


def render_report(
    candidates: list[Candidate],
    tiers: list[ConceptTier],
) -> str:
    by_concept: dict[str, list[Candidate]] = {}
    for c in candidates:
        by_concept.setdefault(c.cid, []).append(c)

    surface_tier_count = {1: 0, 2: 0, 3: 0}
    for t in tiers:
        for f in t.forms:
            surface_tier_count[f.tier] += 1

    out = [
        "# Concept term audit candidates",
        "",
        "Generated by `scripts/analysis/concept_term_audit.py`. One-shot —",
        "not wired into POST_LOAD_GENERATORS. Re-run after curating tiers.",
        "",
        "Each entry is a plain-text mention of a concept display name in",
        "mod localization that is **not** wrapped in `[concept_X]` or",
        "`[Concept('concept_X', ...)]`. Review per-line and tag where the",
        "term unambiguously refers to the game mechanic; leave flavor",
        "untagged.",
        "",
        "## Summary",
        "",
        f"- Concepts (registered, vanilla+mod): {sum(1 for _ in tiers)}",
        f"- Surface forms scanned: {surface_tier_count[1] + surface_tier_count[2]}",
        f"  - Tier 1 (scan everywhere): {surface_tier_count[1]}",
        f"  - Tier 2 (skip event files): {surface_tier_count[2]}",
        f"  - Tier 3 (excluded): {surface_tier_count[3]}",
        f"- Total candidates: {len(candidates)}",
        f"- Concepts with at least one candidate: {len(by_concept)}",
        "",
        "## Candidates by concept",
        "",
    ]

    if not by_concept:
        out.append("_None._")
        out.append("")
        return "\n".join(out) + "\n"

    for cid in sorted(by_concept.keys()):
        rows = by_concept[cid]
        first = rows[0]
        out.append(f"### `{cid}` ({len(rows)}) — {first.surface} [Tier {first.tier}]")
        out.append("")
        # Group by file so the reviewer can sweep one file at a time.
        by_file: dict[str, list[Candidate]] = {}
        for r in rows:
            by_file.setdefault(r.file, []).append(r)
        for fname in sorted(by_file.keys()):
            out.append(f"**`{fname}`**")
            out.append("")
            for r in by_file[fname]:
                # Truncate long values for readability.
                v = r.raw_value
                if len(v) > 240:
                    v = v[:240] + "…"
                out.append(f"- L{r.line} `{r.loc_key}` (matched `{r.matched_term}`)")
                out.append(f"  > {v}")
            out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    registered = load_registered_concepts()
    display = load_concept_display_names(registered)

    tiers = [
        classify(cid, names)
        for cid, names in display.items()
    ]

    print(f"registered concepts: {len(registered)}")
    print(f"with display names: {len(display)}")
    print(f"  Tier 1: {sum(1 for t in tiers if t.tier == 1)}")
    print(f"  Tier 2: {sum(1 for t in tiers if t.tier == 2)}")
    print(f"  Tier 3: {sum(1 for t in tiers if t.tier == 3)}")

    candidates = scan(tiers)
    print(f"candidates found: {len(candidates)}")

    out_dir = Path(mod_path) / "docs" / "audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "concept_term_candidates.md").write_text(
        render_report(candidates, tiers), encoding="utf-8"
    )
    (out_dir / "concept_term_uncategorized.md").write_text(
        render_uncategorized(tiers), encoding="utf-8"
    )
    print(f"wrote {out_dir/'concept_term_candidates.md'}")
    print(f"wrote {out_dir/'concept_term_uncategorized.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
