#!/usr/bin/env python3
"""Retrofit extra-law events with domain-thematic modifiers.

For each (event_id, option_letter, domain_modifier) in RETROFIT_MAP,
finds the option block matching `name = extra_law_events.<id>.<letter>`
and replaces its secondary-effect block (add_radicals / add_loyalists /
scope:opposing_ig / ig:X ?= ... ig:Y ?= ...) with a single
`add_modifier = { name = <domain> days = normal_modifier_time }` line.

The `add_enactment_modifier` and `add_enactment_setback` lines are
preserved; only the formulaic secondary effect is swapped.
"""

import re
import sys
from pathlib import Path

EVENTS_FILE = Path("events/extra_law_events.txt")

# (event_id, option_letter, domain_modifier_name)
# Distribution: aim for ~50/50 A/B split across ~52 retrofits.
RETROFIT_MAP = [
    # ----- Advance events (.1-.24): swap one option, mixed A/B for distribution.
    # Domain effect placement follows narrative: which option NATURALLY produces this effect?
    (1,  "a", "finreg_interest_rate_hike"),         # push through despite bankers → rates up
    (2,  "b", "finreg_banking_stability"),          # depositor protections → stability
    (3,  "b", "monpol_currency_stability"),         # cautious gold compromise
    (4,  "a", "monpol_currency_devaluation"),       # aggressive printing → devalues
    (5,  "a", "te_legitimacy_drain"),               # push surveillance → legitimacy drain
    (6,  "a", "te_research_speed_boost"),           # let viral campaign succeed → info/research surge
    (7,  "b", "te_research_speed_boost"),           # genetics compromise → research
    (8,  "a", "antitrust_market_competition_boost"),# antitrust public win
    (9,  "a", "te_research_speed_chill"),           # IP piracy crackdown chills innovation
    (10, "a", "te_military_morale_drain"),          # atrocity exposure hurts morale
    (11, "b", "te_military_morale_boost"),          # military pushback - compromise rallies
    (12, "b", "crimjust_radicalism_uptick"),        # crimjust reform compromise → unrest
    (13, "a", "langpol_assimilation_boost"),        # force unified language → assimilation push
    (14, "a", "te_legitimacy_drain"),               # donor scandal push → legitimacy loss
    (15, "a", "te_authority_boost"),                # push central authority
    (16, "b", "augment_health_panic"),              # augment ethics relaxed
    (17, "a", "inherit_wealth_consolidation"),      # inheritance push → consolidation
    (18, "a", "lgbtq_social_progress"),             # lgbtq push
    (19, "a", "famrep_birth_rate_boost"),           # pronatalist push
    (20, "b", "te_legitimacy_boost"),               # whistleblower transparency
    (21, "a", "minrights_majority_grievance"),      # affirmative action push → majority grievance
    (22, "a", "welfare_investment_chill"),          # welfare push → investor caution
    (23, "b", "te_research_speed_boost"),           # technocrat showcase
    (24, "b", "te_legitimacy_boost"),               # popular assembly → legitimacy

    # ----- Stall events (.37-.60): swap Option B (drag path) replacing add_radicals.
    # Skip 6 systems for ~18 retrofits.
    (37, "b", "finreg_interest_rate_hike"),
    (38, "b", "finreg_banking_stability"),
    (39, "b", "monpol_currency_stability"),
    (40, "b", "monpol_currency_devaluation"),
    # skip 41 (privacy)
    (42, "b", "te_research_speed_chill"),
    (43, "b", "augment_health_panic"),              # genetics stall → health panic
    (44, "b", "antitrust_market_competition_boost"),
    # skip 45 (ip)
    (46, "b", "te_military_morale_drain"),
    (47, "b", "te_military_morale_drain"),
    (48, "b", "crimjust_radicalism_uptick"),
    (49, "b", "langpol_assimilation_boost"),
    (50, "b", "te_legitimacy_drain"),
    # skip 51 (statepower)
    (52, "b", "augment_health_panic"),
    (53, "b", "inherit_wealth_consolidation"),
    # skip 54 (lgbtq)
    (55, "b", "famrep_birth_rate_boost"),
    (56, "b", "te_legitimacy_drain"),               # whistleblower stall → drain
    (57, "b", "minrights_majority_grievance"),
    (58, "b", "welfare_investment_chill"),
    # skip 59 (govprin tech)
    (60, "b", "te_authority_drain"),                # popular-assembly stall → authority drain

    # ----- Debate events (.61-.84): alternate A/B per system.
    # Each event has two paired IG-approval blocks; we replace ONE option's
    # whole IG-block with the domain modifier (other option keeps its IG pair).
    (61, "a", "finreg_interest_rate_hike"),         # industry-consultation A → bankers happy, rates up
    (62, "b", "finreg_banking_stability"),
    (63, "a", "monpol_currency_stability"),
    (64, "b", "monpol_currency_devaluation"),
    (65, "a", "te_legitimacy_drain"),               # privacy debate
    (66, "a", "te_research_speed_boost"),           # internet freedom debate
    (67, "a", "te_research_speed_boost"),
    (68, "a", "antitrust_market_competition_boost"),
    (69, "a", "te_research_speed_chill"),
    (70, "a", "te_military_morale_drain"),
    (71, "a", "te_military_morale_boost"),
    (72, "b", "crimjust_radicalism_uptick"),
    (73, "a", "langpol_assimilation_boost"),
    (74, "b", "te_legitimacy_boost"),               # electfin hard-caps → legitimacy
    # skip 75 (statepower)
    (76, "a", "augment_health_panic"),
    (77, "a", "inherit_wealth_consolidation"),
    (78, "b", "lgbtq_social_progress"),
    (79, "a", "famrep_birth_rate_boost"),
    (80, "b", "te_legitimacy_boost"),               # rti transparency
    (81, "a", "minrights_majority_grievance"),
    (82, "b", "welfare_investment_chill"),
    (83, "a", "te_research_speed_boost"),           # govprin tech
    (84, "b", "te_legitimacy_boost"),               # direct voting → legitimacy
]


