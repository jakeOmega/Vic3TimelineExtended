import os
from collections import defaultdict
from pathlib import Path

import tech_unlocks_lib
from mod_state import ModState
from path_constants import base_game_path, doc_path, mod_path

_BASE_COMMON = os.path.join(base_game_path, "game", "common")
_MOD_COMMON = os.path.join(mod_path, "common")

base_game_paths = {
    "Building Groups": os.path.join(_BASE_COMMON, "building_groups"),
    "Buildings": os.path.join(_BASE_COMMON, "buildings"),
    "Technologies": os.path.join(_BASE_COMMON, "technology", "technologies"),
    "PM Groups": os.path.join(_BASE_COMMON, "production_method_groups"),
    "PMs": os.path.join(_BASE_COMMON, "production_methods"),
    "Ideologies": os.path.join(_BASE_COMMON, "ideologies"),
    "Battle Conditions": os.path.join(_BASE_COMMON, "battle_conditions"),
    "Buy Packages": os.path.join(_BASE_COMMON, "buy_packages"),
    "Character Interactions": os.path.join(_BASE_COMMON, "character_interactions"),
    "Character Traits": os.path.join(_BASE_COMMON, "character_traits"),
    "Combat Unit Groups": os.path.join(_BASE_COMMON, "combat_unit_groups"),
    "Combat Unit Types": os.path.join(_BASE_COMMON, "combat_unit_types"),
    "Company Types": os.path.join(_BASE_COMMON, "company_types"),
    "Diplomatic Actions": os.path.join(_BASE_COMMON, "diplomatic_actions"),
    "Diplomatic Plays": os.path.join(_BASE_COMMON, "diplomatic_plays"),
    "Goods": os.path.join(_BASE_COMMON, "goods"),
    "Institutions": os.path.join(_BASE_COMMON, "institutions"),
    "Interest Groups": os.path.join(_BASE_COMMON, "interest_groups"),
    "Law Groups": os.path.join(_BASE_COMMON, "law_groups"),
    "Laws": os.path.join(_BASE_COMMON, "laws"),
    "Mobilization Option Groups": os.path.join(_BASE_COMMON, "mobilization_option_groups"),
    "Mobilization Options": os.path.join(_BASE_COMMON, "mobilization_options"),
    "Modifier Types": os.path.join(_BASE_COMMON, "modifier_type_definitions"),
    "Modifiers": os.path.join(_BASE_COMMON, "static_modifiers"),
    "Pop Needs": os.path.join(_BASE_COMMON, "pop_needs"),
    "Subject Types": os.path.join(_BASE_COMMON, "subject_types"),
}

mod_paths = {
    "Building Groups": os.path.join(_MOD_COMMON, "building_groups"),
    "Buildings": os.path.join(_MOD_COMMON, "buildings"),
    "Technologies": os.path.join(_MOD_COMMON, "technology", "technologies"),
    "PM Groups": os.path.join(_MOD_COMMON, "production_method_groups"),
    "PMs": os.path.join(_MOD_COMMON, "production_methods"),
    "Ideologies": os.path.join(_MOD_COMMON, "ideologies"),
    "Battle Conditions": os.path.join(_MOD_COMMON, "battle_conditions"),
    "Buy Packages": os.path.join(_MOD_COMMON, "buy_packages"),
    "Character Interactions": os.path.join(_MOD_COMMON, "character_interactions"),
    "Character Traits": os.path.join(_MOD_COMMON, "character_traits"),
    "Combat Unit Groups": os.path.join(_MOD_COMMON, "combat_unit_groups"),
    "Combat Unit Types": os.path.join(_MOD_COMMON, "combat_unit_types"),
    "Company Types": os.path.join(_MOD_COMMON, "company_types"),
    "Diplomatic Actions": os.path.join(_MOD_COMMON, "diplomatic_actions"),
    "Diplomatic Plays": os.path.join(_MOD_COMMON, "diplomatic_plays"),
    "Goods": os.path.join(_MOD_COMMON, "goods"),
    "Institutions": os.path.join(_MOD_COMMON, "institutions"),
    "Interest Groups": os.path.join(_MOD_COMMON, "interest_groups"),
    "Laws": os.path.join(_MOD_COMMON, "laws"),
    "Law Groups": os.path.join(_MOD_COMMON, "law_groups"),
    "Mobilization Option Groups": os.path.join(_MOD_COMMON, "mobilization_option_groups"),
    "Mobilization Options": os.path.join(_MOD_COMMON, "mobilization_options"),
    "Modifier Types": os.path.join(_MOD_COMMON, "modifier_type_definitions"),
    "Modifiers": os.path.join(_MOD_COMMON, "static_modifiers"),
    "Pop Needs": os.path.join(_MOD_COMMON, "pop_needs"),
    "Subject Types": os.path.join(_MOD_COMMON, "subject_types"),
}

