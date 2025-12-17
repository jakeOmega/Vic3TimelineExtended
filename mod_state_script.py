from collections import defaultdict

from mod_state import ModState
from path_constants import base_game_path, doc_path, mod_path

base_game_paths = {
    "Building Groups": base_game_path + r"\game\common\building_groups",
    "Buildings": base_game_path + r"\game\common\buildings",
    "Technologies": base_game_path + r"\game\common\technology\technologies",
    "PM Groups": base_game_path + r"\game\common\production_method_groups",
    "PMs": base_game_path + r"\game\common\production_methods",
    "Ideologies": base_game_path + r"\game\common\ideologies",
    "Buy Packages": base_game_path + r"\game\common\buy_packages",
    "Character Interactions": base_game_path + r"\game\common\character_interactions",
    "Character Traits": base_game_path + r"\game\common\character_traits",
    "Combat Unit Groups": base_game_path + r"\game\common\combat_unit_groups",
    "Combat Unit Types": base_game_path + r"\game\common\combat_unit_types",
    "Company Types": base_game_path + r"\game\common\company_types",
    # "Customizable Localization": base_game_path + r"\game\common\customizable_localization",
    # "Decisions": base_game_path + r"\game\common\decisions",
    # "Defines": base_game_path + r"\game\common\defines",
    "Diplomatic Actions": base_game_path + r"\game\common\diplomatic_actions",
    "Diplomatic Plays": base_game_path + r"\game\common\diplomatic_plays",
    "Goods": base_game_path + r"\game\common\goods",
    "Institutions": base_game_path + r"\game\common\institutions",
    "Interest Groups": base_game_path + r"\game\common\interest_groups",
    "Law Groups": base_game_path + r"\game\common\law_groups",
    "Laws": base_game_path + r"\game\common\laws",
    "Mobilization Option Groups": base_game_path
    + r"\game\common\mobilization_option_groups",
    "Mobilization Options": base_game_path + r"\game\common\mobilization_options",
    "Modifier Types": base_game_path + r"\game\common\modifier_type_definitions",
    "Modifiers": base_game_path + r"\game\common\static_modifiers",
    # "On Actions": base_game_path + r"\game\common\on_actions",
    "Pop Needs": base_game_path + r"\game\common\pop_needs",
    # "Script Values": base_game_path + r"\game\common\script_values",
    # "Scripted Effects": base_game_path + r"\game\common\scripted_effects",
    "Subject Types": base_game_path + r"\game\common\subject_types",
}

mod_paths = {
    "Building Groups": mod_path + r"\common\building_groups",
    "Buildings": mod_path + r"\common\buildings",
    "Technologies": mod_path + r"\common\technology\technologies",
    "PM Groups": mod_path + r"\common\production_method_groups",
    "PMs": mod_path + r"\common\production_methods",
    "Ideologies": mod_path + r"\common\ideologies",
    "Buy Packages": mod_path + r"\common\buy_packages",
    "Character Interactions": mod_path + r"\common\character_interactions",
    "Character Traits": mod_path + r"\common\character_traits",
    "Combat Unit Groups": mod_path + r"\common\combat_unit_groups",
    "Combat Unit Types": mod_path + r"\common\combat_unit_types",
    "Company Types": mod_path + r"\common\company_types",
    # "Customizable Localization": mod_path + r"\common\customizable_localization",
    # "Decisions": mod_path + r"\common\decisions",
    # "Defines": mod_path + r"\common\defines",
    "Diplomatic Actions": mod_path + r"\common\diplomatic_actions",
    "Diplomatic Plays": mod_path + r"\common\diplomatic_plays",
    "Goods": mod_path + r"\common\goods",
    "Institutions": mod_path + r"\common\institutions",
    "Interest Groups": mod_path + r"\common\interest_groups",
    "Laws": mod_path + r"\common\laws",
    "Law Groups": mod_path + r"\common\law_groups",
    "Mobilization Option Groups": mod_path + r"\common\mobilization_option_groups",
    "Mobilization Options": mod_path + r"\common\mobilization_options",
    "Modifier Types": mod_path + r"\common\modifier_type_definitions",
    "Modifiers": mod_path + r"\common\static_modifiers",
    # "On Actions": mod_path + r"\common\on_actions",
    "Pop Needs": mod_path + r"\common\pop_needs",
    # "Script Values": mod_path + r"\common\script_values",
    # "Scripted Effects": mod_path + r"\common\scripted_effects",
    "Subject Types": mod_path + r"\common\subject_types",
}

