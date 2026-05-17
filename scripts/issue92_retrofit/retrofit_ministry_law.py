#!/usr/bin/env python3
"""Retrofit ministry-law events with domain-thematic modifiers.

Mirrors retrofit_extra_law.py — see that script for the design notes.
For each (event_id, option_letter, domain_modifier) in RETROFIT_MAP,
finds the option block matching `name = ministry_law_events.<id>.<letter>`
and replaces (or inserts) its secondary-effect block.
"""

import re
import sys
from pathlib import Path

EVENTS_FILE = Path("events/ministry_law_events.txt")

# (event_id, option_letter, domain_modifier_name)
# Ministry events: 19 systems × 3 flavors (advance / stall / debate).
# Target ~40 retrofits with ~50/50 A/B split.
RETROFIT_MAP = [
    # ----- Advance events (.1-.19): mixed A/B.
    (1,  "b", "te_legitimacy_boost"),               # staffing — professional path → legitimacy
    (2,  "a", "te_authority_boost"),                # budget — push budget → authority
    (3,  "b", "te_authority_boost"),                # turf — consolidation tradeoff
    # skip 4 (dissolution — direct effect later in debate)
    (5,  "a", "te_military_morale_boost"),          # war generals advance
    (6,  "b", "te_diplomatic_relations_boost"),     # fa diplomacy compromise
    (7,  "b", "te_research_speed_boost"),           # commerce → innovation
    (8,  "b", "te_legitimacy_boost"),               # culture patronage → legitimacy
    # skip 9 (labor — context-sensitive, would need both directions)
    (10, "a", "ministry_env_pollution_reduction"),  # env smokestacks → reduce pollution
    (11, "a", "te_authority_boost"),                # intel shadow → authority
    (12, "b", "te_diplomatic_relations_boost"),     # refugee crisis humanitarian → diplomacy
    (13, "a", "te_legitimacy_boost"),               # prop loudspeaker push → legitimacy
    (14, "a", "te_research_speed_boost"),           # sci laboratory advance
    (15, "a", "te_authority_boost"),                # thought watchers advance
    (16, "a", "ministry_consumer_protection"),      # consumer tainted strict
    (17, "b", "ministry_urban_housing_strain"),     # urban sprawl compromise
    (18, "b", "te_legitimacy_boost"),               # religion pulpit
    (19, "b", "te_diplomatic_relations_boost"),     # aid distant compromise

    # ----- Stall events (.20-.38): mostly Option B (drag path).
    (20, "b", "te_legitimacy_drain"),               # staffing stall
    (21, "b", "te_authority_drain"),                # budget stall
    # skip 22 (turf)
    # skip 23 (dissolution stall)
    (24, "b", "te_military_morale_drain"),
    (25, "b", "te_diplomatic_relations_drain"),
    (26, "b", "welfare_investment_chill"),          # commerce stall → investor chill
    # skip 27 (culture)
    (28, "b", "te_legitimacy_drain"),               # labor stall
    (29, "b", "ministry_env_pollution_reduction"),  # env stall — limited mitigation
    (30, "b", "te_legitimacy_drain"),               # intel stall
    (31, "b", "te_diplomatic_relations_drain"),     # refugee stall
    (32, "b", "te_legitimacy_drain"),               # prop stall
    (33, "b", "te_research_speed_chill"),           # sci lab stall
    (34, "b", "te_authority_drain"),                # thought watchers stall
    (35, "b", "ministry_consumer_protection"),      # consumer stall
    (36, "b", "ministry_urban_housing_strain"),     # urban sprawl stall
    (37, "b", "te_legitimacy_drain"),               # religion stall
    (38, "b", "te_diplomatic_relations_drain"),     # aid stall

    # ----- Debate events (.39-.57): alternate A/B per system.
    (39, "a", "te_legitimacy_boost"),               # staffing professional
    (40, "a", "te_authority_boost"),                # budget lean — Option A frugal
    # 40 Option B handled separately for one-shot treasury below
    (41, "b", "te_authority_boost"),                # turf consolidation B
    (42, "a", "te_authority_boost"),                # dissolution swift — efficient
    (43, "a", "te_military_morale_boost"),          # war civilian-led
    (44, "b", "te_diplomatic_relations_drain"),     # fa hawkish vs dovish
    (45, "a", "welfare_investment_chill"),          # commerce protectionist
    (46, "b", "te_legitimacy_boost"),               # culture independent grants
    # skip 47 (labor pro_capital vs pro_labor — needs paired domain)
    (48, "a", "ministry_env_pollution_reduction"),  # env strict_mandatory
    (49, "a", "te_authority_boost"),                # intel domestic_focus
    (50, "b", "te_diplomatic_relations_boost"),     # refugee restrictive vs generous
    (51, "a", "te_legitimacy_drain"),               # prop state_controlled
    (52, "a", "te_research_speed_boost"),           # sci basic_focus
    (53, "b", "te_authority_boost"),                # thought restrictive
    (54, "a", "ministry_consumer_protection"),      # consumer strict
    # skip 55 (urban density vs sprawl — both have plausible domain effects)
    (56, "a", "te_legitimacy_boost"),               # religion established_faith
    (57, "b", "te_diplomatic_relations_boost"),     # aid humanitarian
]

