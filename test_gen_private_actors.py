"""gen_private_actors: every company type's sector, the law table against the laws, the committed outputs, a
synthetic type end to end, and the script audits over the generated files.

Run: .venv/bin/python test_gen_private_actors.py
"""

import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import gen_private_actors as gen  # noqa: E402
import private_actors_config as cfg  # noqa: E402

# The groups the plan's Task 1 names, by key: the table must cover each, and no other.
COVERED = (
    "lawgroup_economic_system", "lawgroup_labor_rights", "lawgroup_childrens_rights",
    "lawgroup_labour_associations", "lawgroup_ministry_of_labor", "lawgroup_antitrust",
    "lawgroup_resource_transition", "lawgroup_automation_policy", "lawgroup_intellectual_property",
    "lawgroup_financial_regulation", "lawgroup_electoral_finance",
)
OUTPUTS = (gen.EFFECTS_OUT, gen.TRIGGERS_OUT, gen.VALUES_OUT, gen.CUSTOM_LOC_OUT)

_STATE = None


def state():
    global _STATE
    if _STATE is None:
        _STATE = gen.load_state(ROOT)
    return _STATE


def read(rel: Path) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def block(text: str, name: str) -> str:
    """The body of the top-level `name = { … }` block."""
    m = re.search(rf"^{re.escape(name)} = \{{", text, re.M)
    if not m:
        raise AssertionError(f"no {name} block")
    depth, i = 0, m.end() - 1
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[m.end():i]
        i += 1


_ASSESS: dict = {}


def branch(effects: str, company: str) -> str:
    """te_pa_gen_assess's branch for one company type."""
    if effects not in _ASSESS:
        _ASSESS[effects] = block(effects, "te_pa_gen_assess")
    body = _ASSESS[effects]
    m = re.search(rf"\n\t(?:if|else_if) = \{{\n\t\tlimit = \{{ is_company_type = company_type:{company} \}}\n", body)
    if not m:
        raise AssertionError(f"no branch for {company}")
    end = body.find("\n\t}", m.end())
    return body[m.end():end]


class CoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = gen.Data.from_state(state())
        cls.plan = gen.build_plan(state())
        cls.by_company = {s.company: s for s in cls.plan.sectors}
        cls.effects = read(gen.EFFECTS_OUT)

    def test_every_company_type_has_a_branch_or_a_reason(self):
        types = set(self.data.company_types)
        self.assertGreater(len(types), 300)  # vanilla's and the mod's, merged
        assess = block(self.effects, "te_pa_gen_assess")
        for company in sorted(types):
            with self.subTest(company=company):
                if company in cfg.EXCLUDED_COMPANY_TYPES:
                    self.assertTrue(cfg.EXCLUDED_COMPANY_TYPES[company].strip())
                    self.assertNotIn(f"company_type:{company} }}", assess)
                else:
                    self.assertIn(company, self.by_company)
                    branch(self.effects, company)

    def test_flavored_generic_and_mod_types_are_covered(self):
        for company in ("company_basic_steel", "company_krupp", "company_softbank", "company_east_india_company"):
            self.assertIn(company, self.by_company)

    def test_every_sector_is_non_empty(self):
        for s in self.plan.sectors:
            with self.subTest(company=s.company):
                self.assertTrue(s.buildings)
                self.assertIsNotNone(s.output)
                self.assertGreater(s.jobs, 0)
                self.assertTrue(s.techs)

    def test_excluded_types_exist(self):
        for company in cfg.EXCLUDED_COMPANY_TYPES:
            self.assertIn(company, self.data.company_types)
        self.assertIn("company_gm_name_carrier", block(read(gen.TRIGGERS_OUT), "te_pa_gen_excluded_type"))

    def test_known_sectors(self):
        steel = self.by_company["company_basic_steel"]
        self.assertEqual(steel.inputs, ("iron", "coal"))
        self.assertEqual(steel.output, "steel")
        self.assertIn("manufacturing", steel.features)
        self.assertIn("rm_industry_banned", steel.features)
        coal = self.by_company["company_bengal_coal_company"]
        self.assertEqual(coal.output, "coal")
        self.assertIn("fossil", coal.features)
        self.assertIn("extraction", coal.features)
        rail = self.by_company["company_gwr"]
        self.assertTrue(rail.output_local)
        self.assertIn("infrastructure", rail.features)

    def test_inputs_leave_out_local_own_and_listed_goods(self):
        for s in self.plan.sectors:
            made = set()
            for b in s.buildings:
                made |= set(gen.read_building(self.data, b).outputs)
            for good in s.inputs:
                with self.subTest(company=s.company, good=good):
                    self.assertFalse(self.data.is_local(good))
                    self.assertNotIn(good, made)
                    self.assertNotIn(good, cfg.INPUTS_LEFT_OUT)

    def test_every_feature_marks_some_type(self):
        for name in cfg.FEATURES:
            with self.subTest(feature=name):
                self.assertTrue(any(name in s.features for s in self.plan.sectors))

    def test_law_derived_feature_sets_read_something(self):
        sets = gen.law_sets(self.data)
        self.assertIn("building_steel_mill", sets["removes"]["law_industry_banned"])
        self.assertIn("building_power_plant", sets["removes"]["law_industry_banned"])
        self.assertNotIn("building_power_plant", sets["removes"]["law_extraction_economy"])
        self.assertEqual(sets["subsidizes"]["law_interventionism"], {"building_airport", "building_highway"})
        self.assertIn("bg_manufacturing", sets["collectivizes"]["law_factory_councils"])

    def test_financial_companies_exist(self):
        for company in cfg.FEATURES["financial"].companies:
            self.assertIn(company, self.data.company_types)

    def test_base_method_is_the_default_or_the_first(self):
        # The trade center's trade-quantity group lists its default second.
        self.assertEqual(self.data.base_method("pmg_trade_quantity_trade_center"), "pm_trade_center_trade_quantity_normal")
        self.assertEqual(self.data.base_method("pmg_mining_equipment_building_coal_mine"),
                         "pm_picks_and_shovels_building_coal_mine")


class LawTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = gen.Data.from_state(state())

    def test_covered_groups(self):
        self.assertEqual(tuple(cfg.LAW_TABLE), COVERED)
        self.assertFalse(set(cfg.EXCLUDED_LAW_GROUPS) & set(COVERED))
        for group, why in cfg.EXCLUDED_LAW_GROUPS.items():
            self.assertTrue(self.data.laws_of(group), group)
            self.assertTrue(why.strip())

    def test_every_law_of_a_covered_group_has_a_row(self):
        """A law added to a covered group fails here until private_actors_config signs it."""
        for group in COVERED:
            with self.subTest(group=group):
                laws = self.data.laws_of(group)
                self.assertTrue(laws)
                self.assertEqual(sorted(cfg.LAW_TABLE[group]), sorted(laws))

    def test_every_row_has_its_reason_and_known_terms(self):
        for group, rows in cfg.LAW_TABLE.items():
            for law, row in rows.items():
                with self.subTest(law=law):
                    self.assertTrue(row.why.strip())
                    for term in row.terms:
                        self.assertIn(term.kind, ("feature", "all", "when", "labor", "campaign"))
                        self.assertNotEqual(term.weight, 0)
                        self.assertLessEqual(abs(term.weight), 2)
                        if term.kind == "feature":
                            self.assertIn(term.arg, cfg.FEATURES)
                        if term.kind == "when":
                            for condition in term.arg:
                                self.assertIn(condition, cfg.CONDITIONS)

    def test_can_enact_is_mirrored(self):
        gated = {law for rows in cfg.LAW_TABLE.values() for law in rows if self.data.law_has_can_enact(law)}
        self.assertEqual(gated, set(cfg.CAN_ENACT_MIRROR))

    def test_collectivization_groups_match_the_laws(self):
        sets = gen.law_sets(self.data)
        groups = set().union(*sets["collectivizes"].values())
        self.assertEqual(groups, {"bg_manufacturing", "bg_extraction", "bg_power", "bg_private_infrastructure", "bg_arts"})

    def test_every_covered_law_has_a_stance_value(self):
        values = read(gen.VALUES_OUT)
        for rows in cfg.LAW_TABLE.values():
            for law, row in rows.items():
                with self.subTest(law=law):
                    body = block(values, f"te_pa_gen_stance_{law}")
                    if row.terms:
                        self.assertIn("min = -2", body)
                        self.assertIn("max = 2", body)
                    else:
                        self.assertEqual(body.strip(), "value = 0")

    def test_chains_name_every_signed_law(self):
        values = read(gen.VALUES_OUT)
        triggers = read(gen.TRIGGERS_OUT)
        enacting = block(values, "te_pa_gen_stance_enacting")
        worst = block(values, "te_pa_gen_stance_in_force_worst")
        best = block(values, "te_pa_gen_stance_best_available")
        for rows in cfg.LAW_TABLE.values():
            for law, row in rows.items():
                block(triggers, f"te_pa_gen_law_open_{law}")
                if not row.terms:
                    continue
                with self.subTest(law=law):
                    self.assertIn(f"is_enacting_law = law_type:{law} }} }} value = te_pa_gen_stance_{law}", enacting)
                    self.assertIn(f"max = te_pa_gen_stance_{law}", worst)
                    self.assertIn(f"te_pa_gen_law_open_{law} = yes }} }} min = te_pa_gen_stance_{law}", best)

    def test_stance_terms_render(self):
        values = read(gen.VALUES_OUT)
        self.assertIn("if = { limit = { var:te_pa_g_f_fossil ?= 1 } add = -2 }",
                      block(values, "te_pa_gen_stance_law_managed_fossil_phaseout"))
        self.assertIn("add = { value = te_pa_gen_labor_band multiply = -1 }",
                      block(values, "te_pa_gen_stance_law_worker_protections"))
        self.assertIn("add = { value = te_pa_gen_campaign_share multiply = 2 }",
                      block(values, "te_pa_gen_stance_law_unregulated_donations"))
        self.assertIn("add = -2", block(values, "te_pa_gen_stance_law_command_economy"))
        self.assertIn(cfg.CONDITIONS["big"], block(values, "te_pa_gen_stance_law_trust_busting"))


