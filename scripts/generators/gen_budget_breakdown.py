"""Generate the Budget breakdown's category values, charts and legend.

Run explicitly after changing this catalogue or adding an institution. No save
state or refresh effect: the panel evaluates current country data on demand.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.image_pipeline.gen_ch_model_pie_textures import MODELS  # noqa: E402
from organize_loc import _render_loc_file, section_label  # noqa: E402

# Mirrors travel with the actual timed modifier, including its multiplier,
# decay and removal. They have no economic effect; never estimate a live charge
# from a formula that may have changed since the modifier was last refreshed.
SOURCES = {
    "expense": {
        "banking": ("Banking", (
            "banking_event_deposit_guarantee_emergency", "banking_event_import_and_subsidy_cost",
            "banking_event_fx_defense", "banking_event_quiet_rescue", "banking_event_selective_bailout_cost",
            "banking_event_rural_credit_cost", "banking_event_harvest_subsidy_cost",
            "banking_event_sovereign_wealth_fund_cost", "banking_crash_response_cost",
            "banking_event_interbank_guarantee", "banking_event_microfinance_cost",
            "banking_event_student_debt_relief_cost", "banking_event_bailout_cost",
            "planning_treasury_pool_balance", "te_mon_gold_carry_expense",
        )),
        "covert": ("Covert Actions", ("covert_operation_funding_cost",)),
        "culture": ("Cultural Hegemony", ("ch_cultural_program_funding_cost", "ch_world_exposition_cost")),
        "colonial": ("Colonial Development", ("colonial_development_investment_expense_modifier",)),
        "un": ("United Nations", (
            "un_founding_cost_modifier", "un_peacekeeping_contributor_cost",
            "un_development_contributor_cost", "un_humanitarian_aid_cost", "un_humanitarian_token_cost",
            "un_observer_mission_cost", "un_peacekeeping_deployment_cost", "un_mission_service_cost",
            "un_dues_modifier", "un_loan_repayment_modifier",
        )),
        "nuclear": ("Nuclear Program", ("nd_upkeep_cost", "nd_exercise_cost")),
        "nuclear_taboo": ("Nuclear Civil Defence", ("nd_taboo_civil_defence",)),
        "space": ("Space Race", ("we_se_debris_clearance",)),
        "drugs": ("Drug Shortage Response", ("drugs_shortage_spending",)),
    },
    "income": {
        "un": ("United Nations", ("un_dev_fund_treasury_grant_modifier",)),
        "reserve": ("Strategic Reserve Sales", ("st_res_sell_profit_modifier",)),
        "war_tax": ("War Profit Tax", ("war_profit_tax_modifier",)),
        "tax_code": ("Spectrum Auctions", ("te_tax_spectrum_auction_proceeds",)),
    },
}


# Expense source rows that also carry a government building's weekly operating
# cost, moved there from Other Civil Buildings. common/script_values/
# te_budget_values.txt measures it (te_budget_<name>_actual) and caps it at
# the civil pool left after administration (te_budget_<name>_cost).
CARVE_OUTS = {
    "space": ("space_program", "Space Program"),
}


# The native field each copy repeats. No modifier-type key keeps a field out of
# tooltips (vanilla's modifier_types.md lists them all), so the copy line is
# printed like the native one and named as a Breakdown label, not a charge.
NATIVE = {"expense": "country_expenses_add", "income": "country_tax_income_add"}


def native_display(side):
    """The native type's `decimals` and `prefix`, from the vanilla snapshot."""
    body = json.loads((ROOT / "vanilla_parsed/common/modifier_types.json").read_text())[NATIVE[side]][1]
    return body["decimals"][1], body["prefix"][1]


def source_type(side, key):
    return f"country_te_budget_{side}_{key}_add"


def source_getter(side, key):
    return f"GetModifier.GetValueFor('{source_type(side, key)}')"


