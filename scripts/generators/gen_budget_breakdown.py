"""Generate the Budget breakdown's category values, charts and legend.

Run explicitly after changing this catalogue or adding an institution. No save
state or refresh effect: the panel evaluates current country data on demand.
"""
from __future__ import annotations

import json
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
    "pie_tt": "Each color matches a row below. Pies show shares of positive amounts; signed adjustments remain in the list. Weekly headers include those adjustments and exclude Investment Pool Transfer.",
    "row_tt": "Weekly amount and share of positive amounts. Other Civil Buildings excludes the administration costs allocated to institutions and General Administration. Other Income and Other Expenses reconcile the listed amounts to the public budget totals after excluding Investment Pool Transfer, including temporary flows and uncategorized items.",
    "how": "How the Breakdown Works",
    "how_text": "#b Administration Allocation#!\\nGovernment Administration produces bureaucracy and tax capacity rather than goods for sale. Its weekly operating deficit is the cost of its wages and input goods, including any slave upkeep. Universities, ports and other civil buildings stay under Other Civil Buildings.\\n\\nThe share allocated to institutions is their current bureaucracy use divided by all bureaucracy produced, capped at 100%. Each institution receives that pool in proportion to its current level, including institutions with reduced bureaucracy costs. Targets still being implemented do not count. General Administration receives the remainder, including unused capacity and non-institution bureaucracy use. With no production or no institution levels, all administration costs stay there.\\n\\nThe budget predicts wages while administration buildings report their latest weekly balance. Allocation is capped at the government's civil wage, goods and slave-upkeep total, so a wage change cannot allocate more than that total.\\n\\n#b Charts and Amounts#!\\nIncome and expense totals exclude Investment Pool Transfer. Construction Goods also excludes that transfer, which funds private construction. Military includes army and navy wages, goods, slave upkeep, warship construction and warship maintenance. Shipping covers supply ships and port connections.\\n\\n#b Journal Systems#!\\nBanking, Covert Actions, Cultural Hegemony, the United Nations and other systems have separate rows. Hover over a row to see its currently applied sources. Their amounts are removed from Additional Expenses or Income once; only the unattributed remainder stays there. One-time treasury payments and non-monetary resource costs are outside the weekly budget.\\n\\nRows are ordered from largest to smallest amount. Category colors stay fixed across the charts and the list. With many institutions the palette repeats; use the names and percentages to identify each category. Signed negative adjustments appear in the list with a zero chart share. Charts are empty when there are no positive amounts.",
}


def institutions():
    keys = set(json.loads((ROOT / "vanilla_parsed/common/institutions.json").read_text()))
    for path in (ROOT / "common/institutions").glob("*.txt"):
        keys.update(re.findall(r"^(?:INJECT:|REPLACE:)?(institution_\w+)\s*=", path.read_text(encoding="utf-8-sig"), re.M))
    return sorted(keys)


