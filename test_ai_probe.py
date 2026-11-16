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
                        "1e. Where the government's money goes",
                        "2. Technology", "2a. Specific technologies", "3. Laws", "3a. Law starts per idle month",
                        "3b. How enactments ended", "3c. The old law kept", "3d. Institutions", "4. Military",
                        "4a. The army by unit type", "5. Expansion", "5a. Diplomatic plays by type",
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

    def test_the_report_renders_it(self):
        out = ai_probe_report.report(self.parsed, self.key)
        self.assertIn("## 1. Economic growth", out)
        self.assertIn("Not logged by this log's probe version", out)
        self.assertIn("## 3a. Law starts per idle month", out)
        self.assertNotIn("## 4a.", out)                               # no unit line in version 1


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
        for (fixed, price), share, (reserves, debt), bureaucracy, paused, war, bubble, (queued, weekly), admin in \
                itertools.product(((857.0, 1249.0), (75817.0, 1256.0)), (-0.25, 0.03, 0.33),
                                  ((0.0, 0.0), (0.04, 0.0), (0.6, 0.0), (0.0, 0.3), (0.0, 0.45)), (50.0, -5.0),
                                  (False, True), (False, True), (None, 60.0), ((0, 20.0), (1, 10.0), (3, 140.0)),
                                  (0, 1)):
            c = purchase.Country(fixed, share * fixed, price, reserves, debt, bureaucracy, queued, weekly,
                                 paused=paused, at_war=war, bubble=bubble)
            record = {"cm_price": price, "fixed_income": fixed, "net_fixed": share * fixed, "gold_scaled": reserves,
                      "debt_scaled": debt, "queue_gov": queued, "cm_level_max": weekly, "paused": int(paused),
                      "war": int(war), "bubble": bubble or 0, "bur": bureaucracy, "cm_admin": admin}
            count += 1
            with self.subTest(record=record):
                self.assertAlmostEqual(ai_probe_report.purchase_target(record), c.script(), delta=purchase.STEP)
        self.assertGreater(count, 1000)
        self.assertIsNone(ai_probe_report.purchase_target({"cm_price": 1000}))     # version 1: a term missing


if __name__ == "__main__":
    unittest.main()
