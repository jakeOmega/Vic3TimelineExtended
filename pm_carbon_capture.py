"""Generate source-capture controls from the merged building/PM graph.

One capture group per source group avoids a Cartesian product when a building
burns fuel in both its main process and automation. Exempt sources still get
the emissions display; this module only decides which sources can be captured.
"""

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re

import pm_emissions as emissions

u = emissions.unwrap
METHODS = Path("common/production_methods/carbon_capture_generated_pms.txt")
GROUPS = Path("common/production_method_groups/carbon_capture_generated_groups.txt")
BUILDINGS = Path("common/buildings/carbon_capture_generated_injects.txt")
LOC = Path("localization/english/te_production_methods_l_english.yml")
REPORT = Path("docs/systems/carbon_capture_coverage.md")
PREFIX = "pmg_carbon_capture_"
MANDATE = "law_managed_fossil_phaseout"
TIERS = ((1, Decimal("0.25"), "Partial Carbon Capture", "clean_energy_technologies"),
         (2, Decimal("0.50"), "Carbon Capture and Storage", "carbon_capture_and_storage"),
         (3, Decimal("0.75"), "Advanced Carbon Capture", "modern_material_science"))
# Existing shield icons distinguish the three tiers without adding new assets.
ICONS = ("cat_shield_green_p1", "cat_shield_green_p2", "cat_shield_gold_p3")
EXCLUDED_BUILDINGS = {
    **dict.fromkeys(("building_airport", "building_highway", "building_port", "building_railway",
                    "building_fishing_wharf", "building_whaling_station", "building_logging_camp",
                    "building_suez_canal", "building_panama_canal", "building_kiel_canal",
                    "building_generic_rail_nexus", "building_white_star_albion_house"),
                   "Transport or dispersed mobile machinery; no stationary capture stack."),
    **dict.fromkeys(("building_maize_farm", "building_millet_farm", "building_rice_farm",
                    "building_rye_farm", "building_wheat_farm", "building_livestock_ranch"),
                   "Dispersed agricultural machinery."),
    "building_urban_center": "Coal consumed by dispersed street lighting.",
    "building_synthetics_plant_oil": "Synthetic-fuel carbon is already credited; stack capture would double count it.",
    **dict.fromkeys(("building_anglo_persian_abadan_refinery", "building_bp_refinery_complex",
                    "building_caribbean_petroleum_maracaibo_depot", "building_el_aguila_tampico_refinery",
                    "building_galician_boryslaw_oil_field", "building_generic_tank_farm",
                    "building_nederlandse_petroleum_pangkalan_depot", "building_nioc_masjed_soleyman_field",
                    "building_nobel_baku_refinery", "building_reliance_jamnagar_refinery",
                    "building_romanian_star_ploiesti_refinery", "building_standard_oil_refinery",
                    "building_steel_brothers_syriam_depot", "building_turkish_petroleum_kirkuk_depot",
                    "building_west_ural_oil_depot"),
                   "Oil is refinery/feedstock or storage inventory, not a capturable combustion stream."),
}
EXCLUDED_GROUPS = dict.fromkeys(("pmg_synthetic_dyes", "pmg_synthetic_rubber", "pmg_synthetic_silk",
                               "pmg_ig_farben_buna_werke", "pmg_jsr_yokkaichi_complex",
                               "pmg_sibur_tobolsk_complex", "pmg_generic_dye_fiber_park"),
                              "Oil/coal used as chemical feedstock rather than burnt fuel.")
EXCLUDED_METHODS = dict.fromkeys(("pm_houseware_plastics", "pm_injection_molding", "pm_blow_molding",
                                "pm_massed_produced_plastics"),
                               "Oil used as plastics feedstock.")
CONCENTRATED_GROUPS = {"pmg_fertilizer_production", "pmg_explosives_building_chemical_plant"}


def workforce(pm):
    return u(u(u(pm).get("building_modifiers", {})).get("workforce_scaled", {}))


def fuel_recipe(pm, name=None):
    """(coal, oil) burned per level: the recipe's inputs plus fuel netted from its output.

    A method exempt from emissions (`emissions.EXEMPT_METHODS`) burns nothing.
    """
    if name in emissions.EXEMPT_METHODS:
        return Decimal(0), Decimal(0)
    w = workforce(pm)
    netted = emissions.netted_fuel(name, pm)
    return tuple(Decimal(u(w.get(f"goods_input_{f}_add", 0))) + netted.get(f, 0) for f in ("coal", "oil"))


