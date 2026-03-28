#!/usr/bin/env python3
"""Generate antimatter facility wonder buildings and overbuild protection."""

import os
import sys

mod_path = os.path.dirname(os.path.abspath(__file__))


def append_to_file(filepath, content):
    """Append content to a BOM-encoded file, preserving the BOM."""
    with open(filepath, 'rb') as f:
        existing_bytes = f.read()
    if existing_bytes.startswith(b'\xef\xbb\xbf'):
        existing_text = existing_bytes[3:].decode('utf-8')
    else:
        existing_text = existing_bytes.decode('utf-8')
    if not existing_text.endswith('\n'):
        existing_text += '\n'
    existing_text += content
    with open(filepath, 'wb') as f:
        f.write(b'\xef\xbb\xbf')
        f.write(existing_text.encode('utf-8'))


def build_removal_iterations(modifier, buildings, count=5):
    """Generate N if-blocks that each remove one level of excess buildings."""
    result = []
    for _ in range(count):
        if len(buildings) == 1:
            b = buildings[0]
            result.append(
                "\t\tif = {\n"
                f"\t\t\tlimit = {{ modifier:{modifier} < 0 }}\n"
                "\t\t\trandom_scope_state = {\n"
                f"\t\t\t\tlimit = {{ has_building = {b} }}\n"
                f"\t\t\t\tremove_building = {b}\n"
                "\t\t\t}\n"
                "\t\t}"
            )
        else:
            or_part = "".join(f"\t\t\t\t\t\thas_building = {b}\n" for b in buildings)
            if_part = ""
            for i, b in enumerate(buildings):
                kw = "if" if i == 0 else "else_if"
                if_part += (
                    f"\t\t\t\t{kw} = {{\n"
                    f"\t\t\t\t\tlimit = {{ has_building = {b} }}\n"
                    f"\t\t\t\t\tremove_building = {b}\n"
                    f"\t\t\t\t}}\n"
                )
            result.append(
                "\t\tif = {\n"
                f"\t\t\tlimit = {{ modifier:{modifier} < 0 }}\n"
                "\t\t\trandom_scope_state = {\n"
                "\t\t\t\tlimit = {\n"
                "\t\t\t\t\tOR = {\n"
                f"{or_part}"
                "\t\t\t\t\t}\n"
                "\t\t\t\t}\n"
                f"{if_part}"
                "\t\t\t}\n"
                "\t\t}"
            )
    return "\n".join(result)


# =====================================================================
# BUILDINGS
# =====================================================================
buildings_content = """\
#==================================================
# Antimatter Facility Buildings
#==================================================

REPLACE_OR_CREATE:building_antimatter_facility_construction_site = {
\tbuilding_group = bg_government
\ticon = "gfx/interface/icons/building_icons/space_elevator_construction_site.dds"
\tcity_type = city
\tlevels_per_mesh = -1
\t
\tunlocking_technologies = {
\t\tantimatter_production
\t}

\tproduction_method_groups = {
\t\tpmg_base_building_antimatter_facility_construction_site
\t}

\trequired_construction = construction_cost_medium
\t
\texpandable = no
\t
\townership_type = no_ownership
\tbackground = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"
}

REPLACE_OR_CREATE:building_antimatter_facility = {
\tbuilding_group = bg_government
\ticon = "gfx/interface/icons/building_icons/power_plant.dds"
\tcity_type = city
\tlevels_per_mesh = -1

\tproduction_method_groups = {
\t\tpmg_base_building_antimatter_facility
\t}

\trequired_construction = construction_cost_canal
\t
\tbuildable = no
\texpandable = no
\townership_type = self
\tbackground = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"
}

REPLACE_OR_CREATE:building_antimatter_engine = {
\tbuilding_group = bg_private_infrastructure
\ticon = "gfx/interface/icons/building_icons/power_plant.dds"
\tcity_type = city
\tlevels_per_mesh = -1
\t
\tunlocking_technologies = {
\t\tantimatter_production
\t}

\tproduction_method_groups = {
\t\tpmg_base_building_antimatter_engine
\t}

\trequired_construction = construction_cost_medium
\t
\tpossible = {
\t\towner = {
\t\t\tmodifier:country_antimatter_facility_max_level_add > 0
\t\t}
\t}
\t
\townership_type = self
\tbackground = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"
}

REPLACE_OR_CREATE:building_antimatter_warhead_plant = {
\tbuilding_group = bg_military
\ticon = "gfx/interface/icons/building_icons/space_base.dds"
\tcity_type = city
\tlevels_per_mesh = -1
\t
\tunlocking_technologies = {
\t\tantimatter_production
\t}

\tproduction_method_groups = {
\t\tpmg_base_building_antimatter_warhead_plant
\t}

\trequired_construction = construction_cost_medium
\t
\tpossible = {
\t\towner = {
\t\t\tmodifier:country_antimatter_facility_max_level_add > 0
\t\t}
\t}
\t
\townership_type = self
\tbackground = "gfx/interface/icons/building_icons/backgrounds/building_panel_bg_monuments.dds"
}
"""

