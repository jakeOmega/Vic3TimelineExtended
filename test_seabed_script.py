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


def english_loc():
    """Every English loc file, joined: organize_loc files a key by where it
    is used, so a test shouldn't name the file."""
    folder = os.path.join(REPO, "localization", "english")
    return "\n".join(read(os.path.join("localization", "english", f)) for f in sorted(os.listdir(folder))
                     if f.endswith(".yml"))


def defined(kind_dir):
    names = set()
    for root, _, files in os.walk(os.path.join(REPO, "common", kind_dir)):
        for f in files:
            if f.endswith(".txt"):
                names |= set(re.findall(r"^(\w+) = (?:\{|-?\d)", read(os.path.relpath(os.path.join(root, f), REPO)), re.M))
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
        self.assertEqual(literal(self.values, "te_seabed_uninc_coast"), m.UNINCORPORATED_COAST)
        self.assertEqual(literal(self.values, "te_seabed_latent_factor"), m.LATENT_FACTOR)
        for policy, key in ((m.SURVEY, "survey"), (m.SPONSOR, "sponsor"), (m.UNILATERAL, "unilateral")):
            self.assertEqual(literal(self.values, f"te_seabed_policy_factor_{key}"), m.POLICY_FACTOR[policy], key)

    def test_influence_modifiers_are_unit_modifiers(self):
        """Seabed claims spec § 2.3: the cost scales with the claims, so each
        policy modifier is a unit applied with the cost as its multiplier."""
        mods = read(MODIFIERS)
        for key in ("sponsor", "unilateral"):
            body = block(mods, f"te_seabed_policy_{key}_cost")
            self.assertEqual(re.findall(r"country_influence_cost_add = ([\d.]+)", body), ["1"], key)
        self.assertEqual(literal(self.values, "te_seabed_influence_sponsor"), 50)
        self.assertEqual(literal(self.values, "te_seabed_influence_unilateral"), 150)

    def test_long_haul(self):
        body = block(read(MODIFIERS), "te_seabed_long_haul")
        self.assertIn("building_throughput_add = -0.25", body)
        self.assertNotIn("building_ocean_mine_throughput_add", body)
        self.assertEqual(literal(self.values, "te_seabed_long_haul_penalty_pct"), 25)
        # a mod building: the engine registers no throughput type for it (kept
        # for the blockade fallback)
        self.assertIn("building_ocean_mine_throughput_add = {", read(TYPES))

    def test_long_haul_sits_on_the_building(self):
        """On the state's Deep-Sea Mine, from the state pulse: a building has no
        variables, so the multiplier is a state variable read through root, and
        it is never removed; the state's own copy (an older save's) comes off."""
        body = strip_comments(block(read(EFFECTS), "te_seabed_refresh_long_haul"))
        walk = body[body.index("every_scope_building"):]
        self.assertLess(body.index("remove_modifier = te_seabed_long_haul"), body.index("every_scope_building"))
        self.assertIn("name = te_seabed_long_haul_x value = te_seabed_long_haul_mult", body[:body.index("every_scope_building")])
        self.assertIn("is_building_type = building_ocean_mine", walk)
        self.assertLess(walk.index("remove_modifier = te_seabed_long_haul"), walk.index("add_modifier"))
        self.assertIn("multiplier = root.var:te_seabed_long_haul_x", walk)
        self.assertNotIn("remove_variable = te_seabed_long_haul_x", strip_comments(read(EFFECTS)))

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
                  "te_seabed_station_weight", "te_seabed_navy_assertive_mult", "te_seabed_cap_stamped_noshare",
                  "te_seabed_floor", "te_seabed_fz", "te_seabed_pass_year", "te_seabed_reshare", "te_seabed_relinq",
                  "te_seabed_dr", "te_seabed_need_navy", "te_seabed_queued", "te_seabed_fprot",
                  "te_seabed_sh", "te_seabed_lease_src", "te_seabed_lease_n", "te_seabed_lease_built",
                  "te_seabed_lease_unused", "te_seabed_subj_unused", "te_seabed_pass_built",
                  "te_seabed_pass_unused", "te_seabed_own_claims", "te_seabed_lease_past",
                  "te_seabed_pass_to", "te_seabed_part", "te_seabed_wait"}
        named = {n.rstrip("_") for n in named}
        everything = (defined("scripted_effects") | defined("scripted_triggers") | defined("script_values")
                      | defined("diplomatic_actions"))
        missing = sorted(n for n in named if n not in everything and not n.startswith("te_seabed_policy_factor"))
        self.assertEqual(missing, [])


