"""Second-strike survivors against an enemy's arsenal (2026-10-28 rework
spec §3.2): the Python mirror and the script values it mirrors."""

import math
import re
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.analysis.nuclear_incident_rates import Posture, RiskModel
from scripts.analysis.nuclear_survivors import (EXPOSURE_FACTORS, FLOOR_SHARE, SAFEGUARDS_CREDIT_CUT_MAX,
                                                TARGET_ROWS, WARNING_TIME_PENALTY, accuracy_mult, counterforce_destroyed,
                                                counterforce_saved, decapitation_chance, exposed, forces_preview,
                                                full_strike_lost_share, redundancy, survivability_target, survivors)
from test_nuclear_deterrence import block, loc_value, read, squash, strip_comments

ROOT = Path(__file__).resolve().parent


class TestSurvivorsFormula(unittest.TestCase):
    def test_formula_cases(self):
        # Half of ten exposed, an enemy of three: three destroyed.
        self.assertEqual(survivors(10, 50, 1.0, 0, 1.0, 3), 7)
        # All ten exposed, the enemy could destroy 40: Launch on Warning's
        # credit of 0.6 gets six away first.
        self.assertTrue(math.isclose(survivors(10, 0, 1.0, 0.6, 2.0, 20), 6))
        self.assertEqual(survivors(0, 80, 1.0, 0, 1, 5), 0)

    def test_readiness_factor_scales_survivability(self):
        self.assertTrue(math.isclose(survivors(10, 50, 0.5, 0, 1.0, 20), 2.5))


class TestSurvivorsScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def test_launch_credit(self):
        credit = {(a, s): self.model.number("nd_launch_credit", Posture(authority=a, safeguards=s))
                  for a in (1, 2, 3, 4) for s in (0, 3)}
        self.assertEqual(credit[1, 0], 0)
        self.assertEqual(credit[4, 0], 0)
        self.assertTrue(math.isclose(credit[2, 0], 0.25))
        self.assertTrue(math.isclose(credit[2, 3], 0.10))
        self.assertTrue(math.isclose(credit[3, 0], 0.6))
        self.assertTrue(math.isclose(credit[3, 3], 0.45))

    def test_exchange_ratio(self):
        k = self.model.number
        self.assertEqual(k("nd_k_ratio", Posture(icbms=False, pgm=False)), 1)
        self.assertEqual(k("nd_k_ratio", Posture(icbms=True, pgm=False)), 1.5)
        self.assertEqual(k("nd_k_ratio", Posture(icbms=True, pgm=True)), 2)

    def test_redundancy(self):
        # Survivability 0 and reliability 50 add nothing: the spec's 6.
        r = self.model.number("nd_redundancy", Posture(stockpile=30, satellite_communications=True, mainframe=False,
                                                       survivability=0, reliability=50))
        self.assertTrue(math.isclose(r, 6))

    def test_mirror_matches_script(self):
        enemy = Posture(believed_stockpile=12, icbms=True, pgm=False)
        for p in (Posture(readiness=3, authority=1, safeguards=0, survivability=40, stockpile=10, enemy=enemy),
                  Posture(readiness=1, authority=3, safeguards=2, survivability=70, stockpile=6, enemy=enemy),
                  Posture(readiness=2, authority=2, safeguards=3, survivability=10, stockpile=20,
                          enemy=replace(enemy, believed_stockpile=2))):
            factor = self.model.number("nd_effective_survivability", p) / p.survivability
            expected = survivors(p.stockpile, p.survivability, factor, self.model.number("nd_launch_credit", p),
                                 self.model.number("nd_k_ratio", p.enemy), p.enemy.believed_stockpile)
            self.assertTrue(math.isclose(self.model.number("nd_survivors_vs_saved", p), expected), p)

    def test_variants(self):
        enemy = Posture(believed_stockpile=40, icbms=True, pgm=True)
        p = Posture(readiness=0, authority=3, safeguards=0, survivability=60, stockpile=10, enemy=enemy)
        heightened = replace(p, readiness=2)
        self.assertTrue(math.isclose(self.model.number("nd_survivors_r2_vs_saved", p),
                                     self.model.number("nd_survivors_vs_saved", heightened)))
        bare = replace(heightened, authority=1)
        self.assertTrue(math.isclose(self.model.number("nd_survivors_bare_r2_vs_saved", p),
                                     self.model.number("nd_survivors_vs_saved", bare)))
        target = replace(bare, survivability=self.model.number("nd_survivability_target", p))
        self.assertTrue(math.isclose(self.model.number("nd_survivors_target_bare_r2_vs_saved", p),
                                     self.model.number("nd_survivors_vs_saved", target)))


class TestSurvivabilityTarget(unittest.TestCase):
    """Survivability climbs toward a target, 100 x (1 - the product of five
    exposure factors), with no flat ceiling (2026-11-20 delivery spec §3.1,
    owner call 6; phase 1 plan D4)."""

    VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
    # Each factor, its value while held, and the test that it is held.
    FACTORS = {
        "radar": "has_technology_researched = radar",
        "icbms": "nd_fields_icbms = yes",
        "submarines": "nd_fields_missile_submarines = yes",
        "missile_defense": "has_technology_researched = missile_defense_systems",
    }
    # Spec §3.1's table, rounded as it prints them.
    SPEC_TARGETS = (25, 40, 58, 79, 82, 64)
    # Spec §3.3: the share a full first strike destroys at each target, for
    # Central, Delegation and Launch on Warning (rows from Radar on).
    SPEC_LOST = (("+ Radar", (60, 45, 24)), ("+ ICBMs", (42, 31.5, 16.8)), ("+ missile submarines", (21, 15.8, 8.4)),
                 ("+ Missile Defense Systems", (17.9, 13.4, 7.1)))

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()
        cls.values = strip_comments(read(cls.VALUES))

    def test_each_factor_and_its_test(self):
        self.assertEqual(squash(block(self.values, "nd_exposure_factor_bombers")), "value = 0.75")
        for part, held in self.FACTORS.items():
            body = squash(block(self.values, f"nd_exposure_factor_{part}"))
            figure = f"{EXPOSURE_FACTORS[part]:.2f}"
            # The two legs' factors are named (phase 2 plan D16), so the Focus
            # rows read the same figure.
            if part in ("icbms", "submarines"):
                named = f"nd_exposure_factor_{part}_held"
                self.assertIn(f"{named} = {figure}", self.values, part)
                figure = named
            self.assertEqual(body, f"value = 1 if = {{ limit = {{ {held} }} value = {figure} }}", part)

    def test_target_is_one_less_the_product(self):
        share = squash(block(self.values, "nd_survivability_exposed_share"))
        self.assertEqual(share, "value = nd_exposure_factor_bombers multiply = nd_exposure_factor_radar "
                                "multiply = nd_exposure_factor_icbms multiply = nd_exposure_factor_submarines "
                                "multiply = nd_exposure_factor_missile_defense")
        target = squash(block(self.values, "nd_survivability_target"))
        self.assertEqual(target, "value = 1 subtract = nd_survivability_exposed_share multiply = 100")
        self.assertNotIn("max =", target)

    def test_floor_is_three_tenths_of_the_target(self):
        self.assertEqual(squash(block(self.values, "nd_survivability_floor")),
                         "value = nd_survivability_target multiply = 0.3")

    def test_no_reader_names_the_old_ceiling(self):
        for top in ("common", "events", "gui", "localization"):
            for path in (ROOT / top).rglob("*"):
                if path.suffix in (".txt", ".gui", ".yml"):
                    text = path.read_text(encoding="utf-8-sig")
                    for old in ("nd_survivability_cap", "nd_exposed_warheads_ceiling", "nd_survivors_ceiling_bare",
                                "nd_display_survivability_cap", "nd_w_survivability_cap_tt"):
                        self.assertNotIn(old, text, f"{path.relative_to(ROOT)}: {old}")

    def test_spec_table(self):
        self.assertEqual(tuple(round(survivability_target(**kwargs)) for _, kwargs in TARGET_ROWS), self.SPEC_TARGETS)

    def test_mirror_matches_script(self):
        for _, kwargs in TARGET_ROWS:
            p = Posture(radar=kwargs.get("radar", True), icbms=kwargs.get("icbms", True),
                        missile_submarines=kwargs.get("submarines", True),
                        missile_defense=kwargs.get("missile_defense", True))
            self.assertTrue(math.isclose(self.model.number("nd_survivability_target", p),
                                         survivability_target(**kwargs)), kwargs)
            self.assertTrue(math.isclose(self.model.number("nd_survivability_floor", p),
                                         0.3 * survivability_target(**kwargs)), kwargs)

    def test_every_part_counts_by_less(self):
        # Missile defense adds something at any force, unlike the old cap of
        # 80 that Radar, ICBMs and submarines alone already passed.
        full = survivability_target()
        without = survivability_target(missile_defense=False)
        self.assertGreater(full, without)
        self.assertGreater(survivability_target(icbms=False, submarines=False) -
                           survivability_target(icbms=False, submarines=False, missile_defense=False),
                           full - without)
        self.assertLess(full, 100)

    def test_lost_share_table(self):
        rows = dict(TARGET_ROWS)
        for label, lost in self.SPEC_LOST:
            target = survivability_target(**rows[label])
            for credit, share in zip((0, 0.25, 0.6), lost):
                self.assertAlmostEqual(full_strike_lost_share(target, credit) * 100, share, delta=0.06,
                                       msg=(label, credit))
        # And the script's own launch credit gives those three columns.
        credit = [self.model.number("nd_launch_credit", Posture(authority=a, safeguards=0)) for a in (1, 2, 3)]
        self.assertEqual([round(c, 2) for c in credit], [0, 0.25, 0.6])


