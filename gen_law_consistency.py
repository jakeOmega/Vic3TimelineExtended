# -*- coding: utf-8 -*-
"""Generate law-consistency cleanup scripted effects.

Vic3 enforces a law's `unlocking_laws` / `disallowing_laws` constraints only at
enactment time. When OTHER laws change, dependent laws can be left in a
violating state (e.g. country switches from law_wealth_voting to law_technocracy
while keeping law_unregulated_donations active — that finance law's
unlocking_laws aren't met any more, but vanilla never re-checks).

This script reads every law's `group`, `progressiveness`, `unlocking_laws`,
`disallowing_laws`, plus per-ideology attitudes (vanilla files +
`ideology_modifications.modifications`), and emits one scripted effect per
lawgroup that detects the active law's constraint violations and replaces it
with the closest-progressiveness valid alternative. A thin dispatcher
`te_fix_inconsistent_laws` walks all groups in priority order; it is wired into
`on_law_activated` and `on_monthly_pulse_country` from
`common/on_actions/extra_on_actions.txt`.

Replacement-candidate ordering when active law L is invalid:
    1. abs(progressiveness − L.progressiveness) ascending.
    2. Tiebreak by ideology-attitude distance to L
       (per-ideology attitude scored as strongly_disapprove=−2 .. strongly_approve=2;
        distance = sum |a_L[i] − a_C[i]|).
    3. Final tiebreak: file/source order.

Each candidate is emitted with a validity guard (`limit = { ... }`) that must
hold for the `activate_law` to fire: its own `unlocking_laws`/`disallowing_laws`
are satisfied, any variant gate matches, AND every `unlocking_technologies` tech
is researched. The tech check is essential because `activate_law` ignores a
law's `unlocking_technologies` — without it the walk could drop a country into a
law it could never enact. A candidate with none of these (constraint-free,
non-variant, tech-free) is the cascade's unconditional terminal fallback; groups
lacking such a law get a generation-time WARNING (their cascade may leave a
violation unresolved until the relevant tech is researched).

Output: common/scripted_effects/extra_law_consistency_generated.txt
Auto-runs via mod_state_server `_run_post_load_generators`.

Usage:
    python gen_law_consistency.py            # write the generated file
    python gen_law_consistency.py --dry-run  # show summary without writing
"""

import argparse
import os
import re
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from path_constants import base_game_path, mod_path
from paradox_file_parser import ParadoxFileParser

# ── Configuration ────────────────────────────────────────────────────────────

# Lawgroup priority for the cleanup walk. Higher-priority lawgroups appear
# first; their active laws are considered "fixed" by the time the walk reaches
# lower-priority groups, implementing the rule "keep more important laws,
# change less important." Groups absent from this list are treated as lowest
# priority (warned at generation time).
LAWGROUP_PRIORITY = [
    # Tier 1 — regime structure (defines "what kind of country this is")
    "lawgroup_governance_principles",
    "lawgroup_distribution_of_power",
    "lawgroup_economic_system",
    "lawgroup_citizenship",
    "lawgroup_church_and_state",
    "lawgroup_bureaucracy",
    "lawgroup_army_model",
    "lawgroup_navy_model",

    # Tier 2 — functional state laws (regime-affected, broad-impact)
    "lawgroup_internal_security",
    "lawgroup_policing",
    "lawgroup_state_power",
    "lawgroup_trade_policy",
    "lawgroup_taxation",
    "lawgroup_land_reform",
    "lawgroup_colonization",
    "lawgroup_education_system",
    "lawgroup_health_system",
    "lawgroup_welfare",
    "lawgroup_migration",
    "lawgroup_free_speech",
    "lawgroup_labor_rights",
    "lawgroup_labour_associations",
    "lawgroup_childrens_rights",
    "lawgroup_rights_of_women",
    "lawgroup_slavery",
    "lawgroup_caste_hegemony",
    "lawgroup_edo_social_system",
    "lawgroup_rules_of_war",

    # Tier 3 — modern / modifier / overlay laws
    "lawgroup_minority_rights",
    "lawgroup_LGBTQ_rights",
    "lawgroup_criminal_justice",
    "lawgroup_intellectual_property",
    "lawgroup_monetary_policy",
    "lawgroup_right_to_information",
    "lawgroup_inheritance",
    "lawgroup_human_augmentation",
    "lawgroup_genetic_rights",
    "lawgroup_family_reproductive_policy",
    "lawgroup_language_policy",
    "lawgroup_antitrust",
    "lawgroup_financial_regulation",
    "lawgroup_internet_governance",
    "lawgroup_privacy_rights",
    "lawgroup_electoral_finance",

    # Tier 4 — institutions / ministries (toggleable, low coupling)
    "lawgroup_ministry_of_foreign_affairs",
    "lawgroup_ministry_of_war",
    "lawgroup_ministry_of_intelligence_and_security",
    "lawgroup_ministry_of_commerce",
    "lawgroup_national_bank",
    "lawgroup_ministry_of_the_environment",
    "lawgroup_ministry_of_culture",
    "lawgroup_ministry_of_labor",
    "lawgroup_ministry_of_refugee_affairs",
    "lawgroup_ministry_of_propaganda",
    "lawgroup_ministry_of_science",
    "lawgroup_ministry_of_thought_control",
    "lawgroup_ministry_of_consumer_protection",
    "lawgroup_ministry_of_urban_planning",
    "lawgroup_ministry_of_religion",
    "lawgroup_ministry_of_international_aid",
]