def exemption(building, group, method, recipe):
    if building in EXCLUDED_BUILDINGS:
        return EXCLUDED_BUILDINGS[building]
    if group in EXCLUDED_GROUPS:
        return EXCLUDED_GROUPS[group]
    if method in EXCLUDED_METHODS:
        return EXCLUDED_METHODS[method]
    if group.startswith("pmg_steam_automation_building_") and recipe[1]:
        return "Oil used by mobile excavators/earth movers. Coal-fired steam automation remains eligible."
    return ""


def rounded(value):
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def quantity(value):
    """Keep tiny operating costs instead of rounding small emitters to free."""
    whole = rounded(value)
    return whole if whole else value.quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)


def operating_costs(recipe, fraction, concentrated=False, power=False):
    # Design §5.5: electricity £30/MWh, £1 ~= $2.17, coal/oil 3.07/2.64 t.
    # Real-anchor assumptions are balance parameters, not physical game units.
    tier = {Decimal("0.25"): 0, Decimal("0.50"): 1, Decimal("0.75"): 2}[fraction]
    tonnes = (recipe[0] * Decimal("3.07") + recipe[1] * Decimal("2.64")) * fraction
    rate = (Decimal("35"), Decimal("25"), Decimal("20")) if concentrated else (
        Decimal("90"), Decimal("65"), Decimal("45"))
    energy = (Decimal("0.12"), Decimal("0.12"), Decimal("0.10")) if concentrated else (
        Decimal("0.35"), Decimal("0.30"), Decimal("0.22"))
    electricity = tonnes * energy[tier]
    goods = tonnes * rate[tier] / Decimal("2.17") - electricity * 30
    mix = {"engines": (Decimal("0.60"), 60), "steel": (Decimal("0.40"), 50)} if concentrated else {
        "engines": (Decimal("0.40"), 60), "steel": (Decimal("0.35"), 50),
        "fertilizer": (Decimal("0.25"), 30)}
    result = {f"goods_input_{good}_add": quantity(goods * share / price)
              for good, (share, price) in mix.items()}
    result["goods_output_electricity_add" if power else "goods_input_electricity_add"] = (
        -1 if power else 1) * quantity(electricity)
    return {key: value for key, value in result.items() if value}


def capture_catalog(state):
    """Return groups with eligible classes, building attachments and exceptions."""
    methods = state.mod_parsers["PMs"].data
    groups = state.mod_parsers["PM Groups"].data
    attachments, catalog, exceptions = defaultdict(list), {}, []
    for building, data in sorted(state.mod_parsers["Buildings"].data.items()):
        for group in u(u(data).get("production_method_groups", [])):
            if group.startswith(PREFIX):
                continue
            classes, exempt = defaultdict(list), []
            pms = u(u(groups[group])["production_methods"])
            for pm in pms:
                recipe = fuel_recipe(methods[pm], pm)
                reason = exemption(building, group, pm, recipe)
                if any(recipe) and reason:
                    exceptions.append((building, group, pm, reason))
                if not any(recipe) or reason:
                    exempt.append(pm)
                else:
                    classes[recipe].append(pm)
            if not classes:
                continue
            # Shared source groups have the same costs and control in every
            # attached building. Per-building exclusions skip their attachment.
            power = all(Decimal(u(workforce(methods[pm]).get("goods_output_electricity_add", 0))) > 0
                        for names in classes.values() for pm in names)
            entry = (dict(classes), exempt, group in CONCENTRATED_GROUPS, power)
            if group in catalog and entry != catalog[group]:
                raise ValueError(f"Inconsistent shared capture group {group}")
            catalog[group] = entry
            attachments[building].append(PREFIX + group.removeprefix("pmg_"))
    return catalog, dict(attachments), exceptions


def _with_groups(block, desired):
    masked = emissions._mask(block)
    match = re.search(r"\bproduction_method_groups\s*=\s*\{", masked)
    if match is None:
        raise ValueError("Covered building has no production_method_groups")
    end = emissions._end(masked, match.end() - 1)
    inner = block[match.end():end - 1]
    inner = re.sub(r"(?m)^[\t ]*" + PREFIX + r"[\w-]+[\t ]*\n", "", inner)
    inner = inner.rstrip() + "\n" + "".join(f"\t\t{g}\n" for g in desired) + "\t"
    return block[:match.end()] + inner + block[end - 1:]


