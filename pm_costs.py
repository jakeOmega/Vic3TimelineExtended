"""Annotate production method files with input/output cost comments.

Parses goods prices, then calculates and injects cost summaries into
workforce_scaled blocks of PM files. Also handles military unit upkeep costs.

Goods prices come from parsed vanilla data (`regenerate(mod_state)` takes
`mod_state.base_parsers`; standalone, the game's `00_goods.txt` when it's there,
else the committed `vanilla_parsed/` snapshot), so everything that annotates the
MOD's files runs with no Victoria 3 install. The two `docs/engine/commented_vanilla_*`
reference files are the exception: they re-emit vanilla's raw PM and combat-unit
text with cost comments, so they are written only from the game files
(`vanilla_files=False`, or no game files, leaves them as committed).

Usage:
    python pm_costs.py             # Annotate mod PMs + generate commented vanilla files
    python pm_costs.py --dry-run   # Show what would be written without writing

Functions are importable:
    from pm_costs import parse_goods, calculate_costs, calculate_employment
"""

import argparse
import os
import re


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


def _unwrap(value):
    """Strip the (operator, value) tuples ParadoxFileParser wraps values in."""
    while isinstance(value, tuple) and len(value) >= 2:
        value = value[1]
    return value


def goods_from_parsed(goods_data):
    """{good: cost} from parsed Goods data (ModState.base_parsers["Goods"].data
    or the vanilla_parsed snapshot), the same prices `parse_goods` reads from
    a goods file. A good with no numeric `cost` is left out."""
    goods_dict = {}
    for good, body in goods_data.items():
        body = _unwrap(body)
        cost = _unwrap(body.get("cost")) if isinstance(body, dict) else None
        try:
            goods_dict[good] = int(float(cost))
        except (TypeError, ValueError):
            continue
    return goods_dict


def _vanilla_game_dir():
    """<base_game_path>/game, or None when this machine has no game install
    configured (path_constants raises RuntimeError for an unresolvable path)."""
    try:
        from path_constants import base_game_path
    except RuntimeError:
        return None
    return os.path.join(base_game_path, "game")


def load_goods(mod_state=None):
    """{good: cost}: vanilla's prices, then the mod's goods file over them.

    Vanilla from `mod_state` when given, else the game's `00_goods.txt` when
    this machine has it, else the committed `vanilla_parsed/` snapshot."""
    from path_constants import mod_path

    mod_goods = os.path.join(mod_path, "common", "goods", "timeline_extended_extra_goods.txt")
    game_dir = _vanilla_game_dir()
    vanilla_goods = os.path.join(game_dir, "common", "goods", "00_goods.txt") if game_dir else None
    if mod_state is None and vanilla_goods and os.path.isfile(vanilla_goods):
        return parse_goods([vanilla_goods, mod_goods])

    import vanilla_parsed

    goods_dict = goods_from_parsed(vanilla_parsed.parsed_entities(("Goods",), mod_state)["Goods"])
    goods_dict.update(parse_goods([mod_goods]))
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
    if isinstance(pms_file_path, str):
        pms_file_list = [pms_file_path]
    else:
        pms_file_list = pms_file_path
    pms_data = ""
    for file_path in pms_file_list:
        # utf-8-sig strips any leading BOM on read so the utf-8-sig writes below
        # emit exactly one BOM (Paradox wants BOM; double-BOM is a parse error).
        with open(file_path, "r", encoding='utf-8-sig') as file:
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
            # Clear existing comments (preserve newlines to avoid merging lines)
            workforce_scaled_content = re.sub(r"#[^\n]*", "", workforce_scaled_content)

            # Separate and process input and output goods
            input_goods_content, output_goods_content = "", ""
            good_pattern = re.compile(r"(goods_(input|output)_(\w+)_add = (-?[\d\.]+))")
            total_input_cost, total_output_cost = 0, 0
            for good_match in good_pattern.finditer(workforce_scaled_content):
                full_match, in_out, good, quantity = good_match.groups()
                price = goods_dict.get(good, 0)
                total_cost = price * float(quantity)
                if in_out == "input":
                    total_input_cost += total_cost
                else:
                    total_output_cost += total_cost
            for good_match in good_pattern.finditer(workforce_scaled_content):
                full_match, in_out, good, quantity = good_match.groups()
                price = goods_dict.get(good, 0)
                total_cost = price * float(quantity)
                percentage = (
                    (total_cost / total_input_cost * 100)
                    if in_out == "input" and total_input_cost != 0
                    else (total_cost / total_output_cost * 100)
                    if in_out == "output" and total_output_cost != 0
                    else 0
                )
                comment = f" # Price: {price: >4}, Total cost: {total_cost:7.1f} ({percentage:.2f}%)\n"
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
            other_lines_str = "\n".join(other_lines_content)
            other_section = ""
            if other_lines_str.strip():
                other_section = (
                    "\t\t\t# Other modifiers\n"
                    + other_lines_str + "\n"
                )
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
                + other_section
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
        if isinstance(pms_file_path, str):
            # Write the updated content back to the production methods file
            # (utf-8-sig: emit the BOM the Clausewitz engine expects on mod .txt)
            with open(pms_file_path, "w", encoding="utf-8-sig") as file:
                file.write(updated_pms_data)
        else:
            raise ValueError(
                "write_path must be specified if multiple production methods files are provided."
            )
    else:
        # Write the updated content to a new file (utf-8-sig: emit BOM)
        with open(write_path, "w", encoding="utf-8-sig") as file:
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
    if isinstance(military_file_path, str):
        military_file_list = [military_file_path]
    else:
        military_file_list = military_file_path
    mil_cost_data = ""
    for file_path in military_file_list:
        # Tolerate vanilla files that have been split/renamed across patches —
        # e.g. 01_navy_combat_unit_types.txt was removed when ship_types/ was
        # introduced. Skipping is fine: nothing to annotate from a missing file.
        if not os.path.exists(file_path):
            continue
        with open(file_path, "r") as file:
            mil_cost_data += file.read() + "\n"
    if not mil_cost_data.strip():
        return

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
        for good_match in good_pattern.finditer(cost_content):
            full_match, good, quantity = good_match.groups()
            price = goods_dict.get(good, 0)
            total_cost = price * float(quantity)
            percentage = (total_cost / full_cost * 100) if full_cost != 0 else 0
            comment = f" # Price: {price: >4}, Total cost: {total_cost:7.1f} ({percentage:.2f}%)\n"
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


