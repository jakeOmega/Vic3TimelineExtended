"""The AI telemetry probe (TEMPORARY, 2026-11-15): scripts/generators/gen_ai_probe.py and its four script files.

The probe cannot be run offline, and a `debug_log` line the engine cannot render is dropped without a word, so
these tests hold the parts that can be held: the generated files agree with each other and with the key the parser
reads, every hook sits behind the probe's latch, every counter is declared and reset, and the parser reads back
what the templates would print.

The files are NOT held to the mod's current laws and technologies: the generator is run before a probe run, not on
every change (docs/testing/ai-probe-runbook.md). They are held to the generator, through the catalog the key
records (FreshTest), and the version-1 lines to the first long run's (OldLogTest), so that run's log still parses.
"""

import json
import re
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import ai_probe_report  # noqa: E402
import gen_ai_probe  # noqa: E402

VALUES = ROOT / gen_ai_probe.VALUES_FILE
EFFECTS = ROOT / gen_ai_probe.EFFECTS_FILE
ON_ACTIONS = ROOT / gen_ai_probe.ON_ACTIONS_FILE
EVENTS = ROOT / gen_ai_probe.EVENTS_FILE
KEY = ROOT / gen_ai_probe.KEY_FILE
GAME_STRATEGIES = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/common/ai_strategies")
# 142 lines of the first long run's log (2026-11-16, build dab9335f1, probe version 1): the ARM and canary lines,
# five months' K lines, Great Britain's first two snapshots and Luxembourg's first, and one event of each kind.
V1_SAMPLE = ROOT / "test_fixtures/ai_probe/run1_v1_sample.txt"
# That build's snapshot lines, as its ai_probe_key.json gave them.
V1_LINES = ROOT / "test_fixtures/ai_probe/key_v1_lines.json"
# Version 3's (build 2d26c6b5a, run 4 of 2026-11-16): the lines a version-3 log carries.
V3_LINES = ROOT / "test_fixtures/ai_probe/key_v3_lines.json"
# Version 5's (build 6a27d2422, 2026-11-27): the last with the army census, whose six fields end its P2 line.
V5_LINES = ROOT / "test_fixtures/ai_probe/key_v5_lines.json"

_ACCESSOR = re.compile(r"\[[^\]]*\]")
_SCRIPT_VALUE = re.compile(r"ScriptValue\('([a-z0-9_]+)'\)")
_LOG = re.compile(r'debug_log = "(TE_AIP [^"]*)"')


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def render(template: str, n: int = 7) -> str:
    """What a template line would print: the tag for the tag accessor, a figure for every other one."""
    out = template.replace("[THIS.GetCountry.GetTagName]", "FRA")
    out = out.replace("[SCOPE.sCountry('initiator').GetTagName]", "FRA").replace(
        "[SCOPE.sCountry('target').GetTagName]", "GBR")
    out = out.replace("[THIS.ScriptValue('te_aip_id')|0]", "3").replace("[THIS.ScriptValue('te_aip_k')|0]", "24")
    out = out.replace("[SCOPE.ScriptValue('te_aip_k')|0]", "24")
    return _ACCESSOR.sub(str(n), out)


class GeneratedFilesTest(unittest.TestCase):
    def test_script_files_start_with_one_bom(self):
        for path in (VALUES, EFFECTS, ON_ACTIONS, EVENTS):
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), path.name)
            self.assertFalse(raw[3:].startswith(b"\xef\xbb\xbf"), f"{path.name} has two BOMs")

    def test_every_script_value_a_line_reads_is_defined(self):
        defined = set(re.findall(r"(?m)^(te_aip_[a-z0-9_]+) = \{", text(VALUES)))
        read = set(_SCRIPT_VALUE.findall(text(EFFECTS))) | set(_SCRIPT_VALUE.findall(text(ON_ACTIONS)))
        self.assertTrue(read, "no script value read found: the pattern is stale")
        self.assertEqual(read - defined, set())

    def test_building_type_levels_are_read_through_the_bt_link(self):
        """A bare building name there is no event target: the read logs an error at load and gives 0 (the first
        run, 2026-11-15)."""
        reads = re.findall(r'"country_has_building_type_levels\(([^)]*)\)"', text(VALUES))
        self.assertGreater(len(reads), 10)
        self.assertEqual([read for read in reads if not read.startswith("bt:building_")], [])

    def test_unit_tiers_are_eras(self):
        tiers = json.loads(KEY.read_text(encoding="utf-8"))["unit_tier"]
        self.assertEqual(tiers["combat_unit_type_irregular_infantry"], 1)
        self.assertTrue(all(1 <= tier <= 13 for tier in tiers.values()), tiers)

    def test_the_construction_purchase_prints_with_decimals(self):
        """A small government buys a fraction of a point a week; printed whole, 0.08 reads as no purchase."""
        snapshot = re.search(r"(?ms)^te_aip_snapshot = \{\n(.*?)^\}", text(EFFECTS)).group(1)
        for field in ("cm_public", "cm_target"):
            self.assertIn(f"{field}=[THIS.ScriptValue('te_aip_{field}')|3]", snapshot)

    def test_no_script_value_is_defined_twice(self):
        names = re.findall(r"(?m)^(te_aip_[a-z0-9_]+) = \{", text(VALUES))
        self.assertEqual(sorted(n for n in set(names) if names.count(n) > 1), [])

    def test_every_hook_is_behind_the_latch(self):
        """A played game must pay one global-variable test a hook and nothing else."""
        body = text(ON_ACTIONS)
        entries = re.findall(r"(?ms)^(te_aip_[a-z_]+) = \{\n(.*?)^\}", body)
        self.assertGreater(len(entries), 10)
        for name, entry in entries:
            if name == "te_aip_global_monthly":      # it is the one that arms the probe
                continue
            self.assertIn("has_global_variable = te_aip_on", entry, name)
        hooked = set(re.findall(r"on_actions = \{ (te_aip_[a-z_]+) \}", body))
        self.assertEqual(hooked, {name for name, _ in entries})

    def test_the_probe_arms_itself_only_where_nobody_plays(self):
        tick = re.search(r"(?ms)^te_aip_global_tick = \{\n(.*?)^\}", text(EFFECTS)).group(1)
        self.assertIn("NOT = { any_country = { is_player = yes } }", tick)
        self.assertIn("NOT = { has_global_variable = te_aip_off }", tick)

    def test_every_counter_is_declared_and_reset(self):
        effects, on_actions = text(EFFECTS), text(ON_ACTIONS)
        whats = set(re.findall(r"te_aip_law_event = \{ WHAT = ([a-z_]+) \}", on_actions))
        self.assertEqual(whats, {"start", "pass", "fail"})
        self.assertIn("te_aip_law_end_event = yes", on_actions)
        built = set(re.findall(r"te_aip_built_event = \{ WHAT = ([a-z_]+) \}", on_actions))
        self.assertEqual(built, {"built", "expanded"})
        counted = set(re.findall(r"te_aip_count = \{ N = ([a-z_]+) \}", effects + on_actions))
        counted |= {f"law_{what}" for what in whats} | built
        self.assertEqual(counted, set(gen_ai_probe.COUNTERS))
        snapshot = re.search(r"(?ms)^te_aip_snapshot = \{\n(.*?)^\}", effects).group(1)
        reset = set(re.findall(r"set_variable = \{ name = te_aip_n_([a-z_]+) value = 0 \}", snapshot))
        self.assertEqual(reset, set(gen_ai_probe.COUNTERS))

    def test_a_counter_is_set_before_it_is_changed(self):
        """change_variable on an unset variable fails and counts nothing (#1818)."""
        helper = re.search(r"(?ms)^te_aip_count = \{\n(.*?)^\}", text(EFFECTS)).group(1)
        self.assertLess(helper.index("set_variable = { name = te_aip_n_$N$ value = 0 }"),
                        helper.index("change_variable = { name = te_aip_n_$N$ add = 1 }"))

    def test_the_key_matches_the_snapshot_lines(self):
        key = json.loads(KEY.read_text(encoding="utf-8"))
        self.assertEqual(key["version"], gen_ai_probe.VERSION)
        snapshot = re.search(r"(?ms)^te_aip_snapshot = \{\n(.*?)^\}", text(EFFECTS)).group(1)
        lines = dict(re.findall(r'debug_log = "TE_AIP S ([A-Z][0-9]+) ([^"]*)"', snapshot))
        self.assertEqual(list(lines), list(key["lines"]))
        for name, template in lines.items():
            fields = _SCRIPT_VALUE.findall(template)[2:]            # past the id and the tick in the line's head
            self.assertEqual(fields, ["te_aip_" + field for field in key["lines"][name]], name)

    def test_no_line_is_longer_than_the_longest_the_mod_has_seen_print(self):
        """Nobody knows the engine's limit on a debug_log string; the self-checks' lines run to about 1,100
        characters and print, so the probe stays under 1,500."""
        for line in _LOG.findall(text(EFFECTS)) + _LOG.findall(text(ON_ACTIONS)):
            self.assertLess(len(line), 1500, line[:80])

    def test_strategy_lists_name_the_mods_own_strategies(self):
        listed = {name for names in gen_ai_probe.STRATEGIES.values() for name in names}
        own = set()
        for path in (ROOT / "common/ai_strategies").glob("*.txt"):
            own |= set(re.findall(r"(?m)^(?:INJECT:|REPLACE:)?(ai_strategy_[a-z_]+) = \{", text(path)))
        self.assertEqual(own - listed - {"ai_strategy_default"}, set())

    @unittest.skipUnless(GAME_STRATEGIES.is_dir(), "no game install: vanilla's strategy files are not in the snapshot")
    def test_strategy_lists_name_the_games_strategies(self):
        listed = {name for names in gen_ai_probe.STRATEGIES.values() for name in names}
        game = set()
        for path in GAME_STRATEGIES.glob("*.txt"):
            game |= set(re.findall(r"(?m)^(ai_strategy_[a-z_]+) = \{", text(path)))
        self.assertEqual(game - listed - {"ai_strategy_default"}, set())


