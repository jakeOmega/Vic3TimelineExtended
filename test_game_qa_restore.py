"""Tests for game_qa.restore: compare a user-data folder with a snapshot, put it back, hold when the owner has
changed it since, recover runs that never finished, and prune old snapshots.

No game and no Windows program is needed: every test builds its folders in a temp dir. The run's game is
played by the test itself: it edits files between `run_started` and `finish`.
"""

import hashlib
import json
import math
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from game_qa import restore, snapshot
from test_game_qa_snapshot import make_user_data

NOW = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)


def finish(snap, at=None):
    """Record that the run's game exited.

    Journal times have one-second resolution, so by default the exit is stamped at the next whole second at or
    after both the clock and the newest file in the test's user-data folder (a sibling of the backup root): it
    is then never earlier than a file the test wrote a moment ago, even if the machine's clock has been stepped
    back since (WSL's is, by several seconds, now and then).
    """
    if at is None:
        user_data = snap.dir.parents[2] / "user data"
        newest = max((p.stat().st_mtime for p in user_data.rglob("*") if p.is_file()), default=0.0)
        at = datetime.fromtimestamp(math.ceil(max(newest, time.time())), timezone.utc)
    snapshot.record(snap, "game_exited", now=at)


def set_mtime(path: Path, when: datetime, offset_seconds: float = 0.0) -> None:
    stamp = when.timestamp() + offset_seconds
    os.utime(path, (stamp, stamp))


def tree(root: Path) -> dict[str, tuple[bytes, int]]:
    """Every file under root: relative path -> (bytes, mtime_ns)."""
    return {
        p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def events(snap) -> list[str]:
    return [e["event"] for e in snapshot.journal(snap)]


def blob(backups: Path, entry: snapshot.Entry) -> Path:
    return backups / "store" / entry.sha256[:2] / entry.sha256


def age_store(backups: Path, days: float = 2.0) -> None:
    """Make every stored blob old enough for the sweep (it spares anything younger than a day)."""
    when = time.time() - days * 86400
    for path in (backups / "store").glob("??/*"):
        os.utime(path, (when, when))


class RestoreTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.user = self.tmp / "user data"
        make_user_data(self.user)
        self.backups = self.tmp / "backups"
        self.ticks = 0
        self.start = datetime.now(timezone.utc).replace(microsecond=0)

    def next_time(self):
        """A snapshot time one second after the last one this test used, so that ids and `started` times are the
        same on every run whatever this machine's clock (WSL's is stepped by several seconds now and then) does."""
        self.ticks += 1
        return self.start + timedelta(seconds=self.ticks)

    def take(self):
        """A snapshot with no journal: taken, never launched."""
        return snapshot.take(self.user, self.backups, now=self.next_time())

    def run_started(self, at=None, extra=(), pid=4242):
        at = at if at is not None else self.next_time()
        snap = snapshot.take(self.user, self.backups, extra=extra, now=at)
        snapshot.record(snap, "started", now=at, pid=pid, created="2026-11-10T12:00:00Z")
        return snap

    def finished_run(self):
        """A run that changed nothing, exited and was restored: its journal ends in `restored`."""
        snap = self.run_started()
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertFalse(out.held)
        return snap

    def held_run(self):
        """A run that was held (another game was up when it ended); user_data is left as it was."""
        snap = self.run_started()
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=True)
        self.assertTrue(out.held)
        return snap

    def edit_after_exit(self, seconds_after_exit):
        """Run a game that exited at NOW, then change continue_game.json to a time after that; restore."""
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)
        p = self.user / "continue_game.json"
        p.write_text("{}")
        set_mtime(p, NOW, seconds_after_exit)
        return restore.restore(snap, self.user, other_game_running=False)


class CompareTests(RestoreTestCase):
    def test_untouched_folder_has_an_empty_diff(self):
        snap = self.run_started()
        self.assertEqual(restore.compare(snap, self.user), restore.Diff([], [], [], []))

    def test_changed_is_decided_by_the_hash_not_by_size_or_time(self):
        snap = self.run_started()
        p = self.user / "continue_game.json"
        st = p.stat()
        p.write_bytes(bytes(b ^ 1 for b in p.read_bytes()))
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        (self.user / "pdx_settings.json").write_bytes(b"a different length of settings")
        diff = restore.compare(snap, self.user)
        self.assertEqual(diff.changed, ["continue_game.json", "pdx_settings.json"])

    def test_a_deleted_file_is_missing_not_changed(self):
        snap = self.run_started()
        (self.user / "console_history.txt").unlink()
        (self.user / "save games/autosave_1.v3").unlink()
        diff = restore.compare(snap, self.user)
        self.assertEqual((diff.changed, diff.missing), ([], ["console_history.txt", "save games/autosave_1.v3"]))

    def test_a_set_file_the_run_pushed_in_is_added_in_set(self):
        snap = self.run_started()
        (self.user / "save games/autosave_2.v3").write_bytes(b"pushed in by the run")
        (self.user / "logs/game.log").write_text("created by the run")
        (self.user / "save games/mine_too.v3").write_bytes(b"not in the set, not a harness name")
        (self.user / "notes.txt").write_text("not in the set either")
        diff = restore.compare(snap, self.user)
        self.assertEqual(diff.added_in_set, ["logs/game.log", "save games/autosave_2.v3"])
        self.assertEqual(diff.created, [])

    def test_only_rotation_names_count_as_autosaves_the_run_pushed_in(self):
        # OneDrive makes conflict copies such as autosave-Manfred.v3; they match autosave*.v3 and are the owner's
        snap = self.run_started()
        for name in ("autosave_3.v3", "autosave_12.v3", "autosave_exit.v3", "autosave-Manfred.v3",
                     "autosave_1-Manfred.v3", "autosave_.v3", "autosave_exit_2.v3", "autosave 2.v3"):
            (self.user / "save games" / name).write_bytes(b"x")
        diff = restore.compare(snap, self.user)
        self.assertEqual(
            diff.added_in_set,
            ["save games/autosave_12.v3", "save games/autosave_3.v3", "save games/autosave_exit.v3"],
        )

    def test_a_leftover_restore_temp_is_neither_added_nor_created(self):
        snap = self.run_started()
        (self.user / "logs/debug.log.te_qa_restore.tmp").write_bytes(b"x")
        (self.user / "save games/te_qa_x.v3.te_qa_restore.tmp").write_bytes(b"x")
        self.assertEqual(restore.compare(snap, self.user), restore.Diff([], [], [], []))

    def test_created_is_the_harness_names_that_were_not_there_and_are_not_kept(self):
        (self.user / "save games/te_qa_before.v3").write_bytes(b"there before the run")
        (self.user / "tests.txt").write_text("there before the run")
        snap = self.run_started()
        for name in (
            "save games/TEST_FAIL_te_qa_fixture_2 January, 1836.v3",
            "save games/te_qa_scratch.v3",
            "save games/te_qa_fixture_abc.v3",  # kept by the harness
        ):
            (self.user / name).write_bytes(b"x")
        diff = restore.compare(snap, self.user)
        self.assertEqual(
            diff.created,
            ["save games/TEST_FAIL_te_qa_fixture_2 January, 1836.v3", "save games/te_qa_scratch.v3"],
        )

    def test_a_symlink_that_was_there_before_the_run_is_not_added(self):
        # in the listing but not in the manifest: it must not read as something the run pushed in
        (self.user / "logs/latest.log").symlink_to("debug.log")
        snap = self.run_started()
        self.assertIn("logs/latest.log", snap.listing)
        self.assertEqual(restore.compare(snap, self.user).added_in_set, [])

    def test_extra_saves_in_the_manifest_are_compared(self):
        snap = self.run_started(extra=["save games/mine.v3"])
        (self.user / "save games/mine.v3").write_bytes(b"edited by the run")
        self.assertEqual(restore.compare(snap, self.user).changed, ["save games/mine.v3"])

    def test_files_in_subfolders_are_not_looked_at(self):
        snap = self.run_started()
        (self.user / "logs/data_types").mkdir()
        (self.user / "logs/data_types/triggers.txt").write_text("run output")
        (self.user / "save games/sub").mkdir()
        (self.user / "save games/sub/te_qa_deep.v3").write_bytes(b"x")
        self.assertEqual(restore.compare(snap, self.user), restore.Diff([], [], [], []))

    def test_a_missing_user_data_folder_raises(self):
        snap = self.run_started()
        with self.assertRaises(FileNotFoundError):
            restore.compare(snap, self.tmp / "no such folder")


