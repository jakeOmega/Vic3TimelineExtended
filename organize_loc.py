import os
import re

from path_constants import mod_path


def find_technology_keys(project_directory):
    """Finds technology keys by parsing technology definition files."""
    tech_keys = set()
    tech_path = os.path.join(project_directory, "common", "technology", "technologies")
    if not os.path.isdir(tech_path):
        return tech_keys
    for root, _, files in os.walk(tech_path):
        for file in files:
            if file.endswith(".txt"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    for line in f:
                        match = re.match(r"^\s*([\w\._-]+)\s*=\s*{", line)
                        if match:
                            key = match.group(1)
                            tech_keys.add(key)
                            tech_keys.add(f"{key}_desc")
    return tech_keys


def find_notification_keys(project_directory):
    """Finds implicit notification keys from message definitions."""
    notification_keys = set()
    messages_path = os.path.join(project_directory, "common", "messages")
    if not os.path.isdir(messages_path):
        return notification_keys
    for root, _, files in os.walk(messages_path):
        for file in files:
            if file.endswith(".txt"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    for line in f:
                        match = re.match(r"^\s*([\w\._]+)\s*=\s*{", line)
                        if match:
                            base_key = match.group(1)
                            notification_keys.add(f"notification_{base_key}_name")
                            notification_keys.add(f"notification_{base_key}_desc")
                            notification_keys.add(f"notification_{base_key}_tooltip")
    return notification_keys


def find_game_rule_keys(project_directory):
    """Finds implicit setting and rule keys from game rule definitions."""
    game_rule_keys = set()
    rules_path = os.path.join(project_directory, "common", "game_rules")
    if not os.path.isdir(rules_path):
        return game_rule_keys
    for file in os.listdir(rules_path):
        if file.endswith(".txt"):
            with open(os.path.join(rules_path, file), "r", encoding="utf-8") as f:
                content = f.read()
                # Find top-level rules (e.g., custom_religions_allowed_rule)
                top_level_matches = re.findall(
                    r"^([\w_]+)\s*=\s*{", content, re.MULTILINE
                )
                for base_key in top_level_matches:
                    game_rule_keys.add(f"rule_{base_key}")  # NEW: Handles rule_... keys
                # Find nested settings (e.g., custom_religions_allowed)
                nested_matches = re.findall(
                    r"^\s+([\w_]+)\s*=\s*{", content, re.MULTILINE
                )
                for base_key in nested_matches:
                    game_rule_keys.add(f"setting_{base_key}")
                    game_rule_keys.add(f"setting_{base_key}_desc")
    return game_rule_keys


def find_company_keys(project_directory):
    """Finds implicit company keys for dynamic naming."""
    company_keys = set()
    company_path = os.path.join(project_directory, "common", "company_types")
    if not os.path.isdir(company_path):
        return company_keys
    for file in os.listdir(company_path):
        if file.endswith(".txt"):
            with open(os.path.join(company_path, file), "r", encoding="utf-8") as f:
                content = f.read()
                blocks = re.findall(r"(\w+)\s*=\s*{(.*?)}", content, re.DOTALL)
                for block_name, block_content in blocks:
                    company_keys.add(block_name)
                    company_keys.add(f"{block_name}_desc")
                    if "uses_dynamic_naming = yes" in block_content:
                        company_keys.add(f"{block_name}_dynamic_name_tag_singular")
                        company_keys.add(f"{block_name}_dynamic_name_tag_plural")
    return company_keys


def find_law_keys(project_directory):
    """Finds implicit law keys for effects tooltips."""
    law_keys = set()
    laws_path = os.path.join(project_directory, "common", "laws")
    if not os.path.isdir(laws_path):
        return law_keys
    for file in os.listdir(laws_path):
        if file.endswith(".txt"):
            with open(os.path.join(laws_path, file), "r", encoding="utf-8") as f:
                matches = re.findall(r"^\s*([\w\._-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    law_keys.add(base_key)
                    law_keys.add(f"{base_key}_desc")
                    law_keys.add(f"EFFECTS_ON_ACCEPTANCE_{base_key}")
    return law_keys


def find_diplo_action_keys(project_directory):
    """Finds implicit key suites for diplomatic actions."""
    diplo_keys = set()
    diplo_path = os.path.join(project_directory, "common", "diplomatic_actions")
    if not os.path.isdir(diplo_path):
        return diplo_keys
    suffixes = [
        "",
        "_desc",
        "_action_name",
        "_action_propose_name",
        "_action_notification_name",
        "_action_notification_desc",
        "_action_break_name",
        "_action_notification_break_name",
        "_action_notification_break_desc",
        "_proposal_accepted_name",
        "_proposal_accepted_desc",
        "_proposal_declined_name",
        "_proposal_declined_desc",
        "_proposal_notification_name",
        "_proposal_notification_desc",
        "_proposal_notification_effects_desc",
        "_pact_desc",
    ]
    for file in os.listdir(diplo_path):
        if file.endswith(".txt"):
            with open(os.path.join(diplo_path, file), "r", encoding="utf-8") as f:
                matches = re.findall(r"^\s*([\w\._-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    for suffix in suffixes:
                        diplo_keys.add(f"{base_key}{suffix}")
    return diplo_keys


# --- NEW: Function to parse political movement files ---
def find_political_movement_keys(project_directory):
    """Finds implicit keys for political movements."""
    movement_keys = set()
    movements_path = os.path.join(project_directory, "common", "political_movements")
    if not os.path.isdir(movements_path):
        return movement_keys
    for file in os.listdir(movements_path):
        if file.endswith(".txt"):
            with open(os.path.join(movements_path, file), "r", encoding="utf-8") as f:
                matches = re.findall(r"^\s*([\w\._-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    movement_keys.add(base_key)
                    movement_keys.add(f"{base_key}_name")
    return movement_keys


# --- NEW: Function to parse journal entry files ---
def find_journal_entry_keys(project_directory):
    """Finds implicit keys for journal entries."""
    je_keys = set()
    je_path = os.path.join(project_directory, "common", "journal_entries")
    if not os.path.isdir(je_path):
        return je_keys
    for file in os.listdir(je_path):
        if file.endswith(".txt"):
            with open(os.path.join(je_path, file), "r", encoding="utf-8") as f:
                matches = re.findall(r"^\s*([\w\._-]+)\s*=\s*{", f.read(), re.MULTILINE)
                for base_key in matches:
                    je_keys.add(base_key)
                    je_keys.add(f"{base_key}_reason")
                    je_keys.add(f"{base_key}_goal")
    return je_keys


def categorize_key(key, technology_keys):
    """Assigns a category to a localization key."""
    if key in technology_keys:
        return "TECHNOLOGIES"
    if key.startswith("setting_") or key.startswith("rule_"):
        return "GAME_RULES"
    if key.startswith("EFFECTS_ON_ACCEPTANCE_"):
        return "LAWS"
    if key.startswith("movement_"):
        return "POLITICAL_MOVEMENTS"
    if key.startswith(("pm_", "pmg_")):
        return "PRODUCTION_METHODS"
    if key.startswith("combat_unit_"):
        return "COMBAT_UNITS"
    if key.startswith("mobilization_option_"):
        return "MOBILIZATION_OPTIONS"
    if key.startswith("building_"):
        return "BUILDINGS"
    if key.startswith(("law_", "lawgroup_")):
        return "LAWS"
    if key.startswith("institution_"):
        return "INSTITUTIONS"
    if key.endswith(("_add", "_mult", "_add_desc", "_mult_desc")):
        return "MODIFIERS"
    if key.startswith(("goods_", "popneed_")):
        return "GOODS_AND_NEEDS"
    if key.startswith("company_"):
        return "COMPANIES"
    if key.startswith("ideology_"):
        return "IDEOLOGIES"
    if key.startswith("decree_"):
        return "DECREES"
    if key.startswith("je_"):
        return "JOURNAL_ENTRIES"
    if key.startswith("notification_"):
        return "NOTIFICATIONS"
    if "event" in key:
        return "EVENTS"
    if any(s in key for s in ["diplo", "pact", "_subject_", "_proposal_"]):
        return "DIPLOMACY"
    if key.startswith(("power_bloc_", "principle_group_")):
        return "POWER_BLOCS"
    if any(s in key for s in ["religion", "SELECT_IDEOLOGY", "SELECT_TRAIT"]):
        return "RELIGION"
    if "_desc" in key or (re.match(r"^[a-zA-Z_]+$", key) and len(key.split("_")) < 4):
        return "CONCEPTS"
    return "MISCELLANEOUS"


def find_used_keys_explicitly(directory):
    """Recursively finds all keys explicitly written in files."""
    used_keys = set()
    for root, _, files in os.walk(directory):
        if "localization" in root:
            continue
        for file in files:
            if file.endswith((".txt", ".yml", ".gui")):
                try:
                    with open(
                        os.path.join(root, file), "r", encoding="utf-8", errors="ignore"
                    ) as f:
                        content = f.read()
                        found_keys = re.findall(r"[\w\._-]+", content)
                        used_keys.update(found_keys)
                except Exception:
                    continue
    return used_keys


def organize_loc_file(input_file_path, project_directory, output_file_path):
    """Reads, categorizes, and writes an organized localization file."""
    with open(input_file_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    loc_data = {}
    for line in lines[1:]:
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        loc_data[key.strip()] = value.strip()

    all_keys = set(loc_data.keys())

    # --- Comprehensive Key Detection ---
    used_keys = find_used_keys_explicitly(project_directory)

    parser_functions = [
        find_technology_keys,
        find_notification_keys,
        find_game_rule_keys,
        find_company_keys,
        find_law_keys,
        find_diplo_action_keys,
        find_political_movement_keys,
        find_journal_entry_keys,
    ]
    for func in parser_functions:
        used_keys.update(func(project_directory))

    technology_keys = find_technology_keys(project_directory)

    for key in list(used_keys):
        desc_key = f"{key}_desc"
        if desc_key in all_keys:
            used_keys.add(desc_key)

    while True:
        newly_found_keys = set()
        # Check the values of currently used keys for other keys
        for key in used_keys:
            if key in loc_data:
                # Find potential keys inside the value string
                found_in_value = re.findall(
                    r"[\$@!](\w+)[\$@!#|]", loc_data[key]
                )  # More precise regex for variables
                found_in_value.extend(
                    re.findall(r"\[\w+\.Get(Named)?(\w+)", loc_data[key])
                )  # For script values
                for found_key in found_in_value:
                    if found_key in all_keys and found_key not in used_keys:
                        newly_found_keys.add(found_key)
                        desc_key = f"{key}_desc"
                        if desc_key in all_keys:
                            newly_found_keys.add(desc_key)

        if not newly_found_keys:
            break  # Exit loop if no new keys were found in this pass
        used_keys.update(newly_found_keys)

    for key in all_keys:
        if (
            re.match(r"^STANDARD_OF_LIVING_LEVEL_\d+$", key)
            or re.match(r"^STANDARD_OF_LIVING_LEVEL_ONLY_ICON_\d+$", key)
            or re.match(r"^STANDARD_OF_LIVING_NO_ICON_LEVEL_\d+$", key)
        ):
            used_keys.add(key)

    unused_keys = all_keys - used_keys

    # --- Categorization & Writing ---
    categorized_data = {}
    for key, value in loc_data.items():
        category = (
            "UNUSED" if key in unused_keys else categorize_key(key, technology_keys)
        )
        if category not in categorized_data:
            categorized_data[category] = {}
        categorized_data[category][key] = value

    with open(output_file_path, "w", encoding="utf-8-sig") as f:
        f.write("l_english:\n")
        sorted_categories = sorted(
            [cat for cat in categorized_data.keys() if cat != "UNUSED"]
        )

        for category in sorted_categories:
            f.write(f"\n#\n# {category}\n#\n")
            for key in sorted(categorized_data[category].keys()):
                f.write(f" {key}:{loc_data[key]}\n")  # UPDATED: Removed space

        if "UNUSED" in categorized_data and categorized_data["UNUSED"]:
            f.write("\n#\n# UNUSED\n#\n")
            for key in sorted(categorized_data["UNUSED"].keys()):
                f.write(f" {key}:{loc_data[key]}\n")  # UPDATED: Removed space


def main():
    input_file = os.path.join(
        mod_path, "localization", "english", "aaaaa_extra_l_english.yml"
    )
    output_file = os.path.join(
        mod_path, "localization", "english", "aaaaa_extra_l_english.yml"
    )

    organize_loc_file(input_file, mod_path, output_file)


if __name__ == "__main__":
    main()