ATTITUDE_SCORES = {
    "strongly_disapprove": -2,
    "disapprove": -1,
    "neutral": 0,
    "approve": 1,
    "strongly_approve": 2,
}

# ── Variant candidate gates ─────────────────────────────────────────────────
#
# Vanilla marks tag/condition-restricted flavor variants with `parent = law_X`.
# These can be legitimate replacements *for the country they're flavored for*
# (e.g. JAP should be allowed to land on Terakoya when private_schools becomes
# invalid). Each entry below is the variant's `is_visible` block minus any
# same-lawgroup `NOT = { has_law = law_type:X }` mutex clauses — those are
# implicitly satisfied at activate_law time, since each group permits only one
# active law. Variants not listed here are excluded from candidate sets.
#
# Source-of-truth: vanilla `is_visible` blocks in common/laws/*.txt. Regenerate
# this table when vanilla changes (warning printed at generation if unknown
# `parent = law_X` laws appear).
VARIANT_CANDIDATE_GATES = {
    # Japan-specific
    "law_terakoya":              ["c:JAP ?= this"],
    "law_bakufu":                ["c:JAP ?= this"],
    "law_sakoku":                [
        "country_has_primary_culture = cu:japanese",
        "any_scope_state = { state_region = s:STATE_KYUSHU is_largest_state_in_region = yes }",
    ],
    "law_shinsengumi":           ["country_has_primary_culture = cu:japanese"],
    "law_warrior_caste":         ["country_has_primary_culture = cu:japanese"],

    # Han/China-specific
    "law_canton_system":         [
        "any_primary_culture = { has_discrimination_trait = heritage_han }",
        "any_scope_state = { state_region = s:STATE_GUANGDONG is_largest_state_in_region = yes }",
    ],

    # Austria/Romania
    "law_neo_absolutism":        ["c:AUS ?= this", "has_global_variable = neo_absolutism_victory"],
    "law_manorialism":           [
        "OR = {",
        "\tc:AUS ?= this",
        "\tAND = {",
        "\t\texists = c:AUS",
        "\t\tis_subject_of = c:AUS",
        "\t\tOR = {",
        "\t\t\tis_subject_type = subject_type_crown_land",
        "\t\t\tis_subject_type = subject_type_personal_union",
        "\t\t}",
        "\t\tc:AUS ?= { has_law = law_type:law_manorialism }",
        "\t}",
        "\tcountry_has_primary_culture = cu:romanian",
        "}",
    ],
    "law_crownland_diets":       [
        "OR = {",
        "\tc:AUS ?= this",
        "\tAND = {",
        "\t\texists = c:AUS",
        "\t\tis_subject_of = c:AUS",
        "\t}",
        "}",
    ],
    "law_organic_regulation":    ["country_has_primary_culture = cu:romanian", "is_subject = yes"],

    # Islamic / Ottoman
    "law_people_of_the_book":    ["country_is_islamic = yes", "NOT = { c:TUR ?= this }"],
    "law_millet_system":         ["c:TUR ?= this"],

    # Mongolia
    "law_chiefs_distribute_aid": ["c:MON ?= this"],
    "law_women_in_the_fields":   ["c:MON ?= this"],  # NOR of same-group women's-rights laws stripped (mutex)

    # Latin/Romance-language Mediterranean
    "law_latifundias":           [
        "any_primary_culture = { OR = {",
        "\thas_discrimination_trait = language_hispanophone",
        "\thas_discrimination_trait = language_lusophone",
        "\thas_discrimination_trait = language_italian",
        "} }",
        "hidden_trigger = { NOT = { has_variable = upgraded_latifundias_law_var } }",
    ],
    "law_expanded_latifundias":  [
        "any_primary_culture = { OR = {",
        "\thas_discrimination_trait = language_hispanophone",
        "\thas_discrimination_trait = language_lusophone",
        "\thas_discrimination_trait = language_italian",
        "} }",
        "hidden_trigger = { has_variable = upgraded_latifundias_law_var }",
    ],

    # Generic colonial / new-world
    "law_homesteading":          [
        "OR = {",
        "\tcountry_is_colonial_or_company = yes",
        "\tcapital ?= { is_in_geographic_region = geographic_region_new_world }",
        "}",
    ],
    "law_colonial_administration": ["country_is_colonial_or_company = yes"],
}

