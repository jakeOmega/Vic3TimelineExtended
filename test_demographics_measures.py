"""Demographics phase 2 step 3a: the Family Policy measures
(docs/superpowers/archive/specs/2026-10-12-demographics-phase2-consequences-design.md §3.3-§3.7).

Static checks on the catalogue (each measure's modifier carries its census types and interest groups, the laws-allow
table is §3.4's, every button sits under the rule's wrapper) and the measures' effects run through
test_demographics_registry's _Engine: the five-year term, Birth Limit's cycle, the Crash Campaign's run and bar,
leaving the law, the revolution's re-apply, the money upkeep and the AI pulse.
"""

import importlib.util
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from test_demographics_registry import (GENERATED_EFFECTS, GENERATED_VALUES, ROOT, _Engine, _block, _find, _parse_script,
                                       _raw_blocks, _text)

sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
import demographics_modifiers as DM  # noqa: E402
import demographics_params as P  # noqa: E402

MS_MODIFIERS = ROOT / "common" / "static_modifiers" / "te_demog_measure_modifiers.txt"
MS_EFFECTS = ROOT / "common" / "scripted_effects" / "te_demog_measure_effects.txt"
MS_TRIGGERS = ROOT / "common" / "scripted_triggers" / "te_demog_measure_triggers.txt"
MS_VALUES = ROOT / "common" / "script_values" / "te_demog_measure_values.txt"
MS_SGUIS = ROOT / "common" / "scripted_guis" / "te_demog_measure_sguis.txt"
MS_MESSAGES = ROOT / "common" / "messages" / "te_demog_messages.txt"
TYPES_FILE = ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt"
WIDGETS = ROOT / "gui" / "te_demographics_widgets.gui"
LAWS_FILE = ROOT / "common" / "laws" / "extra_laws.txt"
ENGINE_MODIFIERS = ROOT / "docs" / "engine" / "modifiers_summary.txt"
LOC_DIR = ROOT / "localization" / "english"

PN, FP, PC, COMMUNAL, TRADITIONAL = ("law_pro_natalist_subsidies", "law_state_sponsored_family_planning",
                                     "law_population_control_measures", "law_communal_child_rearing",
                                     "law_traditional_family_structure")
FAMILY_LAWS = (TRADITIONAL, PN, FP, PC, COMMUNAL)

# §3.4's catalogue: the laws that allow each measure, and its modifier's lines (census types, interest groups, upkeep
# and other effects). Parental Leave's women's-work line is on phase 2 step 1's family.
CATALOGUE = {
    "child_allowance": ({PN, COMMUNAL}, {
        "state_desired_fertility_mult": 0.14,   # step 3b's fit (§3.4's +8%)
        "interest_group_ig_devout_approval_add": 1, "interest_group_ig_trade_unions_approval_add": 1}),
    "family_housing": ({PN, FP, COMMUNAL}, {
        "state_urban_fertility_relief_add": 0.5, "interest_group_ig_trade_unions_approval_add": 1}),
    "honours": ({TRADITIONAL, PN}, {
        "state_desired_fertility_mult": 0.05, "interest_group_ig_devout_approval_add": 1,   # the fit (+3%)
        "country_authority_cost_add": 50}),   # the authority upkeeps: the rebalance of 2026-10-16 (owner)
    "restricted_contraception": ({PN}, {
        "state_fertility_means_add": -0.2, "state_maternal_mortality_mult": 0.25,
        "interest_group_ig_devout_approval_add": 2, "interest_group_ig_intelligentsia_approval_add": -2,
        "state_pop_support_movement_feminist_mult": 0.1, "country_authority_cost_add": 200}),
    "parental_leave": ({FP, COMMUNAL}, {
        "state_desired_fertility_mult": 0.05, "state_demog_womens_work_ratio_add": 0.02,
        "interest_group_ig_trade_unions_approval_add": 1, "interest_group_ig_industrialists_approval_add": -1}),
    "free_contraception": ({FP, PC, COMMUNAL}, {
        "state_fertility_means_add": 0.1, "interest_group_ig_intelligentsia_approval_add": 1,
        "interest_group_ig_devout_approval_add": -2}),
    "sex_education": ({FP, PC}, {
        "state_means_literacy_add": 0.2, "interest_group_ig_devout_approval_add": -1,
        "country_institution_cost_institution_schools_mult": 0.1}),
    "later_longer_fewer": ({FP, PC}, {
        "state_desired_fertility_mult": -0.1, "interest_group_ig_devout_approval_add": -1,
        "interest_group_ig_rural_folk_approval_add": -1, "country_authority_cost_add": 150}),
    "birth_limit": ({PC}, {
        "state_desired_fertility_mult": -0.3, "state_sex_ratio_at_birth_add": 5,
        "interest_group_ig_rural_folk_approval_add": -3, "interest_group_ig_devout_approval_add": -2,
        "country_authority_cost_add": 300}),
    "rural_exemption": ({PC}, {
        "state_birth_limit_relief_add": 0.5, "interest_group_ig_rural_folk_approval_add": 1}),
    "crash_campaign": ({PC}, {
        "state_desired_fertility_mult": -0.2, "country_legitimacy_base_add": -10,
        "state_radicals_from_political_movements_mult": 0.25, "interest_group_ig_rural_folk_approval_add": -3,
        "interest_group_ig_devout_approval_add": -3, "interest_group_ig_intelligentsia_approval_add": -2,
        "interest_group_ig_trade_unions_approval_add": -2, "country_authority_cost_add": 300}),
}
BIRTH_LIMIT_ONE = {
    "state_desired_fertility_mult": -0.45, "state_sex_ratio_at_birth_add": 10,
    "interest_group_ig_rural_folk_approval_add": -3, "interest_group_ig_devout_approval_add": -2,
    "country_authority_cost_add": 400}
MONEY = {"child_allowance": 0.005, "family_housing": 0.0025, "parental_leave": 0.003, "free_contraception": 0.001}
NEW_TYPES = ("state_desired_fertility_mult", "state_urban_fertility_relief_add", "state_means_literacy_add",
             "state_maternal_mortality_mult", "state_birth_limit_relief_add", "state_sex_ratio_at_birth_add")


def _lines(body):
    """{field: value} of a modifier's lines, comments and the icon dropped."""
    body = re.sub(r"#[^\n]*", "", body)
    return {k: float(v) for k, v in re.findall(r"^\s*(\w+) = (-?[\d.]+)\s*$", body, re.M)}


def _date(year, month=0):
    """te_history_month_index for a date: months from year 0, January = 0."""
    return float(year * 12 + month)