def _format_description(desc, indent="\t\t"):
    """Render a localized description as one or more indented lines.

    Vic3 loc strings often embed literal `\\n` newlines and bracketed concept
    references; we collapse runs of whitespace so each output line is grep-able
    without word-wrapping.
    """
    if not desc:
        return ""
    text = desc.replace("\\n", "\n").strip()
    out = []
    for line in text.split("\n"):
        line = " ".join(line.split())
        if line:
            out.append(f"{indent}{line}")
    return "\n".join(out) + "\n" if out else ""


def generate_docs(mod_state):
    """Generate text reference docs (laws, technologies, buildings, goods, combat units) from parsed mod state.

    Called by mod_state_server.py on startup and reload, and by this script standalone.
    """
    tech_unlock_index = tech_unlocks_lib.build_tech_unlock_index(
        Path(mod_path),
        include_vanilla=True,
        vanilla_common_root=Path(base_game_path) / "game" / "common",
    )
    _generate_laws(mod_state)
    _generate_technologies(mod_state, tech_unlock_index)
    _generate_buildings(mod_state)
    _generate_goods(mod_state)
    _generate_combat_units(mod_state)
    print("Doc generation complete.")


def _generate_laws(mod_state):
    laws_path = os.path.join(doc_path, "engine", "laws.txt")
    laws_output = ""
    laws = mod_state.get_data("Laws")
    laws_dict = {}
    law_effects_dict = defaultdict(list)
    law_variant_dict = {}
    for law_id, (_, law_data) in laws.items():
        law_group = law_data["group"][1]
        if law_group not in laws_dict.keys():
            laws_dict[law_group] = []
        laws_dict[law_group].append(law_id)
        modifiers = law_data.get("modifier", ['', {}])[1]
        if modifiers:
            modifier_list = [key + modifiers[key][0] + modifiers[key][1] for key in modifiers.keys()]
            law_effects_dict[law_id] += modifier_list
        parent = law_data.get("parent", None)
        if parent:
            parent_id = parent[1]
            law_variant_dict[law_id] = parent_id

    for law_group in laws_dict.keys():
        laws_output += f"{mod_state.localize(law_group)}:\n"
        for law_id in laws_dict[law_group]:
            law_data = laws[law_id][1]
            laws_output += f"\t{mod_state.localize(law_id)}"
            progressiveness = law_data.get("progressiveness", ["", ""])[1]
            if progressiveness and progressiveness != "0":
                laws_output += f" [progressiveness={progressiveness}]"
            variant_of = law_data.get("parent", None)
            if variant_of:
                laws_output += f" (Variant of {mod_state.localize(variant_of[1])})"
            unlocking_tech_ids = law_data.get("unlocking_technologies", None)
            if unlocking_tech_ids:
                if unlocking_tech_ids[1]:
                    tech_name = mod_state.localize(unlocking_tech_ids[1][0])
                    laws_output += f" - Unlocking Technology: {tech_name}"
            laws_output += "\n"
            laws_output += _format_description(mod_state.get_description(law_id), indent="\t\t")

    with open(laws_path, "w", encoding="utf-8") as f:
        f.write(laws_output)


