"""The seabed licence script against its model and its contract (Global
Commons, spec § 2).

test_seabed_allocation.py proves the model; this holds the script to it: the
constants are the same numbers, every effect the model names exists, the
yearly pass runs its steps in the model's order, the gate sits in the Deep-Sea
Mine's possible, the influence modifiers restate their script values, and the
UN hooks, the game rule and the variables keep the names the five Global
Commons branches share.
"""
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "analysis"))

import seabed_model as m  # noqa: E402

VALUES = "common/script_values/te_global_commons_seabed_values.txt"
AI_VALUES = "common/script_values/te_global_commons_seabed_ai_values.txt"
EFFECTS = "common/scripted_effects/te_global_commons_seabed_effects.txt"
TRIGGERS = "common/scripted_triggers/te_global_commons_seabed_triggers.txt"
MODIFIERS = "common/static_modifiers/te_global_commons_seabed_modifiers.txt"
TYPES = "common/modifier_type_definitions/te_global_commons_seabed_modifier_types.txt"
ON_ACTIONS = "common/on_actions/te_global_commons_seabed_on_actions.txt"
HOOK_TRIGGERS = "common/scripted_triggers/te_seabed_un_hooks.txt"
HOOK_EFFECTS = "common/scripted_effects/te_seabed_un_hooks.txt"
BUILDINGS = "common/buildings/extra_buildings.txt"
RULES = "common/game_rules/extra_game_rules.txt"


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.split("\n"))


def block(text, name):
    """The body of the top-level `name = { ... }`."""
    mt = re.search(rf"^{re.escape(name)} = \{{", text, re.M)
    assert mt, f"no {name}"
    depth, i = 0, mt.end() - 1
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[mt.end():j]
    raise AssertionError(f"unclosed {name}")


def literal(text, name):
    mt = re.search(rf"^{re.escape(name)} = (-?[\d.]+)\s*$", text, re.M)
    assert mt, f"no literal {name}"
    return float(mt.group(1))


def defined(kind_dir):
    names = set()
    for root, _, files in os.walk(os.path.join(REPO, "common", kind_dir)):
        for f in files:
            if f.endswith(".txt"):
                names |= set(re.findall(r"^(\w+) = \{", read(os.path.relpath(os.path.join(root, f), REPO)), re.M))
    return names


class ConstantsTest(unittest.TestCase):
    """The model's numbers are the script's."""

    @classmethod
    def setUpClass(cls):
        cls.values = read(VALUES)

    def test_pools(self):
        for b, pool in m.POOLS.items():
            self.assertEqual(literal(self.values, f"te_seabed_pool_{b}"), pool, b)
        # spec § 2.2
        self.assertEqual(m.POOLS, {"pacific": 300, "atlantic": 250, "indian": 200, "southern": 150, "arctic": 100})

    def test_weights(self):
        self.assertEqual(literal(self.values, "te_seabed_coast_weight"), m.COAST_WEIGHT)
        self.assertEqual(literal(self.values, "te_seabed_distant_navy_share"), m.DISTANT_NAVY_SHARE)
        self.assertEqual(literal(self.values, "te_seabed_station_weight"), m.STATION_WEIGHT)
        self.assertEqual(literal(self.values, "te_seabed_assertive_navy_mult"), m.ASSERTIVE_NAVY_MULT)
        for policy, key in ((m.SURVEY, "survey"), (m.SPONSOR, "sponsor"), (m.UNILATERAL, "unilateral")):
            self.assertEqual(literal(self.values, f"te_seabed_policy_factor_{key}"), m.POLICY_FACTOR[policy], key)

    def test_influence_modifiers_restate_their_values(self):
        mods = read(MODIFIERS)
        for key in ("sponsor", "unilateral"):
            body = block(mods, f"te_seabed_policy_{key}_cost")
            amount = float(re.search(r"country_influence_cost_add = (\d+)", body).group(1))
            self.assertEqual(amount, literal(self.values, f"te_seabed_influence_{key}"), key)
        self.assertEqual(literal(self.values, "te_seabed_influence_sponsor"), 50)
        self.assertEqual(literal(self.values, "te_seabed_influence_unilateral"), 150)

    def test_long_haul(self):
        body = block(read(MODIFIERS), "te_seabed_long_haul")
        self.assertIn("building_ocean_mine_throughput_add = -0.25", body)
        self.assertEqual(literal(self.values, "te_seabed_long_haul_penalty_pct"), 25)
        # a mod building: the engine registers no throughput type for it
        self.assertIn("building_ocean_mine_throughput_add = {", read(TYPES))

    def test_no_literal_has_six_decimals(self):
        for rel in (VALUES, AI_VALUES, EFFECTS, TRIGGERS):
            self.assertIsNone(re.search(r"\d\.\d{6,}", strip_comments(read(rel))), rel)


