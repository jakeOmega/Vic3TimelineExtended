# -*- coding: utf-8 -*-
"""
Created on Sun Nov 27 01:28:43 2022

@author: jakef
"""

import re, math
from pyparsing import nestedExpr, Word, alphanums, OneOrMore, ParseResults
import numpy as np
from path_constants import mod_path, base_game_path

def convenience_need(i):
    if i < 20:
        return 0
    else:
        return int(0.7 * ((i - 19) ** 3 / 4 + 1) * (1 + 3 * math.tanh(i / 200)))


def services_need(i):
    if i < 9:
        return 0
    elif i < 20:
        return 12 * (i - 9) + 24
    else:
        return services_need(19) + int(50 * (math.exp(0.2 * (i - 19)) - 1))


def art_need(i):
    if i < 25:
        return 0
    else:
        return int(0.02 * (i - 24) ** 4 + 1)


def housing_need(i):
    return max(1, int(services_need(i) ** 0.8 * services_need(20) ** 0.2))


# Define the needs and their corresponding functions
needs = {
    "popneed_convenience": convenience_need,
    "popneed_services": services_need,
    "popneed_art": art_need,
    "popneed_housing": housing_need,
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
    def power_law(x, a, b):
        return a * (x**b)

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
        package_costs[wealth_level] = total_cost
    return package_costs


def calculate_and_write_costs(
    buy_packages_file_paths, pop_needs_file_paths, goods_file_paths, output_file_path
):
    # Combining contents of multiple files for each type
    buy_packages_content = read_and_combine_files(buy_packages_file_paths)
    pop_needs_content = read_and_combine_files(pop_needs_file_paths)
    goods_content = read_and_combine_files(goods_file_paths)

    # Extracting data
    buy_packages = extract_buy_packages(buy_packages_content)
    pop_needs_defaults = extract_pop_needs_default_goods(pop_needs_content)
    goods_cost = extract_goods_cost(goods_content)

    # Calculating costs
    buy_package_costs = calculate_buy_package_costs(
        buy_packages, pop_needs_defaults, goods_cost
    )

    # Writing to output file
    with open(output_file_path, "w", encoding="utf-8-sig") as file:
        file.write("wealth_in_pounds = {\n")
        for wealth_level, cost in buy_package_costs.items():
            file.write(
                f"    if = {{ limit = {{ wealth = {wealth_level} }} value = {cost} }}\n"
            )
        file.write("}\n")


# Example file paths (replace with your actual file paths)
buy_packages_file_paths = [pop_needs_out_path]

pop_needs_file_paths = [
   base_game_path + r"\game\common\pop_needs\00_pop_needs.txt",
   mod_path + r"\common\pop_needs\extra_pop_needs.txt",
]
goods_file_paths = [
   base_game_path + r"\game\common\goods\00_goods.txt",
   mod_path + r"\common\goods\extra_goods.txt",
]
output_file_path = mod_path + r"\common\script_values\wealth_to_pounds.txt"

# Call the function to calculate and write costs
calculate_and_write_costs(
    buy_packages_file_paths, pop_needs_file_paths, goods_file_paths, output_file_path
)
