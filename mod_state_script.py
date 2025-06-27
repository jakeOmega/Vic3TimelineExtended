from mod_state import ModState
import os
from path_constants import base_game_path, mod_path

base_game_path = {
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
    "Decisions": base_game_path + r"\game\common\decisions",
    # "Defines": base_game_path + r"\game\common\defines",
    "Diplomatic Actions": base_game_path + r"\game\common\diplomatic_actions",
    "Diplomatic Plays": base_game_path + r"\game\common\diplomatic_plays",
    "Goods": base_game_path + r"\game\common\goods",
    "Institutions": base_game_path + r"\game\common\institutions",
    "Interest Groups": base_game_path + r"\game\common\interest_groups",
    "Law Groups": base_game_path + r"\game\common\law_groups",
    "Laws": base_game_path + r"\game\common\laws",
    "Mobilization Option Groups": base_game_path + r"\game\common\mobilization_option_groups",
    "Mobilization Options": base_game_path + r"\game\common\mobilization_options",
    # "Modifier Types": base_game_path + r"\game\common\modifier_types",
    "Modifiers": base_game_path + r"\game\common\static_modifiers",
    # "On Actions": base_game_path + r"\game\common\on_actions",
    "Pop Needs": base_game_path + r"\game\common\pop_needs",
    # "Script Values": base_game_path + r"\game\common\script_values",
    # "Scripted Effects": base_game_path + r"\game\common\scripted_effects",
    "Subject Types": base_game_path + r"\game\common\subject_types",
}

mod_path = {
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
    "Decisions": mod_path + r"\common\decisions",
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
    # "Modifier Types": mod_path + r"\common\modifier_types",
    "Modifiers": mod_path + r"\common\static_modifiers",
    # "On Actions": mod_path + r"\common\on_actions",
    "Pop Needs": mod_path + r"\common\pop_needs",
    # "Script Values": mod_path + r"\common\script_values",
    # "Scripted Effects": mod_path + r"\common\scripted_effects",
    "Subject Types": mod_path + r"\common\subject_types",
}

mod_state = ModState(base_game_path, mod_path)
laws = mod_state.get_data("Laws")
laws_dict = {}
for law_id, (_, law_data) in laws.items():
    law_group = law_data["group"][1]
    if law_group not in laws_dict.keys():
        laws_dict[law_group] = []
    laws_dict[law_group].append(law_id)

for law_group in laws_dict.keys():
    print(law_group)
    for law_id in laws_dict[law_group]:
        print("\t", law_id)

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

for era in eras:
    for category in ["production", "military", "society"]:
        bonuses[(category, era)] = 0
        cat_counts[(category, era)] = 0
    counts[era] = 0

tech = mod_state.get_data("Technologies")
for tech_id, (_, tech_data) in tech.items():
    _, category = tech_data["category"]
    _, era = tech_data["era"]
    if era not in eras:
        continue
    counts[era] += 1
    cat_counts[(category, era)] += 1
    if "modifier" not in tech_data.keys():
        continue
    _, modifier = tech_data["modifier"]
    if len(modifier) == 0:
        continue
    if "country_weekly_innovation_max_add" not in modifier.keys():
        continue
    _, bonus = modifier["country_weekly_innovation_max_add"]
    bonuses[(category, era)] += int(bonus)

years_per_era = [40, 40, 40, 40, 30, 30, 20, 20, 20, 20, 20, 20]
weeks_per_era = [52 * year for year in years_per_era]
research_speeds = {}
for era in eras:
    research_speeds[era] = 0
for era in eras:
    for category in ["production", "military", "society"]:
        research_speeds[era] += bonuses[(category, era)]

cumulative_research_speed = 200
research_speed_mult = 2.5
for era_num in range(1, len(eras)):
    era = eras[era_num]
    end_speed, start_speed = (
        research_speeds[era] + cumulative_research_speed,
        cumulative_research_speed,
    )
    cumulative_research_speed = end_speed
    avg_research_speed = (end_speed + start_speed) * research_speed_mult/ 2
    cost_per_tech = avg_research_speed * weeks_per_era[era_num] / counts[era]
    print(
        f"{era:6}",
        "cost per tech: ",
        f"{cost_per_tech:9.2f}",
        " research speed: ",
        f"{avg_research_speed:7.2f}",
        " tech count: ",
        f"{counts[era]:3}",
        " production: ",
        f'{cat_counts[("production", era)]:3}',
        " military: ",
        f'{cat_counts[("military", era)]:3}',
        " society: ",
        f'{cat_counts[("society", era)]:3}',
    )


# Updating and writing back to a file
# buildings_data['new_building'] = {...}
# mod_state.update_and_write_file("Buildings", "/path/to/mod/buildings/updated_building.txt")
