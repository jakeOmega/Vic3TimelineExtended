"""
Replaces has_technology_researched triggers in scripted buttons and power bloc principles
with custom boolean modifier checks, and adds those modifiers to the relevant technologies.

This makes the technology's effects on scripted buttons and power bloc principles visible
when browsing the tech tree.

ADDITIVE AND IDEMPOTENT. Every step below only ever *adds* what is missing, and no file is
opened for writing unless its content actually changed. Running this on a clean tree must
leave `git status` clean — `test_add_tech_modifiers.py` pins that.

Consequences worth knowing before you edit the tables:

* `common/modifier_type_definitions/tech_gate_modifier_types.txt` is **hand-maintained**,
  not owned by this script. It carries definitions this script knows nothing about (the
  `country_sr_*_program_bool` space-program block, without which the space race silently
  never activates — see docs/guides/scripting_best_practices.md). The script used to
  rewrite the file from scratch with `open(..., 'w')`, which deleted that block on every
  run; it now merges in missing definitions and leaves everything else alone.
* Because the merge is additive, **deleting** a tech gate is a two-place edit: drop it from
  the tables here *and* from the modifier-type file / tech files / loc. Removing it from
  the tables alone just makes this script stop re-adding it; removing it from the file
  alone means the next run resurrects it.
* Localization is only emitted for keys that exist in **no** `localization/english/*.yml`
  file. The hardcoded `loc_name` / `loc_desc` strings below are stale placeholders for
  brand-new gates, not the source of truth for the ones already shipped.

Usage: python3 scripts/generators/add_tech_modifiers.py [--root PATH]
"""

import argparse
import os
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from path_constants import mod_path  # noqa: E402

# ============================================================================
# CONFIGURATION: Maps each technology to its modifier(s) and what it gates
# ============================================================================

