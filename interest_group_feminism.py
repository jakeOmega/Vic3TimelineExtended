import os
import regex
import json
import copy


def modify_interest_group_files(input_dir, output_dir, modification_dict):
    """
    Modifies all interest group files in the given directory, adjusting the probability of getting a female in various roles.

    :param input_dir: Directory containing the interest group files.
    :param output_dir: Directory where the modified files will be saved.
    :param modification_dict: Dictionary with modifications for each role, condition, and type (tech or law).
    """
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Iterate over all files in the input directory
    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)

        # Modify file if it's in the modification dictionary
        if filename in modification_dict:
            with open(file_path, "r", encoding="utf8") as file:
                content = file.read().replace("\ufeff", "")

            # Apply modifications for each role
            for role, conditions in modification_dict[filename].items():
                for condition, details in conditions.items():
                    condition_type, increase = details["type"], details["increase"]
                    condition_check = (
                        "has_technology_researched"
                        if condition_type == "technology"
                        else condition_type
                    )
                    search_pattern = rf"{role}.*?{condition_check}:{condition}.*?add\s*=\s*\{{\s*value\s*=\s*(\d*\.\d+|\d+)"

                    if regex.search(search_pattern, content, flags=regex.DOTALL):
                        # Modify existing condition
                        modification_pattern = rf"({role}.*?{condition_check}:{condition}.*?add\s*=\s*\{{\s*value\s*=\s*)(\d*\.\d+|\d+)"
                        content = regex.sub(
                            modification_pattern,
                            lambda m: f"{m.group(1)}{increase}",
                            content,
                            flags=regex.DOTALL,
                        )
                    else:
                        # Add new condition
                        new_condition = f"\n\t\tif = {{\n\t\t\tlimit = {{\n\t\t\t\towner = {{\n\t\t\t\t\t{condition_check} = {condition}\n\t\t\t\t}}\n\t\t\t}}\n\t\t\tadd = {{ value = {increase} }}\n\t\t}}"
                        pattern = regex.compile(
                            rf"""
                                {role}       # Match the specific string
                                \s*=\s*                  # Match an equals sign, potentially with whitespace around
                                \{{                      # Match an opening brace
                                (?<content>              # Start capturing group for the content
                                    (?:                  # Start a non-capturing group for the content
                                        [^{{}}]+         # Match any characters except braces
                                        |                # OR
                                        \{{              # An opening brace
                                            (?&content)  # Recursively match nested content
                                        \}}              # A closing brace
                                    )*                   # Repeat as necessary
                                )                        # End capturing group
                                \}}                      # Match the final closing brace
                            """,
                            regex.VERBOSE,
                        )
                        content = regex.sub(
                            pattern,
                            lambda m: f"{role} = {{{m.group('content')}\n\t\t{new_condition}\n\t}}",
                            content,
                        )

            # Write the modified content to a new file in the output directory
            with open(
                os.path.join(output_dir, filename), "w", encoding="utf-8"
            ) as file:
                file.write(content)

    return "Modification of interest group files completed."


def normalize_values(modifications, desired_total):
    new_modifications = copy.deepcopy(modifications)
    total_increase = sum(
        details["increase"]
        for item, details in modifications.items()
        if item != "law_type:law_comprehensive_rights"
    )
    scale_factor = desired_total / total_increase
    for item, details in modifications.items():
        normalized_increase = details["increase"] * scale_factor
        new_modifications[item]["increase"] = round(normalized_increase, 3)
    return new_modifications


tech_heavy = {
    "law_type:law_protected_class": {"type": "has_law", "increase": 4},
    "law_type:law_comprehensive_rights": {"type": "has_law", "increase": 1},
    "law_type:law_full_equality_and_protection": {"type": "has_law", "increase": 2},
    "second_wave_feminism": {"type": "technology", "increase": 8},
    "sexual_revolution": {"type": "technology", "increase": 4},
    "contraceptive_pill": {"type": "technology", "increase": 2},
    "LGBTQ_rights_movement": {"type": "technology", "increase": 1},
}

balanced = {
    "law_type:law_protected_class": {"type": "has_law", "increase": 8},
    "law_type:law_comprehensive_rights": {"type": "has_law", "increase": 2},
    "law_type:law_full_equality_and_protection": {"type": "has_law", "increase": 4},
    "second_wave_feminism": {"type": "technology", "increase": 4},
    "sexual_revolution": {"type": "technology", "increase": 2},
    "contraceptive_pill": {"type": "technology", "increase": 1},
    "LGBTQ_rights_movement": {"type": "technology", "increase": 1},
    "decline_of_organized_religion": {
        "type": "technology",
        "increase": 1,
    },
}

law_heavy = {
    "law_type:law_protected_class": {"type": "has_law", "increase": 20},
    "law_type:law_comprehensive_rights": {"type": "has_law", "increase": 4},
    "law_type:law_full_equality_and_protection": {"type": "has_law", "increase": 8},
    "second_wave_feminism": {"type": "technology", "increase": 6},
    "sexual_revolution": {"type": "technology", "increase": 3},
    "contraceptive_pill": {"type": "technology", "increase": 2},
    "LGBTQ_rights_movement": {"type": "technology", "increase": 1},
    "decline_of_organized_religion": {
        "type": "technology",
        "increase": 3,
    },
}

input_directory = (
    r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\interest_groups"
)
output_directory = r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\interest_groups"
modifications = {
    "00_armed_forces.txt": {
        "female_commander_chance": normalize_values(balanced, 0.3),
        "female_politician_chance": normalize_values(balanced, 0.4),
        "female_agitator_chance": normalize_values(balanced, 0.5),
    },
    "00_devout.txt": {
        "female_commander_chance": normalize_values(law_heavy, 0.1),
        "female_politician_chance": normalize_values(law_heavy, 0.3),
        "female_agitator_chance": normalize_values(law_heavy, 0.5),
    },
    "00_industrialists.txt": {
        "female_commander_chance": normalize_values(balanced, 0.3),
        "female_politician_chance": normalize_values(balanced, 0.4),
        "female_agitator_chance": normalize_values(balanced, 0.5),
    },
    "00_intelligentsia.txt": {
        "female_commander_chance": normalize_values(tech_heavy, 0.4),
        "female_politician_chance": normalize_values(tech_heavy, 0.5),
        "female_agitator_chance": normalize_values(tech_heavy, 0.5),
    },
    "00_landowners.txt": {
        "female_commander_chance": normalize_values(law_heavy, 0.3),
        "female_politician_chance": normalize_values(law_heavy, 0.4),
        "female_agitator_chance": normalize_values(law_heavy, 0.5),
    },
    "00_petty_bourgeoisie.txt": {
        "female_commander_chance": normalize_values(law_heavy, 0.3),
        "female_politician_chance": normalize_values(law_heavy, 0.4),
        "female_agitator_chance": normalize_values(law_heavy, 0.5),
    },
    "00_rural_folk.txt": {
        "female_commander_chance": normalize_values(law_heavy, 0.3),
        "female_politician_chance": normalize_values(law_heavy, 0.4),
        "female_agitator_chance": normalize_values(law_heavy, 0.5),
    },
    "00_trade_unions.txt": {
        "female_commander_chance": normalize_values(tech_heavy, 0.4),
        "female_politician_chance": normalize_values(tech_heavy, 0.5),
        "female_agitator_chance": normalize_values(tech_heavy, 0.5),
    },
}

# print(json.dumps(modifications, indent=4))

# Call the function
modify_interest_group_files(input_directory, output_directory, modifications)
