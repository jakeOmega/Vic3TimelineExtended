from mod_state import ModState

base_game_dir = {
    # "Building Groups": r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\building_groups",
    # "Buildings": r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\buildings",
    # "Technologies": r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\technology\technologies",
    # "PM Groups": r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\production_method_groups",
    # "PMs": r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\production_methods",
    "Ideologies": r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\ideologies",
}

mod_dir = {
    # "Building Groups": r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\building_groups",
    # "Buildings": r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\buildings",
    # "Technologies": r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\technology\technologies",
    # "PM Groups": r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\production_method_groups",
    # "PMs": r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\production_methods",
    "Ideologies": r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\ideologies",
}

mod_state = ModState(base_game_dir, mod_dir)

ideologies = mod_state.get_data("Ideologies")
for ideology_id, (_, ideology_data) in ideologies.items():
    if "lawgroup_rights_of_women" in ideology_data.keys():
        laws = ideology_data["lawgroup_rights_of_women"][1].keys()
        if "law_protected_class" not in laws:
            print(ideology_id, laws)

# mod_state.update_and_write_file("PM Groups", "F:\Libraries\Documents\pmg_ownership.txt")

# mod_state.save_changes_to_json(r"F:\Libraries\Documents\testing")
# mod_state_from_json = ModState(
#    base_game_dir, r"F:\Libraries\Documents\testing", diff=True
# )


"""
bonuses = {}
counts = {}
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
]

for era in eras:
    for category in ["production", "military", "society"]:
        bonuses[(category, era)] = 0
    counts[era] = 0

tech = mod_state.get_data("Technologies")
for tech_id, (_, tech_data) in tech.items():
    _, category = tech_data["category"]
    _, era = tech_data["era"]
    if era not in eras:
        continue
    counts[era] += 1
    if "modifier" not in tech_data.keys():
        continue
    _, modifier = tech_data["modifier"]
    if len(modifier) == 0 or "country_weekly_innovation_max_add" not in modifier.keys():
        continue
    _, bonus = modifier["country_weekly_innovation_max_add"]
    bonuses[(category, era)] += int(bonus)

years_per_era = [40, 40, 40, 40, 30, 30, 20, 20, 20, 20, 20]
weeks_per_era = [52 * year for year in years_per_era]
research_speeds = {}
for era in eras:
    research_speeds[era] = 0
for era in eras:
    for category in ["production", "military", "society"]:
        research_speeds[era] += bonuses[(category, era)]

cumulative_research_speed = 200
for era_num in range(1, len(eras)):
    era = eras[era_num]
    end_speed, start_speed = (
        research_speeds[era] + cumulative_research_speed,
        cumulative_research_speed,
    )
    cumulative_research_speed = end_speed
    avg_research_speed = (end_speed + start_speed) / 2
    cost_per_tech = avg_research_speed * weeks_per_era[era_num] / counts[era]
    print(
        era,
        "cost per tech: ",
        cost_per_tech,
        " research speed: ",
        avg_research_speed,
        " tech count: ",
        counts[era],
    )
"""

# Updating and writing back to a file
# buildings_data['new_building'] = {...}
# mod_state.update_and_write_file("Buildings", "/path/to/mod/buildings/updated_building.txt")
