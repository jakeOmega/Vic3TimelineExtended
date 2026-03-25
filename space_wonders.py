"""
Generate Orbital Battlestation and Mind Upload Nexus wonder building content.
Appends to existing mod files with proper BOM encoding and tab indentation.
"""
import os
import sys

if __name__ != "__main__":
    sys.exit(0)

from path_constants import mod_path

def read_file_content(path):
    """Read file content, handling BOM."""
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:3] == b'\xef\xbb\xbf':
        return raw[3:].decode('utf-8')
    return raw.decode('utf-8')

def append_to_file(path, content):
    """Append content to a file, preserving BOM encoding."""
    existing = read_file_content(path)
    if not existing.endswith('\n'):
        existing += '\n'
    new_content = existing + content
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(new_content.encode('utf-8'))
    print(f"  Appended to {os.path.relpath(path, mod_path)}")

def insert_after_pattern(path, pattern, content):
    """Insert content after the first line matching pattern."""
    existing = read_file_content(path)
    lines = existing.split('\n')
    for i, line in enumerate(lines):
        if pattern in line:
            lines.insert(i + 1, content.rstrip('\n'))
            break
    else:
        raise ValueError(f"Pattern '{pattern}' not found in {path}")
    new_content = '\n'.join(lines)
    with open(path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(new_content.encode('utf-8'))
    print(f"  Inserted into {os.path.relpath(path, mod_path)}")

# ============================================================
# BUILDINGS
# ============================================================
buildings_content = """
#==================================================
# Orbital Battlestation
#==================================================

REPLACE_OR_CREATE:building_orbital_battlestation_construction_site = {
\tbuilding_group = bg_government\t
\ticon = "gfx/interface/icons/building_icons/space_base.dds"
\tcity_type = city
\tlevels_per_mesh = -1
\t
\tunlocking_technologies = {
\t\torbital_weapon_platforms
\t}

\tproduction_method_groups = {
\t\tpmg_base_building_orbital_battlestation_construction_site
\t}

\trequired_construction = construction_cost_medium
\t
\texpandable = no
\t
\townership_type = no_ownership
\tbackground = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"
}

REPLACE_OR_CREATE:building_orbital_battlestation = {
\tbuilding_group = bg_military\t
\ticon = "gfx/interface/icons/building_icons/space_base.dds"
\tcity_type = city
\tlevels_per_mesh = -1

\tproduction_method_groups = {
\t\tpmg_base_building_orbital_battlestation
\t}

\trequired_construction = construction_cost_canal
\t
\tbuildable = no
\texpandable = no
\townership_type = self
\tbackground = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"
}

#==================================================
# Mind Upload Nexus
#==================================================

REPLACE_OR_CREATE:building_mind_upload_nexus_construction_site = {
\tbuilding_group = bg_government\t
\ticon = "gfx/interface/icons/building_icons/network.dds"
\tcity_type = city
\tlevels_per_mesh = -1
\t
\tunlocking_technologies = {
\t\tmind_backups
\t}

\tproduction_method_groups = {
\t\tpmg_base_building_mind_upload_nexus_construction_site
\t}

\trequired_construction = construction_cost_medium
\t
\texpandable = no
\t
\townership_type = no_ownership
\tbackground = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"
}

REPLACE_OR_CREATE:building_mind_upload_nexus = {
\tbuilding_group = bg_private_infrastructure\t
\ticon = "gfx/interface/icons/building_icons/network.dds"
\tcity_type = city
\tlevels_per_mesh = -1

\tproduction_method_groups = {
\t\tpmg_base_building_mind_upload_nexus
\t}

\trequired_construction = construction_cost_canal
\t
\tbuildable = no
\texpandable = no
\townership_type = self
\tbackground = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"
}
"""

# ============================================================
# PRODUCTION METHODS
# ============================================================
pms_content = """
#==================================================
# Orbital Battlestation PMs
#==================================================

pm_orbital_battlestation_construction_paused = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 5
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 500
\t\t}
\t}
}

pm_orbital_battlestation_construction_slow = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 3000              # Price: 4000, Total cost: 12000000.0 (64.55%)
\t\t\tgoods_input_launch_capacity_add = 30000                # Price:  200, Total cost: 6000000.0 (32.28%)
\t\t\tgoods_input_electronic_components_add = 3000           # Price:   80, Total cost: 240000.0 (1.29%)
\t\t\tgoods_input_steel_add = 5000                           # Price:   50, Total cost: 250000.0 (1.34%)
\t\t\tgoods_input_explosives_add = 2000                      # Price:   50, Total cost: 100000.0 (0.54%)
\t\t\t# Total input cost: 18590000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 20000
\t\t\tbuilding_employment_officers_add = 20000
\t\t\tbuilding_employment_academics_add = 10000
\t\t}
\t}
}

pm_orbital_battlestation_construction_medium = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 6000              # Price: 4000, Total cost: 24000000.0 (64.55%)
\t\t\tgoods_input_launch_capacity_add = 60000                # Price:  200, Total cost: 12000000.0 (32.28%)
\t\t\tgoods_input_electronic_components_add = 6000           # Price:   80, Total cost: 480000.0 (1.29%)
\t\t\tgoods_input_steel_add = 10000                          # Price:   50, Total cost: 500000.0 (1.34%)
\t\t\tgoods_input_explosives_add = 4000                      # Price:   50, Total cost: 200000.0 (0.54%)
\t\t\t# Total input cost: 37180000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 20000
\t\t\tbuilding_employment_officers_add = 20000
\t\t\tbuilding_employment_academics_add = 10000
\t\t}
\t}
}

pm_orbital_battlestation_construction_fast = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 12000             # Price: 4000, Total cost: 48000000.0 (64.55%)
\t\t\tgoods_input_launch_capacity_add = 120000               # Price:  200, Total cost: 24000000.0 (32.28%)
\t\t\tgoods_input_electronic_components_add = 12000          # Price:   80, Total cost: 960000.0 (1.29%)
\t\t\tgoods_input_steel_add = 20000                          # Price:   50, Total cost: 1000000.0 (1.34%)
\t\t\tgoods_input_explosives_add = 8000                      # Price:   50, Total cost: 400000.0 (0.54%)
\t\t\t# Total input cost: 74360000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 20000
\t\t\tbuilding_employment_officers_add = 20000
\t\t\tbuilding_employment_academics_add = 10000
\t\t}
\t}
}

pm_orbital_battlestation = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tcountry_modifiers = {
\t\tlevel_scaled = {
\t\t\tunit_offense_mult = 0.05
\t\t\tunit_defense_mult = 0.05
\t\t\tunit_morale_recovery_mult = 0.05
\t\t\tcountry_nuclear_weapon_defense_chance_add = 0.10
\t\t\tunit_blockade_mult = 0.10
\t\t\tunit_morale_damage_mult = 0.05
\t\t}
\t}

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 300               # Price: 4000, Total cost: 1200000.0 (52.63%)
\t\t\tgoods_input_electronic_components_add = 500            # Price:   80, Total cost: 40000.0 (1.75%)
\t\t\tgoods_input_launch_capacity_add = 5000                 # Price:  200, Total cost: 1000000.0 (43.86%)
\t\t\tgoods_input_explosives_add = 500                       # Price:   50, Total cost: 25000.0 (1.10%)
\t\t\tgoods_input_steel_add = 300                            # Price:   50, Total cost: 15000.0 (0.66%)
\t\t\t# Total input cost: 2280000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 2000
\t\t\tbuilding_employment_officers_add = 3000
\t\t\tbuilding_employment_academics_add = 1000
\t\t}
\t}
}

#==================================================
# Mind Upload Nexus PMs
#==================================================

pm_mind_upload_nexus_construction_paused = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 5
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 500
\t\t}
\t}
}

pm_mind_upload_nexus_construction_slow = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 3000              # Price: 4000, Total cost: 12000000.0 (87.59%)
\t\t\tgoods_input_electronic_components_add = 10000          # Price:   80, Total cost: 800000.0 (5.84%)
\t\t\tgoods_input_digital_access_add = 5000                  # Price:   60, Total cost: 300000.0 (2.19%)
\t\t\tgoods_input_electricity_add = 20000                    # Price:   30, Total cost: 600000.0 (4.38%)
\t\t\t# Total input cost: 13700000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 30000
\t\t\tbuilding_employment_academics_add = 30000
\t\t}
\t}

\trequired_input_goods = electricity
\trequired_input_goods = digital_access
}

pm_mind_upload_nexus_construction_medium = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 6000              # Price: 4000, Total cost: 24000000.0 (87.59%)
\t\t\tgoods_input_electronic_components_add = 20000          # Price:   80, Total cost: 1600000.0 (5.84%)
\t\t\tgoods_input_digital_access_add = 10000                 # Price:   60, Total cost: 600000.0 (2.19%)
\t\t\tgoods_input_electricity_add = 40000                    # Price:   30, Total cost: 1200000.0 (4.38%)
\t\t\t# Total input cost: 27400000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 30000
\t\t\tbuilding_employment_academics_add = 30000
\t\t}
\t}

\trequired_input_goods = electricity
\trequired_input_goods = digital_access
}

pm_mind_upload_nexus_construction_fast = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 12000             # Price: 4000, Total cost: 48000000.0 (87.59%)
\t\t\tgoods_input_electronic_components_add = 40000          # Price:   80, Total cost: 3200000.0 (5.84%)
\t\t\tgoods_input_digital_access_add = 20000                 # Price:   60, Total cost: 1200000.0 (2.19%)
\t\t\tgoods_input_electricity_add = 80000                    # Price:   30, Total cost: 2400000.0 (4.38%)
\t\t\t# Total input cost: 54800000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 30000
\t\t\tbuilding_employment_academics_add = 30000
\t\t}
\t}

\trequired_input_goods = electricity
\trequired_input_goods = digital_access
}

pm_mind_upload_nexus = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tcountry_modifiers = {
\t\tlevel_scaled = {
\t\t\tcountry_tech_research_speed_mult = 0.05
\t\t}
\t}

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\t# Input goods
\t\t\tgoods_input_electricity_add = 30000                    # Price:   30, Total cost: 900000.0 (60.00%)
\t\t\tgoods_input_electronic_components_add = 1000           # Price:   80, Total cost: 80000.0 (5.33%)
\t\t\tgoods_input_digital_access_add = 2000                  # Price:   60, Total cost: 120000.0 (8.00%)
\t\t\tgoods_input_advanced_materials_add = 100               # Price: 4000, Total cost: 400000.0 (26.67%)
\t\t\t# Total input cost: 1500000.0
\t\t\t# Output goods
\t\t\tgoods_output_digital_assets_add = 5000                 # Price:   80, Total cost: 400000.0 (66.67%)
\t\t\tgoods_output_services_add = 5000                       # Price:   40, Total cost: 200000.0 (33.33%)
\t\t\t# Total output cost: 600000.0
\t\t\t# Profit: -900000.0
\t\t\t# Profit margin: -60.00%
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 3000
\t\t\tbuilding_employment_academics_add = 5000
\t\t\tbuilding_employment_clerks_add = 2000
\t\t}
\t}

\trequired_input_goods = electricity
\trequired_input_goods = digital_access
}
"""

# ============================================================
# PRODUCTION METHOD GROUPS
# ============================================================
pmgs_content = """
#==================================================
# Orbital Battlestation PMGs
#==================================================

REPLACE_OR_CREATE:pmg_base_building_orbital_battlestation_construction_site = {
\ttexture = "gfx/interface/icons/generic_icons/mixed_icon_base.dds"
\tproduction_methods = {
\t\tpm_orbital_battlestation_construction_paused
\t\tpm_orbital_battlestation_construction_slow
\t\tpm_orbital_battlestation_construction_medium
\t\tpm_orbital_battlestation_construction_fast
\t}
}
REPLACE_OR_CREATE:pmg_base_building_orbital_battlestation = {
\ttexture = "gfx/interface/icons/generic_icons/mixed_icon_base.dds"
\tproduction_methods = {
\t\tpm_orbital_battlestation
\t}
}

#==================================================
# Mind Upload Nexus PMGs
#==================================================

REPLACE_OR_CREATE:pmg_base_building_mind_upload_nexus_construction_site = {
\ttexture = "gfx/interface/icons/generic_icons/mixed_icon_base.dds"
\tproduction_methods = {
\t\tpm_mind_upload_nexus_construction_paused
\t\tpm_mind_upload_nexus_construction_slow
\t\tpm_mind_upload_nexus_construction_medium
\t\tpm_mind_upload_nexus_construction_fast
\t}
}
REPLACE_OR_CREATE:pmg_base_building_mind_upload_nexus = {
\ttexture = "gfx/interface/icons/generic_icons/mixed_icon_base.dds"
\tproduction_methods = {
\t\tpm_mind_upload_nexus
\t}
}
"""

# ============================================================
# SCRIPTED EFFECTS
# ============================================================
scripted_effects_content = """
orbital_battlestation_construction = {
\tif = {
\t\tlimit = {
\t\t\tNOT = { has_variable = orbital_battlestation_progress_var }
\t\t}
\t\tset_variable = {
\t\t\tname = orbital_battlestation_progress_var
\t\t\tvalue = 0
\t\t}
\t}
\tif = {
\t\tlimit = {
\t\t\thas_variable = orbital_battlestation_progress_var
\t\t\tany_scope_building = {
\t\t\t\tis_building_type = building_orbital_battlestation_construction_site
\t\t\t\tbuilding_has_goods_shortage = no
\t\t\t}
\t\t}
\t\tchange_variable = {
\t\t\tname = orbital_battlestation_progress_var
\t\t\tadd = {
\t\t\t\tvalue = b:building_orbital_battlestation_construction_site.occupancy
\t\t\t\tdivide = 12
\t\t\t\tif = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_scope_building = { has_active_production_method = pm_orbital_battlestation_construction_slow }
\t\t\t\t\t}
\t\t\t\t\tmultiply = 0.25
\t\t\t\t}
\t\t\t\telse_if = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_scope_building = { has_active_production_method = pm_orbital_battlestation_construction_medium }
\t\t\t\t\t}
\t\t\t\t\tmultiply = 0.5
\t\t\t\t}
\t\t\t\telse_if = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_scope_building = { has_active_production_method = pm_orbital_battlestation_construction_fast }
\t\t\t\t\t}
\t\t\t\t\tmultiply = 1
\t\t\t\t}
\t\t\t\telse = {
\t\t\t\t\tmultiply = 0
\t\t\t\t}
\t\t\t\tmultiply = 1000
\t\t\t\tceiling = yes
\t\t\t\tdivide = 1000
\t\t\t}
\t\t}
\t}
\tif = {
\t\tlimit = {
\t\t\tvar:orbital_battlestation_progress_var >= 1
\t\t}
\t\tset_variable = {
\t\t\tname = orbital_battlestation_progress_var
\t\t\tvalue = 0
\t\t}
\t\tremove_building = building_orbital_battlestation_construction_site
\t\tif = {
\t\t\tlimit = { has_building = building_orbital_battlestation }
\t\t\tswitch = {
\t\t\t\ttrigger = b:building_orbital_battlestation.level
\t\t\t\t1 = { create_building = { building = building_orbital_battlestation level = 2 } }
\t\t\t\t2 = { create_building = { building = building_orbital_battlestation level = 3 } }
\t\t\t\t3 = { create_building = { building = building_orbital_battlestation level = 4 } }
\t\t\t\t4 = { create_building = { building = building_orbital_battlestation level = 5 } }
\t\t\t}
\t\t}
\t\telse = {
\t\t\tcreate_building = {
\t\t\t\tbuilding = building_orbital_battlestation
\t\t\t\tlevel = 1
\t\t\t}
\t\t}
\t}
}

mind_upload_nexus_construction = {
\tif = {
\t\tlimit = {
\t\t\tNOT = { has_variable = mind_upload_nexus_progress_var }
\t\t}
\t\tset_variable = {
\t\t\tname = mind_upload_nexus_progress_var
\t\t\tvalue = 0
\t\t}
\t}
\tif = {
\t\tlimit = {
\t\t\thas_variable = mind_upload_nexus_progress_var
\t\t\tany_scope_building = {
\t\t\t\tis_building_type = building_mind_upload_nexus_construction_site
\t\t\t\tbuilding_has_goods_shortage = no
\t\t\t}
\t\t}
\t\tchange_variable = {
\t\t\tname = mind_upload_nexus_progress_var
\t\t\tadd = {
\t\t\t\tvalue = b:building_mind_upload_nexus_construction_site.occupancy
\t\t\t\tdivide = 12
\t\t\t\tif = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_scope_building = { has_active_production_method = pm_mind_upload_nexus_construction_slow }
\t\t\t\t\t}
\t\t\t\t\tmultiply = 0.25
\t\t\t\t}
\t\t\t\telse_if = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_scope_building = { has_active_production_method = pm_mind_upload_nexus_construction_medium }
\t\t\t\t\t}
\t\t\t\t\tmultiply = 0.5
\t\t\t\t}
\t\t\t\telse_if = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_scope_building = { has_active_production_method = pm_mind_upload_nexus_construction_fast }
\t\t\t\t\t}
\t\t\t\t\tmultiply = 1
\t\t\t\t}
\t\t\t\telse = {
\t\t\t\t\tmultiply = 0
\t\t\t\t}
\t\t\t\tmultiply = 1000
\t\t\t\tceiling = yes
\t\t\t\tdivide = 1000
\t\t\t}
\t\t}
\t}
\tif = {
\t\tlimit = {
\t\t\tvar:mind_upload_nexus_progress_var >= 1
\t\t}
\t\tset_variable = {
\t\t\tname = mind_upload_nexus_progress_var
\t\t\tvalue = 0
\t\t}
\t\tremove_building = building_mind_upload_nexus_construction_site
\t\tif = {
\t\t\tlimit = { has_building = building_mind_upload_nexus }
\t\t\tswitch = {
\t\t\t\ttrigger = b:building_mind_upload_nexus.level
\t\t\t\t1 = { create_building = { building = building_mind_upload_nexus level = 2 } }
\t\t\t\t2 = { create_building = { building = building_mind_upload_nexus level = 3 } }
\t\t\t\t3 = { create_building = { building = building_mind_upload_nexus level = 4 } }
\t\t\t\t4 = { create_building = { building = building_mind_upload_nexus level = 5 } }
\t\t\t}
\t\t}
\t\telse = {
\t\t\tcreate_building = {
\t\t\t\tbuilding = building_mind_upload_nexus
\t\t\t\tlevel = 1
\t\t\t}
\t\t}
\t}
}
"""

# ============================================================
# ON-ACTIONS (new action definitions)
# ============================================================
on_actions_content = """
orbital_battlestation_on_action = {
\teffect = {
\t\tif = {
\t\t\tlimit = {
\t\t\t\thas_building = building_orbital_battlestation_construction_site
\t\t\t}
\t\t\torbital_battlestation_construction = yes
\t\t\tevery_scope_building = {
\t\t\t\tlimit = {
\t\t\t\t\tis_building_type = building_orbital_battlestation_construction_site
\t\t\t\t}
\t\t\t\tremove_modifier = orbital_battlestation_progress
\t\t\t\tadd_modifier = {
\t\t\t\t\tname = orbital_battlestation_progress
\t\t\t\t\tmultiplier = this.var:orbital_battlestation_progress_var
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}

mind_upload_nexus_on_action = {
\teffect = {
\t\tif = {
\t\t\tlimit = {
\t\t\t\thas_building = building_mind_upload_nexus_construction_site
\t\t\t}
\t\t\tmind_upload_nexus_construction = yes
\t\t\tevery_scope_building = {
\t\t\t\tlimit = {
\t\t\t\t\tis_building_type = building_mind_upload_nexus_construction_site
\t\t\t\t}
\t\t\t\tremove_modifier = mind_upload_nexus_progress
\t\t\t\tadd_modifier = {
\t\t\t\t\tname = mind_upload_nexus_progress
\t\t\t\t\tmultiplier = this.var:mind_upload_nexus_progress_var
\t\t\t\t}
\t\t\t}
\t\t}
\t}
}
"""

# ============================================================
# MODIFIER TYPE DEFINITIONS
# ============================================================
modifier_types_content = """
building_weekly_orbital_battlestation_progress = {
\tcolor = good
\tpercent = yes
\tscript_only = yes

\tgame_data = {
\t\tai_value = 50000000
\t}
}

building_total_orbital_battlestation_progress = {
\tcolor = good
\tpercent = yes
\tscript_only = yes
}

building_weekly_mind_upload_nexus_progress = {
\tcolor = good
\tpercent = yes
\tscript_only = yes

\tgame_data = {
\t\tai_value = 50000000
\t}
}

building_total_mind_upload_nexus_progress = {
\tcolor = good
\tpercent = yes
\tscript_only = yes
}
"""

# ============================================================
# STATIC MODIFIERS  
# ============================================================
static_modifiers_content = """orbital_battlestation_progress = {
\ticon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
\tbuilding_total_orbital_battlestation_progress = 1
}

mind_upload_nexus_progress = {
\ticon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
\tbuilding_total_mind_upload_nexus_progress = 1
}
"""

# ============================================================
# Execute all modifications
# ============================================================
print("=== Implementing Orbital Battlestation and Mind Upload Nexus ===\n")

# 1. Append building definitions
print("1. Adding building definitions...")
buildings_path = os.path.join(mod_path, "common", "buildings", "extra_buildings.txt")
append_to_file(buildings_path, buildings_content)

# 2. Append production methods
print("2. Adding production methods...")
pms_path = os.path.join(mod_path, "common", "production_methods", "extra_pms.txt")
append_to_file(pms_path, pms_content)

# 3. Append production method groups
print("3. Adding production method groups...")
pmgs_path = os.path.join(mod_path, "common", "production_method_groups", "extra_pm_groups.txt")
append_to_file(pmgs_path, pmgs_content)

# 4. Insert scripted effects after solar_collector_construction
print("4. Adding scripted effects...")
effects_path = os.path.join(mod_path, "common", "scripted_effects", "extra_effects.txt")
# Find the end of solar_collector_construction and insert after it
effects_content = read_file_content(effects_path)
# We need to find the closing brace of solar_collector_construction
# It ends before "thought_control_loyalists_update"
marker = "thought_control_loyalists_update = {"
if marker in effects_content:
    effects_content = effects_content.replace(
        marker,
        scripted_effects_content.lstrip('\n') + '\n' + marker
    )
    with open(effects_path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(effects_content.encode('utf-8'))
    print(f"  Inserted into {os.path.relpath(effects_path, mod_path)}")
else:
    print(f"  ERROR: Could not find insertion point in {effects_path}")
    print(f"  Appending to end instead...")
    append_to_file(effects_path, scripted_effects_content)

# 5. Wire on-actions to on_monthly_pulse_state AND add action definitions
print("5. Wiring on-actions...")
on_actions_path = os.path.join(mod_path, "common", "on_actions", "extra_on_actions.txt")
oa_content = read_file_content(on_actions_path)
# Add to on_monthly_pulse_state list (after solar_collector_on_action)
oa_content = oa_content.replace(
    "\t\tsolar_collector_on_action\n",
    "\t\tsolar_collector_on_action\n\t\torbital_battlestation_on_action\n\t\tmind_upload_nexus_on_action\n"
)
# Append the action definitions
oa_content += on_actions_content
with open(on_actions_path, 'wb') as f:
    f.write(b'\xef\xbb\xbf')
    f.write(oa_content.encode('utf-8'))
print(f"  Updated {os.path.relpath(on_actions_path, mod_path)}")

# 6. Add modifier type definitions
print("6. Adding modifier type definitions...")
mod_types_path = os.path.join(mod_path, "common", "modifier_type_definitions", "extra_modifier_types.txt")
append_to_file(mod_types_path, modifier_types_content)

# 7. Add static modifiers (insert after solar_collector_progress block)
print("7. Adding static modifiers...")
static_mod_path = os.path.join(mod_path, "common", "static_modifiers", "extra_modifiers.txt")
sm_content = read_file_content(static_mod_path)
marker2 = "solar_collector_progress = {\n\ticon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds\n\tbuilding_total_solar_collector_progress = 1\n}"
if marker2 in sm_content:
    sm_content = sm_content.replace(
        marker2,
        marker2 + '\n\n' + static_modifiers_content
    )
    with open(static_mod_path, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(sm_content.encode('utf-8'))
    print(f"  Updated {os.path.relpath(static_mod_path, mod_path)}")
else:
    print(f"  WARNING: Exact marker not found, appending to end")
    append_to_file(static_mod_path, static_modifiers_content)

print("\n=== All game data files updated ===")
print("\nRemaining: Localization files need to be updated separately.")