# =====================================================================
# PRODUCTION METHODS
# =====================================================================
pms_content = """\

#==================================================
# Antimatter Facility PMs
#==================================================

pm_antimatter_facility_construction_paused = {
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

pm_antimatter_facility_construction_slow = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 5000              # Price: 4000, Total cost: 20000000.0 (88.69%)
\t\t\tgoods_input_electronic_components_add = 10000          # Price:   80, Total cost: 800000.0 (3.55%)
\t\t\tgoods_input_electricity_add = 50000                    # Price:   30, Total cost: 1500000.0 (6.65%)
\t\t\tgoods_input_steel_add = 5000                           # Price:   50, Total cost: 250000.0 (1.11%)
\t\t\t# Total input cost: 22550000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 25000
\t\t\tbuilding_employment_academics_add = 25000
\t\t}
\t}

\trequired_input_goods = electricity
}

pm_antimatter_facility_construction_medium = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 10000             # Price: 4000, Total cost: 40000000.0 (88.69%)
\t\t\tgoods_input_electronic_components_add = 20000          # Price:   80, Total cost: 1600000.0 (3.55%)
\t\t\tgoods_input_electricity_add = 100000                   # Price:   30, Total cost: 3000000.0 (6.65%)
\t\t\tgoods_input_steel_add = 10000                          # Price:   50, Total cost: 500000.0 (1.11%)
\t\t\t# Total input cost: 45100000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 25000
\t\t\tbuilding_employment_academics_add = 25000
\t\t}
\t}

\trequired_input_goods = electricity
}

pm_antimatter_facility_construction_fast = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_advanced_materials_add = 20000             # Price: 4000, Total cost: 80000000.0 (88.69%)
\t\t\tgoods_input_electronic_components_add = 40000          # Price:   80, Total cost: 3200000.0 (3.55%)
\t\t\tgoods_input_electricity_add = 200000                   # Price:   30, Total cost: 6000000.0 (6.65%)
\t\t\tgoods_input_steel_add = 20000                          # Price:   50, Total cost: 1000000.0 (1.11%)
\t\t\t# Total input cost: 90200000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 25000
\t\t\tbuilding_employment_academics_add = 25000
\t\t}
\t}

\trequired_input_goods = electricity
}

# Antimatter facility hub - enables antimatter sub-building slots
pm_antimatter_facility = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tcountry_modifiers = {
\t\tlevel_scaled = {
\t\t\tcountry_antimatter_facility_max_level_add = 5
\t\t}
\t}

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_electricity_add = 50000                    # Price:   30, Total cost: 1500000.0 (64.26%)
\t\t\tgoods_input_advanced_materials_add = 200               # Price: 4000, Total cost: 800000.0 (34.28%)
\t\t\tgoods_input_electronic_components_add = 300            # Price:   80, Total cost: 24000.0 (1.03%)
\t\t\tgoods_input_steel_add = 200                            # Price:   50, Total cost: 10000.0 (0.43%)
\t\t\t# Total input cost: 2334000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 3000
\t\t\tbuilding_employment_academics_add = 3000
\t\t}
\t}

\trequired_input_goods = electricity
}

# Antimatter engine - propulsion applications
pm_antimatter_engine = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tcountry_modifiers = {
\t\tlevel_scaled = {
\t\t\tcountry_antimatter_facility_max_level_add = -1
\t\t\tmilitary_formation_movement_speed_mult = 0.02
\t\t\tcountry_convoys_capacity_mult = 0.01
\t\t}
\t}

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_electricity_add = 5000                     # Price:   30, Total cost: 150000.0 (64.10%)
\t\t\tgoods_input_advanced_materials_add = 20                # Price: 4000, Total cost: 80000.0 (34.19%)
\t\t\tgoods_input_electronic_components_add = 50             # Price:   80, Total cost: 4000.0 (1.71%)
\t\t\t# Total input cost: 234000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 500
\t\t\tbuilding_employment_officers_add = 500
\t\t}
\t}

\trequired_input_goods = electricity
}

# Antimatter warhead plant - weapons applications
pm_antimatter_warhead_plant = {
\ttexture = "gfx/interface/icons/production_method_icons/base3.dds"

\tcountry_modifiers = {
\t\tlevel_scaled = {
\t\t\tcountry_antimatter_facility_max_level_add = -1
\t\t\tcountry_nuclear_weapon_attack_success_add = 0.03
\t\t\tunit_offense_mult = 0.01
\t\t}
\t}

\tbuilding_modifiers = {
\t\tworkforce_scaled = {
\t\t\tgoods_input_electricity_add = 5000                     # Price:   30, Total cost: 150000.0 (62.76%)
\t\t\tgoods_input_advanced_materials_add = 20                # Price: 4000, Total cost: 80000.0 (33.47%)
\t\t\tgoods_input_explosives_add = 100                       # Price:   50, Total cost: 5000.0 (2.09%)
\t\t\tgoods_input_electronic_components_add = 50             # Price:   80, Total cost: 4000.0 (1.67%)
\t\t\t# Total input cost: 239000.0
\t\t}

\t\tlevel_scaled = {
\t\t\tbuilding_employment_engineers_add = 500
\t\t\tbuilding_employment_officers_add = 500
\t\t\tbuilding_employment_academics_add = 250
\t\t}
\t}

\trequired_input_goods = electricity
}
"""

