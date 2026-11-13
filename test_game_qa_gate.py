"""game_qa/gate.py: the GPU reading, process identity and the launch gate's decision.

Nothing here runs nvidia-smi or PowerShell: both are passed in as fakes.
"""
import base64
import contextlib
import datetime as dt
import io
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from game_qa import __main__ as cli
from game_qa import gate, restore, snapshot

IDLE = [gate.GpuSample(14, 1607, 10240)] * 5
MINE = gate.ProcId(100, "2026-11-10T12:00:00.0000000Z")
UTC = dt.timezone.utc


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def iso(when: dt.datetime) -> str:
    """A time as Windows prints a process's creation time: seven fractional digits and a Z."""
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0Z")


class UnexpectedStart(BaseException):
    """A test started a game it did not ask for. A BaseException, so `main` cannot turn it into JSON."""


class GpuTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(gate.parse_nvidia_smi("14, 1607, 10240\n"), [gate.GpuSample(14.0, 1607, 10240)])

    def test_parse_skips_lines_it_cannot_read(self):
        self.assertEqual(gate.parse_nvidia_smi("\n[N/A], 10, 20\n3, 4, 5\r\n"), [gate.GpuSample(3.0, 4, 5)])

    def test_idle_is_not_busy(self):
        self.assertFalse(gate.gpu_busy(IDLE))

    def test_mean_of_fifty_is_busy(self):
        self.assertTrue(gate.gpu_busy([gate.GpuSample(u, 1000, 10240) for u in (0, 100, 0, 100, 50)]))

    def test_just_under_fifty_is_not_busy(self):
        self.assertFalse(gate.gpu_busy([gate.GpuSample(u, 1000, 10240) for u in (49, 50, 49, 50, 49)]))

    def test_over_half_the_memory_is_busy(self):
        self.assertTrue(gate.gpu_busy([gate.GpuSample(1, 5121, 10240)] * 5))

    def test_exactly_half_the_memory_is_not_busy(self):
        self.assertFalse(gate.gpu_busy([gate.GpuSample(1, 5120, 10240)] * 5))

    def test_no_reading_is_busy(self):
        self.assertTrue(gate.gpu_busy([]))

    def test_missing_nvidia_smi_gives_no_samples(self):
        def run(*a, **k):
            raise FileNotFoundError

        self.assertEqual(gate.sample_gpu(run=run, sleep=lambda s: None), [])

    def test_failing_nvidia_smi_gives_no_samples(self):
        self.assertEqual(gate.sample_gpu(run=lambda *a, **k: completed("", 9), sleep=lambda s: None), [])

    def test_five_samples_one_second_apart(self):
        naps = []
        out = gate.sample_gpu(run=lambda *a, **k: completed("14, 1607, 10240\n"), sleep=naps.append)
        self.assertEqual(out, IDLE)
        self.assertEqual(naps, [1.0] * 4)


class ListGamesTest(unittest.TestCase):
    END = "te_qa_end\r\n"

    def test_parses_pid_and_creation_time(self):
        out = gate.list_games(run=lambda *a, **k: completed("81168 2026-11-10T18:59:22.1234567Z\r\n" + self.END))
        self.assertEqual(out, [gate.ProcId(81168, "2026-11-10T18:59:22.1234567Z")])

    def test_no_game_is_an_empty_list_whatever_the_exit_code(self):
        # Get-Process with no match may leave a non-zero exit code: the end line is what counts.
        for code in (0, 1):
            with self.subTest(code=code):
                self.assertEqual(gate.list_games(run=lambda *a, **k: completed(self.END, code)), [])

    def test_a_listing_that_did_not_reach_its_end_line_raises(self):
        # Review 2026-11-10, I1: PowerShell ran and failed, and the empty output read as "no game".
        game = "81168 2026-11-10T18:59:22.1234567Z\r\n"
        for stdout, code in (("", 1), ("", 0), (game, 0), (self.END + game, 0)):
            with self.subTest(stdout=stdout, code=code), self.assertRaises(gate.GateError):
                gate.list_games(run=lambda *a, **k: completed(stdout, code))

    def test_a_line_that_does_not_read_as_a_game_raises(self):
        # A skipped line could be a game.
        for line in ("WARNING: something\r\n", "81168\r\n", "81168 a b\r\n", "x 2026-11-10T18:59:22Z\r\n"):
            with self.subTest(line=line), self.assertRaises(gate.GateError):
                gate.list_games(run=lambda *a, **k: completed(line + self.END))

    def test_a_start_time_the_session_may_not_read_is_unknown(self):
        out = gate.list_games(run=lambda *a, **k: completed("4 unknown\r\n" + self.END))
        self.assertEqual(out, [gate.ProcId(4, "unknown")])

    def test_the_command_stops_at_its_first_error_and_prints_the_end_line_last(self):
        # Probed 2026-11-10 with powershell.exe: without Stop, a failing statement is skipped and the end line
        # still printed (exit 0); with it, nothing after the failure runs. A StartTime the session may not
        # read (Idle, System) throws inside the try and prints "<pid> unknown".
        script = gate.LIST_GAMES[-1]
        self.assertTrue(script.startswith("$ErrorActionPreference = 'Stop'; "))
        self.assertIn("catch { '{0} unknown' -f $p.Id }", script)
        self.assertTrue(script.endswith("; 'te_qa_end'"))

    def test_powershell_that_cannot_run_raises(self):
        def run(*a, **k):
            raise FileNotFoundError

        with self.assertRaises(gate.GateError):
            gate.list_games(run=run)


class StartGameTest(unittest.TestCase):
    """gate.start_game builds one PowerShell call; nothing here runs it."""

    EXE = r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\binaries\victoria3.exe"
    CWD = r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\binaries"
    STARTED = "4242 2026-11-10T23:06:35.4149252Z\r\nte_qa_end\r\n"

    def start(self, args, stdout=STARTED, returncode=0):
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            return completed(stdout, returncode)

        return gate.start_game(self.EXE, args, self.CWD, run=run), calls

    def script(self, argv):
        """The script of an `-EncodedCommand` call, which reaches PowerShell without a command line's quoting."""
        self.assertEqual(argv[:3], ["powershell.exe", "-NoProfile", "-EncodedCommand"])
        return base64.b64decode(argv[3]).decode("utf-16-le")

    def test_returns_the_new_process(self):
        proc, calls = self.start(["-debug_mode"])
        self.assertEqual(proc, gate.ProcId(4242, "2026-11-10T23:06:35.4149252Z"))
        self.assertEqual(len(calls), 1)

    def test_starts_the_game_in_its_folder_and_prints_its_id_start_time_and_end_line(self):
        _, calls = self.start(["-debug_mode"])
        script = self.script(calls[0])
        self.assertTrue(script.startswith("$ErrorActionPreference = 'Stop'; "))
        self.assertIn(f"Start-Process -FilePath '{self.EXE}' -WorkingDirectory '{self.CWD}' "
                      "-ArgumentList '-debug_mode' -PassThru", script)
        self.assertIn("catch { '{0} unknown' -f $p.Id }", script)
        self.assertTrue(script.endswith("; 'te_qa_end'"))

    def test_quotes_each_argument_for_powershell_and_for_the_windows_command_line(self):
        # Probed 2026-11-10 with cmd.exe /c echo: Start-Process joins the elements with spaces and adds no quotes,
        # so an argument with a space carries its own double quotes; PowerShell also ends a single-quoted string
        # at a typographic quote, which is doubled like ' is.
        args = ["-debug_mode", "a b", "it's", "-loadsave=te qa's", 'say "hi"', "a\u2019b", ""]
        _, calls = self.start(args)
        self.assertIn("-ArgumentList '-debug_mode', '\"a b\"', 'it''s', '\"-loadsave=te qa''s\"', "
                      "'\"say \\\"hi\\\"\"', 'a\u2019\u2019b', '\"\"' -PassThru", self.script(calls[0]))

    def test_paths_with_a_single_quote_are_quoted_too(self):
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            return completed(self.STARTED)

        gate.start_game(r"D:\Jake's games\victoria3.exe", [], r"D:\Jake's games", run=run)
        script = self.script(calls[0])
        self.assertIn(r"-FilePath 'D:\Jake''s games\victoria3.exe' -WorkingDirectory 'D:\Jake''s games' -PassThru",
                      script)
        self.assertNotIn("-ArgumentList", script)        # Start-Process refuses an empty argument list

    def test_a_start_time_it_cannot_read_is_unknown(self):
        proc, _ = self.start([], stdout="4242 unknown\r\nte_qa_end\r\n")
        self.assertEqual(proc, gate.ProcId(4242, "unknown"))

    def test_raises_without_the_end_line_or_without_an_id(self):
        for stdout, code in (("", 1), ("4242 2026-11-10T23:06:35.4149252Z\r\n", 0), ("te_qa_end\r\n", 0),
                             ("Start-Process : failed\r\nte_qa_end\r\n", 0),
                             ("4242 2026-11-10T23:06:35Z\r\n4243 2026-11-10T23:06:35Z\r\nte_qa_end\r\n", 0)):
            with self.subTest(stdout=stdout), self.assertRaises(gate.GateError):
                self.start(["-debug_mode"], stdout=stdout, returncode=code)

    def test_powershell_that_cannot_run_raises(self):
        def run(*a, **k):
            raise FileNotFoundError

        with self.assertRaises(gate.GateError):
            gate.start_game(self.EXE, [], self.CWD, run=run)


class WindowsPathTest(unittest.TestCase):
    def test_asks_wslpath(self):
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            return completed("C:\\Program Files (x86)\\Steam\r\n")

        self.assertEqual(gate.windows_path(Path("/mnt/c/Program Files (x86)/Steam"), run=run),
                         "C:\\Program Files (x86)\\Steam")
        self.assertEqual(calls, [["wslpath", "-w", "/mnt/c/Program Files (x86)/Steam"]])

    def test_a_failing_or_missing_wslpath_raises(self):
        def missing(*a, **k):
            raise FileNotFoundError

        for run in (lambda *a, **k: completed("", 1), lambda *a, **k: completed("\n"), missing):
            with self.assertRaises(gate.GateError):
                gate.windows_path(Path("/x"), run=run)