class OutputsTest(unittest.TestCase):
    def test_committed_outputs_are_current(self):
        result = gen.regenerate(state(), dry_run=True)
        self.assertFalse(result["changed"], f"stale: {result['changed_files']}; run gen_private_actors.py")

    def test_check_flag(self):
        self.assertEqual(gen.main(["--check"]), 0)

    def test_one_bom_and_header(self):
        for rel in OUTPUTS:
            with self.subTest(file=str(rel)):
                raw = (ROOT / rel).read_bytes()
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"))
                self.assertIn("AUTO-GENERATED by scripts/generators/gen_private_actors.py", read(rel))

    def test_tabs_not_spaces(self):
        for rel in OUTPUTS:
            for n, line in enumerate(read(rel).splitlines(), 1):
                self.assertFalse(line.startswith(" "), f"{rel}:{n}")

    def test_registered_before_organize_loc(self):
        text = (ROOT / "server" / "post_load.py").read_text(encoding="utf-8")
        mine = text.index('"scripts.generators.gen_private_actors"')
        self.assertLess(mine, text.index('("organize_loc",'))

    def test_name_locs_and_fallbacks(self):
        custom = read(gen.CUSTOM_LOC_OUT)
        loc = "".join(p.read_text(encoding="utf-8-sig") for p in (ROOT / "localization" / "english").glob("*.yml"))
        for key in (gen.GOOD_UNKNOWN_KEY, gen.LAW_UNKNOWN_KEY):
            self.assertRegex(loc, rf"(?m)^ {key}:0 ")
        for entry in cfg.NAME_LOCS:
            with self.subTest(key=entry.key):
                self.assertTrue(entry.key.startswith("te_pa_"))
                body = block(custom, entry.key)
                self.assertIn("type = container", body)
                self.assertIn(f"var:{entry.variable} ?= 1 }}", body)
        good = block(custom, "te_pa_row_reason_good")
        plan = gen.build_plan(state())
        self.assertIn(f"var:te_pa_r_reason_good ?= {plan.good_index('coal')} }}\n\t\tlocalization_key = coal\n", good)


