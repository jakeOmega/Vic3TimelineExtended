"""Unit tests for game_log_reader: parsing, classification, mod-only filter,
dedup, diff, session clustering, and category summarization.
"""
import os
import tempfile
import time
import unittest

from game_log_reader import (
    parse_log,
    LogEntry,
    LogFileInfo,
    list_logs,
    filter_mod_only,
    filter_entries,
    dedupe,
    diff_against_backup,
    cluster_sessions,
    summarize,
    render_error_log_digest,
    SOURCE_CATEGORY_PREFIX,
)


def _write_log(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".log")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class ParseLogTests(unittest.TestCase):
    def test_parses_prefixed_lines(self):
        path = _write_log(
            "[00:03:32][gamedatabase.h:378]: Duplicated key concept_arable_land\n"
            "[00:03:33][pdx_persistent_reader.cpp:268]: Error: \"Unknown modifier type: bbuilding_employment_bureaucrats_add\" in file: \"common/production_methods/strategic_reserve_pms.txt\" near line: 32\n"
        )
        try:
            entries = parse_log(path)
        finally:
            os.remove(path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].time, "00:03:32")
        self.assertEqual(entries[0].source, "gamedatabase.h:378")
        self.assertEqual(entries[0].source_file, "gamedatabase.h")
        self.assertIn("Duplicated key", entries[0].message)
        self.assertEqual(entries[0].category, "duplicated_key")

        # Second entry references a mod file path; `files` should pick it up.
        self.assertIn("common/production_methods/strategic_reserve_pms.txt", entries[1].files)
        self.assertEqual(entries[1].category, "script_parse_error")

    def test_continuation_lines_attach_to_previous(self):
        path = _write_log(
            "[00:01:00][engine.cpp:1]: First line\n"
            "  continuation 1\n"
            "  continuation 2\n"
            "[00:01:01][engine.cpp:2]: Second entry\n"
        )
        try:
            entries = parse_log(path)
        finally:
            os.remove(path)
        self.assertEqual(len(entries), 2)
        self.assertIn("continuation 1", entries[0].message)
        self.assertIn("continuation 2", entries[0].message)

    def test_unprefixed_lines_become_their_own_entries(self):
        # game.log has lots of perf-summary lines without the [time][src] prefix;
        # they parse as individual entries with empty time/source.
        path = _write_log(
            "Executing Command, split_formation_command, 0 ms\n"
            "  ExecuteGameCommand, 0 ms\n"
        )
        try:
            entries = parse_log(path)
        finally:
            os.remove(path)
        self.assertEqual(len(entries), 2)
        for e in entries:
            self.assertEqual(e.time, "")
            self.assertEqual(e.source, "")
        self.assertIn("Executing Command", entries[0].message)
        self.assertIn("ExecuteGameCommand", entries[1].message)

    def test_cache_returns_same_list_on_repeat_call(self):
        path = _write_log("[00:00:00][a.cpp:1]: x\n")
        try:
            first = parse_log(path)
            second = parse_log(path)
        finally:
            os.remove(path)
        self.assertIs(first, second)


class ClassificationTests(unittest.TestCase):
    def test_known_source_prefixes_map_to_category(self):
        e = LogEntry("00:00:00", "gamedatabase.h:378", "Duplicated key foo")
        self.assertEqual(e.category, "duplicated_key")
        e = LogEntry("00:00:00", "pdx_persistent_reader.cpp:268", "Unknown modifier type: ...")
        self.assertEqual(e.category, "script_parse_error")
        e = LogEntry("00:00:00", "jomini_effect.cpp:752", "Inconsistent effect scopes")
        self.assertEqual(e.category, "inconsistent_effect_scope")
        e = LogEntry("00:00:00", "virtualfilesystem.cpp:569", "Could not find texture")
        self.assertEqual(e.category, "missing_file")

    def test_unknown_source_falls_back_to_other(self):
        e = LogEntry("00:00:00", "completely_made_up.cpp:99", "whatever")
        self.assertEqual(e.category, "other")

    def test_file_part_match_when_specific_line_unknown(self):
        # `pdx_gui_factory.cpp:611` and `:909` aren't in the prefix table but
        # the file-only mapping should catch them.
        e = LogEntry("00:00:00", "pdx_gui_factory.cpp:909", "X is not a valid type")
        self.assertEqual(e.category, "gui_parse_error")