class ParserTest(unittest.TestCase):
    def setUp(self):
        self.key = json.loads(KEY.read_text(encoding="utf-8"))
        self.log = self.rendered(7)

    @staticmethod
    def rendered(n: int) -> list[str]:
        """Every line the probe can log, as the game would print it with `n` for each figure."""
        log = []
        for template in _LOG.findall(text(EFFECTS)) + _LOG.findall(text(ON_ACTIONS)):
            if "E law_$WHAT$" in template:
                whats = ("start", "pass", "fail")
            elif "$WHAT$" in template:
                whats = ("default", "default_end")
            else:
                whats = ("",)
            for what in whats:
                log.append("[12:00:00][jomini_effect.cpp:1]: " + render(template.replace("$WHAT$", what), n))
        return log

    def test_the_parser_reads_back_every_field_the_templates_print(self):
        parsed = ai_probe_report.parse_lines(self.log, self.key)
        self.assertEqual(parsed.bad, [])
        self.assertTrue(parsed.armed)
        records = parsed.records()
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual((record["tag"], record["id"], record["k"]), ("FRA", 3, 24))
        for name, fields in self.key["lines"].items():
            for field in fields:
                self.assertEqual(record.get(field), 7, f"{name}: {field}")
        self.assertEqual(set(record["x"]) - {"tag", "id", "k"}, set(self.key["data_functions"]))
        self.assertEqual(set(parsed.canary), {"start", "date", "end", *self.key["data_functions"]})
        events = {event["event"] for event in parsed.events}
        self.assertEqual(events, {"law_start", "law_pass", "law_fail", "law_end", "default", "default_end", "play"})
        play = next(event for event in parsed.events if event["event"] == "play")
        self.assertEqual((play["tag"], play["target"]), ("FRA", "GBR"))
        self.assertEqual({f: play.get(f) for f in ("id", "type", "rank", "target_rank", "target_id")},
                         {"id": 7, "type": 7, "rank": 7, "target_rank": 7, "target_id": 7})
        end = next(event for event in parsed.events if event["event"] == "law_end")
        self.assertEqual((end["how"], end["max"], end["law"]), (7, 7, 7))
        self.assertEqual(parsed.ticks[24]["y"], 7)
        self.assertEqual(parsed.world[24], {"k": 24, "y": 7, **{f: 7 for f in gen_ai_probe.WORLD_FIELDS}})
        self.assertEqual(parsed.version(), gen_ai_probe.VERSION)

    def test_check_passes_a_whole_log_and_fails_one_without_the_arm_line(self):
        parsed = ai_probe_report.parse_lines(self.log, self.key)
        lines, ok = ai_probe_report.check(parsed, self.key)
        self.assertTrue(ok, "\n".join(lines))
        unarmed = ai_probe_report.parse_lines([line for line in self.log if " ARM " not in line], self.key)
        self.assertFalse(ai_probe_report.check(unarmed, self.key)[1])

    def test_check_names_a_snapshot_line_the_engine_dropped(self):
        dropped = [line for line in self.log if "TE_AIP S G2 " not in line]
        lines, ok = ai_probe_report.check(ai_probe_report.parse_lines(dropped, self.key), self.key)
        self.assertFalse(ok)
        self.assertTrue(any("G2" in line for line in lines), "\n".join(lines))

    def test_figures_with_grouping_commas_and_decimals_read_as_numbers(self):
        self.assertEqual(ai_probe_report.number("1,234,567"), 1234567)
        self.assertEqual(ai_probe_report.number("-0.25"), -0.25)
        self.assertEqual(ai_probe_report.number("Railways"), "Railways")
        self.assertEqual(ai_probe_report.pairs("a=1 name=Steam Donkey b=2.5"), {"a": 1, "name": "Steam Donkey", "b": 2.5})

    def test_the_report_renders_from_two_years_of_one_country(self):
        log = self.rendered(1)                      # 1 for every figure: an AI country, a recognized one
        second = [line.replace(" FRA 3 24 ", " FRA 3 36 ") for line in log if "TE_AIP S " in line]
        parsed = ai_probe_report.parse_lines(log + second, self.key)
        out = ai_probe_report.report(parsed, self.key)
        for heading in ("The headline", "GDP growth by rank band", "1. Economic growth", "1b. Solvency",
                        "1c. Staffing", "1f. The Construction Sector itself", "1d. The government's purchase",
                        "1g. Construction points a week", "1h. The banking cycle",
                        "1e. Where the government's money goes",
                        "1i. The construction queue by kind", "1j. The cost of construction",
                        "1k. Labour and living standards",
                        "2. Technology", "2a. Specific technologies", "2b. Electrification", "3. Laws",
                        "3a. Law starts per idle month", "3b. How enactments ended", "3c. The old law kept",
                        "3d. Institutions", "3e. Bureaucracy", "4. Military", "4a. The army by unit type",
                        "4b. Where the irregulars come from", "5. Expansion", "5a. Diplomatic plays by type",
                        "5b. The world outside"):
            self.assertIn(heading, out)

    def test_every_table_leads_with_the_largest_economies(self):
        """The owner judges a run first by the big economies (2026-11-16): each lens table gives the largest first,
        then GDP-weighted totals, then the typical country."""
        log = self.rendered(1)
        second = [line.replace(" FRA 3 24 ", " FRA 3 36 ") for line in log if "TE_AIP S " in line]
        out = ai_probe_report.report(ai_probe_report.parse_lines(log + second, self.key), self.key)
        self.assertLess(out.index("A run is judged first by the largest economies"), out.index("## 1. Economic"))
        for section in out.split("\n## ")[1:]:
            if "**The typical country" not in section:
                continue
            with self.subTest(section=section.split("\n", 1)[0]):
                biggest = section.index(f"**The {ai_probe_report.TOP_N} largest AI economies")
                self.assertLess(biggest, section.index("**All AI countries, weighted by GDP"))
                self.assertLess(section.index("**All AI countries, weighted by GDP"),
                                section.index("**The typical country"))