class RestoreTests(RestoreTestCase):
    def test_untouched_folder_restores_nothing(self):
        snap = self.run_started()
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.restored, out.removed, out.held), ([], [], False))
        self.assertEqual(snapshot.journal(snap)[-1]["event"], "restored")

    def test_rotation_is_put_back_as_a_set(self):
        snap = self.run_started()
        old = (self.user / "save games/autosave.v3").read_bytes()
        os.replace(self.user / "save games/autosave.v3", self.user / "save games/autosave_2.v3")
        (self.user / "save games/autosave.v3").write_bytes(b"the run's autosave")
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((self.user / "save games/autosave.v3").read_bytes(), old)
        self.assertFalse((self.user / "save games/autosave_2.v3").exists())
        self.assertIn("save games/autosave_2.v3", out.removed)

    def test_same_size_and_time_different_bytes_is_restored(self):
        snap = self.run_started()
        p = self.user / "continue_game.json"
        st = p.stat()
        before = p.read_bytes()
        p.write_bytes(bytes(b ^ 1 for b in before))
        os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(p.read_bytes(), before)

    def test_restored_file_keeps_its_recorded_time(self):
        snap = self.run_started()
        p = self.user / "console_history.txt"
        p.write_text("event x\n")
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(p.stat().st_mtime_ns, snap.files["console_history.txt"].mtime_ns)

    def test_removes_only_what_the_run_created(self):
        (self.user / "save games/te_qa_old.v3").write_bytes(b"before the run")
        snap = self.run_started()
        for name in ("TEST_FAIL_te_qa_fixture_2 January, 1836.v3", "te_qa_scratch.v3", "te_qa_fixture_abc.v3"):
            (self.user / "save games" / name).write_bytes(b"x")
        (self.user / "tests.txt").write_text("Tests:\n")
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(
            sorted(out.removed),
            ["save games/TEST_FAIL_te_qa_fixture_2 January, 1836.v3", "save games/te_qa_scratch.v3", "tests.txt"],
        )
        self.assertTrue((self.user / "save games/te_qa_fixture_abc.v3").exists())
        self.assertTrue((self.user / "save games/te_qa_old.v3").exists())
        self.assertTrue((self.user / "save games/mine.v3").exists())

    def test_run_logs_are_copied_out_before_the_put_back(self):
        snap = self.run_started()
        (self.user / "logs/debug.log").write_text("the run's log\n")
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False, run_logs_dir=self.tmp / "runlogs")
        self.assertEqual((self.tmp / "runlogs/debug.log").read_text(), "the run's log\n")
        self.assertNotEqual((self.user / "logs/debug.log").read_text(), "the run's log\n")

    def test_every_live_log_is_copied_out_including_ones_the_run_added(self):
        snap = self.run_started()
        (self.user / "logs/game.log").write_text("a log the run created")
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False, run_logs_dir=self.tmp / "runlogs")
        self.assertEqual(sorted(p.name for p in (self.tmp / "runlogs").iterdir()), ["debug.log", "error.log", "game.log"])
        self.assertFalse((self.user / "logs/game.log").exists())

    def test_without_a_given_folder_the_run_logs_go_beside_the_journal(self):
        snap = self.run_started()
        (self.user / "logs/debug.log").write_text("the run's log\n")
        (self.user / "logs/game.log").write_text("a log the run created")
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False)
        run_logs = snap.dir / "run_logs"
        self.assertEqual(sorted(p.name for p in run_logs.iterdir()), ["debug.log", "error.log", "game.log"])
        self.assertEqual((run_logs / "debug.log").read_text(), "the run's log\n")

    def test_told_to_leave_the_logs_alone_it_copies_puts_back_and_removes_none(self):
        # The command line passes logs=False for a snapshot nothing was launched under: its logs are whoever
        # played since, not a run's.
        snap = self.take()
        (self.user / "logs/debug.log").write_text("a later session's log\n")      # changed
        (self.user / "logs/error.log").unlink()                                  # in the manifest, gone now
        (self.user / "logs/game.log").write_text("a log added since")             # new
        before = tree(self.user)
        out = restore.restore(snap, self.user, other_game_running=False, run_logs_dir=self.tmp / "runlogs",
                              logs=False)
        self.assertEqual((out.held, out.restored, out.removed), (False, [], []))
        self.assertEqual(tree(self.user), before)
        self.assertFalse((self.tmp / "runlogs").exists())
        self.assertEqual(events(snap), ["restored"])

    def test_told_to_leave_the_logs_alone_it_still_puts_the_other_files_back(self):
        snap = self.take()
        (self.user / "logs/debug.log").write_text("a later session's log\n")
        (self.user / "pdx_settings.json").unlink()
        out = restore.restore(snap, self.user, other_game_running=False, logs=False)
        self.assertEqual((out.held, out.restored), (False, ["pdx_settings.json"]))
        self.assertEqual((self.user / "logs/debug.log").read_text(), "a later session's log\n")

    def test_no_folder_is_made_for_run_logs_when_there_are_none(self):
        for p in (self.user / "logs").iterdir():
            p.unlink()
        snap = self.run_started()
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False)
        self.assertFalse((snap.dir / "run_logs").exists())

    def test_a_second_restore_keeps_the_run_logs_from_the_first(self):
        snap = self.run_started()
        (self.user / "logs/debug.log").write_text("the run's log\n")
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False)
        restore.restore(snap, self.user, other_game_running=False)  # the logs are the owner's again by now
        self.assertEqual((snap.dir / "run_logs/debug.log").read_text(), "the run's log\n")

    def test_a_run_log_is_copied_again_over_a_stale_copy(self):
        snap = self.run_started()
        (self.user / "logs/debug.log").write_text("the run's log\n")
        finish(snap)
        (snap.dir / "run_logs").mkdir()
        (snap.dir / "run_logs/debug.log").write_text("left over from an earlier attempt")
        restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((snap.dir / "run_logs/debug.log").read_text(), "the run's log\n")

    def test_the_owners_conflict_copies_of_an_autosave_survive(self):
        snap = self.run_started()
        for name in ("autosave-Manfred.v3", "autosave_1-Manfred.v3"):
            (self.user / "save games" / name).write_bytes(b"made by OneDrive during the run")
        (self.user / "save games/autosave_3.v3").write_bytes(b"pushed in by the run")
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(out.removed, ["save games/autosave_3.v3"])
        self.assertTrue((self.user / "save games/autosave-Manfred.v3").exists())
        self.assertTrue((self.user / "save games/autosave_1-Manfred.v3").exists())

    def test_leftover_restore_temps_are_cleared_in_every_folder(self):
        snap = self.run_started()
        stale = ["continue_game.json.te_qa_restore.tmp", "save games/autosave.v3.te_qa_restore.tmp",
                 "logs/debug.log.te_qa_restore.tmp"]
        for name in stale:
            (self.user / name).write_bytes(b"half a file from a killed restore")
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.restored, out.removed), ([], []))
        self.assertFalse([name for name in stale if (self.user / name).exists()])
        self.assertFalse((snap.dir / "run_logs/debug.log.te_qa_restore.tmp").exists())

    def test_a_missing_file_comes_back_with_its_recorded_time_and_alone_causes_no_hold(self):
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)  # long before every real file time, but a missing file has no time
        (self.user / "console_history.txt").unlink()
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.restored, out.held), (["console_history.txt"], False))
        p = self.user / "console_history.txt"
        self.assertEqual(p.read_bytes(), b"set_variable x\n")
        self.assertEqual(p.stat().st_mtime_ns, snap.files["console_history.txt"].mtime_ns)

    def test_a_save_the_run_was_to_load_is_restored(self):
        snap = self.run_started(extra=["save games/mine.v3"])
        (self.user / "save games/mine.v3").write_bytes(b"edited by the run")
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(out.restored, ["save games/mine.v3"])
        self.assertEqual((self.user / "save games/mine.v3").read_bytes(), b"the owner's own save")

    def test_restoring_twice_does_nothing_the_second_time(self):
        snap = self.run_started()
        (self.user / "continue_game.json").write_text("{}")
        (self.user / "tests.txt").write_text("Tests:\n")
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False)
        again = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((again.restored, again.removed, again.held), ([], [], False))
        self.assertEqual(events(snap)[-2:], ["restored", "restored"])

    def test_the_restored_entry_names_what_was_done(self):
        snap = self.run_started()
        (self.user / "continue_game.json").write_text("{}")
        (self.user / "tests.txt").write_text("Tests:\n")
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False, now=NOW)
        entry = snapshot.journal(snap)[-1]
        self.assertEqual(
            entry,
            {
                "event": "restored",
                "at": "2026-11-10T12:00:00Z",
                "restored": ["continue_game.json"],
                "removed": ["tests.txt"],
            },
        )

    def test_no_temp_files_are_left_in_the_owners_folders(self):
        snap = self.run_started()
        (self.user / "continue_game.json").write_text("{}")
        (self.user / "save games/autosave.v3").write_bytes(b"the run's autosave")
        (self.user / "logs/debug.log").unlink()
        before = set(tree(self.user))
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(set(tree(self.user)), before | {"logs/debug.log"})

    def test_a_missing_user_data_folder_raises_and_is_not_created(self):
        snap = self.run_started()
        finish(snap)
        with self.assertRaises(FileNotFoundError):
            restore.restore(snap, self.tmp / "no such folder", other_game_running=False)
        self.assertFalse((self.tmp / "no such folder").exists())
        self.assertEqual(events(snap), ["started", "game_exited"])