class TestWarningTime(unittest.TestCase):
    """Weapons based next door cut warning time (rework spec §7.4; plan 4a
    R13): -10 to our effective survivability against the guest, for that pair
    only, wherever survivors or counterforce are counted."""

    VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
    EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
    # Each reader, the exposure variant it reads, and that variant's penalty.
    READERS = {
        "nd_survivors_vs_saved": "nd_exposed_warheads_vs_saved",
        "nd_survivors_r2_vs_saved": "nd_exposed_warheads_r2_vs_saved",
        "nd_survivors_bare_r2_vs_saved": "nd_exposed_warheads_r2_vs_saved",
        "nd_survivors_target_bare_r2_vs_saved": "nd_exposed_warheads_target_r2_vs_saved",
        "nd_survivors_vs_issuer": "nd_exposed_warheads_vs_issuer",
        "nd_survivors_vs_target": "nd_exposed_warheads_vs_target",
        "nd_counterforce_destroyed_raw": "nd_exposed_warheads_vs_saved",
        "nd_counterforce_saved_raw": "nd_exposed_warheads_vs_saved",
    }
    PENALTIES = {"saved": "scope:nd_sv_enemy", "issuer": "scope:nd_issuer", "target": "scope:nd_target"}

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()
        cls.values = strip_comments(read(cls.VALUES))

    def test_every_reader_reads_its_enemys_variant(self):
        for reader, variant in self.READERS.items():
            self.assertIn(f"max = {variant}", block(self.values, reader), reader)
            penalty = "nd_warning_penalty_" + variant.rsplit("_vs_", 1)[1]
            self.assertIn(f"subtract = {penalty}", block(self.values, variant), variant)

    def test_penalty_names_its_scope(self):
        for name, scope in self.PENALTIES.items():
            body = squash(block(self.values, f"nd_warning_penalty_{name}"))
            self.assertIn(f"is_target_in_variable_list = {{ name = nd_based_near target = {scope} }}", body, name)
            self.assertIn("value = nd_warning_time_penalty", body, name)

    def test_penalty_is_ten_for_a_listed_enemy_only(self):
        self.assertEqual(WARNING_TIME_PENALTY, 10)
        enemy = Posture()
        self.assertEqual(self.model.number("nd_warning_penalty_saved", Posture(based_near=True, enemy=enemy)), 10)
        self.assertEqual(self.model.number("nd_warning_penalty_saved", Posture(based_near=False, enemy=enemy)), 0)

    def test_mirror_and_script_agree(self):
        enemy = Posture(believed_stockpile=12, icbms=True, pgm=False)
        for based_near in (False, True):
            for p in (Posture(readiness=3, authority=1, survivability=40, stockpile=10, enemy=enemy),
                      Posture(readiness=1, authority=3, safeguards=2, survivability=70, stockpile=6, enemy=enemy),
                      # Below the penalty: no warning time at all, never less.
                      Posture(readiness=3, authority=1, survivability=6, stockpile=8, enemy=enemy)):
                p = replace(p, based_near=based_near)
                factor = self.model.number("nd_effective_survivability", p) / p.survivability
                credit = self.model.number("nd_launch_credit", p)
                expected = survivors(p.stockpile, p.survivability, factor, credit,
                                     self.model.number("nd_k_ratio", p.enemy), p.enemy.believed_stockpile,
                                     based_near=based_near)
                self.assertTrue(math.isclose(self.model.number("nd_survivors_vs_saved", p), expected), p)
                bare = exposed(p.stockpile, p.survivability, factor, based_near=based_near)
                self.assertTrue(math.isclose(self.model.number("nd_exposed_warheads_vs_saved", p), bare), p)
                self.assertLessEqual(bare, p.stockpile)
                # An attacker with precision weapons also reaches more of our
                # silos (delivery spec §3.4), after the warning penalty.
                attacker = Posture(salvo_forces_landed=3, icbms=True, pgm=True)
                victim = replace(p, enemy=attacker)
                aimed = exposed(p.stockpile, p.survivability, factor, based_near=based_near,
                                accuracy=accuracy_mult(0.15))
                self.assertTrue(math.isclose(self.model.number("nd_counterforce_destroyed_raw", victim),
                                             counterforce_destroyed(3, 2, aimed, credit), abs_tol=1e-9), p)

    def test_next_door_costs_survivors(self):
        # No precision weapons, so the warning time alone moves the figure.
        enemy = Posture(believed_stockpile=40, icbms=True, pgm=False)
        far = Posture(readiness=3, authority=1, survivability=50, stockpile=10, enemy=enemy)
        near = replace(far, based_near=True)
        self.assertTrue(math.isclose(self.model.number("nd_survivors_vs_saved", far), 5))
        self.assertTrue(math.isclose(self.model.number("nd_survivors_vs_saved", near), 4))

    def test_list_rebuilt_weekly_from_basing_next_door(self):
        effects = strip_comments(read(self.EFFECTS))
        weekly = block(effects, "nd_weekly_update")
        self.assertIn("nd_based_near_refresh = yes", weekly)
        body = squash(block(effects, "nd_based_near_refresh"))
        for needle in ("if = { limit = { has_variable_list = nd_based_near } clear_variable_list = nd_based_near }",
                       "has_type = nuclear_basing source_country = scope:nd_bn_guest",
                       "is_adjacent_to_country = scope:nd_bn_self",
                       "is_target_in_variable_list = { name = nd_based_near target = scope:nd_bn_guest }",
                       "add_to_variable_list = { name = nd_based_near target = scope:nd_bn_guest }"):
            self.assertIn(needle, body)
        self.assertLess(body.index("clear_variable_list"), body.index("nd_is_armed = yes"))
        self.assertLess(body.index("is_target_in_variable_list"), body.index("add_to_variable_list"))
        # The panel's hover counts the main rival's exposure the same way.
        self.assertIn("set_variable = { name = nd_exposed_main value = nd_exposed_warheads_vs_saved }", squash(effects))