mod_state = ModState(base_game_paths, mod_paths)
mod_state.add_localization(base_game_path + r"\game\localization\english")
mod_state.add_localization(mod_path + r"\localization\english")
mod_state.add_localization(mod_path + r"\localization\english\replace")


laws_path = doc_path + r"\laws.txt"
laws_output = ""
laws = mod_state.get_data("Laws")
laws_dict = {}
for law_id, (_, law_data) in laws.items():
    law_group = law_data["group"][1]
    if law_group not in laws_dict.keys():
        laws_dict[law_group] = []
    laws_dict[law_group].append(law_id)

for law_group in laws_dict.keys():
    laws_output += f"{mod_state.localize(law_group)}:\n"
    for law_id in laws_dict[law_group]:
        laws_output += f"\t{mod_state.localize(law_id)}"
        variant_of = laws[law_id][1].get("parent", None)
        if variant_of:
            laws_output += f" (Variant of {mod_state.localize(variant_of[1])})"
        unlocking_tech_ids = laws[law_id][1].get("unlocking_technologies", None)
        if unlocking_tech_ids:
            if unlocking_tech_ids[1]:
                tech_name = mod_state.localize(unlocking_tech_ids[1][0])
                laws_output += f" - Unlocking Technology: {tech_name}"
        laws_output += "\n"

with open(laws_path, "w", encoding="utf-8") as f:
    f.write(laws_output)

"""
mod_state.save_changes_to_json(r"F:\Libraries\Documents\testing")

loaded_mod_state = ModState(base_game_path, r"F:\Libraries\Documents\testing", diff=True)
for type, loc in mod_path.items():
    os.makedirs(r"F:\Libraries\Documents\testing\loaded_mod\\" + type, exist_ok=True)
    new_loc = r"F:\Libraries\Documents\testing\loaded_mod\\" + type + r"\modded.txt"
    loaded_mod_state.update_and_write_file(type, new_loc)
"""

"""
ideologies = mod_state.get_data("Ideologies")
for ideology_id, (_, ideology_data) in ideologies.items():
    if "lawgroup_rights_of_women" in ideology_data.keys():
        laws = ideology_data["lawgroup_rights_of_women"][1].keys()
        if "law_protected_class" not in laws:
            print(ideology_id, laws)
"""

# mod_state.update_and_write_file("PM Groups", "F:\Libraries\Documents\pmg_ownership.txt")

# mod_state.save_changes_to_json(r"F:\Libraries\Documents\testing")
# mod_state_from_json = ModState(
#    base_game_path, r"F:\Libraries\Documents\testing", diff=True
# )


bonuses = {}
counts = {}
cat_counts = {}
eras = [
    "era_1",
    "era_2",
    "era_3",
    "era_4",
    "era_5",
    "era_6",
    "era_7",
    "era_8",
    "era_9",
    "era_10",
    "era_11",
    "era_12",
]

tech_path = doc_path + r"\technologies.txt"
tech_output = ""
tech = mod_state.get_data("Technologies")
tech_dict = defaultdict(list)
for tech_id, (_, tech_data) in tech.items():
    era = tech_data.get("era", ["", "era_0"])[1]
    era_int = int(era.split("_")[-1])
    tech_dict[era_int].append(tech_id)

for era in range(1, 13):
    tech_output += f"{era}: {len(tech_dict[era])} technologies\n"
    for tech_id in tech_dict[era]:
        tech_output += f"\t{mod_state.localize(tech_id)}"
        description = mod_state.get_description(tech_id)
        if description is not None:
            tech_output += f" - {description}"
        tech_output += "\n"
        tech_requirement = tech[tech_id][1].get("unlocking_technologies", None)
        if tech_requirement:
            tech_requirement_ids = tech_requirement[1]
            if tech_requirement_ids:
                tech_output += "\t\tUnlocking Technologies:\n"
                for unlocking_tech_ids in tech_requirement_ids:
                    tech_output += f"\t\t\t{mod_state.localize(unlocking_tech_ids)}\n"

