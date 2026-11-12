"""Tests for modifier_field_audit: every modifier type name the mod writes or
reads is registered (#391), and a written one has a loc key to show (#1072).

Run: .venv/bin/python -m pytest test_modifier_field_audit.py -q
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import mod_state_server as mss
import modifier_field_audit as mfa

ROOT = os.path.dirname(os.path.abspath(__file__))

THROUGHPUT = {"pattern": "building_{building}_throughput_add", "placeholder": "building", "vocab": "building"}


def sources(registered=(), vanilla=(), loc=(), cultures=(), religions=()):
    """`vanilla` names are registered too; `registered` adds the mod's own."""
    return mfa.Sources(
        registered=set(registered) | set(vanilla),
        vanilla_types=set(vanilla),
        cultures=set(cultures),
        vanilla_religions=set(religions),
        has_loc=set(loc).__contains__,
    )


def scan(text, mode="wrapped", rel="common/x/file.txt"):
    return mfa.scan_text(text, rel, mode, mss)


def fields(text, mode="wrapped"):
    return [(s.field, s.line, s.block, s.entity) for s in scan(text, mode)[0]]


def run(text, src, mode="wrapped", patterns=(), engine_listed=frozenset(), reads=""):
    """Judge `text` as one entity file, plus the `modifier:` reads in `reads`."""
    sites, tag_lines = scan(text, mode)
    sites += mfa.scan_reads(reads, "events/reads.txt")
    return mfa.check(sites, [("common/x/file.txt", n) for n in tag_lines], src, patterns, engine_listed)


def kinds(result):
    return sorted((f.kind, f.name) for f in result.flags)


