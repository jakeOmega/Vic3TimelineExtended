"""scripts/analysis/log_triage.py: the snapshot and the report.

Each test builds a small logs folder, a registry and a mod tree in a temp
directory, so nothing here reads the game, the server or this checkout's
registries.
"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "scripts", "analysis"))

import game_log_reader as glr  # noqa: E402
import log_triage  # noqa: E402

DAY = dt.datetime(2026, 11, 9)

SCRIPT_ERROR = (
    "[{t}][jomini_script_system.cpp:247]: Script system error!\n"
    "  Error: {error}\n"
    "  Script location: {where}\n\n"
)

REGISTRY = """## Script errors observed

### `common/on_actions/00_code_on_actions.txt` — a vanilla on_action reads an unset scope

```
Event target link 'capital' returned an unset scope
```

### `gui/right_click_menu.gui` — vanilla's header, carried in the mod's override
{reviewed}
```
Property 'margin_top'(816) not handled
```

## Engine noise (source-anchored)

### `pdx_assert.cpp:637` — dead formation
- source: `pdx_assert.cpp:637`

```
Trying to reposition a dead formation
```

## Watch list (tagged, never hidden)

### `pdx_assert.cpp:641` — occupation data removed with a state
- source: `pdx_assert.cpp:641`
- check: read the same second for a mod effect that moves land

