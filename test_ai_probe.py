"""The AI telemetry probe (TEMPORARY, 2026-11-15): scripts/generators/gen_ai_probe.py and its four script files.

The probe cannot be run offline, and a `debug_log` line the engine cannot render is dropped without a word, so
these tests hold the parts that can be held: the generated files agree with each other and with the key the parser
reads, every hook sits behind the probe's latch, every counter is declared and reset, and the parser reads back
what the templates would print.

The files are NOT held to the mod's current laws and technologies: the generator is run before a probe run, not on
every change (docs/testing/ai-probe-runbook.md).
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
        self.assertEqual(whats, {"start", "pass", "fail", "end"})
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
                whats = ("start", "pass", "fail", "end")
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
        self.assertEqual(parsed.ticks[24]["y"], 7)

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
        for heading in ("1. Economic growth", "1b. Solvency", "1c. Staffing", "1d. The government's purchase", "1e. Where the government's money goes",
                        "2. Technology", "3. Laws", "4. Military", "5. Expansion"):
            self.assertIn(heading, out)


if __name__ == "__main__":
    unittest.main()