# For power bloc principles: one modifier per unique technology
# { tech_name: (modifier_name, loc_name, loc_desc) }
PRINCIPLE_TECH_MODIFIERS = {
    'urbanization': (
        'country_urbanization_pb_principles_bool',
        'Enables Power Bloc Urban Planning Principles',
        'Unlocks Tiers 1-2 Urban Planning power bloc principles.',
    ),
    'pharmaceuticals': (
        'country_pharmaceuticals_pb_principles_bool',
        'Enables Power Bloc Healthcare Principles',
        'Unlocks Tiers 1-3 Healthcare power bloc principles.',
    ),
    'mass_surveillance': (
        'country_mass_surveillance_pb_principles_bool',
        'Enables Advanced Police Coordination Principles',
        'Unlocks Tier 4 Police Coordination power bloc principles.',
    ),
    'modern_tools': (
        'country_modern_tools_pb_principles_bool',
        'Enables Advanced Construction Principles',
        'Unlocks Tier 4 Construction power bloc principles.',
    ),
    'modern_skyscrapers': (
        'country_modern_skyscrapers_pb_principles_bool',
        'Enables Advanced Transport Principles',
        'Unlocks Tier 4 Transport power bloc principles.',
    ),
    'advanced_agricultural_statistics': (
        'country_advanced_agri_stats_pb_principles_bool',
        'Enables Advanced Rural Principles',
        'Unlocks Tier 4 Rural power bloc principles.',
    ),
    'television': (
        'country_television_pb_principles_bool',
        'Enables Advanced External Trade Principles',
        'Unlocks Tier 4 External Trade power bloc principles.',
    ),
    'marketing_research': (
        'country_marketing_research_pb_principles_bool',
        'Enables Advanced Cultural Unity Principles',
        'Unlocks Tier 4 Cultural Unity power bloc principles.',
    ),
    'modern_vaccines': (
        'country_modern_vaccines_pb_principles_bool',
        'Enables Advanced Healthcare and Food Principles',
        'Unlocks Tier 4 Healthcare and Tier 4 Food Standardization power bloc principles.',
    ),
    'mass_media': (
        'country_mass_media_pb_principles_bool',
        'Enables Advanced Power Bloc Principles (Media)',
        'Unlocks Tier 4 power bloc principles for Creative Legislature, Freedom of Movement, Divine Economics, Exploitation, Sacred Civics, Ideological Truth, Education, Diplomacy, Artistic Expression, and Shared Canon.',
    ),
    'keynesian_economics': (
        'country_keynesian_pb_principles_bool',
        'Enables Keynesian Power Bloc Principles',
        'Unlocks Tier 4 Internal Trade and Tier 4 Foreign Investment power bloc principles.',
    ),
    'combined_arms': (
        'country_combined_arms_pb_principles_bool',
        'Enables Advanced Military Power Bloc Principles',
        'Unlocks Tier 4 Defensive Cooperation, Aggressive Coordination, Military Training, and Engineering & Logistics power bloc principles.',
    ),
    'motorized_artillery': (
        'country_motorized_artillery_pb_principles_bool',
        'Enables Advanced Military Industry Principles',
        'Unlocks Tier 4 Military Industry power bloc principles.',
    ),
    'nuclear_weapons': (
        'country_nuclear_weapons_pb_principles_bool',
        'Enables Nuclear Power Bloc Principles',
        'Unlocks Tier 4 Advanced Research and Tiers 1-3 Global Security power bloc principles.',
    ),
    'rocketry': (
        'country_rocketry_pb_principles_bool',
        'Enables Advanced Vassalization Principles',
        'Unlocks Tier 4 Vassalization power bloc principles.',
    ),
    'sonar': (
        'country_sonar_pb_principles_bool',
        'Enables Advanced Naval Principles',
        'Unlocks Tier 4 Navy power bloc principles.',
    ),
    'intergovernmental_organizations': (
        'country_igo_pb_principles_bool',
        'Enables Advanced Market Unification Principles',
        'Unlocks Tier 4 Market Unification power bloc principles.',
    ),
    'public_works_programs': (
        'country_public_works_pb_principles_bool',
        'Enables Advanced Welfare Principles',
        'Unlocks Tier 4 Welfare power bloc principles.',
    ),
    'environmental_movement': (
        'country_env_movement_pb_principles_bool',
        'Enables Environmental Sustainability Principles',
        'Unlocks Tiers 1-3 Environmental Sustainability power bloc principles.',
    ),
    'modern_urban_planning': (
        'country_modern_urban_planning_pb_principles_bool',
        'Enables Modern Urban Planning Principles',
        'Unlocks Tier 3 Urban Planning and Tier 4 Companies power bloc principles.',
    ),
    'civil_rights_movement': (
        'country_civil_rights_pb_principles_bool',
        'Enables Advanced Cultural Plurality Principles',
        'Unlocks Tier 4 Cultural Plurality power bloc principles.',
    ),
    'decolonization': (
        'country_decolonization_pb_principles_bool',
        'Enables Advanced Colonial Offices Principles',
        'Unlocks Tier 4 Colonial Offices power bloc principles.',
    ),
    'green_revolution': (
        'country_green_revolution_pb_principles_bool',
        'Enables Cutting-Edge Rural Principles',
        'Unlocks Tier 5 Rural power bloc principles.',
    ),
    'ICBMs': (
        'country_icbm_pb_principles_bool',
        'Enables Cutting-Edge Military Industry Principles',
        'Unlocks Tier 5 Military Industry power bloc principles.',
    ),
    'tactical_nuclear_weapons': (
        'country_tactical_nukes_pb_principles_bool',
        'Enables Tactical Nuclear Power Bloc Principles',
        'Unlocks Tier 5 Vassalization and Tier 4 Global Security power bloc principles.',
    ),
    'anti_war_movement': (
        'country_anti_war_pb_principles_bool',
        'Enables Cutting-Edge Defensive Cooperation Principles',
        'Unlocks Tier 5 Defensive Cooperation power bloc principles.',
    ),
    'modern_pharmaceuticals': (
        'country_modern_pharma_pb_principles_bool',
        'Enables Cutting-Edge Healthcare Principles',
        'Unlocks Tier 5 Healthcare power bloc principles.',
    ),
    'cellular_networks': (
        'country_cellular_pb_principles_bool',
        'Enables Cutting-Edge External Trade Principles',
        'Unlocks Tier 5 External Trade power bloc principles.',
    ),
    'gene_splicing': (
        'country_gene_splicing_pb_principles_bool',
        'Enables Cutting-Edge Food Standardization Principles',
        'Unlocks Tier 5 Food Standardization power bloc principles.',
    ),
    'automated_surveillance': (
        'country_auto_surveillance_pb_principles_bool',
        'Enables Cutting-Edge Police Coordination Principles',
        'Unlocks Tier 5 Police Coordination power bloc principles.',
    ),
    'robotics': (
        'country_robotics_pb_principles_bool',
        'Enables Cutting-Edge Construction Principles',
        'Unlocks Tier 5 Construction power bloc principles.',
    ),
    'containerization': (
        'country_containerization_pb_principles_bool',
        'Enables Cutting-Edge Internal Trade Principles',
        'Unlocks Tier 5 Internal Trade power bloc principles.',
    ),
    'satellite_communications': (
        'country_satcom_pb_principles_bool',
        'Enables Cutting-Edge Market Unification Principles',
        'Unlocks Tier 5 Market Unification power bloc principles.',
    ),
    'knowledge_economy': (
        'country_knowledge_economy_pb_principles_bool',
        'Enables Cutting-Edge Advanced Research Principles',
        'Unlocks Tier 5 Advanced Research power bloc principles.',
    ),
    'network_centric_warfare': (
        'country_ncw_pb_principles_bool',
        'Enables Cutting-Edge Aggressive Coordination Principles',
        'Unlocks Tier 5 Aggressive Coordination power bloc principles.',
    ),
    'globalization': (
        'country_globalization_pb_principles_bool',
        'Enables Globalization Power Bloc Principles',
        'Unlocks Tier 5 Colonial Offices, Foreign Investment, Cultural Unity, Cultural Plurality, and Companies power bloc principles.',
    ),
    'world_wide_web': (
        'country_www_pb_principles_bool',
        'Enables Internet Power Bloc Principles',
        'Unlocks Tier 5 Creative Legislature, Freedom of Movement, Education, and Diplomacy power bloc principles.',
    ),
    'social_media': (
        'country_social_media_pb_principles_bool',
        'Enables Social Media Power Bloc Principles',
        'Unlocks Tier 5 Divine Economics, Exploitation, Sacred Civics, Ideological Truth, Welfare, Artistic Expression, and Shared Canon power bloc principles.',
    ),
    'clean_energy_technologies': (
        'country_clean_energy_pb_principles_bool',
        'Enables Advanced Environmental Sustainability Principles',
        'Unlocks Tiers 4-5 Environmental Sustainability power bloc principles.',
    ),
    'advanced_workflow_optimization': (
        'country_workflow_opt_pb_principles_bool',
        'Enables Advanced Urban Planning Principles',
        'Unlocks Tier 4 Urban Planning power bloc principles.',
    ),
    'digital_education': (
        'country_digital_ed_pb_principles_bool',
        'Enables Cutting-Edge Urban Planning Principles',
        'Unlocks Tier 5 Urban Planning power bloc principles.',
    ),
    'supply_chain_management': (
        'country_supply_chain_pb_principles_bool',
        'Enables Cutting-Edge Transport Principles',
        'Unlocks Tier 5 Transport power bloc principles.',
    ),
    'rapid_deployment_forces': (
        'country_rapid_deploy_pb_principles_bool',
        'Enables Rapid Deployment Power Bloc Principles',
        'Unlocks Tier 5 Global Security, Military Training, and Engineering & Logistics power bloc principles.',
    ),
    'missile_defense_systems': (
        'country_missile_defense_pb_principles_bool',
        'Enables Cutting-Edge Naval Principles',
        'Unlocks Tier 5 Navy power bloc principles.',
    ),
}