INCOME = (
    ("income_tax", "BUDGET_INCOME_TAXES", "GetIncomeTaxIncome"),
    ("poll_tax", "BUDGET_POLL_TAXES", "GetPollTaxIncome"),
    ("consumption_tax", "BUDGET_CONSUMPTION_TAXES", "PredictConsumptionTaxes"),
    ("dividends_tax", "BUDGET_DIVIDENDS_TAXES", "PredictDividendsTaxes"),
    ("tariffs", "BUDGET_TARIFFS", "PredictTariffs"),
    ("minting", "BUDGET_MINTING", "PredictMinting"),
    ("government_dividends", "DIVIDENDS_FROM_GOVERNMENT_SHARES", "PredictGovernmentShareDividends"),
    ("pacts", "BUDGET_DIPLOMATIC_PACTS", "PredictDiplomaticPactsIncome"),
    ("treaties", "BUDGET_TREATIES", "PredictTreatyIncome"),
    *((key, f"te_budget_chart_source_{side}_{key}", source_getter(side, key)) for side in ("income",) for key in SOURCES[side]),
    ("additional", "te_budget_chart_additional_income", "GetModifier.GetValueFor('country_tax_income_add')"),
)
# Government wages/goods include universities, ports and other civil buildings.
# Remove only the administration buildings' cost, once, before allocating it.
EXPENSE = (
    ("civil", "te_budget_chart_civil", ("PredictGovernmentWagesExpenses", "GetGovernmentGoodsExpenses", "GetGovernmentSlavesExpenses")),
    ("construction", "BUDGET_CONSTRUCTION_GOODS", ("GetConstructionGoodsExpenses",)),
    ("military", "te_budget_chart_military", ("PredictMilitaryWagesExpenses", "GetMilitaryGoodsExpenses", "GetMilitarySlavesExpenses", "GetMilitaryShipConstructionGoodsExpenses", "GetMilitaryShipMaintenanceExpenses")),
    ("shipping", "te_budget_chart_shipping", ("GetSupplyShipConstructionGoodsExpenses", "GetSupplyShipMaintenanceExpenses", "GetPortConnectionExpenses")),
    ("welfare", "BUDGET_WELFARE_PAYMENTS", ("GetWelfarePaymentsExpenses",)),
    ("subsidies", "BUDGET_SUBSIDIES", ("GetSubsidiesExpenses",)),
    ("subventions", "BUDGET_SUBVENTIONS", ("GetSubventionsExpenses",)),
    ("government_losses", "LOSSES_FROM_GOVERNMENT_SHARES", ("PredictGovernmentShareLosses",)),
    ("pacts", "BUDGET_DIPLOMATIC_PACTS", ("PredictDiplomaticPactsExpenses",)),
    ("treaties", "BUDGET_TREATIES", ("PredictTreatyExpenses",)),
    ("interest", "BUDGET_INTEREST", ("GetInterestPayment",)),
    *((key, f"te_budget_chart_source_{side}_{key}", (source_getter(side, key),)) for side in ("expense",) for key in SOURCES[side]),
    ("additional", "te_budget_chart_additional_expense", ("GetModifier.GetValueFor('country_expenses_add')",)),
)

LOCALIZATION = {
    "tab": "Breakdown",
    "tab_tt": "Weekly public income and expenses as pies and itemized amounts. Government Administration costs are allocated among your institutions.",
    "income": "Weekly Income",
    "expense": "Weekly Expenses",
    "civil": "Other Civil Buildings",
    "military": "Military",
    "shipping": "Shipping and Connections",
    "administration": "General Administration",
    "other_income": "Other Income",
    "other_expense": "Other Expenses",
    "additional_income": "Other Additional Income",
    "additional_expense": "Other Additional Expenses",
    "no_income": "No positive income this week.",
    "no_expense": "No positive expenses this week.",
    "pie_tt": "Each color matches a row below. Collapsed groups form one slice; expanded groups use their visible children. Pies show shares of positive component amounts; signed adjustments remain in the list. Weekly headers include those adjustments and exclude Investment Pool Transfer.",
    "row_tt": "Weekly amount and share of positive amounts. Other Civil Buildings excludes the administration costs allocated to institutions and General Administration, and the Space Program, which is under Programme Costs. Other Income and Other Expenses reconcile the listed amounts to the public budget totals after excluding Investment Pool Transfer, including temporary flows and uncategorized items.",
    "how": "How the Breakdown Works",
    "how_text": "#b Administration Allocation#!\\nGovernment Administration produces bureaucracy and tax capacity rather than goods for sale. Its weekly operating deficit is the cost of its wages and input goods, including any slave upkeep. Universities, ports and other civil buildings stay under Other Civil Buildings, except the Space Program: its weekly operating deficit, its wages and Launch Capacity, appears under Programme Costs as part of Space Race.\\n\\nThe share allocated to institutions is their current bureaucracy use divided by all bureaucracy produced, capped at 100%. Each institution receives that pool in proportion to its current level, including institutions with reduced bureaucracy costs. Targets still being implemented do not count. General Administration receives the remainder, including unused capacity and non-institution bureaucracy use. With no production or no institution levels, all administration costs stay there.\\n\\nThe budget predicts wages while administration buildings report their latest weekly balance. Allocation is capped at the government's civil wage, goods and slave-upkeep total, so a wage change cannot allocate more than that total. The Space Program's cost is capped at what that total holds after administration.\\n\\n#b Charts and Amounts#!\\nIncome and expense totals exclude Investment Pool Transfer. Construction Goods also excludes that transfer, which funds private construction. Military includes army and navy wages, goods, slave upkeep, warship construction and warship maintenance. Shipping covers supply ships and port connections.\\n\\n#b Journal Systems#!\\nBanking, Covert Actions, Cultural Hegemony, the United Nations and other systems have separate rows. Hover over a row to see its currently applied sources. Their amounts are removed from Additional Expenses or Income once; only the unattributed remainder stays there. One-time treasury payments and non-monetary resource costs are outside the weekly budget.\\n\\nGroups start collapsed. Click the arrow to expand Taxes, Administration, Military, Shipping, Programme Costs or diplomatic flows. Army and Navy each expand to Wages plus Materials and Support. Rows are ordered from largest to smallest amount within each group. Collapsed groups have one pie slice; expanded groups give their visible parts separate slices. Military wages are derived from each branch’s forecast total minus its goods. Materials and Support includes branch goods plus the full operating deficits of logistics centres and naval fortifications. Their own wages and upkeep are separate from barracks, conscription and naval administration costs covered by the branch forecast. Support upkeep combines wages, goods and slave upkeep. Navy also includes warship construction and maintenance. Other Military Costs reconciles remaining upkeep and forecast differences. Category colors stay fixed across the charts and the list. With many institutions the palette repeats; use the names and percentages to identify each category. Signed negative adjustments appear in the list with a zero chart share. Charts are empty when there are no positive amounts.",
}