class _MeasureEngine(_Engine):
    """_Engine with the measures' files, a law in force (has_law), scripted triggers called with arguments,
    trigger_if, an add_modifier without a multiplier (which fails when the name is already held: a same-name
    add_modifier stacks), set_variable = yes, and the notices and the self-check recorded instead of run."""

    def __init__(self, law=PN, year=1900, month=0, full=True, fixtures=None, triggers=None, others=()):
        super().__init__({"te_history_month_index": _date(year, month), "gdp": 52_000_000.0,
                          "capital.te_demog_women_rate": 0.5, "authority": 1000.0, **(fixtures or {})},
                         triggers={"te_demog_effects_run": full, "is_ai": False, **(triggers or {})})
        self.effects.update(_raw_blocks([MS_EFFECTS]))
        self.values.update(_raw_blocks([MS_VALUES]))
        self.triggers.update(_raw_blocks([MS_TRIGGERS]))
        self.law = law
        self.others = set(others)   # laws in force in other groups (the form of government, free speech)
        self.notices, self.selfchecks = [], []
        self.exists = {"capital"}

    def at(self, year, month=0):
        self.fixtures["te_history_month_index"] = _date(year, month)
        return self

    def sv(self, name):
        return self.value(self._tree(self.values, name))

    def _test(self, key, op, arg):
        if key in ("has_law", "has_law_or_variant"):   # no variants among the laws the tests hold
            return arg == f"law_type:{self.law}" or arg in {f"law_type:{law}" for law in self.others}
        if key == "exists":
            return arg in self.exists
        if key == "trigger_if":
            rest = [i for i in arg if i[0] != "limit"]
            return not self.holds(_find(arg, "limit")) or self.holds(rest)
        if isinstance(arg, list) and key in self.triggers and key not in self.trigger_fixtures:
            return self.holds(self._tree(self.triggers, key, tuple((k, v) for k, _, v in arg)))
        return super()._test(key, op, arg)

    def run(self, items):
        chain = None
        for key, op, arg in items:
            if key in ("if", "else_if", "else"):
                go, chain = self._branch(key, arg, chain)
                if go:
                    self.run([i for i in arg if i[0] != "limit"])
                continue
            chain = None
            if key == "post_notification":
                self.notices.append(arg)
            elif key == "te_debug_demog_ms_selfcheck_start":
                self.selfchecks.append(_find(arg, "M"))
            elif key == "add_modifier":
                name = _find(arg, "name")
                assert name not in self.modifiers, f"{name} added over itself (a same-name add_modifier stacks)"
                mult = next((v for k, _, v in arg if k == "multiplier"), None)
                self.modifiers[name] = 1.0 if mult is None else self._q(self.value(mult))
            elif key == "set_variable" and _find(arg, "value") == "yes":
                self.vars[_find(arg, "name")] = 1.0
            elif key == "hidden_effect":
                self.run(arg)
            elif key == "custom_tooltip":
                if isinstance(arg, list):
                    self.run([i for i in arg if i[0] != "text"])
            else:
                super().run([(key, op, arg)])

    def do(self, effect, **args):
        inner = " ".join(f"{k} = {v}" for k, v in args.items())
        self.run(_parse_script(f"{effect} = {{ {inner} }}" if args else f"{effect} = yes"))
        return self

    def holds_trigger(self, name, **args):
        inner = " ".join(f"{k} = {v}" for k, v in args.items())
        return self.holds(_parse_script(f"{name} = {{ {inner} }}" if args else f"{name} = yes"))

    def sgui_valid(self, key):
        sgui = _parse_script(_block(_text(MS_SGUIS), f"te_demog_ms_{key}_sgui"))
        return self.holds(_find(sgui, "is_valid"))

    def press(self, key):
        """One press of the measure's button: its scripted GUI's effect, if its is_valid allows it."""
        assert self.sgui_valid(key), f"{key}'s button is greyed"
        sgui = _parse_script(_block(_text(MS_SGUIS), f"te_demog_ms_{key}_sgui"))
        self.run(_find(sgui, "effect"))
        return self

    def measure_mods(self):
        return {k: v for k, v in self.modifiers.items() if k.startswith("te_demog_ms_")}