class TickTaskTimingsTests(RestoreTestCase):
    """#1700: console `dump_ticktask_timings` overwrites `ticktask_timings.csv` in the user-data root in place.
    It is in the snapshot set, so the restore's rules for the set decide it: the owner's copy is put back, one the
    run wrote where there was none is removed, and one written after the run's end holds the snapshot. A copy the
    manifest lists but did not store (a symlink, or a snapshot taken before the set named the file) is never the
    run's, so it is neither put back nor removed."""

    NAME = "ticktask_timings.csv"
    OWNERS = b"\xef\xbb\xbfframe,task,milliseconds,calls,longest_lock\n60719946,MoveArmies,0,1,0\n"
    RUNS = b"\xef\xbb\xbfframe,task,milliseconds,calls,longest_lock\n60720000,MoveArmies,1,1,0\n"

    def run_writes_it(self, at_seconds: float = 30.0, exited_after: float = 60.0):
        """A run from NOW, exited `exited_after` seconds later, whose game dumped the timings `at_seconds` in."""
        snap = self.run_started(at=NOW)
        (self.user / self.NAME).write_bytes(self.RUNS)
        set_mtime(self.user / self.NAME, NOW, at_seconds)
        finish(snap, at=NOW + timedelta(seconds=exited_after))
        return snap

    def test_the_owners_copy_is_put_back_with_its_time(self):
        path = self.user / self.NAME
        path.write_bytes(self.OWNERS)
        set_mtime(path, NOW, -86400)
        owners_time = path.stat().st_mtime_ns
        snap = self.run_writes_it()
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertFalse(out.held)
        self.assertIn(self.NAME, out.restored)
        self.assertEqual(path.read_bytes(), self.OWNERS)
        self.assertEqual(path.stat().st_mtime_ns // 10**9, owners_time // 10**9)

    def test_one_the_run_wrote_where_there_was_none_is_removed(self):
        snap = self.run_writes_it()
        self.assertEqual(restore.compare(snap, self.user).added_in_set, [self.NAME])
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(out.removed, [self.NAME])
        self.assertFalse((self.user / self.NAME).exists())

    def test_one_written_after_the_runs_end_holds_and_stays(self):
        snap = self.run_writes_it(at_seconds=70.0, exited_after=60.0)     # later than the end and its slack
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertTrue(out.held)
        self.assertEqual(out.reason, "modified_after_exit")
        self.assertEqual((self.user / self.NAME).read_bytes(), self.RUNS)

    def test_one_the_manifest_lists_but_did_not_store_is_left_alone(self):
        # a snapshot taken before the set named the file: it is in the listing, not in the files
        path = self.user / self.NAME
        path.write_bytes(self.OWNERS)
        snap = self.run_started(at=NOW)
        manifest = snap.dir / snapshot.MANIFEST_NAME
        data = json.loads(manifest.read_text("utf-8"))
        del data["files"][self.NAME]
        manifest.write_text(json.dumps(data), encoding="utf-8")
        snap = snapshot.load(snap.dir)
        self.assertIn(self.NAME, snap.listing)
        path.write_bytes(self.RUNS)
        set_mtime(path, NOW, 30)
        finish(snap, at=NOW + timedelta(seconds=60))
        self.assertEqual(restore.compare(snap, self.user), restore.Diff([], [], [], []))
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.restored, out.removed), ([], []))
        self.assertEqual(path.read_bytes(), self.RUNS)

    def test_a_symlink_by_that_name_is_listed_and_never_removed(self):
        (self.user / "elsewhere.csv").write_bytes(self.OWNERS)
        (self.user / self.NAME).symlink_to("elsewhere.csv")
        snap = self.run_started(at=NOW)
        self.assertNotIn(self.NAME, snap.files)
        finish(snap, at=NOW + timedelta(seconds=60))
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(out.removed, [])
        self.assertTrue((self.user / self.NAME).is_symlink())


