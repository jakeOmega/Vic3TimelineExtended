# -*- coding: utf-8 -*-
"""
Created on Sun Nov 27 01:28:43 2022

@author: jakef
"""

import re, math
from pyparsing import nestedExpr, Word, alphanums, OneOrMore, ParseResults
import matplotlib.pyplot as plt


def convenience_need(i):
    if i < 10:
        return 0
    else:
        return int(0.8 * ((i - 8) ** 3 / 4 + 1) * (1 + 3 * math.tanh(i / 200)))


def services_need(i):
    if i < 9:
        return 0
    else:
        return int(12 * math.exp(0.18 * i))


def art_need(i):
    if i < 20:
        return 0
    else:
        return int(1 * (i - 19) ** 3)


# Define the needs and their corresponding functions
needs = {
    "popneed_convenience": convenience_need,
    "popneed_services": services_need,
    "popneed_art": art_need,
}


def change_one(i, input_match, need_func):
    text = input_match.group(0)
    match = re.match("([a-zA-Z_]+) = ([0-9\.]+)", text)

    key, val = match.group(1), float(match.group(2))
    # print(i, key + " = " + str(need_func(i)))
    return key + " = " + str(need_func(i))


input_file_name = r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\buy_packages\00_buy_packages.txt"
pop_needs_out_path = r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\buy_packages\00_buy_packages.txt"

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
            matches[i] = (
                "\n".join(matches_line[:-2])
                + "\n\t\t"
                + need_name
                + " = "
                + str(need_func(i))
                + "\n\t}\n}"
            )
            values += [(i + 1, 0)]

    plt.plot([x[0] for x in values], [x[1] for x in values])
    plt.plot([x[0] for x in values], [need_func(x[0] - 1) for x in values])

result = "\n\n".join(matches)
plt.xlim([8, 100])
plt.ylim([10, 10**6])
plt.semilogy()

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
    r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\pop_needs\00_pop_needs.txt",
    r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\pop_needs\extra_pop_needs.txt",
]
goods_file_paths = [
    r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\goods\00_goods.txt",
    r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\goods\extra_goods.txt",
]
output_file_path = r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\script_values\wealth_to_pounds.txt"

# Call the function to calculate and write costs
calculate_and_write_costs(
    buy_packages_file_paths, pop_needs_file_paths, goods_file_paths, output_file_path
)

# plt.show()