class CheckTest(unittest.TestCase):
    def test_all_clear(self):
        g = gate.check("asked 12:40", [], set(), IDLE, False, None)
        self.assertEqual((g.ok, g.reason), (True, "ok"))

    def test_blank_permission_refuses_first(self):
        g = gate.check("  ", [], set(), [], False, "no backup root")
        self.assertEqual((g.ok, g.reason), (False, "no_permission"))

    def test_backup_error_refuses(self):
        g = gate.check("asked 12:40", [], set(), IDLE, False, "D: is missing")
        self.assertEqual((g.reason, g.detail), ("backup_root", "D: is missing"))

    def test_a_game_that_is_not_ours_refuses(self):
        theirs = gate.ProcId(100, "2026-11-10T08:00:00.0000000Z")
        self.assertEqual(gate.check("session grant", [theirs], set(), IDLE, True, None).reason, "other_game")

    def test_orphan_of_an_unfinished_run_is_ours(self):
        self.assertTrue(gate.check("session grant", [MINE], {MINE}, IDLE, False, None).ok)

    def test_same_pid_other_creation_time_is_not_ours(self):
        reused = gate.ProcId(100, "2026-11-10T15:00:00.0000000Z")
        self.assertEqual(gate.check("session grant", [reused], {MINE}, IDLE, False, None).reason, "other_game")

    def test_busy_gpu_refuses_until_the_owner_confirms(self):
        busy = [gate.GpuSample(95, 9000, 10240)] * 5
        self.assertEqual(gate.check("session grant", [], set(), busy, False, None).reason, "gpu_busy")
        self.assertTrue(gate.check("session grant", [], set(), busy, True, None).ok)

    def test_no_reading_refuses_until_the_owner_confirms(self):
        self.assertEqual(gate.check("session grant", [], set(), [], False, None).reason, "gpu_busy")
        self.assertTrue(gate.check("session grant", [], set(), [], True, None).ok)

    def test_owner_confirmation_does_not_excuse_another_game(self):
        theirs = gate.ProcId(7, "x")
        self.assertEqual(gate.check("session grant", [theirs], set(), IDLE, True, None).reason, "other_game")

    def test_a_game_whose_start_time_is_unknown_is_never_ours(self):
        unknown = gate.ProcId(MINE.pid, "unknown")
        self.assertEqual(gate.check("session grant", [unknown], {MINE}, IDLE, False, None).reason, "other_game")


class OursFromJournalsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.user = root / "user"
        (self.user / "save games").mkdir(parents=True)
        (self.user / "logs").mkdir()
        (self.user / "continue_game.json").write_text("{}")
        self.backups = root / "backups"

    def test_only_unfinished_runs_count(self):
        done = snapshot.take(self.user, self.backups)
        snapshot.record(done, "started", pid=1, created="A")
        snapshot.record(done, "restored")
        held = snapshot.take(self.user, self.backups)
        snapshot.record(held, "started", pid=2, created="B")
        snapshot.record(held, "held", reason="modified_after_exit")
        live = snapshot.take(self.user, self.backups)
        snapshot.record(live, "started", pid=3, created="C")
        snapshot.record(live, "heartbeat")
        never_started = snapshot.take(self.user, self.backups)
        self.assertTrue(never_started.dir.exists())
        self.assertEqual(gate.ours_from_journals(self.backups), {gate.ProcId(3, "C")})

    def test_no_backup_root_is_no_runs(self):
        self.assertEqual(gate.ours_from_journals(self.backups / "missing"), set())

    def test_a_start_whose_time_is_unknown_is_not_counted_as_ours(self):
        # `launch` records "unknown" when it cannot read the start time; a listed "<pid> unknown" is then
        # anyone's, so the gate must not take it for this harness's own.
        live = snapshot.take(self.user, self.backups)
        snapshot.record(live, "started", pid=5, created="unknown")
        snapshot.record(live, "started", pid=6, created="D")
        self.assertEqual(gate.ours_from_journals(self.backups), {gate.ProcId(6, "D")})


