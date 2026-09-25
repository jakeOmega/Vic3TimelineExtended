"""Organize all mod localization into category-based files.

Reads every .yml file under localization/english/ (except the replace/
subfolder, which contains vanilla overrides), merges all keys into a single
pool, categorises them, detects unused keys, and writes one output file per
category.

Output files:  localization/english/te_<category>_l_english.yml
  e.g. te_buildings_l_english.yml, te_events_l_english.yml, …

The script is idempotent: running it a second time produces identical output.
It preserves UTF-8 BOM encoding required by the Clausewitz engine.

Usage:
    python organize_loc.py            # Reorganize all loc files
    python organize_loc.py --dry-run  # Preview changes without writing
"""

import argparse
import os
import re
from collections import defaultdict

from path_constants import mod_path

# ---------------------------------------------------------------------------
# Implicit-key finders
# ---------------------------------------------------------------------------

def find_technology_keys(project_directory):
    """Finds technology keys by parsing technology definition files."""
    tech_keys = set()
    tech_path = os.path.join(project_directory, "common", "technology", "technologies")
    if not os.path.isdir(tech_path):
        return tech_keys
    for root, _, files in os.walk(tech_path):
        for file in files:
            if file.endswith(".txt"):
                with open(os.path.join(root, file), "r", encoding="utf-8-sig") as f:
                    for line in f:
                        match = re.match(r"^\s*([\w\._-]+)\s*=\s*{", line)
                        if match:
                            key = match.group(1)
                            tech_keys.add(key)
                            tech_keys.add(f"{key}_desc")
    return tech_keys


def find_notification_keys(project_directory):
    """Finds implicit notification keys from message definitions."""
    notification_keys = set()
    messages_path = os.path.join(project_directory, "common", "messages")
    if not os.path.isdir(messages_path):
        return notification_keys
    for root, _, files in os.walk(messages_path):
        for file in files:
            if file.endswith(".txt"):
                with open(os.path.join(root, file), "r", encoding="utf-8-sig") as f:
                    for line in f:
                        # Hyphen must be in the class: message base keys like
                        # `headlines_tech_e-commerce` would otherwise truncate to
                        # `headlines_tech_e`, stranding the real notification keys
                        # (notification_headlines_tech_e-commerce_*) as "unused".
                        match = re.match(r"^\s*([\w\.\-]+)\s*=\s*{", line)
                        if match:
                            base_key = match.group(1)
                            notification_keys.add(f"notification_{base_key}_name")
                            notification_keys.add(f"notification_{base_key}_desc")
                            notification_keys.add(f"notification_{base_key}_tooltip")
    return notification_keys


def find_game_rule_keys(project_directory):
    """Finds implicit setting and rule keys from game rule definitions."""
    game_rule_keys = set()
    rules_path = os.path.join(project_directory, "common", "game_rules")
    if not os.path.isdir(rules_path):
        return game_rule_keys
    for file in os.listdir(rules_path):
        if file.endswith(".txt"):
            with open(os.path.join(rules_path, file), "r", encoding="utf-8-sig") as f:
                content = f.read()
                top_level_matches = re.findall(
                    r"^([\w_]+)\s*=\s*{", content, re.MULTILINE
                )
                for base_key in top_level_matches:
                    game_rule_keys.add(f"rule_{base_key}")
                nested_matches = re.findall(
                    r"^\s+([\w_]+)\s*=\s*{", content, re.MULTILINE
                )
                for base_key in nested_matches:
                    game_rule_keys.add(f"setting_{base_key}")
                    game_rule_keys.add(f"setting_{base_key}_desc")
    return game_rule_keys