class TestCatalogue(unittest.TestCase):
    """§3.4: each measure's modifier, its laws and its upkeep."""

    @classmethod
    def setUpClass(cls):
        cls.mods = _raw_blocks([MS_MODIFIERS])

    def test_each_measures_modifier_carries_its_lines(self):
        for key, (_, lines) in CATALOGUE.items():
            with self.subTest(key):
                self.assertEqual(_lines(self.mods[f"te_demog_ms_{key}"]), {k: float(v) for k, v in lines.items()})
        self.assertEqual(_lines(self.mods["te_demog_ms_birth_limit_one"]),
                         {k: float(v) for k, v in BIRTH_LIMIT_ONE.items()})

    def test_parental_leave_works_through_step_ones_family(self):
        """Its women's-work line sits on step 1's family (re-applied by the moved lines' pair, read by step 2's
        participation model), and its upkeep reads step 1's women's rate in the capital, not a stand-in."""
        family = _text(ROOT / "common" / "modifier_type_definitions" / "demographics_workforce_line_types.txt")
        self.assertIn("state_demog_womens_work_ratio_add = {", family)
        body = _block(_text(MS_VALUES), "te_demog_ms_women_at_work")
        self.assertIn("value = capital.te_demog_women_rate", body)
        self.assertIn("divide = { value = te_demog_k_rate_max min = 0.01 }", body, "the rate over its ceiling: the upkeep's share runs 0 to 1")
        self.assertNotIn("has_law", body)

    def test_money_upkeep_sits_on_its_own_cost_modifier(self):
        """scripting_best_practices.md, "Expense Scaling with GDP": country_expenses_add = 1, the multiplier the
        weekly cost, with the Budget Breakdown's mirror (its Family Policy row); no measure modifier carries money
        itself."""
        for key in CATALOGUE:
            cost = self.mods.get(f"te_demog_ms_{key}_cost")
            if key in MONEY:
                self.assertEqual(_lines(cost), {"country_expenses_add": 1.0, "country_te_budget_expense_family_add": 1.0},
                                 key)
            else:
                self.assertIsNone(cost, key)
        for name, body in self.mods.items():
            if not name.endswith("_cost"):
                self.assertNotIn("country_expenses_add", body, name)
        self.assertEqual(len(self.mods), len(CATALOGUE) + 1 + len(MONEY))

    def test_every_line_is_an_engine_modifier_or_a_registered_type(self):
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        types = {name for path in (ROOT / "common" / "modifier_type_definitions").glob("*.txt")
                 for name in re.findall(r"^(\w+) = \{", _text(path), re.M)}
        for name, body in self.mods.items():
            for field in _lines(body):
                self.assertTrue(field in engine or field in types, f"{name}: {field}")

    def test_the_new_census_types_are_registered_script_only_named_and_new(self):
        text = _text(TYPES_FILE)
        engine = {line.split("|")[1] for line in _text(ENGINE_MODIFIERS).splitlines() if line.count("|") >= 2}
        loc = "".join(_text(p) for p in sorted(LOC_DIR.glob("*.yml")))
        for name in NEW_TYPES:
            with self.subTest(name):
                body = _block(text, name)
                self.assertIn("script_only = yes", body)
                self.assertRegex(body, r"decimals = \d")
                self.assertNotIn(name, engine)
                # never the state_demog_ prefix: a release keeps every state_demog_ line (the moved lines' families)
                self.assertFalse(name.startswith("state_demog_"))
                self.assertRegex(loc, rf"(?m)^ {name}:0 \"")
                self.assertRegex(loc, rf"(?m)^ {name}_desc:0 \"")
        # since step 3b the census reads each of them in state scope, in the generated files (gen_demographics.py), and
        # no script reads one through the owner
        generated = _text(GENERATED_VALUES) + _text(GENERATED_EFFECTS)
        for name in NEW_TYPES:
            self.assertIn(f"modifier:{name}", generated, name)
        for path in (ROOT / "common").rglob("*.txt"):
            for name in NEW_TYPES:
                self.assertNotIn(f"owner.modifier:{name}", _text(path), f"{path.name} reads {name} on the owner")

    def test_the_reader_gives_the_catalogues_census_lines(self):
        """demographics_modifiers.measure_lines (the harness's measures) reads the game file as the catalogue has it."""
        got = DM.measure_lines()
        for key, (_, lines) in CATALOGUE.items():
            want = {k: float(v) for k, v in lines.items() if k in P.MEASURE_TYPES + P.DEMOG_FERTILITY_TYPES}
            self.assertEqual({k: v for k, v in got[key].items() if k in P.MEASURE_TYPES + P.DEMOG_FERTILITY_TYPES},
                             want, key)
        self.assertEqual(got["birth_limit_one"]["state_desired_fertility_mult"],
                         BIRTH_LIMIT_ONE["state_desired_fertility_mult"])

    def test_the_laws_allow_the_catalogues_measures(self):
        for law in FAMILY_LAWS:
            eng = _MeasureEngine(law=law)
            for key, (laws, _) in CATALOGUE.items():
                self.assertEqual(eng.holds_trigger(f"te_demog_ms_allowed_{key}"), law in laws, f"{key} under {law}")

    def test_communal_child_rearing_allows_more_by_who_governs(self):
        """The review of #989 (owner): under Communal Child-Rearing a council or an anarchist commune adds Sex
        Education, a party state or an autocrat that outlaws dissent adds Honours and Restricted Contraception; Birth
        Limit and the Crash Campaign stay Population Control Measures' alone."""
        utopia = {"sex_education"}
        dystopia = {"honours", "restricted_contraception"}
        alone = {key for key, (laws, _) in CATALOGUE.items() if COMMUNAL in laws}
        self.assertEqual(alone, {"child_allowance", "parental_leave", "family_housing", "free_contraception"})
        cases = [
            ((), alone),
            (("law_council_republic",), alone | utopia),
            (("law_anarchy",), alone | utopia),
            (("law_single_party_state", "law_outlawed_dissent"), alone | dystopia),
            (("law_autocracy", "law_outlawed_dissent"), alone | dystopia),
            (("law_single_party_state",), alone),             # dissent not outlawed: no dystopia
            (("law_autocracy", "law_censorship"), alone),
        ]
        for others, want in cases:
            with self.subTest(others):
                eng = _MeasureEngine(law=COMMUNAL, others=others)
                got = {key for key in CATALOGUE if eng.holds_trigger(f"te_demog_ms_allowed_{key}")}
                self.assertEqual(got, want)
        # the government's laws alone, without the communal law, allow nothing of either
        for others in (("law_council_republic",), ("law_single_party_state", "law_outlawed_dissent")):
            for law in set(FAMILY_LAWS) - {COMMUNAL}:
                eng = _MeasureEngine(law=law, others=others)
                got = {key for key in CATALOGUE if eng.holds_trigger(f"te_demog_ms_allowed_{key}")}
                self.assertEqual(got, {key for key, (laws, _) in CATALOGUE.items() if law in laws}, (law, others))
        # the reasons and hovers name the government's laws
        loc = "".join(_text(p) for p in sorted(LOC_DIR.glob("*.yml")))
        for key, names in (("sex_education", ("$law_council_republic$", "$law_anarchy$")),
                           ("honours", ("$law_single_party_state$", "$law_autocracy$", "$law_outlawed_dissent$")),
                           ("restricted_contraception", ("$law_single_party_state$", "$law_outlawed_dissent$"))):
            for suffix in ("_law_tt", "_other_tt", "_tt"):
                line = re.search(rf"(?m)^ te_demog_ms_{key}{suffix}:0 \"(.*)\"$", loc).group(1)
                for name in names + ("$law_communal_child_rearing$",):
                    self.assertIn(name, line, f"{key}{suffix}")

    def test_desired_constants_match_the_modifiers(self):
        """The self-check's expected change (te_demog_ms_desired_<measure>) is each modifier's own line."""
        eng = _MeasureEngine()
        for key, (_, lines) in CATALOGUE.items():
            self.assertAlmostEqual(eng.sv(f"te_demog_ms_desired_{key}"), lines.get("state_desired_fertility_mult", 0),
                                   msg=key)
        self.assertAlmostEqual(eng.sv("te_demog_ms_desired_birth_limit_one"),
                               BIRTH_LIMIT_ONE["state_desired_fertility_mult"])
        eng.modifiers.update(te_demog_ms_child_allowance=1, te_demog_ms_birth_limit_one=1)
        self.assertAlmostEqual(eng.sv("te_demog_ms_desired_on"), 0.14 - 0.45)

    def test_every_measure_has_its_loc_and_notice(self):
        loc = "".join(_text(p) for p in sorted(LOC_DIR.glob("*.yml")))
        messages = _raw_blocks([MS_MESSAGES])
        for name in self.mods:
            self.assertRegex(loc, rf"(?m)^ {name}:0 \"", name)
            self.assertRegex(loc, rf"(?m)^ {name}_desc:0 \"", name)
        for key in CATALOGUE:
            self.assertIn(f"te_demog_ms_ended_{key}", messages)
            for part in ("name", "desc"):
                self.assertRegex(loc, rf"(?m)^ notification_te_demog_ms_ended_{key}_{part}:0 \"")
        self.assertIn("te_demog_ms_crash_campaign_over", messages)