LOCALIZATION.update({
    "taxes": "Taxes", "administration_group": "Administration", "army": "Army", "navy": "Navy",
    "wages": "Wages", "materials": "Materials and Support", "military_adjustment": "Other Military Costs",
    "programmes": "Programme Costs", "diplomacy_income": "Diplomatic Income", "diplomacy_expense": "Diplomatic Payments",
    "supply_construction": "Supply Ship Construction", "supply_maintenance": "Supply Ship Maintenance", "port_connections": "Port Connections",
    "expand_tt": "Expand or collapse this breakdown. The pie groups collapsed categories and separates expanded categories into their visible parts.",
    "materials_tt": "Materials and Support includes branch goods plus full logistics-centre and naval-fortification upkeep, combining their wages, goods and any slave upkeep. Barracks, conscription and naval administration stay in the native branch amounts and are not added again. Navy also includes warship construction and maintenance. Weekly operating balances can differ from wage forecasts; Other Military Costs reconciles the difference.",
    "group_tt": "This total includes the indented rows below it. Expand to see its components as separate pie slices. Shares count positive component amounts; refunds remain signed, so expansion never changes the denominator. A zero net group can still contain costs and refunds.",
})


def institutions():
    keys = set(json.loads((ROOT / "vanilla_parsed/common/institutions.json").read_text()))
    for path in (ROOT / "common/institutions").glob("*.txt"):
        keys.update(re.findall(r"^(?:INJECT:|REPLACE:)?(institution_\w+)\s*=", path.read_text(encoding="utf-8-sig"), re.M))
    return sorted(keys)


def categories(side):
    """Canonical accounting categories, before presentation grouping."""
    if side == "income":
        return [(key, label) for key, label, _ in INCOME] + [("other", "te_budget_chart_other_income")]
    return [(key, key) for key in institutions()] + [("administration", "te_budget_chart_administration")] + [
        (key, label) for key, label, _ in EXPENSE
    ] + [("other", "te_budget_chart_other_expense")]


@dataclass(frozen=True)
class Node:
    key: str
    label: str
    children: tuple[Node, ...] = ()


def tree(side):
    """Display hierarchy; existing totals remain the reconciliation basis."""
    leaves = {key: Node(key, label) for key, label in categories(side)}
    def group(key, label, keys):
        return Node(key, "te_budget_chart_" + label, tuple(leaves[k] for k in keys))
    diplomacy = group("diplomacy", "diplomacy_" + side, ("pacts", "treaties"))
    if side == "income":
        taxes = group("taxes", "taxes", ("income_tax", "poll_tax", "consumption_tax", "dividends_tax", "tariffs", "war_tax"))
        grouped = {child.key for parent in (taxes, diplomacy) for child in parent.children}
        return (taxes, diplomacy, *(node for key, node in leaves.items() if key not in grouped))
    army = Node("army", "te_budget_chart_army", (Node("army_wages", "te_budget_chart_wages"), Node("army_materials", "te_budget_chart_materials")))
    navy = Node("navy", "te_budget_chart_navy", (Node("navy_wages", "te_budget_chart_wages"), Node("navy_materials", "te_budget_chart_materials")))
    military = Node("military", leaves["military"].label, (army, navy, Node("military_adjustment", "te_budget_chart_military_adjustment")))
    shipping = Node("shipping", leaves["shipping"].label, tuple(Node(key, "te_budget_chart_" + key) for key in ("supply_construction", "supply_maintenance", "port_connections")))
    administration = group("administration_group", "administration_group", (*institutions(), "administration"))
    programmes = group("programmes", "programmes", tuple(SOURCES[side]))
    grouped = {child.key for parent in (administration, programmes, diplomacy) for child in parent.children} | {"military", "shipping"}
    return (administration, military, shipping, programmes, diplomacy, *(node for key, node in leaves.items() if key not in grouped))