def find_company_keys(project_directory):
    """Finds implicit company keys for dynamic naming."""
    company_keys = set()
    company_path = os.path.join(project_directory, "common", "company_types")
    if not os.path.isdir(company_path):
        return company_keys
    for file in os.listdir(company_path):
        if file.endswith(".txt"):
            with open(os.path.join(company_path, file), "r", encoding="utf-8-sig") as f:
                content = f.read()
                blocks = re.findall(r"(\w+)\s*=\s*{(.*?)}", content, re.DOTALL)
                for block_name, block_content in blocks:
                    company_keys.add(block_name)
                    company_keys.add(f"{block_name}_desc")
                    if "uses_dynamic_naming = yes" in block_content:
                        company_keys.add(f"{block_name}_dynamic_name_tag_singular")
                        company_keys.add(f"{block_name}_dynamic_name_tag_plural")
    return company_keys


def find_law_keys(project_directory):
    """Finds implicit law keys for effects tooltips."""
    law_keys = set()
    laws_path = os.path.join(project_directory, "common", "laws")
    if not os.path.isdir(laws_path):
        return law_keys
    for file in os.listdir(laws_path):
        if file.endswith(".txt"):
            with open(os.path.join(laws_path, file), "r", encoding="utf-8-sig") as f:
                matches = re.findall(r"^\s*([\w\._-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    law_keys.add(base_key)
                    law_keys.add(f"{base_key}_desc")
                    law_keys.add(f"EFFECTS_ON_ACCEPTANCE_{base_key}")
    return law_keys


def find_diplo_action_keys(project_directory):
    """Finds implicit key suites for diplomatic actions.

    The suffix list is the autokey family vanilla localizes off its own action
    names (`diplomacy_l_english.yml` and friends). The third-party, break and
    directed `_effect_desc_*` / `_trigger_*desc_*` variants were missing until
    2026-09-25, so live keys such as
    `voluntary_union_decentralized_action_notification_third_party_desc` were
    filed to te_unused_l_english.yml.
    """
    diplo_keys = set()
    diplo_path = os.path.join(project_directory, "common", "diplomatic_actions")
    if not os.path.isdir(diplo_path):
        return diplo_keys
    suffixes = [
        "", "_desc", "_action_name", "_action_propose_name",
        "_action_notification_name", "_action_notification_desc",
        "_action_break_name", "_action_ask_to_break_name",
        "_action_notification_break_name", "_action_notification_break_desc",
        "_action_notification_third_party_name",
        "_action_notification_third_party_desc",
        "_action_notification_third_party_break_name",
        "_action_notification_third_party_break_desc",
        "_action_third_party_notification_break_name",
        "_action_third_party_notification_break_desc",
        "_proposal_accepted_name", "_proposal_accepted_desc",
        "_proposal_declined_name", "_proposal_declined_desc",
        "_proposal_notification_name", "_proposal_notification_desc",
        "_proposal_notification_effects_desc",
        "_proposal_third_party_accepted_name", "_proposal_third_party_accepted_desc",
        "_proposal_third_party_declined_name", "_proposal_third_party_declined_desc",
        "_proposal_notification_break_name", "_proposal_notification_break_desc",
        "_proposal_notification_break_effects_desc",
        "_proposal_break_accepted_name", "_proposal_break_accepted_desc",
        "_proposal_break_declined_name", "_proposal_break_declined_desc",
        "_proposal_third_party_break_accepted_name",
        "_proposal_third_party_break_accepted_desc",
        "_proposal_third_party_break_declined_name",
        "_proposal_third_party_break_declined_desc",
        "_effect_desc_first", "_effect_desc_third", "_effect_desc_global",
        "_trigger_desc_first", "_trigger_desc_third", "_trigger_desc_global",
        "_trigger_false_desc_first", "_trigger_false_desc_third",
        "_trigger_false_desc_global",
        "_pact_desc", "_type_break_desc",
    ]
    for file in os.listdir(diplo_path):
        if file.endswith(".txt"):
            with open(os.path.join(diplo_path, file), "r", encoding="utf-8-sig") as f:
                matches = re.findall(r"^\s*([\w\._-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    for suffix in suffixes:
                        diplo_keys.add(f"{base_key}{suffix}")
    return diplo_keys


def find_treaty_article_keys(project_directory):
    """Finds implicit key suites for treaty articles.

    The engine auto-resolves a family of loc keys off each article's top-level
    name — `<article>`, `<article>_desc`, `<article>_effects_desc` (the bullet
    list in the article picker), `<article>_article_short_desc` (the one-line
    summary on the treaty draft), and the directed `_effect_desc_first/_third/
    _global` variants. None of these are referenced from script, so without this
    parser they all fall to UNUSED and organize_loc exiles live, rendering keys
    to te_unused_l_english.yml. Confirmed against vanilla `diplomacy_l_english.yml`
    (guarantee_independence / trade_privilege / treaty_port / law_commitment).
    Added 2026-09-21 after `[concept_leverage]` inside five exiled
    `*_effects_desc` values spammed debug.log 612 times a session.
    """
    article_keys = set()
    articles_path = os.path.join(project_directory, "common", "treaty_articles")
    if not os.path.isdir(articles_path):
        return article_keys
    suffixes = [
        "", "_desc", "_effects_desc", "_article_short_desc",
        "_effect_desc_first", "_effect_desc_third", "_effect_desc_global",
        "_pact_desc",
    ]
    for file in os.listdir(articles_path):
        if file.endswith(".txt"):
            with open(os.path.join(articles_path, file), "r", encoding="utf-8-sig") as f:
                matches = re.findall(r"^([\w\.-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    for suffix in suffixes:
                        article_keys.add(f"{base_key}{suffix}")
    return article_keys


def find_political_movement_keys(project_directory):
    """Finds implicit keys for political movements."""
    movement_keys = set()
    movements_path = os.path.join(project_directory, "common", "political_movements")
    if not os.path.isdir(movements_path):
        return movement_keys
    for file in os.listdir(movements_path):
        if file.endswith(".txt"):
            with open(os.path.join(movements_path, file), "r", encoding="utf-8-sig") as f:
                matches = re.findall(r"^\s*([\w\._-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    movement_keys.add(base_key)
                    movement_keys.add(f"{base_key}_name")
    return movement_keys


def find_progress_bar_keys(project_directory):
    """Finds implicit name/desc keys for scripted progress bars.

    A bar with no explicit `name = "..."` field is labelled by the engine via the
    auto-keys `<bar>_name` / `<bar>_desc` (only 5 of the mod's bars set an explicit
    name; the rest rely on the auto-key). Without this, those auto-keys are flagged
    UNUSED — e.g. heir_education_progress_bar_name.
    """
    bar_keys = set()
    pb_path = os.path.join(project_directory, "common", "scripted_progress_bars")
    if not os.path.isdir(pb_path):
        return bar_keys
    for file in os.listdir(pb_path):
        if file.endswith(".txt"):
            with open(os.path.join(pb_path, file), "r", encoding="utf-8-sig") as f:
                matches = re.findall(r"^\s*([\w\._-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    bar_keys.add(f"{base_key}_name")
                    bar_keys.add(f"{base_key}_desc")
    return bar_keys


def find_journal_entry_keys(project_directory):
    """Finds implicit keys for journal entries."""
    je_keys = set()
    je_path = os.path.join(project_directory, "common", "journal_entries")
    if not os.path.isdir(je_path):
        return je_keys
    for file in os.listdir(je_path):
        if file.endswith(".txt"):
            with open(os.path.join(je_path, file), "r", encoding="utf-8-sig") as f:
                matches = re.findall(r"^\s*([\w\._-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    je_keys.add(base_key)
                    je_keys.add(f"{base_key}_reason")
                    je_keys.add(f"{base_key}_goal")
    return je_keys


# ---------------------------------------------------------------------------
# Key categorisation
# ---------------------------------------------------------------------------

# Event namespace prefixes detected automatically – keys that match
# <namespace>.<number>.<suffix> or <namespace>.<number> are EVENTS.
_EVENT_KEY_RE = re.compile(r"^([\w]+)\.\d+")

# Ordered list of output categories.
CATEGORIES = [
    "BUILDINGS",
    "COMBAT_UNITS",
    "COMPANIES",
    "CONCEPTS",
    "DECREES",
    "DIPLOMACY",
    "EVENTS",
    "FORMABLE_COUNTRIES",
    "GAME_RULES",
    "GOODS_AND_NEEDS",
    "IDEOLOGIES",
    "INSTITUTIONS",
    "JOURNAL_ENTRIES",
    "LAWS",
    "MESSAGES",
    "MOBILIZATION_OPTIONS",
    "MODIFIERS",
    "NOTIFICATIONS",
    "POLITICAL_MOVEMENTS",
    "POWER_BLOCS",
    "POWER_BLOC_UNLOCKS",
    "UN_BUTTON_EFFECTS",
    "PRODUCTION_METHODS",
    "RELIGION",
    "SHIP_MODIFICATIONS",
    "SHIP_TYPES",
    "STATE_TRAITS",
    "TECHNOLOGIES",
    "MISCELLANEOUS",
    "UNUSED",
]


def categorize_key(key, technology_keys):
    """Assigns a category to a localization key."""
    # --- Event keys (namespace.N or namespace.N.suffix) ---
    if _EVENT_KEY_RE.match(key):
        return "EVENTS"

    if key in technology_keys:
        return "TECHNOLOGIES"
    if key.startswith("setting_") or key.startswith("rule_"):
        return "GAME_RULES"
    if key.startswith("EFFECTS_ON_ACCEPTANCE_"):
        return "LAWS"
    if key.startswith("movement_"):
        return "POLITICAL_MOVEMENTS"
    if key.startswith(("pm_", "pmg_")):
        return "PRODUCTION_METHODS"
    if key.startswith("combat_unit_") or key.startswith("battle_condition_"):
        return "COMBAT_UNITS"
    if key.startswith("ship_type_"):
        return "SHIP_TYPES"
    if key.startswith("ship_group_"):
        return "SHIP_TYPES"
    if key.startswith("utility_mod_") or key.startswith("ship_mod_"):
        return "SHIP_MODIFICATIONS"
    if key.startswith("mobilization_option_"):
        return "MOBILIZATION_OPTIONS"
    if key.startswith("state_trait_"):
        return "STATE_TRAITS"
    if key.startswith("building_"):
        return "BUILDINGS"
    if key.startswith(("law_", "lawgroup_")):
        return "LAWS"
    if key.startswith("institution_"):
        return "INSTITUTIONS"
    if key.endswith(("_add", "_mult", "_add_desc", "_mult_desc")):
        return "MODIFIERS"
    if key.startswith(("goods_", "popneed_")):
        return "GOODS_AND_NEEDS"
    if key.startswith("company_"):
        return "COMPANIES"
    if key.startswith("ideology_"):
        return "IDEOLOGIES"
    if (
        key.startswith("dyn_c_")
        or key.startswith("dp_unify_")
        or key.startswith("dp_leadership_")
        or key in {
            "AFU", "INM", "EAF", "EUN", "UNA", "UNE", "ZHO", "BHA", "NUS", "DAR",
            "AFU_ADJ", "INM_ADJ", "EAF_ADJ", "EUN_ADJ", "UNA_ADJ", "UNE_ADJ", "ZHO_ADJ", "BHA_ADJ", "NUS_ADJ", "DAR_ADJ",
        }
    ):
        return "FORMABLE_COUNTRIES"
    if key.startswith("decree_"):
        return "DECREES"
    if key.startswith("je_"):
        return "JOURNAL_ENTRIES"
    if key.startswith("notification_"):
        return "NOTIFICATIONS"
    # Message / headline keys
    if key.startswith("headlines_"):
        return "MESSAGES"
    # "pact" has to match as a word, not a bare substring: `impact` otherwise
    # drags keys like `banking_dash_mon_stance_impact_line` and
    # `banking_event_default_rural_impact` into te_diplomacy_l_english.yml,
    # away from the 237 other `banking_dash_*` keys.
    #
    # `te_mon_` is excluded for the same family-splitting reason: the currency-
    # board modifier `te_mon_board_subject` has no `_subject_` in it but its
    # `_desc` does, so the pair would land in two files. The monetary rule
    # further down files both halves under MISCELLANEOUS.
    if not key.startswith("te_mon_") and (
        any(s in key for s in ["diplo", "_subject_", "_proposal_"])
        or re.search(r"(^|_)pacts?(_|$)", key)
    ):
        return "DIPLOMACY"
    # Tech-gated principle unlock boolean modifiers. The short-label keys
    # (`country_X_pb_principles_bool`) and their auto-generated descriptions
    # (`..._desc`) co-locate in te_power_bloc_unlocks_l_english.yml, where
    # gen_pb_principle_unlock_descs.py owns the `_desc` keys and preserves
    # the short labels around them.
    if key.endswith("_pb_principles_bool") or key.endswith("_pb_principles_bool_desc"):
        return "POWER_BLOC_UNLOCKS"
    # UN scripted-button effect summaries — auto-generated by gen_un_button_descs.py
    # and referenced from the corresponding UN_*_DESC keys via $..._EFFECTS$ splice.
    if key.startswith("UN_") and key.endswith("_EFFECTS"):
        return "UN_BUTTON_EFFECTS"
    if key.startswith(("power_bloc_", "principle_group_")):
        return "POWER_BLOCS"
    if any(s in key for s in ["religion", "SELECT_IDEOLOGY", "SELECT_TRAIT"]):
        return "RELIGION"
    # Broad "event" substring catch (modifier/tooltip keys mentioning events)
    if "event" in key:
        return "EVENTS"
    # Monetary-policy static modifier names. The base keys are four tokens long,
    # so without this rule the `_desc` half of each pair falls to CONCEPTS while
    # the name stays in MISCELLANEOUS and the family is split across two files.
    # Phase 2 adds three more prefixes: `te_mon_` and `te_monetisation_` (whose
    # three-token `te_monetisation_minting` would otherwise fall to CONCEPTS
    # outright, not just its `_desc`) and `te_inflation_` for the band set.
    # This rule must stay BELOW the `_add` / `_mult` line above, so the two
    # pressure modifier types still land in te_modifiers_l_english.yml.
    # Phase 4 adds `te_fx_` (three tokens: both halves would fall to CONCEPTS) and
    # `te_capital_controls_` (four: the pair would split).
    if key.startswith(("te_monetary_", "te_mon_", "te_monetisation_", "te_inflation_",
                       "te_fx_", "te_capital_controls_")):
        return "MISCELLANEOUS"
    if "_desc" in key or (re.match(r"^[a-zA-Z_]+$", key) and len(key.split("_")) < 4):
        return "CONCEPTS"
    return "MISCELLANEOUS"


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def _read_loc_file(path):
    """Parse a .yml loc file, returning {key: raw_value_after_first_colon}.

    Preserves the version number and quoted value exactly as written, e.g.
    for ` key:0 "value"` the dict entry is  key → '0 "value"'.
    Comment lines and the l_english: header are skipped.
    """
    data = {}
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped == "l_english:":
                continue
            m = re.match(r"^\s*([\w\.\-]+)\s*:(.*)", line)
            if m:
                data[m.group(1)] = m.group(2).rstrip("\n").rstrip("\r")
    return data


def _read_all_loc_files(loc_dir):
    """Read every .yml in *loc_dir* (non-recursive – skips subdirs like replace/)."""
    merged = {}
    files_read = []
    for fname in sorted(os.listdir(loc_dir)):
        if not fname.endswith(".yml"):
            continue
        path = os.path.join(loc_dir, fname)
        if not os.path.isfile(path):
            continue
        entries = _read_loc_file(path)
        files_read.append((fname, len(entries)))
        merged.update(entries)
    return merged, files_read


def _write_loc_file(path, sections):
    """Write a categorised loc file with UTF-8 BOM.

    *sections* is a list of tuples: [(section_name, {key: value}), …]
    """
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("l_english:\n")
        for section_name, entries in sections:
            if not entries:
                continue
            f.write(f"\n#\n# {section_name}\n#\n")
            for key in sorted(entries.keys()):
                f.write(f" {key}:{entries[key]}\n")


# ---------------------------------------------------------------------------
# Explicit-usage scanner
# ---------------------------------------------------------------------------

def find_used_keys_explicitly(directory):
    """Recursively finds all tokens that appear in .txt / .yml / .gui files."""
    used_keys = set()
    for root, _, files in os.walk(directory):
        # Skip the localization YAML folder itself (every key would trivially
        # reference itself). Match the path COMPONENT "localization", not the
        # substring — otherwise common/customizable_localization/ is also skipped
        # and every key referenced there (custom_loc localization_key = X) is
        # wrongly flagged unused.
        if "localization" in os.path.relpath(root, directory).split(os.sep):
            continue
        for file in files:
            if file.endswith((".txt", ".yml", ".gui")):
                try:
                    with open(
                        os.path.join(root, file), "r",
                        encoding="utf-8-sig", errors="ignore",
                    ) as f:
                        used_keys.update(re.findall(r"[\w\._-]+", f.read()))
                except Exception:
                    continue
    return used_keys


_QUOTED_ARG_RE = re.compile(r"'([\w.\-]+)'")


def find_quoted_loc_args(value):
    """Return the single-quoted tokens inside a loc value's `[...]` expressions.

    These are the keys a data function renders by name —
    `SelectLocalization( cond, 'a', 'b' )`, `AddLocalizationIf( cond, 'a' )` —
    which the `$key$` / `[X.GetKey]` patterns in the closure below never see.
    Text outside brackets is skipped, so a quoted word in prose never counts.
    """
    parts, depth = [], 0
    for ch in value:
        if ch == "[":
            depth += 1
        elif ch == "]" and depth:
            depth -= 1
            if not depth:
                parts.append(" ")
            continue
        if depth:
            parts.append(ch)
    return _QUOTED_ARG_RE.findall("".join(parts))


# ---------------------------------------------------------------------------
# Main organiser
# ---------------------------------------------------------------------------

def organize_all(project_directory, dry_run=False):
    """Read all loc, categorise, write per-category output files."""
    loc_dir = os.path.join(project_directory, "localization", "english")

    # ── 1. Read every .yml in the loc folder (top level only) ─────────────
    all_loc, files_read = _read_all_loc_files(loc_dir)
    print(f"Read {len(all_loc)} keys from {len(files_read)} files:")
    for fname, count in files_read:
        print(f"  {fname}: {count} keys")

    all_keys = set(all_loc.keys())

    # ── 2. Build the set of "used" keys (explicit + implicit) ─────────────
    used_keys = find_used_keys_explicitly(project_directory)

    parser_functions = [
        find_technology_keys,
        find_notification_keys,
        find_game_rule_keys,
        find_company_keys,
        find_law_keys,
        find_diplo_action_keys,
        find_treaty_article_keys,
        find_political_movement_keys,
        find_journal_entry_keys,
        find_progress_bar_keys,
    ]
    for func in parser_functions:
        used_keys.update(func(project_directory))

    technology_keys = find_technology_keys(project_directory)

    # Auto-add _desc companions
    for key in list(used_keys):
        desc_key = f"{key}_desc"
        if desc_key in all_keys:
            used_keys.add(desc_key)

    # Transitive closure: keys referenced inside loc values
    while True:
        newly_found = set()
        for key in used_keys:
            if key in all_loc:
                found = re.findall(r"[\$@!](\w+)[\$@!#|]", all_loc[key])
                found.extend(
                    m[1] for m in re.findall(r"\[\w+\.Get(Named)?(\w+)", all_loc[key])
                )
                found.extend(find_quoted_loc_args(all_loc[key]))
                for fk in found:
                    if fk in all_keys and fk not in used_keys:
                        newly_found.add(fk)
                        dk = f"{fk}_desc"
                        if dk in all_keys:
                            newly_found.add(dk)
        if not newly_found:
            break
        used_keys.update(newly_found)

    # SoL level keys are always used
    for key in all_keys:
        if re.match(
            r"^STANDARD_OF_LIVING_(LEVEL_\d+|LEVEL_ONLY_ICON_\d+|NO_ICON_LEVEL_\d+)$",
            key,
        ):
            used_keys.add(key)

    unused_keys = all_keys - used_keys

    # ── 3. Categorise every key ───────────────────────────────────────────
    categorized: dict[str, dict[str, str]] = defaultdict(dict)
    for key, value in all_loc.items():
        cat = "UNUSED" if key in unused_keys else categorize_key(key, technology_keys)
        categorized[cat][key] = value

    # ── 4. Sub-sort EVENTS by namespace for readability ───────────────────
    def _event_sections(entries):
        """Split event entries into (namespace, {key: val}) groups."""
        namespaces: dict[str, dict[str, str]] = defaultdict(dict)
        for key, val in entries.items():
            m = _EVENT_KEY_RE.match(key)
            ns = m.group(1).upper() if m else "OTHER_EVENT_KEYS"
            namespaces[ns][key] = val
        ordered = sorted(
            ((ns, d) for ns, d in namespaces.items() if ns != "OTHER_EVENT_KEYS"),
            key=lambda x: x[0],
        )
        if "OTHER_EVENT_KEYS" in namespaces:
            ordered.append(("OTHER_EVENT_KEYS", namespaces["OTHER_EVENT_KEYS"]))
        return ordered

    # ── 5. Build output plan: filename → [(section, {key: val}), …] ──────
    output_plan: dict[str, list[tuple[str, dict]]] = {}

    for cat in CATEGORIES:
        if cat not in categorized or not categorized[cat]:
            continue
        fname = f"te_{cat.lower()}_l_english.yml"
        if cat == "EVENTS":
            output_plan[fname] = _event_sections(categorized[cat])
        else:
            output_plan[fname] = [(cat, categorized[cat])]

    # ── 6. Report ─────────────────────────────────────────────────────────
    total_keys = sum(
        sum(len(d) for _, d in secs) for secs in output_plan.values()
    )
    print(f"\nCategorised {total_keys} keys into {len(output_plan)} files:")
    for fname in sorted(output_plan):
        sections = output_plan[fname]
        n = sum(len(d) for _, d in sections)
        sec_names = ", ".join(s for s, _ in sections)
        print(f"  {fname}: {n} keys  [{sec_names}]")

    if dry_run:
        print("\n--dry-run: no files written.")
        return

    # ── 7. Delete old .yml files (except replace/ subfolder) ──────────────
    for fname in os.listdir(loc_dir):
        fpath = os.path.join(loc_dir, fname)
        if os.path.isfile(fpath) and fname.endswith(".yml"):
            os.remove(fpath)
            print(f"  Removed old: {fname}")

    # ── 8. Write new per-category files ───────────────────────────────────
    for fname in sorted(output_plan):
        fpath = os.path.join(loc_dir, fname)
        _write_loc_file(fpath, output_plan[fname])
        n = sum(len(d) for _, d in output_plan[fname])
        print(f"  Wrote: {fname} ({n} keys)")

    print(f"\nDone. {total_keys} keys across {len(output_plan)} files.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def regenerate(mod_state=None):
    """Auto-run entrypoint invoked by mod_state_server post-load."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        organize_all(mod_path, dry_run=False)


def main():
    parser = argparse.ArgumentParser(
        description="Organize mod localization into per-category files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the output plan without writing any files.",
    )
    args = parser.parse_args()
    organize_all(mod_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