class FreshTest(unittest.TestCase):
    """The five files are what this generator writes, for the catalog the key records."""

    def test_the_files_are_what_the_generator_writes_for_its_key(self):
        key = json.loads(KEY.read_text(encoding="utf-8"))
        for relative, (body, bom) in gen_ai_probe.render_outputs(gen_ai_probe.catalog_from_key(key)).items():
            with self.subTest(file=relative):
                expected = body.encode("utf-8-sig" if bom else "utf-8")
                self.assertEqual((ROOT / relative).read_bytes(), expected,
                                 "stale: run python3 scripts/generators/gen_ai_probe.py")

    def test_every_snapshot_line_is_under_the_version_that_added_it(self):
        key = json.loads(KEY.read_text(encoding="utf-8"))
        added = [name for names in key["lines_added"].values() for name in names]
        self.assertEqual(sorted(added), sorted(key["lines"]), "a line under no version, or under two")
        self.assertEqual(sorted(key["lines_added"]["1"]), sorted(json.loads(V1_LINES.read_text())["lines"]))

    def test_the_technology_flags_and_unit_types_are_defined(self):
        key = json.loads(KEY.read_text(encoding="utf-8"))
        self.assertEqual(set(key["tech_flags"].values()) - set(key["all_techs"]), set())
        for tech in gen_ai_probe.TECH_FLAGS:
            self.assertIn(tech, key["tech_flags"].values())
        info = key["unit_info"]
        self.assertEqual(info["u_line_infantry"]["techs"], ["line_infantry"])
        self.assertEqual(info["u_skirmish_infantry"]["techs"], ["general_staff"])
        self.assertEqual(info["u_irregular_infantry"]["tier"], 1)
        for field, members in key["unit_line"].items():
            if len(members) == 1:
                self.assertIn(field, info)
        self.assertIn("dp_annex_war", key["play_types"])

    def test_the_level_and_end_names_are_in_the_key(self):
        key = json.loads(KEY.read_text(encoding="utf-8"))
        self.assertEqual(key["level_names"][2], "medium")
        self.assertEqual(set(key["level_fields"]) - {f for fields in key["lines"].values() for f in fields}, set())
        self.assertEqual(key["law_end_how"], ["passed", "failed", "cancelled", "replaced"])


class ConstructionSectorTest(unittest.TestCase):
    """The O2 line's Construction Sector fields (gen_ai_probe.py, CONSTRUCTION_SECTOR)."""

    def setUp(self):
        self.key = json.loads(KEY.read_text(encoding="utf-8"))
        self.values = text(VALUES)

    def test_the_fields_fill_the_o2_line_and_add_no_line(self):
        o2 = self.key["lines"]["O2"]
        self.assertEqual(o2[0], "low_mfg_nc")
        self.assertEqual(len(o2), gen_ai_probe.FIELDS_PER_LINE)
        self.assertNotIn("O3", self.key["lines"])
        for name in ("cs_low", "cs_low80", "cs_staffed", "cs_sub", "cs_price", "cs_buy", "cs_sell", "site_low",
                     "site_low80", *self.key["construction_methods"]):
            self.assertIn(name, o2)

    def test_the_methods_are_the_sectors_and_each_counted_once(self):
        """Each sector level runs one construction method, so the cs_pm_* fields add up to the sector's levels."""
        methods = [m for members in self.key["construction_methods"].values() for m in members]
        self.assertEqual(len(methods), len(set(methods)))
        self.assertEqual(methods[:4], ["pm_wooden_buildings", "pm_iron_frame_buildings", "pm_steel_frame_buildings",
                                       "pm_arc_welded_buildings"])
        group = text(ROOT / "common/production_method_groups/13_construction.txt")
        group += text(ROOT / "common/production_method_groups/extra_pm_groups.txt")
        for method in methods:
            self.assertIn(f"\t\t{method}\n", group)

    def test_the_market_reads_use_the_construction_markets_own_chain(self):
        """te_construction_market_price reads the good's price through this chain, and its price moved in the
        first long run (cm_price 968 to 1,678 between the 10th and 90th percentiles), so the read works."""
        chain = "this.market.mg:construction.market_goods_pricier"
        self.assertIn(chain, text(ROOT / "common/script_values/te_construction_market_current_values.txt"))
        price = re.search(r"(?ms)^te_aip_cs_price = \{\n(.*?)^\}", self.values).group(1)
        self.assertIn(chain, price)
        self.assertIn("market_goods_cheaper min = 0", price)

    @unittest.skipUnless((GAME_STRATEGIES.parent / "defines/00_ai.txt").is_file(), "no game install")
    def test_the_80_percent_fields_test_the_ais_expansion_threshold(self):
        defines = text(GAME_STRATEGIES.parent / "defines/00_ai.txt")
        found = re.search(r"PRODUCTION_BUILDING_LOW_EMPLOYMENT_THRESHOLD = ([0-9.]+)", defines)
        self.assertEqual(float(found.group(1)), self.key["ai_expansion_staffing"])

    def test_check_reads_each_field_against_the_others(self):
        def snapshot(**fields):
            row = {"bt_construction_sector": 10, "cs_low": 2, "cs_low80": 6, "cs_staffed": 6.5, "cs_sub": 0,
                   "cs_pm_wooden": 4, "cs_pm_iron_frame": 6, "cs_pm_steel_frame": 0, "cs_pm_arc_welded": 0,
                   "cs_pm_later": 0, "cs_price": 1.35, "cs_buy": 40, "cs_sell": 31, "site_low": 1, "site_low80": 2,
                   "bg_te_construction_market_bg": 3}
            row.update(fields)
            return row

        lines, ok = ai_probe_report.check_construction_sector(self.key, [snapshot(), snapshot(cs_price=0.9)])
        self.assertTrue(ok, "\n".join(lines))
        self.assertTrue(any("add to its levels in 2 of 2" in line for line in lines), "\n".join(lines))
        lines, ok = ai_probe_report.check_construction_sector(self.key, [snapshot(cs_staffed=0)])
        self.assertFalse(ok)
        self.assertTrue(any("occupancy did not read" in line for line in lines))
        lines, ok = ai_probe_report.check_construction_sector(self.key, [snapshot(cs_price=1)])
        self.assertFalse(ok)
        # A version-1 snapshot carries none of the fields: nothing to read, and no verdict.
        self.assertEqual(ai_probe_report.check_construction_sector(self.key, [{"bt_construction_sector": 5}])[1], True)


