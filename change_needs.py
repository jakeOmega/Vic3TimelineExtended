# -*- coding: utf-8 -*-
"""
Created on Sun Nov 27 01:28:43 2022

@author: jakef
"""

import math
import re

import matplotlib.pyplot as plt
import numpy as np

from path_constants import base_game_path, mod_path


def convenience_need(i):
    if i < 20:
        return 0
    else:
        return int(0.7 * ((i - 19) ** 3 / 4 + 1) * (1 + 3 * math.tanh(i / 200)))


def services_need(i):
    if i < 9:
        return 0
    elif i == 9:
        return 24
    elif i == 10:
        return 30
    elif i == 11:
        return 39
    elif i == 12:
        return 46
    elif i == 13:
        return 58
    elif i == 14:
        return 64
    else:
        return 75 + int(50 * (math.exp(0.14 * (i - 15)) - 1))


def art_need(i):
    if i < 25:
        return 0
    elif i < 50:
        return int(0.02 * (i - 24) ** 3.2 + 1)
    elif i < 75:
        base = int(0.02 * (25) ** 3.2 + 1)
        exp = math.exp(0.12 * (i - 49))
        return int(base * exp)
    else:
        base = art_need(74)
        exp = math.exp(0.15 * (i - 74))
        return int(base * exp)


def tourism_need(i):
    if i < 25:
        return 0
    elif i < 35:
        return int((i - 24) ** 1.5)
    elif i < 40:
        base = tourism_need(34)
        exp = math.exp(0.4 * (i - 34))
        return int(base * exp)
    elif i < 45:
        base = tourism_need(39)
        exp = math.exp(0.2 * (i - 39))
        return int(base * exp)
    else:
        base = tourism_need(44)
        exp = math.exp(0.14 * (i - 44))
        return int(base * exp)


print(tourism_need(100))


# Define the needs and their corresponding functions
needs = {
    "popneed_convenience": convenience_need,
    "popneed_services": services_need,
    "popneed_art": art_need,
    "popneed_tourism": tourism_need,
}


def change_one(i, input_match, need_func):
    text = input_match.group(0)
    match = re.match("([a-zA-Z_]+) = ([0-9\.]+)", text)

    key, val = match.group(1), float(match.group(2))
    # print(i, key + " = " + str(need_func(i)))
    return key + " = " + str(need_func(i))


def extract_all_needs(matches):
    all_needs = set()
    for match in matches:
        goods = re.findall(r"popneed_\w+ = \d+", match)
        for good in goods:
            need = good.split(" = ")[0]
            all_needs.add(need)
    return list(all_needs)


def fit_power_law(x, y):
    x = np.array(x)
    y = np.array(y)

    if len(x) < 2 or np.any(y <= 0):  # Not enough data points or non-positive values
        return None

    try:
        # Use logarithmic transformation
        log_x = np.log(x)
        log_y = np.log(y)

        # Linear fit on log-transformed data
        slope, intercept = np.polyfit(log_x, log_y, 1)

        # Convert back to power law parameters
        a = np.exp(intercept)
        b = slope

        return a, b
    except:
        return None


def extrapolate_power_law(x, a, b):
    return a * (x**b)


def calculate_proportions(buy_packages, pop_needs_defaults, goods_cost):
    """
    Calculates the proportion of weekly expenditure for each need at each wealth level.
    This version is corrected to handle missing needs and prevent data misalignment.
    """
    if not buy_packages:
        return [], {}
    max_wealth = max(buy_packages.keys())
    wealth_levels = list(range(1, max_wealth + 1))

    all_needs_set = set(f"popneed_{need}" for need in pop_needs_defaults.keys())
    for wl in wealth_levels:
        if wl in buy_packages:
            all_needs_set.update(buy_packages[wl].keys())

    all_needs_list = sorted(list(all_needs_set))

    proportions = {need: [] for need in all_needs_list}

    for wl in wealth_levels:
        package = buy_packages.get(wl, {})
        total_weekly_cost = 0
        temp_need_costs = {}

        for need, amount in package.items():
            default_good = pop_needs_defaults.get(need.replace("popneed_", ""))
            if default_good and default_good in goods_cost:
                cost = amount * goods_cost[default_good]
                total_weekly_cost += cost
                temp_need_costs[need] = cost

        for need in all_needs_list:
            need_cost = temp_need_costs.get(need, 0)
            if total_weekly_cost > 0:
                proportion = (need_cost / total_weekly_cost) * 100
                proportions[need].append(proportion)
            else:
                proportions[need].append(0)

    return wealth_levels, proportions