def _generate_technologies(mod_state, tech_unlock_index):
    tech_path = os.path.join(doc_path, "engine", "technologies.txt")
    tech_output = ""
    tech = mod_state.get_data("Technologies")
    tech_dict = defaultdict(list)
    for tech_id, (_, tech_data) in tech.items():
        era = tech_data.get("era", ["", "era_0"])[1]
        era_int = int(era.split("_")[-1])
        tech_dict[era_int].append(tech_id)

    for era in range(1, 13):
        tech_output += f"{era}: {len(tech_dict[era])} technologies\n"
        for tech_id in tech_dict[era]:
            tech_output += f"\t{mod_state.localize(tech_id)}"
            description = mod_state.get_description(tech_id)
            if description is not None:
                tech_output += f" - {description}"
            tech_output += "\n"
            tech_requirement = tech[tech_id][1].get("unlocking_technologies", None)
            if tech_requirement:
                tech_requirement_ids = tech_requirement[1]
                if tech_requirement_ids:
                    tech_output += "\t\tUnlocking Technologies:\n"
                    for unlocking_tech_ids in tech_requirement_ids:
                        tech_output += f"\t\t\t{mod_state.localize(unlocking_tech_ids)}\n"
            tech_output += _format_tech_unlocks(mod_state, tech_unlock_index, tech_id)

    with open(tech_path, "w", encoding="utf-8") as f:
        f.write(tech_output)


# Entity types whose unlocked entries we list by name (gameplay-major).
# PMs are summarized as a count instead — they're typically dozens per tech
# and already reachable via the parent building's listing in buildings.txt.
_TECH_UNLOCKS_NAMED_TYPES = (
    "Buildings",
    "Laws",
    "Combat Unit Types",
    "Decrees",
    "Ship Types",
    "Mobilization Options",
    "Parties",
    "Ship Modifications",
)


def _format_tech_unlocks(mod_state, tech_unlock_index, tech_id):
    rec = tech_unlock_index.get(tech_id)
    if not rec:
        return ""
    lines = []
    by_type = rec.get("by_type", {})
    for entity_type in _TECH_UNLOCKS_NAMED_TYPES:
        entries = by_type.get(entity_type)
        if not entries:
            continue
        names = sorted({mod_state.localize(e["id"]) for e in entries})
        lines.append(f"\t\tUnlocks {entity_type}: {', '.join(names)}")
    pm_count = len(by_type.get("PMs", []) or [])
    if pm_count:
        lines.append(f"\t\tUnlocks PMs: {pm_count} (listed under their buildings in buildings.txt)")
    return ("\n".join(lines) + "\n") if lines else ""


def _generate_buildings(mod_state):
    building_path = os.path.join(doc_path, "engine", "buildings.txt")
    building_output = ""
    buildings_data = mod_state.get_data("Buildings")
    pmg_groups = mod_state.get_data("PM Groups")
    production_methods = mod_state.get_data("PMs")
    for building_id, data in buildings_data.items():
        pm_groups = data[1].get("production_method_groups", ["", []])[1]
        building_group = data[1].get("building_group", ["", ""])[1]
        header = mod_state.localize(building_id)
        if building_group:
            header += f" ({building_group})"
        building_output += f"{header}:\n"
        building_output += _format_description(mod_state.get_description(building_id), indent="\t")
        tech_requirement = data[1].get("unlocking_technologies", None)
        if tech_requirement:
            if tech_requirement[1]:
                tech_name = mod_state.localize(tech_requirement[1][0])
                building_output += f"\tUnlocking Technology: {tech_name}\n"
        for pmg in pm_groups:
            if pmg not in pmg_groups.keys():
                building_output += f"Building {mod_state.localize(building_id)} references missing PM Group {mod_state.localize(pmg)}\n"
                continue
            building_output += f"\t{mod_state.localize(pmg)}:\n"
            pms = pmg_groups[pmg][1].get("production_methods", ["", []])[1]
            for pm in pms:
                if pm not in production_methods.keys():
                    building_output += f"Building {mod_state.localize(building_id)} references missing PM {mod_state.localize(pm)}\n"
                    continue
                building_output += f"\t\t{mod_state.localize(pm)}\n"
                pm_data = production_methods[pm][1]
                if isinstance(pm_data, list):
                    pm_data_flat = {}
                    for e in pm_data:
                        pm_data_flat.update(e)
                    pm_data = pm_data_flat
                tech_requirement = pm_data.get("unlocking_technologies", None)
                pollution = None
                state_modifiers = pm_data.get("state_modifiers", None)
                if state_modifiers:
                    workforce_scaled = state_modifiers[1].get("workforce_scaled", None)
                    if workforce_scaled:
                        pollution = workforce_scaled[1].get("state_pollution_generation_add", None)
                if pollution is not None:
                    building_output += f"\t\t\tMonthly Pollution: {pollution[1]}\n"
        building_output += "\n"

    with open(building_path, "w", encoding="utf-8") as f:
        f.write(building_output)


