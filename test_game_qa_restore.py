"""Tests for game_qa.restore: compare a user-data folder with a snapshot, put it back, hold when the owner has
changed it since, recover runs that never finished, and prune old snapshots.

No game and no Windows program is needed: every test builds its folders in a temp dir. The run's game is
played by the test itself: it edits files between `run_started` and `finish`.
"""

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

    Journal times have one-second resolution, so by default the exit is stamped at the next whole second:
    it is then never earlier than a file the test wrote a moment ago.
    """
    if at is None:
        at = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=1)
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


class RestoreTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.user = self.tmp / "user data"
        make_user_data(self.user)
        self.backups = self.tmp / "backups"

    def run_started(self, at=None, extra=(), pid=4242):
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
        before = tree(self.user)
        out = restore.restore(snap, self.user, other_game_running=False, run_logs_dir=self.tmp / "runlogs")
        self.assertEqual((out.held, out.restored, out.removed), (True, [], []))
        self.assertEqual(tree(self.user), before)
        self.assertFalse((self.tmp / "runlogs").exists())

    def test_the_held_entry_gives_the_reason_and_the_files(self):
        out = self.edit_after_exit(600)
        self.assertEqual((out.held, out.reason), (True, "modified_after_exit"))
        entry = snapshot.journal(snapshot.all_snapshots(self.backups)[0])[-1]
        self.assertEqual(
            entry,
            {"event": "held", "at": entry["at"], "reason": "modified_after_exit", "files": ["continue_game.json"]},
        )

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

    def test_a_snapshot_with_no_journal_falls_back_to_the_time_it_was_taken(self):
        snap = snapshot.take(self.user, self.backups, now=NOW)
        self.edit_at(snap, 600)
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.reason), (True, "modified_after_exit"))

    def test_a_snapshot_with_no_journal_and_nothing_to_check_restores(self):
        snap = snapshot.take(self.user, self.backups, now=NOW)
        (self.user / "console_history.txt").unlink()
        out = restore.restore(snap, self.user, other_game_running=False)
        self.assertEqual((out.held, out.restored), (False, ["console_history.txt"]))

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

    def test_recover_hands_each_started_entry_to_own_game_up_oldest_first(self):
        first = self.run_started(pid=11)
        second = self.run_started(pid=22)
        seen = []

        def own_game_up(started):
            seen.append((started["event"], started["pid"], started["created"]))
            return False

        out = restore.recover(self.backups, self.user, False, own_game_up=own_game_up)
        self.assertEqual(seen, [("started", 11, "2026-11-10T12:00:00Z"), ("started", 22, "2026-11-10T12:00:00Z")])
        self.assertEqual([snap_id for snap_id, _ in out], [first.id, second.id])
        self.assertEqual(events(first)[-1], "restored")
        self.assertEqual(events(second)[-1], "restored")

    def test_recover_goes_on_past_a_run_whose_game_is_still_up(self):
        first = self.run_started(pid=11)
        second = self.run_started(pid=22)
        out = restore.recover(self.backups, self.user, False, own_game_up=lambda started: started["pid"] == 11)
        self.assertEqual([(snap_id, o.reason) for snap_id, o in out], [(first.id, "game_still_up"), (second.id, "")])
        self.assertEqual([s.id for s in restore.unfinished(self.backups)], [first.id])

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
        snapshot.take(self.user, self.backups)  # taken, never started
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
        restore.prune(self.backups, keep=5)
        for snap in snapshot.all_snapshots(self.backups):
            for entry in snap.files.values():
                self.assertTrue((self.backups / "store" / entry.sha256[:2] / entry.sha256).is_file())

    def test_current_takes_a_slot_even_when_it_has_not_finished(self):
        # the real caller passes the snapshot it has just taken: no journal at all yet
        done = [self.finished_run() for _ in range(7)]
        current = snapshot.take(self.user, self.backups)
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

    def test_a_pruned_snapshot_is_gone_whole(self):
        first = self.finished_run()
        for _ in range(5):
            self.finished_run()
        restore.prune(self.backups, keep=5)
        self.assertFalse(first.dir.exists())
        self.assertEqual(len(snapshot.all_snapshots(self.backups)), 5)


if __name__ == "__main__":
    unittest.main()