def walk(nodes, ancestors=()):
    for node in nodes:
        yield node, ancestors
        yield from walk(node.children, ancestors + (node,))


def sibling_sets(side):
    yield "root", tree(side)
    for node, _ in walk(tree(side)):
        if node.children:
            yield node.key, node.children


def flag(side, key):
    return f"te_budget_{side}_{key}_open"


MILITARY_FIELDS = {
    "army_total": "PredictTotalArmyExpenses", "navy_total": "PredictTotalNavyExpenses",
    "army_goods": "GetArmyGoodsExpenses", "navy_goods": "GetNavyGoodsExpenses",
}


def sv(name, body):
    return f"{name} = {{\n{body}\n}}\n"


def scope(side):
    expr = "GuiScope.SetRoot(GetPlayer.MakeScope)"
    total = "PredictWeeklyIncome" if side == "income" else "GetWeeklyExpenses"
    expr += f".AddScope('total', MakeScopeValue(Subtract_CFixedPoint(GetPlayer.{total}, GetPlayer.GetInvestmentIncome)))"
    if side == "expense":
        expr += ".AddScope('private_construction', MakeScopeValue(GetPlayer.GetInvestmentIncome))"
    if side == "income":
        fields = [(key, getter) for key, _, getter in INCOME]
    else:
        expr += ".AddScope('institution_usage', MakeScopeValue(GetPlayer.GetInstitutionInvestmentBureaucracyCost))"
        expr += ".AddScope('administration_actual', MakeScopeValue(GetPlayer.MakeScope.ScriptValue('te_budget_administration_actual')))"
        expr += "".join(f".AddScope('{name}_actual', MakeScopeValue(GetPlayer.MakeScope.ScriptValue('te_budget_{name}_actual')))"
                        for name, _ in CARVE_OUTS.values())
        expr += ".AddScope('institution_levels', MakeScopeValue(GetPlayer.MakeScope.ScriptValue('te_budget_institution_levels')))"
        fields = [(f"{key}_{i}", getter) for key, _, getters in EXPENSE for i, getter in enumerate(getters)]
    if side == "expense":
        fields += list(MILITARY_FIELDS.items())
        for branch in ("army", "navy"):
            expr += f".AddScope('{branch}_support_actual', MakeScopeValue(GetPlayer.MakeScope.ScriptValue('te_budget_{branch}_support_actual')))"
    expr += "".join(f".AddScope('{key}', MakeScopeValue(GetPlayer.{getter}))" for key, getter in fields)
    expr += "".join(f".AddScope('open_{node.key}', MakeScopeValue(Select_CFixedPoint(GetVariableSystem.Exists('{flag(side, node.key)}'), '(CFixedPoint)1', '(CFixedPoint)0')))"
                    for node, _ in walk(tree(side)) if node.children)
    return expr


def expression(side, name):
    return f"TopScope.ScriptValue('te_budget_{name}')"


