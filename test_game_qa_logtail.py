"""game_qa/logtail.py: following a log across rotation, and parsing its lines.

The rotation here is the game's as the probes saw it: `debug.log` is renamed
`debug.1.log`, each older generation moves up one, the sixth is dropped.
"""
import os
import tempfile
import unittest
from pathlib import Path

from game_qa import logtail

FIXTURE = Path(__file__).resolve().parent / "test_fixtures" / "game_qa" / "debug_console_lines.txt"


class FollowerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.logs = Path(self._tmp.name)
        self.live = self.logs / "debug.log"
        self.live.write_bytes(b"")
        self.follower = logtail.LogFollower(self.live)

    def append(self, text: str) -> None:
        with open(self.live, "ab") as f:
            f.write(text.encode("utf-8"))

    def rotate(self) -> None:
        oldest = self.logs / f"debug.{logtail.GENERATIONS}.log"
        if oldest.exists():
            oldest.unlink()
        for k in range(logtail.GENERATIONS - 1, 0, -1):
            src = self.logs / f"debug.{k}.log"
            if src.exists():
                os.replace(src, self.logs / f"debug.{k + 1}.log")
        os.replace(self.live, self.logs / "debug.1.log")
        self.live.write_bytes(b"")

    def test_reports_each_line_once(self):
        self.append("a\nb\n")
        self.assertEqual(self.follower.poll(), ["a", "b"])
        self.assertEqual(self.follower.poll(), [])
        self.append("c\n")
        self.assertEqual(self.follower.poll(), ["c"])

    def test_missing_file_is_no_lines_and_is_picked_up_later(self):
        self.live.unlink()
        self.assertEqual(self.follower.poll(), [])
        self.live.write_bytes(b"a\n")
        self.assertEqual(self.follower.poll(), ["a"])

    def test_holds_a_partial_last_line(self):
        self.append("[12:00:00][console.cpp:1203]: console_success: select_event_option "
                    "[option index, or list] [<event id, default ")
        self.assertEqual(self.follower.poll(), [])
        self.append("oldest pending>]\n")
        got = self.follower.poll()
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0].endswith("[<event id, default oldest pending>]"))

    def test_crlf_and_bad_bytes(self):
        with open(self.live, "ab") as f:
            f.write(b"a\r\nb\xff\n")
        self.assertEqual(self.follower.poll(), ["a", "b�"])

    def test_rotation_mid_read_loses_and_repeats_nothing(self):
        self.append("a\nb\n")
        self.assertEqual(self.follower.poll(), ["a", "b"])
        self.append("c\n")
        self.rotate()
        self.append("d\n")
        self.assertEqual(self.follower.poll(), ["c", "d"])
        self.assertEqual(self.follower.poll(), [])

    def test_a_line_split_across_the_rotation(self):
        self.append("a\nfirst half, ")
        self.assertEqual(self.follower.poll(), ["a"])
        self.rotate()
        self.append("second half\n")
        self.assertEqual(self.follower.poll(), ["first half, second half"])

    def test_two_rotations_between_polls(self):
        self.append("a\n")
        self.assertEqual(self.follower.poll(), ["a"])
        self.append("b\n")
        self.rotate()
        self.append("c\n")
        self.rotate()
        self.append("d\n")
        self.assertEqual(self.follower.poll(), ["b", "c", "d"])

    def test_generations_that_start_with_the_same_line_are_told_apart(self):
        flood = "[12:10:58][jomini_effect.cpp:1139]: Adding effect after PostInitAndValidate, unless this is handled\n"
        self.append(flood + "mine 1\n")
        self.assertEqual(self.follower.poll(), [flood.strip(), "mine 1"])
        self.append("mine 2\n")
        self.rotate()
        self.append(flood + "next 1\n")
        self.rotate()
        self.append(flood + "next 2\n")
        self.assertEqual(self.follower.poll(), ["mine 2", flood.strip(), "next 1", flood.strip(), "next 2"])

    def test_flood_past_six_generations_reports_the_gap(self):
        self.append("a\n")
        self.follower.poll()
        self.append("never read\n")
        for i in range(7):
            self.rotate()
            self.append("gen%d\n" % i)
        got = self.follower.poll()
        self.assertEqual(got[0], logtail.GAP_MARKER)
        self.assertEqual(got.count(logtail.GAP_MARKER), 1)
        self.assertEqual(got[1:], ["gen1", "gen2", "gen3", "gen4", "gen5", "gen6"])
        self.assertNotIn("a", got)
        self.assertEqual(self.follower.poll(), [])

    def test_copy_and_truncate_rotation_falls_back_to_the_first_bytes(self):
        # A rotation that copies the file and empties it keeps the live inode: the first bytes find the copy.
        self.append("unique first line of this file, long enough to tell it apart\nb\n")
        self.assertEqual(len(self.follower.poll()), 2)
        self.append("c\n")
        (self.logs / "debug.1.log").write_bytes(self.live.read_bytes())
        with open(self.live, "wb"):
            pass
        self.append("d\n")
        self.assertEqual(self.follower.poll(), ["c", "d"])


class ParseTest(unittest.TestCase):
    def test_parse_the_recorded_session(self):
        lines = FIXTURE.read_text(encoding="utf-8").splitlines()
        parsed = [logtail.parse(line) for line in lines]
        kinds = [p.kind for p in parsed]
        self.assertIn("command", kinds)
        self.assertIn("success", kinds)
        self.assertIn("debug_log", kinds)
        opt = next(p for p in parsed if "option=C country=FRA" in p.text)
        self.assertEqual((opt.file, opt.lineno), ("events/te_qa_probe_events.txt", 44))
        self.assertEqual(opt.text, "TE_QA_PROBE option=C country=FRA")
        tag = next(p for p in parsed if p.kind == "command" and p.text == "tag FRA")
        self.assertEqual(tag.time, "12:51:23")

    def test_console_kinds(self):
        self.assertEqual(logtail.parse("[12:08:13][console.cpp:1203]: console_failure: Usage: x").kind, "failure")
        ok = logtail.parse("[12:51:23][console.cpp:1203]: console_success: Now Playing - France")
        self.assertEqual((ok.kind, ok.text), ("success", "Now Playing - France"))

    def test_cpp_line_numbers_do_not_matter(self):
        moved = logtail.parse("[12:51:23][console.cpp:9999]: Running console command: tag FRA")
        self.assertEqual((moved.kind, moved.text), ("command", "tag FRA"))

    def test_other_lines(self):
        err = logtail.parse("[12:04:00][jomini_eventmanager.cpp:440]: Duplicated event ID 'formation.17' found.")
        self.assertEqual(err.kind, "other")
        cont = logtail.parse("  Script location: file: events/x.txt line: 4")
        self.assertEqual((cont.kind, cont.time), ("other", ""))

    def test_pending_events(self):
        self.assertEqual(
            logtail.pending_events(["2063597726 un_vote.3 options=3", "184549455 te_qa_probe.2 options=3"]),
            [logtail.Pending(2063597726, "un_vote.3", 3), logtail.Pending(184549455, "te_qa_probe.2", 3)],
        )
        self.assertEqual(logtail.pending_events(["No pending events"]), [])


if __name__ == "__main__":
    unittest.main()