class RetimeTests(RestoreTestCase):
    """#1588: a file the run wrote again with the same bytes (the game writes `pdx_settings.json` at every launch)
    is not rewritten, and gets the time the snapshot recorded back, but only a time the run can have set."""

    RUN_SECONDS = 60

    def rewritten(self, rel="pdx_settings.json", seconds_into_run=30.0, exited=True):
        """A run from NOW, exited after RUN_SECONDS, whose game wrote `rel` again with the bytes it had, that long
        after the start; the owner's file was a day old. Returns the snapshot, the path and the owner's time."""
        path = self.user / rel
        set_mtime(path, NOW, -86400)
        owners = path.stat().st_mtime_ns
        snap = self.run_started(at=NOW)
        path.write_bytes(path.read_bytes())
        set_mtime(path, NOW, seconds_into_run)
        if exited:
            finish(snap, at=NOW + timedelta(seconds=self.RUN_SECONDS))
        return snap, path, owners

    def test_a_file_rewritten_with_the_same_bytes_gets_the_snapshots_time_back(self):
        before = tree(self.user)
        set_mtime(self.user / "pdx_settings.json", NOW, -86400)
        before["pdx_settings.json"] = (before["pdx_settings.json"][0], (self.user / "pdx_settings.json").stat().st_mtime_ns)
        snap, path, owners = self.rewritten()
        inode = path.stat().st_ino
        out = restore.restore(snap, self.user, other_game_running=False, now=NOW)
        self.assertEqual((out.held, out.restored, out.removed, out.retimed), (False, [], [], ["pdx_settings.json"]))
        self.assertEqual(path.stat().st_mtime_ns, owners)
        self.assertEqual(path.stat().st_ino, inode)                 # the same file: nothing was written over it
        self.assertEqual(tree(self.user), before)
        self.assertEqual(snapshot.journal(snap)[-1], {"event": "restored", "at": "2026-11-10T12:00:00Z",
                                                      "restored": [], "removed": [], "retimed": ["pdx_settings.json"]})

    def test_it_is_listed_beside_what_was_put_back_and_never_among_it(self):
        snap, path, owners = self.rewritten()
        (self.user / "console_history.txt").write_text("event x\n")
        set_mtime(self.user / "console_history.txt", NOW, 10)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.restored, out.retimed), (["console_history.txt"], ["pdx_settings.json"]))

    def test_nothing_is_listed_when_no_time_moved(self):
        snap = self.run_started()
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(out.retimed, [])
        self.assertNotIn("retimed", snapshot.journal(snap)[-1])

    def test_a_time_later_than_the_runs_end_is_someone_elses_and_stays(self):
        # The owner's launcher saved the same settings after the run: no hold (the bytes match), and their time.
        snap, path, owners = self.rewritten(seconds_into_run=self.RUN_SECONDS + restore.SLACK_SECONDS + 0.5)
        written = path.stat().st_mtime_ns
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.retimed), (False, []))
        self.assertEqual(path.stat().st_mtime_ns, written)

    def test_a_time_within_the_slack_after_the_end_is_the_runs(self):
        snap, path, owners = self.rewritten(seconds_into_run=self.RUN_SECONDS + restore.SLACK_SECONDS)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(out.retimed, ["pdx_settings.json"])
        self.assertEqual(path.stat().st_mtime_ns, owners)

    def test_without_a_recorded_end_no_time_is_touched(self):
        path = self.user / "pdx_settings.json"
        set_mtime(path, NOW, -86400)
        snap = self.take()                                          # no journal: nothing says when a run ended
        path.write_bytes(path.read_bytes())
        set_mtime(path, NOW, 30)
        written = path.stat().st_mtime_ns
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.retimed), (False, []))
        self.assertEqual(path.stat().st_mtime_ns, written)

    def test_with_only_a_start_recorded_the_start_is_the_limit(self):
        snap, path, owners = self.rewritten(seconds_into_run=30.0, exited=False)
        written = path.stat().st_mtime_ns
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(out.retimed, [])
        self.assertEqual(path.stat().st_mtime_ns, written)

    def test_a_time_earlier_than_the_snapshots_is_not_the_runs_and_stays(self):
        snap, path, owners = self.rewritten()
        set_mtime(path, NOW, -2 * 86400)
        earlier = path.stat().st_mtime_ns
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(out.retimed, [])
        self.assertEqual(path.stat().st_mtime_ns, earlier)

    def test_a_log_is_retimed_with_the_rest_and_left_alone_when_told_to_leave_the_logs(self):
        for logs, expected in ((True, ["logs/error.log"]), (False, [])):
            with self.subTest(logs=logs):
                snap, path, owners = self.rewritten("logs/error.log")
                written = path.stat().st_mtime_ns
                out = restore.restore(snap, self.user, other_game_running=False, logs=logs)
                self.assertEqual(out.retimed, expected)
                self.assertEqual(path.stat().st_mtime_ns, owners if logs else written)

    def test_restoring_twice_retimes_nothing_the_second_time(self):
        snap, path, owners = self.rewritten()
        restore.restore(snap, self.user, other_game_running=False)
        again = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((again.restored, again.removed, again.retimed), ([], [], []))
        self.assertEqual(path.stat().st_mtime_ns, owners)

    def test_a_hold_retimes_nothing(self):
        snap, path, owners = self.rewritten()
        written = path.stat().st_mtime_ns
        late = self.user / "continue_game.json"
        late.write_text("{}")
        set_mtime(late, NOW, 600)                                   # the owner has played since
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason, out.retimed), (True, "modified_after_exit", []))
        self.assertEqual(path.stat().st_mtime_ns, written)
        self.assertTrue(restore.restore(snap, self.user, other_game_running=True).held)
        self.assertEqual(path.stat().st_mtime_ns, written)

    def test_a_restore_stopped_part_way_retimes_nothing(self):
        snap, path, owners = self.rewritten()
        written = path.stat().st_mtime_ns
        history = self.user / "console_history.txt"
        history.write_text("event x\n")
        set_mtime(history, NOW, 10)
        real = restore._copy_logs_out

        def the_owner_types(*args, **kwargs):
            real(*args, **kwargs)
            history.write_text("the owner typed this")
        with mock.patch.object(restore, "_copy_logs_out", the_owner_types):
            out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason, out.retimed), (True, "modified_during_restore", []))
        self.assertEqual(path.stat().st_mtime_ns, written)

    def test_a_file_written_again_since_the_comparison_keeps_the_time_it_has(self):
        snap, path, owners = self.rewritten()
        real = restore._copy_logs_out

        def someone_saves_the_same_settings(*args, **kwargs):      # after the comparison, before any change
            real(*args, **kwargs)
            set_mtime(path, NOW, 45)
        with mock.patch.object(restore, "_copy_logs_out", someone_saves_the_same_settings):
            out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.retimed), (False, []))
        self.assertEqual(path.stat().st_mtime, NOW.timestamp() + 45)

    def test_other_bytes_written_in_the_moment_before_the_time_is_set_do_not_keep_the_snapshots_time(self):
        # The one moment nothing can close by looking first: between the last look and the time being set. The
        # file is hashed again afterwards, and one that no longer holds the snapshot's bytes gets the present
        # time, since `snapshot.take` trusts a stored file's size and time and would not read it again.
        snap, path, owners = self.rewritten()
        mine = bytes(b ^ 1 for b in path.read_bytes())              # the same size
        real = os.utime
        calls = []

        def utime(target, *args, **kwargs):
            if Path(target) == path:                                # copying the logs out sets times too
                calls.append((args, kwargs.get("ns")))
                if len(calls) == 1:
                    path.write_bytes(mine)
            return real(target, *args, **kwargs)
        began = time.time()
        with mock.patch.object(restore.os, "utime", utime):
            out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1][1], owners)                    # the snapshot's time was set
        self.assertEqual(calls[1], ((), None))                      # and then the present one
        self.assertEqual((out.held, out.retimed), (False, []))
        self.assertEqual(path.read_bytes(), mine)                   # theirs, untouched
        self.assertNotEqual(path.stat().st_mtime_ns, owners)
        self.assertGreaterEqual(path.stat().st_mtime, began - 5)   # the present time (the clock may step a little)
        again = snapshot.take(self.user, self.backups, now=self.next_time())
        self.assertNotEqual(again.files["pdx_settings.json"].sha256, snap.files["pdx_settings.json"].sha256)

    # Once the snapshot's time is on a file it stays only if the file was then read whole and hashed to the
    # snapshot's bytes. Every other way out takes the time off again, and when that fails too the snapshot is held.

    def failing_hash(self, path, error):
        """`restore._sha256`, raising `error` for `path` once the snapshot's time has been set on it."""
        real = restore._sha256
        entry_time = {}

        def sha(target):
            if Path(target) == path and path.stat().st_mtime_ns == entry_time.get("ns"):
                raise error
            return real(target)
        return sha, entry_time

    def test_a_file_that_cannot_be_read_back_does_not_keep_the_snapshots_time(self):
        # A writer came between the last look and the time being set (other bytes, the same size) and still has
        # the file open, so the hash that would have caught it fails. The time must not stay the snapshot's.
        snap, path, owners = self.rewritten()
        mine = bytes(b ^ 1 for b in path.read_bytes())
        sha, entry_time = self.failing_hash(path, PermissionError(13, "sharing violation"))
        entry_time["ns"] = owners
        real = os.utime
        wrote = []

        def utime(target, *args, **kwargs):
            if Path(target) == path and kwargs.get("ns") is not None and not wrote:
                path.write_bytes(mine)
                wrote.append(1)
            return real(target, *args, **kwargs)
        began = time.time()
        with mock.patch.object(restore.os, "utime", utime), mock.patch.object(restore, "_sha256", sha):
            out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.retimed), (False, []))
        self.assertEqual(path.read_bytes(), mine)
        self.assertNotEqual(path.stat().st_mtime_ns, owners)
        self.assertGreaterEqual(path.stat().st_mtime, began - 5)
        self.assertEqual(events(snap)[-1], "restored")
        # so the next snapshot reads the file, and a later run's restore leaves the newer bytes alone
        again = snapshot.take(self.user, self.backups, now=self.next_time())
        self.assertEqual(again.files["pdx_settings.json"].sha256, hashlib.sha256(mine).hexdigest())
        later = NOW + timedelta(days=1)
        snapshot.record(again, "started", now=later, pid=1, created="x")
        finish(again, at=later + timedelta(seconds=60))
        self.assertEqual(restore.restore(again, self.user, other_game_running=False).restored, [])
        self.assertEqual(path.read_bytes(), mine)

    def test_a_file_that_cannot_be_read_back_is_not_listed_though_its_bytes_are_the_snapshots(self):
        snap, path, owners = self.rewritten()
        before = path.read_bytes()
        sha, entry_time = self.failing_hash(path, OSError(5, "Input/output error"))
        entry_time["ns"] = owners
        with mock.patch.object(restore, "_sha256", sha):
            out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.retimed), (False, []))
        self.assertEqual(path.read_bytes(), before)
        self.assertNotEqual(path.stat().st_mtime_ns, owners)        # not vouched for: not the snapshot's time
        self.assertNotIn("retimed", snapshot.journal(snap)[-1])

    def test_an_interrupt_while_the_file_is_read_back_takes_the_time_off_first(self):
        snap, path, owners = self.rewritten()
        sha, entry_time = self.failing_hash(path, KeyboardInterrupt())
        entry_time["ns"] = owners
        with mock.patch.object(restore, "_sha256", sha), self.assertRaises(KeyboardInterrupt):
            restore.restore(snap, self.user, other_game_running=False)
        self.assertNotEqual(path.stat().st_mtime_ns, owners)
        self.assertNotIn("restored", events(snap))                  # nothing was recorded: the restore runs again

    def unsettable(self, path, owners, refuse):
        """`os.utime` that sets the snapshot's time on `path` and then fails for it as `refuse(kwargs)` says."""
        real = os.utime

        def utime(target, *args, **kwargs):
            if Path(target) == path and path.stat().st_mtime_ns == owners and refuse(kwargs):
                raise PermissionError(13, "sharing violation")
            return real(target, *args, **kwargs)
        return utime

    def test_when_the_present_time_cannot_be_set_the_file_gets_back_the_time_it_had(self):
        snap, path, owners = self.rewritten()
        written = path.stat().st_mtime_ns
        sha, entry_time = self.failing_hash(path, PermissionError(13, "sharing violation"))
        entry_time["ns"] = owners
        utime = self.unsettable(path, owners, lambda kwargs: kwargs.get("ns") is None)
        with mock.patch.object(restore.os, "utime", utime), mock.patch.object(restore, "_sha256", sha):
            out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.retimed), (False, []))
        self.assertEqual(path.stat().st_mtime_ns, written)

    def test_a_time_that_can_be_neither_vouched_for_nor_taken_back_holds_the_snapshot_and_names_the_file(self):
        # The last resort: the snapshot's time is on the file, the file cannot be read, and no other time will
        # go on. That is never a clean restore: the snapshot is held, with the file, for the owner to look at.
        log = self.user / "logs/error.log"                          # a second file the run wrote again
        set_mtime(log, NOW, -86400)
        log_owners = log.stat().st_mtime_ns
        snap, path, owners = self.rewritten()
        set_mtime(log, NOW, 20)
        (self.user / "console_history.txt").write_text("event x\n")
        set_mtime(self.user / "console_history.txt", NOW, 10)
        sha, entry_time = self.failing_hash(path, PermissionError(13, "sharing violation"))
        entry_time["ns"] = owners
        utime = self.unsettable(path, owners, lambda kwargs: True)
        with mock.patch.object(restore.os, "utime", utime), mock.patch.object(restore, "_sha256", sha):
            out = restore.restore(snap, self.user, other_game_running=False, now=NOW)
        self.assertEqual((out.held, out.reason), (True, "retime_unverified"))
        self.assertEqual((out.restored, out.removed, out.retimed), (["console_history.txt"], [], ["logs/error.log"]))
        self.assertEqual(path.stat().st_mtime_ns, owners)           # what the hold is for
        self.assertEqual(snapshot.journal(snap)[-1], {
            "event": "held", "at": "2026-11-10T12:00:00Z", "reason": "retime_unverified",
            "files": ["pdx_settings.json"], "restored": ["console_history.txt"], "retimed": ["logs/error.log"]})
        self.assertNotIn("restored", events(snap))
        self.assertEqual([s.id for s in restore.held(self.backups)], [snap.id])
        self.assertEqual(log.stat().st_mtime_ns, log_owners)        # done before it (in name order), and kept

    def test_a_file_gone_once_its_time_was_set_is_nothing_to_hold_for(self):
        snap, path, owners = self.rewritten()
        real = restore._sha256

        def sha(target):
            if Path(target) == path and path.stat().st_mtime_ns == owners:
                path.unlink()
            return real(target)
        with mock.patch.object(restore, "_sha256", sha):
            out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.retimed), (False, []))
        self.assertFalse(path.exists())

    def test_a_link_where_the_file_was_is_never_retimed_nor_is_what_it_points_to(self):
        snap, path, owners = self.rewritten()
        elsewhere = self.tmp / "elsewhere.json"
        os.replace(path, elsewhere)                                 # same bytes, the run's time
        os.symlink(elsewhere, path)
        written = elsewhere.stat().st_mtime_ns
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.restored, out.retimed), (False, [], []))
        self.assertTrue(path.is_symlink())
        self.assertEqual(elsewhere.stat().st_mtime_ns, written)

    def test_a_time_that_cannot_be_set_fails_nothing(self):
        snap, path, owners = self.rewritten()
        written = path.stat().st_mtime_ns
        (self.user / "console_history.txt").write_text("event x\n")
        set_mtime(self.user / "console_history.txt", NOW, 10)
        real = os.utime

        def utime(target, *args, **kwargs):
            if Path(target) == path:
                raise PermissionError(13, "Permission denied")
            return real(target, *args, **kwargs)
        with mock.patch.object(restore.os, "utime", utime):
            out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.restored, out.retimed), (False, ["console_history.txt"], []))
        self.assertEqual(path.stat().st_mtime_ns, written)
        self.assertEqual(events(snap)[-1], "restored")