def generated_values():
    out = ["# AUTO-GENERATED by scripts/generators/gen_budget_breakdown.py; do not edit manually.\n"]
    for key in institutions():
        out.append(sv(f"te_budget_level_{key}", f"\tvalue = 0\n\tif = {{\n\t\tlimit = {{ has_institution = {key} }}\n\t\tinstitution:{key} = {{ add = investment }}\n\t}}"))
    out.append(sv("te_budget_institution_levels", "\tvalue = 0\n" + "\n".join(f"\tadd = te_budget_level_{key}" for key in institutions())))
    for key in institutions():
        out.append(sv(f"te_budget_expense_{key}", f"\tvalue = scope:institution_pool\n\tmultiply = te_budget_level_{key}\n\tdivide = {{ value = scope:institution_levels min = 1 }}"))
    out.append(sv("te_budget_allocated_institutions", "\tvalue = 0\n" + "\n".join(f"\tadd = te_budget_expense_{key}" for key in institutions())))
    for side in ("income", "expense"):
        items = categories(side)
        if side == "income":
            for key, _, _ in INCOME:
                body = f"\tvalue = scope:{key}"
                if key == "additional":
                    body += "\n" + "\n".join(f"\tsubtract = te_budget_income_{source}" for source in SOURCES[side])
                out.append(sv(f"te_budget_income_{key}", body))
        else:
            out.append(sv("te_budget_expense_administration", "\tvalue = te_budget_administration_cost\n\tsubtract = te_budget_allocated_institutions"))
            for key, _, getters in EXPENSE:
                body = "\tvalue = 0\n" + "\n".join(f"\tadd = scope:{key}_{i}" for i in range(len(getters)))
                if key == "construction":
                    body += "\n\tsubtract = scope:private_construction"
                if key == "civil":
                    body += "\n\tsubtract = te_budget_administration_cost"
                    body += "".join(f"\n\tsubtract = te_budget_{name}_cost" for name, _ in CARVE_OUTS.values())
                if key in CARVE_OUTS:
                    body += f"\n\tadd = te_budget_{CARVE_OUTS[key][0]}_cost"
                if key == "additional":
                    # A carve-out row also holds a building cost that Additional
                    # Expenses never contained; remove only its modifier charges.
                    body += "\n" + "\n".join(f"\tsubtract = scope:{source}_0" if source in CARVE_OUTS else f"\tsubtract = te_budget_expense_{source}"
                                              for source in SOURCES[side])
                out.append(sv(f"te_budget_expense_{key}", body))
        out.append(sv(f"te_budget_{side}_other", "\tvalue = scope:total\n" + "\n".join(f"\tsubtract = te_budget_{side}_{key}" for key, _ in items[:-1])))
        nodes = list(walk(tree(side)))
        if side == "expense":
            extra = {
                "army_wages": "value = scope:army_total\n\tsubtract = scope:army_goods",
                "army_materials": "value = scope:army_goods\n\tadd = scope:army_support_actual",
                "navy_wages": "value = scope:navy_total\n\tsubtract = scope:navy_goods",
                "navy_materials": "value = scope:navy_goods\n\tadd = scope:navy_support_actual\n\tadd = scope:military_3\n\tadd = scope:military_4",
                "military_adjustment": "value = te_budget_expense_military\n\tsubtract = te_budget_expense_army\n\tsubtract = te_budget_expense_navy",
                "supply_construction": "value = scope:shipping_0",
                "supply_maintenance": "value = scope:shipping_1",
                "port_connections": "value = scope:shipping_2",
            }
            for key, body in extra.items():
                out.append(sv(f"te_budget_expense_{key}", "\t" + body))
        existing = {key for key, _ in items}
        for node, ancestors in nodes:
            key = node.key
            if key not in existing and node.children:
                out.append(sv(f"te_budget_{side}_{key}", "\tvalue = 0\n" + "\n".join(f"\tadd = te_budget_{side}_{child.key}" for child in node.children)))
            positive = ("\tvalue = 0\n" + "\n".join(f"\tadd = te_budget_{side}_{child.key}_positive" for child in node.children)
                        if node.children else f"\tvalue = te_budget_{side}_{key}\n\tmin = 0")
            out.append(sv(f"te_budget_{side}_{key}_positive", positive))
            active = ("\tvalue = 0\n" + "\n".join(f"\tadd = te_budget_{side}_{child.key}_active" for child in node.children) + "\n\tmax = 1"
                      if node.children else f"\tvalue = 0\n\tif = {{ limit = {{ NOT = {{ te_budget_{side}_{key} = 0 }} }} value = 1 }}")
            out.append(sv(f"te_budget_{side}_{key}_active", active))
            subtree = f"\tvalue = te_budget_{side}_{key}_active"
            if node.children:
                subtree += f"\n\tif = {{ limit = {{ scope:open_{key} = 1 }}\n" + "\n".join(f"\t\tadd = te_budget_{side}_{child.key}_subtree_rows" for child in node.children) + "\n\t}"
            out.append(sv(f"te_budget_{side}_{key}_subtree_rows", subtree))
            visible = f"\tvalue = te_budget_{side}_{key}_active"
            if ancestors:
                visible = "\tvalue = 0\n\tif = { limit = { " + " ".join(f"scope:open_{parent.key} = 1" for parent in ancestors) + f" }} value = te_budget_{side}_{key}_active }}"
            out.append(sv(f"te_budget_{side}_{key}_visible", visible))
            out.append(sv(f"te_budget_{side}_{key}_cached_rank", f"\tvalue = scope:rank_{key}"))
            out.append(sv(f"te_budget_{side}_{key}_cached_active", f"\tvalue = scope:active_{key}"))
            limits = [f"scope:open_{parent.key} = 1" for parent in ancestors]
            if node.children:
                limits.append(f"scope:open_{key} = 0")
            body = f"\tvalue = scope:positive_{side}_{key}"
            if limits:
                body = "\tvalue = 0\n\tif = {\n\t\tlimit = { " + " ".join(limits) + f" }}\n\t\tvalue = scope:positive_{side}_{key}\n\t}}"
            out.append(sv(f"te_budget_{side}_{key}_slice", body))
            out.append(sv(f"te_budget_{side}_{key}_share", f"\tvalue = te_budget_{side}_{key}_positive\n\tdivide = {{ value = scope:positive_total min = 0.001 }}\n\tmin = 0\n\tmax = 1"))
        out.append(sv(f"te_budget_{side}_positive_total", "\tvalue = 0\n" + "\n".join(f"\tadd = te_budget_{side}_{node.key}_positive" for node in tree(side))))
        out.append(sv(f"te_budget_{side}_root_cached_count", "\tvalue = scope:count_root"))
        siblings_by_parent = dict(sibling_sets(side))
        for node, ancestors in nodes:
            # A flat flow slot list preserves preorder without replicating nested
            # child lists once per possible parent slot. Count whole preceding
            # subtrees at each ancestor level, plus the ancestor headers.
            body = f"\tvalue = {len(ancestors)}"
            for depth, target in enumerate((*ancestors, node)):
                siblings = siblings_by_parent[ancestors[depth - 1].key if depth else "root"]
                index = siblings.index(target)
                for j, other in enumerate(siblings):
                    if other == target:
                        continue
                    op = ">=" if j < index else ">"
                    body += f"\n\tif = {{ limit = {{ scope:subtree_{other.key} > 0 scope:row_{other.key} {op} scope:row_{target.key} }} add = scope:subtree_{other.key} }}"
            out.append(sv(f"te_budget_{side}_{node.key}_display_rank", body))
        out.append(sv(f"te_budget_{side}_display_count", "\tvalue = 0\n" + "\n".join(f"\tadd = scope:subtree_{node.key}" for node in tree(side))))
        for i, _ in enumerate(nodes):
            out.append(sv(f"te_budget_{side}_cum_{i}", "\tvalue = 0\n" + "\n".join(f"\tadd = te_budget_{side}_{node.key}_slice" for node, _ in nodes[:i + 1]) + "\n\tdivide = { value = scope:positive_total min = 0.001 }\n\tmin = 0\n\tmax = 1"))
    return "\n".join(out)


