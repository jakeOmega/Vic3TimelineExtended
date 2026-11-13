"""Tests for game_qa.snapshot: the content-addressed snapshot of the owner's saves, settings and logs.

No game and no Windows program is needed: every test builds a user-data folder in a temp dir.
"""

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from game_qa import snapshot


def make_user_data(root: Path) -> None:
    """Write a small user-data folder: the set, plus `save games/mine.v3`, which is not in it."""
    (root / "save games").mkdir(parents=True)
    (root / "logs").mkdir()
    files = {
        "save games/autosave.v3": b"autosave zero",
        "save games/autosave_1.v3": b"autosave one",
        "save games/mine.v3": b"the owner's own save",
        "continue_game.json": b'{"save": "autosave.v3"}',
        "console_history.txt": b"set_variable x\n",
        "pdx_settings.json": b'{"language": "english"}',
        "content_load.json": b'{"enabled_mods": []}',
        "logs/debug.log": b"debug line\n",
        "logs/error.log": b"error line\n",
    }
    for name, data in files.items():
        (root / name).write_bytes(data)


def store_blobs(backups: Path) -> list[str]:
    return sorted(p.name for p in (backups / "store").rglob("*") if p.is_file())


class SnapshotTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.user = self.base / "user data"
        make_user_data(self.user)
        self.backups = self.base / "backups"  # does not exist yet; take() creates it


