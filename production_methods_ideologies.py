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


def ministry_constructor_typed(ministry_name, types, attitudes):
    attitude_list = [("law_no_" + ministry_name, "neutral")]
    for ministry_type, attitude in zip(types, attitudes):
        if attitude == "+":
            attitude_text = "approve"
        elif attitude == "-":
            attitude_text = "disapprove"
        elif attitude == "++":
            attitude_text = "strongly_approve"
        elif attitude == "--":
            attitude_text = "strongly_disapprove"
        else:
            raise ValueError
        attitude_list.append(
            ("law_" + ministry_type + "_" + ministry_name, attitude_text)
        )
    return attitude_list


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
            "AND = { has_law = law_type:law_protected_class has_law = law_type:law_full_equality_and_protection }",
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
traditional_inheritance = [
    ("law_primogeniture", "strongly_approve"),
    ("law_partible", "neutral"),
    ("law_equal_inheritance", "disapprove"),
    ("law_non_inheritable_usage_rights", "strongly_disapprove"),
]
reform_inheritance = [
    ("law_primogeniture", "disapprove"),
    ("law_partible", "approve"),
    ("law_equal_inheritance", "approve"),
    ("law_non_inheritable_usage_rights", "disapprove"),
]
progressive_inheritance = [
    ("law_primogeniture", "strongly_disapprove"),
    ("law_partible", "neutral"),
    ("law_equal_inheritance", "approve"),
    ("law_non_inheritable_usage_rights", "strongly_approve"),
]
radical_inheritance = [
    ("law_primogeniture", "strongly_disapprove"),
    ("law_partible", "disapprove"),
    ("law_equal_inheritance", "neutral"),
    ("law_non_inheritable_usage_rights", "strongly_approve"),
]
communal_inheritance = [
    ("law_primogeniture", "strongly_disapprove"),
    ("law_partible", "disapprove"),
    ("law_equal_inheritance", "neutral"),
    ("law_non_inheritable_usage_rights", "strongly_approve"),
]
moderate_inheritance = [
    ("law_primogeniture", "disapprove"),
    ("law_partible", "approve"),
    ("law_equal_inheritance", "neutral"),
    ("law_non_inheritable_usage_rights", "strongly_disapprove"),
]
bonapartist_inheritance = [
    ("law_primogeniture", "disapprove"),
    ("law_partible", "neutral"),
    ("law_equal_inheritance", "strongly_approve"),
    ("law_non_inheritable_usage_rights", "disapprove"),
]
aggressive_rules_of_war = [
    ("law_traditional_rules_of_war", "approve"),
    ("law_war_crimes_forbidden", "neutral"),
    ("law_humanitarian_regulations", "disapprove"),
    ("law_limited_war", "strongly_disapprove"),
    ("law_total_war", "strongly_approve"),
]
moderate_rules_of_war = [
    ("law_traditional_rules_of_war", "neutral"),
    ("law_war_crimes_forbidden", "approve"),
    ("law_humanitarian_regulations", "neutral"),
    ("law_limited_war", "disapprove"),
    ("law_total_war", "disapprove"),
]
peaceful_rules_of_war = [
    ("law_traditional_rules_of_war", "disapprove"),
    ("law_war_crimes_forbidden", "neutral"),
    ("law_humanitarian_regulations", "approve"),
    ("law_limited_war", "strongly_approve"),
    ("law_total_war", "strongly_disapprove"),
]
traditional_rules_of_war = [
    ("law_traditional_rules_of_war", "approve"),
    ("law_war_crimes_forbidden", "neutral"),
    ("law_humanitarian_regulations", "disapprove"),
    ("law_limited_war", "disapprove"),
    ("law_total_war", "neutral"),
]
advanced_curency = [
    ("law_commodity_money", "disapprove"),
    ("law_gold_standard", "neutral"),
    ("law_fiat_currency", "approve"),
    ("law_digital_currency", "strongly_approve"),
]
simple_currency = [
    ("law_commodity_money", "neutral"),
    ("law_gold_standard", "approve"),
    ("law_fiat_currency", "disapprove"),
    ("law_digital_currency", "disapprove"),
]
pro_secrecy = [
    ("law_informal_government_secrecy", "neutral"),
    ("law_state_secrets", "approve"),
    ("law_freedom_of_information", "disapprove"),
    ("law_open_government", "strongly_disapprove"),
]
anti_secrecy = [
    ("law_informal_government_secrecy", "neutral"),
    ("law_state_secrets", "disapprove"),
    ("law_freedom_of_information", "approve"),
    ("law_open_government", "strongly_approve"),
]
regressive_criminal_justice = [
    ("law_punishment_focused_criminal_justice", "strongly_approve"),
    ("law_rehabilitation_focused_criminal_justice", "disapprove"),
    ("law_restorative_justice", "neutral"),
]
progressive_criminal_justice = [
    ("law_punishment_focused_criminal_justice", "disapprove"),
    ("law_rehabilitation_focused_criminal_justice", "strongly_approve"),
    ("law_restorative_justice", "neutral"),
]
moderate_criminal_justice = [
    ("law_punishment_focused_criminal_justice", "disapprove"),
    ("law_rehabilitation_focused_criminal_justice", "neutral"),
    ("law_restorative_justice", "approve"),
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
minority_hate = [
    ("law_minority_rights_violent_hostility", "strongly_approve"),
    ("law_minority_rights_ghettoization", "approve"),
    ("law_minority_rights_cultural_assimilation", "disapprove"),
    ("law_minority_rights_discrimination", "neutral"),
    ("law_minority_rights_indifference", "disapprove"),
    ("law_minority_rights_protection", "strongly_disapprove"),
    ("law_minority_rights_affirmative_action", "strongly_disapprove"),
]
minority_dislike = [
    ("law_minority_rights_violent_hostility", "approve"),
    ("law_minority_rights_ghettoization", "strongly_approve"),
    ("law_minority_rights_cultural_assimilation", "approve"),
    ("law_minority_rights_discrimination", "strongly_approve"),
    ("law_minority_rights_indifference", "neutral"),
    ("law_minority_rights_protection", "disapprove"),
    ("law_minority_rights_affirmative_action", "strongly_disapprove"),
]
minority_like = [
    ("law_minority_rights_violent_hostility", "strongly_disapprove"),
    ("law_minority_rights_ghettoization", "disapprove"),
    ("law_minority_rights_cultural_assimilation", "neutral"),
    ("law_minority_rights_discrimination", "disapprove"),
    ("law_minority_rights_indifference", "approve"),
    ("law_minority_rights_protection", "approve"),
    ("law_minority_rights_affirmative_action", "neutral"),
]
minority_love = [
    ("law_minority_rights_violent_hostility", "strongly_disapprove"),
    ("law_minority_rights_ghettoization", "strongly_disapprove"),
    ("law_minority_rights_cultural_assimilation", "disapprove"),
    ("law_minority_rights_discrimination", "disapprove"),
    ("law_minority_rights_indifference", "neutral"),
    ("law_minority_rights_protection", "approve"),
    ("law_minority_rights_affirmative_action", "strongly_approve"),
]

modifications = {
    "ideology_paternalistic": {
        "lawgroup_privacy_rights": anti_privacy_entry,
        "lawgroup_human_augmentation": highly_regulated_augmentation,
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "++"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_particularist": {
        "lawgroup_privacy_rights": pro_privacy_entry,
        "lawgroup_monetary_policy": simple_currency,
        "lawgroup_national_bank": ministry_constructor("national_bank", "--"),
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "-"
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
        "lawgroup_rules_of_war": aggressive_rules_of_war,
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
        "lawgroup_right_to_information": anti_secrecy,
        "lawgroup_human_augmentation": lightly_regulated_augmentation,
        "lawgroup_LGBTQ_rights": lgbtq_like,
        "lawgroup_rules_of_war": peaceful_rules_of_war,
        "lawgroup_criminal_justice": progressive_criminal_justice,
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
        "lawgroup_inheritance": moderate_inheritance,
        "lawgroup_minority_rights": minority_like,
    },
    "ideology_liberal_modern": {
        "lawgroup_privacy_rights": pro_privacy_entry,
        "lawgroup_human_augmentation": lightly_regulated_augmentation,
        "lawgroup_LGBTQ_rights": lgbtq_like,
        "lawgroup_rules_of_war": peaceful_rules_of_war,
        "lawgroup_criminal_justice": progressive_criminal_justice,
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
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "+"
        ),
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "+"
        ),
        "lawgroup_minority_rights": minority_like,
    },
    "ideology_market_liberal": {
        "lawgroup_privacy_rights": reform_privacy_entry,
        "lawgroup_human_augmentation": lightly_regulated_augmentation,
        "lawgroup_intellectual_property": moderate_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_indifference,
        "lawgroup_rules_of_war": peaceful_rules_of_war,
        "lawgroup_criminal_justice": moderate_criminal_justice,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "-"
        ),
        "lawgroup_national_bank": ministry_constructor("national_bank", "+"),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "-"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "-"
        ),
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "+"
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
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "-"
        ),
        "lawgroup_minority_rights": minority_like,
    },
    "ideology_traditionalist": {
        "lawgroup_privacy_rights": trad_privacy_entry,
        "lawgroup_human_augmentation": anti_augmentation,
        "lawgroup_intellectual_property": moderate_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_dislike,
        "lawgroup_rules_of_war": traditional_rules_of_war,
        "lawgroup_criminal_justice": regressive_criminal_justice,
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
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_minority_rights": minority_dislike,
    },
    "ideology_reformer": {
        "lawgroup_privacy_rights": reform_privacy_entry,
        "lawgroup_human_augmentation": medical_augmentation,
        "lawgroup_intellectual_property": moderate_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_like,
        "lawgroup_rules_of_war": moderate_rules_of_war,
        "lawgroup_criminal_justice": moderate_criminal_justice,
        "lawgroup_rights_of_women": [("law_protected_class", "disapprove")],
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "+"
        ),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "+"
        ),
        "lawgroup_inheritance": reform_inheritance,
        "lawgroup_minority_rights": minority_like,
    },
    "ideology_populist": {
        "lawgroup_privacy_rights": reform_privacy_entry,
        "lawgroup_right_to_information": anti_secrecy,
        "lawgroup_human_augmentation": populist_augmentation,
        "lawgroup_ministry_of_culture": ministry_constructor(
            "ministry_of_culture", "+"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor_typed(
            "ministry_of_labor", ["pro_labor", "pro_capital"], ["+", "-"]
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
        "lawgroup_minority_rights": minority_like,
    },
    "ideology_radical": {
        "lawgroup_privacy_rights": pro_privacy_entry,
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_criminal_justice": progressive_criminal_justice,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "-"
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
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "strongly_approve"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_social_democrat": {
        "lawgroup_privacy_rights": reform_privacy_entry,
        "lawgroup_human_augmentation": medical_augmentation,
        "lawgroup_intellectual_property": loose_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_like,
        "lawgroup_criminal_justice": progressive_criminal_justice,
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
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "+"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "--"
        ),
        "lawgroup_inheritance": reform_inheritance,
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "neutral"),
        ],
    },
    "ideology_vanguardist": {
        "lawgroup_privacy_rights": extremist_privacy_entry,
        "lawgroup_intellectual_property": communal_ip_laws,
        "lawgroup_rules_of_war": aggressive_rules_of_war,
        "lawgroup_criminal_justice": regressive_criminal_justice,
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
        "lawgroup_governance_principles": [
            ("law_corporation_state", "strongly_disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "approve"),
        ],
    },
    "ideology_fascist": {
        "lawgroup_privacy_rights": extremist_privacy_entry,
        "lawgroup_human_augmentation": extremist_augmentation,
        "lawgroup_LGBTQ_rights": lgbtq_hate,
        "lawgroup_rules_of_war": aggressive_rules_of_war,
        "lawgroup_right_to_information": pro_secrecy,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "++"
        ),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "-"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "--"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "++"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "++"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
        "lawgroup_minority_rights": minority_hate,
    },
    "ideology_anarchist": {
        "lawgroup_privacy_rights": pro_privacy_entry,
        "lawgroup_human_augmentation": unregulated_augmentation,
        "lawgroup_intellectual_property": communal_ip_laws,
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_rules_of_war": peaceful_rules_of_war,
        "lawgroup_criminal_justice": progressive_criminal_justice,
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "--"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "--"
        ),
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "-"
        ),
        "lawgroup_inheritance": communal_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "strongly_disapprove"),
            ("law_direct_democracy", "approve"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
        "lawgroup_minority_rights": minority_like,
    },
    "ideology_laissez_faire": {
        "lawgroup_ministry_of_commerce": ministry_constructor(
            "ministry_of_commerce", "++"
        ),
        "lawgroup_national_bank": ministry_constructor("national_bank", "+"),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "--"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor_typed(
            "ministry_of_labor", ["pro_labor", "pro_capital"], ["--", "+"]
        ),
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
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_egalitarian": {
        "lawgroup_LGBTQ_rights": lgbtq_indifference,
        "lawgroup_criminal_justice": moderate_criminal_justice,
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "++"
        ),
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "+"
        ),
    },
    "ideology_egalitarian_modern": {
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_criminal_justice": progressive_criminal_justice,
        "lawgroup_rights_of_women": [("law_protected_class", "approve")],
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "++"
        ),
    },
    "ideology_meritocratic": {
        "lawgroup_human_augmentation": unregulated_augmentation,
        "lawgroup_intellectual_property": strict_ip_laws,
        "lawgroup_monetary_policy": advanced_curency,
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "+"),
        "lawgroup_ministry_of_commerce": ministry_constructor(
            "ministry_of_commerce", "+"
        ),
        "lawgroup_national_bank": ministry_constructor("national_bank", "+"),
        "lawgroup_ministry_of_labor": ministry_constructor_typed(
            "ministry_of_labor", ["pro_labor", "pro_capital"], ["--", "-"]
        ),
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "+"
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
        "lawgroup_inheritance": moderate_inheritance,
    },
    "ideology_jingoist": {
        "lawgroup_human_augmentation": militarist_augmentation,
        "lawgroup_right_to_information": pro_secrecy,
        "lawgroup_ministry_of_foreign_affairs": ministry_constructor(
            "ministry_of_foreign_affairs", "+"
        ),
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "++"),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_colonization": [("law_neocolonialism", "neutral")],
    },
    "ideology_jingoist_leader": {
        "lawgroup_human_augmentation": militarist_augmentation,
        "lawgroup_ministry_of_foreign_affairs": ministry_constructor(
            "ministry_of_foreign_affairs", "++"
        ),
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "++"),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_rules_of_war": aggressive_rules_of_war,
        "lawgroup_colonization": [("law_neocolonialism", "neutral")],
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
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "+"
        ),
        "lawgroup_ministry_of_consumer_protection": ministry_constructor(
            "ministry_of_consumer_protection", "--"
        ),
        "lawgroup_inheritance": moderate_inheritance,
    },
    "ideology_proletarian": {
        "lawgroup_intellectual_property": communal_ip_laws,
        "lawgroup_ministry_of_labor": ministry_constructor_typed(
            "ministry_of_labor", ["pro_labor", "pro_capital"], ["++", "--"]
        ),
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
        "lawgroup_inheritance": progressive_inheritance,
    },
    "ideology_communist": {
        "lawgroup_intellectual_property": communal_ip_laws,
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor_typed(
            "ministry_of_labor", ["pro_labor", "pro_capital"], ["++", "--"]
        ),
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "-"
        ),
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "+"
        ),
        "lawgroup_inheritance": communal_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "strongly_disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_pacifist": {
        "lawgroup_ministry_of_war": ministry_constructor("ministry_of_war", "--"),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "++"
        ),
        "lawgroup_rules_of_war": peaceful_rules_of_war,
        "lawgroup_colonization": [("law_neocolonialism", "neutral")],
    },
    "ideology_plutocratic": {
        "lawgroup_intellectual_property": strict_ip_laws,
        "lawgroup_monetary_policy": advanced_curency,
        "lawgroup_ministry_of_culture": ministry_constructor(
            "ministry_of_culture", "-"
        ),
        "lawgroup_governance_principles": [
            ("law_corporation_state", "approve"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_colonization": [("law_neocolonialism", "strongly_approve")],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "neutral"),
        ],
    },
    "ideology_patriarchal": {
        "lawgroup_LGBTQ_rights": lgbtq_dislike,
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_disapprove")],
    },
    "ideology_patriarchal_suffrage": {
        "lawgroup_rights_of_women": [("law_protected_class", "disapprove")],
        "lawgroup_LGBTQ_rights": lgbtq_dislike,
    },
    "ideology_feminist": {
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_rights_of_women": [
            ("law_womens_suffrage", "approve"),
            ("law_protected_class", "strongly_approve"),
        ],
    },
    "ideology_feminist_ig": {
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_rights_of_women": [
            ("law_women_own_property", "disapprove"),
            ("law_women_in_the_workplace", "neutral"),
            ("law_womens_suffrage", "approve"),
            ("law_protected_class", "strongly_approve"),
        ],
    },
    "ideology_humanitarian": {
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_criminal_justice": progressive_criminal_justice,
        "lawgroup_rules_of_war": peaceful_rules_of_war,
        "lawgroup_right_to_information": anti_secrecy,
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_approve")],
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "+"
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
        "lawgroup_minority_rights": minority_love,
    },
    "ideology_humanitarian_royalist": {
        "lawgroup_LGBTQ_rights": lgbtq_love,
        "lawgroup_criminal_justice": progressive_criminal_justice,
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_approve")],
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "+"
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
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "neutral"),
        ],
        "lawgroup_minority_rights": minority_love,
    },
    "ideology_reactionary": {
        "lawgroup_LGBTQ_rights": lgbtq_hate,
        "lawgroup_right_to_information": pro_secrecy,
        "lawgroup_criminal_justice": regressive_criminal_justice,
        "lawgroup_ministry_of_intelligence_and_security": ministry_constructor(
            "ministry_of_intelligence_and_security", "++"
        ),
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "-"
        ),
        "lawgroup_ministry_of_culture": ministry_constructor(
            "ministry_of_culture", "+"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor_typed(
            "ministry_of_labor", ["pro_labor", "pro_capital"], ["-", "+"]
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "--"
        ),
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "+"
        ),
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
        "lawgroup_governance_principles": [
            ("law_corporation_state", "neutral"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_minority_rights": minority_dislike,
    },
    "ideology_theocrat": {
        "lawgroup_LGBTQ_rights": lgbtq_hate,
        "lawgroup_rules_of_war": traditional_rules_of_war,
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "++"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_republican": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "neutral"),
            ("law_direct_democracy", "approve"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_republican_paternalistic": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "approve"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_socialist": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "strongly_disapprove"),
            ("law_direct_democracy", "neutral"),
        ],
    },
    "ideology_scholar_paternalistic": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "neutral"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_junker_paternalistic": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "neutral"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_papal_paternalistic": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "neutral"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_papal_moralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_confucian": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_bakufu": {
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "neutral"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_shinto_moralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_caudillismo": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "approve"),
        ],
    },
    "ideology_buddhist_moralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_inheritance": reform_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_hindu_moralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_inheritance": moderate_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_sikh_moralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_inheritance": reform_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_heavenly_kingdom_theocratic": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_orleanist": {
        "lawgroup_inheritance": reform_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_legitimist": {
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_bonapartist": {
        "lawgroup_inheritance": bonapartist_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_atheist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "-"
        ),
        "lawgroup_governance_principles": [
            ("law_corporation_state", "neutral"),
            ("law_direct_democracy", "neutral"),
        ],
    },
    "ideology_republican_leader": {
        "lawgroup_inheritance": reform_inheritance,
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "neutral"),
        ],
    },
    "ideology_royalist": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "disapprove"),
        ],
    },
    "ideology_jacksonian_democrat": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "neutral"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_positivist": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "disapprove"),
            ("law_direct_democracy", "neutral"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "strongly_approve"),
        ],
    },
    "ideology_russian_patriarch": {
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_disapprove")],
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_orthodox_patriarch": {
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_disapprove")],
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_oriental_orthodox_patriarch": {
        "lawgroup_rights_of_women": [("law_protected_class", "strongly_disapprove")],
        "lawgroup_inheritance": traditional_inheritance,
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_authoritarian": {
        "lawgroup_ministry_of_thought_control": ministry_constructor(
            "ministry_of_thought_control", "++"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "++"
        ),
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "neutral"),
        ],
    },
    "ideology_austrian_hegemony": {
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "++"
        ),
    },
    "ideology_ethno_nationalist": {
        "lawgroup_minority_rights": minority_hate,
    },
    "ideology_anti_clerical": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "--"
        ),
    },
    "ideology_pious": {
        "lawgroup_rules_of_war": moderate_rules_of_war,
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
        "lawgroup_ministry_of_international_aid": ministry_constructor(
            "ministry_of_international_aid", "-"
        ),
        "lawgroup_ministry_of_refugee_affairs": ministry_constructor(
            "ministry_of_refugee_affairs", "-"
        ),
        "lawgroup_colonization": [("law_neocolonialism", "neutral")],
    },
    "ideology_agrarian": {
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "+"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor_typed(
            "ministry_of_labor", ["pro_labor", "pro_capital"], ["+", "-"]
        ),
        "lawgroup_ministry_of_urban_planning": ministry_constructor(
            "ministry_of_urban_planning", "-"
        ),
        "lawgroup_ministry_of_science": ministry_constructor(
            "ministry_of_science", "-"
        ),
        "lawgroup_inheritance": reform_inheritance,
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
        "lawgroup_rules_of_war": traditional_rules_of_war,
        "lawgroup_right_to_information": pro_secrecy,
        "lawgroup_criminal_justice": regressive_criminal_justice,
        "lawgroup_monetary_policy": simple_currency,
    },
    "ideology_constitutionalist": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "neutral"),
            ("law_direct_democracy", "approve"),
        ],
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "approve"),
        ],
    },
    "ideology_corporatist_leader": {
        "lawgroup_governance_principles": [
            ("law_corporation_state", "neutral"),
            ("law_direct_democracy", "neutral"),
        ],
    },
    "ideology_agrarian_jeffersonian": {
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
        "lawgroup_ministry_of_the_environment": ministry_constructor(
            "ministry_of_the_environment", "+"
        ),
        "lawgroup_ministry_of_labor": ministry_constructor_typed(
            "ministry_of_labor", ["pro_labor", "pro_capital"], ["+", "-"]
        ),
        "lawgroup_inheritance": reform_inheritance,
    },
    "ideology_integralist": {
        "lawgroup_ministry_of_religion": ministry_constructor(
            "ministry_of_religion", "++"
        ),
        "lawgroup_ministry_of_propaganda": ministry_constructor(
            "ministry_of_propaganda", "+"
        ),
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "disapprove"),
        ],
    },
    "ideology_liberal_leader": {
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "neutral"),
        ],
        "lawgroup_minority_rights": minority_like,
    },
    "ideology_despotic_utopian": {
        "lawgroup_distribution_of_power": [
            ("law_algorithmic_governance", "strongly_approve"),
        ],
        "lawgroup_minority_rights": minority_love,
    },
}


modified_entries = modify_entries(entries, modifications)
modified_entries = update_law_reqs(modified_entries)
write_to_file(
    r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Vic3TimelineExtended\common\ideologies\modified.txt",
    modified_entries,
)