class FilterTests(unittest.TestCase):
    def test_mod_only_keeps_entries_with_mod_paths(self):
        a = LogEntry("00:00:00", "x.cpp:1", "error in common/buildings/foo.txt: bad")
        b = LogEntry("00:00:00", "x.cpp:2", "error in /some/other/system/path: bad")
        c = LogEntry("00:00:00", "x.cpp:3", "error in events/bar.txt happened")
        self.assertEqual(len(filter_mod_only([a, b, c])), 2)

    def test_filter_entries_q(self):
        a = LogEntry("00:00:00", "x.cpp:1", "Apple is red")
        b = LogEntry("00:00:00", "x.cpp:2", "Banana is yellow")
        result = filter_entries([a, b], q="banana")
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], b)

    def test_filter_entries_file_glob(self):
        a = LogEntry("00:00:00", "x.cpp:1", "msg references events/cultural_hegemony_events.txt")
        b = LogEntry("00:00:00", "x.cpp:2", "msg references events/banking_cycle_events.txt")
        result = filter_entries([a, b], file_glob="*hegemony*")
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], a)

    def test_filter_entries_source(self):
        a = LogEntry("00:00:00", "jomini_effect.cpp:752", "x")
        b = LogEntry("00:00:00", "gamedatabase.h:378", "y")
        result = filter_entries([a, b], source="jomini_effect")
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], a)

    def test_filter_entries_category(self):
        a = LogEntry("00:00:00", "gamedatabase.h:378", "Duplicated key concept_x")
        b = LogEntry("00:00:00", "virtualfilesystem.cpp:569", "Could not find texture")
        result = filter_entries([a, b], category="missing_file")
        self.assertEqual(result, [b])

    def test_filter_entries_since(self):
        a = LogEntry("00:01:00", "x.cpp:1", "early")
        b = LogEntry("00:05:00", "x.cpp:2", "later")
        result = filter_entries([a, b], since="00:03:00")
        self.assertEqual(result, [b])


class DedupeTests(unittest.TestCase):
    def test_dedupe_normalizes_line_numbers(self):
        # Two different lines that differ only in a referenced line number
        # should collapse into one bucket so a UI-element error emitted with
        # different line counts still only shows up once.
        entries = [
            LogEntry("00:00:01", "engine.cpp:1", "Bad thing in events/foo.txt:32"),
            LogEntry("00:00:02", "engine.cpp:1", "Bad thing in events/foo.txt:32"),
            LogEntry("00:00:03", "engine.cpp:1", "Bad thing in events/foo.txt:33"),
        ]
        result = dedupe(entries, key="message+file")
        # "32" vs "33" both normalize to "<n>" so all three should collapse.
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["repeated_times"], 3)
        self.assertEqual(result[0]["first_seen"], "00:00:01")
        self.assertEqual(result[0]["last_seen"], "00:00:03")

    def test_dedupe_exact_keeps_distinct_lines(self):
        entries = [
            LogEntry("00:00:01", "engine.cpp:1", "Bad thing line 32"),
            LogEntry("00:00:02", "engine.cpp:1", "Bad thing line 33"),
        ]
        result = dedupe(entries, key="exact")
        self.assertEqual(len(result), 2)

    def test_dedupe_message_only_ignores_files(self):
        a = LogEntry("00:00:01", "engine.cpp:1", "Same message")
        b = LogEntry("00:00:02", "engine.cpp:1", "Same message")
        result = dedupe([a, b], key="message")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["repeated_times"], 2)


class DiffTests(unittest.TestCase):
    def test_diff_returns_added_and_removed(self):
        backup = [
            LogEntry("00:00:00", "engine.cpp:1", "old issue at events/foo.txt:32"),
            LogEntry("00:00:00", "engine.cpp:2", "shared issue at common/x.txt:1"),
        ]
        current = [
            LogEntry("00:01:00", "engine.cpp:2", "shared issue at common/x.txt:1"),
            LogEntry("00:01:00", "engine.cpp:3", "new issue at events/bar.txt:12"),
        ]
        diff = diff_against_backup(current, backup)
        self.assertEqual(diff["added_count_unique"], 1)
        self.assertEqual(diff["added"][0]["message"], "new issue at events/bar.txt:12")
        self.assertEqual(diff["removed_count"], 1)

    def test_diff_dedupes_added_block(self):
        backup = []
        current = [
            LogEntry("00:00:00", "x.cpp:1", "same issue at events/foo.txt:1"),
            LogEntry("00:00:00", "x.cpp:1", "same issue at events/foo.txt:1"),
            LogEntry("00:00:00", "x.cpp:1", "same issue at events/foo.txt:1"),
        ]
        diff = diff_against_backup(current, backup)
        self.assertEqual(diff["added_count_raw"], 3)
        self.assertEqual(diff["added_count_unique"], 1)


