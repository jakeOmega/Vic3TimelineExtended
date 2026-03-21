"""
Replaces has_technology_researched triggers in scripted buttons and power bloc principles
with custom boolean modifier checks, and adds those modifiers to the relevant technologies.

This makes the technology's effects on scripted buttons and power bloc principles visible
when browsing the tech tree.
"""

import os
import re
from path_constants import mod_path

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
    'combined_arms': [
        ('country_can_use_rearmament_bool', 'Enables Rearmament', 'Enables the Rearmament button for World War preparation.'),
        ('country_can_use_total_war_economy_bool', 'Enables Total War Economy', 'Enables the Total War Economy button during wartime.'),
    ],
    'mass_media': [
        ('country_can_use_war_propaganda_bool', 'Enables War Propaganda', 'Enables the War Propaganda button during wartime.'),
    ],
    'intergovernmental_organizations': [
        ('country_can_join_united_nations_bool', 'Enables Joining the United Nations', 'Enables the option to join the United Nations.'),
    ],
    'decolonization': [
        ('country_can_use_cultural_assimilation_bool', 'Enables Cultural Assimilation Policy', 'Enables the Cultural Assimilation policy for colonial empires.'),
    ],
    'keynesian_economics': [
        ('country_can_use_open_market_ops_bool', 'Enables Open Market Operations', 'Enables the Open Market Operations banking intervention.'),
        ('country_can_use_fx_devaluation_bool', 'Enables FX Devaluation', 'Enables the FX Devaluation banking intervention.'),
        ('country_can_use_asset_relief_bool', 'Enables Asset Relief Program', 'Enables the Asset Relief Program banking intervention.'),
    ],
    'international_exchange_standards': [
        ('country_can_use_countercyclical_buffer_bool', 'Enables Countercyclical Buffer', 'Enables the Countercyclical Buffer banking intervention.'),
        ('country_can_use_fx_support_bool', 'Enables FX Support', 'Enables the FX Support banking intervention.'),
        ('country_can_use_fx_swap_lines_bool', 'Enables FX Swap Lines', 'Enables the FX Swap Lines banking intervention.'),
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
}

