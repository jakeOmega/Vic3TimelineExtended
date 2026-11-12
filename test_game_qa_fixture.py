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
from pathlib import Path

from game_qa import fixture
from game_qa.gate import ProcId

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

    def test_a_negative_keep_is_refused_and_removes_nothing(self):
        with self.assertRaises(ValueError):
            fixture.prune(self.user, keep=-1)
        self.assertTrue((self.save_dir / "te_qa_fixture_aaaaaaaaaaaa.v3").exists())


if __name__ == "__main__":
    unittest.main()