class ModelNamesTest(unittest.TestCase):
    """Every te_seabed_* effect, trigger or value the model's docstrings name
    exists, so the correspondence the comments claim is real."""

    def test_named_counterparts_exist(self):
        with open(os.path.join(REPO, "scripts", "analysis", "seabed_model.py"), encoding="utf-8") as f:
            model = f.read()
        named = set(re.findall(r"\b(te_seabed_[a-z_]+?)(?:_<|\b)", model))
        # variable families, not definitions
        named -= {"te_seabed_basin", "te_seabed_holder", "te_seabed_policy", "te_seabed_regime",
                  "te_seabed_lic", "te_seabed_unbuilt", "te_seabed_held", "te_seabed_w", "te_seabed_ent",
                  "te_seabed_noshare", "te_seabed_rem_res", "te_seabed_rem_open", "te_seabed_act",
                  "te_seabed_wsum_res", "te_seabed_wsum_all", "te_seabed_left", "te_seabed_pool",
                  "te_seabed_policy_factor_", "te_seabed_coast_weight", "te_seabed_distant_navy_share",
                  "te_seabed_station_weight", "te_seabed_navy_assertive_mult", "te_seabed_cap_stamped_noshare"}
        named = {n.rstrip("_") for n in named}
        everything = defined("scripted_effects") | defined("scripted_triggers") | defined("script_values")
        missing = sorted(n for n in named if n not in everything and not n.startswith("te_seabed_policy_factor"))
        self.assertEqual(missing, [])