class TestButtons(unittest.TestCase):
    """§3.3, §3.7: a button a measure, greyed with its reason; every one under the rule's wrapper."""

    @classmethod
    def setUpClass(cls):
        cls.sguis = _raw_blocks([MS_SGUIS])

    def test_one_button_a_measure_under_the_rule(self):
        for key, (laws, _) in CATALOGUE.items():
            with self.subTest(key):
                body = _parse_script(self.sguis[f"te_demog_ms_{key}_sgui"])
                self.assertEqual(_find(body, "scope"), "country")
                self.assertEqual(_find(body, "is_shown"), [(f"te_demog_ms_allowed_{key}", "=", "yes")])
                self.assertEqual(_find(body, "ai_is_valid"), [("always", "=", "no")])
                # the rule first: a greyed button says the measures act only under Full
                first = _find(body, "is_valid")[0]
                self.assertEqual(first[0], "trigger_if")
                self.assertEqual(_find(first[2], "custom_tooltip"),
                                 [("text", "=", "te_demog_ms_rule_tt"), ("te_demog_effects_run", "=", "yes")])

    def test_outside_full_every_button_is_greyed(self):
        for law in FAMILY_LAWS:
            for full in (True, False):
                eng = _MeasureEngine(law=law, full=full)
                eng.vars["te_dg_ms_birth_limit"] = 1890.0
                for key, (laws, _) in CATALOGUE.items():
                    valid = eng.sgui_valid(key)
                    if not full or law not in laws:
                        self.assertFalse(valid, f"{key} under {law}, full={full}")

    def test_the_effects_switch_only_through_the_press(self):
        """Each button's effect is what it says plus the hidden press: no measure switches without te_demog_ms_press
        (or Birth Limit's own), so the button and the AI share the switching effects."""
        for key in CATALOGUE:
            effect = _find(_parse_script(self.sguis[f"te_demog_ms_{key}_sgui"]), "effect")
            hidden = [v for k, _, v in effect if k == "hidden_effect"]
            self.assertEqual(len(hidden), 1, key)
            want = ([("te_demog_ms_press_birth_limit", "=", "yes")] if key == "birth_limit"
                    else [("te_demog_ms_press", "=", [("M", "=", key)])])
            self.assertEqual(hidden[0], want, key)

    def test_the_panel_draws_a_row_and_a_dimmed_row_a_measure(self):
        gui = _text(WIDGETS)
        section = gui[gui.index("type te_demog_sec_family"):gui.index("type te_demog_sec_how")]
        for key in CATALOGUE:
            ctx = f"datacontext = \"[GetScriptedGui('te_demog_ms_{key}_sgui')]\""
            self.assertEqual(section.count(ctx), 2, key)
        self.assertIn("GetVariableSystem.Toggle('te_demog_family_closed')", section)
        self.assertIn("AccessActiveLawFromGroup('lawgroup_family_reproductive_policy')", section)
        layout = _text(ROOT / "gui" / "te_demographics_layout.gui")   # the composers (issue #1029)
        self.assertIn("te_demog_sec_family = {}", layout[layout.index("type te_demog_tab_sections"):])
        # the state subtab shows no Family Policy (§10: country tab only)
        self.assertNotIn("te_demog_sec_family", layout[layout.index("type te_state_demog_content"):])
        self.assertNotIn("te_demog_sec_family", gui[gui.index("type te_state_demog_overview"):])
        # rows read script values, never a measure's variable (a GUI read of a missing variable logs every frame)
        loc = "".join(_text(p) for p in sorted(LOC_DIR.glob("*.yml")))
        self.assertNotRegex(section + loc, r"Var\('te_dg_ms_")

    def test_the_buttons_are_greyed_with_their_reasons(self):
        eng = _MeasureEngine(law=PN, year=1900)
        self.assertTrue(eng.sgui_valid("child_allowance"))
        eng.press("child_allowance").at(1903)
        self.assertFalse(eng.sgui_valid("child_allowance"), "the term hasn't run")
        eng.at(1905)
        self.assertTrue(eng.sgui_valid("child_allowance"))
        # the Rural Exemption needs Birth Limit
        eng = _MeasureEngine(law=PC)
        self.assertFalse(eng.sgui_valid("rural_exemption"))
        eng.press("birth_limit")
        self.assertTrue(eng.sgui_valid("rural_exemption"))


    def test_a_measure_needs_its_authority_upkeep_free_to_start(self):
        """The review of #989 (owner, 2026-10-16): as a decree does, a measure with an authority upkeep greys its Start
        until that much authority is free, with the reason; once on, it can still end with none free."""
        authority = {key: lines["country_authority_cost_add"] for key, (_, lines) in CATALOGUE.items()
                     if "country_authority_cost_add" in lines}
        self.assertEqual(set(authority), {"honours", "restricted_contraception", "later_longer_fewer", "birth_limit",
                                          "crash_campaign"})
        loc = "".join(_text(p) for p in sorted(LOC_DIR.glob("*.yml")))
        for key, cost in authority.items():
            with self.subTest(key):
                law = next(iter(CATALOGUE[key][0]))
                eng = _MeasureEngine(law=law, year=1900, fixtures={"authority": cost - 1.0})
                self.assertFalse(eng.sgui_valid(key), "short of the upkeep")
                eng.fixtures["authority"] = float(cost)
                self.assertTrue(eng.sgui_valid(key))
                body = _block(_text(MS_SGUIS), f"te_demog_ms_{key}_sgui")
                self.assertIn(f"text = te_demog_ms_{key}_authority_tt", body)
                self.assertIn(f"authority >= te_demog_ms_authority_{key}", body)
                self.assertIn(f" te_demog_ms_{key}_authority_tt:0 \"Needs @aut! [GetPlayer.MakeScope.ScriptValue("
                              f"'te_demog_ms_authority_{key}')|0] free authority to start\"", loc)
                if key != "crash_campaign":   # the campaign has no off: the pulse ends it
                    eng.press(key).at(1905)
                    eng.fixtures["authority"] = -50.0
                    if key == "birth_limit":
                        eng.vars["te_dg_ms_birth_limit_one"] = 1.0
                    self.assertTrue(eng.sgui_valid(key), "ending needs no authority")
        # the measures paid in money or bureaucracy have no such reason
        for key in set(CATALOGUE) - set(authority):
            self.assertNotIn("authority", _block(_text(MS_SGUIS), f"te_demog_ms_{key}_sgui"), key)

    def test_birth_limit_needs_the_one_childs_further_upkeep_to_tighten(self):
        eng = _MeasureEngine(law=PC, fixtures={"authority": 300.0}).press("birth_limit")
        self.assertEqual(eng.sv("te_demog_ms_authority_birth_limit_tighten"), 100)
        eng.fixtures["authority"] = 99.0
        self.assertFalse(eng.sgui_valid("birth_limit"), "100 more to tighten")
        eng.fixtures["authority"] = 100.0
        eng.press("birth_limit")
        self.assertIn("te_demog_ms_birth_limit_one", eng.modifiers)
        self.assertIn("text = te_demog_ms_birth_limit_tighten_authority_tt",
                      _block(_text(MS_SGUIS), "te_demog_ms_birth_limit_sgui"))


