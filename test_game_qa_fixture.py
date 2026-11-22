"""Tests for game_qa.fixture: a fresh save made by an unattended run of the game, and kept by a key.

No game and no Windows program is needed. `FakeCli` stands in for `python3 -m game_qa`: it records every call
and plays the side effects on the user-data folder that matter here, and its `spawn_watch` stands in for the
`watch` subprocess. The game's run writes `save games/TEST_FAIL_te_qa_fixture_2 January, 1836.v3` while `watch`
follows it; `restore`, like the real one, removes the saves a run created (`TEST_FAIL_*` and `te_qa_*`, never
`te_qa_fixture_*`), so a test that passes with the rename and the restore in the wrong order cannot happen.
Every wait runs on the test's own clock.
"""

import fnmatch
import os
import tempfile
import unittest
from unittest import mock
import unittest.mock
from pathlib import Path

from game_qa import fixture
from game_qa.gate import ProcId
from game_qa.logtail import GAP_MARKER

KEY = "0123456789ab"
SNAPSHOT = "20261110T120000Z"
OVERLAY = r"C:\Users\someone\Documents\Paradox Interactive\Victoria 3\mod\te_qa_overlay"
PERMISSION = "the owner said go in this session"
GAME_SAVE = "TEST_FAIL_te_qa_fixture_2 January, 1836.v3"
GAME_SAVE_BYTES = b"a fresh game"
CREATED = "2026-11-10T12:00:05.0000000Z"
GAME = ProcId(4242, CREATED)
REFUSED = {"held": False, "refused": "gpu_busy", "detail": "the GPU is at 80% load"}
HELD = {"held": True, "reason": "other_game_ran", "id": SNAPSHOT}
UNCONFIRMED = {"held": False, "refused": "start_unconfirmed", "detail": "PowerShell's reply was lost"}


class FakeWatch:
    """The `watch` subprocess `spawn_watch` started: `poll()` is None while it follows the game, then its exit
    code. By default the game writes its save and quits by itself at once, and watch returns 0 (it recorded the
    exit); `code` 2 is a watch that stopped without recording one (it refused, as for a launch that recorded no
    `started`); `hangs` follows a game that never quits."""

    def __init__(self, cli: "FakeCli"):
        self.cli = cli
        self.code = cli.watch_code
        self.hangs = cli.watch_hangs
        self.polls = 0

    def poll(self):
        self.polls += 1
        if self.hangs:
            return None
        if self.code == 0 and self.polls == 1:
            self.cli.write_saves()
        return self.code


class FakeCli:
    """`python3 -m game_qa <argv>` as `fixture.make` calls it: returns (reply, exit code).

    `replies[verb]` is a list of (reply, exit code) pairs, played in order before the defaults.
    `saves` are the names the game writes while `watch` follows it; `save_at_launch` makes a refused-looking
    `launch` leave one behind as well, as a game that started but could not be confirmed would. `order` is
    every verb and `spawn_watch` in turn."""

    def __init__(self, user_data: Path, replies=None, saves=(GAME_SAVE,), save_at_launch=False):
        self.save_dir = user_data / "save games"
        self.replies = {verb: list(pairs) for verb, pairs in (replies or {}).items()}
        self.saves = tuple(saves)
        self.save_at_launch = save_at_launch
        self.calls: list[list[str]] = []
        self.order: list[str] = []
        self.saves_at_restore: list[list[str]] = []
        self.raise_on: str | None = None
        self.watch_code = 0
        self.watch_hangs = False
        self.spawn_error: Exception | None = None
        self.watches: list[FakeWatch] = []

    @property
    def verbs(self) -> list[str]:
        return [call[0] for call in self.calls]

    def spawn_watch(self, snapshot_id: str) -> FakeWatch:
        self.order.append("spawn_watch " + snapshot_id)
        if self.spawn_error is not None:
            raise self.spawn_error
        watch = FakeWatch(self)
        self.watches.append(watch)
        return watch

    def __call__(self, argv):
        argv = list(argv)
        self.calls.append(argv)
        verb = argv[0]
        self.order.append(verb)
        if verb == self.raise_on:
            raise RuntimeError(f"{verb} blew up")
        default = {
            "snapshot": ({"id": SNAPSHOT}, 0),
            "launch": ({"id": SNAPSHOT, "pid": GAME.pid, "created": GAME.created}, 0),
            "restore": ({"id": SNAPSHOT, "held": False}, 0),
        }[verb]
        played = self.replies.get(verb)
        reply, code = played.pop(0) if played else default
        if verb == "launch" and self.save_at_launch:
            self.write_saves()
        if verb == "restore":
            self.saves_at_restore.append(sorted(os.listdir(self.save_dir)))
            for name in os.listdir(self.save_dir):
                if fnmatch.fnmatch(name, "TEST_FAIL_*.v3") or (
                    fnmatch.fnmatch(name, "te_qa_*.v3") and not name.startswith("te_qa_fixture_")
                ):
                    (self.save_dir / name).unlink()
        return reply, code

    def write_saves(self):
        for name in self.saves:
            (self.save_dir / name).write_bytes(GAME_SAVE_BYTES)


class FixtureTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.user = self.base / "user data"
        self.save_dir = self.user / "save games"
        self.save_dir.mkdir(parents=True)
        self.owner_files = {
            "autosave.v3": b"autosave zero",
            "mine.v3": b"the owner's own save",
            "te_qa_fixture_aaaaaaaaaaaa.v3": b"an older fixture",
            "notes.txt": b"not a save",
        }
        for name, data in self.owner_files.items():
            (self.save_dir / name).write_bytes(data)
        self.target = self.save_dir / f"te_qa_fixture_{KEY}.v3"
        self.sleeps: list[float] = []
        self.now = 0.0
        self.journaled: dict[str, ProcId] = {}     # what `started` finds in a snapshot's journal

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def cli(self, **kwargs) -> FakeCli:
        self.fake = FakeCli(self.user, **kwargs)
        return self.fake

    def make(self, fake=None, **kwargs):
        return fixture.make(
            fake or self.fake, self.user, KEY, OVERLAY, PERMISSION, "mod_only", sleep=self.sleep,
            spawn_watch=self.fake.spawn_watch, clock=lambda: self.now, started=self.journaled.get, **kwargs
        )

    def assert_owner_files_untouched(self):
        for name, data in self.owner_files.items():
            self.assertEqual((self.save_dir / name).read_bytes(), data, name)

    def assert_fixture_error(self, step, **kwargs):
        with self.assertRaises(fixture.FixtureError) as caught:
            self.make(**kwargs)
        self.assertEqual(caught.exception.step, step)
        return caught.exception


class KeyTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.deploy = Path(tmp.name) / "Vic3TimelineExtended"
        for name in ("common/buildings/a.txt", "common/laws/b.txt", "events/c.txt", "map_data/d.txt", "gui/e.gui"):
            path = self.deploy / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name, encoding="utf-8")
        self.mods = [r"C:\mods\Vic3TimelineExtended", r"C:\mods\other"]

    def key(self, version="1.15.0", mods=None, playset="current", dlc=()):
        return fixture.key(version, self.mods if mods is None else mods, self.deploy, playset=playset,
                           disabled_dlc=dlc)

    def test_key_is_twelve_hex_digits_and_stable(self):
        key = self.key()
        self.assertRegex(key, r"^[0-9a-f]{12}$")
        self.assertEqual(self.key(), key)

    def test_key_changes_with_the_version_the_playset_and_a_script_file(self):
        base = self.key()
        keys = {
            "version": self.key(version="1.15.1"),
            "a mod added": self.key(mods=[*self.mods, r"C:\mods\third"]),
            "a mod removed": self.key(mods=self.mods[:1]),
            "mod order": self.key(mods=list(reversed(self.mods))),
            "a mod path": self.key(mods=[self.mods[0], r"C:\mods\Other"]),
            "the playset mode": self.key(playset="mod_only"),
            "a DLC switched off": self.key(dlc=[{"paradoxAppId": "dlc_voice_of_the_people"}]),   # X4
        }
        (self.deploy / "common/laws/b.txt").write_text("a longer file than before", encoding="utf-8")
        keys["a script file grew"] = self.key()
        for label, other in keys.items():
            with self.subTest(change=label):
                self.assertNotEqual(other, base)
        self.assertEqual(len(set(keys.values())), len(keys), "each change gives its own key")

    def test_the_dlc_set_counts_as_a_set(self):
        one, two = {"paradoxAppId": "a"}, {"paradoxAppId": "b"}
        self.assertEqual(self.key(dlc=[one, two]), self.key(dlc=[two, one]))
        self.assertNotEqual(self.key(dlc=[one]), self.key(dlc=[two]))
        self.assertEqual(self.key(dlc=[]), self.key())

    def test_key_changes_with_a_files_modification_time_alone(self):
        base = self.key()
        path = self.deploy / "events/c.txt"
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
        self.assertNotEqual(self.key(), base)

    def test_key_changes_with_a_new_or_removed_file_in_each_hashed_folder(self):
        base = self.key()
        for folder in ("common/buildings", "events", "map_data"):
            with self.subTest(folder=folder):
                extra = self.deploy / folder / "extra.txt"
                extra.write_text("", encoding="utf-8")
                self.assertNotEqual(self.key(), base)
                extra.unlink()
                self.assertEqual(self.key(), base)
        (self.deploy / "events/c.txt").unlink()
        self.assertNotEqual(self.key(), base)

    def test_key_ignores_folders_the_run_does_not_read_scripts_from(self):
        base = self.key()
        gui = self.deploy / "gui/e.gui"
        gui.write_text("changed and longer", encoding="utf-8")
        (self.deploy / "localization/english").mkdir(parents=True)
        (self.deploy / "localization/english/x_l_english.yml").write_text("x", encoding="utf-8")
        self.assertEqual(self.key(), base)

    def test_key_with_a_missing_folder_still_works(self):
        full = self.key()
        for name in ("map_data/d.txt", "events/c.txt"):
            (self.deploy / name).unlink()
        (self.deploy / "map_data").rmdir()
        (self.deploy / "events").rmdir()
        short = self.key()
        self.assertRegex(short, r"^[0-9a-f]{12}$")
        self.assertNotEqual(short, full)
        self.assertRegex(fixture.key("1.15.0", [], self.deploy / "nothing here", playset="mod_only"), r"^[0-9a-f]{12}$")

    def test_key_is_not_fooled_by_where_a_boundary_falls(self):
        self.assertNotEqual(self.key(mods=["ab", "c"]), self.key(mods=["a", "bc"]))
        self.assertNotEqual(self.key(mods=["a", "b"]), self.key(mods=["a\nmod\u0000b"]))

    def test_key_changes_with_the_rules_the_owner_last_applied(self):
        # An unattended new game is made under them, not under the defaults (game_qa.rules).
        plain = fixture.key("1.15.0", self.mods, self.deploy, playset="mod_only")
        self.assertEqual(fixture.key("1.15.0", self.mods, self.deploy, playset="mod_only", rules=[]), plain)
        light = fixture.key("1.15.0", self.mods, self.deploy, playset="mod_only", rules=["a", "tax_light"])
        off = fixture.key("1.15.0", self.mods, self.deploy, playset="mod_only", rules=["a", "tax_off"])
        self.assertEqual(len({plain, light, off}), 3)
        self.assertEqual(fixture.key("1.15.0", self.mods, self.deploy, playset="mod_only", rules=("a", "tax_light")),
                         light)

    def test_key_wants_a_list_of_mods_not_one_path_and_the_playset_by_name(self):
        with self.assertRaises(TypeError):
            fixture.key("1.15.0", r"C:\mods\one", self.deploy, playset="current")
        with self.assertRaises(TypeError):
            fixture.key("1.15.0", self.mods, self.deploy)          # the playset mode is not optional


class FindTest(FixtureTestCase):
    def test_find_returns_the_kept_save_or_none(self):
        self.assertIsNone(fixture.find(self.user, KEY))
        self.target.write_bytes(b"kept")
        self.assertEqual(fixture.find(self.user, KEY), self.target)
        self.assertIsNone(fixture.find(self.user / "no such folder", KEY))

    def test_find_ignores_a_folder_of_that_name(self):
        self.target.mkdir()
        self.assertIsNone(fixture.find(self.user, KEY))

    def test_a_key_that_is_not_a_plain_word_is_refused(self):
        for bad in ("", "../x", "a/b", "a b", "a.b", "a\\b", "x" * 65, "é"):
            with self.subTest(key=bad):
                with self.assertRaises(ValueError):
                    fixture.find(self.user, bad)
                fake = self.cli()
                with self.assertRaises(ValueError):
                    fixture.make(fake, self.user, bad, OVERLAY, PERMISSION, "mod_only", sleep=self.sleeps.append,
                                 spawn_watch=fake.spawn_watch)
                self.assertEqual(fake.calls, [], "no verb ran")