# For scripted buttons: one modifier per button
# { tech_name: [(modifier_name, loc_name, loc_desc), ...] }
# We need to track which button file and the exact has_technology_researched line
BUTTON_TECH_MODIFIERS = {
    'intergovernmental_organizations': [
        ('country_can_join_united_nations_bool', 'Enables Joining the United Nations', 'Enables the option to join the United Nations.'),
    ],
    'decolonization': [
        ('country_can_use_cultural_assimilation_bool', 'Enables Cultural Assimilation Policy', 'Enables the Cultural Assimilation policy for colonial empires.'),
    ],
    'keynesian_economics': [
        ('country_can_use_open_market_ops_bool', 'Enables Open Market Operations', 'Enables the Open Market Operations banking intervention.'),
        ('country_can_use_asset_relief_bool', 'Enables Asset Relief Program', 'Enables the Asset Relief Program banking intervention.'),
    ],
    'international_exchange_standards': [
        ('country_can_use_countercyclical_buffer_bool', 'Enables Countercyclical Buffer', 'Enables the Countercyclical Buffer banking intervention.'),
    ],
    'consumer_credit': [
        ('country_can_use_deposit_guarantee_bool', 'Enables Deposit Guarantee Expansion', 'Enables the Expand Deposit Guarantee banking intervention.'),
    ],
    'investment_banks': [
        ('country_can_use_emergency_liquidity_bool', 'Enables Emergency Liquidity', 'Enables the Emergency Liquidity Program banking intervention.'),
    ],
    'corporate_management': [
        ('country_can_use_export_credit_bool', 'Enables Export Credit Facility', 'Enables the Export Credit Facility banking intervention.'),
    ],
    'rural_electrification': [
        ('country_can_use_directed_credit_electrification_bool', 'Enables Directed Credit: Electrification & High Tech', 'Enables the Directed Credit: Electrification & High Tech banking intervention.'),
    ],
    'globalization': [
        ('country_can_use_bail_in_bool', 'Enables Bail-in Regime', 'Enables the Bail-in Regime banking intervention.'),
    ],
}

