"""game_qa/script_docs.py and `Session.script_docs` (#1907): the mods-off engine-doc dump of a vanilla bump.

The module's checks run on temp folders. The session runs against `test_game_qa_session`'s fake game, whose
`script_docs` writes the six logs into the user-data folder's `docs/` and answers as the real game did on
2026-11-19 (`fakes.FakeHelper._script_docs`). The refusals the issue names: a stale log, the mod's marker in
`modifiers.log`, a version mismatch, an existing folder.
"""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from game_qa import console, fakes, script_docs, server, session
from game_qa.logtail import LogFollower
from test_game_qa_session import PERMISSION, RESTORED, SNAP, SessionTestCase

VERSION = "1.15.0"          # SessionTestCase's game_version


def write_dump(folder: Path, marker: bool = False, skip: tuple = ()) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name in script_docs.LOGS:
        if name in skip:
            continue
        text = "%s of vanilla\n" % name
        if name == "modifiers.log" and marker:
            text += "Tag: %s\n" % script_docs.MOD_MARKER
        (folder / name).write_text(text, encoding="utf-8")


class PlanTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "vic3-engine-docs"

    def test_the_default_folder_is_the_installed_version_under_the_root(self):
        self.assertEqual(script_docs.plan("1.15.2", None, None, root=self.root), self.root / "1.15.2" / "docs")
        self.assertEqual(script_docs.plan("1.15.2", "1.15.2", None, root=self.root), self.root / "1.15.2" / "docs")

    def test_a_version_that_is_not_the_installed_one_is_refused(self):
        with self.assertRaises(script_docs.DocsRefused) as caught:
            script_docs.plan("1.15.2", "1.15.3", None, root=self.root)
        self.assertEqual(caught.exception.code, "version_mismatch")
        self.assertIn("1.15.2", caught.exception.detail)

    def test_an_existing_folder_is_refused_unless_forced(self):
        (self.root / "1.15.2" / "docs").mkdir(parents=True)
        with self.assertRaises(script_docs.DocsRefused) as caught:
            script_docs.plan("1.15.2", None, None, root=self.root)
        self.assertEqual(caught.exception.code, "out_exists")
        self.assertEqual(script_docs.plan("1.15.2", None, None, force=True, root=self.root),
                         self.root / "1.15.2" / "docs")

    def test_an_out_folder_must_end_in_the_version(self):
        with self.assertRaises(script_docs.DocsRefused) as caught:
            script_docs.plan("1.15.2", None, self.root / "1.15.1" / "docs")
        self.assertEqual(caught.exception.code, "out_version")
        self.assertEqual(script_docs.plan("1.15.2", None, self.root / "hotfix-1.15.2"), self.root / "hotfix-1.15.2")

    def test_an_out_folder_inside_the_digests_clone_is_refused(self):
        digests = self.root.parent / "Modding-Digests"
        with self.assertRaises(script_docs.DocsRefused) as caught:
            script_docs.plan("1.15.2", None, digests / "1.15.2" / "docs", digests=digests)
        self.assertEqual(caught.exception.code, "inside_digests")

    def test_an_unreadable_installed_version_is_refused(self):
        with self.assertRaises(script_docs.DocsRefused) as caught:
            script_docs.plan("", None, None, root=self.root)
        self.assertEqual(caught.exception.code, "no_version")


class ChecksTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_a_vanilla_dump_passes(self):
        write_dump(self.dir / "docs")
        self.assertEqual(script_docs.check(self.dir / "docs")["mod_marker_absent"], script_docs.MOD_MARKER)

    def test_the_mods_marker_in_modifiers_log_is_refused(self):
        write_dump(self.dir / "docs", marker=True)
        with self.assertRaises(script_docs.DocsRefused) as caught:
            script_docs.check(self.dir / "docs")
        self.assertEqual(caught.exception.code, "mod_loaded")

    def test_the_marker_counts_only_as_a_whole_name(self):
        write_dump(self.dir / "docs")
        with open(self.dir / "docs" / "modifiers.log", "a", encoding="utf-8") as f:
            f.write("Tag: %s_mult\nTag: x%s\n" % (script_docs.MOD_MARKER, script_docs.MOD_MARKER))
        script_docs.check(self.dir / "docs")

    def test_a_missing_or_empty_log_is_refused(self):
        write_dump(self.dir / "a", skip=("on_actions.log",))
        with self.assertRaises(script_docs.DocsRefused) as caught:
            script_docs.check(self.dir / "a")
        self.assertEqual((caught.exception.code, caught.exception.info["files"]), ("missing", ["on_actions.log"]))
        write_dump(self.dir / "b")
        (self.dir / "b" / "triggers.log").write_bytes(b"")
        with self.assertRaises(script_docs.DocsRefused) as caught:
            script_docs.check(self.dir / "b")
        self.assertEqual(caught.exception.code, "empty")

    def test_a_log_counts_as_written_only_with_a_new_size_or_a_later_time(self):
        before = {name: (10, 1_000) for name in script_docs.LOGS}
        now = dict(before)
        now["effects.log"] = (10, 2_000)            # rewritten, same size
        now["triggers.log"] = (11, 1_000)           # a new size and the same time: not later, so not the run's
        now["modifiers.log"] = None                 # gone
        self.assertEqual(script_docs.unwritten(before, now),
                         ["triggers.log", "modifiers.log", "event_targets.log", "on_actions.log",
                          "custom_localization.log"])
        fresh = {name: (5, 3_000) for name in script_docs.LOGS}
        self.assertEqual(script_docs.unwritten({name: None for name in script_docs.LOGS}, fresh), [])

    def test_install_copies_by_a_temp_folder_and_replaces_only_when_forced(self):
        write_dump(self.dir / "staged")
        files = {name: {"sha256": script_docs.sha256(self.dir / "staged" / name)} for name in script_docs.LOGS}
        out = self.dir / "1.15.2" / "docs"
        script_docs.install(self.dir / "staged", out, files)
        self.assertEqual(sorted(p.name for p in out.iterdir()), sorted(script_docs.LOGS))
        self.assertEqual(sorted(p.name for p in out.parent.iterdir()), ["docs"])          # no temp left
        with self.assertRaises(script_docs.DocsRefused) as caught:
            script_docs.install(self.dir / "staged", out, files)
        self.assertEqual(caught.exception.code, "out_exists")
        (out / "stray.txt").write_text("from an earlier dump")
        script_docs.install(self.dir / "staged", out, files, force=True)
        self.assertEqual(sorted(p.name for p in out.iterdir()), sorted(script_docs.LOGS))
        self.assertEqual(sorted(p.name for p in out.parent.iterdir()), ["docs"])

    def test_the_previous_dump_is_the_newest_older_complete_one(self):
        root = self.dir / "root"
        for version in ("1.14.5", "1.15.0", "1.15.1", "1.15.3"):
            write_dump(root / version / "docs")
        write_dump(root / "1.15.1.9" / "docs")                      # not a version folder's name
        (root / "1.15.1" / "docs" / "effects.log").unlink()           # incomplete
        self.assertEqual(script_docs.previous(root, "1.15.2"), root / "1.15.0" / "docs")
        self.assertIsNone(script_docs.previous(root, "1.14.5"))
        steps = script_docs.next_steps(root / "1.15.2" / "docs", root / "1.15.0" / "docs")
        self.assertIn("vanilla_snapshot_docs_path", steps["pin"])
        self.assertIn("docs %s %s --mod-uses --show-changed" % (root / "1.15.0" / "docs", root / "1.15.2" / "docs"),
                      steps["diff"])