class OldLogTest(unittest.TestCase):
    """A version-1 log (the first long run's) still parses and reports with this version's key."""

    def setUp(self):
        self.key = json.loads(KEY.read_text(encoding="utf-8"))
        with open(V1_SAMPLE, encoding="utf-8") as handle:
            self.parsed = ai_probe_report.parse_lines(handle, self.key)

    def test_version_1_lines_are_unchanged_or_only_extended(self):
        """Positional lines are read by position, so they may never change; a keyed line may only grow."""
        v1 = json.loads(V1_LINES.read_text(encoding="utf-8"))
        for name, fields in v1["lines"].items():
            with self.subTest(line=name):
                now = self.key["lines"][name]
                if name[0] in v1["positional_groups"]:
                    self.assertEqual(now, fields)
                else:
                    self.assertEqual(now[:len(fields)], fields)

    def test_the_sample_parses_with_nothing_unreadable(self):
        self.assertEqual(self.parsed.bad, [])
        self.assertEqual(self.parsed.version(), 1)
        records = {(r["tag"], r["k"]): r for r in self.parsed.records()}
        self.assertEqual(set(records), {("GBR", 1), ("GBR", 13), ("LUX", 11)})
        gbr = records[("GBR", 13)]
        self.assertEqual((gbr["y"], gbr["gdp"], gbr["lit"]), (1837, 29618712, 0.494))
        self.assertEqual(gbr["lw_governance_principles"], 2)          # L1's first value
        self.assertNotIn("im_schools", gbr)                           # version 2's, not logged then
        play = next(e for e in self.parsed.events if e["event"] == "play")
        self.assertEqual((play["tag"], play["id"], play["target"]), ("HER", 0, "MAI"))

    def test_check_passes_it_without_asking_for_version_2_lines(self):
        lines, ok = ai_probe_report.check(self.parsed, self.key)
        self.assertTrue(ok, "\n".join(lines))
        self.assertFalse(any("NEVER" in line for line in lines), "\n".join(lines))
        self.assertFalse(any("MISSING" in line for line in lines), "\n".join(lines))   # nor version 4's canaries

    def test_the_report_renders_it(self):
        out = ai_probe_report.report(self.parsed, self.key)
        self.assertIn("## 1. Economic growth", out)
        self.assertIn("Not logged by this log's probe version (version 2 adds the H line)", out)
        self.assertIn("Not logged by this log's probe version (version 4 adds the P and H2 lines)", out)
        self.assertIn("## 3a. Law starts per idle month", out)
        self.assertNotIn("## 4a.", out)                               # no unit line in version 1
        for heading in ("## 1i.", "## 1j.", "## 1k.", "## 3e."):         # version 4's, not logged then
            self.assertNotIn(heading, out)
        self.assertIn("## 4b. Where the irregulars come from", out)   # the net change reads version 1's M line


class LawEndTest(unittest.TestCase):
    """How an enactment ended: the pass and fail hooks mark it before the end hook reads it."""

    def hook(self, name):
        return re.search(rf"(?ms)^{name} = \{{\n(.*?)^\}}", text(ON_ACTIONS)).group(1)

    def test_pass_and_fail_mark_before_they_log(self):
        for name, mark in (("te_aip_law_passed", 1), ("te_aip_law_failed", 2)):
            body = self.hook(name)
            self.assertLess(body.index(f"set_variable = {{ name = te_aip_law_how value = {mark} }}"),
                            body.index("te_aip_law_event"), name)

    def test_the_end_logs_how_then_spends_any_mark_but_the_passes(self):
        effect = re.search(r"(?ms)^te_aip_law_end_event = \{\n(.*?)^\}", text(EFFECTS)).group(1)
        self.assertLess(effect.index("how=[THIS.ScriptValue('te_aip_ev_law_how')|0]"),
                        effect.index("remove_variable = te_aip_law_how"))
        self.assertIn("NOT = { var:te_aip_law_how = 1 }", effect)
        how = re.search(r"(?ms)^te_aip_ev_law_how = \{\n(.*?)^\}", text(VALUES)).group(1)
        self.assertIn("value = var:te_aip_law_how", how)
        self.assertIn("law_is_available = no } } value = 4", how)

    def test_an_activation_takes_the_pass_mark_or_counts_as_a_law_set(self):
        body = self.hook("te_aip_law_activated")
        self.assertLess(body.index("remove_variable = te_aip_law_how"), body.index("te_aip_count = { N = law_set }"))
        self.assertIn("on_law_activated = {\n\ton_actions = { te_aip_law_activated }", text(ON_ACTIONS))

    def test_a_start_clears_a_mark_left_from_before(self):
        body = self.hook("te_aip_law_started")
        self.assertLess(body.index("remove_variable = te_aip_law_how"), body.index("te_aip_law_event"))


class PlayLineTest(unittest.TestCase):
    def test_the_play_line_reads_only_globals_set_before_it(self):
        """A script value read in debug_log cannot see a saved scope, so the line reads globals the effect set."""
        body = re.search(r"(?ms)^te_aip_play_started = \{\n(.*?)^\}", text(ON_ACTIONS)).group(1)
        line = re.search(r'debug_log = "([^"]*)"', body)
        reads = set(_SCRIPT_VALUE.findall(line.group(1)))
        self.assertEqual(reads - {"te_aip_k"}, {f"te_aip_ev_play_{name}" for name in
                                                ("type", "a_id", "a_rank", "b_id", "b_rank")})
        for name in ("type", "a_id", "a_rank", "b_id", "b_rank"):
            self.assertLess(body.index(f"set_global_variable = {{ name = te_aip_play_{name} "), line.start())
        self.assertIn("te_aip_play_type_index = {", text(VALUES))


class ReportPartsTest(unittest.TestCase):
    def test_the_cadence_counts_idle_months_against_the_agenda_held(self):
        ai = [{"tag": "AAA", "k": 1, "strat_political": 1}, {"tag": "AAA", "k": 13, "strat_political": 3}]
        events = [{"event": "law_start", "tag": "AAA", "k": 2}, {"event": "law_end", "tag": "AAA", "k": 5},
                  {"event": "law_start", "tag": "AAA", "k": 10}, {"event": "law_end", "tag": "AAA", "k": 20}]
        rows = ai_probe_report.law_cadence(events, ai, ["first", "second", "third"], from_k=6)
        self.assertEqual(len(rows), 1)
        self.assertEqual({f: rows[0][f] for f in ("agenda", "starts", "months", "starts_late", "months_late")},
                         {"agenda": "first", "starts": 2, "months": 6, "starts_late": 1, "months_late": 4})
        self.assertEqual(rows[0]["waits"], [1, 5])

    def test_a_default_soon_after_the_last_continues_its_episode(self):
        events = [{"event": "default", "tag": "AAA", "k": 1}, {"event": "default_end", "tag": "AAA", "k": 1},
                  {"event": "default", "tag": "AAA", "k": 2}, {"event": "default_end", "tag": "AAA", "k": 3},
                  {"event": "default", "tag": "AAA", "k": 20}, {"event": "default", "tag": "BBB", "k": 4}]
        self.assertEqual([(e["tag"], e["k"]) for e in ai_probe_report.default_episodes(events)],
                         [("AAA", 1), ("BBB", 4), ("AAA", 20)])

    def test_the_purchase_restated_over_a_snapshot_matches_the_script(self):
        """purchase_target against the script itself, run by the construction market's own evaluator."""
        import itertools

        import test_construction_market_ai_purchase as purchase
        count = 0
        # cm_admin (short of bureaucracy with an administration queued) is no term of the purchase since the
        # purchase through the engine's pause was removed (2026-11-16): the restatement gives the script's figure
        # whichever way the field reads.
        # From version 5 the rate's terms come from the snapshot's cm_reserve and cm_credit, which the probe reads
        # from the script's own values (te_construction_market_ai_required_reserves, _credit_allowance).
        for (fixed, price), share, (reserves, debt), bureaucracy, paused, war, bubble, (queued, weekly), admin, rate in \
                itertools.product(((857.0, 1249.0), (75817.0, 1256.0)), (-0.25, 0.03, 0.33),
                                  ((0.0, 0.0), (0.04, 0.0), (0.6, 0.0), (0.0, 0.03), (0.0, 0.3), (0.0, 0.45)),
                                  (50.0, -5.0), (False, True), (False, True), (None, 60.0),
                                  ((0, 20.0), (1, 10.0), (3, 140.0)), (0, 1), (None, 3.5, 6.0, 11.5)):
            c = purchase.Country(fixed, share * fixed, price, reserves, debt, bureaucracy, queued, weekly,
                                 paused=paused, at_war=war, bubble=bubble, rate=rate)
            record = {"cm_price": price, "fixed_income": fixed, "net_fixed": share * fixed, "gold_scaled": reserves,
                      "debt_scaled": debt, "queue_gov": queued, "cm_level_max": weekly, "paused": int(paused),
                      "war": int(war), "bubble": bubble or 0, "bur": bureaucracy, "cm_admin": admin}
            if rate is not None:
                record["cm_reserve"], record["cm_credit"] = purchase.values(c, *purchase.CURVE)
            count += 1
            with self.subTest(record=record):
                self.assertAlmostEqual(ai_probe_report.purchase_target(record), c.script(), delta=purchase.STEP)
        self.assertGreater(count, 4000)
        self.assertIsNone(ai_probe_report.purchase_target({"cm_price": 1000}))     # version 1: a term missing