class TestCounterforceScript(unittest.TestCase):
    """A Forces salvo destroys min(exposed, K x landed) x (1 - credit) of the
    victim's warheads (rework spec §6.2). The attacker is scope:nd_sv_enemy."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def destroyed(self, victim):
        return self.model.number("nd_counterforce_destroyed_raw", victim)

    def test_counterforce_matches_mirror(self):
        for landed in (0, 1, 3, 8):
            for survivability in (0, 40, 80):
                for authority, safeguards in ((1, 0), (2, 3), (3, 0), (4, 1)):
                    for icbms, pgm in ((False, False), (True, True)):
                        attacker = Posture(salvo_forces_landed=landed, icbms=icbms, pgm=pgm)
                        victim = Posture(readiness=2, authority=authority, safeguards=safeguards,
                                         survivability=survivability, stockpile=10, enemy=attacker)
                        # Our silos against its precision weapons (delivery spec §3.4).
                        exposed = min(victim.stockpile, self.model.number("nd_exposed_warheads", victim)
                                      * accuracy_mult(0.15 if pgm else 0, victim.icbms))
                        k = self.model.number("nd_k_ratio", attacker)
                        credit = self.model.number("nd_launch_credit", victim)
                        self.assertTrue(math.isclose(self.destroyed(victim),
                                                     counterforce_destroyed(landed, k, exposed, credit),
                                                     abs_tol=1e-9), victim)
                        self.assertTrue(math.isclose(self.model.number("nd_counterforce_saved_raw", victim),
                                                     counterforce_saved(landed, k, exposed, credit),
                                                     abs_tol=1e-9), victim)

    def test_counterforce_bounded_by_exposed_and_stockpile(self):
        attacker = Posture(salvo_forces_landed=50, icbms=True, pgm=True)
        for stockpile, survivability in ((3, 0), (0, 0), (6, 50)):
            victim = Posture(readiness=3, authority=1, survivability=survivability, stockpile=stockpile, enemy=attacker)
            self.assertLessEqual(self.destroyed(victim), stockpile)
            self.assertLessEqual(self.destroyed(victim),
                                 self.model.number("nd_exposed_warheads_vs_saved", victim) + 1e-9)
        hidden = Posture(readiness=3, authority=1, survivability=100, stockpile=10, enemy=attacker)
        self.assertEqual(self.destroyed(hidden), 0)

    def test_saved_share_is_the_credit(self):
        attacker = Posture(salvo_forces_landed=4, icbms=False, pgm=False)
        victim = Posture(readiness=3, authority=3, safeguards=0, survivability=0, stockpile=10, enemy=attacker)
        # Four destroyable, Launch on Warning's 0.6 of them get away first.
        self.assertTrue(math.isclose(self.model.number("nd_counterforce_saved_raw", victim), 2.4))
        self.assertTrue(math.isclose(self.destroyed(victim), 1.6))


class TestDecapitationScript(unittest.TestCase):
    """Chance = max(0, 1 - (R/L)^2) for L warheads on the command against
    redundancy R (rework spec §6.3; the curve and R's command terms, owner,
    2026-11-19)."""

    # Survivability 0 and reliability 50: R is the spec's warheads-and-technology figure.
    BASE = Posture(survivability=0, reliability=50)

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def chance(self, landed, redundancy):
        attacker = Posture(salvo_command_landed=landed, salvo_victim_r=redundancy)
        return self.model.number("nd_decapitation_chance_value", Posture(enemy=attacker))

    def r(self, value="nd_redundancy", **fields):
        return self.model.number(value, replace(self.BASE, **fields))

    def test_chance_matches_mirror(self):
        for landed in (0, 1, 2, 5, 9, 25):
            for r in (1, 1.3, 3.5, 6, 21.8):
                self.assertTrue(math.isclose(self.chance(landed, r), decapitation_chance(landed, r),
                                             abs_tol=1e-9), (landed, r))

    def test_nothing_until_landed_exceeds_redundancy(self):
        # Owner call 7, kept: one warhead can't decapitate a large arsenal.
        self.assertEqual(self.chance(0, 1), 0)
        self.assertEqual(self.chance(6, 6), 0)
        self.assertEqual(self.chance(5, 6), 0)
        self.assertGreater(self.chance(7, 6), 0)

    def test_full_salvo_on_an_ai_sized_arsenal(self):
        # Twenty warheads and both technologies, nothing else: 94% from 25.
        r = self.r(stockpile=20, satellite_communications=True, mainframe=True)
        self.assertTrue(math.isclose(r, 6))
        self.assertTrue(math.isclose(self.chance(25, r), (1 - (6 / 25) ** 2) * 100))

    def test_thirty_warhead_power_needs_seven(self):
        r = self.r(stockpile=30, satellite_communications=True, mainframe=False)
        self.assertEqual(self.chance(6, r), 0)
        self.assertGreater(self.chance(7, r), 0)

    def test_three_warhead_state_faces_58_from_two(self):
        r = self.r(stockpile=3, satellite_communications=False, mainframe=False)
        self.assertTrue(math.isclose(r, 1.3))
        self.assertTrue(math.isclose(self.chance(2, r), (1 - 0.65 ** 2) * 100))

    def test_command_terms(self):
        bare = dict(stockpile=0, satellite_communications=False, mainframe=False)
        self.assertTrue(math.isclose(self.r(**bare), 1))
        # Survivability / 20: +4 at the ceiling of 80.
        self.assertTrue(math.isclose(self.r(**bare, survivability=80), 5))
        # A Nuclear Command Center: +2 a staffed level, at most +6.
        self.assertTrue(math.isclose(self.r(**bare, command_center=1), 3))
        self.assertTrue(math.isclose(self.r(**bare, command_center=3), 7))
        self.assertTrue(math.isclose(self.r(**bare, command_center=5), 7))
        # (Reliability - 50) / 10, either way, and never below 1.
        self.assertTrue(math.isclose(self.r(**bare, reliability=98), 5.8))
        self.assertTrue(math.isclose(self.r(**dict(bare, stockpile=40), reliability=30), 3))
        self.assertTrue(math.isclose(self.r(**bare, reliability=5), 1))

    def test_redundancy_matches_mirror(self):
        for fields in (dict(stockpile=20, survivability=50, reliability=72),
                       dict(stockpile=5, survivability=40, reliability=62, mainframe=False),
                       dict(stockpile=50, survivability=80, reliability=98, command_center=3),
                       dict(stockpile=0, satellite_communications=False, mainframe=False, reliability=5)):
            self.assertTrue(math.isclose(self.r(**fields), redundancy(**fields)), fields)

    def test_believed_redundancy_reads_the_worlds_view(self):
        # The shown estimate and the survivability target (delivery spec owner
        # call 13), never the true count, the stored survivability or command
        # reliability. Bombers alone: a target of 25, so +1.25.
        bombers = dict(radar=False, icbms=False, missile_submarines=False, missile_defense=False)
        p = dict(stockpile=30, believed_stockpile=10, public_estimate=10, satellite_communications=False,
                 mainframe=False, **bombers)
        self.assertTrue(math.isclose(self.r("nd_redundancy_believed", **p), 3.25))
        # The world sees a Command Center and the technologies, not reliability
        # or how far hardening has got.
        seen = dict(p, survivability=70, command_center=1, reliability=90)
        self.assertTrue(math.isclose(self.r("nd_redundancy_believed", **seen), 5.25))
        self.assertTrue(math.isclose(self.r("nd_redundancy_believed", **seen),
                                     redundancy(10, False, False, survivability_target(False, False, False, False), 1,
                                                reliability=None)))
        # Before the estimate is seeded the world counts none, not the live 30.
        self.assertTrue(math.isclose(self.r("nd_redundancy_believed", **dict(p, public_estimate=0)), 2.25))

    def test_text_gives_the_scripts_figures(self):
        # Command Redundancy's concept and the tooltips that name its terms
        # (owner, 2026-11-19) state the figures the script values use.
        values = squash(strip_comments(read(ROOT / "common/script_values/nuclear_deterrence_values.txt")))
        colony = squash(strip_comments(read(ROOT / "common/script_values/sr_colony_module_values.txt")))
        self.assertIn("value = nd_stockpile divide = 10 add = 1 add = nd_redundancy_command", values)
        self.assertIn("value = var:nd_reliability subtract = 50 divide = 10", values)
        self.assertIn("value = nd_survivability_or_zero divide = 20", values)
        self.assertIn("sr_mod_bunker_redundancy_per_level = { value = 2 }", colony)
        self.assertIn("sr_mod_bunker_redundancy_max = { value = 6 }", colony)
        concept = loc_value("concept_command_redundancy_desc")
        for words in ("It is 1, and:", "Each ten warheads the country holds: #v +1#!",
                      "[GetTechnology('satellite_communications').GetName]: #v +2#!",
                      "[GetTechnology('mainframe_computers').GetName]: #v +1#!", "Each 20 survivability: #v +1#!",
                      "#v +2#!, at most #v +6#!", "#v +1#! for each 10 above 50, #v −1#! for each 10 below",
                      "never below 1", "twice the redundancy gives three in four",
                      "25 warheads against a redundancy of 6 give 94%"):
            self.assertIn(words, concept)
        self.assertEqual(round(decapitation_chance(50, 25)), 75)
        self.assertEqual(round(decapitation_chance(25, 6)), 94)
        self.assertIn("Each 20 adds #G +1#! [concept_command_redundancy]", loc_value("nd_w_survivability_tt"))
        self.assertIn("#G +1#! for each 10 above 50, #R −1#! for each 10 below", loc_value("nd_w_reliability_tt"))
        for key in ("sr_mod_queue_bunker_tt", "je_space_race_widget_mod_bunker_tt"):
            self.assertIn("#v +2#! [concept_command_redundancy], at most #v +6#!", loc_value(key), key)
        self.assertIn("three in four when twice as many land", loc_value("nd_w_strike_mission_3_tt"))


class TestWorldsView(unittest.TestCase):
    """What one country counts of another is the world's view (2026-11-20
    delivery spec §5.2, owner calls 13 and 14; plan D8, D9): the shown
    estimate, the survivability target, the authority's credit before
    safeguards, and readiness only in a crisis between the two."""

    VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
    CRISIS = ROOT / "common/scripted_effects/nuclear_crisis_effects.txt"
    TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
    SEEN = ("nd_seen_stockpile", "nd_seen_survivability", "nd_seen_launch_credit", "nd_seen_readiness_factor_saved",
            "nd_seen_readiness_factor_target", "nd_seen_exposed_warheads_vs_saved", "nd_seen_exposed_warheads_vs_target",
            "nd_seen_survivors_vs_saved", "nd_seen_survivors_vs_target", "nd_redundancy_command_seen",
            "nd_redundancy_believed", "nd_seen_readiness_factor_issuer", "nd_seen_exposed_warheads_vs_issuer",
            "nd_seen_survivors_vs_issuer")
    # The true state the world never sees (test_nuclear_layout.TRUE_VARS less
    # launch authority, public since rework spec §14.2, and readiness, which a
    # crisis shows each side of the other: test_readiness_only_in_a_crisis).
    HIDDEN = re.compile(
        r"\b(nuclear_weapon_stockpile|nuclear_weapon_program_progress|nuclear_weapons_program_funding"
        r"|nd_readiness\w*|nd_survivability|nd_reliability|nd_strain|nd_upkeep_weekly_cached|nd_warhead_ceiling"
        r"|nd_dismantle_\w+|nd_safeguards|nd_hardening|nd_loose_\w+|nd_custody_\w+|nd_ar_\w+)\b")
    CRISIS_BRANCH = ("if = {{ limit = {{ nd_seen_in_crisis_with = {{ OBSERVER = {} }} }} "
                     "value = nd_readiness_survivability_factor }}")
    OBSERVERS = {"saved": "scope:nd_sv_enemy", "target": "scope:nd_target", "issuer": "scope:nd_issuer"}

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()
        cls.values = strip_comments(read(cls.VALUES))

    @staticmethod
    def observed(body):
        """The body as read at the observed country: blocks in another scope
        (the observer's reach, a crisis opponent's figure) left out."""
        out, i = [], 0
        for m in re.finditer(r"(?:scope:\w+|var:\w+|\$\w+\$) = \{", body):
            if m.start() < i:
                continue
            out.append(body[i:m.start()])
            depth, j = 1, m.end()
            while depth:
                depth += {"{": 1, "}": -1}.get(body[j], 0)
                j += 1
            i = j
        return "".join(out) + body[i:]

    def test_seen_values_read_only_public_inputs(self):
        from test_nuclear_layout import _NAME_REF, _scripts
        graph = {**_scripts("script_values"), **_scripts("scripted_triggers")}
        for name in self.SEEN:
            self.assertIn(name, graph, name)
        found, stack, seen = [], [(n, n) for n in self.SEEN], set()
        while stack:
            name, path = stack.pop()
            if name in seen:
                continue
            seen.add(name)
            body = squash(graph[name])
            for scope, observer in self.OBSERVERS.items():
                if name == f"nd_seen_readiness_factor_{scope}":
                    body = body.replace(self.CRISIS_BRANCH.format(observer), "")
            body = self.observed(body)
            found += [f"{path}: {m.group(0)}" for m in self.HIDDEN.finditer(body)]
            stack += [(ref, f"{path} > {ref}") for ref in set(_NAME_REF.findall(body)) & graph.keys() if ref != name]
        self.assertEqual(found, [], "the world's view reads the true state")

    def test_readiness_only_in_a_crisis_with_the_observer(self):
        for scope, observer in self.OBSERVERS.items():
            body = squash(block(self.values, f"nd_seen_readiness_factor_{scope}"))
            self.assertEqual(body, "value = nd_survivability_factor_heightened " + self.CRISIS_BRANCH.format(observer))
        trigger = squash(block(strip_comments(read(self.TRIGGERS)), "nd_seen_in_crisis_with"))
        self.assertEqual(trigger, "nd_in_crisis = yes var:nd_crisis_opponent ?= $OBSERVER$")

    def test_the_three_readers_read_the_world_view(self):
        exposure = squash(block(self.values, "nd_yp_issuer_exposure_value"))
        self.assertIn("scope:nd_issuer = { add = nd_seen_survivors_vs_target }", exposure)
        preview = squash(block(strip_comments(read(self.CRISIS)), "nd_crisis_preview"))
        self.assertIn("$TARGET$ = { nd_seen_survivors_vs_saved >= 3 }", preview)
        self.assertNotIn("$TARGET$ = { nd_survivors_vs_saved", preview)
        believed = squash(block(self.values, "nd_redundancy_believed"))
        self.assertEqual(believed, "value = nd_seen_stockpile divide = 10 add = 1 add = nd_redundancy_command_seen min = 1")

    def test_a_sides_own_survivors_stay_true(self):
        self.assertTrue(squash(block(self.values, "nd_yp_answer_survivors_value"))
                        .startswith("value = nd_survivors_vs_issuer "))

    def test_the_seen_figures(self):
        self.assertEqual(squash(block(self.values, "nd_seen_stockpile")), "value = nd_shown_public_estimate")
        self.assertEqual(squash(block(self.values, "nd_seen_survivability")), "value = nd_survivability_target")
        for authority, credit in ((1, 0), (2, 0.25), (3, 0.6), (4, 0)):
            for safeguards in (0, 3):
                p = Posture(authority=authority, safeguards=safeguards)
                self.assertTrue(math.isclose(self.model.number("nd_seen_launch_credit", p), credit), p)

    def test_mirror_and_script_agree(self):
        target = survivability_target()
        heightened = self.model.number("nd_survivability_factor_heightened", Posture())
        for enemy_pgm in (False, True):
            enemy = Posture(believed_stockpile=40, icbms=True, pgm=enemy_pgm)
            for authority in (1, 2, 3):
                for stage, readiness in ((0, 0), (0, 3), (2, 0), (3, 3)):
                    p = Posture(readiness=readiness, authority=authority, stage=stage, public_estimate=12,
                                enemy=enemy)
                    factor = self.model.number("nd_readiness_survivability_factor", p) if stage else heightened
                    credit = self.model.number("nd_seen_launch_credit", p)
                    expected = survivors(12, target, factor, credit, self.model.number("nd_k_ratio", enemy), 40,
                                         accuracy=accuracy_mult(0.15 if enemy_pgm else 0))
                    case = (enemy_pgm, authority, stage, readiness)
                    self.assertTrue(math.isclose(self.model.number("nd_seen_survivors_vs_saved", p), expected), case)

    def test_hidden_inputs_change_nothing(self):
        enemy = Posture(believed_stockpile=40, icbms=True, pgm=True)
        base = Posture(readiness=0, authority=3, public_estimate=12, enemy=enemy)
        figure = self.model.number("nd_seen_survivors_vs_saved", base)
        for hidden in (dict(stockpile=50), dict(survivability=5), dict(safeguards=3), dict(reliability=20),
                       dict(readiness=3), dict(believed_stockpile=40)):
            self.assertEqual(self.model.number("nd_seen_survivors_vs_saved", replace(base, **hidden)), figure, hidden)
        # Readiness counts only in a crisis with the observer.
        self.assertNotEqual(self.model.number("nd_seen_survivors_vs_saved", replace(base, stage=1)),
                            self.model.number("nd_seen_survivors_vs_saved", replace(base, stage=1, readiness=3)))

    def test_readiness_factor_matches_effective_survivability(self):
        for readiness in range(4):
            p = Posture(readiness=readiness, survivability=60)
            self.assertTrue(math.isclose(self.model.number("nd_readiness_survivability_factor", p) * 60,
                                         self.model.number("nd_effective_survivability", p)), readiness)

    def test_preview_lines_say_what_they_assume(self):
        for key in ("nd_tt_open_f_survivable", "nd_tt_open_f_armed"):
            self.assertIn("as secure as their technology allows", loc_value(key), key)


# ---- The Strike section's previews (2026-11-20 delivery spec §5.3; plan Task 7, D14) ----

EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
EXTRA_VALUES = ROOT / "common/script_values/extra_script_values.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_deterrence_custom_loc.txt"
SGUIS = ROOT / "common/scripted_guis/nuclear_deterrence_sguis.txt"
GUI = ROOT / "gui/journal_entry_widgets/nuclear_deterrence_widget.gui"

# Each range the panel prints, as a low and a high end (nd_plan_pv_<range>_lo,
# _hi). The razed share is the Cities mission's; the rest rest on the world's
# view of the target (D8).
PREVIEW_RANGES = ("raze", "destroyed", "kept", "flown", "redundancy", "decap")
WORLDS_VIEW_RANGES = ("destroyed", "kept", "flown", "redundancy", "decap")
PREVIEW_VARS = ([f"nd_plan_pv_{kind}_{m}" for kind in ("landed", "deaths") for m in (1, 2, 3)]
                + [f"nd_plan_pv_{r}_{end}" for r in PREVIEW_RANGES for end in ("lo", "hi")]
                + ["nd_plan_pv_warheads", "nd_plan_pv_fires_first", "nd_plan_pv_accuracy", "nd_plan_pv_case"])
# What is stored from the target's own scope (scope:nd_pv_enemy), to a tenth.
ENEMY_FIGURES = (("nd_plan_pv_warheads", "nd_seen_stockpile"),
                 ("nd_plan_pv_destroyed_lo", "nd_pv_destroyed_lo"), ("nd_plan_pv_destroyed_hi", "nd_pv_destroyed_hi"),
                 ("nd_plan_pv_kept_lo", "nd_pv_kept_lo"), ("nd_plan_pv_kept_hi", "nd_pv_kept_hi"),
                 ("nd_plan_pv_flown_lo", "nd_pv_flown_lo"), ("nd_plan_pv_flown_hi", "nd_pv_flown_hi"),
                 ("nd_plan_pv_redundancy_lo", "nd_redundancy_believed_floor"),
                 ("nd_plan_pv_redundancy_hi", "nd_redundancy_believed"))
# The script's round = yes.
def tenth(x):
    return math.floor(x * 10 + 0.5) / 10


class TestStrikePreview(unittest.TestCase):
    """The Strike section previews each mission at the salvo size set
    (2026-11-20 delivery spec §5.3, plan Task 7, D14): Cities its warheads
    expected to land, its deaths and the share of a city razed; Forces the
    warheads it destroys, those flown first and those left to answer;
    Leadership the chance to cut the chain of command. Of the target only the
    world's view is read, and every figure resting on it is a range from its
    worst case for us, with the shared hover (D8, owner call 14)."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()
        cls.values = strip_comments(read(TestWorldsView.VALUES))
        cls.effects = strip_comments(read(EFFECTS))
        cls.custom = strip_comments(read(CUSTOM_LOC))

    def number(self, name, posture):
        return self.model.number(name, posture)

    # ---- when it is stored -------------------------------------------------------

    def test_stored_weekly_and_on_every_planner_op(self):
        """nd_plan_refresh ends with the preview: weekly for a human and on ops
        72/73. Ops 74-78 (mission, size) run the preview alone, behind the
        click-only marker, so the enemy doesn't change under the click. Op 79
        opens the Launch Order, which changes nothing the preview reads."""
        self.assertTrue(squash(block(self.effects, "nd_plan_refresh")).endswith("nd_plan_preview = yes"))
        self.assertIn("if = { limit = { is_ai = no nd_is_armed = yes } nd_plan_refresh = yes }",
                      squash(block(self.effects, "nd_weekly_update")))
        marker = "if = { limit = { has_variable = nd_plan_click } remove_variable = nd_plan_click "
        for name, call in (("nd_plan_step_enemy", "nd_plan_refresh = yes"), ("nd_plan_set_mission", "nd_plan_preview = yes"),
                           ("nd_plan_step_size", "nd_plan_preview = yes")):
            body = squash(block(self.effects, name))
            self.assertIn(call, body[body.index(marker):], name)
        sgui = squash(block(strip_comments(read(SGUIS)), "nd_posture_sgui"))
        for op, call in ((72, "nd_plan_step_enemy = { OP = subtract }"), (73, "nd_plan_step_enemy = { OP = add }"),
                         (74, "nd_plan_set_mission = { M = 1 }"), (75, "nd_plan_set_mission = { M = 2 }"),
                         (76, "nd_plan_set_mission = { M = 3 }"), (77, "nd_plan_step_size = { OP = subtract }"),
                         (78, "nd_plan_step_size = { OP = add }")):
            self.assertIn(f"limit = {{ exists = scope:op scope:op = {op} }} {call}", sgui, op)

    def test_each_figure_is_stored_and_cleared(self):
        body = block(self.effects, "nd_plan_preview")
        keep, clear = body.rsplit("\n\telse = {", 1)
        keep, clear = squash(keep), squash(clear)
        for name, value in ENEMY_FIGURES:
            self.assertIn(f"nd_plan_pv_store = {{ NAME = {name} VALUE = {value} }}", keep, name)
        self.assertEqual(squash(block(self.effects, "nd_plan_pv_store")),
                         "set_variable = { name = $NAME$ value = { value = scope:nd_pv_enemy.$VALUE$ multiply = 10 "
                         "round = yes divide = 10 } }")
        for name, value in (("nd_plan_pv_accuracy", "scope:nd_pv_enemy.nd_accuracy_mult_saved"),
                            ("nd_plan_pv_fires_first", "nd_pv_fires_first"),
                            ("nd_plan_pv_decap_lo", "nd_pv_decap_chance_lo"),
                            ("nd_plan_pv_decap_hi", "nd_pv_decap_chance_hi"),
                            ("nd_plan_pv_case", "nd_pv_leadership_case")):
            self.assertIn(f"set_variable = {{ name = {name} value = {value} }}", keep, name)
        for name in PREVIEW_VARS:
            self.assertIn(f"remove_variable = {name}", clear, name)

    def test_each_mission_runs_the_salvos_own_picker(self):
        """Expected landed is the salvo's own: its picker, once a warhead, at
        each picked state's odds, the marks cleared after. The panel's mission
        is put back, and the scopes the picker reads are cleared, since a
        saved scope outlives the effect that saved it."""
        preview = squash(block(self.effects, "nd_plan_preview"))
        for m in (1, 2, 3):
            self.assertIn(f"nd_plan_preview_mission = {{ M = {m} }}", preview)
        self.assertIn("set_variable = { name = nd_salvo_mission value = var:nd_plan_pv_mission_set }", preview)
        for scope in ("nd_salvo_attacker", "attacking_country", "nd_sv_enemy", "nd_pv_enemy", "nd_salvo_cap_region",
                      "target_state"):
            self.assertIn(f"clear_saved_scope = {scope}", preview, scope)
        mission = squash(block(self.effects, "nd_plan_preview_mission"))
        self.assertIn("set_variable = { name = nd_salvo_mission value = $M$ }", mission)
        self.assertIn("while = { count = nd_salvo_size_value nd_plan_preview_warhead = { M = $M$ } }", mission)
        for name in ("nd_salvo_target", "nd_pv_left", "nd_pv_kill", "nd_pv_raze", "nd_salvo_lead_alt", "nd_salvo_aimed"):
            self.assertIn(f"remove_variable = {name}", mission, name)
        warhead = squash(block(self.effects, "nd_plan_preview_warhead"))
        self.assertTrue(warhead.startswith("scope:nd_pv_enemy = { nd_salvo_pick_target = yes } "
                                           "if = { limit = { has_variable = nd_salvo_aimed } remove_variable = nd_salvo_aimed"))
        self.assertIn("set_variable = { name = nd_plan_pv_p value = nd_plan_pv_land_chance }", warhead)
        self.assertIn("change_variable = { name = nd_plan_pv_landed_$M$ add = var:nd_plan_pv_p }", warhead)
        self.assertEqual(squash(block(self.values, "nd_plan_pv_land_chance")),
                         "value = nuclear_strike_success_chance divide = 100")
        # The order's own warhead: the same picker and the same odds.
        salvo = squash(block(self.effects, "nd_salvo_warhead"))
        self.assertIn("scope:nd_salvo_victim = { nd_salvo_pick_target = yes }", salvo)
        self.assertIn("modifier = nuclear_strike_success_chance nd_salvo_hit = yes", salvo)

    def test_deaths_follow_the_strikes(self):
        """A tenth of the people the earlier warheads left, a quarter of that
        on Forces, as the city and the counterforce strikes kill."""
        extra = strip_comments(read(EXTRA_VALUES))
        city = float(re.search(r"multiply = ([\d.]+) round = yes",
                               squash(block(extra, "nuclear_industrial_strike_killed_population")))[1])
        forces = float(re.search(r"multiply = ([\d.]+) round = yes",
                                 squash(block(extra, "nd_counterforce_strike_killed_population")))[1])
        kill = squash(block(self.values, "nd_pv_kill_value"))
        self.assertEqual(kill, f"value = var:nd_pv_left multiply = {city:g} if = {{ limit = {{ scope:nd_salvo_attacker = "
                               f"{{ var:nd_salvo_mission = 2 }} }} multiply = {forces / city:g} }} "
                               f"multiply = scope:nd_salvo_attacker.var:nd_plan_pv_p")
        self.assertEqual(squash(block(self.values, "nd_pv_people_value")),
                         "value = state_population if = { limit = { has_variable = nd_strike_people_left } "
                         "value = var:nd_strike_people_left max = state_population }")

    # ---- the figures -------------------------------------------------------------

    def test_the_other_end_is_the_floor_and_every_safeguard(self):
        self.assertEqual(squash(block(self.values, "nd_survivability_floor")),
                         f"value = nd_survivability_target multiply = {FLOOR_SHARE}")
        self.assertEqual(squash(block(self.values, "nd_seen_survivability_floor")), "value = nd_survivability_floor")
        self.assertEqual(squash(block(self.values, "nd_seen_launch_credit_low")),
                         "value = nd_seen_launch_credit subtract = { value = nd_launch_credit_safeguards_cut "
                         "multiply = 3 } min = 0")
        self.assertTrue(math.isclose(3 * self.number("nd_launch_credit_safeguards_cut", Posture()),
                                     SAFEGUARDS_CREDIT_CUT_MAX))
        seen = squash(block(self.values, "nd_seen_exposed_warheads_vs_saved"))
        self.assertEqual(squash(block(self.values, "nd_seen_exposed_warheads_floor_vs_saved")),
                         seen.replace("value = nd_seen_survivability ", "value = nd_seen_survivability_floor "))

    def test_forces_ranges_match_the_mirror(self):
        heightened = self.number("nd_survivability_factor_heightened", Posture())
        for pgm in (False, True):
            for landed in (0, 1.5, 6, 20):
                us = Posture(icbms=True, pgm=pgm, plan_pv_landed_2=landed)
                k = self.number("nd_k_ratio", us)
                for authority in (1, 2, 3):
                    for stage, readiness in ((0, 0), (2, 3)):
                        for icbms in (False, True):
                            for based_near in (False, True):
                                them = Posture(authority=authority, stage=stage, readiness=readiness, icbms=icbms,
                                               public_estimate=12, based_near=based_near, enemy=us)
                                case = (pgm, landed, authority, stage, icbms, based_near)
                                factor = (self.number("nd_readiness_survivability_factor", them) if stage
                                          else heightened)
                                destroyed, flown, kept = forces_preview(
                                    12, self.number("nd_survivability_target", them), factor,
                                    self.number("nd_seen_launch_credit", them), k, landed, based_near,
                                    accuracy_mult(0.15 if pgm else 0, fields_icbms=icbms), fires_first=authority == 3)
                                for kind, ends in (("destroyed", destroyed), ("flown", flown), ("kept", kept)):
                                    lo, hi = (self.number(f"nd_pv_{kind}_{end}", them) for end in ("lo", "hi"))
                                    self.assertTrue(math.isclose(lo, ends[0], abs_tol=1e-9), (kind, case))
                                    self.assertTrue(math.isclose(hi, ends[1], abs_tol=1e-9), (kind, case))
                                    self.assertLessEqual(lo, hi, (kind, case))
        # A salvo of one warhead against a large arsenal: the ends differ only by the credit.
        them = Posture(authority=3, public_estimate=40, enemy=Posture(plan_pv_landed_2=1))
        self.assertLess(self.number("nd_pv_destroyed_lo", them), self.number("nd_pv_destroyed_hi", them))

    def test_leadership_chance_matches_the_mirror(self):
        for estimate in (0, 5, 30):
            for sat in (False, True):
                them = Posture(public_estimate=estimate, satellite_communications=sat, stockpile=99, survivability=5,
                               reliability=10)
                target = self.number("nd_survivability_target", them)
                hi = self.number("nd_redundancy_believed", them)
                lo = self.number("nd_redundancy_believed_floor", them)
                self.assertTrue(math.isclose(hi, redundancy(estimate, sat, survivability=target)), estimate)
                self.assertTrue(math.isclose(lo, redundancy(estimate, sat, survivability=target * FLOOR_SHARE)),
                                estimate)
                self.assertLessEqual(lo, hi)
                for landed in (0, 2, 8, 25):
                    us = Posture(plan_pv_landed_3=landed, plan_pv_redundancy_lo=tenth(lo), plan_pv_redundancy_hi=tenth(hi))
                    low = self.number("nd_pv_decap_chance_lo", us)
                    high = self.number("nd_pv_decap_chance_hi", us)
                    self.assertEqual(low, math.floor(decapitation_chance(landed, tenth(hi)) + 0.5), (estimate, landed))
                    self.assertEqual(high, math.floor(decapitation_chance(landed, tenth(lo)) + 0.5), (estimate, landed))
                    self.assertLessEqual(low, high)

    def test_leadership_cases(self):
        """A chance only against Central Authorization and an arsenal the
        world knows of; the real salvo's gate is the same (nd_salvo_aftermath)."""
        self.assertEqual(squash(block(self.values, "nd_pv_leadership_case")),
                         "value = 1 if = { limit = { scope:nd_pv_enemy = { nd_believed_armed = no } } value = 3 } "
                         "else_if = { limit = { scope:nd_pv_enemy = { nd_authority_central = no } } value = 2 }")
        self.assertIn("scope:nd_salvo_victim = { nd_authority_central = yes nd_is_armed = yes }",
                      squash(block(self.effects, "nd_salvo_aftermath")))
        self.assertEqual(squash(block(self.values, "nd_pv_fires_first")),
                         "value = 0 if = { limit = { scope:nd_pv_enemy = { nd_authority_launch_on_warning = yes } } "
                         "value = 1 }")

    # ---- what it reads of the target -----------------------------------------------

    def test_preview_reads_only_the_worlds_view(self):
        """Everything read in the target's scope (scope:nd_pv_enemy.<value>,
        a scope:nd_pv_enemy = { } block, its states through the picker)
        reaches only public inputs: its estimate, its technology, its
        authority, readiness only in a crisis with us, its states. PrivateTest
        covers another country's panel; this covers our panel's reads of an
        enemy."""
        from test_nuclear_layout import _NAME_REF, _scripts
        graph = {**_scripts("script_values"), **_scripts("scripted_triggers"), **_scripts("scripted_effects")}
        entry = set()
        for name in ("nd_plan_preview", "nd_plan_preview_mission", "nd_plan_preview_warhead", "nd_pv_leadership_case",
                     "nd_pv_fires_first"):
            body = squash(graph[name])
            entry |= set(re.findall(r"scope:nd_pv_enemy\.(\w+)", body))
            # nd_plan_pv_store reads its VALUE as scope:nd_pv_enemy.$VALUE$.
            entry |= set(re.findall(r"nd_plan_pv_store = \{ NAME = \w+ VALUE = (\w+) \}", body))
            for m in re.finditer(r"scope:(?:nd_pv_enemy|target_state) = \{", body):
                depth, j = 1, m.end()
                while depth:
                    depth += {"{": 1, "}": -1}.get(body[j], 0)
                    j += 1
                entry |= set(_NAME_REF.findall(body[m.end():j - 1])) & graph.keys()
        entry &= graph.keys()  # scope:nd_pv_enemy.capital.region is the engine's
        for name in ("nd_salvo_pick_target", "nd_seen_stockpile", "nd_pv_destroyed_lo", "nd_pv_flown_hi",
                     "nd_redundancy_believed_floor", "nd_accuracy_mult_saved", "nd_believed_armed", "nd_pv_kill_value"):
            self.assertIn(name, entry, name)
        found, stack, seen = [], [(n, n) for n in entry], set()
        crisis = {f"nd_seen_readiness_factor_{s}": TestWorldsView.CRISIS_BRANCH.format(o)
                  for s, o in TestWorldsView.OBSERVERS.items()}
        while stack:
            name, path = stack.pop()
            if name in seen:
                continue
            seen.add(name)
            body = squash(graph[name])
            if name in crisis:
                body = body.replace(crisis[name], "")
            body = TestWorldsView.observed(body)
            found += [f"{path}: {m.group(0)}" for m in TestWorldsView.HIDDEN.finditer(body)]
            stack += [(ref, f"{path} > {ref}") for ref in set(_NAME_REF.findall(body)) & graph.keys() if ref != name]
        self.assertEqual(found, [], "the preview reads the target's true state")

    def test_hidden_inputs_change_nothing(self):
        us = Posture(plan_pv_landed_2=6, pgm=True)
        base = Posture(authority=3, public_estimate=12, enemy=us)
        names = [f"nd_pv_{k}_{e}" for k in ("destroyed", "flown", "kept") for e in ("lo", "hi")]
        names += ["nd_redundancy_believed", "nd_redundancy_believed_floor"]
        figures = {n: self.number(n, base) for n in names}
        for hidden in (dict(stockpile=50), dict(survivability=5), dict(safeguards=3), dict(reliability=20),
                       dict(readiness=3), dict(believed_stockpile=40)):
            for n in names:
                self.assertEqual(self.number(n, replace(base, **hidden)), figures[n], (n, hidden))

    # ---- the panel ----------------------------------------------------------------

    def range_key(self, name):
        """The custom loc that prints a range, and its two keys."""
        body = squash(block(self.custom, f"nd_pv_{name}_range"))
        self.assertEqual(body, f"type = country random_valid = no text = {{ trigger = {{ has_variable = nd_plan_pv_{name}_hi "
                               f"var:nd_plan_pv_{name}_hi > var:nd_plan_pv_{name}_lo }} localization_key = "
                               f"nd_w_strike_pv_{name}_range }} text = {{ trigger = {{ always = yes }} "
                               f"localization_key = nd_w_strike_pv_{name}_one }}")
        return loc_value(f"nd_w_strike_pv_{name}_range"), loc_value(f"nd_w_strike_pv_{name}_one")

    def test_every_range_prints_both_ends_and_says_so(self):
        for name in PREVIEW_RANGES:
            both, one = self.range_key(name)
            self.assertLess(both.index(f"Var('nd_plan_pv_{name}_lo')"), both.index(f"Var('nd_plan_pv_{name}_hi')"), name)
            self.assertIn("–", both, name)
            self.assertIn(f"Var('nd_plan_pv_{name}_lo')", one, name)
            # A figure about the target from the world's view carries its hover (owner call 14).
            for text in (both, one):
                if name in WORLDS_VIEW_RANGES:
                    self.assertTrue(text.startswith("#tooltippable;tooltip:nd_tt_worlds_view "), (name, text))
                else:
                    self.assertNotIn("nd_tt_worlds_view", text, name)
            # Owner call 14: a single figure keeps its qualifier, the cautious
            # end's: at least what a strike destroys, up to what is left to them.
            if name in WORLDS_VIEW_RANGES:
                qualifier = "at least" if name in ("destroyed", "decap") else "up to"
                self.assertTrue(one.startswith(f"#tooltippable;tooltip:nd_tt_worlds_view {qualifier} #v "), (name, one))

    def test_each_mission_has_a_preview_row(self):
        gui = read(GUI)
        sec = gui[gui.index("type te_nuclear_sec_strike"):gui.index("type te_nuclear_sec_world_crises")]
        for m in (1, 2, 3):
            choice = sec.index(f'text = "nd_w_strike_mission_{m}"')
            row = sec[sec.index("nd_row = {", choice):]
            row = row[:row.index('tooltip = "nd_w_strike_pv_')+40]
            self.assertLess(choice, sec.index(f'text = "nd_w_strike_pv_{m}_value"'))
            if m < 3:
                self.assertLess(sec.index(f'text = "nd_w_strike_pv_{m}_value"'), sec.index(f'text = "nd_w_strike_mission_{m + 1}"'))
            self.assertIn("GetScriptedGui('nd_plan_preview_sgui').IsShown", row, m)
            self.assertIn('text = "nd_w_strike_pv_label"', row, m)
            self.assertIn(f'tooltip = "nd_w_strike_pv_{m}_tt"', row, m)
        self.assertEqual(squash(block(strip_comments(read(SGUIS)), "nd_plan_preview_sgui")),
                         "scope = country is_shown = { has_variable = nd_plan_pv_landed_1 } is_valid = { always = no } "
                         "ai_is_valid = { always = no } effect = { }")

    def test_the_hovers_print_their_figures(self):
        # The size the figures were stored for, not the live one (PR 1b review).
        self.assertIn("set_variable = { name = nd_plan_pv_size value = nd_salvo_size_value }",
                      squash(block(strip_comments(read(EFFECTS)), "nd_plan_preview")))
        size = "Var('nd_plan_pv_size').GetValue"
        cities = loc_value("nd_w_strike_pv_1_tt")
        for needle in (size, "Var('nd_plan_pv_landed_1')", "Var('nd_plan_pv_deaths_1')", "GetCustom('nd_pv_raze_range')"):
            self.assertIn(needle, cities, needle)
        self.assertIn("Var('nd_plan_pv_landed_1')", loc_value("nd_w_strike_pv_1_value"))
        self.assertIn("Var('nd_plan_pv_deaths_1')", loc_value("nd_w_strike_pv_1_value"))
        forces = loc_value("nd_w_strike_pv_2_tt")
        for needle in (size, "Var('nd_plan_pv_landed_2')", "Var('nd_plan_pv_deaths_2')", "Var('nd_plan_pv_warheads')",
                       "GetCustom('nd_pv_destroyed_range')", "GetCustom('nd_pv_kept_range')",
                       "GetCustom('nd_pv_flown_line')", "ScriptValue('nd_k_ratio')", "GetCustom('nd_pv_k_force_part')",
                       "GetCustom('nd_pv_k_tech_part')", "GetCustom('nd_pv_silo_line')"):
            self.assertIn(needle, forces, needle)
        self.assertIn("GetCustom('nd_pv_destroyed_range')", loc_value("nd_w_strike_pv_2_value"))
        leadership = loc_value("nd_w_strike_pv_3_tt")
        for needle in (size, "Var('nd_plan_pv_landed_3')", "Var('nd_plan_pv_deaths_3')",
                       "GetCustom('nd_pv_leadership_line')"):
            self.assertIn(needle, leadership, needle)
        cut = loc_value("nd_w_strike_pv_3_line_cut")
        self.assertIn("GetCustom('nd_pv_redundancy_range')", cut)
        self.assertIn("GetCustom('nd_pv_decap_range')", cut)
        # Our ratio's parts, and the silo line while their silos are found.
        for part, value in (("force", "nd_k_ratio_force_part"), ("tech", "nd_k_ratio_tech_part")):
            self.assertEqual(squash(block(self.custom, f"nd_pv_k_{part}_part")),
                             f"type = country random_valid = no text = {{ trigger = {{ {value} > 0 }} localization_key = "
                             f"nd_w_strike_pv_k_{part} }} text = {{ trigger = {{ always = yes }} localization_key = nd_empty }}")
            self.assertIn(f"ScriptValue('{value}')", loc_value(f"nd_w_strike_pv_k_{part}"))
        self.assertEqual(squash(block(self.custom, "nd_pv_silo_line")),
                         "type = country random_valid = no text = { trigger = { has_variable = nd_plan_pv_accuracy "
                         "var:nd_plan_pv_accuracy > 1 } localization_key = nd_w_strike_pv_silo_line } text = { "
                         "trigger = { always = yes } localization_key = nd_empty }")
        self.assertIn("Var('nd_plan_pv_accuracy')", loc_value("nd_w_strike_pv_silo_line"))
        self.assertIn("GetCustom('nd_pv_flown_range')", loc_value("nd_w_strike_pv_flown_line"))
        self.assertEqual(squash(block(self.custom, "nd_pv_flown_line")),
                         "type = country random_valid = no text = { trigger = { var:nd_plan_pv_fires_first ?= 1 } "
                         "localization_key = nd_w_strike_pv_flown_line } text = { trigger = { always = yes } "
                         "localization_key = nd_empty }")
        for custom in ("nd_pv_leadership_line", "nd_pv_leadership_value"):
            body = squash(block(self.custom, custom))
            for case in (1, 2, 3):
                self.assertIn(f"var:nd_plan_pv_case ?= {case}", body, (custom, case))
        # Each is labelled an estimate.
        for m in (1, 2, 3):
            self.assertIn("Estimate", loc_value(f"nd_w_strike_pv_{m}_tt"), m)
        self.assertEqual(loc_value("nd_w_strike_pv_label"), "Estimate")