class FailureTests(RestoreTestCase):
    def run_that_changed_two_files(self):
        snap = self.run_started()
        (self.user / "continue_game.json").write_text("{}")
        (self.user / "console_history.txt").write_text("event x\n")
        (self.user / "tests.txt").write_text("Tests:\n")
        finish(snap)
        return snap

    def test_a_missing_store_file_raises_before_anything_is_changed(self):
        snap = self.run_that_changed_two_files()
        blob(self.backups, snap.files["continue_game.json"]).unlink()
        before = tree(self.user)
        with self.assertRaises(FileNotFoundError):
            restore.restore(snap, self.user, other_game_running=False, run_logs_dir=self.tmp / "runlogs")
        self.assertEqual(tree(self.user), before)
        self.assertEqual(events(snap), ["started", "game_exited"])
        self.assertFalse((self.tmp / "runlogs").exists())

    def test_a_truncated_store_file_raises_before_anything_is_changed(self):
        snap = self.run_that_changed_two_files()
        blob(self.backups, snap.files["console_history.txt"]).write_bytes(b"torn")
        before = tree(self.user)
        with self.assertRaises(OSError):
            restore.restore(snap, self.user, other_game_running=False, run_logs_dir=self.tmp / "runlogs")
        self.assertEqual(tree(self.user), before)
        self.assertEqual(events(snap), ["started", "game_exited"])
        self.assertFalse((self.tmp / "runlogs").exists())

    def test_a_damaged_store_file_is_never_put_back(self):
        # the right size, the wrong bytes: only reading it can tell
        snap = self.run_that_changed_two_files()
        entry = snap.files["continue_game.json"]
        blob(self.backups, entry).write_bytes(b"x" * entry.size)
        before = tree(self.user)
        with self.assertRaises(OSError):
            restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(tree(self.user), before)
        self.assertEqual(events(snap), ["started", "game_exited"])

    def test_a_failure_while_putting_back_is_not_recorded_as_restored(self):
        snap = self.run_that_changed_two_files()
        with mock.patch("os.replace", side_effect=OSError("disk fell off")):
            with self.assertRaises(OSError):
                restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(events(snap), ["started", "game_exited"])
        self.assertFalse([p for p in self.user.rglob("*") if "te_qa_restore" in p.name])

    def test_a_retry_finishes_a_restore_whose_second_rename_failed(self):
        snap = self.run_that_changed_two_files()
        real_replace, targets = os.replace, []

        def flaky(source, target):
            targets.append(Path(target).name)
            if len(targets) == 2:
                raise OSError("disk fell off")
            real_replace(source, target)

        with mock.patch("os.replace", flaky):
            with self.assertRaises(OSError):
                restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual(targets, ["console_history.txt", "continue_game.json"])
        self.assertEqual((self.user / "console_history.txt").read_bytes(), b"set_variable x\n")  # already back
        self.assertEqual((self.user / "continue_game.json").read_text(), "{}")  # still the run's
        self.assertEqual(events(snap), ["started", "game_exited"])
        self.assertFalse([p for p in self.user.rglob("*") if "te_qa_restore" in p.name])
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.restored, out.removed), (False, ["continue_game.json"], ["tests.txt"]))
        self.assertEqual(restore.compare(snap, self.user), restore.Diff([], [], [], []))
        self.assertEqual(events(snap)[-1], "restored")


class HoldTests(RestoreTestCase):
    def test_other_game_running_holds(self):
        snap = self.run_started()
        (self.user / "continue_game.json").write_text("{}")
        finish(snap)
        out = restore.restore(snap, self.user, other_game_running=True)
        self.assertEqual((out.held, out.reason, out.restored), (True, "other_game_running", []))
        self.assertEqual((self.user / "continue_game.json").read_text(), "{}")

    def test_file_modified_after_exit_holds(self):
        snap = self.run_started()
        finish(snap, at=NOW)
        p = self.user / "save games/autosave.v3"
        p.write_bytes(b"the owner played since")
        os.utime(p, (NOW.timestamp() + 600, NOW.timestamp() + 600))
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason), (True, "modified_after_exit"))
        self.assertEqual(p.read_bytes(), b"the owner played since")

    def test_a_hold_changes_nothing_in_user_data_and_copies_no_logs(self):
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)
        (self.user / "logs/debug.log").write_text("the run's log\n")
        (self.user / "tests.txt").write_text("Tests:\n")
        (self.user / "save games/autosave_2.v3").write_bytes(b"pushed in")
        p = self.user / "continue_game.json"
        p.write_text("{}")
        set_mtime(p, NOW, 600)
        (self.user / "logs/debug.log.te_qa_restore.tmp").write_bytes(b"not ours to clear while holding")
        before = tree(self.user)
        out = restore.restore(snap, self.user, other_game_running=False, run_logs_dir=self.tmp / "runlogs")
        self.assertEqual((out.held, out.restored, out.removed), (True, [], []))
        self.assertEqual(tree(self.user), before)
        self.assertFalse((self.tmp / "runlogs").exists())
        restore.restore(snap, self.user, other_game_running=False)  # again, with the default folder
        self.assertEqual(tree(self.user), before)
        self.assertFalse((snap.dir / "run_logs").exists())

    def test_the_held_entry_gives_the_reason_and_the_files(self):
        out = self.edit_after_exit(600)
        self.assertEqual((out.held, out.reason), (True, "modified_after_exit"))
        entry = snapshot.journal(snapshot.all_snapshots(self.backups)[0])[-1]
        self.assertEqual(
            entry,
            {"event": "held", "at": entry["at"], "reason": "modified_after_exit", "files": ["continue_game.json"]},
        )

    def test_another_game_running_holds_before_anything_is_read(self):
        snap = self.run_started()
        finish(snap)
        with mock.patch.object(restore, "_sha256", side_effect=PermissionError("locked by the running game")):
            out = restore.restore(snap, self.user, other_game_running=True)
        self.assertEqual((out.held, out.reason), (True, "other_game_running"))
        self.assertEqual(snapshot.journal(snap)[-1]["reason"], "other_game_running")

    def test_a_restored_snapshot_is_not_held_because_another_game_is_running(self):
        snap = self.finished_run()
        journal = snapshot.journal(snap)
        out = restore.restore(snap, self.user, other_game_running=True)
        self.assertEqual(out, restore.Outcome([], [], False, "already_restored"))
        self.assertEqual(snapshot.journal(snap), journal)
        self.assertEqual(restore.held(self.backups), [])

    def test_a_held_snapshot_is_held_again_while_another_game_is_running(self):
        snap = self.held_run()
        out = restore.restore(snap, self.user, other_game_running=True)
        self.assertEqual((out.held, out.reason), (True, "other_game_running"))
        self.assertEqual(events(snap)[-2:], ["held", "held"])

    def test_a_snapshot_restored_after_a_hold_is_not_held_by_another_game_either(self):
        snap = self.held_run()
        restore.restore(snap, self.user, other_game_running=False)
        out = restore.restore(snap, self.user, other_game_running=True)
        self.assertEqual((out.held, out.reason), (False, "already_restored"))
        self.assertEqual(restore.held(self.backups), [])

    def test_restoring_a_restored_snapshot_again_with_no_other_game_still_runs(self):
        snap = self.run_started()
        (self.user / "continue_game.json").write_text("{}")
        finish(snap)
        restore.restore(snap, self.user, other_game_running=False)
        (self.user / "continue_game.json").write_text("{}")  # the run's file is back, say, from a stray process
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.restored), (False, ["continue_game.json"]))

    def test_logs_never_cause_a_hold(self):
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)
        for name in ("debug.log", "game.log"):  # one the run changed, one it created
            (self.user / "logs" / name).write_text("written after the exit")
            set_mtime(self.user / "logs" / name, NOW, 600)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason, out.restored, out.removed), (False, "", ["logs/debug.log"], ["logs/game.log"]))

    def test_a_late_log_does_not_excuse_a_late_save(self):
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)
        for name in ("logs/debug.log", "save games/autosave.v3"):
            (self.user / name).write_text("written after the exit")
            set_mtime(self.user / name, NOW, 600)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason), (True, "modified_after_exit"))
        self.assertEqual(snapshot.journal(snap)[-1]["files"], ["save games/autosave.v3"])

    def test_without_a_reference_time_a_file_to_judge_holds_and_nothing_changes(self):
        snap = snapshot.take(self.user, self.backups, now=NOW)  # no journal at all
        (self.user / "continue_game.json").write_text("{}")
        before = tree(self.user)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason, out.restored, out.removed), (True, "no_reference_time", [], []))
        self.assertEqual(tree(self.user), before)
        self.assertEqual(snapshot.journal(snap)[-1]["reason"], "no_reference_time")

    def test_without_a_reference_time_a_created_file_holds_too(self):
        snap = snapshot.take(self.user, self.backups, now=NOW)
        (self.user / "tests.txt").write_text("Tests:\n")
        self.assertEqual(restore.restore(snap, self.user, other_game_running=False).reason, "no_reference_time")
        self.assertTrue((self.user / "tests.txt").exists())

    def test_a_target_changed_since_the_comparison_is_not_overwritten(self):
        snap = self.run_started()
        (self.user / "console_history.txt").write_text("event x\n")
        (self.user / "continue_game.json").write_text("{}")
        finish(snap)
        out = self.restore_while(snap, lambda: (self.user / "console_history.txt").write_text("the owner typed this"))
        self.assertEqual((out.held, out.reason, out.restored, out.removed), (True, "modified_during_restore", [], []))
        self.assertEqual((self.user / "console_history.txt").read_text(), "the owner typed this")
        self.assertEqual((self.user / "continue_game.json").read_text(), "{}")  # nothing further was restored
        entry = snapshot.journal(snap)[-1]
        self.assertEqual((entry["event"], entry["reason"], entry["files"]), ("held", "modified_during_restore", ["console_history.txt"]))
        self.assertFalse([p for p in self.user.rglob("*") if "te_qa_restore" in p.name])

    def test_a_missing_target_that_has_appeared_is_not_overwritten(self):
        snap = self.run_started()
        (self.user / "console_history.txt").unlink()
        finish(snap)
        out = self.restore_while(snap, lambda: (self.user / "console_history.txt").write_text("a new game wrote this"))
        self.assertEqual((out.held, out.reason), (True, "modified_during_restore"))
        self.assertEqual((self.user / "console_history.txt").read_text(), "a new game wrote this")

    def test_files_already_put_back_stay_when_a_later_target_has_changed(self):
        snap = self.run_started()
        (self.user / "console_history.txt").write_text("event x\n")
        (self.user / "continue_game.json").write_text("{}")
        finish(snap)
        real_replace, renamed = os.replace, []

        def replace_then_interfere(source, target):
            real_replace(source, target)
            renamed.append(Path(target).name)
            if len(renamed) == 1:
                (self.user / "continue_game.json").write_text("the owner played")

        with mock.patch("os.replace", replace_then_interfere):
            out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason, out.restored), (True, "modified_during_restore", ["console_history.txt"]))
        self.assertEqual((self.user / "console_history.txt").read_bytes(), b"set_variable x\n")
        self.assertEqual((self.user / "continue_game.json").read_text(), "the owner played")
        entry = snapshot.journal(snap)[-1]
        self.assertEqual((entry["restored"], entry["files"]), (["console_history.txt"], ["continue_game.json"]))
        self.assertFalse([p for p in self.user.rglob("*") if "te_qa_restore" in p.name])

    def test_a_file_to_remove_that_has_changed_since_the_comparison_is_kept(self):
        snap = self.run_started()
        (self.user / "tests.txt").write_text("Tests:\n")
        (self.user / "logs/game.log").write_text("created by the run")
        finish(snap)
        out = self.restore_while(snap, lambda: (self.user / "tests.txt").write_text("Tests: and the owner's notes\n"))
        self.assertEqual((out.held, out.reason), (True, "modified_during_restore"))
        self.assertEqual((self.user / "tests.txt").read_text(), "Tests: and the owner's notes\n")
        self.assertEqual(snapshot.journal(snap)[-1]["files"], ["tests.txt"])

    def restore_while(self, snap, interfere):
        """Restore, with `interfere()` run after the comparison and before the first change to the folder."""
        real = restore._copy_logs_out

        def interfering(*args, **kwargs):
            real(*args, **kwargs)
            interfere()

        with mock.patch.object(restore, "_copy_logs_out", interfering):
            return restore.restore(snap, self.user, other_game_running=False)

    def test_another_game_running_is_the_reason_given_first(self):
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)
        p = self.user / "continue_game.json"
        p.write_text("{}")
        set_mtime(p, NOW, 600)
        out = restore.restore(snap, self.user, other_game_running=True)
        self.assertEqual(out.reason, "other_game_running")
        self.assertEqual(snapshot.journal(snap)[-1]["reason"], "other_game_running")

    def test_a_hold_is_recorded_with_the_given_time(self):
        snap = self.run_started()
        finish(snap)
        restore.restore(snap, self.user, other_game_running=True, now=NOW)
        self.assertEqual(snapshot.journal(snap)[-1]["at"], "2026-11-10T12:00:00Z")

    def test_a_change_within_the_slack_after_exit_is_restored(self):
        self.assertEqual(restore.SLACK_SECONDS, 2.0)
        self.assertFalse(self.edit_after_exit(1).held)

    def test_a_change_exactly_the_slack_after_exit_is_restored(self):
        self.assertFalse(self.edit_after_exit(restore.SLACK_SECONDS).held)

    def test_a_change_beyond_the_slack_after_exit_holds(self):
        self.assertTrue(self.edit_after_exit(3).held)

    def test_a_dangling_link_where_a_file_was_is_missing_and_never_holds(self):
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)
        p = self.user / "console_history.txt"
        p.unlink()
        p.symlink_to("nowhere")
        late = NOW.timestamp() + 600
        os.utime(p, (late, late), follow_symlinks=False)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.restored), (False, ["console_history.txt"]))
        self.assertFalse(p.is_symlink())
        self.assertEqual(p.read_bytes(), b"set_variable x\n")

    def test_a_created_file_modified_after_exit_holds(self):
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)
        p = self.user / "tests.txt"
        p.write_text("Tests:\n")
        set_mtime(p, NOW, 600)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason), (True, "modified_after_exit"))
        self.assertTrue(p.exists())

    def test_an_added_file_modified_after_exit_holds(self):
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)
        p = self.user / "save games/autosave_5.v3"
        p.write_bytes(b"x")
        set_mtime(p, NOW, 600)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason), (True, "modified_after_exit"))
        self.assertTrue(p.exists())

    def test_a_file_the_run_never_touched_does_not_hold_however_new_it_is(self):
        # only files that differ from the snapshot count; the owner's other files do not
        snap = self.run_started(at=NOW)
        finish(snap, at=NOW)
        set_mtime(self.user / "save games/mine.v3", NOW, 600)
        (self.user / "notes.txt").write_text("not in any set")
        set_mtime(self.user / "notes.txt", NOW, 600)
        (self.user / "console_history.txt").write_text("event x\n")
        set_mtime(self.user / "console_history.txt", NOW, 1)  # the run's own change, just before its exit
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.restored), (False, ["console_history.txt"]))


