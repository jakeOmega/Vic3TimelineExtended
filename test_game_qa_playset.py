"""`python3 -m game_qa launch --playset … --add-mod …`: the run's playset in `content_load.json`, and the owner's
put back by `restore` and `recover`, also after a start that failed once the playset was written.

Nothing here runs PowerShell, wslpath or nvidia-smi: gate.list_games, gate.start_game, gate.windows_path and
gate.sample_gpu are fakes, as in test_game_qa_gate.CommandLineTest.
"""
import contextlib
import datetime as dt
import hashlib
import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from game_qa import __main__ as cli
from game_qa import gate, restore, snapshot

IDLE = [gate.GpuSample(14, 1607, 10240)] * 5
UTC = dt.timezone.utc
WORKSHOP = "C:\\Program Files (x86)\\Steam\\steamapps\\workshop\\content\\529340\\"
OVERLAY = "C:\\Users\\owner\\OneDrive\\Documents\\Paradox Interactive\\Victoria 3\\mod\\te_qa_overlay"
PLAYSET = "content_load.json"


def windows(path) -> str:
    """What the fake `wslpath -w` makes of a path."""
    return "W:" + str(path).replace("/", "\\")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class UnexpectedStart(BaseException):
    """A test started a game it did not ask for. A BaseException, so `main` cannot turn it into JSON."""


class Killed(BaseException):
    """The process dying at that point: no `except Exception` catches it."""