def block(name: str, body: str) -> str:
    """A top-level `name = { ... }` block's body."""
    return re.search(rf"(?ms)^{name} = \{{\n(.*?)^\}}", body).group(1)


class WorldLineTest(unittest.TestCase):
    """Version 3's W line: every_country does not reach a decentralized nation (version 2's dn read 0 in every line
    of run 3, while the same game's decentralized_law_baseline self-check found them with
    any_decentralized_country)."""

    def test_decentralized_nations_are_counted_with_their_own_iterator(self):
        values = text(VALUES)
        for name in ("te_aip_w_dn", "te_aip_w_dn_states"):
            body = block(name, values)
            self.assertIn("every_decentralized_country = {", body, name)
            self.assertNotIn("every_country", body, name)

    def test_the_land_is_read_a_second_way(self):
        values = text(VALUES)
        self.assertIn("every_state = { add = 1 }", block("te_aip_w_states", values))
        self.assertIn("add = num_states", block("te_aip_w_c_states", values))
        self.assertEqual(gen_ai_probe.WORLD_FIELDS[:3], ["countries", "dn", "dn_states"])   # version 2's first

    def test_check_reads_the_two_ways_against_each_other(self):
        parsed = ai_probe_report.Parsed()
        parsed.world = {1: {"k": 1, "y": 1836, "countries": 290, "dn": 150, "dn_states": 200, "states": 900,
                            "c_states": 700}}
        lines = ai_probe_report.check_version_3(parsed, {}, [])
        self.assertTrue(any("equals states - c_states in 1 of 1" in line for line in lines), lines)
        parsed.world[1].update(dn=0, dn_states=0)
        lines = ai_probe_report.check_version_3(parsed, {}, [])
        self.assertTrue(any("dn is 0 in every line" in line for line in lines), lines)


class ScheduleTest(unittest.TestCase):
    """Version 3 reports each country once a calendar year, in its own month (te_aip_country_tick)."""

    def test_the_tick_keys_the_report_to_a_calendar_month(self):
        tick = block("te_aip_country_tick", text(EFFECTS))
        self.assertNotIn("te_aip_m ", tick.replace("te_aip_m,", ""))      # versions 1 and 2's pulse count
        self.assertIn("set_variable = { name = te_aip_due value = te_aip_first_due }", tick)
        self.assertIn("limit = { te_aip_due_in < 0 }", tick)
        due = tick.index("limit = { te_aip_due_in <= 0 }")
        self.assertLess(tick.index("set_variable = { name = te_aip_due value = te_aip_next_due }", due),
                        tick.index("te_aip_snapshot = yes", due))
        values = text(VALUES)
        index = block("te_aip_month_index", values)
        self.assertEqual(re.findall(r"month = (\d+) \} add = (\d+)", index), [(str(m), str(m)) for m in range(1, 12)])
        self.assertIn("add = 1\n\tmultiply = 12\n\tadd = te_aip_id_phase", block("te_aip_next_due", values))

    def test_the_schedule_as_written_reports_once_a_calendar_year(self):
        """The tick restated: 30-day pulses at every phase, every reporting month, from a first sight in any month."""
        for slot in range(12):
            for first_day in range(0, 365, 7):
                due, reports = None, Counter()
                for day in range(first_day, first_day + 365 * 30, 30):
                    year, day_of_year = 1836 + day // 365, day % 365
                    month = next(m for m in range(11, -1, -1) if day_of_year >= MONTH_STARTS[m])
                    now = year * 12 + month
                    if due is None:
                        due = year * 12 + slot
                        if due - now < 0:
                            due += 12
                    if due - now <= 0:
                        due = (year + 1) * 12 + slot
                        reports[(year, month)] += 1
                years = Counter(year for year, _ in reports)
                with self.subTest(slot=slot, first_day=first_day):
                    self.assertEqual(set(years.values()), {1})
                    self.assertLessEqual(max(years) - min(years) + 1, 31)
                    self.assertEqual({(month - slot) % 12 for _, month in reports} - {0, 1}, set())
                    if slot != 1:                                     # February's pulse can miss February
                        self.assertEqual({month for _, month in reports}, {slot})

    def test_check_flags_a_doubled_year_in_a_version_3_log(self):
        key = json.loads(KEY.read_text(encoding="utf-8"))
        parsed = ai_probe_report.Parsed()
        parsed.ticks = {1: {"y": 1900, "date": "January 1, 1900"}, 12: {"y": 1900, "date": "December 1, 1900"}}
        records = [{"tag": "CHI", "id": 12, "k": 1, "y": 1900}, {"tag": "CHI", "id": 12, "k": 12, "y": 1900}]
        lines = ai_probe_report.check_spacing(parsed, key, records, 3)
        self.assertTrue(any("did not work as written" in line for line in lines), lines)
        self.assertTrue(any("own month: 1, the month after 0, the month before 1" in line for line in lines), lines)
        lines = ai_probe_report.check_spacing(parsed, key, records, 2)
        self.assertFalse(any("did not work" in line for line in lines), lines)


MONTH_STARTS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]     # the game's year has no leap day


