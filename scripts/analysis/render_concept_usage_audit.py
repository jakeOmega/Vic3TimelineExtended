"""Render docs/audits/concept_usage_audit.md from the concept-usage inventory.

Reads scripts/analysis/concept_usage_inventory.json (produced by
concept_usage_inventory.py), applies the hand-curated semantic verdicts below,
and writes the full audit table. One-shot companion to that inventory; not
wired into POST /reload.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

# --- Ambiguity watchlist -------------------------------------------------
# concept -> (Vic3 meaning, non-Vic3 sense it can be confused with).
# These are the concepts whose display name is a common English word; every
# instance of one was read. Concepts NOT listed here have a Vic3-specific name
# (concept_gdp, concept_bureaucracy, …) and are valid-by-construction.
WATCHLIST = {
    "concept_screening": ("Naval ship-screening (counters ship vulnerability)",
                          "medical/genetic/psychological/personnel screening"),
    "concept_bolster": ("The Bolster action on a political movement",
                        "the plain verb 'to bolster' (strengthen)"),
    "concept_fervor": ("Cultural national-spirit stat (drives assimilation)",
                       "emotional intensity: religious/patriotic/speculative fervor"),
    "concept_dominion": ("Subject type (autonomous vassal)",
                         "'dominion' as realm/domain"),
    "concept_radical": ("A Radical (a dissatisfied/radicalized pop)",
                        "the adjective 'radical' (extreme/revolutionary)"),
    "concept_obligation": ("A diplomatic favor owed (from diplo plays/buyouts)",
                           "treaty/legal/debt 'obligations' generally"),
    "concept_prominence": ("A character's political prominence stat",
                           "'rise to prominence' (general fame)"),
    "concept_state": ("An administrative State region", "nation/condition/government"),
    "concept_market": ("The economic Market", "labour/stock/flea market"),
    "concept_law": ("An enacted government Law", "law of nature / rule of law"),
    "concept_authority": ("The Authority resource", "governmental authority / an expert"),
    "concept_subject": ("A diplomatic Subject (vassal)", "topic / person / 'subject to'"),
    "concept_unit": ("A military Unit", "unit of measure/account"),
    "concept_influence": ("The diplomatic Influence resource", "general influence"),
    "concept_pop": ("A population group (Pop)", "pop culture / pop-up"),
    "concept_company": ("A chartered Company", "military company / companionship"),
    "concept_building": ("An economic Building", "the gerund 'building'"),
    "concept_institution": ("A government Institution", "educational/financial institution"),
    "concept_culture": ("A Culture group", "the arts / corporate culture"),
    "concept_innovation": ("The Innovation (research) resource", "general innovation"),
    "concept_conversion": ("Religious Conversion of pops", "unit/building conversion"),
    "concept_defense": ("Unit combat Defense stat", "legal/self/civil defense"),
    "concept_offense": ("Unit combat Offense stat", "taking offense / criminal offense"),
    "concept_clout": ("An interest group's Clout", "general clout"),
    "concept_escalation": ("Diplomatic-play Escalation", "general escalation"),
    "concept_detection": ("Covert-op/naval Detection", "general detection"),
    "concept_construction": ("The Construction system", "general construction"),
    "concept_amendment": ("An Amendment to a law", "constitutional amendment"),
    "concept_loyalist": ("A Loyalist pop", "political loyalist generally"),
    "concept_profession": ("A pop Profession", "general profession"),
    "concept_occupancy": ("How fully a building is staffed", "military occupation / tenancy"),
    "concept_acceptance": ("Cultural Acceptance", "general acceptance"),
    "concept_heir": ("The dynastic Heir", "metaphorical heir/legacy"),
    "concept_country": ("A Country", "countryside"),
    "concept_homeland": ("A culture's Homeland state", "homeland generally"),
    "concept_turmoil": ("State Turmoil", "emotional turmoil"),
}

# --- Verdicts for individual flagged instances ---------------------------
# (concept, basename, line) -> (verdict, loc_key, note). Keyed by concept too,
# because a single loc line can reference several concepts and a verdict must
# not leak to co-located ones. Watchlist-concept instances not listed are
# "valid" (read and judged correct); non-watchlist concepts are "valid
# (unambiguous)". The MISUSE entries were FIXED in this pass (the concept
# reference was replaced with plain text), so they no longer appear in the live
# inventory — they are recorded here as the authoritative audit finding.
MISUSE = {
    ("concept_screening", "te_laws_l_english.yml", 234): ("misuse", "law_state_eugenics_program_desc", "'genetic screening' → linked naval ship-screening"),
    ("concept_screening", "te_events_l_english.yml", 3436): ("misuse", "space_race_events.48.a", "'psychological screening' → linked naval ship-screening"),
    ("concept_screening", "te_concepts_l_english.yml", 2141): ("misuse", "trait_combined_arms_infantry_screen_desc", "infantry 'screening' → concept is naval-ship-specific"),
    ("concept_bolster", "te_concepts_l_english.yml", 423): ("misuse", "ch_foreign_influence_crackdown_desc", "verb 'bolsters' → Bolster is a political-movement action"),
    ("concept_bolster", "te_concepts_l_english.yml", 653): ("misuse", "concept_operation_detection_desc", "'bolster defenses' (verb) → Bolster political-movement action"),
    ("concept_bolster", "te_concepts_l_english.yml", 1293): ("misuse", "me_security_crackdown_modifier_desc", "verb 'bolster' → Bolster political-movement action"),
    ("concept_bolster", "te_concepts_l_english.yml", 1619): ("misuse", "re_cyber_forensics_desc", "verb 'bolsters' → Bolster political-movement action"),
    ("concept_dominion", "te_religion_l_english.yml", 203): ("misuse", "custom_religion_name_p", "'Dominion' as realm → concept is the subject-type Dominion"),
    ("concept_fervor", "te_concepts_l_english.yml", 225): ("misuse", "amendment_langreform_revival_desc", "'religious fervor' → Fervor is the cultural national-spirit stat"),
    ("concept_fervor", "te_concepts_l_english.yml", 1203): ("misuse", "langreform_revival_desc", "'religious fervor' → Fervor is the cultural national-spirit stat"),
    ("concept_fervor", "te_events_l_english.yml", 96): ("misuse", "banking_cycle_events.1.d", "'speculative fervor' (markets) → cultural Fervor stat"),
    ("concept_fervor", "te_events_l_english.yml", 738): ("misuse", "decolonization_events.19.d", "'nationalist fervor' → cultural Fervor stat"),
    ("concept_fervor", "te_events_l_english.yml", 3827): ("misuse", "un_events.13.d_vs_council", "'equal fervor' → cultural Fervor stat"),
    ("concept_fervor", "te_events_l_english.yml", 4201): ("misuse", "world_war_events.10.d", "'patriotic fervor' → cultural Fervor stat"),
    ("concept_radical", "te_events_l_english.yml", 1064): ("misuse", "extra_law_events.22.d", "'radical action' (adj) → Radical is a pop type"),
    ("concept_radical", "te_events_l_english.yml", 1104): ("misuse", "extra_law_events.25.d_east_asian", "'more radical' (adj) → Radical is a pop type"),
    ("concept_radical", "te_events_l_english.yml", 1116): ("misuse", "extra_law_events.25.d_slavic", "'more radical path' (adj) → Radical is a pop type"),
    ("concept_radical", "te_events_l_english.yml", 2204): ("misuse", "modern_election_events.33.d", "'radical proposal' (adj) → Radical is a pop type"),
    ("concept_radical", "te_events_l_english.yml", 2563): ("misuse", "post_scarcity_events.4.d", "'radical anti-technology movement' (adj) → Radical is a pop type"),
    ("concept_radical", "te_events_l_english.yml", 2602): ("misuse", "religious_revival_events.3.d_dharmic", "'radical egalitarianism' (adj) → Radical is a pop type"),
    ("concept_radical", "te_concepts_l_english.yml", 525): ("misuse", "colonial_empire_crumbling_modifier_desc", "'radical movements' (adj) → Radical is a pop type"),
    ("concept_radical", "te_concepts_l_english.yml", 1603): ("misuse", "radical_law_backlash_desc", "'radical law' (adj) → Radical is a pop type"),
    ("concept_radical", "te_concepts_l_english.yml", 1605): ("misuse", "radical_law_retreat_desc", "'radical law' (adj) → Radical is a pop type"),
    ("concept_radical", "te_unused_l_english.yml", 261): ("misuse", "environmental_events.3.d", "'radical environmentalist cell' (adj) → Radical is a pop type [unused file]"),
}
BORDERLINE = {
    ("concept_radical", "te_events_l_english.yml", 2341): ("borderline", "movement_events_te.223.d", "'radical organizers' — could read as radical-pop organizers"),
    ("concept_radical", "te_miscellaneous_l_english.yml", 357): ("borderline", "HE_DISABLE_RADICAL_DESC", "heir 'Radical' IG-focus label — topically tied to the Radical pop"),
    ("concept_radical", "te_miscellaneous_l_english.yml", 358): ("borderline", "HE_DISABLE_RADICAL_EFFECT_TT", "heir 'Radical' IG-focus label"),
    ("concept_radical", "te_miscellaneous_l_english.yml", 377): ("borderline", "HE_ENABLE_RADICAL_EFFECT_TT", "heir 'Radical' IG-focus label"),
    ("concept_prominence", "te_events_l_english.yml", 1099): ("borderline", "extra_law_events.25.d_aramaic", "'rose to prominence' — flavor; concept is the character prominence stat"),
    ("concept_prominence", "te_events_l_english.yml", 2120): ("borderline", "modern_election_events.20.d", "'risen to prominence' — flavor; concept is the character prominence stat"),
}
# concept_obligation is used broadly for treaty/debt/legal 'obligations'; the
# concept is specifically a diplomatic favor owed. Topical near-miss, low-stakes
# — flagged as borderline at the concept level, not fixed.
BORDERLINE_CONCEPTS = {"concept_obligation"}
# Concepts that were fully removed by the fix pass (every reference was a misuse).
FIXED_CONCEPTS = {"concept_bolster", "concept_dominion", "concept_fervor"}


def verdict_for(concept, basename, line):
    """Verdict for a *live* inventory row (MISUSE rows are gone post-fix)."""
    if (concept, basename, line) in BORDERLINE:
        v = BORDERLINE[(concept, basename, line)]
        return (v[0], v[2])
    if concept in BORDERLINE_CONCEPTS:
        return ("borderline", "treaty/debt/legal 'obligation' — concept is a diplomatic favor owed")
    if concept in WATCHLIST:
        return ("valid", "")
    return ("valid (unambiguous)", "")


def main():
    inv = json.load(open(os.path.join(HERE, "concept_usage_inventory.json")))
    rows = inv["rows"]
    names = {r["concept"]: r["concept_name"] for r in rows}
    by_concept = {}
    for r in rows:
        by_concept.setdefault(r["concept"], []).append(r)

    # Findings are the authoritative audit record. MISUSE entries were fixed
    # this pass (refs replaced with plain text) so they no longer appear in the
    # live inventory; BORDERLINE entries + every concept_obligation use were
    # left in place. audited_count restores the pre-fix per-concept total.
    misuse_count = {}
    for (c, _b, _l) in MISUSE:
        misuse_count[c] = misuse_count.get(c, 0) + 1

    def disp_name(c):
        return names.get(c) or c[len("concept_"):].replace("_", " ").title()

    findings = []  # (status, verdict, concept, basename, line, loc_key, note)
    for (c, base, line), (v, key, note) in MISUSE.items():
        findings.append(("fixed → plain text", v, c, base, line, key, note))
    for (c, base, line), (v, key, note) in BORDERLINE.items():
        findings.append(("kept (in place)", v, c, base, line, key, note))
    for r in rows:
        if r["concept"] in BORDERLINE_CONCEPTS:
            findings.append(("kept (in place)", "borderline", r["concept"],
                             os.path.basename(r["file"]), r["line"], r["loc_key"],
                             "treaty/debt/legal 'obligation' — concept is a diplomatic favor owed"))
    findings.sort(key=lambda f: (f[1] != "misuse", f[2], f[3], f[4]))

    out = []
    w = out.append
    w("# Concept-usage audit — mod localization")
    w("")
    w("One-shot semantic audit of every game-concept reference in "
      "`localization/english/*.yml`. Generated by "
      "`scripts/analysis/concept_usage_inventory.py` + "
      "`render_concept_usage_audit.py`.")
    w("")
    w("**Purpose.** Victoria 3 links concepts only via the explicit forms "
      "`[concept_X]` and `[Concept('concept_X','display')]` (no plain-text "
      "auto-linking — vanilla concepts define no aliases). This audit checks "
      "whether each reference's *meaning* fits its surrounding text. It "
      "complements `concept_reference_audit.py`, which only checks that a "
      "referenced concept *exists* (unregistered refs spam the engine log); "
      "the references here all exist but some link the wrong meaning — e.g. "
      "\"genetic `[concept_screening]`\" links the **naval ship-screening** "
      "concept.")
    w("")
    w("**Method.** Judgment is concentrated on the *ambiguity watchlist* — "
      "concepts whose display name is a common English word (listed below). "
      "Every instance of a watchlist concept was read. Concepts with a "
      "Vic3-specific name (`concept_gdp`, `concept_bureaucracy`, …) cannot be "
      "confused with another meaning and are marked **valid (unambiguous)**.")
    w("")
    forms = {}
    for r in rows:
        forms[r["form"]] = forms.get(r["form"], 0) + 1
    n_mis = sum(1 for f in findings if f[1] == "misuse")
    n_bor = sum(1 for f in findings if f[1] == "borderline")
    n_oblig = sum(1 for r in rows if r["concept"] in BORDERLINE_CONCEPTS)
    w("## Summary")
    w("")
    w(f"- **{len(rows) + len(MISUSE)}** reference instances audited "
      f"(**{n_mis}** misuses fixed this pass → plain text; "
      f"**{len(rows)}** remain in the live inventory below).")
    w(f"- Live: `[concept_X]` {forms.get('[concept_X]',0)}, "
      f"`[Concept(...)]` {forms.get('[Concept(...)]',0)}, across "
      f"**{len(by_concept)}** distinct concepts.")
    w(f"- **{n_mis} misuses** (fixed) + **{n_bor} borderline** instances "
      f"(kept), the latter including all {n_oblig} `concept_obligation` uses.")
    w(f"- `$concept_X$` free-standing substitutions "
      f"({len(inv['dollar_standalone'])}) are loc variables, not links — "
      f"excluded.")
    w("")

    w("## Ambiguity watchlist")
    w("")
    w("Concepts whose display name is a common English word; every instance of "
      "each was read. Count is the **pre-fix** total (live + fixed).")
    w("")
    w("| Concept | Display name | Vic3 meaning | Confusable with |")
    w("|---|---|---|---|")
    for c in sorted(WATCHLIST, key=lambda k: -(len(by_concept.get(k, [])) + misuse_count.get(k, 0))):
        seen = len(by_concept.get(c, [])) + misuse_count.get(c, 0)
        if seen == 0:
            continue
        vic3, conf = WATCHLIST[c]
        w(f"| `{c}` ({seen}) | {disp_name(c)} | {vic3} | {conf} |")
    w("")

    w("## Findings (misuse / borderline)")
    w("")
    w("Misuses were corrected in this pass (the `[concept_X]` / "
      "`[Concept(...)]` wrapper was replaced with the plain word, since no "
      "concept matches the intended meaning). Borderline instances were left "
      "in place.")
    w("")
    w("| Status | Verdict | Concept | Location | Loc key | Issue |")
    w("|---|---|---|---|---|---|")
    for status, v, c, base, line, key, note in findings:
        tag = "**misuse**" if v == "misuse" else "borderline"
        w(f"| {status} | {tag} | `{c}` | `{base}:{line}` | `{key}` | {note} |")
    w("")
    w("All `concept_obligation` instances are flagged borderline: the concept "
      "is specifically a diplomatic favor owed (from diplo plays / buyouts), "
      "but every mod use means a treaty / debt / legal \"obligation\" in the "
      "generic sense. Low-stakes (the word is generic) — reported, not fixed.")
    w("")

    w("## Full inventory")
    w("")
    w("Every reference, grouped by concept (descending frequency). Verdict "
      "column: `valid (unambiguous)` = Vic3-specific name; `valid` = watchlist "
      "concept, read and confirmed correct; `misuse`/`borderline` as above.")
    w("")
    for c in sorted(by_concept, key=lambda k: (-len(by_concept[k]), k)):
        cls = "watchlist" if c in WATCHLIST else "unambiguous"
        w(f"### `{c}` — {names.get(c,'')!r} ({len(by_concept[c])}, {cls})")
        w("")
        w("| Location | Loc key | Form | Verdict |")
        w("|---|---|---|---|")
        for r in sorted(by_concept[c], key=lambda r: (os.path.basename(r["file"]), r["line"])):
            base = os.path.basename(r["file"])
            v, _note = verdict_for(c, base, r["line"])
            tag = f"**{v}**" if v in ("misuse", "borderline") else v
            w(f"| `{base}:{r['line']}` | `{r['loc_key']}` | `{r['form']}` | {tag} |")
        w("")

    path = os.path.join(ROOT, "docs", "audits", "concept_usage_audit.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {path} ({len(out)} lines)")
    print(f"misuses={n_mis} borderline={n_bor}")


if __name__ == "__main__":
    main()