def plot_expenditure_proportions(
    vanilla_buy_packages, modded_buy_packages, pop_needs_defaults, goods_cost
):
    """Generates subplots showing the proportion of expenditure on each need."""
    vanilla_wl, vanilla_props = calculate_proportions(
        vanilla_buy_packages, pop_needs_defaults, goods_cost
    )
    modded_wl, modded_props = calculate_proportions(
        modded_buy_packages, pop_needs_defaults, goods_cost
    )

    all_need_labels = sorted(list(set(vanilla_props.keys()) | set(modded_props.keys())))

    vanilla_data = [
        vanilla_props.get(need, [0] * len(vanilla_wl)) for need in all_need_labels
    ]
    modded_data = [
        modded_props.get(need, [0] * len(modded_wl)) for need in all_need_labels
    ]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), sharex=True)

    ax1.stackplot(
        vanilla_wl,
        vanilla_data,
        labels=[label.replace("popneed_", "") for label in all_need_labels],
        alpha=0.8,
    )
    ax1.set_title("Vanilla: Proportion of Weekly Expenditure by Need", fontsize=16)
    ax1.set_ylabel("Proportion of Expenditure (%)", fontsize=12)
    ax1.legend(loc="center left", bbox_to_anchor=(1, 0.5))
    ax1.set_ylim(0, 100)
    ax1.grid(True)

    ax2.stackplot(
        modded_wl,
        modded_data,
        labels=[label.replace("popneed_", "") for label in all_need_labels],
        alpha=0.8,
    )
    ax2.set_title("Modified: Proportion of Weekly Expenditure by Need", fontsize=16)
    ax2.set_xlabel("Wealth Level", fontsize=12)
    ax2.set_ylabel("Proportion of Expenditure (%)", fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.grid(True)

    plt.xlim(1, max(len(vanilla_wl), len(modded_wl)))
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.show()


input_file_name = base_game_path + r"\game\common\buy_packages\00_buy_packages.txt"
pop_needs_out_path = mod_path + r"\common\buy_packages\00_buy_packages.txt"


with open(input_file_name, "r", encoding="utf-8-sig") as file_obj:
    file_text = file_obj.read()

matches = re.findall("wealth_[0-9]+ = \{.*?\n\}", file_text, re.DOTALL)

values = []

for need_name, need_func in needs.items():
    for i in range(len(matches)):
        function = lambda x: change_one(i, x, need_func)
        if len(re.findall(need_name + " = [0-9\.]+", matches[i])) > 0:
            need_string = re.findall(need_name + " = [0-9\.]+", matches[i])[0]
            matches[i] = re.sub(need_name + " = [0-9\.]+", function, matches[i])
            values += [(i + 1, int(need_string.split("=")[1]))]
        else:
            matches_line = matches[i].split("\n")
            matches_line = [line for line in matches_line if line != ""]
            if need_func(i) == 0:
                continue
            matches[i] = (
                "\n".join(matches_line[:-2])
                + "\n\t\t"
                + need_name
                + " = "
                + str(need_func(i))
                + "\n\t}\n}"
            )
            values += [(i + 1, 0)]

# After processing existing wealth levels
all_needs = extract_all_needs(matches)


# Function to get the value for a specific need and wealth level
def get_need_value(need, wealth_level):
    for match in matches:
        if f"wealth_{wealth_level}" in match:
            need_match = re.search(f"{need} = (\d+)", match)
            if need_match:
                return int(need_match.group(1))
    return 0


# Extrapolate for wealth levels 100 to 200
for need in all_needs:
    # Extract data for wealth levels 90 to 99
    x_data = list(range(90, 100))
    y_data = [get_need_value(need, i) for i in x_data]

    # Only proceed if we have non-zero data
    if any(y_data):
        # Fit power law
        params = fit_power_law(x_data, y_data)

        # Extrapolate for wealth levels 100 to 200
        for i in range(100, 201):
            extrapolated_value = max(0, int(extrapolate_power_law(i, *params)))

            # Find or create the entry for this wealth level
            wealth_entry = next(
                (entry for entry in matches if f"wealth_{i} = {{" in entry), None
            )
            if wealth_entry:
                # Update existing entry
                updated_entry = re.sub(
                    r"(wealth_\d+ = \{.*?goods = \{)(.*?)(\}.*?\})",
                    rf"\1\2\t{need} = {extrapolated_value}\n\t\3",
                    wealth_entry,
                    flags=re.DOTALL,
                )
                matches[matches.index(wealth_entry)] = updated_entry
            else:
                # Create new entry
                new_entry = f"""wealth_{i} = {{
    political_strength = {25 * i - 975:}
    goods = {{
\t\t{need} = {extrapolated_value}
    }}
}}"""
                matches.append(new_entry)

# Sort matches by wealth level
matches.sort(key=lambda x: int(re.search(r"wealth_(\d+)", x).group(1)))

result = "\n\n".join(matches)

with open(pop_needs_out_path, "w", encoding="utf-8-sig") as file_obj:
    file_obj.write(result)


def read_and_combine_files(file_paths):
    """Reads and combines the content of multiple files."""
    combined_content = ""
    for file_path in file_paths:
        with open(file_path, "r", encoding="utf-8-sig") as file:
            combined_content += file.read() + "\n"
    return combined_content


def extract_buy_packages(content):
    """Extracts buy package data from the provided content."""
    pattern = re.compile(r"wealth_(\d+) = {.*?goods = {(.*?)\n\t}", re.DOTALL)
    buy_packages = {}
    for match in pattern.finditer(content):
        wealth_level = int(match.group(1))
        goods_data = match.group(2).strip().split("\n")
        goods = {}
        for good in goods_data:
            good_name, amount = good.split(" = ")
            goods[good_name.strip()] = int(amount)
        buy_packages[wealth_level] = goods
    return buy_packages


def extract_pop_needs_default_goods(content):
    """Extracts the default good for each need from the provided content."""
    pattern = re.compile(r"popneed_(\w+) = {.*?default = (\w+)", re.DOTALL)
    pop_needs_defaults = {}
    for match in pattern.finditer(content):
        need, default_good = match.groups()
        pop_needs_defaults[need] = default_good
    return pop_needs_defaults


def extract_goods_cost(content):
    """Extracts cost of goods from the provided content."""
    pattern = re.compile(r"(\w+) = {.*?cost = (\d+)", re.DOTALL)
    goods_cost = {}
    for match in pattern.finditer(content):
        good, cost = match.groups()
        goods_cost[good] = int(cost)
    return goods_cost


def calculate_buy_package_costs(buy_packages, pop_needs_defaults, goods_cost):
    """Calculates the default cost of each wealth level's buy package."""
    package_costs = {}
    for wealth_level, package in buy_packages.items():
        total_cost = 0
        for need, amount in package.items():
            default_good = pop_needs_defaults.get(need.replace("popneed_", ""), None)
            if default_good in goods_cost:
                total_cost += amount * goods_cost[default_good]
        package_costs[wealth_level] = (
            total_cost / 10000
        )  # buy packages are per 10k working adults
    return package_costs


def calculate_and_write_costs(
    buy_packages_file_paths, pop_needs_file_paths, goods_file_paths, output_file_path
):
    # Combining contents of multiple files for each type
    buy_packages_content = read_and_combine_files(buy_packages_file_paths)
    pop_needs_content = read_and_combine_files(pop_needs_file_paths)
    goods_content = read_and_combine_files(goods_file_paths)

    # Extracting data
    modded_buy_packages = extract_buy_packages(buy_packages_content)
    pop_needs_defaults = extract_pop_needs_default_goods(pop_needs_content)
    goods_cost = extract_goods_cost(goods_content)

    # Calculate Vanilla Costs
    vanilla_buy_packages_content = read_and_combine_files([input_file_name])
    vanilla_buy_packages = extract_buy_packages(vanilla_buy_packages_content)
    vanilla_costs = calculate_buy_package_costs(
        vanilla_buy_packages, pop_needs_defaults, goods_cost
    )

    # Calculate Modded Costs
    modded_costs = calculate_buy_package_costs(
        modded_buy_packages, pop_needs_defaults, goods_cost
    )

    print("Generating graph...")

    # Prepare data for plotting
    vanilla_wealth_levels = sorted(vanilla_costs.keys())
    vanilla_pounds = [vanilla_costs[wl] for wl in vanilla_wealth_levels]

    modded_wealth_levels = sorted(modded_costs.keys())
    modded_pounds = [modded_costs[wl] for wl in modded_wealth_levels]

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(12, 8))

    ax.plot(
        vanilla_pounds,
        vanilla_wealth_levels,
        marker="o",
        linestyle="-",
        label="Vanilla",
    )
    ax.plot(
        modded_pounds,
        modded_wealth_levels,
        marker="x",
        linestyle="--",
        label="Modified",
    )

    ax.set_title("Wealth Level vs. Annual Pop Need Expenditure", fontsize=16)
    ax.set_xlabel("Annual Expenditure (£)", fontsize=12)
    ax.set_ylabel("Wealth Level", fontsize=12)
    ax.legend()
    ax.grid(True)

    # Set a logarithmic scale for the x-axis to better visualize the lower wealth levels
    ax.set_xscale("log")

    plt.tight_layout()

    plot_expenditure_proportions(
        vanilla_buy_packages, modded_buy_packages, pop_needs_defaults, goods_cost
    )


buy_packages_file_paths = [pop_needs_out_path]

pop_needs_file_paths = [
    base_game_path + r"\game\common\pop_needs\00_pop_needs.txt",
    mod_path + r"\common\pop_needs\extra_pop_needs.txt",
]
goods_file_paths = [
    base_game_path + r"\game\common\goods\00_goods.txt",
    mod_path + r"\common\goods\timeline_extended_extra_goods.txt",
]
output_file_path = mod_path + r"\common\script_values\wealth_to_pounds.txt"

# Call the function to calculate and write costs
calculate_and_write_costs(
    buy_packages_file_paths, pop_needs_file_paths, goods_file_paths, output_file_path
)
