"""Tests for game_qa.overlay: the generated mod folder that holds the harness's own script.

No game and no Windows program is needed: every test builds the overlay in a temp dir.
"""

import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game_qa import overlay

BOM = b"\xef\xbb\xbf"
READ_LINE_TEXT = (
    'debug_log = "TE_QA read country=[THIS.GetCountry.GetTagName] date=[TimeKeeper.GetCurrentDate.GetString]"'
)
SETUP_A = "set_variable = { name = te_qa_a value = 1 }"
SETUP_B = "c:FRA = {\n\tadd_treasury = 5000\n}"
TXT_FILES = (
    "events/te_qa_events.txt",
    "common/scripted_effects/te_qa_effects.txt",
    "tools/scripted_tests/te_qa_fixture.txt",
)


def lines_of(path: Path) -> list[str]:
    """The file's lines as the engine counts them: line 1 is the one that starts with the BOM."""
    return path.read_text(encoding="utf-8-sig").split("\n")


class OverlayTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.mods = self.base / "mod"
        self.mods.mkdir()
        self.dest = self.mods / overlay.OVERLAY_NAME

    def build(self, setups=None, version="1.15.0", dest=None):
        return overlay.build(dest or self.dest, {} if setups is None else setups, version)

    def listing(self, folder: Path) -> list[str]:
        return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*"))

    def write_owner_files(self, folder: Path) -> dict[str, bytes]:
        """A folder that is not an overlay: some of the owner's files, one of them a metadata.json."""
        files = {"notes.txt": b"the owner's notes", ".metadata/metadata.json": b'{"name": "Someone else"}'}
        for name, data in files.items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return files

    def assert_files_untouched(self, folder: Path, files: dict[str, bytes]):
        found = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
        self.assertEqual(found, files)