class MakeTest(FixtureTestCase):
    def test_make_renames_the_save_before_restore_and_returns_it(self):
        fake = self.cli()
        path = self.make()
        self.assertEqual(path, self.target)
        self.assertEqual(path.read_bytes(), GAME_SAVE_BYTES)
        self.assertEqual(
            fake.saves_at_restore,
            [sorted([*self.owner_files, self.target.name])],
            "restore saw the renamed save and no TEST_FAIL_ save",
        )
        self.assertFalse((self.save_dir / GAME_SAVE).exists())
        self.assert_owner_files_untouched()
        self.assertEqual(sorted(os.listdir(self.save_dir)), sorted([*self.owner_files, self.target.name]))
        self.assertEqual(self.sleeps, [])

    def test_make_calls_the_verbs_in_order_with_the_fixture_arguments(self):
        fake = self.cli()
        self.make()
        self.assertEqual(
            fake.calls,
            [
                ["snapshot"],
                [
                    "launch", SNAPSHOT, "--permission", PERMISSION, "--playset", "mod_only",
                    "--add-mod", OVERLAY, "--",
                    "-gdpr-compliant", "-debug_mode", "-handsoff", "-scripted_tests", "-run_until=1836.1.4",
                ],
                ["restore", SNAPSHOT],
            ],
        )
        # watch is started the moment launch returns, and followed to the game's exit before restore
        self.assertEqual(fake.order, ["snapshot", "launch", "spawn_watch " + SNAPSHOT, "restore"])
        self.assertEqual(
            fixture.FIXTURE_ARGS,
            ("-gdpr-compliant", "-debug_mode", "-handsoff", "-scripted_tests", "-run_until=1836.1.4"),
        )

    def test_the_fixtures_launch_uses_the_runs_playset(self):
        fake = self.cli()
        fixture.make(fake, self.user, KEY, OVERLAY, PERMISSION, "current", sleep=self.sleep,
                     spawn_watch=fake.spawn_watch, clock=lambda: self.now)
        launch = fake.calls[1]
        self.assertEqual(launch[launch.index("--playset") + 1], "current")

    def test_owner_confirmed_busy_is_passed_to_launch_before_the_game_arguments(self):
        fake = self.cli()
        self.make(owner_confirmed_busy=True)
        launch = fake.calls[1]
        self.assertEqual(launch.index("--owner-confirmed-busy"), launch.index("--add-mod") + 2)
        self.assertLess(launch.index("--owner-confirmed-busy"), launch.index("--"))
        self.assertEqual(launch[launch.index("--") + 1:], list(fixture.FIXTURE_ARGS))
        self.assertNotIn("--owner-confirmed-busy", launch[launch.index("--"):])

    def test_a_refused_snapshot_stops_before_anything_else(self):
        refusal = {"held": False, "refused": "game_running", "detail": "Victoria 3 is running"}
        fake = self.cli(replies={"snapshot": [(refusal, 2)]})
        error = self.assert_fixture_error("snapshot")
        self.assertEqual(error.reply, refusal)
        self.assertIsNone(error.snapshot)
        self.assertIn("game_running", str(error))
        self.assertEqual(fake.verbs, ["snapshot"])

    def test_a_launch_refused_before_its_claim_is_restored_at_once_and_not_watched(self):
        fake = self.cli(replies={"launch": [(REFUSED, 2)]})
        error = self.assert_fixture_error("launch")
        self.assertEqual(error.reply, REFUSED)
        self.assertEqual(error.snapshot, SNAPSHOT)
        self.assertIsNone(error.code)
        self.assertIn("gpu_busy", str(error))
        self.assertEqual(fake.order, ["snapshot", "launch", "restore"], "the armed snapshot is finished, no watch")
        self.assertEqual(error.restore, ({"id": SNAPSHOT, "held": False}, 0))
        self.assertFalse(self.target.exists())
        self.assert_owner_files_untouched()

    def test_a_launch_that_may_have_started_a_game_is_watched_and_never_restored_beside_it(self):
        # start_unconfirmed and not_recorded come after the claim; watch refuses at once (no `started`)
        not_recorded = {"held": False, "refused": "not_recorded", "id": SNAPSHOT, "pid": GAME.pid,
                        "created": GAME.created, "detail": "the game started but its start could not be recorded"}
        for reply, proc in ((UNCONFIRMED, None), (not_recorded, GAME)):
            with self.subTest(refused=reply["refused"]):
                fake = self.cli(replies={"launch": [(reply, 2)]}, save_at_launch=True)
                fake.watch_code = 2
                error = self.assert_fixture_error("launch")
                self.assertEqual(error.code, fixture.GAME_MAY_BE_UP)
                self.assertEqual((error.snapshot, error.proc, error.restore), (SNAPSHOT, proc, None))
                self.assertIs(error.watch, fake.watches[0])
                self.assertEqual(fake.order, ["snapshot", "launch", "spawn_watch " + SNAPSHOT], "no restore")
                self.assertFalse(self.target.exists())
                self.assertIn(SNAPSHOT, str(error))
                (self.save_dir / GAME_SAVE).unlink()

    def test_a_launch_whose_reply_was_lost_is_watched_and_restored_once_the_game_has_quit(self):
        fake = self.cli()
        fake.raise_on = "launch"
        error = self.assert_fixture_error("launch")
        self.assertIsNone(error.code)
        self.assertIn("blew up", str(error))
        self.assertEqual(fake.order, ["snapshot", "launch", "spawn_watch " + SNAPSHOT, "restore"])
        self.assertFalse(self.target.exists(), "a launch that did not answer is not trusted for the fixture")

    def test_a_lost_launch_reply_takes_the_game_from_the_journal_when_it_may_still_be_up(self):
        fake = self.cli()
        fake.raise_on = "launch"
        fake.watch_code = 2
        self.journaled[SNAPSHOT] = GAME
        error = self.assert_fixture_error("launch")
        self.assertEqual((error.code, error.proc), (fixture.GAME_MAY_BE_UP, GAME))
        self.assertNotIn("restore", fake.verbs)

    def test_a_watch_that_returns_without_recording_the_exit_leaves_the_game_to_the_caller(self):
        fake = self.cli()
        fake.watch_code = 2
        error = self.assert_fixture_error("watch")
        self.assertEqual((error.code, error.snapshot, error.proc), (fixture.GAME_MAY_BE_UP, SNAPSHOT, GAME))
        self.assertIs(error.watch, fake.watches[0])
        self.assertNotIn("restore", fake.verbs)
        self.assertFalse(self.target.exists())

    def test_a_watch_that_cannot_be_started_leaves_the_game_to_the_caller(self):
        fake = self.cli()
        fake.spawn_error = OSError("python3 could not be started")
        error = self.assert_fixture_error("watch")
        self.assertEqual((error.code, error.proc, error.watch), (fixture.GAME_MAY_BE_UP, GAME, None))
        self.assertIn("python3 could not be started", str(error))
        self.assertNotIn("restore", fake.verbs)

    def test_the_run_has_a_time_limit(self):
        fake = self.cli()
        fake.watch_hangs = True                 # the game never quits by itself
        error = self.assert_fixture_error("watch")
        self.assertEqual((error.code, error.proc), (fixture.GAME_MAY_BE_UP, GAME))
        self.assertIsNone(error.watch.poll(), "the watch is left following the game")
        self.assertGreaterEqual(self.now, fixture.FIXTURE_LIMIT_S)
        self.assertLess(self.now, fixture.FIXTURE_LIMIT_S + fixture.WATCH_POLL_S + 1)
        self.assertIn("%g s" % fixture.FIXTURE_LIMIT_S, str(error))
        self.assertNotIn("restore", fake.verbs)

    def test_an_interrupt_while_the_game_runs_restores_nothing(self):
        fake = self.cli()
        fake.watch_hangs = True

        def interrupted(seconds):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            fixture.make(fake, self.user, KEY, OVERLAY, PERMISSION, "mod_only", sleep=interrupted,
                         spawn_watch=fake.spawn_watch, clock=lambda: self.now)
        self.assertNotIn("restore", fake.verbs)

    def test_restore_is_still_called_when_no_save_appeared(self):
        fake = self.cli(saves=())
        error = self.assert_fixture_error("save")
        self.assertEqual(error.snapshot, SNAPSHOT)
        self.assertEqual(error.reply, {})
        self.assertEqual(fake.verbs, ["snapshot", "launch", "restore"])
        self.assertFalse(self.target.exists())
        self.assert_owner_files_untouched()

    def test_more_than_one_save_is_a_fixture_error_and_none_is_renamed(self):
        names = ["TEST_FAIL_te_qa_fixture_2 January, 1836.v3", "TEST_FAIL_te_qa_fixture_3 January, 1836.v3"]
        fake = self.cli(saves=names)
        error = self.assert_fixture_error("save")
        self.assertEqual(error.reply, {"saves": sorted(names)})
        self.assertEqual(fake.verbs[-1], "restore")
        self.assertFalse(self.target.exists())
        self.assertEqual(sorted(os.listdir(self.save_dir)), sorted(self.owner_files))

    def test_a_save_of_another_name_is_not_taken_for_the_fixture(self):
        fake = self.cli(saves=("TEST_FAIL_something_else_2 January, 1836.v3", "te_qa_scratch.v3"))
        self.assert_fixture_error("save")
        self.assertFalse(self.target.exists())
        self.assertEqual(fake.verbs[-1], "restore")

    def test_a_held_restore_is_a_fixture_error_that_names_the_snapshot(self):
        fake = self.cli(replies={"restore": [(HELD, 2)]})
        error = self.assert_fixture_error("restore")
        self.assertEqual(error.reply, HELD)
        self.assertEqual(error.snapshot, SNAPSHOT)
        self.assertEqual(error.restore, (HELD, 2))
        self.assertIn(SNAPSHOT, str(error))
        self.assertIn("other_game_ran", str(error))
        self.assertEqual(fake.verbs.count("restore"), 1, "a hold is not retried")
        self.assertEqual(self.target.read_bytes(), GAME_SAVE_BYTES, "the save was kept before the hold")

    def test_the_runs_lines_are_kept_once_the_fixture_is_made_and_restored(self):
        # #1601: the restore has copied the run's logs into its snapshot by then, and nothing else keeps them
        fake = self.cli()
        kept: list[tuple[str, list[str], bool]] = []
        path = self.make(keep_lines=lambda snap: kept.append((snap, list(fake.order), self.target.is_file())))
        self.assertEqual(path, self.target)
        self.assertEqual(kept, [(SNAPSHOT, ["snapshot", "launch", "spawn_watch " + SNAPSHOT, "restore"], True)])

    def test_no_lines_are_kept_for_a_fixture_that_was_not_made_or_not_restored(self):
        for name, kwargs, step in (("no save", {"saves": ()}, "save"),
                                   ("held", {"replies": {"restore": [(HELD, 2)]}}, "restore"),
                                   ("refused launch", {"replies": {"launch": [(REFUSED, 2)]}}, "launch")):
            with self.subTest(name):
                self.target.unlink(missing_ok=True)
                self.cli(**kwargs)
                kept: list[str] = []
                self.assert_fixture_error(step, keep_lines=kept.append)
                self.assertEqual(kept, [])

    def test_the_first_failure_is_the_one_raised_and_a_later_one_is_added_to_the_message(self):
        fake = self.cli(saves=(), replies={"restore": [(HELD, 2)]})
        error = self.assert_fixture_error("save")
        self.assertEqual(error.snapshot, SNAPSHOT)
        self.assertEqual(error.restore, (HELD, 2))
        self.assertIn("left no", str(error))
        self.assertIn("other_game_ran", str(error))
        self.assertEqual(fake.verbs[-1], "restore")

    def test_restore_is_retried_while_watch_is_still_recording_or_busy(self):
        recording = {"held": False, "refused": "watch_still_recording", "id": SNAPSHOT}
        busy = {"held": False, "refused": "busy", "detail": "another session is in `snapshot`"}
        fake = self.cli(replies={"restore": [(recording, 2), (busy, 2), (recording, 2)]})
        self.assertEqual(self.make(), self.target)
        self.assertEqual(fake.verbs, ["snapshot", "launch", "restore", "restore", "restore", "restore"])
        self.assertEqual(self.sleeps, [5, 5, 5])

    def test_restore_retries_stop_after_their_time(self):
        for refused, total in (("watch_still_recording", 30), ("busy", 60)):
            with self.subTest(refused=refused):
                self.sleeps.clear()
                reply = {"held": False, "refused": refused, "id": SNAPSHOT}
                fake = self.cli(replies={"restore": [(reply, 2)] * 20})
                error = self.assert_fixture_error("restore")
                self.assertEqual(error.reply, reply)
                self.assertEqual(self.sleeps, [5] * (total // 5))
                self.assertEqual(fake.verbs.count("restore"), total // 5 + 1)
                self.target.unlink()

    def test_launch_in_flight_and_other_refusals_are_not_retried(self):
        # The fixture cannot end its game: waiting out launch_in_flight would end in a hold beside it.
        for refused in ("launch_in_flight", "game_still_up"):
            with self.subTest(refused=refused):
                self.sleeps.clear()
                fake = self.cli(replies={"restore": [({"held": False, "refused": refused, "id": SNAPSHOT}, 2)]})
                self.assert_fixture_error("restore")
                self.assertEqual(fake.verbs.count("restore"), 1)
                self.assertEqual(self.sleeps, [])
                self.target.unlink()

    def test_a_restore_that_raises_is_a_refusal(self):
        fake = self.cli()
        fake.raise_on = "restore"
        error = self.assert_fixture_error("restore")
        self.assertEqual(error.reply["refused"], "error")
        self.assertIn("blew up", error.reply["detail"])

    def test_a_reply_that_is_not_an_object_is_a_refusal(self):
        fake = self.cli(replies={"snapshot": [("Traceback: boom", 1)]})
        error = self.assert_fixture_error("snapshot")
        self.assertIsInstance(error.reply, dict)
        self.assertEqual(fake.verbs, ["snapshot"])

    def test_a_snapshot_reply_without_an_id_is_refused(self):
        fake = self.cli(replies={"snapshot": [({"files": 3}, 0)]})
        self.assert_fixture_error("snapshot")
        self.assertEqual(fake.verbs, ["snapshot"])

    def test_which_launch_refusals_mean_that_no_game_started(self):
        claimed = ("x could not be written (e), so it is as it was. Nothing was started. The snapshot stays claimed, "
                   "so `launch` refuses it: `restore <id>` or `recover` finishes it 90 s after the claim")
        cases = (({"refused": "gpu_busy"}, True), ({"refused": "busy"}, True), ({"refused": "stale_snapshot"}, True),
                 ({"refused": "playset_unwritable", "detail": "could not be read (e). Nothing was written"}, True),
                 ({"refused": "playset_unwritable", "detail": claimed}, False), ({"refused": "not_recorded"}, False),
                 ({"refused": "start_unconfirmed"}, False), ({"refused": "a_name_not_known_here"}, False),
                 ({"error": "not a JSON object"}, False))
        for reply, no_game in cases:
            with self.subTest(reply=reply):
                self.assertIs(fixture.no_game(reply), no_game)


class BeforeAnythingRunsTest(FixtureTestCase):
    def test_an_existing_fixture_of_that_key_is_refused_before_any_verb(self):
        self.target.write_bytes(b"already kept")
        fake = self.cli()
        error = self.assert_fixture_error("check")
        self.assertIn(self.target.name, str(error))
        self.assertEqual(fake.calls, [])
        self.assertEqual(self.target.read_bytes(), b"already kept")

    def test_a_leftover_test_fail_save_is_refused_before_any_verb(self):
        leftover = self.save_dir / GAME_SAVE
        leftover.write_bytes(b"from an earlier run that was held")
        fake = self.cli()
        error = self.assert_fixture_error("check")
        self.assertIn(GAME_SAVE, str(error))
        self.assertEqual(fake.calls, [])
        self.assertEqual(leftover.read_bytes(), b"from an earlier run that was held")
        self.assertFalse(self.target.exists())

    def test_a_target_that_appears_during_the_run_is_not_overwritten(self):
        fake = self.cli()
        original = fake.__call__

        def appears(argv):
            reply = original(argv)
            if argv[0] == "launch":         # while the game runs
                self.target.write_bytes(b"someone else made it")
            return reply

        error = self.assert_fixture_error("rename", fake=appears)
        self.assertEqual(self.target.read_bytes(), b"someone else made it")
        self.assertEqual(fake.verbs[-1], "restore")
        self.assertEqual(error.snapshot, SNAPSHOT)


class PruneTest(FixtureTestCase):
    def test_prune_keeps_two_and_only_touches_fixtures(self):
        (self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").unlink()
        del self.owner_files["te_qa_fixture_aaaaaaaaaaaa.v3"]
        fixtures = {}
        for age, key in enumerate(("oldest", "older", "newer", "newest")):
            path = self.save_dir / f"te_qa_fixture_{key}.v3"
            path.write_bytes(key.encode())
            os.utime(path, (1_700_000_000 + age * 1000,) * 2)
            fixtures[key] = path
        others = {
            "TEST_FAIL_te_qa_fixture_2 January, 1836.v3": b"a run's save",
            "te_qa_scratch.v3": b"scratch",
            "te_qa_fixture_notes.txt": b"not a save",
            "te_qa_fixture.v3": b"no underscore after fixture",
            "xte_qa_fixture_x.v3": b"other prefix",
        }
        for name, data in others.items():
            (self.save_dir / name).write_bytes(data)
            os.utime(self.save_dir / name, (1_600_000_000,) * 2)
        (self.save_dir / "te_qa_fixture_dir.v3").mkdir()
        (self.user / "te_qa_fixture_elsewhere.v3").write_bytes(b"not in save games")

        removed = fixture.prune(self.user)

        self.assertEqual(removed, ["te_qa_fixture_oldest.v3", "te_qa_fixture_older.v3"])
        self.assertFalse(fixtures["oldest"].exists() or fixtures["older"].exists())
        self.assertTrue(fixtures["newer"].exists() and fixtures["newest"].exists())
        self.assert_owner_files_untouched()
        for name, data in others.items():
            self.assertEqual((self.save_dir / name).read_bytes(), data, name)
        self.assertTrue((self.save_dir / "te_qa_fixture_dir.v3").is_dir())
        self.assertTrue((self.user / "te_qa_fixture_elsewhere.v3").is_file())

    def test_prune_with_few_fixtures_removes_nothing(self):
        self.assertEqual(fixture.prune(self.user), [])
        self.assertTrue((self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").exists())

    def test_prune_with_no_save_folder_removes_nothing(self):
        self.assertEqual(fixture.prune(self.base / "no user data"), [])

    def test_prune_keep_zero_removes_every_fixture_and_nothing_else(self):
        self.assertEqual(fixture.prune(self.user, keep=0), ["te_qa_fixture_aaaaaaaaaaaa.v3"])
        self.assertEqual(sorted(os.listdir(self.save_dir)), ["autosave.v3", "mine.v3", "notes.txt"])

    def test_prune_breaks_equal_times_by_name_and_is_repeatable(self):
        for key in ("a", "b", "c", "d"):
            path = self.save_dir / f"te_qa_fixture_{key}.v3"
            path.write_bytes(b"x")
            os.utime(path, (1_700_000_000,) * 2)
        os.utime(self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3", (1_600_000_000,) * 2)
        self.assertEqual(
            fixture.prune(self.user),
            ["te_qa_fixture_aaaaaaaaaaaa.v3", "te_qa_fixture_a.v3", "te_qa_fixture_b.v3"],
        )
        self.assertEqual(fixture.prune(self.user), [])

    def test_switched_copies_are_not_counted_among_the_fixtures(self):
        # Two copies with a rule switched must not push out the fixture they were made from.
        (self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").unlink()
        times = {"te_qa_fixture_old.v3": 1, "te_qa_fixture_base.v3": 2, "te_qa_fixture_new.v3": 3,
                 "te_qa_fixture_old_s11111111.v3": 4, "te_qa_fixture_base_s22222222.v3": 5,
                 "te_qa_fixture_base_s33333333.v3": 6, "te_qa_fixture_base_s44444444.v3": 7}
        for name, age in times.items():
            (self.save_dir / name).write_bytes(b"x")
            os.utime(self.save_dir / name, (1_700_000_000 + age * 1000,) * 2)
        removed = fixture.prune(self.user)
        # The oldest fixture goes, with the copy made from it; of base's three copies the two newest stay.
        self.assertEqual(removed, ["te_qa_fixture_old.v3", "te_qa_fixture_old_s11111111.v3",
                                   "te_qa_fixture_base_s22222222.v3"])
        left = sorted(name for name in os.listdir(self.save_dir) if name.startswith("te_qa_fixture_"))
        self.assertEqual(left, ["te_qa_fixture_base.v3", "te_qa_fixture_base_s33333333.v3",
                                "te_qa_fixture_base_s44444444.v3", "te_qa_fixture_new.v3"])
        self.assertEqual(fixture.prune(self.user), [])

    def test_a_file_in_use_is_never_removed_whatever_its_age(self):
        # Review finding: a copy used again keeps its old time, so prune removed the save the reply named.
        (self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").unlink()
        names = ["te_qa_fixture_base.v3", "te_qa_fixture_base_s11111111.v3", "te_qa_fixture_base_s22222222.v3",
                 "te_qa_fixture_base_s33333333.v3", "te_qa_fixture_mid.v3", "te_qa_fixture_new.v3"]
        for age, name in enumerate(names):
            (self.save_dir / name).write_bytes(b"x")
            os.utime(self.save_dir / name, (1_700_000_000 + age * 1000,) * 2)
        in_use = ("te_qa_fixture_base_s11111111.v3", "te_qa_fixture_base.v3")
        removed = fixture.prune(self.user, in_use=in_use)
        self.assertEqual(removed, [])       # the base is in use, so its copies have a fixture; the oldest is in use
        os.utime(self.save_dir / "te_qa_fixture_base_s11111111.v3", (1_600_000_000,) * 2)
        (self.save_dir / "te_qa_fixture_base_s44444444.v3").write_bytes(b"x")
        removed = fixture.prune(self.user, in_use=in_use)
        self.assertNotIn("te_qa_fixture_base_s11111111.v3", removed)
        self.assertNotIn("te_qa_fixture_base.v3", removed)
        self.assertTrue(all((self.save_dir / name).exists() for name in in_use))

    def test_a_hand_named_fixture_with_an_underscore_s_is_a_plain_fixture(self):
        # Review finding: `_s` anywhere in the key read as a switched copy, and the file went as an orphan.
        path = self.save_dir / "te_qa_fixture_my_seed.v3"
        path.write_bytes(b"x")
        self.assertEqual(fixture.prune(self.user), [])
        self.assertTrue(path.exists())

    def test_a_negative_keep_is_refused_and_removes_nothing(self):
        with self.assertRaises(ValueError):
            fixture.prune(self.user, keep=-1)
        self.assertTrue((self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").exists())


DATE_1900 = (1900, 1, 1)
SAVE_1900 = "TEST_FAIL_te_qa_fixture_1 January, 1900.v3"
DATED_KEY = KEY + "_d19000101"
GRANT = "the owner, 21:40: run it to 1900 overnight, up to 8 hours"


def plain_text_save(date: str) -> bytes:
    """The start of a harness save as the engine writes one: the header line, then meta_data with its date."""
    return ("SAV01001b3624cd0000078e\nmeta_data={\n\tsave_game_version=1794310339\n\tversion=\"1.15.1\"\n"
            f"\tgame_date={date}\n\treal_date=126.11.12\n}}\n").encode()


class DateTest(unittest.TestCase):
    def test_a_date_is_a_year_or_year_month_day_of_the_games_calendar(self):
        self.assertEqual(fixture.parse_date("1900"), (1900, 1, 1))
        self.assertEqual(fixture.parse_date(" 1950.7.15 "), (1950, 7, 15))
        for bad in ("", "1900.1", "1900.2.29", "1900.13.1", "1900.0.1", "1900.4.31", "nineteen hundred", "19000",
                    "1900.1.1.1", "-1900"):
            with self.subTest(text=bad):
                with self.assertRaises(ValueError):
                    fixture.parse_date(bad)

    def test_days_are_counted_on_a_year_of_365_days(self):
        self.assertEqual(fixture.shift((1899, 12, 31), 1), (1900, 1, 1))
        self.assertEqual(fixture.shift((1900, 2, 28), 1), (1900, 3, 1))       # no leap day, in 1900 or 2000
        self.assertEqual(fixture.shift((2000, 2, 28), 1), (2000, 3, 1))
        self.assertEqual(fixture.shift((1900, 1, 1), -1), (1899, 12, 31))
        self.assertEqual(fixture.day_number((1901, 1, 1)) - fixture.day_number((1900, 1, 1)), 365)
        for number in range(fixture.day_number((1836, 1, 1)), fixture.day_number((1838, 1, 1))):
            self.assertEqual(fixture.day_number(fixture.from_day_number(number)), number)

    def test_the_plain_fixtures_date_gives_the_1836_runs_arguments_and_name(self):
        self.assertEqual(fixture.fixture_args(), fixture.FIXTURE_ARGS)
        self.assertEqual(fixture.fixture_args(fixture.DEFAULT_DATE), fixture.FIXTURE_ARGS)
        self.assertEqual(fixture.expected_save(fixture.DEFAULT_DATE), GAME_SAVE)
        self.assertEqual(fixture.dated_key(KEY, fixture.DEFAULT_DATE), KEY)
        self.assertIsNone(fixture.date_of_key(KEY))

    def test_a_dated_fixture_runs_two_days_past_its_date_as_the_1836_one_does(self):
        self.assertEqual(fixture.fixture_args(DATE_1900)[-1], "-run_until=1900.1.3")
        self.assertEqual(fixture.fixture_args(DATE_1900)[:-1], fixture.FIXTURE_ARGS[:-1])
        self.assertEqual(fixture.expected_save(DATE_1900), SAVE_1900)
        self.assertEqual(fixture.dated_key(KEY, DATE_1900), DATED_KEY)
        self.assertEqual(fixture.date_of_key(DATED_KEY), DATE_1900)
        self.assertEqual(fixture.date_of_key(DATED_KEY + "_s0123abcd"), DATE_1900)   # its switched copy
        self.assertIsNone(fixture.date_of_key(KEY + "_d19000231"))                    # not a date
        self.assertEqual(fixture.written_date(SAVE_1900), DATE_1900)
        self.assertEqual(fixture.written_date(GAME_SAVE), fixture.DEFAULT_DATE)
        self.assertIsNone(fixture.written_date("TEST_FAIL_te_qa_fixture_1 Smarch, 1900.v3"))

    def test_a_fixture_date_must_leave_the_run_inside_the_game(self):
        end = (2136, 1, 1)
        self.assertEqual(fixture.check_fixture_date((1836, 1, 2), end), (1836, 1, 2))
        self.assertEqual(fixture.check_fixture_date((2135, 12, 29), end), (2135, 12, 29))
        for date in ((1836, 1, 1), (1835, 12, 31), (2135, 12, 30), (2200, 1, 1)):
            with self.subTest(date=date):
                with self.assertRaises(ValueError):
                    fixture.check_fixture_date(date, end)

    def test_the_games_end_date_is_read_from_the_defines_the_mod_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            vanilla, mod = Path(tmp) / "vanilla", Path(tmp) / "mod"
            vanilla.mkdir()
            mod.mkdir()
            self.assertEqual(fixture.game_end([vanilla, mod]), fixture.VANILLA_END_DATE)
            (vanilla / "00_defines.txt").write_text('NGame = {\n\tSTART_DATE = "1836.1.1"\n\tEND_DATE = "1936.1.1"\n}\n',
                                                    encoding="utf-8-sig")
            self.assertEqual(fixture.game_end([vanilla, mod]), (1936, 1, 1))
            (mod / "extra_defines.txt").write_text('NGame = {\n\t# END_DATE = "1999.1.1"\n\tEND_DATE = "2136.1.1"\n}\n',
                                                   encoding="utf-8")
            self.assertEqual(fixture.game_end([vanilla, mod]), (2136, 1, 1))


class EstimateTest(unittest.TestCase):
    def test_the_1836_fixtures_limit_is_unchanged(self):
        self.assertEqual(fixture.time_limit_s(fixture.DEFAULT_DATE), fixture.FIXTURE_LIMIT_S)
        self.assertLess(fixture.estimate_s(fixture.DEFAULT_DATE), 120)      # 90 s, live (spec § 3.6)

    def test_a_run_to_1904_is_estimated_at_the_overnight_observer_runs_pace(self):
        # vic3te-demog-overnight-2026-10-12: 1836.2.1 to 1876.1.1 in 1.89 h, 1877.1.1 to 1904.1.1 in 1.44 h.
        hours = fixture.estimate_s((1904, 1, 1)) / 3600
        self.assertGreater(hours, 3.33 * 0.85)
        self.assertLess(hours, 3.33 * 1.25)

    def test_the_estimate_and_the_limit_grow_with_the_span_and_the_limit_stays_well_above(self):
        dates = [(1836, 7, 1), (1850, 1, 1), (1900, 1, 1), (1950, 1, 1), (2000, 1, 1), (2050, 1, 1)]
        estimates = [fixture.estimate_s(date) for date in dates]
        limits = [fixture.time_limit_s(date) for date in dates]
        self.assertEqual(estimates, sorted(estimates))
        self.assertEqual(limits, sorted(limits))
        for date, estimate, limit in zip(dates, estimates, limits):
            with self.subTest(date=date):
                self.assertGreater(limit, fixture.FIXTURE_LIMIT_S + 2.5 * (estimate - fixture.LOAD_S))
        self.assertGreater(fixture.seconds_per_day(2050), fixture.seconds_per_day(1951))   # rising past the last anchor


class TimingTest(unittest.TestCase):
    def test_the_games_timing_file_gives_seconds_per_day_and_its_month_rows_are_not_counted(self):
        text = ("Game Date \tTime Unit \tSeconds\n"
                "1836_03_01\tMonth\t17.889766\n"
                "1836_01_01\tDay\t2.0\n1836_01_01\tDay\t0.5\n"
                "1836_01_02\tDay\t0.25\n1836_01_02\tDay\t0.25\n"
                "1837_01_01\tDay\t1.0\n"
                "\t\t0.070176\nnot a row\n")
        out = fixture.timing(text)
        self.assertEqual((out["days"], out["seconds"], out["seconds_per_day"]), (3, 4.0, 1.333))
        self.assertEqual(out["years"], {"1836": 1.5, "1837": 1.0})
        self.assertEqual(fixture.timing("Game Date \tTime Unit \tSeconds\n")["seconds_per_day"], None)

    def test_a_saves_own_date_is_read_from_its_meta_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.v3"
            path.write_bytes(plain_text_save("1900.1.1"))
            self.assertEqual(fixture.save_date(path), (1900, 1, 1))
            path.write_bytes(b"SAV0103\x00binary")
            self.assertIsNone(fixture.save_date(path))
            self.assertIsNone(fixture.save_date(Path(tmp) / "gone.v3"))


class DatedMakeTest(FixtureTestCase):
    def setUp(self):
        super().setUp()
        self.target = self.save_dir / f"te_qa_fixture_{DATED_KEY}.v3"
        self.follows: list[tuple[str, int]] = []

    def dated(self, fake=None, **kwargs):
        kwargs.setdefault("date", DATE_1900)
        kwargs.setdefault("limit_s", fixture.time_limit_s(DATE_1900))
        kwargs.setdefault("long_run", GRANT)
        return fixture.make(fake or self.fake, self.user, DATED_KEY, OVERLAY, PERMISSION, "mod_only", sleep=self.sleep,
                            spawn_watch=self.fake.spawn_watch, clock=lambda: self.now, started=self.journaled.get,
                            **kwargs)

    def follow(self, snapshot_id):
        self.follows.append((snapshot_id, self.fake.watches[-1].polls if self.fake.watches else 0))

    def test_the_launch_carries_the_dates_end_and_the_owners_grant(self):
        fake = self.cli(saves=(SAVE_1900,))
        fake.watch_code = 0
        made = self.dated()
        self.assertEqual(made, self.target)
        launch = fake.calls[1]
        self.assertEqual(launch[launch.index("--") + 1:], list(fixture.fixture_args(DATE_1900)))
        self.assertEqual(launch[launch.index("--long-run") + 1], GRANT)
        self.assertLess(launch.index("--long-run"), launch.index("--"))
        self.assertEqual(fake.verbs, ["snapshot", "launch", "restore"])

    def test_the_plain_fixtures_launch_carries_no_grant(self):
        fake = self.cli()
        self.make()
        self.assertNotIn("--long-run", fake.calls[1])

    def test_the_watch_waits_the_dated_limit_not_the_1836_one(self):
        fake = self.cli(saves=(SAVE_1900,))
        fake.watch_hangs = True
        limit = fixture.time_limit_s(DATE_1900)
        with self.assertRaises(fixture.FixtureError) as caught:
            self.dated()
        self.assertEqual(caught.exception.code, fixture.GAME_MAY_BE_UP)
        self.assertGreaterEqual(self.now, limit)
        self.assertLess(self.now, limit + fixture.WATCH_POLL_S + 1)
        self.assertNotIn("restore", fake.verbs)                     # never beside a game that may be up

    def test_the_logs_are_followed_while_watch_follows_and_once_more_at_the_exit(self):
        fake = self.cli(saves=(SAVE_1900,))
        fake.watch_hangs = True
        watches = []

        def spawn(snapshot_id):
            watch = fake.spawn_watch(snapshot_id)
            watches.append(watch)
            return watch

        original = FakeWatch.poll

        def poll(watch):
            if watch.polls >= 30:       # the game quits by itself on its date: the save, then watch returns 0
                watch.hangs = False
                watch.polls = 0
            return original(watch)

        with unittest.mock.patch.object(FakeWatch, "poll", poll):
            fixture.make(fake, self.user, DATED_KEY, OVERLAY, PERMISSION, "mod_only", sleep=self.sleep,
                         spawn_watch=spawn, clock=lambda: self.now, date=DATE_1900, limit_s=10_000, long_run=GRANT,
                         follow=self.follow)
        times = [polls for _, polls in self.follows]
        self.assertTrue(all(snap == SNAPSHOT for snap, _ in self.follows))
        self.assertGreaterEqual(len(times), 30 * fixture.WATCH_POLL_S / fixture.FOLLOW_S)   # every FOLLOW_S
        self.assertLessEqual(len(times), 30 * fixture.WATCH_POLL_S / fixture.FOLLOW_S + 2)
        self.assertEqual(self.follows[0][1], 1)                     # from the first poll on
        self.assertEqual(self.follows[-1][1], 1)                    # and once after watch returned, before the rename
        self.assertTrue(self.target.exists())

    def test_a_follow_that_raises_costs_the_run_nothing(self):
        fake = self.cli(saves=(SAVE_1900,))

        def broken(_snapshot_id):
            raise OSError("the backup drive is full")
        self.assertEqual(self.dated(follow=broken), self.target)
        self.assertEqual(fake.verbs, ["snapshot", "launch", "restore"])

    def test_the_saves_name_and_own_date_are_reported_and_never_refused(self):
        # The name of a later save rests on one data point (2 January, 1836): a surprise must not cost the run,
        # since the restore would remove an unrenamed save.
        for name, date, matches in ((SAVE_1900, "1900.1.1", True),
                                    ("TEST_FAIL_te_qa_fixture_2 January, 1900.v3", "1900.1.2", False),
                                    ("TEST_FAIL_te_qa_fixture_1900.01.01.v3", "1900.1.1", True)):
            with self.subTest(name=name):
                for path in self.save_dir.glob("te_qa_fixture_*_d*.v3"):
                    path.unlink()
                fake = self.cli(saves=(name,))
                fake.write_saves = lambda fake=fake, name=name, date=date: (fake.save_dir / name).write_bytes(
                    plain_text_save(date))
                facts: dict = {}
                self.assertEqual(self.dated(facts=facts), self.target)
                self.assertEqual(facts["save_found"], name)
                self.assertEqual(facts["save_expected"], SAVE_1900)
                self.assertEqual((facts["game_date"], facts["date_matches"]), (date, matches))

    def test_a_restore_that_holds_after_the_rename_leaves_the_fixture_and_says_so(self):
        # A run of hours ends held when one of its thousands of looks failed (`unwatched_stretch`): the save has
        # its name already, so the fixture is there for once the owner has resolved the hold.
        self.cli(saves=(SAVE_1900,), replies={"restore": [({"held": True, "reason": "unwatched_stretch",
                                                            "id": SNAPSHOT}, 2)]})
        kept = []
        with self.assertRaises(fixture.FixtureError) as caught:
            self.dated(keep_lines=kept.append)
        self.assertEqual(caught.exception.step, "restore")
        self.assertEqual(caught.exception.saved, self.target)
        self.assertEqual(self.target.read_bytes(), GAME_SAVE_BYTES)
        self.assertEqual(kept, [])                                  # nothing vouches for its lines
        self.assertIsNone(caught.exception.code)                    # the game is known to have quit

    def test_no_save_when_the_owner_closes_the_game_early_restores_and_keeps_nothing(self):
        # How the owner takes the desktop back during a long run: they close the game; `watch` records the exit,
        # no save is found, and the run is restored.
        fake = self.cli(saves=())
        error = self.assert_fixture_error_dated("save")
        self.assertIsNone(error.saved)
        self.assertEqual(fake.verbs, ["snapshot", "launch", "restore"])
        self.assertFalse(self.target.exists())

    def assert_fixture_error_dated(self, step, **kwargs):
        with self.assertRaises(fixture.FixtureError) as caught:
            self.dated(**kwargs)
        self.assertEqual(caught.exception.step, step)
        return caught.exception


class RunLogsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.logs = Path(tmp.name) / "logs"
        self.logs.mkdir()
        self.out = Path(tmp.name) / "backups" / "runs" / SNAPSHOT

    def write(self, name, text, mode="a"):
        with open(self.logs / name, mode, encoding="utf-8", newline="\n") as f:
            f.write(text)

    def rotate(self, name):
        stem, suffix = name.split(".")
        for k in range(5, 0, -1):
            older = self.logs / f"{stem}.{k - 1}.{suffix}" if k > 1 else self.logs / name
            if older.exists():
                os.replace(older, self.logs / f"{stem}.{k}.{suffix}")

    def test_the_copy_holds_every_line_across_rotations_and_skips_the_owners_beginning(self):
        owner = "the owner's last game\n"
        self.write("debug.log", owner, "w")
        found = {"debug.log": (len(owner), __import__("hashlib").sha256(owner.encode()).hexdigest())}
        logs = fixture.RunLogs(self.logs, self.out, found)
        self.write("debug.log", "TE_SELF_CHECK OK setup_line\n")      # the game appended to the log it found
        logs.poll()
        for round_ in range(8):                                      # more rotations than there are generations
            self.rotate("debug.log")
            self.write("debug.log", f"year {round_}\n", "w")
            logs.poll()
        self.write("error.log", "an error\n", "w")
        logs.poll()
        copy = (self.out / "fixture_debug.log").read_text(encoding="utf-8")
        self.assertNotIn("the owner's", copy)
        self.assertEqual(copy.splitlines(), ["TE_SELF_CHECK OK setup_line", *(f"year {k}" for k in range(8))])
        self.assertEqual((self.out / "fixture_error.log").read_text(encoding="utf-8"), "an error\n")
        record = logs.record()
        self.assertEqual((record["lines"], record["gaps"], record["prefix_skipped"]),
                         ({"debug.log": 9, "error.log": 1}, 0, {"debug.log": len(owner)}))
        self.assertNotIn("error", record)

    def test_a_rotation_it_missed_is_marked_and_counted(self):
        self.write("debug.log", "first\n", "w")
        logs = fixture.RunLogs(self.logs, self.out)
        logs.poll()
        for k in range(7):                       # the game wrote and rotated past every generation between polls
            self.rotate("debug.log")
            self.write("debug.log", f"line {k}\n", "w")
        logs.poll()
        self.assertEqual(logs.gaps, 1)
        self.assertIn(GAP_MARKER, (self.out / "fixture_debug.log").read_text(encoding="utf-8"))

    def test_an_error_stops_the_copy_for_good_and_never_raises(self):
        self.write("debug.log", "first\n", "w")
        self.out.parent.mkdir(parents=True)
        self.out.write_text("a file where the run folder should be")
        logs = fixture.RunLogs(self.logs, self.out)
        logs.poll()
        self.assertIsNotNone(logs.error)
        polls = logs.polls
        logs.poll()
        self.assertEqual(logs.polls, polls)
        self.assertIn("error", logs.record())


class RenameTest(FixtureTestCase):
    """Review of #1602: one failed rename of the run's save (OneDrive uploading 140 MB, say) and the restore removed
    it with the run's hours. The rename is tried again, then the save is copied; one that can be neither is left
    under its own name with the run's restore asked to hold (fixture.HOLD_ASKED)."""

    def setUp(self):
        super().setUp()
        self.target = self.save_dir / f"te_qa_fixture_{DATED_KEY}.v3"

    dated = DatedMakeTest.dated

    def rename_failing(self, times):
        real = os.rename
        tries = []

        def rename(src, dst, *a, **k):
            tries.append(str(dst))
            if len(tries) <= times:
                raise PermissionError(13, "The process cannot access the file because it is being used by another "
                                          "process", str(src))
            return real(src, dst, *a, **k)
        return mock.patch.object(fixture.os, "rename", rename), tries

    def test_a_rename_that_fails_for_a_while_is_tried_again(self):
        fake = self.cli(saves=(SAVE_1900,))
        patch, tries = self.rename_failing(3)
        facts = {}
        with patch:
            self.assertEqual(self.dated(facts=facts), self.target)
        self.assertEqual(len(tries), 4)
        self.assertEqual(self.sleeps.count(fixture.RENAME_RETRY_S), 3)
        self.assertEqual((facts["kept_by"], facts["rename_tries"]), ("rename", 4))
        self.assertEqual(fake.saves_at_restore[0].count(SAVE_1900), 0)

    def test_a_save_that_cannot_be_renamed_is_copied_to_its_name(self):
        fake = self.cli(saves=(SAVE_1900,))
        patch, tries = self.rename_failing(10_000)
        facts = {}
        with patch:
            self.assertEqual(self.dated(facts=facts), self.target)
        self.assertEqual(len(tries), fixture.RENAME_TRIES)
        self.assertEqual(self.target.read_bytes(), GAME_SAVE_BYTES)
        self.assertEqual(facts["kept_by"], "copy")
        self.assertFalse(self.target.with_name(self.target.name + ".part").exists())
        self.assertIn(SAVE_1900, fake.saves_at_restore[0])        # the engine's copy: the restore removes it
        self.assertNotIn(SAVE_1900, os.listdir(self.save_dir))

    def test_a_save_that_can_be_neither_renamed_nor_copied_asks_the_restore_to_hold(self):
        fake = self.cli(saves=(SAVE_1900,))
        patch, _tries = self.rename_failing(10_000)
        marks = []
        with patch, mock.patch.object(fixture.shutil, "copy2", side_effect=OSError(28, "No space left on device")):
            with self.assertRaises(fixture.FixtureError) as caught:
                self.dated(mark=lambda snap, event, **fields: marks.append((snap, event, fields, list(fake.verbs))))
        error = caught.exception
        self.assertEqual((error.step, error.left.name, error.reply["left"]), ("rename", SAVE_1900, SAVE_1900))
        # journaled before the restore ran, naming the save
        self.assertEqual(marks, [(SNAPSHOT, fixture.HOLD_ASKED, {"reason": "save_not_kept",
                                                                 "files": ["save games/" + SAVE_1900]},
                                  ["snapshot", "launch"])])
        self.assertEqual(fake.verbs, ["snapshot", "launch", "restore"])
        self.assertFalse(self.target.exists())
        self.assertEqual([p for p in os.listdir(self.save_dir) if p.endswith(".part")], [])

    def test_without_a_way_to_ask_the_hold_the_message_says_what_may_happen(self):
        self.cli(saves=(SAVE_1900,))
        patch, _tries = self.rename_failing(10_000)
        with patch, mock.patch.object(fixture.shutil, "copy2", side_effect=OSError(28, "No space left on device")):
            with self.assertRaises(fixture.FixtureError) as caught:
                self.dated()
        self.assertIn("the restore may remove save games/" + SAVE_1900, str(caught.exception))


class DatedPruneTest(FixtureTestCase):
    def put(self, name, age):
        path = self.save_dir / name
        path.write_bytes(b"x")
        os.utime(path, (1_700_000_000 + age * 1000,) * 2)
        return path

    def left(self):
        return sorted(name for name in os.listdir(self.save_dir) if name.startswith("te_qa_fixture_"))

    def test_cheap_1836_fixtures_never_push_out_a_dated_one(self):
        (self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").unlink()
        self.put("te_qa_fixture_old_d19000101.v3", 1)
        for age, key in enumerate(("p1", "p2", "p3", "p4"), start=2):
            self.put(f"te_qa_fixture_{key}.v3", age)
        removed = fixture.prune(self.user)
        self.assertEqual(removed, ["te_qa_fixture_p1.v3", "te_qa_fixture_p2.v3"])
        self.assertIn("te_qa_fixture_old_d19000101.v3", self.left())

    def test_the_newest_few_stay_whatever_their_dates(self):
        # Review of #1602: a newer fixture of the same date may be the other playset's, not a newer build's (the
        # key cannot say which), so it never makes an older one go: only the count does.
        (self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").unlink()
        self.put("te_qa_fixture_old_d19000101.v3", 1)
        self.put("te_qa_fixture_old_d19500101.v3", 2)
        self.put("te_qa_fixture_new_d19000101.v3", 3)      # 1900 made again: a newer build, or the other playset
        self.assertEqual(fixture.prune(self.user), [])
        self.put("te_qa_fixture_new_d20000701.v3", 4)
        self.assertEqual(fixture.prune(self.user, keep_dated=4), [])
        self.put("te_qa_fixture_new_d18360701.v3", 9)                         # a fifth: the oldest goes
        self.assertEqual(fixture.prune(self.user, keep_dated=4), ["te_qa_fixture_old_d19000101.v3"])

    def test_a_current_playset_fixture_never_pushes_out_the_mod_only_one_of_its_date(self):
        deploy = self.base / "deploy"
        (deploy / "common").mkdir(parents=True)
        (deploy / "common" / "a.txt").write_text("x")
        mod_only = fixture.key("1.15.1", [r"C:\mod\TE", r"C:\mod\te_qa_overlay"], deploy, playset="mod_only")
        current = fixture.key("1.15.1", [r"C:\mod\TE", r"C:\mod\Other", r"C:\mod\te_qa_overlay"], deploy,
                              playset="current")
        first = self.put("te_qa_fixture_%s.v3" % fixture.dated_key(mod_only, (1900, 1, 1)), 1)
        second = self.put("te_qa_fixture_%s.v3" % fixture.dated_key(current, (1900, 1, 1)), 2)
        for in_use in ((second.name,), (first.name,), ()):
            self.assertEqual(fixture.prune(self.user, in_use=in_use), [])
        self.assertTrue(first.exists() and second.exists())

    def test_a_dated_fixtures_switched_copies_go_with_it_and_count_with_the_others(self):
        (self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").unlink()
        self.put("te_qa_fixture_old_d19000101.v3", 1)
        self.put("te_qa_fixture_old_d19000101_s11111111.v3", 2)
        self.put("te_qa_fixture_new_d19000101.v3", 3)
        self.put("te_qa_fixture_new_d19000101_s22222222.v3", 4)
        removed = fixture.prune(self.user, keep_dated=1)
        self.assertEqual(removed, ["te_qa_fixture_old_d19000101.v3", "te_qa_fixture_old_d19000101_s11111111.v3"])
        self.assertEqual(self.left(), ["te_qa_fixture_new_d19000101.v3", "te_qa_fixture_new_d19000101_s22222222.v3"])

    def test_a_dated_fixture_in_use_stays_past_the_count(self):
        (self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").unlink()
        self.put("te_qa_fixture_old_d19000101.v3", 1)
        self.put("te_qa_fixture_new_d19000101.v3", 2)
        self.assertEqual(fixture.prune(self.user, keep_dated=1, in_use=("te_qa_fixture_old_d19000101.v3",)), [])
        with self.assertRaises(ValueError):
            fixture.prune(self.user, keep_dated=-1)

if __name__ == "__main__":
    unittest.main()