OUTPUT_PATH = os.path.join(
    mod_path, "common", "scripted_effects", "extra_law_consistency_generated.txt"
)
HEADER = (
    "# AUTO-GENERATED by gen_law_consistency.py - do not edit manually\n"
    "# See the script header for the algorithm and output contract.\n"
)


# ── Parsing ─────────────────────────────────────────────────────────────────


def _law_dirs():
    return [
        os.path.join(base_game_path, "game", "common", "laws"),
        os.path.join(mod_path, "common", "laws"),
    ]


def _list_law_files():
    paths = []
    for root in _law_dirs():
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if name.endswith(".txt"):
                paths.append(os.path.join(root, name))
    return paths


def _string_value(v):
    """Unwrap (operator, value) tuples from ParadoxFileParser."""
    while isinstance(v, tuple) and len(v) >= 2:
        v = v[1]
    return v


def _law_id_list(v):
    """Extract list of law_* identifiers from an unlocking/disallowing block."""
    v = _string_value(v)
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.startswith("law_") else []
    if isinstance(v, list):
        out = []
        for item in v:
            item = _string_value(item)
            if isinstance(item, str) and item.startswith("law_"):
                out.append(item)
            elif isinstance(item, dict):
                # Rare: parser folded a list into a single-key dict pseudo-list
                for key in item:
                    if isinstance(key, str) and key.startswith("law_"):
                        out.append(key)
        return out
    if isinstance(v, dict):
        return [k for k in v.keys() if isinstance(k, str) and k.startswith("law_")]
    return []


def _id_list(v):
    """Extract a flat list of identifiers from a `{ a b c }`-style block.

    Like `_law_id_list` but accepts any identifier (e.g. technology names in an
    `unlocking_technologies` block), not just `law_*`.
    """
    v = _string_value(v)
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        out = []
        for item in v:
            item = _string_value(item)
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                out.extend(k for k in item if isinstance(k, str))
        return out
    if isinstance(v, dict):
        return [k for k in v if isinstance(k, str)]
    return []