class BuildTest(OverlayTestCase):
    def test_build_writes_the_files_with_one_bom_and_tabs(self):
        result = self.build({"alpha": SETUP_A, "beta": SETUP_B})
        self.assertEqual(
            self.listing(self.dest),
            sorted(
                [
                    ".metadata",
                    ".metadata/metadata.json",
                    "common",
                    "common/scripted_effects",
                    "common/scripted_effects/te_qa_effects.txt",
                    "events",
                    "events/te_qa_events.txt",
                    "tools",
                    "tools/scripted_tests",
                    "tools/scripted_tests/te_qa_fixture.txt",
                ]
            ),
        )
        self.assertEqual(result.dir, self.dest)
        self.assertEqual(result.events_file, self.dest / "events" / "te_qa_events.txt")
        for name in TXT_FILES:
            with self.subTest(file=name):
                raw = (self.dest / name).read_bytes()
                self.assertTrue(raw.startswith(BOM), "starts with a BOM")
                self.assertEqual(raw.count(BOM), 1, "exactly one BOM")
                self.assertNotIn(b"\r", raw)
                self.assertTrue(raw.endswith(b"\n"))
                for number, line in enumerate(raw[len(BOM):].decode("utf-8").split("\n"), start=1):
                    self.assertFalse(line.startswith(" "), f"line {number} is indented with spaces: {line!r}")
                    self.assertEqual(line, line.rstrip(), f"line {number} has trailing whitespace")

    def test_metadata_carries_the_marker_and_the_game_version(self):
        self.build(version="1.15.2")
        raw = (self.dest / ".metadata" / "metadata.json").read_bytes()
        self.assertFalse(raw.startswith(BOM), "like the mod's own metadata.json, no BOM")
        meta = json.loads(raw)
        self.assertIn(overlay.MARKER, meta["short_description"])
        self.assertEqual(meta["supported_game_version"], "1.15.2")
        self.assertEqual(meta["id"], "")
        self.assertEqual(meta["relationships"], [])
        self.assertTrue(meta["name"])
        self.assertIn("\n\t\"name\"", raw.decode("utf-8"), "tab-indented")

    def test_the_scripted_test_fails_on_the_second_day_and_a_companion_passes(self):
        self.build()
        text = "\n".join(lines_of(self.dest / "tools" / "scripted_tests" / "te_qa_fixture.txt"))
        self.assertIn(
            "\t" + overlay.FIXTURE_TEST + ' = {\n\t\tsuccess = { always = no }\n\t\tfail = { game_date > "1836.1.1" }\n',
            text,
        )
        self.assertIn('last_date = "1836.1.3"', text)
        self.assertIn("-scripted_tests -run_until=1836.1.4", text)
        self.assertIn("TEST_FAIL_te_qa_fixture_2 January, 1836.v3", text)
        self.assertIn('success = { game_date > "1836.1.1" }\n\t\tfail = { always = no }', text)

    def test_a_dated_scripted_test_fails_on_its_date_and_its_suite_ends_the_day_after(self):
        # #1602: the 1836 test's offsets carried to a later date, in the fail trigger's form run live.
        overlay.build(self.dest, {}, "1.15.1", fixture_date=(1900, 1, 1))
        text = "\n".join(lines_of(self.dest / "tools" / "scripted_tests" / "te_qa_fixture.txt"))
        self.assertIn('\t\tsuccess = { always = no }\n\t\tfail = { game_date > "1899.12.31" }\n', text)
        self.assertIn('last_date = "1900.1.2"', text)
        self.assertIn("-scripted_tests -run_until=1900.1.3", text)
        self.assertIn("TEST_FAIL_te_qa_fixture_1 January, 1900.v3", text)
        self.assertIn('success = { game_date > "1899.12.31" }\n\t\tfail = { always = no }', text)

    def test_the_plain_fixtures_date_writes_the_1836_test_byte_for_byte(self):
        overlay.build(self.dest, {}, "1.15.1")
        plain = (self.dest / overlay.SCRIPTED_TEST_FILE).read_bytes()
        overlay.build(self.dest, {}, "1.15.1", fixture_date=(1836, 1, 2))
        self.assertEqual((self.dest / overlay.SCRIPTED_TEST_FILE).read_bytes(), plain)

    def test_a_fixture_date_the_test_cannot_fail_on_is_refused_before_anything_is_written(self):
        for date in ((1836, 1, 1), (1900, 2, 29), (1900, 13, 1)):
            with self.subTest(date=date):
                with self.assertRaises(overlay.OverlayError):
                    overlay.build(self.dest, {}, "1.15.1", fixture_date=date)
                self.assertFalse(self.dest.exists())

    def test_the_pad_effect_logs_sixty_lines(self):
        self.build()
        text = "\n".join(lines_of(self.dest / "common" / "scripted_effects" / "te_qa_effects.txt"))
        pad = re.search(r"^te_qa_pad = \{\n(.*?)\n\}\n", text, re.S | re.M)
        self.assertIsNotNone(pad, "te_qa_pad is defined")
        self.assertEqual(
            pad.group(1).split("\n")[:2], ["\twhile = {", "\t\tcount = 60"], "sixty lines through a while loop"
        )
        self.assertRegex(pad.group(1), r'\n\t\tdebug_log = "TE_QA PAD [0-9]{40,}"\n\t\}$')

    def test_the_generated_script_parses_as_paradox_script(self):
        from paradox_file_parser import ParadoxFileParser

        self.build({"alpha": SETUP_A, "beta": SETUP_B})

        def parse(relative: str) -> dict:
            parser = ParadoxFileParser()
            parser.parse_file(str(self.dest / relative))
            return parser.data

        effects = parse("common/scripted_effects/te_qa_effects.txt")
        slots = ["te_qa_slot_%d" % n for n in range(overlay.SLOT_COUNT)]
        self.assertEqual(sorted(effects),
                         sorted(["te_qa_loaded", "te_qa_pad", "te_qa_setup_alpha", "te_qa_setup_beta", *slots]))
        self.assertEqual(effects["te_qa_setup_beta"], ("=", {"c:FRA": ("=", {"add_treasury": ("=", "5000")})}))
        events = parse("events/te_qa_events.txt")
        spare = ["te_qa.%d" % (overlay.FIRST_SLOT_EVENT + n) for n in range(overlay.SLOT_COUNT)]
        self.assertEqual(list(events), ["namespace", "te_qa.1", "te_qa.2", "te_qa.3", "te_qa.10", "te_qa.11", *spare])
        for key in list(events)[1:]:
            body = events[key][1]
            self.assertEqual((body["type"], body["hidden"]), (("=", "country_event"), ("=", "yes")), key)
        tests = parse("tools/scripted_tests/te_qa_fixture.txt")["tests"][1]
        self.assertEqual(list(tests), [overlay.FIXTURE_TEST, "te_qa_pass"])

    def test_a_rebuild_replaces_the_old_overlay_and_leaves_no_temp_folder(self):
        self.build({"alpha": SETUP_A})
        stray = self.dest / "events" / "stray.txt"
        stray.write_text("left over", encoding="utf-8")
        result = self.build({"beta": SETUP_B})
        self.assertFalse(stray.exists())
        self.assertEqual(result.setup_events, {"beta": "te_qa.10"})
        self.assertNotIn("te_qa_setup_alpha", (self.dest / "common/scripted_effects/te_qa_effects.txt").read_text("utf-8"))
        self.assertEqual(os.listdir(self.mods), [overlay.OVERLAY_NAME])

    def test_build_does_not_create_missing_ancestors(self):
        before = self.listing(self.base)
        for dest in (self.base / "no user data" / "mod" / overlay.OVERLAY_NAME, self.base / "nowhere" / overlay.OVERLAY_NAME):
            with self.subTest(dest=dest):
                with self.assertRaises(overlay.OverlayError):
                    self.build(dest=dest)
        self.assertEqual(self.listing(self.base), before, "no folder was made")

    def test_build_refuses_a_parent_that_is_a_file(self):
        parent = self.base / "a file"
        parent.write_bytes(b"not a folder")
        with self.assertRaises(overlay.OverlayError):
            self.build(dest=parent / overlay.OVERLAY_NAME)
        self.assertEqual(parent.read_bytes(), b"not a folder")