def pie_texture(i):
    return f"gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_{MODELS[i % len(MODELS)][0]}.dds"


def chart(side):
    nodes = list(walk(tree(side)))
    out = [f"\ttype te_budget_{side}_charts = flowcontainer {{", "\t\tparentanchor = hcenter", "\t\twidget = {", "\t\t\tsize = { 176 176 }", '\t\t\ttooltip = "te_budget_chart_pie_tt"', '\t\t\ticon = { size = { 100% 100% } texture = "gfx/interface/backgrounds/round_frame_dec.dds" }', "\t\t\twidget = {", "\t\t\t\tsize = { 75% 75% }", "\t\t\t\tparentanchor = center"]
    for i in reversed(range(len(nodes))):
        out += ["\t\t\t\tprogresspie = {", "\t\t\t\t\tsize = { 100% 100% }", "\t\t\t\t\tmin = 0", "\t\t\t\t\tmax = 1", f'\t\t\t\t\tvalue = "[FixedPointToFloat({expression(side, f"{side}_cum_{i}")})]"', f'\t\t\t\t\ttexture = "{pie_texture(i)}"', "\t\t\t\t\tframesize = { 128 128 }", "\t\t\t\t\tframe = 2", "\t\t\t\t}"]
    out += ["\t\t\t}", "\t\t}", "\t}"]
    for i, (node, ancestors) in enumerate(nodes):
        key, label = node.key, node.label
        val, share = expression(side, f"{side}_{key}"), expression(side, f"{side}_{key}_share")
        rank, active = expression(side, f"{side}_{key}_cached_rank"), expression(side, f"{side}_{key}_cached_active")
        tooltip = f"te_budget_chart_{key}_tt" if key.startswith("institution_") else "te_budget_chart_row_tt"
        if key in ("army_materials", "navy_materials"):
            tooltip = "te_budget_chart_materials_tt"
        if key in SOURCES[side]:
            tooltip = f"te_budget_chart_source_{side}_{key}_tt"
        if node.children:
            tooltip = "te_budget_chart_group_tt"
        depth = len(ancestors)
        swatch_alpha = (f' alpha = "[Select_float(GetVariableSystem.Exists(\'{flag(side, key)}\'), \'(float)0\', \'(float)1\')]"'
                        if node.children else "")
        out += [f"\ttype te_budget_{side}_row_{key} = flowcontainer {{", "\t\tdirection = vertical", "\t\tignoreinvisible = yes",
                f'\t\tvisible = "[And(GreaterThan_CFixedPoint({active}, \'(CFixedPoint)0\'), EqualTo_CFixedPoint({rank}, TopScope.ScriptValue(\'te_budget_row_slot\')))]"',
                "\t\tte_budget_chart_row = {", f'\t\t\ttooltip = "{tooltip}"',
                f"\t\t\tblockoverride \"indent\" {{ size = {{ {depth * 14} 1 }} }}",
                f"\t\t\tblockoverride \"label_width\" {{ minimumsize = {{ {271 - depth * 14} 28 }} maximumsize = {{ {271 - depth * 14} -1 }} }}",
                f'\t\t\tblockoverride "swatch" {{ texture = "{pie_texture(i)}"{swatch_alpha} }}', f'\t\t\tblockoverride "label" {{ text = "{label}" }}',
                f'\t\t\tblockoverride "amount" {{ raw_text = "@money![{val}|D]" }}', f'\t\t\tblockoverride "share" {{ raw_text = "[{share}|%1]" }}']
        if node.children:
            f = flag(side, key)
            out += ["\t\t\tblockoverride \"toggle\" {", "\t\t\t\tbutton = {", "\t\t\t\t\tsize = { 18 24 }", "\t\t\t\t\tparentanchor = vcenter",
                    f'\t\t\t\t\tonclick = "[GetVariableSystem.Toggle(\'{f}\')]"', '\t\t\t\t\ttooltip = "te_budget_chart_expand_tt"',
                    f'\t\t\t\t\tbutton = {{ using = expand_arrow size = {{ 18 18 }} parentanchor = center alwaystransparent = yes visible = "[Not(GetVariableSystem.Exists(\'{f}\'))]" }}',
                    f'\t\t\t\t\tbutton = {{ using = expand_arrow_expanded size = {{ 18 18 }} parentanchor = center alwaystransparent = yes visible = "[GetVariableSystem.Exists(\'{f}\')]" }}', "\t\t\t\t}", "\t\t\t}"]
        out += ["\t\t}"]
        out += ["\t}"]
    # Flat sorted slots; each row uses a preorder rank that counts preceding
    # visible subtrees. Expansion never requires nested slot instantiation.
    out += [f"\ttype te_budget_{side}_slot_root = flowcontainer {{", "\t\tdirection = vertical", "\t\tignoreinvisible = yes"]
    out += [f"\t\tte_budget_{side}_row_{node.key} = {{}}" for node, _ in nodes]
    out += ["\t}", f"\ttype te_budget_{side}_list_root = flowcontainer {{", "\t\tdirection = vertical", "\t\tignoreinvisible = yes", "\t\tspacing = 1"]
    for i in range(len(nodes)):
        out += [f"\t\tte_budget_{side}_slot_root = {{", f'\t\t\tvisible = "[GreaterThan_CFixedPoint(TopScope.ScriptValue(\'te_budget_{side}_root_cached_count\'), \'(CFixedPoint){i}\')]"',
                f'\t\t\tdatacontext = "[TopScope.AddScope(\'row_slot\', MakeScopeValue(\'(CFixedPoint){i}\'))]"', "\t\t}"]
    out += ["\t}"]
    return "\n".join(out)