class TestTerm(unittest.TestCase):
    """§3.3: a five-year term from switching on, to the month."""

    def test_switching_on_stores_the_date_and_the_modifiers(self):
        eng = _MeasureEngine(law=PN, year=1900, month=3).press("child_allowance")
        self.assertAlmostEqual(eng.vars["te_dg_ms_child_allowance"], 1900.25)
        self.assertEqual(set(eng.measure_mods()), {"te_demog_ms_child_allowance", "te_demog_ms_child_allowance_cost"})
        self.assertEqual(eng.selfchecks, ["child_allowance"])
        self.assertEqual(eng.sv("te_demog_ms_until_child_allowance"), 1905)
        self.assertEqual(eng.sv("te_demog_ms_state_child_allowance"), 1)
        eng.at(1905, 2)
        self.assertFalse(eng.holds_trigger("te_demog_ms_term_run", M="child_allowance"))
        eng.at(1905, 3)
        self.assertTrue(eng.holds_trigger("te_demog_ms_term_run", M="child_allowance"))
        self.assertEqual(eng.sv("te_demog_ms_state_child_allowance"), 2)
        eng.press("child_allowance")
        self.assertEqual(eng.measure_mods(), {})
        self.assertNotIn("te_dg_ms_child_allowance", eng.vars)
        self.assertEqual(eng.sv("te_demog_ms_years_child_allowance"), -1)
        self.assertEqual(eng.sv("te_demog_ms_state_child_allowance"), 0)

    def test_birth_limit_cycles_off_two_one_off(self):
        eng = _MeasureEngine(law=PC, year=1980).press("birth_limit")
        self.assertEqual(set(eng.measure_mods()), {"te_demog_ms_birth_limit"})
        eng.at(1981).press("birth_limit")
        self.assertEqual(set(eng.measure_mods()), {"te_demog_ms_birth_limit_one"})
        self.assertEqual(eng.sv("te_demog_ms_birth_limit_one_on"), 1)
        self.assertAlmostEqual(eng.vars["te_dg_ms_birth_limit"], 1980.0, msg="the step to one child keeps the term")
        self.assertFalse(eng.sgui_valid("birth_limit"), "back to off waits for the term")
        eng.at(1985).press("birth_limit")
        self.assertEqual(eng.measure_mods(), {})
        self.assertNotIn("te_dg_ms_birth_limit_one", eng.vars)

    def test_the_rural_exemption_ends_with_birth_limit(self):
        eng = _MeasureEngine(law=PC, year=1980).press("birth_limit").press("rural_exemption")
        eng.at(1985).press("birth_limit").press("birth_limit")   # two children, one child, off
        self.assertEqual(eng.measure_mods(), {})
        self.assertNotIn("te_dg_ms_rural_exemption", eng.vars)

    def test_the_crash_campaigns_row_reads_on_until_the_pulse_ends_it(self):
        """Between its five years running out and the country's monthly pulse its code is 2: still on."""
        loc = "".join(_text(p) for p in sorted(LOC_DIR.glob("*.yml")))
        for key, want in (("te_demog_ms_crash_campaign_term", "te_demog_ms_crash_campaign_term_ends"),
                          ("te_demog_ms_crash_campaign_btn", "te_demog_ms_btn_end")):
            line = re.search(rf"(?m)^ {key}:0 \"(.*)\"$", loc).group(1)
            self.assertRegex(line, rf"'\(CFixedPoint\)2' \), '{want}'", key)
        eng = _MeasureEngine(law=PC, year=1975).press("crash_campaign").at(1980, 1)
        self.assertEqual(eng.sv("te_demog_ms_state_crash_campaign"), 2)

    def test_the_crash_campaign_runs_five_years_then_is_barred_for_ten(self):
        eng = _MeasureEngine(law=PC, year=1975, month=6).press("crash_campaign")
        self.assertFalse(eng.sgui_valid("crash_campaign"), "no press ends it")
        eng.at(1980, 5).do("te_demog_ms_monthly")
        self.assertIn("te_demog_ms_crash_campaign", eng.modifiers)
        eng.at(1980, 6).do("te_demog_ms_monthly")
        self.assertNotIn("te_demog_ms_crash_campaign", eng.modifiers)
        self.assertEqual(eng.notices, ["te_demog_ms_crash_campaign_over"])
        self.assertAlmostEqual(eng.vars["te_dg_ms_crash_campaign_end"], 1980.5)
        self.assertEqual(eng.sv("te_demog_ms_state_crash_campaign"), 3)
        self.assertEqual(eng.sv("te_demog_ms_barred_until_crash_campaign"), 1990)
        eng.at(1990, 5)
        self.assertFalse(eng.sgui_valid("crash_campaign"))
        eng.at(1990, 6)
        self.assertTrue(eng.sgui_valid("crash_campaign"))

    def test_the_monthly_end_is_full_only(self):
        eng = _MeasureEngine(law=PC, year=1975).press("crash_campaign")
        eng.trigger_fixtures["te_demog_effects_run"] = False
        eng.at(1981).do("te_demog_ms_monthly")
        self.assertIn("te_demog_ms_crash_campaign", eng.modifiers)


class TestLeavingTheLaw(unittest.TestCase):
    """§3.3: a measure the new law doesn't allow ends at once, with a notice, and its term resets."""

    def test_a_law_change_ends_what_it_doesnt_allow(self):
        eng = _MeasureEngine(law=FP, year=1960)
        for key in ("family_housing", "free_contraception", "parental_leave"):
            eng.press(key)
        eng.law = PN
        eng.at(1961).do("te_demog_ms_law_check")
        self.assertEqual(set(eng.measure_mods()), {"te_demog_ms_family_housing", "te_demog_ms_family_housing_cost"})
        self.assertEqual(sorted(eng.notices), ["te_demog_ms_ended_free_contraception",
                                               "te_demog_ms_ended_parental_leave"])
        self.assertNotIn("te_dg_ms_parental_leave", eng.vars)
        # back under a law that allows it, it starts a new term at once
        eng.law = FP
        eng.at(1962).press("parental_leave")
        self.assertAlmostEqual(eng.vars["te_dg_ms_parental_leave"], 1962.0)

    def test_a_change_of_government_ends_the_communes_measures(self):
        """on_law_activated runs the check on every law, so a party state that stops outlawing dissent loses Honours."""
        eng = _MeasureEngine(law=COMMUNAL, year=1960, others=("law_single_party_state", "law_outlawed_dissent"))
        eng.press("honours").press("family_housing")
        eng.others = {"law_single_party_state", "law_censorship"}
        eng.at(1961).do("te_demog_ms_law_check")
        self.assertEqual(eng.notices, ["te_demog_ms_ended_honours"])
        self.assertIn("te_demog_ms_family_housing", eng.modifiers)
        self.assertNotIn("te_demog_ms_honours", eng.modifiers)

    def test_birth_limit_takes_the_exemption_along(self):
        eng = _MeasureEngine(law=PC, year=1980).press("birth_limit").press("rural_exemption")
        eng.law = FP
        eng.do("te_demog_ms_law_check")
        self.assertEqual(eng.measure_mods(), {})
        self.assertEqual(eng.notices, ["te_demog_ms_ended_birth_limit"])

    def test_the_hook_is_wired_and_full_only(self):
        hooks = _text(ROOT / "common" / "on_actions" / "te_demog_on_actions.txt")
        self.assertIn("te_demog_ms_law_on_action", _block(hooks, "on_law_activated"))
        self.assertIn("te_demog_ms_law_check = yes", _block(hooks, "te_demog_ms_law_on_action"))
        eng = _MeasureEngine(law=PN, year=1960).press("child_allowance")
        eng.law, eng.trigger_fixtures["te_demog_effects_run"] = FP, False
        eng.do("te_demog_ms_law_check")
        self.assertIn("te_demog_ms_child_allowance", eng.modifiers)