class ReadLineTest(OverlayTestCase):
    def check_read_line(self, setups):
        result = self.build(setups)
        lines = lines_of(result.events_file)
        self.assertEqual(lines[0], "namespace = te_qa", "line 1 is the one that starts with the BOM")
        self.assertEqual(lines[result.read_line - 1], f"\t\t{READ_LINE_TEXT}")
        self.assertEqual(lines[result.read_line], "\t\tte_qa_pad = yes")
        self.assertEqual(lines[result.read_line + 1], "\t}")
        self.assertEqual(
            [n for n, line in enumerate(lines, start=1) if "TE_QA read" in line], [result.read_line]
        )
        start = max(n for n, line in enumerate(lines[: result.read_line], start=1) if line.startswith("te_qa."))
        self.assertEqual(lines[start - 1], f"{overlay.READ_EVENT} = {{")
        self.assertEqual(lines[start + 3], "\timmediate = {")
        return result

    def test_read_line_is_the_debug_log_line_of_the_read_event(self):
        self.check_read_line({})

    def test_read_line_does_not_move_with_the_setups(self):
        lines_without = self.check_read_line({}).read_line
        self.assertEqual(self.check_read_line({"alpha": SETUP_A, "beta": SETUP_B}).read_line, lines_without)

    def test_the_pad_event_only_pads(self):
        text = "\n".join(lines_of(self.build().events_file))
        self.assertIn(
            f"{overlay.PAD_EVENT} = {{\n\ttype = country_event\n\thidden = yes\n\n\timmediate = {{\n\t\tte_qa_pad = yes\n\t}}\n}}\n",
            text,
        )