class TakeTests(SnapshotTestCase):
    def test_takes_the_set_and_nothing_else(self):
        snap = snapshot.take(self.user, self.backups)
        self.assertIn("save games/autosave_1.v3", snap.files)
        self.assertIn("logs/debug.log", snap.files)
        self.assertNotIn("save games/mine.v3", snap.files)
        self.assertIn("save games/mine.v3", snap.listing)

    def test_extra_saves_are_taken(self):
        snap = snapshot.take(self.user, self.backups, extra=["save games/mine.v3"])
        self.assertIn("save games/mine.v3", snap.files)

    def test_names_with_spaces_and_commas(self):
        name = "save games/TEST_FAIL_te_qa_fixture_2 January, 1836.v3"
        (self.user / name).write_bytes(b"x" * 10)
        snap = snapshot.take(self.user, self.backups, extra=[name])
        self.assertEqual(snap.files[name].size, 10)

    def test_unchanged_file_is_not_copied_again(self):
        first = snapshot.take(self.user, self.backups)
        stored = sorted(p.name for p in (self.backups / "store").rglob("*") if p.is_file())
        second = snapshot.take(self.user, self.backups)
        self.assertEqual(stored, sorted(p.name for p in (self.backups / "store").rglob("*") if p.is_file()))
        self.assertEqual(first.files, second.files)

    def test_manifest_records_the_content_hash(self):
        # size and time only decide whether take() may skip a copy; Task 3 decides overwrites by this hash
        snap = snapshot.take(self.user, self.backups)
        entry = snap.files["continue_game.json"]
        self.assertEqual(entry.sha256, hashlib.sha256((self.user / "continue_game.json").read_bytes()).hexdigest())

    def test_load_round_trips(self):
        snap = snapshot.take(self.user, self.backups)
        self.assertEqual(snapshot.load(snap.dir).files, snap.files)

    def test_journal_appends_in_order(self):
        snap = snapshot.take(self.user, self.backups)
        snapshot.record(snap, "started", pid=7, created="2026-11-10T12:00:00Z")
        snapshot.record(snap, "heartbeat")
        self.assertEqual([e["event"] for e in snapshot.journal(snap)], ["started", "heartbeat"])
        self.assertEqual(snapshot.journal(snap)[0]["pid"], 7)

    def test_missing_backup_parent_refuses(self):
        with self.assertRaises(snapshot.BackupRootError):
            snapshot.take(self.user, Path("/nonexistent/drive/backups"))

    def test_too_little_free_space_refuses(self):
        with mock.patch("shutil.disk_usage", return_value=(10**12, 10**12, 5)):
            with self.assertRaises(snapshot.BackupRootError):
                snapshot.take(self.user, self.backups)

    # --- beyond the brief ---------------------------------------------------------------

    def test_load_matches_take_in_files_and_listing(self):
        snap = snapshot.take(self.user, self.backups, extra=["save games/mine.v3"])
        loaded = snapshot.load(snap.dir)
        self.assertEqual(loaded.files, snap.files)
        self.assertEqual(loaded.listing, snap.listing)
        self.assertIsInstance(loaded.listing, frozenset)
        self.assertEqual(loaded.id, snap.id)
        self.assertEqual(loaded.dir, snap.dir)

    def test_set_is_files_only_and_not_recursive(self):
        (self.user / "logs" / "data_types").mkdir()
        (self.user / "logs" / "data_types" / "triggers.txt").write_text("deep")
        (self.user / "save games" / "sub").mkdir()
        (self.user / "save games" / "sub" / "autosave_9.v3").write_bytes(b"deep save")
        snap = snapshot.take(self.user, self.backups)
        self.assertFalse([name for name in snap.files if "data_types" in name or "/sub/" in name])
        self.assertFalse([name for name in snap.listing if "data_types" in name or "/sub/" in name])
        self.assertNotIn("logs/data_types", snap.listing)

    def test_listing_is_every_file_in_the_three_folders(self):
        (self.user / "notes.txt").write_text("owner's note")
        snap = snapshot.take(self.user, self.backups)
        self.assertEqual(
            snap.listing,
            frozenset(
                {
                    "save games/autosave.v3",
                    "save games/autosave_1.v3",
                    "save games/mine.v3",
                    "continue_game.json",
                    "console_history.txt",
                    "pdx_settings.json",
                    "content_load.json",
                    "notes.txt",
                    "logs/debug.log",
                    "logs/error.log",
                }
            ),
        )

    def test_a_symlink_is_listed_but_not_copied(self):
        # a name missing from the listing would read as "created by the run" at restore time
        (self.user / "logs" / "latest.log").symlink_to("debug.log")
        snap = snapshot.take(self.user, self.backups)
        self.assertIn("logs/latest.log", snap.listing)
        self.assertNotIn("logs/latest.log", snap.files)

    def test_the_listing_covers_every_folder_the_set_reads_from(self):
        for pattern in snapshot.SNAPSHOT_SET:
            self.assertIn(pattern.rpartition("/")[0], snapshot.LISTED_FOLDERS, pattern)

    def test_a_set_file_that_is_absent_is_not_in_files(self):
        (self.user / "console_history.txt").unlink()
        snap = snapshot.take(self.user, self.backups)
        self.assertNotIn("console_history.txt", snap.files)
        self.assertNotIn("console_history.txt", snap.listing)

    def test_entry_records_size_and_mtime(self):
        path = self.user / "pdx_settings.json"
        os.utime(path, ns=(1_700_000_000 * 10**9, 1_700_000_000 * 10**9))  # whole seconds: any filesystem
        entry = snapshot.take(self.user, self.backups).files["pdx_settings.json"]
        self.assertEqual(entry.size, path.stat().st_size)
        self.assertEqual(entry.mtime_ns, path.stat().st_mtime_ns)
        self.assertEqual(entry.mtime_ns, 1_700_000_000 * 10**9)

    def test_store_layout_is_the_content_hash(self):
        snap = snapshot.take(self.user, self.backups)
        entry = snap.files["logs/debug.log"]
        blob = self.backups / "store" / entry.sha256[:2] / entry.sha256
        self.assertEqual(blob.read_bytes(), b"debug line\n")

    def test_no_temp_files_stay_in_the_store(self):
        snapshot.take(self.user, self.backups)
        for p in (self.backups / "store").rglob("*"):
            if p.is_file():
                self.assertEqual(p.name, hashlib.sha256(p.read_bytes()).hexdigest())

    def test_identical_content_is_stored_once(self):
        (self.user / "logs" / "twin.log").write_bytes(b"debug line\n")
        snap = snapshot.take(self.user, self.backups)
        self.assertEqual(snap.files["logs/twin.log"].sha256, snap.files["logs/debug.log"].sha256)
        self.assertEqual(len(store_blobs(self.backups)), len(set(store_blobs(self.backups))))
        self.assertEqual(len(store_blobs(self.backups)), len({e.sha256 for e in snap.files.values()}))

    def test_changed_file_gets_a_new_blob_and_the_old_one_stays(self):
        first = snapshot.take(self.user, self.backups)
        (self.user / "pdx_settings.json").write_bytes(b'{"language": "german", "extra": 1}')
        second = snapshot.take(self.user, self.backups)
        old, new = first.files["pdx_settings.json"], second.files["pdx_settings.json"]
        self.assertNotEqual(old.sha256, new.sha256)
        self.assertEqual(new.sha256, hashlib.sha256((self.user / "pdx_settings.json").read_bytes()).hexdigest())
        self.assertIn(old.sha256, store_blobs(self.backups))
        self.assertIn(new.sha256, store_blobs(self.backups))
        self.assertEqual(snapshot.load(first.dir).files["pdx_settings.json"], old)

    def test_matching_size_and_mtime_reuse_the_previous_hash(self):
        # the documented trade: size and mtime_ns decide whether take() may skip reading a file
        path = self.user / "content_load.json"
        stamp = path.stat().st_mtime_ns
        first = snapshot.take(self.user, self.backups)
        path.write_bytes(b'{"enabled_mods": {}}')  # same length as before, different bytes
        self.assertEqual(path.stat().st_size, first.files["content_load.json"].size)
        os.utime(path, ns=(stamp, stamp))
        second = snapshot.take(self.user, self.backups)
        self.assertEqual(second.files["content_load.json"], first.files["content_load.json"])

    def test_a_reused_hash_whose_blob_is_gone_is_copied_again(self):
        first = snapshot.take(self.user, self.backups)
        sha = first.files["continue_game.json"].sha256
        (self.backups / "store" / sha[:2] / sha).unlink()
        second = snapshot.take(self.user, self.backups)
        self.assertEqual((self.backups / "store" / sha[:2] / sha).read_bytes(), b'{"save": "autosave.v3"}')
        self.assertEqual(second.files["continue_game.json"], first.files["continue_game.json"])

    def test_a_same_size_blob_that_is_corrupt_is_replaced_by_the_fresh_copy(self):
        path = self.user / "continue_game.json"
        first = snapshot.take(self.user, self.backups)
        sha = first.files["continue_game.json"].sha256
        blob = self.backups / "store" / sha[:2] / sha
        blob.write_bytes(b"x" * first.files["continue_game.json"].size)  # same size, wrong bytes
        stamp = path.stat().st_mtime_ns + 5 * 10**9
        os.utime(path, ns=(stamp, stamp))  # a new mtime, so the file is read again rather than reused
        snapshot.take(self.user, self.backups)
        self.assertEqual(blob.read_bytes(), b'{"save": "autosave.v3"}')

    def test_a_reused_hash_whose_blob_is_the_wrong_size_is_copied_again(self):
        first = snapshot.take(self.user, self.backups)
        sha = first.files["continue_game.json"].sha256
        (self.backups / "store" / sha[:2] / sha).write_bytes(b"torn")
        snapshot.take(self.user, self.backups)
        self.assertEqual((self.backups / "store" / sha[:2] / sha).read_bytes(), b'{"save": "autosave.v3"}')

    def test_file_with_a_different_size_is_rehashed_even_if_mtime_matches(self):
        path = self.user / "content_load.json"
        stamp = path.stat().st_mtime_ns
        first = snapshot.take(self.user, self.backups)
        path.write_bytes(b'{"enabled_mods": ["a", "b"]}')
        os.utime(path, ns=(stamp, stamp))
        second = snapshot.take(self.user, self.backups)
        self.assertNotEqual(first.files["content_load.json"].sha256, second.files["content_load.json"].sha256)

    def test_missing_user_data_raises_instead_of_taking_an_empty_snapshot(self):
        with self.assertRaises(FileNotFoundError):
            snapshot.take(self.base / "no such folder", self.backups)
        self.assertFalse(self.backups.exists())

    def test_backup_root_that_is_a_file_refuses(self):
        self.backups.write_text("not a folder")
        with self.assertRaises(snapshot.BackupRootError):
            snapshot.take(self.user, self.backups)

    def test_backup_root_inside_user_data_refuses(self):
        with self.assertRaises(snapshot.BackupRootError):
            snapshot.take(self.user, self.user / "logs" / "backups")
        self.assertFalse((self.user / "logs" / "backups").exists())

    def test_space_check_counts_only_what_must_be_copied(self):
        # mine.v3 is not in the set, so its bytes are not counted
        total_size = sum(p.stat().st_size for p in self.user.rglob("*") if p.is_file() and p.name != "mine.v3")
        margin = snapshot.FREE_SPACE_MARGIN
        # room for the margin but not for the bytes: refuse before creating the root
        with mock.patch("shutil.disk_usage", return_value=(10**12, 10**12, margin + total_size - 1)):
            with self.assertRaises(snapshot.BackupRootError):
                snapshot.take(self.user, self.backups)
        self.assertFalse(self.backups.exists())
        # room for both: succeeds
        with mock.patch("shutil.disk_usage", return_value=(10**12, 10**12, margin + total_size)):
            snapshot.take(self.user, self.backups)
        # nothing changed, so a second take needs only the margin
        with mock.patch("shutil.disk_usage", return_value=(10**12, 10**12, margin)):
            snapshot.take(self.user, self.backups)

    def test_space_is_checked_against_the_parent_while_the_root_is_missing(self):
        seen = []

        def usage(path):
            seen.append(Path(path))
            return (10**12, 10**12, 10**12)

        with mock.patch("shutil.disk_usage", usage):
            snapshot.take(self.user, self.backups)
        self.assertEqual(seen[0], self.backups.parent)