_COMBAT_UNIT_HEADER_RE = re.compile(
    r"^combat_unit_type_(\w+)\s*=\s*\{", re.MULTILINE
)
_UPKEEP_BLOCK_RE = re.compile(
    r"upkeep_modifier\s*=\s*\{(.*?)\}", re.DOTALL
)
_GOOD_INPUT_LINE_RE = re.compile(
    r"goods_input_(\w+)_add\s*=\s*(-?[\d\.]+)"
)


def _iter_combat_unit_bodies(text):
    """Yield (unit_name, body_text) for non-INJECT combat_unit_type entries.

    Bodies are sliced from the matched header to the next top-level header
    (or end-of-file). INJECT entries are skipped because the mod's loc file
    only carries _desc strings for newly-introduced types.
    """
    headers = []
    inject_re = re.compile(
        r"^INJECT:combat_unit_type_\w+\s*=\s*\{", re.MULTILINE
    )
    for m in _COMBAT_UNIT_HEADER_RE.finditer(text):
        headers.append((m.start(), m.end(), m.group(1)))
    inject_starts = {m.start() for m in inject_re.finditer(text)}
    boundaries = sorted([h[0] for h in headers] + list(inject_starts) + [len(text)])
    for start, end, name in headers:
        if start in inject_starts:
            continue
        next_boundary = next((b for b in boundaries if b > start), len(text))
        yield name, text[end:next_boundary]