class ScanTests(unittest.TestCase):
    """Which lines are modifier fields."""

    def test_static_modifier_fields_are_direct(self):
        text = (
            "my_modifier = {\n"
            "\ticon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds\n"
            "\tcountry_prestige_mult = 0.1\n"
            "\tcountry_some_bool = yes\n"
            "}\n"
        )
        self.assertEqual(fields(text, "direct"), [
            ("country_prestige_mult", 3, "direct", "my_modifier"),
            ("country_some_bool", 4, "direct", "my_modifier"),
        ])

    def test_quoted_icon_and_comments_are_not_fields(self):
        text = (
            "my_modifier = {\n"
            '\ticon = "gfx/interface/icons/a b.dds"\n'
            "\t# country_commented_add = 1\n"
            "\tcountry_real_add = 1 # country_trailing_add = 2\n"
            "}\n"
        )
        self.assertEqual([f[0] for f in fields(text, "direct")], ["country_real_add"])

    def test_wrapped_blocks(self):
        text = (
            "law_x = {\n"
            "\tgroup = lawgroup_x\n"
            "\tmodifier = {\n"
            "\t\tcountry_authority_add = 100\n"
            "\t}\n"
            "\tinstitution_modifier = {\n"
            "\t\tstate_education_access_add = 0.1\n"
            "\t}\n"
            "\ton_enact = {\n"
            "\t\tadd_modifier = { name = some_modifier days = 30 }\n"
            "\t}\n"
            "\tai_will_do = { modifier = { add = 5 } }\n"
            "\tai_modifier = { country_weight_add = 1 }\n"
            "}\n"
        )
        self.assertEqual(fields(text), [
            ("country_authority_add", 4, "modifier", "law_x"),
            ("state_education_access_add", 7, "institution_modifier", "law_x"),
        ])

    def test_production_method_scaling_wrappers(self):
        text = (
            "pm_x = {\n"
            "\tbuilding_modifiers = {\n"
            "\t\tworkforce_scaled = {\n"
            "\t\t\tgoods_input_coal_add = 5\n"
            "\t\t}\n"
            "\t\tlevel_scaled = { building_employment_laborers_add = 1000 }\n"
            "\t}\n"
            "\tstate_modifiers = { unscaled = { state_pollution_generation_add = 5 } }\n"
            "}\n"
        )
        self.assertEqual(fields(text), [
            ("goods_input_coal_add", 4, "building_modifiers/workforce_scaled", "pm_x"),
            ("building_employment_laborers_add", 6, "building_modifiers/level_scaled", "pm_x"),
            ("state_pollution_generation_add", 8, "state_modifiers/unscaled", "pm_x"),
        ])

    def test_a_block_on_one_line(self):
        """The generated tax amendments write every block this way; the
        server's line scan does not see them."""
        text = (
            "amendment_x = {\n"
            "\ttax_modifier_high = { tax_income_add = 0.05 tax_land_add = 0.1 }\n"
            "\tmodifier = { country_x_add = @some_constant }\n"
            "}\n"
        )
        self.assertEqual([f[:3] for f in fields(text)], [
            ("tax_income_add", 2, "tax_modifier_high"),
            ("tax_land_add", 2, "tax_modifier_high"),
            ("country_x_add", 3, "modifier"),
        ])

    def test_directive_prefixes_are_not_part_of_the_name(self):
        text = (
            "INJECT:law_x = {\n"
            "\tREPLACE:modifier = {\n"
            "\t\tcountry_a_add = 1\n"
            "\t}\n"
            "}\n"
            "REPLACE_OR_CREATE:law_y = {\n"
            "\tmodifier = { country_b_add = 1 }\n"
            "}\n"
        )
        self.assertEqual([(f[0], f[3]) for f in fields(text)],
                         [("country_a_add", "law_x"), ("country_b_add", "law_y")])

    def test_a_block_deeper_than_the_first_is_not_a_modifier_block(self):
        text = (
            "je_x = {\n"
            "\tscaling_modifiers_while_active = {\n"
            "\t\tmodifier = some_static_modifier\n"
            "\t\tvalue = { value = 0 add = 1 }\n"
            "\t}\n"
            "\tmodifiers_while_active = { some_static_modifier }\n"
            "\toutcome = { effect = { modifier = { country_nested_add = 1 } } }\n"
            "}\n"
            "diplomatic_action_x = {\n"
            "\tpact = { first_modifier = { country_pact_add = 1 } }\n"
            "}\n"
        )
        self.assertEqual([f[:3] for f in fields(text)],
                         [("country_pact_add", 10, "pact/first_modifier")])

    def test_top_level_scalars_and_anonymous_blocks(self):
        text = (
            "@constant = 5\n"
            "namespace = x\n"
            "entity = {\n"
            "\tmodifier = {\n"
            "\t\tcountry_a_add = 1\n"
            "\t}\n"
            "\tcolor = hsv{ 0.1 0.2 0.3 }\n"
            "\tmodifier = { country_b_add = 1 }\n"
            "}\n"
        )
        self.assertEqual([f[0] for f in fields(text)], ["country_a_add", "country_b_add"])