class ExtraPathTests(SnapshotTestCase):
    def test_extra_that_is_missing_raises_and_writes_nothing(self):
        with self.assertRaises(FileNotFoundError):
            snapshot.take(self.user, self.backups, extra=["save games/not there.v3"])
        self.assertFalse(self.backups.exists())

    def test_extra_must_stay_inside_user_data(self):
        outside = self.base / "secret.txt"
        outside.write_text("outside")
        for bad in ("../secret.txt", "save games/../../secret.txt", str(outside)):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    snapshot.take(self.user, self.backups, extra=[bad])
        self.assertFalse(self.backups.exists())

    def test_extra_that_is_a_folder_raises(self):
        with self.assertRaises(FileNotFoundError):
            snapshot.take(self.user, self.backups, extra=["logs"])

    def test_extra_overlapping_the_set_is_taken_once(self):
        snap = snapshot.take(self.user, self.backups, extra=["save games/autosave.v3", "./save games/autosave.v3"])
        self.assertEqual(list(snap.files).count("save games/autosave.v3"), 1)


class IdAndOrderTests(SnapshotTestCase):
    NOW = datetime(2026, 11, 10, 20, 40, 35, tzinfo=timezone.utc)

    def test_id_is_the_utc_second(self):
        snap = snapshot.take(self.user, self.backups, now=self.NOW)
        self.assertEqual(snap.id, "20261110T204035Z")
        self.assertEqual(snap.dir, self.backups / "snapshots" / "20261110T204035Z")

    def test_naive_time_is_utc_and_aware_time_is_converted(self):
        naive = snapshot.take(self.user, self.backups, now=datetime(2026, 11, 10, 20, 40, 35))
        self.assertEqual(naive.id, "20261110T204035Z")
        plus_two = timezone(timedelta(hours=2))
        aware = snapshot.take(self.user, self.backups, now=datetime(2026, 11, 10, 22, 41, 0, tzinfo=plus_two))
        self.assertEqual(aware.id, "20261110T204100Z")

    def test_same_second_gets_a_numbered_suffix(self):
        ids = [snapshot.take(self.user, self.backups, now=self.NOW).id for _ in range(3)]
        self.assertEqual(ids, ["20261110T204035Z", "20261110T204035Z-2", "20261110T204035Z-3"])

    def test_all_snapshots_is_oldest_first_with_numeric_suffix_order(self):
        later = self.NOW + timedelta(minutes=5)
        taken = [snapshot.take(self.user, self.backups, now=self.NOW).id for _ in range(11)]
        taken.append(snapshot.take(self.user, self.backups, now=later).id)
        listed = [s.id for s in snapshot.all_snapshots(self.backups)]
        self.assertEqual(listed, taken)
        self.assertEqual(listed[9], "20261110T204035Z-10")
        self.assertEqual(listed[-1], "20261110T204535Z")

    # --- ids from the backup drive's clock, never out of order ---------------------------------

    def take_at(self, *times):
        """Take one snapshot per time, with the backup drive's clock reading those times in turn."""
        with mock.patch.object(snapshot, "_drive_clock", side_effect=list(times)) as clock:
            snaps = [snapshot.take(self.user, self.backups) for _ in times]
        self.assertEqual([call.args for call in clock.call_args_list], [(self.backups / "snapshots",)] * len(times))
        return snaps

    def test_without_a_time_the_id_is_the_backup_drives_clock(self):
        # the machine's own clock drifts and is stepped; the drive's is the one file times come from
        (snap,) = self.take_at(self.NOW)
        self.assertEqual(snap.id, "20261110T204035Z")
        manifest = json.loads((snap.dir / "manifest.json").read_text())
        self.assertEqual(manifest["created"], "2026-11-10T20:40:35Z")

    def test_the_real_drive_clock_is_a_marker_in_the_snapshots_folder(self):
        snap = snapshot.take(self.user, self.backups)
        marker = self.backups / "snapshots" / snapshot.CLOCK_MARKER
        stamped = datetime.fromtimestamp(marker.stat().st_mtime, timezone.utc)
        self.assertEqual(snap.id, stamped.strftime("%Y%m%dT%H%M%SZ"))
        self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], [snap.id])  # the marker is no snapshot

    def test_a_given_time_does_not_ask_the_drive_clock(self):
        with mock.patch.object(snapshot, "_drive_clock", side_effect=AssertionError("asked")):
            snap = snapshot.take(self.user, self.backups, now=self.NOW)
        self.assertEqual(snap.id, "20261110T204035Z")
        self.assertFalse((self.backups / "snapshots" / snapshot.CLOCK_MARKER).exists())

    def test_a_clock_stepping_back_never_puts_a_snapshot_before_an_earlier_one(self):
        times = [self.NOW, self.NOW - timedelta(seconds=5), self.NOW - timedelta(seconds=10), self.NOW + timedelta(seconds=1)]
        snaps = self.take_at(*times)
        self.assertEqual(
            [s.id for s in snaps], ["20261110T204035Z", "20261110T204035Z-2", "20261110T204035Z-3", "20261110T204036Z"]
        )
        self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], [s.id for s in snaps])

    def test_a_clock_that_stays_put_gives_the_next_suffix(self):
        snaps = self.take_at(self.NOW, self.NOW, self.NOW)
        self.assertEqual([s.id for s in snaps], ["20261110T204035Z", "20261110T204035Z-2", "20261110T204035Z-3"])

    def test_the_suffix_goes_on_after_the_newest_even_when_an_older_one_was_removed(self):
        for step_back in (5, 0):  # the clock stepped back, and the clock stood still
            with self.subTest(step_back=step_back):
                shutil.rmtree(self.backups, ignore_errors=True)
                first, second, third = self.take_at(self.NOW, self.NOW, self.NOW)
                shutil.rmtree(second.dir)  # as prune does
                (fourth,) = self.take_at(self.NOW - timedelta(seconds=step_back))
                self.assertEqual(fourth.id, "20261110T204035Z-4")  # not -2, which would sort before the third
                self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], [first.id, third.id, fourth.id])

    def test_a_given_time_in_the_past_also_sorts_after_what_is_there(self):
        first = snapshot.take(self.user, self.backups, now=self.NOW)
        second = snapshot.take(self.user, self.backups, now=self.NOW - timedelta(hours=1))
        self.assertEqual(second.id, "20261110T204035Z-2")
        self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], [first.id, second.id])

    def test_a_folder_that_did_not_finish_does_not_decide_the_order(self):
        # only loadable snapshots count: this one is skipped by all_snapshots whatever its name
        half = self.backups / "snapshots" / "20270101T000000Z"
        half.mkdir(parents=True)
        (snap,) = self.take_at(self.NOW)
        self.assertEqual(snap.id, "20261110T204035Z")

    def test_all_snapshots_without_a_backup_root_is_empty(self):
        self.assertEqual(snapshot.all_snapshots(self.base / "nothing here"), [])
        self.assertEqual(snapshot.all_snapshots(self.backups), [])

    def test_a_snapshot_without_a_manifest_does_not_load_and_is_skipped(self):
        good = snapshot.take(self.user, self.backups, now=self.NOW)
        half = self.backups / "snapshots" / "20261110T210000Z"
        half.mkdir()
        (half / "manifest.json.tmp").write_text('{"version": 1, "files": {')
        with self.assertRaises(FileNotFoundError):
            snapshot.load(half)
        self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], [good.id])

    def test_a_corrupt_manifest_is_skipped_and_load_raises_value_error(self):
        good = snapshot.take(self.user, self.backups, now=self.NOW)
        bad = self.backups / "snapshots" / "20261110T210000Z"
        bad.mkdir()
        (bad / "manifest.json").write_text('{"version": 1, "files": {')
        with self.assertRaises(ValueError):
            snapshot.load(bad)
        self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], [good.id])

    def test_a_manifest_missing_a_key_raises_value_error(self):
        bad = self.backups / "snapshots" / "20261110T210000Z"
        bad.mkdir(parents=True)
        (bad / "manifest.json").write_text(json.dumps({"version": 1, "files": {}}))
        with self.assertRaises(ValueError):
            snapshot.load(bad)

    def test_stray_folders_in_snapshots_are_ignored(self):
        good = snapshot.take(self.user, self.backups, now=self.NOW)
        (self.backups / "snapshots" / "scratch").mkdir()
        (self.backups / "snapshots" / "notes.txt").write_text("hi")
        self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], [good.id])

    def test_take_reuses_hashes_from_the_newest_loadable_snapshot(self):
        path = self.user / "content_load.json"
        stamp = path.stat().st_mtime_ns
        first = snapshot.take(self.user, self.backups, now=self.NOW)
        # a newer directory that never finished must not hide the real previous snapshot
        (self.backups / "snapshots" / "20261110T230000Z").mkdir()
        path.write_bytes(b'{"enabled_mods": {}}')  # same size and mtime, so the hash is reused
        os.utime(path, ns=(stamp, stamp))
        second = snapshot.take(self.user, self.backups, now=self.NOW + timedelta(hours=1))
        self.assertEqual(second.files, first.files)

    def test_manifest_is_written_by_rename_and_a_failed_take_leaves_no_snapshot(self):
        snap = snapshot.take(self.user, self.backups)
        self.assertEqual(sorted(p.name for p in snap.dir.iterdir()), ["manifest.json"])
        with mock.patch("os.replace", side_effect=OSError("disk fell off")):
            with self.assertRaises(OSError):
                snapshot.take(self.user, self.backups, now=self.NOW)
        folders = [p.name for p in (self.backups / "snapshots").iterdir() if p.name != snapshot.CLOCK_MARKER]
        self.assertEqual(sorted(folders), [snap.id])
        self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], [snap.id])

    def test_a_failure_after_the_manifest_is_in_place_keeps_the_snapshot(self):
        # the run that made a snapshot never deletes it: once manifest.json exists, a late error
        # (an interrupt, a mount that reports one after the rename) must leave it on disk and loadable
        real_write = snapshot._write_manifest

        def write_then_fail(*args, **kwargs):
            real_write(*args, **kwargs)
            raise KeyboardInterrupt

        with mock.patch.object(snapshot, "_write_manifest", write_then_fail):
            with self.assertRaises(KeyboardInterrupt):
                snapshot.take(self.user, self.backups, now=self.NOW)
        kept = self.backups / "snapshots" / "20261110T204035Z"
        self.assertTrue((kept / "manifest.json").is_file())
        self.assertEqual([s.id for s in snapshot.all_snapshots(self.backups)], ["20261110T204035Z"])

    def test_a_failure_before_the_manifest_leaves_no_temp_manifest_behind(self):
        def write_tmp_then_fail(folder, *args, **kwargs):
            (folder / "manifest.json.tmp").write_text("{")
            raise OSError("disk fell off")

        with mock.patch.object(snapshot, "_write_manifest", write_tmp_then_fail):
            with self.assertRaises(OSError):
                snapshot.take(self.user, self.backups, now=self.NOW)
        self.assertEqual(list((self.backups / "snapshots").iterdir()), [])