class ReferenceTimeTests(RestoreTestCase):
    """The reference time is the journal's game_exited, else its last heartbeat, else started."""

    def edit_at(self, snap, offset_seconds):
        p = self.user / "continue_game.json"
        p.write_text("{}")
        set_mtime(p, NOW, offset_seconds)

    def test_the_exit_is_preferred_to_a_later_heartbeat(self):
        snap = self.run_started(at=NOW)
        snapshot.record(snap, "heartbeat", now=NOW + timedelta(minutes=10))
        finish(snap, at=NOW + timedelta(minutes=1))
        self.edit_at(snap, 300)
        self.assertTrue(restore.restore(snap, self.user, other_game_running=False).held)

    def test_the_last_heartbeat_is_used_without_an_exit(self):
        snap = self.run_started(at=NOW)
        snapshot.record(snap, "heartbeat", now=NOW + timedelta(minutes=1))
        snapshot.record(snap, "heartbeat", now=NOW + timedelta(minutes=10))
        self.edit_at(snap, 9 * 60)
        self.assertFalse(restore.restore(snap, self.user, other_game_running=False).held)

    def test_the_start_is_used_without_an_exit_or_heartbeat(self):
        snap = self.run_started(at=NOW)
        self.edit_at(snap, 600)
        self.assertTrue(restore.restore(snap, self.user, other_game_running=False).held)

    def test_the_start_is_used_without_an_exit_or_heartbeat_and_a_file_before_it_restores(self):
        snap = self.run_started(at=NOW)
        self.edit_at(snap, 1)
        self.assertFalse(restore.restore(snap, self.user, other_game_running=False).held)

    def test_a_snapshot_with_no_journal_has_no_reference_time_and_does_not_borrow_one(self):
        # the time in the snapshot's id is the WSL clock's; the hold rule compares only the drive's times
        snap = snapshot.take(self.user, self.backups, now=NOW)
        self.edit_at(snap, 1)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason), (True, "no_reference_time"))

    def test_a_snapshot_with_no_journal_and_nothing_to_judge_restores(self):
        snap = snapshot.take(self.user, self.backups, now=NOW)
        (self.user / "console_history.txt").unlink()  # missing: no time
        (self.user / "logs/debug.log").write_text("the run's log\n")  # a log: never judged
        (self.user / "logs/game.log").write_text("created by the run")
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.restored, out.removed), (False, ["console_history.txt", "logs/debug.log"], ["logs/game.log"]))

    def test_a_snapshot_with_no_journal_restores_into_an_empty_folder(self):
        # what the command line's self-test does
        snap = snapshot.take(self.user, self.backups, now=NOW)
        empty = self.tmp / "empty"
        empty.mkdir()
        out = restore.restore(snap, empty, other_game_running=False)
        self.assertEqual((out.held, sorted(out.restored)), (False, sorted(snap.files)))
        self.assertEqual({rel: (empty / rel).read_bytes() for rel in snap.files},
                         {rel: (self.user / rel).read_bytes() for rel in snap.files})

    def test_times_are_utc_whatever_the_machine_zone(self):
        # a journal time parsed as local time is off by the zone's offset; CI runs in UTC and never sees it
        if not hasattr(time, "tzset"):
            self.skipTest("needs time.tzset")
        self.addCleanup(time.tzset)
        with mock.patch.dict(os.environ, {"TZ": "XXX-13"}):  # 13 hours ahead of UTC
            time.tzset()
            snap = self.run_started(at=NOW)
            finish(snap, at=NOW)
            self.edit_at(snap, 1)
            self.assertFalse(restore.restore(snap, self.user, other_game_running=False).held)


