"""The Creditors' Consortium power bloc identity (2026-11-16): the structure that matters.

Design: docs/superpowers/specs/2026-11-16-power-bloc-identities-design.md § 5.
System: docs/systems/mod_systems/power_blocs.md § "Creditors' Consortium".

Pins the identity's pieces, its two principle groups and their tiers, the law
clauses (structural adjustment's can_impose, the leader's locks), the
monetary layer's hooks and the order of the default call, the generated
monopoly ladder, the rescue events and their self-checks.

Run: env -u PYTHONPATH .venv/bin/python -m pytest test_creditors_consortium.py -q
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import gen_cred_monopoly_ladder as ladder  # noqa: E402

IDENTITY = "identity_creditors_consortium"
GROUPS_FILE = "common/power_bloc_principle_groups/extra_power_bloc_principle_groups.txt"
OWN_GROUPS_FILE = "common/power_bloc_principle_groups/te_creditors_consortium_principle_groups.txt"
PRINCIPLES_FILE = "common/power_bloc_principles/te_creditors_consortium_principles.txt"
TRIGGERS = "common/scripted_triggers/te_creditors_consortium_triggers.txt"
VALUES = "common/script_values/te_creditors_consortium_values.txt"
EFFECTS = "common/scripted_effects/te_creditors_consortium_effects.txt"
LAWS = "common/laws/te_creditors_consortium_law_injections.txt"
EVENTS = "events/te_creditors_consortium_events.txt"
PLAYTEST = "docs/testing/power-bloc-identities-playtest.md"

# The laws a consortium's leader may impose on a member in its receivership
# (§ 5.3.1): the economic system, trade policy and taxation groups, without
# Command Economy (the leader can't hold it) or Isolationism's variant skins.
IMPOSABLE = [
    "law_traditionalism", "law_interventionism", "law_agrarianism", "law_industry_banned",
    "law_extraction_economy", "law_laissez_faire", "law_cooperative_ownership",
    "law_mercantilism", "law_protectionism", "law_free_trade", "law_isolationism",
    "law_consumption_based_taxation", "law_land_based_taxation", "law_per_capita_based_taxation",
    "law_proportional_taxation", "law_graduated_taxation",
]

# The tier tables (§ 5.4): Conditionality's terms, remittance (share of GDP a
# month), monopolies and months to exit; Development Lending's share and the
# receivers' construction.
CONDITIONALITY = {
    1: (1, 0.001, 1, 12), 2: (1, 0.0015, 1, 18), 3: (2, 0.0015, 2, 24), 4: (2, 0.002, 2, 30), 5: (3, 0.0025, 3, 36),
}
DEVELOPMENT_LENDING = {1: (0.05, 0), 2: (0.075, 0.05), 3: (0.10, 0.10), 4: (0.125, 0.15), 5: (0.15, 0.20)}

SELF_CHECKS = ("cc_receivership_treaty", "cc_monopoly_treaty", "cc_adjustment_imposition")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def strip_comments(text: str) -> str:
    return re.sub(r"#[^\n]*", "", text)


def block_at(text: str, start: int) -> str:
    """The brace block that opens at or after `start`, braces included."""
    i = text.index("{", start)
    depth, j = 0, i
    while True:
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        j += 1
        if depth == 0:
            return text[i:j]


def entity(text: str, name: str) -> str:
    m = re.search(r"(?m)^(?:INJECT:|REPLACE:)?" + re.escape(name) + r"\s*=\s*\{", text)
    if not m:
        raise AssertionError(f"{name} not found")
    return block_at(text, m.start())


def num(text: str, key: str) -> float:
    m = re.search(r"\b" + re.escape(key) + r"\s*=\s*(-?[\d.]+)", text)
    if not m:
        raise AssertionError(f"{key} not in block")
    return float(m.group(1))


class IdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.identity = strip_comments(entity(read("common/power_bloc_identities/extra_power_bloc_identities.txt"), IDENTITY))

    def test_marker_and_its_type(self):
        self.assertIn("power_bloc_debt_administration_bool = yes", self.identity)
        marker = entity(read("common/modifier_type_definitions/power_bloc_extra_modifier_types.txt"),
                        "power_bloc_debt_administration_bool")
        self.assertIn("boolean = yes", marker)
        self.assertIn("script_only = yes", marker)

    def test_visible_only_under_full_banking(self):
        visible = block_at(self.identity, self.identity.index("visible = {"))
        self.assertIn("te_mon_full_system = yes", visible)
        self.assertIn("has_dlc_feature = power_bloc_features", visible)

    def test_founder_is_a_valid_backstop_provider(self):
        possible = block_at(self.identity, self.identity.index("possible = {"))
        self.assertIn("te_mon_backstop_provider_valid = yes", possible)

    def test_can_leave(self):
        can_leave = block_at(self.identity, self.identity.index("can_leave = {"))
        self.assertIn("NOT = { te_cred_in_leaders_receivership = yes }", can_leave)
        self.assertIn("te_cred_guarantee_forfeit = yes", can_leave)
        self.assertRegex(can_leave, r"leverage_advantage = \{\s*target = root\s*value <= 30\s*\}")

    def test_cohesion_terms(self):
        cohesion = block_at(self.identity, self.identity.index("cohesion = {"))
        for desc in ("POWER_BLOC_COHESION_BASE", "POWER_BLOC_COHESION_CREDITORS_SHARE_GDP",
                     "POWER_BLOC_COHESION_CREDITORS_LEADER_DEBT", "POWER_BLOC_COHESION_WORST_LEADER_RELATIONS",
                     "POWER_BLOC_COHESION_CREDITORS_RECEIVERSHIP", "POWER_BLOC_COHESION_CREDITORS_COMMAND_ECONOMY",
                     "POWER_BLOC_COHESION_CREDITORS_LEADER_DEFAULT"):
            with self.subTest(desc=desc):
                self.assertIn(f"desc = {desc}", cohesion)
        # the member walks count a prospective member in and a leaving one out
        # (the GDP share, the relations, and the two member walks)
        self.assertEqual(cohesion.count("exists = scope:with_country"), 4)
        self.assertEqual(cohesion.count("exists = scope:without_country"), 4)

    def test_subjugation_axis(self):
        self.assertIn("country_subjugation_creditor_strength_add = 0.4", self.identity)
        identity_part = entity(read("common/script_values/extra_script_values.txt"), "te_subjugation_strength_identity")
        self.assertIn("identity:identity_creditors_consortium", identity_part)
        self.assertIn("modifier:country_subjugation_creditor_strength_add", identity_part)
        concept = [l for l in read("localization/english/te_concepts_l_english.yml").splitlines()
                   if l.startswith(" concept_subjugation_strength_desc:")][0]
        self.assertIn("$identity_creditors_consortium$: #v +0.40#!", concept)

    def test_own_icon(self):
        self.assertIn('icon = "gfx/interface/icons/central_identity_pillars_icons/identity_creditors_consortium.dds"',
                      self.identity)


class PrincipleGroupsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = strip_comments(read(GROUPS_FILE))
        cls.own = strip_comments(read(OWN_GROUPS_FILE))
        cls.principles = strip_comments(read(PRINCIPLES_FILE))

    def test_new_groups_are_primary_and_locked(self):
        for group in ("principle_group_conditionality", "principle_group_development_lending"):
            with self.subTest(group=group):
                body = entity(self.own, group)
                self.assertIn(f"primary_for_identity = {IDENTITY}", body)
                self.assertEqual(re.findall(r"unlocking_identity = (\w+)", body), [IDENTITY])

    def test_existing_groups_become_primary(self):
        for group in ("principle_group_foreign_investment", "principle_group_monetary_union"):
            with self.subTest(group=group):
                body = entity(self.shared, group)
                self.assertIn(f"primary_for_identity = {IDENTITY}", body)
                self.assertNotIn("unlocking_identity", body)   # still open to every identity

    def test_explicit_unlock_lists(self):
        for group, wanted in (("principle_group_vassalization", True), ("principle_group_colonial_offices", True),
                              ("principle_group_sacred_civics", False)):
            with self.subTest(group=group):
                self.assertEqual(f"unlocking_identity = {IDENTITY}" in entity(self.shared, group), wanted)

    def test_conditionality_tiers(self):
        for tier, (terms, remit, mono, months) in CONDITIONALITY.items():
            with self.subTest(tier=tier):
                body = entity(self.principles, f"principle_conditionality_{tier}")
                self.assertIn(f"principle_tier_{tier}.dds", body)
                self.assertIn("te_pb_principle_slot_free = { GROUP = principle_group_conditionality }", body)
                self.assertIn("te_mon_full_system = yes", block_at(body, body.index("visible = {")))
                self.assertEqual(num(body, "power_bloc_te_cred_rescue_terms_add"), terms)
                self.assertAlmostEqual(num(body, "power_bloc_te_cred_remittance_add"), remit)
                self.assertEqual(num(body, "power_bloc_te_cred_monopolies_add"), mono)
                self.assertEqual(num(body, "power_bloc_te_cred_receivership_months_add"), months)
                self.assertEqual("country_igo_pb_principles_bool" in body, tier == 4)
                self.assertEqual("country_globalization_pb_principles_bool" in body, tier == 5)

    def test_development_lending_tiers(self):
        modifiers = strip_comments(read("common/static_modifiers/te_creditors_consortium_modifiers.txt"))
        for tier, (share, construction) in DEVELOPMENT_LENDING.items():
            with self.subTest(tier=tier):
                body = entity(self.principles, f"principle_development_lending_{tier}")
                self.assertIn(f"principle_tier_{tier}.dds", body)
                self.assertIn("te_pb_principle_slot_free = { GROUP = principle_group_development_lending }", body)
                self.assertAlmostEqual(num(body, "power_bloc_te_cred_dl_share_add"), share)
                self.assertEqual("country_keynesian_pb_principles_bool" in body, tier == 4)
                self.assertEqual("country_globalization_pb_principles_bool" in body, tier == 5)
                if construction:
                    self.assertAlmostEqual(num(body, "power_bloc_te_cred_dl_construction_add"), construction)
                    paid = entity(modifiers, f"te_cred_dl_receiver_{tier}")
                    self.assertAlmostEqual(num(paid, "state_construction_mult"), construction)
                else:
                    self.assertNotIn("power_bloc_te_cred_dl_construction_add", body)

    def test_scripts_pay_what_the_tiers_print(self):
        values = strip_comments(read(VALUES))
        share = entity(values, "te_cred_dl_share")
        for tier, (figure, _) in DEVELOPMENT_LENDING.items():
            self.assertIn(f"value = {figure:g}" if figure != 0.10 else "value = 0.10", share)
        self.assertEqual(re.findall(r"value = (\d)", entity(values, "te_cred_terms_allowed")), ["0", "3", "2", "1"])
        self.assertEqual(re.findall(r"value = (\d)", entity(values, "te_cred_monopolies_allowed")), ["0", "3", "2", "1"])
        take = entity(values, "te_cred_take_extra_own")
        self.assertEqual(re.findall(r"value = ([\d.]+)", take)[2:], ["0.0015", "0.001", "0.0005"])
        exit_ = entity(values, "te_cred_exit_extra_own")
        self.assertEqual(re.findall(r"value = (\d+)", exit_)[2:], ["24", "18", "12", "6"])

    def test_unlock_descriptions_read_every_principle_file(self):
        import gen_pb_principle_unlock_descs as gen   # noqa: E402  (root module)
        rows = gen.collect_principle_unlocks()
        groups = {(b, g) for b, g, _t, _p in rows}
        self.assertIn(("country_igo_pb_principles_bool", "principle_group_conditionality"), groups)
        self.assertIn(("country_keynesian_pb_principles_bool", "principle_group_development_lending"), groups)


class LawsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laws = strip_comments(read(LAWS))
        cls.vanilla = json.loads(read("vanilla_parsed/common/laws.json"))

    def test_can_impose_on_every_imposable_law(self):
        injected = re.findall(r"(?m)^INJECT:(\w+) = \{", self.laws)
        self.assertEqual(sorted(set(injected) - {"law_command_economy"}), sorted(IMPOSABLE))
        for law in IMPOSABLE:
            with self.subTest(law=law):
                body = entity(self.laws, law)
                impose = block_at(body, body.index("can_impose = {"))
                self.assertIn("can_impose_law_default = yes", impose)   # vanilla's subjects keep it
                self.assertIn("te_cred_can_impose_adjustment = yes", impose)
                vanilla = self.vanilla[law][1]
                self.assertNotIn("can_impose", vanilla)   # an INJECT can't add a second block
                self.assertEqual("ai_impose_chance" in body, "ai_impose_chance" not in vanilla)
                if "ai_impose_chance" in body:
                    self.assertIn(f"te_cred_ai_wants_adjustment_of = {{ LAW = {law} }}", body)

    def test_no_other_mod_file_adds_can_impose_to_them(self):
        for path in sorted((ROOT / "common/laws").glob("*.txt")):
            if path.name == Path(LAWS).name:
                continue
            text = strip_comments(path.read_text(encoding="utf-8-sig"))
            for law in IMPOSABLE:
                m = re.search(r"(?m)^(?:INJECT:|REPLACE:)?" + law + r" = \{", text)
                if m:
                    with self.subTest(file=path.name, law=law):
                        self.assertNotIn("can_impose", block_at(text, m.start()))

    def test_leader_locks(self):
        self.assertNotIn("can_enact", self.vanilla["law_command_economy"][1])
        command = entity(self.laws, "law_command_economy")
        self.assertIn("te_cred_leads_consortium = no", command)
        bank = strip_comments(entity(read("common/laws/extra_laws.txt"), "law_no_national_bank"))
        self.assertIn("te_cred_leads_consortium = no", block_at(bank, bank.index("can_enact = {")))

    def test_ladders_name_the_same_laws(self):
        differ = entity(read(TRIGGERS), "te_cred_leader_laws_differ")
        rungs = re.findall(r"te_cred_sc_imposition_rung = \{ LAW = (\w+) \}", read(EFFECTS))
        listed = sorted(set(re.findall(r"has_law = law_type:(\w+) \$TARGET\$", differ)))
        self.assertEqual(sorted(rungs), sorted(IMPOSABLE))
        self.assertEqual(listed, sorted(IMPOSABLE))


class MonetaryHooksTest(unittest.TestCase):
    def test_guarantee_is_a_backstop(self):
        backstop = entity(strip_comments(read("common/scripted_triggers/te_monetary_union_triggers.txt")),
                          "te_mon_has_effective_backstop")
        self.assertIn("te_cred_guarantee_is_effective = yes", backstop)
        guarantee = entity(strip_comments(read(TRIGGERS)), "te_cred_guarantee_is_effective")
        for line in ("te_mon_full_system = yes", "is_power_bloc_leader = no", "te_mon_is_command = no",
                     "te_cred_guarantee_forfeit = no", "te_mon_has_treaty_debt_relief = no",
                     "te_mon_backstop_provider_valid = yes", "te_cred_backer_has_reneged = no"):
            with self.subTest(line=line):
                self.assertIn(line, guarantee)

    def test_relief_is_paid_once(self):
        pays = entity(strip_comments(read(TRIGGERS)), "te_cred_guarantee_pays_relief")
        self.assertIn("te_mon_union_backstop_is_effective = no", pays)
        recipient = entity(strip_comments(read("common/script_values/te_monetary_arrangement_script_values.txt")),
                           "te_mon_arr_recipient_value")
        self.assertIn("add = te_cred_guarantee_relief", recipient)

    def test_discovery_hooks(self):
        discovery = strip_comments(entity(read("common/scripted_effects/te_monetary_arrangement_effects.txt"),
                                          "te_monetary_discover_arrangements"))
        receivership = discovery.index("has_type = debt_receivership")
        direct = discovery.index("te_cred_discover_direct_receivership = yes")
        costs = discovery.index("te_cred_discover_leader_costs = yes")
        self.assertLess(receivership, direct)
        self.assertLess(discovery.index("te_monetary_discover_union = yes"), costs)
        self.assertLess(costs, discovery.index("te_mon_arr_recipient_pts"))
        scan = discovery[discovery.rindex("te_mon_bloc_union_tier_1_plus = yes"):discovery.rindex("te_mon_arr_scan value = 1")]
        self.assertIn("te_cred_in_consortium = yes", scan)
        self.assertIn("has_variable = te_cred_direct_receivership", scan)

    def test_default_call_order(self):
        hook = strip_comments(entity(read("common/on_actions/te_monetary_on_actions.txt"), "te_monetary_on_country_default"))
        treaty = hook.index("te_mon_lolr_is_effective = yes")
        consortium = hook.index("te_cred_guarantee_is_effective = yes")
        union = hook.index("te_mon_union_backstop_is_effective = yes")
        self.assertLess(treaty, consortium)
        self.assertLess(consortium, union)
        self.assertIn("te_cred_call_consortium = yes", hook)
        self.assertNotRegex(hook, r"\belse = \{\s*var:te_mon_anchor")   # no unguarded anchor branch

    def test_receivership_terms_read_the_receiver(self):
        values = strip_comments(read("common/script_values/te_monetary_arrangement_script_values.txt"))
        self.assertIn("add = te_cred_receivership_take_extra", entity(values, "te_mon_receivership_take_share"))
        self.assertIn("add = te_cred_receivership_exit_extra", entity(values, "te_mon_receivership_exit_months"))


class RescueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = strip_comments(read(EVENTS))
        cls.call = entity(cls.events, "te_cc.1")

    def test_namespace(self):
        self.assertIn("namespace = te_cc", self.events)
        self.assertEqual(re.findall(r"(?m)^namespace = (\w+)", read("events/te_debug_cc_events.txt")), ["te_debug_cc"])

    def test_one_option_set_per_term_count(self):
        options = [block_at(self.call, m.start()) for m in re.finditer(r"\boption = \{", self.call)]
        counts = {}
        for option in options:
            m = re.search(r"te_cred_terms_pick_(\d) = yes", option)
            if not m:
                continue
            terms = re.search(r"ADJ = (yes|no) CONC = (yes|no) PRIV = (yes|no)", option).groups()
            self.assertEqual(terms.count("yes"), int(m.group(1)), option)
            counts.setdefault(int(m.group(1)), set()).add(terms)
        self.assertEqual(sorted(counts), [0, 1, 2, 3])
        self.assertEqual([len(counts[n]) for n in range(4)], [1, 3, 3, 1])
        refuse = [o for o in options if "te_cred_refuse_rescue = yes" in o]
        self.assertEqual(len(refuse), 1)
        for option in options:
            chance = block_at(option, option.index("ai_chance = {"))
            self.assertNotIn("if = {", chance)
            self.assertRegex(chance, r"base = \d+")

    def test_refusal_is_te_lolr_renege_without_the_treaty(self):
        refuse = strip_comments(entity(read(EFFECTS), "te_cred_refuse_rescue"))
        self.assertIn("te_mon_lolr_suspended_months value = te_mon_lolr_suspension_months", refuse)
        self.assertIn("add_cohesion_percent = -0.2", refuse)
        self.assertNotIn("change_infamy", refuse)
        self.assertLess(refuse.index("remove_modifier = te_mon_lolr_reneged"), refuse.index("add_modifier"))

    def test_member_refusal_is_a_cooling_off(self):
        refuse = strip_comments(entity(read(EFFECTS), "te_cred_refuse_terms"))
        self.assertIn("set_variable = { name = te_cred_terms_refused days = 3650 }", refuse)

    def test_treaties_are_checked_before_made(self):
        effects = strip_comments(read(EFFECTS))
        for helper in ("te_cred_make_receivership", "te_cred_grant_investment_rights", "te_cred_try_monopoly",
                       "te_cred_make_privatization"):
            with self.subTest(helper=helper):
                body = entity(effects, helper)
                self.assertLess(body.index("can_create_treaty = {"), body.index("create_treaty = {", body.index("can_create_treaty") + 20))
        self.assertIn("te_cred_set_direct_receivership = yes", entity(effects, "te_cred_make_receivership"))

    def test_self_checks_logged_and_listed(self):
        text = read(EVENTS) + read(EFFECTS)
        playtest = read(PLAYTEST)
        section = playtest[playtest.index("## Creditors' Consortium"):]
        for name in SELF_CHECKS:
            with self.subTest(name=name):
                self.assertIn(f"TE_SELF_CHECK OK {name}", text)
                self.assertIn(f"TE_SELF_CHECK BROKEN {name}", text)
                self.assertIn(f"`{name}`", section)

    def test_playtest_header(self):
        self.assertTrue(read(PLAYTEST).startswith(
            "# Power Bloc Identities: Play-Test List\n\n"
            "What only the running game can show for the Creditors' Consortium and the Research Commons\n"))


class GeneratedLadderTest(unittest.TestCase):
    def test_ladder_is_fresh(self):
        self.assertEqual(ladder.main(["--check"]), 0, "run scripts/generators/gen_cred_monopoly_ladder.py")

    def test_ladder_shape(self):
        text = read(str(ladder.OUT))
        self.assertTrue(text.startswith("# AUTO-GENERATED by scripts/generators/gen_cred_monopoly_ladder.py"))
        types = json.loads(read("vanilla_parsed/common/company_types.json"))
        self.assertIn("company_type:company_misr }", text)
        self.assertGreaterEqual(text.count("is_company_type = company_type:"), len(types))
        self.assertIn("te_cred_monopoly_ladder_generated = yes", read(EFFECTS))


class SharedPiecesTest(unittest.TestCase):
    def test_statue_and_hq(self):
        statue = entity(read("common/production_methods/extra_pms.txt"), "pm_power_bloc_statue_creditors_consortium")
        self.assertIn(f"unlocking_identity = {IDENTITY}", statue)
        self.assertIn("pm_power_bloc_statue_creditors_consortium", read("common/production_method_groups/extra_pm_groups.txt"))
        hq = entity(read("common/production_methods/unique_pms.txt"), "pm_hq_creditors_consortium")
        self.assertIn(f"unlocking_identity = {IDENTITY}", hq)
        self.assertIn("pm_hq_creditors_consortium", entity(read("common/production_method_groups/unique_pm_groups.txt"),
                                                            "pmg_power_bloc_hq"))

    def test_ai_invitation_score(self):
        score = strip_comments(entity(read("common/script_values/modified.txt"), "ai_power_bloc_identity_score"))
        part = score[score.index(f"identity:{IDENTITY}"):]
        self.assertIn('desc = "TE_DIPLOMATIC_ACCEPTANCE_CREDITOR_BACKING"', part)
        self.assertIn('desc = "TE_DIPLOMATIC_ACCEPTANCE_CREDITOR_COMMAND_ECONOMY"', part)
        self.assertIn("scope:actor.power_bloc ?=", score[score.rindex("if = {", 0, score.index(f"identity:{IDENTITY}")):])

    def test_nation_tab_registers_the_receiver_modifiers(self):
        text = read("scripts/generators/gen_nation_tab.py")
        self.assertEqual(text.count('"te_cred_dl_receiver_*"'), 2)   # a section and a source group


if __name__ == "__main__":
    unittest.main()