class TestSalvoScale(unittest.TestCase):
    """A salvo's UN record, infamy, world relations and taboo knock are a
    single strike's figure times sqrt(warheads landed) (owner, 2026-10-28)."""

    SINGLE = {
        "nd_salvo_un_order_first": "-4",
        "nd_salvo_un_order_answer": "-2",
        "nd_salvo_un_shock": "-3",
        "nd_salvo_dossier_first": "un_dos_points_first_strike",
        "nd_salvo_dossier_answer": "un_dos_points_retaliation",
        "nd_salvo_infamy": "nd_taboo_infamy_strategic",
        "nd_salvo_world_relations": "nd_taboo_world_relations_strategic",
    }

    def test_scaled_values_are_the_single_strike_times_sqrt(self):
        values = (ROOT / "common/script_values/nuclear_deterrence_values.txt").read_text(encoding="utf-8-sig")
        strike = (ROOT / "common/scripted_effects/extra_effects.txt").read_text(encoding="utf-8-sig")
        for name, single in self.SINGLE.items():
            m = re.search(r"(?m)^" + name + r" = \{(.*?)^\}", values, re.S)
            self.assertIsNotNone(m, name)
            body = " ".join(" ".join(line.split("#", 1)[0] for line in m.group(1).splitlines()).split())
            self.assertIn(f"value = {single} multiply = var:nd_salvo_sqrt", body, name)
            # The single strike still uses that figure.
            self.assertIn(single, strike, name)