def parse_laws():
    """Return dict: law_id -> {group, progressiveness, unlocking_laws,
    disallowing_laws, unlocking_technologies, file_order}.

    File order: integer rank in the order laws are first encountered across
    vanilla files (alphabetical) then mod files (alphabetical). Used as the
    final candidate-sort tiebreak.
    """
    parser = ParadoxFileParser()
    file_order = {}
    rank = 0

    files = _list_law_files()
    law_def_re = re.compile(
        r"^(?:INJECT:|REPLACE:|REPLACE_OR_CREATE:)?(law_[A-Za-z0-9_]+)\s*=\s*\{",
        re.MULTILINE,
    )

    for fp in files:
        with open(fp, encoding="utf-8-sig") as f:
            text = f.read()
        for m in law_def_re.finditer(text):
            law_id = m.group(1)
            if law_id not in file_order:
                file_order[law_id] = rank
                rank += 1
        try:
            parser.parse_file(fp)
        except Exception as e:
            print(f"WARNING: parse error in {fp}: {e}", file=sys.stderr)

    laws = {}
    for law_id, value in parser.data.items():
        if not isinstance(law_id, str) or not law_id.startswith("law_"):
            continue
        body = _string_value(value)
        if not isinstance(body, dict):
            continue
        group = _string_value(body.get("group"))
        if not (isinstance(group, str) and group.startswith("lawgroup_")):
            continue
        progressiveness = _string_value(body.get("progressiveness"))
        try:
            progressiveness = int(progressiveness) if progressiveness is not None else 0
        except (TypeError, ValueError):
            try:
                progressiveness = int(float(progressiveness))
            except (TypeError, ValueError):
                progressiveness = 0
        # Vanilla also uses `requires_law_or` (e.g. law_neo_absolutism). It has
        # the same "at least one of these must be active" semantics as
        # unlocking_laws, so merge them.
        unlocking = _law_id_list(body.get("unlocking_laws"))
        unlocking += [lid for lid in _law_id_list(body.get("requires_law_or")) if lid not in unlocking]

        # Vanilla marks tag/condition-restricted flavor variants with
        # `parent = law_X` (e.g. law_terakoya parent=law_private_schools,
        # law_bakufu parent=law_autocracy, law_sakoku parent=law_isolationism).
        # These have `is_visible` country/tag gates and `can_impose = always = no`;
        # they are not legitimate replacement candidates for the consistency walk.
        parent = _string_value(body.get("parent"))
        if not (isinstance(parent, str) and parent.startswith("law_")):
            parent = None

        laws[law_id] = {
            "group": group,
            "progressiveness": progressiveness,
            "unlocking_laws": unlocking,
            "disallowing_laws": _law_id_list(body.get("disallowing_laws")),
            "unlocking_technologies": _id_list(body.get("unlocking_technologies")),
            "parent": parent,
            "file_order": file_order.get(law_id, 1_000_000),
        }
    return laws


# ── Ideology attitudes ───────────────────────────────────────────────────────


def parse_ideologies():
    """Return dict: ideology_id -> { law_id: attitude_score }.

    Built from vanilla ideology files first (ParadoxFileParser handles
    INJECT/REPLACE for any mod-side ideology .txt files we also load), then
    overlaid with mod-only attitudes from `ideology_modifications.modifications`.
    """
    parser = ParadoxFileParser()
    for root in [
        os.path.join(base_game_path, "game", "common", "ideologies"),
        os.path.join(mod_path, "common", "ideologies"),
    ]:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.endswith(".txt"):
                continue
            try:
                parser.parse_file(os.path.join(root, name))
            except Exception as e:
                print(f"WARNING: ideology parse error in {name}: {e}", file=sys.stderr)

    attitudes = {}
    for ideology_id, value in parser.data.items():
        if not isinstance(ideology_id, str) or not ideology_id.startswith("ideology_"):
            continue
        body = _string_value(value)
        if not isinstance(body, dict):
            continue
        law_attitudes = {}
        for sub_key, sub_value in body.items():
            if not (isinstance(sub_key, str) and sub_key.startswith("lawgroup_")):
                continue
            sub_body = _string_value(sub_value)
            if not isinstance(sub_body, dict):
                continue
            for law_id, attitude in sub_body.items():
                attitude = _string_value(attitude)
                if isinstance(law_id, str) and law_id.startswith("law_") and isinstance(attitude, str):
                    if attitude in ATTITUDE_SCORES:
                        law_attitudes[law_id] = ATTITUDE_SCORES[attitude]
        attitudes[ideology_id] = law_attitudes

    # Overlay ideology_modifications.modifications (mod-only attitudes that the
    # apply_ideologies generator writes into common/ideologies/modified.txt;
    # parsing modified.txt above already accounts for them, but reading the
    # source dict directly avoids depending on apply_ideologies having run).
    try:
        from ideology_modifications import modifications as ideology_mods
    except Exception:
        ideology_mods = {}

    for ideology_id, group_dict in ideology_mods.items():
        target = attitudes.setdefault(ideology_id, {})
        for _group, law_attitude_pairs in group_dict.items():
            for law_id, attitude in law_attitude_pairs:
                if attitude in ATTITUDE_SCORES:
                    target[law_id] = ATTITUDE_SCORES[attitude]

    return attitudes