def _generate_goods(mod_state):
    goods_path = os.path.join(doc_path, "engine", "goods.txt")
    goods_output = ""
    goods = mod_state.get_data("Goods")
    for good_id, (_, good_data) in goods.items():
        category = good_data.get("category", ["", ""])[1]
        cost = good_data.get("cost", ["", ""])[1]
        prestige_factor = good_data.get("prestige_factor", ["", ""])[1]
        attrs = []
        if category:
            attrs.append(f"category={category}")
        if cost:
            attrs.append(f"cost={cost}")
        if prestige_factor and prestige_factor != "0":
            attrs.append(f"prestige={prestige_factor}")
        suffix = f" ({', '.join(attrs)})" if attrs else ""
        goods_output += f"{mod_state.localize(good_id)}{suffix}\n"
        goods_output += _format_description(mod_state.get_description(good_id), indent="\t")

    with open(goods_path, "w", encoding="utf-8") as f:
        f.write(goods_output)


def _generate_combat_units(mod_state):
    combat_units_path = os.path.join(doc_path, "engine", "combat_units.txt")
    combat_units_output = ""
    combat_unit_groups = mod_state.get_data("Combat Unit Groups")
    combat_unit_types = mod_state.get_data("Combat Unit Types")

    combat_unit_dict = defaultdict(list)
    for type, data in combat_unit_types.items():
        group_data = data[1]
        if isinstance(group_data, list):
            group_data_flat = {}
            for e in group_data:
                group_data_flat.update(e)
            group_data = group_data_flat
        group = group_data.get("group")[1]
        combat_unit_dict[group] += [type]

    for group in combat_unit_groups.keys():
        combat_units_output += f"{mod_state.localize(group)}:\n"
        for type in combat_unit_dict[group]:
            combat_units_output += f"\t{mod_state.localize(type)}\n"
            combat_units_output += _format_description(mod_state.get_description(type), indent="\t\t")
            unit_data = combat_unit_types[type][1]
            if isinstance(unit_data, list):
                unit_data_flat = {}
                for e in unit_data:
                    unit_data_flat.update(e)
                unit_data = unit_data_flat
            tech_requirement = unit_data.get("unlocking_technologies", None)
            if tech_requirement:
                if tech_requirement[1]:
                    tech_name = mod_state.localize(tech_requirement[1][0])
                    combat_units_output += f"\t\tUnlocking Technology: {tech_name}\n"
            combat_units_output += _format_combat_unit_stats(unit_data)

    with open(combat_units_path, "w", encoding="utf-8") as f:
        f.write(combat_units_output)


# Combat-stat fields rendered inline. Order chosen for readability: capacity
# first, then offense/defense pair, then breakthrough/recovery pair.
_COMBAT_UNIT_STATS = (
    ("max_manpower", "max_manpower"),
    ("supply_capacity", "supply_capacity"),
    ("unit_offense_add", "offense"),
    ("unit_defense_add", "defense"),
    ("unit_breakthrough_add", "breakthrough"),
    ("unit_recovery_rate_add", "recovery_rate"),
    ("unit_morale_loss_add", "morale_loss"),
    ("unit_morale_recovery_add", "morale_recovery"),
)


def _format_combat_unit_stats(unit_data):
    """One-line stats summary for a combat unit type.

    Reads top-level fields (max_manpower, supply_capacity) and the
    `battle_modifier = { ... }` block, both flat and list forms.
    """
    battle = unit_data.get("battle_modifier")
    bm = {}
    if battle:
        bm_raw = battle[1]
        if isinstance(bm_raw, list):
            for e in bm_raw:
                bm.update(e)
        elif isinstance(bm_raw, dict):
            bm = bm_raw
    parts = []
    for field, label in _COMBAT_UNIT_STATS:
        if field in unit_data:
            value = unit_data[field][1]
        elif field in bm:
            value = bm[field][1]
        else:
            continue
        parts.append(f"{label}={value}")
    return f"\t\tStats: {', '.join(parts)}\n" if parts else ""


if __name__ == "__main__":
    ms = ModState(base_game_paths, mod_paths)
    ms.add_localization(os.path.join(base_game_path, "game", "localization", "english"))
    ms.add_localization(os.path.join(mod_path, "localization", "english"))
    ms.add_localization(os.path.join(mod_path, "localization", "english", "replace"))
    generate_docs(ms)
    print("Done!")
