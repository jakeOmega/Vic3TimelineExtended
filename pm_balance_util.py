from typing import List, Tuple

# Parse files into dictionary


def parse_files_to_dict(files: List[str]) -> dict:
    goods_dict = {}
    for file in files:
        with open(file, "r") as f:
            good_name = None
            for line in f:
                # Ignore lines that start with "#"
                if line.startswith("#"):
                    continue

                # Split line by equals sign and strip whitespace
                parts = line.split("=")
                key = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else None

                # If line is the start of a good, store name
                if value == "{":
                    good_name = key

                # If line is the cost of a good, store cost
                elif key == "cost":
                    goods_dict[good_name] = int(value)

                # If line is the end of a good, reset name
                elif value == "}":
                    good_name = None

    return goods_dict


# Calculate total cost or revenue


def calculate_total_cost_or_revenue(
    goods_dict: dict, goods: List[Tuple[str, float]]
) -> float:
    return sum(amount * goods_dict[good] for good, amount in goods)


# Calculate input goods amounts


def calculate_input_goods_amounts(
    goods_dict,
    input_goods: List[Tuple[str, float]],
    output_goods: List[Tuple[str, float]],
    desired_profit,
    rounding_base=1,
):
    # Output amounts are fixed
    total_output_revenue = calculate_total_cost_or_revenue(goods_dict, output_goods)

    # Initialize range of possible input amounts
    min_input_amount = 0
    max_input_amount = total_output_revenue / min(
        goods_dict[good] for good, _ in input_goods
    )

    # Initialize input amount as midpoint of range
    total_input_amount = (min_input_amount + max_input_amount) / 2

    # Initialize step size for Newton-Raphson method
    step_size = 0.001

    # Iteratively adjust input amount until profit condition is met or max iterations are reached
    max_iterations = 1000000
    for i in range(max_iterations):
        # Calculate total cost and profit
        total_input_cost = calculate_total_cost_or_revenue(
            goods_dict,
            [(good, total_input_amount * ratio) for good, ratio in input_goods],
        )
        profit = total_output_revenue - total_input_cost

        # If profit condition is met, break the loop
        if abs(profit - desired_profit) < 1e-6:
            break

        # Calculate derivative of profit with respect to input amount
        delta = 1e-6
        total_input_cost_plus_delta = calculate_total_cost_or_revenue(
            goods_dict,
            [
                (good, (total_input_amount + delta) * ratio)
                for good, ratio in input_goods
            ],
        )
        profit_plus_delta = total_output_revenue - total_input_cost_plus_delta
        derivative = (profit_plus_delta - profit) / delta

        # Update input amount using Newton-Raphson method
        total_input_amount = (
            total_input_amount - step_size * (profit - desired_profit) / derivative
        )

    # Round amounts to the nearest rounding base
    input_amounts = {
        good: round(total_input_amount * ratio / rounding_base) * rounding_base
        for good, ratio in input_goods
    }

    profit = total_output_revenue - calculate_total_cost_or_revenue(
        goods_dict, [(key, input_amounts[key]) for key in input_amounts.keys()]
    )

    return (
        input_amounts,
        profit,
    )


files = [
    r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\goods\extra_goods.txt",
    r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\goods\00_goods.txt",
]
goods_dict = parse_files_to_dict(files)

print(
    calculate_input_goods_amounts(
        goods_dict,
        [
            ("steel", 11),
            ("glass", 11),
            ("tools", 5),
            ("transportation", 50),
            ("electricity", 105),
            ("electronic_components", 16),
            ("digital_access", 50),
        ],
        [("services", 1000), ("fine_art", 30), ("educational_services", 0.6)],
        1000,
        0.000001,
    )
)