class JournalTests(SnapshotTestCase):
    NOW = datetime(2026, 11, 10, 20, 40, 35, tzinfo=timezone.utc)

    def test_a_new_snapshot_has_an_empty_journal(self):
        snap = snapshot.take(self.user, self.backups)
        self.assertEqual(snapshot.journal(snap), [])

    def test_records_carry_a_utc_timestamp_under_at(self):
        snap = snapshot.take(self.user, self.backups)
        snapshot.record(snap, "started", now=self.NOW, pid=7)
        (entry,) = snapshot.journal(snap)
        self.assertEqual(entry, {"event": "started", "at": "2026-11-10T20:40:35Z", "pid": 7})

    def test_record_defaults_to_the_current_time(self):
        # "current" by the drive's clock, which the marker file carries. The machine's clock is a second clock:
        # WSL's steps by seconds, and a step between two lines failed a tight bound against it (#1604), so it
        # only gets a loose one, enough to tell a stamp made now from a stale or fixed one.
        snap = snapshot.take(self.user, self.backups)
        snapshot.record(snap, "heartbeat")
        at = datetime.strptime(snapshot.journal(snap)[0]["at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        stamped = datetime.fromtimestamp((snap.dir / snapshot.CLOCK_MARKER).stat().st_mtime, timezone.utc)
        self.assertEqual(at, stamped.replace(microsecond=0))
        self.assertLess(abs(datetime.now(timezone.utc) - at), timedelta(minutes=5))

    def test_the_default_time_is_the_backup_drives_own_clock(self):
        # WSL's clock drifts after the host sleeps; file times on the drive do not, and the hold rule compares them
        snap = snapshot.take(self.user, self.backups)
        drive_time = datetime(2031, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        with mock.patch.object(snapshot, "_drive_clock", return_value=drive_time) as clock:
            snapshot.record(snap, "heartbeat")
        clock.assert_called_once_with(snap.dir)
        self.assertEqual(snapshot.journal(snap)[0]["at"], "2031-01-02T03:04:05Z")

    def test_the_drive_clock_is_the_mtime_of_a_marker_file_in_the_snapshot_folder(self):
        snap = snapshot.take(self.user, self.backups)
        snapshot.record(snap, "heartbeat")
        marker = snap.dir / snapshot.CLOCK_MARKER
        stamped = datetime.fromtimestamp(marker.stat().st_mtime, timezone.utc)
        self.assertEqual(snapshot.journal(snap)[0]["at"], stamped.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.assertEqual(snapshot._drive_clock(snap.dir), datetime.fromtimestamp(marker.stat().st_mtime, timezone.utc))

    def test_the_marker_is_stamped_afresh_each_time(self):
        snap = snapshot.take(self.user, self.backups)
        marker = snap.dir / snapshot.CLOCK_MARKER
        snapshot.record(snap, "heartbeat")
        os.utime(marker, (1_000_000_000, 1_000_000_000))  # an old stamp that must not be reused
        snapshot.record(snap, "heartbeat")
        self.assertGreater(marker.stat().st_mtime, 1_000_000_000)
        self.assertGreater(snapshot.journal(snap)[1]["at"], "2001-09-09T01:46:40Z")

    def test_a_given_time_does_not_touch_the_drive_clock(self):
        snap = snapshot.take(self.user, self.backups)
        with mock.patch.object(snapshot, "_drive_clock", side_effect=AssertionError("asked")):
            snapshot.record(snap, "started", now=self.NOW)
        self.assertFalse((snap.dir / snapshot.CLOCK_MARKER).exists())

    def test_fields_may_not_overwrite_the_timestamp(self):
        snap = snapshot.take(self.user, self.backups)
        with self.assertRaises(ValueError):
            snapshot.record(snap, "held", at="yesterday")
        self.assertEqual(snapshot.journal(snap), [])

    def test_journal_is_read_back_from_disk_not_from_the_object(self):
        snap = snapshot.take(self.user, self.backups)
        snapshot.record(snap, "started", pid=7)
        again = snapshot.load(snap.dir)
        snapshot.record(again, "restored")
        self.assertEqual([e["event"] for e in snapshot.journal(snap)], ["started", "restored"])

    def test_non_ascii_and_odd_values_round_trip(self):
        snap = snapshot.take(self.user, self.backups)
        reason = 'owner played "Österreich", then\nquit'
        snapshot.record(snap, "held", reason=reason)
        self.assertEqual(snapshot.journal(snap)[0]["reason"], reason)

    def test_a_torn_last_line_is_skipped_and_the_next_record_survives(self):
        snap = snapshot.take(self.user, self.backups)
        snapshot.record(snap, "started", pid=7)
        with open(snap.dir / "journal.jsonl", "ab") as handle:
            handle.write(b'{"event": "heartb')  # the machine died mid-write: no newline
        self.assertEqual([e["event"] for e in snapshot.journal(snap)], ["started"])
        snapshot.record(snap, "restored")
        self.assertEqual([e["event"] for e in snapshot.journal(snap)], ["started", "restored"])

    def test_names_with_odd_characters_survive_the_manifest(self):
        name = "save games/Königreich_Württemberg, 1836 — “final”.v3"
        (self.user / name).write_bytes(b"x" * 3)
        snap = snapshot.take(self.user, self.backups, extra=[name])
        self.assertEqual(snapshot.load(snap.dir).files[name].size, 3)
        self.assertIn(name, snapshot.load(snap.dir).listing)


class SaveStatsTests(SnapshotTestCase):
    """#1725: the size and time of everything listed in `save games/`, so that `restore` can tell a changed save of
    the owner's (which is never copied) from one left alone."""

    def test_every_save_games_entry_gets_the_size_and_time_its_lstat_gave(self):
        (self.user / "save games/linked.v3").symlink_to("mine.v3")
        snap = snapshot.take(self.user, self.backups)
        expected = {}
        for name in ("autosave.v3", "autosave_1.v3", "mine.v3", "linked.v3"):
            st = os.lstat(self.user / "save games" / name)
            expected["save games/" + name] = (st.st_size, st.st_mtime_ns)
        self.assertEqual(snap.save_stats, expected)                 # as lstat gives it, never rounded
        self.assertEqual(snap.save_stats["save games/linked.v3"][0], len("mine.v3"))             # the link's own

    def test_the_manifest_keeps_them_and_load_reads_them_back(self):
        snap = snapshot.take(self.user, self.backups)
        manifest = json.loads((snap.dir / snapshot.MANIFEST_NAME).read_text("utf-8"))
        self.assertEqual(manifest["version"], 1)                    # older checkouts still load it
        self.assertEqual(manifest["save_stats"]["save games/mine.v3"],
                         {"size": len(b"the owner's own save"),
                          "mtime_ns": os.lstat(self.user / "save games/mine.v3").st_mtime_ns})
        self.assertEqual(snapshot.load(snap.dir).save_stats, snap.save_stats)

    def test_an_empty_save_folder_records_none_and_a_missing_one_too(self):
        for path in (self.user / "save games").iterdir():
            path.unlink()
        self.assertEqual(snapshot.take(self.user, self.backups).save_stats, {})
        (self.user / "save games").rmdir()
        self.assertEqual(snapshot.take(self.user, self.backups).save_stats, {})

    def rewrite(self, snap, change):
        path = snap.dir / snapshot.MANIFEST_NAME
        manifest = json.loads(path.read_text("utf-8"))
        change(manifest)
        path.write_text(json.dumps(manifest), "utf-8")
        return snapshot.load(snap.dir)

    def test_a_manifest_from_before_has_none_and_loads_whole(self):
        snap = snapshot.take(self.user, self.backups)
        loaded = self.rewrite(snap, lambda manifest: manifest.pop("save_stats"))
        self.assertIsNone(loaded.save_stats)
        self.assertEqual((loaded.files, loaded.listing), (snap.files, snap.listing))

    def test_a_record_that_does_not_read_is_none_and_the_rest_still_loads(self):
        def name(manifest, value):
            manifest["save_stats"]["save games/mine.v3"] = value

        def drop(manifest):
            del manifest["save_stats"]["save games/mine.v3"]

        def extra(manifest):
            manifest["save_stats"]["save games/unlisted.v3"] = {"size": 1, "mtime_ns": 1}

        def outside(manifest):
            manifest["save_stats"]["continue_game.json"] = {"size": 1, "mtime_ns": 1}

        cases = {
            "a list": lambda m: m.update(save_stats=[]),
            "null": lambda m: m.update(save_stats=None),
            "a name missing": drop,
            "a name not listed": extra,
            "a name outside save games/": outside,
            "a bool size": lambda m: name(m, {"size": True, "mtime_ns": 1}),
            "a text time": lambda m: name(m, {"size": 1, "mtime_ns": "1"}),
            "a float time": lambda m: name(m, {"size": 1, "mtime_ns": 1.5}),
            "a pair": lambda m: name(m, [1, 1]),
            "no time": lambda m: name(m, {"size": 1}),
        }
        for label, change in cases.items():
            with self.subTest(label):
                snap = snapshot.take(self.user, self.backups)
                loaded = self.rewrite(snap, change)
                self.assertIsNone(loaded.save_stats)
                self.assertEqual((loaded.files, loaded.listing), (snap.files, snap.listing))
                self.assertIn(snap.id, [s.id for s in snapshot.all_snapshots(self.backups)])

    def test_a_snapshot_built_without_them_has_none(self):
        # as selfchecks.py builds one for a run's folder
        snap = snapshot.Snapshot(id="x", dir=self.base, files={}, listing=frozenset())
        self.assertIsNone(snap.save_stats)


class UnlistedSaveTests(SnapshotTestCase):
    """#1725: a save for the run is named as `save games/` lists it, in any letter case. The owner's drive also
    answers to short 8.3 names it does not list (`FRENCH~1.V3`); here a hard link plays that name, and the scan is
    made to leave it out, as the drive's listing does."""

    LONG = "french republic_1867_08_16.v3"
    SHORT = "FRENCH~1.V3"

    def setUp(self):
        super().setUp()
        (self.user / "save games" / self.LONG).write_bytes(b"a long-named save")
        os.link(self.user / "save games" / self.LONG, self.user / "save games" / self.SHORT)
        real = snapshot._scan_folder

        def scan(user_data, folder):
            return {rel: st for rel, st in real(user_data, folder).items() if "~" not in rel}
        patcher = mock.patch.object(snapshot, "_scan_folder", scan)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_short_name_is_refused_naming_the_listed_one_and_nothing_is_written(self):
        with self.assertRaises(snapshot.SaveNotListed) as caught:
            snapshot.take(self.user, self.backups, extra=["save games/" + self.SHORT])
        self.assertIsInstance(caught.exception, ValueError)
        self.assertIn(repr(self.LONG), str(caught.exception))
        self.assertFalse(self.backups.exists())

    def test_the_listed_name_in_any_letter_case_is_taken(self):
        for name in (self.LONG, self.LONG.upper(), "save games/mine.v3"):
            with self.subTest(name=name):
                rel = name if "/" in name else "save games/" + name
                self.assertIsNone(snapshot.unlisted_save(self.user, rel))
        snapshot.take(self.user, self.backups, extra=["save games/" + self.LONG])

    def test_a_name_that_is_no_listed_file_says_so_without_naming_one(self):
        (self.user / "save games/sub").mkdir()
        (self.user / "save games/sub/x.v3").write_bytes(b"x")
        os.link(self.user / "save games/mine.v3", self.user / "save games/MINE~1.V3")
        problem = snapshot.unlisted_save(self.user, "save games/MINE~1.V3")
        self.assertIn("same file as 'mine.v3'", problem)
        os.unlink(self.user / "save games/MINE~1.V3")
        (self.user / "save games/LOOSE~1.V3").write_bytes(b"listed by nothing, linked to nothing")
        problem = snapshot.unlisted_save(self.user, "save games/LOOSE~1.V3")
        self.assertIn("is not a name save games/ lists", problem)
        self.assertNotIn("same file", problem)
        self.assertIsNone(snapshot.unlisted_save(self.user, "save games/sub/x.v3"))     # not directly in it
        self.assertIsNone(snapshot.unlisted_save(self.user, "continue_game.json"))


if __name__ == "__main__":
    unittest.main()