def categories(side):
    if side == "income":
        return [(key, label) for key, label, _ in INCOME] + [("other", "te_budget_chart_other_income")]
    return [(key, key) for key in institutions()] + [("administration", "te_budget_chart_administration")] + [
        (key, label) for key, label, _ in EXPENSE
    ] + [("other", "te_budget_chart_other_expense")]


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
        expr += ".AddScope('institution_levels', MakeScopeValue(GetPlayer.MakeScope.ScriptValue('te_budget_institution_levels')))"
        fields = [(f"{key}_{i}", getter) for key, _, getters in EXPENSE for i, getter in enumerate(getters)]
    return expr + "".join(f".AddScope('{key}', MakeScopeValue(GetPlayer.{getter}))" for key, getter in fields)


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
                if key == "additional":
                    body += "\n" + "\n".join(f"\tsubtract = te_budget_expense_{source}" for source in SOURCES[side])
                out.append(sv(f"te_budget_expense_{key}", body))
        out.append(sv(f"te_budget_{side}_other", "\tvalue = scope:total\n" + "\n".join(f"\tsubtract = te_budget_{side}_{key}" for key, _ in items[:-1])))
        # Absolute row positions let the GUI sort live without writing game state.
        # Compare cached amounts only; catalogue order deterministically breaks ties.
        out.append(sv(f"te_budget_{side}_legend_height", "\tvalue = 0\n" + "\n".join(
            f"\tif = {{ limit = {{ NOT = {{ scope:row_{key} = 0 }} }} add = 44 }}" for key, _ in items)))
        for i, (key, _) in enumerate(items):
            body = "\tvalue = 0"
            for j, (other, _) in enumerate(items):
                if key == other:
                    continue
                op = ">=" if j < i else ">"
                body += f"\n\tif = {{ limit = {{ NOT = {{ scope:row_{other} = 0 }} scope:row_{other} {op} scope:row_{key} }} add = 44 }}"
            out.append(sv(f"te_budget_{side}_{key}_row_y", body))
        for key, _ in items:
            out.append(sv(f"te_budget_{side}_{key}_positive", f"\tvalue = te_budget_{side}_{key}\n\tmin = 0"))
        out.append(sv(f"te_budget_{side}_positive_total", "\tvalue = 0\n" + "\n".join(f"\tadd = te_budget_{side}_{key}_positive" for key, _ in items)))
        for i, (key, _) in enumerate(items):
            out.append(sv(f"te_budget_{side}_{key}_share", f"\tvalue = te_budget_{side}_{key}_positive\n\tdivide = {{ value = scope:positive_total min = 0.001 }}\n\tmin = 0\n\tmax = 1"))
            out.append(sv(f"te_budget_{side}_cum_{i}", "\tvalue = 0\n" + "\n".join(f"\tadd = te_budget_{side}_{k}_positive" for k, _ in items[:i + 1]) + "\n\tdivide = { value = scope:positive_total min = 0.001 }\n\tmin = 0\n\tmax = 1"))
    return "\n".join(out)


def pie_texture(i):
    return f"gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_{MODELS[i % len(MODELS)][0]}.dds"


def chart(side):
    items = categories(side)
    out = [f"\ttype te_budget_{side}_charts = flowcontainer {{", "\t\tdirection = horizontal", "\t\tspacing = 16", "\t\tparentanchor = hcenter", "\t\twidget = {", "\t\t\tsize = { 176 176 }", '\t\t\ttooltip = "te_budget_chart_pie_tt"', '\t\t\ticon = { size = { 100% 100% } texture = "gfx/interface/backgrounds/round_frame_dec.dds" }', "\t\t\twidget = {", "\t\t\t\tsize = { 75% 75% }", "\t\t\t\tparentanchor = center"]
    for i in reversed(range(len(items))):
        out += ["\t\t\t\tprogresspie = {", "\t\t\t\t\tsize = { 100% 100% }", "\t\t\t\t\tmin = 0", "\t\t\t\t\tmax = 1", f'\t\t\t\t\tvalue = "[FixedPointToFloat({expression(side, f"{side}_cum_{i}")})]"', f'\t\t\t\t\ttexture = "{pie_texture(i)}"', "\t\t\t\t\tframesize = { 128 128 }", "\t\t\t\t\tframe = 2", "\t\t\t\t}"]
    out += ["\t\t\t}", "\t\t}", "\t}", f"\ttype te_budget_{side}_legend = widget {{", f"\t\tsize = {{ 480 [FixedPointToInt(TopScope.ScriptValue('te_budget_{side}_legend_height'))] }}"]
    for i, (key, label) in enumerate(items):
        val = expression(side, f"{side}_{key}")
        share = expression(side, f"{side}_{key}_share")
        tooltip = f"te_budget_chart_{key}_tt" if key.startswith("institution_") else "te_budget_chart_row_tt"
        if key in SOURCES[side]:
            tooltip = f"te_budget_chart_source_{side}_{key}_tt"
        out += ["\t\tte_budget_chart_row = {", f"\t\t\tposition = {{ 0 [FixedPointToInt(TopScope.ScriptValue('te_budget_{side}_{key}_row_y'))] }}", f'\t\t\tvisible = "[NotEqualTo_CFixedPoint({val}, \'(CFixedPoint)0\')]"', f'\t\t\ttooltip = "{tooltip}"', f'\t\t\tblockoverride "swatch" {{ texture = "{pie_texture(i)}" }}', f'\t\t\tblockoverride "label" {{ text = "{label}" }}', f'\t\t\tblockoverride "amount" {{ raw_text = "@money![{val}|D]" }}', f'\t\t\tblockoverride "share" {{ raw_text = "[{share}|%1]" }}', "\t\t}"]
    out += ["\t}"]
    return "\n".join(out)