# =====================================================================
# PRODUCTION METHOD GROUPS
# =====================================================================
pmgs_content = """\

#==================================================
# Antimatter Facility PMGs
#==================================================

pmg_base_building_antimatter_facility_construction_site = {
\tproduction_methods = {
\t\tpm_antimatter_facility_construction_paused
\t\tpm_antimatter_facility_construction_slow
\t\tpm_antimatter_facility_construction_medium
\t\tpm_antimatter_facility_construction_fast
\t}
}

pmg_base_building_antimatter_facility = {
\tproduction_methods = {
\t\tpm_antimatter_facility
\t}
}

pmg_base_building_antimatter_engine = {
\tproduction_methods = {
\t\tpm_antimatter_engine
\t}
}

pmg_base_building_antimatter_warhead_plant = {
\tproduction_methods = {
\t\tpm_antimatter_warhead_plant
\t}
}
"""

# =====================================================================
# SCRIPTED EFFECTS
# =====================================================================
effects_content = """\

#==================================================
# Antimatter Facility Construction Effect
#==================================================

antimatter_facility_construction = {
\tif = {
\t\tlimit = {
\t\t\tNOT = { has_variable = antimatter_facility_progress_var }
\t\t}
\t\tset_variable = {
\t\t\tname = antimatter_facility_progress_var
\t\t\tvalue = 0
\t\t}
\t}
\tif = {
\t\tlimit = {
\t\t\thas_variable = antimatter_facility_progress_var
\t\t\tany_scope_building = {
\t\t\t\tis_building_type = building_antimatter_facility_construction_site
\t\t\t\tbuilding_has_goods_shortage = no
\t\t\t}
\t\t}
\t\tchange_variable = {
\t\t\tname = antimatter_facility_progress_var
\t\t\tadd = {
\t\t\t\tvalue = b:building_antimatter_facility_construction_site.occupancy
\t\t\t\tdivide = 12
\t\t\t\tif = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_scope_building = { has_active_production_method = pm_antimatter_facility_construction_slow }
\t\t\t\t\t}
\t\t\t\t\tmultiply = 0.25
\t\t\t\t}
\t\t\t\telse_if = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_scope_building = { has_active_production_method = pm_antimatter_facility_construction_medium }
\t\t\t\t\t}
\t\t\t\t\tmultiply = 0.5
\t\t\t\t}
\t\t\t\telse_if = {
\t\t\t\t\tlimit = {
\t\t\t\t\t\tany_scope_building = { has_active_production_method = pm_antimatter_facility_construction_fast }
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
\t\t\tvar:antimatter_facility_progress_var >= 1
\t\t}
\t\tset_variable = {
\t\t\tname = antimatter_facility_progress_var
\t\t\tvalue = 0
\t\t}
\t\tremove_building = building_antimatter_facility_construction_site
\t\tif = {
\t\t\tlimit = { has_building = building_antimatter_facility }
\t\t\tswitch = {
\t\t\t\ttrigger = b:building_antimatter_facility.level
\t\t\t\t1 = { create_building = { building = building_antimatter_facility level = 2 } }
\t\t\t\t2 = { create_building = { building = building_antimatter_facility level = 3 } }
\t\t\t\t3 = { create_building = { building = building_antimatter_facility level = 4 } }
\t\t\t\t4 = { create_building = { building = building_antimatter_facility level = 5 } }
\t\t\t\t5 = { create_building = { building = building_antimatter_facility level = 6 } }
\t\t\t\t6 = { create_building = { building = building_antimatter_facility level = 7 } }
\t\t\t\t7 = { create_building = { building = building_antimatter_facility level = 8 } }
\t\t\t\t8 = { create_building = { building = building_antimatter_facility level = 9 } }
\t\t\t\t9 = { create_building = { building = building_antimatter_facility level = 10 } }
\t\t\t}
\t\t}
\t\telse = {
\t\t\tcreate_building = {
\t\t\t\tbuilding = building_antimatter_facility
\t\t\t\tlevel = 1
\t\t\t}
\t\t}
\t}
}
"""