def plan_outputs(state, root):
    catalog, attachments, exceptions = capture_catalog(state)
    parser = emissions.ParadoxFileParser()
    parser.parse_file(str(root / emissions.FACTORS))
    factors = {fuel: Decimal(u(parser.data[f"gw_emission_factor_{fuel}"])) for fuel in ("coal", "oil")}
    scale = Decimal(u(parser.data["gw_emission_display_scale"]))
    for value in (*factors.values(), scale):
        if not value.is_finite() or value <= 0:
            raise ValueError("Capture factors and display scale must be finite and positive")
    header = ["# AUTO-GENERATED by gen_carbon_capture_pms.py; do not edit.", ""]
    methods, groups, loc = header.copy(), header.copy(), ["l_english:"]
    count = 0
    for source, (classes, exempt, concentrated, power) in sorted(catalog.items()):
        token = source.removeprefix("pmg_")
        group = PREFIX + token
        none = "pm_no_carbon_capture_" + token
        names = [none]
        label = "$" + source + "$"
        if source.startswith("pmg_base_") or source == "pmg_explosives_building_chemical_plant":
            attached = sorted(b for b, gs in attachments.items() if group in gs)
            if attached:
                label = "$" + attached[0] + "$"
        loc.append(f' {group}:0 "Carbon Capture ({label})"')
        loc.append(f' {none}:0 "No Carbon Capture"')
        methods.extend([f"{none} = {{", '\ttexture = "gfx/interface/icons/production_method_icons/cat_shield_gold_p0.dds"',
                        f"\tdisallowing_laws = {{ {MANDATE} }}", "}", ""])
        if exempt:
            na = "pm_carbon_capture_na_" + token
            names.append(na)
            loc.extend([f' {na}:0 "Capture Not Applicable"',
                        f' {na}_desc:0 "This production method has no eligible stationary fuel emissions to capture."'])
            methods.extend([f"{na} = {{", '\ttexture = "gfx/interface/icons/production_method_icons/cat_shield_gold_p0.dds"',
                            "\tis_hidden_when_unavailable = yes",
                            "\tunlocking_production_methods = { " + " ".join(exempt) + " }", "}", ""])
        for (coal, oil), pms in sorted(classes.items()):
            code = "coal" + str(coal).replace(".", "p") + "_oil" + str(oil).replace(".", "p")
            fuel_text = ", ".join(f"{v:g} {f}" for f, v in (("Coal", coal), ("Oil", oil)) if v)
            for tier, fraction, title, tech in TIERS:
                name = f"pm_carbon_capture_{tier}_{token}_{code}"
                names.append(name)
                count += 1
                # Match the displayed gross rounding, ensuring capture never
                # exceeds that group's visible fuel contribution.
                gross = ((coal * factors["coal"] + oil * factors["oil"]) * scale / 10000).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP)
                precision = Decimal("0.00001") if gross < 1 else Decimal("0.01")
                cut = (gross * fraction).quantize(precision, rounding=ROUND_HALF_UP)
                cut_text = f"{cut:.5f}" if gross < 1 else f"{cut:.2f}"
                methods.extend([f"{name} = {{", f'\ttexture = "gfx/interface/icons/production_method_icons/{ICONS[tier-1]}.dds"',
                                "\tis_hidden_when_unavailable = yes", f"\tunlocking_technologies = {{ {tech} }}",
                                "\tunlocking_production_methods = { " + " ".join(pms) + " }"])
                if tier == 1:
                    methods.append(f"\tdisallowing_laws = {{ {MANDATE} }}")
                methods.extend(["\tstate_modifiers = {", "\t\tworkforce_scaled = {",
                                f"\t\t\t{emissions.STATE_MODIFIER} = -{cut_text}", "\t\t}", "\t}",
                                "\tbuilding_modifiers = {", "\t\tworkforce_scaled = {"])
                for key, value in operating_costs((coal, oil), fraction, concentrated, power).items():
                    methods.append(f"\t\t\t{key} = {value}")
                methods.extend(["\t\t}", "\t}", "}", ""])
                loc.extend([f' {name}:0 "{title} ({fuel_text})"',
                            f' {name}_desc:0 "Captures {fraction * 100:g}% of this production group\'s fuel emissions. Staffing and throughput scale removal and operating costs."'])
        groups.extend([f"{group} = {{", '\ttexture = "gfx/interface/icons/production_method_icons/cat_shield_green_p2.dds"',
                       "\tproduction_methods = {", *(f"\t\t{name}" for name in names), "\t}", "}", ""])
    outputs, owned = {}, set()
    for path in sorted((root / "common/buildings").glob("*.txt")):
        if path == root / BUILDINGS:
            continue
        original = path.read_text(encoding="utf-8-sig")
        masked = emissions._mask(original)
        edits = []
        for match in emissions._DEFINITION.finditer(masked):
            directive, name = parser._split_directive(match[1])
            if directive == "INJECT":
                continue
            owned.add(name)
            end = emissions._end(masked, match.end() - 1)
            block = original[match.start():end]
            if name not in attachments and PREFIX not in block:
                continue
            replacement = _with_groups(block, attachments.get(name, []))
            if block != replacement:
                edits.append((match.start(), end, replacement))
        result = original
        for start, end, replacement in reversed(edits):
            result = result[:start] + replacement + result[end:]
        if result != original:
            outputs[path.relative_to(root)] = result
    injects = header.copy()
    for building, added in sorted(attachments.items()):
        if building in owned:
            continue
        if building not in state.base_parsers["Buildings"].data:
            raise ValueError(f"Cannot INJECT into mod-only building {building}")
        injects.extend([f"INJECT:{building} = {{", "\tproduction_method_groups = {",
                        *(f"\t\t{group}" for group in added), "\t}", "}", ""])
    existing = (root / LOC).read_text(encoding="utf-8-sig").splitlines() if (root / LOC).exists() else []
    generated_prefixes = ("pm_carbon_capture_", "pm_no_carbon_capture_", PREFIX)
    retained = [line for line in existing if re.match(r"\s+[\w-]+:(?:\d+)?\s", line)
                and not line.lstrip().startswith(generated_prefixes)]
    notes = [line for line in existing if line.strip() and line.strip() not in ("l_english:", "#", "# PRODUCTION_METHODS")
             and not re.match(r"\s+[\w-]+:(?:\d+)?\s", line)]
    outputs.update({METHODS: "\n".join(methods), GROUPS: "\n".join(groups),
                    BUILDINGS: "\n".join(injects),
                    LOC: "l_english:\n\n#\n# PRODUCTION_METHODS\n#\n" +
                    "\n".join(notes + sorted(retained + loc[1:])) + "\n"})
    report = ["# Source-capture coverage", "", "Generated by `gen_carbon_capture_pms.py`; do not edit.", "",
              f"{len(attachments)} building types; {len(catalog)} source groups; {count} tier variants.", "",
              "Every coal/oil-consuming building PM shows emissions, including exemptions below, "
              "except the methods in `pm_emissions.EXEMPT_METHODS`, whose goods flow is not burnt fuel: "
              + ", ".join(f"`{name}`" for name in sorted(emissions.EXEMPT_METHODS)) + ".",
              "Market industry uses recipe-derived emissions; exempt feedstocks still contribute emissions but have no capture control.",
              "Each eligible source group has its own capture control; process and automation are independent.",
              "Chemical Plants and Explosives Factories use concentrated-stream costs; other sources use flue-gas costs.",
              "Electricity producers pay energy costs as reduced output; other sources buy electricity.", "",
              "## Included", "", "| Building | Source groups |", "|---|---|"]
    report.extend(f"| `{b}` | " + ", ".join(f"`{g.removeprefix(PREFIX)}`" for g in gs) + " |"
                  for b, gs in sorted(attachments.items()))
    report.extend(["", "## Deliberate exceptions", "", "| Building | Method | Reason |", "|---|---|---|"])
    report.extend(f"| `{b}` | `{m}` | {reason} |" for b, _, m, reason in exceptions)
    outputs[REPORT] = "\n".join(report) + "\n"
    return outputs, {"capture_buildings": len(attachments), "capture_groups": len(catalog), "capture_variants": count}