# Map of (button_file, button_name, tech_name) -> modifier_name
# This is needed because some techs have multiple buttons, we need to match the right one
BUTTON_SPECIFIC_MAP = [
    # World War buttons
    ('common/scripted_buttons/world_war_buttons.txt', 'ww_rearm_button', 'combined_arms', 'country_can_use_rearmament_bool'),
    ('common/scripted_buttons/world_war_buttons.txt', 'ww_total_war_economy_button', 'combined_arms', 'country_can_use_total_war_economy_bool'),
    ('common/scripted_buttons/world_war_buttons.txt', 'ww_war_propaganda_button', 'mass_media', 'country_can_use_war_propaganda_bool'),
    # UN buttons
    ('common/scripted_buttons/un_buttons.txt', 'un_join_button', 'intergovernmental_organizations', 'country_can_join_united_nations_bool'),
    # Colonial empire buttons
    ('common/scripted_buttons/colonial_empire_buttons.txt', 'ce_cultural_assimilation', 'decolonization', 'country_can_use_cultural_assimilation_bool'),
    # Banking buttons
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_open_market_ops', 'keynesian_economics', 'country_can_use_open_market_ops_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_countercyclical_buffer', 'international_exchange_standards', 'country_can_use_countercyclical_buffer_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_expand_deposit_guarantee', 'consumer_credit', 'country_can_use_deposit_guarantee_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_emergency_liquidity_program', 'investment_banks', 'country_can_use_emergency_liquidity_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_fx_devaluation', 'keynesian_economics', 'country_can_use_fx_devaluation_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_fx_support', 'international_exchange_standards', 'country_can_use_fx_support_bool'),
    ('common/scripted_buttons/timeline_extended_scripted_buttons.txt', 'cb_fx_swap_lines', 'international_exchange_standards', 'country_can_use_fx_swap_lines_bool'),
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
# STEP 1: Generate modifier type definitions
# ============================================================================

def generate_modifier_type_definitions():
    """Generate the modifier_type_definitions file content."""
    lines = ['# Auto-generated boolean modifiers for technology-gated features\n']
    lines.append('# These make technology requirements for scripted buttons and\n')
    lines.append('# power bloc principles visible in the tech tree.\n\n')

    # Principle modifiers
    lines.append('# Power bloc principle technology requirements\n')
    for tech, (mod_name, loc_name, loc_desc) in sorted(PRINCIPLE_TECH_MODIFIERS.items()):
        lines.append(f'{mod_name} = {{\n')
        lines.append(f'\tcolor = good\n')
        lines.append(f'\tboolean = yes\n')
        lines.append(f'}}\n\n')

    # Button modifiers
    lines.append('# Scripted button technology requirements\n')
    all_button_mods = set()
    for tech, mods in sorted(BUTTON_TECH_MODIFIERS.items()):
        for mod_name, loc_name, loc_desc in mods:
            if mod_name not in all_button_mods:
                all_button_mods.add(mod_name)
                lines.append(f'{mod_name} = {{\n')
                lines.append(f'\tcolor = good\n')
                lines.append(f'\tboolean = yes\n')
                lines.append(f'}}\n\n')

    return ''.join(lines)


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
            # Insert modifier lines before the closing } of modifier block
            content = (
                content[:match.end(2)]
                + '\n' + modifier_lines
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
    """Add INJECT: entries for vanilla techs to modified.txt."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

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
                content = (
                    content[:match.end(2)]
                    + '\n' + modifier_lines
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

    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.write(content.lstrip('\ufeff'))


# ============================================================================
# STEP 3: Replace has_technology_researched in power bloc principles
# ============================================================================

def replace_tech_in_principles(filepath):
    """Replace has_technology_researched with modifier checks in principles."""
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    replacements = 0
    for tech_name, (mod_name, _, _) in PRINCIPLE_TECH_MODIFIERS.items():
        old = f'has_technology_researched = {tech_name}'
        new = f'modifier:{mod_name} = yes'
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            replacements += count
            print(f"  Replaced {count}x: {tech_name} -> {mod_name}")

    with open(filepath, 'w', encoding='utf-8-sig') as f:
        f.write(content.lstrip('\ufeff'))

    return replacements


# ============================================================================
# STEP 4: Replace has_technology_researched in scripted buttons
# ============================================================================

def replace_tech_in_buttons():
    """Replace has_technology_researched with modifier checks in button files."""
    replacements = 0

    # Group buttons by file
    file_buttons = {}
    for rel_path, button_name, tech_name, mod_name in BUTTON_SPECIFIC_MAP:
        full_path = os.path.join(mod_path, rel_path)
        if full_path not in file_buttons:
            file_buttons[full_path] = []
        file_buttons[full_path].append((button_name, tech_name, mod_name))

    for filepath, buttons in file_buttons.items():
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            content = f.read()

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
                print(f"  WARNING: Could not find '{old}' after button '{button_name}' in {filepath}")
                continue

            # Make sure this occurrence is within the button (before the next top-level def)
            # Replace just this one occurrence
            content = content[:tech_pos] + new + content[tech_pos + len(old):]
            replacements += 1
            print(f"  Replaced in {button_name}: {tech_name} -> {mod_name}")

        with open(filepath, 'w', encoding='utf-8-sig') as f:
            f.write(content.lstrip('\ufeff'))

    return replacements


# ============================================================================
# STEP 5: Generate localization
# ============================================================================

def generate_localization():
    """Generate localization entries for all new modifiers."""
    lines = []

    # Principle modifiers
    for tech, (mod_name, loc_name, loc_desc) in sorted(PRINCIPLE_TECH_MODIFIERS.items()):
        lines.append(f' {mod_name}:0 "{loc_name}"')
        lines.append(f' {mod_name}_desc:0 "{loc_desc}"')

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

def find_tech_in_era_files():
    """Determine which era file each mod tech is defined in."""
    tech_dir = os.path.join(mod_path, 'common', 'technology', 'technologies')
    tech_file_map = {}  # tech_name -> filepath

    for filename in os.listdir(tech_dir):
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


def main():
    print("=" * 60)
    print("Adding technology modifiers for scripted buttons and power bloc principles")
    print("=" * 60)

    # Collect all techs that need modifiers
    all_techs_needing_modifiers = set()
    all_techs_needing_modifiers.update(PRINCIPLE_TECH_MODIFIERS.keys())
    for tech in BUTTON_TECH_MODIFIERS:
        all_techs_needing_modifiers.add(tech)

    # Find which file each tech is in
    tech_file_map = find_tech_in_era_files()

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

    # STEP 1: Generate modifier type definitions
    print("\n--- Step 1: Generating modifier type definitions ---")
    mod_type_path = os.path.join(
        mod_path, 'common', 'modifier_type_definitions', 'tech_gate_modifier_types.txt'
    )
    mod_type_content = generate_modifier_type_definitions()
    with open(mod_type_path, 'w', encoding='utf-8-sig') as f:
        f.write(mod_type_content)
    print(f"  Created {mod_type_path}")

    # STEP 2: Add modifiers to mod tech files
    print("\n--- Step 2: Adding modifiers to mod technology files ---")
    for filepath, tech_map in sorted(era_file_techs.items()):
        print(f"  Processing: {os.path.basename(filepath)}")
        for tech, mods in sorted(tech_map.items()):
            print(f"    {tech}: {', '.join(mods)}")
        add_modifiers_to_tech_file(filepath, tech_map)

    # STEP 3: Add INJECT entries for vanilla techs
    print("\n--- Step 3: Adding INJECT entries for vanilla techs ---")
    modified_path = os.path.join(mod_path, 'common', 'technology', 'technologies', 'modified.txt')
    if vanilla_techs:
        for tech, mods in sorted(vanilla_techs.items()):
            print(f"  {tech}: {', '.join(mods)}")
        add_inject_entries_to_modified(modified_path, vanilla_techs)
    else:
        print("  No vanilla techs to modify")

    # STEP 4: Replace in power bloc principles
    print("\n--- Step 4: Replacing tech triggers in power bloc principles ---")
    principle_path = os.path.join(
        mod_path, 'common', 'power_bloc_principles', 'extra_power_bloc_principles.txt'
    )
    count = replace_tech_in_principles(principle_path)
    print(f"  Total replacements: {count}")

    # STEP 5: Replace in scripted buttons
    print("\n--- Step 5: Replacing tech triggers in scripted buttons ---")
    count = replace_tech_in_buttons()
    print(f"  Total replacements: {count}")

    # STEP 6: Generate localization
    print("\n--- Step 6: Generating localization ---")
    loc_entries = generate_localization()
    loc_path = os.path.join(
        mod_path, 'localization', 'english', 'te_modifiers_l_english.yml'
    )
    with open(loc_path, 'r', encoding='utf-8-sig') as f:
        loc_content = f.read()

    # Append new entries before the end of the file
    loc_content = loc_content.rstrip() + '\n' + loc_entries
    with open(loc_path, 'w', encoding='utf-8-sig') as f:
        f.write(loc_content)
    print(f"  Added localization entries to {os.path.basename(loc_path)}")

    print("\n" + "=" * 60)
    print("DONE! Remember to run: python organize_loc.py")
    print("=" * 60)


if __name__ == '__main__':
    main()