class BankingCycleTest(unittest.TestCase):
    """Version 3's banking fields (gen_ai_probe.py, BANK_PHASES)."""

    def test_the_phases_are_the_bands_the_triggers_test(self):
        triggers = text(ROOT / "common/scripted_triggers/market_triggers.txt")
        bands = dict(re.findall(r"(?m)^banking_cycle_is_([a-z]+) = \{ (.*) \}$", triggers))
        self.assertEqual([phase for phase in bands if phase != "recession"][:7], gen_ai_probe.BANK_PHASES)
        edges = [int(x) for x in re.findall(r">= (\d+)", " ".join(bands[p] for p in gen_ai_probe.BANK_PHASES))]
        self.assertEqual(sorted(set(edges)), [10, 25, 40, 60, 75, 88])        # check_version_3's band edges

    def test_every_phase_read_is_guarded_by_the_running_cycle(self):
        phase = block("te_aip_bank_phase", text(VALUES))
        tests = re.findall(r"limit = \{ (.*?) \}", phase)
        self.assertEqual(tests, ["te_banking_cycle_running = yes"]
                         + [f"banking_cycle_is_{name} = yes" for name in gen_ai_probe.BANK_PHASES])
        inside = phase.index("te_banking_cycle_running = yes")
        self.assertTrue(all(phase.index(f"banking_cycle_is_{name}") > inside for name in gen_ai_probe.BANK_PHASES))
        tick = block("te_aip_country_tick", text(EFFECTS))
        guard = tick.index("te_banking_cycle_running = yes")
        self.assertLess(guard, tick.index("banking_cycle_is_recession = yes"))
        self.assertLess(guard, tick.index("te_aip_count = { N = bank_down }"))

    def test_the_fields_join_existing_lines(self):
        key = json.loads(KEY.read_text(encoding="utf-8"))
        c2 = key["lines"]["C2"]
        start = c2.index("bank_phase")
        self.assertEqual(c2[start:start + 4], ["bank_phase", "bank_cycle", "bank_momentum", "bank_crashed"])
        self.assertEqual(key["lines"]["N2"][-1], "n_bank_down")
        self.assertEqual(key["lines_added"]["3"], [])
        crashed = re.search(r"(?m)^te_aip_bank_crashed = \{.*$", text(VALUES)).group(0)
        self.assertIn("has_variable = banking_crashed_last_year", crashed)
        marker = text(ROOT / "common/scripted_effects/banking_cycle_effects.txt")
        self.assertIn("set_variable = { name = banking_crashed_last_year value = 1 days = 365 }", marker)

    def test_version_5_adds_the_rate_and_the_pass_to_the_end_of_c2(self):
        key = json.loads(KEY.read_text(encoding="utf-8"))
        self.assertEqual(key["lines"]["C2"][-7:], ["rate", "rate_base", "cm_reserve", "cm_credit", "cm_pass",
                                                   "inf_short_states", "inf_short"])
        # C2 is full, so the states the railway entry would act on end B2, the line with room nearest in kind.
        self.assertEqual(len(key["lines"]["C2"]), gen_ai_probe.FIELDS_PER_LINE)
        self.assertEqual(key["lines"]["B2"][-1], "rail_sites")
        self.assertNotIn("C3", key["lines"])
        self.assertEqual(key["lines_added"]["5"], [])
        values = text(VALUES)
        for field, source in (("rate", "var:te_rate_paid_pts"), ("rate_base", "var:te_mon_era_base_now"),
                              ("cm_reserve", "te_construction_market_ai_required_reserves"),
                              ("cm_credit", "te_construction_market_ai_credit_allowance"),
                              ("cm_pass", "var:te_ai_build_pass_count")):
            line = re.search(rf"(?m)^te_aip_{field} = \{{.*$", values).group(0)
            self.assertIn(source, line, field)
        # The railway entry's reading, the pass's own shortfall (te_ai_build_pass_values.txt), summed over the states
        # short of infrastructure.
        for field, added in (("inf_short_states", "add = 1"),
                             ("inf_short", "add = te_ai_build_pass_infrastructure_shortfall")):
            body = re.search(rf"(?ms)^te_aip_{field} = \{{\n(.*?)^\}}", values).group(1)
            self.assertIn("limit = { te_ai_build_pass_infrastructure_shortfall > 0 }", body, field)
            self.assertIn(added, body, field)
        # The states the entry acts on: its own site test (incorporated, short by more than its margin).
        body = re.search(r"(?ms)^te_aip_rail_sites = \{\n(.*?)^\}", values).group(1)
        self.assertIn("limit = { te_ai_build_pass_railway_site = yes }", body)
        self.assertIn("add = 1", body)
        # The report's restatement gains the rate at the script's own gain.
        gain = re.search(r"(?m)^TE_CONSTRUCTION_MARKET_AI_RATE_GAIN = ([0-9.]+)",
                         text(ROOT / "common/script_values/te_construction_market_ai_values.txt")).group(1)
        self.assertEqual(ai_probe_report.RATE_GAIN, float(gain))

    def test_check_holds_the_phase_to_the_value(self):
        key = json.loads(KEY.read_text(encoding="utf-8"))
        rows = [{"bank_phase": 1, "bank_cycle": 9.9}, {"bank_phase": 4, "bank_cycle": 40.0},
                {"bank_phase": 0, "bank_cycle": 0}]
        lines = ai_probe_report.check_version_3(ai_probe_report.Parsed(), key, rows)
        self.assertTrue(any("band of bank_cycle in 2 of 2" in line for line in lines), lines)
        rows.append({"bank_phase": 7, "bank_cycle": 50.0})
        lines = ai_probe_report.check_version_3(ai_probe_report.Parsed(), key, rows)
        self.assertTrue(any("does not read as written" in line for line in lines), lines)