class AddSetupTest(OverlayTestCase):
    """A setup added to a built overlay goes into a spare slot of te_qa_effects.txt (#1600)."""

    def effects(self) -> str:
        return "\n".join(lines_of(self.dest / "common" / "scripted_effects" / "te_qa_effects.txt"))

    def test_every_slot_has_an_event_and_starts_empty(self):
        ov = self.build({"alpha": SETUP_A})
        events = "\n".join(lines_of(ov.events_file))
        effects = self.effects()
        for slot in range(overlay.SLOT_COUNT):
            event = overlay.slot_event(slot)
            self.assertIn(
                f"{event} = {{\n\ttype = country_event\n\thidden = yes\n\n\timmediate = {{\n"
                f"\t\tte_qa_slot_{slot} = yes\n\t\tte_qa_pad = yes\n\t}}\n}}\n", events)
            self.assertIn(f'te_qa_slot_{slot} = {{\n\tdebug_log = "TE_QA slot {slot} is empty"\n}}\n', effects)
        self.assertEqual((overlay.slot_event(0), overlay.slot_event(29)), ("te_qa.100", "te_qa.129"))
        self.assertEqual((ov.revision, ov.added), (0, {}))
        self.assertIn('te_qa_loaded = {\n\tdebug_log = "TE_QA overlay rev 0"\n}\n', effects)

    def test_the_loaded_event_logs_the_revision_and_pads(self):
        events = "\n".join(lines_of(self.build().events_file))
        self.assertIn(
            f"{overlay.LOADED_EVENT} = {{\n\ttype = country_event\n\thidden = yes\n\n\timmediate = {{\n"
            "\t\tte_qa_loaded = yes\n\t\tte_qa_pad = yes\n\t}\n}\n", events)

    def test_an_added_setup_fills_the_next_slot_between_its_own_markers(self):
        ov = self.build({"alpha": SETUP_A})
        events_before = ov.events_file.read_bytes()
        self.assertEqual(overlay.add_setup(ov, "late", SETUP_B), ("te_qa.100", 1))
        self.assertEqual(overlay.add_setup(ov, "later", SETUP_A), ("te_qa.101", 2))
        effects = self.effects()
        self.assertIn(
            'te_qa_slot_0 = {\n\tdebug_log = "TE_QA setup late start"\n\tc:FRA = {\n\t\tadd_treasury = 5000\n\t}\n'
            '\tdebug_log = "TE_QA setup late done"\n}\n', effects)
        self.assertIn(f'te_qa_slot_1 = {{\n\tdebug_log = "TE_QA setup later start"\n\t{SETUP_A}\n', effects)
        self.assertIn('debug_log = "TE_QA slot 2 is empty"', effects)
        self.assertIn('debug_log = "TE_QA overlay rev 2"', effects)
        self.assertNotIn("TE_QA overlay rev 1", effects)
        # The setups given at start are still there, and the events file is not touched: a new event may not
        # reload, which is why the slots' events exist from the start.
        self.assertIn(f"te_qa_setup_alpha = {{\n\t{SETUP_A}\n}}\n", effects)
        self.assertEqual(ov.events_file.read_bytes(), events_before)
        self.assertEqual(ov.setup_events, {"alpha": "te_qa.10", "late": "te_qa.100", "later": "te_qa.101"})
        self.assertTrue((self.dest / "common/scripted_effects/te_qa_effects.txt").read_bytes().startswith(BOM))

    def test_the_rewritten_file_still_parses(self):
        from paradox_file_parser import ParadoxFileParser

        ov = self.build({"alpha": SETUP_A})
        overlay.add_setup(ov, "late", SETUP_B)
        parser = ParadoxFileParser()
        parser.parse_file(str(ov.effects_file))
        self.assertEqual(len(parser.data), 3 + overlay.SLOT_COUNT)
        self.assertEqual(parser.data["te_qa_loaded"], ("=", {"debug_log": ("=", '"TE_QA overlay rev 1"')}))

    def test_a_used_name_is_refused_and_nothing_is_written(self):
        ov = self.build({"alpha": SETUP_A})
        overlay.add_setup(ov, "late", SETUP_A)
        before = ov.effects_file.read_bytes()
        for name in ("alpha", "late"):
            with self.assertRaisesRegex(overlay.OverlayError, "used once"):
                overlay.add_setup(ov, name, SETUP_B)
        self.assertEqual((ov.effects_file.read_bytes(), ov.revision), (before, 1))

    def test_a_bad_name_or_body_is_refused_and_nothing_is_written(self):
        ov = self.build()
        before = ov.effects_file.read_bytes()
        for name, body in (("Bad Name", SETUP_A), ("late", "add_treasury = {"), ("late", "  ")):
            with self.assertRaises(overlay.OverlayError):
                overlay.add_setup(ov, name, body)
        self.assertEqual((ov.effects_file.read_bytes(), ov.revision, ov.added), (before, 0, {}))

    def test_no_slot_left_is_refused(self):
        ov = self.build()
        for n in range(overlay.SLOT_COUNT):
            overlay.add_setup(ov, "late_%d" % n, SETUP_A)
        with self.assertRaisesRegex(overlay.OverlayError, "spare slots are used"):
            overlay.add_setup(ov, "one_more", SETUP_A)
        self.assertEqual(ov.revision, overlay.SLOT_COUNT)

    def test_an_overlay_that_is_gone_or_not_ours_is_refused(self):
        ov = self.build()
        overlay.remove(self.dest)
        with self.assertRaisesRegex(overlay.OverlayError, "not this session's overlay"):
            overlay.add_setup(ov, "late", SETUP_A)
        self.assertFalse(self.dest.exists())
        self.assertEqual(ov.setup_events, {})

    def test_a_failed_write_leaves_the_record_as_it_was(self):
        ov = self.build()
        with mock.patch.object(Path, "write_bytes", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(overlay.OverlayError, "could not be rewritten"):
                overlay.add_setup(ov, "late", SETUP_A)
        self.assertEqual((ov.revision, ov.added, ov.setup_events), (0, {}, {}))

    def test_a_write_cut_short_puts_the_old_file_back(self):
        # Review finding: a failure midway left half a file, which the game would reload.
        ov = self.build({"alpha": SETUP_A})
        before = ov.effects_file.read_bytes()
        real = Path.write_bytes
        calls = []

        def cut_short(path, data):
            calls.append(len(data))
            if len(calls) == 1:
                real(path, data[:197])
                raise OSError("no space left on device")
            return real(path, data)

        with mock.patch.object(Path, "write_bytes", cut_short):
            with self.assertRaisesRegex(overlay.OverlayError, "put back as it was"):
                overlay.add_setup(ov, "late", SETUP_B)
        self.assertEqual(ov.effects_file.read_bytes(), before)
        self.assertEqual((ov.revision, ov.added), (0, {}))

    def test_too_many_start_setups_are_refused(self):
        setups = {"s%d" % n: SETUP_A for n in range(overlay.MAX_START_SETUPS + 1)}
        with self.assertRaisesRegex(overlay.OverlayError, "at most"):
            self.build(setups)
        self.assertFalse(self.dest.exists())

    def test_loaded_revision_reads_the_log_line(self):
        line = "[12:00:01][jomini_effect_impl.cpp:459]: common/scripted_effects/te_qa_effects.txt:12: TE_QA overlay rev 7"
        self.assertEqual(overlay.loaded_revision(line), 7)
        self.assertEqual(overlay.loaded_revision("TE_QA overlay rev 12"), 12)
        self.assertIsNone(overlay.loaded_revision("TE_QA overlay rev"))
        self.assertIsNone(overlay.loaded_revision("TE_QA overlay rev \u00b2"))      # a digit to str.isdigit, not to int
        self.assertIsNone(overlay.loaded_revision("TE_QA overlay rev 3 and more"))
        self.assertIsNone(overlay.loaded_revision("TE_QA PAD 0123"))


class SetupTest(OverlayTestCase):
    def test_each_setup_gets_its_own_event_and_effect(self):
        result = self.build({"zeta": SETUP_B, "alpha": SETUP_A})
        self.assertEqual(result.setup_events, {"alpha": "te_qa.10", "zeta": "te_qa.11"})
        events = "\n".join(lines_of(result.events_file))
        for name, event in result.setup_events.items():
            self.assertIn(
                f"{event} = {{\n\ttype = country_event\n\thidden = yes\n\n\timmediate = {{\n"
                f'\t\tdebug_log = "TE_QA setup {name} start"\n'
                f"\t\tte_qa_setup_{name} = yes\n"
                f'\t\tdebug_log = "TE_QA setup {name} done"\n'
                f"\t\tte_qa_pad = yes\n\t}}\n}}\n",
                events,
            )
        effects = "\n".join(lines_of(self.dest / "common" / "scripted_effects" / "te_qa_effects.txt"))
        self.assertIn(f"te_qa_setup_alpha = {{\n\t{SETUP_A}\n}}\n", effects)
        self.assertIn("te_qa_setup_zeta = {\n\tc:FRA = {\n\t\tadd_treasury = 5000\n\t}\n}\n", effects)

    def test_the_body_is_kept_as_written_and_indented_by_one_tab(self):
        body = "# a comment\nfirst = {\n\tsecond = yes\n\n\t# another\n}\n"
        self.build({"alpha": body})
        effects = "\n".join(lines_of(self.dest / "common" / "scripted_effects" / "te_qa_effects.txt"))
        self.assertIn(
            "te_qa_setup_alpha = {\n\t# a comment\n\tfirst = {\n\t\tsecond = yes\n\n\t\t# another\n\t}\n}\n", effects
        )

    def test_a_body_that_ends_in_a_comment_cannot_comment_out_the_closing_brace(self):
        self.build({"alpha": "x = yes # { not counted"})
        effects = "\n".join(lines_of(self.dest / "common" / "scripted_effects" / "te_qa_effects.txt"))
        self.assertIn("te_qa_setup_alpha = {\n\tx = yes # { not counted\n}\n", effects)

    def test_setup_names_at_the_limits_are_accepted(self):
        for name in ("a", "a" + "b9_" * 13 + "z", "a" * 41):
            with self.subTest(name=name):
                self.assertEqual(self.build({name: SETUP_A}).setup_events, {name: "te_qa.10"})

    def test_a_bad_setup_name_is_refused(self):
        for name in ("", "Alpha", "1abc", "_a", "a-b", "a b", "a\n", "alpha\n", "a" * 42, "é", "a.b"):
            with self.subTest(name=name):
                with self.assertRaises(overlay.OverlayError):
                    self.build({name: SETUP_A})
                self.assertFalse(self.mods.exists() and os.listdir(self.mods), "nothing left behind")


class BodyTest(OverlayTestCase):
    GOOD = (
        "a = { b = yes }",
        "a = yes\nb = { c = { d = yes } }",
        'debug_log = "an open brace { in a string"',
        'debug_log = "a close brace } in a string"',
        "a = yes # an open brace { in a comment",
        "# } a close brace in a comment\na = yes",
        'debug_log = "text with a hash # and a brace }"',
        '# a quote " in a comment does not open a string\na = { b = yes }',
        'debug_log = "#b bold#! { "\nb = { c = yes }',
        'debug_log = "first \n second }"',
    )
    BAD = (
        "a = {",
        "a = { b = { c = yes }",
        "a = yes }",
        "} a = {",
        "a = yes } b = { c = yes",
        "}{",
        'debug_log = "unterminated }',
        'a = { debug_log = "unterminated } }',
        "",
        "   ",
        "\n\t\n",
    )

    def test_a_setup_with_unbalanced_braces_is_refused(self):
        for body in self.BAD:
            with self.subTest(body=body):
                with self.assertRaises(overlay.OverlayError):
                    self.build({"alpha": body})
                self.assertFalse(self.dest.exists())
                self.assertEqual(os.listdir(self.mods) if self.mods.exists() else [], [])

    def test_a_brace_inside_a_string_or_a_comment_does_not_count(self):
        for body in self.GOOD:
            with self.subTest(body=body):
                self.assertEqual(self.build({"alpha": body}).setup_events, {"alpha": "te_qa.10"})

    def test_a_refused_body_leaves_an_existing_overlay_untouched(self):
        self.build({"alpha": SETUP_A})
        before = {p: p.read_bytes() for p in self.dest.rglob("*") if p.is_file()}
        with self.assertRaises(overlay.OverlayError):
            self.build({"alpha": SETUP_A, "beta": "a = {"})
        self.assertEqual({p: p.read_bytes() for p in self.dest.rglob("*") if p.is_file()}, before)
        self.assertEqual(os.listdir(self.mods), [overlay.OVERLAY_NAME])

    def test_the_error_names_the_setup(self):
        with self.assertRaises(overlay.OverlayError) as caught:
            self.build({"alpha": SETUP_A, "beta": "a = {"})
        self.assertIn("beta", str(caught.exception))

    def test_check_setups_refuses_what_build_refuses_and_writes_nothing(self):
        for setups in ({"alpha": "a = {"}, {"Alpha": SETUP_A}, {"alpha": ""}, {"alpha": 3}):
            with self.subTest(setups=setups):
                with self.assertRaises(overlay.OverlayError):
                    overlay.check_setups(setups)
        overlay.check_setups({"alpha": SETUP_A, "beta": "a = { b = yes }"})
        overlay.check_setups({})
        self.assertFalse(self.dest.exists())


class RemoveTest(OverlayTestCase):
    def test_remove_deletes_a_marked_overlay(self):
        self.build({"alpha": SETUP_A})
        self.assertIs(overlay.remove(self.dest), True)
        self.assertFalse(self.dest.exists())
        self.assertTrue(self.mods.is_dir(), "only the overlay itself goes")

    def test_remove_of_a_missing_folder_is_false(self):
        self.assertIs(overlay.remove(self.dest), False)
        self.assertIs(overlay.remove(self.base / "no" / overlay.OVERLAY_NAME), False)

    def test_remove_refuses_a_folder_without_the_marker(self):
        self.dest.mkdir(parents=True)
        files = self.write_owner_files(self.dest)
        self.assertIs(overlay.remove(self.dest), False)
        self.assert_files_untouched(self.dest, files)

    def test_remove_refuses_a_folder_whose_metadata_is_missing_or_unreadable(self):
        for label, content in (("missing", None), ("not json", b"{ nope"), ("a list", b"[1]"), ("a number", b"7"),
                               ("no description", b'{"name": "x"}'), ("odd description", b'{"short_description": 5}'),
                               ("bytes", b"\xff\xfe\x00")):
            with self.subTest(label=label):
                folder = self.base / label.replace(" ", "_") / overlay.OVERLAY_NAME
                files = {"notes.txt": b"keep me"}
                folder.mkdir(parents=True)
                (folder / "notes.txt").write_bytes(b"keep me")
                if content is not None:
                    (folder / ".metadata").mkdir()
                    (folder / ".metadata" / "metadata.json").write_bytes(content)
                    files[".metadata/metadata.json"] = content
                self.assertIs(overlay.remove(folder), False)
                self.assert_files_untouched(folder, files)

    def test_remove_refuses_a_marked_folder_that_is_not_named_te_qa_overlay(self):
        self.build({"alpha": SETUP_A})
        elsewhere = self.mods / "renamed_overlay"
        self.dest.rename(elsewhere)
        before = self.listing(elsewhere)
        self.assertIs(overlay.remove(elsewhere), False)
        self.assertEqual(self.listing(elsewhere), before)

    def test_remove_does_not_follow_a_symlink(self):
        real = self.base / "real" / overlay.OVERLAY_NAME
        real.parent.mkdir()
        self.build({"alpha": SETUP_A}, dest=real)
        link = self.mods / overlay.OVERLAY_NAME
        try:
            link.symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest("no symlinks here")
        before = self.listing(real)
        self.assertIs(overlay.remove(link), False)
        self.assertTrue(link.is_symlink())
        self.assertEqual(self.listing(real), before)

    def test_a_failed_remove_keeps_the_marker_so_a_later_remove_finishes(self):
        if os.geteuid() == 0:
            self.skipTest("root ignores read-only folders")
        self.build({"alpha": SETUP_A})
        locked = self.dest / "events" / "locked"
        locked.mkdir()
        (locked / "x.txt").write_bytes(b"x")

        def unlock():
            if locked.exists():
                locked.chmod(0o755)

        locked.chmod(0o555)
        self.addCleanup(unlock)  # runs before the temp folder is removed
        with self.assertRaises(OSError):
            overlay.remove(self.dest)
        self.assertTrue((self.dest / ".metadata" / "metadata.json").is_file(), "the marker is deleted last")
        unlock()
        self.assertIs(overlay.remove(self.dest), True)
        self.assertFalse(self.dest.exists())

    def test_remove_unlinks_a_symlink_inside_the_overlay_without_following_it(self):
        outside = self.base / "owner folder"
        outside.mkdir()
        (outside / "keep.txt").write_bytes(b"the owner's file")
        self.build({"alpha": SETUP_A})
        try:
            (self.dest / "events" / "link_to_folder").symlink_to(outside, target_is_directory=True)
            (self.dest / "events" / "link_to_file").symlink_to(outside / "keep.txt")
        except OSError:
            self.skipTest("no symlinks here")
        self.assertIs(overlay.remove(self.dest), True)
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.listing(outside), ["keep.txt"])
        self.assertEqual((outside / "keep.txt").read_bytes(), b"the owner's file")

    def test_remove_reads_the_marker_through_a_bom(self):
        self.build()
        meta = self.dest / ".metadata" / "metadata.json"
        meta.write_bytes(BOM + meta.read_bytes())
        self.assertIs(overlay.remove(self.dest), True)