```
Trying to remove occupation data
```
"""


def at(hms: str, day: dt.datetime = DAY) -> float:
    return dt.datetime.combine(day.date(), dt.time.fromisoformat(hms)).timestamp()


class Fixture:
    """A logs folder, a docs root and a mod root under one temp directory."""

    def __init__(self, tmp: str, reviewed: str = ""):
        self.logs = os.path.join(tmp, "logs")
        self.docs = os.path.join(tmp, "repo")
        self.mod = os.path.join(tmp, "mod")
        self.snap = os.path.join(tmp, "snap")
        os.makedirs(self.logs)
        self.write_doc("docs/vanilla/vanilla_known_bugs.md", REGISTRY.format(reviewed=reviewed))
        self.write_doc("docs/audits/mod_known_noise.md", "## Entries\n")
        self.write_doc("docs/audits/open_issues.md", "")
        self.write_doc("docs/testing/strait-playtest.md", "| `TE_SELF_CHECK OK|BROKEN te_seize_strait` |\n")
        for rel in ("common/scripted_effects/te_x.txt", "gui/right_click_menu.gui",
                    "localization/english/x_l_english.yml"):
            path = os.path.join(self.mod, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").close()
        glr._vanilla_bug_cache.clear()

    def write_doc(self, rel: str, text: str) -> None:
        path = os.path.join(self.docs, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def log(self, name: str, text: str, written: str, day: dt.datetime = DAY) -> None:
        """Write logs/<name>, last written at `written` (HH:MM:SS) of `day`."""
        path = os.path.join(self.logs, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.utime(path, (at(written, day), at(written, day)))

    def standard(self) -> None:
        """Two launches: 10:00 (its debug.log start rotated out) and 12:00."""
        self.log("system.1.log", "[10:00:00][game_setup.cpp:225]: Exe Git Version: release/1.15.0 : abc\n", "10:00:05")
        self.log("system.log", "[12:00:00][game_setup.cpp:225]: Exe Git Version: release/1.15.0 : abc\n", "12:00:05")
        self.log("dedicated_server.log", "".join([
            "[12:01:00][jominiapplication.cpp:539]: Pause Toggled! Paused: false, PlayerID: 0\n",
            "[12:01:01][jominiapplication.cpp:539]: Processing Tick: 1869.8.11\n",
            "[12:05:00][jominiapplication.cpp:539]: Processing Tick: 1870.1.1.6\n",
            "[12:06:00][jominiapplication.cpp:539]: Pause Toggled! Paused: true, PlayerID: 0\n",
        ]), "12:06:00")
        self.log("debug.1.log", "".join([
            "[10:30:00][pdx_assert.cpp:637]: Assertion failed: Trying to reposition a dead formation\n",
            "[10:30:01][jomini_effect_impl.cpp:459]: common/scripted_effects/te_x.txt:5: TE_SELF_CHECK START te_late\n",
        ]), "10:31:00")
        self.log("debug.log", "".join([
            "[12:00:01][dlc.cpp:748]: Mod Vic3TimelineExtended () version 1.15.0 successfully matched game version 1.15.0.\n",
            "[12:05:00][jomini_effect_impl.cpp:459]: common/scripted_effects/te_x.txt:9: TE_SELF_CHECK OK te_seize_strait shores=0->1\n",
            "[12:05:00][jomini_effect_impl.cpp:459]: common/scripted_effects/te_x.txt:3: TE_CIVIL_WAR: France faces an uprising\n",
            "[12:05:00][pdx_assert.cpp:641]: Assertion failed: Trying to remove occupation data without returning it\n",
            "[12:05:30][pdx_data_localize.cpp:136]: Data error in loc string 'TE_SELF_CHECK INFO te_lost [THIS.GetName]'\n",
            "[12:05:40][pdx_assert.cpp:650]: Assertion failed: Trying to reposition a dead formation\n",
            "[12:05:41][pdx_assert.cpp:650]: Assertion failed: something else entirely\n",
        ]), "12:06:00")
        self.log("error.log", "".join([
            SCRIPT_ERROR.format(t="12:05:10", error="Variable 'st_1' is not set",
                                where="common/scripted_effects/te_x.txt:45"),
            SCRIPT_ERROR.format(t="12:05:10", error="Variable 'st_1' is not set",
                                where="common/scripted_effects/te_x.txt:99"),
            SCRIPT_ERROR.format(t="12:05:11", error="Variable 'st_2' is not set",
                                where="common/scripted_effects/te_x.txt:45"),
            SCRIPT_ERROR.format(t="12:05:12", error="Event target link 'capital' returned an unset scope",
                                where="common/on_actions/00_code_on_actions.txt:7"),
            SCRIPT_ERROR.format(t="12:05:13", error="Div/0", where="common/scripted_effects/statistics_effects.txt:3"),
            "[12:05:14][pdx_gui_widget.cpp:2295]: gui/right_click_menu.gui:16933 - Property 'margin_top'(816) not handled\n",
        ]), "12:06:00")
        self.log("game.log", "".join([
            "[12:00:40][jomini_eventmanager.cpp:590]: Events loaded events/1848.txt' #9\n",
            # error.log has rotated this one away (it starts at 12:05:10):
            SCRIPT_ERROR.format(t="12:02:00", error="Variable 'st_1' is not set",
                                where="common/scripted_effects/te_x.txt:45"),
            # ... and still holds this one:
            SCRIPT_ERROR.format(t="12:05:10", error="Variable 'st_1' is not set",
                                where="common/scripted_effects/te_x.txt:45"),
        ]), "12:06:00")
        self.log("gui.log", "[12:00:30][pdx_gui_layout.cpp:186]: gui/te_new.gui:162 - Widget cannot have a position in a layout\n",
                 "12:00:30")
        self.log("debug-OtherPC.log", "[09:00:00][pdx_assert.cpp:1]: another machine's log\n", "09:00:00")
        self.log("ai.log", "", "12:00:00")

    def report(self, **kwargs) -> str:
        log_triage.snapshot(self.logs, self.snap, now=dt.datetime.fromtimestamp(at("13:00:00")))
        return log_triage.report(self.snap, docs_root=self.docs, mod_root=self.mod, git_ref=None, **kwargs)


def section(report: str, title: str) -> str:
    start = report.index(f"== {title}")
    end = report.find("\n== ", start + 1)
    return report[start:end if end != -1 else len(report)]


class SnapshotTests(unittest.TestCase):
    def test_copies_the_triage_families_by_exact_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.standard()
            manifest = log_triage.snapshot(fx.logs, fx.snap, now=dt.datetime.fromtimestamp(at("13:00:00")))
            self.assertEqual(sorted(manifest["files"]), [
                "debug.1.log", "debug.log", "dedicated_server.log", "error.log", "game.log", "gui.log",
                "system.1.log", "system.log"])
            self.assertFalse(os.path.exists(os.path.join(fx.snap, "debug-OtherPC.log")))
            self.assertFalse(manifest["game_running"])
            # mtimes survive the copy: every date in the report is worked back from them.
            self.assertEqual(os.path.getmtime(os.path.join(fx.snap, "debug.1.log")), at("10:31:00"))
            with open(os.path.join(fx.snap, log_triage.MANIFEST), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["files"], manifest["files"])

    def test_a_log_written_in_the_last_minute_means_the_game_is_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.standard()
            manifest = log_triage.snapshot(fx.logs, fx.snap, now=dt.datetime.fromtimestamp(at("12:06:20")))
            self.assertTrue(manifest["game_running"])

    def test_crash_folders_are_listed_with_their_fault_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.standard()
            crash = os.path.join(tmp, "crashes", "victoria3_01261009_120700")
            os.makedirs(crash)
            with open(os.path.join(crash, "exception.txt"), "w", encoding="utf-8") as fh:
                fh.write("Unhandled Exception C0000005 at address 0x00007FF61EDB42A6\n")
            os.utime(crash, (at("12:07:00"), at("12:07:00")))
            report = fx.report()
            self.assertIn("victoria3_01261009_120700 at 0x00007FF61EDB42A6", section(report, "Crashes"))


class StampTests(unittest.TestCase):
    def test_dates_are_worked_back_from_the_mtime_across_midnight(self):
        entries = [glr.LogEntry(t, "x.cpp:1", "m") for t in ("23:59:58", "23:59:59", "00:00:01", "00:30:00")]
        stamps = log_triage.stamp(entries, at("00:30:00"))
        self.assertEqual([s.day for s in stamps], [8, 8, 9, 9])
        self.assertEqual(stamps[-1], dt.datetime(2026, 11, 9, 0, 30))

    def test_an_untimed_line_takes_the_time_before_it(self):
        entries = [glr.LogEntry("10:00:00", "x.cpp:1", "m"), glr.LogEntry("", "", "header")]
        stamps = log_triage.stamp(entries, at("10:00:00"))
        self.assertEqual(stamps[1], stamps[0])


class ReportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.fx = Fixture(self._tmp.name)
        self.fx.standard()
        self.report = self.fx.report()

    def test_launches_say_what_each_family_still_holds(self):
        launches = section(self.report, "Launches")
        self.assertIn("#1 2026-11-09 10:00:00", launches)
        self.assertIn("#2 2026-11-09 12:00:00  release/1.15.0  loaded a save, 1869.8.11 to 1870.1.1", launches)
        # Launch 1's debug.log begins half an hour in; launch 2's is whole and names the playset.
        self.assertIn("debug.log from 10:30:00", launches)
        self.assertIn("debug.log whole, error.log from 12:05:10, game.log whole; playset: Vic3TimelineExtended",
                      launches)

    def test_untagged_groups_by_exact_message_and_keeps_every_site(self):
        untagged = section(self.report, "Untagged")
        # st_1 and st_2 stay two findings (no digit folding), and st_1's two lines of the file are both named.
        self.assertIn("Error: Variable 'st_1' is not set", untagged)
        self.assertIn("Error: Variable 'st_2' is not set", untagged)
        self.assertIn("lines of common/scripted_effects/te_x.txt: 45 x2, 99", untagged)
        # error 2 + the one game.log line error.log no longer holds; the 12:05:10 copy is not counted twice.
        self.assertIn("3 lines (error 2, game 1); MOD FILE in the stack", untagged)
        self.assertIn("game date 1869.8.11 to 1870.1.1", untagged)

    def test_what_triage_never_judges_is_left_out(self):
        untagged = section(self.report, "Untagged")
        self.assertNotIn("Events loaded", untagged)            # game.log's own trace
        self.assertNotIn("statistics_effects", untagged)       # a third-party mod
        self.assertNotIn("TE_CIVIL_WAR", untagged.split("near:")[0])  # debug_log output is no finding
        self.assertNotIn("returned an unset scope", untagged)  # registered vanilla
        self.assertNotIn("another machine", self.report)

    def test_gui_log_meets_the_registries(self):
        untagged = section(self.report, "Untagged")
        self.assertIn("gui/te_new.gui:N - Widget cannot have a position in a layout", untagged)
        self.assertIn("1 lines (gui 1)", untagged)

    def test_a_watched_line_is_shown_with_its_check_and_its_neighbours(self):
        watch = section(self.report, "Watch list")
        self.assertIn("Trying to remove occupation data", watch)
        self.assertIn("check: read the same second for a mod effect that moves land", watch)
        self.assertIn("near: 12:05:00 debug.log: common/scripted_effects/te_x.txt:3: TE_CIVIL_WAR: France faces",
                      watch)
        self.assertNotIn("Trying to remove occupation data", section(self.report, "Untagged"))

    def test_a_mod_frame_under_a_vanilla_entry_is_flagged_until_reviewed(self):
        hidden = section(self.report, "Hidden by a vanilla entry")
        self.assertIn("1 lines: vanilla's header, carried in the mod's override  <-- NOT REVIEWED", hidden)
        self.assertIn("via gui/right_click_menu.gui", hidden)
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp, reviewed="- reviewed: mod frame, the override keeps vanilla's block\n")
            fx.standard()
            hidden = section(fx.report(), "Hidden by a vanilla entry")
            self.assertIn("(reviewed: mod frame, the override keeps vanilla's block)", hidden)
            self.assertNotIn("NOT REVIEWED", hidden)

    def test_drift_is_a_registered_signature_at_an_unregistered_line(self):
        registry = section(self.report, "Registry")
        self.assertIn("DRIFT pdx_assert.cpp:650: 1 lines carry the signature of 'dead formation'", registry)
        self.assertEqual(registry.count("DRIFT"), 1)  # "something else entirely" at :650 is no drift
        self.assertIn("something else entirely", section(self.report, "Untagged"))

    def test_self_checks_by_name_with_their_play_test_list(self):
        checks = section(self.report, "Self-checks")
        self.assertIn("te_seize_strait: OK", checks)
        self.assertIn("launch #2, 12:05:00, game date 1870.1.1; listed in docs/testing/strait-playtest.md", checks)
        self.assertIn("te_late: START  <-- START with no verdict", checks)
        self.assertIn("in no play-test list", checks)
        self.assertIn("LOST TE_SELF_CHECK INFO te_lost", checks)
        self.assertIn("other trace lines: TE_CIVIL_WAR 1", checks)

    def test_volume_counts_hidden_lines_too(self):
        volume = section(self.report, "Volume")
        self.assertIn("[vanilla_noise] dead formation", volume)
        self.assertIn("[untagged] Variable 'st_1' is not set", volume)


class ModGuiUntagTests(unittest.TestCase):
    """#1269: a mod GUI's data-context failure names no file, and three
    source-only vanilla entries match its lines. The report lists the lines a
    mod-owned .gui reaches and leaves vanilla's own hidden."""

    ENTRIES = """
### `pdx_data_callstack.cpp:16` — vanilla data context not supplied
- source: `pdx_data_callstack.cpp:16`

```
No context supplied (Use SetDataContext), wanted context of type
```

### `pdx_data_localize_helper.cpp:286` — vanilla FetchData cascade
- source: `pdx_data_localize_helper.cpp:286`

```
FetchData failed for
```

### `pdx_gui_localize.cpp:140` — vanilla GUI loc fetch failure
- source: `pdx_gui_localize.cpp:140`

```
PdxDataFetchLocalizedData failed for
```
"""
    FLOOD = (
        "[12:05:2{n}][pdx_data_callstack.cpp:16]: No context supplied (Use SetDataContext), "
        "wanted context of type '{type}' for '{type}.{get} '\n"
        "[12:05:2{n}][pdx_data_localize_helper.cpp:286]: FetchData failed for '{type}.{get}'\n"
        "[12:05:2{n}][pdx_gui_localize.cpp:140]: PdxDataFetchLocalizedData failed for '{key}'\n"
    )

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.fx = fx = Fixture(self._tmp.name)
        fx.write_doc("docs/vanilla/vanilla_known_bugs.md",
                     REGISTRY.format(reviewed="").replace("## Watch list", self.ENTRIES + "\n## Watch list"))
        glr._vanilla_bug_cache.clear()
        fx.standard()
        # The mod's own widget draws a key of its own that reads a panel only
        # another window has; right_click_menu.gui replaces vanilla's file.
        with open(os.path.join(fx.mod, "gui", "te_census_widgets.gui"), "w", encoding="utf-8-sig") as fh:
            fh.write('textbox = { text = "te_census_income" }\n')
        with open(os.path.join(fx.mod, "gui", "right_click_menu.gui"), "w", encoding="utf-8-sig") as fh:
            fh.write('textbox = { text = "[DiscriminationTraitGroup.GetName]" }\n')
        with open(os.path.join(fx.mod, "localization", "english", "x_l_english.yml"), "w",
                  encoding="utf-8-sig") as fh:
            fh.write('l_english:\n te_census_income:0 "[PopsOverviewPanel.GetAverageIncomeRich|v1] Income"\n')
        self.vanilla_game = os.path.join(self._tmp.name, "install", "game")
        os.makedirs(os.path.join(self.vanilla_game, "gui"))
        open(os.path.join(self.vanilla_game, "gui", "right_click_menu.gui"), "w").close()
        fx.log("debug.log", "".join([
            self.FLOOD.format(n=1, type="PopsOverviewPanel", get="GetAverageIncomeRich", key="te_census_income") * 3,
            self.FLOOD.format(n=2, type="DiscriminationTraitGroup", get="GetName",
                              key="INCORPORATION_TIME_SAME_TRAIT_GROUP"),
        ]), "12:06:00")

    def test_the_mods_lines_are_findings_that_name_the_gui_file(self):
        report = self.fx.report(vanilla_game=self.vanilla_game)
        untagged = section(report, "Untagged")
        for source, text, note in (
            ("pdx_data_callstack.cpp:16", "wanted context of type 'PopsOverviewPanel'",
             "data type 'PopsOverviewPanel' is read by"),
            ("pdx_data_localize_helper.cpp:286", "FetchData failed for 'PopsOverviewPanel.GetAverageIncomeRich'",
             "data type 'PopsOverviewPanel' is read by"),
            ("pdx_gui_localize.cpp:140", "PdxDataFetchLocalizedData failed for 'te_census_income'",
             "loc key 'te_census_income' is drawn by"),
        ):
            self.assertEqual(untagged.count(f"  [{source}]"), 1)  # one finding: vanilla's own is not listed
            start = untagged.index(f"  [{source}]")
            finding = untagged[untagged.rindex("\n[", 0, start):untagged.find("\n[", start)]
            self.assertIn("3 lines (debug 3); no file named", finding)
            self.assertIn(text, finding.split("near:")[0])
            self.assertIn(f"MOD GUI: {note} gui/te_census_widgets.gui", finding)
        self.assertIn("otherwise hidden by 'vanilla GUI loc fetch failure'", untagged)
        # Vanilla's own flood stays under its entries, and is still counted.
        self.assertEqual(untagged.count("MOD GUI:"), 3)
        self.assertIn("[vanilla_noise] vanilla GUI loc fetch failure", section(report, "Volume"))
        self.assertNotIn("mod GUI untagging", report)

    def test_without_the_install_only_the_mods_own_key_shows_and_the_registry_section_says_why(self):
        report = self.fx.report()
        untagged = section(report, "Untagged")
        # A key vanilla's loc lacks is the mod's with no install to consult ...
        self.assertIn("MOD GUI: loc key 'te_census_income' is drawn by gui/te_census_widgets.gui", untagged)
        # ... but no file can be called the mod's own, so no data type is.
        self.assertEqual(untagged.count("MOD GUI:"), 1)
        self.assertNotIn("  [pdx_data_callstack.cpp:16]", untagged)
        self.assertIn("mod GUI untagging is limited to keys only the mod's loc defines: no vanilla GUI folder",
                      section(report, "Registry"))

    def test_a_key_no_gui_names_is_listed_with_the_loc_file_that_defines_it(self):
        note = log_triage.mod_gui_note({"key": "te_event_desc", "files": ["localization/english/te_l_english.yml"],
                                        "file_count": 1, "untagged_from": "vanilla GUI loc fetch failure"})
        self.assertEqual(note, "MOD GUI: loc key 'te_event_desc' is the mod's own "
                               "(localization/english/te_l_english.yml); no .gui names it; "
                               "otherwise hidden by 'vanilla GUI loc fetch failure'")
        note = log_triage.mod_gui_note({"type": "Country", "files": ["gui/a.gui", "gui/b.gui"], "file_count": 7,
                                        "untagged_from": "x"})
        self.assertEqual(note, "MOD GUI: data type 'Country' is read by gui/a.gui, gui/b.gui and 5 more; "
                               "otherwise hidden by 'x'")
        note = log_triage.mod_gui_note({"expression": "GetPlayer.GetFoo", "files": ["gui/a.gui"], "file_count": 1,
                                        "untagged_from": "x"})
        self.assertEqual(note, "MOD GUI: expression 'GetPlayer.GetFoo' is written in gui/a.gui; "
                               "otherwise hidden by 'x'")


class PauseTests(unittest.TestCase):
    def test_a_burst_while_paused_is_called_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            fx.standard()
            burst = "".join(SCRIPT_ERROR.format(t="12:06:%02d" % (10 + i // 10),
                                                error="Variable 'tip' is not set",
                                                where="common/scripted_effects/te_x.txt:7")
                            for i in range(40))
            fx.log("error.log", burst, "12:06:14")
            untagged = section(fx.report(), "Untagged")
            self.assertIn("a burst, 13 lines a second", untagged)
            self.assertIn("40 of 40 while paused", untagged)


class OccasionTests(unittest.TestCase):
    def test_times_split_at_a_gap(self):
        t = [DAY + dt.timedelta(seconds=s) for s in (0, 5, 50, 200, 210)]
        self.assertEqual([len(o) for o in log_triage.occasions(t)], [3, 2])


if __name__ == "__main__":
    unittest.main()
