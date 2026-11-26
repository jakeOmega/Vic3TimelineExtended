"""The capture verbs (#2056): `start --capture`, `view`, `crop`, `hover` against the fake game, and `capture`'s run
of a manifest against a fake session.

Live, 2026-11-26 on a copy of the owner's June 2043 save (run 20261126T040928Z): the console took every command with
its edit line at alpha 0, `click --console` gave the keyboard back, the error counter hid while te_qa_capture was set
and came back when it was cleared, `panel:budget:te_banking`, `panel:military:te_nuclear`, `panel:society:te_ch`,
`panel:diplomatic_overview:te_un` and `market:te_global_warming` each opened the right tab, the Timeline Extended
window opened by its keys as a side panel and full screen, and a hover opened a tooltip that a `read` afterwards did
not disturb. An animated glow behind the Security Council's flag kept two shots of the UN tab 0.013% apart, which is
why `crop --settle` accepts CROP_SETTLE_SHARE.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts" / "image_pipeline"))
import guide_shots  # noqa: E402
import test_game_qa_session as tgs  # noqa: E402
from game_qa import capture, capture_gui, fakes, overlay, pixels, session  # noqa: E402
from game_qa.helper import HelperError  # noqa: E402

CONSOLE = (
    "template ConsoleBackground\n{\n\tusing = clickthrough_blocker\n\n\tmodify_texture = {\n\t\tusing = bg_tiling_pattern\n"
    "\t\talpha = 0.065\n\t}\n}\n\ntemplate console_frame\n{\n\ttexture = \"frame.dds\"\n}\n\n"
    "flowcontainer = {\n\tname = \"console_window\"\n\talwaystransparent = no\n\tscissor = no\n\tlayer = confirmation\n"
    "\tusing = clickthrough_blocker\n\n"
    "\tflowcontainer = {\n\t\tdirection = vertical\n\t\tspacing = 4\n\t\tbackground = {\n\t\t\tusing = ConsoleBackground\n"
    "\t\t}\n\t\tscrollarea = {\n\t\t\tname = \"console_output_scrollarea\"\n\t\t}\n"
    "\t\teditbox = {\n\t\t\tbackground = {\n\t\t\t\tusing = ConsoleEditbg\n\t\t\t\tmargin = { 4 0 }\n\t\t\t}\n"
    "\t\t\tname = \"console_edit\"\n\t\t}\n\t\tflowcontainer = {\n\t\t\tname = \"toolbars_window\"\n\t\t}\n\t}\n}\n"
)
ERROR_DEER = "widget = {\n\tname = \"error_deer\"\n\tvisible = \"[InDebugMode]\"\n\tlayer = layer_error_deer\n}\n"


def install_game_files(base_game: Path) -> None:
    gui = Path(base_game) / "game" / "gui"
    gui.mkdir(parents=True, exist_ok=True)
    (gui / "console.gui").write_bytes(capture_gui.BOM + CONSOLE.encode())
    (gui / "error_deer.gui").write_bytes(ERROR_DEER.encode())


def frame(width: int, height: int, colour=(10, 20, 30), spot: tuple | None = None) -> tuple[int, int, bytes]:
    """A flat image, with one pixel at `spot` ((x, y, colour)) painted."""
    px = bytearray(bytes(colour) * (width * height))
    if spot is not None:
        x, y, c = spot
        px[(y * width + x) * 3:(y * width + x) * 3 + 3] = bytes(c)
    return width, height, bytes(px)


class StartCaptureTest(tgs.SessionTestCase):
    def test_the_overlay_carries_the_capture_files_and_the_reply_names_them(self):
        install_game_files(self.paths.base_game)
        reply = self.start(capture=True)
        self.assertEqual(reply["capture"]["files"], [capture_gui.CONSOLE_FILE, capture_gui.ERROR_DEER_FILE])
        self.assertEqual(reply["capture"]["key"], capture_gui.CAPTURE_KEY)
        ov = self.paths.overlay_dir
        console = (ov / capture_gui.CONSOLE_FILE).read_bytes()
        self.assertTrue(console.startswith(capture_gui.BOM))
        self.assertIn(b"### TE QA capture: the edit line draws nothing", console)
        self.assertIn(b"te_qa_capture", (ov / capture_gui.ERROR_DEER_FILE).read_bytes())

    def test_a_plain_start_carries_neither(self):
        install_game_files(self.paths.base_game)
        reply = self.start()
        self.assertNotIn("capture", reply)
        self.assertFalse((self.paths.overlay_dir / capture_gui.CONSOLE_FILE).exists())

    def test_a_missing_or_moved_file_refuses_before_anything_is_done(self):
        e = self.session_error(self.start, capture=True)
        self.assertEqual(e.code, "capture_gui_missing")
        self.assertEqual(self.cli.calls, [])
        install_game_files(self.paths.base_game)
        (self.paths.base_game / capture_gui.ERROR_DEER_SOURCE).write_text("widget = {}\n")
        fresh = session.Session(self.game, self.cli, self.spawn_watch, self.paths, sleep=self.game.sleep,
                                clock=self.game.clock)
        with self.assertRaises(session.SessionError) as caught:
            fresh.start(tgs.PERMISSION, as_tag="FRA", capture=True)
        self.assertEqual(caught.exception.code, "capture_gui_changed")
        self.assertEqual(self.cli.calls, [])


class VerbsTestBase(tgs.SessionTestCase):
    def setUp(self):
        super().setUp()
        self.reload_logs = True
        real_preview = overlay.write_preview
        self.wrappers: list[str] = []

        def preview(ov, text, revision):
            self.wrappers.append(text)
            real_preview(ov, text, revision)
            if self.reload_logs:
                self.game.error("Unlocalized text 'te_qa_rev_%d' at gui/te_qa_preview.gui:31, either localize it or "
                                "use the raw_text property instead of text" % revision)
        patcher = mock.patch.object(overlay, "write_preview", preview)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.started()
        self.game.client = (0, 0, 400, 300)
        self.game.pending_events = []
        self.session.events()                   # the console open, as after any verb that types


class ViewTest(VerbsTestBase):
    def test_it_writes_one_widget_a_step_waits_for_the_reload_creates_them_in_order_and_clears(self):
        reply = self.session.view([["clear:com_open_window", "close-panel"], ["panel:budget:te_banking"]])
        self.assertEqual(reply["revision"], 1)
        self.assertEqual(reply["steps"], [["clear:com_open_window", "close-panel"], ["panel:budget:te_banking"]])
        gui = [c for c in self.typed() if c.startswith("gui.")]
        self.assertEqual(gui, [session.CLEAR_WIDGETS, session.VIEW_CREATE % 0, session.VIEW_CREATE % 1,
                               session.CLEAR_WIDGETS])
        self.assertIn("InformationPanelBar.OpenPanelTab( 'budget', 'te_banking' )", self.wrappers[-1])
        self.assertEqual(self.game.clicks, [], "a view clicks nothing")
        self.assertFalse(self.session._console.keyboard_away)

    def test_a_bad_action_is_refused_before_anything_is_written(self):
        before = list(self.typed())
        e = self.session_error(self.session.view, [["set:a=b", "ExecuteConsoleCommand('save')"]])
        self.assertEqual(e.code, "bad_action")
        self.assertEqual(self.wrappers, [])
        self.assertEqual(self.typed(), before)

    def test_no_reload_creates_nothing(self):
        self.reload_logs = False
        e = self.session_error(self.session.view, [["close-panel"]])
        self.assertEqual(e.code, "not_reloaded")
        self.assertNotIn(session.VIEW_CREATE % 0, self.typed())

    def test_revisions_count_on_from_a_preview(self):
        self.session.view([["close-panel"]])
        self.assertEqual(self.session.view([["close-panel"]])["revision"], 2)


class CropTest(VerbsTestBase):
    def test_the_box_is_shot_alone_at_full_size(self):
        self.game.frames.append(frame(400, 300, spot=(100, 30, (200, 0, 0))))
        reply = self.session.crop([0.25, 0.1, 0.75, 0.5], label="x")
        self.assertEqual(reply["pixels"], [100, 30, 300, 150])
        self.assertEqual(reply["crop_size"], [200, 120])
        self.assertEqual(reply["window"], [400, 300])
        self.assertEqual(self.game.boxes[-1], (100, 30, 200, 120))
        self.assertTrue(reply["crop"].endswith("_x.png"))
        image = pixels.decode_png(Path(reply["crop"]).read_bytes())
        self.assertEqual(image[:2], (200, 120))
        self.assertEqual(image[2][:3], bytes((200, 0, 0)), "the painted pixel is the crop's first")
        self.assertNotIn("settled", reply)

    def test_settle_shoots_until_two_shots_agree_and_keeps_only_the_last(self):
        for i in range(3):
            self.game.frames.append(frame(400, 300, colour=(i * 50, 0, 0)))
        self.game.frames.append(frame(400, 300, colour=(150, 0, 0)))
        reply = self.session.crop(settle=True)
        # four frames, the last held: the fourth and fifth shots are the first two alike
        self.assertEqual((reply["settled"], reply["tries"], reply["changed_share"]), (True, 5, 0.0))
        crops = sorted(Path(reply["crop"]).parent.glob("crop_*.png"))
        self.assertEqual(crops, [Path(reply["crop"])])

    def test_an_animation_that_never_stops_still_settles(self):
        for i in range(4):
            self.game.frames.append(frame(400, 300, spot=(i, 0, (255, 255, 255))))
        reply = self.session.crop(settle=True)
        self.assertTrue(reply["settled"])
        self.assertEqual(reply["tries"], 2)
        self.assertGreater(reply["changed_share"], 0)

    def test_a_panel_that_keeps_changing_does_not(self):
        for i in range(session.CROP_SETTLE_TRIES + 2):
            self.game.frames.append(frame(400, 300, colour=(i * 28, 0, 0)))      # steps above changed()'s 24
        reply = self.session.crop(settle=True)
        self.assertEqual((reply["settled"], reply["tries"]), (False, session.CROP_SETTLE_TRIES))

    def test_bad_arguments(self):
        for kwargs in ({"box": [0.5, 0.5, 0.4, 0.6]}, {"box": [0, 0, 2, 1]}, {"label": "a b"}, {"settle": "yes"}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(self.session_error(self.session.crop, **kwargs).code, "bad_argument")


class HoverTest(VerbsTestBase):
    def test_it_moves_the_cursor_presses_nothing_and_leaves_the_keyboard(self):
        reply = self.session.hover(0.5, 0.25)
        self.assertEqual(self.game.moves, [(200, 75)])
        self.assertEqual(reply["pixel"], [200, 75])
        self.assertEqual(self.game.clicks, [])
        self.assertFalse(self.session._console.keyboard_away)
        self.session.events()                   # a verb that types still types

    def test_a_refusal_moved_nothing(self):
        def refuse(pid, x, y):
            raise HelperError("covered", "another window is under the point")
        self.game.move = refuse
        self.assertEqual(self.session_error(self.session.hover, 0.5, 0.5).code, "hover_refused")


class ViewStepsTest(unittest.TestCase):
    def test_then_starts_a_step(self):
        from game_qa import client
        self.assertEqual(client.view_steps(["close-panel", "then", "panel:budget:te_banking", "set:a=b"]),
                         [["close-panel"], ["panel:budget:te_banking", "set:a=b"]])
        for words in ([], ["then", "close-panel"], ["close-panel", "then"], ["a", "then", "then", "b"]):
            with self.subTest(words=words):
                with self.assertRaises(ValueError):
                    client.view_steps(words)


class FakeSession:
    """`capture`'s view of a session: each verb answered from what the test set."""

    def __init__(self, tmp: Path, reads: dict | None = None, window=(3840, 2160)) -> None:
        self.tmp, self.reads, self.window = tmp, dict(reads or {}), list(window)
        self.calls: list[tuple[str, dict]] = []
        self.n = 0

    def __call__(self, verb, body=None, timeout=None):
        body = dict(body or {})
        self.calls.append((verb, body))
        if verb == "read":
            return {"reads": [{"expr": e, "ok": e in self.reads, "value": self.reads.get(e)} for e in body["exprs"]]}, 0
        if verb == "crop":
            self.n += 1
            path = self.tmp / ("crop_%02d.png" % self.n)
            path.write_bytes(fakes.win_helper.encode_png(4, 4, bytes(48)))
            return {"crop": str(path), "settled": True, "tries": 2, "crop_size": [4, 4], "window": self.window}, 0
        if verb == "status":
            return {"started": True, "save": "s", "country": "USA"}, 0
        return {"log": []} if verb == "view" else {}, 0