# Special one-shot direct-effect retrofits (treasury changes, not modifiers).
# Use sv_treasury_event_<tier> for country-size scaling per the canonical pattern.
ONESHOT_RETROFITS = [
    # ministry_budget debate Option B ("generous") — treasury hit, ~5% of reserves
    (40, "b", "negate(sv_treasury_event_medium)", "budget — generous funding draws down treasury"),
    # ministry_dissolution debate Option B — treasury savings, ~2% of reserves
    (42, "b", "sv_treasury_event_small", "dissolution — swift cuts free up treasury"),
]


def find_option_block(text: str, event_id: int, option: str):
    name_marker = f"name = ministry_law_events.{event_id}.{option}"
    name_pos = text.find(name_marker)
    if name_pos < 0:
        return None
    opt_open = text.rfind("option = {", 0, name_pos)
    if opt_open < 0:
        return None
    brace_pos = text.find("{", opt_open)
    depth = 1
    i = brace_pos + 1
    while i < len(text) and depth > 0:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return (opt_open, i + 1)
        i += 1
    return None


SECONDARY_EFFECT_PATTERNS = [
    re.compile(
        r"\n\t+add_(?:loyalists|radicals)\s*=\s*\{[^{}]*?\n\t+\}",
        re.DOTALL,
    ),
    re.compile(
        r"\n\t+scope:opposing_ig\s*=\s*\{\s*\n[^{}]*?add_modifier\s*=\s*\{[^{}]*?ig_approval_(?:positive|negative)_modifier[^{}]*?\n\t+\}\s*\n\t+\}",
        re.DOTALL,
    ),
    re.compile(
        r"\n\t+ig:ig_[a-z_]+\s*\?=\s*\{\s*add_modifier\s*=\s*\{[^{}]*?ig_approval_(?:positive|negative)_modifier[^{}]*?\}\s*\}",
    ),
]


def build_payload(domain: str, indent: str, comment_label: str = "Domain side-effect"):
    mult_suffix = ""
    if domain in ("monpol_currency_stability", "monpol_currency_devaluation"):
        mult_suffix = " multiplier = sv_money_flow_event_small"
    return (
        f"{indent}# {comment_label}\n"
        f"{indent}add_modifier = {{ name = {domain} days = normal_modifier_time{mult_suffix} }}"
    )