class TestRevolution(unittest.TestCase):
    """§3.3: a revolution's winner inherits the variables, not the modifiers (CLAUDE.md); the yearly census puts the
    modifiers back where the law still allows the measure, and ends the rest with a notice."""

    def test_the_winner_gets_its_measures_back(self):
        eng = _MeasureEngine(law=PC, year=1985)
        eng.vars.update(te_dg_ms_birth_limit=1981.0, te_dg_ms_birth_limit_one=1.0, te_dg_ms_rural_exemption=1982.0,
                        te_dg_ms_free_contraception=1983.0, te_dg_ms_child_allowance=1980.0)
        eng.do("te_demog_ms_yearly")
        self.assertEqual(set(eng.measure_mods()), {
            "te_demog_ms_birth_limit_one", "te_demog_ms_rural_exemption", "te_demog_ms_free_contraception",
            "te_demog_ms_free_contraception_cost"})
        self.assertEqual(eng.notices, ["te_demog_ms_ended_child_allowance"])
        self.assertAlmostEqual(eng.vars["te_dg_ms_birth_limit"], 1981.0, msg="the term carries over")

    def test_a_second_year_adds_nothing_over_itself_and_refreshes_the_cost(self):
        eng = _MeasureEngine(law=PN, year=1950).press("child_allowance")
        before = eng.modifiers["te_demog_ms_child_allowance_cost"]
        eng.fixtures["gdp"] *= 2
        eng.do("te_demog_ms_yearly")   # _MeasureEngine fails an add over a held name
        self.assertAlmostEqual(eng.modifiers["te_demog_ms_child_allowance_cost"], 2 * before, places=4)

    def test_the_repair_runs_at_the_civil_war(self):
        """The house pattern (inh_repair_after_civil_war): a revolutionary winner copies the loser's variables from
        scope:te_cw_loser explicitly, keeping its own where both hold one, then puts the modifiers back."""
        hooks = _text(ROOT / "common" / "on_actions" / "te_civil_war_on_actions.txt")
        won = _block(hooks, "te_civil_war_on_won")
        self.assertLess(won.index("te_civil_war_resolve_sides = yes"), won.index("te_demog_ms_repair_after_civil_war = yes"))
        self.assertLess(won.index("te_demog_ms_repair_after_civil_war = yes"), won.index("te_civil_war_clear = yes"))
        body = _block(_text(MS_EFFECTS), "te_demog_ms_repair_after_civil_war")
        self.assertIn("te_demog_effects_run = yes", body)
        self.assertIn("var:te_cw_rebels_won = 1", body)
        for name in [f"te_dg_ms_{k}" for k in CATALOGUE] + ["te_dg_ms_birth_limit_one", "te_dg_ms_crash_campaign_end"]:
            self.assertIn(f"te_demog_ms_inherit = {{ NAME = {name} }}", body)
        self.assertLess(body.index("te_demog_ms_inherit"), body.index("te_demog_ms_keep_all = yes"))
        inherit = re.sub(r"#[^\n]*", "", _block(_text(MS_EFFECTS), "te_demog_ms_inherit"))
        self.assertIn("NOT = { has_variable = $NAME$ }", inherit)
        self.assertIn("value = scope:te_cw_loser.var:$NAME$", inherit)


class TestUpkeep(unittest.TestCase):
    """§3.4's money upkeep: a share of GDP a year, paid weekly (gdp is a year's)."""

    def test_the_weekly_cost_is_the_share_of_gdp_over_52(self):
        gdp = 52_000_000.0
        eng = _MeasureEngine(fixtures={"gdp": gdp})
        eng.vars.update(te_dg_young_share=0.15, te_dg_urban_share=0.8)
        self.assertAlmostEqual(eng.sv("te_demog_ms_cost_child_allowance"), gdp * 0.005 * 0.5 / 52, places=2)
        self.assertAlmostEqual(eng.sv("te_demog_ms_cost_family_housing"), gdp * 0.0025 * 0.8 / 52, places=2)
        self.assertAlmostEqual(eng.sv("te_demog_ms_cost_free_contraception"), gdp * 0.001 / 52, places=2)
        # the women's rate is in the game's units (2026-10-20): 0.6 of the most a rate reaches, the upkeep as before
        eng.fixtures["capital.te_demog_women_rate"] = 0.6 * P.RATE_MAX
        self.assertAlmostEqual(eng.sv("te_demog_ms_cost_parental_leave"), gdp * 0.003 * 0.6 / 52, places=2)
        eng.exists.clear()
        self.assertEqual(eng.sv("te_demog_ms_cost_parental_leave"), 0)

    def test_the_cost_modifier_takes_the_cost(self):
        eng = _MeasureEngine(law=FP, fixtures={"gdp": 52_000_000.0}).press("free_contraception")
        self.assertAlmostEqual(eng.modifiers["te_demog_ms_free_contraception_cost"], 1000.0, places=2)