# Map of (button_file, button_name, tech_name) -> modifier_name
# This is needed because some techs have multiple buttons, we need to match the right one
BUTTON_SPECIFIC_MAP = [
    # UN buttons
    ('common/scripted_buttons/un_buttons.txt', 'un_join_button', 'intergovernmental_organizations', 'country_can_join_united_nations_bool'),
    # Colonial empire buttons
    ('common/scripted_buttons/colonial_empire_buttons.txt', 'ce_cultural_assimilation', 'decolonization', 'country_can_use_cultural_assimilation_bool'),
    # Banking buttons
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_open_market_ops', 'keynesian_economics', 'country_can_use_open_market_ops_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_countercyclical_buffer', 'international_exchange_standards', 'country_can_use_countercyclical_buffer_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_expand_deposit_guarantee', 'consumer_credit', 'country_can_use_deposit_guarantee_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_emergency_liquidity_program', 'investment_banks', 'country_can_use_emergency_liquidity_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_export_credit_facility', 'corporate_management', 'country_can_use_export_credit_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_asset_relief_program', 'keynesian_economics', 'country_can_use_asset_relief_bool'),
]

# Vanilla techs that need INJECT: in modified.txt (not defined in mod era files)
VANILLA_TECHS = {
    'mass_surveillance', 'urbanization', 'pharmaceuticals',
    'investment_banks', 'corporate_management', 'international_exchange_standards',
}

# Which era file each mod tech is defined in
# We'll detect this automatically

# ============================================================================
# STEP 1: Merge modifier type definitions
# ============================================================================

PRINCIPLE_SECTION_HEADER = '# Power bloc principle technology requirements'
BUTTON_SECTION_HEADER = '# Scripted button technology requirements'

# Only used when the modifier-type file does not exist at all. The live file's header
# carries the same warning; keep the two in sync if you reword either.
MODIFIER_TYPE_FILE_HEADER = (
    '# Boolean modifiers for technology-gated features.\n'
    '# These make technology requirements for scripted buttons and\n'
    '# power bloc principles visible in the tech tree.\n'
    '#\n'
    '# HAND-MAINTAINED. scripts/generators/add_tech_modifiers.py only appends\n'
    '# definitions missing from its tables; it never rewrites or prunes this file,\n'
    '# so unrelated blocks below are safe. Deleting a gate means removing it here\n'
    '# AND from that script\'s tables.\n'
)


def _definition_block(modifier_name):
    """One `boolean = yes` modifier-type definition, trailing blank line included."""
    return f'{modifier_name} = {{\n\tcolor = good\n\tboolean = yes\n}}\n\n'


def expected_modifier_definitions():
    """[(section_header, [modifier_name, ...]), ...] in this script's canonical order."""
    principles = [mod_name for _, (mod_name, _, _) in sorted(PRINCIPLE_TECH_MODIFIERS.items())]

    buttons, seen = [], set()
    for _, mods in sorted(BUTTON_TECH_MODIFIERS.items()):
        for mod_name, _, _ in mods:
            if mod_name not in seen:
                seen.add(mod_name)
                buttons.append(mod_name)

    return [(PRINCIPLE_SECTION_HEADER, principles), (BUTTON_SECTION_HEADER, buttons)]


def _top_level_keys(content):
    """Every `<key> = {` defined at column 0 — i.e. already-registered modifier types."""
    return set(re.findall(r'(?m)^(\S+)\s*=\s*\{', content))


def _section_end_index(content, header, later_headers):
    """Index just past the last entry of `header`'s section, or None if absent.

    A section runs from its own header to the next known section header, or to EOF.
    """
    start = content.find(header)
    if start == -1:
        return None
    end = len(content)
    for other in later_headers:
        other_start = content.find(other, start + len(header))
        if other_start != -1:
            end = min(end, other_start)
    return end


