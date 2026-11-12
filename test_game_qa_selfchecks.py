"""game_qa/selfchecks.py: the mod's TE_SELF_CHECK lines, kept with the fixture and reported for a run (#1601).

Everything is files in a temp folder. The lines are the ones the game logged on 2026-11-11, committed under
`docs/testing/game_qa_probe/captures/session_2026-11-11_playtest_rows/` without the log's own prefix, which
`logged` puts back.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game_qa import __main__ as cli
from game_qa import client, logtail, selfchecks, server, snapshot

CAPTURES = Path(__file__).resolve().parent / "docs/testing/game_qa_probe/captures/session_2026-11-11_playtest_rows"
RUN = "20261111T182536Z"
FIXTURE_RUN = "20261111T103846Z"
KEY = "81677a2162d5"
SAVE = "te_qa_fixture_" + KEY
NOISE = "[18:26:00][console.cpp:1175]: Running console command: event te_qa.1"


def captured(name: str) -> list[str]:
    return (CAPTURES / name).read_text("utf-8").splitlines()


def logged(lines) -> list[str]:
    """The lines as debug.log holds them."""
    return ["[18:27:%02d][jomini_effect_impl.cpp:459]: %s" % (n % 60, line) for n, line in enumerate(lines)]


def write_log(path: Path, lines) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes("".join(line + "\n" for line in lines).encode("utf-8"))


class SelfCheckTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.user = base / "user data"
        (self.user / "save games").mkdir(parents=True)
        (self.user / "logs").mkdir()
        self.backups = base / "backups"
        self.backups.mkdir()

    def fixture_run(self, lines, owners_log=("an earlier game of the owner's",)) -> str:
        """A snapshot of the user-data folder, then the run's logs as its restore leaves them in `run_logs/`:
        an older generation holding the owner's last log (`debug.1.log`), and the run's own `debug.log`."""
        write_log(self.user / "logs" / "debug.log", owners_log)
        snap = snapshot.take(self.user, self.backups)
        run_logs = snap.dir / "run_logs"
        write_log(run_logs / "debug.1.log", owners_log)
        write_log(run_logs / "debug.log", lines)
        return snap.id

    def run_folder(self, run_id=RUN, fixture=("found", SAVE), log=None) -> Path:
        folder = self.backups / "runs" / run_id
        folder.mkdir(parents=True)
        steps = [{"time": "2026-11-11T18:25:28Z", "verb": "held", "outcome": "none"}]
        if fixture is not None:
            steps.append({"time": "2026-11-11T18:25:15Z", "verb": "fixture", "outcome": fixture[0], "save": fixture[1]})
        (folder / "steps.jsonl").write_text("".join(json.dumps(step) + "\n" for step in steps), encoding="utf-8")
        if log is not None:
            write_log(folder / "debug.log", log)
        return folder

    def save(self, key=KEY) -> Path:
        path = self.user / "save games" / ("te_qa_fixture_%s.v3" % key)
        path.write_bytes(b"a fresh game")
        return path


class KeepTest(SelfCheckTestCase):
    def test_the_fixture_runs_lines_are_kept_under_the_backup_root(self):
        lines = logged(captured("fixture_run_self_checks_and_monuments.txt"))
        snap = self.fixture_run([NOISE, *lines[:60], NOISE, NOISE, *lines[60:]])
        before = sorted(p.relative_to(self.user).as_posix() for p in self.user.rglob("*"))
        record = selfchecks.keep_fixture_lines(self.backups, KEY, snap)
        folder = self.backups / "fixtures" / KEY
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["lines.log", "record.json"])
        self.assertEqual((folder / "lines.log").read_text("utf-8").splitlines(), lines)
        self.assertEqual(json.loads((folder / "record.json").read_text("utf-8")), record)
        self.assertEqual((record["key"], record["save"], record["snapshot"]), (KEY, SAVE, snap))
        self.assertEqual((record["lines"], record["self_checks"]), (114, 11))        # and 103 TE_MONUMENTS lines
        # nothing in the game's folder was written
        self.assertEqual(sorted(p.relative_to(self.user).as_posix() for p in self.user.rglob("*")), before)

    def test_a_generation_that_is_the_owners_earlier_game_is_not_the_runs(self):
        # An older generation the run did not push out (here: the owner's last log, renamed): bytes the snapshot has.
        owners = logged(["common/x.txt:1: TE_SELF_CHECK BROKEN from_the_owners_own_game"])
        snap = self.fixture_run(logged(["common/x.txt:2: TE_SELF_CHECK OK the_runs"]), owners_log=owners)
        record = selfchecks.keep_fixture_lines(self.backups, KEY, snap)
        self.assertEqual((record["read"], record["skipped"]), (["debug.log"], ["debug.1.log"]))
        kept = (self.backups / "fixtures" / KEY / "lines.log").read_text("utf-8")
        self.assertIn("the_runs", kept)
        self.assertNotIn("from_the_owners_own_game", kept)

    def test_a_generation_the_run_itself_rotated_is_read_oldest_first(self):
        snap = self.fixture_run(logged(["common/x.txt:2: TE_SELF_CHECK OK second"]))
        run_logs = self.backups / "snapshots" / snap / "run_logs"
        write_log(run_logs / "debug.2.log", logged(["common/x.txt:1: TE_SELF_CHECK OK first"]))
        record = selfchecks.keep_fixture_lines(self.backups, KEY, snap)
        self.assertEqual(record["read"], ["debug.2.log", "debug.log"])
        kept = (self.backups / "fixtures" / KEY / "lines.log").read_text("utf-8").splitlines()
        self.assertEqual([line.rsplit(" ", 1)[1] for line in kept], ["first", "second"])

    def test_without_the_snapshots_manifest_only_the_live_log_is_read(self):
        snap = self.fixture_run(logged(["common/x.txt:2: TE_SELF_CHECK OK the_runs"]),
                                owners_log=logged(["common/x.txt:1: TE_SELF_CHECK BROKEN the_owners"]))
        (self.backups / "snapshots" / snap / snapshot.MANIFEST_NAME).unlink()
        record = selfchecks.keep_fixture_lines(self.backups, KEY, snap)
        self.assertEqual((record["read"], record["skipped"], record["self_checks"]), (["debug.log"], ["debug.1.log"], 1))

    def test_a_run_that_left_no_log_keeps_nothing(self):
        snap = snapshot.take(self.user, self.backups).id
        with self.assertRaises(selfchecks.SelfCheckError) as caught:
            selfchecks.keep_fixture_lines(self.backups, KEY, snap)
        self.assertEqual(caught.exception.code, "no_run_log")
        self.assertFalse((self.backups / "fixtures").exists())

    def test_a_key_or_an_id_that_is_no_name_is_refused(self):
        snap = self.fixture_run(logged(["common/x.txt:2: TE_SELF_CHECK OK a"]))
        for key in ("../escape", "", "a/b", None):
            with self.subTest(key=key), self.assertRaises(ValueError):
                selfchecks.keep_fixture_lines(self.backups, key, snap)
        with self.assertRaises(selfchecks.SelfCheckError):
            selfchecks.keep_fixture_lines(self.backups, KEY, "../" + snap)
        self.assertFalse((self.backups / "fixtures").exists())

    def test_a_fixture_made_again_under_its_key_replaces_the_lines(self):
        first = self.fixture_run(logged(["common/x.txt:2: TE_SELF_CHECK OK first_run"]))
        selfchecks.keep_fixture_lines(self.backups, KEY, first)
        second = self.fixture_run(logged(["common/x.txt:2: TE_SELF_CHECK OK second_run"]), owners_log=("another",))
        selfchecks.keep_fixture_lines(self.backups, KEY, second)
        kept = (self.backups / "fixtures" / KEY / "lines.log").read_text("utf-8")
        self.assertIn("second_run", kept)
        self.assertNotIn("first_run", kept)
        self.assertEqual(selfchecks.fixture_record(self.backups, KEY)["snapshot"], second)


class DropTest(SelfCheckTestCase):
    def keep(self, key) -> Path:
        snap = self.fixture_run(logged(["common/x.txt:2: TE_SELF_CHECK OK a"]), owners_log=("owner " + key,))
        selfchecks.keep_fixture_lines(self.backups, key, snap)
        return self.backups / "fixtures" / key

    def test_the_lines_go_once_their_fixture_has_gone_and_no_sooner(self):
        kept, gone = self.keep("aaaaaaaaaaaa"), self.keep("bbbbbbbbbbbb")
        self.save("aaaaaaaaaaaa")
        owners = self.user / "save games" / "france_1850.v3"
        owners.write_bytes(b"the owner's own save")
        self.assertEqual(selfchecks.drop_orphans(self.backups, self.user), ["bbbbbbbbbbbb"])
        self.assertFalse(gone.exists())
        self.assertEqual(sorted(p.name for p in kept.iterdir()), ["lines.log", "record.json"])
        self.assertEqual(selfchecks.drop_orphans(self.backups, self.user), [])
        self.assertEqual(sorted(p.name for p in (self.user / "save games").iterdir()),
                         ["france_1850.v3", "te_qa_fixture_aaaaaaaaaaaa.v3"])

    def test_nothing_is_dropped_while_the_saves_cannot_be_seen(self):
        kept = self.keep("aaaaaaaaaaaa")
        os.rmdir(self.user / "save games")      # as a drive that is not mounted: no fixture can be seen
        self.assertEqual(selfchecks.drop_orphans(self.backups, self.user), [])
        self.assertTrue((kept / "lines.log").is_file())

    def test_only_the_harnesss_own_files_are_removed(self):
        gone = self.keep("bbbbbbbbbbbb")
        (gone / "notes of the owner's.txt").write_text("keep me", encoding="utf-8")
        stray = self.backups / "fixtures" / "not a key"
        stray.mkdir()
        (stray / "lines.log").write_text("x", encoding="utf-8")
        self.assertEqual(selfchecks.drop_orphans(self.backups, self.user), ["bbbbbbbbbbbb"])
        self.assertEqual([p.name for p in gone.iterdir()], ["notes of the owner's.txt"])
        self.assertTrue((stray / "lines.log").is_file())

    def test_with_no_fixtures_folder_there_is_nothing_to_drop(self):
        self.assertEqual(selfchecks.drop_orphans(self.backups, self.user), [])
        self.assertFalse((self.backups / "fixtures").exists())


class VerdictTest(unittest.TestCase):
    def test_one_entry_per_check_with_the_line_as_the_script_logged_it(self):
        raw = captured("session2_self_checks.txt")
        checks = selfchecks.verdicts(logged(raw), "session")
        self.assertEqual(len(checks), 28)
        by_name = {check["name"]: check for check in checks}
        self.assertEqual(len(by_name), 28)
        broken = by_name["delayed_state_event"]
        self.assertEqual((broken["verdict"], broken["source"]), ("BROKEN", "session"))
        self.assertEqual(broken["line"], next(line for line in raw if "delayed_state_event" in line))
        self.assertTrue(broken["line"].startswith("events/te_debug_demog_events.txt:1298: TE_SELF_CHECK BROKEN"))
        self.assertNotIn("seen", broken)

    def test_a_start_is_a_verdict_only_while_none_followed_it(self):
        checks = {c["name"]: c for c in selfchecks.verdicts(logged(captured("session2_self_checks.txt")), "session")}
        self.assertEqual(checks["cm_census_yearly"]["verdict"], "START")
        answered = checks["conscription_term_read"]
        self.assertEqual((answered["verdict"], answered["seen"]), ("OK", {"START": 1, "OK": 1}))
        self.assertIn("TE_SELF_CHECK OK conscription_term_read", answered["line"])

    def test_one_broken_line_makes_the_check_broken_whatever_else_it_logged(self):
        lines = logged(["common/a.txt:1: TE_SELF_CHECK OK twice n=1", "common/a.txt:1: TE_SELF_CHECK BROKEN twice n=2",
                        "common/a.txt:1: TE_SELF_CHECK OK twice n=3"])
        (check,) = selfchecks.verdicts(lines, "fixture")
        self.assertEqual((check["verdict"], check["seen"]), ("BROKEN", {"OK": 2, "BROKEN": 1}))
        self.assertTrue(check["line"].endswith("n=2"))

    def test_the_pattern_is_log_triages(self):
        import log_triage       # on the path once selfchecks has asked for it

        self.assertIs(selfchecks._pattern(), log_triage.SELF_CHECK_RE)

    def test_a_line_that_is_not_a_debug_log_line_is_still_read(self):
        (check,) = selfchecks.verdicts(["TE_SELF_CHECK OK bare (a line with no prefix)"], "session")
        self.assertEqual((check["name"], check["line"]), ("bare", "TE_SELF_CHECK OK bare (a line with no prefix)"))


class RunTest(SelfCheckTestCase):
    def kept_fixture(self) -> str:
        snap = self.fixture_run(logged(captured("fixture_run_self_checks_and_monuments.txt")))
        selfchecks.keep_fixture_lines(self.backups, KEY, snap)
        return snap

    def session_log(self) -> list[str]:
        lines = logged(captured("session2_self_checks.txt"))
        return [NOISE, *lines[:10], NOISE, logtail.GAP_MARKER, *lines[10:], NOISE]

    def test_a_runs_verdicts_are_the_fixtures_and_the_sessions_broken_first(self):
        fixture_snap = self.kept_fixture()
        folder = self.run_folder(log=self.session_log())
        found = selfchecks.of_run(self.backups, RUN)
        self.assertEqual(found["run"], RUN)
        self.assertEqual(found["broken"], ["unemployment_share_read", "delayed_state_event"])
        self.assertEqual(found["counts"], {"BROKEN": 2, "START": 2, "OK": 35})
        checks = found["checks"]
        self.assertEqual([c["verdict"] for c in checks], ["BROKEN"] * 2 + ["START"] * 2 + ["OK"] * 35)
        self.assertEqual([(c["name"], c["source"]) for c in checks[:4]], [
            ("unemployment_share_read", "fixture"), ("delayed_state_event", "session"),
            ("conscription_term_read", "fixture"), ("cm_census_yearly", "session")])
        for check in checks:
            self.assertEqual(set(check) - {"seen"}, {"name", "verdict", "line", "source"})
        # the checks a new game logs only at its setup come from the fixture's run alone
        for name in ("decentralized_law_baseline", "primate_state_flag", "monument_piece_rejoins",
                     "monument_artifact_stands_apart"):
            self.assertEqual([c["source"] for c in checks if c["name"] == name], ["fixture"], name)
        # one the fixture's run found broken and the session found working is listed for each
        self.assertEqual([(c["source"], c["verdict"]) for c in checks if c["name"] == "unemployment_share_read"],
                         [("fixture", "BROKEN"), ("session", "OK")])
        self.assertEqual(found["fixture"], {
            "key": KEY, "kept": True, "file": str(self.backups / "fixtures" / KEY / "lines.log"),
            "snapshot": fixture_snap, "kept_at": selfchecks.fixture_record(self.backups, KEY)["kept_at"],
            "lines": 114, "self_checks": 11})
        self.assertEqual(found["session"], {"file": str(folder / "debug.log"), "lines": 31, "gaps": 1})
        json.dumps(found)

    def test_a_fixture_whose_lines_were_never_kept_says_so(self):
        self.run_folder(log=self.session_log())
        found = selfchecks.of_run(self.backups, RUN)
        self.assertEqual((found["fixture"]["key"], found["fixture"]["kept"]), (KEY, False))
        self.assertIn("run_logs/debug.log", found["fixture"]["detail"])
        self.assertEqual({c["source"] for c in found["checks"]}, {"session"})
        self.assertEqual(found["broken"], ["delayed_state_event"])

    def test_a_run_on_the_owners_save_has_no_fixture(self):
        self.kept_fixture()
        self.run_folder(fixture=("not_used", "france_1850"), log=self.session_log())
        found = selfchecks.of_run(self.backups, RUN)
        self.assertEqual((found["fixture"]["key"], found["fixture"]["kept"]), (None, False))
        self.assertIn("a save of the owner's", found["fixture"]["detail"])
        self.assertEqual({c["source"] for c in found["checks"]}, {"session"})

    def test_a_save_name_in_the_steps_is_never_a_path(self):
        self.kept_fixture()
        self.run_folder(fixture=("found", "te_qa_fixture_../../" + KEY), log=[])
        found = selfchecks.of_run(self.backups, RUN)
        self.assertFalse(found["fixture"]["kept"])
        self.assertEqual(found["checks"], [])

    def test_a_run_with_no_log_has_no_session_lines(self):
        folder = self.run_folder()
        found = selfchecks.of_run(self.backups, RUN)
        self.assertEqual((found["checks"], found["broken"], found["counts"]), ([], [], {}))
        self.assertEqual(found["session"], {"file": str(folder / "debug.log"), "lines": 0})

    def test_the_newest_run_is_the_newest_sessions(self):
        with self.assertRaises(selfchecks.SelfCheckError) as caught:
            selfchecks.resolve_run(self.backups)
        self.assertEqual(caught.exception.code, "no_run")
        self.run_folder("20261111T100000Z")
        self.run_folder("20261111T182536Z")
        self.run_folder("20261111T182536Z-2")
        # a run that only made a fixture leaves a folder with its watch's log and no steps; so does the server
        (self.backups / "runs" / "20261111T190000Z").mkdir()
        (self.backups / "runs" / "20261111T190000Z" / "watch.log").write_text("{}", encoding="utf-8")
        (self.backups / "runs" / "session-serve-20261111T200000Z.log").write_text("", encoding="utf-8")
        self.assertEqual(selfchecks.resolve_run(self.backups), "20261111T182536Z-2")
        self.assertEqual(selfchecks.resolve_run(self.backups, "20261111T100000Z"), "20261111T100000Z")
        for missing in ("20261112T000000Z", "../snapshots", "", 5):
            with self.subTest(run=missing), self.assertRaises(selfchecks.SelfCheckError):
                selfchecks.resolve_run(self.backups, missing)


class VerbTest(SelfCheckTestCase):
    """`python3 -m game_qa selfchecks` with no session: files alone."""

    def setUp(self):
        super().setUp()
        patch = mock.patch.dict(os.environ, {"VIC3_QA_BACKUPS": str(self.backups)})
        patch.start()
        self.addCleanup(patch.stop)

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return json.loads(out.getvalue()), code

    def test_the_verb_reads_the_newest_run_or_the_one_named(self):
        self.run_folder("20261111T100000Z", log=logged(["common/a.txt:1: TE_SELF_CHECK OK older"]))
        self.run_folder(RUN, log=logged(captured("session2_self_checks.txt")))
        reply, code = self.run_cli("selfchecks")
        self.assertEqual((code, reply["run"], reply["live"]), (0, RUN, False))
        self.assertNotIn("flushed", reply)
        self.assertEqual(reply["broken"], ["delayed_state_event"])       # a BROKEN is data, not a refusal
        self.assertEqual(reply["checks"][0]["verdict"], "BROKEN")
        reply, code = self.run_cli("selfchecks", "--run", "20261111T100000Z")
        self.assertEqual((code, reply["run"], [c["name"] for c in reply["checks"]]), (0, "20261111T100000Z", ["older"]))

    def test_a_run_that_is_not_there_is_refused(self):
        reply, code = self.run_cli("selfchecks")
        self.assertEqual((reply["refused"], code), ("no_run", 2))
        self.run_folder(RUN)
        reply, code = self.run_cli("selfchecks", "--run", "20200101T000000Z")
        self.assertEqual((reply["refused"], code), ("no_run", 2))

    def test_a_session_file_that_names_a_dead_server_does_not_hide_the_files(self):
        self.run_folder(RUN, log=logged(captured("session2_self_checks.txt")))
        with open(self.backups / server.SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump({"port": 1, "pid": os.getpid(), "started": "2026-11-11T18:25:00Z", "token": "0" * 32,
                       "snapshot": RUN}, f)
        reply, code = client.self_checks(self.backups)
        self.assertEqual((code, reply["live"], reply["flushed"]), (0, True, False))
        self.assertEqual(reply["not_flushed"]["refused"], "no_session")
        self.assertEqual(reply["broken"], ["delayed_state_event"])


if __name__ == "__main__":
    unittest.main()