SYNTHETIC = {
    "common/company_types/zz_te_pa_test.txt": """
company_te_pa_test = {
	icon = "gfx/interface/icons/company_icons/company_basic_textiles.dds"
	background = "gfx/interface/icons/company_icons/company_backgrounds/comp_illu_textile.dds"
	flavored_company = yes
	building_types = { building_te_pa_test_mill building_te_pa_test_farm }
	extension_building_types = { building_coal_mine }
	possible = { always = yes }
}
""",
    "common/buildings/zz_te_pa_test.txt": """
building_te_pa_test_mill = {
	building_group = bg_light_industry
	production_method_groups = { pmg_te_pa_test_mill pmg_te_pa_test_staff }
}
building_te_pa_test_farm = {
	building_group = bg_staple_crops
	production_method_groups = { pmg_te_pa_test_farm }
}
""",
    "common/production_method_groups/zz_te_pa_test.txt": """
pmg_te_pa_test_mill = { production_methods = { pm_te_pa_test_mill_base pm_te_pa_test_mill_robots } }
pmg_te_pa_test_staff = { production_methods = { pm_te_pa_test_staff_a pm_te_pa_test_staff_b } }
pmg_te_pa_test_farm = { production_methods = { pm_te_pa_test_farm_base } }
""",
    "common/production_methods/zz_te_pa_test.txt": """
pm_te_pa_test_mill_base = {
	building_modifiers = {
		workforce_scaled = {
			goods_input_grain_add = 50
			goods_input_dye_add = 10
			goods_input_fabric_add = 10
			goods_input_tools_add = 1
			goods_input_electricity_add = 100
			goods_output_clothes_add = 30
		}
		level_scaled = {
			building_employment_laborers_add = 4000
			building_employment_machinists_add = 1000
			goods_input_construction_add = 1
		}
	}
}
pm_te_pa_test_mill_robots = {
	unlocking_technologies = { mechanical_tools }
	building_modifiers = {
		workforce_scaled = { goods_input_fabric_add = 10 goods_output_clothes_add = 60 }
		level_scaled = { building_employment_laborers_add = 1000 }
		unscaled = { building_robotic_or_ai_managed_bool = yes }
	}
}
pm_te_pa_test_staff_a = {
	building_modifiers = { level_scaled = { building_employment_clerks_add = 9000 } }
}
pm_te_pa_test_staff_b = {
	is_default = yes
	building_modifiers = { level_scaled = { building_employment_clerks_add = 500 } }
}
pm_te_pa_test_farm_base = {
	building_modifiers = {
		workforce_scaled = { goods_output_grain_add = 20 }
		level_scaled = { building_employment_farmers_add = 2000 }
	}
}
""",
}