# =====================================================================
# ON-ACTIONS (definitions only - wiring done via replace_string_in_file)
# =====================================================================

solar_removals = build_removal_iterations(
    "country_solar_receiver_max_level_add",
    ["building_solar_receiver"],
    5
)

antimatter_removals = build_removal_iterations(
    "country_antimatter_facility_max_level_add",
    ["building_antimatter_engine", "building_antimatter_warhead_plant"],
    5
)

on_actions_content = f"""\

#==================================================
# Antimatter Facility Construction On-Action
#==================================================

antimatter_facility_on_action = {{
\teffect = {{
\t\tif = {{
\t\t\tlimit = {{
\t\t\t\thas_building = building_antimatter_facility_construction_site
\t\t\t}}
\t\t\tantimatter_facility_construction = yes
\t\t\tevery_scope_building = {{
\t\t\t\tlimit = {{
\t\t\t\t\tis_building_type = building_antimatter_facility_construction_site
\t\t\t\t}}
\t\t\t\tremove_modifier = antimatter_facility_progress
\t\t\t\tadd_modifier = {{
\t\t\t\t\tname = antimatter_facility_progress
\t\t\t\t\tmultiplier = this.var:antimatter_facility_progress_var
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t}}
}}

#==================================================
# Overbuild Protection - removes excess sub-buildings
# when slot modifier goes negative (race condition fix)
#==================================================

overbuild_protection_on_action = {{
\teffect = {{
\t\t# Solar receivers - remove up to 5 excess per month
{solar_removals}
\t\t# Antimatter sub-buildings - remove up to 5 excess per month
{antimatter_removals}
\t}}
}}
"""

# =====================================================================
# MODIFIER TYPES
# =====================================================================
modifier_types_content = """\

#==================================================
# Antimatter Facility Modifier Types
#==================================================

building_annual_antimatter_facility_progress = {
\tcolor = good
\tpercent = yes
\tai_value = 50000000
}

building_total_antimatter_facility_progress = {
\tcolor = good
\tpercent = yes
}

country_antimatter_facility_max_level_add = {
\tcolor = good
\tpercent = no
\tdecimals = 0
}
"""

# =====================================================================
# STATIC MODIFIERS
# =====================================================================
static_modifiers_content = """\

#==================================================
# Antimatter Facility Progress Modifier
#==================================================

antimatter_facility_progress = {
\ticon = "gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds"

\tbuilding_total_antimatter_facility_progress = 1
}
"""


# =====================================================================
# MAIN
# =====================================================================
if __name__ == "__main__":
    files = {
        "buildings": os.path.join(mod_path, "common", "buildings", "extra_buildings.txt"),
        "pms": os.path.join(mod_path, "common", "production_methods", "extra_pms.txt"),
        "pmgs": os.path.join(mod_path, "common", "production_method_groups", "extra_pm_groups.txt"),
        "effects": os.path.join(mod_path, "common", "scripted_effects", "extra_effects.txt"),
        "on_actions": os.path.join(mod_path, "common", "on_actions", "extra_on_actions.txt"),
        "modifier_types": os.path.join(mod_path, "common", "modifier_type_definitions", "extra_modifier_types.txt"),
        "static_modifiers": os.path.join(mod_path, "common", "static_modifiers", "extra_modifiers.txt"),
    }

    append_to_file(files["buildings"], buildings_content)
    print("OK Appended 4 building definitions to extra_buildings.txt")

    append_to_file(files["pms"], pms_content)
    print("OK Appended 7 PM definitions to extra_pms.txt")

    append_to_file(files["pmgs"], pmgs_content)
    print("OK Appended 4 PMG definitions to extra_pm_groups.txt")

    append_to_file(files["effects"], effects_content)
    print("OK Appended antimatter_facility_construction effect to extra_effects.txt")

    append_to_file(files["on_actions"], on_actions_content)
    print("OK Appended antimatter + overbuild on-actions to extra_on_actions.txt")

    append_to_file(files["modifier_types"], modifier_types_content)
    print("OK Appended 3 modifier type definitions to extra_modifier_types.txt")

    append_to_file(files["static_modifiers"], static_modifiers_content)
    print("OK Appended antimatter_facility_progress static modifier to extra_modifiers.txt")

    print("\n--- REMAINING MANUAL STEPS ---")
    print("1. Wire antimatter_facility_on_action into on_monthly_pulse_state")
    print("2. Wire overbuild_protection_on_action into on_monthly_pulse_country")
    print("3. Add localization entries")
    print("4. Verify BOM encoding on all modified files")
