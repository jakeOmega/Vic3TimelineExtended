"""Recipe-derived building emissions display, owned by gen_carbon_capture_pms.

Vanilla PMs take INJECTs; mod-owned and REPLACEd PMs must be amended in place.
Only the positive emissions line is generated in those handwritten recipes.
Negative capture contributions are owned by the capture-method generator.
The removal-only PM has its own capacity parameter, independent of goods output.
"""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re

from paradox_file_parser import ParadoxFileParser

BUILDINGS = ("building_power_plant", "building_steel_mill", "building_chemical_plant")
MODIFIER = "building_greenhouse_gas_emissions_add"
OUTPUT = Path("common/production_methods/greenhouse_gas_generated_injects.txt")
FACTORS = Path("common/script_values/greenhouse_gas_factors.txt")
REMOVALS = {"pm_direct_air_capture": ("coal", "gw_direct_air_capture_coal_equivalent")}
_DEFINITION = re.compile(r"(?m)^((?:INJECT:|REPLACE:|REPLACE_OR_CREATE:)?[\w-]+)\s*=\s*\{")
_LINE = re.compile(r"(?m)^([\t ]*)" + MODIFIER + r"\s*=\s*([\d.]+)[^\n]*\n")
_SIGNED_LINE = re.compile(r"(?m)^([\t ]*)" + MODIFIER + r"\s*=\s*(-?[\d.]+)[^\n]*\n")


def unwrap(value):
    return value[1] if isinstance(value, tuple) and len(value) == 2 else value


def load_state(root):
    from mod_state import ModState, VANILLA_COMMON_DIRS
    from vanilla_parsed import load

    kinds = ("Buildings", "PM Groups", "PMs")
    snapshot = load(str(root / "vanilla_parsed"))
    state = ModState(
        {kind: "/nonexistent" for kind in kinds},
        {kind: str(root / "common" / VANILLA_COMMON_DIRS[kind]) for kind in kinds},
        vanilla_data=snapshot.data,
    )
    if state.parse_failures:
        raise ValueError(f"Cannot derive emissions from an incomplete parse: {state.parse_failures}")
    return state


def recipe_emissions(method, factors, display_scale=Decimal(1000)):
    building = unwrap(unwrap(method).get("building_modifiers", {}))
    workforce = unwrap(building.get("workforce_scaled", {}))
    total = Decimal(0)
    for fuel, factor in factors.items():
        amount = Decimal(unwrap(workforce.get(f"goods_input_{fuel}_add", 0)))
        if not amount.is_finite() or amount < 0:
            raise ValueError(f"Invalid merged {fuel} input: {amount}")
        total += amount * factor
    return (total * display_scale / 10000).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _mask(text):
    return re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"|#[^\n]*',
                  lambda match: " " * len(match[0]), text)


def _end(text, opening):
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("Unbalanced production method")


def _with_emission(block, amount, *, removal=False):
    matches = list((_SIGNED_LINE if removal else _LINE).finditer(block))
    label = "carbon removal" if removal else "fuel emissions"
    if len(matches) > 1:
        raise ValueError("Duplicate generated emissions lines")
    if matches:
        match = matches[0]
        if amount and Decimal(match[2]) == amount:
            return block
        line = (f"{match[1]}{MODIFIER} = {amount:.2f} # AUTO-GENERATED: {label}\n"
                if amount else "")
        return block[:match.start()] + line + block[match.end():]
    if not amount:
        return block
    masked = _mask(block)
    building = re.search(r"\bbuilding_modifiers\s*=\s*\{", masked)
    if building is None:
        raise ValueError("Fuel recipe has no building_modifiers block")
    closing = _end(masked, building.end() - 1)
    workforce = re.search(r"\bworkforce_scaled\s*=\s*\{", masked[building.end():closing])
    if workforce is None:
        raise ValueError("Fuel recipe has no workforce_scaled block")
    index = building.end() + workforce.end()
    return (block[:index] + f"\n\t\t\t{MODIFIER} = {amount:.2f}"
            f" # AUTO-GENERATED: {label}" + block[index:])


def plan_outputs(state, root):
    parser = ParadoxFileParser()
    parser.parse_file(str(root / FACTORS))
    factors = {fuel: Decimal(unwrap(parser.data[f"gw_emission_factor_{fuel}"]))
               for fuel in ("coal", "oil")}
    if any(not factor.is_finite() or factor < 0 for factor in factors.values()):
        raise ValueError("Emission factors must be finite and nonnegative")
    display_scale = Decimal(unwrap(parser.data["gw_emission_display_scale"]))
    if not display_scale.is_finite() or display_scale <= 0:
        raise ValueError("Emissions display scale must be finite and positive")
    methods = state.mod_parsers["PMs"].data
    groups = state.mod_parsers["PM Groups"].data
    buildings = state.mod_parsers["Buildings"].data
    covered = set()
    for name in BUILDINGS:
        for group in unwrap(unwrap(buildings[name])["production_method_groups"]):
            covered.update(unwrap(unwrap(groups[group])["production_methods"]))
    amounts = {name: recipe_emissions(methods[name], factors, display_scale) for name in covered}
    fuel_methods = sum(bool(amount) for amount in amounts.values())
    for name, (fuel, parameter) in REMOVALS.items():
        if name not in methods:
            raise ValueError(f"Missing removal method: {name}")
        capacity = Decimal(unwrap(parser.data[parameter]))
        if not capacity.is_finite() or capacity <= 0:
            raise ValueError(f"Invalid carbon removal capacity: {capacity}")
        amounts[name] = (-capacity * factors[fuel] * display_scale / 10000).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
    outputs, owned = {}, set()
    for path in sorted((root / "common/production_methods").rglob("*.txt")):
        if path == root / OUTPUT:
            continue
        original = path.read_text(encoding="utf-8-sig")
        masked = _mask(original)
        edits = []
        for match in _DEFINITION.finditer(masked):
            directive, name = parser._split_directive(match[1])
            if directive == "INJECT":
                continue
            if name in owned:
                raise ValueError(f"Duplicate owned production method: {name}")
            owned.add(name)
            end = _end(masked, match.end() - 1)
            block = original[match.start():end]
            replacement = _with_emission(block, amounts.get(name, Decimal(0)), removal=name in REMOVALS)
            if replacement != block:
                edits.append((match.start(), end, replacement))
        result = original
        for start, end, replacement in reversed(edits):
            result = result[:start] + replacement + result[end:]
        if result != original:
            outputs[path.relative_to(root)] = result
    if missing := REMOVALS.keys() - owned:
        raise ValueError(f"Removal methods must have owned definitions: {sorted(missing)}")
    lines = ["# AUTO-GENERATED by gen_carbon_capture_pms.py; do not edit.",
             "# Workforce-scaled fuel emissions, in display units, for covered vanilla PMs.",
             "# Mod-owned and REPLACEd recipes carry the same generated field in place.", ""]
    for name, amount in sorted(amounts.items()):
        if not amount or name in owned:
            continue
        if name not in state.base_parsers["PMs"].data:
            raise ValueError(f"Cannot INJECT into a non-vanilla method: {name}")
        lines.extend([f"INJECT:{name} = {{", "\tbuilding_modifiers = {",
                      "\t\tworkforce_scaled = {", f"\t\t\t{MODIFIER} = {amount:.2f}",
                      "\t\t}", "\t}", "}", ""])
    outputs[OUTPUT] = "\n".join(lines)
    return outputs, fuel_methods