class CommandLineTest(unittest.TestCase):
    """`python3 -m game_qa <verb>` against a temp user-data folder and backup root."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.user = root / "Victoria 3"
        (self.user / "save games").mkdir(parents=True)
        (self.user / "logs").mkdir()
        (self.user / "save games" / "autosave.v3").write_bytes(b"autosave")
        (self.user / "save games" / "new york_1940_07_29.v3").write_bytes(b"a named save")
        (self.user / "continue_game.json").write_text('{"title": "autosave_exit"}')
        (self.user / "console_history.txt").write_text("money 1000\n")
        (self.user / "logs" / "debug.log").write_text("the owner's log\n")
        self.backups = root / "backups"
        # What gate.list_games() returns: a list, or a queue of lists and exceptions (an exception is raised);
        # a queue's last entry repeats.
        self.games = []
        self.clock = 0.0          # seconds the naps add up to
        self.on_nap = []          # callables run at each nap: the world moves on while `watch` sleeps
        self.look_seconds = 0.0   # how far one look moves the clock (PowerShell takes its time)
        self.on_look = []         # callables run at each process listing (not again from inside one of them)
        self._in_look_hook = False
        # What gate.start_game returns, or a callable it calls for that (to act during the start); while None,
        # a start fails the test.
        self.start_result = None
        self.starts = []          # (exe, args, cwd) of every start
        self.base_game = root / "game"
        (self.base_game / "binaries").mkdir(parents=True)
        (self.base_game / "binaries" / "victoria3.exe").write_bytes(b"MZ")
        env = {"VIC3_USER_DATA": str(self.user), "VIC3_QA_BACKUPS": str(self.backups),
               "VIC3_BASE_GAME": str(self.base_game)}
        patches = [mock.patch.dict(os.environ, env),
                   mock.patch.object(gate, "list_games", side_effect=self._list_games),
                   mock.patch.object(gate, "sample_gpu", return_value=IDLE),
                   mock.patch.object(gate, "start_game", side_effect=self._start_game),
                   mock.patch.object(gate, "windows_path", side_effect=lambda path, *a, **k: "W:" + str(path)),
                   mock.patch.object(cli, "_sleep", self._nap)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _nap(self, seconds):
        self.clock += seconds
        for hook in self.on_nap:
            hook()

    def _start_game(self, exe, args, cwd, *a, **k):
        if self.start_result is None:
            raise UnexpectedStart(f"{exe} {args}")
        self.starts.append((exe, list(args), cwd))
        return self.start_result() if callable(self.start_result) else self.start_result

    def _list_games(self, *a, **k):
        self.clock += self.look_seconds
        if self.on_look and not self._in_look_hook:
            self._in_look_hook = True
            try:
                for hook in self.on_look:
                    hook()
            finally:
                self._in_look_hook = False
        if self.games and isinstance(self.games[0], (list, Exception)):
            item = self.games.pop(0) if len(self.games) > 1 else self.games[0]
            if isinstance(item, Exception):
                raise item
            return list(item)
        return list(self.games)

    @staticmethod
    def game(pid=4242, seconds_from_now=60):
        """A game process created that many seconds from now (after a snapshot taken now, or before it)."""
        when = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds_from_now)
        return gate.ProcId(pid, when.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"))

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return json.loads(out.getvalue()), code

    def tree(self):
        return sorted((str(p.relative_to(self.user)), p.stat().st_mtime_ns, p.read_bytes())
                      for p in self.user.rglob("*") if p.is_file())

    def the_snapshot(self):
        return snapshot.all_snapshots(self.backups)[-1]

    def events(self):
        return [e["event"] for e in snapshot.journal(self.the_snapshot())]

    @contextlib.contextmanager
    def naps_clock(self):
        """Inside, the backup drive's clock is the naps': the machine's time on entry, to the second, plus the
        seconds `_nap` adds from then on. Yields a function that reads it. Journal times, and the file times a
        test sets from it, are then as far apart as the run's steps make them, whatever the machine's clock does.
        Two tests whose restore must happen relied on that clock (#1648): WSL steps it by seconds, a step back
        between the run's write and its `game_exited` made the write look later than the exit, and one forward
        between two lines made a resumed `watch`'s gap look longer than WATCH_RESUME_GAP_S."""
        base = dt.datetime.now(UTC).replace(microsecond=0) - dt.timedelta(seconds=self.clock)

        def now():
            return base + dt.timedelta(seconds=self.clock)

        with mock.patch.object(snapshot, "_drive_clock", lambda folder: now()):
            yield now

    def why(self, out) -> str:
        """For an assertion on a restore: its reply (with the reason a hold gave), the journal, and each file's
        time, so that a hold the test did not expect says why it held (#1648)."""
        times = {str(p.relative_to(self.user)): dt.datetime.fromtimestamp(p.stat().st_mtime, UTC).isoformat()
                 for p in sorted(self.user.rglob("*")) if p.is_file()}
        return (f"\nreply: {out}\njournal: {snapshot.journal(self.the_snapshot())}\nfile times: {times}"
                f"\nmachine clock: {dt.datetime.now(UTC).isoformat()}")

    def owner_writes(self, rel, data, minutes_ago):
        """The owner writes `rel`, dated that many minutes ago."""
        path = self.user / rel
        path.write_bytes(data)
        when = (dt.datetime.now(UTC) - dt.timedelta(minutes=minutes_ago)).timestamp()
        os.utime(path, (when, when))

    def armed_snapshot(self, armed: dt.datetime) -> snapshot.Snapshot:
        """A snapshot taken for a run whose journal says it was armed at `armed`."""
        snap = snapshot.take(self.user, self.backups)
        snapshot.record(snap, "armed", now=armed)
        return snap

    def run_an_hour_ago(self, started=True):
        """The 2026-11-10 review's reproductions of C1: a snapshot armed an hour ago (with `started`, its run's
        game started then and exited ten minutes later), and the game the owner started 35 minutes ago."""
        now = dt.datetime.now(UTC)
        armed = now - dt.timedelta(hours=1)
        snap = self.armed_snapshot(armed)
        if started:
            snapshot.record(snap, "started", now=armed + dt.timedelta(seconds=60),
                            pid=4242, created=iso(armed + dt.timedelta(seconds=50)))
            snapshot.record(snap, "game_exited", now=armed + dt.timedelta(minutes=10))
        return snap, gate.ProcId(99, iso(now - dt.timedelta(minutes=35)))

    def launch(self, snap_id, *game_args, permission="session grant", flags=()):
        return self.run_cli("launch", snap_id, "--permission", permission, *flags, "--", *game_args)

    def launched_run(self, during=lambda: None, save="new york_1940_07_29"):
        """snapshot, launch, then `watch` over the game, seen twice and then gone; `during` runs while it is up."""
        taken, code = self.run_cli("snapshot", "--save", save)
        self.assertEqual(code, 0)
        game = self.game(seconds_from_now=1)
        self.start_result = game
        out, code = self.launch(taken["id"], "-debug_mode", "-loadsave=" + save)
        self.assertEqual((code, out["pid"]), (0, game.pid))
        self.start_result = None
        during()
        self.games = [[game], [game], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["exited"], out["pid"]), (0, True, game.pid))
        self.games = []
        return taken["id"]

    # -- snapshot, watch, restore -------------------------------------------

    def test_snapshot_watch_restore_puts_a_changed_file_back(self):
        before = self.tree()

        def the_run():
            (self.user / "continue_game.json").write_text('{"title": "autosave"}')
            (self.user / "save games" / "TEST_FAIL_te_qa_fixture_2 January, 1836.v3").write_bytes(b"x")

        snap_id = self.launched_run(the_run)
        self.assertIn("save games/new york_1940_07_29.v3", self.the_snapshot().files)
        self.assertEqual(self.events(), ["armed", "started", "watching", "heartbeat", "game_exited"])
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"]), (0, False))
        self.assertEqual(self.tree(), before)

    def test_a_file_the_game_wrote_again_with_the_same_bytes_gets_its_time_back(self):
        # #1588: the game writes pdx_settings.json again at launch, byte for byte (here, a file this folder has).
        # Nothing is put back, and the folder still ends exactly as the snapshot found it, times included; the
        # reply says which time moved.
        before = self.tree()

        def the_run():
            path = self.user / "continue_game.json"
            path.write_bytes(path.read_bytes())
            when = time.time() + 0.5                    # later than the snapshot's, whatever the clock's grain
            os.utime(path, (when, when))

        snap_id = self.launched_run(the_run)
        self.assertNotEqual(self.tree(), before)
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["restored"], out["retimed"]), (0, False, [], ["continue_game.json"]))
        self.assertEqual(self.tree(), before)
        self.assertEqual(snapshot.journal(self.the_snapshot())[-1]["retimed"], ["continue_game.json"])
        again, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, again["held"]), (0, False))
        self.assertNotIn("retimed", again)              # nothing moved: the key is there only when a time was set

    def test_restore_writes_no_time_into_the_journal(self):
        taken, _ = self.run_cli("snapshot")
        (self.user / "continue_game.json").write_text("{}")
        out, code = self.run_cli("restore", taken["id"])
        # nothing recorded when the run ended, and a non-log file changed: held, the file untouched
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "no_reference_time"))
        self.assertEqual((self.user / "continue_game.json").read_text(), "{}")
        self.assertNotIn("game_exited", self.events())

    def test_restore_with_nothing_to_judge_needs_no_record(self):
        taken, _ = self.run_cli("snapshot")
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"]), (0, False))
        self.assertEqual(self.events()[-1], "restored")

    def test_a_restore_called_after_the_owner_played_holds_and_keeps_their_save(self):
        # The loss the 2026-11-10 review reproduced against the old --game-just-closed flag.
        snap_id = self.launched_run()
        theirs = self.user / "save games" / "autosave.v3"
        theirs.write_bytes(b"the owner played for an hour after the run")
        later = dt.datetime.now().timestamp() + 3600
        os.utime(theirs, (later, later))
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "modified_after_exit"))
        self.assertEqual(theirs.read_bytes(), b"the owner played for an hour after the run")
        self.assertEqual(self.run_cli("held")[0], {"held": [snap_id]})

    def test_a_restore_beside_the_owners_game_holds_and_a_retry_still_keeps_their_save(self):
        snap_id = self.launched_run()
        self.games = [self.game(pid=99, seconds_from_now=120)]      # the owner started their own game
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["reason"]), (2, "other_game_running"))
        theirs = self.user / "save games" / "autosave.v3"
        theirs.write_bytes(b"their session's autosave")
        later = dt.datetime.now().timestamp() + 3600
        os.utime(theirs, (later, later))
        self.games = []
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"]), (2, True))
        self.assertEqual(theirs.read_bytes(), b"their session's autosave")

    def test_restore_is_refused_while_the_runs_own_game_is_up(self):
        taken, _ = self.run_cli("snapshot")
        snapshot.record(self.the_snapshot(), "started", pid=MINE.pid, created=MINE.created)
        self.games = [MINE]
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["refused"], out["id"]), (2, "game_still_up", taken["id"]))
        self.assertNotIn("game_exited", self.events())

    def test_restore_reports_a_damaged_store_instead_of_a_traceback(self):
        snap_id = self.launched_run(lambda: (self.user / "continue_game.json").write_text("{}"))
        entry = self.the_snapshot().files["continue_game.json"]
        blob = self.backups / "store" / entry.sha256[:2] / entry.sha256
        blob.write_bytes(bytes(b ^ 1 for b in blob.read_bytes()))
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["refused"]), (2, "error"))
        self.assertEqual((self.user / "continue_game.json").read_text(), "{}")

    def test_restore_puts_back_a_changed_save_whose_name_has_spaces_and_commas(self):
        name = "save games/Paris, 2 January, 1836.v3"
        (self.user / name).write_bytes(b"the owner's save")
        before = self.tree()
        snap_id = self.launched_run(lambda: (self.user / name).write_bytes(b"the run saved over it"),
                                   save="Paris, 2 January, 1836")
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["restored"]), (0, False, [name]))
        self.assertEqual(self.tree(), before)

    def test_restore_waits_while_watch_is_still_recording(self):
        # Review 2026-11-10, M1: the game has just closed and `watch` has not seen it yet. Restoring now would
        # judge the game's exit writes against the last heartbeat and hold for nothing.
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        snapshot.record(self.the_snapshot(), "started", pid=game.pid, created=game.created)
        snapshot.record(self.the_snapshot(), "heartbeat")
        (self.user / "continue_game.json").write_text('{"title": "autosave_exit"}  ')
        before = self.tree()
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["refused"], out["id"]), (2, False, "watch_still_recording", taken["id"]))
        self.assertEqual(self.events(), ["armed", "started", "heartbeat"])
        self.assertEqual(self.tree(), before)

    def test_restore_goes_ahead_once_the_last_heartbeat_is_older_than_watch_would_leave_it(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        long_ago = dt.datetime.now(UTC) - dt.timedelta(seconds=20)
        snapshot.record(self.the_snapshot(), "started", now=long_ago, pid=game.pid, created=game.created)
        snapshot.record(self.the_snapshot(), "heartbeat", now=long_ago)
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"]), (0, False))
        self.assertEqual(self.events()[-1], "restored")

    # -- launch ---------------------------------------------------------------

    def test_launch_records_its_start_at_once_and_watch_and_restore_put_a_changed_file_back(self):
        before = self.tree()
        taken, _ = self.run_cli("snapshot")
        game = self.game(seconds_from_now=1)
        self.start_result = game
        args = ["-gdpr-compliant", "-debug_mode", "-loadsave=te_qa_fixture_x"]
        with self.naps_clock() as now:      # the run's write is judged against its exit (#1648)
            out, code = self.launch(taken["id"], *args)
            self.assertEqual((code, out),
                             (0, {"id": taken["id"], "pid": game.pid, "created": game.created, "args": args}))
            exe = self.base_game / "binaries" / "victoria3.exe"
            self.assertEqual(self.starts, [("W:" + str(exe), args, "W:" + str(exe.parent))])   # nothing added
            started = snapshot.journal(self.the_snapshot())[-1]
            self.assertEqual((started["event"], started["pid"], started["created"], started["args"]),
                             ("started", game.pid, game.created, args))
            run_write = self.user / "continue_game.json"
            run_write.write_text('{"title": "te_qa_fixture_x"}')
            os.utime(run_write, (now().timestamp(), now().timestamp()))   # while the run's game is up
            self.games = [[game], [game], []]
            self.assertEqual(self.run_cli("watch", taken["id"])[1], 0)
            self.games = []
            out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["restored"]), (0, False, ["continue_game.json"]), self.why(out))
        self.assertEqual(self.tree(), before)

    def test_launch_refuses_beside_any_running_game(self):
        orphan = self.armed_snapshot(dt.datetime.now(UTC) - dt.timedelta(minutes=5))
        snapshot.record(orphan, "started", pid=MINE.pid, created=MINE.created)     # a run of ours, never finished
        snap = self.armed_snapshot(dt.datetime.now(UTC))
        self.start_result = self.game()
        for games, reason in (([gate.ProcId(9, "2026-11-10T08:00:00.0000000Z")], "other_game"),
                              ([MINE], "game_running")):
            with self.subTest(reason=reason):
                self.games = games
                out, code = self.launch(snap.id, "-debug_mode", flags=("--owner-confirmed-busy",))
                self.assertEqual((code, out["refused"], out["id"]), (2, reason, snap.id))
        self.assertEqual((self.starts, self.events()), ([], ["armed"]))

    def test_launch_refuses_without_a_stated_permission_or_a_usable_backup_root(self):
        taken, _ = self.run_cli("snapshot")
        self.start_result = self.game()
        out, code = self.launch(taken["id"], "-debug_mode", permission="  ")
        self.assertEqual((code, out["refused"]), (2, "no_permission"))
        with mock.patch.object(cli, "MIN_FREE_BYTES", 1 << 62):
            out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["refused"]), (2, "backup_root"))
        self.assertEqual((self.starts, self.events()), ([], ["armed"]))

    def test_launch_refuses_a_busy_gpu_until_the_owner_confirms(self):
        taken, _ = self.run_cli("snapshot")
        self.start_result = self.game()
        with mock.patch.object(gate, "sample_gpu", return_value=[gate.GpuSample(95, 9000, 10240)] * 5):
            out, code = self.launch(taken["id"], "-debug_mode")
            self.assertEqual((code, out["refused"], self.starts), (2, "gpu_busy", []))
            out, code = self.launch(taken["id"], "-debug_mode", flags=("--owner-confirmed-busy",))
        self.assertEqual((code, len(self.starts)), (0, 1))

    def test_launch_refuses_an_unattended_run_without_an_end_date(self):
        # An unattended run without an end date once wrote autosaves over the owner's (spec § 5.3).
        taken, _ = self.run_cli("snapshot")
        self.start_result = self.game()
        for args in (("-debug_mode", "-handsoff", "-start_tag=GBR"), ("-handsoff", "-run_until=")):
            with self.subTest(args=args):
                out, code = self.launch(taken["id"], *args)
                self.assertEqual((code, out["refused"]), (2, "no_end_date"))
        self.assertEqual(self.starts, [])
        self.assertEqual(self.launch(taken["id"], "-debug_mode", "-handsoff", "-run_until=1836.2.10")[1], 0)

    def test_launch_refuses_an_argument_it_cannot_pass_before_claiming_the_snapshot(self):
        # Break-it review 2026-11-10, (7): a lone surrogate failed inside the start, after the checks. A NUL could
        # cut an argument short on the Windows side, after the end-date check had read all of it.
        taken, _ = self.run_cli("snapshot")
        self.start_result = self.game()
        for args in (("-loadsave=\udcff",), ("-handsoff\x00x",), ("-debug_mode\n",)):
            with self.subTest(args=args):
                out, code = self.launch(taken["id"], *args)
                self.assertEqual((code, out["refused"], out["id"]), (2, "bad_argument", taken["id"]))
        self.assertEqual(self.starts, [])
        self.assertFalse((self.the_snapshot().dir / cli.LAUNCH_CLAIM).exists())
        self.assertEqual(self.launch(taken["id"], "-debug_mode")[1], 0)

    def test_launch_refuses_a_snapshot_not_armed_already_started_or_finished(self):
        self.start_result = self.game()
        out, code = self.launch(snapshot.take(self.user, self.backups).id, "-debug_mode")
        self.assertEqual((code, out["refused"]), (2, "not_armed"))
        snap = self.armed_snapshot(dt.datetime.now(UTC))
        snapshot.record(snap, "started", pid=MINE.pid, created=MINE.created)
        out, code = self.launch(snap.id, "-debug_mode")
        self.assertEqual((code, out["refused"]), (2, "already_started"))
        snapshot.record(snap, "game_exited")
        snapshot.record(snap, "restored")
        out, code = self.launch(snap.id, "-debug_mode")
        self.assertEqual((code, out["refused"]), (2, "already_finished"))
        self.assertEqual(self.starts, [])

    def test_launch_refuses_a_snapshot_the_owner_has_played_over(self):
        # The session that took the snapshot died before launching, and the owner has played since. A start
        # recorded now would date their writes before the run, and restore would put the old copies back.
        snap, _owner = self.run_an_hour_ago(started=False)
        self.owner_writes("save games/autosave.v3", b"the owner's own game", minutes_ago=30)
        self.owner_writes("save games/autosave_1.v3", b"the owner's new autosave", minutes_ago=30)
        self.owner_writes("continue_game.json", b'{"title": "autosave"}', minutes_ago=30)
        before = self.tree()
        self.start_result = self.game()
        out, code = self.launch(snap.id, "-debug_mode")
        self.assertEqual((code, out["refused"]), (2, "stale_snapshot"))
        self.assertEqual(out["files"], ["continue_game.json", "save games/autosave.v3", "save games/autosave_1.v3"])
        self.assertIn("unless the only change is a missing file", out["detail"])
        self.assertEqual((self.starts, self.events()), ([], ["armed"]))
        self.assertEqual(self.tree(), before)

    def test_launch_refuses_a_snapshot_whose_logs_the_owner_has_written_since(self):
        # Break-it replay 2026-11-10, s1_orders "logs_only": the owner opened the game after a dead session's
        # snapshot and quit without saving. `launch` passed, since the check skipped logs/; the run's game then
        # wrote over their debug.log, and `recover` put the snapshot's older copy back.
        snap, _owner = self.run_an_hour_ago(started=False)
        self.owner_writes("logs/debug.log", b"the owner's session log, at exit\n", minutes_ago=30)
        before = self.tree()
        self.start_result = self.game()
        out, code = self.launch(snap.id, "-debug_mode")
        self.assertEqual((code, out["refused"], out["files"]), (2, "stale_snapshot", ["logs/debug.log"]))
        self.assertEqual((self.starts, self.events()), ([], ["armed"]))
        out, code = self.run_cli("recover")                         # the remedy the refusal names
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]), (0, [(snap.id, False, "")]))
        self.assertEqual(self.tree(), before)

    def test_launch_refuses_when_the_game_is_not_where_base_game_path_says(self):
        taken, _ = self.run_cli("snapshot")
        self.start_result = self.game()
        (self.base_game / "binaries" / "victoria3.exe").unlink()
        out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["refused"], self.starts, self.events()), (2, "no_game_binary", [], ["armed"]))

    def test_launch_reports_the_pid_it_started_when_the_start_cannot_be_recorded(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        self.start_result = game
        record = snapshot.record

        def failing(snap, event, *a, **k):
            if event == "started":
                raise OSError("the backup drive went away")
            return record(snap, event, *a, **k)

        with mock.patch.object(snapshot, "record", side_effect=failing):
            out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["refused"], out["pid"], out["id"]), (2, "not_recorded", game.pid, taken["id"]))
        self.assertIn(f"only while the game listing shows pid {game.pid} with start time {game.created}", out["detail"])

    def test_launch_after_another_session_recovered_the_snapshot_refuses_and_starts_nothing(self):
        taken, _ = self.run_cli("snapshot")
        self.assertEqual(self.run_cli("recover")[1], 0)          # another session, between snapshot and launch
        self.start_result = self.game()
        out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["refused"]), (2, "already_finished"))
        self.assertEqual(self.starts, [])

    def started_entries(self):
        return [e for e in snapshot.journal(self.the_snapshot()) if e["event"] == "started"]

    def test_launch_records_an_unknown_start_time_once_and_never_looks_it_up(self):
        # Break-it review 2026-11-10, (9a): the look-up matched by pid alone, so a victoria3.exe that took the
        # run's pid within ten seconds was recorded as the run's game, and `watch` then followed it.
        taken, _ = self.run_cli("snapshot")
        self.start_result = gate.ProcId(4242, "unknown")
        impostor = self.game(pid=4242, seconds_from_now=4)
        looks_after_the_start = []

        def looking(*a, **k):
            if self.starts:
                looks_after_the_start.append(1)
                return [impostor]
            return []

        with mock.patch.object(gate, "list_games", side_effect=looking):
            out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["created"]), (0, "unknown"))
        self.assertIn("start time", out["detail"])
        self.assertEqual(looks_after_the_start, [])
        self.assertEqual([(e["pid"], e["created"]) for e in self.started_entries()], [(4242, "unknown")])
        self.games = [[impostor], [impostor], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "unknown_start"))
        self.assertEqual(self.events(), ["armed", "started"])

    def test_two_launches_of_one_snapshot_start_one_game(self):
        # Break-it review 2026-11-10, (5c): two `launch` calls on one id both passed their checks during the
        # one PowerShell start, and both started a game.
        taken, _ = self.run_cli("snapshot")
        live = self.game(pid=1111, seconds_from_now=1)
        second = {}

        def start():                     # the other `launch` runs while this one's game is starting
            self.start_result = live
            second["reply"] = self.launch(taken["id"], "-debug_mode")
            return live

        self.start_result = start
        out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["pid"]), (0, live.pid))
        # Round 5: the lock refuses the second first; the claim would refuse it as already_started.
        self.assertEqual((second["reply"][1], second["reply"][0]["refused"]), (2, "busy"))
        self.assertEqual(len(self.starts), 1)
        self.assertEqual([e["pid"] for e in self.started_entries()], [live.pid])

    def test_a_claim_without_a_recorded_start_is_a_launch_whose_record_was_lost(self):
        taken, _ = self.run_cli("snapshot")
        claim = self.the_snapshot().dir / cli.LAUNCH_CLAIM
        claim.write_text("4242\n")
        old = time.time() - cli.LAUNCH_IN_FLIGHT_S - 30          # no `launch` is still on its way to the record
        os.utime(claim, (old, old))
        self.start_result = self.game()
        out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["refused"], self.starts), (2, "already_started", []))
        unrecorded = self.game(pid=5555)
        self.games = [[unrecorded], [unrecorded], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "not_recorded"))
        self.assertEqual(self.events(), ["armed"])                  # nothing adopted
        before = self.tree()
        self.games = [unrecorded]
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "other_game_running"))
        self.assertEqual(self.tree(), before)

    def test_restore_and_recover_give_no_verdict_while_a_launch_is_in_flight(self):
        # The third round's concern 2: between `launch`'s claim and its `started`, the game may not be listed yet;
        # `recover` saw nothing, recorded `restored`, and the run's writes were then left unrestored.
        taken, _ = self.run_cli("snapshot")
        (self.the_snapshot().dir / cli.LAUNCH_CLAIM).write_text("1\n")          # just made
        (self.user / "continue_game.json").write_text('{"title": "the run, loading"}')
        before = self.tree()
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["refused"], out["id"]), (2, False, "launch_in_flight", taken["id"]))
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(taken["id"], False, "launch_in_flight")]))
        self.assertEqual(self.events(), ["armed"])
        self.assertEqual(self.tree(), before)

    def test_a_launch_whose_start_lands_just_after_such_a_refusal_proceeds_normally(self):
        taken, _ = self.run_cli("snapshot")
        before = self.tree()
        game = self.game(seconds_from_now=1)
        replies = {}

        def start():                     # another session runs `restore` and `recover` while the game starts
            replies["restore"] = self.run_cli("restore", taken["id"])
            replies["recover"] = self.run_cli("recover")
            return game

        self.start_result = start
        out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["pid"]), (0, game.pid))
        self.start_result = None
        # Round 5: `launch` holds the lock until `started` is recorded, so both wait their turn.
        self.assertEqual((replies["restore"][0]["refused"], replies["recover"][0]["refused"]), ("busy", "busy"))
        self.assertEqual(self.events(), ["armed", "started"])
        self.games = [[game], [game], []]
        self.assertEqual(self.run_cli("watch", taken["id"])[1], 0)
        self.games = []
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"]), (0, False))
        self.assertEqual(self.events(), ["armed", "started", "watching", "heartbeat", "game_exited", "restored"])
        self.assertEqual(self.tree(), before)

    def test_an_old_claim_with_no_start_is_judged_as_a_snapshot_nothing_was_launched_under(self):
        old = time.time() - cli.LAUNCH_IN_FLIGHT_S - 30
        for case, games, change, verb, expected in (
                ("a game is up", [self.game(pid=5555)], None, "restore", (2, True, "other_game_running")),
                ("a file changed", [], "continue_game.json", "restore", (2, True, "no_reference_time")),
                ("nothing changed", [], None, "restore", (0, False, "")),
                ("nothing changed, by recover", [], None, "recover", (0, False, ""))):
            with self.subTest(case=case):
                snap = self.armed_snapshot(dt.datetime.now(UTC) - dt.timedelta(minutes=20))
                claim = snap.dir / cli.LAUNCH_CLAIM
                claim.write_text("1\n")
                os.utime(claim, (old, old))
                if change:
                    (self.user / change).write_text('{"title": "%s"}' % case)
                self.games = games
                if verb == "restore":
                    out, code = self.run_cli("restore", snap.id)
                    self.assertEqual((code, out["held"], out["reason"]), expected)
                else:
                    out, code = self.run_cli("recover")
                    self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                                     (expected[0], [(snap.id, *expected[1:])]))

    # -- the owner's own saves (#1725) ----------------------------------------
    # A save of the owner's that the run neither loads nor makes is never copied. `restore` compares it by the size
    # and time the snapshot listed. Files the run changes here get a fixed old time, so that no hold rule compares
    # them with a clock (#1648).

    OWNERS_SAVE = "save games/byzantium_1942_01_27.v3"

    def the_run_writes(self, rel, data):
        path = self.user / rel
        path.write_bytes(data)
        os.utime(path, ns=(1_700_000_000 * 10**9, 1_700_000_000 * 10**9))

    def test_restore_puts_the_rest_back_then_holds_for_a_save_the_run_overwrote(self):
        (self.user / self.OWNERS_SAVE).write_bytes(b"the owner's game of October")

        def the_run():
            self.the_run_writes("continue_game.json", b'{"title": "the run"}')
            (self.user / self.OWNERS_SAVE).write_bytes(b"saved over from the game's menu")

        snap_id = self.launched_run(the_run)
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "manual_save_changed"), self.why(out))
        self.assertEqual((out["restored"], out["manual_saves"]), (["continue_game.json"], {"changed": [self.OWNERS_SAVE]}))
        self.assertEqual((self.user / "continue_game.json").read_text(), '{"title": "autosave_exit"}')
        self.assertEqual((self.user / self.OWNERS_SAVE).read_bytes(), b"saved over from the game's menu")
        self.assertEqual(self.run_cli("held")[0], {"held": [snap_id]})
        again, code = self.run_cli("restore", snap_id)               # nothing can put the save back: held again
        self.assertEqual((code, again["held"], again["reason"], again["restored"]), (2, True, "manual_save_changed", []))

    def test_restore_leaves_a_new_save_where_it_is_and_lists_it(self):
        snap_id = self.launched_run(lambda: self.the_run_writes("save games/france_1836_01_02.v3", b"a new save"))
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["reason"]), (0, False, ""), self.why(out))
        self.assertEqual(out["manual_saves"], {"new": ["save games/france_1836_01_02.v3"]})
        self.assertTrue((self.user / "save games/france_1836_01_02.v3").is_file())
        self.assertEqual(self.events()[-1], "restored")

    def test_recover_holds_a_started_run_for_a_save_it_deleted(self):
        snap, _owner = self.run_an_hour_ago()
        (self.user / "save games/new york_1940_07_29.v3").unlink()
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(snap.id, True, "manual_save_changed")]))
        self.assertEqual(out["runs"][0]["manual_saves"], {"missing": ["save games/new york_1940_07_29.v3"]})

    def test_a_snapshot_nothing_was_launched_under_compares_no_save(self):
        # With no `started`, no session verb ever reached a game: the saves are whoever played since, as the logs are.
        for verb in ("restore", "recover"):
            with self.subTest(verb=verb):
                (self.user / "save games/new york_1940_07_29.v3").write_bytes(b"a named save")
                taken, _ = self.run_cli("snapshot")
                (self.user / "save games/new york_1940_07_29.v3").unlink()
                (self.user / "save games/the_owners_new.v3").write_bytes(b"saved since")
                out, code = self.run_cli(*((verb, taken["id"]) if verb == "restore" else (verb,)))
                reply = out if verb == "restore" else out["runs"][-1]
                self.assertEqual((code, reply["held"], reply["reason"]), (0, False, ""))
                self.assertNotIn("manual_saves", reply)
                (self.user / "save games/the_owners_new.v3").unlink()

    def test_selftest_restore_is_not_held_by_the_owners_saves(self):
        # It restores into an empty scratch folder, where every save of the owner's would read as gone.
        self.assertNotIn("save games/new york_1940_07_29.v3", snapshot.take(self.user, self.backups).files)
        out, code = self.run_cli("selftest-restore")
        self.assertEqual((code, out["match"]), (0, True))
        self.assertEqual(restore.held(self.backups), [])

    # -- the lock -------------------------------------------------------------
    # Round 5 ruling: the verbs that change things take turns, so that no check-then-act of one session can
    # interleave with another's. The pre-claim window (scratch replay r4_preclaim): a `recover` run inside
    # launch's last process listing, before its claim, recorded `restored`; the launch then started the game,
    # `started` landed after the verdict, and the run was never restored.

    def hold_the_lock(self, verb="restore", minutes_ago=0.0):
        """Another session's lock, taken that many minutes ago."""
        self.backups.mkdir(exist_ok=True)
        lock = self.backups / cli.LOCK_NAME
        lock.write_text(json.dumps({"verb": verb, "pid": 1, "token": "theirs"}) + "\n")
        when = time.time() - minutes_ago * 60
        os.utime(lock, (when, when))
        return lock

    def test_every_verb_that_changes_things_refuses_busy_while_another_holds_the_lock(self):
        taken, _ = self.run_cli("snapshot")
        before, count = self.tree(), len(snapshot.all_snapshots(self.backups))
        lock = self.hold_the_lock("launch")
        self.start_result = self.game()
        for argv in (("snapshot",), ("restore", taken["id"]), ("recover",), ("selftest-restore",),
                     ("launch", taken["id"], "--permission", "session grant", "--", "-debug_mode")):
            with self.subTest(verb=argv[0]):
                out, code = self.run_cli(*argv)
                self.assertEqual((code, out["refused"], out["holder"]), (2, "busy", "launch"))
                self.assertLess(out["age_s"], 60)
        self.assertEqual((self.tree(), self.events(), self.starts), (before, ["armed"], []))
        self.assertEqual(len(snapshot.all_snapshots(self.backups)), count)
        self.assertEqual(lock.read_text(), json.dumps({"verb": "launch", "pid": 1, "token": "theirs"}) + "\n")

    def test_watch_gate_and_held_run_while_the_lock_is_held(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        snapshot.record(self.the_snapshot(), "started", pid=game.pid, created=game.created)
        self.hold_the_lock("recover")
        self.games = [[game], [game], []]
        self.assertEqual(self.run_cli("watch", taken["id"])[1], 0)
        self.games = []
        out, code = self.run_cli("gate", "--permission", "session grant")
        self.assertEqual((code, out["ok"]), (0, True))
        self.assertEqual(self.run_cli("held")[1], 0)

    def test_the_lock_is_released_after_a_success_a_refusal_and_an_exception(self):
        lock = self.backups / cli.LOCK_NAME
        taken, code = self.run_cli("snapshot")
        self.assertEqual((code, lock.exists()), (0, False))
        out, code = self.run_cli("snapshot")
        self.assertEqual((code, out["refused"], lock.exists()), (2, "unfinished_run", False))
        self.games = [gate.GateError("the process listing did not finish")]
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["refused"], lock.exists()), (2, "GateError", False))
        self.games = []

        def start_breaks():
            raise RuntimeError("something nobody expected")

        self.start_result = start_breaks                    # an exception from inside `launch`, after its claim
        out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["refused"], lock.exists()), (2, "RuntimeError", False))

    def test_a_lock_older_than_fifteen_minutes_is_broken_and_a_younger_one_is_not(self):
        taken, _ = self.run_cli("snapshot")
        self.hold_the_lock("launch", minutes_ago=14)
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "busy"))
        self.hold_the_lock("launch", minutes_ago=16)              # its process died
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"]), (0, False))
        self.assertFalse((self.backups / cli.LOCK_NAME).exists())

    def test_a_stale_lock_another_session_is_breaking_is_left_to_it(self):
        taken, _ = self.run_cli("snapshot")
        lock = self.hold_the_lock("launch", minutes_ago=16)
        (self.backups / cli.LOCK_BREAK_NAME).write_text("")         # another session is breaking it
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "busy"))
        self.assertTrue(lock.exists())
        self.assertEqual(self.events(), ["armed"])

    def test_a_recover_during_a_launch_is_busy_and_one_before_it_makes_the_launch_refuse(self):
        taken, _ = self.run_cli("snapshot")
        before = self.tree()
        game = self.game(seconds_from_now=1)
        replies = []
        self.on_look = [lambda: replies.append(self.run_cli("recover")[0])]   # at every listing, the last one too
        self.start_result = game
        out, code = self.launch(taken["id"], "-debug_mode")
        self.on_look = []
        self.assertEqual((code, out["pid"]), (0, game.pid))
        self.assertEqual(len(replies), 2)                               # launch's two listings
        self.assertEqual([r["refused"] for r in replies], ["busy", "busy"])
        self.assertEqual(self.events(), ["armed", "started"])
        self.games = [[game], [game], []]
        self.assertEqual(self.run_cli("watch", taken["id"])[1], 0)
        self.games = []
        self.assertEqual(self.run_cli("restore", taken["id"])[1], 0)
        self.assertEqual(self.tree(), before)
        # A `recover` that finished before the launch took the lock: the launch reads its verdict and refuses.
        second, _ = self.run_cli("snapshot")
        self.assertEqual(self.run_cli("recover")[1], 0)
        self.starts.clear()
        out, code = self.launch(second["id"], "-debug_mode")
        self.assertEqual((code, out["refused"], self.starts), (2, "already_finished", []))

    def test_an_unattended_run_needs_an_end_date_in_any_spelling(self):
        # Break-it review 2026-11-10, (8): `--handsoff`, `/handsoff` and `-handsoff=1` went through without an end
        # date, as did `-run_until=never`.
        # Final touches: of the end date, only the spelling probed against the game counts.
        refused = (["-handsoff"], ["--handsoff"], ["-HANDSOFF"], ["/handsoff"], ["-handsoff=1"],
                   ["-debug_mode -handsoff"], ["-handsoff", "-run_until"], ["-handsoff", "-run_until="],
                   ["-handsoff", "-run_until= "], ["-handsoff", "-run_until=never"],
                   ["-handsoff", "-run_until", "1836.2.10"], ["-handsoff", "-run_until=1836.2.10 -foo"],
                   ["-handsoff", "-run_until=1836.2"], ["-handsoff", "-run_until=18361.2.10"],
                   ["-handsoff", "-RUN_UNTIL=1836.2.10"], ["--handsoff", "--run_until=1836.12.31"],
                   ["/handsoff=1", "/run_until=9.1.1"], ["-handsoff", " -run_until=1836.2.10"])
        allowed = (["-debug_mode"], ["-handsoff", "-run_until=1836.2.10"], ["--handsoff", "-run_until=1836.12.31"],
                   ["/HANDSOFF=1", "-run_until=9.1.1"])
        for args in refused:
            with self.subTest(args=args):
                with self.assertRaises(cli._Refused) as raised:
                    cli._check_end_date(args)
                self.assertEqual(raised.exception.result["refused"], "no_end_date")
        for args in allowed:
            with self.subTest(args=args):
                cli._check_end_date(args)

    # -- watch ----------------------------------------------------------------

    def test_watch_adopts_no_game_and_restore_keeps_every_file_of_the_owners(self):
        # Re-review 2026-11-10: a snapshot armed by a session that died; the owner started their own game five
        # minutes later and played. A later `watch` with no --pid adopted it, and `restore` then put the
        # snapshot's autosave.v3 and continue_game.json back over the owner's and removed their autosave_1.v3.
        armed = dt.datetime.now(UTC) - dt.timedelta(minutes=10)
        snap = self.armed_snapshot(armed)
        owner = gate.ProcId(99, iso(armed + dt.timedelta(seconds=300)))
        self.owner_writes("save games/autosave.v3", b"the owner's progress", minutes_ago=1)
        self.owner_writes("save games/autosave_1.v3", b"the owner's new autosave", minutes_ago=1)
        self.owner_writes("continue_game.json", b'{"title": "the owner"}', minutes_ago=1)
        before = self.tree()
        self.games = [[owner], [owner], [owner], []]
        out, code = self.run_cli("watch", snap.id)
        self.assertEqual((code, out["refused"], out["id"]), (2, "not_started", snap.id))
        self.assertIn("start the game with `launch", out["detail"])
        self.assertEqual(self.events(), ["armed"])
        self.games = [owner]
        out, code = self.run_cli("restore", snap.id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "other_game_running"))
        self.games = []
        out, code = self.run_cli("restore", snap.id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "no_reference_time"))
        self.assertEqual(self.tree(), before)

    # The 2026-11-10 review's C1 (1) and (2): a second `watch` after the run's game had exited adopted the game
    # the owner started later, and `restore` put the snapshot's copy over the owner's save or removed theirs.

    def test_a_second_watch_after_the_run_exited_adopts_nothing_and_the_owners_save_is_kept(self):
        snap, owner = self.run_an_hour_ago()
        self.owner_writes("save games/autosave.v3", b"the owner's own game, 30 minutes ago", minutes_ago=30)
        before = self.tree()
        self.games = [[owner], [owner], []]
        out, code = self.run_cli("watch", snap.id)
        self.assertEqual((code, out["refused"]), (2, "already_exited"))
        self.assertEqual(self.events(), ["armed", "started", "game_exited"])
        self.games = [owner]
        out, code = self.run_cli("gate", "--permission", "session grant", "--owner-confirmed-busy")
        self.assertEqual((code, out["reason"]), (2, "other_game"))
        self.games = []
        out, code = self.run_cli("restore", snap.id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "modified_after_exit"))
        self.assertEqual(self.tree(), before)

    def test_a_second_watch_after_the_run_exited_adopts_nothing_and_a_save_the_owner_added_stays(self):
        snap, owner = self.run_an_hour_ago()
        self.owner_writes("save games/autosave_1.v3", b"the owner's new autosave", minutes_ago=30)
        before = self.tree()
        self.games = [[owner], [owner], []]
        out, code = self.run_cli("watch", snap.id)
        self.assertEqual((code, out["refused"]), (2, "already_exited"))
        self.games = []                                             # the owner has closed their game
        out, code = self.run_cli("restore", snap.id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "modified_after_exit"))
        self.assertEqual(self.tree(), before)

    def test_watch_follows_the_recorded_game_and_records_no_second_start(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        snapshot.record(self.the_snapshot(), "started", pid=game.pid, created=game.created)
        snapshot.record(self.the_snapshot(), "heartbeat")
        self.games = [[game], [game], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["heartbeats"], out["pid"]), (0, 1, game.pid))
        self.assertEqual(self.events(), ["armed", "started", "heartbeat", "watch_resumed", "heartbeat", "game_exited"])

    def test_watch_records_no_exit_for_a_recorded_game_gone_at_its_first_look(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        snapshot.record(self.the_snapshot(), "started", pid=game.pid, created=game.created,
                        now=dt.datetime.now(UTC) - dt.timedelta(seconds=30))
        another = self.game(pid=99, seconds_from_now=120)           # a new game, but not the recorded one
        self.games = [[another], [another], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "game_gone_unrecorded"))
        self.assertIn("last heartbeat", out["detail"])
        self.assertEqual(self.events(), ["armed", "started", "watching", "other_game"])   # the first look too
        self.games = []
        later = dt.datetime.now(UTC) + dt.timedelta(seconds=20)       # past `watching`, a sign of life
        with mock.patch.object(snapshot, "_drive_clock", lambda folder: later):
            out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "other_game_ran"))

    def test_watch_refuses_a_recorded_start_it_cannot_read(self):
        taken, _ = self.run_cli("snapshot")
        snapshot.record(self.the_snapshot(), "started", created="2026-11-10T12:00:00.0000000Z")   # no pid
        game = self.game()
        self.games = [[game], [game], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "unreadable_start"))
        self.assertEqual(self.events(), ["armed", "started"])

    def test_watch_keeps_looking_when_a_look_fails(self):
        # Review 2026-11-10, I1: one look that failed read as "the game is gone".
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        snapshot.record(self.the_snapshot(), "started", pid=game.pid, created=game.created)
        failed = gate.GateError("powershell.exe exited 1 with nothing on stdout")
        unreadable = gate.ProcId(game.pid, "unknown")              # its start time, unreadable for a moment
        self.games = [[game], failed, [game], [unreadable], failed, [game], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["heartbeats"]), (0, 2))
        self.assertEqual(self.events(), ["armed", "started", "watching", "look_failed", "heartbeat", "look_failed",
                                         "look_failed", "heartbeat", "game_exited"])
        # Round 4 ruling: during a failed look nobody saw whether another game ran, so nothing vouches for the files.
        before = self.tree()
        self.games = []
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "unwatched_stretch"))
        self.assertEqual(self.tree(), before)

    def test_watch_records_no_exit_when_a_look_failed_since_the_last_heartbeat(self):
        # Break-it review 2026-11-10, (10): four failed looks after the run's game exited, during which the owner
        # played and quit; the next look stamped game_exited after their writes, and restore undid them. Here
        # the journal's clock is the naps' (five seconds each), so times are as far apart as they would be.
        taken, _ = self.run_cli("snapshot")
        game = self.game(seconds_from_now=-1)
        self.start_result = game
        self.launch(taken["id"], "-debug_mode")
        self.start_result = None
        base = dt.datetime.now(UTC).replace(microsecond=0) + dt.timedelta(seconds=5)
        failed = gate.GateError("the listing did not finish")
        naps = []

        def the_owner_plays():
            naps.append(1)
            if len(naps) == 2:           # after the look that last saw the run's game
                when = (base + dt.timedelta(seconds=self.clock)).timestamp()
                for rel, data in (("save games/autosave_1.v3", b"the owner's new autosave"),
                                  ("save games/autosave.v3", b"the owner's progress")):
                    (self.user / rel).write_bytes(data)
                    os.utime(self.user / rel, (when, when))

        self.on_nap = [the_owner_plays]
        self.games = [[game], [game], failed, failed, failed, failed, []]
        with mock.patch.object(snapshot, "_drive_clock", lambda folder: base + dt.timedelta(seconds=self.clock)):
            out, code = self.run_cli("watch", taken["id"])
            self.on_nap = []
            self.assertEqual((code, out["refused"]), (2, "game_gone_unrecorded"))
            self.assertEqual(self.events(), ["armed", "started", "watching", "heartbeat"] + ["look_failed"] * 4)
            before = self.tree()
            self.games = []
            out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "unwatched_stretch"))
        self.assertEqual(self.tree(), before)

    def test_watch_refuses_an_interval_longer_than_ten_seconds(self):
        # Break-it review 2026-11-10, (10): with --interval 600 the exit was stamped up to ten minutes late.
        taken, _ = self.run_cli("snapshot")
        for interval in ("600", "10.5", "0", "-1"):
            with self.subTest(interval=interval):
                out, code = self.run_cli("watch", taken["id"], "--interval", interval)
                self.assertEqual((code, out["refused"], out["id"]), (2, "bad_interval", taken["id"]))
        self.assertEqual(self.events(), ["armed"])

    def test_watch_records_another_game_and_restore_holds_without_touching_the_owners_files(self):
        # Break-it review 2026-11-10, (x): the owner started a second game while the run's game ran, played and
        # quit first; restore judged their writes as the run's, removed their autosave_1.v3 with no copy kept and
        # overwrote their continue_game.json.
        taken, _ = self.run_cli("snapshot")
        run = self.game(seconds_from_now=-1)
        owner = self.game(pid=99, seconds_from_now=10)
        self.start_result = run
        self.launch(taken["id"], "-debug_mode")
        self.start_result = None
        naps = []

        def the_owner_plays():
            naps.append(1)
            if len(naps) == 3:
                (self.user / "save games" / "autosave_1.v3").write_bytes(b"the owner's own new autosave")
                (self.user / "continue_game.json").write_text('{"title": "the owner"}')

        self.on_nap = [the_owner_plays]
        self.games = [[run], [run, owner], [run, owner], [run, owner], [run], [run], []]
        out, code = self.run_cli("watch", taken["id"])
        self.on_nap = []
        self.assertEqual(code, 0)
        journal = snapshot.journal(self.the_snapshot())
        self.assertEqual([(e["pid"], e["created"]) for e in journal if e["event"] == "other_game"],
                         [(owner.pid, owner.created)])                       # once, though seen three times
        before = self.tree()
        self.games = []
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "other_game_ran"))
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.events()[-1], "held")

    def test_watch_stops_without_recording_an_exit_after_five_failed_looks(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        snapshot.record(self.the_snapshot(), "started", pid=game.pid, created=game.created)
        self.games = [[game], [game], gate.GateError("no PowerShell")]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"], out["heartbeats"]), (2, "cannot_look", 1))
        self.assertEqual(self.events(), ["armed", "started", "watching", "heartbeat"] + ["look_failed"] * 5)
        # Once PowerShell answers again, `watch` picks the run up where it was.
        self.games = [[game], []]
        self.assertEqual(self.run_cli("watch", taken["id"])[1], 0)
        self.assertEqual(self.events()[-2:], ["watch_resumed", "game_exited"])
        # Round 4 ruling: while it could not look, nobody saw whether another game ran: the run is held.
        (self.user / "continue_game.json").write_text('{"title": "whose?"}')
        before = self.tree()
        self.games = []
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "unwatched_stretch"))
        self.assertEqual(self.tree(), before)

    def test_a_watch_resumed_after_a_long_gap_leads_to_a_hold(self):
        # Round 4 ruling on the third round's concern 1: the session's `watch` died; the owner started a game of
        # their own beside the run's, played and quit; a later `watch` saw the run's game alive and recorded its
        # exit after the owner's writes, and restore put the snapshot's copy back over them.
        taken, _ = self.run_cli("snapshot")
        game = self.game(seconds_from_now=-120)
        long_ago = dt.datetime.now(UTC) - dt.timedelta(seconds=90)
        for event, fields in (("started", {"pid": game.pid, "created": game.created}), ("watching", {"gap_s": 1}),
                              ("heartbeat", {})):
            snapshot.record(self.the_snapshot(), event, now=long_ago, **fields)
        self.owner_writes("continue_game.json", b'{"title": "the owner"}', minutes_ago=0.5)   # inside the gap
        self.games = [[game], [game], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual(code, 0)
        resumed = [e for e in snapshot.journal(self.the_snapshot()) if e["event"] == "watch_resumed"]
        self.assertEqual(len(resumed), 1)
        self.assertGreaterEqual(resumed[0]["gap_s"], 85)
        before = self.tree()
        self.games = []
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "unwatched_stretch"))
        self.assertEqual(self.tree(), before)

    def test_a_watch_resumed_within_fifteen_seconds_restores_as_before(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game(seconds_from_now=-30)
        with self.naps_clock() as now:      # the gap is the drive clock's time since `lately` (#1648)
            lately = now() - dt.timedelta(seconds=5)
            for event, fields in (("started", {"pid": game.pid, "created": game.created}),
                                  ("watching", {"gap_s": 1}), ("heartbeat", {})):
                snapshot.record(self.the_snapshot(), event, now=lately, **fields)
            self.games = [[game], [game], []]
            self.assertEqual(self.run_cli("watch", taken["id"])[1], 0)
            resumed = [e for e in snapshot.journal(self.the_snapshot()) if e["event"] == "watch_resumed"]
            self.assertEqual([e["gap_s"] for e in resumed], [5.0])
            self.games = []
            out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"]), (0, False), self.why(out))
        self.assertEqual(self.events()[-1], "restored")

    def test_a_first_watch_more_than_two_minutes_after_launch_leads_to_a_hold(self):
        # Final check 2026-11-10: `watch` started two minutes after `launch`; in between the owner's own second
        # instance started, saved and quit; `restore` then judged their writes against the exit and undid them.
        taken, _ = self.run_cli("snapshot")
        launched = dt.datetime.now(UTC) - dt.timedelta(seconds=150)
        game = gate.ProcId(4242, launched.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"))
        snapshot.record(self.the_snapshot(), "started", now=launched, pid=game.pid, created=game.created)
        self.owner_writes("save games/autosave.v3", b"the owner's progress", minutes_ago=1)
        self.owner_writes("save games/autosave_1.v3", b"the owner's new autosave", minutes_ago=1)
        self.owner_writes("continue_game.json", b'{"title": "the owner"}', minutes_ago=1)
        self.games = [[game], [game], []]
        self.assertEqual(self.run_cli("watch", taken["id"])[1], 0)
        watching = [e for e in snapshot.journal(self.the_snapshot()) if e["event"] == "watching"]
        self.assertGreaterEqual(watching[0]["gap_s"], 145)
        before = self.tree()
        self.games = []
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "unwatched_stretch"))
        self.assertEqual(self.tree(), before)

    def test_a_first_watch_within_two_minutes_of_launch_restores_as_before(self):
        taken, _ = self.run_cli("snapshot")
        launched = dt.datetime.now(UTC) - dt.timedelta(seconds=100)
        game = gate.ProcId(4242, launched.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"))
        snapshot.record(self.the_snapshot(), "started", now=launched, pid=game.pid, created=game.created)
        self.games = [[game], [game], []]
        self.assertEqual(self.run_cli("watch", taken["id"])[1], 0)
        self.games = []
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["held"]), (0, False))

    def test_a_first_watch_whose_gap_cannot_be_read_leads_to_a_hold(self):
        taken, _ = self.run_cli("snapshot")
        long_ago = dt.datetime.now(UTC) - dt.timedelta(seconds=30)
        for event, fields in (("started", {"pid": 4242, "created": "2026-11-10T08:00:00.0000000Z"}),
                              ("watching", {"gap_s": None}), ("game_exited", {})):
            snapshot.record(self.the_snapshot(), event, now=long_ago, **fields)
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(taken["id"], True, "unwatched_stretch")]))

    def test_recover_waits_while_a_watch_may_still_be_recording(self):
        # Final touches: `recover` had no such guard; it judged a run whose `watch` was mid-look.
        for newest in ("started", "heartbeat", "watching"):
            with self.subTest(newest=newest):
                snap = self.armed_snapshot(dt.datetime.now(UTC) - dt.timedelta(minutes=5))
                long_ago = dt.datetime.now(UTC) - dt.timedelta(seconds=60)
                snapshot.record(snap, "started", now=long_ago if newest != "started" else None,
                                pid=4242, created="2026-11-10T08:00:00.0000000Z")
                if newest != "started":
                    snapshot.record(snap, newest, **({"gap_s": 1} if newest == "watching" else {}))
                (self.user / "continue_game.json").write_text('{"title": "%s"}' % newest)
                before, events = self.tree(), [e["event"] for e in snapshot.journal(snap)]
                out, code = self.run_cli("recover")
                self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                                 (2, [(snap.id, False, "watch_still_recording")]))
                self.assertEqual((self.tree(), [e["event"] for e in snapshot.journal(snap)]), (before, events))
                snapshot.record(snap, "held", reason="test cleanup")      # out of the next subtest's way

    def test_a_start_whose_reply_was_lost_is_refused_as_unconfirmed(self):
        taken, _ = self.run_cli("snapshot")

        def lost():
            raise gate.GateError("powershell.exe timed out after 60 s")

        self.start_result = lost
        out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["refused"], out["id"]), (2, "start_unconfirmed", taken["id"]))
        self.assertIn("stays claimed", out["detail"])
        self.assertEqual(self.events(), ["armed"])

    def test_watch_stops_without_an_exit_when_the_journal_cannot_take_an_entry(self):
        # The third round's concern 3: a write that fails must not let `watch` go on to record an exit.
        game, other = self.game(), self.game(pid=99, seconds_from_now=90)
        original = snapshot.record
        for event, games in (("other_game", [[game], [game, other], []]),
                             ("look_failed", [[game], gate.GateError("no listing"), []]),
                             ("heartbeat", [[game], [game], []])):
            with self.subTest(event=event):
                snap = self.armed_snapshot(dt.datetime.now(UTC))
                original(snap, "started", pid=game.pid, created=game.created)

                def failing(s, ev, *a, _event=event, **k):
                    if ev == _event:
                        raise OSError(28, "No space left on device")
                    return original(s, ev, *a, **k)

                self.games = games
                with mock.patch.object(snapshot, "record", side_effect=failing):
                    out, code = self.run_cli("watch", snap.id)
                self.assertEqual((code, out["refused"], out["id"]), (2, "journal_unwritable", snap.id))
                self.assertNotIn("game_exited", [e["event"] for e in snapshot.journal(snap)])

    def test_every_watch_refusal_carries_the_snapshot_id(self):
        game = self.game()

        def armed(*records):
            snap = self.armed_snapshot(dt.datetime.now(UTC))
            for event, fields in records:
                snapshot.record(snap, event, **fields)
            return snap

        start = ("started", {"pid": game.pid, "created": game.created})
        claimed = armed()
        (claimed.dir / cli.LAUNCH_CLAIM).write_text("1\n")
        cases = [(armed(), [], "not_started"),
                 (claimed, [], "not_recorded"),
                 (armed(("started", {"created": "x"})), [], "unreadable_start"),
                 (armed(("started", {"pid": game.pid, "created": "unknown"})), [[game]], "unknown_start"),
                 (armed(start), [], "game_gone_unrecorded"),
                 (armed(start), [gate.GateError("no listing")], "cannot_look"),
                 (armed(start, ("game_exited", {})), [], "already_exited"),
                 (armed(("restored", {})), [], "already_finished")]
        for snap, games, reason in cases:
            with self.subTest(reason=reason):
                self.games = games
                out, code = self.run_cli("watch", snap.id)
                self.assertEqual((code, out["refused"], out["id"]), (2, reason, snap.id))

    def test_watch_refuses_a_finished_snapshot_and_one_not_taken_for_a_run(self):
        snap_id = self.launched_run()
        self.run_cli("restore", snap_id)
        self.assertEqual(self.run_cli("watch", snap_id)[0]["refused"], "already_finished")
        selftest, _ = self.run_cli("selftest-restore")
        self.assertEqual(self.run_cli("watch", selftest["id"])[0]["refused"], "already_finished")

    # -- nesting ----------------------------------------------------------------

    def test_snapshot_refuses_while_an_earlier_one_is_unrestored(self):
        taken, _ = self.run_cli("snapshot")
        out, code = self.run_cli("snapshot")
        self.assertEqual((code, out["refused"], out["unfinished"]), (2, "unfinished_run", [taken["id"]]))
        self.assertEqual(len(snapshot.all_snapshots(self.backups)), 1)
        self.run_cli("restore", taken["id"])
        self.assertEqual(self.run_cli("snapshot")[1], 0)

    def test_a_held_snapshot_does_not_block_the_next_one(self):
        taken, _ = self.run_cli("snapshot")
        (self.user / "continue_game.json").write_text("{}")
        self.assertTrue(self.run_cli("restore", taken["id"])[0]["held"])
        out, code = self.run_cli("snapshot")
        self.assertEqual((code, out["held"]), (0, [taken["id"]]))

    def test_snapshot_and_selftest_refuse_beside_a_running_game(self):
        # Review 2026-11-10, M2: a snapshot taken while a game writes its files captures them mid-run.
        self.games = [self.game(pid=7, seconds_from_now=-60)]
        for verb in ("snapshot", "selftest-restore"):
            with self.subTest(verb=verb):
                out, code = self.run_cli(verb)
                self.assertEqual((code, out["refused"]), (2, "game_running"))
        self.assertEqual(snapshot.all_snapshots(self.backups), [])

    # -- recover ----------------------------------------------------------------
    # Review 2026-11-10, I2: a snapshot armed for a run that never recorded `started` blocked `snapshot`, and
    # `recover`, which the refusal named, did nothing about it.

    def test_recover_clears_a_snapshot_whose_run_never_started(self):
        taken, _ = self.run_cli("snapshot")
        before = self.tree()
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (0, [(taken["id"], False, "")]))
        self.assertEqual(self.events()[-1], "restored")
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.run_cli("snapshot")[1], 0)

    def test_recover_holds_a_snapshot_whose_run_never_started_when_a_file_changed(self):
        taken, _ = self.run_cli("snapshot")
        (self.user / "continue_game.json").write_text('{"title": "who knows"}')
        before = self.tree()
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(taken["id"], True, "no_reference_time")]))
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.run_cli("snapshot")[1], 0)                  # a held snapshot does not block

    def test_recover_holds_a_snapshot_whose_run_never_started_beside_a_game(self):
        taken, _ = self.run_cli("snapshot")
        self.games = [self.game(pid=99)]
        before = self.tree()
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(taken["id"], True, "other_game_running")]))
        self.assertEqual(self.tree(), before)

    def test_recover_leaves_a_run_whose_game_is_still_up(self):
        taken, _ = self.run_cli("snapshot")
        snapshot.record(self.the_snapshot(), "started", pid=MINE.pid, created=MINE.created)
        (self.user / "continue_game.json").write_text("{}")
        before = self.tree()
        self.games = [MINE]
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(taken["id"], False, "game_still_up")]))
        self.assertEqual(self.events(), ["armed", "started"])
        self.assertEqual(self.tree(), before)

    def test_recover_holds_a_run_whose_pid_now_belongs_to_another_game(self):
        taken, _ = self.run_cli("snapshot")
        snapshot.record(self.the_snapshot(), "started", pid=MINE.pid, created=MINE.created,
                        now=dt.datetime.now(UTC) - dt.timedelta(seconds=30))     # no `watch` still recording
        (self.user / "continue_game.json").write_text("{}")
        before = self.tree()
        self.games = [gate.ProcId(MINE.pid, "2026-11-10T15:00:00.0000000Z")]
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(taken["id"], True, "other_game_running")]))
        self.assertEqual(self.tree(), before)

    def test_recover_leaves_a_snapshot_whose_run_never_started_when_it_cannot_look_for_games(self):
        taken, _ = self.run_cli("snapshot")
        (self.user / "continue_game.json").write_text("{}")
        before = self.tree()
        self.games = [[], gate.GateError("the process listing did not finish")]   # the second look fails
        out, code = self.run_cli("recover")
        self.assertEqual(code, 2)
        self.assertEqual([(r["id"], r["held"]) for r in out["runs"]], [(taken["id"], False)])
        self.assertTrue(out["runs"][0]["reason"].startswith("error: "))
        self.assertEqual(self.events(), ["armed"])
        self.assertEqual(self.tree(), before)

    def test_recover_holds_while_any_game_runs_even_one_of_an_earlier_recorded_start(self):
        # Break-it review 2026-11-10, (5c): with two recorded starts, recover asked "is the run's game up" only about
        # the last, but counted both as the harness's own, and restored while the first one's game was running.
        taken, _ = self.run_cli("snapshot")
        live, dead = self.game(pid=1111), self.game(pid=2222, seconds_from_now=61)
        long_ago = dt.datetime.now(UTC) - dt.timedelta(seconds=30)          # no `watch` still recording
        snapshot.record(self.the_snapshot(), "started", now=long_ago, pid=live.pid, created=live.created)
        snapshot.record(self.the_snapshot(), "started", now=long_ago, pid=dead.pid, created=dead.created)
        (self.user / "continue_game.json").write_text("{}")
        before = self.tree()
        self.games = [live]
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(taken["id"], True, "other_game_running")]))
        self.assertEqual(self.tree(), before)

    def test_recover_holds_a_run_whose_watch_lost_sight_of_the_game(self):
        taken, _ = self.run_cli("snapshot")
        run = self.game()
        long_ago = dt.datetime.now(UTC) - dt.timedelta(seconds=30)
        for event, fields in (("started", {"pid": run.pid, "created": run.created}), ("watching", {"gap_s": 1}),
                              ("look_failed", {"why": "the listing did not finish"}), ("game_exited", {})):
            snapshot.record(self.the_snapshot(), event, now=long_ago, **fields)
        (self.user / "continue_game.json").write_text('{"title": "whose?"}')
        before = self.tree()
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(taken["id"], True, "unwatched_stretch")]))
        self.assertEqual(self.events()[-1], "held")
        self.assertEqual(self.tree(), before)

    def test_recover_holds_a_run_during_which_another_game_ran(self):
        taken, _ = self.run_cli("snapshot")
        run, owner = self.game(), self.game(pid=99)
        long_ago = dt.datetime.now(UTC) - dt.timedelta(seconds=30)
        for event, fields in (("started", {"pid": run.pid, "created": run.created}),
                              ("other_game", {"pid": owner.pid, "created": owner.created}), ("game_exited", {})):
            snapshot.record(self.the_snapshot(), event, now=long_ago, **fields)
        before = self.tree()
        out, code = self.run_cli("recover")
        self.assertEqual((code, [(r["id"], r["held"], r["reason"]) for r in out["runs"]]),
                         (2, [(taken["id"], True, "other_game_ran")]))
        self.assertEqual(self.events()[-1], "held")
        self.assertEqual(self.tree(), before)

    def test_restore_leaves_the_logs_alone_when_nothing_was_launched(self):
        # Break-it review 2026-11-10, (1): with no `started`, the logs are whoever played since, not a run's: restore
        # put the snapshot's debug.log back over the owner's later one and removed their new error.log.
        armed = dt.datetime.now(UTC) - dt.timedelta(minutes=20)
        for verb in ("restore", "recover"):
            with self.subTest(verb=verb):
                snap = self.armed_snapshot(armed)
                self.owner_writes("logs/debug.log", b"the owner's session log, at exit\n", minutes_ago=1)
                self.owner_writes("logs/error.log", b"the owner's new error log\n", minutes_ago=1)
                before = self.tree()
                out, code = self.run_cli(*((verb, snap.id) if verb == "restore" else (verb,)))
                self.assertEqual(code, 0)
                self.assertEqual(self.tree(), before)
                self.assertFalse((snap.dir / "run_logs").exists())
                (self.user / "logs" / "error.log").unlink()
                (self.user / "logs" / "debug.log").write_text("the owner's log\n")

    # -- every failure is one JSON object -----------------------------------------

    def test_every_verb_that_looks_for_games_refuses_in_json_when_it_cannot(self):
        failed = gate.GateError("the process listing did not finish")
        self.games = [failed]
        for argv in (("gate", "--permission", "asked 12:40"), ("snapshot",), ("selftest-restore",), ("recover",)):
            with self.subTest(argv=argv):
                out, code = self.run_cli(*argv)
                self.assertEqual((code, out["refused"]), (2, "GateError"))
        self.assertEqual(snapshot.all_snapshots(self.backups), [])
        self.games = []
        taken, _ = self.run_cli("snapshot")
        self.games = [failed]
        self.start_result = self.game()
        out, code = self.launch(taken["id"], "-debug_mode")
        self.assertEqual((code, out["refused"], self.starts), (2, "GateError", []))
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "GateError"))
        game = self.game()
        snapshot.record(self.the_snapshot(), "started", pid=game.pid, created=game.created)
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "cannot_look"))
        self.assertEqual(self.events(), ["armed", "started", "watching"] + ["look_failed"] * 5)

    def test_game_arguments_go_to_launch_only(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as raised:
            cli.main(["restore", "20991231T000000Z", "--", "-debug_mode"])
        self.assertEqual(raised.exception.code, 2)                 # a usage error, argparse's own
        self.assertIn("only `launch` takes game arguments", err.getvalue())

    def test_an_unknown_snapshot_id_is_a_json_refusal(self):
        for argv in (("restore",), ("watch",), ("launch", "--permission", "asked 12:40", "--", "-debug_mode")):
            with self.subTest(verb=argv[0]):
                out, code = self.run_cli(argv[0], "20991231T000000Z", *argv[1:])
                self.assertEqual((code, out["refused"]), (2, "UnknownSnapshotError"))

    def test_a_save_that_is_missing_or_outside_the_folder_is_a_json_refusal(self):
        for name, error in (("no such save", "FileNotFoundError"), ("../../escape", "ValueError")):
            with self.subTest(name=name):
                out, code = self.run_cli("snapshot", "--save", name)
                self.assertEqual((code, out["refused"]), (2, error))
        self.assertEqual(snapshot.all_snapshots(self.backups), [])

    def test_a_file_that_keeps_changing_while_it_is_read_is_a_json_refusal(self):
        with mock.patch.object(snapshot, "_store_file", side_effect=OSError("autosave.v3 kept changing")):
            out, code = self.run_cli("snapshot")
        self.assertEqual((code, out["refused"], out["detail"]), (2, "OSError", "autosave.v3 kept changing"))
        self.assertEqual(snapshot.all_snapshots(self.backups), [])

    # -- self-test, gate, listings ---------------------------------------------

    def test_selftest_restore_leaves_no_scratch_folder_behind(self):
        self.run_cli("selftest-restore")
        self.assertEqual([p.name for p in self.backups.iterdir() if p.name.startswith("selftest_")], [])

    def test_selftest_restore_matches_and_changes_nothing(self):
        before = self.tree()
        out, code = self.run_cli("selftest-restore")
        self.assertEqual((code, out["match"], out["mismatched"], out["wrong_time"]), (0, True, [], []))
        self.assertEqual(out["files"], 4)
        self.assertEqual(self.tree(), before)

    def test_selftest_restore_accepts_times_a_coarse_drive_rounds_but_not_wrong_ones(self):
        real_utime = os.utime

        def to_whole_seconds(path, times=None, *, ns=None, **kw):
            if ns is not None:
                ns = tuple(t - t % 1_000_000_000 for t in ns)
            return real_utime(path, times, ns=ns, **kw) if ns is not None else real_utime(path, times, **kw)

        with mock.patch("os.utime", to_whole_seconds):
            out, code = self.run_cli("selftest-restore")
        self.assertEqual((code, out["match"], out["wrong_time"]), (0, True, []))

        def an_hour_off(path, times=None, *, ns=None, **kw):
            if ns is not None:
                ns = tuple(t + 3600 * 1_000_000_000 for t in ns)
            return real_utime(path, times, ns=ns, **kw) if ns is not None else real_utime(path, times, **kw)

        with mock.patch("os.utime", an_hour_off):
            out, code = self.run_cli("selftest-restore")
        self.assertEqual((code, out["match"]), (2, False))
        self.assertEqual(len(out["wrong_time"]), out["files"])

    def test_gate_refuses_without_a_backup_folder(self):
        with mock.patch.dict(os.environ, {"VIC3_QA_BACKUPS": "/nonexistent/drive/backups"}):
            out, code = self.run_cli("gate", "--permission", "session grant")
        self.assertEqual((code, out["reason"]), (2, "backup_root"))

    def test_gate_ok(self):
        out, code = self.run_cli("gate", "--permission", "asked 12:40")
        self.assertEqual((code, out["ok"], out["permission"]), (0, True, "asked 12:40"))

    def test_gate_refuses_beside_another_game(self):
        self.games = [gate.ProcId(9, "x")]
        out, code = self.run_cli("gate", "--permission", "session grant", "--owner-confirmed-busy")
        self.assertEqual((code, out["reason"]), (2, "other_game"))

    def test_held_and_recover_on_an_empty_root(self):
        self.assertEqual(self.run_cli("held"), ({"held": []}, 0))
        self.assertEqual(self.run_cli("recover"), ({"runs": []}, 0))


if __name__ == "__main__":
    unittest.main()