class RecoverTests(RestoreTestCase):
    def test_dead_run_uses_its_last_heartbeat(self):
        snap = self.run_started(at=NOW)
        snapshot.record(snap, "heartbeat", now=NOW + timedelta(minutes=5))
        p = self.user / "continue_game.json"
        p.write_text("{}")
        os.utime(p, ((NOW + timedelta(minutes=4)).timestamp(),) * 2)
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: False)
        self.assertEqual(out[0][1].held, False)

    def test_recover_leaves_a_run_whose_game_is_still_up(self):
        snap = self.run_started()
        (self.user / "continue_game.json").write_text("{}")
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: True)
        self.assertEqual(out[0][1].reason, "game_still_up")
        self.assertEqual((self.user / "continue_game.json").read_text(), "{}")
        self.assertEqual([s.id for s in restore.unfinished(self.backups)], [snap.id])

    def test_a_run_whose_game_is_still_up_gets_no_journal_entry(self):
        snap = self.run_started()
        before = snapshot.journal(snap)
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: True)
        self.assertEqual(out, [(snap.id, restore.Outcome([], [], False, "game_still_up"))])
        self.assertEqual(snapshot.journal(snap), before)

    def dead_run(self, at, content, pid):
        """A run snapshotted at `at` that replaced continue_game.json 10 s later and died 30 s after that."""
        snap = self.run_started(at=at, pid=pid)
        path = self.user / "continue_game.json"
        path.write_text(content)
        set_mtime(path, at, 10)
        snapshot.record(snap, "heartbeat", now=at + timedelta(seconds=40))
        return snap

    def test_recover_hands_each_started_entry_to_own_game_up_newest_first(self):
        first = self.run_started(pid=11)
        second = self.run_started(pid=22)
        seen = []

        def own_game_up(started):
            seen.append((started["event"], started["pid"], started["created"]))
            return False

        out = restore.recover(self.backups, self.user, False, own_game_up=own_game_up)
        self.assertEqual(sorted(seen), [("started", 11, "2026-11-10T12:00:00Z"), ("started", 22, "2026-11-10T12:00:00Z")])
        self.assertEqual([snap_id for snap_id, _ in out], [second.id, first.id])
        self.assertEqual(events(first)[-1], "restored")
        self.assertEqual(events(second)[-1], "restored")

    def test_nested_unfinished_runs_unwind_newest_first_to_the_owners_own_bytes(self):
        # run A dies with the owner's file replaced; B is snapshotted over A's leftovers and dies too.
        # Oldest first would end in A's leftovers (B's manifest holds them) with both journals "restored".
        path = self.user / "continue_game.json"
        original = path.read_bytes()
        original_mtime = path.stat().st_mtime_ns
        first = self.dead_run(NOW, "A's leftover", pid=11)
        second = self.dead_run(NOW + timedelta(seconds=120), "B's leftover", pid=22)
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: False)
        self.assertEqual(
            [(snap_id, o.held, o.reason, o.restored) for snap_id, o in out],
            [(second.id, False, "", ["continue_game.json"]), (first.id, False, "", ["continue_game.json"])],
        )
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), (original, original_mtime))
        self.assertEqual(restore.unfinished(self.backups), [])

    def test_nothing_is_restored_while_any_unfinished_runs_game_is_still_up(self):
        first = self.dead_run(NOW, "A's leftover", pid=11)
        second = self.dead_run(NOW + timedelta(seconds=120), "B's leftover", pid=22)
        before, journals = tree(self.user), [snapshot.journal(first), snapshot.journal(second)]
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: started["pid"] == 11)
        self.assertEqual(
            out,
            [(second.id, restore.Outcome([], [], False, "game_still_up")),
             (first.id, restore.Outcome([], [], False, "game_still_up"))],
        )
        self.assertEqual(tree(self.user), before)
        self.assertEqual([snapshot.journal(first), snapshot.journal(second)], journals)
        self.assertEqual([s.id for s in restore.unfinished(self.backups)], [first.id, second.id])

    def test_an_error_is_reported_for_its_snapshot_and_stops_the_unwinding(self):
        first = self.dead_run(NOW, "A's leftover", pid=11)
        second = self.dead_run(NOW + timedelta(seconds=120), "B's leftover", pid=22)
        blob(self.backups, second.files["continue_game.json"]).unlink()  # what B would put back
        before, journals = tree(self.user), [snapshot.journal(first), snapshot.journal(second)]
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: False)
        self.assertEqual([snap_id for snap_id, _ in out], [second.id])
        outcome = out[0][1]
        self.assertEqual((outcome.restored, outcome.removed, outcome.held), ([], [], False))
        self.assertTrue(outcome.reason.startswith("error: "), outcome.reason)
        self.assertIn("continue_game.json", outcome.reason)
        self.assertEqual(tree(self.user), before)
        self.assertEqual([snapshot.journal(first), snapshot.journal(second)], journals)

    def test_the_unwinding_stops_at_the_first_hold(self):
        # a stack: what is under a held layer is not touched until the owner has dealt with it
        first = self.dead_run(NOW, "A's leftover", pid=11)
        second = self.dead_run(NOW + timedelta(seconds=120), "B's leftover", pid=22)
        before, first_journal = tree(self.user), snapshot.journal(first)
        out = restore.recover(self.backups, self.user, True, own_game_up=lambda started: False)
        self.assertEqual(out, [(second.id, restore.Outcome([], [], True, "other_game_running"))])
        self.assertEqual(tree(self.user), before)
        self.assertEqual(snapshot.journal(first), first_journal)
        self.assertEqual([s.id for s in restore.unfinished(self.backups)], [first.id])
        self.assertEqual([s.id for s in restore.held(self.backups)], [second.id])

    def test_the_unwinding_stops_at_a_hold_for_a_late_file_too(self):
        first = self.dead_run(NOW, "A's leftover", pid=11)
        second = self.dead_run(NOW + timedelta(seconds=120), "B's leftover", pid=22)
        set_mtime(self.user / "continue_game.json", NOW, 3600)  # someone used the folder after B died
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: False)
        self.assertEqual([(snap_id, o.held, o.reason) for snap_id, o in out], [(second.id, True, "modified_after_exit")])
        self.assertEqual([s.id for s in restore.unfinished(self.backups)], [first.id])

    def test_a_bad_started_entry_is_an_error_for_its_snapshot_and_nothing_is_restored(self):
        first = self.dead_run(NOW, "A's leftover", pid="not a number")
        second = self.dead_run(NOW + timedelta(seconds=120), "B's leftover", pid=22)
        before, journals = tree(self.user), [snapshot.journal(first), snapshot.journal(second)]
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: int(started["pid"]) < 0)
        self.assertEqual([snap_id for snap_id, _ in out], [first.id])
        outcome = out[0][1]
        self.assertEqual((outcome.restored, outcome.removed, outcome.held), ([], [], False))
        self.assertTrue(outcome.reason.startswith("error: "), outcome.reason)
        self.assertIn("not a number", outcome.reason)
        self.assertEqual(tree(self.user), before)  # even the newer, sound one waits: the older one's game is unknown
        self.assertEqual([snapshot.journal(first), snapshot.journal(second)], journals)
        self.assertEqual([s.id for s in restore.unfinished(self.backups)], [first.id, second.id])

    def test_the_last_started_entry_is_the_one_own_game_up_is_asked_about(self):
        snap = self.run_started(pid=11)
        snapshot.record(snap, "started", pid=22, created="2026-11-10T13:00:00Z")  # a relaunch
        seen = []
        restore.recover(self.backups, self.user, False, own_game_up=lambda started: seen.append(started) or False)
        self.assertEqual([(e["pid"], e["created"]) for e in seen], [(22, "2026-11-10T13:00:00Z")])

    def test_results_already_gathered_survive_an_error_further_down(self):
        first = self.dead_run(NOW, "A's leftover", pid=11)
        second = self.dead_run(NOW + timedelta(seconds=120), "B's leftover", pid=22)
        blob(self.backups, first.files["continue_game.json"]).unlink()  # what A would put back
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: False)
        self.assertEqual([snap_id for snap_id, _ in out], [second.id, first.id])
        self.assertEqual(events(second)[-1], "restored")
        self.assertTrue(out[1][1].reason.startswith("error: "))
        self.assertEqual([s.id for s in restore.unfinished(self.backups)], [first.id])

    def test_a_dead_runs_logs_are_kept_beside_its_journal(self):
        snap = self.run_started(at=NOW)
        (self.user / "logs/debug.log").write_text("the dead run's log\n")
        snapshot.record(snap, "heartbeat", now=NOW + timedelta(seconds=40))
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: False)
        self.assertFalse(out[0][1].held)
        self.assertEqual((snap.dir / "run_logs/debug.log").read_text(), "the dead run's log\n")
        self.assertNotEqual((self.user / "logs/debug.log").read_text(), "the dead run's log\n")

    def test_recover_holds_while_another_game_is_running(self):
        snap = self.run_started()
        (self.user / "continue_game.json").write_text("{}")
        out = restore.recover(self.backups, self.user, True, own_game_up=lambda started: False)
        self.assertEqual((out[0][1].held, out[0][1].reason), (True, "other_game_running"))
        self.assertEqual(events(snap)[-1], "held")
        self.assertEqual([s.id for s in restore.held(self.backups)], [snap.id])
        self.assertEqual(restore.unfinished(self.backups), [])

    def test_recover_does_not_ask_about_runs_that_are_finished(self):
        self.finished_run()
        self.held_run()
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: self.fail("asked"))
        self.assertEqual(out, [])

    def test_unfinished_and_held_tell_the_journals_apart(self):
        done = self.finished_run()
        held_one = self.held_run()
        open_one = self.run_started()
        self.take()  # taken, never started
        self.assertEqual([s.id for s in restore.unfinished(self.backups)], [open_one.id])
        self.assertEqual([s.id for s in restore.held(self.backups)], [held_one.id])
        self.assertNotIn(done.id, [s.id for s in restore.unfinished(self.backups) + restore.held(self.backups)])

    def test_a_held_run_that_is_restored_later_is_no_longer_held(self):
        snap = self.held_run()
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertFalse(out.held)
        self.assertEqual(restore.held(self.backups), [])
        self.assertEqual(restore.unfinished(self.backups), [])