class VersionFourTest(unittest.TestCase):
    """Version 4's additions (#1877): the H2 and P lines, X7 and X8, the W line's rules (and the army census, retired
    in version 6)."""

    def setUp(self):
        self.key = json.loads(KEY.read_text(encoding="utf-8"))
        self.values = text(VALUES)
        self.effects = text(EFFECTS)

    def test_version_3_lines_are_unchanged_or_only_extended(self):
        """A version-3 log (runs 1 to 4 were versions 1 to 3) still parses: its positional lines are read by position."""
        v3 = json.loads(V3_LINES.read_text(encoding="utf-8"))
        for name, fields in v3["lines"].items():
            with self.subTest(line=name):
                now = self.key["lines"][name]
                if name[0] in v3["positional_groups"]:
                    self.assertEqual(now, fields)
                else:
                    self.assertEqual(now[:len(fields)], fields)
        self.assertEqual(self.key["world_fields"][:len(v3["world_fields"])], v3["world_fields"])
        self.assertEqual(self.key["data_functions"][:len(v3["data_functions"])], v3["data_functions"])
        self.assertEqual(sorted(set(self.key["lines"]) - set(v3["lines"])), sorted(self.key["lines_added"]["4"]))

    def test_a_snapshot_grows_by_five_lines_at_most(self):
        """The game rotates its log every 512 KB: version 3 wrote 36 lines a snapshot (8.1 KB in run 4)."""
        v3 = json.loads(V3_LINES.read_text(encoding="utf-8"))
        x_lines = {line for line, _, _ in gen_ai_probe.DATA_FUNCTIONS}
        old_x = {line for line, key, _ in gen_ai_probe.DATA_FUNCTIONS if key in v3["data_functions"]}
        self.assertLessEqual(len(self.key["lines"]) - len(v3["lines"]) + len(x_lines) - len(old_x), 5)

    def test_the_headquarters_field_reads_the_group(self):
        body = re.search(r"(?m)^te_aip_bt_company_headquarter = \{(.*)\}$", self.values).group(1)
        self.assertIn('"country_has_building_group_levels(bg_company_headquarter)"', body)
        self.assertIn("bg_company_headquarter", self.key["building_groups"])
        self.assertIn("bt_company_headquarter", self.key["lines"]["B2"])          # the line keeps its field

    def test_h2_carries_the_electricity_technologies_and_h1_is_version_3s(self):
        v3 = json.loads(V3_LINES.read_text(encoding="utf-8"))
        self.assertEqual(self.key["lines"]["H1"], v3["lines"]["H1"])
        self.assertEqual(self.key["lines"]["H2"], ["h_" + t for t in self.key["tech_flags_4"]])
        for tech in ("electrical_generation", "steam_turbine", "radio"):
            self.assertIn(tech, self.key["tech_flags_4"])
            self.assertIn(tech, self.key["all_techs"])
        self.assertEqual(set(self.key["tech_flags_4"]) - set(self.key["tech_flags"].values()), set())

    def test_the_units_the_analysis_found_blocked_are_unlocked_by_h1_flags(self):
        flags = set(self.key["tech_flags"].values())
        for unit in ("u_squad_infantry", "u_mechanized_infantry", "u_siege_artillery", "u_light_tanks"):
            self.assertTrue(self.key["unit_info"][unit]["techs"], unit)
            self.assertEqual(set(self.key["unit_info"][unit]["techs"]) - flags, set(), unit)

    def test_the_rules_name_defined_settings_and_every_setting_of_their_rule(self):
        """has_game_rule on an undefined setting is true, so the index would read 1 in every game."""
        gen_ai_probe.check_rules(ROOT)
        rules = "\n".join(text(p) for p in sorted((ROOT / "common/game_rules").glob("*.txt")))
        for name, rule, settings in gen_ai_probe.RULES:
            with self.subTest(rule=rule):
                rule_block = re.search(rf"(?ms)^{rule} = \{{\n(.*?)^\}}", rules).group(1)
                self.assertEqual(set(re.findall(r"(?m)^\t([a-z_]+) = \{", rule_block)), set(settings))
                self.assertEqual(self.key["rules"][name]["settings"], settings)
                body = block_text("te_aip_w_" + name, self.values)
                tests = gen_ai_probe.rule_tests(name, settings)
                self.assertEqual(re.findall(r"limit = \{ (.*?) \}", body), tests)
                self.assertEqual(len(tests), len(settings))
        # A setting read through a system's trigger: the trigger is defined and names its rule's settings only.
        triggers = "\n".join(text(p) for p in (ROOT / "common/scripted_triggers").glob("*.txt"))
        for name, tests in gen_ai_probe.RULE_TESTS.items():
            settings = self.key["rules"][name]["settings"]
            for test in tests:
                trigger = test.split(" = ")[0]
                with self.subTest(trigger=trigger):
                    body = block(trigger, triggers)
                    self.assertTrue(set(re.findall(r"has_game_rule = ([a-z_]+)", body)) <= set(settings), body)
        self.assertIn("r_fmc", self.key["world_fields"])
        self.assertEqual(set(gen_ai_probe.RETOOLING_WAIVED) - set(self.key["rules"]["r_fmc"]["settings"]), set())

    def test_the_waived_settings_are_the_ones_the_retooling_removal_reads(self):
        triggers = text(ROOT / "common/scripted_triggers/te_construction_market_triggers.txt")
        named = set(re.findall(r"has_game_rule = (free_market_construction_[a-z_]+)", triggers))
        named.discard("free_market_construction_disabled")
        self.assertEqual(named, set(gen_ai_probe.RETOOLING_WAIVED))
        # The report's own copy, for a key from before version 4.
        self.assertEqual(ai_probe_report.RETOOLING_WAIVED_BEFORE_V4, gen_ai_probe.RETOOLING_WAIVED)

    def test_the_street_lighting_fields_cover_the_group(self):
        groups = text(ROOT / "common/production_method_groups/extra_pm_groups.txt")
        later = re.search(r"(?ms)^INJECT:pmg_street_lighting = \{\n(.*?)^\}", groups).group(1)
        lights = self.key["street_lights"]
        self.assertEqual(lights["uc_gas_light"], ["pm_gas_streetlights"])
        self.assertEqual(lights["uc_elec_light"][0], "pm_electric_streetlights")
        for method in re.findall(r"(?m)^\t\t(pm_[a-z_]+)$", later):
            self.assertIn(method, lights["uc_elec_light"])
        self.assertIn("uc_no_light", self.key["lines"]["O1"])                    # the third: no lighting

    def test_the_values_the_p_line_borrows_exist(self):
        """A script value or trigger that is renamed breaks the read: each borrowed name must stay defined."""
        defined = ""
        for folder in ("script_values", "scripted_triggers"):
            for path in (ROOT / "common" / folder).glob("*.txt"):
                if path.name != VALUES.name:
                    defined += text(path)
        borrowed = [gen_ai_probe.QUEUED_LEVELS, *gen_ai_probe.ELECTRICITY_VALUES.values(), "te_cc_scaling_factor",
                    "te_cc_total_factor", "te_state_has_a_power_plant"]
        for name in borrowed:
            self.assertRegex(defined, rf"(?m)^{name} = \{{", name)
            self.assertIn(name, self.values)
        for name in ("te_grid_electricity_production", "te_grid_electricity_consumption"):
            self.assertIn("sg:electricity ?=", block_text(name, defined))
        self.assertIn("te_cc_slack", self.values)
        self.assertIn("set_variable = { name = te_cc_slack value = te_country_slack_share }",
                      text(ROOT / "common/scripted_effects/te_construction_cost_effects.txt"))

    def test_no_variable_is_set_on_a_combat_unit(self):
        """A combat unit holds no variables (#2090): the census that marked battalions is out, with its canary."""
        for body in (self.effects, self.values):
            # No walk reaches a battalion (the R line's types are read on the country, not in a unit's scope).
            self.assertIsNone(re.search(r"\b(every|random|ordered)_combat_unit\b", body))
            self.assertNotIn("unit_vars", body)
        self.assertNotIn("te_aip_unit_census", self.effects)
        self.assertNotIn("unit_type_index", self.key)

    def test_a_version_5_log_still_reads(self):
        """Version 5's lines are this version's, but for the army census's six fields, retired from P2's end: an
        older P2 line carries them, and the parser drops them."""
        v5 = json.loads(V5_LINES.read_text(encoding="utf-8"))
        retired = self.key["retired_tail"]
        self.assertEqual(retired, {"P2": ["u_all", "u_new", "u_changed", "u_irr_new", "u_from_irr", "u_flows"]})
        for name, fields in v5["lines"].items():
            with self.subTest(line=name):
                now = self.key["lines"][name]
                if name[0] in v5["positional_groups"]:
                    self.assertEqual(now + retired.get(name, []), fields)
                else:
                    self.assertEqual(now[:len(fields)], fields)
        p2 = v5["lines"]["P2"]
        log = ["[12:00:00][jomini_effect.cpp:1]: TE_AIP S P2 FRA 3 24 " + ";".join(str(i) for i in range(len(p2))),
               "[12:00:00][jomini_effect.cpp:1]: TE_AIP CANARY unit_vars v=0"]
        parsed = ai_probe_report.parse_lines(log, self.key)
        self.assertEqual(parsed.bad, [])
        record = parsed.snapshots[(3, 24)]
        self.assertEqual([record[f] for f in self.key["lines"]["P2"]], list(range(len(self.key["lines"]["P2"]))))
        self.assertNotIn("u_all", record)
        # A line of any other length is still refused.
        short = ai_probe_report.parse_lines(["TE_AIP S P2 FRA 3 24 1;2"], self.key)
        self.assertEqual(len(short.bad), 1)

    def test_the_data_functions_of_a_version(self):
        self.assertEqual(ai_probe_report.data_functions_of(self.key, 3),
                         json.loads(V3_LINES.read_text(encoding="utf-8"))["data_functions"])
        self.assertEqual(ai_probe_report.data_functions_of(self.key, 4), self.key["data_functions"])
        sol = next(a for _, k, a in gen_ai_probe.DATA_FUNCTIONS if k == "sol_lower")
        self.assertEqual(gen_ai_probe.data_function_text(sol), "GetTrendValue(THIS.GetCountry.GetAverageSoLLowerTrend)|1")

    def row(self, **fields):
        row = {"tag": "AAA", "id": 1, "k": 13, "y": 1926, "states": 4, "pp_states": 1, "bg_power": 3, "elec_made": 40,
               "elec_used": 35, "elec_price": 1.4, "bt_urban_center": 10, "uc_no_light": 5, "uc_gas_light": 3,
               "uc_elec_light": 2, "h_electrical_generation": 1, "radio_price": 1.2, "radio_buy": 5, "radio_sell": 4,
               "queue_gov": 6, "queue_levels": 20, "q_uni": 2, "q_admin": 1, "q_mil": 1, "q_infra": 3, "q_power": 1,
               "cc_scale": 2.1, "cc_total": 2.3, "bur_add": 0, "bur_mult": 0.1, "bur_cost_add": 0, "bur_inst_mult": 0.25,
               "bur_pop_mult": 0, "slack": 0.3, "slack_peasants": 0.2, "army": 20, "sol": 12.0, "bur_used": 300,
               "in_schools": 2, "bt_company_headquarter": 3, "bg_company_headquarter": 3,
               "x": {"bur_inst": 120, "sol_lower": 9.0, "sol_upper": 25.0}}
        row.update(fields)
        return row

    def parsed(self, fmc=3, unit_vars=None):
        parsed = ai_probe_report.Parsed()
        parsed.world = {1: {"k": 1, "y": 1925, "r_fmc": fmc, "r_small": 1, "r_bank": 1}}
        if unit_vars is not None:               # a version 4 or 5 log's census canary
            parsed.canary["unit_vars"] = unit_vars
        return parsed

    def test_check_reads_the_rules_and_each_field_against_the_others(self):
        lines = ai_probe_report.check_version_4(self.parsed(), self.key, [self.row(), self.row(id=2)])
        text_ = "\n".join(lines)
        self.assertIn("free_market_construction_rule free_market_construction_no_retooling", text_)
        self.assertIn("rt_* reads 0 by design", text_)
        self.assertIn("none + gas + electric = urban centre levels in 2 of 2", text_)
        self.assertIn("universities + administrations + military <= queue_gov in 2 of 2", text_)
        self.assertNotIn("army census", text_)
        self.assertIn("lower <= average <= upper in 2 of 2", text_)
        lines = ai_probe_report.check_version_4(self.parsed(unit_vars=0), self.key,
                                                [self.row(uc_elec_light=4, h_electrical_generation=0)])
        text_ = "\n".join(lines)
        self.assertIn("retired in version 6, since a combat unit holds no variables", text_)
        self.assertIn("in 0 of 1; electric lights without Electrical Generation in 1", text_)
        # Under `enabled`, retooling at 0 with production methods changing is a read that fails.
        lines = ai_probe_report.check_version_4(self.parsed(fmc=1), self.key, [self.row(n_pm=5, rt_all=0)])
        self.assertTrue(any("does not read in a building walk" in line for line in lines), lines)

    def test_a_version_3_log_says_why_rt_and_the_headquarters_type_read_0(self):
        notes = ai_probe_report.dead_field_notes(ai_probe_report.Parsed(), self.key,
                                                 ["rt_mfg", "rt_all", "bt_company_headquarter"], 3)
        self.assertTrue(any("free_market_construction_no_retooling" in note for note in notes), notes)
        self.assertTrue(any("bg_company_headquarter" in note for note in notes), notes)
        self.assertEqual(ai_probe_report.dead_field_notes(ai_probe_report.Parsed(), self.key,
                                                          ["bt_company_headquarter"], 4), [])
        # A key from before version 4 lists no waiving settings: the note still names them.
        old_key = {k: v for k, v in self.key.items() if k != "retooling_waived"}
        note = ai_probe_report.dead_field_notes(ai_probe_report.Parsed(), old_key, ["rt_all"], 1)[0]
        self.assertIn("Under free_market_construction_no_ai_retooling", note)


