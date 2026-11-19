"""game_qa/crash_reporter.py: the launch flag, the reporter listing and its close, and which reporter is the run's.

Nothing here runs PowerShell: `run` is a fake, and `settle` gets fakes of `list_reporters` and `close`. The
command-line half (`restore` and `recover` closing the run's reporter) is in test_game_qa_gate.CommandLineTest.
"""
import base64
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from game_qa import crash_reporter, gate, snapshot
from test_game_qa_snapshot import make_user_data

END = "te_qa_end\r\n"
EXE = r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\binaries\crash_reporter\binaries\CrashReporter.exe"
GAME_START = datetime(2026, 11, 19, 9, 29, 16, tzinfo=timezone.utc)


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def win(when: datetime) -> str:
    """A time as Windows prints a process's start: seven fractional digits and a Z."""
    return when.strftime("%Y-%m-%dT%H:%M:%S.%f0Z")


def journal_time(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def reporter(pid=7000, after_s=60.0, path=EXE, parent=4242):
    return crash_reporter.Reporter(pid, win(GAME_START + timedelta(seconds=after_s)), parent, path)


def run_journal(exited_after_s: float | None = 62.0, created=None, others=False):
    """A run's journal: its game started at GAME_START, maybe saw another game, maybe exited."""
    entries = [{"event": "armed", "at": journal_time(GAME_START - timedelta(seconds=10))},
               {"event": "started", "at": journal_time(GAME_START), "pid": 4242,
                "created": win(GAME_START) if created is None else created}]
    if others:
        entries.append({"event": "other_game", "at": journal_time(GAME_START), "pid": 9, "created": "x"})
    if exited_after_s is not None:
        entries.append({"event": "game_exited", "at": journal_time(GAME_START + timedelta(seconds=exited_after_s))})
    return entries


class WithFlagTest(unittest.TestCase):
    def test_the_flag_is_added_at_the_end(self):
        given = ["-gdpr-compliant", "-debug_mode"]
        self.assertEqual(crash_reporter.with_flag(given), ["-gdpr-compliant", "-debug_mode", "-no_crash_reporter"])
        self.assertEqual(given, ["-gdpr-compliant", "-debug_mode"])        # the caller's list is not changed

    def test_a_flag_given_in_any_spelling_is_not_added_again(self):
        for spelling in ("-no_crash_reporter", "/no_crash_reporter", "-NO_CRASH_REPORTER", "no_crash_reporter"):
            with self.subTest(spelling=spelling):
                self.assertEqual(crash_reporter.with_flag(["-debug_mode", spelling]), ["-debug_mode", spelling])

    def test_an_empty_list_gets_the_flag(self):
        self.assertEqual(crash_reporter.with_flag([]), ["-no_crash_reporter"])


class ListReportersTest(unittest.TestCase):
    def test_each_line_is_a_reporter_with_its_path_whole(self):
        out = crash_reporter.list_reporters(run=lambda *a, **k: completed(
            f"7000 2026-11-19T09:30:16.1234567Z 4242 {EXE}\r\n"
            "7001 unknown unknown \r\n" + END))
        self.assertEqual(out, [crash_reporter.Reporter(7000, "2026-11-19T09:30:16.1234567Z", 4242, EXE),
                               crash_reporter.Reporter(7001, "unknown", None, "")])

    def test_no_reporter_is_an_empty_list(self):
        self.assertEqual(crash_reporter.list_reporters(run=lambda *a, **k: completed(END, 1)), [])

    def test_a_listing_that_did_not_finish_raises(self):
        for stdout in ("", f"7000 2026-11-19T09:30:16Z 4242 {EXE}\r\n"):
            with self.subTest(stdout=stdout), self.assertRaises(gate.GateError):
                crash_reporter.list_reporters(run=lambda *a, **k: completed(stdout))

    def test_a_line_that_does_not_read_as_a_reporter_raises(self):
        for line in ("WARNING: something\r\n", "7000 2026-11-19T09:30:16Z\r\n"):
            with self.subTest(line=line), self.assertRaises(gate.GateError):
                crash_reporter.list_reporters(run=lambda *a, **k: completed(line + END))

    def test_powershell_that_will_not_run_raises(self):
        def run(*a, **k):
            raise FileNotFoundError("powershell.exe")
        with self.assertRaises(gate.GateError):
            crash_reporter.list_reporters(run=run)

    def test_it_lists_the_crash_reporter_by_name(self):
        script = crash_reporter.LIST_REPORTERS[-1]
        self.assertIn("Get-Process -Name CrashReporter", script)
        self.assertTrue(script.startswith("$ErrorActionPreference = 'Stop'"))
        self.assertTrue(script.endswith("'te_qa_end'"))


class CloseTest(unittest.TestCase):
    def close(self, stdout, who=None):
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            return completed(stdout)
        outcome = crash_reporter.close(who or reporter(), run=run)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3], ["powershell.exe", "-NoProfile", "-EncodedCommand"])
        return outcome, base64.b64decode(calls[0][3]).decode("utf-16-le")

    def test_it_ends_the_process_only_with_its_pid_name_and_start_time(self):
        outcome, script = self.close("closed\r\n" + END)
        self.assertEqual(outcome, crash_reporter.CLOSED)
        self.assertIn("Stop-Process -Id 7000 -Force", script)
        self.assertIn("Get-Process -Id 7000", script)
        self.assertIn("-eq 'CrashReporter'", script)
        self.assertIn("-eq '%s'" % win(GAME_START + timedelta(seconds=60)), script)
        self.assertLess(script.index("if (-not $same) { 'gone' }"), script.index("Stop-Process"))

    def test_gone_and_still_up_are_told_apart(self):
        self.assertEqual(self.close("gone\r\n" + END)[0], crash_reporter.GONE)
        self.assertEqual(self.close("still_up\r\n" + END)[0], crash_reporter.STILL_UP)

    def test_a_start_time_with_a_quote_cannot_break_out_of_its_string(self):
        _, script = self.close("gone\r\n" + END, crash_reporter.Reporter(7000, "x'; Stop-Process -Id 1; '", 1, EXE))
        self.assertIn("'x''; Stop-Process -Id 1; '''", script)

    def test_an_answer_that_did_not_finish_raises(self):
        for stdout in ("", "closed\r\n", "maybe\r\n" + END, "closed\r\nclosed\r\n" + END):
            with self.subTest(stdout=stdout), self.assertRaises(gate.GateError):
                crash_reporter.close(reporter(), run=lambda *a, **k: completed(stdout))


