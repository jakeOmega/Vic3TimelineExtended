"""game_qa/gate.py: the GPU reading, process identity and the launch gate's decision.

Nothing here runs nvidia-smi or PowerShell: both are passed in as fakes.
"""
import contextlib
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


def completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


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
    def test_parses_pid_and_creation_time(self):
        out = gate.list_games(run=lambda *a, **k: completed("81168 2026-11-10T18:59:22.1234567Z\r\n"))
        self.assertEqual(out, [gate.ProcId(81168, "2026-11-10T18:59:22.1234567Z")])

    def test_no_game_is_an_empty_list(self):
        self.assertEqual(gate.list_games(run=lambda *a, **k: completed("")), [])

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
        env = {"VIC3_USER_DATA": str(self.user), "VIC3_QA_BACKUPS": str(self.backups)}
        patches = [mock.patch.dict(os.environ, env),
                   mock.patch.object(gate, "list_games", return_value=[]),
                   mock.patch.object(gate, "sample_gpu", return_value=IDLE)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return json.loads(out.getvalue()), code

    def tree(self):
        return sorted((str(p.relative_to(self.user)), p.stat().st_mtime_ns, p.read_bytes())
                      for p in self.user.rglob("*") if p.is_file())

    def test_snapshot_then_restore_puts_a_changed_file_back(self):
        before = self.tree()
        taken, code = self.run_cli("snapshot", "--save", "new york_1940_07_29")
        self.assertEqual(code, 0)
        self.assertIn("save games/new york_1940_07_29.v3", snapshot.all_snapshots(self.backups)[0].files)
        (self.user / "continue_game.json").write_text('{"title": "autosave"}')
        (self.user / "save games" / "TEST_FAIL_te_qa_fixture_2 January, 1836.v3").write_bytes(b"x")
        out, code = self.run_cli("restore", taken["id"], "--game-just-closed")
        self.assertEqual((code, out["held"]), (0, False))
        self.assertEqual(self.tree(), before)

    def test_restore_without_an_end_of_run_is_refused(self):
        taken, _ = self.run_cli("snapshot")
        (self.user / "continue_game.json").write_text("{}")
        out, code = self.run_cli("restore", taken["id"])
        self.assertEqual((code, out["refused"]), (2, "no_reference_time"))
        self.assertEqual((self.user / "continue_game.json").read_text(), "{}")

    def test_restore_is_refused_while_the_runs_own_game_is_up(self):
        taken, _ = self.run_cli("snapshot")
        snap = snapshot.all_snapshots(self.backups)[0]
        snapshot.record(snap, "started", pid=MINE.pid, created=MINE.created)
        gate.list_games.return_value = [MINE]
        out, code = self.run_cli("restore", taken["id"], "--game-just-closed")
        self.assertEqual((code, out["refused"]), (2, "game_still_up"))
        self.assertNotIn("game_exited", [e["event"] for e in snapshot.journal(snap)])

    def test_snapshot_refuses_while_a_run_is_unfinished(self):
        taken, _ = self.run_cli("snapshot")
        snap = snapshot.all_snapshots(self.backups)[0]
        snapshot.record(snap, "started", pid=MINE.pid, created=MINE.created)
        out, code = self.run_cli("snapshot")
        self.assertEqual((code, out["refused"], out["unfinished"]), (2, "unfinished_run", [taken["id"]]))
        self.assertEqual(len(snapshot.all_snapshots(self.backups)), 1)
        snapshot.record(snap, "game_exited")
        self.run_cli("recover")
        self.assertEqual(self.run_cli("snapshot")[1], 0)

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
        gate.list_games.return_value = [gate.ProcId(9, "x")]
        out, code = self.run_cli("gate", "--permission", "session grant", "--owner-confirmed-busy")
        self.assertEqual((code, out["reason"]), (2, "other_game"))

    def test_held_and_recover_on_an_empty_root(self):
        self.assertEqual(self.run_cli("held"), ({"held": []}, 0))
        self.assertEqual(self.run_cli("recover"), ({"runs": []}, 0))


if __name__ == "__main__":
    unittest.main()
