import re
import os

from path_constants import mod_path, base_game_path

def parse_goods(file_paths):
    """
    Parses multiple goods files to create a dictionary mapping each good to its cost.
    """
    goods_dict = {}
    for file_path in file_paths:
        with open(file_path, "r") as file:
            goods_data = file.read()
            goods_pattern = re.compile(
                r"(\w+) = \{\s*texture.*?cost = (\d+)", re.DOTALL
            )
            for match in re.finditer(goods_pattern, goods_data):
                good, cost = match.groups()
                goods_dict[good] = int(cost)
    return goods_dict


def calculate_employment(pm_content):
    """
    Calculates the total employment for a production method.
    """
    employment_pattern = re.compile(r"building_employment_(\w+)_add = (-?[\d\.]+)")
    employment_total = sum(
        int(qty) for occupation, qty in employment_pattern.findall(pm_content)
    )
    return employment_total


def calculate_costs(pm_content, goods_dict):
    """
    Calculates the total input and output costs for a production method.
    Throws an error if a good is not found in the goods dictionary.
    """
    input_pattern = re.compile(r"goods_input_(\w+)_add = (-?[\d\.]+)")
    output_pattern = re.compile(r"goods_output_(\w+)_add = (-?[\d\.]+)")

    def get_cost(good, quantity):
        if good not in goods_dict:
            raise ValueError(f"Good '{good}' not found in goods dictionary.")
        return float(quantity) * goods_dict[good]

    input_cost = sum(
        get_cost(good, qty) for good, qty in input_pattern.findall(pm_content)
    )
    output_cost = sum(
        get_cost(good, qty) for good, qty in output_pattern.findall(pm_content)
    )
    return input_cost, output_cost


def process_and_update_production_methods_grouped(
    pms_file_path,
    goods_dict,
    calculate_costs_func,
    calculate_employment_func,
    write_path=None,
):
    """
    Processes the production methods file and updates the 'workforce_scaled' section with input and output goods
    grouped separately, followed by a summary. Removes any existing unrelated comments.
    """
    if type(pms_file_path) == str:
        pms_file_list = [pms_file_path]
    else:
        pms_file_list = pms_file_path
    pms_data = ""
    for file_path in pms_file_list:
        with open(file_path, "r") as file:
            pms_data += file.read() + "\n"

    pms_pattern = re.compile(r"([\w-]+) = \{\s*(.*?)\n\}", re.DOTALL)
    updated_pms_data = pms_data
    for match in re.finditer(pms_pattern, pms_data):
        pm_name, pm_content = match.groups()

        # Targeting the 'workforce_scaled' section for goods
        workforce_scaled_pattern = re.compile(
            r"(workforce_scaled = \{.*?\})", re.DOTALL
        )
        # Targeting the 'level_scaled' section for employment
        level_scaled_pattern = re.compile(r"(level_scaled = \{.*?\})", re.DOTALL)
        workforce_scaled_match = workforce_scaled_pattern.findall(pm_content)
        level_scaled_match = level_scaled_pattern.findall(pm_content)
        updated_pm_content = pm_content
        employment = (
            calculate_employment_func(level_scaled_match[0])
            if level_scaled_match
            else 0
        )
        for workforce_scaled_content in workforce_scaled_match:
            original_workforce_scaled_content = workforce_scaled_content
            # Clear existing comments
            workforce_scaled_content = re.sub(r"#.*?\n", "", workforce_scaled_content)

            # Separate and process input and output goods
            input_goods_content, output_goods_content = "", ""
            good_pattern = re.compile(r"(goods_(input|output)_(\w+)_add = (-?[\d\.]+))")
            for good_match in good_pattern.finditer(workforce_scaled_content):
                full_match, in_out, good, quantity = good_match.groups()
                price = goods_dict.get(good, 0)
                total_cost = price * float(quantity)
                comment = f" # Price: {price: >4}, Total cost: {total_cost}\n"
                if in_out == "input":
                    input_goods_content += ("\t\t\t" + full_match).ljust(
                        55, " "
                    ) + comment
                else:
                    output_goods_content += ("\t\t\t" + full_match).ljust(
                        55, " "
                    ) + comment

            other_lines_content = [
                line
                for line in workforce_scaled_content.split("\n")[1:-1]
                if (not good_pattern.search(line)) and line.strip() != ""
            ]

            # Calculate input and output costs, profit, and profit margin for the entire section
            input_cost, output_cost = calculate_costs_func(
                input_goods_content + output_goods_content, goods_dict
            )
            profit = output_cost - input_cost
            profit_margin = (profit / input_cost) * 100 if input_cost != 0 else 0
            zero_profit_price_multiplier = (
                input_cost / output_cost if output_cost != 0 else 0
            )
            wage_breakeven = profit / employment if employment != 0 else 0

            # Construct the updated workforce_scaled content
            updated_workforce_scaled_content = (
                "workforce_scaled = {\n"
                "\t\t\t# Input goods\n"
                + input_goods_content
                + "\t\t\t# Output goods\n"
                + output_goods_content
                + f"\t\t\t# Total input cost: {input_cost}\n"
                f"\t\t\t# Total output cost: {output_cost}\n"
                f"\t\t\t# Profit: {profit}\n"
                f"\t\t\t# Profit margin: {profit_margin:.2f}%\n"
                f"\t\t\t# Zero profit price multiplier: {zero_profit_price_multiplier:.2f}\n"
                f"\t\t\t# Employment: {employment}\n"
                f"\t\t\t# Wage breakeven: {wage_breakeven:.2f}\n"
                + "\n".join(other_lines_content)
                + "\n" * (len(other_lines_content) > 0)
                + "\t\t}"
            )

            # Update the production method content
            if len(input_goods_content) > 0 or len(output_goods_content) > 0:
                updated_pm_content = updated_pm_content.replace(
                    original_workforce_scaled_content, updated_workforce_scaled_content
                )
        updated_pms_data = updated_pms_data.replace(pm_content, updated_pm_content, 1)

    updated_pms_data = updated_pms_data.strip()

    if write_path is None:
        if type(pms_file_path) == str:
            # Write the updated content back to the production methods file
            with open(pms_file_path, "w") as file:
                file.write(updated_pms_data)
        else:
            raise ValueError(
                "write_path must be specified if multiple production methods files are provided."
            )
    else:
        # Write the updated content to a new file
        with open(write_path, "w") as file:
            file.write(updated_pms_data)