def ideology_distance(law_a, law_b, attitudes):
    """Sum |attitude(law_a, ideology) − attitude(law_b, ideology)| over all
    ideologies that have an opinion on either. Missing attitude defaults to 0
    (neutral); ideologies with no opinion on either law contribute 0."""
    distance = 0
    for ideology_id, law_attitudes in attitudes.items():
        a = law_attitudes.get(law_a, 0)
        b = law_attitudes.get(law_b, 0)
        distance += abs(a - b)
    return distance


# ── Algorithm ───────────────────────────────────────────────────────────────


def laws_by_group(laws):
    grouped = {}
    for law_id, law in laws.items():
        grouped.setdefault(law["group"], []).append(law_id)
    return grouped


def has_constraints(law):
    return bool(law["unlocking_laws"]) or bool(law["disallowing_laws"])


def constraint_having_groups(laws):
    """Groups where at least one law declares cross-group constraints."""
    grouped = laws_by_group(laws)
    out = []
    for group_id, law_ids in grouped.items():
        if any(has_constraints(laws[lid]) for lid in law_ids):
            out.append(group_id)
    return out


def candidate_order(active_law_id, group_law_ids, laws, attitudes):
    """Return list of candidate replacement law_ids (excluding active_law_id),
    ordered by progressiveness distance, then ideology distance, then file order.

    Variant laws (`parent = law_X`) are included only if listed in
    VARIANT_CANDIDATE_GATES. Their gate clauses are added to the validity check
    at emit time so the replacement only fires for the country/condition the
    variant is flavored for (e.g. JAP for Terakoya).
    """
    L = laws[active_law_id]

    def sort_key(c_id):
        c = laws[c_id]
        prog_dist = abs(c["progressiveness"] - L["progressiveness"])
        ideo_dist = ideology_distance(active_law_id, c_id, attitudes)
        return (prog_dist, ideo_dist, c["file_order"], c_id)

    candidates = [
        lid for lid in group_law_ids
        if lid != active_law_id
        and (laws[lid].get("parent") is None or lid in VARIANT_CANDIDATE_GATES)
    ]
    candidates.sort(key=sort_key)
    return candidates


# ── Emission ────────────────────────────────────────────────────────────────


def _violation_clause(law, indent):
    """Emit the trigger clauses that detect law's own constraints being violated.

    The full violation predicate (used inside a `limit = { has_law=...; OR={...} }`
    block) is `unlocking_violated OR any_disallowing_active`. We compose it with
    a single OR.
    """
    parts = []
    if law["unlocking_laws"]:
        unlocking = "\n".join(
            f"{indent}\t\thas_law = law_type:{law_id}" for law_id in law["unlocking_laws"]
        )
        parts.append(f"{indent}\tNOR = {{\n{unlocking}\n{indent}\t}}")
    for d_law in law["disallowing_laws"]:
        parts.append(f"{indent}\thas_law = law_type:{d_law}")
    if not parts:
        return ""
    return f"{indent}OR = {{\n" + "\n".join(parts) + f"\n{indent}}}"