class SyntheticTypeTest(unittest.TestCase):
    """A company type of two building types in a temp tree, regenerated end to end."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        (root / "vanilla_parsed").symlink_to(ROOT / "vanilla_parsed", target_is_directory=True)
        for rel, text in SYNTHETIC.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        cls.result = gen.regenerate(root=root)
        cls.effects = (root / gen.EFFECTS_OUT).read_text(encoding="utf-8-sig")
        cls.plan = gen.build_plan(gen.load_state(root))
        cls.sector = next(s for s in cls.plan.sectors if s.company == "company_te_pa_test")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_writes_every_output(self):
        self.assertEqual(sorted(self.result["changed_files"]), sorted(str(p) for p in OUTPUTS))

    def test_inputs_ranked_by_value(self):
        # dye 10 x 40 = 400 beats fabric 10 x 20 = 200 and tools 1 x 40; grain is the farm's own output,
        # electricity is local and construction is the upkeep (INPUTS_LEFT_OUT), so none of them counts.
        self.assertEqual(self.sector.inputs, ("dye", "fabric"))
        self.assertEqual(self.sector.output, "clothes")  # 1.0 of the mill and 1.0 of the farm: clothes' 900 beats 400

    def test_jobs_take_the_default_method_and_average(self):
        # mill: 4,000 + 1,000 by its base method and 500 by the default (not the first) staff method; farm 2,000
        self.assertEqual(self.sector.jobs, round((5500 + 2000) / 2))

    def test_features(self):
        self.assertEqual(set(self.sector.features),
                         {"automatable", "manufacturing", "agriculture", "consumer_good", "collectivizable"})

    def test_extension_types_are_left_out(self):
        self.assertNotIn("building_coal_mine", self.sector.buildings)
        self.assertNotIn("fossil", self.sector.features)

    def test_branch(self):
        text = branch(self.effects, "company_te_pa_test")
        self.assertIn('add = "country_has_building_type_levels(bt:building_te_pa_test_mill)"', text)
        self.assertIn('add = "country_has_building_type_levels(bt:building_te_pa_test_farm)"', text)
        self.assertIn("set_variable = { name = te_pa_g_jobs value = 3750 }", text)
        dye, fabric, clothes = (self.plan.good_index(g) for g in ("dye", "fabric", "clothes"))
        self.assertIn(f"te_pa_gen_read_good = {{ SLOT = in1 GOOD = dye IDX = {dye} }}", text)
        self.assertIn(f"te_pa_gen_read_good = {{ SLOT = in2 GOOD = fabric IDX = {fabric} }}", text)
        self.assertIn(f"te_pa_gen_read_good = {{ SLOT = out GOOD = clothes IDX = {clothes} }}", text)
        for feature in self.sector.features:
            self.assertIn(f"set_variable = {{ name = te_pa_g_f_{feature} value = 1 }}", text)
        self.assertNotIn("te_pa_g_f_fossil value = 1", text)
        self.assertIn(f"te_pa_gen_tech_check = {{ TECH = mechanical_tools N = {self.plan.tech_index('mechanical_tools')} }}",
                      text)
        self.assertIn(f"set_variable = {{ name = te_pa_g_tech_count value = {len(self.sector.techs)} }}", text)

    def test_the_cache_names_its_technologies(self):
        cache = block(self.effects, "te_pa_gen_tech_cache")
        self.assertIn(f"TECH = mechanical_tools N = {self.plan.tech_index('mechanical_tools')} }}", cache)


class AuditsTest(unittest.TestCase):
    """The script audits that apply, over a tree holding the generated files and the two hand-written trigger
    files they call (the audits' catalogs and vanilla's names come from the repo's docs/ and vanilla_parsed/)."""

    CALLED = ("common/scripted_triggers/te_creditors_consortium_triggers.txt",
              "common/scripted_triggers/resource_transition_triggers.txt")

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        for name in ("docs", "vanilla_parsed"):
            (cls.root / name).symlink_to(ROOT / name, target_is_directory=True)
        for rel in (*map(str, OUTPUTS), *cls.CALLED):
            (cls.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, cls.root / rel)
        (cls.root / "events").mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def ours(self, flags):
        return [f for f in flags if "te_pa_gen" in str(getattr(f, "file", "")) and not getattr(f, "exemption", None)]

    def test_effect_trigger_validity(self):
        import effect_trigger_validity_audit as audit
        result = audit.audit(str(self.root))
        self.assertEqual(self.ours(result.flags), [])

    def test_script_value_references(self):
        import script_value_reference_audit as audit
        result = audit.audit(self.root)
        self.assertGreaterEqual(result.files_scanned, 4)
        self.assertEqual(self.ours(result.flags), [])

    def test_script_arguments(self):
        import script_argument_audit as audit
        result = audit.audit(mod_path=str(self.root), vanilla_game=None)
        for helper in ("te_pa_gen_read_good", "te_pa_gen_tech_check", "te_pa_gen_law_pick_open"):
            self.assertIn(helper, result.call_sites)
        self.assertEqual(self.ours(result.flags), [])

    def test_variable_guards(self):
        import variable_guard_audit as audit
        self.assertEqual(self.ours(audit.audit(mod_path=str(self.root)).flags), [])

    def test_change_variable_init(self):
        import change_variable_init_audit as audit
        self.assertEqual(self.ours(audit.audit(mod_path=str(self.root)).flags), [])


if __name__ == "__main__":
    unittest.main()