def block_text(name: str, body: str) -> str:
    """A top-level `name = { ... }` block's body, one line or many."""
    one = re.search(rf"(?m)^{name} = \{{ (.*) \}}$", body)
    return one.group(1) if one else block(name, body)


class OnceAYearTest(unittest.TestCase):
    def test_a_second_report_in_a_year_is_folded_into_the_later_with_its_counters(self):
        rows = [{"tag": "CHI", "id": 4, "k": 768, "y": 1900, "gdp": 10, "n_built": 3, "n_law_pass": 1},
                {"tag": "CHI", "id": 4, "k": 779, "y": 1900, "gdp": 12, "n_built": 5, "n_law_pass": 0},
                {"tag": "CHI", "id": 4, "k": 791, "y": 1901, "gdp": 13, "n_built": 2, "n_law_pass": 2},
                {"tag": "GBR", "id": 9, "k": 770, "y": 1900, "gdp": 50, "n_built": 1}]
        kept, folded = ai_probe_report.once_a_year(rows)
        self.assertEqual(folded, 1)
        china = [r for r in kept if r["tag"] == "CHI"]
        self.assertEqual([(r["k"], r["gdp"], r["n_built"], r["n_law_pass"]) for r in china],
                         [(779, 12, 8, 1), (791, 13, 2, 2)])
        self.assertEqual(rows[1]["n_built"], 5)                       # the input is not changed


class ConstructionReadingTest(unittest.TestCase):
    """The X construction readings the report leaves out (ai_probe_report.x_construction)."""

    def row(self, paused=0, queue_priv=10, pool=5_000_000, **x):
        reading = {"con_used": 500.0, "con_used_priv": 400.0, "con_used_gov": 100.0, "con_base": 500.0,
                   "con_unused": 0.0, "con_goods_priv": 560_000, "con_goods_gov": 140_000}
        reading.update(x)
        return {"paused": paused, "queue_priv": queue_priv, "pool": pool, "x": reading}

    def test_the_kinds(self):
        kind = ai_probe_report.x_construction
        self.assertEqual(kind(self.row()), "ok")
        self.assertEqual(kind({"x": {}}), "none")
        # Great Britain 1893 in run 1: 1,463.5 private points, no private goods booked.
        self.assertEqual(kind(self.row(con_used_priv=1463.5, con_goods_priv=0)), "unpaid")
        idle = dict(con_used=0.0, con_used_priv=0.0, con_used_gov=0.0, con_base=0.0, con_goods_priv=0)
        self.assertEqual(kind(self.row(**idle)), "idle")
        self.assertEqual(kind(self.row(paused=1, **idle)), "ok")              # paused: rightly no construction
        self.assertEqual(kind(self.row(queue_priv=0, **idle)), "ok")          # nothing to build
        self.assertEqual(kind(self.row(pool=10_000, **idle)), "ok")           # no pool to spend
        self.assertTrue(ai_probe_report.valid_x(self.row()))

    def test_the_report_leaves_them_out_and_check_counts_them(self):
        good = {"tag": "AAA", "id": 1, "k": 12, "y": 1840, "gdp": 1000, **self.row()}
        unpaid = {"tag": "BBB", "id": 2, "k": 12, "y": 1840, "gdp": 900,
                  **self.row(con_used_priv=1463.5, con_goods_priv=0)}
        lines = ai_probe_report.check_x_construction([good, unpaid])
        self.assertTrue(lines[0].startswith("X construction readings left out of the report's construction figures: "
                                            "1 unpaid"), lines)
        self.assertIn("BBB 1840 unpaid", lines[1])


if __name__ == "__main__":
    unittest.main()