def merge_modifier_type_definitions(filepath):
    """Append any missing tech-gate boolean definitions to `filepath`. Returns True if written.

    Deliberately additive: the file is hand-maintained and holds definitions this script
    has no table entry for (notably the `country_sr_*_program_bool` space-program block,
    which the space race silently depends on). The previous implementation regenerated the
    whole file with `open(..., 'w')` and dropped every such block on each run.

    When nothing is missing the file is not opened for writing at all, so a run on a clean
    tree leaves no diff — not even a whitespace or BOM round-trip.
    """
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    else:
        content = MODIFIER_TYPE_FILE_HEADER

    original = content
    existing = _top_level_keys(content)
    sections = expected_modifier_definitions()

    for index, (header, modifier_names) in enumerate(sections):
        missing = [m for m in modifier_names if m not in existing]
        if not missing:
            continue
        addition = ''.join(_definition_block(m) for m in missing)
        later_headers = [h for h, _ in sections[index + 1:]]
        insert_at = _section_end_index(content, header, later_headers)

        if insert_at is None:
            # Section absent entirely — start one at EOF.
            content = content.rstrip('\n') + '\n\n' + header + '\n' + addition
        else:
            prefix, suffix = content[:insert_at], content[insert_at:]
            if not prefix.endswith('\n\n'):
                prefix = prefix.rstrip('\n') + '\n\n'
            content = prefix + addition + suffix

        existing.update(missing)

    if content == original:
        return False

    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.write(content.lstrip('﻿'))
    return True


# ============================================================================
# STEP 2: Add modifiers to technology files
# ============================================================================

def get_all_modifiers_for_tech(tech_name):
    """Get all modifiers that need to be added to a technology."""
    modifiers = []
    if tech_name in PRINCIPLE_TECH_MODIFIERS:
        modifiers.append(PRINCIPLE_TECH_MODIFIERS[tech_name][0])
    if tech_name in BUTTON_TECH_MODIFIERS:
        for mod_name, _, _ in BUTTON_TECH_MODIFIERS[tech_name]:
            modifiers.append(mod_name)
    return modifiers


def _modifier_already_present(block_body, modifier_name):
    """True if modifier_name already appears as a key (`<name> = ...`) in block_body."""
    return re.search(r'(?m)^\s*' + re.escape(modifier_name) + r'\s*=', block_body) is not None


def _filter_new_modifiers(block_body, modifier_names):
    """Return the modifier_names not already present in block_body, preserving order.

    Idempotency guard (issue #191): the appenders below splice modifier lines into
    an existing block unconditionally, so a second run would double every modifier
    without this filter. The engine's `Duplicated key` warning only fires on
    top-level entity collisions, never on duplicate keys inside a block.
    """
    return [m for m in modifier_names if not _modifier_already_present(block_body, m)]


def add_modifiers_to_tech_file(filepath, tech_modifiers_map):
    """Add boolean modifiers to technology definitions in a file.

    tech_modifiers_map: { tech_name: [modifier_name, ...] }
    """
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    original = content

    for tech_name, modifier_names in tech_modifiers_map.items():
        modifier_lines = '\n'.join(f'\t\t{m} = yes' for m in modifier_names)

        # Pattern 1: tech has modifier = { ... } block (with content)
        # We insert before the closing } of the modifier block
        pattern_with_content = re.compile(
            r'(' + re.escape(tech_name) + r'\s*=\s*\{.*?'
            r'modifier\s*=\s*\{)'
            r'(.*?)'
            r'(\n\t\})',
            re.DOTALL
        )

        match = pattern_with_content.search(content)
        if match:
            new_mods = _filter_new_modifiers(match.group(2), modifier_names)
            if not new_mods:
                continue  # all modifiers already present — idempotent no-op
            new_lines = '\n'.join(f'\t\t{m} = yes' for m in new_mods)
            # Insert modifier lines before the closing } of modifier block
            content = (
                content[:match.end(2)]
                + '\n' + new_lines
                + content[match.start(3):]
            )
            continue

        # Pattern 2: tech has empty modifier = { } block
        pattern_empty = re.compile(
            r'(' + re.escape(tech_name) + r'\s*=\s*\{.*?)'
            r'(modifier\s*=\s*\{\s*\})',
            re.DOTALL
        )
        match = pattern_empty.search(content)
        if match:
            replacement = f'modifier = {{\n{modifier_lines}\n\t}}'
            content = content[:match.start(2)] + replacement + content[match.end(2):]
            continue

        # Pattern 3: tech has no modifier block - add one after unlocking_technologies or category
        pattern_no_mod = re.compile(
            r'(' + re.escape(tech_name) + r'\s*=\s*\{.*?)'
            r'(\n\t(?:unlocking_technologies\s*=\s*\{[^}]*\}|category\s*=\s*\w+))',
            re.DOTALL
        )
        match = pattern_no_mod.search(content)
        if match:
            insert_point = match.end(2)
            modifier_block = f'\n\n\tmodifier = {{\n{modifier_lines}\n\t}}'
            content = content[:insert_point] + modifier_block + content[insert_point:]
            continue

        print(f"  WARNING: Could not find tech '{tech_name}' in {filepath}")

    if content != original:
        utf8bom = '\ufeff'
        if not content.startswith(utf8bom):
            # Check if original had BOM
            pass
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write(content.lstrip('\ufeff'))
        return True
    return False