class SessionScriptDocsTest(SessionTestCase):
    """`Session.script_docs` against the fake game."""

    def setUp(self):
        super().setUp()
        self.root = self.paths.backup_root.parent / "vic3-engine-docs"
        self.paths.engine_docs_root = self.root
        self.paths.digests = self.paths.backup_root.parent / "Modding-Digests"
        self.docs = self.user / "docs"
        self.game.docs = self.docs
        # No save is loaded: the game sits at its main menu until the hands-off game has set itself up, SETUP_S
        # after the launch, and logged vanilla's setup lines (a party created), as on 2026-11-13.
        self.game.at_menu = True
        self.sets_up = True
        self.game.on_sleep = self.hands_off
        # The owner's last dump, written an hour ago: the run's must be newer.
        write_dump(self.docs, marker=True)
        hour_ago = time.time() - 3600
        for name in script_docs.LOGS:
            os.utime(self.docs / name, (hour_ago, hour_ago))
        write_dump(self.root / "1.14.5" / "docs")
        self.out = self.root / VERSION / "docs"

    SETUP_S = 20.0

    def hands_off(self, seconds):
        if not (self.sets_up and self.game.at_menu and "launch" in self.cli.clock_at and self.game.exists):
            return
        launched_at = self.cli.clock_at["launch"]
        if self.game.now + seconds >= launched_at + self.SETUP_S:
            self.game.at_menu = False
            with open(self.game.log, "a", encoding="utf-8") as f:
                f.write("[12:00:20][jomini_effect_impl.cpp:459]: common/on_actions/00_code_on_actions.txt:4298: "
                        "Tory Party Created - Great Britain\n")

    def take(self, **kwargs) -> dict:
        return self.session.script_docs(PERMISSION, **kwargs)

    def test_the_dump_is_taken_on_no_mod_at_the_main_menu_then_stopped_and_kept(self):
        reply = self.take()
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch", "restore"])
        self.assertEqual(self.cli.calls[1], ["snapshot"])
        self.assertEqual(self.cli.calls[2], ["launch", SNAP, "--permission", PERMISSION, "--playset", "none",
                                             "--", "-gdpr-compliant", "-debug_mode", "-no_crash_reporter",
                                             "-handsoff", "-run_until=1836.3.31"])
        # The console is probed with the log system's own command: the session's usual one crashes the menu. The
        # first probe goes out with the console still shut, the second once the console key has opened it.
        self.assertEqual(self.typed(), [console.MENU_PROBE_COMMAND, console.MENU_PROBE_COMMAND, "script_docs"])
        self.assertIsNone(self.game.crashed)
        self.assertNotIn("tcp_open 6111", self.order)               # no debugger
        self.assertFalse(self.paths.overlay_dir.exists())           # no overlay
        self.assertEqual(self.game.docs_runs, 1)
        self.assertEqual(reply["out"], str(self.out))
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), sorted(script_docs.LOGS))
        for name in script_docs.LOGS:
            self.assertEqual((self.out / name).read_bytes(), (self.docs / name).read_bytes())
            self.assertEqual(reply["files"][name]["sha256"], script_docs.sha256(self.out / name))
        self.assertEqual(reply["stop"]["outcome"], "restored")
        self.assertEqual(reply["previous"], str(self.root / "1.14.5" / "docs"))
        self.assertIn(str(self.out), reply["next"]["pin"])
        self.assertIn("vanilla_patch_diff.py docs", reply["next"]["diff"])
        run = Path(reply["run_dir"])
        self.assertEqual(sorted(p.name for p in (run / session.DOCS_STAGED).iterdir()), sorted(script_docs.LOGS))
        self.assertEqual(json.loads((run / session.DOCS_RECORD).read_text("utf-8"))["out"], str(self.out))
        self.assertEqual(self.session.stop(), reply["stop"])        # stopped once, for good

    def test_the_command_waits_for_the_game_state(self):
        # Live 2026-11-19: `script_docs` typed at the bare main menu crashed the game.
        self.SETUP_S = 200.0
        reply = self.take()
        self.assertIsNone(self.game.crashed)
        self.assertEqual(reply["stop"]["outcome"], "restored")
        steps = [json.loads(line) for line in (Path(reply["run_dir"]) / "steps.jsonl").read_text("utf-8").splitlines()]
        state = next(step for step in steps if step["verb"] == "game_state")
        self.assertIn("Party Created", state["line"])
        self.assertLess([step["verb"] for step in steps].index("game_state"),
                        [step["verb"] for step in steps].index("script_docs"))

    def test_no_game_state_is_refused_with_nothing_typed_but_the_probe(self):
        self.sets_up = False
        error = self.session_error(self.take)
        self.assertEqual(error.code, "no_game_state")
        self.assertEqual(error.info["stop"]["outcome"], "restored")
        self.assertNotIn("script_docs", self.typed())
        self.assertIsNone(self.game.crashed)
        self.assertFalse(self.out.exists())

    def test_a_dump_whose_command_is_already_in_the_history_is_still_taken(self):
        # The owner's history ends in `script_docs` after a hand-taken dump (2026-11-19), and a history that does not
        # write repeats shows nothing of a second one: the log's answer proves it instead.
        self.game.history_skips_repeats = True
        self.game.history.write_text("script_docs\n", encoding="utf-8")
        reply = self.take()
        self.assertEqual(reply["stop"]["outcome"], "restored")
        self.assertEqual(self.game.docs_runs, 1)
        self.assertIsNone(self.game.crashed)

    def test_a_version_mismatch_starts_nothing(self):
        error = self.session_error(self.take, version="1.15.3")
        self.assertEqual(error.code, "version_mismatch")
        self.assertEqual((self.cli.calls, self.game.launched), ([], []))
        self.assertFalse(self.out.exists())

    def test_an_existing_folder_starts_nothing_unless_forced(self):
        write_dump(self.out)
        error = self.session_error(self.take)
        self.assertEqual(error.code, "out_exists")
        self.assertEqual(self.cli.calls, [])

    def test_force_replaces_an_existing_folder(self):
        write_dump(self.out)
        (self.out / "stray.txt").write_text("from an earlier dump")
        reply = self.take(force=True)
        self.assertEqual(reply["stop"]["outcome"], "restored")
        self.assertEqual(sorted(p.name for p in self.out.iterdir()), sorted(script_docs.LOGS))

    def test_a_stale_log_is_refused_after_the_stop_and_nothing_is_kept(self):
        self.game.docs_skipped = {"on_actions.log"}
        error = self.session_error(self.take)
        self.assertEqual((error.code, error.info["files"]), ("stale_docs", ["on_actions.log"]))
        self.assertEqual(error.info["stop"]["outcome"], "restored")
        self.assertEqual(self.cli.verbs, ["held", "snapshot", "launch", "restore"])
        self.assertIn("kill", self.order)
        self.assertFalse(self.out.exists())
        record = json.loads((self.paths.run_root / SNAP / session.DOCS_RECORD).read_text("utf-8"))
        self.assertEqual(record["refused"], "stale_docs")

    def test_a_dump_with_the_mod_loaded_is_refused_and_nothing_is_kept(self):
        self.game.docs_logs = {"modifiers.log": ("Tag: %s\n" % script_docs.MOD_MARKER).encode()}
        error = self.session_error(self.take)
        self.assertEqual(error.code, "mod_loaded")
        self.assertEqual(error.info["stop"]["outcome"], "restored")
        self.assertFalse(self.out.exists())

    def test_a_command_that_writes_nothing_is_refused_stale(self):
        self.game.on("script_docs", failure=["Unknown command"])
        error = self.session_error(self.take)
        self.assertEqual((error.code, error.info["files"]), ("stale_docs", list(script_docs.LOGS)))
        self.assertEqual(error.info["stop"]["outcome"], "restored")
        self.assertFalse(self.out.exists())

    def test_a_crash_names_the_crash_folder_the_run_left(self):
        (self.user / "crashes" / "victoria3_older").mkdir(parents=True)

        def crash(text):
            if text == "script_docs":
                (self.user / "crashes" / "victoria3_01261019_111859").mkdir()
                self.game.exists, self.game.exited = False, True
        self.game.on_command = crash
        error = self.session_error(self.take)
        self.assertEqual(error.code, "watch_ended")              # seen while the logs were waited for
        self.assertEqual(error.info["crashes"], [str(self.user / "crashes" / "victoria3_01261019_111859")])
        self.assertEqual(error.info["stop"]["outcome"], "restored")
        self.assertFalse(self.out.exists())

    def test_a_folder_that_appears_during_the_run_keeps_the_staged_copy(self):
        def appear(argv):
            if argv[0] == "restore":
                write_dump(self.out)
        self.cli.on_call = appear
        error = self.session_error(self.take)
        self.assertEqual(error.code, "out_exists")
        self.assertEqual(error.info["stop"]["outcome"], "restored")
        staged = Path(error.info["staged"])
        self.assertEqual(sorted(p.name for p in staged.iterdir()), sorted(script_docs.LOGS))

    def test_a_held_stop_still_keeps_the_dump_and_says_so(self):
        self.cli.queue("restore", {"restored": [], "removed": [], "held": True, "reason": "other_game_ran"}, 2)
        reply = self.take()
        self.assertEqual(reply["stop"]["outcome"], "held")
        self.assertTrue(self.out.is_dir())
        self.assertFalse(server.clean_stop(reply["stop"]))

    def test_a_second_run_in_one_session_is_refused(self):
        self.take()
        self.assertEqual(self.session_error(self.take).code, "already_started")


