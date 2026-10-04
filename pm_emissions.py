"""Recipe-derived building emissions display, owned by gen_carbon_capture_pms.

Vanilla PMs take INJECTs; mod-owned and REPLACEd PMs must be amended in place.
Fuel contributions, synthetic net emissions and synthetic/removal state credits
are generated in those handwritten recipes. Source-capture contributions are
owned by the capture-method generator. The removal-only PM has its own capacity
parameter, independent of goods output.
"""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re

from paradox_file_parser import ParadoxFileParser

MODIFIER = "building_greenhouse_gas_emissions_add"
STATE_MODIFIER = "state_greenhouse_gas_emissions_add"
ATMOSPHERIC_MODIFIER = "state_atmospheric_carbon_capture_add"
OUTPUT = Path("common/production_methods/greenhouse_gas_generated_injects.txt")
FACTORS = Path("common/script_values/greenhouse_gas_factors.txt")
REMOVALS = {"pm_direct_air_capture": ("coal", "gw_direct_air_capture_coal_equivalent")}
SYNTHETIC_CREDITS = {"pm_synthetic_oil_1": "oil", "pm_synthetic_oil_2": "oil", "pm_synthetic_coal": "coal"}
_DEFINITION = re.compile(r"(?m)^((?:INJECT:|REPLACE:|REPLACE_OR_CREATE:)?[\w-]+)\s*=\s*\{")
_LINE = re.compile(r"(?m)^([\t ]*)" + MODIFIER + r"\s*=\s*([\d.]+)[^\n]*\n")
_SIGNED_LINE = re.compile(r"(?m)^([\t ]*)" + MODIFIER + r"\s*=\s*(-?[\d.]+)[^\n]*\n")


def unwrap(value):
    return value[1] if isinstance(value, tuple) and len(value) == 2 else value


def load_state(root):
    from mod_state import ModState, VANILLA_COMMON_DIRS
    from vanilla_parsed import load

    kinds = ("Buildings", "PM Groups", "PMs", "Buy Packages", "Goods", "Pop Needs", "Pop Types")
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


def _with_emission(block, amount, *, removal=False, label=None):
    matches = list((_SIGNED_LINE if removal else _LINE).finditer(block))
    label = label or ("carbon removal" if removal else "fuel emissions")
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