def indent(text, depth=1):
    return "\n".join("\t" * depth + line if line else "" for line in text.splitlines())


def section(side):
    nodes = list(walk(tree(side)))
    amounts = "TopScope" + "".join(f".AddScope('row_{node.key}', MakeScopeValue(TopScope.ScriptValue('te_budget_{side}_{node.key}')))" for node, _ in nodes)
    subtrees = "TopScope" + "".join(f".AddScope('subtree_{node.key}', MakeScopeValue(TopScope.ScriptValue('te_budget_{side}_{node.key}_subtree_rows')))" for node, _ in nodes)
    cached = "TopScope.AddScope('positive_total', MakeScopeValue(TopScope.ScriptValue('te_budget_" + side + "_positive_total')))"
    for node, _ in nodes:
        for dest, suffix in (("rank_" + node.key, "display_rank"), ("active_" + node.key, "visible"), ("positive_" + side + "_" + node.key, "positive")):
            cached += f".AddScope('{dest}', MakeScopeValue(TopScope.ScriptValue('te_budget_{side}_{node.key}_{suffix}')))"
    cached += f".AddScope('count_root', MakeScopeValue(TopScope.ScriptValue('te_budget_{side}_display_count')))"
    plots = f'''flowcontainer = {{
\tdirection = vertical
\tdatacontext = "[{amounts}]"
\tflowcontainer = {{
\t\tdirection = vertical
\t\tdatacontext = "[{subtrees}]"
\t\tflowcontainer = {{
\t\t\tdirection = vertical
\t\t\tspacing = 4
\t\t\tdatacontext = "[{cached}]"
\t\t\tte_budget_{side}_charts = {{}}
\t\t\tte_budget_{side}_list_root = {{ parentanchor = hcenter }}
\t\t\ttextbox = {{
\t\t\t\tvisible = "[EqualTo_CFixedPoint(TopScope.ScriptValue('te_budget_{side}_positive_total'), '(CFixedPoint)0')]"
\t\t\t\ttext = "te_budget_chart_no_{side}"
\t\t\t\tautoresize = yes
\t\t\t\tparentanchor = hcenter
\t\t\t\tusing = fontsize_medium
\t\t\t}}
\t\t}}
\t}}
}}'''
    if side == "expense":
        plots = "flowcontainer = {\n\tdirection = vertical\n\tdatacontext = \"[TopScope.AddScope('institution_pool', MakeScopeValue(TopScope.ScriptValue('te_budget_institution_pool')))]\"\n" + indent(plots) + "\n}"
    return indent(f'''type te_budget_{side}_section = flowcontainer {{
\tdirection = vertical
\tspacing = 4
\tignoreinvisible = yes
\t# GUI-local expansion flags, then cached amounts/ranks/positive totals.
\tdatacontext = "[{scope(side)}]"
\tdefault_header_2texts = {{
\t\tblockoverride "size" {{ size = {{ 520 44 }} }}
\t\tblockoverride "text1" {{ text = "te_budget_chart_{side}" }}
\t\tblockoverride "text2" {{ raw_text = "@money![TopScope.ScriptValue('te_budget_total')|D]" }}
\t}}
{indent(plots)}
}}''')