class Manifest:
    """A manifest module's shape, two shots in one scene."""
    WINDOW, UI_SCALE, TAKEN, DEFAULT_MAX_KB = (3840, 2160), 1.5, ("pilot", "entry"), 1000
    CAPTURE_KEY, TE_WINDOW_KEYS = "te_qa_capture", ("com_open_window",)
    SCENES = {"late": dict(save="s", as_tag="USA", playset="current", unresponsive_s=120)}
    REGIONS = {"side": (0.0, 0.0, 0.5, 1.0)}

    def __init__(self):
        self.SHOTS = {
            "one": dict(out="img/one.png", status="pilot", scene="late", needs=["nd_stockpile > 0"],
                        view=[["set:te_x=yes", "panel:budget:te_banking"]], crop="side", shows="one"),
            "two": dict(out="img/two.png", status="entry", scene="late", country="GBR",
                        needs=["c:{tag} = { has_journal_entry = je_x }"], view=[["market:te_y"]], crop="side",
                        hover=(0.3, 0.4), setups={"make_y": "add_modifier = y"}, shows="two"),
            "drawn": dict(out="img/drawn.png", status="assisted", scene="late"),
        }

    parse_need = staticmethod(guide_shots.parse_need)

    def crop_box(self, shot):
        return tuple(self.REGIONS[shot["crop"]])

    def shot_countries(self, shot):
        country = shot.get("country")
        return list(country) if isinstance(country, list) else [country or self.SCENES[shot["scene"]]["as_tag"]]

    def validate(self):
        return []


class CaptureRunTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.m = Manifest()

    def run_capture(self, fake, ids=("one", "two")):
        cap = capture.Capture(self.m, fake, self.tmp)
        cap.scene("late", list(ids), {"country": "USA", "capture": {"ui_scale": 1.5}})
        return cap.results

    def test_a_shot_reads_its_needs_views_parks_and_crops(self):
        fake = FakeSession(self.tmp, {"nd_stockpile": 19.0, "c:GBR = { has_journal_entry = je_x }": True})
        results = self.run_capture(fake)
        self.assertEqual(results["one"]["status"], "taken")
        self.assertEqual(results["two"]["status"], "taken")
        verbs = [v for v, _ in fake.calls]
        self.assertEqual(verbs, ["read", "view", "hover", "crop", "tag", "read", "run-setup", "view", "hover", "crop",
                                 "view"])
        views = [b["steps"] for v, b in fake.calls if v == "view"]
        self.assertEqual(views[0][0], ["clear:com_open_window", "close-panel", "set:te_qa_capture=yes"])
        self.assertEqual(views[1][0], ["clear:com_open_window", "clear:te_x", "close-panel", "set:te_qa_capture=yes"],
                         "the next shot clears what the last one set")
        self.assertEqual(views[-1], [["clear:com_open_window", "close-panel", "clear:te_qa_capture"]])
        hovers = [b for v, b in fake.calls if v == "hover"]
        self.assertEqual(hovers, [{"x": capture.CONSOLE_PARK[0], "y": capture.CONSOLE_PARK[1]}, {"x": 0.3, "y": 0.4}])
        crops = [b for v, b in fake.calls if v == "crop"]
        self.assertEqual(crops[0], {"box": [0.0, 0.0, 0.5, 1.0], "settle": True, "label": "one"})
        self.assertTrue(Path(results["one"]["new"]).is_file())

    def test_a_scroll_turns_the_wheel_and_takes_the_keyboard_back_before_the_shot(self):
        self.m.SHOTS["one"]["scroll"] = (0.13, 0.6, -8)
        fake = FakeSession(self.tmp, {"nd_stockpile": 1.0})
        self.run_capture(fake, ["one"])
        verbs = [(v, b) for v, b in fake.calls if v in ("view", "wheel", "click", "hover", "crop")]
        self.assertEqual([v for v, _ in verbs], ["view", "wheel", "click", "hover", "crop", "view"])
        self.assertEqual(verbs[1][1], {"x": 0.13, "y": 0.6, "notches": -8})
        self.assertEqual(verbs[2][1], {"console": True})

    def test_an_unmet_need_skips_the_shot_with_what_was_read(self):
        fake = FakeSession(self.tmp, {"nd_stockpile": 0.0})
        results = self.run_capture(fake, ["one"])
        self.assertEqual(results["one"]["status"], "skipped")
        self.assertEqual(results["one"]["needs"][0]["value"], 0.0)
        self.assertNotIn("crop", [v for v, _ in fake.calls])

    def test_candidate_countries_are_tried_until_one_meets_the_needs(self):
        self.m.SHOTS["one"]["country"] = ["BRZ", "JAP", "KOR"]
        self.m.SHOTS["one"]["needs"] = ["c:{tag} = { has_journal_entry = je_x }"]
        fake = FakeSession(self.tmp, {"c:KOR = { has_journal_entry = je_x }": True})
        real = fake.__call__

        def call(verb, body=None, timeout=None):
            if verb == "tag" and body["tag"] == "BRZ":
                fake.calls.append((verb, dict(body)))
                return {"refused": "tag_failed", "detail": "tag BRZ answered ['Such country does not exist.']"}, 2
            return real(verb, body, timeout)
        cap = capture.Capture(self.m, call, self.tmp)
        cap.scene("late", ["one"], {"country": "USA", "capture": {"ui_scale": 1.5}})
        result = cap.results["one"]
        self.assertEqual((result["status"], result["country"]), ("taken", "KOR"))
        self.assertEqual([t["country"] for t in result["tried"]], ["BRZ", "JAP"])
        self.assertIn("not in this save", result["tried"][0]["reason"])
        self.assertEqual([b["tag"] for v, b in fake.calls if v == "tag"], ["BRZ", "JAP", "KOR"])

    def test_no_candidate_skips_with_each_ones_reason(self):
        self.m.SHOTS["one"]["country"] = ["JAP", "KOR"]
        fake = FakeSession(self.tmp, {"nd_stockpile": 0.0})
        results = self.run_capture(fake, ["one"])
        self.assertEqual(results["one"]["status"], "skipped")
        self.assertEqual([t["country"] for t in results["one"]["tried"]], ["JAP", "KOR"])
        self.assertIn("KOR need not met: nd_stockpile > 0", results["one"]["reason"])
        self.assertNotIn("crop", [v for v, _ in fake.calls])

    def test_a_read_that_fails_is_not_a_met_need(self):
        results = self.run_capture(FakeSession(self.tmp, {}), ["one"])
        self.assertEqual(results["one"]["status"], "skipped")
        self.assertIsNone(results["one"]["needs"][0]["met"])

    def test_another_window_stops_the_scene(self):
        fake = FakeSession(self.tmp, {"nd_stockpile": 1.0, "c:GBR = { has_journal_entry = je_x }": True},
                           window=(1920, 1080))
        results = self.run_capture(fake)
        self.assertEqual((results["one"]["status"], results["one"]["error"]), ("failed", "window_mismatch"))
        self.assertEqual(results["two"]["status"], "not_run")

    def test_needs_and_keys(self):
        self.assertTrue(capture.need_met({"ok": True, "value": 2.0}, ">", 0))
        self.assertFalse(capture.need_met({"ok": True, "value": 0.0}, ">", 0))
        self.assertTrue(capture.need_met({"ok": True, "value": True}, None, None))
        self.assertFalse(capture.need_met({"ok": True, "value": False}, None, None))
        self.assertIsNone(capture.need_met({"ok": False, "value": None}, ">", 0))
        self.assertIsNone(capture.need_met({"ok": True, "value": True}, ">", 0))
        self.assertEqual(capture.keys_set([["set:a=1", "clear:b", "set:a=2"], ["set:c=x"]]), ["a", "c"])

    def test_the_start_body_has_the_scene_and_every_setup(self):
        body = capture.start_body(self.m, "late", ["one", "two"], "granted")
        self.assertEqual((body["save"], body["as_tag"], body["playset"], body["capture"]), ("s", "USA", "current", True))
        self.assertEqual(body["setups"], {"make_y": "add_modifier = y"})
        self.assertEqual(body["game_args"], ["no_notifications"])
        self.assertEqual(body["unresponsive_s"], 120)

    def test_select(self):
        self.assertEqual(capture.select(self.m), ["one", "two"])
        self.assertEqual(capture.select(self.m, only=["two"]), ["two"])
        for kwargs, code in (({"only": ["drawn"]}, "not_a_view"), ({"only": ["nope"]}, "unknown_shot"),
                             ({"scenes": ["nope"]}, "unknown_scene")):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(capture.CaptureError) as caught:
                    capture.select(self.m, **kwargs)
                self.assertEqual(caught.exception.code, code)