class CostAndReadScanTests(unittest.TestCase):
    """The two other places a modifier type is named."""

    def test_ship_cost_blocks(self):
        text = (
            "ship_type_x = {\n"
            "\tconstruction_goods = {\n"
            "\t\tgoods_input_steel_add = 1700\n"
            "\t}\n"
            "\tmateriel_goods = { goods_input_oil_add = 5 }\n"
            "\tmodifier = {\n"
            "\t\tship_hull_add = 10\n"
            "\t}\n"
            "\tmodifications = { construction_goods = { goods_input_nested_add = 1 } }\n"
            "}\n"
        )
        got = scan(text)[0]
        self.assertEqual([(s.field, s.line, s.block, s.shown) for s in got], [
            ("goods_input_steel_add", 3, "construction_goods", False),
            ("goods_input_oil_add", 5, "materiel_goods", False),
            ("ship_hull_add", 7, "modifier", True),
        ])

    def test_reads(self):
        text = (
            "my_trigger = {\n"
            "\tmodifier:country_a_bool = yes\n"
            '\t"modifier:country_b_add" >= 2\n'
            "\tscope:target.modifier:state_c_mult > 0 # modifier:country_commented_add\n"
            "\t# modifier:country_commented_too_add\n"
            "\tadd = modifier:goods_$AXIS$_$GOOD$_mult\n"
            "\thas_modifier = some_static_modifier\n"
            "\tadd_modifier = { name = some_modifier:with_colon }\n"
            "}\n"
        )
        got = mfa.scan_reads(text, "common/scripted_triggers/t.txt")
        self.assertEqual([(s.field, s.line, s.block, s.shown) for s in got], [
            ("country_a_bool", 2, mfa.READ, False),
            ("country_b_add", 3, mfa.READ, False),
            ("state_c_mult", 4, mfa.READ, False),
        ])

    def test_unregistered_read_is_flagged(self):
        """The space programs' booleans: `modifier:country_x_bool = yes` on an
        undeclared type is always false, with no log line."""
        reads = "t = {\n\tmodifier:country_sr_program_bool = yes\n\tmodifier:country_known_bool = yes\n}\n"
        result = run("", sources(registered=["country_known_bool"]), reads=reads)
        self.assertEqual(kinds(result), [("unregistered", "country_sr_program_bool")])
        flag = result.flags[0]
        self.assertEqual((flag.file, flag.line), ("events/reads.txt", 2))
        self.assertIn("so a `modifier:` read of it reads nothing", flag.detail)
        self.assertNotIn("drops the line", flag.detail)
        self.assertEqual((result.fields, result.uses, result.reads), (2, 0, 2))

    def test_a_name_written_and_read_is_one_flag(self):
        text = "pm_x = {\n\tcountry_modifiers = {\n\t\tunscaled = {\n\t\t\tcountry_sr_program_bool = yes\n\t\t}\n\t}\n}\n"
        result = run(text, sources(), reads="t = {\n\tmodifier:country_sr_program_bool = yes\n}\n")
        self.assertEqual(kinds(result), [("unregistered", "country_sr_program_bool")])
        self.assertEqual([(s.file, s.block) for s in result.flags[0].sites],
                         [("common/x/file.txt", "country_modifiers/unscaled"), ("events/reads.txt", mfa.READ)])
        self.assertIn("the engine drops the line and a `modifier:` read of it reads nothing", result.flags[0].detail)

    def test_unregistered_cost_is_flagged(self):
        text = "ship_type_x = {\n\tconstruction_goods = {\n\t\tgoods_input_mod_good_add = 5\n\t}\n}\n"
        result = run(text, sources())
        self.assertEqual(kinds(result), [("unregistered", "goods_input_mod_good_add")])

    def test_costs_and_reads_need_no_loc(self):
        """Neither prints a modifier line."""
        text = (
            "ship_type_x = {\n"
            "\tconstruction_goods = {\n"
            "\t\tcountry_je_korea_action_cost = 5 # REVIEWED 2026-11-12 (modifier_field_loc): a cost\n"
            "\t}\n"
            "}\n"
        )
        result = run(text, sources(vanilla=["country_je_korea_action_cost"]),
                     reads="t = {\n\tmodifier:country_je_korea_action_cost > 0\n}\n")
        self.assertEqual(kinds(result), [("stale_review", "")])
        self.assertIn("the line writes no field of a modifier block", result.flags[0].detail)