def _validity_clause(law_id, law, indent):
    """Emit the inverse: candidate `law` is currently valid (constraints met).

    Uses an AND-by-default `limit = { ... }`-style block. Returns the inner
    lines (without the surrounding `limit = { ... }`). Empty string means the
    law has no constraints, no variant gate, and no unlocking_technologies — it
    is unconditionally valid and serves as the cascade's terminal fallback.

    For variants with an entry in VARIANT_CANDIDATE_GATES, the gate clauses
    are prepended so the candidate only fires for the country/condition the
    variant is flavored for.
    """
    lines = []
    gate = VARIANT_CANDIDATE_GATES.get(law_id)
    if gate:
        for gate_line in gate:
            lines.append(f"{indent}{gate_line}")
    if law["unlocking_laws"]:
        body = "\n".join(
            f"{indent}\thas_law = law_type:{lid}" for lid in law["unlocking_laws"]
        )
        lines.append(f"{indent}OR = {{\n{body}\n{indent}}}")
    if law["disallowing_laws"]:
        body = "\n".join(
            f"{indent}\thas_law = law_type:{lid}" for lid in law["disallowing_laws"]
        )
        lines.append(f"{indent}NOR = {{\n{body}\n{indent}}}")
    # activate_law ignores a law's unlocking_technologies, so the consistency
    # walk must check them itself or it can drop a country into a law it could
    # never enact. Multiple techs are an AND gate (AND-by-default limit block).
    for tech in law.get("unlocking_technologies", []):
        lines.append(f"{indent}has_technology_researched = {tech}")
    return "\n".join(lines)


def emit_lawgroup_helper(group_id, group_law_ids, laws, attitudes):
    """Build the `te_fix_inconsistent_lawgroup_<group> = { ... }` block."""
    name = f"te_fix_inconsistent_lawgroup_{group_id[len('lawgroup_'):]}"
    out = [f"{name} = {{"]

    constrained = [lid for lid in group_law_ids if has_constraints(laws[lid])]
    # Stable order for diffability: sort by file_order
    constrained.sort(key=lambda lid: (laws[lid]["file_order"], lid))

    for active_id in constrained:
        active = laws[active_id]
        violation_clause = _violation_clause(active, "\t\t\t")
        # Sanity: should always be non-empty since `has_constraints(active)` was True
        if not violation_clause:
            continue

        out.append(f"\t# Active: {active_id}  ->  detect violation, cascade replacements")
        out.append("\tif = {")
        out.append("\t\tlimit = {")
        out.append(f"\t\t\thas_law = law_type:{active_id}")
        out.append(violation_clause)
        out.append("\t\t}")

        candidates = candidate_order(active_id, group_law_ids, laws, attitudes)

        first = True
        for cand_id in candidates:
            cand = laws[cand_id]
            validity = _validity_clause(cand_id, cand, "\t\t\t\t")
            kw = "if" if first else "else_if"
            first = False
            if validity:
                out.append(f"\t\t{kw} = {{")
                out.append("\t\t\tlimit = {")
                out.append(validity)
                out.append("\t\t\t}")
                out.append(f"\t\t\tactivate_law = law_type:{cand_id}")
                out.append("\t\t}")
            else:
                # Unconditionally valid candidate — terminal in cascade.
                out.append(f"\t\t{kw} = {{")
                out.append("\t\t\tlimit = { always = yes }")
                out.append(f"\t\t\tactivate_law = law_type:{cand_id}")
                out.append("\t\t}")
                # Once we hit an unconditionally-valid candidate, no later
                # candidate can ever be reached, so stop emitting.
                break

        out.append("\t}")
        out.append("")

    out.append("}")
    return "\n".join(out)


def emit_dispatcher(ordered_groups):
    # The on_law_activated wrapper `te_fix_inconsistent_laws_from_law_scope`
    # is defined as an on_action in common/on_actions/extra_on_actions.txt
    # (must be an on_action, not a scripted_effect, since on_actions invoke
    # other on_actions by tag and won't resolve scripted_effect names).
    out = ["te_fix_inconsistent_laws = {"]
    for g in ordered_groups:
        helper = f"te_fix_inconsistent_lawgroup_{g[len('lawgroup_'):]}"
        out.append(f"\t{helper} = yes")
    out.append("}")
    return "\n".join(out)


