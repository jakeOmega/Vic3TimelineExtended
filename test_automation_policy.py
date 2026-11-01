"""Automation Policy law group (era 13 spec § 7.1).

Static checks on the script: the default law comes first and has no gate, the
group is set for every 1836 country, Human Labor Quotas withdraws exactly the
methods the automated share counts and leaves every group a method, the share's
base is exactly the buildings those methods can run in, the two scaled
modifiers have one writer that removes them before re-adding them, the preview
lines quote the modifiers' figures, and every ideology stance names all four
laws.

Run: python3 test_automation_policy.py
"""
import glob
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

LAWS = os.path.join(REPO, "common", "laws", "te_automation_policy_laws.txt")
LAW_GROUPS = os.path.join(REPO, "common", "law_groups", "extra_law_groups.txt")
HISTORY = os.path.join(REPO, "common", "history", "extra_history.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "te_automation_policy_triggers.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_automation_policy_effects.txt")
VALUES = os.path.join(REPO, "common", "script_values", "te_automation_policy_values.txt")
MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "te_automation_policy_modifiers.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "te_automation_policy_on_actions.txt")
HAND_IDEOLOGIES = os.path.join(REPO, "common", "ideologies", "extra_ideologies.txt")
GENERATED_IDEOLOGIES = os.path.join(REPO, "common", "ideologies", "modified.txt")
LAW_CONSISTENCY = os.path.join(REPO, "gen_law_consistency.py")
LOC_DIR = os.path.join(REPO, "localization", "english")

GROUP = "lawgroup_automation_policy"
LAW_ORDER = ["law_unrestricted_automation", "law_robot_tax", "law_human_labor_quotas", "law_automation_dividend"]
QUOTAS = "law_human_labor_quotas"
TECH = "humanoid_robotics"
SCALED = ("te_automation_robot_tax", "te_automation_dividend")
# Groups whose methods form more than one ladder: the Deep-Sea Mine's capped
# methods and the uncapped ones a game rule picks between.
FAMILIES = {
    "pmg_base_building_ocean_mine": lambda pm: pm.endswith("_uncapped"),
}
# Methods allowed under the quotas although they come after a withdrawn one in
# their group, each with the reason. Empty: every later tier is withdrawn.
ALLOWED_LATER = {}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _code(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _block_from(text, start):
    depth = 0
    for j in range(start - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j]
    raise AssertionError("unbalanced braces")


def _top_level(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"no {name}"
    return _block_from(text, m.end())


def _sub(block, key):
    m = re.search(rf"(?m)^\s*{re.escape(key)} = \{{", block)
    assert m, f"no {key}"
    return _block_from(block, m.end())


def _loc_value(key):
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        m = re.search(rf'^ {re.escape(key)}:\d* "(.*)"\s*$', _read(path), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


def _number(block, field):
    m = re.search(rf"(?m)^\s*{re.escape(field)} = (-?[\d.]+)", block)
    assert m, field
    return float(m.group(1))


def _percent(fraction):
    return f"{round(abs(fraction) * 100)}%"


def _withdrawn_by_trigger():
    return re.findall(r"has_active_production_method = (\w+)",
                      _code(_top_level(_read(TRIGGERS), "te_ap_runs_automated_method")))


def _automatable_by_trigger():
    return re.findall(r"is_building_type = (\w+)", _code(_top_level(_read(TRIGGERS), "te_ap_automatable_building")))


_STATE = None


def _merged():
    """Buildings, PM groups and PMs, vanilla (the committed snapshot) under the mod."""
    global _STATE
    if _STATE is None:
        import vanilla_parsed
        from mod_state import ModState

        types = {"Buildings": "buildings", "PM Groups": "production_method_groups", "PMs": "production_methods"}
        snapshot = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed"))
        vanilla = {k: v for k, v in snapshot.data.items() if k in types}
        state = ModState({k: "" for k in types}, {k: os.path.join(REPO, "common", d) for k, d in types.items()},
                         vanilla_data=vanilla)
        _STATE = {k: {name: _body(v) for name, v in state.get_data(k).items()} for k in types}
    return _STATE


def _body(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def _names(value):
    value = _body(value)
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            item = _body(item)
            out += list(item) if isinstance(item, (list, tuple)) else [item]
        return out
    return [value]


class LawTest(unittest.TestCase):
    def test_group_is_economy(self):
        group = _top_level(_read(LAW_GROUPS), GROUP)
        self.assertIn("law_group_category = economy", group)

    def test_default_law_comes_first_with_no_gate(self):
        """The engine gives an unseeded country, and an old save, the group's
        first law in file order (scripting_best_practices.md). It is also the
        consistency walk's terminal fallback."""
        laws = _read(LAWS)
        self.assertEqual(re.findall(r"(?m)^(law_\w+) = \{", laws), LAW_ORDER)
        for law in LAW_ORDER:
            self.assertIn(f"group = {GROUP}", _top_level(laws, law))
        default = _code(_top_level(laws, LAW_ORDER[0]))
        for gate in ("unlocking_technologies", "unlocking_laws", "disallowing_laws", "can_enact"):
            self.assertNotIn(gate, default)
        others = [p for p in glob.glob(os.path.join(REPO, "common", "laws", "*.txt")) if p != LAWS]
        for p in others:
            self.assertNotIn(GROUP, _read(p), p)

    def test_humanoid_robotics_opens_the_other_three(self):
        laws = _read(LAWS)
        for law in LAW_ORDER[1:]:
            body = _top_level(laws, law)
            self.assertEqual(_sub(body, "unlocking_technologies").split(), [TECH], law)
            self.assertNotIn("unlocking_laws", body, law)

    def test_every_1836_country_starts_on_the_default(self):
        history = _read(HISTORY)
        first = _block_from(history, re.search(r"(?m)^\tevery_country = \{", history).end())
        self.assertIn(f"activate_law = law_type:{LAW_ORDER[0]}", first)

    def test_descriptions_are_flavor(self):
        """The rules are the preview's lines; a description has no figures
        (scripting_best_practices.md, "A Law's Description Is Flavor")."""
        for law in LAW_ORDER:
            desc = _loc_value(f"{law}_desc")
            self.assertNotRegex(desc, r"\d", law)
            self.assertLess(len(desc), 300, law)

    def test_the_group_is_in_the_consistency_walk(self):
        text = _read(LAW_CONSISTENCY)
        self.assertIn(f'"{GROUP}"', text[text.index("LAWGROUP_PRIORITY = ["):text.index("ATTITUDE_SCORES")])


class QuotasTest(unittest.TestCase):
    def test_the_quotas_withdraw_exactly_the_counted_methods(self):
        counted = _withdrawn_by_trigger()
        self.assertEqual(len(counted), len(set(counted)))
        gated = {name for name, pm in _merged()["PMs"].items()
                 if isinstance(pm, dict) and QUOTAS in _names(pm.get("disallowing_laws"))}
        self.assertEqual(sorted(gated), sorted(counted))

    def test_every_group_keeps_an_ungated_method(self):
        """No building is left without a method in any group."""
        state = _merged()
        withdrawn = set(_withdrawn_by_trigger())
        groups = {g for g, body in state["PM Groups"].items() if isinstance(body, dict)
                  and withdrawn & set(_names(body.get("production_methods")))}
        self.assertTrue(groups)
        for group in sorted(groups):
            methods = _names(state["PM Groups"][group].get("production_methods"))
            fallback = [m for m in methods if m not in withdrawn and isinstance(state["PMs"].get(m), dict)
                        and not any(_names(state["PMs"][m].get(k)) for k in
                                    ("unlocking_technologies", "unlocking_laws", "unlocking_production_methods"))]
            self.assertTrue(fallback, group)

    def test_the_quotas_never_move_a_building_to_a_later_method(self):
        """In each group the withdrawn methods are the top of the ladder, so a
        building leaves them for an earlier, more labor-heavy tier."""
        state = _merged()
        withdrawn = set(_withdrawn_by_trigger())
        for group, body in state["PM Groups"].items():
            if not isinstance(body, dict):
                continue
            methods = _names(body.get("production_methods"))
            if not withdrawn & set(methods):
                continue
            split = FAMILIES.get(group, lambda pm: False)
            for family in (False, True):
                ladder = [m for m in methods if split(m) == family]
                hits = [i for i, m in enumerate(ladder) if m in withdrawn]
                if hits:
                    later = [m for m in ladder[hits[0]:] if m not in withdrawn and m not in ALLOWED_LATER]
                    self.assertFalse(later, f"{group}: {later} come after a method Human Labor Quotas withdraws. "
                                            "Withdraw them too (disallowing_laws = { law_human_labor_quotas } and a "
                                            "line in te_ap_runs_automated_method), list them in ALLOWED_LATER with "
                                            "the reason, or, for a separate ladder in the same group, add the group "
                                            "to FAMILIES")

    def test_each_method_is_checked_on_the_buildings_that_can_run_it(self):
        """Vanilla pairs has_active_production_method with is_building_type;
        each block of the trigger names exactly the buildings whose groups
        hold its methods."""
        state = _merged()
        trigger = _code(_top_level(_read(TRIGGERS), "te_ap_runs_automated_method"))
        blocks = [_block_from(trigger, m.end()) for m in re.finditer(r"(?m)^\t\tAND = \{", trigger)]
        self.assertEqual(sum(len(re.findall(r"has_active_production_method", b)) for b in blocks),
                         len(re.findall(r"has_active_production_method", trigger)))
        runs_in = {}
        for building, body in state["Buildings"].items():
            if not isinstance(body, dict):
                continue
            for group in _names(body.get("production_method_groups")):
                for pm in _names((state["PM Groups"].get(group) or {}).get("production_methods")):
                    runs_in.setdefault(pm, set()).add(building)
        checked = {}
        for block in blocks:
            types = set(re.findall(r"is_building_type = (\w+)", block))
            for pm in re.findall(r"has_active_production_method = (\w+)", block):
                self.assertLessEqual(types, runs_in.get(pm, set()), pm)
                checked.setdefault(pm, set()).update(types)
        for pm, types in checked.items():
            self.assertEqual(types, runs_in[pm], pm)

    def test_the_share_counts_every_building_those_methods_run_in(self):
        state = _merged()
        withdrawn = set(_withdrawn_by_trigger())
        groups = {g for g, body in state["PM Groups"].items() if isinstance(body, dict)
                  and withdrawn & set(_names(body.get("production_methods")))}
        buildings = {b for b, body in state["Buildings"].items() if isinstance(body, dict)
                     and groups & set(_names(body.get("production_method_groups")))}
        listed = _automatable_by_trigger()
        self.assertEqual(len(listed), len(set(listed)))
        self.assertEqual(sorted(listed), sorted(buildings))


class ScaledModifierTest(unittest.TestCase):
    def test_one_writer_removes_before_it_adds(self):
        """A same-name add_modifier stacks (CLAUDE.md, "Dynamic-modifier scaling
        pattern"): the monthly update removes each modifier first, and nothing
        else adds them."""
        update = _code(_top_level(_read(EFFECTS), "te_ap_monthly_update"))
        for name in SCALED:
            removal = update.index(f"remove_modifier_if_exists_effect = {{ MODIFIER = {name} }}")
            self.assertLess(removal, update.index(f"name = {name}"), name)
        writers = []
        for path in glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True) + \
                glob.glob(os.path.join(REPO, "events", "**", "*.txt"), recursive=True):
            code = _code(_read(path))
            if any(re.search(rf"add_modifier = \{{\s*name = {name}\b", code) for name in SCALED):
                writers.append(os.path.relpath(path, REPO))
        self.assertEqual(writers, [os.path.relpath(EFFECTS, REPO)])

    def test_the_multipliers_are_persistent_variables(self):
        """The engine re-reads a multiplier later; a removed variable reads
        'none' (modifier_multiplier_var_audit)."""
        effects = _code(_read(EFFECTS))
        self.assertIn("multiplier = var:te_automation_share", effects)
        self.assertIn("multiplier = var:te_ap_dividend_scale", effects)
        for var in ("te_automation_share", "te_ap_dividend_scale"):
            self.assertNotIn(f"remove_variable = {var}", effects)

    def test_the_pulse_is_a_monthly_country_pulse(self):
        on_actions = _read(ON_ACTIONS)
        self.assertRegex(on_actions, r"on_monthly_pulse_country = \{\s*on_actions = \{\s*te_ap_country_monthly_on_action")
        self.assertIn("te_ap_monthly_update = yes", _top_level(on_actions, "te_ap_country_monthly_on_action"))

    def test_the_share_is_bounded(self):
        share = _code(_top_level(_read(VALUES), "te_ap_share_value"))
        self.assertIn("min = 0", share)
        self.assertIn("max = 1", share)
        self.assertIn("var:te_ap_automatable > 0", share)


class NumbersTest(unittest.TestCase):
    """The laws' preview lines quote the modifiers at full automation."""

    def test_robot_tax(self):
        block = _top_level(_read(MODIFIERS), "te_automation_robot_tax")
        text = _loc_value("te_ap_law_robot_tax_tt")
        self.assertIn(f"#G +{_percent(_number(block, 'state_tax_collection_mult'))}#!", text)
        self.assertIn(f"#R {_percent(_number(block, 'state_capitalists_investment_pool_contribution_add'))}#! less", text)

    def test_dividend(self):
        block = _top_level(_read(MODIFIERS), "te_automation_dividend")
        text = _loc_value("te_ap_law_dividend_tt")
        self.assertIn(f"#G +{_number(block, 'state_lower_strata_standard_of_living_add'):g}#!", text)
        self.assertIn(f"#G +{_number(block, 'state_middle_strata_standard_of_living_add'):g}#! for the", text)
        self.assertIn(f"#R {_percent(_number(block, 'state_capitalists_investment_pool_contribution_add'))}#! less", text)
        factor = re.search(r"(?m)^TE_AP_DIVIDEND_WELFARE_FACTOR = ([\d.]+)", _read(VALUES))
        self.assertEqual(float(factor.group(1)), 1.5)
        self.assertIn("Half as much again", text)
        welfare = _code(_top_level(_read(TRIGGERS), "te_ap_dividend_welfare_law"))
        for law in ("law_universal_basic_income", "law_post-scarcity"):
            self.assertIn(f"has_law = law_type:{law}", welfare)
            self.assertIn(_loc_value(law), text)


class StanceTest(unittest.TestCase):
    def test_every_list_names_the_four_laws_in_order(self):
        import ideology_modifications as im

        for name, stances in im.AUTOMATION_LISTS.items():
            self.assertEqual([law for law, _ in stances], LAW_ORDER, name)
        for ideology in im.AUTOMATION_STANCES:
            self.assertEqual([law for law, _ in im.modifications[ideology][GROUP]], LAW_ORDER, ideology)

    def test_the_trade_unions_and_the_industrialists(self):
        """The spec's poles: Trade Unions for Quotas, Industrialists for
        Unrestricted Automation."""
        import ideology_modifications as im

        def stance(ideology, law):
            return dict(im.modifications[ideology][GROUP])[law]

        for ideology in ("ideology_proletarian", "ideology_populist"):
            self.assertEqual(stance(ideology, QUOTAS), "strongly_approve", ideology)
        for ideology in ("ideology_plutocratic", "ideology_laissez_faire"):
            self.assertEqual(stance(ideology, LAW_ORDER[0]), "strongly_approve", ideology)
            self.assertEqual(stance(ideology, QUOTAS), "strongly_disapprove", ideology)

    def test_hand_written_blocks_name_every_law(self):
        text = _read(HAND_IDEOLOGIES)
        blocks = [_block_from(text, m.end()) for m in re.finditer(rf"(?m)^\t{GROUP} = \{{", text)]
        self.assertEqual(len(blocks), 2)
        for block in blocks:
            self.assertEqual(re.findall(r"(law_\w+) =", block), LAW_ORDER)

    def test_the_generated_file_is_current(self):
        import ideology_modifications as im

        generated = _read(GENERATED_IDEOLOGIES)
        self.assertEqual(generated.count(f"\t{GROUP} = {{"), len(im.AUTOMATION_STANCES))


if __name__ == "__main__":
    unittest.main()