with open(tech_path, "w", encoding="utf-8") as f:
    f.write(tech_output)

building_path = doc_path + r"\buildings.txt"
building_output = ""
buildings_data = mod_state.get_data("Buildings")
pmg_groups = mod_state.get_data("PM Groups")
production_methods = mod_state.get_data("PMs")
for building_id, data in buildings_data.items():
    pm_groups = data[1].get("production_method_groups", ["", []])[1]
    building_output += f"{mod_state.localize(building_id)}:\n"
    tech_requirement = data[1].get("unlocking_technologies", None)
    if tech_requirement:
        tech_name = mod_state.localize(tech_requirement[1][0])
        building_output += f"\tUnlocking Technology: {tech_name}\n"
    for pmg in pm_groups:
        if pmg not in pmg_groups.keys():
            building_output += f"Building {mod_state.localize(building_id)} references missing PM Group {mod_state.localize(pmg)}\n"
            continue
        building_output += f"\t{mod_state.localize(pmg)}:\n"
        pms = pmg_groups[pmg][1].get("production_methods", ["", []])[1]
        for pm in pms:
            if pm not in production_methods.keys():
                building_output += f"Building {mod_state.localize(building_id)} references missing PM {mod_state.localize(pm)}\n"
                continue
            building_output += f"\t\t{mod_state.localize(pm)}\n"
            pm_data = production_methods[pm][1]
            # TODO: Why is it sometimes a list??
            if isinstance(pm_data, list):
                pm_data_flat = {}
                for e in pm_data:
                    pm_data_flat.update(e)
                pm_data = pm_data_flat
            tech_requirement = pm_data.get("unlocking_technologies", None)
            if tech_requirement:
                if tech_requirement[1]:
                    tech_name = mod_state.localize(tech_requirement[1][0])
                    building_output += f"\t\t\tUnlocking Technology: {tech_name}\n"
    building_output += "\n"

with open(building_path, "w", encoding="utf-8") as f:
    f.write(building_output)

goods_path = doc_path + r"\goods.txt"
goods_output = ""
goods = mod_state.get_data("Goods")
for good_id, _ in goods.items():
    goods_output += f"{mod_state.localize(good_id)}\n"

with open(goods_path, "w", encoding="utf-8") as f:
    f.write(goods_output)


combat_units_path = doc_path + r"\combat_units.txt"
combat_units_output = ""
combat_unit_groups = mod_state.get_data("Combat Unit Groups")
combat_unit_types = mod_state.get_data("Combat Unit Types")

combat_unit_dict = defaultdict(list)
for type, data in combat_unit_types.items():
    group_data = data[1]
    if isinstance(group_data, list):
        group_data_flat = {}
        for e in group_data:
            group_data_flat.update(e)
        group_data = group_data_flat
    group = group_data.get("group")[1]
    combat_unit_dict[group] += [type]

for group in combat_unit_groups.keys():
    combat_units_output += f"{mod_state.localize(group)}:\n"
    for type in combat_unit_dict[group]:
        combat_units_output += f"\t{mod_state.localize(type)}\n"
        unit_data = combat_unit_types[type][1]
        if isinstance(unit_data, list):
            unit_data_flat = {}
            for e in unit_data:
                unit_data_flat.update(e)
            unit_data = unit_data_flat
        tech_requirement = unit_data.get("unlocking_technologies", None)
        if tech_requirement:
            if tech_requirement[1]:
                tech_name = mod_state.localize(tech_requirement[1][0])
                combat_units_output += f"\t\tUnlocking Technology: {tech_name}\n"

with open(combat_units_path, "w", encoding="utf-8") as f:
    f.write(combat_units_output)

# Updating and writing back to a file
# buildings_data['new_building'] = {...}
# mod_state.update_and_write_file("Buildings", "/path/to/mod/buildings/updated_building.txt")
print("Done!")