def indent(text, depth=1):
    return "\n".join("\t" * depth + line if line else "" for line in text.splitlines())


def section(side):
    row_scopes = "TopScope" + "".join(
        f".AddScope('row_{key}', MakeScopeValue(TopScope.ScriptValue('te_budget_{side}_{key}')))"
        for key, _ in categories(side)
    )
    plots = f'''flowcontainer = {{
\tdirection = vertical
\tspacing = 8
\tdatacontext = "[TopScope.AddScope('positive_total', MakeScopeValue(TopScope.ScriptValue('te_budget_{side}_positive_total')))]"
\tte_budget_{side}_charts = {{}}
\tte_budget_{side}_legend = {{ parentanchor = hcenter datacontext = "[{row_scopes}]" }}
\ttextbox = {{
\t\tvisible = "[EqualTo_CFixedPoint(TopScope.ScriptValue('te_budget_{side}_positive_total'), '(CFixedPoint)0')]"
\t\ttext = "te_budget_chart_no_{side}"
\t\tautoresize = yes
\t\tparentanchor = hcenter
\t\tusing = fontsize_medium
\t}}
}}'''
    if side == "expense":
        plots = '''flowcontainer = {
\tdirection = vertical
\tspacing = 8
\tdatacontext = "[TopScope.AddScope('institution_pool', MakeScopeValue(TopScope.ScriptValue('te_budget_institution_pool')))]"
''' + indent(plots) + "\n}"
    return indent(f'''type te_budget_{side}_section = flowcontainer {{
\tdirection = vertical
\tspacing = 8
\tignoreinvisible = yes
\t# Intermediate value scopes share the building sum, pool and denominator.
\tdatacontext = "[{scope(side)}]"
\tdefault_header_2texts = {{
\t\tblockoverride "size" {{ size = {{ 520 44 }} }}
\t\tblockoverride "text1" {{ text = "te_budget_chart_{side}" }}
\t\tblockoverride "text2" {{ raw_text = "@money![TopScope.ScriptValue('te_budget_total')|D]" }}
\t}}
{indent(plots)}
}}''')


def generated_gui():
    return "# AUTO-GENERATED by scripts/generators/gen_budget_breakdown.py; do not edit manually.\n# Pies use catalogue order/colors; lists sort descending by signed amount.\ntypes te_budget_generated_charts {\n" + "\n".join(chart(side) + "\n" + section(side) for side in ("income", "expense")) + "\n}\n"


def generated_source_types():
    return "# AUTO-GENERATED by scripts/generators/gen_budget_breakdown.py; do not edit manually.\n# Accounting mirrors only; the native currency modifier still charges/credits the treasury.\n\n" + "\n".join(
        sv(source_type(side, key), '\tcolor = neutral\n\tpercent = no\n\tdecimals = 2\n\tprefix = "MONEY_PREFIX"\n\tscript_only = yes')
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
            loc[source_type(side, key)] = f"{label}: Weekly {'Income' if side == 'income' else 'Expenses'}"
            loc[source_type(side, key) + "_desc"] = (
                "This amount is already included in Additional Income. It is not credited again."
                if side == "income" else
                "This amount is already included in Government Expenses. It is not charged again."
            )
            loc[f"te_budget_chart_source_{side}_{key}_tt"] = (
                f"#b {label}#!\\nWeekly amount: @money![TopScope.ScriptValue('te_budget_{side}_{key}')|D]"
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