def process_and_update_military_costs(
    military_file_path,
    goods_dict,
    write_path=None,
):
    """
    Processes the production methods file and updates the 'workforce_scaled' section with input and output goods
    grouped separately, followed by a summary. Removes any existing unrelated comments.
    """
    if type(military_file_path) == str:
        military_file_list = [military_file_path]
    else:
        military_file_list = military_file_path
    mil_cost_data = ""
    for file_path in military_file_list:
        with open(file_path, "r") as file:
            mil_cost_data += file.read() + "\n"

    updated_mil_cost_data = mil_cost_data
    mil_cost_pattern = re.compile(
        r"upkeep_modifier = \{\n([^}]*?)\}", re.DOTALL + re.MULTILINE
    )
    for match in re.finditer(mil_cost_pattern, mil_cost_data):
        cost_content = match.groups()[0]
        full_cost = 0

        good_pattern = re.compile(r"(goods_input_(\w+)_add = (-?[\d\.]+))")
        goods_content = ""
        for good_match in good_pattern.finditer(cost_content):
            full_match, good, quantity = good_match.groups()
            price = goods_dict.get(good, 0)
            total_cost = price * float(quantity)
            full_cost += total_cost
            comment = f" # Price: {price: >4}, Total cost: {total_cost}\n"
            goods_content += ("\t\t" + full_match).ljust(55, " ") + comment
        if len(goods_content) > 0:
            updated_cost_content = goods_content + f"\t\t# Total cost: {full_cost}\n\t"
            updated_mil_cost_data = updated_mil_cost_data.replace(
                cost_content, updated_cost_content, 1
            )

    updated_mil_cost_data = updated_mil_cost_data.strip()
    if write_path is None:
        if type(military_file_path) == str:
            # Write the updated content back to the production methods file
            with open(military_file_path, "w") as file:
                file.write(updated_mil_cost_data)
        else:
            raise ValueError(
                "write_path must be specified if multiple production methods files are provided."
            )
    else:
        # Write the updated content to a new file
        with open(write_path, "w") as file:
            file.write(updated_mil_cost_data)


# Example usage
goods_file_paths = [
    mod_path + r"\common\goods\extra_goods.txt",
    base_game_path + r"\game\common\goods\00_goods.txt",
]
pms_file_path = mod_path + r"\common\production_methods\extra_pms.txt"
vanilla_pms_file_loc = (
    base_game_path + r"\game\common\production_methods"
)
vanilla_pm_file_paths = [
    os.path.join(vanilla_pms_file_loc, file)
    for file in os.listdir(vanilla_pms_file_loc)
    if file.endswith(".txt")
]
output_file_path = mod_path + r"\commented_vanilla_pms.txt"
goods_dict = parse_goods(goods_file_paths)

process_and_update_production_methods_grouped(
    pms_file_path, goods_dict, calculate_costs, calculate_employment
)

process_and_update_production_methods_grouped(
    vanilla_pm_file_paths,
    goods_dict,
    calculate_costs,
    calculate_employment,
    output_file_path,
)
print("Production methods file updated successfully.")

# Military costs
vanilla_military_unit_file_path = base_game_path + r"\game\common\combat_unit_types\00_combat_unit_types.txt"
military_unit_file_path = mod_path + r"\common\combat_unit_types\extra_combat_units.txt"
mobilization_file_path = mod_path + r"\common\mobilization_options\extra_mobilization_options.txt"

process_and_update_military_costs(military_unit_file_path, goods_dict)

process_and_update_military_costs(mobilization_file_path, goods_dict)

process_and_update_military_costs(
   vanilla_military_unit_file_path,
   goods_dict,
   write_path=mod_path + r"\commented_vanilla_military_units.txt",
)
print("Military costs file updated successfully.")