def generated_gui():
    return "# AUTO-GENERATED by scripts/generators/gen_budget_breakdown.py; do not edit manually.\n# Expandable sibling lists sort by amount; pie slices follow the visible frontier.\ntypes te_budget_generated_charts {\n" + "\n".join(chart(side) + "\n" + section(side) for side in ("income", "expense")) + "\n}\n"


def generated_source_types():
    return "# AUTO-GENERATED by scripts/generators/gen_budget_breakdown.py; do not edit manually.\n# Accounting mirrors only; the native currency modifier still charges/credits the treasury.\n# Printed like the native field, so a tooltip shows the same figure twice: once charged, once labelled.\n\n" + "\n".join(
        sv(source_type(side, key), '\tcolor = neutral\n\tpercent = no\n\tdecimals = {}\n\tprefix = {}\n\tscript_only = yes'.format(*native_display(side)))
        for side in ("income", "expense") for key in SOURCES[side]
    )


def main():
    (ROOT / "common/script_values/te_budget_generated_values.txt").write_text(generated_values(), encoding="utf-8-sig")
    (ROOT / "gui/te_budget_generated_charts.gui").write_text(generated_gui(), encoding="utf-8-sig")
    (ROOT / "common/modifier_type_definitions/te_budget_generated_types.txt").write_text(generated_source_types(), encoding="utf-8-sig")
    loc = {f"te_budget_chart_{key}": value for key, value in LOCALIZATION.items()}
    for side in ("income", "expense"):
        for key, (label, _) in SOURCES[side].items():
            loc[f"te_budget_chart_source_{side}_{key}"] = label
            # A source modifier's tooltip prints this line beside the native one;
            # name it as a label so the repeated amount doesn't read as a second charge.
            loc[source_type(side, key)] = f"Counted in the Budget Breakdown under {label}"
            loc[source_type(side, key) + "_desc"] = (
                f"Not a second {'payment' if side == 'income' else 'charge'}: the ${NATIVE[side]}$ line already includes this amount. "
                f"It is repeated so the Budget panel's Breakdown tab can list it under {label}."
            )
            building = ""
            if side == "expense" and key in CARVE_OUTS:
                name, building_label = CARVE_OUTS[key]
                building = (f"\\n{building_label}: @money![TopScope.ScriptValue('te_budget_{name}_cost')|D]"
                            f"\\nThe {building_label}'s wages and input goods, moved here from Other Civil Buildings.")
            loc[f"te_budget_chart_source_{side}_{key}_tt"] = (
                f"#b {label}#!\\nWeekly amount: @money![TopScope.ScriptValue('te_budget_{side}_{key}')|D]"
                f"{building}"
                f"\\n\\n[GetPlayer.GetModifier.GetDescFor('{source_type(side, key)}')]"
                "\\n\\nCurrent applied sources, including temporary charges, their multipliers and any decay. "
                "One-time treasury payments and non-monetary costs are excluded from the weekly budget."
            )
    for key in institutions():
        loc[f"te_budget_chart_{key}_tt"] = (
            f"#b ${key}$#!\\nCurrent level: [TopScope.ScriptValue('te_budget_level_{key}')|0]"
            "\\nAdministration cost: @money![TopScope.ScriptValue('te_budget_administration_cost')|D]"
            "\\nBureaucracy produced: @bur![TopScope.ScriptValue('te_budget_produced_bureaucracy')|D]"
            "\\nInstitution bureaucracy use: @bur![GetPlayer.GetInstitutionInvestmentBureaucracyCost|D]"
            "\\nInstitution pool: @money![TopScope.ScriptValue('te_budget_institution_pool')|D]"
            "\\nTotal institution levels: [TopScope.ScriptValue('te_budget_institution_levels')|0]"
            f"\\nAllocated cost: @money![TopScope.ScriptValue('te_budget_expense_{key}')|D]"
            "\\n\\nAdministration cost × institution bureaucracy use ÷ bureaucracy produced, capped at the administration cost; then institution pool × current level ÷ total institution levels."
        )
    (ROOT / "localization/english/te_budget_l_english.yml").write_bytes(
        _render_loc_file([(section_label("BUDGET"), {key: f'0 "{value}"' for key, value in loc.items()})])
    )


if __name__ == "__main__":
    main()