class UnincorporatedCoastTest(unittest.TestCase):
    """Seabed claims spec § 5.1 (model: compute_weights' _coast): every coastal
    state counts toward the coast term and the navy's spread, unincorporated
    ones at te_seabed_uninc_coast; ports count in full."""

    def test_the_walk_takes_every_coastal_state(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_compute_weights"))
        self.assertNotIn("is_incorporated = yes", body)
        self.assertIn("te_seabed_uninc_coast", body)

    def test_the_tally_counts_unincorporated_at_half(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_weight_tally"))
        self.assertIn("add = local_var:te_sb_wc", body)
        self.assertIn("te_sb_ws_$B$", body)               # every coastal state, for the Build-in hover (review I4)
        walk = strip_comments(block(read(EFFECTS), "te_seabed_compute_weights"))
        self.assertIn("change_local_variable = { name = te_sb_wn_all add = local_var:te_sb_wc }", walk)

    def test_the_build_in_hover_lists_every_coastal_state(self):
        """Review I4: a level in an unincorporated coastal state of its own basin
        works at full throughput (the mine has no incorporation test, long-haul
        goes by basin), so the Free hover lists every coastal state there and
        counts them all."""
        values = read(VALUES)
        for b in m.BASINS:
            self.assertIn(f"te_seabed_coast_states_{b}", block(values, f"te_seabed_build_more_{b}"))
        effects = strip_comments(read(EFFECTS))
        for name in ("te_seabed_build_in_list", "te_seabed_build_in_slot"):
            self.assertNotIn("is_incorporated", block(effects, name), name)
        self.assertIn("change_local_variable = { name = te_sb_ws_$B$ add = 1 }", block(effects, "te_seabed_weight_tally"))
        loc = english_loc()
        for b in m.BASINS:
            line = re.search(rf"(?m)^ te_seabed_build_in_none_{b}:0 \"(.*)\"$", loc).group(1)
            self.assertNotIn("incorporated", line)

    def test_counted_coast_shows_a_decimal(self):
        loc = english_loc()
        for b in m.BASINS:
            line = re.search(rf"(?m)^ te_seabed_weight_home_{b}:0 \"(.*)\"$", loc).group(1)
            self.assertIn(f"ScriptValue('te_seabed_coast_disp_{b}')|1]", line)
            self.assertNotIn(f"ScriptValue('te_seabed_coast_disp_{b}')|0]", line)
        how = re.search(r"(?m)^ te_seabed_how_weight:0 \"(.*)\"$", loc).group(1)
        self.assertIn("unincorporated", how)


class YearlyPassOrderTest(unittest.TestCase):
    """Model: yearly_pass. The spec's order (brief): state basins, the regime
    hook, recording, held, weights, then sharing; then stale shares off."""

    def test_order(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        steps = ["te_seabed_ensure_state_basin", "te_seabed_un_update_regime", "te_seabed_record_country",
                 "te_seabed_compute_held", "te_seabed_set_floors", "te_seabed_compute_weights",
                 "te_seabed_fit_floors = { B = pacific }", "te_seabed_share_basin = { B = pacific }",
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


class WaitingShareScriptTest(unittest.TestCase):
    """Model: yearly_pass's waiting countries (the model's header, "countries
    without the technology"): every coastal country is weighed, one without
    Abyssal Plain Mining at te_seabed_latent_factor, and its share above its
    holdings waits in te_seabed_wait_<basin> with no claims."""

    @classmethod
    def setUpClass(cls):
        cls.effects = strip_comments(read(EFFECTS))
        cls.values = strip_comments(read(VALUES))
        cls.passbody = block(cls.effects, "te_seabed_yearly_pass")

    def test_the_waiting_trigger_is_the_models(self):
        body = strip_comments(block(read(TRIGGERS), "te_seabed_waits"))
        self.assertIn("any_scope_state = { is_coastal = yes }", body)
        self.assertIn("NOT = { te_seabed_takes_part = yes }", body)

    def test_the_factor(self):
        body = block(self.values, "te_seabed_claim_factor")
        self.assertIn("value = te_seabed_latent_factor", body)
        self.assertIn("has_technology_researched = abyssal_plain_mining", body)
        self.assertIn("value = te_seabed_policy_factor", body)
        self.assertIn("value = te_seabed_claim_factor", block(self.effects, "te_seabed_compute_weights"))
        self.assertNotIn("te_seabed_policy_factor", block(self.effects, "te_seabed_compute_weights"))

    def test_the_pass_weighs_every_coastal_country(self):
        body = self.passbody
        basins = body[:body.index("te_seabed_ensure_state_basin")]
        self.assertIn("any_scope_state = { is_coastal = yes }", basins)
        self.assertNotIn("te_seabed_takes_part", basins)
        self.assertNotIn("te_seabed_zero_weights", body)
        order = ["set_variable = te_seabed_part", "te_seabed_waits = yes", "set_variable = te_seabed_wpart",
                 "te_seabed_compute_weights = yes", "te_seabed_wait_weights = yes",
                 "te_seabed_fit_floors = { B = pacific }", "te_seabed_clear_waits = yes",
                 "remove_variable = te_seabed_wpart", "te_seabed_world_totals = { B = pacific }"]
        at = [body.index(s) for s in order]
        self.assertEqual(at, sorted(at))

    def test_waiting_countries_hold_nothing_and_freeze_at_nothing(self):
        body = block(self.effects, "te_seabed_wait_reset")
        for var in ("te_seabed_sh_$B$", "te_seabed_fz_$B$"):
            self.assertIn(f"set_variable = {{ name = {var} value = 0 }}", body)
        self.assertIn("te_seabed_compute_weights = yes", block(self.effects, "te_seabed_wait_weights"))

    def test_the_sharing_takes_them_in_and_gives_them_no_claims(self):
        share = block(self.effects, "te_seabed_share_basin")
        self.assertIn("has_variable = te_seabed_wpart", share[:share.index("set_variable = te_seabed_act_$B$")])
        rnd = block(self.effects, "te_seabed_share_round")
        final = rnd[rnd.index("te_seabed_readout = { B = $B$ }"):]
        self.assertIn("has_variable = te_seabed_wpart", final)
        wait_at = final.index("name = te_seabed_wait_$B$")
        self.assertLess(final.index("has_technology_researched = abyssal_plain_mining"), wait_at)
        self.assertLess(wait_at, final.index("max = var:te_seabed_sh_$B$"))
        self.assertLess(final.index("max = var:te_seabed_sh_$B$"), final.index("name = te_seabed_unbuilt_$B$"))
        self.assertIn("remove_variable = te_seabed_act_$B$", final)

    def test_world_totals_count_the_waiting(self):
        body = block(self.effects, "te_seabed_world_totals")
        self.assertIn("name = te_seabed_world_wait_$B$ add = var:te_seabed_wait_$B$", body)
        self.assertIn("name = te_seabed_world_w_$B$ add = var:te_seabed_w_$B$", body[body.index("te_seabed_world_wait_$B$ add"):])
        for b in m.BASINS:
            self.assertIn(f"subtract = te_seabed_wait_world_disp_{b}", block(self.values, f"te_seabed_rival_claims_{b}"))


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


class FloorScriptTest(unittest.TestCase):
    """Model: set_floors, fit_floors, floor_in_force (seabed claims spec § 2.2)."""

    def test_constant(self):
        self.assertEqual(literal(read(VALUES), "te_seabed_floor_keep"), m.FLOOR_KEEP)

    def test_pass_order(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        order = ["te_seabed_first_of_year", "te_seabed_record_country",
                 "te_seabed_compute_held", "te_seabed_set_floors", "te_seabed_compute_weights",
                 "te_seabed_fit_floors = { B = pacific }", "te_seabed_share_basin = { B = pacific }"]
        at = [body.index(s) for s in order]
        self.assertEqual(at, sorted(at))
        for b in m.BASINS:
            self.assertLess(body.index(f"te_seabed_fit_floors = {{ B = {b} }}"),
                            body.index(f"te_seabed_share_basin = {{ B = {b} }}"), b)

    def test_floors_are_set_only_at_the_years_first_sharing(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        self.assertLess(body.index("te_seabed_first_sharing_of_year = yes"), body.index("name = te_seabed_pass_year"))
        at = body.index("te_seabed_set_floors = yes")
        guard = body.rindex("if = {", 0, at)
        self.assertIn("has_global_variable = te_seabed_first_of_year", body[guard:at])
        trig = strip_comments(block(read(TRIGGERS), "te_seabed_first_sharing_of_year"))
        self.assertIn("global_var:te_seabed_pass_year < te_history_current_year", trig)

    def test_freeze_reads_the_floor(self):
        share = strip_comments(block(read(EFFECTS), "te_seabed_share_basin"))
        self.assertIn("var:te_seabed_fz_$B$ >= var:te_seabed_e_$B$", share)
        self.assertNotIn("var:te_seabed_held_$B$ >= var:te_seabed_e_$B$", share)
        freeze = strip_comments(block(read(EFFECTS), "te_seabed_share_freeze"))
        self.assertNotIn("te_seabed_held_$B$", freeze)
        rnd = strip_comments(block(read(EFFECTS), "te_seabed_share_round"))
        self.assertIn("set_variable = { name = te_seabed_ent_$B$ value = var:te_seabed_fz_$B$ }", rnd)
        self.assertIn("var:te_seabed_ent_$B$ > var:te_seabed_fz_$B$", rnd)
        # unbuilt stays entitlement less holdings, as the sharing counts them
        # (after the leases' shift, seabed_model.share_held)
        self.assertIn("subtract = var:te_seabed_sh_$B$", rnd)

    def test_scramble_and_bar(self):
        floors = strip_comments(block(read(EFFECTS), "te_seabed_set_floors"))
        self.assertIn("te_seabed_regime_scramble", floors)
        self.assertIn("te_seabed_southern_barred", floors)
        self.assertIn("te_seabed_is_claimant", floors)
        triggers = strip_comments(read(TRIGGERS))
        void = block(triggers, "te_seabed_floor_void")
        for term in ("te_seabed_policy_sponsor", "te_seabed_regime_scramble", "te_seabed_is_claimant"):
            self.assertIn(term, void)
        self.assertIn("te_seabed_southern_barred = yes", block(triggers, "te_seabed_floor_void_southern"))
        for b in m.BASINS:
            self.assertIn("te_seabed_floor_void = yes", block(triggers, f"te_seabed_floor_void_{b}"))

    def test_fit_floors_scales_protected_parts(self):
        fit = strip_comments(block(read(EFFECTS), "te_seabed_fit_floors"))
        self.assertIn("te_seabed_floor_void_$B$ = yes", fit)
        self.assertIn("divide = global_var:te_seabed_fz_prot_$B$", fit)
        self.assertIn("floor = yes", fit)
        self.assertIn("change_variable = { name = te_seabed_fz_$B$ add = var:te_seabed_sh_$B$ }", fit)

    def test_every_participant_gets_a_fresh_frozen_amount(self):
        """Review C1: te_seabed_share_round gives a participant outside the
        basin's set its te_seabed_fz_<b> as entitlement, so every participant's
        is written each pass, 0 outside the set (the model's ent.get(cid, 0))."""
        fit = strip_comments(block(read(EFFECTS), "te_seabed_fit_floors"))
        first = fit.index("every_country = {")
        self.assertRegex(fit[first:first + 200], r"every_country = \{\s*limit = \{ has_variable = te_seabed_part \}\s*"
                                                  r"set_variable = \{ name = te_seabed_fz_\$B\$ value = 0 \}")

    def test_the_floor_protects_claims_not_lost_licences(self):
        """Review I3: frozen at max(held, min(floor, held + January's protected part))."""
        effects = strip_comments(read(EFFECTS))
        self.assertIn("name = te_seabed_fprot_$B$", block(effects, "te_seabed_set_floor"))
        fit = block(effects, "te_seabed_fit_floors")
        self.assertIn("var:te_seabed_fprot_$B$", fit)
        self.assertIn("name = te_seabed_fprot_$B$ value = 0", block(effects, "te_seabed_relinquish"))
        self.assertIn("name = te_seabed_fprot_$B$ value = 0", block(effects, "te_seabed_clear_floor"))

    def test_clear_share_clears_the_floor(self):
        effects = read(EFFECTS)
        self.assertIn("te_seabed_clear_floor = { B = $B$ }", block(effects, "te_seabed_clear_share"))
        floor = block(effects, "te_seabed_clear_floor")
        for name in ("te_seabed_floor_$B$", "te_seabed_fprot_$B$"):
            self.assertIn(f"name = {name} value = 0", floor)

    def test_self_check(self):
        effects = strip_comments(read(EFFECTS))
        check = block(effects, "te_seabed_floor_check")
        self.assertIn("TE_SELF_CHECK OK seabed_floor_fits", check)
        self.assertIn("TE_SELF_CHECK BROKEN seabed_floor_fits", check)
        self.assertIn("te_seabed_floor_check = yes", block(effects, "te_seabed_yearly_pass"))


class RelinquishScriptTest(unittest.TestCase):
    """Model: relinquish, claim_again (seabed claims spec § 2.5)."""

    SGUIS = "common/scripted_guis/te_global_commons_seabed_sguis.txt"

    def test_relinquish_never_reshares(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_relinquish"))
        self.assertIn("te_seabed_relinq_$B$", body)
        self.assertIn("set_variable = { name = te_seabed_unbuilt_$B$ value = 0 }", body)
        self.assertIn("set_variable = { name = te_seabed_floor_$B$ value = 0 }", body)
        self.assertNotIn("te_seabed_reshare", body)
        self.assertIn("remove_variable = te_seabed_relinq_$B$", strip_comments(block(read(EFFECTS), "te_seabed_claim_again")))

    def test_relinquish_records_first(self):
        """Review I1: levels queued since the last recording take their licences
        before the claims go."""
        body = strip_comments(block(read(EFFECTS), "te_seabed_relinquish"))
        self.assertLess(body.index("te_seabed_record_country = yes"),
                        body.index("set_variable = { name = te_seabed_unbuilt_$B$ value = 0 }"))

    def test_weight_is_zero_while_relinquished(self):
        effects = strip_comments(read(EFFECTS))
        self.assertIn("te_seabed_relinq_$B$", block(effects, "te_seabed_weight_set"))
        weights = block(effects, "te_seabed_compute_weights")
        station = weights[weights.index("has_variable = te_antarctic_station") - 120:weights.index("te_seabed_station_weight")]
        self.assertIn("te_seabed_relinq_southern", station)

    def test_buttons(self):
        sguis = strip_comments(read(self.SGUIS))
        for b in m.BASINS:
            rel = block(sguis, f"te_seabed_relinquish_{b}_sgui")
            again = block(sguis, f"te_seabed_claim_again_{b}_sgui")
            self.assertIn(f"te_seabed_relinquish = {{ B = {b} }}", rel)
            self.assertIn(f"te_seabed_claim_again = {{ B = {b} }}", again)
            for body in (rel, again):
                self.assertIn("ai_is_valid = { always = no }", body)
            self.assertIn(f"te_seabed_unbuilt_{b} > 0", rel)
            self.assertIn(f"has_variable = te_seabed_relinq_{b}", again)

    def test_loc(self):
        loc = english_loc()
        for key in ("te_seabed_relinquish_btn", "te_seabed_claim_again_btn", "te_seabed_relinquish_tt",
                    "te_seabed_claim_again_tt", "te_seabed_relinquish_has_claims_tt", "te_seabed_claim_again_relinquished_tt"):
            self.assertIn(f" {key}:", loc)


class FeeScriptTest(unittest.TestCase):
    """Model: take_snapshots, fee_base_state, fee_base (seabed claims spec § 2.1)."""

    UN_VALUES = "common/script_values/te_global_commons_un_values.txt"

    def test_rate(self):
        self.assertEqual(literal(read(VALUES), "te_seabed_fee_rate"), m.FEE_RATE)
        self.assertEqual(m.FEE_RATE, 0.02)

    def test_base_is_the_smallest_of_now_and_two_snapshots(self):
        values = strip_comments(read(VALUES))
        state = block(values, "te_seabed_state_fee_base")
        for v in ("te_seabed_unb_snap1", "te_seabed_unb_snap2", "te_seabed_state_unbuilt_lic"):
            self.assertIn(v, state)
        self.assertIn("min = 0", state)
        lic = block(values, "te_seabed_state_unbuilt_lic")
        self.assertIn("subtract = te_seabed_state_built_levels", lic)
        self.assertIn("max = te_seabed_state_queued_levels", lic)
        self.assertIn("add = level\n", block(values, "te_seabed_state_built_levels"))
        self.assertIn("te_seabed_state_fee_base", block(values, "te_seabed_fee_base"))
        weekly = block(values, "te_seabed_fee_weekly_value")
        for v in ("te_seabed_fee_base", "te_seabed_level_output_value", "te_seabed_fee_rate"):
            self.assertIn(v, weekly)

    def test_snapshots_at_the_years_first_sharing_after_recording(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        at = body.index("te_seabed_take_snapshots = yes")
        self.assertLess(body.index("te_seabed_record_country"), at)
        self.assertLess(at, body.index("te_seabed_compute_held"))
        guard = body.rindex("if = {", 0, at)
        self.assertIn("has_global_variable = te_seabed_first_of_year", body[guard:at])
        snap = strip_comments(block(read(EFFECTS), "te_seabed_take_snapshots"))
        self.assertLess(snap.index("name = te_seabed_unb_snap2"), snap.index("name = te_seabed_unb_snap1"))

    def test_one_refresh_site(self):
        effects = strip_comments(read(EFFECTS))
        self.assertEqual(effects.count("name = te_seabed_holding_fee_modifier"), 1)
        self.assertIn("multiplier = var:te_seabed_fee_cached", block(effects, "te_seabed_fee_refresh"))
        monthly = block(effects, "te_seabed_monthly_country")
        self.assertEqual(monthly.count("te_seabed_fee_refresh = yes"), 2)     # with the rule off it comes off

    def test_the_modifier_and_its_breakdown_category(self):
        body = block(read(MODIFIERS), "te_seabed_holding_fee_modifier")
        self.assertIn("country_expenses_add = 1", body)
        self.assertIn("country_te_budget_expense_un_add = 1", body)
        with open(os.path.join(REPO, "scripts", "generators", "gen_budget_breakdown.py"), encoding="utf-8") as f:
            self.assertIn('"te_seabed_holding_fee_modifier"', f.read())

    def test_fee_joins_royalties_under_regulation(self):
        total = strip_comments(block(read(self.UN_VALUES), "te_seabed_royalties_total_value"))
        self.assertIn("te_seabed_fee_cached", total)
        fee = total[total.index("te_seabed_holding_fee_modifier") - 300:]
        self.assertIn("te_seabed_regime_is_regulated = yes", fee)
        self.assertIn("te_seabed_itlos_party = yes", fee)

    def test_loc_states_the_rate(self):
        loc = english_loc()
        self.assertIn(" te_seabed_holding_fee_modifier:", loc)
        desc = re.search(r'^ te_seabed_holding_fee_modifier_desc:0 "(.*)"$', loc, re.M).group(1)
        self.assertIn(f"{m.FEE_RATE * 100:g}% of a level's base output value a week", desc)


class LockTest(unittest.TestCase):
    """Sponsor's scaled cost, the five-year lock and its carve-outs (seabed
    claims spec §§ 2.3-2.4)."""

    def test_constants(self):
        v = read(VALUES)
        self.assertEqual(literal(v, "te_seabed_influence_sponsor"), 50)
        self.assertEqual(literal(v, "te_seabed_influence_per_claim"), 0.5)
        self.assertEqual(literal(v, "te_seabed_unilateral_cost_mult"), 1.5)
        self.assertEqual(literal(v, "te_seabed_influence_unilateral"), 150)
        self.assertEqual(literal(v, "te_seabed_policy_lock_months"), 60)

    def test_cost_formulas(self):
        v = strip_comments(read(VALUES))
        sponsor = block(v, "te_seabed_sponsor_cost_value")
        for term in ("te_seabed_influence_sponsor", "te_seabed_influence_per_claim", "te_seabed_protected_claims"):
            self.assertIn(term, sponsor)
        uni = block(v, "te_seabed_unilateral_cost_value")
        for term in ("te_seabed_sponsor_cost_value", "multiply = te_seabed_unilateral_cost_mult",
                     "min = te_seabed_influence_unilateral"):
            self.assertIn(term, uni)

    def test_costs_are_unit_modifiers_with_a_multiplier(self):
        mods = read(MODIFIERS)
        for key in ("sponsor", "unilateral"):
            self.assertIn("country_influence_cost_add = 1", block(mods, f"te_seabed_policy_{key}_cost"))
        refresh = strip_comments(block(read(EFFECTS), "te_seabed_refresh_policy_cost"))
        self.assertIn("value = te_seabed_sponsor_cost_value", refresh)
        self.assertIn("value = te_seabed_unilateral_cost_value", refresh)
        self.assertEqual(refresh.count("multiplier = var:te_seabed_policy_cost_cached"), 2)
        effects = strip_comments(read(EFFECTS))
        for key in ("sponsor", "unilateral"):
            self.assertEqual(effects.count(f"name = te_seabed_policy_{key}_cost"), 1, key)

    def test_the_cost_follows_the_claims_monthly(self):
        check = strip_comments(block(read(EFFECTS), "te_seabed_policy_cost_check"))
        self.assertIn("te_seabed_policy_cost_cached", check)
        self.assertIn("te_seabed_policy_cost_value", check)

    def test_set_policy_stamps_the_change(self):
        self.assertIn("name = te_seabed_policy_changed value = te_history_month_index",
                      block(read(EFFECTS), "te_seabed_set_policy"))

    def test_the_forced_reset_leaves_the_lock_off(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        at = body.index("te_seabed_set_policy = { POLICY = 1 }")
        self.assertIn("remove_variable = te_seabed_policy_changed", body[at:at + 200])

    def test_buttons_obey_the_lock_and_carve_outs(self):
        t = strip_comments(read(TRIGGERS))
        self.assertIn("te_seabed_policy_locked", block(t, "te_seabed_can_choose_sponsor"))
        self.assertIn("te_seabed_unilateral_answer_open", block(t, "te_seabed_can_choose_unilateral"))
        self.assertIn("te_seabed_influence_deficit", block(t, "te_seabed_can_choose_survey"))
        self.assertIn("influence >= te_seabed_sponsor_cost_value", block(t, "te_seabed_can_choose_sponsor"))
        self.assertIn("influence >= te_seabed_unilateral_cost_value", block(t, "te_seabed_can_choose_unilateral"))
        self.assertIn("influence < 0", block(t, "te_seabed_influence_deficit"))
        answer = block(t, "te_seabed_unilateral_answer_open")
        self.assertIn("te_seabed_policy_unilateral = yes", answer)
        self.assertIn("var:te_seabed_policy_changed > root.var:te_seabed_policy_changed", answer)
        self.assertIn("te_seabed_shares_home_basin_with_root = yes", answer)

    def test_ai_obeys_the_lock(self):
        body = block(read(EFFECTS), "te_seabed_ai_choose_policy")
        for policy in ("survey", "sponsor", "unilateral"):
            self.assertIn(f"te_seabed_can_choose_{policy} = yes", body)

    def test_loc_states_the_lock(self):
        years = literal(read(VALUES), "te_seabed_policy_lock_months") / 12
        loc = english_loc()
        for key in ("te_seabed_policy_effect_2_tt", "te_seabed_policy_effect_3_tt"):
            text = re.search(rf'^ {key}:0 "(.*)"$', loc, re.M).group(1)
            self.assertIn(f"holds for #v {years:g}#! years", text, key)
        for key in ("te_seabed_policy_locked_tt", "te_seabed_policy_answer_tt", "te_seabed_policy_deficit_tt"):
            self.assertIn(f" {key}:", loc)

    def test_no_change_date_is_unlocked(self):
        body = strip_comments(block(read(TRIGGERS), "te_seabed_policy_locked"))
        self.assertIn("has_variable = te_seabed_policy_changed", body)
        self.assertIn("te_seabed_policy_unlock_month_value > te_history_month_index", body)


class PanelDataTest(unittest.TestCase):
    """The panel's figures (seabed claims spec § 3): the readout, the rankings,
    queued licences per basin and the pool bar."""

    SGUIS = "common/scripted_guis/te_global_commons_seabed_sguis.txt"

    def test_readout_written_before_active_flags_go(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_share_round"))
        self.assertLess(body.index("te_seabed_readout = { B = $B$ }"), body.index("remove_variable = te_seabed_act_$B$"))

    def test_readout_follows_the_model(self):
        """Model: need_weight and need_navy: t = entitlement + 1 (frozen: what it
        is frozen at + 1, its holdings back in the halves they came off), the
        deficit form per half, "full" below the model's threshold, navy rounded
        up; -1 full, -2 no weight here."""
        ro = strip_comments(block(read(EFFECTS), "te_seabed_readout"))
        for term in ("var:te_seabed_ent_$B$", "var:te_seabed_fz_$B$", "te_seabed_dr_$B$",
                     "global_var:te_seabed_rem_open_$B$", "global_var:te_seabed_wsum_all_$B$",
                     "global_var:te_seabed_rem_res_$B$", "global_var:te_seabed_wsum_res_$B$",
                     "has_variable = te_seabed_rsv_$B$", "ceiling = yes",
                     "te_seabed_distant_navy_share", "var:te_seabed_coast_$B$", "var:te_seabed_coast_all",
                     "te_seabed_claim_factor", "te_seabed_assertive_navy_mult"):
            self.assertIn(term, ro)
        self.assertIn(f"> {m.READOUT_FULL_BELOW}", ro)
        self.assertIn("name = te_seabed_need_navy_$B$ value = -1", ro)
        self.assertIn("name = te_seabed_need_navy_$B$ value = -2", ro)
        self.assertIn("name = te_seabed_dr_$B$", strip_comments(block(read(EFFECTS), "te_seabed_share_freeze")))
        ws = strip_comments(block(read(EFFECTS), "te_seabed_weight_set"))
        self.assertIn("name = te_seabed_coast_$B$", ws)
        self.assertIn("name = te_seabed_coast_all", strip_comments(block(read(EFFECTS), "te_seabed_compute_weights")))

    def test_ranks_every_basin(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        for b in m.BASINS:
            self.assertIn(f"te_seabed_rank_basin = {{ B = {b} }}", body)
        self.assertIn("name = te_seabed_last_sharing_month value = te_history_month_index", body)

    def test_rank_flags_go_through_the_capital(self):
        rank = strip_comments(block(read(EFFECTS), "te_seabed_rank_basin"))
        self.assertIn("order_by = te_seabed_ent_value_$B$", rank)
        self.assertIn("remove_global_variable = te_seabed_rk_$B$_6", rank)
        self.assertIn("name = te_seabed_rk_more_$B$", rank)
        self.assertIn("is_player = yes", rank)
        seat = strip_comments(block(read(EFFECTS), "te_seabed_rank_seat"))
        self.assertIn("te_seabed_rkcap_$B$_$N$", seat)
        self.assertIn("capital = { save_scope_as = te_seabed_rank_capital }", seat)
        self.assertIn("name = te_seabed_rkcap_count_$B$", seat)

    def test_rival_row_follows_the_leaderboard_pattern(self):
        body = block(read(self.SGUIS), "te_seabed_rival_row_sgui")
        self.assertIn("saved_scopes = { op }", body)
        self.assertIn("custom_tooltip_no_bullet", body)
        self.assertIn("?=", body)
        for i, b in enumerate(m.BASINS, 1):
            for n in range(1, 7):
                self.assertIn(f"scope:op = {10 * i + n} }}", body)
                self.assertIn(f"global_var:te_seabed_rk_{b}_{n} ?= {{ custom_tooltip_no_bullet = te_seabed_rival_row_{b} }}", body)

    def test_our_own_slot_is_not_a_rival(self):
        """Review I2: the viewer shows once, in its own row: its ranked slot is
        hidden, and "and N others" leaves it out when it ranks below six."""
        body = block(read(self.SGUIS), "te_seabed_rival_row_sgui")
        for b in m.BASINS:
            for n in range(1, 7):
                self.assertIn(f"NOT = {{ global_var:te_seabed_rk_{b}_{n} = {{ this = root }} }}", body)
        rank = strip_comments(block(read(EFFECTS), "te_seabed_rank_basin"))
        self.assertIn("name = te_seabed_rank_$B$ value = global_var:te_seabed_rk_idx", rank)
        for b in m.BASINS:
            more = strip_comments(block(read(VALUES), f"te_seabed_rk_more_disp_{b}"))
            self.assertIn(f"var:te_seabed_rank_{b} > 6", more)
            self.assertIn("subtract = 1", more)

    def test_bar_values_exist(self):
        v = strip_comments(read(VALUES))
        for b in m.BASINS:
            for k in (1, 2, 3, 4):
                body = block(v, f"te_seabed_bar_{b}_{k}")
                self.assertIn("max = 1", body)
                self.assertIn("min = 0", body)
            self.assertIn(f"te_seabed_queued_disp_{b}", block(v, f"te_seabed_bar_{b}_1"))
            self.assertIn(f"te_seabed_rival_lic_{b}", block(v, f"te_seabed_bar_{b}_4"))
            for name in (f"te_seabed_weight_pct_disp_{b}", f"te_seabed_ent_value_{b}", f"te_seabed_need_navy_disp_{b}",
                         f"te_seabed_jan_loss_{b}", f"te_seabed_queued_disp_{b}", f"te_seabed_our_lic_{b}",
                         f"te_seabed_bar_pool_{b}", f"te_seabed_rival_lic_{b}"):
                block(v, name)
        for name in ("te_seabed_jan_loss_disp", "te_seabed_asof_year_disp", "te_seabed_asof_month_disp"):
            block(v, name)

    def test_jan_loss_is_what_the_floor_leaves(self):
        loss = strip_comments(block(read(VALUES), "te_seabed_jan_loss_southern"))
        self.assertIn("multiply = te_seabed_floor_keep", loss)
        self.assertIn("te_seabed_southern_barred", loss)
        self.assertIn("te_seabed_floor_void = yes", strip_comments(block(read(VALUES), "te_seabed_jan_loss_pacific")))

    def test_recording_writes_queued_per_basin(self):
        rec = strip_comments(block(read(EFFECTS), "te_seabed_record_country"))
        self.assertIn("te_seabed_queued_", rec)
        self.assertIn("te_seabed_queued_state = yes", rec)
        state = strip_comments(block(read(EFFECTS), "te_seabed_queued_state"))
        # distant licences first, in basin order, then the state's own
        at = [state.index(f"te_seabed_queued_take_distant = {{ B = {b} N = {i} }}") for i, b in enumerate(m.BASINS, 1)]
        self.assertEqual(at, sorted(at))
        self.assertLess(at[-1], state.index("te_seabed_queued_take_own = { B = pacific N = 1 }"))


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


class NavyMeasureTest(unittest.TestCase):
    """Seabed claims spec § 6.1: the navy term is naval power projection,
    scaled to the old flotilla term, behind a once-a-game self-check."""

    def test_power_projection_is_the_navy_term(self):
        body = strip_comments(block(read(VALUES), "te_seabed_navy_effective"))
        self.assertIn("naval_power_projection", body)
        self.assertIn("te_seabed_power_projection_scale", body)
        self.assertNotIn("navy_size", body)

    def test_scale_constant(self):
        """Review I1: vanilla ships project 35-465 each and the mod's late ones
        75-1,350, while navy_size counts ships; 300, the era-11 hull average,
        keeps the navy term near the old flotilla count."""
        self.assertEqual(literal(read(VALUES), "te_seabed_power_projection_scale"), 300)

    def test_self_check_excludes_no_navy(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_power_projection_check"))
        self.assertIn("navy_size > 0", body)
        self.assertIn("seabed_power_projection", body)

    def test_self_check_runs_from_the_sharing_once(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        self.assertIn("te_seabed_power_projection_check = yes", body)
        check = strip_comments(block(read(EFFECTS), "te_seabed_power_projection_check"))
        self.assertIn("te_seabed_npp_check_done", check)
        self.assertIn("TE_SELF_CHECK OK seabed_power_projection", check)
        self.assertIn("TE_SELF_CHECK BROKEN seabed_power_projection", check)

    def test_readout_shows_raw_power_projection(self):
        """The stored readout is in the weight's navy units (the model's
        need_navy); the cell shows it × the scale, the military panel's
        figure. Only above 0: -1 (full) and -2 (no claim) are the cell's
        sentinels."""
        for b in m.BASINS:
            body = strip_comments(block(read(VALUES), f"te_seabed_need_navy_disp_{b}"))
            self.assertRegex(body, rf"limit = \{{ var:te_seabed_need_navy_{b} > 0 \}}\s*"
                                   r"multiply = te_seabed_power_projection_scale")

    def test_loc_names_power_projection(self):
        loc = read("localization/english/te_miscellaneous_l_english.yml")
        for key in ("te_seabed_how_weight", "te_seabed_col_next_tt",
                    *(f"te_seabed_next_tt_{b}" for b in m.BASINS),
                    *(f"te_seabed_weight_home_{b}" for b in m.BASINS),
                    *(f"te_seabed_weight_far_{b}" for b in m.BASINS)):
            line = re.search(rf"^ {key}:0 \"(.*)\"$", loc, re.M).group(1)
            self.assertIn("naval power projection", line, key)
            self.assertNotIn("flotilla", line, key)

    def test_fallback_is_named(self):
        with open(os.path.join(REPO, "docs/testing/global-commons-playtest.md"), encoding="utf-8") as f:
            self.assertIn("seabed_power_projection", f.read())

    def test_concept_names_power_projection(self):
        """Review M1: the licence concept described the weight with \"navy\" and
        \"incorporated coastal states\"."""
        loc = read("localization/english/te_concepts_l_english.yml")
        line = re.search(r"^ concept_seabed_licence_desc:0 \"(.*)\"$", loc, re.M).group(1)
        self.assertIn("naval power projection", line)
        self.assertNotIn("our navy", line)
        self.assertNotIn("incorporated coastal states", line)


class BlockadeTest(unittest.TestCase):
    """Seabed claims spec § 6.2: city_type = port, the field every
    blockade-affected vanilla building shares, so a blockade cuts the mine's
    throughput; unverified, so the play-test list names the fallback."""

    def test_the_deep_sea_mine_is_a_port_building(self):
        body = block(read(BUILDINGS), "REPLACE_OR_CREATE:building_ocean_mine")
        self.assertIn("city_type = port", body)
        self.assertNotIn("city_type = city", body)
        self.assertIn("levels_per_mesh = -1", body)

    def test_fallback_is_named(self):
        with open(os.path.join(REPO, "docs/testing/global-commons-playtest.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("te_seabed_blockaded", text)
        self.assertIn("BLOCKADE_THROUGHPUT_IMPACT_SCALING", text)


if __name__ == "__main__":
    unittest.main()