class TestCalibration(unittest.TestCase):
    """K against the arsenals the AI builds (owner, 2026-10-28: keep K, check
    it here). AI great powers want about 5 to 20 warheads."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def left_after(self, victim):
        return victim.stockpile - self.model.number("nd_counterforce_destroyed_raw", victim)

    def test_one_warhead_cannot_disarm_a_large_arsenal(self):
        attacker = Posture(salvo_forces_landed=1, icbms=True, pgm=True)
        victim = Posture(readiness=3, authority=1, survivability=0, stockpile=20, enemy=attacker)
        self.assertGreaterEqual(self.left_after(victim), 18)

    def test_hardened_great_power_keeps_a_second_strike(self):
        attacker = Posture(salvo_forces_landed=20, icbms=True, pgm=True)
        target = self.model.number("nd_survivability_target", Posture())
        victim = Posture(readiness=2, authority=1, survivability=target, stockpile=20, enemy=attacker)
        self.assertGreaterEqual(self.left_after(victim), 3)

    def test_unhardened_small_arsenal_can_be_disarmed(self):
        attacker = Posture(salvo_forces_landed=3, icbms=True, pgm=True)
        victim = Posture(readiness=3, authority=1, survivability=0, stockpile=5, enemy=attacker)
        self.assertEqual(self.left_after(victim), 0)



class TestAiSalvo(unittest.TestCase):
    """The AI's missions by rule (owner, 2026-10-28; rework spec §9, §14.4).
    The attacker is the posture; scope:nd_sv_enemy its enemy."""

    @classmethod
    def setUpClass(cls):
        cls.model = RiskModel()

    def mission(self, **attacker):
        return self.model.number("nd_ai_salvo_mission_value", Posture(**attacker))

    # An enemy with bombers alone: the world takes its survivability at their
    # target of 25, so its command adds 1.25 whatever it has hardened.
    BOMBERS = dict(radar=False, icbms=False, missile_submarines=False, missile_defense=False, survivability=0)

    def test_mission_rule(self):
        # A large, well-connected enemy under Central Authorization: R = 1 + 3
        # + 2 + 1.25 = 7.25, from the world's view (delivery spec owner call 13).
        hard = Posture(authority=1, believed_stockpile=30, public_estimate=30, satellite_communications=True,
                       mainframe=False, **self.BOMBERS)
        self.assertTrue(math.isclose(self.model.number("nd_redundancy_believed", hard), 7.25))
        # A small one: R = 1 + 0.3 + 1.25 = 2.55.
        small = Posture(authority=1, believed_stockpile=3, public_estimate=3, satellite_communications=False,
                        mainframe=False, **self.BOMBERS)
        self.assertTrue(math.isclose(self.model.number("nd_redundancy_believed", small), 2.55))
        delegated = replace(hard, authority=2)
        # Existential deterrence, an enemy it cannot decapitate: the single strike.
        self.assertEqual(self.mission(doctrine=2, stockpile=9, enemy=hard), 1)
        # Warfighting or Flexible First Use against an enemy believed armed: Forces.
        self.assertEqual(self.mission(doctrine=5, stockpile=9, enemy=delegated), 2)
        self.assertEqual(self.mission(doctrine=3, stockpile=9, enemy=delegated), 2)
        self.assertEqual(self.mission(doctrine=3, stockpile=9, enemy=replace(delegated, believed_armed=False)), 1)
        # Leadership when spare x the capital's hit chance outnumbers R, over Forces.
        self.assertEqual(self.mission(doctrine=5, stockpile=9, capital_hit_share=0.9, enemy=small), 3)
        self.assertEqual(self.mission(doctrine=2, stockpile=9, capital_hit_share=0.9, enemy=small), 3)
        # Six spare at 0.9 is 5.4, short of 7.25: Forces under Warfighting, else the single strike.
        self.assertEqual(self.mission(doctrine=5, stockpile=9, capital_hit_share=0.9, enemy=hard), 2)
        self.assertEqual(self.mission(doctrine=2, stockpile=9, capital_hit_share=0.9, enemy=hard), 1)
        # Not under Central: never Leadership.
        self.assertEqual(self.mission(doctrine=2, stockpile=30, capital_hit_share=1, enemy=replace(small, authority=3)), 1)
        # No spare warhead: no salvo.
        self.assertEqual(self.mission(doctrine=5, stockpile=1, enemy=delegated), 1)
        # A country without warheads has no launch authority to cut off
        # (final review): never Leadership, whatever its nd_authority reads.
        self.assertEqual(self.mission(doctrine=2, stockpile=9, capital_hit_share=0.9,
                                      enemy=replace(small, believed_armed=False)), 1)
        # Leadership needs the capital in reach (plan 4a R6): Forces under
        # Warfighting, else the single strike.
        self.assertEqual(self.mission(doctrine=5, stockpile=9, capital_hit_share=0.9, capital_in_reach=False,
                                      enemy=small), 2)
        self.assertEqual(self.mission(doctrine=2, stockpile=9, capital_hit_share=0.9, capital_in_reach=False,
                                      enemy=small), 1)

    def test_spare_keeps_a_reserve(self):
        spare = {s: self.model.number("nd_ai_salvo_spare_value", Posture(stockpile=s)) for s in (1, 2, 3, 9, 10, 30)}
        self.assertEqual(spare, {1: 0, 2: 1, 3: 2, 9: 6, 10: 7, 30: 20})

    def test_sizes(self):
        size = self.model.number
        # Forces: ceil(believed / K), here 10 / 2, within the spare.
        enemy = Posture(authority=2, believed_stockpile=10)
        self.assertEqual(size("nd_ai_salvo_size_value", Posture(doctrine=5, stockpile=30, icbms=True, pgm=True,
                                                                 enemy=enemy)), 5)
        self.assertEqual(size("nd_ai_salvo_size_value", Posture(doctrine=5, stockpile=30, icbms=False, pgm=False,
                                                                 enemy=replace(enemy, believed_stockpile=7))), 7)
        self.assertEqual(size("nd_ai_salvo_size_value", Posture(doctrine=5, stockpile=6, icbms=True, pgm=True,
                                                                 enemy=enemy)), 4)
        # Leadership: enough to land 2R on the capital, here 2 x 2.55 / 0.9,
        # 5.67, so 6, all six spare.
        small = Posture(authority=1, believed_stockpile=3, public_estimate=3, satellite_communications=False,
                        mainframe=False, **self.BOMBERS)
        self.assertEqual(size("nd_ai_salvo_size_value", Posture(stockpile=9, capital_hit_share=0.9, enemy=small)), 6)
        # At a hit share of 0.4 (final review): 5.1 / 0.4 is 12.75, so 13,
        # where ceil(2R) alone would land 2.4, under R.
        self.assertEqual(size("nd_ai_salvo_size_value", Posture(stockpile=30, capital_hit_share=0.4, enemy=small)),
                         13)

    def test_accept_effect_routes_ai_missions(self):
        nuke = (ROOT / "common/diplomatic_actions/nuke.txt").read_text(encoding="utf-8-sig")
        nuke = "\n".join(line.split("#", 1)[0] for line in nuke.splitlines())
        start = nuke.index("accept_effect = {")
        accept = " ".join(nuke[start:nuke.index("is_hostile = yes", start)].split())
        self.assertIn("scope:target_country = { save_scope_as = nd_sv_enemy }", accept)
        ai = accept[accept.index("is_ai = yes"):accept.index("else_if")]
        for needle in ("nd_ai_salvo_mission_value > 1", "hidden_effect = {",
                       "set_variable = { name = nd_salvo_mission value = nd_ai_salvo_mission_value }",
                       "set_variable = { name = nd_salvo_size value = nd_ai_salvo_size_value }",
                       "scope:target_country = { save_scope_as = nd_salvo_victim }", "nd_order_salvo = yes",
                       "remove_variable = nd_salvo_mission", "remove_variable = nd_salvo_size"):
            self.assertIn(needle, ai, needle)
        self.assertLess(accept.index("save_scope_as = nd_sv_enemy"), accept.index("is_ai = yes"))
        single = accept[accept.index("else_if"):]
        self.assertIn("nuclear_first_strike = yes", single)
        self.assertIn("nd_record_nuclear_use = { VICTIM = scope:target_country }", single)


if __name__ == "__main__":
    unittest.main()