def _with_state_modifier(block, amount, *, modifier, label="state accounting"):
    pattern = re.compile(r"(?m)^([\t ]*)" + modifier + r"\s*=\s*(-?[\d.]+)[^\n]*\n")
    matches = list(pattern.finditer(block))
    if len(matches) > 1:
        raise ValueError("Duplicate generated state credits")
    if matches:
        match = matches[0]
        if Decimal(match[2]) == amount:
            return block
        line = f"{match[1]}{modifier} = {amount:.2f} # AUTO-GENERATED: {label}\n" if amount else ""
        return block[:match.start()] + line + block[match.end():]
    if not amount:
        return block
    masked = _mask(block)
    state = re.search(r"\bstate_modifiers\s*=\s*\{", masked)
    if state:
        end = _end(masked, state.end() - 1)
        workforce = re.search(r"\bworkforce_scaled\s*=\s*\{", masked[state.end():end])
        if workforce is None:
            index = end - 1
            return (block[:index] + "\tworkforce_scaled = {\n"
                    f"\t\t\t{modifier} = {amount:.2f} # AUTO-GENERATED: {label}\n\t\t}}\n\t" + block[index:])
        index = state.end() + workforce.end()
        return (block[:index] + f"\n\t\t\t{modifier} = {amount:.2f}"
                f" # AUTO-GENERATED: {label}" + block[index:])
    index = block.index("{") + 1
    return (block[:index] + "\n\tstate_modifiers = {\n\t\tworkforce_scaled = {\n"
            f"\t\t\t{modifier} = {amount:.2f} # AUTO-GENERATED: {label}\n"
            "\t\t}\n\t}\n" + block[index:])


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
    for building in buildings.values():
        for group in unwrap(unwrap(building).get("production_method_groups", [])):
            covered.update(unwrap(unwrap(groups[group])["production_methods"]))
    amounts = {name: recipe_emissions(methods[name], factors, display_scale) for name in covered}
    gross_amounts = amounts.copy()
    fuel_methods = sum(bool(amount) for amount in amounts.values())
    credits = {}
    for name, fuel in SYNTHETIC_CREDITS.items():
        workforce = unwrap(unwrap(unwrap(methods[name])["building_modifiers"])["workforce_scaled"])
        output = Decimal(unwrap(workforce[f"goods_output_{fuel}_add"]))
        if not output.is_finite() or output <= 0:
            raise ValueError(f"Invalid synthetic {fuel} output: {output}")
        credits[name] = (output * factors[fuel] * display_scale / 10000).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        amounts[name] = recipe_emissions(methods[name], factors, display_scale) - credits[name]
    for name, (fuel, parameter) in REMOVALS.items():
        if name not in methods:
            raise ValueError(f"Missing removal method: {name}")
        capacity = Decimal(unwrap(parser.data[parameter]))
        if not capacity.is_finite() or capacity <= 0:
            raise ValueError(f"Invalid carbon removal capacity: {capacity}")
        amounts[name] = (-capacity * factors[fuel] * display_scale / 10000).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP)
        credits[name] = -amounts[name]
    outputs, owned = {}, set()
    for path in sorted((root / "common/production_methods").rglob("*.txt")):
        if path == root / OUTPUT or path.name == "carbon_capture_generated_pms.txt":
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
            replacement = _with_emission(block, amounts.get(name, Decimal(0)), removal=name in credits,
                                         label="net synthetic emissions" if name in SYNTHETIC_CREDITS else None)
            industrial = amounts[name] if name in SYNTHETIC_CREDITS else gross_amounts.get(name, Decimal(0))
            replacement = _with_state_modifier(replacement, industrial,
                                             modifier=STATE_MODIFIER, label="industrial emissions")
            # Remove the obsolete display-only credit from previously generated recipes.
            replacement = _with_state_modifier(replacement, Decimal(0), modifier="state_carbon_capture_add")
            if name in credits:
                atmospheric = credits[name] if name in REMOVALS else Decimal(0)
                replacement = _with_state_modifier(replacement, atmospheric, modifier=ATMOSPHERIC_MODIFIER,
                                                 label="atmospheric removal")
            if replacement != block:
                edits.append((match.start(), end, replacement))
        result = original
        for start, end, replacement in reversed(edits):
            result = result[:start] + replacement + result[end:]
        if result != original:
            outputs[path.relative_to(root)] = result
    if missing := credits.keys() - owned:
        raise ValueError(f"Removal methods must have owned definitions: {sorted(missing)}")
    lines = ["# AUTO-GENERATED by gen_carbon_capture_pms.py; do not edit.",
             "# Workforce-scaled fuel emissions, in display units, for covered vanilla PMs.",
             "# Mod-owned and REPLACEd recipes carry the same generated field in place.", ""]
    for name, amount in sorted(amounts.items()):
        if not amount or name in owned:
            continue
        if name not in state.base_parsers["PMs"].data:
            raise ValueError(f"Cannot INJECT into a non-vanilla method: {name}")
        lines.extend([f"INJECT:{name} = {{", "\tstate_modifiers = {", "\t\tworkforce_scaled = {",
                      f"\t\t\t{STATE_MODIFIER} = {amount:.2f}", "\t\t}", "\t}", "\tbuilding_modifiers = {",
                      "\t\tworkforce_scaled = {", f"\t\t\t{MODIFIER} = {amount:.2f}",
                      "\t\t}", "\t}", "}", ""])
    outputs[OUTPUT] = "\n".join(lines)
    return outputs, fuel_methods