class MenuProbeTest(unittest.TestCase):
    """The probe that opens the console at the main menu (live 2026-11-19: the session's own crashed the game)."""

    def console_on_the_menu(self, probe):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        user = Path(tmp.name)
        (user / "logs").mkdir()
        game = fakes.FakeHelper(history=user / "console_history.txt", log=user / "logs" / "debug.log")
        game.at_menu = True
        con = console.Console(game, game.proc, user / "console_history.txt", LogFollower(user / "logs" / "debug.log"),
                              sleep=game.sleep, clock=game.clock, **({"probe": probe} if probe else {}))
        return game, con

    def test_the_usual_probe_crashes_a_game_at_its_menu(self):
        # As live: the history took the probe before the game ran it and crashed, so the console seemed open, and
        # the next command found the window gone.
        game, con = self.console_on_the_menu(None)
        con.ensure_open()
        self.assertEqual((game.crashed, game.exists), (console.PROBE_COMMAND, False))
        with self.assertRaises(console.ConsoleError) as caught:
            con.run("script_docs", reply=False)
        self.assertEqual(caught.exception.code, "game_gone")

    def test_the_menu_probe_opens_the_console_there(self):
        game, con = self.console_on_the_menu(console.MENU_PROBE_COMMAND)
        con.ensure_open()
        self.assertTrue(game.console_open)
        self.assertIsNone(game.crashed)
        self.assertNotIn(console.PROBE_COMMAND, [step.get("text") for step in game.steps])


class ServerVerbTest(unittest.TestCase):
    def test_the_server_runs_script_docs_once_and_stops_after(self):
        calls = []

        class Fake:
            def script_docs(self, **kwargs):
                calls.append(kwargs)
                return {"out": "/x/1.15.2/docs"}

            def stop(self):
                calls.append("stop")
                return dict(RESTORED[0], outcome="restored", snapshot=SNAP)

        with tempfile.TemporaryDirectory() as tmp:
            srv = server.SessionServer(Fake(), Path(tmp))
            reply, code = srv.handle("script-docs", {"permission": PERMISSION, "force": False})
            self.assertEqual((code, reply["out"], reply["stop"]["outcome"]), (0, "/x/1.15.2/docs", "restored"))
            self.assertEqual(calls, [{"permission": PERMISSION, "force": False}, "stop"])
            again, code = srv.handle("script-docs", {"permission": PERMISSION})
            self.assertEqual((code, again["refused"]), (2, "session_running"))
            bad, code = server.SessionServer(Fake(), Path(tmp)).handle("script-docs", {"until": "1900"})
            self.assertEqual((code, bad["refused"]), (2, "bad_argument"))


if __name__ == "__main__":
    unittest.main()