class YearlyPassOrderTest(unittest.TestCase):
    """Model: yearly_pass. The spec's order (brief): state basins, the regime
    hook, recording, held, weights, then sharing; then stale shares off."""

    def test_order(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        steps = ["te_seabed_ensure_state_basin", "te_seabed_un_update_regime", "te_seabed_record_country",
                 "te_seabed_compute_held", "te_seabed_compute_weights", "te_seabed_share_basin = { B = pacific }",
                 "te_seabed_share_basin = { B = southern }", "te_seabed_clear_shares", "te_seabed_world_totals"]
        at = [body.index(s) for s in steps]
        self.assertEqual(at, sorted(at))
        for b in m.BASINS:
            self.assertIn(f"te_seabed_share_basin = {{ B = {b} }}", body)
            self.assertIn(f"te_seabed_world_totals = {{ B = {b} }}", body)

    def test_recording_returns_before_new_levels(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_record_country"))
        order = ["te_seabed_state_return_excess", "name = te_sb_pend value = 1", "te_seabed_state_record_new",
                 "te_seabed_state_swap_local", "name = te_seabed_holder value"]
        at = [body.index(s) for s in order]
        self.assertEqual(at, sorted(at))

    def test_water_filling_is_a_real_while(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_share_basin"))
        self.assertIn("while = {", body)
        self.assertNotIn("count =", body)

    def test_the_global_pass_runs_from_the_global_monthly_pulse(self):
        on = read(ON_ACTIONS)
        self.assertIn("te_seabed_global_monthly = yes", block(on, "te_seabed_global_monthly_on_action"))
        self.assertRegex(on, r"on_monthly_pulse = \{\s*on_actions = \{\s*te_seabed_global_monthly_on_action")
        self.assertIn("te_seabed_yearly_pass = yes", block(read(EFFECTS), "te_seabed_global_monthly"))


class ReviewFixesTest(unittest.TestCase):
    """The review's H1, M1, M2, L1 and L3 fixes, as the model has them."""

    def test_an_owners_own_shortfall_waits(self):
        """H1: the no-share fallback skips a payer flagged te_sb_pend, which
        the monthly recording sets for a state stamped by its owner and the
        owner-change hook for a holder that exists."""
        effects = strip_comments(read(EFFECTS))
        into = block(effects, "te_seabed_record_into")
        fallback = into[into.index("local_var:te_sb_n > 0\n\t\t\tNOT = { local_var:te_sb_pend = 1 }"):]
        self.assertIn("change_global_variable = { name = te_seabed_noshare_$OWN$", fallback)
        self.assertIn("var:te_seabed_holder ?= { this = scope:te_seabed_payer }", block(effects, "te_seabed_record_country"))
        hook = block(effects, "te_seabed_on_state_owner_change")
        self.assertLess(hook.index("name = te_sb_pend value = 1"), hook.index("te_seabed_state_record_new = yes"))
        self.assertIn("limit = { exists = scope:te_seabed_payer }", hook)

    def test_the_cap_check_flags_the_leak(self):
        effects = strip_comments(read(EFFECTS))
        cap = block(effects, "te_seabed_cap_check")
        for term in ("global_var:te_seabed_cap_stamped_noshare = 0", "global_var:te_seabed_cap_escaped = 0"):
            self.assertIn(term, cap)
        self.assertIn("te_seabed_cap_stamped_noshare", block(effects, "te_seabed_record_into"))

    def test_the_gates_room_reads_sit_behind_a_cheap_test(self):
        """M1: every te_seabed_room read follows te_seabed_unbuilt_total > 0 or a
        Deep-Sea Mine under construction in the state."""
        gate = strip_comments(block(read(TRIGGERS), "te_seabed_gate"))
        for at in [m_.start() for m_ in re.finditer(r"te_seabed_room [>=]", gate)]:
            before = gate[max(0, at - 260):at]
            self.assertTrue("te_seabed_unbuilt_total > 0" in before or "is_under_construction = yes" in before, before)

    def test_relations_once_a_year(self):
        """M2: a new claimant's mid-year sharing charges no relations."""
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        at = body.index("te_seabed_unilateral_relations = yes")
        guard = body.rindex("if = {", 0, at)
        self.assertIn("global_var:te_seabed_relations_year < te_history_current_year", body[guard:at])

    def test_an_unclaimed_reserved_half_joins_the_open_half(self):
        """L1, model: share_basin's fold_unclaimed."""
        effects = strip_comments(read(EFFECTS))
        self.assertIn("te_seabed_share_fold_unclaimed = { B = $B$ }", block(effects, "te_seabed_share_basin"))
        self.assertIn("te_seabed_share_fold_unclaimed = { B = $B$ }", block(effects, "te_seabed_share_round"))

    def test_a_revolutions_side_writes_no_policy(self):
        """L3."""
        self.assertIn("NOT = { is_revolutionary = yes }",
                      strip_comments(block(read(EFFECTS), "te_seabed_ai_choose_policy")))
        self.assertIn("te_seabed_reshare", strip_comments(read(ON_ACTIONS)))


class GateTest(unittest.TestCase):
    def test_the_deep_sea_mine_reads_the_gate(self):
        building = block(read(BUILDINGS), "REPLACE_OR_CREATE:building_ocean_mine")
        possible = re.search(r"possible = \{(.*?)\n\t\}", building, re.S).group(1)
        self.assertIn("is_coastal = yes", possible)
        self.assertIn("te_seabed_gate = yes", possible)

    def test_the_gate_reads_the_rule_and_no_basin(self):
        gate = strip_comments(block(read(TRIGGERS), "te_seabed_gate"))
        self.assertIn("te_global_commons_enabled = yes", gate)
        room_test = gate[:gate.index("trigger_if = {", gate.index("custom_tooltip"))]
        self.assertNotIn("te_seabed_basin", room_test)
        self.assertIn("te_seabed_room > 0", room_test)
        self.assertIn("te_seabed_unbuilt_total > 0", room_test)

    def test_room_is_unbuilt_less_unrecorded(self):
        values = strip_comments(read(VALUES))
        room = block(values, "te_seabed_room")
        self.assertIn("value = te_seabed_unbuilt_total", room)
        self.assertIn("subtract = te_seabed_unrecorded_total", room)
        self.assertIn("add = level_after_queued_constructions", block(values, "te_seabed_state_levels"))


class ContractTest(unittest.TestCase):
    """The names shared with the UN layer (te_seabed_un_hooks.txt)."""

    def test_the_hooks_are_defined(self):
        """Only that they exist: test_global_commons_un.py checks their bodies."""
        trig = read(HOOK_TRIGGERS)
        for name in ("te_seabed_reserved_half_eligible", "te_seabed_itlos_party", "te_seabed_southern_barred"):
            block(trig, name)
        eff = read(HOOK_EFFECTS)
        block(eff, "te_seabed_un_update_regime")
        block(eff, "te_seabed_un_on_policy_change")

    def test_the_hooks_are_called_where_the_contract_says(self):
        effects = strip_comments(read(EFFECTS))
        triggers = strip_comments(read(TRIGGERS))
        self.assertIn("te_seabed_reserved_half_eligible = yes", block(effects, "te_seabed_share_basin"))
        self.assertIn("te_seabed_southern_barred = yes", block(effects, "te_seabed_compute_weights"))
        self.assertIn("te_seabed_un_update_regime = yes", block(effects, "te_seabed_yearly_pass"))
        self.assertIn("te_seabed_itlos_party = yes",
                      read("common/scripted_guis/te_global_commons_seabed_sguis.txt"))
        self.assertIn("te_seabed_reserved_half_eligible", triggers + effects)

    def test_the_policy_change_calls_the_hook_after_setting_both_variables(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_set_policy"))
        at = [body.index(s) for s in ("name = te_seabed_policy_prev", "name = te_seabed_policy value = $POLICY$",
                                      "te_seabed_un_on_policy_change = yes")]
        self.assertEqual(at, sorted(at))

    def test_the_regime_and_station_are_read_as_named(self):
        everything = read(EFFECTS) + read(TRIGGERS) + read(VALUES)
        self.assertIn("global_var:te_seabed_regime", everything)
        self.assertIn("has_variable = te_antarctic_station", everything)
        for b in m.BASINS:
            self.assertIn(f"te_seabed_held_{b}", everything)

    def test_the_game_rule(self):
        rule = block(read(RULES), "global_commons_rule")
        self.assertIn("default = global_commons_enabled", rule)
        self.assertIn("flag = global_commons_enabled", rule)
        self.assertIn("flag = global_commons_disabled", rule)
        self.assertIn("has_game_rule = global_commons_enabled", block(read(TRIGGERS), "te_global_commons_enabled"))


if __name__ == "__main__":
    unittest.main()
