# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 23:22:15 2023

@author: jakef
"""

import re
from os import walk


def ministry_constructor(ministry_name, attitude):
    if attitude == "+":
        return [
            ("law_no_" + ministry_name, "neutral"),
            ("law_" + ministry_name, "approve"),
        ]
    elif attitude == "-":
        return [
            ("law_no_" + ministry_name, "approve"),
            ("law_" + ministry_name, "neutral"),
        ]
    elif attitude == "++":
        return [
            ("law_no_" + ministry_name, "disapprove"),
            ("law_" + ministry_name, "strongly_approve"),
        ]
    elif attitude == "--":
        return [
            ("law_no_" + ministry_name, "approve"),
            ("law_" + ministry_name, "strongly_disapprove"),
        ]
    else:
        raise ValueError


def parse_file(file_path):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    entries = {}
    stack = []
    key = None
    value = ""

    for line in content.split("\n"):
        if line.strip() == "":
            continue
        if (
            "{" in line and "}" in line
        ):  # Handle the case where the opening and closing braces are on the same line
            value += line + "\n"
        elif "{" in line:
            if key is None:
                key = line.split("=", 1)[0].strip()
                value = "{\n"
            else:
                value += line + "\n"
            stack.append("{")
        elif "}" in line:
            stack.pop()
            value += line + "\n"
        else:
            value += line + "\n"

        if key is not None and len(stack) == 0:
            entries[key] = value
            key = None
            value = ""

    return entries


def modify_entries(entries, modifications):
    for key, sub_entries in modifications.items():
        if key in entries:
            for sub_key, lines in sub_entries.items():
                if sub_key + " = {" in entries[key]:
                    # Modify existing lines within the sub-entry or add new lines
                    for line in lines:
                        line_key, line_value = line
                        line_pattern = f"\t\t{line_key} = .*"
                        new_line = f"\t\t{line_key} = {line_value}"
                        if re.search(line_pattern, entries[key]):
                            entries[key] = re.sub(line_pattern, new_line, entries[key])
                        else:
                            entries[key] = entries[key].replace(
                                f"{sub_key} = {{", f"{sub_key} = {{\n{new_line}", 1
                            )
                else:
                    # Add a new sub-entry before the first line that starts with "lawgroup_"
                    new_value = "\n".join(
                        [f"\t\t{line[0]} = {line[1]}" for line in lines]
                    )
                    new_sub_entry = f"\t{sub_key} = {{\n{new_value}\n\t}}"
                    pattern = re.compile(r"(\n\tlawgroup_)", re.DOTALL)
                    entries[key] = pattern.sub(
                        "\n" + new_sub_entry + r"\1", entries[key], 1
                    )
    return {key: value for key, value in entries.items() if key in modifications}


def update_law_reqs(entries):
    for key, entry in entries.items():
        entry = entry.replace(
            "has_law = law_type:law_womens_suffrage",
            "OR = {has_law = law_type:law_womens_suffrage has_law = law_type:law_protected_class}",
        )
        entries[key] = entry
    return entries


def write_to_file(file_path, entries):
    with open(file_path, "w", encoding="utf-8-sig") as f:
        for key, value in entries.items():
            f.write(f"{key} = {value}\n")


entries = {}
filenames = next(
    walk(r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\ideologies"),
    (None, None, []),
)[2]
for file in filenames:
    print("Parsing: ", file)
    new_entries = parse_file(
        r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\ideologies\\" + file
    )
    print("Found ", len(new_entries.keys()), " new entries")
    entries.update(new_entries)

anti_privacy_entry = [
    ("law_minimal_privacy_protection", "neutral"),
    ("law_moderate_data_privacy", "disapprove"),
    ("law_strong_privacy_rights", "strongly_disapprove"),
    ("law_intrusive_surveillance", "strongly_approve"),
]
pro_privacy_entry = [
    ("law_minimal_privacy_protection", "neutral"),
    ("law_moderate_data_privacy", "approve"),
    ("law_strong_privacy_rights", "strongly_approve"),
    ("law_intrusive_surveillance", "strongly_disapprove"),
]
trad_privacy_entry = [
    ("law_minimal_privacy_protection", "neutral"),
    ("law_moderate_data_privacy", "disapprove"),
    ("law_strong_privacy_rights", "strongly_disapprove"),
    ("law_intrusive_surveillance", "disapprove"),
]
reform_privacy_entry = [
    ("law_minimal_privacy_protection", "neutral"),
    ("law_moderate_data_privacy", "approve"),
    ("law_strong_privacy_rights", "neutral"),
    ("law_intrusive_surveillance", "disapprove"),
]
extremist_privacy_entry = [
    ("law_minimal_privacy_protection", "strongly_disapprove"),
    ("law_moderate_data_privacy", "strongly_disapprove"),
    ("law_strong_privacy_rights", "strongly_disapprove"),
    ("law_intrusive_surveillance", "strongly_approve"),
]
pro_ai_governance = [
    ("law_unrestricted_ai_development", "neutral"),
    ("law_moderate_ai_governance", "approve"),
    ("law_strict_ai_ethics_and_control", "strongly_approve"),
]
anti_ai_governance = [
    ("law_unrestricted_ai_development", "neutral"),
    ("law_moderate_ai_governance", "disapprove"),
    ("law_strict_ai_ethics_and_control", "strongly_disapprove"),
]
moderate_ai_governance = [
    ("law_unrestricted_ai_development", "neutral"),
    ("law_moderate_ai_governance", "approve"),
    ("law_strict_ai_ethics_and_control", "neutral"),
]
light_ai_governance = [
    ("law_unrestricted_ai_development", "neutral"),
    ("law_moderate_ai_governance", "neutral"),
    ("law_strict_ai_ethics_and_control", "disapprove"),
]
punitive_drug_laws = [
    ("law_no_drug_regulation", "strongly_disapprove"),
    ("law_liquor_prohibition", "neutral"),
    ("law_lax_drug_policy", "disapprove"),
    ("law_punitive_drug_policy", "strongly_approve"),
    ("law_harm_reduction_policy", "neutral"),
    ("law_drug_legalization_and_regulation", "disapprove"),
]
trad_punitive_drug_laws = [
    ("law_no_drug_regulation", "disapprove"),
    ("law_punitive_drug_policy", "neutral"),
    ("law_liquor_prohibition", "neutral"),
    ("law_lax_drug_policy", "disapprove"),
    ("law_harm_reduction_policy", "strongly_disapprove"),
    ("law_drug_legalization_and_regulation", "strongly_disapprove"),
]
liberal_drug_laws = [
    ("law_no_drug_regulation", "neutral"),
    ("law_punitive_drug_policy", "disapprove"),
    ("law_liquor_prohibition", "disapprove"),
    ("law_lax_drug_policy", "strongly_approve"),
    ("law_harm_reduction_policy", "approve"),
    ("law_drug_legalization_and_regulation", "strongly_approve"),
]
moderate_drug_laws = [
    ("law_no_drug_regulation", "disapprove"),
    ("law_punitive_drug_policy", "neutral"),
    ("law_liquor_prohibition", "disapprove"),
    ("law_lax_drug_policy", "approve"),
    ("law_harm_reduction_policy", "strongly_approve"),
    ("law_drug_legalization_and_regulation", "approve"),
]
religious_drug_laws = [
    ("law_no_drug_regulation", "disapprove"),
    ("law_punitive_drug_policy", "approve"),
    ("law_liquor_prohibition", "strongly_approve"),
    ("law_lax_drug_policy", "neutral"),
    ("law_harm_reduction_policy", "strongly_disapprove"),
    ("law_drug_legalization_and_regulation", "strongly_disapprove"),
]
anti_augmentation = [
    ("law_no_augmentation", "neutral"),
    ("law_unrestricted_augmentation", "strongly_disapprove"),
    ("law_human_purity", "strongly_approve"),
    ("law_medical_augmentation_only", "neutral"),
    ("law_regulated_augmentation_market", "disapprove"),
    ("law_mandatory_augmentation", "strongly_disapprove"),
]
highly_regulated_augmentation = [
    ("law_no_augmentation", "neutral"),
    ("law_unrestricted_augmentation", "strongly_disapprove"),
    ("law_human_purity", "neutral"),
    ("law_medical_augmentation_only", "approve"),
    ("law_regulated_augmentation_market", "strongly_approve"),
    ("law_mandatory_augmentation", "disapprove"),
]
lightly_regulated_augmentation = [
    ("law_no_augmentation", "neutral"),
    ("law_unrestricted_augmentation", "approve"),
    ("law_human_purity", "disapprove"),
    ("law_medical_augmentation_only", "approve"),
    ("law_regulated_augmentation_market", "strongly_approve"),
    ("law_mandatory_augmentation", "disapprove"),
]
unregulated_augmentation = [
    ("law_no_augmentation", "neutral"),
    ("law_unrestricted_augmentation", "strongly_approve"),
    ("law_human_purity", "strongly_disapprove"),
    ("law_medical_augmentation_only", "disapprove"),
    ("law_regulated_augmentation_market", "neutral"),
    ("law_mandatory_augmentation", "disapprove"),
]
medical_augmentation = [
    ("law_no_augmentation", "neutral"),
    ("law_unrestricted_augmentation", "disapprove"),
    ("law_human_purity", "disapprove"),
    ("law_medical_augmentation_only", "strongly_approve"),
    ("law_regulated_augmentation_market", "approve"),
    ("law_mandatory_augmentation", "strongly_disapprove"),
]
militarist_augmentation = [
    ("law_no_augmentation", "neutral"),
    ("law_unrestricted_augmentation", "neutral"),
    ("law_human_purity", "strongly_disapprove"),
    ("law_medical_augmentation_only", "disapprove"),
    ("law_regulated_augmentation_market", "neutral"),
    ("law_mandatory_augmentation", "strongly_approve"),
]
populist_augmentation = [
    ("law_no_augmentation", "neutral"),
    ("law_unrestricted_augmentation", "disapprove"),
    ("law_human_purity", "strongly_approve"),
    ("law_medical_augmentation_only", "strongly_approve"),
    ("law_regulated_augmentation_market", "approve"),
    ("law_mandatory_augmentation", "strongly_disapprove"),
]
extremist_augmentation = [
    ("law_no_augmentation", "neutral"),
    ("law_unrestricted_augmentation", "strongly_disapprove"),
    ("law_human_purity", "strongly_approve"),
    ("law_medical_augmentation_only", "strongly_disapprove"),
    ("law_regulated_augmentation_market", "strongly_disapprove"),
    ("law_mandatory_augmentation", "strongly_approve"),
]
strict_ip_laws = [
    ("law_no_ip_protection", "disapprove"),
    ("law_creative_commons", "neutral"),
    ("law_traditional_ip_protection", "approve"),
    ("law_strict_ip_protection", "strongly_approve"),
    ("law_open_source_innovation", "disapprove"),
]
moderate_ip_laws = [
    ("law_no_ip_protection", "disapprove"),
    ("law_creative_commons", "neutral"),
    ("law_traditional_ip_protection", "strongly_approve"),
    ("law_strict_ip_protection", "approve"),
    ("law_open_source_innovation", "neutral"),
]
loose_ip_laws = [
    ("law_no_ip_protection", "neutral"),
    ("law_creative_commons", "strongly_approve"),
    ("law_traditional_ip_protection", "disapprove"),
    ("law_strict_ip_protection", "disapprove"),
    ("law_open_source_innovation", "approve"),
]
communal_ip_laws = [
    ("law_no_ip_protection", "approve"),
    ("law_creative_commons", "neutral"),
    ("law_traditional_ip_protection", "disapprove"),
    ("law_strict_ip_protection", "disapprove"),
    ("law_open_source_innovation", "strongly_approve"),
]
lgbtq_hate = [
    ("law_active_persecution", "strongly_approve"),
    ("law_legal_limbo", "approve"),
    ("law_basic_protections", "neutral"),
    ("law_comprehensive_rights", "disapprove"),
    ("law_full_equality_and_protection", "strongly_disapprove"),
]
lgbtq_dislike = [
    ("law_active_persecution", "approve"),
    ("law_legal_limbo", "neutral"),
    ("law_basic_protections", "disapprove"),
    ("law_comprehensive_rights", "disapprove"),
    ("law_full_equality_and_protection", "strongly_disapprove"),
]
lgbtq_indifference = [
    ("law_active_persecution", "disapprove"),
    ("law_legal_limbo", "approve"),
    ("law_basic_protections", "neutral"),
    ("law_comprehensive_rights", "disapprove"),
    ("law_full_equality_and_protection", "strongly_disapprove"),
]
lgbtq_like = [
    ("law_active_persecution", "disapprove"),
    ("law_legal_limbo", "neutral"),
    ("law_basic_protections", "approve"),
    ("law_comprehensive_rights", "strongly_approve"),
    ("law_full_equality_and_protection", "approve"),
]
lgbtq_love = [
    ("law_active_persecution", "strongly_disapprove"),
    ("law_legal_limbo", "disapprove"),
    ("law_basic_protections", "neutral"),
    ("law_comprehensive_rights", "approve"),
    ("law_full_equality_and_protection", "strongly_approve"),
]


modifications = {
    "ideology_paternalistic": {
        "lawgroup_privacy_rights": anti_privacy_entry,
        "lawgroup_artificial_intelligence_governance": pro_ai_governance,
        "lawgroup_drug_laws": punitive_drug_laws,
        "lawgroup_human_augmentation": highly_regulated_augmentation,
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "++"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "++"
        ),
    },
    "ideology_particularist": {
        "lawgroup_privacy_rights": pro_privacy_entry,
        "lawgroup_national_bank": ministry_constructor("national_bank", "--"),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "--"
        ),
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "++"
        ),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "--"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
    },
    "ideology_patriotic": {
        "lawgroup_privacy_rights": anti_privacy_entry,
        "lawgroup_drug_laws": punitive_drug_laws,
        "lawgroup_ministry_of_foreign_affairs": ministry_constructor(
            "ministry_of_foreign_affairs", "+"
        ),
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "++"),
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "++"
        ),
        "lawgroup_ministry_of_culture": ministry_constructor(
            "ministry_of_culture", "+"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "--"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "--"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "+"
        ),
    },
    "ideology_liberal": {
        "lawgroup_privacy_rights": pro_privacy_entry,
        "lawgroup_drug_laws": moderate_drug_laws,
        "lawgroup_human_augmentation": lightly_regulated_augmentation,
        "lawgroup_LGBTQ_rights": lgbtq_like,
        "lawgroup_rights_of_women": [("law_protected_class", "disapprove")],
        "lawgroup_ministry_of_foreign_affairs": ministry_constructor(
            "ministry_of_foreign_affairs", "+"
        ),
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "-"
        ),
        "lawgroup_ministry_of_culture": ministry_constructor(
            "ministry_of_culture", "+"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "+"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "-"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "--"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
    },
    "ideology_liberal_modern": {
        "lawgroup_privacy_rights": pro_privacy_entry,
        "lawgroup_drug_laws": moderate_drug_laws,
        "lawgroup_human_augmentation": lightly_regulated_augmentation,
        "lawgroup_LGBTQ_rights": lgbtq_like,
        "lawgroup_rights_of_women": [("law_protected_class", "disapprove")],
        "lawgroup_ministry_of_foreign_affairs": ministry_constructor(
            "ministry_of_foreign_affairs", "+"
        ),
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "-"
        ),
        "lawgroup_ministry_of_culture": ministry_constructor(
            "ministry_of_culture", "+"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "+"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "-"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "--"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "+"
        ),
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "+"
        ),
    },
    "ideology_market_liberal": {
        "lawgroup_privacy_rights": reform_privacy_entry,
        "lawgroup_artificial_intelligence_governance": anti_ai_governance,
        "lawgroup_drug_laws": moderate_drug_laws,
        "lawgroup_human_augmentation": lightly_regulated_augmentation,
        "lawgroup_intellectual_property": moderate_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_indifference,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "-"
        ),
        "lawgroup_national_bank": ministry_constructor("national_bank", "+"),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "-"
        ),
        "lawgroup_colonization": [("law_neocolonialism", "approve")],
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "-"
        ),
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "-"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "-"
        ),
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "--"
        ),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "-"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "-"
        ),
    },
    "ideology_traditionalist": {
        "lawgroup_privacy_rights": trad_privacy_entry,
        "lawgroup_drug_laws": trad_punitive_drug_laws,
        "lawgroup_human_augmentation": anti_augmentation,
        "lawgroup_intellectual_property": moderate_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_dislike,
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_disapprove")],
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "-"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "+"
        ),
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "+"
        ),
    },
    "ideology_reformer": {
        "lawgroup_privacy_rights": reform_privacy_entry,
        "lawgroup_artificial_intelligence_governance": moderate_ai_governance,
        "lawgroup_drug_laws": moderate_drug_laws,
        "lawgroup_human_augmentation": medical_augmentation,
        "lawgroup_intellectual_property": moderate_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_like,
        "lawgroup_rights_of_women": [("law_protected_class", "disapprove")],
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "+"
        ),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "+"
        ),
    },
    "ideology_populist": {
        "lawgroup_privacy_rights": reform_privacy_entry,
        "lawgroup_artificial_intelligence_governance": pro_ai_governance,
        "lawgroup_human_augmentation": populist_augmentation,
        "lawgroup_national_bank": ministry_constructor("national_bank", "-"),
        "lawgroup_ministry_of_culture": ministry_constructor(
            "ministry_of_culture", "+"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor("ministry_of_labor", "+"),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "+"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
    },
    "ideology_radical": {
        "lawgroup_privacy_rights": pro_privacy_entry,
        "lawgroup_drug_laws": liberal_drug_laws,
        "lawgroup_intellectual_property": loose_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "-"
        ),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "+"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "+"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "--"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "--"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
    },
    "ideology_social_democrat": {
        "lawgroup_privacy_rights": reform_privacy_entry,
        "lawgroup_drug_laws": moderate_drug_laws,
        "lawgroup_human_augmentation": medical_augmentation,
        "lawgroup_intellectual_property": loose_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_like,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "-"
        ),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "+"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "+"
        ),
        "lawgroup_welfare": [
            ("law_no_social_security", "strongly_disapprove"),
            ("law_poor_laws", "disapprove"),
            ("law_wage_subsidies", "neutral"),
            ("law_old_age_pension", "approve"),
            ("law_universal_basic_income", "approve"),
            ("law_post-scarcity", "strongly_approve"),
        ],
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "++"
        ),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "+"
        ),
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "+"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "--"
        ),
    },
    "ideology_vanguardist": {
        "lawgroup_privacy_rights": extremist_privacy_entry,
        "lawgroup_intellectual_property": communal_ip_laws,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "+"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "+"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "++"
        ),
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "-"
        ),
    },
    "ideology_fascist": {
        "lawgroup_privacy_rights": extremist_privacy_entry,
        "lawgroup_drug_laws": trad_punitive_drug_laws,
        "lawgroup_human_augmentation": extremist_augmentation,
        "lawgroup_LGBTQ_rights": lgbtq_hate,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "++"
        ),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "-"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "--"
        ),
        "lawgroup_slavery": [
            ("law_slavery_banned", "disapprove"),
            ("law_debt_slavery", "neutral"),
            ("law_slave_trade", "strongly_approve"),
            ("law_legacy_slavery", "approve"),
        ],
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "++"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "++"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "++"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
    },
    "ideology_anarchist": {
        "lawgroup_privacy_rights": pro_privacy_entry,
        "lawgroup_artificial_intelligence_governance": light_ai_governance,
        "lawgroup_drug_laws": liberal_drug_laws,
        "lawgroup_human_augmentation": unregulated_augmentation,
        "lawgroup_intellectual_property": communal_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "--"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "--"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "-"
        ),
    },
    "ideology_laissez_faire": {
        "lawgroup_artificial_intelligence_governance": anti_ai_governance,
        "lawgroup_ministry_of_commerce": ministry_constructor(
            "ministry_of_commerce", "++"
        ),
        "lawgroup_national_bank": ministry_constructor("national_bank", "+"),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "--"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor("ministry_of_labor", "-"),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "-"
        ),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "-"
        ),
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "--"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
    },
    "ideology_moralist": {
        "lawgroup_artificial_intelligence_governance": pro_ai_governance,
        "lawgroup_drug_laws": religious_drug_laws,
        "lawgroup_human_augmentation": anti_augmentation,
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "-"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "-"
        ),
    },
    "ideology_egalitarian": {
        "lawgroup_drug_laws": liberal_drug_laws,
        "lawgroup_LGBTQ_rights": lgbtq_indifference,
        "lawgroup_rights_of_women": [("law_protected_class", "neutral")],
        "lawgroup_colonization": [
            ("law_neocolonialism", "neutral"),
            ("law_no_colonial_affairs", "neutral"),
            ("law_frontier_colonization", "neutral"),
            ("law_colonial_resettlement", "disapprove"),
            ("law_colonial_exploitation", "strongly_disapprove"),
        ],
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "++"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
    },
    "ideology_egalitarian_modern": {
        "lawgroup_drug_laws": liberal_drug_laws,
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_rights_of_women": [("law_protected_class", "approve")],
        "lawgroup_colonization": [
            ("law_neocolonialism", "neutral"),
            ("law_no_colonial_affairs", "neutral"),
            ("law_frontier_colonization", "neutral"),
            ("law_colonial_resettlement", "disapprove"),
            ("law_colonial_exploitation", "strongly_disapprove"),
        ],
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "++"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
    },
    "ideology_meritocratic": {
        "lawgroup_human_augmentation": unregulated_augmentation,
        "lawgroup_intellectual_property": strict_ip_laws,
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "+"),
        "lawgroup_ministry_of_commerce": ministry_constructor(
            "ministry_of_commerce", "+"
        ),
        "lawgroup_national_bank": ministry_constructor("national_bank", "+"),
        "lawgroup_ministry_of_labor": ministry_constructor("ministry_of_labor", "-"),
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "-"
        ),
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "-"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "+"
        ),
    },
    "ideology_jingoist": {
        "lawgroup_human_augmentation": militarist_augmentation,
        "lawgroup_ministry_of_foreign_affairs": ministry_constructor(
            "ministry_of_foreign_affairs", "+"
        ),
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "++"),
        "lawgroup_colonization": [("law_neocolonialism", "neutral")],
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
    },
    "ideology_jingoist_leader": {
        "lawgroup_human_augmentation": militarist_augmentation,
        "lawgroup_ministry_of_foreign_affairs": ministry_constructor(
            "ministry_of_foreign_affairs", "++"
        ),
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "++"),
        "lawgroup_colonization": [("law_neocolonialism", "neutral")],
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
    },
    "ideology_individualist": {
        "lawgroup_human_augmentation": unregulated_augmentation,
        "lawgroup_welfare": [
            ("law_no_social_security", "neutral"),
            ("law_poor_laws", "approve"),
            ("law_wage_subsidies", "disapprove"),
            ("law_old_age_pension", "strongly_disapprove"),
            ("law_universal_basic_income", "strongly_disapprove"),
            ("law_post-scarcity", "disapprove"),
        ],
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "-"
        ),
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "--"
        ),
    },
    "ideology_proletarian": {
        "lawgroup_intellectual_property": communal_ip_laws,
        "lawgroup_national_bank": ministry_constructor("national_bank", "-"),
        "lawgroup_ministry_of_labor": ministry_constructor("ministry_of_labor", "++"),
        "lawgroup_welfare": [
            ("law_no_social_security", "strongly_disapprove"),
            ("law_poor_laws", "strongly_disapprove"),
            ("law_wage_subsidies", "disapprove"),
            ("law_old_age_pension", "neutral"),
            ("law_universal_basic_income", "approve"),
            ("law_post-scarcity", "strongly_approve"),
        ],
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "++"
        ),
    },
    "ideology_communist": {
        "lawgroup_intellectual_property": communal_ip_laws,
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor("ministry_of_labor", "++"),
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "-"
        ),
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "+"
        ),
    },
    "ideology_pacifist": {
        "lawgroup_colonization": [("law_neocolonialism", "disapprove")],
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "--"),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "++"
        ),
    },
    "ideology_plutocratic": {
        "lawgroup_intellectual_property": strict_ip_laws,
        "lawgroup_ministry_of_culture": ministry_constructor(
            "ministry_of_culture", "-"
        ),
        "lawgroup_colonization": [("law_neocolonialism", "strongly_approve")],
    },
    "ideology_patriarchal": {
        "lawgroup_LGBTQ_rights": lgbtq_dislike,
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_disapprove")],
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "+"
        ),
    },
    "ideology_patriarchal_suffrage": {
        "lawgroup_rights_of_women": [("law_protected_class", "disapprove")],
        "lawgroup_LGBTQ_rights": lgbtq_dislike,
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "+"
        ),
    },
    "ideology_feminist": {
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_rights_of_women": [
            ("law_womens_suffrage", "approve"),
            ("law_protected_class", "strongly_approve"),
        ],
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
    },
    "ideology_feminist_ig": {
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_rights_of_women": [
            ("law_women_own_property", "disapprove"),
            ("law_women_in_the_workplace", "neutral"),
            ("law_womens_suffrage", "approve"),
            ("law_protected_class", "strongly_approve"),
        ],
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
    },
    "ideology_humanitarian": {
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_approve")],
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "++"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "+"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "+"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "--"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
    },
    "ideology_humanitarian_royalist": {
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_approve")],
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "++"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "+"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "+"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "-"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "-"
        ),
    },
    "ideology_reactionary": {
        "lawgroup_LGBTQ_rights": lgbtq_hate,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "++"
        ),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "-"
        ),
        "lawgroup_ministry_of_culture": ministry_constructor(
            "ministry_of_culture", "+"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor("ministry_of_labor", "-"),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "--"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "++"
        ),
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "+"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
    },
    "ideology_theocrat": {
        "lawgroup_LGBTQ_rights": lgbtq_hate,
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "++"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
    },
    "ideology_republican": {},
    "ideology_republican_paternalistic": {},
    "ideology_socialist": {},
    "ideology_scholar_paternalistic": {},
    "ideology_junker_paternalistic": {},
    "ideology_papal_paternalistic": {},
    "ideology_confucian": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
    },
    "ideology_bakufu": {},
    "ideology_shinto_moralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
    },
    "ideology_caudillismo": {},
    "ideology_buddhist_moralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
    },
    "ideology_hindu_moralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
    },
    "ideology_sikh_moralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
    },
    "ideology_heavenly_kingdom_theocratic": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
    },
    "ideology_orleanist": {},
    "ideology_legitimist": {},
    "ideology_bonapartist": {},
    "ideology_atheist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "-"
        ),
    },
    "ideology_republican_leader": {},
    "ideology_royalist": {},
    "ideology_jacksonian_democrat": {},
    "ideology_positivist": {},
    "ideology_russian_patriarch": {
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_disapprove")],
    },
    "ideology_orthodox_patriarch": {
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_disapprove")],
    },
    "ideology_oriental_orthodox_patriarch": {
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_disapprove")],
    },
    "ideology_authoritarian": {
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "++"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "++"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "++"
        ),
    },
    "ideology_austrian_hegemony": {
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "++"
        ),
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "+"
        ),
    },
    "ideology_ethno_nationalist": {
        "lawgroup_ministry_of_population_control": ministry_constructor(
            "ministry_of_population_control", "++"
        ),
    },
    "ideology_anti_clerical": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "--"
        ),
    },
    "ideology_pious": {
        "lawgroup_ministry_of_foreign_affairs": ministry_constructor(
            "ministry_of_foreign_affairs", "+"
        ),
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "-"),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "+"
        ),
    },
    "ideology_isolationist": {
        "lawgroup_ministry_of_foreign_affairs": ministry_constructor(
            "ministry_of_foreign_affairs", "--"
        ),
        "lawgroup_ministry_of_commerce": ministry_constructor(
            "ministry_of_commerce", "-"
        ),
        "lawgroup_colonization": [("law_neocolonialism", "neutral")],
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "-"
        ),
    },
    "ideology_agrarian": {
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "+"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor("ministry_of_labor", "+"),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "-"
        ),
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "+"
        ),
    },
    "ideology_stratocratic": {
        "lawgroup_welfare": [
            ("law_no_social_security", "approve"),
            ("law_poor_laws", "neutral"),
            ("law_wage_subsidies", "disapprove"),
            ("law_old_age_pension", "disapprove"),
            ("law_universal_basic_income", "strongly_disapprove"),
            ("law_post-scarcity", "disapprove"),
        ],
        "lawgroup_ministry_of_emergency_response": ministry_constructor(
            "ministry_of_emergency_response", "-"
        ),
    },
}


modified_entries = modify_entries(entries, modifications)
modified_entries = update_law_reqs(modified_entries)
write_to_file(
    r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\ideologies\modified.txt",
    modified_entries,
)