class SheetTest(unittest.TestCase):
    def test_the_contact_sheet_lists_every_shot_with_its_pictures(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            results = {"one": {"id": "one", "status": "taken", "new": str(out / "one.png"), "old": str(out / "one.old.png"),
                               "change": "changed", "changed_share": 0.5, "shows": "<b>the tab</b>"},
                       "two": {"id": "two", "status": "skipped", "reason": "need not met: x > 0",
                               "needs": [{"need": "x > 0", "value": 0.0}]}}
            page = capture.contact_sheet(results, out, "t").read_text(encoding="utf-8")
            self.assertIn('src="one.png"', page)
            self.assertIn('src="one.old.png"', page)
            self.assertIn("&lt;b&gt;the tab&lt;/b&gt;", page, "the manifest's text is escaped")
            self.assertIn("need not met: x &gt; 0", page)
            self.assertIn("50.00% of pixels", page)
            results["one"].update(change="resized", old_size=[820, 1615], crop_size=[854, 2052])
            page = capture.contact_sheet(results, out, "t").read_text(encoding="utf-8")
            self.assertIn("difference: none: the sizes differ (820x1615 to 854x2052)", page)


class WriteBackTest(unittest.TestCase):
    """`--write`: a changed picture is copied to its `out` and recorded; an unchanged one is left. With Pillow absent
    (CI installs none) a .png is copied as it is and a .jpg is refused, named in the result."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        (self.repo / "img").mkdir()
        (self.repo / "scripts" / "image_pipeline").mkdir(parents=True)
        self.new = self.repo / "new.png"
        self.new.write_bytes(fakes.win_helper.encode_png(2, 2, bytes(12)))
        self.m = Manifest()

    def write(self, results):
        with mock.patch.object(capture, "_git", lambda repo, *a: "abc123"), mock.patch.object(capture, "_pillow",
                                                                                               lambda: None):
            return capture.write_back(results, self.m, self.repo, ([3840, 2160], 1.5), {"one": "s", "two": "s"})

    def test_changed_pictures_are_written_and_recorded(self):
        results = {"one": {"status": "taken", "out": "img/one.png", "new": str(self.new), "change": "changed"},
                   "two": {"status": "taken", "out": "img/two.png", "new": str(self.new), "change": "unchanged"}}
        self.assertEqual(self.write(results), ["img/one.png"])
        self.assertEqual((self.repo / "img" / "one.png").read_bytes(), self.new.read_bytes())
        self.assertFalse((self.repo / "img" / "two.png").exists())
        taken = json.loads((self.repo / capture.TAKEN_FILE).read_text())
        self.assertEqual(list(taken), ["one"])
        self.assertEqual((taken["one"]["commit"], taken["one"]["window"], taken["one"]["ui_scale"], taken["one"]["save"]),
                         ("abc123", [3840, 2160], 1.5, "s"))

    def test_a_jpeg_needs_pillow(self):
        results = {"one": {"status": "taken", "out": "img/one.jpg", "new": str(self.new), "change": "new"}}
        self.assertEqual(self.write(results), [])
        self.assertIn("Pillow", results["one"]["write_error"])


class MainVerbTest(unittest.TestCase):
    def test_list_starts_nothing_and_a_run_needs_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            started = []
            reply, code = capture.main_verb(capture._arg_namespace(list=True), call=None, start=started.append,
                                            stop=None, backup_root=Path(tmp))
            self.assertEqual(code, 0)
            self.assertIn("late_2043", reply["plan"])
            reply, code = capture.main_verb(capture._arg_namespace(), call=None, start=started.append, stop=None,
                                            backup_root=Path(tmp))
            self.assertEqual((code, reply["refused"]), (2, "no_permission"))
            self.assertEqual(started, [])

    def test_a_failed_start_is_reported_and_nothing_is_taken(self):
        for stop_reply, stops_wanted in (({"outcome": "restored"}, 0), ({"outcome": "refused", "stop_again": True}, 1)):
            with self.subTest(stop=stop_reply), tempfile.TemporaryDirectory() as tmp:
                stops = []
                reply, code = capture.main_verb(
                    capture._arg_namespace(permission="granted", only=["banking_tab"]), call=None,
                    start=lambda body: ({"refused": "gpu_busy", "detail": "x", "stop": stop_reply}, 2),
                    stop=lambda: (stops.append(1) or ({"outcome": "restored"}, 0)), backup_root=Path(tmp))
                self.assertEqual(code, 2)
                self.assertEqual(reply["results"]["banking_tab"]["status"], "not_run")
                self.assertEqual(len(stops), stops_wanted, "a stop only when the start's own can be run again")
                self.assertTrue(json.loads(Path(reply["capture_dir"], "capture.json").read_text())["results"])


if __name__ == "__main__":
    unittest.main()