class RunsOwnTest(unittest.TestCase):
    def judge(self, reporters, journal=None, exe=EXE):
        return crash_reporter.runs_own(run_journal() if journal is None else journal, reporters, exe)

    def test_this_installs_reporter_started_after_the_runs_game_is_the_runs(self):
        mine = reporter()
        self.assertEqual(self.judge([mine]), ([mine], []))

    def test_the_path_is_compared_as_windows_compares_it(self):
        mine = reporter(path=EXE.upper().replace("\\", "/"))
        self.assertEqual(self.judge([mine]), ([mine], []))

    def test_another_programs_reporter_is_not_looked_at(self):
        ck3 = reporter(path=r"C:\Program Files (x86)\Steam\steamapps\common\Crusader Kings III\binaries"
                            r"\crash_reporter\binaries\CrashReporter.exe")
        self.assertEqual(self.judge([ck3]), ([], []))

    def test_the_others_are_left_with_why(self):
        cases = {
            "before": (reporter(after_s=-5), None, "before this run's game"),
            "unreadable path": (reporter(path=""), None, "executable could not be read"),
            "unknown start": (crash_reporter.Reporter(7000, "unknown", 4242, EXE), None, "start time could not"),
            "another game ran": (reporter(), run_journal(others=True), "another game"),
            "long after the exit": (reporter(after_s=62 + crash_reporter.AFTER_EXIT_S + 30), None, "after this run"),
            "no game start": (reporter(), run_journal(created="unknown"), "no start time for its game"),
            "no started": (reporter(), run_journal()[:1], "no start time for its game"),
        }
        for name, (who, journal, why) in cases.items():
            with self.subTest(name):
                ours, left = self.judge([who], journal)
                self.assertEqual(ours, [])
                self.assertEqual(len(left), 1)
                self.assertEqual(left[0]["pid"], who.pid)
                self.assertIn(why, left[0]["why"])

    def test_with_no_exit_recorded_any_reporter_since_the_start_is_the_runs(self):
        # `watch` died before it saw the exit: nothing bounds the run's end, and no other game was seen.
        late = reporter(after_s=3600)
        self.assertEqual(self.judge([late], run_journal(exited_after_s=None)), ([late], []))

    def test_a_reporter_a_little_after_the_exit_is_still_the_runs(self):
        # `watch` saw the exit at a look, and two clocks are compared: the margin covers both.
        near = reporter(after_s=62 + crash_reporter.AFTER_EXIT_S - 1)
        self.assertEqual(self.judge([near]), ([near], []))


class SettleTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.user = root / "user data"
        make_user_data(self.user)
        self.snap = snapshot.take(self.user, root / "backups")
        for entry in run_journal():
            fields = {k: v for k, v in entry.items() if k not in ("event", "at")}
            snapshot.record(self.snap, entry["event"], now=datetime.strptime(entry["at"], "%Y-%m-%dT%H:%M:%SZ")
                            .replace(tzinfo=timezone.utc), **fields)
        self.exe = root / "game" / crash_reporter.REPORTER_EXE
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(b"MZ")
        self.up = [reporter()]
        self.closes = []
        self.close_outcome = crash_reporter.CLOSED
        for patch in (mock.patch.object(crash_reporter, "list_reporters", side_effect=self.listing),
                      mock.patch.object(crash_reporter, "close", side_effect=self.close)):
            patch.start()
            self.addCleanup(patch.stop)

    def listing(self, *a, **k):
        if isinstance(self.up, Exception):
            raise self.up
        return list(self.up)

    def close(self, who, *a, **k):
        self.closes.append(who)
        if isinstance(self.close_outcome, Exception):
            raise self.close_outcome
        return self.close_outcome

    def settle(self, games=()):
        return crash_reporter.settle(self.snap, list(games), self.exe, windows_path=lambda path: EXE)

    def test_the_runs_reporter_is_closed_and_journaled(self):
        notes = self.settle()
        self.assertEqual(self.closes, self.up)
        self.assertEqual(notes, {"reporters_closed": [dict(self.up[0].as_dict(), outcome="closed")]})
        entry = snapshot.journal(self.snap)[-1]
        self.assertEqual((entry["event"], entry["pid"], entry["created"], entry["parent"], entry["outcome"]),
                         ("reporter_closed", 7000, self.up[0].created, 4242, "closed"))

    def test_one_that_had_gone_by_the_stop_counts_as_closed(self):
        self.close_outcome = crash_reporter.GONE
        self.assertEqual(self.settle()["reporters_closed"][0]["outcome"], "gone")

    def test_nothing_is_looked_for_without_the_installs_reporter_a_game_running_or_a_start(self):
        self.exe.unlink()
        self.assertEqual(self.settle(), {})
        self.assertEqual(crash_reporter.settle(self.snap, [], None), {})
        self.exe.write_bytes(b"MZ")
        self.assertEqual(self.settle(games=[gate.ProcId(9, "x")]), {})
        never = snapshot.take(self.user, self.snap.dir.parent.parent)
        self.assertEqual(crash_reporter.settle(never, [], self.exe, windows_path=lambda path: EXE), {})
        self.assertEqual(self.closes, [])
        self.assertNotIn("reporter_closed", [e["event"] for e in snapshot.journal(self.snap)])

    def test_one_not_the_runs_is_left_and_listed(self):
        self.up = [reporter(pid=6000, after_s=-600)]
        notes = self.settle()
        self.assertEqual(self.closes, [])
        self.assertEqual([r["pid"] for r in notes["reporters_left"]], [6000])
        self.assertNotIn("reporters_closed", notes)

    def test_one_that_outlives_its_stop_or_whose_stop_fails_is_left(self):
        for outcome, why in ((crash_reporter.STILL_UP, "still up"), (gate.GateError("no powershell"), "failed")):
            with self.subTest(outcome=outcome):
                self.close_outcome = outcome
                notes = self.settle()
                self.assertNotIn("reporters_closed", notes)
                self.assertIn(why, notes["reporters_left"][0]["why"])
        self.assertNotIn("reporter_closed", [e["event"] for e in snapshot.journal(self.snap)])

    def test_a_listing_that_fails_is_noted_and_closes_nothing(self):
        self.up = gate.GateError("could not list crash reporter processes")
        self.assertEqual(self.settle(), {"reporters_unlisted": "could not list crash reporter processes"})
        self.assertEqual(self.closes, [])


class NotesTest(unittest.TestCase):
    def test_merge_joins_the_closed_and_keeps_the_latest_look(self):
        first = {"pid": 1, "created": "a", "outcome": "closed"}
        notes = {"playset_restored": True, "reporters_closed": [first], "reporters_left": [{"pid": 2}]}
        crash_reporter.merge(notes, {"reporters_closed": [first, {"pid": 3, "created": "c", "outcome": "closed"}]})
        self.assertEqual(notes, {"playset_restored": True,
                                 "reporters_closed": [first, {"pid": 3, "created": "c", "outcome": "closed"}]})
        crash_reporter.merge(notes, {"reporters_unlisted": "no powershell"})
        self.assertEqual(notes["reporters_unlisted"], "no powershell")
        self.assertEqual(len(notes["reporters_closed"]), 2)

    def test_the_hint_names_who_may_hold_the_file(self):
        denied = PermissionError(13, "Permission denied")
        left = {"reporters_left": [{"pid": 6000, "created": "t", "why": "it started before this run's game did"}]}
        self.assertIn("pid 6000", crash_reporter.held_open_hint(denied, left))
        self.assertIn("Ask the owner", crash_reporter.held_open_hint(denied, left))
        self.assertIn("doctor", crash_reporter.held_open_hint(denied, {"reporters_unlisted": "x"}))
        self.assertIn("another program", crash_reporter.held_open_hint(denied, {}))
        self.assertEqual(crash_reporter.held_open_hint(OSError("disk fell off"), left), "")


if __name__ == "__main__":
    unittest.main()
