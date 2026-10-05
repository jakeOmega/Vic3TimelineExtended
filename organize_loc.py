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
    python organize_loc.py --check    # Write nothing; exit 1 if a run would change a file (CI)
"""

import argparse
import contextlib
import io
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
    return set(treaty_article_families(project_directory))


_TREATY_ARTICLE_SUFFIXES = (
    "", "_desc", "_effects_desc", "_article_short_desc",
    "_effect_desc_first", "_effect_desc_third", "_effect_desc_global",
    "_pact_desc",
)


def treaty_article_families(project_directory):
    """Map every engine-built treaty-article key to its article: `{key: article}`.

    `find_treaty_article_keys` uses the keys; `categorize_key` uses the map to
    file an article's whole family together (#357).
    """
    families = {}
    articles_path = os.path.join(project_directory, "common", "treaty_articles")
    if not os.path.isdir(articles_path):
        return families
    for file in os.listdir(articles_path):
        if file.endswith(".txt"):
            with open(os.path.join(articles_path, file), "r", encoding="utf-8-sig") as f:
                matches = re.findall(r"^([\w\.-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    for suffix in _TREATY_ARTICLE_SUFFIXES:
                        families[f"{base_key}{suffix}"] = base_key
    return families


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


def find_war_goal_keys(project_directory):
    """Finds the implicit key suite for war goal types.

    The engine names a war goal's text off its type key with no script
    reference: `war_goal_<type>` (the goal as drafted), `_desc`, `_sway_desc`,
    `_type_name` and `_type_desc`. Confirmed against vanilla
    `war_goal_annex_country*`. Without this, te_reunify_country's whole suite
    ("Reunify the Nation") was filed to te_unused_l_english.yml.
    """
    war_goal_keys = set()
    wg_path = os.path.join(project_directory, "common", "war_goal_types")
    if not os.path.isdir(wg_path):
        return war_goal_keys
    suffixes = ["", "_desc", "_sway_desc", "_type_name", "_type_desc"]
    for file in os.listdir(wg_path):
        if file.endswith(".txt"):
            with open(os.path.join(wg_path, file), "r", encoding="utf-8-sig") as f:
                matches = re.findall(r"^([\w\.-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    for suffix in suffixes:
                        war_goal_keys.add(f"war_goal_{base_key}{suffix}")
    return war_goal_keys


# A script token built from literal text and `$PARAM$` placeholders, e.g.
# `nd_tt_$VAR$_$OP$` or `nd_tt_readiness_target_$R$`.
_TEMPLATE_TOKEN_RE = re.compile(r"[\w.\-]*(?:\$[A-Z][A-Z0-9_]*\$[\w.\-]*)+")
_PLACEHOLDER_RE = re.compile(r"\$([A-Z][A-Z0-9_]*)\$")
# A top-level definition in a scripted effect / trigger file.
_TOP_LEVEL_DEF_RE = re.compile(r"^([\w.\-]+)\s*=\s*\{", re.MULTILINE)
# Any block opener; a call of a parameterized effect or trigger is one of these.
_BLOCK_OPEN_RE = re.compile(r"(?<![\w.\-$:@])([A-Za-z_][\w.\-]*)\s*=\s*\{")
# A call-site argument, `PARAM = value`, at the top level of the call block.
_CALL_ARG_RE = re.compile(r"(?<![\w$])([A-Z][A-Z0-9_]*)\s*=\s*([^\s{}\"]+)")
# Where parameterized effects and triggers are defined, and where they are called.
_PARAM_DEF_DIRS = (os.path.join("common", "scripted_effects"), os.path.join("common", "scripted_triggers"))
_SCRIPT_DIRS = ("common", "events")
# Skip a template whose expansion would exceed this many strings.
_MAX_TEMPLATE_EXPANSION = 50000


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block_end(text, open_brace):
    """Index just past the brace that closes the one at `open_brace`."""
    depth = 0
    for i in range(open_brace, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)


def _read_script_texts(project_directory, subdirs):
    texts = {}
    for sub in subdirs:
        for root, _, files in os.walk(os.path.join(project_directory, sub)):
            for file in files:
                if not file.endswith(".txt"):
                    continue
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                        texts[path] = _strip_comments(f.read())
                except OSError:
                    continue
    return texts


def find_parameterized_keys(project_directory, all_keys):
    """Finds loc keys that script reaches only through `$PARAM$` substitution.

    A scripted effect such as `custom_tooltip = { text = nd_tt_$VAR$_$OP$ }`
    names its loc key only after the caller fills in `VAR = nd_hardening
    OP = add`; the plain token scan sees `nd_tt_`, `VAR` and `OP`, never
    `nd_tt_nd_hardening_add`, so such keys were filed as unused.

    Each templated token is expanded with the values that the calls of ITS OWN
    effect or trigger pass for each parameter. A call that passes a parameter
    on (`MILESTONE = $MILESTONE$`) contributes whatever its enclosing
    definition's callers pass. Only expansions that are real loc keys count.
    """
    script = _read_script_texts(project_directory, _SCRIPT_DIRS)
    def_dirs = tuple(os.path.join(project_directory, d) + os.sep for d in _PARAM_DEF_DIRS)

    # Definitions that use placeholders, with their templates and spans.
    templates_of = {}   # def name -> set of templated tokens
    spans = []          # (path, start, end, def name) for every definition
    for path, text in script.items():
        if not path.startswith(def_dirs):
            continue
        for m in _TOP_LEVEL_DEF_RE.finditer(text):
            name = m.group(1)
            end = _block_end(text, m.end() - 1)
            spans.append((path, m.start(), end, name))
            body = text[m.end():end]
            if "$" in body:
                toks = {t for t in _TEMPLATE_TOKEN_RE.findall(body) if _PLACEHOLDER_RE.sub("", t)}
                templates_of.setdefault(name, set()).update(toks)
    # Every definition that uses a placeholder, including one that only passes
    # its parameters on to another call, needs its callers' arguments.
    param_defs = {name for path, start, end, name in spans if "$" in script[path][start:end]}

    def enclosing_def(path, pos):
        for p, start, end, name in spans:
            if p == path and start <= pos < end:
                return name
        return None

    # Every call of a parameterized definition: (callee, {PARAM: value}, caller).
    calls = defaultdict(list)
    for path, text in script.items():
        if "=" not in text:
            continue
        for m in _BLOCK_OPEN_RE.finditer(text):
            callee = m.group(1)
            if callee not in param_defs:
                continue
            end = _block_end(text, m.end() - 1)
            inner = text[m.end():end - 1]
            # Top-level arguments only: blank out nested blocks.
            flat, depth = [], 0
            for c in inner:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                elif depth == 0:
                    flat.append(c)
                    continue
                flat.append(" ")
            args = dict(_CALL_ARG_RE.findall("".join(flat)))
            caller = enclosing_def(path, m.start()) if path.startswith(def_dirs) else None
            calls[callee].append((args, caller))

    memo = {}

    def expand(template, def_name, seen):
        """Every string `template` can become inside `def_name`."""
        pieces = _PLACEHOLDER_RE.split(template)
        # pieces alternate literal, param, literal, param, ..., literal
        pools = [values_for(def_name, p, seen) for p in pieces[1::2]]
        if not all(pools):
            return set()
        size = 1
        for pool in pools:
            size *= len(pool)
        if size > _MAX_TEMPLATE_EXPANSION:
            return set()
        candidates = [pieces[0]]
        for i, pool in enumerate(pools):
            literal = pieces[2 * i + 2]
            candidates = [c + v + literal for c in candidates for v in pool]
        return set(candidates)

    cut_log = []  # keys whose recursion a cycle cut short, in order

    def values_for(def_name, param, seen=()):
        """Every value the callers of `def_name` pass for `param`."""
        key = (def_name, param)
        if key in memo:
            return memo[key]
        if key in seen:
            # A cycle (A passes $X$ to B, B passes it back): stop here. The
            # loop can only feed back values the outer call already collects.
            cut_log.append(key)
            return set()
        cuts_before = len(cut_log)
        out = set()
        for args, caller in calls.get(def_name, ()):
            value = args.get(param)
            if value is None:
                continue
            if "$" in value:
                # Passed on from the caller's own parameters
                # (`MILESTONE = $MILESTONE$`, `KEY = sr_$MILESTONE$`).
                if caller:
                    out |= expand(value, caller, seen + (key,))
            else:
                out.add(value)
        # A result is complete unless a cycle was cut at some OTHER key below
        # this one: then an inner definition is missing values that only its
        # outer caller supplies, so it is not remembered.
        if all(k == key for k in cut_log[cuts_before:]):
            memo[key] = out
        return out

    found = set()
    for def_name, templates in templates_of.items():
        for template in templates:
            found.update(c for c in expand(template, def_name, ()) if c in all_keys)
    return found


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
    "DEBUG_TAX",
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
    "TAX",
    "TAX_GENERATED",
    "BUDGET",
    "TECHNOLOGIES",
    "MISCELLANEOUS",
    "UNUSED",
]

# Disposable developer harnesses. Each owns a dedicated file, and every key it
# claims files there even when the unused scan finds no reference, so removing
# the harness is deleting that one file. The tax probes' `te_tp_action_arm` has
# no button (arming is the console's `event te_debug_tax.1`) and would
# otherwise split off into te_unused_l_english.yml.
HARNESS_CATEGORIES = {"DEBUG_TAX"}

# Categories whose file a generator also writes, mapped to the marker the file
# carries. Like a harness, such a file holds its whole family even for a key no
# script names yet. The marker is part of the section comment, because a run
# rewrites the file from scratch and a comment elsewhere in it would be dropped
# (`_read_loc_file` skips comments); the generator renders its file through
# `section_label`, so the two writers agree byte for byte (docs/auto_generated_files.md).
GENERATED_CATEGORIES = {
    "TAX_GENERATED": "AUTO-GENERATED by scripts/generators/gen_tax_code.py \u2014 do not edit manually",
    "BUDGET": "AUTO-GENERATED by scripts/generators/gen_budget_breakdown.py \u2014 do not edit manually",
}


def section_label(category):
    """The section comment a category's file carries: its name, plus the
    marker when a generator owns the file."""
    marker = GENERATED_CATEGORIES.get(category)
    return f"{category}\n# {marker}" if marker else category


def categorize_key(key, technology_keys, treaty_article_of=None):
    """Assigns a category to a localization key.

    `treaty_article_of` is `treaty_article_families()`'s map. A treaty
    article's keys all file wherever its `<article>_desc` does, so the family
    never splits across files (#357): `lender_of_last_resort` has four tokens
    and `science_aid_2` a digit, so their bare names used to fall to
    MISCELLANEOUS while the `_desc` keys went to CONCEPTS.
    """
    if treaty_article_of and key in treaty_article_of:
        return categorize_key(f"{treaty_article_of[key]}_desc", technology_keys)
    # --- Event keys (namespace.N or namespace.N.suffix) ---
    if _EVENT_KEY_RE.match(key):
        return "EVENTS"

    if key in technology_keys:
        return "TECHNOLOGIES"
    # Grand Monuments (docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md).
    # Every loc-bearing key the system adds carries the gm_ prefix: modifiers
    # (some end in _add-like tokens), skin names ("gm_skin_faith_*", which would
    # otherwise match "religion"-style rules), JE lines and tooltips. Tested
    # before every substring rule so the whole family stays in one file.
    if key.startswith("gm_"):
        return "MISCELLANEOUS"
    # Tax-code engine probes (docs/testing/tax-code-probes.md), a temporary
    # harness kept in te_debug_tax_l_english.yml until it is removed. Tested
    # before the `law_` and `_add` rules, which would take the carrier law and
    # `te_tp_action_grain_add` to LAWS and MODIFIERS.
    if key.startswith(("te_tp_", "amendment_te_tp_", "law_te_probe_carrier")):
        return "DEBUG_TAX"
    # The legislated tax code (docs/superpowers/specs/2026-09-29-legislated-tax-code-design.md).
    # `te_tax_*` keys, its game rule and options and its carrier law file in
    # te_tax_l_english.yml; the amendments gen_tax_code.py generates, one per
    # instrument and index, file in te_tax_generated_l_english.yml, which the
    # generator writes. A later generator-owned key family adds its prefix to
    # the second rule. Both are tested before the `setting_`/`rule_`, `law_`,
    # `_add` and `_desc` rules, which would scatter the family over
    # te_game_rules, te_laws, te_modifiers and te_concepts. Its journal entry's
    # name, description and status keys (`je_tax_code*`) file here too, ahead of
    # the `je_` rule. Generator-owned `te_tax_` families (plan Task 13): the
    # interest groups' view bands and the staple offers' lines.
    if key.startswith(("amendment_te_tax_", "te_tax_ig_view_", "te_tax_offer_untax_", "te_tax_tt_offer_untax_")):
        return "TAX_GENERATED"
    if key.startswith(("te_tax_", "rule_te_tax_", "setting_te_tax_", "law_te_tax_code", "je_tax_code")):
        return "TAX"
    if key.startswith(("te_budget_chart_", "country_te_budget_")):
        return "BUDGET"
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
    if key.startswith(("institution_", "INSTITUTION_FUNDING_LEVEL_", "NO_INSTITUTION_")):
        return "INSTITUTIONS"
    # Families whose members would otherwise split across files. The nuclear
    # deterrence tooltips (`nd_tt_nd_hardening_add` / `_subtract`) must be
    # tested before the `_add` rule below, or the step-up half lands in
    # te_modifiers_l_english.yml. A war goal's engine-implicit suite
    # (find_war_goal_keys) has four-token bases, so its `_desc` halves would
    # fall to CONCEPTS while the names stay in MISCELLANEOUS.
    if key.startswith(("nd_tt_", "war_goal_")):
        return "MISCELLANEOUS"
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
    # The state panel's Homeland Dynamics lines: three-token section headers
    # (`TE_HOMELAND_CREATION`) would otherwise fall to CONCEPTS while their
    # longer siblings stay in MISCELLANEOUS.
    if key.startswith("TE_HOMELAND_"):
        return "MISCELLANEOUS"
    # The nuclear taboo (docs/superpowers/specs/2026-09-26-nuclear-taboo-design.md).
    # Every loc-bearing key it adds — static modifiers, the decision, event
    # options, tooltips, the panel's breakdown lines — carries the nd_taboo_
    # prefix. Four-token bases (`nd_taboo_possession_cost`) would otherwise land
    # in MISCELLANEOUS while their `_desc` fell to CONCEPTS.
    if key.startswith("nd_taboo_"):
        return "MISCELLANEOUS"
    # The mod's decisions that place or advance a system's building
    # (Establish a Strategic Reserve, Found a Space Program, the space
    # missions): names, `_desc` halves and their tooltips. Four-token names
    # would land in MISCELLANEOUS and their `_desc` halves in CONCEPTS.
    if key.startswith("te_decision_"):
        return "MISCELLANEOUS"
    # Internal resettlement (the Settlement Authority): static modifiers,
    # tooltips and the Declaration splice line. Four-token names would land in
    # MISCELLANEOUS and their `_desc` halves in CONCEPTS; two- and three-token
    # ones would all fall to CONCEPTS, away from the rest of the family.
    if key.startswith("resettlement_"):
        return "MISCELLANEOUS"
    # Resource Transition (#660): the Fossil Transition section, its
    # triggers and effects, and the Transition Assistance modifier. Short keys
    # (`rt_btn_start`, `rt_sect_transition`) and `_desc` halves would go to
    # CONCEPTS and the rest to MISCELLANEOUS; keep the family together.
    if key.startswith("rt_"):
        return "MISCELLANEOUS"
    # Collective Governance government types and amendments (law_direct_democracy):
    # four-token bases (`gov_collective_noble_commonwealth`,
    # `amendment_collective_direct_democracy`) would otherwise split, the name
    # to MISCELLANEOUS and the `_desc` to CONCEPTS. File the whole family with
    # the other government-type and amendment loc.
    if key.startswith(("gov_collective_", "gov_direct_democracy", "amendment_collective_")):
        return "CONCEPTS"
    # Climate event modifiers (`climate_crisis_emergency_modifier`,
    # `climate_survival_footing_modifier`, ...): four-token names would land in
    # MISCELLANEOUS and their `_desc` halves in CONCEPTS, while the three-token
    # ones already sit in CONCEPTS. Keep the whole family there.
    if key.startswith("climate_"):
        return "CONCEPTS"
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


def _render_loc_file(sections):
    """Return a categorised loc file's bytes: UTF-8 BOM, LF line endings.

    *sections* is a list of tuples: [(section_name, {key: value}), …]
    """
    lines = ["l_english:\n"]
    for section_name, entries in sections:
        if not entries:
            continue
        lines.append(f"\n#\n# {section_name}\n#\n")
        for key in sorted(entries.keys()):
            lines.append(f" {key}:{entries[key]}\n")
    return "".join(lines).encode("utf-8-sig")


def _write_loc_file(path, sections):
    """Write a categorised loc file (see `_render_loc_file`)."""
    with open(path, "wb") as f:
        f.write(_render_loc_file(sections))


# ---------------------------------------------------------------------------
# Explicit-usage scanner
# ---------------------------------------------------------------------------

# The game folders whose files can name a loc key (common/customizable_localization/
# included). The rest of the repo is left out: a word in prose in a docs dump
# counted as a reference, and gitignored files (a .venv, the generated
# docs/engine/commented_vanilla_*.txt) would make a local run disagree with CI's
# `--check`. gfx/ is left out because no file there names a loc key and CI's
# checks job does not check it out.
_CONTENT_DIRS = ("common", "events", "gui", "map_data")


def find_used_keys_explicitly(directory):
    """Finds every token in the .txt / .yml / .gui files of the game folders."""
    used_keys = set()
    for content_dir in _CONTENT_DIRS:
        for root, _, files in os.walk(os.path.join(directory, content_dir)):
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


def loc_value_refs(value):
    """Return the loc keys a loc value renders by name."""
    found = re.findall(r"[\$@!](\w+)[\$@!#|]", value)
    # `$key$` / `$key|fmt$` splices. Event-style keys contain `.` and some
    # notification keys `-`, which the \w+ pattern above cannot match.
    found.extend(re.findall(r"\$([\w.\-]+)(?:\|[^$]*)?\$", value))
    found.extend(m[1] for m in re.findall(r"\[\w+\.Get(Named)?(\w+)", value))
    found.extend(find_quoted_loc_args(value))
    # Embedded tooltips: `#tooltip:[X.GetTooltipTag],KEY` (and the
    # `;tooltip:` / bare `#tooltip:KEY` forms) render KEY on hover.
    found.extend(re.findall(r"tooltip:(?:[^,\s\"]+,)?(\w+)", value))
    return found


# ---------------------------------------------------------------------------
# Main organiser
# ---------------------------------------------------------------------------

def build_output_plan(project_directory):
    """Read all loc and categorise it: `{filename: [(section, {key: value}), …]}`.

    This is what `organize_all` writes and `find_drift` compares against.
    """
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
        find_war_goal_keys,
    ]
    for func in parser_functions:
        used_keys.update(func(project_directory))
    used_keys.update(find_parameterized_keys(project_directory, all_keys))

    technology_keys = find_technology_keys(project_directory)
    treaty_article_of = treaty_article_families(project_directory)

    # Overrides in replace/ are never organised, but an override's value can
    # name mod keys (a `$splice$` or a SelectLocalization argument), so those
    # count as used.
    replace_dir = os.path.join(loc_dir, "replace")
    if os.path.isdir(replace_dir):
        for fname in sorted(os.listdir(replace_dir)):
            if fname.endswith(".yml"):
                for value in _read_loc_file(os.path.join(replace_dir, fname)).values():
                    used_keys.update(k for k in loc_value_refs(value) if k in all_keys)

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
                found = loc_value_refs(all_loc[key])
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
        cat = categorize_key(key, technology_keys, treaty_article_of)
        if (
            key in unused_keys
            and cat not in HARNESS_CATEGORIES
            and cat not in GENERATED_CATEGORIES
        ):
            cat = "UNUSED"
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
            output_plan[fname] = [(section_label(cat), categorized[cat])]
    return output_plan


def organize_all(project_directory, dry_run=False):
    """Read all loc, categorise, write per-category output files."""
    loc_dir = os.path.join(project_directory, "localization", "english")
    output_plan = build_output_plan(project_directory)

    # ── 6. Report ─────────────────────────────────────────────────────────
    total_keys = sum(
        sum(len(d) for _, d in secs) for secs in output_plan.values()
    )
    print(f"\nCategorised {total_keys} keys into {len(output_plan)} files:")
    for fname in sorted(output_plan):
        sections = output_plan[fname]
        n = sum(len(d) for _, d in sections)
        sec_names = ", ".join(s.splitlines()[0] for s, _ in sections)
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


def find_drift(project_directory):
    """Describe what `organize_all` would change, one line per finding; [] if nothing.

    Writes nothing. Lists the keys a run would move between files (grouped by
    source and destination), keys held in more than one file, and the files it
    would create, delete or only re-sort.
    """
    loc_dir = os.path.join(project_directory, "localization", "english")
    with contextlib.redirect_stdout(io.StringIO()):
        output_plan = build_output_plan(project_directory)
    expected = {fname: _render_loc_file(secs) for fname, secs in output_plan.items()}
    target = {
        key: fname
        for fname, secs in output_plan.items()
        for _, entries in secs
        for key in entries
    }

    actual = {}
    homes = defaultdict(list)  # key -> the files holding it now, in read order
    for fname in sorted(os.listdir(loc_dir)):
        path = os.path.join(loc_dir, fname)
        if not (fname.endswith(".yml") and os.path.isfile(path)):
            continue
        with open(path, "rb") as f:
            actual[fname] = f.read()
        for key in _read_loc_file(path):
            homes[key].append(fname)

    lines, touched = [], set()
    moves = defaultdict(list)
    for key in sorted(target):
        now = homes[key]
        if len(now) > 1:
            # The merge is a dict.update in file-name order, so the last copy wins.
            lines.append(
                f"{key}: in {', '.join(now)}; a run keeps one copy, in "
                f"{target[key]}, with the text from {now[-1]}"
            )
            touched.update(now + [target[key]])
        elif now != [target[key]]:
            moves[(now[0], target[key])].append(key)
            touched.update((now[0], target[key]))
    for (src, dst), keys in sorted(moves.items()):
        shown = ", ".join(keys[:5])
        if len(keys) > 5:
            shown += f", and {len(keys) - 5} more"
        lines.append(f"{len(keys)} key(s) would move {src} -> {dst}: {shown}")
    for fname in sorted(set(actual) | set(expected)):
        if fname not in expected:
            lines.append(f"{fname}: would be deleted")
        elif fname not in actual:
            lines.append(f"{fname}: would be created")
        elif actual[fname] != expected[fname] and fname not in touched:
            lines.append(f"{fname}: would be re-sorted or reformatted")
    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def regenerate(mod_state=None):
    """Auto-run entrypoint invoked by mod_state_server post-load."""
    with contextlib.redirect_stdout(io.StringIO()):
        organize_all(mod_path, dry_run=False)


def main():
    parser = argparse.ArgumentParser(
        description="Organize mod localization into per-category files.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the output plan without writing any files.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; exit 1 if a run would change any loc file (CI).",
    )
    args = parser.parse_args()
    if args.check:
        drift = find_drift(mod_path)
        if not drift:
            print("localization/english/ matches organize_loc.py's output.")
            return 0
        print("localization/english/ does not match organize_loc.py's output:")
        for line in drift:
            print(f"  {line}")
        print(
            "\nRun `python3 organize_loc.py` and commit every file it changes, "
            "deletions included. A new key prefix may need a categorize_key rule "
            "(docs/auto_generated_files.md)."
        )
        return 1
    organize_all(mod_path, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