class LeftoverBuildTest(OverlayTestCase):
    """R4: a build killed between its mkdtemp and its rename leaves a temp folder; `remove_build` deletes it under
    `remove`'s checks."""

    def killed_build(self, name=".te_qa_overlay.tmp-k3j_9x2a") -> Path:
        """What a build killed after its first write leaves: build's files under build's temp name."""
        self.build({"alpha": SETUP_A}).dir.rename(self.mods / name)
        return self.mods / name

    def test_a_marked_temp_folder_is_listed_and_removed(self):
        temp = self.killed_build()
        (self.mods / "owner_mod").mkdir()
        self.assertEqual(overlay.leftover_builds(self.mods), [temp])
        self.assertIs(overlay.remove_build(temp), True)
        self.assertFalse(os.path.lexists(temp))
        self.assertEqual(sorted(os.listdir(self.mods)), ["owner_mod"])
        self.assertEqual(overlay.leftover_builds(self.base / "no such folder"), [])

    def test_a_real_build_cut_short_leaves_a_folder_that_is_listed(self):
        def killed(*args):
            raise KeyboardInterrupt
        with mock.patch.object(overlay.shutil, "rmtree"), mock.patch.object(overlay.os, "rename", killed):
            with self.assertRaises(KeyboardInterrupt):
                self.build({"alpha": SETUP_A})
        [temp] = overlay.leftover_builds(self.mods)
        self.assertIs(overlay.remove_build(temp), True)
        self.assertEqual(os.listdir(self.mods), [])

    def test_an_unmarked_or_misnamed_folder_is_left(self):
        unmarked = self.mods / ".te_qa_overlay.tmp-zz9"
        unmarked.mkdir()
        (unmarked / "notes.txt").write_bytes(b"keep me")
        misnamed = self.killed_build(".te_qa_overlay.tmp-abc.bak")
        self.assertEqual(overlay.leftover_builds(self.mods), [unmarked])
        self.assertIs(overlay.remove_build(unmarked), False)
        self.assertIs(overlay.remove_build(misnamed), False)
        self.assertIs(overlay.remove_build(self.build().dir), False)      # the overlay itself: `remove`'s job
        self.assert_files_untouched(unmarked, {"notes.txt": b"keep me"})
        self.assertTrue((misnamed / overlay.METADATA_FILE).is_file())

    def test_a_marker_reached_through_a_symlink_lets_nothing_be_deleted(self):
        real = self.base / "real" / overlay.OVERLAY_NAME
        real.parent.mkdir()
        self.build(dest=real)
        for folder in (self.dest, self.mods / ".te_qa_overlay.tmp-sym1"):
            for label, link in (("the .metadata folder", ".metadata"), ("metadata.json", overlay.METADATA_FILE)):
                with self.subTest(folder=folder.name, link=label):
                    folder.mkdir()
                    (folder / "notes.txt").write_bytes(b"keep me")
                    target = real / link
                    (folder / link).parent.mkdir(parents=True, exist_ok=True)
                    try:
                        (folder / link).symlink_to(target, target_is_directory=target.is_dir())
                    except OSError:
                        self.skipTest("no symlinks here")
                    remove = overlay.remove if folder == self.dest else overlay.remove_build
                    self.assertIs(remove(folder), False)
                    self.assertEqual((folder / "notes.txt").read_bytes(), b"keep me")
                    self.assertTrue((real / overlay.METADATA_FILE).is_file())
                    (folder / link).unlink()
                    for path in sorted(folder.rglob("*"), reverse=True):
                        path.unlink() if path.is_file() else path.rmdir()
                    folder.rmdir()