def add_inject_entries_to_modified(filepath, tech_modifiers_map):
    """Add INJECT: entries for vanilla techs to modified.txt. Returns True if written."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    original = content
    new_entries = []
    for tech_name, modifier_names in sorted(tech_modifiers_map.items()):
        modifier_lines = '\n'.join(f'\t\t{m} = yes' for m in modifier_names)
        # Check if INJECT for this tech already exists
        if f'INJECT:{tech_name}' in content:
            # Need to add to existing INJECT block
            pattern = re.compile(
                r'(INJECT:' + re.escape(tech_name) + r'\s*=\s*\{\s*\n\tmodifier\s*=\s*\{)'
                r'(.*?)'
                r'(\n\t\})',
                re.DOTALL
            )
            match = pattern.search(content)
            if match:
                new_mods = _filter_new_modifiers(match.group(2), modifier_names)
                if new_mods:
                    new_lines = '\n'.join(f'\t\t{m} = yes' for m in new_mods)
                    content = (
                        content[:match.end(2)]
                        + '\n' + new_lines
                        + content[match.start(3):]
                    )
            else:
                print(f"  WARNING: Found INJECT:{tech_name} but couldn't parse modifier block")
        else:
            # Create new INJECT entry
            entry = f'\nINJECT:{tech_name} = {{\n\tmodifier = {{\n{modifier_lines}\n\t}}\n}}\n'
            new_entries.append(entry)

    if new_entries:
        content = content.rstrip() + '\n' + '\n'.join(new_entries) + '\n'

    if content == original:
        return False

    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.write(content.lstrip('\ufeff'))
    return True


# ============================================================================
# STEP 3: Replace has_technology_researched in power bloc principles
# ============================================================================

def replace_tech_in_principles(filepath):
    """Replace has_technology_researched with modifier checks in principles."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    original = content
    replacements = 0
    for tech_name, (mod_name, _, _) in PRINCIPLE_TECH_MODIFIERS.items():
        old = f'has_technology_researched = {tech_name}'
        new = f'modifier:{mod_name} = yes'
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            replacements += count
            print(f"  Replaced {count}x: {tech_name} -> {mod_name}")

    # Already-converted file: skip the write entirely so no diff is produced.
    if content != original:
        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write(content.lstrip('\ufeff'))

    return replacements


# ============================================================================
# STEP 4: Replace has_technology_researched in scripted buttons
# ============================================================================

def replace_tech_in_buttons(root=None):
    """Replace has_technology_researched with modifier checks in button files."""
    root = root or mod_path
    replacements = 0
    already_converted = 0

    # Group buttons by file
    file_buttons = {}
    for rel_path, button_name, tech_name, mod_name in BUTTON_SPECIFIC_MAP:
        full_path = os.path.join(root, rel_path)
        if full_path not in file_buttons:
            file_buttons[full_path] = []
        file_buttons[full_path].append((button_name, tech_name, mod_name))

    for filepath, buttons in file_buttons.items():
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        original = content
        for button_name, tech_name, mod_name in buttons:
            # Find the button definition and replace has_technology_researched within it
            # We need to be careful to only replace within the specific button
            old = f'has_technology_researched = {tech_name}'
            new = f'modifier:{mod_name} = yes'

            # Find the button start
            button_start = content.find(f'{button_name} = {{')
            if button_start == -1:
                # Try with leading newline
                button_start = content.find(f'\n{button_name} = {{')
                if button_start != -1:
                    button_start += 1

            if button_start == -1:
                print(f"  WARNING: Could not find button '{button_name}' in {filepath}")
                continue

            # Find the next top-level closing brace (the end of this button)
            # Simple approach: find the next occurrence of has_technology_researched = tech_name
            # after the button start
            search_start = button_start
            tech_pos = content.find(old, search_start)

            if tech_pos == -1:
                # Either already converted on an earlier run, or the button no longer
                # gates on that tech. Both are no-ops, not errors — warning on them made
                # every run of an up-to-date tree print eight scary lines.
                already_converted += 1
                continue

            # Make sure this occurrence is within the button (before the next top-level def)
            # Replace just this one occurrence
            content = content[:tech_pos] + new + content[tech_pos + len(old):]
            replacements += 1
            print(f"  Replaced in {button_name}: {tech_name} -> {mod_name}")

        if content != original:
            with open(filepath, 'w', encoding='utf-8-sig') as f:
                f.write(content.lstrip('\ufeff'))

    if already_converted:
        print(f"  {already_converted} button gate(s) already converted \u2014 nothing to do")

    return replacements