def compute_combat_unit_breakdown(file_path, goods_dict):
    """Return {unit_name: [(good, quantity, base_price), ...]} for non-INJECT
    combat_unit_type entries in the given file. Quantities cast to int."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    out = {}
    for name, body in _iter_combat_unit_bodies(text):
        upkeep = _UPKEEP_BLOCK_RE.search(body)
        if not upkeep:
            continue
        rows = []
        for good, qty in _GOOD_INPUT_LINE_RE.findall(upkeep.group(1)):
            rows.append((good, int(float(qty)), int(goods_dict.get(good, 0))))
        if rows:
            out[name] = rows
    return out


def _build_market_cost_line(unit_name):
    return (
        f"\\nCost at current "
        f"[Concept('concept_market_price', 'market prices')]: #N @money!"
        f"[GetPlayer.MakeScope.ScriptValue('value_combat_unit_market_cost_{unit_name}')|0]"
        f" #!"
    )


# Match the cost-base anchor plus zero or more cost-current entries (the
# `*` quantifier sweeps duplicates that earlier idempotency regressions
# may have left behind). The cost-current label may be either the legacy
# untagged "market prices" or the current `[Concept('concept_market_price',
# 'market prices')]` tag — both are accepted on read; output is always
# the tagged form.
_DESC_SUFFIX_RE = re.compile(
    r"(Cost at base prices: #N @money!)(\d+)"
    r"( #!)"
    r"(?:\\nCost at current "
    r"(?:market prices|"
    r"\[Concept\('concept_market_price', 'market prices'\)\]"
    r"): "
    r"#N @money!"
    r"\[GetPlayer\.MakeScope\.ScriptValue\("
    r"'value_combat_unit_market_cost_\w+'\)\|0\] #!)*"
)


def update_combat_unit_loc(loc_path, breakdown):
    """Rewrite te_combat_units_l_english.yml in place: for each non-INJECT
    combat unit, replace the base-price integer in its _desc and ensure the
    market-price SV line follows. Returns a list of warning strings."""
    with open(loc_path, "r", encoding="utf-8-sig") as f:
        original = f.read()

    warnings = []
    updated = original
    keys_seen = set()

    for unit_name, rows in breakdown.items():
        base_total = sum(qty * price for _good, qty, price in rows)
        key_re = re.compile(
            r"^(\s*combat_unit_type_"
            + re.escape(unit_name)
            + r"_desc:\d+\s+\".*?)\"$",
            re.MULTILINE,
        )
        m = key_re.search(updated)
        if not m:
            warnings.append(
                f"[combat_unit_loc] {unit_name}: no _desc key — skipping"
            )
            continue
        keys_seen.add(unit_name)
        body = m.group(1)
        if "Cost at base prices: #N @money!" not in body:
            warnings.append(
                f"[combat_unit_loc] {unit_name}: _desc lacks "
                f"'Cost at base prices:' suffix — skipping (paste the "
                f"suffix once and updates will start flowing)"
            )
            continue

        market_line = _build_market_cost_line(unit_name)

        def _replace(match, _ml=market_line, _bt=base_total):
            return f"{match.group(1)}{_bt}{match.group(3)}{_ml}"

        new_body = _DESC_SUFFIX_RE.sub(_replace, body, count=1)
        new_line = f'{new_body}"'
        if new_line != m.group(0):
            updated = updated[: m.start()] + new_line + updated[m.end():]

    if updated != original:
        with open(loc_path, "wb") as f:
            f.write("﻿".encode("utf-8"))
            f.write(updated.lstrip("﻿").encode("utf-8"))
    return warnings


def emit_combat_unit_market_cost_svs(out_path, breakdown):
    """Write common/script_values/auto_combat_unit_market_costs.txt — one SV
    per non-INJECT combat unit, computing total upkeep at current market
    prices via (1 + market.mg:<good>.market_goods_pricier) * <base_contrib>.
    Whole-file overwrite each run."""
    lines = [
        "# AUTO-GENERATED by pm_costs.py — do not edit manually.",
        "# One value_combat_unit_market_cost_<unit> SV per non-INJECT combat",
        "# unit type in extra_combat_units.txt. Each per-good `add = { ... }`",
        "# block scales the base contribution by (1 + market_goods_pricier).",
        "",
    ]
    for unit_name in sorted(breakdown):
        rows = breakdown[unit_name]
        if not rows:
            continue
        lines.append(f"value_combat_unit_market_cost_{unit_name} = {{")
        for good, qty, price in rows:
            base_contrib = qty * price
            lines.append("\tadd = {")
            lines.append(
                f"\t\tvalue = this.market.mg:{good}.market_goods_pricier"
            )
            lines.append("\t\tadd = 1")
            lines.append(
                f"\t\tmultiply = {base_contrib} # base_price({price}) × quantity({qty})"
            )
            lines.append("\t}")
        lines.append("}")
        lines.append("")
    content = "\n".join(lines).rstrip() + "\n"
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write(content)


def _run(dry_run: bool, verbose: bool, mod_state=None, vanilla_files: bool = True):
    """Annotate the mod's PM and military files and regenerate what derives
    from them. `vanilla_files=False` forbids reading the game files, which
    leaves the two commented-vanilla reference files alone; so does a machine
    with no game files."""
    # Imported here rather than at module scope so the helpers above stay
    # importable (and unit-testable) without a Victoria 3 install configured.
    from path_constants import mod_path

    game_dir = _vanilla_game_dir() if vanilla_files else None
    vanilla_pms_file_loc = os.path.join(game_dir, "common", "production_methods") if game_dir else None
    vanilla_units_loc = os.path.join(game_dir, "common", "combat_unit_types") if game_dir else None
    vanilla_pm_file_paths = (
        [os.path.join(vanilla_pms_file_loc, f)
         for f in sorted(os.listdir(vanilla_pms_file_loc)) if f.endswith(".txt")]
        if vanilla_pms_file_loc and os.path.isdir(vanilla_pms_file_loc) else []
    )
    vanilla_military_unit_file_path = [
        os.path.join(vanilla_units_loc, name)
        for name in ("00_land_combat_unit_types.txt", "01_navy_combat_unit_types.txt")
    ] if vanilla_units_loc else []
    vanilla_docs = bool(vanilla_pm_file_paths) and all(
        os.path.isfile(path) for path in vanilla_military_unit_file_path
    )
    if verbose and not vanilla_docs:
        print(
            "No vanilla game files: leaving docs/engine/commented_vanilla_pms.txt and "
            "commented_vanilla_military_units.txt as they are."
        )

    pms_file_paths = [
        os.path.join(mod_path, "common", "production_methods", "extra_pms.txt"),
        os.path.join(mod_path, "common", "production_methods", "unique_pms.txt"),
    ]
    output_file_path = os.path.join(mod_path, "docs", "engine", "commented_vanilla_pms.txt")
    goods_dict = load_goods(mod_state)

    if dry_run:
        if verbose:
            print("[dry-run] Would annotate mod PM files:")
            for fp in pms_file_paths:
                print(f"  {fp}")
            if vanilla_docs:
                print(f"[dry-run] Would write commented vanilla PMs to: {output_file_path}")
    else:
        for file_path in pms_file_paths:
            process_and_update_production_methods_grouped(
                file_path, goods_dict, calculate_costs, calculate_employment
            )
        if vanilla_docs:
            process_and_update_production_methods_grouped(
                vanilla_pm_file_paths,
                goods_dict,
                calculate_costs,
                calculate_employment,
                output_file_path,
            )
        if verbose:
            print("Production methods file updated successfully.")

    military_unit_file_path = os.path.join(mod_path, "common", "combat_unit_types", "extra_combat_units.txt")
    mobilization_file_path = os.path.join(mod_path, "common", "mobilization_options", "extra_mobilization_options.txt")
    mil_output_path = os.path.join(mod_path, "docs", "engine", "commented_vanilla_military_units.txt")

    sv_output_path = os.path.join(
        mod_path, "common", "script_values", "auto_combat_unit_market_costs.txt"
    )
    loc_output_path = os.path.join(
        mod_path, "localization", "english", "te_combat_units_l_english.yml"
    )

    if dry_run:
        if verbose:
            print("[dry-run] Would annotate military files:")
            print(f"  {military_unit_file_path}")
            print(f"  {mobilization_file_path}")
            if vanilla_docs:
                print(f"[dry-run] Would write commented vanilla military units to: {mil_output_path}")
            breakdown = compute_combat_unit_breakdown(military_unit_file_path, goods_dict)
            print(
                f"[dry-run] Would emit {len(breakdown)} SVs to: {sv_output_path}"
            )
            print(
                f"[dry-run] Would update base-price + market-price lines in: {loc_output_path}"
            )
            for unit, rows in sorted(breakdown.items()):
                base_total = sum(qty * price for _g, qty, price in rows)
                print(f"  {unit}: base_total={base_total}")
    else:
        process_and_update_military_costs(military_unit_file_path, goods_dict)
        process_and_update_military_costs(mobilization_file_path, goods_dict)
        if vanilla_docs:
            process_and_update_military_costs(
                vanilla_military_unit_file_path,
                goods_dict,
                write_path=mil_output_path,
            )
        breakdown = compute_combat_unit_breakdown(military_unit_file_path, goods_dict)
        emit_combat_unit_market_cost_svs(sv_output_path, breakdown)
        warnings = update_combat_unit_loc(loc_output_path, breakdown)
        if verbose:
            print("Military costs file updated successfully.")
            print(
                f"Wrote {len(breakdown)} combat-unit market-cost SVs to {sv_output_path}"
            )
            for w in warnings:
                print(w)


def regenerate(mod_state=None, vanilla_files=True):
    """Auto-run entrypoint invoked by mod_state_server post-load.

    Prices come from `mod_state`'s vanilla, so the mod's files are annotated
    with or without the game files. The server passes `vanilla_files=False`
    when the files on disk are missing or older than the snapshot it loaded;
    the commented-vanilla reference docs, which are cut from those files, are
    then left as committed."""
    _run(dry_run=False, verbose=False, mod_state=mod_state, vanilla_files=vanilla_files)


def main():
    parser = argparse.ArgumentParser(description="Annotate PM files with cost/revenue comments")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing files")
    args = parser.parse_args()
    _run(dry_run=args.dry_run, verbose=True)


if __name__ == "__main__":
    main()