class PruneTests(RestoreTestCase):
    def test_prune_keeps_five_and_never_held_unfinished_or_current(self):
        done = [self.finished_run() for _ in range(7)]
        held_one = self.held_run()
        open_one = self.run_started()
        current = self.finished_run()
        removed = restore.prune(self.backups, keep=5, current=current.id)
        self.assertEqual(removed, [s.id for s in done[:3]])  # 7 done + current = 8 restored; keep 5 incl. current
        for s in (held_one, open_one, current):
            self.assertTrue(s.dir.exists())
        for s in done[:3]:
            self.assertFalse(s.dir.exists())
        for s in done[3:]:
            self.assertTrue(s.dir.exists())

    def test_every_kept_snapshot_still_restores_after_a_prune(self):
        self.finished_run()
        (self.user / "continue_game.json").write_text("v2")
        for _ in range(6):
            self.finished_run()
        age_store(self.backups)
        restore.prune(self.backups, keep=5)
        kept = snapshot.all_snapshots(self.backups)
        self.assertEqual(len(kept), 5)
        for snap in kept:
            for entry in snap.files.values():
                self.assertTrue((self.backups / "store" / entry.sha256[:2] / entry.sha256).is_file())
            # and the whole snapshot comes back out of the store, byte for byte, with its recorded times
            target = self.tmp / ("restored " + snap.id)
            target.mkdir()
            out = restore.restore(snap, target, other_game_running=False)
            self.assertEqual((out.held, sorted(out.restored)), (False, sorted(snap.files)))
            for rel, entry in snap.files.items():
                self.assertEqual(hashlib.sha256((target / rel).read_bytes()).hexdigest(), entry.sha256, rel)
                self.assertEqual((target / rel).stat().st_mtime_ns, entry.mtime_ns, rel)

    def test_current_takes_a_slot_even_when_it_has_not_finished(self):
        # the real caller passes the snapshot it has just taken: no journal at all yet
        done = [self.finished_run() for _ in range(7)]
        current = self.take()
        removed = restore.prune(self.backups, keep=5, current=current.id)
        self.assertEqual(removed, [s.id for s in done[:3]])  # 4 restored + current = 5
        self.assertTrue(current.dir.exists())

    def test_default_keeps_the_last_five(self):
        done = [self.finished_run() for _ in range(7)]
        self.assertEqual(restore.prune(self.backups), [s.id for s in done[:2]])

    def test_nothing_is_removed_when_there_are_not_more_than_keep(self):
        for _ in range(3):
            self.finished_run()
        self.assertEqual(restore.prune(self.backups, keep=5), [])
        self.assertEqual(restore.prune(self.backups, keep=3), [])
        self.assertEqual(len(snapshot.all_snapshots(self.backups)), 3)

    def test_prune_without_a_backup_root_does_nothing(self):
        self.assertEqual(restore.prune(self.tmp / "nothing here"), [])

    def test_the_sweep_deletes_blobs_no_manifest_names(self):
        self.finished_run()
        (self.user / "continue_game.json").write_text("only in the first snapshot's successors")
        gone_sha = snapshot.all_snapshots(self.backups)[0].files["continue_game.json"].sha256
        for _ in range(6):
            self.finished_run()
        age_store(self.backups)
        removed = restore.prune(self.backups, keep=5)
        self.assertEqual(len(removed), 2)
        store = self.backups / "store"
        self.assertFalse((store / gone_sha[:2] / gone_sha).exists())
        for snap in snapshot.all_snapshots(self.backups):
            for entry in snap.files.values():
                self.assertTrue(blob(self.backups, entry).is_file())

    def test_the_sweep_touches_only_store_blobs(self):
        self.finished_run()
        store = self.backups / "store"
        orphan_sha = "ab" * 32
        (store / "ab").mkdir(exist_ok=True)
        (store / "ab" / orphan_sha).write_bytes(b"nobody names me")
        (store / "ab" / "notes.txt").write_text("not a blob")
        (store / ".incoming-abc123").write_bytes(b"a copy in progress")
        age_store(self.backups)
        os.utime(store / ".incoming-abc123", (0, 0))
        restore.prune(self.backups)
        self.assertFalse((store / "ab" / orphan_sha).exists())
        self.assertTrue((store / "ab" / "notes.txt").exists())
        self.assertTrue((store / ".incoming-abc123").exists())

    def test_blobs_of_held_and_unfinished_snapshots_survive_the_sweep(self):
        (self.user / "pdx_settings.json").write_text("held only")
        held_one = self.held_run()
        (self.user / "pdx_settings.json").write_text("unfinished only")
        open_one = self.run_started()
        (self.user / "pdx_settings.json").write_text("everyone else")
        for _ in range(3):
            self.finished_run()
        age_store(self.backups)
        removed = restore.prune(self.backups, keep=1)
        self.assertEqual(len(removed), 2)
        for snap in (held_one, open_one):
            for entry in snapshot.load(snap.dir).files.values():
                self.assertTrue(blob(self.backups, entry).is_file(), snap.id)

    def test_an_unreadable_manifest_stops_the_sweep(self):
        # what it names is unknown, so no blob can be called unreferenced
        self.finished_run()
        bad = self.backups / "snapshots" / "20200101T000000Z"
        bad.mkdir()
        (bad / "manifest.json").write_text('{"version": 1, "files": {')
        orphan = self.backups / "store" / "cd" / ("cd" * 32)
        orphan.parent.mkdir()
        orphan.write_bytes(b"maybe the broken manifest names me")
        age_store(self.backups)
        restore.prune(self.backups)
        self.assertTrue(orphan.exists())
        self.assertTrue(bad.exists())

    def test_a_folder_without_a_manifest_is_not_removed(self):
        done = [self.finished_run() for _ in range(6)]
        half = self.backups / "snapshots" / "20200101T000000Z"
        half.mkdir()
        (half / "manifest.json.tmp").write_text("{")
        self.assertEqual(restore.prune(self.backups, keep=5), [done[0].id])
        self.assertTrue((half / "manifest.json.tmp").exists())

    def test_a_store_file_younger_than_a_day_survives_the_sweep(self):
        # a take in another session copies its files before its manifest names them
        self.finished_run()
        age_store(self.backups)
        orphan = self.backups / "store" / "ab" / ("ab" * 32)
        orphan.parent.mkdir(exist_ok=True)
        orphan.write_bytes(b"a take is writing its manifest")
        restore.prune(self.backups)
        self.assertTrue(orphan.exists())
        day = restore.SWEEP_MIN_AGE_SECONDS
        self.assertEqual(day, 24 * 60 * 60)
        for age, swept in ((day - 600, False), (day + 600, True)):
            with self.subTest(age_seconds=age):
                orphan.write_bytes(b"a take is writing its manifest")
                when = time.time() - age
                os.utime(orphan, (when, when))
                restore.prune(self.backups)
                self.assertEqual(orphan.exists(), not swept)

    def test_the_same_blob_two_days_old_is_swept(self):
        self.finished_run()
        orphan = self.backups / "store" / "ab" / ("ab" * 32)
        orphan.parent.mkdir(exist_ok=True)
        orphan.write_bytes(b"nobody names me")
        restore.prune(self.backups)
        self.assertTrue(orphan.exists())  # fresh
        when = time.time() - 2 * 86400
        os.utime(orphan, (when, when))
        restore.prune(self.backups)
        self.assertFalse(orphan.exists())  # two days back

    def test_snapshots_with_no_journal_or_an_empty_one_count_as_finished(self):
        # taken and never launched, or self-tests: nothing will ever restore them
        idle = [self.take() for _ in range(2)]
        (idle[1].dir / "journal.jsonl").write_bytes(b"")
        done = [self.finished_run() for _ in range(5)]
        current = self.finished_run()
        removed = restore.prune(self.backups, keep=5, current=current.id)
        self.assertEqual(removed, [s.id for s in idle + done[:1]])  # 2 + 5 + current = 8; keep 5 incl. current
        self.assertEqual(restore.unfinished(self.backups), [])
        self.assertEqual(restore.held(self.backups), [])

    def test_a_journal_that_exists_but_does_not_parse_is_never_pruned_or_recovered(self):
        torn = self.take()
        (torn.dir / "journal.jsonl").write_bytes(b'{"event": "star')  # the machine died mid-write
        for _ in range(3):
            self.finished_run()
        (self.user / "continue_game.json").write_text("changed since")
        finished = [s.id for s in snapshot.all_snapshots(self.backups) if s.id != torn.id]
        self.assertEqual(restore.prune(self.backups, keep=0), finished)
        self.assertTrue(torn.dir.exists())
        self.assertEqual(restore.unfinished(self.backups), [])
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: self.fail("asked"))
        self.assertEqual(out, [])
        self.assertEqual((self.user / "continue_game.json").read_text(), "changed since")

    def test_a_journal_with_events_but_no_start_is_never_pruned(self):
        odd = self.take()
        snapshot.record(odd, "heartbeat")
        for _ in range(3):
            self.finished_run()
        restore.prune(self.backups, keep=0)
        self.assertTrue(odd.dir.exists())

    def test_a_pruned_snapshot_is_gone_whole(self):
        first = self.finished_run()
        for _ in range(5):
            self.finished_run()
        restore.prune(self.backups, keep=5)
        self.assertFalse(first.dir.exists())
        self.assertEqual(len(snapshot.all_snapshots(self.backups)), 5)


if __name__ == "__main__":
    unittest.main()