class PlaysetTest(unittest.TestCase):
    """`launch`'s playset options against a temp user-data folder, backup root and deploy folder."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        self.user = root / "Victoria 3"
        (self.user / "save games").mkdir(parents=True)
        (self.user / "logs").mkdir()
        self.deploy = self.user / "mod" / "Vic3TimelineExtended"
        self.deploy.mkdir(parents=True)
        self.this_mod = windows(self.deploy)
        self.backups = root / "backups"
        self.base_game = root / "game"
        (self.base_game / "binaries").mkdir(parents=True)
        (self.base_game / "binaries" / "victoria3.exe").write_bytes(b"MZ")
        self.playset = self.user / PLAYSET
        self.owners_playset = {"enabledMods": [{"path": WORKSHOP + "3142463417"}, {"path": WORKSHOP + "3190466673"},
                                               {"path": self.this_mod}],
                               "disabledDLC": [], "enabledUGC": []}
        self.write_the_owners_files()
        self.games = []           # what gate.list_games() returns
        self.on_look = []         # callables run at each process listing, with the listing's number (1, 2, ...)
        self.looks = 0
        self.start_result = None  # what gate.start_game returns, or a callable it calls; while None, a start fails
        self.starts = []
        self.playset_at_start = None
        env = {"VIC3_USER_DATA": str(self.user), "VIC3_QA_BACKUPS": str(self.backups),
               "VIC3_BASE_GAME": str(self.base_game), "VIC3_MOD_DEPLOY_TARGET": str(self.deploy)}
        patches = [mock.patch.dict(os.environ, env),
                   mock.patch.object(gate, "list_games", side_effect=self._list_games),
                   mock.patch.object(gate, "sample_gpu", return_value=IDLE),
                   mock.patch.object(gate, "start_game", side_effect=self._start_game),
                   mock.patch.object(gate, "windows_path", side_effect=lambda path, *a, **k: windows(path)),
                   mock.patch.object(cli, "_sleep", lambda seconds: None)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def write_the_owners_files(self, playset=None):
        """The owner's folder: an autosave, the Continue pointer, a log, and the playset as the launcher writes
        it (a BOM, one line), all dated a day ago."""
        (self.user / "save games" / "autosave.v3").write_bytes(b"autosave")
        (self.user / "continue_game.json").write_text('{"title": "autosave"}')
        (self.user / "logs" / "debug.log").write_text("the owner's log\n")
        self.playset_bytes = b"\xef\xbb\xbf" + json.dumps(playset or self.owners_playset).encode("utf-8")
        self.playset.write_bytes(self.playset_bytes)
        day_ago = time.time() - 86400
        for rel in ("save games/autosave.v3", "continue_game.json", "logs/debug.log", PLAYSET):
            os.utime(self.user / rel, (day_ago, day_ago))

    def _list_games(self, *a, **k):
        """`self.games` is a listing, or a queue of listings whose last entry repeats."""
        self.looks += 1
        for hook in self.on_look:
            hook(self.looks)
        if self.games and isinstance(self.games[0], list):
            return list(self.games.pop(0) if len(self.games) > 1 else self.games[0])
        return list(self.games)

    def _start_game(self, exe, args, cwd, *a, **k):
        if self.start_result is None:
            raise UnexpectedStart(f"{exe} {args}")
        self.starts.append((exe, list(args), cwd))
        self.playset_at_start = self.playset.read_bytes() if self.playset.exists() else None
        return self.start_result() if callable(self.start_result) else self.start_result

    @staticmethod
    def game(pid=4242):
        when = dt.datetime.now(UTC) + dt.timedelta(seconds=1)
        return gate.ProcId(pid, when.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"))

    def run_cli(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
        return json.loads(out.getvalue()), code

    def launch(self, snap_id, *options):
        return self.run_cli("launch", snap_id, "--permission", "session grant", *options, "--", "-debug_mode")

    def take_snapshot(self) -> str:
        taken, code = self.run_cli("snapshot")
        self.assertEqual(code, 0, taken)
        return taken["id"]

    def armed_snapshot(self) -> snapshot.Snapshot:
        """A snapshot taken for a run, past `snapshot`'s refusal of an unfinished earlier one."""
        snap = snapshot.take(self.user, self.backups)
        snapshot.record(snap, "armed")
        return snap

    def tree(self):
        return sorted((str(p.relative_to(self.user)), p.stat().st_mtime_ns, p.read_bytes())
                      for p in self.user.rglob("*") if p.is_file())

    def the_snapshot(self):
        return snapshot.all_snapshots(self.backups)[-1]

    def journal(self):
        return snapshot.journal(self.the_snapshot())

    def events(self):
        return [e["event"] for e in self.journal()]

    def claim(self) -> Path:
        return self.the_snapshot().dir / cli.LAUNCH_CLAIM

    def age_the_claim(self):
        """Move the claim past the window in which a `launch` may still be on its way to its record."""
        old = time.time() - cli.LAUNCH_IN_FLIGHT_S - 30
        os.utime(self.claim(), (old, old))

    def written(self) -> dict:
        raw = self.playset.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "written back with a BOM")
        return json.loads(raw.decode("utf-8"))

    def enabled(self) -> list[str]:
        return [m["path"] for m in self.written()["enabledMods"]]

    def runs(self, out):
        return [(r["id"], r["held"], r["reason"]) for r in out["runs"]]

    def failed_start_after_the_write(self, *options) -> str:
        """snapshot, then a `launch` that writes the playset and whose start fails (its reply lost)."""
        snap_id = self.take_snapshot()

        def lost():
            raise gate.GateError("powershell.exe timed out after 60 s")

        self.start_result = lost
        out, code = self.launch(snap_id, *(options or ("--add-mod", OVERLAY)))
        self.assertEqual((code, out["refused"], out["id"]), (2, "start_unconfirmed", snap_id))
        self.assertIn(f"the playset this wrote into {PLAYSET} stays the run's until", out["detail"])
        self.start_result = None
        self.assertIn(OVERLAY, self.enabled())                  # the file stays as written
        self.assertEqual(self.events(), ["armed", "playset", "playset_written"])
        self.assertTrue(self.claim().exists())                  # and the snapshot stays claimed
        return snap_id

    def started_run(self, snap_id, *options, others=(), during=lambda: None) -> gate.ProcId:
        """`launch` with `options`, then `watch` over the game, seen twice (beside `others`) and then gone."""
        game = self.game()
        self.start_result = game
        out, code = self.launch(snap_id, *options)
        self.assertEqual(code, 0, out)
        self.start_result = None
        during()
        self.games = [[game], [game, *others], []]
        self.assertEqual(self.run_cli("watch", snap_id)[1], 0)
        self.games = []
        return game

    @contextlib.contextmanager
    def pinned_clock(self):
        """Inside, the backup drive's clock stands at the machine's time on entry, to the second (`_sleep` takes no
        time here), and yields that time. A run's write dated from it is judged against an exit on the same clock,
        whatever the machine's clock does: WSL steps it by seconds, and a step back between the write and the
        `game_exited` after it makes the write look later than the exit (#1693; test_game_qa_gate's naps_clock)."""
        at = dt.datetime.now(UTC).replace(microsecond=0)
        with mock.patch.object(snapshot, "_drive_clock", lambda folder: at):
            yield at

    @staticmethod
    def dated(path: Path, data: bytes, at: dt.datetime | None):
        """Write `data` to `path`, dated `at` (from `pinned_clock`) when one is given."""
        path.write_bytes(data)
        if at is not None:
            os.utime(path, (at.timestamp(), at.timestamp()))

    def is_the_owners_playset(self) -> bool:
        return self.playset.read_bytes() == self.playset_bytes

    # -- what launch writes ------------------------------------------------------

    def test_add_mod_appends_and_keeps_the_owners_entries(self):
        snap_id = self.take_snapshot()
        game = self.game()
        self.start_result = game
        out, code = self.launch(snap_id, "--add-mod", OVERLAY)
        self.assertEqual((code, out["pid"]), (0, game.pid))
        expected = dict(self.owners_playset, enabledMods=[*self.owners_playset["enabledMods"], {"path": OVERLAY}])
        self.assertEqual(self.written(), expected)
        self.assertEqual(list(self.written()), ["enabledMods", "disabledDLC", "enabledUGC"])   # every other key kept
        # UTF-8 without a BOM, indent 2: the form a live session proved the game reads (2026-11-10).
        self.assertEqual(self.playset.read_bytes(), json.dumps(expected, indent=2, ensure_ascii=False).encode("utf-8"))
        self.assertEqual(self.playset_at_start, self.playset.read_bytes())       # written before the start
        self.assertEqual([p.name for p in self.user.iterdir() if p.name.endswith(".tmp")], [])

    def test_mod_only_keeps_this_mod_and_the_added_ones(self):
        # The launcher's spelling of this mod's folder may differ in case and end in a separator; a folder whose
        # name only begins with this mod's is another mod.
        theirs = self.this_mod.upper() + "\\"
        self.write_the_owners_files(dict(self.owners_playset, enabledMods=[
            {"path": WORKSHOP + "3142463417"}, {"path": self.this_mod + "_old"}, {"path": theirs},
            {"path": WORKSHOP + "3312478537"}]))
        snap_id = self.take_snapshot()
        self.start_result = self.game()
        out, code = self.launch(snap_id, "--playset", "mod_only", "--add-mod", OVERLAY)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.enabled(), [theirs, OVERLAY])
        self.assertEqual((self.written()["disabledDLC"], self.written()["enabledUGC"]), ([], []))

    def test_mod_only_without_this_mod_in_the_playset_refuses_before_any_write(self):
        self.write_the_owners_files(dict(self.owners_playset, enabledMods=[
            {"path": WORKSHOP + "3142463417"}, {"path": self.this_mod + "_old"}]))
        snap_id = self.take_snapshot()
        before = self.tree()
        self.start_result = self.game()
        out, code = self.launch(snap_id, "--playset", "mod_only", "--add-mod", OVERLAY)
        self.assertEqual((code, out["refused"], out["id"]), (2, "mod_not_in_playset", snap_id))
        self.assertIn(self.this_mod, out["detail"])
        self.assertEqual((self.starts, self.events(), self.claim().exists()), ([], ["armed"], False))
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.launch(snap_id, "--add-mod", OVERLAY)[1], 0)   # refused before the claim

    def test_no_option_leaves_the_file_untouched(self):
        before = self.tree()
        for options in ((), ("--playset", "current")):
            with self.subTest(options=options):
                snap_id = self.take_snapshot()
                game = self.game()
                self.start_result = game
                out, code = self.launch(snap_id, *options)
                self.assertEqual(code, 0, out)
                self.assertNotIn("playset", out)
                self.assertEqual(self.events(), ["armed", "started"])
                self.assertEqual((self.playset.read_bytes(), self.playset.stat().st_mtime_ns),
                                 (self.playset_bytes, dict((r, t) for r, t, _ in before)[PLAYSET]))
                self.games = [[game], [game], []]
                self.assertEqual(self.run_cli("watch", snap_id)[1], 0)
                self.games = []
                self.assertEqual(self.run_cli("restore", snap_id)[1], 0)
                self.assertEqual(self.tree(), before)

    def test_an_add_mod_already_enabled_leaves_the_file_untouched(self):
        self.write_the_owners_files(dict(self.owners_playset, enabledMods=[
            *self.owners_playset["enabledMods"], {"path": OVERLAY.lower() + "\\"}]))
        before = self.tree()
        snap_id = self.take_snapshot()
        self.start_result = self.game()
        out, code = self.launch(snap_id, "--add-mod", OVERLAY, "--add-mod", OVERLAY)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.tree(), before)
        self.assertFalse(out["playset"]["written"])
        entry = [e for e in self.journal() if e["event"] == "playset"]
        self.assertEqual(len(entry), 1)
        self.assertNotIn("sha256", entry[0])                     # nothing written, so nothing to put back

    def test_an_add_mod_given_twice_is_added_once(self):
        snap_id = self.take_snapshot()
        self.start_result = self.game()
        self.assertEqual(self.launch(snap_id, "--add-mod", OVERLAY, "--add-mod", OVERLAY.upper())[1], 0)
        self.assertEqual(self.enabled()[-2:], [self.this_mod, OVERLAY])

    def test_the_journal_records_what_was_enabled(self):
        snap_id = self.take_snapshot()
        game = self.game()
        self.start_result = game
        out, code = self.launch(snap_id, "--playset", "mod_only", "--add-mod", OVERLAY)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.events(), ["armed", "playset", "playset_written", "started"])
        entry, written = self.journal()[1:3]
        self.assertEqual((entry["mode"], entry["enabled"], entry["sha256"]),
                         ("mod_only", [self.this_mod, OVERLAY], sha256(self.playset.read_bytes())))
        st = self.playset.stat()                                # as read back right after the rename
        self.assertEqual((written["size"], written["mtime_ns"]), (st.st_size, st.st_mtime_ns))
        self.assertEqual(out["playset"], {"mode": "mod_only", "enabled": [self.this_mod, OVERLAY], "written": True})

    # -- the owner's playset put back ------------------------------------------------

    def test_restore_puts_the_owners_playset_back(self):
        before = self.tree()
        snap_id = self.take_snapshot()
        game = self.game()
        self.start_result = game
        with self.pinned_clock() as at:         # the run's write is judged against its exit (#1693)
            self.assertEqual(self.launch(snap_id, "--playset", "mod_only", "--add-mod", OVERLAY)[1], 0)
            self.start_result = None
            self.dated(self.user / "continue_game.json", b'{"title": "the run"}', at)
            self.games = [[game], [game], []]
            self.assertEqual(self.run_cli("watch", snap_id)[1], 0)
            self.games = []
            out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"]), (0, False), out)
        self.assertEqual(sorted(out["restored"]), [PLAYSET, "continue_game.json"])
        self.assertEqual(self.playset.read_bytes(), self.playset_bytes)
        self.assertEqual(self.tree(), before)

    def test_a_failed_start_after_the_playset_write_is_put_back(self):
        # The plan's scenario 2: `launch` wrote the playset and the start failed. Nothing recorded a start, so the
        # rule for a never-started snapshot would hold the changed playset (`no_reference_time`) and leave it
        # altered until the owner resolved the hold; it is `launch`'s own write, known by its hash, and goes back.
        before = self.tree()
        for verb in ("recover", "restore"):
            with self.subTest(verb=verb):
                snap_id = self.failed_start_after_the_write()
                argv = (verb,) if verb == "recover" else (verb, snap_id)
                out, code = self.run_cli(*argv)                 # within the launch's window: no verdict
                self.assertEqual(code, 2)
                self.assertEqual(self.events(), ["armed", "playset", "playset_written"])
                self.age_the_claim()
                out, code = self.run_cli(*argv)
                result = out["runs"][0] if verb == "recover" else out
                self.assertEqual((code, result["held"], result["reason"], result["restored"]),
                                 (0, False, "", [PLAYSET]))
                self.assertEqual(self.events(), ["armed", "playset", "playset_written", "playset_restored", "restored"])
                self.assertEqual(self.playset.read_bytes(), self.playset_bytes)
                self.assertEqual(self.tree(), before)

    def without_the_playset(self, tree):
        return [entry for entry in tree if entry[0] != PLAYSET]

    def test_a_failed_start_with_another_change_since_holds_the_rest_and_puts_the_playset_back(self):
        # Break-it review, Important 1, replay 2: the owner played meanwhile, and with no start recorded nothing
        # can be judged, so the snapshot holds. The playset is `launch`'s own write, provably (its hash), so it
        # goes back; everything else is held exactly as before.
        for verb, autosave in (("recover", "autosave.v3"), ("restore", "autosave.v3"), ("recover", "autosave_1.v3")):
            with self.subTest(verb=verb, autosave=autosave):      # a changed autosave, then a new one
                self.write_the_owners_files()
                snap_id = self.failed_start_after_the_write()
                (self.user / "save games" / autosave).write_bytes(b"the owner played since")
                self.age_the_claim()
                before = self.tree()
                out, code = self.run_cli(*((verb,) if verb == "recover" else (verb, snap_id)))
                result = out["runs"][0] if verb == "recover" else out
                self.assertEqual((code, result["held"], result["reason"], result["playset_restored"]),
                                 (2, True, "no_reference_time", True))
                self.assertTrue(self.is_the_owners_playset())
                self.assertEqual(self.without_the_playset(self.tree()), self.without_the_playset(before))
                self.assertEqual(self.events(), ["armed", "playset", "playset_written", "playset_restored", "held"])
                self.take_snapshot()                                        # the next snapshot is not refused
                self.assertEqual(self.run_cli("recover")[1], 0)

    def test_a_started_run_held_for_another_game_gets_the_owners_playset_back(self):
        # Break-it review, Important 1, replay 1: `watch` saw another game, so the run holds (`other_game_ran`);
        # the run's playset was left live, and the next snapshot recorded it as the owner's.
        for verb in ("restore", "recover"):
            with self.subTest(verb=verb):
                self.write_the_owners_files()
                snap_id = self.take_snapshot()
                self.started_run(snap_id, "--playset", "mod_only", "--add-mod", OVERLAY, others=[self.game(pid=7777)],
                                 during=lambda: (self.user / "continue_game.json").write_text('{"title": "run"}'))
                before = self.tree()
                out, code = self.run_cli(*((verb,) if verb == "recover" else (verb, snap_id)))
                result = out["runs"][0] if verb == "recover" else out
                self.assertEqual((code, result["held"], result["reason"], result["playset_restored"]),
                                 (2, True, "other_game_ran", True))
                self.assertTrue(self.is_the_owners_playset())
                self.assertEqual(self.without_the_playset(self.tree()), self.without_the_playset(before))
                self.assertEqual((self.user / "continue_game.json").read_text(), '{"title": "run"}')   # held
                self.assertEqual(self.events()[-2:], ["playset_restored", "held"])
                taken, code = self.run_cli("snapshot")
                self.assertEqual(code, 0, taken)
                self.assertEqual(self.the_snapshot().files[PLAYSET].sha256, sha256(self.playset_bytes))
                self.assertEqual(self.run_cli("recover")[1], 0)

    def test_a_failed_start_whose_game_wrote_only_logs_gets_its_playset_back_and_keeps_the_logs(self):
        # The reply was lost, the game ran unrecorded and quit at the menu: only `logs/` and the playset changed.
        # With no start recorded the logs are whoever's, and are left as they are; the playset goes back.
        snap_id = self.failed_start_after_the_write()
        (self.user / "logs" / "debug.log").write_text("the unrecorded game's log\n")
        self.assertEqual(self.run_cli("recover")[0]["runs"], [{"restored": [], "removed": [], "held": False,
                                                              "reason": "launch_in_flight", "id": snap_id}])
        (self.user / "logs" / "error.log").write_text("its new error log\n")
        self.age_the_claim()
        logs_before = sorted((p.name, p.read_bytes()) for p in (self.user / "logs").iterdir())
        out, code = self.run_cli("recover")
        self.assertEqual((code, out["runs"][0]["held"], out["runs"][0]["restored"]), (0, False, [PLAYSET]))
        self.assertEqual(self.playset.read_bytes(), self.playset_bytes)
        self.assertEqual(sorted((p.name, p.read_bytes()) for p in (self.user / "logs").iterdir()), logs_before)
        self.assertEqual(self.events(), ["armed", "playset", "playset_written", "playset_restored", "restored"])
        self.assertFalse((self.the_snapshot().dir / "run_logs").exists())

    def test_a_playset_changed_since_the_failed_start_is_held(self):
        # The owner's launcher wrote their playset again after the failed start: those bytes are not `launch`'s.
        snap_id = self.failed_start_after_the_write()
        self.playset.write_bytes(json.dumps({"enabledMods": [], "disabledDLC": []}).encode("utf-8"))
        self.age_the_claim()
        before = self.tree()
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "no_reference_time"))
        self.assertEqual(self.tree(), before)

    def test_a_failed_start_held_beside_a_running_game_gets_its_playset_back_once_none_runs(self):
        # The start's reply was lost but the game did start: it may be anyone's now, so nothing is put back. Once
        # no game runs, `restore` judges the held snapshot again, and the playset is still `launch`'s own write.
        original = self.tree()
        snap_id = self.failed_start_after_the_write()
        self.age_the_claim()
        self.games = [self.game(pid=5555)]
        before = self.tree()
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["reason"], out["playset_left"]), (2, True, "other_game_running", True))
        self.assertIn(f"restore {snap_id}", out["playset_detail"])
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.events(), ["armed", "playset", "playset_written", "held"])
        self.games = []
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["restored"], out["playset_restored"]), (0, False, [PLAYSET], True))
        self.assertEqual(self.events(), ["armed", "playset", "playset_written", "held", "playset_restored", "restored"])
        self.assertEqual(self.tree(), original)

    def test_a_playset_left_beside_a_game_blocks_the_next_snapshot_and_launch_until_restore(self):
        # Break-it review, Important 1, replay 3 (its run 3e): `recover` held the failed start beside a game and
        # never looks at a held snapshot again; `snapshot` then recorded `launch`'s write as the owner's playset,
        # and a later `launch` with no option ran the game with a playset the owner never chose.
        snap_id = self.failed_start_after_the_write()
        self.age_the_claim()
        self.games = [self.game(pid=5555)]
        out, code = self.run_cli("recover")
        run = out["runs"][0]
        self.assertEqual((code, run["held"], run["reason"], run["playset_left"]), (2, True, "other_game_running", True))
        self.games = []
        self.assertEqual(self.run_cli("recover"), ({"runs": []}, 0))      # a held snapshot is not revisited
        (self.user / "save games" / "autosave.v3").write_bytes(b"the owner's game, which was running")
        before = self.tree()
        out, code = self.run_cli("snapshot")
        self.assertEqual((code, out["refused"], out["snapshot"]), (2, "playset_not_restored", snap_id))
        self.assertIn(f"restore {snap_id}", out["detail"])
        self.assertEqual(len(snapshot.all_snapshots(self.backups)), 1)
        laundered = self.armed_snapshot()                      # one taken past that refusal
        self.starts.clear()                                     # (the failed start's)
        self.start_result = self.game()
        for options in ((), ("--add-mod", OVERLAY)):
            with self.subTest(options=options):
                out, code = self.launch(laundered.id, *options)
                self.assertEqual((code, out["refused"], out["snapshot"]), (2, "playset_not_restored", snap_id))
        self.assertEqual((self.starts, (laundered.dir / cli.LAUNCH_CLAIM).exists()), ([], False))
        self.assertEqual(self.tree(), before)
        snapshot.record(laundered, "restored")                  # out of the way, as `recover` would leave it
        out, code = self.run_cli("restore", snap_id)            # no game now: the playset back, the rest held
        self.assertEqual((code, out["held"], out["reason"], out["playset_restored"]),
                         (2, True, "no_reference_time", True))
        self.assertTrue(self.is_the_owners_playset())
        self.assertEqual(self.without_the_playset(self.tree()), self.without_the_playset(before))
        self.assertEqual(self.run_cli("snapshot")[1], 0)

    def test_a_started_run_held_beside_a_running_game_leaves_the_playset_until_restore(self):
        snap_id = self.take_snapshot()
        self.started_run(snap_id, "--add-mod", OVERLAY)
        self.games = [self.game(pid=5555)]                      # the owner started their own game
        before = self.tree()
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["reason"], out["playset_left"]), (2, "other_game_running", True))
        self.assertEqual(self.tree(), before)
        self.games = []
        self.assertEqual(self.run_cli("snapshot")[0]["refused"], "playset_not_restored")
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["playset_restored"]), (0, False, True))
        self.assertTrue(self.is_the_owners_playset())
        self.assertEqual(self.run_cli("snapshot")[1], 0)

    def test_restore_of_an_older_snapshot_never_puts_its_playset_over_a_newer_one(self):
        # Break-it review, Important 2 (runs m1, m1b): with `mod_only`, two snapshots' writes are the same bytes even
        # though the owner changed their other mods in between, so the put-back for the older snapshot matched the
        # newer one's write and put the older playset back over the owner's current one.
        first = self.failed_start_after_the_write("--playset", "mod_only", "--add-mod", OVERLAY)
        self.age_the_claim()
        self.assertEqual(self.run_cli("recover")[1], 0)
        newer = dict(self.owners_playset, enabledMods=[{"path": WORKSHOP + "999"}, *self.owners_playset["enabledMods"]])
        self.write_the_owners_files(newer)
        second = self.failed_start_after_the_write("--playset", "mod_only", "--add-mod", OVERLAY)
        hashes = [e["sha256"] for s in snapshot.all_snapshots(self.backups) for e in snapshot.journal(s)
                  if e["event"] == "playset"]
        self.assertEqual(len(set(hashes)), 1)                   # the two writes coincide
        launchs_write = self.playset.read_bytes()
        out, code = self.run_cli("restore", first)
        self.assertNotIn("playset_restored", out)
        self.assertEqual(self.playset.read_bytes(), launchs_write)            # not the first snapshot's playset
        self.age_the_claim()
        (self.user / "save games" / "autosave.v3").write_bytes(b"the owner played")      # m1: the second holds
        out, code = self.run_cli("restore", second)
        self.assertEqual((code, out["held"], out["playset_restored"]), (2, True, True))
        self.assertTrue(self.is_the_owners_playset())                         # the newer playset, the owner's now
        self.assertEqual(self.run_cli("restore", first)[0].get("playset_restored"), None)
        self.assertTrue(self.is_the_owners_playset())

    def test_restore_of_the_newer_snapshot_puts_its_own_playset_back(self):
        # m1b: as above, and the second restores cleanly.
        first = self.failed_start_after_the_write("--playset", "mod_only", "--add-mod", OVERLAY)
        self.age_the_claim()
        self.assertEqual(self.run_cli("recover")[1], 0)
        self.write_the_owners_files(dict(self.owners_playset,
                                         enabledMods=[{"path": WORKSHOP + "999"}, *self.owners_playset["enabledMods"]]))
        second = self.failed_start_after_the_write("--playset", "mod_only", "--add-mod", OVERLAY)
        self.run_cli("restore", first)
        self.age_the_claim()
        out, code = self.run_cli("restore", second)
        self.assertEqual((code, out["held"], out["restored"]), (0, False, [PLAYSET]))
        self.assertTrue(self.is_the_owners_playset())

    def test_no_snapshot_or_launch_is_refused_after_clean_runs(self):
        for _ in range(2):
            snap_id = self.take_snapshot()
            self.started_run(snap_id, "--playset", "mod_only", "--add-mod", OVERLAY)
            self.assertEqual(self.run_cli("restore", snap_id)[1], 0)
        self.failed_start_after_the_write()
        self.age_the_claim()
        self.assertEqual(self.run_cli("recover")[1], 0)
        snap_id = self.take_snapshot()
        self.start_result = self.game()
        self.assertEqual(self.launch(snap_id)[1], 0)

    def launcher_rewrites_during_the_run(self, snap_id, at: dt.datetime | None = None) -> bytes:
        """A run with --add-mod during which the owner's launcher writes the playset again (dated `at` when given);
        returns `launch`'s bytes. Restore then finds the launcher's bytes, not `launch`'s, and puts no playset back
        of its own."""
        launchs = {}

        def the_launcher_writes():
            launchs["bytes"] = self.playset.read_bytes()
            self.dated(self.playset, json.dumps({"enabledMods": [{"path": WORKSHOP + "1"}]}).encode("utf-8"), at)

        self.started_run(snap_id, "--add-mod", OVERLAY, during=the_launcher_writes)
        return launchs["bytes"]

    def the_owner_chooses(self, data: bytes):
        """The owner's launcher writes `data`, an hour after the run."""
        self.playset.write_bytes(data)
        later = time.time() + 3600
        os.utime(self.playset, (later, later))

    def test_a_restored_snapshot_no_longer_vouches_for_launchs_bytes(self):
        # Ruling on round 1's concern 1: the launcher rewrote the playset during the run, so `restore` put the
        # snapshot's copy back with no `playset_restored`. The owner later chooses a playset that is byte for byte
        # `launch`'s write. `restored` answers the entry: nothing refuses, and `restore <id>` leaves their choice.
        snap_id = self.take_snapshot()
        with self.pinned_clock() as at:         # the launcher's write during the run is judged against its exit (#1693)
            launchs = self.launcher_rewrites_during_the_run(snap_id, at)
            out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], "playset_restored" in out), (0, False, False), out)
        self.assertTrue(self.is_the_owners_playset())
        self.the_owner_chooses(launchs)
        out, code = self.run_cli("restore", snap_id)            # judged again: their later write is held, kept
        self.assertEqual((code, out["held"], out["reason"], "playset_restored" in out),
                         (2, True, "modified_after_exit", False))
        self.assertEqual(self.playset.read_bytes(), launchs)
        taken, code = self.run_cli("snapshot")
        self.assertEqual(code, 0, taken)
        self.start_result = self.game()
        out, code = self.launch(taken["id"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.playset.read_bytes(), launchs)

    def test_a_held_snapshot_blocks_while_launchs_own_write_is_live(self):
        # The other side of that ruling: a held snapshot has no `restored` after its entry, so while `launch`'s
        # write is still in the folder (its bytes, size and time as read back), `snapshot` and `launch` refuse.
        snap_id = self.take_snapshot()
        self.started_run(snap_id, "--add-mod", OVERLAY)
        self.games = [self.game(pid=5555)]
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["reason"], out["playset_left"]), (2, "other_game_running", True))
        self.games = []
        out, code = self.run_cli("snapshot")
        self.assertEqual((code, out["refused"], out["snapshot"]), (2, "playset_not_restored", snap_id))
        laundered = self.armed_snapshot()
        self.start_result = self.game()
        out, code = self.launch(laundered.id)
        self.assertEqual((code, out["refused"], out["snapshot"]), (2, "playset_not_restored", snap_id))

    def same_bytes_saved_again_on_a_held_snapshot(self, launchs_bytes) -> str:
        """Hold the run beside a game, then the owner's launcher saves `launchs_bytes()`'s bytes an hour later."""
        snap_id = self.take_snapshot()
        launchs = launchs_bytes(snap_id)
        self.games = [self.game(pid=5555)]
        self.assertEqual(self.run_cli("restore", snap_id)[0]["reason"], "other_game_running")
        self.games = []
        self.the_owner_chooses(launchs)
        return snap_id

    def assert_the_owners_now(self, snap_id):
        """The live playset, whatever its bytes, is the owner's: nothing refuses and nothing puts it back."""
        theirs = self.playset.read_bytes()
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], "playset_restored" in out), (2, True, False))
        self.assertEqual(self.playset.read_bytes(), theirs)
        taken, code = self.run_cli("snapshot")
        self.assertEqual(code, 0, taken)
        self.start_result = self.game()
        out, code = self.launch(taken["id"])
        self.assertEqual(code, 0, out)
        self.assertEqual(self.playset.read_bytes(), theirs)

    def launchs_own_write(self, snap_id) -> bytes:
        self.started_run(snap_id, "--add-mod", OVERLAY)
        return self.playset.read_bytes()

    def test_launchs_write_saved_again_by_the_owner_is_theirs(self):
        # Re-review hardening 2: a held, unanswered entry matched any later write of identical bytes, naming the
        # snapshot for good, and once newer snapshots were pruned its copy could go back over the owner's choice.
        # The size and time `launch` read back right after its rename are journaled; the same bytes saved again
        # carry a new time, and are the owner's.
        self.assert_the_owners_now(self.same_bytes_saved_again_on_a_held_snapshot(self.launchs_own_write))

    def test_a_later_playset_equal_to_launchs_bytes_is_the_owners_on_a_held_snapshot(self):
        # The launcher rewrote the playset during the run, the run held, and the owner later chose `launch`'s bytes.
        self.assert_the_owners_now(self.same_bytes_saved_again_on_a_held_snapshot(self.launcher_rewrites_during_the_run))

    def test_a_write_whose_size_and_time_were_never_journaled_falls_back_to_its_hash(self):
        # A kill between the rename and the read-back's journal line leaves no `playset_written`: the hash decides.
        snap_id = self.take_snapshot()
        self.start_result = self.game()
        with mock.patch.object(cli, "_record_written", side_effect=Killed()), self.assertRaises(Killed):
            self.launch(snap_id, "--add-mod", OVERLAY)
        self.assertEqual((self.starts, self.events()), ([], ["armed", "playset"]))
        self.assertIn(OVERLAY, self.enabled())
        self.age_the_claim()
        other = self.armed_snapshot()
        out, code = self.launch(other.id)
        self.assertEqual((code, out["refused"], out["snapshot"]), (2, "playset_not_restored", snap_id))
        snapshot.record(other, "restored")
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["restored"], out["playset_restored"]), (0, False, [PLAYSET], True))
        self.assertTrue(self.is_the_owners_playset())

    def test_a_written_playset_the_journal_cannot_describe_refuses_before_the_start(self):
        snap_id = self.take_snapshot()
        self.start_result = self.game()
        record = snapshot.record

        def failing(snap, event, *a, **k):
            if event == "playset_written":
                raise OSError(28, "No space left on device")
            return record(snap, event, *a, **k)

        with mock.patch.object(snapshot, "record", side_effect=failing):
            out, code = self.launch(snap_id, "--add-mod", OVERLAY)
        self.assertEqual((code, out["refused"], self.starts), (2, "playset_unwritable", []))
        self.assertIn("stays claimed", out["detail"])
        self.age_the_claim()
        out, code = self.run_cli("restore", snap_id)               # by its hash alone
        self.assertEqual((code, out["playset_restored"]), (0, True))
        self.assertTrue(self.is_the_owners_playset())

    def test_a_playset_changed_just_before_the_put_back_is_left(self):
        # Re-review hardening 1: the last look before the put-back's rename compared size and time only, so a
        # same-size write that kept the old time was overwritten. The file is hashed again just before the rename.
        snap_id = self.failed_start_after_the_write()
        self.age_the_claim()
        stage = restore._stage
        sneaked = {}

        def stage_then_the_launcher_writes(source, entry, target):
            temp = stage(source, entry, target)
            st = target.stat()
            sneaked["bytes"] = target.read_bytes().replace(b"te_qa_overlay", b"te_qa_overlaz")   # same size
            target.write_bytes(sneaked["bytes"])
            os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns))                              # same time
            return temp

        with mock.patch.object(restore, "_stage", side_effect=stage_then_the_launcher_writes):
            out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["reason"], "playset_restored" in out),
                         (2, True, "no_reference_time", False))
        self.assertEqual(self.playset.read_bytes(), sneaked["bytes"])
        self.assertEqual([p.name for p in self.user.iterdir() if p.name.endswith(".tmp")], [])

    def test_a_hold_after_a_killed_write_sweeps_its_temp(self):
        # A `launch` killed between its temp write and the rename leaves the temp, which is the harness's own.
        snap_id = self.take_snapshot()
        self.start_result = self.game()

        def killed(snap, user, data):
            (user / (PLAYSET + ".te_qa_restore.tmp")).write_bytes(data)
            raise gate.GateError("killed")                      # stands in for the process dying here

        with mock.patch.object(cli, "_write_playset", killed), contextlib.suppress(Exception):
            self.launch(snap_id, "--add-mod", OVERLAY)
        (self.user / "save games" / "autosave.v3").write_bytes(b"the owner played")
        self.age_the_claim()
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"]), (2, True))
        self.assertEqual([p.name for p in self.user.iterdir() if p.name.endswith(".tmp")], [])
        self.assertTrue(self.is_the_owners_playset())

    def test_a_restore_that_fails_after_the_put_back_says_the_playset_went_back(self):
        snap_id = self.failed_start_after_the_write()
        (self.user / "continue_game.json").unlink()            # restore puts a missing file back, from the store
        entry = self.the_snapshot().files["continue_game.json"]
        (self.backups / "store" / entry.sha256[:2] / entry.sha256).unlink()
        self.age_the_claim()
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["refused"], out["playset_restored"]), (2, "error", True))
        self.assertTrue(self.is_the_owners_playset())
        out, code = self.run_cli("recover")
        self.assertEqual(code, 2)
        self.assertTrue(out["runs"][0]["reason"].startswith("error: "))
        self.assertNotIn("playset_restored", out["runs"][0])    # it went back the first time

    def test_the_failure_details_say_the_playset_stays_the_runs(self):
        snap_id = self.take_snapshot()
        self.start_result = self.game()
        record = snapshot.record

        def failing(snap, event, *a, **k):
            if event == "started":
                raise OSError("the backup drive went away")
            return record(snap, event, *a, **k)

        with mock.patch.object(snapshot, "record", side_effect=failing):
            out, code = self.launch(snap_id, "--add-mod", OVERLAY)
        self.assertEqual((code, out["refused"]), (2, "not_recorded"))
        self.assertIn(f"the playset this wrote into {PLAYSET} stays the run's until", out["detail"])

    # -- refusals ---------------------------------------------------------------------

    def test_an_unwritable_playset_refuses_and_starts_nothing(self):
        before = self.tree()
        snap_id = self.take_snapshot()
        self.start_result = self.game()
        with mock.patch("os.replace", side_effect=PermissionError(13, "Permission denied")):
            out, code = self.launch(snap_id, "--add-mod", OVERLAY)
        self.assertEqual((code, out["refused"], out["id"]), (2, "playset_unwritable", snap_id))
        self.assertIn("stays claimed", out["detail"])
        self.assertEqual(self.starts, [])
        self.assertEqual(self.tree(), before)                    # no temp file left either
        self.assertTrue(self.claim().exists())
        self.assertEqual(self.launch(snap_id, "--add-mod", OVERLAY)[0]["refused"], "already_started")
        self.age_the_claim()
        out, code = self.run_cli("recover")
        self.assertEqual((code, self.runs(out)), (0, [(snap_id, False, "")]))
        self.assertEqual(self.tree(), before)

    def test_a_playset_entry_the_journal_cannot_take_writes_nothing(self):
        # The entry goes in before the file is written: a write no entry vouches for would be held.
        before = self.tree()
        snap_id = self.take_snapshot()
        self.start_result = self.game()
        record = snapshot.record

        def failing(snap, event, *a, **k):
            if event == "playset":
                raise OSError(28, "No space left on device")
            return record(snap, event, *a, **k)

        with mock.patch.object(snapshot, "record", side_effect=failing):
            out, code = self.launch(snap_id, "--add-mod", OVERLAY)
        self.assertEqual((code, out["refused"]), (2, "playset_unwritable"))
        self.assertEqual((self.starts, self.events(), self.tree()), ([], ["armed"], before))

    def test_a_playset_changed_after_it_was_read_is_not_written_over(self):
        # The lock keeps other sessions out, not the owner's launcher: it may write the file during the last look.
        snap_id = self.take_snapshot()
        launcher = json.dumps({"enabledMods": [{"path": WORKSHOP + "1"}]}).encode("utf-8")

        def the_launcher_writes(look):
            if look == 2:                                       # launch's last listing, after it read the file
                self.playset.write_bytes(launcher)

        self.on_look = [the_launcher_writes]
        self.looks = 0
        self.start_result = self.game()
        out, code = self.launch(snap_id, "--add-mod", OVERLAY)
        self.assertEqual((code, out["refused"]), (2, "playset_unwritable"))
        self.assertEqual((self.starts, self.playset.read_bytes()), ([], launcher))
        self.assertEqual(self.events(), ["armed", "playset"])   # an entry for a write that never happened is harmless
        self.assertEqual([p.name for p in self.user.iterdir() if p.name.endswith(".tmp")], [])

    def test_a_missing_or_unreadable_playset_refuses_before_the_claim(self):
        cases = {"missing": None, "not JSON": b'{"enabledMods": [', "a list": b"[]",
                 "no enabledMods": b'{"disabledDLC": []}', "enabledMods not a list": b'{"enabledMods": {}}',
                 "an entry without a path": b'{"enabledMods": [{"name": "x"}]}',
                 "a path that is not text": b'{"enabledMods": [{"path": 7}]}',
                 "nested too deep to parse": b"[" * 200000, "UTF-16": '{"enabledMods": []}'.encode("utf-16"),
                 "null": b"null"}
        for case, content in cases.items():
            with self.subTest(case=case):
                if content is None:
                    self.playset.unlink(missing_ok=True)
                else:
                    self.playset.write_bytes(content)
                snap = self.armed_snapshot()
                before = self.tree()
                self.start_result = self.game()
                out, code = self.launch(snap.id, "--add-mod", OVERLAY)
                self.assertEqual((code, out["refused"], out["id"]), (2, "playset_unwritable", snap.id))
                self.assertEqual((self.starts, self.tree()), ([], before))
                self.assertFalse((snap.dir / cli.LAUNCH_CLAIM).exists())

    def test_a_bad_add_mod_path_refuses_before_the_claim(self):
        snap_id = self.take_snapshot()
        before = self.tree()
        self.start_result = self.game()
        for path in ("", "mod\\te_qa_overlay", "/home/owner/te_qa_overlay", "C:", "C:\\mod\x00x", "C:\\mod\n",
                     "C:\\\udcff"):
            with self.subTest(path=path):
                out, code = self.launch(snap_id, "--add-mod", path)
                self.assertEqual((code, out["refused"], out["id"]), (2, "bad_argument", snap_id))
        self.assertEqual((self.starts, self.events(), self.claim().exists()), ([], ["armed"], False))
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.launch(snap_id, "--add-mod", "\\\\wsl.localhost\\Ubuntu\\home\\overlay")[1], 0)

    def test_a_lone_surrogate_in_the_owners_playset_cannot_break_the_reply(self):
        # Break-it review, minor: the owner's file may spell a lone surrogate as an escape; a reply that names the
        # enabled mods then crashed the final print on a UTF-8 stdout.
        self.playset.write_bytes(b'{"enabledMods": [{"path": "C:\\\\a\\ud800"}]}')
        snap = self.armed_snapshot()
        self.start_result = self.game()
        for options in (("--playset", "mod_only"), ("--add-mod", OVERLAY)):
            with self.subTest(options=options):
                raw = io.BytesIO()
                stdout = io.TextIOWrapper(raw, encoding="utf-8", errors="strict")
                with contextlib.redirect_stdout(stdout):
                    code = cli.main(["launch", snap.id, "--permission", "session grant", *options, "--", "-x"])
                stdout.flush()
                out = json.loads(raw.getvalue().decode("ascii"))
                self.assertEqual(code, 2)
                self.assertIn(out["refused"], ("mod_not_in_playset", "playset_unwritable"))
        self.assertEqual(self.starts, [])


if __name__ == "__main__":
    unittest.main()