class ListLogsTests(unittest.TestCase):
    def test_groups_rotated_backups_and_skips_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fname, content in [
                ("error.log", "[00:00:00][a.cpp:1]: latest\n"),
                ("error.1.log", "[00:00:00][a.cpp:1]: prev1\n"),
                ("error.2.log", "[00:00:00][a.cpp:1]: prev2\n"),
                ("ai.log", ""),  # empty — should be skipped
                ("debug.log", "[00:00:00][a.cpp:1]: debug\n"),
            ]:
                with open(os.path.join(tmp, fname), "w") as f:
                    f.write(content)
            infos = list_logs(tmp)
        names = sorted(i.label for i in infos)
        self.assertEqual(names, ["debug.log", "error.1.log", "error.2.log", "error.log"])
        # ai.log was empty; excluded.
        self.assertNotIn("ai.log", names)

    def test_excludes_mp_session_backups_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fname in ("error.log", "error-Manfred.log", "error-pickle.log"):
                with open(os.path.join(tmp, fname), "w") as f:
                    f.write("[00:00:00][a.cpp:1]: x\n")
            without = list_logs(tmp, include_mp_sessions=False)
            with_mp = list_logs(tmp, include_mp_sessions=True)
        self.assertEqual([i.label for i in without], ["error.log"])
        self.assertEqual(len(with_mp), 3)


class ClusterSessionsTests(unittest.TestCase):
    def test_clusters_close_in_time(self):
        now = time.time()
        # Three files within a 5-min window + one ten minutes later
        infos = [
            LogFileInfo("error", 0, "/x", now, 100, 10, "error.log"),
            LogFileInfo("debug", 0, "/x", now + 30, 100, 10, "debug.log"),
            LogFileInfo("game", 0, "/x", now + 60, 100, 10, "game.log"),
            LogFileInfo("error", 1, "/x", now + 60 * 60, 100, 10, "error.1.log"),
        ]
        sessions = cluster_sessions(infos, window_seconds=300)
        self.assertEqual(len(sessions), 2)
        # Most recent session first
        self.assertIn("error.log", sessions[1]["files"])  # earlier session is the older one


class SummarizeTests(unittest.TestCase):
    def test_category_histogram_and_top_repeats(self):
        entries = [
            LogEntry("00:00:01", "gamedatabase.h:378", "Duplicated key foo at common/x.txt:1"),
            LogEntry("00:00:02", "gamedatabase.h:378", "Duplicated key foo at common/x.txt:1"),
            LogEntry("00:00:03", "gamedatabase.h:378", "Duplicated key foo at common/x.txt:1"),
            LogEntry("00:00:04", "virtualfilesystem.cpp:569", "Could not find common/y.dds"),
        ]
        summary = summarize(entries)
        self.assertEqual(summary["total_entries"], 4)
        self.assertEqual(summary["categories"]["duplicated_key"], 3)
        self.assertEqual(summary["categories"]["missing_file"], 1)
        self.assertGreaterEqual(len(summary["top_repeats"]), 1)
        # Top repeat is the 3x duplicated_key
        self.assertEqual(summary["top_repeats"][0]["repeated_times"], 3)
        self.assertEqual(summary["top_repeats"][0]["category"], "duplicated_key")


class RenderErrorLogDigestTests(unittest.TestCase):
    def test_no_log_returns_friendly_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            digest = render_error_log_digest(tmp, mod_path="/tmp/mod")
        self.assertIn("No current `error.log` found", digest)

    def test_digest_includes_categories_and_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "error.log"), "w") as f:
                f.write(
                    "[00:00:01][gamedatabase.h:378]: Duplicated key concept_a at common/x.txt:1\n"
                    "[00:00:02][gamedatabase.h:378]: Duplicated key concept_b at common/y.txt:2\n"
                    "[00:00:03][virtualfilesystem.cpp:569]: Could not find common/z.dds\n"
                )
            with open(os.path.join(tmp, "error.1.log"), "w") as f:
                f.write(
                    "[00:00:01][gamedatabase.h:378]: Duplicated key concept_a at common/x.txt:1\n"
                )
            digest = render_error_log_digest(tmp, mod_path="/tmp/mod")
        self.assertIn("# Error Log Digest", digest)
        self.assertIn("`duplicated_key`", digest)
        self.assertIn("`missing_file`", digest)
        # diff section should appear because error.1.log exists
        self.assertIn("## Diff vs `error.1.log`", digest)
        # The new "Could not find" line should show up under "New since last launch"
        self.assertIn("Could not find common/z.dds", digest)


if __name__ == "__main__":
    unittest.main()