class RefuseOverwriteTest(OverlayTestCase):
    def test_build_refuses_to_overwrite_a_folder_that_is_not_an_overlay(self):
        self.dest.mkdir(parents=True)
        files = self.write_owner_files(self.dest)
        with self.assertRaises(overlay.OverlayError):
            self.build({"alpha": SETUP_A})
        self.assert_files_untouched(self.dest, files)
        self.assertEqual(os.listdir(self.mods), [overlay.OVERLAY_NAME], "no temp folder left")

    def test_build_refuses_a_dest_that_is_a_file(self):
        self.dest.write_bytes(b"not a folder")
        with self.assertRaises(overlay.OverlayError):
            self.build()
        self.assertEqual(self.dest.read_bytes(), b"not a folder")
        self.assertEqual(os.listdir(self.mods), [overlay.OVERLAY_NAME])

    def test_build_refuses_a_dest_not_named_te_qa_overlay(self):
        for name in ("mod_x", "te_qa_overlay2", "TE_QA_OVERLAY"):
            with self.subTest(name=name):
                with self.assertRaises(overlay.OverlayError):
                    self.build(dest=self.mods / name)
                self.assertFalse((self.mods / name).exists())
        self.assertFalse(self.mods.exists() and os.listdir(self.mods))

    def fail_the_third_write(self):
        """Patch Path.write_bytes so the third file written raises, as a full disk would."""
        real = Path.write_bytes
        count = []

        def flaky(path, data):
            count.append(path)
            if len(count) == 3:
                raise OSError("no space left on device")
            return real(path, data)

        return mock.patch.object(Path, "write_bytes", flaky)

    def test_build_leaves_nothing_when_a_write_fails(self):
        with self.fail_the_third_write():
            with self.assertRaises(OSError):
                self.build({"alpha": SETUP_A})
        self.assertEqual(os.listdir(self.mods), [], "no half overlay, no temp folder")

    def test_a_failed_build_keeps_the_old_overlay(self):
        self.build({"alpha": SETUP_A})
        before = {p: p.read_bytes() for p in self.dest.rglob("*") if p.is_file()}
        with self.fail_the_third_write():
            with self.assertRaises(OSError):
                self.build({"beta": SETUP_B})
        self.assertEqual({p: p.read_bytes() for p in self.dest.rglob("*") if p.is_file()}, before)
        self.assertEqual(os.listdir(self.mods), [overlay.OVERLAY_NAME])

    def test_other_files_in_the_mod_folder_are_left_alone(self):
        (self.mods / "owner_file.txt").write_bytes(b"the owner's file")
        self.build()
        overlay.remove(self.dest)
        self.assertEqual(os.listdir(self.mods), ["owner_file.txt"])
        self.assertEqual((self.mods / "owner_file.txt").read_bytes(), b"the owner's file")