def find_option_block(text: str, event_id: int, option: str):
    """Return (start, end) of the option block in `text`."""
    # The option block opens with `option = { ... name = extra_law_events.<id>.<opt>`
    # and closes with a matching `}`. We find the option header first, then walk
    # backward to find the `option = {` and forward to its closing brace.
    name_marker = f"name = extra_law_events.{event_id}.{option}"
    name_pos = text.find(name_marker)
    if name_pos < 0:
        return None
    # Walk backward to find the opening `option = {` that contains this name
    opt_open = text.rfind("option = {", 0, name_pos)
    if opt_open < 0:
        return None
    # Walk forward from opt_open's `{` to find matching close
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
    # add_loyalists / add_radicals (single-line or multi-line; greedy on inner content
    # but [^{}] guarantees we don't escape the brace block).
    re.compile(
        r"\n\t+add_(?:loyalists|radicals)\s*=\s*\{[^{}]*\}",
        re.DOTALL,
    ),
    # scope:<X>_ig = { add_modifier = { ... ig_approval_*_modifier ... } }
    # (multi-line). Matches opposing_ig, devout_ig, industrialists_ig, etc.
    # Needs to skip past the inner add_modifier braces — use a 2-deep match.
    re.compile(
        r"\n\t+scope:[a-z_]+_ig\s*=\s*\{[^{}]*\{[^{}]*?ig_approval_(?:positive|negative)_modifier[^{}]*?\}[^{}]*\}",
        re.DOTALL,
    ),
    # ig:<ig_X> ?= { add_modifier = { ... ig_approval_*_modifier ... } }
    # (typically single-line in debate events).
    re.compile(
        r"\n\t+ig:ig_[a-z_]+\s*\?=\s*\{[^{}]*\{[^{}]*?ig_approval_(?:positive|negative)_modifier[^{}]*?\}[^{}]*\}",
        re.DOTALL,
    ),
]


def retrofit_option(text: str, event_id: int, option: str, domain: str):
    """Replace the secondary-effect block within the option with a domain modifier."""
    span = find_option_block(text, event_id, option)
    if span is None:
        return text, f"NOT FOUND: event {event_id} option {option}"
    start, end = span
    block = text[start:end]

    # Find all secondary effect spans within this block
    matches = []
    for pat in SECONDARY_EFFECT_PATTERNS:
        for m in pat.finditer(block):
            matches.append((m.start(), m.end()))

    # Some modifiers carry a base-1 contract and require a multiplier for GDP scaling.
    mult_suffix = ""
    if domain in ("monpol_currency_stability", "monpol_currency_devaluation"):
        mult_suffix = " multiplier = sv_money_flow_event_small"

    if matches:
        # Replace the FIRST secondary effect with the domain modifier line; REMOVE
        # any other matched secondary effects (so the option's only side-effect is
        # the single domain modifier — no orphan add_radicals/ig_approval lines).
        # For debate events with two paired ig blocks, both get removed.
        matches.sort()
        rep_start, rep_end = matches[0]
        indent_match = re.match(r"\n(\t+)", block[rep_start:])
        indent = indent_match.group(1) if indent_match else "\t\t"
        replacement = (
            f"\n{indent}# Domain side-effect\n"
            f"{indent}add_modifier = {{ name = {domain} days = normal_modifier_time{mult_suffix} }}"
        )
        # Walk matches in REVERSE order so index positions stay valid as we shrink.
        new_block = block
        for i in range(len(matches) - 1, -1, -1):
            ms, me = matches[i]
            if i == 0:
                new_block = new_block[:ms] + replacement + new_block[me:]
            else:
                new_block = new_block[:ms] + new_block[me:]
        msg = f"OK: event {event_id} option {option} → {domain} (swap×{len(matches)})"
    else:
        # Bare option (only add_enactment_modifier). Insert domain modifier before
        # the option's closing `}`.
        aem_match = re.search(r"\n(\t+)add_enactment_modifier", block)
        indent = aem_match.group(1) if aem_match else "\t\t"
        close_pos = block.rfind("}")
        if close_pos < 0:
            return text, f"NO CLOSE BRACE: event {event_id} option {option}"
        insertion = (
            f"{indent}# Domain side-effect\n"
            f"{indent}add_modifier = {{ name = {domain} days = normal_modifier_time{mult_suffix} }}\n"
        )
        line_start = block.rfind("\n", 0, close_pos) + 1
        new_block = block[:line_start] + insertion + block[line_start:]
        msg = f"OK: event {event_id} option {option} → {domain} (insert)"

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
    EVENTS_FILE.write_text(text, encoding="utf-8")
    for line in report:
        print(line)
    ok = sum(1 for r in report if r.startswith("OK:"))
    print(f"\n=== {ok}/{len(RETROFIT_MAP)} options retrofitted ===")


if __name__ == "__main__":
    main()
