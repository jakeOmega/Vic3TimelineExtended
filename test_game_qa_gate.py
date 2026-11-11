"""game_qa/gate.py: the GPU reading, process identity and the launch gate's decision.

Nothing here runs nvidia-smi or PowerShell: both are passed in as fakes.
"""
import contextlib
import datetime as dt
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game_qa import __main__ as cli
from game_qa import gate, snapshot

IDLE = [gate.GpuSample(14, 1607, 10240)] * 5
MINE = gate.ProcId(100, "2026-11-10T12:00:00.0000000Z")
UTC = dt.timezone.utc


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def iso(when: dt.datetime) -> str:
    """A time as Windows prints a process's creation time: seven fractional digits and a Z."""
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f0Z")


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
        self.clock = 0.0          # the clock `watch` measures its wait by; a nap moves it on
        self.look_seconds = 0.0   # how far one look moves it (PowerShell takes its time)
        env = {"VIC3_USER_DATA": str(self.user), "VIC3_QA_BACKUPS": str(self.backups)}
        patches = [mock.patch.dict(os.environ, env),
                   mock.patch.object(gate, "list_games", side_effect=self._list_games),
                   mock.patch.object(gate, "sample_gpu", return_value=IDLE),
                   mock.patch.object(cli, "_sleep", self._nap),
                   mock.patch.object(cli, "_clock", lambda: self.clock)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _nap(self, seconds):
        self.clock += seconds

    def _list_games(self, *a, **k):
        self.clock += self.look_seconds
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

    def watched_run(self, during=lambda: None, save="new york_1940_07_29"):
        """snapshot, then `watch` over a game that is seen twice and then gone; `during` runs while it is up."""
        taken, code = self.run_cli("snapshot", "--save", save)
        self.assertEqual(code, 0)
        game = self.game()
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

        snap_id = self.watched_run(the_run)
        self.assertIn("save games/new york_1940_07_29.v3", self.the_snapshot().files)
        self.assertEqual(self.events(), ["armed", "started", "heartbeat", "game_exited"])
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"]), (0, False))
        self.assertEqual(self.tree(), before)

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
        snap_id = self.watched_run()
        theirs = self.user / "save games" / "autosave.v3"
        theirs.write_bytes(b"the owner played for an hour after the run")
        later = dt.datetime.now().timestamp() + 3600
        os.utime(theirs, (later, later))
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "modified_after_exit"))
        self.assertEqual(theirs.read_bytes(), b"the owner played for an hour after the run")
        self.assertEqual(self.run_cli("held")[0], {"held": [snap_id]})

    def test_a_restore_beside_the_owners_game_holds_and_a_retry_still_keeps_their_save(self):
        snap_id = self.watched_run()
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
        self.assertEqual((code, out["refused"]), (2, "game_still_up"))
        self.assertNotIn("game_exited", self.events())

    def test_restore_reports_a_damaged_store_instead_of_a_traceback(self):
        snap_id = self.watched_run(lambda: (self.user / "continue_game.json").write_text("{}"))
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
        snap_id = self.watched_run(lambda: (self.user / name).write_bytes(b"the run saved over it"),
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
        self.assertEqual((code, out["held"], out["refused"]), (2, False, "watch_still_recording"))
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

    # -- watch ----------------------------------------------------------------

    def test_watch_does_not_adopt_a_game_older_than_the_snapshot(self):
        taken, _ = self.run_cli("snapshot")
        self.games = [self.game(pid=7, seconds_from_now=-3600)]     # the owner's game, running since before
        out, code = self.run_cli("watch", taken["id"], "--wait", "0")
        self.assertEqual((code, out["refused"], out["games_not_adopted"]), (2, "no_game", 1))
        self.assertEqual(self.events(), ["armed"])

    # The 2026-11-10 review's C1, three ways: a `watch` adopted the game the owner started after the run, and
    # `restore` then put the snapshot's copy over the owner's save, or removed the save they had added.

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

    def test_watch_on_a_run_that_never_started_does_not_adopt_the_game_the_owner_started_later(self):
        snap, owner = self.run_an_hour_ago(started=False)       # the session died before `watch`
        self.owner_writes("save games/autosave.v3", b"the owner's own game, 30 minutes ago", minutes_ago=30)
        before = self.tree()
        self.games = [[owner], [owner], []]
        out, code = self.run_cli("watch", snap.id)
        self.assertEqual((code, out["refused"]), (2, "no_game"))
        self.assertEqual(self.events(), ["armed"])
        self.games = []                                             # the owner has closed their game
        out, code = self.run_cli("restore", snap.id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "no_reference_time"))
        self.assertEqual(self.tree(), before)

    def test_watch_resumes_the_recorded_game_and_records_no_second_start(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        snapshot.record(self.the_snapshot(), "started", pid=game.pid, created=game.created)
        snapshot.record(self.the_snapshot(), "heartbeat")
        self.games = [[game], [game], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["resumed"], out["heartbeats"], out["pid"]), (0, True, 1, game.pid))
        self.assertEqual(self.events(), ["armed", "started", "heartbeat", "heartbeat", "game_exited"])

    def test_watch_resumes_nothing_but_the_recorded_game(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        snapshot.record(self.the_snapshot(), "started", pid=game.pid, created=game.created)
        out, code = self.run_cli("watch", taken["id"], "--pid", "99")
        self.assertEqual((code, out["refused"]), (2, "not_the_run"))
        # The recorded game is gone and another new one is up: that one is not adopted, and no exit is
        # recorded, since nobody saw when the run's game exited.
        another = self.game(pid=99, seconds_from_now=120)
        self.games = [[another], [another], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "game_gone_unrecorded"))
        self.assertIn("last heartbeat", out["detail"])
        self.assertEqual(self.events(), ["armed", "started"])

    def test_watch_refuses_a_recorded_start_it_cannot_read(self):
        taken, _ = self.run_cli("snapshot")
        snapshot.record(self.the_snapshot(), "started", created="2026-11-10T12:00:00.0000000Z")   # no pid
        game = self.game()
        self.games = [[game], [game], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "unreadable_start"))
        self.assertEqual(self.events(), ["armed", "started"])

    def test_watch_with_pid_adopts_that_one_of_two_new_games(self):
        taken, _ = self.run_cli("snapshot")
        first, second = self.game(pid=1), self.game(pid=2)
        self.games = [[first, second], [first, second], [first]]
        out, code = self.run_cli("watch", taken["id"], "--pid", "2")
        self.assertEqual((code, out["pid"], out["heartbeats"]), (0, 2, 1))
        started = [e for e in snapshot.journal(self.the_snapshot()) if e["event"] == "started"]
        self.assertEqual([(e["pid"], e["created"]) for e in started], [(2, second.created)])
        self.assertEqual(self.events()[-1], "game_exited")

    def test_watch_with_pid_refuses_a_game_it_may_not_adopt(self):
        taken, _ = self.run_cli("snapshot")
        for game in (self.game(pid=7, seconds_from_now=-3600),      # older than the snapshot
                     self.game(pid=7, seconds_from_now=900),        # more than ten minutes after it
                     gate.ProcId(7, "unknown")):                    # a start time the session may not read
            with self.subTest(game=game):
                self.games = [game]
                out, code = self.run_cli("watch", taken["id"], "--pid", "7")
                self.assertEqual((code, out["refused"]), (2, "not_the_run"))
        self.games = [self.game(pid=8)]                             # a new game, but not the one named
        out, code = self.run_cli("watch", taken["id"], "--pid", "7", "--wait", "10")
        self.assertEqual((code, out["refused"]), (2, "not_the_run"))
        self.assertEqual(self.events(), ["armed"])

    def test_watch_adopts_only_a_game_created_within_ten_minutes_of_the_snapshot(self):
        armed = dt.datetime.now(UTC).replace(microsecond=0) - dt.timedelta(minutes=20)
        for offset, adopted in ((599, True), (600, True), (601, False)):
            with self.subTest(offset=offset):
                snap = self.armed_snapshot(armed)
                self.games = [[gate.ProcId(500, iso(armed + dt.timedelta(seconds=offset)))], []]
                out, code = self.run_cli("watch", snap.id, "--wait", "0")
                self.assertEqual(code, 0 if adopted else 2)
                self.assertEqual(self.events(), ["armed", "started", "game_exited"] if adopted else ["armed"])

    def test_watch_adopts_a_game_created_in_the_second_of_the_snapshot_but_not_before_it(self):
        # `armed` keeps whole seconds; a creation time keeps seven digits.
        armed = dt.datetime.now(UTC).replace(microsecond=0) - dt.timedelta(minutes=5)
        for offset, adopted in ((0.5, True), (0.0, False), (-0.5, False)):
            with self.subTest(offset=offset):
                snap = self.armed_snapshot(armed)
                self.games = [[gate.ProcId(500, iso(armed + dt.timedelta(seconds=offset)))], []]
                out, code = self.run_cli("watch", snap.id, "--wait", "0")
                self.assertEqual(code, 0 if adopted else 2)
                self.assertEqual(self.events(), ["armed", "started", "game_exited"] if adopted else ["armed"])

    def test_watch_never_adopts_a_game_whose_start_time_is_unknown(self):
        taken, _ = self.run_cli("snapshot")
        unknown = gate.ProcId(5, "unknown")          # it may be the run's game as well as the other one
        game = self.game()
        self.games = [[unknown, game], [unknown, game], [unknown]]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "unknown_game"))
        self.assertEqual(self.events(), ["armed"])

    def test_watch_measures_its_wait_on_the_clock_and_not_by_counting_naps(self):
        taken, _ = self.run_cli("snapshot")
        self.look_seconds = 3.0
        start = self.clock
        out, code = self.run_cli("watch", taken["id"], "--wait", "10")
        self.assertEqual((code, out["refused"]), (2, "no_game"))
        self.assertLessEqual(self.clock - start, 10 + 2 + 3)       # at most one nap and one look past the wait

    def test_watch_keeps_looking_when_a_look_fails(self):
        # Review 2026-11-10, I1: one look that failed read as "the game is gone".
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        failed = gate.GateError("powershell.exe exited 1 with nothing on stdout")
        unreadable = gate.ProcId(game.pid, "unknown")              # its start time, unreadable for a moment
        self.games = [[game], failed, [game], [unreadable], failed, []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["heartbeats"]), (0, 1))
        self.assertEqual(self.events(), ["armed", "started", "heartbeat", "game_exited"])

    def test_watch_stops_without_recording_an_exit_after_five_failed_looks(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        self.games = [[game], [game], gate.GateError("no PowerShell")]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"], out["heartbeats"]), (2, "cannot_look", 1))
        self.assertEqual(self.events(), ["armed", "started", "heartbeat"])
        # Once PowerShell answers again, `watch` picks the run up where it was.
        self.games = [[game], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["resumed"]), (0, True))
        self.assertEqual(self.events(), ["armed", "started", "heartbeat", "game_exited"])

    def test_watch_refuses_two_new_games(self):
        taken, _ = self.run_cli("snapshot")
        self.games = [self.game(pid=1), self.game(pid=2)]
        out, code = self.run_cli("watch", taken["id"], "--wait", "0")
        self.assertEqual((code, out["refused"]), (2, "several_games"))
        self.assertEqual(self.events(), ["armed"])

    def test_watch_waits_for_the_game_to_appear(self):
        taken, _ = self.run_cli("snapshot")
        game = self.game()
        self.games = [[], [], [game], [game], []]
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["heartbeats"]), (0, 1))
        self.assertEqual(self.events(), ["armed", "started", "heartbeat", "game_exited"])

    def test_watch_refuses_a_finished_snapshot_and_one_not_taken_for_a_run(self):
        snap_id = self.watched_run()
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
        snapshot.record(self.the_snapshot(), "started", pid=MINE.pid, created=MINE.created)
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
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "GateError"))
        out, code = self.run_cli("watch", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "cannot_look"))
        self.assertEqual(self.events(), ["armed"])

    def test_an_unknown_snapshot_id_is_a_json_refusal(self):
        for verb in ("restore", "watch"):
            with self.subTest(verb=verb):
                out, code = self.run_cli(verb, "20991231T000000Z")
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