class TestAI(unittest.TestCase):
    """§3.6: the laws' weights in every game; the measures' yearly pulse, where is_ai only picks whom it acts for."""

    AI = {"is_ai": True, "has_famine": False, "in_default": False, "te_demog_ms_ai_crowded": False}

    def _eng(self, law, year=1900, **fixtures):
        base = {"te_demog_ms_pop_trend": 0.01, "te_demog_ms_old_share": 0.05, "te_demog_ms_youth_share": 0.1,
                "scaled_debt": 0.0, "authority": 500.0, "government_legitimacy": 50.0, "bureaucracy": 100.0}
        return _MeasureEngine(law=law, year=year, fixtures={**base, **fixtures}, triggers=dict(self.AI))

    def test_is_ai_only_picks_whom_the_pulse_acts_for(self):
        for path in (MS_EFFECTS, MS_TRIGGERS, MS_VALUES, MS_SGUIS, MS_MODIFIERS):
            code = re.sub(r"#[^\n]*", "", _text(path))
            want = 1 if path == MS_EFFECTS else 0
            self.assertEqual(len(re.findall(r"\bis_ai\b", code)), want, path.name)
        body = _parse_script(_block(_text(MS_EFFECTS), "te_demog_ms_ai_choose"))
        self.assertEqual(len(body), 1)
        self.assertEqual(_find(body[0][2], "limit"), [("is_ai", "=", "yes")])
        # the pulse switches only through the buttons' own effects
        text = re.sub(r"#[^\n]*", "", _block(_text(MS_EFFECTS), "te_demog_ms_ai_choose")
                      + _block(_text(MS_EFFECTS), "te_demog_ms_ai_consider"))
        self.assertNotRegex(text, r"add_modifier|remove_modifier|set_variable|remove_variable")

    def test_a_player_country_is_left_alone(self):
        eng = self._eng(PN, te_demog_ms_pop_trend=-0.01)
        eng.trigger_fixtures["is_ai"] = False
        eng.do("te_demog_ms_yearly")
        self.assertEqual(eng.measure_mods(), {})

    def test_a_shrinking_country_takes_the_pro_natalist_measures(self):
        # one money measure a pulse: Child Allowance this year, Family Housing the next
        eng = self._eng(PN, te_demog_ms_pop_trend=-0.002).do("te_demog_ms_yearly")
        self.assertEqual(set(eng.measure_mods()), {
            "te_demog_ms_child_allowance", "te_demog_ms_child_allowance_cost", "te_demog_ms_honours"})
        eng.at(1901).do("te_demog_ms_yearly")
        self.assertIn("te_demog_ms_family_housing_cost", eng.modifiers)
        # near zero growth is not shrinking (the deadband): no pro-natal need
        eng = self._eng(PN, te_demog_ms_pop_trend=-0.0005).do("te_demog_ms_yearly")
        self.assertEqual(eng.measure_mods(), {})
        # far off and legitimate: Restricted Contraception too
        eng = self._eng(PN, te_demog_ms_pop_trend=-0.01, government_legitimacy=80.0).do("te_demog_ms_yearly")
        self.assertIn("te_demog_ms_restricted_contraception", eng.modifiers)

    def test_the_pulse_spends_its_authority_once(self):
        """A modifier added in the pulse isn't visible to it, so the start triggers read a local budget: a famine AI
        with 330 free authority starts Birth Limit (300) and nothing else that costs authority."""
        eng = self._eng(PC, year=1980, authority=330.0, government_legitimacy=80.0)
        eng.trigger_fixtures.update(has_famine=True, te_demog_ms_ai_crowded=True)
        eng.do("te_demog_ms_yearly")
        self.assertIn("te_demog_ms_birth_limit", eng.modifiers)
        self.assertNotIn("te_demog_ms_later_longer_fewer", eng.modifiers)
        self.assertNotIn("te_demog_ms_crash_campaign", eng.modifiers)
        spent = sum(v for k, (_, lines) in CATALOGUE.items() if f"te_demog_ms_{k}" in eng.modifiers
                    for f, v in lines.items() if f == "country_authority_cost_add")
        self.assertLessEqual(spent, 330)

    def test_the_upkeep_constants_match_the_modifiers(self):
        eng = _MeasureEngine()
        for key, (_, lines) in CATALOGUE.items():
            self.assertEqual(eng.sv(f"te_demog_ms_authority_{key}"), lines.get("country_authority_cost_add", 0), key)
            self.assertEqual(eng.sv(f"te_demog_ms_paid_{key}"), 1 if key in MONEY else 0, key)
        self.assertEqual(eng.sv("te_demog_ms_authority_birth_limit_one"), BIRTH_LIMIT_ONE["country_authority_cost_add"])
        # the row shows what Birth Limit costs at its setting: two children's, then the one child's
        eng = _MeasureEngine(law=PC)
        self.assertEqual(eng.sv("te_demog_ms_authority_birth_limit_shown"), 300)
        eng.press("birth_limit")
        self.assertEqual(eng.sv("te_demog_ms_authority_birth_limit_shown"), 300)
        eng.press("birth_limit")
        self.assertEqual(eng.sv("te_demog_ms_authority_birth_limit_shown"), 400)

    def test_authority_upkeep_rises_with_the_enforcement_a_measure_needs(self):
        """The rebalance (owner, 2026-10-16): a measure acts on every state where a decree costs 100 for one, so every
        coercive measure costs more than a decree, and the costs rise with the enforcement each needs."""
        cost = {key: lines.get("country_authority_cost_add", 0) for key, (_, lines) in CATALOGUE.items()}
        cost["birth_limit_one"] = BIRTH_LIMIT_ONE["country_authority_cost_add"]
        for key in ("restricted_contraception", "later_longer_fewer", "birth_limit", "birth_limit_one", "crash_campaign"):
            self.assertGreater(cost[key], 100, key)
        self.assertLess(cost["honours"], cost["later_longer_fewer"])
        self.assertLess(cost["later_longer_fewer"], cost["restricted_contraception"])
        self.assertLess(cost["restricted_contraception"], cost["birth_limit"])
        self.assertLess(cost["birth_limit"], cost["birth_limit_one"])
        # the panel's rows say the same
        loc = "".join(_text(p) for p in sorted(LOC_DIR.glob("*.yml")))
        for key in ("honours", "restricted_contraception", "later_longer_fewer", "crash_campaign"):
            self.assertIn(f' te_demog_ms_{key}_upkeep:0 "@aut! {cost[key]}"', loc, key)
        self.assertIn(" te_demog_ms_birth_limit_upkeep:0 \"@aut! [GetPlayer.MakeScope.ScriptValue("
                      "'te_demog_ms_authority_birth_limit_shown')|0]\"", loc)

    def test_the_one_child_needs_its_further_upkeep(self):
        """The AI tightens Birth Limit to one child only with the one child's further 100 free, and the pulse's budget
        takes it."""
        eng = self._eng(PC, year=1980, authority=400.0, government_legitimacy=80.0)
        eng.trigger_fixtures.update(has_famine=True, te_demog_ms_ai_crowded=True)
        eng.at(1980).do("te_demog_ms_yearly")
        self.assertIn("te_demog_ms_birth_limit", eng.modifiers)
        eng.fixtures["authority"] = 100.0
        eng.at(1981).do("te_demog_ms_yearly")
        self.assertNotIn("te_demog_ms_birth_limit_one", eng.modifiers, "100 free is short of the 100 and the margin")
        eng.fixtures["authority"] = 130.0
        eng.at(1982).do("te_demog_ms_yearly")
        self.assertIn("te_demog_ms_birth_limit_one", eng.modifiers)

    def test_crowding_means_half_the_people_at_the_ceiling(self):
        trigger = _block(_text(MS_TRIGGERS), "te_demog_ms_ai_crowded")
        self.assertIn("te_demog_ms_crowded_share >= 0.5", trigger)
        self.assertNotIn("has_modifier = migration_crowding", trigger)
        share = _block(_text(MS_VALUES), "te_demog_ms_crowded_share")
        self.assertIn("var:migration_crowding_mult_applied >= 4.5", share)
        eng = _MeasureEngine(fixtures={"te_demog_ms_crowded_share": 0.4})
        self.assertFalse(eng.holds_trigger("te_demog_ms_ai_crowded"))
        eng.fixtures["te_demog_ms_crowded_share"] = 0.6
        self.assertTrue(eng.holds_trigger("te_demog_ms_ai_crowded"))

    def test_debt_and_authority_hold_it_back(self):
        eng = self._eng(PN, te_demog_ms_pop_trend=-0.002, scaled_debt=0.4, authority=10.0).do("te_demog_ms_yearly")
        self.assertEqual(eng.measure_mods(), {})

    def test_a_famine_takes_population_control_and_the_term_binds(self):
        eng = self._eng(PC, year=1980, authority=1000.0)
        eng.trigger_fixtures.update(has_famine=True, te_demog_ms_ai_crowded=True)
        eng.fixtures["government_legitimacy"] = 80.0
        eng.at(1980).do("te_demog_ms_yearly")
        self.assertEqual(set(eng.measure_mods()), {
            "te_demog_ms_free_contraception", "te_demog_ms_free_contraception_cost", "te_demog_ms_sex_education",
            "te_demog_ms_later_longer_fewer", "te_demog_ms_birth_limit", "te_demog_ms_crash_campaign"})
        eng.at(1981).do("te_demog_ms_yearly")
        self.assertIn("te_demog_ms_birth_limit_one", eng.modifiers)
        # the famine ends: nothing ends before its term
        eng.trigger_fixtures.update(has_famine=False, te_demog_ms_ai_crowded=False)
        eng.at(1983).do("te_demog_ms_yearly")
        self.assertIn("te_demog_ms_free_contraception", eng.modifiers)
        eng.at(1985).do("te_demog_ms_yearly")
        self.assertEqual(set(eng.measure_mods()), {"te_demog_ms_crash_campaign"}, "the campaign ends itself, monthly")

    def test_the_laws_weigh_the_same_conditions_in_every_game(self):
        laws = _text(LAWS_FILE)
        pn = _block(laws, "law_pro_natalist_subsidies")
        pc = _block(laws, "law_population_control_measures")
        for body, triggers in ((pn, ("te_demog_ms_ai_shrinking", "te_demog_ms_ai_old", "has_famine")),
                               (pc, ("has_famine", "te_demog_ms_ai_crowded", "te_demog_ms_ai_youth",
                                     "te_demog_ms_ai_shrinking"))):
            weight = _block(body.replace("\n\t", "\n"), "ai_enact_weight_modifier")
            for trigger in triggers:
                self.assertIn(f"{trigger} = yes", weight)
            self.assertNotIn("te_demog_effects_run", weight, "every game (owner call 7)")
            self.assertNotIn("is_ai", weight)

    def test_the_walk_keeps_last_years_people(self):
        """Every game, before the yearly walk overwrites te_dg_walk_pop, and outside te_demog_walks (phase 2 step 1's
        golden pins its text)."""
        effects = _text(ROOT / "common" / "scripted_effects" / "te_demog_effects.txt")
        self.assertIn("set_variable = { name = te_dg_walk_pop_prev value = var:te_dg_walk_pop }",
                      _block(effects, "te_demog_walk_keep_prev"))
        self.assertNotIn("te_dg_walk_pop_prev", _block(effects, "te_demog_walks"))
        for body in (_block(effects, "te_demog_state_yearly"),
                     _block(_text(ROOT / "common" / "scripted_effects" / "te_demog_fast_effects.txt"),
                            "te_demog_state_clock_step")):
            self.assertLess(body.index("te_demog_walk_keep_prev = yes"), body.index("te_demog_walks = yes"))
        self.assertNotIn("te_demog_effects_run", _block(effects, "te_demog_state_yearly").split("te_demog_walks")[0])
        values = _text(MS_VALUES)
        for name in ("te_demog_ms_pop_now_sum", "te_demog_ms_pop_prev_sum"):
            self.assertIn("has_variable = te_dg_walk_pop_prev", _block(values, name))