class RegisteredTests(unittest.TestCase):
    """Check 1: the field names a registered modifier type."""

    TEXT = (
        "pm_x = {\n"
        "\tbuilding_modifiers = {\n"
        "\t\tworkforce_scaled = {\n"
        "\t\t\tbuilding_synthetics_plant_biomass_throughput_add = 0.05\n"
        "\t\t\tbuilding_synthetics_plant_coal_throughput_add = 0.05\n"
        "\t\t\tcountry_prestige_from_navy_power_projection_mult = 0.1\n"
        "\t\t\tcountry_prestige_mult = 0.1\n"
        "\t\t}\n"
        "\t}\n"
        "}\n"
    )

    def src(self):
        return sources(
            registered=["building_synthetics_plant_biomass_throughput_add"],
            vanilla=["country_prestige_mult", "country_prestige_from_navy_combat_power_mult"],
            loc=["country_prestige_mult", "country_prestige_from_navy_combat_power_mult"],
        )

    def test_unknown_name_is_flagged(self):
        """The 1.14.4 rename: the old name is registered by nobody."""
        result = run(self.TEXT, self.src())
        flag = next(f for f in result.flags if f.name == "country_prestige_from_navy_power_projection_mult")
        self.assertEqual(flag.kind, "unregistered")
        self.assertEqual((flag.file, flag.line), ("common/x/file.txt", 6))
        self.assertIn("no modifier type definition registers it", flag.detail)
        self.assertIn("`country_prestige_from_navy_combat_power_mult`", flag.detail)

    def test_pattern_match_with_no_registered_instance_is_flagged(self):
        """#681: the building exists and the name fits the family; no
        definition registers it, so the engine ignores the line."""
        result = run(self.TEXT, self.src(), patterns=[THROUGHPUT])
        flag = next(f for f in result.flags if f.name == "building_synthetics_plant_coal_throughput_add")
        self.assertEqual(flag.kind, "unregistered")
        self.assertIn("`building_{building}_throughput_add`", flag.detail)
        self.assertIn("common/modifier_type_definitions/", flag.detail)

    def test_registered_pattern_instance_is_clean(self):
        result = run(self.TEXT, self.src(), patterns=[THROUGHPUT])
        self.assertEqual(kinds(result), [
            ("unregistered", "building_synthetics_plant_coal_throughput_add"),
            ("unregistered", "country_prestige_from_navy_power_projection_mult"),
        ])

    def test_a_name_the_engine_lists_is_still_unregistered(self):
        """`modifiers.log` lists a throughput type for every building; only a
        definition makes one usable. The list only changes the advice."""
        text = "x = {\n\tcountry_listed_only_add = 1\n}\n"
        result = run(text, sources(), mode="direct", engine_listed={"country_listed_only_add"})
        self.assertEqual(kinds(result), [("unregistered", "country_listed_only_add")])
        self.assertIn("`modifiers.log` lists it", result.flags[0].detail)

    def test_one_flag_per_field_with_every_site(self):
        text = (
            "a = {\n\tcountry_typo_add = 1\n}\n"
            "b = {\n\tcountry_typo_add = 2\n}\n"
        )
        result = run(text, sources(), mode="direct")
        self.assertEqual(len(result.flags), 1)
        self.assertEqual([s.line for s in result.flags[0].sites], [2, 5])
        self.assertEqual((result.fields, result.uses, result.reads), (1, 2, 0))

    def test_unregistered_cannot_be_suppressed(self):
        text = "a = {\n\tcountry_typo_add = 1 # REVIEWED 2026-11-12 (modifier_field_loc): wanted\n}\n"
        result = run(text, sources(), mode="direct")
        self.assertEqual(kinds(result), [("stale_review", "country_typo_add"), ("unregistered", "country_typo_add")])
        self.assertTrue(all(f.exemption is None for f in result.flags))
        stale = next(f for f in result.flags if f.kind == "stale_review")
        self.assertIn("an unregistered field takes no comment", stale.detail)