# ============================================================================
# STEP 5: Generate localization
# ============================================================================

def existing_localization_keys(root=None):
    """Every `key:0` defined in any localization/english/*.yml under `root`.

    Cross-file, deliberately: these modifiers' loc long ago migrated out of
    te_modifiers_l_english.yml (the pb ones to te_power_bloc_unlocks_l_english.yml, the
    button ones to te_miscellaneous/te_concepts). A same-file-only check — what this
    script had before — saw them as absent and re-appended ~104 stale duplicates per run.
    """
    root = root or mod_path
    loc_dir = os.path.join(root, 'localization', 'english')
    keys = set()
    if not os.path.isdir(loc_dir):
        return keys
    for filename in sorted(os.listdir(loc_dir)):
        if not filename.endswith('.yml'):
            continue
        with open(os.path.join(loc_dir, filename), 'r', encoding='utf-8-sig') as f:
            keys.update(re.findall(r'(?m)^\s*([\w.]+):\d+\s', f.read()))
    return keys


def generate_localization():
    """Generate candidate localization entries for the configured modifiers.

    These are placeholders for gates that have no loc anywhere yet; main() filters out
    everything `existing_localization_keys` already knows.
    """
    lines = []

    # Principle modifiers.
    #
    # `<name>_desc` is deliberately NOT emitted: gen_pb_principle_unlock_descs.py owns
    # every country_*_pb_principles_bool_desc key and renders it with [GetTechnology(...)]
    # / [Concept(...)] accessors into te_power_bloc_unlocks_l_english.yml. Emitting a
    # plain-text copy here would put the same key in two files with different values,
    # which duplicate_key_audit --strict treats as an error.
    for tech, (mod_name, loc_name, loc_desc) in sorted(PRINCIPLE_TECH_MODIFIERS.items()):
        lines.append(f' {mod_name}:0 "{loc_name}"')

    # Button modifiers
    all_button_mods = set()
    for tech, mods in sorted(BUTTON_TECH_MODIFIERS.items()):
        for mod_name, loc_name, loc_desc in mods:
            if mod_name not in all_button_mods:
                all_button_mods.add(mod_name)
                lines.append(f' {mod_name}:0 "{loc_name}"')
                lines.append(f' {mod_name}_desc:0 "{loc_desc}"')

    return '\n'.join(lines) + '\n'


# ============================================================================
# MAIN
# ============================================================================

def find_tech_in_era_files(root=None):
    """Determine which era file each mod tech is defined in."""
    root = root or mod_path
    tech_dir = os.path.join(root, 'common', 'technology', 'technologies')
    tech_file_map = {}  # tech_name -> filepath
    if not os.path.isdir(tech_dir):
        return tech_file_map

    for filename in sorted(os.listdir(tech_dir)):
        if not filename.endswith('.txt') or filename == 'modified.txt':
            continue
        filepath = os.path.join(tech_dir, filename)
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()

        # Find all tech definitions (top-level keys)
        # Pattern: key = { at the start of a line (not indented, not INJECT:)
        for match in re.finditer(r'^(\S+)\s*=\s*\{', content, re.MULTILINE):
            tech_name = match.group(1)
            if not tech_name.startswith('INJECT:') and not tech_name.startswith('#'):
                tech_file_map[tech_name] = filepath

    return tech_file_map