def build_output(laws, attitudes):
    grouped = laws_by_group(laws)
    have_constraints = constraint_having_groups(laws)

    # Order groups: priority list first (only those that actually have
    # constraint-having laws), then any constraint-having groups missing from
    # the priority list, sorted by name for stability.
    priority_index = {g: i for i, g in enumerate(LAWGROUP_PRIORITY)}
    in_list = [g for g in LAWGROUP_PRIORITY if g in have_constraints]
    out_of_list = sorted(g for g in have_constraints if g not in priority_index)

    if out_of_list:
        print(
            f"WARNING: lawgroups not in LAWGROUP_PRIORITY (treating as lowest priority): {out_of_list}",
            file=sys.stderr,
        )

    ordered_groups = in_list + out_of_list

    # Lawgroups in LAWGROUP_PRIORITY but with no constraint-having laws are
    # silently skipped; print summary so the user sees what's actually emitted.
    print(f"[gen_law_consistency] {len(ordered_groups)} groups emit helpers: {ordered_groups}")

    variants = sorted(lid for lid, law in laws.items() if law.get("parent"))
    gated = [lid for lid in variants if lid in VARIANT_CANDIDATE_GATES]
    skipped = [lid for lid in variants if lid not in VARIANT_CANDIDATE_GATES]
    if gated:
        print(
            f"[gen_law_consistency] {len(gated)} variant laws included with candidate gate: {gated}"
        )
    if skipped:
        # If this prints, vanilla added a new variant; add it to VARIANT_CANDIDATE_GATES.
        print(
            f"WARNING: {len(skipped)} variant laws have parent= but no entry in VARIANT_CANDIDATE_GATES (excluded from candidates): {skipped}",
            file=sys.stderr,
        )

    # A cascade is only guaranteed to resolve a violation if its group contains
    # at least one law that is a valid candidate under every condition: no
    # unlocking_laws, no disallowing_laws, not a tag-restricted variant, and no
    # unlocking_technologies. Tech gating (added because activate_law ignores
    # unlocking_technologies) means a tech-gated constraint-free law is no longer
    # an unconditional terminal. Warn for any group lacking such a fallback — its
    # cascade may leave a violating law in place until the relevant tech is
    # researched (benign: re-checked on monthly pulse / on_law_activated).
    def _has_unconditional_fallback(group_id):
        for lid in grouped.get(group_id, []):
            law = laws[lid]
            if (not law["unlocking_laws"]
                    and not law["disallowing_laws"]
                    and not law.get("parent")
                    and not law.get("unlocking_technologies")):
                return True
        return False

    no_fallback = [g for g in ordered_groups if not _has_unconditional_fallback(g)]
    if no_fallback:
        print(
            f"WARNING: {len(no_fallback)} constrained lawgroups have no tech-free, "
            f"constraint-free fallback law; their consistency cascade may not resolve "
            f"a violation until the relevant tech is researched: {no_fallback}",
            file=sys.stderr,
        )

    parts = [HEADER]
    for g in ordered_groups:
        parts.append(emit_lawgroup_helper(g, grouped[g], laws, attitudes))
        parts.append("")
    parts.append(emit_dispatcher(ordered_groups))
    parts.append("")
    return "\n".join(parts)


def write_output(content, dry_run=False):
    if dry_run:
        print(f"[dry-run] Would write {len(content)} bytes to {OUTPUT_PATH}")
        return
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    # utf-8-sig prepends the UTF-8 BOM the Clausewitz parser requires.
    with open(OUTPUT_PATH, "w", encoding="utf-8-sig") as f:
        f.write(content)
    print(f"[gen_law_consistency] wrote {OUTPUT_PATH} ({len(content)} bytes)")


# ── Entry points ────────────────────────────────────────────────────────────


def regenerate(mod_state=None):
    """Auto-run entrypoint invoked by mod_state_server post-load.

    `mod_state` is accepted for protocol compatibility but unused — the
    generator parses files directly so it works in standalone CLI mode too.
    """
    laws = parse_laws()
    attitudes = parse_ideologies()
    content = build_output(laws, attitudes)
    write_output(content, dry_run=False)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--dry-run", action="store_true", help="Print summary without writing.")
    args = p.parse_args()
    laws = parse_laws()
    attitudes = parse_ideologies()
    content = build_output(laws, attitudes)
    write_output(content, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