class LocTests(unittest.TestCase):
    """Check 2: a type vanilla registers has a loc key of its own name."""

    def test_vanilla_type_with_no_loc_is_flagged(self):
        text = "a = {\n\tcountry_je_korea_action_cost = 1\n\tcountry_prestige_mult = 0.1\n}\n"
        src = sources(vanilla=["country_je_korea_action_cost", "country_prestige_mult"],
                      loc=["country_prestige_mult", "country_je_korea_action_cost_desc"])
        result = run(text, src, mode="direct")
        self.assertEqual(kinds(result), [("no_loc", "country_je_korea_action_cost")])
        self.assertIn("shows the raw key", result.flags[0].detail)
        self.assertIsNone(result.flags[0].exemption)

    def test_missing_desc_is_not_flagged(self):
        text = "a = {\n\tcountry_prestige_mult = 0.1\n}\n"
        result = run(text, sources(vanilla=["country_prestige_mult"], loc=["country_prestige_mult"]), mode="direct")
        self.assertEqual(result.flags, [])

    def test_a_type_only_the_mod_registers_is_left_to_loc_coverage(self):
        text = "a = {\n\tcountry_mod_only_add = 1\n}\n"
        result = run(text, sources(registered=["country_mod_only_add"]), mode="direct")
        self.assertEqual(result.flags, [])

    def test_a_vanilla_type_the_mod_redefines_is_still_judged(self):
        text = "a = {\n\tcountry_shared_add = 1\n}\n"
        result = run(text, sources(registered=["country_shared_add"], vanilla=["country_shared_add"]), mode="direct")
        self.assertEqual(kinds(result), [("no_loc", "country_shared_add")])

    def test_culture_family_is_exempt(self):
        """The generated merged-culture modifiers (mod cultures, mod types) and
        a vanilla culture's three types, which vanilla gives no key."""
        text = (
            "cm_german_standard_of_living_modifier_positive = {\n"
            "\tstate_cm_german_standard_of_living_add = 1\n"
            "\tcountry_cm_german_cultural_acceptance_add = 1\n"
            "\tcountry_fervor_target_cm_german_add = 1\n"
            "\tstate_british_standard_of_living_add = 1\n"
            "\tcountry_british_cultural_acceptance_add = 1\n"
            "\tcountry_fervor_target_british_add = 1\n"
            "}\n"
        )
        src = sources(
            registered=["state_cm_german_standard_of_living_add", "country_cm_german_cultural_acceptance_add",
                        "country_fervor_target_cm_german_add"],
            vanilla=["state_british_standard_of_living_add", "country_british_cultural_acceptance_add",
                     "country_fervor_target_british_add"],
            cultures=["british", "cm_german"],
        )
        self.assertEqual(run(text, src, mode="direct").flags, [])

    def test_culture_shape_without_the_culture_is_not_exempt(self):
        text = "a = {\n\tstate_lower_strata_standard_of_living_add = 1\n}\n"
        src = sources(vanilla=["state_lower_strata_standard_of_living_add"], cultures=["british"])
        self.assertEqual(kinds(run(text, src, mode="direct")),
                         [("no_loc", "state_lower_strata_standard_of_living_add")])

    def test_vanilla_religion_family_is_exempt(self):
        text = "a = {\n\tstate_catholic_standard_of_living_add = 1\n}\n"
        src = sources(vanilla=["state_catholic_standard_of_living_add"], religions=["catholic"])
        self.assertEqual(run(text, src, mode="direct").flags, [])

    def test_reviewed_comment_suppresses_every_use(self):
        text = (
            "a = {\n"
            "\tcountry_je_korea_action_cost = 1 # REVIEWED 2026-11-12 (modifier_field_loc): shown nowhere\n"
            "}\n"
            "b = {\n"
            "\tcountry_je_korea_action_cost = 2\n"
            "}\n"
        )
        result = run(text, sources(vanilla=["country_je_korea_action_cost"]), mode="direct")
        self.assertEqual(kinds(result), [("no_loc", "country_je_korea_action_cost")])
        self.assertEqual(result.flags[0].exemption, {"date": "2026-11-12", "rationale": "shown nowhere"})
        self.assertEqual(len(result.flags[0].sites), 2)

    def test_untagged_or_other_tag_does_not_suppress(self):
        for comment in ("# REVIEWED 2026-11-12: plain form", "# REVIEWED 2026-11-12 (hidden_modifier): other audit"):
            with self.subTest(comment=comment):
                text = f"a = {{\n\tcountry_je_korea_action_cost = 1 {comment}\n}}\n"
                result = run(text, sources(vanilla=["country_je_korea_action_cost"]), mode="direct")
                self.assertEqual(kinds(result), [("no_loc", "country_je_korea_action_cost")])
                self.assertIsNone(result.flags[0].exemption)

    def test_stale_tags(self):
        text = (
            "a = { # REVIEWED 2026-11-12 (modifier_field_loc): on the opener\n"
            "\tcountry_prestige_mult = 0.1 # REVIEWED 2026-11-12 (modifier_field_loc): has a name\n"
            "}\n"
        )
        result = run(text, sources(vanilla=["country_prestige_mult"], loc=["country_prestige_mult"]), mode="direct")
        self.assertEqual(kinds(result), [("stale_review", ""), ("stale_review", "country_prestige_mult")])
        details = sorted(f.detail for f in result.flags)
        self.assertIn("the field is not flagged", details[0])
        self.assertIn("the line writes no field of a modifier block", details[1])


class ReportAndCliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.mod = self._tmp.name
        self.src = sources(
            registered=["country_mod_add"],
            vanilla=["country_prestige_mult", "country_je_korea_action_cost"],
            loc=["country_prestige_mult"],
        )

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, text):
        path = os.path.join(self.mod, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(text)

    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(mfa, "offline_sources", return_value=self.src), \
                mock.patch.object(mfa, "load_patterns", return_value=[THROUGHPUT]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mfa.main(list(argv), mod_path=self.mod)
        return code, out.getvalue(), err.getvalue()

    def test_clean_tree(self):
        self.write("common/static_modifiers/a.txt", "a = {\n\tcountry_prestige_mult = 0.1\n}\n")
        self.write("common/laws/l.txt", "law_x = {\n\tmodifier = {\n\t\tcountry_mod_add = 1\n\t}\n}\n")
        # Script directories and `_`-prefixed files are not entity files.
        self.write("common/scripted_effects/e.txt",
                   "e = {\n\tmodifier = {\n\t\tcountry_typo_add = 1\n\t}\n"
                   "\tif = { limit = { modifier:country_mod_add > 0 } }\n}\n")
        self.write("common/laws/_notes.txt",
                   "law_y = {\n\tmodifier = {\n\t\tcountry_typo_add = 1\n\t}\n\tmodifier:country_typo_add = 1\n}\n")
        self.write("events/e.txt", "e.1 = {\n\ttrigger = { modifier:country_prestige_mult > 0 }\n}\n")
        code, out, err = self.main("--strict")
        self.assertEqual(code, 0, out)
        self.assertIn("## Unreviewed Flags\n\n_None._", out)
        self.assertIn("2 distinct names: 2 lines written in 2 entity files, 2 reads.", err)

    def test_reads_are_found_in_script_and_events(self):
        self.write("common/scripted_triggers/t.txt", "t = {\n\tmodifier:country_gone_bool = yes\n}\n")
        self.write("events/e.txt", "e.1 = {\n\ttrigger = { \"modifier:country_gone_bool\" = yes }\n}\n")
        code, out, _err = self.main("--strict")
        self.assertEqual(code, 1)
        self.assertIn("- `country_gone_bool` — no modifier type definition registers it, so a `modifier:` read "
                      "of it reads nothing (common/scripted_triggers/t.txt:2, events/e.txt:2, 2 uses)", out)

    def test_strict_fails_on_each_kind(self):
        cases = {
            "unregistered": "a = {\n\tcountry_typo_add = 1\n}\n",
            "no_loc": "a = {\n\tcountry_je_korea_action_cost = 1\n}\n",
            "stale_review": "a = {\n\tcountry_prestige_mult = 1 # REVIEWED 2026-11-12 (modifier_field_loc): x\n}\n",
        }
        for kind, text in cases.items():
            with self.subTest(kind=kind):
                self.write("common/static_modifiers/a.txt", text)
                code, out, _err = self.main("--strict")
                self.assertEqual(code, 1)
                self.assertIn(f"### {kind}", out)
                self.assertEqual(self.main()[0], 0, "without --strict the report alone is printed")

    def test_reviewed_no_loc_passes_strict_and_is_listed(self):
        self.write(
            "common/static_modifiers/a.txt",
            "a = {\n\tcountry_je_korea_action_cost = 1 # REVIEWED 2026-11-12 (modifier_field_loc): shown nowhere\n}\n",
        )
        code, out, _err = self.main("--strict")
        self.assertEqual(code, 0, out)
        self.assertIn(
            "- no_loc: `country_je_korea_action_cost` (common/static_modifiers/a.txt) — "
            "**2026-11-12**: shown nowhere", out)

    def test_report_lists_sites(self):
        self.write("common/static_modifiers/a.txt", "".join(
            f"m{i} = {{\n\tbuilding_x_throughput_add = 1\n}}\n" for i in range(7)))
        _code, out, _err = self.main()
        self.assertIn("- `building_x_throughput_add` — no modifier type definition registers it", out)
        self.assertIn("`building_{building}_throughput_add`", out)
        self.assertIn("common/static_modifiers/a.txt:2, ", out)
        self.assertIn(" and 2 more, 7 uses)", out)

    def test_regenerate_counts_feed_the_reload_warning(self):
        self.write("common/static_modifiers/a.txt",
                   "a = {\n\tcountry_typo_add = 1\n\tcountry_prestige_mult = 1\n}\n")
        with mock.patch("path_constants.mod_path", self.mod), \
                mock.patch.object(mfa, "load_patterns", return_value=[]):
            summary = mfa.regenerate(_FakeState(self.src))
        self.assertEqual(summary, {
            "files_audited": 1, "fields_checked": 2, "uses_checked": 2, "reads_checked": 0,
            "total_flags": 1, "unreviewed": 1, "exempted": 0,
        })
        with open(os.path.join(self.mod, mfa.REPORT_PATH), encoding="utf-8") as fh:
            self.assertIn("### unregistered", fh.read())


class _FakeParser:
    def __init__(self, data):
        self.data = data


class _FakeState:
    """The ModState surface `sources_from_state` reads."""

    def __init__(self, src):
        mod_only = src.registered - src.vanilla_types
        self.base_parsers = {
            "Modifier Types": _FakeParser(dict.fromkeys(src.vanilla_types)),
            "Cultures": _FakeParser(dict.fromkeys(src.cultures)),
            "Religions": _FakeParser(dict.fromkeys(src.vanilla_religions)),
        }
        self.mod_parsers = {
            "Modifier Types": _FakeParser(dict.fromkeys(src.vanilla_types | mod_only)),
            "Cultures": _FakeParser({"cm_mod_culture": None}),
        }
        self._has_loc = src.has_loc

    def get_data(self, entity_type):
        parser = self.mod_parsers.get(entity_type)
        return parser.data if parser else None

    def has_localization(self, key):
        return self._has_loc(key)


class SourcesTests(unittest.TestCase):
    def test_sources_from_state(self):
        src = sources(registered=["country_mod_add"], vanilla=["country_prestige_mult"],
                      loc=["country_prestige_mult"], cultures=["british"], religions=["catholic"])
        got = mfa.sources_from_state(_FakeState(src))
        self.assertEqual(got.registered, {"country_mod_add", "country_prestige_mult"})
        self.assertEqual(got.vanilla_types, {"country_prestige_mult"})
        self.assertEqual(got.cultures, {"british", "cm_mod_culture"})
        self.assertEqual(got.vanilla_religions, {"catholic"})
        self.assertTrue(got.has_loc("country_prestige_mult"))
        self.assertFalse(got.has_loc("country_mod_add"))

    def test_pattern_of(self):
        self.assertEqual(mfa.pattern_of("building_x_throughput_add", [THROUGHPUT]), THROUGHPUT["pattern"])
        # nothing between the prefix and the suffix
        self.assertIsNone(mfa.pattern_of("building__throughput_add", [THROUGHPUT]))
        self.assertIsNone(mfa.pattern_of("building_throughput_add", [THROUGHPUT]))
        self.assertIsNone(mfa.pattern_of("country_x_add", [THROUGHPUT]))
        self.assertIsNone(mfa.pattern_of("building_x_throughput_add", []))


class RealModTests(unittest.TestCase):
    """The committed mod and the committed vanilla snapshot."""

    @classmethod
    def setUpClass(cls):
        cls.src = mfa.offline_sources(ROOT)
        cls.sites, cls.tags, cls.files = mfa.scan_mod(ROOT, mss)

    def test_the_mod_is_clean(self):
        result = mfa.check(self.sites, self.tags, self.src, mfa.load_patterns(mss), mfa.load_engine_listed(ROOT))
        self.assertEqual(
            [(f.kind, f.name, f.file, f.line) for f in result.flags if not f.exemption], [],
            "register the type in common/modifier_type_definitions/ (or fix the name); "
            "for a missing loc key add one",
        )
        self.assertGreater(result.fields, 1000)
        self.assertGreater(result.uses, 20000)
        self.assertGreater(result.reads, 1000)

    def test_sources_hold_vanilla_and_mod_types(self):
        self.assertIn("country_prestige_mult", self.src.vanilla_types)
        mod_only = self.src.registered - self.src.vanilla_types
        self.assertGreater(len(mod_only), 500)
        self.assertGreater(len(self.src.vanilla_types), 2000)
        self.assertTrue(self.src.has_loc("country_prestige_mult"))
        self.assertIn("catholic", self.src.vanilla_religions)

    def test_same_sites_as_the_server_scan_plus_one_line_blocks(self):
        """One definition of "a modifier block": every site `GET
        /modifier-grants` finds is a modifier block's site here, and what this
        scan adds is only what the server's line scan cannot see, a block
        opened and closed on one line."""
        mine = {(s.file, s.line, s.field) for s in self.sites if s.shown}
        theirs = set()
        lines_of = {}
        common = os.path.join(ROOT, "common")
        for entity_type, subdir, mode in mss._grant_scan_plan([common]):
            for root, dirs, names in os.walk(os.path.join(common, *subdir.split("/"))):
                dirs.sort()
                for name in sorted(names):
                    if not name.endswith(".txt") or name.startswith("_"):
                        continue
                    abs_p = os.path.join(root, name)
                    rel = os.path.relpath(abs_p, ROOT).replace(os.sep, "/")
                    with open(abs_p, encoding="utf-8-sig", errors="replace") as fh:
                        lines_of[rel] = fh.read().split("\n")
                    for grant in mss._scan_file_for_grants(abs_p, rel, entity_type, mode, "mod", None):
                        code = lines_of[rel][grant["line"] - 1].split("#", 1)[0]
                        theirs.add((rel, grant["line"], mss._GRANT_LINE_RE.match(code).group(1)))
        self.assertGreater(len(theirs), 20000)
        self.assertEqual(theirs - mine, set())
        for file, line, name in sorted(mine - theirs):
            code = lines_of[file][line - 1].split("#", 1)[0]
            self.assertTrue("{" in code and "}" in code, f"{file}:{line} {name}: {code.strip()}")

    def test_the_ship_cost_blocks_are_scanned(self):
        costs = [s for s in self.sites if s.block in mfa.COST_BLOCKS]
        self.assertGreater(len(costs), 400)
        self.assertTrue(all(s.field.startswith("goods_input_") for s in costs), {s.field for s in costs})

    def test_vanilla_writes_no_field_this_audit_would_flag(self):
        """What both checks rest on: every field of every vanilla static
        modifier, and every ship cost, is a registered type, and a static
        modifier's field has a loc key or belongs to a family the engine
        names. A snapshot rebuilt after a patch that breaks either (a new
        engine-named family, say) fails here."""
        def load(name):
            with open(os.path.join(ROOT, "vanilla_parsed", "common", name), encoding="utf-8") as fh:
                return json.load(fh)

        def body_of(value):
            while isinstance(value, list) and len(value) == 2 and value[0] == "=":
                value = value[1]
            return value if isinstance(value, dict) else {}

        sites = []
        for name, raw in load("modifiers.json").items():
            sites += [mfa.Site(key, "vanilla", 0, "direct", name)
                      for key in body_of(raw) if key not in mfa.NOT_A_FIELD]
        self.assertGreater(len(sites), 5000)
        costs = []
        for file in ("ship_types.json", "ship_modifications.json"):
            for name, raw in load(file).items():
                for block in mfa.COST_BLOCKS:
                    costs += [mfa.Site(key, "vanilla", 0, block, name) for key in body_of(body_of(raw).get(block))]
        self.assertGreater(len(costs), 400)
        src = mfa.Sources(self.src.vanilla_types, self.src.vanilla_types, self.src.cultures,
                          self.src.vanilla_religions, self.src.has_loc)
        result = mfa.check(sites + costs, [], src)
        self.assertEqual(kinds(result), [])


if __name__ == "__main__":
    unittest.main()