class ParseDateTest(unittest.TestCase):
    MONTHS = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    )

    def test_parse_date(self):
        for number, name in enumerate(self.MONTHS, start=1):
            with self.subTest(month=name):
                self.assertEqual(overlay.parse_date(f"TE_QA read country=FRA date={name} 11, 1836"), (1836, number, 11))

    def test_parse_date_reads_a_log_line_with_a_prefix_and_a_one_digit_day(self):
        line = "[12:03:44][jomini_script_system.cpp:1]: TE_QA read country=GBR date=March 5, 1901\n"
        self.assertEqual(overlay.parse_date(line), (1901, 3, 5))

    def test_a_line_without_a_date_is_none(self):
        for line in (
            "",
            "TE_QA read country=FRA",
            "TE_QA read country=FRA date=",
            "TE_QA read country=FRA date=Smarch 11, 1836",
            "TE_QA read country=FRA date=January 11 1836",
            "TE_QA read country=FRA date=January 11, 36",
            "TE_QA read country=FRA date=January 0, 1836",
            "TE_QA read country=FRA date=January 32, 1836",
            "January 11, 1836",
            "TE_QA setup alpha done",
        ):
            with self.subTest(line=line):
                self.assertIsNone(overlay.parse_date(line))


if __name__ == "__main__":
    unittest.main()