class TestWiring(unittest.TestCase):
    def test_the_yearly_pulse_follows_the_census(self):
        hook = _block(_text(ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"),
                      "te_demog_country_yearly_on_action")
        self.assertLess(hook.index("te_demog_country_yearly = yes"), hook.index("te_demog_ms_yearly = yes"))
        self.assertIn("te_demog_ms_monthly = yes",
                      _block(_text(ROOT / "common" / "on_actions" / "te_demog_on_actions.txt"),
                             "te_demog_country_monthly_on_action"))

    def test_every_entry_point_is_full_only(self):
        effects = _text(MS_EFFECTS)
        for name in ("te_demog_ms_yearly", "te_demog_ms_monthly", "te_demog_ms_law_check",
                     "te_demog_ms_repair_after_civil_war"):
            limit = _find(_parse_script(_block(effects, name))[0][2], "limit")
            self.assertIn(("te_demog_effects_run", "=", "yes"), limit, name)
        # the buttons' is_valid starts with the wrapper (TestButtons); the AI pulse runs only from te_demog_ms_yearly
        callers = [m.group(0) for m in re.finditer(r"te_demog_ms_ai_choose = yes", effects)]
        self.assertEqual(len(callers), 1)


class TestSelfCheck(unittest.TestCase):
    def test_no_verdict_when_nothing_was_expected(self):
        """A measure ended within the week leaves an expected change near 0, where a read of 0 would pass for OK."""
        event = _block(_text(ROOT / "events" / "te_debug_demog_events.txt"), "te_debug_demog.10")
        self.assertIn("local_var:te_dg_ms_chk_size < 0.01", event)
        size = event.index("local_var:te_dg_ms_chk_size < 0.01")
        self.assertLess(size, event.index("TE_SELF_CHECK NO_VERDICT measure_country_types"))
        self.assertLess(event.index("TE_SELF_CHECK NO_VERDICT"), event.index("TE_SELF_CHECK OK measure_country_types"))
        self.assertIn("remove_global_variable = te_demog_ms_selfcheck_done", event)


class TestRelease(unittest.TestCase):
    """A release comments out every line that sets a census type (comment_out_census_inputs.py, rule 1): the measures'
    new types go, and every measure keeps its interest groups' lines, so none is emptied."""

    def test_the_release_comments_the_measures_types_out(self):
        spec = importlib.util.spec_from_file_location(
            "comment_out_census_inputs", ROOT / "scripts" / "release" / "comment_out_census_inputs.py")
        script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(script)
        with tempfile.TemporaryDirectory() as tmp:
            for rel in (script.TYPES_FILE, script.TRIGGERS, script.RULES, MS_MODIFIERS.relative_to(ROOT)):
                (Path(tmp) / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, Path(tmp) / rel)
            script.run(tmp)
            after = (Path(tmp) / MS_MODIFIERS.relative_to(ROOT)).read_text(encoding="utf-8-sig")
        census = set(NEW_TYPES) | {"state_fertility_means_add"}
        for name, body in _raw_blocks([MS_MODIFIERS]).items():
            kept = re.search(rf"^{name} = \{{(.*?)^\}}", after, re.M | re.S)
            self.assertIsNotNone(kept, f"{name} emptied and commented out whole")
            live = _lines(kept.group(1))
            self.assertFalse(census & set(live), name)
            self.assertTrue(live, name)


if __name__ == "__main__":
    unittest.main()