def retrofit_option(text: str, event_id: int, option: str, domain: str):
    span = find_option_block(text, event_id, option)
    if span is None:
        return text, f"NOT FOUND: event {event_id} option {option}"
    start, end = span
    block = text[start:end]

    matches = []
    for pat in SECONDARY_EFFECT_PATTERNS:
        for m in pat.finditer(block):
            matches.append((m.start(), m.end()))

    if matches:
        matches.sort()
        rep_start, rep_end = matches[0]
        indent_match = re.match(r"\n(\t+)", block[rep_start:])
        indent = indent_match.group(1) if indent_match else "\t\t"
        payload = "\n" + build_payload(domain, indent)
        new_block = block[:rep_start] + payload + block[rep_end:]
        msg = f"OK: event {event_id} option {option} → {domain} (swap)"
    else:
        aem_match = re.search(r"\n(\t+)add_enactment_modifier", block)
        indent = aem_match.group(1) if aem_match else "\t\t"
        close_pos = block.rfind("}")
        if close_pos < 0:
            return text, f"NO CLOSE BRACE: event {event_id} option {option}"
        insertion = build_payload(domain, indent) + "\n"
        line_start = block.rfind("\n", 0, close_pos) + 1
        new_block = block[:line_start] + insertion + block[line_start:]
        msg = f"OK: event {event_id} option {option} → {domain} (insert)"

    new_text = text[:start] + new_block + text[end:]
    return new_text, msg


def retrofit_treasury(text: str, event_id: int, option: str, amount, comment: str):
    """`amount` may be a literal int or a string like 'sv_treasury_event_small' /
    'negate(sv_treasury_event_medium)'."""
    span = find_option_block(text, event_id, option)
    if span is None:
        return text, f"NOT FOUND (treasury): event {event_id} option {option}"
    start, end = span
    block = text[start:end]

    matches = []
    for pat in SECONDARY_EFFECT_PATTERNS:
        for m in pat.finditer(block):
            matches.append((m.start(), m.end()))

    aem_match = re.search(r"\n(\t+)add_enactment_modifier", block)
    indent = aem_match.group(1) if aem_match else "\t\t"

    if matches:
        matches.sort()
        rep_start, rep_end = matches[0]
        indent_match = re.match(r"\n(\t+)", block[rep_start:])
        indent = indent_match.group(1) if indent_match else indent
        payload = f"\n{indent}# Domain side-effect: {comment}\n{indent}add_treasury = {amount}"
        new_block = block[:rep_start] + payload + block[rep_end:]
        msg = f"OK: event {event_id} option {option} → add_treasury = {amount} (swap)"
    else:
        close_pos = block.rfind("}")
        if close_pos < 0:
            return text, f"NO CLOSE BRACE: event {event_id} option {option}"
        insertion = (
            f"{indent}# Domain side-effect: {comment}\n"
            f"{indent}add_treasury = {amount}\n"
        )
        line_start = block.rfind("\n", 0, close_pos) + 1
        new_block = block[:line_start] + insertion + block[line_start:]
        msg = f"OK: event {event_id} option {option} → add_treasury = {amount} (insert)"

    new_text = text[:start] + new_block + text[end:]
    return new_text, msg


def main():
    if not EVENTS_FILE.exists():
        print(f"ERROR: {EVENTS_FILE} not found", file=sys.stderr)
        sys.exit(1)
    text = EVENTS_FILE.read_text(encoding="utf-8")
    report = []
    for event_id, option, domain in RETROFIT_MAP:
        text, msg = retrofit_option(text, event_id, option, domain)
        report.append(msg)
    for event_id, option, amount, comment in ONESHOT_RETROFITS:
        text, msg = retrofit_treasury(text, event_id, option, amount, comment)
        report.append(msg)
    EVENTS_FILE.write_text(text, encoding="utf-8")
    for line in report:
        print(line)
    ok = sum(1 for r in report if r.startswith("OK:"))
    total = len(RETROFIT_MAP) + len(ONESHOT_RETROFITS)
    print(f"\n=== {ok}/{total} options retrofitted ===")


if __name__ == "__main__":
    main()
