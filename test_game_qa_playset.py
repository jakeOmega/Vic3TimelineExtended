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
from game_qa import gate, snapshot

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
        self.assertIn(f"after the claim: it puts back the owner's {PLAYSET}", out["detail"])
        self.start_result = None
        self.assertIn(OVERLAY, self.enabled())                  # the file stays as written
        self.assertEqual(self.events(), ["armed", "playset"])
        self.assertTrue(self.claim().exists())                  # and the snapshot stays claimed
        return snap_id

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
        self.assertEqual(self.events(), ["armed", "playset", "started"])
        entry = self.journal()[1]
        self.assertEqual((entry["mode"], entry["enabled"], entry["sha256"]),
                         ("mod_only", [self.this_mod, OVERLAY], sha256(self.playset.read_bytes())))
        self.assertEqual(out["playset"], {"mode": "mod_only", "enabled": [self.this_mod, OVERLAY], "written": True})

    # -- the owner's playset put back ------------------------------------------------

    def test_restore_puts_the_owners_playset_back(self):
        before = self.tree()
        snap_id = self.take_snapshot()
        game = self.game()
        self.start_result = game
        self.assertEqual(self.launch(snap_id, "--playset", "mod_only", "--add-mod", OVERLAY)[1], 0)
        self.start_result = None
        (self.user / "continue_game.json").write_text('{"title": "the run"}')
        self.games = [[game], [game], []]
        self.assertEqual(self.run_cli("watch", snap_id)[1], 0)
        self.games = []
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"]), (0, False))
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
                self.assertEqual(self.events(), ["armed", "playset"])
                self.age_the_claim()
                out, code = self.run_cli(*argv)
                result = out["runs"][0] if verb == "recover" else out
                self.assertEqual((code, result["held"], result["reason"], result["restored"]),
                                 (0, False, "", [PLAYSET]))
                self.assertEqual(self.events(), ["armed", "playset", "playset_restored", "restored"])
                self.assertEqual(self.playset.read_bytes(), self.playset_bytes)
                self.assertEqual(self.tree(), before)

    def test_a_failed_start_with_another_change_since_holds_and_changes_nothing(self):
        # The owner played meanwhile: the autosave is theirs, and with no start recorded nothing can be judged.
        # Even the playset `launch` wrote is left as it is: a hold changes nothing.
        for verb in ("recover", "restore"):
            with self.subTest(verb=verb):
                self.write_the_owners_files()
                snap_id = self.failed_start_after_the_write()
                (self.user / "save games" / "autosave.v3").write_bytes(b"the owner played since")
                self.age_the_claim()
                before = self.tree()
                out, code = self.run_cli(*((verb,) if verb == "recover" else (verb, snap_id)))
                result = out["runs"][0] if verb == "recover" else out
                self.assertEqual((code, result["held"], result["reason"]), (2, True, "no_reference_time"))
                self.assertEqual(self.tree(), before)
                self.assertEqual(self.events(), ["armed", "playset", "held"])

    def test_a_playset_changed_since_the_failed_start_is_held(self):
        # The owner's launcher wrote their playset again after the failed start: those bytes are not `launch`'s.
        snap_id = self.failed_start_after_the_write()
        self.playset.write_bytes(json.dumps({"enabledMods": [], "disabledDLC": []}).encode("utf-8"))
        self.age_the_claim()
        before = self.tree()
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "no_reference_time"))
        self.assertEqual(self.tree(), before)

    def test_a_failed_start_whose_game_is_running_holds_and_changes_nothing(self):
        # The start's reply was lost but the game did start: it may be anyone's now, so nothing is put back.
        snap_id = self.failed_start_after_the_write()
        self.age_the_claim()
        self.games = [self.game(pid=5555)]
        before = self.tree()
        out, code = self.run_cli("restore", snap_id)
        self.assertEqual((code, out["held"], out["reason"]), (2, True, "other_game_running"))
        self.assertEqual(self.tree(), before)
        self.assertNotIn("playset_restored", self.events())

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
                 "a path that is not text": b'{"enabledMods": [{"path": 7}]}'}
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


if __name__ == "__main__":
    unittest.main()