def main(root=None):
    root = root or mod_path
    print("=" * 60)
    print("Adding technology modifiers for scripted buttons and power bloc principles")
    print(f"Root: {root}")
    print("=" * 60)

    # Collect all techs that need modifiers
    all_techs_needing_modifiers = set()
    all_techs_needing_modifiers.update(PRINCIPLE_TECH_MODIFIERS.keys())
    for tech in BUTTON_TECH_MODIFIERS:
        all_techs_needing_modifiers.add(tech)

    # Find which file each tech is in
    tech_file_map = find_tech_in_era_files(root)

    # Organize techs by file
    era_file_techs = {}  # filepath -> { tech_name: [modifiers] }
    vanilla_techs = {}  # tech_name -> [modifiers]

    for tech in sorted(all_techs_needing_modifiers):
        modifiers = get_all_modifiers_for_tech(tech)
        if not modifiers:
            continue

        if tech in VANILLA_TECHS:
            vanilla_techs[tech] = modifiers
        elif tech in tech_file_map:
            filepath = tech_file_map[tech]
            if filepath not in era_file_techs:
                era_file_techs[filepath] = {}
            era_file_techs[filepath][tech] = modifiers
        else:
            print(f"  WARNING: Tech '{tech}' not found in any era file and not marked as vanilla!")

    # STEP 1: Merge in any missing modifier type definitions
    print("\n--- Step 1: Merging modifier type definitions ---")
    mod_type_path = os.path.join(
        root, 'common', 'modifier_type_definitions', 'tech_gate_modifier_types.txt'
    )
    if merge_modifier_type_definitions(mod_type_path):
        print(f"  Added missing definition(s) to {os.path.basename(mod_type_path)}")
    else:
        print(f"  {os.path.basename(mod_type_path)} already has every definition — unchanged")

    # STEP 2: Add modifiers to mod tech files
    print("\n--- Step 2: Adding modifiers to mod technology files ---")
    for filepath, tech_map in sorted(era_file_techs.items()):
        print(f"  Processing: {os.path.basename(filepath)}")
        for tech, mods in sorted(tech_map.items()):
            print(f"    {tech}: {', '.join(mods)}")
        add_modifiers_to_tech_file(filepath, tech_map)

    # STEP 3: Add INJECT entries for vanilla techs
    print("\n--- Step 3: Adding INJECT entries for vanilla techs ---")
    modified_path = os.path.join(root, 'common', 'technology', 'technologies', 'modified.txt')
    if vanilla_techs:
        for tech, mods in sorted(vanilla_techs.items()):
            print(f"  {tech}: {', '.join(mods)}")
        add_inject_entries_to_modified(modified_path, vanilla_techs)
    else:
        print("  No vanilla techs to modify")

    # STEP 4: Replace in power bloc principles
    print("\n--- Step 4: Replacing tech triggers in power bloc principles ---")
    principle_path = os.path.join(
        root, 'common', 'power_bloc_principles', 'extra_power_bloc_principles.txt'
    )
    count = replace_tech_in_principles(principle_path)
    print(f"  Total replacements: {count}")

    # STEP 5: Replace in scripted buttons
    print("\n--- Step 5: Replacing tech triggers in scripted buttons ---")
    count = replace_tech_in_buttons(root)
    print(f"  Total replacements: {count}")

    # STEP 6: Generate localization
    print("\n--- Step 6: Generating localization ---")
    loc_entries = generate_localization()
    loc_path = os.path.join(
        root, 'localization', 'english', 'te_modifiers_l_english.yml'
    )
    with open(loc_path, 'r', encoding='utf-8-sig') as f:
        loc_content = f.read()

    # Skip any key that already exists in ANY localization/english/*.yml, not just this
    # one (issue #191 only guarded the within-file case). Every one of these keys has
    # since migrated to a topical file — te_power_bloc_unlocks / te_miscellaneous /
    # te_concepts — with richer, accessor-based text, so a same-file check re-appended
    # ~104 stale duplicates on every run and organize_loc.py then had to un-do it.
    existing_loc_keys = existing_localization_keys(root)
    new_loc_lines = []
    for line in loc_entries.splitlines():
        key_match = re.match(r'\s*([\w.]+):\d+\s', line)
        if key_match and key_match.group(1) in existing_loc_keys:
            continue
        new_loc_lines.append(line)
    if new_loc_lines:
        loc_content = loc_content.rstrip() + '\n' + '\n'.join(new_loc_lines) + '\n'
        with open(loc_path, 'w', encoding='utf-8-sig') as f:
            f.write(loc_content)
        print(f"  Added {len(new_loc_lines)} localization line(s) to {os.path.basename(loc_path)}")
    else:
        print("  No new localization entries (every key already has loc somewhere)")

    print("\n" + "=" * 60)
    print("DONE! If anything was added, run: python3 organize_loc.py")
    print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        '--root',
        default=mod_path,
        help='Mod tree to operate on (default: this checkout, via path_constants.mod_path).',
    )
    main(parser.parse_args().root)
